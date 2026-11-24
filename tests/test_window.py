"""The window itself: every tab opens, the look changes, statuses are saved and undone, nothing freezes.

The window runs in its own process on made-up offers, in a temporary folder: your settings and jobs.xlsx are
never touched. Skipped when there is no screen (on GitHub, the tests run on a virtual one: xvfb).
"""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

CHECK = Path(__file__).resolve().parent / "window_check.py"


class Window(unittest.TestCase):
    def test_the_window_works_without_errors_or_freezes(self):
        with tempfile.TemporaryDirectory() as home:
            result = subprocess.run([sys.executable, str(CHECK)], capture_output=True, text=True, encoding="utf-8",
                                    errors="replace", timeout=300,
                                    env={**os.environ, "RETRIEVE_JOB_HOME": home, "PYTHONIOENCODING": "utf-8"})
        if result.returncode == 77:
            self.skipTest("no screen to open a window on")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
