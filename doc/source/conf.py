# Configuration file for the Sphinx_PyAEDT documentation builder.

# -- Project information -----------------------------------------------------
import datetime
import os
import pathlib
import sys
import warnings

import numpy as np
from sphinx_gallery.sorting import FileNameSortKey
from ansys_sphinx_theme import (ansys_favicon, 
                                get_version_match,
                                watermark, 
                                ansys_logo_white, 
                                ansys_logo_white_cropped, latex)
from importlib import import_module
from pprint import pformat
from docutils.parsers.rst import Directive
from docutils import nodes
from sphinx import addnodes
from sphinx.util import logging
import shutil

# <-----------------Override the sphinx pdf builder---------------->
# Some pages do not render properly as per the expected Sphinx LaTeX PDF signature.
# This issue can be resolved by migrating to the autoapi format.
# Additionally, when documenting images in formats other than the supported ones, 
# make sure to specify their types.
from sphinx.builders.latex import LaTeXBuilder
LaTeXBuilder.supported_image_types = ["image/png", "image/pdf", "image/svg+xml"]

from sphinx.writers.latex import CR
from sphinx.writers.latex import LaTeXTranslator
from docutils.nodes import Element

def visit_desc_content(self, node: Element) -> None:
    self.body.append(CR + r'\pysigstopsignatures')
    self.in_desc_signature = False
LaTeXTranslator.visit_desc_content = visit_desc_content

# <----------------- End of sphinx pdf builder override---------------->


logger = logging.getLogger(__name__)


# Sphinx event hooks

class PrettyPrintDirective(Directive):
    """Renders a constant using ``pprint.pformat`` and inserts it into the document."""
    required_arguments = 1

    def run(self):
        module_path, member_name = self.arguments[0].rsplit('.', 1)

        member_data = getattr(import_module(module_path), member_name)
        code = pformat(member_data, 2, width=68)

        literal = nodes.literal_block(code, code)
        literal['language'] = 'python'

        return [
                addnodes.desc_name(text=member_name),
                addnodes.desc_content('', literal)
        ]


def autodoc_skip_member(app, what, name, obj, skip, options):
    try:
        exclude = True if ".. deprecated::" in obj.__doc__ else False
    except Exception:
        exclude = False
    exclude2 = True if name.startswith("_") else False
    return True if (skip or exclude or exclude2) else None  # Can interfere with subsequent skip functions.
    # return True if exclude else None


def directory_size(directory_path):
    """Compute the size (in megabytes) of a directory."""
    res = 0
    for path, _, files in os.walk(directory_path):
        for f in files:
            fp = os.path.join(path, f)
            res += os.stat(fp).st_size
    # Convert in megabytes
    res /= 1e6
    return res

def remove_doctree(app, exception):
    """Remove the ``.doctree`` directory created during the documentation build."""

    # Keep the ``doctree`` directory to avoid creating it twice. This is typically helpful in CI/CD
    # where we want to build both HTML and PDF pages.
    if bool(int(os.getenv("SPHINXBUILD_KEEP_DOCTREEDIR", "0"))):
        logger.info(f"Keeping directory {app.doctreedir}.")
    else:
        size = directory_size(app.doctreedir)
        logger.info(f"Removing doctree {app.doctreedir} ({size} MB).")
        shutil.rmtree(app.doctreedir, ignore_errors=True)
        logger.info(f"Doctree removed.")

def setup(app):
    app.add_directive('pprint', PrettyPrintDirective)
    app.connect('autodoc-skip-member', autodoc_skip_member)
    app.connect('build-finished', remove_doctree)


local_path = os.path.dirname(os.path.realpath(__file__))
module_path = pathlib.Path(local_path)
root_path = module_path.parent.parent
try:
    from ansys.aedt.core import __version__
except ImportError:

    sys.path.append(os.path.abspath(os.path.join(local_path)))
    sys.path.append(os.path.join(root_path))
    from ansys.aedt.core import __version__

from ansys.aedt.core import is_windows

project = "PyAEDT"
copyright = f"(c) {datetime.datetime.now().year} ANSYS, Inc. All rights reserved"
author = "Ansys Inc."
cname = os.getenv("DOCUMENTATION_CNAME", "nocname.com")
switcher_version = get_version_match(__version__)
release = version = __version__

os.environ["PYAEDT_NON_GRAPHICAL"] = "1"
os.environ["PYAEDT_DOC_GENERATION"] = "1"


# -- General configuration ---------------------------------------------------

# Add any Sphinx_PyAEDT extension module names here as strings. They can be
# extensions coming with Sphinx_PyAEDT (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "ansys_sphinx_theme.extension.linkcode",
    "numpydoc",
    "recommonmark",
    "sphinx.ext.autodoc",
    "sphinx.ext.autosummary",
    "sphinx.ext.coverage",
    "sphinx.ext.graphviz",
    "sphinx.ext.imgconverter",
    "sphinx.ext.inheritance_diagram",
    "sphinx.ext.intersphinx",
    "sphinx.ext.mathjax",
    "sphinx.ext.todo",
    "sphinx_copybutton",
    "sphinx_design",
]

# Intersphinx mapping
intersphinx_mapping = {
    "python": ("https://docs.python.org/3.11", None),
    "scipy": ("https://docs.scipy.org/doc/scipy/reference", None),
    "numpy": ("https://numpy.org/devdocs", None),
    "matplotlib": ("https://matplotlib.org/stable", None),
    "imageio": ("https://imageio.readthedocs.io/en/stable", None),
    "pandas": ("https://pandas.pydata.org/pandas-docs/stable", None),
    "pytest": ("https://docs.pytest.org/en/stable", None),
}


