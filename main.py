"""
Pole Bot - Bot de Discord para hacer Pole diario
"""
import discord
from discord.ext import commands
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
    
    async def setup_hook(self):
        """Se ejecuta antes de que el bot se conecte a Discord"""
        # Cargar todos los cogs (extensiones)
        print("🔄 Cargando cogs...")
        
        # Lista de cogs a cargar
        cogs_to_load = [
            'cogs.pole',
            'cogs.events'
        ]
        
        for cog in cogs_to_load:
            try:
                await self.load_extension(cog)
                print(f"✅ Cog cargado: {cog}")
            except Exception as e:
                print(f"❌ Error cargando {cog}: {e}")
    
    async def on_ready(self):
        """Se ejecuta cuando el bot está listo y conectado"""
        print(f'🤖 Bot conectado como {self.user}')
        print(f'📊 Conectado a {len(self.guilds)} servidor(es)')
        print('✨ Pole Bot está listo!')
        
        # Sincronizar comandos slash (opcional, para comandos modernos)
        # await self.tree.sync()

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
