"""可点击的喝水提醒气泡。"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


class ReminderBubble(QWidget):
    drank = Signal()
    snoozed = Signal()
    paused = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedWidth(310)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(5, 5, 5, 5)
        card = QFrame()
        card.setObjectName("card")
        outer.addWidget(card)
        content = QVBoxLayout(card)
        content.setContentsMargins(14, 12, 14, 12)
        content.setSpacing(9)

        self.title_label = QLabel("💧 SipCat 提醒你喝水")
        self.title_label.setObjectName("title")
        self.title_label.setWordWrap(True)
        note = QLabel("休息一下，按自己的节奏喝水。")
        self.today_label = QLabel("今天已记录 0 次")
        content.addWidget(self.title_label)
        content.addWidget(note)
        content.addWidget(self.today_label)

        buttons = QHBoxLayout()
        buttons.setSpacing(5)
        for label, signal in (
            ("喝过了", self.drank),
            ("稍后10分钟", self.snoozed),
            ("暂停", self.paused),
        ):
            button = QPushButton(label)
            button.clicked.connect(lambda checked=False, target=signal: target.emit())
            buttons.addWidget(button)
        content.addLayout(buttons)
        self.setStyleSheet("""
            QFrame#card { background: #172B3B; border: 2px solid #6CCCE7;
                          border-radius: 14px; }
            QLabel { color: #E8F8FC; font-size: 12px; border: none; }
            QLabel#title { font-size: 15px; font-weight: bold; }
            QPushButton { color: #14344A; background: #B7F1FC; border: none;
                          border-radius: 7px; padding: 7px 5px; }
            QPushButton:hover { background: #74D7F0; }
        """)

    def set_today_count(self, count: int | None) -> None:
        if count is None:
            self.today_label.setText("今日记录暂时不可用")
        else:
            self.today_label.setText(f"今天已记录 {count} 次")

    def set_pet_name(self, name: str) -> None:
        self.title_label.setText(f"💧 {name}提醒你喝水")

    def show_near(self, pet: QWidget) -> None:
        self.adjustSize()
        screen = QApplication.screenAt(pet.frameGeometry().center()) or QApplication.primaryScreen()
        if screen is not None:
            area = screen.availableGeometry()
            x = max(area.left(), min(pet.x() + pet.width() - self.width(), area.right() - self.width()))
            above = pet.y() - self.height() - 8
            below = pet.y() + pet.height() + 8
            y = above if above >= area.top() else min(below, area.bottom() - self.height())
            self.move(x, y)
        self.show()
        self.raise_()
