import fastf1
import pandas as pd

# ------------------------------
# Config
# ------------------------------
YEARS = [2022, 2023, 2024]
TRACKS_USA = {
    "Las Vegas Grand Prix",
    "Miami Grand Prix",
    "United States Grand Prix"
}

OUTPUT_CSV_TEMPLATE = "overtake_laps_{}_usa.csv"

# Track normalization map
TRACK_MAP = {
    "Las Vegas Grand Prix": 1.0,
    "Miami Grand Prix": 0.9,
    "United States Grand Prix": 0.8
}

# Pre-scaled compound map (no division later)
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
    """Load and cache the race session data."""
    fastf1.Cache.enable_cache("fastf1_cache")
    session = fastf1.get_session(year, race_name, 'R')
    session.load()
    return session


def extract_overtake_laps(year, session):
    """Extract laps where an overtake occurred on the following lap."""
    laps_all = session.laps.copy()
    weather = session.weather_data.copy()
    total_laps = laps_all['LapNumber'].max()
    records = []

    track_norm = TRACK_MAP.get(session.event['EventName'], 0.5)

    for driver in laps_all['Driver'].unique():
        driver_laps = laps_all[laps_all['Driver'] == driver].sort_values('LapNumber')

        # Detect overtakes
        for i in range(len(driver_laps) - 1):
            lap_current = driver_laps.iloc[i]
            lap_next = driver_laps.iloc[i + 1]

            if pd.isna(lap_current.Position) or pd.isna(lap_next.Position):
                continue

            # Overtake = improved position (lower number)
            if lap_next.Position < lap_current.Position:
                # Closest weather snapshot
                closest_weather = weather.iloc[(weather['Time'] - lap_current.Time).abs().argsort()[:1]].iloc[0]

                record = {
                    "TrackName": session.event['EventName'],
                    "TrackNormalized": track_norm,
                    "Year": year,
                    "Driver": lap_current.Driver,
                    "Team": lap_current.Team,
                    "LapNumber": lap_current.LapNumber,
                    "Position": lap_current.Position / 20,  # normalize by 20 cars
                    "Compound": COMPOUND_MAP.get(lap_current.Compound, 0.0),
                    "TyreLife": (lap_current.TyreLife or 0) / 60,
                    "TrackTemp": closest_weather['TrackTemp'] / 80,  # fixed scaling
                    "Rainfall": float(closest_weather['Rainfall'] > 0)
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
            print(f"Processing overtakes for {track_name} ({year})...")
            try:
                session = get_race_session(year, track_name)
                df_overtakes = extract_overtake_laps(year, session)
                if not df_overtakes.empty:
                    all_race_dfs.append(df_overtakes)
            except Exception as e:
                print(f"Error processing {track_name} {year}: {e}")

        if all_race_dfs:
            df_year = pd.concat(all_race_dfs, ignore_index=True)
            output_file = OUTPUT_CSV_TEMPLATE.format(year)
            df_year.to_csv(output_file, index=False)
            print(f"✅ Saved {len(df_year)} overtaking laps for {year} → {output_file}")
        else:
            print(f"⚠️ No overtakes found for {year}")

if __name__ == "__main__":
    main()
