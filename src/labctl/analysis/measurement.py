"""Measurement containers and axis-aware transformation helpers.

This module defines immutable dataclasses used to store spectral measurements,
including optional background and wavelength metadata, and provides utility
methods for axis reduction, wavelength selection, and background correction.
"""

from collections.abc import Collection, Sequence
from dataclasses import dataclass, fields
from typing import Any, Literal, Self, cast

import numpy as np

from labctl._type_hints import _acc_typehint
from labctl.analysis._numpy_funcs import _get_accumulator


@dataclass(frozen=True)
class BaseMeasurement:
    """Immutable measurement with optional background and wavelength metadata.

    Parameters
    ----------
    intensity : np.ndarray
        Measured data array.
    background : np.ndarray | None
        Background array with a shape compatible with ``intensity``.
    wavelengths : np.ndarray | None
        Wavelength axis values. Required when the last axis is named
        ``"width"``.
    axis_names : tuple[str, ...]
        Names of the data axes in the same order as ``intensity`` dimensions.
    """

    intensity: np.ndarray
    background: np.ndarray | None
    wavelengths: np.ndarray | None
    axis_names: tuple[str, ...]

    def __post_init__(self) -> None:
        """Validate internal consistency after dataclass initialization.

        Raises
        ------
        ValueError
            If the last axis is ``"width"`` while no wavelengths are provided.
        """
        if self.axis_names[-1] == "width" and self.wavelengths is None:
            raise ValueError("Wavelengths not provided")

    @property
    def has_background(self) -> bool:
        """Whether background data is available."""
        return self.background is not None

    @property
    def has_wavelengths(self) -> bool:
        """Whether the last axis corresponds to wavelength bins."""
        return self.axis_names[-1] == "width"

    def get_axis(self, name: str) -> int:
        """Return the integer index of a named axis.

        Parameters
        ----------
        name : str
            Axis name to look up.

        Returns
        -------
        int
            Position of ``name`` in ``axis_names``.

        Raises
        ------
        ValueError
            If ``name`` does not exist.
        """
        if name in self.axis_names:
            return self.axis_names.index(name)
        else:
            raise ValueError(f"Axis name `{name}` not found, valid names are {self.axis_names}")

    def _check_axis(self, index: int | Collection[int]) -> None:
        """Validate one or more axis indices.

        Parameters
        ----------
        index : int | Collection[int]
            Axis index or indices to validate.

        Raises
        ------
        ValueError
            If any axis is out of bounds.
        """
        dimensions = len(self.axis_names)
        if isinstance(index, int):
            index = (index,)

        for i in index:
            i = i % dimensions
            if i >= dimensions:
                raise ValueError(f"Axis {i} out of bounds for measurement with {dimensions} dimensions")

    def apply_over_axis(self, function: _acc_typehint, axis: str | Sequence[str] | int | Sequence[int]) -> Self:
        """Apply an accumulator over one or more axes.

        Parameters
        ----------
        function : _acc_typehint
            Reduction function identifier understood by
            :func:`labctl.analysis._numpy_funcs._get_accumulator`.
        axis : str | Sequence[str] | int | Sequence[int]
            Axis specifier(s), either by name or integer index.

        Returns
        -------
        Self
            New measurement instance with reduced dimensions.
        """
        if isinstance(axis, str | int):
            axes: tuple[str | int, ...] = (axis,)
        else:
            axes = tuple(cast(Sequence[str | int], axis))

        if isinstance(axes[0], str):
            axes_names: tuple[str, ...] = tuple(cast(Sequence[str], axes))
            axis_indices: tuple[int, ...] = tuple(self.get_axis(name) for name in axes_names)
        else:
            axis_indices = tuple(cast(Sequence[int], axes))
            axes_names = tuple(self.axis_names[i] for i in axis_indices)
            self._check_axis(axis_indices)

        accumulator = _get_accumulator(function, axis_indices, "function")

        new_intensity = accumulator(self.intensity)
        new_background = accumulator(self.background) if self.has_background else None
        new_axis_names = tuple(
            name for i, name in enumerate(self.axis_names) if i not in axis_indices
        )

        # If width is reduced away, wavelengths are no longer valid.
        new_wavelengths = None if "width" in axes_names else self.wavelengths
        return self._make_copy_with(new_intensity, new_background, new_wavelengths, new_axis_names)


    def _make_copy_with(
        self,
        new_intensity: np.ndarray,
        new_background: np.ndarray | None,
        new_wavelengths: np.ndarray | None,
        new_axis_names: tuple[str, ...],
    ) -> Self:
        """Create a shallowly-copied instance with updated core arrays.

        Parameters
        ----------
        new_intensity : np.ndarray
            Replacement intensity array.
        new_background : np.ndarray | None
            Replacement background array.
        new_wavelengths : np.ndarray | None
            Replacement wavelength array.
        new_axis_names : tuple[str, ...]
            Replacement axis names.

        Returns
        -------
        Self
            A new instance of the same concrete measurement type.
        """
        kwargs: dict[str, Any] = {
            f.name: getattr(self, f.name) for f in fields(self) if f.init
        }

        # Override the transformed fields.
        kwargs.update(
            intensity=new_intensity,
            background=new_background,
            wavelengths=new_wavelengths,
            axis_names=new_axis_names,
        )

        # Optional: shallow-copy dict metadata if present to avoid aliasing.
        for key, value in kwargs.items():
            if isinstance(value, dict):
                kwargs[key] = value.copy()

        return cast(Self, type(self)(**kwargs))


    def select_wavelengths(
        self,
        *,
        wav_min: float | None = None,
        wav_max: float | None = None,
        mask: np.ndarray,
    ) -> Self:
        """Select wavelength bins using value limits and a boolean mask.

        Parameters
        ----------
        wav_min : float | None, optional
            Lower wavelength bound. If ``None``, the minimum available
            wavelength is used.
        wav_max : float | None, optional
            Upper wavelength bound. If ``None``, the maximum available
            wavelength is used.
        mask : np.ndarray
            Boolean mask over the wavelength axis before applying bounds.

        Returns
        -------
        Self
            New measurement instance containing only selected wavelengths.

        Raises
        ------
        ValueError
            If wavelength metadata is missing or if ``mask`` length does not
            match the last data dimension.
        """
        if not self.has_wavelengths:
            raise ValueError("Data has no wavelengths")
        wavelengths = cast(np.ndarray, self.wavelengths)

        if len(mask) != self.intensity.shape[-1]:
            msg = f"`mask` incompatible with array shape. Got length {len(mask)}, expected {self.intensity.shape[-1]} (last dimension of data)."
            raise ValueError(msg)

        wav_min = wav_min or wavelengths.min()
        wav_max = wav_max or wavelengths.max()

        mask = mask & (wav_min <= wavelengths) & (wavelengths <= wav_max)

        background = self.background[..., mask] if self.has_background else None
        return self._make_copy_with(self.intensity[..., mask], background, wavelengths[mask], self.axis_names)


    def get_corrected_intensity(self, *, use_background: bool | Literal["auto"] = True) -> np.ndarray:
        """Return intensity with optional background subtraction.

        Parameters
        ----------
        use_background : bool | Literal["auto"], optional
            If ``True``, subtract background and raise if unavailable.
            If ``False``, always return raw intensity.
            If ``"auto"``, subtract only when background exists.

        Returns
        -------
        np.ndarray
            Corrected or raw intensity array.

        Raises
        ------
        ValueError
            If ``use_background`` is ``True`` and no background is present.
        """
        if use_background is True and not self.has_background:
            raise ValueError("No background data present.")

        if (not use_background) or not self.has_background:
            return self.intensity
        else:
            return self.intensity - self.background


