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
    natural_key: dict               # locate the existing row, e.g. {"external_id": oid}
    fields: dict = dc_field(default_factory=dict)
    related: dict = dc_field(default_factory=dict)   # FK values needed only on create
    allow_create: bool = False      # create the row if the natural_key finds nothing


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


KONFO_BASE = "https://opintopolku.fi/konfo-backend"

# Search terms grouped by the field_of_study they map to. Driving the search by
# our own categories means every ingested programme gets a correct
# field_of_study by construction.
KONFO_SEARCHES = [
    ("computer science", "IT"),
    ("software", "IT"),
    ("data science", "IT"),
    ("artificial intelligence", "IT"),
    ("information technology", "IT"),
    ("engineering", "Engineering"),
    ("business", "Business"),
    ("economics", "Business"),
    ("design", "Design"),
]

# konfo English provider names that differ from our seeded canonical names.
_UNI_ALIASES = {
    "lappeenranta-lahti university of technology lut": "LUT University",
}


def _normalize(name):
    return " ".join(name.lower().split())


def _strip_html(html):
    from bs4 import BeautifulSoup

    return BeautifulSoup(html or "", "lxml").get_text(" ", strip=True)


@register("opintopolku_programs")
class OpintopolkuScraper(BaseScraper):
    """Ingest the English-taught programme catalogue from Studyinfo/Opintopolku.

    Brings in the fields that are RELIABLY clean at the search level — name,
    English description, provider university, ECTS, degree level, stable koulutus
    oid. Tuition and application deadlines live several inconsistent levels
    deeper and are deliberately NOT sourced here; they stay as admin-managed
    baselines. New programmes are created; changes to existing ones flow through
    the tiered review policy.
    """

    page_size = 50

    def fetch_search(self, keyword):
        """Isolated for mocking in tests."""
        import requests

        resp = requests.get(
            f"{KONFO_BASE}/search/koulutukset",
            params={"keyword": keyword, "lng": "en", "page": 1, "size": self.page_size},
            headers={"User-Agent": self.user_agent},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def _resolve_university(self, name_en, koulutustyyppi):
        from universities.models import University

        canonical = _UNI_ALIASES.get(_normalize(name_en), name_en)
        uni = University.objects.filter(name__iexact=canonical).first()
        if uni is None:
            kind = (
                University.InstitutionType.AMK
                if koulutustyyppi == "amk"
                else University.InstitutionType.UNIVERSITY
            )
            uni = University.objects.create(name=canonical, institution_type=kind, is_active=True)
        return uni

    @staticmethod
    def _degree_level(name, ects):
        from universities.models import Program

        n = name.lower()
        if "bachelor" in n:
            return Program.DegreeLevel.BACHELORS
        if "master" in n:
            return Program.DegreeLevel.MASTERS
        if ects and ects >= 180:
            return Program.DegreeLevel.BACHELORS
        return Program.DegreeLevel.MASTERS

    def scrape(self):
        from universities.models import Program

        seen = set()
        records = []
        for keyword, field_of_study in KONFO_SEARCHES:
            data = self.fetch_search(keyword)
            for hit in data.get("hits", []):
                oid = hit.get("oid")
                kind = hit.get("koulutustyyppi")
                if not oid or oid in seen or kind not in ("yo", "amk"):
                    continue
                name = (hit.get("nimi") or {}).get("en")
                provider = ((hit.get("toteutustenTarjoajat") or {}).get("nimi") or {}).get("en")
                if not name or not provider:
                    continue
                seen.add(oid)

                uni = self._resolve_university(provider, kind)
                ects = hit.get("opintojenLaajuusNumero")
                records.append(ScrapedRecord(
                    model="universities.Program",
                    natural_key={"external_id": oid},
                    fields={
                        "name": name[:200],
                        "field_of_study": field_of_study,
                        "degree_level": self._degree_level(name, ects),
                        "description": _strip_html((hit.get("kuvaus") or {}).get("en", "")),
                        "language": "English",
                        "intake": Program.Intake.SEPTEMBER,
                        "external_source": "opintopolku",
                        "duration_years": 3 if (ects or 0) >= 180 else 2,
                    },
                    related={"university": uni},
                    allow_create=True,
                ))
        return records


@register("migri_figures")
class MigriFiguresScraper(BaseScraper):
    """STUB — scrape Migri's student residence-permit financial requirement.

    Should yield a ScrapedRecord for applications.PolicyFigure keyed by code
    (e.g. migri_monthly_funds_eur) with the current value.
    """

    def scrape(self):
        return []
