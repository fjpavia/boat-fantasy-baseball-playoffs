# Roto Playoffs — League 26714

Six-team single-elimination bracket bolted onto a Yahoo rotisserie season.
Stats come from MLB StatsAPI (no login). Yahoo is used only as the place you
copy starting lineups from, into one spreadsheet per playoff week.

Bracket: 3v6 and 4v5 in round 1; seeds 1 and 2 get byes; in round 2 the
1-seed plays the lowest remaining seed and the 2-seed plays the other.
Each round is one Sun–Sat week. Scoring is 12 head-to-head categories;
a tied category splits half a win each, and a 6–6 overall tie goes to the
higher seed.

    Round 1: 2026-08-30 .. 2026-09-05   (3v6, 4v5)
    Round 2: 2026-09-06 .. 2026-09-12   (1 vs lowest, 2 vs other)
    Round 3: 2026-09-13 .. 2026-09-19   (final)

## Files

    run.py            one command: extract -> compute -> score -> publish
    playoffs.ipynb     the same, as a notebook (one cell per round)
    xlsx_rosters.py   read starters from the weekly spreadsheet
    map_players.py     (used by xlsx_rosters) name -> MLBAM id
    compute.py         tally the 12 categories from game logs
    run_round.py       score a round, advance the bracket
    league.py          dates, categories, scoring rules
    publish.sh         push the latest bracket to the live dashboard
    docs/index.html    the dashboard (GitHub Pages serves this)
    overrides.json     manual name fixes (created as needed)

## Setup (once)

    pip install -r requirements.txt

## The spreadsheet

One workbook per playoff week. Each tab is one team; the tab NAME is the team
name. Paste Yahoo's roster page into each tab (the format you already used:
a "Pos" column, a "Batters"/"Pitchers" header, one player per row). The
script keeps only started players (C/1B/.../SP/RP/P) and ignores BN and IL.

Team tab names must match the seed names you pass to `run_round.py seed`
exactly — that's how a matchup finds its stats.

## Seed the bracket (once, after final roto standings)

    python run.py --seed "<seed 1>" "<seed 2>" "<seed 3>" "<seed 4>" "<seed 5>" "<seed 6>"

## Each playoff week — one command

    python run.py <spreadsheet.xlsx> <round> [--final] [--publish]

This runs all four steps in order: extract rosters, tally categories, score
the round, and (with --publish) push to the dashboard. The round number picks
its own dates, so you never type them.

Round 1, scored as final and pushed live:

    python run.py week1.xlsx 1 --final --publish

Mid-week live update (omit --final; the dashboard shows "in progress"):

    python run.py week1.xlsx 1 --publish

Round 2 and 3 are identical with their own file and number:

    python run.py week2.xlsx 2 --final --publish
    python run.py week3.xlsx 3 --final --publish

Score rounds in order with --final — each round's matchups come from the
previous round's finalized result.

If a team shows fewer than 10 starters (usually an unresolved player name),
run.py stops before scoring and tells you which team. Fix the name in
overrides.json and rerun. To score anyway, add --force.

### Running the four steps by hand

If you ever want to run a single step, they're still separate scripts:

    python xlsx_rosters.py week1.xlsx 2026-08-30
    python compute.py data/rosters_2026-08-30.json 2026-08-30 2026-09-05
    python run_round.py score 1 --final
    ./publish.sh

## Dashboard (GitHub Pages) — once

1. Push this folder to a new GitHub repo:

       git init
       git add .
       git commit -m "Initial commit"
       git branch -M main
       git remote add origin https://github.com/<you>/<repo>.git
       git push -u origin main

2. GitHub -> Settings -> Pages. Source: "Deploy from a branch".
   Branch: main, folder: /docs. Save.

3. Live in ~1 minute at https://<you>.github.io/<repo>/

Nothing sensitive is in this repo (only fantasy stats), so a public repo is
simplest. After setup, `./publish.sh` is all you run to update it.

## Notes

Rate stats (AVG/OPS/ERA/WHIP) are computed from game-log components, so they
can differ slightly from Yahoo's rounded standings. That's precision, not a
bug. Without Yahoo API access there's no automated reconciliation — after
round 1, spot-check a couple of teams' counting stats against how Yahoo's
roto standings moved that week.
