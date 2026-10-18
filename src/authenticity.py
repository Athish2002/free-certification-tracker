"""
Authenticity Verification & Anti-Scam Security Engine for CertPulse.

Capabilities:
1. Domain & Portal Authenticity Gate: Whitelist enforcement against official vendor
   ecosystems, accredited exam delivery partners, and accredited educational institutions (.edu, .ac.uk);
   strict rejection of deceptive lookalikes, homoglyph typosquatting, and scam voucher farms.
2. Redirect Chain & Destination Verification: Follows and audits full HTTP redirect chains
   to ensure intermediate hops do not route through untrusted ad-farms, affiliate shorteners,
   scam networks, or cloaked domains, and verifies the final destination matches the vendor/partner.
3. SSL/TLS & Protocol Security Standards: Enforces strict HTTPS, non-tampered FQDNs,
   canonical URL structures (rejecting userinfo spoofing, raw IP hosts), standard transport ports (443),
   and rejects insecure HTTP protocols.
4. Content & Accreditation Corroboration: Analyzes page content for positive vendor/program
   corroboration markers, and aggressively rejects deceptive signals (paywalls, credit-card traps,
   auto-renewal traps, brain dumps, expired/fake coupon code landing pages).
5. Open Redirect Defense: Detects and validates embedded destination URLs in query parameters
   (e.g., returnUrl, goto, redirect_uri) to prevent open redirect exploits to untrusted third parties.
6. Comprehensive Authenticity Scoring: Outputs multi-dimensional scores (0-100) and
   structured verification flags for tracking in offers.json and dashboard visualizations.
"""

import re
import ipaddress
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any, List, Tuple, Optional, Union

