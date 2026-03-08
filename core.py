"""
MapMole Core — raster change detection engine.

Provides functions to read GeoTIFF rasters, align them, compute pixel-wise
difference maps, and produce binary change masks with adjustable thresholds.
"""

import numpy as np
import rasterio
from rasterio.enums import Resampling


def read_raster(file_path):
    """Read a single-band raster and return (data, profile)."""
    with rasterio.open(file_path) as src:
        data = src.read(1).astype(np.float64)
        profile = src.profile.copy()
    return data, profile


def resample_raster(source_path, target_shape):
    """Re-read a raster resampled to *target_shape* using bilinear interpolation."""
    height, width = target_shape
    with rasterio.open(source_path) as src:
        data = src.read(
            1,
            out_shape=(height, width),
            resampling=Resampling.bilinear,
        ).astype(np.float64)
    return data


def calculate_difference(image1, image2):
    """Absolute pixel-wise difference between two arrays."""
    return np.abs(image1 - image2)


def enhance_contrast(diff_image, threshold_factor=0.75):
    """Normalise, log-stretch, and threshold a difference image.

    Returns a uint8 binary mask (0 or 255).
    """
    dmin, dmax = diff_image.min(), diff_image.max()
    if dmax - dmin == 0:
        return np.zeros_like(diff_image, dtype=np.uint8)

    normed = (diff_image - dmin) / (dmax - dmin) * 255.0
    log_stretched = np.log1p(normed)
    log_max = log_stretched.max()
    if log_max == 0:
        return np.zeros_like(diff_image, dtype=np.uint8)

    log_stretched = (log_stretched / log_max) * 255.0
    threshold = threshold_factor * log_stretched.max()
    return np.where(log_stretched > threshold, 255, 0).astype(np.uint8)


def save_raster(output_path, data, profile):
    """Write a single-band uint8 raster to *output_path*."""
    out_profile = profile.copy()
    out_profile.update(dtype=rasterio.uint8, count=1)
    with rasterio.open(output_path, "w", **out_profile) as dst:
        dst.write(data, 1)


def run_change_detection(image1_path, image2_path, threshold_factor=0.75):
    """Full pipeline: read → align → diff → threshold.

    Returns (image1, image2, change_map, profile).
    """
    image1, profile = read_raster(image1_path)
    image2, profile2 = read_raster(image2_path)

    if image1.shape != image2.shape:
        image2 = resample_raster(image2_path, image1.shape)

    diff = calculate_difference(image1, image2)
    change_map = enhance_contrast(diff, threshold_factor)
    return image1, image2, change_map, profile
