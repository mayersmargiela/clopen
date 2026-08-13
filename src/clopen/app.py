from __future__ import annotations

import ctypes
import copy
import os
import sys
from concurrent.futures import Future, ThreadPoolExecutor
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlparse

from PySide6.QtCore import QAbstractNativeEventFilter, QFileInfo, QPoint, QSettings, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QCursor, QFont, QFontDatabase, QIcon, QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFileIconProvider,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizeGrip,
    QSizePolicy,
    QStyle,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from .app_discovery import DiscoveredApp, discover_apps, search_discovered_apps
from .config import ConfigError, ConfigStore
from .hotkey import GlobalHotkey, HotkeyError
from .launcher import BatchController
from .models import AppEntry, AppGroup, LaunchReport


APP_STYLE = """
* {
    color: #202733;
    font-size: 13px;
}
QMainWindow#mainWindow, QWidget#windowHost {
    background: transparent;
    border: none;
}
QWidget#windowSurface {
    background: #EFF1F4;
    border: none;
    border-radius: 22px;
}
QFrame#sidebar {
    background: rgba(229, 232, 237, 232);
    border: 1px solid rgba(201, 206, 215, 190);
    border-radius: 16px;
}
QFrame#detailCard {
    background: rgba(247, 248, 250, 238);
    border: 1px solid rgba(207, 212, 220, 195);
    border-radius: 16px;
}
QFrame#quickSurface {
    background: #F1F3F6;
    border: none;
    border-radius: 16px;
}
QFrame#entryRow {
    background: rgba(235, 238, 243, 238);
    border: 1px solid rgba(207, 212, 220, 175);
    border-radius: 13px;
}
QLabel#brand { font-size: 24px; font-weight: 700; }
QLabel#eyebrow { color: #697487; font-size: 11px; font-weight: 650; }
QLabel#pageTitle { font-size: 22px; font-weight: 700; }
QLabel#muted { color: #626D7D; font-size: 12px; }
QLabel#entryName { font-weight: 600; }
QLabel#entryMeta { color: #687384; font-size: 11px; }
QLabel#statusDot {
    background: #7D8797;
    border-radius: 4px;
}
QLabel#statusDot[state="launching"] { background: #5B7CFF; }
QLabel#statusDot[state="active"] { background: #2CCB7F; }
QPushButton {
    background: transparent;
    border: 0;
    border-radius: 11px;
    padding: 9px 12px;
    text-align: left;
}
QPushButton:hover { background: rgba(215, 219, 226, 150); }
QPushButton:pressed { background: rgba(205, 211, 221, 190); }
QPushButton#groupButton { color: #536077; padding: 11px 12px; }
QPushButton#groupButton[selected="true"] {
    background: rgba(76, 111, 255, 25);
    border-left: 3px solid #4C6FFF;
    color: #202733;
    font-weight: 650;
}
QPushButton#primaryButton {
    color: white;
    background: #4C6FFF;
    border-radius: 13px;
    padding: 11px 20px;
    text-align: center;
    font-weight: 650;
}
QPushButton#primaryButton:hover { background: #3E61EF; }
QPushButton#primaryButton[danger="true"] { background: #DB5664; }
QPushButton#primaryButton[danger="true"]:hover { background: #C84957; }
QPushButton#primaryButton:disabled { background: #C7CCD5; color: #F4F5F7; }
QPushButton#iconButton {
    color: #606B7D;
    background: rgba(220, 224, 230, 165);
    border-radius: 10px;
    padding: 7px 10px;
    text-align: center;
}
QPushButton#iconButton:hover { background: rgba(207, 212, 220, 220); color: #202733; }
QPushButton#quietButton { color: #626E80; padding: 8px 10px; }
QPushButton#quietButton:hover { color: #273142; }
QScrollArea { background: transparent; border: 0; }
QScrollArea QWidget { background: transparent; }
QScrollBar:vertical { width: 7px; background: transparent; margin: 5px 0; }
QScrollBar::handle:vertical { background: rgba(104, 116, 134, 75); border-radius: 3px; min-height: 24px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
QDialog { background: #EEF0F3; }
QLineEdit, QComboBox, QListWidget {
    background: rgba(247, 248, 250, 245);
    border: 1px solid #D0D5DD;
    border-radius: 9px;
    padding: 8px 10px;
    selection-background-color: #4C6FFF;
}
QLineEdit:focus, QComboBox:focus, QListWidget:focus { border: 1px solid #4C6FFF; }
QCheckBox { spacing: 8px; }
QDialogButtonBox QPushButton {
    background: #DDE1E7;
    border-radius: 9px;
    padding: 8px 18px;
    text-align: center;
}
QDialogButtonBox QPushButton:hover { background: #D2D7DF; }
QMenu {
    background: #F1F3F6;
    border: none;
    border-radius: 10px;
    padding: 6px;
}
QMenu::item { padding: 8px 26px 8px 12px; border-radius: 6px; }
QMenu::item:selected { background: #E0E5ED; }
QMenu::separator { height: 1px; background: #D9DEE6; margin: 5px 8px; }
"""

DARK_STYLE = """
* { color: #E7EBF2; }
QWidget#windowSurface {
    background: #141821;
    border: none;
}
QFrame#sidebar {
    background: rgba(36, 42, 56, 205);
    border-color: rgba(255, 255, 255, 22);
}
QFrame#detailCard, QFrame#entryRow {
    background: rgba(46, 52, 66, 186);
    border-color: rgba(255, 255, 255, 20);
}
QFrame#quickSurface {
    background: #171C24;
    border: none;
}
QLabel#eyebrow, QLabel#muted, QLabel#entryMeta { color: #AAB4C4; }
QLabel#statusDot { background: #596273; }
QLabel#statusDot[state="launching"] { background: #6E88FF; }
QLabel#statusDot[state="active"] { background: #31D887; }
QPushButton:hover { background: rgba(255, 255, 255, 18); }
QPushButton:pressed { background: rgba(255, 255, 255, 28); }
QPushButton#groupButton { color: #B6C0CF; }
QPushButton#groupButton[selected="true"] {
    background: rgba(91, 121, 255, 25);
    border-left-color: #718CFF;
    color: #F4F6FA;
}
QPushButton#iconButton { color: #B3BDCB; background: rgba(255, 255, 255, 10); }
QPushButton#iconButton:hover { color: #FFFFFF; background: rgba(255, 255, 255, 22); }
QPushButton#quietButton { color: #AEB8C8; }
QPushButton#quietButton:hover { color: #FFFFFF; }
QScrollBar::handle:vertical { background: rgba(204, 214, 230, 60); }
QDialog { background: #171C26; }
QLineEdit, QComboBox, QListWidget {
    background: rgba(45, 52, 67, 235);
    border-color: #3B4558;
    color: #F0F3F8;
}
QDialogButtonBox QPushButton { background: #2E3646; color: #E7EBF2; }
QDialogButtonBox QPushButton:hover { background: #394355; }
QMenu { background: #171C24; border: none; border-radius: 10px; padding: 6px; }
QMenu::item:selected { background: #293140; }
QMenu::separator { background: #323A48; }
"""


