"""
Aggregates clutch_shots.csv into a per-player leaderboard: career FG% on
potential game-tying/go-ahead shots in the final 24 seconds of the 4th
quarter/OT, minimum 5 qualifying attempts.

Run it with: python3 aggregate_results.py
"""

import pandas as pd
from nba_api.stats.static import players

INPUT_FILE = "clutch_shots.csv"
OUTPUT_FILE = "clutch_leaderboard.csv"
MIN_ATTEMPTS = 150


def build_name_lookup():
    """Maps personId -> full player name using nba_api's built-in player list."""
    all_players = players.get_players()
    return {p["id"]: p["full_name"] for p in all_players}


def main():
    shots = pd.read_csv(INPUT_FILE)
    shots["made"] = (shots["shotResult"] == "Made").astype(int)

    leaderboard = (
        shots.groupby("personId")
        .agg(attempts=("made", "count"), makes=("made", "sum"))
        .reset_index()
    )
    leaderboard = leaderboard[leaderboard["attempts"] >= MIN_ATTEMPTS].copy()
    leaderboard["fg_pct"] = (leaderboard["makes"] / leaderboard["attempts"]).round(3)

    # Full names from nba_api's static player list, keyed by personId
    name_lookup = build_name_lookup()
    leaderboard["player_name"] = leaderboard["personId"].map(name_lookup)

    # Fallback for anyone missing from that list (can happen with very
    # recent rookies) - just use whatever name showed up in the raw data
    fallback_names = shots.groupby("personId")["playerName"].first()
    leaderboard["player_name"] = leaderboard["player_name"].fillna(
        leaderboard["personId"].map(fallback_names)
    )

    leaderboard = leaderboard[["personId", "player_name", "attempts", "makes", "fg_pct"]]
    leaderboard = leaderboard.sort_values("fg_pct", ascending=False)

    leaderboard.to_csv(OUTPUT_FILE, index=False)
    print(f"Saved {len(leaderboard)} qualifying players to {OUTPUT_FILE}\n")
    print(leaderboard.head(20).to_string(index=False))


if __name__ == "__main__":
    main()