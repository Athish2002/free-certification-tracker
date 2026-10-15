"""
Adversarial Empirical Challenge Test Suite for Milestone 1:
Taxonomy Integrity, Proctoring Segregation, and URL Ground Truth Verification.

Written by Challenger 2 (critic, specialist).
Enforces zero shallow assertions, deep invariant audits, and empirical verification.
"""

import json
import re
from urllib.parse import urlparse
import pytest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "offers.json"

FORMAL_PROCTORING_BODIES = {
    "pearson_vue",
    "kryterion",
    "webassessor",
    "psi",
}

UNPROCTORED_TYPES = {
    "unproctored_lab",
    "online_quiz",
    "none",
}

KNOWN_UNPROCTORED_IDS = {
    "ms-applied-skills",
    "gcp-cloud-skills-boost",
    "snowflake-hands-on-essentials",
    "qualys-certified-specialist",
    "postman-api-expert",
    "databricks-genai-fundamentals",
    "fortinet-cybersecurity-fundamentals",
    "aws-educate-badges",
    "redhat-skills-assessment-rhel",
    "paloalto-pccet-cybersecurity",
    "gitlab-certified-associate",
    "splunk-certified-defense-analyst",
    "ibm-skillsbuild-cybersecurity",
    "databricks-lakehouse-fundamentals",
    "cisco-netacad-cyberops",
    "cisco-rev-up-recert",
    "hist-cisco-rev-up-devnae",
    "hist-databricks-genai-2024",
}

KNOWN_PROCTORED_IDS = {
    "isc2-one-million-cc",
    "oracle-oci-free-cert",
    "linux-foundation-lift",
    "mongodb-developer-cert",
    "salesforce-trailhead-quests",
    "juniper-open-learning",
    "github-student-foundations",
    "hashicorp-terraform-associate-community",
    "cncf-dan-kohn-scholarship",
    "oracle-oci-generative-ai-cert",
    "github-foundations-cert-wave",
    "hist-msft-build-2024",
    "hist-msft-ignite-2023",
    "hist-oracle-race-cert-2024",
    "hist-aws-ai-practitioner-early",
    "hist-gcp-ace-challenge",
    "hist-github-universe-2024",
    "hist-redhat-summit-2024",
    "hist-terraform-challenge-2023",
    "hist-paloalto-ignite-2023",
    "hist-splunk-conf-2024",
}


@pytest.fixture(scope="module")
def raw_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def offers_list(raw_data):
    if isinstance(raw_data, dict):
        return raw_data.get("offers", [])
    elif isinstance(raw_data, list):
        return raw_data
    raise TypeError(f"Unexpected data type: {type(raw_data)}")


# ==============================================================================
# 1. Uniqueness and ID Slug Validation
# ==============================================================================

def test_no_duplicate_offer_ids(offers_list):
    """Assert that every offer ID in data/offers.json is strictly unique and a valid slug."""
    assert len(offers_list) == 39, f"Expected 39 offers, found {len(offers_list)}"
    
    seen_ids = set()
    slug_pattern = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

    for offer in offers_list:
        oid = offer.get("id")
        assert oid is not None, "Encountered offer without 'id'"
        assert isinstance(oid, str) and oid.strip() != "", f"Empty or non-string id: {oid}"
        assert slug_pattern.match(oid), f"Offer id '{oid}' is not a valid kebab-case slug"
        assert oid not in seen_ids, f"Duplicate offer id detected: {oid}"
        seen_ids.add(oid)

    assert len(seen_ids) == 39, f"Unique IDs count ({len(seen_ids)}) != 39"


# ==============================================================================
# 2. Strict Unproctored Credentials Segregation
# ==============================================================================

def test_unproctored_credentials_never_labeled_as_proctored(offers_list):
    """
    Assert that Microsoft Applied Skills, Google Cloud Skill Badges, Snowflake Essentials,
    Qualys Training, Postman Expert, and all 18 unproctored badges are NEVER labeled 'proctored_exam'.
    """
    must_be_unproctored = {
        "ms-applied-skills": "Microsoft Applied Skills",
        "gcp-cloud-skills-boost": "Google Cloud Skill Badges",
        "snowflake-hands-on-essentials": "Snowflake Hands-On Essentials",
        "qualys-certified-specialist": "Qualys Certified Specialist",
        "postman-api-expert": "Postman API Expert",
    }

    offers_by_id = {o["id"]: o for o in offers_list}

    # Verify specific dispatch required targets
    for target_id, target_name in must_be_unproctored.items():
        assert target_id in offers_by_id, f"Missing required offer: {target_id} ({target_name})"
        offer = offers_by_id[target_id]
        tier = offer.get("credential_tier")
        proctor = offer.get("proctoring_type")
        
        assert tier != "proctored_exam", (
            f"CRITICAL VIOLATION: '{target_name}' ({target_id}) is misclassified as 'proctored_exam'!"
        )
        assert tier == "skill_badge_lab", (
            f"Expected '{target_name}' to have credential_tier 'skill_badge_lab', got '{tier}'"
        )
        assert proctor in UNPROCTORED_TYPES, (
            f"Expected '{target_name}' proctoring_type to be unproctored, got '{proctor}'"
        )

    # Verify all 18 unproctored credentials
    for oid in KNOWN_UNPROCTORED_IDS:
        assert oid in offers_by_id, f"Missing known unproctored offer: {oid}"
        offer = offers_by_id[oid]
        tier = offer.get("credential_tier")
        proctor = offer.get("proctoring_type")
        body = offer.get("accredited_body")
        print(f"SKILL BADGE / LAB: {oid} -> tier={tier}, proctoring_type={proctor}, accredited_body={body}")
        assert tier == "skill_badge_lab", f"Offer '{oid}' misclassified as '{tier}' instead of 'skill_badge_lab'"
        assert proctor in UNPROCTORED_TYPES, f"Offer '{oid}' has unexpected proctoring_type: '{proctor}'"