def _clear_layout(layout: QVBoxLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget is not None:
            widget.deleteLater()


def _set_dynamic_property(widget: QWidget, name: str, value: object) -> None:
    widget.setProperty(name, value)
    widget.style().unpolish(widget)
    widget.style().polish(widget)


def _resource_file(name: str) -> Path:
    """Return a bundled Clopen resource both from source and PyInstaller builds."""
    bundle_root = getattr(sys, "_MEIPASS", None)
    if bundle_root:
        bundled = Path(bundle_root) / "clopen" / "resources" / name
        if bundled.exists():
            return bundled
    return Path(__file__).resolve().parent / "resources" / name


def _brand_lockup_icon(dark: bool) -> QIcon:
    """Full Clopen brand lockup supplied by the designer (mark + word + tagline)."""
    name = "clopen-brand-white.svg" if dark else "clopen-brand-black.svg"
    return QIcon(str(_resource_file(name)))


def _app_icon(dark: bool | None = None) -> QIcon:
    """Square app/tray icon with a stable background for taskbar legibility."""
    if dark is None:
        app = QApplication.instance()
        dark = bool(app.property("clopenDark")) if app is not None else True
    name = "clopen-icon-dark.png" if dark else "clopen-icon-light.png"
    return QIcon(str(_resource_file(name)))


def group_matches(group: AppGroup, query: str) -> bool:
    needle = query.strip().casefold()
    if not needle:
        return True
    values = [group.name]
    for entry in group.entries:
        values.extend((entry.name, entry.path, entry.url))
    return any(needle in value.casefold() for value in values if value)


_CATALOG_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="clopen-software-catalog")
_catalog_future: Future[list[DiscoveredApp]] | None = None


def _ensure_catalog_future() -> Future[list[DiscoveredApp]]:
    """Start local software discovery once and reuse it across picker openings."""
    global _catalog_future
    needs_new = _catalog_future is None or _catalog_future.cancelled()
    if _catalog_future is not None and _catalog_future.done() and not _catalog_future.cancelled():
        needs_new = _catalog_future.exception() is not None
    if needs_new:
        _catalog_future = _CATALOG_EXECUTOR.submit(discover_apps)
    return _catalog_future


def _apply_windows_backdrop(widget: QWidget, backdrop: int = 2) -> None:
    """Ask Windows 11 for a Mica/Acrylic system backdrop; fail quietly elsewhere."""
    if os.name != "nt" or os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        return
    try:
        hwnd = ctypes.c_void_p(int(widget.winId()))
        value = ctypes.c_int(backdrop)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, 38, ctypes.byref(value), ctypes.sizeof(value))
    except (AttributeError, OSError, TypeError, ValueError):
        pass


def _configure_borderless_menu(menu: QMenu, dark: bool) -> None:
    """Use a pure Qt popup instead of the Windows tray context-menu frame."""
    menu.setWindowFlags(
        Qt.WindowType.Popup
        | Qt.WindowType.FramelessWindowHint
        | Qt.WindowType.NoDropShadowWindowHint
    )
    menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
    menu.setSeparatorsCollapsible(False)
    _set_windows_dark_mode(menu, dark)
    _remove_windows_border(menu)


