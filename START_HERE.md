# START HERE

Playoff scoring + dashboard for the league. Full detail is in README.md;
this is the short version.

## 1. Install (once)

Open a terminal (or Jupyter/Spyder terminal) IN THIS FOLDER, then:

    pip install -r requirements.txt

Check everything works:

    python check.py

## 2. Turn overrides on (once)

Rename the example file so the scorer uses it:

    mv overrides.example.json overrides.json      # macOS/Linux
    # (or just rename it in Finder)

It already contains the tricky names we verified (the right Max Muncy,
Luis García Jr., Ohtani). Add a line here any time a player name doesn't
resolve.

## 3. Put the dashboard online (once)

    git init && git add . && git commit -m "first"
    git branch -M main
    git remote add origin https://github.com/<you>/<repo>.git
    git push -u origin main

On GitHub: Settings -> Pages -> Deploy from a branch -> main -> /docs -> Save.
Your site: https://<you>.github.io/<repo>/

## 4. Seed the bracket (once, after roto standings are final)

Names must match your spreadsheet tab names EXACTLY:

    python run.py --seed "1 seed" "2 seed" "3 seed" "4 seed" "5 seed" "6 seed"

## 5. Each playoff week

Make that week's spreadsheet (one tab per team, tab named for the team,
Yahoo roster pasted in). Then one command:

    python run.py week1.xlsx 1 --final --publish

- `week1.xlsx` -> your file for that week
- `1` -> the round number (1, 2, or 3)
- `--final` -> only when the week is over; leave off for live mid-week updates
- `--publish` -> pushes to the dashboard

Rounds 2 and 3:

    python run.py week2.xlsx 2 --final --publish
    python run.py week3.xlsx 3 --final --publish

If it stops saying a team has too few starters, a player name didn't match —
read what it printed, add that name to overrides.json, run again.

## The dates (already set)

    Round 1  Aug 30 - Sep 5
    Round 2  Sep 6  - Sep 12
    Round 3  Sep 13 - Sep 19

## Prefer a notebook?

Open `playoffs.ipynb` in Jupyter Lab — one cell per round, same commands.
