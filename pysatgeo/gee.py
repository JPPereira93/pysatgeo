"""Google Earth Engine utilities."""


def split_region(geometry, n):
    """Split an Earth Engine geometry into an `n x n` grid of rectangles."""
    import ee

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


def addNDVI_ee(image):
    """Add an NDVI band to a Sentinel-2 Earth Engine image."""
    ndvi = image.normalizedDifference(["B8", "B4"]).rename("ndvi")
    return image.addBands(ndvi)


def apply_cloud_masks_ee(image):
    """Mask common cloudy Sentinel-2 scene classes using the SCL band."""
    cloud_shadow = image.select("SCL").eq(3)
    cloud_low = image.select("SCL").eq(7)
    cloud_med = image.select("SCL").eq(8)
    cloud_high = image.select("SCL").eq(9)
    cloud_cirrus = image.select("SCL").eq(10)
    cloud_mask = (
        cloud_shadow.add(cloud_low)
        .add(cloud_med)
        .add(cloud_high)
        .add(cloud_cirrus)
    )
    return image.updateMask(cloud_mask.eq(0))


def apply_scale_factor_ee(image):
    """Apply the common Sentinel reflectance scale factor."""
    return image.multiply(0.0001)


def export_tiled_mosaic(
    image,
    aoi,
    out_file,
    scale=500,
    crs="EPSG:4326",
    n=2,
    tmp_dir="tiles_tmp",
    max_attempts=5,
):
    """Export an Earth Engine image in tiles and merge them into one raster."""
    import os

    import ee
    import geemap
    import rasterio
    from rasterio.merge import merge

    attempt = 0
    success = False

    while attempt < max_attempts and not success:
        try:
            os.makedirs(tmp_dir, exist_ok=True)

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
                    tile_number = i * n + j + 1
                    print(
                        f"Exporting tile {tile_number} of {total_tiles} "
                        f"(n={n}) -> {tile_out}"
                    )

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

            print("Merging tiles into final mosaic...")
            src_files = [rasterio.open(path) for path in tile_files]
            mosaic, out_transform = merge(src_files, nodata=0)

            out_meta = src_files[0].meta.copy()
            out_meta.update(
                {
                    "driver": "GTiff",
                    "height": mosaic.shape[1],
                    "width": mosaic.shape[2],
                    "transform": out_transform,
                    "nodata": 0,
                }
            )

            with rasterio.open(out_file, "w", **out_meta) as dest:
                dest.write(mosaic)

            for src in src_files:
                src.close()

            print(f"Mosaic saved at: {out_file}")
            success = True

        except Exception as exc:
            attempt += 1
            print(f"Export failed at n={n} (attempt {attempt}/{max_attempts})")
            print(f"Error: {exc}")
            n += 1
            print(f"Retrying with n={n}...\n")

    if not success:
        raise RuntimeError("Export failed after maximum attempts.")
