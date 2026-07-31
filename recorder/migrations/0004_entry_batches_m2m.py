from django.db import migrations, models


def copy_batch_fk_to_m2m(apps, schema_editor):
    Entry = apps.get_model('recorder', 'Entry')
    for entry in Entry.objects.exclude(batch__isnull=True):
        entry.batches_m2m_temp.add(entry.batch_id)


def copy_m2m_back_to_batch_fk(apps, schema_editor):
    Entry = apps.get_model('recorder', 'Entry')
    for entry in Entry.objects.all():
        first_batch = entry.batches_m2m_temp.first()
        if first_batch:
            entry.batch_id = first_batch.id
            entry.save(update_fields=['batch'])


class Migration(migrations.Migration):

    dependencies = [
        ('recorder', '0003_batch_slug'),
    ]

    operations = [
        migrations.AddField(
            model_name='entry',
            name='batches_m2m_temp',
            field=models.ManyToManyField(blank=True, related_name='entries_m2m_temp', to='recorder.batch'),
        ),
        migrations.RunPython(copy_batch_fk_to_m2m, copy_m2m_back_to_batch_fk),
        migrations.RemoveField(
            model_name='entry',
            name='batch',
        ),
        migrations.RenameField(
            model_name='entry',
            old_name='batches_m2m_temp',
            new_name='batches',
        ),
        migrations.AlterField(
            model_name='entry',
            name='batches',
            field=models.ManyToManyField(blank=True, related_name='entries', to='recorder.batch'),
        ),
    ]