class TitleBar(QFrame):
    def __init__(self, window: "MainWindow"):
        super().__init__()
        self.window = window
        self._drag_origin: QPoint | None = None
        self.setFixedHeight(64)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(22, 10, 18, 10)
        layout.setSpacing(6)
        # Use the supplied lockup as one immutable brand unit. This preserves the
        # designer-defined proportions between the C/O mark, "Clopen" and the tagline.
        self.logo = QLabel()
        self.logo.setFixedSize(179, 44)
        self.logo.setPixmap(_brand_lockup_icon(window.dark_mode).pixmap(179, 44))
        self.logo.setToolTip("Clopen")
        layout.addWidget(self.logo, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addStretch()

        theme_button = QPushButton("浅色" if window.dark_mode else "深色")
        theme_button.setObjectName("iconButton")
        theme_button.setToolTip("切换亮色 / 暗色模式")
        theme_button.clicked.connect(window.toggle_dark_mode)
        window.theme_button = theme_button
        reload_button = QPushButton("刷新")
        reload_button.setObjectName("iconButton")
        reload_button.setToolTip("重新载入配置")
        reload_button.clicked.connect(window.reload)
        minimize_button = QPushButton("—")
        minimize_button.setObjectName("iconButton")
        minimize_button.clicked.connect(window.showMinimized)
        close_button = QPushButton("×")
        close_button.setObjectName("iconButton")
        close_button.setToolTip("隐藏到后台")
        close_button.clicked.connect(window.hide)
        theme_button.setFixedSize(48, 34)
        reload_button.setFixedSize(48, 34)
        for button in (minimize_button, close_button):
            button.setFixedSize(36, 34)
        for button in (theme_button, reload_button, minimize_button, close_button):
            layout.addWidget(button)

    def update_logo(self, dark: bool) -> None:
        self.logo.setPixmap(_brand_lockup_icon(dark).pixmap(179, 44))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = event.globalPosition().toPoint() - self.window.frameGeometry().topLeft()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_origin is not None and event.buttons() & Qt.MouseButton.LeftButton:
            self.window.move(event.globalPosition().toPoint() - self._drag_origin)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._drag_origin = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self.window.showNormal() if self.window.isMaximized() else self.window.showMaximized()
        super().mouseDoubleClickEvent(event)


class QuickMenu(QWidget):
    def __init__(self, owner: "MainWindow"):
        super().__init__(
            None,
            Qt.WindowType.Popup
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.NoDropShadowWindowHint,
        )
        self.owner = owner
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFixedWidth(360)
        self.group_buttons: list[tuple[QPushButton, AppGroup]] = []
        self.surface = QFrame(self)
        self.surface.setObjectName("quickSurface")
        self.layout = QVBoxLayout(self.surface)
        self.layout.setContentsMargins(14, 14, 14, 14)
        self.layout.setSpacing(5)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(self.surface)

    def rebuild(self) -> None:
        _clear_layout(self.layout)
        self.group_buttons = []
        heading = QLabel("快速操作")
        heading.setObjectName("eyebrow")
        self.layout.addWidget(heading)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索组合或软件…")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._filter_groups)
        self.search_edit.returnPressed.connect(self._run_first_result)
        self.layout.addWidget(self.search_edit)
        groups = sorted(
            self.owner.groups,
            key=lambda item: (item.name not in self.owner.controller.active_groups, item.name.casefold()),
        )
        for group in groups:
            active = group.name in self.owner.controller.active_groups
            button = QPushButton(f"{'关闭' if active else '开启'}  {group.name}")
            button.clicked.connect(lambda _checked=False, item=group: self._run(item))
            self.layout.addWidget(button)
            self.group_buttons.append((button, group))
        self.empty_label = QLabel("没有可用组合")
        self.empty_label.setObjectName("muted")
        self.empty_label.setContentsMargins(10, 10, 10, 10)
        self.empty_label.setVisible(not groups)
        self.layout.addWidget(self.empty_label)
        self.layout.addSpacing(4)
        self.layout.addWidget(self._action("打开主界面", self.owner.reveal))
        self.layout.addWidget(self._action("退出 Clopen", self.owner.quit_application))
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
                self._run(group)
                return

    @staticmethod
    def _action(text: str, callback: Callable[[], None]) -> QPushButton:
        button = QPushButton(text)
        button.setObjectName("quietButton")
        button.clicked.connect(callback)
        return button

    def _run(self, group: AppGroup) -> None:
        self.hide()
        self.owner.select_group(group.name)
        if group.name in self.owner.controller.active_groups:
            self.owner.close_selected()
        else:
            self.owner.start_selected()

    def popup(self) -> None:
        self.rebuild()
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        available = screen.availableGeometry()
        point = QCursor.pos() + QPoint(12, 12)
        point.setX(min(point.x(), available.right() - self.width()))
        point.setY(min(point.y(), available.bottom() - self.height()))
        point.setX(max(point.x(), available.left()))
        point.setY(max(point.y(), available.top()))
        self.move(point)
        _set_windows_dark_mode(self, self.owner.dark_mode)
        self.show()
        self.raise_()
        # The native HWND exists only after show(); remove any DWM outline then.
        QTimer.singleShot(0, lambda: _remove_windows_border(self))
        self.search_edit.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def focusOutEvent(self, event) -> None:
        self.hide()
        super().focusOutEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            return
        super().keyPressEvent(event)


class HotkeyNativeFilter(QAbstractNativeEventFilter):
    def __init__(self, hotkey: GlobalHotkey):
        super().__init__()
        self.hotkey = hotkey

    def nativeEventFilter(self, event_type, message):
        try:
            handled = self.hotkey.matches_native_message(int(message))
        except (TypeError, ValueError):
            handled = False
        return handled, 0


class SoftwarePickerDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        apps: list[DiscoveredApp] | None = None,
        *,
        catalog_future: Future[list[DiscoveredApp]] | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("添加软件")
        self.resize(680, 560)
        self.apps = list(apps) if apps is not None else []
        self.visible_apps: list[DiscoveredApp] = []
        self.manual_requested = False
        self.catalog_error = ""
        self._catalog_future = None if apps is not None else (catalog_future or _ensure_catalog_future())
        self._catalog_timer: QTimer | None = None
        self._icon_provider = QFileIconProvider()
        self._fallback_icon: QIcon | None = None

        layout = QVBoxLayout(self)
        heading = QLabel("本机软件库")
        heading.setObjectName("pageTitle")
        hint = QLabel("只显示可直接启动的软件 · 搜索名称，双击加入当前组合")
        hint.setObjectName("muted")
        layout.addWidget(heading)
        layout.addWidget(hint)
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索软件，例如：微信、Photoshop、Steam…")
        self.search_edit.setClearButtonEnabled(True)
        self.search_edit.textChanged.connect(self._filter)
        self.search_edit.returnPressed.connect(self._accept_selected)
        layout.addWidget(self.search_edit)
        self.app_list = QListWidget()
        self.app_list.setIconSize(QSize(34, 34))
        self.app_list.setSpacing(2)
        self.app_list.setUniformItemSizes(True)
        self.app_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.app_list.setTextElideMode(Qt.TextElideMode.ElideRight)
        self.app_list.itemDoubleClicked.connect(lambda _item: self._accept_selected())
        layout.addWidget(self.app_list, 1)
        self.count_label = QLabel("")
        self.count_label.setObjectName("muted")
        layout.addWidget(self.count_label)
        actions = QHBoxLayout()
        manual = QPushButton("＋ 手动添加其他启动项")
        manual.setObjectName("quietButton")
        manual.clicked.connect(self._choose_manual)
        cancel = QPushButton("取消")
        cancel.setObjectName("quietButton")
        cancel.clicked.connect(self.reject)
        choose = QPushButton("添加所选软件")
        choose.setObjectName("primaryButton")
        choose.clicked.connect(self._accept_selected)
        actions.addWidget(manual)
        actions.addStretch()
        actions.addWidget(cancel)
        actions.addWidget(choose)
        layout.addLayout(actions)
        if self._catalog_future is None:
            self._filter("")
        else:
            self._show_loading_state()
            self._catalog_timer = QTimer(self)
            self._catalog_timer.setInterval(80)
            self._catalog_timer.timeout.connect(self._poll_catalog)
            self._catalog_timer.start()
            QTimer.singleShot(0, self._poll_catalog)
        self.search_edit.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def _filter(self, query: str) -> None:
        if self._catalog_future is not None:
            if not self._catalog_future.done():
                self._show_loading_state()
                return
            self._poll_catalog()
            return

        self.visible_apps = search_discovered_apps(self.apps, query)
        self.app_list.clear()
        for app in self.visible_apps:
            item = QListWidgetItem(self._icon_for(app), app.name)
            item.setSizeHint(QSize(0, 48))
            item.setToolTip(app.detail)
            self.app_list.addItem(item)
        if self.visible_apps:
            self.app_list.setCurrentRow(0)
        if self.catalog_error:
            self.count_label.setText("软件库读取失败，可使用手动添加")
        elif self.visible_apps:
            self.count_label.setText(f"{len(self.visible_apps)} 个软件")
        elif query.strip():
            self.count_label.setText("没有找到匹配的软件，可使用手动添加")
        else:
            self.count_label.setText("没有发现可用软件，可使用手动添加")

    def _show_loading_state(self) -> None:
        self.visible_apps = []
        self.app_list.clear()
        loading = QListWidgetItem("正在读取本机软件库…")
        loading.setFlags(Qt.ItemFlag.NoItemFlags)
        loading.setSizeHint(QSize(0, 48))
        self.app_list.addItem(loading)
        self.count_label.setText("正在扫描开始菜单和 Windows 应用")

    def _poll_catalog(self) -> None:
        future = self._catalog_future
        if future is None or not future.done():
            return
        if self._catalog_timer is not None:
            self._catalog_timer.stop()
        try:
            self.apps = list(future.result())
        except Exception as exc:  # discovery should not make the editor unusable
            self.apps = []
            self.catalog_error = str(exc)
        self._catalog_future = None
        self._filter(self.search_edit.text())

    def _icon_for(self, app: DiscoveredApp) -> QIcon:
        if app.path:
            icon = self._icon_provider.icon(QFileInfo(app.path))
            if not icon.isNull():
                return icon
        if self._fallback_icon is None:
            self._fallback_icon = QApplication.style().standardIcon(QStyle.StandardPixmap.SP_DesktopIcon)
        return self._fallback_icon

    def _accept_selected(self) -> None:
        if 0 <= self.app_list.currentRow() < len(self.visible_apps):
            self.accept()

    def _choose_manual(self) -> None:
        self.manual_requested = True
        self.accept()

    def result_app(self) -> DiscoveredApp | None:
        row = self.app_list.currentRow()
        if self.manual_requested or row < 0 or row >= len(self.visible_apps):
            return None
        return self.visible_apps[row]


class EntryEditorDialog(QDialog):
    TYPES = ("应用", "网址", "文件", "文件夹", "UWP")

    def __init__(self, parent: QWidget, entry: AppEntry | None = None):
        super().__init__(parent)
        self.setWindowTitle("编辑启动项" if entry else "添加启动项")
        self.setMinimumWidth(520)
        source = copy.deepcopy(entry) if entry else AppEntry(run_as_admin=True)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(11)
        self.name_edit = QLineEdit(source.name)
        self.type_combo = QComboBox()
        self.type_combo.addItems(self.TYPES)
        self.type_combo.setCurrentText(self._type_for(source))
        self.path_edit = QLineEdit(source.path)
        self.path_edit.setPlaceholderText("程序、文件、文件夹路径或 UWP AppUserModelId")
        self.browse_button = QPushButton("浏览…")
        self.browse_button.setObjectName("quietButton")
        self.browse_button.clicked.connect(self._browse)
        path_row = QHBoxLayout()
        path_row.addWidget(self.path_edit, 1)
        path_row.addWidget(self.browse_button)
        self.url_edit = QLineEdit(source.url)
        self.url_edit.setPlaceholderText("https://example.com（可选）")
        self.args_edit = QLineEdit(source.arguments)
        self.args_edit.setPlaceholderText("可选启动参数")
        self.cwd_edit = QLineEdit(source.working_dir)
        self.cwd_edit.setPlaceholderText("可选工作目录")
        self.admin_check = QCheckBox("以管理员身份启动（推荐）")
        self.admin_check.setChecked(source.run_as_admin)
        form.addRow("名称", self.name_edit)
        form.addRow("类型", self.type_combo)
        form.addRow("路径 / ID", path_row)
        form.addRow("网址", self.url_edit)
        form.addRow("启动参数", self.args_edit)
        form.addRow("工作目录", self.cwd_edit)
        form.addRow("权限", self.admin_check)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("保存")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.type_combo.currentTextChanged.connect(self._sync_fields)
        self._sync_fields()

    @staticmethod
    def _type_for(entry: AppEntry) -> str:
        if entry.is_uwp:
            return "UWP"
        if entry.is_folder:
            return "文件夹"
        if entry.is_file:
            return "文件"
        if entry.url and not entry.path:
            return "网址"
        return "应用"

    def _sync_fields(self) -> None:
        kind = self.type_combo.currentText()
        is_url = kind == "网址"
        is_app = kind == "应用"
        self.path_edit.setEnabled(not is_url)
        self.browse_button.setEnabled(kind in {"应用", "文件", "文件夹"})
        self.url_edit.setEnabled(is_url or is_app)
        self.args_edit.setEnabled(is_app)
        self.cwd_edit.setEnabled(is_app)
        self.admin_check.setEnabled(is_app)

    def _browse(self) -> None:
        kind = self.type_combo.currentText()
        if kind == "文件夹":
            value = QFileDialog.getExistingDirectory(self, "选择文件夹", self.path_edit.text())
        else:
            caption = "选择程序" if kind == "应用" else "选择文件"
            file_filter = "程序 (*.exe);;所有文件 (*)" if kind == "应用" else "所有文件 (*)"
            value, _ = QFileDialog.getOpenFileName(self, caption, self.path_edit.text(), file_filter)
        if value:
            self.path_edit.setText(value)
            if not self.name_edit.text().strip():
                self.name_edit.setText(Path(value).stem)

    def accept(self) -> None:
        name = self.name_edit.text().strip()
        kind = self.type_combo.currentText()
        path = self.path_edit.text().strip()
        url = self.url_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "缺少名称", "请填写启动项名称。")
            return
        if kind != "网址" and not path:
            QMessageBox.warning(self, "缺少路径", "请填写路径或 UWP AppUserModelId。")
            return
        if kind == "网址" or (kind == "应用" and url):
            parsed = urlparse(url)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                QMessageBox.warning(self, "网址无效", "请输入完整的 http:// 或 https:// 网址。")
                return
        super().accept()

    def result_entry(self) -> AppEntry:
        kind = self.type_combo.currentText()
        is_app = kind == "应用"
        is_url = kind == "网址"
        return AppEntry(
            name=self.name_edit.text().strip(),
            path="" if is_url else self.path_edit.text().strip(),
            arguments=self.args_edit.text().strip() if is_app else "",
            working_dir=self.cwd_edit.text().strip() if is_app else "",
            url=self.url_edit.text().strip() if (is_app or is_url) else "",
            is_uwp=kind == "UWP",
            is_folder=kind == "文件夹",
            is_file=kind == "文件",
            run_as_admin=self.admin_check.isChecked() if is_app else False,
        )


