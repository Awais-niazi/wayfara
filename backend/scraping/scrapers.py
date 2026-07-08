"""Scraper framework.

A scraper fetches a source and returns a list of ScrapedRecord — each a
target model, a natural key to locate the existing row, and the fields it
observed. The reconcile engine (services.py) does all DB/diff/policy work;
scrapers only produce data, so they stay simple and independently testable.

Concrete per-site scrapers (Migri, Studyinfo, individual universities) are
STUBS: the parsing selectors must be written and verified against the live
sites before they are enabled. Enable a source by creating a ScrapeSource row
whose scraper_key matches a @register name.
"""

from dataclasses import dataclass, field as dc_field

import requests

SCRAPER_REGISTRY = {}


def register(key):
    def wrap(cls):
        SCRAPER_REGISTRY[key] = cls
        cls.key = key
        return cls
    return wrap


@dataclass
class ScrapedRecord:
    model: str                      # "universities.Program"
    natural_key: dict               # {"university__name": "...", "name": "..."}
    fields: dict = dc_field(default_factory=dict)


class BaseScraper:
    """Subclass and implement scrape() -> list[ScrapedRecord]."""

    timeout = 20
    user_agent = "WayfaraBot/1.0 (+https://wayfara.app; student guidance)"

    def __init__(self, source):
        self.source = source

    def get(self, url):
        resp = requests.get(
            url, timeout=self.timeout, headers={"User-Agent": self.user_agent}
        )
        resp.raise_for_status()
        return resp.text

    def scrape(self):
        raise NotImplementedError


@register("studyinfo_programs")
class StudyinfoProgramScraper(BaseScraper):
    """STUB — fill in real parsing against Studyinfo.fi.

    Should yield one ScrapedRecord per program with at least
    application_deadline / application_opens / tuition_fee_eur so the reconcile
    engine can refresh those (critical) fields into the review queue.
    """

    def scrape(self):
        # html = self.get(self.source.url)
        # ... parse with BeautifulSoup(html, "lxml") ...
        return []


@register("migri_figures")
class MigriFiguresScraper(BaseScraper):
    """STUB — scrape Migri's student residence-permit financial requirement.

    Should yield a ScrapedRecord for applications.PolicyFigure keyed by code
    (e.g. migri_monthly_funds_eur) with the current value.
    """

    def scrape(self):
        return []
