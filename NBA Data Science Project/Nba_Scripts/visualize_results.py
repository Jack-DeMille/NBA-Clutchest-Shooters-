"""
Quick starter visualization: a bar chart of the top clutch shooters, and a
scatter plot showing the attempts-vs-FG% tradeoff (this is what makes the
small-sample noise at the top of the leaderboard visible).

Run it with: python3 visualize_results.py
Saves two PNG files in this folder - open them directly to view.
"""

import pandas as pd
import matplotlib.pyplot as plt
from adjustText import adjust_text

INPUT_FILE = "clutch_leaderboard.csv"
TOP_N = 15


def main():
    df = pd.read_csv(INPUT_FILE)
    top = df.sort_values("fg_pct", ascending=False).head(TOP_N)

    # --- Chart 1: horizontal bar chart of the top clutch shooters ---
    fig, ax = plt.subplots(figsize=(8, 6))
    ax.barh(top["player_name"], top["fg_pct"], color="#1d428a")
    ax.invert_yaxis()  # highest FG% at the top
    ax.set_xlabel("FG% on potential tying/go-ahead shots (\u226424s left, 4th/OT)")
    ax.set_title(f"Top {TOP_N} Clutch Shooters (min 150 attempts)")
    for i, (pct, attempts) in enumerate(zip(top["fg_pct"], top["attempts"])):
        ax.text(pct + 0.01, i, f"{attempts} att", va="center", fontsize=8)
    plt.tight_layout()
    plt.savefig("clutch_leaderboard_bar.png", dpi=150)
    print("Saved clutch_leaderboard_bar.png")

    # --- Chart 2: attempts vs FG%, to visualize the small-sample effect ---
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.scatter(df["attempts"], df["fg_pct"], alpha=0.7, color="#c8102e")

    # adjustText automatically spreads out overlapping labels and draws a
    # thin connector line back to the actual point - much cleaner than
    # manually offsetting text when points are close together.
    # Some players land on the exact same point (identical attempts + FG%,
    # i.e. a tie). Merge their names into one label instead of letting
    # adjustText fight to separate two labels that belong at the same spot.
    top25 = df.head(25).copy()
    grouped = (
        top25.groupby(["attempts", "fg_pct"])["player_name"]
        .apply(lambda names: " / ".join(names))
        .reset_index()
    )

    texts = [
        ax.text(row["attempts"], row["fg_pct"], row["player_name"], fontsize=8)
        for _, row in grouped.iterrows()
    ]
    adjust_text(texts, arrowprops=dict(arrowstyle="-", color="gray", lw=0.5))

    ax.set_xlabel("Qualifying attempts")
    ax.set_ylabel("FG%")
    ax.set_title("Attempts vs. FG% (more attempts = more reliable %)")
    plt.tight_layout()
    plt.savefig("attempts_vs_fgpct.png", dpi=150)
    print("Saved attempts_vs_fgpct.png")


if __name__ == "__main__":
    main()
