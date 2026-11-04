"""
CertPulse Network Provenance & Cryptographic Verification Facade.
Backward-compatible shim re-exporting all symbols from the modular src.network package.
"""

from __future__ import annotations

from src.network import (
    AUTHORIZED_ENTERPRISE_CDNS,
    AUTHORIZED_VENDOR_ASNS,
    DOH_ENDPOINTS,
    GENERIC_CORP_TOKENS,
    KNOWN_CA_DOMAINS,
    KNOWN_CT_LOGS,
    KNOWN_DEFAULT_VENDOR_ASNS,
    KNOWN_SUSPICIOUS_ASNS,
    VENDOR_ASN_DIRECTORY,
    ASNRouteVerifier,
    ASNVerificationResult,
    CAAVerifier,
    DNSSecurityVerifier,
    DNSSECVerifier,
    NetworkProvenance,
    NetworkVerifier,
    TLSCertificateVerifier,
    clean_hostname,
    is_whitelisted_domain,
    match_san,
    query_doh_record,
    verify_network_provenance,
)

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
    "DNSSECVerifier",
    "DNSSecurityVerifier",
    "NetworkProvenance",
    "NetworkVerifier",
    "TLSCertificateVerifier",
    "clean_hostname",
    "is_whitelisted_domain",
    "match_san",
    "query_doh_record",
    "verify_network_provenance",
]
