import logging
import secrets
from datetime import date as date_cls
from decimal import Decimal
from io import BytesIO
from urllib.parse import urlencode
from xml.sax.saxutils import escape as xml_escape

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.contrib.auth.models import User
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db.models import Count
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .forms import EntryForm
from .models import Batch, Entry, entries_with_serial_number

logger = logging.getLogger(__name__)

OTP_TTL_SECONDS = 5 * 60
OTP_RESEND_COOLDOWN_SECONDS = 60
OTP_MAX_ATTEMPTS = 5
EMAIL_REVERT_TTL_SECONDS = 30 * 60
RESET_TOKEN_TTL_SECONDS = 10 * 60

# check_username (unauthenticated, pre-login) has no per-account cache key
# available yet -- that's what it's used to discover -- so it's throttled
# per-IP instead, same cache-backed attempt-cap style as the OTP flows below.
CHECK_USERNAME_MAX_ATTEMPTS = 20
CHECK_USERNAME_ATTEMPTS_TTL_SECONDS = 5 * 60

# Throttles wrong-email guesses against a known username on
# forgot_password_request_otp, the same way OTP_MAX_ATTEMPTS already
# throttles OTP guesses -- keyed by user.pk once a real user is resolved.
FORGOT_PASSWORD_EMAIL_MAX_ATTEMPTS = 5
FORGOT_PASSWORD_EMAIL_ATTEMPTS_TTL_SECONDS = 10 * 60

# Basic lockout for Django's built-in LoginView (see ThrottledLoginView
# below) -- this project has no django-axes or similar, so this is a
# minimal cache-backed attempt cap in the same style as the OTP flows.
LOGIN_MAX_ATTEMPTS = 5
LOGIN_LOCKOUT_SECONDS = 15 * 60



def _fmt_pdf_number(value, suffix=''):
    """Renders an optional numeric Entry field for the PDF table: '—' when
    left blank (None), otherwise the value with the given unit suffix."""
    return '—' if value is None else f'{value}{suffix}'


def _serial_by_id():
    """id -> real, global serial_number lookup, built from
    entries_with_serial_number() (models.py). Shared by home() and
    download_entries_pdf(): both need to look up an already-fetched
    entry's real S.No by id rather than annotating their own (possibly
    filtered) queryset directly — see entries_with_serial_number()'s
    docstring for why."""
    return dict(entries_with_serial_number().values_list('id', 'serial_number'))


def _digit_ids(request):
    """Shared by delete_entries, create_batch, download_entries_pdf
    ('choose' scope), and batch_edit: parses the repeated 'ids' POST field
    into a list of numeric-only id strings, silently dropping anything
    non-digit rather than raising."""
    return [i for i in request.POST.getlist('ids') if i.isdigit()]


def _send_otp_email(otp_key, cooldown_key, cache_payload, recipient_email, subject):
    """
    Shared by change_email_request_otp and forgot_password_request_otp:
    enforces the resend cooldown, generates a 6-digit OTP, caches it (merged
    with `cache_payload` — e.g. the email flow's extra 'email' field, which
    the password flow doesn't have) under `otp_key`, sets the cooldown, and
    emails the code. Returns an error JsonResponse to return immediately, or
    None if the email was sent successfully.
    """
    if cache.get(cooldown_key):
        return JsonResponse({'error': 'Please wait a minute before requesting another code.'}, status=429)

    otp = f'{secrets.randbelow(1_000_000):06d}'
    cache.set(otp_key, {**cache_payload, 'otp': otp, 'attempts': 0}, OTP_TTL_SECONDS)
    cache.set(cooldown_key, True, OTP_RESEND_COOLDOWN_SECONDS)

    try:
        send_mail(
            subject,
            f'Your verification code is {otp}. It expires in 5 minutes.',
            settings.DEFAULT_FROM_EMAIL,
            [recipient_email],
            fail_silently=False,
        )
    except Exception:
        # Swallowed otherwise -- logged so the real cause (auth failure,
        # connection timeout, blocked port, etc.) shows up in server logs
        # instead of vanishing behind this generic user-facing message.
        logger.exception('Failed to send OTP email to %s', recipient_email)
        return JsonResponse(
            {'error': 'Could not send the verification email. Check the SENDGRID_API_KEY setting in .env.'}, status=500,
        )

    return None


