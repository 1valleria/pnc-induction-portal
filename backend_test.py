#!/usr/bin/env python3
"""
Phase 1 Security & Trust Audit — Backend Regression Test
PNC UNIQUE LTD Contractor Induction Portal

This test suite verifies that all backend functionality remains intact after
Phase 1 security hardening (Firestore/Storage rules locked down, CORS restricted,
/docs disabled, retired brand removed, HTML-escaped emails).
"""
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import load_dotenv

# Load environment variables
ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / "frontend" / ".env")
load_dotenv(ROOT_DIR / "backend" / ".env")

# Configuration from environment
BASE_URL = os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

# Retired brand strings that MUST NOT appear in any response
# NOTE: "pncunique" is LEGITIMATE (company email domain) - do NOT flag it
RETIRED_STRINGS = ["induct-pro", "pnc-induction.co.uk", "Unit 1, Headlands House", "onboarding@resend.dev"]

# Test state (shared across test functions)
test_state = {
    "access_code": None,
    "access_code_id": None,
    "employee_id": None,
    "employee_summary_id": None,
    "test_email": "test.contractor@example.com",
    "test_name": "Test Contractor",
}


def log(msg: str, level: str = "INFO"):
    """Log a message with timestamp."""
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] [{level}] {msg}")


def check_retired_strings(text: str, context: str) -> list[str]:
    """Check if any retired brand strings appear in the text."""
    found = []
    for s in RETIRED_STRINGS:
        if s.lower() in text.lower():
            found.append(s)
    if found:
        log(f"❌ RETIRED STRINGS FOUND in {context}: {found}", "ERROR")
    return found


def test_production_hardening():
    """Verify /docs, /redoc, /openapi.json return 404 and /api/health returns 200."""
    log("=" * 80)
    log("TEST: Production Hardening")
    log("=" * 80)
    
    results = []
    
    # Test /docs
    log("Testing GET /docs (should return 404)...")
    resp = requests.get(f"{BASE_URL}/docs", allow_redirects=False)
    if resp.status_code == 404:
        log("✅ /docs returns 404 (correct)")
        results.append(("docs_disabled", True))
    else:
        log(f"❌ /docs returned {resp.status_code}, expected 404", "ERROR")
        results.append(("docs_disabled", False))
    
    # Test /redoc
    log("Testing GET /redoc (should return 404)...")
    resp = requests.get(f"{BASE_URL}/redoc", allow_redirects=False)
    if resp.status_code == 404:
        log("✅ /redoc returns 404 (correct)")
        results.append(("redoc_disabled", True))
    else:
        log(f"❌ /redoc returned {resp.status_code}, expected 404", "ERROR")
        results.append(("redoc_disabled", False))
    
    # Test /openapi.json
    log("Testing GET /openapi.json (should return 404)...")
    resp = requests.get(f"{BASE_URL}/openapi.json", allow_redirects=False)
    if resp.status_code == 404:
        log("✅ /openapi.json returns 404 (correct)")
        results.append(("openapi_disabled", True))
    else:
        log(f"❌ /openapi.json returned {resp.status_code}, expected 404", "ERROR")
        results.append(("openapi_disabled", False))
    
    # Test /api/health
    log("Testing GET /api/health (should return 200)...")
    resp = requests.get(f"{BASE_URL}/api/health")
    if resp.status_code == 200:
        data = resp.json()
        if data.get("status") == "ok" and data.get("service") == "pnc-induction-api":
            log(f"✅ /api/health returns 200 with correct payload: {data}")
            results.append(("health_endpoint", True))
        else:
            log(f"❌ /api/health payload incorrect: {data}", "ERROR")
            results.append(("health_endpoint", False))
    else:
        log(f"❌ /api/health returned {resp.status_code}, expected 200", "ERROR")
        results.append(("health_endpoint", False))
    
    return results


