"""
Pole Bot - Bot de Discord para hacer Pole diario
"""
import discord
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
import asyncio
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from utils.database import Database

# Cargar variables de entorno
load_dotenv()

# ==================== CONFIGURACIÓN DE LOGGING ====================
def setup_logging():
    """Configurar sistema de logging con archivo rotativo y consola"""
    # Crear logger root
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG if os.getenv('DEBUG', '0') in ('1', 'true', 'True') else logging.INFO)
    
    # Formato personalizado con emojis
    class EmojiFormatter(logging.Formatter):
        """Formatter que añade emojis según el nivel de log"""
        EMOJI_MAP = {
            'DEBUG': '🔍',
            'INFO': 'ℹ️ ',
            'WARNING': '⚠️ ',
            'ERROR': '❌',
            'CRITICAL': '🔥'
        }
        
        def format(self, record):
            emoji = self.EMOJI_MAP.get(record.levelname, '  ')
            record.emoji = emoji
            return super().format(record)
    
    # Formato: [2026-02-15 14:30:45] [INFO] ℹ️  mensaje
    log_format = '[%(asctime)s] [%(levelname)-8s] %(emoji)s %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'
    formatter = EmojiFormatter(log_format, datefmt=date_format)
    
    # Handler para archivo con rotación (max 10MB, 5 backups)
    os.makedirs('logs', exist_ok=True)
    file_handler = RotatingFileHandler(
        'bot.log',
        maxBytes=10*1024*1024,  # 10 MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Handler para consola (solo INFO y superior)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Añadir handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    # Reducir verbosidad de discord.py (solo warnings y errores)
    logging.getLogger('discord').setLevel(logging.WARNING)
    logging.getLogger('discord.http').setLevel(logging.WARNING)
    logging.getLogger('discord.gateway').setLevel(logging.INFO)  # Útil para debug de conexión
    
    return logger

# Configurar logging al iniciar
log = setup_logging()
log.info("=" * 60)
log.info("POLE BOT INICIANDO")
log.info("=" * 60)

class PoleBot(commands.Bot):
    def __init__(self):
        # Configurar intents (permisos que necesita el bot)
        intents = discord.Intents.default()
        intents.message_content = True  # Para leer mensajes
        intents.guilds = True           # Para detectar nuevos canales/hilos
        intents.members = True          # Para trackear miembros (opcional)
        
        super().__init__(
            command_prefix='!',  # Prefijo para comandos (ej: !pole, !stats)
            intents=intents,
            help_command=None    # Desactivar comando de ayuda por defecto
        )
        
        # Logger
        self.log = logging.getLogger('PoleBot')
        
        # Se inicializa en setup_hook con await db.initialize()
        self._db: Optional["Database"] = None
        self._commands_synced = False
        self._commands_sync_count = 0
        self._debug_guild_commands_synced = False

    @staticmethod
    def _is_debug_enabled() -> bool:
        return os.getenv('DEBUG', '0') in ('1', 'true', 'True')

    @staticmethod
    def _is_debug_global_sync_enabled() -> bool:
        return os.getenv('DEBUG_SYNC_GLOBAL', '0') in ('1', 'true', 'True')

    def _parse_test_guild_ids(self) -> list[int]:
        raw_ids = os.getenv('TEST_GUILD_ID', '').strip()
        if not raw_ids:
            return []

        parsed_ids: list[int] = []
        for chunk in raw_ids.split(','):
            value = chunk.strip()
            if not value:
                continue
            try:
                parsed_ids.append(int(value))
            except ValueError:
                self.log.warning(f"TEST_GUILD_ID inválido ignorado: {value}")

        return parsed_ids

    async def _sync_debug_guild_commands(self) -> None:
        """Sincronizar comandos en guild(s) para reflejo inmediato durante DEBUG."""
        if self._debug_guild_commands_synced:
            return

        if not self._is_debug_enabled():
            return

        target_guild_ids = self._parse_test_guild_ids()
        if not target_guild_ids:
            target_guild_ids = [guild.id for guild in self.guilds]
            if target_guild_ids:
                self.log.warning(
                    "DEBUG=1 sin TEST_GUILD_ID: usando guild sync en guilds conectadas (%s)",
                    ", ".join(str(gid) for gid in target_guild_ids),
                )

        if not target_guild_ids:
            self.log.warning(
                "DEBUG=1 pero no hay TEST_GUILD_ID ni guilds conectadas para guild sync inmediato"
            )
            return

        successful_syncs = 0
        for guild_id in target_guild_ids:
            try:
                guild_obj = discord.Object(id=guild_id)
                self.tree.copy_global_to(guild=guild_obj)
                synced = await self.tree.sync(guild=guild_obj)
                synced_names = ", ".join(sorted(command.name for command in synced))
                self.log.info(
                    f"{len(synced)} comandos slash sincronizados en guild {guild_id}: {synced_names}"
                )
                successful_syncs += 1
            except Exception as e:
                self.log.error(
                    f"Error sincronizando comandos en guild {guild_id}: {e}",
                    exc_info=True,
                )

        if successful_syncs > 0:
            self._debug_guild_commands_synced = True

    async def _sync_app_commands(self) -> None:
        """Sincronizar comandos slash (global en producción, guild test opcional en DEBUG)."""
        if self._commands_synced:
            return

        command_names = ", ".join(
            sorted(command.qualified_name for command in self.tree.get_commands())
        )
        if command_names:
            self.log.info(f"Comandos registrados en árbol antes de sync: {command_names}")

        # En DEBUG, intentar también guild sync para disponibilidad inmediata.
        await self._sync_debug_guild_commands()

        # En DEBUG usamos por defecto solo sync de guild para evitar comandos duplicados en cliente.
        if self._is_debug_enabled() and not self._is_debug_global_sync_enabled():
            if self._debug_guild_commands_synced:
                self._commands_synced = True
                self._commands_sync_count = len(self.tree.get_commands())
                self.log.info(
                    "DEBUG: sync global omitido (DEBUG_SYNC_GLOBAL=0). Usando solo comandos de guild."
                )
            else:
                self.log.warning(
                    "DEBUG: sync global omitido y guild sync no disponible aún; se reintentará en on_ready."
                )
            return

        # Producción: sync GLOBAL.
        try:
            synced = await self.tree.sync()
            self._commands_synced = True
            self._commands_sync_count = len(synced)
            self.log.info(f"{len(synced)} comandos slash sincronizados globalmente")
        except Exception as e:
            self.log.error(f"Error sincronizando comandos slash globales: {e}", exc_info=True)
    
    async def setup_hook(self):
        """Se ejecuta antes de que el bot se conecte a Discord"""
        # Inicializar base de datos de forma async
        from utils.database import Database
        self._db = Database()
        await self._db.initialize()
        self.log.info("Base de datos inicializada correctamente")

        # Cargar todos los cogs (extensiones)
        self.log.info("Cargando extensiones (cogs)...")
        
        # Lista de cogs a cargar
        cogs_to_load = [
            'cogs.pole',
            'cogs.events'
        ]
        # Cargar cog de depuración solo si DEBUG=1
        if os.getenv('DEBUG', '0') in ('1', 'true', 'True'):
            cogs_to_load.append('cogs.debug')
            self.log.info("Modo DEBUG activado - cargando cog de depuración")
        
        for cog in cogs_to_load:
            try:
                await self.load_extension(cog)
                self.log.info(f"Cog cargado: {cog}")
            except Exception as e:
                self.log.error(f"Error cargando {cog}: {e}", exc_info=True)

        # Sincronizar comandos UNA vez durante arranque (global en producción).
        await self._sync_app_commands()
        
        # Iniciar task de actualización de status
        self.update_status_task.start()
        self.log.debug("Task de actualización de status iniciado")
    
    async def on_ready(self):
        """Se ejecuta cuando el bot está listo y conectado"""
        self.log.info("=" * 60)
        if self.user:
            self.log.info(f"Bot conectado como {self.user} (ID: {self.user.id})")
        self.log.info(f"Conectado a {len(self.guilds)} servidor(es)")
        
        # Listar servidores
        for guild in self.guilds:
            self.log.debug(f"  - {guild.name} (ID: {guild.id}, {guild.member_count} miembros)")
        
        # Failsafe: reintentar sync si en setup_hook falló.
        if not self._commands_synced:
            self.log.warning("Comandos slash no sincronizados aún; reintentando en on_ready")
            await self._sync_app_commands()

        # DEBUG: si faltó guild sync en setup_hook (ej. sin TEST_GUILD_ID), hacerlo ahora.
        await self._sync_debug_guild_commands()
        
        self.log.info("Pole Bot está listo y operativo!")
        self.log.info("=" * 60)
        
        # Actualizar status inmediatamente
        await self._update_presence()
    
    async def _update_presence(self):
        """Actualizar el status del bot con el conteo de usuarios activos que han hecho pole"""
        try:
            # Usar instancia compartida en lugar de crear una nueva
            if self._db is None:
                raise RuntimeError("Base de datos no inicializada")

            active_users = await self._db.get_total_active_users()
            self.log.debug(f"Actualizando presencia: {active_users} jugadores activos")
        except Exception as e:
            self.log.warning(f"Error obteniendo usuarios activos para status: {e}")
            active_users = len(self.guilds) * 10  # Fallback: estimación
        
        activity = discord.Activity(
            type=discord.ActivityType.competing,
            name=f"poleando con {active_users} jugadores"
        )
        await self.change_presence(activity=activity, status=discord.Status.online)
    
    @tasks.loop(minutes=10)
    async def update_status_task(self):
        """Actualizar status cada 10 minutos"""
        if self.is_ready():
            await self._update_presence()
    
    @update_status_task.before_loop
    async def before_update_status(self):
        """Esperar a que el bot esté listo antes de actualizar status"""
        await self.wait_until_ready()

# Crear instancia del bot
bot = PoleBot()

# Iniciar el bot
if __name__ == '__main__':
    TOKEN = os.getenv('DISCORD_TOKEN')
    
    if not TOKEN:
        log.critical("No se encontró DISCORD_TOKEN en el archivo .env")
        log.critical("Por favor, crea un archivo .env con tu token de Discord")
        exit(1)
    
    try:
        log.info("Iniciando conexión con Discord...")
        bot.run(TOKEN, log_handler=None)  # Usamos nuestro propio logging
    except discord.LoginFailure:
        log.critical("Error de autenticación: Token inválido")
        exit(1)
    except KeyboardInterrupt:
        log.info("Bot detenido por el usuario (Ctrl+C)")
    except Exception as e:
        log.critical(f"Error fatal al iniciar el bot: {e}", exc_info=True)
        exit(1)
