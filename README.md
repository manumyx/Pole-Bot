# Pole Bot 🏁

[![Discord](https://img.shields.io/badge/Discord-Bot-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.com)
[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

Bot de Discord para competiciones diarias de `pole` con apertura aleatoria, clasificación por velocidad, rachas globales y temporadas anuales.

## ✨ Funcionalidades clave

- ⏰ Apertura diaria aleatoria por servidor.
- 🏎️ Categorías por velocidad (`critical`, `fast`, `normal`, `marranero`).
- 🌍 Regla global: una pole por usuario y día entre todos los servidores.
- 🔥 Rachas globales con multiplicador progresivo (hasta x2.5).
- 📅 Temporadas con migración automática al cambiar de año.
- 🎬 POLE REWIND al cierre de temporada (local/global).
- 🛟 Notificaciones con lógica de recuperación ante downtime.

## 🧩 Comandos principales

- `/settings` · configuración del servidor (admins).
- `/profile` · perfil y estadísticas de usuario.
- `/leaderboard` · rankings local/global.
- `/streak` · ranking de rachas.
- `/season` · estado de temporada actual.
- `/history` · historial de poles.
- `/putometro` · contador global del putómetro.
- `/polehelp` · ayuda rápida en Discord.

## 🛠️ Modo debug (`DEBUG=1`)

Se habilita el grupo `/debug` en `cogs/debug.py` con utilidades de administración y diagnóstico:

- Inspección y diagnóstico: `info`, `diagnose`.
- Simulación y pruebas: `pole_time`, `notify_test`, `simulate_pole`, `reset_date`, `test_migration`.
- Recuperación operativa: `compensate_downtime`, `restore_streak`, `restore_guild`, `modify_user`.

## 📦 Requisitos e instalación

- Python 3.10+
- Dependencias en `requirements.txt`

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
# Opcional en debug:
# DEBUG_ALLOWLIST=123456789012345678
```

Arranque:

```bash
python main.py
```

## 🗄️ Base de datos

- SQLite en `data/pole_bot.db`.
- Migraciones automáticas al iniciar.
- Schema actual: `v8`.
- Script de restauración de rachas: `scripts/restore_streaks.py`.

## 📚 Documentación

- [Guía de deployment](DEPLOYMENT.md)
- [Índice de documentación](docs/README.md)
- [Reglas del juego](docs/RULES.md)
- [Badges y rangos](docs/ACHIEVEMENTS.md)
- [Internacionalización (i18n)](docs/I18N.md)

## ✅ Validación rápida

```bash
python -m compileall cogs utils main.py scripts
```
