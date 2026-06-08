"""Backend tests for the PNC Induction Portal — Phase 2.

Covers:
- /api/health
- /api/induction/finalize: success, 404, 422, idempotency, PDF reachability
- Ingress routing: /induction/finalize (no /api) should not reach FastAPI
"""
from __future__ import annotations

import os
import re
from urllib.parse import parse_qs, urlparse

import pytest
import requests

BASE_URL = os.environ.get(
    "REACT_APP_BACKEND_URL",
    "https://induct-pro.preview.emergentagent.com",
).rstrip("/")

EXISTING_EMPLOYEE_ID = "0EApcMofHgM1BpaqraJQ"
NONEXISTENT_EMPLOYEE_ID = "this-does-not-exist-xyz"

# Reasonable timeouts: PDF gen + Storage upload + Firestore writes can take a few seconds.
TIMEOUT = 60


@pytest.fixture(scope="module")
def http() -> requests.Session:
    s = requests.Session()
    s.headers.update({"Content-Type": "application/json"})
    return s


# ---------------------------------------------------------------------------
# /api/health
# ---------------------------------------------------------------------------


class TestHealth:
    def test_health_returns_ok(self, http: requests.Session):
        r = http.get(f"{BASE_URL}/api/health", timeout=TIMEOUT)
        assert r.status_code == 200, r.text
        body = r.json()
        assert body == {"status": "ok", "service": "pnc-induction-api"}


# ---------------------------------------------------------------------------
# /api/induction/finalize — success path
# ---------------------------------------------------------------------------


class TestFinalizeSuccess:
    @pytest.fixture(scope="class")
    def finalize_response(self, http: requests.Session):
        r = http.post(
            f"{BASE_URL}/api/induction/finalize",
            json={"employee_id": EXISTING_EMPLOYEE_ID},
            timeout=TIMEOUT,
        )
        return r

    def test_status_code_200(self, finalize_response):
        assert finalize_response.status_code == 200, finalize_response.text

    def test_response_shape(self, finalize_response):
        body = finalize_response.json()
        assert body["employee_id"] == EXISTING_EMPLOYEE_ID
        assert body["employee_summary_id"] == EXISTING_EMPLOYEE_ID
        assert "pdf_url" in body and isinstance(body["pdf_url"], str)
        assert "generated_at" in body
        # ISO 8601 timestamp
        assert re.match(
            r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}", body["generated_at"]
        ), body["generated_at"]

    def test_pdf_url_is_firebase_storage_with_token(self, finalize_response):
        url = finalize_response.json()["pdf_url"]
        parsed = urlparse(url)
        assert parsed.scheme == "https"
        assert parsed.netloc == "firebasestorage.googleapis.com", url
        qs = parse_qs(parsed.query)
        assert qs.get("alt") == ["media"], url
        assert "token" in qs and len(qs["token"][0]) > 0, url

    def test_pdf_url_downloads_valid_pdf(self, finalize_response):
        url = finalize_response.json()["pdf_url"]
        r = requests.get(url, timeout=TIMEOUT)
        assert r.status_code == 200, f"PDF not reachable: {r.status_code}"
        ct = r.headers.get("Content-Type", "")
        assert "application/pdf" in ct.lower() or "pdf" in ct.lower(), ct
        assert r.content[:4] == b"%PDF", "Body does not start with %PDF"
        assert len(r.content) >= 4 * 1024, f"PDF too small: {len(r.content)} bytes"


# ---------------------------------------------------------------------------
# /api/induction/finalize — error paths
# ---------------------------------------------------------------------------


class TestFinalizeErrors:
    def test_nonexistent_employee_returns_404(self, http: requests.Session):
        r = http.post(
            f"{BASE_URL}/api/induction/finalize",
            json={"employee_id": NONEXISTENT_EMPLOYEE_ID},
            timeout=TIMEOUT,
        )
        assert r.status_code == 404, r.text
        body = r.json()
        assert body.get("detail") == "Employee not found"

    def test_missing_employee_id_returns_422(self, http: requests.Session):
        r = http.post(
            f"{BASE_URL}/api/induction/finalize",
            json={},
            timeout=TIMEOUT,
        )
        assert r.status_code == 422, r.text

    def test_empty_employee_id_returns_422(self, http: requests.Session):
        # min_length=1 => pydantic should reject empty string
        r = http.post(
            f"{BASE_URL}/api/induction/finalize",
            json={"employee_id": ""},
            timeout=TIMEOUT,
        )
        assert r.status_code in (400, 422), r.text


# ---------------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------------


class TestFinalizeIdempotency:
    def test_double_finalize_succeeds_and_token_rotates(self, http: requests.Session):
        r1 = http.post(
            f"{BASE_URL}/api/induction/finalize",
            json={"employee_id": EXISTING_EMPLOYEE_ID},
            timeout=TIMEOUT,
        )
        assert r1.status_code == 200, r1.text
        url1 = r1.json()["pdf_url"]

        r2 = http.post(
            f"{BASE_URL}/api/induction/finalize",
            json={"employee_id": EXISTING_EMPLOYEE_ID},
            timeout=TIMEOUT,
        )
        assert r2.status_code == 200, r2.text
        url2 = r2.json()["pdf_url"]

        # Same storage path; tokens differ
        p1 = urlparse(url1)
        p2 = urlparse(url2)
        assert p1.path == p2.path, f"Path changed: {p1.path} vs {p2.path}"
        t1 = parse_qs(p1.query).get("token", [""])[0]
        t2 = parse_qs(p2.query).get("token", [""])[0]
        assert t1 and t2 and t1 != t2, "Token should be rotated on each upload"

        # New URL still resolves to a real PDF
        r = requests.get(url2, timeout=TIMEOUT)
        assert r.status_code == 200
        assert r.content[:4] == b"%PDF"


# ---------------------------------------------------------------------------
# Ingress routing — /induction/finalize without /api should NOT reach FastAPI
# ---------------------------------------------------------------------------


class TestIngressPrefix:
    def test_no_api_prefix_does_not_reach_fastapi(self, http: requests.Session):
        r = http.post(
            f"{BASE_URL}/induction/finalize",
            json={"employee_id": EXISTING_EMPLOYEE_ID},
            timeout=TIMEOUT,
        )
        # K8s ingress only forwards /api/* to the backend. The unprefixed path
        # should be served by the frontend (HTML) or return a non-FastAPI response.
        # In particular it must NOT match the FastAPI route (which would return 200
        # with a JSON body containing pdf_url).
        if r.status_code == 200:
            ct = r.headers.get("Content-Type", "").lower()
            assert "application/json" not in ct or "pdf_url" not in r.text, (
                "Unprefixed /induction/finalize unexpectedly reached FastAPI: "
                f"{r.status_code} {ct} {r.text[:200]}"
            )
        else:
            # Any non-200 is fine — confirms it didn't reach the FastAPI handler
            assert r.status_code != 200