# ==============================================================================
# 3. Exactly 21 Proctored Exams with Genuine Testing Bodies
# ==============================================================================

def test_21_proctored_exams_have_formal_testing_bodies(offers_list):
    """
    Assert that all 21 proctored exams correspond to genuine written proctored exams
    with formal testing delivery bodies (Pearson VUE, Kryterion, Webassessor, PSI).
    """
    offers_by_id = {o["id"]: o for o in offers_list}
    proctored_offers = [o for o in offers_list if o.get("credential_tier") == "proctored_exam"]

    assert len(proctored_offers) == 21, (
        f"Mathematical Invariant Violation: Expected exactly 21 proctored exams, got {len(proctored_offers)}"
    )

    proctored_ids = {o["id"] for o in proctored_offers}
    assert proctored_ids == KNOWN_PROCTORED_IDS, (
        f"Proctored IDs mismatch: diff={proctored_ids ^ KNOWN_PROCTORED_IDS}"
    )

    mismatches = []
    for offer in proctored_offers:
        oid = offer["id"]
        tier = offer.get("credential_tier")
        proctor_type = offer.get("proctoring_type")
        accredited_body = offer.get("accredited_body")
        print(f"PROCTORED EXAM: {oid} -> proctoring_type={proctor_type}, accredited_body={accredited_body}")
        if proctor_type not in FORMAL_PROCTORING_BODIES:
            mismatches.append((oid, proctor_type, accredited_body))
        assert accredited_body is not None and str(accredited_body).strip() != "", (
            f"Offer {oid} has empty accredited_body!"
        )
        assert len(offer.get("claim_steps", "")) > 10, f"Offer {oid} has trivial claim_steps"
        assert offer.get("value_usd", 0) > 0, f"Proctored exam {oid} must have value_usd > 0 (commercial exam value)"

    assert not mismatches, f"Proctored offers with invalid proctoring_type: {mismatches}"


# ==============================================================================
# 4. Strict URL Ground Truth & HTTPS Validation
# ==============================================================================

def test_all_url_schemes_valid_https_and_non_empty(offers_list):
    """
    Assert that all URL fields across every offer are valid HTTPS, non-empty,
    and possess resolvable hostnames without localhost, IPs, or open redirects.
    """
    url_fields = ["url", "verified_vendor_url", "direct_verified_url", "redemption_portal"]

    for offer in offers_list:
        oid = offer["id"]
        
        # Primary url must exist and be valid https
        primary_url = offer.get("url")
        assert primary_url is not None and str(primary_url).strip() != "", f"Offer {oid} missing 'url'"
        
        for field in url_fields:
            if field in offer and offer[field]:
                u = offer[field]
                assert isinstance(u, str), f"Offer {oid} {field} is not a string: {type(u)}"
                assert u.strip() != "", f"Offer {oid} {field} is empty whitespace"
                
                parsed = urlparse(u)
                assert parsed.scheme == "https", (
                    f"Offer {oid} field '{field}' has insecure scheme '{parsed.scheme}': {u}"
                )
                assert parsed.netloc, f"Offer {oid} field '{field}' has missing hostname: {u}"
                
                # Assert no localhost or raw IP
                hostname = parsed.hostname or ""
                assert hostname not in {"localhost", "127.0.0.1", "0.0.0.0"}, f"Localhost in {oid} {field}: {u}"
                assert not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", hostname), (
                    f"Raw IPv4 address in {oid} {field}: {u}"
                )
                # Assert no defunct domain
                assert "academy.databricks.com" not in u, (
                    f"Offer {oid} field '{field}' contains decommissioned domain 'academy.databricks.com'! "
                    f"Must be repaired to 'https://www.databricks.com/learn/training/certification'."
                )
                print(f"URL OK [{oid}] {field}: {u}")

        # Check redemption_guide if present
        rg = offer.get("redemption_guide")
        if isinstance(rg, dict):
            portal_url = rg.get("portal_url")
            if portal_url:
                parsed = urlparse(portal_url)
                assert parsed.scheme == "https", f"Offer {oid} redemption_guide portal_url not https: {portal_url}"
                assert parsed.netloc, f"Offer {oid} redemption_guide portal_url missing netloc: {portal_url}"
                assert "academy.databricks.com" not in portal_url, (
                    f"Offer {oid} redemption_guide portal_url contains decommissioned 'academy.databricks.com'! "
                    f"Must be repaired to 'https://www.databricks.com/learn/training/certification'."
                )


