"""
Cog de Eventos - Maneja eventos de Discord
Como crear nuevos canales o hilos (por si quieres hacer pole automática)
"""
import discord
from discord.ext import commands
import logging
from typing import Optional
from utils.i18n import t

# Logger
log = logging.getLogger('EventsCog')

class EventsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def _pick_welcome_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        """Seleccionar canal para mensaje de bienvenida con verificación de permisos."""
        # Lista de nombres de canales comunes (en orden de prioridad)
        priority_names = ['general', 'chat', 'comandos', 'commands', 'bot', 'bots', 'off-topic', 'offtopic']
        
        # Buscar canales por prioridad
        for priority_name in priority_names:
            for ch in guild.text_channels:
                if priority_name in ch.name.lower():
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
        """Enviar mensaje inicial BILINGÜE explicando pasos de configuración."""
        # Construir descripción bilingüe
        description_es = (
            t('onboarding.intro', guild.id) +
            t('onboarding.language_default', guild.id) +
            t('onboarding.quick_setup', guild.id) +
            t('onboarding.how_it_works', guild.id) +
            t('onboarding.commands', guild.id) +
            t('onboarding.bilingual_notice', guild.id, lang='es')
        )
        
        embed = discord.Embed(
            title=t('onboarding.title', guild.id),
            description=description_es,
            color=discord.Color.gold()
        )
        embed.set_footer(text=t('onboarding.footer', guild.id))
        
        try:
            await channel.send(embed=embed)
            log.info(f"✅ Mensaje de bienvenida bilingüe enviado a {guild.name} (#{channel.name})")
        except discord.Forbidden:
            log.warning(f"⚠️ Sin permisos para enviar mensaje de bienvenida en {guild.name}")
        except Exception as e:
            log.error(f"❌ Error enviando mensaje de bienvenida en {guild.name}: {e}")
    
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
            await channel.send(t('events.first_message_channel', channel.guild.id))
            log.info(f"✅ Pole automática en nuevo canal: {channel.name}")
        except discord.Forbidden:
            log.warning(f"⚠️ Sin permisos para escribir en {channel.name}")
        except Exception as e:
            log.error(f"❌ Error en nuevo canal: {e}")
    
    @commands.Cog.listener()
    async def on_thread_create(self, thread):
        """
        Evento cuando se crea un nuevo hilo en el servidor
        """
        try:
            # Unirse al hilo primero (necesario para poder escribir)
            await thread.join()
            
            # Escribir el primer mensaje
            await thread.send(t('events.first_message_thread', thread.guild.id))
            log.info(f"✅ Pole automática en nuevo hilo: {thread.name}")
        except discord.Forbidden:
            log.warning(f"⚠️ Sin permisos para escribir en el hilo {thread.name}")
        except Exception as e:
            log.error(f"❌ Error en nuevo hilo: {e}")
    
    # @commands.Cog.listener()
    # async def on_member_join(self, member):
    #     """
    #     Evento cuando un nuevo miembro se une al servidor
    #     DESACTIVADO: No se envían mensajes de bienvenida
    #     """
    #     pass

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        """Enviado cuando el bot entra por primera vez a un servidor."""
        log.info(f"🎉 Bot añadido a nuevo servidor: {guild.name} (ID: {guild.id})")
        log.info(f"   Miembros: {guild.member_count} | Canales de texto: {len(guild.text_channels)}")
        
        # Seleccionar canal para mensaje de bienvenida
        ch = self._pick_welcome_channel(guild)
        
        if ch:
            log.info(f"   Canal seleccionado para bienvenida: #{ch.name}")
            await self._send_onboarding_message(ch, guild)
        else:
            log.warning(f"⚠️ No se encontró ningún canal con permisos de escritura en {guild.name}")
            log.info(f"   El bot necesita permisos 'Send Messages' en al menos un canal.")
    
    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        """Enviado cuando el bot es expulsado de un servidor."""
        log.info(f"🗑️ Bot removido del servidor: {guild.name} (ID: {guild.id})")
        log.info(f"   📊 Datos históricos preservados en BD")
    
    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        """Manejo de errores de comandos (traducidos)"""
        if isinstance(error, commands.MissingPermissions):
            await ctx.send(t('events.error.no_permissions', ctx.guild.id if ctx.guild else None))
        elif isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(t('events.error.missing_arg', ctx.guild.id if ctx.guild else None, arg=error.param.name))
        elif isinstance(error, commands.CommandNotFound):
            # Ignorar comandos no encontrados
            pass
        else:
            # Log de otros errores
            log.error(f"❌ Error en comando: {error}")

# Setup function necesaria para cargar el cog
async def setup(bot):
    await bot.add_cog(EventsCog(bot))
