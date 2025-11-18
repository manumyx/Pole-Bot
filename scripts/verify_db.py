"""
Script simple para verificar estructura de la base de datos
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.database import Database

def main():
    print("🔍 Verificando estructura de base de datos...")
    db = Database()
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Listar todas las tablas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [row[0] for row in cursor.fetchall()]
        
        print(f"\n✅ Tablas encontradas ({len(tables)}):")
        for table in tables:
            cursor.execute(f"SELECT COUNT(*) FROM {table}")
            count = cursor.fetchone()[0]
            print(f"   - {table}: {count} registros")
        
        # Verificar tablas críticas
        expected = ['servers', 'users', 'poles', 'seasons', 'season_stats', 'season_history', 'user_badges']
        missing = [t for t in expected if t not in tables]
        
        if missing:
            print(f"\n⚠️  Tablas faltantes: {', '.join(missing)}")
        else:
            print(f"\n✅ Todas las tablas esperadas están presentes")
        
        # Verificar tablas de temporadas
        season_tables = ['seasons', 'season_stats', 'season_history', 'user_badges']
        found_season_tables = [t for t in season_tables if t in tables]
        if len(found_season_tables) == 4:
            print("✅ Sistema de temporadas completo")
        else:
            print(f"⚠️  Sistema de temporadas incompleto: {len(found_season_tables)}/4 tablas")
        
        print("\n🎉 Verificación completada")

if __name__ == '__main__':
    main()
