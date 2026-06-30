from nicegui import binding


class Zoom:
    def __init__(self):
        self.zoom: int = 16

@binding.bindable_dataclass
class Tiles:
    def __init__(self, x_min: int = 0, x_max: int = 0, y_min: int = 0, y_max: int = 0):
        self.x_min = x_min
        self.x_max = x_max
        self.y_min = y_min
        self.y_max = y_max