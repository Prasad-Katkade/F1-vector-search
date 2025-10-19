
# server_cuts.py
import asyncio
import random
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pinecone import Pinecone
from dotenv import load_dotenv
import os

load_dotenv()

# ---------- Pinecone Setup ----------
API_KEY = os.getenv("API_KEY")
INDEX_NAME = "f1-cuts"
NUM_TRACKS = 60  # for normalizing lap numbers

pc = Pinecone(api_key=API_KEY)
index = pc.Index(INDEX_NAME)

# ---------- FastAPI Setup ----------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------- Car / Drivers ----------
drivers = ["MY_CAR"]  # can expand to other cars

# Base vector template: TrackNormalized fixed, others will randomize
BASE_VECTORS = {
    "MY_CAR": [
        0.9,       # TrackNormalized
        12 / NUM_TRACKS,  # LapNumber normalized
        0.45,      # Position
        0.3,       # NewTireCompound
        0.2,       # Rival_Compound
        0.35,      # Rival_TyreLife
        3.0 / 20,  # GapToRival_BeforePit
        0.5,       # TrackTemp
        0.0        # Rainfall
    ]
}

# ---------- Helper Function ----------
async def query_pinecone(driver, vector):
    """Query Pinecone and get relevant undercut matches."""
    results = index.query(
        vector=vector,
        top_k=10,
        include_metadata=True
    )
    matches = results.get("matches", [])

    # Filter matches where rival hasn’t pitted yet (normalized)
    relevant_matches = [
        m for m in matches
        if (m.get("metadata", {}).get("Rival_Pitted_Lap", 0) / NUM_TRACKS) > vector[1]
    ]

    return len(matches), len(relevant_matches), matches

# ---------- WebSocket Endpoint ----------
@app.websocket("/ws/undercuts")
async def undercut_stream(websocket: WebSocket):
    await websocket.accept()
    refresh_count = 0

    try:
        while True:
            refresh_count += 1
            driver_vectors = {}
            response = {}

            # --- Randomize telemetry vector per driver ---
            for driver in drivers:
                base = BASE_VECTORS[driver]
                driver_vectors[driver] = [
                    base[0],  # TrackNormalized constant
                    min(max(base[1] + random.uniform(-0.05, 0.05), 0), 1),  # LapNumber
                    min(max(base[2] + random.uniform(-0.1, 0.1), 0), 1),    # Position
                    min(max(base[3] + random.uniform(-0.05, 0.05), 0), 1),  # NewTireCompound
                    min(max(base[4] + random.uniform(-0.05, 0.05), 0), 1),  # Rival_Compound
                    min(max(base[5] + random.uniform(-0.1, 0.1), 0), 1),    # Rival_TyreLife
                    min(max(base[6] + random.uniform(-0.1, 0.1), 0), 1),    # GapToRival_BeforePit
                    min(max(base[7] + random.uniform(-0.05, 0.05), 0), 1),  # TrackTemp
                    min(max(base[8] + random.uniform(0, 0.05), 0), 1)       # Rainfall
                ]

            # --- Query Pinecone and build response ---
            for driver, vec in driver_vectors.items():
                total_matches, relevant_matches_count, matches_list = await query_pinecone(driver, vec)
                response[driver] = {
                    "total_matches": total_matches,
                    "relevant_matches": relevant_matches_count,
                    "simulated_vector": vec
                }

            # --- Add refresh count and send JSON ---
            response["refresh_count"] = refresh_count
            await websocket.send_json(response)

            # Wait 5 seconds before next telemetry update
            await asyncio.sleep(1)

    except Exception as e:
        print("WebSocket closed:", e)

# ---------- Run Server ----------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
