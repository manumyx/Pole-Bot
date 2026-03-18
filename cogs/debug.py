"""
Cog de Depuración v2.0 - REFACTORIZADO
Comandos de debug unificados y optimizados.
Se carga solo si DEBUG=1 en .env

Este archivo NO requiere de traducciones ya que los comandos son
solo para uso interno y no se exponen a los usuarios finales.
Como excepción, sólo diálogos que se mostrarían de cara a los usuarios SÍ
deben usar traducciones (ej: Compensación por Downtime).
"""
import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Any, Coroutine
import inspect

import discord
from discord.ext import commands
from discord import app_commands

from utils.database import Database
from utils.scoring import (
    calculate_points, classify_delay, get_pole_emoji, get_pole_name,
    update_streak, get_rank_info, get_current_season,
    RANK_THRESHOLDS, RANK_BADGES, RANK_NAMES
)
from utils.i18n import t

# Logger
log = logging.getLogger('DebugCog')

# Emoji constante para rachas
FIRE = "🔥"

# Emoji de fuego personalizado
FIRE = "<a:fire:1440018375144374302>"


def _is_allowed_user(interaction: discord.Interaction) -> bool:
    """
    CRÍTICO DE SEGURIDAD: Solo usuarios en DEBUG_ALLOWLIST pueden ejecutar comandos debug.
    """
    if interaction.user is None:
        return False
    
    allow = os.getenv('DEBUG_ALLOWLIST', '')
    if not allow:
        return False  # Seguro por defecto
    
    try:
        allowed_ids = {int(x.strip()) for x in allow.split(',') if x.strip()}
    except Exception:
        return False
    
    return interaction.user.id in allowed_ids


