"""提醒计时：只负责时间和状态，不依赖宠物窗口。"""

from datetime import datetime, timedelta, timezone
from typing import Callable

from PySide6.QtCore import QObject, QTimer, Signal


class ReminderEngine(QObject):
    reminder_due = Signal()

    def __init__(
        self,
        interval_minutes: int = 55,
        snooze_minutes: int = 10,
        clock: Callable[[], datetime] | None = None,
        parent: QObject | None = None,
    ) -> None:
        super().__init__(parent)
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self.interval_minutes = interval_minutes
        self.snooze_minutes = snooze_minutes
        self.paused = False
        self.awaiting_response = False
        self.next_due_at = self._clock() + timedelta(minutes=interval_minutes)

        # 用实际截止时间判断，而不是累加 QTimer 次数：休眠后最多提醒一次。
        self._timer = QTimer(self)
        self._timer.setInterval(1000)
        self._timer.timeout.connect(self.check_due)
        self._timer.start()

    def check_due(self) -> None:
        if not self.paused and not self.awaiting_response and self._clock() >= self.next_due_at:
            self.trigger_now()

    def trigger_now(self) -> None:
        if self.paused or self.awaiting_response:
            return
        self.awaiting_response = True
        self.reminder_due.emit()

    def _schedule(self, minutes: int) -> None:
        self.awaiting_response = False
        self.next_due_at = self._clock() + timedelta(minutes=minutes)

    def mark_drunk(self) -> None:
        self._schedule(self.interval_minutes)

    def snooze(self) -> None:
        self._schedule(self.snooze_minutes)

    def pause(self) -> None:
        self.paused = True
        self.awaiting_response = False

    def resume(self) -> None:
        self.paused = False
        self._schedule(self.interval_minutes)

    def set_interval_minutes(self, minutes: int) -> None:
        if minutes <= 0:
            raise ValueError("提醒间隔必须大于 0 分钟")
        self.interval_minutes = minutes
        if not self.awaiting_response:
            self._schedule(minutes)
