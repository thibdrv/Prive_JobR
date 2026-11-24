"""The look of the window: a light theme drawn by Tk itself ("clam"), in the app's colours, light or dark.

It replaces the Windows 11 theme (sv_ttk), which drew every button, field and tab from pictures: changing tab, opening
a tab or resizing the window took 3 to 5 times longer with it. Standard library only.
"""
import tkinter as tk
from tkinter import ttk

# Colours of each look: window, fields and tables, text, faint text, borders, buttons and their states, accent blue
# (with white text: 4.6:1 and more), selection, tabs, table headings, scroll bars
PALETTES = {
    "light": {"bg": "#fafafa", "field": "#ffffff", "text": "#1c1c1c", "muted": "#6b6b6b", "border": "#cfcfcf",
              "button": "#ffffff", "hover": "#eef3fb", "pressed": "#dde8f7", "accent": "#1f6fd1",
              "accent_hover": "#195cb0", "on_accent": "#ffffff", "select": "#cfe2fb", "tab": "#ececec",
              "heading": "#f0f0f0", "thumb": "#c4c4c4", "thumb_hover": "#a8a8a8", "disabled": "#a0a0a0"},
    "dark": {"bg": "#1c1c1c", "field": "#262626", "text": "#f0efec", "muted": "#9a9a9a", "border": "#404040",
             "button": "#2b2b2b", "hover": "#34393f", "pressed": "#3b4552", "accent": "#2f7de1",
             "accent_hover": "#4a90e8", "on_accent": "#ffffff", "select": "#264f78", "tab": "#262626",
             "heading": "#2a2a2a", "thumb": "#4a4a4a", "thumb_hover": "#5e5e5e", "disabled": "#6a6a6a"},
}