class GroupEditorDialog(QDialog):
    def __init__(
        self,
        parent: QWidget,
        group: AppGroup | None = None,
        *,
        reserved_names: set[str] | None = None,
    ):
        super().__init__(parent)
        self.setWindowTitle("编辑组合" if group else "新建组合")
        self.resize(640, 470)
        self.entries = copy.deepcopy(group.entries) if group else []
        self.reserved_names = {name.casefold() for name in (reserved_names or set())}

        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name_edit = QLineEdit(group.name if group else "")
        self.name_edit.setPlaceholderText("例如：直播、工作、游戏")
        form.addRow("组合名称", self.name_edit)
        layout.addLayout(form)
        title_row = QHBoxLayout()
        title = QLabel("启动项与顺序")
        title.setObjectName("eyebrow")
        title_row.addWidget(title)
        title_row.addStretch()
        add_button = QPushButton("＋ 添加软件")
        add_button.setObjectName("quietButton")
        add_button.clicked.connect(self._add_entry)
        title_row.addWidget(add_button)
        layout.addLayout(title_row)
        self.entry_list = QListWidget()
        self.entry_list.itemDoubleClicked.connect(lambda _item: self._edit_entry())
        layout.addWidget(self.entry_list, 1)
        action_row = QHBoxLayout()
        for text, callback in (
            ("编辑", self._edit_entry),
            ("删除", self._delete_entry),
            ("上移", lambda: self._move_entry(-1)),
            ("下移", lambda: self._move_entry(1)),
        ):
            button = QPushButton(text)
            button.setObjectName("quietButton")
            button.clicked.connect(callback)
            action_row.addWidget(button)
        action_row.addStretch()
        layout.addLayout(action_row)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("保存")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self._refresh_entries()

    def _refresh_entries(self, selected: int | None = None) -> None:
        self.entry_list.clear()
        for index, entry in enumerate(self.entries, start=1):
            kind = EntryEditorDialog._type_for(entry)
            mode = "外部启动" if entry.is_external else "Clopen 管理"
            self.entry_list.addItem(f"{index}.  {entry.name}    ·    {kind} / {mode}")
        if self.entries:
            row = min(selected if selected is not None else 0, len(self.entries) - 1)
            self.entry_list.setCurrentRow(max(0, row))

    def _add_entry(self) -> None:
        picker = SoftwarePickerDialog(self)
        if picker.exec() != QDialog.DialogCode.Accepted:
            return
        app = picker.result_app()
        if app is not None:
            self.entries.append(app.to_entry())
            self._refresh_entries(len(self.entries) - 1)
            return
        dialog = EntryEditorDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.entries.append(dialog.result_entry())
            self._refresh_entries(len(self.entries) - 1)

    def _edit_entry(self) -> None:
        row = self.entry_list.currentRow()
        if row < 0:
            return
        dialog = EntryEditorDialog(self, self.entries[row])
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.entries[row] = dialog.result_entry()
            self._refresh_entries(row)

    def _delete_entry(self) -> None:
        row = self.entry_list.currentRow()
        if row < 0:
            return
        self.entries.pop(row)
        self._refresh_entries(max(0, row - 1))

    def _move_entry(self, offset: int) -> None:
        row = self.entry_list.currentRow()
        target = row + offset
        if row < 0 or target < 0 or target >= len(self.entries):
            return
        self.entries[row], self.entries[target] = self.entries[target], self.entries[row]
        self._refresh_entries(target)

    def accept(self) -> None:
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "缺少名称", "请填写组合名称。")
            return
        if name.casefold() in self.reserved_names:
            QMessageBox.warning(self, "名称已存在", "组合名称不能重复。")
            return
        super().accept()

    def result_group(self) -> AppGroup:
        return AppGroup(name=self.name_edit.text().strip(), entries=copy.deepcopy(self.entries))


