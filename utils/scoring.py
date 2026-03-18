"""
Sistema de Puntuación y Rachas (v1.0 - Hora Aleatoria + Seasons)
Calcula puntos, multiplicadores, clasifica por retraso y gestiona rachas
"""
from typing import Tuple, Optional, Dict, Union
from datetime import datetime

# ==================== BADGES DE RANGO (EMOJIS CUSTOM) ====================
# Ajuste: se invirtieron Rubí y Bronce para que coincidan con el arte real
BADGE_BRONZE = "<:badge_1:1440023143283429456>"    # Bronce
BADGE_SILVER = "<:badge_2:1440023141563895930>"    # Plata
BADGE_GOLD = "<:badge_3:1440023140423041168>"      # Oro
BADGE_DIAMOND = "<:badge_4:1440023138707439708>"   # Diamante
BADGE_AMETHYST = "<:badge_5:1440023137348751370>"  # Amatista
BADGE_RUBY = "<:badge_6:1440023135524094046>"      # Rubí

# ==================== SISTEMA DE SEASONS ====================
# Configuración de temporadas
# Solo se define preseason explícitamente, las demás se generan dinámicamente
SEASON_CONFIG: Dict[str, Dict[str, Union[str, bool]]] = {
    'preseason': {
        'name': 'Pre-Temporada',
        'start_date': '2025-01-01',  # Todo 2025 es preseason
        'end_date': '2025-12-31',
        'is_ranked': False  # Pre-temporada no cuenta para rankings oficiales
    }
}

def get_season_config(year: int) -> Dict[str, Union[str, bool]]:
    """
    Obtener configuración de una temporada por año
    2025 → preseason
    2026 → season_1
    2027 → season_2
    etc.
    """
    if year == 2025:
        return SEASON_CONFIG['preseason']
    
    season_num = year - 2025  # 2026→1, 2027→2, ...
    return {
        'name': f'Temporada {season_num}',
        'start_date': f'{year}-01-01',
        'end_date': f'{year}-12-31',
        'is_ranked': True
    }

# Umbrales de rangos por season (puntos necesarios)
RANK_THRESHOLDS = {
    'bronze': 0,
    'silver': 500,
    'gold': 1500,
    'diamond': 3500,
    'amethyst': 6000,
    'ruby': 9000
}

# Nombres de rangos
RANK_NAMES = {
    'bronze': 'Bronce - Iniciado',
    'silver': 'Plata - Aspirante',
    'gold': 'Oro - Competidor',
    'diamond': 'Diamante - Veterano',
    'amethyst': 'Amatista - Maestro',
    'ruby': 'Rubí - Leyenda'
}

# Badges por rango
RANK_BADGES = {
    'bronze': BADGE_BRONZE,
    'silver': BADGE_SILVER,
    'gold': BADGE_GOLD,
    'diamond': BADGE_DIAMOND,
    'amethyst': BADGE_AMETHYST,
    'ruby': BADGE_RUBY
}

# Configuración de puntos base según categoría por retraso (v1.0)
POINTS_CONFIG = {
    'critical': 20.0,   # 0–15 min (ultra rápido)
    'fast': 15.0,       # 15 min–3h (rápido)
    'normal': 10.0,     # 3h–00:00 (mismo día)
    'marranero': 5.0    # después 00:00 (día siguiente)
}

# Cuotas por categoría: porcentaje de usuarios (sin bots) que pueden reclamar cada tipo
# Ejemplo: servidor de 100 usuarios → crítico max 10, veloz max 30
QUOTA_CONFIG: Dict[str, Dict[str, Optional[Union[int, float]]]] = {
    'critical': {
        'max_minutes': 10,      # Solo disponible primeros 10 minutos
        'max_percentage': 0.10  # Solo 10% del servidor puede reclamarlo
    },
    'fast': {
        'max_minutes': 180,     # Hasta 3 horas
        'max_percentage': 0.30  # Solo 30% del servidor puede reclamarlo
    },
    'normal': {
        'max_minutes': None,    # Sin límite de tiempo (hasta 00:00)
        'max_percentage': None  # Sin límite de usuarios
    },
    'marranero': {
        'max_minutes': None,
        'max_percentage': None
    }
}

