"""
Cog de Pole - Funcionalidad principal del bot
Maneja el sistema de pole diario con detección automática
"""
import discord
from discord.ext import commands
from discord import app_commands
from discord.ui import View, Select, Button, Modal, TextInput
from datetime import datetime, timedelta, timezone
import re
import asyncio
import logging
import unicodedata
from typing import Optional, Dict, Any

try:
    from zoneinfo import ZoneInfo
    LOCAL_TZ = ZoneInfo('Europe/Madrid')
except Exception:
    # Fallback: CET fijo (UTC+1) para sistemas sin zoneinfo
    LOCAL_TZ = timezone(timedelta(hours=1))

from utils.database import Database
from utils.scheduler import PoleScheduler
from utils.scoring import (
    evaluate_pole_attempt, get_pole_emoji,
    get_pole_name, get_rank_info, get_streak_multiplier,
    check_quota_available
)
from utils.i18n import (
    t,
    get_language_name,
    resolve_guild_language,
    set_cached_guild_language,
)

# Logger
log = logging.getLogger('PoleCog')

# Emoji de fuego personalizado (usar en todo el bot)
FIRE = "<a:fire:1440018375144374302>"
GRAY_FIRE = "<:gray_fire:1445324596751503485>"
PUTA_REGEX = re.compile(r'puta+', re.IGNORECASE)
PUTOMETRO_MEME_URL = "https://i.imgur.com/v2YghCs.jpeg"


