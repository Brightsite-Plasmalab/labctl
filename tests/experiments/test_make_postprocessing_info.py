# TODO: Look at automatic generated tests
import inspect

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
    elif experiment_class.__name__ == "PolarisationFilterCalibrationExperiment":
        exp.alpha = [0.0]
        exp.n_frames = [1]
    elif experiment_class.__name__ == "PolarisedTranslationStageExperiment":
        exp.alpha_hor = 0.0
        exp.alpha_ver = 90.0
        exp.x = [0.0, 1.0]
        exp.n_frames = [1, 2, 1, 2]
    elif experiment_class.__name__ == "PolarisationFilterExperiment":
        exp.n_frames = [1, 2]
        exp.alpha_ver = 0.0
        exp.alpha_hor = 90.0
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
    assert variable is None or isinstance(
        variable, str
    ), f"{experiment_class.__name__}.make_postprocessing_info['variable'] must be str or None"
    if isinstance(variable, str):
        assert variable in info, (
            f"{experiment_class.__name__}.make_postprocessing_info['variable'] is '{variable}', "
            "but that key is missing in the returned dictionary"
        )
