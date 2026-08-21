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

    from PySide6.QtCore import QEventLoop, QTimer
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtWidgets import QApplication
    from clopen import qml_app

    # First prove the real Win32 physical-key API is accessible in this build.
    probe = qml_app._ctrl_shift_e_down()
    if not isinstance(probe, bool):
        raise RuntimeError('GetAsyncKeyState helper did not return bool')
    print('PASS - GetAsyncKeyState path is available')

    # Then force one physical-key edge and prove the background watcher queues
    # it back to the GUI. Qt.Popup auto-closes in some headless Windows runner
    # sessions, so CI verifies the popup invocation rather than persistence.
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

    class PopupProbe:
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

    native_popup = bridge._quick_popup
    popup_probe = PopupProbe()
    bridge._quick_popup = popup_probe

    loop = QEventLoop()
    QTimer.singleShot(500, loop.quit)
    loop.exec()
    result = popup_probe.popup_calls == 1 and popup_probe.isVisible()
    bridge._hotkey_stop.set()
    popup_probe.hide()
    native_popup.hide()
    qml_app._ctrl_shift_e_down = real_probe

    if not result:
        raise RuntimeError('physical-hotkey worker did not reach QuickLauncherPopup')
    print('PASS - hotkey worker -> queued Qt signal -> quick popup')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
