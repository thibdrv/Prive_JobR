"""The Information tab: who made the app, how to use it in a few simple steps, and what the Score means."""
import tkinter as tk
import webbrowser
from tkinter import ttk

from i18n import _
from window.common import with_key_name

CONTACT = "thibaud.derville@outlook.fr"  # shown at the top of the tab; a click on it opens the mail app


def info_sections() -> list[tuple[str, list[str]]]:
    """(heading, paragraphs) of the Information tab, in the chosen language."""
    return [
        (_("À propos"), [
            _("Retrieve Job a été créée par Thibaud. Pour la moindre question, ou s'il manque quelque chose, "
              "écris-moi : {email}").format(email=CONTACT),
        ]),
        (_("À quoi sert Retrieve Job ?"), [
            _("Retrieve Job cherche pour toi les offres d'emploi à Chypre sur une quinzaine de sites, écarte celles "
              "qui ne te conviennent pas et range les autres dans l'onglet Résultats et dans le fichier Excel "
              "results/jobs.xlsx."),
        ]),
        (_("Pour commencer, en 4 étapes"), [
            _("1. Postes : écris les métiers que tu cherches. « Recherches » est ce qui est tapé sur les sites ; "
              "les « Mots du titre » décident dans quelle catégorie va une offre."),
            _("2. Expérience et villes, Autres filtres : dis ce que tu acceptes (années d'expérience, villes, langues "
              "exigées, contrats, salaire minimum…). Une offre qui ne précise pas un point est gardée."),
            _("3. Sites et Entreprises : coche les sites à lire et ajoute les pages carrières des entreprises qui "
              "t'intéressent."),
            _("4. Clique sur « Lancer la recherche », en bas de la fenêtre. La première fois, compte 5 à 15 minutes ; "
              "les suivantes sont plus rapides."),
            _("Le bouton est vert pour lancer la recherche, rouge pour l'arrêter pendant qu'elle tourne."),
            _("Enregistre tes réglages avec « Enregistrer les paramètres » (ou Ctrl+S). Si tu quittes sans "
              "enregistrer, l'application te le rappelle."),
        ]),
        (_("Lire les résultats"), [
            _("Les offres trouvées par la dernière recherche sont en jaune. Les filtres au-dessus du tableau et la case "
              "« Rechercher » (qui lit aussi les descriptions) t'aident à trouver ce que tu veux."),
            _("Clique sur une offre pour lire sa description, double-clique pour l'ouvrir dans ton navigateur, "
              "fais un clic droit pour les autres choix."),
            _("Le menu Statut suit tes candidatures : À voir, Postulé, Entretien, Refusé, Pas intéressé. La ligne prend "
              "la couleur du statut. Ctrl+Z annule le dernier changement."),
            _("« Ouvrir dans Excel » ouvre jobs.xlsx : les mêmes offres, plus une feuille Résumé. Ferme Excel avant de "
              "changer un statut dans l'application."),
        ]),
        (_("Le Score, c'est quoi ?"), [
            _("Le Score dit combien de tes compétences l'offre mentionne. Ta liste de compétences est dans l'onglet "
              "« Autres filtres », champ « Compétences (Score) »."),
            _("L'application lit le titre et la description de l'offre. Chaque compétence trouvée ajoute 1 point, une "
              "seule fois même si le mot revient souvent. Le mot doit être entier : « java » ne compte pas dans "
              "« javascript ». Les majuscules ne changent rien."),
            _("Exemple : avec la liste « python, sql, excel, french », une offre qui demande « SQL, Excel et Python » "
              "a un Score de 3."),
            _("Clique sur le titre de la colonne Score pour voir d'abord les offres qui te correspondent le mieux. "
              "Quand tu cliques sur une offre, les compétences trouvées s'affichent sous le tableau."),
            _("Bon à savoir : chaque compétence vaut 1 point, quelle qu'elle soit. Un mot présent dans presque toutes "
              "les offres (« english » à Chypre) ne départage rien : tu peux le retirer de ta liste. Une offre dont la "
              "page n'a pas pu être lue n'est notée que sur son titre."),
        ]),
        (_("Statistiques"), [
            _("L'onglet Statistiques résume tes offres et tes candidatures en quatre sous-onglets : vue d'ensemble, "
              "offres, candidatures et salaires. Passe la souris sur une barre pour voir sa valeur."),
            _("La couleur d'une barre suit sa valeur, comparée à la plus haute barre du graphique : anthracite et "
              "rouge pour les plus faibles, orange au milieu, vert puis vert clair pour les plus élevées."),
        ]),
        (_("Recherche automatique et sauvegardes"), [
            _("Dans l'onglet Recherche, programme une recherche tous les X jours ou certains jours de la semaine, à "
              "l'heure de ton choix. L'ordinateur doit être allumé à cette heure-là."),
            _("Avant chaque recherche, une copie de jobs.xlsx est gardée. « Restaurer… » remet une ancienne copie en "
              "place si besoin."),
        ]),
        (_("Réglages"), [
            _("Le bouton Réglages, en haut à droite, change la taille du texte, la hauteur des lignes, le thème clair "
              "ou sombre et la langue (français, anglais, grec)."),
        ]),
        (_("En cas de souci"), [
            _("« jobs.xlsx est ouvert dans Excel » : ferme le fichier dans Excel, puis recommence."),
            _("Un site ne donne plus d'offres : il a peut-être changé. Décoche-le dans l'onglet Sites en attendant."),
            _("Si la fenêtre ralentit, se bloque ou affiche une erreur, les détails sont notés dans le dossier "
              ".cache (slow.log, freeze.log et errors.log) : ils aident à trouver la cause."),
        ]),
    ]


class InfoTab:
    """The Information tab of the app window. Part of App (app.py)."""

    def _build_info(self, tab: ttk.Frame) -> None:
        """One text block, with its own scroll bar: one widget to draw instead of thirty labels."""
        ink = getattr(self, "text_colors", ("#ffffff", "#1c1c1c"))[1]
        text = tk.Text(tab, wrap="word", relief="flat", borderwidth=0, highlightthickness=0, padx=4, pady=2,
                       font="RJText", cursor="arrow", background=self.background, foreground=ink, spacing1=2,
                       spacing3=2)
        scroll = ttk.Scrollbar(tab, command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        text.pack(side="left", fill="both", expand=True)
        text.tag_configure("heading", font="RJSection", spacing1=16, spacing3=4)
        text.tag_configure("first", spacing1=0)  # no space above the first heading
        for number, (heading, paragraphs) in enumerate(info_sections()):
            text.insert("end", heading + "\n", ("all", "heading", *(() if number else ("first",))))
            for paragraph in paragraphs:
                text.insert("end", with_key_name(paragraph) + "\n", "all")
        start = text.search(CONTACT, "1.0", stopindex="end")
        if start:  # the address works as a link: a click opens a new mail to it
            text.tag_add("link", start, f"{start}+{len(CONTACT)}c")
            text.tag_configure("link", foreground="#4a90e8" if self.theme == "dark" else "#1f6fd1", underline=True)
            text.tag_bind("link", "<Button-1>", lambda e: webbrowser.open(f"mailto:{CONTACT}"))
            text.tag_bind("link", "<Enter>", lambda e: text.configure(cursor="hand2"))
            text.tag_bind("link", "<Leave>", lambda e: text.configure(cursor="arrow"))
        text.configure(state="disabled")

        def margin(event) -> None:  # lines no longer than is easy to read, on a wide window
            text.tag_configure("all", rmargin=max(0, event.width - 1000))
        text.bind("<Configure>", margin)
