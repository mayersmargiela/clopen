from __future__ import annotations

import copy
import ctypes
import os
import sys
import threading
from pathlib import Path

from PySide6.QtCore import (
    QObject,
    Property,
    QSettings,
    QPoint,
    QTimer,
    QUrl,
    Qt,
    Signal,
    Slot,
)
from PySide6.QtGui import QAction, QColor, QCursor, QFont, QFontDatabase, QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QLabel,
    QLineEdit,
    QMessageBox,
    QMenu,
    QPushButton,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from .app import LIQUID_DIALOG_STYLE, GroupEditorDialog, _app_icon, _apply_liquid_blur, group_matches
from .config import ConfigError, ConfigStore
from .launcher import BatchController
from .models import AppEntry, AppGroup, LaunchReport


# Windows 11 desktop acrylic. The QML scene itself never paints an opaque black/white
# base; this native backdrop is the only full-window material behind the glass layers.
_DWMWA_USE_IMMERSIVE_DARK_MODE = 20
_DWMWA_WINDOW_CORNER_PREFERENCE = 33
_DWMWA_BORDER_COLOR = 34
_DWMWA_SYSTEMBACKDROP_TYPE = 38
_DWMWCP_ROUND = 2
_DWMSBT_TRANSIENTWINDOW = 3
_DWMWA_COLOR_NONE = 0xFFFFFFFE


# Physical-key fallback for Ctrl+Shift+E.  This deliberately does not use
# RegisterHotKey / WM_HOTKEY, so another program owning that Windows shortcut
# cannot block Clopen from seeing the actual key state.
_VK_SHIFT = 0x10
_VK_CONTROL = 0x11
_VK_E = 0x45
_VK_LSHIFT = 0xA0
_VK_RSHIFT = 0xA1
_VK_LCONTROL = 0xA2
_VK_RCONTROL = 0xA3


def _key_down(vk: int) -> bool:
    if os.name != "nt":
        return False
    try:
        user32 = ctypes.windll.user32
        return bool(int(user32.GetAsyncKeyState(vk)) & 0x8000)
    except (AttributeError, OSError, TypeError, ValueError):
        return False


def _ctrl_shift_e_down() -> bool:
    ctrl = _key_down(_VK_CONTROL) or _key_down(_VK_LCONTROL) or _key_down(_VK_RCONTROL)
    shift = _key_down(_VK_SHIFT) or _key_down(_VK_LSHIFT) or _key_down(_VK_RSHIFT)
    return ctrl and shift and _key_down(_VK_E)


def _qml_dir() -> Path:
    root = getattr(sys, "_MEIPASS", None)
    if root:
        return Path(root) / "clopen" / "qml"
    return Path(__file__).resolve().parent / "qml"


