"""
Adaptive Verification Engine: Universal Multi-Platform Proof & Anti-Gatekeeper Resolution.

Governing Invariant:
Verification resilience across enterprise cloud & technology certification platforms
cannot rely on brittle, ad-hoc single-site hacks. This engine classifies platforms into
4 canonical gatekeeper archetypes, resolves dual-phase targets (Deep Claim URL vs Authority Root),
audits redirect degradation (catching silent 302 bounces to generic marketing hubs), pre-injects
cookie consent storage presets (< 50ms), and computes continuous Proof Quality Scores (PQS 0-100).
"""

from __future__ import annotations

import re
import ipaddress
import logging
from enum import Enum
from dataclasses import dataclass, field
from urllib.parse import urlparse
from typing import Dict, Any, List, Tuple, Optional

logger = logging.getLogger("certpulse.adaptive_verifier")


class PlatformCluster(str, Enum):
    """The 4 canonical enterprise platform verification clusters."""
    CLUSTER_A_LMS = "Cluster A: Enterprise LMS Portal"
    CLUSTER_B_SCHOLARSHIP = "Cluster B: Time-Bounded Scholarship"
    CLUSTER_C_CE_COMMUNITY = "Cluster C: CE Recertification Community"
    CLUSTER_D_EVENT_WAVE = "Cluster D: Event-Tied Fast Wave"


@dataclass(frozen=True)
class ClusterProfile:
    """Operational verification profile tailored to a platform cluster."""
    cluster: PlatformCluster
    code: str
    name: str
    primary_gatekeeper: str
    wait_condition: str
    target_selectors: List[str]
    assertion_focus: str


@dataclass(frozen=True)
class DualPhaseTargets:
    """Resolved verification URLs separating deep curriculum proof from authority root."""
    deep_claim_url: str
    authority_root_url: str
    primary_nav_target: str
    is_divergent: bool
    divergence_reason: str


@dataclass(frozen=True)
class PQSResult:
    """Proof Quality Scoring (PQS 0-100) confidence assessment."""
    score: float
    tier: str  # HIGH_CONFIDENCE_VERIFIED, MODERATE_CONFIDENCE_SSO_GATE, LOW_CONFIDENCE_REVIEW_NEEDED
    url_score: float
    dom_score: float
    visual_score: float
    corroboration_score: float
    summary: str


@dataclass(frozen=True)
class SecurityValidationResult:
    """SSRF and URI safety verification result."""
    is_safe: bool
    reason: str
    normalized_url: str


# Private IP network ranges to reject for SSRF defense
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),      # Loopback
    ipaddress.ip_network("10.0.0.0/8"),       # RFC 1918 Private
    ipaddress.ip_network("172.16.0.0/12"),    # RFC 1918 Private
    ipaddress.ip_network("192.168.0.0/16"),   # RFC 1918 Private
    ipaddress.ip_network("169.254.0.0/16"),   # Link-Local / AWS Metadata
    ipaddress.ip_network("::1/128"),          # IPv6 Loopback
    ipaddress.ip_network("fc00::/7"),         # IPv6 Unique Local
    ipaddress.ip_network("fe80::/10"),        # IPv6 Link-Local
]

# Blacklisted generic catalog root paths that indicate a downgraded redirect
GENERIC_CATALOG_HUBS = {
    "mylearn.oracle.com/ou",
    "mylearn.oracle.com/ou/",
    "education.oracle.com",
    "education.oracle.com/",
    "learn.microsoft.com",
    "learn.microsoft.com/",
    "learn.microsoft.com/en-us",
    "learn.microsoft.com/en-us/",
    "explore.skillbuilder.aws",
    "explore.skillbuilder.aws/",
    "netacad.com",
    "netacad.com/",
    "www.netacad.com",
    "www.netacad.com/",
}


def validate_target_url(url: str, allow_local_file: bool = True) -> SecurityValidationResult:
    """
    Validates target URL against SSRF, dangerous URI schemes, and internal network ranges.
    Returns: SecurityValidationResult
    """
    if not url or not isinstance(url, str):
        return SecurityValidationResult(is_safe=False, reason="Empty or non-string URL", normalized_url="")

    url_clean = url.strip()
    parsed = urlparse(url_clean)

    # Allow local file fixtures for test suites
    if parsed.scheme == "file":
        if allow_local_file:
            return SecurityValidationResult(is_safe=True, reason="Local file fixture permitted", normalized_url=url_clean)
        return SecurityValidationResult(is_safe=False, reason="File scheme disallowed in live environment", normalized_url=url_clean)

    if parsed.scheme not in ("http", "https"):
        return SecurityValidationResult(is_safe=False, reason=f"Unsupported or dangerous scheme: {parsed.scheme}", normalized_url=url_clean)

    hostname = parsed.hostname
    if not hostname:
        return SecurityValidationResult(is_safe=False, reason="Missing hostname in URL", normalized_url=url_clean)

    # Check for localhost / loopback aliases
    if hostname.lower() in ("localhost", "127.0.0.1", "::1", "metadata.google.internal", "169.254.169.254"):
        return SecurityValidationResult(is_safe=False, reason=f"Access to internal host '{hostname}' is blocked (SSRF defense)", normalized_url=url_clean)

    # Try resolving if hostname is raw IP
    try:
        ip = ipaddress.ip_address(hostname)
        for net in _BLOCKED_NETWORKS:
            if ip in net:
                return SecurityValidationResult(is_safe=False, reason=f"Access to private IP range {net} is blocked", normalized_url=url_clean)
    except ValueError:
        pass  # Hostname is a standard domain name, proceed

    return SecurityValidationResult(is_safe=True, reason="URL passed security invariants", normalized_url=url_clean)


