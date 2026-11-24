"""The Statistics tab: key figures and bar charts drawn from the offers in jobs.xlsx, in four sub-tabs.

Standard library only (tkinter canvas). Each bar is shaded by its value within its chart, along one gradient:
anthracite and red for the low ones, sand orange in the middle, green then light green for the high ones; the text
stays in the ink colours, and hovering a bar shows its exact value.
The salary charts use the offers that give a salary in euros: their median, and how many offers it is based on.
"""
import re
import statistics
import tkinter as tk
from collections import Counter
from datetime import date, timedelta
from tkinter import font as tkfont
from tkinter import ttk

from i18n import _, value
from window.common import STATUSES

# The bar gradient, from the lowest value (0) to the highest (1): (position, colour), mixed in between
GRADIENT = [(0.0, "#24262a"), (0.14, "#5c2328"), (0.27, "#a3161e"), (0.4, "#c4593a"), (0.52, "#e0a45c"),
            (0.66, "#979449"), (0.8, "#5a8c30"), (1.0, "#93d38e")]
# Ink (primary, secondary, muted, gridline), tooltip, the key-figure cards (background, border), and the gradient.
# On the dark surface the gradient starts from a lighter grey, as anthracite bars would not show on it.
COLORS = {"light": {"ink": ("#0b0b0b", "#52514e", "#898781", "#e1e0d9"), "tip": "#ffffff",
                    "card": ("#ffffff", "#e1e0d9"), "gradient": GRADIENT},
          "dark": {"ink": ("#f0efec", "#c3c2b7", "#898781", "#2c2c2a"), "tip": "#2b2b2b",
                   "card": ("#262626", "#383835"), "gradient": [(0.0, "#5f6167"), *GRADIENT[1:]]}}
# The coloured edge of each key-figure card
FIGURE_COLORS = {"offers": "#2a78d6", "new": "#e0a106", "expired": "#8a8a8a", "median": "#2e9e5b",
                 "with_salary": "#2e9e5b", "applied": "#2a78d6", "interviews": "#2e9e5b", "rate": "#8e5cc7",
                 "to_review": "#e0a106"}
FONT = "RJText"  # named font of the window: follows the chosen text size
# The cities of the salary chart, with the other names and districts the offers use for them
CITIES = {"Nicosia": ["nicosia", "lefkosia", "strovolos", "aglantzia", "engomi", "egkomi", "lakatamia", "latsia"],
          "Limassol": ["limassol", "lemesos", "ypsonas", "germasogeia", "agios athanasios", "mesa geitonia",
                       "polemidia"],
          "Larnaca": ["larnaca", "larnaka", "aradippou", "livadia", "oroklini", "dromolaxia"],
          "Pyla": ["pyla"], "Dali": ["dali", "idalion"], "Paphos": ["paphos", "pafos"],
          "Famagusta": ["famagusta", "ammochostos", "ayia napa", "paralimni"]}


# The sub-tabs: name, key figures on top, charts (key, columns taken in a 2-column grid)
PAGES = [
    ("Vue d'ensemble", ["offers", "new", "expired", "median"], [("weeks", 2), ("statuses", 1), ("categories", 1)]),
    ("Offres", [], [("categories", 1), ("sites", 1), ("cities", 1), ("modes", 1)]),
    ("Candidatures", ["applied", "interviews", "rate", "to_review"], [("statuses", 1), ("applications", 1)]),
    ("Salaires", ["median", "with_salary"], [("salary_categories", 1), ("salary_cities", 1)]),
]
APPLIED = ("Postulé", "Entretien", "Refusé")  # statuses that mean you sent an application


