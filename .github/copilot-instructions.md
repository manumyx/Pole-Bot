# Instrucciones para Asistente de IA - Pole Bot 🎬

Este documento proporciona un contexto detallado sobre el proyecto Pole Bot para que los asistentes de IA (como GitHub Copilot) puedan generar código preciso, coherente y **CON LA ESENCIA** 🔥.

## 1. Propósito Principal del Bot

El "Pole Bot" es un bot de Discord para una especie de juego competitivo. Cada día, a una hora secreta y aleatoria, se "abre el pole". Los usuarios compiten por ser los primeros en escribir la palabra `pole` en un canal designado.

**Contexto cultural:** Pole empezó en forocoches como una manera de competir para ver quién era el más rápido en escribir "pole" como primer mensaje de un hilo o canal. He tomado la inspiración de ese juego para crear un bot que automatice y gestione esta competición en servidores de Discord, y de paso lo he hecho más complejo y competitivo.

- **Puntuación:** Los puntos se otorgan según la rapidez: `Critical` (0-10 min), `Fast` (10 min-3h), `Normal` (3h-00:00) y `Marranero` (día siguiente).
- **Características Clave:** 
  - Rachas progresivas con multiplicadores (hasta x2.5)
  - Temporadas anuales con **POLE REWIND** 🎬
  - Rankings locales y globales
  - Badges permanentes por logros
  - Sistema de notificaciones con failsafe tras downtime
- **Alcance:** El bot funciona a nivel de servidor (local) pero también tiene rankings globales que comparan usuarios y servidores entre sí.

## 2. 🔥 LA ESENCIA DEL POLE BOT

**IMPORTANTE:** El Pole Bot tiene personalidad. No es un bot corporativo ni formal. Tiene CARISMA, VACILE y FLOW.

### **Tono de Mensajes:**
- ✅ **Casual y divertido:** "Qué manera de cerrar el año, familia" 
- ✅ **Con hype:** "Ahora viene lo bueno. 🔥"
- ✅ **Directo y auténtico:** "Se acabó la beta. Ahora va EN SERIO."
- ✅ **Competitivo pero sano:** "Que gane el mejor. 🏁"
- ❌ **Evitar tono corporativo:** "Estimado usuario, gracias por participar..."
- ❌ **Evitar exceso de emojis:** Úsalos con propósito, no spam

### **Ejemplos de Mensajes con Esencia:**

**Bueno:**
```
"¡POLE CRÍTICO! ⚡ 2 minutos. Eres una máquina."
"Pole marranero... Mejor tarde que nunca. 🐷"
"Racha de 30 días. Esa disciplina... 😤"
```

**Malo:**
```
"Has conseguido un pole crítico. Bien hecho."
"Tu racha es de 30 días. Continúa así."
```

### **Características de Personalidad:**
- 🎯 **Competitivo:** Celebra victorias, vacila derrotas
- 🔥 **Motivador:** Impulsa a mantener rachas y mejorar
- 😎 **Cool:** No toma todo súper serio, sabe cuándo relajarse
- 🏆 **Justo:** Celebra a todos, no solo al #1

## 3. Tecnologías y Librerías Principales

- **Framework:** `discord.py>=2.3.0`. El código debe usar las características modernas de la librería.
- **Base de Datos:** SQLite con **schema versioning** (v3 actual).
- **Python:** 3.8+ con type hints obligatorios.
- **Dependencias:** Ver `requirements.txt` completo.

## 4. Arquitectura y Estructura del Proyecto

### **`main.py` (Punto de Entrada):**
- Define la clase `PoleBot(commands.Bot)`.
- Configura los `Intents` de Discord (incluyendo `message_content` y `members`).
- El `setup_hook` carga dinámicamente las extensiones (Cogs).
- Status del bot: "poleando con X jugadores" (no "pole con X").

### **`cogs/` (Capa de Comandos y Lógica):**

**`cogs/pole.py`** - El corazón del bot:
- `on_message`: Detecta la palabra `pole`
- `process_pole`: Validación, puntuación y guardado
- Comandos: `/profile`, `/leaderboard`, `/settings`, `/history`
- Tasks loops:
  - `daily_pole_generator`: Genera hora a las 00:00, ejecuta migración de temporada
  - `midnight_summary_check`: Resúmenes diarios
  - `opening_notification_watcher`: Failsafe de notificaciones
- **POLE REWIND:** `_send_season_change_announcement()` - Sistema de celebración de Año Nuevo

**`cogs/events.py`:**
- Respuestas a menciones del bot
- `on_guild_remove`: Limpieza automática al ser expulsado

**`cogs/debug.py`** (solo si `DEBUG=1`):
- `/debug test_migration`: Testear migraciones (dry run + real)
- `/debug force_generate`: Generar hora manualmente
- `/debug info`: Ver estado del servidor
- `/debug db_check`: Health check de BD

### **`utils/` (Lógica de Negocio):**

