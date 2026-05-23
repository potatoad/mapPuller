# mapPuller
A high-performance, concurrent Python script designed to scrape, download, and stitch map tiles from slippy map APIs (specifically configured for OS Leisure maps).

Instead of blindly downloading tiles, this script intelligently checks for a tile's existence using lightweight HTTP `HEAD` requests. If a tile is missing at the current date, it automatically searches backwards through historical data to find the most recent available version. Finally, it downloads the successful tiles and stitches them into manageable, high-resolution regional PNG chunks.

## Features

* **Interactive Mode:** Run without arguments for a guided CLI setup experience, or use command-line arguments for scripting.
* **Multiple Map Series:** Choose from 11 different map series including modern OS maps, 1-inch historical editions, Bartholomew maps, agriculture maps, and more.
* **Smart Fallback:** For OS 1:25k and OS 1:50k series, checks historical map dates (from present back to 2015) if a tile is missing.
* **Concurrent Processing:** Utilizes connection pooling and ThreadPoolExecutor to check and download hundreds of tiles per second.
* **Coordinate Support:** Target areas using explicit slippy map `X/Y` grids, or standard `Latitude/Longitude` with a tile radius.
* **Safe State Logging:** Successfully located tile URLs are logged to a text file in real-time. If the script crashes, you don't lose your scan progress.
* **Smart Chunking:** Stitches thousands of small 256x256 PNGs into large regional map chunks (e.g., 50x50 grids) to prevent memory overflow and computer crashes.
* **Transparent Backgrounds:** Missing tiles are rendered as transparent (`RGBA`) rather than solid blocks, preserving perfect geographical alignment (where applicable).
* **File Format Options:** Stitched images can be exported in PNG, JPEG, and lossless WebP formats.

## Prerequisites

You will need Python 3.7+ installed.
Install the required dependencies using pip:

```bash
pip install -r requirements.txt

```

## Usage

### Interactive Mode (Recommended for New Users)

Run the script without any arguments to enter an interactive CLI menu that will guide you through all configuration options:

```bash
python3 mapPuller.py
```

This will prompt you to:
- Choose a map series (11 options including modern OS maps and historical editions)
- Select zoom level
- Specify the map area (Latitude/Longitude with radius, or X/Y coordinates)
- Choose output format (PNG, WebP, JPEG)
- Configure performance options

### Command-Line Mode (Advanced Users)

Alternatively, you can provide all arguments directly via the command line for scripting and automation.

### Example 1: Target via Latitude and Longitude (Recommended)

Provide a central coordinate and a radius. The script will automatically calculate the bounding box.
*Example: Center on Brighton, Zoom Level 16, grabbing 10 tiles in every direction with OS 1:25k maps.*

```bash
python3 mapPuller.py --series os25k --lat 50.82854 --lon -0.14001 --zoom 16 --radius 10

```

### Example 2: Target via Explicit X/Y Grid

Manually define the exact slippy map coordinates you want to scrape.

```bash
python3 mapPuller.py --series os50k --x-start 16354 --x-end 16374 --y-start 10977 --y-end 10997 --zoom 15

```

### Example 3: Using 6-inch Historical Maps

Download from historical map series:

```bash
# 6-inch Second Edition
python3 mapPuller.py --series 6inch2nd --lat 50.82854 --lon -0.14001 --zoom 16 --radius 15

# 1-inch Third Edition
python3 mapPuller.py --series 1inch3rd --lat 50.82854 --lon -0.14001 --zoom 16 --radius 15

# Agriculture Land Use (1960-70)
python3 mapPuller.py --series agri-1960-70 --lat 50.82854 --lon -0.14001 --zoom 16 --radius 15

```

### Example 4: Performance Tuning

Increase the number of worker threads for faster downloading, and change the output image dimensions.

```bash
python3 mapPuller.py --series os25k --lat 50.82854 --lon -0.14001 --max-workers 30 --chunk-size 100

```

---

## Available Map Series

| Series ID | Name | Type | Notes |
| --- | --- | --- | --- |
| `os25k` | OS 1:25,000 | Modern | Checks historical dates back to 2015 |
| `os50k` | OS 1:50,000 | Modern | Checks historical dates back to 2015 |
| `6inch2nd` | 6-inch Second Edition | Historical | Historical mapping, no date fallback |
| `1inch2nd` | 1-inch Second Edition (Revised) | Historical | Revised edition of 1-inch maps |
| `1inch3rd` | 1-inch Third Edition (Colored) | Historical | Colored 1-inch maps |
| `bart` | Bartholomew England & Wales (1920s) | Historical | Bartholomew publisher maps |
| `os25k-1937-61` | OS 1:25,000 (1937-1961) | Historical | Post-WWII OS maps |
| `os1in-1919-26` | OS 1-inch Popular Edition (1919-26) | Historical | Early 20th century OS maps |
| `os1in-1945-47` | OS 1-inch New Popular Edition (1945-47) | Historical | Post-WWII 1-inch OS maps |
| `agri-1960-70` | Agricultural Land Use (1960-70) | Historical | Agricultural classification maps |
| `os50k-1974` | OS 50,000 (1974) | Historical | 1974 OS 1:50,000 maps |

---

## Command Line Arguments

| Argument | Type | Default | Description |
| --- | --- | --- | --- |
| `--series` | `[os25k, os50k, 6inch2nd, 1inch2nd, 1inch3rd, bart, os25k-1937-61, os1in-1919-26, os1in-1945-47, agri-1960-70, os50k-1974]` | `os25k` | Map series to download. See "Available Map Series" table for details. Modern OS series check historical dates; historical series use direct URLs. |
| `--zoom` | `int` | `15` | Map zoom level. Higher = closer. |
| `--lat` | `float` | `None` | Central Latitude coordinate (e.g., 50.82854). |
| `--lon` | `float` | `None` | Central Longitude coordinate (e.g., -0.14001). |
| `--radius` | `int` | `10` | If using Lat/Lon, how many tiles in each direction to fetch. |
| `--x-start` | `int` | `16354` | Starting X coordinate (used if Lat/Lon is omitted). |
| `--x-end` | `int` | `16374` | Ending X coordinate (exclusive). |
| `--y-start` | `int` | `10977` | Starting Y coordinate (used if Lat/Lon is omitted). |
| `--y-end` | `int` | `10997` | Ending Y coordinate (exclusive). |
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