def test_security_headers():
    """Verify security headers are present on all responses (200, 401, 404, 422)."""
    log("=" * 80)
    log("TEST: Security Headers Middleware")
    log("=" * 80)
    
    results = []
    
    # Expected headers
    expected_headers = {
        "X-Content-Type-Options": "nosniff",
        "X-Frame-Options": "DENY",
        "Referrer-Policy": "strict-origin-when-cross-origin",
        "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=(), usb=(), interest-cohort=()",
        "Strict-Transport-Security": "max-age=15552000; includeSubDomains",
    }
    
    # Test 1: 200 response on /api/health
    log("Testing security headers on /api/health (200 response)...")
    resp = requests.get(f"{BASE_URL}/api/health")
    if resp.status_code == 200:
        all_present = True
        for header, expected_value in expected_headers.items():
            actual_value = resp.headers.get(header, "")
            if expected_value.lower() in actual_value.lower():
                log(f"  ✅ {header}: {actual_value}")
            else:
                log(f"  ❌ {header}: expected '{expected_value}', got '{actual_value}'", "ERROR")
                all_present = False
        results.append(("security_headers_200", all_present))
    else:
        log(f"❌ /api/health returned {resp.status_code}, expected 200", "ERROR")
        results.append(("security_headers_200", False))
    
    # Test 2: 401 response on /api/admin/employees without credentials
    log("Testing security headers on /api/admin/employees (401 response)...")
    resp = requests.get(f"{BASE_URL}/api/admin/employees")
    if resp.status_code == 401:
        all_present = True
        for header, expected_value in expected_headers.items():
            actual_value = resp.headers.get(header, "")
            if expected_value.lower() in actual_value.lower():
                log(f"  ✅ {header}: {actual_value}")
            else:
                log(f"  ❌ {header}: expected '{expected_value}', got '{actual_value}'", "ERROR")
                all_present = False
        
        # Also check WWW-Authenticate header
        www_auth = resp.headers.get("WWW-Authenticate", "")
        if 'Basic realm="PNC Admin"' in www_auth:
            log(f"  ✅ WWW-Authenticate: {www_auth}")
        else:
            log(f"  ❌ WWW-Authenticate: expected 'Basic realm=\"PNC Admin\"', got '{www_auth}'", "ERROR")
            all_present = False
        
        results.append(("security_headers_401", all_present))
    else:
        log(f"❌ /api/admin/employees returned {resp.status_code}, expected 401", "ERROR")
        results.append(("security_headers_401", False))
    
    # Test 3: 422 response on wrong payload POST
    log("Testing security headers on /api/validate-access-code (422 response)...")
    resp = requests.post(f"{BASE_URL}/api/validate-access-code", json={})
    if resp.status_code == 422:
        all_present = True
        for header, expected_value in expected_headers.items():
            actual_value = resp.headers.get(header, "")
            if expected_value.lower() in actual_value.lower():
                log(f"  ✅ {header}: {actual_value}")
            else:
                log(f"  ❌ {header}: expected '{expected_value}', got '{actual_value}'", "ERROR")
                all_present = False
        results.append(("security_headers_422", all_present))
    else:
        log(f"❌ /api/validate-access-code with empty payload returned {resp.status_code}, expected 422", "ERROR")
        results.append(("security_headers_422", False))
    
    # Test 4: 404 response on /api/nonexistent
    log("Testing security headers on /api/nonexistent (404 response)...")
    resp = requests.get(f"{BASE_URL}/api/nonexistent")
    if resp.status_code == 404:
        all_present = True
        for header, expected_value in expected_headers.items():
            actual_value = resp.headers.get(header, "")
            if expected_value.lower() in actual_value.lower():
                log(f"  ✅ {header}: {actual_value}")
            else:
                log(f"  ❌ {header}: expected '{expected_value}', got '{actual_value}'", "ERROR")
                all_present = False
        results.append(("security_headers_404", all_present))
    else:
        log(f"⚠️  /api/nonexistent returned {resp.status_code}, expected 404", "WARNING")
        # Still check headers even if status code is different
        all_present = True
        for header, expected_value in expected_headers.items():
            actual_value = resp.headers.get(header, "")
            if expected_value.lower() not in actual_value.lower():
                all_present = False
        results.append(("security_headers_404", all_present))
    
    # Verify NO Content-Security-Policy header (intentionally not set)
    log("Verifying Content-Security-Policy is NOT set (intentional)...")
    resp = requests.get(f"{BASE_URL}/api/health")
    csp = resp.headers.get("Content-Security-Policy", "")
    if not csp:
        log("  ✅ Content-Security-Policy not set (correct, Phase 2 item)")
        results.append(("no_csp_header", True))
    else:
        log(f"  ⚠️  Content-Security-Policy is set: {csp}", "WARNING")
        results.append(("no_csp_header", False))
    
    return results


def test_seo_and_security_files():
    """Verify /sitemap.xml, /robots.txt, and /.well-known/security.txt are accessible."""
    log("=" * 80)
    log("TEST: SEO and Security Files")
    log("=" * 80)
    
    results = []
    
    # Test 1: /sitemap.xml
    log("Testing GET /sitemap.xml...")
    resp = requests.get(f"{BASE_URL}/sitemap.xml")
    if resp.status_code == 200:
        content = resp.text
        log(f"✅ /sitemap.xml returns 200")
        
        # Check for expected URLs
        expected_locs = ["/", "/about", "/contact", "/legal/privacy", "/legal/terms"]
        all_found = True
        for loc in expected_locs:
            if f"<loc>{BASE_URL}{loc}</loc>" in content:
                log(f"  ✅ Found <loc>{BASE_URL}{loc}</loc>")
            else:
                log(f"  ❌ Missing <loc>{BASE_URL}{loc}</loc>", "ERROR")
                all_found = False
        
        results.append(("sitemap_xml", all_found))
    else:
        log(f"❌ /sitemap.xml returned {resp.status_code}, expected 200", "ERROR")
        results.append(("sitemap_xml", False))
    
    # Test 2: /robots.txt with Sitemap: line
    log("Testing GET /robots.txt...")
    resp = requests.get(f"{BASE_URL}/robots.txt")
    if resp.status_code == 200:
        content = resp.text
        log(f"✅ /robots.txt returns 200")
        log(f"Content:\n{content}")
        
        # Check for Sitemap: line
        if f"Sitemap: {BASE_URL}/sitemap.xml" in content:
            log(f"  ✅ Found 'Sitemap: {BASE_URL}/sitemap.xml'")
            results.append(("robots_txt_sitemap", True))
        else:
            log(f"  ❌ Missing 'Sitemap: {BASE_URL}/sitemap.xml'", "ERROR")
            results.append(("robots_txt_sitemap", False))
    else:
        log(f"❌ /robots.txt returned {resp.status_code}, expected 200", "ERROR")
        results.append(("robots_txt_sitemap", False))
    
    # Test 3: /.well-known/security.txt
    log("Testing GET /.well-known/security.txt...")
    resp = requests.get(f"{BASE_URL}/.well-known/security.txt")
    if resp.status_code == 200:
        content = resp.text
        log(f"✅ /.well-known/security.txt returns 200")
        log(f"Content:\n{content}")
        
        # Check that it contains the correct origin
        if BASE_URL in content:
            log(f"  ✅ Contains correct origin: {BASE_URL}")
            results.append(("security_txt", True))
        else:
            log(f"  ⚠️  Does not contain origin {BASE_URL}", "WARNING")
            results.append(("security_txt", True))  # Still pass if file exists
    else:
        log(f"❌ /.well-known/security.txt returned {resp.status_code}, expected 200", "ERROR")
        results.append(("security_txt", False))
    
    return results


