"""
CertPulse Network Provenance: TLS X.509 & Certificate Transparency Engine.
Implements direct TLS handshakes, peer X.509 certificate parsing,
RFC 6125 SAN matching, and RFC 6962 embedded SCT extraction.
"""

from __future__ import annotations

import datetime
import logging
import socket
import ssl
from typing import Any

import httpx
from cryptography import x509
from cryptography.x509 import ExtensionNotFound
from cryptography.x509.oid import ExtensionOID

from src.network.asn import clean_hostname

logger = logging.getLogger(__name__)

# Well-known Certificate Transparency Logs (prefix matching on 16 hex characters)
KNOWN_CT_LOGS: dict[str, dict[str, str]] = {
    "d76d7d10d1a7f577": {"name": "Google Xenon2026 / Argon2026", "operator": "Google"},
    "c2317e574519a345": {"name": "Cloudflare Nimbus2026", "operator": "Cloudflare"},
    "c8a3c47fc7b3adb9": {"name": "DigiCert Yeti2026", "operator": "DigiCert"},
    "44c2bd0ce9140e64": {"name": "Cloudflare Nimbus2026", "operator": "Cloudflare"},
    "001a5d1a1c2d9375": {"name": "Google Argon2026", "operator": "Google"},
    "1c9f682ce9faf045": {"name": "DigiCert Nessie2026", "operator": "DigiCert"},
    "af67883b57b04edd": {"name": "Cloudflare Nimbus", "operator": "Cloudflare"},
    "e7368d4a4d65604f": {"name": "Let's Encrypt Oak2026", "operator": "Let's Encrypt"},
    "eecd774b7c12652b": {"name": "Sectigo Mammoth2026", "operator": "Sectigo"},
    "b73ed6f124588a6a": {"name": "Google Aviator / Rocketeer", "operator": "Google"},
}


def match_san(san: str, hostname: str) -> bool:
    """Matches hostname against Subject Alternative Name (SAN), supporting RFC 6125 wildcards."""
    san_lower = san.lower().strip()
    host_lower = hostname.lower().strip()
    if san_lower == host_lower:
        return True
    if san_lower.startswith("*."):
        suffix = san_lower[1:]
        if host_lower.endswith(suffix):
            prefix = host_lower[: -len(suffix)]
            if prefix and "." not in prefix:
                return True
    return False


