"""Reads and writes jobs.xlsx outside the window's thread, one job after the other.

Saving a status rewrites the whole file (about a second with a few hundred offers, more as it grows): done in the
window, it froze it meanwhile. Here the window shows the change at once and the file follows in the background.
One thread does every job in the order asked, so a read after a change sees that change, and two changes never
write the file at the same time.
"""
import queue
import threading
import time

from window.watchdog import log_error


class FileWorker:
    def __init__(self, messages: queue.Queue):
        self.messages = messages  # the window's queue: the answers are handled in the window's thread
        self.jobs: queue.Queue = queue.Queue()
        threading.Thread(target=self._run, daemon=True, name="jobs.xlsx").start()

    def add(self, work, done=None, failed=None) -> None:
        """Runs work() in the background, then done(result) or failed(error) in the window's thread."""
        self.jobs.put((work, done, failed))

    def busy(self) -> bool:
        return self.jobs.unfinished_tasks > 0

    def wait(self, seconds: float) -> bool:
        """Waits until every job asked is done; False if some are still running after that many seconds."""
        end = time.monotonic() + seconds
        while self.busy():
            if time.monotonic() > end:
                return False
            time.sleep(0.05)
        return True

    def _run(self) -> None:
        while True:
            work, done, failed = self.jobs.get()
            try:
                result = work()
            except Exception as error:  # reported, never the end of the thread
                if not isinstance(error, PermissionError):
                    log_error(error)
                if failed:
                    self.messages.put(("call", lambda f=failed, e=error: f(e)))
            else:
                if done:
                    self.messages.put(("call", lambda d=done, r=result: d(r)))
            finally:
                self.jobs.task_done()
