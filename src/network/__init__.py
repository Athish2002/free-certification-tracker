"""
CertPulse Network Provenance & Cryptographic Verification Package.
Modular package providing ASN/BGP route origin lookup, TLS SCT extraction,
DNSSEC AD flag validation, and RFC 8659 CAA policy verification.
"""

from __future__ import annotations

import datetime
from typing import Any

from cryptography import x509

from src.models import NetworkProvenance
from src.network.asn import (
    AUTHORIZED_ENTERPRISE_CDNS,
    AUTHORIZED_VENDOR_ASNS,
    DOH_ENDPOINTS,
    GENERIC_CORP_TOKENS,
    KNOWN_DEFAULT_VENDOR_ASNS,
    KNOWN_SUSPICIOUS_ASNS,
    VENDOR_ASN_DIRECTORY,
    ASNRouteVerifier,
    ASNVerificationResult,
    clean_hostname,
    is_whitelisted_domain,
)
from src.network.caa import (
    KNOWN_CA_DOMAINS,
    CAAVerifier,
)
from src.network.dnssec import (
    DNSSECVerifier,
    query_doh_record,
)
from src.network.tls import (
    KNOWN_CT_LOGS,
    TLSCertificateVerifier,
    match_san,
)


class DNSSecurityVerifier:
    """
    Validates DNSSEC Authentic Data (AD) flag and RFC 8659 CAA records via DoH.
    Unifies DNSSECVerifier and CAAVerifier with 100% backward-compatible interface.
    """

    def __init__(self, timeout: float = 3.0, doh_endpoints: list[str] | None = None):
        self.timeout = timeout
        self.doh_endpoints = doh_endpoints or DOH_ENDPOINTS
        self.dnssec_verifier = DNSSECVerifier(timeout=timeout, doh_endpoints=self.doh_endpoints)
        self.caa_verifier = CAAVerifier(timeout=timeout, doh_endpoints=self.doh_endpoints)

    def query_doh(self, name: str, rtype: str, cd: int = 0) -> dict[str, Any] | None:
        """Queries DoH resolver with failover and client caching."""
        return self.dnssec_verifier.query_doh(name, rtype, cd)

    def verify_dnssec_ad(self, domain_or_url: str) -> dict[str, Any]:
        """Validates RFC 8484 DNSSEC Authentic Data (AD) flag."""
        return self.dnssec_verifier.verify_dnssec_ad(domain_or_url)

    def query_caa_records(self, domain_or_url: str) -> dict[str, Any]:
        """Queries Type 257 (CAA) records with RFC 8659 domain tree climbing."""
        return self.caa_verifier.query_caa_records(domain_or_url)

    def verify_caa_authorization(self, domain_or_url: str, cert_issuer: str = "") -> dict[str, Any]:
        """Validates that cert_issuer is permitted by domain CAA policy."""
        return self.caa_verifier.verify_caa_authorization(domain_or_url, cert_issuer)

    def verify_dns_security(self, domain_or_url: str, cert_issuer: str = "") -> dict[str, Any]:
        """Aggregates DNSSEC AD validation and CAA record authorization."""
        dnssec = self.verify_dnssec_ad(domain_or_url)
        caa = self.verify_caa_authorization(domain_or_url, cert_issuer)

        return {
            "dnssec_valid": dnssec["dnssec_valid"],
            "dnssec_verdict": dnssec["verdict"],
            "caa_authorized": caa["caa_authorized"],
            "has_caa_records": caa["has_caa_records"],
            "authorized_cas": caa["authorized_cas"],
            "flags": dnssec["flags"] + caa["flags"],
        }


