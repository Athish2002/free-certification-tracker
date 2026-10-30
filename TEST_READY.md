# TEST_READY — Security Vulnerabilities Remediation Suite (VULN-01 to VULN-09)

## Executive Summary
A comprehensive, independent, and adversarial security unit and regression test suite has been authored in `tests/test_vulnerability_remediations.py`. It comprises 33 distinct test cases covering all 9 identified security vulnerabilities across the codebase, adhering strictly to the specifications in `PROJECT.md` and the 3 Survey Explorer handoff reports.

## How to Run the Tests

### 1. Targeted Vulnerability Test Suite
Run the newly created vulnerability remediation test suite:
```powershell
pytest tests/test_vulnerability_remediations.py -v
```

### 2. Run by Vulnerability Identifier
To run tests for a specific vulnerability during milestone implementation:
```powershell
# VULN-01: DOM-based XSS Defense (M4)
pytest tests/test_vulnerability_remediations.py -k TestVuln01XssMitigation -v

# VULN-02: file:// Scheme Rejection & HTTPS Enforcement (M1)
pytest tests/test_vulnerability_remediations.py -k TestVuln02UrlSchemeEnforcement -v

# VULN-03: Sandboxed Chromium Launch Arguments (M1)
pytest tests/test_vulnerability_remediations.py -k TestVuln03ChromiumSandboxFlags -v

# VULN-04: News Feed Domain & Protocol Validation (M2)
pytest tests/test_vulnerability_remediations.py -k TestVuln04NewsDomainValidation -v

# VULN-05: defusedxml Entity Expansion Defense (M2)
pytest tests/test_vulnerability_remediations.py -k TestVuln05DefusedXmlHardening -v

# VULN-06: Principle of Least Privilege GitHub Actions CI (M2)
pytest tests/test_vulnerability_remediations.py -k TestVuln06CiWorkflowPermissions -v

# VULN-07: Candidate ID Regex & Screenshot Path Traversal Defense (M3)
pytest tests/test_vulnerability_remediations.py -k TestVuln07ScreenshotPathTraversal -v

# VULN-08: Atomic I/O Schema Pre-Flight Validation in main.py (M3)
pytest tests/test_vulnerability_remediations.py -k TestVuln08AtomicSchemaValidation -v

# VULN-09: Prompt Injection Delimiter Encapsulation & VLM Isolation (M3)
pytest tests/test_vulnerability_remediations.py -k TestVuln09VlmPromptInjectionIsolation -v
```

### 3. Full Regression Suite
Verify the entire test suite (252 baseline tests + 33 new security remediation tests = 285 total tests):
```powershell
pytest tests/ -q
```

---

## Vulnerability Coverage Matrix