class StatsView:
    def __init__(self, parent: ttk.Frame):
        self.offers: list[dict] = []
        self.theme = "light"
        self.background = "#fafafa"
        legend = ttk.Frame(parent)
        legend.pack(fill="x", pady=(0, 6))
        ttk.Label(legend, text=_("Couleur des barres :"), style="Hint.TLabel").pack(side="left")
        ttk.Label(legend, text=_("faible"), style="Hint.TLabel").pack(side="left", padx=(8, 4))
        self.legend = tk.Canvas(legend, width=180, height=12, highlightthickness=0, borderwidth=0)
        self.legend.pack(side="left")
        ttk.Label(legend, text=_("élevée"), style="Hint.TLabel").pack(side="left", padx=(4, 0))
        self.pages = ttk.Notebook(parent)
        self.pages.pack(fill="both", expand=True)
        self.tiles: list[tuple[ttk.Frame, list[str]]] = []
        self.charts: list[tuple[str, ttk.Label, tk.Canvas]] = []
        self.drawn: dict[tk.Canvas, tuple[int, int]] = {}  # size each chart was drawn at; missing = to draw
        self.waiting: dict[tk.Canvas, str] = {}  # charts to draw again once a resize is over
        for name, tiles, charts in PAGES:
            page = ttk.Frame(self.pages, padding=(4, 10, 4, 4))
            self.pages.add(page, text=_(name))
            if tiles:
                row = ttk.Frame(page)
                row.pack(fill="x", pady=(0, 6))
                self.tiles.append((row, tiles))
            grid = ttk.Frame(page)
            grid.pack(fill="both", expand=True)
            grid.columnconfigure((0, 1), weight=1, uniform="charts")
            column = line = 0
            for key, span in charts:
                if column + span > 2:
                    column, line = 0, line + 1
                box = ttk.Frame(grid)
                box.grid(row=line, column=column, columnspan=span, sticky="nsew", padx=6, pady=6)
                grid.rowconfigure(line, weight=1)
                title = ttk.Label(box, font="RJSection")
                title.pack(anchor="w")
                canvas = tk.Canvas(box, height=150, highlightthickness=0, borderwidth=0)
                canvas.pack(fill="both", expand=True, pady=(4, 0))
                chart = (key, title, canvas)
                canvas.bind("<Configure>", lambda e, c=chart: self._resized(c))
                canvas.bind("<Map>", lambda e, c=chart: self._resized(c))  # a sub-tab shown
                self.charts.append(chart)
                column += span

    def show(self, offers: list[dict], theme: str, background: str) -> None:
        self.offers, self.theme, self.background = offers, theme, background
        self._draw_legend()
        figures = self._figures()
        for row, keys in self.tiles:
            self._draw_tiles(row, [(*figures[key], FIGURE_COLORS[key]) for key in keys])
        self.drawn.clear()  # every chart is to draw again; those of the other sub-tabs when they are shown
        for chart in self.charts:
            if chart[2].winfo_ismapped():
                self._draw(*chart)

    def _resized(self, chart: tuple) -> None:
        """A chart shown or resized. Drawn at once the first time (no blank chart); when the window is being
        resized, only once the size stops changing for a moment, not at every pixel."""
        canvas = chart[2]
        size = (canvas.winfo_width(), canvas.winfo_height())
        if not canvas.winfo_ismapped() or self.drawn.get(canvas) == size:
            return
        if canvas in self.waiting:
            canvas.after_cancel(self.waiting.pop(canvas))
        if canvas not in self.drawn:
            self._draw(*chart)
            return

        def draw() -> None:
            self.waiting.pop(canvas, None)
            self._draw(*chart)
        self.waiting[canvas] = canvas.after(150, draw)

    # ---- the key figures ----

    def _figures(self) -> dict[str, tuple]:
        statuses = Counter(offer.get("Statut", "") for offer in self.offers)
        applied = sum(statuses[status] for status in APPLIED)
        answers = statuses["Entretien"] + statuses["Refusé"]
        pay = [amount for offer in self.offers if (amount := salary(offer))]
        return {
            "offers": (len(self.offers), _("offres dans le fichier")),
            "new": (sum(1 for offer in self.offers if offer.get("_new")), _("nouvelles à la dernière recherche")),
            "expired": (sum(1 for offer in self.offers if offer.get("En ligne") == "expirée"), _("offres expirées")),
            "median": (self._euros(statistics.median(pay)) if pay else "–", _("salaire médian (€ brut / mois)")),
            "with_salary": (len(pay), _("offres avec un salaire en €")),
            "applied": (applied, _("candidatures envoyées")),
            "interviews": (statuses["Entretien"], _("entretiens")),
            "rate": (f"{round(100 * answers / applied)} %" if applied else "–", _("taux de réponse")),
            "to_review": (statuses["À voir"], _("offres à voir")),
        }

    def _draw_tiles(self, row: ttk.Frame, tiles: list[tuple]) -> None:
        """One card per key figure: a coloured edge, the number, what it counts."""
        for child in row.winfo_children():
            child.destroy()
        colors = COLORS[self.theme]
        background, border = colors["card"]
        for column, (number, caption, color) in enumerate(tiles):
            row.columnconfigure(column, weight=1, uniform="tiles")
            card = tk.Frame(row, background=background, highlightthickness=1, highlightbackground=border)
            card.grid(row=0, column=column, sticky="nsew", padx=4)
            tk.Frame(card, background=color, width=5).pack(side="left", fill="y")
            inside = tk.Frame(card, background=background, padx=10, pady=6)
            inside.pack(side="left", fill="both", expand=True)
            tk.Label(inside, text=str(number), font="RJNumber", background=background,
                     foreground=colors["ink"][0]).pack(anchor="w")
            tk.Label(inside, text=caption, font="RJText", background=background, foreground=colors["ink"][1],
                     wraplength=170, justify="left").pack(anchor="w")

    # ---- the charts ----

    def _shade(self, number: float, highest: float) -> str:
        """The colour of a bar, from its share of the highest one of its chart, along the gradient
        (so nearly equal values get nearly the same colour)."""
        stops = COLORS[self.theme]["gradient"]
        share = max(0.0, min(1.0, number / highest)) if highest > 0 else 1.0
        for (start, first), (end, last) in zip(stops, stops[1:]):
            if share <= end:
                return _mix(first, last, (share - start) / (end - start))
        return stops[-1][1]

    def _draw_legend(self) -> None:
        self.legend.configure(background=self.background)
        self.legend.delete("all")
        steps = 90
        for step in range(steps):
            x = 180 * step / steps
            self.legend.create_rectangle(x, 0, x + 180 / steps + 1, 12, width=0,
                                         fill=self._shade(step, steps - 1))

    def _draw(self, key: str, title: ttk.Label, canvas: tk.Canvas) -> None:
        self.drawn[canvas] = (canvas.winfo_width(), canvas.winfo_height())
        canvas.configure(background=self.background)
        canvas.delete("all")
        if key == "weeks":
            title.configure(text=_("Offres trouvées par semaine"))
            self._columns(canvas, self._weeks(self.offers, "Trouvée le"))
        elif key == "applications":
            title.configure(text=_("Candidatures par semaine (date du statut)"))
            sent = [offer for offer in self.offers if offer.get("Statut") in APPLIED]
            self._columns(canvas, self._weeks(sent, "Statut modifié le"))
        elif key == "statuses":
            title.configure(text=_("Tes candidatures (statuts)"))
            counts = Counter(offer.get("Statut", "") for offer in self.offers)
            self._rows(canvas, [(value(status), counts[status]) for status in STATUSES])
        elif key == "categories":
            title.configure(text=_("Offres par catégorie"))
            self._rows(canvas, self._top(lambda offer: value(offer.get("Catégorie", ""))))
        elif key == "sites":
            title.configure(text=_("Offres par site"))
            self._rows(canvas, self._top(lambda offer: offer.get("Site", "")))
        elif key == "cities":
            title.configure(text=_("Offres par ville"))
            self._rows(canvas, self._top(city))
        elif key == "modes":
            title.configure(text=_("Offres par mode de travail"))
            self._rows(canvas, self._top(lambda offer: value(offer.get("Mode de travail", ""))))
        elif key == "salary_categories":
            title.configure(text=_("Salaire médian par catégorie (€ brut / mois)"))
            self._rows(canvas, self._salaries(lambda offer: value(offer.get("Catégorie", "")) or "?"))
        else:
            title.configure(text=_("Salaire médian par ville (€ brut / mois)"))
            self._rows(canvas, self._salaries(city))

    @staticmethod
    def _weeks(offers: list[dict], column: str) -> list[tuple[str, int, str]]:
        """The last 8 weeks, oldest first: (short label, offers dated that week, label for the tooltip)."""
        found = Counter()
        for offer in offers:
            try:
                day = date.fromisoformat(offer.get(column, "")[:10])
            except ValueError:
                continue
            found[day - timedelta(days=day.weekday())] += 1
        monday = date.today() - timedelta(days=date.today().weekday())
        weeks = [monday - timedelta(weeks=n) for n in range(7, -1, -1)]
        return [(f"{week.day:02d}/{week.month:02d}", found[week],
                 _("Semaine du {date}").format(date=f"{week.day:02d}/{week.month:02d}")) for week in weeks]

    def _top(self, group) -> list[tuple[str, int]]:
        """The 7 biggest groups, then all the others together."""
        counts = Counter(group(offer) or value("non précisé") for offer in self.offers)
        top = counts.most_common(7)
        rest = sum(counts.values()) - sum(count for _name, count in top)
        return top + ([(_("Autres"), rest)] if rest else [])

    def _salaries(self, group) -> list[tuple[str, int, str, str]]:
        """Median salary of each group (category, city), highest first, from the offers that give one in euros."""
        pay: dict[str, list[int]] = {}
        for offer in self.offers:
            amount = salary(offer)
            if amount:
                pay.setdefault(group(offer), []).append(amount)
        rows = []
        for name, amounts in sorted(pay.items(), key=lambda item: -statistics.median(item[1]))[:8]:
            median = round(statistics.median(amounts))
            tip = _("{name} : médiane {median} €/mois, de {low} à {high}, {count} offre(s)").format(
                name=name, median=self._euros(median), low=self._euros(min(amounts)), high=self._euros(max(amounts)),
                count=len(amounts))
            rows.append((name, median, f"{self._euros(median)} € ({len(amounts)})", tip))
        return rows

    @staticmethod
    def _euros(amount: float) -> str:
        return f"{round(amount):,}".replace(",", " ")

    def _columns(self, canvas: tk.Canvas, weeks: list[tuple[str, int, str]]) -> None:
        colors = COLORS[self.theme]
        primary, _secondary, muted, grid = colors["ink"]
        width, height = max(canvas.winfo_width(), 200), max(canvas.winfo_height(), 120)
        if not any(count for _label, count, _tip in weeks):
            canvas.create_text(width / 2, height / 2, text=_("Pas encore de données"), fill=muted, font=FONT)
            return
        top, bottom, left = 18, height - 22, 8
        highest = max(count for _label, count, _tip in weeks)
        slot = (width - 2 * left) / len(weeks)
        canvas.create_line(left, bottom, width - left, bottom, fill=grid)
        for index, (label, count, tip) in enumerate(weeks):
            x0 = left + index * slot + slot * 0.2
            x1 = left + (index + 1) * slot - slot * 0.2
            y0 = bottom - (bottom - top) * count / highest
            canvas.create_text((x0 + x1) / 2, bottom + 11, text=label, fill=muted, font=FONT)
            if not count:
                continue
            bar = canvas.create_rectangle(x0, y0, x1, bottom, fill=self._shade(count, highest), width=0)
            if index == len(weeks) - 1:  # the current week gets its number
                canvas.create_text((x0 + x1) / 2, y0 - 9, text=str(count), fill=primary, font=FONT)
            self._tooltip(canvas, bar, f"{tip} : {count}")

    def _rows(self, canvas: tk.Canvas, items: list[tuple]) -> None:
        """Horizontal bars: (name, number), or (name, number, text at the end of the bar, tooltip)."""
        colors = COLORS[self.theme]
        primary, secondary, muted, _grid = colors["ink"]
        width, height = max(canvas.winfo_width(), 200), max(canvas.winfo_height(), 100)
        if not items or not any(item[1] for item in items):
            canvas.create_text(width / 2, height / 2, text=_("Pas encore de données"), fill=muted, font=FONT)
            return
        font = tkfont.nametofont(FONT)
        names = [item[0] if len(item[0]) <= 22 else item[0][:21] + "…" for item in items]
        ends = [item[2] if len(item) > 2 else str(item[1]) for item in items]
        label_width = min(220, max(font.measure(name) for name in names) + 16)
        number_width = max(font.measure(end) for end in ends) + 12
        highest = max(item[1] for item in items)
        row = min(font.metrics("linespace") + 10, (height - 4) / len(items))
        for index, (item, shown, end) in enumerate(zip(items, names, ends)):
            name, number = item[0], item[1]
            y = 2 + index * row
            middle = y + row / 2
            canvas.create_text(label_width - 8, middle, text=shown, anchor="e", fill=secondary, font=FONT)
            length = (width - label_width - number_width) * number / highest
            bar = canvas.create_rectangle(label_width, y + row * 0.2, label_width + max(length, 2), y + row * 0.8,
                                          fill=self._shade(number, highest), width=0)
            canvas.create_text(label_width + length + 6, middle, text=end, anchor="w", fill=primary, font=FONT)
            self._tooltip(canvas, bar, item[3] if len(item) > 3 else f"{name} : {number}")

    def _tooltip(self, canvas: tk.Canvas, item: int, text: str) -> None:
        """Shows the exact value next to the pointer while it is over the bar."""
        colors = COLORS[self.theme]

        def show(event) -> None:
            # The tooltip must never be under the pointer: there it hid the bar, the pointer "left" the bar,
            # the tooltip went, the pointer was back on the bar... an endless loop that froze the window.
            # So it goes up-right of the pointer, or up-left when there is no room on the right, or below it
            # at the top of the chart; and it is disabled, so the pointer never "enters" it.
            canvas.delete("tooltip")
            label = canvas.create_text(0, 0, text=text, fill=colors["ink"][0], font=FONT, tags="tooltip",
                                       state="disabled")
            x0, y0, x1, y1 = canvas.bbox(label)
            right = event.x + 14 + (x1 - x0) + 6 <= canvas.winfo_width()
            above = event.y - 14 - (y1 - y0) - 3 >= 0
            anchor = ("s" if above else "n") + ("w" if right else "e")
            canvas.itemconfigure(label, anchor=anchor)
            canvas.coords(label, event.x + (14 if right else -14), event.y + (-14 if above else 14))
            x0, y0, x1, y1 = canvas.bbox(label)
            box = canvas.create_rectangle(x0 - 6, y0 - 3, x1 + 6, y1 + 3, fill=colors["tip"],
                                          outline=colors["ink"][3], tags="tooltip", state="disabled")
            canvas.tag_lower(box, label)

        canvas.tag_bind(item, "<Enter>", show)
        canvas.tag_bind(item, "<Motion>", show)
        canvas.tag_bind(item, "<Leave>", lambda e: canvas.delete("tooltip"))


