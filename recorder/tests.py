import re
from decimal import Decimal
from io import BytesIO

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase
from pypdf import PdfReader

from .models import Batch, Entry, entries_with_serial_number
from .views import CHECK_USERNAME_MAX_ATTEMPTS, FORGOT_PASSWORD_EMAIL_MAX_ATTEMPTS, LOGIN_MAX_ATTEMPTS


def build_after_100_ranges(count):
    """Mirrors buildRanges() in static/js/src/home.js — the "Save by Range"
    modal's range list (101-200, 201-300, ...), extending only as long as
    more than 20 records remain past the last boundary. Kept in sync with
    the JS by hand since this project has no JS test runner; if the JS
    algorithm changes, update this too."""
    ranges = []
    boundary = 100
    while count - boundary > 20:
        ranges.append((boundary + 1, boundary + 100))
        boundary += 100
    return ranges


def expected_range_sno(start, end, total_count):
    """The 'range' scope's S.No is a deliberate exception (see views.py):
    it mirrors the range button's own label — 101-200 -> S.No 101, 102, ...
    — rather than each entry's real app serial_number, capped by however
    many rows actually exist in a partial final range."""
    actual_rows = max(0, min(end, total_count) - start + 1)
    return list(range(start, start + actual_rows))


def extract_pdf_vehicle_numbers(pdf_bytes, pattern):
    """Reads vehicle-number column values out of a generated entries PDF, in
    row order — unlike the S.No column (which is just a label, independent
    of physical row order for the 'range' scope), this is how a test proves
    which actual entry printed in which position."""
    reader = PdfReader(BytesIO(pdf_bytes))
    numbers = []
    for page in reader.pages:
        numbers.extend(re.findall(pattern, page.extract_text()))
    return numbers


def extract_pdf_serial_numbers(pdf_bytes):
    """Reads the S.No column values out of a generated entries PDF, in row
    order. The table layout per row is a fixed sequence of text lines
    (S.No, Date, Vehicle Number, ...), so a bare integer line immediately
    followed by a dd-mm-yyyy line is unambiguously an S.No cell (no other
    column is immediately followed by a date)."""
    reader = PdfReader(BytesIO(pdf_bytes))
    serials = []
    for page in reader.pages:
        lines = [line.strip() for line in page.extract_text().split('\n')]
        for i, line in enumerate(lines):
            if line.isdigit() and i + 1 < len(lines) and re.match(r'^\d{2}-\d{2}-\d{4}$', lines[i + 1]):
                serials.append(int(line))
    return serials


