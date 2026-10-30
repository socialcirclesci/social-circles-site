import datetime as dt
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from getting_there import getting_there  # noqa: E402
from makers import find, format_maker, index, key, to_maker  # noqa: E402
from pages import build, slug  # noqa: E402


class GettingThere(unittest.TestCase):
    def test_town(self):
        self.assertIn("St Helier town", getting_there("Jersey Arts Centre")[0])
        self.assertIn("St Helier town", getting_there("The Wellbeing Hub, 19 Commercial Buildings, St Helier")[0])

    def test_out_of_town(self):
        said, url = getting_there("Watersplash Beach Bar & Diner, St Ouen's Bay")
        self.assertIn("Out of town", said)
        self.assertIn("travelmode=transit", url)

    def test_unknown_place_makes_no_claim(self):
        said, _ = getting_there("The Drift")
        self.assertNotIn("town", said)

    def test_no_place(self):
        self.assertIsNone(getting_there("Location shared when you book"))
        self.assertIsNone(getting_there("Venue on booking"))

    def test_castle(self):
        self.assertIn("causeway", getting_there("Elizabeth Castle, St Aubin's Bay")[0])


class Makers(unittest.TestCase):
    BODY = format_maker({"Organiser": "The Stoodio", "What do you make or run?": "An open arts studio.",
                         "Instagram": "https://www.instagram.com/thestoodio/"})

    def test_parse(self):
        m = to_maker("Meet the maker: The Stoodio", self.BODY)
        self.assertEqual(m["by"], "The Stoodio")
        self.assertEqual(m["insta"], "thestoodio")
        self.assertEqual(m["expect"], "")
        self.assertIsNone(to_maker("Meet the maker: Someone", format_maker({"Organiser": "Someone"})))

    def test_find(self):
        makers = index([to_maker("", self.BODY)])
        self.assertEqual(find(makers, "The Stoodio at ArtHouse Jersey")["by"], "The Stoodio")
        self.assertEqual(find(makers, "The Stoodio (Sophie Harris and Hayley Gibaut)")["by"], "The Stoodio")
        self.assertIsNone(find(makers, "Studio Nine"))

    def test_key(self):
        self.assertEqual(key("The Stoodio"), key("the stoodio."))
        self.assertEqual(key("Jersey Arts Centre"), key("Jersey Arts Centre Ltd"))

    def test_on_page(self):
        e = {"d": "2026-11-07", "t": "Open Studio", "by": "The Stoodio", "at": "Capital House, 8 Church Street, St Helier", "cat": "Art"}
        with tempfile.TemporaryDirectory() as site:
            build(site, [e], dt.date(2026, 10, 30), index([to_maker("", self.BODY)]))
            page = (Path(site) / "events" / slug(e) / "index.html").read_text()
        self.assertIn("Meet the maker", page)
        self.assertIn("An open arts studio.", page)
        self.assertIn("Getting", page)


if __name__ == "__main__":
    unittest.main()
