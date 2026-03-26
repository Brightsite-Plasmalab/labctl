# TODO: Look at automatic generated tests

import pickle
import sys
import types

import numpy as np
import pytest

# Ensure module import works even if sif_parser is not installed in the test environment.
if "sif_parser" not in sys.modules:
    sif_parser_stub = types.ModuleType("sif_parser")
    sif_parser_stub.np_open = lambda _: (_ for _ in ()).throw(RuntimeError("np_open should be monkeypatched in tests"))
    sys.modules["sif_parser"] = sif_parser_stub

from labctl.analysis import get_data as get_data_module


def _write_info_pickle(tmp_path, info: dict) -> str:
    pickle_path = tmp_path / "info.pkl"
    with open(pickle_path, "wb") as f:
        pickle.dump(info, f)
    return str(pickle_path)


def _mock_np_open(monkeypatch: pytest.MonkeyPatch, height: int = 3, width: int = 5):
    img_data = np.zeros((8, height, width), dtype=float)
    img_info = {"size": (width, height)}
    monkeypatch.setattr(get_data_module.sif_parser, "np_open", lambda _: (img_data, img_info))


class _FrameLike:
    def __init__(self, height: int):
        self.height = height

    def __getitem__(self, item):
        _, _, width_slice = item
        width = width_slice.stop - width_slice.start
        return np.ones((self.height, width), dtype=float)


def _mock_get_data(monkeypatch: pytest.MonkeyPatch, height: int = 3):
    monkeypatch.setattr(get_data_module, "_get_data", lambda *args, **kwargs: _FrameLike(height))


def test_get_data_raises_when_variable_key_is_missing(tmp_path, monkeypatch: pytest.MonkeyPatch):
    _mock_np_open(monkeypatch)

    info = {
        "indices": [[(np.array([0]), np.array([1]))]],
        "n_frames": [1],
        "n_iter": 1,
        "background_every": 0,
    }
    pickle_loc = _write_info_pickle(tmp_path, info)

    with pytest.raises(ValueError, match="variable"):
        get_data_module.get_data("dummy.sif", pickle_loc)


def test_get_data_raises_with_mismatched_n_frames_without_accumulator(tmp_path, monkeypatch: pytest.MonkeyPatch):
    _mock_np_open(monkeypatch)

    info = {
        "indices": [[(np.array([0]), np.array([1])), (np.array([2]), np.array([3]))]],
        "n_frames": [1, 2],
        "n_iter": 1,
        "background_every": 0,
        "variable": "x",
        "x": [0, 1],
    }
    pickle_loc = _write_info_pickle(tmp_path, info)

    with pytest.raises(ValueError, match="same number of frames"):
        get_data_module.get_data("dummy.sif", pickle_loc, iter_accumulator=None)


@pytest.mark.parametrize("bad_accumulator", ["max", 3.14])
def test_get_data_rejects_invalid_iter_accumulator(tmp_path, monkeypatch: pytest.MonkeyPatch, bad_accumulator):
    _mock_np_open(monkeypatch)

    info = {
        "indices": [[(np.array([0]), np.array([1]))]],
        "n_frames": [1],
        "n_iter": 1,
        "background_every": 0,
        "variable": "x",
        "x": [0],
    }
    pickle_loc = _write_info_pickle(tmp_path, info)

    with pytest.raises(ValueError):
        get_data_module.get_data("dummy.sif", pickle_loc, iter_accumulator=bad_accumulator)


def test_get_data_with_string_accumulator_currently_raises_type_error(tmp_path, monkeypatch: pytest.MonkeyPatch):
    _mock_np_open(monkeypatch, height=4, width=6)
    _mock_get_data(monkeypatch, height=4)

    info = {
        "indices": [[(np.array([0]), np.array([1]))]],
        "n_frames": [2],
        "n_iter": 1,
        "background_every": 0,
        "variable": "x",
        "x": [0],
    }
    pickle_loc = _write_info_pickle(tmp_path, info)

    with pytest.raises(TypeError, match="multiple values for argument 'img_data'"):
        get_data_module.get_data(
            "dummy.sif",
            pickle_loc,
            width_indexes=(1, 4),
            iter_accumulator="sum",
        )


def test_get_data_with_background_and_string_accumulator_currently_raises_type_error(tmp_path, monkeypatch: pytest.MonkeyPatch):
    _mock_np_open(monkeypatch, height=2, width=5)
    _mock_get_data(monkeypatch, height=2)

    info = {
        "indices": [[(np.array([0]), np.array([1]))]],
        "n_frames": [2],
        "n_iter": 1,
        "background_every": -4,
        "variable": "x",
        "x": [0],
    }
    pickle_loc = _write_info_pickle(tmp_path, info)

    with pytest.raises(TypeError, match="multiple values for argument 'img_data'"):
        get_data_module.get_data(
            "dummy.sif",
            pickle_loc,
            width_indexes=(0, 2),
            iter_accumulator="mean",
        )