class After100RangeExportTests(TestCase):
    """Regression coverage for the 'Save by Range' PDF export (download_entries_pdf,
    scope='range'): the PDF's S.No column must read as a continuation of the
    range button's own label (101-200 -> S.No 101..200), not the entry's real
    app serial_number and not a 1..N renumbering of just the exported slice."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='tester', password='pw12345!Strong')
        # 125 rows is enough to exercise the "Save by Range" modal's first range
        # button (101-200, only partially filled here) without the cost of a
        # multi-thousand-row seed.
        Entry.objects.bulk_create([
            Entry(
                vehicle_number=f'MH12AB{i:04d}',
                loading_roll=10, net_kg_loading_roll=100,
                weight_roll=10, net_kg_weight_roll=100, workers=1,
                remark='' if i % 2 else f'note {i}',
            )
            for i in range(1, 126)
        ])

    def setUp(self):
        self.client.force_login(self.user)

    def test_builds_exactly_the_expected_ranges_for_this_seed(self):
        # 125 - 100 = 25 > 20, so the 101-200 button appears; 125 - 200 < 0,
        # so nothing further does.
        self.assertEqual(build_after_100_ranges(Entry.objects.count()), [(101, 200)])

    def test_pdf_sno_follows_the_range_label_for_each_after_100_range(self):
        ranges = build_after_100_ranges(Entry.objects.count())
        self.assertTrue(ranges, "test seed must produce at least one Save by Range range")

        for start, end in ranges:
            with self.subTest(start=start, end=end):
                response = self.client.post('/entries/download-pdf/', {
                    'scope': 'range', 'start': start, 'end': end,
                })
                self.assertEqual(response.status_code, 200)

                pdf_serials = extract_pdf_serial_numbers(response.content)
                expected = expected_range_sno(start, end, Entry.objects.count())
                self.assertEqual(pdf_serials, expected)

    def test_partial_final_range_numbers_only_as_far_as_it_has_rows(self):
        # 125 entries sliced [100:200] only has 25 rows (101..125), even
        # though the button is labeled "101-200" — S.No must stop at 125,
        # not continue counting up to a phantom 200.
        response = self.client.post('/entries/download-pdf/', {
            'scope': 'range', 'start': '101', 'end': '200',
        })
        pdf_serials = extract_pdf_serial_numbers(response.content)
        self.assertEqual(pdf_serials, list(range(101, 126)))

    def test_first_100_shows_the_oldest_records_ascending(self):
        # The mirror image of the newest 100-record range: the 100 oldest
        # records, oldest first, S.No counting up 1..100 — the real app
        # serial_number for these specific rows already is 1..100, so this
        # doubles as the 'first_100' analog of ChooseExportMatchesAppSerialNumberTests.
        response = self.client.post('/entries/download-pdf/', {'scope': 'first_100'})
        self.assertEqual(response.status_code, 200)
        pdf_serials = extract_pdf_serial_numbers(response.content)
        self.assertEqual(pdf_serials, list(range(1, 101)))

    def test_pdf_includes_remark_column(self):
        response = self.client.post('/entries/download-pdf/', {
            'scope': 'range', 'start': '101', 'end': '200',
        })
        reader = PdfReader(BytesIO(response.content))
        self.assertIn('Remark', reader.pages[0].extract_text())

    def test_range_rows_read_chronologically_ascending_top_to_bottom(self):
        # The 101-200 bucket is still selected by position counted from the
        # newest end, but the rows within it must now print oldest-first —
        # MH12AB0001 (the oldest entry overall) belongs at the top of this
        # 25-row bucket and MH12AB0025 at the bottom, not the reverse.
        response = self.client.post('/entries/download-pdf/', {
            'scope': 'range', 'start': '101', 'end': '200',
        })
        vehicle_numbers = extract_pdf_vehicle_numbers(response.content, r'MH12AB\d{4}')
        self.assertEqual(vehicle_numbers, [f'MH12AB{i:04d}' for i in range(1, 26)])

    def test_range_rejects_invalid_bounds(self):
        for payload in (
            {'scope': 'range', 'start': '200', 'end': '101'},  # end < start
            {'scope': 'range', 'start': '0', 'end': '10'},     # start < 1
            {'scope': 'range', 'start': 'x', 'end': '10'},     # non-digit
        ):
            with self.subTest(payload=payload):
                response = self.client.post('/entries/download-pdf/', payload)
                self.assertEqual(response.status_code, 400)


class ChooseExportMatchesAppSerialNumberTests(TestCase):
    """'all'/'choose' scopes are the opposite case from 'range': their S.No
    must match the entry's real app serial_number (the same value the home
    page's own S.No column shows), not a repositioned count."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='tester_lastn', password='pw12345!Strong')
        Entry.objects.bulk_create([
            Entry(
                vehicle_number=f'MH12CD{i:04d}',
                loading_roll=10, net_kg_loading_roll=100,
                weight_roll=10, net_kg_weight_roll=100, workers=1, remark='',
            )
            for i in range(1, 31)
        ])

    def setUp(self):
        self.client.force_login(self.user)

    def test_first_100_caps_at_the_real_count_when_under_100(self):
        # Only 30 entries exist — 'first_100' must return all 30 (S.No
        # 1..30), not error or pad out to a phantom 100.
        response = self.client.post('/entries/download-pdf/', {'scope': 'first_100'})
        pdf_serials = extract_pdf_serial_numbers(response.content)
        self.assertEqual(pdf_serials, list(range(1, 31)))

    def test_choose_shows_real_serial_numbers_for_the_picked_ids(self):
        picked_ids = list(Entry.objects.order_by('-id').values_list('id', flat=True)[:3])
        response = self.client.post('/entries/download-pdf/', {'scope': 'choose', 'ids': picked_ids})
        pdf_serials = extract_pdf_serial_numbers(response.content)
        self.assertEqual(pdf_serials, [30, 29, 28])

    def test_all_scope_downloads_in_ascending_order(self):
        # 'all' used to be newest-first ('-id'); it's now oldest-first, so
        # the PDF's S.No column reads 1..30 top-to-bottom instead of 30..1.
        response = self.client.post('/entries/download-pdf/', {'scope': 'all'})
        pdf_serials = extract_pdf_serial_numbers(response.content)
        self.assertEqual(pdf_serials, list(range(1, 31)))

    def test_choose_preserves_the_order_ids_were_submitted_in(self):
        # 'choose' used to always re-sort picked rows back to '-id' display
        # order regardless of pick order; it now preserves exactly the order
        # ids arrive in, so this scrambled (non-id-ordered) submission must
        # come back in that same scrambled order, not resorted either way.
        all_ids = list(Entry.objects.order_by('id').values_list('id', flat=True))
        scrambled_ids = [all_ids[5], all_ids[0], all_ids[29], all_ids[14]]
        response = self.client.post('/entries/download-pdf/', {'scope': 'choose', 'ids': scrambled_ids})
        pdf_serials = extract_pdf_serial_numbers(response.content)
        self.assertEqual(pdf_serials, [6, 1, 30, 15])

    def test_choose_drops_stale_ids_but_keeps_submitted_order(self):
        real_ids = list(Entry.objects.order_by('id').values_list('id', flat=True)[:2])
        stale_id = Entry.objects.order_by('-id').first().id + 1000
        response = self.client.post('/entries/download-pdf/', {
            'scope': 'choose', 'ids': [real_ids[1], stale_id, real_ids[0]],
        })
        pdf_serials = extract_pdf_serial_numbers(response.content)
        self.assertEqual(pdf_serials, [2, 1])


