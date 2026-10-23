from pathlib import Path

from experiments import BackgroundConfiguration
from labctl.experiments import PulsedMicrowaveTimesweep

pulse_len = 0.5/1020
delta_t = [0.1*pulse_len, 0.5*pulse_len, 0.9*pulse_len, 2*pulse_len - 30e-6]
print(delta_t)
# %%
dest_folder = Path(r"E:\26_08_25\labctl")

for name, num in (("perp", 5), ("para", 10)):
    experiment = PulsedMicrowaveTimesweep(
        t0 = 100e-9,
        MW_pulse_frequency=1020,
        channel_MW_trigger='E',
        delta_t=delta_t,
        background_every = BackgroundConfiguration.BEGIN_END,

        n_frames = num,
        t_exposure = 10,
        camera_reset_time = 0.1,

        dest_folder = dest_folder,
        camera_delay_optimum = 464e-9,
        file_name = f"pulse_microwave_{name}"
    )
    experiment.save_labctl_script(overwrite=True)
    experiment.save_postprocessing_info(overwrite=True)

# %%