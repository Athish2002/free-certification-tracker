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

The CertPulse team takes security, user privacy, and data integrity seriously. If you identify a security vulnerability, prompt injection attack vector, SSRF bypass, or unexpected data disclosure, please disclose it responsibly.

### How to Report

- **Email**: Send a detailed vulnerability report to `security@certpulse.dev` (or open a confidential security advisory on GitHub via the **Security** tab).
- **Details to Include**:
  - Description of the vulnerability and its potential impact.
  - Step-by-step reproduction instructions or a minimal proof of concept (PoC).
  - Target URL, component, or file affected (e.g. collector, network verifier, VLM semantic gate).
  - Any proposed remediations.

### Scope and Invariants

1. **No Personally Identifiable Information (PII) Stored**:
   CertPulse tracks publicly available vendor campaigns, public community discussion URLs, and official exam portals. CertPulse does not collect, track, or persist PII, candidate identities, payment cards, or private credentials.

2. **No Scraped Authentication Credentials**:
   The CertPulse pipeline only inspects public unauthenticated web portals. No private login sessions, SSO tokens, or bypass credentials are stored in this repository.

3. **Autonomous Bot Etiquette**:
   CertPulse enforces vendor-level rate limiting, concurrency semaphores, standard bot identification headers (`User-Agent: CertPulse-Autonomous-Verifier/2.0`), and complies with vendor robots protocols and maintenance states.

### Response Timelines

- **Initial Acknowledgment**: Within 48 hours of receipt.
- **Triage & Assessment**: Within 5 business days.
- **Remediation & Advisory Release**: Coordinated with the reporter before public disclosure.
