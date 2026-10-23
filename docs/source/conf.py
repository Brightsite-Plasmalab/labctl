# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html
import os
import sys
from pathlib import Path

from sphinx.ext import apidoc


ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'LabCTL'
copyright = '2026, CCE'
author = 'CCE'
release = '0.0.2'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.autosummary',
    'sphinx.ext.napoleon',
    'sphinx.ext.apidoc',
    'sphinx_autodoc_typehints',
]

always_document_param_types = True
add_module_names = False

autosummary_generate = True
# autosummary_imported_members = True
autosummary_ignore_module_all = False

autodoc_default_options = {
    'path': 'src/',
    'destination': 'docs/source/generated',
    "members": True,
    "undoc-members": False,   # set True if you want even undocumented members listed
    "show-inheritance": True,
    "inherited-members": False,
}

templates_path = ['_templates']
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "pydata_sphinx_theme"
html_static_path = ['_static']
