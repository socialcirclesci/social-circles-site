"""Structured data for search engines: the listed events as schema.org Events, built into the page.

Google reads this to show events in its "events near me" results. Every event is credited to
its own organiser; Social Circles is only the site listing it.
"""
import datetime as dt
import json
import re
from zoneinfo import ZoneInfo

SITE = "https://socialcircles.je/"
JERSEY = ZoneInfo("Europe/Jersey")
MARK = re.compile(r'<script type="application/ld\+json" id="ld-events">.*?</script>', re.S)


def start_time(day, text):
    """'7:30pm', '6–7:15pm' or '10am' -> an aware datetime; None when the time isn't a plain start time."""
    m = re.match(r"\s*(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", text or "", re.I)
    if not m:
        return None
    meridiem = m[3] or (re.search(r"(am|pm)", text[m.end():], re.I) or [None, None])[1]
    if not meridiem:
        return None
    hour = int(m[1]) % 12 + (12 if meridiem.lower() == "pm" else 0)
    if hour > 23 or int(m[2] or 0) > 59:
        return None
    return dt.datetime(day.year, day.month, day.day, hour, int(m[2] or 0), tzinfo=JERSEY)


def price(e):
    if e.get("free") or e.get("price", "").strip().lower().startswith("free"):
        return "0"
    m = re.search(r"£\s*(\d+(?:\.\d{2})?)", e.get("price", ""))
    return m[1] if m else None


def event_ld(e):
    day = dt.date.fromisoformat(e["d"])
    start = start_time(day, e.get("time"))
    out = {
        "@type": "Event",
        "name": e["t"],
        "startDate": start.isoformat() if start else e["d"],
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        "eventStatus": "https://schema.org/EventScheduled",
        "location": {"@type": "Place", "name": e["at"],
                     "address": {"@type": "PostalAddress", "streetAddress": e["at"], "addressRegion": "Jersey", "addressCountry": "JE"}},
        "organizer": {"@type": "Organization", "name": e["by"]},
    }
    if e.get("end") and e["end"] != e["d"]:
        out["endDate"] = e["end"]
    if e.get("blurb"):
        out["description"] = e["blurb"]
    if e.get("url"):
        out["url"] = e["url"]
    offer = {"@type": "Offer", "priceCurrency": "GBP", "availability": "https://schema.org/SoldOut" if e.get("out") else "https://schema.org/InStock"}
    if price(e) is not None:
        offer["price"] = price(e)
    if e.get("url"):
        offer["url"] = e["url"]
    if len(offer) > 3 or e.get("out"):
        out["offers"] = offer
    return out


def page_ld(events):
    site = {"@type": "WebSite", "@id": SITE + "#site", "name": "Social Circles", "url": SITE,
            "description": "What's on in Jersey: gigs, markets, workshops, supper clubs and more from local organisers."}
    org = {"@type": "Organization", "@id": SITE + "#org", "name": "Social Circles", "url": SITE,
           "logo": SITE + "img/icon.png", "sameAs": ["https://www.instagram.com/socialcircles_ci/"]}
    return {"@context": "https://schema.org", "@graph": [site, org] + [event_ld(e) for e in events]}


def inject(html, events):
    """Put the structured data into the page, replacing what the last build put there."""
    data = json.dumps(page_ld(events), ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    tag = f'<script type="application/ld+json" id="ld-events">{data}</script>'
    if MARK.search(html):
        return MARK.sub(lambda _: tag, html, count=1)
    return html.replace("</head>", tag + "\n</head>", 1)
