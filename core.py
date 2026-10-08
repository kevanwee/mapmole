"""Georeferenced first-band change detection on the first image's grid."""

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject


def read_raster(file_path):
    """Return masked, finite first-band data and its geographic profile."""
    with rasterio.open(file_path) as src:
        if src.crs is None:
            raise ValueError("Both images need a coordinate reference system (CRS).")
        data = np.ma.masked_invalid(src.read(1, masked=True).astype(np.float64))
        profile = src.profile.copy()
    return data, profile


def align_raster(data, source_profile, target_profile):
    """Reproject values onto the target grid; keep uncovered pixels invalid."""
    shape = (target_profile["height"], target_profile["width"])
    if (source_profile["crs"] == target_profile["crs"]
            and source_profile["transform"] == target_profile["transform"]
            and data.shape == shape):
        return data
    aligned = np.full(shape, np.nan, dtype=np.float64)
    reproject(
        source=data.filled(np.nan),
        destination=aligned,
        src_transform=source_profile["transform"],
        src_crs=source_profile["crs"],
        src_nodata=np.nan,
        dst_transform=target_profile["transform"],
        dst_crs=target_profile["crs"],
        dst_nodata=np.nan,
        resampling=Resampling.bilinear,
    )
    return np.ma.masked_invalid(aligned)


def calculate_difference(image1, image2):
    """Absolute difference over pixels valid in both aligned inputs."""
    difference = np.ma.masked_invalid(np.ma.abs(image1 - image2))
    # Reprojection introduces roundoff even for identical values. Do not stretch
    # that noise into a full-strength change signal.
    tolerance = 1e-12 * np.ma.maximum(np.ma.abs(image1), np.ma.abs(image2))
    return np.ma.where(difference <= tolerance, 0.0, difference)


def enhance_contrast(diff_image, threshold_factor=0.75):
    """Log-stretch differences into a masked 0/255 change map.

    Zero means unchanged; masked means not compared. Scaling from zero preserves
    constant positive differences instead of incorrectly returning no change.
    """
    if not np.isfinite(threshold_factor) or not 0 <= threshold_factor <= 1:
        raise ValueError("Threshold must be a finite number between 0 and 1.")
    diff = np.ma.masked_invalid(diff_image)
    if not diff.count():
        raise ValueError("The images have no overlapping valid pixels to compare.")
    maximum = diff.max()
    if maximum == 0:
        return np.ma.array(np.zeros(diff.shape, dtype=np.uint8), mask=np.ma.getmaskarray(diff))
    stretched = np.log1p(diff / maximum * 255.0)
    threshold = threshold_factor * stretched.max()
    return np.ma.where(stretched > threshold, 255, 0).astype(np.uint8)


def save_raster(output_path, data, profile):
    """Write values and a validity mask; zero is valid unchanged data, not nodata."""
    out_profile = profile.copy()
    out_profile.update(dtype=rasterio.uint8, count=1, nodata=None)
    # An internal mask travels with the downloaded TIFF, without a sidecar .msk.
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
        with rasterio.open(output_path, "w", **out_profile) as dst:
            dst.write(np.ma.filled(data, 0).astype(np.uint8), 1)
            dst.write_mask((~np.ma.getmaskarray(data)).astype(np.uint8) * 255)


def run_change_detection(image1_path, image2_path, threshold_factor=0.75):
    """Compare valid overlap on image 1's grid.

    Returns (image1, aligned_image2, masked_change_map, image1_profile).
    Raises ValueError for missing CRS, no valid overlap, or invalid thresholds.
    """
    image1, profile = read_raster(image1_path)
    image2, profile2 = read_raster(image2_path)
    image2 = align_raster(image2, profile2, profile)
    change_map = enhance_contrast(calculate_difference(image1, image2), threshold_factor)
    return image1, image2, change_map, profile
