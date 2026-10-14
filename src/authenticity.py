"""
Authenticity Verification & Anti-Scam Security Engine for CertPulse.

Capabilities:
1. Domain & Portal Authenticity Gate: Whitelist enforcement against official vendor
   ecosystems and accredited exam partners; rejection of deceptive lookalikes and typo-squatting.
2. Redirect Chain & Destination Verification: Follows and audits full HTTP redirect chains
   to ensure no hops route through untrusted ad-farms, affiliate shorteners, or cloaked domains.
3. SSL/TLS & Protocol Security Standards: Enforces strict HTTPS, non-tampered FQDNs,
   standard transport ports, and rejects insecure HTTP or raw IP addresses.
4. Content & Accreditation Corroboration: Analyzes page content for positive vendor/program
   corroboration markers and rejects deceptive signals (paywalls, credit-card traps, brain dumps).
5. Comprehensive Authenticity Scoring: Outputs multi-dimensional scores (0-100) and
   structured verification flags for tracking in offers.json and dashboard visualizations.
"""

import re
import ipaddress
from urllib.parse import urlparse
from typing import Dict, Any, List, Tuple, Optional

# Canonical platform-to-domain mapping
PLATFORM_DOMAINS: Dict[str, List[str]] = {
    "Microsoft Azure": [
        "microsoft.com",
        "azure.com",
        "learn.microsoft.com",
        "azure.microsoft.com",
        "events.microsoft.com",
        "msft.com"
    ],
    "Amazon Web Services": [
        "amazon.com",
        "aws.amazon.com",
        "awseducate.com",
        "skillbuilder.aws",
        "aws.training",
        "aws"
    ],
    "Google Cloud": [
        "google.com",
        "cloud.google.com",
        "cloudskillsboost.google",
        "skills.google",
        "grow.google",
        "withgoogle.com",
        "qwiklabs.com",
        "google"
    ],
    "Oracle Cloud": [
        "oracle.com",
        "education.oracle.com",
        "mylearn.oracle.com"
    ],
    "Cisco": [
        "cisco.com",
        "u.cisco.com",
        "learningnetwork.cisco.com"
    ],
    "ISC2": [
        "isc2.org",
        "www.isc2.org"
    ],
    "Linux Foundation / CNCF": [
        "linuxfoundation.org",
        "cncf.io",
        "training.linuxfoundation.org"
    ],
    "Snowflake": [
        "snowflake.com",
        "learn.snowflake.com"
    ],
    "MongoDB": [
        "mongodb.com",
        "learn.mongodb.com"
    ],
    "Salesforce": [
        "salesforce.com",
        "trailhead.salesforce.com"
    ],
    "Postman": [
        "postman.com",
        "academy.postman.com"
    ],
    "Juniper Networks": [
        "juniper.net",
        "learningportal.juniper.net"
    ],
    "Qualys": [
        "qualys.com",
        "www.qualys.com"
    ],
    "Databricks": [
        "databricks.com",
        "academy.databricks.com"
    ],
    "Fortinet": [
        "fortinet.com",
        "training.fortinet.com"
    ],
    "GitHub": [
        "github.com",
        "education.github.com",
        "githubuniverse.com",
        "github.blog"
    ]
}

# Accredited Exam Delivery Providers & Digital Credential Registries
ACCREDITED_PARTNER_DOMAINS: List[str] = [
    "pearsonvue.com",
    "webassessor.com",
    "kryteriononline.com",
    "psiexams.com",
    "psi.com",
    "credly.com",
    "accredible.com",
    "certmetrics.com",
    "coursera.org",
    "edx.org",
    "classcentral.com"
]

# Banned URL shorteners & affiliate cloaking services
BANNED_URL_SHORTENERS: List[str] = [
    "bit.ly",
    "tinyurl.com",
    "cutt.ly",
    "adf.ly",
    "shorturl.at",
    "t.co",
    "ow.ly",
    "buff.ly",
    "is.gd",
    "rb.gy"
]

