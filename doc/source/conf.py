# Configuration file for the Sphinx_PyAEDT documentation builder.

# -- Project information -----------------------------------------------------
import datetime
import os
import pathlib
import sys
import warnings

import pyvista
import numpy as np
import json
from sphinx_gallery.sorting import FileNameSortKey
from ansys_sphinx_theme import (ansys_favicon, 
                                get_version_match, pyansys_logo_black,
                                watermark, 
                                ansys_logo_white, 
                                ansys_logo_white_cropped, latex, 
                                get_autoapi_templates_dir_relative_path)
from importlib import import_module
from pprint import pformat
from docutils.parsers.rst import Directive
from docutils import nodes
from sphinx import addnodes

# <-----------------Override the sphinx pdf builder---------------->
# Some pages do not render properly as per the expected Sphinx LaTeX PDF signature.
# This issue can be resolved by migrating to the autoapi format.
# Additionally, when documenting images in formats other than the supported ones, 
# make sure to specify their types.
from sphinx.builders.latex import LaTeXBuilder
LaTeXBuilder.supported_image_types = ["image/png", "image/pdf", "image/svg+xml", "image/webp" ]

from sphinx.writers.latex import CR
from sphinx.writers.latex import LaTeXTranslator
from docutils.nodes import Element

def visit_desc_content(self, node: Element) -> None:
    self.body.append(CR + r'\pysigstopsignatures')
    self.in_desc_signature = False
LaTeXTranslator.visit_desc_content = visit_desc_content

# <----------------- End of sphinx pdf builder override---------------->

class PrettyPrintDirective(Directive):
    """Renders a constant using ``pprint.pformat`` and inserts into the document."""
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
    except:
        exclude = False
    exclude2 = True if name.startswith("_") else False
    return True if (skip or exclude or exclude2) else None  # Can interfere with subsequent skip functions.
    # return True if exclude else None


def setup(app):
    app.add_directive('pprint', PrettyPrintDirective)
    app.connect('autodoc-skip-member', autodoc_skip_member)


local_path = os.path.dirname(os.path.realpath(__file__))
module_path = pathlib.Path(local_path)
root_path = module_path.parent.parent
try:
    from pyaedt import __version__
except ImportError:

    sys.path.append(os.path.abspath(os.path.join(local_path)))
    sys.path.append(os.path.join(root_path))
    from pyaedt import __version__


project = "PyAEDT"
copyright = f"(c) {datetime.datetime.now().year} ANSYS, Inc. All rights reserved"
author = "Ansys Inc."
cname = os.getenv("DOCUMENTATION_CNAME", "nocname.com")

# Check for the local config file, otherwise use default desktop configuration
local_config_file = os.path.join(local_path, "local_config.json")
if os.path.exists(local_config_file):
    with open(local_config_file) as f:
        config = json.load(f)
else:
    config = {"run_examples": True}

release = version = __version__

os.environ["PYAEDT_NON_GRAPHICAL"] = "1"
os.environ["PYAEDT_DOC_GENERATION"] = "1"

# -- General configuration ---------------------------------------------------

# Add any Sphinx_PyAEDT extension module names here as strings. They can be
# extensions coming with Sphinx_PyAEDT (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.intersphinx",
    "sphinx.ext.autodoc",
    "sphinx.ext.todo",
    "sphinx.ext.autosummary",
    "sphinx.ext.intersphinx",
    "sphinx.ext.coverage",
    "sphinx_copybutton",
    "sphinx_design",
    "sphinx_jinja",
    "recommonmark",
    "sphinx.ext.graphviz",
    "sphinx.ext.mathjax",
    "sphinx.ext.inheritance_diagram",
    "numpydoc",
    "ansys_sphinx_theme.extension.linkcode",
    "autoapi.extension",
]

