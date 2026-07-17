"""Seed the official (English) websites of the Finnish HE institutions.

The catalog ships without websites, which silently hides every "visit the
university" affordance in the app (MatchDetail's Website button, the GATE
card's fallback link). Finnish institutional domains are stable enough to
curate here; rows that already have a website are never overwritten.

Usage: manage.py seed_university_websites
"""

from django.core.management.base import BaseCommand

from universities.models import University

WEBSITES = {
    "Aalto University": "https://www.aalto.fi/en",
    "Åbo Akademi University": "https://www.abo.fi/en/",
    "Arcada University of Applied Sciences": "https://www.arcada.fi/en",
    "Centria University of Applied Sciences": "https://net.centria.fi/en/",
    "Haaga-Helia University of Applied Sciences": "https://www.haaga-helia.fi/en",
    "Häme University of Applied Sciences": "https://www.hamk.fi/en/",
    "Hanken School of Economics": "https://www.hanken.fi/en",
    "Högskolan på Åland": "https://www.ha.ax/",
    "JAMK University of Applied Sciences": "https://www.jamk.fi/en",
    "Kajaani University of Applied Sciences": "https://www.kamk.fi/en",
    "Karelia University of Applied Sciences": "https://www.karelia.fi/en/",
    "LAB University of Applied Sciences": "https://lab.fi/en",
    "Lapland University of Applied Sciences": "https://www.lapinamk.fi/en",
    "Laurea University of Applied Sciences": "https://www.laurea.fi/en/",
    "LUT University": "https://www.lut.fi/en",
    "Metropolia University of Applied Sciences": "https://www.metropolia.fi/en",
    "Novia University of Applied Sciences": "https://www.novia.fi/",
    "Oulu University of Applied Sciences": "https://www.oamk.fi/en/",
    "Satakunta University of Applied Sciences SAMK": "https://www.samk.fi/en/",
    "Savonia University of Applied Sciences": "https://www.savonia.fi/en/",
    "South-Eastern Finland University of Applied Sciences Xamk": "https://www.xamk.fi/en/",
    "Tampere University": "https://www.tuni.fi/en",
    "Tampere University of Applied Sciences": "https://www.tuni.fi/en/about-us/tamk",
    "Turku University of Applied Sciences": "https://www.turkuamk.fi/en/",
    "University of Eastern Finland": "https://www.uef.fi/en",
    "University of Helsinki": "https://www.helsinki.fi/en",
    "University of Jyväskylä": "https://www.jyu.fi/en",
    "University of Lapland": "https://www.ulapland.fi/EN",
    "University of Oulu": "https://www.oulu.fi/en",
    "University of the Arts Helsinki": "https://www.uniarts.fi/en/",
    "University of Turku": "https://www.utu.fi/en",
    "University of Vaasa": "https://www.uwasa.fi/en",
    "Vaasa University of Applied Sciences": "https://www.vamk.fi/en/",
}


class Command(BaseCommand):
    help = "Fill University.website for known Finnish institutions (never overwrites)."

    def handle(self, *args, **options):
        updated = skipped = unknown = 0
        for uni in University.objects.all():
            url = WEBSITES.get(uni.name)
            if url is None:
                unknown += 1
                self.stdout.write(f"  – no known website for: {uni.name}")
                continue
            if uni.website:
                skipped += 1
                continue
            uni.website = url
            uni.save(update_fields=["website"])
            updated += 1
        self.stdout.write(
            self.style.SUCCESS(f"Websites set: {updated}, already set: {skipped}, unknown: {unknown}")
        )
