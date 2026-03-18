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
        
        # Instancia única de Database para todo el bot
        from utils.database import Database
        self._db = Database()
        self.log.info("Base de datos inicializada correctamente")
    
    async def setup_hook(self):
        """Se ejecuta antes de que el bot se conecte a Discord"""
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
        
        # Sincronizar comandos slash
        try:
            synced = await self.tree.sync()
            self.log.info(f"{len(synced)} comandos slash sincronizados exitosamente")
        except Exception as e:
            self.log.error(f"Error sincronizando comandos slash: {e}", exc_info=True)
        
        self.log.info("Pole Bot está listo y operativo!")
        self.log.info("=" * 60)
        
        # Actualizar status inmediatamente
        await self._update_presence()
    
    async def _update_presence(self):
        """Actualizar el status del bot con el conteo de usuarios activos que han hecho pole"""
        try:
            # Usar instancia compartida en lugar de crear una nueva
            active_users = self._db.get_total_active_users()
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
