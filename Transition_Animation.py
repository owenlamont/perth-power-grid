import numpy as np
from PIL import Image, ImageChops
from matplotlib.animation import FFMpegWriter
import matplotlib.pyplot as plt
from pathlib import Path

BACKGROUND_COLOUR = "#000000FF"
FRAME_RATE = 60

static_street_frames = FRAME_RATE
fade_to_background_frames = 5 * FRAME_RATE
static_wire_frames = FRAME_RATE
fade_to_foreground_frames = 5 * FRAME_RATE

fade_to_background_indices = np.linspace(1, 2001, fade_to_background_frames, dtype=np.int64)
fade_to_foreground_indices = np.linspace(1999, 0, fade_to_foreground_frames, dtype=np.int64)

background_img = Image.open(Path("./perth_wires.png"))
foreground_img = Image.open(Path("./perth_street_map.png"))

mask_array = np.ones((1430, 2000), dtype=np.uint8)*255
mask = Image.fromarray(mask_array)
composite_img = ImageChops.composite(foreground_img, background_img, mask)

figure = plt.figure(figsize=(20, 14.3))
file_writer = FFMpegWriter(fps=FRAME_RATE)
with file_writer.saving(figure, "perth_wires.mp4", dpi=100):
    render_axes = figure.add_axes([0.0, 0.0, 1.0, 1.0])
    render_axes.axis("off")
    render_axes.imshow(composite_img)
    for frame_number in range(static_street_frames):
        file_writer.grab_frame(facecolor=BACKGROUND_COLOUR)

    for frame_number in range(fade_to_background_frames):
        figure.clear()
        render_axes = figure.add_axes([0.0, 0.0, 1.0, 1.0])
        render_axes.axis("off")
        mask_array[:, :fade_to_background_indices[frame_number]] = 0
        mask = Image.fromarray(mask_array)
        composite_img = ImageChops.composite(foreground_img, background_img, mask)
        render_axes.imshow(composite_img)
        file_writer.grab_frame(facecolor=BACKGROUND_COLOUR)

    for frame_number in range(static_wire_frames):
        file_writer.grab_frame(facecolor=BACKGROUND_COLOUR)

    for frame_number in range(fade_to_foreground_frames):
        figure.clear()
        render_axes = figure.add_axes([0.0, 0.0, 1.0, 1.0])
        render_axes.axis("off")
        mask_array[:, fade_to_foreground_indices[frame_number]:] = 255
        mask = Image.fromarray(mask_array)
        composite_img = ImageChops.composite(foreground_img, background_img, mask)
        render_axes.imshow(composite_img)
        file_writer.grab_frame(facecolor=BACKGROUND_COLOUR)

    for frame_number in range(static_street_frames):
        file_writer.grab_frame(facecolor=BACKGROUND_COLOUR)
