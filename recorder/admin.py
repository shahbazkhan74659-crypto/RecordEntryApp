from django.contrib import admin

from .models import Batch, Entry


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'vehicle_number', 'rolls', 'workers', 'net_kg', 'remark', 'batch_names')
    list_filter = ('date', 'batches')
    search_fields = ('vehicle_number', 'remark')

    def batch_names(self, obj):
        return ", ".join(b.name for b in obj.batches.all())
    batch_names.short_description = 'Batches'


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_at')
    search_fields = ('name',)
