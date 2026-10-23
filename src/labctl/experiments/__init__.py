"""
Experiment classes used to write labctl files for lab automation.
"""

from labctl.experiments.background_config import (
    BackgroundConfiguration as BackgroundConfiguration,
)
from labctl.experiments.camera import BaseCameraExperiment as BaseCameraExperiment
from labctl.experiments.camera_timesweep import (
    CameraTimesweepExperiment as CameraTimesweepExperiment,
)
from labctl.experiments.experiment_polarised_translation_stage import (
    PolarisedTranslationStageExperiment as PolarisedTranslationStageExperiment,
)
from labctl.experiments.filtered_translation_stage import (
    FilteredTranslationStageExperiment as FilteredTranslationStageExperiment,
)
from labctl.experiments.polarisation import (
    PolarisationFilterExperiment as PolarisationFilterExperiment,
)
from labctl.experiments.polarisation_sweep import (
    PolarisationFilterSweepExperiment as PolarisationFilterSweepExperiment,
)
from labctl.experiments.pulsed_microwave_timesweep import (
    PulsedMicrowaveTimesweep as PulsedMicrowaveTimesweep,
)
from labctl.experiments.raman_2d import Raman2DExperiment as Raman2DExperiment
from labctl.experiments.simple import SimpleCameraExperiment as SimpleCameraExperiment
from labctl.experiments.translation_stage import (
    TranslationStageExperiment as TranslationStageExperiment,
)

__all__ = (
    "CameraTimesweepExperiment",
    "PolarisedTranslationStageExperiment",
    "FilteredTranslationStageExperiment",
    "PolarisationFilterExperiment",
    "PolarisationFilterSweepExperiment",
    "PulsedMicrowaveTimesweep",
    "Raman2DExperiment",
    "SimpleCameraExperiment",
    "TranslationStageExperiment",
)