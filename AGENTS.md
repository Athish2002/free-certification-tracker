# Instructions for AI agents working in this repository

This project lists free and discounted certification offers. People act on what it says: they register, study, and sometimes pay. A wrong entry costs a stranger time or money. The owner wants it to be useful and true, not impressive.

On 2026-11-16 a review found fabricated proof images, invented voucher codes and overstated verification claims, all produced by earlier agent work. See `CORRECTIONS.md`. Do not repeat any of it.

## Rules for this repository

1. **Never invent a fact about an offer.** Prices, dates, eligibility, exam codes, voucher codes, recurrence patterns and campaign history must come from a vendor page you actually loaded in this session. If you did not load it, do not write it. Do not rely on what you remember about a vendor's offers.

2. **An offer is Active only with a quoted source.** In `data/curated_policies.json`, an entry with `enforce_status: "Active"` must have all of:
   - `evidence_url`: the vendor page (HTTPS, vendor's own domain)
   - `evidence_quote`: the exact sentence copied from that page that states the terms
   - `reviewed_on`: the date the page was read (YYYY-MM-DD)
   - `reviewed_by`: who read it. Use the person's name if a person read it. If you (an agent) read it, write `agent:<model name>` and say so in your report. Never write the owner's name for a check he did not do.
   - `review_due_utc`: no more than 30 days after `reviewed_on`

   If the page does not contain a sentence that states the terms, the offer is not Active. Do not paraphrase a quote, and do not shorten it in a way that changes its meaning.

3. **Never create an image to serve as a screenshot.** Files in `docs/screenshots/` are written only by the Playwright capture in `src/dom_inspector.py`. If a capture fails, the offer has no screenshot. A screenshot shows that a page loaded; it is not evidence of the terms.

4. **Never publish a voucher code.** The `voucher_code` field was removed on purpose. Do not add it back under any name.

5. **Use the words the code has earned.** The inspector does a reachability check and a keyword check. Do not describe its result as verified, confirmed, authentic, guaranteed or $0. Do not add badges, scores, totals or percentages unless they are computed from real checks. "Free" means the candidate pays nothing; a discount with a co-pay is a discount.

6. **Do not hand-edit generated files.** `README.md`, `docs/index.html` and `data/summary.json` are produced by `python -m src.builders`. Change `src/builders/` or the data, then rebuild.

7. **Do not add machinery.** No new verification tiers, engines, scores or test suites unless the owner asks. If you think one is needed, say what user-visible claim it would support and wait for a yes.

8. **Tests.** Run `python -m pytest tests -q` before saying anything works, and report the real output. Do not delete or weaken a test to get a pass. Do not add tests that only exercise mocks of the thing being claimed. The repository's `.venv` does not have pytest installed; use an interpreter that does and say which one you used.

9. **Git.** Do not commit or push unless asked. The scheduled workflow (`.github/workflows/tracker.yml`) commits data changes as "CertPulse Bot"; rebase before pushing.

10. **Record corrections.** When you find something published here that was wrong, fix it and add an entry to `CORRECTIONS.md` saying what was wrong and what changed.

## When you report back

Say what you changed, what you ran and what it printed, what you did not check, and what you are unsure of. If you found that existing content is unsupported, say so plainly even if you were not asked to look.