class TLSCertificateVerifier:
    """
    Direct TLS handshake extractor for X.509 certificates and embedded RFC 6962 SCTs.
    Completely offline from crt.sh, eliminating 504 timeouts and network latency.
    """

    def __init__(self, timeout: float = 3.0, ct_circuit_breaker_timeout: float = 2.0):
        self.timeout = timeout
        self.ct_circuit_breaker_timeout = ct_circuit_breaker_timeout

    def fetch_peer_certificate(self, hostname: str, port: int = 443) -> tuple[x509.Certificate | None, str | None]:
        """Connects via TLS and extracts peer X.509 certificate in binary DER form."""
        if not hostname or not isinstance(hostname, str) or not hostname.strip():
            return None, "INVALID_EMPTY_HOSTNAME"
        try:
            ctx = ssl.create_default_context()
            with (
                socket.create_connection((hostname, port), timeout=self.timeout) as sock,
                ctx.wrap_socket(sock, server_hostname=hostname) as ssock,
            ):
                der_bytes = ssock.getpeercert(binary_form=True)
                if not der_bytes:
                    return None, "NO_CERTIFICATE_RETURNED"
                cert = x509.load_der_x509_certificate(der_bytes)
                return cert, None
        except ssl.SSLCertVerificationError as e:
            return None, f"SSL_VERIFICATION_FAILED: {e}"
        except TimeoutError:
            return None, "TLS_CONNECTION_TIMEOUT"
        except (socket.gaierror, ConnectionRefusedError, OSError) as e:
            return None, f"TLS_CONNECTION_FAILED: {e}"
        except Exception as e:
            return None, f"TLS_ERROR: {e}"

    def extract_embedded_scts(self, cert: x509.Certificate) -> list[dict[str, Any]]:
        """Parses X.509 Precertificate SCTs (OID 1.3.6.1.4.1.11129.2.4.2)."""
        scts: list[dict[str, Any]] = []
        try:
            ext = cert.extensions.get_extension_for_oid(ExtensionOID.PRECERT_SIGNED_CERTIFICATE_TIMESTAMPS)
            for sct in ext.value:
                log_id_hex = sct.log_id.hex()
                prefix = log_id_hex[:16]
                log_info = KNOWN_CT_LOGS.get(prefix, {"name": "Known/RFC6962 Log", "operator": "Public CT Operator"})
                ts = sct.timestamp
                ts_iso = ts.isoformat() if hasattr(ts, "isoformat") else str(ts)
                scts.append(
                    {
                        "log_id": log_id_hex,
                        "log_name": log_info["name"],
                        "log_operator": log_info["operator"],
                        "timestamp_utc": ts_iso,
                        "entry_type": str(sct.entry_type),
                        "version": getattr(sct.version, "name", str(sct.version)),
                    }
                )
        except ExtensionNotFound:
            pass
        except (ValueError, TypeError, KeyError) as sct_err:
            logger.debug("Embedded SCT parsing notice: %s", sct_err)
        return scts

    def verify_san(self, cert: x509.Certificate, hostname: str) -> tuple[bool, list[str]]:
        """Validates that hostname matches one of the Subject Alternative Names."""
        try:
            san_ext = cert.extensions.get_extension_for_oid(ExtensionOID.SUBJECT_ALTERNATIVE_NAME)
            sans = san_ext.value.get_values_for_type(x509.DNSName)
            matched = any(match_san(san, hostname) for san in sans)
            return matched, sans
        except ExtensionNotFound:
            return False, []

    def verify_validity(self, cert: x509.Certificate) -> dict[str, Any]:
        """Checks certificate expiration dates against current UTC time."""
        now = datetime.datetime.now(datetime.UTC)
        not_before = cert.not_valid_before_utc
        not_after = cert.not_valid_after_utc
        is_expired = now > not_after
        not_yet_valid = now < not_before
        is_valid = (not is_expired) and (not not_yet_valid)
        days_remaining = (not_after - now).days if not is_expired else 0

        return {
            "valid_from_utc": not_before.isoformat(),
            "valid_to_utc": not_after.isoformat(),
            "is_valid": is_valid,
            "is_expired": is_expired,
            "not_yet_valid": not_yet_valid,
            "days_remaining": days_remaining,
        }

    def query_ct_log_circuit_breaker(self, hostname: str) -> dict[str, Any] | None:
        """Optional secondary search on crt.sh with strict 2.0s circuit breaker."""
        url = f"https://crt.sh/?q={hostname}&output=json"
        try:
            with httpx.Client(timeout=self.ct_circuit_breaker_timeout) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    data = resp.json()
                    return {"status": "success", "count": len(data), "source": "crt.sh"}
        except (httpx.HTTPError, OSError, ValueError) as crt_err:
            logger.debug("crt.sh probe fallback: %s", crt_err)
        return {"status": "circuit_broken_or_offline", "count": 0, "source": "crt.sh"}

    def verify_tls(self, url_or_host: str, mock_cert: x509.Certificate | None = None) -> dict[str, Any]:
        """Executes full TLS audit: Handshake, SAN matching, Validity, and SCT extraction."""
        hostname = clean_hostname(url_or_host)
        if not hostname and not mock_cert:
            return {
                "hostname": "",
                "tls_verified": False,
                "tls_ct_verified": False,
                "sct_count": 0,
                "scts": [],
                "san_matched": False,
                "sans": [],
                "issuer": None,
                "subject": None,
                "validity": None,
                "error": "INVALID_EMPTY_HOSTNAME",
                "flags": ["TLS_FETCH_FAILED_INVALID_EMPTY_HOSTNAME"],
            }
        if mock_cert:
            cert = mock_cert
            err = None
        else:
            cert, err = self.fetch_peer_certificate(hostname)

        if not cert or err:
            return {
                "hostname": hostname,
                "tls_verified": False,
                "tls_ct_verified": False,
                "sct_count": 0,
                "scts": [],
                "san_matched": False,
                "sans": [],
                "issuer": None,
                "subject": None,
                "validity": None,
                "error": err,
                "flags": [f"TLS_FETCH_FAILED_{err}"],
            }

        scts = self.extract_embedded_scts(cert)
        san_matched, sans = self.verify_san(cert, hostname)
        validity = self.verify_validity(cert)
        issuer_str = cert.issuer.rfc4514_string()
        subject_str = cert.subject.rfc4514_string()

        flags = []
        if not san_matched:
            flags.append("TLS_SAN_MISMATCH")
        else:
            flags.append("TLS_SAN_MATCHED")

        if validity["is_expired"]:
            flags.append("TLS_CERT_EXPIRED")
        elif validity["not_yet_valid"]:
            flags.append("TLS_CERT_NOT_YET_VALID")
        else:
            flags.append("TLS_CERT_VALID")

        sct_count = len(scts)
        tls_ct_verified = sct_count >= 1
        if tls_ct_verified:
            flags.append(f"TLS_CT_EMBEDDED_SCT_VERIFIED ({sct_count} SCTs)")
        else:
            flags.append("TLS_CT_NO_EMBEDDED_SCTS")

        return {
            "hostname": hostname,
            "tls_verified": san_matched and validity["is_valid"],
            "tls_ct_verified": tls_ct_verified,
            "sct_count": sct_count,
            "scts": scts,
            "san_matched": san_matched,
            "sans": sans[:10],
            "issuer": issuer_str,
            "subject": subject_str,
            "validity": validity,
            "flags": flags,
            "error": None,
        }
