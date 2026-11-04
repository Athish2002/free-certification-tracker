"""
Unit and invariant tests for:
1. Option 1A: Modular src.network package & backward-compatible src.network_verifier facade.
2. Option 3A: Flapping status 2-strike hysteresis & hard-closure fast-path state machine invariants.
"""

from __future__ import annotations

import pytest

from src.models import Offer
from src.main import apply_self_healing
from src.network import (
    AUTHORIZED_ENTERPRISE_CDNS,
    AUTHORIZED_VENDOR_ASNS,
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
    verify_network_provenance,
)
import src.network_verifier as legacy_facade


# ==============================================================================
# 1. Option 1A: Modular Network Package & Facade Invariants
# ==============================================================================

class TestModularNetworkPackage:
    """Verifies that src.network modules and src.network_verifier facade export consistent symbols."""

    def test_facade_reexports_all_symbols(self):
        symbols = [
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
            "verify_network_provenance",
        ]
        for sym in symbols:
            assert hasattr(legacy_facade, sym), f"Facade missing symbol: {sym}"
            assert getattr(legacy_facade, sym) is globals().get(sym, getattr(legacy_facade, sym))

    def test_clean_hostname_extraction(self):
        assert clean_hostname("https://learn.microsoft.com/en-us/credentials") == "learn.microsoft.com"
        assert clean_hostname("http://aws.amazon.com:443/training") == "aws.amazon.com"
        assert clean_hostname("150.171.109.131") == "150.171.109.131"
        assert clean_hostname("") == ""

    def test_match_san_wildcards(self):
        assert match_san("*.microsoft.com", "learn.microsoft.com") is True
        assert match_san("*.microsoft.com", "sub.learn.microsoft.com") is False
        assert match_san("azure.com", "azure.com") is True
        assert match_san("azure.com", "other.com") is False

    def test_asn_route_verifier_offline(self):
        verifier = ASNRouteVerifier(offline_mode=True)
        res = verifier.verify_route_origin("learn.microsoft.com", platform="Microsoft Azure")
        assert res.is_vendor_infra is True
        assert res.asn in AUTHORIZED_VENDOR_ASNS["Microsoft Azure"]
        assert res.lookup_method in ["offline_whitelist_fallback", "offline_fallback", "doh_cymru"]

    def test_network_verifier_orchestration_offline(self):
        verifier = NetworkVerifier(offline_mode=True)
        prov = verifier.verify_network_provenance("https://learn.microsoft.com/credentials", platform="Microsoft Azure")
        assert isinstance(prov, NetworkProvenance)
        assert prov.is_vendor_infra is True
        assert prov.tls_ct_verified is True


# ==============================================================================
# 2. Option 3A: Flapping Status Hysteresis & State Machine Invariants
# ==============================================================================

