from __future__ import annotations

import os
import sys
import time
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


def wait_for_visibility(app: QApplication, window, expected: bool, timeout: float = 2.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        app.processEvents()
        if window.isVisible() is expected:
            return True
        time.sleep(0.02)
    return window.isVisible() is expected


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    qml_app._configure_application(app)
    engine = QQmlApplicationEngine()
    bridge = qml_app.ClopenBridge(app, engine)
    engine.rootContext().setContextProperty('clopen', bridge)

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
    if not wait_for_visibility(app, bridge._quick_popup, True):
        raise RuntimeError('Quick launcher did not become visible by direct bridge call')
    print('PASS - quick launcher direct show path works')

    bridge.toggleQuickLauncher()
    if not wait_for_visibility(app, bridge._quick_popup, False):
        raise RuntimeError('Quick launcher did not hide on second toggle')
    print('PASS - quick launcher hide path works')

    # Validate the exact queued path used by the physical-key worker.
    bridge.hotkeyTriggered.emit()
    if not wait_for_visibility(app, bridge._quick_popup, True):
        raise RuntimeError('Queued hotkey signal did not open quick launcher')
    print('PASS - hotkey signal -> GUI -> quick launcher chain works')

    bridge._quick_popup.hide()
    root.hide()
    bridge._hotkey_stop.set()
    print('RUNTIME_CHAIN_SMOKE_OK')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
