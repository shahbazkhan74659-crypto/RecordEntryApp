from django.core.validators import MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Client (multi-plant table) reshapes Entry's single 5-column numeric
    group into three repeated groups — Plant 5, Plant 6, Warp Plant — since
    a single truck/date/vehicle entry now records all three plants' numbers
    on one row (per the client's hand-drawn paper ledger). The existing 5
    fields are renamed (RenameField, not dropped) into the "plant5_" group
    so the app's existing production rows carry their real history forward
    unchanged; `workers` additionally gets an explicit verbose_name here
    since (unlike the other 4) it never had one, and would otherwise
    auto-derive an ugly "Plant5 workers" label post-rename. Plant 6 and
    Warp Plant's 10 fields are genuinely new, added nullable with no
    default — there is no real historical data for them, matching the
    already-nullable pattern every existing numeric field already uses
    (rendered as "—" in the UI when null). No index/unique-constraint
    operations are added here, so this migration isn't exposed to the
    Postgres `_like`-opclass-index collision documented in
    0003_batch_slug.py.
    """

    dependencies = [
        ('recorder', '0011_alter_entry_loading_roll_and_more'),
    ]

    operations = [
        migrations.RenameField(model_name='entry', old_name='loading_roll', new_name='plant5_loading_roll'),
        migrations.RenameField(model_name='entry', old_name='net_kg_loading_roll', new_name='plant5_net_kg_loading_roll'),
        migrations.RenameField(model_name='entry', old_name='weight_roll', new_name='plant5_weight_roll'),
        migrations.RenameField(model_name='entry', old_name='net_kg_weight_roll', new_name='plant5_net_kg_weight_roll'),
        migrations.RenameField(model_name='entry', old_name='workers', new_name='plant5_workers'),
        migrations.AlterField(
            model_name='entry',
            name='plant5_workers',
            field=models.PositiveIntegerField(verbose_name='Workers', null=True, blank=True),
        ),
        migrations.AddField(
            model_name='entry',
            name='plant6_loading_roll',
            field=models.DecimalField(
                verbose_name='Loading/Roll', max_digits=10, decimal_places=2,
                null=True, blank=True, validators=[MinValueValidator(0)],
            ),
        ),
        migrations.AddField(
            model_name='entry',
            name='plant6_net_kg_loading_roll',
            field=models.DecimalField(
                verbose_name='Net Kg (Loading/Roll)', max_digits=10, decimal_places=2,
                null=True, blank=True, validators=[MinValueValidator(0)],
            ),
        ),
        migrations.AddField(
            model_name='entry',
            name='plant6_weight_roll',
            field=models.DecimalField(
                verbose_name='Weight/Roll', max_digits=10, decimal_places=2,
                null=True, blank=True, validators=[MinValueValidator(0)],
            ),
        ),
        migrations.AddField(
            model_name='entry',
            name='plant6_net_kg_weight_roll',
            field=models.DecimalField(
                verbose_name='Net Kg (Weight/Roll)', max_digits=10, decimal_places=2,
                null=True, blank=True, validators=[MinValueValidator(0)],
            ),
        ),
        migrations.AddField(
            model_name='entry',
            name='plant6_workers',
            field=models.PositiveIntegerField(verbose_name='Workers', null=True, blank=True),
        ),
        migrations.AddField(
            model_name='entry',
            name='warp_loading_roll',
            field=models.DecimalField(
                verbose_name='Loading/Roll', max_digits=10, decimal_places=2,
                null=True, blank=True, validators=[MinValueValidator(0)],
            ),
        ),
        migrations.AddField(
            model_name='entry',
            name='warp_net_kg_loading_roll',
            field=models.DecimalField(
                verbose_name='Net Kg (Loading/Roll)', max_digits=10, decimal_places=2,
                null=True, blank=True, validators=[MinValueValidator(0)],
            ),
        ),
        migrations.AddField(
            model_name='entry',
            name='warp_weight_roll',
            field=models.DecimalField(
                verbose_name='Weight/Roll', max_digits=10, decimal_places=2,
                null=True, blank=True, validators=[MinValueValidator(0)],
            ),
        ),
        migrations.AddField(
            model_name='entry',
            name='warp_net_kg_weight_roll',
            field=models.DecimalField(
                verbose_name='Net Kg (Weight/Roll)', max_digits=10, decimal_places=2,
                null=True, blank=True, validators=[MinValueValidator(0)],
            ),
        ),
        migrations.AddField(
            model_name='entry',
            name='warp_workers',
            field=models.PositiveIntegerField(verbose_name='Workers', null=True, blank=True),
        ),
    ]
