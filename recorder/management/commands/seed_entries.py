from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from recorder.models import Entry

SEED_DATA = [
    {"vehicle_number": "MH12AB1234", "loading_roll": 120, "net_kg_loading_roll": 8500, "weight_roll": 71, "net_kg_weight_roll": 8520, "workers": 4, "remark": "Loaded ahead of schedule."},
    {"vehicle_number": "DL1CAB5678", "loading_roll": 95, "net_kg_loading_roll": 6200, "weight_roll": 65, "net_kg_weight_roll": 6175, "workers": 3, "remark": ""},
    {"vehicle_number": "KA05MH4321", "loading_roll": 150, "net_kg_loading_roll": 10250, "weight_roll": 68, "net_kg_weight_roll": 10200, "workers": 5, "remark": "Driver requested early morning slot."},
    {"vehicle_number": "GJ01XY9988", "loading_roll": 80, "net_kg_loading_roll": 5400, "weight_roll": 68, "net_kg_weight_roll": 5440, "workers": 3, "remark": "Recheck weight next time, seemed off."},
    {"vehicle_number": "RJ14PQ4567", "loading_roll": 110, "net_kg_loading_roll": 7800, "weight_roll": 71, "net_kg_weight_roll": 7810, "workers": 4, "remark": ""},
    {"vehicle_number": "UP32LM7890", "loading_roll": 200, "net_kg_loading_roll": 13400, "weight_roll": 67, "net_kg_weight_roll": 13400, "workers": 6, "remark": "Double trip day, watch worker fatigue."},
    {"vehicle_number": "TN09KJ3456", "loading_roll": 60, "net_kg_loading_roll": 3900, "weight_roll": 65, "net_kg_weight_roll": 3900, "workers": 2, "remark": "Small load, priority customer."},
    {"vehicle_number": "PB03RS6712", "loading_roll": 135, "net_kg_loading_roll": 9100, "weight_roll": 67, "net_kg_weight_roll": 9045, "workers": 4, "remark": ""},
    {"vehicle_number": "HR26TU2345", "loading_roll": 175, "net_kg_loading_roll": 11800, "weight_roll": 67, "net_kg_weight_roll": 11725, "workers": 5, "remark": "Rolls slightly damp, noted for QC."},
    {"vehicle_number": "MP09VW8901", "loading_roll": 90, "net_kg_loading_roll": 6000, "weight_roll": 67, "net_kg_weight_roll": 6030, "workers": 3, "remark": "Regular vendor, no issues."},
]


class Command(BaseCommand):
    help = "Seed the database with sample Truck Loading Entry records."

    def handle(self, *args, **options):
        today = timezone.localdate()
        for offset, data in enumerate(SEED_DATA):
            Entry.objects.create(date=today - timedelta(days=offset), **data)
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(SEED_DATA)} entries."))