# Multiplicadores de racha (días: multiplicador)
STREAK_MULTIPLIERS = {
    1: 1.0,
    7: 1.1,
    14: 1.2,
    21: 1.3,
    30: 1.4,
    45: 1.5,
    60: 1.6,
    75: 1.7,
    90: 1.8,
    120: 1.9,
    150: 2.0,
    180: 2.1,
    210: 2.2,
    240: 2.3,
    270: 2.4,
    300: 2.5,  # MÁXIMO
    365: 2.5   # Mantiene máximo
}

def get_streak_multiplier(streak_days: int) -> float:
    """
    Obtener el multiplicador correspondiente a los días de racha
    
    Args:
        streak_days: Días consecutivos de racha
    
    Returns:
        Multiplicador de racha (1.0 a 2.5)
    """
    if streak_days < 1:
        return 1.0
    
    # Buscar el multiplicador correspondiente
    for threshold in sorted(STREAK_MULTIPLIERS.keys(), reverse=True):
        if streak_days >= threshold:
            return STREAK_MULTIPLIERS[threshold]
    
    return 1.0

def calculate_points(pole_type: str, streak_days: int) -> Tuple[float, float, float]:
    """
    Calcular puntos totales ganados
    
    Args:
        pole_type: Tipo de pole ('critica', 'secundon', 'normal', 'marranero')
        streak_days: Días consecutivos de racha
    
    Returns:
        Tupla de (puntos_base, multiplicador, puntos_totales)
    """
    points_base = POINTS_CONFIG.get(pole_type, 0.0)
    multiplier = get_streak_multiplier(streak_days)
    points_total = points_base * multiplier
    
    return points_base, multiplier, points_total

def classify_delay(delay_minutes: int, is_next_day: bool = False) -> str:
    """
    Clasificar la categoría del pole según el retraso desde la hora de apertura.
    
    Categorías v1.0 (progresivo con cuotas limitadas):
    - critical: 0–10 min (solo 10% del servidor puede reclamarlo)
    - fast: 10 min–3h (solo 30% del servidor puede reclamarlo)
    - normal: 3h hasta 00:00 del mismo día (sin límite)
    - marranero: después de 00:00 (día siguiente, sin límite)
    
    Args:
        delay_minutes: Minutos desde la apertura
        is_next_day: Si es True, automáticamente es marranero (llegó al día siguiente)
    """
    # Si llegó al día siguiente, es marranero
    if is_next_day:
        return 'marranero'
    
    if delay_minutes < 0:
        # Devolver 'critical' por seguridad; el caller debería evitar procesar antes de abrir
        return 'critical'
    
    # Clasificar según límites de tiempo de QUOTA_CONFIG
    critical_max = QUOTA_CONFIG['critical']['max_minutes']
    fast_max = QUOTA_CONFIG['fast']['max_minutes']
    
    # Type narrowing: sabemos que critical y fast siempre tienen valores numéricos
    if critical_max is not None and delay_minutes < critical_max:
        return 'critical'
    if fast_max is not None and delay_minutes < fast_max:
        return 'fast'
    # Desde 3h hasta fin del día (00:00) es normal
    return 'normal'

def get_pole_emoji(pole_type: str) -> str:
    """
    Obtener el emoji correspondiente al tipo de pole
    
    Args:
        pole_type: Tipo de pole
    
    Returns:
        Emoji representativo
    """
    emojis = {
        'critical': '💎',
        'fast': '⚡',
        'normal': '🏁',
        'marranero': '🐷'
    }
    return emojis.get(pole_type, '🏁')

