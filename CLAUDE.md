# Social Circles website

Static site in `site/` served by GitHub Pages. Events are GitHub issues ("event cards"); the publish workflow turns open cards labelled `approved` into `site/events.json`. Read `README.md` for the review flow.

Social Circles is a connector for Jersey's creative community, not an event company: listings are always other people's events, credited "By <organiser>". Never make them look like Social Circles events.

## Event card format

Title = the event name. Body = the headings in `FIELDS` in `scripts/event_card.py`, each `### Heading`, a blank line, then the value (`_No response_` when empty). Build bodies with `format_body` when you can. Dates as `YYYY-MM-DD`. Category must be one of `CATEGORIES`. "Source" and "Fit note" are never published.

## Twice-weekly event search

When asked to run the event search:

1. List the open and the last 200 closed issues so you don't add duplicates. Treat an event as a duplicate when the name and date match a card already there, even if the wording differs.
2. Search these sources for events from today to six weeks ahead:
   - jerseyheritage.org/explore/whats-on
   - jersey.com/things-to-do/events/ (open each listing for time and venue)
   - localevents.je
   - channeleye.media/events-jersey/
   - artscentre.je
   - islandtickethut.com
   - Eventbrite: eventbrite.com/b/jersey/music/ and eventbrite.co.uk/d/jersey--jersey/events/ (open each event page to confirm the date; listing pages are often stale)
   - watersplashjersey.com/events/whats-on/ (often only food offers; check jersey.com for their nights)
   - The Wellbeing Hub, 19 Commercial Buildings, St Helier: app.wellbeinghub.je/suite/organizations/134f8bc6-ea43-4905-929c-b67d1c75b9ec (an app page that may not load without a browser; if you can't read it, say so in the summary rather than guessing)
   - Her Code JSY: hercodejsy.my.canva.site (a Canva site that may not load without a browser; she posts most events on Instagram @hercodejsy, so Nikita sends those as screenshots)
   Instagram and Facebook block automated reading, so skip them.
3. For each new event, open one issue with labels `pending` and `found`. Fill every field you can confirm from the page; leave the rest as `_No response_`. Set "Source" to the page URL. Never add the `approved` label: Nikita approves everything herself.
4. Write a one-line "Fit note" starting "Strong fit", "Maybe" or "Probably not", with the reason. Strong fits are small, independent, creative or social events where people can meet others: gigs, makers' markets, workshops, supper clubs, art, heritage walks, wellbeing, outdoor meet-ups. Probably not: corporate conferences, private functions, chain promotions, anything aimed only at under-18s.
5. Don't create cards for events that have already happened, and never put a person's email or phone number on a card: the repository is public.
6. Finish with a one-line summary: how many cards you added, how many strong fits, and anything you couldn't check.

## Site rules from Nikita

- Accessible colours: no tomato orange for small text; tomato only for buttons with dark text and shapes. Small accent text is violet on light and lilac on dark.
- Photos: never minors, and no supper-club guests (hosts, food and tables are fine).
- "Stay curious" is only ever a sign-off, never a headline.
