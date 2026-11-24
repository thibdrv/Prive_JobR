"""Each job site still answers and its offers are still read correctly (needs internet, a few minutes).

A site that changes its layout makes its reader return nothing, or offers without a title or link:
these tests show which one, so its code in sources/ can be adapted. They are skipped by default;
to run them (Windows):
    set RETRIEVE_JOB_ONLINE=1
    .venv\\Scripts\\python.exe -m unittest tests.test_sites_online -v
"""
import os
import unittest

import settings as app_settings
from sources import BROWSE_SOURCES, SOURCES, company_jobs, remote_boards
from sources.common import Settings, fetch, new_session

ONLINE = os.environ.get("RETRIEVE_JOB_ONLINE") == "1"
SETTINGS = Settings(max_pages=1, max_age_days=31, remote_locations=app_settings.DEFAULTS["remote_locations"],
                    careerfinders_categories=[("Customer Services", "CUSTOM")],
                    cities=app_settings.DEFAULTS["cities"])
# A search that always has offers on each site
SEARCHES = {"ergodotisi": "sales", "cyprusjobs": "sales", "cypruswork": "sales", "fxcareer": "sales",
            "kariera": "sales", "eures": "sales", "workable": "sales", "djinni": "sales", "himalayas": "sales"}
# Boards that give their whole list at once: the list must not be empty (a search in it may well be)
FEEDS = {"remoteok": remote_boards._load_remoteok, "jobicy": remote_boards._load_jobicy,
         "remotive": remote_boards._load_remotive, "weworkremotely": remote_boards._load_weworkremotely}
# One followed company per hiring platform
COMPANIES = [{"name": "FxPro", "platform": "greenhouse", "id": "fxpro"},
             {"name": "Capital.com", "platform": "lever", "id": "capital"},
             {"name": "Admirals", "platform": "workable", "id": "admirals"},
             {"name": "Playtech", "platform": "smartrecruiters", "id": "Playtech"}]


@unittest.skipUnless(ONLINE, "set RETRIEVE_JOB_ONLINE=1 to check the live job sites")
class Sites(unittest.TestCase):
    def assert_offers(self, jobs, site):
        self.assertTrue(jobs, f"{site}: no offer at all, the site may have changed its layout")
        broken = [job for job in jobs if not job.title or not job.url.startswith("http")]
        self.assertFalse(broken, f"{site}: offers without a title or a link, e.g. {broken[:1]}")

    def test_sites_with_a_search(self):
        self.assertEqual(set(SEARCHES) | set(FEEDS), set(SOURCES), "a site in sources/ has no test here")
        for site, search in SEARCHES.items():
            with self.subTest(site=site):
                self.assert_offers(SOURCES[site](new_session(), search, SETTINGS), site)

    def test_remote_boards(self):
        for site, load in FEEDS.items():
            with self.subTest(site=site):
                self.assert_offers(load(new_session()), site)

    def test_sites_read_in_full(self):
        for site in ("careerfinders", "emeraldzebra"):
            with self.subTest(site=site):
                self.assert_offers(BROWSE_SOURCES[site](new_session(), SETTINGS), site)
        # Relocate.me rarely has an offer in Cyprus: check that its list of offers is still readable
        html = fetch(new_session(), "https://relocate.me/search", {"page": 1})
        self.assertIn("job__title", html, "relocate: the list of offers changed its layout")

    def test_followed_companies(self):
        for company in COMPANIES:
            with self.subTest(company=company["name"]):
                jobs = company_jobs(new_session(), company, SETTINGS)  # it fails if the platform changed
                if jobs:  # a company may have no offer in Cyprus today
                    self.assert_offers(jobs, company["name"])


if __name__ == "__main__":
    unittest.main()
