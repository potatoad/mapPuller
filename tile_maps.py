from typing import Final
import codecs
from dataclasses import dataclass

URL_1: Final[str] = codecs.decode("gvyrf.yrvfher.zncf.bfvasen.arg", "rot13")
URL_2: Final[str] = codecs.decode("zncfrevrf-gvyrfrgf.f3.nznmbanjf.pbz", "rot13")
URL_3: Final[str] = codecs.decode("ncv.zncgvyre.pbz", "rot13")
URL_4: Final[str] = codecs.decode("trb.ayf.hx", "rot13")


@dataclass
class TileMap:
    name: str
    url: str
    min_zoom: int
    max_zoom: int


os25k = TileMap(
    name="OS 1:25k",
    url=f"https://{URL_1}/2025-12/1_25k/{{z}}/{{x}}/{{y}}.png",
    min_zoom=13,
    max_zoom=16,
)

os50k = TileMap(
    name="OS 1:50k",
    url=f"https://{URL_1}/2025-12/1_50k/{{z}}/{{x}}/{{y}}.png",
    min_zoom=13,
    max_zoom=16,
)

sixinch2nd = TileMap(
    name="6-inch Second Edition (6inch2nd)",
    url=f"https://{URL_2}/os/6inchsecond/{{z}}/{{x}}/{{y}}.png",
    min_zoom=4,
    max_zoom=16,
)

oneinch2nd = TileMap(
    name="1-inch Second Edition (1inch2nd)",
    url=f"https://{URL_2}/os/1inch_revised/{{z}}/{{x}}/{{y}}.png",
    min_zoom=4,
    max_zoom=16,
)

sixinch3rd = TileMap(
    name="1-inch Third Edition (1inch3rd)",
    url=f"https://{URL_2}/1inch_3rd_col_eng/{{z}}/{{x}}/{{y}}.png",
    min_zoom=4,
    max_zoom=16,
)

bart = TileMap(
    name="Bartholomew England (bart)",
    url=f"https://{URL_2}/bartholomew_england_wales_1920s/{{z}}/{{x}}/{{y}}.png",
    min_zoom=4,
    max_zoom=16,
)

os25k_1937_61 = TileMap(
    name="OS 1:25,000 (os25k-1937-61)",
    url=f"https://{URL_3}/tiles/uk-osgb25k1937/{{z}}/{{x}}/{{y}}.png",
    min_zoom=4,
    max_zoom=16,
)

os1in_1919_26 = TileMap(
    name="OS 1 inch (os1in-1919-26)",
    url=f"https://{URL_2}/os/popular-england/{{z}}/{{x}}/{{y}}.png",
    min_zoom=4,
    max_zoom=16,
)

os1in_1945_47 = TileMap(
    name="OS 1 inch (os1in-1945-47)",
    url=f"https://{URL_2}/os/newpopular/{{z}}/{{x}}/{{y}}.png",
    min_zoom=4,
    max_zoom=16,
)

agri_1960_70 = TileMap(
    name="Agriculture Land Use (agri-1960-70)",
    url=f"https://{URL_2}/one-inch-agricultural/{{z}}/{{x}}/{{y}}.png",
    min_zoom=4,
    max_zoom=16,
)

os50k_1974 = TileMap(
    name="OS 50,000 (os50k-1974)",
    url=f"https://{URL_4}/mapdata3/os/50000_1974/{{z}}/{{x}}/{{y}}.png",
    min_zoom=4,
    max_zoom=16,
)

tile_maps = [
    os25k,
    os50k,
    # sixinch2nd,
    # oneinch2nd,
    # sixinch3rd,
    # bart,
    # os25k_1937_61,
    # os1in_1919_26,
    # os1in_1945_47,
    # agri_1960_70,
]
