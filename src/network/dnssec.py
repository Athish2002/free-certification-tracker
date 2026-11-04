"""
CertPulse Network Provenance: DNSSEC Validation Engine.
Implements RFC 8484 DNS-over-HTTPS Authenticated Data (AD) flag validation.
"""

from __future__ import annotations

from typing import Any

import httpx

from src.network.asn import DOH_ENDPOINTS, clean_hostname


def query_doh_record(
    name: str,
    rtype: str,
    cd: int = 0,
    timeout: float = 3.0,
    doh_endpoints: list[str] | None = None,
    cache: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Queries DoH resolver with failover and client caching."""
    endpoints = doh_endpoints or DOH_ENDPOINTS
    cache_key = f"{name}:{rtype}:{cd}"
    if cache is not None and cache_key in cache:
        return cache[cache_key]

    params = {"name": name, "type": rtype, "cd": str(cd), "do": "1"}
    headers = {"Accept": "application/dns-json"}

    for endpoint in endpoints:
        try:
            with httpx.Client(timeout=timeout) as client:
                resp = client.get(endpoint, params=params, headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    if cache is not None:
                        cache[cache_key] = data
                    return data
        except Exception:
            continue
    return None


class DNSSECVerifier:
    """
    Validates RFC 8484 DNSSEC Authentic Data (AD) flag via DoH.
    Features automatic failover between Google and Cloudflare DoH resolvers.
    """

    def __init__(self, timeout: float = 3.0, doh_endpoints: list[str] | None = None):
        self.timeout = timeout
        self.doh_endpoints = doh_endpoints or DOH_ENDPOINTS
        self._cache: dict[str, Any] = {}

    def query_doh(self, name: str, rtype: str, cd: int = 0) -> dict[str, Any] | None:
        """Queries DoH resolver with failover and client caching."""
        return query_doh_record(
            name=name,
            rtype=rtype,
            cd=cd,
            timeout=self.timeout,
            doh_endpoints=self.doh_endpoints,
            cache=self._cache,
        )

    def verify_dnssec_ad(self, domain_or_url: str) -> dict[str, Any]:
        """Validates RFC 8484 DNSSEC Authentic Data (AD) flag."""
        domain = clean_hostname(domain_or_url)
        data = self.query_doh(name=domain, rtype="A", cd=0)

        if not data:
            return {
                "domain": domain,
                "dnssec_valid": False,
                "verdict": "INDETERMINATE",
                "ad_flag": False,
                "status_code": -1,
                "flags": ["DNSSEC_DOH_UNAVAILABLE"],
            }

        ad_flag = bool(data.get("AD", False))
        status_code = data.get("Status", -1)

        flags = []
        if status_code == 0:
            if ad_flag:
                flags.append("DNSSEC_AUTHENTIC_DATA_VERIFIED")
                verdict = "SECURE"
                dnssec_valid = True
            else:
                flags.append("DNSSEC_ZONE_UNVALIDATED")
                verdict = "INSECURE_STANDARD"
                dnssec_valid = False
        elif status_code == 2:
            flags.append("DNSSEC_BOGUS_VALIDATION_FAILURE")
            verdict = "BOGUS"
            dnssec_valid = False
        else:
            flags.append(f"DNSSEC_STATUS_{status_code}")
            verdict = "INDETERMINATE"
            dnssec_valid = False

        return {
            "domain": domain,
            "dnssec_valid": dnssec_valid,
            "verdict": verdict,
            "ad_flag": ad_flag,
            "status_code": status_code,
            "flags": flags,
        }
