
import pandas as pd

# Load player statistics and NFL schedule
players = pd.read_csv("nfl_player_stats_2026.csv")
schedule = pd.read_csv("nfl_schedule_2026.csv")
print("Opponent column exists:", "opponent_team" in players.columns)
# Keep only offensive skill players
players = players[
    players["position"].isin(["QB", "RB", "WR", "TE"])
].copy()

# Show the latest week with player statistics
print("Latest player stats week:")
print(players["week"].max())

# Check which games are on the schedule for Week 7
week = 7

games = schedule[
    (schedule["week"] == week) &
    (schedule["game_type"] == "REG")
]

print("\nWeek 7 games:")
print(games[["away_team", "home_team"]].to_string(index=False))

# Check the player information available
print("\nPlayer columns:")
print([
    col for col in players.columns
    if col in ["player_id", "player_display_name",
               "position", "team", "recent_team", "week"]
])


# Build projections using games before Week 6
history = players[players["week"] < week].copy()

# Calculate defensive averages by position
defense_stats = (
    history.groupby(["opponent_team", "position"])[
        ["passing_yards", "rushing_yards", "receiving_yards", "receptions"]
    ]
    .mean()
    .reset_index()
)

print("\nDefensive averages by position:")
print(defense_stats.head(10))

stats = [
    "passing_yards",
    "rushing_yards",
    "receiving_yards",
    "receptions",
    "targets"
]

# Calculate season averages and recent averages
history = history.sort_values(["player_id", "week"])

season_avg = history.groupby("player_id")[stats].mean()
last3_avg = (
    history.groupby("player_id")
    .tail(3)
    .groupby("player_id")[stats]
    .mean()
)

# Combine season and recent performance
projections = (
    season_avg * 0.60 +
    last3_avg * 0.40
).reset_index()

# Add player names, positions, and teams
player_details = (
    history.groupby("player_id")
    .tail(1)[
        ["player_id", "player_display_name", "position", "team"]
    ]
)

projections = projections.merge(
    player_details,
    on="player_id",
    how="left",
    validate="one_to_one"
)

# Keep players whose teams are scheduled for Week 6
scheduled_teams = set(games["home_team"]) | set(games["away_team"])

projections = projections[
    projections["team"].isin(scheduled_teams)
].copy()

# Attach each player's Week 6 opponent
matchups = pd.concat([
    games[["home_team", "away_team"]].rename(
        columns={"home_team": "team", "away_team": "opponent_team"}
    ),
    games[["away_team", "home_team"]].rename(
        columns={"away_team": "team", "home_team": "opponent_team"}
    )
], ignore_index=True)

projections = projections.merge(
    matchups,
    on="team",
    how="inner",
    validate="many_to_one"
)

projections["week"] = week

# Compare each defense against the league average by position
defense_columns = [
    "passing_yards",
    "rushing_yards",
    "receiving_yards",
    "receptions"
]

league_avg = history.groupby("position")[defense_columns].mean()

# Calculate how tough or easy each defensive matchup is
for stat in defense_columns:
    defense_stats[stat + "_factor"] = defense_stats.apply(
        lambda row: (
            row[stat] / league_avg.loc[row["position"], stat]
            if league_avg.loc[row["position"], stat] > 0
            else 1.0
        ),
        axis=1
    )

# Attach defensive matchup factors to player projections
factor_columns = [stat + "_factor" for stat in defense_columns]

projections = projections.merge(
    defense_stats[
        ["opponent_team", "position"] + factor_columns
    ],
    on=["opponent_team", "position"],
    how="left",
    validate="many_to_one"
)

# Load our improved tight end defensive ratings
te_matchups = pd.read_csv("te_defensive_matchups_2026.csv")

# Attach each defense's TE matchup score
projections = projections.merge(
    te_matchups[
    ["defense", "matchup_score",
     "te_targets_allowed", "te_receptions_allowed"]
],
    left_on="opponent_team",
    right_on="defense",
    how="left",
    validate="many_to_one"
)

# Replace the old TE receiving-yard factor
te_mask = projections["position"] == "TE"

projections.loc[
    te_mask, "receiving_yards_factor"
] = projections.loc[te_mask, "matchup_score"].fillna(1.0)

# Calculate league averages allowed to tight ends
avg_te_receptions = te_matchups["te_receptions_allowed"].mean()
avg_te_targets = te_matchups["te_targets_allowed"].mean()

# Adjust TE receptions based on opposing defense
if avg_te_receptions > 0:
    projections.loc[te_mask, "receptions_factor"] = (
        projections.loc[te_mask, "te_receptions_allowed"]
        / avg_te_receptions
    )

# Adjust TE targets based on opposing defense
projections["targets_factor"] = 1.0

