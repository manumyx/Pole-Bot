"""
Restaurar rachas globales sin modificar puntos.

Uso seguro:
- Dry-run por defecto (no escribe en la base de datos).
- Con --apply: crea backup y aplica cambios en global_users.

Politica por defecto (forgiving):
- Si el usuario tenia actividad antes del inicio de temporada:
  la racha arranca en start_date de la temporada.
- Si no tenia actividad previa:
  la racha arranca en su primer pole de temporada.
"""

import argparse
import asyncio
import shutil
import sys
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from zoneinfo import ZoneInfo

import aiosqlite


LOCAL_TZ = ZoneInfo("Europe/Madrid")


@dataclass
class SeasonWindow:
    season_id: str
    start_date: date
    end_date: Optional[date]


@dataclass
class GlobalUserState:
    user_id: int
    username: str
    current_streak: int
    best_streak: int
    last_pole_date: Optional[date]
    exists: bool


@dataclass
class UserChange:
    user_id: int
    username: str
    exists: bool
    had_preseason_activity: bool
    season_anchor_date: date
    season_last_pole_date: date
    season_days_with_pole: int
    expected_current_at_last_pole: int
    expected_current_streak: int
    expected_best_streak: int
    old_current_streak: int
    old_best_streak: int
    old_last_pole_date: Optional[date]
    new_current_streak: int
    new_best_streak: int
    new_last_pole_date: date


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Restaura rachas globales en global_users sin tocar puntos."
    )
    parser.add_argument(
        "--db",
        default="data/pole_bot.db",
        help="Ruta a la base de datos SQLite (default: data/pole_bot.db)",
    )
    parser.add_argument(
        "--season-id",
        default=None,
        help="Temporada objetivo (por defecto, temporada activa)",
    )
    parser.add_argument(
        "--mode",
        choices=["forgiving", "strict"],
        default="forgiving",
        help=(
            "forgiving: restaura contando dias desde ancla de temporada/jugador; "
            "strict: recalcula solo por dias consecutivos registrados"
        ),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Aplica cambios en DB. Si no se indica, ejecuta dry-run.",
    )
    parser.add_argument(
        "--allow-decrease",
        action="store_true",
        help="Permite bajar current_streak cuando el recalculo sea menor.",
    )
    parser.add_argument(
        "--rebuild-best",
        action="store_true",
        help="Recalcula best_streak con la racha esperada de temporada.",
    )
    parser.add_argument(
        "--user-id",
        action="append",
        type=int,
        default=None,
        help="Limitar a un user_id concreto. Se puede repetir.",
    )
    parser.add_argument(
        "--max-preview",
        type=int,
        default=50,
        help="Numero maximo de cambios mostrados en la previsualizacion.",
    )
    parser.add_argument(
        "--show-all",
        action="store_true",
        help="Mostrar tambien usuarios sin cambio final.",
    )
    return parser.parse_args()


def parse_db_date(raw_value: Optional[str]) -> Optional[date]:
    if raw_value is None:
        return None

    text = str(raw_value).strip()
    if not text:
        return None

    # Tolerar tanto YYYY-MM-DD como datetime ISO.
    try:
        return date.fromisoformat(text[:10])
    except ValueError:
        return None


def format_date(value: Optional[date]) -> str:
    return value.isoformat() if value else "None"


def build_in_clause(values: Iterable[int]) -> str:
    return ",".join("?" for _ in values)


async def fetch_season_window(conn: aiosqlite.Connection, season_id: Optional[str]) -> SeasonWindow:
    if season_id:
        cursor = await conn.execute(
            """
            SELECT season_id, start_date, end_date
            FROM seasons
            WHERE season_id = ?
            LIMIT 1
            """,
            (season_id,),
        )
    else:
        cursor = await conn.execute(
            """
            SELECT season_id, start_date, end_date
            FROM seasons
            WHERE is_active = 1
            ORDER BY start_date DESC
            LIMIT 1
            """
        )

    row = await cursor.fetchone()
    if not row:
        requested = season_id if season_id else "temporada activa"
        raise RuntimeError(f"No se encontro {requested} en tabla seasons")

    start = parse_db_date(row["start_date"])
    if not start:
        raise RuntimeError(f"start_date invalida en season {row['season_id']}")

    end = parse_db_date(row["end_date"])
    return SeasonWindow(season_id=row["season_id"], start_date=start, end_date=end)


