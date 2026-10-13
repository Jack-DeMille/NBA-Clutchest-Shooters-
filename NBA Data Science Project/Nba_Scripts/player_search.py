"""
Player search: type a player's name (plus an optional season, season range,
and/or "playoffs" / "regular season") in ANY order and get their FG% on
potential game-tying/go-ahead shots (<=24s left in the 4th/OT), with makes,
attempts, a regular season vs. playoffs split, and a season-by-season table.

Examples of things you can type:
    James Harden                         -> career
    James Harden 2019                    -> the 2018-19 season (RS + playoffs)
    James Harden 2019 Regular Season     -> 2018-19 regular season only
    James Harden 2019-2025               -> every season from 2018-19 to 2024-25
    Playoffs 2018 LeBron James           -> LeBron's 2017-18 playoffs
    lebron playoffs                      -> LeBron's career playoffs
    James Harden 2018-19                 -> explicit season format also works

Reads clutch_shots.csv (from build_clutch_dataset.py) and games.csv (from
get_game_ids.py), so run those first and keep this file in the same folder.

Run it with: python3 player_search.py
"""

import re
import unicodedata
import pandas as pd
from nba_api.stats.static import players

SHOTS_FILE = "clutch_shots.csv"
GAMES_FILE = "games.csv"
LEADERBOARD_MIN_ATTEMPTS = 150

# How a lone year like "2019" is read. NBA convention (and Basketball
# Reference) names a season after the year it ENDS, so True means
# "2019" = the 2018-19 season. Set to False if you'd rather have
# "2019" mean the 2019-20 season.
YEAR_MEANS_SEASON_END = True

# Words that can appear in a query but aren't part of a player's name
FILLER_WORDS = {"in", "during", "from", "for", "stats", "season", "seasons", "the", "of"}

PLAYOFF_PATTERN = re.compile(r"\b(?:playoffs?|post\s*season)\b")
REGULAR_PATTERN = re.compile(r"\b(?:regular(?:\s+season)?|reg\s+season)\b")
RANGE_PATTERN = re.compile(r"\b(\d{4})\s*(?:-|\u2013|to|through|thru)\s*(\d{4})\b")
SEASON_PATTERN = re.compile(r"\b(\d{4})\s*-\s*(\d{2})(?!\d)")
YEAR_PATTERN = re.compile(r"\b(\d{4})\b")


def normalize(text):
    """Lowercases, strips accents and punctuation: 'De'Aaron' -> 'deaaron'."""
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    text = text.replace("-", " ")
    text = re.sub(r"[^a-z0-9 ]", "", text)
    return " ".join(text.split())


def year_to_end(year):
    """Converts a typed year into the year its season ENDS (2018-19 -> 2019)."""
    return year if YEAR_MEANS_SEASON_END else year + 1


def season_label(end_year):
    return f"{end_year - 1}-{str(end_year)[-2:]}"


def parse_query(raw):
    """
    Pulls the pieces out of a free-form query, in any order.
    Returns (player_name, first_season_end, last_season_end, season_type);
    the season values are None when no year was given, and season_type is
    None (both), "Regular Season", or "Playoffs".
    """
    text = raw.lower()

    # 1. Season type keywords
    found = set()
    text, n = PLAYOFF_PATTERN.subn(" ", text)
    if n:
        found.add("Playoffs")
    text, n = REGULAR_PATTERN.subn(" ", text)
    if n:
        found.add("Regular Season")
    season_type = found.pop() if len(found) == 1 else None

    # 2. Years: a range (2019-2025), an explicit season (2018-19), or one year
    first = last = None
    m = RANGE_PATTERN.search(text)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        first, last = sorted((year_to_end(a), year_to_end(b)))
    else:
        m = SEASON_PATTERN.search(text)
        if m:
            start, yy = int(m.group(1)), int(m.group(2))
            if yy != (start + 1) % 100:
                raise ValueError(
                    f"'{m.group(0)}' isn't a real season - did you mean "
                    f"{start}-{str(start + 1)[-2:]}?"
                )
            first = last = start + 1
        else:
            m = YEAR_PATTERN.search(text)
            if m:
                first = last = year_to_end(int(m.group(1)))
    if m:
        text = text[:m.start()] + " " + text[m.end():]
    if YEAR_PATTERN.search(text):
        raise ValueError("I found more than one year. Give me a single season "
                         "or one range, like 2019-2025.")

    # 3. Whatever is left is the player's name
    words = [w for w in normalize(text).split() if w not in FILLER_WORDS]
    name = " ".join(words)
    if not name:
        raise ValueError("I didn't catch a player name in that.")
    return name, first, last, season_type


def load_data():
    # Read game IDs as text so leading zeros (e.g. 0022500001) survive
    shots = pd.read_csv(SHOTS_FILE, dtype={"gameId": str})
    games = pd.read_csv(GAMES_FILE, dtype={"game_id": str})

    # If a run was interrupted and redone, the same shot can end up in the
    # file twice, which would inflate attempts. Drop exact repeats and say so.
    before = len(shots)
    shots = shots.drop_duplicates()
    dupes = before - len(shots)
    if dupes:
        print(f"Note: ignored {dupes} exact duplicate rows in {SHOTS_FILE}.")

    shots["gameId"] = shots["gameId"].str.zfill(10)
    games["game_id"] = games["game_id"].str.zfill(10)

    # games.csv knows each game's season and whether it was playoffs or not
    shots = shots.merge(
        games[["game_id", "season", "season_type"]],
        left_on="gameId", right_on="game_id", how="left",
    )
    shots["season_type"] = shots["season_type"].fillna("Unknown")
    shots["season_end_year"] = pd.to_numeric(shots["season"].str[:4], errors="coerce") + 1
    shots["made"] = (shots["shotResult"] == "Made").astype(int)
    return shots