**`utils/database.py`** - **CRÍTICO:**
- **ÚNICA clase que puede tocar la BD** `data/pole_bot.db`
- Usa context managers con rollback automático
- PRAGMA foreign_keys = ON siempre
- Schema versioning con `_run_migrations()`
- **Regla de oro:** Nunca escribas SQL directamente en cogs, añade método aquí

**`utils/scoring.py`:**
- `calculate_points()`: Puntos según tipo + multiplicador de racha
- `classify_delay()`: Critical/Fast/Normal/Marranero
- `get_rank_info()`: Rangos según puntos (Rubí, Amatista, Diamante, Oro, Plata, Bronce)
- `get_season_info()`: Config de temporadas (2025 = pre-temporada, 2026+ = oficiales)

## 5. Esquema de Base de Datos (Schema v3)

**Tablas Core:**
- `servers`: Config por servidor (canal, rol ping, notificaciones, hora diaria)
- `users`: Stats acumuladas (rachas, contadores). **Puntos se calculan dinámicamente**
- `poles`: Historial completo de cada pole individual
- `schema_metadata`: Versión de schema + timestamp

**Tablas de Temporadas:**
- `seasons`: Define temporadas (ID, nombre, fechas, is_active)
- `season_stats`: **Tabla clave para rankings** - Stats por usuario/temporada
- `season_history`: Copia final al terminar temporada
- `user_badges`: Badges permanentes ganados

**Importante:**
- Los puntos totales NO se guardan en `users`, se calculan desde `season_stats`
- Foreign keys habilitadas siempre
- Usa `get_connection()` context manager para transacciones

## 6. 📝 Flujo de Trabajo y Gestión de Tareas

### **`todo.txt` - La Biblia del Proyecto**

El fichero `todo.txt` es la **FUENTE ÚNICA DE VERDAD** para tareas, bugs y progreso.

#### **Workflow Obligatorio:**

1. **ANTES de empezar:** Lee `todo.txt` completo
2. **Implementa la tarea:** Código + tests si aplica
3. **Verifica que funciona:** Compila sin errores, lógica correcta
4. **Actualiza `todo.txt`:**
   - Marca como `[x]` o elimina si completada
   - Añade detalles de implementación si son complejos
5. **Nuevos bugs/ideas:** Añade al `todo.txt` inmediatamente

#### **Formato de Tareas:**

```markdown
## 🚨 CRÍTICOS (hacer YA)
- [ ] Tarea crítica con deadline
  - Detalles técnicos
  - Archivos afectados
  
## 🔧 PENDIENTES (hacer cuando se pueda)
- [ ] Mejora o feature nueva
  
## 🔮 FUTURO (nice to have)
- [ ] Ideas a largo plazo
```

#### **Reglas:**
- ✅ Marca `[x]` cuando completes algo
- ✅ Añade sub-tareas con indentación (bullets)
- ✅ Usa emojis para categorizar (🚨🔧🔮🐛✨)
- ❌ No dejes tareas marcadas como pendientes si ya están hechas
- ❌ No borres el historial de completadas (está al inicio del archivo)

### **El Chiste del `todo.txt`:**

Sí, literalmente escribimos TODO en el `todo.txt`. Es el sistema de gestión de proyectos más simple y efectivo que existe. No Jira, no Trello, solo un archivo de texto plano con markdown. Y funciona. 😎

## 7. Convenciones de Codificación

### **Obligatorias:**
- ✅ `app_commands` (comandos de barra) para toda funcionalidad nueva
- ✅ Type hints en TODAS las funciones nuevas
- ✅ Docstrings en español para funciones complejas
- ✅ `async`/`await` - El bot es 100% asíncrono
- ✅ F-strings para formateo de strings
- ✅ Context managers para DB (`with self.db.get_connection()`)
- ✅ Logging con emojis para mayor claridad (🔄✅❌⚠️)

### **Prohibidas:**
- ❌ SQL directo en cogs (usar métodos de `Database`)
- ❌ Comandos con prefijo `!` (solo app_commands `/`)
- ❌ Código síncrono que bloquee el event loop
- ❌ Mensajes en inglés (todo en español)
- ❌ Type hints con `any` (ser específico)

### **Estilo:**
```python
# BUENO
async def get_user_stats(self, user_id: int, guild_id: int) -> Dict[str, Any]:
    """Obtiene estadísticas completas de un usuario"""
    with self.db.get_connection() as conn:
        cursor = conn.cursor()
        # ... lógica
        return dict(row)

# MALO
def getUserStats(userId, guildId):
    cursor = self.db.conn.cursor()  # ❌ No context manager
    # ... lógica
    return row  # ❌ No type hint de retorno
```

## 8. Sistema de Temporadas y Migración

### **Flujo de Año Nuevo (1 de enero 00:00):**