toc_object_entries_show_parents = "hide"

html_show_sourcelink = True

# numpydoc configuration
numpydoc_use_plots = True
numpydoc_show_class_members = False
numpydoc_xref_param_type = True
numpydoc_validate = True
numpydoc_validation_checks = {
    # general
    "GL06",  # Found unknown section
    "GL07",  # Sections are in the wrong order.
    "GL08",  # The object does not have a docstring
    "GL09",  # Deprecation warning should precede extended summary
    "GL10",  # reST directives {directives} must be followed by two colons
    # Return
    "RT04", # Return value description should start with a capital letter"
    "RT05", # Return value description should finish with "."
    # Summary
    "SS01",  # No summary found
    "SS02",  # Summary does not start with a capital letter
    "SS03",  # Summary does not end with a period
    "SS04",  # Summary contains heading whitespaces
    "SS05",  # Summary must start with infinitive verb, not third person
    # Parameters
    "PR10",  # Parameter "{param_name}" requires a space before the colon
    # separating the parameter name and type",
}

numpydoc_validation_exclude = {  # set of regex
    r"\.AEDTMessageManager.add_message$",  # bad SS05
    r"\.Modeler3D\.create_choke$",  # bad RT05
    r"HistoryProps.",  # bad RT05 because of the base class named dict
}

# Favicon
html_favicon = ansys_favicon

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# disable generating the sphinx nested documentation
if "PYAEDT_CI_NO_AUTODOC" in os.environ:
    templates_path.clear()


# Copy button customization ---------------------------------------------------
# exclude traditional Python prompts from the copied code
copybutton_prompt_text = r">>> ?|\.\.\. "
copybutton_prompt_is_regexp = True


# The language for content autogenerated by Sphinx_PyAEDT. Refer to documentation
# for a list of supported languages.
#
# This is also used if you do content translation via gettext catalogs.
# Usually you set "language" from the command line for these cases.
language = "en"

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "sphinx_boogergreen_theme_1", "Thumbs.db", ".DS_Store", "*.txt"]


inheritance_graph_attrs = dict(rankdir="RL", size='"8.0, 10.0"', fontsize=14, ratio="compress")
inheritance_node_attrs = dict(shape="ellipse", fontsize=14, height=0.75, color="dodgerblue1", style="filled")


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
# html_static_path = ['_static']

source_suffix = {".rst": "restructuredtext", ".md": "markdown"}

# The master toctree document.
master_doc = "index"

# The name of the Pygments (syntax highlighting) style to use.
pygments_style = "sphinx"


# gallery build requires AEDT install
# if is_windows and bool(os.getenv("PYAEDT_CI_RUN_EXAMPLES", "0")):

# -- Options for HTML output -------------------------------------------------
html_short_title = html_title = "PyAEDT"
html_theme = "ansys_sphinx_theme"
html_context = {
    "github_user": "ansys",
    "github_repo": "pyaedt",
    "github_version": "main",
    "doc_path": "doc/source",
}

# specify the location of your github repo
html_theme_options = {
    "logo": "pyansys",
    "github_url": "https://github.com/ansys/pyaedt",
    "navigation_with_keys": False,
    "show_prev_next": False,
    "show_breadcrumbs": True,
    "collapse_navigation": True,
    "use_edit_page_button": True,
    "additional_breadcrumbs": [
        ("PyAnsys", "https://docs.pyansys.com/"),
    ],
    "icon_links": [
        {
            "name": "Support",
            "url": "https://github.com/ansys/pyaedt/discussions",
            "icon": "fa fa-comment fa-fw",
        },
    ],
    "switcher": {
        "json_url": f"https://{cname}/versions.json",
        "version_match": get_version_match(__version__),
    },
    "collapse_navigation": True,
    "navigation_with_keys": True,
    "static_search": {
        "threshold": 0.5,
        "minMatchCharLength": 2,
        "limite": 10,
        "ignoreLocation": True,
    },
    "cheatsheet": {
        "file": "cheatsheet/cheat_sheet.qmd",
        "title": "PyAEDT cheat sheet",
    },
}

# # Add button to download PDF
# html_theme_options["icon_links"].append(
#     {
#         "name": "Download documentation in PDF",
#         # NOTE: Changes to this URL must be reflected in CICD documentation build
#         "url": f"https://{cname}/version/{switcher_version}/_static/assets/download/pyaedt.pdf",
#         # noqa: E501
#         "icon": "fa fa-file-pdf fa-fw",
#     }
# )

html_static_path = ["_static"]

# These paths are either relative to html_static_path
# or fully qualified paths (eg. https://...)
html_css_files = [
    'custom.css',
]

# -- Options for LaTeX output ------------------------------------------------

# Additional logos for the latex coverpage
latex_additional_files = [watermark, ansys_logo_white, ansys_logo_white_cropped]

# Change the preamble of latex with customized title page
# variables are the title of pdf, watermark
latex_elements = {"preamble": latex.generate_preamble(html_title)}

linkcheck_ignore = [
    r"https://download.ansys.com/",
]

# If we are on a release, we have to ignore the "release" URLs, since it is not
# available until the release is published.
if switcher_version != "dev":
    linkcheck_ignore.append(
        f"https://github.com/ansys/pyaedt/releases/tag/v{__version__}"
    )  # noqa: E501