if avg_te_targets > 0:
    projections.loc[te_mask, "targets_factor"] = (
        projections.loc[te_mask, "te_targets_allowed"]
        / avg_te_targets
    )

# Apply a maximum 15% defensive adjustment
for stat in defense_columns:
    factor = projections[stat + "_factor"].fillna(1.0)
    factor = factor.clip(lower=0.85, upper=1.15)

    if stat in ["receiving_yards", "receptions"]:
        factor.loc[projections["position"] == "WR"] = 1.0

    projections[stat] = projections[stat] * factor

    # Apply the defensive adjustment to TE targets
te_target_factor = (
    projections.loc[te_mask, "targets_factor"]
    .fillna(1.0)
    .clip(0.85, 1.15)
)

projections.loc[te_mask, "targets"] = (
    projections.loc[te_mask, "targets"] * te_target_factor
)
# Load wide receiver defensive matchup ratings
wr_matchups = pd.read_csv("wr_defensive_matchups_2026.csv")

# Attach WR defensive stats to player projections
projections = projections.merge(
    wr_matchups[
        ["defense", "wr_targets_allowed",
         "wr_receptions_allowed", "wr_yards_allowed"]
    ],
    left_on="opponent_team",
    right_on="defense",
    how="left",
    validate="many_to_one",
    suffixes=("", "_wr")
)

# Only adjust wide receivers
wr_mask = projections["position"] == "WR"

# Prevent double-counting the original WR defense adjustment
for stat in ["receiving_yards", "receptions"]:
    projections.loc[wr_mask, stat + "_factor"] = 1.0

# Calculate league averages
avg_wr_yards = wr_matchups["wr_yards_allowed"].mean()
avg_wr_receptions = wr_matchups["wr_receptions_allowed"].mean()
avg_wr_targets = wr_matchups["wr_targets_allowed"].mean()

# Adjust WR receiving yards, receptions, and targets
for stat, allowed_col, league_avg in [
    ("receiving_yards", "wr_yards_allowed", avg_wr_yards),
    ("receptions", "wr_receptions_allowed", avg_wr_receptions),
    ("targets", "wr_targets_allowed", avg_wr_targets)
]:
    if league_avg > 0:
        factor = (
            projections.loc[wr_mask, allowed_col] / league_avg
        ).fillna(1.0).clip(0.85, 1.15)

        projections.loc[wr_mask, stat] = (
            projections.loc[wr_mask, stat] * factor
        )

print("WR defensive matchup adjustments applied!")

# Identify likely starting quarterbacks using recent passing volume
qb_history = history[history["position"] == "QB"]

qb_volume = (
    qb_history.groupby(["team", "player_id"])["attempts"]
    .sum()
    .reset_index(name="pass_attempts")
)

qb_volume["qb_rank"] = (
    qb_volume.groupby("team")["pass_attempts"]
    .rank(method="first", ascending=False)
)

projections = projections.merge(
    qb_volume[["team", "player_id", "qb_rank"]],
    on=["team", "player_id"],
    how="left",
    validate="one_to_one"
)

projections["likely_starting_qb"] = (
    (projections["position"] == "QB") &
    (projections["qb_rank"] == 1)
)
# Rank RB, WR, and TE players by recent offensive usage
skill_history = history[
    history["position"].isin(["RB", "WR", "TE"])
].copy()

# Use the last 3 recorded games for each player
recent_skill = (
    skill_history
    .sort_values(["player_id", "week"])
    .groupby("player_id")
    .tail(3)
)

# Carries for running backs, targets for receivers and tight ends
recent_skill["usage"] = (
    recent_skill["carries"].fillna(0)
    + recent_skill["targets"].fillna(0)
)

usage_avg = (
    recent_skill.groupby(["team", "position", "player_id"])["usage"]
    .mean()
    .reset_index(name="recent_usage")
)

usage_avg["usage_rank"] = (
    usage_avg.groupby(["team", "position"])["recent_usage"]
    .rank(method="first", ascending=False)
)

projections = projections.merge(
    usage_avg[["team", "position", "player_id",
               "recent_usage", "usage_rank"]],
    on=["team", "position", "player_id"],
    how="left",
    validate="one_to_one"
)

# Prevent negative statistical projections
for stat in ["passing_yards", "rushing_yards", "receiving_yards",
             "receptions", "targets"]:
    projections[stat] = projections[stat].clip(lower=0)

projections.to_csv(
    "nfl_upcoming_projections_2026.csv",
    index=False
)

print("\nTeams with projections:")
print(projections.groupby("team").size())

print("\nTotal projected players:", len(projections))
print("\nUpcoming projections saved successfully!")
