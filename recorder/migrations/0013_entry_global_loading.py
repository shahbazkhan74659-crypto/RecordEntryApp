from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Client clarified the real workflow (via the app owner's father, who runs
    the three plants): rolls are packed/weighed separately at each plant,
    then physically mix together and get loaded onto the truck as one
    combined operation — there's no such thing as a per-plant loading
    count, only a single global one. Migration 0012_entry_multi_plant.py
    had folded loading_roll/net_kg_loading_roll/workers into "Plant 5"
    under the mistaken assumption loading was per-plant too; this migration
    renames them back to global, un-prefixed names. This also happens to
    restore their true original meaning, since the app's real historical
    `workers` data was always a loading-worker count, never plant-specific.

    Plant 5 then needs its own new `plant5_workers` field (packing workers
    at that plant) to replace the one just renamed away — added nullable
    with no default, since there's no historical data for it (same
    nullable pattern every other numeric field already uses). Plant 6 and
    Warp Plant's own loading fields (`plant6_loading_roll` etc.) are
    dropped entirely: they were always null (added nullable, never
    populated, since loading was never actually per-plant) and are no
    longer meaningful now that loading is modeled as global.
    """

    dependencies = [
        ('recorder', '0012_entry_multi_plant'),
    ]

    operations = [
        migrations.RenameField(model_name='entry', old_name='plant5_loading_roll', new_name='loading_roll'),
        migrations.RenameField(model_name='entry', old_name='plant5_net_kg_loading_roll', new_name='net_kg_loading_roll'),
        migrations.RenameField(model_name='entry', old_name='plant5_workers', new_name='workers'),
        migrations.AddField(
            model_name='entry',
            name='plant5_workers',
            field=models.PositiveIntegerField(verbose_name='Workers', null=True, blank=True),
        ),
        migrations.RemoveField(model_name='entry', name='plant6_loading_roll'),
        migrations.RemoveField(model_name='entry', name='plant6_net_kg_loading_roll'),
        migrations.RemoveField(model_name='entry', name='warp_loading_roll'),
        migrations.RemoveField(model_name='entry', name='warp_net_kg_loading_roll'),
    ]
