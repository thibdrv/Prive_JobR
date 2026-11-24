"""jobs.xlsx: writing, reading back in both languages, changing offers, backups (results_file.py).

Everything happens in a temporary folder: the real results are never touched.
"""
import tempfile
import time
import unittest
from datetime import date
from pathlib import Path
from unittest import mock

from openpyxl import load_workbook

import i18n
import results_file


def offer(number: int, **fields) -> dict:
    row = {"Trouvée le": date.today().isoformat(), "Catégorie": "data", "Score": 2, "Titre": f"Data Analyst {number}",
           "Entreprise": "Acme", "Ville": "Limassol", "Expérience": "3+ ans", "Contrat": "Temps plein",
           "Mode de travail": "Hybride", "Salaire": "1 500–2 000 €/mois", "Site": "Ergodotisi",
           "Lien": f"https://example.com/jobs/{number}", "Statut": "", "Notes": "", "En ligne": "oui",
           "Description": f"Offer {number}"}
    row.update(fields)
    return row


class ResultsFile(unittest.TestCase):
    def setUp(self):
        folder = Path(tempfile.mkdtemp())
        results = folder / "results"
        cache = folder / ".cache"
        self.patch = mock.patch.multiple(
            results_file, RESULTS=results, EXCEL_FILE=results / "jobs.xlsx", BACKUPS=results / "backups",
            CACHE=cache, DESCRIPTIONS_FILE=cache / "descriptions.json", ONLINE_FILE=cache / "online_checks.json")
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.addCleanup(i18n.set_language, "fr")

    def write(self):
        results_file.write([offer(1), offer(2)], [offer(3, Statut="Postulé", Notes="relancer")], ["data"])

    def test_written_and_read_back(self):
        self.write()
        rows = results_file.read_rows(with_new=True)
        self.assertEqual([r["Titre"] for r in rows], ["Data Analyst 1", "Data Analyst 2", "Data Analyst 3"])
        self.assertEqual([r["_new"] for r in rows], [True, True, False])  # this search's offers in yellow
        self.assertEqual([r["Nouvelle"] for r in rows], ["oui", "oui", "non"])
        self.assertEqual((rows[2]["Statut"], rows[2]["Notes"]), ("Postulé", "relancer"))
        sheet = load_workbook(results_file.EXCEL_FILE).worksheets[0]
        self.assertEqual(sheet["D2"].value, 2)  # Score is a number, so Excel sorts it as one
        self.assertEqual([cell.value for cell in sheet[1]], results_file.HEADERS)

    def test_english_file_reads_back_the_same(self):
        i18n.set_language("en")
        self.write()
        sheet = load_workbook(results_file.EXCEL_FILE).worksheets[0]
        self.assertEqual(sheet.title, "Offers")
        headers = [cell.value for cell in sheet[1]]
        self.assertIn("Salary", headers)
        row = dict(zip(headers, [cell.value for cell in sheet[4]]))
        self.assertEqual((row["Status"], row["Experience"], row["Salary"]), ("Applied", "3+ yrs", "1 500–2 000 €/month"))
        i18n.set_language("fr")  # read by the app in the other language: same values inside
        rows = results_file.read_rows()
        self.assertEqual((rows[2]["Statut"], rows[2]["Expérience"], rows[2]["Salaire"]),
                         ("Postulé", "3+ ans", "1 500–2 000 €/mois"))

    def test_greek_file_reads_back_the_same(self):
        i18n.set_language("el")
        self.write()
        sheet = load_workbook(results_file.EXCEL_FILE).worksheets[0]
        self.assertEqual(sheet.title, "Αγγελίες")
        headers = [cell.value for cell in sheet[1]]
        row = dict(zip(headers, [cell.value for cell in sheet[4]]))
        self.assertEqual((row["Κατάσταση"], row["Εμπειρία"], row["Μισθός"]),
                         ("Έκανα αίτηση", "3+ έτη", "1 500–2 000 €/μήνα"))
        i18n.set_language("en")  # read by the app in another language: same values inside
        rows = results_file.read_rows()
        self.assertEqual((rows[2]["Statut"], rows[2]["Expérience"], rows[2]["Salaire"]),
                         ("Postulé", "3+ ans", "1 500–2 000 €/mois"))

    def test_status_and_its_date(self):
        self.write()
        link = offer(1)["Lien"]
        self.assertEqual(results_file.set_status([link], "Entretien"), 1)
        row = results_file.read_rows()[0]
        self.assertEqual((row["Statut"], row["Statut modifié le"]), ("Entretien", date.today().isoformat()))
        results_file.set_field([link], "Notes", "Maria, RH")
        self.assertEqual(results_file.read_rows()[0]["Notes"], "Maria, RH")
        self.assertEqual(results_file.read_rows(with_new=True)[0]["_new"], True)  # the yellow is kept

    def test_quick_copy_is_used_and_follows_the_changes(self):
        """The app reads the quick copy (.cache/offers.json) while jobs.xlsx has not changed, and a status saved
        by the app is in it at once."""
        self.write()
        first = results_file.read_rows(with_new=True)  # from jobs.xlsx, and the copy is made
        self.assertTrue((results_file.CACHE / "offers.json").exists())
        results_file.set_status([offer(3)["Lien"]], "Entretien")
        with mock.patch.object(results_file, "load_workbook", side_effect=AssertionError("Excel was read")):
            rows = results_file.read_rows(with_new=True)
        self.assertEqual([row["Titre"] for row in rows], [row["Titre"] for row in first])
        self.assertEqual((rows[2]["Statut"], rows[2]["Statut modifié le"]), ("Entretien", date.today().isoformat()))
        self.assertEqual(rows, results_file._read_excel(with_new=True))  # the same as reading jobs.xlsx

    def test_quick_copy_is_not_used_once_the_file_changed(self):
        self.write()
        results_file.read_rows(with_new=True)
        results_file.write([offer(7)], [], ["data"])  # a search, Excel or a restored copy changed the file
        self.assertEqual([row["Titre"] for row in results_file.read_rows(with_new=True)], ["Data Analyst 7"])

    def test_backups_keep_the_newest(self):
        self.write()
        for _copy in range(3):
            results_file.backup(2)
            time.sleep(1.1)  # one copy per second: the name holds the time
        self.assertEqual(len(results_file.backups()), 2)
        self.assertIsNone(results_file.backup(0))  # 0 = no copies

    def test_restore_can_be_undone(self):
        self.write()
        copy = results_file.backup(5)
        results_file.set_status([offer(1)["Lien"]], "Refusé")
        time.sleep(1.1)
        results_file.restore(copy, 5)
        self.assertEqual(results_file.read_rows()[0]["Statut"], "")  # back as it was
        self.assertEqual(len(results_file.backups()), 2)  # the file before the restore was kept

    def test_descriptions_are_kept_next_to_the_file(self):
        results_file.save_descriptions({"a": "text a", "b": "text b", "c": ""})
        self.assertEqual(results_file.descriptions(), {"a": "text a", "b": "text b"})
        results_file.save_descriptions({}, keep={"b"})
        self.assertEqual(results_file.descriptions(), {"b": "text b"})


if __name__ == "__main__":
    unittest.main()
