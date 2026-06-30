from typing import Final
import codecs

URL_1: Final[str] = codecs.decode("gvyrf.yrvfher.zncf.bfvasen.arg", "rot13")
URL_2: Final[str] = codecs.decode("zncfrevrf-gvyrfrgf.f3.nznmbanjf.pbz", "rot13")
URL_3: Final[str] = codecs.decode("ncv.zncgvyre.pbz", "rot13")
URL_4: Final[str] = codecs.decode("trb.ayf.hx", "rot13")


class TileMap:
    def __init__(self, name: str, url: str, min_zoom: int, max_zoom: int) -> None:
        self.name = name
        self.url = url
        self.min_zoom = min_zoom
        self.max_zoom = max_zoom

    def url(self):
        return self.url

    def min_zoom(self):
        return self.min_zoom

    def max_zoom(self):
        return self.max_zoom


os25k = TileMap('OS 1:25k',
                ('https://' + URL_1 + r'/2025-12/1_25k/{z}/{x}/{y}.png'),
                13,
                16)

os50k = TileMap('OS 1:50k',
                ('https://' + URL_1 + r'/2025-12/1_50k/{z}/{x}/{y}.png'),
                13,
                16)

sixinch2nd = TileMap('6-inch Second Edition (6inch2nd)',
                     ('https://' + URL_2 + r'/os/6inchsecond/{z}/{x}/{y}.png'),
                     4,
                     16)

oneinch2nd = TileMap('1-inch Second Edition (1inch2nd)',
                     ('https://' + URL_2 + r'/os/1inch_revised/{z}/{x}/{y}.png'),
                     4,
                     16)

sixinch3rd = TileMap('1-inch Third Edition (1inch3rd)',
                     ('https://' + URL_2 + r'/1inch_3rd_col_eng/{z}/{x}/{y}.png'),
                     4,
                     16)

bart = TileMap('Bartholomew England (bart)',
               ('https://' + URL_2 + r'/bartholomew_england_wales_1920s/{z}/{x}/{y}.png'),
               4,
               16)

os25k_1937_61 = TileMap('OS 1:25,000 (os25k-1937-61)',
                        ('https://' + URL_3 + r'/tiles/uk-osgb25k1937/{z}/{x}/{y}.png'),
                        4,
                        16)

os1in_1919_26 = TileMap('OS 1 inch (os1in-1919-26)',
                        ('https://' + URL_2 + r'/os/popular-england/{z}/{x}/{y}.png'),
                        4,
                        16)

os1in_1945_47 = TileMap('OS 1 inch (os1in-1945-47)',
                        ('https://' + URL_2 + r'/os/newpopular/{z}/{x}/{y}.png'),
                        4,
                        16)

agri_1960_70 = TileMap('Agriculture Land Use (agri-1960-70)',
                       ('https://' + URL_2 + r'/one-inch-agricultural/{z}/{x}/{y}.png'),
                       4,
                       16)

os50k_1974 = TileMap('OS 50,000 (os50k-1974)',
                     ('https://' + URL_4 + r'/mapdata3/os/50000_1974/{z}/{x}/{y}.png'),
                     4,
                     16)

tile_maps = [os25k, os50k, sixinch2nd, oneinch2nd, sixinch3rd, bart, os25k_1937_61, os1in_1919_26, os1in_1945_47,
             agri_1960_70]
