"""Reading a posting: experience, languages, contract, work mode, salary and skills (experience.py)."""
import unittest

from experience import (contract_type, requires_language, salary_range, salary_text, skills_found, work_mode,
                        years_required)


class YearsRequired(unittest.TestCase):
    def test_reads_the_years_asked_for(self):
        self.assertEqual(years_required("At least 3 years of experience in sales"), 3)
        self.assertEqual(years_required("2-4 years experience with SQL"), 2)
        self.assertEqual(years_required("Minimum two years of relevant experience"), 2)
        self.assertEqual(years_required("5+ yrs experience. Also 1 year experience with Python"), 5)
        self.assertEqual(years_required("τουλάχιστον 4 χρόνια εμπειρία"), 4)

    def test_ignores_what_is_not_about_you(self):
        self.assertIsNone(years_required("We have 20 years of experience in fintech"))
        self.assertIsNone(years_required("A 3 years contract, no experience needed"))
        self.assertIsNone(years_required("Founded 25 years ago"))
        self.assertIsNone(years_required("No experience required"))


class RequiresLanguage(unittest.TestCase):
    def test_required(self):
        self.assertTrue(requires_language("Sales Agent", "Fluent in Greek and English.", "greek"))
        self.assertTrue(requires_language("Greek Speaking Agent", "", "greek"))
        self.assertTrue(requires_language("Λογιστής", "", "greek"))
        self.assertTrue(requires_language("Agent", "Excellent command of the Greek language is required.", "greek"))

    def test_not_required(self):
        self.assertFalse(requires_language("Agent", "Knowledge of Greek is an advantage.", "greek"))
        self.assertFalse(requires_language("Agent", "You will serve the Greek market.", "greek"))
        self.assertFalse(requires_language("Agent", "We offer free Greek language classes.", "greek"))
        self.assertFalse(requires_language("Agent", "Fluent English. Experience with Greek-speaking customers.", "greek"))


class ContractAndWorkMode(unittest.TestCase):
    def test_contract(self):
        self.assertEqual(contract_type("Junior Data Analyst Internship", "full-time"), "Stage")
        self.assertEqual(contract_type("Sales Agent", "This is a part-time role"), "Temps partiel")
        self.assertEqual(contract_type("Developer", "Permanent full time position"), "Temps plein")
        self.assertEqual(contract_type("Developer", "Freelance, 6 months contract"), "Contrat / freelance")
        self.assertEqual(contract_type("Developer", ""), "")

    def test_work_mode(self):
        self.assertEqual(work_mode("Limassol", "We work in a hybrid model"), "Hybride")
        self.assertEqual(work_mode("Remote", ""), "Télétravail")
        self.assertEqual(work_mode("Nicosia", "Office-based role"), "Sur place")
        self.assertEqual(work_mode("Nicosia", "remote access tools"), "")


class Salary(unittest.TestCase):
    CASES = {
        "Salary: €1,500 - €2,000 gross per month": "1 500–2 000 €/mois",
        "Remuneration package EUR 25k-30k per annum": "2 083–2 500 €/mois",
        "Attractive salary 1.800€ net": "1 800 €/mois",
        "€30,000 annual salary": "2 500 €/mois",
        "Salary range: $60,000 to $80,000 per year": "5 000–6 667 $/mois",
        "€ 1500 - 1800 monthly": "1 500–1 800 €/mois",
        "salary from 2,500 EUR": "2 500 €/mois",
        "Gross salary 25-30k EUR": "2 083–2 500 €/mois",
        "Salary and compensation $10,000 — $50,000/year": "833–4 167 $/mois",
        # "per month" written after the amount wins over a yearly bonus mentioned next to it
        "Salary: EUR 6,000 to 8,000 gross per month Annual performance bonus": "6 000–8 000 €/mois",
        "Sales Assistant €600–700 Monthly salary": "600–700 €/mois",
        "The company raised €5,000,000 in funding. Salary: €2,000 gross per month": "2 000 €/mois",
    }
    NOT_SALARIES = [
        "We offer a €500 bonus for referrals",
        "Pay: €12.50 per hour",
        "Competitive salary and 13th salary",
        "With $200+ million in annual revenue, competitive salary",
    ]

    def test_salaries(self):
        for text, expected in self.CASES.items():
            with self.subTest(text=text):
                self.assertEqual(salary_text(salary_range(text)), expected)

    def test_amounts_that_are_not_a_salary(self):
        for text in self.NOT_SALARIES:
            with self.subTest(text=text):
                self.assertIsNone(salary_range(text))


class Skills(unittest.TestCase):
    def test_whole_words_only(self):
        text = "Strong SQL and Power BI; knowledge of React.js, Node and C++. French speaker. Javascript"
        self.assertEqual(skills_found(text, ["sql", "power bi", "react", "node", "c++", "french", "java", "git"]),
                         ["sql", "power bi", "react", "node", "c++", "french"])


if __name__ == "__main__":
    unittest.main()
