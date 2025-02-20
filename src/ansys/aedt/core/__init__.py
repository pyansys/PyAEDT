# -*- coding: utf-8 -*-
#
# Copyright (C) 2021 - 2025 ANSYS, Inc. and/or its affiliates.
# SPDX-License-Identifier: MIT
#
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import sys
import warnings

if os.name == "nt":
    os.environ["PYTHONMALLOC"] = "malloc"

LATEST_DEPRECATED_PYTHON_VERSION = (3, 9)
PYTHON_VERSION_WARNING = (
    "As part of our ongoing efforts to align with the Python Scientific Community's "
    "best practices, we are moving towards adopting SPEC 0000 "
    "(https://scientific-python.org/specs/spec-0000/). To ensure compatibility and "
    "take full advantage of the latest features and improvements, we strongly "
    "recommend updating the Python version being used."
)
DOTNET_LINUX_WARNING = (
    "Due to compatibility issues between .NET Core and libssl on some Linux versions, "
    "for example Ubuntu 22.04, we are going to stop depending on `dotnetcore2`."
    "Instead of using this package which embeds .NET Core 3, users will be required to "
    "install .NET themselves. For more information, see "
    "https://aedt.docs.pyansys.com/version/stable/release_1_0.html#dotnet-changes-in-linux"
)


def deprecation_warning():
    """Warning message informing users that some Python versions are deprecated in PyAEDT."""
    # Store warnings showwarning
    existing_showwarning = warnings.showwarning

    # Define and use custom showwarning
    def custom_show_warning(message, category, filename, lineno, file=None, line=None):
        """Define and use custom warning to remove <stdin>:loc: pattern."""
        print(f"{category.__name__}: {message}")

    warnings.showwarning = custom_show_warning

    current_python_version = sys.version_info[:2]
    if current_python_version <= LATEST_DEPRECATED_PYTHON_VERSION:
        warnings.warn(PYTHON_VERSION_WARNING, FutureWarning)

    # Restore warnings showwarning
    warnings.showwarning = existing_showwarning


deprecation_warning()

#

pyaedt_path = os.path.dirname(__file__)
__version__ = "0.15.dev0"
version = __version__

# isort: off
# Settings have to be imported before importing other PyAEDT modules
from ansys.aedt.core.generic.general_methods import settings
from ansys.aedt.core.generic.general_methods import inner_project_settings

# isort: on

if not (".NETFramework" in sys.version):  # pragma: no cover
    import ansys.aedt.core.downloads as downloads
from ansys.aedt.core.edb import Edb  # nosec
from ansys.aedt.core.edb import Siwave  # nosec
from ansys.aedt.core.generic import constants
import ansys.aedt.core.generic.data_handlers as data_handler
from ansys.aedt.core.generic.design_types import Circuit
from ansys.aedt.core.generic.design_types import CircuitNetlist
from ansys.aedt.core.generic.design_types import Desktop
from ansys.aedt.core.generic.design_types import Emit
from ansys.aedt.core.generic.design_types import FilterSolutions
from ansys.aedt.core.generic.design_types import Hfss
from ansys.aedt.core.generic.design_types import Hfss3dLayout
from ansys.aedt.core.generic.design_types import Icepak
from ansys.aedt.core.generic.design_types import Maxwell2d
from ansys.aedt.core.generic.design_types import Maxwell3d
from ansys.aedt.core.generic.design_types import MaxwellCircuit
from ansys.aedt.core.generic.design_types import Mechanical
from ansys.aedt.core.generic.design_types import Q2d
from ansys.aedt.core.generic.design_types import Q3d
from ansys.aedt.core.generic.design_types import Rmxprt
from ansys.aedt.core.generic.design_types import Simplorer
from ansys.aedt.core.generic.design_types import TwinBuilder
from ansys.aedt.core.generic.design_types import get_pyaedt_app
from ansys.aedt.core.generic.design_types import launch_desktop
import ansys.aedt.core.generic.general_methods as general_methods
from ansys.aedt.core.generic.general_methods import _retry_ntimes
from ansys.aedt.core.generic.general_methods import generate_unique_folder_name
from ansys.aedt.core.generic.general_methods import generate_unique_name
from ansys.aedt.core.generic.general_methods import generate_unique_project_name
from ansys.aedt.core.generic.general_methods import inside_desktop
from ansys.aedt.core.generic.general_methods import is_linux
from ansys.aedt.core.generic.general_methods import is_windows
from ansys.aedt.core.generic.general_methods import online_help
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.generic.numbers import Quantity
