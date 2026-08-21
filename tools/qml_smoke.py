from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QObject, Property, Signal, Slot, QUrl
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent
from PySide6.QtQuick import QQuickWindow
from PySide6.QtWidgets import QApplication


class Dummy(QObject):
    changed = Signal()

    @Property(bool, notify=changed)
    def darkMode(self): return True

    @Property(str, notify=changed)
    def message(self): return ""

    @Property("QVariantList", notify=changed)
    def groupItems(self):
        return [{"name": "Smoke Test", "count": 1, "active": False, "selected": True}]

    @Property("QVariantMap", notify=changed)
    def selectedGroup(self):
        return {
            "exists": True,
            "name": "Smoke Test",
            "meta": "1 个启动项 · 1 个可安全纳入关闭会话",
            "active": False,
            "entries": [{"name": "Example", "kind": "应用", "mode": "管理员 · 受管"}],
        }

    @Property(bool, notify=changed)
    def anyActive(self): return False

    @Property(str, notify=changed)
    def primaryText(self): return "开启组合"

    @Slot(str)
    def selectGroup(self, _name): pass
    @Slot(str)
    def toggleGroupByName(self, _name): pass
    @Slot()
    def newGroup(self): pass
    @Slot()
    def editSelected(self): pass
    @Slot()
    def deleteSelected(self): pass
    @Slot()
    def primaryAction(self): pass
    @Slot()
    def closeAll(self): pass
    @Slot()
    def showSettings(self): pass
    @Slot()
    def refresh(self): pass
    @Slot()
    def minimizeMain(self): pass
    @Slot()
    def hideMain(self): pass
    @Slot()
    def showMain(self): pass
    @Slot()
    def quitApplication(self): pass


app = QApplication(sys.argv)
engine = QQmlApplicationEngine()
dummy = Dummy()
engine.rootContext().setContextProperty("clopen", dummy)
qml_dir = Path(__file__).resolve().parents[1] / "src" / "clopen" / "qml"

main_qml = qml_dir / "Main.qml"
engine.load(QUrl.fromLocalFile(str(main_qml)))
if not engine.rootObjects() or not isinstance(engine.rootObjects()[0], QQuickWindow):
    raise SystemExit("QML smoke test failed to load Main.qml")

for name in ("QuickLauncher.qml", "TrayPopup.qml"):
    component = QQmlComponent(engine, QUrl.fromLocalFile(str(qml_dir / name)))
    if component.status() != QQmlComponent.Status.Ready:
        errors = "\n".join(error.toString() for error in component.errors())
        raise SystemExit(f"QML smoke test failed for {name}:\n{errors}")
    obj = component.create(engine.rootContext())
    if not isinstance(obj, QQuickWindow):
        raise SystemExit(f"QML smoke test did not create a Window for {name}")
    obj.deleteLater()

print("QML_SMOKE_OK_MAIN_QUICK_TRAY")
