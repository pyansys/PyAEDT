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

"""This module contains the ``Hfss`` class."""

from __future__ import absolute_import  # noreorder

import ast
import math
import os
from pathlib import Path
import tempfile
import warnings

from ansys.aedt.core.application.analysis_3d import FieldAnalysis3D
from ansys.aedt.core.application.analysis_hf import ScatteringMethods
from ansys.aedt.core.generic.constants import INFINITE_SPHERE_TYPE
from ansys.aedt.core.generic.constants import SOLUTIONS
from ansys.aedt.core.generic.data_handlers import _dict2arg
from ansys.aedt.core.generic.data_handlers import str_to_bool
from ansys.aedt.core.generic.errors import AEDTRuntimeError
from ansys.aedt.core.generic.general_methods import generate_unique_name
from ansys.aedt.core.generic.general_methods import is_number
from ansys.aedt.core.generic.general_methods import open_file
from ansys.aedt.core.generic.general_methods import parse_excitation_file
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.generic.general_methods import read_configuration_file
from ansys.aedt.core.generic.settings import settings
from ansys.aedt.core.mixins import CreateBoundaryMixin
from ansys.aedt.core.modeler import cad
from ansys.aedt.core.modeler.cad.component_array import ComponentArray
from ansys.aedt.core.modeler.cad.components_3d import UserDefinedComponent
from ansys.aedt.core.modeler.geometry_operators import GeometryOperators
from ansys.aedt.core.modules.boundary.common import BoundaryObject
from ansys.aedt.core.modules.boundary.hfss_boundary import FarFieldSetup
from ansys.aedt.core.modules.boundary.hfss_boundary import NearFieldSetup
from ansys.aedt.core.modules.boundary.layout_boundary import NativeComponentObject
from ansys.aedt.core.modules.setup_templates import SetupKeys


