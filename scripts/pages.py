"""A page of its own for every listed event, a "this weekend" page and the sitemap, built at publish.

Search engines rank pages, not listings inside one page: a page per event can come up for
"winter market Jersey", and the weekend page for "things to do in Jersey this weekend".
Every event stays credited to its own organiser; Social Circles only lists it.
"""
import datetime as dt
import html
import json
import re
import shutil
import unicodedata
import urllib.parse
from pathlib import Path

from seo import SITE, event_ld

# the "Fix a listing" Tally form (the part after tally.so/r/); while it's empty the link isn't shown
FIX_FORM = ""
DOW, MON = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DAY = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTH = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
esc = lambda s: html.escape(str(s or ""), quote=True)


def short(d):
    return f"{DOW[d.weekday()]} {d.day} {MON[d.month - 1]}"


def long(d):
    return f"{DAY[d.weekday()]} {d.day} {MONTH[d.month - 1]}"


def slug(e):
    """'Winter Market' on 14 Nov -> 'winter-market-14-nov' (the date keeps repeat listings apart)."""
    words = unicodedata.normalize("NFKD", e["t"]).encode("ascii", "ignore").decode().lower()
    words = re.sub(r"[^a-z0-9]+", "-", re.sub(r"['’]", "", words).replace("&", " and ")).strip("-")[:60].strip("-")
    d = dt.date.fromisoformat(e["d"])
    return f"{words or 'event'}-{d.day}-{MON[d.month - 1].lower()}"


def days_on(e, today):
    """Every day it's on from today, as dates (long runs give their whole span)."""
    if e.get("dates"):
        return [dt.date.fromisoformat(x) for x in e["dates"]]
    start, end = dt.date.fromisoformat(e["d"]), dt.date.fromisoformat(e.get("end") or e["d"])
    return [start + dt.timedelta(days=i) for i in range((end - start).days + 1) if start + dt.timedelta(days=i) >= today]


def next_on(e, today, until=None):
    return next((d for d in days_on(e, today) if d >= today and (until is None or d <= until)), None)


def when(e, today):
    """'Sat 14 Nov, 10am', 'Every Fri, 8–8:45am' or 'Until Sat 7 Nov'."""
    start, end = dt.date.fromisoformat(e["d"]), dt.date.fromisoformat(e.get("end") or e["d"])
    if e.get("repeat") == "weekly":
        text = "Every " + " & ".join(dict.fromkeys(DOW[d.weekday()] for d in days_on(e, today)[:7]))
    elif e.get("repeat") == "daily":
        text = f"Daily until {short(days_on(e, today)[-1])}"
    elif e.get("dates"):
        text = ", ".join(short(d) for d in days_on(e, today) if d >= today)
    elif end > start:
        text = (f"Until {MON[end.month - 1]} {end.year}" if end > today + dt.timedelta(days=300) else f"Until {short(end)}") if start <= today else f"{short(start)} to {short(end)}"
    else:
        text = short(start)
    return text + (f", {e['time']}" if e.get("time") else "")


def head(title, description, path, extra=""):
    url = SITE + path
    return f"""<!doctype html>
<html lang="en-GB">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>{esc(title)}</title>
<meta name="description" content="{esc(description)}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="website">
<meta property="og:url" content="{url}">
<meta property="og:site_name" content="Social Circles">
<meta property="og:locale" content="en_GB">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(description)}">
<meta property="og:image" content="{SITE}img/about-mural.jpg">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#FFF6EA">
<link rel="icon" href="/img/icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Bricolage+Grotesque:opsz,wdth,wght@12..96,75..100,400..800&family=DM+Sans:wght@400;500;700&display=swap">
<link rel="stylesheet" href="/page.css">
{extra}</head>
<body>
<header class="top"><div class="wrap"><a href="/" aria-label="Social Circles home"><img src="/img/wordmark-aubergine.png" alt="Social Circles" width="140"></a><a class="btn btn-dark" href="/#whats-on">What's on</a></div></header>
<main class="wrap">
"""


FOOT = """</main>
<footer><div class="wrap"><img src="/img/wordmark-cream.png" alt="Social Circles" width="150"><p>What's on in Jersey, from local organisers. <a href="/">See everything</a> · <a href="https://www.instagram.com/socialcircles_ci/">Instagram</a> · <a href="/privacy.html">Privacy</a></p></div></footer>
</body>
</html>
"""


def ld(data):
    return '<script type="application/ld+json">' + json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + "</script>\n"


def card(e, today):
    """One event in a list, linking to its own page."""
    tags = [e["cat"]] + (["Free"] if e.get("free") else []) + (["Sold out"] if e.get("out") else [])
    return f"""<li class="item"><a href="/events/{slug(e)}/"><span class="by">By {esc(e['by'])}</span><b>{esc(e['t'])}</b>
  <span class="facts">{esc(when(e, today))} · {esc(e['at'])}</span>
  <span class="tags">{''.join(f'<span class="tag">{esc(t)}</span>' for t in tags)}</span></a></li>
"""


def fix_link(e):
    if not FIX_FORM:
        return ""
    query = urllib.parse.urlencode({"event": e["t"], "page": f"events/{slug(e)}/"})
    return f' <a href="https://tally.so/r/{FIX_FORM}?{esc(query)}">Something wrong with this listing?</a>'


