"""
Cog de Pole - Funcionalidad principal del bot
Maneja el sistema de pole diario con reset a las 12h
"""
import discord
from discord.ext import commands, tasks
from datetime import datetime, time
import json
import os
from utils.database import Database

class PoleCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = Database()
        self.config = self._load_config()
        
        # Iniciar tarea de verificación diaria
        self.daily_pole_check.start()
    
    def _load_config(self):
        """Cargar configuración desde config.json"""
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {
                "pole_reset_hour": 12,
                "pole_message": "🏁 ¡POLE! 🏁",
                "penalty_message": "😴 Muy tarde, penalty por dormir..."
            }
    
    def cog_unload(self):
        """Detener tareas cuando se descarga el cog"""
        self.daily_pole_check.cancel()
    
    @tasks.loop(minutes=1)
    async def daily_pole_check(self):
        """
        Tarea que se ejecuta cada minuto para verificar si es hora del pole
        (a las 12:00h se resetea la pole)
        """
        now = datetime.now()
        
        # Verificar si son las 12:00h (o la hora configurada)
        if now.hour == self.config["pole_reset_hour"] and now.minute == 0:
            print(f"🔄 Reset de pole a las {now.hour}:00")
            
            # Aquí podrías enviar un mensaje de aviso si quieres
            # Por ahora solo reseteamos internamente
    
    @daily_pole_check.before_loop
    async def before_daily_check(self):
        """Esperar a que el bot esté listo antes de iniciar la tarea"""
        await self.bot.wait_until_ready()
    
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        """
        Detectar el primer mensaje del día en el canal de pole
        """
        # Ignorar mensajes del propio bot
        if message.author.bot:
            return
        
        # Obtener datos del servidor
        server_data = self.db.get_server_data(message.guild.id)
        pole_channel_id = server_data.get("pole_channel_id")
        
        # Si no hay canal configurado, ignorar
        if not pole_channel_id or message.channel.id != pole_channel_id:
            return
        
        # Verificar si ya hay pole hoy
        last_pole_date = server_data.get("last_pole_date")
        now = datetime.now()
        today_date = now.strftime("%Y-%m-%d")
        
        # Verificar si es después de la hora de reset (12h por defecto)
        reset_hour = self.config["pole_reset_hour"]
        
        if last_pole_date:
            last_pole_datetime = datetime.fromisoformat(last_pole_date)
            last_date = last_pole_datetime.strftime("%Y-%m-%d")
            
            # Si ya hay pole hoy, ignorar
            if last_date == today_date and now.hour >= reset_hour:
                return
            
            # Si es antes de las 12h pero hay pole de ayer, también vale
            if now.hour < reset_hour and last_pole_datetime.hour >= reset_hour:
                return
        
        # ¡Este usuario hizo POLE!
        timestamp = now.isoformat()
        self.db.save_pole_winner(
            message.guild.id,
            message.author.id,
            message.author.name,
            message.channel.id,
            timestamp
        )
        
        # Enviar mensaje de celebración
        pole_msg = self.config["pole_message"]
        embed = discord.Embed(
            title=pole_msg,
            description=f"**{message.author.mention}** ha hecho POLE hoy a las {now.strftime('%H:%M:%S')}!",
            color=discord.Color.gold(),
            timestamp=now
        )
        embed.set_footer(text=f"Reset diario a las {reset_hour}:00h")
        
        await message.channel.send(embed=embed)
    
    @commands.command(name='setpolechannel')
    @commands.has_permissions(administrator=True)
    async def set_pole_channel(self, ctx):
        """
        Establecer el canal actual como canal de pole (solo administradores)
        Uso: !setpolechannel
        """
        self.db.set_pole_channel(ctx.guild.id, ctx.channel.id)
        
        embed = discord.Embed(
            title="✅ Canal de Pole Configurado",
            description=f"Este canal ({ctx.channel.mention}) ahora es el canal oficial de pole!",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    
    @commands.command(name='polestats', aliases=['stats'])
    async def pole_stats(self, ctx):
        """
        Mostrar estadísticas de poles del servidor
        Uso: !polestats
        """
        stats = self.db.get_pole_stats(ctx.guild.id)
        
        embed = discord.Embed(
            title="📊 Estadísticas de Pole",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="Total de Poles",
            value=stats["total_poles"],
            inline=True
        )
        
        embed.add_field(
            name="Total de Penalties",
            value=stats["total_penalties"],
            inline=True
        )
        
        # Top 10 polers
        if stats["top_polers"]:
            top_text = ""
            for i, (user_id, data) in enumerate(stats["top_polers"], 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                top_text += f"{medal} **{data['username']}** - {data['count']} poles\n"
            
            embed.add_field(
                name="🏆 Top Polers",
                value=top_text,
                inline=False
            )
        
        # Último ganador
        if stats["last_winner"]:
            last = stats["last_winner"]
            last_time = datetime.fromisoformat(last["timestamp"])
            embed.add_field(
                name="🎯 Última Pole",
                value=f"**{last['username']}** - {last_time.strftime('%d/%m/%Y %H:%M:%S')}",
                inline=False
            )
        
        await ctx.send(embed=embed)
    
    @commands.command(name='penalty')
    @commands.has_permissions(administrator=True)
    async def add_penalty(self, ctx, member: discord.Member, *, reason: str = "Ninguna razón especificada"):
        """
        Agregar una penalty a un usuario (solo administradores)
        Uso: !penalty @usuario razón
        """
        timestamp = datetime.now().isoformat()
        self.db.add_penalty(
            ctx.guild.id,
            member.id,
            member.name,
            reason,
            timestamp
        )
        
        embed = discord.Embed(
            title="⚠️ Penalty Aplicada",
            description=f"**{member.mention}** ha recibido una penalty",
            color=discord.Color.red()
        )
        embed.add_field(name="Razón", value=reason)
        
        await ctx.send(embed=embed)
    
    @commands.command(name='polehelp')
    async def pole_help(self, ctx):
        """
        Mostrar ayuda sobre el bot de pole
        Uso: !polehelp
        """
        embed = discord.Embed(
            title="🏁 Ayuda de Pole Bot",
            description="Bot para hacer pole diario en Discord",
            color=discord.Color.purple()
        )
        
        embed.add_field(
            name="¿Cómo funciona?",
            value=f"Escribe el primer mensaje en el canal de pole después de las {self.config['pole_reset_hour']}:00h cada día para ganar!",
            inline=False
        )
        
        embed.add_field(
            name="📝 Comandos Usuarios",
            value="`!polestats` - Ver estadísticas\n`!polehelp` - Ver esta ayuda",
            inline=False
        )
        
        embed.add_field(
            name="⚙️ Comandos Administradores",
            value="`!setpolechannel` - Configurar canal de pole\n`!penalty @usuario razón` - Dar penalty",
            inline=False
        )
        
        await ctx.send(embed=embed)

# Setup function necesaria para cargar el cog
async def setup(bot):
    await bot.add_cog(PoleCog(bot))
