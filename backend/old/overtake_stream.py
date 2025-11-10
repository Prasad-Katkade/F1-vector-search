# server_overtakes.py
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
INDEX_NAME = "f1-overtake"

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

# ---------- Drivers ----------
drivers = ["VER", "HAM", "LEC", "ALO", "SAI", "BOT", "MAG", "NOR", "GAS", "RUS",
           "OCO", "PER", "TSU", "LAT", "RIC", "ZHO", "DEV", "SAI2", "HAM2", "VAR"]

# Base vector template: TrackNormalized fixed, others will randomize
BASE_VECTORS = {driver: [0.9, 0.45, 0.35, 0.42, 0.50, 0.0] for driver in drivers}

# ---------- Helper Function ----------
async def query_pinecone(driver, vector):
    """Query Pinecone and count how often this driver appears in top matches."""
    results = index.query(
        vector=vector,
        top_k=10,
        include_metadata=True
    )
    matches = results.get("matches", [])
    count = sum(1 for m in matches if m.get("metadata", {}).get("Driver") == driver)
    return count

# ---------- WebSocket Endpoint ----------
@app.websocket("/ws/overtakes")
async def overtakes_stream(websocket: WebSocket):
    await websocket.accept()
    refresh_count = 0

    try:
        while True:
            refresh_count += 1
            driver_vectors = {}
            counts = {}

            # --- Randomize telemetry vector per driver ---
            for driver in drivers:
                base = BASE_VECTORS[driver]
                driver_vectors[driver] = [
                    base[0],  # TrackNormalized stays constant
                    min(max(base[1] + random.uniform(-0.05, 0.05), 0), 1),  # Position
                    min(max(base[2] + random.uniform(-0.05, 0.05), 0), 1),  # Compound
                    min(max(base[3] + random.uniform(-0.1, 0.1), 0), 1),    # TyreLife
                    min(max(base[4] + random.uniform(-0.1, 0.1), 0), 1),    # TrackTemp
                    min(max(base[5] + random.uniform(0, 0.1), 0), 1)        # Rainfall
                ]

            # --- Query Pinecone for each driver ---
            for driver, vec in driver_vectors.items():
                counts[driver] = await query_pinecone(driver, vec)

            # --- Add refresh count and send JSON to frontend ---
            counts["refresh_count"] = refresh_count
            await websocket.send_json(counts)

            # Wait 10 seconds before next telemetry update
            await asyncio.sleep(1)

    except Exception as e:
        print("WebSocket closed:", e)

# ---------- Run Server ----------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