async def fetch_activity_dates(
    conn: aiosqlite.Connection,
    target_user_ids: Optional[List[int]],
) -> Dict[int, List[date]]:
    params: List[object] = []
    where = "WHERE COALESCE(pole_date, DATE(user_time)) IS NOT NULL"

    if target_user_ids:
        in_clause = build_in_clause(target_user_ids)
        where += f" AND user_id IN ({in_clause})"
        params.extend(target_user_ids)

    cursor = await conn.execute(
        f"""
        SELECT user_id, COALESCE(pole_date, DATE(user_time)) AS effective_date
        FROM poles
        {where}
        ORDER BY user_id, effective_date
        """,
        tuple(params),
    )
    rows = await cursor.fetchall()

    grouped: Dict[int, List[date]] = defaultdict(list)
    for row in rows:
        parsed = parse_db_date(row["effective_date"])
        if parsed:
            grouped[int(row["user_id"])].append(parsed)

    # Dedupe por fecha efectiva para no contar duplicados de la misma fecha.
    deduped: Dict[int, List[date]] = {}
    for user_id, dates in grouped.items():
        deduped[user_id] = sorted(set(dates))

    return deduped


async def fetch_global_user_states(
    conn: aiosqlite.Connection,
    target_user_ids: Optional[List[int]],
) -> Dict[int, GlobalUserState]:
    params: List[object] = []
    where = ""

    if target_user_ids:
        in_clause = build_in_clause(target_user_ids)
        where = f"WHERE user_id IN ({in_clause})"
        params.extend(target_user_ids)

    cursor = await conn.execute(
        f"""
        SELECT user_id, username, current_streak, best_streak, last_pole_date
        FROM global_users
        {where}
        """,
        tuple(params),
    )
    rows = await cursor.fetchall()

    states: Dict[int, GlobalUserState] = {}
    for row in rows:
        user_id = int(row["user_id"])
        states[user_id] = GlobalUserState(
            user_id=user_id,
            username=str(row["username"] or f"user_{user_id}"),
            current_streak=int(row["current_streak"] or 0),
            best_streak=int(row["best_streak"] or 0),
            last_pole_date=parse_db_date(row["last_pole_date"]),
            exists=True,
        )

    return states


async def fetch_usernames_from_users(
    conn: aiosqlite.Connection,
    target_user_ids: Optional[List[int]],
) -> Dict[int, str]:
    params: List[object] = []
    where = ""

    if target_user_ids:
        in_clause = build_in_clause(target_user_ids)
        where = f"WHERE user_id IN ({in_clause})"
        params.extend(target_user_ids)

    cursor = await conn.execute(
        f"""
        SELECT user_id, MAX(username) AS username
        FROM users
        {where}
        GROUP BY user_id
        """,
        tuple(params),
    )
    rows = await cursor.fetchall()

    return {int(row["user_id"]): str(row["username"] or f"user_{int(row['user_id'])}") for row in rows}


def compute_strict_streak(dates: List[date]) -> tuple[int, int]:
    if not dates:
        return 0, 0

    run = 0
    best = 0
    prev: Optional[date] = None

    for value in dates:
        if prev and value == (prev.fromordinal(prev.toordinal() + 1)):
            run += 1
        else:
            run = 1
        best = max(best, run)
        prev = value

    return run, best


