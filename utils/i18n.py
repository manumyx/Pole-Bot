"""
Sistema de Internacionalización (i18n) para Pole Bot
Soporta español (es) e inglés (en)
"""
import random
from typing import Optional, Dict, Any, Union, List

# ==================== DICCIONARIO DE TRADUCCIONES ====================

TRANSLATIONS: Dict[str, Dict[str, Union[str, List[str]]]] = {
    'es': {
        # ==================== COMMANDS ====================
        'cmd.settings.desc': 'Configurar opciones del Pole Bot (vista según permisos)',
        'cmd.profile.desc': 'Ver estadísticas de un usuario',
        'cmd.profile.user_param': 'Usuario del que ver perfil (opcional)',
        'cmd.profile.scope_param': 'Alcance: global (todos los servidores) o local (solo este servidor)',
        'cmd.leaderboard.desc': 'Ver ranking de jugadores o servidores',
        'cmd.leaderboard.scope_param': 'Alcance del ranking',
        'cmd.leaderboard.type_param': 'Tipo de ranking',
        'cmd.leaderboard.limit_param': 'Número de resultados',
        'cmd.leaderboard.season_param': 'Temporada específica (opcional)',
        'cmd.history.desc': 'Ver historial de tus últimos poles',
        'cmd.history.limit_param': 'Número de poles a mostrar (máx 20)',
        'cmd.streak.desc': 'Ver información detallada de tu racha',
        'cmd.season.desc': 'Ver información de la temporada actual y tu progreso',
        'cmd.polehelp.desc': 'Ver información sobre cómo funciona el bot',
        'cmd.mystats.desc': 'Ver tu historial de temporadas y colección de badges',
        
        # Describe params
        'cmd.leaderboard.scope_describe': 'Alcance del ranking: local (este servidor) o global (todos los servidores)',
        'cmd.leaderboard.type_describe': 'Tipo de ranking: personas, servidores o rachas',
        'cmd.leaderboard.season_describe': 'Temporada a mostrar (Lifetime por defecto)',
        'cmd.leaderboard.limit_describe': 'Cantidad de entradas a mostrar (por defecto 10)',
        
        # Choices de comandos
        'choice.scope.global': 'Global (todos los servidores)',
        'choice.scope.local': 'Local (solo este servidor)',
        'choice.type.people': 'Personas',
        'choice.type.servers': 'Servidores',
        'choice.type.streaks': 'Rachas',
        'choice.season.lifetime': 'Lifetime (todas las temporadas)',
        
        # Choices de leaderboard (cortos)
        'choice.local': 'Local',
        'choice.global': 'Global',
        'choice.personas': 'Personas',
        'choice.servidores': 'Servidores',
        'choice.rachas': 'Rachas',
        
        # ==================== SETTINGS ====================
        'settings.title': '⚙️ Configuración del Pole Bot',
        'settings.admin_view': 'Vista de administrador',
        'settings.user_view': 'Vista de usuario',
        'settings.channel': '📺 Canal',
        'settings.channel_not_set': 'No configurado',
        'settings.notifications': '🔔 Notificaciones',
        'settings.notify_opening': 'Apertura de pole',
        'settings.notify_winner': 'Ganador del pole',
        'settings.ping_mode': 'Modo de ping',
        'settings.ping_role': 'Rol de ping',
        'settings.pole_hours': '⏰ Horario del Pole',
        'settings.pole_hours_desc': 'De {start}:00 a {end}:00',
        'settings.today_time': '🎲 Hora de Hoy',
        'settings.today_time_desc': 'Se abre a las {time}',
        'settings.today_time_pending': 'Generando...',
        'settings.language': '🌐 Idioma',
        'settings.language_current': 'Español',
        'settings.represent_server': '🏳️ Servidor que Representas',
        'settings.represent_server_desc': '{server}',
        'settings.represent_server_none': 'Ninguno (elige uno para rankings globales)',
        
        # Botones de settings
        'settings.btn.change_channel': '📺 Cambiar Canal',
        'settings.btn.toggle_opening': '🔔 Notif. Apertura',
        'settings.btn.toggle_winner': '🏆 Notif. Ganador',
        'settings.btn.change_role': '👥 Cambiar Rol',
        'settings.btn.ping_everyone': '📢 Pingear @everyone',
        'settings.btn.ping_here': '📍 Pingear @here',
        'settings.btn.ping_role': '👤 Pingear Rol',
        'settings.btn.no_ping': '🔕 Sin Ping',
        'settings.btn.change_hours': '⏰ Cambiar Horario',
        'settings.btn.change_language': '🌐 Cambiar Idioma',
        'settings.btn.change_represent': '🏳️ Cambiar Servidor',
        'settings.btn.refresh': '🔄 Refrescar',
        
        # Mensajes de settings
        'settings.channel_set': '✅ Canal de pole configurado: {channel}',
        'settings.role_set': '✅ Rol de ping configurado: {role}',
        'settings.opening_enabled': '✅ Notificaciones de apertura activadas',
        'settings.opening_disabled': '❌ Notificaciones de apertura desactivadas',
        'settings.winner_enabled': '✅ Notificaciones de ganador activadas',
        'settings.winner_disabled': '❌ Notificaciones de ganador desactivadas',
        'settings.ping_everyone_set': '✅ Ahora se pingeará @everyone',
        'settings.ping_here_set': '✅ Ahora se pingeará @here',
        'settings.ping_role_set': '✅ Ahora se pingeará al rol (configúralo con el botón "Cambiar Rol")',
        'settings.ping_disabled': '✅ Pings desactivados',
        'settings.represent_set': '✅ Ahora representas a **{server}** en los rankings globales',
        'settings.language_set': '✅ Idioma cambiado a: {language}',
        'settings.no_mutual_servers': '❌ No tienes servidores en común con el bot (además de este)',
        'settings.hours_modal_title': 'Configurar Horario del Pole',
        'settings.hours_start_label': 'Hora de inicio (0-23)',
        'settings.hours_end_label': 'Hora de fin (0-23)',
        'settings.hours_invalid': '❌ Horario inválido. Usa números entre 0 y 23, con inicio < fin.',
        'settings.hours_set': '✅ Horario actualizado: de {start}:00 a {end}:00',
        'settings.only_servers': '❌ Solo en servidores.',
        'settings.no_permissions': '❌ No se pudo determinar tus permisos en este servidor.',
        'settings.admin_only': '❌ Solo administradores pueden cambiar esta opción.',
        'settings.ping_removed': '✅ Rol de ping eliminado',
        'settings.not_configured': '❌ No configurado',
        'settings.update_failed': '❌ Error al actualizar',
        
        # Settings - Field names
        'settings.field.channel': '📺 Canal de Pole',
        'settings.field.language': '🌐 Idioma',
        'settings.field.represented_server': '🌍 Servidor Representado',
        'settings.field.ping_role': '🔔 Rol de Ping',
        'settings.field.notify_opening': '📢 Notif. Apertura',
        'settings.field.notify_winner': '🏆 Notif. Ganador',
        'settings.field.footer': 'Los cambios se aplican inmediatamente',
        
        # ==================== POLE MESSAGES ====================
        'pole.type.critical': 'CRÍTICA',
        'pole.type.fast': 'VELOZ',
        'pole.type.normal': 'POLE',
        'pole.type.marranero': 'MARRANERO',
        
        'pole.critical': '⚡ ¡POLE CRÍTICO! En solo **{minutes} minutos**. Eres una máquina.',
        'pole.fast': '🏎️ Pole rápido en **{hours}h {minutes}m**. Bien hecho.',
        'pole.normal': '✅ Pole conseguido en **{hours}h {minutes}m**.',
        'pole.marranero': '🐷 **Pole marranero**... {hours}h tarde. Mejor tarde que nunca.',
        'pole.points': '+**{points}** pts',
        'pole.streak': 'Racha: **{streak}** días',
        'pole.streak_multiplier': 'Multiplicador: **x{multiplier}**',
        'pole.new_best_streak': '🎉 ¡Nueva mejor racha personal! **{streak}** días',
        'pole.already_done': '❌ {user}, ya hiciste el pole de hoy. Mañana será.',
        'pole.before_opening': '⏰ Tranquilo {user}, el pole aún no se ha abierto. Abre a las **{time}**.',
        'pole.not_configured': '⚠️ El pole no está configurado en este servidor. Un admin debe usar `/settings`.',
        'pole.wrong_channel': '❌ {user}, el pole es en {channel}.',
        'pole.notification_title': '<a:fire:1440018375144374302> ¡EL POLE SE HA ABIERTO! <a:fire:1440018375144374302>',
        'pole.notification_desc': '¡Escribe **pole** ahora mismo para ganar puntos!',
        'pole.notification_time': 'Abierto desde las {time}',
        'pole.winner_title': '🏆 ¡{user} ha ganado el pole!',
        
        # Pole - Additional messages
        'pole.already_done_today': 'Bro, ya hiciste tu pole hoy aquí. Tranqui 🛑',
        'pole.already_done_other_server': '❌ Ya hiciste pole en otro servidor.\nSolo puedes hacer 1 pole por día en total (todos los servidores).',
        'pole.quota_full': '⚠️ La cuota de **{pole_type}** está llena ({current}/{max_allowed}).\nIntenta más tarde o espera al siguiente pole.',
        'pole.success_short': '🏁 Pole pillado: +{points} pts • Racha {streak}',
        'pole.yesterday_done': '🧑‍🦯 Crack, ya hiciste tu pole ayer. Espera a que abra el de hoy.',
        'pole.not_yet': '🧑‍🦯 Crack, aún no toca polear.',
        'pole.offline_recovery': '⚠️ El bot estuvo offline durante la apertura programada.\nEscribe **pole** ahora para ganar puntos 🏁',
        'pole.offline_recovery_title': '🔔 POLE ABIERTO (Recuperación)',
        
        # Pole - Impatient responses (anti-spam)
        'pole.impatient.1': 'Aún no toca crack, sé que no vas a llegar a tiempo',
        'pole.impatient.2': 'Qué ganas tío, déjalo abrirse primero',
        'pole.impatient.3': 'Chill, no seas impaciente',
        'pole.impatient.4': 'Espera loco que aún no ha abierto el pole',
        'pole.impatient.5': '¿No sabes esperar o qué?',
        'pole.impatient.6': '👀 pilladísimo, sigue así y ni te enteras cuando abra',
        'pole.impatient.7': 'Muy ansiosillo tú eh',
        
        # Pole - Embed fields
        'pole.field.time': '⏱️ Hora',
        'pole.field.delay': '⏳ Retraso',
        'pole.field.position': '📍 Posición',
        'pole.field.base_points': '💰 Puntos Base',
        'pole.field.streak': '{emoji} Racha',
        'pole.field.streak_one_day': '1 día',
        'pole.field.streak_multi': '{emoji} Racha (x{multiplier})',
        'pole.field.streak_days': '{days} días',
        'pole.field.total_earned': '✨ Total Ganado',
        'pole.field.broken_streak': '💔 Racha Anterior',
        'pole.field.broken_streak_desc': 'Conservas el 20% de tu racha anterior',
        'pole.field.broken_streak_title': '💔 Racha Rota',
        
        # Pole - Notification descriptions (con variaciones aleatorias)
        'pole.notification.description_critical': [
            '{mention} ⚡ CRÍTICO en solo {delay}! Eres una máquina.',
            '{mention} 💎 CRÍTICO en {delay}. Qué reflejos.',
            '{mention} ⚡ CRÍTICO brutal: {delay}. Vas volao.',
            '{mention} 💥 {delay} de CRÍTICO. Imparable.',
            '{mention} <a:fire:1440018375144374302> {delay}... Estás ROTO. Menudo crítico.',
            '{mention} ⚡ CRÍTICO ({delay}). Qué bárbaro tío.',
            '{mention} 💎 {delay}. Te has comido el pole, crack.',
            '{mention} 🚀 CRÍTICO en {delay}. Nadie te para.',
            '{mention} ⚡ {delay} de CRÍTICO. Así da gusto.',
            '{mention} 💥 CRÍTICO brutal: {delay}. Eres un puto crack.',
        ],
        'pole.notification.description_fast': [
            '{mention} 🏎️ Pole rápido en {delay}. Bien pillado.',
            '{mention} ⚡ Veloz: {delay}. Vas servido.',
            '{mention} 🏎️ {delay}. Nada mal, nada mal.',
            '{mention} 💨 Pole rápido ({delay}). A este ritmo vas a arrasar.',
            '{mention} <a:fire:1440018375144374302> {delay}. Muy fino bro.',
            '{mention} ⚡ Pole en {delay}. Esa velocidad me gusta.',
            '{mention} 🏎️ {delay}... Vas sobrao.',
            '{mention} 💨 Veloz ({delay}). Sigue así campéon.',
        ],
        'pole.notification.description_normal': [
            '{mention} ✅ Pole conseguido en {delay}.',
            '{mention} 🏁 Pole pillado: {delay}. Bien ahí.',
            '{mention} ✅ {delay} de pole. Constante.',
            '{mention} 🏁 Pole en {delay}. Manteniendo el nivel.',
            '{mention} ✅ Pole en {delay}. Sólido.',
            '{mention} 🏁 {delay}. Tranqui pero efectivo.',
            '{mention} ✅ Pole pillado ({delay}). Todo bajo control.',
        ],
        'pole.notification.description_marranero': [
            '{mention} 🐷 Pole marranero... {delay} tarde. Mejor tarde que nunca.',
            '{mention} 🐷 Marranero: {delay}. Mañana madruga más.',
            '{mention} 🐷 {delay} de retraso. Vaya sueño llevas.',
            '{mention} 🐷 Marranero en {delay}. Al menos viniste.',
            '{mention} 🐷 {delay} tarde... Eres un marrano tío.',
            '{mention} 🐷 MARRANERO en {delay}. Qué vergüenza.',
            '{mention} 🐷 {delay} de retraso. Te pasaste de rosca.',
            '{mention} 🐷 Marranero ({delay}). Vaya jeta que tienes.',
            '{mention} 🐷 {delay}... Te dormiste pero bien.',
        ],
        
        # Pole - Footers with personality
        'pole.footer.critical': 'a ver si aguantas el ritmo 🔥',
        'pole.footer.fast': 'vas servido 💪',
        'pole.footer.normal': 'bien pillado 👌',
        'pole.footer.marranero': 'mañana madruga más 🥱',
        
        # ==================== PROFILE ====================
        'profile.title': '📊 Estadísticas de {user}',
        'profile.title_global': '🌍 Stats Globales de {display_name}',
        'profile.title_local': '📊 Stats Locales de {display_name}',
        'profile.desc_global': '*Datos combinados de todos los servidores*',
        'profile.desc_local': '*Datos de este servidor únicamente*',
        'profile.no_data': '❌ {user} no tiene datos todavía. ¡Haz tu primer pole!',
        'profile.no_data_local': '❌ {mention} no ha hecho ningún pole en este servidor.',
        
        # Profile fields
        'profile.field.season_current': '🎯 Temporada Actual',
        'profile.field.rank_historical': '🏅 Rango Histórico',
        'profile.field.rank_historical_server': '🏅 Rango Histórico (Servidor)',
        'profile.field.total_points': '💰 Puntos Totales',
        'profile.field.points_server': '💰 Puntos en este Servidor',
        'profile.field.total_poles': '🏁 Poles Totales',
        'profile.field.poles_server': '🏁 Poles en este Servidor',
        'profile.field.current_streak': '{emoji} Racha Actual',
        'profile.field.current_streak_global': '{emoji} Racha Actual (Global)',
        'profile.field.best_streak': '{emoji} Mejor Racha',
        'profile.field.best_streak_global': '{emoji} Mejor Racha (Global)',
        'profile.field.streak_days': '{days} días',
        'profile.field.breakdown': '📈 Desglose por Tipo',
        'profile.field.breakdown_server': '📈 Desglose por Tipo (Servidor)',
        
        'profile.rank': '🏅 Rango',
        'profile.total_points': '💰 Puntos Totales',
        'profile.total_poles': '🏁 Poles Totales',
        'profile.current_streak': '<a:fire:1440018375144374302> Racha Actual',
        'profile.best_streak': '⭐ Mejor Racha',
        'profile.days': '{days} días',
        'profile.breakdown': '💎 {critical} | ⚡ {fast} | 🏁 {normal} | 🐷 {marranero}',
        'profile.critical_poles': '⚡ Críticos',
        'profile.fast_poles': '🏎️ Rápidos',
        'profile.normal_poles': '✅ Normales',
        'profile.marranero_poles': '🐷 Marraneros',
        'profile.speed_stats': '⏱️ Estadísticas de Velocidad',
        'profile.best_time': '🥇 Mejor Tiempo',
        'profile.minutes': '{minutes} min',
        'profile.average_delay': '📊 Tiempo Promedio',
        'profile.current_season': '🎯 Temporada Actual ({season})',
        'profile.season_points': 'Puntos',
        'profile.season_poles': 'Poles',
        'profile.best_season': '🏆 Mejor Temporada Histórica ({season})',
        'profile.represented_server': '🏳️ Servidor Representado',
        'profile.no_server': 'Ninguno',
        'profile.position': 'Tu posición: #{position} de {total}',
        'profile.title_local_detailed': '📊 Stats de {user} en {server}',
        'profile.footer.last_pole': 'Último pole: {date}',
        
        # Profile - Stats display
        'profile.stats.critical': '⚡ Críticos: **{count}**',
        'profile.stats.fast': '🏎️ Rápidos: **{count}**',
        'profile.stats.normal': '🏁 Normales: **{count}**',
        'profile.stats.marranero': '🐷 Marraneros: **{count}**',
        
        # ==================== LEADERBOARD ====================
        'leaderboard.title': '🏆 RANKING {scope} - {type}',
        'leaderboard.scope.local': 'LOCAL',
        'leaderboard.scope.global': 'GLOBAL',
        'leaderboard.type.people': 'Personas',
        'leaderboard.type.servers': 'Servidores',
        'leaderboard.season': 'Temporada {season}',
        'leaderboard.lifetime': 'Lifetime',
        'leaderboard.server_desc': 'Servidor: {server}',
        'leaderboard.no_data': '❌ Aún no hay estadísticas {season}en este servidor.',
        'leaderboard.no_servers': '❌ Aún no hay servidores representados {season}.',
        'leaderboard.first_place': '🥇 Primer Puesto',
        'leaderboard.only_servers': '❌ Este comando solo funciona en servidores.',
        'leaderboard.stats': '💰 {points} pts • 🏁 {poles} poles',
        'leaderboard.stats_streak': '💰 {points} pts • 🏁 {poles} poles • <a:fire:1440018375144374302> {streak}',
        'leaderboard.position': 'Tu posición: #{position} de {total}',
        'leaderboard.position_season': 'Tu posición en {season}: #{position} de {total}',
        'leaderboard.no_users': '❌ Aún no hay usuarios en este servidor.',
        'leaderboard.no_users_streak': '❌ Aún no hay usuarios con rachas en este servidor.',
        'leaderboard.footer.use_local': 'Usa /profile alcance:local para stats de este servidor',
        
        # ==================== HISTORY ====================
        'history.title': '📜 Historial de Poles - {user}',
        'history.no_data': '❌ No tienes poles registrados aún.',
        'history.pole_entry': '**{date}** - {type} ({delay})',
        'history.points': '{points} pts',
        'history.streak_at': 'Racha: {streak}',
        
        # ==================== MYSTATS ====================
        'mystats.title': '🏆 Historial de {user}',
        'mystats.no_season_data': 'Aún no has hecho ningún pole en {season}.\n¡Empieza ahora y escala el ranking!',
        'mystats.no_badges': 'Aún no has ganado ningún badge.\n¡Completa una temporada para ganar tu primer badge!',
        'mystats.season_points': '💰 **Puntos:** {points}',
        'mystats.season_poles': '🏁 **Poles:** {poles}',
        'mystats.breakdown': '📈 Desglose',
        'mystats.breakdown_entry': '⚡ Critical: {critical} | 🏎️ Fast: {fast} | 🏁 Normal: {normal} | 🐷 Sleepyheads: {marranero}',
        'mystats.field.status': 'Estado',
        
        # ==================== MIDNIGHT SUMMARY ====================
        'midnight.streak_at_risk': '⚠️ **{count}** con la racha en el filo:\n\n',
        
        # ==================== MENCIONES ====================
        'mention.intro': '¡Hola! Soy el **Pole Bot** 🎬',
        'mention.description': 'Cada día, a una hora aleatoria, se abre el pole. ¡Sé el primero en escribir `pole` para ganar puntos!',
        'mention.setup': '**Configuración**',
        'mention.setup_desc': 'Usa `/settings` para configurar el bot',
        'mention.commands': '**Comandos Principales**',
        'mention.help': 'Para más ayuda, visita la documentación o pregunta en el servidor de soporte.',
        
        # ==================== ONBOARDING ====================
        'onboarding.title': '🏁 ¡Gracias por añadirme!',
        'onboarding.intro': '**Soy Pole Bot**, tu asistente para competir por ser el más rápido cada día.\n\n',
        'onboarding.language_default': '🌐 **Idioma predeterminado:** Español\n*(Cámbialo con `/settings` → Idioma)*\n\n',
        'onboarding.quick_setup': '**⚡ Setup Rápido (3 pasos):**\n1️⃣ Usa `/settings` para elegir el **canal de pole**\n2️⃣ (Opcional) Cambia el **idioma** si prefieres inglés\n3️⃣ (Recomendado) Configura un **rol para pings** de notificaciones\n\n',
        'onboarding.how_it_works': '**🎮 Cómo funciona:**\n• Cada día el pole se abre a una hora aleatoria\n• El primero en escribir `pole` gana puntos\n• Mantén rachas consecutivas para multiplicadores\n• Compite local y globalmente\n\n',
        'onboarding.commands': 'Usa `/rules` para ver las reglas completas. ¡Suerte! 🏁',
        'onboarding.footer': '¡Que gane el más rápido! 🔥',
        
        'onboarding.bilingual_notice': '\n\n---\n\n🇬🇧 **English available!** Use `/settings` → Language to switch.\n**Default language:** Spanish',
        
        # ==================== EVENTS (Easter Eggs) ====================
        'events.first_message_channel': '🏁 ¡POLE! Primer mensaje en este canal! 🏁',
        'events.first_message_thread': '🏁 ¡POLE! Primer mensaje en este hilo! 🏁',
        'events.welcome_member': '¡Bienvenido {mention}! Ya somos {count} poleadores. 🎬',
        
        # Command errors
        'events.error.no_permissions': '❌ No tienes permisos para usar este comando.',
        'events.error.missing_arg': '❌ Falta un argumento: {arg}',
        
        # ==================== ERRORS ====================
        'error.generic': '❌ Ha ocurrido un error. Inténtalo de nuevo.',
        'error.no_permissions': '❌ No tienes permisos para hacer esto.',
        'error.dm_not_supported': '❌ Este comando no funciona en mensajes directos.',
        
        # ==================== MISC ====================
        'common.yes': 'Sí',
        'common.no': 'No',
        'common.enabled': '✅ Activo',
        'common.disabled': '❌ Desactivado',
        'common.none': 'Ninguno',
        'common.loading': 'Cargando...',
        'common.pts': 'pts',
        'common.poles': 'poles',
        
        # ==================== MIGRATION ====================
        'migration.in_progress': '⚠️ **Migración de temporada en progreso**\n\nEl sistema de poles está temporalmente deshabilitado mientras se migra a la nueva temporada.\nVuelve en unos minutos.',
        
        # ==================== NOTIFICATIONS (más) ====================
        'notification.recovery_footer': 'Apertura original: {time}',
        
        # ==================== ERRORES CRÍTICOS ====================
        'errors.configure_channel': '⚙️ Configura primero el canal de pole con `/settings`.',
        'errors.no_time_configured': '⚠️ No hay hora de pole configurada para hoy.',
        'errors.invalid_time_config': '⚠️ Config de hora diaria inválida. Contacta a un admin.',
        'errors.command_server_only': '❌ Este comando solo funciona en servidores.',
        'errors.no_mutual_servers': '❌ No estás en ningún servidor donde yo también esté.',
        'errors.server_only_short': '❌ Solo en servidores.',
        'errors.no_permissions_check': '❌ No se pudo determinar tus permisos en este servidor.',
        'errors.no_users': '❌ Aún no hay usuarios en este servidor.',
        'errors.no_streaks': '❌ Aún no hay usuarios con rachas en este servidor.',
        
        # ==================== SETTINGS UI ====================
        'ui.select_channel': 'Selecciona el canal de pole',
        'ui.select_role': 'Selecciona el rol para pingear',
        'ui.select_server': 'Selecciona un servidor...',
        'ui.select_option': 'Selecciona qué configurar...',
        'ui.button.refresh': 'Actualizar Vista',
        
        # Options del menú settings
        'ui.option.channel.label': 'Canal de Pole',
        'ui.option.channel.desc': 'Cambiar el canal donde se hace pole',
        'ui.option.language.label': 'Idioma',
        'ui.option.language.desc': 'Cambiar idioma del bot',
        'ui.option.ping_role.label': 'Rol de Ping',
        'ui.option.ping_role.desc': 'Configurar rol para notificaciones',
        'ui.option.clear_ping.label': 'Quitar Rol de Ping',
        'ui.option.clear_ping.desc': 'Eliminar rol de ping',
        'ui.option.notify_open.label': 'Toggle Notif. Apertura',
        'ui.option.notify_open.desc': 'Activar/Desactivar aviso de apertura',
        'ui.option.notify_winner.label': 'Toggle Notif. Ganador',
        'ui.option.notify_winner.desc': 'Activar/Desactivar aviso de ganador',
        'ui.option.represent.label': 'Cambiar Representación',
        'ui.option.represent.desc': 'Servidor que representas en el ranking global',
        
        # Embeds de configuración
        'ui.language.title': '🌐 Cambiar Idioma',
        'ui.language.desc': 'Idioma actual: **{current}**\n\nSelecciona el nuevo idioma para el bot:',
        'ui.language.button.es': 'Español',
        'ui.language.button.en': 'English',
        'ui.represent.title': '🏳️ Cambiar Representación',
        'ui.represent.desc': 'Selecciona el servidor que quieres representar en los rankings globales.',
        'ui.settings.desc': 'Selecciona las opciones que quieres modificar usando el menú desplegable',
        'ui.select_role_prompt': '🔔 Selecciona el rol para pingear:',
        'ui.select_channel_prompt': '📺 Selecciona el canal de pole:',
        'ui.represent.current': '📍 Actualmente representas',
        'ui.represent.none': '*Ningún servidor configurado*',
        
        # ==================== NOTIFICACIONES ====================
        'notification.pole_open': '🔔 POLE ABIERTO',
        'notification.pole_open_recovery': '🔔 POLE ABIERTO (Recuperación)',
        'notification.pole_open_recovery_desc': '⚠️ El bot estuvo offline durante la apertura programada.\nEscribe **pole** ahora para ganar puntos 🏁',
        'notification.pole_open_desc': 'Llegó la hora: suelta ese **pole** y suma puntos 🏁\nEl primero manda, el resto acompaña.',
        'notification.pole_open_footer': 'Que empiece la poleada ✨',
        'notification.streak_lost': '💔 Racha perdida',
        'notification.streak_lost_desc': '{names}\nLa racha se ha reiniciado por no completar ayer.',
        'notification.daily_summary': '🌃 Resumen del Día',
        'notification.daily_summary_desc': '**{count}** miembros completaron su pole ayer',
        
        # ==================== LEADERBOARD ====================
        'leaderboard.title.local_people': '🏆 RANKING LOCAL - Personas - {season}',
        'leaderboard.title.local_servers': '🏆 RANKING LOCAL - Servidores - {season}',
        'leaderboard.title.local_streaks': '<a:fire:1440018375144374302> RANKING DE RACHAS - Local',
        'leaderboard.title.global_people': '🌍 RANKING GLOBAL - Personas - {season}',
        'leaderboard.title.global_servers': '🌍 RANKING GLOBAL - Servidores - {season}',
        'leaderboard.title.global_streaks': '<a:fire:1440018375144374302> RANKING DE RACHAS - Global',
        
        'leaderboard.desc.local_people': 'Servidor: {server}',
        'leaderboard.desc.local_servers': 'Servidores representados por miembros de {server}',
        'leaderboard.desc.local_streaks': 'Servidor: {server}\n*(Rachas son globales entre todos los servidores)*',
        
        'leaderboard.footer.position': 'Tu posición: #{pos} de {total}',
        'leaderboard.footer.position_season': 'Tu posición en {season}: #{pos} de {total}',
        'leaderboard.footer.streak_position': 'Tu posición: #{pos} • Tu racha: {streak} días',
        'leaderboard.footer.use_local': 'Usa /profile alcance:local para ver stats de este servidor',
        'leaderboard.footer.use_global': 'Usa /profile alcance:global para ver estadísticas globales',
        
        'leaderboard.no_data_local': '❌ Aún no hay datos locales{season_info}.',
        'leaderboard.no_data_global': '❌ Aún no hay datos globales{season_info}.',
        'leaderboard.no_data_servers': '❌ Aún no hay servidores representados {season_info}.',
        'leaderboard.no_data_streaks_global': '❌ Aún no hay rachas registradas.',
        
        # Formato de entradas
        'leaderboard.entry.members': '👥 {count} miembros',
        'leaderboard.entry.current_streak': 'Actual: **{current}** días',
        'leaderboard.entry.best_streak': 'Mejor: **{best}** días',
        
        # ==================== PROFILE ====================
        'profile.title.global': '🌍 Perfil Global de {user}',
        'profile.title.local': '📍 Perfil Local de {user}',
        
        'profile.field.season_rank': '🏆 Rango Temporada',
        'profile.field.season_rank_value': '{emoji} **{name}**\n💰 {points} pts esta temporada',
        'profile.field.rank': '🏆 Rango',
        'profile.field.rank_value': '{emoji} **{name}**\n(Mejor temporada: {best_points} pts)',
        'profile.field.total_points': '💰 Puntos Totales',
        'profile.field.total_poles': '🏁 Poles Totales',
        'profile.field.current_streak': '<a:fire:1440018375144374302> Racha Actual',
        'profile.field.best_streak': '⭐ Mejor Racha',
        'profile.field.server_represented': '🏳️ Servidor Representado',
        'profile.field.server_rep_none': 'No configurado',
        
        'profile.footer.last_pole': 'Último pole: {date}',
        'profile.footer.no_poles': 'Aún no ha hecho pole',
        
        # Profile - Streak
        'profile.streak.current_title': '{emoji} Racha Actual',
        'profile.streak.current_value': '**{days}** días consecutivos\nMultiplicador: **x{multiplier:.1f}**',
        
        # Profile - POLE REWIND Hall of Fame values
        'rewind.points_value': '<@{uid}> - **{points:,}** pts',
        'rewind.poles_value': '<@{uid}> - **{count}** poles',
        'rewind.streak_value': '<@{uid}> - **{streak}** días consecutivos',
        'rewind.speed_value': '<@{uid}> - **{delay:.1f}** min promedio',
        
        # ==================== HISTORY ====================
        'history.title': '📜 Historial de Poles - {user}',
        'history.no_poles': '❌ Aún no has hecho ningún pole.',
        'history.footer': 'Página {current} de {total}',
        'history.entry': '{emoji} **{type}** • {delay} • {date}\n{points} pts • Servidor: {server}',
        
        # ==================== POLEHELP ====================
        'help.title': '📖 Pole Bot - Guía Rápida',
        'help.description': 'Compite cada día por escribir **pole** lo más rápido posible tras la apertura diaria',
        'help.how_to_play': '🎮 Cómo Jugar',
        'help.how_to_play_desc': '1. Espera la **notificación de apertura** (hora aleatoria cada día)\n2. Escribe exactamente **`pole`** en el canal configurado\n3. ¡Gana puntos según tu velocidad!\n⚠️ Solo 1 pole al día, en cualquier servidor',
        'help.categories': '🏆 Categorías de Pole',
        'help.categories_desc': '💎 **Critical** (0-10 min): 20 pts\n    └ Only 10% of server can claim it\n⚡ **Fast** (10 min - 3h): 15 pts\n    └ Only 30% of server can claim it\n🏁 **Normal** (3h - 00:00): 10 pts\n    └ No user limit\n🐷 **Sleepyhead** (next day): 5 pts\n    └ No user limit',
        'help.streaks': '<a:fire:1440018375144374302> Sistema de Rachas',
        'help.streaks_desc': 'Haz pole días consecutivos para aumentar tu multiplicador\n• 7 días: x1.1\n• 30 días: x1.4\n• 90 días: x1.8\n• 300 días: x2.5 (máximo)',
        'help.commands': '⚙️ Comandos',
        'help.commands_desc': '`/profile` - Ver tu perfil y estadísticas\n`/leaderboard` - Ver rankings (local/global, personas/servidores)\n`/streak` - Info detallada de tu racha\n`/season` - Ver temporada actual y tu progreso\n`/history` - Ver badges y temporadas pasadas\n`/settings` - Configurar el bot (admins)\n`/polehelp` - Ver esta ayuda',
        'help.footer': '¡Suerte y que gane el más rápido! 🔥',
        
        # ==================== SEASON ====================
        'season.official': '🏆 **Temporada Oficial**',
        'season.practice': '🎯 **Temporada de Práctica**',
        'season.status': 'Estado',
        'season.time_remaining': '⏰ Tiempo Restante',
        'season.days_left': '**{days}** días',
        'season.finished': '**Finalizada**',
        'season.your_progress': '📊 Tu Progreso en {season}',
        'season.your_progress_desc': '🎖️ **Rango:** {emoji} {name}\n💰 **Puntos:** {points}\n🏁 **Poles:** {poles}\n<a:fire:1440018375144374302> **Mejor Racha:** {streak} días',
        'season.breakdown': '📈 Desglose',
        'season.breakdown_desc': '💎 Critical: {critical} | ⚡ Fast: {fast}\n🏁 Normal: {normal} | 🐷 Sleepyheads: {marranero}',
        'season.no_poles': 'Aún no has hecho ningún pole en {season}.\n¡Empieza ahora y escala el ranking!',
        'season.footer': 'Usa /history para ver temporadas pasadas 🔥',
        'season.period': '**Período:** {start} → {end}',
        
        # ==================== MYSTATS (History) ====================
        'mystats.title': '🏆 Historial de {user}',
        'mystats.description': 'Tu legado a través de las temporadas',
        'mystats.badges': '🏅 Colección de Badges',
        'mystats.no_badges': 'Aún no has ganado ningún badge.\n¡Completa una temporada para conseguir tu primer badge!',
        'mystats.seasons': '📜 Temporadas Completadas',
        'mystats.no_seasons': 'Aún no has completado ninguna temporada.\n¡Sigue jugando y deja tu marca!',
        'mystats.season_entry': '**{name}** ({year})\n🎖️ Rango: {rank} | 💰 {points} pts | #{pos} de {total}\n🏁 {poles} poles | <a:fire:1440018375144374302> Mejor racha: {streak}',
        
        # ==================== STREAK COMMAND ====================
        'streak.off': '<:gray_fire:1445324596751503485> Racha apagada',
        'streak.off_desc': 'Racha de 0 días. Enciéndela con un pole hoy.',
        'streak.best': '🏆 Tu Mejor Racha',
        'streak.best_value': '**{streak}** días',
        'streak.next_milestone': '🎯 Próximo Hito',
        'streak.next_milestone_value': '{milestone} días (faltan **{days}** días)\nMultiplicador: x{multiplier:.1f}',
        'streak.last_pole': '📅 Último Pole',
        'streak.last_pole_today': 'Hoy ✅',
        'streak.last_pole_yesterday': 'Ayer',
        'streak.last_pole_days_ago': 'Hace {days} días',
        
        # ==================== POLE REWIND (Season Change) ====================
        'rewind.intro_first_title': '🎆 ¡FELIZ AÑO NUEVO, EARLY POLERS! 🎆',
        'rewind.intro_first_desc': 'Qué locura de año, familia.\n\nUstedes son los **PIONEROS**. Los que creyeron en este bot cuando era un experimento random. Los que se comieron los bugs, las rachas rotas, las horas locas del pole... y **AÚN ASÍ** siguieron aquí.\n\nEste ha sido solo el **CALENTAMIENTO**. La pre-temporada. El tutorial.\n\nAhora viene el **POLE REWIND {season}**. Vamos a recordar quiénes fueron las leyendas. 🎬',
        'rewind.intro_title': '🎆 ¡FELIZ AÑO NUEVO, POLERS! 🎆',
        'rewind.intro_desc': 'Otro año más, otra batalla ganada.\n\nGracias a todos los que hicieron del pole parte de su rutina diaria. Cada pole a las 3am, cada racha salvada in extremis, cada momento épico... **ESO** es lo que hace que esta comunidad sea lo que es.\n\nEs hora del **POLE REWIND {season}**. 🎬',
        'rewind.local_points_title': '👑 MÁXIMOS ANOTADORES - {server}',
        'rewind.local_points_desc': 'Los que acumularon más puntos en esta temporada:',
        'rewind.local_poles_title': '⚡ POLEMANIÁTICOS - {server}',
        'rewind.local_poles_desc': 'Los que más veces fueron los primeros:',
        'rewind.local_streaks_title': '<a:fire:1440018375144374302> DISCIPLINA MÁXIMA - {server}',
        'rewind.local_streaks_desc': 'Los que mantuvieron las rachas más largas:',
        'rewind.local_speed_title': '⚡ VELOCISTAS - {server}',
        'rewind.local_speed_desc': 'Los más rápidos en promedio (mínimo 10 poles):',
        'rewind.global_title': '🌍 HALL OF FAME GLOBAL',
        'rewind.global_desc': 'Las leyendas que dominaron **TODOS** los servidores en {season}:',
        'rewind.global_points': '**👑 Máximos Anotadores**',
        'rewind.global_poles': '**⚡ Polemaniáticos**',
        'rewind.global_streaks': '**<a:fire:1440018375144374302> Disciplina Máxima**',
        'rewind.global_speed': '**⚡ Velocistas** (min 10 poles)',
        'rewind.footer_hof': 'Hall of Fame {season} • {tagline}',
        'rewind.footer_global': 'Leyendas del Pole Bot • Nivel Dios',
        'rewind.no_data': '_Nadie compitió en esta categoría._',
        'rewind.no_data_speed': '_No hay suficientes datos._',
        'rewind.no_data_global': '_Sin datos globales para esta temporada._',
        
        # Taglines del Hall of Fame
        'rewind.tagline.points': 'La consistencia paga.',
        'rewind.tagline.poles': 'Siempre ahí.',
        'rewind.tagline.streaks': 'La disciplina es poder.',
        'rewind.tagline.speed': 'Reflejos de campeón.',
        
        # Mensajes de nueva temporada
        'rewind.new_season_first_title': '🚀 BIENVENIDOS A LA {season}',
        'rewind.new_season_first_desc': 'Se acabó la beta. Ahora va **EN SERIO**.\n\nEsta es la **TEMPORADA 1** oficial del Pole Bot. Todo lo anterior fue práctica.\n\n♻️ Puntos a 0. Rachas a 0.\n💎 Tus badges BETA se quedan contigo.\n\nTodos empezamos igual. Que gane el que más lo quiera.\n\nLa competencia oficial empieza... **AHORA**. 🏁',
        'rewind.new_season_title': '🚀 BIENVENIDOS A LA {season}',
        'rewind.new_season_desc': 'Se acabó mirar atrás. Desde hoy, borrón y cuenta nueva:\n\n♻️ Puntos reseteados a 0\n♻️ Rachas reseteadas a 0\n💎 Tus badges se quedan contigo (honor)\n\n{season} arranca **YA**. Todos empezamos desde cero, con las mismas posibilidades.\n\nQue gane el mejor. 🏁',
        'rewind.new_season_duration': '📅 Duración de Temporada',
        'rewind.new_season_duration_value': 'Desde **{start}** hasta **{end}**',
        'rewind.new_season_footer': '¡Que comience la competencia! 🔥',
        
        # ==================== MIDNIGHT SUMMARY ====================
        'summary.new_day': '🌅 Nuevo Día',
        'summary.new_day_desc': 'Arranca la jornada: espera el ping y entra a polear.',
        'summary.footer': 'Resumen automático • Sin pings',
        'summary.completed_yesterday': '✅ Completaron su pole ayer',
        'summary.streak_at_risk': '⏳ Racha en Peligro',
        'summary.streak_at_risk_desc': '⚠️ **{count}** con la racha en el filo:\n\n{users}\n\n🐷 Aún puedes hacer el **marranero** hasta la próxima apertura.',
        'summary.user_streak': '⏳ {mention} (racha {streak} días)',
        'summary.and_more': '_...y {count} más_',
        'summary.pole_elsewhere': '🌍 Polearon en Otro Servidor ({count})',
        'summary.user_elsewhere': '🌍 {mention} en **{guild}** (racha {streak} días)',
        
        # ==================== DEDICATORIAS POLE REWIND ====================
        # Dedicatorias Locales
        'dedication.points.1': 'El Rey de la Consistencia',
        'dedication.points.2': 'Segundo pero Letal',
        'dedication.points.3': 'Bronce con Honor',
        
        'dedication.poles.1': 'El Polemaniático Supremo',
        'dedication.poles.2': 'Siempre Segundo, Nunca Olvidado',
        'dedication.poles.3': 'Competencia de Élite',
        
        'dedication.streak.1': 'La Disciplina Hecha Persona',
        'dedication.streak.2': 'Constancia de Acero',
        'dedication.streak.3': 'Disciplina Inquebrantable',
        
        'dedication.speed.1': 'Reflejos de Rayo',
        'dedication.speed.2': 'Velocidad Supersónica',
        'dedication.speed.3': 'Rápido como el Viento',
        
        # Dedicatorias Globales
        'dedication.points_global.1': 'El Titán de los Puntos',
        'dedication.points_global.2': 'Leyenda Viviente',
        'dedication.points_global.3': 'Monstruo de Competición',
        
        'dedication.poles_global.1': 'Obsesión Nivel Dios',
        'dedication.poles_global.2': 'Adicción Pura y Dura',
        'dedication.poles_global.3': 'Siempre en el Top',
        
        'dedication.streak_global.1': 'Constancia Sobrehumana',
        'dedication.streak_global.2': 'Nunca Falta',
        'dedication.streak_global.3': 'Compromiso Total',
        
        'dedication.speed_global.1': 'Velocidad de la Luz',
        'dedication.speed_global.2': 'Flash Hecho Persona',
        'dedication.speed_global.3': 'Reflejos Inhumanos',
        
        # ==================== RANK NAMES ====================
        'rank.bronze': 'Bronce - Iniciado',
        'rank.silver': 'Plata - Aspirante',
        'rank.gold': 'Oro - Competidor',
        'rank.diamond': 'Diamante - Veterano',
        'rank.amethyst': 'Amatista - Maestro',
        'rank.ruby': 'Rubí - Leyenda',
        
        # ==================== BUTTONS ====================
        'button.refresh': 'Actualizar Vista',
        
        # ==================== DOWNTIME COMPENSATION ====================
        'compensation.apology_title': '🛠️ Disculpas por el Downtime',
        'compensation.apology_desc': 'El bot estuvo caído el **{date}** por problemas técnicos.\n\n**{count} usuarios** han sido compensados automáticamente:\n• ✅ Pole normal otorgado retroactivamente\n• {fire} Rachas mantenidas/activadas\n• 🏆 Puntos de temporada añadidos\n\n**Gracias por vuestra paciencia.** 🙏',
        'compensation.apology_footer': 'Compensación automática global • {count} usuarios',
    },
    
    'en': {
        # ==================== COMMANDS ====================
        'cmd.settings.desc': 'Configure Pole Bot settings (view based on your permissions)',
        'cmd.profile.desc': 'Check out player stats',
        'cmd.profile.user_param': 'Player to check (leave empty for yourself)',
        'cmd.profile.scope_param': 'Scope: global (all servers) or local (this server)',
        'cmd.leaderboard.desc': 'Check the leaderboards',
        'cmd.leaderboard.scope_param': 'Leaderboard scope',
        'cmd.leaderboard.type_param': 'Leaderboard type',
        'cmd.leaderboard.limit_param': 'How many results',
        'cmd.leaderboard.season_param': 'Specific season (optional)',
        'cmd.history.desc': 'Check your pole history',
        'cmd.history.limit_param': 'How many poles to show (max 20)',
        'cmd.streak.desc': 'Check detailed info about your streak',
        'cmd.season.desc': 'View current season info and your progress',
        'cmd.polehelp.desc': 'Learn how the bot works',
        'cmd.mystats.desc': 'View your season history and badge collection',
        
        # Describe params
        'cmd.leaderboard.scope_describe': 'Leaderboard scope: local (this server) or global (all servers)',
        'cmd.leaderboard.type_describe': 'Leaderboard type: players, servers or streaks',
        'cmd.leaderboard.season_describe': 'Season to display (Lifetime by default)',
        'cmd.leaderboard.limit_describe': 'Number of entries to show (default 10)',
        
        # Command choices
        'choice.scope.global': 'Global (all servers)',
        'choice.scope.local': 'Local (this server)',
        'choice.type.people': 'Players',
        'choice.type.servers': 'Servers',
        'choice.type.streaks': 'Streaks',
        'choice.season.lifetime': 'Lifetime (all seasons)',
        
        # Leaderboard choices (short)
        'choice.local': 'Local',
        'choice.global': 'Global',
        'choice.personas': 'Players',
        'choice.servidores': 'Servers',
        'choice.rachas': 'Streaks',
        
        # ==================== SETTINGS ====================
        'settings.title': '⚙️ Pole Bot Settings',
        'settings.admin_view': 'Admin view',
        'settings.user_view': 'User view',
        'settings.channel': '📺 Channel',
        'settings.channel_not_set': 'Not configured',
        'settings.notifications': '🔔 Notifications',
        'settings.notify_opening': 'Pole opening',
        'settings.notify_winner': 'Pole winner',
        'settings.ping_mode': 'Ping mode',
        'settings.ping_role': 'Ping role',
        'settings.pole_hours': '⏰ Pole Schedule',
        'settings.pole_hours_desc': 'From {start}:00 to {end}:00',
        'settings.today_time': '🎲 Today\'s Time',
        'settings.today_time_desc': 'Opens at {time}',
        'settings.today_time_pending': 'Generating...',
        'settings.language': '🌐 Language',
        'settings.language_current': 'English',
        'settings.represent_server': '🏳️ Server You Represent',
        'settings.represent_server_desc': '{server}',
        'settings.represent_server_none': 'None (choose one for global rankings)',
        
        # Settings buttons
        'settings.btn.change_channel': '📺 Change Channel',
        'settings.btn.toggle_opening': '🔔 Opening Notif.',
        'settings.btn.toggle_winner': '🏆 Winner Notif.',
        'settings.btn.change_role': '👥 Change Role',
        'settings.btn.ping_everyone': '📢 Ping @everyone',
        'settings.btn.ping_here': '📍 Ping @here',
        'settings.btn.ping_role': '👤 Ping Role',
        'settings.btn.no_ping': '🔕 No Ping',
        'settings.btn.change_hours': '⏰ Change Schedule',
        'settings.btn.change_language': '🌐 Change Language',
        'settings.btn.change_represent': '🏳️ Change Server',
        'settings.btn.refresh': '🔄 Refresh',
        
        # Settings messages
        'settings.channel_set': '✅ Pole channel set: {channel}',
        'settings.role_set': '✅ Ping role set: {role}',
        'settings.opening_enabled': '✅ Opening notifications on',
        'settings.opening_disabled': '❌ Opening notifications off',
        'settings.winner_enabled': '✅ Winner notifications on',
        'settings.winner_disabled': '❌ Winner notifications off',
        'settings.ping_everyone_set': '✅ Now pinging @everyone',
        'settings.ping_here_set': '✅ Now pinging @here',
        'settings.ping_role_set': '✅ Now pinging role (set it with "Change Role" button)',
        'settings.ping_disabled': '✅ Pings off',
        'settings.represent_set': '✅ Now repping **{server}** in global rankings',
        'settings.language_set': '✅ Language changed to: {language}',
        'settings.no_mutual_servers': '❌ You\'re not in any other servers with me',
        'settings.hours_modal_title': 'Set Pole Hours',
        'settings.hours_start_label': 'Start hour (0-23)',
        'settings.hours_end_label': 'End hour (0-23)',
        'settings.hours_invalid': '❌ Invalid hours. Use 0-23, start must be less than end.',
        'settings.hours_set': '✅ Hours updated: {start}:00 to {end}:00',
        'settings.only_servers': '❌ Servers only, mate.',
        'settings.no_permissions': '❌ Can\'t figure out your perms here.',
        'settings.admin_only': '❌ Only admins can change this, chief.',
        'settings.ping_removed': '✅ Ping role removed',
        'settings.not_configured': '❌ Not set up',
        'settings.update_failed': '❌ Failed to update',
        
        # Settings - Field names
        'settings.field.channel': '📺 Pole Channel',
        'settings.field.language': '🌐 Language',
        'settings.field.represented_server': '🌍 Server You Rep',
        'settings.field.ping_role': '🔔 Ping Role',
        'settings.field.notify_opening': '📢 Opening Notif.',
        'settings.field.notify_winner': '🏆 Winner Notif.',
        'settings.field.footer': 'Changes apply instantly',
        
        # ==================== POLE MESSAGES ====================
        'pole.type.critical': 'CRITICAL',
        'pole.type.fast': 'FAST',
        'pole.type.normal': 'POLE',
        'pole.type.marranero': 'SLEEPYHEAD',
        
        'pole.critical': '⚡ CRITICAL POLE! Just **{minutes} minutes**. Absolutely cracked.',
        'pole.fast': '🏎️ Quick pole in **{hours}h {minutes}m**. Pretty solid.',
        'pole.normal': '✅ Pole secured in **{hours}h {minutes}m**.',
        'pole.marranero': '🐷 **Sleepyhead pole**... {hours}h late. Better late than never.',
        'pole.points': '+**{points}** pts',
        'pole.streak': 'Streak: **{streak}** days',
        'pole.streak_multiplier': 'Multiplier: **x{multiplier}**',
        'pole.new_best_streak': '🎉 New personal best! **{streak}** day streak. Unstoppable.',
        'pole.already_done': '❌ {user}, you already bagged today\'s pole. Catch you tomorrow.',
        'pole.before_opening': '⏰ Chill {user}, pole ain\'t open yet. Drops at **{time}**.',
        'pole.not_configured': '⚠️ Pole isn\'t set up on this server. Admin needs to hit `/settings`.',
        'pole.wrong_channel': '❌ {user}, wrong spot. Pole\'s in {channel}.',
        'pole.notification_title': '<a:fire:1440018375144374302> POLE IS LIVE! <a:fire:1440018375144374302>',
        'pole.notification_desc': 'Type **pole** right now to rack up points!',
        'pole.notification_time': 'Live since {time}',
        'pole.winner_title': '🏆 {user} claimed the pole!',
        
        # Pole - Additional messages
        'pole.already_done_today': 'Yo, you already bagged today\'s pole here. Chill 🛑',
        'pole.already_done_other_server': '❌ You already hit pole on another server.\nOnly 1 pole per day total (across all servers).',
        'pole.quota_full': '⚠️ The **{pole_type}** quota is maxed ({current}/{max_allowed}).\nTry later or wait for next pole.',
        'pole.success_short': '🏁 Pole secured: +{points} pts • {streak} streak',
        'pole.yesterday_done': '🧑‍🦯 Yo, you already got yesterday\'s pole. Wait for today\'s drop.',
        'pole.not_yet': '🧑‍🦯 Not yet, hold your horses.',
        'pole.offline_recovery': '⚠️ Bot was offline during scheduled opening.\nType **pole** now to rack up points 🏁',
        'pole.offline_recovery_title': '🔔 POLE LIVE (Recovery)',
        
        # Pole - Impatient responses (anti-spam)
        'pole.impatient.1': 'Not yet mate, you ain\'t gonna make it anyway',
        'pole.impatient.2': 'So eager huh, let it drop first',
        'pole.impatient.3': 'Chill, don\'t be impatient',
        'pole.impatient.4': 'Hold up, pole hasn\'t opened yet',
        'pole.impatient.5': 'Can\'t wait or what?',
        'pole.impatient.6': '👀 caught you, keep this up and you\'ll miss when it actually drops',
        'pole.impatient.7': 'Bit too eager aren\'t we',
        
        # Pole - Embed fields
        'pole.field.time': '⏱️ Time',
        'pole.field.delay': '⏳ Delay',
        'pole.field.position': '📍 Position',
        'pole.field.base_points': '💰 Base Points',
        'pole.field.streak': '{emoji} Streak',
        'pole.field.streak_one_day': '1 day',
        'pole.field.streak_multi': '{emoji} Streak (x{multiplier})',
        'pole.field.streak_days': '{days} days',
        'pole.field.total_earned': '✨ Total Earned',
        'pole.field.broken_streak': '💔 Previous Streak',
        'pole.field.broken_streak_desc': 'You keep 20% of your previous streak',
        'pole.field.broken_streak_title': '💔 Streak Broken',
        
        # Pole - Notification descriptions (with random variations)
        'pole.notification.description_critical': [
            '{mention} ⚡ CRITICAL in just {delay}! Absolutely cracked.',
            '{mention} 💎 CRITICAL: {delay}. Lightning fast.',
            '{mention} ⚡ Brutal CRITICAL: {delay}. On fire.',
            '{mention} 💥 {delay} CRITICAL. Unstoppable.',
            '{mention} <a:fire:1440018375144374302> {delay}... You\'re INSANE. What a crit.',
            '{mention} ⚡ CRITICAL ({delay}). Fucking beast mode.',
            '{mention} 💎 {delay}. You ATE that pole, king.',
            '{mention} 🚀 CRITICAL in {delay}. Built different.',
            '{mention} ⚡ {delay} CRITICAL. No one\'s touching you.',
            '{mention} 💥 Brutal CRITICAL: {delay}. Too clean.',
        ],
        'pole.notification.description_fast': [
            '{mention} 🏎️ Quick pole in {delay}. Solid grab.',
            '{mention} ⚡ Fast: {delay}. Pretty good.',
            '{mention} 🏎️ {delay}. Not bad at all.',
            '{mention} 💨 Quick pole ({delay}). Keep it up.',
            '{mention} <a:fire:1440018375144374302> {delay}. Clean grab bro.',
            '{mention} ⚡ Pole in {delay}. That speed hits different.',
            '{mention} 🏎️ {delay}... You got it like that.',
            '{mention} 💨 Fast ({delay}). Keep cooking champ.',
        ],
        'pole.notification.description_normal': [
            '{mention} ✅ Pole secured in {delay}.',
            '{mention} 🏁 Pole grabbed: {delay}. Nice.',
            '{mention} ✅ {delay} pole. Consistent.',
            '{mention} 🏁 Pole in {delay}. Steady pace.',
            '{mention} ✅ Pole in {delay}. Solid.',
            '{mention} 🏁 {delay}. Chill but effective.',
            '{mention} ✅ Pole grabbed ({delay}). All good.',
        ],
        'pole.notification.description_marranero': [
            '{mention} 🐷 Sleepyhead pole... {delay} late. Better late than never.',
            '{mention} 🐷 Sleepyhead: {delay}. Wake up earlier tomorrow.',
            '{mention} 🐷 {delay} delay. Quite the oversleep.',
            '{mention} 🐷 Sleepyhead in {delay}. At least you showed up.',
            '{mention} 🐷 {delay} late... You a whole mess.',
            '{mention} 🐷 SLEEPYHEAD in {delay}. Shameless.',
            '{mention} 🐷 {delay} delay. Overslept hard.',
            '{mention} 🐷 Sleepyhead ({delay}). The audacity lmao.',
            '{mention} 🐷 {delay}... Bro was in a coma.',
        ],
        
        # Pole - Footers with personality
        'pole.footer.critical': 'let\'s see if you can keep up 🔥',
        'pole.footer.fast': 'pretty nice 💪',
        'pole.footer.normal': 'solid grab 👌',
        'pole.footer.marranero': 'sleepyhead mode 🥱',
        
        # ==================== PROFILE ====================
        'profile.title': '📊 {user}\'s Stats',
        'profile.title_global': '🌍 {display_name}\'s Global Stats',
        'profile.title_local': '📊 {display_name}\'s Local Stats',
        'profile.desc_global': '*Combined data from all servers*',
        'profile.desc_local': '*Data from this server only*',
        'profile.no_data': '❌ {user} hasn\'t hit any poles yet. Time to get on it!',
        'profile.no_data_local': '❌ {mention} hasn\'t bagged any poles on this server.',
        
        # Profile fields  
        'profile.field.season_current': '🎯 Current Season',
        'profile.field.rank_historical': '🏅 Historical Rank',
        'profile.field.rank_historical_server': '🏅 Historical Rank (Server)',
        'profile.field.total_points': '💰 Total Points',
        'profile.field.points_server': '💰 Points on this Server',
        'profile.field.total_poles': '🏁 Total Poles',
        'profile.field.poles_server': '🏁 Poles on this Server',
        'profile.field.current_streak': '{emoji} Current Streak',
        'profile.field.current_streak_global': '{emoji} Current Streak (Global)',
        'profile.field.best_streak': '{emoji} Best Streak',
        'profile.field.best_streak_global': '{emoji} Best Streak (Global)',
        'profile.field.streak_days': '{days} days',
        'profile.field.breakdown': '📈 Breakdown by Type',
        'profile.field.breakdown_server': '📈 Breakdown by Type (Server)',
        
        'profile.rank': '🏅 Rank',
        'profile.total_points': '💰 Total Points',
        'profile.total_poles': '🏁 Total Poles',
        'profile.current_streak': '<a:fire:1440018375144374302> Current Streak',
        'profile.best_streak': '⭐ Best Streak',
        'profile.days': '{days} days',
        'profile.breakdown': '💎 {critical} | ⚡ {fast} | 🏁 {normal} | 🐷 {marranero}',
        'profile.critical_poles': '⚡ Critical',
        'profile.fast_poles': '🏎️ Fast',
        'profile.normal_poles': '✅ Normal',
        'profile.marranero_poles': '🐷 Sleepyheads',
        'profile.speed_stats': '⏱️ Speed Stats',
        'profile.best_time': '🥇 Best Time',
        'profile.minutes': '{minutes} min',
        'profile.average_delay': '📊 Average Time',
        'profile.current_season': '🎯 Current Season ({season})',
        'profile.season_points': 'Points',
        'profile.season_poles': 'Poles',
        'profile.best_season': '🏆 Best Historical Season ({season})',
        'profile.represented_server': '🏳️ Repping',
        'profile.no_server': 'None',
        'profile.position': 'Your position: #{position} of {total}',
        'profile.title_local_detailed': '📊 {user}\'s Stats on {server}',
        'profile.footer.last_pole': 'Last pole: {date}',
        
        # Profile - Stats display
        'profile.stats.critical': '⚡ Critical: **{count}**',
        'profile.stats.fast': '🏎️ Fast: **{count}**',
        'profile.stats.normal': '🏁 Normal: **{count}**',
        'profile.stats.marranero': '🐷 Sleepyheads: **{count}**',
        
        # ==================== LEADERBOARD ====================
        'leaderboard.title': '🏆 {scope} LEADERBOARD - {type}',
        'leaderboard.scope.local': 'LOCAL',
        'leaderboard.scope.global': 'GLOBAL',
        'leaderboard.type.people': 'Players',
        'leaderboard.type.servers': 'Servers',
        'leaderboard.season': 'Season {season}',
        'leaderboard.lifetime': 'Lifetime',
        'leaderboard.server_desc': 'Server: {server}',
        'leaderboard.no_data': '❌ No stats {season}on this server yet.',
        'leaderboard.no_servers': '❌ No servers repping {season}yet.',
        'leaderboard.first_place': '🥇 First Place',
        'leaderboard.only_servers': '❌ This only works in servers, mate.',
        'leaderboard.stats': '💰 {points} pts • 🏁 {poles} poles',
        'leaderboard.stats_streak': '💰 {points} pts • 🏁 {poles} poles • <a:fire:1440018375144374302> {streak}',
        'leaderboard.position': 'Your spot: #{position} of {total}',
        'leaderboard.position_season': 'Your spot in {season}: #{position} of {total}',
        'leaderboard.no_users': '❌ No players on this server yet.',
        'leaderboard.no_users_streak': '❌ No players with streaks on this server yet.',
        'leaderboard.footer.use_local': 'Use /profile scope:local for this server\'s stats',
        
        # ==================== HISTORY ====================
        'history.title': '📜 Pole History - {user}',
        'history.no_data': '❌ You haven\'t hit any poles yet.',
        'history.pole_entry': '**{date}** - {type} ({delay})',
        'history.points': '{points} pts',
        'history.streak_at': 'Streak: {streak}',
        
        # ==================== MYSTATS ====================
        'mystats.title': '🏆 {user}\'s History',
        'mystats.no_season_data': 'You haven\'t hit any poles in {season} yet.\nGet started now and climb the ranks!',
        'mystats.no_badges': 'No badges earned yet.\nComplete a season to get your first badge!',
        'mystats.season_points': '💰 **Points:** {points}',
        'mystats.season_poles': '🏁 **Poles:** {poles}',
        'mystats.breakdown': '📈 Breakdown',
        'mystats.breakdown_entry': '⚡ Critical: {critical} | 🏎️ Fast: {fast} | 🏁 Normal: {normal} | 🐷 Sleepyheads: {marranero}',
        'mystats.field.status': 'Status',
        
        # ==================== MIDNIGHT SUMMARY ====================
        'midnight.streak_at_risk': '⚠️ **{count}** on the edge:\n\n',
        
        # ==================== MENTIONS ====================
        'mention.intro': 'Yo! I\'m the **Pole Bot** 🎬',
        'mention.description': 'Every day at a random time, the pole drops. Be first to type `pole` and rack up points!',
        'mention.setup': '**Setup**',
        'mention.setup_desc': 'Hit `/settings` to configure me',
        'mention.commands': '**Main Commands**',
        'mention.help': 'Need more help? Check the docs or hit up the support server.',
        
        # ==================== ONBOARDING ====================
        'onboarding.title': '🏁 Thanks for adding me!',
        'onboarding.intro': '**I\'m Pole Bot**, your assistant for competing to be the fastest every day.\n\n',
        'onboarding.language_default': '🌐 **Default language:** Spanish\n*(Switch it with `/settings` → Language)*\n\n',
        'onboarding.quick_setup': '**⚡ Quick Setup (3 steps):**\n1️⃣ Use `/settings` to pick the **pole channel**\n2️⃣ (Optional) Change **language** if you prefer English\n3️⃣ (Recommended) Set up a **ping role** for notifications\n\n',
        'onboarding.how_it_works': '**🎮 How it works:**\n• Every day the pole drops at a random time\n• First to type `pole` earns points\n• Keep consecutive streaks for multipliers\n• Compete locally and globally\n\n',
        'onboarding.commands': 'Use `/rules` to see the full rules. Good luck! 🏁',
        'onboarding.footer': 'May the fastest win! 🔥',
        
        'onboarding.bilingual_notice': '\n\n---\n\n🇪🇸 **¡Español disponible!** Usa `/settings` → Idioma para cambiar.\n**Default language:** Spanish',
        
        # ==================== EVENTS (Easter Eggs) ====================
        'events.first_message_channel': '🏁 POLE! First message in this channel! 🏁',
        'events.first_message_thread': '🏁 POLE! First message in this thread! 🏁',
        'events.welcome_member': 'Welcome {mention}! We\'re {count} pole hunters now. 🎬',
        
        # Command errors
        'events.error.no_permissions': '❌ You don\'t have permissions to use this command.',
        'events.error.missing_arg': '❌ Missing argument: {arg}',
        
        # ==================== ERRORS ====================
        'error.generic': '❌ Something went wrong. Give it another shot.',
        'error.no_permissions': '❌ You can\'t do that, chief.',
        'error.dm_not_supported': '❌ This doesn\'t work in DMs.',
        
        # ==================== ERRORES CRÍTICOS ====================
        'errors.configure_channel': '⚙️ Set up the pole channel first with `/settings`.',
        'errors.no_time_configured': '⚠️ No pole time set for today.',
        'errors.invalid_time_config': '⚠️ Invalid time config. Hit up an admin.',
        'errors.command_server_only': '❌ This command only works in servers.',
        'errors.no_mutual_servers': '❌ You\'re not in any server where I am.',
        'errors.server_only_short': '❌ Server only.',
        'errors.no_permissions_check': '❌ Couldn\'t check your permissions in this server.',
        'errors.no_users': '❌ No users in this server yet.',
        'errors.no_streaks': '❌ No users with streaks in this server yet.',
        
        # ==================== SETTINGS UI ====================
        'ui.select_channel': 'Select the pole channel',
        'ui.select_role': 'Select the ping role',
        'ui.select_server': 'Pick a server...',
        'ui.select_option': 'Choose what to configure...',
        'ui.button.refresh': 'Refresh View',
        
        # Options del menú settings
        'ui.option.channel.label': 'Pole Channel',
        'ui.option.channel.desc': 'Change where poles happen',
        'ui.option.language.label': 'Language',
        'ui.option.language.desc': 'Change bot language',
        'ui.option.ping_role.label': 'Ping Role',
        'ui.option.ping_role.desc': 'Set up notification role',
        'ui.option.clear_ping.label': 'Remove Ping Role',
        'ui.option.clear_ping.desc': 'Clear ping role',
        'ui.option.notify_open.label': 'Toggle Opening Notif',
        'ui.option.notify_open.desc': 'Turn on/off opening alerts',
        'ui.option.notify_winner.label': 'Toggle Winner Notif',
        'ui.option.notify_winner.desc': 'Turn on/off winner alerts',
        'ui.option.represent.label': 'Change Representation',
        'ui.option.represent.desc': 'Server you rep in global rankings',
        
        # Embeds de configuración
        'ui.language.title': '🌐 Change Language',
        'ui.language.desc': 'Current language: **{current}**\n\nPick a new language for the bot:',
        'ui.language.button.es': 'Español',
        'ui.language.button.en': 'English',
        'ui.represent.title': '🏳️ Change Representation',
        'ui.represent.desc': 'Pick which server you want to represent in global rankings.',
        'ui.settings.desc': 'Select options to configure using the dropdown menu',
        'ui.select_role_prompt': '🔔 Pick the ping role:',
        'ui.select_channel_prompt': '📺 Select the pole channel:',
        'ui.represent.current': '📍 Currently Repping',
        'ui.represent.none': '*No server set*',
        
        # ==================== NOTIFICACIONES ====================
        'notification.pole_open': '🔔 POLE IS OPEN',
        'notification.pole_open_recovery': '🔔 POLE IS OPEN (Recovery)',
        'notification.pole_open_recovery_desc': '⚠️ Bot was offline during scheduled opening.\nType **pole** now to earn points 🏁',
        'notification.pole_open_desc': 'Time to drop that **pole** and rack up points 🏁\nFirst one wins, rest just watch.',
        'notification.pole_open_footer': 'Let the race begin ✨',
        'notification.streak_lost': '💔 Streak Lost',
        'notification.streak_lost_desc': '{names}\nStreak reset for not completing yesterday.',
        'notification.daily_summary': '🌃 Daily Summary',
        'notification.daily_summary_desc': '**{count}** members hit their pole yesterday',
        
        # ==================== LEADERBOARD ====================
        'leaderboard.title.local_people': '🏆 LOCAL LEADERBOARD - Players - {season}',
        'leaderboard.title.local_servers': '🏆 LOCAL LEADERBOARD - Servers - {season}',
        'leaderboard.title.local_streaks': '<a:fire:1440018375144374302> STREAKS LEADERBOARD - Local',
        'leaderboard.title.global_people': '🌍 GLOBAL LEADERBOARD - Players - {season}',
        'leaderboard.title.global_servers': '🌍 GLOBAL LEADERBOARD - Servers - {season}',
        'leaderboard.title.global_streaks': '<a:fire:1440018375144374302> STREAKS LEADERBOARD - Global',
        
        'leaderboard.desc.local_people': 'Server: {server}',
        'leaderboard.desc.local_servers': 'Servers repped by members of {server}',
        'leaderboard.desc.local_streaks': 'Server: {server}\n*(Streaks are global across all servers)*',
        
        'leaderboard.footer.position': 'Your spot: #{pos} of {total}',
        'leaderboard.footer.position_season': 'Your spot in {season}: #{pos} of {total}',
        'leaderboard.footer.streak_position': 'Your spot: #{pos} • Your streak: {streak} days',
        'leaderboard.footer.use_local': 'Use /profile scope:local to see this server\'s stats',
        'leaderboard.footer.use_global': 'Use /profile scope:global to see global stats',
        
        'leaderboard.no_data_local': '❌ No local data yet{season_info}.',
        'leaderboard.no_data_global': '❌ No global data yet{season_info}.',
        'leaderboard.no_data_servers': '❌ No servers repped {season_info} yet.',
        'leaderboard.no_data_streaks_global': '❌ No streaks recorded yet.',
        
        # Entry format
        'leaderboard.entry.members': '👥 {count} members',
        'leaderboard.entry.current_streak': 'Current: **{current}** days',
        'leaderboard.entry.best_streak': 'Best: **{best}** days',
        
        # ==================== PROFILE ====================
        'profile.title.global': '🌍 Global Profile of {user}',
        'profile.title.local': '📍 Local Profile of {user}',
        
        'profile.field.season_rank': '🏆 Season Rank',
        'profile.field.season_rank_value': '{emoji} **{name}**\n💰 {points} pts this season',
        'profile.field.rank': '🏆 Rank',
        'profile.field.rank_value': '{emoji} **{name}**\n(Best season: {best_points} pts)',
        'profile.field.total_points': '💰 Total Points',
        'profile.field.total_poles': '🏁 Total Poles',
        'profile.field.current_streak': '<a:fire:1440018375144374302> Current Streak',
        'profile.field.best_streak': '⭐ Best Streak',
        'profile.field.server_represented': '🏳️ Server Repping',
        'profile.field.server_rep_none': 'Not set',
        
        'profile.footer.last_pole': 'Last pole: {date}',
        'profile.footer.no_poles': 'Haven\'t hit any poles yet',
        
        # Profile - Streak
        'profile.streak.current_title': '{emoji} Current Streak',
        'profile.streak.current_value': '**{days}** consecutive days\nMultiplier: **x{multiplier:.1f}**',
        
        # Profile - POLE REWIND
        'rewind.streak_value': '<@{uid}> - **{streak}** consecutive days',
        
        # ==================== HISTORY ====================
        'history.title': '📜 Pole History - {user}',
        'history.no_poles': '❌ You haven\'t hit any poles yet.',
        'history.footer': 'Page {current} of {total}',
        'history.entry': '{emoji} **{type}** • {delay} • {date}\n{points} pts • Server: {server}',
        
        # ==================== MISC ====================
        'common.yes': 'Yes',
        'common.no': 'No',
        'common.enabled': '✅ On',
        'common.disabled': '❌ Off',
        'common.none': 'None',
        'common.loading': 'Loading...',
        'common.pts': 'pts',
        'common.poles': 'poles',
        
        # ==================== MIGRATION ====================
        'migration.in_progress': '⚠️ **Season Migration In Progress**\n\nPole system temporarily disabled while migrating to the new season.\nBe back in a few.',
        
        # ==================== NOTIFICATIONS (más) ====================
        'notification.recovery_footer': 'Original opening: {time}',
        
        # ==================== POLEHELP ====================
        'help.title': '📖 Pole Bot - Quick Guide',
        'help.description': 'Compete daily to type **pole** ASAP after the daily opening',
        'help.how_to_play': '🎮 How to Play',
        'help.how_to_play_desc': '1. Wait for **opening notification** (random time daily)\n2. Type exactly **`pole`** in the configured channel\n3. Earn points based on speed!\n⚠️ Only 1 pole per day, across all servers',
        'help.categories': '🏆 Pole Categories',
        'help.categories_desc': '💎 **Critical** (0-10 min): 20 pts\n    └ Only 10% of server can claim it\n⚡ **Fast** (10 min - 3h): 15 pts\n    └ Only 30% of server can claim it\n🏁 **Normal** (3h - 00:00): 10 pts\n    └ No user limit\n🐷 **Sleepyhead** (next day): 5 pts\n    └ No user limit',
        'help.streaks': '<a:fire:1440018375144374302> Streak System',
        'help.streaks_desc': 'Hit poles on consecutive days to increase your multiplier\n• 7 days: x1.1\n• 30 days: x1.4\n• 90 days: x1.8\n• 300 days: x2.5 (max)',
        'help.commands': '⚙️ Commands',
        'help.commands_desc': '`/profile` - View your profile and stats\n`/leaderboard` - View rankings (local/global, players/servers)\n`/streak` - Detailed streak info\n`/season` - View current season and your progress\n`/history` - View badges and past seasons\n`/settings` - Configure the bot (admins)\n`/polehelp` - View this help',
        'help.footer': 'Good luck, may the fastest win! 🔥',
        
        # ==================== SEASON ====================
        'season.official': '🏆 **Official Season**',
        'season.practice': '🎯 **Practice Season**',
        'season.status': 'Status',
        'season.time_remaining': '⏰ Time Remaining',
        'season.days_left': '**{days}** days',
        'season.finished': '**Finished**',
        'season.your_progress': '📊 Your Progress in {season}',
        'season.your_progress_desc': '🎖️ **Rank:** {emoji} {name}\n💰 **Points:** {points}\n🏁 **Poles:** {poles}\n<a:fire:1440018375144374302> **Best Streak:** {streak} days',
        'season.breakdown': '📈 Breakdown',
        'season.breakdown_desc': '💎 Critical: {critical} | ⚡ Fast: {fast}\n🏁 Normal: {normal} | 🐷 Sleepyheads: {marranero}',
        'season.no_poles': 'You haven\'t hit any poles in {season} yet.\nStart now and climb the ranks!',
        'season.footer': 'Use /history to view past seasons 🔥',
        'season.period': '**Period:** {start} → {end}',
        
        # ==================== MYSTATS (History) ====================
        'mystats.title': '🏆 History of {user}',
        'mystats.description': 'Your legacy through the seasons',
        'mystats.badges': '🏅 Badge Collection',
        'mystats.no_badges': 'No badges earned yet.\nComplete a season to get your first badge!',
        'mystats.seasons': '📜 Completed Seasons',
        'mystats.no_seasons': 'No completed seasons yet.\nKeep playing and leave your mark!',
        'mystats.season_entry': '**{name}** ({year})\n🎖️ Rank: {rank} | 💰 {points} pts | #{pos} of {total}\n🏁 {poles} poles | <a:fire:1440018375144374302> Best streak: {streak}',
        
        # ==================== STREAK COMMAND ====================
        'streak.off': '<:gray_fire:1445324596751503485> Streak Off',
        'streak.off_desc': '0-day streak. Light it up with a pole today.',
        'streak.best': '🏆 Your Best Streak',
        'streak.best_value': '**{streak}** days',
        'streak.next_milestone': '🎯 Next Milestone',
        'streak.next_milestone_value': '{milestone} days (**{days}** days left)\nMultiplier: x{multiplier:.1f}',
        'streak.last_pole': '📅 Last Pole',
        'streak.last_pole_today': 'Today ✅',
        'streak.last_pole_yesterday': 'Yesterday',
        'streak.last_pole_days_ago': '{days} days ago',
        
        # ==================== POLE REWIND (Season Change) ====================
        'rewind.intro_first_title': '🎆 HAPPY NEW YEAR, EARLY POLERS! 🎆',
        'rewind.intro_first_desc': 'What a wild year, fam.\n\nYou\'re the **PIONEERS**. The ones who believed in this bot when it was just a random experiment. The ones who dealt with bugs, broken streaks, crazy pole times... and **STILL** stuck around.\n\nThis was just the **WARM-UP**. The pre-season. The tutorial.\n\nNow comes the **POLE REWIND {season}**. Let\'s remember who the legends were. 🎬',
        'rewind.intro_title': '🎆 HAPPY NEW YEAR, POLERS! 🎆',
        'rewind.intro_desc': 'Another year, another battle won.\n\nThanks to everyone who made pole part of their daily routine. Every 3am pole, every last-second saved streak, every epic moment... **THAT\'S** what makes this community what it is.\n\nTime for the **POLE REWIND {season}**. 🎬',
        'rewind.local_points_title': '👑 TOP SCORERS - {server}',
        'rewind.local_points_desc': 'Who racked up the most points this season:',
        'rewind.local_poles_title': '⚡ POLE MANIACS - {server}',
        'rewind.local_poles_desc': 'Who hit first the most times:',
        'rewind.local_streaks_title': '<a:fire:1440018375144374302> MAX DISCIPLINE - {server}',
        'rewind.local_streaks_desc': 'Who kept the longest streaks:',
        'rewind.local_speed_title': '⚡ SPEED DEMONS - {server}',
        'rewind.local_speed_desc': 'Fastest average times (min 10 poles):',
        'rewind.global_title': '🌍 GLOBAL HALL OF FAME',
        'rewind.global_desc': 'The legends who dominated **ALL** servers in {season}:',
        'rewind.global_points': '**👑 Top Scorers**',
        'rewind.global_poles': '**⚡ Pole Maniacs**',
        'rewind.global_streaks': '**<a:fire:1440018375144374302> Max Discipline**',
        'rewind.global_speed': '**⚡ Speed Demons** (min 10 poles)',
        'rewind.footer_hof': 'Hall of Fame {season} • {tagline}',
        'rewind.footer_global': 'Pole Bot Legends • God Tier',
        'rewind.no_data': '_Nobody competed in this category._',
        'rewind.no_data_speed': '_Not enough data._',
        'rewind.no_data_global': '_No global data for this season._',
        
        # Hall of Fame taglines
        'rewind.tagline.points': 'Consistency pays off.',
        'rewind.tagline.poles': 'Always there.',
        'rewind.tagline.streaks': 'Discipline is power.',
        'rewind.tagline.speed': 'Champion reflexes.',
        
        # Hall of Fame values
        'rewind.points_value': '<@{uid}> - **{points:,}** pts',
        'rewind.poles_value': '<@{uid}> - **{count}** poles',
        'rewind.streak_value': '<@{uid}> - **{streak}** days straight',
        'rewind.speed_value': '<@{uid}> - **{delay:.1f}** min avg',
        
        # New season messages
        'rewind.new_season_first_title': '🚀 WELCOME TO {season}',
        'rewind.new_season_first_desc': 'The beta is over. Now it\'s **FOR REAL**.\n\nThis is the official **SEASON 1** of Pole Bot. Everything before was practice.\n\n♻️ Points to 0. Streaks to 0.\n💎 Your BETA badges stay with you.\n\nEveryone starts equal. May the most determined win.\n\nThe official competition starts... **NOW**. 🏁',
        'rewind.new_season_title': '🚀 WELCOME TO {season}',
        'rewind.new_season_desc': 'Time to stop looking back. From today, clean slate:\n\n♻️ Points reset to 0\n♻️ Streaks reset to 0\n💎 Your badges stay with you (honor)\n\n{season} starts **NOW**. Everyone starts from zero, same chances.\n\nMay the best win. 🏁',
        'rewind.new_season_duration': '📅 Season Duration',
        'rewind.new_season_duration_value': 'From **{start}** to **{end}**',
        'rewind.new_season_footer': 'Let the competition begin! 🔥',
        
        # ==================== MIDNIGHT SUMMARY ====================
        'summary.new_day': '🌅 New Day',
        'summary.new_day_desc': 'New day starts: wait for the ping and go pole.',
        'summary.footer': 'Automatic summary • No pings',
        'summary.completed_yesterday': '✅ Completed Yesterday\'s Pole',
        'summary.streak_at_risk': '⏳ Streak at Risk',
        'summary.streak_at_risk_desc': '⚠️ **{count}** on the edge:\n\n{users}\n\n🐷 You can still get the **late pole** until next opening.',
        'summary.user_streak': '⏳ {mention} ({streak}-day streak)',
        'summary.and_more': '_...and {count} more_',
        'summary.pole_elsewhere': '🌍 Poled on Another Server ({count})',
        'summary.user_elsewhere': '🌍 {mention} on **{guild}** ({streak}-day streak)',
        
        # ==================== POLE REWIND DEDICATIONS ====================
        # Local Dedications
        'dedication.points.1': 'The King of Consistency',
        'dedication.points.2': 'Second but Lethal',
        'dedication.points.3': 'Bronze with Honor',
        
        'dedication.poles.1': 'Supreme Pole Maniac',
        'dedication.poles.2': 'Always Second, Never Forgotten',
        'dedication.poles.3': 'Elite Competition',
        
        'dedication.streak.1': 'Discipline Incarnate',
        'dedication.streak.2': 'Consistency of Steel',
        'dedication.streak.3': 'Unbreakable Will',
        
        'dedication.speed.1': 'Lightning Reflexes',
        'dedication.speed.2': 'Supersonic Speed',
        'dedication.speed.3': 'Fast as the Wind',
        
        # Global Dedications
        'dedication.points_global.1': 'The Point Titan',
        'dedication.points_global.2': 'Living Legend',
        'dedication.points_global.3': 'Competitive Beast',
        
        'dedication.poles_global.1': 'God-Tier Obsession',
        'dedication.poles_global.2': 'Pure Addiction',
        'dedication.poles_global.3': 'Forever Top Tier',
        
        'dedication.streak_global.1': 'Superhuman Commitment',
        'dedication.streak_global.2': 'Never Misses',
        'dedication.streak_global.3': 'Total Dedication',
        
        'dedication.speed_global.1': 'Speed of Light',
        'dedication.speed_global.2': 'The Flash Himself',
        'dedication.speed_global.3': 'Inhuman Reflexes',
        
        # ==================== RANK NAMES ====================
        'rank.bronze': 'Bronze - Rookie',
        'rank.silver': 'Silver - Contender',
        'rank.gold': 'Gold - Competitor',
        'rank.diamond': 'Diamond - Veteran',
        'rank.amethyst': 'Amethyst - Master',
        'rank.ruby': 'Ruby - Legend',
        
        # ==================== BUTTONS ====================
        'button.refresh': 'Refresh View',
        
        # ==================== DOWNTIME COMPENSATION ====================
        'compensation.apology_title': '🛠️ Apologies for the Downtime',
        'compensation.apology_desc': 'The bot was down on **{date}** due to technical issues.\n\n**{count} users** have been automatically compensated:\n• ✅ Normal pole granted retroactively\n• {fire} Streaks maintained/activated\n• 🏆 Season points added\n\n**Thanks for your patience.** 🙏',
        'compensation.apology_footer': 'Global automatic compensation • {count} users',
    }
}

