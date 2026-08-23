"""Score a playoff round and advance the bracket.

Setup once, after the final roto standings are in:

    python run_round.py seed "Team 1 Name" "Team 2 Name" ... "Team 6 Name"

Then each round:

    python run_round.py score 1

Reads data/computed_<start>_<end>.json for that round's dates (from
league.PLAYOFF_WEEKS), scores every matchup, stores the result, and derives
the next round's pairings.

Run it mid-week too — compute.py accepts any end date, so scoring a partial
week gives you live standings. Only `score` runs marked final advance the
bracket; use --final on the last run of the week.
"""

import json
import sys
from pathlib import Path

from league import CATEGORIES, PLAYOFF_WEEKS, score_matchup

DATA = Path(__file__).parent / "data"
DATA.mkdir(exist_ok=True)
BRACKET = DATA / "bracket.json"

FMT = {"AVG": "{:.5f}", "OPS": "{:.4f}", "ERA": "{:.3f}", "WHIP": "{:.4f}"}


def load_bracket():
    if not BRACKET.exists():
        sys.exit("No bracket yet. Run: python run_round.py seed <6 team names>")
    return json.loads(BRACKET.read_text())


def save_bracket(b):
    BRACKET.write_text(json.dumps(b, indent=2))


def cmd_seed(names):
    if len(names) != 6:
        sys.exit(f"Need exactly 6 team names in seed order, got {len(names)}")
    bracket = {
        "seeds": {str(i): n for i, n in enumerate(names, start=1)},
        "results": {},
    }
    save_bracket(bracket)
    print("Seeded:")
    for i, n in enumerate(names, start=1):
        bye = "  (bye to round 2)" if i <= 2 else ""
        print(f"  {i}. {n}{bye}")
    print("\nRound 1: 3v6, 4v5")


def matchups_for(bracket, rnd):
    """Return [(seed_a, seed_b), ...] for a round, derived from prior results."""
    if rnd == 1:
        return [(3, 6), (4, 5)]

    prev = bracket["results"].get(str(rnd - 1))
    if not prev or not prev.get("final"):
        sys.exit(f"Round {rnd - 1} isn't final yet. Score it with --final first.")
    winners = sorted(m["winner"] for m in prev["matchups"])

    if rnd == 2:
        # 1 plays the lowest remaining seed; 2 plays the other.
        return [(1, max(winners)), (2, min(winners))]
    if rnd == 3:
        return [(winners[0], winners[1])]
    sys.exit("Only rounds 1-3 exist.")


def cmd_score(rnd, final):
    bracket = load_bracket()
    seeds = bracket["seeds"]
    start, end = PLAYOFF_WEEKS[rnd]

    path = DATA / f"computed_{start}_{end}.json"
    if not path.exists():
        sys.exit(f"Missing {path}\nRun compute.py for {start}..{end} first.")
    computed = json.loads(path.read_text())
    by_name = {v["name"]: v["categories"] for v in computed.values()}

    pairs = matchups_for(bracket, rnd)
    results = []

    print(f"\nROUND {rnd}   {start} .. {end}"
          f"{'   [FINAL]' if final else '   [in progress]'}\n")

    for a_seed, b_seed in pairs:
        a_name, b_name = seeds[str(a_seed)], seeds[str(b_seed)]
        for n in (a_name, b_name):
            if n not in by_name:
                sys.exit(f"No computed stats for '{n}'. Check the team name "
                         f"in your lineups file matches bracket.json exactly.")

        a_pts, b_pts, winner, detail = score_matchup(
            by_name[a_name], by_name[b_name], a_seed, b_seed)

        print(f"  ({a_seed}) {a_name}")
        print(f"  ({b_seed}) {b_name}")
        print(f"  {'cat':<6} {'':>13} {'':>13}   (* = wins the category)")
        for cat in CATEGORIES:
            av, bv, res = detail[cat]
            f = FMT.get(cat, "{:g}")
            a_s, b_s = f.format(av), f.format(bv)
            a_m = "*" if res in ("A", "TIE") else " "
            b_m = "*" if res in ("B", "TIE") else " "
            print(f"  {cat:<6} {a_m}{a_s:>12} {b_m}{b_s:<12}")
        print(f"  {'':<6} {a_pts:>13} {b_pts:<13}")

        win_name = seeds[str(winner)]
        tie_note = "  (6-6, higher seed advances)" if a_pts == b_pts else ""
        print(f"  -> ({winner}) {win_name}{tie_note}\n")

        results.append({
            "a_seed": a_seed, "b_seed": b_seed,
            "a_points": a_pts, "b_points": b_pts,
            "winner": winner, "winner_name": win_name,
            "categories": {k: {"a": v[0], "b": v[1], "result": v[2]}
                           for k, v in detail.items()},
        })

    bracket["results"][str(rnd)] = {
        "start": start, "end": end, "final": final, "matchups": results}
    save_bracket(bracket)

    if final:
        if rnd == 3:
            print(f"CHAMPION: {results[0]['winner_name']}\n")
        else:
            nxt = matchups_for(bracket, rnd + 1)
            print(f"Round {rnd + 1}: " + ", ".join(
                f"({a}) {seeds[str(a)]} vs ({b}) {seeds[str(b)]}"
                for a, b in nxt) + "\n")
    else:
        print("Not saved as final. Rerun with --final once the week closes.\n")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return
    cmd = sys.argv[1]
    if cmd == "seed":
        cmd_seed(sys.argv[2:])
    elif cmd == "score":
        if len(sys.argv) < 3:
            sys.exit("usage: python run_round.py score <1|2|3> [--final]")
        cmd_score(int(sys.argv[2]), "--final" in sys.argv)
    else:
        print(__doc__)


if __name__ == "__main__":
    main()
