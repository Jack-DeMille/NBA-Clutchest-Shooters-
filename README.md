# Who is the most clutch shooter in NBA History?

When the pressure is on, the lights are bright, and the margin for error is none, who can deliver in the clutch in order to help their team win?

**See it for yourself:**

- [Interactive dashboard](https://jack-demille.github.io/NBA-Clutchest-Shooters-/NBA%20Data%20Science%20Project/Nba_Scripts/clutch_dashboard.html): hover over any bar or dot to see a player's exact makes and attempts.
- [Slide deck](https://jack-demille.github.io/NBA-Clutchest-Shooters-/clutch_deck.html): the whole story, plus a player checker where you can look up any player.

The data covers 30 seasons of play-by-play (1996-97 through 2025-26), so "history" here means the modern era.

![Top 15 clutch shooters by FG%](NBA%20Data%20Science%20Project/charts/clutch_leaderboard_bar.png)

## So what is defined as a clutch shot?

For the purpose of this project, a clutch shot is defined as a shot taken by a player to tie or take the lead in a game where there are 24 or fewer seconds left on the clock in the fourth quarter or overtime. For example, let's say the score is 110-110, there are ten seconds left in the game, and a player attempts a three-point shot to take the lead in the game. This is a shot that I would define as clutch due to the importance of the result of the shot and how little time there is left in the game.

Here's the flip side. If a team is down 3 and takes a two-pointer, that shot does **not** count, because even if it goes in they're still losing. Only a three would tie it. Free throws don't count either, only shots from the field.

## Why is it important to know who the most clutch shooters are?

It's super important to know who is historically better at shooting "clutch" shots because it shows which players have actually made them at a higher rate when the pressure is on. This can help inform decisions for teams about which players should get the ball when the pressure is high, and they need a clutch bucket.

## What was my inspiration behind this project?

I'm an avid sports fan; I really love working with computer science, and I want to pursue a career in sports analytics. The real reason I started this project is actually that I saw a TikTok about some of Isaiah Thomas' clutch buckets, and it made me think, "Wow, that's really neat, but I don't wanna scour highlights all day just to see who's a clutch shooter; how can I use my coding skills to figure this out?"

## So who actually came out on top?

To make sure nobody gets on the list off a lucky handful of shots, a player needs at least **150** of these attempts to qualify. Across all shooters, the league-wide FG% on these shots is **35.8%**, so that's the number to beat.

**Tim Duncan came out on top at 43.3% on 178 attempts**, a full 7.5 points above the league average. Dirk Nowitzki is right behind him.

| Rank | Player | FG% (rounded) | Attempts |
|---|---|---|---|
| 1 | Tim Duncan | 43% | 178 |
| 2 | Dirk Nowitzki | 41% | 182 |
| 3 | Rudy Gay | 38% | 150 |
| 4 | Allen Iverson | 38% | 151 |
| 5 | Kevin Garnett | 37% | 189 |

A few things stood out to me:

- **Kobe Bryant took by far the most of these shots (388)** and made a little under a third of them, a bit below the league average. LeBron James has the second most at 308 and sits right around the average at about 35%.
- **Jason Kidd sits at the bottom at roughly 23%.** The rest of the bottom five are Dwyane Wade (about 27%), Andre Iguodala and Paul Pierce (both about 28%), and Jamal Crawford and Russell Westbrook (both about 29%).
- Rudy Gay and Allen Iverson only just cleared the 150 minimum, so their spots are the shakiest on the board.
- Isaiah Thomas, the guy who started all this, didn't take enough of these shots to reach 150, so he isn't on the board. You can still look him up in the player checker in the slide deck.

![Attempts vs. FG% for every player with 150+ attempts](NBA%20Data%20Science%20Project/charts/attempts_vs_fgpct.png)

## How much should we trust these numbers?

Not as much as the chart makes it look. Even with 150+ attempts, a shooting percentage can easily move 7 or 8 points up or down from luck alone, so two players a few points apart can't really be separated. Duncan and Dirk stand out from the pack more than anyone in the middle stands out from anyone else. This is a ranking of who made these specific shots, not a final ruling on who is the most clutch player ever.

## How does the project work?

1. **Pull every game.** I collect the play-by-play (every shot, rebound, and foul, with the clock and the score) for each regular-season and playoff game using the `nba_api` Python library.
2. **Rebuild the score before every shot.** The data only records the score when someone scores, so I fill it in and shift it by one row to know the score *right before* each shot was taken.
3. **Keep only the clutch shots.** A shot qualifies if it's in the fourth quarter or overtime, has 24 or fewer seconds left, and would tie the game or take the lead if it went in.
4. **Rank the players.** I add up each player's makes and attempts, drop anyone under 150 attempts, and sort by FG%.

The leaderboards combine regular season and playoffs. The player checker in the deck lets you split them.

## What are the limits of this?

- **FG% mixes twos and threes.** Down 3, only threes count. Down 1 or 2, both count. A player who mostly gets three-point looks will have a lower FG% for reasons that have nothing to do with skill.
- **It doesn't know how hard the shot was.** There's no data here on how closely a shot was guarded or where it was taken.
- **Coaches choose who shoots.** The results show who made these shots among the players who were given the chance.
- **A few games are missing.** Some games failed to load or have no play-by-play, and the play-in tournament isn't included.

## Want to run it yourself?

You'll need Python and about a couple of hours of patience for the data pull. There's no API key to sign up for.

```bash
pip3 install -r requirements.txt
python3 get_game_ids.py             # builds the list of games
python3 build_clutch_dataset.py     # the slow one (hours); safe to stop and restart
python3 aggregate_results.py        # the leaderboard
python3 aggregate_anti_leaderboard.py
python3 visualize_results.py        # the charts
python3 visualize_interactive.py    # the interactive dashboard
python3 player_search.py            # type a name like "Playoffs 2018 LeBron James"
```

Run these from the folder that holds the scripts. The raw play-by-play files aren't in this repo because the scripts generate them.

## How I built this

I want to be upfront: I used Claude, an AI assistant, as a coding partner on this project. The idea, the definition of a clutch shot, and the decisions about how to measure it (like the 150-attempt minimum) are mine, and I ran and debugged everything myself in PyCharm.

Built with Python, pandas, `nba_api`, matplotlib, and Plotly. The data comes from the NBA's stats endpoints through `nba_api`.

## About me

Built by [Jack DeMille](https://github.com/Jack-DeMille).  
[LinkedIn](www.linkedin.com/in/jack-demille)