def _check_otp(otp_key, is_mismatch):
    """
    Shared by change_email_verify and forgot_password_verify_otp: looks up
    `otp_key` in cache, returns an error JsonResponse if it's expired/missing.
    Otherwise calls `is_mismatch(entry)` — the two callers compare different
    things (email+otp vs otp only) — and on a mismatch increments the attempt
    count, capping at OTP_MAX_ATTEMPTS (deleting the entry so it can't be
    replayed) same as before. Returns (error_response, entry): error_response
    is None and entry is the (now cache-cleared) cached dict on success.
    """
    entry = cache.get(otp_key)
    if entry is None:
        return JsonResponse({'error': 'This code has expired. Please request a new one.'}, status=400), None

    if is_mismatch(entry):
        entry['attempts'] += 1
        if entry['attempts'] >= OTP_MAX_ATTEMPTS:
            cache.delete(otp_key)
            return JsonResponse({'error': 'Too many incorrect attempts. Please request a new code.'}, status=400), None
        cache.set(otp_key, entry, OTP_TTL_SECONDS)
        return JsonResponse({'error': 'Incorrect code.'}, status=400), None

    cache.delete(otp_key)
    return None, entry


class ThrottledLoginView(auth_views.LoginView):
    """Wraps Django's stock LoginView with a minimal cache-backed lockout
    (LOGIN_MAX_ATTEMPTS within LOGIN_LOCKOUT_SECONDS) — this project has no
    django-axes or similar, so this follows the same cache cooldown/
    attempt-cap style already used throughout this file for the OTP flows.
    Keyed by the submitted username (lowercased, matching this app's
    __iexact convention elsewhere) rather than IP: a shared IP (e.g. NAT)
    shouldn't lock out every user behind it, and there's only ever one real
    account here to protect regardless.
    """

    @staticmethod
    def _attempts_key(username):
        return f'login_attempts:{username.strip().lower()}'

    def post(self, request, *args, **kwargs):
        username = request.POST.get('username', '')
        if username:
            key = self._attempts_key(username)
            if cache.get(key, 0) >= LOGIN_MAX_ATTEMPTS:
                form = self.get_form()
                form.add_error(None, 'Too many failed login attempts. Please try again in a few minutes.')
                return self.render_to_response(self.get_context_data(form=form))
        return super().post(request, *args, **kwargs)

    def form_invalid(self, form):
        username = self.request.POST.get('username', '')
        if username:
            key = self._attempts_key(username)
            cache.set(key, cache.get(key, 0) + 1, LOGIN_LOCKOUT_SECONDS)
        return super().form_invalid(form)

    def form_valid(self, form):
        username = self.request.POST.get('username', '')
        if username:
            cache.delete(self._attempts_key(username))
        return super().form_valid(form)


HOME_PAGE_SIZE = 30


