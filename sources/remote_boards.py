"""Remote-job boards with a free public API: Remotive, RemoteOK, Jobicy, We Work Remotely and Himalayas.

Most boards give their whole list in one request, so it is downloaded once per run
and every search is matched against the job titles locally. Himalayas has a search of its own.
"""
import html
import re
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from bs4 import BeautifulSoup

from experience import contract_type, salary_range
from .common import Job, Settings, clean, fetch, title_matches

_feeds: dict[str, list[Job]] = {}


def remotive(session, keyword: str, settings: Settings) -> list[Job]:
    return _matching("remotive", _load_remotive, session, keyword, settings)


def remoteok(session, keyword: str, settings: Settings) -> list[Job]:
    return _matching("remoteok", _load_remoteok, session, keyword, settings)


def jobicy(session, keyword: str, settings: Settings) -> list[Job]:
    return _matching("jobicy", _load_jobicy, session, keyword, settings)


def weworkremotely(session, keyword: str, settings: Settings) -> list[Job]:
    return _matching("weworkremotely", _load_weworkremotely, session, keyword, settings)


def himalayas(session, keyword: str, settings: Settings) -> list[Job]:
    """Himalayas' search, limited to the offers open to people living in Cyprus."""
    jobs: list[Job] = []
    for page in range(settings.max_pages):
        data = fetch(session, "https://himalayas.app/jobs/api/search",
                     {"q": keyword, "country": "Cyprus", "page": page + 1}, as_json=True)
        for item in data.get("jobs", []):
            places = item.get("locationRestrictions") or []
            low, high = item.get("minSalary"), item.get("maxSalary")
            period = (item.get("salaryPeriod") or "").lower()
            jobs.append(Job(
                source="Himalayas",
                title=clean(html.unescape(item.get("title") or "")),
                company=clean(html.unescape(item.get("companyName") or "")),
                location="Worldwide" if not places else "Cyprus" if "Cyprus" in places else ", ".join(places[:5]),
                url=item.get("applicationLink") or item.get("guid") or "",
                posted=_date_from_seconds(item.get("pubDate")),
                description=_text(item.get("description")),
                contract=contract_type(item.get("employmentType") or "", ""),
                work_mode="Télétravail",
                salary=(_yearly(low, high, {"EUR": "€", "GBP": "£"}.get(item.get("currency") or "", "$"))
                        if period in ("annual", "yearly", "") else None),
            ))
        if len(data.get("jobs", [])) < 20:
            break
    return [job for job in jobs if job.url and title_matches(job.title, keyword)]


def _matching(name, loader, session, keyword: str, settings: Settings) -> list[Job]:
    if name not in _feeds:
        _feeds[name] = loader(session)
    allowed = [place.lower() for place in settings.remote_locations]
    return [job for job in _feeds[name]
            if title_matches(job.title, keyword) and _location_ok(job.location, allowed)]


def _location_ok(location: str, allowed: list[str]) -> bool:
    # Many remote jobs are only open to people living in one country (often the USA).
    location = location.lower()
    return not location or not allowed or any(place in location for place in allowed)


def _load_remotive(session) -> list[Job]:
    data = fetch(session, "https://remotive.com/api/remote-jobs", as_json=True)
    return [Job(
        source="Remotive",
        title=clean(item.get("title")),
        company=clean(item.get("company_name")),
        location=clean(item.get("candidate_required_location")),
        url=item.get("url", ""),
        posted=(item.get("publication_date") or "")[:10],
        description=_text(item.get("description")),
        contract=contract_type((item.get("job_type") or "").replace("_", "-"), ""),
        work_mode="Télétravail",
        salary=salary_range(f"salary {item.get('salary') or ''}"),
    ) for item in data.get("jobs", []) if item.get("url")]


def _load_remoteok(session) -> list[Job]:
    data = fetch(session, "https://remoteok.com/api", as_json=True)
    return [Job(
        source="RemoteOK",
        title=clean(html.unescape(item.get("position") or "")),
        company=clean(html.unescape(item.get("company") or "")),
        location=clean(item.get("location")),
        url=item.get("url", ""),
        posted=(item.get("date") or "")[:10],
        description=_text(item.get("description")),
        work_mode="Télétravail",
        salary=_yearly(item.get("salary_min"), item.get("salary_max"), "$"),
    ) for item in data if isinstance(item, dict) and item.get("position") and item.get("url")]


def _load_jobicy(session) -> list[Job]:
    data = fetch(session, "https://jobicy.com/api/v2/remote-jobs", {"count": 100}, as_json=True)
    return [Job(
        source="Jobicy",
        title=clean(html.unescape(item.get("jobTitle") or "")),
        company=clean(html.unescape(item.get("companyName") or "")),
        location=clean(item.get("jobGeo")),
        url=item.get("url", ""),
        posted=(item.get("pubDate") or "")[:10],
        description=_text(item.get("jobDescription")),
        contract=contract_type(" ".join(item.get("jobType") or []), ""),
        work_mode="Télétravail",
        salary=_yearly(item.get("annualSalaryMin"), item.get("annualSalaryMax"),
                       {"EUR": "€", "GBP": "£"}.get(item.get("salaryCurrency") or "", "$")),
    ) for item in data.get("jobs", []) if item.get("url")]


def _load_weworkremotely(session) -> list[Job]:
    feed = fetch(session, "https://weworkremotely.com/remote-jobs.rss")
    jobs = []
    for item in re.findall(r"<item>(.*?)</item>", feed, re.DOTALL):
        def field(tag: str) -> str:
            match = re.search(rf"<{tag}>(.*?)</{tag}>", item, re.DOTALL)
            return html.unescape(re.sub(r"^<!\[CDATA\[|\]\]>$", "", match.group(1).strip())) if match else ""
        company, _, title = field("title").partition(": ")  # "Affirm: Analytics Lead"
        try:
            posted = parsedate_to_datetime(field("pubDate")).date().isoformat()
        except (TypeError, ValueError):
            posted = ""
        jobs.append(Job(
            source="WeWorkRemotely",
            title=clean(title or company),
            company=clean(company if title else ""),
            location=clean(field("region")),
            url=field("link") or field("guid"),
            posted=posted,
            description=_text(field("description")),
            contract=contract_type(field("type"), ""),
            work_mode="Télétravail",
        ))
    return [job for job in jobs if job.url]


def _date_from_seconds(seconds) -> str:
    try:
        return datetime.fromtimestamp(int(seconds), timezone.utc).date().isoformat()
    except (TypeError, ValueError):
        return ""


def _yearly(low, high, currency: str) -> tuple[int, int, str] | None:
    """A yearly salary range, in gross per month."""
    try:
        low, high = float(low or high or 0), float(high or low or 0)
    except (TypeError, ValueError):
        return None
    return (round(low / 12), round(high / 12), currency) if low else None


def _text(description_html: str | None) -> str:
    return clean(BeautifulSoup(html.unescape(description_html or ""), "html.parser").get_text(" "))