def _mix(start: str, end: str, share: float) -> str:
    """The colour share of the way from start to end ("#rrggbb")."""
    first, last = (tuple(int(color[i:i + 2], 16) for i in (1, 3, 5)) for color in (start, end))
    return "#" + "".join(f"{round(a + (b - a) * share):02x}" for a, b in zip(first, last))


def salary(offer: dict) -> int | None:
    """The middle of the offer's salary range in € per month ("1 500–2 000 €/mois" -> 1750), None without one."""
    match = re.fullmatch(r"([\d ]+?)(?:–([\d ]+?))? € */mois", offer.get("Salaire", "").strip())
    if not match:
        return None  # no salary, or in dollars or pounds
    low = int(match.group(1).replace(" ", ""))
    high = int((match.group(2) or match.group(1)).replace(" ", ""))
    return round((low + high) / 2)


def city(offer: dict) -> str:
    """The Cypriot city of the offer, as named in CITIES; "Télétravail" or "Autres" when it has none."""
    location = offer.get("Ville", "").lower()
    places = [(location.find(alias), name) for name, aliases in CITIES.items() for alias in aliases
              if re.search(rf"\b{re.escape(alias)}", location)]
    if places:
        return min(places)[1]  # the first city the offer names
    if offer.get("Mode de travail") == "Télétravail" or "remote" in location:
        return _("Télétravail")
    return _("Chypre, ville non précisée") if "cyprus" in location else _("Autres")
