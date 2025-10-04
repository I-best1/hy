# Run this in PowerShell to start the dataagent (assumes Python 3.10+ installed)
python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt; python -m uvicorn app:app --host 0.0.0.0 --port 3001 --reload