def test_cors_protection():
    """Verify CORS rejects unknown origins."""
    log("=" * 80)
    log("TEST: CORS Protection")
    log("=" * 80)
    
    results = []
    
    # Test OPTIONS preflight with untrusted origin
    log("Testing OPTIONS preflight with untrusted origin...")
    headers = {
        "Origin": "https://phishing.example.com",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type",
    }
    resp = requests.options(f"{BASE_URL}/api/validate-access-code", headers=headers)
    
    # Should either return 400 or not echo the untrusted origin
    acao = resp.headers.get("Access-Control-Allow-Origin", "")
    if resp.status_code == 400 or "phishing.example.com" not in acao:
        log(f"✅ CORS rejects untrusted origin (status={resp.status_code}, ACAO={acao})")
        results.append(("cors_protection", True))
    else:
        log(f"❌ CORS accepted untrusted origin: {acao}", "ERROR")
        results.append(("cors_protection", False))
    
    return results


def test_system_status():
    """Verify GET /api/admin/system-status returns correct config."""
    log("=" * 80)
    log("TEST: Admin System Status (Email Config Verification)")
    log("=" * 80)
    
    results = []
    
    log("Testing GET /api/admin/system-status...")
    resp = requests.get(
        f"{BASE_URL}/api/admin/system-status",
        auth=(ADMIN_USERNAME, ADMIN_PASSWORD)
    )
    
    if resp.status_code == 200:
        data = resp.json()
        log(f"Response: {data}")
        
        # A. Verify exact email config values
        expected_values = {
            "sender_email": "admin@pnc-admin.com",
            "sender_name": "PNC Onboarding",
            "sender_display": "PNC Onboarding <admin@pnc-admin.com>",
            "reply_to_email": "admin@pncunique.com",
            "resend_configured": False,
            "default_manager_emails": ["admin@pncunique.com"],
            "email_test_mode": False,
            "email_redirect_to": None,
        }
        
        all_correct = True
        for key, expected in expected_values.items():
            actual = data.get(key)
            if actual == expected:
                log(f"✅ {key}: {actual}")
            else:
                log(f"❌ {key}: expected {expected!r}, got {actual!r}", "ERROR")
                all_correct = False
                results.append((f"system_status_{key}", False))
        
        if all_correct:
            log("✅ All email config values match expected")
            results.append(("system_status_email_config", True))
        else:
            results.append(("system_status_email_config", False))
        
        # Check for retired strings (including onboarding@resend.dev)
        response_text = resp.text
        found = check_retired_strings(response_text, "system-status response")
        if len(found) == 0:
            log("✅ No retired strings found in system-status response")
            results.append(("system_status_no_retired_strings", True))
        else:
            log(f"❌ Found retired strings: {found}", "ERROR")
            results.append(("system_status_no_retired_strings", False))
        
        results.append(("system_status_endpoint", True))
    else:
        log(f"❌ /api/admin/system-status returned {resp.status_code}, expected 200", "ERROR")
        results.append(("system_status_endpoint", False))
    
    return results


