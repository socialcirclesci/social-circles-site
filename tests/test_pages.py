import datetime as dt
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from pages import build, slug, weekend  # noqa: E402

TODAY = dt.date(2026, 10, 28)  # a Wednesday
EVENTS = [
    {"d": "2026-10-30", "t": "80's & 90's Disco Night", "by": "Island Music", "at": "The Drift", "time": "7:30pm", "cat": "Music", "url": "https://example.com"},
    {"d": "2026-10-24", "end": "2026-11-07", "t": "Fox Open", "by": "Jersey Arts Centre", "at": "Arts Centre", "cat": "Art", "type": "exhibition"},
    {"d": "2026-11-20", "t": "Sea Shanty Night", "by": "The Pub", "at": "St Aubin", "cat": "Music"},
]


class Pages(unittest.TestCase):
    def test_slug(self):
        self.assertEqual(slug(EVENTS[0]), "80s-and-90s-disco-night-30-oct")

    def test_weekend_is_friday_to_sunday(self):
        self.assertEqual(weekend(TODAY), (dt.date(2026, 10, 30), dt.date(2026, 11, 1)))
        self.assertEqual(weekend(dt.date(2026, 10, 31)), (dt.date(2026, 10, 31), dt.date(2026, 11, 1)))

    def test_build(self):
        with tempfile.TemporaryDirectory() as site:
            build(site, EVENTS, TODAY)
            page = (Path(site) / "events" / slug(EVENTS[0]) / "index.html").read_text()
            self.assertIn("By Island Music", page)
            self.assertIn('"@type":"Event"', page)
            week = (Path(site) / "this-weekend" / "index.html").read_text()
            self.assertIn("Disco Night", week)
            self.assertIn("Fox Open", week)
            self.assertNotIn("Sea Shanty", week)
            self.assertIn("/events/sea-shanty-night-20-nov/", (Path(site) / "sitemap.xml").read_text())


if __name__ == "__main__":
    unittest.main()
