"""
Builds the master list of games to pull play-by-play for.

For each season in the configured range, this fetches every game (regular
season + playoffs) along with which team was home vs away, and saves it
all to games.csv. build_clutch_dataset.py reads this file to know which
games to fetch.

Reliable play-by-play data really only goes back to the 1996-97 season -
widen START_SEASON_YEAR down to 1996 once you're ready for full history.

Run it with: python3 get_game_ids.py
"""

import time
import pandas as pd
from nba_api.stats.endpoints import leaguegamelog

# --- Configuration: adjust this range any time and just rerun ---
START_SEASON_YEAR = 1996   # 1996 -> "1996-97" season
END_SEASON_YEAR = 2025     # 2025 -> "2025-26" season

SEASON_TYPES = ["Regular Season", "Playoffs"]


def season_str(year):
    return f"{year}-{str(year + 1)[-2:]}"


def main():
    all_games = []

    for year in range(START_SEASON_YEAR, END_SEASON_YEAR + 1):
        season = season_str(year)
        for season_type in SEASON_TYPES:
            print(f"Fetching {season} {season_type}...")
            try:
                log = leaguegamelog.LeagueGameLog(
                    season=season, season_type_all_star=season_type
                )
                df = log.get_data_frames()[0]
            except Exception as e:
                print(f"  Skipped ({e})")
                continue

            if df.empty:
                continue

            # One row per team per game - figure out home vs away from
            # MATCHUP text ("LAL vs. OKC" = home, "LAL @ OKC" = away)
            df["IS_HOME"] = df["MATCHUP"].str.contains("vs.", regex=False)

            for game_id, group in df.groupby("GAME_ID"):
                home_row = group[group["IS_HOME"]]
                away_row = group[~group["IS_HOME"]]
                if home_row.empty or away_row.empty:
                    continue  # incomplete data for this game, skip it

                all_games.append({
                    "game_id": game_id,
                    "season": season,
                    "season_type": season_type,
                    "game_date": group.iloc[0]["GAME_DATE"],
                    "home_team_id": home_row.iloc[0]["TEAM_ID"],
                    "away_team_id": away_row.iloc[0]["TEAM_ID"],
                })

            time.sleep(0.6)  # be polite to the API

    games_df = pd.DataFrame(all_games).drop_duplicates(subset="game_id")
    games_df.to_csv("games.csv", index=False)
    print(f"\nSaved {len(games_df)} games to games.csv")


if __name__ == "__main__":
    main()