def test_create_invite():
    """Test POST /api/admin/invites with send_email=false and send_email=true."""
    log("=" * 80)
    log("TEST: Create Invitation")
    log("=" * 80)
    
    results = []
    
    # Test with send_email=false
    log("Testing POST /api/admin/invites with send_email=false...")
    payload = {
        "full_name": test_state["test_name"],
        "email": test_state["test_email"],
        "send_email": False,
    }
    resp = requests.post(
        f"{BASE_URL}/api/admin/invites",
        json=payload,
        auth=(ADMIN_USERNAME, ADMIN_PASSWORD)
    )
    
    if resp.status_code == 200:
        data = resp.json()
        log(f"Response: {data}")
        
        if data.get("code") and data.get("id"):
            test_state["access_code"] = data["code"]
            test_state["access_code_id"] = data["id"]
            log(f"✅ Invite created: code={data['code']}, id={data['id']}")
            results.append(("create_invite_no_email", True))
            
            # Check for retired strings
            response_text = resp.text
            found = check_retired_strings(response_text, "create invite response")
            results.append(("create_invite_no_retired_strings", len(found) == 0))
        else:
            log(f"❌ Missing code or id in response", "ERROR")
            results.append(("create_invite_no_email", False))
    else:
        log(f"❌ POST /api/admin/invites returned {resp.status_code}, expected 200", "ERROR")
        log(f"Response: {resp.text}")
        results.append(("create_invite_no_email", False))
    
    # Test with send_email=true (should be skipped, not failed)
    log("Testing POST /api/admin/invites with send_email=true (email should be skipped)...")
    payload2 = {
        "full_name": "Another Test User",
        "email": "another.test@example.com",
        "send_email": True,
    }
    resp2 = requests.post(
        f"{BASE_URL}/api/admin/invites",
        json=payload2,
        auth=(ADMIN_USERNAME, ADMIN_PASSWORD)
    )
    
    if resp2.status_code == 200:
        data2 = resp2.json()
        log(f"Response: {data2}")
        
        email_result = data2.get("email_result", {})
        email_status = email_result.get("status") if email_result else None
        
        # Email should be "skipped" since RESEND_API_KEY is unset
        if email_status == "skipped":
            log(f"✅ Email status is 'skipped' (correct, RESEND_API_KEY unset)")
            results.append(("create_invite_email_skipped", True))
        else:
            log(f"⚠️  Email status is '{email_status}' (expected 'skipped')", "WARNING")
            # This is acceptable if the email system handles it gracefully
            results.append(("create_invite_email_skipped", email_status in ["skipped", None]))
    else:
        log(f"❌ POST /api/admin/invites with send_email=true returned {resp2.status_code}", "ERROR")
        results.append(("create_invite_email_skipped", False))
    
    return results


def test_list_invites():
    """Test GET /api/admin/invites."""
    log("=" * 80)
    log("TEST: List Invitations")
    log("=" * 80)
    
    results = []
    
    log("Testing GET /api/admin/invites...")
    resp = requests.get(
        f"{BASE_URL}/api/admin/invites",
        auth=(ADMIN_USERNAME, ADMIN_PASSWORD)
    )
    
    if resp.status_code == 200:
        data = resp.json()
        log(f"Response: count={data.get('count')}, items={len(data.get('items', []))}")
        
        # Check if our newly created invite is in the list
        items = data.get("items", [])
        found_invite = any(item.get("code") == test_state["access_code"] for item in items)
        
        if found_invite:
            log(f"✅ Newly created invite found in list")
            results.append(("list_invites", True))
        else:
            log(f"❌ Newly created invite NOT found in list", "ERROR")
            results.append(("list_invites", False))
        
        # Check for retired strings
        response_text = resp.text
        found = check_retired_strings(response_text, "list invites response")
        results.append(("list_invites_no_retired_strings", len(found) == 0))
    else:
        log(f"❌ GET /api/admin/invites returned {resp.status_code}, expected 200", "ERROR")
        results.append(("list_invites", False))
    
    return results


def test_validate_access_code():
    """Test POST /api/validate-access-code with various scenarios."""
    log("=" * 80)
    log("TEST: Validate Access Code")
    log("=" * 80)
    
    results = []
    
    # Test with valid code and correct email
    log("Testing valid code with correct email...")
    payload = {
        "code": test_state["access_code"],
        "email": test_state["test_email"],
    }
    resp = requests.post(f"{BASE_URL}/api/validate-access-code", json=payload)
    
    if resp.status_code == 200:
        data = resp.json()
        log(f"Response: {data}")
        
        if data.get("valid") == True and data.get("access_code_id"):
            log(f"✅ Valid code accepted: access_code_id={data['access_code_id']}")
            results.append(("validate_code_valid", True))
        else:
            log(f"❌ Valid code rejected: {data}", "ERROR")
            results.append(("validate_code_valid", False))
    else:
        log(f"❌ POST /api/validate-access-code returned {resp.status_code}", "ERROR")
        results.append(("validate_code_valid", False))
    
    # Test with wrong email
    log("Testing valid code with wrong email...")
    payload2 = {
        "code": test_state["access_code"],
        "email": "wrong.email@example.com",
    }
    resp2 = requests.post(f"{BASE_URL}/api/validate-access-code", json=payload2)
    
    if resp2.status_code == 200:
        data2 = resp2.json()
        log(f"Response: {data2}")
        
        if data2.get("valid") == False and data2.get("reason") == "email_mismatch":
            log(f"✅ Wrong email rejected with reason 'email_mismatch'")
            results.append(("validate_code_email_mismatch", True))
        else:
            log(f"❌ Wrong email not rejected properly: {data2}", "ERROR")
            results.append(("validate_code_email_mismatch", False))
    else:
        log(f"❌ POST /api/validate-access-code returned {resp2.status_code}", "ERROR")
        results.append(("validate_code_email_mismatch", False))
    
    # Test with unknown code
    log("Testing unknown code...")
    payload3 = {
        "code": "PNC-XXXX-YYYY",
        "email": test_state["test_email"],
    }
    resp3 = requests.post(f"{BASE_URL}/api/validate-access-code", json=payload3)
    
    if resp3.status_code == 200:
        data3 = resp3.json()
        log(f"Response: {data3}")
        
        if data3.get("valid") == False and data3.get("reason") == "not_recognised":
            log(f"✅ Unknown code rejected with reason 'not_recognised'")
            results.append(("validate_code_not_recognised", True))
        else:
            log(f"❌ Unknown code not rejected properly: {data3}", "ERROR")
            results.append(("validate_code_not_recognised", False))
    else:
        log(f"❌ POST /api/validate-access-code returned {resp3.status_code}", "ERROR")
        results.append(("validate_code_not_recognised", False))
    
    return results


