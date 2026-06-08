"""Backend tests for the PNC Induction Portal — Phase 3 admin routes.

Covers /api/admin/* with HTTP Basic Auth:
- /api/admin/employees (list, search/filter)
- /api/admin/employees.csv (export with UTF-8 BOM)
- /api/admin/employees/{id}/review (PATCH)
- Idempotency: finalize after PATCH must NOT overwrite review_status.
"""
from __future__ import annotations

import os
from urllib.parse import urlencode

import pytest
import requests

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL",
    "https://induct-pro.preview.emergentagent.com",
).rstrip("/")

ADMIN_USER = "pnc-admin"
ADMIN_PASS = "7o0nSzhqwvS6lBfjwqqRnGOwmI8"
EXISTING_EMPLOYEE_ID = "0EApcMofHgM1BpaqraJQ"
NONEXISTENT_EMPLOYEE_ID = "no-such-employee-zzz"
TIMEOUT = 60

# CSV header mirror — kept in sync with /app/backend/admin_routes.py CSV_SCHEMA.
# This mirrors PNC's existing subcontractor spreadsheet column order.
CSV_COLUMNS = [
    "Name", "Date Of Birth", "Address", "Post Code", "Phone Number",
    "Email Address", "NI Number",
    "Induction Status", "Medical Status",
    "Driving Licence", "Driving Licence Check", "Passport",
    "Right To Work", "Proof Of Bank",
    "Business Name", "Account Number", "Sort Code", "VAT Number", "UTR",
    "Review Status", "PDF Link",
    "Employee ID", "Submitted At",
]


@pytest.fixture(scope="module")
def admin_session():
    s = requests.Session()
    s.auth = (ADMIN_USER, ADMIN_PASS)
    return s


@pytest.fixture(scope="module")
def anon_session():
    return requests.Session()


def _finalize(employee_id: str = EXISTING_EMPLOYEE_ID) -> dict:
    r = requests.post(
        f"{BASE_URL}/api/induction/finalize",
        json={"employee_id": employee_id},
        timeout=TIMEOUT,
    )
    assert r.status_code == 200, r.text
    return r.json()


def _get_record(admin_session, employee_id: str = EXISTING_EMPLOYEE_ID) -> dict | None:
    r = admin_session.get(f"{BASE_URL}/api/admin/employees", timeout=TIMEOUT)
    assert r.status_code == 200, r.text
    body = r.json()
    for item in body.get("items", []):
        if item.get("employee_id") == employee_id:
            return item
    return None


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


