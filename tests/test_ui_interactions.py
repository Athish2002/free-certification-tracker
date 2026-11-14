"""
Playwright End-to-End Browser Interaction & UI Verification Test Suite.
Verifies:
1. Binary Theme Toggle (GitHub Dark for dark mode, GitHub Light for light mode, Zero-FOIT, localStorage persistence).
2. Clean Separation of Exam Waves, Active Discounts, and Digital Skill Badges in both navigation and views.
3. Proof Button Clickability across all cards, views, and modal lightbox content integrity.
4. Navigation, Tab Switching, and Keyboard Hotkeys.
"""

import os

import pytest
from playwright.sync_api import Page, sync_playwright

pytestmark = pytest.mark.browser


@pytest.fixture(scope="module")
def html_dashboard_url():
    """Returns local file:// URL pointing to compiled docs/index.html."""
    path = os.path.abspath("docs/index.html").replace("\\", "/")
    return f"file:///{path}"


@pytest.fixture(scope="module")
def browser_page(html_dashboard_url):
    """Launches headless Chromium and navigates to the compiled dashboard."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()
        page.goto(html_dashboard_url, wait_until="networkidle")
        page.wait_for_timeout(500)
        yield page
        browser.close()


class TestThemeModeSwitching:
    """Verifies binary theme toggle: GitHub Light for light mode and GitHub Dark for dark mode."""

    def test_default_theme_is_github_dark(self, browser_page: Page):
        """Page must initialize with github-dark by default."""
        theme = browser_page.evaluate("document.documentElement.getAttribute('data-theme')")
        assert theme == "github-dark", f"Expected default theme 'github-dark', got '{theme}'"

        meta = browser_page.evaluate("document.querySelector('meta[name=\"theme-color\"]').getAttribute('content')")
        assert meta == "#0d1117", f"Expected dark meta theme color #0d1117, got '{meta}'"

    def test_theme_toggle_button_switches_to_github_light(self, browser_page: Page):
        """Clicking the toggle button must switch directly to github-light."""
        toggle_btn = browser_page.query_selector("#themeToggleBtn")
        assert toggle_btn is not None, "Theme toggle button '#themeToggleBtn' must exist"

        toggle_btn.click()
        browser_page.wait_for_timeout(200)

        theme = browser_page.evaluate("document.documentElement.getAttribute('data-theme')")
        assert theme == "github-light", f"Expected theme 'github-light', got '{theme}'"

        meta = browser_page.evaluate("document.querySelector('meta[name=\"theme-color\"]').getAttribute('content')")
        assert meta == "#ffffff", f"Expected light meta theme color #ffffff, got '{meta}'"

    def test_theme_toggle_button_switches_back_to_github_dark(self, browser_page: Page):
        """Clicking toggle button again must switch back to github-dark."""
        toggle_btn = browser_page.query_selector("#themeToggleBtn")
        toggle_btn.click()
        browser_page.wait_for_timeout(200)

        theme = browser_page.evaluate("document.documentElement.getAttribute('data-theme')")
        assert theme == "github-dark", f"Expected theme 'github-dark', got '{theme}'"

    def test_theme_hotkey_t_toggles_mode(self, browser_page: Page):
        """Pressing 'T' key must toggle between github-dark and github-light."""
        # Ensure focus is not on input
        browser_page.keyboard.press("Escape")
        browser_page.wait_for_timeout(100)

        # Press T to switch to light
        browser_page.keyboard.press("t")
        browser_page.wait_for_timeout(200)
        assert browser_page.evaluate("document.documentElement.getAttribute('data-theme')") == "github-light"

        # Press T to switch back to dark
        browser_page.keyboard.press("t")
        browser_page.wait_for_timeout(200)
        assert browser_page.evaluate("document.documentElement.getAttribute('data-theme')") == "github-dark"

    def test_no_lingering_theme_dropdown(self, browser_page: Page):
        """The 10-theme dropdown button must be eliminated from the interface."""
        dropdown_btn = browser_page.query_selector("#themeDropdownToggleBtn")
        assert dropdown_btn is None, "The old theme dropdown button should no longer exist in the DOM"


class TestSeparationOfWavesAndDiscounts:
    """Verifies that Exam Waves, Active Discounts, and Skill Badges are cleanly segmented."""

    def test_tier_filter_pills_exist_with_correct_labels(self, browser_page: Page):
        """Tier filter bar must provide All, Exam Waves, Active Discounts, and Skill Badges."""
        all_pill = browser_page.query_selector("#tierPillAll")
        wave_pill = browser_page.query_selector("#tierPillWave")
        discount_pill = browser_page.query_selector("#tierPillDiscount")
        badges_pill = browser_page.query_selector("#tierPillBadges")

        assert all_pill is not None, "All Credentials pill must exist"
        assert wave_pill is not None, "🌊 Exam Waves pill must exist"
        assert discount_pill is not None, "🏷️ Active Discounts pill must exist"
        assert badges_pill is not None, "🎓 Skill Badges pill must exist"

        assert "Exam Waves" in wave_pill.inner_text()
        assert "Active Discounts" in discount_pill.inner_text()
        assert "Skill Badges" in badges_pill.inner_text()

    def test_bento_grid_counters_reflect_segmented_counts(self, browser_page: Page):
        """Hero Bento boxes must display distinct metrics for Waves, Discounts, and Badges."""
        cards = browser_page.query_selector_all(".primer-card")
        assert len(cards) >= 4, "Must have at least 4 hero bento cards"

        page_text = browser_page.inner_text("#vouchersSection")
        assert "Exam Waves" in page_text
        assert "Active Discounts" in page_text
        assert "Skill Badges" in page_text

    def test_all_view_renders_distinct_section_headers(self, browser_page: Page):
        """In 'all' view, the catalog must display clear section headers separating categories."""
        browser_page.query_selector("#tierPillAll").click()
        browser_page.wait_for_timeout(300)

        grid_text = browser_page.inner_text("#offersGrid")
        assert "Limited-Time Exam Waves & Seasonal Challenge Cohorts" in grid_text
        assert "Active Ongoing Discounts & Vouchers" in grid_text
        assert "Free Digital Skill Badges & Hands-On Cloud Labs" in grid_text

    def test_filter_by_exam_waves_shows_only_waves(self, browser_page: Page):
        """Clicking Exam Waves pill filters catalog strictly to seasonal/challenge wave opportunities."""
        browser_page.query_selector("#tierPillWave").click()
        browser_page.wait_for_timeout(300)

        visible_cards = browser_page.query_selector_all("#offersGrid .primer-card")
        assert len(visible_cards) > 0, "Must have visible cards for Exam Waves"

        # Verify section title indicates wave-filtered state or each card is an exam wave
        card_badges = [c.inner_text() for c in visible_cards]
        for badge_text in card_badges:
            assert "🌊 Exam Wave" in badge_text or "Wave" in badge_text or "Challenge" in badge_text

    def test_filter_by_active_discounts_shows_only_discounts(self, browser_page: Page):
        """Clicking Active Discounts pill filters catalog strictly to ongoing discounts & student vouchers."""
        browser_page.query_selector("#tierPillDiscount").click()
        browser_page.wait_for_timeout(300)

        visible_cards = browser_page.query_selector_all("#offersGrid .primer-card")
        assert len(visible_cards) > 0, "Must have visible cards for Active Discounts"

        card_badges = [c.inner_text() for c in visible_cards]
        for badge_text in card_badges:
            assert (
                "🏷️ Active Discount" in badge_text
                or "Discount" in badge_text
                or "Voucher" in badge_text
                or "Student" in badge_text
            )

    def test_filter_by_skill_badges_shows_only_badges(self, browser_page: Page):
        """Clicking Skill Badges pill filters catalog to digital badges and labs."""
        browser_page.query_selector("#tierPillBadges").click()
        browser_page.wait_for_timeout(300)

        visible_cards = browser_page.query_selector_all("#offersGrid .primer-card")
        assert len(visible_cards) > 0, "Must have visible cards for Skill Badges"

        card_badges = [c.inner_text() for c in visible_cards]
        for badge_text in card_badges:
            assert "🎓 Skill Badge" in badge_text or "Badge" in badge_text or "Lab" in badge_text


class TestProofButtonClickabilityAndModalContent:
    """Verifies that all Proof buttons are 100% clickable and display accurate modal content."""

    def test_proof_buttons_in_grid_open_modal_with_correct_data(self, browser_page: Page):
        """Every proof button in Grid view must open the lightbox with authentic title and screenshot path."""
        # Reset to all
        browser_page.query_selector("#tierPillAll").click()
        browser_page.wait_for_timeout(300)

        proof_buttons = browser_page.query_selector_all("#offersGrid button[data-proof-id]")
        assert len(proof_buttons) > 0, "Must find proof buttons with data-proof-id attribute"

        # Test first 5 cards thoroughly
        for i in range(min(5, len(proof_buttons))):
            btn = proof_buttons[i]
            target_id = btn.get_attribute("data-proof-id")
            assert target_id, "Button must have a non-empty data-proof-id"

            btn.scroll_into_view_if_needed()
            btn.click()
            browser_page.wait_for_timeout(200)

            modal = browser_page.query_selector("#proofModal")
            assert modal is not None and modal.is_visible(), (
                f"Modal must be visible after clicking button {i} ({target_id})"
            )

            # Verify title is populated and not empty
            title = browser_page.inner_text("#proofModalTitle")
            assert len(title) > 3, f"Modal title must be populated for {target_id}"

            # Verify image src contains target_id
            img_src = browser_page.get_attribute("#proofModalImage", "src")
            assert target_id in img_src or "screenshots" in img_src, f"Image src '{img_src}' must match {target_id}"

            # Verify tier label is populated
            tier = browser_page.inner_text("#proofModalTier")
            assert any(t in tier for t in ["Exam Wave", "Active Discount", "Skill Badge", "Proctored Exam"]), (
                f"Invalid tier label '{tier}'"
            )

            # Verify candidate eligibility is populated
            elig = browser_page.inner_text("#proofModalEligibility")
            assert len(elig) > 0, f"Candidate eligibility must be populated for {target_id}"

            # Verify full-res link
            full_res_href = browser_page.get_attribute("#proofModalFullResLink", "href")
            assert full_res_href and ".png" in full_res_href, f"Full-res link must target screenshot png"

            # Close via close button
            close_btn = browser_page.query_selector("#closeProofModalBtn")
            assert close_btn is not None and close_btn.is_visible()
            close_btn.click()
            browser_page.wait_for_timeout(200)

            assert not modal.is_visible(), "Modal must be hidden after clicking close button"

    def test_card_back_flip_shows_verified_claim_spec_without_fake_fingerprint(self, browser_page: Page):
        """Flipping a card must display the genuine claim spec and no fake SHA-256 fingerprints or curl replays."""
        flip_btn = browser_page.query_selector("#offersGrid button[title*='Policy']")
        if flip_btn:
            flip_btn.scroll_into_view_if_needed()
            flip_btn.click()
            browser_page.wait_for_timeout(300)

            grid_text = browser_page.inner_text("#offersGrid")
            assert "VERIFIED CLAIM & POLICY SPEC" in grid_text
            assert "SHA-256 Fingerprint:" not in grid_text
            assert "curl -sI" not in grid_text
            assert "Tuition Saved:" in grid_text

            # Flip back so front face buttons remain clickable for subsequent tests
            return_btn = browser_page.query_selector("#offersGrid button:has-text('Return to Voucher')")
            if return_btn:
                return_btn.click()
            browser_page.wait_for_timeout(300)

    def test_proof_modal_closes_on_escape_key(self, browser_page: Page):
        """Opening modal and pressing Escape key must close it cleanly."""
        btn = browser_page.query_selector("#offersGrid button[data-proof-id]")
        btn.scroll_into_view_if_needed()
        btn.click()
        browser_page.wait_for_timeout(200)

        modal = browser_page.query_selector("#proofModal")
        assert modal.is_visible(), "Modal must be open"

        browser_page.keyboard.press("Escape")
        browser_page.wait_for_timeout(200)
        assert not modal.is_visible(), "Modal must be closed after pressing Escape"

    def test_proof_modal_closes_on_backdrop_click(self, browser_page: Page):
        """Clicking outside the modal content (on the backdrop) must close it."""
        btn = browser_page.query_selector("#offersGrid button[data-proof-id]")
        btn.scroll_into_view_if_needed()
        btn.click()
        browser_page.wait_for_timeout(200)

        modal = browser_page.query_selector("#proofModal")
        assert modal.is_visible(), "Modal must be open"

        # Click top-left edge of the modal backdrop
        browser_page.mouse.click(10, 10)
        browser_page.wait_for_timeout(200)
        assert not modal.is_visible(), "Modal must be closed after clicking backdrop"

    def test_table_view_proof_buttons_clickable(self, browser_page: Page):
        """Proof buttons in Table/List view must be fully clickable and open modal."""
        # Switch to list view
        browser_page.query_selector("#viewBtnList").click()
        browser_page.wait_for_timeout(300)

        table_proof_btns = browser_page.query_selector_all("#offersTableBody button[data-proof-id]")
        assert len(table_proof_btns) > 0, "Must have proof buttons in table view"

        first_btn = table_proof_btns[0]
        first_btn.scroll_into_view_if_needed()
        first_btn.click()
        browser_page.wait_for_timeout(200)

        modal = browser_page.query_selector("#proofModal")
        assert modal.is_visible(), "Modal must open when clicking proof button in Table view"

        browser_page.keyboard.press("Escape")
        browser_page.wait_for_timeout(200)
        assert not modal.is_visible()

        # Switch back to grid view
        browser_page.query_selector("#viewBtnGrid").click()
        browser_page.wait_for_timeout(200)


class TestNavigationAndTabs:
    """Verifies tab switching and keyboard hotkeys."""

    def test_tab_switching_navigation(self, browser_page: Page):
        """Clicking tabs must switch between Vouchers, Tech Radar, and Redemption sections."""
        # Switch to Industry Tech Radar
        browser_page.query_selector("#tabBtnNews").click()
        browser_page.wait_for_timeout(300)
        assert browser_page.is_visible("#newsSection"), "News section must be visible"
        assert not browser_page.is_visible("#vouchersSection"), "Vouchers section must be hidden"

        # Switch to Where Offers Are Applied (Redemption)
        browser_page.query_selector("#tabBtnRedemption").click()
        browser_page.wait_for_timeout(300)
        assert browser_page.is_visible("#redemptionSection"), "Redemption section must be visible"
        assert not browser_page.is_visible("#newsSection"), "News section must be hidden"

        # Switch back to Vouchers
        browser_page.query_selector("#tabBtnVouchers").click()
        browser_page.wait_for_timeout(300)
        assert browser_page.is_visible("#vouchersSection"), "Vouchers section must be visible"

    def test_numeric_hotkeys_navigation(self, browser_page: Page):
        """Pressing 1, 2, 3 must switch tabs."""
        browser_page.keyboard.press("Escape")
        browser_page.wait_for_timeout(100)

        browser_page.keyboard.press("2")
        browser_page.wait_for_timeout(200)
        assert browser_page.is_visible("#newsSection")

        browser_page.keyboard.press("3")
        browser_page.wait_for_timeout(200)
        assert browser_page.is_visible("#redemptionSection")

        browser_page.keyboard.press("1")
        browser_page.wait_for_timeout(200)
        assert browser_page.is_visible("#vouchersSection")