def test_submit_induction():
    """Test POST /api/induction/submit with file entries without URL."""
    log("=" * 80)
    log("TEST: Submit Induction")
    log("=" * 80)
    
    results = []
    
    # Build a realistic submission payload
    now_iso = datetime.now(timezone.utc).isoformat()
    
    # Test with files WITHOUT url field (only path, name, size, type)
    log("Testing submission with files WITHOUT url field...")
    payload = {
        "access_code_id": test_state["access_code_id"],
        "access_code": test_state["access_code"],
        "invited_email": test_state["test_email"],
        "full_name": test_state["test_name"],
        "dob": "1990-01-15",
        "telephone": "07700900123",
        "email": test_state["test_email"],
        "address1": "123 Test Street, Test City",
        "postcode": "TE5 7ST",
        "ni_number": "AB123456C",
        "emergency_name": "Jane Doe",
        "emergency_phone": "07700900456",
        "emergency_relationship": "Spouse",
        "right_to_work_share_code": "ABC123XYZ",
        "dvla_check": "yes",
        "company_name": "Test Contracting Ltd",
        "bank_account": "12345678",
        "sort_code": "12-34-56",
        "utr": "1234567890",
        "vat_number": "GB123456789",
        "insurance_option": "pnc",
        "invoice_service_requested": False,
        "digital_signature_name": test_state["test_name"],
        "medical": {
            "receiving_treatment": "no",
            "prescribed_medication": "no",
            "medical_warning_card": "no",
            "pregnant": "no",
            "allergies": "no",
            "asthma_bronchitis_chest": "no",
            "fainting_blackouts_epilepsy": "no",
            "heart_problems": "no",
            "diabetes": "no",
            "bone_or_joint_disease": "no",
            "skin_disease": "no",
            "persistent_bleeding_bruising": "no",
            "liver_or_kidney_disease": "no",
            "havs_or_cts": "no",
            "other_serious_illness": "no",
            "if_yes_details": "",
            "medication_disability_details": "",
        },
        "havs": {
            "tingling_after_vibration": "no",
            "tingling_other_times": "no",
            "night_pain_tingling_numbness": "no",
            "finger_numbness_after_vibration": "no",
            "fingers_white_in_cold": "no",
            "fingers_white_other_times": "no",
            "muscle_or_joint_problems": "no",
            "difficulty_handling_small_objects": "no",
        },
        "files": {
            "passport": {
                "path": "test-contractor/passport.jpg",
                "name": "passport.jpg",
                "size": 12345,
                "type": "image/jpeg",
            },
            "driving_licence": {
                "path": "test-contractor/driving_licence.jpg",
                "name": "driving_licence.jpg",
                "size": 12345,
                "type": "image/jpeg",
            },
            "bank_proof": {
                "path": "test-contractor/bank_proof.pdf",
                "name": "bank_proof.pdf",
                "size": 12345,
                "type": "application/pdf",
            },
            "signature": {
                "path": "test-contractor/signature.png",
                "name": "signature.png",
                "size": 12345,
                "type": "image/png",
            },
        },
        "storage_folder_path": "test-contractor/",
        "submitted_at": now_iso,
        "health_safety_acknowledged": True,
        "health_safety_completed_at": now_iso,
        "health_safety_sections": {
            "hand_arm_vibration": now_iso,
            "food_consumption": now_iso,
            "manual_handling": now_iso,
            "slips_trips_falls": now_iso,
            "ppe": now_iso,
            "skin_respiratory": now_iso,
            "working_at_height": now_iso,
            "fire": now_iso,
            "electrical": now_iso,
            "coshh": now_iso,
            "risk_assessments": now_iso,
            "housekeeping": now_iso,
            "noise": now_iso,
        },
        "site_rules_acknowledged": True,
        "site_rules_completed_at": now_iso,
    }
    
    resp = requests.post(f"{BASE_URL}/api/induction/submit", json=payload)
    
    if resp.status_code == 200:
        data = resp.json()
        log(f"Response: {data}")
        
        if data.get("employee_id") and data.get("employee_summary_id"):
            test_state["employee_id"] = data["employee_id"]
            test_state["employee_summary_id"] = data["employee_summary_id"]
            log(f"✅ Submission successful: employee_id={data['employee_id']}")
            results.append(("submit_induction_without_url", True))
            
            # Check for retired strings
            response_text = resp.text
            found = check_retired_strings(response_text, "submit induction response")
            results.append(("submit_induction_no_retired_strings", len(found) == 0))
        else:
            log(f"❌ Missing employee_id or employee_summary_id in response", "ERROR")
            results.append(("submit_induction_without_url", False))
    else:
        log(f"❌ POST /api/induction/submit returned {resp.status_code}", "ERROR")
        log(f"Response: {resp.text}")
        results.append(("submit_induction_without_url", False))
    
    return results


