import math
import pickle
from pathlib import Path

import numpy as np
import pytest

from labctl.analysis import read_data as read_data_module

# ---------------------------------------------------------------------------
# Paths to real test data
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).parent.parent / "data"
REAL_SIF = DATA_DIR / "S3_646_673.sif"
REAL_PKL = DATA_DIR / "S3.pkl"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_info_pickle(tmp_path, info: dict) -> str:
    pickle_path = tmp_path / "info.pkl"
    with open(pickle_path, "wb") as f:
        pickle.dump(info, f)
    return str(pickle_path)


def _load_real_info() -> dict:
    """Return a copy of the metadata stored in S3.pkl."""
    with open(REAL_PKL, "rb") as f:
        return pickle.load(f)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_get_data_raises_when_variable_key_is_missing(tmp_path):
    """Removing 'variable' from the metadata must raise ValueError."""
    info = _load_real_info()
    del info["variable"]
    pickle_loc = _write_info_pickle(tmp_path, info)

    msg = "When no accumulator function is used, all configurations must have the same number of frames. Found "
    with pytest.raises(ValueError, match=msg):
        read_data_module.get_data(str(REAL_SIF), pickle_loc)


def test_get_data_raises_with_mismatched_n_frames_without_accumulator():
    """Real data has n_frames=[10, 5]; omitting an accumulator must raise ValueError."""
    with pytest.raises(ValueError, match="same number of frames"):
        read_data_module.get_data(str(REAL_SIF), str(REAL_PKL), config_flattener=None)


@pytest.mark.parametrize("bad_accumulator", ["max", math.pi])
def test_get_data_rejects_invalid_config_flattener(bad_accumulator):
    """Unsupported accumulator values must raise ValueError."""
    with pytest.raises(ValueError):
        read_data_module.get_data(str(REAL_SIF), str(REAL_PKL), config_flattener=bad_accumulator)


@pytest.mark.parametrize("accumulator", ["mean", "sum", "median"])
def test_get_data_with_string_accumulator_returns_correct_shapes(accumulator):
    """
    Each string accumulator collapses the frame axis and returns two arrays.

    With n_iter=1 and 2 polarisation configs, the shape is (n_configs, height, width)
    = (2, 1024, 1024) for signal and background.
    """
    measurement = read_data_module.get_data(
        str(REAL_SIF), str(REAL_PKL), config_flattener=accumulator
    )
    assert measurement.intensity.shape == (2, 1024, 1024), f"Expected (2, 1024, 1024), got {measurement.intensity.shape}"
    assert measurement.has_background
    assert measurement.background.shape == (2, 1024, 1024)


def test_get_data_with_asymmetric_crop_sizes_returns_expected_shape():
    """Cropping with different height/width extents should preserve axis ordering."""
    measurement = read_data_module.get_data(
        str(REAL_SIF),
        str(REAL_PKL),
        config_flattener="mean",
        width_indexes=(100, 300),
        height_indexes=(10, 60),
    )

    # height span = 50, width span = 200
    assert measurement.intensity.shape == (2, 50, 200)
    assert measurement.has_background
    assert measurement.background.shape == (2, 50, 200)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"width_indexes": (200, 100)},
        {"width_indexes": (-1, 100)},
        {"width_indexes": (0, 2000)},
        {"height_indexes": (100, 50)},
        {"height_indexes": (-5, 100)},
        {"height_indexes": (0, 2000)},
    ],
)
def test_get_data_rejects_invalid_crop_ranges(kwargs):
    """Invalid crop ranges should raise ValueError."""
    with pytest.raises(ValueError):
        read_data_module.get_data(
            str(REAL_SIF),
            str(REAL_PKL),
            config_flattener="mean",
            **kwargs,
        )


def test_get_data_accepts_custom_callable_config_flattener():
    """A user-provided accumulator callable should be accepted and applied per config."""
    measurement = read_data_module.get_data(
        str(REAL_SIF),
        str(REAL_PKL),
        config_flattener=lambda x: np.max(x, axis=-3),
    )

    assert measurement.intensity.shape == (2, 1024, 1024)
    assert measurement.has_background
    assert measurement.background.shape == (2, 1024, 1024)


# def test_get_wavelengths_full_and_crop_are_consistent():
#     """Cropped wavelengths should match slicing the full calibration array."""
#     full = read_data_module.get_wavelengths(str(REAL_SIF))
#     cropped = read_data_module.get_wavelengths(str(REAL_SIF), width_indexes=(100, 300))
#
#     assert full.shape == (1024,)
#     assert cropped.shape == (200,)
#     assert np.all(np.isfinite(full))
#     np.testing.assert_allclose(cropped, full[100:300])