def _apply_native_glass(window: QQuickWindow, dark: bool) -> None:
    """Use an untinted Win32 blur behind a genuinely transparent QQuickWindow.

    DWMWA_SYSTEMBACKDROP_TYPE=TRANSIENTWINDOW paints Microsoft's own Acrylic
    material, including its system tint. That is what produced the large gray
    base in v0.5.0. For Clopen Liquid Glass the OS should only blur whatever is
    behind the HWND; QML owns the optical highlights and glass hierarchy.
    """
    if os.name != "nt" or os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        return
    try:
        hwnd_value = int(window.winId())
        hwnd = ctypes.c_void_p(hwnd_value)
        dwm = ctypes.windll.dwmapi
        user32 = ctypes.windll.user32

        # Explicitly turn the Windows 11 system backdrop off. It adds a gray /
        # theme-colored surface even when the Qt scene is fully transparent.
        backdrop_none = ctypes.c_int(1)  # DWMSBT_NONE
        dwm.DwmSetWindowAttribute(
            hwnd,
            _DWMWA_SYSTEMBACKDROP_TYPE,
            ctypes.byref(backdrop_none),
            ctypes.sizeof(backdrop_none),
        )

        class ACCENT_POLICY(ctypes.Structure):
            _fields_ = [
                ("AccentState", ctypes.c_int),
                ("AccentFlags", ctypes.c_int),
                ("GradientColor", ctypes.c_uint),
                ("AnimationId", ctypes.c_int),
            ]

        class WINDOWCOMPOSITIONATTRIBDATA(ctypes.Structure):
            _fields_ = [
                ("Attribute", ctypes.c_int),
                ("Data", ctypes.c_void_p),
                ("SizeOfData", ctypes.c_size_t),
            ]

        # ACCENT_ENABLE_BLURBEHIND = 3. GradientColor=0 means no fixed tint.
        policy = ACCENT_POLICY(3, 0, 0x00000000, 0)
        data = WINDOWCOMPOSITIONATTRIBDATA(
            19, ctypes.cast(ctypes.pointer(policy), ctypes.c_void_p), ctypes.sizeof(policy)
        )
        user32.SetWindowCompositionAttribute(hwnd, ctypes.byref(data))

        # Native rounding/border settings only; no DWM frame extension is used.
        corner = ctypes.c_int(_DWMWCP_ROUND)
        dwm.DwmSetWindowAttribute(
            hwnd,
            _DWMWA_WINDOW_CORNER_PREFERENCE,
            ctypes.byref(corner),
            ctypes.sizeof(corner),
        )
        border = ctypes.c_uint(_DWMWA_COLOR_NONE)
        dwm.DwmSetWindowAttribute(
            hwnd,
            _DWMWA_BORDER_COLOR,
            ctypes.byref(border),
            ctypes.sizeof(border),
        )
        dark_value = ctypes.c_int(1 if dark else 0)
        dwm.DwmSetWindowAttribute(
            hwnd,
            _DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(dark_value),
            ctypes.sizeof(dark_value),
        )
    except (AttributeError, OSError, TypeError, ValueError):
        return


class GlassSettingsDialog(QDialog):
    def __init__(self, owner: "ClopenBridge"):
        super().__init__(None)
        self.owner = owner
        self.setWindowTitle("Clopen 设置")
        self.setMinimumWidth(390)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet(LIQUID_DIALOG_STYLE)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)
        hotkey = QLabel("Ctrl + Shift + E")
        hotkey.setObjectName("muted")
        form.addRow("快速呼出", hotkey)
        tray_note = QLabel("关闭主界面后，Clopen 会继续驻留在系统托盘。")
        tray_note.setObjectName("muted")
        tray_note.setWordWrap(True)
        form.addRow("后台运行", tray_note)
        glass_note = QLabel("Liquid Glass 自动适配当前电脑的桌面与系统深浅模式，不使用固定玻璃颜色。")
        glass_note.setObjectName("muted")
        glass_note.setWordWrap(True)
        form.addRow("玻璃材质", glass_note)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.button(QDialogButtonBox.StandardButton.Close).setText("关闭")
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        QTimer.singleShot(0, lambda: _apply_native_glass(self, owner.darkMode))


