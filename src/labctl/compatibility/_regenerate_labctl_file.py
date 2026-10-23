from __future__ import annotations

import inspect
import pathlib
import pickle
from abc import ABC
from dataclasses import dataclass
from os import PathLike
from typing import Any, NotRequired, TypedDict, get_args, get_origin, get_type_hints

from labctl import experiments

_classes_by_name = {
    name: obj
    for name, obj in inspect.getmembers(experiments, inspect.isclass)
    if obj.__module__.startswith("labctl.experiments")
}

def _typed_dict_fields(td_cls: type[TypedDict]) -> dict[str, bool]:
    """
    Return TypedDict fields as:
        {field_name: is_required}
    """
    hints = get_type_hints(td_cls, include_extras=True)
    result: dict[str, bool] = {}

    for name, tp in hints.items():
        is_required = True
        if getattr(tp, "__origin__", None) is NotRequired:
            is_required = False
        result[name] = is_required

    return result


def _class_init_fields(cls: type) -> dict[str, bool]:
    """
    Collect parameters from cls.__init__ only (not inherited ones).

    If the class uses **kwargs, parent parameters are passed through **kwargs
    so we don't need to explicitly include them.
    """
    result: dict[str, bool] = {}

    init = cls.__dict__.get("__init__")
    if init is None:
        return result

    sig = inspect.signature(init)

    for name, param in sig.parameters.items():
        if name == "self":
            continue
        # Skip *args and **kwargs
        if param.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            continue

        required = param.default is inspect._empty
        result[name] = required

    return result


def _get_unpack_typeddict(sig: inspect.Signature) -> type[TypedDict] | None:
    """
    If a signature has **kwargs: Unpack[SomeTypedDict], return SomeTypedDict.
    """
    for param in sig.parameters.values():
        if param.kind == inspect.Parameter.VAR_KEYWORD:
            ann = param.annotation
            if ann is inspect._empty:
                continue
            origin = get_origin(ann)
            # Check for Unpack (from typing or typing_extensions)
            if getattr(origin, "__name__", None) == "Unpack":
                args = get_args(ann)
                if args:
                    return args[0]
    return None


def _find_kwargs_typeddict_for_class(cls: type) -> type[TypedDict] | None:
    """
    Look for a TypedDict named '<ClassName>Kwargs' in labctl.experiments.
    """
    td_name = f"{cls.__name__}Kwargs"
    obj = getattr(experiments, td_name, None)
    if obj is not None and inspect.isclass(obj):
        return obj
    return None


def _extract_argument_names_for_experiment(
    cls: type,
    kwargs_typed_dict: type[TypedDict] | None = None,
) -> dict[str, list[str]]:
    """
    Extract experiment argument names split into required / not_required.

    Returns
    -------
    dict with:
        required: list[str]
        not_required: list[str]
    """
    required: list[str] = []
    not_required: list[str] = []

    init_fields = _class_init_fields(cls)
    for name, is_required in init_fields.items():
        if is_required:
            required.append(name)
        else:
            not_required.append(name)

    # First try the provided kwargs_typed_dict
    if kwargs_typed_dict is not None:
        td_fields = _typed_dict_fields(kwargs_typed_dict)
        for name, is_required in td_fields.items():
            if is_required:
                required.append(name)
            else:
                not_required.append(name)
    else:
        # If not provided, try to extract from **kwargs: Unpack[...]
        init = cls.__dict__.get("__init__")
        if init is not None:
            sig = inspect.signature(init)
            unpacked_td = _get_unpack_typeddict(sig)
            if unpacked_td is not None:
                td_fields = _typed_dict_fields(unpacked_td)
                for name, is_required in td_fields.items():
                    if is_required:
                        required.append(name)
                    else:
                        not_required.append(name)

    return {
        "required": required,
        "not_required": not_required,
    }


def _extract_all_experiment_arguments() -> dict[str, dict[str, list[str]]]:
    """
    Extract argument names for all experiment classes in labctl.experiments.
    """
    out: dict[str, dict[str, list[str]]] = {}

    for name, cls in _classes_by_name.items():
        if name.endswith("Kwargs"):
            continue
        if not issubclass(cls, ABC):
            continue

        kwargs_td = _find_kwargs_typeddict_for_class(cls)
        out[name] = _extract_argument_names_for_experiment(cls, kwargs_td)

    return out

_classes_arguments = _extract_all_experiment_arguments()


@dataclass
class ValueMap:
    value: Any


def regenerate_file(pickle_loc: str | PathLike, loc_out: str | PathLike | None = None, **extra_info) -> str:
    """
    Regenerate labctl file with the new version based on the pickle file

    if a value got a different name in the new version, you can use a :class:`ValueMap` as a kwarg to map the old name
    (value in the :class:`ValueMap`) to the new name (kwarg name).

    Returns
    -------
    The output loc of the generated pkl file
    """
    with open(pickle_loc, "rb") as f:
        info = pickle.load(f)


    def find_value(name, *, required: bool):
        if name not in info:
            cap_name = name[0].upper() + name[1:]
            if cap_name in info:
                return info[cap_name]

            if name not in extra_info:
                if required:
                    info_keys = tuple(info.keys())
                    extra_keys = tuple(extra_info.keys())

                    msg = f"{name} not found in info nor extra_info. pkl info keys: {info_keys}, extra_info keys: {extra_keys}."
                    raise ValueError(msg)
                else:
                    return None
            else:
                val = extra_info[name]
                if isinstance(val, ValueMap):
                    return info[val.value]
                return val
        else:
            return info[name]

    experiment_type = find_value("experiment_type", required=True)
    arguments = _classes_arguments[experiment_type]
    required_arguments, not_required_arguments = arguments["required"], arguments["not_required"]

    call_kwargs = {}

    if loc_out is None:
        pickle_loc = pathlib.Path(pickle_loc)
        loc_out = pickle_loc.parent / (pickle_loc.stem + "_regenerated.pkl")

    defaults = {
        "dest_folder": "",
        "file_name": "",
    }

    errors = []
    for arg in required_arguments:
        if arg in defaults and arg not in extra_info:
            call_kwargs[arg] = defaults[arg]
        else:
            try:
                call_kwargs[arg] = find_value(arg, required=True)
            except ValueError as e:
                errors.append(e)
    if len(errors) > 0:
        raise BaseExceptionGroup("Did not find all needed parameters", errors)

    for arg in not_required_arguments:
        value = find_value(arg, required=False)
        if value is not None:
            call_kwargs[arg] = value

    experiment_class: experiments.BaseExperiment = _classes_by_name[experiment_type](**call_kwargs)
    experiment_class.save_postprocessing_info(loc_out)
    return str(loc_out)