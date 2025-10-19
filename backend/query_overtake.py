import pandas as pd
from pinecone import Pinecone
from dotenv import load_dotenv
import os

load_dotenv()

# ---------- Pinecone Setup ----------
API_KEY = os.getenv("API_KEY")
INDEX_NAME = "f1-overtake"

pc = Pinecone(api_key=API_KEY)
index = pc.Index(INDEX_NAME)

# --- Rival telemetry vector (Hamilton) ---
rival_name = "HAM"
rival_vector = [
    0.9,   # TrackNormalized
    0.45,  # Position (midfield)
    0.35,  # Compound
    0.42,  # TyreLife
    0.50,  # TrackTemp
    0.00   # Rainfall
]

print(f"\n🔍 Querying index '{INDEX_NAME}' for conditions similar to {rival_name}...\n")

# --- Query Pinecone ---
results = index.query(
    vector=rival_vector,
    top_k=50,
    include_metadata=True
)

matches = results.get("matches", [])
if not matches:
    print("⚠️ No similar race conditions found.")
else:
    print(f"✅ Found {len(matches)} similar entries:\n")

# --- Print all results with metadata and vector ---
for i, match in enumerate(matches, start=1):
    meta = match.get("metadata", {})
    print(f"🔸 Match #{i}")
    print(f"   Score: {match.get('score', 'N/A')}")
    print(f"   Metadata: {meta}")
    print(f"   Vector: {rival_vector}\n")

# --- Filter: only print if rival ('HAM') appears in metadata ---
rival_matches = [m for m in matches if m.get("metadata", {}).get("Driver") == rival_name]

if rival_matches:
    print(f"🔥 Found entries where rival '{rival_name}' appears:\n")
    for rm in rival_matches:
        print(f"Driver: {rm['metadata'].get('Driver')}")
        print(f"Track: {rm['metadata'].get('TrackName')}")
        print(f"Year: {rm['metadata'].get('Year')}")
        print(f"Lap: {rm['metadata'].get('LapNumber')}")
        print(f"Team: {rm['metadata'].get('Team')}")
        print(f"Score: {rm.get('score', 'N/A')}\n")
else:
    print(f"⚙️ No direct overtakes found involving '{rival_name}'.")