def _ensure_local_tz(dt: datetime) -> datetime:
    """Normaliza datetime a Europe/Madrid; inyecta tz si viene naive."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=LOCAL_TZ)
    return dt.astimezone(LOCAL_TZ)


def _opening_time_for_day(base_dt: datetime, hour: int, minute: int, second: int) -> datetime:
    """Crea opening_time SIEMPRE timezone-aware en LOCAL_TZ."""
    return datetime(
        base_dt.year, base_dt.month, base_dt.day,
        hour, minute, second,
        tzinfo=LOCAL_TZ
    )

# ==================== HELPER PARA LOCALIZACIONES ====================

def _T(key_es: str, key_en: Optional[str] = None) -> app_commands.locale_str:
    """
    Helper para crear locale_str con traducciones español/inglés
    Discord usa el locale del CLIENTE, no del servidor
    
    Args:
        key_es: Key de traducción en español
        key_en: Key de traducción en inglés (opcional, usa misma key si no se pasa)
    """
    from utils.i18n import TRANSLATIONS
    
    if key_en is None:
        key_en = key_es
    
    # DEFAULT es INGLÉS (para todos los idiomas que no sean español)
    en_value = TRANSLATIONS['en'].get(key_en, key_en)
    es_value = TRANSLATIONS['es'].get(key_es, TRANSLATIONS['en'].get(key_en, key_en))
    
    # Si son listas, tomar el primer elemento (solo para comandos/opciones, no debería pasar)
    if isinstance(en_value, list):
        en_value = en_value[0]
    if isinstance(es_value, list):
        es_value = es_value[0]
    
    message = app_commands.locale_str(en_value)
    # Añadir traducción SOLO para español (España y Latinoamérica)
    message.extras[discord.Locale.spain_spanish.value] = es_value
    message.extras[discord.Locale.latin_american_spanish.value] = es_value
    
    return message

def _C(key_es: str, value: str, key_en: Optional[str] = None) -> app_commands.Choice[str]:
    """
    Helper para crear Choice con nombre en inglés (default)
    
    NOTA: Discord.py no soporta bien name_localizations en Choices.
    Usamos inglés siempre para los nombres de choices (simple y universal).
    
    Args:
        key_es: Key de traducción en español (no usado, por compatibilidad)
        value: Valor del choice
        key_en: Key de traducción en inglés (opcional)
    """
    from utils.i18n import TRANSLATIONS
    
    if key_en is None:
        key_en = key_es
    
    # Siempre en inglés para universalidad
    en_value = TRANSLATIONS['en'].get(key_en, key_en)
    if isinstance(en_value, list):
        en_value = en_value[0]  # Tomar primer elemento si es lista
    
    return app_commands.Choice(
        name=en_value,
        value=value
    )

# ==================== VIEWS PARA SETTINGS ====================

class ChannelSelectView(View):
    """Vista para seleccionar canal"""
    def __init__(self, db: Database, guild_id: int, original_interaction: discord.Interaction):
        super().__init__(timeout=60)
        self.db = db
        self.guild_id = guild_id
        self.original_interaction = original_interaction
        
    @discord.ui.select(cls=discord.ui.ChannelSelect, placeholder=t('ui.select_channel', None), channel_types=[discord.ChannelType.text])
    async def channel_select(self, interaction: discord.Interaction, select: discord.ui.ChannelSelect):
        channel = select.values[0]
        await self.db.init_server(self.guild_id, channel.id)
        await self.db.update_server_config(self.guild_id, pole_channel_id=channel.id)
        await interaction.response.send_message(
            t('settings.channel_set', self.guild_id, channel=channel.mention),
            ephemeral=True
        )
        self.stop()


class RoleSelectView(View):
    """Vista para seleccionar rol de ping"""
    def __init__(self, db: Database, guild_id: int):
        super().__init__(timeout=60)
        self.db = db
        self.guild_id = guild_id
        
    @discord.ui.select(cls=discord.ui.RoleSelect, placeholder=t('ui.select_role', None))
    async def role_select(self, interaction: discord.Interaction, select: discord.ui.RoleSelect):
        role = select.values[0]
        await self.db.update_server_config(self.guild_id, ping_role_id=role.id, ping_mode='role')
        await interaction.response.send_message(
            t('settings.role_set', self.guild_id, role=role.mention),
            ephemeral=True
        )
        self.stop()


class RepresentSelectView(View):
    """Vista para cambiar representación de servidor"""
    def __init__(self, db: Database, user_id: int, bot, mutual_guilds: list, current_guild_id: Optional[int], guild_id: int):
        super().__init__(timeout=60)
        self.db = db
        self.user_id = user_id
        self.bot = bot
        self.guild_id = guild_id  # Para traducciones
        
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
            placeholder=t('ui.select_server', self.guild_id),
            options=options
        )
        
        async def select_callback(interaction: discord.Interaction):
            new_guild_id = int(select.values[0])
            await self.db.set_represented_guild(self.user_id, new_guild_id)
            new_guild = self.bot.get_guild(new_guild_id)
            guild_name = new_guild.name if new_guild else f"ID {new_guild_id}"
            await interaction.response.send_message(
                t('settings.represent_set', self.guild_id, server=guild_name),
                ephemeral=True
            )
            self.stop()
        
        select.callback = select_callback
        self.add_item(select)


class LanguageSelectView(View):
    """Vista para cambiar idioma del servidor"""
    def __init__(self, db: Database, guild_id: int, current_lang: str = 'es'):
        super().__init__(timeout=60)
        self.db = db
        self.guild_id = guild_id
        
        # Crear botones para cada idioma
        spanish_button = Button(
            label=t('ui.language.button.es', guild_id),
            emoji="🇪🇸",
            style=discord.ButtonStyle.primary if current_lang == 'es' else discord.ButtonStyle.secondary
        )
        english_button = Button(
            label=t('ui.language.button.en', guild_id),
            emoji="🇬🇧",
            style=discord.ButtonStyle.primary if current_lang == 'en' else discord.ButtonStyle.secondary
        )
        
        async def spanish_callback(interaction: discord.Interaction):
            await self.db.set_server_language(self.guild_id, 'es')
            set_cached_guild_language(self.guild_id, 'es')
            await interaction.response.send_message(
                t('settings.language_set', guild_id, lang='es', language='Español'),
                ephemeral=True
            )
            self.stop()
        
        async def english_callback(interaction: discord.Interaction):
            await self.db.set_server_language(self.guild_id, 'en')
            set_cached_guild_language(self.guild_id, 'en')
            await interaction.response.send_message(
                t('settings.language_set', guild_id, lang='en', language='English'),
                ephemeral=True
            )
            self.stop()
        
        spanish_button.callback = spanish_callback
        english_button.callback = english_callback
        
        self.add_item(spanish_button)
        self.add_item(english_button)


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
                discord.SelectOption(
                    label=t('ui.option.channel.label', self.guild_id),
                    description=t('ui.option.channel.desc', self.guild_id),
                    emoji="📺", value="channel"),
                discord.SelectOption(
                    label=t('ui.option.language.label', self.guild_id),
                    description=t('ui.option.language.desc', self.guild_id),
                    emoji="🌐", value="language"),
                discord.SelectOption(
                    label=t('ui.option.ping_role.label', self.guild_id),
                    description=t('ui.option.ping_role.desc', self.guild_id),
                    emoji="🔔", value="ping_role"),
                discord.SelectOption(
                    label=t('ui.option.clear_ping.label', self.guild_id),
                    description=t('ui.option.clear_ping.desc', self.guild_id),
                    emoji="🚫", value="clear_ping"),
                discord.SelectOption(
                    label=t('ui.option.notify_open.label', self.guild_id),
                    description=t('ui.option.notify_open.desc', self.guild_id),
                    emoji="📢", value="notify_opening"),
                discord.SelectOption(
                    label=t('ui.option.notify_winner.label', self.guild_id),
                    description=t('ui.option.notify_winner.desc', self.guild_id),
                    emoji="🏆", value="notify_winner"),
            ])
        # Opción disponible para todos
        options.append(discord.SelectOption(
            label=t('ui.option.represent.label', self.guild_id),
            description=t('ui.option.represent.desc', self.guild_id),
            emoji="🏳️", value="represent"))
        
        select = discord.ui.Select(
            placeholder=t('ui.select_option', self.guild_id),
            options=options)
        
        async def on_select(interaction: discord.Interaction):
            value = select.values[0]
            # Acciones restringidas a admins
            admin_only = {"channel", "language", "ping_role", "clear_ping", "notify_opening", "notify_winner"}
            if value in admin_only and not self.is_admin:
                await interaction.response.send_message(
                    t('settings.admin_only', self.guild_id),
                    ephemeral=True
                )
                return
            
            if value == "channel":
                view = ChannelSelectView(self.db, self.guild_id, interaction)
                await interaction.response.send_message(t('ui.select_channel_prompt', self.guild_id), view=view, ephemeral=True)
            elif value == "language":
                current_lang = await self.db.get_server_language(self.guild_id)
                view = LanguageSelectView(self.db, self.guild_id, current_lang)
                lang_name = get_language_name(current_lang)
                embed = discord.Embed(title=t('ui.language.title', self.guild_id),
                    description=t('ui.language.desc', self.guild_id, current=lang_name),
                    color=discord.Color.blue()
                )
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            elif value == "ping_role":
                view = RoleSelectView(self.db, self.guild_id)
                await interaction.response.send_message(t('ui.select_role_prompt', self.guild_id), view=view, ephemeral=True)
            elif value == "clear_ping":
                await self.db.update_server_config(self.guild_id, ping_role_id=None, ping_mode='none')
                await interaction.response.send_message(
                    t('settings.ping_removed', self.guild_id),
                    ephemeral=True
                )
            elif value == "notify_opening":
                cfg = await self.db.get_server_config(self.guild_id) or {}
                new_val = 0 if cfg.get('notify_opening', 1) else 1
                await self.db.update_server_config(self.guild_id, notify_opening=new_val)
                msg_key = 'settings.opening_enabled' if new_val else 'settings.opening_disabled'
                await interaction.response.send_message(
                    t(msg_key, self.guild_id),
                    ephemeral=True
                )
            elif value == "notify_winner":
                cfg = await self.db.get_server_config(self.guild_id) or {}
                new_val = 0 if cfg.get('notify_winner', 1) else 1
                await self.db.update_server_config(self.guild_id, notify_winner=new_val)
                msg_key = 'settings.winner_enabled' if new_val else 'settings.winner_disabled'
                await interaction.response.send_message(
                    t(msg_key, self.guild_id),
                    ephemeral=True
                )
            elif value == "represent":
                # Obtener servidor actual representado
                current_guild_id = await self.db.get_represented_guild(interaction.user.id)
                
                # Obtener lista de servidores donde el usuario y el bot están presentes
                bot = interaction.client
                mutual_guilds = []
                for guild in bot.guilds:
                    member = guild.get_member(interaction.user.id)
                    if member:
                        mutual_guilds.append(guild)
                
                if not mutual_guilds:
                    await interaction.response.send_message(
                        t('errors.no_mutual_servers', self.guild_id),
                        ephemeral=True
                    )
                    return
                
                # Crear embed con info actual
                embed = discord.Embed(
                    title=t('ui.represent.title', self.guild_id),
                    description=t('ui.represent.desc', self.guild_id),
                    color=discord.Color.blue()
                )
                
                if current_guild_id:
                    current_guild = bot.get_guild(current_guild_id)
                    current_name = current_guild.name if current_guild else f"ID {current_guild_id}"
                    embed.add_field(
                        name=t('ui.represent.current', self.guild_id),
                        value=f"**{current_name}**",
                        inline=False
                    )
                else:
                    embed.add_field(
                        name=t('ui.represent.current', self.guild_id),
                        value=t('ui.represent.none', self.guild_id),
                        inline=False
                    )
                
                view = RepresentSelectView(self.db, interaction.user.id, bot, mutual_guilds, current_guild_id, self.guild_id)
                await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        
        select.callback = on_select
        self.add_item(select)
        
    async def create_embed(self, guild: discord.Guild) -> discord.Embed:
        """Crear embed con configuración actual"""
        cfg = await self.db.get_server_config(self.guild_id) or {}

        embed = discord.Embed(
            title=t('settings.title', self.guild_id),
            description=t('ui.settings.desc', self.guild_id),
            color=discord.Color.blurple()
        )

        # Canal de pole
        channel_id = cfg.get('pole_channel_id')
        channel_value = f"<#{channel_id}>" if channel_id else t('settings.not_configured', self.guild_id)
        embed.add_field(
            name=t('settings.field.channel', self.guild_id),
            value=channel_value,
            inline=False
        )

        # Idioma
        current_lang = await self.db.get_server_language(self.guild_id)
        lang_name = get_language_name(current_lang)
        lang_emoji = "🇪🇸" if current_lang == 'es' else "🇬🇧"
        embed.add_field(
            name=t('settings.field.language', self.guild_id),
            value=f"{lang_emoji} {lang_name}",
            inline=False
        )

        # Servidor representado (personal del usuario)
        represented_guild_id = await self.db.get_represented_guild(self.requester.id)
        if represented_guild_id:
            represented_guild = self.requester._state._get_guild(represented_guild_id)
            if represented_guild:
                represented_value = f"🏳️ **{represented_guild.name}**"
            else:
                represented_value = f"🏳️ *Servidor ID {represented_guild_id}*"
        else:
            represented_value = t('settings.not_configured', self.guild_id)
        embed.add_field(
            name=t('settings.field.represented_server', self.guild_id),
            value=represented_value,
            inline=False
        )
        
        # Rol de ping
        role_id = cfg.get('ping_role_id')
        role_value = f"<@&{role_id}>" if role_id else t('settings.not_configured', self.guild_id)
        embed.add_field(
            name=t('settings.field.ping_role', self.guild_id),
            value=role_value,
            inline=True
        )
        
        # Notificaciones
        notify_opening = t('common.enabled', self.guild_id) if cfg.get('notify_opening', 1) else t('common.disabled', self.guild_id)
        notify_winner = t('common.enabled', self.guild_id) if cfg.get('notify_winner', 1) else t('common.disabled', self.guild_id)
        embed.add_field(
            name=t('settings.field.notify_opening', self.guild_id),
            value=notify_opening,
            inline=True
        )
        embed.add_field(
            name=t('settings.field.notify_winner', self.guild_id),
            value=notify_winner,
            inline=True
        )
        
        embed.set_footer(text=t('settings.field.footer', self.guild_id))
        
        return embed
    
    @discord.ui.button(label=t('button.refresh', None), style=discord.ButtonStyle.secondary, emoji="🔄")
    async def refresh_button(self, interaction: discord.Interaction, button: Button):
        """Refrescar el embed con la configuración actual"""
        if interaction.guild:
            new_embed = await self.create_embed(interaction.guild)
            await interaction.response.edit_message(embed=new_embed, view=self)
        else:
            await interaction.response.send_message(
                t('settings.update_failed', self.guild_id),
                ephemeral=True
            )
    


class PoleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot._db  # Instancia compartida de Database (creada en main.py)
        self._pole_locks: Dict[str, asyncio.Lock] = {}  # Anti-race-condition: lock por usuario+guild+fecha
        self._putometro_milestones = (10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000, 25000, 50000, 100000, 250000, 500000, 1000000)
        self._putometro_boss_threshold = 5
        self._putometro_user_cooldown_seconds = 120
        self._putometro_guild_cooldown_seconds = 30
        self._putometro_user_cooldowns: Dict[tuple[int, int], datetime] = {}
        self._putometro_guild_cooldowns: Dict[int, datetime] = {}
        self._last_generation_date: Optional[str] = None  # Marca de rollover diario en hora local
        self._scheduler_started = False
        self._scheduler_start_task: Optional[asyncio.Task[Any]] = None
        self.scheduler = PoleScheduler(
            self.db,
            on_send_summary=self._send_summary,
            on_close_for_marranero=self._close_pole,
            on_open_pole=self._open_pole,
        )
        
        log.info("Pole Cog inicializado correctamente")

    async def _start_scheduler_safe(self) -> None:
        """Iniciar scheduler exactamente una vez, con trazas claras."""
        if self._scheduler_started:
            return

        await self.scheduler.start()
        self._last_generation_date = datetime.now(LOCAL_TZ).strftime('%Y-%m-%d')
        self._scheduler_started = True
        log.info("PoleScheduler iniciado correctamente")

    async def _start_scheduler_when_ready(self) -> None:
        """Esperar a READY antes de arrancar scheduler para evitar callbacks con caché incompleta."""
        try:
            await self.bot.wait_until_ready()
            await self._start_scheduler_safe()
        except asyncio.CancelledError:
            return
        except Exception:
            log.exception("❌ Error iniciando PoleScheduler post-ready")
    
    async def cog_load(self) -> None:
        """Arranque del Cog: iniciar scheduler cuando el bot esté listo."""
        if self.bot.is_ready():
            await self._start_scheduler_safe()
            return

        self._scheduler_start_task = asyncio.create_task(self._start_scheduler_when_ready())
        log.info("PoleScheduler diferido hasta que el bot esté READY")
    
    async def cog_unload(self) -> None:
        """Detener scheduler cuando se descarga el cog."""
        if self._scheduler_start_task and not self._scheduler_start_task.done():
            self._scheduler_start_task.cancel()
        self._scheduler_start_task = None

        if self._scheduler_started:
            await self.scheduler.shutdown(wait=False)
            self._scheduler_started = False

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Resolver idioma del servidor antes de ejecutar comandos slash del cog."""
        if interaction.guild is not None:
            await resolve_guild_language(interaction.guild.id, self.db)
        return True

    async def _resolve_text_channel(self, guild_id: int, channel_id: int) -> Optional[discord.TextChannel]:
        """Resolver canal de texto usando caché y fallback a fetch para robustez."""
        guild = self.bot.get_guild(guild_id)
        if guild is None:
            log.warning(f"⚠️ Guild {guild_id} no está en caché para resolver canal {channel_id}")
            return None

        channel = guild.get_channel(channel_id)
        if isinstance(channel, discord.TextChannel):
            return channel

        alt_channel = self.bot.get_channel(channel_id)
        if isinstance(alt_channel, discord.TextChannel):
            return alt_channel

        try:
            fetched = await self.bot.fetch_channel(channel_id)
            if isinstance(fetched, discord.TextChannel):
                return fetched
            log.warning(f"⚠️ Canal {channel_id} en guild {guild_id} no es TextChannel")
        except Exception as exc:
            log.warning(f"⚠️ No se pudo resolver canal {channel_id} en guild {guild_id}: {exc}")

        return None

    async def _send_summary(self, guild_id: int, summary_date: str) -> None:
        """Hook del scheduler: enviar resumen diario del guild."""
        log.info(f"🌃 Callback summary guild={guild_id} date={summary_date}")
        server_config = await self.db.get_server_config(guild_id)
        if not server_config:
            log.warning(f"⚠️ Callback summary: sin configuración para guild {guild_id}")
            return

        lang = await resolve_guild_language(guild_id, self.db)
        set_cached_guild_language(guild_id, lang)

        channel_id = server_config.get('pole_channel_id')
        if not channel_id:
            log.warning(f"⚠️ Callback summary: guild {guild_id} sin pole_channel_id")
            return

        await self.send_midnight_summary(guild_id, int(channel_id), summary_date)

    async def _close_pole(self, guild_id: int, dt: datetime) -> None:
        """Hook del scheduler: transición a ventana marranero en medianoche."""
        dt_local = _ensure_local_tz(dt)
        self._last_generation_date = dt_local.strftime('%Y-%m-%d')

        # Limpiar locks antiguos (de días pasados) para evitar memory leak.
        today_str = dt_local.strftime('%Y-%m-%d')
        old_locks = [key for key in self._pole_locks.keys() if not key.endswith(today_str)]
        for key in old_locks:
            del self._pole_locks[key]

        if old_locks:
            log.info(f"🧹 Limpiados {len(old_locks)} locks antiguos")

        log.info(f"🌙 Guild {guild_id}: pole cerrada, fase marranero activa")

    async def _open_pole(self, guild_id: int, dt: datetime) -> None:
        """Hook del scheduler: apertura real de la pole del día."""
        log.info(f"🌅 Callback open guild={guild_id} dt={dt.isoformat()}")
        server_config = await self.db.get_server_config(guild_id)
        if not server_config:
            log.warning(f"⚠️ Callback open: sin configuración para guild {guild_id}")
            return

        lang = await resolve_guild_language(guild_id, self.db)
        set_cached_guild_language(guild_id, lang)

        channel_id = server_config.get('pole_channel_id')
        if not channel_id:
            log.warning(f"⚠️ Callback open: guild {guild_id} sin pole_channel_id")
            return

        if int(server_config.get('notify_opening', 1)) == 0:
            log.info(f"🔕 Guild {guild_id}: apertura en {dt.isoformat()} sin notificación (desactivada)")
            return

        await self.send_opening_notification(
            guild_id=guild_id,
            channel_id=int(channel_id),
            ping_role_id=server_config.get('ping_role_id'),
            ping_mode=str(server_config.get('ping_mode', 'none')),
            opening_dt=dt,
        )

    # ==================== SISTEMA DE ROBUSTEZ/FAILSAFE ====================
    

    # ==================== HELPERS ====================

    async def _get_or_create_user_data(self, guild_id: int, member: discord.abc.User) -> dict:
        """Obtiene los datos del usuario, creándolo si no existe."""
        user = await self.db.get_user(member.id, guild_id)
        if not user:
            await self.db.create_user(member.id, guild_id, member.name)
            user = await self.db.get_user(member.id, guild_id)
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
        
        server_config = await self.db.get_server_config(guild.id)
        daily_time = server_config.get('daily_pole_time') if server_config else None
        pole_channel_id = server_config.get('pole_channel_id') if server_config else None

        now = datetime.now(LOCAL_TZ)
        
        # Si no hay configuración, ignorar silenciosamente
        if not pole_channel_id or not daily_time:
            return
        
        # Parsear hora de apertura
        try:
            h, m, s = [int(x) for x in str(daily_time).split(':')]
            opening_time = _opening_time_for_day(now, h, m, s)
        except:
            return
        
        # Ver si ya abrió o no
        if now < opening_time:
            # Aún no abre - NO decimos la hora, solo vacilamos
            responses = [
                t('pole.impatient.1', guild.id),
                t('pole.impatient.2', guild.id),
                t('pole.impatient.3', guild.id),
                t('pole.impatient.4', guild.id),
                t('pole.impatient.5', guild.id),
                t('pole.impatient.6', guild.id),
                t('pole.impatient.7', guild.id),
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

    @staticmethod
    def _sanitize_for_putometro(content: str) -> str:
        """Sanitizar contenido para detección robusta anti-evasión del putómetro."""
        text = (content or "").lower()
        replacements = str.maketrans({
            'а': 'a',
            'о': 'o',
            'е': 'e',
            'р': 'p',
            'с': 'c',
            'у': 'y',
            'т': 't',
            '@': 'a',
            '0': 'o',
            '4': 'a',
            '7': 't',
        })
        text = text.translate(replacements)
        text = unicodedata.normalize('NFKD', text)
        text = ''.join(ch for ch in text if not unicodedata.combining(ch))
        return re.sub(r'[^a-z]', '', text)

    @staticmethod
    def _count_puta_occurrences(content: str) -> int:
        """Contar ocurrencias de 'puta' (incluye variantes tipo putaaa)."""
        sanitized = PoleCog._sanitize_for_putometro(content)
        return len(PUTA_REGEX.findall(sanitized))

    @staticmethod
    def _find_crossed_milestone(prev_total: int, new_total: int, milestones: tuple[int, ...]) -> Optional[int]:
        """Detectar el mayor milestone cruzado entre prev_total y new_total."""
        crossed = [m for m in milestones if prev_total < m <= new_total]
        return max(crossed) if crossed else None

    def _prune_putometro_cooldowns(self, now: datetime) -> None:
        """Limpiar cooldowns expirados para evitar crecimiento indefinido en memoria."""
        expired_users = [k for k, v in self._putometro_user_cooldowns.items() if v <= now]
        for key in expired_users:
            del self._putometro_user_cooldowns[key]

        expired_guilds = [gid for gid, v in self._putometro_guild_cooldowns.items() if v <= now]
        for gid in expired_guilds:
            del self._putometro_guild_cooldowns[gid]

    def _can_emit_putometro_boss(self, guild_id: int, user_id: int, now: datetime) -> bool:
        """Controlar cooldown de boss mode por usuario+guild y por guild."""
        self._prune_putometro_cooldowns(now)

        user_key = (guild_id, user_id)
        user_until = self._putometro_user_cooldowns.get(user_key)
        guild_until = self._putometro_guild_cooldowns.get(guild_id)

        if user_until is not None and user_until > now:
            return False
        if guild_until is not None and guild_until > now:
            return False

        self._putometro_user_cooldowns[user_key] = now + timedelta(seconds=self._putometro_user_cooldown_seconds)
        self._putometro_guild_cooldowns[guild_id] = now + timedelta(seconds=self._putometro_guild_cooldown_seconds)
        return True

    @staticmethod
    def _putometro_color(occurrences: int) -> discord.Color:
        """Color del embed según intensidad del mensaje."""
        if occurrences >= 6:
            return discord.Color.from_rgb(220, 20, 60)
        if occurrences >= 3:
            return discord.Color.orange()
        return discord.Color.blurple()

    @staticmethod
    def _putometro_mode_key(occurrences: int, user_total: int) -> str:
        """Seleccionar modo textual del putómetro para el embed."""
        if occurrences >= 6:
            return 'putometro.trigger.mode.nuclear'
        if occurrences >= 3:
            return 'putometro.trigger.mode.chaos'
        if user_total >= 100:
            return 'putometro.trigger.mode.veteran'
        return 'putometro.trigger.mode.warmup'

    async def _handle_putometro_message(self, message: discord.Message) -> None:
        """Procesar easter egg de putómetro sin tocar el flujo de poles."""
        guild = message.guild
        if guild is None:
            return

        occurrences = self._count_puta_occurrences(message.content)
        if occurrences <= 0:
            return

        try:
            lang = await resolve_guild_language(guild.id, self.db)
            set_cached_guild_language(guild.id, lang)

            now_local = datetime.now(LOCAL_TZ)
            user_total, guild_total = await self.db.increment_puta_counter(
                guild_id=guild.id,
                user_id=message.author.id,
                amount=occurrences,
            )
            prev_total = max(0, int(user_total) - int(occurrences))
            crossed_milestone = self._find_crossed_milestone(prev_total, int(user_total), self._putometro_milestones)

            boss_enabled = False
            flash_context: Optional[Dict[str, Any]] = None
            if occurrences >= self._putometro_boss_threshold:
                boss_enabled = self._can_emit_putometro_boss(guild.id, message.author.id, now_local)
                if boss_enabled:
                    flash_context = await self.db.get_puta_boss_flash_context(
                        guild_id=guild.id,
                        user_id=message.author.id,
                        top_limit=3,
                    )

            mode_key = self._putometro_mode_key(occurrences, int(user_total))
            if boss_enabled:
                mode_key = 'putometro.trigger.mode.boss'

            embed = discord.Embed(
                title=t('putometro.trigger.title', guild.id),
                description=t(
                    'putometro.trigger.desc',
                    guild.id,
                    mention=message.author.mention,
                    message_count=occurrences,
                ),
                color=self._putometro_color(occurrences),
                timestamp=now_local
            )
            embed.set_thumbnail(url=message.author.display_avatar.url)
            embed.set_image(url=f"{PUTOMETRO_MEME_URL}?v={int(now_local.timestamp())}")

            embed.add_field(
                name=t('putometro.trigger.field.message', guild.id),
                value=t('putometro.trigger.value.message_count', guild.id, message_count=occurrences),
                inline=True
            )
            embed.add_field(
                name=t('putometro.trigger.field.user_total', guild.id),
                value=t('putometro.trigger.value.user_total', guild.id, user_count=user_total),
                inline=True
            )
            embed.add_field(
                name=t('putometro.trigger.field.guild_total', guild.id),
                value=t('putometro.trigger.value.guild_total', guild.id, guild_total=guild_total),
                inline=True
            )
            embed.add_field(
                name=t('putometro.trigger.field.mode', guild.id),
                value=t(mode_key, guild.id),
                inline=False
            )

            if crossed_milestone is not None:
                embed.add_field(
                    name=t('putometro.trigger.field.milestone', guild.id),
                    value=t(
                        'putometro.trigger.milestone.value',
                        guild.id,
                        milestone=int(crossed_milestone),
                        user_count=int(user_total),
                    ),
                    inline=False
                )

            if boss_enabled and flash_context:
                top_rows = flash_context.get('top', [])
                top_text = "\n".join(
                    t(
                        'putometro.trigger.ranking.top_entry',
                        guild.id,
                        position=idx,
                        mention=f"<@{int(row['user_id'])}>",
                        count=int(row['total_count']),
                    )
                    for idx, row in enumerate(top_rows, start=1)
                )
                if not top_text:
                    top_text = t('common.none', guild.id)

                embed.add_field(
                    name=t('putometro.trigger.field.ranking_flash', guild.id),
                    value=t(
                        'putometro.trigger.ranking.you',
                        guild.id,
                        rank=int(flash_context.get('user_rank', 0)),
                        total_users=int(flash_context.get('total_users', 0)),
                        user_total=int(flash_context.get('user_total', 0)),
                        top=top_text,
                    ),
                    inline=False
                )

            if boss_enabled and crossed_milestone is not None:
                footer_key = 'putometro.trigger.footer.boss_milestone'
            elif boss_enabled:
                footer_key = 'putometro.trigger.footer.boss'
            elif crossed_milestone is not None:
                footer_key = 'putometro.trigger.footer.milestone'
            else:
                footer_key = 'putometro.trigger.footer'

            embed.set_footer(
                text=t(
                    footer_key,
                    guild.id,
                    milestone=int(crossed_milestone or 0),
                )
            )

            await message.reply(embed=embed, mention_author=False)
        except Exception as exc:
            log.warning(f"⚠️ Putómetro: no se pudo procesar mensaje en guild {guild.id}: {exc}")
    
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
                await self._handle_putometro_message(message)
                return
        except Exception as e:
            log.error(f"❌ Error en verificaciones iniciales de on_message: {e}")
            import traceback
            traceback.print_exc()
            return
        
        # Obtener configuración del servidor (sin autoasignar canal)
        server_config = await self.db.get_server_config(guild.id)
        if not server_config:
            # Inicializa entrada del servidor sin canal aún (placeholder 0)
            await self.db.init_server(guild.id, 0)
            server_config = await self.db.get_server_config(guild.id)
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
                    'language': 'es',
                    'migration_in_progress': 0,
                }

        # Mantener cache de idioma en caliente para respuestas de texto (on_message).
        set_cached_guild_language(guild.id, str(server_config.get('language') or 'es'))
        
        # Verificar si hay migración en progreso
        if server_config.get('migration_in_progress', 0):
            try:
                await message.reply(
                    t('migration.in_progress', guild.id)
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
                    await message.reply(t('errors.configure_channel', message.guild.id if message.guild else None))
                except:
                    pass
            return
        if message.channel.id != pole_channel_id:
            return
        
        # ANTI-RACE-CONDITION: Lock por usuario+guild+fecha para evitar poles duplicados
        # Si el usuario escribe "pole" dos veces rápido, el segundo espera al primero
        now = datetime.now(LOCAL_TZ)
        lock_key = f"{message.author.id}_{message.guild.id}_{now.strftime('%Y-%m-%d')}"
        
        # Crear lock si no existe
        if lock_key not in self._pole_locks:
            self._pole_locks[lock_key] = asyncio.Lock()
        
        # Procesar con lock (solo uno a la vez por usuario+guild+fecha)
        async with self._pole_locks[lock_key]:
            await self.process_pole(message)
    
    async def process_pole(self, message: discord.Message):
        """
        Procesar un pole válido usando fase actual del scheduler + evaluación centralizada.

        Flujo:
        1) Leer fase actual (cerrada/abierta) y hora de apertura desde BD.
        2) Evaluar intento con evaluate_pole_attempt(...).
        3) Aplicar validación global por effective_pole_date.
        4) Persistir de forma atómica y actualizar estadísticas.
        """
        now = datetime.now(LOCAL_TZ)
        guild = message.guild
        if guild is None:
            return

        server_config = await self.db.get_server_config(guild.id) or {}
        set_cached_guild_language(guild.id, str(server_config.get('language') or 'es'))
        daily_time = await self.db.get_daily_pole_time(guild.id)
        
        # ========== PASO 1: Verificar configuración ==========
        if not daily_time:
            try:
                await message.reply(t('errors.no_time_configured', guild.id))
            except:
                pass
            return

        # Parsear hora de apertura de hoy
        try:
            h, m, s = [int(x) for x in str(daily_time).split(':')]
        except Exception:
            try:
                await message.reply(t('errors.invalid_time_config', guild.id))
            except:
                pass
            return
        
        phase = self.scheduler.get_phase(guild.id)
        phase_value = str(getattr(phase, 'value', phase))

        # Hora de referencia por defecto: apertura de hoy (hora programada).
        opening_time = _opening_time_for_day(now, h, m, s)

        # Si estamos en fase abierta, priorizar hora real de notificación (delay más justo).
        notification_sent_str = await self.db.get_notification_sent_at(guild.id)
        if phase_value == 'ABIERTA_JUGANDO' and notification_sent_str:
            try:
                notif_dt = _ensure_local_tz(datetime.fromisoformat(notification_sent_str))
                if notif_dt.date() == now.date():
                    opening_time = notif_dt
            except Exception:
                pass

        # Si estamos en fase cerrada, el marranero se evalúa contra la apertura de AYER.
        if phase_value == 'CERRADA_ESPERANDO_APERTURA':
            last_opening_str = await self.db.get_last_daily_pole_time(guild.id)
            if last_opening_str:
                try:
                    parts = str(last_opening_str).split(':')
                    last_h = int(parts[0])
                    last_m = int(parts[1])
                    last_s = int(parts[2]) if len(parts) > 2 else 0
                    yesterday = now - timedelta(days=1)
                    opening_time = _opening_time_for_day(yesterday, last_h, last_m, last_s)
                except Exception as exc:
                    log.warning(f"⚠️ Error parseando last_daily_pole_time en guild {guild.id}: {exc}")

        # Seguridad defensiva: si por drift de estado aparece abierta antes de tiempo, se rechaza.
        if phase_value == 'ABIERTA_JUGANDO' and now < opening_time:
            await self.db.increment_impatient_attempts(message.author.id, guild.id)
            try:
                await message.add_reaction('⏳')
            except:
                pass
            try:
                await message.reply(t('pole.not_yet', guild.id))
            except:
                pass
            return

        try:
            evaluation = evaluate_pole_attempt(
                user_time=now,
                opening_time=opening_time,
                phase=phase,
            )
        except ValueError as exc:
            log.error(f"❌ Error evaluando pole en guild {guild.id}: {exc}")
            try:
                await message.reply(t('error.generic', guild.id))
            except:
                pass
            return

        pole_type = evaluation['pole_type']
        delay_minutes = max(0, int(evaluation['delay_minutes']))
        effective_date = str(evaluation['effective_pole_date'])

        # Verificación global por fecha efectiva (marranero = ayer, normal = hoy).
        global_pole = await self.db.get_user_pole_on_date_global(message.author.id, effective_date)
        if global_pole:
            await self.db.increment_impatient_attempts(message.author.id, guild.id)
            existing_gid = int(global_pole.get('guild_id', 0))

            if existing_gid and existing_gid != guild.id:
                prev_guild = self.bot.get_guild(existing_gid)
                prev_name = prev_guild.name if prev_guild else f"ID {existing_gid}"
                try:
                    await message.add_reaction('🚫')
                except:
                    pass
                try:
                    await message.reply(
                        t('pole.already_done_other_server', guild.id, server_name=prev_name)
                    )
                except:
                    pass
            else:
                try:
                    await message.add_reaction('🛑')
                except:
                    pass
                try:
                    embed = discord.Embed(
                        description=t('pole.already_done_today', guild.id),
                        color=discord.Color.orange()
                    )
                    embed.set_image(url="https://i.imgflip.com/37dceb.jpg")
                    await message.reply(embed=embed)
                except:
                    pass
            return

        # Posición y conteos por fecha efectiva (no forzar "hoy").
        async with self.db.get_connection() as conn:
            cursor = await conn.execute('''
                SELECT pole_type FROM poles
                WHERE guild_id = ? AND pole_date = ?
                ORDER BY user_time ASC
            ''', (guild.id, effective_date))
            day_rows = await cursor.fetchall()

        day_pole_types = [str(row[0]) for row in day_rows]
        position = len(day_pole_types) + 1
        
        # ====== VERIFICAR CUOTAS (solo para critical y fast) ======
        # La degradación es SILENCIOSA: si critical está lleno, baja a fast; si fast lleno, a normal.
        # IMPORTANTE: Los poles degradados NO consumen cuota de la categoría inferior.
        # Solo se cuentan poles ORIGINALMENTE clasificados en esa categoría.
        if pole_type in ['critical', 'fast']:
            # Contar JUGADORES ACTIVOS del servidor (usuarios que han hecho pole alguna vez)
            # NO contar total de miembros para evitar meta roto (ej: 80 miembros, 10 juegan)
            active_players = await self.db.get_total_active_users(guild.id)
            
            # Verificar cuota de critical
            if pole_type == 'critical':
                poles_of_type = sum(1 for p in day_pole_types if p == 'critical')
                has_quota, current, max_allowed = check_quota_available('critical', poles_of_type, active_players)
                
                if not has_quota:
                    # Degradar a fast (sin mensaje - la notificación del pole mostrará el tipo real)
                    pole_type = 'fast'
            
            # Verificar cuota de fast (ya sea original o degradado desde critical)
            if pole_type == 'fast':
                # Solo contar poles ORIGINALMENTE fast (no degradados) para cuota justa
                poles_of_type = sum(1 for p in day_pole_types if p == 'fast')
                has_quota, current, max_allowed = check_quota_available('fast', poles_of_type, active_players)
                
                if not has_quota:
                    # Degradar a normal (sin límite de cuota)
                    pole_type = 'normal'
        
        # Obtener o crear usuario LOCAL (stats por servidor)
        user = await self._get_or_create_user_data(guild.id, message.author)

        # Guardar pole + actualizar racha global en una transacción atómica.
        pole_result = await self.db.record_pole_and_update_streak_atomic(
            user_id=message.author.id,
            guild_id=guild.id,
            username=message.author.name,
            opening_time=opening_time,
            user_time=now,
            delay_minutes=delay_minutes,
            pole_type=pole_type,
            effective_date=effective_date,
            pole_date=effective_date
        )

        # Failsafe anti-carrera: si otro servidor ganó la condición de escritura,
        # no duplicamos pole ni racha para la misma fecha efectiva.
        if not pole_result.get('accepted'):
            await self.db.increment_impatient_attempts(message.author.id, guild.id)
            existing_gid = pole_result.get('existing_guild_id')

            if existing_gid and int(existing_gid) != guild.id:
                prev_guild = self.bot.get_guild(int(existing_gid))
                prev_name = prev_guild.name if prev_guild else f"ID {existing_gid}"
                try:
                    await message.add_reaction('🚫')
                except:
                    pass
                try:
                    await message.reply(
                        t('pole.already_done_other_server', guild.id, server_name=prev_name)
                    )
                except:
                    pass
            else:
                try:
                    await message.add_reaction('🛑')
                except:
                    pass
                try:
                    embed = discord.Embed(
                        description=t('pole.already_done_today', guild.id),
                        color=discord.Color.orange()
                    )
                    embed.set_image(url="https://i.imgflip.com/37dceb.jpg")
                    await message.reply(embed=embed)
                except:
                    pass
            return

        # Asignar representación automáticamente solo cuando el pole se registró.
        represented = await self.db.get_represented_guild(message.author.id)
        if represented is None:
            await self.db.set_represented_guild(message.author.id, guild.id)

        new_streak = int(pole_result['new_streak'])
        streak_broken = bool(pole_result['streak_broken'])
        points_base = float(pole_result['points_base'])
        streak_multiplier = float(pole_result['streak_multiplier'])
        points_earned = float(pole_result['points_earned'])
        
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
        elif pole_type == 'late':
            update_data['late_poles'] = int(user.get('late_poles', 0)) + 1
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
        
        await self.db.update_user(message.author.id, guild.id, **update_data)

        # ====== ACTUALIZAR STATS DE TEMPORADA ======
        from utils.scoring import get_current_season
        current_season = get_current_season()

        # Obtener stats actuales de la temporada
        season_stats = await self.db.get_season_stats(message.author.id, guild.id, current_season)
        
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
            elif pole_type in ('normal', 'late'):
                season_update['season_normal'] = season_stats['season_normal'] + 1
            elif pole_type == 'marranero':
                season_update['season_marranero'] = season_stats['season_marranero'] + 1
            
            await self.db.update_season_stats(
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
                'season_normal': 1 if pole_type in ('normal', 'late') else 0,
                'season_marranero': 1 if pole_type == 'marranero' else 0,
                'season_best_streak': new_streak
            }

            await self.db.update_season_stats(
                message.author.id, guild.id, current_season,
                **season_data
            )

        # ====== ACTUALIZAR FIRST_POLE_DATE DEL SERVIDOR SI ES EL PRIMERO ======
        server_config = await self.db.get_server_config(guild.id)
        if server_config and not server_config.get('first_pole_date'):
            # Es el primer pole del servidor, guardarlo
            await self.db.update_server_config(guild.id, first_pole_date=effective_date)
            log.info(f"🎉 Primer pole registrado en {guild.name} (fecha: {effective_date})")
        
        # Enviar notificación de victoria
        try:
            await self.send_pole_notification(
                message, pole_type, position, points_base,
                streak_multiplier, points_earned, new_streak,
                streak_broken, now, delay_minutes, guild.id
            )
        except Exception as e:
            log.error(f"❌ Error enviando notificación de pole: {e}")
            # Intentar enviar mensaje simple como fallback
            try:
                await message.reply(
                    t('pole.success_short', guild.id, 
                      points=f"{points_earned:.1f}", streak=new_streak)
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

    @staticmethod
    def _format_delay_for_notification(minutes: int) -> str:
        h = minutes // 60
        m = minutes % 60
        if h > 0:
            return f"{h}h {m} min" if m > 0 else f"{h}h"
        return f"{m} min"

    def _build_pole_notification_embed(
        self,
        guild: Optional[discord.Guild],
        author: discord.abc.User,
        pole_type: str,
        position: int,
        points_base: float,
        multiplier: float,
        points_earned: float,
        streak: int,
        streak_broken: bool,
        timestamp: datetime,
        delay_minutes: int,
        guild_id: int,
    ) -> discord.Embed:
        """Construir embed de pole ganado para uso normal y preview debug."""
        emoji = get_pole_emoji(pole_type)
        name = get_pole_name(pole_type, guild_id)
        delay_formatted = self._format_delay_for_notification(delay_minutes)
        time_str = timestamp.strftime('%H:%M:%S')
        points_label = t('common.pts', guild_id)

        embed = discord.Embed(
            title=f"{emoji} {name} {emoji}",
            color=self.get_pole_color(pole_type),
            timestamp=timestamp
        )
        embed.set_author(
            name=t('pole.notification.author', guild_id, user=author.display_name),
            icon_url=author.display_avatar.url
        )
        if guild and guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        descriptions = {
            'critical': t('pole.notification.description_critical', guild_id, mention=author.mention, delay=delay_formatted),
            'fast': t('pole.notification.description_fast', guild_id, mention=author.mention, delay=delay_formatted),
            'normal': t('pole.notification.description_normal', guild_id, mention=author.mention, delay=delay_formatted),
            'late': t('pole.notification.description_late', guild_id, mention=author.mention, delay=delay_formatted),
            'marranero': t('pole.notification.description_marranero', guild_id, mention=author.mention, delay=delay_formatted)
        }
        description = descriptions.get(pole_type, f"{author.mention}")
        embed.description = description

        embed.add_field(
            name=t('pole.field.total_earned', guild_id),
            value=f"```+{points_earned:.1f} {points_label}```",
            inline=False
        )

        streak_emoji = FIRE if streak > 1 else GRAY_FIRE
        if streak > 1:
            streak_value = t(
                'pole.field.streak_hot_value',
                guild_id,
                emoji=streak_emoji,
                days=streak,
                multiplier=f"{multiplier:.1f}"
            )
        else:
            streak_value = t(
                'pole.field.streak_cold_value',
                guild_id,
                emoji=streak_emoji,
                days=streak,
                multiplier=f"{multiplier:.1f}"
            )

        embed.add_field(name=t('pole.field.position', guild_id), value=f"#{position}", inline=True)
        embed.add_field(name=t('pole.field.delay', guild_id), value=delay_formatted, inline=True)
        embed.add_field(name=t('pole.field.time', guild_id), value=time_str, inline=True)

        embed.add_field(
            name=t('pole.field.base_points', guild_id),
            value=f"{points_base:.1f} {points_label}",
            inline=True
        )
        embed.add_field(
            name=t('pole.field.streak_status', guild_id),
            value=streak_value,
            inline=True
        )

        embed.add_field(
            name=t('pole.field.streak', guild_id, emoji=streak_emoji),
            value=t('pole.field.streak_days', guild_id, days=streak),
            inline=True
        )

        footer_messages = {
            'critical': t('pole.footer.critical', guild_id),
            'fast': t('pole.footer.fast', guild_id),
            'normal': t('pole.footer.normal', guild_id),
            'late': t('pole.footer.late', guild_id),
            'marranero': t('pole.footer.marranero', guild_id)
        }
        embed.set_footer(text=footer_messages.get(pole_type, ""))

        if streak_broken:
            embed.add_field(
                name=t('pole.field.broken_streak_title', guild_id),
                value=t('pole.field.broken_streak_desc', guild_id),
                inline=False
            )

        return embed
    
    async def send_pole_notification(self, message: discord.Message,
                                     pole_type: str, position: int,
                                     points_base: float, multiplier: float,
                                     points_earned: float, streak: int,
                                     streak_broken: bool, timestamp: datetime,
                                     delay_minutes: int, guild_id: int):
        """
        Enviar notificación de victoria con personalidad
        """
        embed = self._build_pole_notification_embed(
            guild=message.guild,
            author=message.author,
            pole_type=pole_type,
            position=position,
            points_base=points_base,
            multiplier=multiplier,
            points_earned=points_earned,
            streak=streak,
            streak_broken=streak_broken,
            timestamp=timestamp,
            delay_minutes=delay_minutes,
            guild_id=guild_id,
        )
        await message.channel.send(embed=embed)

    async def send_pole_notification_preview(
        self,
        guild: discord.Guild,
        channel: discord.TextChannel,
        member: discord.Member,
        pole_type: str,
        position: int,
        points_base: float,
        multiplier: float,
        points_earned: float,
        streak: int,
        streak_broken: bool,
        timestamp: datetime,
        delay_minutes: int,
    ) -> None:
        """Enviar preview de notificación de pole sin tocar estado de base de datos."""
        embed = self._build_pole_notification_embed(
            guild=guild,
            author=member,
            pole_type=pole_type,
            position=position,
            points_base=points_base,
            multiplier=multiplier,
            points_earned=points_earned,
            streak=streak,
            streak_broken=streak_broken,
            timestamp=timestamp,
            delay_minutes=delay_minutes,
            guild_id=guild.id,
        )
        await channel.send(embed=embed)
    
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

    @app_commands.command(name="settings", description=_T('cmd.settings.desc'))
    async def settings(self, interaction: discord.Interaction):
        """Comando único para configurar el bot con una interfaz interactiva"""
        if interaction.guild is None:
            await interaction.response.send_message(t('errors.server_only_short', None), ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)

        await resolve_guild_language(interaction.guild.id, self.db)
        
        member = interaction.user if isinstance(interaction.user, discord.Member) else interaction.guild.get_member(interaction.user.id)
        if member is None:
            await interaction.followup.send(t('errors.no_permissions_check', interaction.guild.id), ephemeral=True)
            return
        view = SettingsView(self.db, interaction.guild.id, member)
        embed = await view.create_embed(interaction.guild)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="profile", description=_T('cmd.profile.desc'))
    @app_commands.describe(
        usuario=_T('cmd.profile.user_param'),
        alcance=_T('cmd.profile.scope_param')
    )
    @app_commands.choices(alcance=[
        app_commands.Choice(name="Global (all servers)", value="global"),
        app_commands.Choice(name="Local (this server)", value="local")
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
            global_stats = await self.db.get_user_global_stats(target_user.id)
            global_user = await self.db.get_global_user(target_user.id)
            
            if not global_stats or global_stats['total_poles'] == 0:
                await interaction.followup.send(
                    t('profile.no_data_global', interaction.guild.id if interaction.guild else None, 
                      mention=target_user.mention),
                    ephemeral=True
                )
                return
            
            # Obtener mejor temporada para rango histórico (todos los servidores)
            current_season_id = get_current_season()
            async with self.db.get_connection() as conn:
                # Mejor temporada (sumando todos los servidores)
                cursor = await conn.execute('''
                    SELECT season_id, SUM(season_points) as total_points
                    FROM season_stats
                    WHERE user_id = ?
                    GROUP BY season_id
                    ORDER BY total_points DESC
                    LIMIT 1
                ''', (target_user.id,))
                best_season = await cursor.fetchone()
                best_season_points = best_season['total_points'] if best_season else 0.0

                # Temporada actual (sumando todos los servidores)
                cursor = await conn.execute('''
                    SELECT SUM(season_points) as total_points, SUM(season_poles) as total_poles
                    FROM season_stats
                    WHERE user_id = ? AND season_id = ?
                ''', (target_user.id, current_season_id))
                current_season = await cursor.fetchone()
                current_season_points = current_season['total_points'] if current_season and current_season['total_points'] else 0.0
                current_season_poles = current_season['total_poles'] if current_season and current_season['total_poles'] else 0
            
            rank_emoji, rank_name = get_rank_info(best_season_points, interaction.guild.id if interaction.guild else None)
            
            # Crear embed
            embed = discord.Embed(
                title=t('profile.title_global', interaction.guild.id if interaction.guild else None,
                        display_name=target_user.display_name),
                description=t('profile.desc_global', interaction.guild.id if interaction.guild else None),
                color=discord.Color.gold(),
                timestamp=datetime.now(LOCAL_TZ)
            )
            embed.set_thumbnail(url=target_user.display_avatar.url)

            gid_ctx = interaction.guild.id if interaction.guild else None

            # Fila 1: temporada actual + rango histórico
            if current_season_poles > 0:
                season_rank_emoji, season_rank_name = get_rank_info(current_season_points, gid_ctx)
                season_value = t(
                    'profile.field.season_rank_value',
                    gid_ctx,
                    emoji=season_rank_emoji,
                    name=season_rank_name,
                    points=f"{current_season_points:.1f}"
                )
            else:
                season_value = t('common.none', gid_ctx)

            embed.add_field(
                name=t('profile.field.season_current', gid_ctx),
                value=season_value,
                inline=True
            )
            
            # Rango Histórico (basado en mejor temporada)
            embed.add_field(
                name=t('profile.field.rank_historical', gid_ctx),
                value=t('profile.field.rank_value', gid_ctx,
                        emoji=rank_emoji, name=rank_name, best_points=f"{best_season_points:.1f}"),
                inline=True
            )
            embed.add_field(name="\u200b", value="\u200b", inline=True)
            
            # Grid 2x2 de métricas
            embed.add_field(
                name=t('profile.field.total_points', gid_ctx),
                value=f"**{global_stats['total_points']:.1f}** {t('common.pts', gid_ctx)}",
                inline=True
            )
            embed.add_field(
                name=t('profile.field.total_poles', gid_ctx),
                value=f"**{global_stats['total_poles']}**",
                inline=True
            )
            embed.add_field(name="\u200b", value="\u200b", inline=True)
            
            # Racha actual (GLOBAL entre servidores)
            current_streak = global_user['current_streak'] if global_user else 0
            streak_emoji = FIRE if current_streak > 0 else GRAY_FIRE
            embed.add_field(
                name=t('profile.field.current_streak', gid_ctx, 
                       emoji=streak_emoji),
                value=t('profile.field.streak_days', gid_ctx, 
                        days=current_streak),
                inline=True
            )
            
            # Mejor racha (GLOBAL entre servidores)
            best_streak = global_user['best_streak'] if global_user else 0
            best_streak_emoji = FIRE if best_streak > 0 else GRAY_FIRE
            embed.add_field(
                name=t('profile.field.best_streak', gid_ctx, 
                       emoji=best_streak_emoji),
                value=t('profile.field.streak_days', gid_ctx, 
                        days=best_streak),
                inline=True
            )
            embed.add_field(name="\u200b", value="\u200b", inline=True)
            
            # Desglose por tipo compacto (centrado visualmente)
            breakdown = (
                f"💎 **{global_stats.get('critical_poles', 0)}**"
                f"  |  ⚡ **{global_stats.get('fast_poles', 0)}**"
                f"  |  🏁 **{global_stats.get('normal_poles', 0)}**"
                f"  |  🐷 **{global_stats.get('marranero_poles', 0)}**"
            )
            embed.add_field(
                name=t('profile.field.breakdown', gid_ctx),
                value=breakdown,
                inline=False
            )
            
            # Último pole (GLOBAL, puede ser de cualquier servidor)
            footer_text = ""
            guild_id = interaction.guild.id if interaction.guild else None
            if global_user and global_user['last_pole_date']:
                last_date = datetime.strptime(global_user['last_pole_date'], '%Y-%m-%d')
                footer_text = t('profile.footer.last_pole', guild_id, date=last_date.strftime('%d/%m/%Y'))
            
            if footer_text:
                footer_text += " • " + t('leaderboard.footer.use_local', guild_id)
            else:
                footer_text = t('leaderboard.footer.use_local', guild_id)
            embed.set_footer(text=footer_text)
            
            await interaction.followup.send(embed=embed)
        
        # ==================== ALCANCE LOCAL ====================
        else:  # alcance == "local"
            if interaction.guild is None:
                await interaction.followup.send(t('errors.command_server_only', None), ephemeral=True)
                return
            
            gid = interaction.guild.id
            
            # Obtener datos LOCALES del servidor
            user_data = await self.db.get_user(target_user.id, gid)
            global_user = await self.db.get_global_user(target_user.id)
            
            if not user_data or user_data['total_poles'] == 0:
                await interaction.followup.send(
                    t('profile.no_data_local', gid, mention=target_user.mention),
                    ephemeral=True
                )
                return
            
            # Obtener stats de la temporada actual (SOLO este servidor)
            current_season_id = get_current_season()
            season_stats = await self.db.get_season_stats(target_user.id, gid, current_season_id)

            # Obtener rango histórico basado en el mejor desempeño en cualquier temporada (SOLO este servidor)
            best_season_points = await self.db.get_user_best_season_points(target_user.id, gid)
            rank_emoji, rank_name = get_rank_info(best_season_points, gid)
            
            # Crear embed
            embed = discord.Embed(
                title=t('profile.title_local', gid, display_name=target_user.display_name,
                        guild_name=interaction.guild.name),
                description=t('profile.desc_local', gid),
                color=discord.Color.blurple(),
                timestamp=datetime.now(LOCAL_TZ)
            )
            embed.set_thumbnail(url=target_user.display_avatar.url)

            # Fila 1: temporada actual + rango histórico
            if season_stats and season_stats.get('season_poles', 0) > 0:
                season_rank_emoji, season_rank_name = get_rank_info(season_stats['season_points'], gid)
                season_value = t(
                    'profile.field.season_rank_value',
                    gid,
                    emoji=season_rank_emoji,
                    name=season_rank_name,
                    points=f"{season_stats['season_points']:.1f}"
                )
            else:
                season_value = t('common.none', gid)

            embed.add_field(
                name=t('profile.field.season_current', gid),
                value=season_value,
                inline=True
            )
            
            # Rango Histórico (basado en mejor temporada EN ESTE SERVIDOR)
            embed.add_field(
                name=t('profile.field.rank_historical_server', gid),
                value=t('profile.field.rank_value', gid,
                        emoji=rank_emoji, name=rank_name, best_points=f"{best_season_points:.1f}"),
                inline=True
            )
            embed.add_field(name="\u200b", value="\u200b", inline=True)
            
            # Grid 2x2 de métricas
            embed.add_field(
                name=t('profile.field.points_server', gid),
                value=f"**{user_data['total_points']:.1f}** {t('common.pts', gid)}",
                inline=True
            )
            embed.add_field(
                name=t('profile.field.poles_server', gid),
                value=f"**{user_data['total_poles']}**",
                inline=True
            )
            embed.add_field(name="\u200b", value="\u200b", inline=True)
            
            # Racha actual (GLOBAL entre servidores)
            current_streak = global_user['current_streak'] if global_user else 0
            streak_emoji = FIRE if current_streak > 0 else GRAY_FIRE
            embed.add_field(
                name=t('profile.field.current_streak_global', gid, emoji=streak_emoji),
                value=t('profile.field.streak_days', gid, days=current_streak),
                inline=True
            )
            
            # Mejor racha (GLOBAL entre servidores)
            best_streak = global_user['best_streak'] if global_user else 0
            best_streak_emoji = FIRE if best_streak > 0 else GRAY_FIRE
            embed.add_field(
                name=t('profile.field.best_streak_global', gid, emoji=best_streak_emoji),
                value=t('profile.field.streak_days', gid, days=best_streak),
                inline=True
            )
            embed.add_field(name="\u200b", value="\u200b", inline=True)
            
            # Desglose por tipo compacto (centrado visualmente)
            breakdown = (
                f"💎 **{user_data.get('critical_poles', 0)}**"
                f"  |  ⚡ **{user_data.get('fast_poles', 0)}**"
                f"  |  🏁 **{user_data.get('normal_poles', 0)}**"
                f"  |  🐷 **{user_data.get('marranero_poles', 0)}**"
            )
            embed.add_field(
                name=t('profile.field.breakdown_server', gid),
                value=breakdown,
                inline=False
            )
            
            # Footer
            footer_text = t('leaderboard.footer.use_global', gid)
            embed.set_footer(text=footer_text)
            
            await interaction.followup.send(embed=embed)
    
    async def temporada_autocomplete(
        self,
        interaction: discord.Interaction,
        current: str,
    ) -> list[app_commands.Choice[str]]:
        """Autocomplete para temporadas disponibles"""
        from utils.scoring import get_current_season
        
        # Obtener temporadas disponibles
        seasons = await self.db.get_available_seasons()
        current_season_id = get_current_season()
        
        # Crear choices: primero "Temporada Actual", luego Lifetime, luego el resto
        choices = []
        
        # Opción 1: Temporada actual (default)
        current_season = next((s for s in seasons if s['season_id'] == current_season_id), None)
        if current_season:
            choices.append(app_commands.Choice(
                name=f"⭐ {current_season['season_name']} (Actual)",
                value=current_season['season_id']
            ))
        
        # Opción 2: Lifetime (todas las temporadas)
        choices.append(app_commands.Choice(
            name="🏆 Lifetime (Todas las temporadas)",
            value="lifetime"
        ))
        
        # Opción 3: Resto de temporadas (ordenadas por más reciente)
        for season in seasons:
            if season['season_id'] != current_season_id:  # Ya la pusimos arriba
                emoji = "🎯" if season['is_active'] else "📜"
                choices.append(app_commands.Choice(
                    name=f"{emoji} {season['season_name']}",
                    value=season['season_id']
                ))
        
        # Filtrar por lo que el usuario está escribiendo
        if current:
            choices = [c for c in choices if current.lower() in c.name.lower()]
        
        # Discord limita a 25 choices
        return choices[:25]
    
    @app_commands.command(name="leaderboard", description=_T('cmd.leaderboard.desc'))
    @app_commands.describe(
        alcance=_T('cmd.leaderboard.scope_param'),
        tipo=_T('cmd.leaderboard.type_param'),
        temporada=_T('cmd.leaderboard.season_param'),
        limite=_T('cmd.leaderboard.limit_param')
    )
    @app_commands.choices(
        alcance=[
            app_commands.Choice(name="Local (this server)", value="local"),
            app_commands.Choice(name="Global (all servers)", value="global")
        ],
        tipo=[
            app_commands.Choice(name="Players", value="personas"),
            app_commands.Choice(name="Servers", value="servers"),
            app_commands.Choice(name="Streaks", value="rachas")
        ]
    )
    @app_commands.autocomplete(temporada=temporada_autocomplete)
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
                t('leaderboard.error_limit', interaction.guild.id if interaction.guild else None),
                ephemeral=True
            )
            return
        
        # Obtener temporada actual y disponibles
        from utils.scoring import get_current_season
        current_season_id = get_current_season()
        
        # Si no se especifica temporada, usar la temporada ACTUAL (no lifetime)
        if temporada is None:
            temporada = current_season_id
        
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
                await interaction.followup.send(t('errors.command_server_only', None), ephemeral=True)
                return
            gid = interaction.guild.id
            
            # Obtener datos según temporada
            if is_lifetime:
                top_users = await self.db.get_leaderboard(gid, limite)
                points_key = 'total_points'
                poles_key = 'total_poles'
                title_suffix = "Lifetime"
            else:
                top_users = await self.db.get_season_leaderboard(gid, season_id, limite)
                points_key = 'season_points'
                poles_key = 'season_poles'
                # Obtener nombre legible de la season
                seasons = await self.db.get_available_seasons()
                season_name = next((s['season_name'] for s in seasons if s['season_id'] == season_id), season_id)
                title_suffix = season_name
            
            if not top_users:
                await interaction.followup.send(
                    t('leaderboard.no_data_local', gid, season_info='de esta temporada ' if not is_lifetime else ''),
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title=t('leaderboard.title.local_people', gid, season=title_suffix),
                description=t('leaderboard.desc.local_people', gid, server=interaction.guild.name),
                color=discord.Color.gold(),
                timestamp=datetime.now(LOCAL_TZ)
            )
            
            ranking_text = ""
            for idx, user_data in enumerate(top_users, start=1):
                points = user_data.get(points_key, 0)
                poles = user_data.get(poles_key, 0)
                rank_emoji, _ = get_rank_info(points, gid)
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
                
                ranking_text += (
                    f"{position_emoji} {rank_emoji} **{user_data['username']}**{guild_text}"
                    f" • 💰 {points:.1f} {t('common.pts', gid)}"
                    f" • 🏁 {poles} {t('common.poles', gid)}{streak_info}\n"
                )
            
            embed.description = ranking_text
            
            # Footer con posición del usuario
            if is_lifetime:
                user_data = await self.db.get_user(interaction.user.id, gid)
                if user_data:
                    all_users = await self.db.get_leaderboard(gid, 1000)
                    user_position = next(
                        (idx for idx, u in enumerate(all_users, start=1) if u['user_id'] == interaction.user.id),
                        None
                    )
                    if user_position:
                        embed.set_footer(text=t('leaderboard.footer.position', gid, pos=user_position, total=len(all_users)))
            else:
                user_data = await self.db.get_season_stats(interaction.user.id, gid, season_id)
                if user_data:
                    all_users = await self.db.get_season_leaderboard(gid, season_id, 1000)
                    user_position = next(
                        (idx for idx, u in enumerate(all_users, start=1) if u['user_id'] == interaction.user.id),
                        None
                    )
                    if user_position:
                        embed.set_footer(text=t('leaderboard.footer.position_season', gid, season=title_suffix, pos=user_position, total=len(all_users)))
        
        # LOCAL + SERVIDORES
        elif alcance == "local" and tipo == "servers":
            if interaction.guild is None:
                await interaction.followup.send(t('errors.command_server_only', None), ephemeral=True)
                return
            gid = interaction.guild.id
            
            # Obtener datos según temporada
            if is_lifetime:
                top_servers = await self.db.get_local_server_leaderboard(gid, limite)
                title_suffix = "Lifetime"
            else:
                top_servers = await self.db.get_local_server_season_leaderboard(gid, season_id, limite)
                seasons = await self.db.get_available_seasons()
                season_name = next((s['season_name'] for s in seasons if s['season_id'] == season_id), season_id)
                title_suffix = season_name
            
            if not top_servers:
                await interaction.followup.send(
                    t('leaderboard.no_data_servers', gid, season_info='en esta temporada' if not is_lifetime else ''),
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title=t('leaderboard.title.local_servers', gid, season=title_suffix),
                description=t('leaderboard.desc.local_servers', gid, server=interaction.guild.name),
                color=discord.Color.blue(),
                timestamp=datetime.now(LOCAL_TZ)
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
                await interaction.followup.send(t('errors.command_server_only', None), ephemeral=True)
                return
            gid = interaction.guild.id
            
            # Obtener usuarios activos del servidor (tienen poles locales)
            local_users = await self.db.get_leaderboard(gid, limit=1000, order_by='points')
            if not local_users:
                await interaction.followup.send(
                    t('errors.no_users', gid),
                    ephemeral=True
                )
                return
            
            # Obtener rachas GLOBALES de esos usuarios
            user_ids = [u['user_id'] for u in local_users]
            users_with_streaks = []
            
            for uid in user_ids:
                global_user = await self.db.get_global_user(uid)
                if global_user and (global_user['current_streak'] > 0 or global_user['best_streak'] > 0):
                    users_with_streaks.append(global_user)
            
            # Ordenar por racha actual (descendente), luego por mejor racha
            users_with_streaks.sort(key=lambda u: (u['current_streak'], u['best_streak']), reverse=True)
            top_users = users_with_streaks[:limite]
            
            if not top_users:
                await interaction.followup.send(
                    t('errors.no_streaks', gid),
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title=t('leaderboard.title.local_streaks', gid),
                description=t('leaderboard.desc.local_streaks', gid, server=interaction.guild.name),
                color=discord.Color.orange(),
                timestamp=datetime.now(LOCAL_TZ)
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
            global_user = await self.db.get_global_user(interaction.user.id)
            if global_user:
                user_position = next(
                    (idx for idx, u in enumerate(users_with_streaks, start=1) if u['user_id'] == interaction.user.id),
                    None
                )
                if user_position:
                    embed.set_footer(text=t('leaderboard.footer.streak_position', gid, 
                                            pos=user_position, 
                                            streak=global_user.get('current_streak', 0)))
        
        # GLOBAL + RACHAS
        elif alcance == "global" and tipo == "rachas":
            # Obtener rachas globales
            top_users = await self.db.get_global_leaderboard(limite, order_by='streak')
            
            if not top_users:
                await interaction.followup.send(
                    t('leaderboard.no_data_streaks_global', interaction.guild.id if interaction.guild else None),
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title=t('leaderboard.title.global_streaks', interaction.guild.id if interaction.guild else None),
                color=discord.Color.orange(),
                timestamp=datetime.now(LOCAL_TZ)
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
                top_users = await self.db.get_global_leaderboard(limite)
                points_key = 'total_points'
                poles_key = 'total_poles'
                title_suffix = "Lifetime"
            else:
                top_users = await self.db.get_global_season_leaderboard(season_id, limite)
                points_key = 'total_season_points'
                poles_key = 'total_season_poles'
                seasons = await self.db.get_available_seasons()
                season_name = next((s['season_name'] for s in seasons if s['season_id'] == season_id), season_id)
                title_suffix = season_name
            
            if not top_users:
                await interaction.followup.send(
                    t('leaderboard.no_data_global', interaction.guild.id if interaction.guild else None,
                      season_info=' de esta temporada' if not is_lifetime else ''),
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title=t('leaderboard.title.global_people', interaction.guild.id if interaction.guild else None, season=title_suffix),
                color=discord.Color.gold(),
                timestamp=datetime.now(LOCAL_TZ)
            )
            
            ranking_text = ""
            for idx, user_data in enumerate(top_users, start=1):
                points = user_data.get(points_key, 0)
                poles = user_data.get(poles_key, 0)
                rank_emoji, _ = get_rank_info(points, interaction.guild.id if interaction.guild else None)
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
                
                ranking_text += (
                    f"{position_emoji} {rank_emoji} **{user_data['username']}**{guild_text}"
                    f" • 💰 {points:.1f} {t('common.pts', interaction.guild.id if interaction.guild else None)}"
                    f" • 🏁 {poles} {t('common.poles', interaction.guild.id if interaction.guild else None)}{streak_info}\n"
                )
            
            embed.description = ranking_text
        
        # GLOBAL + SERVIDORES
        else:  # alcance == "global" and tipo == "servers"
            # Obtener datos según temporada
            if is_lifetime:
                top_servers = await self.db.get_global_server_leaderboard(limite)
                title_suffix = "Lifetime"
            else:
                top_servers = await self.db.get_global_server_season_leaderboard(season_id, limite)
                seasons = await self.db.get_available_seasons()
                season_name = next((s['season_name'] for s in seasons if s['season_id'] == season_id), season_id)
                title_suffix = season_name
            
            if not top_servers:
                await interaction.followup.send(
                    t('leaderboard.no_data_servers_global', interaction.guild.id if interaction.guild else None,
                      season_info=' en esta temporada' if not is_lifetime else ''),
                    ephemeral=True
                )
                return
            
            embed = discord.Embed(
                title=f"🌍 RANKING GLOBAL - Servidores - {title_suffix}",
                color=discord.Color.blue(),
                timestamp=datetime.now(LOCAL_TZ)
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

    @app_commands.command(name="putometro", description=_T('cmd.putometro.desc'))
    @app_commands.describe(
        alcance=_T('cmd.putometro.scope_param'),
        limite=_T('cmd.putometro.limit_param')
    )
    @app_commands.choices(
        alcance=[
            _C('choice.putometro.scope.local', 'local'),
            _C('choice.putometro.scope.global', 'global')
        ]
    )
    async def putometro(
        self,
        interaction: discord.Interaction,
        alcance: str = "local",
        limite: app_commands.Range[int, 1, 25] = 10,
    ):
        """Ver ranking del putómetro local (usuarios) o global (guilds)."""
        if interaction.guild is None:
            await interaction.response.send_message(t('putometro.error.server_only', None), ephemeral=True)
            return

        await interaction.response.defer()
        gid = interaction.guild.id

        try:
            if alcance == 'local':
                top_users = await self.db.get_puta_user_leaderboard(gid, int(limite))
                guild_total = await self.db.get_puta_guild_total(gid)

                if guild_total <= 0 or not top_users:
                    embed = discord.Embed(
                        title=t('putometro.rank.local.title', gid, server=interaction.guild.name),
                        description=t('putometro.empty.local', gid),
                        color=discord.Color.blurple(),
                        timestamp=datetime.now(LOCAL_TZ),
                    )
                    embed.set_footer(text=t('putometro.footer.local', gid))
                    await interaction.followup.send(embed=embed)
                    return

                embed = discord.Embed(
                    title=t('putometro.rank.local.title', gid, server=interaction.guild.name),
                    description=t('putometro.rank.local.desc', gid),
                    color=discord.Color.purple(),
                    timestamp=datetime.now(LOCAL_TZ),
                )

                top_lines = [
                    t(
                        'putometro.rank.local.entry',
                        gid,
                        position=idx,
                        mention=f"<@{int(user_row['user_id'])}>",
                        count=int(user_row['total_count']),
                    )
                    for idx, user_row in enumerate(top_users, start=1)
                ]
                embed.add_field(
                    name=t('putometro.rank.local.field.top', gid, limit=int(limite)),
                    value="\n".join(top_lines),
                    inline=False,
                )

                user_total = await self.db.get_puta_user_count(gid, interaction.user.id)
                user_rank = await self.db.get_puta_user_rank(gid, interaction.user.id)
                if user_total > 0 and user_rank is not None:
                    you_value = t(
                        'putometro.rank.local.you_value',
                        gid,
                        mention=interaction.user.mention,
                        user_count=user_total,
                        position=user_rank,
                    )
                else:
                    you_value = t(
                        'putometro.rank.local.you_none',
                        gid,
                        mention=interaction.user.mention,
                    )
                embed.add_field(
                    name=t('putometro.rank.local.field.you', gid),
                    value=you_value,
                    inline=False,
                )

                embed.add_field(
                    name=t('putometro.rank.local.field.total', gid),
                    value=t('putometro.rank.local.total_value', gid, guild_total=guild_total, server=interaction.guild.name),
                    inline=False,
                )

                updated_text = t('putometro.footer.updated', gid, time=datetime.now(LOCAL_TZ).strftime('%H:%M:%S'))
                local_text = t('putometro.footer.local', gid)
                embed.set_footer(text=f"{updated_text} • {local_text}")
                await interaction.followup.send(embed=embed)
                return

            if alcance == 'global':
                top_guilds = await self.db.get_puta_guild_leaderboard(int(limite))
                guilds_count = await self.db.get_puta_guilds_count()

                if not top_guilds:
                    embed = discord.Embed(
                        title=t('putometro.rank.global.title', gid),
                        description=t('putometro.empty.global', gid),
                        color=discord.Color.blurple(),
                        timestamp=datetime.now(LOCAL_TZ),
                    )
                    embed.set_footer(text=t('putometro.footer.global', gid, guilds_count=0))
                    await interaction.followup.send(embed=embed)
                    return

                def guild_name_or_unknown(target_guild_id: int) -> str:
                    target_guild = self.bot.get_guild(target_guild_id)
                    if target_guild:
                        return target_guild.name
                    return t('putometro.guild.unknown', gid, target_id=target_guild_id)

                embed = discord.Embed(
                    title=t('putometro.rank.global.title', gid),
                    description=t('putometro.rank.global.desc', gid),
                    color=discord.Color.gold(),
                    timestamp=datetime.now(LOCAL_TZ),
                )

                champion = top_guilds[0]
                champion_name = guild_name_or_unknown(int(champion['guild_id']))
                embed.add_field(
                    name=t('putometro.rank.global.field.champion', gid),
                    value=t('putometro.rank.global.champion_value', gid, guild_name=champion_name, count=int(champion['total_count'])),
                    inline=False,
                )

                top_lines = [
                    t(
                        'putometro.rank.global.entry',
                        gid,
                        position=idx,
                        guild_name=guild_name_or_unknown(int(guild_row['guild_id'])),
                        count=int(guild_row['total_count']),
                    )
                    for idx, guild_row in enumerate(top_guilds, start=1)
                ]
                embed.add_field(
                    name=t('putometro.rank.global.field.top', gid, limit=int(limite)),
                    value="\n".join(top_lines),
                    inline=False,
                )

                current_total = await self.db.get_puta_guild_total(gid)
                current_rank = await self.db.get_puta_guild_rank(gid)
                if current_total > 0 and current_rank is not None:
                    current_value = t(
                        'putometro.rank.global.current_value',
                        gid,
                        guild_name=interaction.guild.name,
                        position=current_rank,
                        count=current_total,
                    )
                else:
                    current_value = t('putometro.rank.global.current_none', gid, guild_name=interaction.guild.name)
                embed.add_field(
                    name=t('putometro.rank.global.field.current', gid),
                    value=current_value,
                    inline=False,
                )

                updated_text = t('putometro.footer.updated', gid, time=datetime.now(LOCAL_TZ).strftime('%H:%M:%S'))
                global_text = t('putometro.footer.global', gid, guilds_count=guilds_count)
                embed.set_footer(text=f"{updated_text} • {global_text}")
                await interaction.followup.send(embed=embed)
                return

            await interaction.followup.send(t('putometro.error.invalid_scope', gid), ephemeral=True)
        except Exception as exc:
            log.error(f"❌ Error en /putometro guild={gid}: {exc}")
            await interaction.followup.send(t('putometro.error.load_failed', gid), ephemeral=True)
    
    @app_commands.command(name="streak", description=_T('cmd.streak.desc'))
    async def streak(self, interaction: discord.Interaction):
        """Ver información de racha del usuario"""
        # Defer para evitar timeout
        await interaction.response.defer()
        
        if interaction.guild is None:
            await interaction.followup.send(t('errors.command_server_only', None), ephemeral=True)
            return
        gid = interaction.guild.id
        user_data = await self.db.get_user(interaction.user.id, gid)
        
        if not user_data or user_data['total_poles'] == 0:
            await interaction.followup.send(
                t('streak.no_poles', gid),
                ephemeral=True
            )
            return
        
        # Crear embed
        streak_title_emoji = FIRE if user_data['current_streak'] > 0 else GRAY_FIRE
        embed = discord.Embed(
            title=f"{streak_title_emoji} Tu Racha Actual",
            color=discord.Color.orange() if user_data['current_streak'] > 0 else discord.Color.red(),
            timestamp=datetime.now(LOCAL_TZ)
        )
        
        embed.set_thumbnail(url=interaction.user.display_avatar.url)
        
        # Racha actual
        if user_data['current_streak'] > 0:
            multiplier = get_streak_multiplier(user_data['current_streak'])
            current_streak_emoji = FIRE if user_data['current_streak'] > 1 else GRAY_FIRE
            
            embed.add_field(
                name=t('profile.streak.current_title', gid, emoji=current_streak_emoji),
                value=t('profile.streak.current_value', gid, days=user_data['current_streak'], multiplier=multiplier),
                inline=False
            )
            
            # Calcular próximo hito
            milestones = [7, 14, 21, 30, 45, 60, 75, 90, 120, 150, 180, 210, 240, 270, 300, 365]
            next_milestone = next((m for m in milestones if m > user_data['current_streak']), None)
            
            if next_milestone:
                days_to_next = next_milestone - user_data['current_streak']
                next_multiplier = get_streak_multiplier(next_milestone)
                embed.add_field(
                    name=t('streak.next_milestone', gid),
                    value=t('streak.next_milestone_value', gid, milestone=next_milestone, days=days_to_next, multiplier=next_multiplier),
                    inline=False
                )
        else:
            embed.add_field(
                name=t('streak.off', gid),
                value=t('streak.off_desc', gid),
                inline=False
            )
        
        # Mejor racha
        embed.add_field(
            name=t('streak.best', gid),
            value=t('streak.best_value', gid, streak=user_data['best_streak']),
            inline=True
        )
        
        # Último pole
        if user_data['last_pole_date']:
            last_date = datetime.strptime(user_data['last_pole_date'], '%Y-%m-%d').date()
            today = datetime.now(LOCAL_TZ).date()
            days_since = (today - last_date).days
            
            if days_since == 0:
                last_text = t('streak.last_pole_today', gid)
            elif days_since == 1:
                last_text = t('streak.last_pole_yesterday', gid)
            else:
                last_text = t('streak.last_pole_days_ago', gid, days=days_since)
            
            embed.add_field(
                name=t('streak.last_pole', gid),
                value=last_text,
                inline=True
            )
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="polehelp", description=_T('cmd.polehelp.desc'))
    async def polehelp(self, interaction: discord.Interaction):
        """Mostrar ayuda del bot"""
        gid = interaction.guild.id if interaction.guild else None
        embed = discord.Embed(
            title=t('help.title', gid),
            description=t('help.description', gid),
            color=discord.Color.blue(),
            timestamp=datetime.now(LOCAL_TZ)
        )
        
        # Cómo jugar
        embed.add_field(
            name=t('help.how_to_play', gid),
            value=t('help.how_to_play_desc', gid),
            inline=False
        )
        
        # Tipos de pole según delay
        embed.add_field(
            name=t('help.categories', gid),
            value=t('help.categories_desc', gid),
            inline=False
        )
        
        # Rachas
        embed.add_field(
            name=t('help.streaks', gid),
            value=t('help.streaks_desc', gid),
            inline=False
        )
        
        # Comandos
        embed.add_field(
            name=t('help.commands', gid),
            value=t('help.commands_desc', gid),
            inline=False
        )
        
        embed.set_footer(text=t('help.footer', gid))
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="season", description=_T('cmd.season.desc'))
    async def season(self, interaction: discord.Interaction):
        """Ver información de la temporada actual"""
        if not interaction.guild:
            await interaction.response.send_message(t('errors.command_server_only', None), ephemeral=True)
            return
        await interaction.response.defer()
        
        from utils.scoring import get_current_season, get_season_info
        
        current_season_id = get_current_season()
        season_info = get_season_info(current_season_id)
        
        # Obtener stats del usuario en esta temporada
        season_stats = await self.db.get_season_stats(interaction.user.id, interaction.guild.id, current_season_id)
        
        # Crear embed
        gid = interaction.guild.id
        embed = discord.Embed(
            title=f"🎮 {season_info['name']}",
            description=t('season.period', gid, start=season_info['start_date'], end=season_info['end_date']),
            color=discord.Color.gold() if season_info['is_ranked'] else discord.Color.blue(),
            timestamp=datetime.now(LOCAL_TZ)
        )
        
        # Estado de la temporada
        status = t('season.official', gid) if season_info['is_ranked'] else t('season.practice', gid)
        embed.add_field(name=t('season.status', gid), value=status, inline=False)
        
        # Calcular tiempo restante
        try:
            end_date = datetime.strptime(str(season_info['end_date']), '%Y-%m-%d').date()
            today = datetime.now(LOCAL_TZ).date()
            days_left = (end_date - today).days
            
            if days_left > 0:
                embed.add_field(
                    name=t('season.time_remaining', gid),
                    value=t('season.days_left', gid, days=days_left),
                    inline=True
                )
            else:
                embed.add_field(
                    name=t('season.status', gid),
                    value=t('season.finished', gid),
                    inline=True
                )
        except:
            pass
        
        # Stats del usuario en esta temporada
        if season_stats and season_stats.get('season_poles', 0) > 0:
            rank_emoji, rank_name = get_rank_info(season_stats['season_points'], gid)
            
            embed.add_field(
                name=t('season.your_progress', gid, season=season_info['name']),
                value=t('season.your_progress_desc', gid,
                        emoji=rank_emoji, name=rank_name,
                        points=f"{season_stats['season_points']:.1f}",
                        poles=season_stats['season_poles'],
                        streak=season_stats['season_best_streak']),
                inline=False
            )
            
            # Desglose por tipo
            embed.add_field(
                name=t('season.breakdown', gid),
                value=t('season.breakdown_desc', gid,
                        critical=season_stats['season_critical'],
                        fast=season_stats['season_fast'],
                        normal=season_stats['season_normal'],
                        marranero=season_stats['season_marranero']),
                inline=False
            )
        else:
            embed.add_field(
                name=t('season.your_progress', gid, season=""),
                value=t('season.no_poles', gid, season=season_info['name']),
                inline=False
            )
        
        embed.set_footer(text=t('season.footer', gid))
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="history", description=_T('cmd.mystats.desc'))
    async def history(self, interaction: discord.Interaction):
        """Ver historial de temporadas pasadas"""
        if not interaction.guild:
            await interaction.response.send_message(t('errors.command_server_only', None), ephemeral=True)
            return
        await interaction.response.defer()
        
        # Obtener badges del usuario
        badges = await self.db.get_user_badges(interaction.user.id, interaction.guild.id)

        # Obtener historial de temporadas
        async with self.db.get_connection() as conn:
            cursor = await conn.execute('''
                SELECT season_id, final_points, final_rank, final_badge,
                       final_position, total_players, total_poles, best_streak,
                       season_ended_at
                FROM season_history
                WHERE user_id = ? AND guild_id = ?
                ORDER BY season_ended_at DESC
                LIMIT 10
            ''', (interaction.user.id, interaction.guild.id))
            history = await cursor.fetchall()
        
        gid = interaction.guild.id
        embed = discord.Embed(
            title=t('mystats.title', gid, user=interaction.user.display_name),
            description=t('mystats.description', gid),
            color=discord.Color.purple(),
            timestamp=datetime.now(LOCAL_TZ)
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
                name=t('mystats.badges', gid),
                value=badge_text or t('mystats.no_badges', gid),
                inline=False
            )
        else:
            embed.add_field(
                name=t('mystats.badges', gid),
                value=t('mystats.no_badges', gid),
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
                name=t('mystats.seasons', gid),
                value=history_text,
                inline=False
            )
        else:
            embed.add_field(
                name=t('mystats.seasons', gid),
                value=t('mystats.no_seasons', gid),
                inline=False
            )
        
        embed.set_footer(text=t('season.footer', gid))
        await interaction.followup.send(embed=embed)
    
    # [DEPRECATED] season_leaderboard eliminado. Usar /leaderboard con 'temporada'.
    
    # ==================== HELPERS DE TEMPORADA ====================
    
    async def _send_season_change_announcement(
        self,
        old_season_id: str,
        new_season_id: str,
        target_guild_id: Optional[int] = None,
    ):
        """
        🎬 POLE REWIND - Enviar resumen de año con estadísticas y celebración
        Sistema de 8 mensajes: Intro + 5 categorías locales + 1 global condensado + cierre
        """
        from utils.scoring import get_season_info
        
        old_info = get_season_info(old_season_id)
        new_info = get_season_info(new_season_id)
        
        # Detectar si es la transición BETA → Temporada 1
        is_first_season = (old_season_id == "2025")
        
        # Obtener servidores configurados
        async with self.db.get_connection() as conn:
            if target_guild_id is None:
                cursor = await conn.execute(
                    'SELECT guild_id, pole_channel_id FROM servers WHERE pole_channel_id IS NOT NULL'
                )
                servers = await cursor.fetchall()
            else:
                cursor = await conn.execute(
                    'SELECT guild_id, pole_channel_id FROM servers WHERE guild_id = ? AND pole_channel_id IS NOT NULL',
                    (target_guild_id,)
                )
                servers = await cursor.fetchall()
        
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
                        title=t('rewind.intro_first_title', guild.id),
                        description=t('rewind.intro_first_desc', guild.id, season=old_season_id),
                        color=discord.Color.gold(),
                        timestamp=datetime.now(LOCAL_TZ)
                    )
                else:
                    embed_intro = discord.Embed(
                        title=t('rewind.intro_title', guild.id),
                        description=t('rewind.intro_desc', guild.id, season=old_season_id),
                        color=discord.Color.gold(),
                        timestamp=datetime.now(LOCAL_TZ)
                    )
                
                embed_intro.set_thumbnail(url="https://em-content.zobj.net/thumbs/120/twitter/348/party-popper_1f389.png")
                await channel.send(embed=embed_intro)
                await asyncio.sleep(2)
                
                # Obtener datos
                local_rankings = await self._get_season_rankings_local(guild_id, old_season_id)
                global_rankings = await self._get_season_rankings_global(old_season_id)
                puta_rankings = await self.db.get_puta_user_leaderboard(guild_id, 3)
                puta_total = await self.db.get_puta_guild_total(guild_id)
                
                # ==================== MENSAJE 2: 👑 MÁXIMOS ANOTADORES (Local) ====================
                embed_points_local = discord.Embed(
                    title=t('rewind.local_points_title', guild.id, server=guild.name),
                    description=t('rewind.local_points_desc', guild.id),
                    color=discord.Color.gold(),
                    timestamp=datetime.now(LOCAL_TZ)
                )
                
                if local_rankings['points']:
                    for i, (uid, pts) in enumerate(local_rankings['points'][:3], 1):
                        medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉'
                        dedication = self._get_dedication_points(i, guild.id)
                        embed_points_local.add_field(
                            name=f"{medal} {dedication}",
                            value=t('rewind.points_value', guild.id, uid=uid, points=pts),
                            inline=False
                        )
                else:
                    if embed_points_local.description:
                        embed_points_local.description += "\n\n" + t('rewind.no_data', guild.id)
                
                embed_points_local.set_footer(text=t('rewind.footer_hof', guild.id, season=old_season_id, tagline=t('rewind.tagline.points', guild.id)))
                await channel.send(embed=embed_points_local)
                await asyncio.sleep(1.5)
                
                # ==================== MENSAJE 3: ⚡ MÁS POLES (Local) ====================
                embed_poles_local = discord.Embed(
                    title=t('rewind.local_poles_title', guild.id, server=guild.name),
                    description=t('rewind.local_poles_desc', guild.id),
                    color=discord.Color.red(),
                    timestamp=datetime.now(LOCAL_TZ)
                )
                
                if local_rankings['poles']:
                    for i, (uid, count) in enumerate(local_rankings['poles'][:3], 1):
                        medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉'
                        dedication = self._get_dedication_poles(i, guild.id)
                        embed_poles_local.add_field(
                            name=f"{medal} {dedication}",
                            value=t('rewind.poles_value', guild.id, uid=uid, count=count),
                            inline=False
                        )
                else:
                    if embed_poles_local.description:
                        embed_poles_local.description += "\n\n" + t('rewind.no_data', guild.id)
                
                embed_poles_local.set_footer(text=t('rewind.footer_hof', guild.id, season=old_season_id, tagline=t('rewind.tagline.poles', guild.id)))
                await channel.send(embed=embed_poles_local)
                await asyncio.sleep(1.5)
                
                # ==================== MENSAJE 4: 🔥 MEJOR RACHA (Local) ====================
                embed_streak_local = discord.Embed(
                    title=t('rewind.local_streaks_title', guild.id, server=guild.name),
                    description=t('rewind.local_streaks_desc', guild.id),
                    color=discord.Color.orange(),
                    timestamp=datetime.now(LOCAL_TZ)
                )
                
                if local_rankings['streaks']:
                    for i, (uid, streak) in enumerate(local_rankings['streaks'][:3], 1):
                        medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉'
                        dedication = self._get_dedication_streak(i, guild.id)
                        embed_streak_local.add_field(
                            name=f"{medal} {dedication}",
                            value=t('rewind.streak_value', guild.id, uid=uid, streak=streak),
                            inline=False
                        )
                else:
                    if embed_streak_local.description:
                        embed_streak_local.description += "\n\n" + t('rewind.no_data', guild.id)
                
                embed_streak_local.set_footer(text=t('rewind.footer_hof', guild.id, season=old_season_id, tagline=t('rewind.tagline.streaks', guild.id)))
                await channel.send(embed=embed_streak_local)
                await asyncio.sleep(1.5)
                
                # ==================== MENSAJE 5: ⚡ VELOCISTAS (Local) ====================
                embed_speed_local = discord.Embed(
                    title=t('rewind.local_speed_title', guild.id, server=guild.name),
                    description=t('rewind.local_speed_desc', guild.id),
                    color=discord.Color.blue(),
                    timestamp=datetime.now(LOCAL_TZ)
                )
                
                if local_rankings['speed']:
                    for i, (uid, delay) in enumerate(local_rankings['speed'][:3], 1):
                        medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉'
                        dedication = self._get_dedication_speed(i, guild.id)
                        embed_speed_local.add_field(
                            name=f"{medal} {dedication}",
                            value=t('rewind.speed_value', guild.id, uid=uid, delay=delay),
                            inline=False
                        )
                else:
                    if embed_speed_local.description:
                        embed_speed_local.description += "\n\n" + t('rewind.no_data_speed', guild.id)
                
                embed_speed_local.set_footer(text=t('rewind.footer_hof', guild.id, season=old_season_id, tagline=t('rewind.tagline.speed', guild.id)))
                await channel.send(embed=embed_speed_local)
                await asyncio.sleep(1.5)

                # ==================== MENSAJE 6: 🔥 MÁS PUTERO (Local) ====================
                embed_puta_local = discord.Embed(
                    title=t('rewind.local_puta_title', guild.id, server=guild.name),
                    description=t('rewind.local_puta_desc', guild.id),
                    color=discord.Color.purple(),
                    timestamp=datetime.now(LOCAL_TZ)
                )

                if puta_rankings:
                    for i, row in enumerate(puta_rankings[:3], 1):
                        medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉'
                        dedication = self._get_dedication_puta(i, guild.id)
                        embed_puta_local.add_field(
                            name=f"{medal} {dedication}",
                            value=t('rewind.puta_value', guild.id, uid=int(row['user_id']), count=int(row['total_count'])),
                            inline=False
                        )
                else:
                    if embed_puta_local.description:
                        embed_puta_local.description += "\n\n" + t('rewind.no_data', guild.id)

                embed_puta_local.add_field(
                    name=t('rewind.puta_total_label', guild.id),
                    value=t('rewind.puta_total_value', guild.id, total=puta_total),
                    inline=False
                )

                embed_puta_local.set_footer(text=t('rewind.footer_hof', guild.id, season=old_season_id, tagline=t('rewind.tagline.puta', guild.id)))
                await channel.send(embed=embed_puta_local)
                await asyncio.sleep(2)
                
                # ==================== MENSAJE 7: 🌍 HALL OF FAME GLOBAL (CONDENSADO) ====================
                embed_global = discord.Embed(
                    title=t('rewind.global_title', guild.id),
                    description=t('rewind.global_desc', guild.id, season=old_season_id),
                    color=discord.Color.purple(),
                    timestamp=datetime.now(LOCAL_TZ)
                )
                
                # Puntos
                if global_rankings['points']:
                    points_text = t('rewind.global_points', guild.id) + "\n"
                    for i, (uid, pts) in enumerate(global_rankings['points'][:3], 1):
                        medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉'
                        points_text += f"{medal} <@{uid}> - **{pts:,}** pts\n"
                    embed_global.add_field(name="\u200b", value=points_text, inline=False)
                
                # Poles
                if global_rankings['poles']:
                    poles_text = t('rewind.global_poles', guild.id) + "\n"
                    for i, (uid, count) in enumerate(global_rankings['poles'][:3], 1):
                        medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉'
                        poles_text += f"{medal} <@{uid}> - **{count}** poles\n"
                    embed_global.add_field(name="\u200b", value=poles_text, inline=False)
                
                # Rachas
                if global_rankings['streaks']:
                    streak_text = t('rewind.global_streaks', guild.id) + "\n"
                    for i, (uid, streak) in enumerate(global_rankings['streaks'][:3], 1):
                        medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉'
                        streak_text += f"{medal} <@{uid}> - **{streak}** días\n"
                    embed_global.add_field(name="\u200b", value=streak_text, inline=False)
                
                # Velocidad
                if global_rankings['speed']:
                    speed_text = t('rewind.global_speed', guild.id) + "\n"
                    for i, (uid, delay) in enumerate(global_rankings['speed'][:3], 1):
                        medal = '🥇' if i == 1 else '🥈' if i == 2 else '🥉'
                        speed_text += f"{medal} <@{uid}> - **{delay:.1f}** min\n"
                    embed_global.add_field(name="\u200b", value=speed_text, inline=False)
                
                if not any([global_rankings['points'], global_rankings['poles'], 
                           global_rankings['streaks'], global_rankings['speed']]):
                    if embed_global.description:
                        embed_global.description += "\n\n" + t('rewind.no_data_global', guild.id)
                
                embed_global.set_footer(text=t('rewind.footer_global', guild.id))
                await channel.send(embed=embed_global)
                await asyncio.sleep(2)
                
                # ==================== MENSAJE 8: NUEVA TEMPORADA ====================
                season_name = str(new_info['name'])  # Type assertion para Pylance
                if is_first_season:
                    embed_new_season = discord.Embed(
                        title=t('rewind.new_season_first_title', guild.id, season=season_name.upper()),
                        description=t('rewind.new_season_first_desc', guild.id),
                        color=discord.Color.green(),
                        timestamp=datetime.now(LOCAL_TZ)
                    )
                else:
                    embed_new_season = discord.Embed(
                        title=t('rewind.new_season_title', guild.id, season=season_name.upper()),
                        description=t('rewind.new_season_desc', guild.id, season=season_name),
                        color=discord.Color.green(),
                        timestamp=datetime.now(LOCAL_TZ)
                    )
                
                embed_new_season.add_field(
                    name=t('rewind.new_season_duration', guild.id),
                    value=t('rewind.new_season_duration_value', guild.id, start=new_info['start_date'], end=new_info['end_date']),
                    inline=False
                )
                
                embed_new_season.set_footer(text=t('rewind.new_season_footer', guild.id))
                await channel.send(embed=embed_new_season)
                
                sent_count += 1
                await asyncio.sleep(0.5)
                
            except Exception as e:
                log.error(f"⚠️ Error enviando POLE REWIND a guild {server['guild_id']}: {e}")
                import traceback
                traceback.print_exc()
        
        log.info(f"🎬 POLE REWIND enviado a {sent_count} servidores")
    
    # ==================== DEDICATORIAS POLE REWIND ====================
    def _get_dedication_points(self, position: int, guild_id: int) -> str:
        """Dedicatoria para categoría Puntos (local)"""
        return t(f'dedication.points.{position}', guild_id)
    
    def _get_dedication_poles(self, position: int, guild_id: int) -> str:
        """Dedicatoria para categoría Poles (local)"""
        return t(f'dedication.poles.{position}', guild_id)
    
    def _get_dedication_streak(self, position: int, guild_id: int) -> str:
        """Dedicatoria para categoría Rachas (local)"""
        return t(f'dedication.streak.{position}', guild_id)
    
    def _get_dedication_speed(self, position: int, guild_id: int) -> str:
        """Dedicatoria para categoría Velocidad (local)"""
        return t(f'dedication.speed.{position}', guild_id)

    def _get_dedication_puta(self, position: int, guild_id: int) -> str:
        """Dedicatoria para categoría Putómetro (local)."""
        return t(f'dedication.puta.{position}', guild_id)
    
    def _get_dedication_points_global(self, position: int, guild_id: int) -> str:
        """Dedicatoria para categoría Puntos (global)"""
        return t(f'dedication.points_global.{position}', guild_id)
    
    def _get_dedication_poles_global(self, position: int, guild_id: int) -> str:
        """Dedicatoria para categoría Poles (global)"""
        return t(f'dedication.poles_global.{position}', guild_id)
    
    def _get_dedication_streak_global(self, position: int, guild_id: int) -> str:
        """Dedicatoria para categoría Rachas (global)"""
        return t(f'dedication.streak_global.{position}', guild_id)
    
    def _get_dedication_speed_global(self, position: int, guild_id: int) -> str:
        """Dedicatoria para categoría Velocidad (global)"""
        return t(f'dedication.speed_global.{position}', guild_id)
    
    async def _get_season_rankings_local(self, guild_id: int, season_id: str) -> dict:
        """Obtener rankings completos de un servidor (filtro: min 500 pts + min 10 poles para velocidad)"""
        from utils.scoring import RANK_THRESHOLDS
        MIN_RANK_POINTS = RANK_THRESHOLDS['silver']  # 500 puntos (rango Plata)

        async with self.db.get_connection() as conn:
            # Top 3 Puntos (mínimo rango Plata)
            cursor = await conn.execute('''
                SELECT user_id, season_points
                FROM season_stats
                WHERE guild_id = ? AND season_id = ?
                  AND season_points >= ?
                ORDER BY season_points DESC
                LIMIT 3
            ''', (guild_id, season_id, MIN_RANK_POINTS))
            top_points = [(row[0], row[1]) for row in await cursor.fetchall()]

            # Top 3 Poles (mínimo rango Plata)
            cursor = await conn.execute('''
                SELECT user_id, season_poles
                FROM season_stats
                WHERE guild_id = ? AND season_id = ?
                  AND season_points >= ?
                ORDER BY season_poles DESC
                LIMIT 3
            ''', (guild_id, season_id, MIN_RANK_POINTS))
            top_poles = [(row[0], row[1]) for row in await cursor.fetchall()]

            # Top 3 Rachas (mínimo rango Plata)
            cursor = await conn.execute('''
                SELECT user_id, season_best_streak
                FROM season_stats
                WHERE guild_id = ? AND season_id = ?
                  AND season_points >= ?
                ORDER BY season_best_streak DESC
                LIMIT 3
            ''', (guild_id, season_id, MIN_RANK_POINTS))
            top_streaks = [(row[0], row[1]) for row in await cursor.fetchall()]

            # Top 3 Velocidad (mínimo rango Plata + mínimo 10 poles)
            cursor = await conn.execute('''
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
            top_speed = [(row[0], row[1]) for row in await cursor.fetchall()]

        return {
            'points': top_points,
            'poles': top_poles,
            'streaks': top_streaks,
            'speed': top_speed
        }
    
    async def _get_season_rankings_global(self, season_id: str) -> dict:
        """Obtener rankings globales (filtro: min 500 pts total + min 10 poles para velocidad)"""
        from utils.scoring import RANK_THRESHOLDS
        MIN_RANK_POINTS = RANK_THRESHOLDS['silver']  # 500 puntos (rango Plata)

        async with self.db.get_connection() as conn:
            # Top 3 Puntos Global (mínimo rango Plata)
            cursor = await conn.execute('''
                SELECT user_id, SUM(season_points) as total_points
                FROM season_stats
                WHERE season_id = ?
                GROUP BY user_id
                HAVING total_points >= ?
                ORDER BY total_points DESC
                LIMIT 3
            ''', (season_id, MIN_RANK_POINTS))
            top_points = [(row[0], row[1]) for row in await cursor.fetchall()]

            # Top 3 Poles Global (mínimo rango Plata)
            cursor = await conn.execute('''
                SELECT user_id, SUM(season_poles) as total_poles
                FROM season_stats
                WHERE season_id = ?
                GROUP BY user_id
                HAVING SUM(season_points) >= ?
                ORDER BY total_poles DESC
                LIMIT 3
            ''', (season_id, MIN_RANK_POINTS))
            top_poles = [(row[0], row[1]) for row in await cursor.fetchall()]

            # Top 3 Rachas Global (mínimo rango Plata)
            cursor = await conn.execute('''
                SELECT user_id, MAX(season_best_streak) as best_streak
                FROM season_stats
                WHERE season_id = ?
                GROUP BY user_id
                HAVING SUM(season_points) >= ?
                ORDER BY best_streak DESC
                LIMIT 3
            ''', (season_id, MIN_RANK_POINTS))
            top_streaks = [(row[0], row[1]) for row in await cursor.fetchall()]

            # Top 3 Velocidad Global (mínimo rango Plata + mínimo 10 poles)
            cursor = await conn.execute('''
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
            top_speed = [(row[0], row[1]) for row in await cursor.fetchall()]

        return {
            'points': top_points,
            'poles': top_poles,
            'streaks': top_streaks,
            'speed': top_speed
        }
    
    async def send_opening_notification(
        self,
        guild_id: int,
        channel_id: int,
        ping_role_id: Optional[int],
        ping_mode: str,
        opening_dt: Optional[datetime] = None,
        persist_sent_at: bool = True,
        run_streak_reset: bool = True,
    ):
        """
        Enviar notificación de apertura del pole
        """
        guild = self.bot.get_guild(guild_id)
        if not guild:
            log.warning(f"⚠️ Notificación apertura: guild {guild_id} no disponible en caché")
            return

        await resolve_guild_language(guild_id, self.db)

        channel = await self._resolve_text_channel(guild_id, channel_id)
        if not channel:
            log.warning(f"⚠️ Notificación apertura: canal {channel_id} no resoluble en guild {guild_id}")
            return
        
        now_local = datetime.now(LOCAL_TZ)

        # CROSS-MIDNIGHT PROTECTION: Si la hora de apertura es nocturna y estamos en madrugada,
        # este es un envío tardío de ayer. No resetear rachas (el reset real viene con el nuevo día).
        server_config = await self.db.get_server_config(guild_id)
        daily_time = server_config.get('daily_pole_time') if server_config else None
        skip_reset = False
        opening_reference: Optional[datetime] = _ensure_local_tz(opening_dt) if opening_dt else None
        if daily_time:
            try:
                dh = int(str(daily_time).split(':')[0])
                if dh >= 20 and now_local.hour < 6:
                    skip_reset = True
                    log.info(f"🌙 [Notif] Omitiendo reset cross-midnight para guild {guild_id}")

                if opening_reference is None:
                    h, m, s = [int(x) for x in str(daily_time).split(':')]
                    opening_reference = _opening_time_for_day(now_local, h, m, s)
            except Exception:
                pass

        # Detectar modo recuperación cuando la apertura real debió ocurrir bastante antes.
        recovery_mode = False
        if opening_reference is not None:
            delay_seconds = (now_local - opening_reference).total_seconds()
            recovery_mode = delay_seconds > 120

        if recovery_mode:
            delay_minutes = int(max(0, (now_local - opening_reference).total_seconds()) // 60) if opening_reference else 0
            log.warning(
                "⚠️ [Notif Recovery] guild=%s opening=%s now=%s delay=%smin",
                guild_id,
                opening_reference.isoformat() if opening_reference else "unknown",
                now_local.isoformat(),
                delay_minutes,
            )
        
        # Antes de abrir: resetear rachas que realmente se perdieron (no hicieron ni pole ayer ni marranero hoy)
        # Usar try-except para evitar que un fallo aquí bloquee la notificación
        if run_streak_reset and not skip_reset:
            try:
                await asyncio.wait_for(
                    self._reset_lost_streaks_before_opening(guild_id, channel_id),
                    timeout=30.0  # Máximo 30 segundos para esta operación
                )
            except asyncio.TimeoutError:
                log.warning(f"⚠️ Timeout reseteando rachas en guild {guild_id} - continuando con notificación")
            except Exception as e:
                log.error(f"⚠️ Error reseteando rachas antes de apertura en guild {guild_id}: {e}")
        elif not run_streak_reset:
            log.info(f"🧪 Notificación apertura en modo test: sin reset de rachas para guild {guild_id}")

        # Construir mensaje con ping opcional
        content = ""
        if ping_mode == 'role' and ping_role_id:
            role = guild.get_role(ping_role_id)
            if role:
                content = f"{role.mention} "
        elif ping_mode == 'everyone':
            content = "@everyone "

        title_key = 'notification.pole_open_recovery' if recovery_mode else 'notification.pole_open'
        desc_key = 'notification.pole_open_recovery_desc' if recovery_mode else 'notification.pole_open_desc'
        mode_key = 'notification.field.mode_recovery' if recovery_mode else 'notification.field.mode_normal'

        embed = discord.Embed(
            title=t(title_key, guild_id),
            description=t(desc_key, guild_id),
            color=discord.Color.orange() if recovery_mode else discord.Color.green(),
            timestamp=now_local
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.add_field(
            name=t('notification.field.command', guild_id),
            value=t('notification.field.command_value', guild_id, command='pole'),
            inline=True
        )
        embed.add_field(
            name=t('notification.field.mode', guild_id),
            value=t(mode_key, guild_id),
            inline=True
        )
        if opening_reference is not None:
            embed.add_field(
                name=t('notification.field.opened_at', guild_id),
                value=opening_reference.strftime('%H:%M:%S'),
                inline=True
            )

        if recovery_mode and opening_reference is not None:
            embed.set_footer(text=t('notification.recovery_footer', guild_id, time=opening_reference.strftime('%H:%M:%S')))
        else:
            embed.set_footer(text=t('notification.pole_open_footer', guild_id))
        
        try:
            await channel.send(content=content if content else None, embed=embed)
            # IMPORTANTE: Guardar timestamp de cuando realmente se envió la notificación
            # Esto se usará para calcular delays justos (por si llegó tarde por lag)
            if persist_sent_at:
                await self.db.set_notification_sent_at(guild_id, now_local.isoformat())
            else:
                log.info(f"🧪 Notificación apertura en modo test: sin persistir notification_sent_at para guild {guild_id}")
            mode = "RECOVERY" if recovery_mode else "NORMAL"
            if persist_sent_at:
                log.info(f"🔔 Notificación {mode} enviada y timestamp guardado para guild {guild_id}")
            else:
                log.info(f"🔔 Notificación {mode} enviada en modo test para guild {guild_id}")
        except Exception as e:
            log.error(f"❌ Error enviando notificación a guild {guild_id}: {e}")

    async def _reset_lost_streaks_before_opening(self, guild_id: int, channel_id: int):
        """Resetear rachas perdidas justo antes de la apertura de hoy y avisar al canal.

        Regla: pierden racha quienes no hicieron pole ayer, ni marranero hoy,
        ni ya polearon hoy (protección contra resets múltiples por día).
        
        IMPORTANTE: Esta función se ejecuta cada vez que un servidor envía notificación.
        La protección did_pole_today evita que usuarios que ya polearon hoy pierdan su racha
        si otro servidor envía notificación después.
        """
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return

        channel = await self._resolve_text_channel(guild_id, channel_id)
        if channel is None:
            log.warning(
                f"⚠️ Reset rachas: canal {channel_id} no resoluble en guild {guild_id}; se ejecuta reset sin aviso público"
            )

        yesterday = (datetime.now(LOCAL_TZ) - timedelta(days=1)).strftime('%Y-%m-%d')
        today = datetime.now(LOCAL_TZ).strftime('%Y-%m-%d')

        # Usuarios que hicieron pole ayer EN CUALQUIER SERVIDOR (racha es global)
        async with self.db.get_connection() as conn:
            cursor = await conn.execute('''
                SELECT DISTINCT user_id
                FROM poles
                WHERE pole_date = ?
            ''', (yesterday,))
            did_pole_yesterday_global = {row[0] for row in await cursor.fetchall()}

            # Usuarios que hicieron marranero HOY EN CUALQUIER SERVIDOR (recuperaron el día de ayer)
            cursor = await conn.execute('''
                SELECT DISTINCT user_id
                FROM poles
                WHERE pole_date = ? AND pole_type = 'marranero'
            ''', (yesterday,))
            did_marranero_today = {row[0] for row in await cursor.fetchall()}

            # PROTECCIÓN CRÍTICA: Usuarios que ya polearon HOY (cualquier tipo, cualquier servidor)
            # Esto evita que un reset tardío (ej: notificación de otro servidor a las 14:00)
            # borre la racha de alguien que ya poleó exitosamente hoy
            cursor = await conn.execute('''
                SELECT DISTINCT user_id
                FROM poles
                WHERE pole_date = ?
            ''', (today,))
            did_pole_today = {row[0] for row in await cursor.fetchall()}

        protected_users = did_pole_yesterday_global.union(did_marranero_today).union(did_pole_today)

        # Obtener todos los usuarios con rachas GLOBALES activas
        async with self.db.get_connection() as conn:
            cursor = await conn.execute('''
                SELECT user_id, username, current_streak
                FROM global_users
                WHERE current_streak > 0
            ''')
            global_users_with_streaks = await cursor.fetchall()

        lost_members = []
        for gu in global_users_with_streaks:
            if gu['user_id'] not in protected_users:
                # Resetear racha GLOBAL
                await self.db.update_global_user(gu['user_id'], current_streak=0)
                
                # Solo notificar si el usuario está en ESTE servidor
                member = guild.get_member(gu['user_id'])
                if member:
                    lost_members.append(member)

        if lost_members and channel:
            names_text = ", ".join(m.mention for m in lost_members[:10])
            more = len(lost_members) - 10
            if more > 0:
                names_text += f" y {more} más"
            try:
                await channel.send(
                    content=None,
                    embed=discord.Embed(
                        title=t('notification.streak_lost', guild_id),
                        description=t('notification.streak_lost_desc', guild_id, names=names_text),
                        color=discord.Color.red(),
                        timestamp=datetime.now(LOCAL_TZ)
                    )
                )
            except Exception as e:
                log.error(f"⚠️ Error avisando racha perdida en guild {guild_id}: {e}")
        elif lost_members:
            log.info(
                f"ℹ️ Reset rachas aplicado en guild {guild_id} para {len(lost_members)} miembro(s) sin aviso de canal"
            )

    # ==================== RESUMEN DE MEDIANOCHE ====================
    
    async def send_midnight_summary(self, guild_id: int, channel_id: int, summary_date: Optional[str] = None):
        """Enviar resumen diario para la fecha lógica indicada (YYYY-MM-DD)."""
        guild = self.bot.get_guild(guild_id)
        if not guild:
            log.warning(f"⚠️ Resumen medianoche: guild {guild_id} no disponible en caché")
            return

        await resolve_guild_language(guild_id, self.db)

        channel = await self._resolve_text_channel(guild_id, channel_id)
        if not channel:
            log.warning(f"⚠️ Resumen medianoche: canal {channel_id} no resoluble en guild {guild_id}")
            return
        
        # Obtener poles del día a resumir (por defecto: ayer en horario local)
        if summary_date:
            yesterday_date = summary_date
        else:
            yesterday = datetime.now(LOCAL_TZ) - timedelta(days=1)
            yesterday_date = yesterday.strftime('%Y-%m-%d')
        async with self.db.get_connection() as conn:
            cursor = await conn.execute('''
                SELECT
                    user_id,
                    MIN(pole_type) as pole_type,
                    SUM(points_earned) as points_earned,
                    MIN(created_at) as created_at
                FROM poles
                WHERE guild_id = ? AND (pole_date = ? OR (pole_date = ? AND pole_type = 'marranero'))
                GROUP BY user_id
                ORDER BY created_at ASC
            ''', (guild_id, yesterday_date, yesterday_date))
            yesterday_poles = [dict(row) for row in await cursor.fetchall()]
        
        if not yesterday_poles:
            # No enviar si nadie hizo pole ayer
            return
        
        # Usuarios con racha activa que NO hicieron pole ayer
        # Obtener todos los user_ids del servidor
        all_users = await self.db.get_leaderboard(guild_id, 1000)
        users_streak_at_risk = []  # No hicieron pole en ningún servidor (racha en peligro)
        users_pole_elsewhere = []  # Hicieron pole en otro servidor (racha salvada)
        user_ids_with_pole = {p['user_id'] for p in yesterday_poles}

        for user_data in all_users:
            # Obtener racha GLOBAL del usuario
            global_user = await self.db.get_global_user(user_data['user_id'])
            if not global_user:
                continue
            
            current_streak = int(global_user.get('current_streak', 0))
            if current_streak > 0 and user_data['user_id'] not in user_ids_with_pole:
                member = guild.get_member(user_data['user_id'])
                if member:
                    # Verificar si hizo pole en OTRO servidor
                    global_pole = await self.db.get_user_pole_on_date_global(user_data['user_id'], yesterday_date)
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
        at_risk_count = len(users_streak_at_risk)
        elsewhere_count = len(users_pole_elsewhere)
        embed = discord.Embed(
            title=t('notification.daily_summary', guild_id),
            description=t('notification.daily_summary_desc', guild_id, count=len(yesterday_poles)),
            color=discord.Color.red() if at_risk_count > 0 else discord.Color.dark_blue(),
            timestamp=datetime.now(LOCAL_TZ)
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        embed.add_field(
            name=t('summary.field.completed_count', guild.id),
            value=f"**{len(yesterday_poles)}**",
            inline=True
        )
        embed.add_field(
            name=t('summary.field.risk_count', guild.id),
            value=f"**{at_risk_count}**",
            inline=True
        )
        embed.add_field(
            name=t('summary.field.elsewhere_count', guild.id),
            value=f"**{elsewhere_count}**",
            inline=True
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
                    name=t('summary.completed_yesterday', guild.id),
                    value=pole_list,
                    inline=False
                )
        
        # Advertencia: racha en peligro (marranero disponible hasta la nueva apertura)
        if users_streak_at_risk:
            streak_users = ""
            for user_info in users_streak_at_risk[:5]:
                streak_users += t('summary.user_streak', guild.id, mention=user_info['member'].mention, streak=user_info['streak']) + "\n"
            if len(users_streak_at_risk) > 5:
                streak_users += "\n" + t('summary.and_more', guild.id, count=len(users_streak_at_risk) - 5)
            
            streak_warning = t('summary.streak_at_risk_desc', guild.id, count=len(users_streak_at_risk), users=streak_users)

            embed.add_field(
                name=t('summary.streak_at_risk', guild.id),
                value=streak_warning,
                inline=False
            )
        
        # Info: usuarios que hicieron pole en otro servidor
        if users_pole_elsewhere:
            elsewhere_info = ""
            for user_info in users_pole_elsewhere[:10]:
                elsewhere_info += t('summary.user_elsewhere', guild.id, mention=user_info['member'].mention, guild=user_info['other_guild'], streak=user_info['streak']) + "\n"
            if len(users_pole_elsewhere) > 10:
                elsewhere_info += "\n" + t('summary.and_more', guild.id, count=len(users_pole_elsewhere) - 10)

            embed.add_field(
                name=t('summary.pole_elsewhere', guild.id, count=len(users_pole_elsewhere)),
                value=elsewhere_info,
                inline=False
            )
        
        # Info del nuevo día
        embed.add_field(
            name=t('summary.new_day', guild.id),
            value=t('summary.new_day_desc', guild.id),
            inline=True
        )
        
        embed.set_footer(text=t('summary.footer', guild.id))
        
        try:
            await channel.send(embed=embed)
        except Exception as e:
            log.error(f"❌ Error enviando resumen de medianoche a guild {guild_id}: {e}")

# Setup function necesaria para cargar el cog
async def setup(bot):
    await bot.add_cog(PoleCog(bot))
