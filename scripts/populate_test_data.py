"""
Script de Población de Datos de Prueba
Genera datos aleatorios para testing y simula una migración de temporada
"""
import sys
import os
import random
from datetime import datetime, timedelta

# Añadir directorio padre al path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.database import Database
from utils.scoring import calculate_points, classify_delay, get_rank_info, get_current_season

# Configuración
TEST_GUILD_ID = 123456789012345678  # ID de servidor ficticio
NUM_USERS = 25  # Número de usuarios a generar
DAYS_TO_SIMULATE = 90  # Días de historial (3 meses)

# Nombres aleatorios para usuarios
USERNAMES = [
    "AlphaGamer", "BetaTester", "GammaRay", "DeltaForce", "EpsilonPrime",
    "ZetaWave", "EtaStorm", "ThetaCore", "IotaBlast", "KappaStar",
    "LambdaWolf", "MuPhoenix", "NuDragon", "XiTiger", "OmicronLion",
    "PiHawk", "RhoEagle", "SigmaKnight", "TauViking", "UpsilonWarrior",
    "PhiMage", "ChiMonk", "PsiNinja", "OmegaLegend", "AlphaPro"
]

def generate_random_poles(db: Database, guild_id: int, num_users: int, num_days: int):
    """Generar poles aleatorias para simular actividad"""
    print(f"\n📊 Generando datos para {num_users} usuarios durante {num_days} días...")
    
    # Crear usuarios con IDs únicos
    user_ids = []
    for i in range(num_users):
        user_id = 100000000000000000 + i  # IDs ficticios pero válidos
        username = USERNAMES[i % len(USERNAMES)] + str(i // len(USERNAMES) + 1) if i >= len(USERNAMES) else USERNAMES[i]
        db.create_user(user_id, guild_id, username)
        user_ids.append(user_id)
        print(f"  ✅ Usuario creado: {username} (ID: {user_id})")
    
    print(f"\n🎲 Simulando {num_days} días de poles...")
    
    # Simular poles durante N días
    base_date = datetime.now() - timedelta(days=num_days)
    poles_created = 0
    
    for day in range(num_days):
        current_date = base_date + timedelta(days=day)
        
        # Hora de apertura aleatoria (entre 8:00 y 20:00)
        opening_hour = random.randint(8, 19)
        opening_minute = random.randint(0, 59)
        opening_time = current_date.replace(hour=opening_hour, minute=opening_minute, second=0)
        
        # Determinar cuántos usuarios participan este día (entre 40% y 90%)
        num_participants = random.randint(int(num_users * 0.4), int(num_users * 0.9))
        participants = random.sample(user_ids, num_participants)
        
        # Generar poles con delays variados
        for position, user_id in enumerate(participants):
            # Delay aleatorio basado en distribución realista
            if position < num_participants * 0.1:  # 10% críticos
                delay = random.randint(0, 10)
            elif position < num_participants * 0.4:  # 30% veloz
                delay = random.randint(11, 180)
            elif position < num_participants * 0.8:  # 40% normal
                delay = random.randint(181, 720)  # hasta 12h
            else:  # 20% marranero
                delay = random.randint(1440, 2880)  # 1-2 días
            
            user_time = opening_time + timedelta(minutes=delay)
            is_next_day = user_time.date() > opening_time.date()
            pole_type = classify_delay(delay, is_next_day)
            
            # Obtener datos del usuario
            user_data = db.get_user(user_id, guild_id)
            if not user_data:
                continue
            
            # Calcular racha (simplificado)
            last_pole_date = user_data.get('last_pole_date')
            if last_pole_date:
                last_date = datetime.strptime(last_pole_date, '%Y-%m-%d').date()
                days_diff = (current_date.date() - last_date).days
                if days_diff == 1:
                    current_streak = user_data.get('current_streak', 0) + 1
                elif days_diff == 0:
                    current_streak = user_data.get('current_streak', 0)
                else:
                    current_streak = 1
            else:
                current_streak = 1
            
            # Calcular puntos
            base, mult, total = calculate_points(pole_type, current_streak)
            
            # Calcular pole_date (para marranero sería día anterior, pero aquí simulamos normal)
            pole_date = current_date.strftime('%Y-%m-%d')
            
            # Guardar pole
            db.save_pole(
                user_id=user_id,
                guild_id=guild_id,
                opening_time=opening_time,
                user_time=user_time,
                delay_minutes=delay,
                pole_type=pole_type,
                points_earned=total,
                streak=current_streak,
                pole_date=pole_date
            )
            
            # Actualizar usuario (sin total_points/total_poles - calculados desde seasons)
            update_data = {
                'current_streak': current_streak,
                'best_streak': max(user_data.get('best_streak', 0), current_streak),
                'last_pole_date': current_date.strftime('%Y-%m-%d')
            }
            
            # Actualizar contadores por tipo
            if pole_type == 'critical':
                update_data['critical_poles'] = user_data.get('critical_poles', 0) + 1
            elif pole_type == 'fast':
                update_data['fast_poles'] = user_data.get('fast_poles', 0) + 1
            elif pole_type == 'normal':
                update_data['normal_poles'] = user_data.get('normal_poles', 0) + 1
            elif pole_type == 'marranero':
                update_data['marranero_poles'] = user_data.get('marranero_poles', 0) + 1
            
            db.update_user(user_id, guild_id, **update_data)
            poles_created += 1
        
        if (day + 1) % 10 == 0:
            print(f"  📅 Día {day + 1}/{num_days} completado ({poles_created} poles hasta ahora)")
    
    print(f"\n✅ Total de poles generadas: {poles_created}")

def migrate_to_season_stats(db: Database, guild_id: int):
    """Migrar datos actuales a season_stats"""
    print("\n📦 Migrando datos a season_stats...")
    
    current_season = get_current_season()
    print(f"  🎮 Season actual: {current_season}")
    
    # Obtener todos los usuarios del servidor
    users = db.get_leaderboard(guild_id, 100)
    
    for user_data in users:
        user_id = user_data['user_id']
        
        # Crear/actualizar registro en season_stats
        # NOTA: total_points y total_poles ahora se calculan dinámicamente desde seasons
        db.update_season_stats(
            user_id=user_id,
            guild_id=guild_id,
            season_id=current_season,
            season_points=user_data.get('total_points', 0),  # Calculado dinámicamente
            season_poles=user_data.get('total_poles', 0),    # Calculado dinámicamente
            season_critical=user_data.get('critical_poles', 0),
            season_fast=user_data.get('fast_poles', 0),
            season_normal=user_data.get('normal_poles', 0),
            season_marranero=user_data.get('marranero_poles', 0),
            season_best_streak=user_data.get('best_streak', 0)
        )
    
    print(f"  ✅ {len(users)} usuarios migrados a season_stats")

def simulate_season_end(db: Database, guild_id: int):
    """Simular finalización de una season"""
    print("\n🏁 Simulando finalización de season...")
    
    # Finalizar la season actual (guardará en historial y otorgará badges)
    current_season = get_current_season()
    db.finalize_season(current_season)
    
    print(f"  ✅ Season '{current_season}' finalizada")
    print("  📜 Datos guardados en season_history")
    print("  🏆 Badges otorgados según ranking final")

def show_statistics(db: Database, guild_id: int):
    """Mostrar estadísticas generadas"""
    print("\n📊 ESTADÍSTICAS GENERADAS")
    print("=" * 60)
    
    # Top 10 usuarios
    top_users = db.get_leaderboard(guild_id, 10)
    print("\n🏆 Top 10 Jugadores:")
    for i, user in enumerate(top_users, 1):
        badge, rank = get_rank_info(user['total_points'])
        print(f"  {i}. {badge} {user['username']}")
        print(f"     💰 {user['total_points']:.1f} pts | 🏁 {user['total_poles']} poles | {user.get('current_streak', 0)} días racha")
    
    # Estadísticas globales
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Total de poles
        cursor.execute('SELECT COUNT(*) FROM poles WHERE guild_id = ?', (guild_id,))
        total_poles = cursor.fetchone()[0]
        
        # Distribución por tipo
        cursor.execute('''
            SELECT pole_type, COUNT(*) as count 
            FROM poles 
            WHERE guild_id = ?
            GROUP BY pole_type
        ''', (guild_id,))
        distribution = cursor.fetchall()
    
    print(f"\n📈 Estadísticas Globales:")
    print(f"  🏁 Total de poles: {total_poles}")
    print(f"\n  📊 Distribución por tipo:")
    for row in distribution:
        pole_type = row[0]
        count = row[1]
        percentage = (count / total_poles * 100) if total_poles > 0 else 0
        print(f"    {pole_type.capitalize()}: {count} ({percentage:.1f}%)")
    
    # Season stats
    current_season = get_current_season()
    season_users = db.get_season_leaderboard(guild_id, current_season, 5)
    
    if season_users:
        print(f"\n🎮 Top 5 Season '{current_season}':")
        for i, user in enumerate(season_users, 1):
            badge, rank = get_rank_info(user['season_points'])
            print(f"  {i}. {badge} {user['username']}: {user['season_points']:.1f} pts")

def main():
    """Función principal"""
    print("=" * 60)
    print("🎮 POLE BOT - Generador de Datos de Prueba")
    print("=" * 60)
    
    db = Database()
    
    # Confirmar antes de continuar
    print(f"\n⚠️  Este script va a generar datos de prueba:")
    print(f"   • {NUM_USERS} usuarios ficticios")
    print(f"   • {DAYS_TO_SIMULATE} días de historial de poles")
    print(f"   • Guild ID: {TEST_GUILD_ID}")
    print(f"\n¿Continuar? (s/n): ", end="")
    
    response = input().lower()
    if response != 's':
        print("❌ Cancelado por el usuario")
        return
    
    # Verificar si el servidor ya tiene datos
    existing = db.get_server_config(TEST_GUILD_ID)
    if existing:
        print("\n⚠️  El servidor ya existe. ¿Limpiar datos existentes? (s/n): ", end="")
        clean = input().lower()
        if clean == 's':
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM users WHERE guild_id = ?', (TEST_GUILD_ID,))
                cursor.execute('DELETE FROM poles WHERE guild_id = ?', (TEST_GUILD_ID,))
                cursor.execute('DELETE FROM season_stats WHERE guild_id = ?', (TEST_GUILD_ID,))
                cursor.execute('DELETE FROM season_history WHERE guild_id = ?', (TEST_GUILD_ID,))
                print("  ✅ Datos anteriores limpiados")
    
    # Inicializar servidor
    print("\n⚙️  Inicializando servidor...")
    db.init_server(TEST_GUILD_ID, 999999999999999999)  # Canal ficticio
    print("  ✅ Servidor inicializado")
    
    # Generar datos
    generate_random_poles(db, TEST_GUILD_ID, NUM_USERS, DAYS_TO_SIMULATE)
    
    # Migrar a season
    migrate_to_season_stats(db, TEST_GUILD_ID)
    
    # Mostrar estadísticas
    show_statistics(db, TEST_GUILD_ID)
    
    # Opción de simular fin de season
    print("\n🏁 ¿Simular finalización de season? (s/n): ", end="")
    sim = input().lower()
    if sim == 's':
        simulate_season_end(db, TEST_GUILD_ID)
        print("\n  ℹ️  Puedes verificar el historial con:")
        print("     SELECT * FROM season_history WHERE guild_id = " + str(TEST_GUILD_ID))
    
    print("\n" + "=" * 60)
    print("✅ COMPLETADO")
    print("=" * 60)
    print(f"\n📝 Usa este Guild ID para testing: {TEST_GUILD_ID}")
    print("💡 Puedes ejecutar este script múltiples veces con diferentes configuraciones")

if __name__ == "__main__":
    main()
