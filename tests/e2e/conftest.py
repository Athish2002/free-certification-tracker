"""
Pytest Fixtures and Test Helpers for CertPulse E2E Test Suite.
Provides isolated namespaces, schema providers, mock payloads, and progressive probes.
"""

from __future__ import annotations

import io
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple, Union

import pytest
from PIL import Image, ImageDraw

# Root directory
ROOT_DIR = Path(__file__).resolve().parent.parent.parent


@pytest.fixture(scope="session")
def project_root() -> Path:
    """Returns absolute Path to project root."""
    return ROOT_DIR


@pytest.fixture(scope="session")
def live_offers_path(project_root: Path) -> Path:
    """Returns path to data/offers.json."""
    return project_root / "data" / "offers.json"


@pytest.fixture(scope="session")
def live_news_path(project_root: Path) -> Path:
    """Returns path to data/news.json."""
    return project_root / "data" / "news.json"


@pytest.fixture
def live_offers_data(live_offers_path: Path) -> Dict[str, Any]:
    """Loads current live offers.json content."""
    with open(live_offers_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def live_news_data(live_news_path: Path) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
    """Loads current live news.json content."""
    with open(live_news_path, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def sample_offer_dict() -> Dict[str, Any]:
    """Provides a canonical, schema-compliant offer dictionary."""
    return {
        "id": "e2e-test-offer-oracle",
        "title": "Oracle Cloud Infrastructure 2026 Free Exam Voucher",
        "platform": "Oracle Cloud",
        "category": "Cloud Architecture",
        "certification_name": "OCI Certified Architect Associate",
        "credential_tier": "proctored_exam",
        "proctoring_type": "pearson_vue",
        "accredited_body": "Pearson VUE",
        "url": "https://education.oracle.com/oracle-cloud-infrastructure",
        "verified_vendor_url": "https://education.oracle.com/oracle-cloud-infrastructure",
        "status": "Active",
        "seasonality": "evergreen",
        "value_usd": 245,
        "difficulty_tier": "Associate",
        "eligibility": "Global candidates",
        "time_period": "Rolling",
        "recurrence_pattern": "Continuous",
        "application_flow_type": "Checkout Promo Code",
        "redemption_portal": "https://home.pearsonvue.com/oracle",
        "checkout_field": "Promo Code",
        "cart_balance_verified": "$0.00 (100% Free / Waiver Confirmed)",
        "voucher_code": "AUTO_APPLIED",
        "is_authentic_vendor": True,
        "authenticity_score": 98,
        "authenticity_details": {
            "is_authentic_vendor": True,
            "authenticity_score": 98,
            "verdict": "VERIFIED_AUTHENTIC",
            "trust_tier": "Official Vendor Portal",
            "domain_verified": True,
            "ssl_verified": True,
            "redirect_secure": True,
            "corroboration_passed": True,
            "checks_passed": [
                "OFFICIAL_PRIMARY_VENDOR_DOMAIN",
                "STRICT_HTTPS_PROTOCOL",
                "CLEAN_REDIRECT_CHAIN",
            ],
            "warning_flags": [],
            "summary": "98% Authenticity: Official Vendor Portal (TLS Verified, Clean Destination)",
        },
        "screenshot_path": "docs/screenshots/oracle-oci-free-cert.png",
        "verification_date": "2026-10-23",
        "inspection_notes": "Ground-truth verified $0.00 cart balance.",
        "offer_type": "100% Free Exam Voucher",
        "is_historical_archive": False,
        "expiry_date": "Rolling",
    }


@pytest.fixture
def sample_offers_list(sample_offer_dict: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Provides a diverse list of valid offers across proctored, lab, active, and expired."""
    offer1 = dict(sample_offer_dict)
    
    offer2 = dict(sample_offer_dict)
    offer2.update({
        "id": "e2e-test-aws-educate",
        "title": "AWS Educate Cloud Practitioner Badge",
        "platform": "Amazon Web Services",
        "category": "Cloud Foundational",
        "certification_name": "AWS Educate Badge",
        "credential_tier": "skill_badge_lab",
        "proctoring_type": "unproctored_lab",
        "accredited_body": "Amazon Web Services",
        "url": "https://www.awseducate.com",
        "status": "Active",
        "seasonality": "student_restricted_evergreen",
        "value_usd": 0,
        "difficulty_tier": "Foundational",
        "expiry_date": "Rolling",
    })

    offer3 = dict(sample_offer_dict)
    offer3.update({
        "id": "e2e-test-closed-voucher",
        "title": "Historical Microsoft Ignite 2023 Free Exam",
        "platform": "Microsoft Azure",
        "category": "Cloud Architecture",
        "certification_name": "Azure Solutions Architect Expert",
        "status": "Registrations Closed",
        "seasonality": "annual_window",
        "expiry_date": "2023-12-31",
        "is_historical_archive": True,
    })

    return [offer1, offer2, offer3]


@pytest.fixture
def sample_news_articles() -> List[Dict[str, Any]]:
    """Provides valid sample news items."""
    return [
        {
            "id": "news-azure-wave-2026",
            "title": "Microsoft Azure Announces Spring 2026 Cloud Skills Challenge",
            "url": "https://learn.microsoft.com/en-us/training/challenges",
            "date": "2026-04-15",
            "published_date": "2026-04-15T08:00:00Z",
            "vendor": "Microsoft Azure",
            "summary": "Eligible participants can earn 100% discounted certification vouchers.",
        },
        {
            "id": "news-redhat-summit-2026",
            "title": "Red Hat Summit 2026 Hands-On Labs and Preliminary Free Assessments",
            "url": "https://www.redhat.com/en/summit",
            "date": "2026-05-20",
            "published_date": "2026-05-20T10:00:00Z",
            "vendor": "Red Hat",
            "summary": "Red Hat introduces new exam voucher allocations for summit attendees.",
        },
        {
            "id": "news-hashicorp-cert-2026",
            "title": "HashiCorp Announces Community Certification Program Updates",
            "url": "https://www.hashicorp.com/blog/community-cert-updates",
            "date": "2026-06-01",
            "published_date": "2026-06-01T12:00:00Z",
            "vendor": "HashiCorp",
            "summary": "Terraform and Vault certification vouchers made accessible for developers.",
        },
    ]


@pytest.fixture(scope="session")
def canonical_offers_schema() -> Dict[str, Any]:
    """Returns canonical JSON Schema for data/offers.json."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": ["offers"],
        "properties": {
            "$schema": {"type": "string"},
            "last_updated": {"type": "string"},
            "offers": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": [
                        "id",
                        "title",
                        "platform",
                        "category",
                        "certification_name",
                        "url",
                        "status",
                    ],
                    "properties": {
                        "id": {"type": "string", "pattern": "^[a-z0-9-]+$"},
                        "title": {"type": "string"},
                        "platform": {"type": "string"},
                        "category": {"type": "string"},
                        "certification_name": {"type": "string"},
                        "url": {"type": "string", "pattern": "^https://"},
                        "status": {"type": "string"},
                        "credential_tier": {
                            "type": "string",
                            "enum": ["proctored_exam", "skill_badge_lab"],
                        },
                        "expiry_date": {"type": ["string", "null"]},
                        "authenticity_details": {"type": ["object", "null"]},
                    },
                },
            },
        },
    }


