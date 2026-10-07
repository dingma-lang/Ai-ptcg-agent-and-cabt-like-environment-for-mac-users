from html.parser import HTMLParser
import unittest

from cabt_local.official_visualizer import OFFICIAL_REPLAY_HTML
from cabt_local.study_page import STUDY_HTML
from cabt_local.webapp import INDEX_HTML


class PageStructure(HTMLParser):
    def __init__(self, page):
        super().__init__()
        self.ids = []
        self.details = {}
        self.feed(page)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if 'id' in attrs:
            self.ids.append(attrs['id'])
        if tag == 'details' and 'id' in attrs:
            self.details[attrs['id']] = 'open' in attrs


class PresentationTests(unittest.TestCase):
    def test_technical_sections_follow_agent_selection_and_start_closed(self):
        page = PageStructure(INDEX_HTML)
        for name in ['packageSettings', 'deckSettings', 'engineSettings', 'logImport']:
            self.assertFalse(page.details[name])
            self.assertGreater(page.ids.index(name), page.ids.index('playBtn'))
        self.assertFalse(page.details['executionLog'])

    def test_study_advanced_controls_start_closed(self):
        page = PageStructure(STUDY_HTML)
        for name in ['traceSettings', 'memorySettings', 'checkpointSettings']:
            self.assertFalse(page.details[name])
        self.assertIn('integrationStatus', page.ids)

    def test_replay_zones_remain_available_after_actions(self):
        page = PageStructure(OFFICIAL_REPLAY_HTML)
        self.assertFalse(page.details['cardZones'])
        self.assertGreater(page.ids.index('cardZones'), page.ids.index('actions'))
        for name in ['exportReview', 'revealZones', 'zone-prize', 'playbackSpeed']:
            self.assertIn(name, page.ids)

    def test_pages_keep_unique_ids_and_inline_icons(self):
        for html in [INDEX_HTML, STUDY_HTML, OFFICIAL_REPLAY_HTML]:
            page = PageStructure(html)
            self.assertEqual(len(page.ids), len(set(page.ids)))
            self.assertNotIn('__ICON_', html)
            self.assertIn('class="lucide ', html)
            self.assertNotIn('<script src=', html)
            self.assertIn('prefers-reduced-motion', html)


if __name__ == '__main__':
    unittest.main()
