# 🚀 Deployment y Setup - Pole Bot

Esta guía cubre la instalación inicial y deployment tanto para desarrollo como producción.

---

## 📋 Pre-requisitos

- Python 3.8+
- Git
- Cuenta de Discord con bot configurado
- SQLite (incluido con Python)

---

## 🆕 Setup Inicial (Primera Vez)

### 1. Clonar el Repositorio

```bash
git clone https://github.com/manumyx/Pole-Bot.git
cd Pole-Bot
```

### 2. Crear Entorno Virtual

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux/Mac
source .venv/bin/activate
```

### 3. Instalar Dependencias

```bash
pip install -r requirements.txt
```

### 4. Configurar Variables de Entorno

Crea un archivo `.env` en la raíz:

```env
DISCORD_TOKEN=tu_token_aqui
DEBUG=1  # Para desarrollo, usar 0 en producción
```

### 5. **IMPORTANTE: Inicializar Base de Datos**

El bot necesita que la base de datos esté correctamente inicializada antes del primer uso.

#### **Paso 5.1: Ejecutar Migraciones**

```bash
# El bot ejecuta migraciones automáticamente al iniciar
# Pero puedes verificarlas manualmente con:
python -c "from utils.database import Database; db = Database(); print('✅ BD inicializada')"
```

#### **Paso 5.2: Inicializar Temporadas** ⚠️ **CRÍTICO**

```bash
python scripts/initialize_seasons.py
```

Este script:

- ✅ Crea todas las temporadas desde 2025 (preseason) hasta el año actual
- ✅ Marca la temporada actual como activa
- ✅ Previene errores de FOREIGN KEY constraint

**Salida esperada:**

```
============================================================
🎬 POLE BOT - Inicialización de Temporadas
============================================================
🔄 Inicializando temporadas en la base de datos...
  + preseason (Pre-temporada 2025) - ⚪ inactiva
  + season_1 (Temporada 1 (2026)) - ✅ ACTIVA

✅ Inicialización completada:
   📝 2 temporadas creadas
   🔄 0 temporadas actualizadas
   🎯 Temporada actual: season_1