def event_page(e, events, today):
    first = next_on(e, today) or dt.date.fromisoformat(e["d"])
    title = f"{e['t']}, {short(first)} · What's on in Jersey · Social Circles"
    desc = e.get("blurb") or f"{e['t']} by {e['by']} at {e['at']}, {when(e, today)}. Find it and more things to do in Jersey on Social Circles."
    crumbs = {"@context": "https://schema.org", "@type": "BreadcrumbList", "itemListElement": [
        {"@type": "ListItem", "position": 1, "name": "What's on in Jersey", "item": SITE},
        {"@type": "ListItem", "position": 2, "name": e["t"], "item": f"{SITE}events/{slug(e)}/"}]}
    out = head(title, desc[:300], f"events/{slug(e)}/", ld({"@context": "https://schema.org", **event_ld(e)}) + ld(crumbs))
    facts = [("When", when(e, today)), ("Where", e["at"])] + ([("Price", e["price"])] if e.get("price") else []) + [("Organiser", e["by"])]
    tags = [e["cat"]] + (["Exhibition"] if e.get("type") == "exhibition" else []) + (["Free"] if e.get("free") else []) + (["Sold out"] if e.get("out") else [])
    out += f"""<nav class="crumbs"><a href="/">What's on in Jersey</a> / <span>{esc(e['cat'])}</span></nav>
<article class="event">
  <span class="by">By {esc(e['by'])}</span>
  <h1>{esc(e['t'])}</h1>
  <div class="tags">{''.join(f'<span class="tag">{esc(t)}</span>' for t in tags)}</div>
  {f'<p class="intro">{esc(e["blurb"])}</p>' if e.get("blurb") else ""}
  <dl>{''.join(f'<dt>{k}</dt><dd>{esc(v)}</dd>' for k, v in facts)}</dl>
  <div class="actions">{f'<a class="btn btn-dark" href="{esc(e["url"])}">{esc(e.get("link") or "Tickets & info")}</a>' if e.get("url") else ""}{'' if e.get("out") else '<a class="btn btn-line" href="/#meetup">Find people to go with</a>'}</div>
  <p class="note">{esc(e['by'])} runs this event. Social Circles lists it so more people hear about it; tickets and details come from the organiser.{fix_link(e)}</p>
</article>
"""
    more = [x for x in events if x is not e and next_on(x, today)]
    more.sort(key=lambda x: (x["cat"] != e["cat"], next_on(x, today)))
    if more:
        out += f'<section class="more"><h2>More on<br><span class="v">in Jersey</span></h2><ul class="list">{"".join(card(x, today) for x in more[:6])}</ul><p><a class="btn btn-line" href="/this-weekend/">This weekend in Jersey</a> <a class="btn btn-line" href="/#whats-on">See everything</a></p></section>\n'
    return out + FOOT


def weekend(today):
    """Friday to Sunday: this one, or what's left of it."""
    fri = today + dt.timedelta(days=(4 - today.weekday()) % 7 if today.weekday() < 5 else -(today.weekday() - 4))
    return max(fri, today), fri + dt.timedelta(days=2)


def weekend_page(events, today):
    start, end = weekend(today)
    dates = f"{short(start)} to {short(end)}" if start < end else short(end)
    days = [start + dt.timedelta(days=i) for i in range((end - start).days + 1)]
    on = [e for e in events if next_on(e, start, end)]
    running = [e for e in on if not e.get("dates") and dt.date.fromisoformat(e["d"]) < start]
    title = f"Things to do in Jersey this weekend ({dates}) · Social Circles"
    names = ", ".join(e["t"] for e in on[:4])
    desc = f"What's on in Jersey this weekend, {dates}: {len(on)} gigs, markets, workshops and more from local organisers" + (f", including {names}." if names else ".")
    items = {"@context": "https://schema.org", "@type": "ItemList", "name": f"Things to do in Jersey this weekend ({dates})",
             "itemListElement": [{"@type": "ListItem", "position": i + 1, "url": f"{SITE}events/{slug(e)}/"} for i, e in enumerate(on)]}
    out = head(title, desc[:300], "this-weekend/", ld(items))
    out += f"""<section class="hero"><span class="eyebrow">{esc(dates)}</span><h1>This weekend<br><span class="v">in Jersey</span></h1>
<p class="intro">Gigs, markets, workshops and things to do around the island this weekend, from local organisers. Updated every morning.</p></section>
"""
    if not on:
        out += '<p class="empty">Nothing listed for this weekend yet. <a href="/#whats-on">See everything coming up</a>.</p>\n'
    if running:
        out += f'<section class="day"><h2 class="date">On all weekend</h2><ul class="list">{"".join(card(e, today) for e in running)}</ul></section>\n'
    for d in days:
        here = [e for e in on if e not in running and next_on(e, start, end) == d]
        if here:
            out += f'<section class="day"><h2 class="date">{long(d)}</h2><ul class="list">{"".join(card(e, today) for e in here)}</ul></section>\n'
    out += '<p class="cta"><a class="btn btn-dark" href="/#whats-on">See everything coming up</a> <a class="btn btn-line" href="/#meetup">Find people to go with</a></p>\n'
    return out + FOOT


def sitemap(events, today):
    urls = [(SITE, "daily"), (SITE + "this-weekend/", "daily")] + [(f"{SITE}events/{slug(e)}/", "weekly") for e in events] + [(SITE + "privacy.html", "yearly")]
    rows = "".join(f"  <url><loc>{u}</loc><changefreq>{f}</changefreq></url>\n" for u, f in urls)
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{rows}</urlset>\n'


def build(site, events, today=None):
    """Write site/events/<slug>/, site/this-weekend/ and site/sitemap.xml from the published events."""
    today, site = today or dt.date.today(), Path(site)
    shutil.rmtree(site / "events", ignore_errors=True)  # finished events drop off with their pages
    for e in events:
        page = site / "events" / slug(e) / "index.html"
        page.parent.mkdir(parents=True, exist_ok=True)
        page.write_text(event_page(e, events, today))
    (site / "this-weekend").mkdir(exist_ok=True)
    (site / "this-weekend" / "index.html").write_text(weekend_page(events, today))
    (site / "sitemap.xml").write_text(sitemap(events, today))
