"""Seed real Finnish universities, campuses and English-taught programmes.

Idempotent (keyed on natural keys). Data accuracy note:
- University names, cities, institution types, and programme names are stable,
  verifiable facts.
- Tuition figures, application dates, and IELTS minimums are RESEARCHED
  BASELINES for the autumn-2027 intake and change yearly — they are exactly the
  fields the nightly scraper is built to keep current. Treat them as starting
  values to be confirmed/refreshed, not authoritative.

Sources consulted (July 2026): studyinfinland.fi, study.eu, individual
university tuition pages. Non-EU tuition €8–20k/yr; €100 application fee since
2025; IELTS 6.5 typical for master's.
"""

from datetime import date

from django.core.management.base import BaseCommand

from universities.models import Campus, Program, University

U = University.InstitutionType.UNIVERSITY
AMK = University.InstitutionType.AMK
BSC = Program.DegreeLevel.BACHELORS
MSC = Program.DegreeLevel.MASTERS
SEP = Program.Intake.SEPTEMBER

# Approximate autumn-2027 joint-application window (verify each cycle).
OPENS = date(2027, 1, 7)
DEADLINE = date(2027, 1, 21)
STARTS = date(2027, 9, 1)


def prog(name, field, level=MSC, tuition=12000, ielts="6.5", scholarship=True, accept=None):
    return {
        "name": name, "field_of_study": field, "degree_level": level,
        "tuition_fee_eur": tuition, "min_ielts_score": ielts,
        "scholarship_available": scholarship, "acceptance_rate": accept,
    }


# (name, type, city, [extra campuses], [programmes])
DATA = [
    ("Aalto University", U, "Espoo", ["Otaniemi"], [
        prog("Computer, Communication and Information Sciences", "IT", tuition=15000, accept=12),
        prog("Data Science", "IT", tuition=15000, accept=10),
        prog("Machine Learning, Data Science and AI", "IT", tuition=15000, accept=9),
        prog("Bachelor's in Science and Technology", "Engineering", BSC, tuition=12000, ielts="6.5"),
        prog("International Design Business Management", "Business", tuition=15000),
    ]),
    ("University of Helsinki", U, "Helsinki", [], [
        prog("Data Science", "IT", tuition=18000, accept=13),
        prog("Computer Science", "IT", tuition=15000),
        prog("Bachelor's Programme in Science", "IT", BSC, tuition=13000),
    ]),
    ("Tampere University", U, "Tampere", [], [
        prog("Computing Sciences", "IT", tuition=12000),
        prog("Software, Web and Cloud", "IT", tuition=12000),
        prog("Sustainable Digital Life", "IT", tuition=10000),
        prog("Bachelor's in Computing and Electrical Engineering", "Engineering", BSC, tuition=10000),
    ]),
    ("LUT University", U, "Lappeenranta", ["Lahti"], [
        prog("Software Engineering", "IT", tuition=12500),
        prog("Business Analytics", "Business", tuition=12500),
        prog("Computational Engineering", "Engineering", tuition=12500),
    ]),
    ("University of Oulu", U, "Oulu", [], [
        prog("Computer Science and Engineering", "IT", tuition=13000),
        prog("Wireless Communications Engineering", "Engineering", tuition=13000),
    ]),
    ("University of Turku", U, "Turku", [], [
        prog("Information and Communication Technology", "IT", tuition=12000),
        prog("Bachelor's in Computer Science", "IT", BSC, tuition=10000),
    ]),
    ("University of Jyväskylä", U, "Jyväskylä", [], [
        prog("Cognitive Computing and Collective Intelligence", "IT", tuition=12000),
        prog("Web Intelligence and Service Engineering", "IT", tuition=12000),
    ]),
    ("University of Eastern Finland", U, "Joensuu", ["Kuopio"], [
        prog("Computer Science", "IT", tuition=10000),
        prog("Photonics", "Engineering", tuition=10000),
    ]),
    ("University of Vaasa", U, "Vaasa", [], [
        prog("Smart Energy", "Engineering", tuition=11000),
        prog("International Business", "Business", tuition=11000),
    ]),
    ("Åbo Akademi University", U, "Turku", [], [
        prog("Information Technology", "IT", tuition=10000),
    ]),
    ("University of Lapland", U, "Rovaniemi", [], [
        prog("Service Design", "Design", tuition=10000),
    ]),
    ("Hanken School of Economics", U, "Helsinki", ["Vaasa"], [
        prog("Business Analytics", "Business", tuition=13500),
        prog("Economics", "Business", tuition=13500),
    ]),
    ("University of the Arts Helsinki", U, "Helsinki", [], [
        prog("Global Music", "Design", tuition=10000),
    ]),
    # Universities of Applied Sciences (AMK) — more practice-oriented, common
    # bachelor's destinations for international students.
    ("Metropolia University of Applied Sciences", AMK, "Helsinki", [], [
        prog("Information Technology", "IT", BSC, tuition=12000, ielts="6.0"),
        prog("Industrial Management", "Business", MSC, tuition=11000),
    ]),
    ("Haaga-Helia University of Applied Sciences", AMK, "Helsinki", [], [
        prog("Business Information Technology", "IT", BSC, tuition=11000, ielts="6.0"),
        prog("International Business", "Business", BSC, tuition=11000, ielts="6.0"),
    ]),
    ("Laurea University of Applied Sciences", AMK, "Vantaa", [], [
        prog("Business Management", "Business", BSC, tuition=10000, ielts="6.0"),
    ]),
    ("JAMK University of Applied Sciences", AMK, "Jyväskylä", [], [
        prog("Information and Communications Technology", "IT", BSC, tuition=10000, ielts="6.0"),
        prog("International Business", "Business", BSC, tuition=10000, ielts="6.0"),
    ]),
    ("Turku University of Applied Sciences", AMK, "Turku", [], [
        prog("Information and Communications Technology", "IT", BSC, tuition=11000, ielts="6.0"),
    ]),
    ("Tampere University of Applied Sciences", AMK, "Tampere", [], [
        prog("International Business", "Business", BSC, tuition=10000, ielts="6.0"),
    ]),
    ("LAB University of Applied Sciences", AMK, "Lahti", ["Lappeenranta"], [
        prog("Business Information Technology", "IT", BSC, tuition=9500, ielts="6.0"),
    ]),
    ("Oulu University of Applied Sciences", AMK, "Oulu", [], [
        prog("Information Technology", "IT", BSC, tuition=10000, ielts="6.0"),
    ]),
    ("Arcada University of Applied Sciences", AMK, "Helsinki", [], [
        prog("Information Technology", "IT", BSC, tuition=10000, ielts="6.0"),
    ]),
]


