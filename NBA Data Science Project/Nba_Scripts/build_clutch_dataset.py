"""
Walks every game in games.csv, pulls its play-by-play, and saves only the
shot attempts that qualify as "potential game-tying or go-ahead shots":
<=24 seconds left in the 4th quarter/OT, where the shot's point value is
enough to tie or take the lead (team must be trailing or tied entering
the shot).

Resumable: progress is checkpointed in processed_games.txt, so
interrupting and rerunning picks up where it left off - safe to Ctrl+C
any time. Games that error out are logged to failed_games.txt instead of
being marked done, so a rerun automatically retries them rather than
silently dropping them from the dataset.

Run it with: python3 build_clutch_dataset.py
"""

import os
import re
import time
import pandas as pd
from concurrent.futures import ThreadPoolExecutor, as_completed
from nba_api.stats.endpoints import playbyplayv3

GAMES_FILE = "games.csv"
OUTPUT_FILE = "clutch_shots.csv"
PROGRESS_FILE = "processed_games.txt"
FAILED_FILE = "failed_games.txt"

CLOCK_CUTOFF_SECONDS = 24
CLOCK_PATTERN = re.compile(r"PT(\d+)M([\d.]+)S")

REQUEST_TIMEOUT = 15            # seconds - fail fast instead of hanging
SLEEP_BETWEEN_REQUESTS = 0.8    # 0.4 was too aggressive and triggered
                                 # throttling - keep this at 0.6+ for safety
MAX_RETRIES = 3                 # per-game retry attempts before giving up
MAX_WORKERS = 1                 # fetch this many games in parallel - see
                                 # the note at the bottom of this file
                                 # before raising this


def clock_to_seconds(clock_str):
    """Converts a clock string like 'PT00M18.00S' to seconds remaining."""
    match = CLOCK_PATTERN.match(str(clock_str))
    if not match:
        return None
    minutes, seconds = match.groups()
    return int(minutes) * 60 + float(seconds)


def load_ids(path):
    if not os.path.exists(path):
        return set()
    with open(path) as f:
        return set(line.strip() for line in f if line.strip())


def append_id(path, game_id):
    with open(path, "a") as f:
        f.write(f"{game_id}\n")


def find_qualifying_shots(df, home_team_id, away_team_id):
    """Returns the subset of rows that are potential tying/go-ahead shots."""
    df = df.sort_values("actionNumber").reset_index(drop=True)

    # scoreHome/scoreAway only populate on scoring plays - forward-fill to
    # get the running score at every point, then shift by 1 so we know the
    # score as it stood BEFORE each play (not after it).
    home_score = pd.to_numeric(df["scoreHome"], errors="coerce").ffill().fillna(0)
    away_score = pd.to_numeric(df["scoreAway"], errors="coerce").ffill().fillna(0)
    df["home_score_entering"] = home_score.shift(1).fillna(0)
    df["away_score_entering"] = away_score.shift(1).fillna(0)

    df["is_field_goal"] = pd.to_numeric(df["isFieldGoal"], errors="coerce").fillna(0)
    shots = df[df["is_field_goal"] == 1].copy()
    if shots.empty:
        return shots

    shots["seconds_remaining"] = shots["clock"].apply(clock_to_seconds)
    shots["shot_value"] = shots["description"].apply(
        lambda d: 3 if "3PT" in str(d) else 2
    )
    shots["team_id"] = pd.to_numeric(shots["teamId"], errors="coerce")

    def deficit(row):
        if row["team_id"] == home_team_id:
            return row["away_score_entering"] - row["home_score_entering"]
        else:
            return row["home_score_entering"] - row["away_score_entering"]

    shots["deficit"] = shots.apply(deficit, axis=1)

    qualifying = shots[
        (shots["period"] >= 4)
        & (shots["seconds_remaining"] <= CLOCK_CUTOFF_SECONDS)
        & (shots["deficit"] >= 0)
        & (shots["deficit"] <= shots["shot_value"])
    ]

    return qualifying[[
        "gameId", "period", "clock", "personId", "playerName",
        "shot_value", "shotResult", "deficit",
    ]]


def fetch_game(game_id, home_team_id, away_team_id):
    """Fetches and filters one game, retrying a couple times on failure."""
    last_error = None
    for attempt in range(MAX_RETRIES + 1):
        try:
            pbp = playbyplayv3.PlayByPlayV3(game_id=game_id, timeout=REQUEST_TIMEOUT)
            df = pbp.get_data_frames()[0]
            time.sleep(SLEEP_BETWEEN_REQUESTS)  # paces this worker's own requests
            return find_qualifying_shots(df, home_team_id, away_team_id)
        except Exception as e:
            last_error = e
            time.sleep(10 * (attempt + 1))  # escalating backoff (10s, 20s, 30s) so a
            # throttle has time to cool off before the next try
    raise last_error


def process_game(row):
    try:
        qualifying = fetch_game(row.game_id, row.home_team_id, row.away_team_id)
        return row.game_id, qualifying, None
    except Exception as e:
        return row.game_id, None, str(e)


def main():
    games = pd.read_csv(GAMES_FILE, dtype={"game_id": str})
    done = load_ids(PROGRESS_FILE)
    remaining = games[~games["game_id"].isin(done)]
    print(f"{len(done)} games already done, {len(remaining)} to go.")

    rows = list(remaining.itertuples())
    completed = 0

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process_game, row) for row in rows]
        for future in as_completed(futures):
            game_id, qualifying, error = future.result()

            if error:
                print(f"  Game {game_id} failed: {error}")
                append_id(FAILED_FILE, game_id)
            else:
                if qualifying is not None and not qualifying.empty:
                    qualifying.to_csv(
                        OUTPUT_FILE, mode="a", index=False,
                        header=not os.path.exists(OUTPUT_FILE),
                    )
                append_id(PROGRESS_FILE, game_id)

            completed += 1
            if completed % 25 == 0:
                print(f"  ...{completed}/{len(rows)} games processed")

    print("\nDone. Qualifying shots saved to", OUTPUT_FILE)
    if os.path.exists(FAILED_FILE):
        print(f"Some games failed - see {FAILED_FILE}. Just rerun this "
              f"script to automatically retry them.")


if __name__ == "__main__":
    main()

# --- Want it faster still? ---
# Bump MAX_WORKERS up to 3 or 4 to fetch multiple games at once - a real
# speedup, since each worker paces its own requests independently. But it
# also means hitting stats.nba.com harder, which raises the chance of
# getting rate-limited or temporarily blocked. If you try it and
# failed_games.txt starts filling up fast, that's your signal to dial
# MAX_WORKERS back down.