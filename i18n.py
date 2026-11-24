"""The app's languages. Texts are written in French in the code; _() gives them in the chosen language.

The data keeps its French names inside the app (settings, columns, statuses); they are translated only
where you see them: the window, the search log, the notification and jobs.xlsx.
Each language is a file in the languages folder. Standard library only.
"""
import re

from languages import el, en

LANGUAGES = {"fr": "Français", "en": "English", "el": "Ελληνικά"}
TRANSLATIONS = {"en": en.TEXTS, "el": el.TEXTS}
_YEARS = {"fr": "ans", "en": "yrs", "el": "έτη"}  # "3+ ans" in the Experience column
_MONTH = {"fr": "/mois", "en": "/month", "el": "/μήνα"}  # "1 500 €/mois" in the Salary column
_language = "fr"

# Values written in jobs.xlsx, recognised in every language when it is read back
_VALUES = [
    'Nouvelle',
    'Trouvée par',
    'Statut modifié le',
    'Vérifiée le',
    'Description',
    'non',
    'Trouvée le',
    'Catégorie',
    'Score',
    'Titre',
    'Entreprise',
    'Ville',
    'Publiée',
    'Expérience',
    'Contrat',
    'Mode de travail',
    'Salaire',
    'Compétences',
    'Site',
    'Lien',
    'Statut',
    'Notes',
    'En ligne',
    'À voir',
    'Postulé',
    'Entretien',
    'Refusé',
    'Pas intéressé',
    'Temps plein',
    'Temps partiel',
    'Stage',
    'Contrat / freelance',
    'Sur place',
    'Hybride',
    'Télétravail',
    'non précisé',
    'page non lue',
    'oui',
    'expirée',
    'Entreprises suivies',
    'Offres',
    'Résumé',
]


def set_language(code: str) -> None:
    global _language
    _language = code if code in LANGUAGES else "fr"


def language() -> str:
    return _language


# In every language of the app, a space comes before ? ! : ; (and inside « »): made unbreakable, so the mark
# never starts a line alone. The tests check that no text forgets it.
_SPACES = re.compile(r" (?=[?!:;»])|(?<=«) ")
NO_BREAK_SPACE = chr(0xA0)


def _(text: str) -> str:
    """The text in the chosen language."""
    return _SPACES.sub(NO_BREAK_SPACE, TRANSLATIONS.get(_language, {}).get(text, text))


def value(text: str) -> str:
    """A value the app stores in French ("3+ ans", "Temps plein"...), in the chosen language."""
    if _language == "fr" or not text:
        return text
    match = re.fullmatch(r"(\d+)\+ ans", text)
    if match:
        return f"{match.group(1)}+ {_YEARS[_language]}"
    return _(text).replace("/mois", _MONTH[_language])


def to_french(text: str) -> str:
    """A value read back from jobs.xlsx, whatever language it was written in, as the app knows it."""
    for table in _FROM.values():
        if text in table:
            return table[text]
    match = re.fullmatch(r"(\d+)\+ (\S+)", text)  # experience
    if match and match.group(2) in _YEARS.values():
        return f"{match.group(1)}+ ans"
    for month in _MONTH.values():  # salary
        text = text.replace(month, "/mois")
    return text


_FROM = {code: {table[text]: text for text in _VALUES if table.get(text, text) != text}
         for code, table in TRANSLATIONS.items()}
