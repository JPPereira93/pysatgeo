"""
Google Earth Engine helpers for pysatgeo.
"""

def addNDVI_ee(image):
    ndvi = image.normalizedDifference(['B8', 'B4']).rename('ndvi')
    return image.addBands(ndvi)

def apply_cloud_masks_ee(image):
    # Cloud shadow 
    cloud_shadow = image.select('SCL').eq(3)
    # Medium Probability
    cloud_low = image.select('SCL').eq(7)
    # Medium Probability
    cloud_med = image.select('SCL').eq(8)
    # High Probability
    cloud_high = image.select('SCL').eq(9)
    # Cirrus Mask
    cloud_cirrus = image.select('SCL').eq(10)
    cloud_mask = cloud_shadow.add(cloud_low).add(cloud_med).add(cloud_high).add(cloud_cirrus)

    # Invert the selected images to mask out the clouds
    invert_mask = cloud_mask.eq(0)

    # Apply the mask to the image
    return image.updateMask(invert_mask)

def apply_scale_factor_ee(image):
    return image.multiply(0.0001)


def split_region(geometry, n):
    tiles = []
    bounds = geometry.bounds().getInfo()["coordinates"][0]
    x_min, y_min = bounds[0]
    x_max, y_max = bounds[2]
    width = x_max - x_min
    height = y_max - y_min
    tile_width = width / n
    tile_height = height / n
    for i in range(n):
        for j in range(n):
            x1 = x_min + i * tile_width
            y1 = y_min + j * tile_height
            x2 = x1 + tile_width
            y2 = y1 + tile_height
            tiles.append(ee.Geometry.Rectangle([x1, y1, x2, y2]))
    return tiles