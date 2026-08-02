import random
import string
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from recorder.models import Entry

TOTAL_RECORDS = 1000
DAYS_SPAN = 365
BATCH_SIZE = 500

STATE_CODES = [
    'MH', 'DL', 'KA', 'GJ', 'RJ', 'UP', 'TN', 'PB', 'HR', 'MP',
    'WB', 'AP', 'TS', 'KL', 'OR', 'BR', 'CG', 'JH', 'UK', 'HP',
    'CH', 'GA', 'AS', 'JK',
]

REMARKS = [
    '', '', '', '', '',
    'Loaded ahead of schedule.',
    'Driver requested early morning slot.',
    'Recheck weight next time, seemed off.',
    'Double trip day, watch worker fatigue.',
    'Small load, priority customer.',
    'Rolls slightly damp, noted for QC.',
    'Regular vendor, no issues.',
    'Delayed due to weather.',
    'Weighbridge recalibrated before this entry.',
    'Customer requested extra padding.',
]


def random_vehicle_number():
    state = random.choice(STATE_CODES)
    rto = random.randint(1, 99)
    series = ''.join(random.choices(string.ascii_uppercase, k=random.randint(1, 3)))
    number = random.randint(1, 9999)
    return f"{state}{rto}{series}{number:04d}"


def build_entry(date):
    loading_roll = random.randint(40, 220)
    per_roll_kg = random.randint(60, 75)
    net_kg_loading_roll = int(loading_roll * per_roll_kg * random.uniform(0.97, 1.03))

    weight_roll = random.randint(55, 80)
    net_kg_weight_roll = int(loading_roll * weight_roll * random.uniform(0.97, 1.03))

    return Entry(
        date=date,
        vehicle_number=random_vehicle_number(),
        loading_roll=loading_roll,
        net_kg_loading_roll=net_kg_loading_roll,
        weight_roll=weight_roll,
        net_kg_weight_roll=net_kg_weight_roll,
        workers=random.randint(2, 8),
        remark=random.choice(REMARKS),
    )


class Command(BaseCommand):
    help = "Seed the database with sample Truck Loading Entry records."

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=TOTAL_RECORDS, help='Number of entries to seed.')

    def handle(self, *args, **options):
        count = options['count']
        today = timezone.localdate()
        entries = [
            build_entry(today - timedelta(days=random.randint(0, DAYS_SPAN)))
            for _ in range(count)
        ]
        Entry.objects.bulk_create(entries, batch_size=BATCH_SIZE)
        self.stdout.write(self.style.SUCCESS(f"Seeded {len(entries)} entries."))
