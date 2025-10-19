import fastf1
import pandas as pd
import numpy as np

# ------------------------------
# Config
# ------------------------------
YEARS = [2020, 2021, 2022, 2023, 2024]  # last 5 years
TRACKS_USA = [
    "Las Vegas Grand Prix",
    "Miami Grand Prix",
    "United States Grand Prix"
]

OUTPUT_CSV_TEMPLATE = "undercut_laps_{}_williams.csv"

TRACK_MAP = {
    "Las Vegas Grand Prix": 1.0,
    "Miami Grand Prix": 0.9,
    "United States Grand Prix": 0.8
}

COMPOUND_MAP = {
    'SOFT': 0.1,
    'MEDIUM': 0.2,
    'HARD': 0.3,
    'INTERMEDIATE': 0.4,
    'WET': 0.5,
    'TEST_UNKNOWN': 0.0,
    'UNKNOWN': 0.0
}

# ------------------------------
# Helper functions
# ------------------------------
def get_race_session(year, race_name):
    fastf1.Cache.enable_cache("fastf1_cache")
    session = fastf1.get_session(year, race_name, 'R')
    session.load()
    return session

def extract_undercut_laps(year, session):
    laps_all = session.laps.copy()
    weather = session.weather_data.copy()
    records = []

    track_norm = TRACK_MAP.get(session.event['EventName'], 0.5)
    max_lap = laps_all['LapNumber'].max()

    # Filter team Williams
    team_laps = laps_all[laps_all['Team'] == "Williams"]

    for driver in team_laps['Driver'].unique():
        driver_laps = team_laps[team_laps['Driver'] == driver].sort_values('LapNumber')

        for i in range(1, len(driver_laps)):
            prev_lap = driver_laps.iloc[i-1]
            curr_lap = driver_laps.iloc[i]

            # Pit detected: StintNumber changed
            if curr_lap.Stint != prev_lap.Stint:
                # Find rival in front (closest position)
                rivals = laps_all[(laps_all['LapNumber'] == curr_lap.LapNumber) &
                                  (laps_all['Position'] < curr_lap.Position)]
                if rivals.empty:
                    continue
                rival = rivals.sort_values('Position').iloc[-1]  # closest rival ahead

                closest_weather = weather.iloc[(weather['Time'] - curr_lap.Time).abs().argsort()[:1]].iloc[0]

                record = {
                    "TrackName": session.event['EventName'],
                    "TrackNormalized": track_norm,
                    "Year": year,
                    "Driver": curr_lap.Driver,
                    "Team": curr_lap.Team,
                    "LapNumber": curr_lap.LapNumber / max_lap,  # normalized
                    "Position": curr_lap.Position / 20 if pd.notna(curr_lap.Position) else 0,
                    "NewTireCompound": COMPOUND_MAP.get(curr_lap.Compound, 0.0),
                    "Rival_Compound": COMPOUND_MAP.get(rival.Compound, 0.0),
                    "Rival_TyreLife": (rival.TyreLife or 0) / 60,
                    "GapToRival_BeforePit": (rival.Time - curr_lap.Time).total_seconds() / 20,  # normalize by 20s
                    "TrackTemp": closest_weather['TrackTemp'] / 80,
                    "Rainfall": float(closest_weather['Rainfall'] > 0),
                    "Rival_Pitted_Lap": rival.LapNumber
                }
                records.append(record)

    return pd.DataFrame(records)

# ------------------------------
# Main
# ------------------------------
def main():
    for year in YEARS:
        all_race_dfs = []
        for track_name in TRACKS_USA:
            print(f"Processing undercut data for {track_name} ({year})...")
            try:
                session = get_race_session(year, track_name)
                df_undercut = extract_undercut_laps(year, session)
                if not df_undercut.empty:
                    all_race_dfs.append(df_undercut)
            except Exception as e:
                print(f"Error processing {track_name} {year}: {e}")

        if all_race_dfs:
            df_year = pd.concat(all_race_dfs, ignore_index=True)
            output_file = OUTPUT_CSV_TEMPLATE.format(year)
            df_year.to_csv(output_file, index=False)
            print(f"✅ Saved {len(df_year)} undercut laps for {year} → {output_file}")
        else:
            print(f"⚠️ No undercut laps found for {year}")

if __name__ == "__main__":
    main()
