"""Helpers for parsing GIS style files."""

import xml.etree.ElementTree as ET


def parse_qml_colors(qml_file_path):
    """Parse QGIS QML raster colors into RGBA tuples."""
    tree = ET.parse(qml_file_path)
    root = tree.getroot()

    colors = []
    for item in root.findall(".//rastershader/colorrampshader/item"):
        color_hex = item.get("color")
        if color_hex:
            rgb = tuple(
                int(color_hex[i : i + 2], 16) / 255.0 for i in (1, 3, 5)
            ) + (1,)
            colors.append(rgb)

    return colors
