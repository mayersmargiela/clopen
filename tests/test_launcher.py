import unittest
from unittest.mock import Mock

from clopen.launcher import BatchController


class BatchControllerTests(unittest.TestCase):
    def test_close_failure_keeps_session_for_retry(self):
        controller = BatchController()
        session = Mock()
        session.close.side_effect = [RuntimeError("close failed"), 1]
        controller._sessions["Agent"] = session

        failed = controller.close_group("Agent")
        self.assertIn("Agent", controller.active_groups)
        self.assertEqual(failed.closed, 0)

        succeeded = controller.close_group("Agent")
        self.assertNotIn("Agent", controller.active_groups)
        self.assertEqual(succeeded.closed, 1)


if __name__ == "__main__":
    unittest.main()
