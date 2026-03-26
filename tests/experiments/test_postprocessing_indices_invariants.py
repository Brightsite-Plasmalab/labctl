import numpy as np
import pytest

from labctl.experiments.camera import BackgroundConfiguration
from labctl.experiments.camera_timesweep import CameraTimesweepExperiment
from labctl.experiments.polarisation import PolarisationFilterExperiment
from labctl.experiments.polarisation_calibration import PolarisationFilterCalibrationExperiment
from labctl.experiments.pulsed_microwave import PulsedMicrowaveTimesweep
from labctl.experiments.raman_2d import Raman2DExperiment
from labctl.experiments.translation_stage import TranslationStageExperiment


def _build_experiment_instance(experiment_class: type, background_every: BackgroundConfiguration):
    exp = object.__new__(experiment_class)

    exp.file_name = "test"
    exp.short_explanation = ""
    exp.author = ""
    exp.n_iter = 1
    exp.t_exposure = 0.1
    exp.camera_delay_optimum = 0.0
    exp.camera_delay_background = 0.0
    exp.laser_frequency = 30
    exp.camera_channel = "C"
    exp.background_every = background_every

    if experiment_class is CameraTimesweepExperiment:
        exp.n_frames = [2, 3]
        exp.t0 = 0.0
        exp.delta_t = [0.0, 1.0]
    elif experiment_class is PolarisationFilterCalibrationExperiment:
        exp.n_frames = [2, 1, 2]
        exp.alpha = [0.0, 45.0, 90.0]
    elif experiment_class is PolarisationFilterExperiment:
        exp.n_frames = [1, 2]
        exp.alpha_ver = 0.0
        exp.alpha_hor = 90.0
    elif experiment_class is Raman2DExperiment:
        exp.n_frames = [2, 1]
        exp.filters = ["f0", "f1"]
    elif experiment_class is TranslationStageExperiment:
        exp.n_frames = [1, 3]
        exp.x = [0.0, 1.0]
    elif experiment_class is PulsedMicrowaveTimesweep:
        exp.n_frames = [2, 2]
        exp.t0 = 100e-9
        exp.delta_t = [0.0, 10e-9]
        exp.MW_pulse_frequency = 300
        exp.channel_MW_trigger = "D"
        exp.channel_MW_trigger_int = 4
    else:
        raise ValueError(f"Unsupported experiment class {experiment_class.__name__}")

    return exp


def _expected_indices_for_first_iteration(exp) -> list[tuple[np.ndarray, np.ndarray]]:
    expected: list[tuple[np.ndarray, np.ndarray]] = []
    running_total = 0
    for frames in exp.n_frames:
        names = exp.background_every.make_name_list(frames)
        names_array = np.asarray(names)
        foreground = np.where(names_array == "foreground")[0] + running_total
        background = np.where(names_array == "background")[0] + running_total
        expected.append((foreground, background))
        running_total += len(names)
    return expected


@pytest.mark.parametrize(
    "experiment_class",
    [
        CameraTimesweepExperiment,
        PolarisationFilterCalibrationExperiment,
        PolarisationFilterExperiment,
        Raman2DExperiment,
        TranslationStageExperiment,
        PulsedMicrowaveTimesweep,
    ],
    ids=lambda cls: cls.__name__,
)
@pytest.mark.parametrize("background_every", [BackgroundConfiguration.NONE, BackgroundConfiguration.BEGIN_END])
def test_postprocessing_indices_are_well_formed(experiment_class: type, background_every: BackgroundConfiguration):
    exp = _build_experiment_instance(experiment_class, background_every)

    info = exp.make_postprocessing_info()

    assert "indices" in info
    assert info["n_iter"] == exp.n_iter
    assert info["n_frames"] == exp.n_frames

    indices = info["indices"]
    assert isinstance(indices, list)
    assert len(indices) == exp.n_iter

    expected = _expected_indices_for_first_iteration(exp)
    first_iteration = indices[0]
    assert len(first_iteration) == len(exp.n_frames)

    total_measurements = sum(exp.background_every.measurement_count(frames) for frames in exp.n_frames)

    for config_index, (foreground_idx, background_idx) in enumerate(first_iteration):
        assert np.all(np.diff(foreground_idx) >= 0)
        assert np.all(np.diff(background_idx) >= 0)

        # Foreground and background slices should not overlap.
        assert np.intersect1d(foreground_idx, background_idx).size == 0

        expected_foreground, expected_background = expected[config_index]
        np.testing.assert_array_equal(foreground_idx, expected_foreground)
        np.testing.assert_array_equal(background_idx, expected_background)

        assert len(foreground_idx) + len(background_idx) == exp.background_every.measurement_count(exp.n_frames[config_index])

        all_indices = np.concatenate((foreground_idx, background_idx))
        assert np.all(all_indices >= 0)
        assert np.all(all_indices < total_measurements)