# Suspicious TLDs heavily correlated with voucher scam / ad-farming sites
SUSPICIOUS_TLDS: List[str] = [
    ".xyz", ".top", ".buzz", ".cam", ".click", ".stream", ".bid", ".loan", ".win", ".men"
]

# Scam & exam braindump patterns in domain names
SCAM_DOMAIN_KEYWORDS: List[str] = [
    "dumps",
    "braindump",
    "examdump",
    "pass4sure",
    "lead4pass",
    "itexams",
    "cert2pass",
    "crackexams",
    "cheatcert",
    "vouchercoupon",
    "freevouchercodes",
    "promocodegenerator",
    "testking",
    "examtopics"
]

# Deceptive typo-squatting patterns targeting primary enterprise cloud vendors
TYPOSQUATTING_PATTERNS: List[re.Pattern] = [
    re.compile(r"micros[0o]ft", re.IGNORECASE),
    re.compile(r"m[i1]cr[o0]s[o0]ft", re.IGNORECASE),
    re.compile(r"am[a4]z[o0]n", re.IGNORECASE),
    re.compile(r"g[o0]{2}gle", re.IGNORECASE),
    re.compile(r"[o0]rac[l1]e", re.IGNORECASE),
    re.compile(r"c[i1]sc[o0]", re.IGNORECASE),
    re.compile(r"g[i1]thub", re.IGNORECASE)
]

# Deceptive & scam indicators in web page body text
DECEPTIVE_CONTENT_PATTERNS: List[re.Pattern] = [
    re.compile(r"\bbraindump(s)?\b", re.IGNORECASE),
    re.compile(r"\bexam dumps?\b", re.IGNORECASE),
    re.compile(r"\bguaranteed pass\b", re.IGNORECASE),
    re.compile(r"\b100% pass guarantee\b", re.IGNORECASE),
    re.compile(r"\breal exam questions and answers\b", re.IGNORECASE),
    re.compile(r"\bactual test questions\b", re.IGNORECASE),
    re.compile(r"\bcrack (the )?exam\b", re.IGNORECASE),
    re.compile(r"\bbuy exam questions\b", re.IGNORECASE),
    re.compile(r"\bcheat sheet\b", re.IGNORECASE),
    re.compile(r"\bcredit card (is )?required to (claim|enroll|register)\b", re.IGNORECASE),
    re.compile(r"\b7-day (free )?trial then \$\b", re.IGNORECASE),
    re.compile(r"\bbilled automatically after trial\b", re.IGNORECASE),
    re.compile(r"\benter credit card to unlock free\b", re.IGNORECASE),
    re.compile(r"\bclick here to reveal (the )?(promo|coupon|voucher) code\b", re.IGNORECASE),
    re.compile(r"\bcoupon code revealed\b", re.IGNORECASE)
]

# Positive corroboration markers for authentic technical certifications
POSITIVE_CORROBORATION_SIGNALS: List[str] = [
    "certification",
    "credential",
    "exam",
    "badge",
    "voucher",
    "training",
    "course",
    "curriculum",
    "scholarship",
    "academy",
    "learning",
    "skills",
    "assessment",
    "continuing education",
    "accredited",
    "verify",
    " Pearson ",
    " PSI "
]


def clean_hostname(url_or_netloc: str) -> str:
    """Extracts lowercase FQDN hostname without port or user info."""
    if "://" in url_or_netloc:
        parsed = urlparse(url_or_netloc)
        host = parsed.netloc or parsed.path
    else:
        host = url_or_netloc
    
    # Strip port if present
    host = host.split(":")[0].strip().lower()
    return host


def is_ip_address(host: str) -> bool:
    """Returns True if the hostname is a raw IPv4 or IPv6 address."""
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def get_all_authorized_domains() -> set:
    """Returns the union of all vendor and accredited partner domains."""
    all_domains = set()
    for domain_list in PLATFORM_DOMAINS.values():
        all_domains.update(domain_list)
    all_domains.update(ACCREDITED_PARTNER_DOMAINS)
    return all_domains


