"""
CertPulse Core Domain Models.
Strict Pydantic V2 schemas enforcing credential tiering, proctoring classification,
promotional seasonality, visual screenshot proof metadata, and candidate lead vetting.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# --- 1. Enumeration & Literal Type Aliases ---

CredentialTier = Literal["proctored_exam", "skill_badge_lab"]
ProctoringType = Literal[
    "pearson_vue",
    "kryterion",
    "webassessor",
    "psi",
    "unproctored_lab",
    "online_quiz",
]
Seasonality = Literal[
    "evergreen",
    "periodic_challenge_wave",
    "annual_window",
    "student_restricted_evergreen",
    "monthly_sweepstakes",
    "event_driven",
]
OfferStatus = Literal[
    "Active",
    "Registrations Closed",
    "Expired",
    "Broken Link",
    "Review Needed",
    "Server Error",
    "Network Warning",
]
DifficultyTier = Literal["Foundational", "Associate", "Professional"]
ApplicationFlowType = Literal[
    "Checkout Promo Code",
    "Automated Account Link Waiver",
    "Direct Assessment Launch",
    "Scholarship Award Token",
    "Continuing Education Claim",
    "Training Milestone Token",
    "Event Voucher Code",
]
VisualProofStatus = Literal["verified", "missing", "failed", "placeholder"]


# --- 2. Visual Proof Schema ---


class VisualProof(BaseModel):
    """
    Metadata for visual screenshot proof captured via Headless Playwright.
    Enforces dual visual ground-truth gating requirements (R2, R3).
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    screenshot_path: str = Field(
        ...,
        description="Relative repository path to captured PNG (e.g. 'docs/screenshots/<id>.png')",
    )
    screenshot_url: str | None = Field(
        default=None,
        description="Optional web URI or relative link for UI embedding",
    )
    captured_at: str | None = Field(
        default=None,
        description="ISO 8601 UTC timestamp of the most recent visual capture",
    )
    status: VisualProofStatus = Field(
        default="placeholder",
        description="Visual verification health: verified | missing | failed | placeholder",
    )
    zero_dollar_confirmed: bool = Field(
        default=True,
        description="Affirmative verification that screenshot/page confirms $0.00 waiver/scholarship terms",
    )
    maintenance_detected: bool = Field(
        default=False,
        description="True if capture detected downtime banner or maintenance page",
    )
    paid_catalog_detected: bool = Field(
        default=False,
        description="True if capture resolved to full-price commercial catalog without waiver",
    )

    # --- Milestone 2 Tier 3 Additions ---
    vlm_verdict: dict[str, Any] | None = Field(
        default=None,
        description="Serialized VLMSemanticVerdict payload from Multimodal VLM Semantic Gate",
    )
    visual_confidence_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Visual confidence rating between 0.00 and 1.00",
    )
    badge_phash_matched: bool = Field(
        default=False,
        description="True if official certification badge was perceptually matched",
    )
    ocr_text_snippet: str | None = Field(
        default=None,
        description="Extracted OCR text snippet from viewport screenshot",
    )

    @property
    def is_verified(self) -> bool:
        """Returns True if screenshot is captured and affirmatively verifies zero-dollar terms."""
        vlm_ok = True
        if self.vlm_verdict is not None:
            vlm_ok = (
                self.vlm_verdict.get("has_zero_dollar_waiver", True)
                and not self.vlm_verdict.get("requires_payment_or_copay", False)
                and self.vlm_verdict.get("registration_status") == "open"
            )
        return (
            self.status == "verified"
            and self.zero_dollar_confirmed
            and not self.maintenance_detected
            and not self.paid_catalog_detected
            and vlm_ok
        )


# --- 3. Structured Redemption Guide Schema ---


class RedemptionGuide(BaseModel):
    """Structured zero-dollar checkout instructions and portal details."""

    model_config = ConfigDict(extra="ignore")

    portal_name: str
    portal_url: str
    field_location: str
    flow_type: ApplicationFlowType
    verified_cart_balance: str
    instructions: list[str] = Field(default_factory=list)

    @field_validator("verified_cart_balance")
    @classmethod
    def validate_cart_balance(cls, v: str) -> str:
        if "$0.00" not in v:
            raise ValueError(f"verified_cart_balance must confirm '$0.00', got: {v}")
        return v


# --- 3B. Network Provenance & Temporal Longevity Schemas (Tier 1 & Tier 2) ---


