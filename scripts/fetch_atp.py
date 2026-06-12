"""
fetch_atp.py
------------
Fetches ATP top 100 singles rankings via RapidAPI, then gets
player headshots from Wikipedia REST API.

Run manually:  set RAPIDAPI_KEY=your_key && python scripts/fetch_atp.py
"""

import os, json, time, pathlib, requests

RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "")
if not RAPIDAPI_KEY:
    raise SystemExit("ERROR: RAPIDAPI_KEY env var is not set.")

RAPIDAPI_HEADERS = {
    "X-RapidAPI-Key":  RAPIDAPI_KEY,
    "X-RapidAPI-Host": "tennis-api-atp-wta-itf.p.rapidapi.com",
}
WIKI_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"}

REPO_ROOT   = pathlib.Path(__file__).parent.parent
DATA_DIR    = REPO_ROOT / "game" / "data"
IMAGES_DIR  = REPO_ROOT / "game" / "images"
PLAYERS_OUT = DATA_DIR / "players.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

def get_rankings():
    r = requests.get(
        "https://tennis-api-atp-wta-itf.p.rapidapi.com/tennis/v2/atp/ranking/singles",
        headers=RAPIDAPI_HEADERS,
        params={"pageSize": 100, "pageNo": 1},
        timeout=15
    )
    r.raise_for_status()
    data = r.json()
    if isinstance(data, dict) and "data" in data:
        return data["data"]
    return data

def get_wikipedia_photo(player_name):
    """Try multiple name formats against Wikipedia REST API."""
    # Build a list of name variants to try
    name_underscored = player_name.replace(" ", "_")
    last_name = player_name.split()[-1]
    first_last = "_".join(player_name.split()[:2]) if len(player_name.split()) > 1 else name_underscored

    variants = [
        name_underscored,
        first_last,
        last_name,
    ]

    for variant in variants:
        try:
            r = requests.get(
                f"https://en.wikipedia.org/api/rest_v1/page/summary/{variant}",
                headers=WIKI_HEADERS,
                timeout=10
            )
            if r.status_code == 200:
                data = r.json()
                # Make sure it's actually a person/tennis player page
                thumb = data.get("thumbnail", {}).get("source", "")
                if thumb:
                    return thumb
        except Exception:
            continue

    # Final fallback: use search API
    try:
        search = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={"action":"query","list":"search","srsearch":player_name+" tennis","srlimit":1,"format":"json"},
            headers=WIKI_HEADERS,
            timeout=10
        )
        results = search.json().get("query", {}).get("search", [])
        if results:
            title = results[0]["title"].replace(" ", "_")
            r = requests.get(
                f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}",
                headers=WIKI_HEADERS,
                timeout=10
            )
            if r.status_code == 200:
                return r.json().get("thumbnail", {}).get("source", "")
    except Exception:
        pass

    return ""

def download_image(url, dest):
    try:
        resp = requests.get(url, timeout=15, stream=True, headers=WIKI_HEADERS)
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"    ⚠ Download failed: {e}")
        return False

# ── Fetch rankings ────────────────────────────────────────────────────────────

print("Fetching ATP singles rankings...")
rankings = get_rankings()[:100]
print(f"  Got {len(rankings)} players.\n")

# ── Fetch photos + build output ───────────────────────────────────────────────

players_out = []

for i, entry in enumerate(rankings, 1):
    p    = entry["player"]
    pid  = p["id"]
    name = p["name"]
    rank = entry.get("position", i)

    print(f"[{i:3}/100] #{rank} {name}")

    img_path  = IMAGES_DIR / f"{pid}.jpg"
    has_photo = False

    if img_path.exists():
        print(f"  ✓ Cached")
        has_photo = True
    else:
        photo_url = get_wikipedia_photo(name)
        if photo_url:
            has_photo = download_image(photo_url, img_path)
            if has_photo:
                print(f"  ✓ Downloaded")
            else:
                print(f"  – Download failed")
        else:
            print(f"  – No photo found")

    players_out.append({
        "rank":    rank,
        "id":      pid,
        "name":    name,
        "country": p.get("countryAcr", ""),
        "points":  entry.get("point", 0),
        "photo":   f"images/{pid}.jpg" if has_photo else "",
    })

    time.sleep(0.3)

# ── Write players.json ────────────────────────────────────────────────────────

with open(PLAYERS_OUT, "w", encoding="utf-8") as f:
    json.dump(players_out, f, ensure_ascii=False, indent=2)

print(f"\nDone. {len(players_out)} players written.")
print(f"Players with photos: {sum(1 for p in players_out if p['photo'])}/100")
