"""Pre-check the pending event cards so only the ones with a problem need a close look.

Each pending card gets the label "ready" or "check", and one comment saying what was checked
and what (if anything) looks wrong. A card is only re-checked when its text changes, or once a
day for the date. Nothing here approves a card: that stays a person's call.
"""
import argparse
import datetime as dt
import hashlib
import html
import re
import urllib.error
import urllib.request

from event_card import CATEGORIES, MONTHS, GitHub, parse_body, to_event, value, yes

MARK = "<!-- sc-review"
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"(?<![\w/.=-])(?:\+44\s?|0)(?:\d[\s-]?){9,10}\b")
UA = "Mozilla/5.0 (compatible; SocialCirclesCardCheck/1.0; +https://socialcircles.je)"


def fetch(url):
    """(status, page text). Status 0 when the site couldn't be reached at all."""
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-GB,en"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, r.read(2_000_000).decode("utf-8", "replace")
    except urllib.error.HTTPError as err:
        return err.code, ""
    except Exception:
        return 0, ""


def date_on_page(day, page):
    """Does the page mention this date in any of the usual ways?"""
    text = html.unescape(re.sub(r"<[^>]+>", " ", page)).lower()
    months = [name for name, i in MONTHS.items() if i == day.month]
    pats = [day.isoformat(), f"{day.day}/{day.month}/", f"{day.day:02d}/{day.month:02d}/", f"{day.day}.{day.month}."]
    pats += [rf"\b{day.day}(?:st|nd|rd|th)?\s+(?:of\s+)?{m}\b" for m in months] + [rf"\b{m}\.?\s+{day.day}(?:st|nd|rd|th)?\b" for m in months]
    return any(re.search(p if p.startswith("\\") else re.escape(p), text) for p in pats) or day.isoformat() in page


def norm(title):
    return re.sub(r"[^a-z0-9]+", " ", (title or "").lower()).strip()


def review(issue, others, today, fetcher=fetch):
    """-> (problems, notes). Problems earn the "check" label; notes are just said."""
    f, problems, notes = parse_body(issue["body"]), [], []
    e, missing = to_event(issue["title"], issue["body"], today)
    problems += ["Fix " + m for m in missing]
    if e:
        last = dt.date.fromisoformat(max([e.get("end", e["d"])] + e.get("dates", [])))
        if last < today:
            problems.append("The date has already passed")
        if e["cat"] not in CATEGORIES:
            problems.append(f"The category \"{e['cat']}\" isn't one the site filters by")
        twins = [o["number"] for o in others if o["number"] != issue["number"] and norm(o["title"]) == norm(issue["title"])
                 and parse_body(o["body"]).get("Date", "").strip()[:10] == f.get("Date", "").strip()[:10]]
        if twins:
            problems.append("Looks like a duplicate of " + ", ".join(f"#{n}" for n in twins))
    for heading in ("Time", "Link"):
        if not value(f.get(heading)):
            problems.append(f"No {heading.lower()}")
    if not value(f.get("Price")) and not yes(f.get("Free")):
        problems.append("No price, and it isn't marked free")
    public = "\n".join(v for k, v in f.items() if k != "Source")
    if EMAIL.search(public) or PHONE.search(public):
        problems.append("Has an email address or phone number on it (the card is public): remove it")
    fit = value(f.get("Fit note"))
    if fit.lower().startswith("probably not"):
        problems.append("Fit note says probably not: " + fit)
    if yes(f.get("Sold out")):
        notes.append("Marked sold out")
    url = (e or {}).get("url")
    if url:
        status, page = fetcher(url)
        if status in (404, 410) or status == 0:
            problems.append(f"The link doesn't open ({'no response' if not status else status})")
        elif status >= 400 or not page:
            notes.append("The link's site didn't let me read it, so I couldn't check the date there")
        elif e and not date_on_page(dt.date.fromisoformat(e["d"]), page):
            problems.append(f"I couldn't find {dt.date.fromisoformat(e['d']).strftime('%a %-d %b')} on the event page: check the date")
        else:
            notes.append("The date matches the event page")
    return problems, notes


def comment(problems, notes, digest):
    if problems:
        text = "**Worth a look before approving:**\n" + "\n".join(f"- {p}" for p in problems)
    else:
        text = "**Looks ready.** Name, date, venue, organiser, time, price and link are all filled in, with no contact details and no duplicate."
    if notes:
        text += "\n\n" + "\n".join(f"- {n}" for n in notes)
    return f"{text}\n\n_Checked automatically; approving is still your call._\n\n{MARK}:{digest} -->"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="print what each card would get, change nothing")
    args = ap.parse_args()
    gh, today = GitHub(), dt.date.today()
    if not args.dry_run:
        gh.ensure_labels()
    cards = gh.issues(labels="pending")
    others = cards + gh.issues(labels="approved")
    for issue in cards:
        names = {l["name"] for l in issue["labels"]}
        if "approved" in names:
            continue
        digest = hashlib.sha1(f"{issue['title']}\n{issue['body']}\n{today}".encode()).hexdigest()[:12]
        problems, notes = review(issue, others, today)
        if args.dry_run:
            print(f"#{issue['number']} {issue['title']}: {'check' if problems else 'ready'}", *problems, *notes, sep="\n  ")
            continue
        comments = gh.call("GET", f"/repos/{gh.repo}/issues/{issue['number']}/comments?per_page=100")
        old = next((c for c in comments if MARK in c["body"]), None)
        if old and f"{MARK}:{digest}" in old["body"]:
            continue
        body = comment(problems, notes, digest)
        if old:
            gh.call("PATCH", f"/repos/{gh.repo}/issues/comments/{old['id']}", {"body": body})
        else:
            gh.call("POST", f"/repos/{gh.repo}/issues/{issue['number']}/comments", {"body": body})
        want, drop = ("check", "ready") if problems else ("ready", "check")
        if drop in names:
            gh.call("DELETE", f"/repos/{gh.repo}/issues/{issue['number']}/labels/{drop}")
        if want not in names:
            gh.call("POST", f"/repos/{gh.repo}/issues/{issue['number']}/labels", {"labels": [want]})
        print(f"#{issue['number']}: {want}")


if __name__ == "__main__":
    main()
