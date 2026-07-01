import math
import os
from pathlib import Path
import threading
from collections import defaultdict
import requests
from PIL import Image

session = requests.Session()
session.headers.update(
    {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
)

file_write_lock = threading.Lock()

TILE_DIR = "tiles"
OUTPUT_DIR = Path("output")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
FORMAT = "png"
CHUNK_SIZE = 10000
TILE_SIZE = 256
MAX_WORKERS = 10
IMG_FORMATS = ["png", "jpg", "webp"]

draw_control = {
    "draw": {
        "polygon": False,
        "marker": False,
        "circle": False,
        "rectangle": True,
        "polyline": False,
        "circlemarker": False,
    },
    "edit": {
        "edit": True,
        "remove": True,
    },
}


def geocode_place(place_name, api_key=None):
    """Convert a place name to latitude and longitude using geocode.maps.co API."""
    if not api_key:
        api_key = os.environ.get("GEOCODE_API_KEY", "")
        if not api_key:
            print("⚠️  Geocoding API key not found.")
            print("Set GEOCODE_API_KEY environment variable or provide one now.")
            api_key = input(
                "Enter your geocode.maps.co API key (or press Enter to use free tier): "
            ).strip()

    try:
        url = "https://geocode.maps.co/search"
        params = {"q": place_name}
        if api_key:
            params["api_key"] = api_key

        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            results = response.json()
            if results:
                result = results[0]
                lat = float(result["lat"])
                lon = float(result["lon"])
                display_name = result.get("display_name", place_name)
                print(f"\n✓ Found: {display_name}")
                print(f"  Coordinates: {lat:.6f}, {lon:.6f}")
                return lat, lon
            else:
                print(
                    f"\n✗ No results found for '{place_name}'. Please try a different query."
                )
                return None, None
        else:
            print(f"\n✗ Geocoding error: HTTP {response.status_code}")
            return None, None
    except Exception as e:
        print(f"\n✗ Geocoding failed: {e}")
        return None, None


def deg2num(lat_deg, lon_deg, zoom):
    """Converts Latitude/Longitude to standard slippy map X and Y tile coordinates."""
    lat_rad = math.radians(lat_deg)
    n = 2.0**zoom
    x_tile = int((lon_deg + 180.0) / 360.0 * n)
    y_tile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return x_tile, y_tile


def rect_coords_to_tiles(coords, zoom, all_tiles=False):
    #  1-->--2
    # /|\   \|/
    #  0     3

    bottom_left = coords[0] # 0
    top_left = coords[1] # 1
    top_right = coords[2] # 2
    bottom_right = coords[3] # 3

    bottom_left_tile = deg2num(bottom_left["lat"], bottom_left["lng"], zoom)
    top_left_tile = deg2num(top_left["lat"], top_left["lng"], zoom)
    top_right_tile = deg2num(top_right["lat"], top_right["lng"], zoom)
    bottom_right_tile = deg2num(bottom_right["lat"], bottom_right["lng"], zoom)

    if all_tiles:
        return [bottom_left_tile, top_left_tile, top_right_tile, bottom_right_tile]

    return [
        top_left_tile[0],
        bottom_right_tile[0],
        top_left_tile[1],
        bottom_right_tile[1],
    ]


def find_latest_tile(coords, zoom, url_pattern: str):
    """Worker function: Checks cache, then checks dates backwards, logs URL if found, and returns."""
    x, y = coords
    z = zoom
    url = url_pattern.format(x=x, y=y, z=z)
    try:
        response = session.head(url, timeout=5)
        if response.status_code == 200:
            return x, y, url
    except requests.exceptions.RequestException:
        pass
    return None


def download_tile(tile_info):
    """Downloads a single tile if it hasn't been downloaded yet."""
    x, y, url = tile_info
    filepath = Path(TILE_DIR, f"{x}_{y}.png")
    filepath.parent.mkdir(parents=True, exist_ok=True)

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            with open(filepath, "wb") as f:
                f.write(response.content)
            return x, y, filepath
    except Exception as e:
        print(f'Failed to download tile {x}_{y}.png: {e}')
    return None


def stitch_in_chunks(valid_tiles: list, format: str, filename: str):
    """Groups tiles into smaller grids and stitches multiple PNGs."""
    chunks = defaultdict(list)
    for x, y, filepath in valid_tiles:
        chunk_x = x // CHUNK_SIZE
        chunk_y = y // CHUNK_SIZE
        chunks[(chunk_x, chunk_y)].append((x, y, filepath))

    print(f"\nCreated {len(chunks)} separate image chunk(s) to stitch.")

    for (cx, cy), chunk_tiles in chunks.items():
        min_x = min(t[0] for t in chunk_tiles)
        max_x = max(t[0] for t in chunk_tiles)
        min_y = min(t[1] for t in chunk_tiles)
        max_y = max(t[1] for t in chunk_tiles)

        width_px = ((max_x - min_x) + 1) * TILE_SIZE
        height_px = ((max_y - min_y) + 1) * TILE_SIZE


        output_path = OUTPUT_DIR / filename

        canvas = Image.new(
            "RGB" if format == "JPEG" else "RGBA", (width_px, height_px), (0, 0, 0, 0)
        )

        for x, y, filepath in chunk_tiles:
            if os.path.exists(filepath):
                try:
                    with Image.open(filepath) as tile_img:
                        tile_img = tile_img.convert("RGBA")
                        paste_x = (x - min_x) * TILE_SIZE
                        paste_y = (y - min_y) * TILE_SIZE
                        canvas.paste(tile_img, (paste_x, paste_y))
                except Exception as e:
                    print(f"Error pasting {filepath}: {e}")

        canvas.save(output_path, FORMAT, lossless=1 if FORMAT == "WEBP" else None)
