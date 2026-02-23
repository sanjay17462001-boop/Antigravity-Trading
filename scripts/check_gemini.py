import os
import httpx
from dotenv import load_dotenv
from pathlib import Path
load_dotenv(Path(__file__).parent.parent / ".env")

key = os.environ.get("GEMINI_API_KEY", "")
if not key:
    print("ERROR: GEMINI_API_KEY not found in .env file")
    exit(1)
r = httpx.get(f"https://generativelanguage.googleapis.com/v1beta/models?key={key}", timeout=10)
if r.status_code == 200:
    models = r.json().get("models", [])
    for m in models:
        name = m.get("name", "")
        display = m.get("displayName", "")
        if "flash" in name.lower() or "pro" in name.lower() or "gemini-2" in name.lower():
            print(f"  {name}: {display}")
    print(f"\nTotal models available: {len(models)}")
else:
    print(f"Error {r.status_code}: {r.text[:300]}")