| Vulnerability | Test Class | Target Component / File | Test Methods | Focus / Attack Vectors Tested |
|---|---|---|---|---|
| **VULN-01** | `TestVuln01XssMitigation` | `src/builders/client_bundle.py`<br>`src/builders/html_builder.py` | `test_client_bundle_defines_sanitization_helpers`<br>`test_client_bundle_sanitizer_logic_invariants`<br>`test_client_bundle_escapes_dynamic_fields_in_render_views`<br>`test_html_builder_closed_offers_escapes_js_attributes` | Client-side DOM XSS, `escapeHtml`, `escapeJs`, `sanitizeUrl`, single-quote JS event attribute injection (`openProofModal`). |
| **VULN-02** | `TestVuln02UrlSchemeEnforcement` | `src/dom_inspector.py`<br>`src/inspector.py` | `test_headless_dom_inspector_rejects_file_scheme`<br>`test_headless_dom_inspector_rejects_windows_file_scheme`<br>`test_headless_dom_inspector_rejects_non_https_protocols`<br>`test_source_code_has_no_file_scheme_authenticity_bypass` | Local file read via `file:///etc/passwd`, `file:///C:/Windows/win.ini`, unencrypted HTTP, javascript/data URIs, elimination of `is_local_file` bypass. |
| **VULN-03** | `TestVuln03ChromiumSandboxFlags` | `src/dom_inspector.py`<br>`src/constants.py` | `test_dom_inspector_playwright_launch_args_no_sandbox_flags`<br>`test_constants_playwright_launch_args_no_sandbox_flags`<br>`test_source_code_clean_of_insecure_sandbox_flags` | Removal of `--no-sandbox` and `--disable-setuid-sandbox` from `PLAYWRIGHT_LAUNCH_ARGS`. |
| **VULN-04** | `TestVuln04NewsDomainValidation` | `src/news_collector.py` | `test_news_collector_domain_and_protocol_validation_logic`<br>`test_news_collector_source_has_no_bidirectional_substring_check` | Strict HTTPS scheme, exact FQDN / authentic subdomain matching (`hostname == allowed or hostname.endswith('.' + allowed)`), rejection of substring spoofing (`evil-hashicorp.com`, `hashicorp.com.attacker.com`). |
| **VULN-05** | `TestVuln05DefusedXmlHardening` | `src/collector.py`<br>`src/news_collector.py`<br>`requirements.txt` | `test_requirements_contains_defusedxml`<br>`test_collector_uses_defusedxml`<br>`test_news_collector_uses_defusedxml`<br>`test_xml_entity_expansion_payload_rejected_by_collector_et`<br>`test_xml_entity_expansion_payload_rejected_by_news_collector_et` | Rejection of DTD entity expansion (Billion Laughs / quadratic blowup) with `DefusedXmlException`, verification of `defusedxml>=0.7.1` in `requirements.txt`. |
| **VULN-06** | `TestVuln06CiWorkflowPermissions` | `.github/workflows/tracker.yml` | `test_workflow_top_level_permissions_least_privilege`<br>`test_workflow_test_job_has_no_write_permissions`<br>`test_workflow_update_and_deploy_job_has_scoped_write_permissions`<br>`test_workflow_deploy_pages_job_has_scoped_pages_permissions` | Top-level permissions restricted to `contents: read`, write permissions restricted strictly to `update-and-deploy` (`contents: write`) and `deploy-pages` (`pages: write`, `id-token: write`). |
| **VULN-07** | `TestVuln07ScreenshotPathTraversal` | `src/collector.py` | `test_candidate_id_regex_invariant`<br>`test_vet_candidate_lead_rejects_path_traversal_ids`<br>`test_screenshot_path_containment_in_collector_source` | Rejection of candidate IDs with traversal sequences (`../../`, `\`, uppercase, spaces), enforcement of `^[a-z0-9-]+$` pattern and `relative_to` screenshot path containment. |
| **VULN-08** | `TestVuln08AtomicSchemaValidation` | `src/main.py`<br>`src/io_utils.py` | `test_main_imports_atomic_write_json`<br>`test_main_does_not_use_raw_file_replace_for_offers`<br>`test_atomic_write_json_pre_flight_blocks_invalid_schema`<br>`test_atomic_write_json_preserves_valid_schema` | Pre-flight validation against `data/schema.json` before disk commit, elimination of raw `open()` and `replace()` in `src/main.py`. |
| **VULN-09** | `TestVuln09VlmPromptInjectionIsolation` | `src/vlm/provider_adapters.py`<br>`src/vlm/models.py` | `test_vlm_user_prompt_encapsulates_untrusted_content_in_boundary_tags`<br>`test_vlm_user_prompt_neutralizes_closing_tag_breakout`<br>`test_gemini_payload_isolates_system_instruction`<br>`test_vlm_system_instruction_contains_injection_defense_guidance` | Wrapping external fields in `<untrusted_external_content>`, escaping closing tags to prevent breakout, isolating Gemini `system_instruction` at root level, and system instruction injection defense. |

---

## Test Execution Results (Pre-Remediation Baseline)

```
============================= test session starts =============================
platform win32 -- Python 3.14.7, pytest-9.1.1, pluggy-1.6.0
collected 33 items

- Passed (5): Invariant & mathematical property specification tests
  * test_news_collector_domain_and_protocol_validation_logic (VULN-04)
  * test_workflow_test_job_has_no_write_permissions (VULN-06)
  * test_candidate_id_regex_invariant (VULN-07)
  * test_atomic_write_json_pre_flight_blocks_invalid_schema (VULN-08)
  * test_atomic_write_json_preserves_valid_schema (VULN-08)

- Failed as Expected (28): Correctly identifying un-remediated vulnerabilities
  * VULN-01: 4 tests failed (missing escapeHtml/escapeJs/sanitizeUrl and onclick escaping)
  * VULN-02: 4 tests failed (file:// and non-HTTPS accepted, is_local_file bypass present)
  * VULN-03: 3 tests failed (--no-sandbox and --disable-setuid-sandbox still present)
  * VULN-04: 1 test failed (bidirectional substring check still present)
  * VULN-05: 5 tests failed (requirements.txt missing defusedxml, standard ET in use)
  * VULN-06: 3 tests failed (top-level contents: write, update/deploy un-scoped)
  * VULN-07: 2 tests failed (vet_candidate_lead does not reject ../ or check path containment)
  * VULN-08: 2 tests failed (main.py does not import/use atomic_write_json)
  * VULN-09: 4 tests failed (missing boundary tags, breakout unescaped, Gemini system_instruction not isolated)

Results: 28 failed, 5 passed in 16.33s
Baseline Suite Integrity: 252 passed in 18.68s (100% pass rate)
```

## Readiness Assessment
The test suite is verified and ready. Each milestone worker (M1, M2, M3, M4) can verify their implementations against their respective test class. Once all 9 vulnerability fixes are applied, all 33 tests in `tests/test_vulnerability_remediations.py` are expected to turn green, bringing the project total to 285 passing tests.
