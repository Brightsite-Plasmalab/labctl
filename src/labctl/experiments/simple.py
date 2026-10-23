"""Simple single-configuration camera experiment."""

from typing_extensions import override

from labctl.experiments.camera import BaseCameraExperiment


class SimpleCameraExperiment(BaseCameraExperiment):
    """Camera experiment with exactly one no-op configuration."""

    @override
    def get_config_names(self) -> list[str]:
        """Return the single configuration name.

        Returns
        -------
        list[str]
            Single empty-string configuration label.
        """
        # Only one configuration
        return [""]

    @override
    def prepare_config(self, cmds, i: int) -> None:
        """No-op configuration hook for the single config.

        Parameters
        ----------
        cmds : Script
            Script command collector.
        i : int
            Configuration index.
        """
        # No configuration to prepare

    @override
    def make_postprocessing_info(self) -> dict[str, object]:
        """Build postprocessing metadata for a single fixed configuration.

        Returns
        -------
        dict[str, object]
            Metadata dictionary with no sweep variable.
        """
        return {
            **super().make_postprocessing_info(),
            "variable": None,
        }
