
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="NFL Matchup Analytics",
    layout="wide"
)

st.title("NFL Matchup Analytics")
st.caption("2026 NFL Player Matchup Dashboard")

@st.cache_data
def load_data():
    return pd.read_csv(
        "nfl_upcoming_projections_2026.csv"
    )

data = load_data()

# Load tight end defensive matchup ratings
@st.cache_data
def load_te_matchups():
    return pd.read_csv("te_defensive_matchups_2026.csv")

te_matchups = load_te_matchups()

print("\nProjection weeks and teams:")
print(data.groupby("week")["team"].unique())

# Load the full NFL schedule
schedule = pd.read_csv("nfl_schedule_2026.csv")

# Keep only regular-season games
schedule = schedule[schedule["game_type"] == "REG"].copy()

# Check available games
print("\nSchedule loaded:")
print(schedule[["week", "away_team", "home_team"]].head())


print("\nTeams in Week 6:")
print(
    data.loc[data["week"] == 6, "team"]
    .value_counts()
)

print("\nTeams available by week:")
print(
    data.groupby("week")["team"]
    .nunique()
)
# Load player names
player_info = pd.read_csv("nfl_player_stats_2026.csv")

print("Player information columns:")
print(player_info.columns.tolist())

print("\nProjection columns:")
print(data.columns.tolist())

# Use the actual team column in our dataset
team_col = "recent_team" if "recent_team" in data.columns else "team"

# Available weeks and teams
week_col = "week" if "week" in data.columns else "week_y" if "week_y" in data.columns else "week"

if week_col not in data.columns:
    st.error("No week column found in the dataset.")
    st.stop()


# Get all weeks from the NFL schedule
weeks = sorted(schedule["week"].dropna().unique())

st.sidebar.header("Matchup Filters")

week = st.sidebar.selectbox(
    "Select Week",
    weeks,
    index=len(weeks) - 1
)

# Get every scheduled game for the selected week
week_games = schedule[schedule["week"] == week].copy()

week_games["matchup"] = (
    week_games["away_team"] + " vs " + week_games["home_team"]
)

matchup = st.sidebar.selectbox(
    "Select Matchup",
    week_games["matchup"].tolist()
)

selected_game = week_games[
    week_games["matchup"] == matchup
].iloc[0]

away_team = selected_game["away_team"]
home_team = selected_game["home_team"]

st.subheader(f"{away_team} vs {home_team} — Week {week}")

# Find projections for either team
filtered = data[
    (data[week_col] == week) &
    (
        ((data[team_col] == away_team) &
         (data["opponent_team"] == home_team)) |
        ((data[team_col] == home_team) &
         (data["opponent_team"] == away_team))
    )
].copy()

if filtered.empty:
    st.info("No player projections available for this matchup yet.")
    st.stop()

opponent = home_team



# Position filter
positions = ["QB", "RB", "WR", "TE"]

position = st.selectbox(
    "Select Position",
    ["All"] + positions
)

if position != "All":
    filtered = filtered[
        filtered["position"] == position
    ]

# Projection columns
projection_cols = [
    col for col in [
        "passing_yards",
        "rushing_yards",
        "receiving_yards",
        "receptions",
        "targets"
    ]
    if col in filtered.columns
]


st.write("Projection columns found:", projection_cols)
st.write("All available columns:", filtered.columns.tolist())

display_cols = [
    col for col in [
        "player_id",
        "position",
        "likely_starting_qb",
        "recent_usage",
        "usage_rank",
        "pregame_snap_avg",
        "pregame_snap_last3",
        "snap_trend_change"
    ] if col in filtered.columns
]

display_cols += projection_cols


# Put player names first in the table
display_cols = ["player_display_name"] + display_cols

# Show the top 5 players based on projected production
ranking_stat = {
    "QB": "passing_yards",
    "RB": "rushing_yards",
    "WR": "receiving_yards",
    "TE": "receiving_yards"
}

if position in ranking_stat:
    stat = ranking_stat[position]

    if stat in filtered.columns:
        top_players = filtered.sort_values(
            by=stat,
            ascending=False
        ).head(5)

        st.subheader(f"Top 5 {position} Projections")

        st.dataframe(
            top_players[["player_display_name", stat]].round(2),
            hide_index=True,
            width="stretch"
        )
# Display tight end defensive matchup ratings
if position == "TE":
    st.subheader("TE Defensive Matchup Ratings")

    matchup_info = filtered.drop(
    columns=["matchup_score", "matchup_rating", "defense"],
    errors="ignore"
).merge(
    te_matchups[
        ["defense", "matchup_score", "matchup_rating"]
    ],
    left_on="opponent_team",
    right_on="defense",
    how="left",
    validate="many_to_one"
)

    st.dataframe(
        matchup_info[
            ["player_display_name", "opponent_team",
             "matchup_score", "matchup_rating"]
        ].round(2),
        hide_index=True,
        use_container_width=True
    )

st.subheader("Player Projections")



st.dataframe(
    filtered[display_cols].round(2),
    use_container_width=True,
    hide_index=True
)

st.caption(
    "Projections are experimental and based on "
    "historical player statistics."
)


# WR and TE Backtest Results
st.header("WR & TE Matchup Backtest")

st.write(
    "Compare normal player projections against "
    "defense-adjusted projections. Lower MAE means "
    "better accuracy."
)

try:
    backtest = pd.read_csv("matchup_backtest_results_2026.csv")

    # Select which position to examine
    selected_position = st.selectbox(
        "Choose Position",
        ["WR", "TE"],
        key="backtest_position"
    )

    # Filter results
    filtered_backtest = backtest[
        backtest["position"] == selected_position
    ]

    # Display comparison table
    st.subheader(f"{selected_position} Prediction Accuracy")

    st.dataframe(
        filtered_backtest,
        use_container_width=True,
        hide_index=True
    )

    # Compare errors visually
    selected_stat = st.selectbox(
        "Choose Statistic",
        ["receiving_yards", "receptions", "targets"],
        key="backtest_stat"
    )

    chart_data = filtered_backtest[
        filtered_backtest["stat"] == selected_stat
    ].copy()

    chart_data = chart_data.set_index("week")

    st.subheader("Normal vs Defense-Adjusted Projections")

    st.line_chart(
        chart_data[["baseline_mae", "matchup_mae"]]
    )

except FileNotFoundError:
    st.warning(
        "Backtest results not found. "
        "Run python backtest_matchups.py first."
    )
