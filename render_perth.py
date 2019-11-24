import datashader as ds
from datashader.utils import export_image
import datashader.transfer_functions as tf
import pandas as pd
from colorcet import fire
from PIL import Image
from tilemap import TileMap

point_df = pd.read_parquet("point_data.gzip")
bounds = [1.288423e+07, 1.291500e+07, -3.772000e+06, -3.750000e+06]
filter_point_df = point_df[(point_df["x"] >= bounds[0]) & (point_df["x"] <= bounds[1]) & (point_df["y"] >= bounds[2]) & (point_df["y"] <= bounds[3])]
filter_point_desc_df = filter_point_df.describe()
aspect_ratio = (filter_point_desc_df.loc["max", "y"] - filter_point_desc_df.loc["min", "y"])/(filter_point_desc_df.loc["max", "x"] - filter_point_desc_df.loc["min", "x"])

dim = 2000
cvs = ds.Canvas(plot_width=dim, plot_height=int(dim * aspect_ratio))
agg = cvs.points(filter_point_df, 'x', 'y')
img = tf.shade(agg, cmap=fire)

figname = 'perth_wires'
export_image(img, figname, background="black")

render_map = TileMap(extents=(115.7410072222, -32.0661730556, 116.0174188889, -31.8985416667))
map_image = render_map.render(zoom=14)
map_image_resized = map_image.resize((2000, 1430), resample=Image.LANCZOS)
map_image_resized.putalpha(255)
map_image_resized.save("perth_street_map.png")