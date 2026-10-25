import datetime as dt
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from event_card import format_body, parse_date, to_event  # noqa: E402
from tally_to_cards import heading_for, text  # noqa: E402

TODAY = dt.date(2026, 10, 25)


class Dates(unittest.TestCase):
    def test_formats(self):
        for raw in ["2026-11-12", "12/11/2026", "12 Nov 2026", "Thu 12 Nov 2026", "12th November 2026", "Thu 12 Nov", "12.11.26"]:
            self.assertEqual(parse_date(raw, TODAY), dt.date(2026, 11, 12), raw)

    def test_next_year_without_year(self):
        self.assertEqual(parse_date("9 Jan", TODAY), dt.date(2027, 1, 9))

    def test_empty_and_bad(self):
        for raw in ["", "_No response_", "soon", "31/02/2026"]:
            self.assertIsNone(parse_date(raw, TODAY), raw)


class Cards(unittest.TestCase):
    def card(self, **kw):
        fields = {"Date": "2026-11-12", "Time": "5:30pm", "Venue": "Springfield, St Helier", "Organiser": "Jersey Heritage",
                  "Price": "£16", "Category": "heritage", "Free": "No", "Link": "jerseyheritage.org/visit", "Type": "Event",
                  "Weekend pick": "No", "Season": "None", "Sold out": "No", "Source": "jerseyheritage.org", "Fit note": "Strong fit"}
        fields.update(kw)
        return format_body(fields, "<!-- tally:abc -->")

    def test_round_trip(self):
        e, problems = to_event("Cold War Bunker Tour", self.card(), TODAY)
        self.assertEqual(problems, [])
        self.assertEqual(e, {"d": "2026-11-12", "t": "Cold War Bunker Tour", "by": "Jersey Heritage", "at": "Springfield, St Helier",
                             "time": "5:30pm", "price": "£16", "cat": "Heritage", "url": "https://jerseyheritage.org/visit"})

    def test_private_fields_stay_off_the_site(self):
        e, _ = to_event("x", self.card(), TODAY)
        self.assertNotIn("Strong fit", str(e))
        self.assertNotIn("jerseyheritage.org\"", str(e))

    def test_flags(self):
        e, _ = to_event("Winter market", self.card(**{"End date": "15 Nov 2026", "Free": "Yes", "Weekend pick": "Yes",
                                                    "Pick blurb": "Stalls by the sea.", "Season": "Christmas", "Type": "Exhibition"}), TODAY)
        self.assertEqual((e["end"], e["free"], e["pick"], e["blurb"], e["season"], e["type"]),
                         ("2026-11-15", True, True, "Stalls by the sea.", "christmas", "exhibition"))

    def test_problems_block_publishing(self):
        e, problems = to_event("Gig", self.card(Date="next week", Venue="_No response_"), TODAY)
        self.assertIsNone(e)
        self.assertEqual(len(problems), 2)

    def test_end_before_start_is_dropped(self):
        e, problems = to_event("Gig", self.card(**{"End date": "2026-11-01"}), TODAY)
        self.assertIsNone(e)
        self.assertIn("End date", problems[0])

    def test_issue_form_body(self):
        body = "### Date\n\n12 Nov 2026\n\n### End date\n\n_No response_\n\n### Venue\n\nThe Drift\n\n### Organiser\n\nIsland Music\n\n### Category\n\nMusic\n"
        e, problems = to_event("Bruce Foxton", body, TODAY)
        self.assertEqual(problems, [])
        self.assertEqual((e["d"], e["at"], e["cat"]), ("2026-11-12", "The Drift", "Music"))


class Tally(unittest.TestCase):
    def test_headings(self):
        cases = {"Event name": "_title", "Date of the event": "Date", "End date (if it runs over several days)": "End date",
                 "Start time": "Time", "Venue": "Venue", "Who's running it?": "Organiser", "Organiser name": "Organiser",
                 "Ticket link": "Link", "Price": "Price", "Category": "Category", "Your email": None, "Tell us about it": "_about"}
        for title, heading in cases.items():
            self.assertEqual(heading_for(title), heading, title)

    def test_option_ids_become_titles(self):
        self.assertEqual(text(["u1", "u2"], {"u1": "Music", "u2": "Art"}), "Music, Art")
        self.assertEqual(text("2026-11-12", {}), "2026-11-12")


if __name__ == "__main__":
    unittest.main()