def compute_changes(
    *,
    activity_dates: Dict[int, List[date]],
    global_states: Dict[int, GlobalUserState],
    usernames: Dict[int, str],
    season_window: SeasonWindow,
    mode: str,
    allow_decrease: bool,
    rebuild_best: bool,
) -> List[UserChange]:
    changes: List[UserChange] = []
    season_end = season_window.end_date
    today = datetime.now(LOCAL_TZ).date()

    for user_id, all_dates in activity_dates.items():
        in_season_dates = [
            value
            for value in all_dates
            if value >= season_window.start_date and (season_end is None or value <= season_end)
        ]
        if not in_season_dates:
            continue

        had_preseason_activity = any(value < season_window.start_date for value in all_dates)
        season_last_date = in_season_dates[-1]

        if mode == "forgiving":
            season_anchor_date = season_window.start_date if had_preseason_activity else in_season_dates[0]
            expected_current_at_last_pole = (season_last_date - season_anchor_date).days + 1
            expected_best_streak = expected_current_at_last_pole
        else:
            season_anchor_date = in_season_dates[0]
            expected_current_at_last_pole, expected_best_streak = compute_strict_streak(in_season_dates)

        # La racha "actual" solo puede estar viva si el ultimo pole fue hoy o ayer.
        if season_last_date >= (today - timedelta(days=1)):
            expected_current_streak = expected_current_at_last_pole
        else:
            expected_current_streak = 0

        state = global_states.get(user_id)
        if not state:
            state = GlobalUserState(
                user_id=user_id,
                username=usernames.get(user_id, f"user_{user_id}"),
                current_streak=0,
                best_streak=0,
                last_pole_date=None,
                exists=False,
            )

        old_last = state.last_pole_date
        if old_last and old_last > season_last_date:
            new_last = old_last
        else:
            new_last = season_last_date

        if allow_decrease:
            new_current = expected_current_streak
        else:
            new_current = max(state.current_streak, expected_current_streak)

        if rebuild_best:
            new_best = max(state.best_streak, expected_best_streak, new_current)
        else:
            # Modo conservador: no reescribe historial completo de best_streak.
            new_best = max(state.best_streak, new_current)

        username = state.username or usernames.get(user_id, f"user_{user_id}")
        changes.append(
            UserChange(
                user_id=user_id,
                username=username,
                exists=state.exists,
                had_preseason_activity=had_preseason_activity,
                season_anchor_date=season_anchor_date,
                season_last_pole_date=season_last_date,
                season_days_with_pole=len(in_season_dates),
                expected_current_at_last_pole=expected_current_at_last_pole,
                expected_current_streak=expected_current_streak,
                expected_best_streak=expected_best_streak,
                old_current_streak=state.current_streak,
                old_best_streak=state.best_streak,
                old_last_pole_date=state.last_pole_date,
                new_current_streak=new_current,
                new_best_streak=new_best,
                new_last_pole_date=new_last,
            )
        )

    return changes


def is_changed(item: UserChange) -> bool:
    return any(
        [
            item.old_current_streak != item.new_current_streak,
            item.old_best_streak != item.new_best_streak,
            item.old_last_pole_date != item.new_last_pole_date,
            not item.exists,
        ]
    )


def ensure_backup(db_path: Path) -> Path:
    backups_dir = db_path.parent / "backups"
    backups_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now(LOCAL_TZ).strftime("%Y%m%d_%H%M%S")
    backup_path = backups_dir / f"{db_path.stem}_streak_restore_{timestamp}{db_path.suffix}"
    shutil.copy2(db_path, backup_path)
    return backup_path