def classify_platform_cluster(platform: str, url: str) -> ClusterProfile:
    """
    Maps an offer's platform and URL into one of the 4 canonical verification clusters.
    """
    url_lower = url.lower()
    parsed = urlparse(url_lower)
    domain = parsed.netloc
    path = parsed.path

    # Cluster B: Scholarships & Annual Cohorts
    if any(k in path for k in ["scholarship", "pack", "1mcc", "lift"]) or "cncf.io" in domain or "isc2.org/landing/1mcc" in url_lower:
        return ClusterProfile(
            cluster=PlatformCluster.CLUSTER_B_SCHOLARSHIP,
            code="SCHOLARSHIP",
            name="Annual Time-Bounded Scholarship",
            primary_gatekeeper="Cohort / Capacity Closure Wall",
            wait_condition="domcontentloaded",
            target_selectors=[".application-form", ".scholarship-header", "button:has-text('Apply')"],
            assertion_focus="Scan for 'capacity reached', 'cohort full', or application date windows"
        )

    # Cluster C: Continuous Education (CE) Communities
    if any(k in path for k in ["rev-up", "recert", "community"]) or "learningnetwork.cisco.com" in domain:
        return ClusterProfile(
            cluster=PlatformCluster.CLUSTER_C_CE_COMMUNITY,
            code="RECERT_COMMUNITY",
            name="CE Recertification Community",
            primary_gatekeeper="Community Forum Thread Expiration",
            wait_condition="networkidle",
            target_selectors=[".cforum-topic", ".feed-item", ".discussion-thread"],
            assertion_focus="Scan for active 30-day challenge thread & CE credit eligibility"
        )

    # Cluster D: Event-Tied Fast Challenges (Historical Archive)
    if any(k in domain for k in ["githubuniverse", "conf", "summit"]) or any(k in path for k in ["challenges", "summit"]):
        return ClusterProfile(
            cluster=PlatformCluster.CLUSTER_D_EVENT_WAVE,
            code="EVENT_WAVE",
            name="Event-Tied Fast Challenge",
            primary_gatekeeper="Promotional Expiration 302 Silent Bounce",
            wait_condition="domcontentloaded",
            target_selectors=[".challenge-card", ".event-hero", ".leaderboard"],
            assertion_focus="Audit redirect chain against root conference hub downgrade"
        )

    # Cluster A: Enterprise LMS Portals (Default)
    return ClusterProfile(
        cluster=PlatformCluster.CLUSTER_A_LMS,
        code="ENTERPRISE_LMS",
        name="Enterprise LMS Portal",
        primary_gatekeeper="SPA Hydration Lag + OneTrust / TrustArc Cookie Shield",
        wait_condition="networkidle",
        target_selectors=[".learning-path-header", ".course-title", "button:has-text('Enroll')", ".price-badge"],
        assertion_focus="Inject storage preset, await semantic route hydration, check $0.00 waiver"
    )


def resolve_dual_phase_targets(offer: Dict[str, Any]) -> DualPhaseTargets:
    """
    Resolves verification targets:
    - Primary Nav Target: Prioritizes deep claim URL (e.g. mylearn.oracle.com/.../127177)
      for visual DOM proof, syllabus capture, and $0.00 waiver confirmation.
    - Authority Target: Preserves corporate marketing root (e.g. oracle.com/education/)
      for domain authenticity, SSL validation, and anti-scam gating.
    Fixes the bug where deep URLs were overridden by generic marketing roots.
    """
    deep_claim_url = offer.get("url", "").strip()
    direct_verified_url = offer.get("direct_verified_url", "").strip()
    verified_vendor_url = offer.get("verified_vendor_url", "").strip()

    # Determine authority root
    authority_root_url = verified_vendor_url or direct_verified_url or deep_claim_url

    # Check for divergence (landing page trap)
    is_divergent = False
    divergence_reason = "Aligned"

    if direct_verified_url and direct_verified_url != deep_claim_url:
        is_divergent = True
        divergence_reason = f"Divergence detected: direct_verified_url ({direct_verified_url}) differs from deep claim ({deep_claim_url})"

    # Prioritize deep claim URL for browser navigation so proof captures the actual syllabus
    primary_nav_target = deep_claim_url or direct_verified_url or verified_vendor_url

    return DualPhaseTargets(
        deep_claim_url=deep_claim_url,
        authority_root_url=authority_root_url,
        primary_nav_target=primary_nav_target,
        is_divergent=is_divergent,
        divergence_reason=divergence_reason
    )


