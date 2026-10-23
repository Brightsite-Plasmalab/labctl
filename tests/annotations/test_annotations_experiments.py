import pytest

from labctl.experiments.base import BaseExperiment, BaseExperimentKwargs
from labctl.experiments.camera import BaseCameraExperiment, BaseCameraExperimentKwargs
from labctl.experiments.camera_timesweep import (
    CameraTimesweepExperiment,
    CameraTimesweepExperimentKwargs,
)
from labctl.experiments.experiment_polarised_translation_stage import (
    PolarisedTranslationStageExperiment,
    PolarisedTranslationStageExperimentKwargs,
)
from labctl.experiments.filtered_translation_stage import (
    FilteredTranslationStageExperiment,
    FilteredTranslationStageExperimentKwargs,
)
from labctl.experiments.polarisation import (
    PolarisationFilterExperiment,
    PolarisationFilterExperimentKwargs,
)
from labctl.experiments.polarisation_sweep import (
    PolarisationFilterSweepExperiment,
    PolarisationFilterSweepExperimentKwargs,
)
from labctl.experiments.pulsed_microwave_timesweep import (
    PulsedMicrowaveTimesweep,
    PulsedMicrowaveTimesweepKwargs,
)
from labctl.experiments.raman_2d import Raman2DExperiment, Raman2DExperimentKwargs
from labctl.experiments.translation_stage import (
    TranslationStageExperiment,
    TranslationStageExperimentKwargs,
)

from ._test_annotations import typed_dict_func_class_same

experiments_plus_kwargs = [
    (BaseExperiment, BaseExperimentKwargs),
    (BaseCameraExperiment, BaseCameraExperimentKwargs),
    (CameraTimesweepExperiment, CameraTimesweepExperimentKwargs),
    (PolarisationFilterSweepExperiment, PolarisationFilterSweepExperimentKwargs),
    (PolarisationFilterExperiment, PolarisationFilterExperimentKwargs),
    (TranslationStageExperiment, TranslationStageExperimentKwargs),
    (Raman2DExperiment, Raman2DExperimentKwargs),
    (PulsedMicrowaveTimesweep, PulsedMicrowaveTimesweepKwargs),
    (PolarisedTranslationStageExperiment, PolarisedTranslationStageExperimentKwargs),
    (FilteredTranslationStageExperiment, FilteredTranslationStageExperimentKwargs)
]

@pytest.mark.parametrize("test_class, test_typed_dict", experiments_plus_kwargs)
def test_typed_dict_class_init_same(test_class, test_typed_dict):
    typed_dict_func_class_same(test_class, test_typed_dict, 'class')
