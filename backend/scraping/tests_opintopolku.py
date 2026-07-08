from unittest.mock import patch

from django.test import TestCase

from universities.models import Program, University

from .models import DataChange, ScrapeSource
from .scrapers import OpintopolkuScraper
from .services import run_source


def hit(oid, name, provider, kind="yo", ects=120, desc="<p>Great.</p>"):
    return {
        "oid": oid, "koulutustyyppi": kind,
        "nimi": {"en": name}, "kuvaus": {"en": desc},
        "opintojenLaajuusNumero": ects,
        "toteutustenTarjoajat": {"nimi": {"en": provider}},
    }


# keyword -> konfo-shaped response
FIXTURES = {
    "computer science": {"hits": [
        hit("oid-cs", "Data Science, Master's Programme (2 yrs)", "Aalto University"),
    ]},
    "engineering": {"hits": [
        hit("oid-eng", "Chemical Engineering, Bachelor (3 yrs)", "Aalto University", ects=180),
    ]},
    "business": {"hits": [
        hit("oid-biz", "International Business", "Metropolia University of Applied Sciences", kind="amk"),
        hit("oid-skip", "Some Vocational Thing", "A College", kind="amm"),  # not higher-ed
    ]},
}


def fake_fetch(self, keyword):
    return FIXTURES.get(keyword, {"hits": []})


class OpintopolkuIngestTests(TestCase):
    def setUp(self):
        self.src = ScrapeSource.objects.create(
            name="Opintopolku", scraper_key="opintopolku_programs"
        )

    @patch.object(OpintopolkuScraper, "fetch_search", fake_fetch)
    def test_ingest_creates_clean_programmes(self):
        run_source(self.src.pk)

        # three higher-ed hits ingested, the "amm" one skipped
        self.assertEqual(Program.objects.filter(external_source="opintopolku").count(), 3)
        self.assertFalse(Program.objects.filter(external_id="oid-skip").exists())

        ds = Program.objects.get(external_id="oid-cs")
        self.assertEqual(ds.field_of_study, "IT")          # from the search category
        self.assertEqual(ds.degree_level, "masters")        # inferred from name
        self.assertEqual(ds.university.name, "Aalto University")
        self.assertEqual(ds.description, "Great.")           # HTML stripped

        eng = Program.objects.get(external_id="oid-eng")
        self.assertEqual(eng.field_of_study, "Engineering")
        self.assertEqual(eng.degree_level, "bachelors")

    @patch.object(OpintopolkuScraper, "fetch_search", fake_fetch)
    def test_new_provider_university_created_with_right_type(self):
        run_source(self.src.pk)
        metro = University.objects.get(name="Metropolia University of Applied Sciences")
        self.assertEqual(metro.institution_type, "amk")

    def test_university_alias_resolves_without_duplicate(self):
        University.objects.create(name="LUT University", institution_type="university", city="Lappeenranta")
        fixture = {"lut": {"hits": [
            hit("oid-lut", "Software Engineering, Master's Programme",
                "Lappeenranta-Lahti University of Technology LUT")
        ]}}
        with patch.object(OpintopolkuScraper, "fetch_search",
                          lambda self, kw: fixture.get(kw, {"hits": []})), \
             patch("scraping.scrapers.KONFO_SEARCHES", [("lut", "IT")]):
            run_source(self.src.pk)
        self.assertEqual(University.objects.filter(name__icontains="LUT").count(), 1)
        self.assertEqual(Program.objects.get(external_id="oid-lut").university.name, "LUT University")

    @patch.object(OpintopolkuScraper, "fetch_search", fake_fetch)
    def test_idempotent_rerun(self):
        run_source(self.src.pk)
        n_progs, n_unis = Program.objects.count(), University.objects.count()
        run_source(self.src.pk)
        self.assertEqual(Program.objects.count(), n_progs)
        self.assertEqual(University.objects.count(), n_unis)
        self.assertEqual(DataChange.objects.count(), 0)

    def test_existing_programme_change_follows_tiered_policy(self):
        run_source(self.src.pk) if False else None
        with patch.object(OpintopolkuScraper, "fetch_search", fake_fetch):
            run_source(self.src.pk)
        ds = Program.objects.get(external_id="oid-cs")

        # now konfo reports a new description (low -> auto) and a new name (critical -> staged)
        changed = {"computer science": {"hits": [
            hit("oid-cs", "Data Science RENAMED, Master's Programme", "Aalto University",
                desc="<p>Updated blurb.</p>")
        ]}}
        with patch.object(OpintopolkuScraper, "fetch_search",
                          lambda self, kw: changed.get(kw, {"hits": []})), \
             patch("scraping.scrapers.KONFO_SEARCHES", [("computer science", "IT")]):
            run_source(self.src.pk)

        ds.refresh_from_db()
        self.assertEqual(ds.description, "Updated blurb.")   # low-risk applied
        self.assertEqual(ds.name, "Data Science, Master's Programme (2 yrs)")  # name unchanged (staged)
        staged = DataChange.objects.get(field_name="name", status="pending_review")
        self.assertEqual(staged.risk, "critical")