class TestFlappingStatusHysteresis:
    """Verifies 2-strike hysteresis with hard-closure fast-path."""

    def test_offer_model_contains_consecutive_transient_failures(self):
        offer = Offer(
            id="test-hysteresis-model",
            title="Test Hysteresis Model Certification",
            platform="Microsoft Azure",
            category="Cloud",
            certification_name="AZ-900",
            credential_tier="proctored_exam",
            url="https://learn.microsoft.com/azure",
        )
        assert hasattr(offer, "consecutive_transient_failures")
        assert offer.consecutive_transient_failures == 0

    def test_strike_1_transient_outage_preserves_active_status(self):
        """Strike 1 transient 503/timeout preserves Active and increments counter."""
        offer = {
            "id": "azure-ai-fundamentals",
            "title": "Microsoft Certified: Azure AI Fundamentals",
            "status": "Active",
            "consecutive_transient_failures": 0,
        }
        inspection_res = {
            "status": "Server Error",
            "http_status": 503,
            "reason": "HTTP 503 Service Unavailable (Gateway Timeout)",
            "maintenance_detected": False,
            "zero_dollar_confirmed": False,
        }

        updated = apply_self_healing(offer, inspection_res)
        assert updated["status"] == "Active", "Strike 1 transient outage must preserve Active status"
        assert updated["consecutive_transient_failures"] == 1
        assert updated.get("in_grace_period") is True
        assert "Active (Warning: Transient Outage Strike 1)" in updated["inspection_notes"]

    def test_strike_2_transient_outage_demotes_status(self):
        """Strike 2 consecutive transient outage demotes from Active to Review Needed."""
        offer = {
            "id": "azure-ai-fundamentals",
            "title": "Microsoft Certified: Azure AI Fundamentals",
            "status": "Active",
            "consecutive_transient_failures": 1,
            "in_grace_period": True,
        }
        inspection_res = {
            "status": "Server Error",
            "http_status": 502,
            "reason": "HTTP 502 Bad Gateway",
            "maintenance_detected": False,
            "zero_dollar_confirmed": False,
        }

        updated = apply_self_healing(offer, inspection_res)
        assert updated["status"] in ["Review Needed", "Server Error"], "Strike 2 must demote status"
        assert updated["consecutive_transient_failures"] == 2
        assert "in_grace_period" not in updated

    def test_healthy_check_resets_consecutive_transient_failures(self):
        """Healthy 200 OK + confirmed $0.00 terms resets transient failure strike counter to 0."""
        offer = {
            "id": "azure-ai-fundamentals",
            "title": "Microsoft Certified: Azure AI Fundamentals",
            "status": "Active",
            "consecutive_transient_failures": 1,
            "in_grace_period": True,
        }
        inspection_res = {
            "status": "Active",
            "http_status": 200,
            "reason": "DOM confirmed $0.00 cart balance and live registration",
            "zero_dollar_confirmed": True,
            "maintenance_detected": False,
            "paid_catalog_detected": False,
        }

        updated = apply_self_healing(offer, inspection_res)
        assert updated["status"] == "Active"
        assert updated["consecutive_transient_failures"] == 0
        assert "in_grace_period" not in updated

    def test_hard_closure_fast_path_strike_1(self):
        """Affirmative hard closure (capacity reached / registrations closed / voucher expired) demotes immediately on Strike 1."""
        offer = {
            "id": "salesforce-ai-associate",
            "title": "Salesforce AI Associate Certification",
            "status": "Active",
            "consecutive_transient_failures": 0,
        }
        inspection_res = {
            "status": "Registrations Closed",
            "http_status": 200,
            "reason": "Capacity Invariant: Detected capacity limit reached / cohort full ('capacity has been reached')",
            "zero_dollar_confirmed": False,
            "maintenance_detected": False,
        }

        updated = apply_self_healing(offer, inspection_res)
        assert updated["status"] == "Registrations Closed", "Hard-closure must demote immediately on Strike 1"
        assert updated["consecutive_transient_failures"] == 0
        assert "in_grace_period" not in updated

    def test_coupon_expired_hard_closure_fast_path(self):
        """Expired promo coupon code demotes immediately to Expired on Strike 1."""
        offer = {
            "id": "oracle-cloud-infrastructure",
            "title": "Oracle OCI Certified Foundations Associate",
            "status": "Active",
            "consecutive_transient_failures": 0,
        }
        inspection_res = {
            "status": "Expired",
            "http_status": 200,
            "reason": "Coupon Invariant: Detected expired promo/coupon code ('promo code has expired')",
            "zero_dollar_confirmed": False,
        }

        updated = apply_self_healing(offer, inspection_res)
        assert updated["status"] == "Expired", "Coupon expiration must demote to Expired on Strike 1"
        assert updated["consecutive_transient_failures"] == 0
        assert "in_grace_period" not in updated


# ==============================================================================
# 3. Concurrency, Timeout Isolation & DoH Fallback Resilience
# ==============================================================================