@dataclass(frozen=True)
class Measurement(BaseMeasurement):
    """Measurement with single-acquisition metadata.

    Parameters
    ----------
    info : dict[str, Any]
        General metadata dictionary.
    sif_info : dict[str, Any]
        SIF-file specific metadata dictionary.
    """

    info: dict[str, Any]
    sif_info: dict[str, Any]


@dataclass(frozen=True)
class CombinedMeasurement(BaseMeasurement):
    """Measurement composed of multiple acquisitions.

    Parameters
    ----------
    infos : tuple[dict[str, Any], ...]
        Metadata entries for each source acquisition.
    sif_infos : tuple[dict[str, Any], ...]
        SIF metadata entries for each source acquisition.
    """

    infos: tuple[dict[str, Any], ...]
    sif_infos: tuple[dict[str, Any], ...]

    @staticmethod
    def from_measurement(measurement: Measurement) -> "CombinedMeasurement":
        """Create a combined measurement containing a single source.

        Parameters
        ----------
        measurement : Measurement
            Source measurement.

        Returns
        -------
        CombinedMeasurement
            Combined representation with one metadata entry.
        """
        return CombinedMeasurement(
            measurement.intensity,
            measurement.background,
            measurement.wavelengths,
            measurement.axis_names,
            (measurement.info,),
            (measurement.sif_info,),
        )