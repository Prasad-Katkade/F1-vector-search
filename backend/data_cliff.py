import fastf1
import pandas as pd
import numpy as np

# ------------------------------
# Config
# ------------------------------
YEARS = [2022, 2023, 2024]
TRACKS_USA = [
    "Las Vegas Grand Prix",
    "Miami Grand Prix",
    "United States Grand Prix"
]

OUTPUT_CSV_TEMPLATE = "tire_cliff_laps_{}_usa.csv"

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

def extract_tire_cliff_laps(year, session, drop_threshold_sec=2.0):
    laps_all = session.laps.copy()
    weather = session.weather_data.copy()
    records = []

    track_norm = TRACK_MAP.get(session.event['EventName'], 0.5)
    max_lap = laps_all['LapNumber'].max()

    for driver in laps_all['Driver'].unique():
        driver_laps = laps_all[laps_all['Driver'] == driver].sort_values('LapNumber')

        # Convert LapTime to seconds, skip NaNs
        lap_times = driver_laps['LapTime'].dt.total_seconds().fillna(np.nan).values
        for i in range(3, len(driver_laps)):
            if np.isnan(lap_times[i-3:i]).any():
                continue
            avg_prev3 = np.mean(lap_times[i-3:i])
            curr_lap = driver_laps.iloc[i]
            curr_lap_time = lap_times[i]
            drop_sec = curr_lap_time - avg_prev3

            # Check for tire cliff
            if drop_sec >= drop_threshold_sec:
                closest_weather = weather.iloc[(weather['Time'] - curr_lap.Time).abs().argsort()[:1]].iloc[0]

                record = {
                    "TrackName": session.event['EventName'],
                    "TrackNormalized": track_norm,
                    "Year": year,
                    "Driver": curr_lap.Driver,
                    "Team": curr_lap.Team,
                    "LapNumber": curr_lap.LapNumber / max_lap,  # normalized 0-1
                    "Position": curr_lap.Position / 20 if pd.notna(curr_lap.Position) else 0,  # normalized
                    "Compound": COMPOUND_MAP.get(curr_lap.Compound, 0.0),
                    "TyreLife": (curr_lap.TyreLife or 0) / 60,
                    "TrackTemp": closest_weather['TrackTemp'] / 80,
                    "Rainfall": float(closest_weather['Rainfall'] > 0),
                    "LapTimeLoss": round(drop_sec, 3)
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
            print(f"Processing tire cliff data for {track_name} ({year})...")
            try:
                session = get_race_session(year, track_name)
                df_cliffs = extract_tire_cliff_laps(year, session)
                if not df_cliffs.empty:
                    all_race_dfs.append(df_cliffs)
            except Exception as e:
                print(f"Error processing {track_name} {year}: {e}")

        if all_race_dfs:
            df_year = pd.concat(all_race_dfs, ignore_index=True)
            output_file = OUTPUT_CSV_TEMPLATE.format(year)
            df_year.to_csv(output_file, index=False)
            print(f"✅ Saved {len(df_year)} tire cliff laps for {year} → {output_file}")
        else:
            print(f"⚠️ No tire cliffs found for {year}")

if __name__ == "__main__":
    main()
