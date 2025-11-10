import os
from pinecone import Pinecone
from dotenv import load_dotenv

# ----------------------------------------
# Setup
# ----------------------------------------
load_dotenv()
API_KEY = os.getenv("API_KEY")
INDEX_NAME = "f1-overtake"

# ----------------------------------------
# Connect to Pinecone
# ----------------------------------------
pc = Pinecone(api_key=API_KEY)
index = pc.Index(INDEX_NAME)
print(f"📡 Connected to Pinecone index: {INDEX_NAME}")

# ----------------------------------------
# Example live telemetry vector (normalized)

# query_vector = [
# 0.25, # LapNumber
# 0.1, # Position
# 0.2, # Compound
# 0.05, # TyreLife
# 0.45, # TrackTemp
# 0.0, # Rainfall
# 0.6, # DRS_Usage
# 0.3, # Brake_Usage
# 0.02, # AvgDistanceAhead
# 0.8 # TrackNormalized
# ]
query_vector = [
    0.45,  # LapNumber (Mid-race)
    0.4,   # Position (e.g., P8)
    0.75,  # Compound (Inters)
    0.3,   # TyreLife (Used Inters)
    0.15,  # TrackTemp (Very cold)
    0.7,   # Rainfall (Raining)
    0.0,   # DRS_Usage (DRS disabled)
    0.8,   # Brake_Usage (Heavy braking)
    0.05,  # AvgDistanceAhead (Very close)
    0.8    # TrackNormalized (FIXED to 0.8)
]

# ----------------------------------------
# Metadata filter for driver VER
metadata_filter = {"Driver": {"$eq": "VER"}}

# ----------------------------------------
# Query Pinecone
TOP_K = 50
results = index.query(
    vector=query_vector,
    top_k=TOP_K,
    include_metadata=True,
    filter=metadata_filter
)

# ----------------------------------------
# Print results
print(f"\nTop {TOP_K} similar past overtakes for VER:\n")
for match in results["matches"]:
    score = match["score"]
    meta = match["metadata"]
    print(f"Score: {score:.4f} | Driver: {meta['Driver']} | Team: {meta['Team']} | Track: {meta['TrackName']} | Year: {meta['Year']}")
