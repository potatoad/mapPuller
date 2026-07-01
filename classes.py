from dataclasses import dataclass

from nicegui import binding

from tile_maps import tile_maps


@binding.bindable_dataclass
class Tiles:
    def __init__(self, x_min: int = 0, x_max: int = 0, y_min: int = 0, y_max: int = 0):
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max

@dataclass
class AppState:
    lat: float = 0.0
    lon: float = 0.0
    zoom: int = 15
    url_pattern: str = tile_maps[0].url
    format: str = "png"
    tile_search_progress: float = 0.0
    tile_download_progress: float = 0.0
    tile_stitch_progress: float = 0.0
    status: str = ""
    filename: str = "output.png"