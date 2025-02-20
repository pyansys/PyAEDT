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

"""
This module contains these classes: ``Design``.

This module provides all functionalities for basic project information and objects.
These classes are inherited in the main tool class.

"""

from __future__ import absolute_import  # noreorder

from abc import abstractmethod
import gc
import json
import os
import random
import re
import shutil
import string
import sys
import threading
import time
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import Union
import warnings

from ansys.aedt.core.application.aedt_objects import AedtObjects
from ansys.aedt.core.application.design_solutions import DesignSolution
from ansys.aedt.core.application.design_solutions import HFSSDesignSolution
from ansys.aedt.core.application.design_solutions import IcepakDesignSolution
from ansys.aedt.core.application.design_solutions import Maxwell2DDesignSolution
from ansys.aedt.core.application.design_solutions import RmXprtDesignSolution
from ansys.aedt.core.application.design_solutions import model_names
from ansys.aedt.core.application.design_solutions import solutions_defaults
from ansys.aedt.core.application.variables import DataSet
from ansys.aedt.core.application.variables import VariableManager
from ansys.aedt.core.desktop import _init_desktop_from_design
from ansys.aedt.core.desktop import exception_to_desktop
from ansys.aedt.core.generic.aedt_versions import aedt_versions
from ansys.aedt.core.generic.constants import AEDT_UNITS
from ansys.aedt.core.generic.constants import unit_system
from ansys.aedt.core.generic.data_handlers import variation_string_to_dict
from ansys.aedt.core.generic.errors import GrpcApiError
from ansys.aedt.core.generic.general_methods import check_and_download_file
from ansys.aedt.core.generic.general_methods import generate_unique_name
from ansys.aedt.core.generic.general_methods import inner_project_settings
from ansys.aedt.core.generic.general_methods import is_project_locked
from ansys.aedt.core.generic.general_methods import is_windows
from ansys.aedt.core.generic.general_methods import open_file
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.generic.general_methods import read_csv
from ansys.aedt.core.generic.general_methods import read_tab
from ansys.aedt.core.generic.general_methods import read_xlsx
from ansys.aedt.core.generic.general_methods import remove_project_lock
from ansys.aedt.core.generic.general_methods import settings
from ansys.aedt.core.generic.general_methods import write_csv
from ansys.aedt.core.generic.load_aedt_file import load_entire_aedt_file
from ansys.aedt.core.generic.numbers import _units_assignment
from ansys.aedt.core.generic.numbers import decompose_variable_value
from ansys.aedt.core.modules.boundary.common import BoundaryObject
from ansys.aedt.core.modules.boundary.icepak_boundary import NetworkObject
from ansys.aedt.core.modules.boundary.layout_boundary import BoundaryObject3dLayout
from ansys.aedt.core.modules.boundary.maxwell_boundary import MaxwellParameters

if sys.version_info.major > 2:
    import base64


def load_aedt_thread(project_path) -> None:
    """
    Load an AEDT file in a separate thread and update project settings.

    Parameters
    ----------
    project_path : str
        Path to the AEDT project file.
    """
    pp = load_entire_aedt_file(project_path)
    inner_project_settings.properties[os.path.normpath(project_path)] = pp
    inner_project_settings.time_stamp = os.path.getmtime(project_path)


