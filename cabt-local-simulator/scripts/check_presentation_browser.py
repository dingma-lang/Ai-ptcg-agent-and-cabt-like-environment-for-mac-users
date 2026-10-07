"""Read-only UI smoke checks; no agent rules or real matches are changed."""
from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', default='http://127.0.0.1:8769')
    parser.add_argument('--screenshots', default='/private/tmp/cabt-presentation')
    args = parser.parse_args()
    output = Path(args.screenshots)
    output.mkdir(parents=True, exist_ok=True)
    errors = []
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', headless=True)
        page = browser.new_page(viewport={'width':1440, 'height':1000})
        page.on('pageerror', lambda error: errors.append(str(error)))

        def snapshot(name):
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), name
            page.screenshot(path=str(output / (name + '.png')))

        for width, height, label in [(1440,1000,'desktop'), (390,844,'mobile')]:
            page.set_viewport_size({'width':width, 'height':height})
            page.goto(args.base_url)
            page.wait_for_selector('.battle-row')
            for key in ['packageSettings','deckSettings','engineSettings','logImport','executionLog']:
                assert page.locator('#'+key).get_attribute('open') is None
            assert page.locator('#agentA').is_visible()
            assert page.locator('#agentB').is_visible()
            snapshot(label+'-simulator')
            page.locator('#battleSearch').fill('battle24_')
            assert page.locator('.battle-row').count() == 1
            page.locator('#battleSearch').fill('not-a-real-match')
            assert 'No matching battles' in page.locator('#resultLinks').inner_text()
            page.locator('#battleSearch').fill('')
            for key, child in [('packageSettings','agentFileA'),('deckSettings','deckA'),('engineSettings','verifyEngineBtn')]:
                page.locator('#'+key+' > summary').click()
                assert page.locator('#'+child).is_visible()
                page.locator('#'+key+' > summary').click()

            page.locator('#logImport > summary').click()
            page.locator('#logText').fill("Setup\nAlice played Finizen to the Active Spot.\nBob played Dratini to the Active Spot.\nAlice's Turn\nAlice drew a card.\nAlice ended their turn.\nAlice wins.")
            page.locator('#parseLogBtn').click()
            page.wait_for_selector('#replayRange')
            assert page.locator('#battleLibrary').is_hidden()
            assert page.locator('#replayRange').input_value() == '0'
            page.locator('#replayNextBtn').click()
            assert page.locator('#replayRange').input_value() == '1'
            page.locator('#backToBattles').click()
            assert page.locator('#battleLibrary').is_visible()
            assert page.locator('#visualizer').is_hidden()

            page.goto(args.base_url + '/study')
            page.wait_for_function('state.agents.length > 0')
            assert page.locator('#memorySettings').get_attribute('open') is None
            assert page.locator('#checkpointSettings').get_attribute('open') is None
            snapshot(label+'-study-empty')
            page.goto(args.base_url + '/study?study=study-20260913-142523-5eda6ba1e43b')
            page.wait_for_selector('#studyView', state='visible')
            snapshot(label+'-study')
            page.locator('#findingFilter').select_option('accepted')
            assert page.locator('[data-finding-status="pending"]:visible').count() == 0
            page.locator('#findingFilter').select_option('all')

            page.goto(args.base_url + '/files/data/replays/battle17_20-39_2026-09-08_pal_vs_pal.html')
            page.wait_for_selector('#turnTitle')
            assert page.locator('#cardZones').get_attribute('open') is None
            page.locator('#nextTurn').click()
            before = page.locator('#position').inner_text()
            page.locator('#playbackSpeed').select_option('375')
            page.locator('#play').click()
            page.wait_for_timeout(850)
            page.locator('#play').click()
            assert page.evaluate('actionCursor >= 0')
            page.evaluate('goTurn(1)')
            page.evaluate('scrollTo(0,0)')
            snapshot(label+'-replay')
            page.locator('#cardZones > summary').click()
            page.locator('#zone-prize').click()
            assert page.locator('#zonePlayers').is_visible()
            page.locator('#revealZones').uncheck()
            assert page.locator('#zonePlayers [data-card-id]').count() == 0
            page.locator('#revealZones').check()
        assert not errors, errors
        browser.close()
    print('PASS: simulator, disclosures, search, study/filter, replay/playback, hidden zones and desktop/mobile layouts; no JS errors.')


if __name__ == '__main__':
    main()