def find_matches(name, all_players, ids_in_data):
    """Returns (matches that have shot data, matches overall)."""
    overall = [p for p in all_players if name in normalize(p["full_name"])]

    # An exact full-name match wins outright (so 'jamal murray' is one result)
    exact = [p for p in overall if normalize(p["full_name"]) == name]
    if exact:
        overall = exact

    in_data = [p for p in overall if p["id"] in ids_in_data]
    return in_data, overall


def record(df, empty="no qualifying attempts"):
    """Formats a slice of shots as 'makes/attempts (FG%)'."""
    attempts = len(df)
    if attempts == 0:
        return empty
    makes = int(df["made"].sum())
    return f"{makes}/{attempts} ({makes / attempts:.1%})"


def print_season_table(df, season_type):
    seasons = sorted(df["season"].dropna().unique())
    if len(seasons) < 2:
        return

    print("\nBy season (seasons with no qualifying shots aren't listed):")
    if season_type:
        print(f"  {'Season':<10}{season_type}")
    else:
        print(f"  {'Season':<10}{'Regular Season':<20}{'Playoffs':<20}Total")

    for s in seasons:
        sdf = df[df["season"] == s]
        if season_type:
            print(f"  {s:<10}{record(sdf, '-')}")
        else:
            reg = record(sdf[sdf["season_type"] == "Regular Season"], "-")
            po = record(sdf[sdf["season_type"] == "Playoffs"], "-")
            print(f"  {s:<10}{reg:<20}{po:<20}{record(sdf, '-')}")


def print_report(name, df, first, last, season_type):
    if first is None:
        scope = "Career"
    elif first == last:
        scope = f"{season_label(first)} season"
    else:
        scope = f"{season_label(first)} to {season_label(last)}"
    title = f"{name}  |  {scope}" + (f"  |  {season_type}" if season_type else "")
    print("\n" + title)
    print("-" * len(title))

    if len(df) == 0:
        print("No qualifying shots for that player in that window.")
        return

    if season_type:
        print(f"{season_type + ':':<17}{record(df)}")
    else:
        total_label = "Career:" if first is None else "Total:"
        print(f"{total_label:<17}{record(df)}")
        print(f"{'Regular season:':<17}{record(df[df['season_type'] == 'Regular Season'])}")
        print(f"{'Playoffs:':<17}{record(df[df['season_type'] == 'Playoffs'])}")

    if first is None and season_type is None:
        unknown = df[df["season_type"] == "Unknown"]
        if len(unknown):
            print(f"{'Unclassified:':<17}{record(unknown)}  (game not found in {GAMES_FILE})")

    print_season_table(df, season_type)

    if first is None and season_type is None and len(df) < LEADERBOARD_MIN_ATTEMPTS:
        print(f"\nHeads up: that's under the {LEADERBOARD_MIN_ATTEMPTS}-attempt "
              f"leaderboard minimum, so take the percentage with a grain of salt.")
    elif len(df) < 10:
        print("\nSmall sample (under 10 attempts), so the percentage swings a lot.")


def main():
    shots = load_data()
    all_players = players.get_players()
    ids_in_data = set(shots["personId"].unique())
    print(f"Loaded {len(shots)} qualifying shots from {len(ids_in_data)} players.")
    print("\nType a player with an optional season, range, or season type, in any order.")
    print("  e.g.  James Harden 2019 Regular Season  |  Playoffs 2018 LeBron James")
    print("        James Harden 2019-2025            |  Jamal Murray")
    note = "ends" if YEAR_MEANS_SEASON_END else "starts"
    print(f"A lone year means the season that {note} that year.")

    while True:
        query = input("\nSearch (or 'quit'): ").strip()
        if not query:
            continue
        if query.lower() in ("q", "quit", "exit"):
            break

        try:
            name, first, last, season_type = parse_query(query)
        except ValueError as e:
            print(e)
            continue

        in_data, overall = find_matches(name, all_players, ids_in_data)

        if not overall:
            print(f"No player found matching '{name}'. Check the spelling?")
            continue
        if not in_data:
            names = ", ".join(p["full_name"] for p in overall[:5])
            print(f"Found {names}, but no qualifying shots in the dataset.")
            continue

        if len(in_data) == 1:
            player = in_data[0]
        else:
            print("Multiple matches:")
            for i, p in enumerate(in_data, 1):
                print(f"  {i}. {p['full_name']}")
            choice = input("Pick a number: ").strip()
            if not choice.isdigit() or not 1 <= int(choice) <= len(in_data):
                print("That wasn't one of the options.")
                continue
            player = in_data[int(choice) - 1]

        df = shots[shots["personId"] == player["id"]]
        if first is not None:
            df = df[df["season_end_year"].between(first, last)]
        if season_type:
            df = df[df["season_type"] == season_type]

        print_report(player["full_name"], df, first, last, season_type)


if __name__ == "__main__":
    main()