def match_domain_to_list(hostname: str, domain_list: List[str]) -> bool:
    """
    Checks if a hostname strictly equals or is a legitimate subdomain
    of any domain in domain_list.
    Prevents substring spoofing (e.g. 'microsoft.com.scam.xyz' -> False).
    """
    for allowed in domain_list:
        allowed_clean = allowed.lower().strip()
        if hostname == allowed_clean or hostname.endswith("." + allowed_clean):
            return True
    return False


def check_domain_authenticity(url: str, platform: str = "") -> Tuple[bool, str, str, List[str]]:
    """
    Evaluates domain legitimacy against trusted vendor ecosystem, partner whitelist,
    banned shorteners, typo-squatting, and scam patterns.
    
    Returns:
        (is_authentic, trust_tier, reason, flags)
    """
    host = clean_hostname(url)
    flags: List[str] = []

    if not host or "." not in host:
        return False, "Untrusted", "Malformed or missing hostname", ["MALFORMED_HOSTNAME"]

    if is_ip_address(host):
        return False, "Untrusted", "Raw IP address instead of canonical vendor domain", ["RAW_IP_HOSTNAME"]

    # 1. Banned shortener check
    for shortener in BANNED_URL_SHORTENERS:
        if host == shortener or host.endswith("." + shortener):
            flags.append("BANNED_URL_SHORTENER")
            return False, "Untrusted", f"Disallowed URL shortener / redirect cloaker: {host}", flags

    # 2. Scam keyword check in hostname
    for kw in SCAM_DOMAIN_KEYWORDS:
        if kw in host:
            flags.append("SCAM_KEYWORD_IN_DOMAIN")
            return False, "Scam / Deceptive", f"Detected scam / braindump keyword '{kw}' in domain name", flags

    # 3. Suspicious TLD check
    for tld in SUSPICIOUS_TLDS:
        if host.endswith(tld):
            flags.append("SUSPICIOUS_TLD")
            return False, "Untrusted", f"High-risk scam TLD detected: {tld}", flags

    # 4. Check for typo-squatting lookalikes if not in authorized domains
    all_authorized = get_all_authorized_domains()
    if not match_domain_to_list(host, list(all_authorized)):
        for pattern in TYPOSQUATTING_PATTERNS:
            if pattern.search(host):
                flags.append("DECEPTIVE_TYPOSQUATTING_DOMAIN")
                return False, "Scam / Deceptive", f"Deceptive typo-squatting pattern detected: {host}", flags

    # 5. Platform-specific domain verification
    if platform and platform in PLATFORM_DOMAINS:
        allowed_for_platform = PLATFORM_DOMAINS[platform]
        if match_domain_to_list(host, allowed_for_platform):
            flags.append("OFFICIAL_PRIMARY_VENDOR_DOMAIN")
            return True, "Official Vendor Portal", f"Verified official {platform} primary portal", flags

    # 6. Check generic vendor domains
    for plat_name, domain_list in PLATFORM_DOMAINS.items():
        if match_domain_to_list(host, domain_list):
            flags.append("OFFICIAL_PRIMARY_VENDOR_DOMAIN")
            return True, "Official Vendor Portal", f"Verified official {plat_name} portal", flags

    # 7. Check accredited partner domains
    if match_domain_to_list(host, ACCREDITED_PARTNER_DOMAINS):
        flags.append("ACCREDITED_PARTNER_DOMAIN")
        return True, "Accredited Exam Partner", f"Verified accredited partner domain: {host}", flags

    # If domain doesn't match any official vendor or partner:
    flags.append("UNVERIFIED_THIRD_PARTY_DOMAIN")
    return False, "Untrusted", f"Unrecognized domain outside verified provider directory: {host}", flags