def apply(root: tk.Tk, theme: str) -> dict[str, str]:
    """Sets the look of every ttk widget, menu and list; returns the palette used."""
    c = PALETTES.get(theme, PALETTES["light"])
    style = ttk.Style(root)
    style.theme_use("clam")
    flat = {"bordercolor": c["border"], "lightcolor": c["field"], "darkcolor": c["field"]}
    style.configure(".", background=c["bg"], foreground=c["text"], fieldbackground=c["field"], troughcolor=c["bg"],
                    bordercolor=c["border"], lightcolor=c["bg"], darkcolor=c["bg"], focuscolor=c["accent"],
                    selectbackground=c["select"], selectforeground=c["text"], insertcolor=c["text"],
                    arrowcolor=c["text"], insertwidth=1)
    style.map(".", foreground=[("disabled", c["disabled"])])
    style.configure("TLabel", background=c["bg"], foreground=c["text"])

    # buttons
    for name, base, hover, pressed, text in (("TButton", c["button"], c["hover"], c["pressed"], c["text"]),
                                             ("TMenubutton", c["button"], c["hover"], c["pressed"], c["text"]),
                                             ("Accent.TButton", c["accent"], c["accent_hover"], c["accent_hover"],
                                              c["on_accent"])):
        edge = c["accent"] if name == "Accent.TButton" else c["border"]
        style.configure(name, background=base, foreground=text, bordercolor=edge, lightcolor=base, darkcolor=base,
                        padding=(10, 4), relief="raised", arrowcolor=text, focusthickness=0)
        style.map(name, background=[("disabled", c["bg"]), ("pressed", pressed), ("active", hover)],
                  lightcolor=[("pressed", pressed), ("active", hover)],
                  darkcolor=[("pressed", pressed), ("active", hover)],
                  foreground=[("disabled", c["disabled"])])

    # fields
    for name in ("TEntry", "TCombobox", "TSpinbox"):
        style.configure(name, fieldbackground=c["field"], foreground=c["text"], background=c["button"],
                        insertcolor=c["text"], arrowcolor=c["text"], padding=(5, 3), **flat)
        style.map(name, bordercolor=[("focus", c["accent"])], lightcolor=[("focus", c["field"])],
                  fieldbackground=[("readonly", c["field"]), ("disabled", c["bg"])],
                  foreground=[("disabled", c["disabled"])],
                  selectbackground=[("readonly", c["field"])], selectforeground=[("readonly", c["text"])],
                  background=[("active", c["hover"])])

    # ticks and choices: a real tick and a round dot, drawn once as small pictures in the colours of the look
    _indicators(root, style, c)
    for name in ("TCheckbutton", "TRadiobutton"):
        style.configure(name, background=c["bg"], foreground=c["text"], focusthickness=0)
        style.map(name, background=[("active", c["bg"])])

    # tabs
    style.configure("TNotebook", background=c["bg"], bordercolor=c["border"], lightcolor=c["bg"], darkcolor=c["bg"],
                    tabmargins=(0, 2, 0, 0))
    style.configure("TNotebook.Tab", background=c["tab"], foreground=c["text"], padding=(12, 5),
                    bordercolor=c["border"], lightcolor=c["tab"], darkcolor=c["tab"], focuscolor=c["tab"])
    style.map("TNotebook.Tab", background=[("selected", c["bg"]), ("active", c["hover"])],
              lightcolor=[("selected", c["bg"]), ("active", c["hover"])],
              focuscolor=[("selected", c["bg"])], expand=[("selected", (1, 2, 1, 0))])

    # the table
    style.configure("Treeview", background=c["field"], fieldbackground=c["field"], foreground=c["text"], **flat)
    style.map("Treeview", background=[("selected", c["select"])], foreground=[("selected", c["text"])])
    style.configure("Treeview.Heading", background=c["heading"], foreground=c["text"], relief="flat",
                    bordercolor=c["border"], lightcolor=c["heading"], darkcolor=c["heading"], padding=(6, 4))
    style.map("Treeview.Heading", background=[("active", c["hover"])], lightcolor=[("active", c["hover"])])

    # scroll bars, progress, frames with a title, dividers
    for name in ("Vertical.TScrollbar", "Horizontal.TScrollbar"):
        style.configure(name, background=c["thumb"], troughcolor=c["bg"], bordercolor=c["bg"],
                        lightcolor=c["thumb"], darkcolor=c["thumb"], arrowcolor=c["muted"], gripcount=0,
                        arrowsize=12)
        style.map(name, background=[("active", c["thumb_hover"])], lightcolor=[("active", c["thumb_hover"])],
                  darkcolor=[("active", c["thumb_hover"])])
    style.configure("Horizontal.TProgressbar", background=c["accent"], troughcolor=c["tab"], bordercolor=c["tab"],
                    lightcolor=c["accent"], darkcolor=c["accent"], thickness=8)
    style.configure("TLabelframe", background=c["bg"], bordercolor=c["border"], lightcolor=c["bg"],
                    darkcolor=c["bg"])
    style.configure("TLabelframe.Label", background=c["bg"], foreground=c["text"], font="RJBold")
    style.configure("TPanedwindow", background=c["bg"])
    style.configure("Sash", sashthickness=7, gripcount=0, background=c["bg"], lightcolor=c["bg"],
                    darkcolor=c["bg"], bordercolor=c["bg"])
    style.configure("TSeparator", background=c["border"])

    # plain Tk parts: the menus, the lists that open under a choice box, the window itself
    menu = {"background": c["field"], "foreground": c["text"], "activebackground": c["accent"],
            "activeforeground": c["on_accent"], "selectcolor": c["text"], "disabledforeground": c["disabled"]}
    lists = {"background": c["field"], "foreground": c["text"], "selectBackground": c["accent"],
             "selectForeground": c["on_accent"]}
    for option, value in menu.items():
        root.option_add(f"*Menu.{option}", value)
    for option, value in lists.items():
        root.option_add(f"*TCombobox*Listbox.{option}", value)
    root.configure(background=c["bg"])
    _recolor_plain_parts(root, menu, lists)
    return c


_pictures: dict[str, tk.PhotoImage] = {}  # kept here: Tk forgets a picture once Python does


