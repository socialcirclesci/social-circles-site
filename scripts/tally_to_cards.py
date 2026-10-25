"""Turn new "Add an event" submissions from Tally into pending event cards.

Run every hour by the Tally workflow. Needs the TALLY_API_KEY secret and the
TALLY_SUBMIT_FORM_ID variable; until both are set it does nothing. The submitter's email
and phone stay in Tally: this repository is public, so they never go on a card.
"""
import json
import os
import re
import urllib.error
import urllib.request

from event_card import GitHub, format_body

# question title words -> card heading, checked in this order (first match wins)
MATCH = [
    (r"e-?mail|phone|contact|your name", None),
    (r"photo|screenshot|image|poster|flyer|picture", "_photo"),
    (r"end", "End date"),
    (r"link|url|website|ticket", "Link"),
    (r"organi[sz]|host|who('| i)s running", "Organiser"),
    (r"event name|name of|title|what's it called", "_title"),
    (r"date|when", "Date"),
    (r"time|start", "Time"),
    (r"venue|where|location|address", "Venue"),
    (r"price|cost|free", "Price"),
    (r"categor|type of", "Category"),
    (r"descri|about|tell us|details", "_about"),
]


def heading_for(title):
    t = title.lower()
    for pattern, heading in MATCH:
        if re.search(pattern, t):
            return heading
    return "_about"


def text(answer, options):
    if answer is None:
        return ""
    if isinstance(answer, list):
        return ", ".join(text(a, options) for a in answer if a not in (None, ""))
    if isinstance(answer, dict):
        for k in ("text", "name", "title", "url", "value"):
            if answer.get(k):
                return str(answer[k])
        return json.dumps(answer, ensure_ascii=False)
    return options.get(str(answer), str(answer))


def tally(path, key):
    # Tally's API sits behind a bot check that refuses Python's default User-Agent with a 403
    req = urllib.request.Request(f"https://api.tally.so{path}", headers={
        "Authorization": f"Bearer {key}", "Accept": "application/json", "User-Agent": "social-circles-site (GitHub Actions)"})
    try:
        with urllib.request.urlopen(req) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as err:
        detail = err.read().decode(errors="replace")[:300]
        hint = " Check the TALLY_API_KEY secret is a current key from the same Tally account as the form." if err.code in (401, 403) else ""
        raise SystemExit(f"Tally said {err.code} {err.reason} for {path.split('?')[0]}: {detail}{hint}") from None


def main():
    key, form = os.environ.get("TALLY_API_KEY"), os.environ.get("TALLY_SUBMIT_FORM_ID")
    if not key or not form:
        print("Tally isn't connected yet (TALLY_API_KEY secret or TALLY_SUBMIT_FORM_ID variable missing). Nothing to do.")
        return
    gh = GitHub()
    gh.ensure_labels()
    seen = set()
    for issue in gh.issues(state="all", labels="submitted"):
        seen.update(re.findall(r"<!-- tally:([\w-]+) -->", issue["body"] or ""))

    page, made = 1, 0
    while True:
        data = tally(f"/forms/{form}/submissions?filter=completed&limit=100&page={page}", key)
        questions = {q["id"]: q for q in data.get("questions", [])}
        options = {f["uuid"]: f["title"] for q in questions.values() for f in q.get("fields", []) if f.get("uuid") and f.get("title")}
        for sub in data.get("submissions", []):
            if sub["id"] in seen:
                continue
            fields, title, about, photo = {}, "", [], False
            for r in sub.get("responses", []):
                q = questions.get(r["questionId"], {})
                heading = heading_for(q.get("title", ""))
                v = r.get("formattedAnswer") or text(r.get("answer"), options)
                if heading is None or not str(v).strip():
                    continue
                if heading == "_title":
                    title = v
                elif heading == "_photo":  # stays in Tally with the contact details, the card just says it's there
                    photo = True
                elif heading == "_about":
                    about.append(v)
                else:
                    fields.setdefault(heading, v)
            fields["Pick blurb"] = " ".join(about)[:400]
            fields["Type"] = "Event"
            kept = "Their contact details and the photo they attached are" if photo else "Their contact details are"
            fields["Source"] = f"Website form, sent {sub.get('submittedAt', '')[:10]}. {kept} in Tally: https://tally.so/forms/{form}/submissions"
            fields["Fit note"] = "Sent in by the organiser or a guest. Check the details and the link before approving."
            gh.call("POST", f"/repos/{gh.repo}/issues", {
                "title": (title or "Event sent in through the website").strip()[:200],
                "body": format_body(fields, f"<!-- tally:{sub['id']} -->"),
                "labels": ["pending", "submitted"],
            })
            seen.add(sub["id"])
            made += 1
        if not data.get("hasMore"):
            break
        page += 1
    print(f"{made} new submissions turned into cards")


if __name__ == "__main__":
    main()
