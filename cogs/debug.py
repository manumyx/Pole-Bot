"""
Cog de Depuración v2.0 - REFACTORIZADO
Comandos de debug unificados y optimizados.
Se carga solo si DEBUG=1 en .env
"""
import os
import asyncio
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
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = Database()

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
                        print(f"⚠️ Error enviando notificación: {e}")
            
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
                print(f"⚠️ Error reprogramando: {e}")
            
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
            
            old_streak = user_data.get('current_streak', 0)
            old_best = user_data.get('best_streak', 0)
            new_best = max(old_best, racha)
            
            self.db.update_user(usuario.id, gid, current_streak=racha, best_streak=new_best)
            
            embed.add_field(name="🔥 Racha", value=f"{old_streak} → **{racha}**", inline=True)
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
            old_streak = user_data.get('current_streak', 0)
            best_streak = user_data.get('best_streak', 0)
            
            if best_streak == 0:
                await interaction.response.send_message(
                    f"❌ {usuario.mention} no tiene mejor racha registrada.",
                    ephemeral=True
                )
                return
            
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            self.db.update_user(usuario.id, gid, current_streak=best_streak, last_pole_date=yesterday)
            
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


async def setup(bot: commands.Bot):
    await bot.add_cog(DebugCog(bot))
