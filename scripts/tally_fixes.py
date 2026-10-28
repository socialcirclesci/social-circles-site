"""Put "Fix a listing" reports from Tally on the event's card and label it "check".

Run every hour by the Tally workflow, after the event import. Needs the TALLY_API_KEY secret
and the "Fix a listing" form id; until both are set it does nothing. The reporter's email
stays in Tally (this repository is public), and so does anything that looks like contact details.
"""
import os
import re

from event_card import GitHub, to_event
from pages import slug
from tally_to_cards import tally, text

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"(?:\+44\s?|0)\d(?:[\s-]?\d){8,9}\b")


def clean(s):
    return PHONE.sub("[phone number removed]", EMAIL.sub("[email removed]", s or "")).strip()


def find_card(cards, page, name):
    """The card for this event: by its page address, or failing that by its name."""
    for issue in cards:
        e, _ = to_event(issue["title"], issue["body"])
        if e and page and page.strip("/").endswith(slug(e)):
            return issue
    name = re.sub(r"\W+", " ", (name or "").lower()).strip()
    return next((i for i in cards if name and re.sub(r"\W+", " ", i["title"].lower()).strip() == name), None)


def note(sub, fields, form):
    quoted = "\n".join("> " + line for line in clean(fields.get("what"))[:800].splitlines() or ["(no details)"])
    who = clean(fields.get("who"))[:120]
    reply = " They left an email for a reply." if fields.get("email") else ""
    return (f"**Someone flagged this listing** through the website on {sub.get('submittedAt', '')[:10]}{f' ({who})' if who else ''}:\n\n{quoted}\n\n"
            f"Fix the card if it's right, then remove the `check` label.{reply} Full report in Tally: https://tally.so/forms/{form}/submissions\n\n"
            f"<!-- tally-fix:{sub['id']} -->")


def main():
    key, form = os.environ.get("TALLY_API_KEY"), os.environ.get("TALLY_FIX_FORM_ID")
    if not key or not form:
        print("The Fix a listing form isn't connected yet. Nothing to do.")
        return
    gh = GitHub()
    gh.ensure_labels()
    cards = gh.issues(labels="approved")
    done = set()
    for issue in gh.issues(state="all"):  # every card a report has gone on, even once the label's off
        if issue.get("comments") and "pull_request" not in issue:
            for c in gh.call("GET", f"/repos/{gh.repo}/issues/{issue['number']}/comments?per_page=100"):
                done.update(re.findall(r"<!-- tally-fix:([\w-]+) -->", c["body"] or ""))

    page, posted = 1, 0
    while True:
        data = tally(f"/forms/{form}/submissions?filter=completed&limit=100&page={page}", key)
        questions = {q["id"]: q for q in data.get("questions", [])}
        options = {f["uuid"]: f["title"] for q in questions.values() for f in q.get("fields", []) if f.get("uuid") and f.get("title")}
        for sub in data.get("submissions", []):
            if sub["id"] in done:
                continue
            fields = {}
            for r in sub.get("responses", []):
                title = questions.get(r["questionId"], {}).get("title", "").lower()
                v = str(r.get("formattedAnswer") or text(r.get("answer"), options)).strip()
                kind = ("email" if "mail" in title else "page" if title == "page" else "event" if title == "event"
                        else "who" if re.search(r"name|organi[sz]", title) else "what")
                if v:
                    fields.setdefault(kind, v)
            issue = find_card(cards, fields.get("page"), fields.get("event"))
            if not issue:
                print(f"{sub['id']}: no live card matches {fields.get('event')!r}; it's in Tally")
                continue
            gh.call("POST", f"/repos/{gh.repo}/issues/{issue['number']}/comments", {"body": note(sub, fields, form)})
            gh.call("POST", f"/repos/{gh.repo}/issues/{issue['number']}/labels", {"labels": ["check"]})
            done.add(sub["id"])
            posted += 1
        if not data.get("hasMore"):
            break
        page += 1
    print(f"{posted} listing reports put on their cards")


if __name__ == "__main__":
    main()
