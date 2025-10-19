#!/usr/bin/env python3

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx

GEMINI_API_KEY = "AIzaSyDSk-nr2zAkK2rhirHBA6UZnZs5oA9k1hc"
GEMINI_MODEL = "gemini-pro"
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalysisRequest(BaseModel):
    type: str
    prompt: str

class AnalysisResponse(BaseModel):
    text: str

async def call_gemini(prompt: str) -> str:
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(GEMINI_URL, json=payload)
        data = r.json()
    return (
        data.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [{}])[0]
        .get("text", "Analysis pending...")
    )

@app.get("/health")
async def health():
    return {"ok": True}

@app.post("/api/gemini/analyze", response_model=AnalysisResponse)
async def analyze(req: AnalysisRequest):
    text = await call_gemini(req.prompt)
    return AnalysisResponse(text=text)

@app.post("/api/gemini/batch", response_model=list[AnalysisResponse])
async def analyze_batch(reqs: list[AnalysisRequest]):
    results = []
    for r in reqs:
        txt = await call_gemini(r.prompt)
        results.append(AnalysisResponse(text=txt))
    return results

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)
