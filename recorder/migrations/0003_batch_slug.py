from django.db import migrations, models
from django.utils.text import slugify


def generate_slugs(apps, schema_editor):
    Batch = apps.get_model('recorder', 'Batch')
    for batch in Batch.objects.all():
        base_slug = slugify(batch.name) or 'batch'
        slug = base_slug
        counter = 2
        while Batch.objects.filter(slug=slug).exclude(pk=batch.pk).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1
        batch.slug = slug
        batch.save(update_fields=['slug'])


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('recorder', '0002_batch_entry_batch'),
    ]

    operations = [
        migrations.AddField(
            model_name='batch',
            name='slug',
            # db_index=False here: SlugField defaults db_index=True, which on
            # PostgreSQL creates both a plain btree index and a "_like"
            # opclass index at this step — then the AlterField below (which
            # adds unique=True, itself index-backed) tries to create an
            # index with the same deterministic name and fails with
            # "relation ... _like already exists". SQLite has no such
            # opclass index, so this never surfaced there. Explicitly
            # unindexed here since the field is about to become unique
            # anyway; the final schema (unique index) is unchanged.
            field=models.SlugField(blank=True, default='', max_length=140, db_index=False),
            preserve_default=False,
        ),
        migrations.RunPython(generate_slugs, noop),
        migrations.AlterField(
            model_name='batch',
            name='slug',
            field=models.SlugField(blank=True, max_length=140, unique=True),
        ),
    ]
