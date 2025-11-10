import pandas as pd
from pinecone import Pinecone

from dotenv import load_dotenv
import os

load_dotenv()

# ---------- Pinecone Setup ----------
API_KEY = os.getenv("API_KEY")
INDEX_NAME = "f1-cliff"

pc = Pinecone(api_key=API_KEY)
index = pc.Index(INDEX_NAME)

# --- Current car telemetry vector (potential cliff) ---
current_vector = [
    0.88,  # TrackNormalized
    0.45,  # Compound (Soft)
    0.70,  # TyreLife (old tires)
    0.78,  # TrackTemp (hot)
    0.10,  # Rainfall (dry)
    0.80,  # LapNumber (late stint)
    0.35   # Position (midfield)
]


# --- Function to run query and classify ---
def check_tire_cliff(vector, label):
    print(f"\n🔍 Checking tire cliff risk for: {label}\n")

    results = index.query(
        vector=vector,
        top_k=30,
        include_metadata=True
    )

    matches = results.get("matches", [])
    if not matches:
        print("⚠️ No similar race conditions found — possibly safe.")
        return

    # Determine the highest similarity score
    max_score = max(m.get("score", 0) for m in matches)
    print(f"📈 Max similarity score: {max_score:.3f}")

    # Decide if it's risky
    if max_score > 0.85:
        print("🚨 Tire cliff risk detected! Similar conditions found.\n")
        for i, match in enumerate(matches[:5], start=1):
            meta = match.get("metadata", {})
            print(f"   🔸 Match #{i}")
            print(f"      Score: {match.get('score', 'N/A')}")
            print(f"      Track: {meta.get('TrackName')}")
            print(f"      Year: {meta.get('Year')}")
            print(f"      Driver: {meta.get('Driver')}")
            print(f"      Lap: {meta.get('LapNumber')}")
            print(f"      Team: {meta.get('Team')}\n")
    else:
        print("✅ Safe: No strong similarity to known tire cliff events.\n")

# --- Run both tests ---
check_tire_cliff(current_vector, "Current Conditions")