class PdfTotalsRowTests(TestCase):
    """The exported PDF ends with a summary 'Total' row across the four
    numeric roll/net-kg columns (Loading/Roll, Net Kg (Loading/Roll),
    Weight/Roll, Net Kg (Weight/Roll)) — added per an explicit client
    request after reviewing a downloaded PDF. S.No/Date/Workers/Remark stay
    blank on that row; a None field on an individual entry counts as 0
    toward the sum (it renders as '—' on its own row, but shouldn't make
    the total wrong)."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='tester_totals', password='pw12345!Strong')
        Entry.objects.bulk_create([
            Entry(
                vehicle_number=f'MH12EF{i:04d}',
                loading_roll=Decimal(i), net_kg_loading_roll=Decimal(i) * 10,
                weight_roll=Decimal(i) * 2, net_kg_weight_roll=Decimal(i) * 20,
                workers=1, remark='',
            )
            for i in range(1, 6)
        ])
        # One entry with blank numeric fields, to prove None doesn't break
        # or silently exclude itself from the sum in a wrong way.
        Entry.objects.create(vehicle_number='MH12EF9999', workers=1, remark='')

    def setUp(self):
        self.client.force_login(self.user)

    def test_total_row_sums_the_four_numeric_columns(self):
        response = self.client.post('/entries/download-pdf/', {'scope': 'all'})
        text = PdfReader(BytesIO(response.content)).pages[-1].extract_text()
        self.assertIn('Total', text)
        # loading_roll: 1+2+3+4+5=15, net_kg_loading_roll: 10*(1+..+5)=150,
        # weight_roll: 2*(1+..+5)=30, net_kg_weight_roll: 20*(1+..+5)=300 —
        # the blank-fields entry contributes 0 to each.
        self.assertIn('15.00', text)
        self.assertIn('150.00 kg', text)
        self.assertIn('30.00', text)
        self.assertIn('300.00 kg', text)

    def test_total_row_appears_for_choose_scope_too(self):
        ids = list(Entry.objects.values_list('id', flat=True))
        response = self.client.post('/entries/download-pdf/', {'scope': 'choose', 'ids': ids})
        text = PdfReader(BytesIO(response.content)).pages[-1].extract_text()
        self.assertIn('Total', text)
        self.assertIn('15.00', text)


class After100RangeExportAtProductionScaleTests(TestCase):
    """Same range-label-numbering check as After100RangeExportTests, but at a
    row count (1121) matching what was actually seeded and manually tested in
    this project when a S.No mismatch was reported — covers all 11 range
    buttons and multi-page PDFs (each 100-row range spans several pages),
    which the smaller 125-row test above doesn't exercise."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='tester2', password='pw12345!Strong')
        Entry.objects.bulk_create([
            Entry(
                vehicle_number=f'MH12AB{i:04d}',
                loading_roll=10, net_kg_loading_roll=100,
                weight_roll=10, net_kg_weight_roll=100, workers=1,
                remark='' if i % 2 else f'note {i}',
            )
            for i in range(1, 1122)
        ], batch_size=500)

    def setUp(self):
        self.client.force_login(self.user)

    def test_builds_eleven_ranges_for_this_seed(self):
        ranges = build_after_100_ranges(Entry.objects.count())
        self.assertEqual(ranges, [(b + 1, b + 100) for b in range(100, 1101, 100)])

    def test_pdf_sno_follows_the_range_label_across_every_range(self):
        total = Entry.objects.count()
        ranges = build_after_100_ranges(total)

        for start, end in ranges:
            with self.subTest(start=start, end=end):
                response = self.client.post('/entries/download-pdf/', {
                    'scope': 'range', 'start': start, 'end': end,
                })
                self.assertEqual(response.status_code, 200)

                pdf_serials = extract_pdf_serial_numbers(response.content)
                expected = expected_range_sno(start, end, total)
                self.assertEqual(
                    pdf_serials, expected,
                    f"range {start}-{end}: PDF S.No {pdf_serials[:5]}...{pdf_serials[-5:]} "
                    f"!= expected {expected[:5]}...{expected[-5:]}",
                )

    def test_last_range_is_partial_and_stops_at_the_real_count(self):
        # 1121 total -> the final button is labeled "1101-1200" but only
        # 21 rows actually exist there (1101..1121).
        response = self.client.post('/entries/download-pdf/', {
            'scope': 'range', 'start': '1101', 'end': '1200',
        })
        pdf_serials = extract_pdf_serial_numbers(response.content)
        self.assertEqual(pdf_serials, list(range(1101, 1122)))


