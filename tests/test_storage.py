"""验证本地记录跨重启保存，且今日统计不会混入昨天。"""

import sys
import tempfile
import unittest
from datetime import datetime, time, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from storage import DrinkStore, database_path_for_app


class StorageTests(unittest.TestCase):
    def test_records_and_interval_survive_reopening(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "water_pet.sqlite3"
            store = DrinkStore(path)
            now = datetime.now().astimezone()
            yesterday = datetime.combine(now.date() - timedelta(days=1), time(12), now.tzinfo)
            store.record_drink(yesterday)
            store.record_drink(now)
            store.save_interval(60)
            store.save_name(" 小墨 ")

            reopened = DrinkStore(path)
            self.assertEqual(reopened.load_interval(), 60)
            self.assertEqual(reopened.load_name(), "小墨")
            self.assertEqual(len(reopened.today_records(now.date())), 1)
            self.assertEqual(reopened.today_records(now.date())[0].date(), now.date())
            self.assertEqual([count for _, count in reopened.weekly_counts(now.date())][-2:], [1, 1])

    def test_blank_name_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = DrinkStore(Path(directory) / "water_pet.sqlite3")
            with self.assertRaises(ValueError):
                store.save_name("   ")
            self.assertEqual(store.load_name(), "SipCat")

    def test_existing_database_remains_available_after_rename(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            old_path = base / "水滴伙伴" / "water_pet.sqlite3"
            old_store = DrinkStore(old_path)
            old_store.save_name("小墨")
            self.assertEqual(database_path_for_app(base / "SipCat"), old_path)
            self.assertEqual(DrinkStore(database_path_for_app(base / "SipCat")).load_name(), "小墨")
            new_path = base / "SipCat" / "sipcat.sqlite3"
            DrinkStore(new_path)
            self.assertEqual(database_path_for_app(base / "SipCat"), new_path)


if __name__ == "__main__":
    unittest.main()