class Design(AedtObjects):
    """Contains all functions and objects connected to the active project and design.

    This class is inherited in the caller application and is accessible through it for
    example, ``hfss.method_name``.

    Parameters
    ----------
    design_type : str
        Type of the design.
    project_name : str, optional
        Name of the project to select or the full path to the project
        or AEDTZ archive to open. The default is ``None``, in which
        case an attempt is made to get an active project. If no
        projects are present, an empty project is created.
    design_name : str, optional
        Name of the design to select. The default is ``None``, in
        which case an attempt is made to get an active design. If no
        designs are present, an empty design is created.
    solution_type : str, optional
        Solution type to apply to the design. The default is
        ``None``, in which case the default type is applied.
    version : str, int, float, optional
        Version of AEDT to use. The default is ``None``, in which case
        the active version or latest installed version is used.
    non_graphical : bool, optional
        Whether to run AEDT in non-graphical mode. The default
        is ``False``, in which case AEDT launches in graphical mode.
    new_desktop : bool, optional
        Whether to launch an instance of AEDT in a new thread, even if
        another instance of the ``specified_version`` is active on the
        machine. The default is ``False``.
    close_on_exit : bool, optional
        Whether to release AEDT on exit. The default is ``False``.
    student_version : bool, optional
        Whether to enable the student version of AEDT. The default
        is ``False``.
    aedt_process_id : int, optional
        Only used when ``new_desktop = False``, specifies by process ID which instance
        of Electronics Desktop to point PyAEDT at.
    ic_mode : bool, optional
        Whether to set the design to IC mode or not. The default is ``None``, which means to retain
        the existing setting. Applicable only to ``Hfss3dLayout``.
    remove_lock : bool, optional
        Whether to remove lock to project before opening it or not.
        The default is ``False``, which means to not unlock
        the existing project if needed and raise an exception.
    """

    def __init__(
        self,
        design_type: str,
        project_name: Optional[str] = None,
        design_name: Optional[str] = None,
        solution_type: Optional[str] = None,
        version: Optional[Union[str, int, float]] = None,
        non_graphical: bool = False,
        new_desktop: bool = False,
        close_on_exit: bool = False,
        student_version: bool = False,
        machine: str = "",
        port: int = 0,
        aedt_process_id: Optional[int] = None,
        ic_mode: Optional[bool] = None,
        remove_lock: bool = False,
    ):
        self._design_name: Optional[str] = None
        self._project_name: Optional[str] = None
        self._project_path: Optional[str] = None
        self.__t: Optional[threading.Thread] = None
        if (
            project_name
            and os.path.exists(project_name)
            and (os.path.splitext(project_name)[1] == ".aedt" or os.path.splitext(project_name)[1] == ".a3dcomp")
        ):
            self.__t = threading.Thread(target=load_aedt_thread, args=(project_name,), daemon=True)
            self.__t.start()
        self._init_variables()
        self._ic_mode: Optional[bool] = ic_mode
        self._design_type: str = design_type
        self.last_run_log: str = ""
        self.last_run_job: str = ""
        self._design_dictionary: Optional[Dict] = None
        self._project_dictionary: Dict = {}
        self._boundaries: Dict = {}
        self._project_datasets: List = []
        self._design_datasets: List = []
        self.close_on_exit: bool = close_on_exit
        self._desktop_class = None
        self._desktop_class = _init_desktop_from_design(
            version,
            non_graphical,
            new_desktop,
            close_on_exit,
            student_version,
            machine,
            port,
            aedt_process_id,
        )
        self._global_logger = self._desktop_class.logger
        self._logger = self._desktop_class.logger

        self.student_version = self._desktop_class.student_version
        if self.student_version:
            settings.disable_bounding_box_sat = True

        self._mttime: Optional[float] = None
        self._desktop = self._desktop_class.odesktop
        self._desktop_install_dir: Optional[str] = settings.aedt_install_dir
        self._odesign: Optional[Any] = None
        self._oproject: Optional[Any] = None

        if design_type == "HFSS":
            self.design_solutions = HFSSDesignSolution(None, design_type, self._aedt_version)
        elif design_type == "Icepak":
            self.design_solutions = IcepakDesignSolution(None, design_type, self._aedt_version)
        elif design_type == "Maxwell 2D":
            self.design_solutions = Maxwell2DDesignSolution(None, design_type, self._aedt_version)
        elif design_type == "RMxprtSolution" or design_type == "ModelCreation":
            self.design_solutions = RmXprtDesignSolution(None, design_type, self._aedt_version)
        else:
            self.design_solutions = DesignSolution(None, design_type, self._aedt_version)
        self.design_solutions._solution_type = solution_type

        self._temp_solution_type: Optional[str] = solution_type
        self._remove_lock: bool = remove_lock
        self.oproject: Optional[str] = project_name
        self.odesign: Optional[str] = design_name

        self._logger.oproject = self.oproject
        self._logger.odesign = self.odesign
        AedtObjects.__init__(self, self._desktop_class, self.oproject, self.odesign, is_inherithed=True)
        self.logger.info("Aedt Objects correctly read")
        if not self.__t and not settings.lazy_load and os.path.exists(self.project_file):
            self.__t = threading.Thread(target=load_aedt_thread, args=(self.project_file,), daemon=True)
            self.__t.start()

        self._variable_manager = VariableManager(self)
        self._project_datasets = []
        self._design_datasets = []

        if self._design_type not in ["Maxwell Circuit", "Circuit Netlist"]:
            self.design_settings = DesignSettings(self)

    @property
    def _pyaedt_details(self) -> Dict[str, str]:
        """Retrieve detailed session information for PyAEDT.

        Returns
        -------
        dict
            Session details including.
        """
        import platform

        from ansys.aedt.core import __version__ as pyaedt_version

        _p_dets = {
            "PyAEDT Version": pyaedt_version,
            "Product": f"Ansys Electronics Desktop {settings.aedt_version}",
            "Design Type": self.design_type,
            "Solution Type": self.solution_type,
            "Project Name": self.project_name,
            "Design Name": self.design_name,
            "Project Path": "",
        }
        if self._oproject:
            _p_dets["Project Path"] = self.project_file
        _p_dets["Platform"] = platform.platform()
        _p_dets["Python Version"] = platform.python_version()
        _p_dets["AEDT Process ID"] = self.desktop_class.aedt_process_id
        _p_dets["AEDT GRPC Port"] = self.desktop_class.port
        return _p_dets

    def __str__(self) -> str:
        return "\n".join(
            [
                f"{each_name}:".ljust(25) + f"{each_attr}".ljust(25)
                for each_name, each_attr in self._pyaedt_details.items()
            ]
        )

    def __exit__(self, ex_type, ex_value, ex_traceback) -> None:
        if ex_type:
            exception_to_desktop(ex_value, ex_traceback)
        if self._desktop_class._connected_app_instances > 0:  # pragma: no cover
            self._desktop_class._connected_app_instances -= 1
        if self._desktop_class._connected_app_instances <= 0 and self._desktop_class._initialized_from_design:
            self.release_desktop(self.close_on_exit, self.close_on_exit)

    def __enter__(self):  # pragma: no cover
        self._desktop_class._connected_app_instances += 1
        return self

    @pyaedt_function_handler()
    def __getitem__(self, variable_name: str) -> str:
        return self.variable_manager[variable_name].expression

    @pyaedt_function_handler()
    def __setitem__(self, variable_name: str, variable_value: Optional[Union[str, int, float]]) -> bool:
        variable_value = _units_assignment(variable_value)
        self.variable_manager[variable_name] = variable_value
        return True

    @property
    def info(self) -> Dict[str, str]:
        """Dictionary of the PyAEDT session information.

        Returns
        -------
        dict
            Dictionary containing session details.
        """
        return self._pyaedt_details

    def _init_design(self, project_name: str, design_name: str, solution_type: Optional[str] = None) -> None:
        """Initializes a new design.

        Parameters
        ----------
        project_name : str
            The name of the project to create or load.
        design_name : str
            The name of the design to create or load.
        solution_type : str, optional
            The solution type for the design.
        """
        # calls the method from the application class
        self._init_from_design(
            project=project_name,
            design=design_name,
            solution_type=solution_type,
            version=settings.aedt_version,
            non_graphical=self._desktop_class.non_graphical,
            new_desktop=False,
            close_on_exit=self.close_on_exit,
            student_version=self.student_version,
            machine=self._desktop_class.machine,
            port=self._desktop_class.port,
        )

    @property
    def desktop_class(self):
        """``Desktop`` class.

        Returns
        -------
        :class:`ansys.aedt.core.desktop.Desktop`
        """
        return self._desktop_class

    @property
    def project_datasets(self) -> Dict[str, DataSet]:
        """Dictionary of project datasets.

        Returns
        -------
        dict[str, :class:`ansys.aedt.core.application.variables.DataSet`]
            Project datasets.
        """
        if not self._project_datasets:
            self._project_datasets = self._get_project_datasets()
        return self._project_datasets

    @property
    def design_datasets(self) -> Dict[str, DataSet]:
        """Dictionary of Design Datasets.

        Returns
        -------
        dict[str, :class:`ansys.aedt.core.application.variables.DataSet`]
            Design datasets.
        """
        if not self._design_datasets:
            self._design_datasets = self._get_design_datasets()
        return self._design_datasets

    @property
    def boundaries(self) -> List[BoundaryObject]:
        """Design boundaries and excitations.

        Returns
        -------
        list[:class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`]
            Boundaries available in design.
        """
        bb = []
        if self.oboundary and "GetBoundaries" in self.oboundary.__dir__():
            bb = list(self.oboundary.GetBoundaries())
        elif (
            self.oboundary
            and "GetAllBoundariesList" in self.oboundary.__dir__()
            and self.design_type == "HFSS 3D Layout Design"
        ):
            bb = list(self.oboundary.GetAllBoundariesList())
            bb = [elem for sublist in zip(bb, ["Port"] * len(bb)) for elem in sublist]
        elif "Boundaries" in self.get_oo_name(self.odesign):
            bb = self.get_oo_name(self.odesign, "Boundaries")
        bb = list(bb)
        if self.oboundary and "GetHybridRegions" in self.oboundary.__dir__():
            hybrid_regions = self.oboundary.GetHybridRegions()
            for region in hybrid_regions:
                bb.append(region)
                bb.append("FE-BI")
        current_excitations = []
        current_excitation_types = []
        if self.oboundary and "GetExcitations" in self.oboundary.__dir__():
            ee = list(self.oboundary.GetExcitations())
            current_excitations = [i.split(":")[0] for i in ee[::2]]
            current_excitation_types = ee[1::2]
            ff = [i.split(":")[0] for i in ee]
            bb.extend(ff)
            for i in set(current_excitation_types):
                if "GetExcitationsOfType" in self.oboundary.__dir__():
                    ports = list(self.oboundary.GetExcitationsOfType(i))
                    for p in ports:
                        bb.append(p)
                        bb.append(i)
        elif (
            self.oboundary
            and "Excitations" in self.get_oo_name(self.odesign)
            and self.design_type == "HFSS 3D Layout Design"
        ):
            ee = self.get_oo_name(self.odesign, "Excitations")
            ee = [elem for sublist in zip(ee, ["Port"] * len(ee)) for elem in sublist]
            current_excitations = ee[::2]
            current_excitation_types = ee[1::2]

        # Parameters and Motion definitions
        if self.design_type in ["Maxwell 3D", "Maxwell 2D"]:
            maxwell_parameters = list(self.get_oo_name(self.odesign, "Parameters"))
            for parameter in maxwell_parameters:
                bb.append(parameter)
                bb.append("MaxwellParameters")
            if "Model" in list(self.get_oo_name(self.odesign)):
                maxwell_model = list(self.get_oo_name(self.odesign, "Model"))
                for parameter in maxwell_model:
                    if self.get_oo_property_value(self.odesign, f"Model\\{parameter}", "Type") == "Band":
                        bb.append(parameter)
                        bb.append("MotionSetup")

        # Icepak definition
        elif self.design_type == "Icepak":
            othermal = self.get_oo_object(self.odesign, "Thermal")
            thermal_definitions = list(self.get_oo_name(othermal))
            for thermal in thermal_definitions:
                bb.append(thermal)
                bb.append(self.get_oo_property_value(othermal, thermal, "Type"))

            if self.modeler.user_defined_components.items():
                for component in self.modeler.user_defined_components.keys():
                    thermal_properties = self.get_oo_properties(self.oeditor, component)
                    if thermal_properties and "Type" not in thermal_properties and thermal_properties[-1] != "Icepak":
                        thermal_boundaries = self.design_properties["BoundarySetup"]["Boundaries"]
                        for component_boundary in thermal_boundaries:
                            if component_boundary not in bb and isinstance(
                                thermal_boundaries[component_boundary], dict
                            ):
                                boundarytype = thermal_boundaries[component_boundary]["BoundType"]
                                bb.append(component_boundary)
                                bb.append(boundarytype)

        current_boundaries = bb[::2]
        current_types = bb[1::2]
        if hasattr(self, "excitations"):
            check_boundaries = list(current_boundaries[:]) + list(self.ports[:]) + self.excitations[:]
            if "nets" in dir(self):
                check_boundaries += self.nets
            for k in list(self._boundaries.keys())[:]:
                if k not in check_boundaries:
                    del self._boundaries[k]
        for boundary, boundarytype in zip(current_boundaries, current_types):
            if boundary in self._boundaries:
                self._boundaries[boundary]._initialize_tree_node()
                continue
            if boundarytype == "MaxwellParameters":
                maxwell_parameter_type = self.get_oo_property_value(self.odesign, f"Parameters\\{boundary}", "Type")

                self._boundaries[boundary] = MaxwellParameters(self, boundary, boundarytype=maxwell_parameter_type)
            elif boundarytype == "MotionSetup":
                maxwell_motion_type = self.get_oo_property_value(self.odesign, f"Model\\{boundary}", "Type")

                self._boundaries[boundary] = BoundaryObject(self, boundary, boundarytype=maxwell_motion_type)
            elif boundarytype == "Network":
                self._boundaries[boundary] = NetworkObject(self, boundary)
            else:
                self._boundaries[boundary] = BoundaryObject(self, boundary, boundarytype=boundarytype)

        try:
            for k, v in zip(current_excitations, current_excitation_types):
                if k not in self._boundaries:
                    if self.design_type == "HFSS 3D Layout Design" and v == "Port":
                        self._boundaries[k] = BoundaryObject3dLayout(self, k, props=None, boundarytype=v)
                    else:
                        self._boundaries[k] = BoundaryObject(self, k, boundarytype=v)
        except Exception:
            self.logger.info("Failed to design boundary object.")
        return list(self._boundaries.values())

    @property
    def boundaries_by_type(self) -> Dict[str, List[BoundaryObject]]:
        """Design boundaries by type.

        Returns
        -------
        dict[str, :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`]
        """
        _dict_out = {}
        for bound in self.boundaries:
            if bound.type in _dict_out:
                _dict_out[bound.type].append(bound)
            else:
                _dict_out[bound.type] = [bound]
        return _dict_out

    @property
    def ports(self) -> List[str]:
        """Design excitations.

        Returns
        -------
        list
            Port names.
        """
        design_excitations = []

        if self.oboundary and "GetExcitations" in self.oboundary.__dir__():
            ee = list(self.oboundary.GetExcitations())
            current_types = ee[1::2]
            for i in set(current_types):
                new_port = []
                if "GetExcitationsOfType" in self.oboundary.__dir__():
                    new_port = list(self.oboundary.GetExcitationsOfType(i))
                if new_port:
                    design_excitations += new_port
                    current_types = current_types + [i] * len(new_port)
            return design_excitations

        elif (
            self.oboundary
            and "GetAllPortsList" in self.oboundary.__dir__()
            and self.design_type in ["HFSS 3D Layout Design"]
        ):
            return self.oboundary.GetAllPortsList()
        return []

    @property
    def odesktop(self):
        """AEDT instance containing all projects and designs.

        Examples
        --------
        Get the COM object representing the desktop.

        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss.odesktop
        <class 'win32com.client.CDispatch'>
        """
        return self.desktop_class.odesktop

    @pyaedt_function_handler()
    def __delitem__(self, key: str) -> None:
        """Implement destructor with array name or index."""
        del self._variable_manager[key]

    def _init_variables(self) -> None:
        self.__aedt_version = ""
        self._modeler = None
        self._post = None
        self._materials = None
        self._variable_manager = None
        self._parametrics = None
        self._optimizations = None
        self._native_components = None
        self._mesh = None

    @property
    def settings(self) -> Dict:
        """Settings of the current Python/Pyaedt session."""
        return settings

    @property
    def logger(self):
        """Logger for the design.

        Returns
        -------
        :class:`ansys.aedt.core.aedt_logger.AedtLogger`
        """
        return self._logger

    @property
    def project_properties(self) -> Dict[str, dict]:
        """Project properties.

        Returns
        -------
        dict
            Dictionary of the project properties.
        """
        if self.__t:
            self.__t.join()
        self.__t = None
        start = time.time()
        if self.project_timestamp_changed or (
            os.path.exists(self.project_file)
            and os.path.normpath(self.project_file) not in inner_project_settings.properties
        ):
            inner_project_settings.properties[os.path.normpath(self.project_file)] = load_entire_aedt_file(
                self.project_file
            )
            self._logger.info(f"aedt file load time {time.time() - start}")
        elif (
            os.path.normpath(self.project_file) not in inner_project_settings.properties
            and settings.remote_rpc_session
            and settings.remote_rpc_session.filemanager.pathexists(self.project_file)
        ):
            file_path = check_and_download_file(self.project_file)
            try:
                inner_project_settings.properties[os.path.normpath(self.project_file)] = load_entire_aedt_file(
                    file_path
                )
            except Exception:
                self._logger.info("Failed to load AEDT file.")
            else:
                self._logger.info(f"Time to load AEDT file: {time.time() - start}.")
        if os.path.normpath(self.project_file) in inner_project_settings.properties:
            return inner_project_settings.properties[os.path.normpath(self.project_file)]
        return {}

    @property
    def design_properties(self) -> Dict[str, dict]:
        """Design properties.

        Returns
        -------
        dict
           Dictionary of the design properties.

        """
        try:
            if model_names[self._design_type] in self.project_properties["AnsoftProject"]:
                designs = self.project_properties["AnsoftProject"][model_names[self._design_type]]
                if isinstance(designs, list):
                    for design in designs:
                        if design["Name"] == self.design_name:
                            return design
                else:
                    if designs["Name"] == self.design_name:
                        return designs
        except Exception:
            return {}

    @property
    def aedt_version_id(self) -> str:
        """AEDT version.

        Returns
        -------
        str
            Version of AEDT.

        References
        ----------
        >>> oDesktop.GetVersion()
        """
        return aedt_versions.get_version_env_variable(self._aedt_version)

    @property
    def _aedt_version(self) -> str:
        return self.desktop_class.aedt_version_id

    @property
    def design_name(self) -> Optional[str]:
        """Design name.

        Returns
        -------
        str
            Name of the parent AEDT design.

        References
        ----------
        >>> oDesign.GetName
        >>> oDesign.RenameDesignInstance

        Examples
        --------
        Set the design name.

        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss.design_name = 'new_design'
        """
        if self._design_name:
            return self._design_name
        from ansys.aedt.core.generic.general_methods import _retry_ntimes

        if not self.odesign:
            return None
        self._design_name = _retry_ntimes(5, self.odesign.GetName)
        if ";" in self._design_name:
            self._design_name = self._design_name.split(";")[1]
        return self._design_name

    @design_name.setter
    def design_name(self, new_name: str) -> None:
        if ";" in new_name:
            new_name = new_name.split(";")[1]

        # If new_name is the name of an existing design, set the current
        # design to this design.
        if new_name in self.design_list:
            self.set_active_design(new_name)
        else:  # Otherwise rename the current design.
            self.odesign.RenameDesignInstance(self.design_name, new_name)
            timeout = 5.0
            timestep = 0.1
            while new_name not in [
                i.GetName() if ";" not in i.GetName() else i.GetName().split(";")[1]
                for i in list(self._oproject.GetDesigns())
            ]:
                time.sleep(timestep)
                timeout -= timestep
                if timeout < 0:
                    raise RuntimeError("Timeout reached while checking design renaming.")
            self._design_name = new_name

    @property
    def design_list(self) -> List[str]:
        """Design list.

        Returns
        -------
        list
            List of the designs.

        References
        ----------
        >>> oProject.GetTopDesignList()
        """
        deslist = list(self.oproject.GetTopDesignList())
        updateddeslist = []
        for el in deslist:
            m = re.search(r"[^;]+$", el)
            updateddeslist.append(m.group(0))
        return updateddeslist

    @property
    def design_type(self) -> str:
        """Design type.

        Options are ``"Circuit Design"``, ``"Circuit Netlist"``, ``"Emit"``, ``"HFSS"``,
        ``"HFSS 3D Layout Design"``, ``"Icepak"``, ``"Maxwell 2D"``,
        ``"Maxwell 3D"``, ``"Maxwell Circuit"``, ``"Mechanical"``, ``"ModelCreation"``,
        ``"Q2D Extractor"``, ``"Q3D Extractor"``, ``"RMxprtSolution"``,
        and ``"Twin Builder"``.

        Returns
        -------
        str
            Type of the design. See above for a list of possible return values.

        """
        return self._design_type

    @property
    def project_name(self) -> Optional[str]:
        """Project name.

        Returns
        -------
        str
            Name of the project.

        References
        ----------
        >>> oProject.GetName
        """
        if self._project_name:
            return self._project_name
        if self.oproject:
            try:
                self._project_name = self.oproject.GetName()
                self._project_path = None
                return self._project_name
            except Exception:
                return None
        else:
            return None

    @property
    def project_list(self) -> List[str]:
        """Project list.

        Returns
        -------
        list
            List of projects.

        References
        ----------
        >>> oDesktop.GetProjectList
        """
        return list(self.odesktop.GetProjectList())

    @property
    def project_path(self) -> Optional[str]:
        """Project path.

        Returns
        -------
        str
            Path to the project.

        References
        ----------
        >>> oProject.GetPath
        """
        if not self._project_path and self.oproject:
            self._project_path = self.oproject.GetPath()
        return self._project_path

    @property
    def project_time_stamp(self) -> Union[int, float]:
        """Return Project time stamp."""
        if os.path.exists(self.project_file):
            inner_project_settings.time_stamp = os.path.getmtime(self.project_file)
        else:
            inner_project_settings.time_stamp = 0
        return inner_project_settings.time_stamp

    @property
    def project_timestamp_changed(self) -> bool:
        """Return a bool if time stamp changed or not."""
        old_time = inner_project_settings.time_stamp
        return old_time != self.project_time_stamp

    @property
    def project_file(self) -> Optional[str]:
        """Project name and path.

        Returns
        -------
        str
            Full absolute name and path for the project.

        """
        if self.project_path:
            return os.path.join(self.project_path, self.project_name + ".aedt")

    @property
    def lock_file(self) -> Optional[str]:
        """Lock file.

        Returns
        -------
        str
            Full absolute name and path for the project's lock file.

        """
        if self.project_path:
            return os.path.join(self.project_path, self.project_name + ".aedt.lock")

    @property
    def results_directory(self) -> Optional[str]:
        """Results directory.

        Returns
        -------
        str
            Full absolute path for the ``aedtresults`` directory.

        """
        if self.project_path:
            return os.path.join(self.project_path, self.project_name + ".aedtresults")

    @property
    def solution_type(self) -> Optional[str]:
        """Solution type.

        Returns
        -------
        str
            Type of the solution.

        References
        ----------
        >>> oDesign.GetSolutionType
        >>> oDesign.SetSolutionType
        """
        if self.design_solutions:
            return self.design_solutions.solution_type
        return None

    @solution_type.setter
    def solution_type(self, soltype: str) -> None:
        if self.design_solutions:
            if (
                self.design_type == "HFSS" and self.design_solutions.solution_type == "Terminal" and soltype == "Modal"
            ):  # pragma: no cover
                boundaries = self.boundaries
                for exc in boundaries:
                    if exc.type == "Terminal":
                        del self._boundaries[exc.name]
            self.design_solutions.solution_type = soltype

    @property
    def valid_design(self) -> bool:
        """Valid design.

        Returns
        -------
        bool
            ``True`` when the project and design exists, ``False`` otherwise.

        """
        if self._oproject and self._odesign:
            return True
        else:
            return False

    @property
    def personallib(self) -> str:
        """PersonalLib directory.

        Returns
        -------
        str
            Full absolute path for the ``PersonalLib`` directory.

        References
        ----------
        >>> oDesktop.GetPersonalLibDirectory
        """
        return self.desktop_class.personallib

    @property
    def userlib(self) -> str:
        """UserLib directory.

        Returns
        -------
        str
            Full absolute path for the ``UserLib`` directory.

        References
        ----------
        >>> oDesktop.GetUserLibDirectory
        """
        return self.desktop_class.userlib

    @property
    def syslib(self) -> str:
        """SysLib directory.

        Returns
        -------
        str
            Full absolute path for the ``SysLib`` directory.

        References
        ----------
        >>> oDesktop.GetLibraryDirectory
        """
        return self.desktop_class.syslib

    @property
    def src_dir(self) -> str:
        """Source directory for Python.

        Returns
        -------
        str
            Full absolute path for the ``python`` directory.

        """
        return os.path.dirname(os.path.realpath(__file__))

    @property
    def pyaedt_dir(self) -> str:
        """PyAEDT directory.

        Returns
        -------
        str
           Full absolute path for the ``pyaedt`` directory.

        """
        return os.path.realpath(os.path.join(self.src_dir, ".."))

    @property
    def library_list(self) -> List[str]:
        """Library list.

        Returns
        -------
        list
            List of libraries: ``[syslib, userlib, personallib]``.

        """
        return [self.syslib, self.userlib, self.personallib]

    @property
    def temp_directory(self) -> str:
        """Path to the temporary directory.

        Returns
        -------
        str
            Full absolute path for the ``temp`` directory.

        """
        return self.odesktop.GetTempDirectory()

    @property
    def toolkit_directory(self) -> str:
        """Path to the toolkit directory.

        Returns
        -------
        str
            Full absolute path for the ``pyaedt`` directory for this project.
            If this directory does not exist, it is created.
        """
        if self.project_name:
            name = self.project_name.replace(" ", "_")
        else:
            name = generate_unique_name("prj")
        toolkit_directory = os.path.join(self.project_path, name + ".pyaedt")
        if settings.remote_rpc_session:
            toolkit_directory = self.project_path + "/" + name + ".pyaedt"
            try:
                settings.remote_rpc_session.filemanager.makedirs(toolkit_directory)
            except Exception:
                toolkit_directory = settings.remote_rpc_session.filemanager.temp_dir() + "/" + name + ".pyaedt"
        elif settings.remote_api or settings.remote_rpc_session:
            toolkit_directory = self.results_directory
        elif not os.path.isdir(toolkit_directory):
            try:
                os.makedirs(toolkit_directory)
            except FileNotFoundError:
                toolkit_directory = self.results_directory

        return toolkit_directory

    @property
    def working_directory(self) -> str:
        """Path to the working directory.

        Returns
        -------
        str
             Full absolute path for the project's working directory.
             If this directory does not exist, it is created.

        """
        if self.design_name:
            name = self.design_name.replace(" ", "_")
        else:
            name = generate_unique_name("prj")
        working_directory = os.path.join(os.path.normpath(self.toolkit_directory), name)
        if settings.remote_rpc_session:
            working_directory = self.toolkit_directory + "/" + name
            settings.remote_rpc_session.filemanager.makedirs(working_directory)
        elif not os.path.isdir(working_directory):
            try:
                os.makedirs(working_directory)
            except FileNotFoundError:
                working_directory = os.path.join(self.toolkit_directory, name + ".results")
        return working_directory

    @property
    def default_solution_type(self) -> str:
        """Default solution type.

        Returns
        -------
        str
           Default for the solution type.

        """
        return solutions_defaults[self._design_type]

    @pyaedt_function_handler()
    def _find_design(self) -> Tuple[str, str]:
        activedes = None
        warning_msg = ""
        names = self.get_oo_name(self.oproject)
        if names:
            valids = []
            for name in names:
                des = self.get_oo_object(self.oproject, name)
                des_type = None
                if hasattr(des, "GetDesignType"):
                    des_type = des.GetDesignType()
                if des_type == self.design_type or (
                    des_type == "RMxprt"
                    and self.design_type
                    in [
                        "RMxprtSolution",
                        "ModelCreation",
                    ]
                ):
                    if self.design_type in [
                        "Circuit Design",
                        "Twin Builder",
                        "HFSS 3D Layout Design",
                        "EMIT",
                        "Q3D Extractor",
                        "RMxprtSolution",
                        "ModelCreation",
                    ]:
                        valids.append(name)
                    elif not self._temp_solution_type:
                        valids.append(name)
                    elif self._temp_solution_type in des.GetSolutionType():
                        valids.append(name)
            if len(valids) > 1:
                des_name = self.oproject.GetActiveDesign().GetName()
                if des_name in valids:
                    activedes = self.oproject.GetActiveDesign().GetName()
                else:
                    activedes = valids[0]
                warning_msg = f"Active Design set to {valids[0]}"
            elif len(valids) == 1:
                activedes = valids[0]
                warning_msg = f"Active Design set to {valids[0]}"
            else:
                warning_msg = "No consistent unique design is present. Inserting a new design."

        # legacy support for version < 2021.2
        elif self.design_list:  # pragma: no cover
            self._odesign = self._oproject.GetDesign(self.design_list[0])
            if not self._check_design_consistency():
                count_consistent_designs = 0
                for des in self.design_list:
                    self._odesign = self.desktop_class.active_design(self.oproject, des, self.design_type)
                    if self._check_design_consistency():
                        count_consistent_designs += 1
                        activedes = des
                if count_consistent_designs != 1:
                    warning_msg = "No consistent unique design is present. Inserting a new design."
                else:
                    self.logger.info(f"Active Design set to {activedes}")
            else:
                activedes = self.design_list[0]
                warning_msg = f"Active design is set to {self.design_list[0]}"
        else:
            warning_msg = "No design is present. Inserting a new design."
        return activedes, warning_msg

    @property
    def odesign(self):
        """Design.

        Returns
        -------
        Design object

        References
        ----------
        >>> oProject.SetActiveDesign
        >>> oProject.InsertDesign
        """
        if settings.use_multi_desktop:  # pragma: no cover
            self._desktop_class.grpc_plugin.recreate_application(True)
            if self._design_name:
                self._odesign = self.oproject.SetActiveDesign(self._design_name)
        return self._odesign

    @odesign.setter
    def odesign(self, des_name) -> None:
        if des_name:
            if self._assert_consistent_design_type(des_name) == des_name:
                self._insert_design(self._design_type, design_name=des_name)
            self.design_solutions._odesign = self.odesign
            if self._temp_solution_type:
                self.design_solutions.solution_type = self._temp_solution_type
        else:
            activedes, warning_msg = self._find_design()
            if activedes:
                self._odesign = self.desktop_class.active_design(self.oproject, activedes, self.design_type)
                self.logger.info(warning_msg)
                self.design_solutions._odesign = self.odesign

            else:
                self.logger.info(warning_msg)
                self._insert_design(self._design_type)
                self.design_solutions._odesign = self.odesign
                if self._temp_solution_type:
                    self.design_solutions.solution_type = self._temp_solution_type
        if self._ic_mode is not None and (
            self.solution_type == "HFSS3DLayout" or self.solution_type == "HFSS 3D Layout Design"
        ):
            self.set_oo_property_value(self.odesign, "Design Settings", "Design Mode/IC", self._ic_mode)
            self.desktop_class.active_design(self.oproject, des_name)
        self._design_name = None

    @property
    def oproject(self):
        """Project property.

        Returns
        -------
            Project object

        References
        ----------
        >>> oDesktop.GetActiveProject
        >>> oDesktop.SetActiveProject
        >>> oDesktop.NewProject
        """
        if settings.use_multi_desktop:  # pragma: no cover
            self._desktop_class.grpc_plugin.recreate_application(True)
        return self._oproject

    @oproject.setter
    def oproject(self, proj_name=None):
        if not proj_name:
            self._oproject = self.desktop_class.active_project()
            if self._oproject:
                self.logger.info(f"No project is defined. Project {self._oproject.GetName()} exists and has been read.")
        else:
            prj_list = self.odesktop.GetProjectList()
            if prj_list and proj_name in list(prj_list):
                self._oproject = self.desktop_class.active_project(proj_name)
                self._add_handler()
                self.logger.info("Project %s set to active.", proj_name)
            elif os.path.exists(proj_name) or (
                settings.remote_rpc_session and settings.remote_rpc_session.filemanager.pathexists(proj_name)
            ):
                if ".aedtz" in proj_name:
                    name = self._generate_unique_project_name()
                    path = os.path.dirname(proj_name)
                    self.odesktop.RestoreProjectArchive(proj_name, os.path.join(path, name), True, True)
                    time.sleep(0.5)
                    self._oproject = self.desktop_class.active_project()
                    self._add_handler()
                    self.logger.info(f"Archive {proj_name} has been restored to project {self._oproject.GetName()}")
                elif ".def" in proj_name or proj_name[-5:] == ".aedb":
                    if ".def" in proj_name:
                        project = os.path.dirname(proj_name)[:-5] + ".aedt"
                    else:
                        project = proj_name[:-5] + ".aedt"
                    if os.path.exists(project) and self.check_if_project_is_loaded(project):
                        pname = self.check_if_project_is_loaded(project)
                        self._oproject = self.desktop_class.active_project(pname)
                        self._add_handler()
                        self.logger.info("Project %s set to active.", pname)
                    elif os.path.exists(project):
                        if is_project_locked(project):
                            if self._remove_lock:  # pragma: no cover
                                self.logger.warning("Project is locked. Removing it and opening.")
                                remove_project_lock(project)
                            else:  # pragma: no cover
                                raise RuntimeError("Project is locked. Close or remove the lock before proceeding.")
                        self.logger.info("aedt project found. Loading it.")
                        self._oproject = self.odesktop.OpenProject(project)
                        self._add_handler()
                        self.logger.info("Project %s has been opened.", self._oproject.GetName())
                        time.sleep(0.5)
                    else:
                        oTool = self.odesktop.GetTool("ImportExport")
                        if ".def" in proj_name:
                            oTool.ImportEDB(proj_name)
                        else:
                            oTool.ImportEDB(os.path.join(proj_name, "edb.def"))
                        self._oproject = self.desktop_class.active_project()
                        self._oproject.Save()
                        self._add_handler()
                        self.logger.info(
                            "EDB folder %s has been imported to project %s", proj_name, self._oproject.GetName()
                        )
                elif self.check_if_project_is_loaded(proj_name):
                    pname = self.check_if_project_is_loaded(proj_name)
                    self._oproject = self.desktop_class.active_project(pname)
                    self._add_handler()
                    self.logger.info("Project %s set to active.", pname)
                else:
                    if is_project_locked(proj_name):
                        if self._remove_lock:  # pragma: no cover
                            self.logger.warning("Project is locked. Removing it and opening.")
                            remove_project_lock(proj_name)
                        else:  # pragma: no cover
                            raise RuntimeError("Project is locked. Close or remove the lock before proceeding.")
                    self._oproject = self.odesktop.OpenProject(proj_name)
                    if not is_windows and settings.aedt_version:
                        time.sleep(1)
                        self.desktop_class.close_windows()
                    self._add_handler()
                    self.logger.info("Project %s has been opened.", self._oproject.GetName())
                    time.sleep(0.5)
            elif settings.force_error_on_missing_project and ".aedt" in proj_name:
                raise Exception("Project doesn't exist. Check it and retry.")
            else:
                project_list = self.odesktop.GetProjectList()
                self._oproject = self.odesktop.NewProject()
                if not self._oproject:
                    new_project_list = [i for i in self.odesktop.GetProjectList() if i not in project_list]
                    if new_project_list:
                        self._oproject = self.desktop_class.active_project(new_project_list[0])
                if proj_name.endswith(".aedt"):
                    self._oproject.Rename(proj_name, True)
                elif not proj_name.endswith(".aedtz"):
                    self._oproject.Rename(os.path.join(self.project_path, proj_name + ".aedt"), True)
                self._add_handler()
                self.logger.info("Project %s has been created.", self._oproject.GetName())
        if not self._oproject:
            project_list = self.odesktop.GetProjectList()
            self._oproject = self.odesktop.NewProject()
            if not self._oproject:
                new_project_list = [i for i in self.odesktop.GetProjectList() if i not in project_list]
                if new_project_list:
                    self._oproject = self.desktop_class.active_project(new_project_list[0])
            self._add_handler()
            self.logger.info("Project %s has been created.", self._oproject.GetName())
        self._project_name = None
        self._project_path = None

    def _add_handler(self):
        if (
            not self._oproject
            or not settings.enable_local_log_file
            or settings.remote_api
            or settings.remote_rpc_session
        ):
            return
        for handler in self._global_logger._files_handlers:
            if f"pyaedt_{self._oproject.GetName()}.log" in str(handler):
                return
        self._logger = self._global_logger.add_file_logger(
            os.path.join(self.toolkit_directory, f"pyaedt_{self._oproject.GetName()}.log"),
            project_name=self.project_name,
        )

    @property
    def desktop_install_dir(self):
        """AEDT installation directory.

        Returns
        -------
        str
            AEDT installation directory.

        """
        return self._desktop_install_dir

    @pyaedt_function_handler()
    def remove_all_unused_definitions(self):
        """Remove all unused definitions in the project.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        self.oproject.RemoveAllUnusedDefinitions()
        return True

    @pyaedt_function_handler()
    def get_profile(self, name=None):
        """Get profile information.

        Parameters
        ----------
        name : str
            Setup name. The default is ``None``, in which case all available setups are returned.

        Returns
        -------
        dict of :class:`ansys.aedt.core.modeler.cad.elements_3d.BinaryTree` when successful,
        ``False`` when failed.
        """
        from ansys.aedt.core.modeler.cad.elements_3d import BinaryTreeNode

        if not name:
            name = self.setup_names
        if not isinstance(name, list):
            name = [name]

        profile_setups_obj = self.get_oo_object(self.odesign, "results/profile")

        profile_objs = {}
        if profile_setups_obj:
            profile_setup_names = self.get_oo_name(self.odesign, "results/profile")
            for n in name:
                for profile_setup_name in profile_setup_names:
                    if n in profile_setup_name:
                        profile_setup_obj = self.get_oo_object(profile_setups_obj, profile_setup_name)
                        if profile_setup_obj and self.get_oo_name(profile_setup_obj):
                            try:
                                profile_tree = BinaryTreeNode("profile", profile_setup_obj, app=self._app)
                                profile_objs[profile_setup_name] = profile_tree
                            except Exception:  # pragma: no cover
                                self.logger.error(f"{profile_setup_name} profile could not be obtained.")
            return profile_objs
        else:  # pragma: no cover
            self.logger.error("Profile can not be obtained.")
            return False

    @pyaedt_function_handler()
    def get_oo_name(self, aedt_object, object_name=None):
        """Return the object-oriented AEDT property names.

        Parameters
        ----------
        aedt_object : object
            AEDT Object on which search for property. It can be any oProperty (ex. oDesign).
        object_name : str, optional
            Path to the object list. Example `"DesignName\\Boundaries"`.

        Returns
        -------
        list
            Values returned by method if any.
        """
        try:
            if object_name:
                return aedt_object.GetChildObject(object_name).GetChildNames()
            else:
                return aedt_object.GetChildNames()

        except Exception:
            return []

    @pyaedt_function_handler()
    def get_oo_object(self, aedt_object, object_name):
        """Return the Object Oriented AEDT Object.

        Parameters
        ----------
        aedt_object : object
            AEDT Object on which search for property. It can be any oProperty (ex. oDesign).
        object_name : str
            Path to the object list. Example ``"DesignName\\Boundaries"``.

        Returns
        -------
        object
            Aedt Object if Any.
        """
        try:
            return aedt_object.GetChildObject(object_name)
        except Exception:
            return False

    @pyaedt_function_handler()
    def get_oo_properties(self, aedt_object, object_name):
        """Return the Object Oriented AEDT Object Properties.

        Parameters
        ----------
        aedt_object : object
            AEDT Object on which search for property. It can be any oProperty (ex. oDesign).
        object_name : str
            Path to the object list. Example ``"DesignName\\Boundaries"``.

        Returns
        -------
        list
            Values returned by method if any.
        """
        try:
            return aedt_object.GetChildObject(object_name).GetPropNames()
        except Exception:
            return []

    @pyaedt_function_handler()
    def get_oo_property_value(self, aedt_object, object_name, prop_name):
        """Return the Object Oriented AEDT Object Properties.

        Parameters
        ----------
        aedt_object : object
            AEDT Object on which search for property. It can be any oProperty (ex. oDesign).
        object_name : str
            Path to the object list. For example, ``"DesignName\\Boundaries"``.
        prop_name : str
            Property name.

        Returns
        -------
        str, float, bool
            ``True`` when successful, ``False`` when failed.
        """
        try:
            return aedt_object.GetChildObject(object_name).GetPropValue(prop_name)
        except Exception:
            return None

    @pyaedt_function_handler()
    def set_oo_property_value(self, aedt_object, object_name, prop_name, value):
        """Change the property value of the object-oriented AEDT object.

        Parameters
        ----------
        aedt_object : object
            AEDT object to search for the property on. It can be any oProperty. For example, oDesign.
        object_name : str
            Path to the object list. Example ``"DesignName\\Boundaries"``.
        prop_name : str
            Property name.
        value : str
            Property value.

        Returns
        -------
        bool
            Values returned by method if any.
        """
        try:
            aedt_object.GetChildObject(object_name).SetPropValue(prop_name, value)
            return True
        except Exception:
            return False

    @pyaedt_function_handler(setup_name="setup", variation_string="variation", file_path="output_file")
    def export_profile(self, setup, variation="", output_file=None):
        """Export a solution profile to a PROF file.

        Parameters
        ----------
        setup : str
            Setup name. For example, ``'Setup1'``.
        variation : str
            Variation string with values. For example, ``'radius=3mm'``.
        output_file : str, optional
            Full path to the PROF file. The default is ``None``, in which case
            the working directory is used.


        Returns
        -------
        str
            File path if created.

        References
        ----------
        >>> oDesign.ExportProfile
        """
        if not output_file:
            output_file = os.path.join(self.working_directory, generate_unique_name("Profile") + ".prof")
        if not variation:
            val_str = []
            for el, val in self.available_variations.nominal_w_values_dict.items():
                val_str.append(f"{el}={val}")
            if self.design_type == "HFSS 3D Layout Design":
                variation = " ".join(val_str)
            else:
                variation = ",".join(val_str)
        if self.design_type == "2D Extractor":
            for s in self.setups:
                if s.name == setup:
                    if "CGDataBlock" in s.props:
                        output_file = os.path.splitext(output_file)[0] + "CG" + os.path.splitext(output_file)[1]
                        self.odesign.ExportProfile(setup, variation, "CG", output_file, True)
                        self.logger.info(f"Exported Profile to file {output_file}")
                    if "RLDataBlock" in s.props:
                        output_file = os.path.splitext(output_file)[0] + "RL" + os.path.splitext(output_file)[1]
                        self.odesign.ExportProfile(setup, variation, "RL", output_file, True)
                        self.logger.info(f"Exported Profile to file {output_file}")
                    break
        elif self.design_type == "Q3D Extractor":
            for s in self.setups:
                if s.name == setup:
                    if "Cap" in s.props:
                        output_file = os.path.splitext(output_file)[0] + "CG" + os.path.splitext(output_file)[1]
                        self.odesign.ExportProfile(setup, variation, "CG", output_file, True)
                        self.logger.info(f"Exported Profile to file {output_file}")
                    if "AC" in s.props:
                        output_file = os.path.splitext(output_file)[0] + "ACRL" + os.path.splitext(output_file)[1]
                        self.odesign.ExportProfile(setup, variation, "AC RL", output_file, True)
                        self.logger.info(f"Exported Profile to file {output_file}")
                    if "DC" in s.props:
                        output_file = os.path.splitext(output_file)[0] + "DC" + os.path.splitext(output_file)[1]
                        self.odesign.ExportProfile(setup, variation, "DC RL", output_file, True)
                        self.logger.info(f"Exported Profile to file {output_file}")
                    break
        else:
            try:
                self.odesign.ExportProfile(setup, variation, output_file)
            except Exception:
                self.odesign.ExportProfile(setup, variation, output_file, True)
            self.logger.info(f"Exported Profile to file {output_file}")
        return output_file

    @pyaedt_function_handler(message_text="text", message_type="level")
    def add_info_message(self, text, level=None):
        """Add a type 0 "Info" message to either the global, active project, or active design
        level of the message manager tree.

        Also add an "Info" message to the logger if the handler is present.

        Parameters
        ----------
        text : str
            Text to display as the info message.
        level : str, optional
            Level to add the "Info" message to. Options are ``"Global"``,
            ``"Project"``, and ``"Design"``. The default is ``None``,
            in which case the "Info" message gets added to the ``"Design"``
            level.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss.logger.info("Global info message")
        >>> hfss.logger.project_logger.info("Project info message")
        >>> hfss.logger.design_logger.info("Design info message")
        """
        warnings.warn(
            "`add_info_message` is deprecated. Use `logger.design_logger.info` instead.",
            DeprecationWarning,
        )
        if level.lower() == "project":
            self.logger.project_logger.info(text)
        elif level.lower() == "design":
            self.logger.design_logger.info(text)
        else:
            self.logger.info(text)
        return True

    @pyaedt_function_handler(message_text="text", message_type="level")
    def add_warning_message(self, text, level=None):
        """Add a type 0 "Warning" message to either the global, active project, or active design
        level of the message manager tree.

        Also add an "Warning" message to the logger if the handler is present.

        Parameters
        ----------
        text : str
            Text to display as the "Warning" message.
        level : str, optional
            Level to add the "Warning" message to. Options are ``"Global"``,
            ``"Project"``, and ``"Design"``. The default is ``None``,
            in which case the "Warning" message gets added to the ``"Design"``
            level.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss.logger.warning("Global warning message", "Global")
        >>> hfss.logger.project_logger.warning("Project warning message", "Project")
        >>> hfss.logger.design_logger.warning("Design warning message")
        """
        warnings.warn(
            "`add_warning_message` is deprecated. Use `logger.design_logger.warning` instead.",
            DeprecationWarning,
        )

        if level.lower() == "project":
            self.logger.project_logger.warning(text)
        elif level.lower() == "design":
            self.logger.design_logger.warning(text)
        else:
            self.logger.warning(text)
        return True

    @pyaedt_function_handler(message_text="text", message_type="level")
    def add_error_message(self, text, level=None):
        """Add a type 0 "Error" message to either the global, active project, or active design
        level of the message mmanager tree.

        Also add an "Error" message to the logger if the handler is present.

        Parameters
        ----------
        text : str
            Text to display as the "Error" message.
        level : str, optional
            Level to add the "Error" message to. Options are ``"Global"``,
            ``"Project"``, and ``"Design"``. The default is ``None``,
            in which case the "Error" message gets added to the ``"Design"``
            level.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss.logger.error("Global error message", "Global")
        >>> hfss.logger.project_logger.error("Project error message", "Project")
        >>> hfss.logger.design_logger.error("Design error message")
        """
        warnings.warn(
            "`add_error_message` is deprecated. Use `logger.design_logger.error` instead.",
            DeprecationWarning,
        )

        if level.lower() == "project":
            self.logger.project_logger.error(text)
        elif level.lower() == "design":
            self.logger.design_logger.error(text)
        else:
            self.logger.error(text)
        return True

    @property
    def variable_manager(self):
        """Variable manager for creating and managing project design and postprocessing variables.

        Returns
        -------
        ansys.aedt.core.application.variables.VariableManager

        """
        return self._variable_manager

    @pyaedt_function_handler()
    def _arg_with_units(self, value, units=None):
        """Dimension argument.

        Parameters
        ----------
        value :

        units : optional
             The default is ``None``.

        Returns
        -------
        str
            String concatenating the value and unit.

        """
        if units is None:
            units = self.modeler.model_units
        if isinstance(value, str):
            try:
                float(value)
                val = f"{value}{units}"
            except Exception:
                val = value
        else:
            val = f"{value}{units}"
        return val

    @pyaedt_function_handler()
    def set_license_type(self, license_type="Pool"):
        """Change the license type between ``"Pack"`` and ``"Pool"``.

        Parameters
        ----------
        license_type : str, optional
            Type of license type, which can be either ``"Pack"`` or ``"Pool"``.

        Returns
        -------
        bool
            ``True``.

            .. note::
               Because of an API limitation, the command returns ``True`` even when the key is wrong.

        References
        ----------
        >>> oDesktop.SetRegistryString
        """
        try:
            self.odesktop.SetRegistryString("Desktop/Settings/ProjectOptions/HPCLicenseType", license_type)
            return True
        except Exception:
            return False

    @pyaedt_function_handler(key_full_name="name", key_value="value")
    def set_registry_key(self, name, value):
        """Change a specific registry key to a new value.

        Parameters
        ----------
        name : str
            Full name of the AEDT registry key.
        value : str, int
            Value for the AEDT registry key.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesktop.SetRegistryString
        >>> oDesktop.SetRegistryInt
        """
        if isinstance(value, str):
            try:
                self.odesktop.SetRegistryString(name, value)
                self.logger.info("Key %s correctly changed.", name)
                return True
            except Exception:
                self.logger.warning("Error setting up Key %s.", name)
                return False
        elif isinstance(value, int):
            try:
                self.odesktop.SetRegistryInt(name, value)
                self.logger.info("Key %s correctly changed.", name)
                return True
            except Exception:
                self.logger.warning("Error setting up Key %s.", name)
                return False
        else:
            self.logger.warning("Key value must be an integer or string.")
            return False

    @pyaedt_function_handler(key_full_name="name")
    def get_registry_key_string(self, name):
        """Get the value for the AEDT registry key if one exists.

        Parameters
        ----------
        name : str
            Full name of the AEDT registry key.

        Returns
        -------
        str
          Value for the AEDT registry key, otherwise ``''``.

        References
        ----------
        >>> oDesktop.GetRegistryString
        """
        return self.odesktop.GetRegistryString(name)

    @pyaedt_function_handler(key_full_name="name")
    def get_registry_key_int(self, name):
        """Get the value for the AEDT registry key if one exists.

        Parameters
        ----------
        name : str
            Full name of the AEDT registry key.

        Returns
        -------
        str
            Value for the AEDT registry key, otherwise ``0``.

        References
        ----------
        >>> oDesktop.GetRegistryInt
        """
        return self.odesktop.GetRegistryInt(name)

    @pyaedt_function_handler(beta_option_name="beta_option")
    def check_beta_option_enabled(self, beta_option):
        """Check if a beta option is enabled.

        Parameters
        ----------
        beta_option : str
            Name of the beta option to check. For example, ``'SF43060_HFSS_PI'``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesktop.GetRegistryString
        """
        limit = 100
        i = 0
        while limit > 0:
            a = self.get_registry_key_string(f"Desktop/Settings/ProjectOptions/EnabledBetaOptions/Item{i}")
            if a and a == beta_option:
                return True
            elif a:
                i += 1
                limit -= 1
            else:
                limit = 0
        return False

    @pyaedt_function_handler()
    def _is_object_oriented_enabled(self):
        if self._aedt_version >= "2022.1":
            return True
        elif self.check_beta_option_enabled("SF159726_SCRIPTOBJECT"):
            return True
        else:
            try:
                self.oproject.GetChildObject("Variables")
                return True
            except Exception:
                return False

    @pyaedt_function_handler()
    def set_active_dso_config_name(self, product_name="HFSS", config_name="Local"):
        """Change a specific registry key to a new value.

        Parameters
        ----------
        product_name : str, optional
            Name of the tool to apply the active configuration to. The default is ``"HFSS"``.
        config_name : str, optional
            Name of the configuration to apply. The default is ``"Local"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesktop.SetRegistryString
        """
        try:
            self.set_registry_key(f"Desktop/ActiveDSOConfigurations/{product_name}", config_name)
            self.logger.info("Configuration Changed correctly to %s for %s.", config_name, product_name)
            return True
        except Exception:
            self.logger.warning("Error Setting Up Configuration %s for %s.", config_name, product_name)
            return False

    @pyaedt_function_handler()
    def set_registry_from_file(self, registry_file, make_active=True):
        """Apply desktop registry settings from an ACT file.

        One way to get an ACF file is to export a configuration from the AEDT UI and then edit and reuse it.

        Parameters
        ----------
        registry_file : str
            Full path to the ACF file.
        make_active : bool, optional
            Whether to set the imported configuration as active. The default is ``True``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesktop.SetRegistryFromFile
        """
        try:
            self.odesktop.SetRegistryFromFile(registry_file)
            if make_active:
                with open_file(registry_file, "r") as f:
                    for line in f:
                        stripped_line = line.strip()
                        if "ConfigName" in stripped_line:
                            config_name = stripped_line.split("=")
                        elif "DesignType" in stripped_line:
                            design_type = stripped_line.split("=")
                            break
                    if design_type and config_name:
                        self.set_active_dso_config_name(design_type[1], config_name[1])
            return True
        except Exception:
            return False

    @pyaedt_function_handler()
    def _optimetrics_variable_args(
        self,
        arg,
        optimetrics_type,
        variable_name,
        min_val=None,
        max_val=None,
        tolerance=None,
        probability=None,
        mean=None,
        enable=True,
    ):
        """Optimetrics variable arguments.

        Parameters
        ----------
        arg :

        optimetrics_type :

        variable_name : str
            Name of the variable.
        min_val : optional
            Minimum value for the variable. The default is ``None``.
        max_val :  optional
            Maximum value for the variable. The default is ``None``.
        tolerance : optional
            The default is ``None``.
        probability : optional
            The default is ``None``.
        mean : optional
            The default is ``None``.
        enable : bool, optional
            The default is ``True``.

        Returns
        -------

        """
        if variable_name not in self.variable_manager.variables:
            self.logger.error(f"Variable {variable_name} does not exists.")
            return False
        if variable_name.startswith("$"):
            tab = "NAME:ProjectVariableTab"
            propserver = "ProjectVariables"
        else:
            tab = "NAME:LocalVariableTab"
            propserver = "LocalVariables"
            if self.design_type == "HFSS 3D Layout Design":
                if variable_name in self.odesign.GetProperties("DefinitionParameterTab", "LocalVariables"):
                    tab = "NAME:DefinitionParameterTab"
            elif self.design_type == "Circuit Design":
                tab = "NAME:DefinitionParameterTab"
                propserver = f"Instance:{self._odesign.GetName()}"
        arg2 = ["NAME:" + optimetrics_type, "Included:=", enable]
        if min_val:
            arg2.append("Min:=")
            arg2.append(min_val)
        if max_val:
            arg2.append("Max:=")
            arg2.append(max_val)
        if tolerance:
            arg2.append("Tol:=")
            arg2.append(tolerance)
        if probability:
            arg2.append("Prob:=")
            arg2.append(probability)
        if mean:
            arg2.append("Mean:=")
            arg2.append(mean)
        arg3 = [tab, ["NAME:PropServers", propserver], ["NAME:ChangedProps", ["NAME:" + variable_name, arg2]]]
        arg.append(arg3)

    @pyaedt_function_handler(variable_name="name", min_val="minimum", max_val="maximum")
    def activate_variable_statistical(
        self, name, minimum=None, maximum=None, tolerance=None, probability=None, mean=None
    ):
        """Activate statitistical analysis for a variable and optionally set up ranges.

        Parameters
        ----------
        name : str
            Name of the variable.
        minimum : optional
            Minimum value for the variable. The default is ``None``.
        maximum : optional
            Maximum value for the variable. The default is ``None``.
        tolerance : optional
            Tolerance value for the variable. The default is ``None``.
        probability : optional
            Probability value for the variable. The default is ``None``.
        mean :
            Mean value for the variable. The default is ``None``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesign.ChangeProperty
        """
        arg = ["NAME:AllTabs"]
        self._optimetrics_variable_args(arg, "Statistical", name, minimum, maximum, tolerance, probability, mean)
        if "$" in name:
            self.oproject.ChangeProperty(arg)
        else:
            self.odesign.ChangeProperty(arg)
        return True

    @pyaedt_function_handler(variable_name="name", min_val="minimum", max_val="maximum")
    def activate_variable_optimization(self, name, minimum=None, maximum=None):
        """Activate optimization analysis for a variable and optionally set up ranges.

        Parameters
        ----------
        name : str
            Name of the variable.
        minimum : optional
            Minimum value for the variable. The default is ``None``.
        maximum : optional
            Maximum value for the variable. The default is ``None``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesign.ChangeProperty
        """
        arg = ["NAME:AllTabs"]
        self._optimetrics_variable_args(arg, "Optimization", name, minimum, maximum)
        if name.startswith("$"):
            self.oproject.ChangeProperty(arg)
        else:
            self.odesign.ChangeProperty(arg)
        return True

    @pyaedt_function_handler(variable_name="name", min_val="minimum", max_val="maximum")
    def activate_variable_sensitivity(self, name, minimum=None, maximum=None):
        """Activate sensitivity analysis for a variable and optionally set up ranges.

        Parameters
        ----------
        name : str
            Name of the variable.
        minimum : optional
            Minimum value for the variable. The default is ``None``.
        maximum : optional
            Maximum value for the variable. The default is ``None``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesign.ChangeProperty
        """
        arg = ["NAME:AllTabs"]
        self._optimetrics_variable_args(arg, "Sensitivity", name, minimum, maximum)
        if "$" in name:
            self.oproject.ChangeProperty(arg)
        else:
            self.odesign.ChangeProperty(arg)
        return True

    @pyaedt_function_handler(variable_name="name", min_val="minimum", max_val="maximum")
    def activate_variable_tuning(self, name, minimum=None, maximum=None):
        """Activate tuning analysis for a variable and optionally set up ranges.

        Parameters
        ----------
        name : str
            Name of the variable.
        minimum : optional
            Minimum value for the variable. The default is ``None``.
        maximum : optional
            Maximum value for the variable. The default is ``None``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesign.ChangeProperty
        """
        arg = ["NAME:AllTabs"]
        self._optimetrics_variable_args(arg, "Tuning", name, minimum, maximum)
        if "$" in name:
            self.oproject.ChangeProperty(arg)
        else:
            self.odesign.ChangeProperty(arg)
        return True

    @pyaedt_function_handler(variable_name="name")
    def deactivate_variable_statistical(self, name):
        """Deactivate the statistical analysis for a variable.

        Parameters
        ----------
        name : str
            Name of the variable.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesign.ChangeProperty
        """
        arg = ["NAME:AllTabs"]
        self._optimetrics_variable_args(arg, "Statistical", name, enable=False)
        if "$" in name:
            self.oproject.ChangeProperty(arg)
        else:
            self.odesign.ChangeProperty(arg)
        return True

    @pyaedt_function_handler(variable_name="name")
    def deactivate_variable_optimization(self, name):
        """Deactivate the optimization analysis for a variable.

        Parameters
        ----------
        name : str
            Name of the variable.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesign.ChangeProperty
        """
        arg = ["NAME:AllTabs"]
        self._optimetrics_variable_args(arg, "Optimization", name, enable=False)
        if "$" in name:
            self.oproject.ChangeProperty(arg)
        else:
            self.odesign.ChangeProperty(arg)
        return True

    @pyaedt_function_handler(variable_name="name")
    def deactivate_variable_sensitivity(self, name):
        """Deactivate the sensitivity analysis for a variable.

        Parameters
        ----------
        name : str
            Name of the variable.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesign.ChangeProperty
        """
        arg = ["NAME:AllTabs"]
        self._optimetrics_variable_args(arg, "Sensitivity", name, enable=False)
        if "$" in name:
            self.oproject.ChangeProperty(arg)
        else:
            self.odesign.ChangeProperty(arg)
        return True

    @pyaedt_function_handler(variable_name="name")
    def deactivate_variable_tuning(self, name):
        """Deactivate the tuning analysis for a variable.

        Parameters
        ----------
        name : str
            Name of the variable.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesign.ChangeProperty
        """
        arg = ["NAME:AllTabs"]
        self._optimetrics_variable_args(arg, "Tuning", name, enable=False)
        if "$" in name:
            self.oproject.ChangeProperty(arg)
        else:
            self.odesign.ChangeProperty(arg)
        return True

    @pyaedt_function_handler(variable_name="name")
    def hidden_variable(self, name, value=True):
        """Set the variable to a hidden or unhidden variable.

        Parameters
        ----------
        name : str or list
            One or more variable names.
        value : bool, optional
            Whether to hide the variable. The default is ``True``, in which case the variable
            is hidden. When ``False,`` the variable is unhidden.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesign.ChangeProperty

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss["my_hidden_leaf"] = "15mm"
        >>> hfss.hidden_variable("my_hidden_leaf",True)
        """
        if not isinstance(name, list):
            self.variable_manager[name].hidden = value
        else:
            design_variables = ["NAME:ChangedProps"]
            project_variables = ["NAME:ChangedProps"]
            for name in name:
                if name in self.variable_manager.design_variable_names:
                    design_variables.append(["NAME:" + name, "Hidden:=", value])
                elif name in self.variable_manager.project_variable_names:
                    project_variables.append(["NAME:" + name, "Hidden:=", value])

            if len(design_variables) > 1:
                command = [
                    "NAME:AllTabs",
                    ["NAME:LocalVariableTab", ["NAME:PropServers", "LocalVariables"], design_variables],
                ]
                self.odesign.ChangeProperty(command)
            if len(project_variables) > 1:
                command = [
                    "NAME:AllTabs",
                    ["NAME:ProjectVariableTab", ["NAME:PropServers", "ProjectVariables"], project_variables],
                ]
                self.oproject.ChangeProperty(command)
        return True

    @pyaedt_function_handler(variable_name="name")
    def read_only_variable(self, name, value=True):
        """Set the variable to a read-only or not read-only variable.

        Parameters
        ----------
        name : str
            Name of the variable.
        value : bool, optional
            Whether the variable is read-only. The default is ``True``, in which case
            the variable is read-only. When ``False``, the variable is not read-only.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesign.ChangeProperty

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss["my_read_only_variable"] = "15mm"
        >>> hfss.make_read_only_variable("my_read_only_variable")
        """
        self.variable_manager[name].read_only = value
        return True

    @pyaedt_function_handler()
    def _get_boundaries_data(self):
        """Retrieve boundary data.

        Returns
        -------
        list[:class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`]
        """
        boundaries = []
        if self.design_properties and "BoundarySetup" in self.design_properties:
            for ds in self.design_properties["BoundarySetup"]["Boundaries"]:
                try:
                    if isinstance(self.design_properties["BoundarySetup"]["Boundaries"][ds], dict):
                        if (
                            self.design_properties["BoundarySetup"]["Boundaries"][ds]["BoundType"] == "Network"
                            and self.design_type == "Icepak"
                        ):
                            boundaries.append(
                                NetworkObject(self, ds, self.design_properties["BoundarySetup"]["Boundaries"][ds])
                            )
                        else:
                            boundaries.append(
                                BoundaryObject(
                                    self,
                                    ds,
                                    self.design_properties["BoundarySetup"]["Boundaries"][ds],
                                    self.design_properties["BoundarySetup"]["Boundaries"][ds]["BoundType"],
                                )
                            )
                except Exception:
                    self.logger.debug("Failed to retrieve boundary data from 'BoundarySetup'.")
        if self.design_properties and "MaxwellParameterSetup" in self.design_properties:
            for ds in self.design_properties["MaxwellParameterSetup"]["MaxwellParameters"]:
                try:
                    param = "MaxwellParameters"
                    setup = "MaxwellParameterSetup"
                    if isinstance(self.design_properties[setup][param][ds], dict):
                        boundaries.append(
                            MaxwellParameters(
                                self,
                                ds,
                                self.design_properties["MaxwellParameterSetup"]["MaxwellParameters"][ds],
                                self.design_properties["MaxwellParameterSetup"]["MaxwellParameters"][ds][
                                    "MaxwellParameterType"
                                ],
                            )
                        )
                except Exception:
                    self.logger.debug("Failed to retrieve boundary data from 'MaxwellParameterSetup'.")
        if self.design_properties and "ModelSetup" in self.design_properties:
            if "MotionSetupList" in self.design_properties["ModelSetup"]:
                for ds in self.design_properties["ModelSetup"]["MotionSetupList"]:
                    try:
                        motion_list = "MotionSetupList"
                        setup = "ModelSetup"
                        # check moving part
                        if isinstance(self.design_properties[setup][motion_list][ds], dict):
                            boundaries.append(
                                BoundaryObject(
                                    self,
                                    ds,
                                    self.design_properties["ModelSetup"]["MotionSetupList"][ds],
                                    self.design_properties["ModelSetup"]["MotionSetupList"][ds]["MotionType"],
                                )
                            )
                    except Exception:
                        self.logger.debug("Failed to retrieve boundary data from 'ModelSetup'.")
        if self.design_type in ["HFSS 3D Layout Design"]:
            for port in self.oboundary.GetAllPortsList():
                bound = self._update_port_info(port)
                if bound:
                    boundaries.append(bound)
        return boundaries

    @pyaedt_function_handler()
    def _get_boundaries_object(self):
        """Retrieve boundary objects.

        Returns
        -------
        list
            Boundary objects.
        """
        boundaries = []
        boundaries_names = list(self.get_oo_name(self.odesign, "Boundaries"))
        if boundaries_names:
            boundaries = self.get_oo_object(self.odesign, "Boundaries")

        return boundaries

    @pyaedt_function_handler()
    def _get_ds_data(self, name, data):
        """

        Parameters
        ----------
        name :

        data :


        Returns
        -------

        """
        units = data["DimUnits"]
        numcol = len(units)
        x = []
        y = []
        z = None
        v = None
        if numcol > 2:
            z = []
            v = []
        if "Coordinate" in data:
            for el in data["Coordinate"]:
                x.append(el["CoordPoint"][0])
                y.append(el["CoordPoint"][1])
                if numcol > 2:
                    z.append(el["CoordPoint"][2])
                    v.append(el["CoordPoint"][3])
        else:
            new_list = [data["Points"][i : i + numcol] for i in range(0, len(data["Points"]), numcol)]
            for el in new_list:
                x.append(el[0])
                y.append(el[1])
                if numcol > 2:
                    z.append(el[2])
                    v.append(el[3])
        if numcol == 2:
            return DataSet(self, name, x, y, z, v, units[0], units[1])
        else:
            return DataSet(self, name, x, y, z, v, units[0], units[1], units[2], units[3])

    @pyaedt_function_handler()
    def _get_project_datasets(self):
        """ """
        datasets = {}
        try:
            for ds in self.project_properties["AnsoftProject"]["ProjectDatasets"]["DatasetDefinitions"]:
                data = self.project_properties["AnsoftProject"]["ProjectDatasets"]["DatasetDefinitions"][ds][
                    "Coordinates"
                ]
                datasets[ds] = self._get_ds_data(ds, data)
        except Exception:
            self.logger.debug("Failed to retrieve project data sets.")
        return datasets

    @pyaedt_function_handler()
    def _get_design_datasets(self):
        """ """
        datasets = {}
        try:
            for ds in self.design_properties["ModelSetup"]["DesignDatasets"]["DatasetDefinitions"]:
                data = self.design_properties["ModelSetup"]["DesignDatasets"]["DatasetDefinitions"][ds]["Coordinates"]
                datasets[ds] = self._get_ds_data(ds, data)
        except Exception:
            self.logger.debug("Failed to retrieve design data sets.")
        return datasets

    @pyaedt_function_handler()
    def close_desktop(self):
        """Close AEDT and release it.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        self.release_desktop()
        return True

    @pyaedt_function_handler()
    def autosave_disable(self):
        """Disable autosave in AEDT.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesktop.EnableAutoSave
        """
        self.odesktop.EnableAutoSave(False)
        return True

    @pyaedt_function_handler()
    def autosave_enable(self):
        """Enable autosave in AEDT.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesktop.EnableAutoSave
        """
        self.odesktop.EnableAutoSave(True)
        return True

    @pyaedt_function_handler()
    def release_desktop(self, close_projects=True, close_desktop=True):
        """Release AEDT.

        Parameters
        ----------
        close_projects : bool, optional
            Whether to close all projects. The default is ``True``.
        close_desktop : bool, optional
            Whether to close AEDT after releasing it. The default is ``True``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        self.desktop_class.release_desktop(close_projects, close_desktop)
        props = [a for a in dir(self) if not a.startswith("__")]
        for a in props:
            self.__dict__.pop(a, None)

        self._desktop_class = None
        gc.collect()
        return True

    @pyaedt_function_handler(subdir_name="name")
    def generate_temp_project_directory(self, name):
        """Generate a unique directory string to save a project to.

        This method creates a directory for storage of a project in the ``temp`` directory
        of the AEDT installation because this location is guaranteed to exist. If the ``name``
        parameter is defined, a subdirectory is added within the ``temp`` directory and a
        hash suffix is added to ensure that this directory is empty and has a unique name.

        Parameters
        ----------
        name : str
            Base name of the subdirectory to create in the ``temp`` directory.

        Returns
        -------
        str
            Base name of the created subdirectory.

        Examples
        --------
        >>> m3d = Maxwell3d()
        >>> proj_directory = m3d.generate_temp_project_directory("Example")

        """
        base_path = self.temp_directory

        if not isinstance(name, str):
            self.logger.error("Input argument 'subdir' must be a string")
            return False
        dir_name = generate_unique_name(name)
        project_dir = os.path.join(base_path, dir_name)
        try:
            if not os.path.exists(project_dir):
                os.makedirs(project_dir)
            return project_dir
        except OSError:
            return False

    @pyaedt_function_handler(
        project_file="file_name",
        design_name="design",
        close_active_proj="close_active",
        save_active_project="set_active",
    )
    def load_project(self, file_name, design=None, close_active=False, set_active=False):
        """Open an AEDT project based on a project and optional design.

        Parameters
        ----------
        file_name : str
            Full path of the project to load.
        design : str, optional
            Design name. The default is ``None``.
        close_active : bool, optional
            Whether to close the active project. The default is ``False``.
        set_active : bool, optional
            Whether to save the active project. The default is ``False``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesktop.OpenProject
        """
        proj = self.odesktop.OpenProject(file_name)
        if close_active and self.oproject:
            self._close_edb()
            self.close_project(self.project_name, save=set_active)
        if proj:
            self._init_design(project_name=proj.GetName(), design_name=design)
            return True
        else:
            return False

    @pyaedt_function_handler()
    def _close_edb(self):
        if self.design_type == "HFSS 3D Layout Design":  # pragma: no cover
            if self.modeler and self.modeler._edb:
                self.modeler._edb.close_edb()

    @pyaedt_function_handler(dsname="name", xlist="x", ylist="y", xunit="x_unit", yunit="y_unit")
    def create_dataset1d_design(self, name, x, y, x_unit="", y_unit="", sort=True):
        """Create a design dataset.

        Parameters
        ----------
        name : str
            Name of the dataset (without a prefix for a project dataset).
        x : list
            List of X-axis values for the dataset.
        y : list
            List of Y-axis values for the dataset.
        x_unit : str, optional
            Units for the X axis. The default is ``""``.
        y_unit : str, optional
            Units for the Y axis. The default is ``""``.
        sort : bool, optional
            Sort dataset. The default is ``True``.

        Returns
        -------
        :class:`ansys.aedt.core.application.variables.DataSet`

        References
        ----------
        >>> oProject.AddDataset
        >>> oDesign.AddDataset
        """
        return self.create_dataset(name, x, y, is_project_dataset=False, x_unit=x_unit, y_unit=y_unit, sort=sort)

    @pyaedt_function_handler(dsname="name", xlist="x", ylist="y", xunit="x_unit", yunit="y_unit")
    def create_dataset1d_project(self, name, x, y, x_unit="", y_unit="", sort=True):
        """Create a project dataset.

        Parameters
        ----------
        name : str
            Name of dataset (without a prefix for a project dataset).
        x : list
            List of X-axis values for the dataset.
        y : list
            List of Y-axis values for the dataset.
        x_unit : str, optional
            Units for the X axis. The default is ``""``.
        y_unit : str, optional
            Units for the Y axis. The default is ``""``.
        sort : bool, optional
            Sort dataset. The default is ``True``.

        Returns
        -------
        :class:`ansys.aedt.core.application.variables.DataSet`
            Dataset object when the dataset is created, ``False`` otherwise.

        References
        ----------
        >>> oProject.AddDataset
        >>> oDesign.AddDataset
        """
        return self.create_dataset(name, x, y, is_project_dataset=True, x_unit=x_unit, y_unit=y_unit, sort=sort)

    @pyaedt_function_handler(
        dsname="name",
        xlist="x",
        ylist="y",
        zlist="z",
        vlist="v",
        xunit="x_unit",
        yunit="y_unit",
        zunit="z_unit",
        vunit="v_unit",
    )
    def create_dataset3d(
        self, name, x, y, z=None, v=None, x_unit="", y_unit="", z_unit="", v_unit="", is_project_dataset=True, sort=True
    ):
        """Create a 3D dataset.

        Parameters
        ----------
        name : str
            Name of the dataset (without a prefix for a project dataset).
        x : list
            List of X-axis values for the dataset.
        y : list
            List of Y-axis values for the dataset.
        z : list, optional
            List of Z-axis values for a 3D dataset only. The default is ``None``.
        v : list, optional
            List of V-axis values for a 3D dataset only. The default is ``None``.
        x_unit : str, optional
            Units for the X axis. The default is ``""``.
        y_unit : str, optional
            Units for the Y axis. The default is ``""``.
        z_unit : str, optional
            Units for the Z axis for a 3D dataset only. The default is ``""``.
        v_unit : str, optional
            Units for the V axis for a 3D dataset only. The default is ``""``.
        is_project_dataset : bool, optional
            Whether it is a project data set. The default is ``True``.
        sort : bool, optional
            Sort dataset. The default is ``True``.

        Returns
        -------
        :class:`ansys.aedt.core.application.variables.DataSet`
            Dataset object when the dataset is created, ``False`` otherwise.

        References
        ----------
        >>> oDesign.AddDataset
        """
        if name[0] == "$":
            name = name[1:]
            is_project_dataset = True
        if self.design_type != "Maxwell 3D" and self.design_type != "Icepak":
            is_project_dataset = True

        return self.create_dataset(
            name=name,
            x=x,
            y=y,
            z=z,
            v=v,
            is_project_dataset=is_project_dataset,
            x_unit=x_unit,
            y_unit=y_unit,
            z_unit=z_unit,
            v_unit=v_unit,
            sort=sort,
        )

    @pyaedt_function_handler(filename="input_file", dsname="name")
    def import_dataset1d(self, input_file, name=None, is_project_dataset=True, sort=True):
        """Import a 1D dataset.

        Parameters
        ----------
        input_file : str
            Full path and name for the TAB file.
        name : str, optional
            Name of the dataset. The default is the file name.
        is_project_dataset : bool, optional
            Whether it is a project data set. The default is ``True``.
        sort : bool, optional
            Sort dataset. The default is ``True``.

        Returns
        -------
        :class:`ansys.aedt.core.application.variables.DataSet`

        References
        ----------
        >>> oProject.AddDataset
        >>> oDesign.AddDataset
        """
        with open_file(input_file, "r") as f:
            lines = f.read().splitlines()
        header = lines[0]
        points = lines[1:]

        header_list = header.split("\t")
        units = ["", ""]
        cont = 0
        for h in header_list:
            result = re.search(r"\[([A-Za-z0-9_]+)\]", h)
            if result:
                units[cont] = result.group(1)
            cont += 1

        xlist = []
        ylist = []
        for item in points:
            xlist.append(float(item.split()[0]))
            ylist.append(float(item.split()[1]))

        if not name:
            name = os.path.basename(os.path.splitext(input_file)[0])

        if name[0] == "$":
            name = name[1:]
            is_project_dataset = True

        return self.create_dataset(
            name, xlist, ylist, is_project_dataset=is_project_dataset, x_unit=units[0], y_unit=units[1], sort=sort
        )

    @pyaedt_function_handler(filename="input_file", dsname="name")
    def import_dataset3d(self, input_file, name=None, encoding="utf-8-sig", is_project_dataset=True, sort=True):
        """Import a 3D dataset.

        Parameters
        ----------
        input_file : str
            Full path and name for the tab/csv/xlsx file.
        name : str, optional
            Name of the dataset. The default is the file name.
        encoding : str, optional
            File encoding to be provided for csv.
        is_project_dataset : bool, optional
            Whether it is a project data set. The default is ``True``.
        sort : bool, optional
            Sort dataset. The default is ``True``.

        Returns
        -------
        :class:`ansys.aedt.core.application.variables.DataSet`

        References
        ----------
        >>> oProject.AddDataset
        """
        index_of_dot = input_file.rfind(".")
        file_extension = input_file[index_of_dot + 1 :]
        xlist = []
        ylist = []
        zlist = []
        vlist = []

        if file_extension == "xlsx":
            self.logger.warning("You need pandas and openpyxl library installed for reading excel files")
            lines = read_xlsx(input_file)
            if list(lines):
                header = str([lines.columns[i] for i in range(len(lines.columns))])
                xlist = list((lines.iloc[:, 0]).array)
                ylist = list((lines.iloc[:, 1]).array)
                zlist = list((lines.iloc[:, 2]).array)
                vlist = list((lines.iloc[:, 3]).array)
            else:
                self.logger.error("Pandas is not installed. Either install pandas or save the file as .csv or .tab.")
                return False

        elif file_extension == "csv":
            lines = read_csv(input_file, encoding)
            header = " ".join(lines[0])
            for row in lines[1:]:
                xlist.append(float(row[0]))
                ylist.append(float(row[1]))
                zlist.append(float(row[2]))
                vlist.append(float(row[3]))

        elif file_extension == "tab":
            lines = read_tab(input_file)
            header = lines[0]
            for item in lines[1:]:
                xlist.append(float(item.split()[0]))
                ylist.append(float(item.split()[1]))
                zlist.append(float(item.split()[2]))
                vlist.append(float(item.split()[3]))

        header_list = header.split()
        units = ["", "", "", ""]
        cont = 0
        for h in header_list:
            result = re.search(r"\[([A-Za-z0-9_]+)\]", h)
            if result:
                units[cont] = result.group(1)
            cont += 1

        if not name:
            name = os.path.basename(os.path.splitext(input_file)[0])

        if name[0] == "$":
            name = name[1:]
            is_project_dataset = True
        if self.design_type != "Maxwell 3D" and self.design_type != "Icepak":
            is_project_dataset = True

        return self.create_dataset(
            name,
            xlist,
            ylist,
            zlist,
            vlist,
            is_project_dataset=is_project_dataset,
            x_unit=units[0],
            y_unit=units[1],
            z_unit=units[2],
            v_unit=units[3],
            sort=sort,
        )

    @pyaedt_function_handler(
        dsname="name",
        xlist="x",
        ylist="y",
        zlist="z",
        vlist="v",
        xunit="x_unit",
        yunit="y_unit",
        zunit="z_unit",
        vunit="v_unit",
    )
    def create_dataset(
        self, name, x, y, z=None, v=None, is_project_dataset=True, x_unit="", y_unit="", z_unit="", v_unit="", sort=True
    ):
        """Create a dataset.

        Parameters
        ----------
        name : str
            Name of the dataset (without a prefix for a project dataset).
        x : list
            List of X-axis values for the dataset.
        y : list
            List of Y-axis values for the dataset.
        z : list, optional
            List of Z-axis values for a 3D dataset only. The default is ``None``.
        v : list, optional
            List of V-axis values for a 3D dataset only. The default is ``None``.
        is_project_dataset : bool, optional
            Whether it is a project data set. The default is ``True``.
        x_unit : str, optional
            Units for the X axis. The default is ``""``.
        y_unit : str, optional
            Units for the Y axis. The default is ``""``.
        z_unit : str, optional
            Units for the Z axis for a 3D dataset only. The default is ``""``.
        v_unit : str, optional
            Units for the V axis for a 3D dataset only. The default is ``""``.
        sort : bool, optional
            Sort dataset. The default is ``True``.

        Returns
        -------
        :class:`ansys.aedt.core.application.variables.DataSet`
            Dataset object when the dataset is created, ``False`` otherwise.

        References
        ----------
        >>> oProject.AddDataset
        >>> oDesign.AddDataset
        """
        if not self.dataset_exists(name, is_project_dataset):
            if is_project_dataset:
                name = "$" + name
            ds = DataSet(self, name, x, y, z, v, x_unit, y_unit, z_unit, v_unit, sort)
        else:
            self.logger.warning("Dataset %s already exists", name)
            return False
        ds.create()
        if is_project_dataset:
            self.project_datasets[name] = ds
        else:
            self.design_datasets[name] = ds
        self.logger.info("Dataset %s created successfully.", name)
        return ds

    @pyaedt_function_handler()
    def dataset_exists(self, name, is_project_dataset=True):
        """Check if a dataset exists.

        Parameters
        ----------
        name : str
            Name of the dataset (without a prefix for a project dataset).
        is_project_dataset : bool, optional
            Whether it is a project data set. The default is ``True``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        if is_project_dataset and "$" + name in self.project_datasets:
            self.logger.info("Dataset %s$ exists.", name)
            return True
            # self.oproject.ExportDataSet("$"+name, os.path.join(self.temp_directory, "ds.tab"))
        elif not is_project_dataset and name in self.design_datasets:
            self.logger.info("Dataset %s exists.", name)
            return True
            # self.odesign.ExportDataSet(name, os.path.join(self.temp_directory, "ds.tab"))
        self.logger.info("Dataset %s doesn't exist.", name)
        return False

    @pyaedt_function_handler()
    def change_design_settings(self, settings):
        """Set Design Settings.

        Parameters
        ----------
        settings : dict
            Dictionary of settings with value to apply.

        Returns
        -------
        bool
        """
        arg = ["NAME:Design Settings Data"]
        for key, value in settings.items():
            if "SkewSliceTable" not in key:
                arg.append(key + ":=")
                arg.append(value)
            else:
                arg_skew = [key]
                if isinstance(value, list):
                    for v in value:
                        arg_skew.append(v)
                arg.append(arg_skew)
        self.odesign.SetDesignSettings(arg)
        return True

    @pyaedt_function_handler()
    def change_automatically_use_causal_materials(self, lossy_dielectric=True):
        """Enable or disable the automatic use of causal materials for lossy dielectrics.

        Parameters
        ----------
        lossy_dielectric : bool, optional
            Whether to enable causal materials.
            The default is ``True``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesign.SetDesignSettings
        """
        if lossy_dielectric:
            self.logger.info("Enabling Automatic use of causal materials")
        else:
            self.logger.info("Disabling Automatic use of causal materials")
        return self.change_design_settings({"Calculate Lossy Dielectrics": lossy_dielectric})

    @pyaedt_function_handler()
    def change_material_override(self, material_override=True):
        """Enable or disable the material override in the project.

        Parameters
        ----------
        material_override : bool, optional
            Whether to enable the material override.
            The default is ``True``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesign.SetDesignSettings
        """
        if material_override:
            self.logger.info("Enabling Material Override")
        else:
            self.logger.info("Disabling Material Override")
        return self.change_design_settings({"Allow Material Override": material_override})

    @pyaedt_function_handler()
    def change_validation_settings(
        self, entity_check_level="Strict", ignore_unclassified=False, skip_intersections=False
    ):
        """Update the validation design settings.

        Parameters
        ----------
        entity_check_level : str, optional
            Entity check level. The default is ``"Strict"``.
            Options are ``"Strict"``, ``"Basic"``, ``"Warning Only"``, ``"None"``.
        ignore_unclassified : bool, optional
            Whether to ignore unclassified elements. The default is ``False``.
        skip_intersections : bool, optional
            Whether to skip intersections. The default is ``False``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesign.SetDesignSettings
        """
        self.logger.info("Changing the validation design settings")
        self.odesign.SetDesignSettings(
            ["NAME:Design Settings Data"],
            [
                "NAME:Model Validation Settings",
                "EntityCheckLevel:=",
                entity_check_level,
                "IgnoreUnclassifiedObjects:=",
                ignore_unclassified,
                "SkipIntersectionChecks:=",
                skip_intersections,
            ],
        )
        return True

    @pyaedt_function_handler()
    def clean_proj_folder(self, directory=None, name=None):
        """Delete a project folder.

        Parameters
        ----------
        directory : str, optionl
            Name of the directory. The default is ``None``, in which case the active project is
            deleted from the ``aedtresults`` directory.
        name : str, optional
            Name of the project. The default is ``None``, in which case the data for the
            active project is deleted.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        if not name:
            name = self.project_name
        if not directory:
            directory = self.results_directory
        self.logger.info("Cleanup folder %s from project %s", directory, name)
        if os.path.exists(directory):
            shutil.rmtree(directory, True)
            if not os.path.exists(directory):
                os.makedirs(directory)
        self.logger.info("Project Directory cleaned")
        return True

    @pyaedt_function_handler(path="destination", dest="name")
    def copy_project(self, destination, name):
        """Copy the project to another destination.

        .. note::
           This method saves the project before copying it.

        Parameters
        ----------
        destination : str
            Path to save a copy of the project to.
        name :
            Name to give the project in the new destination.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oProject.SaveAs
        """
        self.logger.info("Copy AEDT Project ")
        self.oproject.Save()
        self.oproject.SaveAs(os.path.join(destination, name + ".aedt"), True)
        return True

    @pyaedt_function_handler(proj_name="name")
    def create_new_project(self, name):
        """Create a project within AEDT.

        Parameters
        ----------
        name :
            Name of the project.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesktop.NewProject
        """
        self.logger.info("Creating new Project ")
        prj = self.odesktop.NewProject(name)
        prj_name = prj.GetName()
        self.oproject = prj_name
        self.odesign = None
        return True

    @pyaedt_function_handler(save_project="save")
    def close_project(self, name=None, save=True):
        """Close an AEDT project.

        Parameters
        ----------
        name : str, optional
            Name of the project. The default is ``None``, in which case the
            active project is closed.
        save : bool, optional
            Whether to save the project before closing it. The default is
            ``True``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesktop.CloseProject
        """
        legacy_name = self.project_name
        if name and name not in self.project_list:
            self.logger.warning("Project named '%s' was not found.", name)
            return False
        if not name:
            name = self.project_name
            if self.design_type == "HFSS 3D Layout Design":
                self._close_edb()
        self.logger.info(f"Closing the AEDT Project {name}")
        oproj = self.desktop_class.active_project(name)
        proj_path = oproj.GetPath()
        proj_file = os.path.join(proj_path, name + ".aedt")
        if save:
            oproj.Save()
        if name == legacy_name:
            self._global_logger.remove_file_logger(name)
            self._logger = self._global_logger
        self.odesktop.CloseProject(name)
        if name == legacy_name:
            self._init_variables()
            self._oproject = None
            self._odesign = None
            self.logger.odesign = None
            self.logger.oproject = None
            self.design_solutions._odesign = None
            AedtObjects.__init__(self, self._desktop_class, is_inherithed=True)
        else:
            self.desktop_class.active_project(legacy_name)

        i = 0
        timeout = 10
        while True:
            if not os.path.exists(os.path.join(proj_path, name + ".aedt.lock")):
                self.logger.info(f"Project {name} closed correctly")
                break
            elif i > timeout:
                self.logger.warning("Lock File still exists.")
                break
            else:
                i += 0.2
                time.sleep(0.2)

        if os.path.normpath(proj_file) in inner_project_settings.properties:
            del inner_project_settings.properties[os.path.normpath(proj_file)]
        return True

    @pyaedt_function_handler()
    def delete_design(self, name=None, fallback_design=None):
        """Delete a design from the current project.

        .. warning::
           This method does not work from the toolkit.

        Parameters
        ----------
        name : str, optional
            Name of the design. The default is ``None``, in which case
            the active design is deleted.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oProject.DeleteDesign
        """
        if not name:
            name = self.design_name
        self.oproject.DeleteDesign(name)
        if name != self.design_name:
            return True
        if fallback_design and (
            fallback_design in [x for i in list(self._oproject.GetDesigns()) for x in (i.GetName(), i.GetName()[2:])]
        ):
            try:
                self.set_active_design(fallback_design)
            except Exception:
                if is_windows:
                    self._init_variables()
                self._odesign = None
                self.logger.odesign = None
                self.design_solutions._odesign = None
                AedtObjects.__init__(self, self._desktop_class, project=self.oproject, is_inherithed=True)
                return False
        else:
            if is_windows:
                self._init_variables()
            self._odesign = None
            self.logger.odesign = None
            self.design_solutions._odesign = None
            AedtObjects.__init__(self, self._desktop_class, project=self.oproject, is_inherithed=True)
        return True

    @pyaedt_function_handler(separator_name="name")
    def delete_separator(self, name):
        """Delete a separator from either the active project or a design.

        Parameters
        ----------
        name : str
            Name of the separator.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oProject.ChangeProperty
        >>> oDesign.ChangeProperty
        """
        return self._variable_manager.delete_separator(name)

    @pyaedt_function_handler(sVarName="name")
    def delete_variable(self, name):
        """Delete a variable.

        Parameters
        ----------
        name :
            Name of the variable.

        References
        ----------
        >>> oProject.ChangeProperty
        >>> oDesign.ChangeProperty
        """
        return self.variable_manager.delete_variable(name)

    @pyaedt_function_handler()
    def delete_unused_variables(self):
        """Delete design and project unused variables.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        return self.variable_manager.delete_unused_variables()

    @pyaedt_function_handler(design_name="name")
    def insert_design(self, name=None, solution_type=None):
        """Add a design of a specified type.

        The default design type is taken from the derived application class.

        Parameters
        ----------
        name : str, optional
            Name of the design. The default is ``None``, in which case the
            default design name is ``<Design-Type>Design<_index>``. If the
            given or default design name is in use, then an underscore and
            index is added to ensure that the design name is unique.
            The inserted object is assigned to the ``Design`` object.
        solution_type : str, optional
            Solution type to apply to the design. The default is
            ``None``, in which case the default type is applied.

        Returns
        -------
        str
            Name of the design.

        References
        ----------
        >>> oProject.InsertDesign
        """
        self._close_edb()
        return self._init_design(
            project_name=self.project_name if self.project_name else generate_unique_name("Project"),
            design_name=name,
            solution_type=solution_type if solution_type else self.solution_type,
        )

    def _insert_design(self, design_type, design_name=None):
        if design_type not in self.design_solutions.design_types:
            raise ValueError(f"Design type of insert '{design_type}' is invalid.")

        # self.save_project() ## Commented because it saves a Projectxxx.aedt when launched on an empty Desktop
        unique_design_name = self._generate_unique_design_name(design_name)

        if design_type == "RMxprtSolution":
            new_design = self._oproject.InsertDesign("RMxprt", unique_design_name, "Inner-Rotor Induction Machine", "")
        elif design_type == "ModelCreation":
            new_design = self._oproject.InsertDesign(
                "RMxprt", unique_design_name, "Model Creation Inner-Rotor Induction Machine", ""
            )
        elif design_type == "Icepak":
            new_design = self._oproject.InsertDesign("Icepak", unique_design_name, "SteadyState TemperatureAndFlow", "")
        elif design_type == "Circuit Design":
            new_design = self._oproject.InsertDesign(design_type, unique_design_name, "None", "")
        else:
            if design_type == "HFSS" and self._aedt_version < "2021.2":
                new_design = self._oproject.InsertDesign(design_type, unique_design_name, "DrivenModal", "")
            elif design_type == "HFSS" and self._aedt_version < "2024.1":
                new_design = self._oproject.InsertDesign(design_type, unique_design_name, "HFSS Modal Network", "")
            else:
                new_design = self._oproject.InsertDesign(
                    design_type, unique_design_name, self.default_solution_type, ""
                )
        if not is_windows and settings.aedt_version and self.design_type == "Circuit Design":
            time.sleep(1)
            self.desktop_class.close_windows()
        if new_design is None:  # pragma: no cover
            new_design = self.desktop_class.active_design(self.oproject, unique_design_name, self.design_type)
            if new_design is None:
                self.logger.error("Failed to create design.")
                return
        self.logger.info("Added design '%s' of type %s.", unique_design_name, design_type)
        name = new_design.GetName()
        self._odesign = new_design
        return name

    @pyaedt_function_handler()
    def _generate_unique_design_name(self, design_name):
        """Generate an unique design name.

        Parameters
        ----------
        design_name : str
            Name of the design.


        Returns
        -------
        str
            Name of the design.

        """
        design_index = 0
        suffix = ""
        if not design_name:
            char_set = string.ascii_uppercase + string.digits
            uName = "".join(random.sample(char_set, 3))
            design_name = self._design_type + "_" + uName
        while design_name in self.design_list:
            if design_index:
                design_name = design_name[0 : -len(suffix)]
            design_index += 1
            suffix = "_" + str(design_index)
            design_name += suffix
        return design_name

    @pyaedt_function_handler()
    def _generate_unique_project_name(self):
        """Generate an unique project name.

        Returns
        --------
        str
            Unique project name in the form ``"Project_<unique_name>.aedt".

        """
        char_set = string.ascii_uppercase + string.digits
        uName = "".join(random.sample(char_set, 3))
        proj_name = "Project_" + uName + ".aedt"
        return proj_name

    @pyaedt_function_handler(new_name="name", save_after_duplicate="save")
    def rename_design(self, name, save=True):
        """Rename the active design.

        Parameters
        ----------
        name : str
            New name of the design.
        save : bool, optional
            Save project after the duplication is completed. If ``False``, pyaedt objects like boundaries will not be
            available.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesign.RenameDesignInstance
        """
        self._odesign.RenameDesignInstance(self.design_name, name)
        self._design_name = None
        if save:
            self.oproject.Save()
            self._project_dictionary = None
        return True

    @pyaedt_function_handler(project_fullname="project", design_name="design")
    def copy_design_from(self, project, design, save_project=True, set_active_design=True):
        """Copy a design from a project into the active project.

        Parameters
        ----------
        project : str
            Full path and name for the project containing the design to copy.
            The active design is maintained.
        design : str
            Name of the design to copy into the active design. If a design with this
            name is already present in the destination project, AEDT automatically
            changes the name.
        save_project : bool, optional
            Save the project after the design has been copied. Default value is `True`.
        set_active_design : bool, optional
            Set the design active after it has been copied. Default value is `True`.

        Returns
        -------
        str
           Name of the copied design name when successful or ``None`` when failed.
           Failure is generally a result of the name specified for ``design_name``
           not existing in the project specified for ``project_fullname``.

        References
        ----------
        >>> oProject.CopyDesign
        >>> oProject.Paste
        """
        self.save_project()
        active_design = self.design_name
        # open the origin project
        if os.path.exists(project):
            proj_from = self.odesktop.OpenProject(project)
            proj_from_name = proj_from.GetName()
        else:
            return None
        # check if the requested design exists in the origin project
        if design not in [x for i in list(proj_from.GetDesigns()) for x in (i.GetName(), i.GetName()[2:])]:
            return None
        # copy the source design
        proj_from.CopyDesign(design)
        # paste in the destination project and get the name
        self._oproject.Paste()
        new_designname = self.desktop_class.active_design(self._oproject, design_type=self.design_type).GetName()
        if (
            self.desktop_class.active_design(self._oproject, design_type=self.design_type).GetDesignType()
            == "HFSS 3D Layout Design"
        ):
            new_designname = new_designname[2:]  # name is returned as '2;EMDesign3'
        # close the source project
        self.odesktop.CloseProject(proj_from_name)
        if save_project:
            self.save_project()
        if set_active_design:
            self._close_edb()
            self._init_design(project_name=self.project_name, design_name=new_designname)
            self.set_active_design(active_design)
        # return the pasted design name
        return new_designname

    @pyaedt_function_handler(label="name")
    def duplicate_design(self, name, save_after_duplicate=True):
        """Copy a design to a new name.

        The new name consists of the original
        design name plus a suffix of ``MMode`` and a running index
        as necessary to allow for multiple calls.

        Parameters
        ----------
        name : str
            Name of the design to copy.
        save_after_duplicate : bool, optional
            Save project after the duplication is completed. If ``False``, pyaedt objects like boundaries will not be
            available.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oProject.CopyDesign
        >>> oProject.Paste
        """
        active_design = self.design_name
        design_list = self.design_list
        self._oproject.CopyDesign(active_design)
        self._oproject.Paste()
        newname = name
        ind = 1
        while newname in self.design_list:
            newname = name + "_" + str(ind)
            ind += 1
        actual_name = [i for i in self.design_list if i not in design_list]
        self.odesign = actual_name[0]
        self.design_name = newname
        self._close_edb()
        AedtObjects.__init__(self, self._desktop_class, self.oproject, self.odesign, is_inherithed=True)
        if save_after_duplicate:
            self.oproject.Save()
            self._project_dictionary = None
        return True

    @pyaedt_function_handler(filename="output_file")
    def export_design_preview_to_jpg(self, output_file):
        """Export design preview image to a JPG file.

        Parameters
        ----------
        output_file : str
            Full path and name for the JPG file.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        design_info = self.project_properties["ProjectPreview"]["DesignInfo"]
        if not isinstance(design_info, dict):
            # there are multiple designs, find the right one
            # is self.design_name guaranteed to be there?
            design_info = [design for design in design_info if design["DesignName"] == self.design_name][0]
        image_data_str = design_info["Image64"]
        with open_file(output_file, "wb") as f:
            if sys.version_info.major == 2:
                bytestring = bytes(image_data_str).decode("base64")
            else:
                bytestring = base64.decodebytes(image_data_str.encode("ascii"))
            f.write(bytestring)
        return True

    @pyaedt_function_handler(
        filename="output_file", export_project="export_project_variables", export_design="export_design_properties"
    )
    def export_variables_to_csv(self, output_file, export_project_variables=True, export_design_properties=True):
        """Export design properties, project variables, or both to a CSV file.

        Parameters
        ----------
        output_file : str
            Full path and name for the CSV file.
        export_project_variables : bool, optional
            Whether to export project variables. The default is ``True``.
        export_design_properties : bool, optional
            Whether to export design properties. The default is ``True``.


        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oProject.GetProperties
        >>> oDesign.GetProperties
        >>> oProject.GetVariableValue
        >>> oDesign.GetVariableValue
        """
        varnames = []
        desnames = []
        if export_project_variables:
            varnames = self.oproject.GetProperties("ProjectVariableTab", "ProjectVariables")
        if export_design_properties:
            desnames = self.odesign.GetProperties("LocalVariableTab", "LocalVariables")
            if self.design_type in ["HFSS 3D Layout Design", "Circuit Design"]:
                desnames.extend(self.odesign.GetProperties("DefinitionParameterTab", "LocalVariables"))
        list_full = [["Name", "Value"]]
        for el in varnames:
            value = self.oproject.GetVariableValue(el)
            list_full.append([el, value])
        for el in desnames:
            value = self.odesign.GetVariableValue(el)
            list_full.append([el, value])
        return write_csv(output_file, list_full)

    @pyaedt_function_handler()
    def read_design_data(self):
        """Read back the design data as a dictionary.

        Returns
        -------
        dict
            Dictionary of the design data.

        """
        design_file = os.path.join(self.working_directory, "design_data.json")
        with open_file(design_file, "r") as fps:
            design_data = json.load(fps)
        return design_data

    @pyaedt_function_handler(project_file="file_name", refresh_obj_ids_after_save="refresh_ids")
    def save_project(self, file_name=None, overwrite=True, refresh_ids=False):
        """Save the project and add a message.

        Parameters
        ----------
        file_name : str, optional
            Full path and project name. The default is ````None``.
        overwrite : bool, optional
            Whether to overwrite the existing project. The default is ``True``.
        refresh_ids : bool, optional
            Whether to refresh object IDs after saving the project.
            The default is ``False``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oProject.Save
        >>> oProject.SaveAs
        """
        if file_name:
            file_parent_dir = os.path.dirname(os.path.normpath(file_name))
            if settings.remote_rpc_session and not settings.remote_rpc_session.filemanager.pathexists(file_parent_dir):
                settings.remote_rpc_session.filemanager.makedirs(file_parent_dir)
            elif not settings.remote_rpc_session and not os.path.isdir(file_parent_dir):
                os.makedirs(file_parent_dir)
            self.oproject.SaveAs(file_name, overwrite)
            self._add_handler()
        else:
            self.oproject.Save()
        if refresh_ids:
            self.modeler.refresh_all_ids()
            self.modeler._refresh_all_ids_wrapper()
            self.mesh._refresh_mesh_operations()
        self._project_name = None
        self._project_path = None
        msg_text = f"Project {self.project_name} Saved correctly"
        self.logger.info(msg_text)
        return True

    @pyaedt_function_handler(project_file="project_path", additional_file_lists="additional_files")
    def archive_project(
        self,
        project_path=None,
        include_external_files=True,
        include_results_file=True,
        additional_files=None,
        notes="",
    ):
        """Archive the AEDT project and add a message.

        Parameters
        ----------
        project_path : str, optional
            Full path and project name. The default is ``None``.
        include_external_files : bool, optional
            Whether to include external files in the archive. The default is ``True``.
        include_results_file : bool, optional
            Whether to include simulation results files in the archive. The default is ``True``.
        additional_files : list, optional
            List of additional files to add to the archive.
            The default is ``None`` in which case an empty list is set.
        notes : str, optional
            Simulation notes to add to the archive. The default is ``""``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oProject.Save
        >>> oProject.SaveProjectArchive
        """
        additional_files = [] if additional_files is None else additional_files
        msg_text = f"Saving {self.project_name} Project"
        self.logger.info(msg_text)
        if not project_path:
            project_path = os.path.join(self.project_path, self.project_name + ".aedtz")
        self.oproject.Save()
        self.oproject.SaveProjectArchive(
            project_path, include_external_files, include_results_file, additional_files, notes
        )
        return True

    @pyaedt_function_handler(project_name="name")
    def delete_project(self, name):
        """Delete a project.

        Parameters
        ----------
        name : str
            Name of the project.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesktop.DeleteProject
        """
        if self.project_name == name:
            raise ValueError("You cannot delete the active project.")
        self.odesktop.DeleteProject(name)
        return True

    @pyaedt_function_handler()
    def set_active_design(self, name):
        """Change the active design to another design.

        Parameters
        ----------
        name :
            Name of the design to make active.

        References
        ----------
        >>> oProject.SetActiveDesign
        """
        self._close_edb()
        self._init_design(project_name=self.project_name, design_name=name)
        return True

    @pyaedt_function_handler(logfile="log_file")
    def validate_simple(self, log_file=None):
        """Validate a design.

        Parameters
        ----------
        log_file : str, optional
            Name of the log file to save validation information to.
            The default is ``None``.

        Returns
        -------
        int
            ``1`` when successful, ``0`` when failed.

        References
        ----------
        >>> oDesign.ValidateDesign
        """
        if log_file:
            return self._odesign.ValidateDesign(log_file)
        else:
            return self._odesign.ValidateDesign()

    @pyaedt_function_handler(variable_name="name")
    def get_evaluated_value(self, name, units=None):
        """Retrieve the evaluated value of a design property or project variable in SI units if no unit is provided.

        Parameters
        ----------
        name : str
            Name of the design property or project variable.
        units : str, optional
            Name of the unit to use for rescaling. The default is ``None``,
            in which case SI units are applied by default.

        Returns
        -------
        float
            Evaluated value of the design property or project variable in SI units.

        References
        ----------
        >>> oDesign.GetNominalVariation
        >>> oDesign.GetVariationVariableValue

        Examples
        --------

        >>> M3D = Maxwell3d()
        >>> M3D["p1"] = "10mm"
        >>> M3D["p2"] = "20mm"
        >>> M3D["p3"] = "P1 * p2"
        >>> eval_p3 = M3D.get_evaluated_value("p3")
        """
        val = None
        var_obj = None
        if "$" in name:
            app = self._oproject
            var_obj = self.get_oo_object(app, f"Variables/{name}")

        else:
            app = self._odesign
            if self.design_type in ["Circuit Design", "Twin Builder", "HFSS 3D Layout Design"]:
                if name in self.get_oo_name(app, f"Instance:{self._odesign.GetName()}"):
                    var_obj = self.get_oo_object(app, f"Instance:{self._odesign.GetName()}/{name}")
                elif name in self.get_oo_object(app, "DefinitionParameters").GetPropNames():
                    val = self.get_oo_object(app, "DefinitionParameters").GetPropEvaluatedValue(name)
            else:
                var_obj = self.get_oo_object(app, f"Variables/{name}")
        if var_obj:
            val = var_obj.GetPropValue("SIValue")
        elif not val:
            try:
                variation_string = self._odesign.GetNominalVariation()
                val = self._odesign.GetVariationVariableValue(variation_string, name)  # pragma: no cover
            except Exception:
                val_units = app.GetVariableValue(name)
                val, original_units = decompose_variable_value(val_units)
                try:
                    if original_units:
                        scale = AEDT_UNITS[unit_system(original_units)][original_units]
                        if isinstance(scale, tuple):  # pragma: no cover
                            val = scale[0](val, True)
                        else:
                            val = val * scale
                except (ValueError, KeyError, TypeError, AttributeError):  # pragma: no cover
                    return val_units
        try:
            if units:
                scale = AEDT_UNITS[unit_system(units)][units]
                if isinstance(scale, tuple):  # pragma: no cover
                    return scale[0](val, True)
                else:
                    return val * scale
            return float(val)
        except (ValueError, KeyError, TypeError, AttributeError):  # pragma: no cover
            return val

    @pyaedt_function_handler(expression_string="expression")
    def evaluate_expression(self, expression):
        """Evaluate a valid string expression and return the numerical value in SI units.

        Parameters
        ----------
        expression : str
            A valid string expression for a design property or project variable.
            For example, ``"34mm*sqrt(2)"`` or ``"$G1*p2/34"``.

        Returns
        -------
        float
            Evaluated value for the string expression.

        """
        # Set the value of an internal reserved design variable to the specified string
        if expression in self._variable_manager.variables:
            return self._variable_manager.variables[expression].value
        elif "pwl" in str(expression):
            for ds in self.project_datasets:
                if ds in expression:
                    return expression
            for ds in self.design_datasets:
                if ds in expression:
                    return expression
        try:
            return float(expression)
        except ValueError:
            pass
        try:
            variable_name = "pyaedt_evaluator"
            if "$" in expression:
                variable_name = "$pyaedt_evaluator"
            self._variable_manager.set_variable(
                variable_name, expression=expression, read_only=True, hidden=True, description="Internal_Evaluator"
            )
            eval_value = self._variable_manager.variables[variable_name].value
            # Extract the numeric value of the expression (in SI units!)
            self._variable_manager.delete_variable(variable_name)
            return eval_value
        except Exception:
            self.logger.warning(f"Invalid string expression {expression}")
            return expression

    @pyaedt_function_handler(variation_string="variation")
    def design_variation(self, variation=None):
        """Generate a string to specify a desired variation.

        This method converts an input string defining a desired solution variation into a valid
        string taking into account all existing design properties and project variables, including
        dependent (non-sweep) properties.

        This is needed because the standard method COM function ``GetVariationVariableValue``
        does not work for obtaining values of dependent (non-sweep) variables.
        Using the object-oriented scripting model, which is a beta feature, could make this redundant in
        future releases.

        Parameters
        ----------
        variation : str, optional
            Variation string. For example, ``"p1=1mm"`` or ``"p2=3mm"``.

        Returns
        -------
        str
            String specifying the desired variation.

        References
        ----------
        >>> oDesign.GetNominalVariation
        """
        nominal = self._odesign.GetNominalVariation()
        if variation:
            # decompose the nominal variation into a dictionary of name[value]
            nominal_dict = variation_string_to_dict(nominal)

            # decompose the desired variation into a dictionary of name[value]
            var_dict = variation_string_to_dict(variation)

            # set the values of the desired variation in the active design
            for key, value in var_dict.items():
                self[key] = value

            # get the desired variation values
            nominal = self._odesign.GetNominalVariation()

            # Reset the nominal values in the active design
            for key in var_dict:
                self[key] = nominal_dict[key]

        return nominal

    @pyaedt_function_handler()
    def _assert_consistent_design_type(self, des_name):
        if des_name in self.design_list:
            self._odesign = self.desktop_class.active_design(self.oproject, des_name, self.design_type)
            dtype = self._odesign.GetDesignType()
            if dtype != "RMxprt":
                if dtype != self._design_type:
                    raise ValueError(f"Specified design is not of type {self._design_type}.")
            elif self._design_type not in {"RMxprtSolution", "ModelCreation"}:
                raise ValueError(f"Specified design is not of type {self._design_type}.")

            return True
        elif ":" in des_name:
            try:
                self._odesign = self.desktop_class.active_design(self.oproject, des_name, self.design_type)
                return True
            except Exception:
                return des_name
        else:
            return des_name

    @pyaedt_function_handler()
    def _check_solution_consistency(self):
        """Check solution consistency."""
        if self.design_type in ["Circuit Design", "Twin Builder", "HFSS 3D Layout Design", "EMIT", "Q3D Extractor"]:
            return True
        self.design_solutions._odesign = self._odesign
        if self.design_solutions and self.design_solutions.solution_type:
            return self.design_solutions.solution_type in self._odesign.GetSolutionType()
        else:
            return True

    @pyaedt_function_handler()
    def _check_design_consistency(self):
        """ """
        consistent = False
        destype = self._odesign.GetDesignType()
        if destype == self._design_type:
            consistent = self._check_solution_consistency()
        return consistent

    @pyaedt_function_handler(toolkit_object="toolkit")
    def add_from_toolkit(self, toolkit, draw=False, **kwargs):
        """Add a new toolkit to the current application.

        Parameters
        ----------
        toolkit :
            Application object from ``"ansys.aedt.toolkits"``.


        Returns
        -------
            Application-created object.
        """
        app = toolkit(self, **kwargs)
        if draw:
            app.init_model()
            app.model_hfss()
            app.setup_hfss()
        return app

    @pyaedt_function_handler(project_path="input_file")
    def check_if_project_is_loaded(self, input_file):
        """Check if a project path is already loaded in active Desktop.

        Parameters
        ----------
        input_file : str
            Project path to check in active desktop.

        Returns
        -------
        str
            Project name if loaded in Desktop.
        """
        for p in self.odesktop.GetProjects():
            if os.path.normpath(os.path.join(p.GetPath(), p.GetName()) + ".aedt") == os.path.normpath(input_file):
                return p.GetName()
        return False

    @pyaedt_function_handler(temp_dir_path="path")
    def set_temporary_directory(self, path):
        """Set temporary directory path.

        Parameters
        ----------
        path : str
            Temporary directory path.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesktop.SetTempDirectory()
        """
        self.odesktop.SetTempDirectory(path)
        return True

    @pyaedt_function_handler()
    def edit_notes(self, text):
        """Edit notes.

        Notes are used to document aspects of designs only.

        Parameters
        ----------
        text : str
            Text to be added in the design notes.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesign.EditNotes()

        Examples
        --------

        >>> from ansys.aedt.core import Maxwell3d
        >>> m3d = Maxwell3d()
        >>> m3d.edit_notes("This is an example.")
        """
        if not isinstance(text, str):
            self.logger.error("Input type of edit_notes is not valid.")
            return False
        self.odesign.EditNotes(text)
        return True


class DesignSettings:
    """Get design settings for the current AEDT app.

    References
    ----------
    >>> oDesign.GetChildObject("Design Settings")
    """

    def __init__(self, app):
        self._app: Any = app
        self.manipulate_inputs: Optional[DesignSettingsManipulation] = None

    @property
    def design_settings(self) -> Optional[Any]:
        """Design settings."""
        try:
            return self._app.odesign.GetChildObject("Design Settings")
        except GrpcApiError:  # pragma: no cover
            self._app.logger.error("Failed to retrieve design settings.")
            return None

    @property
    def available_properties(self) -> List[str]:
        """Available properties names for the current design."""
        return [prop for prop in self.design_settings.GetPropNames() if not prop.endswith("/Choices")]

    def __repr__(self) -> str:
        lines = ["{"]
        for prop in self.available_properties:
            lines.append(f"\t{prop}: {self.design_settings.GetPropValue(prop)}")
        lines.append("}")
        return "\n".join(lines)

    def __setitem__(self, key: str, value: Any) -> Union[bool, None]:
        value = _units_assignment(value)
        if key in self.available_properties:
            if self.manipulate_inputs is not None:
                value = self.manipulate_inputs.execute(key, value)
            key_choices = f"{key}/Choices"
            if key_choices in self.design_settings.GetPropNames():
                value_choices = self.design_settings.GetPropValue(key_choices)
                if value not in value_choices:
                    self._app.logger.error(
                        f"{value} is not a valid choice. Possible choices are: {', '.join(value_choices)}"
                    )
                    return False
            self.design_settings.SetPropValue(key, value)
        else:
            self._app.logger.error(f"{key} property is not available in design settings.")

    def __getitem__(self, key: str) -> Optional[Any]:
        if key in self.available_properties:
            return self.design_settings.GetPropValue(key)
        else:
            self._app.logger.error(f"{key} property is not available in design settings.")
            return None

    def __contains__(self, item: str) -> bool:
        return item in self.available_properties


class DesignSettingsManipulation:
    @abstractmethod
    def execute(self, k: str, v: Any) -> Any:
        pass
