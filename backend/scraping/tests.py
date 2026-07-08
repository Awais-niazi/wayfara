from datetime import date

from django.core import mail
from django.test import TestCase

from applications.models import PolicyFigure
from universities.models import Program, University

from . import scrapers
from .models import DataChange, ScrapeRun, ScrapeSource
from .scrapers import BaseScraper, ScrapedRecord, register
from .services import run_source


def make_program(**overrides):
    uni = University.objects.create(
        name=overrides.pop("uni", "Aalto University"), institution_type="university", city="Espoo"
    )
    defaults = dict(
        university=uni, name="Computer Science", degree_level="masters",
        field_of_study="IT", intake="september",
        tuition_fee_eur=15000, application_deadline=date(2027, 1, 15),
        description="Old description.",
    )
    return Program.objects.create(**{**defaults, **overrides})


class ReconcileTests(TestCase):
    def tearDown(self):
        # keep the scraper registry clean between tests
        for key in ("fake_prog", "fake_boom", "fake_figure"):
            scrapers.SCRAPER_REGISTRY.pop(key, None)

    def _source(self, key):
        return ScrapeSource.objects.create(name=f"src-{key}", scraper_key=key)

    def test_low_risk_change_auto_applies(self):
        prog = make_program()

        @register("fake_prog")
        class _S(BaseScraper):
            def scrape(self):
                return [ScrapedRecord(
                    "universities.Program",
                    {"university__name": "Aalto University", "name": "Computer Science"},
                    {"description": "Fresh new description."},
                )]

        run_source(self._source("fake_prog").pk)
        prog.refresh_from_db()
        self.assertEqual(prog.description, "Fresh new description.")  # applied live
        change = DataChange.objects.get()
        self.assertEqual(change.risk, "low")
        self.assertEqual(change.status, "applied")
        self.assertTrue(change.applied_automatically)

    def test_critical_change_is_staged_not_applied(self):
        prog = make_program()

        @register("fake_prog")
        class _S(BaseScraper):
            def scrape(self):
                return [ScrapedRecord(
                    "universities.Program",
                    {"university__name": "Aalto University", "name": "Computer Science"},
                    {"application_deadline": "2027-02-01", "tuition_fee_eur": "16000"},
                )]

        run_source(self._source("fake_prog").pk)
        prog.refresh_from_db()
        # live data untouched
        self.assertEqual(prog.application_deadline, date(2027, 1, 15))
        self.assertEqual(int(prog.tuition_fee_eur), 15000)
        # staged for review + alert email sent
        pending = DataChange.objects.filter(status="pending_review", risk="critical")
        self.assertEqual(pending.count(), 2)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("need review", mail.outbox[0].subject)

    def test_approving_a_staged_change_applies_it_typed(self):
        prog = make_program()

        @register("fake_prog")
        class _S(BaseScraper):
            def scrape(self):
                return [ScrapedRecord(
                    "universities.Program",
                    {"university__name": "Aalto University", "name": "Computer Science"},
                    {"application_deadline": "2027-02-01"},
                )]

        run_source(self._source("fake_prog").pk)
        change = DataChange.objects.get(status="pending_review")
        change.apply(automatic=False)  # admin approval path
        prog.refresh_from_db()
        self.assertEqual(prog.application_deadline, date(2027, 2, 1))  # coerced to date
        self.assertFalse(change.applied_automatically)

    def test_no_diff_no_change(self):
        make_program()

        @register("fake_prog")
        class _S(BaseScraper):
            def scrape(self):
                return [ScrapedRecord(
                    "universities.Program",
                    {"university__name": "Aalto University", "name": "Computer Science"},
                    {"tuition_fee_eur": "15000", "description": "Old description."},
                )]

        run_source(self._source("fake_prog").pk)
        self.assertEqual(DataChange.objects.count(), 0)

    def test_scraper_error_isolated_run_marked_failed(self):
        @register("fake_boom")
        class _S(BaseScraper):
            def scrape(self):
                raise RuntimeError("site layout changed")

        run_source(self._source("fake_boom").pk)
        run = ScrapeRun.objects.get()
        self.assertEqual(run.status, "failed")
        self.assertIn("layout changed", run.error)

    def test_unknown_field_defaults_to_critical(self):
        make_program()
        PolicyFigure.objects.create(code="migri_monthly_funds_eur", label="Migri funds", value="560", unit="EUR/month")

        @register("fake_figure")
        class _S(BaseScraper):
            def scrape(self):
                return [ScrapedRecord(
                    "applications.PolicyFigure",
                    {"code": "migri_monthly_funds_eur"},
                    {"value": "600"},
                )]

        run_source(self._source("fake_figure").pk)
        figure = PolicyFigure.objects.get(code="migri_monthly_funds_eur")
        self.assertEqual(figure.value, "560")  # NOT auto-applied
        self.assertEqual(DataChange.objects.get().risk, "critical")