# ==================== FUNCIÓN PRINCIPAL ====================

# Singleton de Database para evitar crear instancias en cada llamada a t()
_db_instance = None

def _get_db():
    """Obtener instancia singleton de Database para i18n"""
    global _db_instance
    if _db_instance is None:
        from utils.database import Database
        _db_instance = Database()
    return _db_instance

def t(key: str, guild_id: Optional[int] = None, lang: Optional[str] = None, **kwargs: Any) -> str:
    """
    Traduce un string según el idioma del servidor
    
    Args:
        key: Clave de traducción (ej: 'pole.critical')
        guild_id: ID del servidor (para obtener idioma configurado)
        lang: Idioma forzado (opcional, si no se pasa guild_id)
        **kwargs: Variables para formatear el string
    
    Returns:
        String traducido y formateado
    
    Ejemplos:
        t('pole.critical', guild_id=123, minutes=5)
        t('settings.title', lang='en')
        t('common.yes', guild_id=456)
    """
    # Determinar idioma
    if lang is None:
        if guild_id is not None:
            db = _get_db()
            lang = db.get_server_language(guild_id)
        else:
            lang = 'es'  # Default
    
    # Obtener traducción
    lang_dict = TRANSLATIONS.get(lang, TRANSLATIONS['es'])
    template = lang_dict.get(key, key)  # Si no existe, devuelve la key
    
    # Si el template es una lista, elegir uno aleatorio (variaciones)
    if isinstance(template, list):
        template = random.choice(template)
    
    # Formatear con kwargs si se proveen
    if kwargs:
        try:
            return template.format(**kwargs)
        except KeyError as e:
            # Si falta una variable, devolver template sin formatear
            print(f"⚠️ Missing variable {e} in translation key '{key}'")
            return template
    
    return template


def get_available_languages() -> List[str]:
    """Retorna lista de idiomas disponibles"""
    return list(TRANSLATIONS.keys())


def get_language_name(lang_code: str) -> str:
    """Retorna nombre legible del idioma"""
    names = {
        'es': 'Español',
        'en': 'English'
    }
    return names.get(lang_code, lang_code)