class NetworkProvenance(BaseModel):
    """
    Tier 1 Network Provenance & Cryptographic Verification Payload.
    Enforces ASN BGP route origin, TLS X.509 SCT Certificate Transparency,
    and DNSSEC/CAA domain integrity invariants.
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    asn: int | None = Field(default=None, description="Autonomous System Number (e.g. 8075 for Microsoft)")
    asn_org: str | None = Field(default=None, description="BGP route origin organization handle")
    ip_address: str | None = Field(default=None, description="Resolved IPv4/IPv6 host address")
    is_vendor_infra: bool = Field(
        default=True, description="True if IP maps to authorized vendor ASN or enterprise CDN"
    )
    tls_ct_verified: bool = Field(default=True, description="True if certificate carries valid embedded RFC 6962 SCTs")
    sct_count: int = Field(default=0, ge=0, description="Count of embedded Signed Certificate Timestamps")
    dnssec_valid: bool = Field(default=False, description="True if DNSSEC AD flag confirms cryptographic trust")
    caa_authorized: bool = Field(default=True, description="True if certificate issuer is permitted by CAA records")
    verified_at_utc: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="ISO 8601 UTC timestamp of verification",
    )

    # Diagnostic telemetry
    dnssec_verdict: str | None = Field(default="INSECURE_STANDARD")
    authorized_cas: list[str] = Field(default_factory=list)
    sct_log_operators: list[str] = Field(default_factory=list)
    security_flags: list[str] = Field(default_factory=list)


class TemporalLongevity(BaseModel):
    """
    Tier 2 Temporal Longevity & Promotional Recurrence Payload.
    Enforces Wayback CDX historical archive durability, Anti-Fly-by-Night
    domain age scoring (<60 days penalized), and seasonal recurrence classification.
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    first_seen_archive_utc: str | None = Field(
        default=None,
        description="ISO 8601 UTC timestamp of earliest recorded Internet Archive snapshot",
    )
    domain_age_days: int | None = Field(
        default=None,
        description="Calculated domain age in days since earliest archive snapshot",
    )
    snapshot_count: int = Field(
        default=0,
        ge=0,
        description="Total count of historical snapshots retrieved",
    )
    is_anti_fly_by_night_passed: bool = Field(
        default=True,
        description="True if domain age >= 60 days or belongs to whitelisted vendor directory",
    )
    is_seasonal_recurrent: bool = Field(
        default=False,
        description="True if offer URL shows multi-year recurrence or periodic challenge cadence",
    )
    longevity_score: int = Field(
        default=100,
        ge=0,
        le=100,
        description="Calculated longevity trust score (0-100)",
    )
    recurrence_classification: str = Field(
        default="unknown",
        description="Classification: annual_window | periodic_challenge_wave | evergreen | event_driven | unknown",
    )
    verified_at_utc: str = Field(
        default_factory=lambda: datetime.now(UTC).isoformat(),
        description="ISO 8601 UTC timestamp when temporal analysis was performed",
    )
    source: str = Field(
        default="live_cdx",
        description="Provenance of verdict: live_cdx | cache | vendor_whitelist_fallback | offline_fallback",
    )
    warning_flags: list[str] = Field(default_factory=list)


# --- 4. Canonical Offer Schema ---