@login_required
def home(request):
    current_search = request.GET.get('q', '').strip()

    current_date = request.GET.get('date', '').strip()
    if current_date:
        try:
            date_cls.fromisoformat(current_date)
        except ValueError:
            current_date = ''  # malformed/tampered query param, ignore rather than 500

    # The page to return to when the "All" filter-clear button is clicked —
    # captured once (client-side, in home.js) at the moment a filter is
    # first applied, then carried forward through every subsequent
    # date/search/pagination link for the rest of that filtered session.
    # Never used in a query, purely echoed back into pagination link hrefs
    # below, so a non-digit value is just dropped rather than validated
    # further (Paginator.get_page() already falls back to page 1 for a
    # bogus/out-of-range page number on its own).
    return_page = request.GET.get('return_page', '').strip()
    if not return_page.isdigit():
        return_page = ''

    # Display order is "-id" (newest created first) rather than "-date, -id"
    # — sorting by date first breaks a monotonic descending S.No the moment
    # two entries share a date, since same-date rows would then interleave
    # by id in a way that doesn't match their serial_number order
    # top-to-bottom (see serial_number backfill below).
    qs = Entry.objects.order_by('-id')
    if current_date:
        qs = qs.filter(date=current_date)
    if current_search:
        qs = qs.filter(vehicle_number__icontains=current_search)

    paginator = Paginator(qs, HOME_PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get('page'))

    # serial_number is each entry's stable rank by creation order (ascending
    # id) — the same real, global S.No the PDF export uses (see
    # download_entries_pdf's use of the same _serial_by_id() helper).
    # Backfilled onto just this page's ~25 already-fetched rows via a fresh,
    # *unfiltered* ranking rather than annotating the filtered/paginated
    # queryset directly: Window(RowNumber()) ranks against whatever rows
    # survive the SQL WHERE clause, which runs before window functions do,
    # so annotating after a date/search .filter() would rank only within the
    # filtered subset instead of each entry's real, global serial number.
    serial_by_id = _serial_by_id()
    for entry in page_obj.object_list:
        entry.serial_number = serial_by_id[entry.id]

    entry_count = Entry.objects.count()
    empty_message = 'No matching entries.' if (current_date or current_search) else 'No entries yet.'

    # Shared query-string suffix (everything but "page") for the First/Prev/
    # Next/Last pagination links below, built once here rather than repeated
    # inline in the template 4x — each link just does "?page=N{{ pagination_qs }}".
    extra_params = {}
    if current_date:
        extra_params['date'] = current_date
    if current_search:
        extra_params['q'] = current_search
    if return_page:
        extra_params['return_page'] = return_page
    pagination_qs = ('&' + urlencode(extra_params)) if extra_params else ''

    return render(request, "home.html", {
        "entries": page_obj.object_list,
        "page_obj": page_obj,
        "current_date": current_date,
        "current_search": current_search,
        "return_page": return_page,
        "entry_count": entry_count,
        "empty_message": empty_message,
        "pagination_qs": pagination_qs,
    })


BATCH_PAGE_SIZE = 40  # 10 rows x 4 cards/row (the grid's default column count)


@login_required
def batch(request):
    current_search = request.GET.get('q', '').strip()

    batches = Batch.objects.annotate(entry_count=Count('entries')).order_by('-created_at')
    if current_search:
        batches = batches.filter(name__icontains=current_search)

    paginator = Paginator(batches, BATCH_PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get('page'))

    pagination_qs = ('&' + urlencode({'q': current_search})) if current_search else ''
    empty_message = (
        'No matching batches.' if current_search
        else 'No batches yet. Select multiple entries on the Home page and click Group to create one.'
    )

    return render(request, "batch.html", {
        "batches": page_obj.object_list,
        "page_obj": page_obj,
        "current_search": current_search,
        "pagination_qs": pagination_qs,
        "empty_message": empty_message,
    })


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
        ids = _digit_ids(request)

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
            else:
                messages.error(request, "Select at least one entry to remove.")

        elif action == 'add':
            entries_to_add = Entry.objects.filter(pk__in=ids).exclude(batches=batch_obj)
            added = entries_to_add.count()
            batch_obj.entries.add(*entries_to_add)
            if added:
                messages.success(request, f"Added {added} {'entry' if added == 1 else 'entries'} to the batch.")
            else:
                messages.error(request, "Select at least one entry to add.")

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
def create_entry(request):
    if request.method == 'POST':
        form = EntryForm(request.POST)
        if form.is_valid():
            entry = form.save()
            messages.success(request, f"Entry for {entry.vehicle_number} created.")
            return redirect('home')
    else:
        form = EntryForm()

    return render(request, "new_entry.html", {"form": form})


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
    ids = _digit_ids(request)
    if not ids:
        return JsonResponse({'error': 'No ids provided.'}, status=400)
    deleted_count, _ = Entry.objects.filter(pk__in=ids).delete()
    return JsonResponse({'deleted': deleted_count})


