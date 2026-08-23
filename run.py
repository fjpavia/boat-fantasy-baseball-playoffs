"""Run a whole playoff round in one command.

    python run.py <spreadsheet.xlsx> <round 1|2|3> [--final] [--publish]

What it does, in order:
  1. xlsx_rosters  — read starters from the spreadsheet
  2. compute       — tally the 12 categories from MLB game logs
  3. run_round     — score the round and advance the bracket
  4. publish.sh    — push to the dashboard   (only with --publish)

The round number picks the dates from league.PLAYOFF_WEEKS, so you never type
them. Example — score round 1 as final and push it live:

    python run.py week1.xlsx 1 --final --publish

Mid-week live update (no --final; standings show as "in progress"):

    python run.py week1.xlsx 1 --publish

Seed the bracket once before round 1:

    python run.py --seed "Seed 1" "Seed 2" "Seed 3" "Seed 4" "Seed 5" "Seed 6"
"""

import subprocess
import sys
from pathlib import Path

from league import PLAYOFF_WEEKS

HERE = Path(__file__).parent


def run(args):
    """Run a subprocess, stream its output, stop the whole thing on failure."""
    print(f"\n$ {' '.join(args)}\n" + "-" * 60)
    result = subprocess.run(args)
    if result.returncode != 0:
        print(f"\n!! '{args[1] if len(args) > 1 else args[0]}' failed "
              f"(exit {result.returncode}). Stopping — nothing was published.")
        sys.exit(result.returncode)


def main():
    argv = sys.argv[1:]
    if not argv or argv[0] in ("-h", "--help"):
        print(__doc__)
        return

    if argv[0] == "--seed":
        names = argv[1:]
        if len(names) != 6:
            sys.exit("--seed needs exactly 6 team names, in seed order.")
        run([sys.executable, "run_round.py", "seed", *names])
        print("\nSeeded. Run a round with:  python run.py <file.xlsx> 1 --final --publish")
        return

    if len(argv) < 2:
        print(__doc__)
        return

    xlsx = argv[0]
    try:
        rnd = int(argv[1])
    except ValueError:
        sys.exit(f"Round must be 1, 2, or 3 — got '{argv[1]}'.")
    if rnd not in PLAYOFF_WEEKS:
        sys.exit(f"No round {rnd}. Rounds are {sorted(PLAYOFF_WEEKS)}.")

    final = "--final" in argv
    publish = "--publish" in argv

    if not Path(xlsx).exists():
        sys.exit(f"Spreadsheet not found: {xlsx}")

    start, end = PLAYOFF_WEEKS[rnd]
    rosters = f"data/rosters_{start}.json"

    print(f"ROUND {rnd}   {start} .. {end}   "
          f"{'FINAL' if final else 'in progress'}"
          f"{'   + publish' if publish else ''}")

    run([sys.executable, "xlsx_rosters.py", xlsx, start])

    # Guard: if any name failed to resolve, xlsx_rosters prints it but still
    # exits 0. Re-read the file and warn loudly before we score on bad data.
    import json
    data = json.loads(Path(rosters).read_text())
    thin = [t["name"] for t in data.values()
            if sum(1 for p in t["players"] if p["started"]) < 10]
    if thin:
        print("\n!! These teams have fewer than 10 starters — likely an "
              "unresolved name:")
        for n in thin:
            print(f"     {n}")
        print("   Check the output above and fix overrides.json, then rerun.")
        if "--force" in argv:
            print("   --force set; scoring anyway.")
        elif not sys.stdin.isatty():
            # Notebook `!` cells and other non-interactive runs can't answer a
            # prompt, so stop rather than hang. Rerun with --force to override.
            sys.exit("   Non-interactive run: stopping. Rerun with --force to "
                     "score anyway.")
        elif input("\n   Continue anyway? [y/N] ").strip().lower() != "y":
            sys.exit("Stopped. Nothing scored.")

    run([sys.executable, "compute.py", rosters, start, end])

    score_args = [sys.executable, "run_round.py", "score", str(rnd)]
    if final:
        score_args.append("--final")
    run(score_args)

    if publish:
        run(["bash", "publish.sh"])
    else:
        print("\nNot published. Add --publish to push this to the dashboard.")


if __name__ == "__main__":
    main()
