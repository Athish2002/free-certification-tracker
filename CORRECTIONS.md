# Corrections

A record of things this repository got wrong and what was changed. Newest first. To report an error, open an issue with the "Report a wrong or closed offer" template.

## 2026-11-16: Verification claims were overstated and some proofs were not real

A review of the repository found that it claimed more checking than it performed. Much of the earlier content was produced by AI coding agents and was not checked by a person before publication. The following was wrong and has been changed.

**Proof images that were not screenshots.** Eight offers added on 2026-11-14 had "proof" images that were generated cards with typed text, not captures of the vendor page. They were presented as screenshot proof and the offers were described as "Playwright DOM Verified". The images have been deleted and the offers are marked as having no screenshot. The offers concerned are `aws-cloud-quest-practitioner`, `aws-educate-machine-learning`, `cisco-netacad-network-defense`, `databricks-genai-engineer-path`, `gcp-cloud-digital-leader-genai`, `linux-foundation-intro-linux`, `ms-applied-skills-azure-openai` and `oracle-oci-security-cert-prep`.

**Historical "proofs".** The archive of past campaigns linked screenshots that showed today's generic vendor pages or error pages, not the original campaigns. Those images have been deleted. The archive entries were written by hand and are now labelled as not independently verified.

**Invented voucher codes.** Every offer carried a `voucher_code` value such as `CC-FREE-1M`. None of these were real codes. The field has been removed from the data, the schema and the output. If you tried to use one of them, it was never valid.

**"$0 Confirmed" and "100% Verified".** The automated check only loads the page and looks for closure wording and for words such as "free" or "badge". It never confirmed a price. The labels now say "Page checked". Badges and summary rows claiming "100% verified", "zero scam domains" and "policy corroborated" have been removed.

**"Total value saved".** The dollar total summed list prices, including made-up values for courses and badges that are free to everyone. It has been removed.

**Juniper Open Learning listed as free.** It was shown as a free voucher with a confirmed $0 balance while its own note said the voucher is a 75% discount with about $50 still payable. It is now described as a partial discount.

**Offers listed as Active without anyone having read the terms.** Policy notes are written by hand in `data/curated_policies.json`. Their review dates had passed without effect, and no note recorded who had read the vendor page or what it said. Two rules now apply: a note past its review date cannot keep an offer Active, and a note without a quoted source (who read it, when, the page, and the sentence) cannot keep an offer Active.

**Re-check of all 28 open offers on 2026-11-16.** Each tracked vendor page was loaded and read by an AI agent (Claude), not by a person; each entry says so in `reviewed_by`. Results:

- 10 offers have a sentence on the vendor page that states the terms and are listed as Active with that sentence quoted: Snowflake Hands-On Essentials, Qualys training, the Databricks Generative AI Fundamentals badge, the Databricks Fundamentals badge, AWS Educate, Juniper Open Learning (a 75% discount with $50 payable, not free), Linux Foundation Introduction to Linux (course only), Cisco Networking Academy Introduction to Cybersecurity, Cisco Networking Academy Network Defense, and Google Skills (a no-cost subscription limited to 35 credits a month).
- 2 are retired: Microsoft Applied Skills "Develop generative AI solutions with Azure OpenAI Service" (the page says the assessment has been retired) and the Oracle OCI Generative AI learning path (the page says the course may be retired or obsolete). Both had been listed as Active and free.
- 3 links are dead: the MongoDB certification page, the Databricks Generative AI Engineer page, and the AWS Cloud Quest course link.
- 13 could not be confirmed and stay under "Needs re-check", each with a note saying what the page did and did not state. Examples: the Postman page showed a paid promotion; the Red Hat page offers a free skills assessment but no badge; the GitLab page says the learning content is free but does not give the exam price; the Oracle pages showed no terms without signing in.

The nine free entries are free courses and unproctored badges. None is an exam voucher. **No free proctored exam offer is currently confirmed in this list.**

**The automated "Active" signal was unreliable.** The keyword page check was measured against the 28 hand-read pages with `scripts/evaluate_checker.py`. It called 19 offers Active; the reader could confirm the terms for 9 of them. It called a retired credential Active. It no longer decides whether an offer is Active: new leads enter as "Review Needed", and "has been retired" wording is now treated as closed.

**New automated check.** For offers with a quoted source, the pipeline reloads the page and looks for that exact sentence (`src/evidence_check.py`). If it is missing in two consecutive runs, the offer stops being shown as Active. On its first run it found 9 of the 10 Active sentences; the AWS Educate sentence was not found in the headless load, and that offer will be demoted if it happens again.

**Dashboard.** Cards showed a "Challenge Window / Active Sprint" progress bar that was a fixed 76% decoration, a "$0.00 Apply" button, a "Claim Free" link with a confetti effect, and a "PRO" label. A free badge was tagged "Exam Wave" with a list price. These have been removed or corrected. Cards now show the quoted vendor sentence, who read it and when, and the result of the automated sentence check. Offer-type labels were rewritten to match what the quoted sentence supports.

**Test files in the proof folder.** `docs/screenshots/test-candidate.png` and `docs/screenshots/test-spa-offer.png` were leftovers from test runs and have been deleted.

**Licence badge.** The README showed an MIT badge although the repository has no LICENSE file. The badge is now shown only when a LICENSE file exists.

**Project documentation.** `PROJECT.md` described modules and test files that were never written. It now describes what is in the repository.

### Not yet corrected

- The 10 Active entries were read by an AI agent, not by a person. A person should re-read each quoted source.
- The 13 offers in "Needs re-check" may be real offers whose terms are on a different page from the one tracked. Nobody has looked for those pages.
- The historical archive (13 entries, with dates and exam codes) has not been checked against any source. Treat it as unverified.
- The claim steps and checkout guides were written without testing the flows.
- The news section is pulled from feeds without review.
