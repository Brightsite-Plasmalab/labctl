import pathlib

from labctl.analysis import analyse_polarisation_calibration

base_loc = r"D:\26_08_17\cali"

f_pickle = pathlib.Path(rf"{base_loc}\angle_calibration.pkl")
f_data = pathlib.Path(rf"{base_loc}\angle_calibration2.sif")

analyse_polarisation_calibration(f_data, f_pickle)