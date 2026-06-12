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

# Hardcoded Wikipedia page titles for players whose names don't match automatically
WIKI_TITLES = {
    "Carlos Alcaraz":              "Carlos_Alcaraz",
    "Ben Shelton":                 "Ben_Shelton_(tennis)",
    "Alex De Minaur":              "Alex_de_Minaur",
    "Taylor Fritz":                "Taylor_Fritz",
    "Flavio Cobolli":              "Flavio_Cobolli",
    "Alexander Bublik":            "Alexander_Bublik",
    "Jiri Lehecka":                "Jiří_Lehečka",
    "Casper Ruud":                 "Casper_Ruud",
    "Karen Khachanov":             "Karen_Khachanov",
    "Lorenzo Musetti":             "Lorenzo_Musetti",
    "Jakub Mensik":                "Jakub_Menšík",
    "Luciano Darderi":             "Luciano_Darderi",
    "Learner Tien":                "Learner_Tien",
    "Valentin Vacherot":           "Valentin_Vacherot",
    "Rafael Jodar":                "Rafael_Jodar",
    "Joao Fonseca":                "João_Fonseca_(tennis)",
    "Tommy Paul":                  "Tommy_Paul_(tennis)",
    "Cameron Norrie":              "Cameron_Norrie",
    "Tomas Martin Etcheverry":     "Tomás_Martín_Etcheverry",
    "Alejandro Tabilo":            "Alejandro_Tabilo",
    "Brandon Nakashima":           "Brandon_Nakashima",
    "Ugo Humbert":                 "Ugo_Humbert",
    "Matteo Arnaldi":              "Matteo_Arnaldi",
    "Ignacio Buse":                "Ignacio_Buse",
    "Corentin Moutet":             "Corentin_Moutet",
    "Alexander Blockx":            "Alexander_Blockx",
    "Alex Michelsen":              "Alex_Michelsen",
    "Mariano Navone":              "Mariano_Navone",
    "Zizou Bergs":                 "Zizou_Bergs",
    "Juan Manuel Cerundolo":       "Juan_Manuel_Cerundolo",
    "Adrian Mannarino":            "Adrian_Mannarino",
    "Matteo Berrettini":           "Matteo_Berrettini",
    "Miomir Kecmanovic":           "Miomir_Kecmanović",
    "Nuno Borges":                 "Nuno_Borges_(tennis)",
    "Raphael Collignon":           "Raphaël_Collignon",
    "Thiago Agustin Tirante":      "Thiago_Agustín_Tirante",
    "Terence Atmane":              "Terence_Atmane",
    "Gabriel Diallo":              "Gabriel_Diallo",
    "Botic Van De Zandschulp":     "Botic_van_de_Zandschulp",
    "Sebastian Baez":              "Sebastián_Báez",
    "Camilo Ugo Carabelli":        "Camilo_Ugo_Carabelli",
    "Martin Landaluce":            "Martín_Landaluce",
    "Yannick Hanfmann":            "Yannick_Hanfmann",
    "Roman Andres Burruchaga":     "Román_Andrés_Burruchaga",
    "Vit Kopriva":                 "Vít_Kopřiva",
    "Ethan Quinn":                 "Ethan_Quinn_(tennis)",
    "Hamad Medjedovic":            "Hamad_Medjedovic",
    "Aleksandar Kovacevic":        "Aleksandar_Kovačević_(tennis)",
    "Dino Prizmic":                "Dino_Prižmić",
    "Pablo Carreno-Busta":         "Pablo_Carreño_Busta",
    "Adolfo Daniel Vallejo":       "Adolfo_Daniel_Vallejo",
    "Jenson Brooksby":             "Jenson_Brooksby",
    "Valentin Royer":              "Valentin_Royer",
    "Marton Fucsovics":            "Márton_Fucsovics",
    "Kamil Majchrzak":             "Kamil_Majchrzak",
    "Jan-Lennard Struff":          "Jan-Lennard_Struff",
    "Mattia Bellucci":             "Mattia_Bellucci",
    "James Duckworth":             "James_Duckworth_(tennis)",
    "Marco Trungelliti":           "Marco_Trungelliti",
    "Arthur Cazaux":               "Arthur_Cazaux",
    "Daniel Merida Aguilar":       "Daniel_Mérida",
    "Jesper De Jong":              "Jesper_de_Jong_(tennis)",
    "Daniel Altmaier":             "Daniel_Altmaier",
    "Reilly Opelka":               "Reilly_Opelka",
    "Emilio Nava":                 "Emilio_Nava",
    "Marcos Giron":                "Marcos_Giron",
    "Francisco Comesana":          "Francisco_Comesaña",
    "Alexei Popyrin":              "Alexei_Popyrin",
    "Adam Walton":                 "Adam_Walton_(tennis)",
    "Quentin Halys":               "Quentin_Halys",
    "Giovanni Mpetshi Perricard":  "Giovanni_Mpetshi_Perricard",
    "Jaime Faria":                 "Jaime_Faria_(tennis)",
    "Luca Van Assche":             "Luca_Van_Assche",
    "Benjamin Bonzi":              "Benjamin_Bonzi",
    "Aleksandar Vukic":            "Aleksandar_Vukic",
}

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
    """Get photo URL from Wikipedia REST API."""
    # Use hardcoded title if available, otherwise try name directly
    title = WIKI_TITLES.get(player_name, player_name.replace(" ", "_"))

    try:
        r = requests.get(
            f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}",
            headers=WIKI_HEADERS,
            timeout=10
        )
        if r.status_code == 200:
            thumb = r.json().get("thumbnail", {}).get("source", "")
            if thumb:
                return thumb
    except Exception as e:
        print(f"    ⚠ Wikipedia error: {e}")

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
    rank = entry.get("position", 1)

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
            print(f"  {'✓ Downloaded' if has_photo else '– Download failed'}")
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

    time.sleep(4)

# ── Write players.json ────────────────────────────────────────────────────────

with open(PLAYERS_OUT, "w", encoding="utf-8") as f:
    json.dump(players_out, f, ensure_ascii=False, indent=2)

print(f"\nDone. {len(players_out)} players written.")
print(f"Players with photos: {sum(1 for p in players_out if p['photo'])}/100")
