"""
Cog de Eventos - Maneja eventos de Discord
Como crear nuevos canales o hilos (por si quieres hacer pole automática)
"""
import discord
from discord.ext import commands
from typing import Optional

class EventsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _pick_welcome_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        """Seleccionar canal para mensaje de bienvenida con verificación de permisos."""
        # Prioriza canales cuyo nombre contiene 'general'
        for ch in guild.text_channels:
            if 'general' in ch.name.lower():
                # Verificar permisos de escritura
                if ch.permissions_for(guild.me).send_messages:
                    return ch
        
        # Fallback: buscar primer canal donde podamos escribir
        for ch in guild.text_channels:
            if ch.permissions_for(guild.me).send_messages:
                return ch
        
        # Si no hay canales con permisos, devolver None
        return None

    async def _send_onboarding_message(self, channel: discord.TextChannel, guild: discord.Guild):
        """Enviar mensaje inicial explicando pasos de configuración."""
        embed = discord.Embed(
            title="🏁 ¡Gracias por invitarme!",
            description=(
                "Soy **Pole Bot**, tu asistente para competir por ser el más rápido cada día.\n\n"
                "**Configuración rápida (2 pasos):**\n"
                "1️⃣ Usa `/settings set_channel` para elegir el canal de pole\n"
                "2️⃣ (Opcional) Configura notificaciones y rol con `/settings`\n\n"
                "**¿Cómo funciona?**\n"
                "• Cada día se abre el pole a una hora aleatoria\n"
                "• El primero en escribir `pole` gana puntos\n"
                "• Mantén rachas consecutivas para multiplicadores\n"
                "• Compite localmente y globalmente\n\n"
                "Usa `/rules` para ver las reglas completas. ¡Suerte! 🏁"
            ),
            color=discord.Color.gold()
        )
        embed.add_field(
            name="⚙️ Comandos Útiles",
            value=(
                "`/settings` - Configurar el bot\n"
                "`/rules` - Ver reglas del juego\n"
                "`/profile` - Tu perfil de pole\n"
                "`/leaderboard` - Rankings del servidor"
            ),
            inline=False
        )
        embed.set_footer(text="¡Que gane el más rápido! 🔥")
        
        try:
            await channel.send(embed=embed)
            print(f"✅ Mensaje de bienvenida enviado a {guild.name} (#{channel.name})")
        except discord.Forbidden:
            print(f"⚠️ Sin permisos para enviar mensaje de bienvenida en {guild.name}")
        except Exception as e:
            print(f"❌ Error enviando mensaje de bienvenida en {guild.name}: {e}")
    
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
    async def on_guild_join(self, guild: discord.Guild):
        """Enviado cuando el bot entra por primera vez a un servidor."""
        print(f"🎉 Bot añadido a nuevo servidor: {guild.name} (ID: {guild.id})")
        print(f"   Miembros: {guild.member_count} | Canales de texto: {len(guild.text_channels)}")
        
        # Seleccionar canal para mensaje de bienvenida
        ch = self._pick_welcome_channel(guild)
        
        if ch:
            print(f"   Canal seleccionado para bienvenida: #{ch.name}")
            await self._send_onboarding_message(ch, guild)
        else:
            print(f"⚠️ No se encontró ningún canal con permisos de escritura en {guild.name}")
            print(f"   El bot necesita permisos 'Send Messages' en al menos un canal.")
    
    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        """Enviado cuando el bot es expulsado de un servidor."""
        print(f"🗑️ Bot removido del servidor: {guild.name} (ID: {guild.id})")
        print(f"   📊 Datos históricos preservados en BD")
    
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