@login_required
@require_POST
def create_batch(request):
    ids = _digit_ids(request)
    name = request.POST.get('name', '').strip()

    # Validated against entries that actually exist, not just len(ids): a
    # stale/deleted id slipping through here would otherwise let a 2-id
    # request past this guard while resolving to 0 or 1 real rows.
    entries = list(Entry.objects.filter(pk__in=ids))
    if len(entries) < 2:
        return JsonResponse({'error': 'Select at least two entries to group.'}, status=400)
    if not name:
        return JsonResponse({'error': 'Batch name is required.'}, status=400)

    new_batch = Batch.objects.create(name=name)
    new_batch.entries.add(*entries)
    return JsonResponse({'batch_id': new_batch.id, 'grouped': len(entries)})


@login_required
@require_POST
def download_entries_pdf(request):
    scope = request.POST.get('scope', '')
    batch_obj = None

    if scope == 'choose':
        ids = _digit_ids(request)
        if not ids:
            return JsonResponse({'error': 'Select at least one entry to download.'}, status=400)
        # Preserves the exact order ids were submitted in (the order rows
        # were selected/checked on the home page, see home.js), rather than
        # re-sorting by id/date — a picked-order download, not a ledger
        # slice. Built via a dict lookup instead of filter(...).order_by(...)
        # since a queryset has no way to sort by "position in an arbitrary
        # id list"; also silently drops any stale id that no longer resolves
        # to a real row, same as the existence check this replaces.
        entries_by_id = {str(entry.id): entry for entry in Entry.objects.filter(pk__in=ids)}
        entries = [entries_by_id[i] for i in ids if i in entries_by_id]
        if not entries:
            return JsonResponse({'error': 'Select at least one entry to download.'}, status=400)
    elif scope == 'batch':
        batch_obj = get_object_or_404(Batch, slug=request.POST.get('slug', ''))
        entries = batch_obj.entries.order_by('-date', '-id')
    elif scope == 'range':
        start = request.POST.get('start', '')
        end = request.POST.get('end', '')
        if not (start.isdigit() and end.isdigit()) or int(start) < 1 or int(end) < int(start):
            return JsonResponse({'error': 'Invalid range.'}, status=400)
        start, end = int(start), int(end)
        # The bucket itself is still selected by position counted from the
        # newest end ('-id'), but the rows within it are then reversed to
        # ascending (oldest-in-bucket first) so the PDF reads chronologically
        # top-to-bottom — consistent with 'all'/'first_100' below, and with
        # the S.No column (still labeled start..end via enumerate() further
        # down) counting up in the same direction as the actual dates.
        entries = list(Entry.objects.order_by('-id')[start - 1:end])[::-1]
    elif scope == 'first_100':
        # The oldest 100 records — the mirror image of a 100-record range
        # anchored to the *other* end of the table. Ordered ascending (oldest first)
        # rather than the '-id' newest-first convention every other scope
        # uses, so the PDF reads top-to-bottom the same direction its S.No
        # counts up: the real app serial_number for these specific rows
        # already is 1..100 (or fewer, capped naturally by the slice), so
        # no special-casing is needed in the S.No section below.
        entries = Entry.objects.order_by('id')[:100]
    elif scope == 'all':
        # Ascending (oldest first) so the PDF reads top-to-bottom the same
        # direction its S.No counts up, matching 'first_100' below.
        entries = Entry.objects.order_by('id')
    else:
        return JsonResponse({'error': 'Invalid scope.'}, status=400)

    entries = list(entries)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=landscape(A4), title='Truck Loading Entries',
        leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
    )
    styles = getSampleStyleSheet()
    # Plain strings don't wrap inside a Table cell, and these headers are too
    # wide for a column narrow enough to fit 8 columns on the page — wrapped
    # in Paragraphs so long headers like "Net Kg (Loading/Roll)" break onto a
    # second line instead of overflowing into the next column.
    header_style = ParagraphStyle(
        'PdfTableHeader', parent=styles['Normal'], textColor=colors.white,
        fontName='Helvetica-Bold', fontSize=8, leading=10, alignment=TA_CENTER,
    )

    body_style = ParagraphStyle(
        'PdfTableBody', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=10, alignment=TA_LEFT,
    )

    # This header tuple's length/order must stay in lockstep with the
    # colWidths list passed to Table() below (9 entries each, position-for-
    # position) — reportlab raises if their lengths mismatch, so a column
    # added to only one of them fails loudly at PDF-build time rather than
    # silently misrendering, but check both together if you touch either.
    rows = [[
        Paragraph(text, header_style) for text in (
            'S.No', 'Date', 'Vehicle Number', 'Loading/Roll', 'Net Kg (Loading/Roll)',
            'Weight/Roll', 'Net Kg (Weight/Roll)', 'Workers', 'Remark',
        )
    ]]
    if scope == 'range':
        # This scope's S.No mirrors the range button's own label (101-200 ->
        # S.No 101..200) rather than each entry's real app serial_number — a
        # deliberate difference from every other scope below: a range
        # download is conceptually "page 2 of the ledger", so its row
        # numbers should read as a continuous 101, 102, ... regardless of
        # the underlying ids, the same way a printed ledger's second page
        # would be numbered.
        sno_source = enumerate(entries, start=start)
    else:
        # The home page's own S.No (a rank by creation order, ascending id).
        # Deliberately computed as a fresh, unfiltered ranking over the
        # *whole* table rather than an annotate()+filter() on one query:
        # Window(RowNumber()) ranks against whatever rows survive the SQL
        # WHERE clause, which runs before window functions do — so e.g.
        # annotating then .filter(pk__in=ids) for "choose" would rank only
        # within the 2-3 chosen rows (1, 2, 3...) instead of their real,
        # global serial numbers. Ranking the full table once (via the shared
        # _serial_by_id() helper) and looking up by id sidesteps that trap
        # for every scope that filters first (choose, batch).
        serial_by_id = _serial_by_id()
        sno_source = ((serial_by_id[entry.id], entry) for entry in entries)

    total_loading_roll = Decimal('0')
    total_net_kg_loading_roll = Decimal('0')
    total_weight_roll = Decimal('0')
    total_net_kg_weight_roll = Decimal('0')

    for sno, entry in sno_source:
        total_loading_roll += entry.loading_roll or Decimal('0')
        total_net_kg_loading_roll += entry.net_kg_loading_roll or Decimal('0')
        total_weight_roll += entry.weight_roll or Decimal('0')
        total_net_kg_weight_roll += entry.net_kg_weight_roll or Decimal('0')
        rows.append([
            str(sno),
            entry.date.strftime('%d-%m-%Y'),
            # vehicle_number is now free text up to 100 chars (a phrase, for
            # trucks that don't report a number) rather than a short plate
            # code, so it's wrapped in a Paragraph like remark below --
            # escaped the same way, for the same reason.
            Paragraph(xml_escape(entry.vehicle_number) if entry.vehicle_number else '—', body_style),
            _fmt_pdf_number(entry.loading_roll),
            _fmt_pdf_number(entry.net_kg_loading_roll, ' kg'),
            _fmt_pdf_number(entry.weight_roll),
            _fmt_pdf_number(entry.net_kg_weight_roll, ' kg'),
            _fmt_pdf_number(entry.workers),
            # remark is free text (EntryForm has no character restriction) and
            # Paragraph() interprets a small XML-like markup language rather
            # than plain text (<b>, <font color=...>, <a href=...>, etc.) --
            # escaped first so a literal '&'/'<' in a remark can't break PDF
            # generation or be interpreted as real markup/hyperlinks.
            Paragraph(xml_escape(entry.remark) if entry.remark else '—', body_style),
        ])

    # Trailing summary row — S.No/Date/Workers/Remark left blank (a "Total"
    # doesn't have any of those), 'Total' spans the first three columns via
    # the SPAN style below, and the four roll/net-kg columns are summed
    # across every exported entry (None values treated as 0, same as
    # _fmt_pdf_number already renders a bare None as '—' per-row).
    # 'Total' must go in the span's *first* cell (index 0, not 1 or 2) —
    # ReportLab only renders the top-left cell's content across a SPAN and
    # silently drops whatever's in the other spanned cells.
    total_row_index = len(rows)
    rows.append([
        Paragraph('Total', body_style), '', '',
        _fmt_pdf_number(total_loading_roll),
        _fmt_pdf_number(total_net_kg_loading_roll, ' kg'),
        _fmt_pdf_number(total_weight_roll),
        _fmt_pdf_number(total_net_kg_weight_roll, ' kg'),
        '', '',
    ])

    # Kept in sync with the header tuple above (see its comment) — 9 widths
    # for the same 9 columns, in the same order.
    table = Table(rows, repeatRows=1, colWidths=[35, 65, 100, 65, 85, 65, 85, 55, 185])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16233d')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        # Total row: spans 'Total' across S.No/Date/Vehicle Number, bold,
        # and set off from the data rows with a shaded background + a rule
        # above it rather than blending into the alternating row stripes.
        ('SPAN', (0, total_row_index), (2, total_row_index)),
        ('FONTNAME', (0, total_row_index), (-1, total_row_index), 'Helvetica-Bold'),
        ('BACKGROUND', (0, total_row_index), (-1, total_row_index), colors.HexColor('#e2e8f0')),
        ('LINEABOVE', (0, total_row_index), (-1, total_row_index), 1, colors.HexColor('#16233d')),
    ]))

    record_word = 'record' if len(entries) == 1 else 'records'
    title = f'Batch — {batch_obj.name}' if batch_obj else 'Truck Loading Entries'
    elements = [
        Paragraph(title, styles['Title']),
        Paragraph(
            f'Generated on {timezone.localdate().strftime("%d-%m-%Y")} — {len(entries)} {record_word}',
            styles['Normal'],
        ),
        Spacer(1, 10),
        table,
    ]
    doc.build(elements)

    if batch_obj:
        scope_part = batch_obj.slug
    elif scope == 'range':
        scope_part = f'range-{start}-{end}'
    else:
        scope_part = scope
    filename = f'truck-entries-{scope_part}-{timezone.localdate().isoformat()}.pdf'
    response = HttpResponse(buffer.getvalue(), content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


@login_required
@require_POST
def change_username(request):
    new_username = request.POST.get('new_username', '').strip()
    if not new_username:
        return JsonResponse({'error': 'Enter a username.'}, status=400)

    try:
        UnicodeUsernameValidator()(new_username)
    except ValidationError as exc:
        return JsonResponse({'error': ' '.join(exc.messages)}, status=400)

    if User.objects.exclude(pk=request.user.pk).filter(username=new_username).exists():
        return JsonResponse({'error': 'That username is already taken.'}, status=400)

    request.user.username = new_username
    request.user.save(update_fields=['username'])
    return JsonResponse({'username': new_username})


@login_required
@require_POST
def change_password(request):
    old_password = request.POST.get('old_password', '')
    new_password = request.POST.get('new_password', '')
    confirm_password = request.POST.get('confirm_password', '')
    # Set by Account Settings' own Cancel-revert call (see account-settings.js)
    # to restore whatever password was active before this session's change.
    # Strength validation is intentionally skipped in that case only: the
    # value being restored was already the live password moments earlier
    # (proven by matching check_password below), so re-running
    # AUTH_PASSWORD_VALIDATORS against it — which can reject an existing
    # password it never would have blocked at set-time (e.g.
    # UserAttributeSimilarityValidator flagging it against the account's own
    # email) — would make Cancel unable to undo a password change at all.
    is_revert = request.POST.get('revert') == '1'

    if not request.user.check_password(old_password):
        return JsonResponse({'error': 'Current password is incorrect.'}, status=400)
    if new_password != confirm_password:
        return JsonResponse({'error': 'Passwords do not match.'}, status=400)

    if not is_revert:
        try:
            validate_password(new_password, user=request.user)
        except ValidationError as exc:
            return JsonResponse({'error': ' '.join(exc.messages)}, status=400)

    request.user.set_password(new_password)
    request.user.save(update_fields=['password'])
    update_session_auth_hash(request, request.user)
    return JsonResponse({'detail': 'Password changed successfully.'})


@login_required
@require_POST
def change_email_request_otp(request):
    new_email = request.POST.get('new_email', '').strip()
    try:
        validate_email(new_email)
    except ValidationError as exc:
        return JsonResponse({'error': ' '.join(exc.messages)}, status=400)

    user = request.user
    error_response = _send_otp_email(
        otp_key=f'account_email_otp:{user.pk}',
        cooldown_key=f'account_email_otp_cooldown:{user.pk}',
        cache_payload={'email': new_email},
        recipient_email=new_email,
        subject='Entry Recorder — Confirm Your New Email',
    )
    if error_response is not None:
        return error_response

    return JsonResponse({'detail': 'A verification code has been sent to the new email address.'})


@login_required
@require_POST
def change_email_verify(request):
    new_email = request.POST.get('new_email', '').strip()
    otp = request.POST.get('otp', '').strip()

    user = request.user
    otp_key = f'account_email_otp:{user.pk}'
    error_response, _entry = _check_otp(
        otp_key, lambda entry: entry['email'].lower() != new_email.lower() or entry['otp'] != otp,
    )
    if error_response is not None:
        return error_response

    cache.set(f'account_email_revert:{user.pk}', user.email, EMAIL_REVERT_TTL_SECONDS)

    user.email = new_email
    user.save(update_fields=['email'])
    return JsonResponse({'email': new_email})


@login_required
@require_POST
def change_email_revert(request):
    user = request.user
    key = f'account_email_revert:{user.pk}'
    previous_email = cache.get(key)
    if previous_email is not None:
        user.email = previous_email
        user.save(update_fields=['email'])
        cache.delete(key)
    return JsonResponse({'email': user.email})


# --- Forgot Password (unauthenticated — runs before login) ---
# username lookups use __iexact throughout because Django's own ModelBackend
# (UserManager.get_by_natural_key) authenticates case-insensitively on
# username, so "correct" here has to mean the same thing it means at actual
# login time.


@require_POST
def check_username(request):
    # Unauthenticated username-enumeration oracle otherwise -- rate-limited
    # per-IP (see CHECK_USERNAME_MAX_ATTEMPTS above) since there's no valid
    # username yet to key a per-account limit on. Once throttled, this
    # returns the same {'valid': False} shape as a genuine miss rather than
    # a distinguishable error, so it can't itself be used to detect throttling.
    ip = request.META.get('REMOTE_ADDR', 'unknown')
    attempts_key = f'check_username_attempts:{ip}'
    attempts = cache.get(attempts_key, 0)
    if attempts >= CHECK_USERNAME_MAX_ATTEMPTS:
        return JsonResponse({'valid': False}, status=429)
    cache.set(attempts_key, attempts + 1, CHECK_USERNAME_ATTEMPTS_TTL_SECONDS)

    username = request.POST.get('username', '').strip()
    valid = bool(username) and User.objects.filter(username__iexact=username).exists()
    return JsonResponse({'valid': valid})


@require_POST
def forgot_password_request_otp(request):
    username = request.POST.get('username', '').strip()
    email = request.POST.get('email', '').strip()

    user = User.objects.filter(username__iexact=username).first()

    # Wrong-email guesses against a known username are throttled the same
    # way OTP verification already is (OTP_MAX_ATTEMPTS / _check_otp) --
    # without this, an attacker who already knows (or has enumerated) a
    # valid username could brute-force the account's registered email with
    # no limit, since the cooldown in _send_otp_email is only ever reached
    # after a correct email match. Keyed by user.pk, same convention as
    # every other OTP-related cache key in this file.
    attempts_key = f'forgot_password_email_attempts:{user.pk}' if user else None
    throttled = attempts_key is not None and cache.get(attempts_key, 0) >= FORGOT_PASSWORD_EMAIL_MAX_ATTEMPTS

    if throttled or user is None or not email or user.email.lower() != email.lower():
        # Deliberately the same error whether the username doesn't exist,
        # the email just doesn't match it, or the attempt cap above was
        # just hit — this step can't be used to probe which usernames are
        # real, or to detect that throttling (rather than a wrong guess)
        # is what triggered the error.
        if attempts_key and not throttled:
            cache.set(attempts_key, cache.get(attempts_key, 0) + 1, FORGOT_PASSWORD_EMAIL_ATTEMPTS_TTL_SECONDS)
        return JsonResponse({'error': 'Enter Correct Email'}, status=400)

    cache.delete(attempts_key)

    error_response = _send_otp_email(
        otp_key=f'forgot_password_otp:{user.pk}',
        cooldown_key=f'forgot_password_cooldown:{user.pk}',
        cache_payload={},
        recipient_email=user.email,
        subject='Entry Recorder — Password Reset Code',
    )
    if error_response is not None:
        return error_response

    return JsonResponse({'detail': 'A verification code has been sent to your email.'})


@require_POST
def forgot_password_verify_otp(request):
    username = request.POST.get('username', '').strip()
    otp = request.POST.get('otp', '').strip()

    user = User.objects.filter(username__iexact=username).first()
    if user is None:
        return JsonResponse({'error': 'Enter Correct Email'}, status=400)

    otp_key = f'forgot_password_otp:{user.pk}'
    error_response, _entry = _check_otp(otp_key, lambda entry: entry['otp'] != otp)
    if error_response is not None:
        return error_response

    # Single-use: consumed as soon as it's checked correctly (_check_otp
    # already deleted it from cache on the success path above).
    reset_token = secrets.token_urlsafe(32)
    cache.set(f'forgot_password_reset_token:{reset_token}', user.pk, RESET_TOKEN_TTL_SECONDS)
    return JsonResponse({'reset_token': reset_token})


@require_POST
def forgot_password_reset(request):
    reset_token = request.POST.get('reset_token', '').strip()
    new_password = request.POST.get('new_password', '')
    confirm_password = request.POST.get('confirm_password', '')

    token_key = f'forgot_password_reset_token:{reset_token}'
    user_pk = cache.get(token_key) if reset_token else None
    if user_pk is None:
        return JsonResponse({'error': 'This reset link has expired. Please start again.'}, status=400)

    try:
        user = User.objects.get(pk=user_pk)
    except User.DoesNotExist:
        cache.delete(token_key)
        return JsonResponse({'error': 'This reset link has expired. Please start again.'}, status=400)

    if new_password != confirm_password:
        return JsonResponse({'error': 'Passwords do not match.'}, status=400)

    try:
        validate_password(new_password, user=user)
    except ValidationError as exc:
        return JsonResponse({'error': ' '.join(exc.messages)}, status=400)

    user.set_password(new_password)
    user.save(update_fields=['password'])
    # Single-use: a spent or abandoned token can't be replayed.
    cache.delete(token_key)

    return JsonResponse({'detail': 'Password reset successful. Please log in with your new password.'})