class Command(BaseCommand):
    help = "Seed real Finnish universities and English-taught programmes (autumn-2027 baseline)"

    def handle(self, *args, **options):
        unis = campuses = progs = 0
        for name, kind, city, extra_campuses, programmes in DATA:
            uni, created = University.objects.update_or_create(
                name=name,
                defaults={"institution_type": kind, "city": city, "is_active": True},
            )
            unis += created

            for campus_name in [f"{city} campus", *extra_campuses]:
                _, c_created = Campus.objects.update_or_create(
                    university=uni, name=campus_name,
                    defaults={"city": campus_name.replace(" campus", "") or city},
                )
                campuses += c_created

            for p in programmes:
                _, p_created = Program.objects.update_or_create(
                    university=uni, name=p["name"],
                    degree_level=p["degree_level"], intake=SEP,
                    defaults={
                        "field_of_study": p["field_of_study"],
                        "tuition_fee_eur": p["tuition_fee_eur"],
                        "min_ielts_score": p["min_ielts_score"],
                        "scholarship_available": p["scholarship_available"],
                        "scholarship_notes": "50–100% tuition waivers available (legally required).",
                        "acceptance_rate": p["acceptance_rate"],
                        "application_opens": OPENS,
                        "application_deadline": DEADLINE,
                        "start_date": STARTS,
                        "duration_years": 3 if p["degree_level"] == BSC else 2,
                        "language": "English",
                        "is_active": True,
                    },
                )
                progs += p_created

        self.stdout.write(self.style.SUCCESS(
            f"Seeded: {University.objects.count()} universities "
            f"({unis} new), {Campus.objects.count()} campuses, "
            f"{Program.objects.count()} programmes ({progs} new)."
        ))
        self.stdout.write(self.style.WARNING(
            "Tuition, dates and IELTS mins are autumn-2027 BASELINES — "
            "let the nightly scraper confirm/refresh them."
        ))
