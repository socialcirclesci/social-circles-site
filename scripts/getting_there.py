"""The "Getting there" box on each event page: is it in town, and how to find the bus there and back.

Jersey has no open bus timetable data (only live arrivals), and routes and last buses change
with the seasons, so this never states route numbers or times. It says whether the venue is
in St Helier, where every LibertyBus route starts, and links to bus directions and the
timetables. Venues with no fixed place ("shared when you book") get no box.
"""
import re
import urllib.parse

TIMETABLES = "https://www.libertybus.je/routes_times/timetables"

# Venues in St Helier town that don't say "St Helier" in their name, matched on lower case words
TOWN = ["jersey arts centre", "berni gallery", "methodist centre", "methodist church", "capital house", "wellbeing hub",
        "commercial buildings", "sundown", "wharf st", "opera house", "town church", "town hall", "town library",
        "jersey museum", "jersey archive", "royal square", "havre des pas", "ommaroo", "weighbridge", "harbour gallery",
        "the quay", "halket place", "new street", "phillips street", "post horn", "royal hotel"]
# Places with their own way in, said plainly
SPECIAL = [
    ("elizabeth castle", "Elizabeth Castle sits out in St Aubin's Bay: walk the causeway at low tide or take the castle ferry from West Park, a short walk from Liberation Station."),
]
# Parishes and places outside town
AWAY = ["st ouen", "trinity", "st lawrence", "st mary", "st clement", "st brelade", "st aubin", "grouville", "gorey",
        "st martin", "st john", "st peter", "st saviour", "greve de lecq", "carrefour", "corbiere", "rozel", "bouley bay"]
NO_PLACE = re.compile(r"\bbook|\bshared\b|\btbc\b|\bvarious\b|\bonline\b", re.I)


def getting_there(venue):
    """Return (sentence, directions URL), or None when there's no fixed place to go."""
    v = (venue or "").strip()
    if len(v) < 4 or NO_PLACE.search(v):
        return None
    low = v.lower()
    directions = "https://www.google.com/maps/dir/?" + urllib.parse.urlencode(
        {"api": "1", "destination": f"{v}, Jersey", "travelmode": "transit"})
    said = next((s for k, s in SPECIAL if k in low), None)
    if said:
        return said, directions
    if "st helier" in low or any(k in low for k in TOWN):
        return "In St Helier town, walkable from Liberation Station, where every bus route starts and ends.", directions
    if any(k in low for k in AWAY):
        return "Out of town. Buses leave from Liberation Station in St Helier; check the route and the last bus home before you go, as times change with the seasons.", directions
    return "Buses leave from Liberation Station in St Helier; check the route and the last bus home before you go, as times change with the seasons.", directions
