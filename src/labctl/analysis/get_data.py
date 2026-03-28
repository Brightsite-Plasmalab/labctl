import functools
import pickle
from collections.abc import Callable

import numpy as np
import sif_parser


def _get_data(data, info, indexer, frame_index: int, iter_index: int = 0):
    indexes = info['indices'][iter_index][frame_index][indexer]
    return np.squeeze(data[indexes, :, :])


def _config_num(info):
    if "variable" in info:
        variable = info["variable"]
        if not isinstance(variable, str):
            variable = variable[0]
        return len(info[variable])
    else:
        raise ValueError("No 'variable' key found in info, cannot extract experiment variable(s).")


def get_data(sif_loc, pickle_loc, width_indexes=None, height_indexes=None, iter_accumulator=None):
    """
    If iter_accumulator is a function, it should perform its accumulation over axis -3.
    """
    with open(pickle_loc, "rb") as f:
        info = pickle.load(f)
    img_data, img_info = sif_parser.np_open(sif_loc)
    image_size = img_info['size']
    has_background = info["background_every"] != 0

    config_num = _config_num(info)

    def set_indexes(given_value, dir_image_size, name):
        if given_value is None:
            return 0, dir_image_size
        elif given_value[0] >= given_value[1]:
            msg = f"For `{name}_indexes` first value should be smaller than second value, found {given_value}"
            raise ValueError(msg)
        elif given_value[0] < 0:
            msg = f"For `{name}_indexes` first value should be bigger or equal to zero, found {given_value[0]}"
            raise ValueError(msg)
        elif given_value[1] > dir_image_size:
            msg = (f"For `{name}_indexes` second value should be smaller or equal to image size ({dir_image_size}), "
                   f"found {given_value[0]}")
            raise ValueError(msg)
        else:
            return given_value[0], given_value[1]


    width_indexes = set_indexes(width_indexes, image_size[0], "width_indexes")
    height_indexes = set_indexes(height_indexes, image_size[1], "height_indexes")
    new_image_size = (height_indexes[1]-height_indexes[0], width_indexes[1]-width_indexes[0])

    def _data_getter(signal, img_data, info, accumulator_func, index_iter, indexer):
        nonlocal new_image_size
        index = 0
        for i, frames in enumerate(info["n_frames"]):
            acc_signal = np.zeros((frames, *new_image_size))

            for j in range(frames):
                data = _get_data(img_data, info, index, index_iter, indexer)
                acc_signal[j] = data[:, :, slice(*width_indexes)]
            signal[i] = accumulator_func(acc_signal)

    def _over_n_iter(function, n_iter, curr_shape):
        if n_iter == 1:
            signal = np.zeros(curr_shape)
            function(signal, 0)
            return signal
        else:
            shape = (n_iter,) + curr_shape
            signal = np.zeros(shape)
            for index in range(n_iter):
                function(signal[index], index)
            return signal

    def accumulator_data(info, img_data, accumulator_func, n_iter, indexer):
        nonlocal new_image_size
        data_shape = (config_num, *new_image_size)
        partial_func = functools.partial(_data_getter, img_data=img_data, info=info, accumulator_func=accumulator_func,
                                         indexer=indexer)
        return _over_n_iter(partial_func, n_iter, data_shape)

    def full_data(info, img_data, n_frames, n_iter, indexer):
        nonlocal new_image_size
        data_shape = (config_num, n_frames, *new_image_size)
        partial_func = functools.partial(_data_getter, img_data=img_data, info=info, accumulator_func=lambda x: x,
                                         indexer=indexer)
        return _over_n_iter(partial_func, n_iter, data_shape)

    if iter_accumulator is None:
        n_frames_set = set(info["n_frames"])
        if len(n_frames_set) != 1:
            msg = ("When no accumulator function is used, all configurations must have the same number of frames."
                   f"Found {list(n_frames_set)}")
            raise ValueError(msg)
        n_frames = info["n_frames"][0]
        caller = functools.partial(full_data, info, img_data, n_frames)
    elif isinstance(iter_accumulator, Callable | str):
        if isinstance(iter_accumulator, str):
            match iter_accumulator:
                case "median":
                    func = np.median
                case "mean":
                    func = np.mean
                case "sum":
                    func = np.sum
                case _:
                    raise ValueError("Only 'median', 'mean', or 'sum' are valid values str value for `iter_accumulator`.")
            accumulator_func = functools.partial(func, axis=-3)
        else:
            accumulator_func = iter_accumulator
        caller = functools.partial(accumulator_data, info, img_data, accumulator_func, info["n_iter"])
    else:
        msg = f"`iter_accumulator` must be either a str of Callable, not {type(iter_accumulator).__name__}"
        raise ValueError(msg)

    data = caller(0)
    if has_background:
        background = caller(1)
        return data, background
    return data, None
