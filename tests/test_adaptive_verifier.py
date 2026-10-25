"""
Unit and Invariant Tests for the Adaptive Verification Engine (src/adaptive_verifier.py).
Ensures SSRF defense, dual-phase target resolution, platform cluster classification,
redirect degradation detection, and Proof Quality Scoring (PQS).
"""

import pytest
from src.adaptive_verifier import (
    PlatformCluster,
    validate_target_url,
    classify_platform_cluster,
    resolve_dual_phase_targets,
    get_pre_navigation_storage,
    audit_redirect_degradation,
    calculate_proof_quality_score,
)


class TestSecurityInvariants:
    def test_ssrf_rejects_localhost_and_loopback(self):
        blocked_hosts = [
            "http://127.0.0.1/admin",
            "http://localhost:8080/token",
            "http://[::1]/secret",
            "http://169.254.169.254/latest/meta-data/",
            "http://metadata.google.internal/computeMetadata/v1/",
        ]
        for url in blocked_hosts:
            res = validate_target_url(url, allow_local_file=True)
            assert not res.is_safe, f"Expected SSRF block for {url}"
            assert "blocked" in res.reason.lower() or "internal" in res.reason.lower()

    def test_ssrf_rejects_private_subnets(self):
        private_ips = [
            "http://10.0.0.1/path",
            "http://192.168.1.50/exam",
            "http://172.16.0.5/api",
        ]
        for url in private_ips:
            res = validate_target_url(url, allow_local_file=True)
            assert not res.is_safe, f"Expected private subnet block for {url}"

    def test_rejects_dangerous_uri_schemes(self):
        dangerous_urls = [
            "javascript:alert(1)",
            "data:text/html,<script>window.location='http://attacker.com'</script>",
            "mailto:security@certpulse.dev",
            "ftp://files.example.com/dump.tar",
        ]
        for url in dangerous_urls:
            res = validate_target_url(url, allow_local_file=True)
            assert not res.is_safe
            assert "unsupported" in res.reason.lower() or "dangerous" in res.reason.lower()

    def test_accepts_valid_https_and_local_fixtures(self):
        valid_urls = [
            "https://mylearn.oracle.com/ou/learning-path/ai-foundations/127177",
            "https://learn.microsoft.com/en-us/credentials/applied-skills/",
            "https://aws.amazon.com/education/awseducate/",
            "file:///C:/Users/test/fixture.html",
        ]
        for url in valid_urls:
            res = validate_target_url(url, allow_local_file=True)
            assert res.is_safe, f"Expected safe for {url}, got: {res.reason}"


class TestClusterClassification:
    def test_classifies_cluster_a_lms(self):
        lms_cases = [
            ("Oracle Cloud", "https://mylearn.oracle.com/ou/learning-path/127177"),
            ("Microsoft Azure", "https://learn.microsoft.com/en-us/credentials/applied-skills/"),
            ("Snowflake", "https://learn.snowflake.com/en/pages/hands-on-essentials-track/"),
            ("Databricks", "https://www.databricks.com/learn/training/certification"),
            ("MongoDB", "https://learn.mongodb.com/pages/certification"),
        ]
        for platform, url in lms_cases:
            prof = classify_platform_cluster(platform, url)
            assert prof.cluster == PlatformCluster.CLUSTER_A_LMS
            assert prof.code == "ENTERPRISE_LMS"
            assert "networkidle" in prof.wait_condition

    def test_classifies_cluster_b_scholarships(self):
        scholarship_cases = [
            ("Linux Foundation", "https://www.linuxfoundation.org/about/lift-scholarships"),
            ("CNCF", "https://www.cncf.io/scholarships/"),
            ("ISC2", "https://www.isc2.org/landing/1mcc"),
            ("GitHub", "https://education.github.com/pack"),
        ]
        for platform, url in scholarship_cases:
            prof = classify_platform_cluster(platform, url)
            assert prof.cluster == PlatformCluster.CLUSTER_B_SCHOLARSHIP
            assert prof.code == "SCHOLARSHIP"
            assert "capacity" in prof.assertion_focus.lower()

    def test_classifies_cluster_c_ce_community(self):
        ce_cases = [
            ("Cisco", "https://learningnetwork.cisco.com/s/topic/0TO6e000002e4QmGAI/rev-up-to-recert-community"),
        ]
        for platform, url in ce_cases:
            prof = classify_platform_cluster(platform, url)
            assert prof.cluster == PlatformCluster.CLUSTER_C_CE_COMMUNITY
            assert prof.code == "RECERT_COMMUNITY"

    def test_classifies_cluster_d_event_wave(self):
        event_cases = [
            ("Microsoft Azure", "https://learn.microsoft.com/en-us/training/challenges"),
            ("GitHub", "https://githubuniverse.com/"),
        ]
        for platform, url in event_cases:
            prof = classify_platform_cluster(platform, url)
            assert prof.cluster == PlatformCluster.CLUSTER_D_EVENT_WAVE
            assert prof.code == "EVENT_WAVE"


