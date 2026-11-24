"""Every job site the app can read, by the name used in settings.json."""
from . import cyprus_sites, eures, international, remote_boards
from .companies import company_jobs

SOURCES = {
    "ergodotisi": cyprus_sites.ergodotisi,
    "cyprusjobs": cyprus_sites.cyprusjobs,
    "cypruswork": cyprus_sites.cypruswork,
    "fxcareer": cyprus_sites.fxcareer,
    "kariera": cyprus_sites.kariera,
    "eures": eures.eures,
    "workable": international.workable,
    "djinni": international.djinni,
    "himalayas": remote_boards.himalayas,
    "weworkremotely": remote_boards.weworkremotely,
    "remoteok": remote_boards.remoteok,
    "jobicy": remote_boards.jobicy,
    "remotive": remote_boards.remotive,
}

# Sites read in full (by category, not by search): called once per run, each offer's search is its category there.
BROWSE_SOURCES = {
    "careerfinders": cyprus_sites.careerfinders,
    "emeraldzebra": cyprus_sites.emeraldzebra,
    "relocate": international.relocate,
}

# The careers pages of the companies in the settings: read once per company.
COMPANY_SOURCE = "companies"

# Remote-work boards: their offers are not tied to a city, so the city filter skips them.
# Djinni also lists offers in a Cypriot office, but most are remote: it checks the places itself.
REMOTE_SOURCES = {"remotive", "remoteok", "jobicy", "weworkremotely", "himalayas", "djinni"}

__all__ = ["SOURCES", "BROWSE_SOURCES", "COMPANY_SOURCE", "REMOTE_SOURCES", "company_jobs"]
