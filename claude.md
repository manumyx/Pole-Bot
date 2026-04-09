# Contexto del Proyecto: Pole-Bot
Bot de Discord modular desarrollado en Python 3.10+ usando la librería `discord.py`.

# Reglas Arquitectónicas Inquebrantables (OBLIGATORIO)
1. **Asincronía Total:** PROHIBIDO usar `sqlite3` síncrono. Toda la interacción con la base de datos debe hacerse con `aiosqlite` (`async/await`) para no bloquear el event loop.
2. **Control del Tiempo (Bug Crítico):** El servidor host está en UTC. Usa SIEMPRE la zona horaria `Europe/Madrid` (importando `LOCAL_TZ`) en cualquier llamada a `datetime.now()` o al comparar fechas.
3. **Separación de Lógica:** - Los comandos de Discord (`app_commands`) van exclusivamente en la carpeta `cogs/`.
   - La lógica pura de datos y negocio va en `utils/` (ej. `utils/database.py`).
4. **Internacionalización (i18n):** Nunca hardcodees textos sueltos en las respuestas. Usa siempre la función `t()` de `utils.i18n` para soportar múltiples idiomas.

# Instrucciones de Ahorro de Tokens
- Devuelve directamente el código corregido o los comandos necesarios. 
- Omite explicaciones teóricas, saludos, disculpas o relleno a menos que yo te haga una pregunta directa.
- Si necesitas contexto extra sobre el proyecto, lee los archivos dentro de la carpeta `docs/`.
