"""Double-click this file to open Retrieve Job: it starts at once, without the black window.

(Double-clicking app.py works too, but Windows first opens it in a console, then the app starts again without one:
Python starts twice.)
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import app  # noqa: E402

app.main()