class SettingsDialog(QDialog):
    def __init__(self, owner: "MainWindow"):
        super().__init__(owner)
        self.owner = owner
        self.setWindowTitle("Clopen 设置")
        self.setMinimumWidth(390)
        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setHorizontalSpacing(18)
        form.setVerticalSpacing(12)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["浅色", "深色"])
        self.theme_combo.setCurrentText("深色" if owner.dark_mode else "浅色")
        form.addRow("外观", self.theme_combo)
        hotkey = QLabel("Ctrl + Shift + E")
        hotkey.setObjectName("muted")
        form.addRow("快速呼出", hotkey)
        tray_note = QLabel("关闭主界面后，Clopen 会继续驻留在系统托盘")
        tray_note.setObjectName("muted")
        tray_note.setWordWrap(True)
        form.addRow("后台运行", tray_note)
        layout.addLayout(form)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("保存")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("取消")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def accept(self) -> None:
        self.owner.set_dark_mode(self.theme_combo.currentText() == "深色")
        super().accept()


class MainWindow(QMainWindow):
    def __init__(self, *, register_hotkey: bool = True):
        super().__init__()
        self.store = ConfigStore()
        self.controller = BatchController()
        self.dark_mode = bool(QApplication.instance().property("clopenDark"))
        self.groups: list[AppGroup] = []
        self.selected_index = -1
        self.hotkey = GlobalHotkey(self.toggle_quick_menu)
        self.hotkey_filter = HotkeyNativeFilter(self.hotkey)
        QApplication.instance().installNativeEventFilter(self.hotkey_filter)

        self.setObjectName("mainWindow")
        self.setWindowTitle("Clopen")
        self.setWindowIcon(_app_icon(self.dark_mode))
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Window
            | Qt.WindowType.NoDropShadowWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.resize(920, 600)
        self.setMinimumSize(780, 520)
        self._build_ui()
        self.quick_menu = QuickMenu(self)
        self.tray_icon: QSystemTrayIcon | None = None
        self.tray_menu: QMenu | None = None
        self._setup_system_tray()
        self.reload(silent=True)

        if register_hotkey:
            try:
                self.hotkey.register()
            except HotkeyError as exc:
                self.set_status(str(exc), error=True)

        QTimer.singleShot(0, self._apply_window_effects)
        # Warm the local app catalog after the window appears, so “添加软件”
        # normally opens with results already available instead of blocking.
        QTimer.singleShot(180, _ensure_catalog_future)

    def _apply_window_effects(self) -> None:
        # The main window owns its exact rounded shape. Native DWM corner rendering
        # and drop shadows are disabled because they can leak a gray under-layer at
        # the four corners on Windows 11.
        _apply_windows_backdrop(self, 1)
        _disable_windows_round_corners(self)
        _set_windows_dark_mode(self, self.dark_mode)
        _remove_windows_border(self)
        _apply_windows_round_region(self, 22)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        # Keep the native window region in lockstep with the QSS 22 px radius.
        if self.isVisible():
            _apply_windows_round_region(self, 22)

    def changeEvent(self, event) -> None:
        super().changeEvent(event)
        # Maximizing/restoring changes the required region shape.
        QTimer.singleShot(0, lambda: _apply_windows_round_region(self, 22))

    def _build_ui(self) -> None:
        host = QWidget()
        host.setObjectName("windowHost")
        host_layout = QVBoxLayout(host)
        # The main window deliberately has no outer stroke, halo or shadow gutter.
        # The rounded surface reaches the native window edge exactly.
        host_layout.setContentsMargins(0, 0, 0, 0)
        surface = QFrame()
        surface.setObjectName("windowSurface")
        host_layout.addWidget(surface)
        self.setCentralWidget(host)

        root = QVBoxLayout(surface)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.title_bar = TitleBar(self)
        root.addWidget(self.title_bar)
        body = QHBoxLayout()
        body.setContentsMargins(18, 8, 18, 18)
        body.setSpacing(18)
        root.addLayout(body, 1)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(232)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(14, 16, 14, 14)
        side.setSpacing(8)
        side_heading = QHBoxLayout()
        side_title = QLabel("软件组合")
        side_title.setObjectName("eyebrow")
        side_heading.addWidget(side_title)
        side_heading.addStretch()
        new_group_button = QPushButton("＋ 新建")
        new_group_button.setObjectName("quietButton")
        new_group_button.clicked.connect(self.new_group)
        side_heading.addWidget(new_group_button)
        side.addLayout(side_heading)
        self.group_search = QLineEdit()
        self.group_search.setPlaceholderText("搜索组合或软件…")
        self.group_search.setClearButtonEnabled(True)
        self.group_search.textChanged.connect(self._search_groups)
        self.group_search.returnPressed.connect(self._run_primary_action)
        side.addWidget(self.group_search)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        self.group_host = QWidget()
        self.group_layout = QVBoxLayout(self.group_host)
        self.group_layout.setContentsMargins(0, 4, 0, 4)
        self.group_layout.setSpacing(5)
        self.group_layout.addStretch()
        scroll.setWidget(self.group_host)
        side.addWidget(scroll, 1)
        edit_row = QHBoxLayout()
        self.edit_group_button = QPushButton("编辑组合")
        self.edit_group_button.setObjectName("quietButton")
        self.edit_group_button.clicked.connect(self.edit_selected_group)
        self.delete_group_button = QPushButton("删除")
        self.delete_group_button.setObjectName("quietButton")
        self.delete_group_button.clicked.connect(self.delete_selected_group)
        edit_row.addWidget(self.edit_group_button)
        edit_row.addWidget(self.delete_group_button)
        side.addLayout(edit_row)
        close_all = QPushButton("关闭全部活动会话")
        close_all.setObjectName("quietButton")
        close_all.clicked.connect(self.close_all)
        self.close_all_button = close_all
        side.addWidget(close_all)
        body.addWidget(sidebar)

        content = QVBoxLayout()
        content.setSpacing(14)
        body.addLayout(content, 1)
        header = QHBoxLayout()
        header.setSpacing(6)
        title_area = QVBoxLayout()
        title_area.setSpacing(3)
        self.group_title = QLabel("选择一个组合")
        self.group_title.setObjectName("pageTitle")
        self.group_meta = QLabel("从左侧选择要开启的软件环境")
        self.group_meta.setObjectName("muted")
        title_area.addWidget(self.group_title)
        title_area.addWidget(self.group_meta)
        header.addLayout(title_area)
        header.addStretch()

        # Status is deliberately a tiny indicator rather than a third button:
        # grey = inactive, blue = launching, green = active.
        self.status_dot = QLabel()
        self.status_dot.setObjectName("statusDot")
        self.status_dot.setFixedSize(8, 8)
        self.status_dot.setToolTip("当前未启动")
        self.status_dot.setProperty("state", "inactive")
        header.addWidget(self.status_dot, alignment=Qt.AlignmentFlag.AlignVCenter)
        header.addSpacing(4)
        self.primary_button = QPushButton("开启组合")
        self.primary_button.setObjectName("primaryButton")
        self.primary_button.clicked.connect(self._run_primary_action)
        self.primary_button.setFixedSize(132, 44)
        header.addWidget(self.primary_button, alignment=Qt.AlignmentFlag.AlignTop)
        content.addLayout(header)

        card = QFrame()
        card.setObjectName("detailCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(14, 14, 14, 14)
        card_layout.setSpacing(8)
        self.entry_host = QWidget()
        self.entry_layout = QVBoxLayout(self.entry_host)
        self.entry_layout.setContentsMargins(0, 0, 0, 0)
        self.entry_layout.setSpacing(7)
        self.entry_layout.addStretch()
        entry_scroll = QScrollArea()
        entry_scroll.setWidgetResizable(True)
        entry_scroll.setWidget(self.entry_host)
        card_layout.addWidget(entry_scroll)
        content.addWidget(card, 1)

        footer = QHBoxLayout()
        self.source_label = QLabel("")
        self.source_label.setObjectName("muted")
        self.message_label = QLabel("")
        self.message_label.setObjectName("muted")
        footer.addWidget(self.source_label)
        footer.addStretch()
        footer.addWidget(self.message_label)
        footer.addWidget(QSizeGrip(self), alignment=Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight)
        content.addLayout(footer)

    def reload(self, _checked: bool = False, *, silent: bool = False) -> None:
        selected_name = self.selected_group().name if self.selected_group() else None
        try:
            self.groups = self.store.load()
        except ConfigError as exc:
            self.groups = []
            if not silent:
                QMessageBox.critical(self, "配置读取失败", str(exc))
            self.set_status(str(exc), error=True)
        self._render_groups(selected_name)
        self.source_label.setText("Clopen 配置  ·  Ctrl + Shift + E")
        self.set_status(f"{len(self.groups)} 个组合 · {len(self.controller.active_groups)} 个活动会话")
        self._refresh_tray_menu()

    def _render_groups(self, selected_name: str | None = None) -> None:
        _clear_layout(self.group_layout)
        query = self.group_search.text() if hasattr(self, "group_search") else ""
        matches = [(index, group) for index, group in enumerate(self.groups) if group_matches(group, query)]
        if matches:
            matching_names = [group.name for _, group in matches]
            self.selected_index = (
                next(index for index, group in matches if group.name == selected_name)
                if selected_name in matching_names
                else matches[0][0]
            )
            for index, group in matches:
                active = group.name in self.controller.active_groups
                button = QPushButton(f"{'●' if active else '○'}   {group.name}\n      {len(group.entries)} 个启动项")
                button.setObjectName("groupButton")
                button.setProperty("groupIndex", index)
                button.setProperty("selected", index == self.selected_index)
                button.clicked.connect(lambda _checked=False, row=index: self.select_index(row))
                self.group_layout.addWidget(button)
        else:
            self.selected_index = -1
            text = "没有搜索结果\n换个组合名或软件名试试" if query.strip() else "还没有组合\n点击“新建”创建第一个组合"
            empty = QLabel(text)
            empty.setObjectName("muted")
            empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.group_layout.addWidget(empty)
        self.group_layout.addStretch()
        self.render_selected()

    def selected_group(self) -> AppGroup | None:
        if 0 <= self.selected_index < len(self.groups):
            return self.groups[self.selected_index]
        return None

    def select_group(self, name: str) -> None:
        for index, group in enumerate(self.groups):
            if group.name == name:
                self.select_index(index)
                return

    def select_index(self, index: int) -> None:
        self.selected_index = index
        for row in range(self.group_layout.count()):
            widget = self.group_layout.itemAt(row).widget()
            if isinstance(widget, QPushButton) and widget.objectName() == "groupButton":
                _set_dynamic_property(widget, "selected", widget.property("groupIndex") == index)
        self.render_selected()

    def _search_groups(self, _query: str) -> None:
        selected = self.selected_group()
        self._render_groups(selected.name if selected else None)

    def new_group(self) -> None:
        dialog = GroupEditorDialog(self, reserved_names={group.name for group in self.groups})
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        group = dialog.result_group()
        candidate = copy.deepcopy(self.groups)
        candidate.append(group)
        if self._save_groups(candidate):
            self.reload(silent=True)
            self.select_group(group.name)

    def edit_selected_group(self) -> None:
        group = self.selected_group()
        if group is None:
            return
        if group.name in self.controller.active_groups:
            QMessageBox.information(self, "组合正在运行", "请先关闭该组合，再进行编辑。")
            return
        reserved = {item.name for item in self.groups if item is not group}
        dialog = GroupEditorDialog(self, group, reserved_names=reserved)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        edited = dialog.result_group()
        candidate = copy.deepcopy(self.groups)
        candidate[self.selected_index] = edited
        if self._save_groups(candidate):
            self.reload(silent=True)
            self.select_group(edited.name)

    def delete_selected_group(self) -> None:
        group = self.selected_group()
        if group is None:
            return
        if group.name in self.controller.active_groups:
            QMessageBox.information(self, "组合正在运行", "请先关闭该组合，再进行删除。")
            return
        answer = QMessageBox.question(self, "删除组合", f"确定删除「{group.name}」？")
        if answer != QMessageBox.StandardButton.Yes:
            return
        candidate = copy.deepcopy(self.groups)
        candidate.pop(self.selected_index)
        if self._save_groups(candidate):
            self.reload(silent=True)

    def _save_groups(self, groups: list[AppGroup]) -> bool:
        previous = self.store.groups
        self.store.groups = copy.deepcopy(groups)
        try:
            self.store.save()
        except OSError as exc:
            self.store.groups = previous
            QMessageBox.critical(self, "保存失败", str(exc))
            return False
        self.groups = groups
        self.set_status("组合配置已保存到 Clopen")
        return True

    def render_selected(self) -> None:
        _clear_layout(self.entry_layout)
        group = self.selected_group()
        if group is None:
            self.group_title.setText("没有可用组合")
            self.group_meta.setText("点击左侧“新建”创建 Clopen 组合")
            self.primary_button.setEnabled(False)
            _set_dynamic_property(self.status_dot, "state", "inactive")
            self.status_dot.setToolTip("没有选择组合")
            self.edit_group_button.setEnabled(False)
            self.delete_group_button.setEnabled(False)
            self.entry_layout.addStretch()
            return
        active = group.name in self.controller.active_groups
        managed = sum(not item.is_external for item in group.entries)
        self.group_title.setText(group.name)
        self.group_meta.setText(f"{len(group.entries)} 个启动项 · {managed} 个可安全纳入关闭会话")
        for entry in group.entries:
            self.entry_layout.addWidget(self._entry_row(entry))
        self.entry_layout.addStretch()
        _set_dynamic_property(self.status_dot, "state", "active" if active else "inactive")
        self.status_dot.setToolTip("当前运行中" if active else "当前未启动")
        self.primary_button.setText("关闭组合" if active else "开启组合")
        _set_dynamic_property(self.primary_button, "danger", active)
        self.primary_button.setEnabled(True)
        self.edit_group_button.setEnabled(not active)
        self.delete_group_button.setEnabled(not active)
        self.close_all_button.setEnabled(bool(self.controller.active_groups))

    def _entry_row(self, entry: AppEntry) -> QFrame:
        row = QFrame()
        row.setObjectName("entryRow")
        layout = QHBoxLayout(row)
        layout.setContentsMargins(14, 11, 14, 11)
        text = QVBoxLayout()
        text.setSpacing(2)
        name = QLabel(entry.name or "未命名")
        name.setObjectName("entryName")
        meta = QLabel(f"{self._entry_kind(entry)} · {self._entry_mode(entry)}")
        meta.setObjectName("entryMeta")
        text.addWidget(name)
        text.addWidget(meta)
        layout.addLayout(text)
        layout.addStretch()
        return row

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

    def _run_primary_action(self) -> None:
        group = self.selected_group()
        if group is None:
            return
        if group.name in self.controller.active_groups:
            self.close_selected()
        else:
            self.start_selected()

    def start_selected(self) -> None:
        group = self.selected_group()
        if group is None:
            return
        self.set_status(f"正在开启 {group.name}…")
        _set_dynamic_property(self.status_dot, "state", "launching")
        self.status_dot.setToolTip("正在启动")
        QApplication.processEvents()
        report = self.controller.launch_group(group)
        self._show_launch_report(report)
        self.reload(silent=True)

    def close_selected(self) -> None:
        group = self.selected_group()
        if group is None:
            return
        answer = QMessageBox.question(
            self,
            "确认关闭",
            f"只关闭「{group.name}」由 Clopen 本次登记的进程？\n\n未保存内容可能丢失。",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        report = self.controller.close_group(group.name)
        QMessageBox.information(self, "关闭结果", f"{report.detail}\n关闭数量：{report.closed}")
        self.reload(silent=True)

    def close_all(self) -> None:
        if not self.controller.active_groups:
            return
        answer = QMessageBox.question(
            self,
            "确认关闭全部",
            "只关闭 Clopen 本次登记的全部进程会话？\n\n未保存内容可能丢失。",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        reports = self.controller.close_all()
        detail = "\n".join(f"{item.group_name}：{item.closed} 个" for item in reports)
        QMessageBox.information(self, "关闭结果", detail)
        self.reload(silent=True)

    def _show_launch_report(self, report: LaunchReport) -> None:
        lines = [f"成功登记：{report.started}", f"外部启动：{report.unmanaged}", f"失败：{report.failed}"]
        details = [f"{item.name}：{item.detail}" for item in report.results if item.detail]
        if details:
            lines.extend(["", *details])
        QMessageBox.information(self, "启动结果", "\n".join(lines))

    def set_status(self, text: str, *, error: bool = False) -> None:
        self.message_label.setText(text)
        self.message_label.setStyleSheet("color: #C54857;" if error else "")

    def _setup_system_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        self.tray_menu = QMenu()
        _configure_borderless_menu(self.tray_menu, self.dark_mode)
        self.tray_icon = QSystemTrayIcon(_app_icon(self.dark_mode), self)
        self.tray_icon.setToolTip("Clopen")
        # Avoid QSystemTrayIcon.setContextMenu(): Windows may wrap it in a native
        # framed menu. We show the Qt.Popup ourselves.
        self.tray_icon.activated.connect(self._tray_activated)
        self._refresh_tray_menu()
        self.tray_icon.show()

    def _refresh_tray_menu(self) -> None:
        if self.tray_menu is None:
            return
        self.tray_menu.clear()
        brand = QAction(_app_icon(self.dark_mode), "Clopen", self.tray_menu)
        brand.setEnabled(False)
        self.tray_menu.addAction(brand)
        self.tray_menu.addSeparator()
        open_action = self.tray_menu.addAction("打开主界面")
        open_action.triggered.connect(self.reveal)
        quick_menu = self.tray_menu.addMenu("快速启动")
        _configure_borderless_menu(quick_menu, self.dark_mode)
        quick_menu.aboutToShow.connect(
            lambda menu=quick_menu: QTimer.singleShot(0, lambda: _remove_windows_border(menu))
        )
        if self.groups:
            for group in self.groups:
                active = group.name in self.controller.active_groups
                text = f"{'关闭' if active else '开启'}  {group.name}"
                action = quick_menu.addAction(text)
                action.triggered.connect(
                    lambda _checked=False, group_name=group.name: self._tray_run_group(group_name)
                )
        else:
            empty = quick_menu.addAction("暂无组合")
            empty.setEnabled(False)
        self.tray_menu.addSeparator()
        settings_action = self.tray_menu.addAction("设置")
        settings_action.triggered.connect(self.show_settings)
        self.tray_menu.addSeparator()
        quit_action = self.tray_menu.addAction("退出 Clopen")
        quit_action.triggered.connect(self.quit_application)
        if self.tray_icon is not None:
            active_count = len(self.controller.active_groups)
            self.tray_icon.setToolTip("Clopen" if not active_count else f"Clopen · {active_count} 个活动组合")

    def _show_tray_menu(self) -> None:
        if self.tray_menu is None:
            return
        self._refresh_tray_menu()
        _configure_borderless_menu(self.tray_menu, self.dark_mode)
        self.tray_menu.popup(QCursor.pos())
        QTimer.singleShot(0, lambda: _remove_windows_border(self.tray_menu))

    def _tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Context:
            self._show_tray_menu()
            return
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.reveal()

    def _tray_run_group(self, group_name: str) -> None:
        self.select_group(group_name)
        group = self.selected_group()
        if group is None:
            return
        if group.name in self.controller.active_groups:
            self.close_selected()
        else:
            self.start_selected()

    def show_settings(self) -> None:
        dialog = SettingsDialog(self)
        dialog.exec()
        self._refresh_tray_menu()

    def toggle_dark_mode(self) -> None:
        self.set_dark_mode(not self.dark_mode)

    def set_dark_mode(self, dark: bool, *, persist: bool = True) -> None:
        self.dark_mode = dark
        app = QApplication.instance()
        app.setProperty("clopenDark", dark)
        app.setStyleSheet(APP_STYLE + (DARK_STYLE if dark else ""))
        self.theme_button.setText("浅色" if dark else "深色")
        self.title_bar.update_logo(dark)
        app_icon = _app_icon(dark)
        self.setWindowIcon(app_icon)
        app.setWindowIcon(app_icon)
        if self.tray_icon is not None:
            self.tray_icon.setIcon(app_icon)
        self._refresh_tray_menu()
        if persist:
            QSettings("Clopen", "Clopen").setValue("theme", "dark" if dark else "light")
        _set_windows_dark_mode(self, dark)
        _remove_windows_border(self)
        if self.quick_menu.isVisible():
            _set_windows_dark_mode(self.quick_menu, dark)

    def toggle_quick_menu(self) -> None:
        if self.quick_menu.isVisible():
            self.quick_menu.hide()
        else:
            self.quick_menu.popup()

    def reveal(self) -> None:
        self.quick_menu.hide()
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def quit_application(self) -> None:
        self.quick_menu.hide()
        if self.tray_icon is not None:
            self.tray_icon.hide()
        self.hotkey.unregister()
        QApplication.instance().removeNativeEventFilter(self.hotkey_filter)
        self.controller.detach_all()
        QApplication.instance().quit()

    def closeEvent(self, event) -> None:
        event.ignore()
        self.hide()


def _enable_dpi_awareness() -> None:
    if os.name != "nt":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        pass


def _disable_windows_round_corners(widget: QWidget) -> None:
    """Disable DWM's own rounded frame so it cannot show behind Clopen's surface."""
    if os.name != "nt" or os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        return
    try:
        # DWMWA_WINDOW_CORNER_PREFERENCE = 33; DWMWCP_DONOTROUND = 1.
        value = ctypes.c_int(1)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            ctypes.c_void_p(int(widget.winId())), 33, ctypes.byref(value), ctypes.sizeof(value)
        )
    except (AttributeError, OSError, TypeError, ValueError):
        pass


def _apply_windows_round_region(widget: QWidget, radius: int) -> None:
    """Clip the native HWND itself to Clopen's rounded rectangle.

    This removes the last gray crescent/under-layer that can remain in the four
    corners of a translucent frameless window on Windows 11.
    """
    if os.name != "nt" or os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        return
    try:
        hwnd = ctypes.c_void_p(int(widget.winId()))
        user32 = ctypes.windll.user32
        gdi32 = ctypes.windll.gdi32

        class RECT(ctypes.Structure):
            _fields_ = [
                ("left", ctypes.c_long),
                ("top", ctypes.c_long),
                ("right", ctypes.c_long),
                ("bottom", ctypes.c_long),
            ]

        user32.GetWindowRect.argtypes = [ctypes.c_void_p, ctypes.POINTER(RECT)]
        user32.GetWindowRect.restype = ctypes.c_bool
        user32.SetWindowRgn.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_bool]
        user32.SetWindowRgn.restype = ctypes.c_int
        gdi32.CreateRoundRectRgn.argtypes = [
            ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int
        ]
        gdi32.CreateRoundRectRgn.restype = ctypes.c_void_p
        gdi32.CreateRectRgn.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int]
        gdi32.CreateRectRgn.restype = ctypes.c_void_p
        gdi32.DeleteObject.argtypes = [ctypes.c_void_p]
        gdi32.DeleteObject.restype = ctypes.c_bool

        rect = RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            return
        width = max(1, rect.right - rect.left)
        height = max(1, rect.bottom - rect.top)

        if widget.isMaximized():
            region = gdi32.CreateRectRgn(0, 0, width + 1, height + 1)
        else:
            native_radius = max(1, round(radius * widget.devicePixelRatioF()))
            diameter = native_radius * 2
            region = gdi32.CreateRoundRectRgn(0, 0, width + 1, height + 1, diameter, diameter)
        if not region:
            return
        # After a successful SetWindowRgn, Windows owns the HRGN.
        if not user32.SetWindowRgn(hwnd, region, True):
            gdi32.DeleteObject(region)
    except (AttributeError, OSError, TypeError, ValueError):
        pass


