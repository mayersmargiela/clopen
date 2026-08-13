import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QApplication

from clopen.app import MainWindow, create_application


class UiBehaviorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or create_application(["clopen-test"])

    def test_constructing_main_window_does_not_show_without_user_action(self):
        with patch("clopen.app.ConfigStore.load", return_value=[]):
            window = MainWindow(register_hotkey=False)
        try:
            self.app.processEvents()
            self.assertFalse(window.isVisible())
            self.assertFalse(window.quick_menu.isVisible())
        finally:
            window.quit_application()
            self.app.processEvents()


if __name__ == "__main__":
    unittest.main()
