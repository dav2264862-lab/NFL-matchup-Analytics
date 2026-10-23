import pandas as pd

# Load the same player data as our NFL dashboard
players = pd.read_csv("nfl_player_stats_2026.csv")

# Choose the week we want to analyze
week = 7

# Only use games before the selected week
history = players[players["week"] < week].copy()

# Keep tight ends only
tight_ends = history[history["position"] == "TE"].copy()

# First, total all TE stats against each defense each week
te_weekly = (
    tight_ends.groupby(["opponent_team", "week"])[
        ["targets", "receptions", "receiving_yards"]
    ]
    .sum()
    .reset_index()
)

# Include games where a defense allowed zero TE production
all_games = history[["opponent_team", "week"]].drop_duplicates()

te_weekly = all_games.merge(
    te_weekly,
    on=["opponent_team", "week"],
    how="left"
)

te_weekly[["targets", "receptions", "receiving_yards"]] = (
    te_weekly[["targets", "receptions", "receiving_yards"]].fillna(0)
)

# Then calculate average TE production allowed per game
te_defense = (
    te_weekly.groupby("opponent_team")[
        ["targets", "receptions", "receiving_yards"]
    ]
    .mean()
    .reset_index()
)

# Rename columns
te_defense = te_defense.rename(columns={
    "opponent_team": "defense",
    "targets": "te_targets_allowed",
    "receptions": "te_receptions_allowed",
    "receiving_yards": "te_yards_allowed"
})

# Display the results
print("\nNFL DEFENSE VS TIGHT ENDS")
print(te_defense.round(2).to_string(index=False))

# Calculate league averages against tight ends
league_avg = te_defense[
    ["te_targets_allowed", "te_receptions_allowed", "te_yards_allowed"]
].mean()

# Compare each defense to the league average
te_defense["matchup_score"] = (
    te_defense["te_yards_allowed"] / league_avg["te_yards_allowed"]
)

# Give each defense a matchup rating
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

te_defense["matchup_rating"] = te_defense["matchup_score"].apply(rate_matchup)

# Show defenses ranked from easiest to hardest for tight ends
print("\nTE MATCHUP RANKINGS")
print(
    te_defense[
        ["defense", "te_yards_allowed", "matchup_score", "matchup_rating"]
    ]
    .sort_values("matchup_score", ascending=False)
    .round(2)
    .to_string(index=False)
)

# Save tight end defensive matchup ratings
te_defense.to_csv("te_defensive_matchups_2026.csv", index=False)

print("\nTE matchup ratings saved successfully!")