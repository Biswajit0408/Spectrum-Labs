import os
from typing import List

import numpy as np
from PIL import Image
from sklearn.cluster import KMeans


def rgb_to_hex(color: np.ndarray) -> str:
    r, g, b = [max(0, min(255, int(x))) for x in color]
    return "#{:02x}{:02x}{:02x}".format(r, g, b)


def brightness(rgb: np.ndarray) -> float:
    """
    Calculate perceived brightness of an RGB color.
    Formula based on human eye sensitivity.
    """
    r, g, b = rgb
    return 0.299 * r + 0.587 * g + 0.114 * b

def luminance(rgb):
    """Relative luminance for contrast calculation"""
    def channel(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast_ratio(rgb1, rgb2):
    """WCAG contrast ratio between two colors"""
    l1 = luminance(rgb1)
    l2 = luminance(rgb2)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)
def assign_color_roles(colors_rgb):
    """
    Assign roles to colors based on brightness and contrast.
    Expects colors sorted dark → light.
    """
    roles = {}

    roles["text"] = colors_rgb[0]
    roles["background"] = colors_rgb[-1]

    # Primary = middle color
    mid_index = len(colors_rgb) // 2
    roles["primary"] = colors_rgb[mid_index]

    # Accent = highest contrast with background
    remaining = [
        c for i, c in enumerate(colors_rgb)
        if i not in (0, mid_index, len(colors_rgb) - 1)
    ]

    if remaining:
        accent = max(
            remaining,
            key=lambda c: contrast_ratio(c, roles["background"])
        )
        roles["accent"] = accent
    else:
        roles["accent"] = roles["primary"]

    return roles
def wcag_result(rgb1, rgb2):
    ratio = contrast_ratio(rgb1, rgb2)
    if ratio >= 7:
        level = "AAA"
    elif ratio >= 4.5:
        level = "AA"
    else:
        level = "Fail"

    return round(ratio, 2), level




def extract_palette(image_path: str, n_colors: int = 5):
    img = Image.open(image_path).convert("RGB")
    img = img.resize((200, 200))
    pixels = np.array(img).reshape(-1, 3)

    kmeans = KMeans(n_clusters=n_colors, n_init=5, random_state=42)
    kmeans.fit(pixels)

    centers = sorted(
        kmeans.cluster_centers_,
        key=lambda c: brightness(c)
    )

    rgb_colors = [tuple(int(x) for x in c) for c in centers]
    hex_colors = [rgb_to_hex(c) for c in rgb_colors]

    return rgb_colors, hex_colors



def create_palette_image(colors: List[str], width: int = 600, height: int = 100) -> Image.Image:
    """
    Create an image strip showing the given colors.

    :param colors: List of HEX color strings.
    :param width: Width of the output image.
    :param height: Height of the output image.
    :return: PIL Image object.
    """
    n = len(colors)
    if n == 0:
        raise ValueError("No colors provided to create a palette image.")

    # Width of each color block
    block_width = width // n

    palette_img = Image.new("RGB", (width, height))

    for i, hex_color in enumerate(colors):
        # Convert hex to RGB tuple
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)

        # Draw a block of this color
        for x in range(i * block_width, (i + 1) * block_width):
            for y in range(height):
                palette_img.putpixel((x, y), (r, g, b))

    return palette_img