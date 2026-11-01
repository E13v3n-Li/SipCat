"""程序入口：连接宠物动画、提醒计时、气泡和托盘菜单。"""

import sys
import sqlite3
import tempfile
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QAction, QActionGroup, QIcon
from PySide6.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon

from bubble import ReminderBubble
from dashboard import DashboardDialog
from pet import PetWindow
from reminder import ReminderEngine
from storage import DrinkStore


def self_check(app: QApplication) -> int:
    """供打包脚本检查：实际创建图片和面板，不触碰用户记录。"""
    try:
        with tempfile.TemporaryDirectory() as directory:
            store = DrinkStore(Path(directory) / "self_check.sqlite3")
            pet = PetWindow()
            dashboard = DashboardDialog(store)
            dashboard.show()
            app.processEvents()
            if not dashboard.isVisible() or len(pet._frames) != 4:
                return 1
            dashboard.close()
            pet.close()
        return 0
    except Exception:
        import traceback
        traceback.print_exc()
        return 1


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("SipCat")
    app.setQuitOnLastWindowClosed(False)
    if "--self-check" in sys.argv:
        return self_check(app)

    store = DrinkStore()
    pet = PetWindow()
    bubble = ReminderBubble()
    dashboard = DashboardDialog(store)
    reminder = ReminderEngine(interval_minutes=store.load_interval(), snooze_minutes=10)
    base_state = "normal"  # 喝水完成后会自动切换为 working。
    was_hidden_before_reminder = False
    tray = None

    def apply_name(name: str) -> None:
        pet.setWindowTitle(name)
        pet.setToolTip(f"{name}：左键拖动，右键打开菜单")
        bubble.set_pet_name(name)
        dashboard.setWindowTitle(f"{name} · 数据面板")
        if tray is not None:
            tray.setToolTip(name)

    dashboard.name_saved.connect(apply_name)
    apply_name(store.load_name())

    menu = QMenu()
    pet.context_menu = menu
    tray_available = QSystemTrayIcon.isSystemTrayAvailable()

    show_action = QAction("隐藏宠物", app)
    show_action.setEnabled(tray_available)

    def restore_pet() -> None:
        pet.set_state(base_state)
        if was_hidden_before_reminder and tray_available:
            pet.hide()
            show_action.setText("显示宠物")
        else:
            show_action.setText("隐藏宠物")

    def toggle_pet() -> None:
        if pet.isVisible():
            if bubble.isVisible():
                bubble.hide()
                reminder.snooze()  # 用户主动隐藏时，稍后再提醒。
                pet.set_state(base_state)
            pet.hide()
            show_action.setText("显示宠物")
        else:
            pet.show()
            show_action.setText("隐藏宠物")

    show_action.triggered.connect(toggle_pet)
    menu.addAction(show_action)

    state_menu = menu.addMenu("宠物状态")
    state_group = QActionGroup(app)
    state_actions = {}
    for state, label in (
        ("normal", "正常"),
        ("working", "努力工作"),
        ("drinking", "喝水（预览）"),
        ("reminder", "提醒（预览）"),
    ):
        action = state_menu.addAction(label)
        action.setCheckable(True)
        action.setChecked(state == "normal")
        state_group.addAction(action)
        state_actions[state] = action

        def select_state(checked=False, name=state) -> None:
            nonlocal base_state
            base_state = name
            if not bubble.isVisible():
                pet.set_state(name)

        action.triggered.connect(select_state)

    interval_menu = menu.addMenu("提醒间隔")
    interval_group = QActionGroup(app)

    def change_interval(minutes: int) -> None:
        reminder.set_interval_minutes(minutes)
        try:
            store.save_interval(minutes)
        except sqlite3.Error as error:
            QMessageBox.warning(pet, "保存失败", f"本次间隔已更改，但无法保存设置：{error}")

    for minutes in (50, 55, 60):
        action = interval_menu.addAction(f"{minutes} 分钟")
        action.setCheckable(True)
        action.setChecked(minutes == reminder.interval_minutes)
        interval_group.addAction(action)
        action.triggered.connect(lambda checked=False, value=minutes: change_interval(value))

    def on_reminder_due() -> None:
        nonlocal was_hidden_before_reminder
        was_hidden_before_reminder = not pet.isVisible()
        pet.set_state("reminder")
        pet.show()
        show_action.setText("隐藏宠物")
        try:
            bubble.set_today_count(len(store.today_records()))
        except (sqlite3.Error, ValueError):
            bubble.set_today_count(None)
        bubble.show_near(pet)

    def on_drunk() -> None:
        nonlocal base_state
        bubble.hide()
        reminder.mark_drunk()
        try:
            store.record_drink()
            if dashboard.isVisible():
                dashboard.refresh_data()
        except sqlite3.Error as error:
            QMessageBox.warning(pet, "记录失败", f"喝水提醒已重置，但时间未能保存：{error}")
        base_state = "working"
        state_actions["working"].setChecked(True)
        pet.set_state("drinking")
        # 先喝水，再持续播放努力工作的动画；新提醒出现时不要覆盖它。
        QTimer.singleShot(1600, lambda: restore_pet() if not bubble.isVisible() else None)

    def on_snooze() -> None:
        bubble.hide()
        reminder.snooze()
        restore_pet()

    pause_action = QAction("暂停提醒", app)
    test_action = QAction("立即测试提醒", app)
    dashboard_action = QAction("数据面板与改名", app)

    def show_dashboard() -> None:
        try:
            dashboard.refresh_data()
        except (sqlite3.Error, ValueError) as error:
            QMessageBox.warning(pet, "读取失败", f"无法读取喝水记录：{error}")
            return
        dashboard.show()
        dashboard.raise_()
        dashboard.activateWindow()

    pet.panel_requested.connect(show_dashboard)

    def toggle_pause() -> None:
        if reminder.paused:
            reminder.resume()
            pause_action.setText("暂停提醒")
            test_action.setEnabled(True)
        else:
            had_bubble = bubble.isVisible()
            bubble.hide()
            reminder.pause()
            if had_bubble:
                restore_pet()
            pause_action.setText("恢复提醒")
            test_action.setEnabled(False)

    reminder.reminder_due.connect(on_reminder_due)
    bubble.drank.connect(on_drunk)
    bubble.snoozed.connect(on_snooze)
    bubble.paused.connect(lambda: toggle_pause() if not reminder.paused else None)
    pet.moved.connect(lambda: bubble.show_near(pet) if bubble.isVisible() else None)
    pause_action.triggered.connect(toggle_pause)
    test_action.triggered.connect(reminder.trigger_now)
    dashboard_action.triggered.connect(show_dashboard)
    menu.insertAction(show_action, dashboard_action)
    menu.addAction(pause_action)
    menu.addAction(test_action)
    menu.addSeparator()
    quit_action = QAction("退出", app)
    quit_action.triggered.connect(app.quit)
    menu.addAction(quit_action)

    if tray_available:
        tray = QSystemTrayIcon(QIcon(pet.sprite), app)
        tray.setToolTip(store.load_name())
        tray.setContextMenu(menu)
        tray.activated.connect(
            lambda reason: show_dashboard()
            if reason == QSystemTrayIcon.ActivationReason.DoubleClick else None
        )
        tray.show()

    screen = app.primaryScreen()
    if screen is not None:
        area = screen.availableGeometry()
        pet.move(area.right() - pet.width() - 24, area.bottom() - pet.height() - 24)
    pet.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
