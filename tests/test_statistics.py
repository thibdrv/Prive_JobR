"""The numbers behind the salary charts of the Statistics tab (window/stats_view.py)."""
import unittest

from window.stats_view import city, salary


class Salary(unittest.TestCase):
    def test_middle_of_the_range_in_euros(self):
        self.assertEqual(salary({"Salaire": "1 500–2 000 €/mois"}), 1750)
        self.assertEqual(salary({"Salaire": "1 200 €/mois"}), 1200)

    def test_other_currencies_and_no_salary_are_left_out(self):
        self.assertIsNone(salary({"Salaire": "833–4 167 $/mois"}))
        self.assertIsNone(salary({"Salaire": ""}))
        self.assertIsNone(salary({}))


class City(unittest.TestCase):
    def test_city_from_its_names_and_districts(self):
        self.assertEqual(city({"Ville": "Limassol, Cyprus"}), "Limassol")
        self.assertEqual(city({"Ville": "Cyprus, Ypsonas"}), "Limassol")
        self.assertEqual(city({"Ville": "Strovolos, Lefkosia"}), "Nicosia")
        self.assertEqual(city({"Ville": "Larnaka"}), "Larnaca")

    def test_first_city_named_wins(self):
        self.assertEqual(city({"Ville": "Nicosia, Larnaca"}), "Nicosia")
        self.assertEqual(city({"Ville": "Larnaca, Nicosia"}), "Larnaca")

    def test_offers_without_a_city(self):
        self.assertEqual(city({"Ville": "Worldwide", "Mode de travail": "Télétravail"}), "Télétravail")
        self.assertEqual(city({"Ville": "Cyprus"}), "Chypre, ville non précisée")
        self.assertEqual(city({"Ville": "Athens, Greece"}), "Autres")


if __name__ == "__main__":
    unittest.main()
