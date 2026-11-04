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

CertPulse is created, architected, and maintained independently by a solo developer ([Athish R S](https://github.com/Athish2002)). Security, user privacy, and data integrity are taken seriously. If you identify a security vulnerability, SSRF bypass, prompt injection vector, or unexpected data disclosure, please disclose it responsibly.

### How to Report

To protect users and community members, **do not disclose vulnerabilities in public GitHub issues, discussions, or pull requests**.

Please report all security vulnerabilities confidentially through **GitHub Private Vulnerability Reporting**:
1. Navigate to the repository's [Security Advisories tab](https://github.com/Athish2002/free-certification-tracker/security/advisories).
2. Click **"Report a vulnerability"** to open a confidential advisory draft.
3. Provide details including:
   - Description of the vulnerability and its potential impact.
   - Minimal proof of concept (PoC) or reproduction steps.
   - Affected component or file (e.g. collector, network verifier, builders).
   - Any proposed remediations.

Reports submitted through GitHub Private Vulnerability Reporting alert the repository maintainer directly, keep the disclosure confidential until a fix is released, and allow collaborative security drafting in a temporary private fork.

---

### Scope and Invariants

1. **No Personally Identifiable Information (PII) Stored**:
   CertPulse tracks publicly available vendor campaigns, public community discussion URLs, and official exam portals. CertPulse does not collect, track, or persist PII, candidate identities, payment cards, or private credentials.

2. **No Scraped Authentication Credentials**:
   The CertPulse pipeline only inspects public unauthenticated web portals. No private login sessions, SSO tokens, or bypass credentials are stored in this repository.

3. **Autonomous Bot Etiquette**:
   CertPulse enforces vendor-level rate limiting, concurrency semaphores, standard bot identification headers (`User-Agent: CertPulse-Autonomous-Verifier/2.0`), and complies with vendor robots protocols and maintenance states.

---

### Solo Maintainer Response & Realistic Expectations

- **Single Maintainer**: CertPulse is an independent, non-commercial open-source project operated by a single person. There is **no full-time security team, commercial response rotation, or guaranteed response timeline (no formal 48-hour or 5-business-day response SLA)**.
- **Best-Effort Handling**: Vulnerability reports submitted via GitHub Private Vulnerability Reporting are reviewed on a **best-effort basis** around personal availability.
- **Coordinated Disclosure**: Valid vulnerabilities will be remediated and released through GitHub Advisories as swiftly as feasible before public disclosure.
