"""
Comprehensive Unit and Integration Test Suite for CertPulse Atomic I/O,
JSON Schema Pre-Flight Validation, Dataset Conformance, and Defensive Deserialization.
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

def test_load_schema_from_path():
    """Verify load_schema successfully loads schema from Path or str."""
    schema = load_schema(OFFERS_SCHEMA_FILE)
    assert isinstance(schema, dict)
    assert schema.get("$schema") == "http://json-schema.org/draft-07/schema#"
    assert "definitions" in schema or "properties" in schema

    # Test loading via str
    schema_str = load_schema(str(OFFERS_SCHEMA_FILE))
    assert schema_str == schema


def test_load_schema_missing_file_raises():
    """Verify load_schema raises FileNotFoundError for non-existent file."""
    with pytest.raises(FileNotFoundError):
        load_schema("data/non_existent_schema_xyz.json")


def test_validate_payload_valid_data():
    """Verify validate_payload succeeds when payload matches schema."""
    simple_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": ["name", "status"],
        "properties": {
            "name": {"type": "string"},
            "status": {"type": "string", "enum": ["active", "inactive"]},
        },
    }
    valid_data = {"name": "CertPulse", "status": "active"}
    # Should not raise
    validate_payload(valid_data, simple_schema)


def test_validate_payload_invalid_data_raises_validation_error():
    """Verify validate_payload raises jsonschema.ValidationError on mismatch."""
    simple_schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": ["name", "status"],
        "properties": {
            "name": {"type": "string"},
            "status": {"type": "string", "enum": ["active", "inactive"]},
        },
    }
    invalid_data = {"name": "CertPulse", "status": "unknown_status"}
    with pytest.raises(jsonschema.ValidationError):
        validate_payload(invalid_data, simple_schema)


# --- 2. Atomic Write and Pre-Flight Protection Tests ---

def test_atomic_write_json_creates_valid_file(tmp_path: Path):
    """Verify atomic_write_json creates a well-formatted JSON file."""
    target = tmp_path / "test_output.json"
    data = {"status": "success", "count": 42, "items": ["a", "b"]}

    atomic_write_json(target, data, indent=2)

    assert target.exists()
    loaded = read_json(target)
    assert loaded == data


def test_atomic_write_json_with_valid_schema(tmp_path: Path):
    """Verify atomic_write_json validates schema and writes successfully."""
    schema = {
        "type": "object",
        "required": ["id", "val"],
        "properties": {
            "id": {"type": "string"},
            "val": {"type": "integer"},
        },
    }
    schema_file = tmp_path / "test_schema.json"
    schema_file.write_text(json.dumps(schema), encoding="utf-8")

    target = tmp_path / "valid_target.json"
    data = {"id": "item-1", "val": 100}

    atomic_write_json(target, data, schema_path=schema_file)
    assert target.exists()
    assert read_json(target) == data


def test_atomic_write_json_preflight_failure_protects_existing_file(tmp_path: Path):
    """
    CRITICAL: Verify that when target file already exists, pre-flight validation failure
    raises ValidationError AND preserves original target file completely untouched.
    """
    schema = {
        "type": "object",
        "required": ["id", "val"],
        "properties": {
            "id": {"type": "string"},
            "val": {"type": "integer"},
        },
    }
    schema_file = tmp_path / "test_schema.json"
    schema_file.write_text(json.dumps(schema), encoding="utf-8")

    target = tmp_path / "existing_data.json"
    initial_content = {"id": "original", "val": 1}
    atomic_write_json(target, initial_content, schema_path=schema_file)
    original_mtime = target.stat().st_mtime

    invalid_data = {"id": "corrupted", "val": "not-an-integer"}

    with pytest.raises(jsonschema.ValidationError):
        atomic_write_json(target, invalid_data, schema_path=schema_file)

    # File must be preserved with exact original content
    preserved = read_json(target)
    assert preserved == initial_content
    assert preserved["id"] == "original"
    assert target.stat().st_mtime == original_mtime

    # No leftover .tmp files
    tmp_files = list(tmp_path.glob("*.tmp"))
    assert len(tmp_files) == 0


def test_atomic_write_json_preflight_failure_creates_no_file(tmp_path: Path):
    """Verify that if target file does not exist, pre-flight validation failure leaves no file on disk."""
    schema = {
        "type": "object",
        "required": ["mandatory_field"],
    }
    target = tmp_path / "never_created.json"
    invalid_data = {"wrong_field": 123}

    with pytest.raises(jsonschema.ValidationError):
        atomic_write_json(target, invalid_data, schema_path=schema)

    assert not target.exists()
    assert len(list(tmp_path.glob("*.tmp"))) == 0


def test_atomic_write_json_cleans_up_temp_on_io_error(tmp_path: Path):
    """Verify that if an exception occurs during replace, temp file is deleted cleanly."""
    target = tmp_path / "io_fail.json"
    data = {"sample": "data"}

    with patch("os.replace", side_effect=OSError("Simulated Disk Lock")):
        with pytest.raises(OSError):
            atomic_write_json(target, data)

    assert not target.exists()
    tmp_files = list(tmp_path.glob("*.tmp"))
    assert len(tmp_files) == 0


# --- 3. Live Dataset Schema Verification Tests ---

def test_live_offers_json_validates_against_schema():
    """
    Asserts that data/offers.json conforms 100% to data/schema.json.
    Validates all 39 offers against the formal JSON schema without warnings or errors.
    """
    assert OFFERS_FILE.exists(), f"Missing offers file: {OFFERS_FILE}"
    assert OFFERS_SCHEMA_FILE.exists(), f"Missing schema file: {OFFERS_SCHEMA_FILE}"

    offers_data = read_json(OFFERS_FILE)
    schema = read_json(OFFERS_SCHEMA_FILE)

    # Validates without raising ValidationError
    validate_payload(offers_data, schema)
    assert len(offers_data["offers"]) == 39


def test_live_news_json_validates_against_schema():
    """
    Asserts that data/news.json conforms 100% to data/news_schema.json.
    Validates all 75 articles against the formal JSON schema without warnings or errors.
    """
    assert NEWS_FILE.exists(), f"Missing news file: {NEWS_FILE}"
    assert NEWS_SCHEMA_FILE.exists(), f"Missing schema file: {NEWS_SCHEMA_FILE}"

    news_data = read_json(NEWS_FILE)
    schema = read_json(NEWS_SCHEMA_FILE)

    validate_payload(news_data, schema)
    assert len(news_data["news"]) >= 75


# --- 4. Expiry Date and News Date Invariants ---

def test_zero_offers_have_null_expiry_date():
    """
    R2 Invariant: Assert that 0 offers in data/offers.json have null expiry_date.
    Every single offer must possess a non-null string date or canonical sentinel.
    """
    offers_data = read_json(OFFERS_FILE)
    offers = offers_data["offers"]
    assert len(offers) == 39

    null_exp = [o["id"] for o in offers if o.get("expiry_date") is None]
    assert len(null_exp) == 0, f"Found offers with null expiry_date: {null_exp}"

    # Verify previously null historical offers now have 'Rolling'
    historical_ids = [
        "hist-msft-build-2024",
        "hist-msft-ignite-2023",
        "hist-oracle-race-cert-2024",
        "hist-cisco-rev-up-devnae",
        "hist-aws-ai-practitioner-early",
        "hist-gcp-ace-challenge",
        "hist-databricks-genai-2024",
        "hist-github-universe-2024",
    ]
    offer_map = {o["id"]: o for o in offers}
    for hid in historical_ids:
        assert hid in offer_map
        assert offer_map[hid]["expiry_date"] == "Rolling"


def test_all_news_articles_have_synchronized_date():
    """
    R1 Invariant: Assert that 100% of articles in data/news.json have non-null 'date'
    populated and synchronized with 'published_date'.
    """
    news_data = read_json(NEWS_FILE)
    articles = news_data["news"]
    assert len(articles) >= 75

    for item in articles:
        nid = item.get("id", "UNKNOWN")
        assert "date" in item, f"Article {nid} is missing 'date' key"
        assert item["date"] is not None, f"Article {nid} has null 'date'"
        assert isinstance(item["date"], str)
        assert re.match(r"^\d{4}-\d{2}-\d{2}", item["date"]), f"Invalid date format in {nid}: {item['date']}"
        assert item["date"] == item.get("published_date"), f"Desynchronized date in {nid}"


# --- 5. PowerShell Hashtable String Defensive Deserialization Tests ---

def test_parse_powershell_hash_str_simple():
    """Verify parsing simple PowerShell stringified hashtables."""
    raw = "@{key=value; number=42; flag=True}"
    parsed = parse_powershell_hash_str(raw)
    assert parsed["key"] == "value"
    assert parsed["number"] == 42
    assert parsed["flag"] is True


def test_parse_powershell_hash_str_booleans_and_nulls():
    """Verify handling of PowerShell booleans ($true, $false) and nulls ($null)."""
    raw = "@{is_active=$true; is_expired=$false; optional_tag=$null}"
    parsed = parse_powershell_hash_str(raw)
    assert parsed["is_active"] is True
    assert parsed["is_expired"] is False
    assert parsed["optional_tag"] is None


def test_parse_powershell_hash_str_arrays():
    """Verify handling of PowerShell array representations (System.Object[], @(), and tuples)."""
    raw = "@{empty_arr=System.Object[]; explicit_empty=@(); items=@('ALPHA', 'BETA')}"
    parsed = parse_powershell_hash_str(raw)
    assert parsed["empty_arr"] == []
    assert parsed["explicit_empty"] == []
    assert parsed["items"] == ["ALPHA", "BETA"]


def test_parse_powershell_hash_str_nested_hashtables():
    """Verify handling of nested PowerShell hashtables."""
    raw = "@{outer_key=100; child=@{inner_name='nested_val'; active=True}}"
    parsed = parse_powershell_hash_str(raw)
    assert parsed["outer_key"] == 100
    assert isinstance(parsed["child"], dict)
    assert parsed["child"]["inner_name"] == "nested_val"
    assert parsed["child"]["active"] is True


def test_parse_powershell_hash_str_real_authenticity_details_payload():
    """
    Verify parsing real-world PowerShell-stringified authenticity_details object.
    Matches the exact degradation format observed when ConvertTo-Json lacks -Depth.
    """
    ps_str = (
        "@{is_authentic_vendor=True; authenticity_score=95; verdict=VERIFIED_AUTHENTIC; "
        "trust_tier=Official Vendor Portal; domain_verified=True; ssl_verified=True; "
        "redirect_secure=True; corroboration_passed=True; checks_passed=System.Object[]; "
        "warning_flags=System.Object[]; summary=95% Authenticity: Official Vendor Portal (TLS Verified, Clean Destination)}"
    )
    parsed = parse_powershell_hash_str(ps_str)
    assert parsed["is_authentic_vendor"] is True
    assert parsed["authenticity_score"] == 95
    assert parsed["verdict"] == "VERIFIED_AUTHENTIC"
    assert parsed["trust_tier"] == "Official Vendor Portal"
    assert parsed["domain_verified"] is True
    assert parsed["ssl_verified"] is True
    assert parsed["redirect_secure"] is True
    assert parsed["corroboration_passed"] is True
    assert parsed["checks_passed"] == []
    assert parsed["warning_flags"] == []
    assert "95% Authenticity" in parsed["summary"]


def test_parse_powershell_hash_str_idempotent_on_dict():
    """Verify existing dict is returned as-is without mutation."""
    original = {"verdict": "VERIFIED_AUTHENTIC", "score": 90}
    assert parse_powershell_hash_str(original) == original


def test_parse_powershell_hash_str_standard_json():
    """Verify valid JSON string is parsed cleanly."""
    json_str = '{"verdict": "VERIFIED_AUTHENTIC", "authenticity_score": 95}'
    parsed = parse_powershell_hash_str(json_str)
    assert parsed["verdict"] == "VERIFIED_AUTHENTIC"
    assert parsed["authenticity_score"] == 95


def test_parse_powershell_hash_str_invalid_inputs_return_empty_dict():
    """Verify invalid or non-hash inputs gracefully return empty dict."""
    assert parse_powershell_hash_str("") == {}
    assert parse_powershell_hash_str("just a random string") == {}
    assert parse_powershell_hash_str(None) == {}
    assert parse_powershell_hash_str(12345) == {}


# --- 6. Model Integration Tests ---

def test_offer_model_converts_powershell_authenticity_details():
    """Verify Pydantic Offer model field validator converts stringified authenticity_details."""
    raw_ps = (
        "@{is_authentic_vendor=True; authenticity_score=92; verdict=VERIFIED_AUTHENTIC; "
        "domain_verified=True; ssl_verified=True}"
    )
    offer = Offer(
        id="test-ps-conversion-offer",
        title="PowerShell Deserialization Test",
        platform="Microsoft Azure",
        category="Cloud Architecture",
        certification_name="Azure Administrator",
        credential_tier="proctored_exam",
        url="https://learn.microsoft.com/credentials",
        authenticity_details=raw_ps,
    )
    assert isinstance(offer.authenticity_details, dict)
    assert offer.authenticity_details["is_authentic_vendor"] is True
    assert offer.authenticity_details["authenticity_score"] == 92
    assert offer.authenticity_details["verdict"] == "VERIFIED_AUTHENTIC"


def test_audit_offer_authenticity_returns_clean_dict():
    """Verify audit_offer_authenticity strictly returns a valid dictionary payload."""
    sample_offer = {
        "id": "azure-admin-test",
        "url": "https://learn.microsoft.com/credentials",
        "platform": "Microsoft Azure",
        "certification_name": "Azure Administrator Associate",
        "exam_code": "AZ-104",
    }
    result = audit_offer_authenticity(sample_offer)
    assert isinstance(result, dict)
    assert "is_authentic_vendor" in result
    assert "authenticity_score" in result
    assert "verdict" in result
    assert "checks_passed" in result
    assert isinstance(result["checks_passed"], list)
