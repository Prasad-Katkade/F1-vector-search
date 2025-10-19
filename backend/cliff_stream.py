# server_cliff.py
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
INDEX_NAME = "f1-cliff"

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
drivers = ["MY_CAR"]  # can expand to other cars if needed

# Base vector template: TrackNormalized fixed, others will randomize
BASE_VECTORS = {
    "MY_CAR": [
        0.88,  # TrackNormalized (constant)
        0.45,  # Compound
        0.70,  # TyreLife
        0.78,  # TrackTemp
        0.10,  # Rainfall
        0.80,  # LapNumber
        0.35   # Position
    ]
}

# ---------- Helper Function ----------
async def query_pinecone(driver, vector):
    """Query Pinecone and get matches for tire cliff risk."""
    results = index.query(
        vector=vector,
        top_k=30,
        include_metadata=True
    )
    matches = results.get("matches", [])
    max_score = max(m.get("score", 0) for m in matches) if matches else 0
    return len(matches), round(max_score, 3), max_score > 0.85

# ---------- WebSocket Endpoint ----------
@app.websocket("/ws/cliff")
async def cliff_stream(websocket: WebSocket):
    await websocket.accept()
    refresh_count = 0

    try:
        while True:
            refresh_count += 1
            driver_vectors = {}
            response = {}

            # --- Randomize telemetry vector ---
            for driver in drivers:
                base = BASE_VECTORS[driver]
                driver_vectors[driver] = [
                    base[0],  # TrackNormalized stays constant
                    min(max(base[1] + random.uniform(-0.05, 0.05), 0), 1),  # Compound
                    min(max(base[2] + random.uniform(-0.1, 0.1), 0), 1),    # TyreLife
                    min(max(base[3] + random.uniform(-0.1, 0.1), 0), 1),    # TrackTemp
                    min(max(base[4] + random.uniform(0, 0.05), 0), 1),      # Rainfall
                    min(max(base[5] + random.uniform(-0.05, 0.05), 0), 1),  # LapNumber
                    min(max(base[6] + random.uniform(-0.05, 0.05), 0), 1)   # Position
                ]

            # --- Query Pinecone ---
            for driver, vec in driver_vectors.items():
                matches_count, max_score, risk_detected = await query_pinecone(driver, vec)
                response[driver] = {
                    "matches_found": matches_count,
                    "max_similarity": max_score,
                    "risk_detected": risk_detected,
                    "simulated_vector": vec
                }

            # --- Add refresh count and send JSON ---
            response["refresh_count"] = refresh_count
            await websocket.send_json(response)

            # Wait 10 seconds before next telemetry update
            await asyncio.sleep(1)

    except Exception as e:
        print("WebSocket closed:", e)

# ---------- Run Server ----------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
