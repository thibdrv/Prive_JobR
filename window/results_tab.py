"""The Results tab: the table of offers, its filters, an offer's details, notes and status."""
import sys
import threading
import time
import tkinter as tk
import webbrowser
from tkinter import messagebox, ttk

import desktop
import settings as app_settings
from i18n import _, value
from window.common import (ALL, CATEGORY_DOTS, EXCEL_FILE, EXPIRED, KEY, MENU_KEY, NO_STATUS, NOT_STATED,
                           STATUS_COLORS, STATUSES, TABLE_COLUMNS, TITLE, TRANSLATED_COLUMNS, marker)
from window.stats_view import StatsView

UNDO_STEPS = 20  # changes of status or note that Ctrl+Z (Cmd+Z on a Mac) can take back


def app_module_started() -> float:
    """When the app started (app.STARTED); now if it was started another way (the tests)."""
    main = sys.modules.get("app") or sys.modules.get("__main__")
    return getattr(main, "STARTED", time.monotonic())


class ResultsTab:
    """The Results tab of the app window. Part of App (app.py), so it shares its attributes."""

    def _build_results(self, tab: ttk.Frame) -> None:
        tools = ttk.Frame(tab)
        tools.pack(fill="x", pady=(0, 8))
        self.filter_category = tk.StringVar(value=_(ALL))
        self.filter_status = tk.StringVar(value=_(ALL))
        self.filter_text = tk.StringVar()
        self.only_new = tk.BooleanVar()
        self.hide_expired = tk.BooleanVar(value=True)
        self.search_descriptions = tk.BooleanVar(value=True)
        self.undo_steps: list[tuple[str, dict[str, tuple[str, str]]]] = []  # (column, link -> (value, date))
        self.markers: dict[tuple, tk.PhotoImage] = {}  # dot and badge pictures, made once each
        self.lower_descriptions: dict[str, str] = {}
        self.category_colors: dict[str, str] = {}
        ttk.Label(tools, text=_("Catégorie")).pack(side="left")
        self.category_box = ttk.Combobox(tools, textvariable=self.filter_category, state="readonly", width=15)
        self.category_box.pack(side="left", padx=(4, 10))
        ttk.Label(tools, text=_("Statut")).pack(side="left")
        ttk.Combobox(tools, textvariable=self.filter_status, state="readonly", width=11,
                     values=[_(ALL), _(NO_STATUS)] + [value(status) for status in STATUSES]).pack(
            side="left", padx=(4, 10))
        ttk.Label(tools, text=_("Rechercher")).pack(side="left")
        ttk.Entry(tools, textvariable=self.filter_text, width=18).pack(side="left", padx=(4, 6))
        ttk.Checkbutton(tools, text=_("aussi dans les descriptions"), variable=self.search_descriptions,
                        command=self._show_offers).pack(side="left")
        more = ttk.Frame(tab)
        more.pack(fill="x", pady=(0, 8))
        self.column_filters = {}  # column -> (variable, combobox): Site, Mode de travail, Contrat
        for column, label, width in (("Site", "Site", 11), ("Mode de travail", "Mode", 9), ("Contrat", "Contrat", 11)):
            ttk.Label(more, text=_(label)).pack(side="left")
            variable = tk.StringVar(value=_(ALL))
            box = ttk.Combobox(more, textvariable=variable, state="readonly", width=width)
            box.pack(side="left", padx=(4, 8))
            self.column_filters[column] = (variable, box)
        ttk.Checkbutton(more, text=_("Nouvelles seulement"), variable=self.only_new,
                        command=self._show_offers).pack(side="left")
        ttk.Checkbutton(more, text=_("Masquer les expirées"), variable=self.hide_expired,
                        command=self._show_offers).pack(side="left", padx=(8, 0))
        ttk.Button(more, text=_("Tout afficher"), command=self._clear_filters).pack(side="right")
        for variable in (self.filter_category, self.filter_status, self.filter_text,
                         *(variable for variable, _box in self.column_filters.values())):
            variable.trace_add("write", lambda *args: self._show_offers())

        actions = ttk.Frame(tab)
        actions.pack(side="bottom", fill="x", pady=(6, 0))
        panes = ttk.PanedWindow(tab, orient="vertical")
        panes.pack(fill="both", expand=True)
        table_box = ttk.Frame(panes)
        details_box = ttk.Frame(panes, padding=(0, 6, 0, 0))
        panes.add(table_box, weight=3)
        panes.add(details_box, weight=2)

        self.table = ttk.Treeview(table_box, columns=list(TABLE_COLUMNS), show="tree headings",
                                  selectmode="extended")
        self.table.column("#0", width=42, minwidth=42, stretch=False)  # the category dot and the status badge
        for column, (heading, width) in TABLE_COLUMNS.items():
            self.table.heading(column, text=_(heading), command=lambda c=column: self._sort_by(c))
            self.table.column(column, width=width, minwidth=40, stretch=column == "Titre",
                              anchor="center" if column == "Score" else "w")
        scroll_y = ttk.Scrollbar(table_box, orient="vertical", command=self.table.yview)
        scroll_x = ttk.Scrollbar(table_box, orient="horizontal", command=self.table.xview)
        self.table.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        scroll_y.pack(side="right", fill="y")
        scroll_x.pack(side="bottom", fill="x")
        self.table.pack(side="left", fill="both", expand=True)
        self.table.bind("<Double-1>", lambda e: self.open_offers())
        self.table.bind("<Return>", lambda e: self.open_offers())
        self.table.bind("<<TreeviewSelect>>", lambda e: self._show_details())
        self.table.bind("<Button-3>", self._offer_menu)  # right-click

        self.details = ttk.Label(details_box, text="", style="Hint.TLabel", wraplength=1000)
        self.details.pack(fill="x")
        notes = ttk.Frame(details_box)
        notes.pack(fill="x", pady=(4, 4))
        self.notes = tk.StringVar()
        ttk.Label(notes, text=_("Notes")).pack(side="left")
        self.notes_entry = ttk.Entry(notes, textvariable=self.notes)
        self.notes_entry.pack(side="left", fill="x", expand=True, padx=6)
        self.notes_entry.bind("<Return>", lambda e: self.save_notes())
        ttk.Button(notes, text=_("Enregistrer la note"), command=self.save_notes).pack(side="left")
        self.load_button = ttk.Button(notes, text=_("Charger la description"), command=self.load_description)
        self.load_button.pack(side="left", padx=(6, 0))
        text_box = ttk.Frame(details_box)
        text_box.pack(fill="both", expand=True)
        self.description = tk.Text(text_box, height=6, wrap="word", state="disabled", relief="flat", borderwidth=8,
                                   font="RJText")
        scroll = ttk.Scrollbar(text_box, command=self.description.yview)
        self.description.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.description.pack(side="left", fill="both", expand=True)

        ttk.Button(actions, text=_("Ouvrir l'offre"), command=self.open_offers, style="Accent.TButton").pack(
            side="left")
        status_button = ttk.Menubutton(actions, text=_("Statut"))
        status_button.configure(menu=self._status_menu(status_button))
        status_button.pack(side="left", padx=(8, 0))
        ttk.Button(actions, text=_("Annuler"), command=self.undo).pack(side="left", padx=(8, 0))
        self.root.bind(f"<{KEY}-z>", self._undo_key)
        self.root.bind(f"<{KEY}-Z>", self._undo_key)
        ttk.Button(actions, text=_("Ouvrir dans Excel"), command=self.open_results).pack(side="right")
        self.count_label = ttk.Label(actions, text="", style="Hint.TLabel")
        self.count_label.pack(side="right", padx=10)

    def load_offers(self, then=None) -> None:
        """Reads jobs.xlsx in the background (after any change still being saved), then shows it; then() after."""
        if not self.ready:
            self.count_label.configure(text=_("Les résultats s'afficheront ici une fois l'installation terminée."))
            return
        self.loads += 1
        number = self.loads
        if then:
            self.after_load = then
        self.count_label.configure(text=_("Chargement des offres…"))

        def read() -> tuple:
            import results_file
            offers = results_file.read_rows(with_new=True)
            order = results_file.category_order([c["name"] for c in app_settings.load()["categories"]], offers)
            return offers, results_file.descriptions(), order

        def done(result: tuple) -> None:
            if number == self.loads:  # else a newer reading is coming
                self.loaded = number
                self._offers_read(*result)
                after, self.after_load = self.after_load, None
                if after:
                    after()

        def failed(error: Exception) -> None:
            if number != self.loads:
                return
            self.loaded, self.after_load = number, None
            self.offers = []
            self.offers_version += 1
            self._show_offers()
            self.count_label.configure(
                text=_("jobs.xlsx est ouvert ailleurs : ferme-le puis appuie sur F5.") if isinstance(
                    error, PermissionError) else _("Impossible de lire jobs.xlsx ({error}).").format(error=error))

        self.files.add(read, done, failed)

    def _offers_read(self, offers: list[dict], descriptions: dict[str, str], order: list[str]) -> None:
        keep = self.table.selection()
        self.offers, self.descriptions, self.lower_descriptions = offers, descriptions, {}
        self.offers_version += 1
        self.category_colors = {name: CATEGORY_DOTS[index % len(CATEGORY_DOTS)] for index, name in enumerate(order)}
        categories = sorted({value(offer.get("Catégorie", "")) for offer in self.offers} - {""})
        self.category_box.configure(values=[_(ALL)] + categories)
        if self.filter_category.get() not in [_(ALL)] + categories:
            self.filter_category.set(_(ALL))
        for column, (variable, box) in self.column_filters.items():
            found = sorted({value(offer.get(column, "")) for offer in self.offers} - {""})
            choices = [_(ALL), *found, _(NOT_STATED)]
            box.configure(values=choices)
            if variable.get() not in choices:
                variable.set(_(ALL))
        self._show_offers()
        self.table.selection_set([iid for iid in keep if self.table.exists(iid)])
        self._show_stats()
        if not self.start_noted:
            self.start_noted = True
            self.root.after_idle(lambda: self.watchdog.note(
                f"start: {time.monotonic() - app_module_started():.1f} s until the {len(self.offers)} offers showed"))

    def _visible_offers(self) -> list[int]:
        """Positions in self.offers of the offers that pass the filters, in the chosen order."""
        category, status = self.filter_category.get(), self.filter_status.get()
        statuses = {value(name): name for name in STATUSES}
        words = self.filter_text.get().lower().split()
        offers = []
        for index, offer in enumerate(self.offers):
            if category != _(ALL) and value(offer.get("Catégorie", "")) != category:
                continue
            if status == _(NO_STATUS) and offer.get("Statut"):
                continue
            if status in statuses and offer.get("Statut") != statuses[status]:
                continue
            if self.only_new.get() and not offer.get("_new"):
                continue
            if any(variable.get() != _(ALL) and (value(offer.get(column, "")) or _(NOT_STATED)) != variable.get()
                   for column, (variable, _box) in self.column_filters.items()):
                continue
            if self.hide_expired.get() and offer.get("En ligne") == EXPIRED:
                continue
            if words:
                text = " ".join(str(text) for key, text in offer.items() if key != "Description").lower()
                if self.search_descriptions.get():
                    text += " " + self._lower_description(offer)
                if not all(word in text for word in words):
                    continue
            offers.append(index)
        column, descending = self.sort
        if column:
            def key(index):
                text = self.offers[index].get(column, "")
                return (0, int(text), "") if column == "Score" and str(text).isdigit() else (1, 0, str(text).lower())
            offers.sort(key=key, reverse=descending)
        return offers

    def _row(self, offer: dict) -> dict:
        """What a table row shows for an offer: colours (tags), dot and badge, the columns."""
        tags = ["new"] if offer.get("_new") else [f"status{STATUSES.index(offer['Statut'])}"] if offer.get(
            "Statut") in STATUSES else []  # one background per row: new offers first, then the status
        if offer.get("En ligne") == EXPIRED:
            tags.append("expired")
        return {"tags": tags, "image": self._marker(offer),
                "values": [value(offer.get(column, "")) if column in TRANSLATED_COLUMNS else offer.get(column, "")
                           for column in TABLE_COLUMNS]}

    def _update_rows(self, indexes: list[int]) -> None:
        """After a status or note change: only these rows are drawn again, the 300 others stay.
        When the change moves offers in or out of the list or in its order (a filter or a sort on what changed),
        the whole list is drawn again."""
        self.offers_version += 1
        keep = self.table.selection()
        if [str(index) for index in self._visible_offers()] != list(self.table.get_children()):
            self._show_offers()
            self.table.selection_set([iid for iid in keep if self.table.exists(iid)])
            return
        for index in indexes:
            if self.table.exists(str(index)):
                self.table.item(str(index), **self._row(self.offers[index]))
        self._show_details()

    def _show_offers(self) -> None:
        self.table.delete(*self.table.get_children())
        visible = self._visible_offers()
        for index in visible:
            self.table.insert("", "end", iid=str(index), **self._row(self.offers[index]))
        new = sum(1 for offer in self.offers if offer.get("_new"))
        self.count_label.configure(text=_("{shown} / {total} offres").format(shown=len(visible), total=len(self.offers))
                                   + (" · " + _("{count} nouvelles").format(count=new) if new else ""))
        self._show_details()

    def _clear_filters(self) -> None:
        for variable in (self.filter_category, self.filter_status,
                         *(variable for variable, _box in self.column_filters.values())):
            variable.set(_(ALL))
        self.filter_text.set("")
        self.only_new.set(False)
        self._show_offers()

    def _sort_by(self, column: str) -> None:
        current, descending = self.sort
        self.sort = (column, not descending if current == column else column == "Score")
        self._show_offers()

    def _selected(self) -> list[dict]:
        return [self.offers[int(iid)] for iid in self.table.selection()]

    def _show_details(self) -> None:
        selected = self._selected()
        description = ""
        if len(selected) == 1:
            offer = selected[0]
            online = {"oui": _("oui"), EXPIRED: _("non, expirée")}.get(offer.get("En ligne", ""), _("pas encore vérifié"))
            self.details.configure(text="   ·   ".join([
                _("Compétences trouvées : {skills}").format(skills=offer.get("Compétences") or _("aucune de ta liste")),
                _("Publiée : {date}").format(date=offer.get("Publiée") or _("non précisé")),
                _("Trouvée le {date}").format(date=offer.get("Trouvée le", "")),
                _("En ligne : {state}").format(state=online)
                + (" " + _("(vérifiée le {date})").format(date=offer["Vérifiée le"]) if offer.get("Vérifiée le") else ""),
                *([_("Statut modifié le {date}").format(date=offer["Statut modifié le"])]
                  if offer.get("Statut modifié le") else []),
                offer.get("Lien", "")]))
            self.notes.set(offer.get("Notes", ""))
            description = offer.get("Description") or self.descriptions.get(offer.get("Lien", ""), "")
            if not description:
                description = _("Pas de description enregistrée pour cette offre : clique sur « Charger la description ».")
        else:
            self.notes.set("")
            self.details.configure(text=_("{count} offres sélectionnées").format(count=len(selected)) if selected else
                                   _("Double-clique sur une offre pour l'ouvrir. Clique sur un titre de colonne pour trier."))
        self.description.configure(state="normal")
        self.description.delete("1.0", "end")
        self.description.insert("1.0", description)
        self._highlight_search()
        self.description.configure(state="disabled")

    def _status_menu(self, parent) -> tk.Menu:
        menu = tk.Menu(parent, tearoff=False)
        for status in STATUSES:
            menu.add_command(label=value(status), command=lambda s=status: self.set_status(s))
        menu.add_separator()
        menu.add_command(label=_("Effacer le statut"), command=lambda: self.set_status(""))
        return menu

    def _offer_menu(self, event) -> None:
        """Right-click on an offer: what you can do with it, without going to the buttons."""
        row = self.table.identify_row(event.y)
        if not row:
            return
        if row not in self.table.selection():
            self.table.selection_set(row)
        menu = tk.Menu(self.table, tearoff=False)
        menu.add_command(label=_("Ouvrir l'offre"), command=self.open_offers)
        menu.add_cascade(label=_("Statut"), menu=self._status_menu(menu))
        menu.add_command(label=_("Copier le lien"), command=self.copy_links)
        menu.add_separator()
        menu.add_command(label=_("Annuler"), accelerator=f"{MENU_KEY}Z", command=self.undo)
        menu.add_command(label=_("Actualiser les résultats"), accelerator="F5", command=self.load_offers)
        menu.tk_popup(event.x_root, event.y_root)

    def copy_links(self) -> None:
        links = [offer["Lien"] for offer in self._selected() if offer.get("Lien")]
        if links:
            self.root.clipboard_clear()
            self.root.clipboard_append("\n".join(links))
            self.status.configure(text=_("{count} lien(s) copié(s).").format(count=len(links)))

    def _highlight_search(self) -> None:
        """Marks the searched words in the description shown."""
        for word in self.filter_text.get().split():
            start = "1.0"
            while len(word) > 1:
                start = self.description.search(word, start, stopindex="end", nocase=True)
                if not start:
                    break
                end = f"{start}+{len(word)}c"
                self.description.tag_add("match", start, end)
                start = end

    def _lower_description(self, offer: dict) -> str:
        link = offer.get("Lien", "")
        if link not in self.lower_descriptions:
            self.lower_descriptions[link] = (offer.get("Description") or self.descriptions.get(link, "")).lower()
        return self.lower_descriptions[link]

    def _marker(self, offer: dict) -> tk.PhotoImage:
        key = (self.category_colors.get(offer.get("Catégorie", "")), STATUS_COLORS.get(offer.get("Statut", "")))
        if key not in self.markers:
            self.markers[key] = marker(*key)
        return self.markers[key]

    def open_offers(self) -> None:
        for offer in self._selected()[:10]:
            if offer.get("Lien"):
                webbrowser.open(offer["Lien"])

    def _can_write(self) -> bool:
        """False, with the reason shown, when the offers can't be changed now."""
        if self.process:
            messagebox.showinfo(TITLE, _("Attends la fin de la recherche pour modifier une offre."))
            return False
        import results_file
        if results_file.is_locked():
            messagebox.showerror(TITLE, _("jobs.xlsx est ouvert dans Excel : ferme-le, puis recommence."))
            return False
        return True

    def _write_field(self, header: str, text: str) -> bool:
        """Changes Statut or Notes of the selected offers: in the table at once, in jobs.xlsx in the background."""
        selected = self._selected()
        if not selected:
            messagebox.showinfo(TITLE, _("Sélectionne d'abord une ou plusieurs offres dans la liste."))
            return False
        if not self._can_write():
            return False
        import results_file
        before = {offer["Lien"]: (offer.get(header, ""), offer.get("Statut modifié le", "")) for offer in selected}
        links = list(before)
        for offer in selected:
            offer[header] = text
            if header == "Statut":
                offer["Statut modifié le"] = time.strftime("%Y-%m-%d") if text else ""
        self.undo_steps = (self.undo_steps + [(header, before)])[-UNDO_STEPS:]
        self.files.add(lambda: results_file.set_field(links, header, text), failed=self._not_saved)
        self._read_again_if_reading()
        return True

    def _read_again_if_reading(self) -> None:
        """A reading of jobs.xlsx asked before this change would show the file without it: read it again after."""
        if self.loaded != self.loads:
            self.load_offers()

    def _not_saved(self, error: Exception) -> None:
        """A change could not reach jobs.xlsx: say so, and show the file as it really is."""
        self.undo_steps.clear()  # they may no longer match the file
        self.load_offers()
        if self.error_shown:  # one message for several changes that failed together
            return
        self.error_shown = True
        try:
            messagebox.showerror(TITLE, _("jobs.xlsx est ouvert dans Excel : ferme-le, puis recommence.")
                                 if isinstance(error, PermissionError) else
                                 _("Le changement n'a pas pu être enregistré dans jobs.xlsx ({error}).").format(
                                     error=error))
        finally:
            self.error_shown = False

    def _undo_key(self, event) -> str | None:
        """Ctrl+Z: in a text field it stays the field's own; elsewhere it takes back the last status or note."""
        if isinstance(event.widget, (tk.Entry, ttk.Entry, tk.Text)):
            return None
        self.undo()
        return "break"

    def undo(self) -> None:
        """Puts back the status or note the last change replaced, in the file and in the table."""
        if not self.undo_steps:
            self.status.configure(text=_("Rien à annuler."))
            return
        if not self._can_write():
            return
        import results_file
        header, before = self.undo_steps.pop()
        groups: dict[tuple[str, str], list[str]] = {}
        for link, old in before.items():
            groups.setdefault(old, []).append(link)

        def write() -> None:
            for (old_value, old_date), links in groups.items():
                results_file.set_field(links, header, old_value)
                if header == "Statut":  # set_field dated the change: give back the earlier date
                    results_file.set_field(links, "Statut modifié le", old_date)
        self.files.add(write, failed=self._not_saved)
        self._read_again_if_reading()
        for offer in self.offers:
            if offer.get("Lien") in before:
                old_value, old_date = before[offer["Lien"]]
                offer[header] = old_value
                if header == "Statut":
                    offer["Statut modifié le"] = old_date
        self._update_rows([index for index, offer in enumerate(self.offers) if offer.get("Lien") in before])
        what = _("statut") if header == "Statut" else _("note")
        self.status.configure(text=_("Annulé : {what} de {count} offre(s).").format(what=what, count=len(before)))

    def set_status(self, status: str) -> None:
        if self._write_field("Statut", status):
            self._update_rows([int(iid) for iid in self.table.selection()])

    def save_notes(self) -> None:
        if self._write_field("Notes", self.notes.get().strip()):
            self._update_rows([int(iid) for iid in self.table.selection()])
            self.status.configure(text=_("Note enregistrée."))

    def load_description(self) -> None:
        """Reads the description of the selected offer from its page, and keeps it for next time."""
        selected = self._selected()
        if len(selected) != 1 or not self.ready:
            return
        link = selected[0].get("Lien", "")
        self.load_button.configure(state="disabled")

        def read() -> None:
            import results_file
            from sources.common import new_session, page_text
            try:
                text, ok = page_text(new_session(), link), True
            except Exception as exc:
                text, ok = _("La page de l'offre n'a pas pu être lue ({error}).").format(error=exc), False
            else:
                def keep() -> None:
                    if self.process:  # the search is writing the same files: the text stays in the window only
                        return
                    results_file.save_descriptions({link: text})
                    try:  # also in the Description column of jobs.xlsx, when Excel doesn't hold it
                        results_file.set_field([link], "Description", text)
                    except PermissionError:
                        pass
                self.files.add(keep)

            def done() -> None:
                if ok:
                    self.descriptions[link] = text
                    self.lower_descriptions.pop(link, None)
                self.load_button.configure(state="normal")
                self._show_details()
                if link not in self.descriptions:
                    self.description.configure(state="normal")
                    self.description.delete("1.0", "end")
                    self.description.insert("1.0", text)
                    self.description.configure(state="disabled")
            self.messages.put(("call", done))
        threading.Thread(target=read, daemon=True).start()

    def open_results(self) -> None:
        if EXCEL_FILE.exists():
            desktop.open_file(EXCEL_FILE)
        else:
            messagebox.showinfo(TITLE, _("Pas encore de résultats : lance d'abord une recherche."))

    def _show_stats(self) -> None:
        """Draws Statistics when it is the tab shown; it is built the first time it is opened, and drawn again
        only when the offers or the look changed since (going back and forth between tabs redraws nothing)."""
        if self.built and not self.rebuilding and self.notebook.select() == str(self.stats_tab):
            if self.stats is None:
                self.stats = StatsView(self.stats_tab)
                self.stats_drawn = None
            drawn = (self.offers_version, self.theme, self.background)
            if drawn != self.stats_drawn:
                self.stats.show(self.offers, self.theme, self.background)
                self.stats_drawn = drawn
