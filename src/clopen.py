from __future__ import annotations

import os
import sys

from clopen.config import ConfigStore


def run() -> None:
    if "--smoke-test" in sys.argv:
        ConfigStore().load()
        return
    if "--hotkey-self-test" in sys.argv:
        from clopen.hotkey import GlobalHotkey

        hotkey = GlobalHotkey(lambda: None)
        hotkey.register()
        hotkey.unregister()
        return
    if "--ui-self-test" in sys.argv:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        from clopen.app import MainWindow, create_application
        from clopen.models import AppEntry, AppGroup

        app = create_application(sys.argv)
        window = MainWindow(register_hotkey=False)
        window.groups = [
            AppGroup("工作", [AppEntry(name="Visual Studio Code", path="C:/Code.exe")]),
            AppGroup("直播", [AppEntry(name="OBS Studio", path="C:/OBS.exe")]),
        ]
        window._render_groups()
        window.group_search.setText("obs")
        if not window.selected_group() or window.selected_group().name != "直播":
            raise SystemExit("main search self-test failed")
        window.quick_menu.rebuild()
        window.quick_menu.search_edit.setText("code")
        visible_names = [
            group.name
            for button, group in window.quick_menu.group_buttons
            if not button.isHidden()
        ]
        if visible_names != ["工作"]:
            raise SystemExit("quick-menu search self-test failed")
        window.set_dark_mode(not window.dark_mode, persist=False)
        window.show()
        app.processEvents()
        window.close()
        app.processEvents()
        if window.isVisible():
            raise SystemExit("close-to-background self-test failed")
        window.quit_application()
        app.processEvents()
        return
    if "--render-preview" in sys.argv or "--render-preview-dark" in sys.argv:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
        from pathlib import Path

        from clopen.app import MainWindow, create_application

        option = "--render-preview-dark" if "--render-preview-dark" in sys.argv else "--render-preview"
        output_index = sys.argv.index(option) + 1
        if output_index >= len(sys.argv):
            raise SystemExit("--render-preview requires an output path")
        output = Path(sys.argv[output_index])
        output.parent.mkdir(parents=True, exist_ok=True)
        app = create_application(sys.argv)
        window = MainWindow(register_hotkey=False)
        window.set_dark_mode(option == "--render-preview-dark", persist=False)
        window.show()
        app.processEvents()
        if not window.grab().save(str(output), "PNG"):
            raise SystemExit(f"failed to render preview: {output}")
        window.quit_application()
        app.processEvents()
        return
    from clopen.app import main

    main()


if __name__ == "__main__":
    run()
