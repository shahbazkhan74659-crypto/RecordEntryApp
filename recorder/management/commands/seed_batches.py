import random

from django.core.management.base import BaseCommand

from recorder.models import Batch, Entry

TOTAL_BATCHES = 100

# Realistic-ish batch names (the client's own real usage: grouping by
# dispatch run, by customer, or by a plant/day label) -- combined with a
# random suffix below so 100 runs don't collide into a handful of names,
# though Batch.save()'s own slug dedupe would handle that regardless.
NAME_PREFIXES = [
    'Morning Dispatch', 'Evening Dispatch', 'Night Dispatch',
    'Customer Order', 'Priority Load', 'Weekly Consignment',
    'Plant 5 Batch', 'Plant 6 Batch', 'Warp Plant Batch',
    'Export Shipment', 'Local Delivery', 'Bulk Order',
]

MIN_ENTRIES_PER_BATCH = 2
MAX_ENTRIES_PER_BATCH = 12


class Command(BaseCommand):
    help = "Seed the database with sample Batches, grouping random existing entries."

    def add_arguments(self, parser):
        parser.add_argument('--count', type=int, default=TOTAL_BATCHES, help='Number of batches to seed.')

    def handle(self, *args, **options):
        count = options['count']
        entry_ids = list(Entry.objects.values_list('id', flat=True))

        if len(entry_ids) < MIN_ENTRIES_PER_BATCH:
            self.stdout.write(self.style.ERROR(
                f"Need at least {MIN_ENTRIES_PER_BATCH} entries to seed batches "
                f"(found {len(entry_ids)}). Run seed_entries first."
            ))
            return

        max_per_batch = min(MAX_ENTRIES_PER_BATCH, len(entry_ids))
        created = 0
        for i in range(count):
            name = f"{random.choice(NAME_PREFIXES)} #{i + 1}"
            batch = Batch.objects.create(name=name)
            sample_size = random.randint(MIN_ENTRIES_PER_BATCH, max_per_batch)
            batch.entries.add(*random.sample(entry_ids, sample_size))
            created += 1

        self.stdout.write(self.style.SUCCESS(f"Seeded {created} batches from {len(entry_ids)} existing entries."))
