"""The event card format shared by the GitHub issue form, the Tally import and the site build.

An event card is a GitHub issue. Its title is the event name and its body is a list of
"### Field" headings, each followed by the value, which is what GitHub issue forms produce.
"""
import calendar
import datetime as dt
import json
import os
import re
import urllib.error
import urllib.request

# heading in the card -> key in events.json (None = kept on the card only, never published)
FIELDS = [
    ("Date", "d"),
    ("End date", "end"),
    ("Repeats", "repeat"),
    ("Time", "time"),
    ("Venue", "at"),
    ("Organiser", "by"),
    ("Price", "price"),
    ("Category", "cat"),
    ("Free", "free"),
    ("Link", "url"),
    ("Button text", "link"),
    ("Type", "type"),
    ("Weekend pick", "pick"),
    ("Pick blurb", "blurb"),
    ("Season", "season"),
    ("Sold out", "out"),
    ("Source", None),
    ("Fit note", None),
]
CATEGORIES = ["Music", "Art", "Workshops", "Markets", "Food & drink", "Outdoors", "Wellbeing", "Heritage", "Family"]
LABELS = {
    "pending": ("C3B2F7", "Waiting for review"),
    "approved": ("2DA44E", "Live on the site"),
    "found": ("7B4DFF", "Found by the twice-weekly search"),
    "submitted": ("FF5B2E", "Sent in through the website form"),
}
EMPTY = {"", "_no response_", "none", "n/a", "-", "tbc"}


def parse_body(body):
    """Return {heading: value} from a card body."""
    out, current, lines = {}, None, []
    for line in (body or "").replace("\r\n", "\n").split("\n"):
        m = re.match(r"^#{2,4}\s+(.+?)\s*$", line)
        if m:
            if current:
                out[current] = "\n".join(lines).strip()
            current, lines = m.group(1).strip(), []
        elif current and not line.lstrip().startswith("<!--"):
            lines.append(line)
    if current:
        out[current] = "\n".join(lines).strip()
    return out


def value(raw):
    v = (raw or "").strip()
    return "" if v.lower() in EMPTY else v


def yes(raw):
    return value(raw).lower() in {"yes", "y", "true", "x", "[x]"}


MONTHS = {name.lower(): i for i, name in enumerate(calendar.month_abbr) if name}
MONTHS.update({name.lower(): i for i, name in enumerate(calendar.month_name) if name})


def parse_date(raw, today=None):
    """Read the date formats people actually type. Returns a date or None."""
    v = value(raw)
    if not v:
        return None
    today = today or dt.date.today()
    v = re.sub(r"(\d)(st|nd|rd|th)\b", r"\1", v.lower()).replace(",", " ")
    m = re.search(r"(\d{4})-(\d{1,2})-(\d{1,2})", v)
    if m:
        return _date(int(m[1]), int(m[2]), int(m[3]))
    m = re.search(r"\b(\d{1,2})[/.](\d{1,2})[/.](\d{2,4})\b", v)  # UK order: day/month/year
    if m:
        y = int(m[3]) + (2000 if len(m[3]) == 2 else 0)
        return _date(y, int(m[2]), int(m[1]))
    m = re.search(r"\b(\d{1,2})\s+([a-z]+)\.?(?:\s+(\d{4}))?", v)
    if m and m[2] in MONTHS:
        if m[3]:
            return _date(int(m[3]), MONTHS[m[2]], int(m[1]))
        d = _date(today.year, MONTHS[m[2]], int(m[1]))
        if d and d < today - dt.timedelta(days=60):  # "12 Jan" typed in November means next year
            d = _date(today.year + 1, MONTHS[m[2]], int(m[1]))
        return d
    return None


def _date(y, m, d):
    try:
        return dt.date(y, m, d)
    except ValueError:
        return None


DAYS = [d.lower() for d in calendar.day_name]
AHEAD = 84  # how far ahead a repeating event is listed (the site rebuilds every morning)


def repeats(raw, start, end, today):
    """Expand the Repeats field into ("daily" | "weekly" | "dates", [dates from today on]), or None.

    "Daily", "Weekly", "Every Friday" or "Every Tue and Thu" repeat until the End date (or 12 weeks
    ahead); anything with numbers in it is read as a list of extra dates, like "30 Oct, 6 Nov".
    """
    v = value(raw).lower()
    if not v or not start:
        return None
    first, last = max(start, today), min(end or today + dt.timedelta(days=AHEAD), today + dt.timedelta(days=AHEAD))
    span = [first + dt.timedelta(days=i) for i in range((last - first).days + 1)]
    if re.search(r"\b(daily|every ?day)\b", v):
        return "daily", span
    if re.search(r"\d", v):  # dates, which may name their weekday ("Fri 30 Oct")
        dates = {start} | {d for d in (parse_date(part, today) for part in re.split(r"[,;&+\n]|\band\b", v)) if d}
        return "dates", sorted(d for d in dates if d >= today)
    days = {i for i, name in enumerate(DAYS) if re.search(rf"\b{name[:3]}(?!th)", v)}
    if days or re.search(r"\b(weekly|every week)\b", v):
        days = days or {start.weekday()}
        return "weekly", [d for d in span if d.weekday() in days]
    return None


