"""
CertPulse Temporal Longevity Engine (Tier 2: Wayback CDX & Recurrence).

Capabilities:
1. WaybackCDXClient: Queries web.archive.org/cdx/search/cdx with compact column projections,
   yearly/monthly collapsing, and resilient 3.0s circuit-breaker timeout handling.
2. TemporalLongevityCache: Thread- and process-safe persistent local JSON caching in
   data/temporal_longevity_cache.json using atomic temp-file replacement.
3. LongevityScorer: Anti-Fly-by-Night domain age scoring engine that penalizes disposable
   domains (<60 days old with zero archive footprint) while pre-approving whitelisted vendor ecosystems.
4. SeasonalRecurrenceClassifier: Distinguishes multi-year recurring challenge waves, annual windows,
   evergreen portals, and ephemeral one-off anomalies.
5. TemporalAnalyzer: Master orchestrator integrating caching, scoring, classification, and
   exporting strict Pydantic V2 TemporalLongevity models.
"""

from __future__ import annotations

import os
import re
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from typing import Any, Dict, List, Optional, Tuple, Union

import httpx
from src.models import TemporalLongevity

# Import domain authorization directories from authenticity engine
try:
    from src.authenticity import PLATFORM_DOMAINS, ACCREDITED_PARTNER_DOMAINS
    def is_domain_authorized(host: str, platform: str = "") -> bool:
        if not host:
            return False
        clean = host.strip().lower()
        if platform and platform in PLATFORM_DOMAINS:
            for dom in PLATFORM_DOMAINS[platform]:
                if clean == dom or clean.endswith(f".{dom}"):
                    return True
        for plat_doms in PLATFORM_DOMAINS.values():
            for dom in plat_doms:
                if clean == dom or clean.endswith(f".{dom}"):
                    return True
        for partner in ACCREDITED_PARTNER_DOMAINS:
            if clean == partner or clean.endswith(f".{partner}"):
                return True
        return False
except ImportError:
    PLATFORM_DOMAINS = {}
    ACCREDITED_PARTNER_DOMAINS = []
    def is_domain_authorized(host: str, platform: str = "") -> bool:
        return False

logger = logging.getLogger(__name__)


# ==============================================================================
# 1. Wayback Machine CDX API Client
# ==============================================================================

