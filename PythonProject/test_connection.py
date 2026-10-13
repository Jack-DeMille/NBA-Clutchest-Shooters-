"""
Quick connectivity test for nba_api.

This confirms three things before we build the real pipeline:
1. We can reach stats.nba.com from this machine
2. We can look up a real game
3. We can pull that game's play-by-play data

Uses PlayByPlayV3 (V2 was deprecated and no longer returns data as of 2025).

Run it with: python3 test_connection.py
"""

from nba_api.stats.static import teams
from nba_api.stats.endpoints import leaguegamefinder, playbyplayv3


def main():
    # Step 1: look up a team (Lakers, just as an example - any team works)
    lakers = teams.find_teams_by_full_name("Los Angeles Lakers")[0]
    print(f"Found team: {lakers['full_name']} (ID: {lakers['id']})")

    # Step 2: pull that team's full game log and grab the most recent game
    print("\nFetching game log...")
    gamefinder = leaguegamefinder.LeagueGameFinder(team_id_nullable=lakers["id"])
    games = gamefinder.get_data_frames()[0]
    games = games.sort_values("GAME_DATE", ascending=False)
    most_recent = games.iloc[0]
    game_id = most_recent["GAME_ID"]
    print(f"Most recent game: {most_recent['MATCHUP']} on {most_recent['GAME_DATE']} "
          f"(Game ID: {game_id})")

    # Step 3: pull the play-by-play for that game
    print("\nFetching play-by-play...")
    pbp = playbyplayv3.PlayByPlayV3(game_id=game_id)
    df = pbp.get_data_frames()[0]  # index 0 = "PlayByPlay" dataset
    print(f"Success! Pulled {len(df)} play-by-play events.\n")

    # Peek at the columns we'll actually rely on for the real analysis:
    # period, clock (time remaining), scoreHome/scoreAway, isFieldGoal (is
    # this a shot attempt), shotResult (Made/Missed), and description
    relevant_cols = ["period", "clock", "scoreHome", "scoreAway",
                      "isFieldGoal", "shotResult", "description"]
    print("Sample of the columns we'll actually use later:")
    print(df[relevant_cols].head(10).to_string(index=False))


if __name__ == "__main__":
    main()