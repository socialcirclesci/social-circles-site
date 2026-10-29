import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from event_card import format_body  # noqa: E402
from review_cards import date_on_page, review  # noqa: E402

TODAY = dt.date(2026, 10, 28)
PAGE = "<html><h1>Sea Shanty Night</h1><p>Friday 20th November, 7pm</p></html>"


def card(n=1, title="Sea Shanty Night", **kw):
    fields = {"Date": "2026-11-20", "Time": "7pm", "Venue": "The Moorings", "Organiser": "Shanty Crew", "Price": "£5",
              "Category": "Music", "Link": "https://example.com/shanty", "Fit note": "Strong fit: a sing-along", "Source": "x"}
    fields.update(kw)
    return {"number": n, "title": title, "body": format_body(fields)}


class Review(unittest.TestCase):
    def check(self, c, others=(), page=(200, PAGE)):
        return review(c, list(others) + [c], TODAY, fetcher=lambda url: page)

    def test_ready(self):
        problems, notes = self.check(card())
        self.assertEqual(problems, [])
        self.assertIn("The date matches the event page", notes)

    def test_wrong_date(self):
        problems, _ = self.check(card(Date="2026-11-21"))
        self.assertTrue(any("couldn't find Sat 21 Nov" in p for p in problems))

    def test_dead_link_and_blocked_site(self):
        self.assertIn("The link doesn't open (404)", self.check(card(), page=(404, ""))[0])
        problems, notes = self.check(card(), page=(403, ""))
        self.assertEqual(problems, [])
        self.assertTrue(notes[0].startswith("The link's site didn't let me read it"))

    def test_missing_fields_contact_details_and_fit(self):
        problems, _ = self.check(card(Time="", Price="", Venue="Call 07797 123456 or jo@example.com", **{"Fit note": "Probably not: corporate"}))
        text = " ".join(problems)
        for bit in ("No time", "No price", "email address or phone number", "probably not"):
            self.assertIn(bit, text)

    def test_duplicate_and_past(self):
        problems, _ = self.check(card(2, title="Sea shanty night!"), others=[card(1)])
        self.assertIn("Looks like a duplicate of #1", problems)
        self.assertIn("The date has already passed", self.check(card(Date="2026-10-01"))[0])

    def test_date_formats(self):
        day = dt.date(2026, 11, 20)
        for page in ["20 Nov 2026", "November 20th", "2026-11-20T19:00", "Fri 20/11/2026"]:
            self.assertTrue(date_on_page(day, page), page)
        self.assertFalse(date_on_page(day, "21 November"))


if __name__ == "__main__":
    unittest.main()
