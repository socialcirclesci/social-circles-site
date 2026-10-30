"""Build site/events.json from the approved event cards, and keep the review queue tidy.

Run by the publish workflow. Only open cards labelled "approved" are published, and only
cards written by the repository's owner or collaborators, or by this repository's own
workflows: anyone can open an issue on a public repository and edit what they wrote.
"""
import argparse
import datetime as dt
import json

from event_card import GitHub, to_event
from makers import index, to_maker
from pages import build, slug
from seo import inject

TRUSTED = {"OWNER", "MEMBER", "COLLABORATOR"}
CHECK = "<!-- sc-check -->"


def trusted(issue):
    return issue.get("author_association") in TRUSTED or issue["user"]["login"] == "github-actions[bot]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="site/events.json")
    ap.add_argument("--html", help="page to build the events' search-engine data into, e.g. site/index.html")
    ap.add_argument("--pages", help="site folder to build a page per event, the weekend page and the sitemap into, e.g. site")
    ap.add_argument("--tidy", action="store_true", help="comment on cards that can't be read and close finished ones")
    args = ap.parse_args()
    gh, today = GitHub(), dt.date.today()
    if args.tidy:
        gh.ensure_labels()

    events = []
    for issue in gh.issues(labels="approved"):
        if any(l["name"] == "maker" for l in issue["labels"]):  # Meet the maker answers, read below
            continue
        if not trusted(issue):
            print(f"#{issue['number']}: skipped, written by someone outside the project")
            continue
        e, problems = to_event(issue["title"], issue["body"], today)
        if problems:
            print(f"#{issue['number']}: not published, check " + "; ".join(problems))
            if args.tidy:
                note(gh, issue, problems)
            continue
        last = dt.date.fromisoformat(max([e.get("end", e["d"])] + e.get("dates", [])))
        if last < today - dt.timedelta(days=1):
            if args.tidy:
                gh.call("POST", f"/repos/{gh.repo}/issues/{issue['number']}/comments", {"body": "This event has finished, so I've taken it off the site and closed the card."})
                gh.call("PATCH", f"/repos/{gh.repo}/issues/{issue['number']}", {"state": "closed", "state_reason": "completed"})
            continue
        e["id"] = issue["number"]
        events.append(e)

    if args.tidy:  # pending cards for events that have already happened
        for issue in gh.issues(labels="pending"):
            if any(l["name"] in ("approved", "maker") for l in issue["labels"]):
                continue
            e, _ = to_event(issue["title"], issue["body"], today)
            if e and dt.date.fromisoformat(max([e.get("end", e["d"])] + e.get("dates", []))) < today - dt.timedelta(days=1):
                gh.call("PATCH", f"/repos/{gh.repo}/issues/{issue['number']}", {"state": "closed", "state_reason": "not_planned"})

    events.sort(key=lambda e: (e["d"], e["t"].lower()))
    if args.pages:
        for e in events:
            e["page"] = f"events/{slug(e)}/"
    with open(args.out, "w") as f:
        json.dump({"generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "events": events}, f, ensure_ascii=False, indent=1)
    if args.html:
        with open(args.html) as f:
            page = f.read()
        with open(args.html, "w") as f:
            f.write(inject(page, events))
    if args.pages:
        makers = [to_maker(i["title"], i["body"]) for i in gh.issues(labels="maker,approved") if trusted(i)]
        build(args.pages, events, today, index(m for m in makers if m))
    print(f"{len(events)} events published")


def note(gh, issue, problems):
    """Tell the card once that it can't go live yet, and why."""
    comments = gh.call("GET", f"/repos/{gh.repo}/issues/{issue['number']}/comments?per_page=100")
    text = "This one is approved but can't go on the site until you fix " + ", and ".join(problems) + ". Edit the card and it'll go live a minute later."
    old = next((c for c in comments if CHECK in c["body"]), None)
    if old and text in old["body"]:
        return
    body = f"{text}\n\n{CHECK}"
    if old:
        gh.call("PATCH", f"/repos/{gh.repo}/issues/comments/{old['id']}", {"body": body})
    else:
        gh.call("POST", f"/repos/{gh.repo}/issues/{issue['number']}/comments", {"body": body})


if __name__ == "__main__":
    main()
