"""
Adversarial Empirical Challenge Test Suite for Milestone 1:
Data & Deserializer Integrity (parse_powershell_hash_str, offers.json, news.json).

Written by challenger_m1_2 (critic, specialist).
Empirically stresses:
1. PowerShell stringified hashtable deserialization under pathological & adversarial inputs.
2. Graceful fallback on corrupt, incomplete, and malformed strings without crashes.
3. Database invariants for data/offers.json (39 offers, non-null expiry_date, dict authenticity_details).
4. Database invariants for data/news.json (75 articles, valid ISO "date" field).
5. Pydantic V2 schema validation across all 39 offers via Offer(**o).
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import pytest
from pydantic import ValidationError

from src.authenticity import parse_powershell_hash_str
from src.models import Offer, OffersDatabase

ROOT = Path(__file__).resolve().parent.parent
OFFERS_FILE = ROOT / "data" / "offers.json"
NEWS_FILE = ROOT / "data" / "news.json"
OFFERS_SCHEMA_FILE = ROOT / "data" / "schema.json"
NEWS_SCHEMA_FILE = ROOT / "data" / "news_schema.json"


# ==============================================================================
# SECTION 1: Pathological PowerShell Hash String Deserialization Tests
# ==============================================================================

class TestPowerShellDeserializerPathological:
    """Stress tests for parse_powershell_hash_str against adversarial & pathological inputs."""

    def test_nested_hashtables_standard(self):
        """Verify standard nested hashtables: @{foo=@{bar=1; baz=$true}}."""
        raw = "@{foo=@{bar=1; baz=$true}}"
        res = parse_powershell_hash_str(raw)
        assert isinstance(res, dict)
        assert "foo" in res
        assert isinstance(res["foo"], dict)
        assert res["foo"]["bar"] == 1
        assert res["foo"]["baz"] is True

    def test_deeply_nested_hashtables(self):
        """Verify deeply nested hashtables: 5+ levels of nesting."""
        raw = "@{l1=@{l2=@{l3=@{l4=@{l5='deep_value'}}}}} "
        res = parse_powershell_hash_str(raw)
        assert isinstance(res, dict)
        cur = res
        for lvl in ["l1", "l2", "l3", "l4"]:
            assert lvl in cur
            assert isinstance(cur[lvl], dict)
            cur = cur[lvl]
        assert cur["l5"] == "deep_value"

    def test_multiple_nested_siblings(self):
        """Verify multiple nested hashtable siblings within the same parent."""
        raw = "@{sub1=@{a=1; b=2}; sub2=@{c='hello'; d=$false}; count=42}"
        res = parse_powershell_hash_str(raw)
        assert res["sub1"] == {"a": 1, "b": 2}
        assert res["sub2"] == {"c": "hello", "d": False}
        assert res["count"] == 42

    def test_arrays_and_lists(self):
        """Verify arrays and lists: @{items=@(1, 2, 3); name='test'}."""
        raw = "@{items=@(1, 2, 3); name='test'}"
        res = parse_powershell_hash_str(raw)
        assert isinstance(res, dict)
        assert res["name"] == "test"
        assert res["items"] == [1, 2, 3]

    def test_arrays_various_syntaxes(self):
        """Verify empty arrays and alternate PowerShell collection markers."""
        assert parse_powershell_hash_str("@{arr=@()}")["arr"] == []
        assert parse_powershell_hash_str("@{arr=System.Object[]}")["arr"] == []
        assert parse_powershell_hash_str("@{arr=()}")["arr"] == []
        assert parse_powershell_hash_str("@{arr=@(10, 20, 30)}")["arr"] == [10, 20, 30]
        assert parse_powershell_hash_str("@{arr=('alpha', 'beta')}")["arr"] == ["alpha", "beta"]

    def test_strings_with_semicolons_inside_quotes(self):
        """Verify strings containing semicolons inside single and double quotes do not split prematurely."""
        raw = "@{note=\"semicolon;separated;text\"; title='another;semi;here'; standard=123}"
        res = parse_powershell_hash_str(raw)
        assert res["note"] == "semicolon;separated;text"
        assert res["title"] == "another;semi;here"
        assert res["standard"] == 123

    def test_strings_with_nested_quotes_and_equals(self):
        """Verify strings containing equal signs, brackets, and quotes inside values."""
        raw = "@{formula=\"x=y+z; a=b\"; query='https://example.com?foo=bar&baz=1'; flag=$true}"
        res = parse_powershell_hash_str(raw)
        assert res["formula"] == "x=y+z; a=b"
        assert res["query"] == "https://example.com?foo=bar&baz=1"
        assert res["flag"] is True

    def test_strings_with_special_characters(self):
        """Verify strings containing special punctuation, colons, slashes, and symbols."""
        raw = "@{url='https://learn.microsoft.com/en-us/certifications/exams/az-900'; tag='[PROMO-2026]'; symbols='!@#$%^&*()_+'}"
        res = parse_powershell_hash_str(raw)
        assert res["url"] == "https://learn.microsoft.com/en-us/certifications/exams/az-900"
        assert res["tag"] == "[PROMO-2026]"
        assert res["symbols"] == "!@#$%^&*()_+"

    def test_powershell_booleans_and_nulls(self):
        """Verify case-insensitive $true, $false, $null, null, none."""
        raw = "@{t1=$true; t2=$True; f1=$false; f2=$False; n1=$null; n2=$Null; n3=null; n4=none}"
        res = parse_powershell_hash_str(raw)
        assert res["t1"] is True
        assert res["t2"] is True
        assert res["f1"] is False
        assert res["f2"] is False
        assert res["n1"] is None
        assert res["n2"] is None
        assert res["n3"] is None
        assert res["n4"] is None

    def test_newline_delimited_hashtable(self):
        """PowerShell allows newline-separated key-values without semicolons."""
        raw = "@{\n  portal = 'Pearson VUE'\n  score = 95\n  status = 'Active'\n}"
        res = parse_powershell_hash_str(raw)
        assert res["portal"] == "Pearson VUE"
        assert res["score"] == 95
        assert res["status"] == "Active"

    def test_numeric_integers_and_floats(self):
        """Verify integer and float parsing including negative values."""
        raw = "@{positive=100; negative=-50; float_val=99.95; zero=0}"
        res = parse_powershell_hash_str(raw)
        assert res["positive"] == 100
        assert res["negative"] == -50
        assert res["float_val"] == 99.95
        assert res["zero"] == 0

    def test_already_dict_input(self):
        """If input is already a dictionary, it must be returned intact."""
        sample = {"verdict": "VERIFIED_AUTHENTIC", "score": 100}
        assert parse_powershell_hash_str(sample) is sample

    def test_json_string_fallback(self):
        """If input is a JSON string, it should parse to a dictionary."""
        json_str = '{"verdict": "VERIFIED_AUTHENTIC", "domain_ok": true, "score": 90}'
        res = parse_powershell_hash_str(json_str)
        assert res == {"verdict": "VERIFIED_AUTHENTIC", "domain_ok": True, "score": 90}

    def test_pydantic_offer_model_integration_with_ps_hash_str(self):
        """Verify that passing stringified PowerShell hash to Offer automatically converts to dict."""
        sample_offer = {
            "id": "test-ps-hash-offer",
            "title": "Test Offer for PS Hash",
            "platform": "Microsoft Azure",
            "category": "Cloud Architecture",
            "certification_name": "Azure Fundamentals",
            "credential_tier": "proctored_exam",
            "url": "https://learn.microsoft.com/en-us/credentials/certifications/azure-fundamentals/",
            "authenticity_details": "@{verdict='VERIFIED_AUTHENTIC'; score=95; domain_ok=$true; hops=@('https://azure.com', 'https://learn.microsoft.com')}",
            "expiry_date": "Rolling",
        }
        offer = Offer(**sample_offer)
        assert isinstance(offer.authenticity_details, dict)
        assert offer.authenticity_details["verdict"] == "VERIFIED_AUTHENTIC"
        assert offer.authenticity_details["score"] == 95
        assert offer.authenticity_details["domain_ok"] is True
        assert offer.authenticity_details["hops"] == ["https://azure.com", "https://learn.microsoft.com"]


# ==============================================================================
# SECTION 2: Graceful Degradation on Corrupt / Incomplete Strings
# ==============================================================================

class TestPowerShellDeserializerGracefulDegradation:
    """Ensure corrupt, unclosed, or invalid strings NEVER crash and degrade gracefully."""

    @pytest.mark.parametrize(
        "corrupt_input",
        [
            "",
            "   ",
            "\n\t",
            "None",
            "null",
            "not a powershell string",
            "@{",                      # Missing closing brace
            "}",                       # Missing opening
            "@{}",                     # Empty content -> returns {}
            "@{   }",                  # Whitespace content -> returns {}
            "@{unclosed=\"string",     # Unclosed quote
            "@{key=",                  # Key without value
            "@{=value}",               # Value without key
            "@{===}",                  # Malformed syntax
            "@{;;;}",                  # Empty semicolons
            "@{k1=v1;;;k2=v2}",        # Redundant semicolons
            "@{k1=@{unclosed=1",       # Unclosed nested brace
            "@{k1=1}}",                # Extra closing brace
            "@{arr=@(1, 2, }",         # Malformed array
            None,                      # Non-string None
            12345,                     # Integer input
            12.34,                     # Float input
            ["item1", "item2"],        # List input
            True,                      # Boolean input
            "{bad json: not valid",    # Broken JSON string
            "@{k1='v1'; k2=}",         # Trailing empty value
            "@{;;;k1=1}",              # Leading semicolons
            "@{=; =; =}",              # Garbage tokens
        ]
    )
    def test_no_crash_on_corrupt_inputs(self, corrupt_input):
        """Parser must never raise an unhandled exception on corrupt inputs."""
        try:
            res = parse_powershell_hash_str(corrupt_input)
            assert isinstance(res, dict)
        except Exception as exc:
            pytest.fail(f"parse_powershell_hash_str crashed on {corrupt_input!r}: {exc}")


# ==============================================================================
# SECTION 3: Empirical Verification of data/offers.json
# ==============================================================================

@pytest.fixture(scope="module")
def offers_data() -> Dict[str, Any]:
    with open(OFFERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def offers_list(offers_data) -> list:
    return offers_data["offers"]


class TestOffersDataIntegrity:
    """Empirical audit of data/offers.json contents."""

    def test_offer_count_is_39(self, offers_list):
        """Assert exactly 39 offers exist in data/offers.json."""
        assert len(offers_list) == 39, f"Expected 39 offers, found {len(offers_list)}"

    def test_all_offers_have_valid_dict_authenticity_details(self, offers_list):
        """Assert all 39 offers have valid dict authenticity_details."""
        missing_or_invalid = []
        for o in offers_list:
            auth = o.get("authenticity_details")
            if not isinstance(auth, dict) or not auth:
                missing_or_invalid.append((o.get("id"), type(auth), auth))
        assert not missing_or_invalid, f"Offers with invalid authenticity_details: {missing_or_invalid}"

    def test_all_offers_have_non_null_expiry_date(self, offers_list):
        """Assert all 39 offers have non-null expiry_date."""
        null_expiry = []
        for o in offers_list:
            exp = o.get("expiry_date")
            if exp is None:
                null_expiry.append(o.get("id"))
        assert not null_expiry, f"Offers with null expiry_date: {null_expiry}"

    def test_expiry_date_values_are_valid_strings(self, offers_list):
        """Assert all expiry_date fields are non-empty strings complying with schema minLength: 1."""
        invalid_expiry = []
        for o in offers_list:
            exp = o.get("expiry_date")
            if not isinstance(exp, str) or not exp.strip():
                invalid_expiry.append((o.get("id"), exp))
        assert not invalid_expiry, f"Offers with invalid empty or non-string expiry_date: {invalid_expiry}"

    def test_all_39_offers_instantiate_pydantic_model(self, offers_list):
        """Run Pydantic model validation on all 39 offers (Offer(**o))."""
        validation_errors = []
        for o in offers_list:
            try:
                model_inst = Offer(**o)
                assert model_inst.id == o["id"]
                assert isinstance(model_inst.authenticity_details, dict)
            except ValidationError as err:
                validation_errors.append((o.get("id"), str(err)))
            except Exception as err:
                validation_errors.append((o.get("id"), f"Unexpected: {err}"))
        assert not validation_errors, f"Pydantic Offer validation failures: {validation_errors}"

    def test_offers_database_model_validation(self, offers_data):
        """Assert complete data/offers.json payload instantiates OffersDatabase."""
        try:
            db = OffersDatabase(**offers_data)
            assert len(db.offers) == 39
        except Exception as exc:
            pytest.fail(f"OffersDatabase validation failed: {exc}")


# ==============================================================================
# SECTION 4: Empirical Verification of data/news.json
# ==============================================================================

@pytest.fixture(scope="module")
def news_data() -> Dict[str, Any]:
    with open(NEWS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def news_items(news_data) -> list:
    if isinstance(news_data, list):
        return news_data
    return news_data.get("news", news_data.get("articles", []))


class TestNewsDataIntegrity:
    """Empirical audit of data/news.json contents."""

    def test_news_item_count_is_at_least_75(self, news_items):
        """Assert at least 75 news articles exist in data/news.json."""
        assert len(news_items) >= 75, f"Expected at least 75 news articles, found {len(news_items)}"

    def test_all_75_news_items_have_non_null_date(self, news_items):
        """Assert all 75 news items have a non-null 'date' field."""
        missing_date = []
        for idx, item in enumerate(news_items):
            date_val = item.get("date")
            if date_val is None:
                missing_date.append((idx, item.get("id", item.get("title", f"item_{idx}"))))
        assert not missing_date, f"News items missing 'date': {missing_date}"

    def test_all_75_news_items_have_valid_iso_date(self, news_items):
        """Assert all 75 news items have a valid ISO-8601 date string."""
        invalid_dates = []
        for idx, item in enumerate(news_items):
            date_str = item.get("date")
            if not isinstance(date_str, str):
                invalid_dates.append((idx, "Not a string", date_str))
                continue
            clean_date = date_str.replace("Z", "+00:00")
            try:
                datetime.fromisoformat(clean_date)
            except Exception:
                if not re.match(r"^\d{4}-\d{2}-\d{2}", date_str):
                    invalid_dates.append((idx, "Invalid ISO format", date_str))
        assert not invalid_dates, f"News items with invalid ISO date: {invalid_dates}"

    def test_news_date_synchronization_with_published_date(self, news_items):
        """Assert 'date' field matches 'published_date' when published_date is present."""
        mismatched = []
        for idx, item in enumerate(news_items):
            pub_date = item.get("published_date")
            date_val = item.get("date")
            if pub_date and date_val != pub_date:
                mismatched.append((idx, pub_date, date_val))
        assert not mismatched, f"News items where date != published_date: {mismatched}"


# ==============================================================================
# SECTION 5: Schema Pre-Flight Validation with jsonschema
# ==============================================================================

class TestJsonSchemasValidation:
    """Verify that both data files pass their respective JSON schemas."""

    def test_offers_passes_draft07_schema(self):
        import jsonschema
        with open(OFFERS_SCHEMA_FILE, "r", encoding="utf-8") as f:
            schema = json.load(f)
        with open(OFFERS_FILE, "r", encoding="utf-8") as f:
            instance = json.load(f)
        jsonschema.validate(instance=instance, schema=schema)

    def test_news_passes_draft07_schema(self):
        import jsonschema
        with open(NEWS_SCHEMA_FILE, "r", encoding="utf-8") as f:
            schema = json.load(f)
        with open(NEWS_FILE, "r", encoding="utf-8") as f:
            instance = json.load(f)
        jsonschema.validate(instance=instance, schema=schema)
