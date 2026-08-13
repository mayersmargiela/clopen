import os
import subprocess
import sys
import unittest

from clopen.process_control import ProcessGroup


class ProcessControlTests(unittest.TestCase):
    def test_close_only_terminates_the_registered_process(self):
        command = [sys.executable, "-c", "import time; time.sleep(30)"]
        flags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        owned = subprocess.Popen(command, creationflags=flags)
        unrelated = subprocess.Popen(command, creationflags=flags)
        session = ProcessGroup("test")
        try:
            session.add_handle(owned._handle, owned.pid, "owned", sys.executable, popen=owned)
            self.assertEqual(session.pids, {owned.pid})
            self.assertEqual(session.close(grace_period=0), 1)
            owned.wait(timeout=3)
            self.assertIsNone(unrelated.poll())
        finally:
            if owned.poll() is None:
                owned.kill()
            if unrelated.poll() is None:
                unrelated.kill()
            unrelated.wait(timeout=3)
            if os.name == "nt":
                # close() already releases the Job Object; this branch only
                # documents that the test never detaches an active session.
                pass


if __name__ == "__main__":
    unittest.main()
