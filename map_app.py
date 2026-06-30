import concurrent.futures
import os
import asyncio

from dotenv import load_dotenv
from nicegui import ui, events
from nicegui.functions.download import Download

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

    # print(tiles.x_min, tiles.x_max, tiles.y_min, tiles.y_max)


tile_search_progress: float = 0.0
tile_download_progress: float = 0.0
tile_stitch_progress: float = 0.0


async def handle_download():
    global tile_search_progress, tile_download_progress, tile_stitch_progress
    tile_search_progress = 0.0
    tile_download_progress = 0.0
    tile_stitch_progress = 0.0

    setup_directories()

    with open(LOG_FILE, "w") as f:
        f.write(f"--- Tile Scan Started ---\n")

    tiles_to_check = (
        (x, y)
        for x in range(tiles.x_min, tiles.x_max + 1)
        for y in range(tiles.y_min, tiles.y_max + 1)
    )

    total_tiles = ((tiles.x_max - tiles.x_min) + 1) * ((tiles.y_max - tiles.y_min) + 1)

    print(f"Checking {total_tiles:,} coordinates concurrently...")

    increment = 1.0 / total_tiles if total_tiles > 0 else 1.0

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(find_latest_tile, coords, zoom, current_url_pattern) for coords in tiles_to_check]

        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            print(f'Result: {result}')

            tile_search_progress += increment
            if tile_search_progress > 1.0:
                tile_search_progress = 1.0

            await asyncio.sleep(0.01)

    tile_search_progress = 0.0

    tiles_1 = parse_urls_from_log()
    print(f"\nFound {len(tiles_1)} available tiles.")

    valid_tiles = []
    if tiles_1:
        tile_download_progress = 0.0
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            futures = [executor.submit(download_tile, tile, zoom) for tile in tiles_1]

            for future in concurrent.futures.as_completed(futures):
                result = future.result()
                print(f'Result: {result}')

                tile_download_progress += increment
                if tile_download_progress > 1.0:
                    tile_download_progress = 1.0

                valid_tiles.append(result)
                await asyncio.sleep(0.01)

    tile_download_progress = 0.0

    if valid_tiles:
        stitch_in_chunks(valid_tiles)

    print("\nCleaning up temporary files...")
    if os.path.exists(LOG_FILE):
        try:
            os.remove(LOG_FILE)
            print(f"Removed log file: {LOG_FILE}")
        except Exception as e:
            print(f"Could not remove {LOG_FILE}: {e}")

    print("\nAll tasks complete!")

    download_path = f'output/filename.png'

    ui.download(download_path)



ui.page_title('MapApp')
ui.context.client.content.classes('p-0 flex-col !max-w-full h-[calc(100vh-58px)]')

lat: float = 53
lon: float = -1.5
place: str = ''
current_url_pattern: str = tile_maps[0].url
current_min_zoom: int = tile_maps[0].min_zoom
current_max_zoom: int = tile_maps[0].max_zoom

with ui.header().classes(replace='row items-center') as header:
    ui.button(on_click=lambda: left_drawer.toggle(), icon='menu').props('flat color=white')
    ui.button(text='Download', on_click=lambda: handle_download(), icon='download').props('flat color=white')

with ui.footer(value=False) as footer:
    ui.label('Footer')

with ui.left_drawer().classes('bg-blue-100') as left_drawer:
    ui.markdown('''
            # Map App
            A dodgy app to download OS maps you haven't paid for.
        ''')

    with ui.dropdown_button('Select Map', auto_close=True):
        for tile_map in tile_maps:
            ui.item(tile_map.name, on_click=lambda tm=tile_map: (
                os_map.clear_layers(),
                globals().update(current_url_pattern=tm.url),
                print(tm.name),
                os_map.tile_layer(
                    url_template=tm.url,
                    options={'minZoom': tm.min_zoom, 'maxZoom': tm.max_zoom}
                )
            ))

    with ui.input(placeholder='Search...').props('rounded outlined dense').on('keydown', handle_search_key) as i:
        ui.button(icon='search', on_click=handle_search).props('flat dense')

    ui.button('Download', on_click=handle_download).props('rounded outlined dense')

os_map = ui.leaflet(center=(lat, lon), zoom=10, draw_control=draw_control).classes('grow')
os_map.clear_layers()
os_map.tile_layer(url_template=(current_url_pattern),
                  options={'minZoom': current_min_zoom, 'maxZoom': current_max_zoom})
os_map.on('draw:created', handle_rect)


with ui.page_sticky(position='bottom-right', x_offset=20, y_offset=20):
    ui.button(on_click=footer.toggle, icon='contact_support').props('fab')

# Progress bars remain at the bottom of the flex column
(ui.linear_progress(show_value=False, size='20px').bind_value_from(globals(),
                                                                   'tile_search_progress').bind_visibility_from(
    globals(), 'tile_search_progress'))
ui.linear_progress(show_value=False, size='20px').bind_value_from(globals(),
                                                                  'tile_download_progress').bind_visibility_from(
    globals(), 'tile_download_progress')

ui.run()
