import fastf1
import pandas as pd
import os

# ------------------------------
# Config
# ------------------------------
YEARS = [2022, 2023, 2024]
OUTPUT_CSV_TEMPLATE = "overtake_laps_{}_usa.csv"

# Normalized US tracks
TRACKS_USA = {
    "Las Vegas Grand Prix": 1.0,
    "Miami Grand Prix": 0.9,
    "United States Grand Prix": 0.8
}

# Pre-scaled compound map (for normalization)
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
def normalize_event_name(raw_name: str):
    """Normalize event names to handle sponsor names in FastF1 data."""
    raw_name = raw_name.lower()
    if "las vegas" in raw_name:
        return "Las Vegas Grand Prix"
    elif "miami" in raw_name:
        return "Miami Grand Prix"
    elif "united states" in raw_name or "austin" in raw_name:
        return "United States Grand Prix"
    else:
        return None


def get_race_session(year, race_name):
    """Load and cache the race session data."""
    fastf1.Cache.enable_cache("fastf1_cache")
    session = fastf1.get_session(year, race_name, 'R')
    session.load()
    return session


def extract_overtake_laps(year, session):
    """Extract laps where overtakes occurred, with added telemetry data."""
    laps_all = session.laps.copy()
    weather = session.weather_data.copy()
    records = []

    event_name = normalize_event_name(session.event["EventName"])
    if not event_name:
        print(f"Skipping non-US track: {session.event['EventName']}")
        return pd.DataFrame()

    track_norm = TRACKS_USA[event_name]

    for driver in laps_all["Driver"].unique():
        driver_laps = laps_all[laps_all["Driver"] == driver].sort_values("LapNumber")

        for i in range(len(driver_laps) - 1):
            lap_current = driver_laps.iloc[i]
            lap_next = driver_laps.iloc[i + 1]

            if pd.isna(lap_current.Position) or pd.isna(lap_next.Position):
                continue

            # Detect overtakes (lower position number = improved)
            if lap_next.Position < lap_current.Position:
                # Closest weather data
                closest_weather = weather.iloc[
                    (weather["Time"] - lap_current.Time).abs().argsort()[:1]
                ].iloc[0]

                # Get telemetry for lap
                try:
                    tel = lap_current.get_car_data().add_distance().add_driver_ahead()
                    drs_active = (tel["DRS"] > 0).mean()  # avg fraction of DRS usage in lap
                    brake_usage = (tel["Brake"] > 0).mean()  # % time braking
                    avg_distance_ahead = tel["DistanceToDriverAhead"].mean()
                    if pd.isna(avg_distance_ahead):
                        avg_distance_ahead = -1  # handle missing data
                except Exception as e:
                    print(f"Telemetry error for {driver} {year} {event_name}: {e}")
                    drs_active, brake_usage, avg_distance_ahead = 0, 0, -1

                record = {
                    "TrackName": event_name,
                    "TrackNormalized": track_norm,
                    "Year": year,
                    "Driver": lap_current.Driver,
                    "Team": lap_current.Team,
                    "LapNumber": lap_current.LapNumber,
                    "Position": lap_current.Position / 20,  # normalize
                    "Compound": COMPOUND_MAP.get(lap_current.Compound, 0.0),
                    "TyreLife": (lap_current.TyreLife or 0) / 60,
                    "TrackTemp": closest_weather["TrackTemp"] / 80,
                    "Rainfall": float(closest_weather["Rainfall"] > 0),
                    "DRS_Usage": drs_active,
                    "Brake_Usage": brake_usage,
                    "AvgDistanceAhead": avg_distance_ahead / 100  # normalize ~100m scale
                }

                records.append(record)

    return pd.DataFrame(records)


# ------------------------------
# Main
# ------------------------------
def main():
    for year in YEARS:
        all_race_dfs = []
        for raw_track_name in TRACKS_USA.keys():
            print(f"Processing overtakes for {raw_track_name} ({year})...")
            try:
                session = get_race_session(year, raw_track_name)
                df_overtakes = extract_overtake_laps(year, session)
                if not df_overtakes.empty:
                    all_race_dfs.append(df_overtakes)
            except Exception as e:
                print(f"Error processing {raw_track_name} {year}: {e}")

        if all_race_dfs:
            df_year = pd.concat(all_race_dfs, ignore_index=True)
            output_file = OUTPUT_CSV_TEMPLATE.format(year)
            if os.path.exists(output_file):
                os.remove(output_file)
            df_year.to_csv(output_file, index=False)
            print(f"✅ Saved {len(df_year)} overtaking laps for {year} → {output_file}")
        else:
            print(f"⚠️ No overtakes found for {year}")


if __name__ == "__main__":
    main()
