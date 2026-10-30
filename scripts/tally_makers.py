"""Turn new "Meet the maker" answers from Tally into maker cards waiting for Nikita.

Run every hour by the Tally workflow, after the event import. Needs the TALLY_API_KEY secret
and the TALLY_MAKER_FORM_ID variable; until both are set it does nothing. Emails and phone
numbers stay in Tally: this repository is public.
"""
import os
import re

from event_card import GitHub
from makers import format_maker
from tally_to_cards import tally, text

# question title words -> maker card heading, first match wins
MATCH = [
    (r"e-?mail|phone|contact", None),
    (r"insta", "Instagram"),
    (r"first time|expect", "What should someone coming for the first time expect?"),
    (r"else|love", "Where else in Jersey do you love to go?"),
    (r"make|run", "What do you make or run?"),
    (r"organi[sz]|name|business|who", "Organiser"),
]
CONTACT = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+|(?:\+44\s?|0)\d(?:[\s-]?\d){8,9}\b")


def heading_for(title):
    return next((h for p, h in MATCH if re.search(p, title.lower())), None)


def main():
    key, form = os.environ.get("TALLY_API_KEY"), os.environ.get("TALLY_MAKER_FORM_ID")
    if not key or not form:
        print("The Meet the maker form isn't connected yet (TALLY_MAKER_FORM_ID variable missing). Nothing to do.")
        return
    gh = GitHub()
    gh.ensure_labels()
    seen = set()
    for issue in gh.issues(state="all", labels="maker"):
        seen.update(re.findall(r"<!-- tally-maker:([\w-]+) -->", issue["body"] or ""))
    page, made = 1, 0
    while True:
        data = tally(f"/forms/{form}/submissions?filter=completed&limit=100&page={page}", key)
        questions = {q["id"]: q for q in data.get("questions", [])}
        options = {f["uuid"]: f["title"] for q in questions.values() for f in q.get("fields", []) if f.get("uuid") and f.get("title")}
        for sub in data.get("submissions", []):
            if sub["id"] in seen:
                continue
            fields = {}
            for r in sub.get("responses", []):
                heading = heading_for(questions.get(r["questionId"], {}).get("title", ""))
                v = CONTACT.sub("[contact details removed]", str(r.get("formattedAnswer") or text(r.get("answer"), options))).strip()
                if heading and v:
                    fields.setdefault(heading, v[:600])
            name = fields.get("Organiser") or "Organiser"
            gh.call("POST", f"/repos/{gh.repo}/issues", {
                "title": f"Meet the maker: {name}"[:200],
                "body": format_maker(fields, f"<!-- tally-maker:{sub['id']} -->"),
                "labels": ["maker", "pending"],
            })
            seen.add(sub["id"])
            made += 1
        if not data.get("hasMore"):
            break
        page += 1
    print(f"{made} new Meet the maker answers turned into cards")


if __name__ == "__main__":
    main()
