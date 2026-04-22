# 🚀 Deployment - Pole Bot

Guía breve para preparar, desplegar y validar el bot en entornos reales.

## 📦 Requisitos

- Python 3.10+
- `.venv` recomendado
- Token válido de Discord
- Dependencias de `requirements.txt`

## ⚙️ Setup rápido

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate
pip install -r requirements.txt
```

`.env` mínimo:

```env
DISCORD_TOKEN=tu_token
DEBUG=0
# Solo debug:
# DEBUG_ALLOWLIST=123456789012345678
```

Arranque:

```bash
python main.py
```

## ✅ Checklist pre-push

- [ ] Compilación rápida OK.
- [ ] Documentación alineada con el código.
- [ ] Sin referencias a scripts/comandos inexistentes.

Validación recomendada:

```bash
python -m py_compile main.py
python -m compileall cogs utils scripts
```

## 🧯 Checklist pre-producción

- [ ] Backup de `data/pole_bot.db`.
- [ ] `DEBUG=0` en `.env`.
- [ ] Dependencias actualizadas.
- [ ] Bot conectado y comandos slash sincronizados.

Backup rápido:

```bash
# Windows (PowerShell)
Copy-Item data/pole_bot.db data/backups/pole_bot_predeploy.db

# Linux/Mac
cp data/pole_bot.db data/backups/pole_bot_predeploy.db
```

## 🔎 Validación post-deploy

- Probar: `/settings`, `/profile`, `/leaderboard`.
- Verificar notificación de apertura y captura de `pole`.
- Revisar logs de inicio (migraciones y carga de cogs).

## 🧰 Scripts operativos disponibles

- `scripts/check_missing_translations.py`
- `scripts/check_placeholders.py`
- `scripts/migrate_seasons.py`
- `scripts/restore_streaks.py`

## ♻️ Restaurar rachas (sin tocar puntos)

Simulación (`dry-run` por defecto):

```bash
python scripts/restore_streaks.py --db data/pole_bot.db
```

Aplicar cambios reales:

```bash
python scripts/restore_streaks.py --db data/pole_bot.db --apply
```

Notas clave:

- En `--apply` crea backup automático en `data/backups/`.
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
```