class QuickLauncherPopup(QWidget):
    """Native QWidget quick launcher used by the Liquid Glass shell.

    The main interface stays QML.  The quick launcher intentionally uses the
    same stable QWidget popup path as the classic Clopen build: it is created
    once, uses Qt.Popup so clicking outside dismisses it, and receives native
    blur after its HWND exists.  This avoids runtime QQmlComponent/window
    creation in the global-shortcut path.
    """

    def __init__(self, owner: "ClopenBridge"):
        super().__init__(
            None,
            Qt.WindowType.Popup
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint
            | Qt.WindowType.WindowStaysOnTopHint,
        )
        self.owner = owner
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setObjectName("quickRoot")
        self.setFixedWidth(340)
        self.group_buttons: list[tuple[QPushButton, AppGroup]] = []

        self.surface = QFrame(self)
        self.surface.setObjectName("quickSurface")
        self.body = QVBoxLayout(self.surface)
        self.body.setContentsMargins(12, 12, 12, 12)
        self.body.setSpacing(6)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.surface)
        self._apply_theme()

    def _apply_theme(self) -> None:
        dark = self.owner.darkMode
        text = "#F6F7FA" if dark else "#20242A"
        muted = "rgba(235,239,246,185)" if dark else "rgba(32,36,42,160)"
        surface = "rgba(255,255,255,18)" if dark else "rgba(255,255,255,72)"
        control = "rgba(255,255,255,18)" if dark else "rgba(255,255,255,82)"
        hover = "rgba(255,255,255,30)" if dark else "rgba(255,255,255,118)"
        edge = "rgba(255,255,255,38)" if dark else "rgba(255,255,255,145)"
        self.setStyleSheet(f"""
        QWidget#quickRoot {{ background: transparent; }}
        QFrame#quickSurface {{
            background: {surface};
            border: none;
            border-radius: 18px;
        }}
        QLabel {{ color: {text}; background: transparent; font-family: 'Microsoft YaHei UI'; }}
        QLabel#quickTitle {{ font-size: 12px; font-weight: 600; }}
        QLabel#quickMuted {{ color: {muted}; font-size: 12px; }}
        QLineEdit {{
            min-height: 36px;
            color: {text};
            background: {control};
            border: 1px solid {edge};
            border-radius: 10px;
            padding: 0 12px;
            font-family: 'Microsoft YaHei UI';
            font-size: 13px;
        }}
        QPushButton {{
            min-height: 38px;
            color: {text};
            background: {control};
            border: 1px solid {edge};
            border-radius: 10px;
            padding: 0 12px;
            text-align: center;
            font-family: 'Microsoft YaHei UI';
            font-size: 13px;
        }}
        QPushButton:hover {{ background: {hover}; }}
        QPushButton:pressed {{ background: rgba(255,255,255,42); }}
        """)

    @staticmethod
    def _clear(layout: QVBoxLayout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def rebuild(self) -> None:
        self._apply_theme()
        self._clear(self.body)
        self.group_buttons = []

        title = QLabel("快速操作")
        title.setObjectName("quickTitle")
        self.body.addWidget(title)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索组合或软件…")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._filter_groups)
        self.search_edit.returnPressed.connect(self._run_first_result)
        self.body.addWidget(self.search_edit)

        groups = sorted(
            self.owner.groups,
            key=lambda item: (item.name not in self.owner.controller.active_groups, item.name.casefold()),
        )
        for group in groups:
            active = group.name in self.owner.controller.active_groups
            button = QPushButton(f"{'关闭' if active else '开启'}  {group.name}")
            button.clicked.connect(lambda _checked=False, name=group.name: self._run_group(name))
            self.body.addWidget(button)
            self.group_buttons.append((button, group))

        self.empty_label = QLabel("没有可用组合")
        self.empty_label.setObjectName("quickMuted")
        self.empty_label.setContentsMargins(8, 8, 8, 8)
        self.empty_label.setVisible(not groups)
        self.body.addWidget(self.empty_label)

        self.body.addSpacing(2)
        open_button = QPushButton("打开主界面")
        open_button.clicked.connect(self._open_main)
        self.body.addWidget(open_button)
        quit_button = QPushButton("退出 Clopen")
        quit_button.clicked.connect(self._quit)
        self.body.addWidget(quit_button)
        self.adjustSize()

    def _filter_groups(self, query: str) -> None:
        visible = 0
        for button, group in self.group_buttons:
            matches = group_matches(group, query)
            button.setVisible(matches)
            visible += int(matches)
        self.empty_label.setText("没有搜索结果" if query.strip() else "没有可用组合")
        self.empty_label.setVisible(visible == 0)
        self.adjustSize()

    def _run_first_result(self) -> None:
        for button, group in self.group_buttons:
            if button.isVisible():
                self._run_group(group.name)
                return

    def _run_group(self, name: str) -> None:
        self.hide()
        self.owner.toggleGroupByName(name)

    def _open_main(self) -> None:
        self.hide()
        self.owner.showMain()

    def _quit(self) -> None:
        self.hide()
        self.owner.quitApplication()

    def popup(self) -> None:
        self.rebuild()
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        area = screen.availableGeometry()
        point = QCursor.pos() + QPoint(12, 12)
        point.setX(min(point.x(), area.right() - self.width()))
        point.setY(min(point.y(), area.bottom() - self.height()))
        point.setX(max(point.x(), area.left()))
        point.setY(max(point.y(), area.top()))
        self.move(point)
        self.show()
        self.raise_()
        self.activateWindow()
        if os.environ.get("QT_QPA_PLATFORM") != "offscreen":
            QTimer.singleShot(0, lambda: _apply_liquid_blur(self))
        QTimer.singleShot(0, lambda: self.search_edit.setFocus(Qt.FocusReason.ShortcutFocusReason))




class ClopenBridge(QObject):
    groupsChanged = Signal()
    selectedChanged = Signal()
    stateChanged = Signal()
    themeChanged = Signal()
    messageChanged = Signal()
    hotkeyTriggered = Signal()

    def __init__(self, app: QApplication, engine: QQmlApplicationEngine):
        super().__init__()
        self.app = app
        self.engine = engine
        self.store = ConfigStore()
        self.controller = BatchController()
        self.groups: list[AppGroup] = []
        self.selected_index = -1
        self._message = ""
        self._main_window: QQuickWindow | None = None
        self._dark_mode = self._resolve_dark_mode()
        self.app.styleHints().colorSchemeChanged.connect(self._system_scheme_changed)

        # The quick launcher uses the same stable native QWidget popup model as
        # classic Clopen.  It is created once and never depends on QML runtime
        # component creation.
        self._quick_popup = QuickLauncherPopup(self)

        # The physical hotkey watcher runs independently of the Qt/QML native
        # message path.  It can still see Ctrl+Shift+E when another program has
        # registered the same Windows hotkey (ERROR_HOTKEY_ALREADY_REGISTERED).
        self._hotkey_stop = threading.Event()
        self._hotkey_thread: threading.Thread | None = None
        self.hotkeyTriggered.connect(
            self.toggleQuickLauncher,
            Qt.ConnectionType.QueuedConnection,
        )

        self.tray_icon: QSystemTrayIcon | None = None
        self.tray_menu: QMenu | None = None
        self.reload(silent=True)
        self._setup_tray()
        QTimer.singleShot(0, self._start_hotkey_watcher)

    def _start_hotkey_watcher(self) -> None:
        if os.name != "nt":
            return
        if self._hotkey_thread is not None and self._hotkey_thread.is_alive():
            return
        self._hotkey_stop.clear()
        self._hotkey_thread = threading.Thread(
            target=self._hotkey_watch_loop,
            name="ClopenPhysicalHotkey",
            daemon=True,
        )
        self._hotkey_thread.start()

    def _hotkey_watch_loop(self) -> None:
        latched = False
        while not self._hotkey_stop.wait(0.025):
            down = _ctrl_shift_e_down()
            if down and not latched:
                latched = True
                self.hotkeyTriggered.emit()
            elif not down:
                latched = False

    def _resolve_dark_mode(self) -> bool:
        return self.app.styleHints().colorScheme() == Qt.ColorScheme.Dark

    def _system_scheme_changed(self, scheme) -> None:
        new_dark = scheme == Qt.ColorScheme.Dark
        if new_dark == self._dark_mode:
            return
        self._dark_mode = new_dark
        self.app.setProperty("clopenDark", new_dark)
        self.app.setWindowIcon(_app_icon(new_dark))
        if self.tray_icon is not None:
            self.tray_icon.setIcon(_app_icon(new_dark))
        self._refresh_tray_menu()
        if self._main_window is not None:
            _apply_native_glass(self._main_window, new_dark)
        self._quick_popup._apply_theme()
        self.themeChanged.emit()

    @Property(bool, notify=themeChanged)
    def darkMode(self) -> bool:
        return self._dark_mode

    @Property(str, notify=messageChanged)
    def message(self) -> str:
        return self._message

    def _set_message(self, value: str) -> None:
        if value == self._message:
            return
        self._message = value
        self.messageChanged.emit()

    @Property("QVariantList", notify=groupsChanged)
    def groupItems(self):
        return [
            {
                "name": group.name,
                "count": len(group.entries),
                "active": group.name in self.controller.active_groups,
                "selected": index == self.selected_index,
            }
            for index, group in enumerate(self.groups)
        ]

    @Property("QVariantMap", notify=selectedChanged)
    def selectedGroup(self):
        group = self._selected_group()
        if group is None:
            return {
                "exists": False,
                "name": "没有可用组合",
                "meta": "点击左侧“新建”创建 Clopen 组合",
                "active": False,
                "entries": [],
            }
        managed = sum(not item.is_external for item in group.entries)
        return {
            "exists": True,
            "name": group.name,
            "meta": f"{len(group.entries)} 个启动项 · {managed} 个可安全纳入关闭会话",
            "active": group.name in self.controller.active_groups,
            "entries": [
                {
                    "name": entry.name or "未命名",
                    "kind": self._entry_kind(entry),
                    "mode": self._entry_mode(entry),
                }
                for entry in group.entries
            ],
        }

    @Property(bool, notify=stateChanged)
    def anyActive(self) -> bool:
        return bool(self.controller.active_groups)

    @Property(str, notify=stateChanged)
    def primaryText(self) -> str:
        group = self._selected_group()
        if group is None:
            return "开启组合"
        return "关闭组合" if group.name in self.controller.active_groups else "开启组合"

    def _selected_group(self) -> AppGroup | None:
        if 0 <= self.selected_index < len(self.groups):
            return self.groups[self.selected_index]
        return None

    def reload(self, *, silent: bool = False) -> None:
        previous = self._selected_group().name if self._selected_group() else ""
        try:
            self.groups = self.store.load()
        except ConfigError as exc:
            self.groups = []
            if not silent:
                QMessageBox.critical(None, "配置错误", str(exc))
        self.selected_index = 0 if self.groups else -1
        if previous:
            for index, group in enumerate(self.groups):
                if group.name == previous:
                    self.selected_index = index
                    break
        self._notify_all()

    def _notify_all(self) -> None:
        self.groupsChanged.emit()
        self.selectedChanged.emit()
        self.stateChanged.emit()
        self._refresh_tray_menu()

    def _save_groups(self, groups: list[AppGroup]) -> bool:
        old = self.store.groups
        self.store.groups = copy.deepcopy(groups)
        try:
            self.store.save()
        except OSError as exc:
            self.store.groups = old
            QMessageBox.critical(None, "保存失败", str(exc))
            return False
        self.groups = groups
        self._set_message("组合配置已保存到 Clopen")
        return True

    @staticmethod
    def _entry_kind(entry: AppEntry) -> str:
        if entry.is_uwp:
            return "UWP"
        if entry.is_folder:
            return "文件夹"
        if entry.is_file:
            return "文件"
        if entry.url and not entry.path:
            return "网址"
        return "应用"

    @staticmethod
    def _entry_mode(entry: AppEntry) -> str:
        if entry.is_external:
            return "外部启动"
        if entry.run_as_admin:
            return "管理员 · 受管"
        return "普通权限 · 受管"

    @Slot(str)
    def selectGroup(self, name: str) -> None:
        for index, group in enumerate(self.groups):
            if group.name == name:
                if self.selected_index != index:
                    self.selected_index = index
                    self.groupsChanged.emit()
                    self.selectedChanged.emit()
                    self.stateChanged.emit()
                return

    @Slot()
    def refresh(self) -> None:
        self.reload(silent=False)
        self._set_message("已刷新")

    @Slot()
    def newGroup(self) -> None:
        dialog = GroupEditorDialog(None, reserved_names={g.name for g in self.groups})
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        group = dialog.result_group()
        candidate = copy.deepcopy(self.groups)
        candidate.append(group)
        if self._save_groups(candidate):
            self.reload(silent=True)
            self.selectGroup(group.name)

    @Slot()
    def editSelected(self) -> None:
        group = self._selected_group()
        if group is None:
            return
        if group.name in self.controller.active_groups:
            QMessageBox.information(None, "组合正在运行", "请先关闭该组合，再进行编辑。")
            return
        reserved = {item.name for item in self.groups if item.name != group.name}
        dialog = GroupEditorDialog(None, group, reserved_names=reserved)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        edited = dialog.result_group()
        candidate = copy.deepcopy(self.groups)
        candidate[self.selected_index] = edited
        if self._save_groups(candidate):
            self.reload(silent=True)
            self.selectGroup(edited.name)

    @Slot()
    def deleteSelected(self) -> None:
        group = self._selected_group()
        if group is None:
            return
        if group.name in self.controller.active_groups:
            QMessageBox.information(None, "组合正在运行", "请先关闭该组合，再进行删除。")
            return
        if QMessageBox.question(None, "删除组合", f"确定删除「{group.name}」？") != QMessageBox.StandardButton.Yes:
            return
        candidate = copy.deepcopy(self.groups)
        candidate.pop(self.selected_index)
        if self._save_groups(candidate):
            self.reload(silent=True)

    @Slot()
    def primaryAction(self) -> None:
        group = self._selected_group()
        if group is None:
            return
        self._toggle_group(group)

    @Slot(str)
    def toggleGroupByName(self, name: str) -> None:
        group = next((g for g in self.groups if g.name == name), None)
        if group is None:
            return
        self._toggle_group(group)

    def _toggle_group(self, group: AppGroup) -> None:
        if group.name in self.controller.active_groups:
            if QMessageBox.question(
                None,
                "确认关闭",
                f"只关闭「{group.name}」由 Clopen 本次登记的进程？\n\n未保存内容可能丢失。",
            ) != QMessageBox.StandardButton.Yes:
                return
            report = self.controller.close_group(group.name)
            QMessageBox.information(None, "关闭结果", f"{report.detail}\n关闭数量：{report.closed}")
        else:
            self._set_message(f"正在开启 {group.name}…")
            self.stateChanged.emit()
            report = self.controller.launch_group(group)
            self._show_launch_report(report)
        self._notify_all()
        self._refresh_tray_tooltip()

    @Slot()
    def closeAll(self) -> None:
        if not self.controller.active_groups:
            return
        if QMessageBox.question(
            None,
            "确认关闭全部",
            "只关闭 Clopen 本次登记的全部进程会话？\n\n未保存内容可能丢失。",
        ) != QMessageBox.StandardButton.Yes:
            return
        reports = self.controller.close_all()
        QMessageBox.information(None, "关闭结果", "\n".join(f"{r.group_name}：{r.closed} 个" for r in reports))
        self._notify_all()
        self._refresh_tray_tooltip()

    @staticmethod
    def _show_launch_report(report: LaunchReport) -> None:
        lines = [f"成功登记：{report.started}", f"外部启动：{report.unmanaged}", f"失败：{report.failed}"]
        details = [f"{item.name}：{item.detail}" for item in report.results if item.detail]
        if details:
            lines.extend(["", *details])
        QMessageBox.information(None, "启动结果", "\n".join(lines))

    @Slot()
    def showSettings(self) -> None:
        GlassSettingsDialog(self).exec()

    def set_main_window(self, window: QQuickWindow) -> None:
        self._main_window = window
        window.setColor(QColor(0, 0, 0, 0))
        window.setIcon(_app_icon(self._dark_mode))
        QTimer.singleShot(0, lambda: _apply_native_glass(window, self._dark_mode))

    @Slot()
    def toggleQuickLauncher(self) -> None:
        if self._quick_popup.isVisible():
            self._quick_popup.hide()
        else:
            self._quick_popup.popup()


    @Slot()
    def showMain(self) -> None:
        self._quick_popup.hide()
        if self._main_window is not None:
            self._main_window.showNormal()
            self._main_window.raise_()
            self._main_window.requestActivate()

    @Slot()
    def hideMain(self) -> None:
        if self._main_window is not None:
            self._main_window.hide()

    @Slot()
    def minimizeMain(self) -> None:
        if self._main_window is not None:
            self._main_window.showMinimized()

    @Slot()
    def quitApplication(self) -> None:
        if self.tray_icon is not None:
            self.tray_icon.hide()
        self._hotkey_stop.set()
        self._quick_popup.hide()
        self.controller.detach_all()
        self.app.quit()

    @staticmethod
    def _glass_menu_style(dark: bool) -> str:
        text = "#F5F7FA" if dark else "#20242A"
        muted = "rgba(245,247,250,150)" if dark else "rgba(32,36,42,150)"
        return f"""
        QMenu {{
            color: {text};
            background: rgba(255, 255, 255, 18);
            border: 1px solid rgba(255, 255, 255, 42);
            border-radius: 14px;
            padding: 7px;
            font-family: 'Microsoft YaHei UI';
            font-size: 13px;
        }}
        QMenu::item {{
            min-width: 188px;
            padding: 8px 28px 8px 12px;
            border-radius: 9px;
            background: transparent;
        }}
        QMenu::item:selected {{ background: rgba(255, 255, 255, 28); }}
        QMenu::item:disabled {{ color: {muted}; }}
        QMenu::separator {{
            height: 1px;
            margin: 5px 8px;
            background: rgba(255, 255, 255, 26);
        }}
        QMenu::right-arrow {{ width: 7px; height: 10px; }}
        """

    def _configure_glass_menu(self, menu: QMenu) -> None:
        menu.setWindowFlags(
            Qt.WindowType.Popup
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint
        )
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        menu.setSeparatorsCollapsible(False)
        menu.setStyleSheet(self._glass_menu_style(self._dark_mode))
        # Apply blur only after the native popup HWND exists.
        menu.aboutToShow.connect(lambda m=menu: QTimer.singleShot(0, lambda: _apply_liquid_blur(m)))

    def _setup_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray_icon = QSystemTrayIcon(_app_icon(self._dark_mode))
        self.tray_menu = QMenu()
        self._configure_glass_menu(self.tray_menu)
        self.tray_icon.setContextMenu(self.tray_menu)
        self._refresh_tray_tooltip()
        # Qt's documented context-menu path handles right-click reliably on Windows.
        # The activated signal is kept only for left/double click.
        self.tray_icon.activated.connect(self._tray_activated)
        self._refresh_tray_menu()
        self.tray_icon.show()

    def _refresh_tray_menu(self) -> None:
        menu = self.tray_menu
        if menu is None:
            return
        menu.clear()
        menu.setStyleSheet(self._glass_menu_style(self._dark_mode))

        brand = QAction(_app_icon(self._dark_mode), "Clopen", menu)
        brand.setEnabled(False)
        menu.addAction(brand)
        menu.addSeparator()

        open_action = menu.addAction("打开主界面")
        open_action.triggered.connect(self.showMain)

        quick_menu = menu.addMenu("快速启动")
        self._configure_glass_menu(quick_menu)
        if self.groups:
            for group in self.groups:
                active = group.name in self.controller.active_groups
                action = quick_menu.addAction(f"{'关闭' if active else '开启'}  {group.name}")
                action.triggered.connect(
                    lambda _checked=False, group_name=group.name: self.toggleGroupByName(group_name)
                )
        else:
            empty = quick_menu.addAction("暂无组合")
            empty.setEnabled(False)

        menu.addSeparator()
        settings_action = menu.addAction("设置")
        settings_action.triggered.connect(self.showSettings)
        menu.addSeparator()
        quit_action = menu.addAction("退出 Clopen")
        quit_action.triggered.connect(self.quitApplication)

    def _refresh_tray_tooltip(self) -> None:
        if self.tray_icon is None:
            return
        count = len(self.controller.active_groups)
        self.tray_icon.setToolTip("Clopen" if not count else f"Clopen · {count} 个活动组合")

    def _tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self.showMain()


def _configure_application(app: QApplication) -> bool:
    app.setApplicationName("Clopen")
    app.setQuitOnLastWindowClosed(False)
    app.setProperty("clopenLiquidGlass", True)
    dark = app.styleHints().colorScheme() == Qt.ColorScheme.Dark
    app.setProperty("clopenDark", dark)
    app.setWindowIcon(_app_icon(dark))
    # Widget-based editors/software picker inherit the same glass visual system.
    app.setStyleSheet(LIQUID_DIALOG_STYLE)
    family = "Microsoft YaHei UI"
    if os.name == "nt":
        font_id = QFontDatabase.addApplicationFont(r"C:\Windows\Fonts\msyh.ttc")
        families = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
        if families:
            family = families[0]
    app.setFont(QFont(family, 10))
    return dark


def main() -> None:
    app = QApplication(sys.argv)
    _configure_application(app)
    engine = QQmlApplicationEngine()
    bridge = ClopenBridge(app, engine)
    engine.rootContext().setContextProperty("clopen", bridge)
    main_qml = _qml_dir() / "Main.qml"
    engine.load(QUrl.fromLocalFile(str(main_qml)))
    if not engine.rootObjects():
        raise SystemExit(2)
    root = engine.rootObjects()[0]
    if not isinstance(root, QQuickWindow):
        raise RuntimeError("Main.qml root must be a Window")
    bridge.set_main_window(root)
    root.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
