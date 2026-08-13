import unittest

from clopen.app_discovery import (
    DiscoveredApp,
    _dedupe_apps,
    _looks_like_software,
    parse_executable_path,
    search_discovered_apps,
)


class AppDiscoveryTests(unittest.TestCase):
    def test_parses_registry_executable_values(self):
        self.assertEqual(
            parse_executable_path('"C:\\Program Files\\Demo\\demo.exe",0'),
            "C:\\Program Files\\Demo\\demo.exe",
        )
        self.assertEqual(
            parse_executable_path("C:\\Apps\\demo.exe, -1"),
            "C:\\Apps\\demo.exe",
        )
        self.assertEqual(parse_executable_path("C:\\Apps\\icon.dll,0"), "")

    def test_discovered_app_becomes_managed_or_start_menu_entry(self):
        managed = DiscoveredApp(
            "Demo",
            path="C:/Demo.exe",
            arguments="--profile work",
            working_dir="C:/",
        ).to_entry()
        start_app = DiscoveredApp("Store Demo", app_id="Demo.App_123!App").to_entry()
        self.assertFalse(managed.is_external)
        self.assertTrue(managed.run_as_admin)
        self.assertEqual(managed.arguments, "--profile work")
        self.assertEqual(managed.working_dir, "C:/")
        self.assertTrue(start_app.is_uwp)
        self.assertTrue(start_app.is_external)


    def test_filters_maintenance_helpers_from_software_library(self):
        self.assertFalse(_looks_like_software("Uninstall Demo", "C:/Demo/uninstall.exe"))
        self.assertFalse(_looks_like_software("Demo Updater", "C:/Demo/updater.exe"))
        self.assertFalse(_looks_like_software("用户手册", "C:/Demo/manual.exe"))
        self.assertTrue(_looks_like_software("WeGame", "C:/Apps/WeGame.exe"))
        self.assertTrue(_looks_like_software("Photoshop", "C:/Adobe/Photoshop.exe"))

    def test_deduplication_prefers_first_human_friendly_shortcut_name(self):
        apps = _dedupe_apps(
            [
                DiscoveredApp("Photoshop", path="C:/Adobe/Photoshop.exe"),
                DiscoveredApp("Photoshop.exe", path="C:/Adobe/Photoshop.exe"),
                DiscoveredApp("Calculator", app_id="Microsoft.WindowsCalculator_abc!App"),
            ]
        )
        self.assertEqual([app.name for app in apps], ["Photoshop", "Calculator"])

    def test_search_prioritizes_exact_and_prefix_name_matches(self):
        apps = [
            DiscoveredApp("Adobe Photoshop", path="C:/Adobe/Photoshop.exe"),
            DiscoveredApp("Photoshop Beta", path="C:/Adobe/Beta.exe"),
            DiscoveredApp("Photoshop", path="C:/Adobe/Stable.exe"),
            DiscoveredApp("Photo Tool", path="C:/Tools/PhotoshopHelper.exe"),
        ]
        results = search_discovered_apps(apps, "photoshop")
        self.assertEqual(results[0].name, "Photoshop")
        self.assertEqual(results[1].name, "Photoshop Beta")
        self.assertIn("Adobe Photoshop", [app.name for app in results])

    def test_empty_search_keeps_direct_apps_before_packaged_apps(self):
        apps = [
            DiscoveredApp("Calculator", app_id="Calc_abc!App"),
            DiscoveredApp("OBS", path="C:/OBS/obs64.exe"),
        ]
        results = search_discovered_apps(apps, "")
        self.assertEqual([app.name for app in results], ["OBS", "Calculator"])


if __name__ == "__main__":
    unittest.main()
