import os
import requests
import concurrent.futures
import threading
import argparse
import math
from collections import defaultdict
from PIL import Image

def deg2num(lat_deg, lon_deg, zoom):
    """Converts Latitude/Longitude to standard slippy map X and Y tile coordinates."""
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    x_tile = int((lon_deg + 180.0) / 360.0 * n)
    y_tile = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return x_tile, y_tile

# --- Command Line Arguments Setup ---
parser = argparse.ArgumentParser(description="Scrape, download, and stitch OS map tiles using Lat/Lon or X/Y.")

parser.add_argument("--zoom", type=int, default=15, help="Zoom level (default: 15)")

# Coordinate based targeting
parser.add_argument("--lat", type=float, help="Center Latitude (e.g., 50.88074)")
parser.add_argument("--lon", type=float, help="Center Longitude (e.g., -0.21368)")
parser.add_argument("--radius", type=int, default=10, help="If using Lat/Lon, how many tiles in each direction to fetch (default: 10)")

# Manual X/Y targeting (Fallbacks)
parser.add_argument("--x-start", type=int, default=16354, help="Starting X coordinate (if not using lat/lon)")
parser.add_argument("--x-end", type=int, default=16374, help="Ending X coordinate (if not using lat/lon)")
parser.add_argument("--y-start", type=int, default=10977, help="Starting Y coordinate (if not using lat/lon)")
parser.add_argument("--y-end", type=int, default=10997, help="Ending Y coordinate (if not using lat/lon)")

# File system and script configuration
parser.add_argument("--log-file", type=str, default="successful_tile_urls.txt", help="Log file path")
parser.add_argument("--tile-dir", type=str, default="downloaded_tiles", help="Directory to save downloaded tiles")
parser.add_argument("--output-dir", type=str, default="stitched_chunks", help="Directory to save stitched chunks")
parser.add_argument("--tile-size", type=int, default=256, help="Tile size in pixels (default: 256)")
parser.add_argument("--max-workers", type=int, default=15, help="Maximum concurrent threads (default: 15)")
parser.add_argument("--chunk-size", type=int, default=50, help="Grid size for stitched chunks. 50 = 50x50 tiles (default: 50)")

args = parser.parse_args()

# --- Configuration & Logic Routing ---
ZOOM_LEVEL = args.zoom

# Determine bounding box based on Lat/Lon OR explicit X/Y
if args.lat is not None and args.lon is not None:
    center_x, center_y = deg2num(args.lat, args.lon, ZOOM_LEVEL)
    print(f"Calculated central tile for [{args.lat}, {args.lon}] at Zoom {ZOOM_LEVEL}: X:{center_x}, Y:{center_y}")
    
    # Create a bounding box around the central tile based on the radius
    X_START = center_x - args.radius
    X_END = center_x + args.radius + 1  # +1 because Python range() is exclusive at the end
    Y_START = center_y - args.radius
    Y_END = center_y + args.radius + 1
else:
    # Fallback to manual X/Y inputs
    X_START, X_END = args.x_start, args.x_end 
    Y_START, Y_END = args.y_start, args.y_end

LOG_FILE = args.log_file
TILE_DIR = args.tile_dir
OUTPUT_DIR = args.output_dir
TILE_SIZE = args.tile_size
MAX_WORKERS = args.max_workers
CHUNK_SIZE = args.chunk_size 

# Global session for connection pooling
session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
})

file_write_lock = threading.Lock()
Image.MAX_IMAGE_PIXELS = None 

def log_url_to_file(url):
    """Safely appends a URL to the log file."""
    with file_write_lock:
        with open(LOG_FILE, "a") as f:
            f.write(url + "\n")

def generate_date_list(start_year, start_month, end_year, end_month):
    """Generates a list of YYYY-MM strings going backwards in time."""
    dates = []
    y, m = start_year, start_month
    while (y > end_year) or (y == end_year and m >= end_month):
        dates.append(f"{y}-{m:02d}")
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return dates

