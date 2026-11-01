"""数据面板：今日时间列表、七日柱状图和宠物改名。"""

import sqlite3
from datetime import date

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QMessageBox, QPushButton, QVBoxLayout, QWidget,
)

from storage import DrinkStore


class WeeklyChart(QWidget):
    """一根柱子代表一天的喝水记录次数，不代表饮水量。"""

    def __init__(self) -> None:
        super().__init__()
        self.counts: list[tuple[date, int]] = []
        self.setMinimumHeight(180)

    def set_counts(self, counts: list[tuple[date, int]]) -> None:
        self.counts = counts
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#183347"))
        if not self.counts:
            return

        left, right, top, bottom = 12, 12, 28, 33
        plot_width = self.width() - left - right
        baseline = self.height() - bottom
        plot_height = baseline - top
        slot = plot_width / len(self.counts)
        maximum = max(1, *(count for _, count in self.counts))

        painter.setPen(QColor("#86A6B5"))
        painter.drawLine(left, baseline, self.width() - right, baseline)
        for index, (day, count) in enumerate(self.counts):
            x = left + index * slot + slot * 0.18
            width = slot * 0.64
            height = (count / maximum) * (plot_height - 20)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor("#67D2ED" if index == len(self.counts) - 1 else "#428BAA"))
            if count:
                painter.drawRoundedRect(QRectF(x, baseline - height, width, height), 4, 4)
            painter.setPen(QColor("#E8F8FC"))
            painter.drawText(
                QRectF(x, baseline - height - 24, width, 20),
                Qt.AlignmentFlag.AlignCenter, str(count),
            )
            painter.drawText(
                QRectF(x - 5, baseline + 5, width + 10, 20),
                Qt.AlignmentFlag.AlignCenter, day.strftime("%m/%d"),
            )


class DashboardDialog(QDialog):
    name_saved = Signal(str)

    def __init__(self, store: DrinkStore) -> None:
        super().__init__()
        self.store = store
        self.setWindowTitle("SipCat · 数据面板")
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint)
        self.resize(460, 530)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(12)

        heading = QLabel("喝水记录")
        heading.setObjectName("heading")
        layout.addWidget(heading)
        self.summary = QLabel()
        layout.addWidget(self.summary)

        chart_title = QLabel("最近 7 天 · 记录次数")
        layout.addWidget(chart_title)
        self.chart = WeeklyChart()
        layout.addWidget(self.chart)

        layout.addWidget(QLabel("今天的时间"))
        self.records_list = QListWidget()
        self.records_list.setMinimumHeight(100)
        layout.addWidget(self.records_list)

        layout.addWidget(QLabel("给宠物起个名字"))
        name_row = QHBoxLayout()
        self.name_input = QLineEdit(store.load_name())
        self.name_input.setObjectName("petNameInput")
        self.name_input.setMaxLength(20)
        self.name_input.setPlaceholderText("1–20 个字符")
        save_button = QPushButton("保存名字")
        save_button.setObjectName("saveNameButton")
        save_button.clicked.connect(self.save_name)
        self.name_input.returnPressed.connect(self.save_name)
        name_row.addWidget(self.name_input)
        name_row.addWidget(save_button)
        layout.addLayout(name_row)
        self.name_status = QLabel("")
        layout.addWidget(self.name_status)

        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.close)
        layout.addWidget(close_button)
        self.setStyleSheet("""
            QDialog { background: #142938; color: #E8F8FC; }
            QLabel { color: #E8F8FC; font-size: 13px; }
            QLabel#heading { font-size: 21px; font-weight: bold; }
            QLineEdit, QListWidget { background: #203D50; color: #F3FCFF;
                                  border: 1px solid #5CA9C5; border-radius: 6px;
                                  padding: 6px; }
            QPushButton { background: #75D3EB; color: #143142; border: none;
                          border-radius: 7px; padding: 8px 12px; font-weight: bold; }
            QPushButton:hover { background: #A8E8F5; }
        """)
        self.refresh_data()

    def refresh_data(self) -> None:
        records = self.store.today_records()
        self.chart.set_counts(self.store.weekly_counts())
        last_time = records[-1].strftime("%H:%M:%S") if records else "暂无"
        self.summary.setText(f"今天记录 {len(records)} 次  ·  最近一次 {last_time}")
        self.records_list.clear()
        if records:
            for index, moment in enumerate(records, start=1):
                self.records_list.addItem(f"{index:02d}    {moment.strftime('%H:%M:%S')}")
        else:
            self.records_list.addItem("今天还没有记录，喝水后点‘喝过了’即可添加。")

    def save_name(self) -> None:
        try:
            name = self.store.save_name(self.name_input.text())
        except (ValueError, sqlite3.Error) as error:
            QMessageBox.warning(self, "无法保存名字", str(error))
            return
        self.name_input.setText(name)
        self.name_status.setText(f"已保存：{name}")
        self.name_saved.emit(name)
