"""宠物窗口：加载逐帧图片、切换状态并处理拖动。

图片与本文件在同一打包目录下的 assets 文件夹中。
"""

from pathlib import Path

from PySide6.QtCore import QPoint, QTimer, Qt, Signal
from PySide6.QtGui import QMouseEvent, QPainter, QPixmap
from PySide6.QtWidgets import QMenu, QWidget


class PetWindow(QWidget):
    moved = Signal()
    panel_requested = Signal()
    WIDTH = 180
    HEIGHT = 180
    FRAMES = {
        "normal": ("cat_normal.png", "cat_normal_1.png"),
        "drinking": ("cat_drinking.png", "cat_drinking_1.png"),
        "reminder": ("cat_reminder.png", "cat_reminder_1.png"),
        "working": ("cat_working.png", "cat_working_1.png"),
    }
    # 每帧停留的时间（毫秒）：正常状态会隔几秒才眨眼。
    DURATIONS = {
        "normal": (3500, 180),
        "drinking": (360, 360),
        "reminder": (480, 480),
        "working": (300, 300),
    }

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(self.WIDTH, self.HEIGHT)
        self.setWindowTitle("SipCat")
        self.setToolTip("左键拖动，右键打开菜单")
        self.context_menu: QMenu | None = None
        self._drag_offset: QPoint | None = None

        self._frames = {
            state: tuple(self._load_frame(name) for name in names)
            for state, names in self.FRAMES.items()
        }
        self._animation_timer = QTimer(self)
        self._animation_timer.setSingleShot(True)
        self._animation_timer.timeout.connect(self._next_frame)
        self.set_state("normal")

    def _load_frame(self, filename: str) -> QPixmap:
        image_path = Path(__file__).resolve().parent / "assets" / filename
        image = QPixmap(str(image_path))
        if image.isNull():
            raise FileNotFoundError(f"无法加载宠物图片：{image_path}")
        return image.scaled(
            self.WIDTH, self.HEIGHT,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.FastTransformation,
        )

    def set_state(self, state: str) -> None:
        if state not in self._frames:
            raise ValueError(f"未知的宠物状态：{state}")
        self.state = state
        self._frame_index = 0
        self._show_frame()

    def _show_frame(self) -> None:
        self.sprite = self._frames[self.state][self._frame_index]
        self.setMask(self.sprite.mask())  # 透明处不拦截桌面的鼠标操作。
        self.update()
        self._animation_timer.start(self.DURATIONS[self.state][self._frame_index])

    def _next_frame(self) -> None:
        self._frame_index = (self._frame_index + 1) % len(self._frames[self.state])
        self._show_frame()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.sprite)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton and self.context_menu is not None:
            self.context_menu.exec(event.globalPosition().toPoint())
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_offset is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_offset)
            self.moved.emit()
            event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_offset = None
            event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.panel_requested.emit()
            event.accept()
