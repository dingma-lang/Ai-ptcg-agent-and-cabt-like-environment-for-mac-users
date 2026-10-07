from __future__ import annotations

import json
import unittest

from visualize_replay import build_frames, render_html, synthetic_mirror_trace


class ReplayVisualizerTests(unittest.TestCase):
    def test_synthetic_mirror_trace_builds_enriched_frames(self) -> None:
        records = synthetic_mirror_trace()
        frames = build_frames(records)

        self.assertGreaterEqual(len(frames), 5)
        self.assertTrue(all("options" in frame for frame in frames))
        self.assertTrue(any(option.get("chosen") for frame in frames for option in frame["options"]))
        self.assertTrue(any("Buddy-Buddy Poffin" in option.get("label", "") for frame in frames for option in frame["options"]))

    def test_render_html_embeds_replay_payload(self) -> None:
        replay = {
            "title": "test",
            "source": "synthetic",
            "generated_at": "now",
            "summary": {},
            "frames": build_frames(synthetic_mirror_trace()[:1]),
        }
        html = render_html(replay)

        self.assertIn("PTCG Replay Inspector", html)
        self.assertIn("window.REPLAY_DATA =", html)
        payload_text = html.split("window.REPLAY_DATA = ", 1)[1].split(";\n", 1)[0]
        payload = json.loads(payload_text)
        self.assertEqual(payload["source"], "synthetic")


if __name__ == "__main__":
    unittest.main()