def get_pole_name(pole_type: str, guild_id: Optional[int] = None) -> str:
    """
    Obtener el nombre legible del tipo de pole
    
    Args:
        pole_type: Tipo de pole
        guild_id: ID del servidor (para traducción)
    
    Returns:
        Nombre del tipo de pole traducido
    """
    # Importar aquí para evitar circular dependency
    try:
        from utils.i18n import t
        names = {
            'critical': t('pole.type.critical', guild_id),
            'fast': t('pole.type.fast', guild_id),
            'normal': t('pole.type.normal', guild_id),
            'marranero': t('pole.type.marranero', guild_id)
        }
        return names.get(pole_type, t('pole.type.normal', guild_id))
    except:
        # Fallback si falla la importación
        names = {
            'critical': 'CRÍTICA',
            'fast': 'VELOZ',
            'normal': 'POLE',
            'marranero': 'MARRANERO'
        }
        return names.get(pole_type, 'POLE')

def check_quota_available(pole_type: str, current_count: int, active_players: int) -> Tuple[bool, int, Optional[int]]:
    """
    Verificar si aún hay cuota disponible para este tipo de pole.
    
    IMPORTANTE: Se basa en JUGADORES ACTIVOS (usuarios que han hecho pole alguna vez)
    NO en el total de miembros del servidor. Esto evita meta roto en servers grandes
    con pocos jugadores activos.
    
    Args:
        pole_type: Tipo de pole (critical, fast, normal, marranero)
        current_count: Cantidad actual de poles de este tipo reclamados hoy
        active_players: Total de jugadores activos en el servidor (han hecho pole alguna vez)
    
    Returns:
        Tupla (hay_cuota_disponible, current_count, max_allowed)
    """
    quota_config = QUOTA_CONFIG.get(pole_type, {})
    max_percentage = quota_config.get('max_percentage')
    
    # Si no hay límite de porcentaje, siempre hay cuota disponible
    if max_percentage is None:
        return (True, current_count, None)
    
    # Calcular máximo permitido basándose en jugadores ACTIVOS
    # Mínimo siempre 1 para evitar división por 0 o servers nuevos
    max_allowed = max(1, int(active_players * max_percentage))
    
    # Verificar si aún hay cupo
    has_quota = current_count < max_allowed
    
    return (has_quota, current_count, max_allowed)

def update_streak(last_pole_date: Optional[str], current_streak: int, current_date: Optional[str] = None) -> Tuple[int, bool]:
    """
    Actualizar la racha del usuario
    
    Args:
        last_pole_date: Fecha del último pole (YYYY-MM-DD) o None
        current_streak: Racha actual del usuario
    
    Returns:
        Tupla de (nueva_racha, racha_rota)
    """
    # Permitir override de la fecha efectiva del día a contabilizar (para marranero)
    today = current_date or datetime.now().strftime('%Y-%m-%d')
    
    # Si no hay pole previo, empieza racha
    if not last_pole_date:
        return 1, False
    
    # Si ya hizo pole hoy, mantiene racha
    if last_pole_date == today:
        return current_streak, False
    
    # Calcular días desde último pole
    last_date = datetime.strptime(last_pole_date, '%Y-%m-%d')
    today_date = datetime.strptime(today, '%Y-%m-%d')
    days_diff = (today_date - last_date).days
    
    # Si fue ayer, continúa racha
    if days_diff == 1:
        return current_streak + 1, False
    
    # Si fue hace más tiempo, se rompió la racha
    return 1, True

