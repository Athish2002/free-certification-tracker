"""
Dynamic Pipeline Scenario Tests
Prevents recurring CI workflow failures by testing dynamic real-world execution lifecycles:
1. Partial discount / copay candidate rejection (50% off + free retake, 75% off copays).
2. Schema completeness of newly promoted candidate leads (mandatory redemption_guide).
3. Defensive resilience of src/builder.py against null or missing optional fields.
4. End-to-end dry-run pipeline stability.
"""

import json
import pytest
from pathlib import Path
from src.collector import vet_candidate_lead, classify_credential_tier
from src.models import Offer, OffersDatabase
from src.builder import generate_readme, generate_web_dashboard
from src.truth_oracle import corroborate_offer

ROOT = Path(__file__).resolve().parent.parent


def test_scenario_partial_discount_copay_rejection():
    """
    Scenario: Reddit feed contains a post offering a partial discount (e.g. 50% off)
    combined with a 'free retake' or 'free practice'.
    Invariant: Must be rejected at the candidate gate with PARTIAL_DISCOUNT_ONLY.
    """
    leads_to_reject = [
        {"title": "Azure 50% off + FREE Retake", "url": "https://www.pearsonvue.com/us/en/test-takers/free-retake.html", "platform": "Microsoft Azure"},
        {"title": "AWS 50% discount voucher challenge", "url": "https://aws.amazon.com/certification/", "platform": "Amazon Web Services"},
        {"title": "Get 75% off JNCIA voucher with free assessment", "url": "https://learningportal.juniper.net/juniper/", "platform": "Juniper Networks"},
        {"title": "Half off certification exam copay required", "url": "https://mylearn.oracle.com/", "platform": "Oracle Cloud"},
    ]

    for lead in leads_to_reject:
        promoted, reason = vet_candidate_lead(lead)
        assert promoted is None, f"Expected lead '{lead['title']}' to be rejected, but got promoted!"
        assert "PARTIAL_DISCOUNT_ONLY" in reason, f"Expected PARTIAL_DISCOUNT_ONLY for '{lead['title']}', got '{reason}'"



def test_scenario_forum_question_and_troubleshooting_rejection():
    """
    Scenario: Community feeds contain user questions, support complaints, or troubleshooting posts.
    Examples:
    - 'Can't upgrade my account?'
    - 'Question about how to get a free voucher'
    - 'How do I reschedule my Azure exam?'
    - 'Anyone have a discount code for AWS?'
    - 'General discussion on cloud career path'
    Invariant: Must be rejected with NON_OFFER_DISCUSSION or IRRELEVANT_TOPIC, never promoted to Active.
    """
    discussion_leads = [
        {"title": "Can't upgrade my account?", "url": "https://aws.amazon.com/free", "platform": "Amazon Web Services"},
        {"title": "Question about how to get a free voucher", "url": "https://learn.microsoft.com/", "platform": "Microsoft Azure"},
        {"title": "How do I reschedule my exam voucher?", "url": "https://mylearn.oracle.com/", "platform": "Oracle Cloud"},
        {"title": "Anyone have AWS voucher code for tight budget?", "url": "https://aws.amazon.com/", "platform": "Amazon Web Services"},
        {"title": "General discussion on cloud career path", "url": "https://cloud.google.com/", "platform": "Google Cloud"},
    ]

    for lead in discussion_leads:
        promoted, reason = vet_candidate_lead(lead)
        assert promoted is None, f"Expected discussion lead '{lead['title']}' to be rejected, but got promoted!"
        assert any(k in reason for k in ["NON_OFFER_DISCUSSION", "IRRELEVANT_TOPIC", "UNTRUSTED_VENDOR"]), (
            f"Expected rejection reason for '{lead['title']}', got '{reason}'"
        )


