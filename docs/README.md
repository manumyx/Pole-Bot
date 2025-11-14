# 📚 Documentación del Pole Bot

Bienvenido a la documentación técnica del Pole Bot. Esta guía está organizada en módulos temáticos para facilitar la navegación y colaboración.

## 📖 Índice de Documentación

### [DESIGN.md](DESIGN.md) - Documento Maestro
Referencia técnica completa del proyecto. Contiene toda la información consolidada en un solo lugar para consulta técnica profunda.

**Cuándo consultarlo:**
- Necesitas una visión completa del sistema
- Buscas detalles técnicos específicos de implementación
- Quieres entender la arquitectura general

---

### [RULES.md](RULES.md) - Reglas y Validaciones
Todo lo relacionado con las reglas del pole, validaciones y sistema de penalizaciones.

**Contenido:**
- ✅ Validación de poles (horarios, condiciones)
- 🏷️ Tipos de pole (Crítica, Secundón, Normal, Marranero)
- ⚠️ Sistema de strikes (3 strikes progresivos)
- 🛡️ Anti-trampas (anti-bot, anti-spam, anti-macros)
- 💀 Penalizaciones y suspensiones temporales

**Para desarrolladores:**
- Implementar lógica de validación en `cogs/pole.py`
- Gestión de strikes en base de datos
- Detección de comportamiento sospechoso

---

### [SCORING.md](SCORING.md) - Sistema de Puntos
Cálculo de puntos, rachas, multiplicadores y sistema de rangos.

**Contenido:**
- 💰 Puntos base por tipo de pole (20/11/10/7)
- 🔥 Sistema de rachas (hasta 2.5× multiplicador)
- 📊 Tabla de hitos de racha (1→365 días)
- 🏆 Sistema de rangos (Novato → Inmortal)
- 📈 Fórmula de puntos: `Base × Multiplicador`

**Para desarrolladores:**
- Implementar cálculo de puntos en `utils/scoring.py`
- Gestión de rachas en base de datos
- Sistema de progresión de rangos

---

### [ACHIEVEMENTS.md](ACHIEVEMENTS.md) - Logros y Recompensas
Todos los logros del bot: públicos, especiales y ocultos.

**Contenido:**
- 🎯 20+ logros públicos (El Imparable, Crítico en Serie, Vampiro...)
- 🎁 Logros especiales por hitos (Centurión, Inmortal...)
- 🤫 15 logros ocultos (EL NANO?????????, 4:20, 69, 404...)
- 💬 Mensajes de desbloqueo personalizados
- 📊 Sistema de rareza dinámico

**Para desarrolladores:**
- Implementar detección de logros en `utils/achievements.py`
- Triggers de desbloqueo
- Notificaciones de logros

---

### [COMMANDS.md](COMMANDS.md) - Referencia de Comandos
Lista completa de comandos slash, permisos y configuración.

**Contenido:**
- 👤 Comandos de usuario (`/pole`, `/stats`, `/leaderboard`)
- 👑 Comandos de administrador (`/polereset`, `/polestrike`, `/poleping`)
- ℹ️ Comandos de información (`/polehelp`, `/achievements`)
- ⚙️ Panel de configuración del bot
- 🔔 Sistema de notificaciones y menciones

**Para desarrolladores:**
- Implementar comandos en `cogs/pole.py`
- Sistema de permisos y roles
- UI de leaderboards y embeds

---

### [NOTIFICATIONS.md](NOTIFICATIONS.md) - Personalidad y Mensajes
Tono del bot, notificaciones y easter eggs.

**Contenido:**
- 🎭 Personalidad del bot (tono directo, humor auténtico)
- 🔔 Notificaciones de reset y victoria
- 🎉 Mensajes especiales (récords, empates, rachas)
- 🥚 Easter eggs y respuestas contextuales
- ⚙️ Configuración de notificaciones

**Para desarrolladores:**
- Implementar mensajes en `utils/messages.py`
- Sistema de respuestas dinámicas
- Easter eggs condicionales

---

## 🔧 Guía Rápida por Rol

### Para Contribuidores Nuevos
1. Lee [RULES.md](RULES.md) para entender la mecánica básica
2. Revisa [SCORING.md](SCORING.md) para el sistema de puntos
3. Consulta [COMMANDS.md](COMMANDS.md) para la interfaz de usuario

### Para Implementadores
1. [DESIGN.md](DESIGN.md) → Arquitectura general
2. [RULES.md](RULES.md) → Validaciones y lógica de negocio
3. [SCORING.md](SCORING.md) → Fórmulas y cálculos
4. [ACHIEVEMENTS.md](ACHIEVEMENTS.md) → Sistema de logros
5. [NOTIFICATIONS.md](NOTIFICATIONS.md) → Mensajes y personalidad

### Para Diseñadores/Escritores
1. [NOTIFICATIONS.md](NOTIFICATIONS.md) → Tono y personalidad
2. [ACHIEVEMENTS.md](ACHIEVEMENTS.md) → Nombres y descripciones
3. [COMMANDS.md](COMMANDS.md) → UI y embeds

---

## 🚀 Estado del Proyecto

**Versión Actual:** v1.0 (En desarrollo)  
**Última Actualización:** Enero 2025

### Componentes Completados
- ✅ Diseño completo del sistema de puntos v1.0
- ✅ Sistema de rachas y multiplicadores
- ✅ 35+ logros diseñados (20 públicos + 15 ocultos)
- ✅ Personalidad del bot definida
- ✅ Sistema de strikes y penalizaciones

### Pendiente de Implementación
- ⏳ Comandos slash en Discord.py
- ⏳ Base de datos SQLite
- ⏳ Detección de logros
- ⏳ Sistema de notificaciones configurables
- ⏳ Leaderboard con paginación

---

## 📞 Contacto y Contribuciones

¿Tienes dudas sobre la documentación? Abre un issue en GitHub con la etiqueta `documentation`.

¿Encontraste algo confuso o incompleto? Pull requests son bienvenidos.

---

**Volver al [README principal](../README.md)**
