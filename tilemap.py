import itertools
import time
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from math import log, tan, pi, cos, ceil, floor, atan, sinh

import requests
from PIL import Image


def lon_to_x(lon: float, zoom: int) -> float:
    """
    Longitude to x tile
    :param lon:
    :param zoom:
    :return:
    """
    if not (-180 <= lon <= 180):
        lon = (lon + 180) % 360 - 180

    return ((lon + 180.0) / 360) * pow(2, zoom)


def lat_to_y(lat: float, zoom: int) -> float:
    """
    Latitude to y tile
    :param lat: latitude
    :param zoom:
    :return:
    """
    if not (-90 <= lat <= 90):
        lat = (lat + 90) % 180 - 90

    return (
        (1 - log(tan(lat * pi / 180) + 1 / cos(lat * pi / 180)) / pi) / 2 * pow(2, zoom)
    )


def _y_to_lat(y, zoom):
    """

    :param y:
    :param zoom:
    :return:
    """
    return atan(sinh(pi * (1 - 2 * y / pow(2, zoom)))) / pi * 180


def _x_to_lon(x, zoom):
    """

    :param x:
    :param zoom:
    :return:
    """
    return x / pow(2, zoom) * 360.0 - 180.0


class TileMap:
    def __init__(
        self,
        extents,
        # url_template="https://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}",
        # url_template="https://mt0.google.com/vt/lyrs=m&hl=en&x={x}&y={y}&z={z}",

        # url_template="https://mt1.google.com/vt/lyrs=t&x={x}&y={y}&z={z}", # Terrain
        # url_template="https://mt1.google.com/vt/lyrs=y&x={x}&y={y}&z={z}",  # Satellite Hybrid
        # url_template="https://mt0.google.com/vt/lyrs=s&hl=en&x={x}&y={y}&z={z}", # Satellite
        url_template="http://mt0.google.com/vt/lyrs=m&hl=en&x={x}&y={y}&z={z}&s=Gal&apistyle=s.t%3A0|s.e%3Al|p.v%3Aoff",

        # url_template="https://a.tile.opentopomap.org/{z}/{x}/{y}.png",
        # url_template="http://gsp2.apple.com/tile?api=1&style=slideshow&layers=default&lang=en_En&z={z}&x={x}&y={y}&v=9",
        tile_size=256,
        tile_request_timeout=None,
        headers=None,
        reverse_y=False,
        background_color="#fff",
        delay_between_retries=0,
    ):
        """
        :param url_template: tile URL
        :type url_template: str
        :param tile_size: the size of the map tiles in pixel
        :type tile_size: int
        :param tile_request_timeout: time in seconds to wait for requesting map tiles
        :type tile_request_timeout: float
        :param headers: additional headers to add to http requests
        :type headers: dict
        :param reverse_y: tile source has TMS y origin
        :type reverse_y: bool
        :param background_color: Image background color, only visible when tiles are transparent
        :type background_color: str
        :param delay_between_retries: number of seconds to wait between retries of map tile requests
        :type delay_between_retries: int
        """
        self.extents = extents
        self.url_template = url_template
        self.headers = headers
        self.tile_size = tile_size
        self.request_timeout = tile_request_timeout
        self.reverse_y = reverse_y
        self.background_color = background_color

        # fields that get set when map is rendered
        self.x_center = 0
        self.y_center = 0
        self.zoom = 0

        self.delay_between_retries = delay_between_retries

    def render(self, zoom=None):
        """

        :param zoom:
        :return:
        """

        self.zoom = zoom

        # calculate center point of map
        lon_center, lat_center = (
            (self.extents[0] + self.extents[2]) / 2,
            (self.extents[1] + self.extents[3]) / 2,
        )
        self.x_center = lon_to_x(lon_center, self.zoom)
        self.y_center = lat_to_y(lat_center, self.zoom)

        image = self._draw_base_layer()

        return image

    def _x_to_px(self, x):
        """
        transform tile number to pixel on image canvas
        :param x:
        :return:
        """
        px = (x - self.x_center) * self.tile_size + self.width / 2
        return int(round(px))

    def _y_to_px(self, y):
        """
        transform tile number to pixel on image canvas
        :param y:
        :return:
        """
        px = (y - self.y_center) * self.tile_size + self.height / 2
        return int(round(px))

    def _draw_base_layer(self) -> Image:
        """
        :return: PIL Image
        """
        self.width = ceil(
            (
                lon_to_x(self.extents[2], self.zoom)
                - lon_to_x(self.extents[0], self.zoom)
            )
            * self.tile_size
        )
        self.height = ceil(
            (
                lat_to_y(self.extents[1], self.zoom)
                - lat_to_y(self.extents[3], self.zoom)
            )
            * self.tile_size
        )

        image = Image.new("RGB", (self.width, self.height), self.background_color)

        x_min = int(floor(self.x_center - (0.5 * self.width / self.tile_size)))
        x_max = int(ceil(self.x_center + (0.5 * self.width / self.tile_size)))
        y_min = int(floor(self.y_center - (0.5 * self.height / self.tile_size)))
        y_max = int(ceil(self.y_center + (0.5 * self.height / self.tile_size)))

        # assemble all map tiles needed for the map
        tiles = []
        for x in range(x_min, x_max):
            for y in range(y_min, y_max):
                # x and y may have crossed the date line
                max_tile = 2 ** self.zoom
                tile_x = (x + max_tile) % max_tile
                tile_y = (y + max_tile) % max_tile

                if self.reverse_y:
                    tile_y = ((1 << self.zoom) - tile_y) - 1

                url = self.url_template.format(z=self.zoom, x=tile_x, y=tile_y)
                tiles.append((x, y, url))

        thread_pool = ThreadPoolExecutor(4)

        for nb_retry in itertools.count():
            if not tiles:
                # no tiles left
                break

            if nb_retry > 0 and self.delay_between_retries:
                # to avoid stressing the map tile server to much, wait some seconds
                time.sleep(self.delay_between_retries)

            if nb_retry >= 3:
                # maximum number of retries exceeded
                raise RuntimeError(
                    "could not download {} tiles: {}".format(len(tiles), tiles)
                )

            failed_tiles = []

            futures = [
                thread_pool.submit(
                    requests.get,
                    tile[2],
                    timeout=self.request_timeout,
                    headers=self.headers,
                )
                for tile in tiles
            ]

            for tile, future in zip(tiles, futures):
                x, y, url = tile

                try:
                    response = future.result()
                except:
                    response = None

                if not response or response.status_code != 200:
                    print(
                        "request failed [{}]: {}".format(
                            response.status_code if response else "?", url
                        )
                    )
                    failed_tiles.append(tile)
                    continue

                tile_image = Image.open(BytesIO(response.content)).convert("RGBA")
                box = [
                    self._x_to_px(x),
                    self._y_to_px(y),
                    self._x_to_px(x + 1),
                    self._y_to_px(y + 1),
                ]
                image.paste(tile_image, box, tile_image)

            # put failed back into list of tiles to fetch in next try
            tiles = failed_tiles

        return image


if __name__ == "__main__":
    render_map = TileMap(extents=(115.7410072222, -32.0661730556, 116.0174188889, -31.8985416667))
    map_image = render_map.render(zoom=13)
    map_image.save("perth_map.png")
