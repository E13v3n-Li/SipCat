"""本地记录：用 SQLite 保存喝水时间、提醒间隔和宠物名字。"""

import sys
import sqlite3
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

from PySide6.QtCore import QStandardPaths


def default_database_path() -> Path:
    base = (
        Path(sys.executable).resolve().parent
        if getattr(sys, "frozen", False)
        else Path(__file__).resolve().parent
    )
    return base / "data" / "sipcat.sqlite3"


def database_path_for_app(app_data_dir: Path) -> Path:
    """优先使用新版目录；旧版用户继续读取原数据库，不丢失记录。"""
    current = app_data_dir / "sipcat.sqlite3"
    legacy = app_data_dir.parent / "水滴伙伴" / "water_pet.sqlite3"
    return legacy if legacy.is_file() and not current.exists() else current


class DrinkStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or default_database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as database:
            database.execute(
                "CREATE TABLE IF NOT EXISTS drinks ("
                "id INTEGER PRIMARY KEY, occurred_at TEXT NOT NULL)"
            )
            database.execute(
                "CREATE TABLE IF NOT EXISTS settings ("
                "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )

    def record_drink(self, at: datetime | None = None) -> datetime:
        """每次确认喝水，记录一个带时区的本地时间。"""
        moment = at or datetime.now().astimezone()
        if moment.tzinfo is None:
            raise ValueError("记录时间必须包含时区")
        with sqlite3.connect(self.path) as database:
            database.execute(
                "INSERT INTO drinks (occurred_at) VALUES (?)",
                (moment.isoformat(timespec="seconds"),),
            )
        return moment

    def today_records(self, day: date | None = None) -> list[datetime]:
        """按电脑当前时区筛选今天的记录，并按时间排序。"""
        local_day = day or datetime.now().astimezone().date()
        return [moment for moment in self._all_records() if moment.date() == local_day]

    def _all_records(self) -> list[datetime]:
        with sqlite3.connect(self.path) as database:
            rows = database.execute("SELECT occurred_at FROM drinks ORDER BY occurred_at").fetchall()
        return sorted(datetime.fromisoformat(row[0]).astimezone() for row in rows)

    def weekly_counts(self, today: date | None = None) -> list[tuple[date, int]]:
        """最近七个本地日期的喝水记录次数，包含今天。"""
        current = today or datetime.now().astimezone().date()
        counts = Counter(moment.date() for moment in self._all_records())
        return [
            (day, counts[day])
            for day in (current - timedelta(days=offset) for offset in range(6, -1, -1))
        ]

    def load_interval(self) -> int:
        with sqlite3.connect(self.path) as database:
            row = database.execute(
                "SELECT value FROM settings WHERE key = 'interval_minutes'"
            ).fetchone()
        try:
            interval = int(row[0]) if row else 55
        except ValueError:
            return 55
        return interval if interval in (50, 55, 60) else 55

    def save_interval(self, minutes: int) -> None:
        if minutes not in (50, 55, 60):
            raise ValueError("提醒间隔只能是 50、55 或 60 分钟")
        with sqlite3.connect(self.path) as database:
            database.execute(
                "INSERT INTO settings (key, value) VALUES ('interval_minutes', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (str(minutes),),
            )

    def load_name(self) -> str:
        with sqlite3.connect(self.path) as database:
            row = database.execute(
                "SELECT value FROM settings WHERE key = 'pet_name'"
            ).fetchone()
        name = row[0].strip() if row else ""
        return name if name else "SipCat"

    def save_name(self, name: str) -> str:
        clean_name = name.strip()
        if not clean_name or len(clean_name) > 20:
            raise ValueError("名字需要 1–20 个字符")
        with sqlite3.connect(self.path) as database:
            database.execute(
                "INSERT INTO settings (key, value) VALUES ('pet_name', ?) "
                "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                (clean_name,),
            )
        return clean_name
