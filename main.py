"""
Pole Bot - Bot de Discord para hacer Pole diario
"""
import discord
from discord.ext import commands, tasks
import os
from dotenv import load_dotenv
import asyncio

# Cargar variables de entorno
load_dotenv()

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
        
        # Instancia única de Database para todo el bot
        from utils.database import Database
        self._db = Database()
        print("✅ Base de datos inicializada")
    
    async def setup_hook(self):
        """Se ejecuta antes de que el bot se conecte a Discord"""
        # Cargar todos los cogs (extensiones)
        print("🔄 Cargando cogs...")
        
        # Lista de cogs a cargar
        cogs_to_load = [
            'cogs.pole',
            'cogs.events'
        ]
        # Cargar cog de depuración solo si DEBUG=1
        if os.getenv('DEBUG', '0') in ('1', 'true', 'True'):
            cogs_to_load.append('cogs.debug')
        
        for cog in cogs_to_load:
            try:
                await self.load_extension(cog)
                print(f"✅ Cog cargado: {cog}")
            except Exception as e:
                print(f"❌ Error cargando {cog}: {e}")
        
        # Iniciar task de actualización de status
        self.update_status_task.start()
    
    async def on_ready(self):
        """Se ejecuta cuando el bot está listo y conectado"""
        print(f'🤖 Bot conectado como {self.user}')
        print(f'📊 Conectado a {len(self.guilds)} servidor(es)')
        
        # Sincronizar comandos slash
        try:
            synced = await self.tree.sync()
            print(f'✅ {len(synced)} comandos slash sincronizados')
        except Exception as e:
            print(f'❌ Error sincronizando comandos: {e}')
        
        print('✨ Pole Bot está listo!')
        
        # Actualizar status inmediatamente
        await self._update_presence()
    
    async def _update_presence(self):
        """Actualizar el status del bot con el conteo de usuarios activos que han hecho pole"""
        # Usar instancia compartida en lugar de crear una nueva
        active_users = self._db.get_total_active_users()
        
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
        print("❌ ERROR: No se encontró DISCORD_TOKEN en el archivo .env")
        print("Por favor, crea un archivo .env con tu token de Discord")
        exit(1)
    
    try:
        bot.run(TOKEN)
    except discord.LoginFailure:
        print("❌ ERROR: Token de Discord inválido")
    except Exception as e:
        print(f"❌ ERROR: {e}")