def get_rank_info(total_points: float, guild_id: Optional[int] = None) -> Tuple[str, str]:
    """
    Obtener rango e emoji según puntos totales (Sistema de Seasons)
    
    Args:
        total_points: Puntos totales del usuario en la season actual
        guild_id: ID del servidor (para traducción)
    
    Returns:
        Tupla de (badge_emoji, nombre_rango_completo)
    """
    # Importar aquí para evitar circular dependency
    try:
        from utils.i18n import t
        
        if total_points >= RANK_THRESHOLDS['ruby']:
            return RANK_BADGES['ruby'], t('rank.ruby', guild_id)
        elif total_points >= RANK_THRESHOLDS['amethyst']:
            return RANK_BADGES['amethyst'], t('rank.amethyst', guild_id)
        elif total_points >= RANK_THRESHOLDS['diamond']:
            return RANK_BADGES['diamond'], t('rank.diamond', guild_id)
        elif total_points >= RANK_THRESHOLDS['gold']:
            return RANK_BADGES['gold'], t('rank.gold', guild_id)
        elif total_points >= RANK_THRESHOLDS['silver']:
            return RANK_BADGES['silver'], t('rank.silver', guild_id)
        else:
            return RANK_BADGES['bronze'], t('rank.bronze', guild_id)
    except ImportError:
        # Fallback si falla el import
        if total_points >= RANK_THRESHOLDS['ruby']:
            return RANK_BADGES['ruby'], RANK_NAMES['ruby']
        elif total_points >= RANK_THRESHOLDS['amethyst']:
            return RANK_BADGES['amethyst'], RANK_NAMES['amethyst']
        elif total_points >= RANK_THRESHOLDS['diamond']:
            return RANK_BADGES['diamond'], RANK_NAMES['diamond']
        elif total_points >= RANK_THRESHOLDS['gold']:
            return RANK_BADGES['gold'], RANK_NAMES['gold']
        elif total_points >= RANK_THRESHOLDS['silver']:
            return RANK_BADGES['silver'], RANK_NAMES['silver']
        else:
            return RANK_BADGES['bronze'], RANK_NAMES['bronze']

def get_current_season(db_path: str = "data/pole_bot.db") -> str:
    """
    Detectar la season actual basándose en el AÑO ACTUAL
    
    La temporada se determina por el año, NO por lo que esté en la BD.
    Esto evita que una migración fallida bloquee el sistema.
    
    Returns:
        ID de la season actual ('preseason', 'season_1', 'season_2', etc.)
    """
    # Calcular por año actual (SIEMPRE)
    year = datetime.now().year
    
    if year == 2025:
        return 'preseason'
    else:
        season_num = year - 2025  # 2026→1, 2027→2, ...
        return f'season_{season_num}'

def get_season_info(season_id: Optional[str] = None) -> Dict[str, Union[str, bool]]:
    """
    Obtener información de una season
    
    Args:
        season_id: ID de la season (si es None, usa la actual)
    
    Returns:
        Dict con info de la season (id, name, start_date, end_date, is_ranked)
    """
    if season_id is None:
        season_id = get_current_season()
    
    # Si es preseason, usar config estático
    if season_id == 'preseason':
        return {
            'id': season_id,
            **SEASON_CONFIG['preseason']
        }
    
    # Si es season_N, generar dinámicamente
    if season_id.startswith('season_'):
        try:
            season_num = int(season_id.split('_')[1])
            year = 2025 + season_num  # season_1→2026, season_2→2027
            return {
                'id': season_id,
                'name': f'Temporada {year}',
                'start_date': f'{year}-01-01',
                'end_date': f'{year}-12-31',
                'is_ranked': True
            }
        except (IndexError, ValueError):
            pass
    
    # Si es un año numérico (ej: "2026"), convertir a season_N
    try:
        year = int(season_id)
        if year >= 2026:
            season_num = year - 2025
            return {
                'id': f'season_{season_num}',
                'name': f'Temporada {year}',
                'start_date': f'{year}-01-01',
                'end_date': f'{year}-12-31',
                'is_ranked': True
            }
        elif year == 2025:
            return get_season_info('preseason')
    except (ValueError, TypeError):
        pass
    
    # Fallback: Error en vez de devolver basura
    raise ValueError(
        f"❌ season_id inválido: '{season_id}'. "
        f"Usa 'preseason', 'season_1', 'season_2', etc., o un año numérico (2026, 2027...)"
    )
