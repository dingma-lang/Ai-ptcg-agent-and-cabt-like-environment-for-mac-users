"""Optional Playwright checks for recorded deck, Prize and discard snapshots."""
from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8768")
    parser.add_argument("--chrome", default="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    parser.add_argument("--screenshots", default="/private/tmp/cabt-zone-checks")
    args = parser.parse_args()
    output = Path(args.screenshots)
    output.mkdir(parents=True, exist_ok=True)
    url = args.base_url + "/files/data/replays/battle20_10-13_2026-09-09_sub_vs_sub.html"
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.chrome, headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(url)
        page.locator('#cardZones > summary').click()
        page.wait_for_selector("#zonePlayers")
        assert page.locator("[data-zone-player]").count() == 2
        page.evaluate("goTurn(turns.findIndex(t => t.turn === 3))")

        # All timing modes use the same exact frame for the board and all three zones.
        for mode in ["start", "action", "end"]:
            page.locator(f'[name="snapshotMoment"][value="{mode}"]').check()
            selected = page.evaluate("selectedFrameIndex()")
            assert f"Frame {selected + 1}" in page.locator("#framePosition").inner_text()
            assert page.locator("#zoneFrame").inner_text() == f"Frame {selected + 1}"
            for zone in ["deck", "prize", "discard"]:
                page.locator(f"#zone-{zone}").click()
                counts = page.evaluate("zone => frames[selectedFrameIndex()].current.players.map(player => zone === 'deck' ? player.deckCount : player[zone].length)", zone)
                for index, count in enumerate(counts):
                    panel = page.locator(f'[data-zone-player="{index}"]')
                    assert f": {count}" in panel.locator('.zone-player-head').inner_text()
                    if zone == "prize":
                        assert panel.locator('.zone-row').count() == max(1, count)
                    elif count:
                        total = sum(int(text[1:]) for text in panel.locator('.zone-quantity').all_text_contents())
                        assert total == count
            current_turn = page.evaluate("frames[selectedFrameIndex()].current.turn")
            displayed_turn = page.evaluate("turns[turnCursor].turn")
            if current_turn > displayed_turn:
                assert "Next-turn prompt" in page.locator('#zoneTiming').inner_text()

        # Card selection updates local metadata; sorting/grouping does not invent deck order.
        page.locator('#zone-deck').click()
        first = page.locator('[data-zone-player="0"] [data-card-id]').first
        name = first.inner_text()
        first.click()
        assert page.locator('#cardDetail h2').inner_text() == name
        page.locator('#zoneFilter').fill('no-such-card-name')
        assert page.locator('#zonePlayers').inner_text().count('No matching cards') == 2
        page.locator('#zoneFilter').fill('')
        page.locator('#revealZones').uncheck()
        assert page.locator('#zonePlayers [data-card-id]').count() == 0
        assert 'Deck contents concealed' in page.locator('#zonePlayers').inner_text()
        page.locator('#zone-prize').click()
        assert page.locator('#zonePlayers [data-card-id]').count() == 0
        assert 'Face-down Prize card' in page.locator('#zonePlayers').inner_text()
        page.locator('#zone-discard').click()
        assert page.locator('#zonePlayers [data-card-id]').count() > 0
        page.locator('#revealZones').check()

        # Partial recordings retain unknown identities/counts without guessing from future frames.
        unknown = page.evaluate("zoneSnapshot({deckCount:10}, 'deck')")
        assert unknown['count'] == 10 and unknown['unknown'] == 10 and unknown['known'] == 0
        partial = page.evaluate("zoneSnapshot({prize:[null,{id:105},null]}, 'prize')")
        assert partial['unknown'] == 2 and partial['count'] == 3
        assert page.evaluate("zoneSnapshot({}, 'discard').count") is None
        assert page.evaluate("zoneSnapshot({discard:[]}, 'discard').count") == 0
        assert page.evaluate("zoneSnapshot({deckCount:0,deck:[{id:105}]}, 'deck').inconsistent")
        assert page.evaluate("zoneSnapshot({deck:[{name:7}]}, 'deck').known") == 0
        grouped = page.evaluate("inventoryRows(zoneSnapshot({deck:[{id:105,serial:1},{id:105,serial:2},{id:106,serial:3}]},'deck'),'deck',true)")
        assert sorted(row['count'] for row in grouped) == [1,2]

        # Controls do not re-render or clear an open review draft.
        page.evaluate("goTurn(1)")
        frame = page.evaluate("turns[1].actions[0].frame")
        editor = page.locator(f'[data-review-frame="{frame}"]')
        editor.locator('summary').click()
        editor.locator('textarea').fill('Keep this note while checking deck and Prizes')
        page.locator('[name="snapshotMoment"][value="end"]').check()
        page.locator('#zone-prize').click()
        assert editor.get_attribute('open') is not None
        assert editor.locator('textarea').input_value().startswith('Keep this note')
        page.evaluate("goAction(0)")
        assert page.evaluate("snapshotMoment") == 'action'
        assert page.evaluate("selectedFrameIndex() === turns[turnCursor].actions[0].result_frame")
        assert page.evaluate("reviewExport().changes[0].comment").startswith('Keep this note')
        page.locator('#zone-deck').click()
        page.locator('#zone-deck').focus()
        page.keyboard.press('ArrowRight')
        assert page.locator('#zone-prize').get_attribute('aria-selected') == 'true'

        for width, height, label in [(1440, 1000, 'desktop'), (390, 844, 'mobile')]:
            page.set_viewport_size({'width':width, 'height':height})
            page.locator('#zone-deck').click()
            page.locator('#zoneFrame').scroll_into_view_if_needed()
            page.screenshot(path=str(output / f'{label}-deck.png'))
            page.locator('#zone-prize').click()
            page.screenshot(path=str(output / f'{label}-prizes.png'))
            assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
        assert not errors, errors
        browser.close()
    print('PASS: deck/Prize/discard counts, both players, all snapshot modes, reveal toggle, unknowns, grouping, metadata, keyboard tabs, review retention and responsive layout.')


if __name__ == '__main__':
    main()
