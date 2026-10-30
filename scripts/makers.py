"""Meet the maker: an organiser's answers to three quick questions, shown on their event pages.

A maker card is a GitHub issue labelled "maker", written by the Tally import (or by hand) and
published when Nikita adds "approved", the same as an event card. Its title is the organiser's
name as it appears on their events. Contact details never go on it: the repository is public.
"""
import re

from event_card import parse_body, value

# heading on the maker card -> key
QUESTIONS = [
    ("What do you make or run?", "what"),
    ("What should someone coming for the first time expect?", "expect"),
    ("Where else in Jersey do you love to go?", "loves"),
]
EXTRA = [("Organiser", "by"), ("Instagram", "insta")]
HANDLE = re.compile(r"^@?([A-Za-z0-9._]{1,30})$")


def key(name):
    """'The Stoodio' and 'the stoodio.' match; so do 'Jersey Arts Centre' and 'Jersey Arts Centre Ltd'."""
    words = re.sub(r"[^a-z0-9 ]+", " ", (name or "").lower()).split()
    return " ".join(w for w in words if w not in {"the", "ltd", "limited", "jersey"} or len(words) == 1)


def to_maker(title, body):
    """Card -> {"by", "what", "expect", "loves", "insta"}, or None if no question was answered."""
    fields = parse_body(body)
    m = {k: value(fields.get(h, "")) for h, k in QUESTIONS + EXTRA}
    m["by"] = m["by"] or re.sub(r"^meet the maker:\s*", "", (title or "").strip(), flags=re.I)
    insta = HANDLE.match(re.sub(r"^https?://(www\.)?instagram\.com/|/$", "", m["insta"] or ""))
    m["insta"] = insta.group(1) if insta else ""
    if not m["by"] or not any(m[k] for _, k in QUESTIONS):
        return None
    return m


def format_maker(fields, marker=""):
    parts = [f"### {h}\n\n{str(fields.get(h) or '').strip() or '_No response_'}" for h, _ in EXTRA[:1] + QUESTIONS + EXTRA[1:]]
    return "\n\n".join(parts + ([marker] if marker else [])) + "\n"


def index(makers):
    return {key(m["by"]): m for m in makers}


def find(makers, by):
    """The maker behind an event: "The Stoodio at ArtHouse Jersey" and "The Stoodio (Sophie Harris)" find The Stoodio."""
    k = key(by)
    hits = [n for n in makers if n and (k == n or k.startswith(n + " "))]
    return makers[max(hits, key=len)] if hits else None
