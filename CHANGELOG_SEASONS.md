# 🎮 Changelog - Sistema de Seasons v1.0

## ✅ Implementado (17 Nov 2025)

### 1. Sistema de Badges Custom
- **6 rangos progresivos** con emojis custom de Discord:
  - 🟤 Bronce (0-500 pts) - Iniciado
  - ⬜ Plata (500-1,500 pts) - Aspirante  
  - 🟡 Oro (1,500-3,500 pts) - Competidor
  - 🔷 Diamante (3,500-6,000 pts) - Veterano
  - 🟣 Amatista (6,000-9,000 pts) - Maestro
  - 🔻 Rubí (9,000+ pts) - Leyenda

- **IDs integrados en `utils/scoring.py`:**
  ```python
  BADGE_BRONZE = "<:badge_6:1440023135524094046>"
  BADGE_SILVER = "<:badge_5:1440023137348751370>"
  BADGE_GOLD = "<:badge_4:1440023138707439708>"
  BADGE_DIAMOND = "<:badge_3:1440023140423041168>"
  BADGE_AMETHYST = "<:badge_2:1440023141563895930>"
  BADGE_RUBY = "<:badge_1:1440023143283429456>"
  ```

- **Badges aparecen en:**
  - Leaderboards (al lado del nombre)
  - Comando `/stats`
  - Mensajes de victoria
  - Resumen de mediodía

### 2. Sistema de Temporadas (Seasons)
**Estructura automática:**
- **Pre-Temporada**: Nov-Dic 2025 (warmup, no oficial)
- **Season 1**: 1 Ene 2026 - 31 Dic 2026 (oficial)
- **Seasons futuras**: Auto-generadas cada año

**Tablas de DB creadas:**
- `seasons` - Configuración de temporadas
- `season_stats` - Estadísticas por season (se resetea)
- `season_history` - Historial permanente de seasons finalizadas
- `user_badges` - Colección de badges ganados

**Funcionalidad automática:**
- Reset a medianoche del 1 de enero
- Badges otorgados según rango final
- Historial preservado para siempre
- Detección automática de season actual

### 3. Resumen de Mediodía
**Nuevo sistema a las 12:00:**
- 📊 Tabla resumen con jugadores que hicieron pole hoy
- 🔥 Recordatorio a jugadores con racha activa
- 🐷 Info sobre pole marranero (sin pings)
- Loop cada 5 minutos entre 12:00-12:15

**Aparece en:** Canal configurado de cada servidor

### 4. Sistema Debug Simplificado
**Eliminado:**
- ❌ Tablas duales (debug_users, debug_poles)
- ❌ Toggle entre modos
- ❌ Comando copy_to_debug

**Mantenido y mejorado:**
- ✅ `/debug set_opening` - Forzar hora de apertura
- ✅ `/debug simulate_pole` - Simular poles **ESCRIBE EN PRODUCCIÓN**
- ✅ `/debug represent` - Cambiar representación
- ✅ `/debug notify_opening` - Test de notificación
- ✅ `/debug clear` - Resetear servidor completo

**Nota importante:** Todos los comandos debug ahora escriben directamente en producción. Ideal para testing con datos reales.

### 5. Emoji de Fuego Custom
- Reemplazado 🔥 estándar por `<a:fire:1440018375144374302>` en TODO el bot
- Constante `FIRE` en `cogs/pole.py` y `cogs/debug.py`
- Aparece en: rachas, mensajes, embeds, footers

### 6. Ajustes de Configuración Mejorados
**Cambios de seguridad:**
- Hora de apertura **OCULTA** en `/settings` (evita spoilers)
- Menú dinámico según permisos:
  - **Admins**: ven y cambian canal, ventana, pings, notificaciones
  - **Usuarios**: solo pueden cambiar representación
- `/settings` accesible para todos pero opciones filtradas

### 7. Notificaciones Exactas
**Nuevo sistema de scheduler:**
- Notificaciones enviadas en el **segundo exacto** de apertura
- `asyncio.sleep` hasta hora exacta por servidor
- Sin sondeos periódicos (eliminado loop de 30s)
- Auto-reprogramación al cambiar hora con `/debug set_opening`

## 📁 Archivos Modificados

### Nuevos
- `scripts/migrate_seasons.py` - Script de migración de DB
- `CHANGELOG_SEASONS.md` - Este archivo

### Modificados
- `utils/scoring.py` - Badges, rangos, detección de seasons
- `utils/database.py` - Métodos de seasons, eliminado modo debug
- `cogs/pole.py` - Resumen mediodía, scheduler exacto, ajustes filtrados, emoji FIRE
- `cogs/debug.py` - Simplificado, escribe en producción, emoji FIRE

## 🚀 Cómo Usar

### Arrancar el bot
```powershell
python .\main.py
```

### Testing con Debug
```
1. /debug set_opening hora:14 minuto:30
   → Fija hora de apertura (reprograma notificación automáticamente)

2. /debug simulate_pole delay_minutos:5
   → Simula un pole crítico (0-10 min)
   → ESCRIBE EN PRODUCCIÓN, no necesitas hacer pole real

3. /stats
   → Ver tu badge y puntos de season

4. /leaderboard alcance:local tipo:personas
   → Ver ranking con badges
```

### Ver Resumen de Mediodía
- Espera hasta las 12:00 (o simula con `/debug notify_opening`)
- Aparecerá automáticamente en canal configurado

### Resetear Datos
```
/debug clear
→ Borra todos los datos del servidor (producción)
→ Úsalo para empezar limpio
```

## 📊 Próximas Features (No Implementadas)

### Comandos de Season
- [ ] `/season` - Ver info de season actual y progreso personal
- [ ] `/history` - Ver badges de seasons anteriores
- [ ] `/season_leaderboard` - Ranking de season vs all-time

### Integración en Comandos Existentes
- [ ] Actualizar `/stats` para mostrar:
  - Badge de season actual
  - Colección de badges históricos
  - Progreso a próximo rango
- [ ] Actualizar `/leaderboard` para:
  - Mostrar badges al lado de nombres
  - Filtrar por season específica

## 🐛 Notas de Testing

**Base de datos migrada:** ✅
- 2 usuarios existentes copiados a `season_stats`
- Pre-temporada activada
- Ready para testing

**Comandos funcionales:**
- ✅ `/settings` (filtrado por permisos)
- ✅ `/debug set_opening` (reprograma notificación)
- ✅ `/debug simulate_pole` (escribe en producción)
- ✅ Notificaciones exactas (sin delay)
- ✅ Resumen de mediodía (loop activo)

**Pendiente de testing:**
- Verificar badges aparecen correctamente en Discord
- Confirmar resumen de mediodía a las 12:00
- Testear reset automático de season (1 ene 2026)
