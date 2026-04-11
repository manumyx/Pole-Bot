"""
Central scheduler for Pole-Bot using APScheduler.

Phase 1 responsibilities:
- Fixed cron job at 00:00:00 Europe/Madrid.
- Midnight rollover flow:
  1) send previous-day summary (mockable callback),
  2) close pole and move to marranero window,
  3) generate random opening time for each guild,
  4) schedule dynamic opening jobs.
- Dynamic one-shot job per guild to open the pole at the generated time.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Awaitable, Callable, Optional, TYPE_CHECKING

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger

from utils.database import LOCAL_TZ

if TYPE_CHECKING:
    from utils.database import Database


SummaryCallback = Callable[[int, str], Awaitable[None]]
PhaseCallback = Callable[[int, datetime], Awaitable[None]]


class PolePhase(str, Enum):
    CERRADA_ESPERANDO_APERTURA = "CERRADA_ESPERANDO_APERTURA"
    ABIERTA_JUGANDO = "ABIERTA_JUGANDO"


@dataclass(frozen=True)
class ServerScheduleConfig:
    guild_id: int
    pole_range_start: int
    pole_range_end: int
    daily_pole_time: Optional[str]
    last_daily_pole_time: Optional[str]


class PoleScheduler:
    MIDNIGHT_JOB_ID = "pole:midnight-rollover"
    OPEN_JOB_PREFIX = "pole:open"

    def __init__(
        self,
        db: Database,
        on_send_summary: Optional[SummaryCallback] = None,
        on_close_for_marranero: Optional[PhaseCallback] = None,
        on_open_pole: Optional[PhaseCallback] = None,
        minimum_gap_hours: int = 4,
        random_seed: Optional[int] = None,
    ) -> None:
        self._db = db
        self._log = logging.getLogger("PoleScheduler")
        self._scheduler = AsyncIOScheduler(
            timezone=LOCAL_TZ,
            job_defaults={
                "coalesce": True,
                "max_instances": 1,
                "misfire_grace_time": 3600,
            },
        )
        self._on_send_summary = on_send_summary or self._noop_send_summary
        self._on_close_for_marranero = on_close_for_marranero
        self._on_open_pole = on_open_pole
        self._minimum_gap_hours = max(0, minimum_gap_hours)
        self._random = random.Random(random_seed)
        self._phase_by_guild: dict[int, PolePhase] = {}

    async def start(self) -> None:
        if not self._scheduler.running:
            self._scheduler.add_job(
                self._run_midnight_rollover,
                trigger=CronTrigger(hour=0, minute=0, second=0, timezone=LOCAL_TZ),
                id=self.MIDNIGHT_JOB_ID,
                replace_existing=True,
            )
            self._scheduler.start()
            self._log.info("Scheduler started with strict 00:00:00 Europe/Madrid cron")

        await self.bootstrap_today()

    async def shutdown(self, wait: bool = True) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=wait)
            self._log.info("Scheduler stopped")

    async def bootstrap_today(self) -> None:
        now = datetime.now(LOCAL_TZ)
        today = now.date()

        self._clear_open_jobs()
        configs = await self._fetch_server_configs()

        for cfg in configs:
            if not cfg.daily_pole_time:
                self._phase_by_guild[cfg.guild_id] = PolePhase.CERRADA_ESPERANDO_APERTURA
                continue

            try:
                opening_dt = self._local_datetime_for_time(today, cfg.daily_pole_time)
            except ValueError as exc:
                self._phase_by_guild[cfg.guild_id] = PolePhase.CERRADA_ESPERANDO_APERTURA
                self._log.warning(
                    "Invalid daily_pole_time for guild %s (%s): %s",
                    cfg.guild_id,
                    cfg.daily_pole_time,
                    exc,
                )
                continue

            if now < opening_dt:
                self._phase_by_guild[cfg.guild_id] = PolePhase.CERRADA_ESPERANDO_APERTURA
                self._schedule_opening_job(cfg.guild_id, opening_dt)
            else:
                self._phase_by_guild[cfg.guild_id] = PolePhase.ABIERTA_JUGANDO

    def get_phase(self, guild_id: int) -> PolePhase:
        return self._phase_by_guild.get(guild_id, PolePhase.CERRADA_ESPERANDO_APERTURA)

    async def run_midnight_rollover_now(self) -> None:
        await self._run_midnight_rollover()

    async def _run_midnight_rollover(self) -> None:
        now = datetime.now(LOCAL_TZ)
        summary_date = (now - timedelta(days=1)).date().isoformat()
        target_date = now.date()

        configs = await self._fetch_server_configs()
        if not configs:
            self._log.debug("No configured guilds found for midnight rollover")
            return

        self._clear_open_jobs()

        for cfg in configs:
            guild_id = cfg.guild_id

            try:
                await self._on_send_summary(guild_id, summary_date)
            except Exception:
                self._log.exception(
                    "Error sending previous-day summary for guild %s", guild_id
                )

            self._phase_by_guild[guild_id] = PolePhase.CERRADA_ESPERANDO_APERTURA

            if self._on_close_for_marranero is not None:
                try:
                    await self._on_close_for_marranero(guild_id, now)
                except Exception:
                    self._log.exception(
                        "Error closing pole at midnight for guild %s", guild_id
                    )

        for cfg in configs:
            guild_id = cfg.guild_id
            try:
                opening_dt = self._generate_opening_datetime(cfg, target_date)

                await self._db.set_daily_pole_time(
                    guild_id, opening_dt.strftime("%H:%M:%S")
                )
                await self._db.clear_notification_sent_at(guild_id)

                self._schedule_opening_job(guild_id, opening_dt)
                self._log.info(
                    "Scheduled opening for guild %s at %s",
                    guild_id,
                    opening_dt.isoformat(),
                )
            except Exception:
                self._log.exception(
                    "Error generating/scheduling opening for guild %s", guild_id
                )

    async def _run_opening_job(self, guild_id: int, opening_iso: str) -> None:
        opening_dt = self._ensure_local_tz(datetime.fromisoformat(opening_iso))
        self._phase_by_guild[guild_id] = PolePhase.ABIERTA_JUGANDO

        if self._on_open_pole is None:
            return

        try:
            await self._on_open_pole(guild_id, opening_dt)
        except Exception:
            self._log.exception("Error opening pole for guild %s", guild_id)

    def _schedule_opening_job(self, guild_id: int, opening_dt: datetime) -> None:
        opening_local = self._ensure_local_tz(opening_dt)
        job_id = self._build_open_job_id(guild_id, opening_local.date().isoformat())

        self._scheduler.add_job(
            self._run_opening_job,
            trigger=DateTrigger(run_date=opening_local, timezone=LOCAL_TZ),
            args=[guild_id, opening_local.isoformat()],
            id=job_id,
            replace_existing=True,
            coalesce=True,
            max_instances=1,
            misfire_grace_time=1800,
        )

    def _clear_open_jobs(self) -> None:
        for job in list(self._scheduler.get_jobs()):
            if job.id.startswith(self.OPEN_JOB_PREFIX):
                self._scheduler.remove_job(job.id)

    def _build_open_job_id(self, guild_id: int, date_str: str) -> str:
        return f"{self.OPEN_JOB_PREFIX}:{guild_id}:{date_str}"

    async def _fetch_server_configs(self) -> list[ServerScheduleConfig]:
        async with self._db.get_connection() as conn:
            cursor = await conn.execute(
                """
                SELECT guild_id, pole_range_start, pole_range_end,
                       daily_pole_time, last_daily_pole_time
                FROM servers
                WHERE pole_channel_id IS NOT NULL
                """
            )
            rows = await cursor.fetchall()

        configs: list[ServerScheduleConfig] = []
        for row in rows:
            start = self._normalize_hour(row["pole_range_start"], default=8)
            end = self._normalize_hour(row["pole_range_end"], default=20)
            configs.append(
                ServerScheduleConfig(
                    guild_id=int(row["guild_id"]),
                    pole_range_start=start,
                    pole_range_end=end,
                    daily_pole_time=row["daily_pole_time"],
                    last_daily_pole_time=row["last_daily_pole_time"],
                )
            )
        return configs

    def _generate_opening_datetime(
        self, cfg: ServerScheduleConfig, target_date: date
    ) -> datetime:
        last_opening_dt: Optional[datetime] = None
        if cfg.last_daily_pole_time:
            try:
                yesterday = target_date - timedelta(days=1)
                last_opening_dt = self._local_datetime_for_time(
                    yesterday, cfg.last_daily_pole_time
                )
            except ValueError as exc:
                self._log.warning(
                    "Invalid last_daily_pole_time for guild %s (%s): %s",
                    cfg.guild_id,
                    cfg.last_daily_pole_time,
                    exc,
                )

        best_candidate = self._pick_random_opening(cfg, target_date)

        if last_opening_dt is None or self._minimum_gap_hours == 0:
            return best_candidate

        minimum_gap_seconds = float(self._minimum_gap_hours * 3600)
        best_gap_seconds = (best_candidate - last_opening_dt).total_seconds()

        for _ in range(63):
            candidate = self._pick_random_opening(cfg, target_date)
            gap_seconds = (candidate - last_opening_dt).total_seconds()

            if gap_seconds > best_gap_seconds:
                best_candidate = candidate
                best_gap_seconds = gap_seconds

            if gap_seconds >= minimum_gap_seconds:
                return candidate

        self._log.warning(
            "Guild %s: no candidate met %sh minimum gap, using best available",
            cfg.guild_id,
            self._minimum_gap_hours,
        )
        return best_candidate

    def _pick_random_opening(self, cfg: ServerScheduleConfig, target_date: date) -> datetime:
        minute_of_day = self._pick_random_minute_of_day(
            cfg.pole_range_start,
            cfg.pole_range_end,
        )
        hour, minute = divmod(minute_of_day, 60)
        return datetime(
            target_date.year,
            target_date.month,
            target_date.day,
            hour,
            minute,
            0,
            tzinfo=LOCAL_TZ,
        )

    def _pick_random_minute_of_day(self, start_hour: int, end_hour: int) -> int:
        start_minute = start_hour * 60
        end_minute = end_hour * 60 + 59

        if start_hour <= end_hour:
            return self._random.randint(start_minute, end_minute)

        # Wrapped range, for example 20:00 -> 04:59.
        first_window_size = 1440 - start_minute
        second_window_size = end_minute + 1
        pick = self._random.randrange(first_window_size + second_window_size)

        if pick < first_window_size:
            return start_minute + pick
        return pick - first_window_size

    def _local_datetime_for_time(self, target_date: date, time_str: str) -> datetime:
        hour, minute, second = self._parse_hms(time_str)
        return datetime(
            target_date.year,
            target_date.month,
            target_date.day,
            hour,
            minute,
            second,
            tzinfo=LOCAL_TZ,
        )

    @staticmethod
    def _parse_hms(time_str: str) -> tuple[int, int, int]:
        parts = [part.strip() for part in time_str.split(":")]
        if len(parts) not in (2, 3):
            raise ValueError("expected HH:MM or HH:MM:SS")

        hour = int(parts[0])
        minute = int(parts[1])
        second = int(parts[2]) if len(parts) == 3 else 0

        if not 0 <= hour <= 23:
            raise ValueError("hour out of range")
        if not 0 <= minute <= 59:
            raise ValueError("minute out of range")
        if not 0 <= second <= 59:
            raise ValueError("second out of range")

        return hour, minute, second

    @staticmethod
    def _normalize_hour(value: object, default: int) -> int:
        try:
            hour = int(value)
        except (TypeError, ValueError):
            return default

        return min(23, max(0, hour))

    @staticmethod
    def _ensure_local_tz(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=LOCAL_TZ)
        return value.astimezone(LOCAL_TZ)

    async def _noop_send_summary(self, guild_id: int, summary_date: str) -> None:
        _ = guild_id
        _ = summary_date