def find_latest_tile(coords):
    """Worker function: Checks dates backwards, logs URL if found, and returns."""
    x, y, dates_to_check = coords
    for map_date in dates_to_check:
        url = f"https://tiles.leisure.maps.osinfra.net/{map_date}/1_25k/{ZOOM_LEVEL}/{x}/{y}.png"
        try:
            response = session.head(url, timeout=5)
            if response.status_code == 200:
                print(f"[FOUND] {url}")
                log_url_to_file(url)
                return (x, y, map_date)
            elif response.status_code == 429:
                print(f"[WARNING] Rate Limited (429) at x:{x} y:{y}. Server is blocking us.")
        except requests.exceptions.RequestException:
            pass
    print(f"[MISSING] x:{x} y:{y}  -->  Not found in any dates.")
    return (x, y, None)

def setup_directories():
    for directory in [TILE_DIR, OUTPUT_DIR]:
        if not os.path.exists(directory):
            os.makedirs(directory)

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

def download_tile(tile_info):
    """Downloads a single tile if it hasn't been downloaded yet."""
    x, y, url = tile_info
    filepath = os.path.join(TILE_DIR, f"{x}_{y}.png")
    if os.path.exists(filepath):
        return (x, y, filepath)
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                f.write(response.content)
            print(f"[DOWNLOADED] {x}_{y}.png")
            return (x, y, filepath)
    except Exception:
        pass
    return None

def stitch_in_chunks(valid_tiles):
    """Groups tiles into smaller grids and stitches multiple PNGs."""
    print(f"\nGrouping {len(valid_tiles)} tiles into chunks of {CHUNK_SIZE}x{CHUNK_SIZE}...")
    
    chunks = defaultdict(list)
    for x, y, filepath in valid_tiles:
        chunk_x = x // CHUNK_SIZE
        chunk_y = y // CHUNK_SIZE
        chunks[(chunk_x, chunk_y)].append((x, y, filepath))
        
    print(f"Created {len(chunks)} separate image chunks to stitch.\n")

    for (cx, cy), chunk_tiles in chunks.items():
        min_x = min(t[0] for t in chunk_tiles)
        max_x = max(t[0] for t in chunk_tiles)
        min_y = min(t[1] for t in chunk_tiles)
        max_y = max(t[1] for t in chunk_tiles)
        
        width_px = ((max_x - min_x) + 1) * TILE_SIZE
        height_px = ((max_y - min_y) + 1) * TILE_SIZE
        
        filename = f"map_X{min_x}-{max_x}_Y{min_y}-{max_y}.png"
        output_path = os.path.join(OUTPUT_DIR, filename)
        
        print(f"Stitching {filename} ({width_px}x{height_px} px)...")
        canvas = Image.new('RGBA', (width_px, height_px), (0, 0, 0, 0))
        
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
                    
        canvas.save(output_path)
        print(f"Saved to {output_path}")

if __name__ == "__main__":
    with open(LOG_FILE, "w") as f:
        f.write(f"--- Tile Scan Started ---\n")
    setup_directories()
    
    dates = generate_date_list(2025, 12, 2015, 1)
    
    tiles_to_check = (
        (x, y, dates) 
        for x in range(X_START, X_END) 
        for y in range(Y_START, Y_END)
    )
    
    total_tiles = (X_END - X_START) * (Y_END - Y_START)
    print(f"Checking {total_tiles:,} coordinates concurrently...")
    print(f"Results will be saved in real-time to '{LOG_FILE}'\n")

    # Step 1: Locate Images
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = executor.map(find_latest_tile, tiles_to_check)
        for result in results:
            pass 
                
    print(f"\nFinished scanning. Check '{LOG_FILE}' for successful URLs.")
    
    tiles = parse_urls_from_log()
    print(f"Found {len(tiles)} tiles in log file.")
    
    # Step 2: Download Images
    print("\nStarting downloads...")
    valid_tiles = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = executor.map(download_tile, tiles)
        for result in results:
            if result:
                valid_tiles.append(result)
                
    # Step 3: Group and Stitch
    if valid_tiles:
        stitch_in_chunks(valid_tiles)
        print("\nAll chunking and stitching complete!")
