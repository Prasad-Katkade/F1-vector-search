# 🏎️ F1 Vector Search

### ⏱️ Description
**F1 Vector Search** is a project inspired by the concept of a **"time machine"** — enabling you to find **similar scenarios from past Formula 1 races** within seconds using **live telemetry data**.  
By combining FastF1 race telemetry, vector embeddings, and Pinecone similarity search, this system helps identify comparable overtaking conditions across seasons and drivers.

---

## 📁 Project Structure

| File | Description |
|------|--------------|
| **`overtake_data.py`** | Fetches and processes past F1 race data (from the last 3 years) for all U.S. tracks using the FastF1 library. Extracts overtakes, tyre data, track conditions, and telemetry signals (DRS, braking, etc.). |
| **`overtake_upload.py`** | Normalizes and uploads the extracted race data as vectors to a Pinecone index. Each vector represents an overtaking event enriched with metadata (driver, team, lap number, etc.). |
| **`overtake_query.py`** | Demonstrates how to query the Pinecone index using a sample telemetry vector to find similar historical racing conditions. Useful for testing search relevance and tuning embeddings. |
| **`server_overtakes.py`** | FastAPI WebSocket server that streams **live telemetry data** for all drivers, queries Pinecone in real-time, and compares current race conditions against historical overtakes. Designed for live visualization dashboards or analytics tools. |

---

## ⚙️ Features
- 🚀 Real-time telemetry stream processing  
- 🔍 Semantic vector search across historical races  
- 🧠 LLM-ready insights layer (for contextual reasoning or commentary)  
- 🏁 Multi-driver comparison with DRS, brake, tyre, and weather data  
- 🌎 Scalable via Pinecone Serverless Vector Index  

---

## 🧰 Tech Stack
- **Python 3.10+**
- **FastAPI** – for WebSocket streaming and APIs  
- **FastF1** – to access FIA telemetry and session data  
- **Pandas / Scikit-learn** – for preprocessing and normalization  
- **Pinecone** – for vector similarity search  
- **TQDM** – for progress tracking  

---

## 🚀 Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/f1-vector-search.git
   cd f1-vector-search