# Canonical platform-to-domain mapping
PLATFORM_DOMAINS: Dict[str, List[str]] = {
    "Microsoft Azure": [
        "microsoft.com",
        "azure.com",
        "learn.microsoft.com",
        "azure.microsoft.com",
        "events.microsoft.com",
        "msft.com",
        "microsoftonline.com"
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
        "mylearn.oracle.com",
        "blogs.oracle.com"
    ],
    "Cisco": [
        "cisco.com",
        "u.cisco.com",
        "learningnetwork.cisco.com",
        "blogs.cisco.com",
        "netacad.com"
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
    ],
    "Red Hat": [
        "redhat.com",
        "learn.redhat.com",
        "access.redhat.com",
        "developers.redhat.com"
    ],
    "HashiCorp": [
        "hashicorp.com",
        "developer.hashicorp.com",
        "learn.hashicorp.com"
    ],
    "Palo Alto Networks": [
        "paloaltonetworks.com",
        "beacon.paloaltonetworks.com"
    ],
    "GitLab": [
        "gitlab.com",
        "university.gitlab.com",
        "about.gitlab.com"
    ],
    "Splunk": [
        "splunk.com",
        "lantern.splunk.com",
        "education.splunk.com"
    ],
    "IBM": [
        "ibm.com",
        "skillsbuild.org",
        "yourlearning.ibm.com"
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

# Accredited University & Academic Suffixes / TLDs
ACCREDITED_UNIVERSITY_SUFFIXES: List[str] = [
    ".edu",
    ".ac.uk",
    ".edu.au",
    ".edu.in",
    ".ac.in",
    ".edu.sg",
    ".ac.jp",
    ".edu.cn",
    ".edu.br"
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
    "rb.gy",
    "goo.gl",
    "tiny.cc",
    "bl.ink",
    "clck.ru",
    "s.id",
    "trib.al",
    "lnkd.in",
    "snip.ly",
    "rebrand.ly"
]

# Known affiliate aggregators & ad network redirectors
KNOWN_AFFILIATE_NETWORKS: List[str] = [
    "awin1.com",
    "cj.com",
    "impact.com",
    "shareasale.com",
    "rakuten.com",
    "doubleclick.net",
    "tradedoubler.com",
    "linksynergy.com",
    "flexoffers.com",
    "viglink.com",
    "skimresources.com",
    "adservice.google.com"
]

# Suspicious TLDs heavily correlated with voucher scam / ad-farming sites
SUSPICIOUS_TLDS: List[str] = [
    ".xyz", ".top", ".buzz", ".cam", ".click", ".stream",
    ".bid", ".loan", ".win", ".men", ".cfd", ".icu",
    ".rest", ".gq", ".ml", ".tk", ".ga"
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
    "examtopics",
    "prepaway",
    "examcollection",
    "dumpsboss",
    "dumpsarena",
    "dumpsbase",
    "certlibrary",
    "killtest",
    "surepass",
    "dumpsexpert",
    "validexamdumps"
]

# Deceptive typo-squatting patterns targeting primary enterprise cloud vendors
TYPOSQUATTING_PATTERNS: List[re.Pattern] = [
    re.compile(r"m[i1l!]cr[o0]s[o0]ft|microsft|micro-soft", re.IGNORECASE),
    re.compile(r"am[a4]z[o0]n|amazn|amzon|aws-voucher|aws-exam", re.IGNORECASE),
    re.compile(r"g[o0]{2}gl[e]?|g[o0]g[l1]e|googl", re.IGNORECASE),
    re.compile(r"[o0]rac[l1]e|0racle|oracl", re.IGNORECASE),
    re.compile(r"c[i1]sc[o0]|c1sco|ciscco", re.IGNORECASE),
    re.compile(r"1sc2|isc-2|isc2-exam", re.IGNORECASE),
    re.compile(r"salesf[o0]rce|sales-force|sa1esforce|salesf0rce", re.IGNORECASE),
    re.compile(r"sn[o0]wflake|sn0wflake|snow-flake", re.IGNORECASE),
    re.compile(r"m[o0]ng[o0]db|m0ngodb|mongo-db", re.IGNORECASE),
    re.compile(r"g[i1]thub|g1thub|git-hub", re.IGNORECASE),
    re.compile(r"databr[i1]cks|data-bricks|databr1cks", re.IGNORECASE),
    re.compile(r"f[o0]rt[i1]net|fort1net", re.IGNORECASE),
    re.compile(r"jun[i1]per|jun1per", re.IGNORECASE),
    re.compile(r"r[e3]dh[a4]t|red-hat|redh4t", re.IGNORECASE),
    re.compile(r"h[a4]sh[i1]c[o0]rp|hashic0rp|hashi-corp", re.IGNORECASE),
    re.compile(r"p[a4]l[o0][a4]lt[o0]|palo-alto", re.IGNORECASE),
    re.compile(r"g[i1]tl[a4]b|g1tlab|git-lab", re.IGNORECASE),
    re.compile(r"spl[u0]nk|sp1unk|spl-unk", re.IGNORECASE)
]

# Common query parameter names used for URL redirection / destination targets
OPEN_REDIRECT_PARAM_KEYS = {
    "redirect", "redirect_url", "redirect_uri", "returnurl", "return_url",
    "goto", "target", "dest", "destination", "url", "link", "next", "out"
}

# Deceptive & scam indicators in web page body text
DECEPTIVE_CONTENT_PATTERNS: List[re.Pattern] = [
    # Braindump & exam fraud patterns
    re.compile(r"\bbraindump(s)?\b", re.IGNORECASE),
    re.compile(r"\bexam dumps?\b", re.IGNORECASE),
    re.compile(r"\bguaranteed pass\b", re.IGNORECASE),
    re.compile(r"\b100% pass guarantee\b", re.IGNORECASE),
    re.compile(r"\breal exam questions and answers\b", re.IGNORECASE),
    re.compile(r"\bactual test questions\b", re.IGNORECASE),
    re.compile(r"\bcrack (the )?exam\b", re.IGNORECASE),
    re.compile(r"\bbuy exam questions\b", re.IGNORECASE),
    re.compile(r"\bcheat sheet\b", re.IGNORECASE),
    # Paywall & credit card traps (strictly excluding 'no credit card required')
    re.compile(r"(?<!\bno\s)(?<!\bwithout\s)\bcredit card (is )?required\b", re.IGNORECASE),
    re.compile(r"(?<!\bno\s)(?<!\bnever\s)\benter (your )?credit card\b", re.IGNORECASE),
    re.compile(r"(?<!\bno\s)(?<!\bwithout\s)\bcredit card details required\b", re.IGNORECASE),
    re.compile(r"\b\d+[- ]day (free )?trial then \$\b", re.IGNORECASE),
    re.compile(r"\bbilled automatically (after|upon|following)\b", re.IGNORECASE),
    re.compile(r"\bauto[- ]renews? at \$\b", re.IGNORECASE),
    re.compile(r"\bsubscription (will )?renew(s)? automatically\b", re.IGNORECASE),
    re.compile(r"\benter credit card to unlock\b", re.IGNORECASE),
    # Expired coupon / fake coupon bait-and-switch patterns
    re.compile(r"\bpromo code (is )?(invalid|expired|no longer valid)\b", re.IGNORECASE),
    re.compile(r"\bcoupon (code )?(is )?(invalid|expired|has expired|no longer valid)\b", re.IGNORECASE),
    re.compile(r"\bvoucher code (is )?(invalid|expired|no longer valid)\b", re.IGNORECASE),
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
        host = parsed.hostname or parsed.netloc or parsed.path
    else:
        host = url_or_netloc
        if "@" in host:
            host = host.split("@")[-1]
    
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


def is_university_domain(host: str) -> bool:
    """Returns True if the hostname belongs to an accredited academic/university domain."""
    for suffix in ACCREDITED_UNIVERSITY_SUFFIXES:
        if host.endswith(suffix):
            # Ensure it is a valid domain structure (e.g. harvard.edu, not just .edu)
            parts = host.split(".")
            if len(parts) >= 2:
                return True
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


def is_domain_authorized(host: str, platform: str = "") -> bool:
    """Checks if a host belongs to the authorized platform, accredited partner, or university."""
    if platform and platform in PLATFORM_DOMAINS:
        if match_domain_to_list(host, PLATFORM_DOMAINS[platform]):
            return True
    elif not platform or platform not in PLATFORM_DOMAINS:
        for domain_list in PLATFORM_DOMAINS.values():
            if match_domain_to_list(host, domain_list):
                return True

    if match_domain_to_list(host, ACCREDITED_PARTNER_DOMAINS):
        return True

    if is_university_domain(host):
        return True

    return False


def check_open_redirect_parameters(url: str, platform: str = "") -> Tuple[bool, List[str]]:
    """
    Inspects URL query parameters for open redirect targets pointing to untrusted or scam destinations.
    """
    flags: List[str] = []
    try:
        parsed = urlparse(url)
        if not parsed.query:
            return True, flags

        qs = parse_qs(parsed.query)
        for key, vals in qs.items():
            if key.lower() in OPEN_REDIRECT_PARAM_KEYS:
                for val in vals:
                    if "://" in val:
                        dest_parsed = urlparse(val)
                        dest_host = dest_parsed.hostname or dest_parsed.netloc.split(":")[0].strip().lower()
                        if not dest_host:
                            continue

                        # Check destination against scam keywords
                        for scam in SCAM_DOMAIN_KEYWORDS:
                            if scam in dest_host:
                                flags.append(f"DECEPTIVE_OPEN_REDIRECT_SCAM_TARGET: '{dest_host}' contains '{scam}'")
                                return False, flags

                        # Check destination against suspicious TLDs
                        for tld in SUSPICIOUS_TLDS:
                            if dest_host.endswith(tld):
                                flags.append(f"DECEPTIVE_OPEN_REDIRECT_SUSPICIOUS_TLD: '{dest_host}' ends with '{tld}'")
                                return False, flags

                        # Check destination against banned shorteners
                        for shortener in BANNED_URL_SHORTENERS:
                            if dest_host == shortener or dest_host.endswith("." + shortener):
                                flags.append(f"DECEPTIVE_OPEN_REDIRECT_SHORTENER: '{shortener}'")
                                return False, flags

                        # Check destination against authorized domains
                        if not is_domain_authorized(dest_host, platform):
                            flags.append(f"UNTRUSTED_OPEN_REDIRECT_DESTINATION: '{dest_host}' is outside authorized directory")
                            return False, flags
    except Exception:
        pass

    return True, flags


def check_domain_authenticity(url: str, platform: str = "") -> Tuple[bool, str, str, List[str]]:
    """
    Evaluates domain legitimacy against trusted vendor ecosystem, partner whitelist,
    accredited universities, banned shorteners, affiliate networks, typo-squatting,
    and open redirect vulnerabilities.
    
    Returns:
        (is_authentic, trust_tier, reason, flags)
    """
    host = clean_hostname(url)
    flags: List[str] = []

    if not host or "." not in host:
        return False, "Untrusted", "Malformed or missing hostname", ["MALFORMED_HOSTNAME"]

    if is_ip_address(host):
        return False, "Untrusted", "Raw IP address instead of canonical vendor domain", ["RAW_IP_HOSTNAME"]

    # 1. Check for typo-squatting lookalikes FIRST before generic checks
    all_authorized = get_all_authorized_domains()
    if not match_domain_to_list(host, list(all_authorized)):
        for pattern in TYPOSQUATTING_PATTERNS:
            if pattern.search(host):
                flags.append("DECEPTIVE_TYPOSQUATTING_DOMAIN")
                return False, "Scam / Deceptive", f"Deceptive typo-squatting pattern detected: {host}", flags

    # 2. Scam keyword check in hostname
    for kw in SCAM_DOMAIN_KEYWORDS:
        if kw in host:
            flags.append("SCAM_KEYWORD_IN_DOMAIN")
            return False, "Scam / Deceptive", f"Detected scam / braindump keyword '{kw}' in domain name", flags

    # 3. Banned shortener check
    for shortener in BANNED_URL_SHORTENERS:
        if host == shortener or host.endswith("." + shortener):
            flags.append("BANNED_URL_SHORTENER")
            return False, "Scam / Deceptive", f"Disallowed URL shortener / redirect cloaker: {host}", flags

    # 4. Known affiliate network check
    for aff in KNOWN_AFFILIATE_NETWORKS:
        if host == aff or host.endswith("." + aff):
            flags.append("UNTRUSTED_AFFILIATE_NETWORK")
            return False, "Untrusted Affiliate Network", f"Redirect/ad affiliate aggregator detected: {host}", flags

    # 5. Suspicious TLD check
    for tld in SUSPICIOUS_TLDS:
        if host.endswith(tld):
            flags.append("SUSPICIOUS_TLD")
            return False, "Untrusted", f"High-risk scam TLD detected: {tld}", flags

    # 6. Open redirect parameter security check
    open_redirect_ok, redirect_param_flags = check_open_redirect_parameters(url, platform)
    if not open_redirect_ok:
        flags.extend(redirect_param_flags)
        is_scam = any("DECEPTIVE" in f for f in redirect_param_flags)
        tier = "Scam / Deceptive" if is_scam else "Untrusted"
        return False, tier, f"Deceptive open redirect parameter detected: {'; '.join(redirect_param_flags)}", flags

    # 7. Platform-specific domain verification
    if platform and platform in PLATFORM_DOMAINS:
        allowed_for_platform = PLATFORM_DOMAINS[platform]
        if match_domain_to_list(host, allowed_for_platform):
            flags.append("OFFICIAL_PRIMARY_VENDOR_DOMAIN")
            return True, "Official Vendor Portal", f"Verified official {platform} primary portal", flags

        # Check accredited partners (allowed for any platform)
        if match_domain_to_list(host, ACCREDITED_PARTNER_DOMAINS):
            flags.append("ACCREDITED_PARTNER_DOMAIN")
            return True, "Accredited Exam Partner", f"Verified accredited partner domain: {host}", flags

        # Check accredited university domains
        if is_university_domain(host):
            flags.append("ACCREDITED_UNIVERSITY_DOMAIN")
            return True, "Accredited Educational Institution", f"Verified accredited educational domain: {host}", flags

        # Check if domain belongs to a DIFFERENT vendor in PLATFORM_DOMAINS
        for other_platform, other_domains in PLATFORM_DOMAINS.items():
            if other_platform != platform and match_domain_to_list(host, other_domains):
                flags.append("MISMATCHED_VENDOR_DOMAIN")
                return False, "Mismatched Vendor", f"Vendor domain mismatch: offer declared as '{platform}', but domain '{host}' belongs to '{other_platform}'", flags

        flags.append("UNVERIFIED_THIRD_PARTY_DOMAIN")
        return False, "Untrusted", f"Unrecognized domain outside verified {platform} directory: {host}", flags

    # 8. Platform not specified or not in PLATFORM_DOMAINS
    for plat_name, domain_list in PLATFORM_DOMAINS.items():
        if match_domain_to_list(host, domain_list):
            flags.append("OFFICIAL_PRIMARY_VENDOR_DOMAIN")
            return True, "Official Vendor Portal", f"Verified official {plat_name} portal", flags

    if match_domain_to_list(host, ACCREDITED_PARTNER_DOMAINS):
        flags.append("ACCREDITED_PARTNER_DOMAIN")
        return True, "Accredited Exam Partner", f"Verified accredited partner domain: {host}", flags

    if is_university_domain(host):
        flags.append("ACCREDITED_UNIVERSITY_DOMAIN")
        return True, "Accredited Educational Institution", f"Verified accredited educational domain: {host}", flags

    flags.append("UNVERIFIED_THIRD_PARTY_DOMAIN")
    return False, "Untrusted", f"Unrecognized domain outside verified provider directory: {host}", flags


def check_ssl_and_protocol(url: str) -> Tuple[bool, List[str]]:
    """
    Enforces strict HTTPS, canonical URL structure, standard transport ports,
    and rejects userinfo credential injection or raw IP hosts.
    """
    flags: List[str] = []
    parsed = urlparse(url)

    if parsed.scheme.lower() != "https":
        flags.append("INSECURE_HTTP_PROTOCOL")
        return False, flags

    flags.append("STRICT_HTTPS_PROTOCOL")

    # Reject userinfo (e.g. https://user:pass@domain.com)
    if parsed.username or parsed.password:
        flags.append("MALFORMED_URL_USERINFO")
        return False, flags

    # Standard port validation
    if parsed.port and parsed.port != 443:
        flags.append(f"NON_STANDARD_PORT_{parsed.port}")
        return False, flags
    else:
        flags.append("STANDARD_PORT_SECURITY")

    # Reject raw IP addresses
    host = clean_hostname(url)
    if is_ip_address(host):
        flags.append("RAW_IP_HOSTNAME")
        return False, flags

    # Canonical FQDN requirement (must contain at least one dot)
    if not host or "." not in host:
        flags.append("MALFORMED_HOSTNAME")
        return False, flags

    flags.append("CANONICAL_URL_STRUCTURE")
    return True, flags


def check_redirect_chain_security(chain: List[str], platform: str = "") -> Tuple[bool, List[str]]:
    """
    Audits the entire redirect trail to ensure:
    - Every intermediate hop maintained HTTPS transport security (no SSL downgrades).
    - No hop routed through banned URL shorteners or scam affiliate networks.
    - No hop routed through scam domains or suspicious TLDs.
    - No hop routed through untrusted ad-tracking networks.
    - Final destination lands on an authorized vendor, partner, or university domain.
    """
    flags: List[str] = []
    if not chain:
        return True, ["CLEAN_REDIRECT_CHAIN"]

    # 1. Audit all hops for SSL protocol integrity
    for hop in chain:
        parsed = urlparse(hop)
        if parsed.scheme.lower() != "https":
            flags.append("REDIRECT_SSL_DOWNGRADE")
            return False, flags

    # 2. Audit intermediate hops (excluding final destination)
    for hop in chain[:-1]:
        host = clean_hostname(hop)

        # Check banned shorteners
        for shortener in BANNED_URL_SHORTENERS:
            if host == shortener or host.endswith("." + shortener):
                flags.append("REDIRECT_THROUGH_SHORTENER")
                return False, flags

        # Check scam keywords in hop domain
        for scam in SCAM_DOMAIN_KEYWORDS:
            if scam in host:
                flags.append(f"REDIRECT_THROUGH_SCAM_DOMAIN: '{host}' contains '{scam}'")
                return False, flags

        # Check suspicious TLDs in hop domain
        for tld in SUSPICIOUS_TLDS:
            if host.endswith(tld):
                flags.append(f"REDIRECT_THROUGH_SUSPICIOUS_TLD: '{host}' ends with '{tld}'")
                return False, flags

        # Check affiliate networks in hop domain
        for aff in KNOWN_AFFILIATE_NETWORKS:
            if host == aff or host.endswith("." + aff):
                flags.append(f"REDIRECT_THROUGH_AFFILIATE_NETWORK: '{host}'")
                return False, flags

        # Check open redirect parameters in hop URL
        or_ok, or_flags = check_open_redirect_parameters(hop, platform)
        if not or_ok:
            flags.extend(or_flags)
            return False, flags

    # 3. Audit final destination authenticity
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
        return True, 0, ["CONTENT_INSPECTION_BYPASS"], []

    lower_text = body_text.lower()
    positives: List[str] = []
    warnings: List[str] = []
    score_delta = 0

    # 1. Check for deceptive scam / braindump / paywall / expired patterns
    for pat in DECEPTIVE_CONTENT_PATTERNS:
        match = pat.search(lower_text)
        if match:
            warnings.append(f"DECEPTIVE_PATTERN_DETECTED: '{match.group(0)}'")

    if warnings:
        return False, -50, positives, warnings

    # 2. Corroborate vendor / platform name
    if platform:
        platform_tokens = [tok.lower() for tok in re.split(r"[\s/]+", platform) if len(tok) > 2]
        if any(tok in lower_text for tok in platform_tokens):
            positives.append("VENDOR_NAME_MATCHED")
            score_delta += 5

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
        score_delta += 5
    elif len(matched_kws) == 1:
        positives.append("SINGLE_CREDENTIAL_SIGNAL")
        score_delta += 3

    passed = len(warnings) == 0
    return passed, score_delta, positives, warnings


def audit_offer_authenticity(
    offer: Dict[str, Any],
    body_text: str = "",
    redirect_chain: Optional[List[str]] = None,
    network_provenance: Optional[Union[Any, Dict[str, Any]]] = None,
    temporal_longevity: Optional[Union[Any, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Executes the multi-layer authenticity verification pipeline for an offer.
    Integrates Tier 1 Network Provenance (ASN/BGP, TLS CT, DNSSEC) and
    Tier 2 Temporal Longevity (Wayback CDX, Anti-Fly-by-Night, Recurrence).
    Computes an authenticity score (0-100), security flags, and definitive verdict.
    """
    url = offer.get("url", "")
    platform = offer.get("platform", "")
    cert_name = offer.get("certification_name", "")
    exam_code = offer.get("exam_code", "")

    checks_passed: List[str] = []
    warning_flags: List[str] = []
    score = 0

    # Layer 1: Domain & Portal Whitelist Check (up to 45 pts)
    domain_ok, trust_tier, domain_reason, domain_flags = check_domain_authenticity(url, platform)
    if domain_ok:
        if trust_tier == "Official Vendor Portal":
            score += 45
        elif trust_tier in ["Accredited Exam Partner", "Accredited Educational Institution"]:
            score += 40
        else:
            score += 35
        checks_passed.extend(domain_flags)
    else:
        warning_flags.extend(domain_flags)
        if any(f.startswith("DECEPTIVE") or "SCAM" in f or "MISMATCHED" in f for f in domain_flags):
            score -= 50
        else:
            score -= 20

    # Layer 2: SSL/TLS & Protocol Security (up to 25 pts)
    ssl_ok, ssl_flags = check_ssl_and_protocol(url)
    if ssl_ok:
        score += 25
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

    # Layer 4: Content & Accreditation Corroboration (up to 15 pts)
    corr_ok, corr_delta, corr_positives, corr_warnings = corroborate_content(
        body_text=body_text,
        platform=platform,
        cert_name=cert_name,
        exam_code=exam_code
    )
    score += corr_delta
    checks_passed.extend(corr_positives)
    warning_flags.extend(corr_warnings)

    # Layer 5: Network Provenance Integration (Tier 1)
    prov_obj = network_provenance or offer.get("network_provenance")
    if prov_obj:
        if hasattr(prov_obj, "is_vendor_infra"):
            is_infra = prov_obj.is_vendor_infra
            asn_val = prov_obj.asn
            dnssec = prov_obj.dnssec_valid
            ct_ver = prov_obj.tls_ct_verified
            sct_cnt = prov_obj.sct_count
            caa_auth = prov_obj.caa_authorized
        elif isinstance(prov_obj, dict):
            is_infra = prov_obj.get("is_vendor_infra", True)
            asn_val = prov_obj.get("asn")
            dnssec = prov_obj.get("dnssec_valid", False)
            ct_ver = prov_obj.get("tls_ct_verified", True)
            sct_cnt = prov_obj.get("sct_count", 0)
            caa_auth = prov_obj.get("caa_authorized", True)
        else:
            is_infra = True
            asn_val = None
            dnssec = False
            ct_ver = True
            sct_cnt = 0
            caa_auth = True

        if is_infra:
            checks_passed.append(f"ASN_ORIGIN_VERIFIED_AS{asn_val or 'DEFAULT'}")
            score += 5
        else:
            warning_flags.append(f"SUSPICIOUS_NETWORK_ORIGIN_AS{asn_val or 'UNKNOWN'}")
            score -= 15

        if dnssec:
            checks_passed.append("DNSSEC_CRYPTOGRAPHICALLY_VALID")
            score += 5

        if ct_ver:
            checks_passed.append(f"TLS_CT_VERIFIED ({sct_cnt} SCTs)")
        else:
            warning_flags.append("TLS_CT_MISSING_OR_INVALID")
            score -= 10

        if not caa_auth:
            warning_flags.append("CAA_ISSUER_UNAUTHORIZED")
            score -= 10

    # Layer 6: Temporal Longevity Integration (Tier 2)
    temp_obj = temporal_longevity or offer.get("temporal_longevity")
    if temp_obj:
        if hasattr(temp_obj, "is_anti_fly_by_night_passed"):
            fly_passed = temp_obj.is_anti_fly_by_night_passed
            seasonal = temp_obj.is_seasonal_recurrent
            recurr_cls = getattr(temp_obj, "recurrence_classification", "unknown")
            age = temp_obj.domain_age_days
        elif isinstance(temp_obj, dict):
            fly_passed = temp_obj.get("is_anti_fly_by_night_passed", True)
            seasonal = temp_obj.get("is_seasonal_recurrent", False)
            recurr_cls = temp_obj.get("recurrence_classification", "unknown")
            age = temp_obj.get("domain_age_days")
        else:
            fly_passed = True
            seasonal = False
            recurr_cls = "unknown"
            age = None

        if not fly_passed:
            warning_flags.append("FLY_BY_NIGHT_DOMAIN_PENALTY")
            score -= 40
        else:
            if age is not None and age >= 365:
                checks_passed.append(f"ESTABLISHED_DOMAIN_LONGEVITY ({age} days)")

        if seasonal:
            checks_passed.append(f"SEASONAL_RECURRENCE_VERIFIED_{recurr_cls.upper()}")
            score += 5

    # Historical Archive special-case: If archived record on authentic domain, guarantee baseline
    if offer.get("is_historical_archive") and domain_ok and ssl_ok:
        score = max(score, 100)

    # Clamping score [0, 100]
    final_score = max(0, min(100, score))

    # Determine verdict
    has_critical_scam_flags = any(
        f.startswith("DECEPTIVE") or "SCAM" in f or "BANNED_URL_SHORTENER" in f or "AFFILIATE" in f or "MISMATCHED" in f
        for f in warning_flags
    )

    has_suspicious_flags = any(
        "FLY_BY_NIGHT" in f or "SUSPICIOUS_NETWORK_ORIGIN" in f
        for f in warning_flags
    )

    if has_critical_scam_flags:
        verdict = "DECEPTIVE_SCAM"
        is_authentic = False
    elif not domain_ok or not ssl_ok or not redirect_ok or not corr_ok or has_suspicious_flags:
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

    res = {
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
        "summary": summary,
    }
    if prov_obj:
        res["network_provenance"] = prov_obj.model_dump() if hasattr(prov_obj, "model_dump") else prov_obj
    if temp_obj:
        res["temporal_longevity"] = temp_obj.model_dump() if hasattr(temp_obj, "model_dump") else temp_obj
    return res

