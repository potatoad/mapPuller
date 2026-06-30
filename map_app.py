import concurrent.futures
import os

from dotenv import load_dotenv
from nicegui import ui, events

from utils import geocode_place, rect_coords_to_tiles, setup_directories, LOG_FILE, parse_urls_from_log, MAX_WORKERS, \
    find_latest_tile, download_tile, stitch_in_chunks
from tile_maps import tile_maps, URL_2, os50k
from classes import Zoom, Tiles

load_dotenv()

zoom = Zoom()

tiles = Tiles()

draw_control = {
    'draw': {
        'polygon': False,
        'marker': False,
        'circle': False,
        'rectangle': True,
        'polyline': False,
        'circlemarker': False,
    },
    'edit': {
        'edit': True,
        'remove': True,
    },
}


def handle_search():
    new_lat, new_lon = geocode_place(i.value)

    if new_lat and new_lon:
        global lat, lon
        lat, lon = new_lat, new_lon
        os_map.set_center((lat, lon))
    else:
        ui.notify("Location not found", type='warning')


def handle_change_map(e):
    os_map.clear_layers()


def handle_search_key(e: events.GenericEventArguments):
    if e.args['key'] == 'Enter':
        handle_search()


def handle_rect(e: events.GenericEventArguments):
    coords = e.args['layer'].get('_latlng') or e.args['layer'].get('_latlngs')
    coords = coords[0]

    tiles.x_min, tiles.x_max, tiles.y_min, tiles.y_max = rect_coords_to_tiles(coords, zoom)

    print(tiles.x_min, tiles.x_max, tiles.y_min, tiles.y_max)


def handle_download():
    setup_directories()

    with open(LOG_FILE, "w") as f:
        f.write(f"--- Tile Scan Started ---\n")

    tiles_to_check = (
        (x, y)
        for x in range(tiles.x_min, tiles.x_max + 1)
        for y in range(tiles.y_min, tiles.y_max + 1)
    )

    total_tiles = (tiles.x_max - tiles.x_min) * (tiles.y_max - tiles.y_min)
    print(f"Checking {total_tiles:,} coordinates concurrently...")
    print(f"Results are saving in real-time to '{LOG_FILE}'\n")


    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = executor.map(find_latest_tile, tiles_to_check)
        for result in results:
            print(result)

    tiles_1 = parse_urls_from_log()
    print(f"\nFound {len(tiles_1)} available tiles.")

    # Step 2: Download Images (With Progress Bar)
    valid_tiles = []
    if tiles_1:
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            results = executor.map(download_tile, tiles_1)
            for result in results:
                if result:
                    valid_tiles.append(result)

    # Step 3: Group and Stitch
    if valid_tiles:
        stitch_in_chunks(valid_tiles)

    # --- NEW: Step 4: Cleanup ---
    print("\nCleaning up temporary files...")
    if os.path.exists(LOG_FILE):
        try:
            os.remove(LOG_FILE)
            print(f"Removed log file: {LOG_FILE}")
        except Exception as e:
            print(f"Could not remove {LOG_FILE}: {e}")

    print("\nAll tasks complete!")


ui.context.client.content.classes("h-screen")

lat: float = 53
lon: float = -1.5
place: str = ''

with ui.row():
    ui.markdown('''
        # Map App
        A dodgy app to download OS maps you haven't paid for.
    ''')

    with ui.column():
        with ui.dropdown_button('Select Map', auto_close=True):
            for tile_map in tile_maps:
                ui.item(tile_map.name, on_click=lambda tm=tile_map: (
                    os_map.clear_layers(),
                    print(tm.name),
                    os_map.tile_layer(
                        url_template=tm.url,
                        options={'minZoom': tm.min_zoom, 'maxZoom': tm.max_zoom}
                    )
                ))

        with ui.input(placeholder='Search...').props('rounded outlined dense').on('keydown', handle_search_key) as i:
            ui.button(icon='search', on_click=handle_search).props('flat dense')

        ui.slider(min=13, max=16).props('label-always').bind_value(zoom, 'zoom')

ui.button('Download', on_click=handle_download).props('rounded outlined dense')

os_map = ui.leaflet(center=(lat, lon), zoom=7, draw_control=draw_control).classes('grow')
os_map.clear_layers()
os_map.tile_layer(url_template=('https://' + URL_2 + r'/bartholomew_england_wales_1920s/{z}/{x}/{y}.png'),
                  options={'maxZoom': 16, 'minZoom': 7}, )

os_map.on('draw:created', handle_rect)

ui.run()
