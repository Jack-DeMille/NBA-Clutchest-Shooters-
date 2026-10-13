"""
Builds the "anti-leaderboard": players with the LOWEST career FG% on
potential game-tying/go-ahead shots (<=24s left, 4th/OT), minimum 150
qualifying attempts.

Identical qualification logic to aggregate_results.py - the only
difference is the sort direction, so the worst shooters land at the top.

Run it with: python3 aggregate_anti_leaderboard.py
"""

import pandas as pd
from nba_api.stats.static import players

INPUT_FILE = "clutch_shots.csv"
OUTPUT_FILE = "clutch_anti_leaderboard.csv"
MIN_ATTEMPTS = 100


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

    name_lookup = build_name_lookup()
    leaderboard["player_name"] = leaderboard["personId"].map(name_lookup)
    fallback_names = shots.groupby("personId")["playerName"].first()
    leaderboard["player_name"] = leaderboard["player_name"].fillna(
        leaderboard["personId"].map(fallback_names)
    )

    leaderboard = leaderboard[["personId", "player_name", "attempts", "makes", "fg_pct"]]
    leaderboard = leaderboard.sort_values("fg_pct", ascending=True)  # worst first

    leaderboard.to_csv(OUTPUT_FILE, index=False)
    print(f"Saved {len(leaderboard)} qualifying players to {OUTPUT_FILE}\n")
    print(leaderboard.head(20).to_string(index=False))


if __name__ == "__main__":
    main()