def _remove_windows_border(widget: QWidget) -> None:
    """Disable the Windows 11 DWM one-pixel outline around the frameless window."""
    if os.name != "nt" or os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        return
    try:
        # DWMWA_BORDER_COLOR = 34, DWMWA_COLOR_NONE = 0xFFFFFFFE.
        color_none = ctypes.c_uint(0xFFFFFFFE)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            ctypes.c_void_p(int(widget.winId())), 34, ctypes.byref(color_none), ctypes.sizeof(color_none)
        )
    except (AttributeError, OSError, TypeError, ValueError):
        pass


def _set_windows_dark_mode(widget: QWidget, dark: bool) -> None:
    if os.name != "nt" or os.environ.get("QT_QPA_PLATFORM") == "offscreen":
        return
    try:
        value = ctypes.c_int(1 if dark else 0)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            ctypes.c_void_p(int(widget.winId())), 20, ctypes.byref(value), ctypes.sizeof(value)
        )
    except (AttributeError, OSError, TypeError, ValueError):
        pass


def create_application(argv: list[str] | None = None) -> QApplication:
    app = QApplication(argv or sys.argv)
    app.setApplicationName("Clopen")
    app.setQuitOnLastWindowClosed(False)
    saved_theme = str(QSettings("Clopen", "Clopen").value("theme", "system"))
    system_dark = app.styleHints().colorScheme() == Qt.ColorScheme.Dark
    dark = system_dark if saved_theme == "system" else saved_theme == "dark"
    app.setProperty("clopenDark", dark)
    app.setWindowIcon(_app_icon(dark))
    app.setStyleSheet(APP_STYLE + (DARK_STYLE if dark else ""))
    font_family = "Microsoft YaHei UI"
    if os.name == "nt":
        font_id = QFontDatabase.addApplicationFont(r"C:\Windows\Fonts\msyh.ttc")
        families = QFontDatabase.applicationFontFamilies(font_id) if font_id >= 0 else []
        if families:
            font_family = families[0]
    font = QFont(font_family, 10)
    app.setFont(font)
    return app


def main() -> None:
    _enable_dpi_awareness()
    app = create_application()
    window = MainWindow()
    window.show()
    raise SystemExit(app.exec())


if __name__ == "__main__":
    main()
