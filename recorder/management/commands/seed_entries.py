from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from recorder.models import Entry

SEED_DATA = [
    {"vehicle_number": "MH12AB1234", "rolls": 120, "workers": 4, "net_kg": 8500, "remark": "Loaded ahead of schedule."},
    {"vehicle_number": "DL1CAB5678", "rolls": 95, "workers": 3, "net_kg": 6200, "remark": ""},
    {"vehicle_number": "KA05MH4321", "rolls": 150, "workers": 5, "net_kg": 10250, "remark": "Driver requested early morning slot."},
    {"vehicle_number": "GJ01XY9988", "rolls": 80, "workers": 3, "net_kg": 5400, "remark": "Recheck weight next time, seemed off."},
    {"vehicle_number": "RJ14PQ4567", "rolls": 110, "workers": 4, "net_kg": 7800, "remark": ""},
    {"vehicle_number": "UP32LM7890", "rolls": 200, "workers": 6, "net_kg": 13400, "remark": "Double trip day, watch worker fatigue."},
    {"vehicle_number": "TN09KJ3456", "rolls": 60, "workers": 2, "net_kg": 3900, "remark": "Small load, priority customer."},
    {"vehicle_number": "PB03RS6712", "rolls": 135, "workers": 4, "net_kg": 9100, "remark": ""},
    {"vehicle_number": "HR26TU2345", "rolls": 175, "workers": 5, "net_kg": 11800, "remark": "Rolls slightly damp, noted for QC."},
    {"vehicle_number": "MP09VW8901", "rolls": 90, "workers": 3, "net_kg": 6000, "remark": "Regular vendor, no issues."},
]


class Command(BaseCommand):
    help = "Seed the database with sample Truck Loading Entry records."

    def handle(self, *args, **options):
        today = timezone.localdate()
        for offset, data in enumerate(SEED_DATA):
            Entry.objects.create(date=today - timedelta(days=offset), **data)
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(SEED_DATA)} entries."))