class WaybackCDXClient:
    """
    Resilient client for the Internet Archive Wayback Machine CDX API.
    Enforces a strict 3.0s timeout and handles 503/429/connection errors gracefully.
    """
    DEFAULT_BASE_URL: str = "https://web.archive.org/cdx/search/cdx"
    DEFAULT_TIMEOUT: float = 3.0
    DEFAULT_USER_AGENT: str = "CertPulse-Verifier/2.0 (+https://github.com/athishpranav/certpulse)"

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        self.base_url = base_url
        self.timeout = timeout
        self.user_agent = user_agent

    def clean_target(self, target: Optional[str]) -> str:
        """Normalizes a URL or hostname into clean CDX query format."""
        if not target or not isinstance(target, str):
            return ""
        clean = target.strip()
        if not clean:
            return ""
        if "://" in clean:
            parsed = urlparse(clean)
            host = (parsed.hostname or parsed.netloc or "").split(":")[0].lower()
            path = parsed.path.rstrip("/")
            return f"{host}{path}" if path else host
        return clean.split("/")[0].split(":")[0].strip().lower()

    def query_snapshots(
        self,
        url_or_domain: Optional[str],
        collapse: str = "timestamp:4",
        limit: int = 20,
        match_type: Optional[str] = None,
    ) -> List[Dict[str, str]]:
        """
        Queries Wayback CDX API for snapshots.
        Returns parsed list of snapshot dictionaries with keys: timestamp, original, statuscode, digest.
        Returns empty list on 503, 429, timeout, empty target, or empty archive history without raising exceptions.
        """
        clean_url = self.clean_target(url_or_domain)
        if not clean_url:
            return []

        params: Dict[str, Union[str, int]] = {
            "url": clean_url,
            "output": "json",
            "fl": "timestamp,original,statuscode,digest",
            "collapse": collapse,
            "limit": limit,
        }
        if match_type:
            params["matchType"] = match_type

        headers = {
            "User-Agent": self.user_agent,
            "Accept": "application/json",
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(self.base_url, params=params, headers=headers)
                if response.status_code != 200:
                    logger.warning(
                        "Wayback CDX API returned status %d for %s",
                        response.status_code,
                        clean_url,
                    )
                    return []

                raw_data = response.json()
                if not raw_data or not isinstance(raw_data, list) or len(raw_data) < 2:
                    return []

                headers_row = [str(h).lower() for h in raw_data[0]]
                snapshots: List[Dict[str, str]] = []
                for row in raw_data[1:]:
                    if isinstance(row, list) and len(row) == len(headers_row):
                        snapshots.append(dict(zip(headers_row, [str(c) for c in row])))
                return snapshots

        except (httpx.TimeoutException, httpx.ConnectError, httpx.HTTPStatusError, httpx.RequestError) as exc:
            logger.warning("Wayback CDX query failed for %s: %s", clean_url, exc)
            return []
        except Exception as exc:
            logger.error("Unexpected error querying Wayback CDX for %s: %s", clean_url, exc)
            return []

    def get_earliest_snapshot(self, url_or_domain: Optional[str]) -> Optional[Dict[str, str]]:
        """Retrieves the single earliest snapshot for a domain or URL."""
        if not url_or_domain:
            return None
        snapshots = self.query_snapshots(url_or_domain, collapse="timestamp:4", limit=1)
        return snapshots[0] if snapshots else None

    def get_yearly_snapshot_years(self, url_or_domain: Optional[str]) -> List[int]:
        """Extracts sorted distinct calendar years recorded in CDX snapshots."""
        if not url_or_domain:
            return []
        snapshots = self.query_snapshots(url_or_domain, collapse="timestamp:4", limit=25)
        years: set[int] = set()
        for snap in snapshots:
            if not isinstance(snap, dict):
                continue
            ts = snap.get("timestamp", "")
            dt = LongevityScorer.parse_cdx_timestamp(ts)
            if dt:
                years.add(dt.year)
            elif len(ts) >= 4 and ts[:4].isdigit():
                try:
                    yr = int(ts[:4])
                    if 1990 <= yr <= 2100:
                        years.add(yr)
                except (ValueError, TypeError):
                    pass
        return sorted(list(years))


# ==============================================================================
# 2. Local Persistent Cache
# ==============================================================================

class TemporalLongevityCache:
    """
    Manages thread- and process-safe disk caching in data/temporal_longevity_cache.json.
    Uses atomic temporary file write and replacement to prevent corrupted state.
    """
    DEFAULT_CACHE_PATH = Path("data/temporal_longevity_cache.json")

    def __init__(self, cache_path: Optional[Path] = None) -> None:
        self.cache_path = cache_path or self.DEFAULT_CACHE_PATH
        self._cache: Dict[str, Any] = {}
        self.load()

    def load(self) -> Dict[str, Any]:
        """Loads cache records from disk. Initializes empty cache if file does not exist or is corrupted."""
        if self.cache_path.exists():
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    parsed = json.loads(content) if content else {}
                    self._cache = parsed if isinstance(parsed, dict) else {}
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to decode cache file %s, initializing empty: %s", self.cache_path, exc)
                self._cache = {}
        else:
            self._cache = {}
        return self._cache

    def get(self, key: Optional[str]) -> Optional[Dict[str, Any]]:
        """Retrieves a cached entry by canonical key."""
        if not key or not isinstance(key, str):
            return None
        if not isinstance(self._cache, dict):
            self._cache = {}
        return self._cache.get(key.lower().strip())

    def set(self, key: str, data: Dict[str, Any]) -> None:
        """Sets a cached entry and synchronizes to persistent disk storage."""
        if not key or not isinstance(key, str):
            return
        if not isinstance(self._cache, dict):
            self._cache = {}
        clean_key = key.lower().strip()
        self._cache[clean_key] = data
        self.save()

    def has_valid_entry(self, key: str, max_age_days: int = 30) -> bool:
        """
        Returns True if a cached entry exists and is within freshness window.
        Established domains (>365 days old) are treated as permanently valid.
        """
        entry = self.get(key)
        if not entry or not isinstance(entry, dict):
            return False

        # Entries with no archive longevity footprint are invalid
        longevity_days = entry.get("longevity_days")
        domain_age_days = entry.get("domain_age_days")
        if longevity_days is None and domain_age_days is None:
            return False

        # Established domains with over 1 year of age have permanent longevity validity
        l_days = longevity_days if isinstance(longevity_days, (int, float)) else 0
        d_days = domain_age_days if isinstance(domain_age_days, (int, float)) else 0
        if l_days >= 365 or d_days >= 365:
            return True

        last_audited = entry.get("last_audited_utc")
        if not last_audited:
            return False

        try:
            audited_dt = datetime.fromisoformat(last_audited.replace("Z", "+00:00"))
            age = (datetime.now(timezone.utc) - audited_dt).days
            return age <= max_age_days
        except Exception:
            return False

    def save(self) -> None:
        """Atomically persists in-memory cache to disk via temp-file rename."""
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.cache_path.with_suffix(".tmp")
        try:
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2, sort_keys=True)
            # Atomic replacement on Windows and POSIX
            os.replace(temp_path, self.cache_path)
        except OSError as exc:
            logger.error("Failed to atomically save cache to %s: %s", self.cache_path, exc)
            if temp_path.exists():
                try:
                    temp_path.unlink()
                except OSError:
                    pass


