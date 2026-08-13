import unittest

from clopen.models import AppEntry


class ModelTests(unittest.TestCase):
    def test_external_entries_and_legacy_serialization(self):
        self.assertTrue(AppEntry(name="Folder", path="C:/x", is_folder=True).is_external)
        self.assertTrue(AppEntry(name="UWP", path="Vendor.App!App", is_uwp=True).is_external)
        self.assertTrue(AppEntry(name="URL", url="https://example.com").is_external)
        self.assertFalse(AppEntry(name="Process", path="C:/tool.exe").is_external)

        legacy = {
            "run_as_admin": 1,
            "is_file": 0,
            "is_folder": False,
            "is_uwp": True,
            "url": "https://example.com",
            "working_dir": "C:/Apps",
            "arguments": "--profile work",
            "path": "C:/Apps/demo.exe",
            "name": 42,
            "unknown": "ignored",
        }
        restored = AppEntry.from_dict(legacy)
        serialized = restored.to_dict()
        self.assertEqual(
            list(serialized),
            [
                "name",
                "path",
                "arguments",
                "working_dir",
                "url",
                "is_uwp",
                "is_folder",
                "is_file",
                "run_as_admin",
            ],
        )
        self.assertEqual(serialized["name"], "42")
        self.assertTrue(serialized["is_uwp"])
        self.assertTrue(serialized["run_as_admin"])
        self.assertNotIn("unknown", serialized)


if __name__ == "__main__":
    unittest.main()
