# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
import os
import sys
from footings_idi_model import __version__ as version

sys.path.insert(0, os.path.abspath("./.."))

# -- Project information -----------------------------------------------------

project = "Footings IDI Model"
copyright = "2020, Dustin Tindall"
author = "Dustin Tindall"

# The full version, including alpha/beta/rc tags
release = version

# -- Update NumpyDocString ---------------------------------------------------

# inspiration from
# https://michaelgoerz.net/notes/extending-sphinx-napoleon-docstring-sections.html
def _parse_steps_section(section):
    return ["Steps"]


from sphinx.ext.napoleon.docstring import NumpyDocstring


def parse_steps_section(self, section):
    return self._format_fields("steps", self._consume_fields())


NumpyDocstring._parse_steps_section = parse_steps_section


# def parse_dispatch_section(self, section):
#     return self._format_fields("dispatch", self._consume_fields())
#
#
# NumpyDocstring._parse_dispatch_section = parse_dispatch_section
#
#
# def parse_loaded_section(self, section):
#     return self._format_fields("loaded", self._consume_fields())
#
#
# NumpyDocstring._parse_loaded_section = parse_loaded_section


def patched_parse(self):
    self._sections["steps"] = self._parse_steps_section
    # self._sections["dispatch"] = self._parse_dispatch_section
    # self._sections["loaded"] = self._parse_loaded_section
    self._unpatched_parse()


NumpyDocstring._unpatched_parse = NumpyDocstring._parse
NumpyDocstring._parse = patched_parse

# -- General configuration ---------------------------------------------------


# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named "sphinx.ext.*") or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx.ext.autosummary",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "nbsphinx",
    "recommonmark",
    "sphinx_rtd_theme",
]
napoleon_use_param = True
napoleon_google_docstring = False
add_module_names = False

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store", "**.ipynb_checkpoints"]

# The master toctree document.
master_doc = "index"

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]

source_suffix = {
    ".rst": "restructuredtext",
    ".txt": "markdown",
    ".md": "markdown",
}
