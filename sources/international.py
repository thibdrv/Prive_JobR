"""Job sites that are not Cypriot but list offers in Cyprus: Workable's job search, Djinni and Relocate.me."""
import re
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from experience import contract_type
from .common import Job, Settings, clean, fetch, has_word

_WORKPLACES = {"remote": "Télétravail", "hybrid": "Hybride", "on_site": "Sur place", "onsite": "Sur place"}


def workable(session, keyword: str, settings: Settings) -> list[Job]:
    """Every company that recruits with Workable and has an offer in Cyprus (jobs.workable.com)."""
    jobs: list[Job] = []
    token = None
    for _ in range(settings.max_pages):
        params = {"location": "Cyprus", "query": keyword}
        if token:
            params["pageToken"] = token
        data = fetch(session, "https://jobs.workable.com/api/v1/jobs", params, as_json=True)
        for item in data.get("jobs", []):
            place = item.get("location") or {}
            sections = " ".join(item.get(key) or "" for key in ("description", "requirementsSection", "benefitsSection"))
            jobs.append(Job(
                source="Workable",
                title=clean(item.get("title")),
                company=clean((item.get("company") or {}).get("title")),
                location=clean(", ".join(part for part in (place.get("city"), place.get("countryName")) if part)
                               or "; ".join(item.get("locations") or [])),
                url=item.get("url", ""),
                posted=(item.get("created") or "")[:10],
                description=clean(BeautifulSoup(sections, "html.parser").get_text(" ")),
                contract=contract_type(item.get("employmentType") or "", ""),
                work_mode=_WORKPLACES.get((item.get("workplace") or "").lower(), ""),
            ))
        token = data.get("nextPageToken")
        if not token:
            break
    return [job for job in jobs if job.url]


def djinni(session, keyword: str, settings: Settings) -> list[Job]:
    """Djinni (tech jobs): offers in Cyprus and remote offers open to people living there."""
    jobs: list[Job] = []
    # the place must be open to Cyprus: "Countries of Europe or Ukraine" yes, "Ukraine" no
    allowed = ["cyprus", *settings.cities, *(p for p in settings.remote_locations if p.lower() != "remote")]
    for page in range(1, settings.max_pages + 1):
        html = fetch(session, "https://djinni.co/jobs/", {"location": "cyprus", "all_keywords": keyword, "page": page})
        cards = BeautifulSoup(html, "html.parser").select(".job-item")
        for card in cards:
            link = card.select_one("a[href^='/jobs/']")
            title = card.select_one(".job-item__position")
            if not link or not title:
                continue
            details = [clean(span.get_text(" ")) for span in card.select(".fw-medium > span") if "middot" not in
                       (span.get("class") or [])]
            place = clean(_text(card, ".location-text"))
            mode = next((d for d in details if re.search(r"remote|office|hybrid", d, re.IGNORECASE)), "")
            company = card.select_one("header .col span")
            updated = next((clean(span.get_text()) for span in card.select("span[title]")
                            if re.search(r"ago|yesterday|today", span.get_text())), "")
            job = Job(
                source="Djinni",
                title=clean(title.get_text()),
                company=clean(company.get_text()) if company else "",
                location=f"{place} ({mode})" if mode else place,
                url=urljoin("https://djinni.co", link["href"]),
                posted=_djinni_age(updated),
                description=clean(_text(card, ".js-original-text")),
                work_mode=("Télétravail" if "remote" in mode.lower() else "Hybride" if "hybrid" in mode.lower()
                           else "Sur place" if "office" in mode.lower() else ""),
            )
            if any(has_word(place, word) for word in allowed):
                jobs.append(job)
        if not cards or f"page={page + 1}" not in html:
            break
    return jobs


def relocate(session, settings: Settings) -> list[Job]:
    """Relocate.me (jobs with relocation help): its latest offers, all countries, keeping those in Cyprus.

    Its search page is filled in by the browser, so the offers are read from its list of newest ones.
    """
    jobs: list[Job] = []
    for page in range(1, 11):
        html = fetch(session, "https://relocate.me/search", {"page": page})
        titles = BeautifulSoup(html, "html.parser").select(".job__title a[href]")
        for link in titles:
            parts = link["href"].strip("/").split("/")  # cyprus / limassol / company / title-id
            if len(parts) != 4 or parts[0] != "cyprus":
                continue
            jobs.append(Job(
                source="Relocate.me",
                title=clean(link.select_one("b").get_text() if link.select_one("b") else link.get_text()),
                company=parts[2].replace("-", " ").title(),
                location=f"{parts[1].replace('-', ' ').title()}, Cyprus",
                url=urljoin("https://relocate.me", link["href"]),
            ))  # no search: only the offers that fit one of your job types are kept
        if not titles or f"page={page + 1}" not in html:
            break
    return jobs


def _djinni_age(updated: str) -> str:
    """"updated 2d ago" -> "2 days ago", the wording the age filter reads."""
    match = re.search(r"(\d+)\s*(mo|w|d|h|m)\b", updated)
    if not match:
        return updated.replace("updated", "").strip()
    unit = {"mo": "months", "w": "weeks", "d": "days"}.get(match.group(2))
    return f"{match.group(1)} {unit} ago" if unit else "today"


def _text(card, selector: str) -> str:
    node = card.select_one(selector)
    return node.get_text(" ") if node else ""
