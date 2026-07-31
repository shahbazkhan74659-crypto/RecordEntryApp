from django.core.validators import RegexValidator
from django.db import models
from django.utils import timezone
from django.utils.text import slugify

vehicle_number_validator = RegexValidator(
    regex=r'^(?i:[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{4})$',
    message="Enter a valid vehicle number, e.g. MH12AB1234.",
)


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
    vehicle_number = models.CharField(max_length=15, validators=[vehicle_number_validator])
    rolls = models.PositiveIntegerField()
    workers = models.PositiveIntegerField()
    net_kg = models.PositiveIntegerField()
    remark = models.TextField(blank=True, default='')
    batches = models.ManyToManyField(Batch, blank=True, related_name='entries')

    class Meta:
        verbose_name_plural = "Entries"
        ordering = ['-date', '-id']

    def __str__(self):
        return f"{self.vehicle_number} — {self.date}"

    def save(self, *args, **kwargs):
        self.vehicle_number = self.vehicle_number.upper()
        super().save(*args, **kwargs)
