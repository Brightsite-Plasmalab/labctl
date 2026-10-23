"""
Typehints for the LabCTL package.

It includes two typehints for the path of files: :data:`_file_path_type`, :data:`_file_path_or_collection_type`.

It has one protocol class for a function acting on a numpy array: :class:`ArrayProcessor`

It has one typehint for accumulators in the data getters: :data:`_acc_typehint`


.. autodata:: _file_path_type
.. autodata:: _file_path_or_collection_type
.. autodata:: _acc_typehint
"""

import os
from collections.abc import Collection
from typing import Literal, Protocol

import numpy as np

_file_path_type = os.PathLike | str
_file_path_or_collection_type = _file_path_type | Collection[_file_path_type]


class ArrayProcessor(Protocol):
    def __call__(self, arr: np.ndarray, axis: int | tuple[int, ...]) -> np.ndarray:
        ...

_acc_typehint = Literal["median", "mean", "sum"] | ArrayProcessor