def get_pre_navigation_storage(url: str) -> Dict[str, Any]:
    """
    Returns pre-baked localStorage and cookie presets to dismiss OneTrust, TrustArc,
    and Cookiebot consent banners before initial DOM render (< 50ms).
    """
    parsed = urlparse(url.lower())
    domain = parsed.netloc

    local_storage: Dict[str, str] = {
        "OptanonAlertBoxClosed": "2026-01-01T00:00:00.000Z",
        "cookie_consent": "true",
        "cookie_banner_dismissed": "true",
        "eu_cookie": "accepted",
    }

    if "oracle" in domain:
        local_storage["oracle_cookie_consent"] = "true"
        local_storage["trustarc_notice"] = "accepted"
    elif "microsoft" in domain:
        local_storage["MS_COOKIE_CONSENT"] = "accepted"
        local_storage["ms_learn_locale"] = "en-us"
    elif "amazon" in domain or "aws" in domain:
        local_storage["aws-cookie-consent"] = "accepted"

    return {
        "local_storage": local_storage,
        "locale": "en-US",
        "timezone_id": "America/New_York",
    }


def audit_redirect_degradation(initial_url: str, final_url: str, expected_slug: str = "") -> Tuple[bool, str, float]:
    """
    Audits whether a redirect chain preserved the deep syllabus slug or degraded
    into a generic marketing hub (catching silent 302 campaign expirations).
    Returns: (is_degraded, reason, url_score)
    """
    if not initial_url or not final_url:
        return False, "Empty URL provided", 50.0

    if initial_url == final_url:
        return False, "Direct connection (No redirect)", 100.0

    parsed_init = urlparse(initial_url)
    parsed_final = urlparse(final_url)

    # Normalize domain and path
    final_hub = f"{parsed_final.netloc}{parsed_final.path}".rstrip("/")

    # Check if final URL collapsed to a known generic catalog hub
    for blacklisted in GENERIC_CATALOG_HUBS:
        clean_bl = blacklisted.rstrip("/")
        if final_hub == clean_bl or final_hub.endswith(clean_bl):
            return True, f"Degraded to generic catalog hub: {final_url}", 0.0

    # Path depth check: if initial path had depth >= 3 and final path collapsed to <= 1
    init_depth = len([p for p in parsed_init.path.split("/") if p])
    final_depth = len([p for p in parsed_final.path.split("/") if p])

    if init_depth >= 3 and final_depth <= 1:
        return True, f"Path slug stripped: {parsed_init.path} -> {parsed_final.path}", 10.0

    # Domain shift check: if redirected to completely different vendor domain
    if parsed_init.netloc != parsed_final.netloc:
        # Check if it was an expected SSO redirect (e.g. to login.oracle.com)
        if "login" in parsed_final.netloc or "auth" in parsed_final.netloc or "sso" in parsed_final.netloc:
            return False, f"Redirected to SSO authentication gate ({parsed_final.netloc})", 75.0
        return False, f"Redirected across trusted subdomain ({parsed_init.netloc} -> {parsed_final.netloc})", 85.0

    return False, "Healthy deep-link redirect", 100.0


def calculate_proof_quality_score(
    url_score: float,
    dom_score: float,
    visual_score: float,
    corroboration_score: float
) -> PQSResult:
    """
    Calculates the continuous Proof Quality Score (PQS 0-100) using the standard weights:
    PQS = 0.30 * S_url + 0.30 * S_dom + 0.20 * S_visual + 0.20 * S_corroboration
    """
    pqs = (0.30 * url_score) + (0.30 * dom_score) + (0.20 * visual_score) + (0.20 * corroboration_score)
    pqs = max(0.0, min(100.0, round(pqs, 1)))

    if pqs >= 85.0:
        tier = "HIGH_CONFIDENCE_VERIFIED"
        summary = "High confidence proof: deep-link syllabus and $0.00 waiver verified."
    elif pqs >= 60.0:
        tier = "MODERATE_CONFIDENCE_SSO_GATE"
        summary = "Moderate confidence: free curriculum confirmed; unauthenticated SSO required for final booking."
    else:
        tier = "LOW_CONFIDENCE_REVIEW_NEEDED"
        summary = "Low confidence: possible campaign expiration or degraded redirect detected."

    return PQSResult(
        score=pqs,
        tier=tier,
        url_score=url_score,
        dom_score=dom_score,
        visual_score=visual_score,
        corroboration_score=corroboration_score,
        summary=summary
    )