class TestDualPhaseTargetResolution:
    def test_resolves_deep_claim_over_marketing_root(self):
        offer = {
            "id": "oracle-oci-free-cert",
            "url": "https://mylearn.oracle.com/ou/learning-path/become-an-oci-ai-foundations-associate-2023/127177",
            "direct_verified_url": "https://www.oracle.com/education/certification/",
            "verified_vendor_url": "https://www.oracle.com/education/certification/",
        }
        targets = resolve_dual_phase_targets(offer)
        # Deep claim URL must be chosen as the primary browser navigation target
        assert targets.primary_nav_target == "https://mylearn.oracle.com/ou/learning-path/become-an-oci-ai-foundations-associate-2023/127177"
        # Authority root must preserve the corporate marketing root
        assert targets.authority_root_url == "https://www.oracle.com/education/certification/"
        # Divergence must be detected
        assert targets.is_divergent is True

    def test_handles_aligned_targets(self):
        offer = {
            "id": "ms-applied-skills",
            "url": "https://learn.microsoft.com/en-us/credentials/applied-skills/",
            "direct_verified_url": "https://learn.microsoft.com/en-us/credentials/applied-skills/",
        }
        targets = resolve_dual_phase_targets(offer)
        assert targets.primary_nav_target == offer["url"]
        assert targets.is_divergent is False


class TestPreNavigationStorage:
    def test_provides_oracle_cookie_consent_preset(self):
        storage = get_pre_navigation_storage("https://mylearn.oracle.com/ou/path")
        assert "local_storage" in storage
        assert storage["local_storage"]["OptanonAlertBoxClosed"]
        assert storage["local_storage"]["oracle_cookie_consent"] == "true"
        assert storage["locale"] == "en-US"

    def test_provides_microsoft_preset(self):
        storage = get_pre_navigation_storage("https://learn.microsoft.com/en-us/credentials")
        assert storage["local_storage"]["MS_COOKIE_CONSENT"] == "accepted"


class TestRedirectDegradationAudit:
    def test_detects_degradation_to_generic_hub(self):
        is_deg, reason, score = audit_redirect_degradation(
            "https://mylearn.oracle.com/ou/learning-path/oci-genai/136227",
            "https://mylearn.oracle.com/ou"
        )
        assert is_deg is True
        assert score == 0.0
        assert "degraded" in reason.lower()

    def test_detects_path_depth_collapse(self):
        is_deg, reason, score = audit_redirect_degradation(
            "https://www.linuxfoundation.org/about/lift-scholarships/2024",
            "https://www.linuxfoundation.org/"
        )
        assert is_deg is True
        assert score <= 10.0

    def test_healthy_redirect_across_trusted_subdomain(self):
        is_deg, reason, score = audit_redirect_degradation(
            "https://cloud.google.com/innovators",
            "https://go.cloudskillsboost.google/arcade"
        )
        assert is_deg is False
        assert score >= 80.0


class TestProofQualityScoring:
    def test_high_confidence_score(self):
        res = calculate_proof_quality_score(url_score=100.0, dom_score=100.0, visual_score=100.0, corroboration_score=100.0)
        assert res.score == 100.0
        assert res.tier == "HIGH_CONFIDENCE_VERIFIED"

    def test_moderate_confidence_sso_gate(self):
        # Good URL, moderate DOM token (SSO gate), standard screenshot and corroboration
        res = calculate_proof_quality_score(url_score=80.0, dom_score=60.0, visual_score=70.0, corroboration_score=80.0)
        assert 60.0 <= res.score < 85.0
        assert res.tier == "MODERATE_CONFIDENCE_SSO_GATE"

    def test_low_confidence_review_needed(self):
        # Bounced redirect, no DOM free token
        res = calculate_proof_quality_score(url_score=0.0, dom_score=20.0, visual_score=50.0, corroboration_score=30.0)
        assert res.score < 60.0
        assert res.tier == "LOW_CONFIDENCE_REVIEW_NEEDED"
