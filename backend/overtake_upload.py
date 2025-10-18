import os
import pandas as pd
from tqdm import tqdm
from sklearn.preprocessing import MinMaxScaler
from pinecone import Pinecone, ServerlessSpec
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    # dotenv is optional; env vars can be set in the environment
    pass

# ---------- CONFIG ----------
# Read Pinecone API key from environment for safety
API_KEY = "pcsk_4tWwKX_NSmRA1RFweMDNdWMs6j2mU49R87beca6GjtYRnzEZa6wN8Cx84vBE8k4GDEjzvP"

INDEX_NAME = "f1-overtake"
INDEX_DIM = 6  # number of features
MAX_BATCH = 1000

OUTPUT_CSV_TEMPLATE = "overtake_laps_{}_usa.csv"
YEARS = [2022, 2023, 2024]

FEATURE_COLS = [
    'TrackNormalized',  # Track name numeric representation
    'Position',
    'Compound',
    'TyreLife',
    'TrackTemp',
    'Rainfall'
]

METADATA_COLS = ['TrackName', 'Year', 'Driver', 'Team', 'LapNumber']
# ------------------------------------------------------------

# ---------- Step 1: Load & Combine ----------
dfs = []
for year in YEARS:
    path = OUTPUT_CSV_TEMPLATE.format(year)
    if not os.path.exists(path):
        print(f"⚠️ File not found: {path}, skipping...")
        continue

    df = pd.read_csv(path)
    df["Year"] = year

    # Normalize compound types 0–1
    COMPOUND_MAP = {"SOFT": 1, "MEDIUM": 2, "HARD": 3, "INTERMEDIATE": 4, "WET": 5, "UNKNOWN": 0}
    df["Compound"] = df["Compound"].map(COMPOUND_MAP).fillna(0) / 5

    # Normalize track names (numeric ID → 0–1)
    track_map = {t: i for i, t in enumerate(df["TrackName"].unique())}
    df["TrackNormalized"] = df["TrackName"].map(track_map) / max(track_map.values())

    dfs.append(df)

if not dfs:
    raise ValueError("❌ No valid CSVs found. Check file paths or names.")

combined = pd.concat(dfs, ignore_index=True)
print(f"✅ Combined shape: {combined.shape}")

# ---------- Step 2: Global Normalization ----------
scaler = MinMaxScaler()
combined[["Position", "TyreLife", "TrackTemp", "Rainfall"]] = scaler.fit_transform(
    combined[["Position", "TyreLife", "TrackTemp", "Rainfall"]].fillna(0)
)

# Save combined normalized file for debugging
combined.to_csv("overtake_all_years_combined.csv", index=False)
print("💾 Saved: overtake_all_years_combined.csv")

# ---------- Step 3: Pinecone Setup ----------
pc = Pinecone(api_key=API_KEY)

if INDEX_NAME not in pc.list_indexes().names():
    print(f"🧱 Creating index '{INDEX_NAME}'...")
    pc.create_index(
        name=INDEX_NAME,
        dimension=INDEX_DIM,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )

index = pc.Index(INDEX_NAME)
print(f"📡 Connected to index '{INDEX_NAME}'")

# ---------- Step 4: Upload to Pinecone ----------
vectors = combined[FEATURE_COLS].values.tolist()
metadata = combined[METADATA_COLS].to_dict(orient="records")
ids = [f"{row['Year']}_{i}" for i, row in combined.iterrows()]

print(f"\n🚀 Uploading {len(vectors)} total vectors...\n")

for i in tqdm(range(0, len(vectors), MAX_BATCH), desc="Uploading batches"):
    batch_vecs = vectors[i:i + MAX_BATCH]
    batch_meta = metadata[i:i + MAX_BATCH]
    batch_ids = ids[i:i + MAX_BATCH]
    index.upsert(vectors=list(zip(batch_ids, batch_vecs, batch_meta)))

print("✅ All vectors uploaded successfully!")

# ---------- Step 5: Stats ----------
stats = index.describe_index_stats()
print("\n📊 Pinecone Index Stats:")
print(stats)
