"""用可控制的时钟验证休眠与暂停后的提醒行为。"""

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PySide6.QtCore import QCoreApplication

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reminder import ReminderEngine


class ReminderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def setUp(self) -> None:
        self.now = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)
        self.engine = ReminderEngine(clock=lambda: self.now)
        self.fired = []
        self.engine.reminder_due.connect(lambda: self.fired.append(self.now))

    def tearDown(self) -> None:
        self.engine._timer.stop()

    def test_waking_from_long_sleep_does_not_stack_reminders(self) -> None:
        self.now += timedelta(hours=3)
        self.engine.check_due()
        self.engine.check_due()
        self.assertEqual(len(self.fired), 1)
        self.engine.mark_drunk()
        self.assertEqual(self.engine.next_due_at, self.now + timedelta(minutes=55))

    def test_snooze_and_pause(self) -> None:
        self.engine.trigger_now()
        self.engine.snooze()
        self.now += timedelta(minutes=9)
        self.engine.check_due()
        self.assertEqual(len(self.fired), 1)
        self.now += timedelta(minutes=1)
        self.engine.check_due()
        self.assertEqual(len(self.fired), 2)
        self.engine.pause()
        self.now += timedelta(hours=2)
        self.engine.check_due()
        self.assertEqual(len(self.fired), 2)
        self.engine.resume()
        self.assertEqual(self.engine.next_due_at, self.now + timedelta(minutes=55))


if __name__ == "__main__":
    unittest.main()
