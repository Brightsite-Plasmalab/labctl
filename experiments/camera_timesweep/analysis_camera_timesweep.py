from labctl.analysis import analyse_camera_timesweep_intensity

base_loc = r"D:\26_08_21"
pickle_loc = rf"{base_loc}\labctl\OES_pulsed_test2.pkl"
sif_loc = rf"{base_loc}\OES_pulse_test2.sif"

analyse_camera_timesweep_intensity(sif_loc, pickle_loc)