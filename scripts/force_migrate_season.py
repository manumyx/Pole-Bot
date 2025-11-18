"""
Script de Migración FORZADA de Temporadas - TESTING ONLY
Permite forzar el cambio de temporada manualmente para testing

⚠️ IMPORTANTE:
- Este script es SOLO para testing/desarrollo
- En producción, las migraciones ocurren automáticamente al cambio de año
- Usa la misma lógica que el sistema automático (DRY principle)

EFECTOS:
- Finaliza la temporada actual (guarda historial y otorga badges)
- Crea la siguiente temporada
- Resetea puntos de temporada y rachas

USOS:
python scripts/force_migrate_season.py           # Detecta automáticamente siguiente season
python scripts/force_migrate_season.py season_2  # Fuerza migración a season_2 específica
"""
import sys
import os

# Añadir directorio padre al path para importar módulos
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.database import Database
from typing import Optional

def force_migrate_season(target_season_id: Optional[str] = None, db_path: Optional[str] = None):
    """
    Forzar migración de temporada usando el sistema unificado.
    
    Args:
        target_season_id: ID de la temporada destino (ej: 'season_1', 'season_2')
                         Si es None, se auto-detecta por año actual
        db_path: Ruta a la base de datos (None = usa ruta por defecto)
    """
    
    # Construir ruta absoluta a la base de datos
    if db_path is None:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        db_path = os.path.join(project_root, "data", "pole_bot.db")
    
    print("=" * 60)
    print("🔄 MIGRACIÓN FORZADA DE TEMPORADA (TESTING)")
    print("=" * 60)
    print(f"📂 Base de datos: {db_path}")
    print("")
    
    # Crear instancia de Database
    db = Database(db_path)
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Obtener temporada actual activa
        cursor.execute('SELECT season_id, season_name FROM seasons WHERE is_active = 1')
        row = cursor.fetchone()
        
        if row:
            current_season_id = row[0]
            current_season_name = row[1]
            print(f"📊 Temporada actual: {current_season_name} ({current_season_id})")
        else:
            print("ℹ️  No hay temporada activa (primera inicialización)")
            current_season_id = None
            current_season_name = None
        
        print("")
        
        # Si no se especifica target, auto-calcular
        if target_season_id is None:
            if current_season_id is None:
                # Primera inicialización - usar auto-detección del sistema
                from utils.scoring import get_current_season
                target_season_id = get_current_season()
                print(f"🎯 Target auto-detectado (primera inicialización): {target_season_id}")
            elif current_season_id == 'preseason':
                target_season_id = 'season_1'
                print(f"🎯 Target auto-detectado: {target_season_id}")
            elif current_season_id.startswith('season_'):
                current_num = int(current_season_id.split('_')[1])
                target_season_id = f'season_{current_num + 1}'
                print(f"🎯 Target auto-detectado: {target_season_id}")
            else:
                print("❌ No se pudo determinar temporada destino")
                return
        else:
            print(f"🎯 Target especificado: {target_season_id}")
        
        print("")
        
        # Confirmación
        print("⚠️  ATENCIÓN: Esta operación realizará los siguientes cambios:")
        if current_season_name:
            print(f"   1. Finalizará {current_season_name} (guardará historial y otorgará badges)")
        print(f"   2. Activará {target_season_id}")
        print("   3. Reseteará rachas actuales de todos los usuarios")
        print("   4. Mantendrá puntos all-time intactos")
        print("")
        
        response = input("¿Continuar con la migración? (escribe 'SI' para confirmar): ")
        
        if response.strip().upper() != 'SI':
            print("❌ Migración cancelada")
            return
        
        print("")
        print("🚀 Iniciando migración...")
        print("")
    
    # Ejecutar migración usando sistema unificado
    success = db.migrate_season(target_season_id=target_season_id, force=True)
    
    if success:
        print("")
        print("=" * 60)
        print("✅ MIGRACIÓN COMPLETADA EXITOSAMENTE")
        print("=" * 60)
        print("")
        print("📝 Próximos pasos:")
        print("   1. Reinicia el bot para que cargue la nueva temporada")
        print("   2. Verifica con /season que muestra la temporada correcta")
        print("   3. Verifica con /leaderboard que los puntos están reseteados")
        print("   4. Los badges se pueden ver con /badges")
        print("")
    else:
        print("")
        print("⚠️  No se realizó migración (ya estaba en la temporada correcta)")
        print("")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else None
    force_migrate_season(target)
