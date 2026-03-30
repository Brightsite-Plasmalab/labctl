"""
Tests that each concrete BaseExperiment subclass can execute
``make_labctl_script`` and ``make_postprocessing_script`` without errors.
"""

import pytest

from labctl.experiments.camera_timesweep import CameraTimesweepExperiment
from labctl.experiments.polarisation import PolarisationFilterExperiment
from labctl.experiments.polarisation_calibration import (
    PolarisationFilterCalibrationExperiment,
)
from labctl.experiments.polarised_translation_stage import (
    PolarisedTranslationStageExperiment,
)
from labctl.experiments.pulsed_microwave import PulsedMicrowaveTimesweep
from labctl.experiments.raman_2d import Raman2DExperiment
from labctl.experiments.laser_Qswitch_timesweep import LaserTimesweepExperiment
from labctl.experiments.simple import SimpleCameraExperiment
from labctl.experiments.translation_stage import TranslationStageExperiment


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _base_camera_kwargs(**overrides):
    """Minimal valid kwargs shared by every CameraExperiment subclass."""
    kwargs = {
        "dest_folder": ".",
        "file_name": "test",
        "t_exposure": 0.1,
        "camera_delay_optimum": 0.0,
    }
    kwargs.update(overrides)
    return kwargs


# ---------------------------------------------------------------------------
# Fixtures – one per concrete subclass
# ---------------------------------------------------------------------------


@pytest.fixture()
def simple_camera_experiment():
    return SimpleCameraExperiment(
        **_base_camera_kwargs(n_frames=[1]),
    )


@pytest.fixture()
def camera_timesweep_experiment():
    return CameraTimesweepExperiment(
        delta_t=[0.0, 1e-6],
        **_base_camera_kwargs(n_frames=[1, 1]),
    )


@pytest.fixture()
def polarisation_filter_experiment():
    return PolarisationFilterExperiment(
        alpha_ver=30.0,
        **_base_camera_kwargs(n_frames=[1, 1]),
    )


@pytest.fixture()
def polarisation_filter_calibration_experiment():
    return PolarisationFilterCalibrationExperiment(
        alpha=[0.0, 45.0, 90.0],
        **_base_camera_kwargs(n_frames=[1, 1, 1]),
    )


@pytest.fixture()
def translation_stage_experiment():
    return TranslationStageExperiment(
        x=[0.0, 1.0],
        **_base_camera_kwargs(n_frames=[1, 1]),
    )


@pytest.fixture()
def polarised_translation_stage_experiment():
    return PolarisedTranslationStageExperiment(
        x=[0.0, 1.0],
        alpha_ver=10.0,
        **_base_camera_kwargs(n_frames=[1, 1]),
    )


@pytest.fixture()
def pulsed_microwave_timesweep():
    return PulsedMicrowaveTimesweep(
        t0=100e-9,
        delta_t=[0.0, 10e-9],
        MW_pulse_frequency=60,
        channel_MW_trigger="D",
        **_base_camera_kwargs(n_frames=[1, 1]),
    )


@pytest.fixture()
def raman_2d_experiment():
    return Raman2DExperiment(
        filters=["F1", "F2"],
        **_base_camera_kwargs(n_frames=[1, 1]),
    )


# ---------------------------------------------------------------------------
# Tests – make_labctl_script
# ---------------------------------------------------------------------------


class TestMakeLabctlScript:
    def test_simple_camera(self, simple_camera_experiment):
        result = simple_camera_experiment.make_labctl_script()
        assert result is not None

    def test_camera_timesweep(self, camera_timesweep_experiment):
        result = camera_timesweep_experiment.make_labctl_script()
        assert result is not None

    def test_polarisation_filter(self, polarisation_filter_experiment):
        result = polarisation_filter_experiment.make_labctl_script()
        assert result is not None

    def test_polarisation_filter_calibration(
        self, polarisation_filter_calibration_experiment
    ):
        result = polarisation_filter_calibration_experiment.make_labctl_script()
        assert result is not None

    def test_translation_stage(self, translation_stage_experiment):
        result = translation_stage_experiment.make_labctl_script()
        assert result is not None

    def test_polarised_translation_stage(self, polarised_translation_stage_experiment):
        result = polarised_translation_stage_experiment.make_labctl_script()
        assert result is not None

    def test_raman_2d(self, raman_2d_experiment):
        result = raman_2d_experiment.make_labctl_script()
        assert result is not None

    def test_pulsed_microwave_timesweep(self, pulsed_microwave_timesweep):
        result = pulsed_microwave_timesweep.make_labctl_script()
        assert result is not None

    def test_laser_timesweep_not_implemented(self):
        with pytest.raises((NotImplementedError, TypeError)):
            LaserTimesweepExperiment(
                t0=0.0,
                delta_t=[0.0, 1e-6],
                **_base_camera_kwargs(n_frames=[1, 1]),
            )


# ---------------------------------------------------------------------------
# Tests – make_postprocessing_script
# ---------------------------------------------------------------------------


class TestMakePostprocessingScript:
    def test_simple_camera(self, simple_camera_experiment):
        result = simple_camera_experiment.make_postprocessing_script()
        assert isinstance(result, str)

    def test_camera_timesweep(self, camera_timesweep_experiment):
        result = camera_timesweep_experiment.make_postprocessing_script()
        assert isinstance(result, str)

    def test_polarisation_filter(self, polarisation_filter_experiment):
        result = polarisation_filter_experiment.make_postprocessing_script()
        assert isinstance(result, str)

    def test_polarisation_filter_calibration(
        self, polarisation_filter_calibration_experiment
    ):
        result = polarisation_filter_calibration_experiment.make_postprocessing_script()
        assert isinstance(result, str)

    def test_translation_stage(self, translation_stage_experiment):
        result = translation_stage_experiment.make_postprocessing_script()
        assert isinstance(result, str)

    def test_polarised_translation_stage(self, polarised_translation_stage_experiment):
        result = polarised_translation_stage_experiment.make_postprocessing_script()
        assert isinstance(result, str)

    def test_raman_2d(self, raman_2d_experiment):
        result = raman_2d_experiment.make_postprocessing_script()
        assert isinstance(result, str)

    def test_pulsed_microwave_timesweep(self, pulsed_microwave_timesweep):
        result = pulsed_microwave_timesweep.make_postprocessing_script()
        assert isinstance(result, str)