```
daily_pole_generator() se ejecuta
   ↓
Detecta cambio: old_season != current_season
   ↓
migrate_season(new_season)
   ├─ finalize_season(old_season)
   │  ├─ Guarda en season_history
   │  ├─ Otorga badges finales
   │  └─ Marca como inactiva
   ├─ Activa nueva temporada
   ├─ Resetea current_streak = 0
   └─ Limpia season_stats antiguas (últimas 3)
   ↓
_send_season_change_announcement() - POLE REWIND 🎬
   ├─ Mensaje 1: Felicitación (especial si es primera temporada)
   ├─ Mensaje 2: Intro "POLE REWIND {year}"
   ├─ Mensaje 3: Hall of Fame Local (Top 3)
   ├─ Mensaje 4: Hall of Fame Global (Top 3)
   └─ Mensaje 5: Bienvenida nueva temporada
   ↓
Genera hora de pole del día
   ↓
Operación normal
```

### **Temporadas Especiales:**

- **2025:** Pre-temporada / Beta (mensaje especial para early adopters)
- **2026+:** Temporadas oficiales (mensaje estándar)

El sistema detecta automáticamente si es la primera temporada real y ajusta los mensajes del POLE REWIND.

## 9. Sistema de Notificaciones

### **Tres Capas de Notificaciones:**

1. **Scheduler Principal:** `_schedule_single_notification()`
   - Programa notificación exacta con `asyncio.sleep()`
   - Una task por servidor

2. **Watcher Failsafe:** `opening_notification_watcher`
   - Corre cada 1 minuto
   - Detecta notificaciones perdidas (ej: bot caído)
   - Envía si estamos dentro de ventana de 60 min
   - **SIEMPRE envía**, incluso si ya hay poles

3. **Startup Failsafe:** `_run_startup_failsafe()`
   - Ejecuta al iniciar bot
   - Corrige rachas perdidas
   - Regenera hora si falta

**Filosofía:** Mejor enviar notificación duplicada que no enviarla.

## 10. Documentación y Releases

### **Archivos de Documentación:**

- **`README.md`:** Overview del proyecto, features, instalación
- **`QUICK_START.md`:** Deployment en 5 pasos
- **`DEPLOYMENT_CHECKLIST.md`:** Checklist pre-deployment completo
- **`RELEASE_NOTES.md`:** Notas detalladas de cada versión
- **`docs/`:**
  - `COMMANDS.md`: Lista de comandos
  - `RULES.md`: Reglas del juego
  - `ACHIEVEMENTS.md`: Sistema de badges
  - `CHANGELOG_*.md`: Changelogs específicos

### **Cuando Modificas Código:**

1. ✅ Actualiza docstrings en el código
2. ✅ Actualiza `docs/` si afecta comandos/reglas
3. ✅ Actualiza `README.md` si es feature mayor
4. ✅ Añade a `RELEASE_NOTES.md` si es para próximo release
5. ✅ Actualiza `todo.txt` marcando tarea completada
6. ✅ Actualiza `.github/copilot-instructions.md` si cambia arquitectura

**No dejes documentación desactualizada.** Es tan importante como el código.

## 11. Testing y Deployment

### **Antes de Deployar:**

1. ✅ `python -m py_compile` en todos los archivos
2. ✅ Linter sin errores (type hints correctos)
3. ✅ Revisar `DEPLOYMENT_CHECKLIST.md`
4. ✅ Backup de `data/pole_bot.db`
5. ✅ `DEBUG=0` en `.env` de producción
6. ✅ Todos los `todo.txt` críticos completados

### **Testing Recomendado:**

- **Bot de prueba:** Crea aplicación Discord separada para testear
- **Comandos debug:** Usa `/debug test_migration dry_run:True` antes de real
- **Verificación:** `/debug db_check` para health check

### **En Caso de Emergencia:**

```bash
# Migración manual
/debug test_migration dry_run:False target_season:2026

# Regenerar hora
/debug force_generate

# Ver estado
/debug info
```

## 12. Principios de Desarrollo

### **KISS (Keep It Simple, Stupid):**
- No sobre-ingenierizar
- Soluciones directas sobre complejas
- `todo.txt` > sistemas de tickets elaborados

### **Robustez:**
- Context managers con rollback automático
- Logging detallado con emojis
- Failsafes para downtimes
- Verificación de integridad post-migración

### **User Experience:**
- Mensajes con personalidad y carisma
- Feedback inmediato
- Embeds visualmente atractivos
- Emojis con propósito

### **Mantenibilidad:**
- Código autodocumentado (nombres claros)
- Type hints obligatorios
- SQL centralizado en `Database`
- Documentación actualizada

## 13. Resumen Ejecutivo para IA

**Si solo puedes recordar 5 cosas:**

1. 🔥 **LA ESENCIA:** Mensajes con carisma, no corporativos
2. 📝 **`todo.txt` es ley:** Consulta antes, actualiza después
3. 🛢️ **SQL solo en `Database`:** Nunca en cogs directamente
4. ⚡ **Todo es async:** `async`/`await` siempre
5. 📚 **Documenta todo:** Código + docs + `todo.txt`

**Versión Actual:** v2.0 - Pre-Año Nuevo Edition (POLE REWIND 🎬)  
**Última Actualización:** 27 de diciembre de 2025  
**Estado:** ✅ Producción Ready

---

🎆 **¡Que el pole esté contigo!** 🎆