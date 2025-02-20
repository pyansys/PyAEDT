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

"""This module contains the ``CircuitNetlist`` class."""

import os
import shutil

from ansys.aedt.core.application.analysis_circuit_netlist import AnalysisCircuitNetlist
from ansys.aedt.core.generic.filesystem import search_files
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler


class CircuitNetlist(AnalysisCircuitNetlist, object):
    """Provides the Circuit Netlist application interface.

    Parameters
    ----------
    project : str, optional
        Name of the project to select or the full path to the project
        or AEDTZ archive to open.  The default is ``None``, in which
        case an attempt is made to get an active project. If no
        projects are present, an empty project is created.
    design : str, optional
        Name of the design to select. The default is ``None``, in
        which case an attempt is made to get an active design. If no
        designs are present, an empty design is created.
    version : str, int, float, optional
        Version of AEDT to use. The default is ``None``, in which case
        the active version or latest installed version is  used.
        This parameter is ignored when Script is launched within AEDT.
        Examples of input values are ``251``, ``25.1``,``2025.1``,``"2025.1"``.
    non_graphical : bool, optional
        Whether to run AEDT in non-graphical mode. The default
        is ``False``, in which case AEDT is launched in graphical mode.
        This parameter is ignored when a script is launched within AEDT.
    new_desktop : bool, optional
        Whether to launch an instance of AEDT in a new thread, even if
        another instance of the ``specified_version`` is active on the
        machine.  The default is ``False``. This parameter is ignored when
        a script is launched within AEDT.
    close_on_exit : bool, optional
        Whether to release AEDT on exit. The default is ``False``.
    student_version : bool, optional
        Whether to open the AEDT student version. The default is ``False``.
        This parameter is ignored when Script is launched within AEDT.
    machine : str, optional
        Machine name to which connect the oDesktop Session. Works only in 2022 R2
        or later. The remote server must be up and running with the command
        `"ansysedt.exe -grpcsrv portnum"`. If a machine is `"localhost"`, the
        server also starts if not present.
    port : int, optional
        Port number on which to start the oDesktop communication on an already existing server.
        This parameter is ignored when creating a new server. It works only in 2022 R2 or
        later. The remote server must be up and running with the command
        `"ansysedt.exe -grpcsrv portnum"`.
    aedt_process_id : int, optional
        Process ID for the instance of AEDT to point PyAEDT at. The default is
        ``None``. This parameter is only used when ``new_desktop = False``.
    remove_lock : bool, optional
        Whether to remove lock to project before opening it or not.
        The default is ``False``, which means to not unlock
        the existing project if needed and raise an exception.

    Examples
    --------
    Create an instance of CircuitNetlist and connect to an existing CircuitNetlist
    design or create a new HFSS design if one does not exist.

    >>> from ansys.aedt.core import CircuitNetlist
    >>> aedtapp = CircuitNetlist()

    Create an instance of Circuit and link to a project named
    ``"projectname"``. If this project does not exist, create one with
    this name.

    >>> aedtapp = CircuitNetlist(projectname)

    Create an instance of Circuit and link to a design named
    ``"designname"`` in a project named ``"projectname"``.

    >>> aedtapp = CircuitNetlist(projectname,designame)

    Create an instance of Circuit and open the specified project,
    which is ``"myfie.aedt"``.

    >>> aedtapp = CircuitNetlist("myfile.aedt")

    Create an instance of Circuit using the 2025 R1 version and
    open the specified project, which is ``"myfile.aedt"``.

    >>> aedtapp = CircuitNetlist(version=2025.1, project="myfile.aedt")

    Create an instance of Circuit using the 2025 R1 student version and open
    the specified project, which is named ``"myfile.aedt"``.

    >>> hfss = CircuitNetlist(version="2025.1", project="myfile.aedt", student_version=True)

    """

    @pyaedt_function_handler()
    def __init__(
        self,
        project=None,
        design=None,
        version=None,
        non_graphical=False,
        new_desktop=False,
        close_on_exit=False,
        student_version=False,
        machine="",
        port=0,
        aedt_process_id=None,
        remove_lock=False,
    ):
        AnalysisCircuitNetlist.__init__(
            self,
            project,
            design,
            version,
            non_graphical,
            new_desktop,
            close_on_exit,
            student_version,
            machine,
            port,
            aedt_process_id,
            remove_lock,
        )

    def _init_from_design(self, *args, **kwargs):  # pragma: no cover
        self.__init__(*args, **kwargs)

    @pyaedt_function_handler(filepath="input_file")
    def browse_log_file(self, input_file=None):  # pragma: no cover
        """Save the most recent log file in a new directory.

        Parameters
        ----------
        input_file : str, optional
            File path to save the new log file to. The default is the ``pyaedt`` folder.

        Returns
        -------
        str
            File Path.
        """
        if input_file and not os.path.exists(os.path.normpath(input_file)):
            self.logger.error("Path does not exist.")
            return None
        elif not input_file:
            input_file = os.path.join(os.path.normpath(self.working_directory), "logfile")
            if not os.path.exists(input_file):
                os.mkdir(input_file)

        results_path = os.path.join(os.path.normpath(self.results_directory), self.design_name)
        results_temp_path = os.path.join(results_path, "temp")

        # Check if .log exist in temp folder
        if os.path.exists(results_temp_path) and search_files(results_temp_path, "*.log"):
            # Check the most recent
            files = search_files(results_temp_path, "*.log")
            latest_file = max(files, key=os.path.getctime)
        elif os.path.exists(results_path) and search_files(results_path, "*.log"):
            # Check the most recent
            files = search_files(results_path, "*.log")
            latest_file = max(files, key=os.path.getctime)
        else:
            self.logger.error("Design not solved")
            return None

        shutil.copy(latest_file, input_file)
        filename = os.path.basename(latest_file)
        return os.path.join(input_file, filename)
