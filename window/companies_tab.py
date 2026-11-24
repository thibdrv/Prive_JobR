"""The Companies tab: the followed companies' careers pages."""
import threading
import tkinter as tk
from tkinter import messagebox, ttk

import settings as app_settings
from i18n import _
from window.common import TITLE, company_from_link, split_list


class CompaniesTab:
    """The Companies tab. Part of App (app.py), so it shares its attributes."""

    def _build_companies(self, tab: ttk.Frame) -> None:
        self.companies_built = True
        self._render_companies(self.company_data)

    def _render_companies(self, companies: list[dict]) -> None:
        self.company_data = companies  # kept as data until the tab is opened
        if not getattr(self, "companies_built", False):
            return
        for child in self.companies_tab.winfo_children():
            child.destroy()
        tab = self.companies_tab
        ttk.Label(tab, style="Hint.TLabel", wraplength=900, text=_(
            "Les offres à Chypre des pages carrières de ces entreprises sont lues directement (case « Pages "
            "carrières des entreprises suivies » de l'onglet Sites). Ça marche pour les entreprises qui recrutent "
            "avec Greenhouse, Lever, Workable ou SmartRecruiters : colle le lien de leur page d'offres "
            "(par exemple https://jobs.lever.co/capital) et clique sur Ajouter."
        )).grid(row=0, column=0, columnspan=5, sticky="w", pady=(0, 8))
        paste = ttk.Frame(tab)
        paste.grid(row=1, column=0, columnspan=5, sticky="ew", pady=(0, 10))
        self.company_link = tk.StringVar()
        ttk.Label(paste, text=_("Lien de la page d'offres")).pack(side="left")
        ttk.Entry(paste, textvariable=self.company_link, width=60).pack(side="left", padx=6, fill="x", expand=True)
        ttk.Button(paste, text=_("Ajouter"), command=self._add_company_from_link).pack(side="left")
        for column, text in enumerate([_("Nom"), _("Plateforme"), _("Identifiant")]):
            ttk.Label(tab, text=text, font="RJBold").grid(row=2, column=column, sticky="w")
        tab.columnconfigure(0, weight=1)
        tab.columnconfigure(2, weight=1)
        platform_names = {code: name for name, code in app_settings.COMPANY_PLATFORMS.items()}
        self.company_rows = []
        for index, company in enumerate(companies):
            name, platform, ident = ttk.Entry(tab), ttk.Combobox(
                tab, state="readonly", width=16, values=list(app_settings.COMPANY_PLATFORMS)), ttk.Entry(tab)
            name.insert(0, company.get("name", ""))
            platform.set(platform_names.get(company.get("platform"), "Greenhouse"))
            ident.insert(0, company.get("id", ""))
            result = ttk.Label(tab, text="", style="Hint.TLabel", width=24)
            row = index + 3
            name.grid(row=row, column=0, sticky="ew", padx=(0, 6), pady=2)
            platform.grid(row=row, column=1, sticky="w", padx=(0, 6), pady=2)
            ident.grid(row=row, column=2, sticky="ew", padx=(0, 6), pady=2)
            buttons = ttk.Frame(tab)
            buttons.grid(row=row, column=3, sticky="w", pady=2)
            entry = {"name": name, "platform": platform, "id": ident, "result": result}
            ttk.Button(buttons, text=_("Tester"), command=lambda e=entry: self._test_company(e)).pack(side="left")
            ttk.Button(buttons, text=_("Supprimer"), command=lambda i=index: self._remove_company(i)).pack(
                side="left", padx=4)
            result.grid(row=row, column=4, sticky="w")
            self.company_rows.append(entry)
        ttk.Button(tab, text=_("+ Ajouter une entreprise à la main"), command=self._add_company).grid(
            row=len(companies) + 3, column=0, sticky="w", pady=(8, 0))
        ttk.Checkbutton(tab, variable=self.companies_keep_all, text=_(
            "Garder aussi leurs offres qui ne correspondent à aucun type de poste (catégorie « Entreprises "
            "suivies »)")).grid(row=len(companies) + 4, column=0, columnspan=5, sticky="w", pady=(12, 0))
        ttk.Label(tab, style="Hint.TLabel", text=_(
            "Sans cette case, leurs offres passent par les mêmes filtres que les autres sites (types de poste, "
            "niveau, expérience, langue…).")).grid(row=len(companies) + 5, column=0, columnspan=5, sticky="w")

    def _companies_from_form(self) -> list[dict]:
        if not getattr(self, "companies_built", False):
            return [dict(company) for company in self.company_data]
        return [{"name": row["name"].get().strip() or row["id"].get().strip(),
                 "platform": app_settings.COMPANY_PLATFORMS.get(row["platform"].get(), "greenhouse"),
                 "id": row["id"].get().strip()} for row in self.company_rows]

    def _add_company(self, company: dict | None = None) -> None:
        self._render_companies(self._companies_from_form() + [company or {"name": "", "platform": "greenhouse",
                                                                          "id": ""}])

    def _add_company_from_link(self) -> None:
        company = company_from_link(self.company_link.get())
        if not company:
            messagebox.showinfo(TITLE, _("Ce lien n'est pas une page Greenhouse, Lever, Workable ou SmartRecruiters. "
                                         "Sur le site de l'entreprise, ouvre une offre : son adresse indique souvent "
                                         "la plateforme (jobs.lever.co/…, boards.greenhouse.io/…)."))
            return
        company["name"] = company["id"].replace("-", " ").title()
        self._add_company(company)
        self.company_link.set("")

    def _remove_company(self, index: int) -> None:
        companies = self._companies_from_form()
        del companies[index]
        self._render_companies(companies)

    def _test_company(self, entry: dict) -> None:
        if not self.ready:
            messagebox.showinfo(TITLE, _("Attends la fin de l'installation."))
            return
        company = {"name": entry["name"].get().strip() or "?", "id": entry["id"].get().strip(),
                   "platform": app_settings.COMPANY_PLATFORMS.get(entry["platform"].get(), "greenhouse")}
        entry["result"].configure(text=_("Test en cours…"))
        cities = split_list(self.cities.get())

        def test() -> None:
            from sources import company_jobs
            from sources.common import Settings, new_session
            try:
                count = len(company_jobs(new_session(), company, Settings(1, 31, [], cities=cities)))
                text = _("{count} offre(s) à Chypre").format(count=count) if count else _("OK, aucune offre à Chypre")
            except Exception:
                text = _("Introuvable : vérifie l'identifiant")
            self.messages.put(("call", lambda: entry["result"].configure(text=text)))
        threading.Thread(target=test, daemon=True).start()