@pytest.fixture(scope="session")
def canonical_news_schema() -> Dict[str, Any]:
    """Returns canonical JSON Schema for data/news.json."""
    return {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": ["object", "array"],
        "definitions": {
            "news_item": {
                "type": "object",
                "required": ["title", "url", "date", "published_date"],
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "url": {"type": "string", "pattern": "^https?://"},
                    "date": {"type": "string"},
                    "published_date": {"type": "string"},
                    "vendor": {"type": "string"},
                    "summary": {"type": "string"},
                },
            }
        },
    }


@pytest.fixture
def mock_png_bytes() -> Callable[[Tuple[int, int], Tuple[int, int, int]], bytes]:
    """Factory fixture returning callable to create PNG image bytes."""
    def _create_png(
        size: Tuple[int, int] = (200, 200),
        color: Tuple[int, int, int] = (255, 255, 255),
        box_rect: Optional[Tuple[int, int, int, int]] = (50, 50, 150, 150),
        box_color: Tuple[int, int, int] = (0, 120, 215),
        ensure_min_size: bool = True,
    ) -> bytes:
        img = Image.new("RGB", size, color=color)
        d = ImageDraw.Draw(img)
        if ensure_min_size:
            for i in range(0, size[1], 2):
                d.line([(0, i), (size[0], (i * 3) % size[1])], fill=((i * 37) % 256, (i * 59) % 256, (i * 101) % 256))
        if box_rect:
            d.rectangle(box_rect, fill=box_color)
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return buf.getvalue()

    return _create_png


