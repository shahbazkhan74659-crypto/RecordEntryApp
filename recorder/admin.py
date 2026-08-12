from django.contrib import admin

from .models import Batch, Entry


@admin.register(Entry)
class EntryAdmin(admin.ModelAdmin):
    # 12 raw numeric columns would be unusable in the changelist grid, so
    # only the identifying columns show there; the full breakdown is
    # grouped into fieldsets on the change form instead (see below) --
    # necessary since plant5_workers/plant6_workers/warp_workers etc. all
    # share the same bare verbose_name ('Workers') and would otherwise be
    # indistinguishable without their surrounding group.
    list_display = ('id', 'date', 'vehicle_number', 'remark', 'batch_names')
    list_filter = ('date', 'batches')
    search_fields = ('vehicle_number', 'remark')
    fieldsets = (
        (None, {'fields': ('date', 'vehicle_number')}),
        ('Loading', {'fields': ('loading_roll', 'net_kg_loading_roll', 'workers')}),
        ('Plant 5', {'fields': ('plant5_weight_roll', 'plant5_net_kg_weight_roll', 'plant5_workers')}),
        ('Plant 6', {'fields': ('plant6_weight_roll', 'plant6_net_kg_weight_roll', 'plant6_workers')}),
        ('Warp Plant', {'fields': ('warp_weight_roll', 'warp_net_kg_weight_roll', 'warp_workers')}),
        (None, {'fields': ('remark', 'batches')}),
    )

    def batch_names(self, obj):
        return ", ".join(b.name for b in obj.batches.all())
    batch_names.short_description = 'Batches'


@admin.register(Batch)
class BatchAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'created_at')
    search_fields = ('name',)
