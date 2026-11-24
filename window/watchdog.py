"""Notes what holds the window: slow moments in .cache/slow.log, freezes in .cache/freeze.log, errors in errors.log.

The window ticks every quarter of a second; a separate thread checks the ticks. When a tick comes more than
SLOW_SECONDS late, the moment goes in slow.log with the tab on screen and the code that was running (seen by the
thread while the window was held), so the slow spots of real use can be found and fixed. Windows shows
"Not responding" when the window doesn't answer for about 5 seconds: past FREEZE_SECONDS, freeze.log gets the
whole stack. Errors in the window's callbacks and in its background threads go to errors.log.
"""
import sys
import threading
import time
import traceback
from datetime import datetime
from pathlib import Path

from settings import APP_DIR

FREEZE_LOG = APP_DIR / ".cache" / "freeze.log"
ERROR_LOG = APP_DIR / ".cache" / "errors.log"
SLOW_LOG = APP_DIR / ".cache" / "slow.log"
FREEZE_SECONDS = 4.0
SLOW_SECONDS = 0.5  # a hold you feel
TICK = 0.25
LOG_SIZE = 200_000  # bytes: beyond, slow.log keeps only its newer half
CODE = Path(__file__).resolve().parent.parent  # the app's own files, to show only them in slow.log


def _append(path, text: str) -> None:
    try:
        path.parent.mkdir(exist_ok=True)
        with path.open("a", encoding="utf-8") as log:
            log.write(text)
        if path == SLOW_LOG and path.stat().st_size > LOG_SIZE:
            lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
            path.write_text("".join(lines[len(lines) // 2:]), encoding="utf-8")
    except OSError:
        pass  # never let the diagnosis itself break the app


def log_error(error: BaseException) -> None:
    """Notes an error with where it happened in .cache/errors.log (and in the terminal, if there is one)."""
    text = "".join(traceback.format_exception(type(error), error, error.__traceback__))
    _append(ERROR_LOG, f"{datetime.now():%Y-%m-%d %H:%M:%S}\n{text}\n")
    if sys.stderr:
        print(text, file=sys.stderr)


def app_code(frame) -> str:
    """The app's own functions running in this stack, innermost last: "results_tab.py:213 _show_offers < ...".
    Without any, the time went to Tk drawing the window."""
    calls = []
    for summary in traceback.extract_stack(frame):
        try:
            inside = Path(summary.filename).resolve().is_relative_to(CODE)
        except (OSError, ValueError):
            inside = False
        if inside and summary.name != "<module>" and summary.name != "main":
            calls.append(f"{Path(summary.filename).name}:{summary.lineno} {summary.name}")
    return " > ".join(calls[-4:]) or "Tk drawing the window (no app code running)"


class Watchdog:
    def __init__(self, root, context=None):
        self.root = root
        self.context = context or (lambda: "")  # what the window shows (its tab), asked in the window's thread
        self.main = threading.main_thread().ident
        self.beat = time.monotonic()
        self.frozen_since = 0.0  # set while a freeze is being reported
        self.sample = ""  # the code seen running while the window was held
        self.stopped = False
        root.bind("<Destroy>", lambda event: self._stop() if event.widget is root else None, add="+")
        root.report_callback_exception = self._callback_error
        threading.excepthook = lambda args: log_error(args.exc_value) if args.exc_value else None
        self._tick()
        threading.Thread(target=self._watch, daemon=True).start()

    def _stop(self) -> None:
        self.stopped = True

    def note(self, text: str) -> None:
        """A line in slow.log, such as how long the app took to start."""
        _append(SLOW_LOG, f"{datetime.now():%Y-%m-%d %H:%M:%S}  {text}\n")

    def _tick(self) -> None:
        now = time.monotonic()
        held = now - self.beat - TICK
        if SLOW_SECONDS <= held < 60 and not self.stopped:  # longer: the PC was asleep, not the app
            try:
                where = self.context()
            except Exception:  # noqa: BLE001 - the diagnosis never breaks the app
                where = ""
            self.note(f"{held:4.1f} s  [{where}]  {self.sample or 'Tk drawing the window (no app code running)'}")
        self.sample = ""
        if self.frozen_since:
            _append(FREEZE_LOG, f"    ... answered again after {now - self.frozen_since:.1f} s\n\n")
            self.frozen_since = 0.0
        self.beat = now
        if not self.stopped:
            self.root.after(int(TICK * 1000), self._tick)

    def _watch(self) -> None:
        while not self.stopped:
            time.sleep(0.1)
            stuck = time.monotonic() - self.beat
            if stuck > TICK + SLOW_SECONDS * 0.6 and not self.sample:  # held for a while: what is running?
                frame = sys._current_frames().get(self.main)
                self.sample = app_code(frame) if frame else ""
            if stuck > FREEZE_SECONDS and not self.frozen_since and not self.stopped:
                self.frozen_since = self.beat
                frame = sys._current_frames().get(self.main)
                where = "".join(traceback.format_stack(frame)[-12:]) if frame else "(unknown)\n"
                _append(FREEZE_LOG, f"{datetime.now():%Y-%m-%d %H:%M:%S} the window stopped answering, "
                                    f"stuck for {stuck:.1f} s here:\n{where}")

    @staticmethod
    def _callback_error(kind, error, trace) -> None:
        log_error(error.with_traceback(trace))