✅ Listo! Ahora puedes ejecutar el bot con: py main.py
```

### 6. Iniciar el Bot

```bash
python main.py
```

---

## 🔄 Deployment a Producción

### Pre-Deployment Checklist

- [ ] **Backup de la base de datos**

  ```bash
  cp data/pole_bot.db data/backups/pole_bot_$(date +%Y%m%d_%H%M%S).db
  ```

- [ ] **Variables de entorno correctas**

  ```env
  DEBUG=0  # ⚠️ Importante en producción
  DISCORD_TOKEN=tu_token_de_produccion
  ```

- [ ] **Ejecutar tests de compilación**

  ```bash
  python -m py_compile main.py cogs/*.py utils/*.py
  ```

- [ ] **Verificar migraciones**

  ```bash
  # Al iniciar el bot verás:
  # 🔍 Schema actual: v6, Target: v6
  # ✅ Base de datos ya está en v6
  ```

- [ ] **Inicializar temporadas (si es primera vez o nuevo año)**
  ```bash
  python scripts/initialize_seasons.py
  ```

### Deployment Steps

1. **Pull últimos cambios**

   ```bash
   git pull origin main
   ```

2. **Activar entorno virtual**

   ```bash
   # Windows
   .venv\Scripts\activate

   # Linux/Mac
   source .venv/bin/activate
   ```

3. **Actualizar dependencias** (si cambiaron)

   ```bash
   pip install -r requirements.txt --upgrade
   ```

4. **Backup de BD** (SIEMPRE)

   ```bash
   python scripts/verify_db.py  # Health check
   cp data/pole_bot.db data/backups/backup_pre_deploy.db
   ```

5. **Inicializar temporadas** (si es necesario)

   ```bash
   # Solo si:
   # - Es primera vez que deployeas
   # - Cambió de año (nueva temporada)
   # - Restauraste un backup antiguo
   python scripts/initialize_seasons.py
   ```

6. **Iniciar bot**

   ```bash
   python main.py
   ```

7. **Verificar en Discord**
   - Escribe `pole` en un canal configurado
   - Verifica que `/settings` funciona
   - Comprueba que `/profile` muestra stats correctas

---

## 🆘 Troubleshooting

### Error: `FOREIGN KEY constraint failed`

**Causa:** La temporada actual no existe en la tabla `seasons`.

**Solución:**

```bash
python scripts/initialize_seasons.py
```

### Error: `Table seasons doesn't exist`

**Causa:** Base de datos no migrada correctamente.

**Solución:**

```bash
# Backup primero (si existe)
cp data/pole_bot.db data/pole_bot_backup.db

# Iniciar el bot para que ejecute migraciones
python main.py

# Luego inicializar temporadas
python scripts/initialize_seasons.py
```

### Error: `Discord token is invalid`

**Causa:** Token incorrecto en `.env`.

**Solución:**

1. Ve a [Discord Developer Portal](https://discord.com/developers/applications)
2. Regenera el token
3. Actualiza `.env`

### El bot no responde a comandos slash

**Causa:** Comandos no sincronizados.

**Solución:**

1. Verifica que el bot tiene permiso `applications.commands` en el servidor
2. Reinicia el bot (sincroniza automáticamente)
3. Si persiste, usa `/debug sync` (requiere permisos admin)

---

## 📊 Verificación de Salud de la BD

Ejecuta regularmente:

```bash
python scripts/verify_db.py
```

Esto verifica:

- ✅ Integridad de foreign keys
- ✅ Consistencia de datos
- ✅ Schema version correcta
- ✅ No hay registros huérfanos

---

## 🔄 Cambio de Año (Migración de Temporada)

**El bot maneja esto automáticamente**, pero puedes verificar:

### Antes del 1 de Enero (Pre-cambio)

```bash
# Verificar que el sistema está listo
python scripts/verify_db.py

# Backup preventivo
cp data/pole_bot.db data/backups/pre_new_year_$(date +%Y).db
```

### El 1 de Enero (Día del cambio)

El bot ejecutará automáticamente:

1. **Finalización de temporada anterior** → Guarda en `season_history`
2. **Otorgamiento de badges** → Top 3 reciben badges permanentes
3. **Creación de nueva temporada** → Automático con `initialize_seasons.py`
4. **POLE REWIND** → Mensajes de celebración en todos los servidores
5. **Reset de rachas** → `current_streak = 0` para todos

### Después del 1 de Enero (Post-cambio)

```bash
# Verificar que todo funcionó bien
python scripts/verify_db.py

# Inicializar nueva temporada (si no se hizo antes)
python scripts/initialize_seasons.py
```

---

## 🛠️ Scripts Disponibles

| Script                          | Descripción                                               |
| ------------------------------- | --------------------------------------------------------- |
| `scripts/initialize_seasons.py` | **Inicializar temporadas** (OBLIGATORIO en setup inicial) |
| `scripts/verify_db.py`          | Verificar integridad de la base de datos                  |
| `scripts/db_health_check.py`    | Health check completo con diagnóstico                     |
| `scripts/migrate_seasons.py`    | Migración manual de temporadas (desarrollo)               |
| `scripts/populate_test_data.py` | Poblar BD con datos de prueba (solo testing)              |

---

## 🎯 Resumen del Workflow

### Primera Vez

```bash
git clone → venv → pip install → .env → python scripts/initialize_seasons.py → python main.py
```

### Cada Deployment

```bash
git pull → backup BD → python scripts/initialize_seasons.py (si es necesario) → python main.py
```

### Cambio de Año

```bash
backup BD → dejar que el bot maneje automáticamente → verificar con verify_db.py
```

---

**¿Dudas?** Revisa los logs del bot o usa `/debug info` (requiere DEBUG=1).