class Hfss(FieldAnalysis3D, ScatteringMethods, CreateBoundaryMixin):
    """Provides the HFSS application interface.

    This class allows you to create an interactive instance of HFSS and
    connect to an existing HFSS design or create a new HFSS design if
    one does not exist.

    Parameters
    ----------
    project : str, optional
        Name of the project to select or the full path to the project
        or AEDTZ archive to open. The default is ``None``, in which
        case an attempt is made to get an active project. If no
        projects are present, an empty project is created.
    design : str, optional
        Name of the design to select. The default is ``None``, in
        which case an attempt is made to get an active design. If no
        designs are present, an empty design is created.
    solution_type : str, optional
        Solution type to apply to the design. The default is
        ``None``, in which case the user-defined
        default type is applied.
        Options are:

        - "Terminal"
        - "Modal"
        - "SBR+"
        - "Transient"
        - "Eigenmode"

    setup : str, optional
        Name of the setup to use as the nominal. The default is
        ``None``, in which case the active setup is used or
        nothing is used.
    version : str, int, float, optional
        Version of AEDT to use. The default is ``None``, in which case
        the active version or latest installed version is used.
        This parameter is ignored when a script is launched within AEDT.
        Examples of input values are ``251``, ``25.1``, ``2025.1``, ``"2025.1"``.
    non_graphical : bool, optional
        Whether to run AEDT in non-graphical mode. The default
        is ``False``, in which case AEDT is launched in graphical mode.
        This parameter is ignored when a script is launched within AEDT.
    new_desktop : bool, optional
        Whether to launch an instance of AEDT in a new thread, even if
        another instance of the ``specified_version`` is active on the
        machine. The default is ``False``. This parameter is ignored when
        a script is launched within AEDT.
    close_on_exit : bool, optional
        Whether to release AEDT on exit. The default is ``False``.
    student_version : bool, optional
        Whether to open the AEDT student version. The default is
        ``False``. This parameter is ignored when a script is launched
        within AEDT.
    machine : str, optional
        Machine name to connect the oDesktop session to. This parameter works only on
        2022 R2 or later. The remote Server must be up and running with the command
        `"ansysedt.exe -grpcsrv portnum"`. If the machine is `"localhost"`, the server
        starts if it is not present.
    port : int, optional
        Port number on which to start the oDesktop communication on an already existing server.
        This parameter is ignored when creating a new server. It works only in 2022 R2 or later.
        The remote server must be up and running with the command `"ansysedt.exe -grpcsrv portnum"`.
    aedt_process_id : int, optional
        Process ID for the instance of AEDT to point PyAEDT at. The default is
        ``None``. This parameter is only used when ``new_desktop = False``.
    remove_lock : bool, optional
        Whether to remove lock to project before opening it or not.
        The default is ``False``, which means to not unlock
        the existing project if needed and raise an exception.

    Examples
    --------
    Create an instance of HFSS and connect to an existing HFSS
    design or create a new HFSS design if one does not exist.

    >>> from ansys.aedt.core import Hfss
    >>> hfss = Hfss()
    PyAEDT INFO: No project is defined...
    PyAEDT INFO: Active design is set to...


    Create an instance of HFSS and link to a project named
    ``HfssProject``. If this project does not exist, create one with
    this name.

    >>> hfss = Hfss("HfssProject")
    PyAEDT INFO: Project HfssProject has been created.
    PyAEDT INFO: No design is present. Inserting a new design.
    PyAEDT INFO: Added design ...


    Create an instance of HFSS and link to a design named
    ``HfssDesign1`` in a project named ``HfssProject``.

    >>> hfss = Hfss("HfssProject","HfssDesign1")
    PyAEDT INFO: Added design 'HfssDesign1' of type HFSS.


    Create an instance of HFSS and open the specified project,
    which is named ``"myfile.aedt"``.

    >>> hfss = Hfss("myfile.aedt")
    PyAEDT INFO: Project myfile has been created.
    PyAEDT INFO: No design is present. Inserting a new design.
    PyAEDT INFO: Added design...


    Create an instance of HFSS using the 2025 R1 release and open
    the specified project, which is named ``"myfile2.aedt"``.

    >>> hfss = Hfss(version=251, project="myfile2.aedt")
    PyAEDT INFO: Project myfile2 has been created.
    PyAEDT INFO: No design is present. Inserting a new design.
    PyAEDT INFO: Added design...


    Create an instance of HFSS using the 2025 R1 student version and open
    the specified project, which is named ``"myfile3.aedt"``.

    >>> hfss = Hfss(version="251", project="myfile3.aedt", student_version=True)
    PyAEDT INFO: Project myfile3 has been created.
    PyAEDT INFO: No design is present. Inserting a new design.
    PyAEDT INFO: Added design...

    """

    @pyaedt_function_handler(
        designname="design",
        projectname="project",
        specified_version="version",
        setup_name="setup",
        new_desktop_session="new_desktop",
    )
    def __init__(
        self,
        project=None,
        design=None,
        solution_type=None,
        setup=None,
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
        FieldAnalysis3D.__init__(
            self,
            "HFSS",
            project,
            design,
            solution_type,
            setup,
            version,
            non_graphical,
            new_desktop,
            close_on_exit,
            student_version,
            machine,
            port,
            aedt_process_id,
            remove_lock=remove_lock,
        )
        ScatteringMethods.__init__(self, self)
        self._field_setups = []
        self.component_array = {}
        self.component_array_names = list(self.get_oo_name(self.odesign, "Model"))
        for component_array in self.component_array_names:
            self.component_array[component_array] = ComponentArray(self, component_array)

    def _init_from_design(self, *args, **kwargs):
        self.__init__(*args, **kwargs)

    @property
    def field_setups(self):
        """List of AEDT radiation fields.

        Returns
        -------
        List of :class:`ansys.aedt.core.modules.boundary.hfss_boundary.FarFieldSetup` and
        :class:`ansys.aedt.core.modules.hfss_boundary.NearFieldSetup`
        """
        self._field_setups = []
        for field in self.field_setup_names:
            obj_field = self.odesign.GetChildObject("Radiation").GetChildObject(field)
            type_field = obj_field.GetPropValue("Type")
            if type_field == "Infinite Sphere":
                self._field_setups.append(FarFieldSetup(self, field, {}, "FarFieldSphere"))
            else:
                self._field_setups.append(NearFieldSetup(self, field, {}, f"NearField{type_field}"))
        # if not self._field_setups:
        #     self._field_setups = self._get_rad_fields()
        return self._field_setups

    @property
    def field_setup_names(self):
        """List of AEDT radiation field names.

        Returns
        -------
        List of str
        """
        return self.odesign.GetChildObject("Radiation").GetChildNames()

    class BoundaryType(CreateBoundaryMixin):
        """Creates and manages boundaries."""

        (
            PerfectE,
            PerfectH,
            Aperture,
            Radiation,
            Impedance,
            LayeredImp,
            LumpedRLC,
            FiniteCond,
            Hybrid,
            FEBI,
        ) = range(0, 10)

    @property
    def hybrid(self):
        """HFSS hybrid mode for the active solution.

        For instance, it must be set to ``True`` to define the solution type as 'HFSS with Hybrid and Arrays'.

        Returns
        -------
        bool
        """
        return self.design_solutions.hybrid

    @hybrid.setter
    def hybrid(self, value):
        if value != self.design_solutions.hybrid and isinstance(value, bool):
            self.design_solutions.hybrid = value

    @property
    def composite(self):
        """HFSS composite mode for the active solution.

        Returns
        -------
        bool
        """
        return self.design_solutions.composite

    @composite.setter
    def composite(self, value):
        self.design_solutions.composite = value

    @property
    def table_names(self):
        """Imported table names.

        Returns
        -------
        list of str
            List of names of all imported tables in the design.

        References
        ----------
        >>> oModule.GetValidISolutionList
        """
        table_names = []
        if self.osolution and "GetValidISolutionList" in self.osolution.__dir__():
            solution_list = self.osolution.GetValidISolutionList(True)
            if solution_list:
                table_names = [
                    item.split(" :")[0]
                    for item in solution_list
                    if not any(setup_name + " :" in item for setup_name in self.setup_names)
                ]
        return table_names

    @pyaedt_function_handler(boundary_type="opening_type")
    def set_auto_open(self, enable=True, opening_type="Radiation"):
        """Set the HFSS auto open type.

        Parameters
        ----------
        enable : bool, optional
            Whether to enable the HFSS auto open option. The default is ``True``.
        opening_type : str, optional
            Boundary type to use with auto open. Options are ``"Radiation"``,
            ``"FEBI"``, and ``"PML"``. The default is ``"Radiation"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------
        Enable auto open type for the PML boundary.

        >>> hfss.set_auto_open(True,"PML")
        """
        if enable and opening_type not in ["Radiation", "FEBI", "PML"]:
            raise AttributeError("Wrong boundary type. Check Documentation for valid inputs")
        return self.design_solutions.set_auto_open(enable=enable, opening_type=opening_type)

    @pyaedt_function_handler()
    def _get_unique_source_name(self, source_name, root_name):
        if not source_name:
            source_name = generate_unique_name(root_name)
        elif source_name in self.excitations or source_name + ":1" in self.excitations:
            source_name = generate_unique_name(source_name)
        return source_name

    @pyaedt_function_handler(objectname="assignment", portname="port_name")
    def _create_lumped_driven(self, assignment, int_line_start, int_line_stop, impedance, port_name, renorm, deemb):
        assignment = self.modeler.convert_to_selections(assignment, True)
        start = [str(i) + self.modeler.model_units for i in int_line_start]
        stop = [str(i) + self.modeler.model_units for i in int_line_stop]
        props = {}
        if isinstance(assignment[0], str):
            props["Objects"] = assignment
        else:
            props["Faces"] = assignment
        props["DoDeembed"] = deemb
        props["RenormalizeAllTerminals"] = renorm
        if renorm:
            props["Modes"] = {
                "Mode1": {
                    "ModeNum": 1,
                    "UseIntLine": True,
                    "IntLine": {"Start": start, "End": stop},
                    "AlignmentGroup": 0,
                    "CharImp": "Zpi",
                    "RenormImp": str(impedance) + "ohm",
                }
            }
        else:
            props["Modes"] = {
                "Mode1": {
                    "ModeNum": 1,
                    "UseIntLine": True,
                    "IntLine": {"Start": start, "End": stop},
                    "AlignmentGroup": 0,
                    "CharImp": "Zpi",
                }
            }

        props["ShowReporterFilter"] = False
        props["ReporterFilter"] = [True]
        props["Impedance"] = str(impedance) + "ohm"
        return self._create_boundary(port_name, props, "Lumped Port")

    @pyaedt_function_handler(objectname="assignment", portname="port_name")
    def _create_port_terminal(
        self,
        assignment,
        int_line_stop,
        port_name,
        renorm=True,
        deembed=None,
        iswaveport=False,
        impedance=None,
        terminals_rename=True,
    ):
        ref_conductors = self.modeler.convert_to_selections(int_line_stop, True)
        props = {}
        props["Faces"] = int(assignment)
        props["IsWavePort"] = iswaveport
        props["ReferenceConductors"] = ref_conductors
        props["RenormalizeModes"] = True
        ports = list(self.oboundary.GetExcitationsOfType("Terminal"))
        boundary = self._create_boundary(port_name, props, "AutoIdentify")
        if boundary:
            new_ports = list(self.oboundary.GetExcitationsOfType("Terminal"))
            terminals = [i for i in new_ports if i not in ports]
            for count, terminal in enumerate(terminals, start=1):
                props_terminal = {}
                props_terminal["TerminalResistance"] = "50ohm"
                props_terminal["ParentBndID"] = boundary.name
                terminal_name = terminal

                if impedance:
                    props_terminal["TerminalResistance"] = str(impedance) + "ohm"
                    properties = [
                        "NAME:AllTabs",
                        [
                            "NAME:HfssTab",
                            ["NAME:PropServers", "BoundarySetup:" + terminal],
                            [
                                "NAME:ChangedProps",
                                ["NAME:Terminal Renormalizing Impedance", "Value:=", str(impedance) + "ohm"],
                            ],
                        ],
                    ]
                    try:
                        self.odesign.ChangeProperty(properties)
                    except Exception:  # pragma: no cover
                        self.logger.warning("Failed to change terminal impedance.")
                if not renorm:
                    properties = [
                        "NAME:AllTabs",
                        [
                            "NAME:HfssTab",
                            ["NAME:PropServers", "BoundarySetup:" + boundary.name],
                            [
                                "NAME:ChangedProps",
                                ["NAME:Renorm All Terminals", "Value:=", False],
                            ],
                        ],
                    ]
                    try:
                        self.odesign.ChangeProperty(properties)
                    except Exception:  # pragma: no cover
                        self.logger.warning("Failed to change normalization.")
                if terminals_rename:
                    new_name = port_name + "_T" + str(count)
                    terminal_name = new_name
                    properties = [
                        "NAME:AllTabs",
                        [
                            "NAME:HfssTab",
                            ["NAME:PropServers", "BoundarySetup:" + terminal],
                            ["NAME:ChangedProps", ["NAME:Name", "Value:=", new_name]],
                        ],
                    ]
                    try:
                        self.odesign.ChangeProperty(properties)
                    except Exception:  # pragma: no cover
                        self.logger.warning(f"Failed to rename terminal {terminal}.")
                bound = BoundaryObject(self, terminal_name, props_terminal, "Terminal")
                self._boundaries[terminal_name] = bound

            if iswaveport:
                boundary.type = "Wave Port"
            else:
                boundary.type = "Lumped Port"
            props["Faces"] = [assignment]
            if iswaveport:
                props["NumModes"] = 1
                props["UseLineModeAlignment"] = 1
            if deembed is None:
                props["DoDeembed"] = False
                if iswaveport:
                    props["DeembedDist"] = self.modeler._arg_with_dim(0)
            else:
                props["DoDeembed"] = True
                if iswaveport:
                    props["DeembedDist"] = self.modeler._arg_with_dim(deembed)
            props["RenormalizeAllTerminals"] = renorm
            props["ShowReporterFilter"] = False
            props["UseAnalyticAlignment"] = False
            boundary.auto_update = False
            boundary.props.update(props)
            boundary.auto_update = True
            boundary.update()

        return boundary

    @pyaedt_function_handler(edgelist="assignment")
    def _create_circuit_port(self, assignment, impedance, name, renorm, deemb, renorm_impedance=""):
        edgelist = self.modeler.convert_to_selections(assignment, True)
        props = dict(
            {
                "Edges": edgelist,
                "Impedance": str(impedance) + "ohm",
                "DoDeembed": deemb,
                "RenormalizeAllTerminals": renorm,
            }
        )

        if "Modal" in self.solution_type:
            if renorm:
                if isinstance(renorm_impedance, (int, float)) or "i" not in renorm_impedance:
                    renorm_imp = str(renorm_impedance) + "ohm"
                else:
                    renorm_imp = "(" + renorm_impedance + ") ohm"
            else:
                renorm_imp = "0ohm"
            props["RenormImp"] = renorm_imp
        else:
            props["TerminalIDList"] = []
        return self._create_boundary(name, props, "Circuit Port")

    @pyaedt_function_handler(objectname="assignment", portname="port_name")
    def _create_waveport_driven(
        self,
        assignment,
        int_line_start=None,
        int_line_stop=None,
        impedance=50,
        port_name="",
        renorm=True,
        nummodes=1,
        deemb_distance=0,
        characteristic_impedance="Zpi",
    ):
        if not int_line_start or not int_line_stop:
            int_line_start = []
            int_line_stop = []
        elif not isinstance(int_line_start[0], list):
            int_line_start = [int_line_start]
            int_line_stop = [int_line_stop]

        props = {}  # Used to create the argument to pass to native api: oModule.AssignWavePort()
        if isinstance(assignment, int):  # Assumes a Face ID is passed in objectname
            props["Faces"] = [assignment]
        elif isinstance(assignment, list):  # Assume [x, y, z] point is passed in objectname
            props["Faces"] = self.modeler.get_faceid_from_position(assignment)
        else:
            props["Objects"] = [assignment]
        props["NumModes"] = nummodes
        props["UseLineModeAlignment"] = False

        if deemb_distance != 0:
            props["DoDeembed"] = True
            props["DeembedDist"] = self.modeler._arg_with_dim(deemb_distance)
        else:
            props["DoDeembed"] = False
        props["RenormalizeAllTerminals"] = renorm
        modes = {}
        i = 1
        report_filter = []
        while i <= nummodes:
            start = None
            stop = None
            line_index = i - 1
            if (
                len(int_line_start) > line_index
                and len(int_line_stop) > line_index
                and int_line_start[line_index]
                and int_line_stop[line_index]
            ):
                useintline = True
                start = [
                    str(i) + self.modeler.model_units if type(i) in (int, float) else i
                    for i in int_line_start[line_index]
                ]
                stop = [
                    str(i) + self.modeler.model_units if type(i) in (int, float) else i
                    for i in int_line_stop[line_index]
                ]
            else:
                useintline = False
            if useintline:
                mode = {"ModeNum": i, "UseIntLine": useintline}
                if useintline:
                    mode["IntLine"] = dict({"Start": start, "End": stop})
                mode["AlignmentGroup"] = 0
                mode["CharImp"] = characteristic_impedance[line_index]
                if renorm:
                    mode["RenormImp"] = str(impedance) + "ohm"
                modes["Mode" + str(i)] = mode
            else:
                mode = {
                    "ModeNum": i,
                    "UseIntLine": False,
                    "AlignmentGroup": 0,
                    "CharImp": characteristic_impedance[line_index],
                }

                if renorm:
                    mode["RenormImp"] = str(impedance) + "ohm"
                modes["Mode" + str(i)] = mode
            report_filter.append(True)
            i += 1
        props["Modes"] = modes
        props["ShowReporterFilter"] = False
        props["ReporterFilter"] = report_filter
        props["UseAnalyticAlignment"] = False
        return self._create_boundary(port_name, props, "Wave Port")

    @pyaedt_function_handler(
        obj="assignment",
        mat="material",
        cond="conductivity",
        perm="permittivity",
        usethickness="use_thickness",
        isinfgnd="is_infinite_ground",
        istwoside="is_two_side",
        isInternal="is_internal",
        issheelElement="is_shell_element",
        usehuray="use_huray",
    )
    def assign_coating(
        self,
        assignment,
        material=None,
        conductivity=58000000,
        permittivity=1,
        use_thickness=False,
        thickness="0.1mm",
        roughness="0um",
        is_infinite_ground=False,
        is_two_side=False,
        is_internal=True,
        is_shell_element=False,
        use_huray=False,
        radius="0.5um",
        ratio="2.9",
        name=None,
    ):
        """Assign finite conductivity to one or more objects or faces of a given material.

        Parameters
        ----------
        assignment : str or list
            One or more objects or faces to assign finite conductivity to.
        material : str, optional
            Material to use. The default is ``None``.
        conductivity : float, optional
            Conductivity. The default is ``58000000``.
            If no material is provided, a value must be supplied.
        permittivity : float, optional
            Permittivity. The default is ``1``. If no
            material is provided, a value must be supplied.
        use_thickness : bool, optional
            Whether to use thickness. The default is ``False``.
        thickness : str, optional
            Thickness value if ``usethickness=True``. The default is ``"0.1mm"``.
        roughness : str, optional
            Roughness value  with units. The default is ``"0um"``.
        is_infinite_ground : bool, optional
            Whether the finite conductivity is an infinite ground. The default is ``False``.
        is_two_side : bool, optional
            Whether the finite conductivity is two-sided. The default is ``False``.
        is_internal : bool, optional
            Whether the finite conductivity is internal. The default is ``True``.
        is_shell_element : bool, optional
            Whether the finite conductivity is a shell element.
            The default is ``False``.
        use_huray : bool, optional
            Whether to use a Huray coefficient. The default is ``False``.
        radius : str, optional
            Radius value if ``usehuray=True``. The default is ``"0.5um"``.
        ratio : str, optional
            Ratio value if ``usehuray=True``. The default is ``"2.9"``.
        name : str
            Name of the boundary.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Boundary object.

        References
        ----------
        >>> oModule.AssignFiniteCond

        Examples
        --------

        Create two cylinders in the XY working plane and assign a copper coating of 0.2 mm to the inner cylinder and
        outer face.

        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> origin = hfss.modeler.Position(0, 0, 0)
        >>> inner = hfss.modeler.create_cylinder(hfss.PLANE.XY,origin,3,200,0,"inner")
        >>> outer = hfss.modeler.create_cylinder(hfss.PLANE.XY,origin,4,200,0,"outer")
        >>> coat = hfss.assign_coating(["inner", outer.faces[2].id], "copper", use_thickness=True, thickness="0.2mm")

        """

        userlst = self.modeler.convert_to_selections(assignment, True)
        lstobj = []
        lstface = []
        for selection in userlst:
            if selection in self.modeler.model_objects:
                lstobj.append(selection)
            elif isinstance(selection, int) and self.modeler._find_object_from_face_id(selection):
                lstface.append(selection)

        if not lstface and not lstobj:
            raise AEDTRuntimeError("Objects or Faces selected do not exist in the design.")

        listobjname = ""
        props = {}
        if lstobj:
            listobjname = listobjname + "_" + "_".join(lstobj)
            props["Objects"] = lstobj
        if lstface:
            props["Faces"] = lstface
            lstface = [str(i) for i in lstface]
            listobjname = listobjname + "_" + "_".join(lstface)
        if material:
            if self.materials[material]:
                props["UseMaterial"] = True
                props["Material"] = self.materials[material].name
            else:
                raise AEDTRuntimeError(f"Material '{material}' does not exist.")
        else:
            props["UseMaterial"] = False
            props["Conductivity"] = str(conductivity)
            props["Permeability"] = str(str(permittivity))
        props["UseThickness"] = use_thickness
        if use_thickness:
            props["Thickness"] = thickness
        if use_huray:
            props["Radius"] = str(radius)
            props["Ratio"] = str(ratio)
            props["InfGroundPlane"] = False
        else:
            props["Roughness"] = roughness
            props["InfGroundPlane"] = is_infinite_ground
        props["IsTwoSided"] = is_two_side

        if is_two_side:
            props["IsShellElement"] = is_shell_element
        else:
            props["IsInternal"] = is_internal
        if not name:
            name = "Coating_" + listobjname[1:]
        return self._create_boundary(name, props, "Finite Conductivity")

    @pyaedt_function_handler(setupname="name", setuptype="setup_type")
    def create_setup(self, name="MySetupAuto", setup_type=None, **kwargs):
        """Create an analysis setup for HFSS.

        Optional arguments are passed along with ``setup_type`` and ``name``. Keyword
        names correspond to keyword for the ``setup_type`` as defined in
        the native AEDT API.

        .. note::
           This method overrides the ``Analysis.setup()`` method for the HFSS app.

        Parameters
        ----------
        name : str, optional
            Name of the setup. The default is ``"Setup1"``.
        setup_type : str, optional
            Type of the setup, which is based on the solution type. Options are
            ``"HFSSDrivenAuto"``, ``"HFSSDriven"``, ``"HFSSEigen"``, ``"HFSSTransient"``,
            and ``"HFSSSBR"``. The default is ``"HFSSDriven"``.
        **kwargs : dict, optional
            Keyword arguments from the native AEDT API.
            For more information, see
            :doc:`../SetupTemplatesHFSS`.

        Returns
        -------
        :class:`ansys.aedt.core.modules.solve_setup.SetupHFSS`,
        :class:`ansys.aedt.core.modules.solve_setup.SetupHFSSAuto`
            3D Solver Setup object.

        References
        ----------
        >>> oModule.InsertSetup

        Examples
        --------

        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss.create_setup(name="Setup1",setup_type="HFSSDriven",Frequency="10GHz")

        """
        if setup_type is None:
            setup_type = self.design_solutions.default_setup
        elif setup_type in SetupKeys.SetupNames:
            setup_type = SetupKeys.SetupNames.index(setup_type)
        name = self.generate_unique_setup_name(name)
        setup = self._create_setup(name=name, setup_type=setup_type)
        setup.auto_update = False
        for arg_name, arg_value in kwargs.items():
            if setup[arg_name] is not None:
                if arg_name == "MultipleAdaptiveFreqsSetup":  # A list of frequency values is passed if
                    setup[arg_name].delete_all()  # the default convergence criteria are to be
                    if isinstance(arg_value, list):  # used.
                        for i in arg_value:
                            setup[arg_name][i] = [0.02]
                    else:
                        for i, k in arg_value.items():
                            setup[arg_name][i] = [k]
                    setup.props["SolveType"] = "MultiFrequency"
                else:
                    setup[arg_name] = arg_value
        setup.auto_update = True
        setup.update()
        return setup

    @pyaedt_function_handler(
        setupname="setup", unit="units", freqstart="start_frequency", freqstop="stop_frequency", sweepname="name"
    )
    def create_linear_count_sweep(
        self,
        setup,
        units,
        start_frequency,
        stop_frequency,
        num_of_freq_points=None,
        name=None,
        save_fields=True,
        save_rad_fields=False,
        sweep_type="Discrete",
        interpolation_tol=0.5,
        interpolation_max_solutions=250,
    ):
        """Create a sweep with a specified number of points.

        Parameters
        ----------
        setup : str
            Name of the setup.
        units : str
            Unit of the frequency. For example, ``"MHz"`` or ``"GHz"``.
        start_frequency : float
            Starting frequency of the sweep, such as ``1``.
        stop_frequency : float
            Stopping frequency of the sweep.
        num_of_freq_points : int
            Number of frequency points in the range.
            The default is ``401`` for ``sweep_type = "Interpolating"``. The defaults
            are "Fast"`` and ``5`` for ``sweep_type = ""Discrete"``.
        name : str, optional
            Name of the sweep. The default is ``None``, in which
            case a name is automatically assigned.
        save_fields : bool, optional
            Whether to save the fields. The default is ``True``.
        save_rad_fields : bool, optional
            Whether to save the radiating fields. The default is ``False``.
        sweep_type : str, optional
            Type of the sweep. Options are ``"Fast"``, ``"Interpolating"``,
            and ``"Discrete"``. The default is ``"Discrete"``.
        interpolation_tol : float, optional
            Error tolerance threshold for the interpolation process. The default
            is ``0.5``.
        interpolation_max_solutions : int, optional
            Maximum number of solutions evaluated for the interpolation process.
            The default is ``250``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.solve_sweeps.SweepHFSS` or bool
            Sweep object if successful, ``False`` otherwise.

        References
        ----------
        >>> oModule.InsertFrequencySweep

        Examples
        --------

        Create a setup named ``"LinearCountSetup"`` and use it in a linear count sweep
        named ``"LinearCountSweep"``.

        >>> setup = hfss.create_setup("LinearCountSetup")
        >>> linear_count_sweep = hfss.create_linear_count_sweep(setup="LinearCountSetup",
        ...                                                     sweep="LinearCountSweep",
        ...                                                     units="MHz", start_frequency=1.1e3,
        ...                                                     stop_frequency=1200.1, num_of_freq_points=1658)
        >>> type(linear_count_sweep)
        <class 'from ansys.aedt.core.modules.setup_templates.SweepHFSS'>

        """
        if setup not in self.setup_names:
            raise AEDTRuntimeError(f"Unknown setup '{setup}'")

        if sweep_type in ["Interpolating", "Fast"]:
            if num_of_freq_points == None:
                num_of_freq_points = 401
        elif sweep_type == "Discrete":
            if num_of_freq_points == None:
                num_of_freq_points = 5
        else:
            raise AttributeError(
                "Invalid value for `sweep_type`. The value must be 'Discrete', 'Interpolating', or 'Fast'."
            )

        if name is None:
            name = generate_unique_name("Sweep")

        for s in self.setups:
            if s.name == setup:
                setupdata = s
                if name in [sweep.name for sweep in setupdata.sweeps]:
                    oldname = name
                    name = generate_unique_name(oldname)
                    self.logger.warning("Sweep %s is already present. Sweep has been renamed in %s.", oldname, name)
                sweepdata = setupdata.add_sweep(name, sweep_type)
                if not sweepdata:
                    raise AEDTRuntimeError(f"Failed to add sweep '{name}' with type {sweep_type}")

                sweepdata.props["RangeType"] = "LinearCount"
                sweepdata.props["RangeStart"] = str(start_frequency) + units
                sweepdata.props["RangeEnd"] = str(stop_frequency) + units
                sweepdata.props["RangeCount"] = num_of_freq_points
                sweepdata.props["Type"] = sweep_type
                if sweep_type == "Interpolating":
                    sweepdata.props["InterpTolerance"] = interpolation_tol
                    sweepdata.props["InterpMaxSolns"] = interpolation_max_solutions
                    sweepdata.props["InterpMinSolns"] = 0
                    sweepdata.props["InterpMinSubranges"] = 1
                sweepdata.props["SaveFields"] = save_fields
                sweepdata.props["SaveRadFields"] = save_rad_fields
                sweepdata.update()
                self.logger.info(f"Linear count sweep {name} has been correctly created.")
                return sweepdata
        return False

    @pyaedt_function_handler(
        setup_name="setup",
        setupname="setup",
        freqstart="start_frequency",
        freqstop="stop_frequency",
        sweepname="name",
        sweep_name="name",
    )
    def create_linear_step_sweep(
        self,
        setup,
        unit,
        start_frequency,
        stop_frequency,
        step_size,
        name=None,
        save_fields=True,
        save_rad_fields=False,
        sweep_type="Discrete",
    ):
        """Create a sweep with a specified frequency step.

        Parameters
        ----------
        setup : str
            Name of the setup.
        unit : str
            Unit of the frequency. For example, ``"MHz"`` or ``"GHz"``.
        start_frequency : float
            Starting frequency of the sweep.
        stop_frequency : float
            Stopping frequency of the sweep.
        step_size : float
            Frequency size of the step.
        name : str, optional
            Name of the sweep. The default is ``None``, in
            which case a name is automatically assigned.
        save_fields : bool, optional
            Whether to save fields. The default is ``True``.
        save_rad_fields : bool, optional
            Whether to save radiating fields. The default is ``False``.
        sweep_type : str, optional
            Type of the sweep. Options are ``"Discrete"``,``"Interpolating"`` and
            ``"Fast"``. The default is ``"Discrete"``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.solve_sweeps.SweepHFSS` or bool
            Sweep object if successful, ``False`` otherwise.

        References
        ----------
        >>> oModule.InsertFrequencySweep

        Examples
        --------

        Create a setup named ``"LinearStepSetup"`` and use it in a linear step sweep
        named ``"LinearStepSweep"``.

        >>> setup = hfss.create_setup("LinearStepSetup")
        >>> linear_step_sweep = hfss.create_linear_step_sweep(setup="LinearStepSetup", unit="MHz",
        ...                                                   start_frequency=1.1e3, stop_frequency=1200.1,
        ...                                                   step_size=153.8)
        >>> type(linear_step_sweep)
        <class 'from ansys.aedt.core.modules.setup_templates.SweepHFSS'>

        """
        if sweep_type not in ["Discrete", "Interpolating", "Fast"]:
            raise AttributeError(
                "Invalid value for `sweep_type`. The value must be 'Discrete', 'Interpolating', or 'Fast'."
            )
        if setup not in self.setup_names:
            raise AEDTRuntimeError(f"Unknown setup '{setup}'")
        if name is None:
            sweep_name = generate_unique_name("Sweep")
        else:
            sweep_name = name

        for s in self.setups:
            if s.name == setup:
                return s.create_linear_step_sweep(
                    unit=unit,
                    start_frequency=start_frequency,
                    stop_frequency=stop_frequency,
                    step_size=step_size,
                    name=sweep_name,
                    save_fields=save_fields,
                    save_rad_fields=save_rad_fields,
                    sweep_type=sweep_type,
                )
        return False

    @pyaedt_function_handler(setupname="setup", sweepname="name")
    def create_single_point_sweep(
        self,
        setup,
        unit,
        freq,
        name=None,
        save_single_field=True,
        save_fields=False,
        save_rad_fields=False,
    ):
        """Create a sweep with a single frequency point.

        Parameters
        ----------
        setup : str
            Name of the setup.
        unit : str
            Unit of the frequency. For example, ``"MHz"`` or ``"GHz"``.
        freq : float, list
            Frequency of the single point or list of frequencies to create distinct single points.
        name : str, optional
            Name of the sweep. The default is ``None``, in
            which case a name is automatically assigned.
        save_single_field : bool, list, optional
            Whether to save the fields of the single point. The default is ``True``.
            If a list is specified, the length must be the same as the list of frequencies.
        save_fields : bool, optional
            Whether to save fields for all points and subranges defined in the sweep.
            The default is ``False``.
        save_rad_fields : bool, optional
            Whether to save only radiating fields. The default is ``False``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.solve_sweeps.SweepHFSS` or bool
            Sweep object if successful, ``False`` otherwise.

        References
        ----------
        >>> oModule.InsertFrequencySweep

        Examples
        --------

        Create a setup named ``"LinearStepSetup"`` and use it in a single point sweep
        named ``"SinglePointSweep"``.

        >>> setup = hfss.create_setup("LinearStepSetup")
        >>> single_point_sweep = hfss.create_single_point_sweep(setup="LinearStepSetup",unit="MHz",freq=1.1e3)
        >>> type(single_point_sweep)
        <class 'from ansys.aedt.core.modules.setup_templates.SweepHFSS'>

        """
        if setup not in self.setup_names:
            raise AEDTRuntimeError(f"Unknown setup '{setup}'")

        if name is None:
            sweep_name = generate_unique_name("SinglePoint")
        else:
            sweep_name = name

        if isinstance(save_single_field, list):
            if not isinstance(freq, list) or len(save_single_field) != len(freq):
                raise AttributeError("The length of save_single_field must be the same as the frequency length.")

        add_subranges = False
        if isinstance(freq, list):
            if not freq:
                raise AttributeError("Frequency list is empty. Specify at least one frequency point.")
            _ = freq.pop(0)
            if freq:
                add_subranges = True

        if isinstance(save_single_field, list):
            _ = save_single_field.pop(0)
        else:
            save0 = save_single_field
            if add_subranges:
                save_single_field = [save0] * len(freq)

        for s in self.setups:
            if s.name == setup:
                return s.create_single_point_sweep(
                    unit=unit,
                    freq=freq,
                    name=sweep_name,
                    save_single_field=save_single_field,
                    save_fields=save_fields,
                    save_rad_fields=save_rad_fields,
                )
        return False

    @pyaedt_function_handler()
    def _create_native_component(
        self, antenna_type, target_cs=None, model_units=None, parameters_dict=None, antenna_name=None
    ):
        from ansys.aedt.core.modeler.cad.modeler import CoordinateSystem

        if antenna_name is None:
            antenna_name = generate_unique_name(antenna_type.replace(" ", "").replace("-", ""))
        if not model_units:
            model_units = self.modeler.model_units

        native_props = dict({"NativeComponentDefinitionProvider": dict({"Type": antenna_type, "Unit": model_units})})
        if isinstance(target_cs, CoordinateSystem):
            target_cs = target_cs.name
        native_props["TargetCS"] = target_cs
        if isinstance(parameters_dict, dict):
            for el in parameters_dict:
                if (
                    el not in ["antenna_type", "offset", "rotation", "rotation_axis", "mode"]
                    and parameters_dict[el] is not None
                ):
                    native_props["NativeComponentDefinitionProvider"][el.replace("_", " ").title()] = parameters_dict[
                        el
                    ]
        native = NativeComponentObject(self, antenna_type, antenna_name, native_props)

        _ = self.native_components

        if native.create():
            user_defined_component = UserDefinedComponent(
                self.modeler, native.name, native_props["NativeComponentDefinitionProvider"], antenna_type
            )
            self.modeler.user_defined_components[native.name] = user_defined_component
            self._native_components.append(native)
            self.logger.info("Native component %s %s has been correctly created.", antenna_type, antenna_name)
            return native

        raise AEDTRuntimeError(f"Failed to create native component {antenna_type} {antenna_name}")

    class SbrAntennas:
        (
            ConicalHorn,
            CrossDipole,
            HalfWaveDipole,
            HorizontalDipole,
            ParametricBeam,
            ParametricSlot,
            PyramidalHorn,
            QuarterWaveMonopole,
            ShortDipole,
            SmallLoop,
            WireDipole,
            WireMonopole,
        ) = (
            "Conical Horn",
            "Cross Dipole",
            "Half-Wave Dipole",
            "Horizontal Dipole",
            "Parametric Beam",
            "Parametric Slot",
            "Pyramidal Horn",
            "Quarter-Wave Monopole",
            "Short Dipole",
            "Small Loop",
            "Wire Dipole",
            "Wire Monopole",
        )

    class SBRAntennaDefaults:
        _conical = dict(
            {
                "Unit": "mm",
                "Version": 0,
                "Is Parametric Array": False,
                "MatchedPortImpedance": "50ohm",
                "Polarization": "Vertical",
                "Representation": "Far Field",
                "Mouth Diameter": "0.3meter",
                "Flare Half Angle": "20deg",
            }
        )

        _cross = dict(
            {
                "Unit": "mm",
                "Version": 0,
                "Is Parametric Array": False,
                "MatchedPortImpedance": "50ohm",
                "Polarization": "RHCP",
                "Representation": "Current Source",
                "Density": "1",
                "UseGlobalCurrentSrcOption": True,
                "Resonant Frequency": "0.3GHz",
                "Wire Length": "499.654096666667mm",
                "Mode": 0,
            }
        )

        _dipole = dict(
            {
                "Unit": "mm",
                "Version": 0,
                "Is Parametric Array": False,
                "Size": "1mm",
                "MatchedPortImpedance": "50ohm",
                "Representation": "Far Field",
            }
        )

        _horizontal = dict(
            {
                "Unit": "mm",
                "Version": 0,
                "Is Parametric Array": False,
                "MatchedPortImpedance": "50ohm",
                "Polarization": "Vertical",
                "Representation": "Current Source",
                "Density": "1",
                "UseGlobalCurrentSrcOption": False,
                "Resonant Frequency": "0.3GHz",
                "Wire Length": "499.654096666667mm",
                "Height Over Ground Plane": "249.827048333333mm",
                "Use Default Height": True,
            }
        )

        _parametricbeam = dict(
            {
                "Unit": "mm",
                "Version": 0,
                "Is Parametric Array": False,
                "Size": "0.1meter",
                "MatchedPortImpedance": "50ohm",
                "Polarization": "Vertical",
                "Representation": "Far Field",
                "Vertical BeamWidth": "30deg",
                "Horizontal BeamWidth": "60deg",
            }
        )

        _slot = dict(
            {
                "Unit": "mm",
                "Version": 0,
                "Is Parametric Array": False,
                "MatchedPortImpedance": "50ohm",
                "Representation": "Far Field",
                "Resonant Frequency": "0.3GHz",
                "Slot Length": "499.654096666667mm",
            }
        )

        _horn = dict(
            {
                "Unit": "mm",
                "Version": 0,
                "Is Parametric Array": False,
                "MatchedPortImpedance": "50ohm",
                "Representation": "Far Field",
                "Mouth Width": "0.3meter",
                "Mouth Height": "0.5meter",
                "Waveguide Width": "0.15meter",
                "Width Flare Half Angle": "20deg",
                "Height Flare Half Angle": "35deg",
            }
        )

        _smallloop = dict(
            {
                "Unit": "mm",
                "Version": 0,
                "Is Parametric Array": False,
                "MatchedPortImpedance": "50ohm",
                "Polarization": "Vertical",
                "Representation": "Current Source",
                "Density": "1",
                "UseGlobalCurrentSrcOption": False,
                "Current Source Conformance": "Disable",
                "Thin Sources": True,
                "Power Fraction": "0.95",
                "Mouth Diameter": "0.3meter",
                "Flare Half Angle": "20deg",
            }
        )

        _wiredipole = dict(
            {
                "Unit": "mm",
                "Version": 0,
                "Is Parametric Array": False,
                "MatchedPortImpedance": "50ohm",
                "Representation": "Far Field",
                "Resonant Frequency": "0.3GHz",
                "Wire Length": "499.654096666667mm",
            }
        )
        parameters = {
            "Conical Horn": _conical,
            "Cross Dipole": _cross,
            "Half-Wave Dipole": _dipole,
            "Horizontal Dipole": _horizontal,
            "Parametric Beam": _parametricbeam,
            "Parametric Slot": _slot,
            "Pyramidal Horn": _horn,
            "Quarter-Wave Monopole": _dipole,
            "Short Dipole": _dipole,
            "Small Loop": _dipole,
            "Wire Dipole": _wiredipole,
            "Wire Monopole": _wiredipole,
        }
        default_type_id = {
            "Conical Horn": 12,
            "Cross Dipole": 13,
            "Half-Wave Dipole": 4,
            "Horizontal Dipole": 14,
            "Parametric Beam": 1,
            "Parametric Slot": 8,
            "Pyramidal Horn": 11,
            "Quarter-Wave Monopole": 5,
            "Short Dipole": 2,
            "Small Loop": 3,
            "Wire Dipole": 6,
            "Wire Monopole": 7,
            "File Based Antenna": 9,
            "Linked Antenna": 10,
        }
        array_parameters = {
            "Array Element Type": 1,
            "Array Element Angle Phi": "0deg",
            "Array Element Angle Theta": "0deg",
            "Array Element Offset X": "0meter",
            "Array Element Offset Y": "0meter",
            "Array Element Offset Z": "0meter",
            "Array Element Conformance Type": 0,
            "Array Element Conform Orientation": False,
            "Array Design Frequency": "1GHz",
            "Array Layout Type": 0,
            "Array Specify Design In Wavelength": True,
            "Array Element Num": 5,
            "Array Length": "1meter",
            "Array Width": "1meter",
            "Array Length Spacing": "0.1meter",
            "Array Width Spacing": "0.1meter",
            "Array Length In Wavelength": "3",
            "Array Width In Wavelength": "4",
            "Array Length Spacing In Wavelength": "0.5",
            "Array Stagger Type": 0,
            "Array Stagger Angle": "0deg",
            "Array Symmetry Type": 0,
            "Array Weight Type": 3,
            "Array Beam Angle Theta": "0deg",
            "Array Weight Edge TaperX": -200,
            "Array Weight Edge TaperY": -200,
            "Array Weight Cosine Exp": 1,
            "Array Differential Pattern Type": 0,
            "Custom Array Filename": "",
            "Custom Array State": "1",
        }

    @pyaedt_function_handler(model_units="units", parameters_dict="parameters", antenna_name="name")
    def create_sbr_antenna(
        self,
        antenna_type=SbrAntennas.ConicalHorn,
        target_cs=None,
        units=None,
        parameters=None,
        use_current_source_representation=False,
        is_array=False,
        custom_array=None,
        name=None,
    ):
        """Create a parametric beam antennas in SBR+.

        Parameters
        ----------
        antenna_type : str, `SbrAntennas.ConicalHorn`
            Name of the antennas type. The enumerator ``SbrAntennas`` can also be used.
            The default is ``"SbrAntennas.Conical Horn"``.
        target_cs : str, optional
            Target coordinate system. The default is ``None``, in which case
            the active coodiante system is used.
        units : str, optional
            Model units to apply to the object. The default is
            ``None``, in which case the active modeler units are applied.
        parameters : dict, optional
            Dictionary of parameters. The default is ``None``.
        use_current_source_representation : bool, optional
            Whether to use the current source representation. The default is ``False``.
        is_array : bool, optional
            Whether to define a parametric array. The default is ``False``.
        custom_array : str, optional
            Custom array file. The extensions supported are ``".sarr"``. The default is ``None``, in which case
            parametric array is created.
        name : str, optional
            Name of the 3D component. The default is ``None``, in which case the
            name is auto-generated based on the antenna type.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.layout_boundary.NativeComponentObject`
            NativeComponentObject object.

        References
        ----------
        >>> oEditor.InsertNativeComponent

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss(solution_type="SBR+")
        >>> parm = {"Polarization": "Vertical"}
        >>> par_beam = hfss.create_sbr_antenna(hfss.SbrAntennas.ShortDipole, parameters=parm, name="TX1")
        >>> custom_array = "my_file.sarr"
        >>> antenna_array = hfss.create_sbr_antenna(hfss.SbrAntennas.ShortDipole, custom_array=custom_array)
        >>> antenna_array_parametric = hfss.create_sbr_antenna(hfss.SbrAntennas.ShortDipole, is_array=True)

        """
        if self.solution_type != "SBR+":
            raise AEDTRuntimeError("This native component only applies to a SBR+ solution.")
        if target_cs is None:
            target_cs = self.modeler.get_working_coordinate_system()

        parameters_defaults = self.SBRAntennaDefaults.parameters[antenna_type].copy()

        if custom_array:
            is_array = True
        else:
            custom_array = ""

        if not units:
            units = self.modeler.model_units

        if "Unit" in parameters_defaults:
            parameters_defaults["Unit"] = units

        if use_current_source_representation and antenna_type in [
            "Conical Horn",
            "Horizontal Dipole",
            "Parametric Slot",
            "Pyramidal Horn",
            "Wire Dipole",
            "Wire Monopole",
        ]:
            parameters_defaults["Representation"] = "Current Source"
            parameters_defaults["Density"] = "1"
            parameters_defaults["UseGlobalCurrentSrcOption"] = False
            parameters_defaults["Current Source Conformance"] = "Disable"
            parameters_defaults["Thin Sources"] = False
            parameters_defaults["Power Fraction"] = "0.95"
        if is_array:
            parameters_defaults["Is Parametric Array"] = True
            parameters_defaults["Sheet"] = -1

            element_parameters = parameters_defaults.copy()

            array_parameters = self.SBRAntennaDefaults.array_parameters
            array_parameters["Array Element Type"] = self.SBRAntennaDefaults.default_type_id[antenna_type]
            if custom_array:
                array_parameters["Array Layout Type"] = 0
            else:
                array_parameters["Array Layout Type"] = 1
            array_parameters["Custom Array Filename"] = custom_array

            parameters_defaults = {
                "Type": "Parametric Array",
                "Unit": element_parameters["Unit"],
                "Version": element_parameters["Version"],
                "Is Parametric Array": element_parameters["Is Parametric Array"],
                "Antenna Array Parameters": array_parameters,
                "Array Element Parameters": element_parameters,
            }

            antenna_type = "Parametric Array"

        if parameters:
            for el, value in parameters.items():
                parameters_defaults[el] = value

        return self._create_native_component(antenna_type, target_cs, units, parameters_defaults, name)

    @pyaedt_function_handler(ffd_full_path="far_field_data", model_units="units", antenna_name="name")
    def create_sbr_file_based_antenna(
        self,
        far_field_data,
        antenna_size="1mm",
        antenna_impedance="50ohm",
        representation_type="Far Field",
        target_cs=None,
        units=None,
        is_array=False,
        custom_array=None,
        name=None,
    ):
        """Create a linked antenna.

        Parameters
        ----------
        far_field_data : str
            Full path to the FFD file.
        antenna_size : str, optional
            Antenna size with units. The default is ``"1mm"``.
        antenna_impedance : str, optional
            Antenna impedance with units. The default is ``"50ohm"``.
        representation_type : str, optional
            Type of the antennas. Options are ``"Far Field"`` and ``"Near Field"``.
            The default is ``"Far Field"``.
        target_cs : str, optional
            Target coordinate system. The default is ``None``, in which case the
            active coordinate system is used.
        units : str, optional
            Model units to apply to the object. The default is
            ``None``, in which case the active modeler units are applied.
        is_array : bool, optional
            Whether to define a parametric array. The default is ``False``.
        custom_array : str, optional
            Custom array file. The extensions supported are ``".sarr"``. The default is ``None``, in which case
            parametric array is created.
        name : str, optional
            Name of the 3D component. The default is ``None``, in which case
            the name is auto-generated based on the antenna type.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.layout_boundary.NativeComponentObject`

        References
        ----------
        >>> oEditor.InsertNativeComponent

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss(solution_type="SBR+")  # doctest: +SKIP
        >>> ffd_file = "full_path/to/ffdfile.ffd"
        >>> par_beam = hfss.create_sbr_file_based_antenna(ffd_file)  # doctest: +SKIP

        """
        if self.solution_type != "SBR+":
            raise AEDTRuntimeError("This native component only applies to a SBR+ solution.")

        if target_cs is None:
            target_cs = self.modeler.oeditor.GetActiveCoordinateSystem()

        if custom_array:
            is_array = True
        else:
            custom_array = ""

        if not units:
            units = self.modeler.model_units

        parameters_defaults = dict(
            {
                "Size": antenna_size,
                "MatchedPortImpedance": antenna_impedance,
                "Representation": representation_type,
                "ExternalFile": far_field_data,
                "Version": 0,
                "Unit": units,
            }
        )

        antenna_type = "File Based Antenna"

        if is_array:
            parameters_defaults["Is Parametric Array"] = True
            parameters_defaults["Sheet"] = -1

            element_parameters = parameters_defaults.copy()

            array_parameters = self.SBRAntennaDefaults.array_parameters
            array_parameters["Array Element Type"] = self.SBRAntennaDefaults.default_type_id[antenna_type]
            if custom_array:
                array_parameters["Array Layout Type"] = 0
            else:
                array_parameters["Array Layout Type"] = 1
            array_parameters["Custom Array Filename"] = custom_array

            parameters_defaults = {
                "Type": "Parametric Array",
                "Unit": element_parameters["Unit"],
                "Version": element_parameters["Version"],
                "Is Parametric Array": element_parameters["Is Parametric Array"],
                "Antenna Array Parameters": array_parameters,
                "Array Element Parameters": element_parameters,
            }

            antenna_type = "Parametric Array"

        return self._create_native_component(antenna_type, target_cs, units, parameters_defaults, name)

    @pyaedt_function_handler(source_object="assignment", solution="setup", fieldtype="field_type", source_name="name")
    def create_sbr_linked_antenna(
        self,
        assignment,
        target_cs="Global",
        setup=None,
        field_type="nearfield",
        use_composite_ports=False,
        use_global_current=True,
        current_conformance=False,
        thin_sources=True,
        power_fraction="0.95",
        visible=True,
        is_array=False,
        custom_array=None,
        name=None,
    ):
        """Create a linked antennas.

        Parameters
        ----------
        assignment : ansys.aedt.core.Hfss
            Source object.
        target_cs : str, optional
            Target coordinate system. The default is ``"Global"``.
        setup : optional
            Name of the setup. The default is ``None``, in which
            case a name is automatically assigned.
        field_type : str, optional
            Field type. The options are ``"nearfield"`` and ``"farfield"``.
            The default is ``"nearfield"``.
        use_composite_ports : bool, optional
            Whether to use composite ports. The default is ``False``.
        use_global_current : bool, optional
            Whether to use the global current. The default is ``True``.
        current_conformance : bool, optional
            Whether to enable current conformance. The default is ``False``.
        thin_sources : bool, optional
             Whether to enable thin sources. The default is ``True``.
        power_fraction : str, optional
             The default is ``"0.95"``.
        visible : bool, optional.
            Whether to make source objects in the target design visible. The default is ``True``.
        is_array : bool, optional
            Whether to define a parametric array. The default is ``False``.
        custom_array : str, optional
            Custom array file. The extensions supported are ``".sarr"``. The default is ``None``, in which case
            parametric array is created.
        name : str, optional
            Name of the source.
            The default is ``None`` in which case a name is automatically assigned.

        References
        ----------
        >>> oEditor.InsertNativeComponent

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> target_project = "my/path/to/targetProject.aedt"
        >>> source_project = "my/path/to/sourceProject.aedt"
        >>> target = Hfss(project=target_project, solution_type="SBR+",
        ...               version="2025.1", new_desktop=False)
        >>> source = Hfss(project=source_project, design="feeder",
        ...               version="2025.1", new_desktop=False)
        >>> target.create_sbr_linked_antenna(source,target_cs="feederPosition",field_type="farfield")  # doctest: +SKIP

        """
        if self.solution_type != "SBR+":
            raise AEDTRuntimeError("Native components only apply to the SBR+ solution.")

        if name is None:
            uniquename = generate_unique_name(assignment.design_name)
        else:
            uniquename = generate_unique_name(name)

        if assignment.project_name == self.project_name:
            project_name = "This Project*"
        else:
            project_name = os.path.join(assignment.project_path, assignment.project_name + ".aedt")
        design_name = assignment.design_name
        if not setup:
            setup = assignment.nominal_adaptive
        params = {}
        pars = assignment.available_variations.get_independent_nominal_values()

        for el in pars:
            params[el] = pars[el]
        native_props = dict(
            {
                "Type": "Linked Antenna",
                "Unit": self.modeler.model_units,
                "Version": 0,
                "Is Parametric Array": False,
                "Project": project_name,
                "Product": "HFSS",
                "Design": design_name,
                "Soln": setup,
                "Params": params,
                "ForceSourceToSolve": True,
                "PreservePartnerSoln": True,
                "PathRelativeTo": "TargetProject",
                "FieldType": field_type,
                "UseCompositePort": use_composite_ports,
                "SourceBlockageStructure": dict({"NonModelObject": []}),
            }
        )
        if field_type == "nearfield":
            native_props["UseGlobalCurrentSrcOption"] = use_global_current
            if current_conformance:
                native_props["Current Source Conformance"] = "Enable"
            else:
                native_props["Current Source Conformance"] = "Disable"
            native_props["Thin Sources"] = thin_sources
            native_props["Power Fraction"] = power_fraction
        if visible:
            native_props["VisualizationObjects"] = assignment.modeler.solid_names

        if custom_array:
            is_array = True
        else:
            custom_array = ""

        antenna_type = "Linked Antenna"

        if is_array:
            native_props["Is Parametric Array"] = True
            native_props["Sheet"] = -1

            element_parameters = native_props.copy()

            array_parameters = self.SBRAntennaDefaults.array_parameters
            array_parameters["Array Element Type"] = self.SBRAntennaDefaults.default_type_id[antenna_type]
            if custom_array:
                array_parameters["Array Layout Type"] = 0
            else:
                array_parameters["Array Layout Type"] = 1
            array_parameters["Custom Array Filename"] = custom_array

            native_props = {
                "Type": "Parametric Array",
                "Unit": element_parameters["Unit"],
                "Version": element_parameters["Version"],
                "Is Parametric Array": element_parameters["Is Parametric Array"],
                "Antenna Array Parameters": array_parameters,
                "Array Element Parameters": element_parameters,
            }

            antenna_type = "Parametric Array"

        return self._create_native_component(
            antenna_type, target_cs, self.modeler.model_units, native_props, uniquename
        )

    @pyaedt_function_handler()
    def create_sbr_custom_array_file(
        self,
        output_file=None,
        frequencies=None,
        element_number=1,
        state_number=1,
        position=None,
        x_axis=None,
        y_axis=None,
        weight=None,
    ):
        """Create custom array file with sarr format.

        Parameters
        ----------
        output_file : str, optional
            Full path and name for the file.
            The default is ``None``, in which case the file is exported to the working directory.
        frequencies : list, optional
            List of frequencies in GHz. The default is ``[1.0]``.
        element_number : int, optional
            Number of elements in the array. The default is ``1``.
        state_number : int, optional
            Number of states. The default is ``1``.
        position : list of list
            List of the ``[x, y, z]`` coordinates for each element. The default is ``[1, 0, 0]``.
        x_axis : list of list
            List of X, Y, Z components of X-axis unit vector.
        y_axis : list of list
            List of X, Y, Z components of Y-axis unit vector. The default is ``[0, 1, 0]``.
        weight : list of list
            Weight of each element. The default is ``None`` in which case all elements have uniform weight.
            The second dimension contains the weights for each element, organized as follows:
            The first ``frequencies`` entries correspond to the weights for that element at each
            of the ``frequencies``, for the first state.
            If there are multiple states, the next ``frequencies`` entries represent the weights for the second state,
            and so on.
            For example, for 3 frequencies ``(f1, f2, f3)``, 2 elements ``(e1, e2)``, and 2 states ``(s1, s2)``,
            the weight would be represented as: ``[[w_f1_e1_s1, w_f1_e2_s1], [w_f2_e1_s1, w_f2_e2_s1],
            [w_f3_e1_s1, w_f3_e2_s1], [w_f1_e1_s2, w_f1_e2_s2], [w_f2_e1_s2, w_f2_e2_s2], [w_f3_e1_s2, w_f3_e2_s2]]``.
            ```

        Returns
        -------
        str
            File name when successful, ``False`` when failed.

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss.create_sbr_custom_array_file()
        >>> hfss.release_desktop()
        """
        if output_file is None:
            output_file = os.path.join(self.working_directory, "custom_array.sarr")

        if frequencies is None:
            frequencies = [1.0]

        if position is None:
            position = [[0.0, 0.0, 0.0]] * element_number

        if x_axis is None:
            x_axis = [[1.0, 0.0, 0.0]] * element_number

        if y_axis is None:
            y_axis = [[0.0, 1.0, 0.0]] * element_number

        try:
            with open(output_file, "w") as sarr_file:
                sarr_file.write("# Array Element List (.sarr) file\n")
                sarr_file.write("# Blank lines and lines beginning with pound sign ('#') are ignored\n")

                # Write whether weight exists
                has_weight = weight is not None
                sarr_file.write("\n")
                sarr_file.write("# has_weights flags whether array file includes element weight data.\n")
                sarr_file.write("# If not, then array file only specifies element positions and orientations.\n")
                sarr_file.write(f"has_weights {'true' if has_weight else 'false'}\n")

                # Write frequency domain
                nf = len(frequencies)
                if len(frequencies) == 1 or all(
                    abs(frequencies[i + 1] - frequencies[i] - (frequencies[1] - frequencies[0])) < 1e-9
                    for i in range(len(frequencies) - 1)
                ):
                    sarr_file.write("\n")
                    sarr_file.write("# freq <start_ghz> <stop_ghz> # nstep = nfreq - 1\n")
                    sarr_file.write(f"freq {frequencies[0]} {frequencies[-1]} {nf - 1}\n")
                else:
                    sarr_file.write("\n")
                    sarr_file.write("# freq_list\n")
                    sarr_file.write(f"freq_list {nf}\n")
                    for freq in frequencies:
                        sarr_file.write(f"{freq}\n")

                # Handle states
                ns = state_number
                nfns = nf * ns
                if has_weight:
                    sarr_file.write("\n")
                    sarr_file.write("# num_states\n")
                    sarr_file.write(f"num_states {ns}\n")
                    # Flatten weights
                    weight_reshaped = [[weight[i][j] for i in range(nfns)] for j in range(element_number)]

                # Number of elements
                sarr_file.write("\n")
                sarr_file.write("# num_elements\n")
                sarr_file.write(f"num_elements {element_number}\n")

                # Element data block
                sarr_file.write("\n")
                sarr_file.write("# Element List Data Block\n")
                for elem in range(element_number):
                    sarr_file.write(f"\n# Element {elem + 1}\n")
                    sarr_file.write(f"{position[elem][0]:13.7e} {position[elem][1]:13.7e} {position[elem][2]:13.7e}\n")
                    sarr_file.write(f"{x_axis[elem][0]:13.7e} {x_axis[elem][1]:13.7e} {x_axis[elem][2]:13.7e}\n")
                    sarr_file.write(f"{y_axis[elem][0]:13.7e} {y_axis[elem][1]:13.7e} {y_axis[elem][2]:13.7e}\n")

                    if has_weight:
                        for ifs in range(nfns):
                            weight0 = weight_reshaped[elem][ifs]
                            sarr_file.write(f"{weight0.real:13.7e} {weight0.imag:13.7e}\n")
        except Exception as e:  # pragma: no cover
            raise AEDTRuntimeError("Failed to create custom array file with sarr format.") from e

        return output_file

    @pyaedt_function_handler()
    def set_sbr_txrx_settings(self, txrx_settings):
        """Set SBR+ TX RX antennas settings.

        Parameters
        ----------
        txrx_settings : dict
            Dictionary containing the TX as key and RX as values.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Boundary object.

        References
        ----------
        >>> oModule.SetSBRTxRxSettings
        """
        if self.solution_type != "SBR+":
            raise AEDTRuntimeError("This boundary only applies to a SBR+ solution.")

        id_ = 0
        props = {}
        for el, val in txrx_settings.items():
            props["Tx/Rx List " + str(id_)] = dict({"Tx Antenna": el, "Rx Antennas": txrx_settings[el]})
            id_ += 1
        return self._create_boundary("SBRTxRxSettings", props, "SBRTxRxSettings")

    @pyaedt_function_handler(start_object="assignment", end_object="reference", port_width="width")
    def create_spiral_lumped_port(self, assignment, reference, width=None, name=None):
        """Create a spiral lumped port between two adjacent objects.

        The two objects must have two adjacent, parallel, and identical faces.
        The faces must be a polygon (not a circle).
        The closest faces must be aligned with the main planes of the reference system.

        Parameters
        ----------
        assignment : str or int or :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
            First solid connected to the spiral port.
        reference : str or int or :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
            Second object connected to the spiral port.
        width : float, optional
            Width of the spiral port.
            If a width is not specified, it is calculated based on the object dimensions.
            The default is ``None``.
        name : str, optional
            Port name.  The default is ``None``.


        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Boundary object.

        Examples
        --------
        >>> aedtapp = Hfss()
        >>> aedtapp.insert_design("Design_Terminal_2")
        >>> aedtapp.solution_type = "Terminal"
        >>> box1 = aedtapp.modeler.create_box([-100, -100, 0],[200, 200, 5],name="gnd2z",material="copper")
        >>> box2 = aedtapp.modeler.create_box([-100, -100, 20],[200, 200, 25],name="sig2z",material="copper")
        >>> aedtapp.modeler.fit_all()
        >>> portz = aedtapp.create_spiral_lumped_port(box1,box2)
        """
        if not "Terminal" in self.solution_type:
            raise Exception("This method can be used only in Terminal solutions.")
        assignment = self.modeler.convert_to_selections(assignment)
        reference = self.modeler.convert_to_selections(reference)

        # find the closest faces (based on face center)
        closest_distance = 1e9
        closest_faces = []
        for face1 in self.modeler[assignment].faces:
            for face2 in self.modeler[reference].faces:
                facecenter_distance = GeometryOperators.points_distance(face1.center, face2.center)
                if facecenter_distance <= closest_distance:
                    closest_distance = facecenter_distance
                    closest_faces = [face1, face2]

        # check if the faces are parallel
        if not GeometryOperators.is_collinear(closest_faces[0].normal, closest_faces[1].normal):
            raise AttributeError("The two objects must have parallel adjacent faces.")
        if GeometryOperators.is_collinear(closest_faces[0].normal, [1, 0, 0]):
            plane = "X"
        elif GeometryOperators.is_collinear(closest_faces[0].normal, [0, 1, 0]):
            plane = "Y"
        elif GeometryOperators.is_collinear(closest_faces[0].normal, [0, 0, 1]):
            plane = "Z"
        else:
            raise AttributeError(
                "The closest faces of the two objects must be aligned with the main planes of the reference system."
            )

        # check if the faces are identical (actually checking only the area, not the shape)
        if abs(closest_faces[0].area - closest_faces[1].area) > 1e-10:
            raise AttributeError("The closest faces of the two objects must be identical in shape.")

        # evaluate the vector to move from face0 to the middle distance between the faces
        move_vector = GeometryOperators.v_sub(closest_faces[1].center, closest_faces[0].center)
        move_vector_mid = GeometryOperators.v_prod(0.5, move_vector)

        # fmt: off
        if width:
            spiral_width = width
            filling = 1.5
        else:
            # get face bounding box
            face_bb = [1e15, 1e15, 1e15, -1e15, -1e15, -1e15]
            for i in range(3):
                for v in closest_faces[0].vertices:
                    face_bb[i] = min(face_bb[i], v.position[i])
                    face_bb[i + 3] = max(face_bb[i + 3], v.position[i])
            # get the ratio in 2D
            bb_dim = [abs(face_bb[i] - face_bb[i + 3]) for i in range(3) if abs(face_bb[i] - face_bb[i + 3]) > 1e-12]
            bb_ratio = max(bb_dim) / min(bb_dim)
            if bb_ratio > 2:
                spiral_width = min(bb_dim) / 12
                filling = -0.2828 * bb_ratio ** 2 + 3.4141 * bb_ratio - 4.197
                print(filling)
            else:
                vertex_coordinates = []
                for v in closest_faces[0].vertices:
                    vertex_coordinates.append(v.position)
                segments_lengths = []
                for vc in vertex_coordinates:
                    segments_lengths.append(GeometryOperators.points_distance(vc, closest_faces[0].center))
                spiral_width = min(segments_lengths) / 15
                filling = 1.5
        # fmt: on
        if not name:
            name = generate_unique_name("P", n=3)

        spiral = self.modeler.create_spiral_on_face(closest_faces[0], spiral_width, filling_factor=filling)
        spiral.name = name
        spiral.move(move_vector_mid)
        spiral_center = GeometryOperators.get_mid_point(closest_faces[0].center, closest_faces[1].center)

        # get the polyline center point (before width operation). They need to be moved as well.
        poly_points = [GeometryOperators.v_sum(i, move_vector_mid) for i in spiral.points]

        # get the vertices of the spiral created. These need to be divided in two lists, one following the external
        # contour (p1) and one following the internal contour (p2). We use poly_points to discern the points.
        poly_v = [[v.position[0], v.position[1], v.position[2]] for v in spiral.vertices]

        p1 = []
        p2 = []
        for p in poly_points:
            cp = GeometryOperators.find_closest_points(poly_v, p)
            if len(cp) > 2:
                raise Exception("Internal error in spiral creation, please review the port_width parameter.")
            if GeometryOperators.points_distance(cp[0], spiral_center) > GeometryOperators.points_distance(
                cp[1], spiral_center
            ):
                p1.append(cp[0])
                p2.append(cp[1])
            else:
                p1.append(cp[1])
                p2.append(cp[0])

        # move the p1 down and the p2 up
        move_vector_quarter = GeometryOperators.v_prod(0.25, move_vector)
        p1_down = [GeometryOperators.v_sub(i, move_vector_quarter) for i in p1]
        p2_up = [GeometryOperators.v_sum(i, move_vector_quarter) for i in p2]

        # create first polyline to join spiral with conductor face
        dx = abs(p1_down[0][0] - p1_down[1][0])
        dy = abs(p1_down[0][1] - p1_down[1][1])
        dz = abs(p1_down[0][2] - p1_down[1][2])
        if plane == "X":
            orient = "Y" if (dy < dz) else "Z"
        elif plane == "Y":
            orient = "X" if (dx < dz) else "Z"
        else:
            orient = "X" if (dx < dy) else "Y"

        poly1 = self.modeler.create_polyline(
            p1_down,
            name=assignment + "_sheet",
            xsection_type="Line",
            xsection_orient=orient,
            xsection_width=closest_distance / 2,
        )

        # create second polyline to join spiral with conductor face
        dx = abs(p2_up[0][0] - p2_up[1][0])
        dy = abs(p2_up[0][1] - p2_up[1][1])
        dz = abs(p2_up[0][2] - p2_up[1][2])
        if plane == "X":
            orient = "Y" if (dy < dz) else "Z"
        elif plane == "Y":
            orient = "X" if (dx < dz) else "Z"
        else:
            orient = "X" if (dx < dy) else "Y"
        poly2 = self.modeler.create_polyline(
            p2_up,
            name=reference + "_sheet",
            xsection_type="Line",
            xsection_orient=orient,
            xsection_width=closest_distance / 2,
        )

        # assign pec to created polylines
        self.assign_perfecte_to_sheets(poly1, name=assignment)
        self.assign_perfecte_to_sheets(poly2, name=reference)

        # create lumped port on spiral
        port = self.lumped_port(spiral, reference=[poly2.name], name=name)

        return port

    @pyaedt_function_handler(startobj="assignment", endobject="reference", sourcename="name", axisdir="start_direction")
    def create_voltage_source_from_objects(
        self, assignment, reference, start_direction=0, name=None, source_on_plane=True
    ):
        """Create a voltage source taking the closest edges of two objects.

        Parameters
        ----------
        assignment : str or int or :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
            First object connected to the voltage source.
        reference : str or int or :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
            Second object connected to the voltage source.
        start_direction : int or :class:`ansys.aedt.core.application.analysis.Analysis.AxisDir`, optional
            Start direction for the port location.
            It should be one of the values for ``Application.AxisDir``, which are: ``XNeg``, ``YNeg``,
            ``ZNeg``, ``XPos``, ``YPos``, and ``ZPos``.
            The default is ``Application.AxisDir.XNeg``.
        name : str, optional
            Name of the source. The default is ``None``.
        source_on_plane : bool, optional
            Whether to create the source on the plane orthogonal to
            ``AxisDir``. The default is ``True``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Boundary object.

        References
        ----------
        >>> oModule.AssignVoltage

        Examples
        --------

        Create two boxes for creating a voltage source named ``'VoltageSource'``.

        >>> box1 = hfss.modeler.create_box([30, 0, 0],[40, 10, 5],"BoxVolt1","copper")
        >>> box2 = hfss.modeler.create_box([30, 0, 10],[40, 10, 5],"BoxVolt2","copper")
        >>> v1 = hfss.create_voltage_source_from_objects("BoxVolt1","BoxVolt2",hfss.AxisDir.XNeg,"VoltageSource")
        PyAEDT INFO: Connection Correctly created
        """

        if not self.modeler.does_object_exists(assignment) or not self.modeler.does_object_exists(reference):
            raise AEDTRuntimeError("One or both objects doesn't exists. Check and retry")

        if self.solution_type not in (
            SOLUTIONS.Hfss.DrivenModal,
            SOLUTIONS.Hfss.DrivenTerminal,
            SOLUTIONS.Hfss.Transient,
        ):
            raise AEDTRuntimeError("Invalid solution type.")

        sheet_name, point0, point1 = self.modeler._create_sheet_from_object_closest_edge(
            assignment, reference, start_direction, source_on_plane
        )
        name = self._get_unique_source_name(name, "Voltage")
        return self.create_source_excitation(sheet_name, point0, point1, name, source_type="Voltage")

    @pyaedt_function_handler(startobj="assignment", endobject="reference", sourcename="name", axisdir="start_direction")
    def create_current_source_from_objects(
        self, assignment, reference, start_direction=0, name=None, source_on_plane=True
    ):
        """Create a current source taking the closest edges of two objects.

        Parameters
        ----------
        assignment : str or int or :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
            First object connected to the current source.
        reference : str or int or :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
            Second object connected to the current source.
        start_direction : int or :class:`ansys.aedt.core.application.analysis.Analysis.AxisDir`, optional
            Start direction for the port location.
            It should be one of the values for ``Application.AxisDir``, which are: ``XNeg``, ``YNeg``,
            ``ZNeg``, ``XPos``, ``YPos``, and ``ZPos``.
            The default is ``Application.AxisDir.XNeg``.
        name : str, optional
            Name of the source. The default is ``None``.
        source_on_plane : bool, optional
            Whether to create the source on the plane orthogonal to
            the start direction. The default is ``True``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Boundary object.

        References
        ----------
        >>> oModule.AssignCurrent

        Examples
        --------

        Create two boxes for creating a current source named ``'CurrentSource'``.

        >>> box1 = hfss.modeler.create_box([30, 0, 20],[40, 10, 5],"BoxCurrent1","copper")
        >>> box2 = hfss.modeler.create_box([30, 0, 30],[40, 10, 5],"BoxCurrent2","copper")
        >>> i1 = hfss.create_current_source_from_objects("BoxCurrent1","BoxCurrent2",hfss.AxisDir.XPos,"CurrentSource")
        PyAEDT INFO: Connection created 'CurrentSource' correctly.
        """

        if not self.modeler.does_object_exists(assignment) or not self.modeler.does_object_exists(reference):
            raise ValueError("One or both objects do not exist. Check and retry.")

        if self.solution_type not in (
            SOLUTIONS.Hfss.DrivenModal,
            SOLUTIONS.Hfss.DrivenTerminal,
            SOLUTIONS.Hfss.Transient,
        ):
            raise AEDTRuntimeError("Invalid solution type.")

        sheet_name, point0, point1 = self.modeler._create_sheet_from_object_closest_edge(
            assignment, reference, start_direction, source_on_plane
        )
        name = self._get_unique_source_name(name, "Current")
        return self.create_source_excitation(sheet_name, point0, point1, name, source_type="Current")

    @pyaedt_function_handler(sheet_name="assignment", sourcename="name", sourcetype="source_type")
    def create_source_excitation(self, assignment, point1, point2, name, source_type="Voltage"):
        """Create a source excitation.

        Parameters
        ----------
        assignment : str
            Name of the sheet.
        point1 : list
            First point of the source excitation.
        point2 : list
            Second point of the source excitation.
        name : str
            Name of the source.
        source_type : str, optional
            Type of the source. The default is ``"Voltage"``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Boundary object.

        References
        ----------
        >>> oModule.AssignVoltage
        >>> oModule.AssignCurrent
        """

        props = dict({"Objects": [assignment], "Direction": dict({"Start": point1, "End": point2})})
        return self._create_boundary(name, props, source_type)

    @pyaedt_function_handler(
        face="assignment", nummodes="modes", portname="name", renorm="renormalize", deembed_dist="deembed_distance"
    )
    def create_floquet_port(
        self,
        assignment,
        lattice_origin=None,
        lattice_a_end=None,
        lattice_b_end=None,
        modes=2,
        name=None,
        renormalize=True,
        deembed_distance=0,
        reporter_filter=True,
        lattice_cs="Global",
    ):
        """Create a floquet port on a face.

        Parameters
        ----------
        assignment :
            Face or sheet to apply the floquet port to.
        lattice_origin : list
            List of ``[x,y,z]`` coordinates for the lattice A-B origin. The default is ``None``,
            in which case the method tries to compute the A-B automatically.
        lattice_a_end : list
            List of ``[x,y,z]`` coordinates for the lattice A end point. The default is ``None``,
            in which case the method tries to compute the A-B automatically.
        lattice_b_end : list
            List of ``[x,y,z]`` coordinates for the lattice B end point. The default is ``None``,
            in which case the method tries to compute the A-B automatically.
        modes : int, optional
            Number of modes. The default is ``2``.
        name : str, optional
            Name of the port. The default is ``None``.
        renormalize : bool, optional
            Whether to renormalize the mode. The default is ``True``.
        deembed_distance : float, str, optional
            Deembed distance in millimeters. The default is ``0``,
            in which case deembed is disabled.
        reporter_filter : bool, list of bool
            Whether to include modes in the report. The default is ``True``. If a single
            Boolean value is specified, it applies to all modes. If a list of Boolean values is specified, it applies
            to each mode in the list. A list must have ``nummodes`` elements.
        lattice_cs : str, optional
            Coordinate system for the lattice A-B vector reference. The default is ``Global``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Boundary object.


        References
        ----------
        >>> oModule.AssignFloquetPort
        """
        face_id = self.modeler.convert_to_selections(assignment, True)
        props = {}
        if isinstance(face_id[0], int):
            props["Faces"] = face_id
        else:
            props["Objects"] = face_id

        props["NumModes"] = modes
        if deembed_distance:
            props["DoDeembed"] = True
            props["DeembedDist"] = self.modeler._arg_with_dim(deembed_distance)
        else:
            props["DoDeembed"] = False
            props["DeembedDist"] = "0mm"
        props["RenormalizeAllTerminals"] = renormalize
        props["Modes"] = {}
        for i in range(1, 1 + modes):
            props["Modes"][f"Mode{i}"] = {}
            props["Modes"][f"Mode{i}"]["ModeNum"] = i
            props["Modes"][f"Mode{i}"]["UseIntLine"] = False
            props["Modes"][f"Mode{i}"]["CharImp"] = "Zpi"
        props["ShowReporterFilter"] = True
        if isinstance(reporter_filter, bool):
            props["ReporterFilter"] = [reporter_filter for i in range(modes)]
        else:
            props["ReporterFilter"] = reporter_filter
        if not lattice_a_end or not lattice_origin or not lattice_b_end:
            result, output = self.modeler._find_perpendicular_points(face_id[0])
            lattice_origin = output[0]
            lattice_a_end = output[1]
            lattice_b_end = output[2]
        props["LatticeAVector"] = {}
        props["LatticeAVector"]["Coordinate System"] = lattice_cs
        props["LatticeAVector"]["Start"] = lattice_origin
        props["LatticeAVector"]["End"] = lattice_a_end
        props["LatticeBVector"] = {}
        props["LatticeBVector"]["Coordinate System"] = lattice_cs
        props["LatticeBVector"]["Start"] = lattice_origin
        props["LatticeBVector"]["End"] = lattice_b_end
        if not name:
            name = generate_unique_name("Floquet")
        return self._create_boundary(name, props, "Floquet Port")

    @pyaedt_function_handler(face_couple="assignment", pair_name="name")
    def assign_lattice_pair(
        self,
        assignment,
        reverse_v=False,
        phase_delay="UseScanAngle",
        phase_delay_param1="0deg",
        phase_delay_param2="0deg",
        name=None,
    ):
        """Assign a lattice pair to a couple of faces.

        Parameters
        ----------
        assignment : list
            List of two faces to assign the lattice pair to.
        reverse_v : bool, optional
            Whether to reverse the V vector. The default is `False`.
        phase_delay : str, optional
            Phase delay approach. Options are ``"UseScanAngle"``,
            ``"UseScanUV"``, and ``"InputPhaseDelay"``. The default is
            ``"UseScanAngle"``.
        phase_delay_param1 : str, optional
            Value for the first phase delay parameter, which depends on the approach:

            - Phi angle if the approach is ``"UseScanAngle"``.
            - U value if the approach is ``"UseScanUV"``.
            - Phase if the approach is ``"InputPhaseDelay"``.

            The default is ``0deg``.

        phase_delay_param2 :  str, optional
            Value for the second phase delay parameter, which depends on the approach:

            - Theta angle if the approach is "``UseScanAngle"``.
            - V value if the approach is ``"UseScanUV"``.

            The default is ``0deg``.
        name : str, optional
            Boundary name.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Boundary object.

        References
        ----------
        >>> oModule.AssignLatticePair
        """
        props = {}
        face_id = self.modeler.convert_to_selections(assignment, True)
        props["Faces"] = face_id
        props["ReverseV"] = reverse_v

        props["PhaseDelay"] = phase_delay
        if phase_delay == "UseScanAngle":
            props["Phi"] = phase_delay_param1
            props["Theta"] = phase_delay_param2
        elif phase_delay == "UseScanUV":
            props["ScanU"] = phase_delay_param1
            props["ScanV"] = phase_delay_param2
        else:
            props["Phase"] = phase_delay_param1
        if not name:
            name = generate_unique_name("LatticePair")
        return self._create_boundary(name, props, "Lattice Pair")

    @pyaedt_function_handler(object_to_assign="assignment")
    def auto_assign_lattice_pairs(self, assignment, coordinate_system="Global", coordinate_plane="XY"):
        """Assign lattice pairs to a geometry automatically.

        Parameters
        ----------
        assignment : str, :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
            Object to assign a lattice to.
        coordinate_system : str, optional
            Coordinate system to look for the lattice on.
        coordinate_plane : str, optional
            Plane to look for the lattice on. Options are ``"XY"``, ``"XZ"``, and
            ``"YZ"``. The default is ``"XY"``.

        Returns
        -------
        list of str
            List of created pair names.

        References
        ----------
        >>> oModule.AutoIdentifyLatticePair
        """
        objectname = self.modeler.convert_to_selections(assignment, True)
        boundaries = list(self.oboundary.GetBoundaries())
        self.oboundary.AutoIdentifyLatticePair(f"{coordinate_system}:{coordinate_plane}", objectname[0])
        boundaries = [i for i in list(self.oboundary.GetBoundaries()) if i not in boundaries]
        bounds = [i for i in boundaries if boundaries.index(i) % 2 == 0]
        return bounds

    @pyaedt_function_handler(
        face="assignment", primary_name="primary", coord_name="coordinate_system", secondary_name="name"
    )
    def assign_secondary(
        self,
        assignment,
        primary,
        u_start,
        u_end,
        reverse_v=False,
        phase_delay="UseScanAngle",
        phase_delay_param1="0deg",
        phase_delay_param2="0deg",
        coordinate_system="Global",
        name=None,
    ):
        """Assign the secondary boundary condition.

        Parameters
        ----------
        assignment : int, FacePrimitive
            Face to assign the lattice pair to.
        primary : str
            Name of the primary boundary to couple.
        u_start : list
            List of ``[x,y,z]`` values for the starting point of the U vector.
        u_end : list
            List of ``[x,y,z]`` values for the ending point of the U vector.
        reverse_v : bool, optional
            Whether to reverse the V vector. The default is ``False``.
        phase_delay : str, optional
            Phase delay approach. Options are ``"UseScanAngle"``,
            ``"UseScanUV"``, and ``"InputPhaseDelay"``. The default is
            ``"UseScanAngle"``.
        phase_delay_param1 : str, optional
            Value for the first phase delay parameter, which depends on the approach:

            - Phi angle if the approach is ``"UseScanAngle"``.
            - U value if the approach is ``"UseScanUV"``.
            - Phase if the approach is ``"InputPhaseDelay"``.

            The default is ``0deg``.
        phase_delay_param2 :  str, optional
            Value for the second phase delay parameter, which depends on the approach:

            - Theta angle if the approach is "``UseScanAngle"``.
            - V value if the approach is ``"UseScanUV"``.

            The default is ``0deg``.
        coordinate_system : str, optional
            Name of the coordinate system for U coordinates.
        name : str, optional
            Name of the boundary. The default is ``None``,
            in which case a name is automatically assigned.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Boundary object.

        References
        ----------
        >>> oModule.AssignSecondary
        """
        props = {}
        face_id = self.modeler.convert_to_selections(assignment, True)
        if isinstance(face_id[0], str):
            props["Objects"] = face_id

        else:
            props["Faces"] = face_id

        props["CoordSysVector"] = {}
        props["CoordSysVector"]["Coordinate System"] = coordinate_system
        props["CoordSysVector"]["Origin"] = u_start
        props["CoordSysVector"]["UPos"] = u_end
        props["ReverseV"] = reverse_v

        props["Primary"] = primary
        props["PhaseDelay"] = phase_delay
        if phase_delay == "UseScanAngle":
            props["Phi"] = phase_delay_param1
            props["Theta"] = phase_delay_param2
        elif phase_delay == "UseScanUV":
            props["ScanU"] = phase_delay_param1
            props["ScanV"] = phase_delay_param2
        else:
            props["Phase"] = phase_delay_param1
        if not name:
            name = generate_unique_name("Secondary")
        return self._create_boundary(name, props, "Secondary")

    @pyaedt_function_handler(face="assignment", coord_name="coordinate_system", primary_name="name")
    def assign_primary(self, assignment, u_start, u_end, reverse_v=False, coordinate_system="Global", name=None):
        """Assign the primary boundary condition.

        Parameters
        ----------
        assignment : int, FacePrimitive
            Face to assign the lattice pair to.
        u_start : list
            List of ``[x,y,z]`` values for the starting point of the U vector.
        u_end : list
            List of ``[x,y,z]`` values for the ending point of the U vector.
        reverse_v : bool, optional
            Whether to reverse the V vector. The default is `False`.
        coordinate_system : str, optional
            Name of the coordinate system for the U coordinates. The
            default is ``"Global"``.
        name : str, optional
            Name of the boundary. The default is ``None``,
            in which case a name is automatically assigned.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Boundary object.

        References
        ----------
        >>> oModule.AssignPrimary
        """
        props = {}
        face_id = self.modeler.convert_to_selections(assignment, True)
        if isinstance(face_id[0], str):
            props["Objects"] = face_id

        else:
            props["Faces"] = face_id
        props["ReverseV"] = reverse_v
        props["CoordSysVector"] = {}
        props["CoordSysVector"]["Coordinate System"] = coordinate_system
        props["CoordSysVector"]["Origin"] = u_start
        props["CoordSysVector"]["UPos"] = u_end
        if not name:
            name = generate_unique_name("Primary")
        return self._create_boundary(name, props, "Primary")

    def _create_pec_cap(self, sheet_name, obj_name, pecthick):
        """Create a PEC object to back a wave port.

        Parameters
        ----------
        sheet_name : str
            Name of the sheet object touching the port surface.
        obj_name : str
            Name of the 3D object touching the port surface.
        pecthick : float
            Thickness of the PEC cap

        Returns
        -------
        bool
           ``True`` when successful, ``False`` when failed.
        """
        if isinstance(sheet_name, str) and isinstance(obj_name, cad.elements_3d.FacePrimitive):
            obj = obj_name.create_object()  # Create face object of type cad.object_3d.Object3d from FacePrimitive
            oname = obj_name._object3d.name
            bounding1 = self.modeler[oname].bounding_box
        else:
            obj = self.modeler[sheet_name].clone()
            bounding1 = self.modeler[obj_name].bounding_box
        out_obj = self.modeler.thicken_sheet(obj, pecthick, False)
        bounding2 = out_obj.bounding_box
        tol = 1e-9
        i = 0

        # Check that the pec cap is internal by comparing the bounding box
        # of the cap with the bounding box of obj_name.
        internal = False
        for a, b in zip(bounding1, bounding2):
            if i < 3:
                if (b - a) > tol:
                    internal = True
            elif (b - a) < tol:
                internal = True
            i += 1
        if internal:
            self.odesign.Undo()
            self.modeler.cleanup_objects()
            out_obj = self.modeler.thicken_sheet(obj, -pecthick, False)

        out_obj.material_name = "pec"
        return True

    @pyaedt_function_handler(
        startobj="assignment",
        endobj="reference",
        sourcename="name",
        is_infinite_gnd="is_infinite_ground",
        bound_on_plane="is_boundary_on_plane",
        axisdir="start_direction",
    )
    def create_perfecte_from_objects(
        self, assignment, reference, start_direction=0, name=None, is_infinite_ground=False, is_boundary_on_plane=True
    ):
        """Create a Perfect E taking the closest edges of two objects.

        Parameters
        ----------
        assignment : str or int or :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
            Starting object for the integration line.
        reference :  str or int or :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
           Ending object for the integration line.
        start_direction : int or :class:`ansys.aedt.core.application.analysis.Analysis.AxisDir`, optional
            Start direction for the boundary location. It should be one of the values for
            ``Application.AxisDir``, which are: ``XNeg``, ``YNeg``,
            ``ZNeg``, ``XPos``, ``YPos``, and ``ZPos``.  The default
            is ``Application.AxisDir.XNeg``.
        name : str, optional
            Perfect E name. The default is ``None``, in which
            case a name is automatically assigned.
        is_infinite_ground : bool, optional
            Whether the Perfect E is an infinite ground. The default is ``False``.
        is_boundary_on_plane : bool, optional
            Whether to create the Perfect E on the plane orthogonal to
            the axis direction. The default is ``True``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject` or bool
            Boundary object if successful, ``False`` otherwise.

        References
        ----------
        >>> oModule.AssignPerfectE

        Examples
        --------

        Create two boxes for creating a Perfect E named ``'PerfectE'``.

        >>> box1 = hfss.modeler.create_box([0,0,0],[10,10,5],"perfect1","Copper")
        >>> box2 = hfss.modeler.create_box([0, 0, 10],[10, 10, 5],"perfect2","copper")
        >>> perfect_e = hfss.create_perfecte_from_objects("perfect1","perfect2",hfss.AxisDir.ZNeg,"PerfectE")
        PyAEDT INFO: Connection Correctly created
        >>> type(perfect_e)
        <class 'from ansys.aedt.core.modules.boundary.common.BoundaryObject'>

        """

        if not self.modeler.does_object_exists(assignment) or not self.modeler.does_object_exists(reference):
            raise ValueError("One or both objects do not exist. Check and retry.")
        if self.solution_type not in (
            SOLUTIONS.Hfss.DrivenModal,
            SOLUTIONS.Hfss.DrivenTerminal,
            SOLUTIONS.Hfss.Transient,
        ):
            raise AEDTRuntimeError("Invalid solution type.")

        sheet_name, _, _ = self.modeler._create_sheet_from_object_closest_edge(
            assignment, reference, start_direction, is_boundary_on_plane
        )

        if not name:
            name = generate_unique_name("PerfE")
        elif name in self.modeler.get_boundaries_name():
            name = generate_unique_name(name)
        return self.create_boundary(self.BoundaryType.PerfectE, sheet_name, name, is_infinite_ground)

    @pyaedt_function_handler(
        startobj="assignment",
        endobject="reference",
        sourcename="name",
        bound_on_plane="is_boundary_on_plane",
        axisdir="start_direction",
    )
    def create_perfecth_from_objects(
        self, assignment, reference, start_direction=0, name=None, is_boundary_on_plane=True
    ):
        """Create a Perfect H taking the closest edges of two objects.

        Parameters
        ----------
        assignment : str or int or :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
            Starting object for the integration line.
        reference : str or int or :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
            Ending object for the integration line.
        start_direction : int or :class:`ansys.aedt.core.application.analysis.Analysis.AxisDir`, optional
            Start direction for the boundary location. It should be one of the values for ``Application.AxisDir``,
            which are: ``XNeg``, ``YNeg``, ``ZNeg``, ``XPos``, ``YPos``, and ``ZPos``.
            The default is ``Application.AxisDir.XNeg``.
        name : str, optional
            Perfect H name. The default is ``None``,
             in which case a name is automatically assigned.
        is_boundary_on_plane : bool, optional
            Whether to create the Perfect H on the plane
            orthogonal to the axis direction. The default is ``True``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject` or bool
            Boundary object if successful, ``False`` otherwise.

        References
        ----------
        >>> oModule.AssignPerfectH

        Examples
        --------

        Create two boxes for creating a Perfect H named ``'PerfectH'``.

        >>> box1 = hfss.modeler.create_box([0,0,20],[10,10,5],"perfect1","Copper")
        >>> box2 = hfss.modeler.create_box([0, 0, 30],[10, 10, 5],"perfect2","copper")
        >>> perfect_h = hfss.create_perfecth_from_objects("perfect1","perfect2",hfss.AxisDir.ZNeg,"Perfect H")
        PyAEDT INFO: Connection Correctly created
        >>> type(perfect_h)
        <class 'from ansys.aedt.core.modules.boundary.common.BoundaryObject'>

        """

        if not self.modeler.does_object_exists(assignment) or not self.modeler.does_object_exists(reference):
            raise ValueError("One or both objects do not exist. Check and retry.")
        if self.solution_type not in (
            SOLUTIONS.Hfss.DrivenModal,
            SOLUTIONS.Hfss.DrivenTerminal,
            SOLUTIONS.Hfss.Transient,
        ):
            raise AEDTRuntimeError("Invalid solution type.")

        sheet_name, _, _ = self.modeler._create_sheet_from_object_closest_edge(
            assignment, reference, start_direction, is_boundary_on_plane
        )
        if not name:
            name = generate_unique_name("PerfH")
        elif name in self.modeler.get_boundaries_name():
            name = generate_unique_name(name)
        return self.create_boundary(self.BoundaryType.PerfectH, sheet_name, name)

    @pyaedt_function_handler(
        Tissue_object_List_ID="assignment",
        TissueMass="tissue_mass",
        MaterialDensity="material_density",
        Average_SAR_method="average_sar_method",
    )
    def sar_setup(self, assignment=-1, tissue_mass=1, material_density=1, voxel_size=1, average_sar_method=0):
        """Define SAR settings.

        Parameters
        ----------
        assignment : int, optional
           Object ID. The default is ``-1`` to not specify the object.
        tissue_mass : float, optional
            Mass of tissue in grams. The default is ``1``.
        material_density : optional
            Density of material in gram/cm^3. The default is ``1``.
        voxel_size : optional
            Size of a voxel in millimeters. The default is ``1``.
        average_sar_method : optional
            SAR method. There are two options, ``0`` for IEEE Standard 1528 and ``1`` for the standard Ansys method.
            The default is ``0``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesign.SARSetup
        """
        self.odesign.SARSetup(tissue_mass, material_density, assignment, voxel_size, average_sar_method)
        self.logger.info("SAR settings are correctly applied.")
        return True

    @pyaedt_function_handler(
        Frequency="frequency", Boundary="boundary", ApplyInfiniteGP="apply_infinite_ground", GPAXis="gp_axis"
    )
    def create_open_region(self, frequency="1GHz", boundary="Radiation", apply_infinite_ground=False, gp_axis="-z"):
        """Create an open region on the active editor.

        Parameters
        ----------
        frequency : str, optional
            Frequency with units. The default is ``"1GHz"``.
        boundary : str, optional
            Type of the boundary. The default is ``"Radiation"``.
        apply_infinite_ground : bool, optional
            Whether to apply an infinite ground plane. The default is ``False``.
        gp_axis : str, optional
            Open region direction. The default is ``"-z"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.CreateOpenRegion
        """
        vars = [
            "NAME:Settings",
            "OpFreq:=",
            frequency,
            "Boundary:=",
            boundary,
            "ApplyInfiniteGP:=",
            apply_infinite_ground,
        ]
        if apply_infinite_ground:
            vars.append("Direction:=")
            vars.append(gp_axis)

        self.omodelsetup.CreateOpenRegion(vars)
        self.logger.info("Open Region correctly created.")
        self.save_project()
        return True

    @pyaedt_function_handler(
        startobj="assignment",
        endobj="reference",
        sourcename="name",
        rlctype="rlc_type",
        Rvalue="resistance",
        Lvalue="inductance",
        Cvalue="capacitance",
        bound_on_plane="is_boundary_on_plane",
        axisdir="start_direction",
    )
    def create_lumped_rlc_between_objects(
        self,
        assignment,
        reference,
        start_direction=0,
        name=None,
        rlc_type="Parallel",
        resistance=None,
        inductance=None,
        capacitance=None,
        is_boundary_on_plane=True,
    ):
        """Create a lumped RLC taking the closest edges of two objects.

        Parameters
        ----------
        assignment :
            Starting object for the integration line.
        reference :
            Ending object for the integration line.
        start_direction : int or :class:`ansys.aedt.core.application.analysis.Analysis.AxisDir`, optional
            Start direction for the boundary location.. It should be one of the values for ``Application.AxisDir``,
            which are: ``XNeg``, ``YNeg``, ``ZNeg``, ``XPos``, ``YPos``, and ``ZPos``.
            The default is ``Application.AxisDir.XNeg``.
        name : str, optional
            Perfect H name. The default is ``None``, in which
            case a name is automatically assigned.
        rlc_type : str, optional
            Type of the RLC. Options are ``"Parallel"`` and ``"Serial"``.
            The default is ``"Parallel"``.
        resistance : optional
            Resistance value in ohms. The default is ``None``,
            in which case this parameter is disabled.
        inductance : optional
            Inductance value in H. The default is ``None``,
            in which case this parameter is disabled.
        capacitance : optional
            Capacitance value in F. The default is ``None``,
            in which case this parameter is disabled.
        is_boundary_on_plane : bool, optional
            Whether to create the boundary on the plane orthogonal
            to ``AxisDir``. The default is ``True``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject` or bool
            Boundary object if successful, ``False`` otherwise.

        References
        ----------
        >>> oModule.AssignLumpedRLC

        Examples
        --------

        Create two boxes for creating a lumped RLC named ``'LumpedRLC'``.

        >>> box1 = hfss.modeler.create_box([0, 0, 50],[10, 10, 5],"rlc1","copper")
        >>> box2 = hfss.modeler.create_box([0, 0, 60],[10, 10, 5],"rlc2","copper")
        >>> rlc = hfss.create_lumped_rlc_between_objects("rlc1","rlc2",hfss.AxisDir.XPos,"Lumped RLC",resistance=50,
        ...                                              inductance=1e-9, capacitance=1e-6)
        PyAEDT INFO: Connection Correctly created

        """

        if not self.modeler.does_object_exists(assignment) or not self.modeler.does_object_exists(reference):
            raise AEDTRuntimeError("One or both objects do not exist. Check and retry.")
        if self.solution_type not in (
            SOLUTIONS.Hfss.DrivenModal,
            SOLUTIONS.Hfss.DrivenTerminal,
            SOLUTIONS.Hfss.Transient,
        ):
            raise AEDTRuntimeError("Invalid solution type.")
        if not (resistance or inductance or capacitance):
            raise ValueError(
                "A value is required to at least a parameter among `resistance`, `inductance` or `capacitance`."
            )

        sheet_name, point0, point1 = self.modeler._create_sheet_from_object_closest_edge(
            assignment, reference, start_direction, is_boundary_on_plane
        )
        if not name:
            name = generate_unique_name("Lump")
        elif name in self.modeler.get_boundaries_name():
            name = generate_unique_name(name)
        start = [str(i) + self.modeler.model_units for i in point0]
        stop = [str(i) + self.modeler.model_units for i in point1]

        props = {}
        props["Objects"] = [sheet_name]
        props["CurrentLine"] = dict({"Start": start, "End": stop})
        props["RLC Type"] = rlc_type
        if resistance:
            props["UseResist"] = True
            props["Resistance"] = str(resistance) + "ohm"
        if inductance:
            props["UseInduct"] = True
            props["Inductance"] = str(inductance) + "H"
        if capacitance:
            props["UseCap"] = True
            props["Capacitance"] = str(capacitance) + "farad"

        return self._create_boundary(name, props, "Lumped RLC")

    @pyaedt_function_handler(
        startobj="start_assignment",
        endobject="end_assignment",
        axisdir="start_direction",
        sourcename="source_name",
        is_infground="is_infinite_ground",
    )
    def create_impedance_between_objects(
        self,
        start_assignment,
        end_assignment,
        start_direction=0,
        source_name=None,
        resistance=50,
        reactance=0,
        is_infinite_ground=False,
        bound_on_plane=True,
    ):
        """Create an impedance taking the closest edges of two objects.

        Parameters
        ----------
        start_assignment : str or int or :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
            Starting object for the integration line.
        end_assignment : str or int or :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
            Ending object for the integration line.
        start_direction : int or :class:`ansys.aedt.core.application.analysis.Analysis.AxisDir`, optional
            Start direction for the boundary location. It should be one of the values for ``Application.AxisDir``,
            which are: ``XNeg``, ``YNeg``, ``ZNeg``, ``XPos``, ``YPos``, and ``ZPos``.
            The default is ``Application.AxisDir.XNeg``.
        source_name : str, optional
            Name of the impedance. The default is ``None``.
        resistance : float, optional
            Resistance value in ohms. The default is ``50``. If ``None``,
            this parameter is disabled.
        reactance : optional
            Reactance value in ohms. The default is ``0``. If ``None``,
            this parameter is disabled.
        is_infinite_ground : bool, optional
            Whether the impendance is an infinite ground. The default is ``False``.
        bound_on_plane : bool, optional
            Whether to create the impedance on the plane orthogonal to ``AxisDir``.
            The default is ``True``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject` or bool
            Boundary object if successful, ``False`` otherwise.

        References
        ----------
        >>> oModule.AssignImpedance

        Examples
        --------

        Create two boxes for creating an impedance named ``'ImpedanceExample'``.

        >>> box1 = hfss.modeler.create_box([0, 0, 70],[10, 10, 5],"box1","copper")
        >>> box2 = hfss.modeler.create_box([0, 0, 80],[10, 10, 5],"box2","copper")
        >>> impedance = hfss.create_impedance_between_objects("box1", "box2", hfss.AxisDir.XPos,
        ...                                                   "ImpedanceExample", 100, 50)
        PyAEDT INFO: Connection Correctly created

        """

        if not self.modeler.does_object_exists(start_assignment) or not self.modeler.does_object_exists(end_assignment):
            raise AEDTRuntimeError("One or both objects do not exist. Check and retry.")
        if self.solution_type not in (
            SOLUTIONS.Hfss.DrivenModal,
            SOLUTIONS.Hfss.DrivenTerminal,
            SOLUTIONS.Hfss.Transient,
        ):
            raise AEDTRuntimeError("Invalid solution type.")

        sheet_name, _, _ = self.modeler._create_sheet_from_object_closest_edge(
            start_assignment, end_assignment, start_direction, bound_on_plane
        )

        if not source_name:
            source_name = generate_unique_name("Imped")
        elif source_name in self.modeler.get_boundaries_name():
            source_name = generate_unique_name(source_name)
        props = dict(
            {
                "Objects": [sheet_name],
                "Resistance": str(resistance),
                "Reactance": str(reactance),
                "InfGroundPlane": is_infinite_ground,
            }
        )
        return self._create_boundary(source_name, props, "Impedance")

    @pyaedt_function_handler(sheet_name="assignment", boundary_name="name", is_inifinite_gnd="is_inifinite_ground")
    def create_boundary(
        self, boundary_type=BoundaryType.PerfectE, assignment=None, name=None, is_inifinite_ground=False
    ):
        """Assign a boundary condition to a sheet or surface.

        This method is generally used by other methods in the ``Hfss`` class such as the
        :meth:``Hfss.assign_febi`` or :meth:``Hfss.assign_radiation_boundary_to_faces`` method.

        Parameters
        ----------
        boundary_type : int, optional
            Type of boundary condition to assign to a sheet or surface. The
            default is ``Hfss.BoundaryType.PerfectE``. Options are the properties of the
            :class:``Hfss.BoundaryType`` class. For example:

                - ``Hfss.BoundaryType.PerfectE``
                - ``Hfss.BoundaryType.PerfectH``
                - ``Hfss.BoundaryType.Radiation``
                - ``Hfss.BoundaryType.Impedance``
                - ``Hfss.BoundaryType.LumpedRLC``
                - ``Hfss.BoundaryType.FEBI``

        assignment : int, str, or list, optional
            Name of the sheet or face to assign the boundary condition to. The
            default is ``None``. You can provide an integer (face ID), a string (sheet),
            or a list of integers and strings.
        name : str, optional
            Name of the boundary. The default is ``None``.
        is_inifinite_ground : bool, optional
            Whether the boundary is an infinite ground. The default is ``False``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Boundary object.

        """
        props = {}
        assignment = self.modeler.convert_to_selections(assignment, True)
        if type(assignment) is list:
            if type(assignment[0]) is str:
                props["Objects"] = assignment
            else:
                props["Faces"] = assignment

        if boundary_type == self.BoundaryType.PerfectE:
            props["InfGroundPlane"] = is_inifinite_ground
            boundary_type = "Perfect E"
        elif boundary_type == self.BoundaryType.PerfectH:
            boundary_type = "Perfect H"
        elif boundary_type == self.BoundaryType.Aperture:
            boundary_type = "Aperture"
        elif boundary_type == self.BoundaryType.Radiation:
            props["IsFssReference"] = False
            props["IsForPML"] = False
            boundary_type = "Radiation"
        elif boundary_type == self.BoundaryType.Hybrid:
            props["IsLinkedRegion"] = False
            props["Type"] = "SBR+"
            boundary_type = "Hybrid"
        elif boundary_type == self.BoundaryType.FEBI:
            boundary_type = "FE-BI"
        else:
            return None
        return self._create_boundary(name, props, boundary_type)

    @pyaedt_function_handler()
    def _get_reference_and_integration_points(self, sheet, axisdir, obj_name=None):
        if isinstance(sheet, int):
            objID = [sheet]
            sheet = obj_name
        else:
            objID = self.modeler.oeditor.GetFaceIDs(sheet)
        face_edges = self.modeler.get_face_edges(objID[0])
        mid_points = [self.modeler.get_edge_midpoint(i) for i in face_edges]
        if axisdir < 3:
            min_point = [1e6, 1e6, 1e6]
            max_point = [-1e6, -1e6, -1e6]
            for el in mid_points:
                if el[axisdir] < min_point[axisdir]:
                    min_point = el
                if el[axisdir] > max_point[axisdir]:
                    max_point = el
        else:
            min_point = [-1e6, -1e6, -1e6]
            max_point = [1e6, 1e6, 1e6]
            for el in mid_points:
                if el[axisdir - 3] > min_point[axisdir - 3]:
                    min_point = el
                if el[axisdir - 3] < max_point[axisdir - 3]:
                    max_point = el

        refid = self.modeler.get_bodynames_from_position(min_point)
        refid.remove(sheet)
        diels = self.get_all_dielectrics_names()
        for el in refid:
            if el in diels:
                refid.remove(el)

        int_start = None
        int_stop = None
        if min_point != max_point:
            int_start = min_point
            int_stop = max_point
        return refid, int_start, int_stop

    @pyaedt_function_handler(sheet_name="assignment", sourcename="name", axisdir="start_direction")
    def assign_voltage_source_to_sheet(self, assignment, start_direction=0, name=None):
        """Create a voltage source taking one sheet.

        Parameters
        ----------
        assignment : str
            Name of the sheet to apply the boundary to.
        start_direction : int, :class:`ansys.aedt.core.application.analysis.Analysis.AxisDir` or list, optional
            Direction of the integration line. It should be one of the values for ``Application.AxisDir``,
            which are: ``XNeg``, ``YNeg``, ``ZNeg``, ``XPos``, ``YPos``, and ``ZPos``. It also accepts the list
            of the start point and end point with the format [[xstart, ystart, zstart], [xend, yend, zend]]
            The default is ``Application.AxisDir.XNeg``.
        name : str, optional
            Name of the source. The default is ``None``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Boundary object.

        References
        ----------
        >>> oModule.AssignVoltage

        Examples
        --------
        Create a sheet and assign to it some voltage.

        >>> sheet = hfss.modeler.create_rectangle(hfss.PLANE.XY,[0, 0, -70],[10, 2],
        ...                                       name="VoltageSheet",material="copper")
        >>> v1 = hfss.assign_voltage_source_to_sheet(sheet.name,hfss.AxisDir.XNeg,"VoltageSheetExample")
        >>> v2 = hfss.assign_voltage_source_to_sheet(sheet.name,[sheet.bottom_edge_x.midpoint,
        ...                                     sheet.bottom_edge_y.midpoint],50)

        """
        if self.solution_type not in (
            SOLUTIONS.Hfss.DrivenModal,
            SOLUTIONS.Hfss.DrivenTerminal,
            SOLUTIONS.Hfss.Transient,
        ):
            raise AEDTRuntimeError("Invalid solution type.")

        if isinstance(start_direction, list):
            if len(start_direction) != 2 or len(start_direction[0]) != len(start_direction[1]):
                raise AEDTRuntimeError("List of coordinates is not set correctly")
            point0 = start_direction[0]
            point1 = start_direction[1]
        else:
            point0, point1 = self.modeler.get_mid_points_on_dir(assignment, start_direction)
        name = self._get_unique_source_name(name, "Voltage")
        return self.create_source_excitation(assignment, point0, point1, name, source_type="Voltage")

    @pyaedt_function_handler(sheet_name="assignment", sourcename="name", axisdir="start_direction")
    def assign_current_source_to_sheet(self, assignment, start_direction=0, name=None):
        """Create a current source taking one sheet.

        Parameters
        ----------
        assignment : str
            Name of the sheet to apply the boundary to.
        start_direction : int, :class:`ansys.aedt.core.application.analysis.Analysis.AxisDir` or list, optional
            Direction of the integration line. It should be one of the values for ``Application.AxisDir``,
            which are: ``XNeg``, ``YNeg``, ``ZNeg``, ``XPos``, ``YPos``, and ``ZPos``. It also accepts the list
            of the start point and end point with the format [[xstart, ystart, zstart], [xend, yend, zend]]
            The default is ``Application.AxisDir.XNeg``.
        name : str, optional
            Name of the source. The default is ``None``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Boundary object.

        References
        ----------
        >>> oModule.AssignCurrent

        Examples
        --------

        Create a sheet and assign some current to it.

        >>> sheet = hfss.modeler.create_rectangle(hfss.PLANE.XY,[0, 0, -50],[5, 1],
        ...                                       name="CurrentSheet",material="copper")
        >>> hfss.assign_current_source_to_sheet(sheet.name,hfss.AxisDir.XNeg,"CurrentSheetExample")
        'CurrentSheetExample'
        >>> c1 = hfss.assign_current_source_to_sheet(sheet.name,[sheet.bottom_edge_x.midpoint,
        ...                                     sheet.bottom_edge_y.midpoint])

        """

        if self.solution_type not in (
            SOLUTIONS.Hfss.DrivenModal,
            SOLUTIONS.Hfss.DrivenTerminal,
            SOLUTIONS.Hfss.Transient,
        ):
            raise AEDTRuntimeError("Invalid solution type.")

        if isinstance(start_direction, list):
            if len(start_direction) != 2 or len(start_direction[0]) != len(start_direction[1]):
                raise AEDTRuntimeError("List of coordinates is not set correctly")
            point0 = start_direction[0]
            point1 = start_direction[1]
        else:
            point0, point1 = self.modeler.get_mid_points_on_dir(assignment, start_direction)
        name = self._get_unique_source_name(name, "Current")
        return self.create_source_excitation(assignment, point0, point1, name, source_type="Current")

    @pyaedt_function_handler(sheet_list="assignment", sourcename="name", is_infinite_gnd="is_infinite_ground")
    def assign_perfecte_to_sheets(self, assignment, name=None, is_infinite_ground=False):
        """Create a Perfect E taking one sheet.

        Parameters
        ----------
        assignment : str or list
            One or more names of the sheets to apply the boundary to.
        name : str, optional
            Name of the Perfect E source. The default is ``None``.
        is_infinite_ground : bool, optional
            Whether the Perfect E is an infinite ground. The default is ``False``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Boundary object.

        References
        ----------
        >>> oModule.AssignPerfectE

        Examples
        --------

        Create a sheet and use it to create a Perfect E.

        >>> sheet = hfss.modeler.create_rectangle(hfss.PLANE.XY, [0, 0, -90],
        ...                                       [10, 2], name="PerfectESheet", material="Copper")
        >>> perfect_e_from_sheet = hfss.assign_perfecte_to_sheets(sheet.name,"PerfectEFromSheet")
        >>> type(perfect_e_from_sheet)
        <class 'from ansys.aedt.core.modules.boundary.common.BoundaryObject'>

        """
        if self.solution_type not in (
            SOLUTIONS.Hfss.DrivenModal,
            SOLUTIONS.Hfss.DrivenTerminal,
            SOLUTIONS.Hfss.Transient,
            SOLUTIONS.Hfss.SBR,
            SOLUTIONS.Hfss.EigenMode,
        ):
            raise AEDTRuntimeError("Invalid solution type.")

        assignment = self.modeler.convert_to_selections(assignment, True)
        if not name:
            name = generate_unique_name("PerfE")
        elif name in self.modeler.get_boundaries_name():
            name = generate_unique_name(name)
        return self.create_boundary(self.BoundaryType.PerfectE, assignment, name, is_infinite_ground)

    @pyaedt_function_handler(sheet_list="assignment", sourcename="name")
    def assign_perfecth_to_sheets(self, assignment, name=None):
        """Assign a Perfect H to sheets.

        Parameters
        ----------
        assignment : list
            List of sheets to apply the boundary to.
        name : str, optional
            Perfect H name. The default is ``None``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Boundary object.

        References
        ----------
        >>> oModule.AssignPerfectH

        Examples
        --------

        Create a sheet and use it to create a Perfect H.

        >>> sheet = hfss.modeler.create_rectangle(hfss.PLANE.XY, [0, 0, -90],
        ...                                       [10, 2], name="PerfectHSheet", material="Copper")
        >>> perfect_h_from_sheet = hfss.assign_perfecth_to_sheets(sheet.name,"PerfectHFromSheet")
        >>> type(perfect_h_from_sheet)
        <class 'from ansys.aedt.core.modules.boundary.common.BoundaryObject'>

        """
        if self.solution_type not in (
            SOLUTIONS.Hfss.DrivenModal,
            SOLUTIONS.Hfss.DrivenTerminal,
            SOLUTIONS.Hfss.Transient,
            SOLUTIONS.Hfss.SBR,
            SOLUTIONS.Hfss.EigenMode,
        ):
            raise AEDTRuntimeError("Invalid solution type.")

        if not name:
            name = generate_unique_name("PerfH")
        elif name in self.modeler.get_boundaries_name():
            name = generate_unique_name(name)
        return self.create_boundary(self.BoundaryType.PerfectH, assignment, name)

    @pyaedt_function_handler(
        sheet_name="assignment",
        sourcename="name",
        rlctype="rlc_type",
        Rvalue="resistance",
        Lvalue="inductance",
        Cvalue="capacitance",
        axisdir="start_direction",
    )
    def assign_lumped_rlc_to_sheet(
        self,
        assignment,
        start_direction=0,
        name=None,
        rlc_type="Parallel",
        resistance=None,
        inductance=None,
        capacitance=None,
    ):
        """Create a lumped RLC taking one sheet.

        Parameters
        ----------
        assignment : str
            Name of the sheet to apply the boundary to.
        start_direction : int, :class:`ansys.aedt.core.application.analysis.Analysis.AxisDir` or list, optional
            Direction of the integration line. It should be one of the values for ``Application.AxisDir``,
            which are: ``XNeg``, ``YNeg``, ``ZNeg``, ``XPos``, ``YPos``, and ``ZPos``. It also accepts the list
            of the start point and end point with the format [[xstart, ystart, zstart], [xend, yend, zend]]
            The default is ``Application.AxisDir.XNeg``.
        name : str, optional
            Lumped RLC name. The default is ``None``.
        rlc_type : str, optional
            Type of the RLC. Options are ``"Parallel"`` and ``"Serial"``. The default is ``"Parallel"``.
        resistance : float, optional
            Resistance value in ohms. The default is ``None``, in which
            case this parameter is disabled.
        inductance : float, optional
            Inductance value in Henry (H). The default is ``None``, in which
            case this parameter is disabled.
        capacitance : float, optional
            Capacitance value in  farads (F). The default is ``None``, in which
            case this parameter is disabled.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Boundary object if successful, ``False`` otherwise.

        References
        ----------
        >>> oModule.AssignLumpedRLC

        Examples
        --------

        Create a sheet and use it to create a lumped RLC.

        >>> sheet = hfss.modeler.create_rectangle(hfss.PLANE.XY,
        ...                                       [0, 0, -90], [10, 2], name="RLCSheet",
        ...                                        material="Copper")
        >>> lumped_rlc_to_sheet = hfss.assign_lumped_rlc_to_sheet(sheet.name,hfss.AxisDir.XPos,resistance=50,
        ...                                                       inductance=1e-9,capacitance=1e-6)
        >>> type(lumped_rlc_to_sheet)
        <class 'from ansys.aedt.core.modules.boundary.common.BoundaryObject'>
        >>> h2 = hfss.assign_lumped_rlc_to_sheet(sheet.name,[sheet.bottom_edge_x.midpoint,
        ...                                      sheet.bottom_edge_y.midpoint],resistance=50,inductance=1e-9,
        ...                                      capacitance=1e-6)

        """
        if self.solution_type not in (
            SOLUTIONS.Hfss.DrivenModal,
            SOLUTIONS.Hfss.DrivenTerminal,
            SOLUTIONS.Hfss.Transient,
            SOLUTIONS.Hfss.SBR,
            SOLUTIONS.Hfss.EigenMode,
        ):
            raise AEDTRuntimeError("Invalid solution type.")
        if not (resistance or inductance or capacitance):
            raise ValueError(
                "A value is required to at least a parameter among `resistance`, `inductance` or `capacitance`."
            )

        if isinstance(start_direction, list):
            if len(start_direction) != 2 or len(start_direction[0]) != len(start_direction[1]):
                raise AEDTRuntimeError("List of coordinates is not set correctly")
            point0 = start_direction[0]
            point1 = start_direction[1]
        else:
            point0, point1 = self.modeler.get_mid_points_on_dir(assignment, start_direction)

        if not name:
            name = generate_unique_name("Lump")
        elif name in self.modeler.get_boundaries_name():
            name = generate_unique_name(name)
        start = [str(i) + self.modeler.model_units for i in point0]
        stop = [str(i) + self.modeler.model_units for i in point1]
        props = {}
        props["Objects"] = [assignment]
        props["CurrentLine"] = dict({"Start": start, "End": stop})
        props["RLC Type"] = rlc_type
        if resistance:
            props["UseResist"] = True
            props["Resistance"] = str(resistance) + "ohm"
        if inductance:
            props["UseInduct"] = True
            props["Inductance"] = str(inductance) + "H"
        if capacitance:
            props["UseCap"] = True
            props["Capacitance"] = str(capacitance) + "F"
        return self._create_boundary(name, props, "Lumped RLC")

    @pyaedt_function_handler(
        sheet_name="assignment", sourcename="name", is_infground="is_infinite_ground", reference_cs="coordinate_system"
    )
    def assign_impedance_to_sheet(
        self,
        assignment,
        name=None,
        resistance=50.0,
        reactance=0.0,
        is_infinite_ground=False,
        coordinate_system="Global",
    ):
        """Create an impedance taking one sheet.

        Parameters
        ----------
        assignment : str or list
            One or more names of the sheets to apply the boundary to.
        name : str, optional
            Name of the impedance. The default is ``None``.
        resistance : float or list, optional
            Resistance value in ohms. The default is ``50.0``.
            If a list of four elements is passed, an anisotropic impedance is assigned with the following order,
            [``Zxx``, ``Zxy``, ``Zyx``, ``Zyy``].
        reactance : optional
            Reactance value in ohms. The default is ``0.0``.
            If a list of four elements is passed, an anisotropic impedance is assigned with the following order,
            [``Zxx``, ``Zxy``, ``Zyx``, ``Zyy``].
        is_infinite_ground : bool, optional
            Whether the impedance is an infinite ground. The default is ``False``.
        coordinate_system : str, optional
            Name of the coordinate system for the XY plane. The default is ``"Global"``.
            This parameter is only used for anisotropic impedance assignment.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Boundary object if successful, ``False`` otherwise.

        References
        ----------
        >>> oModule.AssignImpedance

        Examples
        --------

        Create a sheet and use it to create an impedance.

        >>> sheet = hfss.modeler.create_rectangle(hfss.PLANE.XY,
        ...                                       [0, 0, -90], [10, 2], name="ImpedanceSheet",
        ...                                        material="Copper")
        >>> impedance_to_sheet = hfss.assign_impedance_to_sheet(sheet.name,"ImpedanceFromSheet",100,50)

        Create a sheet and use it to create an anisotropic impedance.

        >>> sheet = hfss.modeler.create_rectangle(hfss.PLANE.XY,
        ...                                       [0, 0, -90], [10, 2], name="ImpedanceSheet",
        ...                                        material="Copper")
        >>> anistropic_impedance_to_sheet = hfss.assign_impedance_to_sheet(sheet.name,
        ...                                                                "ImpedanceFromSheet",
        ...                                                                [377, 0, 0, 377],
        ...                                                                [0, 50, 0, 0])

        """

        if self.solution_type not in (
            SOLUTIONS.Hfss.DrivenModal,
            SOLUTIONS.Hfss.DrivenTerminal,
            SOLUTIONS.Hfss.Transient,
            SOLUTIONS.Hfss.EigenMode,
        ):
            raise AEDTRuntimeError("Invalid solution type.")

        if not name:
            name = generate_unique_name("Imped")
        elif name in self.modeler.get_boundaries_name():
            name = generate_unique_name(name)

        objects = self.modeler.convert_to_selections(assignment, True)

        props = dict(
            {
                "Faces": objects,
            }
        )
        if isinstance(objects[0], str):
            props = dict(
                {
                    "Objects": objects,
                }
            )

        if isinstance(resistance, list) and isinstance(reactance, list):
            if len(resistance) != 4 or len(reactance) != 4:
                raise AEDTRuntimeError("Number of elements in resistance and reactance must be four.")
            props["UseInfiniteGroundPlane"] = is_infinite_ground
            props["CoordSystem"] = coordinate_system
            props["HasExternalLink"] = False
            props["ZxxResistance"] = str(resistance[0])
            props["ZxxReactance"] = str(reactance[0])
            props["ZxyResistance"] = str(resistance[1])
            props["ZxyReactance"] = str(reactance[1])
            props["ZyxResistance"] = str(resistance[2])
            props["ZyxReactance"] = str(reactance[2])
            props["ZyyResistance"] = str(resistance[3])
            props["ZyyReactance"] = str(reactance[3])
            return self._create_boundary(name, props, "Anisotropic Impedance")
        else:
            props["Resistance"] = str(resistance)
            props["Reactance"] = str(reactance)
            props["InfGroundPlane"] = is_infinite_ground
            return self._create_boundary(name, props, "Impedance")

    @pyaedt_function_handler(
        edge_signale="assignment", edge_gnd="reference", port_name="name", port_impedance="impedance"
    )
    def create_circuit_port_from_edges(
        self,
        assignment,
        reference,
        name="",
        impedance="50",
        renormalize=False,
        renorm_impedance="50",
        deembed=False,
    ):
        """Create a circuit port from two edges.

        The integration line is from edge 2 to edge 1.

        .. deprecated:: 0.6.70
        Use :func:`circuit_port` method instead.

        Parameters
        ----------
        assignment : int
            Edge ID of the signal.
        reference : int
            Edge ID of the ground.
        name : str, optional
            Name of the port. The default is ``""``.
        impedance : int, str, or float, optional
            Impedance. The default is ``"50"``. You can also
            enter a string that looks like this: ``"50+1i*55"``.
        renormalize : bool, optional
            Whether to renormalize the mode. The default is ``False``.
            This parameter is ignored for a driven terminal.
        renorm_impedance :  str, optional
            Impedance. The default is ``50``.
        deembed : bool, optional
            Whether to deembed the port. The default is ``False``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Boundary object.

        References
        ----------
        >>> oModule.AssignCircuitPort

        Examples
        --------

        Create two rectangles in the XY plane.
        Select the first edge of each rectangle created previously.
        Create a circuit port from the first edge of the first rectangle
        toward the first edge of the second rectangle.

        >>> plane = hfss.PLANE.XY
        >>> rectangle1 = hfss.modeler.create_rectangle(plane, [10, 10, 10], [10, 10],
        ...                                            name="rectangle1_for_port")
        >>> edges1 = hfss.modeler.get_object_edges(rectangle1.id)
        >>> first_edge = edges1[0]
        >>> rectangle2 = hfss.modeler.create_rectangle(plane, [30, 10, 10], [10, 10],
        ...                                            name="rectangle2_for_port")
        >>> edges2 = hfss.modeler.get_object_edges(rectangle2.id)
        >>> second_edge = edges2[0]
        >>> hfss.solution_type = "Modal"
        >>> hfss.create_circuit_port_from_edges(first_edge,second_edge,
        ...                                     name="PortExample",
        ...                                     impedance=50.1,
        ...                                     renormalize=False,
        ...                                     renorm_impedance="50")
        'PortExample'

        """
        warnings.warn("Use :func:`circuit_port` method instead.", DeprecationWarning)
        return self.circuit_port(
            assignment=assignment,
            reference=reference,
            port_location=0,
            impedance=impedance,
            name=name,
            renormalize=renormalize,
            renorm_impedance=renorm_impedance,
            deembed=deembed,
        )

    @pyaedt_function_handler(excitations="assignment")
    def edit_sources(
        self,
        assignment,
        include_port_post_processing=True,
        max_available_power=None,
        use_incident_voltage=False,
        eigenmode_stored_energy=True,
    ):
        """Set up the power loaded for HFSS postprocessing in multiple sources simultaneously.

        Parameters
        ----------
        assignment : dict
            Dictionary of input sources to modify module and phase.
            Dictionary values can be:
            - 1 value to setup 0deg as default
            - 2 values tuple or list (magnitude and phase) or
            - 3 values (magnitude, phase, and termination flag) for Terminal solution in case of incident voltage usage.
        include_port_post_processing : bool, optional
            Include port post-processing effects. The default is ``True``.
        max_available_power : str, optional
            System power for gain calculations.
            The default is ``None``, in which case maximum available power is applied.
        use_incident_voltage : bool, optional
            Use incident voltage definition. The default is ``False``.
            This argument applies only to the Terminal solution type.
        eigenmode_stored_energy : bool, optional
            Use stored energy definition. The default is ``True``.
            This argument applies only to the Eigenmode solution type.

        Returns
        -------
        bool

        Examples
        --------
        >>> sources = {"Port1:1": ("0W", "0deg"), "Port2:1": ("1W", "90deg")}
        >>> hfss.edit_sources(sources, include_port_post_processing=True)

        >>> sources = {"Box2_T1": ("0V", "0deg", True), "Box1_T1": ("1V", "90deg")}
        >>> hfss.edit_sources(sources,max_available_power="2W", use_incident_voltage=True)

        >>> aedtapp = add_app(solution_type="Eigenmode")
        >>> _ = aedtapp.modeler.create_box([0, 0, 0], [10, 20, 20])
        >>> setup = aedtapp.create_setup()
        >>> setup.props["NumModes"] = 2
        >>> sources = {"1": "1Joules", "2": "0Joules"}
        >>> aedtapp.edit_sources(sources, eigenmode_stored_energy=True)
        >>> sources = {"1": ("0V/M", "0deg"), "2": ("2V/M", "90deg")}
        >>> aedtapp.edit_sources(sources, eigenmode_stored_energy=False)
        """
        if self.solution_type != "Eigenmode":
            data = {i: ("0W", "0deg", False) for i in self.excitations}
            for key, value in assignment.items():
                data[key] = value
            setting = []
            for key, vals in data.items():
                if isinstance(vals, str):
                    power = vals
                    phase = "0deg"
                else:
                    power = vals[0]
                    if len(vals) == 1:
                        phase = "0deg"
                    else:
                        phase = vals[1]
                if isinstance(vals, (list, tuple)) and len(vals) == 3:
                    terminated = vals[2]
                else:
                    terminated = False
                if use_incident_voltage and self.solution_type == "Terminal":
                    setting.append(["Name:=", key, "Terminated:=", terminated, "Magnitude:=", power, "Phase:=", phase])
                else:
                    setting.append(["Name:=", key, "Magnitude:=", power, "Phase:=", phase])
            argument = []
            if self.solution_type == "Terminal":
                argument.extend(["UseIncidentVoltage:=", use_incident_voltage])

            argument.extend(
                [
                    "IncludePortPostProcessing:=",
                    include_port_post_processing,
                    "SpecifySystemPower:=",
                    True if max_available_power else False,
                ]
            )

            if max_available_power:
                argument.append("Incident Power:=")
                argument.append(max_available_power)
        else:
            eigenmode_type_definition = "EigenStoredEnergy" if eigenmode_stored_energy else "EigenPeakElectricField"
            argument = ["FieldType:=", eigenmode_type_definition]
            power = []
            phase = []
            for _, value in assignment.items():
                if eigenmode_stored_energy:
                    power.append(value)
                else:
                    if isinstance(value, (list, tuple)):
                        power.append(value[0])
                        phase.append(value[1])
                    elif isinstance(value, str):
                        power.append(value)
                        phase.append("0deg")
            if eigenmode_stored_energy:
                setting = [["Name:=", "Modes", "Magnitudes:=", power]]
            else:
                setting = [["Name:=", "Modes", "Magnitudes:=", power, "Phases:=", phase]]

        args = [argument]
        args.extend(setting)
        self.osolution.EditSources(args)
        return True

    @pyaedt_function_handler(portandmode="assignment", powerin="power")
    def edit_source(self, assignment=None, power="1W", phase="0deg"):
        """Set up the power loaded for HFSS postprocessing.

        .. deprecated:: 0.11.2
           Use :func:`edit_sources` method instead.

        Parameters
        ----------
        assignment : str, optional
            Port name and mode. For example, ``"Port1:1"``.
            The port name must be defined if the solution type is other than Eigenmodal. This parameter
            is ignored if the solution type is Eigenmodal.
        power : str, optional
            Power in watts (W) or the project variable to put as stored energy in the project.
            The default is ``"1W"``.
        phase : str, optional
            Phase of the excitation. The default is ``"0deg"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.EditSources

        Examples
        --------

        Create a circle sheet and use it to create a wave port.
        Set up the thermal power for this wave port.

        >>> sheet = hfss.modeler.create_circle(hfss.PLANE.YZ,
        ...                                    [-20, 0, 0], 10,
        ...                                    name="sheet_for_source")
        >>> hfss.solution_type = "Modal"
        >>> wave_port = hfss.create_wave_port_from_sheet(sheet,5,hfss.AxisDir.XNeg,40,2,"SheetWavePort",True)
        >>> hfss.edit_source("SheetWavePort" + ":1","10W")
        PyAEDT INFO: Setting up power to "SheetWavePort:1" = 10W
        True

        """
        warnings.warn("`edit_sources` is deprecated. Use `edit_sources` method instead.", DeprecationWarning)

        if self.solution_type != SOLUTIONS.Hfss.EigenMode:
            if assignment is None:
                raise AEDTRuntimeError(f"Port and mode must be defined for solution type {self.solution_type}")
            self.logger.info(f'Setting up power to "{assignment}" = {power}')
            source = {assignment: (power, phase)}
            self.edit_sources(
                assignment=source,
                include_port_post_processing=True,
                max_available_power=None,
                eigenmode_stored_energy=True,
            )

        else:
            self.logger.info(f"Setting up power to Eigenmode = {power}")
            source = {"1": power}
            self.edit_sources(assignment=source, eigenmode_stored_energy=True)
        return True

    @pyaedt_function_handler(portandmode="assignment", file_name="input_file")
    def edit_source_from_file(
        self,
        input_file,
        assignment=None,
        is_time_domain=True,
        x_scale=1,
        y_scale=1,
        impedance=50,
        data_format="Power",
        encoding="utf-8",
        window="hamming",
    ):
        """Edit a source from file data.

        File data is a CSV containing either frequency data or time domain data that will be converted through FFT.

        Parameters
        ----------
        input_file : str
            Full name of the input file. If ``assignment`` is ``None``, it loads directly the file, in this case
            the file must have AEDT format.
        assignment : str, optional
            Port name and mode. For example, ``"Port1:1"``.
            The port name must be defined if the solution type is other than Eigenmodal.
        is_time_domain : bool, optional
            Whether the input data is time-based or frequency-based. Frequency based data are Mag/Phase (deg).
        x_scale : float, optional
            Scaling factor for the x axis. This argument is ignored if the algorithm
             identifies the format from the file header.
        y_scale : float, optional
            Scaling factor for the y axis. This argument is ignored if the algorithm
             identifies the format from the file header.
        impedance : float, optional
            Excitation impedance. Default is `50`.
        data_format : str, optional
            Data format. Options are ``"Current"``, ``"Power"``, and ``"Voltage"``. This
            argument is ignored if the algoritmm identifies the format from the
            file header.
        encoding : str, optional
            CSV file encoding.
        window : str, optional
            Fft window. Options are ``"hamming"``, ``"hanning"``, ``"blackman"``, ``"bartlett"`` or ``None``.

        Returns
        -------
        bool
        """
        if not assignment:
            self.osolution.LoadSourceWeights(input_file)
            return True

        def find_scale(data, header_line):
            for td in data.keys():
                if td in header_line:
                    return data[td]
            return None

        with open(input_file, "r") as f:
            header = f.readlines()[0]
            time_data = {"[ps]": 1e-12, "[ns]": 1e-9, "[us]": 1e-6, "[ms]": 1e-3, "[s]": 1}
            curva_data_V = {
                "[nV]": 1e-9,
                "[pV]": 1e-12,
                "[uV]": 1e-6,
                "[mV]": 1e-3,
                "[V]": 1,
                "[kV]": 1e3,
            }
            curva_data_W = {
                "[nW]": 1e-9,
                "[pW]": 1e-12,
                "[uW]": 1e-6,
                "[mW]": 1e-3,
                "[W]": 1,
                "[kW]": 1e3,
            }
            curva_data_A = {
                "[nA]": 1e-9,
                "[pA]": 1e-12,
                "[uA]": 1e-6,
                "[mA]": 1e-3,
                "[A]": 1,
                "[kA]": 1e3,
            }
            scale = find_scale(time_data, header)
            x_scale = scale if scale else x_scale
            scale = find_scale(curva_data_V, header)
            if scale:
                y_scale = scale
                data_format = "Voltage"
            else:
                scale = find_scale(curva_data_W, header)
                if scale:
                    y_scale = scale
                    data_format = "Power"
                else:
                    scale = find_scale(curva_data_A, header)
                    if scale:
                        y_scale = scale
                        data_format = "Current"
        if self.solution_type == "Modal":
            out = "Power"
        else:
            out = "Voltage"
        freq, mag, phase = parse_excitation_file(
            input_file=input_file,
            is_time_domain=is_time_domain,
            x_scale=x_scale,
            y_scale=y_scale,
            impedance=impedance,
            data_format=data_format,
            encoding=encoding,
            out_mag=out,
            window=window,
        )
        ds_name_mag = "ds_" + assignment.replace(":", "_mode_") + "_Mag"
        ds_name_phase = "ds_" + assignment.replace(":", "_mode_") + "_Angle"
        if self.dataset_exists(ds_name_mag, False):
            self.design_datasets[ds_name_mag].x = freq
            self.design_datasets[ds_name_mag].y = mag
            self.design_datasets[ds_name_mag].update()
        else:
            self.create_dataset1d_design(ds_name_mag, freq, mag, x_unit="Hz")
        if self.dataset_exists(ds_name_phase, False):
            self.design_datasets[ds_name_phase].x = freq
            self.design_datasets[ds_name_phase].y = phase
            self.design_datasets[ds_name_phase].update()

        else:
            self.create_dataset1d_design(ds_name_phase, freq, phase, x_unit="Hz", y_unit="deg")
        self.osolution.EditSources(
            [
                ["IncludePortPostProcessing:=", True, "SpecifySystemPower:=", False],
                [
                    "Name:=",
                    assignment,
                    "Magnitude:=",
                    f"pwl({ds_name_mag}, Freq)",
                    "Phase:=",
                    f"pwl({ds_name_phase}, Freq)",
                ],
            ]
        )
        self.logger.info("Source Excitation updated with Dataset.")
        return True

    @pyaedt_function_handler(file_name="input_file")
    def edit_sources_from_file(self, input_file):  # pragma: no cover
        """Update all sources from a CSV file.

        .. deprecated:: 0.11.2
           Use :func:`edit_source_from_file` method instead.

        Parameters
        ----------
        input_file : str
            File name.

        Returns
        -------
        bool
        """
        warnings.warn(
            "`edit_source_from_file` is deprecated. Use `edit_source_from_file` method instead.", DeprecationWarning
        )
        self.edit_source_from_file(input_file=input_file)
        return True

    @pyaedt_function_handler(
        inputlist="assignment", internalExtr="extrude_internally", internalvalue="internal_extrusion"
    )
    def thicken_port_sheets(self, assignment, value, extrude_internally=True, internal_extrusion=1):
        """Create thickened sheets over a list of input port sheets.

        This method is built to work with the output of ``modeler.find_port_faces``.

        Parameters
        ----------
        assignment : list
            List of the sheets to thicken.
        value :
            Value in millimeters for thickening the faces.
        extrude_internally : bool, optional
            Whether to extrude the sheets internally (going into the model).
            The default is ``True``.
        internal_extrusion : int, optional
            Value in millimeters for thickening the sheets internally if ``internalExtr=True``.
            The default is ``1``.

        Returns
        -------
        Dict
            For each input sheet, returns the port IDs where thickened sheets were created
            if the name contains the word "Vacuum".

        References
        ----------
        >>> oEditor.ThickenSheet

        Examples
        --------

        Create a circle sheet and use it to create a wave port.
        Set the thickness of this circle sheet to ``"2 mm"``.

        >>> sheet_for_thickness = hfss.modeler.create_circle(hfss.PLANE.YZ,
        ...                                                  [60, 60, 60], 10,
        ...                                                  name="SheetForThickness")
        >>> port_for_thickness = hfss.create_wave_port_from_sheet(sheet_for_thickness,5,
        ...                                                       hfss.AxisDir.XNeg,
        ...                                                       40,
        ...                                                       2,
        ...                                                       "WavePortForThickness",True)
        >>> hfss.thicken_port_sheets(["SheetForThickness"],2)
        PyAEDT INFO: done
        {}

        """

        tol = 1e-6
        ports_ID = {}
        aedt_bounding_box = self.modeler.get_model_bounding_box()
        aedt_bounding_dim = self.modeler.get_bounding_dimension()
        directions = {}
        for el in assignment:
            objID = self.modeler.oeditor.GetFaceIDs(el)
            face_center = self.modeler.oeditor.GetFaceCenter(int(objID[0]))
            direction_found = False
            thickness = min(aedt_bounding_dim) / 2
            while not direction_found:
                self.modeler.oeditor.ThickenSheet(
                    ["NAME:Selections", "Selections:=", el, "NewPartsModelFlag:=", "Model"],
                    ["NAME:SheetThickenParameters", "Thickness:=", str(thickness) + "mm", "BothSides:=", False],
                )

                aedt_bounding_box2 = self.modeler.get_model_bounding_box()
                self._odesign.Undo()
                if aedt_bounding_box != aedt_bounding_box2:
                    directions[el] = "External"
                    direction_found = True
                self.modeler.oeditor.ThickenSheet(
                    ["NAME:Selections", "Selections:=", el, "NewPartsModelFlag:=", "Model"],
                    ["NAME:SheetThickenParameters", "Thickness:=", "-" + str(thickness) + "mm", "BothSides:=", False],
                )

                aedt_bounding_box2 = self.modeler.get_model_bounding_box()

                self._odesign.Undo()

                if aedt_bounding_box != aedt_bounding_box2:
                    directions[el] = "Internal"
                    direction_found = True
                else:
                    thickness = thickness + min(aedt_bounding_dim) / 2
        for el in assignment:
            objID = self.modeler.oeditor.GetFaceIDs(el)
            maxarea = 0
            for f in objID:
                faceArea = self.modeler.get_face_area(int(f))
                if faceArea > maxarea:
                    maxarea = faceArea
                    face_center = self.modeler.oeditor.GetFaceCenter(int(f))
            if directions[el] == "Internal":
                self.modeler.oeditor.ThickenSheet(
                    ["NAME:Selections", "Selections:=", el, "NewPartsModelFlag:=", "Model"],
                    ["NAME:SheetThickenParameters", "Thickness:=", "-" + str(value) + "mm", "BothSides:=", False],
                )
            else:
                self.modeler.oeditor.ThickenSheet(
                    ["NAME:Selections", "Selections:=", el, "NewPartsModelFlag:=", "Model"],
                    ["NAME:SheetThickenParameters", "Thickness:=", str(value) + "mm", "BothSides:=", False],
                )
            if "Vacuum" in el:
                newfaces = self.modeler.oeditor.GetFaceIDs(el)
                for f in newfaces:
                    try:
                        fc2 = self.modeler.oeditor.GetFaceCenter(f)
                        fc2 = [float(i) for i in fc2]
                        fa2 = self.modeler.get_face_area(int(f))
                        faceoriginal = [float(i) for i in face_center]
                        if abs(fa2 - maxarea) < tol**2 and (
                            abs(faceoriginal[2] - fc2[2]) > tol
                            or abs(faceoriginal[1] - fc2[1]) > tol
                            or abs(faceoriginal[0] - fc2[0]) > tol
                        ):
                            ports_ID[el] = int(f)
                    except Exception:
                        self.logger.debug(f"Failed to handle face {f} when creating thickened sheets")
            if extrude_internally:
                objID2 = self.modeler.oeditor.GetFaceIDs(el)
                for fid in objID2:
                    try:
                        face_center2 = self.modeler.oeditor.GetFaceCenter(int(fid))
                        if face_center2 == face_center:
                            self.modeler.oeditor.MoveFaces(
                                ["NAME:Selections", "Selections:=", el, "NewPartsModelFlag:=", "Model"],
                                [
                                    "NAME:Parameters",
                                    [
                                        "NAME:MoveFacesParameters",
                                        "MoveAlongNormalFlag:=",
                                        True,
                                        "OffsetDistance:=",
                                        str(internal_extrusion) + "mm",
                                        "MoveVectorX:=",
                                        "0mm",
                                        "MoveVectorY:=",
                                        "0mm",
                                        "MoveVectorZ:=",
                                        "0mm",
                                        "FacesToMove:=",
                                        [int(fid)],
                                    ],
                                ],
                            )
                    except Exception:
                        self.logger.info("done")
        return ports_ID

    @pyaedt_function_handler(dname="design", outputdir="output_dir")
    def validate_full_design(self, design=None, output_dir=None, ports=None):
        """Validate a design based on an expected value and save information to the log file.

        Parameters
        ----------
        design : str,  optional
            Name of the design to validate. The default is ``None``, in which case
            the current design is used.
        output_dir : str, optional
            Directory to save the log file to. The default is ``None``,
            in which case the current project path is used.
        ports : int, optional
            Number of excitations (sum of modes) that is expected. The default is ``None``.

        Returns
        -------
        list of str
            List of all the validation information for later use.
        bool
            ``True`` if the validation was successful, ``False`` otherwise.

        References
        ----------
        >>> oDesign.ValidateDesign

        Examples
        --------
        Validate the current design and save the log file in the current project directory.

        >>> validation = hfss.validate_full_design()
        PyAEDT INFO: Design Validation Checks
        >>> validation[1]
        False
        """
        self.logger.info("Design validation checks.")
        validation_ok = True
        val_list = []
        if not design:
            design = self.design_name
        if not output_dir:
            output_dir = self.working_directory
        pname = self.project_name
        validation_log_file = os.path.join(output_dir, pname + "_" + design + "_validation.log")

        # Desktop Messages
        msg = "Desktop messages:"
        val_list.append(msg)
        temp_msg = list(self._desktop.GetMessages(pname, design, 0))
        if temp_msg:
            temp2_msg = [i.strip("Project: " + pname + ", Design: " + design + ", ").strip("\r\n") for i in temp_msg]
            val_list.extend(temp2_msg)

        # Run design validation and write out the lines to the log.
        temp_dir = tempfile.gettempdir()
        temp_val_file = os.path.join(temp_dir, "val_temp.log")
        simple_val_return = self.validate_simple(temp_val_file)
        if simple_val_return == 1:
            msg = "Design validation check PASSED."
        elif simple_val_return == 0:
            msg = "Design validation check ERROR."
            validation_ok = False
        val_list.append(msg)
        msg = "Design validation messages:"
        val_list.append(msg)
        if os.path.isfile(temp_val_file) or settings.remote_rpc_session:
            with open_file(temp_val_file, "r") as df:
                temp = df.read().splitlines()
                val_list.extend(temp)
            os.remove(temp_val_file)
        else:
            msg = "** No design validation file is found. **"
            self.logger.info(msg)
            val_list.append(msg)
        msg = "** End of design validation messages. **"
        val_list.append(msg)

        # Find the excitations and check or list them out
        msg = "Excitations check:"
        val_list.append(msg)
        if self.solution_type != "Eigenmode":
            detected_excitations = self.excitations
            if ports:
                if ports != len(detected_excitations):
                    msg = "** Port number error. Check the model. **"
                    self.logger.error(msg)
                    val_list.append(msg)
                    validation_ok = False
                else:
                    msg1 = "Solution type: " + str(self.solution_type)
                    msg2 = "Ports Requested: " + str(ports)
                    msg3 = "Defined excitations number: " + str(len(detected_excitations))
                    msg4 = "Defined excitations names: " + str(detected_excitations)
                    val_list.append(msg1)
                    val_list.append(msg2)
                    val_list.append(msg3)
                    val_list.append(msg4)
        else:
            msg = "Eigen model is detected. No excitatons are defined."
            self.logger.info(msg)
            val_list.append(msg)

        # Find the number of analysis setups and output the info.
        msg = "Analysis setup messages:"
        val_list.append(msg)
        setups = self.oanalysis.GetSetups()
        if setups:
            setups = list(setups)
            msg = "Detected setup and sweep: "
            val_list.append(msg)
            for setup in setups:
                msg = str(setup)
                val_list.append(msg)
                if self.solution_type.lower() != "eigenmode":
                    sweepsname = self.oanalysis.GetSweeps(setup)
                    if sweepsname:
                        for sw in sweepsname:
                            msg = " |__ " + sw
                            val_list.append(msg)
        else:
            msg = "No setup is detected."
            val_list.append(msg)

        with open_file(validation_log_file, "w") as f:
            for item in val_list:
                f.write("%s\n" % item)
        return val_list, validation_ok  # Return all the information in a list for later use.

    @pyaedt_function_handler(plot_name="plot", sweep_name="sweep", port_names="ports", port_excited="ports_excited")
    def create_scattering(
        self, plot="S Parameter Plot Nominal", sweep=None, ports=None, ports_excited=None, variations=None
    ):
        """Create an S-parameter report.

        Parameters
        ----------
        plot : str, optional
             Name of the plot. The default is ``"S Parameter Plot Nominal"``.
        sweep : str, optional
             Name of the sweep. The default is ``None``.
        ports : list, optional
             List of port names. The first index, i, in S[i,j].
             The default is ``None``.
        ports_excited : list or str, optional
             List of port names. The seconds index, j in S[i,j].
             The default is ``None``.
        variations : str, optional
             The default is ``None``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.CreateReport

        Examples
        --------

        Create an S-parameter plot named ``"S Parameter Plot Nominal"`` for a 3-port network.
        plotting S11, S21, S31.  The port names are ``P1``, ``P2``, and ``P3``.

        >>> hfss.create_scattering(ports=["P1", "P2", "P3"],ports_excited=["P1", "P1", "P1"])
        True

        """

        solution_data = "Standard"
        if "Modal" in self.solution_type:
            solution_data = "Modal Solution Data"
        elif "Terminal" in self.solution_type:
            solution_data = "Terminal Solution Data"
        if not ports:
            ports = self.excitations
        if not ports_excited:
            ports_excited = ports
        traces = ["dB(S(" + p + "," + q + "))" for p, q in zip(list(ports), list(ports_excited))]
        return self.post.create_report(
            traces, sweep, variations=variations, report_category=solution_data, plot_name=plot
        )

    @pyaedt_function_handler(outputlist="output", setupname="setup", plotname="name", Xaxis="x_axis")
    def create_qfactor_report(self, project_dir, output, setup, name, x_axis="X"):
        """Export a CSV file of the EigenQ plot.

        Parameters
        ----------
        project_dir : str
            Directory to export the CSV file to.
        output : list
            Output quantity, which in this case is the Q-factor.
        setup : str
            Name of the setup to generate the report from.
        name : str
            Name of the plot.
        x_axis : str, optional
            Value for the X axis. The default is ``"X"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.CreateReport

        """
        npath = project_dir

        # Setup arguments list for createReport function
        args = [x_axis + ":=", ["All"]]
        args2 = ["X Component:=", x_axis, "Y Component:=", output]

        self.post.post_oreport_setup.CreateReport(
            name, "Eigenmode Parameters", "Rectangular Plot", setup + " : LastAdaptive", [], args, args2, []
        )
        return True

    @pyaedt_function_handler(obh_names="assignment", boundary_name="name")
    def assign_radiation_boundary_to_objects(self, assignment, name=None):
        """Assign a radiation boundary to one or more objects (usually airbox objects).

        Parameters
        ----------
        assignment : str or list or int or :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
            One or more object names or IDs.
        name : str, optional
            Name of the boundary. The default is ``None``, in which case a name is automatically assigned.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Boundary object.

        References
        ----------
        >>> oModule.AssignRadiation

        Examples
        --------

        Create a box and assign a radiation boundary to it.

        >>> radiation_box = hfss.modeler.create_box([0, -200, -200],[200, 200, 200],name="Radiation_box")
        >>> radiation = hfss.assign_radiation_boundary_to_objects("Radiation_box")
        >>> type(radiation)
        <class 'from ansys.aedt.core.modules.boundary.common.BoundaryObject'>

        """

        object_list = self.modeler.convert_to_selections(assignment, return_list=True)
        if name:
            rad_name = name
        else:
            rad_name = generate_unique_name("Rad_")
        return self.create_boundary(self.BoundaryType.Radiation, object_list, rad_name)

    @pyaedt_function_handler(obj_names="assignment", boundary_name="name")
    def assign_hybrid_region(self, assignment, name=None, hybrid_region="SBR+"):
        """Assign a hybrid region to one or more objects.

        Parameters
        ----------
        assignment : str or list or int or :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
            One or more object names or IDs.
        name : str, optional
            Name of the boundary. The default is ``None``, in which case a name is automatically assigned.
        hybrid_region : str, optional
            Hybrid region to assign. The default is `"SBR+"``. Options are ``"IE"``, ``"PO"``
            and ``"SBR+"``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Boundary object.

        References
        ----------
        >>> oModule.AssignHybridRegion

        Examples
        --------

        Create a box and assign a hybrid boundary to it.

        >>> box = hfss.modeler.create_box([0, -200, -200],[200, 200, 200],name="Radiation_box")
        >>> sbr_box = hfss.assign_hybrid_region("Radiation_box")
        >>> type(sbr_box)
        <class 'from ansys.aedt.core.modules.boundary.common.BoundaryObject'>

        """

        object_list = self.modeler.convert_to_selections(assignment, return_list=True)
        if name:
            region_name = name
        else:
            region_name = generate_unique_name("Hybrid_")
        bound = self.create_boundary(self.BoundaryType.Hybrid, object_list, region_name)
        if hybrid_region != "SBR+":
            bound.props["Type"] = hybrid_region
        return bound

    @pyaedt_function_handler(obj_names="assignment", boundary_name="name")
    def assign_febi(self, assignment, name=None):
        """Assign an FE-BI region to one or more objects.

        Parameters
        ----------
        assignment : str or list or int or :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
            One or more object names or IDs.
        name : str, optional
            Name of the boundary. The default is ``None``, in which case a name is automatically assigned.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Boundary object.

        References
        ----------
        >>> oModule.AssignFEBI

        Examples
        --------

        Create a box and assign an FE-BI boundary to it.

        >>> box = hfss.modeler.create_box([0, -200, -200],[200, 200, 200],name="Radiation_box")
        >>> febi_box = hfss.assign_febi("Radiation_box")
        >>> type(febi_box)
        <class 'from ansys.aedt.core.modules.boundary.common.BoundaryObject'>

        """

        object_list = self.modeler.convert_to_selections(assignment, return_list=True)
        if name:
            region_name = name
        else:
            region_name = generate_unique_name("FEBI_")
        bound = self.create_boundary(self.BoundaryType.FEBI, object_list, region_name)

        return bound

    @pyaedt_function_handler(faces_id="assignment", boundary_name="name")
    def assign_radiation_boundary_to_faces(self, assignment, name=None):
        """Assign a radiation boundary to one or more faces.

        Parameters
        ----------
        assignment :
            Face ID to assign the boundary condition to.
        name : str, optional
            Name of the boundary. The default is ``None``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Boundary object.

        References
        ----------
        >>> oModule.AssignRadiation

        Examples
        --------

        Create a box. Select the faces of this box and assign a radiation
        boundary to them.

        >>> radiation_box = hfss.modeler.create_box([0 , -100, 0],[200, 200, 200],name="RadiationForFaces")
        >>> ids = [i.id for i in hfss.modeler["RadiationForFaces"].faces]
        >>> radiation = hfss.assign_radiation_boundary_to_faces(ids)
        >>> type(radiation)
        <class 'from ansys.aedt.core.modules.boundary.common.BoundaryObject'>

        """
        faces_list = self.modeler.convert_to_selections(assignment, True)
        if name:
            rad_name = name
        else:
            rad_name = generate_unique_name("Rad_")
        return self.create_boundary(self.BoundaryType.Radiation, faces_list, rad_name)

    @pyaedt_function_handler()
    def _create_sbr_doppler_setup(
        self,
        setup_type,
        time_var,
        center_freq,
        resolution,
        period,
        velocity_resolution,
        min_velocity,
        max_velocity,
        ray_density_per_wavelength,
        max_bounces,
        setup_name,
        include_coupling_effects=False,
        doppler_ad_sampling_rate=20,
    ):
        setup1 = self.create_setup(setup_name, 4)
        setup1.auto_update = False
        setup1.props["IsSbrRangeDoppler"] = True
        del setup1.props["PTDUTDSimulationSettings"]
        del setup1.props["ComputeFarFields"]
        del setup1.props["Sweeps"]
        if setup_type == "ChirpIQ":
            setup1.props["SbrRangeDopplerWaveformType"] = "ChirpSeqFmcw"
            setup1.props["ChannelConfiguration"] = "IQChannels"
        elif setup_type == "ChirpI":
            setup1.props["SbrRangeDopplerWaveformType"] = "ChirpSeqFmcw"
            setup1.props["ChannelConfiguration"] = "IChannelOnly"
        else:
            setup1.props["SbrRangeDopplerWaveformType"] = setup_type
        setup1.props["SbrRangeDopplerTimeVariable"] = time_var
        setup1.props["SbrRangeDopplerCenterFreq"] = self.modeler._arg_with_dim(center_freq, "GHz")
        setup1.props["SbrRangeDopplerRangeResolution"] = self.modeler._arg_with_dim(resolution, "meter")
        setup1.props["SbrRangeDopplerRangePeriod"] = self.modeler._arg_with_dim(period, "meter")
        setup1.props["SbrRangeDopplerVelocityResolution"] = self.modeler._arg_with_dim(velocity_resolution, "m_per_sec")
        setup1.props["SbrRangeDopplerVelocityMin"] = self.modeler._arg_with_dim(min_velocity, "m_per_sec")
        setup1.props["SbrRangeDopplerVelocityMax"] = self.modeler._arg_with_dim(max_velocity, "m_per_sec")
        setup1.props["DopplerRayDensityPerWavelength"] = ray_density_per_wavelength
        setup1.props["MaxNumberOfBounces"] = max_bounces
        if setup_type != "PulseDoppler":
            setup1.props["IncludeRangeVelocityCouplingEffect"] = include_coupling_effects
            setup1.props["SbrRangeDopplerA/DSamplingRate"] = self.modeler._arg_with_dim(doppler_ad_sampling_rate, "MHz")
        setup1.update()
        setup1.auto_update = True
        return setup1

    @pyaedt_function_handler(setupname="setup")
    def _create_sbr_doppler_sweep(self, setup, time_var, tstart, tstop, tsweep, parametric_name):
        time_stop = self.modeler._arg_with_dim(tstop, "s")
        return self.parametrics.add(time_var, tstart, time_stop, tsweep, "LinearStep", setup, name=parametric_name)

    @pyaedt_function_handler(time_var="time_variable", setup_name="setup")
    def create_sbr_chirp_i_doppler_setup(
        self,
        time_variable=None,
        sweep_time_duration=0,
        center_freq=76.5,
        resolution=1,
        period=200,
        velocity_resolution=0.4,
        min_velocity=-20,
        max_velocity=20,
        ray_density_per_wavelength=0.2,
        max_bounces=5,
        include_coupling_effects=False,
        doppler_ad_sampling_rate=20,
        setup=None,
    ):
        """Create an SBR+ Chirp I setup.

        Parameters
        ----------
        time_variable : str, optional
            Name of the time variable. The default is ``None``, in which case
            a search for the first time variable is performed.
        sweep_time_duration : float, optional
            Duration for the sweep time. The default is ``0.`` If a value greater
            than ``0`` is specified, a parametric sweep is created.
        center_freq : float, optional
            Center frequency in gigahertz (GHz). The default is ``76.5``.
        resolution : float, optional
            Doppler resolution in meters (m). The default is ``1``.
        period : float, optional
            Period of analysis in meters (m). The default is ``200``.
        velocity_resolution : float, optional
            Doppler velocity resolution in meters per second (m/s). The default is ``0.4``.
        min_velocity : str, optional
            Minimum Doppler velocity in meters per second (m/s). The default is ``-20``.
        max_velocity : str, optional
            Maximum Doppler velocity in meters per second (m/s). The default is ``20``.
        ray_density_per_wavelength : float, optional
            Doppler ray density per wavelength. The default is ``0.2``.
        max_bounces : int, optional
            Maximum number of bounces. The default is ``5``.
        include_coupling_effects : float, optional
            Whether to include coupling effects. The default is ``False``.
        doppler_ad_sampling_rate : float, optional
            Doppler AD sampling rate to use if ``include_coupling_effects``
            is ``True``. The default is ``20``.
        setup : str, optional
            Name of the setup. The default is ``None``, in which case the active setup is used.

        Returns
        -------
        tuple
            The tuple contains: (:class:`ansys.aedt.core.modules.solve_setup.Setup`,
            :class:`ansys.aedt.core.modules.design_xploration.ParametericsSetups.Optimetrics`).

        References
        ----------
        >>> oModule.InsertSetup

        """
        if self.solution_type != "SBR+":
            raise AEDTRuntimeError("Method applies only to the SBR+ solution.")

        if not setup:
            setup = generate_unique_name("ChirpI")
            parametric_name = generate_unique_name("PulseSweep")
        else:
            parametric_name = generate_unique_name(setup)

        if not time_variable:
            for var_name, var in self.variable_manager.independent_variables.items():
                if var.unit_system == "Time":
                    time_variable = var_name
                    break
            if not time_variable:
                raise ValueError(
                    "No time variable is found. Set up or explicitly assign a time variable to the method."
                )
        setup = self._create_sbr_doppler_setup(
            "ChirpI",
            time_var=time_variable,
            center_freq=center_freq,
            resolution=resolution,
            period=period,
            velocity_resolution=velocity_resolution,
            min_velocity=min_velocity,
            max_velocity=max_velocity,
            ray_density_per_wavelength=ray_density_per_wavelength,
            max_bounces=max_bounces,
            include_coupling_effects=include_coupling_effects,
            doppler_ad_sampling_rate=doppler_ad_sampling_rate,
            setup_name=setup,
        )
        if sweep_time_duration > 0:
            sweeptime = math.ceil(300000000 / (2 * center_freq * 1000000000 * velocity_resolution) * 1000) / 1000
            sweep = self._create_sbr_doppler_sweep(
                setup.name, time_variable, 0, sweep_time_duration, sweeptime, parametric_name
            )
            return setup, sweep
        return setup, False

    @pyaedt_function_handler(time_var="time_variable", setup_name="setup")
    def create_sbr_chirp_iq_doppler_setup(
        self,
        time_variable=None,
        sweep_time_duration=0,
        center_freq=76.5,
        resolution=1,
        period=200,
        velocity_resolution=0.4,
        min_velocity=-20,
        max_velocity=20,
        ray_density_per_wavelength=0.2,
        max_bounces=5,
        include_coupling_effects=False,
        doppler_ad_sampling_rate=20,
        setup=None,
    ):
        """Create an SBR+ Chirp IQ setup.

        Parameters
        ----------
        time_variable : str, optional
            Name of the time variable. The default is ``None``, in which case
            a search for the first time variable is performed.
        sweep_time_duration : float, optional
            Duration of the sweep time. The default is ``0``. If a value greater
            than ``0`` is specified, a parametric sweep is created.
        center_freq : float, optional
            Center frequency in gighertz (GHz). The default is ``76.5``.
        resolution : float, optional
            Doppler resolution in meters (m). The default is ``1``.
        period : float, optional
            Period of analysis in meters (m). The default is ``200``.
        velocity_resolution : float, optional
            Doppler velocity resolution in meters per second (m/s). The default is ``0.4``.
        min_velocity : str, optional
            Minimum Doppler velocity in meters per second (m/s). The default is ``-20``.
        max_velocity : str, optional
            Maximum Doppler velocity in meters per second (m/s). The default is ``20``.
        ray_density_per_wavelength : float, optional
            Doppler ray density per wavelength. The default is ``0.2``.
        max_bounces : int, optional
            Maximum number of bounces. The default is ``5``.
        include_coupling_effects : float, optional
            Whether to include coupling effects. The default is ``False``.
        doppler_ad_sampling_rate : float, optional
            Doppler AD sampling rate to use if ``include_coupling_effects`` is
            ``True``. The default is ``20``.
        setup : str, optional
            Name of the setup. The default is ``None``, in which case the active
            setup is used.

        Returns
        -------
        tuple
            The tuple contains: (:class:`ansys.aedt.core.modules.solve_setup.Setup`,
            :class:`ansys.aedt.core.modules.design_xploration.ParametericsSetups.Optimetrics`).

        References
        ----------
        >>> oModule.InsertSetup
        """
        if self.solution_type != SOLUTIONS.Hfss.SBR:
            raise AEDTRuntimeError("Method applies only to the SBR+ solution.")

        if not setup:
            setup = generate_unique_name("ChirpIQ")
            parametric_name = generate_unique_name("PulseSweep")
        else:
            parametric_name = generate_unique_name(setup)
        if not time_variable:
            for var_name, var in self.variable_manager.independent_variables.items():
                if var.unit_system == "Time":
                    time_variable = var_name
                    break
            if not time_variable:
                raise ValueError("No Time Variable Found")
        setup = self._create_sbr_doppler_setup(
            "ChirpIQ",
            time_var=time_variable,
            center_freq=center_freq,
            resolution=resolution,
            period=period,
            velocity_resolution=velocity_resolution,
            min_velocity=min_velocity,
            max_velocity=max_velocity,
            ray_density_per_wavelength=ray_density_per_wavelength,
            max_bounces=max_bounces,
            include_coupling_effects=include_coupling_effects,
            doppler_ad_sampling_rate=doppler_ad_sampling_rate,
            setup_name=setup,
        )
        if sweep_time_duration > 0:
            sweeptime = math.ceil(300000000 / (2 * center_freq * 1000000000 * velocity_resolution) * 1000) / 1000
            sweep = self._create_sbr_doppler_sweep(
                setup.name, time_variable, 0, sweep_time_duration, sweeptime, parametric_name
            )
            return setup, sweep
        return setup, False

    @pyaedt_function_handler(time_var="time_variable", center_freq="frequency", setup_name="setup")
    def create_sbr_pulse_doppler_setup(
        self,
        time_variable=None,
        sweep_time_duration=0,
        frequency=76.5,
        resolution=1,
        period=200,
        velocity_resolution=0.4,
        min_velocity=-20,
        max_velocity=20,
        ray_density_per_wavelength=0.2,
        max_bounces=5,
        setup=None,
    ):
        """Create an SBR+ pulse Doppler setup.

        Parameters
        ----------
        time_variable : str, optional
            Name of the time variable. The default is ``None``, in which case
            a search for the first time variable is performed.
        sweep_time_duration : float, optional
            Duration of the sweep time. The default is ``0``. If a value greater
            than ``0`` is specified, a parametric sweep is created.
        frequency : float, optional
            Center frequency in gigahertz (GHz). The default is ``76.5``.
        resolution : float, optional
            Doppler resolution in meters (m). The default is ``1``.
        period : float, optional
            Period of analysis in meters (m). The default is ``200``.
        velocity_resolution : float, optional
            Doppler velocity resolution in meters per second (m/s).
            The default is ``0.4``.
        min_velocity : str, optional
            Minimum Doppler velocity in meters per second (m/s). The default
            is ``-20``.
        max_velocity : str, optional
            Maximum Doppler velocity in meters per second (m/s). The default
            is ``20``.
        ray_density_per_wavelength : float, optional
            Doppler ray density per wavelength. The default is ``0.2``.
        max_bounces : int, optional
            Maximum number of bounces. The default is ``5``.
        setup : str, optional
            Name of the setup. The default is ``None``, in which case the active
            setup is used.

        Returns
        -------
        tuple
            The tuple contains: (:class:`ansys.aedt.core.modules.solve_setup.Setup`,
            :class:`ansys.aedt.core.modules.design_xploration.ParametericsSetups.Optimetrics`).

        References
        ----------
        >>> oModule.InsertSetup
        """
        if self.solution_type != SOLUTIONS.Hfss.SBR:
            raise AEDTRuntimeError("Method Applies only to SBR+ Solution.")

        if not setup:
            setup = generate_unique_name("PulseSetup")
            parametric_name = generate_unique_name("PulseSweep")
        else:
            parametric_name = generate_unique_name(setup)

        if not time_variable:
            for var_name, var in self.variable_manager.independent_variables.items():
                if var.unit_system == "Time":
                    time_variable = var_name
                    break
            if not time_variable:
                raise ValueError("No Time Variable Found")
        setup = self._create_sbr_doppler_setup(
            "PulseDoppler",
            time_var=time_variable,
            center_freq=frequency,
            resolution=resolution,
            period=period,
            velocity_resolution=velocity_resolution,
            min_velocity=min_velocity,
            max_velocity=max_velocity,
            ray_density_per_wavelength=ray_density_per_wavelength,
            max_bounces=max_bounces,
            setup_name=setup,
        )
        if sweep_time_duration > 0:
            sweeptime = math.ceil(300000000 / (2 * frequency * 1000000000 * velocity_resolution) * 1000) / 1000
            sweep = self._create_sbr_doppler_sweep(
                setup.name, time_variable, 0, sweep_time_duration, sweeptime, parametric_name
            )
            return setup, sweep
        return setup, False

    @pyaedt_function_handler(radar_name="name")
    def create_sbr_radar_from_json(
        self, radar_file, name, offset=None, speed=0.0, use_relative_cs=False, relative_cs_name=None
    ):
        """Create an SBR+ radar setup from a JSON file.

        Example of input JSON file:

          .. code-block:: json

            {
                "name": "Example_1Tx_1Rx",
                "version": 1,
                "number_tx":"1",
                "number_rx":"1",
                "units":"mm",
                "antennas": {
                    "tx1": {
                        "antenna_type":"parametric",
                        "mode":"tx",
                        "offset":["0" ,"0" ,"0"],
                        "rotation_axis":null,
                        "rotation":null,
                        "beamwidth_elevation":"10deg",
                        "beamwidth_azimuth":"60deg",
                        "polarization":"Vertical"
                        },
                    "rx1": {
                        "antenna_type":"parametric",
                        "mode":"rx",
                        "offset":["0" ,"1.8" ,"0"],
                        "rotation_axis":null,
                        "rotation":null,
                        "beamwidth_elevation":"10deg",
                        "beamwidth_azimuth":"60deg",
                        "polarization":"Vertical"
                        }
                }
            }

        Parameters
        ----------
        radar_file : str
            Path to the directory with the radar file.
        name : str
            Name of the radar file.
        offset : list, optional
            Offset relative to the global coordinate system.
        speed : float, optional
            Radar movement speed relative to the global coordinate system if greater than ``0``.
        use_relative_cs : bool, optional
            Whether to use the relative coordinate system. The default is ``False``.
        relative_cs_name : str
            Name of the relative coordinate system to link the radar to.
            The default is ``None``, in which case the global coordinate system is used.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.actors.Radar`
            Radar  class object.

        References
        ----------
        AEDT API Commands.

        >>> oEditor.CreateRelativeCS
        >>> oModule.SetSBRTxRxSettings
        >>> oEditor.CreateGroup
        """
        from ansys.aedt.core.modeler.advanced_cad.actors import Radar

        if self.solution_type != SOLUTIONS.Hfss.SBR:
            raise AEDTRuntimeError("Method applies only to SBR+ solution.")

        if offset is None:
            offset = [0, 0, 0]

        self.modeler._initialize_multipart()
        use_motion = abs(speed) > 0.0
        r = Radar(
            radar_file,
            name=name,
            motion=use_motion,
            offset=offset,
            speed=speed,
            use_relative_cs=(use_relative_cs or use_motion),
            relative_cs_name=relative_cs_name,
        )
        r.insert(self, abs(speed) > 0)
        return r

    @pyaedt_function_handler()
    def insert_infinite_sphere(
        self,
        definition=INFINITE_SPHERE_TYPE.ThetaPhi,
        x_start=0,
        x_stop=180,
        x_step=10,
        y_start=0,
        y_stop=180,
        y_step=10,
        units="deg",
        custom_radiation_faces=None,
        custom_coordinate_system=None,
        use_slant_polarization=False,
        polarization_angle=45,
        name=None,
    ):
        """Create an infinite sphere.

        .. note::
           This method is not supported by HFSS ``EigenMode`` and ``CharacteristicMode`` solution types.

        Parameters
        ----------
        definition : str
            Coordinate definition type. The default is ``"Theta-Phi"``.
            It can be a ``ansys.aedt.core.generic.constants.INFINITE_SPHERE_TYPE`` enumerator value.
        x_start : float, str, optional
            First angle start value. The default is ``0``.
        x_stop : float, str, optional
            First angle stop value. The default is ``180``.
        x_step : float, str, optional
            First angle step value. The default is ``10``.
        y_start : float, str, optional
            Second angle start value. The default is ``0``.
        y_stop : float, str, optional
            Second angle stop value. The default is ``180``.
        y_step : float, str, optional
            Second angle step value. The default is ``10``.
        units : str
            Angle units. The default is ``"deg"``.
        custom_radiation_faces : str, optional
            List of radiation faces to use for far field computation. The default is ``None``.
        custom_coordinate_system : str, optional
            Local coordinate system to use for far field computation. The default is
            ``None``.
        use_slant_polarization : bool, optional
            Whether to use slant polarization. The default is ``False``.
        polarization_angle : float, str, optional
            Slant angle value. The default is ``45``.
        name : str, optional
            Name of the sphere. The default is ``None``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.hfss_boundary.FarFieldSetup`
        """
        if not self.oradfield:
            raise AEDTRuntimeError("Radiation Field not available in this solution.")
        if not name:
            name = generate_unique_name("Infinite")

        props = dict({"UseCustomRadiationSurface": custom_radiation_faces is not None})
        if custom_radiation_faces:
            props["CustomRadiationSurface"] = custom_radiation_faces
        else:
            props["CustomRadiationSurface"] = ""
        props["CSDefinition"] = definition
        if use_slant_polarization:
            props["Polarization"] = "Slant"
        else:
            props["Polarization"] = "Linear"
        props["SlantAngle"] = self.modeler._arg_with_dim(polarization_angle, units)

        if definition == "Theta-Phi":
            defs = ["ThetaStart", "ThetaStop", "ThetaStep", "PhiStart", "PhiStop", "PhiStep"]
        elif definition == "El Over Az":
            defs = ["AzimuthStart", "AzimuthStop", "AzimuthStep", "ElevationStart", "ElevationStop", "ElevationStep"]
        else:
            defs = ["ElevationStart", "ElevationStop", "ElevationStep", "AzimuthStart", "AzimuthStop", "AzimuthStep"]
        props[defs[0]] = self.modeler._arg_with_dim(x_start, units)
        props[defs[1]] = self.modeler._arg_with_dim(x_stop, units)
        props[defs[2]] = self.modeler._arg_with_dim(x_step, units)
        props[defs[3]] = self.modeler._arg_with_dim(y_start, units)
        props[defs[4]] = self.modeler._arg_with_dim(y_stop, units)
        props[defs[5]] = self.modeler._arg_with_dim(y_step, units)
        props["UseLocalCS"] = custom_coordinate_system is not None
        if custom_coordinate_system:
            props["CoordSystem"] = custom_coordinate_system
        else:
            props["CoordSystem"] = ""
        bound = FarFieldSetup(self, name, props, "FarFieldSphere", units)
        if bound.create():
            self.field_setups.append(bound)
            return bound
        return False

    @pyaedt_function_handler()
    def insert_near_field_sphere(
        self,
        radius=20,
        radius_units="mm",
        x_start=0,
        x_stop=180,
        x_step=10,
        y_start=0,
        y_stop=180,
        y_step=10,
        angle_units="deg",
        custom_radiation_faces=None,
        custom_coordinate_system=None,
        name=None,
    ):
        """Create a near field sphere.

        .. note::
           This method is not supported by HFSS ``EigenMode`` and ``CharacteristicMode`` solution types.

        Parameters
        ----------
        radius : float, str, optional
            Sphere radius. The default is ``20``.
        radius_units : str
            Radius units. The default is ``"mm"``.
        x_start : float, str, optional
            First angle start value. The default is ``0``.
        x_stop : float, str, optional
            First angle stop value. The default is ``180``.
        x_step : float, str, optional
            First angle step value. The default is ``10``.
        y_start : float, str, optional
            Second angle start value. The default is ``0``.
        y_stop : float, str, optional
            Second angle stop value. The default is ``180``.
        y_step : float, str, optional
            Second angle step value. The default is ``10``.
        angle_units : str
            Angle units. The default is ``"deg"``.
        custom_radiation_faces : str, optional
            List of radiation faces to use for far field computation. The default is ``None``.
        custom_coordinate_system : str, optional
            Local coordinate system to use for far field computation. The default is ``None``.
        name : str, optional
            Name of the sphere. The default is ``None``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.hfss_boundary.NearFieldSetup`
        """
        if not self.oradfield:
            raise AEDTRuntimeError("Radiation Field not available in this solution.")
        if not name:
            name = generate_unique_name("Sphere")

        props = dict({"UseCustomRadiationSurface": custom_radiation_faces is not None})
        if custom_radiation_faces:
            props["CustomRadiationSurface"] = custom_radiation_faces
        else:
            props["CustomRadiationSurface"] = ""

        props["Radius"] = self.modeler._arg_with_dim(radius, radius_units)

        defs = ["ThetaStart", "ThetaStop", "ThetaStep", "PhiStart", "PhiStop", "PhiStep"]
        props[defs[0]] = self.modeler._arg_with_dim(x_start, angle_units)
        props[defs[1]] = self.modeler._arg_with_dim(x_stop, angle_units)
        props[defs[2]] = self.modeler._arg_with_dim(x_step, angle_units)
        props[defs[3]] = self.modeler._arg_with_dim(y_start, angle_units)
        props[defs[4]] = self.modeler._arg_with_dim(y_stop, angle_units)
        props[defs[5]] = self.modeler._arg_with_dim(y_step, angle_units)
        props["UseLocalCS"] = custom_coordinate_system is not None
        if custom_coordinate_system:
            props["CoordSystem"] = custom_coordinate_system
        else:
            props["CoordSystem"] = ""
        bound = NearFieldSetup(self, name, props, "NearFieldSphere")
        if bound.create():
            self.field_setups.append(bound)
            return bound
        return False

    @pyaedt_function_handler()
    def insert_near_field_box(
        self,
        u_length=20,
        u_samples=21,
        v_length=20,
        v_samples=21,
        w_length=20,
        w_samples=21,
        units="mm",
        custom_radiation_faces=None,
        custom_coordinate_system=None,
        name=None,
    ):
        """Create a near field box.

        .. note::
           This method is not supported by HFSS ``EigenMode`` and ``CharacteristicMode`` solution types.

        Parameters
        ----------
        u_length : float, str, optional
            U axis length. The default is ``20``.
        u_samples : float, str, optional
            U axis samples. The default is ``21``.
        v_length : float, str, optional
            V axis length. The default is ``20``.
        v_samples : float, str, optional
            V axis samples. The default is ``21``.
        w_length : float, str, optional
            W axis length. The default is ``20``.
        w_samples : float, str, optional
            W axis samples. The default is ``21``.
        units : str
            Length units. The default is ``"mm"``.
        custom_radiation_faces : str, optional
            List of radiation faces to use for far field computation. The default is ``None``.
        custom_coordinate_system : str, optional
            Local coordinate system to use for far field computation. The default is ``None``.
        name : str, optional
            Name of the sphere. The default is ``None``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.hfss_boundary.NearFieldSetup`
        """
        if not self.oradfield:
            raise AEDTRuntimeError("Radiation Field not available in this solution.")
        if not name:
            name = generate_unique_name("Box")

        props = dict({"UseCustomRadiationSurface": custom_radiation_faces is not None})
        if custom_radiation_faces:
            props["CustomRadiationSurface"] = custom_radiation_faces
        else:
            props["CustomRadiationSurface"] = ""

        defs = ["U Size", "V Size", "W Size", "U Samples", "V Samples", "W Samples"]
        props[defs[0]] = self.modeler._arg_with_dim(u_length, units)
        props[defs[1]] = self.modeler._arg_with_dim(v_length, units)
        props[defs[2]] = self.modeler._arg_with_dim(w_length, units)
        props[defs[3]] = self.modeler._arg_with_dim(u_samples, units)
        props[defs[4]] = self.modeler._arg_with_dim(v_samples, units)
        props[defs[5]] = self.modeler._arg_with_dim(w_samples, units)

        if custom_coordinate_system:
            props["CoordSystem"] = custom_coordinate_system
        else:
            props["CoordSystem"] = "Global"
        bound = NearFieldSetup(self, name, props, "NearFieldBox")
        if bound.create():
            self.field_setups.append(bound)
            return bound
        return False

    @pyaedt_function_handler()
    def insert_near_field_rectangle(
        self,
        u_length=20,
        u_samples=21,
        v_length=20,
        v_samples=21,
        units="mm",
        custom_radiation_faces=None,
        custom_coordinate_system=None,
        name=None,
    ):
        """Create a near field rectangle.

        .. note::
           This method is not supported by HFSS ``EigenMode`` and ``CharacteristicMode`` solution types.

        Parameters
        ----------
        u_length : float, str, optional
            U axis length. The default is ``20``.
        u_samples : float, str, optional
            U axis samples. The default is ``21``.
        v_length : float, str, optional
            V axis length. The default is ``20``.
        v_samples : float, str, optional
            V axis samples. The default is ``21``.
        units : str
            Length units. The default is ``"mm"``.
        custom_radiation_faces : str, optional
            List of radiation faces to use for far field computation. The default is ``None``.
        custom_coordinate_system : str, optional
            Local coordinate system to use for far field computation. The default is ``None``.
        name : str, optional
            Name of the sphere. The default is ``None``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.hfss_boundary.NearFieldSetup`
        """
        if not self.oradfield:
            raise AEDTRuntimeError("Radiation Field not available in this solution.")
        if not name:
            name = generate_unique_name("Rectangle")

        props = dict({"UseCustomRadiationSurface": custom_radiation_faces is not None})
        if custom_radiation_faces:
            props["CustomRadiationSurface"] = custom_radiation_faces
        else:
            props["CustomRadiationSurface"] = ""

        defs = ["Length", "Width", "LengthSamples", "WidthSamples"]
        props[defs[0]] = self.modeler._arg_with_dim(u_length, units)
        props[defs[1]] = self.modeler._arg_with_dim(v_length, units)
        props[defs[2]] = u_samples
        props[defs[3]] = v_samples

        if custom_coordinate_system:
            props["CoordSystem"] = custom_coordinate_system
        else:
            props["CoordSystem"] = "Global"
        bound = NearFieldSetup(self, name, props, "NearFieldRectangle")
        if bound.create():
            self.field_setups.append(bound)
            return bound
        return False

    @pyaedt_function_handler(line="assignment")
    def insert_near_field_line(
        self,
        assignment,
        points=1000,
        custom_radiation_faces=None,
        name=None,
    ):
        """Create a near field line.

        .. note::
           This method is not supported by HFSS ``EigenMode`` and ``CharacteristicMode`` solution types.

        Parameters
        ----------
        assignment : str
            Polyline name.
        points : float, str, optional
            Number of points. The default value is ``1000``.
        custom_radiation_faces : str, optional
            List of radiation faces to use for far field computation. The default is ``None``.
        name : str, optional
            Name of the sphere. The default is ``None``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.hfss_boundary.NearFieldSetup`
        """
        if not self.oradfield:
            raise AEDTRuntimeError("Radiation Field not available in this solution.")
        if not name:
            name = generate_unique_name("Line")

        props = dict({"UseCustomRadiationSurface": custom_radiation_faces is not None})
        if custom_radiation_faces:
            props["CustomRadiationSurface"] = custom_radiation_faces
        else:
            props["CustomRadiationSurface"] = ""

        props["NumPts"] = points
        props["Line"] = assignment

        bound = NearFieldSetup(self, name, props, "NearFieldLine")
        if bound.create():
            self.field_setups.append(bound)
            return bound
        return False

    @pyaedt_function_handler()
    def set_sbr_current_sources_options(self, conformance=False, thin_sources=False, power_fraction=0.95):
        """Set SBR+ setup options for the current source.

        Parameters
        ----------
        conformance : bool, optional
            Whether to enable current source conformance. The default is ``False``.
        thin_sources : bool, optional
            Whether to enable thin sources. The default is ``False``.
        power_fraction : float or str, optional
            Power fraction to use if ``thin_sources=True``. The default is ``0.95``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.EditGlobalCurrentSourcesOption
        """
        if self.solution_type != SOLUTIONS.Hfss.SBR:
            raise AEDTRuntimeError("Method Applies only to SBR+ Solution.")

        current_conformance = "Disable"
        if conformance:
            current_conformance = "Enable"
        arg = [
            "NAME:CurrentSourceOption",
            "Current Source Conformance:=",
            current_conformance,
            "Thin Sources:=",
            thin_sources,
        ]
        if thin_sources:
            arg.append("Power Fraction:=")
            arg.append(str(power_fraction))
        self.oboundary.EditGlobalCurrentSourcesOption(arg)
        self.logger.info("SBR+ current source options correctly applied.")
        return True

    @pyaedt_function_handler(
        positive_terminal="assignment",
        negative_terminal="reference",
        common_name="common_mode",
        diff_name="differential_mode",
        common_ref="common_reference",
        diff_ref_z="differential_reference",
    )
    def set_differential_pair(
        self,
        assignment,
        reference,
        common_mode=None,
        differential_mode=None,
        common_reference=25,
        differential_reference=100,
        active=True,
        matched=False,
    ):
        """Add a differential pair definition.

        Differential pairs can be defined only in Terminal and Transient solution types.
        The differential pair is created from an existing port definition having at least two
        terminals.

        Parameters
        ----------
        assignment : str
            Name of the terminal to use as the positive terminal.
        reference : str
            Name of the terminal to use as the negative terminal.
        common_mode : str, optional
            Name for the common mode. The default is ``None``, in which case a unique name is assigned.
        differential_mode : str, optional
            Name for the differential mode. The default is ``None``, in which case a unique name is assigned.
        common_reference : float, optional
            Reference impedance for the common mode in ohms. The default is ``25``.
        differential_reference : float, optional
            Reference impedance for the differential mode in ohms. The default is ``100``.
        active : bool, optional
            Whether the differential pair is active. The default is ``True``.
        matched : bool, optional
            Whether the differential pair is matched. The default is ``False``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.EditDiffPairs
        """

        if self.solution_type not in (SOLUTIONS.Hfss.Transient, SOLUTIONS.Hfss.DrivenTerminal):  # pragma: no cover
            raise AEDTRuntimeError("Differential pairs can be defined only in Terminal and Transient solution types.")

        props = {}
        props["PosBoundary"] = assignment
        props["NegBoundary"] = reference
        if not common_mode:
            common_name = generate_unique_name("Comm")
        else:
            common_name = common_mode
        props["CommonName"] = common_name
        props["CommonRefZ"] = str(common_reference) + "ohm"
        if not differential_mode:
            differential_mode = generate_unique_name("Diff")
        props["DiffName"] = differential_mode
        props["DiffRefZ"] = str(differential_reference) + "ohm"
        props["IsActive"] = active
        props["UseMatched"] = matched
        arg = ["NAME:" + generate_unique_name("Pair")]
        _dict2arg(props, arg)

        arg2 = ["NAME:EditDiffPairs", arg]

        existing_pairs = self.oboundary.GetDiffPairs()
        # Native API returns Boolean values as strings. Therefore, map to Boolean.
        num_old_pairs = len(existing_pairs)
        if existing_pairs:
            for i, p in enumerate(existing_pairs):
                tmp_p = list(map(str_to_bool, p))
                tmp_p.insert(0, "NAME:Pair_" + str(i))
                arg2.append(tmp_p)

        self.oboundary.EditDiffPairs(arg2)

        if len(self.oboundary.GetDiffPairs()) == num_old_pairs + 1:
            return True
        else:
            return False

    @pyaedt_function_handler(array_name="name", json_file="input_data")
    def add_3d_component_array_from_json(self, input_data, name=None):
        """Add or edit a 3D component array from a JSON file, TOML file, or dictionary.

        The 3D component is placed in the layout if it is not present.

        Parameters
        ----------
        input_data : str, dict
            Full path to either the JSON file, TOML file, or the dictionary
            containing the array information.
        name : str, optional
             Name of the boundary to add or edit.

        Returns
        -------
        class:`ansys.aedt.core.modeler.cad.component_array.ComponentArray`

        Examples
        --------
        Add a 3D component array from a json file.
        Below is the content of a json file that will be used in the following code sample.

        >>> {
        >>> "primarylattice": "MyFirstLattice",
        >>> "secondarylattice": "MySecondLattice",
        >>> "useairobjects": true,
        >>> "rowdimension": 4,
        >>> "columndimension": 4,
        >>> "visible": true,
        >>> "showcellnumber": true,
        >>> "paddingcells": 0,
        >>> "referencecsid": 1,
        >>> "MyFirstCell": "path/to/firstcell.a3dcomp", # optional to insert 3d comp
        >>> "MySecondCell": "path/to/secondcell.a3dcomp",# optional to insert 3d comp
        >>> "MyThirdCell": "path/to/thirdcell.a3dcomp",  # optional to insert 3d comp
        >>> "cells": { "(1,1)": {
        >>>            "name" : "MyFirstCell",
        >>>            "color" : "(255,0,20)", #optional
        >>>            "active" : true, #optional
        >>>            "postprocessing" : true #optional
        >>>            "rotation" : 0.0  #optional
        >>>             },
        >>>            "(1,2)": {
        >>>            "name" : "MySecondCell",
        >>>            "rotation" : 90.0
        >>>             }
        >>>             # continue
        >>> }

        >>> from ansys.aedt.core import Hfss
        >>> from ansys.aedt.core.generic.general_methods import read_configuration_file
        >>> hfss_app = Hfss()
        >>> dict_in = read_configuration_file(r"path\\to\\json_file")
        >>> component_array = hfss_app.add_3d_component_array_from_json(dict_in)
        """
        self.hybrid = True
        if isinstance(input_data, dict):
            json_dict = input_data
        else:
            json_dict = read_configuration_file(input_data)
        if not name and self.omodelsetup.IsArrayDefined():
            name = self.omodelsetup.GetArrayNames()[0]
        elif not name:
            name = generate_unique_name("Array")

        cells_names = {}
        cells_color = {}
        cells_active = []
        cells_rotation = {}
        cells_post = {}
        for k, v in json_dict["cells"].items():
            if isinstance(k, (list, tuple)):
                k1 = str(list(k))
            else:
                k1 = str(list(ast.literal_eval(k)))
            if v["name"] in cells_names:
                cells_names[v["name"]].append(k1)
            else:
                def_names = self.oeditor.Get3DComponentDefinitionNames()
                if v["name"] not in def_names and v["name"][:-1] not in def_names and v["name"][:-2] not in def_names:
                    if v["name"] not in json_dict:
                        raise AEDTRuntimeError(
                            "3D component array is not present in design and not defined correctly in the JSON file."
                        )

                    geometryparams = self.get_components3d_vars(json_dict[v["name"]])

                    self.modeler.insert_3d_component(json_dict[v["name"]], geometryparams)
                cells_names[v["name"]] = [k1]
            if v.get("color", None):
                cells_color[v["name"]] = v.get("color", None)
            if str(v.get("rotation", "0.0")) in cells_rotation:
                cells_rotation[str(v.get("rotation", "0.0"))].append(k1)
            else:
                cells_rotation[str(v.get("rotation", "0.0"))] = [k1]
            if v.get("active", True) in cells_active:
                cells_active.append(k1)

            if v.get("postprocessing", False):
                cells_post[v["name"]] = k1

        primary_lattice = json_dict.get("primarylattice", None)
        secondary_lattice = json_dict.get("secondarylattice", None)
        if not primary_lattice:
            primary_lattice = self.omodelsetup.GetLatticeVectors()[0]
        if not secondary_lattice:
            secondary_lattice = self.omodelsetup.GetLatticeVectors()[1]

        args = [
            "NAME:" + name,
            "Name:=",
            name,
            "UseAirObjects:=",
            json_dict.get("useairobjects", True),
            "RowPrimaryBnd:=",
            primary_lattice,
            "ColumnPrimaryBnd:=",
            secondary_lattice,
            "RowDimension:=",
            json_dict.get("rowdimension", 4),
            "ColumnDimension:=",
            json_dict.get("columndimension", 4),
            "Visible:=",
            json_dict.get("visible", True),
            "ShowCellNumber:=",
            json_dict.get("showcellnumber", True),
            "RenderType:=",
            0,
            "Padding:=",
            json_dict.get("paddingcells", 0),
            "ReferenceCSID:=",
            json_dict.get("referencecsid", 1),
        ]

        cells = ["NAME:Cells"]
        for k, v in cells_names.items():
            cells.append(k + ":=")
            cells.append([", ".join(v)])
        rotations = ["NAME:Rotation"]
        for k, v in cells_rotation.items():
            if float(k) != 0.0:
                rotations.append(k + " deg:=")
                rotations.append([", ".join(v)])
        args.append(cells)
        args.append(rotations)
        args.append("Active:=")
        if cells_active:
            args.append(", ".join(cells_active))
        else:
            args.append("All")
        post = ["NAME:PostProcessingCells"]
        for k, v in cells_post.items():
            post.append(k + ":=")
            post.append(str(ast.literal_eval(v)))
        args.append(post)
        args.append("Colors:=")
        col = []
        for k, v in cells_color.items():
            col.append(k)
            col.append(str(v).replace(",", " "))
        args.append(col)

        if self.omodelsetup.IsArrayDefined():
            # Save project, because coordinate system information can not be obtained from AEDT API
            self.save_project()
            self.omodelsetup.EditArray(args)
        else:
            self.omodelsetup.AssignArray(args)
            # Save project, because coordinate system information can not be obtained from AEDT API
            self.save_project()
            self.component_array[name] = ComponentArray(self, name)
        self.component_array_names = [name]
        return self.component_array[name]

    @pyaedt_function_handler()
    def get_antenna_ffd_solution_data(
        self,
        frequencies=None,
        setup=None,
        sphere=None,
        variations=None,
        overwrite=True,
        link_to_hfss=True,
        export_touchstone=True,
        set_phase_center_per_port=True,
    ):  # pragma: no cover
        """Export the antenna parameters to Far Field Data (FFD) files and return an
        instance of the ``FfdSolutionDataExporter`` object.

        .. deprecated:: 0.9.8
        Use :func:`get_antenna_data` method instead.

        Parameters
        ----------
        frequencies : float, list, optional
            Frequency value or list of frequencies to compute far field data. The default is ``None,`` in which case
            all available frequencies are computed.
        setup : str, optional
            Name of the setup to use. The default is ``None,`` in which case ``nominal_adaptive`` is used.
        sphere : str, optional
            Infinite sphere to use. The default is ``None``, in which case an existing sphere is used or a new
            one is created.
        variations : dict, optional
            Variation dictionary. The default is ``None``, in which case the nominal variation is exported.
        overwrite : bool, optional
            Whether to overwrite FFD files. The default is ``True``.
        link_to_hfss : bool, optional
            Whether to return an instance of the
            :class:`ansys.aedt.core.generic.farfield_explorerf.FfdSolutionDataExporter` class,
            which requires a connection to an instance of the :class:`Hfss` class.
            The default is `` True``. If ``False``, returns an instance of
            :class:`ansys.aedt.core.generic.farfield_explorer.FfdSolutionData` class, which is
            independent of the running HFSS instance.
        export_touchstone : bool, optional
            Whether to export touchstone file. The default is ``False``.
        set_phase_center_per_port : bool, optional
            Set phase center per port location. The default is ``True``.

        Returns
        -------
        :class:`ansys.aedt.core.visualization.post.farfield_exporter.FfdSolutionDataExporter`
            SolutionData object.
        """
        warnings.warn("Use :func:`get_antenna_data` method instead.", DeprecationWarning)
        return self.get_antenna_data(
            frequencies=frequencies,
            setup=setup,
            sphere=sphere,
            variations=variations,
            overwrite=overwrite,
            link_to_hfss=link_to_hfss,
            export_touchstone=export_touchstone,
            set_phase_center_per_port=set_phase_center_per_port,
        )

    @pyaedt_function_handler()
    def get_antenna_data(
        self,
        frequencies=None,
        setup=None,
        sphere=None,
        variations=None,
        overwrite=True,
        link_to_hfss=True,
        export_touchstone=True,
        set_phase_center_per_port=True,
    ):
        """Export the antenna parameters to Far Field Data (FFD) files and return an
        instance of the ``FfdSolutionDataExporter`` object.

        For phased array cases, only one phased array is calculated.

        Parameters
        ----------
        frequencies : float, list, optional
            Frequency value or list of frequencies to compute far field data. The default is ``None,`` in which case
            all available frequencies are computed.
        setup : str, optional
            Name of the setup to use. The default is ``None,`` in which case ``nominal_adaptive`` is used.
        sphere : str, optional
            Infinite sphere to use. The default is ``None``, in which case an existing sphere is used or a new
            one is created.
        variations : dict, optional
            Variation dictionary. The default is ``None``, in which case the nominal variation is exported.
        overwrite : bool, optional
            Whether to overwrite FFD files. The default is ``True``.
        link_to_hfss : bool, optional
            Whether to return an instance of the
            :class:`ansys.aedt.core.visualization.advanced.farfield_exporter.FfdSolutionDataExporter` class,
            which requires a connection to an instance of the :class:`Hfss` class.
            The default is `` True``. If ``False``, returns an instance of
            :class:`ansys.aedt.core.visualization.advanced.farfield_visualization.FfdSolutionData` class, which is
            independent of the running HFSS instance.
        export_touchstone : bool, optional
            Whether to export touchstone file. The default is ``False``.
        set_phase_center_per_port : bool, optional
            Set phase center per port location. The default is ``True``.

        Returns
        -------
        :class:`ansys.aedt.core.visualization.advanced.farfield_visualization.FfdSolutionDataExporter`
            SolutionData object.

        Examples
        --------
        The method :func:`get_antenna_data` is used to export the farfield of each element of the design.

        Open a design and create the objects.

        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> ffdata = hfss.get_antenna_data()
        >>> ffdata.farfield_data.plot_cut(primary_sweep="theta",theta=0,is_polar=False)
        """
        from ansys.aedt.core.visualization.advanced.farfield_visualization import FfdSolutionData
        from ansys.aedt.core.visualization.post.farfield_exporter import FfdSolutionDataExporter

        if not variations:
            variations = self.available_variations.get_independent_nominal_values()
        if not setup:
            setup = self.nominal_adaptive

        if sphere:
            names = [i.name for i in self.field_setups]
            if sphere in names:
                self.logger.info("Far field sphere %s is assigned", sphere)

            else:
                self.insert_infinite_sphere(
                    x_start=0, x_stop=180, x_step=5, y_start=-180, y_stop=180, y_step=5, name=sphere
                )
                self.logger.info("Far field sphere %s is created.", sphere)
        elif self.field_setups:
            sphere = self.field_setups[0].name
            self.logger.info("No far field sphere is defined. Using %s", sphere)
        else:
            sphere = "Infinite Sphere1"
            self.insert_infinite_sphere(
                x_start=0, x_stop=180, x_step=5, y_start=-180, y_stop=180, y_step=5, name=sphere
            )
            self.logger.info("Far field sphere %s is created.", setup)

        frequency_units = self.odesktop.GetDefaultUnit("Frequency")

        # Prepend analysis name if only the sweep name is passed for the analysis.
        setup = self.nominal_adaptive.split(":")[0] + ": " + setup if not ":" in setup else setup

        if setup in self.existing_analysis_sweeps and frequencies is None:
            trace_name = "mag(rETheta)"
            farfield_data = self.post.get_far_field_data(expressions=trace_name, setup_sweep_name=setup, domain=sphere)
            if farfield_data and getattr(farfield_data, "primary_sweep_values", None) is not None:
                frequencies = farfield_data.primary_sweep_values

        if frequencies is not None:
            if type(frequencies) in [float, int, str]:
                frequencies = [frequencies]
            frequencies = [f"{freq}{frequency_units}" if is_number(freq) else f"{freq}" for freq in frequencies]
        else:  # pragma: no cover
            self.logger.info("Frequencies could not be obtained.")
            return False

        ffd = FfdSolutionDataExporter(
            self,
            sphere_name=sphere,
            setup_name=setup,
            frequencies=frequencies,
            variations=variations,
            overwrite=overwrite,
            export_touchstone=export_touchstone,
            set_phase_center_per_port=set_phase_center_per_port,
        )

        metadata_file = ffd.export_farfield()
        if link_to_hfss:
            return ffd
        elif metadata_file:
            return FfdSolutionData(input_file=metadata_file)

        raise AEDTRuntimeError("Farfield solution data could not be exported.")

    @pyaedt_function_handler()
    def get_rcs_data(
        self,
        frequencies=None,
        setup=None,
        expression="ComplexMonostaticRCSTheta",
        variations=None,
        overwrite=True,
        link_to_hfss=True,
        variation_name=None,
    ):
        """Export the radar cross-section data.

        This method returns an instance of the ``RcsSolutionDataExporter`` object.

        Parameters
        ----------
        frequencies : float, list, optional
            Frequency value or list of frequencies to compute the data. The default is ``None,`` in which case
            all available frequencies are computed.
        setup : str, optional
            Name of the setup to use. The default is ``None,`` in which case ``nominal_adaptive`` is used.
        expression : str, optional
            Monostatic expression name. The default value is ``"ComplexMonostaticRCSTheta"``.
        variations : dict, optional
            Variation dictionary. The default is ``None``, in which case the nominal variation is exported.
        overwrite : bool, optional
            Whether to overwrite metadata files. The default is ``True``.
        link_to_hfss : bool, optional
            Whether to return an instance of the
            :class:`ansys.aedt.core.visualization.post.rcs_exporter.MonostaticRCSExporter` class,
            which requires a connection to an instance of the :class:`Hfss` class.
            The default is `` True``. If ``False``, returns an instance of
            :class:`ansys.aedt.core.visualization.advanced.rcs_visualization.MonostaticRCSData` class, which is
            independent of the running HFSS instance.
        variation_name : str, optional
            Variation name. The default is ``None``, in which case the nominal variation is added.

        Returns
        -------
        :class:`ansys.aedt.core.post.rcs_exporter.MonostaticRCSExporter`
            SolutionData object.

        Examples
        --------
        The method :func:`get_antenna_data` is used to export the farfield of each element of the design.

        Open a design and create the objects.

        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> rcs_data = hfss.get_rcs_data()
        """
        from ansys.aedt.core.visualization.advanced.rcs_visualization import MonostaticRCSData
        from ansys.aedt.core.visualization.post.rcs_exporter import MonostaticRCSExporter

        if not variations:
            variations = self.available_variations.get_independent_nominal_values()
        if not setup:
            setup = self.nominal_adaptive

        if setup in self.existing_analysis_sweeps and not frequencies:
            rcs_data = self.post.get_solution_data(
                expressions=expression,
                variations=variations,
                setup_sweep_name=setup,
                report_category="Monostatic RCS",
            )
            if rcs_data and rcs_data.primary_sweep_values is not None:
                frequencies = rcs_data.primary_sweep_values
                frequency_units = self.odesktop.GetDefaultUnit("Frequency")
                frequencies = [str(freq) + frequency_units for freq in frequencies]

        if not frequencies:  # pragma: no cover
            self.logger.info("Frequencies could not be obtained.")
            return False

        rcs = MonostaticRCSExporter(
            self,
            setup_name=setup,
            frequencies=frequencies,
            expression=expression,
            variations=variations,
            overwrite=overwrite,
        )

        if variation_name:
            rcs.solution = variation_name

        metadata = rcs.export_rcs()
        if link_to_hfss:
            return rcs
        elif metadata:
            return MonostaticRCSData(input_file=metadata)

        raise AEDTRuntimeError("Farfield solution data could not be exported.")

    @pyaedt_function_handler()
    def set_material_threshold(self, threshold=100000):
        """Set the material conductivity threshold.

        Parameters
        ----------
        threshold : float, optional
            Conductivity threshold. The default value is ``100000``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        try:
            self.odesign.SetSolveInsideThreshold(threshold)
            return True
        except Exception as e:
            raise AEDTRuntimeError("Material conductivity threshold could not be set.") from e

    @pyaedt_function_handler(entity_list="assignment", simmetry_name="name")
    def assign_symmetry(self, assignment, name=None, is_perfect_e=True):
        """Assign symmetry to planar entities.

        Parameters
        ----------
        assignment : list
            List of IDs or :class:`ansys.aedt.core.modeler.cad.elements_3d.FacePrimitive`.
        name : str, optional
            Name of the boundary.
            If a name is not provided, one is automatically generated.
        is_perfect_e : bool, optional
            Type of symmetry plane the boundary represents: Perfect E or Perfect H.
            The default value is ``True`` (Perfect E).

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Boundary object.

        References
        ----------
        >>> oModule.AssignSymmetry

        Examples
        --------

        Create a box. Select the faces of this box and assign a symmetry.

        >>> symmetry_box = hfss.modeler.create_box([0 , -100, 0],[200, 200, 200],name="SymmetryForFaces")
        >>> ids = [i.id for i in hfss.modeler["SymmetryForFaces"].faces]
        >>> symmetry = hfss.assign_symmetry(ids)
        >>> type(symmetry)
        <class 'from ansys.aedt.core.modules.boundary.common.BoundaryObject'>

        """
        if self.solution_type not in (SOLUTIONS.Hfss.DrivenModal, SOLUTIONS.Hfss.EigenMode):
            raise AEDTRuntimeError("Symmetry is only available with 'Modal' and 'Eigenmode' solution types.")
        if not isinstance(assignment, list):
            raise TypeError("Entities have to be provided as a list.")

        if name is None:
            name = generate_unique_name("Symmetry")

        assignment = self.modeler.convert_to_selections(assignment, True)

        props = dict({"Name": name, "Faces": assignment, "IsPerfectE": is_perfect_e})
        return self._create_boundary(name, props, "Symmetry")

    @pyaedt_function_handler()
    def set_impedance_multiplier(self, multiplier):
        # type: (float) -> bool
        """Set impedance multiplier.

        Parameters
        ----------
        multiplier : float
            Impedance Multiplier.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.ChangeImpedanceMult

        Examples
        --------

        Create a box. Select the faces of this box and assign a symmetry.

        >>> symmetry_box = hfss.modeler.create_box([0 , -100, 0],[200, 200, 200],name="SymmetryForFaces")
        >>> ids = [i.id for i in hfss.modeler["SymmetryForFaces"].faces]
        >>> symmetry = hfss.assign_symmetry(ids)
        >>> hfss.set_impedance_multiplier(2.0)

        """
        if self.solution_type != SOLUTIONS.Hfss.DrivenModal:
            raise AEDTRuntimeError("Symmetry is only available with 'Modal' solution type.")

        self.oboundary.ChangeImpedanceMult(multiplier)
        return True

    @pyaedt_function_handler()
    def set_phase_center_per_port(self, coordinate_system=None):
        # type: (list) -> bool
        """Set phase center per port.

        Parameters
        ----------
        coordinate_system : list
            List of the coordinate system per port. The default is ``None``, in which case the
            default port location is assigned.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.SetPhaseCenterPerPort

        Examples
        --------

        Set phase center of an antenna with two ports.

        >>> hfss.set_phase_center_per_port(["Global", "Global"])

        """

        if not self.desktop_class.is_grpc_api:  # pragma: no cover
            raise AEDTRuntimeError("Set phase center is not supported by AEDT COM API. Set phase center manually.")

        port_names = self.ports[::]

        if not port_names:  # pragma: no cover
            return False

        if not coordinate_system:
            coordinate_system = ["<-Port Location->"] * len(port_names)
        elif not isinstance(coordinate_system, list):
            return False
        elif len(coordinate_system) != len(port_names):
            return False

        cont = 0
        arg = []
        for port in port_names:
            arg.append(["NAME:" + port, "Coordinate System:=", coordinate_system[cont]])
            cont += 1

        try:
            self.oboundary.SetPhaseCenterPerPort(arg)
        except Exception:
            return False
        return True

    @pyaedt_function_handler(filename="file_name")
    def parse_hdm_file(self, file_name):
        """Parse an HFSS SBR+ or Creeping Waves ``hdm`` file.

        Parameters
        ----------
        file_name : str
            Name of the file to parse.

        Returns
        -------
        :class:`ansys.aedt.core.modules.hdm_parser.Parser`
        """

        from ansys.aedt.core.visualization.advanced.sbrplus.hdm_parser import Parser

        if os.path.exists(file_name):
            return Parser(file_name).parse_message()
        return False

    @pyaedt_function_handler(filename="file_name")
    def get_hdm_plotter(self, file_name=None):
        """Get the HDM plotter.

        Parameters
        ----------
        file_name : str, optional


        Returns
        -------
        :class:`ansys.aedt.core.sbrplus.plot.HDMPlotter`

        """
        from ansys.aedt.core.visualization.advanced.hdm_plot import HDMPlotter

        hdm = HDMPlotter()
        files = self.post.export_model_obj(export_as_multiple_objects=True, air_objects=False)
        for file in files:
            hdm.add_cad_model(file[0], file[1], file[2], self.modeler.model_units)
        hdm.add_hdm_bundle_from_file(file_name)
        return hdm

    @pyaedt_function_handler(signal="assignment")
    def circuit_port(
        self,
        assignment,
        reference,
        port_location=0,
        impedance=50,
        name=None,
        renormalize=True,
        renorm_impedance=50,
        deembed=False,
    ):
        """Create a circuit port from two objects.

        The integration line is from edge 2 to edge 1.

        Parameters
        ----------
        assignment : int or :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d` or
         :class:`ansys.aedt.core.modeler.cad.FacePrimitive`or :class:`ansys.aedt.core.modeler.cad.EdgePrimitive`
            Signal object.
        reference : int or :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d` or
         :class:`ansys.aedt.core.modeler.cad.FacePrimitive`or :class:`ansys.aedt.core.modeler.cad.EdgePrimitive`
            Reference object.
        port_location : int or :class:`ansys.aedt.core.application.analysis.Analysis.AxisDir`, optional
            Position of the port when an object different from an edge is provided.
            It should be one of the values for ``Application.AxisDir``,
            which are: ``XNeg``, ``YNeg``, ``ZNeg``, ``XPos``, ``YPos``, and ``ZPos``.
            The default is ``Application.AxisDir.XNeg``.
        name : str, optional
            Name of the port. The default is ``""``.
        impedance : int, str, or float, optional
            Impedance. The default is ``"50"``. You can also
            enter a string that looks like this: ``"50+1i*55"``.
        renormalize : bool, optional
            Whether to renormalize the mode. The default is ``False``.
            This parameter is ignored for a driven terminal.
        renorm_impedance :  str, optional
            Impedance. The default is ``50``.
        deembed : bool, optional
            Whether to deembed the port. The default is ``False``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Boundary object.

        References
        ----------
        >>> oModule.AssignCircuitPort

        Examples
        --------

        Create two rectangles in the XY plane.
        Select the first edge of each rectangle created previously.
        Create a circuit port from the first edge of the first rectangle
        toward the first edge of the second rectangle.

        >>> plane = hfss.PLANE.XY
        >>> rectangle1 = hfss.modeler.create_rectangle(plane, [10, 10, 10], [10, 10],
        ...                                            name="rectangle1_for_port")
        >>> edges1 = hfss.modeler.get_object_edges(rectangle1.id)
        >>> first_edge = edges1[0]
        >>> rectangle2 = hfss.modeler.create_rectangle(plane, [30, 10, 10], [10, 10],
        ...                                            name="rectangle2_for_port")
        >>> edges2 = hfss.modeler.get_object_edges(rectangle2.id)
        >>> second_edge = edges2[0]
        >>> hfss.solution_type = "Modal"
        >>> hfss.circuit_port(first_edge,second_edge,
        ...                   impedance=50.1,
        ...                   name="PortExample",
        ...                   renormalize=False,
        ...                   renorm_impedance="50")
        'PortExample'
        """
        if self.solution_type not in (
            SOLUTIONS.Hfss.DrivenModal,
            SOLUTIONS.Hfss.DrivenTerminal,
            SOLUTIONS.Hfss.Transient,
        ):
            raise AEDTRuntimeError("Invalid solution type.")

        if not self.modeler.does_object_exists(assignment) or not self.modeler.does_object_exists(reference):
            out = self.modeler.convert_to_selections([assignment, reference], True)
            if isinstance(out[0], str) or isinstance(out[1], str):
                raise AEDTRuntimeError("Failed to create circuit port.")
        else:
            out, _ = self.modeler.find_closest_edges(assignment, reference, port_location)
        name = self._get_unique_source_name(name, "Port")
        return self._create_circuit_port(out, impedance, name, renormalize, deembed, renorm_impedance=renorm_impedance)

    @pyaedt_function_handler(signal="assignment")
    def lumped_port(
        self,
        assignment,
        reference=None,
        create_port_sheet=False,
        port_on_plane=True,
        integration_line=0,
        impedance=50,
        name=None,
        renormalize=True,
        deembed=False,
        terminals_rename=True,
    ):
        """Create a waveport taking the closest edges of two objects.

        Parameters
        ----------
        assignment : str, int, list, :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d` or
            :class:`ansys.aedt.core.modeler.cad.elements_3d.FacePrimitive`
            Main object for port creation or starting object for the integration line.
        reference : int, list or :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
            Ending object for the integration line or reference for Terminal solution. Can be multiple objects.
        create_port_sheet : bool, optional
            Whether to create a port sheet or use given start_object as port sheet.
        integration_line : int or :class:`ansys.aedt.core.application.analysis.Analysis.AxisDir`, optional
            Position of the port. It should be one of the values for ``Application.AxisDir``,
            which are: ``XNeg``, ``YNeg``, ``ZNeg``, ``XPos``, ``YPos``, and ``ZPos``.
            The default is ``Application.AxisDir.XNeg``.
            It can also be a list of 2 points.
        port_on_plane : bool, optional
            Whether to create the source on the plane orthogonal to ``AxisDir``.
            The default is ``True``.
        impedance : float, optional
            Port impedance. The default is ``50``.
        name : str, optional
            Name of the port. The default is ``None``.
        renormalize : bool, optional
            Whether to renormalize the mode. The default is ``True``.
        deembed : float, optional
            Deembed distance in millimeters. The default is ``0``, in which case deembed is disabled.
        terminals_rename : bool, optional
            Modify terminals name with the port name plus the terminal number. The default value is ``True``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Port object.

        Examples
        --------

        Create two boxes that will be used to create a lumped port
        named ``'LumpedPort'``.

        >>> box1 = hfss.modeler.create_box([0, 0, 50],[10, 10, 5],"BoxLumped1","copper")
        >>> box2 = hfss.modeler.create_box([0, 0, 60],[10, 10, 5],"BoxLumped2","copper")
        >>> hfss.lumped_port("BoxLumped1","BoxLumped2",hfss.AxisDir.XNeg,50,"LumpedPort",True,False)
        PyAEDT INFO: Connection Correctly created
        'LumpedPort'

        """
        if create_port_sheet:
            assignment = self.modeler.convert_to_selections(assignment)
            reference = self.modeler.convert_to_selections(reference)
            if not self.modeler.does_object_exists(assignment) or not self.modeler.does_object_exists(reference):
                raise AEDTRuntimeError("One or both objects do not exist. Check and retry.")
            sheet_name, point0, point1 = self.modeler._create_sheet_from_object_closest_edge(
                assignment, reference, integration_line, port_on_plane
            )
        else:
            if isinstance(assignment, list):
                objs = self.modeler.get_faceid_from_position(assignment)
                if len(objs) == 1:
                    assignment = objs[0]
                elif len(objs) > 1:
                    self.logger.warning("More than one face was found. Getting the first one.")
                    assignment = objs[0]
                else:
                    raise AEDTRuntimeError("No Faces found on given location.")

            sheet_name = self.modeler.convert_to_selections(assignment, False)
            if isinstance(integration_line, list):
                if len(integration_line) != 2 or len(integration_line[0]) != len(integration_line[1]):
                    raise ValueError("List of coordinates is not set correctly.")

                point0 = integration_line[0]
                point1 = integration_line[1]
            else:
                point0, point1 = self.modeler.get_mid_points_on_dir(sheet_name, integration_line)

        if self.solution_type not in (
            SOLUTIONS.Hfss.DrivenModal,
            SOLUTIONS.Hfss.DrivenTerminal,
            SOLUTIONS.Hfss.Transient,
        ):
            raise AEDTRuntimeError("Invalid solution type.")

        name = self._get_unique_source_name(name, "Port")

        if "Modal" in self.solution_type:
            return self._create_lumped_driven(sheet_name, point0, point1, impedance, name, renormalize, deembed)
        else:
            faces = self.modeler.get_object_faces(sheet_name)
            if deembed:
                deembed = 0
            else:
                deembed = None
            return self._create_port_terminal(
                faces[0],
                reference,
                name,
                renorm=renormalize,
                deembed=deembed,
                iswaveport=False,
                impedance=impedance,
                terminals_rename=terminals_rename,
            )

    @pyaedt_function_handler(signal="assignment", num_modes="modes")
    def wave_port(
        self,
        assignment,
        reference=None,
        create_port_sheet=False,
        create_pec_cap=False,
        integration_line=0,
        port_on_plane=True,
        modes=1,
        impedance=50,
        name=None,
        renormalize=True,
        deembed=0,
        is_microstrip=False,
        vfactor=3,
        hfactor=5,
        terminals_rename=True,
        characteristic_impedance="Zpi",
    ):
        """Create a waveport from a sheet (``start_object``) or taking the closest edges of two objects.

        Parameters
        ----------
        assignment : int, str, :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d` or
         :class:`ansys.aedt.core.modeler.cad.elements_3d.FacePrimitive`
            Main object for port creation or starting object for the integration line.
        reference : int, str, list or :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
            Ending object for the integration line or reference for Terminal solution. Can be multiple objects.
        create_port_sheet : bool, optional
            Whether to create a port sheet or use the start object as the surface
            to create the port. The default is ``False``.
        create_pec_cap : bool, False
            Whether to create a port cap. The default is ``False``.
        integration_line : list or int or :class:`ansys.aedt.core.application.analysis.Analysis.AxisDir`, optional
            Position of the integration. It should be one of the values for ``Application.AxisDir``,
            which are: ``XNeg``, ``YNeg``, ``ZNeg``, ``XPos``, ``YPos``, and ``ZPos``
            The default is ``Application.AxisDir.XNeg``.
            It can also be a list of 2 points.
        port_on_plane : bool, optional
            Whether to create the source on the plane orthogonal to ``AxisDir``.
            The default is ``True``.
        impedance : float, optional
            Port impedance. The default is ``50``.
        modes : int, optional
            Number of modes. The default is ``1``.
        name : str, optional
            Name of the port. The default is ``None``, in which
            case a name is automatically assigned.
        renormalize : bool, optional
            Whether to renormalize the mode. The default is ``True``.
        deembed : float, optional
            Deembed distance in millimeters. The default is ``0``.
        is_microstrip : bool, optional
            Whether if the wave port will be created and is a microstrip port.
            The default is ``False``.
        vfactor : int, optional
            Port vertical factor. Only valid if ``is_microstrip`` is enabled. The default is ``3``.
        hfactor : int, optional
            Port horizontal factor. Only valid if ``is_microstrip`` is enabled. The default is ``5``.
        terminals_rename : bool, optional
            Modify terminals name with the port name plus the terminal number. The default is ``True``.
        characteristic_impedance : str or list, optional
            Characteristic impedance for each mode. Available options are `"Zpi"``,`"Zpv"``, `"Zvi"``, and `"Zwave"``.
            The default is ``"Zpi"``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Port object.

        References
        ----------
        >>> oModule.AssignWavePort

        Examples
        --------

        Create a wave port supported by a microstrip line.

        >>> import ansys.aedt.core
        >>> hfss = ansys.aedt.core.Hfss()
        >>> ms = hfss.modeler.create_box([4, 5, 0], [1, 100, 0.2], name="MS1", material="copper")
        >>> sub = hfss.modeler.create_box([0, 5, -2], [20, 100, 2],name="SUB1", material="FR4_epoxy")
        >>> gnd = hfss.modeler.create_box([0, 5, -2.2], [20, 100, 0.2],name="GND1", material="FR4_epoxy")
        >>> port = hfss.wave_port("GND1", "MS1", integration_line=1, name="MS1")

        Create a wave port in a circle.

        >>> import ansys.aedt.core
        >>> hfss = ansys.aedt.core.Hfss()
        >>> c = hfss.modeler.create_circle("Z", [-1.4 ,-1.6 ,0], 1, name="wave_port")
        >>> start = [["-1.4mm", "-1.6mm", "0mm"], ["-1.4mm", "-1.6mm", "0mm"]]
        >>> end = [["-1.4mm", "-0.6mm", "0mm"], ["-1.4mm", "-2.6mm", "0mm"]]
        >>> port = hfss.wave_port(c.name, integration_line=[start, end], characteristic_impedance=["Zwave", "Zpv"])

        """
        oname = ""

        if create_port_sheet:
            if not self.modeler.does_object_exists(assignment) or not self.modeler.does_object_exists(reference):
                raise AEDTRuntimeError("One or both objects do not exist. Check and retry.")

            elif isinstance(assignment, cad.elements_3d.FacePrimitive):
                port_sheet = assignment.create_object()
                oname = port_sheet.name
            if is_microstrip:
                sheet_name, int_start, int_stop = self.modeler._create_microstrip_sheet_from_object_closest_edge(
                    assignment, reference, integration_line, vfactor, hfactor
                )
            else:
                sheet_name, int_start, int_stop = self.modeler._create_sheet_from_object_closest_edge(
                    assignment, reference, integration_line, port_on_plane
                )
        else:
            if isinstance(assignment, list):
                objs = self.modeler.get_faceid_from_position(assignment)
                if len(objs) == 1:
                    assignment = objs[0]
                elif len(objs) > 1:
                    self.logger.warning("More than one face found. Getting first.")
                    assignment = objs[0]
                else:
                    raise AEDTRuntimeError("No faces were found on given location.")

            sheet_name = self.modeler.convert_to_selections(assignment, True)[0]
            if isinstance(sheet_name, int):
                try:
                    # NOTE: if isinstance(sheet_name, cad.elements_3d.FacePrimitive) then
                    # the name of the 3d object is returned.
                    # TODO: Need to improve the way a FacePrimitive is handled.
                    oname = self.modeler.oeditor.GetObjectNameByFaceID(sheet_name)
                except Exception:
                    oname = ""
            if reference:
                reference = self.modeler.convert_to_selections(reference, True)
            #  TODO: integration_line == self.aedtapp.AxisDir.XNeg will be False in next line. Fix this.
            if integration_line:
                if isinstance(integration_line, list):
                    if len(integration_line) != 2 or len(integration_line[0]) != len(integration_line[1]):
                        raise ValueError("List of coordinates is not set correctly.")

                    int_start = integration_line[0]
                    int_stop = integration_line[1]

                else:
                    # Get two points on the port surface: if only the direction is given.
                    # int_start and int_stop.
                    try:
                        _, int_start, int_stop = self._get_reference_and_integration_points(
                            sheet_name, integration_line, oname
                        )
                    except (IndexError, TypeError):
                        int_start = int_stop = None
            else:
                int_start = int_stop = None
        if self.solution_type not in (
            SOLUTIONS.Hfss.DrivenModal,
            SOLUTIONS.Hfss.DrivenTerminal,
            SOLUTIONS.Hfss.Transient,
        ):
            raise AEDTRuntimeError("Invalid solution type.")

        if create_pec_cap:
            if oname:
                #  if isinstance(signal, cad.elements_3d.FacePrimitive):
                #      pec_face = signal.create_object()
                #      face = pec_face.id
                #  else:
                face = oname
            else:
                face = sheet_name
            dist = math.sqrt(self.modeler[face].faces[0].area)  # TODO: Move this into _create_pec_cap
            if settings.aedt_version > "2022.2":
                self._create_pec_cap(face, assignment, -dist / 10)
            else:
                self._create_pec_cap(face, assignment, dist / 10)
        name = self._get_unique_source_name(name, "Port")

        if self.solution_type == SOLUTIONS.Hfss.DrivenModal:
            if isinstance(characteristic_impedance, str):
                characteristic_impedance = [characteristic_impedance] * modes
            elif modes != len(characteristic_impedance):
                raise ValueError("List of characteristic impedance is not set correctly.")
            return self._create_waveport_driven(
                sheet_name, int_start, int_stop, impedance, name, renormalize, modes, deembed, characteristic_impedance
            )
        elif reference:
            if isinstance(sheet_name, int):
                faces = [sheet_name]
            else:
                faces = self.modeler.get_object_faces(sheet_name)
            if deembed == 0:
                deembed = None
            else:
                deembed = deembed

            # Draw terminal lumped port between two objects.
            return self._create_port_terminal(
                faces[0],
                reference,
                name,
                renorm=renormalize,
                deembed=deembed,
                iswaveport=True,
                impedance=impedance,
                terminals_rename=terminals_rename,
            )
        else:
            raise AEDTRuntimeError("Reference conductors are missing.")

    @pyaedt_function_handler()
    def plane_wave(
        self,
        vector_format="Spherical",
        origin=None,
        polarization=None,
        propagation_vector=None,
        wave_type="Propagating",
        wave_type_properties=None,
        name=None,
    ):
        """Create a plane wave excitation.

        Parameters
        ----------
        vector_format : str, optional
            Vector input format. Options are ``"Spherical"`` or ``"Cartesian"``. The default is ``"Spherical"``.
        origin : list, optional
            Excitation location and zero phase position. The default is ``["0mm", "0mm", "0mm"]``.
        polarization : str or list, optional
            Electric field polarization vector. If ``"Vertical"`` or ``"Horizontal"`` is passed, the method computes
            the electric polarization vector.
            If a ``list`` is passed, the user can customize the input vector. If ``vector_format`` is ``"Cartesian"``,
            the vector has three coordinates which corresponds to ``["Ex", "Ey", "Ez"]``.
            If ``vector_format`` is ``"Spherical"``, the vector has two coordinates which corresponds to
            ``["Ephi", "Etheta"]``.
            The default is ``"Vertical"``.
        propagation_vector : list, optional
            Propagation vector.
            If ``vector_format`` is ``"Cartesian"`` the type must be a ``list`` with three elements.
            If ``vector_format`` is ``"Spherical"`` the type must be a ``list`` with two elements. The first element
            corresponds to the phi sweep, which must be a ``list`` of three elements: start, stop, and number of points.
            The second element has the same format, it corresponds to the theta sweep.
            The default is ``[0.0, 0.0, 1.0]`` for ``"Cartesian"`` and
            ``[["0.0deg", "0.0deg", 1], ["0.0deg", "0.0deg", 1]]`` for ``"Spherical"``.
        wave_type : str, optional
            Type of plane wave. Options are ``"Propagating"``, ``"Evanescent"``,  or ``"Elliptical"``.
            The default is ``"Propagating"``.
        wave_type_properties : list, optional
            Properties of the plane wave type.
            If ``"Propagating"`` is used, no additional properties are needed. The default is ``None``.
            If ``"Evanescent"`` is selected, the propagation constant is expressed as both real and
            imaginary components. The default is ``[0.0, 1.0]``.
            If ``"Elliptical"`` is used, the polarization angle and ratio are defined. The default is
            ``["0deg", 1.0]``.
        name : str, optional
            Name of the excitation. The default is ``None``, in which
            case a name is automatically assigned.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Port object.

        References
        ----------
        >>> oModule.AssignPlaneWave

        Examples
        --------

        Create a plane wave excitation.

        >>> port1 = hfss.plane_wave(vector_format="Spherical",
         ...                        polarization="Vertical",
         ...                        propagation_vector=[["0deg","90deg", 25], ["0deg","0deg", 1]])
        >>> port2 = hfss.plane_wave(vector_format="Cartesian",
         ...                        polarization=[1, 1, 0], propagation_vector=[0, 0, 1])
        """

        if vector_format.lower() not in ["spherical", "cartesian"]:
            raise ValueError("Invalid value for `vector_format`. The value must be 'Spherical', or 'Cartesian'.")
        if wave_type.lower() not in ["propagating", "evanescent", "elliptical"]:
            raise ValueError(
                "Invalid value for `wave_type`." " The value must be 'Propagating', Evanescent, or 'Elliptical'."
            )
        if not origin:
            origin = ["0mm", "0mm", "0mm"]
        elif not isinstance(origin, list) or len(origin) != 3:
            raise ValueError("Invalid value for `origin`.")

        x_origin, y_origin, z_origin = self.modeler._pos_with_arg(origin)

        name = self._get_unique_source_name(name, "IncPWave")
        wave_type_props = {"IsPropagating": True, "IsEvanescent": False, "IsEllipticallyPolarized": False}

        if wave_type.lower() == "evanescent":
            wave_type_props["IsPropagating"] = False
            wave_type_props["IsEvanescent"] = True
            if not wave_type_properties:
                wave_type_properties = [0.0, 1.0]
            elif not isinstance(wave_type_properties, list) or len(wave_type_properties) != 2:
                raise ValueError("Invalid value for `wave_type_properties`.")
            wave_type_props["RealPropConst"] = wave_type_properties[0]
            wave_type_props["ImagPropConst"] = wave_type_properties[1]

        elif wave_type.lower() == "elliptical":
            wave_type_props["IsPropagating"] = False
            wave_type_props["IsEllipticallyPolarized"] = True
            if not wave_type_properties:
                wave_type_properties = ["0.0deg", 1.0]
            elif not isinstance(wave_type_properties, list) or len(wave_type_properties) != 2:
                raise ValueError("Invalid value for `wave_type_properties`.")
            wave_type_props["PolarizationAngle"] = wave_type_properties[0]
            wave_type_props["PolarizationRatio"] = wave_type_properties[0]

        inc_wave_args = {"OriginX": x_origin, "OriginY": y_origin, "OriginZ": z_origin}

        if vector_format == "Cartesian":
            if not polarization or polarization == "Vertical":
                polarization = [1.0, 0.0, 0.0]
            elif polarization == "Horizontal":
                polarization = [0.0, 1.0, 0.0]
            elif not isinstance(polarization, list) or len(polarization) != 3:
                raise ValueError("Invalid value for `polarization`.")

            if not propagation_vector:
                propagation_vector = [0.0, 0.0, 1.0]
            elif not isinstance(propagation_vector, list) or len(propagation_vector) != 3:
                raise ValueError("Invalid value for `propagation_vector`.")

            new_inc_wave_args = {
                "IsCartesian": True,
                "EoX": polarization[0],
                "EoY": polarization[1],
                "EoZ": polarization[2],
                "kX": propagation_vector[0],
                "kY": propagation_vector[1],
                "kZ": propagation_vector[2],
            }

        else:
            if not polarization or polarization == "Vertical":
                polarization = [0.0, 1.0]
            elif polarization == "Horizontal":
                polarization = [1.0, 0.0]
            elif not isinstance(polarization, list) or len(polarization) != 2:
                raise ValueError("Invalid value for `polarization`.")

            if not propagation_vector:
                propagation_vector = [["0.0deg", "0.0deg", 1], ["0.0deg", "0.0deg", 1]]
            elif (
                not isinstance(propagation_vector, list)
                or len(propagation_vector) != 2
                or not all(isinstance(vec, list) and len(vec) == 3 for vec in propagation_vector)
            ):
                raise ValueError("Invalid value for `propagation_vector`.")

            new_inc_wave_args = {
                "IsCartesian": False,
                "PhiStart": propagation_vector[0][0],
                "PhiStop": propagation_vector[0][1],
                "PhiPoints": propagation_vector[0][2],
                "ThetaStart": propagation_vector[1][0],
                "ThetaStop": propagation_vector[1][1],
                "ThetaPoints": propagation_vector[1][2],
                "EoPhi": polarization[0],
                "EoTheta": polarization[1],
            }

        inc_wave_args.update(new_inc_wave_args)
        inc_wave_args.update(wave_type_props)

        return self._create_boundary(name, inc_wave_args, "Plane Incident Wave")

    @pyaedt_function_handler()
    def hertzian_dipole_wave(
        self,
        assignment=None,
        origin=None,
        polarization=None,
        is_electric=True,
        radius="10mm",
        name=None,
    ) -> "BoundaryObject":
        """Create a hertzian dipole wave excitation.

        The excitation is assigned in the assigned sphere. Inside this sphere, the field magnitude
        is equal to the field magnitude calculated on the surface of the sphere.

        Parameters
        ----------
        assignment : str or list, optional
            One or more objects or faces to assign finite conductivity to. The default is ``None``, in which
            case the excitation is assigned to anything.
        origin : list, optional
            Excitation location. The default is ``["0mm", "0mm", "0mm"]``.
        polarization : list, optional
            Electric field polarization vector.
            The default is ``[0, 0, 1]``.
        is_electric : bool, optional
            Type of dipole. Electric dipole if ``True``, magnetic dipole if ``False``. The default is ``True``.
        radius : str or float, optional
            Radius of surrounding sphere. The default is "10mm".
        name : str, optional
            Name of the boundary.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Port object.

        References
        ----------
        >>> oModule.AssignHertzianDipoleWave

        Examples
        --------

        Create a hertzian dipole wave excitation.
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> sphere = hfss.modeler.primitives.create_sphere([0, 0, 0], 10)
        >>> port1 = hfss.hertzian_dipole_wave(assignment=sphere, radius=10)
        """
        if not origin:
            origin = ["0mm", "0mm", "0mm"]
        elif not isinstance(origin, list) or len(origin) != 3:
            raise ValueError("Invalid value for `origin`.")
        if not polarization:
            polarization = [0, 0, 1]
        elif not isinstance(polarization, list) or len(polarization) != 3:
            raise ValueError("Invalid value for `polarization`.")

        userlst = self.modeler.convert_to_selections(assignment, True)
        lstobj = []
        lstface = []
        for selection in userlst:
            if selection in self.modeler.model_objects:
                lstobj.append(selection)
            elif isinstance(selection, int) and self.modeler._find_object_from_face_id(selection):
                lstface.append(selection)

        props = {"Objects": [], "Faces": []}

        if lstobj:
            props["Objects"] = lstobj
        if lstface:
            props["Faces"] = lstface

        x_origin, y_origin, z_origin = self.modeler._pos_with_arg(origin)

        name = self._get_unique_source_name(name, "IncPWave")

        hetzian_wave_args = {"OriginX": x_origin, "OriginY": y_origin, "OriginZ": z_origin}

        new_hertzian_args = {
            "IsCartesian": True,
            "EoX": polarization[0],
            "EoY": polarization[1],
            "EoZ": polarization[2],
            "kX": polarization[0],
            "kY": polarization[1],
            "kZ": polarization[2],
        }

        hetzian_wave_args["IsElectricDipole"] = False
        if is_electric:
            hetzian_wave_args["IsElectricDipole"] = True

        hetzian_wave_args["SphereRadius"] = radius
        hetzian_wave_args.update(new_hertzian_args)
        hetzian_wave_args.update(props)

        return self._create_boundary(name, hetzian_wave_args, "Hertzian Dipole Wave")

    @pyaedt_function_handler()
    def set_radiated_power_calc_method(self, method="Auto"):
        """Set the radiated power calculation method in Hfss.

        method : str, optional
            Radiated power calculation method.
            The options are ``"Auto"``, ``"Radiation Surface Integral"`` and ``"Far Field Integral"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        self.oradfield.EditRadiatedPowerCalculationMethod(method)
        return True

    @pyaedt_function_handler(component="assignment")
    def set_mesh_fusion_settings(self, assignment=None, volume_padding=None, priority=None):
        # type: (list|str, list, list) -> bool

        """Set mesh fusion settings in HFSS.

        component : list, optional
            List of active 3D Components.
            The default is ``None``, in which case components are disabled.
        volume_padding : list, optional
            List of mesh envelope padding, the format is ``[+x, -x, +y, -y, +z, -z]``.
            The default is ``None``, in which case all zeros are applied.
        priority : list, optional
            List of components with the priority flag enabled. The default is ``None``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesign.SetDoMeshAssembly

        Examples
        --------

        >>> import ansys.aedt.core
        >>> app = ansys.aedt.core.Hfss()
        >>> app.set_mesh_fusion_settings(assignment=["Comp1", "Comp2"],
        >>>                              volume_padding=[[0,0,0,0,0,0], [0,0,5,0,0,0]],priority=["Comp1"])
        """
        arg = ["NAME:AllSettings"]
        arg2 = ["NAME:MeshAssembly"]
        arg3 = ["NAME:Priority Components"]

        if assignment and not isinstance(assignment, list):
            assignment = [assignment]

        if not volume_padding and assignment:
            for comp in assignment:
                if comp in self.modeler.user_defined_component_names:
                    mesh_assembly_arg = ["NAME:" + comp]
                    mesh_assembly_arg.append("MeshAssemblyBoundingVolumePadding:=")
                    mesh_assembly_arg.append(["0", "0", "0", "0", "0", "0"])
                    arg2.append(mesh_assembly_arg)
                else:
                    self.logger.warning(comp + " does not exist.")

        elif assignment and isinstance(volume_padding, list) and len(volume_padding) == len(assignment):
            count = 0
            for comp in assignment:
                padding = [str(pad) for pad in volume_padding[count]]
                if comp in self.modeler.user_defined_component_names:
                    mesh_assembly_arg = ["NAME:" + comp]
                    mesh_assembly_arg.append("MeshAssemblyBoundingVolumePadding:=")
                    mesh_assembly_arg.append(padding)
                    arg2.append(mesh_assembly_arg)
                else:
                    self.logger.warning(f"{str(comp)} does not exist")
                count += 1
        elif assignment and isinstance(volume_padding, list) and len(volume_padding) != len(assignment):
            raise ValueError("Volume padding length is different than component list length.")

        if priority and not isinstance(priority, list):
            priority = [priority]

        if assignment and priority:
            for p in priority:
                if p in self.modeler.user_defined_component_names:
                    arg3.append(p)
                else:
                    self.logger.warning(f"{str(p)} does not exist")

        arg.append(arg2)
        arg.append(arg3)
        self.odesign.SetDoMeshAssembly(arg)
        return True

    @pyaedt_function_handler()
    def export_element_pattern(
        self, frequencies, setup, sphere, variations=None, element_name="element", output_dir=None
    ):
        """Export the element pattern.

        For phased array cases, only one phased array is calculated.

        Parameters
        ----------
        frequencies : float, list
            Frequency value or list of frequencies to compute far field data.
        setup : str
            Name of the setup to use.
        sphere : str
            Infinite sphere to use.
        variations : dict, optional
            Variation dictionary. The default is ``None``, in which case the nominal variation is exported.
        element_name : str, optional
            Element pattern file name. The default is ``"element"``.
        output_dir : str, optional
            Path to export the element patterns to. The default is ``None``, in which
            case the files are exported to the working_directory path.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.ExportElementPatternToFile
        """
        self.logger.info("Exporting embedded element patterns...")

        variation = self.available_variations.variation_string(variations)
        command = [
            "ExportFileName:=",
            os.path.join(output_dir, element_name + ".ffd"),
            "SetupName:=",
            sphere,
        ]

        for frequency in frequencies:
            command.append("IntrinsicVariationKey:=")
            command.append("Freq='" + str(frequency) + "'")

        command.append("DesignVariationKey:=")
        command.append(variation)
        command.append("SolutionName:=")
        command.append(setup)

        try:
            self.oradfield.ExportElementPatternToFile(command)
            return True
        except Exception as e:  # pragma: no cover
            raise RuntimeError("Failed to export one element pattern.") from e

    @pyaedt_function_handler()
    def export_antenna_metadata(
        self,
        frequencies,
        setup,
        sphere,
        variations=None,
        output_dir=None,
        export_element_pattern=True,
        export_objects=False,
        export_touchstone=True,
        export_power=False,
    ):
        """Export the element pattern.

        For phased array cases, only one phased array is calculated.

        Parameters
        ----------
        frequencies : float, list
            Frequency value or list of frequencies to compute far field data.
        setup : str
            Name of the setup to use.
        sphere : str
            Infinite sphere to use.
        variations : dict, optional
            Variation dictionary. The default is ``None``, in which case the nominal variation is exported.
        output_dir : str, optional
            Path to export the element patterns to. The default is ``None``, in which
            case the files are exported to the working_directory path.
        export_element_pattern : bool, optional
            Whether to export the element patterns. The default is ``True``.
        export_objects : bool, optional
            Whether to export the objects. The default is ``False``.
        export_touchstone : bool, optional
            Whether to export touchstone file. The default is ``True``.
        export_power : bool, optional
            Whether to export all available powers: ``IncidentPower``, ``RadiatedPower``, ``AcceptedPower``.
            The default is ``False``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.ExportMetadata
        """
        self.logger.info("Exporting antenna metadata...")

        variation = self.available_variations.variation_string(variations)

        command = [
            "SolutionName:=",
            setup,
            "ExportElementPattern:=",
            export_element_pattern,
            "SetupName:=",
            sphere,
            "SourceGroupName:=",
            "Use Edit Sources",
        ]

        for frequency in frequencies:
            command.append("IntrinsicVariable:=")
            command.append("Freq='" + str(frequency) + "'")

        command.append("DesignVariable:=")
        command.append(variation)

        available_categories = self.post.available_quantities_categories()

        if "Active VSWR" in available_categories:  # pragma: no cover
            quantities = self.post.available_report_quantities(quantities_category="Active VSWR")
            for quantity in quantities:
                command.append("ElementPatterns:=")
                command.append(quantity[len("ActiveVSWR(") : -1])
        elif "Terminal VSWR" in available_categories:  # pragma: no cover
            quantities = self.post.available_report_quantities(quantities_category="Terminal VSWR")
            for quantity in quantities:
                command.append("ElementPatterns:=")
                command.append(quantity[len("VSWRt(") : -1])
        elif "Gamma" in available_categories:  # pragma: no cover
            quantities = self.post.available_report_quantities(quantities_category="Gamma")
            for quantity in quantities:
                command.append("ElementPatterns:=")
                command.append(quantity[len("Gamma(") : -1])
        else:  # pragma: no cover
            sources = self.get_all_sources()
            modes = self.get_all_source_modes()
            for source_cont, excitation in enumerate(sources):
                command.append("ElementPatterns:=")
                if self.solution_type == "SBR+":
                    command.append(excitation + ":" + modes[source_cont])
                else:
                    command.append(excitation)

        if export_power:
            command.append("ElementPowers:=")
            command.append("IncidentPower")
            command.append("ElementPowers:=")
            command.append("AcceptedPower")
            command.append("ElementPowers:=")
            command.append("RadiatedPower")
        command.append("ExportObject:=")
        command.append(export_objects)
        command.append("ExportTouchstone:=")
        if export_touchstone:
            command.append(True)
        else:
            command.append(False)

        command.append("ExportDirectory:=")
        command.append(output_dir)

        try:
            self.omodelsetup.ExportMetadata(command)
            self.logger.info("Antenna metadata exported.")
            return True
        except Exception as e:  # pragma: no cover
            raise AEDTRuntimeError("Failed to export antenna metadata.") from e

    @pyaedt_function_handler()
    def export_touchstone_on_completion(self, export=True, output_dir=None):
        """Enable or disable the automatic export of the touchstone file after completing frequency sweep.

        Parameters
        ----------
        export : bool, optional
            Whether to export the Touchstone file after the simulation.
            The default is ``True``.
        output_dir : str, optional
            Path to the directory of exported file. The default is the project path.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesign.SetDesignSettings
        """
        if export:
            self.logger.info("Enabling Export On Completion")
        else:
            self.logger.info("Disabling Export On Completion")
        if not output_dir:
            output_dir = ""
        props = {"Export After Simulation": export, "Export Dir": output_dir}
        return self.change_design_settings(props)

    @pyaedt_function_handler()
    def set_export_touchstone(
        self,
        file_format="TouchStone1.0",
        enforce_passivity=True,
        enforce_causality=False,
        use_common_ground=True,
        show_gamma_comments=True,
        renormalize=False,
        impedance=50.0,
        fitting_error=0.5,
        maximum_poles=1000,
        passivity_type="PassivityByPerturbation",
        column_fitting_type="Matrix",
        state_space_fitting="IterativeRational",
        relative_error_tolerance=True,
        ensure_accurate_fit=False,
        touchstone_output="MA",
        units="GHz",
        precision=11,
    ):
        """Set or disable the automatic export of the touchstone file after completing frequency sweep.

        Parameters
        ----------
        file_format : str, optional
            Touchstone format. Available options are: ``"TouchStone1.0"``, and ``"TouchStone2.0"``.
            The default is ``"TouchStone1.0"``.
        enforce_passivity : bool, optional
            Enforce passivity. The default is ``True``.
        enforce_causality : bool, optional
            Enforce causality. The default is ``False``.
        use_common_ground : bool, optional
            Use common ground. The default is ``True``.
        show_gamma_comments : bool, optional
            Show gamma comments. The default is ``True``.
        renormalize : bool, optional
            Renormalize. The default is ``False``.
        impedance : float, optional
            Impedance in ohms. The default is ``50.0``.
        fitting_error : float, optional
            Fitting error. The default is ``0.5``.
        maximum_poles : int, optional
            Maximum number of poles. The default is ``10000``.
        passivity_type : str, optional
            Passivity type. Available options are: ``"PassivityByPerturbation"``, ``"IteratedFittingOfPV"``,
            ``"IteratedFittingOfPVLF"``, and ``"ConvexOptimization"``.
        column_fitting_type : str, optional
            Column fitting type. Available options are: ``"Matrix"``, `"Column"``, and `"Entry"``.
        state_space_fitting : str, optional
            State space fitting algorithm. Available options are: ``"IterativeRational"``, `"TWA"``, and `"FastFit"``.
        relative_error_tolerance : bool, optional
            Relative error tolerance. The default is ``True``.
        ensure_accurate_fit : bool, optional
            Ensure accurate impedance fit. The default is ``False``.
        touchstone_output : str, optional
            Touchstone output format. Available options are: ``"MA"`` for magnitude and phase in ``deg``,
            ``"RI"`` for real and imaginary part, and ``"DB"`` for magnitude in ``dB`` and phase in ``deg``.
        units : str, optional
            Frequency units. The default is ``"GHz"``.
        precision : int, optional
            Touchstone precision. The default is ``11``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oTool.SetExportTouchstoneOptions

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss.export_touchstone_on_completion()
        >>> hfss.export_touchstone_on_completion()


        """
        preferences = "Hfss\\Preferences"
        design_name = self.design_name

        props = [
            "NAME:SpiceData",
            "SpiceType:=",
            file_format,
            "EnforcePassivity:=",
            enforce_passivity,
            "EnforceCausality:=",
            enforce_causality,
            "UseCommonGround:=",
            use_common_ground,
            "ShowGammaComments:=",
            show_gamma_comments,
            "Renormalize:=",
            renormalize,
            "RenormImpedance:=",
            impedance,
            "FittingError:=",
            fitting_error,
            "MaxPoles:=",
            maximum_poles,
            "PassivityType:=",
            passivity_type,
            "ColumnFittingType:=",
            column_fitting_type,
            "SSFittingType:=",
            state_space_fitting,
            "RelativeErrorToleranc:=",
            relative_error_tolerance,
            "EnsureAccurateZfit:=",
            ensure_accurate_fit,
            "TouchstoneFormat:=",
            touchstone_output,
            "TouchstoneUnits:=",
            units,
            "TouchStonePrecision:=",
            precision,
            "SubcircuitName:=",
            "",
        ]

        self.onetwork_data_explorer.SetExportTouchstoneOptions(preferences, design_name, props)
        return True

    @pyaedt_function_handler()
    def import_table(
        self,
        input_file,
        name,
        is_real_imag=True,
        is_field=False,
        column_names=None,
        independent_columns=None,
    ):
        """Import a data table.

            The table can have multiple independent real-valued columns of data,
            and multiple dependent real- or complex-valued columns of data.
            The data supported is comma delimited format (.csv).
            The first row may contain column names. Complex data columns are inferred from the column data format.
            In comma delimited format, "(double, double)" denotes a complex number.

        Parameters
        ----------
        input_file : str
            Full path to the file. Supported formats is ``".csv"``.
        name : str
            Table name.
        is_real_imag : bool, optional
            Whether to use real and imaginary to interpret data for any complex column. If ``False``, then use
            magnitude and phase in degrees. The default is ``True``.
        is_field : bool, optional
            Whether to matrix data. If ``True``, then use field data. The default is ``False``.
        column_names : list, optional
            Column names. The default is ``None``, in which case column names obtained from data file are assigned.
        independent_columns : list, optional
            Indicates which columns are independent. If ``None``, only the first column is independent.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.ImportTable

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss.import_table(input_file="my_file.csv")
        """
        input_path = Path(input_file).resolve()

        if not input_path.is_file():
            raise FileNotFoundError("File does not exist.")
        elif input_path.suffix != ".csv":
            raise ValueError("Invalid file extension. It must be ``.csv``.")
        if name in self.table_names:
            raise AEDTRuntimeError("Table name already assigned.")

        delimiter = ","

        with open_file(str(input_path), "r") as f:
            first_line = next(f)
            columns = first_line.split(delimiter)
            column_number = len(columns)
            is_header = all(not is_number(col) for col in columns)
            if not is_header:
                file_column_names = [f"col{i + 1}" for i in range(column_number)]
            else:
                last_column = columns[-1]
                file_column_names = columns[:-1]
                file_column_names.append(last_column[:-1])

        if not column_names:
            column_names = file_column_names
        elif isinstance(column_names, list) and len(column_names) != column_number:
            raise ValueError("Number of column names must be the same than number of data columns.")

        if not independent_columns:
            independent_columns = [False] * column_number
            independent_columns[0] = True
        elif isinstance(independent_columns, list) and len(independent_columns) != column_number:
            raise ValueError("Number of independent columns must be the same than number of data columns.")

        self.osolution.ImportTable(
            str(input_path), name, "Table", is_real_imag, is_field, column_names, independent_columns
        )
        return True

    @pyaedt_function_handler()
    def delete_table(self, name):
        """Delete data table.

        Parameters
        ----------
        name : str or list of str
            Table name to delete.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.DeleteImportData

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss.import_table(name="Table1")
        """
        name_list = self.modeler.convert_to_selections(name, True)
        new_name_list = []
        for new_name in name_list:
            new_name_list.append(f"{new_name}:Table")
        self.osolution.DeleteImportData(new_name_list)
        # UI is not updated, and it needs to save the project
        self.save_project()
        return True
