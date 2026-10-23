import functools
from collections.abc import Callable

import numpy as np

from labctl._type_hints import _acc_typehint


def _get_accumulator(
    value: _acc_typehint,
    axis: int | tuple[int, ...],
    name: str,
) -> Callable[..., np.ndarray]:
    """
    Return an accumulator callable bound to *axis*.

    Parameters
    ----------
    value : _acc_typehint
        Either a string shorthand for a built-in NumPy reduction
        (``'median'``, ``'mean'``, or ``'sum'``) or a custom callable that
        has a numpy array as the first argument and the reduction axis as
        the second argument.
    axis : int
        Axis along which the built-in reduction is applied when *value* is
        a string.  Ignored for custom callables.
    name : str
        Name of the parameter being validated; used only in error messages.

    Returns
    -------
    Callable[..., np.ndarray]
        A callable that performs the requested reduction on an array.

    Raises
    ------
    ValueError
        If *value* is an unrecognised string or is neither a string nor a
        callable.
    """
    if isinstance(value, str):
        match value:
            case "median":
                value = np.median
            case "mean":
                value = np.mean
            case "sum":
                value = np.sum
            case _:
                msg = f"Only 'median', 'mean', or 'sum' are valid str value for `{name}`."
                raise ValueError(msg)
    elif not isinstance(value, Callable):
        msg = f"Expected str or Callable for `{name}`, got {type(value).__name__}."
        raise TypeError(msg)

    return functools.partial(value, axis=axis)