"""
CertPulse Network Provenance: CAA Authorization Verification Engine.
Implements RFC 8659 Type 257 Certification Authority Authorization (CAA) queries
with domain tree climbing and Certificate Authority authorization matching.
"""

from __future__ import annotations

import ipaddress
from typing import Any

from src.network.asn import DOH_ENDPOINTS, clean_hostname
from src.network.dnssec import query_doh_record

KNOWN_CA_DOMAINS: dict[str, list[str]] = {
    "digicert": ["digicert.com", "symantec.com"],
    "let's encrypt": ["letsencrypt.org"],
    "google": ["pki.goog", "google.com"],
    "amazon": ["amazon.com", "amazonaws.com", "amazontrust.com"],
    "microsoft": ["microsoft.com"],
    "sectigo": ["sectigo.com", "comodoca.com"],
    "globalsign": ["globalsign.com"],
    "identrust": ["identrust.com"],
    "ssl.com": ["ssl.com"],
}


class CAAVerifier:
    """
    Validates RFC 8659 CAA records via DoH.
    Features RFC 8659 Section 3 domain tree climbing and CNAME resolution.
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

    def query_caa_records(self, domain_or_url: str) -> dict[str, Any]:
        """Queries Type 257 (CAA) records with RFC 8659 domain tree climbing."""
        hostname = clean_hostname(domain_or_url)
        try:
            ipaddress.ip_address(hostname)
            return {
                "hostname": hostname,
                "queried_domain": hostname,
                "has_caa": False,
                "records": [],
                "tree_climbed": False,
            }
        except ValueError:
            pass

        parts = hostname.split(".")
        candidates = []
        for i in range(len(parts) - 1):
            cand = ".".join(parts[i:])
            if "." in cand:
                candidates.append(cand)

        visited_cnames: set[str] = set()
        cname_hops = 0
        max_hops = 5

        for cand in candidates:
            curr_domain = cand
            while cname_hops < max_hops:
                data = self.query_doh(name=curr_domain, rtype="CAA", cd=0)
                if not data:
                    break

                answers = data.get("Answer", [])
                caa_entries = []
                cname_target = None

                for ans in answers:
                    if ans.get("type") == 257:
                        raw_data = ans.get("data", "")
                        tokens = raw_data.strip().split(maxsplit=2)
                        if len(tokens) >= 3:
                            try:
                                caa_entries.append({
                                    "flags": int(tokens[0]),
                                    "tag": tokens[1].lower(),
                                    "value": tokens[2].strip('"\''),
                                    "domain": curr_domain,
                                })
                            except ValueError:
                                pass
                    elif ans.get("type") == 5:
                        cname_target = ans.get("data", "").strip().rstrip(".")

                if caa_entries:
                    return {
                        "hostname": hostname,
                        "queried_domain": curr_domain,
                        "has_caa": True,
                        "records": caa_entries,
                        "tree_climbed": curr_domain != hostname,
                    }

                if cname_target and cname_target not in visited_cnames:
                    visited_cnames.add(cname_target)
                    curr_domain = cname_target
                    cname_hops += 1
                else:
                    break

        return {
            "hostname": hostname,
            "queried_domain": hostname,
            "has_caa": False,
            "records": [],
            "tree_climbed": False,
        }

    def verify_caa_authorization(self, domain_or_url: str, cert_issuer: str = "") -> dict[str, Any]:
        """Validates that cert_issuer is permitted by domain CAA policy."""
        caa_result = self.query_caa_records(domain_or_url)
        records = caa_result.get("records", [])

        if not records:
            return {
                "caa_authorized": True,
                "has_caa_records": False,
                "authorized_cas": [],
                "queried_domain": caa_result.get("queried_domain", clean_hostname(domain_or_url)),
                "flags": ["CAA_RECORDS_ABSENT_UNRESTRICTED"],
            }

        issue_cas = [r["value"].lower() for r in records if r["tag"] in ["issue", "issuewild"]]

        if not issue_cas:
            return {
                "caa_authorized": True,
                "has_caa_records": True,
                "authorized_cas": [],
                "queried_domain": caa_result["queried_domain"],
                "flags": ["CAA_CONTACT_OR_IODEF_ONLY"],
            }

        flags = [f"CAA_CONFIGURED_WITH_{len(issue_cas)}_ISSUERS"]

        if any(ca.strip() == ";" for ca in issue_cas):
            flags.append("CAA_ISSUE_PROHIBITED_LOCKOUT")
            return {
                "caa_authorized": False,
                "has_caa_records": True,
                "authorized_cas": issue_cas,
                "queried_domain": caa_result["queried_domain"],
                "flags": flags,
            }

        if not cert_issuer:
            flags.append("CAA_ISSUER_NOT_PROVIDED")
            return {
                "caa_authorized": True,
                "has_caa_records": True,
                "authorized_cas": issue_cas,
                "queried_domain": caa_result["queried_domain"],
                "flags": flags,
            }

        issuer_lower = cert_issuer.lower()
        matched = False
        for ca in issue_cas:
            ca_clean = ca.strip()
            if not ca_clean or ca_clean == ";":
                continue
            if ca_clean in issuer_lower:
                matched = True
                break
            ca_base = ca_clean.split(".")[0]
            if len(ca_base) >= 3 and ca_base in issuer_lower:
                matched = True
                break
            for ca_alias, doms in KNOWN_CA_DOMAINS.items():
                if (ca_clean in doms or any(d in ca_clean for d in doms)) and ca_alias in issuer_lower:
                    matched = True
                    break
            if matched:
                break

        if matched:
            flags.append("CAA_ISSUER_AUTHORIZED")
            caa_authorized = True
        else:
            flags.append("CAA_ISSUER_NOT_EXPLICITLY_LISTED")
            flags.append("CAA_ISSUER_UNAUTHORIZED")
            caa_authorized = False

        return {
            "caa_authorized": caa_authorized,
            "has_caa_records": True,
            "authorized_cas": issue_cas,
            "queried_domain": caa_result["queried_domain"],
            "flags": flags,
        }
