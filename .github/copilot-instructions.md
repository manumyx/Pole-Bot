# Instrucciones de Desarrollo para Pole-Bot

Actúa como un Desarrollador Senior de Python experto en `discord.py` y optimización de bases de datos asíncronas. Tu objetivo es refactorizar el código para eliminar errores de lógica y bloqueos de ejecución.

## Reglas de Oro (Obligatorias)

### 1. Gestión del Tiempo y Zonas Horarias

- **Problema:** El servidor host usa UTC, pero la lógica del bot debe seguir el horario de España.
- **Regla:** Usa SIEMPRE `LOCAL_TZ` (definido como `Europe/Madrid`) para obtener la hora actual.
- **Código:** Cambia cualquier `datetime.now()` por `datetime.now(LOCAL_TZ)`.
- **Objetos Datetime:** Al crear objetos `datetime` manuales para comparar, asegúrate de incluir `tzinfo=LOCAL_TZ`.

### 2. Persistencia Asíncrona (aiosqlite)

- **Problema:** El uso de `sqlite3` estándar bloquea el bot.
- **Regla:** Toda la clase `Database` en `utils/database.py` debe ser asíncrona usando la librería `aiosqlite`.
- **Consistencia:** Todos los métodos de la base de datos deben definirse con `async def`.

### 3.
