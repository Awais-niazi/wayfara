"""Seed the curated knowledge base for the top Finnish research universities.

Adds only what the scraper can't produce: ranking + a short evergreen overview.
Rankings are QS World University Rankings 2026 (source cited), verified via
studyinfinland.fi. AMKs (universities of applied sciences) are intentionally
omitted — they are not research-ranked in QS/THE; their value is practice- and
employability-oriented, better expressed elsewhere.

`needs_review=False` reflects Awais's explicit sign-off on this editorial content.
`operational_verified` stays False: that stamp means a human has confirmed the
SCRAPED tuition/deadline/campus for the university, which is a separate manual
check to do in admin.
"""

from django.core.management.base import BaseCommand

from universities.models import University, UniversityProfile

QS_2026_SOURCE = "https://www.studyinfinland.fi/news-events/qs-world-university-rankings-2026"

# (DB university name, QS World 2026 rank, short evergreen overview)
PROFILES = [
    ("Aalto University", 114,
     "Finland's leading university for technology, business and design, formed "
     "from a 2010 merger of three institutions. The strongest choice for "
     "engineering, computer science and entrepreneurship, on the Otaniemi campus near Helsinki."),
    ("University of Helsinki", 116,
     "Finland's oldest (1640) and largest research university, with broad academic "
     "strength — especially the sciences, humanities, law and medicine."),
    ("University of Oulu", 342,
     "Northern Finland's main research university, known for information technology, "
     "wireless communications (historic Nokia links) and engineering."),
    ("University of Turku", 366,
     "A comprehensive research university in Finland's oldest city, strong in "
     "medicine, the natural sciences and technology."),
    ("LUT University", 397,
     "A technical university specialising in engineering and business, with a strong "
     "focus on energy, sustainability and clean technology; based in Lappeenranta."),
    ("Tampere University", 423,
     "A large multidisciplinary university (formed 2019) strong in technology, health "
     "sciences and society, in Finland's biggest inland city and a major student hub."),
    ("University of Jyväskylä", 498,
     "Known for education, sport sciences and IT, with a strong teaching reputation "
     "in central Finland."),
    ("University of Eastern Finland", 604,
     "Campuses in Joensuu and Kuopio; strengths in forestry, health sciences and photonics."),
    ("Åbo Akademi University", 643,
     "Finland's Swedish-language university, based in Turku, with notable strength in "
     "chemistry and materials science."),
]


class Command(BaseCommand):
    help = "Seed curated UniversityProfiles (QS 2026 rankings + overviews) for top universities"

    def handle(self, *args, **options):
        created = updated = skipped = 0
        for order, (name, qs_rank, overview) in enumerate(PROFILES, start=1):
            uni = University.objects.filter(name=name).first()
            if uni is None:
                self.stdout.write(self.style.WARNING(f"  skip (not in DB): {name}"))
                skipped += 1
                continue
            _, was_created = UniversityProfile.objects.update_or_create(
                university=uni,
                defaults={
                    "featured": True,
                    "sort_order": order,
                    "overview": overview,
                    "world_ranking": qs_rank,
                    "ranking_system": UniversityProfile.RankingSystem.QS,
                    "ranking_year": 2026,
                    "ranking_source_url": QS_2026_SOURCE,
                    "needs_review": False,          # Awais signed off on this content
                    # operational_verified left False — separate manual check of scraped figures
                },
            )
            created += was_created
            updated += not was_created

        self.stdout.write(self.style.SUCCESS(
            f"Profiles: {created} created, {updated} updated, {skipped} skipped."
        ))
        self.stdout.write(self.style.WARNING(
            "operational_verified is still False for all — tick it in admin once "
            "you've confirmed each university's scraped tuition/deadline/campus."
        ))
