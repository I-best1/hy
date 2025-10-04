# Simple runner for *nix shells. On Windows use the README instructions (venv & uvicorn)
python -m uvicorn app:app --host 0.0.0.0 --port 3001 --reload
