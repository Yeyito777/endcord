# xterm256 color palette
# palette is a tuple of rgb values
# palette_short is palette without first 16 colors, used in pillow's putpalette
# colors is a tuple of tuples each containing rgb values, where index is 8bit ANSI color code

import re

system_colors = (
    (0, 0, 0),
    (128, 0, 0),
    (0, 128, 0),
    (128, 128, 0),
    (0, 0, 128),
    (128, 0, 128),
    (0, 128, 128),
    (192, 192, 192),
    (128, 128, 128),
    (255, 0, 0),
    (0, 255, 0),
    (255, 255, 0),
    (0, 0, 255),
    (255, 0, 255),
    (0, 255, 255),
    (255, 255, 255),
)

cube_steps = (0, 95, 135, 175, 215, 255)
hex_color = re.compile(r"^#?[0-9a-fA-F]{6}$")


def build_colors():
    """Build the complete xterm-256 palette, including grayscale ramp."""
    palette_colors = list(system_colors)
    for r in cube_steps:
        for g in cube_steps:
            for b in cube_steps:
                palette_colors.append((r, g, b))
    for gray in range(8, 239, 10):
        palette_colors.append((gray, gray, gray))
    return tuple(palette_colors)



def is_rgb_color(value):
    """Return True if value is exact RGB color specification."""
    if isinstance(value, str):
        return bool(hex_color.fullmatch(value.strip()))
    return (
        isinstance(value, (list, tuple)) and
        len(value) == 3 and
        all(isinstance(channel, int) and 0 <= channel <= 255 for channel in value)
    )



def parse_rgb_color(value):
    """Parse rgb tuple/list or #RRGGBB string into RGB tuple."""
    if isinstance(value, str):
        color_value = value.strip().lstrip("#")
        if not hex_color.fullmatch(value.strip()):
            raise ValueError(f"Invalid RGB color: {value}")
        return tuple(int(color_value[i:i+2], 16) for i in (0, 2, 4))
    if is_rgb_color(value):
        return tuple(value)
    raise ValueError(f"Invalid RGB color: {value}")


colors = build_colors()
palette = tuple(channel for color in colors for channel in color)
palette_short = palette[16*3:]
