"""EURES, the European Union's job portal: offers in Cyprus, through the API its search page uses."""
import html
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from .common import Job, Settings, clean, fetch

_API = "https://europa.eu/eures/api/jv-searchengine/public/jv-search/search"
_PER_PAGE = 50
# EURES codes -> settings.CONTRACTS
_SCHEDULES = {"fulltime": "Temps plein", "parttime": "Temps partiel"}
_OFFERINGS = {"internship": "Stage", "apprenticeship": "Stage", "traineeship": "Stage",
              "temporary": "Contrat / freelance", "contract": "Contrat / freelance", "seasonal": "Contrat / freelance"}


def eures(session, keyword: str, settings: Settings) -> list[Job]:
    jobs: list[Job] = []
    for page in range(1, settings.max_pages + 1):
        data = fetch(session, _API, as_json=True, post=_query(keyword, page, settings.max_age_days))
        for item in data.get("jvs", []):
            title = clean(html.unescape(item.get("title") or ""))
            created = item.get("creationDate")
            offering = _OFFERINGS.get(item.get("positionOfferingCode") or "")
            schedule = next((_SCHEDULES[c] for c in item.get("positionScheduleCodes") or [] if c in _SCHEDULES), "")
            jobs.append(Job(
                source="EURES",
                title=title.title() if title.isupper() else title,  # many Cypriot offers are in capitals
                company=clean((item.get("employer") or {}).get("name")),
                location="Cyprus",  # EURES only gives the region code, CY000 = all of Cyprus
                url=f"https://europa.eu/eures/portal/jv-se/jv-details/{item['id']}?lang=en",
                posted=(datetime.fromtimestamp(created / 1000, timezone.utc).date().isoformat() if created else ""),
                description=clean(BeautifulSoup(html.unescape(item.get("description") or ""),
                                                "html.parser").get_text(" ")),
                contract=offering or schedule,
            ))
        if len(data.get("jvs", [])) < _PER_PAGE:
            break
    return jobs


def _query(keyword: str, page: int, max_age_days: int) -> dict:
    period = "LAST_WEEK" if 0 < max_age_days <= 7 else "LAST_MONTH" if 0 < max_age_days <= 31 else None
    return {
        "resultsPerPage": _PER_PAGE, "page": page, "sortSearch": "MOST_RECENT",
        "keywords": [{"keyword": keyword, "specificSearchCode": "EVERYWHERE"}],
        "publicationPeriod": period, "locationCodes": ["cy"], "occupationUris": [], "skillUris": [],
        "requiredExperienceCodes": [], "positionScheduleCodes": [], "sectorCodes": [],
        "educationAndQualificationLevelCodes": [], "positionOfferingCodes": [], "euresFlagCodes": [],
        "otherBenefitsCodes": [], "requiredLanguages": [], "minNumberPost": None, "sessionId": "retrieve-job",
    }
