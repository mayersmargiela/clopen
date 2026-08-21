from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> int:
    if os.name != 'nt':
        print('SKIP - Windows physical-hotkey worker smoke test is Windows-only')
        return 0

    os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
    ROOT = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(ROOT / 'src'))

    from PySide6.QtCore import QTimer
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtWidgets import QApplication
    from clopen import qml_app

    # First prove the real Win32 physical-key API is accessible in this build.
    probe = qml_app._ctrl_shift_e_down()
    if not isinstance(probe, bool):
        raise RuntimeError('GetAsyncKeyState helper did not return bool')
    print('PASS - GetAsyncKeyState path is available')

    # Then force one physical-key edge and prove the background watcher queues
    # it back to the GUI and opens the actual quick popup.
    calls = {'n': 0}
    real_probe = qml_app._ctrl_shift_e_down

    def fake_probe() -> bool:
        calls['n'] += 1
        return 2 <= calls['n'] <= 4

    qml_app._ctrl_shift_e_down = fake_probe
    app = QApplication.instance() or QApplication(sys.argv)
    qml_app._configure_application(app)
    engine = QQmlApplicationEngine()
    bridge = qml_app.ClopenBridge(app, engine)
    engine.rootContext().setContextProperty('clopen', bridge)

    result = {'ok': False}

    def verify() -> None:
        result['ok'] = bridge._quick_popup.isVisible()
        bridge._hotkey_stop.set()
        bridge._quick_popup.hide()
        app.quit()

    QTimer.singleShot(500, verify)
    app.exec()
    qml_app._ctrl_shift_e_down = real_probe

    if not result['ok']:
        raise RuntimeError('physical-hotkey worker did not reach QuickLauncherPopup')
    print('PASS - hotkey worker -> queued Qt signal -> quick popup')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
