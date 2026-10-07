"""Optional browser regression. Requires Playwright; runs against a local app."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import tempfile

from playwright.sync_api import sync_playwright


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8768")
    parser.add_argument("--chrome", default="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    parser.add_argument("--screenshots", default="/private/tmp/cabt-review-checks")
    args = parser.parse_args()
    output = Path(args.screenshots)
    output.mkdir(parents=True, exist_ok=True)
    url = args.base_url + "/files/data/replays/battle17_20-39_2026-09-08_pal_vs_pal.html"
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.chrome, headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 1000}, accept_downloads=True)
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(url)
        page.wait_for_selector("[data-review-frame]")
        assert page.evaluate("reviewActions.every(a => a.review.editable)")

        def open_review(frame: int):
            page.evaluate("frame => goTurn(turns.findIndex(t => t.actions.some(a => a.frame === frame)))", frame)
            panel = page.locator(f'[data-review-frame="{frame}"]')
            panel.locator("summary").click()
            return panel

        panel = open_review(16)
        assert panel.locator("[data-review-option]").count() == 4
        assert "Dratini" not in panel.locator(".review-options").inner_text()
        assert "Palafin ex" not in panel.locator(".review-options").inner_text()
        assert "Buddy-Buddy Poffin" in panel.inner_text()
        assert panel.locator('[value="1"]').is_disabled()
        panel.locator('[value="0"]').uncheck()
        panel.locator('[value="3"]').uncheck()
        panel.locator('[value="1"]').check()
        panel.locator('[value="2"]').check()
        assert panel.locator('[value="3"]').is_disabled()
        comment = 'Choose two Finizen, not Tatsugiri. <script>alert("unsafe")</script>'
        panel.locator("textarea").fill(comment)
        panel.locator("[data-review-filter]").fill("Tatsugiri")
        assert panel.locator('[data-review-row]:visible').count() == 1
        panel.locator("[data-review-filter]").fill("")
        page.reload()
        panel = open_review(16)
        assert panel.locator("textarea").input_value() == comment
        assert panel.locator('[value="1"]').is_checked()
        assert panel.locator('[value="2"]').is_checked()
        assert page.locator("#exportReview").is_enabled()
        panel.scroll_into_view_if_needed()
        page.screenshot(path=str(output / "desktop-review.png"))

        panel = open_review(15)
        original = page.evaluate("reviewByFrame.get('15').review.original[0]")
        replacement = page.evaluate("reviewByFrame.get('15').review.options.find(o => o.index !== reviewByFrame.get('15').review.original[0]).index")
        panel.locator(f'[value="{replacement}"]').check()
        panel.locator("textarea").fill("Use this legal action before the original Poffin play.")
        panel = open_review(16)
        assert "Earlier action edited" in panel.locator("[data-review-dependency]").inner_text()
        log = page.evaluate("reviewExport()")
        assert [c["decision_index"] for c in log["changes"]] == [15, 16]
        assert log["changes"][1]["proposed_indexes"] == [1, 2]
        assert log["changes"][1]["after_edited_decisions"] == [15]
        assert "not a simulated" in log["notice"]
        with tempfile.TemporaryDirectory() as tmp:
            for fmt in ["txt", "json"]:
                page.locator("#reviewFormat").select_option(fmt)
                with page.expect_download() as event:
                    page.locator("#exportReview").click()
                download = event.value
                assert download.suggested_filename.endswith("_review." + fmt)
                target = Path(tmp) / download.suggested_filename
                download.save_as(target)
                data = target.read_text()
                assert comment in (json.loads(data)["changes"][1]["comment"] if fmt == "json" else data)

        # Strict export checks reject tampered, duplicated, excessive, and undersized selections.
        for indexes in [[-1], [400], [1, 1], [True], [0, 1, 2]]:
            assert page.evaluate("xs => !!reviewError(reviewByFrame.get('16').review, xs)", indexes)
        assert page.evaluate("reviewError(reviewByFrame.get('16').review, [])") == ""
        assert page.evaluate("!!reviewError(reviewByFrame.get('15').review, [])")
        page.evaluate("reviewDraft['15'].indexes = []; syncReviewPanels()")
        assert page.locator("#exportReview").is_disabled()
        panel = open_review(15)
        panel.locator(f'[value="{replacement}"]').check()
        assert page.locator("#exportReview").is_enabled()

        # Reset one entry does not erase a different turn's comments.
        panel.locator("[data-review-reset]").click()
        assert page.evaluate("reviewEntries().length") == 1
        assert page.evaluate("draftFor(reviewByFrame.get('15')).indexes[0]") == original
        page.goto(url.replace("battle17_20-39_2026-09-08_pal_vs_pal", "battle16_20-39_2026-09-08_pal_vs_pal"))
        assert page.evaluate("reviewEntries().length") == 0
        page.goto(url)
        assert page.evaluate("reviewEntries().length") == 1
        page.set_viewport_size({"width": 390, "height": 844})
        panel = open_review(16)
        panel.locator("textarea").fill("Mobile draft")
        panel.scroll_into_view_if_needed()
        page.screenshot(path=str(output / "mobile-review.png"))
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        assert page.evaluate("draftFor(reviewByFrame.get('16')).comment") == "Mobile draft"

        # Browser storage failures must not prevent choices, comments, or export.
        page.evaluate("() => { Storage.prototype.setItem = () => { throw new Error('quota'); }; }")
        panel.locator("textarea").fill("Memory-only draft")
        assert "Page memory only" in page.locator("#reviewStatus").inner_text()
        assert page.locator("#exportReview").is_enabled()
        assert page.evaluate("reviewExport().changes[0].comment") == "Memory-only draft"
        page.on("dialog", lambda dialog: dialog.accept())
        page.locator("#clearReview").click()
        assert page.evaluate("reviewEntries().length") == 0
        assert page.locator("#exportReview").is_disabled()
        assert not errors, errors
        browser.close()
    print("PASS: legal alternatives, Poffin limits, hidden-free search, drafts, export, isolation, reset, mobile layout, storage failure; no browser errors.")


if __name__ == "__main__":
    main()
