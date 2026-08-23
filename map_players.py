"""Map Yahoo player names to MLBAM IDs.

  python map_players.py data/rosters_2026-08-23.json

Writes data/player_map.json and prints anything it couldn't match.
Unmatched players go in overrides.json as {"Yahoo Name": mlbam_id} and are
merged on every run, so you fix each one exactly once.
"""

import json
import sys
import unicodedata
from pathlib import Path

import requests

DATA = Path(__file__).parent / "data"
OVERRIDES = Path(__file__).parent / "overrides.json"
SEASON = 2026

SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}


def normalize(name):
    if not name:
        return ""
    n = unicodedata.normalize("NFKD", name)
    n = "".join(c for c in n if not unicodedata.combining(c))
    n = "".join(c if c.isalnum() or c.isspace() else " " for c in n.lower())
    parts = [p for p in n.split() if p not in SUFFIXES]
    return " ".join(parts)


def fetch_mlb_players():
    """One call gets every player in the league with an MLBAM id."""
    url = f"https://statsapi.mlb.com/api/v1/sports/1/players?season={SEASON}"
    resp = requests.get(url, timeout=60)
    resp.raise_for_status()
    return resp.json()["people"]


def build_index(people):
    by_name = {}
    for p in people:
        key = normalize(p.get("fullName"))
        by_name.setdefault(key, []).append({
            "id": p["id"],
            "name": p.get("fullName"),
            "team": (p.get("currentTeam") or {}).get("name"),
            "abbr": (p.get("currentTeam") or {}).get("abbreviation"),
        })
    return by_name


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    rosters = json.loads(Path(sys.argv[1]).read_text())

    print("Fetching MLB player universe...")
    index = build_index(fetch_mlb_players())
    print(f"  indexed {sum(len(v) for v in index.values())} players")

    overrides = json.loads(OVERRIDES.read_text()) if OVERRIDES.exists() else {}

    mapping, unmatched, ambiguous = {}, [], []
    seen = set()
    for team in rosters.values():
        for p in team["players"]:
            name = p["name"]
            if name in seen:
                continue
            seen.add(name)

            if name in overrides:
                mapping[name] = overrides[name]
                continue

            hits = index.get(normalize(name), [])
            if len(hits) == 1:
                mapping[name] = hits[0]["id"]
            elif len(hits) > 1:
                # Disambiguate on Yahoo's team abbreviation.
                match = [h for h in hits if h["abbr"] == p.get("team_abbr")]
                if len(match) == 1:
                    mapping[name] = match[0]["id"]
                else:
                    ambiguous.append((name, p.get("team_abbr"), hits))
            else:
                unmatched.append((name, p.get("team_abbr")))

    path = DATA / "player_map.json"
    path.write_text(json.dumps(mapping, indent=2))
    print(f"\nMatched {len(mapping)} of {len(seen)} players -> {path}")

    if ambiguous:
        print("\nAMBIGUOUS — add the right id to overrides.json:")
        for name, abbr, hits in ambiguous:
            print(f"  {name} ({abbr})")
            for h in hits:
                print(f"      {h['id']}  {h['name']}  {h['team']}")
    if unmatched:
        print("\nUNMATCHED — look these up and add to overrides.json:")
        for name, abbr in unmatched:
            print(f"  {name} ({abbr})")
    if not ambiguous and not unmatched:
        print("Clean sweep. No manual fixes needed.")


if __name__ == "__main__":
    main()
