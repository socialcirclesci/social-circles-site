import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from event_card import format_body  # noqa: E402
from tally_fixes import clean, find_card, note  # noqa: E402

CARDS = [{"number": n, "title": t, "body": format_body({"Date": d, "Venue": "Somewhere", "Organiser": "Someone"})}
         for n, t, d in [(14, "Winter Market", "2026-11-14"), (7, "Create your own signature candle", "2026-10-31"),
                         (20, "Create your own signature candle", "2026-11-28")]]


class Fixes(unittest.TestCase):
    def test_finds_the_card_by_page_then_name(self):
        self.assertEqual(find_card(CARDS, "events/create-your-own-signature-candle-28-nov/", "x")["number"], 20)
        self.assertEqual(find_card(CARDS, "", "Winter market")["number"], 14)
        self.assertIsNone(find_card(CARDS, "events/gone-1-jan/", "Gone"))

    def test_contact_details_stay_off_the_card(self):
        self.assertEqual(clean("call 07797 123456 or a@b.com"), "call [phone number removed] or [email removed]")
        body = note({"id": "abc", "submittedAt": "2026-10-28T10:00"}, {"what": "Now 8pm.\nEmail me x@y.je", "who": "Jo", "email": "x@y.je"}, "F1")
        self.assertNotIn("x@y.je", body)
        self.assertIn("> Now 8pm.", body)
        self.assertIn("<!-- tally-fix:abc -->", body)


if __name__ == "__main__":
    unittest.main()
