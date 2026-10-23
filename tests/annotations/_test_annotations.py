import inspect
import types
import typing

import typing_extensions


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

    if not has_none:
        return False

    if isinstance(expected_inner, types.UnionType):
        expected_inner = typing.get_args(expected_inner)
        if len(non_none_args) != len(expected_inner):
            return False

        return all(type_value in expected_inner for type_value in non_none_args)

    return len(non_none_args) == 1 and non_none_args[0] == expected_inner


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
    """
    Return whether a parameter is compatible with a TypedDict field.
    """
    if _annotations_compatible(parameter.annotation, typed_dict_annotation):
        return True
    return _is_optional_of(
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


def typed_dict_func_class_same(test_value, test_typed_dict,
                               class_or_func: typing.Literal['class', 'func']):

    if class_or_func == "class":
        name = f"{test_value.__name__}.__init__"
        test_value = test_value.__init__
    else:
        name = test_value.__name__

    sig = inspect.signature(test_value).parameters

    # Check if all parameters have some typehint.
    for k, v in sig.items():
        if k == "self":
            continue
        assert v.annotation != inspect._empty, f"Parameter {k} in {name} is not annotated"

    sig, kwargs = extract_kwargs(dict(sig))

    # Select parameters to skip
    # for the class we only skip the self parameter, for the functions we skip all non keyword-only parameters
    if class_or_func == 'class':
        def selector(key, _):
            return key != 'self'
    else:
        def selector(_, value):
            return value.kind == value.KEYWORD_ONLY
    
    test_class_params = {
        k: v.annotation for k, v in sig.items() if selector(k, v)
    }
    test_class_defaults = [
        k for k, v in sig.items() if selector(k, v) and v.default != inspect._empty
    ]

    typed_dict_params = inspect.get_annotations(test_typed_dict)
    typed_dict_params_unwrapped = {
        k: unwrap_not_required(v) for k, v in typed_dict_params.items()
    }
    typed_dict_params_not_required = [
        k for k, v in typed_dict_params.items() if check_not_required(v)
    ]

    # Test if all parameters in the TypedDict are in the function and have the same typehint
    for key in typed_dict_params:
        # The kwargs are skipped, since it's assumed those are tested in the parent class or other called function
        if key in kwargs:
            continue
        assert key in test_class_params, f"Parameter {key} is missing in {name}"
        assert _parameter_matches_typed_dict(sig[key], typed_dict_params[key]), \
            (f"Parameter {key} has type {test_class_params[key]} in {name} "
             f"but {typed_dict_params_unwrapped[key]} in {test_typed_dict.__name__}")

    # Test if all the NotRequired values also have a default
    for key in typed_dict_params_not_required:
        # The kwargs are skipped, since it's assumed those are tested in the parent class or other called function
        if key in kwargs:
            continue
        assert key in test_class_defaults, \
            (f"Parameter {key} is NotRequired in {test_typed_dict.__name__}, "
             f"but has no default value in {name}")

    # Test if all parameters in the function are in the TypedDict
    for key in test_class_params:
        assert key in typed_dict_params, \
            f"{name} has parameter {key}, but this is not in {test_typed_dict.__name__}"

    # Test if all the values with a default are marked NotRequired
    for key in test_class_defaults:
        assert key in typed_dict_params_not_required, \
            (f"Parameter {key} has a default value in {name}, "
             f"but is not marked NotRequired in {test_typed_dict.__name__}")
