"""
Generate plausible Sri Lankan cell tower locations for map visualization.
Uses the serving cell IDs and neighbor IDs from CellModel + demo data,
distributing them across the Colombo metro / Western Province area.
"""

import random
from django.core.management.base import BaseCommand
from detection.models import CellModel, CellLocation

SRI_LANKA_REGIONS = [
    {"name": "Colombo Fort",      "lat": 6.9340, "lon": 79.8428, "radius": 0.015},
    {"name": "Colombo 07",        "lat": 6.9147, "lon": 79.8634, "radius": 0.012},
    {"name": "Bambalapitiya",     "lat": 6.8883, "lon": 79.8570, "radius": 0.010},
    {"name": "Dehiwala",          "lat": 6.8566, "lon": 79.8632, "radius": 0.012},
    {"name": "Mount Lavinia",     "lat": 6.8390, "lon": 79.8660, "radius": 0.010},
    {"name": "Nugegoda",          "lat": 6.8725, "lon": 79.8874, "radius": 0.012},
    {"name": "Rajagiriya",        "lat": 6.9070, "lon": 79.8920, "radius": 0.010},
    {"name": "Battaramulla",      "lat": 6.8980, "lon": 79.9180, "radius": 0.012},
    {"name": "Malabe",            "lat": 6.9020, "lon": 79.9560, "radius": 0.015},
    {"name": "Kaduwela",          "lat": 6.9320, "lon": 79.9830, "radius": 0.012},
    {"name": "Kottawa",           "lat": 6.8430, "lon": 79.9610, "radius": 0.012},
    {"name": "Maharagama",        "lat": 6.8470, "lon": 79.9260, "radius": 0.010},
    {"name": "Borella",           "lat": 6.9230, "lon": 79.8770, "radius": 0.008},
    {"name": "Maradana",          "lat": 6.9290, "lon": 79.8620, "radius": 0.008},
    {"name": "Pettah",            "lat": 6.9400, "lon": 79.8500, "radius": 0.008},
    {"name": "Wellawatte",        "lat": 6.8740, "lon": 79.8600, "radius": 0.008},
    {"name": "Kirulapone",        "lat": 6.8780, "lon": 79.8750, "radius": 0.008},
    {"name": "Narahenpita",       "lat": 6.8990, "lon": 79.8770, "radius": 0.008},
    {"name": "Pelawatte",         "lat": 6.8870, "lon": 79.9300, "radius": 0.010},
    {"name": "Thalawathugoda",    "lat": 6.8720, "lon": 79.9420, "radius": 0.010},
]

BANDS = ["B1 (2100)", "B3 (1800)", "B7 (2600)", "B28 (700)", "n78 (3500)"]


class Command(BaseCommand):
    help = "Generate plausible Sri Lankan coordinates for cell towers"

    def add_arguments(self, parser):
        parser.add_argument("--clear", action="store_true", help="Clear existing locations first")

    def handle(self, *args, **options):
        if options["clear"]:
            CellLocation.objects.all().delete()
            self.stdout.write("Cleared existing cell locations.")

        all_cell_ids = set()

        for cm in CellModel.objects.all():
            all_cell_ids.add(cm.serving_cell_id)
            if cm.neighbor_order:
                all_cell_ids.update(cm.neighbor_order)

        from detection.models import SuspiciousNeighbor
        for sn in SuspiciousNeighbor.objects.all():
            all_cell_ids.add(sn.neighbor_id)

        existing = set(CellLocation.objects.values_list("global_cell_id", flat=True))
        new_ids = all_cell_ids - existing

        if not new_ids:
            self.stdout.write("No new cell IDs to create locations for.")
            return

        created = 0
        cell_list = sorted(new_ids)
        regions = SRI_LANKA_REGIONS.copy()

        for i, cell_id in enumerate(cell_list):
            region = regions[i % len(regions)]
            lat = region["lat"] + random.uniform(-region["radius"], region["radius"])
            lon = region["lon"] + random.uniform(-region["radius"], region["radius"])

            is_fbs = cell_id.startswith("99999") or cell_id.startswith("88888")
            tech = "LTE"
            band = random.choice(BANDS[:4])
            name = f"{region['name']} Site {cell_id.split('_')[-1]}"

            if is_fbs:
                name = f"Unknown Site {cell_id.split('_')[-1]}"
                band = ""

            CellLocation.objects.update_or_create(
                global_cell_id=cell_id,
                defaults={
                    "cell_name": name,
                    "latitude": round(lat, 6),
                    "longitude": round(lon, 6),
                    "technology": tech,
                    "band": band,
                },
            )
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Created {created} cell locations across {len(regions)} regions."))