@pytest.fixture
def parse_powershell_dict() -> Callable[[str], Dict[str, Any]]:
    """
    Defensive parser converting stringified PowerShell @{...} structures into valid dicts.
    Implements the R1 parsing requirement.
    """
    def _parse(ps_str: str) -> Dict[str, Any]:
        if not isinstance(ps_str, str):
            raise TypeError("Expected string input")
        clean = ps_str.strip()
        if not (clean.startswith("@{") and clean.endswith("}")):
            raise ValueError("Invalid PowerShell hashtable syntax: must begin with '@{' and end with '}'")

        inner = clean[2:-1].strip()
        result: Dict[str, Any] = {}
        # Matches key=value; key="value"; key='value'
        pattern = re.compile(r"([a-zA-Z0-9_]+)\s*=\s*(?:'([^']*)'|\"([^\"]*)\"|([^;]+))(?:;|$)")
        for match in pattern.finditer(inner):
            k = match.group(1).strip()
            v_sq = match.group(2)
            v_dq = match.group(3)
            v_raw = match.group(4)
            if v_sq is not None:
                val: Any = v_sq
            elif v_dq is not None:
                val = v_dq
            elif v_raw is not None:
                raw_s = v_raw.strip()
                if raw_s.lower() == "$true" or raw_s.lower() == "true":
                    val = True
                elif raw_s.lower() == "$false" or raw_s.lower() == "false":
                    val = False
                elif raw_s.isdigit():
                    val = int(raw_s)
                else:
                    val = raw_s
            else:
                val = ""
            result[k] = val
        return result

    return _parse


@pytest.fixture
def fallback_io_utils() -> Any:
    """
    Provides standard implementation of io_utils contract conforming to PROJECT.md.
    Uses jsonschema if installed; executes atomic write via tempfile + os.replace.
    """
    class IOUtilsContract:
        @staticmethod
        def validate_payload(data: Any, schema_path: Union[str, Path]) -> None:
            schema_file = Path(schema_path)
            if not schema_file.exists():
                raise FileNotFoundError(f"Schema not found at {schema_file}")
            with open(schema_file, "r", encoding="utf-8") as f:
                schema = json.load(f)
            import jsonschema
            jsonschema.validate(instance=data, schema=schema)

        @staticmethod
        def atomic_write_json(
            target_path: Union[str, Path],
            data: Any,
            schema_path: Optional[Union[str, Path]] = None,
            indent: int = 2,
            ensure_ascii: bool = False,
        ) -> None:
            target = Path(target_path)
            target.parent.mkdir(parents=True, exist_ok=True)

            if schema_path is not None:
                IOUtilsContract.validate_payload(data, schema_path)

            dir_path = target.parent
            with tempfile.NamedTemporaryFile(
                mode="w",
                dir=dir_path,
                delete=False,
                encoding="utf-8",
                suffix=".tmp",
            ) as tmp:
                json.dump(data, tmp, indent=indent, ensure_ascii=ensure_ascii)
                tmp_path = Path(tmp.name)

            try:
                os.replace(tmp_path, target)
            except Exception:
                if tmp_path.exists():
                    tmp_path.unlink()
                raise

    return IOUtilsContract


@pytest.fixture
def canonical_themes_spec() -> List[Dict[str, Any]]:
    """Returns the 10 canonical developer palettes specified in PROJECT.md."""
    return [
        {"id": "catppuccin-latte", "name": "Catppuccin Latte", "type": "light"},
        {"id": "catppuccin-mocha", "name": "Catppuccin Mocha", "type": "dark"},
        {"id": "github-dark", "name": "GitHub Dark", "type": "dark"},
        {"id": "github-light", "name": "GitHub Light", "type": "light"},
        {"id": "dracula", "name": "Dracula", "type": "dark"},
        {"id": "nord", "name": "Nord", "type": "dark"},
        {"id": "tokyo-night", "name": "Tokyo Night", "type": "dark"},
        {"id": "one-dark", "name": "One Dark", "type": "dark"},
        {"id": "gruvbox-dark", "name": "Gruvbox Dark", "type": "dark"},
        {"id": "solarized-light", "name": "Solarized Light", "type": "light"},
    ]
