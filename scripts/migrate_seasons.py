"""
⚠️⚠️⚠️ SCRIPT OBSOLETO - NO USAR ⚠️⚠️⚠️

Este script está DEPRECADO desde la implementación del sistema de auto-inicialización.

RAZÓN: El bot ahora crea automáticamente todas las tablas de seasons en el primer inicio.
Ya no es necesario ejecutar ningún script de migración inicial.

Si necesitas crear las tablas manualmente:
1. Simplemente inicia el bot (main.py)
2. Las tablas se crean automáticamente en Database.__init__()

Si necesitas forzar una migración para testing:
1. Usa: python scripts/force_migrate_season.py

SISTEMA ACTUAL (2025+):
- 2025 = preseason (auto-creada en primer inicio)
- 2026+ = season_N (creadas automáticamente al cambio de año)
- Migraciones automáticas cada 1 de enero
- Script de testing: force_migrate_season.py

Este archivo se mantiene solo para referencia histórica.
"""
import sqlite3
import sys
import os

# Añadir directorio padre al path para importar módulos
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.database import Database
from utils.scoring import get_current_season
from typing import Optional

def migrate_seasons(db_path: Optional[str] = None):
    """Crear tablas de seasons y migrar datos existentes"""
    
    # Construir ruta absoluta a la base de datos
    if db_path is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        db_path = os.path.join(project_root, "data", "pole_bot.db")
    
    print("🔄 Iniciando migración a sistema de seasons...")
    print(f"📂 Base de datos: {db_path}")
    print("")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # ==================== TABLA SEASONS ====================
        print("📋 Creando tabla seasons...")
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
        # Estadísticas por season (se resetea cada año)
        print("📋 Creando tabla season_stats...")
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
        # Historial permanente de seasons completadas
        print("📋 Creando tabla season_history...")
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
        # Colección de badges ganados (permanente)
        print("📋 Creando tabla user_badges...")
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
        
        # ==================== INICIALIZAR PRE-TEMPORADA ====================
        print("🎮 Inicializando pre-temporada...")
        current_season = get_current_season()
        
        # Insertar pre-temporada si no existe
        cursor.execute('''
            INSERT OR IGNORE INTO seasons (season_id, season_name, start_date, end_date, is_ranked, is_active)
            VALUES ('preseason', 'Pre-Temporada', '2025-11-17', '2025-12-31', 0, ?)
        ''', (1 if current_season == 'preseason' else 0,))
        
        # Insertar Season 1 si no existe
        cursor.execute('''
            INSERT OR IGNORE INTO seasons (season_id, season_name, start_date, end_date, is_ranked, is_active)
            VALUES ('season_1', 'Temporada 1', '2026-01-01', '2026-12-31', 1, ?)
        ''', (1 if current_season == 'season_1' else 0,))
        
        # ==================== MIGRAR DATOS EXISTENTES ====================
        print("📦 Migrando datos existentes a season_stats...")
        
        # Copiar stats de users a season_stats para la season actual
        # ADVERTENCIA: Este script es OBSOLETO desde la refactorización que eliminó
        # total_points y total_poles de la tabla users. Ahora se calculan dinámicamente
        # desde season_stats. No ejecutar este script en BDs modernas.
        cursor.execute(f'''
            INSERT OR IGNORE INTO season_stats (
                user_id, guild_id, season_id,
                season_points, season_poles,
                season_critical, season_fast, season_normal, season_marranero,
                season_best_streak
            )
            SELECT 
                user_id, guild_id, '{current_season}',
                total_points, total_poles,
                critical_poles, fast_poles, normal_poles, marranero_poles,
                best_streak
            FROM users
            WHERE total_poles > 0
        ''')
        
        rows_migrated = cursor.rowcount
        print(f"✅ {rows_migrated} registros migrados a season_stats")
        
        # ==================== AÑADIR COLUMNA CURRENT_SEASON A SERVERS ====================
        print("📋 Añadiendo tracking de season a servers...")
        try:
            cursor.execute('''
                ALTER TABLE servers ADD COLUMN current_season TEXT DEFAULT 'preseason'
            ''')
            print("✅ Columna current_season añadida")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print("⚠️  Columna current_season ya existe")
            else:
                raise
        
        conn.commit()
        print("\n✅ Migración completada exitosamente!")
        print(f"🎮 Season actual: {current_season}")
        print("\n📝 Sistema configurado:")
        print("  ✅ Badges custom de rangos ya configurados")
        print("  ✅ Migración automática configurada (se ejecuta cada 1 de enero)")
        print("  ✅ Mensaje de felicitación de año nuevo configurado")
        print("\n🎊 Las futuras migraciones de temporadas son AUTOMÁTICAS:")
        print("  • El bot detecta el cambio de año el 1 de enero a las 00:00")
        print("  • Finaliza la temporada anterior (guarda historial)")
        print("  • Crea automáticamente la nueva temporada (season_2, season_3, etc.)")
        print("  • Resetea puntos y rachas de todos los usuarios")
        print("  • Envía mensaje de felicitación a todos los servidores")
        print("\n⚠️  NO ejecutar este script de nuevo. Ya está todo listo.")
        
    except Exception as e:
        conn.rollback()
        print(f"\n❌ Error durante la migración: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate_seasons()
