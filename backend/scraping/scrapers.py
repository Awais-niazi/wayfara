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

import logging
from dataclasses import dataclass, field as dc_field

import requests

logger = logging.getLogger(__name__)

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

    def _get_json(self, path):
        import requests

        resp = requests.get(
            f"{KONFO_BASE}{path}",
            headers={"User-Agent": self.user_agent},
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    # The three fetches are separated so tests can mock them without a network.
    def fetch_search(self, keyword):
        return self._get_json(
            f"/search/koulutukset?keyword={keyword}&lng=en&page=1&size={self.page_size}"
        )

    def fetch_koulutus(self, oid):
        return self._get_json(f"/koulutus/{oid}")

    def fetch_toteutus(self, oid):
        return self._get_json(f"/toteutus/{oid}")

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

    def _enrich(self, koulutus_oid, university):
        """Fetch toteutus detail and extract tuition, deadline, start, campus.

        Returns a dict of Program fields (+ a resolved Campus). Any part that
        can't be read is simply omitted — partial data is fine, never fabricated.
        Never raises: enrichment failure must not lose the catalogue record.
        """
        from datetime import date

        from universities.models import Campus, Program

        out = {}
        campus = None
        try:
            detail = self.fetch_koulutus(koulutus_oid)
            toteutukset = detail.get("toteutukset") or []
            if not toteutukset:
                return out, None
            tot = self.fetch_toteutus(toteutukset[0]["oid"])

            # Tuition: yearly fee (lukuvuosimaksu) non-EU students pay; else free.
            maksut = ((tot.get("metadata") or {}).get("opetus") or {}).get("maksut") or []
            fee = next((m.get("maksunMaara") for m in maksut
                        if m.get("maksullisuustyyppi") == "lukuvuosimaksu"), None)
            if fee is not None:
                out["tuition_fee_eur"] = fee

            # Application window + campus from the application targets.
            deadlines, opens = [], []
            for ht in (tot.get("hakutiedot") or []):
                kausi = (ht.get("koulutuksenAlkamiskausi") or {})
                year = kausi.get("koulutuksenAlkamisvuosi")
                season = (((kausi.get("koulutuksenAlkamiskausi") or {}).get("koodiUri")) or "")
                if year:
                    if season.startswith("kausi_s"):
                        out["intake"] = Program.Intake.SEPTEMBER
                        out["start_date"] = date(int(year), 9, 1).isoformat()
                    elif season.startswith("kausi_k"):
                        out["intake"] = Program.Intake.JANUARY
                        out["start_date"] = date(int(year), 1, 8).isoformat()
                for hk in ht.get("hakukohteet", []):
                    if campus is None:
                        cname = ((hk.get("jarjestyspaikka") or {}).get("nimi") or {}).get("en")
                        if cname:
                            campus, _ = Campus.objects.get_or_create(
                                university=university, name=cname[:200],
                                defaults={"city": cname.split(",")[-1].strip()[:100]},
                            )
                    for ha in hk.get("hakuajat", []):
                        if ha.get("paattyy"):
                            deadlines.append(ha["paattyy"][:10])
                        if ha.get("alkaa"):
                            opens.append(ha["alkaa"][:10])
            if deadlines:
                out["application_deadline"] = max(deadlines)
            if opens:
                out["application_opens"] = min(opens)
        except Exception:  # noqa: BLE001 — never lose the catalogue row over enrichment
            logger.warning("Enrichment failed for koulutus %s", koulutus_oid, exc_info=True)
        return out, campus

    def scrape(self):
        """Yield one ScrapedRecord per programme (generator, so the caller can
        commit incrementally over a long run)."""
        from universities.models import Program

        seen = set()
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
                fields = {
                    "name": name[:200],
                    "field_of_study": field_of_study,
                    "degree_level": self._degree_level(name, ects),
                    "description": _strip_html((hit.get("kuvaus") or {}).get("en", "")),
                    "language": "English",
                    "intake": Program.Intake.SEPTEMBER,
                    "external_source": "opintopolku",
                    "duration_years": 3 if (ects or 0) >= 180 else 2,
                }
                # Enrich with tuition / deadline / start / campus from detail.
                enriched, campus = self._enrich(oid, uni)
                fields.update(enriched)
                related = {"university": uni}
                if campus is not None:
                    related["campus"] = campus

                yield ScrapedRecord(
                    model="universities.Program",
                    natural_key={"external_id": oid},
                    fields=fields,
                    related=related,
                    allow_create=True,
                )


@register("migri_figures")
class MigriFiguresScraper(BaseScraper):
    """STUB — scrape Migri's student residence-permit financial requirement.

    Should yield a ScrapedRecord for applications.PolicyFigure keyed by code
    (e.g. migri_monthly_funds_eur) with the current value.
    """

    def scrape(self):
        return []