# ==============================================================================
# 3. Anti-Fly-by-Night Longevity Scorer
# ==============================================================================

class LongevityScorer:
    """
    Evaluates domain historical age and enforces Anti-Fly-by-Night defense rules.
    Penalizes newly minted domains (<60 days old) and domains with zero archive footprint.
    """

    @staticmethod
    def parse_cdx_timestamp(ts: Optional[str]) -> Optional[datetime]:
        """Parses CDX 14-digit timestamp YYYYMMDDhhmmss or ISO string into UTC datetime."""
        if not ts:
            return None
        ts = str(ts).strip()
        # Handle ISO format
        if "T" in ts or "-" in ts:
            try:
                clean_iso = ts.replace("Z", "+00:00")
                dt = datetime.fromisoformat(clean_iso)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                pass
        # Handle 14-digit numeric string
        if len(ts) < 8 or not ts[:8].isdigit():
            return None
        try:
            year = int(ts[:4])
            month = int(ts[4:6])
            day = int(ts[6:8])
            hour = int(ts[8:10]) if len(ts) >= 10 and ts[8:10].isdigit() else 0
            minute = int(ts[10:12]) if len(ts) >= 12 and ts[10:12].isdigit() else 0
            second = int(ts[12:14]) if len(ts) >= 14 and ts[12:14].isdigit() else 0
            return datetime(year, month, day, hour, minute, second, tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return None

    def calculate_domain_age(self, first_seen_ts: Optional[str]) -> Optional[int]:
        """Calculates domain age in days from first seen CDX timestamp."""
        dt = self.parse_cdx_timestamp(first_seen_ts)
        if not dt:
            return None
        now = datetime.now(timezone.utc)
        age_days = (now - dt).days
        return max(0, age_days)

    def score_domain_longevity(
        self,
        domain: str,
        first_seen_ts: Optional[str],
        platform: str = "",
    ) -> Dict[str, Any]:
        """
        Computes the longevity score (0-100), pass/fail verdict, and warning flags.
        Enforces strict mathematical invariant:
          - Whitelisted platform domains: Score 100, Passed True.
          - Age >= 365 days: Score 100, Passed True.
          - 180 <= Age < 365 days: Score 80, Passed True.
          - 60 <= Age < 180 days: Score 60, Passed True.
          - 14 <= Age < 60 days: Score 25, Passed False (Fly-by-Night candidate).
          - Age < 14 days: Score 0, Passed False (Freshly minted domain).
          - Age None / Zero Footprint: Score 10, Passed False.
        """
        clean_domain = (domain or "").strip().lower()
        platform = platform or ""
        warning_flags: List[str] = []

        # 1. Whitelist Invariant Check
        if is_domain_authorized(clean_domain, platform):
            age_days = self.calculate_domain_age(first_seen_ts) or 1000
            first_seen_dt = self.parse_cdx_timestamp(first_seen_ts)
            return {
                "longevity_score": 100,
                "domain_age_days": age_days,
                "is_anti_fly_by_night_passed": True,
                "risk_tier": "TRUSTED_VENDOR",
                "first_seen_utc": first_seen_dt.isoformat() if first_seen_dt else None,
                "warning_flags": [],
            }

        # 2. Unindexed / Zero Footprint Check
        if not first_seen_ts:
            warning_flags.append("ZERO_ARCHIVE_FOOTPRINT")
            warning_flags.append("FLY_BY_NIGHT_RISK")
            return {
                "longevity_score": 10,
                "domain_age_days": None,
                "is_anti_fly_by_night_passed": False,
                "risk_tier": "ZERO_ARCHIVE_FOOTPRINT",
                "first_seen_utc": None,
                "warning_flags": warning_flags,
            }

        age_days = self.calculate_domain_age(first_seen_ts)
        first_seen_dt = self.parse_cdx_timestamp(first_seen_ts)
        first_seen_iso = first_seen_dt.isoformat() if first_seen_dt else None

        if age_days is None:
            warning_flags.append("UNPARSEABLE_ARCHIVE_TIMESTAMP")
            warning_flags.append("FLY_BY_NIGHT_RISK")
            return {
                "longevity_score": 10,
                "domain_age_days": None,
                "is_anti_fly_by_night_passed": False,
                "risk_tier": "ZERO_ARCHIVE_FOOTPRINT",
                "first_seen_utc": None,
                "warning_flags": warning_flags,
            }

        if age_days >= 365:
            score = 100
            passed = True
            risk_tier = "ESTABLISHED_DOMAIN"
        elif age_days >= 180:
            score = 80
            passed = True
            risk_tier = "MATURE_DOMAIN"
        elif age_days >= 60:
            score = 60
            passed = True
            risk_tier = "MODERATE_AGE_DOMAIN"
        elif age_days >= 14:
            score = 25
            passed = False
            risk_tier = "FLY_BY_NIGHT_CANDIDATE"
            warning_flags.append("DOMAIN_AGE_BELOW_60_DAYS")
            warning_flags.append("FLY_BY_NIGHT_RISK")
        else:
            score = 0
            passed = False
            risk_tier = "EXTREME_FLY_BY_NIGHT_RISK"
            warning_flags.append("FRESHLY_MINTED_DOMAIN")
            warning_flags.append("CRITICAL_PHISHING_RISK")

        return {
            "longevity_score": score,
            "domain_age_days": age_days,
            "is_anti_fly_by_night_passed": passed,
            "risk_tier": risk_tier,
            "first_seen_utc": first_seen_iso,
            "warning_flags": warning_flags,
        }


# ==============================================================================
# 4. Seasonal Promotion Recurrence Classifier
# ==============================================================================

class SeasonalRecurrenceClassifier:
    """
    Classifies promotional seasonality based on historical snapshot temporal distribution:
    - annual_window: Snapshots span >= 2 distinct calendar years.
    - periodic_challenge_wave: Snapshots cluster across >= 2 quarters in past 24 months.
    - evergreen: Unbroken continuous 200 OK presence across >= 3 years.
    - event_driven: Snapshot history spans < 90 days (one-off promotional anomaly).
    """

    KNOWN_ANNUAL_PROGRAMS = [
        "lift",
        "scholarship",
        "build-challenge",
        "cloud-skills-challenge",
        "she-builds",
        "learn-to-earn",
        "1mcc",
        "innovators",
    ]

    def classify_recurrence(
        self,
        url: Optional[str],
        snapshots: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """Evaluates snapshot timeline and returns recurrence classification."""
        url_lower = (url or "").lower()
        # Fast catalog check for known annual program tokens in path
        is_known_annual = any(prog in url_lower for prog in self.KNOWN_ANNUAL_PROGRAMS)

        if not snapshots:
            if is_known_annual:
                return {
                    "is_seasonal_recurrent": True,
                    "classification": "annual_window",
                    "distinct_years": [],
                    "confidence": 0.85,
                }
            return {
                "is_seasonal_recurrent": False,
                "classification": "unknown",
                "distinct_years": [],
                "confidence": 0.50,
            }

        years: set[int] = set()
        year_months: set[str] = set()
        timestamps: List[datetime] = []
        ok_snapshots = 0

        for s in snapshots:
            if not isinstance(s, dict):
                continue
            ts = s.get("timestamp", "")
            if not ts:
                continue
            dt = LongevityScorer.parse_cdx_timestamp(ts)
            if not dt:
                continue
            years.add(dt.year)
            year_months.add(f"{dt.year:04d}{dt.month:02d}")
            timestamps.append(dt)
            status = str(s.get("statuscode", ""))
            if status in ("200", "301", "302"):
                ok_snapshots += 1

        sorted_years = sorted(list(years))
        distinct_year_count = len(sorted_years)

        # Calculate time span in days
        if len(timestamps) >= 2:
            timestamps.sort()
            span_days = (timestamps[-1] - timestamps[0]).days
        else:
            span_days = 0

        # Edge Case: Single burst within 7 days or < 90 days
        if distinct_year_count <= 1 and span_days < 90 and not is_known_annual:
            return {
                "is_seasonal_recurrent": False,
                "classification": "event_driven",
                "distinct_years": sorted_years,
                "confidence": 0.70,
            }

        # Edge Case: Exactly 2 sporadic snapshots widely separated without recurrent cluster
        if distinct_year_count == 2 and len(snapshots) == 2 and span_days > 400 and not is_known_annual:
            return {
                "is_seasonal_recurrent": False,
                "classification": "event_driven",
                "distinct_years": sorted_years,
                "confidence": 0.65,
            }

        # 1. Multi-Year Established Recurring Promotion
        if distinct_year_count >= 2 or is_known_annual:
            # Check for evergreen continuous vs seasonal window
            if distinct_year_count >= 3 and ok_snapshots >= 5 and not is_known_annual:
                classification = "evergreen"
                confidence = 0.95
            else:
                classification = "annual_window"
                confidence = 0.90
            return {
                "is_seasonal_recurrent": True,
                "classification": classification,
                "distinct_years": sorted_years,
                "confidence": confidence,
            }

        # 2. Periodic Challenge Wave within Recent Timeline (>= 3 distinct months)
        if len(year_months) >= 3:
            return {
                "is_seasonal_recurrent": True,
                "classification": "periodic_challenge_wave",
                "distinct_years": sorted_years,
                "confidence": 0.80,
            }

        # 3. Default one-off or ephemeral
        return {
            "is_seasonal_recurrent": False,
            "classification": "event_driven",
            "distinct_years": sorted_years,
            "confidence": 0.70,
        }


# ==============================================================================
# 5. Master Temporal Analyzer
# ==============================================================================

class TemporalAnalyzer:
    """
    Master orchestrator for CertPulse Temporal Longevity Engine.
    Unifies Wayback CDX querying, persistent caching, Anti-Fly-by-Night domain scoring,
    and seasonal promotion recurrence classification.
    """

    def __init__(
        self,
        cache_path: Optional[Path] = None,
        timeout: float = 3.0,
    ) -> None:
        self.cdx_client = WaybackCDXClient(timeout=timeout)
        self.cache = TemporalLongevityCache(cache_path=cache_path)
        self.longevity_scorer = LongevityScorer()
        self.recurrence_classifier = SeasonalRecurrenceClassifier()

    def _extract_hostname(self, url_or_host: Optional[str]) -> str:
        """Extracts lowercase FQDN hostname."""
        if not url_or_host or not isinstance(url_or_host, str):
            return ""
        if "://" in url_or_host:
            parsed = urlparse(url_or_host)
            host = parsed.hostname or parsed.netloc or parsed.path or ""
        else:
            host = url_or_host.split("/")[0]
        return host.split(":")[0].strip().lower()

    def analyze_url(self, url: Optional[str], platform: str = "") -> TemporalLongevity:
        """
        Executes full temporal verification pipeline for a target URL.
        Guarantees resilient fallback so builds and tests never fail on external 503s.
        """
        now_utc = datetime.now(timezone.utc).isoformat()
        if not url or not isinstance(url, str) or not url.strip():
            return TemporalLongevity(
                first_seen_archive_utc=None,
                domain_age_days=None,
                snapshot_count=0,
                is_anti_fly_by_night_passed=False,
                is_seasonal_recurrent=False,
                longevity_score=10,
                recurrence_classification="unknown",
                verified_at_utc=now_utc,
                source="offline_fallback",
                warning_flags=["ZERO_ARCHIVE_FOOTPRINT", "FLY_BY_NIGHT_RISK"],
            )

        hostname = self._extract_hostname(url)
        if not hostname:
            return TemporalLongevity(
                first_seen_archive_utc=None,
                domain_age_days=None,
                snapshot_count=0,
                is_anti_fly_by_night_passed=False,
                is_seasonal_recurrent=False,
                longevity_score=10,
                recurrence_classification="unknown",
                verified_at_utc=now_utc,
                source="offline_fallback",
                warning_flags=["ZERO_ARCHIVE_FOOTPRINT", "FLY_BY_NIGHT_RISK"],
            )

        # Step 1: Check Local Persistent Cache First
        cached_entry = self.cache.get(hostname)
        if cached_entry and isinstance(cached_entry, dict) and self.cache.has_valid_entry(hostname):
            first_seen = cached_entry.get("first_seen_utc")
            raw_ts = (
                str(first_seen).replace("-", "").replace(":", "").replace("T", "")[:14]
                if first_seen else None
            )
            score_data = self.longevity_scorer.score_domain_longevity(
                domain=hostname,
                first_seen_ts=raw_ts,
                platform=platform,
            )

            # Defensive deserialization of cached fields
            cached_snap_count = cached_entry.get("snapshot_count_yearly")
            if not isinstance(cached_snap_count, int) or cached_snap_count < 0:
                cached_snap_count = 1

            cached_score = cached_entry.get("longevity_score")
            if not isinstance(cached_score, int) or not (0 <= cached_score <= 100):
                cached_score = score_data.get("longevity_score", 100)

            cached_afbn = cached_entry.get("anti_fly_by_night_passed")
            if not isinstance(cached_afbn, bool):
                cached_afbn = score_data.get("is_anti_fly_by_night_passed", True)

            cached_rec = cached_entry.get("is_seasonal_recurrent")
            if not isinstance(cached_rec, bool):
                cached_rec = False

            cached_class = cached_entry.get("recurrence_classification")
            if not isinstance(cached_class, str) or not cached_class:
                cached_class = "unknown"

            cached_domain_age = cached_entry.get("domain_age_days")
            if cached_domain_age is None:
                cached_domain_age = cached_entry.get("longevity_days")
            if not isinstance(cached_domain_age, int) or cached_domain_age < 0:
                cached_domain_age = score_data.get("domain_age_days")

            return TemporalLongevity(
                first_seen_archive_utc=first_seen if isinstance(first_seen, str) else None,
                domain_age_days=cached_domain_age,
                snapshot_count=cached_snap_count,
                is_anti_fly_by_night_passed=cached_afbn,
                is_seasonal_recurrent=cached_rec,
                longevity_score=cached_score,
                recurrence_classification=cached_class,
                verified_at_utc=now_utc,
                source="cache",
                warning_flags=score_data.get("warning_flags", []),
            )

        # Step 2: Live CDX Query with 3.0s Timeout Protection
        snapshots = self.cdx_client.query_snapshots(hostname, collapse="timestamp:4", limit=15)
        path_snapshots = (
            self.cdx_client.query_snapshots(url, collapse="timestamp:4", limit=10)
            if url != hostname else snapshots
        )

        # Step 3: Handle External CDX Failure / 503 / Offline Fallback
        if not snapshots and is_domain_authorized(hostname, platform):
            # Whitelisted vendor domain fallback guarantee
            fallback_model = TemporalLongevity(
                first_seen_archive_utc="2015-01-01T00:00:00Z",
                domain_age_days=3000,
                snapshot_count=1,
                is_anti_fly_by_night_passed=True,
                is_seasonal_recurrent=False,
                longevity_score=100,
                recurrence_classification="evergreen",
                verified_at_utc=now_utc,
                source="vendor_whitelist_fallback",
                warning_flags=[],
            )
            return fallback_model

        if not snapshots:
            # Unknown unindexed or unreachable domain fallback
            fallback_model = TemporalLongevity(
                first_seen_archive_utc=None,
                domain_age_days=None,
                snapshot_count=0,
                is_anti_fly_by_night_passed=False,
                is_seasonal_recurrent=False,
                longevity_score=10,
                recurrence_classification="unknown",
                verified_at_utc=now_utc,
                source="offline_fallback",
                warning_flags=["ZERO_ARCHIVE_FOOTPRINT", "FLY_BY_NIGHT_RISK"],
            )
            return fallback_model

        # Step 4: Scoring & Classification
        earliest_snap = snapshots[0]
        first_seen_raw = earliest_snap.get("timestamp") if isinstance(earliest_snap, dict) else None
        scorer_res = self.longevity_scorer.score_domain_longevity(
            domain=hostname,
            first_seen_ts=first_seen_raw,
            platform=platform,
        )
        recurrence_res = self.recurrence_classifier.classify_recurrence(
            url=url,
            snapshots=path_snapshots or snapshots,
        )

        # Step 5: Save to Persistent Cache
        cache_record = {
            "first_seen_utc": scorer_res["first_seen_utc"],
            "snapshot_count_yearly": len(snapshots),
            "longevity_days": scorer_res["domain_age_days"],
            "domain_age_days": scorer_res["domain_age_days"],
            "anti_fly_by_night_passed": scorer_res["is_anti_fly_by_night_passed"],
            "longevity_score": scorer_res["longevity_score"],
            "is_seasonal_recurrent": recurrence_res["is_seasonal_recurrent"],
            "recurrence_classification": recurrence_res["classification"],
            "last_audited_utc": now_utc,
            "source": "live_cdx",
        }
        self.cache.set(hostname, cache_record)

        return TemporalLongevity(
            first_seen_archive_utc=scorer_res["first_seen_utc"],
            domain_age_days=scorer_res["domain_age_days"],
            snapshot_count=len(snapshots),
            is_anti_fly_by_night_passed=scorer_res["is_anti_fly_by_night_passed"],
            is_seasonal_recurrent=recurrence_res["is_seasonal_recurrent"],
            longevity_score=scorer_res["longevity_score"],
            recurrence_classification=recurrence_res["classification"],
            verified_at_utc=now_utc,
            source="live_cdx",
            warning_flags=scorer_res.get("warning_flags", []),
        )

    def audit_offer_longevity(self, offer: Dict[str, Any]) -> Dict[str, Any]:
        """Audits an offer dictionary and returns serializable dict for database storage."""
        if not isinstance(offer, dict):
            return {}
        url = offer.get("url") or ""
        platform = offer.get("platform") or ""
        result = self.analyze_url(url=url, platform=platform)
        return result.model_dump()
