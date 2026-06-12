"""
fetch_atp.py
------------
Fetches the ATP top 100 singles rankings + player headshots via the
Tennis API (tennis-api-atp-wta-itf.p.rapidapi.com) on RapidAPI.

Outputs:
  data/players.json   — array of {rank, id, name, country, points, photo}
  game/images/        — one JPEG per player, named by player ID (e.g. 104925.jpg)

Run manually:  RAPIDAPI_KEY=your_key python scripts/fetch_atp.py
Run via CI:    GitHub Actions injects RAPIDAPI_KEY from repo secrets
"""

import os
import json
import time
import pathlib
import requests

# ── Config ────────────────────────────────────────────────────────────────────

RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "")
if not RAPIDAPI_KEY:
    raise SystemExit("ERROR: RAPIDAPI_KEY env var is not set.")

BASE_URL  = "https://tennis-api-atp-wta-itf.p.rapidapi.com"
HEADERS   = {
    "X-RapidAPI-Key":  RAPIDAPI_KEY,
    "X-RapidAPI-Host": "tennis-api-atp-wta-itf.p.rapidapi.com",
}

REPO_ROOT   = pathlib.Path(__file__).parent.parent
DATA_DIR    = REPO_ROOT / "data"
IMAGES_DIR  = REPO_ROOT / "game" / "images"
PLAYERS_OUT = DATA_DIR / "players.json"

DATA_DIR.mkdir(parents=True, exist_ok=True)
IMAGES_DIR.mkdir(parents=True, exist_ok=True)

TOP_N = 100  # number of ranked players to keep

# ── Helpers ───────────────────────────────────────────────────────────────────

def get(path: str, params: dict = None) -> dict | list:
    url = f"{BASE_URL}{path}"
    resp = requests.get(url, headers=HEADERS, params=params, timeout=15)
    resp.raise_for_status()
    return resp.json()


def download_image(url: str, dest: pathlib.Path) -> bool:
    """Download image from url to dest. Returns True on success."""
    try:
        resp = requests.get(url, timeout=15, stream=True)
        resp.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        return True
    except Exception as e:
        print(f"  ⚠ Could not download {url}: {e}")
        return False

# ── Step 1: Fetch rankings (top 100) ─────────────────────────────────────────

print("Fetching ATP singles rankings …")
# The rankings endpoint returns the full list sorted by rank.
# pageSize=100 gets all top 100 in one call.
rankings = get("/tennis/v2/atp/player", params={
    "filter": "PlayerGroup:singles",
    "pageSize": 100,
    "pageNo": 1,
})

# Sort by currentRank ascending, keep only top 100 ranked players
ranked = [p for p in rankings if p.get("currentRank") is not None]
ranked.sort(key=lambda p: p["currentRank"])
top100 = ranked[:TOP_N]
print(f"  Got {len(top100)} ranked players.")

# ── Step 2: Fetch profile for each player (for photo URL) ─────────────────────

players_out = []

for i, player in enumerate(top100, 1):
    pid   = player["id"]
    name  = player["name"]
    rank  = player["currentRank"]
    print(f"  [{i:3}/{TOP_N}] #{rank} {name} (id={pid})")

    # Fetch full profile to get photo URL
    try:
        profile = get(f"/tennis/v2/atp/player/profile/{pid}")
    except Exception as e:
        print(f"    ⚠ Profile fetch failed: {e}")
        profile = {}

    # Photo field is typically 'photo' or 'photoUrl' — handle both
    photo_url = (
        profile.get("photo")
        or profile.get("photoUrl")
        or profile.get("image")
        or ""
    )

    # Download photo locally
    img_path = IMAGES_DIR / f"{pid}.jpg"
    has_photo = False
    if photo_url:
        if img_path.exists():
            print(f"    ✓ Photo already cached.")
            has_photo = True
        else:
            has_photo = download_image(photo_url, img_path)
            if has_photo:
                print(f"    ✓ Photo downloaded.")
    else:
        print(f"    – No photo URL in profile.")

    players_out.append({
        "rank":    rank,
        "id":      pid,
        "name":    name,
        "country": player.get("countryAcr", ""),
        "points":  player.get("points", 0),
        # Relative path used by the game HTML (images live next to index.html)
        "photo":   f"images/{pid}.jpg" if has_photo else "",
        "photoUrl": photo_url,  # original URL as fallback
    })

    # Polite rate-limiting: 100 req/min allowed, we have 100 profile calls
    # 0.7s gap = ~85 req/min, safely under the limit
    time.sleep(0.7)

# ── Step 3: Write players.json ────────────────────────────────────────────────

with open(PLAYERS_OUT, "w", encoding="utf-8") as f:
    json.dump(players_out, f, ensure_ascii=False, indent=2)

print(f"\nDone. Wrote {len(players_out)} players to {PLAYERS_OUT}")
print(f"Images saved to {IMAGES_DIR}")