def category(raw):
    v = value(raw)
    for c in CATEGORIES:
        if v.lower() == c.lower() or v.lower().replace("and", "&") == c.lower():
            return c
    return v


def to_event(title, body, today=None):
    """Card -> (event dict, list of problems). The event is None when it can't be published."""
    f = parse_body(body)
    problems = []
    d = parse_date(f.get("Date"), today)
    end = parse_date(f.get("End date"), today)
    if not d:
        problems.append("the **Date** (write it like 2026-11-12 or 12 Nov 2026)")
    if end and d and end < d:
        problems.append("the **End date**, which is before the start date")
        end = None
    for heading in ("Venue", "Organiser"):
        if not value(f.get(heading)):
            problems.append(f"the **{heading}**, which is empty")
    url = value(f.get("Link"))
    if url and not re.match(r"^https?://", url):
        url = "https://" + url if "." in url and " " not in url else ""
    season = value(f.get("Season")).lower()
    e = {
        "d": d.isoformat() if d else "",
        "t": re.sub(r"^\[[^\]]*\]\s*", "", title or "").strip(),
        "by": value(f.get("Organiser")),
        "at": value(f.get("Venue")),
        "time": value(f.get("Time")),
        "price": value(f.get("Price")),
        "cat": category(f.get("Category")) or "Events",
        "url": url,
    }
    if end and end != d:
        e["end"] = end.isoformat()
    rep = repeats(f.get("Repeats"), d, end, today or dt.date.today())
    if rep and rep[1]:
        e["repeat"], e["dates"] = rep[0], [x.isoformat() for x in rep[1]]
        e.pop("end", None)  # the dates say when it's on
    if yes(f.get("Free")) or re.match(r"free\b", e["price"], re.I):
        e["free"] = True
    if value(f.get("Button text")):
        e["link"] = value(f.get("Button text"))
    if value(f.get("Type")).lower().startswith("exhib"):
        e["type"] = "exhibition"
    if yes(f.get("Weekend pick")):
        e["pick"] = True
    if value(f.get("Pick blurb")):
        e["blurb"] = value(f.get("Pick blurb"))
    if season in ("halloween", "christmas"):
        e["season"] = season
    if yes(f.get("Sold out")):
        e["out"] = True
    if not e["t"]:
        problems.append("the event name (the card's title)")
    return (None if problems else e), problems


def format_body(fields, marker=""):
    """{heading: value} -> card body in the same layout as the issue form."""
    parts = []
    for heading, _ in FIELDS:
        v = str(fields.get(heading) or "").strip()
        parts.append(f"### {heading}\n\n{v or '_No response_'}")
    if marker:
        parts.append(marker)
    return "\n\n".join(parts) + "\n"


class GitHub:
    """Just enough of the GitHub REST API, with the workflow's token."""

    def __init__(self, repo=None, token=None):
        self.repo = repo or os.environ["GITHUB_REPOSITORY"]
        self.token = token or os.environ["GITHUB_TOKEN"]

    def call(self, method, path, data=None):
        url = path if path.startswith("http") else f"https://api.github.com{path}"
        req = urllib.request.Request(url, method=method, data=json.dumps(data).encode() if data is not None else None)
        req.add_header("Authorization", f"Bearer {self.token}")
        req.add_header("Accept", "application/vnd.github+json")
        req.add_header("X-GitHub-Api-Version", "2022-11-28")
        with urllib.request.urlopen(req) as r:
            body = r.read()
            return json.loads(body) if body else None

    def issues(self, state="open", labels=""):
        page, out = 1, []
        while True:
            batch = self.call("GET", f"/repos/{self.repo}/issues?state={state}&labels={labels}&per_page=100&page={page}")
            out += [i for i in batch if "pull_request" not in i]
            if len(batch) < 100:
                return out
            page += 1

    def ensure_labels(self):
        have = {l["name"] for l in self.call("GET", f"/repos/{self.repo}/labels?per_page=100")}
        for name, (color, desc) in LABELS.items():
            if name not in have:
                try:
                    self.call("POST", f"/repos/{self.repo}/labels", {"name": name, "color": color, "description": desc})
                except urllib.error.HTTPError as err:
                    print(f"couldn't create label {name}: {err}")
