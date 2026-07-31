from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import EntryForm
from .models import Batch, Entry


@login_required
def home(request):
    return render(request, "home.html", {"entries": Entry.objects.order_by('-date', '-id')})


@login_required
def batch(request):
    batches = Batch.objects.annotate(entry_count=Count('entries')).order_by('-created_at')
    return render(request, "batch.html", {"batches": batches})


@login_required
def batch_detail(request, slug):
    batch_obj = get_object_or_404(Batch, slug=slug)
    entries = batch_obj.entries.order_by('-date', '-id')
    return render(request, "batch_detail.html", {"batch": batch_obj, "entries": entries})


@login_required
def batch_edit(request, slug):
    batch_obj = get_object_or_404(Batch, slug=slug)

    if request.method == 'POST':
        action = request.POST.get('action')
        ids = request.POST.getlist('ids')

        if action == 'rename':
            name = request.POST.get('name', '').strip()
            if name:
                batch_obj.name = name
                batch_obj.save(update_fields=['name'])
                messages.success(request, "Batch name updated.")
            else:
                messages.error(request, "Batch name is required.")

        elif action == 'remove':
            entries_to_remove = Entry.objects.filter(pk__in=ids, batches=batch_obj)
            removed = entries_to_remove.count()
            batch_obj.entries.remove(*entries_to_remove)
            if removed:
                messages.success(request, f"Removed {removed} {'entry' if removed == 1 else 'entries'} from the batch.")

        elif action == 'add':
            entries_to_add = Entry.objects.filter(pk__in=ids).exclude(batches=batch_obj)
            added = entries_to_add.count()
            batch_obj.entries.add(*entries_to_add)
            if added:
                messages.success(request, f"Added {added} {'entry' if added == 1 else 'entries'} to the batch.")

        return redirect('batch_edit', slug=batch_obj.slug)

    grouped_entries = batch_obj.entries.order_by('-date', '-id')
    available_entries = Entry.objects.exclude(batches=batch_obj).order_by('-date', '-id')
    return render(request, "batch_edit.html", {
        "batch": batch_obj,
        "grouped_entries": grouped_entries,
        "available_entries": available_entries,
    })


@login_required
@require_POST
def delete_batch(request, slug):
    batch_obj = get_object_or_404(Batch, slug=slug)
    batch_obj.delete()
    return JsonResponse({'deleted': True})


@login_required
def edit_entry(request, pk):
    entry = get_object_or_404(Entry, pk=pk)

    if request.method == 'POST':
        form = EntryForm(request.POST, instance=entry)
        if form.is_valid():
            form.save()
            messages.success(request, f"Entry for {entry.vehicle_number} updated.")
            return redirect('home')
    else:
        form = EntryForm(instance=entry)

    return render(request, "edit_entry.html", {"form": form, "entry": entry})


@login_required
@require_POST
def delete_entries(request):
    ids = request.POST.getlist('ids')
    if not ids:
        return JsonResponse({'error': 'No ids provided.'}, status=400)
    deleted_count, _ = Entry.objects.filter(pk__in=ids).delete()
    return JsonResponse({'deleted': deleted_count})


@login_required
@require_POST
def create_batch(request):
    ids = request.POST.getlist('ids')
    name = request.POST.get('name', '').strip()

    if len(ids) < 2:
        return JsonResponse({'error': 'Select at least two entries to group.'}, status=400)
    if not name:
        return JsonResponse({'error': 'Batch name is required.'}, status=400)

    new_batch = Batch.objects.create(name=name)
    entries = Entry.objects.filter(pk__in=ids)
    new_batch.entries.add(*entries)
    return JsonResponse({'batch_id': new_batch.id, 'grouped': entries.count()})
