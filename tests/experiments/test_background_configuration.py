# TODO: Look at automatic generated tests
import numpy as np
import pytest

from labctl.experiments.camera import BackgroundConfiguration
from labctl.experiments.camera_timesweep import CameraTimesweepExperiment


@pytest.mark.parametrize(
    ("config", "foreground_num", "expected"),
    [
        (
            BackgroundConfiguration.EVERY_FRAME,
            3,
            [
                "foreground",
                "background",
                "foreground",
                "background",
                "foreground",
                "background",
            ],
        ),
        (BackgroundConfiguration.NONE, 3, ["foreground", "foreground", "foreground"]),
        (
            BackgroundConfiguration.BEGIN,
            3,
            ["background", "foreground", "foreground", "foreground"],
        ),
        (
            BackgroundConfiguration.END,
            3,
            ["foreground", "foreground", "foreground", "background"],
        ),
        (
            BackgroundConfiguration.BEGIN_MIDDLE_END,
            4,
            [
                "background",
                "foreground",
                "foreground",
                "background",
                "foreground",
                "foreground",
                "background",
            ],
        ),
        (
            BackgroundConfiguration.BEGIN_MIDDLE_END,
            5,
            [
                "background",
                "foreground",
                "foreground",
                "background",
                "foreground",
                "foreground",
                "foreground",
                "background",
            ],
        ),
        (
            BackgroundConfiguration.BEGIN_END,
            3,
            ["background", "foreground", "foreground", "foreground", "background"],
        ),
    ],
)
def test_make_name_list_expected_sequences(
    config: BackgroundConfiguration, foreground_num: int, expected: list[str]
):
    assert config.make_name_list(foreground_num) == expected


@pytest.mark.parametrize("config", list(BackgroundConfiguration))
def test_make_name_list_rejects_zero_foreground_frames(config: BackgroundConfiguration):
    assert config.make_name_list(0) == []


@pytest.mark.parametrize(
    ("config", "foreground_num"),
    [
        (BackgroundConfiguration.EVERY_FRAME, 3),
        (BackgroundConfiguration.NONE, 1),
        (BackgroundConfiguration.BEGIN, 2),
        (BackgroundConfiguration.END, 2),
        (BackgroundConfiguration.BEGIN_MIDDLE_END, 5),
        (BackgroundConfiguration.BEGIN_END, 2),
    ],
)
def test_measurement_count_matches_generated_names(
    config: BackgroundConfiguration, foreground_num: int
):
    names = config.make_name_list(foreground_num)
    assert config.measurement_count(foreground_num) == len(names)


@pytest.mark.parametrize(
    ("config"),
    [
        BackgroundConfiguration.EVERY_FRAME,
        BackgroundConfiguration.NONE,
        BackgroundConfiguration.BEGIN,
        BackgroundConfiguration.END,
        BackgroundConfiguration.BEGIN_MIDDLE_END,
        BackgroundConfiguration.BEGIN_END,
    ],
)
def test_measurement_count_rejects_zero_foreground_frames(
    config: BackgroundConfiguration,
):
    assert config.measurement_count(0) == 0


def test_invalid_int_value_cannot_be_converted_to_background_configuration():
    with pytest.raises(ValueError):
        BackgroundConfiguration(2)


def test_make_name_list_rejects_invalid_configuration_object():
    class InvalidBackgroundConfiguration:
        value = 999

        def __gt__(self, other):
            return False

        def __eq__(self, other):
            return False

    with pytest.raises(ValueError, match="Invalid BackgroundConfiguration value"):
        BackgroundConfiguration.make_name_list(InvalidBackgroundConfiguration(), 3)  # type: ignore[arg-type]


def test_postprocessing_indices_follow_generated_schedule_for_single_iteration():
    exp = object.__new__(CameraTimesweepExperiment)
    exp.file_name = "test"
    exp.short_explanation = ""
    exp.author = ""

    exp.n_frames = [2, 1]
    exp.n_iter = 1
    exp.t_exposure = 0.1
    exp.background_every = BackgroundConfiguration.BEGIN_END
    exp.camera_delay_optimum = 0.0
    exp.t0 = 0.0
    exp.delta_t = [0.0, 1.0]

    info = exp.make_postprocessing_info()

    iter0 = info["indices"]
    print(iter0)
    config0_foreground, config0_background = iter0[0]
    config1_foreground, config1_background = iter0[1]

    np.testing.assert_array_equal(config0_foreground, np.array([1, 2]))
    np.testing.assert_array_equal(config0_background, np.array([0, 3]))
    np.testing.assert_array_equal(config1_foreground, np.array([5]))
    np.testing.assert_array_equal(config1_background, np.array([4, 6]))
