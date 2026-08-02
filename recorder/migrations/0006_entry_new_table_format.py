from django.db import migrations, models


class Migration(migrations.Migration):
    """
    Client (new table format) reshapes Entry's numeric columns from
    (Rolls, Workers, Net Kg) into (Loading/Roll, Net Kg for Loading/Roll,
    Weight/Roll, Net Kg for Weight/Roll, Workers). `rolls` and `net_kg`
    are renamed rather than dropped so existing data carries over;
    `weight_roll`/`net_kg_weight_roll` are genuinely new columns, backfilled
    to 0 on existing rows (preserve_default=False — there's no real "weight
    per roll" for old entries, and the form requires a value going forward).
    """

    dependencies = [
        ('recorder', '0005_alter_entry_date'),
    ]

    operations = [
        migrations.RenameField(
            model_name='entry',
            old_name='rolls',
            new_name='loading_roll',
        ),
        migrations.RenameField(
            model_name='entry',
            old_name='net_kg',
            new_name='net_kg_loading_roll',
        ),
        migrations.AlterField(
            model_name='entry',
            name='loading_roll',
            field=models.PositiveIntegerField(verbose_name='Loading/Roll'),
        ),
        migrations.AlterField(
            model_name='entry',
            name='net_kg_loading_roll',
            field=models.PositiveIntegerField(verbose_name='Net Kg (Loading/Roll)'),
        ),
        migrations.AddField(
            model_name='entry',
            name='weight_roll',
            field=models.PositiveIntegerField(default=0, verbose_name='Weight/Roll'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='entry',
            name='net_kg_weight_roll',
            field=models.PositiveIntegerField(default=0, verbose_name='Net Kg (Weight/Roll)'),
            preserve_default=False,
        ),
    ]