async def apply_changes(conn: aiosqlite.Connection, items: List[UserChange]) -> None:
    now_iso = datetime.now(LOCAL_TZ).isoformat()

    try:
        await conn.execute("BEGIN IMMEDIATE")

        for item in items:
            if item.exists:
                await conn.execute(
                    """
                    UPDATE global_users
                    SET username = ?,
                        current_streak = ?,
                        best_streak = ?,
                        last_pole_date = ?,
                        updated_at = ?
                    WHERE user_id = ?
                    """,
                    (
                        item.username,
                        item.new_current_streak,
                        item.new_best_streak,
                        item.new_last_pole_date.isoformat(),
                        now_iso,
                        item.user_id,
                    ),
                )
            else:
                await conn.execute(
                    """
                    INSERT INTO global_users (
                        user_id, username, current_streak, best_streak,
                        last_pole_date, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item.user_id,
                        item.username,
                        item.new_current_streak,
                        item.new_best_streak,
                        item.new_last_pole_date.isoformat(),
                        now_iso,
                    ),
                )

        await conn.commit()
    except Exception:
        await conn.rollback()
        raise


def print_report(
    *,
    season_window: SeasonWindow,
    mode: str,
    apply_mode: bool,
    allow_decrease: bool,
    rebuild_best: bool,
    all_items: List[UserChange],
    changed_items: List[UserChange],
    max_preview: int,
    show_all: bool,
) -> None:
    print("=" * 80)
    print("RESTORE STREAKS REPORT")
    print("=" * 80)
    print(f"Season: {season_window.season_id} ({season_window.start_date} -> {season_window.end_date})")
    print(f"Mode: {mode}")
    print(f"Execution: {'APPLY' if apply_mode else 'DRY-RUN'}")
    print(f"Allow decrease: {allow_decrease}")
    print(f"Rebuild best: {rebuild_best}")
    print(f"Users with season activity: {len(all_items)}")
    print(f"Users with effective changes: {len(changed_items)}")

    if not all_items:
        print("No hay usuarios con actividad en la temporada seleccionada.")
        return

    preview_items = all_items if show_all else changed_items
    preview_items = sorted(
        preview_items,
        key=lambda item: (
            (item.new_current_streak - item.old_current_streak),
            item.user_id,
        ),
        reverse=True,
    )

    if not preview_items:
        print("No hay cambios para aplicar.")
        return

    print("-" * 80)
    print("Preview:")

    for item in preview_items[:max_preview]:
        current_delta = item.new_current_streak - item.old_current_streak
        best_delta = item.new_best_streak - item.old_best_streak
        preseason_text = "yes" if item.had_preseason_activity else "no"
        print(
            "  "
            f"user={item.user_id} ({item.username}) "
            f"current {item.old_current_streak}->{item.new_current_streak} ({current_delta:+d}) "
            f"calc_now={item.expected_current_streak} "
            f"calc_last={item.expected_current_at_last_pole} "
            f"best {item.old_best_streak}->{item.new_best_streak} ({best_delta:+d}) "
            f"last {format_date(item.old_last_pole_date)}->{format_date(item.new_last_pole_date)} "
            f"anchor={item.season_anchor_date} "
            f"season_days={item.season_days_with_pole} "
            f"preseason={preseason_text}"
        )

    remaining = len(preview_items) - max_preview
    if remaining > 0:
        print(f"... y {remaining} usuario(s) mas")


async def run() -> int:
    args = parse_args()
    db_path = Path(args.db).resolve()

    if not db_path.exists():
        print(f"ERROR: No existe la DB en {db_path}")
        return 1

    backup_path: Optional[Path] = None
    if args.apply:
        backup_path = ensure_backup(db_path)

    async with aiosqlite.connect(db_path, timeout=30.0) as conn:
        conn.row_factory = aiosqlite.Row
        await conn.execute("PRAGMA foreign_keys = ON")
        await conn.execute("PRAGMA journal_mode = WAL")

        season_window = await fetch_season_window(conn, args.season_id)
        activity_dates = await fetch_activity_dates(conn, args.user_id)
        global_states = await fetch_global_user_states(conn, args.user_id)
        usernames = await fetch_usernames_from_users(conn, args.user_id)

        all_items = compute_changes(
            activity_dates=activity_dates,
            global_states=global_states,
            usernames=usernames,
            season_window=season_window,
            mode=args.mode,
            allow_decrease=args.allow_decrease,
            rebuild_best=args.rebuild_best,
        )
        changed_items = [item for item in all_items if is_changed(item)]

        print_report(
            season_window=season_window,
            mode=args.mode,
            apply_mode=args.apply,
            allow_decrease=args.allow_decrease,
            rebuild_best=args.rebuild_best,
            all_items=all_items,
            changed_items=changed_items,
            max_preview=args.max_preview,
            show_all=args.show_all,
        )

        if args.apply and changed_items:
            await apply_changes(conn, changed_items)
            print("-" * 80)
            print(f"Cambios aplicados en global_users: {len(changed_items)} usuario(s)")
            if backup_path:
                print(f"Backup: {backup_path}")
        elif args.apply and not changed_items:
            print("No hay cambios para aplicar.")
            if backup_path:
                print(f"Backup creado igualmente: {backup_path}")
        else:
            print("Dry-run completado. Para aplicar, ejecuta con --apply.")
            if backup_path:
                print(f"Backup: {backup_path}")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(asyncio.run(run()))
    except KeyboardInterrupt:
        print("Interrumpido por usuario")
        raise SystemExit(130)