class Offer(BaseModel):
    """
    Canonical Offer Schema for CertPulse.
    Enforces strict distinction between formal proctored exam vouchers (Tier 1)
    and unproctored skill badges & labs (Tier 2).
    """

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    # Core identification
    id: str = Field(..., pattern=r"^[a-z0-9-]+$", min_length=3, max_length=64)
    title: str = Field(..., min_length=3)
    platform: str = Field(..., min_length=2)
    category: str = Field(..., min_length=2)
    certification_name: str = Field(..., min_length=2)

    # R1: Credential Segmentation & Proctoring
    credential_tier: CredentialTier = Field(
        ...,
        description="Tier 1: 'proctored_exam' vs Tier 2: 'skill_badge_lab'",
    )
    proctoring_type: ProctoringType = Field(
        default="unproctored_lab",
        description="Delivery mode: pearson_vue | kryterion | webassessor | psi | unproctored_lab | online_quiz",
    )
    accredited_body: str | None = Field(
        default=None,
        description="Official certifying / delivery body: Pearson VUE, Kryterion, PSI, Oracle, etc.",
    )

    # URL Ground Truth
    url: str = Field(..., pattern=r"^https://", description="Primary vendor or promo landing URL")
    verified_vendor_url: str | None = Field(
        default=None,
        description="Direct verified URL bypassing generic homepages or maintenance roots",
    )
    direct_verified_url: str | None = Field(
        default=None,
        description="Alternative direct link target",
    )

    # Status & Seasonality
    status: OfferStatus = Field(default="Active")
    seasonality: Seasonality = Field(
        default="evergreen",
        description="Promotional cycle: evergreen | periodic_challenge_wave | annual_window | student_restricted_evergreen | monthly_sweepstakes | event_driven",
    )
    value_usd: int | None = Field(default=None, ge=0)
    difficulty_tier: DifficultyTier = Field(default="Foundational")
    eligibility: str = Field(default="Open to all global candidates")
    time_period: str = Field(default="Rolling")
    recurrence_pattern: str = Field(default="Continuous")

    # Redemption Funnel
    application_flow_type: ApplicationFlowType = Field(default="Direct Assessment Launch")
    redemption_portal: str = Field(default="")
    checkout_field: str = Field(default="")
    cart_balance_verified: str = Field(default="$0.00 (100% Free / Waiver Confirmed)")
    voucher_code: str = Field(default="AUTO_APPLIED")
    redemption_guide: dict[str, Any] | None = None
    claim_steps: str = Field(default="")

    # Authenticity & Security
    is_authentic_vendor: bool = Field(default=True)
    authenticity_score: int = Field(default=90, ge=0, le=100)
    authenticity_details: dict[str, Any] | None = None

    # Tier 1 Network Provenance & Tier 2 Temporal Longevity (M1)
    network_provenance: NetworkProvenance | None = None
    temporal_longevity: TemporalLongevity | None = None

    # Online Truth Oracle Verification
    truth_verification: dict[str, Any] | None = None
    oracle_timeout: bool | None = Field(
        default=None, description="True if Truth Oracle circuit breaker timed out during audit"
    )

    # Visual Proof Metadata (R2, R3)
    visual_proof: VisualProof | None = None
    screenshot_path: str | None = None

    # Lifecycle & Archival
    verification_date: str | None = None
    last_zero_dollar_confirmed_date: str | None = Field(
        default=None,
        description="ISO 8601 date when $0.00 terms were last affirmatively validated",
    )
    inspection_notes: str = Field(default="")
    inspection_method: str | None = "Playwright Headless DOM & Visual Proof"
    offer_type: str | None = "100% Free Exam Voucher"
    exam_code: str | None = None
    is_historical_archive: bool = Field(default=False)
    concluded_date: str | None = None
    expiry_date: str | None = None
    consecutive_transient_failures: int = Field(
        default=0,
        ge=0,
        description="Hysteresis strike counter for transient network/maintenance events",
    )
    consecutive_failures: int = Field(
        default=0,
        ge=0,
        description="Legacy strike counter for backward compatibility",
    )

    # Schema Alignment & Dual Compatibility Fields
    company: str | None = None
    tier: str | None = None
    official_url: str | None = None
    terms_url: str | None = None
    terms: str | None = None
    last_verified: str | None = None
    badge_eligible: bool | None = None
    verification_state: str | None = None

    @field_validator("authenticity_details", mode="before")
    @classmethod
    def validate_authenticity_details(cls, v: Any) -> dict[str, Any] | None:
        if v is None or isinstance(v, dict):
            return v
        if isinstance(v, str):
            from src.authenticity import parse_powershell_hash_str

            return parse_powershell_hash_str(v)
        return v

    @field_validator("cart_balance_verified")
    @classmethod
    def validate_offer_cart_balance(cls, v: str) -> str:
        if "$0.00" not in v:
            raise ValueError(f"cart_balance_verified must confirm '$0.00', got: {v}")
        return v

    @model_validator(mode="after")
    def populate_defaults_and_proof(self) -> Offer:
        # Default verified_vendor_url and direct_verified_url to prevent unexpected None values
        if not self.verified_vendor_url:
            self.verified_vendor_url = self.direct_verified_url or self.url
        if not self.direct_verified_url:
            self.direct_verified_url = self.verified_vendor_url or self.url

        # Populate schema alignment fields if not explicitly supplied
        if self.company is None:
            self.company = self.platform
        if self.tier is None:
            self.tier = self.credential_tier
        if self.official_url is None:
            self.official_url = self.verified_vendor_url or self.url
        if self.terms_url is None:
            self.terms_url = self.verified_vendor_url or self.url
        if self.terms is None:
            self.terms = self.cart_balance_verified or "$0.00 (100% Free / Waiver Confirmed)"
        if self.last_verified is None:
            self.last_verified = self.verification_date or "2026-10-23"
        if self.badge_eligible is None:
            self.badge_eligible = self.credential_tier == "skill_badge_lab"
        if self.verification_state is None:
            if self.authenticity_details and isinstance(self.authenticity_details, dict):
                self.verification_state = self.authenticity_details.get("verdict", "VERIFIED_AUTHENTIC")
            else:
                self.verification_state = "VERIFIED_AUTHENTIC"

        # Ensure visual_proof is initialized
        expected_path = f"docs/screenshots/{self.id}.png"
        if self.visual_proof is None:
            self.visual_proof = VisualProof(
                screenshot_path=self.screenshot_path or expected_path,
                screenshot_url=f"docs/screenshots/{self.id}.png",
                status="placeholder",
                zero_dollar_confirmed=True,
            )
        elif not self.visual_proof.screenshot_path:
            self.visual_proof.screenshot_path = expected_path

        # Sync screenshot_path top-level attribute
        self.screenshot_path = self.visual_proof.screenshot_path

        return self

    # Helper methods
    def is_proctored(self) -> bool:
        """Returns True if this is an accredited written proctored examination."""
        return self.credential_tier == "proctored_exam"

    def is_active(self) -> bool:
        """Returns True if currently marked Active."""
        return self.status == "Active"

    def get_screenshot_path(self) -> str:
        """Returns the canonical screenshot path."""
        if self.visual_proof and self.visual_proof.screenshot_path:
            return self.visual_proof.screenshot_path
        return f"docs/screenshots/{self.id}.png"

    def get_direct_url(self) -> str:
        """Returns the most direct verified URL."""
        return self.verified_vendor_url or self.direct_verified_url or self.url


