"""
Sistema de Base de Datos v1.0 - Sistema de Hora Aleatoria + Seasons
Maneja toda la persistencia del Pole Bot
"""
import sqlite3
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Tuple
from contextlib import contextmanager

class Database:
    def __init__(self, db_path: str = "data/pole_bot.db"):
        self.db_path = db_path
        
        # Crear directorio si no existe
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Inicializar base de datos
        self._init_database()
        
        # Inicializar sistema de seasons (auto-setup en primer inicio)
        self._auto_initialize_seasons()
        
        print(f"✅ Base de datos inicializada: {db_path}")
    
    @contextmanager
    def get_connection(self):
        """Context manager para conexiones a la base de datos"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Para acceder por nombre de columna
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
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_users_streak ON users(guild_id, current_streak DESC)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_poles_user ON poles(user_id, guild_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_poles_date ON poles(created_at)')
    
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
    
    def set_daily_pole_time(self, guild_id: int, time_str: str):
        """Establecer hora de pole del día (formato HH:MM:SS)"""
        self.update_server_config(guild_id, daily_pole_time=time_str)
    
    def get_daily_pole_time(self, guild_id: int) -> Optional[str]:
        """Obtener hora de pole del día"""
        config = self.get_server_config(guild_id)
        return config.get('daily_pole_time') if config else None
    
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
    
    # ==================== MÉTODOS DE POLES ====================
    
    def save_pole(self, user_id: int, guild_id: int, opening_time: datetime, 
                  user_time: datetime, delay_minutes: int, pole_type: str, 
                  points_earned: float, streak: int):
        """Guardar pole en historial"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO poles (
                    user_id, guild_id, opening_time, user_time, 
                    delay_minutes, pole_type, points_earned, streak_at_time
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, guild_id, opening_time, user_time, 
                  delay_minutes, pole_type, points_earned, streak))
    
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
        """Obtener la hora de apertura (HH:MM:SS) del último pole registrado (normalmente ayer)"""
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
                order_clause = 'MAX(u.current_streak) DESC, total_points DESC'
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
                    MAX(u.current_streak) AS current_streak,
                    MAX(u.best_streak) AS best_streak,
                    MAX(u.represented_guild_id) AS represented_guild_id
                FROM users u
                LEFT JOIN season_stats ss ON u.user_id = ss.user_id AND u.guild_id = ss.guild_id
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
                SELECT represented_guild_id FROM users
                WHERE user_id = ? AND represented_guild_id IS NOT NULL
                LIMIT 1
            ''', (user_id,))
            row = cursor.fetchone()
            return int(row['represented_guild_id']) if row and row['represented_guild_id'] else None
    
    def set_represented_guild(self, user_id: int, guild_id: int):
        """Establecer el servidor que representa un usuario (actualizar en todas sus entradas)"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE users
                SET represented_guild_id = ?
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
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Para cada servidor, obtener rankings finales
            cursor.execute('SELECT DISTINCT guild_id FROM season_stats WHERE season_id = ?', (season_id,))
            guilds = [row[0] for row in cursor.fetchall()]
            
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
                    
                    # Otorgar badge permanente
                    cursor.execute('''
                        INSERT OR IGNORE INTO user_badges (
                            user_id, guild_id, season_id, badge_type, badge_emoji
                        ) VALUES (?, ?, ?, ?, ?)
                    ''', (user_id, guild_id, season_id, rank_name, badge))
            
            # Marcar season como inactiva
            cursor.execute('''
                UPDATE seasons SET is_active = 0 WHERE season_id = ?
            ''', (season_id,))
            
            print(f"✅ Season {season_id} finalizada. Datos guardados en historial.")
    
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
        
        # Determinar season objetivo
        if target_season_id is None:
            target_season_id = get_current_season()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Obtener season activa actual
            cursor.execute('SELECT season_id FROM seasons WHERE is_active = 1')
            row = cursor.fetchone()
            active_season = row[0] if row else None
            
            # Si ya está en la season correcta y no es forzado
            if active_season == target_season_id and not force:
                print(f"ℹ️  Ya estamos en {target_season_id}, no se requiere migración")
                return False
            
            # PASO 1: Finalizar season anterior (si existe)
            if active_season:
                print(f"🔄 Finalizando {active_season}...")
                self.finalize_season(active_season)
            
            # PASO 2: Crear nueva season si no existe
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
            
            # PASO 3: Activar nueva season
            cursor.execute('UPDATE seasons SET is_active = 0')  # Desactivar todas
            cursor.execute('''
                UPDATE seasons SET is_active = 1 
                WHERE season_id = ?
            ''', (target_season_id,))
            
            # PASO 4: Reset de stats de producción (users table)
            # Las rachas actuales se resetean, pero best_streak permanece
            cursor.execute('''
                UPDATE users SET 
                    current_streak = 0,
                    last_pole_date = NULL
            ''')
            
            print(f"✅ Migración completada: {active_season or 'inicial'} → {target_season_id}")
            return True
    
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