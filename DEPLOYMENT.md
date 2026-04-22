# Deployment - Pole Bot

Guia actualizada para preparar, desplegar y validar el bot antes de subir cambios a GitHub o pasar a produccion.

## Requisitos

- Python 3.8+
- Entorno virtual recomendado
- Token valido de Discord
- Dependencias instaladas con `requirements.txt`

## Setup local rapido

```bash
git clone https://github.com/manumyx/Pole-Bot.git
cd Pole-Bot
python -m venv .venv
```

Activar entorno:

```bash
# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

Instalar deps:

```bash
pip install -r requirements.txt
```

Crear `.env`:

```env
DISCORD_TOKEN=tu_token
DEBUG=0
# Solo debug:
# DEBUG_ALLOWLIST=123456789012345678
```

Arrancar:

```bash
python main.py
```

## Checklist antes de push a GitHub

- [ ] El proyecto compila sin errores
- [ ] Los docs estan alineados con el codigo actual
- [ ] No hay referencias a scripts/comandos inexistentes
- [ ] `todo.txt` actualizado si cerraste tareas

Comando recomendado de compilacion:

```bash
python -m py_compile main.py cogs/pole.py cogs/events.py cogs/debug.py utils/database.py utils/scoring.py utils/i18n.py
```

## Checklist antes de deploy a produccion

- [ ] Backup de la BD (`data/pole_bot.db`)
- [ ] `DEBUG=0` en `.env`
- [ ] Dependencias al dia
- [ ] Compilacion correcta
- [ ] Bot conectado y slash commands sincronizados

Backup ejemplo:

```bash
# PowerShell (Windows)
Copy-Item data/pole_bot.db data/backups/pole_bot_predeploy.db

# Linux/Mac
cp data/pole_bot.db data/backups/pole_bot_predeploy.db
```

## Deploy recomendado

1. `git pull`
2. Activar `.venv`
3. `pip install -r requirements.txt`
4. Backup de BD
5. `python main.py`

## Validacion post-deploy

- Comprobar en Discord:
  - `/settings`
  - `/profile`
  - `/leaderboard`
  - Mensajes de apertura y validacion de `pole`
- Revisar logs de inicio:
  - Migraciones aplicadas correctamente
  - Sin errores de extension/cogs

## Temporadas y cambio de ano

El bot gestiona la migracion de temporada automaticamente. En caso de incidencia:

- Ejecutar diagnostico con comandos debug (si `DEBUG=1`)
- Usar `scripts/migrate_seasons.py` solo para mantenimiento manual

## Scripts disponibles en este repo

- `scripts/check_missing_translations.py`
- `scripts/check_placeholders.py`
- `scripts/migrate_seasons.py`
- `scripts/restore_streaks.py`

Si ves referencias a `verify_db.py`, `initialize_seasons.py`, `db_health_check.py` o `populate_test_data.py`, estan desactualizadas y no forman parte del repo actual.

## Restaurar rachas (sin tocar puntos)

Si hubo caida/incidencia y quieres recuperar solo rachas globales, usa:

```bash
python scripts/restore_streaks.py --db data/pole_bot.db
```

Comportamiento por defecto:

- `dry-run` (no escribe nada)
- modo `forgiving`
  - si un usuario tenia actividad antes del inicio de temporada, la racha se reconstruye desde `start_date` de la temporada
  - si no tenia actividad previa, se reconstruye desde su primer pole de temporada
- no reduce rachas existentes (solo restaura hacia arriba)
- modo conservador de `best_streak`: solo sube si sube `current_streak`

Aplicar cambios reales:

```bash
python scripts/restore_streaks.py --db data/pole_bot.db --apply
```

Notas operativas:

- En `--apply` crea backup automatico en `data/backups/`.
- Solo actualiza `global_users` (`current_streak`, `best_streak`, `last_pole_date`, `updated_at`).
- No modifica puntos ni filas de `season_stats`.
- Recomendado: parar el bot durante la operacion para evitar escrituras concurrentes.

Opciones utiles:

```bash
# Limitar a un usuario concreto
python scripts/restore_streaks.py --db data/pole_bot.db --user-id 123456789012345678

# Forzar temporada concreta
python scripts/restore_streaks.py --db data/pole_bot.db --season-id season_1

# Recalculo estricto por dias consecutivos registrados
python scripts/restore_streaks.py --db data/pole_bot.db --mode strict

# Recalcular tambien best_streak historico desde la temporada
python scripts/restore_streaks.py --db data/pole_bot.db --rebuild-best

# Proteger rachas para manana (perdona hoy sin tocar puntos)
python scripts/restore_streaks.py --db data/pole_bot.db --protect-tomorrow

# Igual que arriba, pero sumando +1 de racha al dia perdonado
python scripts/restore_streaks.py --db data/pole_bot.db --protect-tomorrow --protect-bump
```
