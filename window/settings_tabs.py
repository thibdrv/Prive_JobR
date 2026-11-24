"""The settings tabs: job types, experience and cities, more filters, sites."""
import tkinter as tk
from tkinter import messagebox, ttk

import settings as app_settings
from i18n import _, value
from window.common import TITLE, join_list, split_list


class SettingsTabs:
    """The settings tabs, and the settings between the form and settings.json.

    Part of App (app.py), so it shares its attributes.
    """

    def _make_settings_variables(self) -> None:
        """The values of the settings tabs. They exist from the start, the tabs' widgets only once opened."""
        self.max_years, self.max_age, self.keep_days, self.max_pages = (tk.IntVar() for _i in range(4))
        self.seniority, self.languages, self.cities, self.places, self.exclude, self.remote = (
            tk.StringVar() for _i in range(6))
        self.required, self.forbidden, self.companies_out, self.skills = (tk.StringVar() for _i in range(4))
        self.min_salary = tk.IntVar()
        self.contract_vars = {name: tk.BooleanVar() for name in app_settings.CONTRACTS}
        self.mode_vars = {name: tk.BooleanVar() for name in app_settings.WORK_MODES}
        self.site_vars = {name: tk.BooleanVar() for name in app_settings.SITE_NAMES}
        self.careerfinders_vars = {name: tk.BooleanVar() for name in app_settings.CAREERFINDERS_CATEGORIES}
        self.type_data: list[dict] = []  # the job types while their tab hasn't been opened
        self.type_rows: list[dict] = []  # their widgets, once it has
        self.types_built = False

    def _fields(self, tab: ttk.Frame, fields: list[tuple[str, tk.Widget, str]], start: int = 0) -> int:
        """Label, field and hint, one under the other; returns the next free row."""
        tab.columnconfigure(1, weight=1)
        for row, (label, widget, hint) in enumerate(fields, start=start):
            ttk.Label(tab, text=label).grid(row=2 * row, column=0, sticky="w", padx=(0, 12), pady=(8, 0))
            widget.grid(row=2 * row, column=1, sticky="w" if isinstance(widget, (ttk.Spinbox, ttk.Frame)) else "ew",
                        pady=(8, 0))
            ttk.Label(tab, text=hint, style="Hint.TLabel", wraplength=720).grid(row=2 * row + 1, column=1, sticky="w")
        return start + len(fields)

    def _build_filters(self, tab: ttk.Frame) -> None:
        self._fields(tab, [
            (_("Expérience maximum (années)"), ttk.Spinbox(tab, from_=0, to=15, width=6, textvariable=self.max_years),
             _("Chaque nouvelle offre est lue : si elle demande plus d'années, elle est écartée. "
               "Les titres « junior », « graduate », « trainee »… sont toujours gardés.")),
            (_("Exclure les titres de niveau"), ttk.Entry(tab, textvariable=self.seniority),
             _("Mots séparés par des virgules (senior, lead, director…).")),
            (_("Écarter les offres qui exigent"), ttk.Entry(tab, textvariable=self.languages),
             _("Langues, en anglais, séparées par des virgules (greek, russian…). Une offre est écartée si "
               "elle est écrite dans cette langue ou la demande. « Greek is a plus » ne l'écarte pas.")),
            (_("Villes"), ttk.Entry(tab, textvariable=self.cities),
             _("Avec leurs autres orthographes et leurs quartiers. Les offres qui indiquent seulement « Cyprus » "
               "sont gardées.")),
            (_("Lieux exclus"), ttk.Entry(tab, textvariable=self.places),
             _("Une offre qui cite aussi un de ces lieux est en fait à l'étranger (« Limassol, Dubai »).")),
            (_("Offres publiées depuis moins de (jours)"),
             ttk.Spinbox(tab, from_=1, to=365, width=6, textvariable=self.max_age),
             _("31 = un mois. Ergodotisi ne donne pas la date : ses offres sont toujours gardées.")),
            (_("Retirer du fichier les offres trouvées il y a plus de (jours)"),
             ttk.Spinbox(tab, from_=0, to=365, width=6, textvariable=self.keep_days),
             _("À chaque recherche. Les offres qui ont un Statut restent. 0 = ne jamais retirer.")),
            (_("Autres mots exclus du titre"), ttk.Entry(tab, textvariable=self.exclude),
             _("Par exemple les langues que tu ne parles pas (« Russian speaking sales »…).")),
            (_("Télétravail : zones acceptées"), ttk.Entry(tab, textvariable=self.remote),
             _("Pour les sites de télétravail et Djinni. Beaucoup d'offres sont réservées aux États-Unis.")),
            (_("Pages lues par site et par recherche"), ttk.Spinbox(tab, from_=1, to=10, width=6,
                                                                    textvariable=self.max_pages),
             _("Plus de pages = plus d'offres, mais une recherche plus longue.")),
        ])

    def _build_more_filters(self, tab: ttk.Frame) -> None:
        contracts, modes = ttk.Frame(tab), ttk.Frame(tab)
        for box, variables in ((contracts, self.contract_vars), (modes, self.mode_vars)):
            for name, variable in variables.items():
                ttk.Checkbutton(box, text=value(name), variable=variable).pack(side="left", padx=(0, 14))
        self._fields(tab, [
            (_("Compétences (Score)"), ttk.Entry(tab, textvariable=self.skills),
             _("Chaque compétence trouvée dans l'offre ajoute 1 à son Score : trie par Score pour voir "
               "d'abord les offres qui te correspondent le mieux.")),
            (_("Mots obligatoires dans l'offre"), ttk.Entry(tab, textvariable=self.required),
             _("L'offre doit contenir au moins un de ces mots (par exemple sql, python). Vide = pas de condition.")),
            (_("Mots interdits dans l'offre"), ttk.Entry(tab, textvariable=self.forbidden),
             _("L'offre est écartée si elle contient un de ces mots (« commission only », « night shift »…).")),
            (_("Entreprises exclues"), ttk.Entry(tab, textvariable=self.companies_out),
             _("Les offres de ces entreprises sont ignorées.")),
            (_("Contrats acceptés"), contracts,
             _("Une offre qui ne précise pas son contrat est toujours gardée.")),
            (_("Modes de travail acceptés"), modes,
             _("Une offre qui ne précise pas où l'on travaille est toujours gardée.")),
            (_("Salaire minimum (€ brut par mois)"),
             ttk.Spinbox(tab, from_=0, to=20000, increment=100, width=8, textvariable=self.min_salary),
             _("Les salaires annuels sont divisés par 12. Une offre sans salaire indiqué est gardée. "
               "0 = pas de condition.")),
        ])

    def _build_sites(self, tab: ttk.Frame) -> None:
        ttk.Label(tab, text=_("Sites à interroger :"), font="RJSection").pack(anchor="w", pady=(0, 4))
        sites = ttk.Frame(tab)
        sites.pack(anchor="w", fill="x")
        for index, (name, label) in enumerate(app_settings.SITE_NAMES.items()):
            ttk.Checkbutton(sites, text=_(label), variable=self.site_vars[name]).grid(
                row=index // 2, column=index % 2, sticky="w", padx=(0, 30), pady=2)
        box = ttk.LabelFrame(tab, text=_("Catégories lues sur CareerFinders (toutes leurs offres sont prises, "
                                         "puis passent par les mêmes filtres)"), padding=8)
        box.pack(anchor="w", fill="x", pady=(12, 0))
        for index, name in enumerate(app_settings.CAREERFINDERS_CATEGORIES):
            ttk.Checkbutton(box, text=name, variable=self.careerfinders_vars[name]).grid(
                row=index // 4, column=index % 4, sticky="w", padx=(0, 14), pady=1)

    def _build_types(self, tab: ttk.Frame) -> None:
        self.types_built = True
        self._render_types(self.type_data)

    def _render_types(self, categories: list[dict]) -> None:
        self.type_data = categories
        if not self.types_built:
            return
        for child in self.types_tab.winfo_children():
            child.destroy()
        tab = self.types_tab
        ttk.Label(tab, style="Hint.TLabel", wraplength=900, text=_(
            "Chaque type de poste est une catégorie dans les résultats. « Recherches » est ce qui est tapé "
            "sur chaque site ; une offre va dans la catégorie si son titre contient un des « mots du titre ». "
            "Si un titre correspond à plusieurs types, le premier de la liste gagne. Sépare par des virgules."
        )).grid(row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))
        for column, text in enumerate([_("Nom"), _("Recherches"), _("Mots du titre")]):
            ttk.Label(tab, text=text, font="RJBold").grid(row=1, column=column, sticky="w")
        tab.columnconfigure(1, weight=1)
        tab.columnconfigure(2, weight=2)
        self.type_rows = []
        for index, category in enumerate(categories):
            name = ttk.Entry(tab, width=22)
            name.insert(0, category["name"])
            searches = tk.Text(tab, height=3, width=30, wrap="word", font="RJText", relief="flat",
                               borderwidth=6)
            searches.insert("1.0", join_list(category["searches"]))
            words = tk.Text(tab, height=3, width=50, wrap="word", font="RJText", relief="flat", borderwidth=6)
            words.insert("1.0", join_list(category["title_words"]))
            row = index + 2
            name.grid(row=row, column=0, sticky="nw", padx=(0, 6), pady=3)
            searches.grid(row=row, column=1, sticky="ew", padx=(0, 6), pady=3)
            words.grid(row=row, column=2, sticky="ew", padx=(0, 6), pady=3)
            ttk.Button(tab, text=_("Supprimer"), command=lambda i=index: self._remove_type(i)).grid(
                row=row, column=3, sticky="n", pady=3)
            self.type_rows.append({"name": name, "searches": searches, "words": words})
        ttk.Button(tab, text=_("+ Ajouter un type de poste"), command=self._add_type).grid(
            row=len(categories) + 2, column=0, columnspan=2, sticky="w", pady=(8, 0))
        self._style_texts()

    def _types_from_form(self) -> list[dict]:
        if not self.types_built:
            return [dict(category) for category in self.type_data]
        return [{"name": row["name"].get().strip(),
                 "searches": split_list(row["searches"].get("1.0", "end")),
                 "title_words": split_list(row["words"].get("1.0", "end"))} for row in self.type_rows]

    def _add_type(self) -> None:
        self._render_types(self._types_from_form() + [{"name": "", "searches": [], "title_words": []}])

    def _remove_type(self, index: int) -> None:
        categories = self._types_from_form()
        del categories[index]
        self._render_types(categories)

    # ---- the whole form ----

    def _fill_form(self, settings: dict) -> None:
        self._render_types(settings["categories"])
        self._render_companies(settings["companies"])
        self.check_online_box.configure(variable=self.check_online)
        self.max_years.set(settings["max_experience_years"])
        self.max_age.set(settings["max_age_days"])
        self.keep_days.set(settings["keep_found_days"])
        self.max_pages.set(settings["max_pages"])
        self.seniority.set(join_list(settings["seniority_words"]))
        self.languages.set(join_list(settings["excluded_languages"]))
        self.cities.set(join_list(settings["cities"]))
        self.places.set(join_list(settings["excluded_places"]))
        self.exclude.set(join_list(settings["exclude_words"]))
        self.remote.set(join_list(settings["remote_locations"]))
        self.skills.set(join_list(settings["skills"]))
        self.required.set(join_list(settings["required_words"]))
        self.forbidden.set(join_list(settings["forbidden_words"]))
        self.companies_out.set(join_list(settings["excluded_companies"]))
        self.min_salary.set(settings["min_salary"])
        self.notify.set(settings["notify"])
        self.companies_keep_all.set(settings["companies_keep_all"])
        self.check_online.set(settings["check_online"])
        self.backups_to_keep.set(settings["backups_to_keep"])
        for variables, key in ((self.site_vars, "sources"), (self.contract_vars, "contracts"),
                               (self.mode_vars, "work_modes")):
            for name, var in variables.items():
                var.set(settings[key].get(name, True))
        for name, var in self.careerfinders_vars.items():
            var.set(name in settings["careerfinders_categories"])

    def _settings_from_form(self, quiet: bool = False) -> dict | None:
        """The settings as the form shows them; None when a field is wrong (said in a message unless quiet)."""
        settings = app_settings.load()
        try:
            settings["max_experience_years"] = int(self.max_years.get())
            settings["max_age_days"] = int(self.max_age.get())
            settings["keep_found_days"] = int(self.keep_days.get())
            settings["max_pages"] = int(self.max_pages.get())
            settings["min_salary"] = int(self.min_salary.get())
            settings["backups_to_keep"] = int(self.backups_to_keep.get())
        except (tk.TclError, ValueError):
            if not quiet:
                messagebox.showerror(TITLE, _("L'expérience, les jours, les pages et le salaire doivent être des "
                                              "nombres."))
            return None
        categories = self._types_from_form()
        if any(not c["name"] and (c["searches"] or c["title_words"]) for c in categories):
            if not quiet:
                messagebox.showerror(TITLE, _("Donne un nom à chaque type de poste."))
            return None
        settings["categories"] = [c for c in categories if c["name"]]
        settings["companies"] = [c for c in self._companies_from_form() if c["id"]]
        settings["seniority_words"] = split_list(self.seniority.get())
        settings["excluded_languages"] = split_list(self.languages.get())
        settings["cities"] = split_list(self.cities.get())
        settings["excluded_places"] = split_list(self.places.get())
        settings["exclude_words"] = split_list(self.exclude.get())
        settings["remote_locations"] = split_list(self.remote.get())
        settings["skills"] = split_list(self.skills.get())
        settings["required_words"] = split_list(self.required.get())
        settings["forbidden_words"] = split_list(self.forbidden.get())
        settings["excluded_companies"] = split_list(self.companies_out.get())
        settings["sources"] = {name: var.get() for name, var in self.site_vars.items()}
        settings["contracts"] = {name: var.get() for name, var in self.contract_vars.items()}
        settings["work_modes"] = {name: var.get() for name, var in self.mode_vars.items()}
        settings["careerfinders_categories"] = [name for name, var in self.careerfinders_vars.items() if var.get()]
        settings["notify"] = self.notify.get()
        settings["companies_keep_all"] = self.companies_keep_all.get()
        settings["check_online"] = self.check_online.get()
        settings["theme"] = self.theme
        return settings

    def save_settings(self) -> bool:
        settings = self._settings_from_form()
        if settings is None:
            return False
        app_settings.save(settings)
        self.status.configure(text=_("Paramètres enregistrés dans {file}.").format(file=app_settings.SETTINGS_FILE.name))
        return True

    def reset_settings(self) -> None:
        if messagebox.askyesno(TITLE, _("Remettre tous les paramètres par défaut ? "
                                        "(Ils seront enregistrés au prochain « Enregistrer » ou à la recherche.)")):
            self._fill_form(app_settings.DEFAULTS)
