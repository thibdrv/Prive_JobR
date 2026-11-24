"""Companies' own careers pages, read through the public job lists of their hiring platform.

Greenhouse, Lever, Workable and SmartRecruiters each give a company's whole list in a few requests.
Only the offers in Cyprus (or in one of the cities) are kept.
"""
import html
import re
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from experience import contract_type
from .common import Job, Settings, clean, fetch


def company_jobs(session, company: dict, settings: Settings) -> list[Job]:
    read = {"greenhouse": _greenhouse, "lever": _lever, "workable": _workable,
            "smartrecruiters": _smartrecruiters}[company["platform"]]
    places = ["cyprus", *settings.cities]
    return [job for job in read(session, company["id"].strip(), company["name"])
            if any(re.search(rf"\b{re.escape(place)}", job.location, re.IGNORECASE) for place in places)]


def _greenhouse(session, board: str, name: str) -> list[Job]:
    data = fetch(session, f"https://boards-api.greenhouse.io/v1/boards/{board}/jobs", {"content": "true"},
                 as_json=True)
    return [Job(
        source=name,
        title=clean(item.get("title")),
        company=name,
        location=clean((item.get("location") or {}).get("name")),
        url=item["absolute_url"],
        posted=(item.get("first_published") or item.get("updated_at") or "")[:10],
        description=_text(html.unescape(item.get("content") or "")),
    ) for item in data.get("jobs", []) if item.get("absolute_url")]


def _lever(session, account: str, name: str) -> list[Job]:
    try:
        data = fetch(session, f"https://api.lever.co/v0/postings/{account}", {"mode": "json"}, as_json=True)
    except RuntimeError:  # accounts hosted in Europe have their own address
        data = fetch(session, f"https://api.eu.lever.co/v0/postings/{account}", {"mode": "json"}, as_json=True)
    jobs = []
    for item in data:
        categories = item.get("categories") or {}
        places = categories.get("allLocations") or [categories.get("location") or ""]
        lists = " ".join(f"{block.get('text', '')} {_text(block.get('content', ''))}" for block in item.get("lists", []))
        salary = item.get("salaryRange") or {}
        jobs.append(Job(
            source=name,
            title=clean(item.get("text")),
            company=name,
            location=clean(", ".join(places)),
            url=item.get("hostedUrl", ""),
            posted=_date_from_ms(item.get("createdAt")),
            description=clean(f"{item.get('descriptionPlain', '')} {lists} {item.get('additionalPlain', '')}"),
            contract=contract_type(categories.get("commitment") or "", ""),
            work_mode={"onsite": "Sur place", "hybrid": "Hybride", "remote": "Télétravail"}.get(
                item.get("workplaceType") or "", ""),
            salary=_salary(salary.get("min"), salary.get("max"), salary.get("currency"), salary.get("interval")),
        ))
    return [job for job in jobs if job.url]


def _workable(session, account: str, name: str) -> list[Job]:
    data = fetch(session, f"https://apply.workable.com/api/v1/widget/accounts/{account}", as_json=True)
    jobs = []
    for item in data.get("jobs", []):
        places = [", ".join(part for part in (place.get("city"), place.get("country")) if part)
                  for place in item.get("locations") or []] or [f"{item.get('city', '')}, {item.get('country', '')}"]
        job = Job(
            source=name,
            title=clean(item.get("title")),
            company=name,
            location=clean("; ".join(places)),
            url=item.get("url") or item.get("shortlink") or "",
            posted=(item.get("published_on") or item.get("created_at") or "")[:10],
            contract=contract_type(item.get("employment_type") or "", ""),
            work_mode="Télétravail" if item.get("telecommuting") else "",
        )
        if not job.url:
            continue
        jobs.append(job)
        shortcode = item.get("shortcode")  # the list has no description: ask for it per offer in Cyprus
        if shortcode and re.search(r"cyprus|limassol|nicosia|larnaca", job.location, re.IGNORECASE):
            try:
                details = fetch(session, f"https://apply.workable.com/api/v2/accounts/{account}/jobs/{shortcode}",
                                as_json=True)
                job.description = _text(" ".join(str(details.get(key) or "")
                                                  for key in ("description", "requirements", "benefits")))
            except RuntimeError:
                pass  # read from the offer's page later
    return jobs


def _smartrecruiters(session, company: str, name: str) -> list[Job]:
    api = f"https://api.smartrecruiters.com/v1/companies/{company}/postings"
    jobs = []
    for offset in range(0, 1000, 100):
        data = fetch(session, api, {"limit": 100, "offset": offset}, as_json=True)
        for item in data.get("content", []):
            place = item.get("location") or {}
            job = Job(
                source=name,
                title=clean(item.get("name")),
                company=name,
                location=clean(place.get("fullLocation") or f"{place.get('city', '')}, {place.get('country', '')}"),
                url=f"https://jobs.smartrecruiters.com/{company}/{item['id']}",
                posted=(item.get("releasedDate") or "")[:10],
                contract=contract_type((item.get("typeOfEmployment") or {}).get("label") or "", ""),
                work_mode="Télétravail" if place.get("remote") else "Hybride" if place.get("hybrid") else "",
            )
            if place.get("country", "").lower() == "cy" or re.search(r"cyprus", job.location, re.IGNORECASE):
                try:  # the list has no description: ask for it per offer in Cyprus
                    sections = (fetch(session, f"{api}/{item['id']}", as_json=True).get("jobAd") or {}).get(
                        "sections") or {}
                    job.description = _text(" ".join((part or {}).get("text") or "" for part in sections.values()))
                except RuntimeError:
                    pass
            jobs.append(job)
        if offset + 100 >= data.get("totalFound", 0):
            break
    return jobs


def _salary(low, high, currency, interval) -> tuple[int, int, str] | None:
    """Lever's salary range, in gross per month."""
    if not low and not high:
        return None
    low, high = float(low or high), float(high or low)
    if "year" in (interval or "") or low >= 12000:
        low, high = low / 12, high / 12
    symbol = {"EUR": "€", "USD": "$", "GBP": "£"}.get((currency or "").upper(), "€")
    return round(low), round(high), symbol


def _date_from_ms(milliseconds) -> str:
    return datetime.fromtimestamp(milliseconds / 1000, timezone.utc).date().isoformat() if milliseconds else ""


def _text(html_text: str) -> str:
    return clean(BeautifulSoup(html_text or "", "html.parser").get_text(" "))