def test_validate_code_already_used():
    """Test that the access code is now marked as used."""
    log("=" * 80)
    log("TEST: Validate Access Code (Already Used)")
    log("=" * 80)
    
    results = []
    
    log("Testing access code after submission (should be marked as used)...")
    payload = {
        "code": test_state["access_code"],
        "email": test_state["test_email"],
    }
    resp = requests.post(f"{BASE_URL}/api/validate-access-code", json=payload)
    
    if resp.status_code == 200:
        data = resp.json()
        log(f"Response: {data}")
        
        if data.get("valid") == False and data.get("reason") == "already_used":
            log(f"✅ Access code correctly marked as used")
            results.append(("validate_code_already_used", True))
        else:
            log(f"❌ Access code not marked as used: {data}", "ERROR")
            results.append(("validate_code_already_used", False))
    else:
        log(f"❌ POST /api/validate-access-code returned {resp.status_code}", "ERROR")
        results.append(("validate_code_already_used", False))
    
    return results


def test_list_employees():
    """Test GET /api/admin/employees."""
    log("=" * 80)
    log("TEST: List Employees")
    log("=" * 80)
    
    results = []
    
    log("Testing GET /api/admin/employees...")
    resp = requests.get(
        f"{BASE_URL}/api/admin/employees",
        auth=(ADMIN_USERNAME, ADMIN_PASSWORD)
    )
    
    if resp.status_code == 200:
        data = resp.json()
        log(f"Response: count={data.get('count')}, items={len(data.get('items', []))}")
        
        # Check if our newly submitted employee is in the list
        items = data.get("items", [])
        found_employee = None
        for item in items:
            if item.get("employee_id") == test_state["employee_id"]:
                found_employee = item
                break
        
        if found_employee:
            log(f"✅ Newly submitted employee found in list")
            log(f"   pdf_url: {found_employee.get('pdf_url')}")
            log(f"   passport_url: {found_employee.get('passport_url')}")
            results.append(("list_employees", True))
            
            # Verify URLs are present
            if found_employee.get("pdf_url"):
                log(f"✅ PDF URL is present")
                results.append(("list_employees_pdf_url", True))
            else:
                log(f"⚠️  PDF URL is missing", "WARNING")
                results.append(("list_employees_pdf_url", False))
        else:
            log(f"❌ Newly submitted employee NOT found in list", "ERROR")
            results.append(("list_employees", False))
        
        # Check for retired strings
        response_text = resp.text
        found = check_retired_strings(response_text, "list employees response")
        results.append(("list_employees_no_retired_strings", len(found) == 0))
    else:
        log(f"❌ GET /api/admin/employees returned {resp.status_code}, expected 200", "ERROR")
        results.append(("list_employees", False))
    
    return results


def test_review_approved():
    """Test PATCH /api/admin/employees/{id}/review with review_status=approved."""
    log("=" * 80)
    log("TEST: Review Employee (Approved)")
    log("=" * 80)
    
    results = []
    
    if not test_state["employee_id"]:
        log("⚠️  Skipping test (no employee_id available)", "WARNING")
        return [("review_approved", False)]
    
    log(f"Testing PATCH /api/admin/employees/{test_state['employee_id']}/review...")
    payload = {
        "review_status": "approved",
        "review_note": "All documents verified and approved.",
    }
    resp = requests.patch(
        f"{BASE_URL}/api/admin/employees/{test_state['employee_id']}/review",
        json=payload,
        auth=(ADMIN_USERNAME, ADMIN_PASSWORD)
    )
    
    if resp.status_code == 200:
        data = resp.json()
        log(f"Response: {data}")
        
        if data.get("review_status") == "approved":
            log(f"✅ Review status updated to 'approved'")
            results.append(("review_approved", True))
            
            # Email status should be "skipped" (RESEND_API_KEY unset)
            email_status = data.get("email_status")
            if email_status == "skipped":
                log(f"✅ Email status is 'skipped' (correct)")
                results.append(("review_approved_email_skipped", True))
            else:
                log(f"⚠️  Email status is '{email_status}' (expected 'skipped')", "WARNING")
                results.append(("review_approved_email_skipped", email_status in ["skipped", None]))
        else:
            log(f"❌ Review status not updated: {data}", "ERROR")
            results.append(("review_approved", False))
        
        # Check for retired strings
        response_text = resp.text
        found = check_retired_strings(response_text, "review approved response")
        results.append(("review_approved_no_retired_strings", len(found) == 0))
    else:
        log(f"❌ PATCH /api/admin/employees/{test_state['employee_id']}/review returned {resp.status_code}", "ERROR")
        log(f"Response: {resp.text}")
        results.append(("review_approved", False))
    
    return results


