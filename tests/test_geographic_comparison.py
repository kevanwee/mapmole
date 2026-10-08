from pathlib import Path

import numpy as np
import pytest
import rasterio
from rasterio.transform import from_bounds, from_origin
from rasterio.warp import transform_bounds

from core import calculate_difference, enhance_contrast, run_change_detection, save_raster


def raster(tmp_path, name, values, *, transform=None, crs="EPSG:4326", nodata=None):
    values = np.asarray(values, dtype="float32")
    path = tmp_path / f"{name}.tif"
    with rasterio.open(
        path, "w", driver="GTiff", height=values.shape[0], width=values.shape[1],
        count=1, dtype="float32", crs=crs, nodata=nodata,
        transform=transform or from_origin(100, 5, 0.1, 0.1),
    ) as dst:
        dst.write(values, 1)
    return path


def test_non_overlapping_equal_size_rasters_are_rejected(tmp_path):
    a = raster(tmp_path, "a", np.ones((4, 4)))
    b = raster(tmp_path, "b", np.ones((4, 4)), transform=from_origin(120, 5, 0.1, 0.1))
    with pytest.raises(ValueError, match="no overlapping valid pixels"):
        run_change_detection(a, b)


def test_shifted_grid_compares_same_locations_and_masks_uncovered_pixels(tmp_path):
    a = raster(tmp_path, "a", [[10, 20, 30, 40], [10, 20, 30, 40]])
    b = raster(tmp_path, "b", [[20, 30, 40, 50], [20, 30, 40, 50]],
               transform=from_origin(100.1, 5, 0.1, 0.1))
    _, aligned, changes, _ = run_change_detection(a, b)
    assert changes.count() == 6
    assert changes.mask[:, 0].all()
    np.testing.assert_allclose(aligned[:, 1:], [[20, 30, 40], [20, 30, 40]])
    assert not np.count_nonzero(changes.filled(0))


def test_different_crs_is_reprojected_to_reference_grid(tmp_path):
    a = raster(tmp_path, "a", np.full((4, 4), 7))
    bounds = transform_bounds("EPSG:4326", "EPSG:3857", 100, 4.6, 100.4, 5)
    b = raster(tmp_path, "b", np.full((8, 8), 7), crs="EPSG:3857",
               transform=from_bounds(*bounds, width=8, height=8))
    _, aligned, changes, profile = run_change_detection(a, b)
    assert profile["crs"].to_epsg() == 4326
    assert aligned.shape == (4, 4)
    assert changes.count() == 16
    np.testing.assert_allclose(aligned, 7)
    assert not changes.any()


def test_nodata_nan_and_infinity_are_excluded_and_exported_as_internal_mask(tmp_path):
    a = raster(tmp_path, "a", [[1, -9999], [3, 4]], nodata=-9999)
    b = raster(tmp_path, "b", [[1, 2], [np.nan, np.inf]])
    _, _, changes, profile = run_change_detection(a, b)
    assert changes.count() == 1
    out = tmp_path / "changes.tif"
    save_raster(out, changes, profile)
    with rasterio.open(out) as src:
        result = src.read(1, masked=True)
        assert src.nodata is None
        assert src.crs == profile["crs"]
        assert src.transform == profile["transform"]
        assert result.count() == 1
        assert result[0, 0] == 0  # Valid zero must not be confused with nodata.
    assert not Path(str(out) + ".msk").exists()


def test_invalid_source_pixels_do_not_pollute_bilinear_interpolation(tmp_path):
    a = raster(tmp_path, "a", np.full((4, 4), 7))
    b = raster(tmp_path, "b", [[7, -9999], [7, 7]], nodata=-9999,
               transform=from_origin(100, 5, 0.2, 0.2))
    _, aligned, changes, _ = run_change_detection(a, b)
    assert 0 < changes.count() < changes.size
    np.testing.assert_allclose(aligned.compressed(), 7)
    assert not changes.any()


def test_all_invalid_overlap_is_rejected(tmp_path):
    a = raster(tmp_path, "a", [[1, 2]])
    b = raster(tmp_path, "b", [[-1, -1]], nodata=-1)
    with pytest.raises(ValueError, match="no overlapping valid pixels"):
        run_change_detection(a, b)


def test_missing_crs_is_rejected(tmp_path):
    a = raster(tmp_path, "a", [[1, 2]])
    b = raster(tmp_path, "b", [[1, 2]], crs=None)
    with pytest.raises(ValueError, match="CRS"):
        run_change_detection(a, b)


@pytest.mark.parametrize("threshold", [-0.1, 1.1, float("nan"), float("inf")])
def test_invalid_threshold(threshold):
    with pytest.raises(ValueError, match="Threshold"):
        enhance_contrast(np.ones((2, 2)), threshold)


def test_uniform_positive_difference_is_not_reported_as_unchanged():
    assert (enhance_contrast(np.full((2, 2), 5)) == 255).all()
    assert (enhance_contrast(np.zeros((2, 2))) == 0).all()


def test_bundled_pair_remains_usable():
    samples = Path(__file__).resolve().parents[1] / "samples"
    _, _, result, _ = run_change_detection(
        samples / "tuas_2018-01-21_nir.tif", samples / "tuas_2025-12-05_nir.tif",
    )
    assert result.count() > 0
    assert np.isin(result.compressed(), [0, 255]).all()


def test_meaningful_small_differences_remain_detectable():
    before = np.ma.array([[1.0, 1e-9]])
    after = before + 1e-6
    assert (enhance_contrast(calculate_difference(before, after)) == 255).all()