def debug_only():
    """Check decorator para comandos de debug."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if os.getenv('DEBUG', '0') not in ('1', 'true', 'True'):
            await interaction.response.send_message(
                "❌ Debug desactivado. Pon DEBUG=1 en .env",
                ephemeral=True
            )
            return False
        if not _is_allowed_user(interaction):
            await interaction.response.send_message(
                "❌ No tienes permiso para usar comandos de debug.",
                ephemeral=True
            )
            return False
        return True
    return app_commands.check(predicate)


class DebugCog(commands.Cog):
    def __init__(self, bot):  # type: ignore[override] — PoleBot tiene _db
        self.bot = bot
        self.db = bot._db  # Instancia compartida de Database (creada en main.py)

    debug = app_commands.Group(name="debug", description="Herramientas de depuración v2.0")

    # ==================== INFORMACIÓN Y DIAGNÓSTICO ====================
    
    @debug.command(name="info", description="📊 Info completa del servidor o historial de usuario")
    @app_commands.describe(usuario="Ver historial de poles de este usuario (opcional)")
    @debug_only()
    async def info(self, interaction: discord.Interaction, usuario: Optional[discord.Member] = None):
        """
        Muestra info del servidor O historial de un usuario específico.
        UNIFICA: server_info + user_poles
        """
        if not interaction.guild:
            await interaction.response.send_message("❌ Solo en servidores.", ephemeral=True)
            return
        
        gid = interaction.guild.id
        
        # ========== MODO 1: HISTORIAL DE USUARIO ==========
        if usuario:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                since = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
                
                cursor.execute('''
                    SELECT id, DATE(user_time) as fecha, pole_type, points_earned, 
                           streak_at_time, delay_minutes
                    FROM poles
                    WHERE user_id = ? AND guild_id = ? AND DATE(user_time) >= ?
                    ORDER BY user_time DESC
                    LIMIT 20
                ''', (usuario.id, gid, since))
                
                poles = cursor.fetchall()
            
            if not poles:
                await interaction.response.send_message(
                    f"❌ {usuario.mention} no tiene poles en los últimos 7 días.",
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title=f"📜 Historial - {usuario.display_name}",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            lines = []
            for p in poles:
                emoji = {'critical': '💎', 'fast': '⚡', 'normal': '🏁', 'marranero': '🐷'}.get(p[2], '❓')
                lines.append(
                    f"{emoji} **{p[1]}** • {p[2]} • {p[3]:.1f}pts • racha:{p[4]} • {p[5]}min"
                )
            
            embed.description = "\n".join(lines[:15])
            if len(lines) > 15:
                embed.set_footer(text=f"Mostrando 15 de {len(lines)} poles")
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # ========== MODO 2: INFO DEL SERVIDOR ==========
        config = self.db.get_server_config(gid) or {}
        
        embed = discord.Embed(
            title=f"🔧 Información del Servidor",
            description=f"**{interaction.guild.name}**\nGuild ID: `{gid}`",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Canal
        channel_id = config.get('pole_channel_id')
        channel_str = f"<#{channel_id}>" if channel_id else "❌ No configurado"
        embed.add_field(name="📺 Canal", value=channel_str, inline=False)
        
        # Hora de apertura + tiempo restante/pasado
        daily_time = config.get('daily_pole_time')
        time_str = f"**{daily_time}**" if daily_time else "❌ No configurada"
        
        if daily_time:
            try:
                now = datetime.now()
                h, m, s = [int(x) for x in daily_time.split(':')]
                opening = datetime(now.year, now.month, now.day, h, m, s)
                
                if now < opening:
                    delta = opening - now
                    hours = int(delta.total_seconds() // 3600)
                    minutes = int((delta.total_seconds() % 3600) // 60)
                    time_str += f"\n⏳ Abre en {hours}h {minutes}m"
                else:
                    delta = now - opening
                    hours = int(delta.total_seconds() // 3600)
                    minutes = int((delta.total_seconds() % 3600) // 60)
                    time_str += f"\n✅ Abierto hace {hours}h {minutes}m"
            except:
                pass
        
        embed.add_field(name="⏰ Hora de Hoy", value=time_str, inline=True)
        
        # Notificaciones + Rol
        notify_opening = "✅" if config.get('notify_opening', 1) else "❌"
        notify_winner = "✅" if config.get('notify_winner', 1) else "❌"
        role_id = config.get('ping_role_id')
        role_str = f"<@&{role_id}>" if role_id else "❌"
        ping_mode = config.get('ping_mode', 'none')
        
        embed.add_field(
            name="🔔 Notificaciones",
            value=f"Apertura: {notify_opening} | Ganador: {notify_winner}\nRol: {role_str} ({ping_mode})",
            inline=True
        )
        
        # Stats del día
        today_poles = self.db.get_poles_today(gid)
        total_members = sum(1 for m in interaction.guild.members if not m.bot)
        embed.add_field(
            name="📊 Hoy",
            value=f"**{len(today_poles)}** poles\n👥 {total_members} miembros",
            inline=True
        )
        
        # Schema version
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT version FROM schema_metadata ORDER BY version DESC LIMIT 1')
                schema_row = cursor.fetchone()
                schema_info = f"v{schema_row['version']}" if schema_row else "N/A"
        except:
            schema_info = "Error"
        
        embed.set_footer(text=f"Schema: {schema_info} | Usa /debug info @usuario para ver historial")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @debug.command(name="diagnose", description="🔬 Diagnóstico completo de usuario")
    @app_commands.describe(usuario="Usuario a diagnosticar (default: tú)")
    @debug_only()
    async def diagnose(self, interaction: discord.Interaction, usuario: Optional[discord.Member] = None):
        """Diagnóstico completo: datos, verificaciones, estado pole"""
        if not interaction.guild:
            await interaction.response.send_message("❌ Solo en servidores.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        target = usuario or interaction.user
        gid = interaction.guild.id
        now = datetime.now()
        today_str = now.strftime('%Y-%m-%d')
        yesterday_str = (now - timedelta(days=1)).strftime('%Y-%m-%d')
        
        config = self.db.get_server_config(gid)
        user_data = self.db.get_user(target.id, gid)
        
        embed = discord.Embed(
            title=f"🔬 Diagnóstico: {target.display_name}",
            color=discord.Color.blue(),
            timestamp=now
        )
        
        # ========== DATOS ==========
        if user_data:
            embed.add_field(
                name="👤 Datos",
                value=(
                    f"🆔 `{target.id}`\n"
                    f"💰 {user_data.get('total_points', 0):.1f} pts\n"
                    f"🏁 {user_data.get('total_poles', 0)} poles\n"
                    f"🔥 Racha: {user_data.get('current_streak', 0)} (mejor: {user_data.get('best_streak', 0)})"
                ),
                inline=True
            )
        else:
            embed.add_field(name="👤 Datos", value="⚠️ Primera vez", inline=True)
        
        # ========== POLE HOY/AYER ==========
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT pole_type, user_time, delay_minutes, points_earned
                FROM poles WHERE user_id = ? AND guild_id = ? AND pole_date = ?
                ORDER BY user_time DESC LIMIT 1
            ''', (target.id, gid, today_str))
            pole_today = cursor.fetchone()
            
            cursor.execute('''
                SELECT pole_type FROM poles
                WHERE user_id = ? AND guild_id = ? AND pole_date = ?
                ORDER BY user_time DESC LIMIT 1
            ''', (target.id, gid, yesterday_str))
            pole_yesterday = cursor.fetchone()
        
        pole_info = []
        if pole_today:
            emoji = {'critical': '💎', 'fast': '⚡', 'normal': '🏁', 'marranero': '🐷'}.get(pole_today[0], '❓')
            pole_info.append(f"HOY: {emoji} {pole_today[0]} • {pole_today[3]:.1f}pts • {pole_today[2]}min")
        else:
            pole_info.append("HOY: ❌")
        
        if pole_yesterday:
            emoji = {'critical': '💎', 'fast': '⚡', 'normal': '🏁', 'marranero': '🐷'}.get(pole_yesterday[0], '❓')
            pole_info.append(f"AYER: {emoji} {pole_yesterday[0]}")
        else:
            pole_info.append("AYER: ❌")
        
        embed.add_field(name="🗓️ Historial", value="\n".join(pole_info), inline=True)
        
        # ========== VERIFICACIONES ==========
        checks = []
        can_pole = True
        
        if not config or not config.get('pole_channel_id'):
            checks.append("❌ Sin canal")
            can_pole = False
        else:
            checks.append(f"✅ <#{config['pole_channel_id']}>")
        
        daily_time = config.get('daily_pole_time') if config else None
        if daily_time:
            try:
                h, m, s = [int(x) for x in daily_time.split(':')]
                opening = datetime(now.year, now.month, now.day, h, m, s)
                if now < opening:
                    mins = int((opening-now).total_seconds()//60)
                    checks.append(f"⏳ Abre en {mins}min")
                    can_pole = False
                else:
                    checks.append(f"🟢 Abierto")
            except:
                checks.append("⚠️ Error hora")
        else:
            checks.append("❌ Sin hora")
            can_pole = False
        
        if pole_today:
            checks.append("🛑 Ya hizo hoy")
            can_pole = False
        else:
            checks.append("✅ Sin pole hoy")
        
        global_today = self.db.get_user_pole_on_date_global(target.id, today_str)
        if global_today and int(global_today.get('guild_id', 0)) != gid:
            checks.append(f"🌍 Pole en otro server")
            can_pole = False
        
        embed.add_field(name="🔍 Checks", value="\n".join(checks), inline=True)
        embed.add_field(
            name="🎯 Veredicto", 
            value="✅ PUEDE" if can_pole else "❌ NO PUEDE", 
            inline=True
        )
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    # ==================== GESTIÓN DE POLE TIME ====================
    
    @debug.command(name="pole_time", description="⏰ Gestionar hora de apertura del pole")
    @app_commands.describe(
        accion="Qué hacer con la hora",
        hora="Hora personalizada (0-23, solo para 'custom')",
        minuto="Minuto personalizado (0-59, solo para 'custom')"
    )
    @app_commands.choices(accion=[
        app_commands.Choice(name="🟢 Abrir AHORA", value="now"),
        app_commands.Choice(name="🕐 Hora Custom", value="custom"),
        app_commands.Choice(name="🔄 Regenerar", value="regenerate"),
    ])
    @debug_only()
    async def pole_time(
        self, 
        interaction: discord.Interaction, 
        accion: str,
        hora: Optional[app_commands.Range[int, 0, 23]] = None,
        minuto: Optional[int] = None
    ):
        """
        UNIFICA: set_opening + force_generate + open_now
        """
        if not interaction.guild:
            await interaction.response.send_message("❌ Solo en servidores.", ephemeral=True)
            return
        
        gid = interaction.guild.id
        
        # ========== ABRIR AHORA ==========
        if accion == "now":
            now = datetime.now()
            time_str = now.strftime("%H:%M:%S")
            self.db.set_daily_pole_time(gid, time_str)
            
            cfg = self.db.get_server_config(gid)
            if cfg and cfg.get('notify_opening', 1) and cfg.get('pole_channel_id'):
                pole_cog = self.bot.get_cog('PoleCog')
                send_fn = getattr(pole_cog, 'send_opening_notification', None) if pole_cog else None
                if callable(send_fn):
                    try:
                        if asyncio.iscoroutinefunction(send_fn):
                            await send_fn(
                                gid, cfg['pole_channel_id'],
                                cfg.get('ping_role_id'), cfg.get('ping_mode', 'none')
                            )
                    except Exception as e:
                        log.error(f"⚠️ Error enviando notificación: {e}")
            
            await interaction.response.send_message(
                f"✅ Pole abierto AHORA ({time_str})\n"
                f"💬 Escribe **pole** en el canal configurado.",
                ephemeral=True
            )
        
        # ========== HORA CUSTOM ==========
        elif accion == "custom":
            if hora is None:
                await interaction.response.send_message(
                    "❌ Debes especificar `hora` (0-23) para acción 'custom'",
                    ephemeral=True
                )
                return
            
            if minuto is None:
                minuto = 0
            
            if minuto < 0 or minuto > 59:
                await interaction.response.send_message("❌ Minuto debe estar entre 0-59", ephemeral=True)
                return
            
            time_str = f"{hora:02d}:{minuto:02d}:00"
            self.db.set_daily_pole_time(gid, time_str)
            
            # Reprogramar notificación
            try:
                pole_cog = self.bot.get_cog('PoleCog')
                schedule_fn = getattr(pole_cog, 'schedule_all_today_notifications', None) if pole_cog else None
                if callable(schedule_fn):
                    result = schedule_fn()
                    if asyncio.iscoroutine(result):
                        asyncio.create_task(result)
            except Exception as e:
                log.error(f"⚠️ Error reprogramando: {e}")
            
            await interaction.response.send_message(
                f"✅ Hora custom configurada: **{time_str}**",
                ephemeral=True
            )
        
        # ========== REGENERAR ==========
        elif accion == "regenerate":
            await interaction.response.defer(ephemeral=True)
            
            try:
                pole_cog = self.bot.get_cog('PoleCog')
                if not pole_cog:
                    await interaction.followup.send("❌ No se encontró PoleCog", ephemeral=True)
                    return
                
                generator = getattr(pole_cog, 'daily_pole_generator', None)
                if generator and callable(generator):
                    generator_func = getattr(generator, 'callback', generator)
                    if callable(generator_func):
                        result = generator_func()
                        if inspect.iscoroutine(result):
                            await result  # type: ignore
                
                new_time = self.db.get_daily_pole_time(gid)
                
                await interaction.followup.send(
                    f"✅ Hora regenerada: **{new_time}**\n"
                    f"Usa `/debug info` para verificar.",
                    ephemeral=True
                )
            except Exception as e:
                await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    # ==================== MODIFICAR DATOS DE USUARIO ====================
    
    @debug.command(name="modify_user", description="✏️ Modificar datos de un usuario")
    @app_commands.describe(
        usuario="Usuario a modificar",
        tipo="Qué modificar",
        valor="Nuevo valor (número para points/streak, fecha YYYY-MM-DD para last_pole)"
    )
    @app_commands.choices(tipo=[
        app_commands.Choice(name="💰 Puntos (añadir)", value="add_points"),
        app_commands.Choice(name="🔥 Racha (establecer)", value="set_streak"),
        app_commands.Choice(name="📅 Último Pole (fecha)", value="set_last_pole"),
        app_commands.Choice(name="♻️ Restaurar Racha", value="restore_streak"),
    ])
    @debug_only()
    async def modify_user(
        self, 
        interaction: discord.Interaction, 
        usuario: discord.Member,
        tipo: str,
        valor: Optional[str] = None
    ):
        """
        UNIFICA: add_points + set_streak + set_last_pole + restore_streak
        """
        if not interaction.guild:
            await interaction.response.send_message("❌ Solo en servidores.", ephemeral=True)
            return
        
        gid = interaction.guild.id
        user_data = self.db.get_user(usuario.id, gid)
        
        # Crear usuario si no existe
        if not user_data:
            self.db.create_user(usuario.id, gid, usuario.name)
            user_data = self.db.get_user(usuario.id, gid) or {}
        
        embed = discord.Embed(
            title="✏️ Usuario Modificado",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        embed.add_field(name="👤 Usuario", value=usuario.mention, inline=False)
        
        # ========== ADD POINTS ==========
        if tipo == "add_points":
            if valor is None:
                await interaction.response.send_message("❌ Debes especificar `valor` (puntos a añadir)", ephemeral=True)
                return
            
            try:
                puntos = float(valor)
            except ValueError:
                await interaction.response.send_message("❌ Valor debe ser un número", ephemeral=True)
                return
            
            # Añadir a season_stats
            season_id = get_current_season()
            season_stats = self.db.get_season_stats(usuario.id, gid, season_id)
            old_season = float(season_stats.get("season_points", 0.0)) if season_stats else 0.0
            new_season = old_season + puntos
            self.db.update_season_stats(usuario.id, gid, season_id, season_points=new_season)
            
            embed.add_field(
                name="💰 Puntos Añadidos",
                value=f"Season ({season_id}): {old_season:.1f} → **{new_season:.1f}** (+{puntos:.1f})",
                inline=False
            )
        
        # ========== SET STREAK ==========
        elif tipo == "set_streak":
            if valor is None:
                await interaction.response.send_message("❌ Debes especificar `valor` (nueva racha)", ephemeral=True)
                return
            
            try:
                racha = int(valor)
            except ValueError:
                await interaction.response.send_message("❌ Valor debe ser un número entero", ephemeral=True)
                return
            
            # Obtener global_user (rachas son globales desde v5)
            global_user = self.db.get_global_user(usuario.id)
            if not global_user:
                await interaction.response.send_message("❌ Usuario no encontrado en global_users", ephemeral=True)
                return
            
            old_streak = global_user.get('current_streak', 0)
            old_best = global_user.get('best_streak', 0)
            new_best = max(old_best, racha)
            
            # Rachas se guardan en global_users, no en users
            self.db.update_global_user(usuario.id, current_streak=racha, best_streak=new_best)
            
            embed.add_field(name="🔥 Racha (Global)", value=f"{old_streak} → **{racha}**", inline=True)
            embed.add_field(name="🏆 Mejor", value=f"{old_best} → **{new_best}**", inline=True)
        
        # ========== SET LAST POLE ==========
        elif tipo == "set_last_pole":
            if valor is None:
                await interaction.response.send_message("❌ Debes especificar `valor` (fecha YYYY-MM-DD)", ephemeral=True)
                return
            
            try:
                datetime.strptime(valor, '%Y-%m-%d')
            except ValueError:
                await interaction.response.send_message("❌ Formato: YYYY-MM-DD (ej: 2026-01-15)", ephemeral=True)
                return
            
            old_date = user_data.get('last_pole_date', 'Nunca')
            self.db.update_user(usuario.id, gid, last_pole_date=valor)
            
            embed.add_field(name="📅 Último Pole", value=f"{old_date} → **{valor}**", inline=False)
        
        # ========== RESTORE STREAK ==========
        elif tipo == "restore_streak":
            # Obtener racha actual de global_users (donde se guardan las rachas)
            global_user = self.db.get_global_user(usuario.id)
            if not global_user:
                await interaction.response.send_message(
                    f"❌ {usuario.mention} no está registrado globalmente.",
                    ephemeral=True
                )
                return
            
            old_streak = global_user.get('current_streak', 0)
            best_streak = global_user.get('best_streak', 0)
            
            if best_streak == 0:
                await interaction.response.send_message(
                    f"❌ {usuario.mention} no tiene mejor racha registrada.",
                    ephemeral=True
                )
                return
            
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            # Actualizar en global_users (donde están las rachas)
            self.db.update_global_user(usuario.id, current_streak=best_streak, last_pole_date=yesterday)
            
            embed.add_field(name="♻️ Racha Restaurada", value=f"{old_streak} → **{best_streak}**", inline=True)
            embed.add_field(name="📅 Último Pole", value=f"Ajustado a {yesterday}", inline=True)
            embed.set_footer(text="⚠️ Debe hacer pole hoy para mantener la racha")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ==================== TESTING Y SIMULACIÓN ====================
    
    @debug.command(name="simulate_pole", description="🧪 Simular un pole con delay específico")
    @app_commands.describe(
        delay_minutos="Retraso desde apertura (0-2000 min)",
        usuario="Usuario objetivo (default: tú)"
    )
    @debug_only()
    async def simulate_pole(self, interaction: discord.Interaction, delay_minutos: int, usuario: Optional[discord.Member] = None):
        """Simula pole con delay específico (ESCRIBE EN BD)"""
        if not interaction.guild:
            await interaction.response.send_message("❌ Solo en servidores.", ephemeral=True)
            return
        
        target = usuario or interaction.user
        gid = interaction.guild.id
        
        opening_str = self.db.get_daily_pole_time(gid)
        if not opening_str:
            await interaction.response.send_message(
                "❌ Sin hora configurada. Usa `/debug pole_time`",
                ephemeral=True
            )
            return
        
        now = datetime.now()
        h, m, s = [int(x) for x in opening_str.split(':')]
        opening_time = datetime(now.year, now.month, now.day, h, m, s)
        user_time = opening_time + timedelta(minutes=delay_minutos)
        is_next_day = user_time.date() > opening_time.date()
        
        pole_date = opening_time.strftime('%Y-%m-%d') if is_next_day else user_time.strftime('%Y-%m-%d')
        pole_type = classify_delay(delay_minutos, is_next_day)
        
        user_data = self.db.get_user(target.id, gid)
        if not user_data:
            self.db.create_user(target.id, gid, target.name)
            user_data = self.db.get_user(target.id, gid) or {}
        
        current_streak = int(user_data.get("current_streak", 0))
        last_pole_date = user_data.get("last_pole_date")
        new_streak, _ = update_streak(last_pole_date, current_streak)
        
        base, mult, total = calculate_points(pole_type, new_streak)
        
        # Guardar pole
        self.db.save_pole(
            user_id=target.id, guild_id=gid,
            opening_time=opening_time, user_time=user_time,
            delay_minutes=delay_minutos, pole_type=pole_type,
            points_earned=total, streak=new_streak, pole_date=pole_date
        )
        
        # Actualizar usuario
        fields = {
            "current_streak": new_streak,
            "best_streak": max(int(user_data.get("best_streak", 0)), new_streak),
            "last_pole_date": now.strftime('%Y-%m-%d'),
            "username": target.name,
        }
        
        if pole_type == "critical":
            fields["critical_poles"] = int(user_data.get("critical_poles", 0)) + 1
        elif pole_type == "fast":
            fields["fast_poles"] = int(user_data.get("fast_poles", 0)) + 1
        elif pole_type == "normal":
            fields["normal_poles"] = int(user_data.get("normal_poles", 0)) + 1
        elif pole_type == "marranero":
            fields["marranero_poles"] = int(user_data.get("marranero_poles", 0)) + 1
        
        self.db.update_user(target.id, gid, **fields)
        
        # Respuesta
        emoji = get_pole_emoji(pole_type)
        name = get_pole_name(pole_type, gid)
        color_map = {
            'critical': discord.Color.gold(),
            'fast': discord.Color.from_rgb(192, 192, 192),
            'normal': discord.Color.green(),
            'marranero': discord.Color.from_rgb(205, 133, 63)
        }
        
        embed = discord.Embed(
            title=f"{emoji} {name} {emoji}",
            color=color_map.get(pole_type, discord.Color.blue()),
            timestamp=user_time
        )
        embed.description = f"(DEBUG) {target.mention} simulado"
        embed.add_field(name="⏱️ Hora", value=user_time.strftime('%H:%M:%S'), inline=True)
        embed.add_field(name="⏳ Delay", value=f"{delay_minutos} min", inline=True)
        embed.add_field(name="💰 Base", value=f"{base:.1f} pts", inline=True)
        embed.add_field(name=f"{FIRE} Racha", value=f"{new_streak} días (x{mult:.1f})", inline=True)
        embed.add_field(name="🎯 Total", value=f"**{total:.1f} pts**", inline=True)
        embed.set_footer(text="✅ Guardado en BD de producción")
        
        await interaction.response.send_message(embed=embed)

    @debug.command(name="reset_date", description="♻️ Resetear fecha de pole para testing")
    @app_commands.describe(usuario="Usuario (default: tú)")
    @debug_only()
    async def reset_date(self, interaction: discord.Interaction, usuario: Optional[discord.Member] = None):
        """Resetea last_pole_date y elimina poles de hoy"""
        if not interaction.guild:
            await interaction.response.send_message("❌ Solo en servidores.", ephemeral=True)
            return
        
        target = usuario or interaction.user
        gid = interaction.guild.id
        
        self.db.update_user(target.id, gid, last_pole_date=None)
        
        today = datetime.now().strftime('%Y-%m-%d')
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM poles 
                WHERE user_id = ? AND guild_id = ? AND DATE(created_at) = ?
            ''', (target.id, gid, today))
            deleted = cursor.rowcount
            conn.commit()
        
        await interaction.response.send_message(
            f"✅ {target.mention} reseteado\n"
            f"• last_pole_date → None\n"
            f"• Poles eliminados: {deleted}\n"
            f"💡 Ahora puede hacer `/debug pole_time now`",
            ephemeral=True
        )

    # ==================== TEMPORADAS Y MIGRACIONES ====================
    
    @debug.command(name="test_migration", description="🧪 Testear migración de temporada")
    @app_commands.describe(
        dry_run="Solo simular (recomendado)",
        target_season="Temporada objetivo (ej: 2026, season_1, preseason)"
    )
    @debug_only()
    async def test_migration(self, interaction: discord.Interaction, dry_run: bool = True, target_season: Optional[str] = None):
        """Testear sistema de migración de temporadas (DRY RUN o REAL)"""
        await interaction.response.defer(ephemeral=True)
        
        from utils.scoring import get_current_season, get_season_info
        
        if target_season is None:
            target_season = get_current_season()
        else:
            try:
                year = int(target_season)
                if year >= 2026:
                    target_season = f'season_{year - 2025}'
                elif year == 2025:
                    target_season = 'preseason'
            except ValueError:
                pass
        
        try:
            season_info = get_season_info(target_season)
        except ValueError as e:
            await interaction.followup.send(
                f"❌ Error: {e}\n**Formatos válidos:** preseason, season_1, 2026, etc.",
                ephemeral=True
            )
            return
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT season_id FROM seasons WHERE is_active = 1')
                row = cursor.fetchone()
                current_active = row[0] if row else "Ninguna"
            
            embed = discord.Embed(
                title="🧪 Test de Migración",
                color=discord.Color.orange() if dry_run else discord.Color.red(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="🔍 Estado",
                value=f"Activa: **{current_active}**\nObjetivo: **{target_season}**",
                inline=False
            )
            
            if dry_run:
                embed.add_field(
                    name="⚠️ MODO DRY RUN",
                    value="Solo simulación, sin cambios reales",
                    inline=False
                )
                
                if current_active == target_season:
                    embed.add_field(name="ℹ️ Resultado", value="Ya estamos en la temporada objetivo", inline=False)
                else:
                    with self.db.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute('SELECT COUNT(*) FROM season_stats WHERE season_id = ?', (current_active,))
                        stats_count = cursor.fetchone()[0]
                    
                    actions = [
                        f"✅ Finalizar **{current_active}**",
                        f"📊 Guardar {stats_count} registros",
                        f"🏆 Otorgar badges",
                        f"🔄 Activar **{target_season}**",
                        f"♻️ Resetear rachas",
                    ]
                    
                    embed.add_field(name="📋 Acciones", value="\n".join(actions), inline=False)
                
                embed.set_footer(text="Usa dry_run=False para ejecutar (¡CUIDADO!)")
            
            else:
                embed.add_field(name="🚨 MODO REAL", value="Migración REAL (no se puede deshacer)", inline=False)
                
                migrated = self.db.migrate_season(target_season, force=False)
                
                if migrated:
                    embed.add_field(
                        name="✅ Completado",
                        value=f"**{current_active}** → **{target_season}**",
                        inline=False
                    )
                    
                    verification = self.db.verify_migration_integrity(target_season)
                    
                    if verification['is_valid']:
                        embed.add_field(name="✅ Verificación", value="Todo OK", inline=False)
                    else:
                        issues = "\n".join([f"⚠️ {i}" for i in verification['issues']])
                        embed.add_field(name="⚠️ Problemas", value=issues, inline=False)
                else:
                    embed.add_field(name="ℹ️ Sin Cambios", value="Migración no necesaria", inline=False)
                
                embed.set_footer(text="Migración ejecutada en modo REAL")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    # ==================== COMPENSACIÓN POR DOWNTIME ====================
    
    @debug.command(name="compensate_downtime", description="🩹 Compensar usuarios afectados por caída del bot (TODOS los servidores)")
    @app_commands.describe(
        fecha="Fecha del downtime (YYYY-MM-DD, ej: 2026-02-14)",
        dry_run="Solo simular, no aplicar cambios reales"
    )
    @debug_only()
    async def compensate_downtime(
        self, 
        interaction: discord.Interaction,
        fecha: str,
        dry_run: bool = True
    ):
        """
        Compensa a TODOS los usuarios (en TODOS los servidores) afectados por downtime.
        
        - Identifica usuarios GLOBALMENTE con rachas activas que NO hicieron pole en la fecha
        - Les da un pole "normal" retroactivo en CADA servidor donde estaban activos
        - Mantiene/reactiva sus rachas globales
        - Envía mensaje oficial de disculpa en TODOS los canales configurados
        """
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Validar formato de fecha
            try:
                target_date = datetime.strptime(fecha, '%Y-%m-%d')
                fecha_str = target_date.strftime('%Y-%m-%d')
            except ValueError:
                await interaction.followup.send("❌ Formato de fecha inválido. Usa YYYY-MM-DD", ephemeral=True)
                return
            
            # No permitir fechas futuras
            if target_date.date() > datetime.now().date():
                await interaction.followup.send("❌ No puedes compensar fechas futuras", ephemeral=True)
                return
            
            # Obtener día anterior para verificar rachas
            day_before = (target_date - timedelta(days=1)).strftime('%Y-%m-%d')
            
            # ========== IDENTIFICAR USUARIOS AFECTADOS GLOBALMENTE ==========
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Obtener TODOS los usuarios que hicieron pole el día anterior (cualquier servidor)
                # IMPORTANTE: Usar streak_at_time del pole del día anterior, NO current_streak
                cursor.execute('''
                    SELECT DISTINCT p.user_id, gu.username, MAX(p.streak_at_time) as streak_before
                    FROM poles p
                    JOIN global_users gu ON p.user_id = gu.user_id
                    WHERE p.pole_date = ?
                    GROUP BY p.user_id
                ''', (day_before,))
                
                users_with_activity_before = cursor.fetchall()
                
                # De esos, filtrar quienes NO hicieron pole en la fecha del downtime
                affected_global = []
                for user_data in users_with_activity_before:
                    user_id = user_data['user_id']
                    
                    # Verificar si hizo pole en la fecha afectada (en cualquier servidor)
                    cursor.execute('''
                        SELECT COUNT(*) FROM poles
                        WHERE user_id = ? AND pole_date = ?
                    ''', (user_id, fecha_str))
                    
                    pole_count = cursor.fetchone()[0]
                    
                    if pole_count == 0:
                        # Este usuario NO hizo pole ese día → afectado
                        # Obtener en qué servidores estaba activo (todos los servidores recientes)
                        cursor.execute('''
                            SELECT DISTINCT guild_id
                            FROM poles
                            WHERE user_id = ?
                              AND DATE(created_at) >= DATE('now', '-30 days')
                            ORDER BY created_at DESC
                        ''', (user_id,))
                        
                        active_guilds = [row[0] for row in cursor.fetchall()]
                        
                        # Usar la racha que tenía en el pole del día anterior
                        affected_global.append({
                            'user_id': user_id,
                            'username': user_data['username'],
                            'streak': user_data['streak_before'],  # Racha del día anterior
                            'guilds': active_guilds
                        })
            
            if not affected_global:
                embed = discord.Embed(
                    title="ℹ️ Sin Usuarios Afectados",
                    description=f"No hay usuarios que necesiten compensación para **{fecha_str}**",
                    color=discord.Color.blue(),
                    timestamp=datetime.now()
                )
                embed.set_footer(text="No se encontraron rachas perdidas por downtime")
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # ========== SIMULAR O APLICAR COMPENSACIÓN ==========
            current_season = get_current_season()
            compensated_users = []
            total_poles_created = 0
            guilds_affected = set()
            
            for user_data in affected_global:
                user_id = user_data['user_id']
                username = user_data['username']
                streak = user_data['streak']
                guilds = user_data['guilds']
                
                if dry_run:
                    # Simulación
                    compensated_users.append({
                        'user_id': user_id,
                        'username': username,
                        'old_streak': streak,
                        'new_streak': streak + 1,
                        'guilds_count': len(guilds),
                        'guilds': guilds,  # Guardar para mensajes
                        'simulated': True
                    })
                    total_poles_created += len(guilds)
                    guilds_affected.update(guilds)
                else:
                    # Aplicar REAL
                    # Hora de apertura simulada: 09:00 del día afectado
                    opening_time = target_date.replace(hour=9, minute=0, second=0)
                    # Hora del pole simulada: 12:00 (3 horas después = normal)
                    pole_time = target_date.replace(hour=12, minute=0, second=0)
                    
                    # Calcular puntos (normal = 10 base + multiplicador de racha)
                    base_points = 10
                    multiplier = 1.0 + min(streak, 100) * 0.015
                    total_points = int(base_points * multiplier)
                    
                    # Validar que los guilds existen y el bot sigue ahí
                    valid_guilds = []
                    for guild_id in guilds:
                        guild = self.bot.get_guild(guild_id)
                        if guild:
                            valid_guilds.append(guild_id)
                        else:
                            log.warning(f"Bot ya no está en guild {guild_id}, saltando...")
                    
                    if not valid_guilds:
                        log.warning(f"Usuario {user_id} no tiene guilds válidos, saltando...")
                        continue
                    
                    # Crear pole en CADA servidor válido donde estaba activo
                    poles_created = 0
                    for guild_id in valid_guilds:
                        # ✅ VERIFICAR DUPLICADOS
                        with self.db.get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute('''
                                SELECT COUNT(*) FROM poles
                                WHERE user_id = ? AND guild_id = ? AND pole_date = ?
                            ''', (user_id, guild_id, fecha_str))
                            
                            existing = cursor.fetchone()[0]
                            
                            if existing > 0:
                                log.warning(f"Pole ya existe para user {user_id} en guild {guild_id} fecha {fecha_str}, saltando...")
                                continue
                            
                            # Insertar pole (sin username ni season_id, que no existen en la tabla)
                            cursor.execute('''
                                INSERT INTO poles (
                                    user_id, guild_id, opening_time, user_time,
                                    delay_minutes, pole_date, pole_type, 
                                    points_earned, streak_at_time
                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            ''', (
                                user_id, guild_id, opening_time, pole_time,
                                180,  # 3 horas (normal range)
                                fecha_str, 'normal', total_points, streak
                            ))
                            conn.commit()
                        
                        poles_created += 1
                        total_poles_created += 1
                        guilds_affected.add(guild_id)
                    
                    if poles_created == 0:
                        log.warning(f"No se crearon poles para user {user_id}, saltando...")
                        continue
                    
                    # ✅ Actualizar racha GLOBAL (solo si se creó al menos 1 pole)
                    new_streak = streak + 1
                    self.db.update_global_user(user_id, current_streak=new_streak)
                    
                    # Actualizar stats de temporada para cada servidor donde se creó pole
                    for guild_id in valid_guilds:
                        # Obtener stats actuales de la temporada
                        season_stats = self.db.get_season_stats(user_id, guild_id, current_season)
                        
                        if season_stats:
                            # Actualizar existente
                            season_update = {
                                'season_points': season_stats['season_points'] + total_points,
                                'season_poles': season_stats['season_poles'] + 1,
                                'season_normal': season_stats['season_normal'] + 1,
                                'season_best_streak': max(season_stats['season_best_streak'], new_streak)
                            }
                            self.db.update_season_stats(user_id, guild_id, current_season, **season_update)
                        else:
                            # Crear nueva entrada
                            season_data = {
                                'season_points': total_points,
                                'season_poles': 1,
                                'season_normal': 1,
                                'season_best_streak': new_streak
                            }
                            self.db.update_season_stats(user_id, guild_id, current_season, **season_data)
                    
                    compensated_users.append({
                        'user_id': user_id,
                        'username': username,
                        'old_streak': streak,
                        'new_streak': new_streak,
                        'guilds_count': poles_created,
                        'guilds': valid_guilds,  # Guardar para mensajes
                        'simulated': False
                    })
            
            # ========== MOSTRAR RESULTADO ==========
            embed = discord.Embed(
                title="🩹 Compensación Global por Downtime" if not dry_run else "🧪 Simulación de Compensación Global",
                description=(
                    f"**Fecha:** {fecha_str}\n"
                    f"**Usuarios afectados:** {len(compensated_users)}\n"
                    f"**Servidores afectados:** {len(guilds_affected)}\n"
                    f"**Poles a crear:** {total_poles_created}"
                ),
                color=discord.Color.green() if not dry_run else discord.Color.orange(),
                timestamp=datetime.now()
            )
            
            # Lista de usuarios
            user_lines = []
            for comp in compensated_users[:15]:  # Máximo 15 en embed
                emoji = "🔄" if comp['simulated'] else "✅"
                user_lines.append(
                    f"{emoji} <@{comp['user_id']}> • {FIRE} {comp['old_streak']}→{comp['new_streak']} • {comp['guilds_count']} servidor(es)"
                )
            
            if len(compensated_users) > 15:
                user_lines.append(f"... y {len(compensated_users) - 15} más")
            
            embed.add_field(
                name="👥 Usuarios Compensados",
                value="\n".join(user_lines) if user_lines else "Ninguno",
                inline=False
            )
            
            if dry_run:
                embed.add_field(
                    name="⚠️ MODO SIMULACIÓN",
                    value="Usa `dry_run=False` para aplicar los cambios REALES en TODOS los servidores",
                    inline=False
                )
                embed.set_footer(text="Ningún cambio aplicado (solo simulación)")
            else:
                embed.add_field(
                    name="✅ APLICADO GLOBALMENTE",
                    value=f"{total_poles_created} poles creados en {len(guilds_affected)} servidores",
                    inline=False
                )
                embed.set_footer(text=f"Cambios aplicados • {len(compensated_users)} usuarios • {len(guilds_affected)} servidores")
                
                # ========== ENVIAR MENSAJE DE DISCULPA EN TODOS LOS CANALES ==========
                messages_sent = 0
                for guild_id in guilds_affected:
                    config = self.db.get_server_config(guild_id)
                    if config and config.get('pole_channel_id'):
                        channel = self.bot.get_channel(config['pole_channel_id'])
                        if channel and isinstance(channel, discord.TextChannel):
                            try:
                                # Obtener idioma del servidor
                                lang = config.get('language', 'es')
                                
                                # Contar cuántos usuarios fueron compensados en ESTE servidor
                                users_in_guild = sum(1 for u in compensated_users if guild_id in u.get('guilds', []))
                                
                                apology_embed = discord.Embed(
                                    title=t('compensation.apology_title', guild_id),
                                    description=t('compensation.apology_desc', guild_id, 
                                                date=fecha_str, 
                                                count=len(compensated_users), 
                                                fire=FIRE),
                                    color=discord.Color.gold(),
                                    timestamp=datetime.now()
                                )
                                apology_embed.set_footer(text=t('compensation.apology_footer', guild_id, count=len(compensated_users)))
                                
                                await channel.send(embed=apology_embed)
                                messages_sent += 1
                            except Exception as e:
                                log.warning(f"⚠️ No se pudo enviar mensaje de disculpa en guild {guild_id}: {e}")
                
                if messages_sent > 0:
                    embed.add_field(
                        name="📢 Notificaciones",
                        value=f"Mensaje de disculpa enviado a {messages_sent} canal(es)",
                        inline=False
                    )
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    # ==================== RESTAURAR RACHA ====================
    
    @debug.command(name="restore_streak", description="🔧 Restaurar racha perdida de un usuario + compensar días y puntos")
    @app_commands.describe(
        usuario="Usuario al que restaurar la racha",
        guild_id="Guild ID donde dar los puntos de compensación (default: este servidor)",
        dry_run="Solo simular, no aplicar cambios"
    )
    @debug_only()
    async def restore_streak(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member,
        guild_id: Optional[str] = None,
        dry_run: bool = True
    ):
        """
        Restaurar racha perdida por bug del bot.
        
        Auto-detecta todo desde la BD:
        - best_streak → racha que tenía antes de perderla
        - Analiza historial de poles desde su ÚLTIMO POLE hacia atrás
        - Calcula días perdidos y puntos de compensación
        """
        if not interaction.guild:
            await interaction.response.send_message("❌ Solo en servidores.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            target_guild_id = int(guild_id) if guild_id else interaction.guild.id
            
            # 1. Obtener datos globales del usuario
            global_user = self.db.get_or_create_global_user(usuario.id, usuario.name)
            current_streak = global_user['current_streak'] if global_user else 0
            best_streak = global_user['best_streak'] if global_user else 0
            
            if best_streak <= current_streak:
                await interaction.followup.send(
                    f"❌ {usuario.mention} no parece necesitar restauración.\n"
                    f"Racha actual: **{current_streak}** | Mejor racha: **{best_streak}**\n"
                    f"La racha actual ya es >= que la mejor registrada.",
                    ephemeral=True
                )
                return
            
            # 2. Obtener historial de fechas de poles (ordenadas DESC)
            pole_dates = self.db.get_user_pole_dates_global(usuario.id, limit=120)
            pole_dates_set = set(pole_dates)
            
            if not pole_dates:
                await interaction.followup.send(
                    f"❌ {usuario.mention} no tiene historial de poles.",
                    ephemeral=True
                )
                return
            
            # 3. Anclar en el ÚLTIMO POLE del usuario, no en hoy
            last_pole_str = pole_dates[0]  # Más reciente (DESC)
            last_pole_obj = datetime.strptime(last_pole_str, '%Y-%m-%d').date()
            
            # Contar poles consecutivos desde el último pole hacia atrás (post-gap)
            d = last_pole_obj
            post_gap_run = 0
            while d.isoformat() in pole_dates_set:
                post_gap_run += 1
                d -= timedelta(days=1)
            
            # d ahora es el día más reciente del gap
            gap_days = 0
            gap_dates: list[str] = []
            while d.isoformat() not in pole_dates_set and gap_days < 30:
                gap_dates.append(d.isoformat())
                gap_days += 1
                d -= timedelta(days=1)
            
            if gap_days == 0:
                await interaction.followup.send(
                    f"❌ No se encontró ningún hueco en el historial de {usuario.mention}.\n"
                    f"Tiene poles consecutivos hasta su último registro. La racha no parece rota.",
                    ephemeral=True
                )
                return
            
            # Contar racha antigua (verificación)
            old_streak_run = 0
            while d.isoformat() in pole_dates_set:
                old_streak_run += 1
                d -= timedelta(days=1)
            
            racha_original = best_streak
            nueva_racha = racha_original + gap_days + post_gap_run
            
            # 4. Compensación: días del gap (no polearon)
            total_comp_points = 0.0
            day_details = []
            for i, gap_date in enumerate(gap_dates):
                simulated_streak = racha_original + (i + 1)
                base_pts, multiplier, day_pts = calculate_points('normal', simulated_streak)
                total_comp_points += day_pts
                day_details.append(
                    f"`{gap_date}`: racha {simulated_streak} → {base_pts:.0f} × {multiplier:.1f} = **{day_pts:.1f}** pts"
                )
            
            # 5. Compensación: diferencia de multiplicador post-gap
            diff_comp_points = 0.0
            diff_details = []
            for day_offset in range(post_gap_run):
                post_date = (last_pole_obj - timedelta(days=post_gap_run - 1 - day_offset)).isoformat()
                streak_they_had = day_offset + 1
                streak_should_have = racha_original + gap_days + day_offset + 1
                _, _, pts_got = calculate_points('normal', streak_they_had)
                _, _, pts_should = calculate_points('normal', streak_should_have)
                diff = pts_should - pts_got
                if diff > 0:
                    diff_comp_points += diff
                    diff_details.append(
                        f"`{post_date}`: racha {streak_they_had}→{streak_should_have} | diff **+{diff:.1f}** pts"
                    )
            
            total_compensation = total_comp_points + diff_comp_points
            
            # ========== EMBED ==========
            embed = discord.Embed(
                title="🔧 Restaurar Racha" + (" (SIMULACIÓN)" if dry_run else ""),
                color=discord.Color.orange() if dry_run else discord.Color.green(),
                timestamp=datetime.now()
            )
            
            embed.add_field(name="👤 Usuario", value=f"{usuario.mention} ({usuario.name})", inline=True)
            embed.add_field(name="📊 Racha actual → nueva", value=f"{current_streak} → **{nueva_racha}** días", inline=True)
            embed.add_field(name="🏆 Mejor racha", value=f"{best_streak} → **{max(best_streak, nueva_racha)}**", inline=True)
            
            detection_text = (
                f"🔍 **Racha original (best_streak):** {racha_original}\n"
                f"📅 **Último pole:** {last_pole_str}\n"
                f"💔 **Gap:** {gap_days}d ({', '.join(gap_dates[:5])})\n"
                f"📈 **Post-gap (poleados con racha rota):** {post_gap_run}d\n"
                f"🔢 **Cálculo:** {racha_original} + {gap_days} + {post_gap_run} = **{nueva_racha}**\n"
                f"📅 **Racha antigua verificada:** {old_streak_run}d antes del gap"
            )
            embed.add_field(name="🔎 Auto-detección", value=detection_text, inline=False)
            
            if day_details:
                details_text = "\n".join(day_details[:8])
                if len(day_details) > 8:
                    details_text += f"\n... y {len(day_details) - 8} días más"
                embed.add_field(name=f"💰 Compensación gap ({gap_days}d): **{total_comp_points:.1f}** pts", value=details_text, inline=False)
            
            if diff_details:
                diff_text = "\n".join(diff_details[:8])
                if len(diff_details) > 8:
                    diff_text += f"\n... y {len(diff_details) - 8} días más"
                embed.add_field(name=f"📊 Compensación multiplicador ({post_gap_run}d): **{diff_comp_points:.1f}** pts", value=diff_text, inline=False)
            
            embed.add_field(name="💎 TOTAL COMPENSACIÓN", value=f"**{total_compensation:.1f}** pts → guild {target_guild_id}", inline=False)
            
            if dry_run:
                embed.set_footer(text="⚠️ SIMULACIÓN - Usa dry_run:False para aplicar los cambios")
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # ========== APLICAR ==========
            new_best = max(best_streak, nueva_racha)
            self.db.update_global_user(
                usuario.id,
                current_streak=nueva_racha,
                best_streak=new_best,
                last_pole_date=last_pole_str,  # Fecha REAL del último pole, no hoy
                username=usuario.name
            )
            
            current_season = get_current_season()
            season_stats = self.db.get_season_stats(usuario.id, target_guild_id, current_season)
            if season_stats:
                self.db.update_season_stats(
                    usuario.id, target_guild_id, current_season,
                    season_points=season_stats['season_points'] + total_compensation,
                    season_best_streak=max(season_stats['season_best_streak'], nueva_racha)
                )
            else:
                self.db.update_season_stats(
                    usuario.id, target_guild_id, current_season,
                    season_points=total_compensation, season_poles=0,
                    season_critical=0, season_fast=0, season_normal=0, season_marranero=0,
                    season_best_streak=nueva_racha
                )
            
            log.info(
                f"🔧 [Restore] {usuario.name} (ID:{usuario.id}): "
                f"racha {current_streak} → {nueva_racha} (best:{racha_original} + gap:{gap_days} + post:{post_gap_run}), "
                f"compensación +{total_compensation:.1f} pts, last_pole={last_pole_str}"
            )
            embed.set_footer(text=f"✅ Cambios aplicados por {interaction.user.name}")
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            log.error(f"❌ Error en restore_streak: {e}")
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)

    # ==================== RESTAURAR GUILD COMPLETO ====================

    @debug.command(name="restore_guild", description="🔧 Restaurar rachas de TODOS los afectados en un guild por fecha")
    @app_commands.describe(
        fecha="Fecha del bug (YYYY-MM-DD) - día en que se perdieron las rachas",
        guild_id="Guild ID (default: este servidor)",
        dry_run="Solo simular, no aplicar cambios"
    )
    @debug_only()
    async def restore_guild(
        self,
        interaction: discord.Interaction,
        fecha: str,
        guild_id: Optional[str] = None,
        dry_run: bool = True
    ):
        """
        Restaurar rachas de TODOS los usuarios afectados en un guild.
        
        Detección robusta por historial de poles:
        1. Para cada usuario con best_streak > current_streak
        2. Ancla en su ÚLTIMO POLE, camina hacia atrás para encontrar el gap
        3. Verifica que el gap está cerca de la fecha indicada (±1 día)
        4. Calcula compensación automática
        """
        if not interaction.guild:
            await interaction.response.send_message("❌ Solo en servidores.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            try:
                bug_date = datetime.strptime(fecha, '%Y-%m-%d').date()
            except ValueError:
                await interaction.followup.send("❌ Formato de fecha inválido. Usa YYYY-MM-DD", ephemeral=True)
                return
            
            target_guild_id = int(guild_id) if guild_id else interaction.guild.id
            today = datetime.now().date()
            
            if bug_date >= today:
                await interaction.followup.send("❌ La fecha debe ser anterior a hoy.", ephemeral=True)
                return
            
            # Rango de tolerancia: la fecha del bug ±1 día
            # (por cross-midnight, el gap puede estar en fecha o fecha+1)
            tolerance_dates = {
                (bug_date - timedelta(days=1)).isoformat(),
                bug_date.isoformat(),
                (bug_date + timedelta(days=1)).isoformat(),
            }
            
            # 1. Obtener usuarios activos del guild
            active_user_ids = self.db.get_guild_active_user_ids(target_guild_id)
            if not active_user_ids:
                await interaction.followup.send(f"❌ No hay usuarios activos en guild {target_guild_id}", ephemeral=True)
                return
            
            affected_users = []
            skipped_users = []
            
            for uid in active_user_ids:
                global_user = self.db.get_global_user(uid)
                if not global_user:
                    continue
                
                best = global_user['best_streak'] or 0
                current = global_user['current_streak'] or 0
                username = global_user.get('username', f'ID:{uid}')
                
                # Filtro 1: racha actual >= best → no necesita restauración
                if current >= best:
                    continue
                
                pole_dates = self.db.get_user_pole_dates_global(uid, limit=120)
                pole_dates_set = set(pole_dates)
                
                if not pole_dates:
                    continue
                
                # ===== ANCLAR EN ÚLTIMO POLE, caminar hacia atrás =====
                last_pole_str = pole_dates[0]  # Más reciente (DESC)
                last_pole_obj = datetime.strptime(last_pole_str, '%Y-%m-%d').date()
                
                # Contar post-gap: poles consecutivos desde el último hacia atrás
                d = last_pole_obj
                post_gap_run = 0
                while d.isoformat() in pole_dates_set:
                    post_gap_run += 1
                    d -= timedelta(days=1)
                
                # d ahora es el día más reciente del gap
                gap_days = 0
                gap_dates_list: list[str] = []
                while d.isoformat() not in pole_dates_set and gap_days < 30:
                    gap_dates_list.append(d.isoformat())
                    gap_days += 1
                    d -= timedelta(days=1)
                
                if gap_days == 0:
                    skipped_users.append(f"{username}: sin gap detectado")
                    continue
                
                # Verificar racha pre-gap (cuántos días consecutivos antes del gap)
                old_streak_run = 0
                while d.isoformat() in pole_dates_set:
                    old_streak_run += 1
                    d -= timedelta(days=1)
                
                # Filtro 2: el gap debe estar CERCA de la fecha del bug (±1 día)
                gap_overlaps = any(gd in tolerance_dates for gd in gap_dates_list)
                if not gap_overlaps:
                    skipped_users.append(f"{username}: gap en {gap_dates_list[0]} no coincide con {fecha}")
                    continue
                
                # Filtro 3: debe tener racha significativa pre-gap (al menos 3 días)
                # Esto descarta usuarios que perdieron racha por inactividad normal
                if old_streak_run < 3 and best < 5:
                    skipped_users.append(f"{username}: racha pre-gap muy corta ({old_streak_run}d)")
                    continue
                
                racha_original = best
                nueva_racha = racha_original + gap_days + post_gap_run
                
                # Compensación: días del gap (no polearon)
                total_comp_points = 0.0
                for i in range(gap_days):
                    simulated_streak = racha_original + (i + 1)
                    _, _, day_pts = calculate_points('normal', simulated_streak)
                    total_comp_points += day_pts
                
                # Compensación: diferencia multiplicador post-gap
                diff_comp_points = 0.0
                for day_offset in range(post_gap_run):
                    streak_they_had = day_offset + 1
                    streak_should_have = racha_original + gap_days + day_offset + 1
                    _, _, pts_got = calculate_points('normal', streak_they_had)
                    _, _, pts_should = calculate_points('normal', streak_should_have)
                    diff = pts_should - pts_got
                    if diff > 0:
                        diff_comp_points += diff
                
                total_compensation = total_comp_points + diff_comp_points
                
                affected_users.append({
                    'user_id': uid,
                    'username': username,
                    'current_streak': current,
                    'best_streak': best,
                    'racha_original': racha_original,
                    'gap_days': gap_days,
                    'gap_dates': gap_dates_list,
                    'post_gap_run': post_gap_run,
                    'old_streak_run': old_streak_run,
                    'nueva_racha': nueva_racha,
                    'actual_last_pole': last_pole_str,
                    'comp_gap': total_comp_points,
                    'comp_diff': diff_comp_points,
                    'comp_total': total_compensation,
                })
            
            if not affected_users:
                msg = f"✅ No se encontraron usuarios afectados en guild {target_guild_id} para {fecha}."
                if skipped_users:
                    msg += f"\n\n📋 **Descartados ({len(skipped_users)}):**\n" + "\n".join(skipped_users[:15])
                await interaction.followup.send(msg, ephemeral=True)
                return
            
            # Construir embed
            embed = discord.Embed(
                title=f"🔧 Restaurar Guild {'(SIMULACIÓN)' if dry_run else ''}",
                description=(
                    f"**Fecha del bug:** {fecha} (tolerancia ±1 día)\n"
                    f"**Guild:** {target_guild_id}\n"
                    f"**Usuarios afectados:** {len(affected_users)}\n"
                    f"**Descartados:** {len(skipped_users)}"
                ),
                color=discord.Color.orange() if dry_run else discord.Color.green(),
                timestamp=datetime.now()
            )
            
            total_points_all = 0.0
            user_lines = []
            for u in affected_users:
                total_points_all += u['comp_total']
                gap_str = f"{u['gap_days']}d gap ({', '.join(u['gap_dates'][:3])})"
                post_str = f"+{u['post_gap_run']}d post" if u['post_gap_run'] > 0 else ""
                pre_str = f"pre:{u['old_streak_run']}d"
                user_lines.append(
                    f"**{u['username']}**: {u['current_streak']}→**{u['nueva_racha']}** "
                    f"({pre_str}, {gap_str}{', ' + post_str if post_str else ''}) "
                    f"+**{u['comp_total']:.1f}**pts"
                )
            
            users_text = "\n".join(user_lines)
            if len(users_text) <= 1024:
                embed.add_field(name=f"👥 Usuarios a restaurar ({len(affected_users)})", value=users_text, inline=False)
            else:
                chunk = ""
                chunk_num = 1
                for line in user_lines:
                    if len(chunk) + len(line) + 1 > 1000:
                        embed.add_field(name=f"👥 Usuarios ({chunk_num})", value=chunk, inline=False)
                        chunk = line
                        chunk_num += 1
                    else:
                        chunk = chunk + "\n" + line if chunk else line
                if chunk:
                    embed.add_field(name=f"👥 Usuarios ({chunk_num})", value=chunk, inline=False)
            
            embed.add_field(
                name="💎 TOTAL COMPENSACIÓN",
                value=f"**{total_points_all:.1f}** pts entre {len(affected_users)} usuarios",
                inline=False
            )
            
            if skipped_users:
                skip_text = "\n".join(skipped_users[:10])
                if len(skipped_users) > 10:
                    skip_text += f"\n... y {len(skipped_users) - 10} más"
                embed.add_field(name=f"⏭️ Descartados ({len(skipped_users)})", value=skip_text, inline=False)
            
            if dry_run:
                embed.set_footer(text="⚠️ SIMULACIÓN - Usa dry_run:False para aplicar")
                await interaction.followup.send(embed=embed, ephemeral=True)
                return
            
            # ========== APLICAR CAMBIOS ==========
            current_season = get_current_season()
            applied_count = 0
            
            for u in affected_users:
                uid = u['user_id']
                nueva_racha = u['nueva_racha']
                new_best = max(u['best_streak'], nueva_racha)
                
                self.db.update_global_user(
                    uid,
                    current_streak=nueva_racha,
                    best_streak=new_best,
                    last_pole_date=u['actual_last_pole'],  # Fecha REAL, no hoy
                    username=u['username']
                )
                
                season_stats = self.db.get_season_stats(uid, target_guild_id, current_season)
                if season_stats:
                    self.db.update_season_stats(
                        uid, target_guild_id, current_season,
                        season_points=season_stats['season_points'] + u['comp_total'],
                        season_best_streak=max(season_stats['season_best_streak'], nueva_racha)
                    )
                else:
                    self.db.update_season_stats(
                        uid, target_guild_id, current_season,
                        season_points=u['comp_total'], season_poles=0,
                        season_critical=0, season_fast=0, season_normal=0, season_marranero=0,
                        season_best_streak=nueva_racha
                    )
                
                applied_count += 1
                log.info(
                    f"🔧 [RestoreGuild] {u['username']} (ID:{uid}): "
                    f"racha {u['current_streak']}→{nueva_racha}, "
                    f"+{u['comp_total']:.1f}pts, last_pole={u['actual_last_pole']}"
                )
            
            embed.set_footer(text=f"✅ {applied_count}/{len(affected_users)} restaurados por {interaction.user.name}")
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            log.error(f"❌ Error en restore_guild: {e}")
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(DebugCog(bot))
