"""
Sistema de Base de Datos v1.0 - Sistema de Hora Aleatoria + Seasons
Maneja toda la persistencia del Pole Bot
"""
import aiosqlite
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple, Any
from contextlib import asynccontextmanager
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo('Europe/Madrid')

class Database:
    # Versión actual del schema - incrementar con cada migración
    SCHEMA_VERSION = 8  # v1: inicial, v2: pole_date, v3: last_daily_pole_time, v4: impatient_attempts, v5: global_users, v6: i18n (language), v7: notification_sent_at, v8: puta_counter

    def __init__(self, db_path: str = "data/pole_bot.db"):
        self.db_path = db_path
        self.log = logging.getLogger('Database')

        # Crear directorio si no existe
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        # Sin llamadas a DB — se inicializa desde setup_hook con await db.initialize()

    @asynccontextmanager
    async def get_connection(self):
        """Context manager async para conexiones a la base de datos"""
        async with aiosqlite.connect(self.db_path, timeout=10.0) as conn:
            conn.row_factory = aiosqlite.Row
            await conn.execute('PRAGMA foreign_keys = ON')
            await conn.execute('PRAGMA journal_mode = WAL')
            try:
                yield conn
                await conn.commit()
            except Exception:
                await conn.rollback()
                raise

    async def initialize(self):
        """Inicialización async: crear tablas, migraciones, seasons"""
        await self._init_database()
        await self._run_migrations()
        await self._auto_initialize_seasons()
        self.log.info(f"Base de datos lista: {self.db_path}")

    async def _init_database(self):
        """Crear todas las tablas necesarias para v1.0"""
        async with self.get_connection() as conn:

            # ==================== TABLA SERVERS ====================
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS servers (
                    guild_id INTEGER PRIMARY KEY,
                    pole_channel_id INTEGER,

                    -- Sistema de hora aleatoria (v1.0)
                    daily_pole_time TIME,
                    last_daily_pole_time TIME,
                    pole_range_start INTEGER DEFAULT 8,
                    pole_range_end INTEGER DEFAULT 20,
                    notify_opening BOOLEAN DEFAULT 1,

                    -- Configuración de notificaciones
                    notify_winner BOOLEAN DEFAULT 1,
                    ping_role_id INTEGER,
                    ping_mode TEXT DEFAULT 'none',

                    -- Bloqueo primer día
                    first_pole_date TEXT,

                    -- Timestamps
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # ==================== TABLA USERS ====================
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER,
                    guild_id INTEGER,
                    username TEXT,

                    -- Contadores por categoría (v1.0: por velocidad)
                    critical_poles INTEGER DEFAULT 0,
                    fast_poles INTEGER DEFAULT 0,
                    normal_poles INTEGER DEFAULT 0,
                    late_poles INTEGER DEFAULT 0,
                    marranero_poles INTEGER DEFAULT 0,

                    -- Sistema de rachas
                    current_streak INTEGER DEFAULT 0,
                    best_streak INTEGER DEFAULT 0,
                    last_pole_date TEXT,

                    -- Estadísticas de velocidad (v1.0)
                    average_delay_minutes REAL DEFAULT 0,
                    best_time_minutes INTEGER,

                    -- Stats secretas para POLE REWIND (v2.1)
                    impatient_attempts INTEGER DEFAULT 0,

                    -- Representación de servidor (v1.0 global)
                    represented_guild_id INTEGER,

                    -- Timestamps
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

                    PRIMARY KEY (user_id, guild_id)
                )
            ''')

            # ==================== TABLA POLES ====================
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS poles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    guild_id INTEGER,

                    -- Sistema v1.0: Hora aleatoria
                    opening_time DATETIME NOT NULL,
                    user_time DATETIME NOT NULL,
                    delay_minutes INTEGER NOT NULL,

                    -- Fecha efectiva del pole (para marranero es el día anterior)
                    pole_date TEXT,

                    -- Tipo y puntos
                    pole_type TEXT,
                    points_earned REAL,
                    streak_at_time INTEGER,

                    -- Timestamps
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (user_id, guild_id) REFERENCES users(user_id, guild_id)
                )
            ''')

            # ==================== TABLA ACHIEVEMENTS ====================
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS achievements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    guild_id INTEGER,
                    achievement_id TEXT,
                    unlocked_at DATETIME DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (user_id, guild_id) REFERENCES users(user_id, guild_id)
                )
            ''')

            # ==================== TABLA PUTA_COUNTER ====================
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS puta_counter (
                    guild_id INTEGER NOT NULL,
                    user_id INTEGER NOT NULL,
                    total_count INTEGER DEFAULT 0,
                    updated_at TEXT,
                    PRIMARY KEY (guild_id, user_id)
                )
            ''')

            # ==================== ÍNDICES ====================
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_users_guild ON users(guild_id)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_poles_user ON poles(user_id, guild_id)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_poles_date ON poles(created_at)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_poles_pole_date ON poles(pole_date)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_puta_counter_guild ON puta_counter(guild_id, total_count DESC)')
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_puta_counter_guild_count_user ON puta_counter(guild_id, total_count DESC, user_id ASC)')
            try:
                await conn.execute('CREATE INDEX IF NOT EXISTS idx_season_stats_lookup ON season_stats(user_id, guild_id, season_id)')
            except Exception:
                pass  # season_stats puede no existir aún en primer inicio

    async def _get_schema_version(self) -> int:
        """Obtener la versión actual del schema de la base de datos"""
        async with self.get_connection() as conn:
            try:
                cursor = await conn.execute('SELECT version FROM schema_metadata ORDER BY version DESC LIMIT 1')
                row = await cursor.fetchone()
                return row[0] if row else 0
            except Exception:
                # Tabla schema_metadata no existe, crear
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS schema_metadata (
                        version INTEGER PRIMARY KEY,
                        applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        description TEXT
                    )
                ''')
                return 0

    async def _set_schema_version(self, conn, version: int, description: str):
        """Registrar que una migración fue aplicada (usa conexión existente)"""
        await conn.execute('''
            INSERT OR REPLACE INTO schema_metadata (version, applied_at, description)
            VALUES (?, CURRENT_TIMESTAMP, ?)
        ''', (version, description))

    async def _run_migrations(self):
        """Ejecutar migraciones pendientes de forma segura"""
        current_version = await self._get_schema_version()

        self.log.debug(f"Schema actual: v{current_version}, Target: v{self.SCHEMA_VERSION}")

        if current_version >= self.SCHEMA_VERSION:
            self.log.debug(f"Base de datos ya está en v{self.SCHEMA_VERSION}")
            return

        self.log.info(f"🔄 Ejecutando migraciones desde v{current_version} a v{self.SCHEMA_VERSION}...")

        async with self.get_connection() as conn:

            # MIGRACIÓN v1 → v2: Añadir pole_date
            if current_version < 2:
                try:
                    await conn.execute('ALTER TABLE poles ADD COLUMN pole_date TEXT')
                    await conn.execute('UPDATE poles SET pole_date = DATE(user_time) WHERE pole_date IS NULL')
                    await self._set_schema_version(conn, 2, "Añadida columna pole_date a poles")
                    self.log.info("✅ Migración v2: columna pole_date añadida")
                except Exception as e:
                    if "duplicate column" not in str(e).lower():
                        raise
                    self.log.info("ℹ️  Migración v2: columna pole_date ya existe")
                    await self._set_schema_version(conn, 2, "Columna pole_date ya existía")

            # MIGRACIÓN v2 → v3: Añadir last_daily_pole_time
            if current_version < 3:
                try:
                    await conn.execute('ALTER TABLE servers ADD COLUMN last_daily_pole_time TIME')
                    await self._set_schema_version(conn, 3, "Añadida columna last_daily_pole_time a servers")
                    self.log.info("✅ Migración v3: columna last_daily_pole_time añadida")
                except Exception as e:
                    if "duplicate column" not in str(e).lower():
                        raise
                    self.log.info("ℹ️  Migración v3: columna last_daily_pole_time ya existe")
                    await self._set_schema_version(conn, 3, "Columna last_daily_pole_time ya existía")

            # MIGRACIÓN v3 → v4: Añadir impatient_attempts (stat secreta)
            if current_version < 4:
                try:
                    await conn.execute('ALTER TABLE users ADD COLUMN impatient_attempts INTEGER DEFAULT 0')
                    await self._set_schema_version(conn, 4, "Añadida columna impatient_attempts a users")
                    self.log.info("✅ Migración v4: columna impatient_attempts añadida")
                except Exception as e:
                    if "duplicate column" not in str(e).lower():
                        raise
                    self.log.info("ℹ️  Migración v4: columna impatient_attempts ya existe")
                    await self._set_schema_version(conn, 4, "Columna impatient_attempts ya existía")

            # MIGRACIÓN v4 → v5: Crear tabla global_users y migrar rachas
            if current_version < 5:
                self.log.info("Migración v5: Creando sistema de rachas globales...")

                # Flush cualquier transacción pendiente antes del bloque DDL
                await conn.commit()

                # Desactivar foreign keys para permitir DROP TABLE
                await conn.execute('PRAGMA foreign_keys = OFF')

                # Verificar que se desactivaron
                cursor = await conn.execute('PRAGMA foreign_keys')
                fk_row = await cursor.fetchone()
                fk_status = fk_row[0] if fk_row else 1
                self.log.warning(f"   🔧 Foreign keys: {'OFF' if fk_status == 0 else 'ON (⚠️ ADVERTENCIA)'}")

                # Limpiar residuos de intentos fallidos previos
                await conn.execute('DROP TABLE IF EXISTS users_new')

                # Respaldar global_users si existe
                cursor = await conn.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type = 'table' AND name = 'global_users'
                """)
                if await cursor.fetchone():
                    await conn.execute('''
                        CREATE TABLE IF NOT EXISTS global_users_backup_v5 AS
                        SELECT * FROM global_users
                    ''')
                    await conn.execute('DROP TABLE global_users')

                self.log.info("   🧹 Limpieza de tablas temporales completada (respaldo de global_users si existía)")

                # Crear tabla global_users
                await conn.execute('''
                    CREATE TABLE global_users (
                        user_id INTEGER PRIMARY KEY,
                        username TEXT,

                        -- Rachas GLOBALES (compartidas entre todos los servidores)
                        current_streak INTEGER DEFAULT 0,
                        best_streak INTEGER DEFAULT 0,
                        last_pole_date TEXT,

                        -- Representación de servidor (global)
                        represented_guild_id INTEGER,

                        -- Timestamps
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                # Migrar datos existentes: consolidar rachas de todos los servidores
                self.log.info("   📊 Consolidando rachas de usuarios...")

                cursor = await conn.execute('''
                    SELECT
                        u.user_id,
                        MAX(u.username) as username,
                        MAX(u.current_streak) as best_current_streak,
                        MAX(u.best_streak) as best_overall_streak,
                        MAX(u.last_pole_date) as most_recent_pole,
                        (
                            SELECT u2.guild_id
                            FROM users u2
                            WHERE u2.user_id = u.user_id
                            ORDER BY u2.best_streak DESC, u2.critical_poles DESC
                            LIMIT 1
                        ) as primary_guild_id
                    FROM users u
                    GROUP BY u.user_id
                ''')

                users_to_migrate = await cursor.fetchall()
                migrated_count = 0

                for user in users_to_migrate:
                    await conn.execute('''
                        INSERT OR REPLACE INTO global_users
                        (user_id, username, current_streak, best_streak, last_pole_date, represented_guild_id)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        user[0],  # user_id
                        user[1],  # username
                        user[2],  # best_current_streak de todos los servidores
                        user[3],  # best_overall_streak de todos los servidores
                        user[4],  # most_recent_pole
                        user[5]   # primary_guild_id
                    ))
                    migrated_count += 1

                # Crear tabla users_new (sin columnas de racha)
                await conn.execute('''
                    CREATE TABLE users_new (
                        user_id INTEGER,
                        guild_id INTEGER,
                        username TEXT,

                        -- Contadores por categoría (v1.0: por velocidad)
                        critical_poles INTEGER DEFAULT 0,
                        fast_poles INTEGER DEFAULT 0,
                        normal_poles INTEGER DEFAULT 0,
                        late_poles INTEGER DEFAULT 0,
                        marranero_poles INTEGER DEFAULT 0,

                        -- Estadísticas de velocidad (v1.0) - LOCALES
                        average_delay_minutes REAL DEFAULT 0,
                        best_time_minutes INTEGER,

                        -- Stats secretas para POLE REWIND (v2.1)
                        impatient_attempts INTEGER DEFAULT 0,

                        -- Timestamps
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

                        PRIMARY KEY (user_id, guild_id)
                    )
                ''')

                # Copiar datos (sin las columnas de racha)
                await conn.execute('''
                    INSERT INTO users_new
                    SELECT
                        user_id, guild_id, username,
                        critical_poles, fast_poles, normal_poles, late_poles, marranero_poles,
                        average_delay_minutes, best_time_minutes,
                        impatient_attempts,
                        created_at, updated_at
                    FROM users
                ''')

                # Reemplazar tabla
                await conn.execute('DROP TABLE users')
                await conn.execute('ALTER TABLE users_new RENAME TO users')

                # Crear índices para tabla global_users
                await conn.execute('CREATE INDEX IF NOT EXISTS idx_global_users_streak ON global_users(current_streak DESC)')
                await conn.execute('CREATE INDEX IF NOT EXISTS idx_global_users_best ON global_users(best_streak DESC)')

                # Reactivar foreign keys
                await conn.execute('PRAGMA foreign_keys = ON')

                # Verificar integridad
                cursor = await conn.execute('PRAGMA foreign_key_check')
                integrity = list(await cursor.fetchall())
                if integrity:
                    self.log.warning(f"   ⚠️ Advertencia: {len(integrity)} violaciones de foreign key detectadas")
                    for violation in list(integrity)[:5]:
                        self.log.info(f"      {violation}")
                else:
                    self.log.info("   ✅ Verificación de integridad: OK")

                await self._set_schema_version(conn, 5, f"Sistema de rachas globales creado. {migrated_count} usuarios migrados")
                self.log.info(f"Migración v5: {migrated_count} usuarios migrados a rachas globales")

            # ==================== MIGRACIÓN v6: Sistema i18n ====================
            if current_version < 6:
                self.log.info("Migración v6: Sistema de internacionalización (i18n)...")

                try:
                    await conn.execute("ALTER TABLE servers ADD COLUMN language TEXT DEFAULT 'es'")
                    self.log.info("Columna 'language' añadida a tabla servers")
                except Exception:
                    self.log.debug("Columna 'language' ya existe, saltando...")

                await self._set_schema_version(conn, 6, "Sistema de internacionalización (i18n) implementado")
                self.log.info("✅ Migración v6: Sistema i18n listo. Idiomas disponibles: es, en")

            # ==================== MIGRACIÓN v7: notification_sent_at ====================
            if current_version < 7:
                self.log.info("Migración v7: Timestamp real de notificación para cálculo justo de delays...")

                try:
                    await conn.execute("ALTER TABLE servers ADD COLUMN notification_sent_at TEXT DEFAULT NULL")
                    self.log.info("   Columna 'notification_sent_at' añadida a tabla servers")
                except Exception:
                    self.log.debug("   Columna 'notification_sent_at' ya existe, saltando...")

                await self._set_schema_version(conn, 7, "Sistema de delays justos (desde notificación real)")
                self.log.info("✅ Migración v7: Delays ahora se calculan desde notificación enviada, no hora programada")

            # ==================== MIGRACIÓN v8: puta_counter ====================
            if current_version < 8:
                self.log.info("Migración v8: Activando contador global de putómetro...")

                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS puta_counter (
                        guild_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        total_count INTEGER DEFAULT 0,
                        updated_at TEXT,
                        PRIMARY KEY (guild_id, user_id)
                    )
                ''')
                await conn.execute('CREATE INDEX IF NOT EXISTS idx_puta_counter_guild ON puta_counter(guild_id, total_count DESC)')
                await conn.execute('CREATE INDEX IF NOT EXISTS idx_puta_counter_guild_count_user ON puta_counter(guild_id, total_count DESC, user_id ASC)')

                await self._set_schema_version(conn, 8, "Sistema de putómetro por usuario/guild")
                self.log.info("✅ Migración v8: Putómetro listo")

    async def _auto_initialize_seasons(self):
        """
        Auto-inicialización del sistema de seasons (transparente en primer inicio)
        """
        async with self.get_connection() as conn:

            # Verificar si ya existe la tabla seasons
            cursor = await conn.execute('''
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='seasons'
            ''')
            table_exists = await cursor.fetchone() is not None

            if not table_exists:
                self.log.info("🔄 Primera inicialización: Creando tablas de seasons...")

            # ==================== TABLA SEASONS ====================
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS seasons (
                    season_id TEXT PRIMARY KEY,
                    season_name TEXT NOT NULL,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    is_ranked BOOLEAN DEFAULT 1,
                    is_active BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # ==================== TABLA SEASON_STATS ====================
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS season_stats (
                    user_id INTEGER,
                    guild_id INTEGER,
                    season_id TEXT,

                    -- Puntos y poles de la season
                    season_points REAL DEFAULT 0,
                    season_poles INTEGER DEFAULT 0,

                    -- Contadores por categoría
                    season_critical INTEGER DEFAULT 0,
                    season_fast INTEGER DEFAULT 0,
                    season_normal INTEGER DEFAULT 0,
                    season_marranero INTEGER DEFAULT 0,

                    -- Mejor racha alcanzada en esta season
                    season_best_streak INTEGER DEFAULT 0,

                    -- Rango final
                    final_rank TEXT,
                    final_badge TEXT,

                    -- Timestamps
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,

                    PRIMARY KEY (user_id, guild_id, season_id),
                    FOREIGN KEY (season_id) REFERENCES seasons(season_id)
                )
            ''')

            # ==================== TABLA SEASON_HISTORY ====================
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS season_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    guild_id INTEGER,
                    season_id TEXT,

                    -- Resultados finales
                    final_points REAL,
                    final_rank TEXT,
                    final_badge TEXT,
                    final_position INTEGER,
                    total_players INTEGER,

                    -- Estadísticas
                    total_poles INTEGER,
                    best_streak INTEGER,
                    critical_count INTEGER,
                    fast_count INTEGER,
                    normal_count INTEGER,
                    marranero_count INTEGER,

                    -- Timestamps
                    season_ended_at DATETIME DEFAULT CURRENT_TIMESTAMP,

                    FOREIGN KEY (season_id) REFERENCES seasons(season_id)
                )
            ''')

            # ==================== TABLA USER_BADGES ====================
            await conn.execute('''
                CREATE TABLE IF NOT EXISTS user_badges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    guild_id INTEGER,
                    season_id TEXT,
                    badge_type TEXT,
                    badge_emoji TEXT,
                    earned_at DATETIME DEFAULT CURRENT_TIMESTAMP,

                    UNIQUE(user_id, guild_id, season_id, badge_type)
                )
            ''')

            # Crear índice de season_stats aquí, donde la tabla sí existe
            await conn.execute('CREATE INDEX IF NOT EXISTS idx_season_stats_lookup ON season_stats(user_id, guild_id, season_id)')

            # ==================== INICIALIZAR TEMPORADAS ====================
            from utils.scoring import get_current_season, get_season_info

            cursor = await conn.execute('SELECT season_id FROM seasons WHERE is_active = 1')
            active_season = await cursor.fetchone()

            if not active_season:
                self.log.info("🔄 Inicializando sistema de temporadas...")

                current_season_id = get_current_season()
                season_info = get_season_info(current_season_id)

                await conn.execute('''
                    INSERT OR IGNORE INTO seasons
                    (season_id, season_name, start_date, end_date, is_ranked, is_active)
                    VALUES (?, ?, ?, ?, ?, 1)
                ''', (
                    season_info['id'],
                    season_info['name'],
                    season_info['start_date'],
                    season_info['end_date'],
                    season_info['is_ranked']
                ))

                if not table_exists:
                    self.log.info(f"✅ Sistema de seasons inicializado:")
                    self.log.info(f"   • {season_info['name']} ({season_info['id']}) activa")
            elif not table_exists:
                self.log.info(f"ℹ️  Sistema de seasons inicializado: {active_season[0]} activa")

    # ==================== MÉTODOS DE SERVIDORES ====================

    async def init_server(self, guild_id: int, channel_id: int):
        """Inicializar configuración de servidor"""
        async with self.get_connection() as conn:
            await conn.execute('''
                INSERT OR IGNORE INTO servers (guild_id, pole_channel_id)
                VALUES (?, ?)
            ''', (guild_id, channel_id))

    async def get_server_config(self, guild_id: int) -> Optional[Dict]:
        """Obtener configuración de servidor"""
        async with self.get_connection() as conn:
            cursor = await conn.execute('SELECT * FROM servers WHERE guild_id = ?', (guild_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def update_server_config(self, guild_id: int, **kwargs):
        """Actualizar configuración de servidor"""
        async with self.get_connection() as conn:
            fields = ', '.join([f"{key} = ?" for key in kwargs.keys()])
            values = list(kwargs.values()) + [guild_id]

            await conn.execute(f'''
                UPDATE servers SET {fields}
                WHERE guild_id = ?
            ''', values)

    async def get_server_language(self, guild_id: int) -> str:
        """Obtener idioma configurado del servidor (default: 'es')"""
        async with self.get_connection() as conn:
            cursor = await conn.execute('SELECT language FROM servers WHERE guild_id = ?', (guild_id,))
            row = await cursor.fetchone()
            return row['language'] if row and row['language'] else 'es'

    async def set_server_language(self, guild_id: int, language: str):
        """Configurar idioma del servidor"""
        async with self.get_connection() as conn:
            await conn.execute('''
                UPDATE servers SET language = ?
                WHERE guild_id = ?
            ''', (language, guild_id))

    async def set_daily_pole_time(self, guild_id: int, time_str: str):
        """Establecer hora de pole del día (formato HH:MM:SS)"""
        config = await self.get_server_config(guild_id)
        if not config:
            await self.init_server(guild_id, 0)
            config = await self.get_server_config(guild_id)

        current_time = config.get('daily_pole_time') if config else None

        if current_time:
            await self.update_server_config(guild_id,
                                            daily_pole_time=time_str,
                                            last_daily_pole_time=current_time)
        else:
            await self.update_server_config(guild_id, daily_pole_time=time_str)

    async def get_daily_pole_time(self, guild_id: int) -> Optional[str]:
        """Obtener hora de pole del día"""
        config = await self.get_server_config(guild_id)
        return config.get('daily_pole_time') if config else None

    async def get_last_daily_pole_time(self, guild_id: int) -> Optional[str]:
        """Obtener la hora de apertura generada AYER (para cálculo de margen)"""
        config = await self.get_server_config(guild_id)
        return config.get('last_daily_pole_time') if config else None

    async def set_notification_sent_at(self, guild_id: int, timestamp: str):
        """Guardar timestamp de cuando se envió la notificación (ISO format)"""
        await self.update_server_config(guild_id, notification_sent_at=timestamp)

    async def get_notification_sent_at(self, guild_id: int) -> Optional[str]:
        """Obtener timestamp de cuando se envió la notificación de apertura"""
        config = await self.get_server_config(guild_id)
        return config.get('notification_sent_at') if config else None

    async def clear_notification_sent_at(self, guild_id: int):
        """Limpiar timestamp de notificación (al generar nueva hora)"""
        await self.update_server_config(guild_id, notification_sent_at=None)

    # ==================== MÉTODOS DE USUARIOS ====================

    async def get_user(self, user_id: int, guild_id: int) -> Optional[Dict]:
        """Obtener datos de usuario con totales calculados dinámicamente desde seasons"""
        async with self.get_connection() as conn:
            cursor = await conn.execute('''
                SELECT * FROM users
                WHERE user_id = ? AND guild_id = ?
            ''', (user_id, guild_id))
            row = await cursor.fetchone()

            if not row:
                return None

            user_data = dict(row)

            cursor = await conn.execute('''
                SELECT
                    COALESCE(SUM(season_points), 0) as total_points,
                    COALESCE(SUM(season_poles), 0) as total_poles
                FROM season_stats
                WHERE user_id = ? AND guild_id = ?
            ''', (user_id, guild_id))
            totals = await cursor.fetchone()

            user_data['total_points'] = float(totals['total_points']) if totals else 0.0
            user_data['total_poles'] = int(totals['total_poles']) if totals else 0

            return user_data

    async def create_user(self, user_id: int, guild_id: int, username: str):
        """Crear nuevo usuario"""
        async with self.get_connection() as conn:
            await conn.execute('''
                INSERT OR IGNORE INTO users (user_id, guild_id, username)
                VALUES (?, ?, ?)
            ''', (user_id, guild_id, username))

    async def update_user(self, user_id: int, guild_id: int, **kwargs):
        """Actualizar datos de usuario"""
        async with self.get_connection() as conn:
            kwargs['updated_at'] = datetime.now(tz=LOCAL_TZ).isoformat()

            fields = ', '.join([f"{key} = ?" for key in kwargs.keys()])
            values = list(kwargs.values()) + [user_id, guild_id]

            await conn.execute(f'''
                UPDATE users SET {fields}
                WHERE user_id = ? AND guild_id = ?
            ''', values)

    async def increment_impatient_attempts(self, user_id: int, guild_id: int):
        """Incrementar contador de intentos impacientes (stat secreta para POLE REWIND)"""
        async with self.get_connection() as conn:
            await conn.execute('''
                UPDATE users
                SET impatient_attempts = impatient_attempts + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND guild_id = ?
            ''', (user_id, guild_id))

    # ==================== MÉTODOS DE GLOBAL_USERS (RACHAS GLOBALES) ====================

    async def get_global_user(self, user_id: int) -> Optional[Dict]:
        """Obtener datos globales de un usuario (rachas compartidas entre servidores)"""
        async with self.get_connection() as conn:
            cursor = await conn.execute('SELECT * FROM global_users WHERE user_id = ?', (user_id,))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def create_global_user(self, user_id: int, username: str):
        """Crear usuario global si no existe"""
        async with self.get_connection() as conn:
            await conn.execute('''
                INSERT OR IGNORE INTO global_users (user_id, username)
                VALUES (?, ?)
            ''', (user_id, username))

    async def update_global_user(self, user_id: int, **kwargs):
        """Actualizar datos globales de usuario (rachas, representación, etc.)"""
        async with self.get_connection() as conn:
            kwargs['updated_at'] = datetime.now(tz=LOCAL_TZ).isoformat()

            fields = ', '.join([f"{key} = ?" for key in kwargs.keys()])
            values = list(kwargs.values()) + [user_id]

            await conn.execute(f'''
                UPDATE global_users SET {fields}
                WHERE user_id = ?
            ''', values)

    async def get_or_create_global_user(self, user_id: int, username: str) -> Optional[Dict]:
        """Obtener o crear usuario global"""
        user = await self.get_global_user(user_id)
        if not user:
            await self.create_global_user(user_id, username)
            user = await self.get_global_user(user_id)
        return user

    async def record_pole_and_update_streak_atomic(
        self,
        *,
        user_id: int,
        guild_id: int,
        username: str,
        opening_time: datetime,
        user_time: datetime,
        delay_minutes: int,
        pole_type: str,
        effective_date: str,
        pole_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Registrar un pole y actualizar racha global de forma atómica.

        Esta operación es idempotente por (user_id, effective_date): si ya existe
        un pole global para esa fecha efectiva, no vuelve a incrementar racha.
        """
        from utils.scoring import calculate_points, update_streak

        # Normalizar datetimes para evitar mezclas naive/aware en persistencia.
        opening_time_local = opening_time.replace(tzinfo=LOCAL_TZ) if opening_time.tzinfo is None else opening_time.astimezone(LOCAL_TZ)
        user_time_local = user_time.replace(tzinfo=LOCAL_TZ) if user_time.tzinfo is None else user_time.astimezone(LOCAL_TZ)
        # La fecha efectiva del pole SIEMPRE debe venir del calendario local (Europe/Madrid).
        # Si llega una distinta por error, priorizamos effective_date para mantener rachas coherentes.
        pole_date_value = pole_date or effective_date
        if pole_date_value != effective_date:
            self.log.warning(
                "pole_date (%s) distinto de effective_date (%s) para user_id=%s. Se usará effective_date.",
                pole_date_value,
                effective_date,
                user_id,
            )
            pole_date_value = effective_date

        async with self.get_connection() as conn:
            # Serializa writers para cerrar ventanas de carrera en rachas globales.
            await conn.execute('BEGIN IMMEDIATE')

            # Idempotencia global: un único pole por usuario y fecha efectiva.
            cursor = await conn.execute('''
                SELECT id, guild_id FROM poles
                WHERE user_id = ?
                                    AND pole_date = ?
                ORDER BY user_time ASC
                LIMIT 1
                        ''', (user_id, pole_date_value))
            existing_pole = await cursor.fetchone()
            if existing_pole:
                return {
                    'accepted': False,
                    'existing_pole_id': existing_pole['id'],
                    'existing_guild_id': existing_pole['guild_id']
                }

            # Garantizar fila global para poder calcular racha con estado consistente.
            await conn.execute('''
                INSERT OR IGNORE INTO global_users (user_id, username)
                VALUES (?, ?)
            ''', (user_id, username))

            cursor = await conn.execute('''
                SELECT current_streak, best_streak, last_pole_date
                FROM global_users
                WHERE user_id = ?
            ''', (user_id,))
            global_row = await cursor.fetchone()

            current_streak = int(global_row['current_streak'] or 0) if global_row else 0
            best_streak = int(global_row['best_streak'] or 0) if global_row else 0
            last_pole_date = global_row['last_pole_date'] if global_row else None

            # Si llega una escritura de una fecha anterior a la última registrada,
            # se rechaza para no corromper el estado de racha por out-of-order writes.
            if last_pole_date and effective_date < last_pole_date:
                return {
                    'accepted': False,
                    'reason': 'stale_effective_date'
                }

            new_streak, streak_broken = update_streak(
                last_pole_date,
                current_streak,
                current_date=effective_date
            )
            points_base, streak_multiplier, points_earned = calculate_points(pole_type, new_streak)
            new_best_streak = max(best_streak, int(new_streak))
            now_iso = datetime.now(LOCAL_TZ).isoformat()

            await conn.execute('''
                INSERT INTO poles (
                    user_id, guild_id, opening_time, user_time,
                    delay_minutes, pole_date, pole_type, points_earned, streak_at_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                user_id, guild_id, opening_time_local, user_time_local,
                delay_minutes, pole_date_value, pole_type, points_earned, new_streak
            ))

            await conn.execute('''
                UPDATE global_users
                SET username = ?,
                    current_streak = ?,
                    best_streak = ?,
                    last_pole_date = ?,
                    updated_at = ?
                WHERE user_id = ?
            ''', (
                username,
                int(new_streak),
                int(new_best_streak),
                effective_date,
                now_iso,
                user_id
            ))

            return {
                'accepted': True,
                'new_streak': int(new_streak),
                'streak_broken': bool(streak_broken),
                'best_streak': int(new_best_streak),
                'points_base': float(points_base),
                'streak_multiplier': float(streak_multiplier),
                'points_earned': float(points_earned),
                'pole_date_saved': pole_date_value,
            }

    async def get_user_global_stats(self, user_id: int) -> Optional[Dict]:
        """Obtener estadísticas globales del usuario (sumando TODOS los servidores)"""
        async with self.get_connection() as conn:
            cursor = await conn.execute('''
                SELECT
                    SUM(critical_poles) as critical_poles,
                    SUM(fast_poles) as fast_poles,
                    SUM(normal_poles) as normal_poles,
                    SUM(late_poles) as late_poles,
                    SUM(marranero_poles) as marranero_poles,
                    AVG(average_delay_minutes) as average_delay_minutes,
                    MIN(best_time_minutes) as best_time_minutes
                FROM users
                WHERE user_id = ?
            ''', (user_id,))

            stats = await cursor.fetchone()

            if not stats or stats['critical_poles'] is None:
                return None

            cursor = await conn.execute('''
                SELECT
                    SUM(season_points) as total_points,
                    SUM(season_poles) as total_poles
                FROM season_stats
                WHERE user_id = ?
            ''', (user_id,))

            points_data = await cursor.fetchone()

            return {
                'user_id': user_id,
                'critical_poles': stats['critical_poles'] or 0,
                'fast_poles': stats['fast_poles'] or 0,
                'normal_poles': stats['normal_poles'] or 0,
                'late_poles': stats['late_poles'] or 0,
                'marranero_poles': stats['marranero_poles'] or 0,
                'average_delay_minutes': stats['average_delay_minutes'] or 0.0,
                'best_time_minutes': stats['best_time_minutes'] or 0,
                'total_points': (points_data['total_points'] if points_data else 0.0) or 0.0,
                'total_poles': (points_data['total_poles'] if points_data else 0) or 0
            }

    # ==================== MÉTODOS DE POLES ====================

    async def save_pole(self, user_id: int, guild_id: int, opening_time: datetime,
                        user_time: datetime, delay_minutes: int, pole_type: str,
                        points_earned: float, streak: int, pole_date: Optional[str] = None):
        """Guardar pole en historial"""
        if pole_date is None:
            user_time_local = user_time.replace(tzinfo=LOCAL_TZ) if user_time.tzinfo is None else user_time.astimezone(LOCAL_TZ)
            pole_date = user_time_local.date().isoformat()

        async with self.get_connection() as conn:
            await conn.execute('''
                INSERT INTO poles (
                    user_id, guild_id, opening_time, user_time,
                    delay_minutes, pole_date, pole_type, points_earned, streak_at_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, guild_id, opening_time, user_time,
                  delay_minutes, pole_date, pole_type, points_earned, streak))

    async def get_user_poles(self, user_id: int, guild_id: int, limit: int = 50) -> List[Dict]:
        """Obtener historial de poles de un usuario"""
        async with self.get_connection() as conn:
            cursor = await conn.execute('''
                SELECT * FROM poles
                WHERE user_id = ? AND guild_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (user_id, guild_id, limit))
            return [dict(row) for row in await cursor.fetchall()]

    async def get_poles_today(self, guild_id: int, use_pole_date: bool = False) -> List[Dict]:
        """Obtener todos los poles del día actual"""
        async with self.get_connection() as conn:
            today = datetime.now(tz=LOCAL_TZ).date().isoformat()

            # Compatibilidad: mantenemos el parámetro use_pole_date, pero la fuente
            # de verdad para fecha efectiva es siempre pole_date (Madrid).
            cursor = await conn.execute('''
                SELECT * FROM poles
                WHERE guild_id = ? AND pole_date = ?
                ORDER BY user_time ASC
            ''', (guild_id, today))
            return [dict(row) for row in await cursor.fetchall()]

    async def get_last_pole_opening_time(self, guild_id: int) -> Optional[str]:
        """Obtener la hora de apertura (HH:MM:SS) del último pole registrado"""
        async with self.get_connection() as conn:
            cursor = await conn.execute('''
                SELECT opening_time FROM poles
                WHERE guild_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            ''', (guild_id,))
            row = await cursor.fetchone()
            if row and row['opening_time']:
                dt = datetime.fromisoformat(str(row['opening_time']))
                return dt.strftime('%H:%M:%S')
            return None

    async def get_user_pole_today_global(self, user_id: int) -> Optional[Dict]:
        """Obtener el pole de hoy de un usuario en cualquier servidor (si existe)"""
        async with self.get_connection() as conn:
            today = datetime.now(tz=LOCAL_TZ).date().isoformat()
            cursor = await conn.execute('''
                SELECT * FROM poles
                WHERE user_id = ? AND pole_date = ?
                ORDER BY user_time ASC
                LIMIT 1
            ''', (user_id, today))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_user_pole_on_date_global(self, user_id: int, date_str: str, exclude_created_today: bool = False) -> Optional[Dict]:
        """Verificar si un usuario hizo pole en CUALQUIER servidor en una fecha específica.

        Nota de compatibilidad:
        - exclude_created_today=True mantiene el contrato histórico de process_pole,
          pero internamente se implementa excluyendo poles tipo 'marranero' para
          evitar depender de DATE(created_at) (UTC).
        """
        async with self.get_connection() as conn:
            if exclude_created_today:
                cursor = await conn.execute('''
                    SELECT * FROM poles
                    WHERE user_id = ?
                      AND pole_date = ?
                      AND pole_type != 'marranero'
                    ORDER BY user_time ASC
                    LIMIT 1
                ''', (user_id, date_str))
            else:
                cursor = await conn.execute('''
                    SELECT * FROM poles
                    WHERE user_id = ? AND pole_date = ?
                    ORDER BY user_time ASC
                    LIMIT 1
                ''', (user_id, date_str))

            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_user_pole_dates_global(self, user_id: int, limit: int = 120) -> List[str]:
        """Obtener lista de fechas en las que el usuario hizo pole en cualquier servidor."""
        async with self.get_connection() as conn:
            cursor = await conn.execute('''
                SELECT DISTINCT pole_date as effective_date
                FROM poles
                WHERE user_id = ?
                  AND pole_date IS NOT NULL
                ORDER BY effective_date DESC
                LIMIT ?
            ''', (user_id, limit))
            return [row['effective_date'] for row in await cursor.fetchall()]

    async def user_has_pole_on_date(self, user_id: int, guild_id: int, date_str: str) -> bool:
        """Verificar si un usuario hizo pole en una fecha específica (YYYY-MM-DD)"""
        async with self.get_connection() as conn:
            cursor = await conn.execute('''
                SELECT COUNT(*) FROM poles
                WHERE user_id = ? AND guild_id = ?
                  AND pole_date = ?
            ''', (user_id, guild_id, date_str))
            row = await cursor.fetchone()
            return bool(row and row[0] > 0)

    # ==================== MÉTODOS DE LEADERBOARD ====================

    async def get_leaderboard(self, guild_id: int, limit: int = 10, order_by: str = 'points') -> List[Dict]:
        """Obtener ranking del servidor con totales calculados desde seasons"""
        async with self.get_connection() as conn:
            if order_by == 'points':
                order_clause = 'total_points DESC'
            elif order_by == 'streak':
                order_clause = 'u.current_streak DESC, total_points DESC'
            elif order_by == 'speed':
                order_clause = 'u.average_delay_minutes ASC'
            else:
                order_clause = 'total_points DESC'

            cursor = await conn.execute(f'''
                SELECT
                    u.*,
                    COALESCE(SUM(ss.season_points), 0) as total_points,
                    COALESCE(SUM(ss.season_poles), 0) as total_poles
                FROM users u
                LEFT JOIN season_stats ss ON u.user_id = ss.user_id AND u.guild_id = ss.guild_id
                WHERE u.guild_id = ?
                GROUP BY u.user_id, u.guild_id
                HAVING total_poles > 0
                ORDER BY {order_clause}
                LIMIT ?
            ''', (guild_id, limit))
            return [dict(row) for row in await cursor.fetchall()]

    async def get_global_leaderboard(self, limit: int = 10, order_by: str = 'points') -> List[Dict]:
        """Ranking global por usuario (agregado en todos los servidores) con totales desde seasons"""
        async with self.get_connection() as conn:
            if order_by == 'points':
                order_clause = 'total_points DESC'
            elif order_by == 'streak':
                order_clause = 'COALESCE(gu.current_streak, 0) DESC, total_points DESC'
            elif order_by == 'speed':
                order_clause = 'AVG(u.average_delay_minutes) ASC'
            else:
                order_clause = 'total_points DESC'

            cursor = await conn.execute(f'''
                SELECT
                    u.user_id,
                    MAX(u.username) AS username,
                    COALESCE(SUM(ss.season_points), 0) AS total_points,
                    COALESCE(SUM(ss.season_poles), 0) AS total_poles,
                    COALESCE(gu.current_streak, 0) AS current_streak,
                    COALESCE(gu.best_streak, 0) AS best_streak,
                    gu.represented_guild_id
                FROM users u
                LEFT JOIN season_stats ss ON u.user_id = ss.user_id AND u.guild_id = ss.guild_id
                LEFT JOIN global_users gu ON u.user_id = gu.user_id
                GROUP BY u.user_id
                HAVING total_poles > 0
                ORDER BY {order_clause}
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in await cursor.fetchall()]

    # ==================== MÉTODOS PUTÓMETRO ====================

    async def increment_puta_counter(self, guild_id: int, user_id: int, amount: int = 1) -> Tuple[int, int]:
        """Incrementar contador de putómetro y devolver (total_usuario, total_guild)."""
        increment = max(1, int(amount))
        now_iso = datetime.now(LOCAL_TZ).isoformat()

        async with self.get_connection() as conn:
            await conn.execute('''
                INSERT INTO puta_counter (guild_id, user_id, total_count, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(guild_id, user_id) DO UPDATE SET
                    total_count = total_count + excluded.total_count,
                    updated_at = excluded.updated_at
            ''', (guild_id, user_id, increment, now_iso))

            cursor = await conn.execute('''
                SELECT total_count
                FROM puta_counter
                WHERE guild_id = ? AND user_id = ?
            ''', (guild_id, user_id))
            user_row = await cursor.fetchone()
            user_total = int(user_row['total_count']) if user_row else 0

            cursor = await conn.execute('''
                SELECT COALESCE(SUM(total_count), 0) as guild_total
                FROM puta_counter
                WHERE guild_id = ?
            ''', (guild_id,))
            guild_row = await cursor.fetchone()
            guild_total = int(guild_row['guild_total']) if guild_row else 0

            return user_total, guild_total

    async def get_puta_user_count(self, guild_id: int, user_id: int) -> int:
        """Obtener total de putómetro para un usuario en un guild."""
        async with self.get_connection() as conn:
            cursor = await conn.execute('''
                SELECT total_count
                FROM puta_counter
                WHERE guild_id = ? AND user_id = ?
            ''', (guild_id, user_id))
            row = await cursor.fetchone()
            return int(row['total_count']) if row else 0

    async def get_puta_guild_total(self, guild_id: int) -> int:
        """Obtener total de putómetro acumulado en un guild."""
        async with self.get_connection() as conn:
            cursor = await conn.execute('''
                SELECT COALESCE(SUM(total_count), 0) as guild_total
                FROM puta_counter
                WHERE guild_id = ?
            ''', (guild_id,))
            row = await cursor.fetchone()
            return int(row['guild_total']) if row else 0

    async def get_puta_user_leaderboard(self, guild_id: int, limit: int = 10) -> List[Dict]:
        """Top usuarios de putómetro en un guild."""
        async with self.get_connection() as conn:
            cursor = await conn.execute('''
                SELECT user_id, total_count
                FROM puta_counter
                WHERE guild_id = ? AND total_count > 0
                ORDER BY total_count DESC, user_id ASC
                LIMIT ?
            ''', (guild_id, limit))
            return [dict(row) for row in await cursor.fetchall()]

    async def get_puta_guild_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Top guilds de putómetro (agregado global)."""
        async with self.get_connection() as conn:
            cursor = await conn.execute('''
                SELECT guild_id,
                       SUM(total_count) as total_count,
                       COUNT(*) as tracked_users
                FROM puta_counter
                GROUP BY guild_id
                HAVING total_count > 0
                ORDER BY total_count DESC, guild_id ASC
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in await cursor.fetchall()]

    async def get_puta_user_rank(self, guild_id: int, user_id: int) -> Optional[int]:
        """Ranking (1-based) de un usuario en putómetro local del guild."""
        user_total = await self.get_puta_user_count(guild_id, user_id)
        if user_total <= 0:
            return None

        async with self.get_connection() as conn:
            cursor = await conn.execute('''
                SELECT COUNT(*) as higher_count
                FROM puta_counter
                WHERE guild_id = ? AND total_count > ?
            ''', (guild_id, user_total))
            row = await cursor.fetchone()
            higher_count = int(row['higher_count']) if row else 0
            return higher_count + 1

    async def get_puta_boss_flash_context(self, guild_id: int, user_id: int, top_limit: int = 3) -> Dict[str, Any]:
        """Snapshot consistente para boss mode: rank del usuario + top N del guild."""
        safe_limit = max(1, min(int(top_limit), 10))

        async with self.get_connection() as conn:
            cursor = await conn.execute('''
                WITH ranked AS (
                    SELECT
                        user_id,
                        total_count,
                        ROW_NUMBER() OVER (ORDER BY total_count DESC, user_id ASC) AS pos
                    FROM puta_counter
                    WHERE guild_id = ? AND total_count > 0
                )
                SELECT
                    COALESCE((SELECT pos FROM ranked WHERE user_id = ?), 0) AS user_rank,
                    COALESCE((SELECT total_count FROM ranked WHERE user_id = ?), 0) AS user_total,
                    (SELECT COUNT(*) FROM ranked) AS total_users
            ''', (guild_id, user_id, user_id))
            summary = await cursor.fetchone()

            cursor = await conn.execute('''
                SELECT user_id, total_count
                FROM puta_counter
                WHERE guild_id = ? AND total_count > 0
                ORDER BY total_count DESC, user_id ASC
                LIMIT ?
            ''', (guild_id, safe_limit))
            top_rows = [dict(row) for row in await cursor.fetchall()]

        return {
            'user_rank': int(summary['user_rank']) if summary else 0,
            'user_total': int(summary['user_total']) if summary else 0,
            'total_users': int(summary['total_users']) if summary else 0,
            'top': top_rows,
        }

    async def get_puta_guild_rank(self, guild_id: int) -> Optional[int]:
        """Ranking (1-based) de un guild en el putómetro global."""
        guild_total = await self.get_puta_guild_total(guild_id)
        if guild_total <= 0:
            return None

        async with self.get_connection() as conn:
            cursor = await conn.execute('''
                SELECT COUNT(*) as higher_count
                FROM (
                    SELECT guild_id, SUM(total_count) as guild_total
                    FROM puta_counter
                    GROUP BY guild_id
                ) ranked
                WHERE ranked.guild_total > ?
            ''', (guild_total,))
            row = await cursor.fetchone()
            higher_count = int(row['higher_count']) if row else 0
            return higher_count + 1

    async def get_puta_guilds_count(self) -> int:
        """Cantidad de guilds con actividad en putómetro global."""
        async with self.get_connection() as conn:
            cursor = await conn.execute('''
                SELECT COUNT(DISTINCT guild_id) as guilds_count
                FROM puta_counter
                WHERE total_count > 0
            ''')
            row = await cursor.fetchone()
            return int(row['guilds_count']) if row else 0

    # ==================== MÉTODOS DEBUG ====================

    # ==================== MÉTODOS DE LOGROS ====================

    async def unlock_achievement(self, user_id: int, guild_id: int, achievement_id: str):
        """Desbloquear logro para usuario"""
        async with self.get_connection() as conn:
            await conn.execute('''
                INSERT OR IGNORE INTO achievements (user_id, guild_id, achievement_id)
                VALUES (?, ?, ?)
            ''', (user_id, guild_id, achievement_id))

    async def get_user_achievements(self, user_id: int, guild_id: int) -> List[str]:
        """Obtener logros desbloqueados de usuario"""
        async with self.get_connection() as conn:
            cursor = await conn.execute('''
                SELECT achievement_id FROM achievements
                WHERE user_id = ? AND guild_id = ?
            ''', (user_id, guild_id))
            return [row['achievement_id'] for row in await cursor.fetchall()]

    async def has_achievement(self, user_id: int, guild_id: int, achievement_id: str) -> bool:
        """Verificar si usuario tiene un logro"""
        achievements = await self.get_user_achievements(user_id, guild_id)
        return achievement_id in achievements

    # ==================== MÉTODOS DE REPRESENTACIÓN ====================

    async def get_represented_guild(self, user_id: int) -> Optional[int]:
        """Obtener el guild_id que representa un usuario globalmente"""
        async with self.get_connection() as conn:
            cursor = await conn.execute('''
                SELECT represented_guild_id FROM global_users
                WHERE user_id = ?
            ''', (user_id,))
            row = await cursor.fetchone()
            return int(row['represented_guild_id']) if row and row['represented_guild_id'] else None

    async def set_represented_guild(self, user_id: int, guild_id: int):
        """Establecer el servidor que representa un usuario"""
        async with self.get_connection() as conn:
            await conn.execute('''
                UPDATE global_users
                SET represented_guild_id = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (guild_id, user_id))

    async def get_global_server_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Ranking global de servidores por suma de puntos de usuarios que los representan"""
        async with self.get_connection() as conn:
            cursor = await conn.execute('''
                SELECT u.represented_guild_id AS guild_id,
                       COALESCE(SUM(ss.season_points), 0) AS total_points,
                       COUNT(DISTINCT u.user_id) AS member_count
                FROM users u
                LEFT JOIN season_stats ss ON u.user_id = ss.user_id AND u.guild_id = ss.guild_id
                WHERE u.represented_guild_id IS NOT NULL
                GROUP BY u.represented_guild_id
                HAVING total_points > 0
                ORDER BY total_points DESC
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in await cursor.fetchall()]

    async def get_local_server_leaderboard(self, guild_id: int, limit: int = 10) -> List[Dict]:
        """Ranking local de servidores representados por miembros de este servidor"""
        async with self.get_connection() as conn:
            cursor = await conn.execute('''
                SELECT u.represented_guild_id AS guild_id,
                       COALESCE(SUM(ss.season_points), 0) AS total_points,
                       COUNT(DISTINCT u.user_id) AS member_count
                FROM users u
                LEFT JOIN season_stats ss ON u.user_id = ss.user_id AND u.guild_id = ss.guild_id
                WHERE u.guild_id = ? AND u.represented_guild_id IS NOT NULL
                GROUP BY u.represented_guild_id
                HAVING total_points > 0
                ORDER BY total_points DESC
                LIMIT ?
            ''', (guild_id, limit))
            return [dict(row) for row in await cursor.fetchall()]

    # ==================== MÉTODOS DE SEASONS ====================

    async def get_season_stats(self, user_id: int, guild_id: int, season_id: str) -> Optional[Dict]:
        """Obtener estadísticas de un usuario en una season específica"""
        async with self.get_connection() as conn:
            cursor = await conn.execute('''
                SELECT * FROM season_stats
                WHERE user_id = ? AND guild_id = ? AND season_id = ?
            ''', (user_id, guild_id, season_id))
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def get_user_best_season_points(self, user_id: int, guild_id: int) -> float:
        """Obtener el máximo de puntos alcanzados por un usuario en cualquier temporada."""
        async with self.get_connection() as conn:
            cursor = await conn.execute('''
                SELECT MAX(season_points) as max_points
                FROM season_stats
                WHERE user_id = ? AND guild_id = ?
            ''', (user_id, guild_id))
            row = await cursor.fetchone()
            return float(row['max_points']) if row and row['max_points'] is not None else 0.0

    async def get_user_total_points(self, user_id: int, guild_id: int) -> float:
        """Obtener puntos totales de un usuario (suma de todas las temporadas)."""
        async with self.get_connection() as conn:
            cursor = await conn.execute('''
                SELECT COALESCE(SUM(season_points), 0) as total_points
                FROM season_stats
                WHERE user_id = ? AND guild_id = ?
            ''', (user_id, guild_id))
            row = await cursor.fetchone()
            return float(row['total_points']) if row else 0.0

    async def get_user_total_poles(self, user_id: int, guild_id: int) -> int:
        """Obtener poles totales de un usuario en un servidor (todas las temporadas)."""
        async with self.get_connection() as conn:
            cursor = await conn.execute('''
                SELECT COALESCE(SUM(season_poles), 0) as total_poles
                FROM season_stats
                WHERE user_id = ? AND guild_id = ?
            ''', (user_id, guild_id))
            row = await cursor.fetchone()
            return int(row['total_poles']) if row else 0

    async def update_season_stats(self, user_id: int, guild_id: int, season_id: str, **kwargs):
        """Actualizar estadísticas de season de un usuario"""
        async with self.get_connection() as conn:
            cursor = await conn.execute('''
                SELECT 1 FROM season_stats
                WHERE user_id = ? AND guild_id = ? AND season_id = ?
            ''', (user_id, guild_id, season_id))

            if await cursor.fetchone():
                set_clause = ', '.join([f"{k} = ?" for k in kwargs.keys()])
                values = list(kwargs.values())
                values.extend([user_id, guild_id, season_id])

                await conn.execute(f'''
                    UPDATE season_stats
                    SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND guild_id = ? AND season_id = ?
                ''', values)
            else:
                columns = ', '.join(kwargs.keys())
                placeholders = ', '.join(['?' for _ in kwargs])
                values = list(kwargs.values())

                await conn.execute(f'''
                    INSERT INTO season_stats (user_id, guild_id, season_id, {columns})
                    VALUES (?, ?, ?, {placeholders})
                ''', [user_id, guild_id, season_id] + values)

    async def get_season_leaderboard(self, guild_id: int, season_id: str, limit: int = 10) -> List[Dict]:
        """Obtener leaderboard de una season local"""
        async with self.get_connection() as conn:
            cursor = await conn.execute('''
                SELECT ss.*, u.username, gu.represented_guild_id
                FROM season_stats ss
                JOIN users u ON ss.user_id = u.user_id AND ss.guild_id = u.guild_id
                LEFT JOIN global_users gu ON ss.user_id = gu.user_id
                WHERE ss.guild_id = ? AND ss.season_id = ?
                ORDER BY ss.season_points DESC
                LIMIT ?
            ''', (guild_id, season_id, limit))
            return [dict(row) for row in await cursor.fetchall()]

    async def get_global_season_leaderboard(self, season_id: str, limit: int = 10) -> List[Dict]:
        """Obtener leaderboard global de una season (todos los servidores)"""
        async with self.get_connection() as conn:
            cursor = await conn.execute('''
                SELECT
                    ss.user_id,
                    MAX(u.username) as username,
                    MAX(gu.represented_guild_id) as represented_guild_id,
                    SUM(ss.season_points) as total_season_points,
                    SUM(ss.season_poles) as total_season_poles,
                    MAX(ss.season_best_streak) as best_season_streak
                FROM season_stats ss
                JOIN users u ON ss.user_id = u.user_id AND ss.guild_id = u.guild_id
                LEFT JOIN global_users gu ON ss.user_id = gu.user_id
                WHERE ss.season_id = ?
                GROUP BY ss.user_id
                ORDER BY total_season_points DESC
                LIMIT ?
            ''', (season_id, limit))
            return [dict(row) for row in await cursor.fetchall()]

    async def get_available_seasons(self) -> List[Dict]:
        """Obtener lista de todas las seasons disponibles."""
        async with self.get_connection() as conn:
            cursor = await conn.execute('''
                SELECT season_id, season_name, is_active, start_date, end_date, is_ranked
                FROM seasons
                ORDER BY start_date DESC
            ''')
            return [dict(row) for row in await cursor.fetchall()]

    async def get_local_server_season_leaderboard(self, guild_id: int, season_id: str, limit: int = 10) -> List[Dict]:
        """Obtener leaderboard local de servidores representados en una season"""
        async with self.get_connection() as conn:
            cursor = await conn.execute('''
                SELECT
                    u.represented_guild_id as guild_id,
                    SUM(ss.season_points) as total_points,
                    COUNT(DISTINCT ss.user_id) as member_count
                FROM season_stats ss
                JOIN users u ON ss.user_id = u.user_id AND ss.guild_id = u.guild_id
                WHERE ss.guild_id = ? AND ss.season_id = ? AND u.represented_guild_id IS NOT NULL
                GROUP BY u.represented_guild_id
                ORDER BY total_points DESC
                LIMIT ?
            ''', (guild_id, season_id, limit))
            return [dict(row) for row in await cursor.fetchall()]

    async def get_guild_active_user_ids(self, guild_id: int) -> List[int]:
        """Obtener lista de user_ids únicos que han hecho pole en un guild"""
        async with self.get_connection() as conn:
            cursor = await conn.execute(
                'SELECT DISTINCT user_id FROM poles WHERE guild_id = ?',
                (guild_id,)
            )
            return [row['user_id'] for row in await cursor.fetchall()]

    async def get_total_active_users(self, guild_id: Optional[int] = None) -> int:
        """Obtener el número total de usuarios que han hecho al menos 1 pole."""
        async with self.get_connection() as conn:
            if guild_id is not None:
                cursor = await conn.execute('SELECT COUNT(DISTINCT user_id) FROM poles WHERE guild_id = ?', (guild_id,))
            else:
                cursor = await conn.execute('SELECT COUNT(DISTINCT user_id) FROM poles')
            row = await cursor.fetchone()
            return int(row[0]) if row else 0

    async def get_global_server_season_leaderboard(self, season_id: str, limit: int = 10) -> List[Dict]:
        """Obtener leaderboard global de servidores representados en una season"""
        async with self.get_connection() as conn:
            cursor = await conn.execute('''
                SELECT
                    u.represented_guild_id as guild_id,
                    SUM(ss.season_points) as total_points,
                    COUNT(DISTINCT ss.user_id) as member_count
                FROM season_stats ss
                JOIN users u ON ss.user_id = u.user_id AND ss.guild_id = u.guild_id
                WHERE ss.season_id = ? AND u.represented_guild_id IS NOT NULL
                GROUP BY u.represented_guild_id
                ORDER BY total_points DESC
                LIMIT ?
            ''', (season_id, limit))
            return [dict(row) for row in await cursor.fetchall()]

    async def finalize_season(self, season_id: str):
        """Finalizar una season: copiar datos a historial y resetear stats"""
        from utils.scoring import get_rank_info

        self.log.info(f"   📊 Iniciando finalización de temporada {season_id}...")

        async with self.get_connection() as conn:
            cursor = await conn.execute('SELECT DISTINCT guild_id FROM season_stats WHERE season_id = ?', (season_id,))
            guilds = [row[0] for row in await cursor.fetchall()]

            self.log.info(f"      └─ Servidores afectados: {len(guilds)}")

            total_saved = 0
            total_badges = 0

            for guild_id in guilds:
                cursor = await conn.execute('''
                    SELECT user_id, season_points, season_poles,
                           season_best_streak, season_critical, season_fast,
                           season_normal, season_marranero
                    FROM season_stats
                    WHERE guild_id = ? AND season_id = ?
                    ORDER BY season_points DESC
                ''', (guild_id, season_id))

                rankings = list(await cursor.fetchall())
                total_players = len(rankings)

                for position, row in enumerate(rankings, start=1):
                    user_id = row[0]
                    points = row[1]

                    badge, rank_name = get_rank_info(points)

                    await conn.execute('''
                        INSERT INTO season_history (
                            user_id, guild_id, season_id,
                            final_points, final_rank, final_badge,
                            final_position, total_players,
                            total_poles, best_streak,
                            critical_count, fast_count, normal_count, marranero_count
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        user_id, guild_id, season_id,
                        points, rank_name, badge,
                        position, total_players,
                        row[2], row[3], row[4], row[5], row[6], row[7]
                    ))
                    total_saved += 1

                    badge_cursor = await conn.execute('''
                        INSERT OR IGNORE INTO user_badges (
                            user_id, guild_id, season_id, badge_type, badge_emoji
                        ) VALUES (?, ?, ?, ?, ?)
                    ''', (user_id, guild_id, season_id, rank_name, badge))
                    if badge_cursor.rowcount > 0:
                        total_badges += 1

            await conn.execute('''
                UPDATE seasons SET is_active = 0 WHERE season_id = ?
            ''', (season_id,))

            self.log.info(f"      └─ ✅ {total_saved} registros guardados en historial")
            self.log.info(f"      └─ ✅ {total_badges} badges otorgados")
            self.log.info(f"      └─ ✅ Temporada marcada como inactiva")

    async def get_user_badges(self, user_id: int, guild_id: int) -> List[Dict]:
        """Obtener todos los badges ganados por un usuario"""
        async with self.get_connection() as conn:
            cursor = await conn.execute('''
                SELECT * FROM user_badges
                WHERE user_id = ? AND guild_id = ?
                ORDER BY earned_at DESC
            ''', (user_id, guild_id))
            return [dict(row) for row in await cursor.fetchall()]

    async def migrate_season(self, target_season_id: Optional[str] = None, force: bool = False) -> bool:
        """Migración unificada de seasons (automática o manual)."""
        from utils.scoring import get_current_season, get_season_info

        self.log.info(f"\n{'='*60}")
        self.log.info(f"🔄 INICIO DE MIGRACIÓN DE TEMPORADA")
        self.log.info(f"{'='*60}")
        self.log.info(f"⏰ Timestamp: {datetime.now(tz=LOCAL_TZ).strftime('%Y-%m-%d %H:%M:%S')}")

        if target_season_id is None:
            target_season_id = get_current_season()

        self.log.info(f"🎯 Temporada objetivo: {target_season_id}")
        self.log.debug(f"🔧 Modo force: {force}")

        async with self.get_connection() as conn:
            self.log.debug(f"\n📋 PASO 0: Verificando temporada activa actual...")
            cursor = await conn.execute('SELECT season_id FROM seasons WHERE is_active = 1')
            row = await cursor.fetchone()
            active_season = row[0] if row else None
            self.log.info(f"   └─ Temporada activa: {active_season if active_season else 'Ninguna'}")

            if active_season == target_season_id and not force:
                self.log.info(f"   └─ ℹ️  Ya estamos en {target_season_id}, no se requiere migración")
                self.log.info(f"{'='*60}\n")
                return False

        # Finalizar season anterior fuera del bloque anterior (abre su propia conexión)
        if active_season:
            self.log.info(f"\n📊 PASO 1: Finalizando temporada {active_season}...")
            start_time = datetime.now(tz=LOCAL_TZ)
            await self.finalize_season(active_season)
            elapsed = (datetime.now(tz=LOCAL_TZ) - start_time).total_seconds()
            self.log.info(f"   └─ ✅ Temporada finalizada en {elapsed:.2f}s")
        else:
            self.log.info(f"\n⏭️  PASO 1: Omitido (no hay temporada previa)")

        async with self.get_connection() as conn:
            # PASO 2: Crear nueva season si no existe
            self.log.debug(f"\n🆕 PASO 2: Creando/verificando temporada {target_season_id}...")
            season_info = get_season_info(target_season_id)
            season_cursor = await conn.execute('''
                INSERT OR IGNORE INTO seasons
                (season_id, season_name, start_date, end_date, is_ranked, is_active)
                VALUES (?, ?, ?, ?, ?, 0)
            ''', (
                season_info['id'],
                season_info['name'],
                season_info['start_date'],
                season_info['end_date'],
                season_info['is_ranked']
            ))
            if season_cursor.rowcount > 0:
                self.log.info(f"   └─ ✅ Nueva temporada creada")
            else:
                self.log.info(f"   └─ ℹ️  Temporada ya existía")

            # PASO 3: Activar nueva season
            self.log.info(f"\n🎯 PASO 3: Activando temporada {target_season_id}...")
            deact_cursor = await conn.execute('UPDATE seasons SET is_active = 0')
            deactivated = deact_cursor.rowcount
            await conn.execute('''
                UPDATE seasons SET is_active = 1
                WHERE season_id = ?
            ''', (target_season_id,))
            self.log.info(f"   └─ ✅ {deactivated} temporada(s) desactivada(s)")
            self.log.info(f"   └─ ✅ Temporada {target_season_id} activada")

            # PASO 4: Reset de rachas actuales (GLOBALES)
            self.log.info(f"\n♻️  PASO 4: Reseteando rachas actuales...")
            reset_cursor = await conn.execute('''
                UPDATE global_users SET
                    current_streak = 0,
                    last_pole_date = NULL
            ''')
            affected = reset_cursor.rowcount
            self.log.info(f"   └─ ✅ {affected} usuario(s) reseteados (current_streak → 0)")

            # PASO 5: Limpieza opcional de season_stats antiguas
            self.log.info(f"\n🗑️  PASO 5: Limpiando season_stats antiguas (mantener últimas 3)...")
            try:
                del_cursor = await conn.execute('''
                    DELETE FROM season_stats
                    WHERE season_id NOT IN (
                        SELECT DISTINCT season_id FROM seasons
                        ORDER BY start_date DESC
                        LIMIT 3
                    )
                ''')
                deleted = del_cursor.rowcount
                if deleted > 0:
                    self.log.info(f"   └─ ✅ {deleted} registro(s) antiguos eliminados")
                else:
                    self.log.info(f"   └─ ℹ️  No hay registros antiguos para eliminar")
            except Exception as e:
                self.log.error(f"   └─ ⚠️  Error en limpieza: {e}")

            self.log.info(f"\n{'='*60}")
            self.log.info(f"✅ MIGRACIÓN COMPLETADA CON ÉXITO")
            self.log.info(f"{'='*60}")
            self.log.info(f"📌 Temporada activa: {target_season_id}")
            self.log.info(f"📊 Cambio: {active_season or 'inicial'} → {target_season_id}")
            self.log.info(f"⏰ Finalizado: {datetime.now(tz=LOCAL_TZ).strftime('%Y-%m-%d %H:%M:%S')}")
            self.log.info(f"{'='*60}\n")
            return True

    async def verify_migration_integrity(self, season_id: str) -> Dict[str, Any]:
        """Verificar la integridad de datos tras una migración de temporada."""
        issues = []
        stats = {}

        async with self.get_connection() as conn:
            cursor = await conn.execute('SELECT is_active FROM seasons WHERE season_id = ?', (season_id,))
            row = await cursor.fetchone()
            if not row or row[0] != 1:
                issues.append(f"Season {season_id} no está marcada como activa")

            cursor = await conn.execute('SELECT COUNT(*) FROM users WHERE current_streak > 0')
            row = await cursor.fetchone()
            streaks_not_reset = int(row[0]) if row else 0
            if streaks_not_reset > 0:
                issues.append(f"{streaks_not_reset} usuarios tienen current_streak > 0 (deberían estar en 0)")

            cursor = await conn.execute('SELECT COUNT(*) FROM seasons WHERE is_active = 1')
            row = await cursor.fetchone()
            active_count = int(row[0]) if row else 0
            if active_count != 1:
                issues.append(f"Hay {active_count} temporadas activas (debería ser 1)")

            cursor = await conn.execute('SELECT COUNT(*) FROM season_history WHERE season_id != ?', (season_id,))
            row = await cursor.fetchone()
            stats['history_records'] = int(row[0]) if row else 0

            cursor = await conn.execute('SELECT COUNT(*) FROM user_badges')
            row = await cursor.fetchone()
            stats['total_badges'] = int(row[0]) if row else 0

            cursor = await conn.execute('''
                SELECT COUNT(*) FROM season_stats
                WHERE season_id = ? AND (season_points < 0 OR season_poles < 0)
            ''', (season_id,))
            row = await cursor.fetchone()
            invalid_stats = int(row[0]) if row else 0
            if invalid_stats > 0:
                issues.append(f"{invalid_stats} registros con valores negativos en season_stats")

        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'stats': stats
        }

    async def check_and_update_season(self):
        """
        Verificar si cambió la season y hacer reset automático si es necesario.
        ⚠️ DEPRECADO: Usar migrate_season() directamente.
        """
        migrated = await self.migrate_season()
        if not migrated:
            self.log.info("ℹ️  Season actual ya está activa, no se requiere acción")

    # ==================== MÉTODOS DE REPRESENTACIÓN DE SERVIDOR ====================
