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


def export_tiled_mosaic(
    image,
    aoi,
    out_file,
    scale=500,
    crs="EPSG:4326",
    n=2,
    tmp_dir="tiles_tmp",
    max_attempts=5
):
    """
    Export a large Earth Engine image in tiles and merge them into a single raster.
    If export fails due to request size, n is automatically increased.
    """

    attempt = 0
    success = False

    while attempt < max_attempts and not success:
        try:
            os.makedirs(tmp_dir, exist_ok=True)

            # ---- Split region into tiles ----
            bounds = aoi.bounds().coordinates().getInfo()[0]
            x_min, y_min = bounds[0]
            x_max, y_max = bounds[2]
            width = x_max - x_min
            height = y_max - y_min
            tile_width = width / n
            tile_height = height / n

            tile_files = []
            total_tiles = n * n

            for i in range(n):
                for j in range(n):
                    x1 = x_min + i * tile_width
                    y1 = y_min + j * tile_height
                    x2 = x1 + tile_width
                    y2 = y1 + tile_height
                    tile_geom = ee.Geometry.Rectangle([x1, y1, x2, y2])

                    tile_out = os.path.join(tmp_dir, f"tile_{i}_{j}.tif")
                    print(f"Exporting tile {i*n + j + 1} of {total_tiles} (n={n}) -> {tile_out}")

                    geemap.ee_export_image(
                        image,
                        filename=tile_out,
                        scale=scale,
                        region=tile_geom,
                        crs=crs,
                        file_per_band=False,
                    )

                    with rasterio.open(tile_out, "r+") as dst:
                        dst.nodata = 0

                    tile_files.append(tile_out)

            # ---- Merge tiles ----
            print("Merging tiles into final mosaic...")
            src_files = [rasterio.open(f) for f in tile_files]
            mosaic, out_transform = merge(src_files, nodata=0)

            out_meta = src_files[0].meta.copy()
            out_meta.update({
                "driver": "GTiff",
                "height": mosaic.shape[1],
                "width": mosaic.shape[2],
                "transform": out_transform,
                "nodata": 0
            })

            with rasterio.open(out_file, "w", **out_meta) as dest:
                dest.write(mosaic)

            for src in src_files:
                src.close()

            print(f"Mosaic saved at: {out_file}")
            success = True

        except Exception as e:
            attempt += 1
            print(f"⚠️ Export failed at n={n} (attempt {attempt}/{max_attempts})")
            print(f"Error: {e}")
            n += 1  # increase tile split
            print(f"Retrying with n={n}...\n")

    if not success:
        raise RuntimeError("Export failed after maximum attempts.")