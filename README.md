# Pole Bot

[![Discord](https://img.shields.io/badge/Discord-Bot-5865F2?style=for-the-badge&logo=discord&logoColor=white)](https://discord.com)
[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

Bot de Discord para competiciones diarias de pole: hora aleatoria, puntos por velocidad, rachas globales y temporadas anuales.

## Que hace

- Apertura diaria con hora aleatoria por servidor.
- Clasificacion por velocidad: critica, veloz, normal y marranero.
- Rachas globales (compartidas entre todos los servidores).
- Multiplicador progresivo de racha hasta x2.5.
- Temporadas anuales con migracion automatica.
- POLE REWIND en cambio de temporada (resumen local/global).
- Sistema de notificaciones con failsafe para downtime.

## Comandos principales

- `/settings` Configuracion del servidor (admins).
- `/profile` Perfil y estadisticas del usuario.
- `/leaderboard` Rankings local/global.
- `/streak` Ranking de rachas.
- `/season` Info de temporada actual.
- `/history` Historial de poles del usuario.
- `/polehelp` Ayuda rapida dentro de Discord.

## Modo debug (solo DEBUG=1)

Si `DEBUG=1`, se carga `cogs/debug.py` con herramientas admin:

- `/debug info`
- `/debug diagnose`
- `/debug test_migration`
- `/debug compensate_downtime`
- `/debug restore_streak`
- `/debug restore_guild`

## Requisitos

- Python 3.8+
- `discord.py>=2.3.0`
- `python-dotenv>=1.0.0`

Instalacion:

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux/Mac
source .venv/bin/activate

pip install -r requirements.txt
```

`.env` minimo:

```env
DISCORD_TOKEN=tu_token
DEBUG=0
# Opcional en debug:
# DEBUG_ALLOWLIST=123456789012345678
```

Iniciar:

```bash
python main.py
```

## Base de datos y migraciones

- SQLite en `data/pole_bot.db`.
- Migraciones automaticas al iniciar.
- Schema actual: `v7`.
- Restauracion de rachas (solo global_users, sin puntos): `scripts/restore_streaks.py`.

No necesitas ejecutar scripts de inicializacion para arrancar el bot en un entorno nuevo.

## Documentacion

- Guia de deploy: [DEPLOYMENT.md](DEPLOYMENT.md)
- Indice de docs: [docs/README.md](docs/README.md)
- Reglas de juego: [docs/RULES.md](docs/RULES.md)
- Sistema de badges: [docs/ACHIEVEMENTS.md](docs/ACHIEVEMENTS.md)
- Internacionalizacion: [docs/I18N.md](docs/I18N.md)

## Notas de operacion

- El bot usa solo slash commands para usuarios finales.
- Los comandos debug solo estan disponibles cuando `DEBUG=1` y el usuario esta en `DEBUG_ALLOWLIST`.
- En cambio de año, el bot migra temporada automaticamente y puede emitir POLE REWIND.
