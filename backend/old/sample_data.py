import fastf1
import pandas as pd
from fastf1.api import timing_data

# ------------------------------
# Configurable parameters
# ------------------------------
YEAR = 2024
TRACK_NAME = "United States Grand Prix"  # Full race name as in FastF1
OUTPUT_CSV = f"data{YEAR}_normalized.csv"

COMPOUND_MAP = {
    'SOFT': 1,
    'MEDIUM': 2,
    'HARD': 3,
    'INTERMEDIATE': 4,
    'WET': 5,
    'TEST_UNKNOWN': 0,
    'UNKNOWN': 0
}

# ------------------------------
# Helper functions
# ------------------------------
def get_race_session(year, race_name):
    fastf1.Cache.enable_cache("fastf1_cache")
    session = fastf1.get_session(year, race_name, 'R')  # 'R' = Race
    session.load()
    return session

def normalize_series(series):
    if series.max() == series.min():
        return series.apply(lambda x: 0.5)
    return (series - series.min()) / (series.max() - series.min())

def extract_lap_weather_data(session):
    laps_all = session.laps.copy()
    weather = session.weather_data.copy()
    
    # Fetch timing stream for GapToLeader
    _, stream_data = timing_data(session.api_path)
    
    # Map driver abbreviation -> permanent number
    driver_map = {}
    for driver_abbr in session.drivers:
        driver_obj = session.get_driver(driver_abbr)
        driver_map[driver_obj.Abbreviation] = driver_obj.DriverNumber


    
    # Precompute normalization factors
    fastest_lap_time = laps_all['LapTime'].dropna().min().total_seconds()
    total_laps = laps_all['LapNumber'].max()
    total_cars = len(laps_all['Driver'].unique())

    records = []

    for _, lap in laps_all.iterrows():
        if lap.Deleted or pd.isna(lap.LapTime):
            continue  # skip invalid laps

        # Closest weather
        closest_weather = weather.iloc[(weather['Time'] - lap.Time).abs().argsort()[:1]].iloc[0]

        # Map driver abbreviation to number
        driver_number = driver_map.get(lap.Driver, None)
        if driver_number is None:
            print("driver_number is None")
            gap_leader_sec = 0
        else:
            gap_driver_data = stream_data[stream_data['Driver'] == driver_number]
            if not gap_driver_data.empty:
                closest_gap = gap_driver_data.iloc[(gap_driver_data['Time'] - lap.Time).abs().argsort()[:1]]
                if not closest_gap.empty:
                    gap_val = closest_gap['GapToLeader'].iloc[0]
                    # Convert timedelta to seconds
                    if isinstance(gap_val, pd.Timedelta):
                        gap_leader_sec = gap_val.total_seconds()
                    else:
                        try:
                            gap_leader_sec = float(str(gap_val).replace('+',''))
                        except:
                            gap_leader_sec = 0
                else:
                    print("closest_gap.empty:")
                    gap_leader_sec = 0
            else:
                print("gap_driver_data.empty:")
                gap_leader_sec = 0

        # Lap times in seconds
        lap_time_sec = lap.LapTime.total_seconds()
        sector1_sec = lap.Sector1Time.total_seconds() if pd.notna(lap.Sector1Time) else 0
        sector2_sec = lap.Sector2Time.total_seconds() if pd.notna(lap.Sector2Time) else 0
        sector3_sec = lap.Sector3Time.total_seconds() if pd.notna(lap.Sector3Time) else 0

        record = {
            "TrackName": session.event['EventName'],
            "Year": YEAR,
            "Driver": lap.Driver,
            "Team": lap.Team,
            "LapNumber": lap.LapNumber / total_laps,
            "Position": lap.Position / total_cars if pd.notna(lap.Position) else 0,
            "StintNumber": lap.Stint / 10,
            "Compound": COMPOUND_MAP.get(lap.Compound, 0) / 5,
            "TyreLife": lap.TyreLife / 60,
            "FreshTyre": float(lap.FreshTyre),
            "LapTime": lap_time_sec / fastest_lap_time,
            "Sector1Time": sector1_sec / fastest_lap_time,
            "Sector2Time": sector2_sec / fastest_lap_time,
            "Sector3Time": sector3_sec / fastest_lap_time,
            "SpeedI1": lap.SpeedI1 / 360,
            "SpeedI2": lap.SpeedI2 / 360,
            "SpeedFL": lap.SpeedFL / 360,
            "GapToLeader": gap_leader_sec / fastest_lap_time,
            "AirTemp": closest_weather['AirTemp'] / 50,
            "TrackTemp": closest_weather['TrackTemp'] / 80,
            "Humidity": closest_weather['Humidity'] / 100,
            "WindSpeed": closest_weather['WindSpeed'] / 150,
            "WindDirection": closest_weather['WindDirection'] / 360,
            "Rainfall": float(closest_weather['Rainfall'] > 0)
        }

        records.append(record)

    return pd.DataFrame(records)

# ------------------------------
# Main
# ------------------------------
def main(year, track_name, output_file):
    session = get_race_session(year, track_name)
    df = extract_lap_weather_data(session)
    df.to_csv(output_file, index=False)
    print(f"Normalized data saved to {output_file}, shape: {df.shape}")

if __name__ == "__main__":
    main(YEAR, TRACK_NAME, OUTPUT_CSV)


# feature_cols_overtake = [
#     'Driver',        # Driver making the overtake
#     'Year',          # Season
#     'LapNumber',     # Lap when overtake happens
#     'Position',      # Position at lap start or end
#     'Compound',      # Tire compound (Soft/Medium/Hard)
#     'TyreLife',      # Normalized tire life (0-1)
#     'GapToCarAhead', # Gap to car in front optional
#     'TrackTemp',     # Track temperature (°C)
#     'Rainfall',      # Rain or dry (0/1)
#     'TrackName'      # Track name (filter for USA Grand Prix)
# ]
