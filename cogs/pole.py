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
from typing import Optional

from utils.database import Database
from utils.scoring import (
    calculate_points, classify_delay, get_pole_emoji,
    get_pole_name, update_streak, get_rank_info, get_streak_multiplier,
    check_quota_available
)

# Emoji de fuego personalizado (usar en todo el bot)
FIRE = "<a:fire:1440018375144374302>"

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
        
        # No mostrar hora de apertura de hoy por equidad del juego
        
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
        
        # Iniciar tareas programadas v1.0
        self.daily_pole_generator.start()
        self.midnight_summary_check.start()
        # Programar notificaciones exactas para hoy al iniciar
        asyncio.create_task(self.schedule_all_today_notifications())
        
        print("✅ Pole Cog inicializado")
    
    async def cog_unload(self) -> None:
        """Detener tareas cuando se descarga el cog"""
        self.daily_pole_generator.cancel()
        self.midnight_summary_check.cancel()
        # Cancelar tareas programadas por servidor
        for task in list(self._scheduled_notifications.values()):
            try:
                task.cancel()
            except:
                pass

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
        Detectar mensajes de 'pole' y procesarlos
        """
        try:
            # Ignorar bots
            if message.author.bot:
                return
            
            # Ignorar si no está en un servidor
            if not message.guild:
                return
            guild = message.guild
            
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
        """
        now = datetime.now()
        guild = message.guild  # seguro por llamada desde on_message
        if guild is None:
            return
        server_config = self.db.get_server_config(guild.id) or {}
        daily_time = server_config.get('daily_pole_time')
        
        if not daily_time:
            try:
                await message.reply("⌛ Aún no se ha abierto el pole de hoy.")
            except:
                pass
            return

        # Construir datetime de apertura de hoy (local)
        try:
            h, m, s = [int(x) for x in str(daily_time).split(':')]
        except Exception:
            try:
                await message.reply("⚠️ Config de hora diaria inválida. Contacta a un admin.")
            except:
                pass
            return
        opening_time = datetime(now.year, now.month, now.day, h, m, s)

        # Bloquear si aún no ha abierto
        if now < opening_time:
            try:
                await message.add_reaction('⚠️')
            except:
                pass
            try:
                await message.reply("⏳ Aún no ha abierto. Espera al aviso.")
            except:
                pass
            return

        # Obtener poles del día y verificar duplicado del usuario
        today_poles = self.db.get_poles_today(guild.id)
        user_pole_today = any(p['user_id'] == message.author.id for p in today_poles)
        if user_pole_today:
            return

        # Verificación global: sólo 1 pole al día en cualquier servidor
        global_pole = self.db.get_user_pole_today_global(message.author.id)
        if global_pole and int(global_pole.get('guild_id', 0)) != guild.id:
            prev_guild = self.bot.get_guild(int(global_pole['guild_id']))
            prev_name = prev_guild.name if prev_guild else f"ID {global_pole['guild_id']}"
            try:
                await message.add_reaction('🚫')
            except:
                pass
            try:
                await message.reply(
                    f"❌ Sólo puedes hacer una pole al día a nivel global.\n"
                    f"Ya hiciste pole hoy en: **{prev_name}**."
                )
            except:
                pass
            return

        # Posición informativa
        position = len(today_poles) + 1

        # Calcular retraso y clasificar
        delay_minutes = int((now - opening_time).total_seconds() // 60)
        
        # Detectar si llegó al día siguiente (después de 00:00)
        # Si la apertura fue ayer y ahora es un nuevo día, es marranero
        is_next_day = opening_time.date() < now.date()
        
        pole_type = classify_delay(delay_minutes, is_next_day)
        
        # ====== VERIFICAR CUOTAS (solo para critical y fast) ======
        if pole_type in ['critical', 'fast']:
            # Contar cuántos poles de este tipo ya se reclamaron hoy
            poles_of_type = sum(1 for p in today_poles if p.get('pole_type') == pole_type)
            
            # Contar miembros del servidor (sin bots)
            total_members = sum(1 for m in guild.members if not m.bot)
            
            # Verificar cuota
            has_quota, current, max_allowed = check_quota_available(pole_type, poles_of_type, total_members)
            
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
                    has_quota, current, max_allowed = check_quota_available('fast', poles_of_type, total_members)
                    if not has_quota:
                        pole_type = 'normal'  # Degradar a normal (sin cuota)
                elif pole_type == 'fast':
                    pole_type = 'normal'  # Degradar a normal (sin cuota)
        
        # Obtener o crear usuario
        user = self._get_or_create_user_data(guild.id, message.author)
        
        # Asignar representación automáticamente si es su primer pole global
        represented = self.db.get_represented_guild(message.author.id)
        if represented is None:
            self.db.set_represented_guild(message.author.id, guild.id)
        
        # Actualizar racha
        current_streak = user['current_streak'] if user else 0
        last_pole_date = user['last_pole_date'] if user else None
        new_streak, streak_broken = update_streak(last_pole_date, current_streak)
        
        # Calcular puntos
        points_base, streak_multiplier, points_earned = calculate_points(pole_type, new_streak)
        
        # Guardar pole en historial (v1.0)
        self.db.save_pole(
            user_id=message.author.id,
            guild_id=guild.id,
            opening_time=opening_time,
            user_time=now,
            delay_minutes=delay_minutes,
            pole_type=pole_type,
            points_earned=points_earned,
            streak=new_streak
        )
        
        # Actualizar estadísticas del usuario (sin total_points/total_poles, se calculan desde seasons)
        best_streak = max(int(user['best_streak']), int(new_streak))
        
        update_data = {
            'current_streak': new_streak,
            'best_streak': best_streak,
            'last_pole_date': now.strftime('%Y-%m-%d'),
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
                await message.reply(f"✅ Pole capturado! +{points_earned:.1f} pts (Racha: {new_streak})")
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
        embed.add_field(name="⏳ Retraso", value=f"{delay_minutes} min", inline=True)
        embed.add_field(name="📍 Posición", value=f"#{position}", inline=True)
        
        # Información de puntos
        embed.add_field(
            name="💰 Puntos Base",
            value=f"{points_base:.1f} pts",
            inline=True
        )
        
        if streak > 1:
            embed.add_field(
                name=f"{FIRE} Racha x{multiplier:.1f}",
                value=f"{streak} días",
                inline=True
            )
        else:
            embed.add_field(
                name=f"{FIRE} Racha",
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
    
    @app_commands.command(name="profile", description="Ver perfil y estadísticas de un usuario")
    @app_commands.describe(usuario="Usuario del que ver perfil (opcional)")
    async def profile(self, interaction: discord.Interaction, usuario: Optional[discord.Member] = None):
        """Ver perfil y estadísticas de un usuario"""
        if interaction.guild is None:
            await interaction.response.send_message("❌ Este comando solo funciona en servidores.", ephemeral=True)
            return
        
        from utils.scoring import get_current_season
        
        gid = interaction.guild.id
        target_user = usuario or interaction.user
        
        # Obtener datos del usuario (all-time)
        user_data = self.db.get_user(target_user.id, gid)
        
        if not user_data or user_data['total_poles'] == 0:
            await interaction.response.send_message(
                f"❌ {target_user.mention} aún no ha hecho ningún pole.",
                ephemeral=True
            )
            return
        
        # Obtener stats de la temporada actual
        current_season_id = get_current_season()
        season_stats = self.db.get_season_stats(target_user.id, gid, current_season_id)
        
        # Obtener rango histórico basado en el mejor desempeño en cualquier temporada
        best_season_points = self.db.get_user_best_season_points(target_user.id, gid)
        rank_emoji, rank_name = get_rank_info(best_season_points)
        
        # Crear embed
        embed = discord.Embed(
            title=f"📊 Estadísticas de {target_user.display_name}",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.set_thumbnail(url=target_user.display_avatar.url)
        
        # Mostrar badge de temporada actual si existe
        if season_stats and season_stats.get('season_poles', 0) > 0:
            season_rank_emoji, season_rank_name = get_rank_info(season_stats['season_points'])
            embed.add_field(
                name="🎖️ Temporada Actual",
                value=f"{season_rank_emoji} **{season_rank_name}**\n💰 {season_stats['season_points']:.1f} pts esta temporada",
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
            value=f"**{user_data['total_points']:.1f}** pts",
            inline=True
        )
        
        # Poles totales
        embed.add_field(
            name="🏁 Poles Totales",
            value=f"**{user_data['total_poles']}**",
            inline=True
        )
        
        # Racha actual
        streak_emoji = FIRE if user_data['current_streak'] > 0 else "💀"
        embed.add_field(
            name=f"{streak_emoji} Racha Actual",
            value=f"**{user_data['current_streak']}** días",
            inline=True
        )
        
        # Mejor racha
        embed.add_field(
            name=f"{FIRE} Mejor Racha",
            value=f"**{user_data.get('best_streak', 0)}** días",
            inline=True
        )
        
        # Desglose por tipo
        breakdown = (
            f"💎 Críticas: **{user_data.get('critical_poles', 0)}**\n"
            f"⚡ Veloz: **{user_data.get('fast_poles', 0)}**\n"
            f"🏁 Normales: **{user_data.get('normal_poles', 0)}**\n"
            f"🐷 Marraneros: **{user_data.get('marranero_poles', 0)}**"
        )
        embed.add_field(
            name="📈 Desglose de Poles",
            value=breakdown,
            inline=False
        )
        
        # Último pole
        footer_text = ""
        if user_data['last_pole_date']:
            last_date = datetime.strptime(user_data['last_pole_date'], '%Y-%m-%d')
            footer_text = f"Último pole: {last_date.strftime('%d/%m/%Y')}"
        
        footer_text += f" • Usa /season para ver progreso de temporada"
        embed.set_footer(text=footer_text)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="leaderboard", description="Ver ranking de poles")
    @app_commands.describe(
        alcance="Alcance del ranking: local (este servidor) o global (todos los servidores)",
        tipo="Tipo de ranking: personas o servidores",
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
            app_commands.Choice(name="Servidores", value="servers")
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
        if limite < 1 or limite > 25:
            await interaction.response.send_message(
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
                await interaction.response.send_message("❌ Este comando solo funciona en servidores.", ephemeral=True)
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
                await interaction.response.send_message(
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
                if is_lifetime and user_data.get('current_streak', 0) > 0:
                    streak_info = f" • {FIRE} {user_data['current_streak']}"
                
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
                await interaction.response.send_message("❌ Este comando solo funciona en servidores.", ephemeral=True)
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
                await interaction.response.send_message(
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
                await interaction.response.send_message(
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
                if is_lifetime and user_data.get('current_streak', 0) > 0:
                    streak_info = f" • {FIRE} {user_data['current_streak']}"
                
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
                await interaction.response.send_message(
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
        
        await interaction.response.send_message(embed=embed)
    
    @leaderboard.autocomplete('temporada')
    async def temporada_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """Autocompletar opciones de temporada dinámicamente"""
        from utils.scoring import get_current_season
        
        choices = []
        
        # Opción Lifetime siempre disponible
        choices.append(app_commands.Choice(name="🏆 Lifetime (Todos los tiempos)", value="lifetime"))
        
        # Obtener seasons disponibles
        try:
            seasons = self.db.get_available_seasons()
            current_season_id = get_current_season()
            
            for season in seasons:
                # Determinar si es la activa
                is_active = season['season_id'] == current_season_id or season.get('is_active', False)
                
                # Formatear nombre
                if is_active:
                    display_name = f"⭐ {season['season_name']} (Actual)"
                else:
                    display_name = f"📅 {season['season_name']}"
                
                choices.append(app_commands.Choice(
                    name=display_name,
                    value=season['season_id']
                ))
        except Exception as e:
            print(f"Error obteniendo seasons para autocomplete: {e}")
        
        # Filtrar por texto actual
        if current:
            choices = [c for c in choices if current.lower() in c.name.lower()]
        
        # Discord limita a 25 opciones
        return choices[:25]
    
    @app_commands.command(name="streak", description="Ver información detallada de tu racha")
    async def streak(self, interaction: discord.Interaction):
        """Ver información de racha del usuario"""
        if interaction.guild is None:
            await interaction.response.send_message("❌ Este comando solo funciona en servidores.", ephemeral=True)
            return
        gid = interaction.guild.id
        user_data = self.db.get_user(interaction.user.id, gid)
        
        if not user_data or user_data['total_poles'] == 0:
            await interaction.response.send_message(
                "❌ Aún no has hecho ningún pole.",
                ephemeral=True
            )
            return
        
        # Crear embed
        embed = discord.Embed(
            title=f"{FIRE} Tu Racha de Pole",
            color=discord.Color.orange() if user_data['current_streak'] > 0 else discord.Color.red(),
            timestamp=datetime.now()
        )
        
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        # Racha actual
        if user_data['current_streak'] > 0:
            multiplier = get_streak_multiplier(user_data['current_streak'])
            
            embed.add_field(
                name=f"{FIRE} Racha Actual",
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
                name="💀 Racha Perdida",
                value="¡Empieza una nueva racha haciendo pole hoy!",
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
        
        await interaction.response.send_message(embed=embed)
    
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
    
    @tasks.loop(hours=24)
    async def daily_pole_generator(self):
        """
        Generar hora de apertura diaria a las 00:00 para cada servidor.
        Aplica margen de 8h: si ayer abrió después de las 20:00 (8pm),
        hoy no puede abrir antes de las 04:00 (4am).
        También verifica si hay cambio de temporada y envía mensaje de felicitación.
        """
        import random
        from utils.scoring import get_current_season, get_season_info
        
        now = datetime.now()
        # Solo ejecutar a medianoche (tolerancia de 5 min por loop)
        if now.hour != 0:
            return
        
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
            cursor.execute('SELECT guild_id FROM servers WHERE pole_channel_id IS NOT NULL')
            servers = cursor.fetchall()
        
        # Margen mínimo entre poles: 4 horas (configurable)
        MIN_HOURS_BETWEEN_POLES = 4
        
        for server in servers:
            guild_id = server['guild_id']
            
            # Obtener hora de apertura de ayer
            last_opening_str = self.db.get_last_pole_opening_time(guild_id)
            
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
                    
                    # Validar margen mínimo
                    if time_diff >= MIN_HOURS_BETWEEN_POLES:
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
        Enviar mensaje de felicitación de año nuevo y anuncio de cambio de temporada
        a todos los servidores configurados
        """
        from utils.scoring import get_season_info
        
        old_info = get_season_info(old_season_id)
        new_info = get_season_info(new_season_id)
        
        # Crear embed de anuncio
        embed = discord.Embed(
            title="🎊 ¡FELIZ AÑO NUEVO! 🎊",
            description=(
                f"✨ **¡Bienvenidos a {new_info['name']}!** ✨\n\n"
                f"La temporada anterior **{old_info['name']}** ha finalizado.\n"
                f"Tus estadísticas han sido guardadas en el historial.\n\n"
                f"🏆 **Puntos y rachas se han reseteado**\n"
                f"💎 **Tus badges ganados se mantienen para siempre**\n"
                f"{FIRE} **¡Es hora de comenzar de nuevo y alcanzar la cima!**\n\n"
                f"Usa `/profile` para ver tu progreso y `/history` para ver tus logros pasados."
            ),
            color=discord.Color.gold(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="📅 Nueva Temporada",
            value=f"**{new_info['name']}**\nDesde {new_info['start_date']} hasta {new_info['end_date']}",
            inline=False
        )
        
        embed.set_footer(text=f"¡Que comience la competencia! {FIRE}")
        embed.set_thumbnail(url="https://em-content.zobj.net/thumbs/120/twitter/348/party-popper_1f389.png")
        
        # Enviar a todos los servidores configurados
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
                if channel:
                    await channel.send(embed=embed)
                    sent_count += 1
                    await asyncio.sleep(1)  # Evitar rate limit
            except Exception as e:
                print(f"⚠️ Error enviando anuncio a guild {server['guild_id']}: {e}")
        
        print(f"✅ Mensaje de cambio de temporada enviado a {sent_count} servidores")
    
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
        
        # Construir mensaje con ping opcional
        content = ""
        if ping_mode == 'role' and ping_role_id:
            role = guild.get_role(ping_role_id)
            if role:
                content = f"{role.mention} "
        elif ping_mode == 'everyone':
            content = "@everyone "
        
        embed = discord.Embed(
            title="🔔 ¡EL POLE HA ABIERTO!",
            description=f"Escribe **pole** ahora para ganar puntos 🏁",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.set_footer(text="¡Suerte! 🔥")
        
        try:
            await channel.send(content=content if content else None, embed=embed)
        except Exception as e:
            print(f"❌ Error enviando notificación a guild {guild_id}: {e}")

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
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT user_id, pole_type, points_earned
                FROM poles
                WHERE guild_id = ? AND DATE(created_at) = ?
                ORDER BY created_at ASC
            ''', (guild_id, yesterday.strftime('%Y-%m-%d')))
            yesterday_poles = [dict(row) for row in cursor.fetchall()]
        
        if not yesterday_poles:
            # No enviar si nadie hizo pole ayer
            return
        
        # Obtener usuarios con rachas activas que NO hicieron pole ayer
        all_users = self.db.get_leaderboard(guild_id, 100)
        users_lost_streak = []
        user_ids_with_pole = {p['user_id'] for p in yesterday_poles}
        
        for user_data in all_users:
            if user_data['current_streak'] > 0 and user_data['user_id'] not in user_ids_with_pole:
                member = guild.get_member(user_data['user_id'])
                if member:
                    users_lost_streak.append({
                        'member': member,
                        'streak': user_data['current_streak']
                    })
        
        # Crear embed de resumen
        embed = discord.Embed(
            title="🌃 Resumen del Día Anterior",
            description=f"**{len(yesterday_poles)}** jugadores hicieron pole ayer",
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
        
        # Advertencia para usuarios que perdieron racha
        if users_lost_streak:
            streak_warning = f"⚠️ **{len(users_lost_streak)} jugadores perdieron su racha:**\n\n"
            
            # Mostrar solo los primeros 5 para no saturar
            for user_info in users_lost_streak[:5]:
                streak_warning += f"💔 {user_info['member'].mention} (perdí {user_info['streak']} días)\n"
            
            if len(users_lost_streak) > 5:
                streak_warning += f"\n_...y {len(users_lost_streak) - 5} más_"
            
            embed.add_field(
                name=f"💔 Rachas Perdidas",
                value=streak_warning,
                inline=False
            )
        
        # Info del nuevo día
        embed.add_field(
            name="🌅 Nuevo Día",
            value="¡Un nuevo día comienza! Espera la notificación de apertura para hacer tu pole.",
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
