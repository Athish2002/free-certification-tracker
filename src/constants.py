"""
Authoritative Constants and Signal Patterns for CertPulse.

Centralizes browser headers, Playwright launch options, route blocking patterns,
and signal keyword dictionaries across inspector, collector, and DOM verification engines.
"""

from __future__ import annotations

import re
from typing import Dict, List

# Standard realistic browser headers for HTTP requests
BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Playwright launch arguments for headless environments
PLAYWRIGHT_LAUNCH_ARGS: List[str] = [
    "--no-sandbox",
    "--disable-setuid-sandbox",
    "--disable-dev-shm-usage",
    "--disable-gpu",
    "--disable-extensions",
    "--disable-background-networking",
    "--disable-default-apps",
    "--disable-sync",
    "--disable-translate",
    "--mute-audio",
    "--hide-scrollbars",
    "--blink-settings=imagesEnabled=true",
]

# Heavy resource types and trackers blocked during DOM inspection
BLOCKED_RESOURCE_TYPES: List[str] = [
    "media",
    "font",
    "eventsource",
    "websocket",
    "manifest",
    "other",
]

BLOCKED_URL_REGEX = re.compile(
    r"(google-analytics\.com|googletagmanager\.com|doubleclick\.net|hotjar\.com|"
    r"facebook\.net|segment\.io|mixpanel\.com|optimizely\.com|clarity\.ms|"
    r"adroll\.com|criteo\.net|adnxs\.com|scorecardresearch\.com)",
    re.IGNORECASE,
)

# Capacity & cohort limits
CAPACITY_PATTERNS: List[str] = [
    "capacity has been reached",
    "capacity reached",
    "cohort is full",
    "cohort full",
    "seats no longer available",
    "seats are full",
    "all seats have been filled",
    "all seats are filled",
    "waitlist active",
    "waitlist only",
    "join the waitlist",
    "joined the waitlist",
    "registration limit reached",
    "capacity has been filled",
    "maximum capacity reached",
    "maximum capacity",
    "maximum attendees reached",
    "session is full",
    "sessions are full",
    "no seats remaining",
    "no seats left",
    "sold out",
]

# Expired coupon / promo code / redemption limits
COUPON_EXPIRED_PATTERNS: List[str] = [
    "coupon has expired",
    "coupon expired",
    "promo code invalid",
    "promo code has expired",
    "code is no longer valid",
    "redemption limit reached",
    "redemption limit has been reached",
    "discount no longer valid",
    "promotional code is no longer active",
    "voucher code expired",
    "voucher code is expired",
    "voucher is no longer valid",
    "voucher has expired",
    "promotion code invalid",
    "offer has expired",
    "promotion has ended",
    "discount code expired",
    "voucher code invalid",
    "redemption code has expired",
    "discount code is invalid",
    "invalid discount code",
    "coupon code is not valid",
    "promotion is no longer available",
]

# Registration closed or campaign concluded
REGISTRATION_CLOSED_PATTERNS: List[str] = [
    "has concluded",
    "closed new enrollments",
    "has closed new enrollments",
    "registration is closed",
    "registrations are closed",
    "registration has closed",
    "registration closed",
    "all vouchers have been claimed",
    "all vouchers are claimed",
    "vouchers are no longer available",
    "this promotion has ended",
    "promotion has ended",
    "this offer has expired",
    "the event has ended",
    "program is closed",
    "program has closed",
    "program concluded",
    "program has concluded",
    "program has ended",
    "no longer accepting submissions",
    "no longer accepting applications",
    "no longer accepting new enrollments",
    "enrollments are closed",
    "enrollment is closed",
    "no longer available",
    "campaign concluded",
    "offer ended",
    "milestone achieved",
]

# Maintenance and portal downtime
MAINTENANCE_PATTERNS: List[str] = [
    "down for maintenance",
    "scheduled maintenance",
    "system maintenance",
    "under maintenance",
    "maintenance in progress",
    "site is currently down",
    "routine maintenance",
    "maintenance mode",
    "temporarily unavailable",
    "portal is currently unavailable",
    "we are performing maintenance",
]

# Paid commercial catalog patterns without waivers
PAID_CATALOG_PATTERNS: List[str] = [
    "add to cart",
    "proceed to checkout",
    "buy now",
    "purchase exam",
    "exam fee:",
    "standard price:",
    "regular price:",
    "price: $",
    "cart total:",
    "billing details",
]

# Affirmative signals that page offers something free / waived
ZERO_DOLLAR_SIGNALS: List[str] = [
    "100% discount",
    "100% off",
    "free certification exam",
    "free exam voucher",
    "free certification",
    "$0.00",
    "$0",
    "0.00 usd",
    "zero dollar",
    "zero-dollar",
    "full scholarship",
    "fee waiver",
    "waiver code",
    "complimentary exam",
    "no cost exam",
]

CONFIRMED_ZERO_DOLLAR_CART: List[str] = [
    "total: $0.00",
    "balance due: $0.00",
    "amount due: $0.00",
    "order total: $0.00",
    "total due: $0.00",
    "$0.00 total",
]

CLOSED_PATTERNS: List[str] = list(dict.fromkeys(REGISTRATION_CLOSED_PATTERNS + CAPACITY_PATTERNS))

SOFT_404_PATTERNS: List[str] = [
    "page not found",
    "we couldn't find that page",
    "page you're looking for doesn't exist",
    "the page has been removed",
    "error 404",
    "this page is not available",
]

AFFIRMATIVE_OFFER_SIGNALS: List[str] = [
    "free",
    "voucher",
    "scholarship",
    "challenge",
    "no cost",
    "waiver",
    "discount",
    "reward",
    "credits",
    "badge",
    "grant",
    "complimentary",
    "100%",
    "level up",
    "applied skills",
]

VOUCHER_KEYWORDS: List[str] = [
    "voucher",
    "challenge",
    "free exam",
    "100%",
    "cloud skills",
    "level up",
    "levelup",
    "promo code",
    "discount code",
]

NOISE_KEYWORDS: List[str] = [
    "passed az",
    "passed aws",
    "failed",
    "exam tomorrow",
    "cancelled my exam",
    "lost my voucher",
    "retry az",
    "exam dump",
    "braindump",
    "dumps",
]

UNPROCTORED_BADGE_KEYWORDS: List[str] = [
    "skill badge",
    "applied skills",
    "arcade",
    "hands-on essentials",
    "fundamentals student",
    "digital credential",
    "educate graduate",
    "skills assessment",
    "lantern",
    "lakehouse fundamentals",
    "learning path",
    "workshop",
    "unproctored",
    "interactive lab",
    "sandbox",
    "course quiz",
    "accreditation",
]

PROCTORED_EXAM_KEYWORDS: List[str] = [
    "pearson",
    "vue",
    "kryterion",
    "webassessor",
    "psi",
    "proctored",
    "written exam",
    "exam voucher",
    "100% voucher",
    "certification exam",
    "cka",
    "ckad",
    "cks",
    "lfcs",
    "associate",
    "professional",
    "specialty",
    "foundations associate",
]

# Staleness threshold in days for active offers
STALENESS_THRESHOLD_DAYS: int = 14