# Intersphinx mapping
intersphinx_mapping = {
    "python": ("https://docs.python.org/3.10", None),
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
    r"HistoryProps.",  # bad RT05 because of the base class named OrderedDict
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


# Manage errors
pyvista.set_error_output_file("errors.txt")

# Ensure that offscreen rendering is used for docs generation
pyvista.OFF_SCREEN = True

# Preferred plotting style for documentation
# pyvista.set_plot_theme('document')

# must be less than or equal to the XVFB window size
pyvista.global_theme["window_size"] = np.array([1024, 768])

# Save figures in specified directory
pyvista.FIGURE_PATH = os.path.join(os.path.abspath("./images/"), "auto-generated/")
if not os.path.exists(pyvista.FIGURE_PATH):
    os.makedirs(pyvista.FIGURE_PATH)

# gallery build requires AEDT install
if os.name != "posix" and "PYAEDT_CI_NO_EXAMPLES" not in os.environ:

    # suppress annoying matplotlib bug
    warnings.filterwarnings(
        "ignore",
        category=UserWarning,
        message="Matplotlib is currently using agg, which is a non-GUI backend, so cannot show the figure.",
    )

    # necessary for pyvista when building the sphinx gallery
    pyvista.BUILDING_GALLERY = True

    if config["run_examples"]:
        extensions.append("sphinx_gallery.gen_gallery")

        sphinx_gallery_conf = {
            # convert rst to md for ipynb
            "pypandoc": True,
            # path to your examples scripts
            "examples_dirs": ["../../examples/"],
            # path where to save gallery generated examples
            "gallery_dirs": ["examples"],
            # Patter to search for examples files
            "filename_pattern": r"\.py",
            # Remove the "Download all examples" button from the top level gallery
            "download_all_examples": False,
            # Sort gallery examples by file name instead of number of lines (default)
            "within_subsection_order": FileNameSortKey,
            # directory where function granular galleries are stored
            "backreferences_dir": None,
            # Modules for which function level galleries are created.  In
            "doc_module": "ansys-pyaedt",
            "image_scrapers": ("pyvista", "matplotlib"),
            "ignore_pattern": "flycheck*",
            "thumbnail_size": (350, 350),
            # 'first_notebook_cell': ("%matplotlib inline\n"
            #                         "from pyvista import set_plot_theme\n"
            #                         "set_plot_theme('document')"),
        }

jinja_contexts = {
    "main_toctree": {
        "run_examples": config["run_examples"],
    },
}

# -- Options for HTML output -------------------------------------------------
html_short_title = html_title = "PyAEDT"
html_theme = "ansys_sphinx_theme"
html_logo = pyansys_logo_black
html_context = {
    "github_user": "ansys",
    "github_repo": "pyaedt",
    "github_version": "main",
    "doc_path": "doc/source",
}

# specify the location of your github repo
html_theme_options = {
    "github_url": "https://github.com/ansys/pyaedt",
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
    "use_meilisearch": {
        "api_key": os.getenv("MEILISEARCH_PUBLIC_API_KEY", ""),
        "index_uids": {
            f"pyaedt-v{get_version_match(__version__).replace('.', '-')}": "PyAEDT",
            f"pyedb-v{get_version_match(__version__).replace('.', '-')}": "EDB API",
        },
    },
}

html_static_path = ["_static"]

# These paths are either relative to html_static_path
# or fully qualified paths (eg. https://...)
html_css_files = [
    'custom.css',
]


# -- Options for HTMLHelp output ---------------------------------------------

# Output file base name for HTML help builder.
htmlhelp_basename = "pyaedtdoc"

# -- Options for LaTeX output ------------------------------------------------
# additional logos for the latex coverpage
latex_additional_files = [watermark, ansys_logo_white, ansys_logo_white_cropped]

# change the preamble of latex with customized title page
# variables are the title of pdf, watermark
latex_elements = {"preamble": latex.generate_preamble(html_title)}

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
    (
        master_doc,
        f"{project}-Documentation-{__version__}.tex",
        f"{project} Documentation",
        author,
        "manual",
    ),
]

def prepare_jinja_env(jinja_env) -> None:
    """
    Customize the jinja env.

    Notes
    -----
    See https://jinja.palletsprojects.com/en/3.0.x/api/#jinja2.Environment
    """
    jinja_env.globals["project_name"] = project


autoapi_prepare_jinja_env = prepare_jinja_env


autoapi_type = "python"
autoapi_dirs = ["../../pyaedt/"]
autoapi_options = [
    "members",
    "undoc-members",
    "show-inheritance",
    "show-module-summary",
    "special-members",
]
autoapi_template_dir = get_autoapi_templates_dir_relative_path(pathlib.Path(__file__))
suppress_warnings = ["autoapi.python_import_resolution"]
exclude_patterns = [
    "autoapi",
    "**/ExampleData*",
    "**/LaunchWorkbench*",
]
autoapi_root = "API"
autoapi_python_use_implicit_namespaces = True
autoapi_render_in_single_page = ["class", "enum", "exception"]