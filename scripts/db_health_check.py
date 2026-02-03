#!/usr/bin/env python3
"""
🔍 Health Check de Base de Datos - Pole Bot
============================================
Script independiente para verificar, consultar y reparar la base de datos sin parar el bot.

Uso:
    python scripts/db_health_check.py              # Solo verificar
    python scripts/db_health_check.py --fix        # Verificar y reparar
    python scripts/db_health_check.py --user 123   # Diagnosticar usuario específico
    python scripts/db_health_check.py --backup     # Crear backup antes de operar
    python scripts/db_health_check.py --interactive # Modo interactivo con menú

Ejemplos:
    python scripts/db_health_check.py --fix --backup
    python scripts/db_health_check.py --user 123456789 --guild 987654321
    python scripts/db_health_check.py -i  # Modo interactivo
"""

import sqlite3
import sys
import argparse
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict

# Colores para terminal
class Colors:
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    END = '\033[0m'

def c(text: str, color: str) -> str:
    """Colorear texto"""
    return f"{color}{text}{Colors.END}"

# Ruta de la BD
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DB_PATH = PROJECT_ROOT / "data" / "pole_bot.db"


def get_connection() -> sqlite3.Connection:
    """Obtener conexión a la BD"""
    if not DB_PATH.exists():
        print(c(f"❌ No se encontró la base de datos en: {DB_PATH}", Colors.RED))
        sys.exit(1)
    
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def create_backup() -> str:
    """Crear backup de la BD"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = PROJECT_ROOT / "data" / "backups"
    backup_dir.mkdir(exist_ok=True)
    
    backup_path = backup_dir / f"pole_bot_backup_{timestamp}.db"
    shutil.copy2(DB_PATH, backup_path)
    
    print(c(f"✅ Backup creado: {backup_path}", Colors.GREEN))
    return str(backup_path)


def get_stats(conn: sqlite3.Connection) -> Dict[str, int]:
    """Obtener estadísticas generales"""
    cursor = conn.cursor()
    stats = {}
    
    cursor.execute('SELECT COUNT(*) FROM users')
    stats['total_users'] = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM poles')
    stats['total_poles'] = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM servers')
    stats['total_servers'] = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM season_stats')
    stats['total_season_stats'] = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(DISTINCT guild_id) FROM poles')
    stats['guilds_with_poles'] = cursor.fetchone()[0]
    
    return stats


def check_stale_streaks(conn: sqlite3.Connection) -> List[Dict]:
    """Verificar rachas fantasma (racha activa pero sin pole reciente)"""
    cursor = conn.cursor()
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    cursor.execute('''
        SELECT user_id, guild_id, username, current_streak, last_pole_date
        FROM users
        WHERE current_streak > 0 
          AND (last_pole_date IS NULL OR last_pole_date < ?)
    ''', (yesterday,))
    
    return [dict(row) for row in cursor.fetchall()]


def check_duplicate_poles(conn: sqlite3.Connection) -> List[Dict]:
    """Verificar poles duplicados (mismo usuario, servidor y día, usando pole_date efectiva)"""
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT user_id, guild_id, pole_date, COUNT(*) as cnt
        FROM poles
        WHERE pole_date IS NOT NULL
        GROUP BY user_id, guild_id, pole_date
        HAVING cnt > 1
    ''')
    
    return [dict(row) for row in cursor.fetchall()]


def check_null_pole_dates(conn: sqlite3.Connection) -> List[Dict]:
    """Verificar poles con pole_date NULL (poles legadas sin procesar)"""
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT user_id, guild_id, COUNT(*) as cnt, 
               MIN(created_at) as oldest, MAX(created_at) as newest
        FROM poles
        WHERE pole_date IS NULL
        GROUP BY user_id, guild_id
    ''')
    
    return [dict(row) for row in cursor.fetchall()]


def check_orphan_poles(conn: sqlite3.Connection) -> List[Dict]:
    """Verificar poles sin usuario correspondiente"""
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT p.user_id, p.guild_id, COUNT(*) as cnt
        FROM poles p
        LEFT JOIN users u ON p.user_id = u.user_id AND p.guild_id = u.guild_id
        WHERE u.user_id IS NULL
        GROUP BY p.user_id, p.guild_id
    ''')
    
    return [dict(row) for row in cursor.fetchall()]


def check_streak_inconsistency(conn: sqlite3.Connection) -> List[Dict]:
    """Verificar current_streak > best_streak"""
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT user_id, guild_id, username, current_streak, best_streak
        FROM users
        WHERE current_streak > best_streak
    ''')
    
    return [dict(row) for row in cursor.fetchall()]


def check_season_stats_mismatch(conn: sqlite3.Connection) -> List[Dict]:
    """Verificar discrepancias entre season_stats y poles reales"""
    cursor = conn.cursor()
    
    # Obtener season activa
    cursor.execute('SELECT season_id FROM seasons WHERE is_active = 1')
    row = cursor.fetchone()
    if not row:
        return []
    
    current_season = row[0]
    season_year = '2025' if current_season == 'preseason' else str(2025 + int(current_season.split('_')[1]))
    
    cursor.execute('''
        SELECT 
            ss.user_id, ss.guild_id, ss.season_poles,
            COUNT(p.id) as actual_poles
        FROM season_stats ss
        LEFT JOIN poles p ON ss.user_id = p.user_id 
            AND ss.guild_id = p.guild_id
            AND strftime('%Y', p.created_at) = ?
        WHERE ss.season_id = ?
        GROUP BY ss.user_id, ss.guild_id, ss.season_poles
        HAVING ABS(ss.season_poles - actual_poles) > 0
    ''', (season_year, current_season))
    
    return [dict(row) for row in cursor.fetchall()]


def check_servers_no_channel(conn: sqlite3.Connection) -> List[Dict]:
    """Verificar servidores con poles pero sin canal configurado"""
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT s.guild_id, COUNT(p.id) as pole_count
        FROM servers s
        JOIN poles p ON s.guild_id = p.guild_id
        WHERE s.pole_channel_id IS NULL OR s.pole_channel_id = 0
        GROUP BY s.guild_id
    ''')
    
    return [dict(row) for row in cursor.fetchall()]


def check_poles_without_season_stats(conn: sqlite3.Connection) -> List[Dict]:
    """Verificar poles que NO tienen entrada en season_stats correspondiente"""
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT DISTINCT p.user_id, p.guild_id, COUNT(*) as pole_count, p.created_at
        FROM poles p
        LEFT JOIN season_stats ss ON p.user_id = ss.user_id 
            AND p.guild_id = ss.guild_id
        WHERE ss.user_id IS NULL
        GROUP BY p.user_id, p.guild_id
    ''')
    
    return [dict(row) for row in cursor.fetchall()]


def check_category_counters_mismatch(conn: sqlite3.Connection) -> List[Dict]:
    """Verificar si critical_poles + fast_poles + normal_poles + marranero_poles != total conteo real"""
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            u.user_id, u.guild_id, u.username,
            (u.critical_poles + u.fast_poles + u.normal_poles + u.marranero_poles) as counted,
            COUNT(p.id) as actual_poles
        FROM users u
        LEFT JOIN poles p ON u.user_id = p.user_id AND u.guild_id = p.guild_id
        GROUP BY u.user_id, u.guild_id
        HAVING counted != actual_poles
    ''')
    
    return [dict(row) for row in cursor.fetchall()]


def check_last_pole_date_mismatch(conn: sqlite3.Connection) -> List[Dict]:
    """Verificar si last_pole_date no coincide con el último pole real"""
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            u.user_id, u.guild_id, u.username, u.last_pole_date,
            MAX(DATE(p.user_time)) as actual_last_pole
        FROM users u
        LEFT JOIN poles p ON u.user_id = p.user_id AND u.guild_id = p.guild_id
        GROUP BY u.user_id, u.guild_id
        HAVING u.last_pole_date != actual_last_pole
    ''')
    
    return [dict(row) for row in cursor.fetchall()]


def check_season_best_streak_mismatch(conn: sqlite3.Connection) -> List[Dict]:
    """Verificar si season_best_streak < current_streak (inconsistencia lógica)"""
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            ss.user_id, ss.guild_id, ss.season_best_streak,
            u.current_streak
        FROM season_stats ss
        JOIN users u ON ss.user_id = u.user_id AND ss.guild_id = u.guild_id
        WHERE ss.season_best_streak < u.current_streak
    ''')
    
    return [dict(row) for row in cursor.fetchall()]


def check_poles_without_guild_config(conn: sqlite3.Connection) -> List[Dict]:
    """Verificar poles de guilds que no existen en tabla servers"""
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT DISTINCT p.guild_id, COUNT(*) as pole_count, MAX(p.created_at) as last_pole
        FROM poles p
        LEFT JOIN servers s ON p.guild_id = s.guild_id
        WHERE s.guild_id IS NULL
        GROUP BY p.guild_id
    ''')
    
    return [dict(row) for row in cursor.fetchall()]


def diagnose_user(conn: sqlite3.Connection, user_id: int, guild_id: Optional[int] = None):
    """Diagnosticar un usuario específico"""
    cursor = conn.cursor()
    
    print(c(f"\n{'='*60}", Colors.CYAN))
    print(c(f"🔍 DIAGNÓSTICO DE USUARIO: {user_id}", Colors.BOLD))
    print(c(f"{'='*60}", Colors.CYAN))
    
    # Buscar en qué guilds está
    if guild_id:
        cursor.execute('SELECT * FROM users WHERE user_id = ? AND guild_id = ?', (user_id, guild_id))
    else:
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    
    users = cursor.fetchall()
    
    if not users:
        print(c(f"❌ Usuario {user_id} no encontrado en la BD", Colors.RED))
        return
    
    for user in users:
        user = dict(user)
        gid = user['guild_id']
        
        print(c(f"\n📊 Guild: {gid}", Colors.YELLOW))
        print(f"   Username: {user.get('username', 'N/A')}")
        print(f"   Racha actual: {user.get('current_streak', 0)}")
        print(f"   Mejor racha: {user.get('best_streak', 0)}")
        print(f"   Último pole: {user.get('last_pole_date', 'NUNCA')}")
        
        # Poles de este usuario en este guild
        cursor.execute('''
            SELECT DATE(user_time) as fecha, pole_type, points_earned, delay_minutes
            FROM poles
            WHERE user_id = ? AND guild_id = ?
            ORDER BY user_time DESC
            LIMIT 10
        ''', (user_id, gid))
        
        poles = cursor.fetchall()
        print(f"\n   📜 Últimos poles ({len(poles)}):")
        for p in poles:
            p = dict(p)
            emoji = {'critical': '💎', 'fast': '⚡', 'normal': '🏁', 'marranero': '🐷'}.get(p['pole_type'], '❓')
            print(f"      {emoji} {p['fecha']} | {p['pole_type']:10} | {p['points_earned']:.1f}pts | {p['delay_minutes']}min")
        
        # Verificar pole global hoy
        today = datetime.now().strftime('%Y-%m-%d')
        cursor.execute('''
            SELECT guild_id, pole_type, points_earned
            FROM poles
            WHERE user_id = ? AND DATE(user_time) = ?
        ''', (user_id, today))
        
        today_poles = cursor.fetchall()
        if today_poles:
            print(c(f"\n   ⚠️  Poles HOY ({today}):", Colors.YELLOW))
            for tp in today_poles:
                tp = dict(tp)
                status = "✅ Este guild" if tp['guild_id'] == gid else "🚫 OTRO guild"
                print(f"      {status} (guild {tp['guild_id']}) - {tp['pole_type']}")
        else:
            print(c(f"\n   ✅ Sin poles hoy ({today}) - puede polear", Colors.GREEN))


def fix_issues(conn: sqlite3.Connection) -> List[str]:
    """Reparar problemas detectados"""
    fixes = []
    cursor = conn.cursor()
    
    # FIX 0: Llenar pole_date NULL con DATE(user_time) [CRÍTICO]
    cursor.execute('''
        UPDATE poles
        SET pole_date = DATE(user_time)
        WHERE pole_date IS NULL
    ''')
    
    if cursor.rowcount > 0:
        fixes.append(f"✅ Reparadas {cursor.rowcount} poles con pole_date faltante")
    
    # FIX 1: Rachas fantasma
    yesterday = (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d')
    
    cursor.execute('''
        UPDATE users
        SET current_streak = 0
        WHERE current_streak > 0 
          AND (last_pole_date IS NULL OR last_pole_date < ?)
    ''', (yesterday,))
    
    if cursor.rowcount > 0:
        fixes.append(f"✅ Reseteadas {cursor.rowcount} rachas fantasma")
    
    # FIX 2: best_streak < current_streak
    cursor.execute('''
        UPDATE users
        SET best_streak = current_streak
        WHERE current_streak > best_streak
    ''')
    
    if cursor.rowcount > 0:
        fixes.append(f"✅ Corregidas {cursor.rowcount} mejores rachas")
    
    # FIX 3: Crear usuarios para poles huérfanos
    cursor.execute('''
        SELECT DISTINCT p.user_id, p.guild_id
        FROM poles p
        LEFT JOIN users u ON p.user_id = u.user_id AND p.guild_id = u.guild_id
        WHERE u.user_id IS NULL
    ''')
    orphans = cursor.fetchall()
    
    for user_id, guild_id in orphans:
        cursor.execute('''
            INSERT OR IGNORE INTO users (user_id, guild_id, username)
            VALUES (?, ?, ?)
        ''', (user_id, guild_id, f"User_{user_id}"))
    
    if orphans:
        fixes.append(f"✅ Creados {len(orphans)} usuarios para poles huérfanos")
    
    # FIX 4: Eliminar poles duplicados (mantener el primero de cada día, usando pole_date)
    cursor.execute('''
        SELECT user_id, guild_id, pole_date
        FROM poles
        WHERE pole_date IS NOT NULL
        GROUP BY user_id, guild_id, pole_date
        HAVING COUNT(*) > 1
    ''')
    dup_groups = cursor.fetchall()
    
    total_deleted = 0
    for row in dup_groups:
        user_id, guild_id, pole_date = row['user_id'], row['guild_id'], row['pole_date']
        # Obtener todos los IDs de ese grupo, ordenados por user_time (el primero es el válido)
        cursor.execute('''
            SELECT id FROM poles
            WHERE user_id = ? AND guild_id = ? AND DATE(user_time) = ?
            ORDER BY user_time ASC
        ''', (user_id, guild_id, pole_date))
        pole_ids = [r['id'] for r in cursor.fetchall()]
        
        # Eliminar todos menos el primero
        if len(pole_ids) > 1:
            ids_to_delete = pole_ids[1:]  # Todo excepto el primero
            placeholders = ','.join('?' * len(ids_to_delete))
            cursor.execute(f'DELETE FROM poles WHERE id IN ({placeholders})', ids_to_delete)
            total_deleted += len(ids_to_delete)
    
    if total_deleted > 0:
        fixes.append(f"✅ Eliminados {total_deleted} poles duplicados (manteniendo el primero de cada día)")
    
    # FIX 5: Crear season_stats para poles sin entry
    poles_without_stats = check_poles_without_season_stats(conn)
    stats_created = 0
    for row in poles_without_stats:
        user_id = row['user_id']
        guild_id = row['guild_id']
        
        # Obtener current_season
        cursor.execute('SELECT season_id FROM seasons WHERE is_active = 1')
        season_row = cursor.fetchone()
        if season_row:
            current_season = season_row[0]
            
            # Contar poles reales para este usuario en esta season
            cursor.execute('''
                SELECT COUNT(*) as pole_count,
                       SUM(CASE WHEN pole_type = 'critical' THEN 1 ELSE 0 END) as critical,
                       SUM(CASE WHEN pole_type = 'fast' THEN 1 ELSE 0 END) as fast,
                       SUM(CASE WHEN pole_type = 'normal' THEN 1 ELSE 0 END) as normal,
                       SUM(CASE WHEN pole_type = 'marranero' THEN 1 ELSE 0 END) as marranero,
                       COALESCE(SUM(points_earned), 0) as total_points
                FROM poles
                WHERE user_id = ? AND guild_id = ?
            ''', (user_id, guild_id))
            pole_stats = cursor.fetchone()
            
            if pole_stats and pole_stats[0] > 0:
                cursor.execute('''
                    INSERT OR IGNORE INTO season_stats 
                    (user_id, guild_id, season_id, season_poles, season_points, 
                     season_critical, season_fast, season_normal, season_marranero)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (user_id, guild_id, current_season, pole_stats[0], pole_stats[5],
                      pole_stats[1] or 0, pole_stats[2] or 0, pole_stats[3] or 0, pole_stats[4] or 0))
                stats_created += 1
    
    if stats_created > 0:
        fixes.append(f"✅ Creadas {stats_created} entradas en season_stats para poles huérfanas")
    
    # FIX 6: Recalcular contadores de categoría
    category_mismatches = check_category_counters_mismatch(conn)
    category_fixed = 0
    for row in category_mismatches:
        user_id = row['user_id']
        guild_id = row['guild_id']
        
        # Recalcular desde poles
        cursor.execute('''
            SELECT 
                SUM(CASE WHEN pole_type = 'critical' THEN 1 ELSE 0 END) as critical,
                SUM(CASE WHEN pole_type = 'fast' THEN 1 ELSE 0 END) as fast,
                SUM(CASE WHEN pole_type = 'normal' THEN 1 ELSE 0 END) as normal,
                SUM(CASE WHEN pole_type = 'marranero' THEN 1 ELSE 0 END) as marranero
            FROM poles
            WHERE user_id = ? AND guild_id = ?
        ''', (user_id, guild_id))
        counts = cursor.fetchone()
        
        cursor.execute('''
            UPDATE users
            SET critical_poles = ?, fast_poles = ?, normal_poles = ?, marranero_poles = ?
            WHERE user_id = ? AND guild_id = ?
        ''', (counts[0] or 0, counts[1] or 0, counts[2] or 0, counts[3] or 0, user_id, guild_id))
        category_fixed += 1
    
    if category_fixed > 0:
        fixes.append(f"✅ Recalculados contadores de categoría en {category_fixed} usuarios")
    
    # FIX 7: Sincronizar last_pole_date
    date_mismatches = check_last_pole_date_mismatch(conn)
    date_fixed = 0
    for row in date_mismatches:
        user_id = row['user_id']
        guild_id = row['guild_id']
        actual_last = row['actual_last_pole']
        
        if actual_last:
            cursor.execute('''
                UPDATE users
                SET last_pole_date = ?
                WHERE user_id = ? AND guild_id = ?
            ''', (actual_last, user_id, guild_id))
            date_fixed += 1
        else:
            # Si no hay poles, resetear
            cursor.execute('''
                UPDATE users
                SET last_pole_date = NULL
                WHERE user_id = ? AND guild_id = ?
            ''', (user_id, guild_id))
            date_fixed += 1
    
    if date_fixed > 0:
        fixes.append(f"✅ Sincronizados last_pole_date en {date_fixed} usuarios")
    
    # FIX 8: Corregir season_best_streak < current_streak
    streak_mismatches = check_season_best_streak_mismatch(conn)
    streak_fixed = 0
    for row in streak_mismatches:
        user_id = row['user_id']
        guild_id = row['guild_id']
        current = row['current_streak']
        
        cursor.execute('''
            UPDATE season_stats
            SET season_best_streak = ?
            WHERE user_id = ? AND guild_id = ?
        ''', (current, user_id, guild_id))
        streak_fixed += 1
    
    if streak_fixed > 0:
        fixes.append(f"✅ Corregidas {streak_fixed} entradas con season_best_streak inválido")
    
    # FIX 9: Crear servidores faltantes
    missing_guilds = check_poles_without_guild_config(conn)
    guilds_created = 0
    for row in missing_guilds:
        guild_id = row['guild_id']
        
        cursor.execute('''
            INSERT OR IGNORE INTO servers (guild_id)
            VALUES (?)
        ''', (guild_id,))
        guilds_created += 1
    
    if guilds_created > 0:
        fixes.append(f"✅ Creadas {guilds_created} configuraciones de guild faltantes")
    
    conn.commit()
    return fixes


def run_health_check(do_fix: bool = False, backup: bool = False):
    """Ejecutar verificación completa"""
    print(c("\n" + "="*60, Colors.CYAN))
    print(c("   🔍 POLE BOT - DATABASE HEALTH CHECK", Colors.BOLD))
    print(c("="*60, Colors.CYAN))
    print(f"   📂 BD: {DB_PATH}")
    print(f"   🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(c("="*60 + "\n", Colors.CYAN))
    
    if backup:
        create_backup()
    
    conn = get_connection()
    
    # Estadísticas
    stats = get_stats(conn)
    print(c("📈 ESTADÍSTICAS GENERALES", Colors.BOLD))
    print(f"   👥 Usuarios: {stats['total_users']}")
    print(f"   🏁 Poles: {stats['total_poles']}")
    print(f"   🏠 Servidores: {stats['total_servers']}")
    print(f"   📊 Season Stats: {stats['total_season_stats']}")
    print(f"   🌍 Guilds con poles: {stats['guilds_with_poles']}")
    
    issues = []
    warnings = []
    
    # CHECK 1: Rachas fantasma
    print(c("\n🔎 Verificando rachas fantasma...", Colors.BLUE))
    stale = check_stale_streaks(conn)
    if stale:
        for s in stale[:5]:
            issues.append(f"⚠️ Racha fantasma: {s['username']} (ID:{s['user_id']}) racha={s['current_streak']} último={s['last_pole_date']}")
        if len(stale) > 5:
            issues.append(f"   ... y {len(stale) - 5} más")
        print(c(f"   ❌ Encontradas {len(stale)} rachas fantasma", Colors.RED))
    else:
        print(c("   ✅ Sin rachas fantasma", Colors.GREEN))
    
    # CHECK 2: Poles duplicados
    print(c("\n🔎 Verificando poles duplicados...", Colors.BLUE))
    dups = check_duplicate_poles(conn)
    if dups:
        for d in dups[:5]:
            issues.append(f"🔴 Duplicado: user {d['user_id']} guild {d['guild_id']} fecha {d['pole_date']} x{d['cnt']}")
        if len(dups) > 5:
            issues.append(f"   ... y {len(dups) - 5} más")
        print(c(f"   ❌ Encontrados {len(dups)} duplicados", Colors.RED))
    else:
        print(c("   ✅ Sin duplicados", Colors.GREEN))
    
    # CHECK 2.5: Poles con pole_date NULL
    print(c("\n🔎 Verificando poles con pole_date NULL...", Colors.BLUE))
    null_dates = check_null_pole_dates(conn)
    if null_dates:
        total_null = sum(row['cnt'] for row in null_dates)
        for nd in null_dates[:5]:
            issues.append(f"🔴 pole_date NULL: user {nd['user_id']} guild {nd['guild_id']} x{nd['cnt']} (desde {nd['oldest']})")
        if len(null_dates) > 5:
            issues.append(f"   ... y {len(null_dates) - 5} más")
        print(c(f"   ❌ Encontradas {total_null} poles con pole_date NULL", Colors.RED))
    else:
        print(c("   ✅ Todas las poles tienen pole_date válida", Colors.GREEN))
    
    # CHECK 3: Poles huérfanos
    print(c("\n🔎 Verificando poles huérfanos...", Colors.BLUE))
    orphans = check_orphan_poles(conn)
    if orphans:
        for o in orphans[:5]:
            warnings.append(f"🟡 Huérfano: user {o['user_id']} guild {o['guild_id']} x{o['cnt']} poles")
        if len(orphans) > 5:
            warnings.append(f"   ... y {len(orphans) - 5} más")
        print(c(f"   ⚠️ Encontrados {len(orphans)} huérfanos", Colors.YELLOW))
    else:
        print(c("   ✅ Sin huérfanos", Colors.GREEN))
    
    # CHECK 4: Racha inconsistente
    print(c("\n🔎 Verificando consistencia de rachas...", Colors.BLUE))
    streak_issues = check_streak_inconsistency(conn)
    if streak_issues:
        for si in streak_issues[:5]:
            issues.append(f"🔴 Racha inválida: {si['username']} current={si['current_streak']} > best={si['best_streak']}")
        print(c(f"   ❌ Encontradas {len(streak_issues)} inconsistencias", Colors.RED))
    else:
        print(c("   ✅ Rachas consistentes", Colors.GREEN))
    
    # CHECK 5: Season stats
    print(c("\n🔎 Verificando season_stats...", Colors.BLUE))
    mismatches = check_season_stats_mismatch(conn)
    if mismatches:
        for m in mismatches[:5]:
            warnings.append(f"🟠 Discrepancia: user {m['user_id']} guild {m['guild_id']} stats={m['season_poles']} vs real={m['actual_poles']}")
        if len(mismatches) > 5:
            warnings.append(f"   ... y {len(mismatches) - 5} más")
        print(c(f"   ⚠️ Encontradas {len(mismatches)} discrepancias", Colors.YELLOW))
    else:
        print(c("   ✅ Season stats correctos", Colors.GREEN))
    
    # CHECK 6: Poles sin season_stats
    print(c("\n🔎 Verificando poles sin season_stats...", Colors.BLUE))
    poles_no_stats = check_poles_without_season_stats(conn)
    if poles_no_stats:
        total_orphan_poles = sum(row['pole_count'] for row in poles_no_stats)
        for pns in poles_no_stats[:5]:
            issues.append(f"🔴 Poles sin season_stats: user {pns['user_id']} guild {pns['guild_id']} ({pns['pole_count']} poles)")
        if len(poles_no_stats) > 5:
            issues.append(f"   ... y {len(poles_no_stats) - 5} más")
        print(c(f"   ❌ Encontradas {len(poles_no_stats)} entradas sin season_stats ({total_orphan_poles} poles)", Colors.RED))
    else:
        print(c("   ✅ Todas las poles tienen season_stats", Colors.GREEN))
    
    # CHECK 7: Contadores de categoría desactualizados
    print(c("\n🔎 Verificando contadores de categoría...", Colors.BLUE))
    category_mismatches = check_category_counters_mismatch(conn)
    if category_mismatches:
        for cm in category_mismatches[:5]:
            issues.append(f"🔴 Contador desactualizado: {cm['username']} (ID:{cm['user_id']}) counted={cm['counted']} actual={cm['actual_poles']}")
        if len(category_mismatches) > 5:
            issues.append(f"   ... y {len(category_mismatches) - 5} más")
        print(c(f"   ❌ Encontrados {len(category_mismatches)} desajustes", Colors.RED))
    else:
        print(c("   ✅ Contadores de categoría correctos", Colors.GREEN))
    
    # CHECK 8: last_pole_date desincronizado
    print(c("\n🔎 Verificando last_pole_date...", Colors.BLUE))
    date_mismatches = check_last_pole_date_mismatch(conn)
    if date_mismatches:
        for dm in date_mismatches[:5]:
            issues.append(f"🔴 Fecha desincronizada: {dm['username']} (ID:{dm['user_id']}) stored={dm['last_pole_date']} actual={dm['actual_last_pole']}")
        if len(date_mismatches) > 5:
            issues.append(f"   ... y {len(date_mismatches) - 5} más")
        print(c(f"   ❌ Encontrados {len(date_mismatches)} desajustes", Colors.RED))
    else:
        print(c("   ✅ last_pole_date sincronizado correctamente", Colors.GREEN))
    
    # CHECK 9: Guilds sin configuración
    print(c("\n🔎 Verificando configuración de guilds...", Colors.BLUE))
    missing_guilds = check_poles_without_guild_config(conn)
    if missing_guilds:
        total_poles_missing = sum(row['pole_count'] for row in missing_guilds)
        for mg in missing_guilds[:5]:
            warnings.append(f"🟡 Guild sin config: {mg['guild_id']} ({mg['pole_count']} poles)")
        if len(missing_guilds) > 5:
            warnings.append(f"   ... y {len(missing_guilds) - 5} más")
        print(c(f"   ⚠️ Encontrados {len(missing_guilds)} guilds sin config ({total_poles_missing} poles)", Colors.YELLOW))
    else:
        print(c("   ✅ Todos los guilds configurados", Colors.GREEN))
    
    # RESUMEN
    print(c("\n" + "="*60, Colors.CYAN))
    print(c("   📋 RESUMEN", Colors.BOLD))
    print(c("="*60, Colors.CYAN))
    
    if issues:
        print(c(f"\n🔴 PROBLEMAS ({len(issues)}):", Colors.RED))
        for i in issues:
            print(f"   {i}")
    
    if warnings:
        print(c(f"\n🟡 ADVERTENCIAS ({len(warnings)}):", Colors.YELLOW))
        for w in warnings:
            print(f"   {w}")
    
    if not issues and not warnings:
        print(c("\n✅ ¡La base de datos está en buen estado!", Colors.GREEN))
    
    # REPARAR si se pidió
    if do_fix and (issues or warnings):
        print(c("\n" + "="*60, Colors.MAGENTA))
        print(c("   🔧 REPARANDO...", Colors.BOLD))
        print(c("="*60, Colors.MAGENTA))
        
        fixes = fix_issues(conn)
        if fixes:
            for f in fixes:
                print(f"   {f}")
        else:
            print("   No se aplicaron reparaciones automáticas.")
    elif issues or warnings:
        print(c("\n💡 Usa --fix para intentar reparar automáticamente", Colors.CYAN))
    
    conn.close()
    print()


# ==================== MODO INTERACTIVO ====================

def confirm(prompt: str) -> bool:
    """Pedir confirmación al usuario"""
    while True:
        resp = input(f"{prompt} [s/n]: ").strip().lower()
        if resp in ('s', 'si', 'sí', 'y', 'yes'):
            return True
        if resp in ('n', 'no'):
            return False
        print("Por favor, responde 's' o 'n'")


def interactive_menu():
    """Menú interactivo para operaciones de BD"""
    conn = get_connection()
    
    while True:
        print(c("\n" + "="*60, Colors.CYAN))
        print(c("   🔧 POLE BOT - GESTIÓN DE BASE DE DATOS", Colors.BOLD))
        print(c("="*60, Colors.CYAN))
        print("""
   1. 🔍 Health Check (verificar integridad)
   2. 🔧 Reparar problemas automáticamente
   3. 💾 Crear backup
   4. 👤 Consultar usuario
   5. 📊 Ver estadísticas generales
   6. 🏁 Ver últimos poles
   7. 🔥 Ver rachas activas
   8. ⏰ Ver configuración de servidores (horas de apertura)
   9. ⚙️  Modificar datos de usuario
  10. 🗑️  Eliminar pole específico
  11. 🔄 Resetear racha de usuario
  12. 📅 Ver poles de un día específico
   0. 🚪 Salir
        """)
        
        choice = input(c("Selecciona una opción: ", Colors.YELLOW)).strip()
        
        if choice == '0':
            print(c("\n👋 ¡Hasta luego!", Colors.GREEN))
            break
        
        elif choice == '1':
            conn.close()
            run_health_check(do_fix=False, backup=False)
            conn = get_connection()
        
        elif choice == '2':
            if confirm("¿Crear backup antes de reparar?"):
                create_backup()
            conn.close()
            run_health_check(do_fix=True, backup=False)
            conn = get_connection()
        
        elif choice == '3':
            create_backup()
        
        elif choice == '4':
            user_id = input("ID de usuario: ").strip()
            guild_id = input("ID de guild (Enter para todos): ").strip()
            try:
                uid = int(user_id)
                gid = int(guild_id) if guild_id else None
                diagnose_user(conn, uid, gid)
            except ValueError:
                print(c("❌ ID inválido", Colors.RED))
        
        elif choice == '5':
            interactive_show_stats(conn)
        
        elif choice == '6':
            interactive_show_recent_poles(conn)
        
        elif choice == '7':
            interactive_show_active_streaks(conn)
        
        elif choice == '8':
            interactive_show_server_config(conn)
        
        elif choice == '9':
            interactive_modify_user(conn)
        
        elif choice == '10':
            interactive_delete_pole(conn)
        
        elif choice == '11':
            interactive_reset_streak(conn)
        
        elif choice == '12':
            interactive_show_poles_by_date(conn)
        
        else:
            print(c("❌ Opción no válida", Colors.RED))
    
    conn.close()


def interactive_show_stats(conn: sqlite3.Connection):
    """Mostrar estadísticas detalladas"""
    cursor = conn.cursor()
    
    print(c("\n📊 ESTADÍSTICAS DETALLADAS", Colors.BOLD))
    
    # General
    stats = get_stats(conn)
    print(f"\n👥 Total usuarios: {stats['total_users']}")
    print(f"🏁 Total poles: {stats['total_poles']}")
    print(f"🏠 Servidores: {stats['total_servers']}")
    
    # Por tipo de pole
    cursor.execute('''
        SELECT pole_type, COUNT(*) as cnt, SUM(points_earned) as pts
        FROM poles
        GROUP BY pole_type
        ORDER BY cnt DESC
    ''')
    print(c("\n📈 Poles por tipo:", Colors.CYAN))
    for row in cursor.fetchall():
        emoji = {'critical': '💎', 'fast': '⚡', 'normal': '🏁', 'marranero': '🐷'}.get(row[0], '❓')
        print(f"   {emoji} {row[0]}: {row[1]} poles ({row[2]:.1f} pts)")
    
    # Top 5 usuarios
    cursor.execute('''
        SELECT u.username, u.user_id, 
               COALESCE(SUM(ss.season_points), 0) as pts,
               COALESCE(SUM(ss.season_poles), 0) as poles
        FROM users u
        LEFT JOIN season_stats ss ON u.user_id = ss.user_id AND u.guild_id = ss.guild_id
        GROUP BY u.user_id
        ORDER BY pts DESC
        LIMIT 5
    ''')
    print(c("\n🏆 Top 5 usuarios:", Colors.CYAN))
    for i, row in enumerate(cursor.fetchall(), 1):
        print(f"   {i}. {row[0]} - {row[2]:.1f} pts ({row[3]} poles)")


def interactive_show_recent_poles(conn: sqlite3.Connection):
    """Mostrar últimos poles"""
    cursor = conn.cursor()
    
    limit = input("¿Cuántos poles mostrar? [10]: ").strip()
    limit = int(limit) if limit.isdigit() else 10
    
    cursor.execute('''
        SELECT p.id, u.username, p.guild_id, DATE(p.user_time) as fecha,
               p.pole_type, p.points_earned, p.delay_minutes
        FROM poles p
        LEFT JOIN users u ON p.user_id = u.user_id AND p.guild_id = u.guild_id
        ORDER BY p.created_at DESC
        LIMIT ?
    ''', (limit,))
    
    print(c(f"\n🏁 Últimos {limit} poles:", Colors.BOLD))
    for row in cursor.fetchall():
        emoji = {'critical': '💎', 'fast': '⚡', 'normal': '🏁', 'marranero': '🐷'}.get(row[4], '❓')
        print(f"   #{row[0]} | {row[3]} | {emoji} {row[4]:10} | {row[1] or 'Unknown':15} | {row[5]:.1f}pts | {row[6]}min")


def interactive_show_active_streaks(conn: sqlite3.Connection):
    """Mostrar rachas activas"""
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT username, user_id, guild_id, current_streak, best_streak, last_pole_date
        FROM users
        WHERE current_streak > 0
        ORDER BY current_streak DESC
    ''')
    
    rows = cursor.fetchall()
    if not rows:
        print(c("\n❌ No hay rachas activas", Colors.YELLOW))
        return
    
    print(c(f"\n🔥 Rachas activas ({len(rows)}):", Colors.BOLD))
    for row in rows:
        print(f"   🔥 {row[0]} (ID:{row[1]}) - {row[3]} días (mejor: {row[4]}) - último: {row[5]}")


def interactive_show_server_config(conn: sqlite3.Connection):
    """Mostrar configuración de todos los servidores incluyendo hora de apertura"""
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT guild_id, pole_channel_id, daily_pole_time, 
               pole_range_start, pole_range_end,
               notify_opening, notify_winner, ping_role_id, ping_mode,
               created_at
        FROM servers
        ORDER BY created_at DESC
    ''')
    
    rows = cursor.fetchall()
    if not rows:
        print(c("\n❌ No hay servidores configurados", Colors.YELLOW))
        return
    
    now = datetime.now()
    
    print(c(f"\n⏰ CONFIGURACIÓN DE SERVIDORES ({len(rows)}):", Colors.BOLD))
    print(c("="*80, Colors.CYAN))
    
    for row in rows:
        row = dict(row)
        print(c(f"\n🏠 Guild ID: {row['guild_id']}", Colors.YELLOW))
        print(f"   📺 Canal pole: {row['pole_channel_id'] or 'No configurado'}")
        
        # Hora de apertura de hoy
        daily_time = row['daily_pole_time']
        if daily_time:
            print(c(f"   ⏰ Hora de apertura HOY: {daily_time}", Colors.GREEN))
            
            # Calcular si ya pasó o cuánto falta
            try:
                h, m, s = [int(x) for x in str(daily_time).split(':')]
                opening = datetime(now.year, now.month, now.day, h, m, s)
                
                if now < opening:
                    delta = opening - now
                    hours, remainder = divmod(int(delta.total_seconds()), 3600)
                    minutes = remainder // 60
                    print(c(f"   ⏳ Faltan: {hours}h {minutes}m para abrir", Colors.CYAN))
                else:
                    delta = now - opening
                    hours, remainder = divmod(int(delta.total_seconds()), 3600)
                    minutes = remainder // 60
                    print(c(f"   ✅ Ya abrió hace: {hours}h {minutes}m", Colors.GREEN))
            except:
                pass  # Ignorar si no se puede parsear la hora de apertura
        else:
            print(c(f"   ⚠️ Sin hora de apertura configurada para hoy", Colors.RED))
        
        print(f"   📢 Notif. apertura: {'✅' if row['notify_opening'] else '❌'}")
        print(f"   🏆 Notif. ganador: {'✅' if row['notify_winner'] else '❌'}")
        print(f"   🔔 Ping mode: {row['ping_mode'] or 'none'}")
        if row['ping_role_id']:
            print(f"   🎭 Ping role ID: {row['ping_role_id']}")
        
        # Contar poles de hoy en este servidor
        today = now.strftime('%Y-%m-%d')
        cursor.execute('''
            SELECT COUNT(*) FROM poles
            WHERE guild_id = ? AND DATE(user_time) = ?
        ''', (row['guild_id'], today))
        poles_today = cursor.fetchone()[0]
        print(f"   🏁 Poles hoy: {poles_today}")
        
        # Último pole en este servidor
        cursor.execute('''
            SELECT u.username, p.pole_type, p.user_time
            FROM poles p
            LEFT JOIN users u ON p.user_id = u.user_id AND p.guild_id = u.guild_id
            WHERE p.guild_id = ?
            ORDER BY p.created_at DESC
            LIMIT 1
        ''', (row['guild_id'],))
        last_pole = cursor.fetchone()
        if last_pole:
            print(f"   📝 Último pole: {last_pole[0] or 'Unknown'} ({last_pole[1]}) - {last_pole[2]}")


def interactive_show_poles_by_date(conn: sqlite3.Connection):
    """Mostrar poles de un día específico"""
    cursor = conn.cursor()
    
    date_str = input("Fecha (YYYY-MM-DD) [hoy]: ").strip()
    if not date_str:
        date_str = datetime.now().strftime('%Y-%m-%d')
    
    # Validar formato
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
    except ValueError:
        print(c("❌ Formato de fecha inválido. Usa YYYY-MM-DD", Colors.RED))
        return
    
    cursor.execute('''
        SELECT p.id, u.username, p.user_id, p.guild_id, 
               TIME(p.user_time) as hora,
               p.pole_type, p.points_earned, p.delay_minutes, p.streak_at_time
        FROM poles p
        LEFT JOIN users u ON p.user_id = u.user_id AND p.guild_id = u.guild_id
        WHERE DATE(p.user_time) = ?
        ORDER BY p.user_time ASC
    ''', (date_str,))
    
    rows = cursor.fetchall()
    if not rows:
        print(c(f"\n❌ No hay poles para {date_str}", Colors.YELLOW))
        return
    
    print(c(f"\n📅 Poles del {date_str} ({len(rows)} total):", Colors.BOLD))
    print(c("-"*90, Colors.CYAN))
    print(f"   {'ID':>5} | {'Hora':>8} | {'Tipo':>10} | {'Usuario':>15} | {'Pts':>6} | {'Delay':>6} | {'Racha':>5}")
    print(c("-"*90, Colors.CYAN))
    
    for row in rows:
        emoji = {'critical': '💎', 'fast': '⚡', 'normal': '🏁', 'marranero': '🐷'}.get(row[5], '❓')
        username = (row[1] or f"ID:{row[2]}")[:15]
        print(f"   {row[0]:>5} | {row[4]:>8} | {emoji} {row[5]:>8} | {username:>15} | {row[6]:>5.1f} | {row[7]:>5}m | {row[8]:>5}")


def interactive_modify_user(conn: sqlite3.Connection):
    """Modificar datos de un usuario"""
    cursor = conn.cursor()
    
    user_id = input("ID de usuario: ").strip()
    guild_id = input("ID de guild: ").strip()
    
    try:
        uid = int(user_id)
        gid = int(guild_id)
    except ValueError:
        print(c("❌ IDs inválidos", Colors.RED))
        return
    
    # Mostrar datos actuales
    cursor.execute('SELECT * FROM users WHERE user_id = ? AND guild_id = ?', (uid, gid))
    user = cursor.fetchone()
    
    if not user:
        print(c("❌ Usuario no encontrado", Colors.RED))
        return
    
    user = dict(user)
    print(c("\n📋 Datos actuales:", Colors.CYAN))
    print(f"   Username: {user.get('username')}")
    print(f"   Racha actual: {user.get('current_streak')}")
    print(f"   Mejor racha: {user.get('best_streak')}")
    print(f"   Último pole: {user.get('last_pole_date')}")
    
    print(c("\n¿Qué quieres modificar?", Colors.YELLOW))
    print("   1. Racha actual")
    print("   2. Mejor racha")
    print("   3. Último pole date")
    print("   4. Username")
    print("   0. Cancelar")
    
    field_choice = input("Opción: ").strip()
    
    if field_choice == '0':
        return
    
    field_map = {
        '1': ('current_streak', 'int'),
        '2': ('best_streak', 'int'),
        '3': ('last_pole_date', 'str'),
        '4': ('username', 'str'),
    }
    
    if field_choice not in field_map:
        print(c("❌ Opción inválida", Colors.RED))
        return
    
    field_name, field_type = field_map[field_choice]
    new_value = input(f"Nuevo valor para {field_name}: ").strip()
    
    if field_type == 'int':
        try:
            new_value = int(new_value)
        except ValueError:
            print(c("❌ Debe ser un número", Colors.RED))
            return
    
    if not confirm(f"¿Confirmas cambiar {field_name} a '{new_value}'?"):
        print("Cancelado.")
        return
    
    cursor.execute(f'UPDATE users SET {field_name} = ? WHERE user_id = ? AND guild_id = ?',
                   (new_value, uid, gid))
    conn.commit()
    print(c(f"✅ {field_name} actualizado a {new_value}", Colors.GREEN))


def interactive_delete_pole(conn: sqlite3.Connection):
    """Eliminar un pole específico"""
    cursor = conn.cursor()
    
    pole_id = input("ID del pole a eliminar: ").strip()
    
    try:
        pid = int(pole_id)
    except ValueError:
        print(c("❌ ID inválido", Colors.RED))
        return
    
    # Mostrar info del pole
    cursor.execute('''
        SELECT p.*, u.username
        FROM poles p
        LEFT JOIN users u ON p.user_id = u.user_id AND p.guild_id = u.guild_id
        WHERE p.id = ?
    ''', (pid,))
    
    pole = cursor.fetchone()
    if not pole:
        print(c("❌ Pole no encontrado", Colors.RED))
        return
    
    pole = dict(pole)
    print(c("\n📋 Pole a eliminar:", Colors.YELLOW))
    print(f"   ID: {pole['id']}")
    print(f"   Usuario: {pole.get('username', 'Unknown')} (ID: {pole['user_id']})")
    print(f"   Guild: {pole['guild_id']}")
    print(f"   Fecha: {pole['user_time']}")
    print(f"   Tipo: {pole['pole_type']}")
    print(f"   Puntos: {pole['points_earned']}")
    
    if not confirm(c("⚠️  ¿ELIMINAR este pole? Esta acción NO se puede deshacer", Colors.RED)):
        print("Cancelado.")
        return
    
    # Crear backup antes
    if confirm("¿Crear backup antes de eliminar?"):
        create_backup()
    
    cursor.execute('DELETE FROM poles WHERE id = ?', (pid,))
    conn.commit()
    print(c(f"✅ Pole #{pid} eliminado", Colors.GREEN))
    print(c("⚠️  Nota: Puede que necesites ajustar manualmente season_stats y contadores de usuario", Colors.YELLOW))


def interactive_reset_streak(conn: sqlite3.Connection):
    """Resetear racha de un usuario"""
    cursor = conn.cursor()
    
    user_id = input("ID de usuario: ").strip()
    guild_id = input("ID de guild: ").strip()
    
    try:
        uid = int(user_id)
        gid = int(guild_id)
    except ValueError:
        print(c("❌ IDs inválidos", Colors.RED))
        return
    
    cursor.execute('SELECT username, current_streak FROM users WHERE user_id = ? AND guild_id = ?', (uid, gid))
    user = cursor.fetchone()
    
    if not user:
        print(c("❌ Usuario no encontrado", Colors.RED))
        return
    
    print(f"\n👤 {user[0]} tiene racha de {user[1]} días")
    
    if not confirm("¿Resetear racha a 0?"):
        print("Cancelado.")
        return
    
    cursor.execute('UPDATE users SET current_streak = 0 WHERE user_id = ? AND guild_id = ?', (uid, gid))
    conn.commit()
    print(c(f"✅ Racha de {user[0]} reseteada a 0", Colors.GREEN))


def main():
    parser = argparse.ArgumentParser(
        description="🔍 Health Check de Base de Datos - Pole Bot",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos:
  python scripts/db_health_check.py              # Modo interactivo (predeterminado)
  python scripts/db_health_check.py --check      # Solo verificar (no interactivo)
  python scripts/db_health_check.py --fix        # Verificar y reparar
  python scripts/db_health_check.py --backup     # Crear backup primero
  python scripts/db_health_check.py --user 123   # Diagnosticar usuario
        """
    )
    
    parser.add_argument('--check', action='store_true', help='Solo ejecutar health check (no interactivo)')
    parser.add_argument('--fix', action='store_true', help='Intentar reparar problemas encontrados')
    parser.add_argument('--backup', action='store_true', help='Crear backup antes de operar')
    parser.add_argument('--user', type=int, help='Diagnosticar un usuario específico por ID')
    parser.add_argument('--guild', type=int, help='Guild específico (usar con --user)')
    
    args = parser.parse_args()
    
    # Si hay argumentos específicos, ejecutar en modo no interactivo
    if args.user:
        conn = get_connection()
        diagnose_user(conn, args.user, args.guild)
        conn.close()
    elif args.check or args.fix:
        run_health_check(do_fix=args.fix, backup=args.backup)
    else:
        # Por defecto: modo interactivo
        interactive_menu()


if __name__ == "__main__":
    main()
