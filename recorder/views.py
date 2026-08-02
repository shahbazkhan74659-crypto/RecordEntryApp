import secrets
from io import BytesIO

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.contrib.auth.models import User
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.db.models import Count, F, Window
from django.db.models.functions import RowNumber
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .forms import EntryForm
from .models import Batch, Entry

OTP_TTL_SECONDS = 5 * 60
OTP_RESEND_COOLDOWN_SECONDS = 60
OTP_MAX_ATTEMPTS = 5
EMAIL_REVERT_TTL_SECONDS = 30 * 60
RESET_TOKEN_TTL_SECONDS = 10 * 60

# "Last N" scopes for download_entries_pdf, mapped to the slice size taken
# off Entry.objects.order_by('-id') (None means no limit, i.e. all records).
PDF_SCOPE_LIMITS = {'all': None, 'last_10': 10, 'last_50': 50, 'last_100': 100}


def _fmt_pdf_number(value, suffix=''):
    """Renders an optional numeric Entry field for the PDF table: '—' when
    left blank (None), otherwise the value with the given unit suffix."""
    return '—' if value is None else f'{value}{suffix}'


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
        return JsonResponse(
            {'error': 'Could not send the verification email. Check the SMTP settings in .env.'}, status=500,
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


@login_required
def home(request):
    # serial_number is a stable rank by creation order (ascending id). Display
    # order is "-id" (newest created first) rather than "-date, -id" —
    # sorting by date first breaks a monotonic descending S.No the moment two
    # entries share a date (e.g. two added the same day the table was already
    # seeded for "today"), since same-date rows would then interleave by id
    # in a way that doesn't match their serial_number order top-to-bottom.
    entries = Entry.objects.annotate(
        serial_number=Window(expression=RowNumber(), order_by=F('id').asc())
    ).order_by('-id')
    return render(request, "home.html", {"entries": entries})


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
        ids = [i for i in request.POST.getlist('ids') if i.isdigit()]

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
    ids = [i for i in request.POST.getlist('ids') if i.isdigit()]
    if not ids:
        return JsonResponse({'error': 'No ids provided.'}, status=400)
    deleted_count, _ = Entry.objects.filter(pk__in=ids).delete()
    return JsonResponse({'deleted': deleted_count})


@login_required
@require_POST
def create_batch(request):
    ids = [i for i in request.POST.getlist('ids') if i.isdigit()]
    name = request.POST.get('name', '').strip()

    if len(ids) < 2:
        return JsonResponse({'error': 'Select at least two entries to group.'}, status=400)
    if not name:
        return JsonResponse({'error': 'Batch name is required.'}, status=400)

    new_batch = Batch.objects.create(name=name)
    entries = Entry.objects.filter(pk__in=ids)
    new_batch.entries.add(*entries)
    return JsonResponse({'batch_id': new_batch.id, 'grouped': entries.count()})


@login_required
@require_POST
def download_entries_pdf(request):
    scope = request.POST.get('scope', '')
    batch_obj = None

    if scope == 'choose':
        ids = [i for i in request.POST.getlist('ids') if i.isdigit()]
        if not ids:
            return JsonResponse({'error': 'Select at least one entry to download.'}, status=400)
        # Reordered to match the home table's own display order ('-id') rather
        # than the order ids were selected in, so e.g. picking the 1st and 3rd
        # visible rows always renders as rows 1 and 2 in the PDF, in that order.
        entries = Entry.objects.filter(pk__in=ids).order_by('-id')
    elif scope == 'batch':
        batch_obj = get_object_or_404(Batch, slug=request.POST.get('slug', ''))
        entries = batch_obj.entries.order_by('-date', '-id')
    elif scope in PDF_SCOPE_LIMITS:
        entries = Entry.objects.order_by('-id')
        limit = PDF_SCOPE_LIMITS[scope]
        if limit is not None:
            entries = entries[:limit]
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

    rows = [[
        Paragraph(text, header_style) for text in (
            'S.No', 'Date', 'Vehicle Number', 'Loading/Roll', 'Net Kg (Loading/Roll)',
            'Weight/Roll', 'Net Kg (Weight/Roll)', 'Workers',
        )
    ]]
    for index, entry in enumerate(entries, start=1):
        rows.append([
            str(index),
            entry.date.strftime('%d-%m-%Y'),
            entry.vehicle_number,
            _fmt_pdf_number(entry.loading_roll),
            _fmt_pdf_number(entry.net_kg_loading_roll, ' kg'),
            _fmt_pdf_number(entry.weight_roll),
            _fmt_pdf_number(entry.net_kg_weight_roll, ' kg'),
            _fmt_pdf_number(entry.workers),
        ])

    table = Table(rows, repeatRows=1, colWidths=[35, 65, 100, 65, 85, 65, 85, 55])
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

    scope_part = batch_obj.slug if batch_obj else scope
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
    username = request.POST.get('username', '').strip()
    valid = bool(username) and User.objects.filter(username__iexact=username).exists()
    return JsonResponse({'valid': valid})


@require_POST
def forgot_password_request_otp(request):
    username = request.POST.get('username', '').strip()
    email = request.POST.get('email', '').strip()

    user = User.objects.filter(username__iexact=username).first()
    if user is None or not email or user.email.lower() != email.lower():
        # Deliberately the same error whether the username doesn't exist or
        # the email just doesn't match it — this step can't be used to probe
        # which usernames are real.
        return JsonResponse({'error': 'Enter Correct Email'}, status=400)

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