def _indicators(root: tk.Tk, style: ttk.Style, c: dict) -> None:
    """The box of a tick box and the circle of a choice, off, off under the mouse, and on. The pictures are made
    once and redrawn in place when the look changes, so the styles that use them follow."""
    size = max(13, round(13 * root.winfo_fpixels("1i") / 96))  # the size of the text, at any display scale
    looks = {"box": (c["field"], c["muted"], None), "box_hover": (c["field"], c["accent"], None),
             "box_on": (c["accent"], c["accent"], c["on_accent"]), "box_off": (c["bg"], c["disabled"], None)}
    first = not _pictures
    for kind in ("box", "dot"):
        for name, (fill, edge, mark) in looks.items():
            key = name.replace("box", kind)
            picture = _pictures.setdefault(key, tk.PhotoImage(master=root, width=size, height=size))
            _draw_indicator(picture, size, kind, fill, edge, mark, c["bg"])
    if first:
        for kind, element in (("box", "RJ.Checkbutton.indicator"), ("dot", "RJ.Radiobutton.indicator")):
            style.element_create(element, "image", _pictures[kind],
                                 ("disabled", _pictures[f"{kind}_off"]),
                                 ("selected", _pictures[f"{kind}_on"]),
                                 ("active", _pictures[f"{kind}_hover"]),
                                 width=size + round(size / 2), sticky="w")
    for name, element in (("TCheckbutton", "RJ.Checkbutton.indicator"), ("TRadiobutton", "RJ.Radiobutton.indicator")):
        part = name[1:]
        style.layout(name, [(f"{part}.padding", {"sticky": "nswe", "children": [
            (element, {"side": "left", "sticky": ""}),
            (f"{part}.focus", {"side": "left", "sticky": "w", "children": [(f"{part}.label", {"sticky": "nswe"})]}),
        ]})])


def _draw_indicator(picture: tk.PhotoImage, size: int, kind: str, fill: str, edge: str, mark: str | None,
                    outside: str) -> None:
    """A rounded box (kind "box") or a circle ("dot"), with a tick or a dot inside when mark is a colour."""
    rows = []
    middle = (size - 1) / 2
    for y in range(size):
        row = []
        for x in range(size):
            if kind == "dot":
                distance = ((x - middle) ** 2 + (y - middle) ** 2) ** 0.5
                inside, border = distance <= middle, distance > middle - 1.2
                spot = mark and distance <= size * 0.2
            else:
                corner = min(x, size - 1 - x) + min(y, size - 1 - y) < 2  # rounded corners
                inside = not corner
                border = x in (0, size - 1) or y in (0, size - 1) or (min(x, size - 1 - x) + min(y, size - 1 - y)) == 2
                spot = mark and _on_tick(x / (size - 1), y / (size - 1), size)
            row.append(mark if spot else edge if inside and border else fill if inside else outside)
        rows.append("{" + " ".join(row) + "}")
    picture.put(" ".join(rows))


def _on_tick(x: float, y: float, size: int) -> bool:
    """True on the two strokes of a tick ✓, as wide as the size allows."""
    width = 1.6 / size + 0.05
    for (x0, y0), (x1, y1) in (((0.22, 0.52), (0.42, 0.72)), ((0.42, 0.72), (0.78, 0.3))):
        dx, dy = x1 - x0, y1 - y0
        share = max(0.0, min(1.0, ((x - x0) * dx + (y - y0) * dy) / (dx * dx + dy * dy)))
        if ((x - x0 - share * dx) ** 2 + (y - y0 - share * dy) ** 2) ** 0.5 <= width:
            return True
    return False


def _recolor_plain_parts(widget, menu: dict, lists: dict) -> None:
    """The menus and choice lists made before a change of look (the options above apply to the next ones)."""
    if isinstance(widget, tk.Menu):
        widget.configure(**menu)
    elif isinstance(widget, ttk.Combobox):
        try:
            popdown = widget.tk.call("ttk::combobox::PopdownWindow", widget)
            widget.tk.call(f"{popdown}.f.l", "configure", "-background", lists["background"], "-foreground",
                           lists["foreground"], "-selectbackground", lists["selectBackground"],
                           "-selectforeground", lists["selectForeground"])
        except tk.TclError:
            pass
    for child in widget.winfo_children():
        _recolor_plain_parts(child, menu, lists)