class TestAuth:
    def test_no_auth_returns_401_with_basic_realm(self, anon_session):
        r = anon_session.get(f"{BASE_URL}/api/admin/employees", timeout=TIMEOUT)
        assert r.status_code == 401, r.text
        www_auth = r.headers.get("WWW-Authenticate", "")
        assert "Basic" in www_auth, www_auth
        assert 'realm="PNC Admin"' in www_auth, www_auth

    def test_wrong_credentials_returns_401(self):
        r = requests.get(
            f"{BASE_URL}/api/admin/employees",
            auth=("pnc-admin", "definitely-wrong"),
            timeout=TIMEOUT,
        )
        assert r.status_code == 401, r.text

    def test_correct_credentials_returns_200(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/employees", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        body = r.json()
        assert "count" in body and isinstance(body["count"], int)
        assert "items" in body and isinstance(body["items"], list)


# ---------------------------------------------------------------------------
# List endpoint shape
# ---------------------------------------------------------------------------


class TestListShape:
    @pytest.fixture(scope="class", autouse=True)
    def ensure_finalized(self):
        # Make sure there is at least one summary doc.
        _finalize()

    def test_items_contain_required_keys(self, admin_session):
        rec = _get_record(admin_session)
        assert rec is not None, "Test employee summary not present in /api/admin/employees"
        for key in ("review_status", "missing_documents", "completed_modules",
                    "pdf_url", "passport_url", "driving_licence_url",
                    "bank_proof_url", "signature_url"):
            assert key in rec, f"Missing key in admin record: {key}"
        assert isinstance(rec["missing_documents"], list)
        assert isinstance(rec["completed_modules"], list)

    def test_missing_documents_exact_for_test_employee(self, admin_session):
        rec = _get_record(admin_session)
        # Test employee chose 'pnc' coverage so insurance_certificate is NOT required.
        assert rec["missing_documents"] == [
            "passport", "driving_licence", "bank_proof", "signature"
        ], rec["missing_documents"]

    def test_completed_modules_is_induction(self, admin_session):
        rec = _get_record(admin_session)
        assert rec["completed_modules"] == ["induction"], rec["completed_modules"]


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------


class TestCsvExport:
    @pytest.fixture(scope="class", autouse=True)
    def ensure_finalized(self):
        _finalize()

    def test_csv_headers_and_bom(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/employees.csv", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        ct = r.headers.get("Content-Type", "")
        assert "text/csv" in ct.lower(), ct
        assert "charset=utf-8" in ct.lower(), ct
        cd = r.headers.get("Content-Disposition", "")
        assert cd.startswith("attachment;"), cd
        assert 'filename="pnc-employees-' in cd, cd
        assert cd.endswith('.csv"'), cd

        # BOM check on raw bytes
        body = r.content
        assert body[:3] == b"\xef\xbb\xbf", f"Missing UTF-8 BOM, got: {body[:8]!r}"

        # First non-BOM line is the header
        text = body.decode("utf-8-sig")
        first_line = text.split("\r\n", 1)[0]
        # CRLF must be used
        assert "\r\n" in text, "CSV is not CRLF-terminated"
        header_cols = first_line.split(",")
        assert header_cols == CSV_COLUMNS, (
            f"Header mismatch. Got: {header_cols[:8]}... expected first: {CSV_COLUMNS[:8]}..."
        )

    def test_csv_list_cells_use_comma_space_and_no_literal_none(self, admin_session):
        r = admin_session.get(f"{BASE_URL}/api/admin/employees.csv", timeout=TIMEOUT)
        assert r.status_code == 200
        text = r.content.decode("utf-8-sig")
        lines = text.split("\r\n")
        header = lines[0].split(",")

        emp_idx = header.index("Employee ID")
        dvla_idx = header.index("Driving Licence Check")
        review_idx = header.index("Review Status")

        import csv as _csv
        reader = _csv.reader(lines[1:])
        row = None
        for r_ in reader:
            if not r_:
                continue
            if r_[emp_idx] == EXISTING_EMPLOYEE_ID:
                row = r_
                break
        assert row is not None, "Test employee row missing in CSV"

        # DVLA Licence Check value should be Yes/No (Title-cased), not "yes"/"no"
        assert row[dvla_idx] in {"Yes", "No", ""}, f"Bad DVLA value: {row[dvla_idx]!r}"
        # Review Status should be human-readable (e.g. "Pending Review")
        assert row[review_idx] in {"Pending Review", "Approved", "Rejected", ""}, \
            f"Bad review_status: {row[review_idx]!r}"

        # No literal 'None' in any cell
        for cell in row:
            assert cell != "None", f"Found literal None in row: {row}"


# ---------------------------------------------------------------------------
# Search / filter (AND-combined)
# ---------------------------------------------------------------------------


class TestSearch:
    @pytest.fixture(scope="class", autouse=True)
    def ensure_finalized(self):
        _finalize()

    def _get(self, admin_session, **params):
        url = f"{BASE_URL}/api/admin/employees?{urlencode(params)}"
        r = admin_session.get(url, timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        return r.json()

    def test_q_filter_matches_name(self, admin_session):
        body = self._get(admin_session, q="test")
        assert body["count"] >= 1, body

    def test_email_filter(self, admin_session):
        body = self._get(admin_session, email="new.hire")
        assert body["count"] >= 1, body

    def test_ni_filter(self, admin_session):
        body = self._get(admin_session, ni="TES")
        assert body["count"] >= 1, body

    def test_company_filter(self, admin_session):
        body = self._get(admin_session, company="Test")
        assert body["count"] >= 1, body

    def test_date_from_inclusive(self, admin_session):
        body = self._get(admin_session, date_from="2026-01-01")
        assert body["count"] >= 1, body

    def test_date_to_inclusive(self, admin_session):
        body = self._get(admin_session, date_to="2026-12-31")
        assert body["count"] >= 1, body

    def test_impossible_company_returns_zero(self, admin_session):
        body = self._get(admin_session, company="ZZZNoSuchCompany")
        assert body["count"] == 0, body

    def test_review_status_filter_after_finalize(self, admin_session):
        # Reset review_status to pending_review by PATCH first so the filter
        # is deterministic regardless of test order.
        requests.patch(
            f"{BASE_URL}/api/admin/employees/{EXISTING_EMPLOYEE_ID}/review",
            auth=(ADMIN_USER, ADMIN_PASS),
            json={"review_status": "pending_review", "review_note": "reset for test"},
            timeout=TIMEOUT,
        )
        _finalize()
        body = self._get(admin_session, review_status="pending_review")
        assert body["count"] >= 1
        # Our test employee should be in there
        assert any(it["employee_id"] == EXISTING_EMPLOYEE_ID for it in body["items"])


# ---------------------------------------------------------------------------
# PATCH review status
# ---------------------------------------------------------------------------


class TestPatchReview:
    def test_invalid_review_status_returns_422(self):
        r = requests.patch(
            f"{BASE_URL}/api/admin/employees/{EXISTING_EMPLOYEE_ID}/review",
            auth=(ADMIN_USER, ADMIN_PASS),
            json={"review_status": "in-progress"},
            timeout=TIMEOUT,
        )
        assert r.status_code == 422, r.text

    def test_nonexistent_employee_returns_404(self):
        r = requests.patch(
            f"{BASE_URL}/api/admin/employees/{NONEXISTENT_EMPLOYEE_ID}/review",
            auth=(ADMIN_USER, ADMIN_PASS),
            json={"review_status": "approved", "review_note": "test"},
            timeout=TIMEOUT,
        )
        assert r.status_code == 404, r.text
        assert r.json().get("detail") == "employee_summary not found"

    def test_patch_approves_and_persists(self, admin_session):
        # Ensure the doc exists
        _finalize()
        r = requests.patch(
            f"{BASE_URL}/api/admin/employees/{EXISTING_EMPLOYEE_ID}/review",
            auth=(ADMIN_USER, ADMIN_PASS),
            json={"review_status": "approved", "review_note": "OK"},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["employee_id"] == EXISTING_EMPLOYEE_ID
        assert body["review_status"] == "approved"

        rec = _get_record(admin_session)
        assert rec is not None
        assert rec["review_status"] == "approved"
        assert rec.get("review_note") == "OK"


# ---------------------------------------------------------------------------
# IDEMPOTENCY (most important new behaviour):
# PATCH approved -> POST finalize -> review_status MUST remain 'approved'.
# ---------------------------------------------------------------------------


class TestFinalizePreservesReviewStatus:
    def test_finalize_does_not_overwrite_review_status(self, admin_session):
        # Step 1: PATCH to approved
        r = requests.patch(
            f"{BASE_URL}/api/admin/employees/{EXISTING_EMPLOYEE_ID}/review",
            auth=(ADMIN_USER, ADMIN_PASS),
            json={"review_status": "approved", "review_note": "idempotency test"},
            timeout=TIMEOUT,
        )
        assert r.status_code == 200, r.text

        rec = _get_record(admin_session)
        assert rec["review_status"] == "approved"

        # Step 2: re-run finalize
        _finalize()

        # Step 3: verify it is still approved (not reset to pending_review)
        rec2 = _get_record(admin_session)
        assert rec2 is not None
        assert rec2["review_status"] == "approved", (
            f"finalize overwrote review_status. Got: {rec2.get('review_status')!r}"
        )

    def test_first_time_finalize_sets_pending_review_code_path(self):
        """Code path verification (per review_request): we do NOT delete the
        real employee_summary doc. Read server.py to confirm the conditional
        used to seed review_status on first creation."""
        with open("/app/backend/server.py", "r", encoding="utf-8") as f:
            src = f.read()
        # Look for the guarded set: only set review_status if doc doesn't exist
        # or doesn't already have a review_status.
        normalised = src.replace("'", '"').replace(" ", "")
        needle = (
            'ifnotexisting_summary.existsornot(existing_summary.to_dict()or{}).get("review_status")'
        )
        assert needle in normalised, (
            "finalize_induction is missing the review_status preservation guard"
        )
        assert 'summary["review_status"] = "pending_review"' in src, (
            "finalize_induction must default new summaries to 'pending_review'"
        )


# ---------------------------------------------------------------------------
# Teardown: leave the test employee in a clean 'approved' state so subsequent
# test runs are deterministic. (We don't delete the doc per review_request.)
# ---------------------------------------------------------------------------


def teardown_module(module):
    try:
        requests.patch(
            f"{BASE_URL}/api/admin/employees/{EXISTING_EMPLOYEE_ID}/review",
            auth=(ADMIN_USER, ADMIN_PASS),
            json={"review_status": "approved", "review_note": "post-test cleanup"},
            timeout=TIMEOUT,
        )
    except Exception:
        pass
