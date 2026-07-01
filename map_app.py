from utils import (
    download_tile,
    draw_control,
    find_latest_tile,
    geocode_place,
    rect_coords_to_tiles,
    stitch_in_chunks,
    MAX_WORKERS,
    IMG_FORMATS,
)
import asyncio
import concurrent.futures
from pathlib import Path
from dotenv import load_dotenv
from nicegui import events, ui
from classes import AppState, Tiles
from tile_maps import tile_maps


load_dotenv()

tiles = Tiles()
state = AppState()


def handle_search():
    new_lat, new_lon = geocode_place(i.value)

    if new_lat and new_lon:
        global lat, lon
        lat, lon = new_lat, new_lon
        os_map.set_center((lat, lon))
    else:
        ui.notify("Location not found", type="warning")


def change_map(selected_map):
    os_map.clear_layers()
    state.url_pattern = selected_map.url

    os_map.tile_layer(
        url_template="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
        options={"maxZoom": 19, "attribution": "&copy; OpenStreetMap contributors"},
    )

    os_map.tile_layer(
        url_template=selected_map.url,
        options={"minZoom": selected_map.min_zoom, "maxZoom": selected_map.max_zoom,"attribution": "&copy; Ordnance Survey"},
    )


def change_format(selected_format):
    state.format = selected_format


def change_zoom(selected_zoom):
    state.zoom = selected_zoom


def handle_search_key(e: events.GenericEventArguments):
    if e.args["key"] == "Enter":
        handle_search()


def handle_rect(e: events.GenericEventArguments):
    coords = e.args["layer"].get("_latlng") or e.args["layer"].get("_latlngs")
    coords = coords[0]

    tiles.x_min, tiles.x_max, tiles.y_min, tiles.y_max = rect_coords_to_tiles(
        coords, state.zoom
    )

    # filename_coords = f"{e.args['layer']['_renderer']['_center']['lat']:.4f}_{e.args['layer']['_renderer']['_center']['lng']:.4f}"
    # state.filename = f"{filename_coords}.png"


async def handle_download():
    state.tile_search_progress = 0.0

    tiles_to_check = [
        (x, y)
        for x in range(tiles.x_min, tiles.x_max + 1)
        for y in range(tiles.y_min, tiles.y_max + 1)
    ]

    total_tiles = ((tiles.x_max - tiles.x_min) + 1) * ((tiles.y_max - tiles.y_min) + 1)

    print(total_tiles)

    increment = 1.0 / total_tiles if total_tiles > 0 else 1.0

    valid_urls = []

    tasks = [
        asyncio.to_thread(find_latest_tile, coords, state.zoom, current_url_pattern)
        for coords in tiles_to_check
    ]

    state.status = f"Searching for {len(tasks)} tiles..."

    for task in asyncio.as_completed(tasks):
        result = await task
        if result:
            valid_urls.append(result)

        state.tile_search_progress += increment

    state.status = f"Found {len(valid_urls)} available tiles."

    valid_tiles = []

    if valid_urls:
        state.status = f"Downloading {len(tasks)} tiles..."
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            results = executor.map(lambda tile: download_tile(tile), valid_urls)
            for result in results:
                if result:
                    valid_tiles.append(result)
                    state.tile_download_progress += increment

    state.status = f"Stitching {len(valid_tiles)} tiles together as a {state.format}"

    filename = f"{tile_map.name}-{state.lat}-{state.lon}.{state.format}"
    # Step 3: Group and Stitch
    if valid_tiles:
        stitch_in_chunks(valid_tiles, state.format, filename)

    print("\nAll tasks complete!")

    download_path = f"output/{filename}"
    download_path = Path(download_path)

    ui.download(download_path)


ui.page_title("MapApp")
ui.context.client.content.classes("p-0 flex-col !max-w-full h-[calc(100vh-58px)]")

lat: float = 54.154863
lon: float = -2.880168
place: str = ""
current_url_pattern: str = tile_maps[0].url
current_min_zoom: int = tile_maps[0].min_zoom
current_max_zoom: int = tile_maps[0].max_zoom

with ui.header().classes(replace="row items-center") as header:
    ui.button(on_click=lambda: left_drawer.toggle(), icon="menu").props(
        "flat color=white"
    )
    ui.button(
        text="Download", on_click=lambda: handle_download(), icon="download"
    ).props("flat color=white")

with ui.footer(value=False) as footer:
    ui.label("Footer")

with ui.left_drawer().classes("bg-blue-100") as left_drawer:
    ui.markdown("""
            # Map App
            A dodgy app to download OS maps you haven't paid for.
        """)

    with ui.dropdown_button("Select Map", auto_close=True):
        for tile_map in tile_maps:
            ui.item(tile_map.name, on_click=lambda tm=tile_map: change_map(tm))

    with ui.dropdown_button("Download format", auto_close=True):
        for img_format in IMG_FORMATS:
            ui.item(img_format, on_click=lambda f=img_format: change_format(f))

    with (
        ui.input(placeholder="Search...")
        .props("rounded outlined dense")
        .on("keydown", handle_search_key) as i
    ):
        ui.button(icon="search", on_click=handle_search).props("flat dense")

    ui.button("Download", on_click=handle_download).props("rounded outlined dense")

    ui.label().bind_text_from(state, "status")

os_map = ui.leaflet(center=(lat, lon), zoom=6, draw_control=draw_control)

os_map.classes("grow")
change_map(tile_maps[0])
os_map.on("draw:created", handle_rect)


# with ui.page_sticky(position="bottom-right", x_offset=20, y_offset=20):
#     ui.button(on_click=footer.toggle, icon="contact_support").props("fab")

# Progress bars remain at the bottom of the flex column
(
    ui.linear_progress(show_value=False, size="20px")
    .bind_value_from(state, "tile_search_progress")
    .bind_visibility_from(state, "tile_search_progress")
)
ui.linear_progress(show_value=False, size="20px").bind_value_from(
    state, "tile_download_progress"
).bind_visibility_from(state, "tile_download_progress")

ui.run()
