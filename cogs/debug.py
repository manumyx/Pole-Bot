"""
Cog de Depuración v1.0
Permite simular poles con retraso, forzar hora de apertura, cambiar representación, etc.
Se carga solo si la variable de entorno DEBUG=1.
"""
import os
import asyncio
from datetime import datetime, timedelta
from typing import Optional

import discord
from discord.ext import commands
from discord import app_commands

from utils.database import Database
from utils.scoring import (
    calculate_points, classify_delay, get_pole_emoji, get_pole_name,
    update_streak, get_rank_info,
    RANK_THRESHOLDS, RANK_BADGES, RANK_NAMES
)

# Emoji de fuego personalizado (usar en todo el bot)
FIRE = "<a:fire:1440018375144374302>"


def _is_allowed_user(interaction: discord.Interaction) -> bool:
    """Restringe el uso del debug a owner/administradores o allowlist."""
    if interaction.user is None:
        return False
    # Allowlist por IDs (separado por comas) en DEBUG_ALLOWLIST
    allow = os.getenv('DEBUG_ALLOWLIST', '')
    if allow:
        try:
            ids = {int(x.strip()) for x in allow.split(',') if x.strip()}
        except Exception:
            ids = set()
        if interaction.user.id in ids:
            return True
    # Si no hay allowlist, permitir a administradores y propietarios del servidor
    if interaction.guild and isinstance(interaction.user, discord.Member):
        perms = interaction.user.guild_permissions
        if perms.administrator or interaction.user.id == interaction.guild.owner_id:
            return True
    return False


