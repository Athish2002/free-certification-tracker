"""
CertPulse Semantic Accessibility Tree & Actionable Element Scanner.
Evaluates page intent by analyzing interactive elements, ARIA roles, and accessible names
to distinguish genuine educational fulfillment portals from corporate sales lead funnels.
"""

from __future__ import annotations

import re
from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field, ConfigDict


ActionabilityVerdict = Literal[
    "ACTIONABLE_FULFILLMENT_PORTAL",
    "MARKETING_LEAD_FUNNEL",
    "NEUTRAL_INFORMATIONAL"
]


class ActionabilityReport(BaseModel):
    """
    Structured outcome of semantic accessibility and interactive element analysis.
    """
    model_config = ConfigDict(extra="ignore")

    fulfillment_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Confidence score that the page contains actionable enrollment, exam scheduling, or voucher claim triggers."
    )
    marketing_fluff_score: int = Field(
        ...,
        ge=0,
        le=100,
        description="Intensity score of corporate sales lead capture, marketing forms, and whitepaper downloads."
    )
    detected_ctas: List[str] = Field(
        default_factory=list,
        description="Actionable Call-To-Action buttons and links identified on the page."
    )
    detected_traps: List[str] = Field(
        default_factory=list,
        description="Marketing and sales lead trap phrases identified on the page."
    )
    is_actionable: bool = Field(
        default=False,
        description="True if fulfillment elements dominate marketing fluff."
    )
    verdict: ActionabilityVerdict = Field(
        default="NEUTRAL_INFORMATIONAL",
        description="Categorical intent verdict: ACTIONABLE_FULFILLMENT_PORTAL | MARKETING_LEAD_FUNNEL | NEUTRAL_INFORMATIONAL"
    )
    reason: str = Field(
        default="",
        description="Summary explanation of the actionability determination."
    )


# Curated lists of semantic triggers
FULFILLMENT_TRIGGERS = [
    "enroll",
    "enroll in path",
    "enroll for free",
    "start course",
    "start learning",
    "schedule exam",
    "schedule free exam",
    "book exam",
    "take assessment",
    "start assessment",
    "claim voucher",
    "apply voucher",
    "register for exam",
    "start lab",
    "launch lab",
    "take exam",
    "begin course",
    "view learning path",
    "sign in to enroll",
    "join challenge",
    "start challenge"
]

MARKETING_TRAPS = [
    "speak to an ai expert",
    "speak to an expert",
    "talk to an expert",
    "speak to our experts",
    "speak to sales",
    "talk to sales",
    "contact sales",
    "connect with sales",
    "contact an expert",
    "request a demo",
    "request demo",
    "schedule a demo",
    "download whitepaper",
    "download datasheet",
    "idc marketscape",
    "gartner magic quadrant",
    "forrester wave",
    "contact us for enterprise pricing",
    "book a sales meeting"
]


def scan_accessibility_elements(
    interactive_elements: List[str],
    page_text: str = "",
    page_title: str = ""
) -> ActionabilityReport:
    """
    Analyzes interactive element labels, page text, and document title to determine
    whether a page offers concrete actionable fulfillment or is an informational sales funnel.
    """
    combined = f"{page_title.lower()} {page_text.lower()}"
    found_ctas: List[str] = []
    found_traps: List[str] = []

    # 1. Scan interactive elements (buttons, links, accessible names)
    for el in interactive_elements:
        clean_el = el.lower().strip()
        for trig in FULFILLMENT_TRIGGERS:
            if trig in clean_el and trig not in found_ctas:
                found_ctas.append(trig)
        for trap in MARKETING_TRAPS:
            if trap in clean_el and trap not in found_traps:
                found_traps.append(trap)

    # 2. Corroborate with page body copy
    for trig in FULFILLMENT_TRIGGERS:
        if trig in combined and trig not in found_ctas:
            found_ctas.append(trig)

    for trap in MARKETING_TRAPS:
        if trap in combined and trap not in found_traps:
            found_traps.append(trap)

    # 3. Compute scores
    fulfillment_score = min(100, len(found_ctas) * 30)
    fluff_score = min(100, len(found_traps) * 35)

    if found_ctas and fulfillment_score >= fluff_score:
        verdict = "ACTIONABLE_FULFILLMENT_PORTAL"
        is_actionable = True
        reason = f"Actionable fulfillment confirmed: found {len(found_ctas)} educational/exam CTAs ({', '.join(found_ctas[:3])})."
    elif found_traps and fluff_score > fulfillment_score:
        verdict = "MARKETING_LEAD_FUNNEL"
        is_actionable = False
        reason = f"Marketing funnel detected: found {len(found_traps)} sales-pitch/lead triggers ({', '.join(found_traps[:3])}) without actionable course CTAs."
    else:
        verdict = "NEUTRAL_INFORMATIONAL"
        is_actionable = len(found_ctas) > 0
        reason = "Neutral informational landing page."

    return ActionabilityReport(
        fulfillment_score=fulfillment_score,
        marketing_fluff_score=fluff_score,
        detected_ctas=found_ctas,
        detected_traps=found_traps,
        is_actionable=is_actionable,
        verdict=verdict,
        reason=reason
    )
