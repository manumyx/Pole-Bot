"""
Cog de Pole - Funcionalidad principal del bot
Maneja el sistema de pole diario con detección automática
"""
import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.ui import View, Select, Button, Modal, TextInput
from datetime import datetime, time, timedelta
import re
import asyncio
import sqlite3
from typing import Optional, Dict, Any

from utils.database import Database
from utils.scoring import (
    calculate_points, classify_delay, get_pole_emoji,
    get_pole_name, update_streak, get_rank_info, get_streak_multiplier,
    check_quota_available
)

# Emoji de fuego personalizado (usar en todo el bot)
FIRE = "<a:fire:1440018375144374302>"
GRAY_FIRE = "<:gray_fire:1445324596751503485>"

# ==================== VIEWS PARA SETTINGS ====================

class ChannelSelectView(View):
    """Vista para seleccionar canal"""
    def __init__(self, db: Database, guild_id: int, original_interaction: discord.Interaction):
        super().__init__(timeout=60)
        self.db = db
        self.guild_id = guild_id
        self.original_interaction = original_interaction
        
    @discord.ui.select(cls=discord.ui.ChannelSelect, placeholder="Selecciona el canal de pole", channel_types=[discord.ChannelType.text])
    async def channel_select(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        channel = select.values[0]
        self.db.init_server(self.guild_id, channel.id)
        self.db.update_server_config(self.guild_id, pole_channel_id=channel.id)
        await interaction.response.send_message(f"✅ Canal de pole configurado: {channel.mention}", ephemeral=True)
        self.stop()


class RoleSelectView(View):
    """Vista para seleccionar rol de ping"""
    def __init__(self, db: Database, guild_id: int):
        super().__init__(timeout=60)
        self.db = db
        self.guild_id = guild_id
        
    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder="Selecciona el rol para pingear")
    async def role_select(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        role = select.values[0]
        self.db.update_server_config(self.guild_id, ping_role_id=role.id, ping_mode='role')
        await interaction.response.send_message(f"✅ Rol de ping configurado: {role.mention}", ephemeral=True)
        self.stop()


class RepresentSelectView(View):
    """Vista para cambiar representación de servidor"""
    def __init__(self, db: Database, user_id: int, bot, mutual_guilds: list, current_guild_id: Optional[int]):
        super().__init__(timeout=60)
        self.db = db
        self.user_id = user_id
        self.bot = bot
        
        # Crear select con opciones
        options = []
        for guild in mutual_guilds[:25]:  # Discord limit
            options.append(
                discord.SelectOption(
                    label=guild.name,
                    value=str(guild.id),
                    description=f"ID: {guild.id}",
                    default=(current_guild_id == guild.id if current_guild_id else False)
                )
            )
        
        select = discord.ui.Select(
            placeholder="Selecciona un servidor...",
            options=options
        )
        
        async def select_callback(interaction: discord.Interaction):
            new_guild_id = int(select.values[0])
            self.db.set_represented_guild(self.user_id, new_guild_id)
            new_guild = self.bot.get_guild(new_guild_id)
            guild_name = new_guild.name if new_guild else f"ID {new_guild_id}"
            await interaction.response.send_message(
                f"✅ Ahora representas a **{guild_name}** en los rankings globales",
                ephemeral=True
            )
            self.stop()
        
        select.callback = select_callback
        self.add_item(select)


class SettingsView(View):
    """Vista interactiva para configurar el bot (opciones según permisos)"""
    def __init__(self, db: Database, guild_id: int, requester: discord.Member):
        super().__init__(timeout=300)
        self.db = db
        self.guild_id = guild_id
        self.requester = requester
        self.is_admin = requester.guild_permissions.administrator if requester and isinstance(requester, discord.Member) else False
        self._build_dynamic_select()
    
    def _build_dynamic_select(self):
        options = []
        if self.is_admin:
            options.extend([
                discord.SelectOption(label="Canal de Pole", description="Cambiar el canal donde se hace pole", emoji="📺", value="channel"),
                discord.SelectOption(label="Rol de Ping", description="Configurar rol para notificaciones", emoji="🔔", value="ping_role"),
                discord.SelectOption(label="Quitar Rol de Ping", description="Eliminar rol de ping", emoji="🚫", value="clear_ping"),
                discord.SelectOption(label="Toggle Notif. Apertura", description="Activar/Desactivar aviso de apertura", emoji="📢", value="notify_opening"),
                discord.SelectOption(label="Toggle Notif. Ganador", description="Activar/Desactivar aviso de ganador", emoji="🏆", value="notify_winner"),
            ])
        # Opción disponible para todos
        options.append(discord.SelectOption(label="Cambiar Representación", description="Servidor que representas en el ranking global", emoji="🏳️", value="represent"))
        
        select = discord.ui.Select(placeholder="Selecciona qué configurar...", options=options)
        
        async def on_select(interaction: discord.Interaction):
            value = select.values[0]
            # Acciones restringidas a admins
            admin_only = {"channel", "ping_role", "clear_ping", "notify_opening", "notify_winner"}
            if value in admin_only and not self.is_admin:
                await interaction.response.send_message("❌ Solo administradores pueden cambiar esta opción.", ephemeral=True)
                return
            
            if value == "channel":
                view = ChannelSelectView(self.db, self.guild_id, interaction)
                await interaction.response.send_message("📺 Selecciona el canal de pole:", view=view, ephemeral=True)
            elif value == "ping_role":
                view = RoleSelectView(self.db, self.guild_id)
                await interaction.response.send_message("🔔 Selecciona el rol para pingear:", view=view, ephemeral=True)
            elif value == "clear_ping":
                self.db.update_server_config(self.guild_id, ping_role_id=None, ping_mode='none')
                await interaction.response.send_message("✅ Rol de ping eliminado", ephemeral=True)
            elif value == "notify_opening":
                cfg = self.db.get_server_config(self.guild_id) or {}
                new_val = 0 if cfg.get('notify_opening', 1) else 1
                self.db.update_server_config(self.guild_id, notify_opening=new_val)
                estado = "activado" if new_val else "desactivado"
                await interaction.response.send_message(f"✅ Notificaciones de apertura {estado}", ephemeral=True)
            elif value == "notify_winner":
                cfg = self.db.get_server_config(self.guild_id) or {}
                new_val = 0 if cfg.get('notify_winner', 1) else 1
                self.db.update_server_config(self.guild_id, notify_winner=new_val)
                estado = "activado" if new_val else "desactivado"
                await interaction.response.send_message(f"✅ Notificaciones de ganador {estado}", ephemeral=True)
            elif value == "represent":
                # Obtener servidor actual representado
                current_guild_id = self.db.get_represented_guild(interaction.user.id)
                
                # Obtener lista de servidores donde el usuario y el bot están presentes
                bot = interaction.client
                mutual_guilds = []
                for guild in bot.guilds:
                    member = guild.get_member(interaction.user.id)
                    if member:
                        mutual_guilds.append(guild)
                
                if not mutual_guilds:
                    await interaction.response.send_message(
                        "❌ No estás en ningún servidor donde yo también esté.",
                        ephemeral=True
                    )
                    return
                
                # Crear embed con info actual
                embed = discord.Embed(
                    title="🏳️ Cambiar Representación",
                    description="Selecciona el servidor que quieres representar en los rankings globales.",
                    color=discord.Color.blue()
                )
                
                if current_guild_id:
                    current_guild = bot.get_guild(current_guild_id)
                    current_name = current_guild.name if current_guild else f"ID {current_guild_id}"
                    embed.add_field(
                        name="📍 Actualmente representas",
                        value=f"**{current_name}**",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name="📍 Actualmente representas",
                        value="*Ningún servidor configurado*",
                        inline=False
                    )
                
                view = RepresentSelectView(self.db, interaction.user.id, bot, mutual_guilds, current_guild_id)
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
        select.callback = on_select
        self.add_item(select)
        
    def create_embed(self, guild: discord.Guild) -> discord.Embed:
        """Crear embed con configuración actual"""
        cfg = self.db.get_server_config(self.guild_id) or {}
        
        embed = discord.Embed(
            title="⚙️ Configuración del Pole Bot",
            description="Selecciona las opciones que quieres modificar usando el menú desplegable",
            color=discord.Color.blurple()
        )
        
        # Canal de pole
        channel_id = cfg.get('pole_channel_id')
        channel_value = f"<#{channel_id}>" if channel_id else "❌ No configurado"
        embed.add_field(name="📺 Canal de Pole", value=channel_value, inline=False)
        
        # Servidor representado (personal del usuario)
        represented_guild_id = self.db.get_represented_guild(self.requester.id)
        if represented_guild_id:
            represented_guild = self.requester._state._get_guild(represented_guild_id)
            if represented_guild:
                represented_value = f"🏳️ **{represented_guild.name}**"
            else:
                represented_value = f"🏳️ *Servidor ID {represented_guild_id}*"
        else:
            represented_value = "❌ No configurado"
        embed.add_field(name="🌍 Servidor Representado", value=represented_value, inline=False)
        
        # Rol de ping
        role_id = cfg.get('ping_role_id')
        role_value = f"<@&{role_id}>" if role_id else "❌ No configurado"
        embed.add_field(name="🔔 Rol de Ping", value=role_value, inline=True)
        
        # Notificaciones
        notify_opening = "✅ Activo" if cfg.get('notify_opening', 1) else "❌ Desactivado"
        notify_winner = "✅ Activo" if cfg.get('notify_winner', 1) else "❌ Desactivado"
        embed.add_field(name="📢 Notif. Apertura", value=notify_opening, inline=True)
        embed.add_field(name="🏆 Notif. Ganador", value=notify_winner, inline=True)
        
        embed.set_footer(text="Los cambios se aplican inmediatamente")
        
        return embed
    
    @discord.ui.button(label="Actualizar Vista", style=discord.ButtonStyle.secondary, emoji="🔄")
    async def refresh_button(self, interaction: discord.Interaction, button: Button):
        """Refrescar el embed con la configuración actual"""
        if interaction.guild:
            new_embed = self.create_embed(interaction.guild)
            await interaction.response.edit_message(embed=new_embed, view=self)
        else:
            await interaction.response.send_message("❌ Error al actualizar", ephemeral=True)
    


class PoleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
        self._notified_openings = set()  # Track already sent notifications (guild_id, date)
        self._scheduled_notifications = {}  # guild_id -> asyncio.Task
        self._midnight_summaries_sent = set()  # Track midnight summaries (guild_id, date)
        self._startup_check_done = False  # Flag para evitar doble ejecución
        
        # Iniciar tareas programadas v1.0
        self.daily_pole_generator.start()  # type: ignore[attr-defined]
        self.midnight_summary_check.start()  # type: ignore[attr-defined]
        self.opening_notification_watcher.start()  # type: ignore[attr-defined]
        # Programar notificaciones exactas para hoy al iniciar
        asyncio.create_task(self.schedule_all_today_notifications())
        
        print("✅ Pole Cog inicializado")
    
    @commands.Cog.listener()
    async def on_ready(self):
        """
        Sistema de robustez/failsafe al iniciar o reconectar el bot.
        Detecta y corrige problemas causados por outages:
        1. Genera hora de apertura si falta para hoy
        2. Resetea rachas perdidas si hubo outage durante la apertura
        3. Envía resumen de medianoche si se perdió
        """
        if self._startup_check_done:
            return  # Evitar múltiples ejecuciones en reconexiones
        
        self._startup_check_done = True
        print("🔄 Ejecutando verificación de robustez post-inicio...")
        
        await self._run_startup_failsafe()
    
    async def cog_unload(self) -> None:
        """Detener tareas cuando se descarga el cog"""
        self.daily_pole_generator.cancel()  # type: ignore[attr-defined]
        self.midnight_summary_check.cancel()  # type: ignore[attr-defined]
        self.opening_notification_watcher.cancel()  # type: ignore[attr-defined]
        # Cancelar tareas programadas por servidor
        for task in list(self._scheduled_notifications.values()):
            try:
                task.cancel()
            except:
                pass

    # ==================== SISTEMA DE ROBUSTEZ/FAILSAFE ====================
    
    async def _run_startup_failsafe(self):
        """
        Sistema de recuperación automática tras outage o reinicio.
        Se ejecuta una vez en on_ready.
        """
        import random
        now = datetime.now()
        today_str = now.strftime('%Y-%m-%d')
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT guild_id, pole_channel_id, daily_pole_time, notify_opening, ping_role_id, ping_mode FROM servers WHERE pole_channel_id IS NOT NULL')
            servers = cursor.fetchall()
        
        for server in servers:
            guild_id = server['guild_id']
            channel_id = server['pole_channel_id']
            daily_time = server['daily_pole_time']
            
            guild = self.bot.get_guild(guild_id)
            if not guild:
                continue
            
            channel = guild.get_channel(channel_id)
            if not channel:
                continue
            
            print(f"🔍 [Failsafe] Verificando guild {guild_id}...")
            
            # ========== CHECK 1: ¿Hay hora de apertura para hoy? ==========
            if not daily_time:
                # Generar hora aleatoria para hoy
                random_hour = random.randint(0, 23)
                random_minute = random.randint(0, 59)
                time_str = f"{random_hour:02d}:{random_minute:02d}:00"
                self.db.set_daily_pole_time(guild_id, time_str)
                daily_time = time_str
                print(f"   ⚠️ Sin hora configurada → generada: {time_str}")
            
            # Parsear hora de apertura
            try:
                h, m, s = [int(x) for x in str(daily_time).split(':')]
                opening_time = datetime(now.year, now.month, now.day, h, m, s)
            except Exception as e:
                print(f"   ❌ Error parseando hora: {e}")
                continue
            
            # ========== CHECK 2: ¿Se perdió la notificación de apertura? ==========
            # Verificar si la hora de apertura ya pasó
            if now > opening_time:
                notif_key = (guild_id, today_str)
                
                # Calcular cuánto tiempo pasó desde la apertura
                minutes_since_opening = (now - opening_time).total_seconds() / 60
                
                # Si ya notificamos o pasó demasiado tiempo, no hacer nada
                if notif_key in self._notified_openings:
                    print(f"   ✅ Notificación ya enviada hoy")
                elif minutes_since_opening > 60:
                    # Marcar como "enviado" para evitar reintentos
                    self._notified_openings.add(notif_key)
                    print(f"   ⚠️ Notificación omitida (>{int(minutes_since_opening)}m tarde)")
                else:
                    # Verificar si ya hay poles hoy
                    today_poles = self.db.get_poles_today(guild_id)
                    
                    if today_poles:
                        # Ya hay poles = el sistema funcionó, la gente se enteró
                        # NO enviar notificación, solo marcar como notificado
                        self._notified_openings.add(notif_key)
                        print(f"   ✅ Ya hay {len(today_poles)} poles hoy - no se requiere notificación")
                    else:
                        # Sin poles = posible outage, enviar notificación de recuperación
                        # PERO: Solo resetear rachas si estamos CERCA de la hora de apertura
                        # Si pasó mucho tiempo, las rachas ya se resetearon o están correctas
                        try:
                            # Solo resetear rachas si estamos en ventana razonable (< 30 min desde apertura)
                            # Esto evita reseteos incorrectos por outages largos
                            if minutes_since_opening < 30:
                                await self._reset_lost_streaks_before_opening(guild_id, channel_id)
                            
                            embed = discord.Embed(
                                title="🔔 POLE ABIERTO (Recuperación)",
                                description=(
                                    f"⚠️ El bot estuvo offline durante la apertura programada.\n"
                                    f"Escribe **pole** ahora para ganar puntos 🏁"
                                ),
                                color=discord.Color.orange(),
                                timestamp=now
                            )
                            embed.set_footer(text=f"Apertura original: {daily_time}")
                            
                            # Ping si está configurado
                            content = None
                            if server['ping_mode'] == 'role' and server['ping_role_id']:
                                role = guild.get_role(server['ping_role_id'])
                                if role:
                                    content = f"{role.mention}"
                            
                            await channel.send(content=content, embed=embed)
                            self._notified_openings.add(notif_key)
                            print(f"   ✅ Notificación de recuperación enviada ({int(minutes_since_opening)}m tarde)")
                        except Exception as e:
                            print(f"   ❌ Error enviando notificación de recuperación: {e}")
            
            # ========== CHECK 3: ¿Se perdió el resumen de medianoche? ==========
            # Si es después de las 00:15 y no se envió resumen hoy
            if now.hour == 0 and now.minute < 30:
                summary_key = (guild_id, today_str)
                if summary_key not in self._midnight_summaries_sent:
                    # Verificar si hubo poles ayer
                    yesterday = (now - timedelta(days=1)).strftime('%Y-%m-%d')
                    with self.db.get_connection() as conn:
                        cursor = conn.cursor()
                        cursor.execute('''
                            SELECT COUNT(*) FROM poles
                            WHERE guild_id = ? AND (pole_date = ? OR (pole_date IS NULL AND DATE(created_at) = ?))
                        ''', (guild_id, yesterday, yesterday))
                        yesterday_count = cursor.fetchone()[0]
                    
                    if yesterday_count > 0:
                        print(f"   ⚠️ Resumen de medianoche no enviado, enviando ahora...")
                        try:
                            await self.send_midnight_summary(guild_id, channel_id)
                            self._midnight_summaries_sent.add(summary_key)
                            print(f"   ✅ Resumen de medianoche enviado")
                        except Exception as e:
                            print(f"   ❌ Error enviando resumen: {e}")
        
        # Reprogramar notificaciones para hoy
        await self.schedule_all_today_notifications()
        print("✅ Verificación de robustez completada")

    # ==================== HELPERS ====================

    def _get_or_create_user_data(self, guild_id: int, member: discord.abc.User) -> dict:
        """Obtiene los datos del usuario, creándolo si no existe."""
        user = self.db.get_user(member.id, guild_id)
        if not user:
            self.db.create_user(member.id, guild_id, member.name)
            user = self.db.get_user(member.id, guild_id)
        # Coaccionar a dict y garantizar claves con valores por defecto
        # NOTA: total_points y total_poles se calculan dinámicamente en get_user() desde season_stats
        defaults = {
            'total_points': 0.0,  # Calculado dinámicamente desde season_stats
            'total_poles': 0,     # Calculado dinámicamente desde season_stats
            'critical_poles': 0,
            'fast_poles': 0,
            'normal_poles': 0,
            'marranero_poles': 0,
            'current_streak': 0,
            'best_streak': 0,
            'last_pole_date': None,
        }
        base = dict(user) if user else {}
        for k, v in defaults.items():
            if k not in base or base[k] is None:
                base[k] = v
        return base
    
    # ==================== DETECCIÓN DE POLES ====================
    
    async def _handle_bot_mention(self, message: discord.Message):
        """
        Responder cuando mencionan al bot con palabras clave sobre el pole.
        Respuestas vacilones SIN revelar la hora. Puro vacile.
        """
        import random
        
        guild = message.guild
        if not guild:
            return
        
        server_config = self.db.get_server_config(guild.id)
        daily_time = server_config.get('daily_pole_time') if server_config else None
        pole_channel_id = server_config.get('pole_channel_id') if server_config else None
        
        now = datetime.now()
        
        # Si no hay configuración, ignorar silenciosamente
        if not pole_channel_id or not daily_time:
            return
        
        # Parsear hora de apertura
        try:
            h, m, s = [int(x) for x in str(daily_time).split(':')]
            opening_time = datetime(now.year, now.month, now.day, h, m, s)
        except:
            return
        
        # Ver si ya abrió o no
        if now < opening_time:
            # Aún no abre - NO decimos la hora, solo vacilamos
            responses = [
                "Aún no toca crack, sé que no vas a llegar a tiempo",
                "Tranqui bro, cuando abra te enteras... o no 🧑‍🦯",
                "El que pregunta, no llega. Así funciona esto",
                "Bro preguntando la hora como si fuera a llegar",
            ]
            embed = discord.Embed(
                description=random.choice(responses),
                color=discord.Color.gold()
            )
            embed.set_image(url="https://files.catbox.moe/exkjzt.webp")
            await message.reply(embed=embed)
        else:
            # Ya abrió - vacilar con "mañana"
            responses = [
                "Mañana",
                "mañana bro",
                "Mañana será",
                "F en el chat. Mañana",
            ]
            embed = discord.Embed(
                description=random.choice(responses),
                color=discord.Color.red()
            )
            embed.set_image(url="https://files.catbox.moe/b2k99x.jpg")
            await message.reply(embed=embed)
    
    def is_valid_pole(self, content: str) -> bool:
        """
        Verificar si un mensaje es un pole válido
        Debe ser EXACTAMENTE 'pole' (case insensitive, sin espacios extra)
        """
        # Eliminar espacios al inicio y final
        content = content.strip()
        
        # Verificar que sea exactamente "pole" (case insensitive)
        return content.lower() == 'pole'
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Detectar mensajes de 'pole' y procesarlos.
        También responde a menciones al bot con palabras clave.
        """
        try:
            # Ignorar bots
            if message.author.bot:
                return
            
            # Ignorar si no está en un servidor
            if not message.guild:
                return
            guild = message.guild
            
            # Detectar menciones al bot con palabras clave
            if self.bot.user and self.bot.user.mentioned_in(message):
                content_lower = message.content.lower()
                # Palabras clave que disparan respuesta
                keywords = ['pole', 'saca', 'abre', 'cuando', 'hora']
                if any(kw in content_lower for kw in keywords):
                    await self._handle_bot_mention(message)
                    return
            
            # Verificar si el mensaje es un pole válido
            if not self.is_valid_pole(message.content):
                return
        except Exception as e:
            print(f"❌ Error en verificaciones iniciales de on_message: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Obtener configuración del servidor (sin autoasignar canal)
        server_config = self.db.get_server_config(guild.id)
        if not server_config:
            # Inicializa entrada del servidor sin canal aún (placeholder 0)
            self.db.init_server(guild.id, 0)
            server_config = self.db.get_server_config(guild.id)
            if not server_config:
                server_config = {
                    'guild_id': guild.id,
                    'pole_channel_id': None,
                    'daily_pole_time': None,
                    'pole_range_start': 8,
                    'pole_range_end': 20,
                    'notify_opening': 1,
                    'notify_winner': 1,
                    'ping_role_id': None,
                    'ping_mode': 'none',
                    'migration_in_progress': 0,
                }
        
        # Verificar si hay migración en progreso
        if server_config.get('migration_in_progress', 0):
            try:
                await message.reply(
                    "⚠️ **Migración de temporada en progreso**\n\n"
                    "El sistema de poles está temporalmente deshabilitado mientras se migra a la nueva temporada.\n"
                    "Vuelve en unos minutos."
                )
            except:
                pass
            return
        
        # Verificar si el canal está configurado como canal de pole
        pole_channel_id = server_config['pole_channel_id']
        
        # Requiere canal explícito
        if not pole_channel_id:
            if isinstance(message.author, discord.Member) and message.author.guild_permissions.administrator:
                try:
                    await message.reply("⚙️ Configura primero el canal de pole con `/settings`.")
                except:
                    pass
            return
        if message.channel.id != pole_channel_id:
            return
        
        # Procesar el pole
        await self.process_pole(message)
    
    async def process_pole(self, message: discord.Message):
        """
        Procesar un pole válido y determinar tipo, puntos, etc.
        
        FLUJO DE VALIDACIÓN (orden importante):
        1. Verificar configuración del servidor
        2. Determinar si estamos en ventana de marranero o pole normal
        3. Verificar duplicados (ya hizo pole hoy/ayer según corresponda)
        4. Procesar y otorgar puntos
        """
        now = datetime.now()
        guild = message.guild
        if guild is None:
            return
        
        server_config = self.db.get_server_config(guild.id) or {}
        daily_time = server_config.get('daily_pole_time')
        
        # ========== PASO 1: Verificar configuración ==========
        if not daily_time:
            try:
                await message.reply("⚠️ No hay hora de pole configurada para hoy.")
            except:
                pass
            return

        # Parsear hora de apertura de hoy
        try:
            h, m, s = [int(x) for x in str(daily_time).split(':')]
        except Exception:
            try:
                await message.reply("⚠️ Config de hora diaria inválida. Contacta a un admin.")
            except:
                pass
            return
        
        opening_time_today = datetime(now.year, now.month, now.day, h, m, s)
        today_str = now.strftime('%Y-%m-%d')
        
        # ========== PASO 2: Determinar modo (marranero vs normal) ==========
        use_marranero = False
        opening_time = opening_time_today
        effective_date = today_str  # Fecha para la racha
        
        # Caso A: ANTES de la apertura de hoy
        if now < opening_time_today:
            # Ventana de marranero: desde apertura de ayer hasta apertura de hoy
            last_opening_str = self.db.get_last_pole_opening_time(guild.id)
            if last_opening_str:
                try:
                    last_h, last_m = [int(x) for x in last_opening_str.split(':')[:2]]
                    yesterday = now - timedelta(days=1)
                    opening_time_yesterday = datetime(yesterday.year, yesterday.month, yesterday.day, last_h, last_m, 0)
                    yesterday_str = yesterday.strftime('%Y-%m-%d')
                    
                    # ¿Ya hizo pole AYER? Si sí, no puede hacer marranero
                    user_did_pole_yesterday = self.db.user_has_pole_on_date(message.author.id, guild.id, yesterday_str)
                    
                    if not user_did_pole_yesterday:
                        # Puede hacer marranero
                        use_marranero = True
                        opening_time = opening_time_yesterday
                        effective_date = yesterday_str
                    else:
                        # Ya hizo pole ayer, tiene que esperar al de hoy
                        try:
                            await message.add_reaction('⏳')
                        except:
                            pass
                        try:
                            await message.reply("🧑‍🦯 Crack, ya hiciste tu pole ayer. Espera a que abra el de hoy.")
                        except:
                            pass
                        return
                except Exception:
                    # Si falla al parsear la hora de ayer, no se puede hacer marranero
                    self.db.increment_impatient_attempts(message.author.id, guild.id)
                    try:
                        await message.add_reaction('⏳')
                    except:
                        pass
                    try:
                        await message.reply("🧑‍🦯 Crack, aún no toca polear.")
                    except:
                        pass
                    return
            
            # Si no hay última hora registrada (primer día del servidor), no se puede hacer nada
            if not use_marranero:
                self.db.increment_impatient_attempts(message.author.id, guild.id)
                try:
                    await message.add_reaction('⏳')
                except:
                    pass
                try:
                    await message.reply("🧑‍🦯 Crack, aún no toca polear.")
                except:
                    pass
                return
        
        # Caso B: DESPUÉS de la apertura de hoy (pole normal)
        else:
            # ¿Ya hizo pole HOY en este servidor?
            user_pole_today = self.db.user_has_pole_on_date(message.author.id, guild.id, today_str)
            if user_pole_today:
                # Incrementar stat secreta de intentos impacientes
                self.db.increment_impatient_attempts(message.author.id, guild.id)
                try:
                    await message.add_reaction('🛑')
                except:
                    pass
                try:
                    embed = discord.Embed(
                        description="Bro, ya hiciste tu pole hoy aquí. Tranqui 🛑",
                        color=discord.Color.orange()
                    )
                    embed.set_image(url="https://i.imgflip.com/37dceb.jpg")
                    await message.reply(embed=embed)
                except:
                    pass
                return
        
        # ========== PASO 3: Verificación global (1 pole al día en cualquier servidor) ==========
        # Verificar que no haya hecho pole en la fecha efectiva (ayer para marranero, hoy para normal)
        # Esto asegura que solo puedas hacer 1 pole por día, sin importar el servidor
        global_pole = self.db.get_user_pole_on_date_global(message.author.id, effective_date)
        if global_pole and int(global_pole.get('guild_id', 0)) != guild.id:
            # Incrementar stat secreta de intentos impacientes
            self.db.increment_impatient_attempts(message.author.id, guild.id)
            prev_guild = self.bot.get_guild(int(global_pole['guild_id']))
            prev_name = prev_guild.name if prev_guild else f"ID {global_pole['guild_id']}"
            try:
                await message.add_reaction('🚫')
            except:
                pass
            try:
                await message.reply(
                    f"❌ Ya hiciste pole en otro servidor.\n"
                    f"Te vimos en **{prev_name}**; mañana más suerte."
                )
            except:
                pass
            return
        
        # ========== PASO 4: Procesar el pole ==========
        # Obtener poles del día para posición
        today_poles = self.db.get_poles_today(guild.id)
        position = len(today_poles) + 1

        # Calcular retraso y clasificar
        delay_minutes = int((now - opening_time).total_seconds() // 60)
        is_next_day = use_marranero  # Si es marranero, es "día siguiente"
        
        pole_type = classify_delay(delay_minutes, is_next_day)
        
        # ====== VERIFICAR CUOTAS (solo para critical y fast) ======
        if pole_type in ['critical', 'fast']:
            # Contar cuántos poles de este tipo ya se reclamaron hoy
            poles_of_type = sum(1 for p in today_poles if p.get('pole_type') == pole_type)
            
            # Contar JUGADORES ACTIVOS del servidor (usuarios que han hecho pole alguna vez)
            # NO contar total de miembros para evitar meta roto (ej: 80 miembros, 10 juegan)
            active_players = self.db.get_total_active_users(guild.id)
            
            # Verificar cuota
            has_quota, current, max_allowed = check_quota_available(pole_type, poles_of_type, active_players)
            
            if not has_quota:
                pole_name = get_pole_name(pole_type)
                try:
                    await message.add_reaction('⏱️')
                except:
                    pass
                try:
                    await message.reply(
                        f"⚠️ La cuota de **{pole_name}** está llena ({current}/{max_allowed}).\n"
                        f"Se te asignará la siguiente categoría disponible."
                    )
                except:
                    pass
                # Degradar a la siguiente categoría
                if pole_type == 'critical':
                    pole_type = 'fast'
                    # Verificar cuota de fast también
                    poles_of_type = sum(1 for p in today_poles if p.get('pole_type') == 'fast')
                    has_quota, current, max_allowed = check_quota_available('fast', poles_of_type, active_players)
                    if not has_quota:
                        pole_type = 'normal'  # Degradar a normal (sin cuota)
                elif pole_type == 'fast':
                    pole_type = 'normal'  # Degradar a normal (sin cuota)
        
        # Obtener o crear usuario LOCAL (stats por servidor)
        user = self._get_or_create_user_data(guild.id, message.author)
        
        # Obtener o crear usuario GLOBAL (rachas compartidas)
        global_user = self.db.get_or_create_global_user(message.author.id, message.author.name)
        
        # Asignar representación automáticamente si es su primer pole global
        represented = self.db.get_represented_guild(message.author.id)
        if represented is None:
            self.db.set_represented_guild(message.author.id, guild.id)
        
        # Actualizar racha GLOBAL
        current_streak = global_user['current_streak'] if global_user else 0
        last_pole_date = global_user['last_pole_date'] if global_user else None
        # Para marranero, usar la fecha efectiva (ayer) para mantener racha correctamente
        new_streak, streak_broken = update_streak(last_pole_date, current_streak, current_date=effective_date)
        
        # Calcular puntos
        points_base, streak_multiplier, points_earned = calculate_points(pole_type, new_streak)
        
        # Guardar pole en historial (v1.0)
        # pole_date = fecha efectiva (para marranero es ayer, para normal es hoy)
        self.db.save_pole(
            user_id=message.author.id,
            guild_id=guild.id,
            opening_time=opening_time,
            user_time=now,
            delay_minutes=delay_minutes,
            pole_type=pole_type,
            points_earned=points_earned,
            streak=new_streak,
            pole_date=effective_date  # CRÍTICO: fecha efectiva, no user_time
        )
        
        # Actualizar estadísticas GLOBALES (rachas)
        best_streak_global = max(int(global_user['best_streak']) if global_user else 0, int(new_streak))
        pole_date_to_save = effective_date if use_marranero else now.strftime('%Y-%m-%d')
        
        self.db.update_global_user(
            message.author.id,
            current_streak=new_streak,
            best_streak=best_streak_global,
            last_pole_date=pole_date_to_save,
            username=message.author.name  # Actualizar nombre por si cambió
        )
        
        # Actualizar estadísticas LOCALES (contadores de poles y velocidad)
        update_data: Dict[str, Any] = {
            'username': message.author.name  # Actualizar nombre por si cambió
        }
        
        # Actualizar contador específico del tipo de pole (v1.0)
        if pole_type == 'critical':
            update_data['critical_poles'] = int(user['critical_poles']) + 1
        elif pole_type == 'fast':
            update_data['fast_poles'] = int(user.get('fast_poles', 0)) + 1
        elif pole_type == 'normal':
            update_data['normal_poles'] = int(user['normal_poles']) + 1
        elif pole_type == 'marranero':
            update_data['marranero_poles'] = int(user['marranero_poles']) + 1

        # Actualizar métricas de velocidad
        prev_avg = float(user.get('average_delay_minutes') or 0)
        prev_count = int(user.get('total_poles') or 0)
        new_avg = ((prev_avg * prev_count) + delay_minutes) / (prev_count + 1)
        update_data['average_delay_minutes'] = new_avg
        best_time = user.get('best_time_minutes')
        if best_time is None or delay_minutes < int(best_time):
            update_data['best_time_minutes'] = delay_minutes
        
        self.db.update_user(message.author.id, guild.id, **update_data)
        
        # ====== ACTUALIZAR STATS DE TEMPORADA ======
        from utils.scoring import get_current_season
        current_season = get_current_season()
        
        # Obtener stats actuales de la temporada
        season_stats = self.db.get_season_stats(message.author.id, guild.id, current_season)
        
        if season_stats:
            # Actualizar existente
            season_update = {
                'season_points': season_stats['season_points'] + points_earned,
                'season_poles': season_stats['season_poles'] + 1,
                'season_best_streak': max(season_stats['season_best_streak'], new_streak)
            }
            
            # Actualizar contadores por tipo
            if pole_type == 'critical':
                season_update['season_critical'] = season_stats['season_critical'] + 1
            elif pole_type == 'fast':
                season_update['season_fast'] = season_stats['season_fast'] + 1
            elif pole_type == 'normal':
                season_update['season_normal'] = season_stats['season_normal'] + 1
            elif pole_type == 'marranero':
                season_update['season_marranero'] = season_stats['season_marranero'] + 1
            
            self.db.update_season_stats(
                message.author.id, guild.id, current_season,
                **season_update
            )
        else:
            # Crear nueva entrada para esta temporada
            season_data = {
                'season_points': points_earned,
                'season_poles': 1,
                'season_critical': 1 if pole_type == 'critical' else 0,
                'season_fast': 1 if pole_type == 'fast' else 0,
                'season_normal': 1 if pole_type == 'normal' else 0,
                'season_marranero': 1 if pole_type == 'marranero' else 0,
                'season_best_streak': new_streak
            }
            
            self.db.update_season_stats(
                message.author.id, guild.id, current_season,
                **season_data
            )
        
        # ====== ACTUALIZAR FIRST_POLE_DATE DEL SERVIDOR SI ES EL PRIMERO ======
        server_config = self.db.get_server_config(guild.id)
        if server_config and not server_config.get('first_pole_date'):
            # Es el primer pole del servidor, guardarlo
            self.db.update_server_config(guild.id, first_pole_date=effective_date)
            print(f"🎉 Primer pole registrado en {guild.name} (fecha: {effective_date})")
        
        # Enviar notificación de victoria
        try:
            await self.send_pole_notification(
                message, pole_type, position, points_base,
                streak_multiplier, points_earned, new_streak,
                streak_broken, now, delay_minutes
            )
        except Exception as e:
            print(f"❌ Error enviando notificación de pole: {e}")
            # Intentar enviar mensaje simple como fallback
            try:
                await message.reply(
                    f"🏁 Pole pillado: +{points_earned:.1f} pts • Racha {new_streak}"
                )
            except:
                pass
    
    async def handle_early_pole(self, message: discord.Message):
        """
        Manejar pole anticipada (antes de las 12h)
        """
        # Añadir reacción 🚫
        try:
            await message.add_reaction('🚫')
        except:
            pass
    
    async def send_pole_notification(self, message: discord.Message,
                                     pole_type: str, position: int,
                                     points_base: float, multiplier: float,
                                     points_earned: float, streak: int,
                                     streak_broken: bool, timestamp: datetime,
                                     delay_minutes: int):
        """
        Enviar notificación de victoria con personalidad
        """
        def format_delay(minutes: int) -> str:
            h = minutes // 60
            m = minutes % 60
            if h > 0:
                return f"{h}h {m}m" if m > 0 else f"{h}h"
            return f"{m}m"
        emoji = get_pole_emoji(pole_type)
        name = get_pole_name(pole_type)
        
        # Crear embed
        embed = discord.Embed(
            title=f"{emoji} {name} {emoji}",
            color=self.get_pole_color(pole_type),
            timestamp=timestamp
        )
        
        # Mensaje personalizado según tipo
        descriptions = {
            'critical': f"{message.author.mention} ¡ahí, al tiro!",
            'fast': f"{message.author.mention} rapidísimo ⚡",
            'normal': f"{message.author.mention}",
            'late': f"{message.author.mention} llegaste tarde ⏳",
            'marranero': f"{message.author.mention} ya era hora 🐷"
        }
        description = descriptions.get(pole_type, f"{message.author.mention}")
        
        embed.description = description
        
        # Información de tiempo
        time_str = timestamp.strftime('%H:%M:%S')
        embed.add_field(name="⏱️ Hora", value=time_str, inline=True)
        embed.add_field(name="⏳ Retraso", value=format_delay(delay_minutes), inline=True)
        embed.add_field(name="📍 Posición", value=f"#{position}", inline=True)
        
        # Información de puntos
        embed.add_field(
            name="💰 Puntos Base",
            value=f"{points_base:.1f} pts",
            inline=True
        )
        
        # Emoji según estado de racha
        streak_emoji = FIRE if streak > 1 else GRAY_FIRE
        if streak > 1:
            embed.add_field(
                name=f"{streak_emoji} Racha x{multiplier:.1f}",
                value=f"{streak} días",
                inline=True
            )
        else:
            embed.add_field(
                name=f"{streak_emoji} Racha",
                value="1 día",
                inline=True
            )
        
        embed.add_field(
            name="🎯 Total Ganado",
            value=f"**{points_earned:.1f} pts**",
            inline=True
        )
        
        # Mensaje final con personalidad
        footer_messages = {
            'critical': "imparable",
            'fast': "bien jugado 👏",
            'normal': "así se hace 🤝",
            'late': "truco pero vale 😅",
            'marranero': "mañana madruga más 🥱"
        }
        
        embed.set_footer(text=footer_messages.get(pole_type, ""))
        
        # Si se rompió una racha larga, avisar
        if streak_broken and streak > 7:
            embed.add_field(
                name="💔 Racha Anterior",
                value=f"Conservas el 20% de tu racha anterior",
                inline=False
            )
        
        await message.channel.send(embed=embed)
    
    def get_pole_color(self, pole_type: str) -> discord.Color:
        """Obtener color del embed según tipo de pole"""
        colors = {
            'critical': discord.Color.gold(),
            'fast': discord.Color.from_rgb(192, 192, 192),  # Plata
            'normal': discord.Color.green(),
            'late': discord.Color.orange(),
            'marranero': discord.Color.from_rgb(205, 133, 63)  # Marrón
        }
        return colors.get(pole_type, discord.Color.blue())
    
    # ==================== COMANDOS SLASH ====================

    @app_commands.command(name="settings", description="Configurar opciones del Pole Bot (vista según permisos)")
    async def settings(self, interaction: discord.Interaction):
        """Comando único para configurar el bot con una interfaz interactiva"""
        if interaction.guild is None:
            await interaction.response.send_message("❌ Solo en servidores.", ephemeral=True)
            return
        
        member = interaction.user if isinstance(interaction.user, discord.Member) else interaction.guild.get_member(interaction.user.id)
        if member is None:
            await interaction.response.send_message("❌ No se pudo determinar tus permisos en este servidor.", ephemeral=True)
            return
        view = SettingsView(self.db, interaction.guild.id, member)
        embed = view.create_embed(interaction.guild)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="profile", description="Ver estadísticas de un usuario")
    @app_commands.describe(
        usuario="Usuario del que ver perfil (opcional)",
        alcance="Alcance: global (todos los servidores) o local (solo este servidor)"
    )
    @app_commands.choices(alcance=[
        app_commands.Choice(name="Global (todos los servidores)", value="global"),
        app_commands.Choice(name="Local (solo este servidor)", value="local")
    ])
    async def profile(
        self, 
        interaction: discord.Interaction, 
        usuario: Optional[discord.Member] = None,
        alcance: str = "global"
    ):
        """Ver estadísticas del usuario con alcance configurable"""
        # Defer para evitar timeout
        await interaction.response.defer()
        
        from utils.scoring import get_current_season
        
        target_user = usuario or interaction.user
        
        # ==================== ALCANCE GLOBAL ====================
        if alcance == "global":
            # Obtener datos GLOBALES del usuario
            global_stats = self.db.get_user_global_stats(target_user.id)
            global_user = self.db.get_global_user(target_user.id)
            
            if not global_stats or global_stats['total_poles'] == 0:
                await interaction.followup.send(
                    f"❌ {target_user.mention} no tiene datos todavía. ¡Haz tu primer pole!",
                    ephemeral=True
                )
                return
            
            # Obtener mejor temporada para rango histórico (todos los servidores)
            current_season_id = get_current_season()
            with self.db.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Mejor temporada (sumando todos los servidores)
                cursor.execute('''
                    SELECT season_id, SUM(season_points) as total_points
                    FROM season_stats
                    WHERE user_id = ?
                    GROUP BY season_id
                    ORDER BY total_points DESC
                    LIMIT 1
                ''', (target_user.id,))
                best_season = cursor.fetchone()
                best_season_points = best_season['total_points'] if best_season else 0.0
                
                # Temporada actual (sumando todos los servidores)
                cursor.execute('''
                    SELECT SUM(season_points) as total_points, SUM(season_poles) as total_poles
                    FROM season_stats
                    WHERE user_id = ? AND season_id = ?
                ''', (target_user.id, current_season_id))
                current_season = cursor.fetchone()
                current_season_points = current_season['total_points'] if current_season and current_season['total_points'] else 0.0
                current_season_poles = current_season['total_poles'] if current_season and current_season['total_poles'] else 0
            
            rank_emoji, rank_name = get_rank_info(best_season_points)
            
            # Crear embed
            embed = discord.Embed(
                title=f"🌍 Estadísticas Globales de {target_user.display_name}",
                description="*Datos combinados de todos los servidores*",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            embed.set_thumbnail(url=target_user.display_avatar.url)
            
            # Mostrar badge de temporada actual si existe
            if current_season_poles > 0:
                season_rank_emoji, season_rank_name = get_rank_info(current_season_points)
                embed.add_field(
                    name="🎖️ Temporada Actual",
                    value=f"{season_rank_emoji} **{season_rank_name}**\n💰 {current_season_points:.1f} pts esta temporada",
                    inline=False
                )
            
            # Rango Histórico (basado en mejor temporada)
            embed.add_field(
                name="🏆 Rango Histórico",
                value=f"{rank_emoji} **{rank_name}**\n(Mejor temporada: {best_season_points:.1f} pts)",
                inline=True
            )
            
            # Puntos totales
            embed.add_field(
                name="💰 Puntos Totales",
                value=f"**{global_stats['total_points']:.1f}** pts",
                inline=True
            )
            
            # Poles totales
            embed.add_field(
                name="🏁 Poles Totales",
                value=f"**{global_stats['total_poles']}**",
                inline=True
            )
            
            # Racha actual (GLOBAL entre servidores)
            current_streak = global_user['current_streak'] if global_user else 0
            streak_emoji = FIRE if current_streak > 0 else GRAY_FIRE
            embed.add_field(
                name=f"{streak_emoji} Racha Actual",
                value=f"**{current_streak}** días",
                inline=True
            )
            
            # Mejor racha (GLOBAL entre servidores)
            best_streak = global_user['best_streak'] if global_user else 0
            best_streak_emoji = FIRE if best_streak > 0 else GRAY_FIRE
            embed.add_field(
                name=f"{best_streak_emoji} Mejor Racha",
                value=f"**{best_streak}** días",
                inline=True
            )
            
            # Desglose por tipo (GLOBAL)
            breakdown = (
                f"💎 Críticas: **{global_stats.get('critical_poles', 0)}**\n"
                f"⚡ Veloz: **{global_stats.get('fast_poles', 0)}**\n"
                f"🏁 Normales: **{global_stats.get('normal_poles', 0)}**\n"
                f"🐷 Marraneros: **{global_stats.get('marranero_poles', 0)}**"
            )
            embed.add_field(
                name="📈 Desglose de Poles",
                value=breakdown,
                inline=False
            )
            
            # Último pole (GLOBAL, puede ser de cualquier servidor)
            footer_text = ""
            if global_user and global_user['last_pole_date']:
                last_date = datetime.strptime(global_user['last_pole_date'], '%Y-%m-%d')
                footer_text = f"Último pole: {last_date.strftime('%d/%m/%Y')}"
            
            footer_text += f" • Usa /profile alcance:local para ver stats de este servidor"
            embed.set_footer(text=footer_text)
            
            await interaction.followup.send(embed=embed)
        
        # ==================== ALCANCE LOCAL ====================
        else:  # alcance == "local"
            if interaction.guild is None:
                await interaction.followup.send("❌ El alcance local solo funciona en servidores.", ephemeral=True)
                return
            
            gid = interaction.guild.id
            
            # Obtener datos LOCALES del servidor
            user_data = self.db.get_user(target_user.id, gid)
            global_user = self.db.get_global_user(target_user.id)
            
            if not user_data or user_data['total_poles'] == 0:
                await interaction.followup.send(
                    f"❌ {target_user.mention} no ha hecho ningún pole en este servidor.",
                    ephemeral=True
                )
                return
            
            # Obtener stats de la temporada actual (SOLO este servidor)
            current_season_id = get_current_season()
            season_stats = self.db.get_season_stats(target_user.id, gid, current_season_id)
            
            # Obtener rango histórico basado en el mejor desempeño en cualquier temporada (SOLO este servidor)
            best_season_points = self.db.get_user_best_season_points(target_user.id, gid)
            rank_emoji, rank_name = get_rank_info(best_season_points)
            
            # Crear embed
            embed = discord.Embed(
                title=f"📊 Stats de {target_user.display_name} en {interaction.guild.name}",
                description=f"*Datos solo de este servidor • Las rachas son globales*",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            
            embed.set_thumbnail(url=target_user.display_avatar.url)
            
            # Mostrar badge de temporada actual si existe
            if season_stats and season_stats.get('season_poles', 0) > 0:
                season_rank_emoji, season_rank_name = get_rank_info(season_stats['season_points'])
                embed.add_field(
                    name="🎖️ Temporada Actual (servidor)",
                    value=f"{season_rank_emoji} **{season_rank_name}**\n💰 {season_stats['season_points']:.1f} pts esta temporada",
                    inline=False
                )
            
            # Rango Histórico (basado en mejor temporada EN ESTE SERVIDOR)
            embed.add_field(
                name="🏆 Rango Histórico (servidor)",
                value=f"{rank_emoji} **{rank_name}**\n(Mejor temporada: {best_season_points:.1f} pts)",
                inline=True
            )
            
            # Puntos totales EN ESTE SERVIDOR
            embed.add_field(
                name="💰 Puntos (servidor)",
                value=f"**{user_data['total_points']:.1f}** pts",
                inline=True
            )
            
            # Poles totales EN ESTE SERVIDOR
            embed.add_field(
                name="🏁 Poles (servidor)",
                value=f"**{user_data['total_poles']}**",
                inline=True
            )
            
            # Racha actual (GLOBAL entre servidores)
            current_streak = global_user['current_streak'] if global_user else 0
            streak_emoji = FIRE if current_streak > 0 else GRAY_FIRE
            embed.add_field(
                name=f"{streak_emoji} Racha Actual (global)",
                value=f"**{current_streak}** días",
                inline=True
            )
            
            # Mejor racha (GLOBAL entre servidores)
            best_streak = global_user['best_streak'] if global_user else 0
            best_streak_emoji = FIRE if best_streak > 0 else GRAY_FIRE
            embed.add_field(
                name=f"{best_streak_emoji} Mejor Racha (global)",
                value=f"**{best_streak}** días",
                inline=True
            )
            
            # Desglose por tipo (SOLO ESTE SERVIDOR)
            breakdown = (
                f"💎 Críticas: **{user_data.get('critical_poles', 0)}**\n"
                f"⚡ Veloz: **{user_data.get('fast_poles', 0)}**\n"
                f"🏁 Normales: **{user_data.get('normal_poles', 0)}**\n"
                f"🐷 Marraneros: **{user_data.get('marranero_poles', 0)}**"
            )
            embed.add_field(
                name="📈 Desglose de Poles (servidor)",
                value=breakdown,
                inline=False
            )
            
            # Footer
            footer_text = f"Usa /profile alcance:global para ver estadísticas globales"
            embed.set_footer(text=footer_text)
            
            await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="leaderboard", description="Ver ranking de poles")
    @app_commands.describe(
        alcance="Alcance del ranking: local (este servidor) o global (todos los servidores)",
        tipo="Tipo de ranking: personas, servidores o rachas",
        temporada="Temporada a mostrar (Lifetime por defecto)",
        limite="Cantidad de entradas a mostrar (por defecto 10)"
    )
    @app_commands.choices(
        alcance=[
            app_commands.Choice(name="Local", value="local"),
            app_commands.Choice(name="Global", value="global")
        ],
        tipo=[
            app_commands.Choice(name="Personas", value="personas"),
            app_commands.Choice(name="Servidores", value="servers"),
            app_commands.Choice(name="Rachas", value="rachas")
        ]
    )
    async def leaderboard(
        self, 
        interaction: discord.Interaction, 
        alcance: str = "local", 
        tipo: str = "personas", 
        temporada: Optional[str] = None,
        limite: int = 10
    ):
        """Ver ranking de poles con diferentes alcances, tipos y temporadas"""
        # Defer para evitar timeout de 3 segundos
        await interaction.response.defer()
        
        if limite < 1 or limite > 25:
            await interaction.followup.send(
                "❌ El límite debe estar entre 1 y 25.",
                ephemeral=True
            )
            return
        
        # Obtener temporada actual y disponibles
        from utils.scoring import get_current_season
        current_season_id = get_current_season()
        
        # Si no se especifica temporada, usar "lifetime"
        if temporada is None:
            temporada = "lifetime"
        
        # Determinar si es lifetime o una season específica
        is_lifetime = (temporada == "lifetime")
        
        # season_id solo se usa cuando NO es lifetime (garantiza que no sea None en esos casos)
        if not is_lifetime:
            season_id: str = temporada  # Type assertion: sabemos que temporada es str aquí
        else:
            season_id = current_season_id  # No usado, pero evita None
        
        # LOCAL + PERSONAS
        if alcance == "local" and tipo == "personas":
            if interaction.guild is None:
                await interaction.followup.send("❌ Este comando solo funciona en servidores.", ephemeral=True)
                return
            gid = interaction.guild.id
            
            # Obtener datos según temporada
            if is_lifetime:
                top_users = self.db.get_leaderboard(gid, limite)
                points_key = 'total_points'
                poles_key = 'total_poles'
                title_suffix = "Lifetime"
            else:
                top_users = self.db.get_season_leaderboard(gid, season_id, limite)
                points_key = 'season_points'
                poles_key = 'season_poles'
                # Obtener nombre legible de la season
                seasons = self.db.get_available_seasons()
                season_name = next((s['season_name'] for s in seasons if s['season_id'] == season_id), season_id)
                title_suffix = season_name
            
            if not top_users:
                await interaction.followup.send(
                    f"❌ Aún no hay estadísticas {'de esta temporada ' if not is_lifetime else ''}en este servidor.",
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title=f"🏆 RANKING LOCAL - Personas - {title_suffix}",
                description=f"Servidor: {interaction.guild.name}",
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )
            
            ranking_text = ""
            for idx, user_data in enumerate(top_users, start=1):
                points = user_data.get(points_key, 0)
                poles = user_data.get(poles_key, 0)
                rank_emoji, _ = get_rank_info(points)
                position_emoji = {1: "🥇", 2: "🥈", 3: "🥉"}.get(idx, f"{idx}.")
                
                # Racha solo para lifetime
                streak_info = ""
                if is_lifetime:
                    current_streak = user_data.get('current_streak', 0)
                    if current_streak > 0:
                        streak_info = f" • {FIRE} {current_streak}"
                    # No mostrar racha si es 0 para no saturar
                
                # Obtener servidor representado
                represented_guild_id = user_data.get('represented_guild_id')
                guild_text = ""
                if represented_guild_id:
                    guild = self.bot.get_guild(represented_guild_id)
                    if guild:
                        guild_text = f" • 🏳️ {guild.name}"
                    else:
                        guild_text = f" • 🏳️ ID:{represented_guild_id}"
                
                ranking_text += (
                    f"{position_emoji} {rank_emoji} **{user_data['username']}**{guild_text}\n"
                    f"💰 {points:.1f} pts • "
                    f"🏁 {poles} poles{streak_info}\n\n"
                )
            
            embed.description = ranking_text
            
            # Footer con posición del usuario
            if is_lifetime:
                user_data = self.db.get_user(interaction.user.id, gid)
                if user_data:
                    all_users = self.db.get_leaderboard(gid, 1000)
                    user_position = next(
                        (idx for idx, u in enumerate(all_users, start=1) if u['user_id'] == interaction.user.id),
                        None
                    )
                    if user_position:
                        embed.set_footer(text=f"Tu posición: #{user_position} de {len(all_users)}")
            else:
                user_data = self.db.get_season_stats(interaction.user.id, gid, season_id)
                if user_data:
                    all_users = self.db.get_season_leaderboard(gid, season_id, 1000)
                    user_position = next(
                        (idx for idx, u in enumerate(all_users, start=1) if u['user_id'] == interaction.user.id),
                        None
                    )
                    if user_position:
                        embed.set_footer(text=f"Tu posición en {title_suffix}: #{user_position} de {len(all_users)}")
        
        # LOCAL + SERVIDORES
        elif alcance == "local" and tipo == "servers":
            if interaction.guild is None:
                await interaction.followup.send("❌ Este comando solo funciona en servidores.", ephemeral=True)
                return
            gid = interaction.guild.id
            
            # Obtener datos según temporada
            if is_lifetime:
                top_servers = self.db.get_local_server_leaderboard(gid, limite)
                title_suffix = "Lifetime"
            else:
                top_servers = self.db.get_local_server_season_leaderboard(gid, season_id, limite)
                seasons = self.db.get_available_seasons()
                season_name = next((s['season_name'] for s in seasons if s['season_id'] == season_id), season_id)
                title_suffix = season_name
            
            if not top_servers:
                await interaction.followup.send(
                    f"❌ Aún no hay servidores representados {'en esta temporada' if not is_lifetime else ''}.",
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title=f"🏆 RANKING LOCAL - Servidores - {title_suffix}",
                description=f"Servidores representados por miembros de {interaction.guild.name}",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            ranking_text = ""
            for idx, server_data in enumerate(top_servers, start=1):
                guild = self.bot.get_guild(int(server_data['guild_id']))
                server_name = guild.name if guild else f"Servidor ID {server_data['guild_id']}"
                position_emoji = {1: "🥇", 2: "🥈", 3: "🥉"}.get(idx, f"{idx}.")
                
                ranking_text += (
                    f"{position_emoji} **{server_name}**\n"
                    f"    💰 {server_data['total_points']:.1f} pts | "
                    f"👥 {server_data['member_count']} miembros\n\n"
                )
            
            embed.description = ranking_text
        
        # LOCAL + RACHAS (muestra rachas GLOBALES de usuarios de este servidor)
        elif alcance == "local" and tipo == "rachas":
            if interaction.guild is None:
                await interaction.followup.send("❌ Este comando solo funciona en servidores.", ephemeral=True)
                return
            gid = interaction.guild.id
            
            # Obtener usuarios activos del servidor (tienen poles locales)
            local_users = self.db.get_leaderboard(gid, limit=1000, order_by='points')
            if not local_users:
                await interaction.followup.send(
                    "❌ Aún no hay usuarios en este servidor.",
                    ephemeral=True
                )
                return
            
            # Obtener rachas GLOBALES de esos usuarios
            user_ids = [u['user_id'] for u in local_users]
            users_with_streaks = []
            
            for uid in user_ids:
                global_user = self.db.get_global_user(uid)
                if global_user and (global_user['current_streak'] > 0 or global_user['best_streak'] > 0):
                    users_with_streaks.append(global_user)
            
            # Ordenar por racha actual (descendente), luego por mejor racha
            users_with_streaks.sort(key=lambda u: (u['current_streak'], u['best_streak']), reverse=True)
            top_users = users_with_streaks[:limite]
            
            if not top_users:
                await interaction.followup.send(
                    "❌ Aún no hay usuarios con rachas en este servidor.",
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title="🔥 RANKING DE RACHAS - Local",
                description=f"Servidor: {interaction.guild.name}\n*(Rachas son globales entre todos los servidores)*",
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            
            ranking_text = ""
            for idx, user_data in enumerate(top_users, start=1):
                current_streak = user_data.get('current_streak', 0)
                best_streak = user_data.get('best_streak', 0)
                position_emoji = {1: "🥇", 2: "🥈", 3: "🥉"}.get(idx, f"{idx}.")
                
                # Emoji según estado de racha
                streak_emoji = FIRE if current_streak > 0 else GRAY_FIRE
                
                ranking_text += (
                    f"{position_emoji} {streak_emoji} **{user_data['username']}**\n"
                    f"    Actual: **{current_streak}** días • Mejor: **{best_streak}** días\n\n"
                )
            
            if embed.description:
                embed.description += f"\n\n{ranking_text}"
            else:
                embed.description = ranking_text
            
            # Footer con posición del usuario
            global_user = self.db.get_global_user(interaction.user.id)
            if global_user:
                user_position = next(
                    (idx for idx, u in enumerate(users_with_streaks, start=1) if u['user_id'] == interaction.user.id),
                    None
                )
                if user_position:
                    footer_text = f"Tu posición: #{user_position} • Tu racha: {global_user.get('current_streak', 0)} días"
                    embed.set_footer(text=footer_text)
        
        # GLOBAL + RACHAS
        elif alcance == "global" and tipo == "rachas":
            # Obtener rachas globales
            top_users = self.db.get_global_leaderboard(limite, order_by='streak')
            
            if not top_users:
                await interaction.followup.send(
                    "❌ Aún no hay estadísticas globales.",
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title="🔥 RANKING DE RACHAS - Global",
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            
            ranking_text = ""
            for idx, user_data in enumerate(top_users, start=1):
                current_streak = user_data.get('current_streak', 0)
                best_streak = user_data.get('best_streak', 0)
                position_emoji = {1: "🥇", 2: "🥈", 3: "🥉"}.get(idx, f"{idx}.")
                
                # Emoji según estado de racha
                streak_emoji = FIRE if current_streak > 0 else GRAY_FIRE
                
                # Servidor representado
                represented_guild_id = user_data.get('represented_guild_id')
                guild_text = ""
                if represented_guild_id:
                    guild = self.bot.get_guild(represented_guild_id)
                    if guild:
                        guild_text = f" • 🏳️ {guild.name}"
                
                ranking_text += (
                    f"{position_emoji} {streak_emoji} **{user_data['username']}**{guild_text}\n"
                    f"    Actual: **{current_streak}** días • Mejor: **{best_streak}** días\n\n"
                )
            
            embed.description = ranking_text

        # GLOBAL + PERSONAS
        elif alcance == "global" and tipo == "personas":
            # Obtener datos según temporada
            if is_lifetime:
                top_users = self.db.get_global_leaderboard(limite)
                points_key = 'total_points'
                poles_key = 'total_poles'
                title_suffix = "Lifetime"
            else:
                top_users = self.db.get_global_season_leaderboard(season_id, limite)
                points_key = 'total_season_points'
                poles_key = 'total_season_poles'
                seasons = self.db.get_available_seasons()
                season_name = next((s['season_name'] for s in seasons if s['season_id'] == season_id), season_id)
                title_suffix = season_name
            
            if not top_users:
                await interaction.followup.send(
                    f"❌ Aún no hay estadísticas globales{'de esta temporada' if not is_lifetime else ''}.",
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title=f"🌍 RANKING GLOBAL - Personas - {title_suffix}",
                color=discord.Color.gold(),
                timestamp=datetime.now()
            )
            
            ranking_text = ""
            for idx, user_data in enumerate(top_users, start=1):
                points = user_data.get(points_key, 0)
                poles = user_data.get(poles_key, 0)
                rank_emoji, _ = get_rank_info(points)
                position_emoji = {1: "🥇", 2: "🥈", 3: "🥉"}.get(idx, f"{idx}.")
                
                # Racha solo para lifetime
                streak_info = ""
                if is_lifetime:
                    current_streak = user_data.get('current_streak', 0)
                    if current_streak > 0:
                        streak_info = f" • {FIRE} {current_streak}"
                    # No mostrar racha si es 0 para no saturar
                
                # Obtener servidor que representa
                represented_guild_id = user_data.get('represented_guild_id')
                guild_text = ""
                if represented_guild_id:
                    guild = self.bot.get_guild(represented_guild_id)
                    if guild:
                        guild_text = f" • 🏳️ {guild.name}"
                    else:
                        guild_text = f" • 🏳️ ID:{represented_guild_id}"
                
                ranking_text += (
                    f"{position_emoji} {rank_emoji} **{user_data['username']}**{guild_text}\n"
                    f"💰 {points:.1f} pts • "
                    f"🏁 {poles} poles{streak_info}\n\n"
                )
            
            embed.description = ranking_text
        
        # GLOBAL + SERVIDORES
        else:  # alcance == "global" and tipo == "servers"
            # Obtener datos según temporada
            if is_lifetime:
                top_servers = self.db.get_global_server_leaderboard(limite)
                title_suffix = "Lifetime"
            else:
                top_servers = self.db.get_global_server_season_leaderboard(season_id, limite)
                seasons = self.db.get_available_seasons()
                season_name = next((s['season_name'] for s in seasons if s['season_id'] == season_id), season_id)
                title_suffix = season_name
            
            if not top_servers:
                await interaction.followup.send(
                    f"❌ Aún no hay servidores representados{'en esta temporada' if not is_lifetime else ''}.",
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title=f"🌍 RANKING GLOBAL - Servidores - {title_suffix}",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            
            ranking_text = ""
            for idx, server_data in enumerate(top_servers, start=1):
                guild = self.bot.get_guild(int(server_data['guild_id']))
                server_name = guild.name if guild else f"Servidor ID {server_data['guild_id']}"
                position_emoji = {1: "🥇", 2: "🥈", 3: "🥉"}.get(idx, f"{idx}.")
                
                ranking_text += (
                    f"{position_emoji} **{server_name}**\n"
                    f"    💰 {server_data['total_points']:.1f} pts | "
                    f"👥 {server_data['member_count']} miembros\n\n"
                )
            
            embed.description = ranking_text
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="streak", description="Ver información detallada de tu racha")
    async def streak(self, interaction: discord.Interaction):
        """Ver información de racha del usuario"""
        # Defer para evitar timeout
        await interaction.response.defer()
        
        if interaction.guild is None:
            await interaction.followup.send("❌ Este comando solo funciona en servidores.", ephemeral=True)
            return
        gid = interaction.guild.id
        user_data = self.db.get_user(interaction.user.id, gid)
        
        if not user_data or user_data['total_poles'] == 0:
            await interaction.followup.send(
                "❌ Aún no has hecho ningún pole.",
                ephemeral=True
            )
            return
        
        # Crear embed
        streak_title_emoji = FIRE if user_data['current_streak'] > 0 else GRAY_FIRE
        embed = discord.Embed(
            title=f"{streak_title_emoji} Tu Racha Actual",
            color=discord.Color.orange() if user_data['current_streak'] > 0 else discord.Color.red(),
            timestamp=datetime.now()
        )
        
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        # Racha actual
        if user_data['current_streak'] > 0:
            multiplier = get_streak_multiplier(user_data['current_streak'])
            current_streak_emoji = FIRE if user_data['current_streak'] > 1 else GRAY_FIRE
            
            embed.add_field(
                name=f"{current_streak_emoji} Racha Actual",
                value=f"**{user_data['current_streak']}** días consecutivos\nMultiplicador: **x{multiplier:.1f}**",
                inline=False
            )
            
            # Calcular próximo hito
            milestones = [7, 14, 21, 30, 45, 60, 75, 90, 120, 150, 180, 210, 240, 270, 300, 365]
            next_milestone = next((m for m in milestones if m > user_data['current_streak']), None)
            
            if next_milestone:
                days_to_next = next_milestone - user_data['current_streak']
                next_multiplier = get_streak_multiplier(next_milestone)
                embed.add_field(
                    name="🎯 Próximo Hito",
                    value=f"{next_milestone} días (faltan **{days_to_next}** días)\nMultiplicador: x{next_multiplier:.1f}",
                    inline=False
                )
        else:
            embed.add_field(
                name=f"{GRAY_FIRE} Racha apagada",
                value="Racha de 0 días. Enciéndela con un pole hoy.",
                inline=False
            )
        
        # Mejor racha
        embed.add_field(
            name="🏆 Tu Mejor Racha",
            value=f"**{user_data['best_streak']}** días",
            inline=True
        )
        
        # Último pole
        if user_data['last_pole_date']:
            last_date = datetime.strptime(user_data['last_pole_date'], '%Y-%m-%d')
            today = datetime.now()
            days_since = (today - last_date).days
            
            if days_since == 0:
                last_text = "Hoy ✅"
            elif days_since == 1:
                last_text = "Ayer"
            else:
                last_text = f"Hace {days_since} días"
            
            embed.add_field(
                name="📅 Último Pole",
                value=last_text,
                inline=True
            )
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="polehelp", description="Ver información sobre cómo funciona el bot")
    async def polehelp(self, interaction: discord.Interaction):
        """Mostrar ayuda del bot"""
        embed = discord.Embed(
            title="📖 Pole Bot - Guía Rápida",
            description="Compite cada día por escribir **pole** lo más rápido posible tras la apertura diaria",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Cómo jugar
        embed.add_field(
            name="🎮 Cómo Jugar",
            value=(
                "1. Espera la **notificación de apertura** (hora aleatoria cada día)\n"
                "2. Escribe exactamente **`pole`** en el canal configurado\n"
                "3. ¡Gana puntos según tu velocidad!\n"
                "⚠️ Solo 1 pole al día, en cualquier servidor"
            ),
            inline=False
        )
        
        # Tipos de pole según delay
        embed.add_field(
            name="🏆 Categorías de Pole",
            value=(
                "💎 **Crítica** (0-10 min): 20 pts\n"
                "    └ Solo 10% del servidor puede reclamarla\n"
                "⚡ **Veloz** (10 min - 3h): 15 pts\n"
                "    └ Solo 30% del servidor puede reclamarla\n"
                "🏁 **Normal** (3h - 00:00): 10 pts\n"
                "    └ Sin límite de usuarios\n"
                "🐷 **Marranero** (día siguiente): 5 pts\n"
                "    └ Sin límite de usuarios"
            ),
            inline=False
        )
        
        # Rachas
        embed.add_field(
            name=f"{FIRE} Sistema de Rachas",
            value=(
                "Haz pole días consecutivos para aumentar tu multiplicador\n"
                "• 7 días: x1.1\n"
                "• 30 días: x1.4\n"
                "• 90 días: x1.8\n"
                "• 300 días: x2.5 (máximo)"
            ),
            inline=False
        )
        
        # Comandos
        embed.add_field(
            name="⚙️ Comandos",
            value=(
                "`/profile` - Ver tu perfil y estadísticas\n"
                "`/leaderboard` - Ver rankings (local/global, personas/servidores)\n"
                "`/streak` - Info detallada de tu racha\n"
                "`/season` - Ver temporada actual y tu progreso\n"
                "`/history` - Ver badges y temporadas pasadas\n"
                "`/leaderboard` - También permite ver temporadas específicas (selector de temporada)\n"
                "`/settings` - Configurar el bot (admins)\n"
                "`/polehelp` - Ver esta ayuda"
            ),
            inline=False
        )
        
        embed.set_footer(text=f"¡Suerte y que gane el más rápido! {FIRE}")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="season", description="Ver información de la temporada actual y tu progreso")
    async def season(self, interaction: discord.Interaction):
        """Ver información de la temporada actual"""
        if not interaction.guild:
            await interaction.response.send_message("❌ Este comando solo funciona en servidores.", ephemeral=True)
            return
        
        from utils.scoring import get_current_season, get_season_info
        
        current_season_id = get_current_season()
        season_info = get_season_info(current_season_id)
        
        # Obtener stats del usuario en esta temporada
        season_stats = self.db.get_season_stats(interaction.user.id, interaction.guild.id, current_season_id)
        
        # Crear embed
        embed = discord.Embed(
            title=f"🎮 {season_info['name']}",
            description=f"**Período:** {season_info['start_date']} → {season_info['end_date']}",
            color=discord.Color.gold() if season_info['is_ranked'] else discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Estado de la temporada
        status = "🏆 **Temporada Oficial**" if season_info['is_ranked'] else "🎯 **Temporada de Práctica**"
        embed.add_field(name="Estado", value=status, inline=False)
        
        # Calcular tiempo restante
        try:
            end_date = datetime.strptime(season_info['end_date'], '%Y-%m-%d').date()
            today = datetime.now().date()
            days_left = (end_date - today).days
            
            if days_left > 0:
                embed.add_field(
                    name="⏰ Tiempo Restante",
                    value=f"**{days_left}** días",
                    inline=True
                )
            else:
                embed.add_field(
                    name="⏰ Estado",
                    value="**Finalizada**",
                    inline=True
                )
        except:
            pass
        
        # Stats del usuario en esta temporada
        if season_stats and season_stats.get('season_poles', 0) > 0:
            rank_emoji, rank_name = get_rank_info(season_stats['season_points'])
            
            embed.add_field(
                name=f"\n📊 Tu Progreso en {season_info['name']}",
                value=(
                    f"🎖️ **Rango:** {rank_emoji} {rank_name}\n"
                    f"💰 **Puntos:** {season_stats['season_points']:.1f}\n"
                    f"🏁 **Poles:** {season_stats['season_poles']}\n"
                    f"{FIRE} **Mejor Racha:** {season_stats['season_best_streak']} días"
                ),
                inline=False
            )
            
            # Desglose por tipo
            breakdown = (
                f"💎 Críticas: {season_stats['season_critical']} | "
                f"⚡ Veloces: {season_stats['season_fast']}\n"
                f"🏁 Normales: {season_stats['season_normal']} | "
                f"🐷 Marraneros: {season_stats['season_marranero']}"
            )
            embed.add_field(name="📈 Desglose", value=breakdown, inline=False)
        else:
            embed.add_field(
                name="📊 Tu Progreso",
                value=f"Aún no has hecho ningún pole en {season_info['name']}.\n¡Empieza ahora y escala el ranking!",
                inline=False
            )
        
        embed.set_footer(text=f"Usa /history para ver temporadas pasadas {FIRE}")
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="history", description="Ver tu historial de temporadas y colección de badges")
    async def history(self, interaction: discord.Interaction):
        """Ver historial de temporadas pasadas"""
        if not interaction.guild:
            await interaction.response.send_message("❌ Este comando solo funciona en servidores.", ephemeral=True)
            return
        
        # Obtener badges del usuario
        badges = self.db.get_user_badges(interaction.user.id, interaction.guild.id)
        
        # Obtener historial de temporadas
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT season_id, final_points, final_rank, final_badge, 
                       final_position, total_players, total_poles, best_streak,
                       season_ended_at
                FROM season_history
                WHERE user_id = ? AND guild_id = ?
                ORDER BY season_ended_at DESC
                LIMIT 10
            ''', (interaction.user.id, interaction.guild.id))
            history = cursor.fetchall()
        
        embed = discord.Embed(
            title=f"🏆 Historial de {interaction.user.display_name}",
            description="Tu legado a través de las temporadas",
            color=discord.Color.purple(),
            timestamp=datetime.now()
        )
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        # Mostrar badges ganados
        if badges:
            from utils.scoring import get_season_info
            
            badge_text = ""
            for badge in badges[:6]:  # Mostrar últimos 6
                season_info = get_season_info(badge['season_id'])
                badge_text += f"{badge['badge_emoji']} **{season_info['name']}** - {badge['badge_type'].title()}\n"
            
            embed.add_field(
                name="💎 Colección de Badges",
                value=badge_text or "No has ganado badges aún",
                inline=False
            )
        else:
            embed.add_field(
                name="💎 Colección de Badges",
                value="Aún no has ganado ningún badge.\n¡Completa una temporada para ganar tu primer badge!",
                inline=False
            )
        
        # Mostrar historial de temporadas
        if history:
            from utils.scoring import get_season_info
            
            history_text = ""
            for h in history[:5]:  # Mostrar últimas 5
                season_info = get_season_info(h['season_id'])
                history_text += (
                    f"**{season_info['name']}**\n"
                    f"  {h['final_badge']} {h['final_rank'].title()} • "
                    f"{h['final_points']:.0f} pts • "
                    f"#{h['final_position']}/{h['total_players']}\n\n"
                )
            
            embed.add_field(
                name="📜 Historial de Temporadas",
                value=history_text,
                inline=False
            )
        else:
            embed.add_field(
                name="📜 Historial de Temporadas",
                value="No has completado ninguna temporada aún.\n¡Sigue jugando para crear tu historial!",
                inline=False
            )
        
        embed.set_footer(text=f"Usa /season para ver la temporada actual {FIRE}")
        await interaction.response.send_message(embed=embed)
    
    # [DEPRECATED] season_leaderboard eliminado. Usar /leaderboard con 'temporada'.
    
    # ==================== TAREAS PROGRAMADAS v1.0 ====================
    
    @tasks.loop(time=time(hour=0, minute=0))
    async def daily_pole_generator(self):
        """
        Generar hora de apertura diaria a medianoche (hora local) para cada servidor.
        Aplica margen mínimo entre aperturas y verifica cambio de temporada.
        """
        import random
        from utils.scoring import get_current_season, get_season_info
        
        now = datetime.now()
        # El decorador @tasks.loop con time=00:00 ya garantiza ejecución a medianoche
        
        # ==================== VERIFICAR CAMBIO DE TEMPORADA ====================
        # Esto debe hacerse ANTES de generar las horas del día
        old_season = None
        new_season = None
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT season_id FROM seasons WHERE is_active = 1')
                row = cursor.fetchone()
                old_season = row[0] if row else None
            
            current_season = get_current_season()
            
            # Si cambió la temporada (normalmente en año nuevo)
            if old_season and old_season != current_season:
                print(f"🎊 ¡CAMBIO DE TEMPORADA DETECTADO! {old_season} → {current_season}")
                
                # Ejecutar migración automática usando sistema unificado
                migrated = self.db.migrate_season()
                
                if migrated:
                    new_season = current_season
                    # Enviar mensaje de felicitación a todos los servidores
                    await self._send_season_change_announcement(old_season, new_season)
                else:
                    print("ℹ️  La migración ya se había ejecutado previamente")
        except Exception as e:
            print(f"⚠️ Error verificando temporada: {e}")
        
        # Iterar por todos los servidores configurados
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT guild_id FROM servers 
                WHERE pole_channel_id IS NOT NULL
            ''')
            servers = cursor.fetchall()
        
        print(f"📋 Generando horas para {len(servers)} servidores configurados...")
        
        # Margen mínimo entre poles: 4 horas (configurable)
        MIN_HOURS_BETWEEN_POLES = 4
        # Jitter aleatorio para reducir predictibilidad (±30 minutos)
        JITTER_MINUTES = 30
        
        for server in servers:
            guild_id = server['guild_id']
            
            # Validar que el bot todavía está en este servidor
            guild = self.bot.get_guild(guild_id)
            if not guild:
                print(f"⚠️ Saltando guild {guild_id}: bot ya no está en el servidor")
                continue
            
            # Obtener hora de apertura generada AYER (no del último pole)
            last_opening_str = self.db.get_last_daily_pole_time(guild_id)
            
            # Inicializar variables
            random_hour = 12  # Valor por defecto
            random_minute = 0
            
            # Generar hora aleatoria con validación de margen
            max_attempts = 100
            valid_time_found = False
            
            for attempt in range(max_attempts):
                # Generar hora aleatoria (00:00 - 23:59)
                random_hour = random.randint(0, 23)
                random_minute = random.randint(0, 59)
                
                # Si no hay apertura previa, cualquier hora es válida
                if not last_opening_str:
                    valid_time_found = True
                    break
                
                # Calcular diferencia con la apertura de ayer
                try:
                    # Apertura de ayer
                    yesterday = datetime.now() - timedelta(days=1)
                    last_parts = last_opening_str.split(':')
                    last_hour = int(last_parts[0])
                    last_minute = int(last_parts[1])
                    last_opening = yesterday.replace(hour=last_hour, minute=last_minute, second=0)
                    
                    # Apertura propuesta para hoy
                    today = datetime.now().replace(hour=random_hour, minute=random_minute, second=0)
                    
                    # Calcular diferencia en horas
                    time_diff = (today - last_opening).total_seconds() / 3600
                    
                    # Aplicar jitter aleatorio al margen para reducir predictibilidad
                    jitter = random.randint(-JITTER_MINUTES, JITTER_MINUTES) / 60.0
                    effective_margin = MIN_HOURS_BETWEEN_POLES + jitter
                    
                    # Validar margen mínimo con jitter
                    if time_diff >= effective_margin:
                        valid_time_found = True
                        break
                    
                except Exception as e:
                    print(f"⚠️ Error calculando margen para guild {guild_id}: {e}")
                    # Si hay error, aceptar esta hora
                    valid_time_found = True
                    break
            
            # Si después de todos los intentos no se encontró hora válida,
            # forzar una hora que cumpla el margen
            if not valid_time_found and last_opening_str:
                try:
                    last_parts = last_opening_str.split(':')
                    last_hour = int(last_parts[0])
                    last_minute = int(last_parts[1])
                    
                    # Calcular hora mínima para hoy (ayer + MIN_HOURS)
                    min_hour = (last_hour + MIN_HOURS_BETWEEN_POLES) % 24
                    
                    # Generar hora entre min_hour y fin del día
                    if min_hour < 23:
                        random_hour = random.randint(min_hour, 23)
                        random_minute = random.randint(0, 59)
                    else:
                        # Si min_hour >= 23, usar la primera hora válida del día siguiente
                        random_hour = 0
                        random_minute = random.randint(0, 59)
                    
                    print(f"⚠️ Forzando hora con margen para guild {guild_id}: {random_hour:02d}:{random_minute:02d}")
                except Exception as e:
                    print(f"❌ Error forzando margen para guild {guild_id}: {e}")
                    # Fallback: hora aleatoria simple
                    random_hour = random.randint(8, 20)
                    random_minute = random.randint(0, 59)
            
            # Guardar en DB
            time_str = f"{random_hour:02d}:{random_minute:02d}:00"
            self.db.set_daily_pole_time(guild_id, time_str)
            
            if last_opening_str:
                print(f"✅ Hora generada para guild {guild_id}: {time_str} (anterior: {last_opening_str}, margen: ≥{MIN_HOURS_BETWEEN_POLES}h)")
            else:
                print(f"✅ Hora generada para guild {guild_id}: {time_str} (primera vez)")
        
        # Programar notificaciones exactas para hoy tras generar todas las horas
        await self.schedule_all_today_notifications()
    
    async def _send_season_change_announcement(self, old_season_id: str, new_season_id: str):
        """
        🎬 POLE REWIND - Enviar resumen de año con estadísticas y celebración
        Sistema de 7 mensajes: Intro + 4 categorías locales + 1 global condensado + cierre
        """
        from utils.scoring import get_season_info
        
        old_info = get_season_info(old_season_id)
        new_info = get_season_info(new_season_id)
        
        # Detectar si es la transición BETA → Temporada 1
        is_first_season = (old_season_id == "2025")
        
        # Obtener servidores configurados
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT guild_id, pole_channel_id FROM servers WHERE pole_channel_id IS NOT NULL')
            servers = cursor.fetchall()
        
        sent_count = 0
        for server in servers:
            try:
                guild = self.bot.get_guild(server['guild_id'])
                if not guild:
                    continue
                
                channel = guild.get_channel(server['pole_channel_id'])
                if not channel:
                    continue
                
                guild_id = server['guild_id']
                
                # ==================== MENSAJE 1: INTRODUCCIÓN ====================
                if is_first_season:
                    embed_intro = discord.Embed(
                        title="🎆 ¡FELIZ AÑO NUEVO, EARLY POLERS! 🎆",
                        description=(
                            "Qué locura de año, familia.\n\n"
                            "Ustedes son los **PIONEROS**. Los que creyeron en este bot cuando era un "
                            "experimento random. Los que se comieron los bugs, las rachas rotas, las horas "
                            "locas del pole... y **AÚN ASÍ** siguieron aquí.\n\n"
                            "Este ha sido solo el **CALENTAMIENTO**. La pre-temporada. El tutorial.\n\n"
                            f"Ahora viene el **POLE REWIND {old_season_id}**. Vamos a recordar quiénes fueron las leyendas. 🎬"
                        ),
                        color=discord.Color.gold(),
                        timestamp=datetime.now()
                    )
                else:
                    embed_intro = discord.Embed(
                        title="🎆 ¡FELIZ AÑO NUEVO, POLERS! 🎆",
                        description=(
                            "Otro año más, otra batalla ganada.\n\n"
                            "Gracias a todos los que hicieron del pole parte de su rutina diaria. "
                            "Cada pole a las 3am, cada racha salvada in extremis, cada momento épico... "
                            "**ESO** es lo que hace que esta comunidad sea lo que es.\n\n"
                            f"Es hora del **POLE REWIND {old_season_id}**. 🎬"
                        ),
                        color=discord.Color.gold(),
                        timestamp=datetime.now()
                    )
                
                embed_intro.set_thumbnail(url="https://em-content.zobj.net/thumbs/120/twitter/348/party-popper_1f389.png")
                await channel.send(embed=embed_intro)
                await asyncio.sleep(2)
                
                # Obtener datos
                local_rankings = self._get_season_rankings_local(guild_id, old_season_id)
                global_rankings = self._get_season_rankings_global(old_season_id)
                
                # ==================== MENSAJE 2: 👑 MÁXIMOS ANOTADORES (Local) ====================
                embed_points_local = discord.Embed(
                    title=f"👑 MÁXIMOS ANOTADORES - {guild.name}",
                    description="Los que acumularon más puntos en esta temporada:",
                    color=discord.Color.gold(),
                    timestamp=datetime.now()
                )
                
                if local_rankings['points']:
                    for i, (uid, pts) in enumerate(local_rankings['points'][:3], 1):
                        medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉'
                        dedication = self._get_dedication_points(i)
                        embed_points_local.add_field(
                            name=f"{medal} {dedication}",
                            value=f"<@{uid}> - **{pts:,}** puntos",
                            inline=False
                        )
                else:
                    if embed_points_local.description:
                        embed_points_local.description += "\n\n_Nadie compitió en esta categoría._"
                
                embed_points_local.set_footer(text=f"Hall of Fame {old_season_id} • La consistencia paga.")
                await channel.send(embed=embed_points_local)
                await asyncio.sleep(1.5)
                
                # ==================== MENSAJE 3: ⚡ MÁS POLES (Local) ====================
                embed_poles_local = discord.Embed(
                    title=f"⚡ POLEMANIÁTICOS - {guild.name}",
                    description="Los que más veces fueron los primeros:",
                    color=discord.Color.red(),
                    timestamp=datetime.now()
                )
                
                if local_rankings['poles']:
                    for i, (uid, count) in enumerate(local_rankings['poles'][:3], 1):
                        medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉'
                        dedication = self._get_dedication_poles(i)
                        embed_poles_local.add_field(
                            name=f"{medal} {dedication}",
                            value=f"<@{uid}> - **{count}** poles",
                            inline=False
                        )
                else:
                    if embed_poles_local.description:
                        embed_poles_local.description += "\n\n_Nadie compitió en esta categoría._"
                
                embed_poles_local.set_footer(text=f"Hall of Fame {old_season_id} • Siempre ahí.")
                await channel.send(embed=embed_poles_local)
                await asyncio.sleep(1.5)
                
                # ==================== MENSAJE 4: 🔥 MEJOR RACHA (Local) ====================
                embed_streak_local = discord.Embed(
                    title=f"{FIRE} DISCIPLINA MÁXIMA - {guild.name}",
                    description="Los que mantuvieron las rachas más largas:",
                    color=discord.Color.orange(),
                    timestamp=datetime.now()
                )
                
                if local_rankings['streaks']:
                    for i, (uid, streak) in enumerate(local_rankings['streaks'][:3], 1):
                        medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉'
                        dedication = self._get_dedication_streak(i)
                        embed_streak_local.add_field(
                            name=f"{medal} {dedication}",
                            value=f"<@{uid}> - **{streak}** días consecutivos",
                            inline=False
                        )
                else:
                    if embed_streak_local.description:
                        embed_streak_local.description += "\n\n_Nadie compitió en esta categoría._"
                
                embed_streak_local.set_footer(text=f"Hall of Fame {old_season_id} • La disciplina es poder.")
                await channel.send(embed=embed_streak_local)
                await asyncio.sleep(1.5)
                
                # ==================== MENSAJE 5: ⚡ VELOCISTAS (Local) ====================
                embed_speed_local = discord.Embed(
                    title=f"⚡ VELOCISTAS - {guild.name}",
                    description="Los más rápidos en promedio (mínimo 10 poles):",
                    color=discord.Color.blue(),
                    timestamp=datetime.now()
                )
                
                if local_rankings['speed']:
                    for i, (uid, delay) in enumerate(local_rankings['speed'][:3], 1):
                        medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉'
                        dedication = self._get_dedication_speed(i)
                        embed_speed_local.add_field(
                            name=f"{medal} {dedication}",
                            value=f"<@{uid}> - **{delay:.1f}** min promedio",
                            inline=False
                        )
                else:
                    if embed_speed_local.description:
                        embed_speed_local.description += "\n\n_No hay suficientes datos._"
                
                embed_speed_local.set_footer(text=f"Hall of Fame {old_season_id} • Reflejos de campeón.")
                await channel.send(embed=embed_speed_local)
                await asyncio.sleep(2)
                
                # ==================== MENSAJE 6: 🌍 HALL OF FAME GLOBAL (CONDENSADO) ====================
                embed_global = discord.Embed(
                    title="🌍 HALL OF FAME GLOBAL",
                    description=f"Las leyendas que dominaron **TODOS** los servidores en {old_season_id}:",
                    color=discord.Color.purple(),
                    timestamp=datetime.now()
                )
                
                # Puntos
                if global_rankings['points']:
                    points_text = "**👑 Máximos Anotadores**\n"
                    for i, (uid, pts) in enumerate(global_rankings['points'][:3], 1):
                        medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉'
                        points_text += f"{medal} <@{uid}> - **{pts:,}** pts\n"
                    embed_global.add_field(name="\u200b", value=points_text, inline=False)
                
                # Poles
                if global_rankings['poles']:
                    poles_text = "**⚡ Polemaniáticos**\n"
                    for i, (uid, count) in enumerate(global_rankings['poles'][:3], 1):
                        medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉'
                        poles_text += f"{medal} <@{uid}> - **{count}** poles\n"
                    embed_global.add_field(name="\u200b", value=poles_text, inline=False)
                
                # Rachas
                if global_rankings['streaks']:
                    streak_text = f"**{FIRE} Disciplina Máxima**\n"
                    for i, (uid, streak) in enumerate(global_rankings['streaks'][:3], 1):
                        medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉'
                        streak_text += f"{medal} <@{uid}> - **{streak}** días\n"
                    embed_global.add_field(name="\u200b", value=streak_text, inline=False)
                
                # Velocidad
                if global_rankings['speed']:
                    speed_text = "**⚡ Velocistas** (min 10 poles)\n"
                    for i, (uid, delay) in enumerate(global_rankings['speed'][:3], 1):
                        medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉'
                        speed_text += f"{medal} <@{uid}> - **{delay:.1f}** min\n"
                    embed_global.add_field(name="\u200b", value=speed_text, inline=False)
                
                if not any([global_rankings['points'], global_rankings['poles'], 
                           global_rankings['streaks'], global_rankings['speed']]):
                    if embed_global.description:
                        embed_global.description += "\n\n_Sin datos globales para esta temporada._"
                
                embed_global.set_footer(text="Leyendas del Pole Bot • Nivel Dios")
                await channel.send(embed=embed_global)
                await asyncio.sleep(2)
                
                # ==================== MENSAJE 7: NUEVA TEMPORADA ====================
                if is_first_season:
                    embed_new_season = discord.Embed(
                        title=f"🚀 BIENVENIDOS A LA {new_info['name'].upper()}",
                        description=(
                            "Se acabó la beta. Ahora va **EN SERIO**.\n\n"
                            f"Esta es la **TEMPORADA 1** oficial del Pole Bot. "
                            "Todo lo anterior fue práctica.\n\n"
                            "♻️ Puntos a 0. Rachas a 0.\n"
                            "💎 Tus badges BETA se quedan contigo.\n\n"
                            "Todos empezamos igual. Que gane el que más lo quiera.\n\n"
                            "La competencia oficial empieza... **AHORA**. 🏁"
                        ),
                        color=discord.Color.green(),
                        timestamp=datetime.now()
                    )
                else:
                    embed_new_season = discord.Embed(
                        title=f"🚀 BIENVENIDOS A LA {new_info['name'].upper()}",
                        description=(
                            f"Se acabó mirar atrás. Desde hoy, borrón y cuenta nueva:\n\n"
                            "♻️ Puntos reseteados a 0\n"
                            "♻️ Rachas reseteadas a 0\n"
                            "💎 Tus badges se quedan contigo (honor)\n\n"
                            f"La {new_info['name']} arranca **YA**. Todos empezamos desde cero, "
                            "con las mismas posibilidades.\n\n"
                            "Que gane el mejor. 🏁"
                        ),
                        color=discord.Color.green(),
                        timestamp=datetime.now()
                    )
                
                embed_new_season.add_field(
                    name="📅 Duración de Temporada",
                    value=f"Desde **{new_info['start_date']}** hasta **{new_info['end_date']}**",
                    inline=False
                )
                
                embed_new_season.set_footer(text=f"¡Que comience la competencia! {FIRE}")
                await channel.send(embed=embed_new_season)
                
                sent_count += 1
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"⚠️ Error enviando POLE REWIND a guild {server['guild_id']}: {e}")
                import traceback
                traceback.print_exc()
        
        print(f"🎬 POLE REWIND enviado a {sent_count} servidores")
    
    # ==================== DEDICATORIAS POLE REWIND ====================
    def _get_dedication_points(self, position: int) -> str:
        """Dedicatoria para categoría Puntos (local)"""
        if position == 1:
            return "El Rey de la Consistencia"
        elif position == 2:
            return "Segundo pero Letal"
        else:
            return "Bronce con Honor"
    
    def _get_dedication_poles(self, position: int) -> str:
        """Dedicatoria para categoría Poles (local)"""
        if position == 1:
            return "El Polemaniático Supremo"
        elif position == 2:
            return "Siempre Segundo, Nunca Olvidado"
        else:
            return "Competencia de Élite"
    
    def _get_dedication_streak(self, position: int) -> str:
        """Dedicatoria para categoría Rachas (local)"""
        if position == 1:
            return "La Disciplina Hecha Persona"
        elif position == 2:
            return "Constancia de Acero"
        else:
            return "Disciplina Inquebrantable"
    
    def _get_dedication_speed(self, position: int) -> str:
        """Dedicatoria para categoría Velocidad (local)"""
        if position == 1:
            return "Reflejos de Rayo"
        elif position == 2:
            return "Velocidad Supersónica"
        else:
            return "Rápido como el Viento"
    
    def _get_dedication_points_global(self, position: int) -> str:
        """Dedicatoria para categoría Puntos (global)"""
        if position == 1:
            return "El Titán de los Puntos"
        elif position == 2:
            return "Leyenda Viviente"
        else:
            return "Monstruo de Competición"
    
    def _get_dedication_poles_global(self, position: int) -> str:
        """Dedicatoria para categoría Poles (global)"""
        if position == 1:
            return "Obsesión Nivel Dios"
        elif position == 2:
            return "Adicción Pura y Dura"
        else:
            return "Siempre en el Top"
    
    def _get_dedication_streak_global(self, position: int) -> str:
        """Dedicatoria para categoría Rachas (global)"""
        if position == 1:
            return "Constancia Sobrehumana"
        elif position == 2:
            return "Nunca Falta"
        else:
            return "Compromiso Total"
    
    def _get_dedication_speed_global(self, position: int) -> str:
        """Dedicatoria para categoría Velocidad (global)"""
        if position == 1:
            return "Velocidad de la Luz"
        elif position == 2:
            return "Flash Hecho Persona"
        else:
            return "Reflejos Inhumanos"
    
    def _get_season_rankings_local(self, guild_id: int, season_id: str) -> dict:
        """Obtener rankings completos de un servidor (filtro: min 500 pts + min 10 poles para velocidad)"""
        from utils.scoring import RANK_THRESHOLDS
        MIN_RANK_POINTS = RANK_THRESHOLDS['silver']  # 500 puntos (rango Plata)
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Top 3 Puntos (mínimo rango Plata)
            cursor.execute('''
                SELECT user_id, season_points
                FROM season_stats
                WHERE guild_id = ? AND season_id = ?
                  AND season_points >= ?
                ORDER BY season_points DESC
                LIMIT 3
            ''', (guild_id, season_id, MIN_RANK_POINTS))
            top_points = [(row[0], row[1]) for row in cursor.fetchall()]
            
            # Top 3 Poles (mínimo rango Plata)
            cursor.execute('''
                SELECT user_id, season_poles
                FROM season_stats
                WHERE guild_id = ? AND season_id = ?
                  AND season_points >= ?
                ORDER BY season_poles DESC
                LIMIT 3
            ''', (guild_id, season_id, MIN_RANK_POINTS))
            top_poles = [(row[0], row[1]) for row in cursor.fetchall()]
            
            # Top 3 Rachas (mínimo rango Plata)
            cursor.execute('''
                SELECT user_id, season_best_streak
                FROM season_stats
                WHERE guild_id = ? AND season_id = ?
                  AND season_points >= ?
                ORDER BY season_best_streak DESC
                LIMIT 3
            ''', (guild_id, season_id, MIN_RANK_POINTS))
            top_streaks = [(row[0], row[1]) for row in cursor.fetchall()]
            
            # Top 3 Velocidad (mínimo rango Plata + mínimo 10 poles)
            cursor.execute('''
                SELECT ss.user_id, u.average_delay_minutes
                FROM season_stats ss
                JOIN users u ON ss.user_id = u.user_id AND ss.guild_id = u.guild_id
                WHERE ss.guild_id = ? AND ss.season_id = ?
                  AND ss.season_points >= ?
                  AND u.average_delay_minutes > 0
                  AND ss.season_poles >= 10
                ORDER BY u.average_delay_minutes ASC
                LIMIT 3
            ''', (guild_id, season_id, MIN_RANK_POINTS))
            top_speed = [(row[0], row[1]) for row in cursor.fetchall()]
        
        return {
            'points': top_points,
            'poles': top_poles,
            'streaks': top_streaks,
            'speed': top_speed
        }
    
    def _get_season_rankings_global(self, season_id: str) -> dict:
        """Obtener rankings globales (filtro: min 500 pts total + min 10 poles para velocidad)"""
        from utils.scoring import RANK_THRESHOLDS
        MIN_RANK_POINTS = RANK_THRESHOLDS['silver']  # 500 puntos (rango Plata)
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Top 3 Puntos Global (mínimo rango Plata)
            cursor.execute('''
                SELECT user_id, SUM(season_points) as total_points
                FROM season_stats
                WHERE season_id = ?
                GROUP BY user_id
                HAVING total_points >= ?
                ORDER BY total_points DESC
                LIMIT 3
            ''', (season_id, MIN_RANK_POINTS))
            top_points = [(row[0], row[1]) for row in cursor.fetchall()]
            
            # Top 3 Poles Global (mínimo rango Plata)
            cursor.execute('''
                SELECT user_id, SUM(season_poles) as total_poles
                FROM season_stats
                WHERE season_id = ?
                GROUP BY user_id
                HAVING SUM(season_points) >= ?
                ORDER BY total_poles DESC
                LIMIT 3
            ''', (season_id, MIN_RANK_POINTS))
            top_poles = [(row[0], row[1]) for row in cursor.fetchall()]
            
            # Top 3 Rachas Global (mínimo rango Plata)
            cursor.execute('''
                SELECT user_id, MAX(season_best_streak) as best_streak
                FROM season_stats
                WHERE season_id = ?
                GROUP BY user_id
                HAVING SUM(season_points) >= ?
                ORDER BY best_streak DESC
                LIMIT 3
            ''', (season_id, MIN_RANK_POINTS))
            top_streaks = [(row[0], row[1]) for row in cursor.fetchall()]
            
            # Top 3 Velocidad Global (mínimo rango Plata + mínimo 10 poles)
            cursor.execute('''
                SELECT u.user_id, AVG(u.average_delay_minutes) as avg_delay
                FROM users u
                JOIN season_stats ss ON u.user_id = ss.user_id AND u.guild_id = ss.guild_id
                WHERE ss.season_id = ? 
                  AND u.average_delay_minutes > 0
                GROUP BY u.user_id
                HAVING SUM(ss.season_poles) >= 10 AND SUM(ss.season_points) >= ?
                ORDER BY avg_delay ASC
                LIMIT 3
            ''', (season_id, MIN_RANK_POINTS))
            top_speed = [(row[0], row[1]) for row in cursor.fetchall()]
        
        return {
            'points': top_points,
            'poles': top_poles,
            'streaks': top_streaks,
            'speed': top_speed
        }
    
    @daily_pole_generator.before_loop
    async def before_daily_generator(self):
        """Esperar a que el bot esté listo y sincronizar a medianoche"""
        await self.bot.wait_until_ready()
        
        # Calcular tiempo hasta próxima medianoche
        now = datetime.now()
        next_midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        wait_seconds = (next_midnight - now).total_seconds()
        
        print(f"⏰ Esperando {wait_seconds/3600:.1f}h hasta medianoche para generar horas diarias")
        await asyncio.sleep(wait_seconds)
    
    @tasks.loop(seconds=30)  # Revisar cada 30 segundos para mayor precisión
    async def check_opening_notification(self):
        """Desactivado: reemplazado por programaciones exactas por servidor."""
        return
    
    @check_opening_notification.before_loop
    async def before_opening_check(self):
        """Esperar a que el bot esté listo"""
        await self.bot.wait_until_ready()
    
    async def send_opening_notification(self, guild_id: int, channel_id: int, ping_role_id: Optional[int], ping_mode: str):
        """
        Enviar notificación de apertura del pole
        """
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return
        
        channel = guild.get_channel(channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            return
        
        # Antes de abrir: resetear rachas que realmente se perdieron (no hicieron ni pole ayer ni marranero hoy)
        try:
            await self._reset_lost_streaks_before_opening(guild_id, channel_id)
        except Exception as e:
            print(f"⚠️ Error reseteando rachas antes de apertura en guild {guild_id}: {e}")

        # Construir mensaje con ping opcional
        content = ""
        if ping_mode == 'role' and ping_role_id:
            role = guild.get_role(ping_role_id)
            if role:
                content = f"{role.mention} "
        elif ping_mode == 'everyone':
            content = "@everyone "
        
        embed = discord.Embed(
            title="🔔 POLE ABIERTO",
            description=(
                "Llegó la hora: suelta ese **pole** y suma puntos 🏁\n"
                "El primero manda, el resto acompaña."
            ),
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.set_footer(text="Que empiece la poleada ✨")
        
        try:
            await channel.send(content=content if content else None, embed=embed)
        except Exception as e:
            print(f"❌ Error enviando notificación a guild {guild_id}: {e}")

    async def _reset_lost_streaks_before_opening(self, guild_id: int, channel_id: int):
        """Resetear rachas perdidas justo antes de la apertura de hoy y avisar al canal.

        Regla: pierden racha quienes no hicieron pole ayer ni marranero hoy.
        """
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return
        channel = guild.get_channel(channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            return

        yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')

        # Usuarios que hicieron pole ayer EN CUALQUIER SERVIDOR (racha es global)
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT DISTINCT user_id
                FROM poles
                WHERE pole_date = ? OR (pole_date IS NULL AND DATE(created_at) = ?)
            ''', (yesterday, yesterday))
            did_pole_yesterday_global = {row[0] for row in cursor.fetchall()}

            # Usuarios que hicieron marranero hoy EN CUALQUIER SERVIDOR (recuperaron el día de ayer)
            today = datetime.now().strftime('%Y-%m-%d')
            cursor.execute('''
                SELECT DISTINCT user_id
                FROM poles
                WHERE pole_date = ? AND pole_type = 'marranero'
            ''', (yesterday,))  # Marranero tiene pole_date = ayer
            did_marranero_today = {row[0] for row in cursor.fetchall()}

        protected_users = did_pole_yesterday_global.union(did_marranero_today)

        # Obtener todos los usuarios con rachas GLOBALES activas
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, username, current_streak
                FROM global_users
                WHERE current_streak > 0
            ''')
            global_users_with_streaks = cursor.fetchall()

        lost_members = []
        for gu in global_users_with_streaks:
            if gu['user_id'] not in protected_users:
                # Resetear racha GLOBAL
                self.db.update_global_user(gu['user_id'], current_streak=0)
                
                # Solo notificar si el usuario está en ESTE servidor
                member = guild.get_member(gu['user_id'])
                if member:
                    lost_members.append(member)

        if lost_members:
            names_text = ", ".join(m.mention for m in lost_members[:10])
            more = len(lost_members) - 10
            if more > 0:
                names_text += f" y {more} más"
            try:
                await channel.send(
                    content=None,
                    embed=discord.Embed(
                        title="💔 Racha perdida",
                        description=f"{names_text}\nLa racha se ha reiniciado por no completar ayer.",
                        color=discord.Color.red(),
                        timestamp=datetime.now()
                    )
                )
            except Exception as e:
                print(f"⚠️ Error avisando racha perdida en guild {guild_id}: {e}")

    # ==================== SCHEDULER EXACTO DE NOTIFICACIONES ====================
    async def schedule_all_today_notifications(self):
        """Programar una tarea exacta por servidor para enviar la notificación a la hora configurada de hoy."""
        await self.bot.wait_until_ready()
        now = datetime.now()
        today_key = now.date().isoformat()
        
        # Limpiar tareas anteriores para evitar duplicados
        for gid, task in list(self._scheduled_notifications.items()):
            if task.done() or task.cancelled():
                self._scheduled_notifications.pop(gid, None)
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT guild_id, pole_channel_id, daily_pole_time, notify_opening, ping_role_id, ping_mode
                FROM servers
                WHERE pole_channel_id IS NOT NULL
                  AND notify_opening = 1
                  AND daily_pole_time IS NOT NULL
            ''')
            servers = cursor.fetchall()
        
        for server in servers:
            guild_id = server['guild_id']
            channel_id = server['pole_channel_id']
            daily_time = server['daily_pole_time']
            
            # Verificar que el servidor existe
            if not self.bot.get_guild(guild_id):
                continue
            
            try:
                h, m, s = [int(x) for x in str(daily_time).split(':')]
                opening_time = datetime(now.year, now.month, now.day, h, m, s)
            except Exception:
                continue
            # Si la hora ya pasó, no programar (evitar envíos tardíos)
            if opening_time <= now:
                continue
            await self._schedule_single_notification(
                guild_id, channel_id, opening_time,
                server['ping_role_id'], server['ping_mode'], today_key
            )

    async def _schedule_single_notification(self, guild_id: int, channel_id: int, opening_time: datetime,
                                            ping_role_id: Optional[int], ping_mode: str, today_key: str):
        """Programar una notificación única para un servidor a una hora exacta."""
        # Cancelar si ya hay una tarea pendiente para ese guild
        existing = self._scheduled_notifications.get(guild_id)
        if existing and not existing.done() and not existing.cancelled():
            try:
                existing.cancel()
            except:
                pass
        
        async def runner():
            try:
                now = datetime.now()
                delay = (opening_time - now).total_seconds()
                if delay > 0:
                    await asyncio.sleep(delay)
                # Evitar duplicado por si se reprogramó
                key = (guild_id, today_key)
                if key in self._notified_openings:
                    return
                await self.send_opening_notification(guild_id, channel_id, ping_role_id, ping_mode)
                self._notified_openings.add(key)
            except asyncio.CancelledError:
                pass
            except Exception as e:
                print(f"❌ Error en scheduler de guild {guild_id}: {e}")
        
        task = asyncio.create_task(runner())
        self._scheduled_notifications[guild_id] = task
    
    # ==================== VIGILANTE DE NOTIFICACIONES (FAILSAFE) ====================
    @tasks.loop(minutes=1)
    async def opening_notification_watcher(self):
        """
        Vigilante que verifica cada minuto si se perdió alguna notificación de apertura.
        Esto es un failsafe por si el scheduler de asyncio.sleep() falla.
        
        Escenario: Si el bot se reinicia o pierde conexión después de medianoche pero antes
        de la hora del pole, el task programado se pierde. Este vigilante lo detecta y
        envía la notificación tardía.
        """
        now = datetime.now()
        today_str = now.date().isoformat()
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT guild_id, pole_channel_id, daily_pole_time, notify_opening, ping_role_id, ping_mode
                FROM servers
                WHERE pole_channel_id IS NOT NULL
                  AND notify_opening = 1
                  AND daily_pole_time IS NOT NULL
            ''')
            servers = cursor.fetchall()
        
        for server in servers:
            guild_id = server['guild_id']
            channel_id = server['pole_channel_id']
            daily_time = server['daily_pole_time']
            
            notif_key = (guild_id, today_str)
            
            # Si ya notificamos hoy, saltar
            if notif_key in self._notified_openings:
                continue
            
            # Parsear hora de apertura
            try:
                h, m, s = [int(x) for x in str(daily_time).split(':')]
                opening_time = datetime(now.year, now.month, now.day, h, m, s)
            except Exception:
                continue
            
            # Si la hora aún no llegó, hay que esperar (el scheduler debería encargarse)
            if now < opening_time:
                # Verificar si el scheduler está activo para este guild
                scheduled_task = self._scheduled_notifications.get(guild_id)
                if scheduled_task is None or scheduled_task.done() or scheduled_task.cancelled():
                    # El task no existe o murió, reprogramar
                    print(f"⚠️ [Watcher] Reprogramando notificación para guild {guild_id} (task perdido)")
                    await self._schedule_single_notification(
                        guild_id, channel_id, opening_time,
                        server['ping_role_id'], server['ping_mode'], today_str
                    )
                continue
            
            # La hora ya pasó y no hemos notificado - NOTIFICACIÓN PERDIDA
            # Calcular cuánto tiempo pasó desde la apertura
            minutes_since_opening = (now - opening_time).total_seconds() / 60
            
            # Solo enviar si no han pasado más de 60 minutos (evitar spam tardío)
            if minutes_since_opening > 60:
                # Demasiado tarde, marcar como notificado para no reintentar
                self._notified_openings.add(notif_key)
                print(f"⚠️ [Watcher] Guild {guild_id}: Notificación descartada (>{int(minutes_since_opening)}m tarde)")
                continue
            
            # Dar un margen de 2 minutos después de la apertura antes de intervenir
            # Esto evita conflictos con el scheduler normal que podría estar ejecutándose
            if minutes_since_opening < 2:
                continue
            
            # Verificar si hay un task activo que quizás aún no terminó
            scheduled_task = self._scheduled_notifications.get(guild_id)
            if scheduled_task and not scheduled_task.done() and not scheduled_task.cancelled():
                # Hay un task pendiente, darle unos segundos más
                continue
            
            # ENVIAR NOTIFICACIÓN PERDIDA (independientemente de si ya hay poles)
            # Si la gente ya poleó sin notificación, al menos avisamos para futuros participantes
            print(f"🔔 [Watcher] Enviando notificación perdida para guild {guild_id} ({int(minutes_since_opening)}m tarde)")
            
            try:
                # ⚠️ NO resetear rachas si ya pasó tiempo desde la apertura
                # Los usuarios pueden haber poleado ya, resetear ahora sería injusto
                # El reset de rachas solo debe ocurrir JUSTO ANTES de la apertura programada
                # Si hay outage y recuperamos tarde, las rachas ya están en su estado correcto
                
                # Enviar notificación
                await self.send_opening_notification(
                    guild_id, channel_id,
                    server['ping_role_id'], server['ping_mode']
                )
                self._notified_openings.add(notif_key)
                print(f"✅ [Watcher] Notificación enviada para guild {guild_id}")
            except Exception as e:
                print(f"❌ [Watcher] Error enviando notificación para guild {guild_id}: {e}")
    
    @opening_notification_watcher.before_loop
    async def before_opening_watcher(self):
        """Esperar a que el bot esté listo"""
        await self.bot.wait_until_ready()
        # Pequeña espera para que el scheduler principal tenga tiempo de programar
        await asyncio.sleep(5)

    # ==================== RESUMEN DE MEDIANOCHE ====================
    @tasks.loop(minutes=5)
    async def midnight_summary_check(self):
        """Enviar resumen a las 00:00 mostrando quién NO hizo pole y avisar que pierden racha"""
        now = datetime.now()
        
        # Solo ejecutar entre 00:00 y 00:15
        if not (now.hour == 0 and now.minute < 15):
            return
        
        today_key = now.date().isoformat()
        
        # Iterar por servidores activos
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT guild_id, pole_channel_id
                FROM servers
                WHERE pole_channel_id IS NOT NULL
            ''')
            servers = cursor.fetchall()
        
        for server in servers:
            guild_id = server['guild_id']
            channel_id = server['pole_channel_id']
            summary_key = (guild_id, today_key)
            
            # Evitar duplicados
            if summary_key in self._midnight_summaries_sent:
                continue
            
            await self.send_midnight_summary(guild_id, channel_id)
            self._midnight_summaries_sent.add(summary_key)
            
            # Limpiar summaries antiguos
            yesterday_key = (now - timedelta(days=1)).date().isoformat()
            self._midnight_summaries_sent = {
                (gid, date) for gid, date in self._midnight_summaries_sent
                if date >= yesterday_key
            }
    
    @midnight_summary_check.before_loop
    async def before_midnight_check(self):
        """Esperar a que el bot esté listo"""
        await self.bot.wait_until_ready()
    
    async def send_midnight_summary(self, guild_id: int, channel_id: int):
        """Enviar resumen de medianoche con estadísticas del día anterior"""
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return
        
        channel = guild.get_channel(channel_id)
        if not channel or not isinstance(channel, discord.TextChannel):
            return
        
        # Obtener poles del día ANTERIOR (ya es medianoche del nuevo día)
        yesterday = datetime.now() - timedelta(days=1)
        today = datetime.now().strftime('%Y-%m-%d')
        yesterday_date = yesterday.strftime('%Y-%m-%d')
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            # Buscar poles con pole_date = ayer O marraneros de hoy con pole_date = ayer
            cursor.execute('''
                SELECT user_id, pole_type, points_earned, created_at
                FROM poles
                WHERE guild_id = ? AND (pole_date = ? OR (pole_date = ? AND pole_type = 'marranero'))
                ORDER BY created_at ASC
            ''', (guild_id, yesterday_date, yesterday_date))
            yesterday_poles = [dict(row) for row in cursor.fetchall()]
        
        if not yesterday_poles:
            # No enviar si nadie hizo pole ayer
            return
        
        # Usuarios con racha activa que NO hicieron pole ayer
        # Obtener todos los user_ids del servidor
        all_users = self.db.get_leaderboard(guild_id, 1000)
        users_streak_at_risk = []  # No hicieron pole en ningún servidor (racha en peligro)
        users_pole_elsewhere = []  # Hicieron pole en otro servidor (racha salvada)
        user_ids_with_pole = {p['user_id'] for p in yesterday_poles}

        for user_data in all_users:
            # Obtener racha GLOBAL del usuario
            global_user = self.db.get_global_user(user_data['user_id'])
            if not global_user:
                continue
            
            current_streak = int(global_user.get('current_streak', 0))
            if current_streak > 0 and user_data['user_id'] not in user_ids_with_pole:
                member = guild.get_member(user_data['user_id'])
                if member:
                    # Verificar si hizo pole en OTRO servidor
                    global_pole = self.db.get_user_pole_on_date_global(user_data['user_id'], yesterday_date)
                    if global_pole and int(global_pole.get('guild_id', 0)) != guild_id:
                        # Hizo pole en otro servidor
                        other_guild = self.bot.get_guild(int(global_pole['guild_id']))
                        other_guild_name = other_guild.name if other_guild else f"ID {global_pole['guild_id']}"
                        users_pole_elsewhere.append({
                            'member': member,
                            'streak': current_streak,
                            'other_guild': other_guild_name
                        })
                    else:
                        # No hizo pole en ningún servidor
                        users_streak_at_risk.append({
                            'member': member,
                            'streak': current_streak
                        })
        
        # Crear embed de resumen
        embed = discord.Embed(
            title="🌃 Resumen del Día",
            description=f"**{len(yesterday_poles)}** miembros completaron su pole ayer",
            color=discord.Color.dark_blue(),
            timestamp=datetime.now()
        )
        
        # Lista de jugadores que hicieron pole ayer (top 10)
        if yesterday_poles:
            pole_list = ""
            for idx, pole in enumerate(yesterday_poles[:10], start=1):
                member = guild.get_member(pole['user_id'])
                if member:
                    emoji = get_pole_emoji(pole.get('pole_type', 'normal'))
                    pole_list += f"{idx}. {emoji} {member.mention}\n"
            
            if pole_list:
                embed.add_field(
                    name="✅ Completaron su pole ayer",
                    value=pole_list,
                    inline=False
                )
        
        # Advertencia: racha en peligro (marranero disponible hasta la nueva apertura)
        if users_streak_at_risk:
            streak_warning = (
                f"⚠️ **{len(users_streak_at_risk)}** con la racha en el filo:\n\n"
            )
            for user_info in users_streak_at_risk[:5]:
                streak_warning += f"⏳ {user_info['member'].mention} (racha {user_info['streak']} días)\n"
            if len(users_streak_at_risk) > 5:
                streak_warning += f"\n_...y {len(users_streak_at_risk) - 5} más_"
            streak_warning += "\n\n🐷 Aún puedes hacer el **marranero** hasta la próxima apertura."

            embed.add_field(
                name=f"⏳ Racha en Peligro",
                value=streak_warning,
                inline=False
            )
        
        # Info: usuarios que hicieron pole en otro servidor
        if users_pole_elsewhere:
            elsewhere_info = ""
            for user_info in users_pole_elsewhere[:10]:
                elsewhere_info += f"🌍 {user_info['member'].mention} en **{user_info['other_guild']}** (racha {user_info['streak']} días)\n"
            if len(users_pole_elsewhere) > 10:
                elsewhere_info += f"\n_...y {len(users_pole_elsewhere) - 10} más_"

            embed.add_field(
                name=f"🌍 Polearon en Otro Servidor ({len(users_pole_elsewhere)})",
                value=elsewhere_info,
                inline=False
            )
        
        # Info del nuevo día
        embed.add_field(
            name="🌅 Nuevo Día",
            value="Arranca la jornada: espera el ping y entra a polear.",
            inline=False
        )
        
        embed.set_footer(text="Resumen automático • Sin pings")
        
        try:
            await channel.send(embed=embed)
        except Exception as e:
            print(f"❌ Error enviando resumen de medianoche a guild {guild_id}: {e}")

# Setup function necesaria para cargar el cog
async def setup(bot):
    await bot.add_cog(PoleCog(bot))
