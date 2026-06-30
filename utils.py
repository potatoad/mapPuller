import math
import os
import threading
from collections import defaultdict
import requests
from classes import Zoom
from PIL import Image

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
})

file_write_lock = threading.Lock()

LOG_FILE = 'log.txt'
TILE_DIR = 'tiles'
OUTPUT_DIR = 'output'
FORMAT = 'png'
CHUNK_SIZE = 100
TILE_SIZE = 256
MAX_WORKERS = 10


def geocode_place(place_name, api_key=None):
    """Convert a place name to latitude and longitude using geocode.maps.co API."""
    if not api_key:
        api_key = os.environ.get("GEOCODE_API_KEY", "")
        if not api_key:
            print("\n⚠️  Geocoding API key not found.")
            print("Set GEOCODE_API_KEY environment variable or provide one now.")
            api_key = input("Enter your geocode.maps.co API key (or press Enter to use free tier): ").strip()

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
                print(f"\n✗ No results found for '{place_name}'. Please try a different query.")
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
    n = 2.0 ** zoom
    x_tile = int((lon_deg + 180.0) / 360.0 * n)
    y_tile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return x_tile, y_tile


def rect_coords_to_tiles(coords, zoom: Zoom):
    # 0: Bottom left
    # 1: Top Left
    # 2: Top Right
    # 3: Bottom Right

    #  1---->----2
    #  |         |
    # /|\       \|/
    #  |         |
    #  0         3

    bottom_left = coords[0]
    top_left = coords[1]
    top_right = coords[2]
    bottom_right = coords[3]

    bottom_left_tile = deg2num(bottom_left['lat'], bottom_left['lng'], zoom.zoom)
    top_left_tile = deg2num(top_left['lat'], top_left['lng'], zoom.zoom)
    top_right_tile = deg2num(top_right['lat'], top_right['lng'], zoom.zoom)
    bottom_right_tile = deg2num(bottom_right['lat'], bottom_right['lng'], zoom.zoom)

    return [top_left_tile[0], bottom_right_tile[0], top_left_tile[1], bottom_right_tile[1]]


def find_latest_tile(coords, zoom: Zoom, url_pattern: str):
    """Worker function: Checks cache, then checks dates backwards, logs URL if found, and returns."""
    x, y = coords
    z = zoom.zoom
    # Check if we already have this file on disk
    filepath = os.path.join(TILE_DIR, f"{x}_{y}_{z}.png")
    if os.path.exists(filepath):
        # Log a dummy URL so the parser grabs the X and Y for stitching, but we avoid network calls
        dummy_url = f"LOCAL_CACHE/skip_download/{x}_{y}_{z}.png"
        log_url_to_file(dummy_url)
        return (x, y, "CACHED")

    # If series doesn't require date, check URL directly

    url = url_pattern.format(z=z, x=x, y=y)
    print(url)
    try:
        response = session.head(url, timeout=5)
        if response.status_code == 200:
            log_url_to_file(url)
            return (x, y, "FOUND")
        elif response.status_code == 429:
            print(f"[WARNING] Rate Limited (429) at x:{x} y:{y}. Server is blocking us.")
    except requests.exceptions.RequestException:
        pass
    print(f"[MISSING] x:{x} y:{y}  -->  Not found.")
    return (x, y, None)
'https://mapseries-tilesets.s3.amazonaws.com/bartholomew_england_wales_1920s/10/505/333.png'
'https://mapseries-tilesets.s3.amazonaws.com/bartholomew_england_wales_1920s/16/32418/21295.png'

def setup_directories(TILE_DIR=TILE_DIR, OUTPUT_DIR=OUTPUT_DIR):
    for directory in [TILE_DIR, OUTPUT_DIR]:
        if not os.path.exists(directory):
            os.makedirs(directory)


def log_url_to_file(url):
    """Safely appends a URL to the log file."""
    with file_write_lock:
        with open(LOG_FILE, "a") as f:
            f.write(url + "\n")


def parse_urls_from_log():
    """Reads the log file and extracts coordinates and URLs."""
    tiles_data = []
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, "r") as f:
        for line in f:
            url = line.strip()
            if not url or url.startswith("---"):
                continue
            parts = url.split('/')
            try:
                y = int(parts[-1].replace('.png', ''))
                x = int(parts[-2])
                tiles_data.append((x, y, url))
            except ValueError:
                continue
    return tiles_data


def download_tile(tile_info, zoom):
    """Downloads a single tile if it hasn't been downloaded yet."""
    print(tile_info)
    x, y, url = tile_info
    z = zoom
    filepath = os.path.join(TILE_DIR, f"{x}_{y}_{z}.png")

    # Because find_latest_tile logs a dummy URL for cached files, this check
    # triggers immediately and safely skips the requests.get() step.
    if os.path.exists(filepath):
        return (x, y, filepath)

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                f.write(response.content)
            return (x, y, filepath)
    except Exception:
        pass
    return None


def stitch_in_chunks(valid_tiles):
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

        # def generate_filename(args, SCALE_LABEL, ZOOM_LEVEL, cx, cy, FORMAT, X_CENTRE=None, Y_CENTRE=None):
        #     if args.lat is not None and args.lon is not None:
        #         return (
        #             f"map_lat{args.lat}_lon{args.lon}_1_{SCALE_LABEL}_z{ZOOM_LEVEL}_r{args.radius}_"
        #             f"X{cx}_Y{cy}.{FORMAT.lower()}"
        #         )
        #     else:
        #         return (
        #             f"map_x{X_CENTRE}_y{Y_CENTRE}_1_{SCALE_LABEL}_z{ZOOM_LEVEL}_r{args.radius}_"
        #             f"X{cx}_Y{cy}.{FORMAT.lower()}"
        #         )
        #
        # filename = generate_filename(args, SCALE_LABEL, ZOOM_LEVEL, cx, cy, FORMAT,
        #                              X_CENTRE if 'X_CENTRE' in globals() else None,
        #                              Y_CENTRE if 'Y_CENTRE' in globals() else None)
        output_path = os.path.join(OUTPUT_DIR, 'filename.png')

        canvas = Image.new('RGB' if FORMAT == "JPEG" else 'RGBA', (width_px, height_px), (0, 0, 0, 0))

        for x, y, filepath in chunk_tiles:
            if os.path.exists(filepath):
                try:
                    with Image.open(filepath) as tile_img:
                        tile_img = tile_img.convert("RGBA")
                        paste_x = (x - min_x) * TILE_SIZE
                        paste_y = (y - min_y) * TILE_SIZE
                        canvas.paste(tile_img, (paste_x, paste_y))
                except Exception as e:
                    print(f"  -> Error pasting {filepath}: {e}")

        canvas.save(output_path, FORMAT, lossless=1 if FORMAT == "WEBP" else None)
