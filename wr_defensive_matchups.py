import pandas as pd

# Load NFL player statistics
players = pd.read_csv("nfl_player_stats_2026.csv")

# Analyze games before Week 7
week = 7
history = players[players["week"] < week].copy()

# Keep wide receivers only
wr = history[history["position"] == "WR"].copy()

# Total WR production allowed by each defense per week
wr_weekly = (
    wr.groupby(["opponent_team", "week"])[
        ["targets", "receptions", "receiving_yards"]
    ]
    .sum()
    .reset_index()
)

# Include games where no WR production was recorded
all_games = history[["opponent_team", "week"]].drop_duplicates()

wr_weekly = all_games.merge(
    wr_weekly,
    on=["opponent_team", "week"],
    how="left"
)

wr_weekly[
    ["targets", "receptions", "receiving_yards"]
] = wr_weekly[
    ["targets", "receptions", "receiving_yards"]
].fillna(0)

# Average WR production allowed per game
wr_defense = (
    wr_weekly.groupby("opponent_team")[
        ["targets", "receptions", "receiving_yards"]
    ]
    .mean()
    .reset_index()
)

# Rename columns
wr_defense = wr_defense.rename(columns={
    "opponent_team": "defense",
    "targets": "wr_targets_allowed",
    "receptions": "wr_receptions_allowed",
    "receiving_yards": "wr_yards_allowed"
})

# Compare each defense against league average
league_avg = wr_defense["wr_yards_allowed"].mean()

wr_defense["matchup_score"] = (
    wr_defense["wr_yards_allowed"] / league_avg
)

# Rate defensive matchups
def rate_matchup(score):
    if score >= 1.15:
        return "Very Favorable"
    elif score >= 1.05:
        return "Favorable"
    elif score <= 0.85:
        return "Very Difficult"
    elif score <= 0.95:
        return "Difficult"
    else:
        return "Neutral"

wr_defense["matchup_rating"] = (
    wr_defense["matchup_score"].apply(rate_matchup)
)

# Display WR matchup rankings
print("\nWR DEFENSIVE MATCHUP RANKINGS")
print(
    wr_defense.sort_values(
        "matchup_score", ascending=False
    ).round(2).to_string(index=False)
)

# Save results
wr_defense.to_csv(
    "wr_defensive_matchups_2026.csv",
    index=False
)

print("\nWR matchup ratings saved successfully!")