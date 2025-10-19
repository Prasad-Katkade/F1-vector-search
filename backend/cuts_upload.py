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
INDEX_NAME = "f1-cuts"
INDEX_DIM = 8 
MAX_BATCH = 1000

OUTPUT_CSV_TEMPLATE = "undercut_laps_{}_williams.csv"
YEARS = [2020, 2021, 2022, 2023, 2024]

# ---------- Feature + Metadata Columns ----------
FEATURE_COLS = [
    'TrackNormalized',
    'LapNumber',
    'Position',
    'NewTireCompound',
    'Rival_Compound',
    'Rival_TyreLife',
    'GapToRival_BeforePit',
    'TrackTemp',
    'Rainfall'
]

METADATA_COLS = [
    'Driver',
    'Year',
    'TrackName',
    'Team',
    'Rival_Pitted_Lap'
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

    # Map numeric normalization for compounds if needed
    # Already normalized in extraction, so we skip mapping

    # Assign numeric ID to each track → normalize 0–1
    track_map = {t: i for i, t in enumerate(df["TrackName"].unique())}
    df["TrackNormalized"] = df["TrackName"].map(track_map) / max(track_map.values())

    # Fill missing values for numeric columns
    for col in FEATURE_COLS:
        df[col] = df[col].fillna(0)

    dfs.append(df)

if not dfs:
    raise ValueError("❌ No valid CSVs found. Check file paths or names.")

combined = pd.concat(dfs, ignore_index=True)
print(f"✅ Combined shape: {combined.shape}")

# ---------- Step 2: Global Normalization ----------
scaler = MinMaxScaler()
cols_to_scale = ['LapNumber', 'Position', 'NewTireCompound', 'Rival_Compound', 'Rival_TyreLife', 'GapToRival_BeforePit', 'TrackTemp', 'Rainfall']
combined[cols_to_scale] = scaler.fit_transform(combined[cols_to_scale])

# Save combined normalized file for reference
combined.to_csv("undercut_all_years_combined.csv", index=False)
print("💾 Saved normalized data: undercut_all_years_combined.csv")

# ---------- Step 3: Pinecone Setup ----------
pc = Pinecone(api_key=API_KEY)

if INDEX_NAME not in pc.list_indexes().names():
    print(f"🧱 Creating index '{INDEX_NAME}'...")
    pc.create_index(
        name=INDEX_NAME,
        dimension=len(FEATURE_COLS),
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
