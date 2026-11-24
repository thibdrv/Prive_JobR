"""Every French text of the app has its English version (i18n.py).

The French sentences are the keys of the translation: a sentence changed in the code but not in i18n.TRANSLATIONS["en"]
would silently stay in French in English mode. These tests find every text the code passes to _() or value()
and every list of values shown translated, and check them against i18n.TRANSLATIONS["en"].
"""
import ast
import re
import unittest
from pathlib import Path

import i18n
import results_file
import retrieve_jobs
import settings
from window import common, stats_view

PROJECT = Path(__file__).resolve().parent.parent
CODE = [*PROJECT.glob("*.py"), *(PROJECT / "window").glob("*.py"), *(PROJECT / "sources").glob("*.py")]


def texts_in_code() -> dict[str, str]:
    """Text -> file, for every literal passed to _(), value() or the summary's section()."""
    found = {}
    for path in CODE:
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (isinstance(node, ast.Call) and getattr(node.func, "id", None) in ("_", "value", "section")
                    and node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str)):
                found.setdefault(node.args[0].value, path.name)
    return found


def _constants(node) -> set[str]:
    """The texts an expression can give: "a", or "a" if ... else "b"."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return {node.value} - {""}
    if isinstance(node, ast.IfExp):
        return _constants(node.body) | _constants(node.orelse)
    return set()


def rejection_reasons_and_experience() -> set[str]:
    """What _rejection() returns ("langue", "salaire"...) or writes in Expérience ("junior", "page non lue"...)."""
    tree = ast.parse((PROJECT / "retrieve_jobs.py").read_text(encoding="utf-8"))
    function = next(n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "_rejection")
    found = set()
    for node in ast.walk(function):
        if isinstance(node, ast.Return):
            found |= _constants(node.value)
        elif isinstance(node, ast.Assign) and any(getattr(t, "attr", "") == "experience" for t in node.targets):
            found |= _constants(node.value)
    return found


def values_shown_translated() -> set[str]:
    """Values that reach _() or value() through a variable: site names, statuses, columns..."""
    return {*settings.SITE_NAMES.values(), *settings.CONTRACTS, *settings.WORK_MODES, *common.STATUSES,
            *common.WEEKDAYS, common.ALL, common.NO_STATUS, common.NOT_STATED, *results_file.HEADERS,
            *(name for name, _factor in [*common.TEXT_SIZES.values(), *common.DENSITIES.values()]),
            *(name for name, _tiles, _charts in stats_view.PAGES),
            *(text for text, _color, _hover in common.SEARCH_BUTTON.values()),
            *results_file.SHEETS, *(heading for heading, _width in common.TABLE_COLUMNS.values()),
            retrieve_jobs.FOLLOWED, results_file.ONLINE, results_file.EXPIRED, "non",
            *rejection_reasons_and_experience()}


def is_a_name(text: str) -> bool:
    """Site names like "CyprusJobs.com" are the same in both languages."""
    return re.fullmatch(r"[\w.]+\.(com|eu|cy)", text) is not None


class Translations(unittest.TestCase):
    """Run for each language of i18n.TRANSLATIONS (English, Greek...)."""

    def test_every_text_in_the_code_is_translated(self):
        for code, table in i18n.TRANSLATIONS.items():
            with self.subTest(language=code):
                missing = {text: where for text, where in texts_in_code().items()
                           if text not in table and not is_a_name(text)}
                self.assertEqual(missing, {}, f"texts with no {code} version (file where they are used)")

    def test_every_value_shown_translated_is_translated(self):
        for code, table in i18n.TRANSLATIONS.items():
            with self.subTest(language=code):
                missing = sorted(text for text in values_shown_translated()
                                 if text not in table and not is_a_name(text))
                self.assertEqual(missing, [])

    def test_no_forgotten_translation(self):
        used = set(texts_in_code()) | values_shown_translated()
        for code, table in i18n.TRANSLATIONS.items():
            with self.subTest(language=code):
                self.assertEqual(sorted(set(table) - used), [], f"{code} texts no longer used by the code")

    def test_every_text_has_a_space_before_double_punctuation(self):
        """In every language: "Prêt : …", "Ready : …", "Score ?", "Βαθμολογία ;": the space before ? ! : ;
        is never forgotten (in Greek, ";" is the question mark)."""
        texts = {"fr": set(texts_in_code()) | values_shown_translated()}
        texts.update({code: set(table.values()) for code, table in i18n.TRANSLATIONS.items()})
        for code, found in texts.items():
            with self.subTest(language=code):
                missing = []
                for text in found:
                    plain = re.sub(r"\{[^}]*\}|https?://\S+|\d:\d", "", text)  # placeholders, links, times aside
                    if re.search(rf"[^\s{i18n.NO_BREAK_SPACE}][?!:;]", plain):
                        missing.append(text)
                self.assertEqual(sorted(missing), [], "add a space before ? ! : ; in these texts")

    def test_punctuation_never_starts_a_line(self):
        self.addCleanup(i18n.set_language, "fr")
        space = i18n.NO_BREAK_SPACE
        i18n.set_language("fr")
        self.assertEqual(i18n._("Le Score, c'est quoi ?"), f"Le Score, c'est quoi{space}?")
        self.assertEqual(i18n._("Exemple : « python »"), f"Exemple{space}: «{space}python{space}»")
        i18n.set_language("en")
        self.assertEqual(i18n._("Le Score, c'est quoi ?"), f"What is the Score{space}?")
        i18n.set_language("el")
        self.assertEqual(i18n._("Le Score, c'est quoi ?"), f"Τι είναι η Βαθμολογία{space};")

    def test_same_placeholders(self):
        for code, table in i18n.TRANSLATIONS.items():
            for french, translated in table.items():
                with self.subTest(language=code, text=french):
                    self.assertEqual(sorted(re.findall(r"\{(\w+)", french)),
                                     sorted(re.findall(r"\{(\w+)", translated)))

    def test_file_values_read_back_in_every_language(self):
        self.addCleanup(i18n.set_language, "fr")
        for code in i18n.LANGUAGES:
            i18n.set_language(code)
            for text in [*i18n._VALUES, "3+ ans", "1 500–2 000 €/mois"]:
                with self.subTest(language=code, text=text):
                    self.assertEqual(i18n.to_french(i18n.value(text)), text)

    def test_file_values_have_distinct_names(self):
        for code, table in i18n.TRANSLATIONS.items():
            with self.subTest(language=code):
                names = [table[text] for text in i18n._VALUES]
                self.assertEqual(sorted({name for name in names if names.count(name) > 1}), [])


if __name__ == "__main__":
    unittest.main()
