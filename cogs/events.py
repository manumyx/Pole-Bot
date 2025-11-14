"""
Cog de Eventos - Maneja eventos de Discord
Como crear nuevos canales o hilos (por si quieres hacer pole automática)
"""
import discord
from discord.ext import commands

class EventsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_guild_channel_create(self, channel):
        """
        Evento cuando se crea un nuevo canal en el servidor
        Puedes hacer que el bot escriba el primer mensaje automáticamente
        """
        # Solo responder en canales de texto
        if not isinstance(channel, discord.TextChannel):
            return
        
        try:
            # Esperar un momento para que el canal esté completamente creado
            await channel.send("🏁 ¡POLE! Primer mensaje en este canal! 🏁")
            print(f"✅ Pole automática en nuevo canal: {channel.name}")
        except discord.Forbidden:
            print(f"⚠️ Sin permisos para escribir en {channel.name}")
        except Exception as e:
            print(f"❌ Error en nuevo canal: {e}")
    
    @commands.Cog.listener()
    async def on_thread_create(self, thread):
        """
        Evento cuando se crea un nuevo hilo en el servidor
        """
        try:
            # Unirse al hilo primero (necesario para poder escribir)
            await thread.join()
            
            # Escribir el primer mensaje
            await thread.send("🏁 ¡POLE! Primer mensaje en este hilo! 🏁")
            print(f"✅ Pole automática en nuevo hilo: {thread.name}")
        except discord.Forbidden:
            print(f"⚠️ Sin permisos para escribir en el hilo {thread.name}")
        except Exception as e:
            print(f"❌ Error en nuevo hilo: {e}")
    
    @commands.Cog.listener()
    async def on_member_join(self, member):
        """
        Evento cuando un nuevo miembro se une al servidor
        Puedes enviar un mensaje de bienvenida
        """
        # Buscar un canal de bienvenida o general
        # Este es solo un ejemplo, puedes personalizarlo
        
        # Intenta encontrar un canal llamado "general" o "bienvenida"
        welcome_channel = None
        for channel in member.guild.text_channels:
            if channel.name.lower() in ['general', 'bienvenida', 'welcome']:
                welcome_channel = channel
                break
        
        if welcome_channel:
            try:
                embed = discord.Embed(
                    title="👋 ¡Bienvenido!",
                    description=f"Dale la bienvenida a {member.mention}!",
                    color=discord.Color.green()
                )
                embed.set_thumbnail(url=member.display_avatar.url)
                await welcome_channel.send(embed=embed)
            except:
                pass  # Si hay error, simplemente ignorar
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """
        Manejo de errores de comandos
        """
        if isinstance(error, commands.MissingPermissions):
            await ctx.send("❌ No tienes permisos para usar este comando.")
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"❌ Falta un argumento: {error.param.name}")
        elif isinstance(error, commands.CommandNotFound):
            # Ignorar comandos no encontrados
            pass
        else:
            # Log de otros errores
            print(f"❌ Error en comando: {error}")

# Setup function necesaria para cargar el cog
async def setup(bot):
    await bot.add_cog(EventsCog(bot))