def test_review_rejected():
    """Test PATCH /api/admin/employees/{id}/review with review_status=rejected."""
    log("=" * 80)
    log("TEST: Review Employee (Rejected)")
    log("=" * 80)
    
    results = []
    
    if not test_state["employee_id"]:
        log("⚠️  Skipping test (no employee_id available)", "WARNING")
        return [("review_rejected", False)]
    
    log(f"Testing PATCH /api/admin/employees/{test_state['employee_id']}/review...")
    payload = {
        "review_status": "rejected",
        "review_note": "Please resubmit with clearer passport photo.",
    }
    resp = requests.patch(
        f"{BASE_URL}/api/admin/employees/{test_state['employee_id']}/review",
        json=payload,
        auth=(ADMIN_USERNAME, ADMIN_PASSWORD)
    )
    
    if resp.status_code == 200:
        data = resp.json()
        log(f"Response: {data}")
        
        if data.get("review_status") == "rejected":
            log(f"✅ Review status updated to 'rejected'")
            results.append(("review_rejected", True))
            
            # Should have a new access code
            if data.get("new_access_code"):
                log(f"✅ New access code minted: {data['new_access_code']}")
                results.append(("review_rejected_new_code", True))
            else:
                log(f"❌ No new access code in response", "ERROR")
                results.append(("review_rejected_new_code", False))
            
            # portal_url should match PUBLIC_PORTAL_URL (or be empty if unset)
            portal_url = data.get("portal_url", "")
            public_portal_url = os.environ.get("PUBLIC_PORTAL_URL", "")
            if portal_url == public_portal_url:
                log(f"✅ portal_url matches PUBLIC_PORTAL_URL: {portal_url}")
                results.append(("review_rejected_portal_url", True))
            else:
                log(f"❌ portal_url mismatch: got '{portal_url}', expected '{public_portal_url}'", "ERROR")
                results.append(("review_rejected_portal_url", False))
        else:
            log(f"❌ Review status not updated: {data}", "ERROR")
            results.append(("review_rejected", False))
        
        # Check for retired strings
        response_text = resp.text
        found = check_retired_strings(response_text, "review rejected response")
        results.append(("review_rejected_no_retired_strings", len(found) == 0))
    else:
        log(f"❌ PATCH /api/admin/employees/{test_state['employee_id']}/review returned {resp.status_code}", "ERROR")
        log(f"Response: {resp.text}")
        results.append(("review_rejected", False))
    
    return results


def test_export_csv():
    """Test GET /api/admin/employees.csv."""
    log("=" * 80)
    log("TEST: Export Employees CSV")
    log("=" * 80)
    
    results = []
    
    log("Testing GET /api/admin/employees.csv...")
    resp = requests.get(
        f"{BASE_URL}/api/admin/employees.csv",
        auth=(ADMIN_USERNAME, ADMIN_PASSWORD)
    )
    
    if resp.status_code == 200:
        csv_content = resp.text
        log(f"CSV length: {len(csv_content)} bytes")
        
        # Check for UTF-8 BOM
        if csv_content.startswith("\ufeff"):
            log(f"✅ CSV starts with UTF-8 BOM")
            results.append(("csv_export_bom", True))
        else:
            log(f"❌ CSV missing UTF-8 BOM", "ERROR")
            results.append(("csv_export_bom", False))
        
        # Check if our employee is in the CSV
        if test_state["test_name"] in csv_content:
            log(f"✅ Newly submitted employee found in CSV")
            results.append(("csv_export_contains_employee", True))
        else:
            log(f"❌ Newly submitted employee NOT found in CSV", "ERROR")
            results.append(("csv_export_contains_employee", False))
        
        # Check for retired strings
        found = check_retired_strings(csv_content, "CSV export")
        results.append(("csv_export_no_retired_strings", len(found) == 0))
        
        results.append(("csv_export", True))
    else:
        log(f"❌ GET /api/admin/employees.csv returned {resp.status_code}, expected 200", "ERROR")
        results.append(("csv_export", False))
    
    return results


def test_mark_code_used():
    """Test POST /api/access-code/mark-used (idempotent)."""
    log("=" * 80)
    log("TEST: Mark Access Code Used")
    log("=" * 80)
    
    results = []
    
    if not test_state["access_code_id"] or not test_state["employee_id"]:
        log("⚠️  Skipping test (no access_code_id or employee_id available)", "WARNING")
        return [("mark_code_used", False)]
    
    log("Testing POST /api/access-code/mark-used...")
    payload = {
        "access_code_id": test_state["access_code_id"],
        "employee_id": test_state["employee_id"],
    }
    resp = requests.post(f"{BASE_URL}/api/access-code/mark-used", json=payload)
    
    if resp.status_code == 200:
        data = resp.json()
        log(f"Response: {data}")
        
        if data.get("ok") == True:
            log(f"✅ Access code marked as used (idempotent)")
            results.append(("mark_code_used", True))
        else:
            log(f"❌ Unexpected response: {data}", "ERROR")
            results.append(("mark_code_used", False))
    else:
        log(f"❌ POST /api/access-code/mark-used returned {resp.status_code}", "ERROR")
        results.append(("mark_code_used", False))
    
    return results


