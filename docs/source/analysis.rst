.. currentmodule:: labctl.analysis

Analysis
============
Analysis helpers for processing experiment output data.

Reading data
-------------
The :mod:`read_data<labctl.analysis.read_data>` module contains two functions to read experimental data from sif files
using the experimental information stored in pickle files. To read single measurements, use :func:`get_data`.
If you want to glue the multiple spectra together to get a wider wavelength range, use :func:`get_data_glued`.

Calibration
------------
Functions used for calibration analysis:

- :func:`analyse_camera_timesweep_intensity`
- :func:`analyse_polarisation_calibration`

Plotting
----------
This module also contains some simple plotting functions, these are located in the
:mod:`plotter<labctl.analysis.plotter>` submodule.
