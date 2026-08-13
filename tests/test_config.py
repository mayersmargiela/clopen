import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch

from clopen.config import ConfigStore
from clopen.models import AppEntry, AppGroup


class ConfigStoreTests(unittest.TestCase):
    def test_default_path_is_clopen_appdata_config(self):
        with patch.dict(os.environ, {"APPDATA": "C:/Users/Test/AppData/Roaming"}):
            self.assertEqual(
                ConfigStore().path,
                Path("C:/Users/Test/AppData/Roaming/Clopen/config.json"),
            )

    def test_missing_clopen_config_starts_empty(self):
        path = Path("Z:/Clopen/config.json")
        with patch.object(type(path), "exists", autospec=True, return_value=False):
            store = ConfigStore(path=path)
            self.assertEqual(store.load(), [])
        self.assertEqual(store.source, path)


    def test_v1_desktop_apps_migrate_to_admin_launch(self):
        path = Path("Z:/Clopen/config.json")
        payload = json.dumps({
            "version": 1,
            "groups": [{
                "name": "游戏",
                "entries": [{"name": "WeGame", "path": "C:/WeGame.exe", "run_as_admin": False}],
            }],
        })
        with (
            patch.object(type(path), "exists", autospec=True, return_value=True),
            patch.object(type(path), "read_text", autospec=True, return_value=payload),
        ):
            groups = ConfigStore(path=path).load()
        self.assertTrue(groups[0].entries[0].run_as_admin)

    def test_save_writes_only_clopen_config(self):
        path = Path("Z:/Clopen/config.json")
        writes = {}

        def write_text(target, text, *, encoding):
            writes[target] = (text, encoding)
            return len(text)

        with (
            patch.object(type(path), "mkdir", autospec=True),
            patch.object(type(path), "write_text", autospec=True, side_effect=write_text),
        ):
            store = ConfigStore(path=path)
            store.groups = [AppGroup(name="工作")]
            store.save()

        self.assertEqual(set(writes), {path})
        saved = json.loads(writes[path][0])
        self.assertEqual(saved["version"], 2)
        self.assertEqual(saved["groups"][0]["name"], "工作")
        self.assertEqual(writes[path][1], "utf-8")


if __name__ == "__main__":
    unittest.main()