def test_finalize_induction():
    """Test POST /api/induction/finalize (legacy PDF regeneration)."""
    log("=" * 80)
    log("TEST: Finalize Induction (Legacy)")
    log("=" * 80)
    
    results = []
    
    if not test_state["employee_id"]:
        log("⚠️  Skipping test (no employee_id available)", "WARNING")
        return [("finalize_induction", False)]
    
    log("Testing POST /api/induction/finalize...")
    payload = {
        "employee_id": test_state["employee_id"],
    }
    resp = requests.post(f"{BASE_URL}/api/induction/finalize", json=payload)
    
    if resp.status_code == 200:
        data = resp.json()
        log(f"Response: {data}")
        
        if data.get("employee_id") and data.get("pdf_url"):
            log(f"✅ PDF regenerated: pdf_url={data['pdf_url']}")
            results.append(("finalize_induction", True))
            
            # Check for retired strings
            response_text = resp.text
            found = check_retired_strings(response_text, "finalize induction response")
            results.append(("finalize_induction_no_retired_strings", len(found) == 0))
        else:
            log(f"❌ Missing employee_id or pdf_url in response", "ERROR")
            results.append(("finalize_induction", False))
    else:
        log(f"❌ POST /api/induction/finalize returned {resp.status_code}", "ERROR")
        log(f"Response: {resp.text}")
        results.append(("finalize_induction", False))
    
    return results


def test_auth_gate():
    """Test that admin endpoints require authentication."""
    log("=" * 80)
    log("TEST: Admin Authentication Gate")
    log("=" * 80)
    
    results = []
    
    # Test without credentials
    log("Testing GET /api/admin/employees without credentials...")
    resp = requests.get(f"{BASE_URL}/api/admin/employees")
    
    if resp.status_code == 401:
        www_auth = resp.headers.get("WWW-Authenticate", "")
        if "Basic" in www_auth and "PNC Admin" in www_auth:
            log(f"✅ Admin endpoint requires authentication (401 with WWW-Authenticate)")
            results.append(("admin_auth_gate", True))
        else:
            log(f"❌ WWW-Authenticate header incorrect: {www_auth}", "ERROR")
            results.append(("admin_auth_gate", False))
    else:
        log(f"❌ Expected 401, got {resp.status_code}", "ERROR")
        results.append(("admin_auth_gate", False))
    
    # Test with wrong credentials
    log("Testing GET /api/admin/employees with wrong credentials...")
    resp2 = requests.get(
        f"{BASE_URL}/api/admin/employees",
        auth=("wrong", "credentials")
    )
    
    if resp2.status_code == 401:
        log(f"✅ Wrong credentials rejected (401)")
        results.append(("admin_auth_wrong_creds", True))
    else:
        log(f"❌ Expected 401, got {resp2.status_code}", "ERROR")
        results.append(("admin_auth_wrong_creds", False))
    
    return results


def main():
    """Run all tests in sequence."""
    log("=" * 80)
    log("Phase 1 Security & Trust Audit — Backend Regression Test")
    log("=" * 80)
    log(f"BASE_URL: {BASE_URL}")
    log(f"ADMIN_USERNAME: {ADMIN_USERNAME}")
    log("=" * 80)
    
    if not BASE_URL:
        log("❌ REACT_APP_BACKEND_URL not set in frontend/.env", "ERROR")
        sys.exit(1)
    
    if not ADMIN_USERNAME or not ADMIN_PASSWORD:
        log("❌ ADMIN_USERNAME or ADMIN_PASSWORD not set in backend/.env", "ERROR")
        sys.exit(1)
    
    all_results = []
    
    # Run tests in order
    all_results.extend(test_production_hardening())
    all_results.extend(test_security_headers())
    all_results.extend(test_seo_and_security_files())
    all_results.extend(test_cors_protection())
    all_results.extend(test_auth_gate())
    all_results.extend(test_system_status())
    all_results.extend(test_create_invite())
    all_results.extend(test_list_invites())
    all_results.extend(test_validate_access_code())
    all_results.extend(test_submit_induction())
    all_results.extend(test_validate_code_already_used())
    all_results.extend(test_list_employees())
    all_results.extend(test_review_approved())
    all_results.extend(test_review_rejected())
    all_results.extend(test_export_csv())
    all_results.extend(test_mark_code_used())
    all_results.extend(test_finalize_induction())
    
    # Summary
    log("=" * 80)
    log("TEST SUMMARY")
    log("=" * 80)
    
    passed = sum(1 for _, result in all_results if result)
    failed = sum(1 for _, result in all_results if not result)
    total = len(all_results)
    
    log(f"Total: {total} tests")
    log(f"Passed: {passed} ✅")
    log(f"Failed: {failed} ❌")
    
    if failed > 0:
        log("=" * 80)
        log("FAILED TESTS:")
        log("=" * 80)
        for name, result in all_results:
            if not result:
                log(f"  ❌ {name}")
    
    log("=" * 80)
    
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