def debug_only():
    """Check decorator para comandos de debug."""
    async def predicate(interaction: discord.Interaction) -> bool:
        if os.getenv('DEBUG', '0') not in ('1', 'true', 'True'):
            await interaction.response.send_message(
                "❌ Debug desactivado. Pon DEBUG=1 en .env para usar estos comandos.",
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

    debug = app_commands.Group(name="debug", description="Herramientas de depuración v1.0")

    # ====== MOSTRAR BADGES/RANGOS ======
    @debug.command(name="badges", description="Muestra los rangos, badges y umbrales actuales")
    @debug_only()
    async def show_badges(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="🎖️ Rangos y Umbrales (DEBUG)",
            color=discord.Color.purple(),
            timestamp=datetime.now()
        )

        order = [
            ('ruby', 'Rubí'),
            ('amethyst', 'Amatista'),
            ('diamond', 'Diamante'),
            ('gold', 'Oro'),
            ('silver', 'Plata'),
            ('bronze', 'Bronce'),
        ]

        lines = []
        for key, label in order:
            badge = RANK_BADGES[key]
            thr = RANK_THRESHOLDS[key]
            name = RANK_NAMES[key]
            lines.append(f"{badge} **{label}** — {name} • ≥ {thr} pts")

        embed.description = "\n".join(lines)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ====== DAR PUNTOS MANUALMENTE ======
    @debug.command(name="add_points", description="Añadir puntos manualmente (lifetime o temporada)")
    @app_commands.describe(
        puntos="Cantidad de puntos a añadir (puede ser decimal)",
        alcance="Dónde sumar: lifetime (histórico) o season (temporada actual)",
        usuario="Usuario objetivo (por defecto tú)"
    )
    @app_commands.choices(
        alcance=[
            app_commands.Choice(name="Lifetime (Histórico)", value="lifetime"),
            app_commands.Choice(name="Season (Temporada Actual)", value="season"),
            app_commands.Choice(name="Ambos (Lifetime + Season)", value="both"),
        ]
    )
    @debug_only()
    async def add_points(self, interaction: discord.Interaction, puntos: float, alcance: str = "lifetime", usuario: Optional[discord.Member] = None):
        if interaction.guild is None:
            await interaction.response.send_message("❌ Solo en servidores.", ephemeral=True)
            return
        
        target = usuario or interaction.user
        gid = interaction.guild.id
        
        # Asegurar usuario existe en DB (PRODUCCIÓN)
        user_data = self.db.get_user(target.id, gid)
        if not user_data:
            self.db.create_user(target.id, gid, target.name)
            user_data = self.db.get_user(target.id, gid) or {}
            print(f"[DEBUG] Usuario {target.name} ({target.id}) creado en PRODUCCIÓN")
        
        summary_lines = []
        
        # Lifetime (calculado desde season_stats - NO se actualiza directamente)
        # NOTA: total_points se calcula dinámicamente, solo actualizamos season_stats
        if alcance in ("lifetime", "both"):
            old_total = float(user_data.get("total_points", 0.0))
            new_total = old_total + float(puntos)
            # No actualizar tabla users - totales se calculan automáticamente
            print(f"[DEBUG] Lifetime (calculado): {old_total:.1f} → {new_total:.1f} (vía season_stats)")
            summary_lines.append(f"🏆 Lifetime: +{puntos:.1f} → {new_total:.1f} pts (calculado)")
        
        # Season (tabla season_stats en PRODUCCIÓN)
        if alcance in ("season", "both"):
            from utils.scoring import get_current_season
            season_id = get_current_season()
            season_stats = self.db.get_season_stats(target.id, gid, season_id)
            old_season = float(season_stats.get("season_points", 0.0)) if season_stats else 0.0
            new_season_total = old_season + float(puntos)
            self.db.update_season_stats(target.id, gid, season_id, season_points=new_season_total)
            print(f"[DEBUG] Season ({season_id}) actualizada en PRODUCCIÓN: {old_season:.1f} → {new_season_total:.1f}")
            summary_lines.append(f"🎮 Season ({season_id}): +{puntos:.1f} → {new_season_total:.1f} pts")
        
        # Responder
        embed = discord.Embed(
            title="🛠️ Puntos Ajustados (DEBUG)",
            description=f"{target.mention}\n" + "\n".join(summary_lines),
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ====== FORZAR HORA DE APERTURA ======
    @debug.command(name="set_opening", description="Forzar hora de apertura del pole para hoy")
    @app_commands.describe(
        hora="Hora (0-23)",
        minuto="Minuto (0-59, opcional)"
    )
    @debug_only()
    async def set_opening(self, interaction: discord.Interaction, hora: app_commands.Range[int, 0, 23], minuto: int = 0):
        if interaction.guild is None:
            await interaction.response.send_message("❌ Solo en servidores.", ephemeral=True)
            return
        
        if minuto < 0 or minuto > 59:
            await interaction.response.send_message("❌ Minuto debe estar entre 0 y 59.", ephemeral=True)
            return
        
        time_str = f"{hora:02d}:{minuto:02d}:00"
        self.db.set_daily_pole_time(interaction.guild.id, time_str)
        
        # Reprogramar notificación exacta para hoy
        try:
            pole_cog = self.bot.get_cog('PoleCog')
            schedule_fn = getattr(pole_cog, 'schedule_all_today_notifications', None) if pole_cog else None
            if callable(schedule_fn):
                result = schedule_fn()
                if asyncio.iscoroutine(result):
                    asyncio.create_task(result)
        except Exception as e:
            print(f"⚠️ No se pudo reprogramar notificación tras set_opening: {e}")
        
        await interaction.response.send_message(
            f"✅ Hora de apertura de hoy configurada a **{time_str}** (DEBUG).",
            ephemeral=True
        )

    # ====== SIMULAR POLE CON RETRASO ======
    @debug.command(name="simulate_pole", description="Simula un pole con retraso específico (en minutos)")
    @app_commands.describe(
        delay_minutos="Retraso desde apertura en minutos (0-2000)",
        usuario="Usuario objetivo (opcional, por defecto tú)"
    )
    @debug_only()
    async def simulate_pole(self, interaction: discord.Interaction, delay_minutos: int, usuario: Optional[discord.Member] = None):
        if interaction.guild is None:
            await interaction.response.send_message("❌ Solo en servidores.", ephemeral=True)
            return
        
        target = usuario or interaction.user
        gid = interaction.guild.id
        
        # Verificar que hay hora de apertura configurada
        opening_str = self.db.get_daily_pole_time(gid)
        if not opening_str:
            await interaction.response.send_message(
                "❌ No hay hora de apertura configurada. Usa `/debug set_opening` primero.",
                ephemeral=True
            )
            return
        
        # Construir opening_time de hoy
        now = datetime.now()
        h, m, s = [int(x) for x in opening_str.split(':')]
        opening_time = datetime(now.year, now.month, now.day, h, m, s)
        user_time = opening_time + timedelta(minutes=delay_minutos)
        
        # Detectar si es día siguiente (simular que pasó 00:00)
        is_next_day = user_time.date() > opening_time.date()
        
        # Clasificar por delay
        pole_type = classify_delay(delay_minutos, is_next_day)
        
        # Obtener o crear usuario (ESCRIBE EN PRODUCCIÓN)
        user_data = self.db.get_user(target.id, gid)
        if not user_data:
            self.db.create_user(target.id, gid, target.name)
            user_data = self.db.get_user(target.id, gid) or {}
        
        # Calcular racha
        current_streak = int(user_data.get("current_streak", 0))
        last_pole_date = user_data.get("last_pole_date")
        new_streak, streak_broken = update_streak(last_pole_date, current_streak)
        
        # Calcular puntos
        base, mult, total = calculate_points(pole_type, new_streak)
        
        # Guardar pole en producción
        self.db.save_pole(
            user_id=target.id,
            guild_id=gid,
            opening_time=opening_time,
            user_time=user_time,
            delay_minutes=delay_minutos,
            pole_type=pole_type,
            points_earned=total,
            streak=new_streak
        )
        
        # Actualizar usuario en producción (sin total_points/total_poles - calculados desde seasons)
        fields = {
            "current_streak": new_streak,
            "best_streak": max(int(user_data.get("best_streak", 0)), new_streak),
            "last_pole_date": now.strftime('%Y-%m-%d'),
            "username": target.name,
        }
        
        # Actualizar contadores por categoría
        if pole_type == "critical":
            fields["critical_poles"] = int(user_data.get("critical_poles", 0)) + 1
        elif pole_type == "fast":
            fields["fast_poles"] = int(user_data.get("fast_poles", 0)) + 1
        elif pole_type == "normal":
            fields["normal_poles"] = int(user_data.get("normal_poles", 0)) + 1
        elif pole_type == "marranero":
            fields["marranero_poles"] = int(user_data.get("marranero_poles", 0)) + 1
        
        # Actualizar métricas de velocidad
        prev_avg = float(user_data.get("average_delay_minutes") or 0)
        prev_count = int(user_data.get("total_poles") or 0)
        new_avg = ((prev_avg * prev_count) + delay_minutos) / (prev_count + 1)
        fields["average_delay_minutes"] = new_avg
        best_time = user_data.get("best_time_minutes")
        if best_time is None or delay_minutos < int(best_time):
            fields["best_time_minutes"] = delay_minutos
        
        self.db.update_user(target.id, gid, **fields)
        
        # Respuesta con embed tipo victoria
        emoji = get_pole_emoji(pole_type)
        name = get_pole_name(pole_type)
        color_map = {
            'critical': discord.Color.gold(),
            'fast': discord.Color.from_rgb(192, 192, 192),
            'normal': discord.Color.green(),
            'late': discord.Color.orange(),
            'marranero': discord.Color.from_rgb(205, 133, 63)
        }
        
        embed = discord.Embed(
            title=f"{emoji} {name} {emoji}",
            color=color_map.get(pole_type, discord.Color.blue()),
            timestamp=user_time
        )
        embed.description = f"(DEBUG) {target.mention} simulado"
        embed.add_field(name="⏱️ Hora", value=user_time.strftime('%H:%M:%S'), inline=True)
        embed.add_field(name="⏳ Retraso", value=f"{delay_minutos} min", inline=True)
        embed.add_field(name="📍 Posición", value="Simulado", inline=True)
        embed.add_field(name="💰 Puntos Base", value=f"{base:.1f} pts", inline=True)
        if new_streak > 1:
            embed.add_field(name=f"{FIRE} Racha x{mult:.1f}", value=f"{new_streak} días", inline=True)
        else:
            embed.add_field(name=f"{FIRE} Racha", value="1 día", inline=True)
        embed.add_field(name="🎯 Total Ganado", value=f"**{total:.1f} pts**", inline=True)
        embed.set_footer(text="✅ Datos guardados en producción (DEBUG activo)")
        
        await interaction.response.send_message(embed=embed)

    # ====== [DEPRECATED] Comandos represent y config eliminados ======



    # ====== RESETEAR FECHA DE ÚLTIMO POLE ======
    @debug.command(name="reset_date", description="Resetea last_pole_date y elimina poles de hoy (TESTING)")
    @debug_only()
    async def reset_date(
        self,
        interaction: discord.Interaction,
        usuario: Optional[discord.Member] = None
    ):
        """Resetea last_pole_date y elimina poles de hoy para permitir múltiples poles"""
        if not interaction.guild:
            await interaction.response.send_message("❌ Solo en servidores.", ephemeral=True)
            return
        
        target = usuario or interaction.user
        gid = interaction.guild.id
        
        # Resetear last_pole_date a None
        self.db.update_user(target.id, gid, last_pole_date=None)
        
        # Eliminar poles de hoy del usuario en este servidor
        today = datetime.now().strftime('%Y-%m-%d')
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM poles 
                WHERE user_id = ? AND guild_id = ? 
                AND DATE(created_at) = ?
            ''', (target.id, gid, today))
            deleted_count = cursor.rowcount
            conn.commit()
        
        await interaction.response.send_message(
            f"✅ Reseteado para {target.mention}\n"
            f"• `last_pole_date` → None\n"
            f"• Poles eliminados hoy: {deleted_count}\n"
            f"💡 Ahora puedes hacer `/debug open_now` y volver a polear.",
            ephemeral=True
        )

    # ====== ABRIR POLE INSTANTÁNEAMENTE ======
    @debug.command(name="open_now", description="Abre el pole AHORA mismo (sin esperar hora configurada)")
    @debug_only()
    async def open_now(self, interaction: discord.Interaction):
        if not interaction.guild:
            await interaction.response.send_message("❌ Solo en servidores.", ephemeral=True)
            return
        
        gid = interaction.guild.id
        
        # Establecer hora actual como hora de apertura
        now = datetime.now()
        time_str = now.strftime("%H:%M:%S")
        self.db.set_daily_pole_time(gid, time_str)
        
        # Obtener configuración del servidor
        cfg = self.db.get_server_config(gid)
        if not cfg or not cfg.get('pole_channel_id'):
            await interaction.response.send_message(
                "❌ Debes configurar el canal de pole primero con `/settings`.",
                ephemeral=True
            )
            return
        
        # Enviar notificación de apertura si está habilitado
        if cfg.get('notify_opening', 1):
            pole_cog = self.bot.get_cog('PoleCog')
            send_fn = getattr(pole_cog, 'send_opening_notification', None) if pole_cog else None
            if callable(send_fn):
                try:
                    if asyncio.iscoroutinefunction(send_fn):
                        await send_fn(
                            gid,
                            cfg['pole_channel_id'],
                            cfg.get('ping_role_id'),
                            cfg.get('ping_mode', 'none')
                        )
                    else:
                        send_fn(
                            gid,
                            cfg['pole_channel_id'],
                            cfg.get('ping_role_id'),
                            cfg.get('ping_mode', 'none')
                        )
                except Exception as e:
                    print(f"⚠️ Error enviando notificación de apertura (DEBUG): {e}")
        
        await interaction.response.send_message(
            f"✅ ¡Pole abierto AHORA! ({time_str})\n"
            f"💬 Escribe **pole** en <#{cfg['pole_channel_id']}> para probarlo.",
            ephemeral=True
        )


async def setup(bot: commands.Bot):
    await bot.add_cog(DebugCog(bot))
