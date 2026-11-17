"""Tests for the watchlist: reporting when offer wording on a vendor program page changes."""

import json

from src.watchlist import compare, issue_body, relevant_lines, run_watchlist

FILLER = "General information about certification programs and exam delivery partners. " * 5
BASE_PAGE = FILLER + "\nCertification exams cost $200.\nApplications open in April.\n"
NOW = "2026-11-17T00:00:00+00:00"


def test_relevant_lines_keeps_only_offer_wording_and_normalizes():
    lines = relevant_lines(
        "About us\nGet a FREE   exam voucher today!\nGet a free exam voucher today!\nContact sales\n"
    )
    assert lines == ["get a free exam voucher today!"]
    # Navigation words and very long blocks are not offer wording
    assert relevant_lines("Home\nFree\n" + ("free " * 100)) == []


def test_first_readable_load_is_a_baseline_not_a_change():
    state, change = compare(None, BASE_PAGE, NOW)
    assert change is None
    assert state["last_result"] == "read"
    assert state["last_changed_at"] is None
    assert "applications open in april." in state["lines"]


def test_added_and_removed_wording_is_reported():
    state, _ = compare(None, BASE_PAGE, NOW)
    new_page = BASE_PAGE.replace("Applications open in April.", "Register by December 5 for a free exam voucher.")
    later = "2026-11-18T00:00:00+00:00"
    state2, change = compare(state, new_page, later)
    assert change == {
        "added": ["register by december 5 for a free exam voucher."],
        "removed": ["applications open in april."],
    }
    assert state2["last_changed_at"] == later
    # The same page again is not a change
    _, again = compare(state2, new_page, "2026-11-19T00:00:00+00:00")
    assert again is None


def test_wording_unrelated_to_offers_is_ignored():
    state, _ = compare(None, BASE_PAGE, NOW)
    _, change = compare(state, BASE_PAGE + "\nOur new office opened in Berlin.\n", NOW)
    assert change is None


def test_unreadable_page_never_counts_as_a_change_and_keeps_the_baseline():
    state, _ = compare(None, BASE_PAGE, NOW)
    for broken in (None, "", "Loading..."):
        kept, change = compare(state, broken, "2026-11-18T00:00:00+00:00")
        assert change is None
        assert kept["lines"] == state["lines"]
        assert kept["last_result"] == "unreadable"
    # When the page comes back with new wording, the change is measured against the kept baseline
    kept, _ = compare(state, None, "2026-11-18T00:00:00+00:00")
    _, change = compare(kept, BASE_PAGE + "\n100% off vouchers for students.\n", "2026-11-19T00:00:00+00:00")
    assert change is not None and change["added"] == ["100% off vouchers for students."]


def test_run_watchlist_end_to_end_with_injected_pages(tmp_path):
    watch = tmp_path / "watchlist.json"
    state_file = tmp_path / "state.json"
    changes_file = tmp_path / "changes.json"
    watch.write_text(
        json.dumps(
            {
                "pages": [
                    {"id": "a", "vendor": "VendorA", "name": "Page A", "url": "https://a.example/offers"},
                    {"id": "b", "vendor": "VendorB", "name": "Page B", "url": "https://b.example/offers"},
                    {"id": "bad", "vendor": "X", "name": "Not https", "url": "http://x.example/"},
                ]
            }
        ),
        encoding="utf-8",
    )
    pages = {"https://a.example/offers": BASE_PAGE, "https://b.example/offers": BASE_PAGE}

    first = run_watchlist(watch, state_file, changes_file, fetch=pages.get)
    assert first == []  # baseline run reports nothing
    assert set(json.loads(state_file.read_text(encoding="utf-8"))) == {"a", "b"}  # non-https entry skipped

    pages["https://a.example/offers"] = BASE_PAGE + "\nFree exam voucher for the first 5,000 learners.\n"
    pages["https://b.example/offers"] = None  # page B fails to load
    second = run_watchlist(watch, state_file, changes_file, fetch=pages.get)
    assert [c["id"] for c in second] == ["a"]
    assert second[0]["added"] == ["free exam voucher for the first 5,000 learners."]

    log = json.loads(changes_file.read_text(encoding="utf-8"))
    assert [c["id"] for c in log["latest"]] == ["a"]
    assert json.loads(state_file.read_text(encoding="utf-8"))["b"]["last_result"] == "unreadable"

    third = run_watchlist(watch, state_file, changes_file, fetch=pages.get)
    assert third == []
    log = json.loads(changes_file.read_text(encoding="utf-8"))
    assert log["latest"] == [] and len(log["changes"]) == 1  # history kept, nothing re-reported


def test_issue_body_says_a_change_is_not_a_confirmed_offer():
    body = issue_body(
        {
            "vendor": "VendorA",
            "name": "Page A",
            "url": "https://a.example/offers",
            "detected_at": NOW,
            "added": ["free exam voucher for the first 5,000 learners."],
            "removed": [],
        }
    )
    assert "https://a.example/offers" in body
    assert "does not mean an offer is open" in body
    assert "- free exam voucher for the first 5,000 learners." in body
    assert "Wording removed" not in body


def test_published_watchlist_is_well_formed():
    from src.watchlist import load_watchlist

    pages = load_watchlist()
    ids = [p["id"] for p in pages]
    assert len(pages) >= 10
    assert len(ids) == len(set(ids))
    assert all(p["url"].startswith("https://") and p.get("vendor") and p.get("name") for p in pages)
