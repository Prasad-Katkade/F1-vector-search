import pandas as pd
from pinecone import Pinecone

from dotenv import load_dotenv
import os

load_dotenv()

# ---------- Pinecone Setup ----------
API_KEY = os.getenv("API_KEY")
INDEX_NAME = "f1-cuts"

pc = Pinecone(api_key=API_KEY)
index = pc.Index(INDEX_NAME)

# --- Config ---
NUM_TRACKS = 60  # for normalizing lap numbers

# --- Current car situation vector (normalized Rival_Pitted_Lap) ---
current_vector = [
    0.9,                 # TrackNormalized
    12 / NUM_TRACKS,      # LapNumber (normalized)
    0.45,                # Position (normalized)
    0.3,                 # NewTireCompound (normalized)
    0.2,                 # Rival_Compound
    0.35,                # Rival_TyreLife
    3.0 / 20,            # GapToRival_BeforePit
    0.5,                 # TrackTemp
    0.0                  # Rainfall
]



print(f"\n🔍 Querying index '{INDEX_NAME}' for undercut scenarios...\n")

# --- Query Pinecone ---
results = index.query(
    vector=SAFE_VECTOR,
    top_k=10,
    include_metadata=True
)

matches = results.get("matches", [])
if not matches:
    print("⚠️ No similar pit-stop scenarios found — safe to continue.")
else:
    print(f"✅ Found {len(matches)} similar entries:\n")

# --- Filter matches where rival hasn’t pitted yet (normalized) ---
relevant_matches = [
    m for m in matches
    if (m.get("metadata", {}).get("Rival_Pitted_Lap", 0) / NUM_TRACKS) > current_vector[1]
]

if relevant_matches:
    print(f"🔥 Found historical scenarios where rival hasn’t pitted yet:\n")
    for i, match in enumerate(relevant_matches, start=1):
        meta = match.get("metadata", {})
        print(f"   🔸 Match #{i}")
        print(f"      Score: {match.get('score', 'N/A')}")
        print(f"      Track: {meta.get('TrackName')}")
        print(f"      Year: {meta.get('Year')}")
        print(f"      Driver: {meta.get('Driver')}")
        print(f"      Team: {meta.get('Team')}")
        print(f"      Lap: {meta.get('LapNumber')}")
        print(f"      Rival Pitted Lap: {meta.get('Rival_Pitted_Lap')}\n")

    print(f"📊 Recommendation: Rival hasn’t pitted in {len(relevant_matches)} out of {len(matches)} similar scenarios.")
else:
    print("✅ Safe: No similar scenarios where rival is yet to pit.")