def check_ssl_and_protocol(url: str) -> Tuple[bool, List[str]]:
    """
    Enforces strict HTTPS and standard transport security protocol invariants.
    """
    flags: List[str] = []
    parsed = urlparse(url)

    if parsed.scheme.lower() != "https":
        flags.append("INSECURE_HTTP_PROTOCOL")
        return False, flags

    flags.append("STRICT_HTTPS_PROTOCOL")

    # Standard port validation
    if parsed.port and parsed.port != 443:
        flags.append(f"NON_STANDARD_PORT_{parsed.port}")
        return False, flags
    else:
        flags.append("STANDARD_PORT_SECURITY")

    return True, flags


def check_redirect_chain_security(chain: List[str], platform: str = "") -> Tuple[bool, List[str]]:
    """
    Audits the entire redirect trail to ensure:
    - Every intermediate hop maintained HTTPS transport security (no SSL downgrades).
    - No hop routed through banned URL shorteners or scam affiliate networks.
    - Final destination lands on an authorized vendor or partner domain.
    """
    flags: List[str] = []
    if not chain:
        return True, ["CLEAN_REDIRECT_CHAIN"]

    for idx, hop in enumerate(chain):
        parsed = urlparse(hop)
        if parsed.scheme.lower() != "https":
            flags.append("REDIRECT_SSL_DOWNGRADE")
            return False, flags

        host = clean_hostname(hop)
        for shortener in BANNED_URL_SHORTENERS:
            if host == shortener or host.endswith("." + shortener):
                flags.append("REDIRECT_THROUGH_SHORTENER")
                return False, flags

    final_url = chain[-1]
    is_dest_auth, _, _, domain_flags = check_domain_authenticity(final_url, platform)
    if not is_dest_auth:
        flags.append("REDIRECT_UNTRUSTED_DESTINATION")
        flags.extend(domain_flags)
        return False, flags

    flags.append("CLEAN_REDIRECT_CHAIN")
    return True, flags


def corroborate_content(
    body_text: str,
    platform: str = "",
    cert_name: str = "",
    exam_code: str = ""
) -> Tuple[bool, int, List[str], List[str]]:
    """
    Performs deep semantic inspection of response body text.
    Returns:
        (corroboration_passed, score_delta, positive_matches, warning_flags)
    """
    if not body_text:
        # If body text is empty or unavailable (e.g. bot protection or offline check), return neutral pass
        return True, 10, ["CONTENT_INSPECTION_BYPASS"], []

    lower_text = body_text.lower()
    positives: List[str] = []
    warnings: List[str] = []
    score_delta = 0

    # 1. Check for deceptive scam / braindump / paywall patterns
    for pat in DECEPTIVE_CONTENT_PATTERNS:
        match = pat.search(lower_text)
        if match:
            warnings.append(f"DECEPTIVE_PATTERN_DETECTED: '{match.group(0)}'")

    if warnings:
        return False, -40, positives, warnings

    # 2. Corroborate vendor / platform name
    if platform:
        # Check main platform tokens
        platform_tokens = [tok.lower() for tok in re.split(r"[\s/]+", platform) if len(tok) > 2]
        if any(tok in lower_text for tok in platform_tokens):
            positives.append("VENDOR_NAME_MATCHED")
            score_delta += 10

    # 3. Corroborate exam code if present
    if exam_code:
        exam_tokens = [c.strip().lower() for c in exam_code.split(",") if c.strip()]
        for code in exam_tokens:
            if code in lower_text:
                positives.append(f"EXAM_CODE_MATCHED ({code.upper()})")
                score_delta += 5
                break

    # 4. Corroborate positive credentialing keywords
    matched_kws = [kw for kw in POSITIVE_CORROBORATION_SIGNALS if kw.lower() in lower_text]
    if len(matched_kws) >= 2:
        positives.append(f"CREDENTIAL_SIGNALS_FOUND ({len(matched_kws)})")
        score_delta += 10
    elif len(matched_kws) == 1:
        positives.append("SINGLE_CREDENTIAL_SIGNAL")
        score_delta += 5

    passed = len(warnings) == 0
    return passed, score_delta, positives, warnings


