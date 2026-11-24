"""What differs between Windows, Mac and Linux, checked on any of them: the mouse wheel and the shortcut keys."""
import tkinter as tk
import unittest
from types import SimpleNamespace
from unittest import mock

from window import common


class MouseWheel(unittest.TestCase):
    def setUp(self):
        try:
            self.root = tk.Tk()
        except tk.TclError:
            self.skipTest("no screen to open a window on")
        self.addCleanup(self.root.destroy)
        self.root.geometry("300x200")
        self.page = common.Scrollable(self.root)
        self.page.pack(fill="both", expand=True)
        for number in range(60):  # much taller than the window
            tk.Label(self.page.inner, text=f"line {number}").pack()
        self.root.update()

    def top(self) -> float:
        return self.page.canvas.yview()[0]

    def test_linux_wheel_buttons_scroll(self):
        """Linux sends button 5 to go down and button 4 to go up."""
        self.page._wheel(SimpleNamespace(num=5, delta=0))
        self.assertGreater(self.top(), 0)
        self.page._wheel(SimpleNamespace(num=4, delta=0))
        self.assertEqual(self.top(), 0)

    def test_windows_and_mac_wheel_scrolls(self):
        """Windows (delta ±120) and Mac (small deltas) send <MouseWheel> with a sign."""
        for down, up in ((-120, 120), (-1, 1)):
            self.page._wheel(SimpleNamespace(num="??", delta=down))
            self.assertGreater(self.top(), 0)
            self.page._wheel(SimpleNamespace(num="??", delta=up))
            self.assertEqual(self.top(), 0)

    def test_every_wheel_event_is_listened_to_inside_the_page(self):
        self.page._listen_to_wheel(True)
        for event in common.Scrollable.WHEEL_EVENTS:
            self.assertTrue(self.root.bind_all(event), event)
        self.page._listen_to_wheel(False)
        for event in common.Scrollable.WHEEL_EVENTS:
            self.assertFalse(self.root.bind_all(event), event)


class ShortcutKeys(unittest.TestCase):
    def test_help_names_the_mac_key_on_a_mac(self):
        text = "Enregistre avec Ctrl+S ; Ctrl+Z annule."
        with mock.patch.object(common, "KEY_NAME", "Cmd+"):
            self.assertEqual(common.with_key_name(text), "Enregistre avec Cmd+S ; Cmd+Z annule.")
        if not common.MAC:
            self.assertEqual(common.with_key_name(text), text)
            self.assertEqual(common.KEY, "Control")


if __name__ == "__main__":
    unittest.main()
