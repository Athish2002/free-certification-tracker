"""
Comprehensive Unit and Integration Test Suite for CertPulse Atomic I/O,
JSON Schema Pre-Flight Validation, Dataset Conformance, and Defensive Deserialization.
Consolidated Logical Invariant Suite.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict
from unittest.mock import patch

import jsonschema
import pytest

from src.authenticity import audit_offer_authenticity, parse_powershell_hash_str
from src.io_utils import atomic_write_json, load_schema, read_json, validate_payload
from src.models import Offer, OffersDatabase

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
OFFERS_FILE = DATA_DIR / "offers.json"
NEWS_FILE = DATA_DIR / "news.json"
OFFERS_SCHEMA_FILE = DATA_DIR / "schema.json"
NEWS_SCHEMA_FILE = DATA_DIR / "news_schema.json"


# --- 1. Schema Loading and Validation Tests ---

def test_schema_loading_and_payload_validation_invariants():
    """Verify schema loading from Path/str, missing file exception, and payload validation."""
    schema = load_schema(OFFERS_SCHEMA_FILE)
    assert isinstance(schema, dict) and schema.get("$schema") == "http://json-schema.org/draft-07/schema#"
    assert load_schema(str(OFFERS_SCHEMA_FILE)) == schema

    with pytest.raises(FileNotFoundError):
        load_schema("data/non_existent_schema_xyz.json")

    simple_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": ["name", "status"],
        "properties": {
            "name": {"type": "string"},
            "status": {"type": "string", "enum": ["active", "inactive"]},
        },
    }
    validate_payload({"name": "CertPulse", "status": "active"}, simple_schema)
    with pytest.raises(jsonschema.ValidationError):
        validate_payload({"name": "CertPulse", "status": "unknown"}, simple_schema)


# --- 2. Atomic Write and Pre-Flight Protection Tests ---

def test_atomic_write_json_success_and_schema_validation(tmp_path: Path):
    """Verify atomic_write_json creates valid files with indentation and schema compliance."""
    target = tmp_path / "valid_output.json"
    data = {"status": "success", "count": 42}
    atomic_write_json(target, data, indent=2)
    assert target.exists() and read_json(target) == data

    schema_file = tmp_path / "test_schema.json"
    schema_file.write_text(json.dumps({
        "type": "object", "required": ["id"], "properties": {"id": {"type": "string"}}
    }), encoding="utf-8")
    atomic_write_json(target, {"id": "test-1"}, schema_path=schema_file)
    assert read_json(target)["id"] == "test-1"


def test_atomic_write_preflight_protection_and_cleanup_invariants(tmp_path: Path):
    """
    CRITICAL: Verify pre-flight validation failure preserves existing file,
    creates no new file when target is missing, and cleans up temp files on I/O error.
    """
    schema = {"type": "object", "required": ["id", "val"], "properties": {"id": {"type": "string"}, "val": {"type": "integer"}}}
    schema_file = tmp_path / "test_schema.json"
    schema_file.write_text(json.dumps(schema), encoding="utf-8")

    # 1. Existing file preserved
    target = tmp_path / "existing_data.json"
    initial = {"id": "original", "val": 1}
    atomic_write_json(target, initial, schema_path=schema_file)
    with pytest.raises(jsonschema.ValidationError):
        atomic_write_json(target, {"id": "bad", "val": "not-int"}, schema_path=schema_file)
    assert read_json(target) == initial

    # 2. Never created file
    missing_target = tmp_path / "never_created.json"
    with pytest.raises(jsonschema.ValidationError):
        atomic_write_json(missing_target, {"id": "bad", "val": "not-int"}, schema_path=schema_file)
    assert not missing_target.exists()

    # 3. Temp cleanup on I/O error
    io_target = tmp_path / "io_fail.json"
    with patch("os.replace", side_effect=OSError("Disk Lock")):
        with pytest.raises(OSError):
            atomic_write_json(io_target, {"data": 1})
    assert len(list(tmp_path.glob("*.tmp"))) == 0


# --- 3. Live Dataset Schema Verification Tests ---

def test_live_datasets_conformance_to_schemas_invariant():
    """Asserts that data/offers.json and data/news.json conform 100% to their schemas."""
    assert OFFERS_FILE.exists() and NEWS_FILE.exists()
    offers_data = read_json(OFFERS_FILE)
    offers_schema = read_json(OFFERS_SCHEMA_FILE)
    validate_payload(offers_data, offers_schema)
    assert len(offers_data["offers"]) == 39

    news_data = read_json(NEWS_FILE)
    news_schema = read_json(NEWS_SCHEMA_FILE)
    validate_payload(news_data, news_schema)
    assert len(news_data["news"]) >= 75


# --- 4. Expiry Date and News Date Invariants ---

def test_live_dataset_dates_and_rolling_invariants():
    """Verify zero offers have null expiry_date and all news articles have synchronized dates."""
    offers_data = read_json(OFFERS_FILE)
    null_exp = [o["id"] for o in offers_data["offers"] if o.get("expiry_date") is None]
    assert len(null_exp) == 0, f"Found offers with null expiry_date: {null_exp}"

    news_data = read_json(NEWS_FILE)
    for item in news_data["news"]:
        nid = item.get("id", "UNKNOWN")
        assert "date" in item and item["date"] is not None
        assert re.match(r"^\d{4}-\d{2}-\d{2}", item["date"])
        assert item["date"] == item.get("published_date")


# --- 5. PowerShell Hashtable String Defensive Deserialization Tests ---

@pytest.mark.parametrize("raw_input,expected_subset", [
    ("@{key=value; number=42; flag=True}", {"key": "value", "number": 42, "flag": True}),
    ("@{is_active=$true; is_expired=$false; optional_tag=$null}", {"is_active": True, "is_expired": False, "optional_tag": None}),
    ("@{empty_arr=System.Object[]; explicit_empty=@(); items=@('ALPHA', 'BETA')}", {"empty_arr": [], "explicit_empty": [], "items": ["ALPHA", "BETA"]}),
    ("@{outer_key=100; child=@{inner_name='nested_val'; active=True}}", {"outer_key": 100, "child": {"inner_name": "nested_val", "active": True}}),
])
def test_parse_powershell_hash_str_structural_variants(raw_input, expected_subset):
    """Verify parsing PowerShell stringified hashtables across structural variants."""
    parsed = parse_powershell_hash_str(raw_input)
    for k, v in expected_subset.items():
        assert parsed[k] == v


def test_parse_powershell_hash_str_real_payload_and_fallbacks():
    """Verify real-world degraded PowerShell string, dict idempotency, JSON parsing, and invalid fallbacks."""
    ps_str = (
        "@{is_authentic_vendor=True; authenticity_score=95; verdict=VERIFIED_AUTHENTIC; "
        "trust_tier=Official Vendor Portal; domain_verified=True; ssl_verified=True; "
        "redirect_secure=True; corroboration_passed=True; checks_passed=System.Object[]; "
        "warning_flags=System.Object[]; summary=95% Authenticity: Official Vendor Portal}"
    )
    parsed = parse_powershell_hash_str(ps_str)
    assert parsed["is_authentic_vendor"] is True and parsed["authenticity_score"] == 95
    assert parsed["verdict"] == "VERIFIED_AUTHENTIC" and parsed["checks_passed"] == []

    # Idempotent on dict
    orig_dict = {"verdict": "VERIFIED_AUTHENTIC", "score": 90}
    assert parse_powershell_hash_str(orig_dict) == orig_dict

    # Standard JSON string
    assert parse_powershell_hash_str('{"score": 95}') == {"score": 95}

    # Invalid inputs return empty dict
    for bad in ["", "not a hash", None, 12345]:
        assert parse_powershell_hash_str(bad) == {}


# --- 6. Offer Model and Authenticity Audit Integration ---

def test_offer_model_and_audit_authenticity_invariants():
    """Verify Pydantic Offer model parses PowerShell string and audit returns clean dict."""
    offer_data = {
        "id": "test-ps-offer", "title": "Test PS Offer", "platform": "Oracle Cloud",
        "category": "Cloud Computing", "certification_name": "Oracle Cloud Foundations",
        "credential_tier": "proctored_exam", "url": "https://mylearn.oracle.com/exam/123",
        "status": "Active", "cost": 0.0,
        "authenticity_details": "@{is_authentic_vendor=$true; authenticity_score=92; verdict='VERIFIED_AUTHENTIC'}"
    }
    model = Offer.model_validate(offer_data)
    assert isinstance(model.authenticity_details, dict)
    assert model.authenticity_details.get("is_authentic_vendor") is True

    audit = audit_offer_authenticity(offer_data)
    assert isinstance(audit, dict) and "authenticity_score" in audit and 0 <= audit["authenticity_score"] <= 100
