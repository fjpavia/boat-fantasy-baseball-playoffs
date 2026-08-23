"""League configuration and category math."""

LEAGUE_ID = "26714"

# Sunday-start weeks, matching your lineup lock. CONFIRM THESE DATES.
FINAL_ROTO_WEEK = ("2026-08-23", "2026-08-29")
PLAYOFF_WEEKS = {
    1: ("2026-08-30", "2026-09-05"),  # 3v6, 4v5
    2: ("2026-09-06", "2026-09-12"),  # 1 vs lowest remaining, 2 vs other
    3: ("2026-09-13", "2026-09-19"),  # final
}

# Which direction is good. True = higher wins.
CATEGORIES = {
    "R": True, "HR": True, "RBI": True, "SB": True, "AVG": True, "OPS": True,
    "W": True, "SV": True, "K": True, "HLD": True, "ERA": False, "WHIP": False,
}

BENCH_POSITIONS = {"BN", "IL", "IL+", "IL10", "IL60", "NA"}


def ip_to_outs(ip):
    """MLB reports innings as '12.1' meaning 12 and 1/3. Convert to outs."""
    if ip in (None, ""):
        return 0
    whole, _, frac = str(ip).partition(".")
    return int(whole or 0) * 3 + int(frac or 0)


def outs_to_ip(outs):
    return f"{outs // 3}.{outs % 3}"


def compute_categories(hit, pit):
    """Turn aggregated component totals into the 12 scoring categories.

    hit: atBats, hits, baseOnBalls, hitByPitch, sacFlies, totalBases, runs,
         homeRuns, rbi, stolenBases
    pit: outs, earnedRuns, hits, baseOnBalls, strikeOuts, wins, saves, holds
    """
    ab = hit.get("atBats", 0)
    h = hit.get("hits", 0)
    bb = hit.get("baseOnBalls", 0)
    hbp = hit.get("hitByPitch", 0)
    sf = hit.get("sacFlies", 0)
    tb = hit.get("totalBases", 0)

    obp_denom = ab + bb + hbp + sf
    obp = (h + bb + hbp) / obp_denom if obp_denom else 0.0
    slg = tb / ab if ab else 0.0

    outs = pit.get("outs", 0)
    innings = outs / 3 if outs else 0.0

    return {
        "R": hit.get("runs", 0),
        "HR": hit.get("homeRuns", 0),
        "RBI": hit.get("rbi", 0),
        "SB": hit.get("stolenBases", 0),
        "AVG": h / ab if ab else 0.0,
        "OPS": obp + slg,
        "W": pit.get("wins", 0),
        "SV": pit.get("saves", 0),
        "K": pit.get("strikeOuts", 0),
        "HLD": pit.get("holds", 0),
        "ERA": pit.get("earnedRuns", 0) * 9 / innings if innings else 0.0,
        "WHIP": (pit.get("baseOnBalls", 0) + pit.get("hits", 0)) / innings if innings else 0.0,
    }


def score_matchup(a_cats, b_cats, a_seed, b_seed, tolerance=1e-9):
    """Head-to-head across 12 categories. Ties split; overall tie -> higher seed.

    Returns (a_points, b_points, winner_seed, per_category_detail).
    """
    a_pts = b_pts = 0.0
    detail = {}
    for cat, higher_wins in CATEGORIES.items():
        av, bv = a_cats[cat], b_cats[cat]
        # A team with zero innings shouldn't "win" ERA with a 0.00.
        if cat in ("ERA", "WHIP") and (av == 0.0) != (bv == 0.0):
            av_valid, bv_valid = av > 0, bv > 0
            if not av_valid:
                a_pts += 0; b_pts += 1; detail[cat] = (av, bv, "B")
                continue
            if not bv_valid:
                a_pts += 1; detail[cat] = (av, bv, "A")
                continue
        if abs(av - bv) <= tolerance:
            a_pts += 0.5
            b_pts += 0.5
            result = "TIE"
        elif (av > bv) == higher_wins:
            a_pts += 1
            result = "A"
        else:
            b_pts += 1
            result = "B"
        detail[cat] = (av, bv, result)

    if a_pts > b_pts:
        winner = a_seed
    elif b_pts > a_pts:
        winner = b_seed
    else:
        winner = min(a_seed, b_seed)  # overall tie -> higher seed
    return a_pts, b_pts, winner, detail
