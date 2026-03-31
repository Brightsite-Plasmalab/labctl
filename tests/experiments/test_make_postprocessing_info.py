# TODO: Look at automatic generated tests
import inspect

import numpy as np
import pytest

import labctl.experiments as experiments_module
from labctl.experiments.base import BaseExperiment
from labctl.experiments.camera import BackgroundConfiguration, CameraExperiment


def _iter_public_experiment_classes() -> list[type[BaseExperiment]]:
    classes: list[type[BaseExperiment]] = []
    for _, value in inspect.getmembers(experiments_module, inspect.isclass):
        if not issubclass(value, BaseExperiment):
            continue
        if value is BaseExperiment:
            continue
        # Skip abstract classes (those with unimplemented abstract methods)
        if inspect.isabstract(value):
            continue
        classes.append(value)
    return classes


def _make_instance_for_postprocessing_info(
    experiment_class: type[BaseExperiment],
) -> BaseExperiment:
    # Use __new__ to avoid device initialization and constructor-side validation.
    exp = object.__new__(experiment_class)

    exp.file_name = "test"
    exp.short_explanation = ""
    exp.author = ""

    if issubclass(experiment_class, CameraExperiment):
        exp.n_frames = [2]
        exp.n_iter = 1
        exp.t_exposure = 0.1
        exp.background_every = BackgroundConfiguration.NONE

    if experiment_class.__name__ in {
        "CameraTimesweepExperiment",
        "LaserTimesweepExperiment",
        "PulsedMicrowaveTimesweep",
    }:
        exp.n_frames = [1, 2]
        exp.t0 = 0.0
        exp.delta_t = [0.0, 1.0]
        exp.camera_delay_optimum = 0.0
    elif experiment_class.__name__ == "PolarisationFilterSweepExperiment":
        exp.alpha = [0.0, 1.0, 2.0, 3.0]
        exp.n_frames = [1, 2, 1, 3]
    elif experiment_class.__name__ == "PolarisedTranslationStageExperiment":
        exp.alpha_hor = 0.0
        exp.alpha_ver = 90.0
        exp.alpha = [exp.alpha_ver, exp.alpha_hor]
        exp.x = [0.0, 1.0]
        exp.n_frames = [1, 2, 1, 2]
    elif experiment_class.__name__ == "PolarisationFilterExperiment":
        exp.n_frames = [1, 2]
        exp.alpha_ver = 0.0
        exp.alpha_hor = 90.0
        exp.alpha = [exp.alpha_ver, exp.alpha_hor]
    elif experiment_class.__name__ == "Raman2DExperiment":
        exp.filters = ["f0"]
    elif experiment_class.__name__ == "TranslationStageExperiment":
        exp.x = [0.0]
    elif experiment_class.__name__ == "SimpleCameraExperiment":
        pass
    else:
        raise ValueError(f"Test not yet implemented for {experiment_class.__name__}")

    return exp


@pytest.mark.parametrize(
    "experiment_class",
    _iter_public_experiment_classes(),
    ids=lambda cls: cls.__name__,
)
def test_make_postprocessing_info_contains_variable_key(
    experiment_class: type[BaseExperiment],
):
    experiment = _make_instance_for_postprocessing_info(experiment_class)

    info = experiment.make_postprocessing_info()

    assert isinstance(
        info, dict
    ), f"{experiment_class.__name__}.make_postprocessing_info must return a dict"
    assert (
        "variable" in info
    ), f"{experiment_class.__name__}.make_postprocessing_info must contain a 'variable' key"

    variable = info["variable"]
    assert variable is None or isinstance(variable, (str, list)), (
        f"{experiment_class.__name__}.make_postprocessing_info['variable'] must be None, str, or list[str]"
    )
    if isinstance(variable, str):
        assert variable in info, (
            f"{experiment_class.__name__}.make_postprocessing_info['variable'] is '{variable}', "
            "but that key is missing in the returned dictionary"
        )
    if isinstance(variable, list):
        assert all(isinstance(v, str) for v in variable), (
            f"{experiment_class.__name__}.make_postprocessing_info['variable'] list must contain only strings"
        )
        for v in variable:
            assert v in info, (
                f"{experiment_class.__name__}.make_postprocessing_info['variable'] contains '{v}', "
                "but that key is missing in the returned dictionary"
            )


@pytest.mark.parametrize(
    "experiment_class",
    [
        cls
        for cls in _iter_public_experiment_classes()
        if issubclass(cls, CameraExperiment)
    ],
    ids=lambda cls: cls.__name__,
)
def test_make_postprocessing_info_legacy_and_new_index_keys_are_consistent(
    experiment_class: type[BaseExperiment],
):
    experiment = _make_instance_for_postprocessing_info(experiment_class)
    info = experiment.make_postprocessing_info()

    assert "configs" in info
    assert "indices" in info
    assert "indices_full" in info
    assert len(info["indices_full"]) == info["n_iter"]

    config_items = list(info["configs"].items())
    assert len(config_items) == len(info["indices"])

    for index, (config_name, config_info) in enumerate(config_items):
        sig_key = f"{config_name}_sig"
        bg_key = f"{config_name}_bg"

        assert sig_key in info
        assert bg_key in info

        np.testing.assert_array_equal(info[sig_key], config_info["foreground"])
        np.testing.assert_array_equal(info[bg_key], config_info["background"])

        np.testing.assert_array_equal(info["indices"][index][0], config_info["foreground"])
        np.testing.assert_array_equal(info["indices"][index][1], config_info["background"])

        # For n_iter == 1 in this fixture, grouped and full first-iteration are identical.
        np.testing.assert_array_equal(info["indices_full"][0][index][0], config_info["foreground"])
        np.testing.assert_array_equal(info["indices_full"][0][index][1], config_info["background"])

