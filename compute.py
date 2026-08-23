"""Compute team category totals for a date range from MLB StatsAPI components.

  python compute.py data/rosters_2026-08-23.json 2026-08-23 2026-08-29
"""

import json
import sys
from collections import defaultdict
from pathlib import Path

import requests

from league import compute_categories, ip_to_outs

DATA = Path(__file__).parent / "data"
STATSAPI = "https://statsapi.mlb.com/api/v1/people/{pid}/stats"

HIT_FIELDS = ["atBats", "hits", "baseOnBalls", "hitByPitch", "sacFlies",
              "totalBases", "runs", "homeRuns", "rbi", "stolenBases"]
PIT_FIELDS = ["earnedRuns", "hits", "baseOnBalls", "strikeOuts",
              "wins", "saves", "holds"]


def player_range_stats(pid, start, end, group, session):
    resp = session.get(
        STATSAPI.format(pid=pid),
        params={"stats": "byDateRange", "startDate": start, "endDate": end,
                "group": group, "sportId": 1},
        timeout=30,
    )
    if resp.status_code != 200:
        return None
    splits = resp.json().get("stats", [])
    if not splits or not splits[0].get("splits"):
        return None
    return splits[0]["splits"][0].get("stat", {})


def compute_team(players, start, end, session):
    hit = defaultdict(int)
    pit = defaultdict(int)
    missing = []

    for p in players:
        if not p["started"]:
            continue
        pid = p.get("player_id")
        if not pid:
            missing.append(p["name"])
            continue

        group = "pitching" if p.get("position_type") == "P" else "hitting"
        stat = player_range_stats(pid, start, end, group, session)
        if not stat:
            continue

        if group == "hitting":
            for f in HIT_FIELDS:
                hit[f] += int(stat.get(f, 0) or 0)
        else:
            pit["outs"] += ip_to_outs(stat.get("inningsPitched"))
            for f in PIT_FIELDS:
                pit[f] += int(stat.get(f, 0) or 0)

    return dict(hit), dict(pit), missing


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return
    roster_file, start, end = sys.argv[1], sys.argv[2], sys.argv[3]

    rosters = json.loads(Path(roster_file).read_text())

    session = requests.Session()
    results = {}
    for team_key, team in rosters.items():
        hit, pit, missing = compute_team(
            team["players"], start, end, session)
        cats = compute_categories(hit, pit)
        results[team_key] = {
            "name": team["name"],
            "categories": cats,
            "components": {"hitting": hit, "pitching": pit},
            "unmapped": missing,
        }
        print(f"{team['name']:<35} "
              f"R{cats['R']:>4} HR{cats['HR']:>3} RBI{cats['RBI']:>4} "
              f"SB{cats['SB']:>3} AVG {cats['AVG']:.5f} OPS {cats['OPS']:.4f} | "
              f"W{cats['W']:>3} SV{cats['SV']:>3} K{cats['K']:>4} "
              f"HLD{cats['HLD']:>3} ERA {cats['ERA']:.3f} WHIP {cats['WHIP']:.4f}")
        if missing:
            print(f"    !! unmapped: {', '.join(missing)}")

    path = DATA / f"computed_{start}_{end}.json"
    path.write_text(json.dumps(results, indent=2))
    print(f"\nWrote {path}")


if __name__ == "__main__":
    main()
