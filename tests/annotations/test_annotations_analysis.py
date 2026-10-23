import pytest

from labctl.analysis.plotter import PlotVsWavelengthKwargs, plot_vs_wavelength
from labctl.analysis.read_data import (
    GetDataGluedKwargs,
    GetDataKwargs,
    get_data,
    get_data_glued,
)

from ._test_annotations import typed_dict_func_class_same

functions_plus_kwargs = [
    (get_data, GetDataKwargs),
    (get_data_glued, GetDataGluedKwargs),
    (plot_vs_wavelength, PlotVsWavelengthKwargs),
]


@pytest.mark.parametrize("test_func, test_typed_dict", functions_plus_kwargs)
def test_typed_dict_func_same(test_func, test_typed_dict):
    typed_dict_func_class_same(test_func, test_typed_dict, 'func')