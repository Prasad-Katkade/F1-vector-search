#!/usr/bin/env python3

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from google import genai
from dotenv import load_dotenv
import os
import json

# --- Load environment variables ---
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# --- Gemini client ---
client = genai.Client(api_key=GEMINI_API_KEY)

# --- FastAPI setup ---
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Data models ---
class StrategyInput(BaseModel):
    overtake_data: dict
    tire_data: dict
    pit_data: dict

class StrategyResponse(BaseModel):
    strategy: str


# --- Prompt builder ---
# --- Prompt builder ---
def build_f1_prompt(req: StrategyInput) -> str:
    # Convert incoming dicts to readable JSON strings
    overtake_info = json.dumps(req.overtake_data, indent=2)
    tire_info = json.dumps(req.tire_data, indent=2)
    pit_info = json.dumps(req.pit_data, indent=2)

    # Extract key metrics for easier reading in prompt
    cliff_risk = "High ⚠️" if req.tire_data.get("risk_detected") else "Low ✅"
    undercut_success = req.pit_data.get("relevant_matches", 0)
    total_matches = req.pit_data.get("total_matches", 0)
    undercut_recommendation = (
        f"Recommended: Pit (Undercut successful in {undercut_success}/{total_matches} scenarios)"
        if undercut_success < total_matches
        else "Safe: No similar scenarios where rival is yet to pit"
    )

    # Build the final prompt
    prompt = f"""
**ROLE:** You are an elite Formula 1 Chief Race Strategist.

**CURRENT AGGREGATED RACE SITUATION:**
- Overtake probabilities per driver:
{overtake_info}

- Tire cliff risk (aggregated):
{tire_info} → Risk Level: {cliff_risk}

- Pit stop insights (Undercut/Overcut potential):
{pit_info} → {undercut_recommendation}

**TASK:**
Based on the aggregated data above, provide a concise 1–2 line strategic recommendation for the current situation considering:
- Immediate tire cliff risk
- Pit strategy (overcut/undercut)
- Optimal next move
"""
    return prompt



# --- Gemini call ---
async def call_gemini(prompt: str) -> str:
    try:
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt
        )
        return getattr(response, "text", None) or "No response from model."
    except Exception as e:
        print(f"❌ Gemini API error: {e}")
        return f"Error: {e}"


# --- Endpoint ---
@app.post("/api/strategy", response_model=StrategyResponse)
async def generate_strategy(req: StrategyInput):
    prompt = build_f1_prompt(req)
    print(prompt)
    result = await call_gemini(prompt)
    return StrategyResponse(strategy=result)


# --- Health check ---
@app.get("/health")
async def health():
    return {"ok": True}


# --- Run Server ---
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)
