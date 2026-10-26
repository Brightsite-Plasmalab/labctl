Calibration
============
Some standard calibrations are included in the **LabCTL** package.

Laser timing calibration
-------------------------
To calibrate the laser timing, run a :class:`CameraTimesweepExperiment<labctl.experiments.camera_timesweep.CameraTimesweepExperiment>`,
the data is then analysed using :func:`analyse_camera_timesweep_intensity<labctl.analysis.analyse_camera_timesweep_intensity>`.

The output is a graph of total intensity over time, and it prints the camera timing with the highest intensity.


Polarisation filter calibration
--------------------------------
To calibrate the angle of the polarisation filter, run a :class:`PolarisationFilterSweepExperiment<labctl.experiments.polarisation_sweep.PolarisationFilterSweepExperiment>`,
the data is then analysed using :func:`analyse_polarisation_calibration<labctl.analysis.analyse_polarisation_calibration>`.


Multitrack calibration
-----------------------
The Andor camera has the capability to output a spectrum for each fiber, but for this you need the pixel bounds for each
fiber. The function :func:`multitrack_calibration<labctl.analysis.multitrack_calibration>` can be used to find these bounds
and output a file for the Andor software to read.

