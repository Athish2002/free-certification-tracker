# Security Policy

CertPulse is an open-source, automated telemetry and verification system monitoring 100% free ($0.00 USD) cloud and technology certification vouchers and professional examination opportunities.

---

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 2.x     | :white_check_mark: |
| < 2.0   | :x:                |

---

## Reporting a Vulnerability

The CertPulse maintainers take security, user privacy, and data integrity seriously. If you identify a security vulnerability, SSRF bypass, prompt injection vector, or unexpected data disclosure, please disclose it responsibly.

### How to Report

To protect our users and maintainers, **do not disclose vulnerabilities in public GitHub issues, discussions, or pull requests**.

Please report all security vulnerabilities confidentially through **GitHub Private Vulnerability Reporting**:
1. Navigate to the repository's [Security Advisories tab](https://github.com/Athish2002/free-certification-tracker/security/advisories).
2. Click **"Report a vulnerability"** to open a confidential advisory draft.
3. Provide details including:
   - Description of the vulnerability and its potential impact.
   - Minimal proof of concept (PoC) or reproduction steps.
   - Affected component or file (e.g. collector, network verifier, builders).
   - Any proposed remediations.

Reports submitted through GitHub Private Vulnerability Reporting alert repository maintainers directly, keep the disclosure confidential until a patch is released, and allow collaborative security drafting in a temporary private fork.

---

### Scope and Invariants

1. **No Personally Identifiable Information (PII) Stored**:
   CertPulse tracks publicly available vendor campaigns, public community discussion URLs, and official exam portals. CertPulse does not collect, track, or persist PII, candidate identities, payment cards, or private credentials.

2. **No Scraped Authentication Credentials**:
   The CertPulse pipeline only inspects public unauthenticated web portals. No private login sessions, SSO tokens, or bypass credentials are stored in this repository.

3. **Autonomous Bot Etiquette**:
   CertPulse enforces vendor-level rate limiting, concurrency semaphores, standard bot identification headers (`User-Agent: CertPulse-Autonomous-Verifier/2.0`), and complies with vendor robots protocols and maintenance states.

---

### Response Timelines

- **Initial Acknowledgment**: Within 48 hours of receipt.
- **Triage & Assessment**: Within 5 business days.
- **Remediation & Advisory Release**: Coordinated with the reporter before public disclosure.
