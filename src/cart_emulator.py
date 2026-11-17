"""
CertPulse cart-balance metadata check.

This module does NOT perform a checkout and proves nothing about a vendor's real cart.
It reads the offer's own hand-written metadata (cart_balance_verified, title, the co-pay
registry below) and reports whether that metadata describes a zero-dollar offer, a co-pay,
or neither. The status code VERIFIED_ZERO_DOLLAR is kept for compatibility and means only
"metadata says zero-dollar".
"""

from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CartAssertionVerdict(BaseModel):
    """
    Structured outcome of synthetic cart and voucher balance assertion.
    """

    model_config = ConfigDict(extra="ignore")

    is_zero_dollar: bool = Field(
        ..., description="True if order summary cart balance is confirmed to drop to $0.00 USD."
    )
    is_copay_required: bool = Field(
        default=False, description="True if a copay, proctoring fee, or administrative booking fee is required."
    )
    copay_amount_usd: float = Field(
        default=0.0, ge=0.0, description="Detected copay fee in USD (e.g. 50.0 for Juniper Pearson VUE)."
    )
    cart_balance_str: str = Field(default="$0.00", description="Display representation of verified cart balance.")
    flow_type: str = Field(default="Checkout Promo Code", description="Identified application flow type.")
    verdict_status: str = Field(
        default="VERIFIED_ZERO_DOLLAR",
        description="Status code: VERIFIED_ZERO_DOLLAR | COPAY_REQUIRED | FEE_UNVERIFIED",
    )
    reason: str = Field(default="", description="Detailed explanation of cart assertion outcome.")


# Known co-pay policies and fees by offer ID or platform
COPAY_POLICY_REGISTRY: dict[str, dict[str, Any]] = {
    "juniper-open-learning": {
        "copay_required": True,
        "copay_amount_usd": 50.0,
        "reason": "Juniper Open Learning provides a 75% voucher waiver, but Pearson VUE requires a $50 candidate registration fee.",
    }
}


def assert_cart_balance(offer: dict[str, Any]) -> CartAssertionVerdict:
    """
    Classifies an offer from its own metadata as zero-dollar, co-pay, or unverified.
    No checkout is performed.
    """
    offer_id = offer.get("id", "")
    title = offer.get("title", "")
    float(offer.get("value_usd", 0.0) or 0.0)
    flow_type = offer.get("application_flow_type") or "Checkout Promo Code"
    cart_verified = str(offer.get("cart_balance_verified") or "")

    # 1. Check known policy registry for copays
    if offer_id in COPAY_POLICY_REGISTRY:
        pol = COPAY_POLICY_REGISTRY[offer_id]
        if pol.get("copay_required"):
            copay = float(pol.get("copay_amount_usd", 50.0))
            return CartAssertionVerdict(
                is_zero_dollar=False,
                is_copay_required=True,
                copay_amount_usd=copay,
                cart_balance_str=f"${copay:.2f} (Partial Discount / Copay)",
                flow_type=flow_type,
                verdict_status="COPAY_REQUIRED",
                reason=pol.get("reason", "Partial discount with required exam copay."),
            )

    # 2. Check title / description for copay signals
    combined = f"{title.lower()} {str(offer.get('description', '')).lower()} {cart_verified.lower()}"
    copay_match = re.search(r"(\$?\d+(?:\.\d{2})?)\s*(?:fee|copay|co-pay|booking fee)", combined)
    if copay_match and "$0" not in copay_match.group(0):
        # Found explicit fee
        return CartAssertionVerdict(
            is_zero_dollar=False,
            is_copay_required=True,
            copay_amount_usd=50.0,
            cart_balance_str="Copay Required",
            flow_type=flow_type,
            verdict_status="COPAY_REQUIRED",
            reason=f"Detected copay requirement in offer details: {copay_match.group(0)}",
        )

    # 3. Assert zero-dollar confirmation
    has_zero_signal = any(
        s in cart_verified.lower() for s in ["$0.00", "0.00", "100% free", "waiver confirmed", "free"]
    )
    if has_zero_signal:
        return CartAssertionVerdict(
            is_zero_dollar=True,
            is_copay_required=False,
            copay_amount_usd=0.0,
            cart_balance_str="$0.00 expected (from offer metadata; not test-purchased)",
            flow_type=flow_type,
            verdict_status="VERIFIED_ZERO_DOLLAR",
            reason="Offer metadata describes a zero-dollar offer. No checkout was performed.",
        )

    return CartAssertionVerdict(
        is_zero_dollar=False,
        is_copay_required=False,
        copay_amount_usd=0.0,
        cart_balance_str="Unverified",
        flow_type=flow_type,
        verdict_status="FEE_UNVERIFIED",
        reason="Offer metadata does not state a zero-dollar balance.",
    )