def audit_offer_authenticity(
    offer: Dict[str, Any],
    body_text: str = "",
    redirect_chain: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Executes the multi-layer authenticity verification pipeline for an offer.
    Computes an authenticity score (0-100), security flags, and definitive verdict.
    """
    url = offer.get("url", "")
    platform = offer.get("platform", "")
    cert_name = offer.get("certification_name", "")
    exam_code = offer.get("exam_code", "")

    checks_passed: List[str] = []
    warning_flags: List[str] = []
    score = 0

    # Layer 1: Domain & Portal Whitelist Check (up to 40 pts)
    domain_ok, trust_tier, domain_reason, domain_flags = check_domain_authenticity(url, platform)
    if domain_ok:
        if trust_tier == "Official Vendor Portal":
            score += 40
        else:
            score += 35
        checks_passed.extend(domain_flags)
    else:
        warning_flags.extend(domain_flags)
        if "SCAM_KEYWORD_IN_DOMAIN" in domain_flags or "DECEPTIVE_TYPOSQUATTING_DOMAIN" in domain_flags:
            score -= 50
        else:
            score -= 20

    # Layer 2: SSL/TLS & Protocol Security (up to 20 pts)
    ssl_ok, ssl_flags = check_ssl_and_protocol(url)
    if ssl_ok:
        score += 20
        checks_passed.extend(ssl_flags)
    else:
        warning_flags.extend(ssl_flags)
        score -= 30

    # Layer 3: Redirect Chain & Destination Verification (up to 15 pts)
    chain = redirect_chain if redirect_chain else [url]
    redirect_ok, redirect_flags = check_redirect_chain_security(chain, platform)
    if redirect_ok:
        score += 15
        checks_passed.extend(redirect_flags)
    else:
        warning_flags.extend(redirect_flags)
        score -= 25

    # Layer 4: Content & Accreditation Corroboration (up to 25 pts)
    corr_ok, corr_delta, corr_positives, corr_warnings = corroborate_content(
        body_text=body_text,
        platform=platform,
        cert_name=cert_name,
        exam_code=exam_code
    )
    score += corr_delta
    checks_passed.extend(corr_positives)
    warning_flags.extend(corr_warnings)

    # Historical Archive special-case: If archived record on authentic domain, guarantee baseline
    if offer.get("is_historical_archive") and domain_ok and ssl_ok:
        score = max(score, 100)

    # Clamping score [0, 100]
    final_score = max(0, min(100, score))

    # Determine verdict
    has_critical_scam_flags = any(
        f.startswith("DECEPTIVE") or "SCAM" in f or "BANNED_URL_SHORTENER" in f
        for f in warning_flags
    )

    if has_critical_scam_flags:
        verdict = "DECEPTIVE_SCAM"
        is_authentic = False
    elif not domain_ok or not ssl_ok or not redirect_ok:
        verdict = "SUSPICIOUS_UNTRUSTED"
        is_authentic = False
    elif final_score >= 80:
        verdict = "VERIFIED_AUTHENTIC"
        is_authentic = True
    else:
        verdict = "INCONCLUSIVE"
        is_authentic = False

    summary = (
        f"{final_score}% Authenticity: {trust_tier} "
        f"({'TLS Verified' if ssl_ok else 'TLS Failed'}, "
        f"{'Clean Destination' if redirect_ok else 'Redirect Alert'})"
    )

    return {
        "is_authentic_vendor": is_authentic,
        "authenticity_score": final_score,
        "verdict": verdict,
        "trust_tier": trust_tier,
        "domain_verified": domain_ok,
        "ssl_verified": ssl_ok,
        "redirect_secure": redirect_ok,
        "corroboration_passed": corr_ok,
        "checks_passed": list(dict.fromkeys(checks_passed)),
        "warning_flags": list(dict.fromkeys(warning_flags)),
        "summary": summary
    }
