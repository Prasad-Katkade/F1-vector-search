import os
import pandas as pd
from tqdm import tqdm
from sklearn.preprocessing import MinMaxScaler
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv
import os

load_dotenv()

# ---------- Pinecone Setup ----------
API_KEY = os.getenv("API_KEY")
INDEX_NAME = "f1-cliff"
INDEX_DIM = 7  # number of feature dimensions (updated from 6 → 7)
MAX_BATCH = 1000

OUTPUT_CSV_TEMPLATE = "tire_cliff_laps_{}_usa.csv"
YEARS = [2022, 2023, 2024]

# ---------- Feature + Metadata Columns ----------
FEATURE_COLS = [
    'TrackNormalized',  # encoded track
    'Compound',         # normalized tire compound
    'TyreLife',         # normalized tire wear
    'TrackTemp',        # normalized track temp
    'Rainfall',         # normalized rainfall
    'LapNumber',        # normalized lap
    'Position'          # normalized driver position
]

METADATA_COLS = [
    'Driver',
    'Year',
    'LapTimeLoss',
    'TrackName',
    'Team'
]
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

    # Map compound types → 0–1 range
    COMPOUND_MAP = {"SOFT": 1, "MEDIUM": 2, "HARD": 3, "INTERMEDIATE": 4, "WET": 5, "UNKNOWN": 0}
    df["Compound"] = df["Compound"].map(COMPOUND_MAP).fillna(0) / 5.0

    # Assign numeric ID to each track → normalize 0–1
    track_map = {t: i for i, t in enumerate(df["TrackName"].unique())}
    df["TrackNormalized"] = df["TrackName"].map(track_map) / max(track_map.values())

    # Fill missing values for numeric columns
    for col in ["TyreLife", "TrackTemp", "Rainfall", "LapNumber", "Position"]:
        df[col] = df[col].fillna(0)

    dfs.append(df)

if not dfs:
    raise ValueError("❌ No valid CSVs found. Check file paths or names.")

combined = pd.concat(dfs, ignore_index=True)
print(f"✅ Combined shape: {combined.shape}")

# ---------- Step 2: Global Normalization ----------
scaler = MinMaxScaler()
cols_to_scale = ["TyreLife", "TrackTemp", "Rainfall", "LapNumber", "Position"]
combined[cols_to_scale] = scaler.fit_transform(combined[cols_to_scale])

# Save combined normalized file for reference
combined.to_csv("cliff_all_years_combined.csv", index=False)
print("💾 Saved normalized data: cliff_all_years_combined.csv")

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
