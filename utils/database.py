"""
Sistema de Base de Datos v1.0 - Sistema de Hora Aleatoria + Seasons
Maneja toda la persistencia del Pole Bot
"""
import sqlite3
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple, Any
from contextlib import contextmanager

class Database:
    # Versión actual del schema - incrementar con cada migración
    SCHEMA_VERSION = 6  # v1: inicial, v2: pole_date, v3: last_daily_pole_time, v4: impatient_attempts, v5: global_users, v6: i18n (language)
    
    def __init__(self, db_path: str = "data/pole_bot.db"):
        self.db_path = db_path
        
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Inicializar base de datos
        self._init_database()
        
        # Ejecutar migraciones pendientes
        self._run_migrations()
        
        # Inicializar sistema de seasons (auto-setup en primer inicio)
        self._auto_initialize_seasons()
        
        print(f"✅ Base de datos inicializada: {db_path}")
    
    @contextmanager
    def get_connection(self):
        """Context manager para conexiones a la base de datos"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Para acceder por nombre de columna
        # Habilitar foreign keys (SQLite las tiene desactivadas por defecto)
        conn.execute('PRAGMA foreign_keys = ON')
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()
    
    def _init_database(self):
        """Crear todas las tablas necesarias para v1.0"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # ==================== TABLA SERVERS ====================
            # Configuración de cada servidor
            cursor.execute('''
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
            # Estadísticas de usuarios (PRODUCCIÓN)
            # NOTA: total_points y total_poles se calculan dinámicamente desde season_stats
            cursor.execute('''
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
            # Historial de poles (PRODUCCIÓN)
            cursor.execute('''
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
            
            # NOTA: Las migraciones de columnas ahora se manejan en _run_migrations()
            # para tener un sistema de versionado controlado
            
            # ==================== TABLA ACHIEVEMENTS ====================
            # Sistema de logros
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS achievements (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    guild_id INTEGER,
                    achievement_id TEXT,
                    unlocked_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    
                    FOREIGN KEY (user_id, guild_id) REFERENCES users(user_id, guild_id)
                )
            ''')
            
            # ==================== ÍNDICES ====================
            # Optimización de queries comunes
            
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_guild ON users(guild_id)')
            # NOTA: idx_users_points eliminado - total_points ya no existe en tabla users
            # NOTA: idx_users_streak eliminado - current_streak movido a global_users en v5
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_poles_user ON poles(user_id, guild_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_poles_date ON poles(created_at)')
    
    def _get_schema_version(self) -> int:
        """Obtener la versión actual del schema de la base de datos"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('SELECT version FROM schema_metadata ORDER BY version DESC LIMIT 1')
                row = cursor.fetchone()
                return row[0] if row else 0
            except sqlite3.OperationalError:
                # Tabla schema_metadata no existe, crear
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS schema_metadata (
                        version INTEGER PRIMARY KEY,
                        applied_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        description TEXT
                    )
                ''')
                return 0
    
    def _set_schema_version(self, cursor, version: int, description: str):
        """Registrar que una migración fue aplicada (usa cursor existente)"""
        cursor.execute('''
            INSERT OR REPLACE INTO schema_metadata (version, applied_at, description)
            VALUES (?, CURRENT_TIMESTAMP, ?)
        ''', (version, description))
    
    def _run_migrations(self):
        """Ejecutar migraciones pendientes de forma segura"""
        current_version = self._get_schema_version()
        
        print(f"🔍 Schema actual: v{current_version}, Target: v{self.SCHEMA_VERSION}")
        
        if current_version >= self.SCHEMA_VERSION:
            print(f"✅ Base de datos ya está en v{self.SCHEMA_VERSION}")
            return  # Ya está actualizado
        
        print(f"🔄 Ejecutando migraciones desde v{current_version} a v{self.SCHEMA_VERSION}...")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # MIGRACIÓN v1 → v2: Añadir pole_date
            if current_version < 2:
                try:
                    cursor.execute('ALTER TABLE poles ADD COLUMN pole_date TEXT')
                    cursor.execute('UPDATE poles SET pole_date = DATE(user_time) WHERE pole_date IS NULL')
                    self._set_schema_version(cursor, 2, "Añadida columna pole_date a poles")
                    print("✅ Migración v2: columna pole_date añadida")
                except sqlite3.OperationalError as e:
                    if "duplicate column" not in str(e).lower():
                        raise
                    print("ℹ️  Migración v2: columna pole_date ya existe")
                    self._set_schema_version(cursor, 2, "Columna pole_date ya existía")
            
            # MIGRACIÓN v2 → v3: Añadir last_daily_pole_time
            if current_version < 3:
                try:
                    cursor.execute('ALTER TABLE servers ADD COLUMN last_daily_pole_time TIME')
                    self._set_schema_version(cursor, 3, "Añadida columna last_daily_pole_time a servers")
                    print("✅ Migración v3: columna last_daily_pole_time añadida")
                except sqlite3.OperationalError as e:
                    if "duplicate column" not in str(e).lower():
                        raise
                    print("ℹ️  Migración v3: columna last_daily_pole_time ya existe")
                    self._set_schema_version(cursor, 3, "Columna last_daily_pole_time ya existía")
            
            # MIGRACIÓN v3 → v4: Añadir impatient_attempts (stat secreta)
            if current_version < 4:
                try:
                    cursor.execute('ALTER TABLE users ADD COLUMN impatient_attempts INTEGER DEFAULT 0')
                    self._set_schema_version(cursor, 4, "Añadida columna impatient_attempts a users")
                    print("✅ Migración v4: columna impatient_attempts añadida")
                except sqlite3.OperationalError as e:
                    if "duplicate column" not in str(e).lower():
                        raise
                    print("ℹ️  Migración v4: columna impatient_attempts ya existe")
                    self._set_schema_version(cursor, 4, "Columna impatient_attempts ya existía")
            
            # MIGRACIÓN v4 → v5: Crear tabla global_users y migrar rachas
            if current_version < 5:
                print("🔄 Migración v5: Creando sistema de rachas globales...")
                
                # COMMIT pendientes y cerrar transacción actual
                conn.commit()
                
                # DESACTIVAR foreign keys temporalmente para permitir DROP TABLE
                # CRÍTICO: Debe hacerse FUERA de transacción para que surta efecto
                conn.isolation_level = None  # Autocommit mode
                cursor.execute('PRAGMA foreign_keys = OFF')
                
                # Verificar que se desactivaron
                fk_status = cursor.execute('PRAGMA foreign_keys').fetchone()[0]
                print(f"   🔧 Foreign keys: {'OFF' if fk_status == 0 else 'ON (⚠️ ADVERTENCIA)'}")
                
                # LIMPIAR RESIDUOS de intentos fallidos previos
                # Esto es SEGURO porque estamos en autocommit
                cursor.execute('DROP TABLE IF EXISTS users_new')
                
                # Antes de eliminar global_users, crear un respaldo si existe
                cursor.execute("""
                    SELECT name FROM sqlite_master
                    WHERE type = 'table' AND name = 'global_users'
                """)
                if cursor.fetchone():
                    # Crear tabla de respaldo solo si aún no existe
                    cursor.execute('''
                        CREATE TABLE IF NOT EXISTS global_users_backup_v5 AS
                        SELECT * FROM global_users
                    ''')
                    cursor.execute('DROP TABLE global_users')
                
                print("   🧹 Limpieza de tablas temporales completada (respaldo de global_users si existía)")
                
                # Crear tabla global_users
                cursor.execute('''
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
                print("   📊 Consolidando rachas de usuarios...")
                
                # Estrategia: Para cada usuario, tomar el MAX de rachas y el guild donde tiene mejor desempeño
                cursor.execute('''
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
                
                users_to_migrate = cursor.fetchall()
                migrated_count = 0
                
                for user in users_to_migrate:
                    cursor.execute('''
                        INSERT OR REPLACE INTO global_users 
                        (user_id, username, current_streak, best_streak, last_pole_date, represented_guild_id)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (
                        user[0],  # user_id
                        user[1],  # username
                        user[2],  # best_current_streak de todos los servidores
                        user[3],  # best_overall_streak de todos los servidores
                        user[4],  # most_recent_pole
                        user[5]   # primary_guild_id (servidor donde tiene mejor desempeño)
                    ))
                    migrated_count += 1
                
                # Eliminar columnas de racha de la tabla users (ya no se usan)
                # SQLite no permite DROP COLUMN, así que creamos tabla nueva
                cursor.execute('''
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
                cursor.execute('''
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
                cursor.execute('DROP TABLE users')
                cursor.execute('ALTER TABLE users_new RENAME TO users')
                
                # Crear índices para tabla global_users
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_global_users_streak ON global_users(current_streak DESC)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_global_users_best ON global_users(best_streak DESC)')
                
                # REACTIVAR foreign keys y modo transaccional
                cursor.execute('PRAGMA foreign_keys = ON')
                conn.isolation_level = ''  # Volver a modo transaccional (default)
                
                # Verificar integridad
                integrity = cursor.execute('PRAGMA foreign_key_check').fetchall()
                if integrity:
                    print(f"   ⚠️ Advertencia: {len(integrity)} violaciones de foreign key detectadas")
                    for violation in integrity[:5]:  # Mostrar primeras 5
                        print(f"      {violation}")
                else:
                    print("   ✅ Verificación de integridad: OK")
                
                self._set_schema_version(cursor, 5, f"Sistema de rachas globales creado. {migrated_count} usuarios migrados")
                print(f"✅ Migración v5: {migrated_count} usuarios migrados a rachas globales")
            
            # ==================== MIGRACIÓN v6: Sistema i18n (idioma por servidor) ====================
            if current_version < 6:
                print("🔄 Ejecutando migración v6: Sistema de internacionalización (i18n)...")
                
                # Añadir columna language a servers
                try:
                    cursor.execute("ALTER TABLE servers ADD COLUMN language TEXT DEFAULT 'es'")
                    print("   ✅ Columna 'language' añadida a tabla servers")
                except sqlite3.OperationalError:
                    print("   ⚠️ Columna 'language' ya existe, saltando...")
                
                self._set_schema_version(cursor, 6, "Sistema de internacionalización (i18n) implementado")
                print("✅ Migración v6: Sistema i18n listo. Idiomas disponibles: es, en")
    
    def _auto_initialize_seasons(self):
        """
        Auto-inicialización del sistema de seasons (transparente en primer inicio)
        
        Crea las tablas de seasons si no existen y configura la pre-temporada activa.
        Sistema diseñado para 2025 = preseason, 2026+ = season_N (infinito).
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar si ya existe la tabla seasons
            cursor.execute('''
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='seasons'
            ''')
            table_exists = cursor.fetchone() is not None
            
            if not table_exists:
                print("🔄 Primera inicialización: Creando tablas de seasons...")
            
            # ==================== TABLA SEASONS ====================
            cursor.execute('''
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
            cursor.execute('''
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
            cursor.execute('''
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
            cursor.execute('''
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
            
            # ==================== INICIALIZAR TEMPORADAS ====================
            from utils.scoring import get_current_season, get_season_info
            
            # Verificar si ya existe alguna season activa
            cursor.execute('SELECT season_id FROM seasons WHERE is_active = 1')
            active_season = cursor.fetchone()
            
            if not active_season:
                # Primera inicialización: crear solo la temporada actual
                print("🔄 Inicializando sistema de temporadas...")
                
                # Crear y activar temporada actual según el año
                # 2025 → preseason, 2026 → season_1, etc.
                current_season_id = get_current_season()
                season_info = get_season_info(current_season_id)
                
                cursor.execute('''
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
                
                conn.commit()
                
                if not table_exists:
                    print(f"✅ Sistema de seasons inicializado:")
                    print(f"   • {season_info['name']} ({season_info['id']}) activa")
            elif not table_exists:
                print(f"ℹ️  Sistema de seasons inicializado: {active_season[0]} activa")
    
    # ==================== MÉTODOS DE SERVIDORES ====================
    
    def init_server(self, guild_id: int, channel_id: int):
        """Inicializar configuración de servidor"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO servers (guild_id, pole_channel_id)
                VALUES (?, ?)
            ''', (guild_id, channel_id))
    
    def get_server_config(self, guild_id: int) -> Optional[Dict]:
        """Obtener configuración de servidor"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM servers WHERE guild_id = ?', (guild_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def update_server_config(self, guild_id: int, **kwargs):
        """Actualizar configuración de servidor"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Construir query dinámicamente
            fields = ', '.join([f"{key} = ?" for key in kwargs.keys()])
            values = list(kwargs.values()) + [guild_id]
            
            cursor.execute(f'''
                UPDATE servers SET {fields}
                WHERE guild_id = ?
            ''', values)
    
    def get_server_language(self, guild_id: int) -> str:
        """Obtener idioma configurado del servidor (default: 'es')"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT language FROM servers WHERE guild_id = ?', (guild_id,))
            row = cursor.fetchone()
            return row['language'] if row and row['language'] else 'es'
    
    def set_server_language(self, guild_id: int, language: str):
        """Configurar idioma del servidor"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE servers SET language = ?
                WHERE guild_id = ?
            ''', (language, guild_id))
    
    def set_daily_pole_time(self, guild_id: int, time_str: str):
        """Establecer hora de pole del día (formato HH:MM:SS)
        Guarda la hora actual como last_daily_pole_time antes de actualizar.
        """
        # Verificar que el servidor existe, si no, inicializarlo
        config = self.get_server_config(guild_id)
        if not config:
            self.init_server(guild_id, 0)  # Inicializar con canal placeholder
            config = self.get_server_config(guild_id)
        
        # Obtener hora actual antes de actualizar
        current_time = config.get('daily_pole_time') if config else None
        
        # Actualizar guardando la hora anterior
        if current_time:
            self.update_server_config(guild_id, 
                                    daily_pole_time=time_str,
                                    last_daily_pole_time=current_time)
        else:
            self.update_server_config(guild_id, daily_pole_time=time_str)
    
    def get_daily_pole_time(self, guild_id: int) -> Optional[str]:
        """Obtener hora de pole del día"""
        config = self.get_server_config(guild_id)
        return config.get('daily_pole_time') if config else None
    
    def get_last_daily_pole_time(self, guild_id: int) -> Optional[str]:
        """Obtener la hora de apertura generada AYER (para cálculo de margen)"""
        config = self.get_server_config(guild_id)
        return config.get('last_daily_pole_time') if config else None
    
    # ==================== MÉTODOS DE USUARIOS ====================
    
    def get_user(self, user_id: int, guild_id: int) -> Optional[Dict]:
        """Obtener datos de usuario con totales calculados dinámicamente desde seasons"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM users 
                WHERE user_id = ? AND guild_id = ?
            ''', (user_id, guild_id))
            row = cursor.fetchone()
            
            if not row:
                return None
            
            user_data = dict(row)
            
            # Calcular total_points y total_poles desde todas las temporadas
            cursor.execute('''
                SELECT 
                    COALESCE(SUM(season_points), 0) as total_points,
                    COALESCE(SUM(season_poles), 0) as total_poles
                FROM season_stats
                WHERE user_id = ? AND guild_id = ?
            ''', (user_id, guild_id))
            totals = cursor.fetchone()
            
            user_data['total_points'] = float(totals['total_points']) if totals else 0.0
            user_data['total_poles'] = int(totals['total_poles']) if totals else 0
            
            return user_data
    
    def create_user(self, user_id: int, guild_id: int, username: str):
        """Crear nuevo usuario"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO users (user_id, guild_id, username)
                VALUES (?, ?, ?)
            ''', (user_id, guild_id, username))
    
    def update_user(self, user_id: int, guild_id: int, **kwargs):
        """Actualizar datos de usuario"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Añadir updated_at automáticamente
            kwargs['updated_at'] = datetime.now().isoformat()
            
            fields = ', '.join([f"{key} = ?" for key in kwargs.keys()])
            values = list(kwargs.values()) + [user_id, guild_id]
            
            cursor.execute(f'''
                UPDATE users SET {fields}
                WHERE user_id = ? AND guild_id = ?
            ''', values)
    
    def increment_impatient_attempts(self, user_id: int, guild_id: int):
        """Incrementar contador de intentos impacientes (stat secreta para POLE REWIND)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users 
                SET impatient_attempts = impatient_attempts + 1,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND guild_id = ?
            ''', (user_id, guild_id))
    
    # ==================== MÉTODOS DE GLOBAL_USERS (RACHAS GLOBALES) ====================
    
    def get_global_user(self, user_id: int) -> Optional[Dict]:
        """Obtener datos globales de un usuario (rachas compartidas entre servidores)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM global_users WHERE user_id = ?', (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def create_global_user(self, user_id: int, username: str):
        """Crear usuario global si no existe"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO global_users (user_id, username)
                VALUES (?, ?)
            ''', (user_id, username))
    
    def update_global_user(self, user_id: int, **kwargs):
        """Actualizar datos globales de usuario (rachas, representación, etc.)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Añadir updated_at automáticamente
            kwargs['updated_at'] = datetime.now().isoformat()
            
            fields = ', '.join([f"{key} = ?" for key in kwargs.keys()])
            values = list(kwargs.values()) + [user_id]
            
            cursor.execute(f'''
                UPDATE global_users SET {fields}
                WHERE user_id = ?
            ''', values)
    
    def get_or_create_global_user(self, user_id: int, username: str) -> Optional[Dict]:
        """Obtener o crear usuario global"""
        user = self.get_global_user(user_id)
        if not user:
            self.create_global_user(user_id, username)
            user = self.get_global_user(user_id)
        return user
    
    def get_user_global_stats(self, user_id: int) -> Optional[Dict]:
        """Obtener estadísticas globales del usuario (sumando TODOS los servidores)"""
        with self.get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Sumar todos los poles de todos los servidores
            cursor.execute('''
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
            
            stats = cursor.fetchone()
            
            if not stats or stats['critical_poles'] is None:
                return None
            
            # Calcular puntos totales desde season_stats
            cursor.execute('''
                SELECT 
                    SUM(season_points) as total_points,
                    SUM(season_poles) as total_poles
                FROM season_stats
                WHERE user_id = ?
            ''', (user_id,))
            
            points_data = cursor.fetchone()
            
            return {
                'user_id': user_id,
                'critical_poles': stats['critical_poles'] or 0,
                'fast_poles': stats['fast_poles'] or 0,
                'normal_poles': stats['normal_poles'] or 0,
                'late_poles': stats['late_poles'] or 0,
                'marranero_poles': stats['marranero_poles'] or 0,
                'average_delay_minutes': stats['average_delay_minutes'] or 0.0,
                'best_time_minutes': stats['best_time_minutes'] or 0,
                'total_points': points_data['total_points'] or 0.0,
                'total_poles': points_data['total_poles'] or 0
            }

    # ==================== MÉTODOS DE POLES ====================
    
    def save_pole(self, user_id: int, guild_id: int, opening_time: datetime, 
                  user_time: datetime, delay_minutes: int, pole_type: str, 
                  points_earned: float, streak: int, pole_date: Optional[str] = None):
        """Guardar pole en historial
        
        Args:
            pole_date: Fecha efectiva del pole (YYYY-MM-DD). Para marranero es el día anterior.
                       Si no se proporciona, usa DATE(user_time).
        """
        if pole_date is None:
            pole_date = user_time.strftime('%Y-%m-%d')
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO poles (
                    user_id, guild_id, opening_time, user_time, 
                    delay_minutes, pole_date, pole_type, points_earned, streak_at_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, guild_id, opening_time, user_time, 
                  delay_minutes, pole_date, pole_type, points_earned, streak))
    
    def get_user_poles(self, user_id: int, guild_id: int, limit: int = 50) -> List[Dict]:
        """Obtener historial de poles de un usuario"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM poles 
                WHERE user_id = ? AND guild_id = ?
                ORDER BY created_at DESC
                LIMIT ?
            ''', (user_id, guild_id, limit))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_poles_today(self, guild_id: int) -> List[Dict]:
        """Obtener todos los poles del día actual"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            today = datetime.now().date().isoformat()
            cursor.execute('''
                SELECT * FROM poles 
                WHERE guild_id = ? AND DATE(user_time) = ?
                ORDER BY user_time ASC
            ''', (guild_id, today))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_last_pole_opening_time(self, guild_id: int) -> Optional[str]:
        """Obtener la hora de apertura (HH:MM:SS) del último pole registrado (normalmente ayer)
        
        DEPRECATED: Usar get_last_daily_pole_time() para cálculo de margen.
        Este método queda solo para compatibilidad con lógica de marranero.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT opening_time FROM poles
                WHERE guild_id = ?
                ORDER BY created_at DESC
                LIMIT 1
            ''', (guild_id,))
            row = cursor.fetchone()
            if row and row['opening_time']:
                # opening_time es datetime, extraer solo hora
                dt = datetime.fromisoformat(str(row['opening_time']))
                return dt.strftime('%H:%M:%S')
            return None

    def get_user_pole_today_global(self, user_id: int) -> Optional[Dict]:
        """Obtener el pole de hoy de un usuario en cualquier servidor (si existe)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            today = datetime.now().date().isoformat()
            cursor.execute('''
                SELECT * FROM poles 
                WHERE user_id = ? AND DATE(user_time) = ?
                ORDER BY user_time ASC
                LIMIT 1
            ''', (user_id, today))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_user_pole_on_date_global(self, user_id: int, date_str: str) -> Optional[Dict]:
        """
        Verificar si un usuario hizo pole en CUALQUIER servidor en una fecha específica.
        Retorna el primer pole encontrado o None.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Usar pole_date (fecha efectiva) si existe, sino fallback a DATE(user_time)
            cursor.execute('''
                SELECT * FROM poles 
                WHERE user_id = ? AND (pole_date = ? OR (pole_date IS NULL AND DATE(user_time) = ?))
                ORDER BY user_time ASC
                LIMIT 1
            ''', (user_id, date_str, date_str))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def user_has_pole_on_date(self, user_id: int, guild_id: int, date_str: str) -> bool:
        """Verificar si un usuario hizo pole en una fecha específica (YYYY-MM-DD)
        
        Usa pole_date (fecha efectiva) para verificar. Para marranero, pole_date
        es el día anterior aunque user_time sea del día actual.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Usar pole_date (fecha efectiva) si existe, sino fallback a DATE(user_time)
            cursor.execute('''
                SELECT COUNT(*) FROM poles 
                WHERE user_id = ? AND guild_id = ? 
                  AND (pole_date = ? OR (pole_date IS NULL AND DATE(user_time) = ?))
            ''', (user_id, guild_id, date_str, date_str))
            count = cursor.fetchone()[0]
            return count > 0
    
    # ==================== MÉTODOS DE LEADERBOARD ====================
    
    def get_leaderboard(self, guild_id: int, limit: int = 10, order_by: str = 'points') -> List[Dict]:
        """
        Obtener ranking del servidor con totales calculados desde seasons
        order_by: 'points' (total_points), 'streak' (current_streak), 'speed' (average_delay_minutes)
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if order_by == 'points':
                order_clause = 'total_points DESC'
            elif order_by == 'streak':
                order_clause = 'u.current_streak DESC, total_points DESC'
            elif order_by == 'speed':
                order_clause = 'u.average_delay_minutes ASC'
            else:
                order_clause = 'total_points DESC'
            
            cursor.execute(f'''
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
            return [dict(row) for row in cursor.fetchall()]

    def get_global_leaderboard(self, limit: int = 10, order_by: str = 'points') -> List[Dict]:
        """Ranking global por usuario (agregado en todos los servidores) con totales desde seasons"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if order_by == 'points':
                order_clause = 'total_points DESC'
            elif order_by == 'streak':
                # Ordenar por rachas GLOBALES (de global_users)
                order_clause = 'COALESCE(gu.current_streak, 0) DESC, total_points DESC'
            elif order_by == 'speed':
                # Promedio ponderado simplificado por conteo (aprox)
                order_clause = 'AVG(u.average_delay_minutes) ASC'
            else:
                order_clause = 'total_points DESC'

            cursor.execute(f'''
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
            return [dict(row) for row in cursor.fetchall()]
    
    # ==================== MÉTODOS DEBUG ====================
    
    # ==================== MÉTODOS DE LOGROS ====================
    
    def unlock_achievement(self, user_id: int, guild_id: int, achievement_id: str):
        """Desbloquear logro para usuario"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO achievements (user_id, guild_id, achievement_id)
                VALUES (?, ?, ?)
            ''', (user_id, guild_id, achievement_id))
    
    def get_user_achievements(self, user_id: int, guild_id: int) -> List[str]:
        """Obtener logros desbloqueados de usuario"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT achievement_id FROM achievements 
                WHERE user_id = ? AND guild_id = ?
            ''', (user_id, guild_id))
            return [row['achievement_id'] for row in cursor.fetchall()]
    
    def has_achievement(self, user_id: int, guild_id: int, achievement_id: str) -> bool:
        """Verificar si usuario tiene un logro"""
        achievements = self.get_user_achievements(user_id, guild_id)
        return achievement_id in achievements
    
    # ==================== MÉTODOS DE REPRESENTACIÓN ====================
    
    def get_represented_guild(self, user_id: int) -> Optional[int]:
        """Obtener el guild_id que representa un usuario globalmente"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT represented_guild_id FROM global_users
                WHERE user_id = ?
            ''', (user_id,))
            row = cursor.fetchone()
            return int(row['represented_guild_id']) if row and row['represented_guild_id'] else None
    
    def set_represented_guild(self, user_id: int, guild_id: int):
        """Establecer el servidor que representa un usuario"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Actualizar en global_users
            cursor.execute('''
                UPDATE global_users
                SET represented_guild_id = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ?
            ''', (guild_id, user_id))
    
    def get_global_server_leaderboard(self, limit: int = 10) -> List[Dict]:
        """Ranking global de servidores por suma de puntos de usuarios que los representan"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
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
            return [dict(row) for row in cursor.fetchall()]
    
    def get_local_server_leaderboard(self, guild_id: int, limit: int = 10) -> List[Dict]:
        """Ranking local de servidores representados por miembros de este servidor"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
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
            return [dict(row) for row in cursor.fetchall()]
    
    # ==================== MÉTODOS DE SEASONS ====================
    
    def get_season_stats(self, user_id: int, guild_id: int, season_id: str) -> Optional[Dict]:
        """Obtener estadísticas de un usuario en una season específica"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM season_stats
                WHERE user_id = ? AND guild_id = ? AND season_id = ?
            ''', (user_id, guild_id, season_id))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_user_best_season_points(self, user_id: int, guild_id: int) -> float:
        """
        Obtener el máximo de puntos alcanzados por un usuario en cualquier temporada.
        Usado para calcular el "Rango Histórico" basado en el mejor desempeño en seasons.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT MAX(season_points) as max_points
                FROM season_stats
                WHERE user_id = ? AND guild_id = ?
            ''', (user_id, guild_id))
            row = cursor.fetchone()
            return float(row['max_points']) if row and row['max_points'] is not None else 0.0
    
    def get_user_total_points(self, user_id: int, guild_id: int) -> float:
        """
        Obtener puntos totales de un usuario (suma de todas las temporadas).
        v5: Los puntos totales NO se guardan en users, se calculan desde season_stats.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COALESCE(SUM(season_points), 0) as total_points
                FROM season_stats
                WHERE user_id = ? AND guild_id = ?
            ''', (user_id, guild_id))
            row = cursor.fetchone()
            return float(row['total_points']) if row else 0.0
    
    def get_user_total_poles(self, user_id: int, guild_id: int) -> int:
        """
        Obtener poles totales de un usuario en un servidor (todas las temporadas).
        v5: Los totales NO se guardan en users, se calculan desde season_stats.
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COALESCE(SUM(season_poles), 0) as total_poles
                FROM season_stats
                WHERE user_id = ? AND guild_id = ?
            ''', (user_id, guild_id))
            row = cursor.fetchone()
            return int(row['total_poles']) if row else 0
    
    def update_season_stats(self, user_id: int, guild_id: int, season_id: str, **kwargs):
        """Actualizar estadísticas de season de un usuario"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Verificar si existe el registro
            cursor.execute('''
                SELECT 1 FROM season_stats
                WHERE user_id = ? AND guild_id = ? AND season_id = ?
            ''', (user_id, guild_id, season_id))
            
            if cursor.fetchone():
                # Actualizar registro existente
                set_clause = ', '.join([f"{k} = ?" for k in kwargs.keys()])
                values = list(kwargs.values())
                values.extend([user_id, guild_id, season_id])
                
                cursor.execute(f'''
                    UPDATE season_stats
                    SET {set_clause}, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND guild_id = ? AND season_id = ?
                ''', values)
            else:
                # Crear nuevo registro
                columns = ', '.join(kwargs.keys())
                placeholders = ', '.join(['?' for _ in kwargs])
                values = list(kwargs.values())
                
                cursor.execute(f'''
                    INSERT INTO season_stats (user_id, guild_id, season_id, {columns})
                    VALUES (?, ?, ?, {placeholders})
                ''', [user_id, guild_id, season_id] + values)
    
    def get_season_leaderboard(self, guild_id: int, season_id: str, limit: int = 10) -> List[Dict]:
        """Obtener leaderboard de una season local"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT ss.*, u.username, u.represented_guild_id
                FROM season_stats ss
                JOIN users u ON ss.user_id = u.user_id AND ss.guild_id = u.guild_id
                WHERE ss.guild_id = ? AND ss.season_id = ?
                ORDER BY ss.season_points DESC
                LIMIT ?
            ''', (guild_id, season_id, limit))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_global_season_leaderboard(self, season_id: str, limit: int = 10) -> List[Dict]:
        """Obtener leaderboard global de una season (todos los servidores)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT 
                    ss.user_id,
                    MAX(u.username) as username,
                    MAX(u.represented_guild_id) as represented_guild_id,
                    SUM(ss.season_points) as total_season_points,
                    SUM(ss.season_poles) as total_season_poles,
                    MAX(ss.season_best_streak) as best_season_streak
                FROM season_stats ss
                JOIN users u ON ss.user_id = u.user_id AND ss.guild_id = u.guild_id
                WHERE ss.season_id = ?
                GROUP BY ss.user_id
                ORDER BY total_season_points DESC
                LIMIT ?
            ''', (season_id, limit))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_available_seasons(self) -> List[Dict]:
        """
        Obtener lista de todas las seasons disponibles (activas y finalizadas).
        Retorna ordenadas por fecha de inicio DESC (más reciente primero).
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT season_id, season_name, is_active, start_date, end_date, is_ranked
                FROM seasons
                ORDER BY start_date DESC
            ''')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_local_server_season_leaderboard(self, guild_id: int, season_id: str, limit: int = 10) -> List[Dict]:
        """Obtener leaderboard local de servidores representados en una season"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
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
            return [dict(row) for row in cursor.fetchall()]
    
    def get_total_active_users(self, guild_id: Optional[int] = None) -> int:
        """
        Obtener el número total de usuarios que han hecho al menos 1 pole.
        
        Args:
            guild_id: Si se especifica, cuenta solo usuarios activos de ese servidor.
                     Si es None, cuenta usuarios activos globalmente.
        
        Returns:
            Número de usuarios activos
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            if guild_id is not None:
                # Contar usuarios únicos que han hecho pole en este servidor específico
                cursor.execute('SELECT COUNT(DISTINCT user_id) FROM poles WHERE guild_id = ?', (guild_id,))
            else:
                # Contar usuarios únicos globalmente
                cursor.execute('SELECT COUNT(DISTINCT user_id) FROM poles')
            return cursor.fetchone()[0]
    
    def get_global_server_season_leaderboard(self, season_id: str, limit: int = 10) -> List[Dict]:
        """Obtener leaderboard global de servidores representados en una season"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
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
            return [dict(row) for row in cursor.fetchall()]
    
    def finalize_season(self, season_id: str):
        """
        Finalizar una season: copiar datos a historial y resetear stats
        Se ejecuta automáticamente al cambiar de año
        """
        from utils.scoring import get_rank_info
        
        print(f"   📊 Iniciando finalización de temporada {season_id}...")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Para cada servidor, obtener rankings finales
            cursor.execute('SELECT DISTINCT guild_id FROM season_stats WHERE season_id = ?', (season_id,))
            guilds = [row[0] for row in cursor.fetchall()]
            
            print(f"      └─ Servidores afectados: {len(guilds)}")
            
            total_saved = 0
            total_badges = 0
            
            for guild_id in guilds:
                # Obtener ranking ordenado
                cursor.execute('''
                    SELECT user_id, season_points, season_poles,
                           season_best_streak, season_critical, season_fast,
                           season_normal, season_marranero
                    FROM season_stats
                    WHERE guild_id = ? AND season_id = ?
                    ORDER BY season_points DESC
                ''', (guild_id, season_id))
                
                rankings = cursor.fetchall()
                total_players = len(rankings)
                
                # Guardar en historial con posiciones
                for position, row in enumerate(rankings, start=1):
                    user_id = row[0]
                    points = row[1]
                    
                    # Calcular rango final
                    badge, rank_name = get_rank_info(points)
                    
                    # Insertar en historial
                    cursor.execute('''
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
                    
                    # Otorgar badge permanente
                    cursor.execute('''
                        INSERT OR IGNORE INTO user_badges (
                            user_id, guild_id, season_id, badge_type, badge_emoji
                        ) VALUES (?, ?, ?, ?, ?)
                    ''', (user_id, guild_id, season_id, rank_name, badge))
                    if cursor.rowcount > 0:
                        total_badges += 1
            
            # Marcar season como inactiva
            cursor.execute('''
                UPDATE seasons SET is_active = 0 WHERE season_id = ?
            ''', (season_id,))
            
            print(f"      └─ ✅ {total_saved} registros guardados en historial")
            print(f"      └─ ✅ {total_badges} badges otorgados")
            print(f"      └─ ✅ Temporada marcada como inactiva")
    
    def get_user_badges(self, user_id: int, guild_id: int) -> List[Dict]:
        """Obtener todos los badges ganados por un usuario"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM user_badges
                WHERE user_id = ? AND guild_id = ?
                ORDER BY earned_at DESC
            ''', (user_id, guild_id))
            return [dict(row) for row in cursor.fetchall()]
    
    def migrate_season(self, target_season_id: Optional[str] = None, force: bool = False) -> bool:
        """
        Migración unificada de seasons (automática o manual).
        
        Esta función es la ÚNICA fuente de verdad para migrar seasons:
        - Automática: Llamada por task loop al detectar cambio de año
        - Manual: Llamada por scripts de testing con target_season_id
        
        Args:
            target_season_id: Season destino (None = auto-detectar por año)
            force: Si True, fuerza migración aunque ya esté activa
        
        Returns:
            bool: True si hubo migración, False si ya estaba actualizado
        """
        from utils.scoring import get_current_season, get_season_info
        
        # Banner de inicio
        print(f"\n{'='*60}")
        print(f"🔄 INICIO DE MIGRACIÓN DE TEMPORADA")
        print(f"{'='*60}")
        print(f"⏰ Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Determinar season objetivo
        if target_season_id is None:
            target_season_id = get_current_season()
        
        print(f"🎯 Temporada objetivo: {target_season_id}")
        print(f"🔧 Modo force: {force}")
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Obtener season activa actual
            print(f"\n📋 PASO 0: Verificando temporada activa actual...")
            cursor.execute('SELECT season_id FROM seasons WHERE is_active = 1')
            row = cursor.fetchone()
            active_season = row[0] if row else None
            print(f"   └─ Temporada activa: {active_season if active_season else 'Ninguna'}")
            
            # Si ya está en la season correcta y no es forzado
            if active_season == target_season_id and not force:
                print(f"   └─ ℹ️  Ya estamos en {target_season_id}, no se requiere migración")
                print(f"{'='*60}\n")
                return False
            
            # PASO 1: Finalizar season anterior (si existe)
            if active_season:
                print(f"\n📊 PASO 1: Finalizando temporada {active_season}...")
                start_time = datetime.now()
                self.finalize_season(active_season)
                elapsed = (datetime.now() - start_time).total_seconds()
                print(f"   └─ ✅ Temporada finalizada en {elapsed:.2f}s")
            else:
                print(f"\n⏭️  PASO 1: Omitido (no hay temporada previa)")
            
            # PASO 2: Crear nueva season si no existe
            print(f"\n🆕 PASO 2: Creando/verificando temporada {target_season_id}...")
            season_info = get_season_info(target_season_id)
            cursor.execute('''
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
            if cursor.rowcount > 0:
                print(f"   └─ ✅ Nueva temporada creada")
            else:
                print(f"   └─ ℹ️  Temporada ya existía")
            
            # PASO 3: Activar nueva season
            print(f"\n🎯 PASO 3: Activando temporada {target_season_id}...")
            cursor.execute('UPDATE seasons SET is_active = 0')  # Desactivar todas
            deactivated = cursor.rowcount
            cursor.execute('''
                UPDATE seasons SET is_active = 1 
                WHERE season_id = ?
            ''', (target_season_id,))
            print(f"   └─ ✅ {deactivated} temporada(s) desactivada(s)")
            print(f"   └─ ✅ Temporada {target_season_id} activada")
            
            # PASO 4: Reset de rachas actuales (GLOBALES)
            print(f"\n♻️  PASO 4: Reseteando rachas actuales...")
            cursor.execute('''
                UPDATE global_users SET 
                    current_streak = 0,
                    last_pole_date = NULL
            ''')
            affected = cursor.rowcount
            print(f"   └─ ✅ {affected} usuario(s) reseteados (current_streak → 0)")
            
            # PASO 5: Limpieza opcional de season_stats antiguas (reducir basura)
            print(f"\n🗑️  PASO 5: Limpiando season_stats antiguas (mantener últimas 3)...")
            try:
                cursor.execute('''
                    DELETE FROM season_stats
                    WHERE season_id NOT IN (
                        SELECT DISTINCT season_id FROM seasons
                        ORDER BY start_date DESC
                        LIMIT 3
                    )
                ''')
                deleted = cursor.rowcount
                if deleted > 0:
                    print(f"   └─ ✅ {deleted} registro(s) antiguos eliminados")
                else:
                    print(f"   └─ ℹ️  No hay registros antiguos para eliminar")
            except Exception as e:
                print(f"   └─ ⚠️  Error en limpieza: {e}")
            
            # Banner de finalización
            print(f"\n{'='*60}")
            print(f"✅ MIGRACIÓN COMPLETADA CON ÉXITO")
            print(f"{'='*60}")
            print(f"📌 Temporada activa: {target_season_id}")
            print(f"📊 Cambio: {active_season or 'inicial'} → {target_season_id}")
            print(f"⏰ Finalizado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*60}\n")
            return True
    
    def verify_migration_integrity(self, season_id: str) -> Dict[str, Any]:
        """
        Verificar la integridad de datos tras una migración de temporada.
        Retorna un diccionario con el estado de la verificación.
        """
        issues = []
        stats = {}
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # 1. Verificar que la season está activa
            cursor.execute('SELECT is_active FROM seasons WHERE season_id = ?', (season_id,))
            row = cursor.fetchone()
            if not row or row[0] != 1:
                issues.append(f"Season {season_id} no está marcada como activa")
            
            # 2. Verificar que todas las rachas se resetearon
            cursor.execute('SELECT COUNT(*) FROM users WHERE current_streak > 0')
            streaks_not_reset = cursor.fetchone()[0]
            if streaks_not_reset > 0:
                issues.append(f"{streaks_not_reset} usuarios tienen current_streak > 0 (deberían estar en 0)")
            
            # 3. Verificar que season anterior está inactiva
            cursor.execute('SELECT COUNT(*) FROM seasons WHERE is_active = 1')
            active_count = cursor.fetchone()[0]
            if active_count != 1:
                issues.append(f"Hay {active_count} temporadas activas (debería ser 1)")
            
            # 4. Contar stats guardadas en historial
            cursor.execute('SELECT COUNT(*) FROM season_history WHERE season_id != ?', (season_id,))
            history_count = cursor.fetchone()[0]
            stats['history_records'] = history_count
            
            # 5. Contar badges otorgados
            cursor.execute('SELECT COUNT(*) FROM user_badges')
            badges_count = cursor.fetchone()[0]
            stats['total_badges'] = badges_count
            
            # 6. Verificar integridad de season_stats para season actual
            cursor.execute('''
                SELECT COUNT(*) FROM season_stats 
                WHERE season_id = ? AND (season_points < 0 OR season_poles < 0)
            ''', (season_id,))
            invalid_stats = cursor.fetchone()[0]
            if invalid_stats > 0:
                issues.append(f"{invalid_stats} registros con valores negativos en season_stats")
        
        return {
            'is_valid': len(issues) == 0,
            'issues': issues,
            'stats': stats
        }
    
    def check_and_update_season(self):
        """
        Verificar si cambió la season y hacer reset automático si es necesario.
        Llamar en el scheduler diario.
        
        ⚠️ DEPRECADO: Usar migrate_season() directamente para lógica unificada.
        Esta función se mantiene por compatibilidad pero internamente usa migrate_season().
        """
        migrated = self.migrate_season()
        if not migrated:
            print("ℹ️  Season actual ya está activa, no se requiere acción")
    
    # ==================== MÉTODOS DE REPRESENTACIÓN DE SERVIDOR ====================