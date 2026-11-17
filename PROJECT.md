# Project: CertPulse

CertPulse tracks free and discounted certification offers. A scheduled pipeline loads each tracked vendor page, records whether it is reachable and whether it shows a closure notice, and regenerates `README.md` and `docs/index.html` from the data files.

This document describes what is in the repository today. An earlier version described a planned "7-tier verification architecture", including modules that were never written. Those sections have been removed.

## What the pipeline does

1. **Collect** (`src/collector.py`, `src/news_collector.py`): pulls candidate leads from public Reddit search feeds and vendor channels, and news items from official vendor RSS/Atom feeds. Candidates are filtered by a vendor-domain allow-list before they are considered.
2. **Inspect** (`src/inspector.py`, `src/dom_inspector.py`): a headless Chromium (Playwright) loads each offer URL and screens the rendered page for error pages, soft-404s, redirects, maintenance banners and closure wording. It also looks for words such as "free" or "badge". This is a keyword check on the page text. It does not confirm a price. A viewport screenshot is saved to `docs/screenshots/<id>.png` when the capture succeeds.
3. **Apply policy notes** (`src/truth_oracle.py`): attaches the hand-maintained policy note for each offer from `data/curated_policies.json` (co-pays, eligibility, enrollment windows) and enforces its status. Each note has a `review_due_utc` date. When that date has passed and the note says "Active", the offer is set to "Review Needed" until a maintainer re-checks it. A note that says "Active" must also record a quoted source (`evidence_url`, `evidence_quote`, `reviewed_on`, `reviewed_by`); without all four the offer is set to "Review Needed".
4. **Watch program pages** (`src/watchlist.py`, `data/watchlist.json`): loads a fixed list of vendor pages where exam offers get announced, keeps the lines that mention offer wording, and compares them with the previous run (`data/watchlist_state.json`). Changes are logged to `data/watchlist_changes.json`, and the `watch-alerts` workflow job opens an issue per changed page (`scripts/open_watch_issues.py`). A change means the wording moved, not that an offer exists.
5. **Build** (`src/builders/`): generates `README.md`, `docs/index.html` and `data/summary.json` from `data/offers.json` and `data/news.json`.

The workflow in `.github/workflows/tracker.yml` runs this twice a day (cron `0 0,12 * * *`) and commits the changed data and generated files.

## What it does not do

- It does not register for an exam, apply a voucher, or run a checkout. No price is confirmed by purchase. `src/cart_emulator.py` only classifies an offer from its own hand-written metadata.
- It does not hold or publish voucher codes.
- The policy notes are not derived from vendor pages automatically. They are written by the maintainer and can be out of date.
- The historical archive entries were written by hand. No screenshot or archive capture of the original campaign pages is stored.

## Supporting checks

These modules exist and have tests. They add signals to an offer record; none of them establishes that an offer is free.

| Module | What it does |
| --- | --- |
| `src/authenticity.py` | Vendor-domain allow-list, HTTPS and redirect-chain checks, scam-keyword screening of URLs |
| `src/network/` (`asn.py`, `tls.py`, `dnssec.py`, `caa.py`), `src/network_verifier.py` | ASN lookup, TLS certificate and SCT parsing, DNSSEC AD flag and CAA record queries over DNS-over-HTTPS |
| `src/temporal_analyzer.py` | Wayback Machine CDX lookups for domain age and past snapshots, cached in `data/temporal_longevity_cache.json` |
| `src/visual_hasher.py` | Perceptual hashing of screenshots; used to detect blank captures and skip unchanged ones |
| `src/vlm/`, `src/vlm_engine.py` | OCR (if Tesseract or EasyOCR is installed) and an optional multimodal model call. The CI workflow sets no model API keys, so scheduled runs use the deterministic heuristic fallback |
| `src/adaptive_verifier.py`, `src/accessibility_scanner.py` | Page-structure heuristics used by the inspector |
| `src/audit_ledger.py` | Appends SHA-256 digests of the rendered DOM and screenshot to `data/audit_log.jsonl`. The log is append-only by convention; it is a plain file in the repository and is not tamper-proof |

## Not implemented

The earlier version of this document listed these as part of the architecture. They do not exist in the repository:

- `src/cross_corroborator.py` (cross-checking offers against vendor feeds and Reddit reports). Reddit is only used as a source of candidate leads in `src/collector.py`.
- `src/checkout_sandbox.py` (a sandboxed checkout that asserts a $0.00 cart total).
- The test files `tests/test_network_provenance.py`, `tests/test_temporal_longevity.py`, `tests/test_visual_multimodal.py`, `tests/test_corroboration_cart.py`, `tests/test_audit_ledger.py` and `tests/test_e2e_verification.py`. The tests that do exist are listed below.

## Code layout

```
src/
├── main.py                  # Pipeline entry point (python -m src.main; --dry-run skips network work)
├── collector.py             # Candidate leads from Reddit search feeds and vendor channels
├── news_collector.py        # Vendor RSS/Atom news ingestion
├── inspector.py             # URL inspection runner, status transitions
├── dom_inspector.py         # Headless page rendering, closure/keyword checks, screenshots
├── truth_oracle.py          # Hand-maintained policy notes, status enforcement, review-date rule
├── authenticity.py          # Domain allow-list and URL safety checks
├── cart_emulator.py         # Classifies an offer from its own metadata (no checkout)
├── enrich_redemption.py     # One-off script that writes hand-written redemption guidance
├── audit_ledger.py          # SHA-256 digests appended to data/audit_log.jsonl
├── temporal_analyzer.py     # Wayback CDX lookups
├── visual_hasher.py         # Perceptual hashing of screenshots
├── adaptive_verifier.py     # Page-structure heuristics
├── accessibility_scanner.py # Interactive-element scan of a rendered page
├── network_verifier.py      # Facade over src/network/
├── network/                 # asn.py, tls.py, dnssec.py, caa.py
├── vlm_engine.py            # Facade over src/vlm/
├── vlm/                     # models.py, ocr_engine.py, heuristic.py, provider_adapters.py
├── models.py                # Pydantic models for offers and proofs
├── constants.py             # Shared headers, patterns and keyword lists
├── io_utils.py              # Atomic JSON writes with schema validation
├── builder.py               # Backward-compatible facade over src/builders/
└── builders/                # readme_builder.py, html_builder.py, client_bundle.py, theme_engine.py

data/
├── offers.json              # Tracked offers (active, triage and historical)
├── curated_policies.json    # Hand-maintained policy notes with review dates
├── schema.json              # JSON Schema for offers.json
├── candidates.json          # Queue of candidate leads
├── news.json, news_schema.json
├── summary.json             # Generated counts
├── reference_badges.json    # Reference hashes for badge matching
├── audit_log.jsonl          # Inspection digests (plus an archived .gz)
└── temporal_longevity_cache.json

docs/
├── index.html               # Generated dashboard (GitHub Pages)
├── screenshots/             # Real captures of vendor pages; offers without one have none
└── DEEP_DIVE_PAST_FAILURES_AND_ARCHITECTURE_RFC.md

scripts/                     # audit_authenticity.py, check_ci.py, dry_run_dual_phase_evaluation.py, validate_ci_workflow.py

tests/
├── test_invariants.py, test_models.py, test_builders.py, test_io_utils.py
├── test_truth_oracle.py, test_oracle_stress.py, test_boost_all_improvements.py
├── test_integration_pipeline.py, test_dynamic_pipeline_scenarios.py, test_async_concurrency.py
├── test_inspector_security_flow.py, test_network_and_hysteresis.py, test_adaptive_verifier.py
├── test_news_feeds.py, test_visual_delta_skipping.py, test_ui_interactions.py
├── test_adversarial_challenger.py, test_adversarial_hardening.py, test_empirical_challenger2_harness.py
├── test_vulnerability_remediations.py
└── e2e/                     # test_tier1_features.py … test_tier4_scenarios.py
```

## Running

```
python -m pytest tests -q        # test suite (needs pytest, pytest-asyncio, playwright + chromium)
python -m src.builders           # regenerate README.md, docs/index.html, data/summary.json from data/
python -m src.main --dry-run     # pipeline without network inspection
python -m src.main               # live run: hits vendor sites and rewrites data/
```

## Known gaps

- Several stored screenshots show a vendor's general certification page, not the specific offer.
- `value_usd` on free skill badges is not a real price; the generated outputs no longer show it for badges or total it.
- The README carries an MIT licence badge but the repository has no `LICENSE` file.
