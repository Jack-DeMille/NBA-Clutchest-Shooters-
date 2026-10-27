"""
Interactive Plotly version of the clutch-shooter leaderboard.

Instead of static text labels fighting for space, hover over any bar or
point to see the exact player and stats. The scatter plot also encodes
two extra dimensions visually: marker SIZE = attempts, marker COLOR =
FG%, so reliable high-volume shooters visually pop out from small-sample
noise without reading a single number.

Run it with: python3 visualize_interactive.py
Saves clutch_dashboard.html - double-click it to open in a browser.
No Python needed to view it once it's saved; you could host this exact
file on GitHub Pages for a live, shareable link.
"""

import pandas as pd
from plotly.subplots import make_subplots
import plotly.graph_objects as go

INPUT_FILE = "clutch_leaderboard.csv"
OUTPUT_FILE = "clutch_dashboard.html"
TOP_N = 15


def hover_text(df):
    return [
        f"{name}<br>{makes}/{att} ({pct:.1%})"
        for name, makes, att, pct in zip(
            df["player_name"], df["makes"], df["attempts"], df["fg_pct"]
        )
    ]


def main():
    df = pd.read_csv(INPUT_FILE)
    top = df.sort_values("fg_pct", ascending=False).head(TOP_N)

    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.55, 0.45],
        subplot_titles=(
            f"Top {TOP_N} Clutch Shooters (min 150 attempts)",
            "Attempts vs. FG% \u2014 All Qualifying Players",
        ),
        vertical_spacing=0.15,
    )

    # --- Panel 1: leaderboard bar chart ---
    # Reverse the order so the highest FG% ends up at the top of the chart
    top_rev = top.iloc[::-1]
    fig.add_trace(
        go.Bar(
            y=top_rev["player_name"],
            x=top_rev["fg_pct"],
            orientation="h",
            marker_color="#1d428a",
            hovertext=hover_text(top_rev),
            hoverinfo="text",
        ),
        row=1, col=1,
    )

    # --- Panel 2: attempts vs FG% scatter, ALL qualifying players ---
    # Marker size = attempts (bubble chart sizing formula, per Plotly docs)
    max_attempts = df["attempts"].max()
    fig.add_trace(
        go.Scatter(
            x=df["attempts"],
            y=df["fg_pct"],
            mode="markers",
            marker=dict(
                size=df["attempts"],
                sizemode="area",
                sizeref=2. * max_attempts / (40. ** 2),
                sizemin=4,
                color=df["fg_pct"],
                colorscale="Reds",
                showscale=True,
                colorbar=dict(title="FG%", tickformat=".0%", y=0.2, len=0.4),
            ),
            hovertext=hover_text(df),
            hoverinfo="text",
        ),
        row=2, col=1,
    )

    fig.update_xaxes(title_text="FG% on potential tying/go-ahead shots",
                      tickformat=".0%", row=1, col=1)
    fig.update_xaxes(title_text="Qualifying attempts", row=2, col=1)
    fig.update_yaxes(title_text="FG%", tickformat=".0%", row=2, col=1)

    fig.update_layout(
        height=950,
        showlegend=False,
        title_text="NBA Clutch Shooters: Potential Tying/Go-Ahead Shots (\u226424s left, 4th/OT)",
        template="plotly_white",
    )

    fig.write_html(OUTPUT_FILE)
    print(f"Saved {OUTPUT_FILE} - open it in a browser to explore")


if __name__ == "__main__":
    main()