class TestConcurrencyAndResilience:
    """Verifies timeout isolation, DoH resolver failover, and thread-safety under load."""

    def test_doh_primary_failover_to_secondary(self, respx_mock):
        """When primary DoH resolver (Google) fails, automatically fails over to Cloudflare."""
        import httpx
        # Primary fails with 500
        respx_mock.get("https://dns.google/resolve").mock(return_value=httpx.Response(500))
        # Secondary succeeds with valid DNSSEC AD=True
        respx_mock.get("https://cloudflare-dns.com/dns-query").mock(
            return_value=httpx.Response(200, json={
                "Status": 0,
                "AD": True,
                "Answer": [{"name": "example.com", "type": 1, "data": "93.184.216.34"}]
            })
        )

        verifier = DNSSECVerifier(timeout=1.0)
        res = verifier.verify_dnssec_ad("example.com")
        assert res["dnssec_valid"] is True
        assert res["verdict"] == "SECURE"
        assert "DNSSEC_AUTHENTIC_DATA_VERIFIED" in res["flags"]

    def test_doh_all_endpoints_fail_graceful_degradation(self, respx_mock):
        """When all DoH resolvers time out, returns indeterminate verdict without raising."""
        import httpx
        respx_mock.get("https://dns.google/resolve").mock(side_effect=httpx.ConnectTimeout("timeout"))
        respx_mock.get("https://cloudflare-dns.com/dns-query").mock(side_effect=httpx.ConnectTimeout("timeout"))

        verifier = DNSSECVerifier(timeout=0.1)
        res = verifier.verify_dnssec_ad("example.com")
        assert res["dnssec_valid"] is False
        assert res["verdict"] == "INDETERMINATE"
        assert "DNSSEC_DOH_UNAVAILABLE" in res["flags"]

    def test_asn_route_cymru_fail_rdap_fallback(self, respx_mock):
        """When Team Cymru DoH TXT query fails, falls back to ARIN RDAP HTTPS."""
        import httpx
        # DoH A query for learn.microsoft.com succeeds
        respx_mock.get("https://dns.google/resolve", params__contains={"type": "A"}).mock(
            return_value=httpx.Response(200, json={
                "Status": 0,
                "Answer": [{"name": "learn.microsoft.com", "type": 1, "data": "150.171.109.131"}]
            })
        )
        # Cymru DoH TXT fails
        respx_mock.get("https://dns.google/resolve", params__contains={"type": "TXT"}).mock(return_value=httpx.Response(500))
        respx_mock.get("https://cloudflare-dns.com/dns-query", params__contains={"type": "TXT"}).mock(return_value=httpx.Response(500))
        # ARIN RDAP succeeds
        respx_mock.get("https://rdap.arin.net/registry/ip/150.171.109.131").mock(
            return_value=httpx.Response(200, json={
                "name": "MSFT-CORP",
                "handle": "NET-150-171-0-0-1",
                "entities": [{"vcardArray": ["vcard", [["fn", {}, "text", "Microsoft Corporation"]]]}]
            })
        )

        verifier = ASNRouteVerifier(timeout=1.0)
        res = verifier.verify_route_origin("learn.microsoft.com", platform="Microsoft Azure")
        assert res.lookup_method == "rdap"
        assert res.asn == 8075
        assert "Microsoft" in res.asn_org
        assert res.is_vendor_infra is True

    def test_multi_threaded_network_verifier_thread_safety(self):
        """Verifies concurrent multi-threaded execution across 16 worker threads."""
        import concurrent.futures
        verifier = NetworkVerifier(offline_mode=True)
        hosts = [
            ("https://learn.microsoft.com/credentials", "Microsoft Azure"),
            ("https://aws.amazon.com/certification", "Amazon Web Services"),
            ("https://cloud.google.com/certification", "Google Cloud"),
            ("https://education.oracle.com", "Oracle Cloud"),
            ("https://www.cisco.com/training", "Cisco"),
        ] * 10  # 50 total concurrent requests

        def worker(item):
            url, plat = item
            return verifier.verify_network_provenance(url, platform=plat)

        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
            results = list(pool.map(worker, hosts))

        assert len(results) == 50
        assert all(isinstance(r, NetworkProvenance) for r in results)
        assert all(r.is_vendor_infra for r in results)

    def test_tls_timeout_isolation_never_raises(self):
        """TLS handshake timeout produces structured error contract, never raising uncaught exception."""
        verifier = TLSCertificateVerifier(timeout=0.001)
        # Unroutable RFC 5737 TEST-NET address guaranteed to time out
        res = verifier.verify_tls("192.0.2.1")
        assert res["tls_verified"] is False
        assert res["error"] is not None
        assert any("TLS_FETCH_FAILED" in f for f in res["flags"])
