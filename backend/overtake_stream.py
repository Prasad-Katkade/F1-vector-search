import asyncio
import random
import os
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pinecone import Pinecone
from dotenv import load_dotenv
import uvicorn

load_dotenv()

# ---------- Pinecone Setup ----------
API_KEY = os.getenv("API_KEY")
INDEX_NAME = "f1-overtake"

# Initialize Pinecone client outside the function to avoid re-initializing
try:
    pc = Pinecone(api_key=API_KEY)
    index = pc.Index(INDEX_NAME)
    print(f"📡 Connected to Pinecone index: {INDEX_NAME}")
except Exception as e:
    print(f"Error connecting to Pinecone: {e}")
    # Handle error or exit if connection fails
    
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

# ---------- Configuration Constants ----------
# TrackNormalized is fixed at 0.9 to simulate a single, crucial track location (e.g., Turn 1 braking zone)
TRACK_NORMALIZED_CONSTANT = 0.9
SIM_THRESHOLD = 0.85 # Similarity score threshold for counting an overtake likelihood

# ---------- Driver State Simulation ----------
DRIVER_STATES = {}
# Vector Order: [LapNumber, Position, Compound, TyreLife, TrackTemp, Rainfall, DRS_Usage, Brake_Usage, AvgDistanceAhead, TrackNormalized]

def initialize_driver_states():
    """Set unique starting states for each driver with fixed TrackNormalized."""
    print("Initializing unique driver states...")
    compounds = [0.0, 0.5, 1.0] # Hard, Medium, Soft (example mapping)
    for i, driver in enumerate(drivers):
        position_norm = (i + 1) / len(drivers) 
        compound = random.choice(compounds)
        DRIVER_STATES[driver] = {
            "vector": [
                random.uniform(0.02, 0.2), # Start LapNumber slightly random
                position_norm,          
                compound,               
                random.uniform(0.05, 0.2), # TyreLife (Used slightly)
                random.uniform(0.4, 0.6), # TrackTemp 
                0.0,                    # Rainfall (Assume dry start)
                0.0,                    # DRS_Usage (Off)
                0.0,                    # Brake_Usage (Low)
                random.uniform(0.1, 0.4), # AvgDistanceAhead (Spread out)
                TRACK_NORMALIZED_CONSTANT # <-- FIXED VALUE
            ],
            "tyre_wear_rate": random.uniform(0.0008, 0.0012) # Unique wear rate
        }

def update_driver_states():
    """Logically update all driver states for a 'tick' of the race, keeping TrackNormalized fixed."""
    lap_increment = 0.0005 
    
    for driver, state in DRIVER_STATES.items():
        vec = state["vector"]
        
        # --- Logical progressions ---
        vec[0] = min(vec[0] + lap_increment, 1.0) # LapNumber increases
        vec[3] = min(vec[3] + state["tyre_wear_rate"], 1.0) # TyreLife increases
        
        # --- Volatile, random changes to simulate action at T=0.9 track spot ---
        vec[1] = min(max(vec[1] + random.uniform(-0.005, 0.005), 0.05), 1.0) # Position jiggle
        vec[4] = min(max(vec[4] + random.uniform(-0.002, 0.002), 0), 1.0)    # TrackTemp drift
        
        # Simulating an "overtake attempt" at T=0.9 (Braking Zone)
        distance = vec[8]
        if distance < 0.1: 
             vec[6] = random.choice([0.0, 0.9]) # DRS activation on approach
             vec[7] = random.uniform(0.7, 1.0) # HEAVY BRAKING
             vec[8] = min(max(distance + random.uniform(-0.05, 0.01), 0.01), 1.0) # Distance closes/opens
        else:
            # Normal driving/closing up
            vec[6] = 0.0 
            vec[7] = random.uniform(0.0, 0.3) 
            vec[8] = min(max(distance + random.uniform(-0.02, 0.01), 0.01), 1.0) 

        # TrackNormalized MUST remain constant
        vec[9] = TRACK_NORMALIZED_CONSTANT 


# ---------- Pinecone Query Function ----------
async def query_pinecone(driver, vector):
    """Runs the blocking Pinecone query in a non-blocking thread and returns richer data."""
    try:
        # Run the blocking I/O in a separate thread
        results = await asyncio.to_thread(
            index.query,
            vector=vector,
            top_k=10,
            include_metadata=True,
            filter={"Driver": {"$eq": driver}}
        )
        
        matches = results.get("matches", [])
        if not matches:
            return {"driver": driver, "count": 0, "max_score": 0.0, "avg_score": 0.0}

        high_scorers = [m.get("score", 0) for m in matches if m.get("score", 0) >= SIM_THRESHOLD]

        if not high_scorers:
            # Return max score even if below threshold, for debugging/visualization
            return {"driver": driver, "count": 0, "max_score": matches[0].get("score", 0), "avg_score": 0.0, "current_vector": vector}

        return {
            "driver": driver,
            "count": len(high_scorers),
            "max_score": max(high_scorers),
            "avg_score": sum(high_scorers) / len(high_scorers),
            "current_vector": vector
        }
    except Exception as e:
        print(f"Error querying for {driver}: {e}")
        return {"driver": driver, "count": -1, "max_score": 0.0, "avg_score": 0.0, "current_vector": vector}

# ---------- WebSocket Endpoint ----------
@app.websocket("/ws/overtakes")
async def overtakes_stream(websocket: WebSocket):
    await websocket.accept()
    initialize_driver_states()
    refresh_count = 0

    try:
        while True:
            refresh_count += 1
            
            # 1. Update all driver states logically
            update_driver_states()

            # 2. Create all query tasks
            tasks = []
            for driver, state in DRIVER_STATES.items():
                tasks.append(query_pinecone(driver, state["vector"]))
            
            # 3. Run all 20 queries concurrently and wait for results
            results = await asyncio.gather(*tasks)

            # 4. Format results for frontend
            payload = {res["driver"]: res for res in results}
            payload["refresh_count"] = refresh_count
            
            await websocket.send_json(payload)

            # Wait 1 second before next telemetry update
            await asyncio.sleep(1)

    except Exception as e:
        print("WebSocket closed:", e)

# ---------- Run Server ----------
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)