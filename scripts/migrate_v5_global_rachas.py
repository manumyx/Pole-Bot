"""
Script de testing de migración v5
Ejecuta la migración en una COPIA de la BD de producción
"""
import sqlite3
import shutil

# Crear copia de seguridad
print("="*70)
print("TEST DE MIGRACIÓN v5 - RACHAS GLOBALES")
print("="*70)

print("\n📋 Copiando BD de producción...")
shutil.copy('data/pole_bot_prod29012026.db', 'data/pole_bot_test_migration.db')
print("✅ Copia creada: pole_bot_test_migration.db")

# Conectar a la copia
conn = sqlite3.connect('data/pole_bot_test_migration.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# Verificar schema version
cursor.execute("SELECT version FROM schema_metadata")
current_version = cursor.fetchone()['version']
print(f"\n📊 Schema version actual: {current_version}")

# Hacer un snapshot PRE-migración
print("\n📸 Snapshot PRE-migración:")
cursor.execute("SELECT COUNT(*) as count FROM users")
total_users = cursor.fetchone()['count']
print(f"   - Total registros en users: {total_users}")

cursor.execute("SELECT COUNT(DISTINCT user_id) as count FROM users")
unique_users = cursor.fetchone()['count']
print(f"   - Usuarios únicos: {unique_users}")

cursor.execute("""
    SELECT user_id, COUNT(*) as server_count 
    FROM users 
    GROUP BY user_id 
    HAVING server_count > 1
    ORDER BY server_count DESC
    LIMIT 5
""")
multi_server = cursor.fetchall()
print(f"   - Usuarios en múltiples servidores: {len(multi_server)}")
for u in multi_server[:3]:
    print(f"     └─ user_id={u['user_id']}: {u['server_count']} servidores")

# Verificar takusito específicamente
print(f"\n🔍 Estado de takusito (ID: 572416955961835520) ANTES:")
cursor.execute("""
    SELECT guild_id, current_streak, best_streak, last_pole_date
    FROM users
    WHERE user_id = 572416955961835520
""")
taku_before = cursor.fetchall()
for t in taku_before:
    print(f"   - Server {t['guild_id']}: racha={t['current_streak']}, mejor={t['best_streak']}, último={t['last_pole_date']}")

# EJECUTAR MIGRACIÓN v5
print("\n" + "="*70)
print("🔄 EJECUTANDO MIGRACIÓN v5...")
print("="*70)

try:
    # Crear tabla global_users
    print("\n1️⃣ Creando tabla global_users...")
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS global_users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            current_streak INTEGER DEFAULT 0,
            best_streak INTEGER DEFAULT 0,
            last_pole_date TEXT,
            represented_guild_id INTEGER,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    print("   ✅ Tabla creada")
    
    # Migrar datos
    print("\n2️⃣ Consolidando rachas...")
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
            user[2],  # best_current_streak
            user[3],  # best_overall_streak
            user[4],  # most_recent_pole
            user[5]   # primary_guild_id
        ))
        migrated_count += 1
    
    print(f"   ✅ {migrated_count} usuarios migrados")
    
    # Verificar takusito DESPUÉS
    print(f"\n🔍 Estado de takusito (ID: 572416955961835520) DESPUÉS:")
    cursor.execute("""
        SELECT user_id, username, current_streak, best_streak, last_pole_date, represented_guild_id
        FROM global_users
        WHERE user_id = 572416955961835520
    """)
    taku_after = cursor.fetchone()
    if taku_after:
        print(f"   ✅ Racha actual: {taku_after['current_streak']} días")
        print(f"   ✅ Mejor racha: {taku_after['best_streak']} días")
        print(f"   ✅ Último pole: {taku_after['last_pole_date']}")
        print(f"   ✅ Representa server: {taku_after['represented_guild_id']}")
        
        # Verificar que es el MAX
        expected_current = max([t['current_streak'] for t in taku_before])
        expected_best = max([t['best_streak'] for t in taku_before])
        
        if taku_after['current_streak'] == expected_current and taku_after['best_streak'] == expected_best:
            print(f"   ✅ CORRECTO: Se preservó el máximo (27 días)")
        else:
            print(f"   ❌ ERROR: Esperado {expected_current}/{expected_best}, obtenido {taku_after['current_streak']}/{taku_after['best_streak']}")
    else:
        print("   ❌ ERROR: takusito no migrado")
    
    # Crear nueva tabla users sin rachas
    print("\n3️⃣ Recreando tabla users sin columnas de racha...")
    cursor.execute('''
        CREATE TABLE users_new (
            user_id INTEGER,
            guild_id INTEGER,
            username TEXT,
            critical_poles INTEGER DEFAULT 0,
            fast_poles INTEGER DEFAULT 0,
            normal_poles INTEGER DEFAULT 0,
            late_poles INTEGER DEFAULT 0,
            marranero_poles INTEGER DEFAULT 0,
            average_delay_minutes REAL DEFAULT 0,
            best_time_minutes INTEGER,
            impatient_attempts INTEGER DEFAULT 0,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, guild_id)
        )
    ''')
    
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
    
    cursor.execute('DROP TABLE users')
    cursor.execute('ALTER TABLE users_new RENAME TO users')
    print("   ✅ Tabla users actualizada (rachas eliminadas)")
    
    # Actualizar schema version
    cursor.execute('''
        UPDATE schema_metadata 
        SET version = 5, 
            applied_at = CURRENT_TIMESTAMP,
            description = 'TEST: Sistema de rachas globales'
        WHERE version = 2
    ''')
    
    conn.commit()
    
    # Snapshot POST-migración
    print("\n📸 Snapshot POST-migración:")
    cursor.execute("SELECT COUNT(*) as count FROM global_users")
    global_count = cursor.fetchone()['count']
    print(f"   - Total usuarios en global_users: {global_count}")
    
    cursor.execute("SELECT COUNT(*) as count FROM users")
    local_count = cursor.fetchone()['count']
    print(f"   - Total registros en users: {local_count}")
    
    if global_count == unique_users:
        print(f"   ✅ CORRECTO: {global_count} usuarios únicos migrados")
    else:
        print(f"   ❌ ERROR: Esperado {unique_users}, migrado {global_count}")
    
    print("\n" + "="*70)
    print("✅ MIGRACIÓN COMPLETADA CON ÉXITO")
    print("="*70)
    print("\n💾 BD de prueba guardada en: data/pole_bot_test_migration.db")
    print("📌 Puedes inspeccionarla manualmente antes de aplicar en producción")
    
except Exception as e:
    print(f"\n❌ ERROR en migración: {e}")
    import traceback
    traceback.print_exc()
    conn.rollback()
finally:
    conn.close()