def extract_row_id_sno_pairs(html):
    """Reads (entry id, S.No) per row out of the home page's rendered HTML,
    via each row's select checkbox value (the entry's real pk) paired with
    the S.No cell that immediately follows it."""
    return [
        (int(pk), int(sno))
        for pk, sno in re.findall(r'value="(\d+)" aria-label="Select row"></label></td>\s*<td>(\d+)</td>', html)
    ]


class HomePagePaginationTests(TestCase):
    """The home page (recorder/views.py:home) paginates to HOME_PAGE_SIZE
    (30) rows and supports date/vehicle-number filtering via 'date'/'q' GET
    params — added because the table previously rendered every row
    unpaginated with client-side-only filtering. Covers: correct page size,
    no cross-page duplication, filters narrowing the paginated result set
    (not just the current page), and S.No staying each entry's real,
    global serial_number even when filtered (the same filter-then-window
    trap already fixed once for the PDF export's choose/batch scopes)."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='pager', password='pw12345!Strong')
        Entry.objects.bulk_create([
            # Half MH, half DL -> 32 MH matches, enough to span 2 pages of
            # 30 itself, so filtered-result pagination gets real coverage
            # too (not just the unfiltered 65-row case).
            Entry(
                vehicle_number=f'{"MH" if i % 2 == 0 else "DL"}12AB{i:04d}',
                loading_roll=10, net_kg_loading_roll=100,
                weight_roll=10, net_kg_weight_roll=100, workers=1, remark='',
            )
            for i in range(1, 66)  # 65 rows -> 3 pages of 30/30/5
        ], batch_size=500)

    def setUp(self):
        self.client.force_login(self.user)

    def test_page_one_has_30_rows_and_no_overlap_with_page_two(self):
        page1_ids = {pk for pk, _ in extract_row_id_sno_pairs(self.client.get('/').content.decode())}
        page2_ids = {pk for pk, _ in extract_row_id_sno_pairs(self.client.get('/?page=2').content.decode())}
        self.assertEqual(len(page1_ids), 30)
        self.assertEqual(len(page2_ids), 30)
        self.assertEqual(page1_ids & page2_ids, set())

    def test_last_page_has_the_remainder(self):
        page3_ids = {pk for pk, _ in extract_row_id_sno_pairs(self.client.get('/?page=3').content.decode())}
        self.assertEqual(len(page3_ids), 5)  # 65 - 30 - 30

    def test_sno_is_the_real_global_serial_number_even_when_filtered(self):
        serial_by_id = dict(entries_with_serial_number().values_list('id', 'serial_number'))
        html = self.client.get('/?q=MH').content.decode()
        rows = extract_row_id_sno_pairs(html)
        self.assertTrue(rows, "search must return at least one row")
        for pk, sno in rows:
            with self.subTest(pk=pk):
                self.assertEqual(sno, serial_by_id[pk])

    def test_search_filters_the_whole_dataset_not_just_current_page(self):
        # Every 2nd entry is MH-prefixed (see setUpTestData) -> 32 of 65.
        html = self.client.get('/?q=MH').content.decode()
        self.assertIn('Page 1 of', html)
        total_mh = Entry.objects.filter(vehicle_number__icontains='MH').count()
        self.assertIn(f'{total_mh} entries', html)

    def test_no_match_shows_filtered_empty_message_not_generic_one(self):
        html = self.client.get('/?q=ZZZZZ').content.decode()
        self.assertIn('No matching entries.', html)
        self.assertNotIn('No entries yet.', html)

    def test_malformed_date_param_does_not_500(self):
        response = self.client.get('/?date=not-a-real-date')
        self.assertEqual(response.status_code, 200)

    def test_pagination_links_preserve_active_filters(self):
        html = self.client.get('/?q=MH&page=1').content.decode()
        # HTML-escaped in the rendered href (& -> &amp;), since the query
        # suffix is now a single pre-built context var (pagination_qs) —
        # correct per HTML attribute-escaping rules, not a regression.
        self.assertIn('?page=2&amp;q=MH', html)

    def test_return_page_round_trips_through_pagination_links(self):
        # Regression: "All" (clear filter) must snap back to the page you
        # were on *before* filtering, not page 1 and not wherever you ended
        # up while filtered — return_page is how home.js threads that
        # memory through the server-rendered pagination links.
        html = self.client.get('/?q=MH&return_page=23').content.decode()
        self.assertIn('return_page=23', html)

    def test_malformed_return_page_is_dropped_not_500(self):
        response = self.client.get('/?q=MH&return_page=not-a-number')
        self.assertEqual(response.status_code, 200)
        self.assertNotIn('return_page=not-a-number', response.content.decode())

    def test_first_and_prev_disabled_on_page_one(self):
        # 65-row fixture -> 3 pages of 30/30/5.
        html = self.client.get('/').content.decode()
        self.assertIn('pagination-icon disabled" aria-hidden="true">&laquo;&laquo;', html)
        self.assertIn('pagination-icon disabled" aria-hidden="true">&laquo;', html)
        self.assertIn('aria-label="Next page">&raquo;</a>', html)
        self.assertIn('aria-label="Last page">&raquo;&raquo;</a>', html)

    def test_next_and_last_disabled_on_last_page(self):
        html = self.client.get('/?page=3').content.decode()
        self.assertIn('pagination-icon disabled" aria-hidden="true">&raquo;', html)
        self.assertIn('pagination-icon disabled" aria-hidden="true">&raquo;&raquo;', html)
        self.assertIn('aria-label="First page">', html)
        self.assertIn('aria-label="Previous page">', html)

    def test_first_and_last_links_jump_directly_not_one_page_at_a_time(self):
        html = self.client.get('/?page=2').content.decode()
        self.assertIn('href="?page=1"', html)  # First, from page 2
        self.assertIn('href="?page=3"', html)  # Last (num_pages=3), from page 2


class BatchPagePaginationTests(TestCase):
    """The batch list page (recorder/views.py:batch) paginates to
    BATCH_PAGE_SIZE (40 = 10 rows x the grid's 4 cards/row) cards per page —
    same Paginator pattern as the home page, but with no filter/search to
    preserve across page links."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='batchpager', password='pw12345!Strong')
        # Batch.save() auto-generates the slug; bulk_create() bypasses save()
        # entirely, which would leave every row's slug blank and collide on
        # the field's unique constraint — plain .create() per row instead.
        for i in range(1, 96):  # 95 -> 3 pages of 40/40/15
            Batch.objects.create(name=f'Batch {i:03d}')

    def setUp(self):
        self.client.force_login(self.user)

    def test_page_one_has_40_cards_and_no_overlap_with_page_two(self):
        page1 = set(re.findall(r'batch-card-name">([^<]+)</h2>', self.client.get('/batch/').content.decode()))
        page2 = set(re.findall(r'batch-card-name">([^<]+)</h2>', self.client.get('/batch/?page=2').content.decode()))
        self.assertEqual(len(page1), 40)
        self.assertEqual(len(page2), 40)
        self.assertEqual(page1 & page2, set())

    def test_last_page_has_the_remainder(self):
        page3 = re.findall(r'batch-card-name">([^<]+)</h2>', self.client.get('/batch/?page=3').content.decode())
        self.assertEqual(len(page3), 15)  # 95 - 40 - 40

    def test_pagination_status_shows_total_count(self):
        html = self.client.get('/batch/').content.decode()
        self.assertIn('Page 1 of 3', html)
        self.assertIn('95 batches', html)

    def test_deleting_a_card_pulls_the_next_page_forward_on_reload(self):
        # Regression: batch.js used to just remove the deleted card's DOM
        # node, leaving page 1 with 39 cards instead of pulling page 2's
        # first card into the vacated slot. It now re-fetches the current
        # page after a successful delete instead — this test covers the
        # server-side half that makes that re-fetch actually work: deleting
        # one of the 40 on page 1 must still return a full 40 (39 remaining
        # + 1 pulled forward from what was page 2), not 39.
        first_batch = Batch.objects.order_by('-created_at')[0]
        response = self.client.post(f'/batch/{first_batch.slug}/delete/')
        self.assertEqual(response.status_code, 200)

        html = self.client.get('/batch/').content.decode()
        page1 = re.findall(r'batch-card-name">([^<]+)</h2>', html)
        self.assertEqual(len(page1), 40)
        self.assertNotIn(first_batch.name, page1)
        self.assertIn('94 batches', html)


class BatchNameSearchTests(TestCase):
    """The batch list page's search bar (templates/partials/search_bar.html,
    included from batch.html) filters by Batch.name — added alongside the
    home page's vehicle-number search, reusing the same server-side
    filter-then-paginate approach and the same initDateSearchFilter() JS
    (in search-only mode, since batch.html has no date filter)."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='batchsearch', password='pw12345!Strong')
        for name in ('Morning Dispatch', 'Evening Dispatch', 'Customer X Orders'):
            Batch.objects.create(name=name)

    def setUp(self):
        self.client.force_login(self.user)

    def test_search_matches_by_partial_case_insensitive_name(self):
        html = self.client.get('/batch/?q=dispatch').content.decode()
        cards = re.findall(r'batch-card-name">([^<]+)</h2>', html)
        self.assertEqual(set(cards), {'Morning Dispatch', 'Evening Dispatch'})

    def test_search_excludes_non_matching_batches(self):
        html = self.client.get('/batch/?q=dispatch').content.decode()
        self.assertNotIn('Customer X Orders', html)

    def test_no_match_shows_filtered_empty_message(self):
        html = self.client.get('/batch/?q=nonexistent').content.decode()
        self.assertIn('No matching batches.', html)
        self.assertNotIn('Select multiple entries on the Home page', html)

    def test_unfiltered_empty_state_keeps_the_original_message(self):
        Batch.objects.all().delete()
        html = self.client.get('/batch/').content.decode()
        self.assertIn('Select multiple entries on the Home page and click Group to create one.', html)

    def test_search_bar_appears_right_below_the_heading(self):
        html = self.client.get('/batch/').content.decode()
        page_header_idx = html.index('<h1 class="page-title">Batches</h1>')
        search_bar_idx = html.index('id="entry-search-input"')
        grid_idx = html.index('class="batch-grid"')
        self.assertTrue(page_header_idx < search_bar_idx < grid_idx)


class CheckUsernameRateLimitTests(TestCase):
    """check_username (recorder/views.py) is unauthenticated (runs
    pre-login, used by the Forgot Password flow) and would otherwise be an
    unthrottled username-enumeration oracle — rate-limited per-IP
    (CHECK_USERNAME_MAX_ATTEMPTS within CHECK_USERNAME_ATTEMPTS_TTL_SECONDS)."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='ratelimituser', password='pw12345!Strong')

    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_requests_within_the_cap_still_resolve_normally(self):
        for _ in range(CHECK_USERNAME_MAX_ATTEMPTS):
            response = self.client.post('/forgot-password/check-username/', {'username': 'ratelimituser'})
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()['valid'])

    def test_requests_beyond_the_cap_are_throttled(self):
        for _ in range(CHECK_USERNAME_MAX_ATTEMPTS):
            self.client.post('/forgot-password/check-username/', {'username': 'ratelimituser'})
        # Even a genuinely valid username is now rejected — proving the
        # throttle itself, not a real lookup miss, is what's blocking this.
        response = self.client.post('/forgot-password/check-username/', {'username': 'ratelimituser'})
        self.assertEqual(response.status_code, 429)
        self.assertFalse(response.json()['valid'])


