# mapPuller
A high-performance, concurrent Python script designed to scrape, download, and stitch map tiles from slippy map APIs (specifically configured for OS Leisure maps).

Instead of blindly downloading tiles, this script intelligently checks for a tile's existence using lightweight HTTP `HEAD` requests. If a tile is missing at the current date, it automatically searches backwards through historical data to find the most recent available version. Finally, it downloads the successful tiles and stitches them into manageable, high-resolution regional PNG chunks.

## Features

* **Smart Fallback:** Checks historical map dates (from present back to 2015) if a tile is missing.
* **Concurrent Processing:** Utilizes connection pooling and ThreadPoolExecutor to check and download hundreds of tiles per second.
* **Coordinate Support:** Target areas using explicit slippy map `X/Y` grids, or standard `Latitude/Longitude` with a tile radius.
* **Safe State Logging:** Successfully located tile URLs are logged to a text file in real-time. If the script crashes, you don't lose your scan progress.
* **Smart Chunking:** Stitches thousands of small 256x256 PNGs into large regional map chunks (e.g., 50x50 grids) to prevent memory overflow and computer crashes.
* **Transparent Backgrounds:** Missing tiles are rendered as transparent (`RGBA`) rather than solid blocks, preserving perfect geographical alignment (where applicable).
* **FIle Format Options:** Stitched images can be exported in PNG, JPEG, and lossless WebP formats.

## Prerequisites

You will need Python 3.7+ installed.
Install the required dependencies using pip:

```bash
pip install -r requirements.txt

```

## Usage

The script is entirely configurable via command-line arguments. You can run it using real-world coordinates (Latitude/Longitude) or by defining an explicit mathematical X/Y bounding box.

### Example 1: Target via Latitude and Longitude (Recommended)

Provide a central coordinate and a radius. The script will automatically calculate the bounding box.
*Example: Center on London, Zoom Level 16, grabbing 20 tiles in every direction.*

```bash
python map_scraper.py --lat 51.5074 --lon -0.1278 --zoom 16 --radius 20

```

### Example 2: Target via Explicit X/Y Grid

Manually define the exact slippy map coordinates you want to scrape.

```bash
python map_scraper.py --x-start 32000 --x-end 32050 --y-start 21000 --y-end 21050 --zoom 15

```

### Example 3: Performance Tuning

Increase the number of worker threads for faster downloading, and change the output image dimensions.

```bash
python map_scraper.py --lat 51.5074 --lon -0.1278 --max-workers 30 --chunk-size 100

```

---

## Command Line Arguments

| Argument | Type | Default | Description |
| --- | --- | --- | --- |
| `--zoom` | `int` | `15` | Map zoom level. Higher = closer. |
| `--scale` | `[25, 50]` | `25` | Map scale. Either 1:25,000 or 1:50,000. |
| `--lat` | `float` | `None` | Central Latitude coordinate (e.g., 51.5074). |
| `--lon` | `float` | `None` | Central Longitude coordinate (e.g., -0.1278). |
| `--radius` | `int` | `10` | If using Lat/Lon, how many tiles in each direction to fetch. |
| `--x-start` | `int` | `16183` | Starting X coordinate (used if Lat/Lon is omitted). |
| `--x-end` | `int` | `16196` | Ending X coordinate (exclusive). |
| `--y-start` | `int` | `10986` | Starting Y coordinate (used if Lat/Lon is omitted). |
| `--y-end` | `int` | `10999` | Ending Y coordinate (exclusive). |
| `--max-workers` | `int` | `15` | Number of concurrent threads. **Warning: See rate limits.** |
| `--chunk-size` | `int` | `50` | Grid size for stitched PNGs. (50 = 50x50 tiles per image). |
| `--log-file` | `string` | `successful_tile_urls.txt` | File path to log discovered URLs. |
| `--tile-dir` | `string` | `downloaded_tiles/` | Folder to save individual downloaded PNGs. |
| `--output-dir` | `string` | `stitched_chunks/` | Folder to save the final stitched PNG grids. |
| `--format` | `["png", "jpeg", "webp"]` | `png` | File format for the saved stitched image. |

---

## The Pipeline (How it Works)

1. **Scan & Log:** The script generates a queue of URLs. It pings the server using an HTTP `HEAD` request. If it receives a `200 OK`, it logs the URL to `--log-file` and stops checking that coordinate. If it receives a `404`, it checks the previous month.
2. **Download:** It reads the generated text log and downloads all valid URLs into the `--tile-dir` folder. Skips files that already exist on disk.
3. **Group & Stitch:** It mathematically groups the downloaded tiles into distinct grids (defined by `--chunk-size`). It stitches these smaller chunks together and saves them to the `--output-dir`.
4. **Cleanup:** It removes the log file.

---

## ⚠️ Important Warnings

### 1. Rate Limiting (HTTP Error 429)

Map tile servers are expensive to run. Hitting them with too many concurrent requests will trigger their automated defenses, resulting in your IP being temporarily or permanently banned.

* Monitor your console output. If you start seeing `[WARNING] Rate Limited (429)`, immediately stop the script and lower the `--max-workers` argument.
* Because the script features a 10-year historical fallback (checking ~132 months), querying an "empty" tile in the ocean will generate 132 back-to-back requests.

### 2. Physical Memory Constraints

Stitching thousands of map tiles together requires a massive amount of RAM. A 1,000 x 1,000 tile grid creates an image that is 256,000 x 256,000 pixels, requiring over 250 GB of RAM just to hold the blank canvas in memory.

* Do not set `--chunk-size` excessively high.
* The default `50` creates a 12,800 x 12,800 pixel image, requiring roughly 650 MB of RAM, which is safe for nearly all standard hardware.
