import pickle
from pathlib import Path

import numpy as np
import pytest

from labctl.analysis import get_data as get_data_module

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

    with pytest.raises(ValueError, match="variable"):
        get_data_module.get_data(str(REAL_SIF), pickle_loc)


def test_get_data_raises_with_mismatched_n_frames_without_accumulator():
    """Real data has n_frames=[10, 5]; omitting an accumulator must raise ValueError."""
    with pytest.raises(ValueError, match="same number of frames"):
        get_data_module.get_data(str(REAL_SIF), str(REAL_PKL), iter_accumulator=None)


@pytest.mark.parametrize("bad_accumulator", ["max", 3.14])
def test_get_data_rejects_invalid_iter_accumulator(bad_accumulator):
    """Unsupported accumulator values must raise ValueError."""
    with pytest.raises(ValueError):
        get_data_module.get_data(str(REAL_SIF), str(REAL_PKL), iter_accumulator=bad_accumulator)


@pytest.mark.parametrize("accumulator", ["mean", "sum", "median"])
def test_get_data_with_string_accumulator_returns_correct_shapes(accumulator):
    """
    Each string accumulator collapses the frame axis and returns two arrays.

    With n_iter=1 and 2 polarisation configs, the shape is (n_configs, height, width)
    = (2, 1024, 1024) for signal and background.
    """
    data, background = get_data_module.get_data(
        str(REAL_SIF), str(REAL_PKL), iter_accumulator=accumulator
    )
    assert data.shape == (2, 1024, 1024), f"Expected (2, 1024, 1024), got {data.shape}"
    assert background is not None
    assert background.shape == (2, 1024, 1024)


def test_get_data_2d_collapses_height_axis_with_real_data():
    """get_data_2D should collapse height and keep config x width for both signal and background."""
    data_2d, background_2d = get_data_module.get_data_2D(
        str(REAL_SIF), str(REAL_PKL), iter_accumulator="mean"
    )

    assert data_2d.shape == (2, 1024)
    assert background_2d is not None
    assert background_2d.shape == (2, 1024)


def test_get_data_with_asymmetric_crop_sizes_returns_expected_shape():
    """Cropping with different height/width extents should preserve axis ordering."""
    data, background = get_data_module.get_data(
        str(REAL_SIF),
        str(REAL_PKL),
        iter_accumulator="mean",
        width_indexes=(100, 300),
        height_indexes=(10, 60),
    )

    # height span = 50, width span = 200
    assert data.shape == (2, 50, 200)
    assert background is not None
    assert background.shape == (2, 50, 200)


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
        get_data_module.get_data(
            str(REAL_SIF),
            str(REAL_PKL),
            iter_accumulator="mean",
            **kwargs,
        )


def test_get_data_accepts_custom_callable_iter_accumulator():
    """A user-provided accumulator callable should be accepted and applied per config."""
    data, background = get_data_module.get_data(
        str(REAL_SIF),
        str(REAL_PKL),
        iter_accumulator=lambda x: np.max(x, axis=-3),
    )

    assert data.shape == (2, 1024, 1024)
    assert background is not None
    assert background.shape == (2, 1024, 1024)


def test_get_wavelengths_full_and_crop_are_consistent():
    """Cropped wavelengths should match slicing the full calibration array."""
    full = get_data_module.get_wavelengths(str(REAL_SIF))
    cropped = get_data_module.get_wavelengths(str(REAL_SIF), width_indexes=(100, 300))

    assert full.shape == (1024,)
    assert cropped.shape == (200,)
    assert np.all(np.isfinite(full))
    np.testing.assert_allclose(cropped, full[100:300])

