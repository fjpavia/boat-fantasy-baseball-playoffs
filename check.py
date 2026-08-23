"""Preflight check — run this once before the playoffs to catch problems early.

    python check.py

Verifies: Python version, required packages, MLB StatsAPI reachability,
and that the expected files are present. It does NOT need your spreadsheet.
"""

import sys
from pathlib import Path

HERE = Path(__file__).parent
ok = True


def good(msg): print(f"  OK   {msg}")
def bad(msg):
    global ok
    ok = False
    print(f"  FAIL {msg}")


print("Preflight check\n")

# Python version
v = sys.version_info
if v >= (3, 9):
    good(f"Python {v.major}.{v.minor}")
else:
    bad(f"Python {v.major}.{v.minor} — need 3.9+")

# Packages
for pkg in ("pandas", "openpyxl", "requests"):
    try:
        __import__(pkg)
        good(f"{pkg} installed")
    except ImportError:
        bad(f"{pkg} missing — run: pip install -r requirements.txt")

# Files
for f in ("league.py", "xlsx_rosters.py", "compute.py", "run_round.py",
          "run.py", "map_players.py", "publish.sh", "docs/index.html"):
    if (HERE / f).exists():
        good(f"{f}")
    else:
        bad(f"{f} is missing")

# MLB StatsAPI reachability (the only network dependency)
try:
    import requests
    r = requests.get("https://statsapi.mlb.com/api/v1/sports/1/players",
                     params={"season": 2026, "sportId": 1}, timeout=20)
    r.raise_for_status()
    n = len(r.json().get("people", []))
    if n > 100:
        good(f"MLB StatsAPI reachable ({n} players in 2026)")
    else:
        bad(f"MLB StatsAPI returned only {n} players — check the season")
except Exception as e:
    bad(f"MLB StatsAPI unreachable: {e}")

# overrides.json present? (optional but recommended)
if (HERE / "overrides.json").exists():
    import json
    try:
        d = json.loads((HERE / "overrides.json").read_text())
        good(f"overrides.json loaded ({len(d)} entries)")
    except Exception as e:
        bad(f"overrides.json is not valid JSON: {e}")
else:
    print("  --   overrides.json not present yet (fine; add names as needed)")

print()
if ok:
    print("All good. You're ready to run a round:")
    print("  python run.py week1.xlsx 1 --final --publish")
else:
    print("Fix the FAIL lines above, then run check.py again.")
    sys.exit(1)
