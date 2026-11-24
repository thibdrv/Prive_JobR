"""The rules the search applies to each offer, and the small readers around it (no internet needed)."""
import unittest
from datetime import date, timedelta

import desktop
import retrieve_jobs
from sources.common import canonical_url, has_word, title_matches
from sources.international import _djinni_age
from window.common import company_from_link

CITIES = ["nicosia", "limassol", "ypsonas", "larnaca"]


class Area(unittest.TestCase):
    def test_kept(self):
        for location in ("Limassol, Cyprus", "Cyprus, Ypsonas", "Cyprus", "Republic of Cyprus", "Remote", "",
                         "Hybrid - Cyprus"):
            with self.subTest(location=location):
                self.assertTrue(retrieve_jobs._in_area(location, CITIES))

    def test_dropped(self):
        for location in ("Paphos, Cyprus", "Athens, Greece", "Dubai"):
            with self.subTest(location=location):
                self.assertFalse(retrieve_jobs._in_area(location, CITIES))


class Duplicates(unittest.TestCase):
    def test_same_offer_on_two_sites(self):
        self.assertEqual(retrieve_jobs._offer_key("Data Analyst (m/f)", "Tickmill Europe Ltd"),
                         retrieve_jobs._offer_key("Data Analyst m/f", "TICKMILL EUROPE LIMITED"))

    def test_recruiters_hide_the_employer(self):
        self.assertEqual(retrieve_jobs._offer_key("Sales Agent", "CareerFinders (pour un client)"), "")
        self.assertEqual(retrieve_jobs._offer_key("Sales Agent", ""), "")


class Age(unittest.TestCase):
    def test_wordings(self):
        ten_days_ago = (date.today() - timedelta(days=10)).isoformat()
        cases = {ten_days_ago: 10, "today": 0, "3 hours ago": 0, "yesterday": 1, "2 weeks ago": 14,
                 "a month ago": 30, "Posted recently": None, "": None}
        for posted, days in cases.items():
            with self.subTest(posted=posted):
                self.assertEqual(retrieve_jobs._age_in_days(posted), days)

    def test_too_old(self):
        self.assertTrue(retrieve_jobs._too_old("2 months ago", 31))
        self.assertFalse(retrieve_jobs._too_old("2 weeks ago", 31))
        self.assertFalse(retrieve_jobs._too_old("no date", 31))  # unknown dates are kept

    def test_djinni_wording(self):
        self.assertEqual([_djinni_age(t) for t in ("updated 3h ago", "updated 2d ago", "updated 1w ago")],
                         ["today", "2 days ago", "1 weeks ago"])


class ExpiredFromFile(unittest.TestCase):
    def test_old_offers_leave_unless_they_have_a_status(self):
        old = (date.today() - timedelta(days=40)).isoformat()
        rows = [{"Trouvée le": old, "Statut": ""}, {"Trouvée le": old, "Statut": "Postulé"},
                {"Trouvée le": date.today().isoformat(), "Statut": ""}, {"Trouvée le": "?", "Statut": ""}]
        kept, removed = retrieve_jobs._drop_expired(rows, 31)
        self.assertEqual((len(kept), removed), (3, 1))
        self.assertEqual(retrieve_jobs._drop_expired(rows, 0), (rows, 0))  # 0 = never remove


class Category(unittest.TestCase):
    CATEGORIES = {"data": ["data", "business analyst"], "dev": ["developer", "react"],
                  "sales": ["sales", "support"]}

    def test_first_fitting_type_wins(self):
        self.assertEqual(retrieve_jobs._category("Data Analyst", self.CATEGORIES), "data")
        self.assertEqual(retrieve_jobs._category("React Developer", self.CATEGORIES), "dev")
        self.assertEqual(retrieve_jobs._category("Sales Data Specialist", self.CATEGORIES), "data")
        self.assertEqual(retrieve_jobs._category("Accountant", self.CATEGORIES), "")

    def test_words_start_where_a_word_starts(self):
        self.assertTrue(has_word("Senior Analysts", "analyst"))
        self.assertFalse(has_word("Workshop Manager", "shop"))
        self.assertTrue(title_matches("Junior Data Analyst", "data analyst"))
        self.assertFalse(title_matches("Data Engineer", "data analyst"))

    def test_whole_words_for_exclusions(self):
        self.assertTrue(retrieve_jobs._has_whole_word("Senior Developer", "senior"))
        self.assertFalse(retrieve_jobs._has_whole_word("Seniority bonus", "senior"))
        self.assertFalse(retrieve_jobs._has_whole_word("Anything", " "))


class Links(unittest.TestCase):
    def test_one_spelling_per_offer(self):
        self.assertEqual(canonical_url("https://Ergodotisi.com/en-CY/jobs/data-1?utm_source=x#top"),
                         "https://ergodotisi.com/en-CY/jobs/data-1")
        self.assertEqual(canonical_url("https://www.linkedin.com/jobs/view/data-analyst-at-x-4012345678?trk=1"),
                         "https://www.linkedin.com/jobs/view/4012345678/")

    def test_company_careers_pages(self):
        self.assertEqual(company_from_link("https://jobs.lever.co/capital/7c3b-22e2"),
                         {"platform": "lever", "id": "capital"})
        self.assertEqual(company_from_link("https://job-boards.eu.greenhouse.io/fxpro/jobs/5024766101"),
                         {"platform": "greenhouse", "id": "fxpro"})
        self.assertEqual(company_from_link("https://apply.workable.com/admirals/j/ABC123/"),
                         {"platform": "workable", "id": "admirals"})
        self.assertEqual(company_from_link("https://jobs.smartrecruiters.com/Playtech/744000160885649"),
                         {"platform": "smartrecruiters", "id": "Playtech"})
        self.assertIsNone(company_from_link("https://www.example.com/careers"))


class Schedule(unittest.TestCase):
    def test_windows_task(self):
        daily = ("<CalendarTrigger><StartBoundary>2026-11-23T09:30:00</StartBoundary><ScheduleByDay>"
                 "<DaysInterval>3</DaysInterval></ScheduleByDay></CalendarTrigger>")
        weekly = ("<CalendarTrigger><StartBoundary>2026-11-23T18:05:00</StartBoundary><ScheduleByWeek><DaysOfWeek>"
                  "<Monday /><Thursday /></DaysOfWeek></ScheduleByWeek></CalendarTrigger>")
        self.assertEqual(desktop._from_task_xml(daily), {"hour": 9, "minute": 30, "every_days": 3, "weekdays": []})
        self.assertEqual(desktop._from_task_xml(weekly), {"hour": 18, "minute": 5, "every_days": 0, "weekdays": [0, 3]})
        self.assertIsNone(desktop._from_task_xml(""))

    def test_cron_line(self):
        mark = desktop._CRON_MARK
        self.assertEqual(desktop._from_cron(f"30 9 */2 * * 'python' 'run.py' >/dev/null 2>&1 {mark}"),
                         {"hour": 9, "minute": 30, "every_days": 2, "weekdays": []})
        self.assertEqual(desktop._from_cron(f"5 18 * * 1,4 'python' 'run.py' >/dev/null 2>&1 {mark}"),
                         {"hour": 18, "minute": 5, "every_days": 0, "weekdays": [0, 3]})
        self.assertIsNone(desktop._from_cron("0 8 * * * some other job"))


if __name__ == "__main__":
    unittest.main()