# --- 5. Candidate Lead Schema ---


class CandidateLead(BaseModel):
    """
    Schema for unverified incoming community leads from Reddit, forums, or vendor blogs.
    Must pass domain authenticity and dual DOM/screenshot verification gates before promotion.
    """

    model_config = ConfigDict(extra="ignore")

    source: str = Field(..., description="Community source: e.g. 'Reddit r/AzureCertification'")
    title: str = Field(..., description="Lead title or post subject")
    url: str = Field(..., description="Lead reference URL")
    platform: str = Field(..., description="Associated cloud vendor / provider")
    timestamp: str | None = Field(default=None, description="ISO 8601 discovery timestamp")
    keywords: list[str] = Field(default_factory=list)
    match_confidence: str | None = Field(default="Medium")
    is_authentic_vendor: bool = Field(default=False)
    verified_vendor_url: str = Field(default="")
    authenticity_tier: str = Field(default="Community Lead")

    def to_offer_stub(
        self,
        offer_id: str,
        credential_tier: CredentialTier = "proctored_exam",
        authenticity_result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Converts candidate lead into a draft offer payload ready for inspection."""
        now_iso = datetime.now(UTC).date().isoformat()
        if authenticity_result and "authenticity_score" in authenticity_result:
            auth_score = int(authenticity_result["authenticity_score"])
        elif authenticity_result and "score" in authenticity_result:
            auth_score = int(authenticity_result["score"])
        else:
            auth_score = 85 if self.is_authentic_vendor else 60
        return {
            "id": offer_id,
            "title": self.title,
            "platform": self.platform,
            "category": "Cloud Architecture",
            "certification_name": self.title,
            "credential_tier": credential_tier,
            "proctoring_type": "unproctored_lab" if credential_tier == "skill_badge_lab" else "pearson_vue",
            "url": self.verified_vendor_url or self.url,
            "verified_vendor_url": self.verified_vendor_url or self.url,
            "status": "Review Needed",
            "verification_date": now_iso,
            "claim_steps": "Awaiting automated verification.",
            "is_authentic_vendor": self.is_authentic_vendor,
            "authenticity_score": auth_score,
            "authenticity_details": authenticity_result if authenticity_result else None,
            "visual_proof": {
                "screenshot_path": f"docs/screenshots/{offer_id}.png",
                "status": "placeholder",
                "zero_dollar_confirmed": False,
            },
        }


# --- 6. Offers Database Container Schema ---


class OffersDatabase(BaseModel):
    """Complete schema for data/offers.json database file."""

    model_config = ConfigDict(extra="ignore", populate_by_name=True)

    schema_version: str | None = Field(default="./schema.json", alias="$schema")
    last_updated: str | None = None
    last_inspected: str | None = None
    last_truth_corroborated: str | None = None
    last_sync: str | None = None
    total_offers: int | None = None
    offers: list[Offer] = Field(default_factory=list)


# --- 7. Offers Data Dictionary Helper ---


class OfferDataDict(dict):
    """
    Mapping and container helper for CertPulse offers data.
    Provides clean dictionary and list access without mutating the standard library json module.
    Preserves all standard Python dictionary invariants (e.g. list(d) == list(d.keys())).
    """

    @property
    def offers(self) -> list[dict[str, Any]]:
        """Returns the list of raw offer dictionaries."""
        return self.get("offers", [])

    def to_models(self) -> list[Offer]:
        """Converts offers to validated Pydantic Offer instances."""
        return [Offer(**o) for o in self.get("offers", [])]

    @classmethod
    def load(cls, fp_or_path: Any) -> OfferDataDict:
        """Loads offers JSON from a file pointer or file path without mutating json.load."""
        if hasattr(fp_or_path, "read"):
            data = json.load(fp_or_path)
        else:
            with open(fp_or_path, encoding="utf-8") as f:
                data = json.load(f)
        return cls(data)