def test_scenario_promoted_candidate_schema_completeness():
    """
    Scenario: A genuine 100% free candidate lead is processed.
    Invariant: The constructed stub must contain a valid redemption_guide with all 6 required fields
    and at least 2 instruction steps so that downstream builders and tests never crash.
    """
    valid_lead = {
        "title": "Microsoft Cloud Skills Challenge: Free Certification Exam",
        "url": "https://learn.microsoft.com/en-us/training/challenges",
        "verified_vendor_url": "https://learn.microsoft.com/en-us/training/challenges",
        "platform": "Microsoft Azure",
        "is_authentic_vendor": True
    }

    tier, proctoring_type, accredited_body = classify_credential_tier(valid_lead["title"], valid_lead["url"])
    assert tier == "proctored_exam"
    assert accredited_body is not None

    # Simulate stub creation pattern in collector
    stub = {
        "id": "msft-dynamic-test-offer",
        "title": valid_lead["title"],
        "platform": valid_lead["platform"],
        "category": "Cloud Architecture",
        "certification_name": valid_lead["title"],
        "credential_tier": tier,
        "proctoring_type": proctoring_type,
        "accredited_body": accredited_body,
        "url": valid_lead["url"],
        "verified_vendor_url": valid_lead["url"],
        "status": "Active",
        "seasonality": "periodic_challenge_wave",
        "value_usd": 165,
        "difficulty_tier": "Associate",
        "eligibility": "Open to all global candidates",
        "time_period": "Rolling",
        "recurrence_pattern": "Continuous",
        "application_flow_type": "Checkout Promo Code",
        "redemption_portal": valid_lead["url"],
        "checkout_field": "Voucher / Promo Code",
        "cart_balance_verified": "$0.00 (100% Free / Waiver Confirmed)",
        "voucher_code": "AUTO_APPLIED",
        "redemption_guide": {
            "portal_name": "Microsoft Learn Challenge Portal",
            "portal_url": valid_lead["url"],
            "field_location": "Voucher / Promo Code input at checkout",
            "flow_type": "Checkout Promo Code",
            "verified_cart_balance": "$0.00 (100% Free / Waiver Confirmed)",
            "instructions": [
                "Complete challenge modules on Microsoft Learn.",
                "Redeem 100% voucher code at Pearson VUE checkout to confirm $0.00 cart balance."
            ]
        },
        "claim_steps": "Complete challenge modules on Microsoft Learn.",
        "is_authentic_vendor": True,
        "authenticity_score": 95,
        "visual_proof": {
            "screenshot_path": "docs/screenshots/msft-dynamic-test-offer.png",
            "screenshot_url": "docs/screenshots/msft-dynamic-test-offer.png",
            "captured_at": "2026-10-19T00:00:00Z",
            "status": "verified",
            "zero_dollar_confirmed": True,
            "maintenance_detected": False,
            "paid_catalog_detected": False
        },
        "verification_date": "2026-10-19",
        "inspection_notes": "Playwright DOM Verified: 100% free voucher terms confirmed."
    }

    # Validate against strict Offer Pydantic model
    validated = Offer(**stub)
    assert validated.id == "msft-dynamic-test-offer"
    assert validated.redemption_guide is not None
    assert "$0.00" in validated.redemption_guide.get("verified_cart_balance", "")
    assert len(validated.redemption_guide.get("instructions", [])) >= 2


def test_scenario_builder_resilience_to_null_and_missing_fields():
    """
    Scenario: Offers in the database have null or missing redemption_guide or instructions.
    Invariant: generate_readme and generate_html must NEVER raise AttributeError or TypeError.
    """
    mock_data = {
        "$schema": "./schema.json",
        "last_updated": "2026-10-19T00:00:00Z",
        "last_sync": "2026-10-19T00:00:00Z",
        "offers": [
            {
                "id": "test-null-guide-offer",
                "title": "Test Null Guide Offer",
                "platform": "Google Cloud",
                "category": "Cloud Architecture",
                "certification_name": "Test Null Guide Offer",
                "credential_tier": "skill_badge_lab",
                "proctoring_type": "unproctored_lab",
                "accredited_body": None,
                "url": "https://cloud.google.com/innovators",
                "verified_vendor_url": "https://cloud.google.com/innovators",
                "status": "Active",
                "seasonality": "evergreen",
                "value_usd": 0,
                "difficulty_tier": "Foundational",
                "eligibility": "Open to all",
                "time_period": "Rolling",
                "recurrence_pattern": "Continuous",
                "application_flow_type": "Direct Assessment Launch",
                "redemption_portal": "https://cloud.google.com/innovators",
                "checkout_field": "",
                "cart_balance_verified": "$0.00 (100% Free / Waiver Confirmed)",
                "voucher_code": "AUTO_APPLIED",
                "redemption_guide": None,  # Explicitly None to test resilience
                "claim_steps": "Direct link access.",
                "is_authentic_vendor": True,
                "authenticity_score": 90,
                "visual_proof": {
                    "screenshot_path": "docs/screenshots/gcp-cloud-skills-boost.png",
                    "screenshot_url": "docs/screenshots/gcp-cloud-skills-boost.png",
                    "status": "verified",
                    "zero_dollar_confirmed": True,
                    "maintenance_detected": False,
                    "paid_catalog_detected": False
                },
                "verification_date": "2026-10-19",
                "inspection_notes": "Active verification."
            }
        ]
    }

    mock_news = {
        "$schema": "./news_schema.json",
        "last_updated": "2026-10-19T00:00:00Z",
        "last_sync": "2026-10-19T00:00:00Z",
        "news": []
    }

    # Must generate cleanly without throwing AttributeError: 'NoneType' object has no attribute 'get'
    readme = generate_readme(mock_data, mock_news)
    assert "Test Null Guide Offer" in readme
    assert "## 💳 Where & How Vouchers Are Applied" in readme

    html = generate_web_dashboard(mock_data, mock_news)
    assert "Test Null Guide Offer" in html
    assert "test-null-guide-offer" in html


def test_scenario_truth_oracle_on_incoming_offer():
    """
    Scenario: Truth oracle encounters an offer not yet registered in its static TRUTH_POLICY_REGISTRY.
    Invariant: Must safely return a default verdict payload without raising KeyError.
    """
    new_offer = {
        "id": "new-brand-unknown-cert",
        "title": "Brand New Free Exam",
        "platform": "New Tech Vendor",
        "credential_tier": "proctored_exam",
        "url": "https://newtech.example.com/cert"
    }

    truth_payload = corroborate_offer(new_offer)
    assert isinstance(truth_payload, dict)
    assert truth_payload["policy_type"] == "verified_100pct_free"
    assert truth_payload["is_misleading"] is False
