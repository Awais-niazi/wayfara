"""Resolve Opintopolku koulutus oids for curated programmes that lack one.

Manually seeded KB rows have no external_id, so their workspace "gate" button
falls back to a Studyinfo keyword search — which, for generic programme names
("Information and Communications Technology"), buries the actual programme
under dozens of lookalikes. Worse, the scraper has often ingested the same
programme as a SEPARATE row (it upserts by oid, so it can't converge into a
manual row), leaving duplicates in the catalog: the curated row students match
against, and a scraped twin holding the oid.

This command searches konfo by programme name and, when exactly one hit agrees
on provider + name + degree level:
  - if a scraped twin row holds that oid, the twin is MERGED into the curated
    row (oid moves over, blank fields backfilled, twin deleted) so future
    scraper runs upsert into the curated row from now on;
  - otherwise the oid is simply assigned.
Students whose matches pointed at a deleted twin are re-matched at the end.

Conservative by design: ambiguous or unmatched programmes are reported and
left untouched (curators can fill external_id by hand in admin). Twins with
live applications are never deleted.

Usage:
    manage.py backfill_studyinfo_oids            # apply
    manage.py backfill_studyinfo_oids --dry-run  # report only
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from scraping.scrapers import OpintopolkuScraper, _UNI_ALIASES, _normalize
from universities.models import Program


def _canonical_provider(name_en: str) -> str:
    return _normalize(_UNI_ALIASES.get(_normalize(name_en), name_en))


# Curated fields the twin may fill IF the curated row left them blank. Fees and
# deadlines stay curator-owned; we never overwrite a non-blank curated value.
_BACKFILL_FIELDS = ("description", "min_ielts_score", "application_deadline", "tuition_fee_eur")


class Command(BaseCommand):
    help = "Fill Program.external_id from Opintopolku search; merge scraped twin rows."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Report matches, change nothing")

    def handle(self, *args, **options):
        dry = options["dry_run"]
        scraper = OpintopolkuScraper(source=None)
        todo = Program.objects.filter(is_active=True, external_id=None).select_related("university")

        resolved = merged = skipped = 0
        affected_students = set()

        for program in todo:
            oids = self._candidates(scraper, program)
            if len(oids) != 1:
                skipped += 1
                why = "no match" if not oids else f"{len(oids)} ambiguous hits"
                self.stdout.write(f"  – {program}: {why}")
                continue

            oid = oids[0]
            twin = Program.objects.filter(external_id=oid).exclude(pk=program.pk).first()
            if twin is not None:
                if twin.university_id != program.university_id:
                    skipped += 1
                    self.stdout.write(f"  – {program}: oid held by other university ({twin})")
                    continue
                if twin.applications.exists():
                    skipped += 1
                    self.stdout.write(f"  – {program}: twin {twin.pk} has live applications, not touching")
                    continue
                merged += 1
                twin_pk = twin.pk
                if not dry:
                    affected_students.update(
                        twin.matches.values_list("student_id", flat=True)
                    )
                    with transaction.atomic():
                        for field in _BACKFILL_FIELDS:
                            if not getattr(program, field) and getattr(twin, field):
                                setattr(program, field, getattr(twin, field))
                        if program.campus_id is None and twin.campus_id is not None:
                            program.campus_id = twin.campus_id
                        twin.delete()  # cascades the twin's matches
                        program.external_source = "opintopolku"
                        program.external_id = oid
                        program.save()
                self.stdout.write(f"  ⇄ {program}: merged scraped twin {twin_pk} -> {oid}")
            else:
                resolved += 1
                if not dry:
                    program.external_source = "opintopolku"
                    program.external_id = oid
                    program.save(update_fields=["external_source", "external_id"])
                self.stdout.write(f"  ✓ {program} -> {oid}")

        # Matches that pointed at deleted twins are gone — rebuild those students.
        if affected_students and not dry:
            from applications.services import match_programs_for_student

            for student_id in affected_students:
                match_programs_for_student(student_id)
            self.stdout.write(f"  ↻ re-matched {len(affected_students)} student(s)")

        summary = f"Assigned {resolved}, merged {merged}, skipped {skipped}" + (
            " (dry run)" if dry else ""
        )
        self.stdout.write(self.style.SUCCESS(summary))

    def _candidates(self, scraper, program):
        """Konfo oids that agree with the programme on provider, name and level."""
        try:
            data = scraper.fetch_search(program.name)
        except Exception as exc:  # network hiccup: skip, never crash the run
            self.stderr.write(f"  ! search failed for {program}: {exc}")
            return []

        uni_key = _normalize(program.university.name)
        want_name = _normalize(program.name)
        loose, exact = [], []
        for hit in data.get("hits", []):
            oid = hit.get("oid")
            kind = hit.get("koulutustyyppi")
            if not oid or kind not in ("yo", "amk"):
                continue
            name = (hit.get("nimi") or {}).get("en")
            provider = ((hit.get("toteutustenTarjoajat") or {}).get("nimi") or {}).get("en")
            if not name or not provider:
                continue
            if _canonical_provider(provider) != uni_key:
                continue
            # Konfo decorates names ("Master's Degree Programme in X, (2 years)")
            # — containment either way is the signal once provider and degree
            # level already agree.
            hit_name = _normalize(name)
            if want_name not in hit_name and hit_name not in want_name:
                continue
            ects = hit.get("opintojenLaajuusNumero")
            if scraper._degree_level(name, ects) != program.degree_level:
                continue
            loose.append(oid)
            # "software engineering, …" is our programme; "software engineering
            # and digital transformation, …" is a different one. The comma
            # boundary separates the two.
            if hit_name == want_name or hit_name.startswith(want_name + ","):
                exact.append(oid)
        if len(loose) > 1 and len(exact) == 1:
            return exact
        return loose
