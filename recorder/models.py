from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import F, Window
from django.db.models.functions import RowNumber
from django.utils import timezone
from django.utils.text import slugify


class Batch(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=140, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Batches"
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or 'batch'
            slug = base_slug
            counter = 2
            while Batch.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)


class Entry(models.Model):
    date = models.DateField(default=timezone.localdate)
    vehicle_number = models.CharField(max_length=150, null=True, blank=True)
    loading_roll = models.DecimalField(
        verbose_name='Loading/Roll', max_digits=10, decimal_places=2,
        null=True, blank=True, validators=[MinValueValidator(0)],
    )
    net_kg_loading_roll = models.DecimalField(
        verbose_name='Net Kg (Loading/Roll)', max_digits=10, decimal_places=2,
        null=True, blank=True, validators=[MinValueValidator(0)],
    )
    weight_roll = models.DecimalField(
        verbose_name='Weight/Roll', max_digits=10, decimal_places=2,
        null=True, blank=True, validators=[MinValueValidator(0)],
    )
    net_kg_weight_roll = models.DecimalField(
        verbose_name='Net Kg (Weight/Roll)', max_digits=10, decimal_places=2,
        null=True, blank=True, validators=[MinValueValidator(0)],
    )
    workers = models.PositiveIntegerField(null=True, blank=True)
    remark = models.TextField(blank=True, null=True)
    batches = models.ManyToManyField(Batch, blank=True, related_name='entries')

    class Meta:
        verbose_name_plural = "Entries"
        ordering = ['-date', '-id']

    def __str__(self):
        return f"{self.vehicle_number} — {self.date}"

    def save(self, *args, **kwargs):
        if self.vehicle_number:
            self.vehicle_number = self.vehicle_number.upper()
        super().save(*args, **kwargs)


def entries_with_serial_number():
    """The full, unfiltered Entry queryset annotated with each row's stable,
    global serial_number (rank by creation order, ascending id) — the same
    real S.No the home page's own table and the PDF export show. Single
    shared source for this query, used by recorder.views (home,
    download_entries_pdf) and recorder.tests. Must always be computed over
    the *entire* table before any further .filter()/slicing: Window() ranks
    against whatever rows survive the SQL WHERE clause, which runs before
    window functions do, so annotating after a .filter() would rank only
    within the filtered subset instead of each entry's real, global
    serial number."""
    return Entry.objects.annotate(
        serial_number=Window(expression=RowNumber(), order_by=F('id').asc())
    )