class NetworkVerifier:
    """
    Tier 1 Master Network Verifier.
    Integrates ASNRouteVerifier, TLSCertificateVerifier, and DNSSecurityVerifier
    to produce the canonical NetworkProvenance model contract.
    """

    def __init__(
        self,
        asn_verifier: ASNRouteVerifier | None = None,
        tls_verifier: TLSCertificateVerifier | None = None,
        dns_verifier: DNSSecurityVerifier | None = None,
        offline_mode: bool = False,
    ):
        self.offline_mode = offline_mode
        self.asn_verifier = asn_verifier or ASNRouteVerifier(offline_mode=offline_mode)
        self.tls_verifier = tls_verifier or TLSCertificateVerifier()
        self.dns_verifier = dns_verifier or DNSSecurityVerifier()

    def verify_network_provenance(
        self,
        url_or_host: str,
        platform: str = "",
        ip_override: str | None = None,
        mock_cert: x509.Certificate | None = None,
    ) -> NetworkProvenance:
        """
        Executes full Tier 1 Network Provenance audit:
        1. Resolves IP and queries Team Cymru ASN BGP prefix & RDAP org.
        2. Executes direct TLS handshake, extracts RFC 6962 SCTs & validates SAN.
        3. Queries DoH for DNSSEC AD flag and performs RFC 8659 CAA tree climbing.
        4. Returns validated Pydantic V2 NetworkProvenance contract.
        """
        now_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()
        hostname = clean_hostname(url_or_host)

        # 1. ASN Route verification
        asn_res = self.asn_verifier.verify_route_origin(
            hostname, platform=platform, ip_override=ip_override
        )

        # 2. TLS & CT verification
        if self.offline_mode and not mock_cert:
            tls_res = {
                "tls_verified": True,
                "tls_ct_verified": True,
                "sct_count": 2,
                "scts": [{"log_name": "Cloudflare Nimbus2026", "log_operator": "Cloudflare"}],
                "issuer": "CN=DigiCert Global Root G2",
                "flags": ["OFFLINE_TLS_CT_FALLBACK"],
            }
        else:
            tls_res = self.tls_verifier.verify_tls(hostname, mock_cert=mock_cert)

        # 3. DNSSEC & CAA verification
        if self.offline_mode:
            dns_res = {
                "dnssec_valid": False,
                "dnssec_verdict": "INSECURE_STANDARD",
                "caa_authorized": True,
                "authorized_cas": ["digicert.com"],
                "flags": ["OFFLINE_DNS_FALLBACK"],
            }
        else:
            dns_res = self.dns_verifier.verify_dns_security(
                hostname, cert_issuer=tls_res.get("issuer") or ""
            )

        # Combine flags and log operators
        security_flags = list(dict.fromkeys(
            asn_res.flags + tls_res.get("flags", []) + dns_res.get("flags", [])
        ))
        log_operators = list(dict.fromkeys(
            [sct.get("log_operator", "Unknown") for sct in tls_res.get("scts", [])]
        ))

        return NetworkProvenance(
            asn=asn_res.asn,
            asn_org=asn_res.asn_org,
            ip_address=asn_res.ip_address,
            is_vendor_infra=asn_res.is_vendor_infra,
            tls_ct_verified=tls_res.get("tls_ct_verified", True),
            sct_count=tls_res.get("sct_count", 0),
            dnssec_valid=dns_res.get("dnssec_valid", False),
            caa_authorized=dns_res.get("caa_authorized", True),
            verified_at_utc=now_utc,
            dnssec_verdict=dns_res.get("dnssec_verdict"),
            authorized_cas=dns_res.get("authorized_cas", []),
            sct_log_operators=log_operators,
            security_flags=security_flags,
        )


def verify_network_provenance(
    url_or_host: str,
    platform: str = "",
    asn_verifier: ASNRouteVerifier | None = None,
    tls_verifier: TLSCertificateVerifier | None = None,
    dns_verifier: DNSSecurityVerifier | None = None,
    offline_mode: bool = False,
) -> NetworkProvenance:
    """Convenience top-level entry point for Network Provenance verification."""
    verifier = NetworkVerifier(
        asn_verifier=asn_verifier,
        tls_verifier=tls_verifier,
        dns_verifier=dns_verifier,
        offline_mode=offline_mode,
    )
    return verifier.verify_network_provenance(url_or_host, platform=platform)


__all__ = [
    "AUTHORIZED_ENTERPRISE_CDNS",
    "AUTHORIZED_VENDOR_ASNS",
    "DOH_ENDPOINTS",
    "GENERIC_CORP_TOKENS",
    "KNOWN_CA_DOMAINS",
    "KNOWN_CT_LOGS",
    "KNOWN_DEFAULT_VENDOR_ASNS",
    "KNOWN_SUSPICIOUS_ASNS",
    "VENDOR_ASN_DIRECTORY",
    "ASNRouteVerifier",
    "ASNVerificationResult",
    "CAAVerifier",
    "DNSSecurityVerifier",
    "DNSSECVerifier",
    "NetworkProvenance",
    "NetworkVerifier",
    "TLSCertificateVerifier",
    "clean_hostname",
    "is_whitelisted_domain",
    "match_san",
    "query_doh_record",
    "verify_network_provenance",
]
