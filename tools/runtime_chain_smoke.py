from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickWindow
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / 'src'
sys.path.insert(0, str(SRC))

from clopen import qml_app


def pump(app: QApplication, count: int = 8) -> None:
    for _ in range(count):
        app.processEvents()


class PopupProbe:
    """Deterministic stand-in for Qt.Popup in headless CI sessions."""

    def __init__(self) -> None:
        self.visible = False
        self.popup_calls = 0

    def isVisible(self) -> bool:
        return self.visible

    def popup(self) -> None:
        self.popup_calls += 1
        self.visible = True

    def hide(self) -> None:
        self.visible = False

    def _apply_theme(self) -> None:
        pass


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    qml_app._configure_application(app)
    engine = QQmlApplicationEngine()
    bridge = qml_app.ClopenBridge(app, engine)
    engine.rootContext().setContextProperty('clopen', bridge)
    native_popup = bridge._quick_popup
    popup_probe = PopupProbe()
    bridge._quick_popup = popup_probe

    main_qml = ROOT / 'src' / 'clopen' / 'qml' / 'Main.qml'
    engine.load(QUrl.fromLocalFile(str(main_qml)))
    roots = engine.rootObjects()
    if not roots or not isinstance(roots[0], QQuickWindow):
        raise RuntimeError('Main.qml did not create a QQuickWindow')

    root = roots[0]
    bridge.set_main_window(root)
    root.show()
    pump(app)
    if not root.isVisible():
        raise RuntimeError('Main window did not become visible')
    print('PASS - main window loads and becomes visible')

    bridge.toggleQuickLauncher()
    if not popup_probe.isVisible() or popup_probe.popup_calls != 1:
        raise RuntimeError('Direct bridge call did not invoke quick launcher popup')
    print('PASS - quick launcher direct show path works')

    bridge.toggleQuickLauncher()
    if popup_probe.isVisible():
        raise RuntimeError('Quick launcher did not hide on second toggle')
    print('PASS - quick launcher hide path works')

    # Validate the exact queued path used by the physical-key worker.
    bridge.hotkeyTriggered.emit()
    pump(app, 16)
    if not popup_probe.isVisible() or popup_probe.popup_calls != 2:
        raise RuntimeError('Queued hotkey signal did not invoke quick launcher popup')
    print('PASS - hotkey signal -> GUI -> quick launcher chain works')

    popup_probe.hide()
    native_popup.hide()
    root.hide()
    bridge._hotkey_stop.set()
    print('RUNTIME_CHAIN_SMOKE_OK')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
