# 📚 Documentación Pole Bot v1.0

Bienvenido a la documentación completa del **Pole Bot v1.0**. Aquí encontrarás toda la información sobre el funcionamiento, configuración y uso del bot.

---

## 📖 Índice de Documentación

### 🎨 Diseño y Arquitectura
- **[DESIGN.md](DESIGN.md)** - Arquitectura completa del sistema
  - Sistema de hora aleatoria
  - Base de datos y tablas
  - Flujo de eventos y tasks
  - Prevención de spam multi-servidor

### 💰 Sistema de Puntos
- **[SCORING.md](SCORING.md)** - Sistema de puntuación detallado
  - Categorías y puntos por velocidad
  - Sistema de cuotas (10% crítica, 30% veloz)
  - Multiplicadores de racha (x1.0 a x2.5)
  - Cálculo de puntos finales

### 📜 Reglas del Juego
- **[RULES.md](RULES.md)** - Reglas oficiales del Pole Bot
  - Cómo funciona el juego
  - Restricciones y límites
  - Rachas y cómo mantenerlas
  - Penalizaciones y resets

### 🎖️ Logros y Badges
- **[ACHIEVEMENTS.md](ACHIEVEMENTS.md)** - Sistema de logros
  - Badges de temporada (Top 3 final)
  - Rangos por puntos (Rubí, Diamante, Oro...)
  - Logros especiales
  - Cómo obtenerlos

### 🏆 Sistema de Temporadas
- **[SEASONS.md](SEASONS.md)** - Temporadas competitivas
  - Ciclo anual (1 enero - 31 diciembre)
  - Migración automática de temporadas
  - Historial y estadísticas
  - Leaderboards por temporada

### 🔔 Notificaciones
- **[NOTIFICATIONS.md](NOTIFICATIONS.md)** - Sistema de avisos
  - Notificación de apertura
  - Resumen de medianoche
  - Pole marranero
  - Configuración de pings

### 💬 Comandos
- **[COMMANDS.md](COMMANDS.md)** - Lista completa de comandos
  - Comandos de usuario
  - Comandos de administración
  - Comandos de debug (desarrollo)

---

## 🚀 Inicio Rápido

### Para Usuarios
1. Espera la notificación de apertura del pole
2. Escribe `pole` lo más rápido posible
3. Gana puntos según tu velocidad
4. Mantén tu racha haciendo pole diariamente

### Para Administradores
1. Usa `/settings` para configurar:
   - Canal de pole
   - Rango horario (ej: 12:00-20:00)
   - Rol de ping (opcional)
   - Notificaciones
2. El bot generará una hora aleatoria cada día
3. Los usuarios podrán competir automáticamente

---

## 📊 Conceptos Clave

### Hora Aleatoria
El bot genera una hora diferente cada día dentro del rango configurado. Esto mantiene la competencia fresca y evita que los usuarios memoricen horarios.

### Sistema de Cuotas
Las categorías premium (Crítica y Veloz) tienen límites:
- **Crítica**: Solo 10% del servidor puede reclamarla
- **Veloz**: Solo 30% del servidor puede reclamarla

Si la cuota está llena, se degrada automáticamente a la siguiente categoría disponible.

### Rachas
Hacer pole **diariamente** aumenta tu racha y tu multiplicador de puntos. Perder un día resetea tu racha a 0.

### Temporadas
Cada año es una temporada competitiva. Al finalizar el año:
- Se guardan posiciones finales
- Se otorgan badges permanentes
- Se resetean puntos de temporada
- Se mantienen estadísticas lifetime

---

## 🛠️ Configuración Técnica

### Variables de Entorno
```env
# Discord
DISCORD_TOKEN=tu_token_aqui
DISCORD_CLIENT_ID=tu_client_id

# Debug (opcional)
DEBUG=0
DEBUG_ALLOWLIST=123456789,987654321
```

### Base de Datos
El bot usa SQLite3 con las siguientes tablas principales:
- `users` - Datos de usuarios y rachas
- `poles` - Historial de poles
- `seasons` - Configuración de temporadas
- `season_stats` - Estadísticas por temporada
- `season_history` - Historial de temporadas finalizadas
- `user_badges` - Badges permanentes ganados
- `servers` - Configuración por servidor

### Requisitos
- Python 3.10+
- discord.py 2.3.2+
- SQLite3 (incluido en Python)

---

## 🎮 Flujo del Juego

```
1. 🌅 Inicio del día
   ↓
2. 🎲 Bot genera hora aleatoria (margen mínimo 4h del día anterior)
   ↓
3. ⏰ Hora de apertura
   ↓
4. 🔔 Bot envía notificación de apertura
   ↓
5. 🏃 Usuarios escriben "pole"
   ↓
6. ⚡ Bot calcula velocidad y asigna categoría
   ↓
7. 🎯 Verifica cuotas y aplica multiplicador de racha
   ↓
8. 💰 Otorga puntos y actualiza estadísticas
   ↓
9. 🌙 Medianoche: Resumen del día
   ↓
10. 🔄 Ciclo se repite
```

---

## 📝 Notas Importantes

### Prevención de Spam
- **Una pole por día** por usuario a nivel global
- Si ya hiciste pole en otro servidor, no podrás en otro el mismo día
- Esto mantiene la competencia justa y evita abuso

### Margen Mínimo
El sistema garantiza al menos **4 horas** entre la apertura de un día y el siguiente. Esto asegura que todos tengan tiempo suficiente para reclamar el pole anterior antes del siguiente.

### Resumen de Medianoche
A las 00:00 el bot envía un resumen automático:
- Quién ganó el pole del día anterior
- Quién perdió su racha
- Anuncia el nuevo día

### Migración de Temporadas
El 1 de enero a las 00:00, el bot automáticamente:
1. Finaliza la temporada anterior
2. Guarda posiciones finales en historial
3. Otorga badges a los Top 3
4. Crea y activa la nueva temporada
5. Resetea rachas pero mantiene estadísticas lifetime

---

## 🔧 Comandos Rápidos

| Comando | Descripción |
|---------|-------------|
| `/profile` | Ver tus estadísticas |
| `/leaderboard` | Rankings del servidor |
| `/settings` | Configurar bot (admin) |
| `/polehelp` | Ayuda y tutoriales |

---

## 📞 Soporte

Si encuentras bugs o tienes sugerencias, abre un issue en el repositorio de GitHub.

---

**Versión:** 1.0  
**Última actualización:** Diciembre 2024
