from labctl.analysis.plotter import plot_vs_wavelength

sif_loc = r"D:\26_07_08\spec\S6_2_0to8.sif"
pkl_loc = r"D:\26_07_08\spec\raman\Raman_4s_12_0to8.pkl"

plot_vs_wavelength(sif_loc, pkl_loc, variable_key="translation_loc", show=True)
plot_vs_wavelength(sif_loc, pkl_loc, variable_key="alpha", show=True)

# %%