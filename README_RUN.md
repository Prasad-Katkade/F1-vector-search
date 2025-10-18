# Running the F1 vector upload/query scripts (Windows PowerShell)

This project uses Pinecone for vector storage. For safety, the Pinecone API key is read from an environment variable named `PINECONE_API_KEY`.

1) Create a virtual environment and install dependencies

PowerShell commands:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2) Provide your Pinecone API key

Option A: create a `.env` file in the repo root (recommended for local testing). Copy `.env.example` to `.env` and paste your key.

Option B: set the environment variable in your current PowerShell session (temporary):

```powershell
$env:PINECONE_API_KEY = 'pcsk_...'
```

Option C: set it permanently via System environment variables (Windows Settings) or PowerShell profile.

3) Run the scripts

From the repository root (where `backend/` lives):

Upload vectors (ensure CSVs exist as expected by `overtake_upload.py`):

```powershell
python .\backend\overtake_upload.py
```

Query the index:

```powershell
python .\backend\query_overtake.py
```

Notes:
- `sample_data.py` shows how to produce normalized CSVs using FastF1; install and configure cache as required.
- Replace hard-coded filenames in the scripts if your CSVs are named differently.
- The repo intentionally does not contain the Pinecone API key. Do not commit your `.env` to source control.
