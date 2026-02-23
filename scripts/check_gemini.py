import httpx

key = "AIzaSyDmxaQT-G_PmhZg4TBOaGw5qFMmNym6fIQ"
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
