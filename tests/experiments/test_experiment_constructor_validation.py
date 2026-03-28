# TODO: Look at automatic generated tests
import pytest

from labctl.experiments.polarisation_sweep import PolarisationFilterSweepExperiment
from labctl.experiments.pulsed_microwave import PulsedMicrowaveTimesweep


def _base_camera_kwargs(**overrides):
    kwargs = {
        "dest_folder": ".",
        "file_name": "test",
        "n_frames": [1, 1],
        "t_exposure": 0.1,
        "camera_delay_optimum": 0.0,
    }
    kwargs.update(overrides)
    return kwargs


def test_polarisation_calibration_rejects_n_frames_length_mismatch():
    with pytest.raises(ValueError, match="Length of `N_frames` must match"):
        PolarisationFilterSweepExperiment(
            alpha=[0.0, 45.0],
            **_base_camera_kwargs(n_frames=[1]),
        )


def test_polarisation_calibration_rejects_non_sized_n_frames():
    with pytest.raises(TypeError, match="N_frames"):
        PolarisationFilterSweepExperiment(
            alpha=[0.0, 45.0],
            **_base_camera_kwargs(n_frames=object()),
        )


def test_polarisation_calibration_rejects_invalid_background_configuration_value():
    with pytest.raises(ValueError):
        PolarisationFilterSweepExperiment(
            alpha=[0.0, 45.0],
            **_base_camera_kwargs(background_every=2),
        )


def test_pulsed_microwave_rejects_invalid_trigger_channel():
    with pytest.raises(ValueError, match="Invalid channel"):
        PulsedMicrowaveTimesweep(
            t0=100e-9,
            delta_t=[0.0, 10e-9],
            MW_pulse_frequency=60,
            channel_MW_trigger="B",
            **_base_camera_kwargs(),
        )


def test_pulsed_microwave_rejects_non_multiple_frequency(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(PulsedMicrowaveTimesweep, "laser_frequency", 30, raising=False)

    with pytest.raises(ValueError, match="multiple of the laser frequency"):
        PulsedMicrowaveTimesweep(
            t0=100e-9,
            delta_t=[0.0, 10e-9],
            MW_pulse_frequency=35,
            channel_MW_trigger="D",
            **_base_camera_kwargs(),
        )