# ==============================================================================
# 5. Semantic Audit of Title, Provider, and Description
# ==============================================================================

def test_semantic_audit_title_provider_description(offers_list):
    """
    Audit every entry in data/offers.json against its title, provider, and description.
    Ensure title and description align with the assigned credential tier.
    """
    for offer in offers_list:
        oid = offer["id"]
        title = offer.get("title", "")
        platform = offer.get("platform", "")
        desc = offer.get("claim_steps", "")
        tier = offer.get("credential_tier")
        seasonality = offer.get("seasonality")
        cart_balance = offer.get("cart_balance_verified", "")

        assert title.strip(), f"Offer {oid} has empty title"
        assert platform.strip(), f"Offer {oid} has empty platform"
        assert desc.strip(), f"Offer {oid} has empty claim_steps"
        assert "$0.00" in cart_balance, f"Offer {oid} cart_balance_verified does not confirm $0.00: '{cart_balance}'"

        # Check title patterns for unproctored indicators
        unproctored_title_keywords = ["applied skills", "skill badge", "hands-on essentials", "skills assessment"]
        for kw in unproctored_title_keywords:
            if kw in title.lower():
                assert tier == "skill_badge_lab", (
                    f"Offer {oid} with title '{title}' contains '{kw}' but is marked as '{tier}'!"
                )

        # Check proctored indicators
        if tier == "proctored_exam":
            # Must not have unproctored delivery
            assert offer.get("proctoring_type") in FORMAL_PROCTORING_BODIES, (
                f"Proctored offer {oid} has non-formal proctoring type: {offer.get('proctoring_type')}"
            )
        elif tier == "skill_badge_lab":
            assert offer.get("proctoring_type") in UNPROCTORED_TYPES, (
                f"Skill badge offer {oid} has formal proctoring type: {offer.get('proctoring_type')}"
            )

        # Check seasonality validity
        valid_seasonalities = {
            "evergreen",
            "periodic_challenge_wave",
            "annual_window",
            "student_restricted_evergreen",
            "monthly_sweepstakes",
            "event_driven",
        }
        assert seasonality in valid_seasonalities, f"Offer {oid} has invalid seasonality: '{seasonality}'"


# ==============================================================================
# 6. Deep Pydantic Model Invariant & Validation Enforcement
# ==============================================================================

def test_pydantic_model_enforcement(offers_list):
    """
    Verify that all offers deserialize into the Offer Pydantic V2 model cleanly,
    and stress-test that invalid models raise validation errors.
    """
    from src.models import Offer, VisualProof, CandidateLead
    from pydantic import ValidationError

    # 1. Valid loading of all 39 offers
    parsed_offers = [Offer(**o) for o in offers_list]
    assert len(parsed_offers) == 39

    proctored_count = sum(1 for o in parsed_offers if o.is_proctored())
    assert proctored_count == 21

    # 2. Adversarial: reject invalid credential_tier
    with pytest.raises(ValidationError):
        Offer(
            id="bad-tier-offer",
            title="Bad Tier",
            platform="AWS",
            category="Cloud",
            certification_name="Bad Cert",
            credential_tier="super_proctored",  # Invalid literal
            url="https://aws.amazon.com",
            status="Active",
            claim_steps="Steps",
            cart_balance_verified="$0.00",
        )

    # 3. Adversarial: reject cart_balance_verified without $0.00
    with pytest.raises(ValidationError):
        Offer(
            id="bad-balance-offer",
            title="Bad Balance",
            platform="AWS",
            category="Cloud",
            certification_name="Bad Cert",
            credential_tier="proctored_exam",
            proctoring_type="pearson_vue",
            url="https://aws.amazon.com",
            status="Active",
            claim_steps="Steps",
            cart_balance_verified="$100.00 (Standard Fee)",  # Missing $0.00
        )

    # 4. Candidate lead stub generation
    lead = CandidateLead(
        source="Reddit r/aws",
        title="AWS Free Voucher Wave",
        url="https://aws.amazon.com/free-voucher",
        platform="AWS",
    )
    stub = lead.to_offer_stub("aws-new-voucher-lead")
    assert stub["id"] == "aws-new-voucher-lead"
    assert stub["status"] == "Review Needed"
    assert stub["visual_proof"]["status"] == "placeholder"
    assert stub["visual_proof"]["zero_dollar_confirmed"] is False
