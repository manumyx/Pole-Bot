"""
Cog de Depuración v1.0
Permite simular poles con retraso, forzar hora de apertura, cambiar representación, etc.
Se carga solo si la variable de entorno DEBUG=1.
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

    # ====== INFORMACIÓN DEL SERVIDOR ======
    @debug.command(name="info", description="Muestra información del servidor (config, hora, poles, etc)")
    @debug_only()
    async def server_info(self, interaction: discord.Interaction):
        """Muestra configuración completa del servidor para debugging"""
        if interaction.guild is None:
            await interaction.response.send_message("❌ Solo en servidores.", ephemeral=True)
            return
        
        gid = interaction.guild.id
        config = self.db.get_server_config(gid) or {}
        
        # Información básica
        embed = discord.Embed(
            title=f"🔧 Información del Servidor",
            description=f"**{interaction.guild.name}**\nGuild ID: `{gid}`",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Canal y notificaciones
        channel_id = config.get('pole_channel_id')
        channel_str = f"<#{channel_id}>" if channel_id else "❌ No configurado"
        embed.add_field(name="📺 Canal pole", value=channel_str, inline=False)
        
        # Hora de apertura
        daily_time = config.get('daily_pole_time')
        last_daily_time = config.get('last_daily_pole_time')
        time_str = f"**{daily_time}**" if daily_time else "❌ No configurada"
        if last_daily_time:
            time_str += f"\n🕐 Anterior: {last_daily_time}"
        embed.add_field(name="⏰ Hora de apertura HOY", value=time_str, inline=True)
        
        # Calcular tiempo hasta apertura
        if daily_time:
            try:
                now = datetime.now()
                h, m, s = [int(x) for x in daily_time.split(':')]
                opening = datetime(now.year, now.month, now.day, h, m, s)
                
                if now < opening:
                    delta = opening - now
                    hours = int(delta.total_seconds() // 3600)
                    minutes = int((delta.total_seconds() % 3600) // 60)
                    time_left = f"⏳ Faltan {hours}h {minutes}m"
                else:
                    delta = now - opening
                    hours = int(delta.total_seconds() // 3600)
                    minutes = int((delta.total_seconds() % 3600) // 60)
                    time_left = f"✅ Abierto hace {hours}h {minutes}m"
                embed.add_field(name="⏱️ Estado", value=time_left, inline=True)
            except:
                pass
        
        # Rol de ping
        role_id = config.get('ping_role_id')
        role_str = f"<@&{role_id}>" if role_id else "❌ No configurado"
        ping_mode = config.get('ping_mode', 'none')
        embed.add_field(name="🔔 Rol de Ping", value=f"{role_str}\nModo: {ping_mode}", inline=True)
        
        # Notificaciones
        notify_opening = "✅ Activo" if config.get('notify_opening', 1) else "❌ Desactivado"
        notify_winner = "✅ Activo" if config.get('notify_winner', 1) else "❌ Desactivado"
        embed.add_field(name="📢 Notif. Apertura", value=notify_opening, inline=True)
        embed.add_field(name="🏆 Notif. Ganador", value=notify_winner, inline=True)
        
        # Estadísticas del día
        today_poles = self.db.get_poles_today(gid)
        total_members = sum(1 for m in interaction.guild.members if not m.bot)
        embed.add_field(
            name="📊 Poles hoy",
            value=f"**{len(today_poles)}** poles\n👥 {total_members} miembros (sin bots)",
            inline=True
        )
        
        # Última actualización de schema
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT version, description, applied_at FROM schema_metadata ORDER BY version DESC LIMIT 1')
                schema_row = cursor.fetchone()
                if schema_row:
                    schema_info = f"v{schema_row['version']} - {schema_row['description']}"
                else:
                    schema_info = "No disponible"
        except:
            schema_info = "Error al obtener"
        
        embed.set_footer(text=f"Schema DB: {schema_info}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @debug.command(name="diagnose_user", description="Diagnosticar por qué un usuario no puede hacer pole hoy")
    @app_commands.describe(usuario="Usuario a diagnosticar")
    @debug_only()
    async def diagnose_user(self, interaction: discord.Interaction, usuario: Optional[discord.Member] = None):
        if not interaction.guild:
            await interaction.response.send_message("❌ Solo en servidores.", ephemeral=True)
            return
        target = usuario or interaction.user
        gid = interaction.guild.id
        report = []
        try:
            server_config = self.db.get_server_config(gid) or {}
            pole_channel_id = server_config.get('pole_channel_id')
            daily_time = server_config.get('daily_pole_time')
            migration = server_config.get('migration_in_progress', 0)
            report.append(f"Canal pole: {pole_channel_id}")
            report.append(f"Hora diaria: {daily_time}")
            report.append(f"Migración: {migration}")

            # Poles de hoy en este servidor
            today_poles = self.db.get_poles_today(gid)
            user_pole_today = any(p['user_id'] == target.id for p in today_poles)
            report.append(f"Pole hoy en este server: {user_pole_today}")

            # Pole global hoy
            global_pole = self.db.get_user_pole_today_global(target.id)
            report.append(f"Pole global hoy: {bool(global_pole)} en guild {global_pole['guild_id'] if global_pole else 'N/A'}")

            # Cuotas estimadas según hora actual
            from utils.scoring import check_quota_available, classify_delay
            import datetime as _dt
            now = _dt.datetime.now()
            quota_info = "N/A"
            if daily_time:
                try:
                    h, m, s = [int(x) for x in str(daily_time).split(':')]
                    opening = _dt.datetime(now.year, now.month, now.day, h, m, s)
                    delay_minutes = int((now - opening).total_seconds() // 60)
                    is_next_day = opening.date() < now.date()
                    pole_type = classify_delay(delay_minutes, is_next_day)
                    count_type = sum(1 for p in today_poles if p.get('pole_type') == pole_type)
                    total_members = sum(1 for mem in interaction.guild.members if not mem.bot)
                    has_quota, current, max_allowed = check_quota_available(pole_type, count_type, total_members)
                    quota_info = f"{pole_type}: {current}/{max_allowed if max_allowed is not None else '∞'} disponible={has_quota}"
                except Exception as e:
                    quota_info = f"Error cuota: {e}"
            report.append(f"Cuota estimada: {quota_info}")

            # Datos de usuario
            user_data = self.db.get_user(target.id, gid) or {}
            report.append(f"Racha actual: {int(user_data.get('current_streak', 0))}")
            report.append(f"Último pole: {user_data.get('last_pole_date', 'N/A')}")

            embed = discord.Embed(
                title=f"🔍 Diagnóstico de {target.display_name}",
                description="\n".join(report),
                color=discord.Color.dark_gray(),
                timestamp=_dt.datetime.now()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Error: {e}", ephemeral=True)

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

    # ====== FORZAR GENERACIÓN DE HORA DIARIA ======
    @debug.command(name="force_generate", description="Fuerza la generación de hora diaria para hoy (simula medianoche)")
    @debug_only()
    async def force_generate(self, interaction: discord.Interaction):
        """Ejecuta manualmente el generador de horas diarias"""
        if interaction.guild is None:
            await interaction.response.send_message("❌ Solo en servidores.", ephemeral=True)
            return
        
        await interaction.response.defer(ephemeral=True)
        
        try:
            pole_cog = self.bot.get_cog('PoleCog')
            if not pole_cog:
                await interaction.followup.send("❌ No se pudo encontrar PoleCog.", ephemeral=True)
                return
            
            # Ejecutar el generador manualmente usando getattr para evitar error de type checker
            generator = getattr(pole_cog, 'daily_pole_generator', None)
            if generator and callable(generator):
                # Llamar a la función del loop manualmente
                generator_func = getattr(generator, 'callback', generator)
                if callable(generator_func):
                    result = generator_func()
                    # Verificar si es coroutine y ejecutarlo
                    if inspect.iscoroutine(result):
                        await result  # type: ignore
                
                # Obtener hora generada
                new_time = self.db.get_daily_pole_time(interaction.guild.id)
                
                await interaction.followup.send(
                    f"✅ Generación forzada completada.\n"
                    f"Nueva hora de apertura: **{new_time}**\n"
                    f"Revisa `/debug info` para verificar.",
                    ephemeral=True
                )
            else:
                await interaction.followup.send("❌ No se pudo acceder al generador.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)
            print(f"❌ Error en force_generate: {e}")

    # ====== TESTEAR MIGRACIÓN DE TEMPORADA ======
    @debug.command(name="test_migration", description="Probar migración de temporada (DRY RUN o REAL)")
    @app_commands.describe(
        dry_run="Si es True, solo simula sin hacer cambios reales (recomendado)",
        target_season="ID de temporada objetivo (ej: 2026, dejar vacío para auto-detectar)"
    )
    @debug_only()
    async def test_migration(self, interaction: discord.Interaction, dry_run: bool = True, target_season: Optional[str] = None):
        """Testear el sistema de migración de temporadas"""
        await interaction.response.defer(ephemeral=True)
        
        from utils.scoring import get_current_season, get_season_info
        
        # Determinar season objetivo
        if target_season is None:
            target_season = get_current_season()
        else:
            # Normalizar: Si es un año numérico, convertir a season_N
            try:
                year = int(target_season)
                if year >= 2026:
                    target_season = f'season_{year - 2025}'
                    print(f"🔧 target_season normalizado: año {year} → {target_season}")
                elif year == 2025:
                    target_season = 'preseason'
                    print(f"🔧 target_season normalizado: año {year} → {target_season}")
            except ValueError:
                # No es un año, usar tal cual (ej: "season_1", "preseason")
                pass
        
        # Validar que el season_id sea válido
        try:
            season_info = get_season_info(target_season)
        except ValueError as e:
            await interaction.followup.send(
                f"❌ Error: {e}\n\n**Formatos válidos:**\n"
                f"• `preseason` o `2025`\n"
                f"• `season_1` o `2026`\n"
                f"• `season_2` o `2027`\n"
                f"• etc.",
                ephemeral=True
            )
            return
        
        try:
            # Obtener season activa actual
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT season_id FROM seasons WHERE is_active = 1')
                row = cursor.fetchone()
                current_active = row[0] if row else "Ninguna"
            
            embed = discord.Embed(
                title="🧪 Test de Migración de Temporada",
                color=discord.Color.orange() if dry_run else discord.Color.red(),
                timestamp=datetime.now()
            )
            
            embed.add_field(
                name="🔍 Estado Actual",
                value=f"Season activa: **{current_active}**\nSeason objetivo: **{target_season}**",
                inline=False
            )
            
            if dry_run:
                # SIMULACIÓN - Solo mostrar qué pasaría
                embed.add_field(
                    name="⚠️ MODO DRY RUN",
                    value="No se harán cambios reales. Solo simulación.",
                    inline=False
                )
                
                # Simular lo que pasaría
                if current_active == target_season:
                    embed.add_field(
                        name="ℹ️ Resultado",
                        value="Ya estamos en la temporada objetivo. No se requiere migración.",
                        inline=False
                    )
                else:
                    # Contar datos que se guardarían
                    with self.db.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute('SELECT COUNT(*) FROM season_stats WHERE season_id = ?', (current_active,))
                        stats_count = cursor.fetchone()[0]
                        
                        cursor.execute('SELECT COUNT(DISTINCT guild_id) FROM season_stats WHERE season_id = ?', (current_active,))
                        guilds_count = cursor.fetchone()[0]
                    
                    actions = [
                        f"✅ Finalizar temporada **{current_active}**",
                        f"📊 Guardar {stats_count} registros en historial",
                        f"🏆 Otorgar badges a usuarios de {guilds_count} servidores",
                        f"🔄 Activar temporada **{target_season}**",
                        f"♻️ Resetear rachas actuales (current_streak → 0)",
                        f"🗑️ Limpiar season_stats antiguas (mantener últimas 3)"
                    ]
                    
                    embed.add_field(
                        name="📋 Acciones que se ejecutarían",
                        value="\n".join(actions),
                        inline=False
                    )
                
                embed.set_footer(text="Usa dry_run=False para ejecutar la migración real (¡CUIDADO!)")
                
            else:
                # EJECUCIÓN REAL
                embed.add_field(
                    name="🚨 MODO REAL",
                    value="Se ejecutará la migración REAL. Esto NO se puede deshacer.",
                    inline=False
                )
                
                # Ejecutar migración
                migrated = self.db.migrate_season(target_season, force=False)
                
                if migrated:
                    embed.add_field(
                        name="✅ Migración Completada",
                        value=f"Temporada migrada: **{current_active}** → **{target_season}**",
                        inline=False
                    )
                    
                    # Verificar integridad
                    verification = self.db.verify_migration_integrity(target_season)
                    
                    if verification['is_valid']:
                        embed.add_field(
                            name="✅ Verificación de Integridad",
                            value="Todos los checks pasaron correctamente.",
                            inline=False
                        )
                    else:
                        issues_text = "\n".join([f"⚠️ {issue}" for issue in verification['issues']])
                        embed.add_field(
                            name="⚠️ Problemas Detectados",
                            value=issues_text,
                            inline=False
                        )
                    
                    stats_text = "\n".join([f"• {k}: {v}" for k, v in verification['stats'].items()])
                    embed.add_field(
                        name="📊 Estadísticas",
                        value=stats_text,
                        inline=False
                    )
                    
                    # 🎬 MOSTRAR POLE REWIND después de migración exitosa
                    if migrated and verification['is_valid']:
                        embed.add_field(
                            name="🎬 POLE REWIND",
                            value=(
                                f"Se enviará el POLE REWIND de **{current_active}** a todos los servidores.\n"
                                "Espera unos segundos..."
                            ),
                            inline=False
                        )
                        
                        await interaction.followup.send(embed=embed, ephemeral=True)
                        
                        # Obtener PoleCog y ejecutar POLE REWIND
                        pole_cog = self.bot.get_cog('PoleCog')
                        if pole_cog and hasattr(pole_cog, '_send_season_change_announcement'):
                            await pole_cog._send_season_change_announcement(current_active, target_season)  # type: ignore[attr-defined]
                            
                            # Confirmar envío
                            confirm_embed = discord.Embed(
                                title="✅ POLE REWIND Enviado",
                                description=f"El POLE REWIND de **{current_active}** se ha enviado a todos los servidores configurados.",
                                color=discord.Color.green(),
                                timestamp=datetime.now()
                            )
                            await interaction.followup.send(embed=confirm_embed, ephemeral=True)
                        else:
                            await interaction.followup.send(
                                "⚠️ No se pudo enviar POLE REWIND (PoleCog no encontrado)",
                                ephemeral=True
                            )
                        return  # Salir aquí para evitar enviar embed dos veces
                    
                else:
                    embed.add_field(
                        name="ℹ️ Sin Cambios",
                        value="La migración no era necesaria (ya estamos en la temporada correcta).",
                        inline=False
                    )
                
                embed.set_footer(text="Migración ejecutada en modo REAL")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ Error durante el test de migración: {e}",
                ephemeral=True
            )
            print(f"❌ Error en test_migration: {e}")
            import traceback
            traceback.print_exc()

    # ====== REPARAR ESTADO DE TEMPORADA (EMERGENCIA) ======
    @debug.command(name="fix_season_state", description="🚨 Reparar estado corrupto de temporadas (EMERGENCIA)")
    @app_commands.describe(
        confirm="Escribe 'CONFIRMAR' para ejecutar la reparación"
    )
    @debug_only()
    async def fix_season_state(self, interaction: discord.Interaction, confirm: str):
        """
        Comando de emergencia para reparar el estado de temporadas cuando
        la migración automática falla (ej: bot caído en año nuevo).
        
        Esto detecta la temporada correcta según el año actual y fuerza
        que sea la única activa en la base de datos.
        """
        await interaction.response.defer(ephemeral=True)
        
        if confirm.upper() != "CONFIRMAR":
            await interaction.followup.send(
                "❌ Debes escribir exactamente `CONFIRMAR` para ejecutar esta reparación.",
                ephemeral=True
            )
            return
        
        from utils.scoring import get_current_season, get_season_info
        
        try:
            # Detectar temporada correcta según año actual
            correct_season = get_current_season()
            correct_info = get_season_info(correct_season)
            
            embed = discord.Embed(
                title="🚨 Reparación de Estado de Temporadas",
                description="Forzando temporada correcta según el año actual...",
                color=discord.Color.red(),
                timestamp=datetime.now()
            )
            
            # Paso 1: Ver estado actual
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT season_id, season_name, is_active FROM seasons ORDER BY season_id')
                all_seasons = cursor.fetchall()
            
            seasons_list = "\n".join([
                f"{'✅' if row[2] else '❌'} **{row[0]}**: {row[1]}"
                for row in all_seasons
            ])
            
            embed.add_field(
                name="📊 Estado Antes de Reparación",
                value=seasons_list if seasons_list else "❌ No hay temporadas en BD",
                inline=False
            )
            
            # Paso 2: Verificar si la temporada correcta existe
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT 1 FROM seasons WHERE season_id = ?', (correct_season,))
                season_exists = cursor.fetchone() is not None
            
            if not season_exists:
                # Crear la temporada correcta
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        INSERT INTO seasons (season_id, season_name, start_date, end_date, is_active)
                        VALUES (?, ?, ?, ?, 1)
                    ''', (
                        correct_season,
                        correct_info['name'],
                        correct_info['start_date'],  # Ya es string 'YYYY-MM-DD'
                        correct_info['end_date']     # Ya es string 'YYYY-MM-DD'
                    ))
                    conn.commit()
                
                embed.add_field(
                    name="✅ Temporada Creada",
                    value=f"**{correct_season}** ({correct_info['name']}) creada y activada.",
                    inline=False
                )
            
            # Paso 3: Desactivar TODAS las temporadas
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE seasons SET is_active = 0')
                deactivated = cursor.rowcount
                conn.commit()
            
            # Paso 4: Activar SOLO la temporada correcta
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('UPDATE seasons SET is_active = 1 WHERE season_id = ?', (correct_season,))
                activated = cursor.rowcount
                conn.commit()
            
            embed.add_field(
                name="🔧 Acciones Ejecutadas",
                value=(
                    f"• Desactivadas: **{deactivated}** temporadas\n"
                    f"• Activada: **{correct_season}** ({correct_info['name']})\n"
                    f"• Período: {correct_info['start_date']} → {correct_info['end_date']}"
                ),
                inline=False
            )
            
            # Paso 5: Verificar estado final
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT season_id, season_name, is_active FROM seasons ORDER BY season_id')
                all_seasons = cursor.fetchall()
            
            seasons_list_after = "\n".join([
                f"{'✅' if row[2] else '❌'} **{row[0]}**: {row[1]}"
                for row in all_seasons
            ])
            
            embed.add_field(
                name="📊 Estado Después de Reparación",
                value=seasons_list_after,
                inline=False
            )
            
            # Paso 6: Verificar integridad
            verification = self.db.verify_migration_integrity(correct_season)
            
            if verification['is_valid']:
                embed.add_field(
                    name="✅ Verificación de Integridad",
                    value="Base de datos consistente. El sistema debería funcionar correctamente.",
                    inline=False
                )
            else:
                issues_text = "\n".join([f"⚠️ {issue}" for issue in verification['issues']])
                embed.add_field(
                    name="⚠️ Advertencias",
                    value=issues_text,
                    inline=False
                )
            
            embed.set_footer(text="Reparación completada. Verifica /season en un servidor para confirmar.")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Log para servidor
            print(f"🚨 fix_season_state ejecutado por {interaction.user.name}")
            print(f"   Temporada corregida a: {correct_season} ({correct_info['name']})")
            
        except Exception as e:
            await interaction.followup.send(
                f"❌ Error durante la reparación: {e}",
                ephemeral=True
            )
            print(f"❌ Error en fix_season_state: {e}")
            import traceback
            traceback.print_exc()

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
        
        # Calcular pole_date efectivo (para marranero es el día anterior)
        if is_next_day:
            # Marranero: cuenta para el día anterior
            pole_date = opening_time.strftime('%Y-%m-%d')
        else:
            # Normal: cuenta para hoy
            pole_date = user_time.strftime('%Y-%m-%d')
        
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
            streak=new_streak,
            pole_date=pole_date  # CRÍTICO: fecha efectiva
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

    # ====== HEALTH CHECK DE BASE DE DATOS ======
    @debug.command(name="db_check", description="Verificar integridad y consistencia de la base de datos")
    @debug_only()
    async def db_check(self, interaction: discord.Interaction):
        """
        Verifica la BD en busca de inconsistencias:
        - Usuarios huérfanos (sin poles pero con racha)
        - Rachas inconsistentes (current_streak > 0 pero last_pole_date muy antiguo)
        - season_stats que no coinciden con conteo de poles
        - Poles sin usuario correspondiente
        - Duplicados de pole en el mismo día/servidor/usuario
        """
        await interaction.response.defer(ephemeral=True)
        
        issues: list[str] = []
        warnings: list[str] = []
        stats: dict[str, int] = {}
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # ========== ESTADÍSTICAS GENERALES ==========
            cursor.execute('SELECT COUNT(*) FROM users')
            stats['total_users'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM poles')
            stats['total_poles'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM servers')
            stats['total_servers'] = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM season_stats')
            stats['total_season_stats'] = cursor.fetchone()[0]
            
            # ========== CHECK 1: Usuarios con racha pero sin pole reciente ==========
            today = datetime.now().strftime('%Y-%m-%d')
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            
            cursor.execute('''
                SELECT user_id, guild_id, username, current_streak, last_pole_date
                FROM users
                WHERE current_streak > 0 
                  AND (last_pole_date IS NULL OR last_pole_date < ?)
            ''', (yesterday,))
            stale_streaks = cursor.fetchall()
            
            if stale_streaks:
                for row in stale_streaks[:5]:
                    issues.append(
                        f"⚠️ Racha fantasma: {row[2]} (ID:{row[0]}) tiene racha {row[3]} "
                        f"pero último pole fue {row[4] or 'NUNCA'}"
                    )
                if len(stale_streaks) > 5:
                    issues.append(f"   ... y {len(stale_streaks) - 5} más")
            
            # ========== CHECK 2: Poles duplicados mismo día/servidor/usuario ==========
            # Usar pole_date (fecha efectiva) en lugar de DATE(user_time)
            cursor.execute('''
                SELECT user_id, guild_id, pole_date, COUNT(*) as cnt
                FROM poles
                WHERE pole_date IS NOT NULL
                GROUP BY user_id, guild_id, pole_date
                HAVING cnt > 1
            ''')
            duplicates = cursor.fetchall()
            
            if duplicates:
                for row in duplicates[:5]:
                    issues.append(
                        f"🔴 Pole duplicado: user {row[0]} en guild {row[1]} "
                        f"fecha {row[2]} tiene {row[3]} poles"
                    )
                if len(duplicates) > 5:
                    issues.append(f"   ... y {len(duplicates) - 5} más")
            
            # ========== CHECK 2.5: Poles con pole_date NULL ==========
            cursor.execute('''
                SELECT COUNT(*) FROM poles WHERE pole_date IS NULL
            ''')
            null_dates_count = cursor.fetchone()[0]
            
            if null_dates_count > 0:
                issues.append(
                    f"🔴 {null_dates_count} poles con pole_date NULL (legadas, necesitan reparación)"
                )
            
            # ========== CHECK 3: Poles sin usuario en tabla users ==========
            cursor.execute('''
                SELECT p.user_id, p.guild_id, COUNT(*) as cnt
                FROM poles p
                LEFT JOIN users u ON p.user_id = u.user_id AND p.guild_id = u.guild_id
                WHERE u.user_id IS NULL
                GROUP BY p.user_id, p.guild_id
            ''')
            orphan_poles = cursor.fetchall()
            
            if orphan_poles:
                for row in orphan_poles[:5]:
                    warnings.append(
                        f"🟡 Poles huérfanos: user {row[0]} guild {row[1]} "
                        f"tiene {row[2]} poles pero no existe en users"
                    )
                if len(orphan_poles) > 5:
                    warnings.append(f"   ... y {len(orphan_poles) - 5} más")
            
            # ========== CHECK 4: season_stats vs poles (discrepancia de conteo) ==========
            current_season = get_current_season()
            
            # Obtener año de la season actual para filtrar poles
            season_year = 2025 if current_season == 'preseason' else (2025 + int(current_season.split('_')[1]))
            
            cursor.execute('''
                SELECT 
                    ss.user_id, ss.guild_id, ss.season_poles,
                    COUNT(p.id) as actual_poles
                FROM season_stats ss
                LEFT JOIN poles p ON ss.user_id = p.user_id 
                    AND ss.guild_id = p.guild_id
                    AND strftime('%Y', p.created_at) = ?
                WHERE ss.season_id = ?
                GROUP BY ss.user_id, ss.guild_id, ss.season_poles
                HAVING ABS(ss.season_poles - actual_poles) > 0
            ''', (str(season_year), current_season))
            mismatched = cursor.fetchall()
            
            if mismatched:
                for row in mismatched[:5]:
                    warnings.append(
                        f"🟠 Discrepancia: user {row[0]} guild {row[1]} "
                        f"season_stats={row[2]} vs poles reales={row[3]}"
                    )
                if len(mismatched) > 5:
                    warnings.append(f"   ... y {len(mismatched) - 5} más")
            
            # ========== CHECK 5: best_streak < current_streak ==========
            cursor.execute('''
                SELECT user_id, guild_id, username, current_streak, best_streak
                FROM users
                WHERE current_streak > best_streak
            ''')
            streak_issues = cursor.fetchall()
            
            if streak_issues:
                for row in streak_issues[:5]:
                    issues.append(
                        f"🔴 Racha inválida: {row[2]} (ID:{row[0]}) "
                        f"current={row[3]} > best={row[4]}"
                    )
                if len(streak_issues) > 5:
                    issues.append(f"   ... y {len(streak_issues) - 5} más")
            
            # ========== CHECK 6: Servidores sin canal configurado pero con poles ==========
            cursor.execute('''
                SELECT s.guild_id, COUNT(p.id) as pole_count
                FROM servers s
                JOIN poles p ON s.guild_id = p.guild_id
                WHERE s.pole_channel_id IS NULL OR s.pole_channel_id = 0
                GROUP BY s.guild_id
            ''')
            no_channel = cursor.fetchall()
            
            if no_channel:
                for row in no_channel[:3]:
                    warnings.append(
                        f"🟡 Guild {row[0]} tiene {row[1]} poles pero sin canal configurado"
                    )
            
            # ========== CHECK 7: Poles sin season_stats ==========
            cursor.execute('''
                SELECT COUNT(DISTINCT p.user_id, p.guild_id) as orphan_count
                FROM poles p
                LEFT JOIN season_stats ss ON p.user_id = ss.user_id 
                    AND p.guild_id = ss.guild_id
                WHERE ss.user_id IS NULL
            ''')
            orphan_result = cursor.fetchone()
            orphan_count = orphan_result[0] if orphan_result and orphan_result[0] else 0
            if orphan_count > 0:
                issues.append(f"🔴 {orphan_count} entradas de poles sin season_stats")
            
            # ========== CHECK 8: Contadores de categoría desactualizados ==========
            cursor.execute('''
                SELECT COUNT(*) FROM users u
                WHERE (u.critical_poles + u.fast_poles + u.normal_poles + u.marranero_poles) != 
                      (SELECT COUNT(*) FROM poles p WHERE p.user_id = u.user_id AND p.guild_id = u.guild_id)
            ''')
            category_mismatches = cursor.fetchone()[0]
            if category_mismatches > 0:
                issues.append(f"🔴 {category_mismatches} usuarios con contadores de categoría desactualizados")
            
            # ========== CHECK 9: last_pole_date desincronizado ==========
            cursor.execute('''
                SELECT COUNT(*) FROM users u
                WHERE u.last_pole_date != 
                      (SELECT MAX(DATE(p.user_time)) FROM poles p WHERE p.user_id = u.user_id AND p.guild_id = u.guild_id)
            ''')
            date_mismatches = cursor.fetchone()[0]
            if date_mismatches > 0:
                issues.append(f"🔴 {date_mismatches} usuarios con last_pole_date desincronizado")
            
            # ========== CHECK 10: Guilds sin configuración ==========
            cursor.execute('''
                SELECT COUNT(DISTINCT p.guild_id) FROM poles p
                LEFT JOIN servers s ON p.guild_id = s.guild_id
                WHERE s.guild_id IS NULL
            ''')
            missing_guilds = cursor.fetchone()[0]
            if missing_guilds > 0:
                warnings.append(f"🟡 {missing_guilds} guilds con poles pero sin configuración en servers")
        
        # ========== CONSTRUIR EMBED DE RESULTADO ==========
        embed = discord.Embed(
            title="🔍 Health Check de Base de Datos",
            color=discord.Color.green() if not issues else discord.Color.red(),
            timestamp=datetime.now()
        )
        
        # Stats generales
        stats_text = (
            f"👥 Usuarios: **{stats['total_users']}**\n"
            f"🏁 Poles: **{stats['total_poles']}**\n"
            f"🏠 Servidores: **{stats['total_servers']}**\n"
            f"📊 Season Stats: **{stats['total_season_stats']}**"
        )
        embed.add_field(name="📈 Estadísticas", value=stats_text, inline=False)
        
        # Issues críticos
        if issues:
            embed.add_field(
                name=f"🔴 Problemas ({len(issues)})",
                value="\n".join(issues[:10]) or "Ninguno",
                inline=False
            )
            embed.color = discord.Color.red()
        
        # Warnings
        if warnings:
            embed.add_field(
                name=f"🟡 Advertencias ({len(warnings)})",
                value="\n".join(warnings[:10]) or "Ninguna",
                inline=False
            )
            if not issues:
                embed.color = discord.Color.orange()
        
        # Resumen
        if not issues and not warnings:
            embed.add_field(
                name="✅ Estado",
                value="La base de datos está en buen estado. No se encontraron inconsistencias.",
                inline=False
            )
        else:
            embed.add_field(
                name="💡 Recomendación",
                value="Usa `/debug db_fix` para intentar reparar automáticamente los problemas detectados.",
                inline=False
            )
        
        embed.set_footer(text="Health check completado")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @debug.command(name="db_fix", description="Intentar reparar inconsistencias de la base de datos")
    @debug_only()
    async def db_fix(self, interaction: discord.Interaction):
        """
        Intenta reparar automáticamente las inconsistencias detectadas:
        - Resetea rachas fantasma (current_streak con last_pole_date muy antiguo)
        - Actualiza best_streak si current_streak > best_streak
        - Crea entradas de usuario faltantes para poles huérfanos
        """
        await interaction.response.defer(ephemeral=True)
        
        fixes: list[str] = []
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # ========== FIX 1: Rachas fantasma ==========
            yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
            
            cursor.execute('''
                UPDATE users
                SET current_streak = 0
                WHERE current_streak > 0 
                  AND (last_pole_date IS NULL OR last_pole_date < ?)
            ''', (yesterday,))
            
            if cursor.rowcount > 0:
                fixes.append(f"✅ Reseteadas {cursor.rowcount} rachas fantasma")
            
            # ========== FIX 2: best_streak < current_streak ==========
            cursor.execute('''
                UPDATE users
                SET best_streak = current_streak
                WHERE current_streak > best_streak
            ''')
            
            if cursor.rowcount > 0:
                fixes.append(f"✅ Corregidas {cursor.rowcount} mejores rachas")
            
            # ========== FIX 3: Crear usuarios para poles huérfanos ==========
            cursor.execute('''
                SELECT DISTINCT p.user_id, p.guild_id
                FROM poles p
                LEFT JOIN users u ON p.user_id = u.user_id AND p.guild_id = u.guild_id
                WHERE u.user_id IS NULL
            ''')
            orphans = cursor.fetchall()
            
            for user_id, guild_id in orphans:
                cursor.execute('''
                    INSERT OR IGNORE INTO users (user_id, guild_id, username)
                    VALUES (?, ?, ?)
                ''', (user_id, guild_id, f"User_{user_id}"))
            
            if orphans:
                fixes.append(f"✅ Creados {len(orphans)} usuarios para poles huérfanos")
            
            # ========== FIX 4: Eliminar poles duplicados (mantener el primero) ==========
            # Primero encontrar todos los duplicados
            cursor.execute('''
                SELECT user_id, guild_id, DATE(user_time) as pole_date
                FROM poles
                GROUP BY user_id, guild_id, pole_date
                HAVING COUNT(*) > 1
            ''')
            dup_groups = cursor.fetchall()
            
            total_deleted = 0
            for user_id, guild_id, pole_date in dup_groups:
                # Obtener todos los IDs de ese grupo, ordenados por user_time (el primero es el válido)
                cursor.execute('''
                    SELECT id FROM poles
                    WHERE user_id = ? AND guild_id = ? AND DATE(user_time) = ?
                    ORDER BY user_time ASC
                ''', (user_id, guild_id, pole_date))
                pole_ids = [row[0] for row in cursor.fetchall()]
                
                # Eliminar todos menos el primero
                if len(pole_ids) > 1:
                    ids_to_delete = pole_ids[1:]  # Todo excepto el primero
                    placeholders = ','.join('?' * len(ids_to_delete))
                    cursor.execute(f'DELETE FROM poles WHERE id IN ({placeholders})', ids_to_delete)
                    total_deleted += len(ids_to_delete)
            
            if total_deleted > 0:
                fixes.append(f"✅ Eliminados {total_deleted} poles duplicados (manteniendo el primero de cada día)")
            
            conn.commit()
        
        # Resultado
        embed = discord.Embed(
            title="🔧 Reparación de Base de Datos",
            color=discord.Color.green() if fixes else discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        if fixes:
            embed.description = "\n".join(fixes)
        else:
            embed.description = "No se encontraron problemas que reparar."
        
        embed.set_footer(text="Usa /debug db_check para verificar el estado")
        await interaction.followup.send(embed=embed, ephemeral=True)

    @debug.command(name="user_poles", description="Ver historial de poles de un usuario")
    @app_commands.describe(usuario="Usuario a consultar", dias="Días hacia atrás (default 7)")
    @debug_only()
    async def user_poles(self, interaction: discord.Interaction, usuario: Optional[discord.Member] = None, dias: int = 7):
        """Ver los últimos poles de un usuario para diagnosticar"""
        if not interaction.guild:
            await interaction.response.send_message("❌ Solo en servidores.", ephemeral=True)
            return
        
        target = usuario or interaction.user
        gid = interaction.guild.id
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            since = (datetime.now() - timedelta(days=dias)).strftime('%Y-%m-%d')
            
            cursor.execute('''
                SELECT id, DATE(user_time) as fecha, pole_type, points_earned, 
                       streak_at_time, delay_minutes
                FROM poles
                WHERE user_id = ? AND guild_id = ? AND DATE(user_time) >= ?
                ORDER BY user_time DESC
                LIMIT 20
            ''', (target.id, gid, since))
            
            poles = cursor.fetchall()
        
        if not poles:
            await interaction.response.send_message(
                f"❌ {target.mention} no tiene poles en los últimos {dias} días.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title=f"📜 Historial de Poles - {target.display_name}",
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

    # ====== EDITAR RACHA DE USUARIO ======
    @debug.command(name="set_streak", description="Establecer la racha de un usuario manualmente")
    @app_commands.describe(
        usuario="Usuario al que modificar la racha",
        racha="Nueva racha actual",
        mejor_racha="Nueva mejor racha (opcional, si no se pone mantiene la actual)"
    )
    @debug_only()
    async def set_streak(
        self, 
        interaction: discord.Interaction, 
        usuario: discord.Member,
        racha: app_commands.Range[int, 0, 1000],
        mejor_racha: Optional[int] = None
    ):
        """Establecer racha de un usuario manualmente (usa rachas globales en v5)"""
        if not interaction.guild:
            await interaction.response.send_message("❌ Solo en servidores.", ephemeral=True)
            return
        
        gid = interaction.guild.id
        
        # v5: Rachas están en global_users, no en users
        global_user = self.db.get_global_user(usuario.id)
        
        if not global_user:
            await interaction.response.send_message(
                f"❌ {usuario.mention} no tiene datos globales.",
                ephemeral=True
            )
            return
        
        old_streak = global_user.get('current_streak', 0)
        old_best = global_user.get('best_streak', 0)
        
        # Si no se especifica mejor_racha, usar la mayor entre la actual y la nueva
        new_best = mejor_racha if mejor_racha is not None else max(old_best, racha)
        
        # Actualizar en global_users
        self.db.update_global_user(
            usuario.id, 
            current_streak=racha, 
            best_streak=new_best
        )
        
        embed = discord.Embed(
            title="🔧 Racha Modificada (Global)",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        embed.add_field(name="👤 Usuario", value=usuario.mention, inline=True)
        embed.add_field(name="🔥 Racha Actual", value=f"{old_streak} → **{racha}**", inline=True)
        embed.add_field(name="🏆 Mejor Racha", value=f"{old_best} → **{new_best}**", inline=True)
        embed.set_footer(text="Las rachas son globales en v5 (compartidas entre servidores)")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ====== ESTABLECER ÚLTIMO POLE DATE ======
    @debug.command(name="set_last_pole", description="Establecer la fecha del último pole de un usuario")
    @app_commands.describe(
        usuario="Usuario al que modificar",
        fecha="Fecha en formato YYYY-MM-DD (ej: 2025-12-01)"
    )
    @debug_only()
    async def set_last_pole(
        self, 
        interaction: discord.Interaction, 
        usuario: discord.Member,
        fecha: str
    ):
        """Establecer fecha del último pole de un usuario"""
        if not interaction.guild:
            await interaction.response.send_message("❌ Solo en servidores.", ephemeral=True)
            return
        
        # Validar formato de fecha
        try:
            parsed_date = datetime.strptime(fecha, '%Y-%m-%d')
        except ValueError:
            await interaction.response.send_message(
                "❌ Formato de fecha inválido. Usa YYYY-MM-DD (ej: 2025-12-01)",
                ephemeral=True
            )
            return
        
        gid = interaction.guild.id
        user_data = self.db.get_user(usuario.id, gid)
        
        if not user_data:
            await interaction.response.send_message(
                f"❌ {usuario.mention} no tiene datos en este servidor.",
                ephemeral=True
            )
            return
        
        old_date = user_data.get('last_pole_date', 'Nunca')
        
        # Actualizar
        self.db.update_user(usuario.id, gid, last_pole_date=fecha)
        
        embed = discord.Embed(
            title="📅 Fecha de Último Pole Modificada",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        embed.add_field(name="👤 Usuario", value=usuario.mention, inline=True)
        embed.add_field(name="📅 Último Pole", value=f"{old_date} → **{fecha}**", inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ====== VER INFO COMPLETA DE USUARIO ======
    # ====== DIAGNÓSTICO COMPLETO DE USUARIO ======
    @debug.command(name="diagnose", description="Diagnóstico completo: info de usuario + verificación de pole")
    @app_commands.describe(usuario="Usuario a diagnosticar (default: tú)")
    @debug_only()
    async def diagnose(self, interaction: discord.Interaction, usuario: Optional[discord.Member] = None):
        """Diagnóstico completo: info de usuario, estado de pole, y verificaciones"""
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
        
        # ========== SECCIÓN 1: DATOS DEL USUARIO ==========
        if user_data:
            embed.add_field(
                name="👤 Datos Básicos",
                value=(
                    f"🆔 ID: `{target.id}`\n"
                    f"📛 BD: {user_data.get('username', 'N/A')}\n"
                    f"💰 Puntos: {user_data.get('total_points', 0):.1f}\n"
                    f"🏁 Poles: {user_data.get('total_poles', 0)}"
                ),
                inline=True
            )
            
            embed.add_field(
                name="🔥 Rachas",
                value=(
                    f"Actual: **{user_data.get('current_streak', 0)}**\n"
                    f"Mejor: {user_data.get('best_streak', 0)}\n"
                    f"Último: {user_data.get('last_pole_date', 'Nunca')}"
                ),
                inline=True
            )
            
            # Contadores por tipo (compacto)
            embed.add_field(
                name="📊 Por Tipo",
                value=(
                    f"💎 {user_data.get('critical_poles', 0)} | "
                    f"⚡ {user_data.get('fast_poles', 0)} | "
                    f"🏁 {user_data.get('normal_poles', 0)} | "
                    f"🐷 {user_data.get('marranero_poles', 0)}"
                ),
                inline=False
            )
        else:
            embed.add_field(
                name="👤 Datos del Usuario",
                value="⚠️ Sin datos en este servidor (primera vez)",
                inline=False
            )
        
        # ========== SECCIÓN 2: POLE DE HOY ==========
        # Buscar si hizo pole hoy o ayer
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            # Pole de hoy (por pole_date efectiva)
            cursor.execute('''
                SELECT pole_type, user_time, delay_minutes, points_earned, pole_date
                FROM poles
                WHERE user_id = ? AND guild_id = ? 
                  AND (pole_date = ? OR (pole_date IS NULL AND DATE(user_time) = ?))
                ORDER BY user_time DESC
                LIMIT 1
            ''', (target.id, gid, today_str, today_str))
            pole_today = cursor.fetchone()
            
            # Pole de ayer (por pole_date efectiva)
            cursor.execute('''
                SELECT pole_type, user_time, delay_minutes, points_earned, pole_date
                FROM poles
                WHERE user_id = ? AND guild_id = ? 
                  AND (pole_date = ? OR (pole_date IS NULL AND DATE(user_time) = ?))
                ORDER BY user_time DESC
                LIMIT 1
            ''', (target.id, gid, yesterday_str, yesterday_str))
            pole_yesterday = cursor.fetchone()
        
        pole_info_lines = []
        
        if pole_today:
            pole_time = pole_today['user_time']
            pole_type = pole_today['pole_type']
            pole_date_eff = pole_today['pole_date'] or 'N/A'
            delay = pole_today['delay_minutes']
            points = pole_today['points_earned']
            
            type_emoji = {'critical': '💎', 'fast': '⚡', 'normal': '🏁', 'marranero': '🐷'}.get(pole_type, '❓')
            pole_info_lines.append(f"**HOY** ({today_str}):")
            pole_info_lines.append(f"   {type_emoji} {pole_type.upper()} a las `{pole_time}`")
            pole_info_lines.append(f"   ⏱️ {delay} min | 💰 {points:.1f} pts")
            if pole_date_eff != today_str:
                pole_info_lines.append(f"   ⚠️ pole_date={pole_date_eff} (¿marranero?)")
        else:
            pole_info_lines.append(f"**HOY** ({today_str}): ❌ No ha hecho pole")
        
        if pole_yesterday:
            pole_time = pole_yesterday['user_time']
            pole_type = pole_yesterday['pole_type']
            pole_date_eff = pole_yesterday['pole_date'] or 'N/A'
            type_emoji = {'critical': '💎', 'fast': '⚡', 'normal': '🏁', 'marranero': '🐷'}.get(pole_type, '❓')
            pole_info_lines.append(f"**AYER** ({yesterday_str}): {type_emoji} {pole_type} a las `{pole_time}`")
        else:
            pole_info_lines.append(f"**AYER** ({yesterday_str}): ❌ No hizo pole")
        
        embed.add_field(
            name="🗓️ Historial Reciente",
            value="\n".join(pole_info_lines),
            inline=False
        )
        
        # ========== SECCIÓN 3: VERIFICACIONES (¿Puede hacer pole?) ==========
        checks = []
        can_pole = True
        
        # Check 1: Servidor configurado
        if not config or not config.get('pole_channel_id'):
            checks.append("❌ Sin canal configurado")
            can_pole = False
        else:
            checks.append(f"✅ Canal: <#{config['pole_channel_id']}>")
        
        # Check 2: Hora y estado
        daily_time = config.get('daily_pole_time') if config else None
        if not daily_time:
            checks.append("❌ Sin hora de pole hoy")
            can_pole = False
        else:
            try:
                h, m, s = [int(x) for x in str(daily_time).split(':')]
                opening = datetime(now.year, now.month, now.day, h, m, s)
                
                if now < opening:
                    if now.hour < 8:
                        checks.append(f"🟡 Ventana marranero (abre {daily_time})")
                    else:
                        mins = int((opening-now).total_seconds()//60)
                        checks.append(f"⏳ Abre en {mins} min ({daily_time})")
                        can_pole = False
                else:
                    mins = int((now-opening).total_seconds()//60)
                    checks.append(f"🟢 ABIERTO hace {mins} min ({daily_time})")
            except:
                checks.append("⚠️ Error hora")
        
        # Check 3: Ya hizo pole hoy
        if pole_today:
            checks.append("🛑 Ya hizo pole HOY")
            can_pole = False
        else:
            checks.append("✅ Sin pole hoy")
        
        # Check 4: Marranero (si aplica)
        if now.hour < 8:
            if pole_yesterday:
                checks.append("🛑 Ya hizo ayer (no marranero)")
            else:
                checks.append("✅ Puede marranero")
        
        # Check 5: Pole global
        global_today = self.db.get_user_pole_on_date_global(target.id, today_str)
        if global_today and int(global_today.get('guild_id', 0)) != gid:
            other_guild = self.bot.get_guild(int(global_today['guild_id']))
            other_name = other_guild.name if other_guild else f"ID {global_today['guild_id']}"
            checks.append(f"🌍 Pole en: {other_name}")
            can_pole = False
        
        embed.add_field(
            name="🔍 Verificaciones",
            value="\n".join(checks),
            inline=True
        )
        
        # Veredicto
        verdict = "✅ **PUEDE** hacer pole" if can_pole else "❌ **NO PUEDE** hacer pole"
        embed.add_field(name="🎯 Veredicto", value=verdict, inline=True)
        
        # ========== SECCIÓN 4: INFO TÉCNICA (debug) ==========
        if user_data:
            last_pole_date_db = user_data.get('last_pole_date', 'NULL')
            embed.set_footer(text=f"last_pole_date en BD: {last_pole_date_db} | Miembros server: {len([m for m in interaction.guild.members if not m.bot])}")
        
        await interaction.followup.send(embed=embed, ephemeral=True)

    # ====== RESTAURAR RACHA (si se perdió por error) ======
    @debug.command(name="restore_streak", description="Restaurar racha de un usuario a su mejor racha histórica")
    @app_commands.describe(usuario="Usuario al que restaurar la racha")
    @debug_only()
    async def restore_streak(self, interaction: discord.Interaction, usuario: discord.Member):
        """Restaura la racha actual al valor de la mejor racha histórica"""
        if not interaction.guild:
            await interaction.response.send_message("❌ Solo en servidores.", ephemeral=True)
            return
        
        gid = interaction.guild.id
        user_data = self.db.get_user(usuario.id, gid)
        
        if not user_data:
            await interaction.response.send_message(
                f"❌ {usuario.mention} no tiene datos en este servidor.",
                ephemeral=True
            )
            return
        
        old_streak = user_data.get('current_streak', 0)
        best_streak = user_data.get('best_streak', 0)
        
        if best_streak == 0:
            await interaction.response.send_message(
                f"❌ {usuario.mention} no tiene mejor racha registrada.",
                ephemeral=True
            )
            return
        
        # Restaurar y actualizar last_pole_date a ayer para que no se resetee
        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
        self.db.update_user(usuario.id, gid, current_streak=best_streak, last_pole_date=yesterday)
        
        embed = discord.Embed(
            title="♻️ Racha Restaurada",
            description=f"{usuario.mention} ha recuperado su mejor racha",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.add_field(name="🔥 Racha", value=f"{old_streak} → **{best_streak}**", inline=True)
        embed.add_field(name="📅 Último Pole", value=f"Ajustado a: {yesterday}", inline=True)
        embed.set_footer(text="⚠️ El usuario debe hacer pole hoy para mantener la racha")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ====== ESTADO DEL SERVIDOR ======
    @debug.command(name="server_status", description="Ver configuración del servidor y estado del pole")
    @debug_only()
    async def server_status(self, interaction: discord.Interaction):
        """Ver toda la configuración del servidor para diagnosticar"""
        if not interaction.guild:
            await interaction.response.send_message("❌ Solo en servidores.", ephemeral=True)
            return
        
        gid = interaction.guild.id
        config = self.db.get_server_config(gid)
        
        embed = discord.Embed(
            title=f"🏠 Estado del Servidor",
            description=f"**{interaction.guild.name}**",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        if not config:
            embed.add_field(
                name="❌ Sin Configuración",
                value="Este servidor no tiene configuración de pole.\nUsa `/settings` para configurar.",
                inline=False
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # Canal de pole
        pole_channel_id = config.get('pole_channel_id')
        if pole_channel_id:
            channel = interaction.guild.get_channel(pole_channel_id)
            channel_status = f"<#{pole_channel_id}>" if channel else f"❌ Canal eliminado (ID: {pole_channel_id})"
        else:
            channel_status = "❌ No configurado"
        embed.add_field(name="📢 Canal de Pole", value=channel_status, inline=True)
        
        # Hora de apertura
        daily_time = config.get('daily_pole_time')
        if daily_time:
            embed.add_field(name="⏰ Hora de Hoy", value=f"`{daily_time}`", inline=True)
        else:
            embed.add_field(name="⏰ Hora de Hoy", value="❌ No generada", inline=True)
        
        # Rango horario
        range_start = config.get('pole_range_start', 8)
        range_end = config.get('pole_range_end', 20)
        embed.add_field(name="🕐 Rango", value=f"{range_start}:00 - {range_end}:00", inline=True)
        
        # Notificaciones
        notify_opening = config.get('notify_opening', True)
        notify_winner = config.get('notify_winner', True)
        embed.add_field(
            name="🔔 Notificaciones",
            value=f"Apertura: {'✅' if notify_opening else '❌'} | Ganador: {'✅' if notify_winner else '❌'}",
            inline=True
        )
        
        # Rol de ping
        ping_role_id = config.get('ping_role_id')
        ping_mode = config.get('ping_mode', 'none')
        if ping_role_id and ping_mode != 'none':
            role = interaction.guild.get_role(ping_role_id)
            role_status = f"@{role.name}" if role else f"❌ Rol eliminado (ID: {ping_role_id})"
        else:
            role_status = "Ninguno"
        embed.add_field(name="📣 Rol de Ping", value=f"{role_status} (modo: {ping_mode})", inline=True)
        
        # Estado actual del pole
        now = datetime.now()
        today_str = now.strftime('%Y-%m-%d')
        
        if daily_time:
            try:
                h, m, s = [int(x) for x in str(daily_time).split(':')]
                opening = datetime(now.year, now.month, now.day, h, m, s)
                
                if now < opening:
                    time_until = opening - now
                    hours, remainder = divmod(int(time_until.total_seconds()), 3600)
                    minutes = remainder // 60
                    pole_status = f"⏳ Abre en {hours}h {minutes}m"
                else:
                    time_since = now - opening
                    hours, remainder = divmod(int(time_since.total_seconds()), 3600)
                    minutes = remainder // 60
                    
                    # Ver si alguien ya lo hizo
                    poles_today = self.db.get_poles_today(gid)
                    if poles_today:
                        winner_id = poles_today[0].get('user_id')
                        if winner_id:
                            winner = interaction.guild.get_member(int(winner_id))
                            winner_name = winner.display_name if winner else f"ID {winner_id}"
                        else:
                            winner_name = "Desconocido"
                        pole_status = f"✅ Ganado por **{winner_name}** hace {hours}h {minutes}m"
                    else:
                        pole_status = f"🟢 ABIERTO hace {hours}h {minutes}m - ¡Nadie lo ha hecho!"
            except:
                pole_status = "⚠️ Error parseando hora"
        else:
            pole_status = "❌ Sin hora configurada"
        
        embed.add_field(name="🏁 Estado del Pole", value=pole_status, inline=False)
        
        # Estadísticas del servidor
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM users WHERE guild_id = ?', (gid,))
            total_users = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM poles WHERE guild_id = ?', (gid,))
            total_poles = cursor.fetchone()[0]
        
        embed.add_field(name="👥 Usuarios", value=str(total_users), inline=True)
        embed.add_field(name="🏁 Poles Totales", value=str(total_poles), inline=True)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ====== BACKUP Y RESTORE DE BASE DE DATOS ======
    @debug.command(name="backup_db", description="Crea una copia de seguridad de la base de datos")
    @debug_only()
    async def backup_database(self, interaction: discord.Interaction):
        """Crea un backup timestamped de la base de datos"""
        await interaction.response.defer(ephemeral=True)
        
        import shutil
        
        try:
            # Ruta de la BD original
            db_path = "data/pole_bot.db"
            if not os.path.exists(db_path):
                await interaction.followup.send("❌ No se encuentra la base de datos en `data/pole_bot.db`")
                return
            
            # Crear carpeta de backups si no existe
            backup_dir = "data/backups"
            os.makedirs(backup_dir, exist_ok=True)
            
            # Timestamp para el backup
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_name = f"pole_bot_backup_{timestamp}.db"
            backup_path = os.path.join(backup_dir, backup_name)
            
            # Copiar archivo
            shutil.copy2(db_path, backup_path)
            
            # Verificar tamaño
            original_size = os.path.getsize(db_path)
            backup_size = os.path.getsize(backup_path)
            
            if original_size != backup_size:
                await interaction.followup.send(
                    f"⚠️ Backup creado pero con tamaño diferente:\n"
                    f"Original: {original_size} bytes\n"
                    f"Backup: {backup_size} bytes"
                )
                return
            
            # Éxito
            size_mb = original_size / (1024 * 1024)
            embed = discord.Embed(
                title="✅ Backup Creado",
                description=f"Copia de seguridad guardada correctamente",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(name="📁 Archivo", value=f"`{backup_name}`", inline=False)
            embed.add_field(name="📍 Ubicación", value=f"`{backup_path}`", inline=False)
            embed.add_field(name="💾 Tamaño", value=f"{size_mb:.2f} MB", inline=True)
            
            # Listar backups existentes
            backups = sorted([f for f in os.listdir(backup_dir) if f.endswith('.db')])
            if len(backups) > 1:
                embed.add_field(
                    name="📚 Backups Totales", 
                    value=f"{len(backups)} archivos en `{backup_dir}/`", 
                    inline=True
                )
            
            await interaction.followup.send(embed=embed)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error al crear backup: {str(e)}")

    @debug.command(name="list_backups", description="Lista todas las copias de seguridad disponibles")
    @debug_only()
    async def list_backups(self, interaction: discord.Interaction):
        """Muestra todos los backups disponibles"""
        backup_dir = "data/backups"
        
        if not os.path.exists(backup_dir):
            await interaction.response.send_message(
                "📂 No hay carpeta de backups. Crea uno con `/debug backup_db`",
                ephemeral=True
            )
            return
        
        backups = sorted([f for f in os.listdir(backup_dir) if f.endswith('.db')], reverse=True)
        
        if not backups:
            await interaction.response.send_message(
                "📂 No hay backups guardados. Crea uno con `/debug backup_db`",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="📚 Backups Disponibles",
            description=f"Se encontraron {len(backups)} copias de seguridad",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Mostrar hasta 10 backups más recientes
        for i, backup in enumerate(backups[:10], 1):
            backup_path = os.path.join(backup_dir, backup)
            size = os.path.getsize(backup_path) / (1024 * 1024)  # MB
            modified = datetime.fromtimestamp(os.path.getmtime(backup_path))
            
            # Parsear timestamp del nombre
            try:
                timestamp_str = backup.replace('pole_bot_backup_', '').replace('.db', '')
                date_str = f"{timestamp_str[:4]}-{timestamp_str[4:6]}-{timestamp_str[6:8]} {timestamp_str[9:11]}:{timestamp_str[11:13]}:{timestamp_str[13:15]}"
            except:
                date_str = modified.strftime('%Y-%m-%d %H:%M:%S')
            
            embed.add_field(
                name=f"{i}. {backup}",
                value=f"📅 {date_str} • 💾 {size:.2f} MB",
                inline=False
            )
        
        if len(backups) > 10:
            embed.set_footer(text=f"Mostrando 10 de {len(backups)} backups. Los más antiguos no se muestran.")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @debug.command(name="restore_db", description="⚠️ PELIGRO: Restaura la base de datos desde un backup")
    @debug_only()
    async def restore_database(
        self, 
        interaction: discord.Interaction,
        backup_file: str
    ):
        """
        Restaura la BD desde un backup.
        CUIDADO: Esto sobrescribe la base de datos actual.
        """
        # Vista de confirmación
        class RestoreConfirmView(discord.ui.View):
            def __init__(self, cog: 'DebugCog', backup_file: str):
                super().__init__(timeout=60)
                self.cog = cog
                self.backup_file = backup_file
                self.value = None

            @discord.ui.button(label="✅ SÍ, RESTAURAR", style=discord.ButtonStyle.danger)
            async def confirm(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                await button_interaction.response.defer()
                await self.perform_restore(button_interaction)
                self.value = True
                self.stop()

            @discord.ui.button(label="❌ Cancelar", style=discord.ButtonStyle.secondary)
            async def cancel(self, button_interaction: discord.Interaction, button: discord.ui.Button):
                await button_interaction.response.send_message("❌ Restauración cancelada.", ephemeral=True)
                self.value = False
                self.stop()

            async def perform_restore(self, button_interaction: discord.Interaction):
                """Ejecuta la restauración"""
                import shutil
                
                try:
                    # Rutas
                    backup_dir = "data/backups"
                    backup_path = os.path.join(backup_dir, self.backup_file)
                    db_path = "data/pole_bot.db"
                    
                    # Verificar que existe el backup
                    if not os.path.exists(backup_path):
                        await button_interaction.followup.send(
                            f"❌ No se encuentra el backup: `{self.backup_file}`"
                        )
                        return
                    
                    # PASO 1: Crear backup de la BD actual antes de sobrescribir
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    pre_restore_backup = os.path.join(backup_dir, f"pole_bot_pre_restore_{timestamp}.db")
                    shutil.copy2(db_path, pre_restore_backup)
                    
                    # PASO 2: Sobrescribir con el backup seleccionado
                    shutil.copy2(backup_path, db_path)
                    
                    # PASO 3: Verificar integridad
                    restored_size = os.path.getsize(db_path)
                    backup_size = os.path.getsize(backup_path)
                    
                    if restored_size != backup_size:
                        # Rollback
                        shutil.copy2(pre_restore_backup, db_path)
                        await button_interaction.followup.send(
                            "❌ Error: Tamaños no coinciden. Restauración revertida."
                        )
                        return
                    
                    # PASO 4: Health check de la BD restaurada
                    try:
                        with self.cog.db.get_connection() as conn:
                            cursor = conn.cursor()
                            cursor.execute("PRAGMA integrity_check")
                            result = cursor.fetchone()
                            if result[0] != 'ok':
                                # Rollback
                                shutil.copy2(pre_restore_backup, db_path)
                                await button_interaction.followup.send(
                                    f"❌ BD restaurada falló integrity check: {result[0]}\n"
                                    "Restauración revertida."
                                )
                                return
                    except Exception as e:
                        # Rollback
                        shutil.copy2(pre_restore_backup, db_path)
                        await button_interaction.followup.send(
                            f"❌ Error verificando BD restaurada: {str(e)}\n"
                            "Restauración revertida."
                        )
                        return
                    
                    # ÉXITO
                    size_mb = restored_size / (1024 * 1024)
                    embed = discord.Embed(
                        title="✅ Base de Datos Restaurada",
                        description="La restauración se completó correctamente",
                        color=discord.Color.green(),
                        timestamp=datetime.now()
                    )
                    embed.add_field(name="📁 Backup Restaurado", value=f"`{self.backup_file}`", inline=False)
                    embed.add_field(name="💾 Tamaño", value=f"{size_mb:.2f} MB", inline=True)
                    embed.add_field(name="🔒 Backup de Seguridad", value=f"`{os.path.basename(pre_restore_backup)}`", inline=False)
                    embed.add_field(
                        name="⚠️ Siguiente Paso",
                        value="**REINICIA EL BOT** para que los cambios surtan efecto completamente.",
                        inline=False
                    )
                    
                    await button_interaction.followup.send(embed=embed)
                    
                except Exception as e:
                    await button_interaction.followup.send(f"❌ Error durante restauración: {str(e)}")

        # Validar que el archivo existe
        backup_dir = "data/backups"
        backup_path = os.path.join(backup_dir, backup_file)
        
        if not os.path.exists(backup_path):
            await interaction.response.send_message(
                f"❌ No se encuentra el backup: `{backup_file}`\n"
                f"Usa `/debug list_backups` para ver backups disponibles.",
                ephemeral=True
            )
            return
        
        # Información del backup
        backup_size = os.path.getsize(backup_path) / (1024 * 1024)
        backup_date = datetime.fromtimestamp(os.path.getmtime(backup_path))
        
        # Advertencia de confirmación
        embed = discord.Embed(
            title="⚠️ ADVERTENCIA: Restauración de Base de Datos",
            description=(
                "**Estás a punto de SOBRESCRIBIR la base de datos actual.**\n\n"
                "Esto significa:\n"
                "• ❌ Se perderán todos los poles/stats desde este backup\n"
                "• ❌ No se puede deshacer (excepto con otro backup)\n"
                "• ✅ Se creará un backup automático de la BD actual antes de restaurar\n\n"
                "**¿Estás SEGURO de que quieres continuar?**"
            ),
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        embed.add_field(name="📁 Backup a Restaurar", value=f"`{backup_file}`", inline=False)
        embed.add_field(name="📅 Fecha del Backup", value=backup_date.strftime('%Y-%m-%d %H:%M:%S'), inline=True)
        embed.add_field(name="💾 Tamaño", value=f"{backup_size:.2f} MB", inline=True)
        
        view = RestoreConfirmView(self, backup_file)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(DebugCog(bot))
