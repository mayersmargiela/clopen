import unittest

from clopen.app import group_matches
from clopen.models import AppEntry, AppGroup


class GroupSearchTests(unittest.TestCase):
    def setUp(self):
        self.group = AppGroup(
            name="直播工作台",
            entries=[
                AppEntry(name="OBS Studio", path="C:/Apps/obs64.exe"),
                AppEntry(name="控制面板", url="https://studio.example.com"),
            ],
        )

    def test_matches_group_and_entry_fields_case_insensitively(self):
        self.assertTrue(group_matches(self.group, "直播"))
        self.assertTrue(group_matches(self.group, "obs"))
        self.assertTrue(group_matches(self.group, "STUDIO.EXAMPLE"))

    def test_non_matching_query_is_hidden(self):
        self.assertFalse(group_matches(self.group, "游戏"))


if __name__ == "__main__":
    unittest.main()
