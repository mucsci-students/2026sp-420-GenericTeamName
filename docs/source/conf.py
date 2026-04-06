# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

import os
import sys

project = 'Scheduler GUI'
copyright = '2026, GenericTeamName'
author = 'GenericTeamName'
release = '4.2'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = []

templates_path = ['_templates']
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'alabaster'
html_static_path = ['_static']

# Point to the root directory where main.py and the /app folder live
sys.path.insert(0, os.path.abspath('../../'))

extensions = [
    'sphinx.ext.autodoc',      # Pulls documentation from docstrings
    'sphinx.ext.viewcode',     # Adds links to highlighted source code
    'sphinx.ext.napoleon',     # Supports Google/NumPy style docstrings
]

html_theme = 'sphinx_rtd_theme'
