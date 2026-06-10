import inspect
import pytest
import typing

import typing_extensions

from labctl.experiments.base import BaseExperiment, BaseExperimentKwargs
from labctl.experiments.camera import CameraExperiment, CameraExperimentKwargs
from labctl.experiments.camera_timesweep import CameraTimesweepExperiment, CameraTimesweepExperimentKwargs
from labctl.experiments.polarisation_sweep import (PolarisationFilterSweepExperiment,
                                                         PolarisationFilterSweepExperimentKwargs)
from labctl.experiments.polarisation import PolarisationFilterExperiment, PolarisationFilterExperimentKwargs
from labctl.experiments.translation_stage import TranslationStageExperiment, TranslationStageExperimentKwargs
from labctl.experiments.raman_2d import Raman2DExperiment, Raman2DExperimentKwargs
from labctl.experiments.pulsed_microwave import PulsedMicrowaveTimesweep, PulsedMicrowaveTimesweepKwargs
from labctl.experiments.experiment_polarised_translation_stage import (PolarisedTranslationStageExperiment,
                                                                             PolarisedTranslationStageExperimentKwargs)


def check_not_required(tp):
    """
    Return True if `tp` is `NotRequired[T]` (typing or typing_extensions),
    otherwise return False.
    """
    origin = typing.get_origin(tp)
    return origin is typing_extensions.NotRequired


def unwrap_not_required(tp):
    """
    If `tp` is `NotRequired[T]` (typing or typing_extensions), return `T`,
    otherwise return `tp` unchanged.
    """
    if check_not_required(tp):
        args = typing.get_args(tp)
        return args[0]
    return tp


def _is_optional_of(tp, expected_inner) -> bool:
    """Return True if ``tp`` is ``expected_inner | None`` / ``Optional[expected_inner]``."""
    args = typing.get_args(tp)
    if not args:
        return False
    non_none_args = tuple(arg for arg in args if arg is not type(None))
    has_none = len(non_none_args) != len(args)
    return has_none and len(non_none_args) == 1 and non_none_args[0] == expected_inner


def _annotations_compatible(param_annotation, typed_dict_annotation) -> bool:
    """Return whether constructor and TypedDict annotations are compatible.

    For ``NotRequired[T]`` fields, constructor annotations may be either ``T``
    or ``T | None`` / ``Optional[T]``.
    """
    unwrapped = unwrap_not_required(typed_dict_annotation)
    if param_annotation == unwrapped:
        return True
    if check_not_required(typed_dict_annotation):
        return _is_optional_of(param_annotation, unwrapped)
    return False


def _parameter_matches_typed_dict(
    parameter: inspect.Parameter,
    typed_dict_annotation,
) -> bool:
    """Return whether a constructor parameter is compatible with a TypedDict field.

    Besides exact matches, this accepts ``T | None`` when the constructor
    default is ``None`` because the codebase uses that pattern for values that
    are validated explicitly at runtime.
    """
    if _annotations_compatible(parameter.annotation, typed_dict_annotation):
        return True
    return parameter.default is None and _is_optional_of(
        parameter.annotation, unwrap_not_required(typed_dict_annotation)
    )

def _is_unpack(tp):
    """Return True if tp is Unpack[...] (typing or typing_extensions)."""
    origin = typing.get_origin(tp)
    return origin is typing_extensions.Unpack

def _type_hints_for_typeddict(td_type):
    """
    Return annotations for a TypedDict class/type as a dict.
    Tries typing.get_type_hints(include_extras=True) first to preserve wrappers
    like NotRequired, falls back to inspect.get_annotations.
    """
    hints = typing.get_type_hints(td_type, include_extras=True)
    if not hints:
        # fallback if get_type_hints returns empty for some runtime-created TDs
        hints = inspect.get_annotations(td_type)
    return hints

def unwrap_unpack(tp):
    """
    If `tp` is `Unpack[T]` where T is a TypedDict type, return a dict of
    the underlying TypedDict's annotations (possibly containing NotRequired).
    Otherwise return None.
    """
    if not _is_unpack(tp):
        return None
    args = typing.get_args(tp)
    if not args:
        return None
    underlying = args[0]
    return _type_hints_for_typeddict(underlying)

def extract_kwargs(parameters: dict[str, inspect.Parameter]):
    """
    Given a mapping of names -> typehint where some values may be Unpack[TypedDict],
    return a new dict with all Unpack expansions merged into the result.
    Example input:
      {"a": int, "b": Unpack[SomeTD]}
    -> result will contain "a" plus all keys from SomeTD.
    """
    result = {}
    params = parameters.copy()
    for name, tp in parameters.items():
        expanded = unwrap_unpack(tp.annotation)
        if expanded is not None:
            for k, v in expanded.items():
                if k in result:
                    raise ValueError(f"Conflict while unpacking TypedDict: {k} already present")
                result[k] = v
            del params[name]
    return params, result


experiments_plus_kwargs = [
    (BaseExperiment, BaseExperimentKwargs),
    (CameraExperiment, CameraExperimentKwargs),
    (CameraTimesweepExperiment, CameraTimesweepExperimentKwargs),
    (PolarisationFilterSweepExperiment, PolarisationFilterSweepExperimentKwargs),
    (PolarisationFilterExperiment, PolarisationFilterExperimentKwargs),
    (TranslationStageExperiment, TranslationStageExperimentKwargs),
    (Raman2DExperiment, Raman2DExperimentKwargs),
    (PulsedMicrowaveTimesweep, PulsedMicrowaveTimesweepKwargs),
    (PolarisedTranslationStageExperiment, PolarisedTranslationStageExperimentKwargs),
]

@pytest.mark.parametrize("test_class, test_typed_dict", experiments_plus_kwargs)
def test_typed_dict_init_same(test_class, test_typed_dict):
    sig = inspect.signature(test_class.__init__).parameters
    for k, v in sig.items():
        if k == "self":
            continue
        assert v.annotation != inspect._empty, f"Parameter {k} in {test_class.__name__}.__init__ is not annotated"

    sig, kwargs = extract_kwargs(dict(sig))

    test_class_params = {
        k: v.annotation for k, v in sig.items() if k != "self"
    }
    test_class_defaults = [
        k for k, v in sig.items() if k != "self" and v.default != inspect._empty
    ]

    typed_dict_params = inspect.get_annotations(test_typed_dict)
    typed_dict_params_unwrapped = {
        k: unwrap_not_required(v) for k, v in typed_dict_params.items()
    }
    typed_dict_params_not_required = [
        k for k, v in typed_dict_params.items() if check_not_required(v)
    ]

    for key in typed_dict_params:
        if key in kwargs:
            continue
        assert key in test_class_params, f"Parameter {key} is missing in {test_class.__name__}.__init__"
        assert _parameter_matches_typed_dict(sig[key], typed_dict_params[key]), \
            (f"Parameter {key} has type {test_class_params[key]} in {test_class.__name__}.__init__, "
             f"but {typed_dict_params_unwrapped[key]} in {test_typed_dict.__name__}")

    for key in test_class_params:
        assert key in typed_dict_params, \
            f"{test_class.__name__}.__init__ has parameter {key}, but this is not in {test_typed_dict.__name__}"

    for key in typed_dict_params_not_required:
        if key in kwargs:
            continue
        assert key in test_class_defaults, \
            (f"Parameter {key} is NotRequired in {test_typed_dict.__name__}, "
             f"but has no default value in {test_class.__name__}.__init__")

