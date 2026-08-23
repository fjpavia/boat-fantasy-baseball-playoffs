"""Build a rosters file from the Yahoo roster copy-paste spreadsheet.

  python xlsx_rosters.py Fantasy_teams_copies.xlsx 2026-08-30

Each tab is one team (tab name = team name). Within a tab, the layout is
Yahoo's roster page pasted in: a 'Pos' header row, then one row per player
with the position slot in column A and a mashed-together name string in
column B like "Alejandro KirkPlayer NoteTOR - C". Every player row is
followed by a junk row (the live score line).

Started vs bench is read from the Pos column:
  started:  C 1B 2B 3B SS OF Util SP RP P  (and CI/MI/IF/DH if present)
  excluded: BN, IL, IL10, IL60, NA
The 'Pitchers' header switches section so we tag position type from the
sheet itself.

Names still go through MLB StatsAPI for the MLBAM id (used by compute.py),
but hitter/pitcher comes from the sheet, which handles two-way players
correctly if they appear in both sections.
"""

import json
import re
import sys
from pathlib import Path

import pandas as pd

from map_players import build_index, fetch_mlb_players, normalize

DATA = Path(__file__).parent / "data"
DATA.mkdir(exist_ok=True)
OVERRIDES = Path(__file__).parent / "overrides.json"

STARTED_SLOTS = {"C", "1B", "2B", "3B", "SS", "OF", "CF", "LF", "RF",
                 "Util", "UTIL", "CI", "MI", "IF", "DH",
                 "SP", "RP", "P"}
BENCH_SLOTS = {"BN", "NA"}  # IL* handled by prefix

CRUFT_MARKERS = [
    "Video Forecast", "New Player Note", "No new player Notes",
    "No New Player Notes", "Player Note", "DTD", "IL10", "IL15", "IL60",
    "IL7", "NA", "(Batter)", "(Pitcher)",
]


def clean_name(raw):
    """'Jose RamirezVideo ForecastNew Player NoteCLE - 3B' -> 'Jose Ramirez'."""
    if not isinstance(raw, str):
        return None
    s = raw.strip()
    cut = len(s)
    for m in CRUFT_MARKERS:
        idx = s.find(m)
        if idx != -1:
            cut = min(cut, idx)
    s = s[:cut].strip()
    s = re.sub(r"\s*[A-Z]{2,3}\s*-\s*[A-Z0-9,/]+\s*$", "", s).strip()
    s = re.sub(r"\s*\((?:Batter|Pitcher)\)\s*$", "", s).strip()
    return s or None


def slot_kind(pos):
    if not isinstance(pos, str):
        return None
    p = pos.strip()
    if not p:
        return None
    if p.upper().startswith("IL"):
        return "bench"
    if p in BENCH_SLOTS:
        return "bench"
    if p in STARTED_SLOTS:
        return "start"
    return None


def parse_team(df):
    section = "B"
    for i in range(len(df)):
        pos = df.iloc[i, 0]
        raw = df.iloc[i, 1]
        if isinstance(pos, str) and pos.strip() == "Pos":
            section = "P" if (isinstance(raw, str) and "Pitch" in raw) else "B"
            continue
        kind = slot_kind(pos)
        if kind is None:
            continue
        name = clean_name(raw)
        if not name:
            continue
        yield name, section, (kind == "start")


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return
    xlsx_file, date = sys.argv[1], sys.argv[2]

    sheets = pd.read_excel(xlsx_file, sheet_name=None, dtype=str, header=None)
    print(f"Found {len(sheets)} tabs: {', '.join(sheets)}\n")

    print("Fetching MLB player universe...")
    people = fetch_mlb_players()
    index = build_index(people)
    overrides = json.loads(OVERRIDES.read_text()) if OVERRIDES.exists() else {}

    out, problems = {}, []
    for i, (tab, df) in enumerate(sheets.items(), start=1):
        players, started_ct = [], 0
        for name, sect, started in parse_team(df):
            if not started:
                # Bench/IL players don't score, and injured players are often
                # absent from MLB's active list — don't try to resolve them.
                players.append({
                    "player_id": None, "name": name, "team_abbr": None,
                    "position_type": sect,
                    "selected_position": None, "started": False,
                })
                continue
            pid = overrides.get(name)
            if pid is None:
                hits = index.get(normalize(name), [])
                if len(hits) == 1:
                    pid = hits[0]["id"]
                else:
                    problems.append((tab, name, hits))
                    continue
            players.append({
                "player_id": pid, "name": name, "team_abbr": None,
                "position_type": sect,
                "selected_position": None, "started": started,
            })
            started_ct += started

        out[f"manual.t.{i}"] = {"name": tab.strip(), "players": players}
        print(f"[{tab}]  {started_ct} starters "
              f"({len(players)} total incl. bench/IL)")
        for p in players:
            flag = "  " if p["started"] else "BN"
            print(f"    {flag} {p['position_type']}  {p['name']}")
        print()

    path = DATA / f"rosters_{date}.json"
    path.write_text(json.dumps(out, indent=2))
    print(f"Wrote {path}")

    if problems:
        print('\nUnresolved names -- add to overrides.json as {"Name": mlbam_id}:')
        for tab, name, hits in problems:
            print(f"  [{tab}] {name!r}")
            for h in hits:
                print(f"      {h['id']}  {h['name']}  {h['team']}")
        print("\nThese were DROPPED. Fix and rerun before scoring.")
    else:
        print("\nAll names resolved.")
    print("Only the un-flagged (started) players count toward scoring.")


if __name__ == "__main__":
    main()
