# Social Circles website

The Social Circles site: Jersey's creative community in one place.

## How events get on the site

Every event is a card in this repository's [Issues](../../issues) tab.

- **Claude's search** (Monday and Thursday mornings) adds new events it finds, labelled `pending` and `found`.
- **The "Add an event" form** on the site adds what people send in, labelled `pending` and `submitted`, within the hour.
- **You can add one yourself** with New issue → Event.

Every pending card is pre-checked within the hour and labelled **`ready`** (nothing looks wrong) or **`check`** (a comment on the card says what to look at: a missing time, price or link, a link that doesn't open, a date that's passed or isn't on the event page, a duplicate, contact details, or a "Probably not" fit). Filter by `check` to see only the ones that need you.

To review a card (the GitHub phone app works well for this):

| To | Do this |
| --- | --- |
| Fix a detail | Edit the card's text (the ⋯ menu → Edit) |
| Put it on the site | Add the `approved` label |
| Take it off the site | Remove the `approved` label, or close the card |
| Reject it | Close the card |
| Make it a weekend pick | Set "Weekend pick" to Yes and write a short "Pick blurb" |
| Something on more than once | Set "Repeats" to Daily, Every Friday, or the other dates (like 30 Oct, 6 Nov). It stops at the "End date" if there is one |
| Something on for several days | Set the "End date". Exhibitions and anything running over a week show under "Running now" at the top of the list |

The site updates a minute or two after you approve. Finished events come off by themselves the next morning and their cards close.

## Settings

- **Tally forms** go in `FORMS` at the top of the script in `site/index.html` (the part of the link after `tally.so/r/`).
- **Tally import** needs the `TALLY_API_KEY` secret (Settings → Secrets and variables → Actions). The "Add an event" form id is set in `.github/workflows/tally.yml`; a `TALLY_SUBMIT_FORM_ID` variable overrides it.
- **Your domain** goes in Settings → Pages → Custom domain.

## For developers

- `site/` is the whole website, plain HTML with no build step. `events.json` is generated on deploy.
- `scripts/event_card.py` reads and writes the card format; `scripts/build_events.py` builds `events.json`; `scripts/tally_to_cards.py` imports Tally submissions; `scripts/review_cards.py` pre-checks pending cards.
- Tests: `python3 -m unittest discover -s tests`.