class ForgotPasswordEmailGuessRateLimitTests(TestCase):
    """forgot_password_request_otp's wrong-email branch is throttled the
    same way OTP verification already is (FORGOT_PASSWORD_EMAIL_MAX_ATTEMPTS
    within FORGOT_PASSWORD_EMAIL_ATTEMPTS_TTL_SECONDS), keyed by user.pk —
    otherwise a known username's registered email could be brute-forced
    unauthenticated with no limit, since the cooldown in _send_otp_email is
    only ever reached after a correct email match."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username='emailguesstarget', password='pw12345!Strong', email='real@example.com',
        )

    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_wrong_email_guess_returns_the_generic_error(self):
        response = self.client.post(
            '/forgot-password/request-otp/', {'username': 'emailguesstarget', 'email': 'wrong@example.com'},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Enter Correct Email')

    def test_guesses_beyond_the_cap_are_throttled_with_the_same_error(self):
        for _ in range(FORGOT_PASSWORD_EMAIL_MAX_ATTEMPTS):
            self.client.post(
                '/forgot-password/request-otp/', {'username': 'emailguesstarget', 'email': 'wrong@example.com'},
            )
        # Even the *correct* email is now rejected with the exact same
        # generic error — proving the throttle, not just another wrong
        # guess, is what's blocking this, and that it can't be told apart
        # from a mismatch by the response.
        response = self.client.post(
            '/forgot-password/request-otp/', {'username': 'emailguesstarget', 'email': 'real@example.com'},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'Enter Correct Email')


class LoginLockoutTests(TestCase):
    """ThrottledLoginView (recorder/views.py, wired in as the /login/ view
    in entryrecorder/urls.py) adds a minimal cache-backed lockout on top of
    Django's stock LoginView — LOGIN_MAX_ATTEMPTS wrong passwords within
    LOGIN_LOCKOUT_SECONDS locks out further attempts for that username,
    including a subsequent correct one, since this project has no
    django-axes or similar."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username='loginlockouttarget', password='CorrectHorse123!')

    def setUp(self):
        cache.clear()

    def tearDown(self):
        cache.clear()

    def test_correct_password_still_logs_in_under_the_cap(self):
        response = self.client.post('/login/', {'username': 'loginlockouttarget', 'password': 'CorrectHorse123!'})
        self.assertRedirects(response, '/')

    def test_locks_out_after_max_failed_attempts(self):
        for _ in range(LOGIN_MAX_ATTEMPTS):
            self.client.post('/login/', {'username': 'loginlockouttarget', 'password': 'wrong'})

        # Even the correct password is now rejected while locked out: no
        # redirect (a real login always redirects to LOGIN_REDIRECT_URL) and
        # the session stays unauthenticated. login.html now surfaces the
        # lockout's own distinct message rather than the generic "didn't
        # match" text used for an ordinary wrong password.
        response = self.client.post('/login/', {'username': 'loginlockouttarget', 'password': 'CorrectHorse123!'})
        self.assertEqual(response.status_code, 200)  # re-rendered login form, not a redirect
        self.assertFalse(response.wsgi_request.user.is_authenticated)
        self.assertContains(response, 'Too many failed login attempts')

    def test_a_successful_login_clears_the_attempt_counter(self):
        self.client.post('/login/', {'username': 'loginlockouttarget', 'password': 'wrong'})
        response = self.client.post('/login/', {'username': 'loginlockouttarget', 'password': 'CorrectHorse123!'})
        self.assertRedirects(response, '/')
