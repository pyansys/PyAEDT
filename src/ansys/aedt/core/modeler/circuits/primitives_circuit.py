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

import math
import os
import secrets

from ansys.aedt.core.application.variables import decompose_variable_value
from ansys.aedt.core.generic.constants import AEDT_UNITS
from ansys.aedt.core.generic.general_methods import filter_string
from ansys.aedt.core.generic.general_methods import generate_unique_name
from ansys.aedt.core.generic.general_methods import open_file
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.generic.general_methods import recursive_glob
from ansys.aedt.core.generic.load_aedt_file import load_keyword_in_aedt_file
from ansys.aedt.core.modeler.circuits.object_3d_circuit import CircuitComponent
from ansys.aedt.core.modeler.circuits.object_3d_circuit import Wire


class CircuitComponents(object):
    """CircutComponents class.

    Manages all circuit components for Nexxim and Twin Builder.

    Examples
    --------
    >>> from ansys.aedt.core import Circuit
    >>> aedtapp = Circuit()
    >>> prim = aedtapp.modeler.schematic
    """

    @pyaedt_function_handler()
    def __getitem__(self, partname):
        """Retrieve a part.

        Parameters
        ----------
        partname : int or str
           Part ID or part name.

        Returns
        -------
        type
            Part object details.
        """
        if isinstance(partname, int):
            return self.components[partname]
        for el in self.components:
            if self.components[el].name == partname or self.components[el].composed_name == partname or el == partname:
                return self.components[el]

        return None

    def __init__(self, modeler):
        self._app = modeler._app
        self._modeler = modeler
        self.logger = self._app.logger
        self.o_model_manager = self._modeler.o_model_manager

        self.oeditor = self._modeler.oeditor
        self._currentId = 0
        self.components = {}
        self.refresh_all_ids()
        self.current_position = [0, 0]
        self.increment_mils = [1000, 1000]
        self.limits_mils = 20000

    @pyaedt_function_handler()
    def get_wire_by_name(self, name):
        """Wire class by name.

        Parameters
        ----------
        name : str
            Wire name.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.circuits.object_3d_circuit.Wire`
        """
        for _, w in self.wires.items():
            if w.name == name:
                return w
            wname = w.name.split(";")[0].split("@")[0]
            if name == wname:
                return w

    @property
    def wires(self):
        """All schematic wires in the design.

        Returns
        -------
        dict
            Wires.
        """
        wire_names = {}
        for wire in self.oeditor.GetAllElements():
            if "Wire" in wire:
                w = Wire(self, composed_name=wire)
                if ":" in wire.split(";")[1]:
                    wire_id = int(wire.split(";")[1].split(":")[0])
                else:
                    wire_id = int(wire.split(";")[1])
                name = wire.split(";")[0].split("@")[1]
                w.id = wire_id
                w.name = name
                wire_names[wire_id] = w
        return wire_names

    @property
    def o_definition_manager(self):
        """Aedt oDefinitionManager.

        References
        ----------
        >>> oDefinitionManager = oProject.GetDefinitionManager()
        """
        return self._app.oproject.GetDefinitionManager()

    @property
    def o_component_manager(self):
        """Component manager object."""
        return self._app.o_component_manager

    @property
    def o_symbol_manager(self):
        """Model manager object."""
        return self._app.o_symbol_manager

    @property
    def version(self):
        """Version."""
        return self._app._aedt_version

    @property
    def model_units(self):
        """Model units."""
        return self._modeler.model_units

    @property
    def schematic_units(self):
        """Schematic units.

        Options are ``"mm"``, ``"mil"``, ``"cm"`` and all other metric and imperial units.
        The default is ``"meter"``.
        """
        return self._modeler.schematic_units

    @schematic_units.setter
    def schematic_units(self, value):
        self._modeler.schematic_units = value

    @property
    def design_type(self):
        """Design type."""
        return self._app.design_type

    @property
    def nets(self):
        """List of all schematic nets."""
        nets_comp = self.oeditor.GetAllNets()
        nets = []
        for net in nets_comp:
            v = net.split(";")
            if v[0].replace("Wire@", "") not in nets:
                nets.append(v[0].replace("Wire@", ""))
        return nets

    @pyaedt_function_handler()
    def _convert_point_to_meter(self, point):
        """Convert numbers automatically to mils.

        It is rounded to the nearest 100 mil which is minimum schematic snap unit.
        """
        xpos = point[0]
        ypos = point[1]

        if isinstance(point[0], (float, int)):
            xpos = (
                round(point[0] * AEDT_UNITS["Length"][self.schematic_units] / AEDT_UNITS["Length"]["mil"], -2)
                * AEDT_UNITS["Length"]["mil"]
            )
        else:
            decomposed = decompose_variable_value(point[0])
            if decomposed[1] != "":
                xpos = (
                    round(decomposed[0] * AEDT_UNITS["Length"][decomposed[1]] / AEDT_UNITS["Length"]["mil"], -2)
                    * AEDT_UNITS["Length"]["mil"]
                )
        if isinstance(point[1], (float, int)):
            ypos = (
                round(point[1] * AEDT_UNITS["Length"][self.schematic_units] / AEDT_UNITS["Length"]["mil"], -2)
                * AEDT_UNITS["Length"]["mil"]
            )
        else:
            decomposed = decompose_variable_value(point[1])
            if decomposed[1] != "":
                ypos = (
                    round(decomposed[0] * AEDT_UNITS["Length"][decomposed[1]] / AEDT_UNITS["Length"]["mil"], -2)
                    * AEDT_UNITS["Length"]["mil"]
                )
        return xpos, ypos

    @pyaedt_function_handler()
    def _convert_point_to_units(self, point):
        """Numbers are automatically converted and rounded to 100mil."""
        return [i / AEDT_UNITS["Length"][self.schematic_units] for i in self._convert_point_to_meter(point)]

    @pyaedt_function_handler()
    def _get_location(self, location=None):
        if not location:
            xpos = self.current_position[0]
            ypos = self.current_position[1]
        else:
            xpos, ypos = self._convert_point_to_meter(location)
            if isinstance(xpos, (float, int)) and isinstance(ypos, (float, int)):
                self.current_position = [xpos, ypos]
        self.current_position[1] += AEDT_UNITS["Length"]["mil"] * self.increment_mils[1]
        if self.current_position[1] / AEDT_UNITS["Length"]["mil"] > self.limits_mils:
            self.current_position[1] = 0
            self.current_position[0] += AEDT_UNITS["Length"]["mil"] * self.increment_mils[0]
        return xpos, ypos

    @pyaedt_function_handler()
    def create_unique_id(self):
        """Create an unique ID.

        Returns
        -------
        int
            Unique ID in the range of ``[1, 65535]``.

        """
        element_ids = []
        for el in self.oeditor.GetAllElements():
            try:
                element_ids.append(int(el.split("@")[1].split(";")[1].split(":")[0]))
            except (IndexError, ValueError):
                pass
        secure_random = secrets.SystemRandom()
        id = secure_random.randint(1, 65535)
        while id in element_ids:
            id = secure_random.randint(1, 65535)
        return id

    @pyaedt_function_handler()
    def add_pin_iports(self, name, id_num):
        """Add ports on pins.

        Parameters
        ----------
        name : str
            Name of the component.
        id_num : int
            ID of circuit component.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oeditor.AddPinIPorts
        """
        comp_id = "CompInst@" + name + ";" + str(id_num) + ";395"
        arg1 = ["Name:Selections", "Selections:=", [comp_id]]
        self.oeditor.AddPinIPorts(arg1)
        self.refresh_all_ids()
        return True

    @pyaedt_function_handler()
    def create_interface_port(self, name, location=None, angle=0):
        """Create an interface port.

        Parameters
        ----------
        name : str
            Name of the port.
        location : list, optional
            Position on the X and Y axis. The default is ``None``.
        angle : float, optional
            Angle rotation in degrees. The default is ``0``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.icepak_boundary.Excitation`
            Circuit Excitation Object.

        References
        ----------
        >>> oEditor.CreateIPort
        """
        if location is None:
            location = []

        if name in self._app.excitations:
            self.logger.warning("Port name already assigned.")
            return False

        xpos, ypos = self._get_location(location)
        id = self.create_unique_id()
        arg1 = ["NAME:IPortProps", "Name:=", name, "Id:=", id]
        arg2 = ["NAME:Attributes", "Page:=", 1, "X:=", xpos, "Y:=", ypos, "Angle:=", angle, "Flip:=", False]
        id = self.oeditor.CreateIPort(arg1, arg2)

        id = int(id.split(";")[1])
        self.add_id_to_component(id)
        # return id, self.components[id].composed_name
        for el in self.components:
            if ("IPort@" + name + ";" + str(id)) in self.components[el].composed_name:
                return self._app.excitation_objects[name]
        return False

    @pyaedt_function_handler()
    def create_page_port(self, name, location=None, angle=0):
        """Create a page port.

        Parameters
        ----------
        name : str
            Name of the port.
        location : list, optional
            Position on the X and Y axis.
            If not provided the default is ``None``, in which case an empty list is set.
        angle : optional
            Angle rotation in degrees. The default is ``0``.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.circuits.object_3d_circuit.CircuitComponent`
            Circuit Component Object.

        References
        ----------
        >>> oEditor.CreatePagePort
        """
        location = [] if location is None else location
        xpos, ypos = self._get_location(location)

        id = self.create_unique_id()
        id = self.oeditor.CreatePagePort(
            ["NAME:PagePortProps", "Name:=", name, "Id:=", id],
            ["NAME:Attributes", "Page:=", 1, "X:=", xpos, "Y:=", ypos, "Angle:=", angle, "Flip:=", False],
        )
        id = int(id.split(";")[1])
        # self.refresh_all_ids()
        self.add_id_to_component(id)
        return self.components[id]

    @pyaedt_function_handler()
    def create_gnd(self, location=None, angle=0, page=1):
        """Create a ground.

        Parameters
        ----------
        location : list, optional
            Position on the X and Y axis. The default is ``None``.
        angle : optional
            Angle rotation in degrees. The default is ``0``.
        page: int, optional
            Schematics page number. The default value is ``1``.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.circuits.object_3d_circuit.CircuitComponent`
            Circuit Component Object.

        References
        ----------
        >>> oEditor.CreateGround
        """
        if location is None:
            location = []

        xpos, ypos = self._get_location(location)
        id = self.create_unique_id()
        angle = math.pi * angle / 180
        name = self.oeditor.CreateGround(
            ["NAME:GroundProps", "Id:=", id],
            ["NAME:Attributes", "Page:=", page, "X:=", xpos, "Y:=", ypos, "Angle:=", angle, "Flip:=", False],
        )
        id = int(name.split(";")[1])
        self.add_id_to_component(id)
        # return id, self.components[id].composed_name
        for el in self.components:
            if name in self.components[el].composed_name:
                return self.components[el]

    @pyaedt_function_handler(touchstone_full_path="input_file")
    def create_model_from_touchstone(self, input_file, model_name=None, show_bitmap=True):
        """Create a model from a Touchstone file.

        Parameters
        ----------
        input_file : str
            Full path to the Touchstone file.
        model_name : str, optional
            Name of the model. The default is ``None``.
        show_bitmap : bool, optional
            Show bitmap image of schematic component.
            The default value is ``True``.

        Returns
        -------
        str
            Model name when successfully created. ``False`` if something went wrong.

        References
        ----------
        >>> oModelManager.Add
        >>> oComponentManager.Add
        """

        def _parse_ports_name(file, num_terminal):
            """Parse and interpret the option line in the touchstone file.

            Parameters
            ----------
            file : str
                Path of the Touchstone file.
            num_terminal : int
                Number of terminals.

            Returns
            -------
            List of str
                Names of the ports in the touchstone file.

            """
            portnames = []
            line = file.readline()
            while not line.startswith("! Port") and not line.startswith("! NPort") and line.find("S11") == -1:
                line = file.readline()
            if line.startswith("! Port"):
                while line.startswith("! Port"):
                    portnames.append(line.split(" = ")[1].strip())
                    line = file.readline()
            else:  # pragma: no cover
                portnames = ["Port" + str(n) for n in range(1, num_terminal + 1)]
            return portnames

        if not model_name:
            model_name = os.path.splitext(os.path.basename(input_file))[0]
            if "." in model_name:
                model_name = model_name.replace(".", "_")
        if model_name in list(self.o_model_manager.GetNames()):
            model_name = generate_unique_name(model_name, n=2)
        num_terminal = int(os.path.splitext(input_file)[1].lower().strip(".sp"))
        # with open_file(touchstone_full_path, "r") as f:
        # port_names = _parse_ports_name(f, num_terminal)

        port_names = []
        with open_file(input_file, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith(("!", "#", "")):
                    if "Port" in line and "=" in line and "Impedance" not in line:
                        port_names.append(line.split("=")[-1].strip().replace(" ", "_").strip("[]"))
                else:
                    break
        image_subcircuit_path = ""
        bmp_file_name = ""
        if show_bitmap:
            image_subcircuit_path = os.path.join(self._app.desktop_install_dir, "syslib", "Bitmaps", "nport.bmp")
            bmp_file_name = os.path.basename(image_subcircuit_path)

        if not port_names:
            port_names = ["Port" + str(i + 1) for i in range(num_terminal)]
        arg = [
            "NAME:" + model_name,
            "Name:=",
            model_name,
            "ModTime:=",
            0,
            "Library:=",
            "",
            "LibLocation:=",
            "Project",
            "ModelType:=",
            "nport",
            "Description:=",
            "",
            "ImageFile:=",
            image_subcircuit_path,
            "SymbolPinConfiguration:=",
            0,
            ["NAME:PortInfoBlk"],
            ["NAME:PortOrderBlk"],
            "filename:=",
            input_file,
            "numberofports:=",
            num_terminal,
            "sssfilename:=",
            "",
            "sssmodel:=",
            False,
            "PortNames:=",
            port_names,
            "domain:=",
            "frequency",
            "datamode:=",
            "Link",
            "devicename:=",
            "",
            "SolutionName:=",
            "",
            "displayformat:=",
            "MagnitudePhase",
            "datatype:=",
            "SMatrix",
            [
                "NAME:DesignerCustomization",
                "DCOption:=",
                0,
                "InterpOption:=",
                0,
                "ExtrapOption:=",
                1,
                "Convolution:=",
                0,
                "Passivity:=",
                0,
                "Reciprocal:=",
                False,
                "ModelOption:=",
                "",
                "DataType:=",
                1,
            ],
            [
                "NAME:NexximCustomization",
                "DCOption:=",
                3,
                "InterpOption:=",
                1,
                "ExtrapOption:=",
                3,
                "Convolution:=",
                0,
                "Passivity:=",
                0,
                "Reciprocal:=",
                False,
                "ModelOption:=",
                "",
                "DataType:=",
                2,
            ],
            [
                "NAME:HSpiceCustomization",
                "DCOption:=",
                1,
                "InterpOption:=",
                2,
                "ExtrapOption:=",
                3,
                "Convolution:=",
                0,
                "Passivity:=",
                0,
                "Reciprocal:=",
                False,
                "ModelOption:=",
                "",
                "DataType:=",
                3,
            ],
            "NoiseModelOption:=",
            "External",
        ]
        self.o_model_manager.Add(arg)
        arg = [
            "NAME:" + model_name,
            "Info:=",
            [
                "Type:=",
                10,
                "NumTerminals:=",
                num_terminal,
                "DataSource:=",
                "",
                "ModifiedOn:=",
                1618569625,
                "Manufacturer:=",
                "",
                "Symbol:=",
                "",
                "ModelNames:=",
                "",
                "Footprint:=",
                "",
                "Description:=",
                "",
                "InfoTopic:=",
                "",
                "InfoHelpFile:=",
                "",
                "IconFile:=",
                bmp_file_name,
                "Library:=",
                "",
                "OriginalLocation:=",
                "Project",
                "IEEE:=",
                "",
                "Author:=",
                "",
                "OriginalAuthor:=",
                "",
                "CreationDate:=",
                1618569625,
                "ExampleFile:=",
                "",
                "HiddenComponent:=",
                0,
                "CircuitEnv:=",
                0,
                "GroupID:=",
                0,
            ],
            "CircuitEnv:=",
            0,
            "Refbase:=",
            "S",
            "NumParts:=",
            1,
            "ModSinceLib:=",
            False,
        ]
        for i in range(num_terminal):
            arg.append("Terminal:=")
            arg.append([port_names[i], port_names[i], "A", False, i, 1, "", "Electrical", "0"])
        arg.append("CompExtID:=")
        arg.append(5)
        arg.append(
            [
                "NAME:Parameters",
                "MenuProp:=",
                ["CoSimulator", "SD", "", "Default", 0],
                "ButtonProp:=",
                ["CosimDefinition", "SD", "", "Edit", "Edit", 40501, "ButtonPropClientData:=", []],
            ]
        )
        arg.append(
            [
                "NAME:CosimDefinitions",
                [
                    "NAME:CosimDefinition",
                    "CosimulatorType:=",
                    102,
                    "CosimDefName:=",
                    "Default",
                    "IsDefinition:=",
                    True,
                    "Connect:=",
                    True,
                    "ModelDefinitionName:=",
                    model_name,
                    "ShowRefPin2:=",
                    2,
                    "LenPropName:=",
                    "",
                ],
                "DefaultCosim:=",
                "Default",
            ]
        )

        self.o_component_manager.Add(arg)
        return model_name

    @pyaedt_function_handler()
    def create_touchstone_component(
        self,
        model_name,
        location=None,
        angle=0,
        show_bitmap=True,
    ):
        """Create a component from a Touchstone model.

        Parameters
        ----------
        model_name : str
            Name of the Touchstone model or full path to touchstone file.
            If full touchstone is provided then, new model will be created.
        location : list of float, optional
            Position on the X  and Y axis.
        angle : float, optional
            Angle rotation in degrees. The default is ``0``.
        show_bitmap : bool, optional
            Show bitmap image of schematic component.
            The default value is ``True``.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.circuits.object_3d_circuit.CircuitComponent`
            Circuit Component Object.

        References
        ----------
        >>> oModelManager.Add
        >>> oComponentManager.Add
        >>> oEditor.CreateComponent

        Examples
        --------

        >>> from ansys.aedt.core import Circuit
        >>> cir = Circuit()
        >>> comps = cir.modeler.components
        >>> s_parameter_path = os.path.join("your_path", "s_param_file_name.s4p")
        >>> circuit_comp = comps.create_touchstone_component(s_parameter_path, location=[0.0, 0.0], show_bitmap=False)
        """
        if location is None:
            location = []
        xpos, ypos = self._get_location(location)
        id = self.create_unique_id()
        if os.path.exists(model_name):
            model_name = self.create_model_from_touchstone(model_name, show_bitmap=show_bitmap)
        arg1 = ["NAME:ComponentProps", "Name:=", model_name, "Id:=", str(id)]
        arg2 = ["NAME:Attributes", "Page:=", 1, "X:=", xpos, "Y:=", ypos, "Angle:=", angle, "Flip:=", False]
        id = self.oeditor.CreateComponent(arg1, arg2)
        id = int(id.split(";")[1])
        self.add_id_to_component(id)
        return self.components[id]

    @pyaedt_function_handler(inst_name="name")
    def create_component(
        self,
        name=None,
        component_library="Resistors",
        component_name="RES_",
        location=None,
        angle=0,
        use_instance_id_netlist=False,
        global_netlist_list=None,
        page=1,
    ):
        """Create a component from a library.

        Parameters
        ----------
        name : str, optional
            Name of the instance. The default is ``None.``
        component_library : str, optional
            Name of the component library. The default is ``""``.
        component_name : str, optional
            Name of component in the library. The default is ``"RES"``.
        location : list of float, optional
            Position on the X axis and Y axis.
            The default is ``None``, in which case the component is placed in [0, 0].
        angle : optional
            Angle rotation in degrees. The default is ``0``.
        use_instance_id_netlist : bool, optional
            Whether to enable the instance ID in the net list.
            The default is ``False``.
        global_netlist_list : list, optional
            The default is ``None``, in which case an empty list is passed.
        page: int, optional
            Schematic page number. The default value is ``1``.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.circuits.object_3d_circuit.CircuitComponent`
            Circuit Component Object.

        References
        ----------
        >>> oEditor.CreateComponent

        Examples
        --------

        >>> from ansys.aedt.core import TwinBuilder
        >>> aedtapp = TwinBuilder()
        >>> cmp = aedtapp.modeler.schematic.create_component(component_library="",component_name="ExcitationComponent")
        >>> cmp.set_property("ShowPin",True)
        >>> aedtapp.release_desktop(True, True)
        """
        id = self.create_unique_id()
        if component_library:
            inst_name = self.design_libray + "\\" + component_library + ":" + component_name
        else:
            inst_name = component_name
        arg1 = ["NAME:ComponentProps", "Name:=", inst_name, "Id:=", str(id)]
        xpos, ypos = self._get_location(location)
        angle = math.pi * angle / 180
        arg2 = ["NAME:Attributes", "Page:=", page, "X:=", xpos, "Y:=", ypos, "Angle:=", angle, "Flip:=", False]
        id = self.oeditor.CreateComponent(arg1, arg2)
        id = int(id.split(";")[1])
        # self.refresh_all_ids()
        self.add_id_to_component(id)
        if name:
            self.components[id].set_property("InstanceName", name)
        if use_instance_id_netlist:
            self.enable_use_instance_name(component_library, component_name)
        elif global_netlist_list:
            self.enable_global_netlist(component_name, global_netlist_list)
        return self.components[id]

    @pyaedt_function_handler(component_name="assignment")
    def disable_data_netlist(self, assignment):
        """Disable the Nexxim global net list.

        Parameters
        ----------
        assignment : str
            Name of the component.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oComponentManager.GetData
        >>> oComponentManager.Edit
        """
        name = assignment

        properties = self.o_component_manager.GetData(name)
        if len(properties) > 0:
            nexxim = list(properties[len(properties) - 1][1])
            for el in nexxim:
                if el == "Data:=":
                    nexxim_data = list(nexxim[nexxim.index(el) + 1])
                    nexxim_data[1] = ""
                    nexxim[nexxim.index(el) + 1] = nexxim_data
        self.o_component_manager.Edit(
            name, ["Name:" + assignment, ["NAME:CosimDefinitions", nexxim, "DefaultCosim:=", "DefaultNetlist"]]
        )
        return True

    @pyaedt_function_handler(component_name="assignment")
    def enable_global_netlist(self, assignment, global_netlist_list=None):
        """Enable Nexxim global net list.

        Parameters
        ----------
        assignment : str
            Name of the component.
        global_netlist_list : list
            A list of lines to include. The default is ``None``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oComponentManager.GetData
        >>> oComponentManager.Edit
        """
        if global_netlist_list is None:
            global_netlist_list = []

        name = assignment

        properties = self.o_component_manager.GetData(name)
        if len(properties) > 0:
            nexxim = list(properties[len(properties) - 1][1])
            for el in nexxim:
                if el == "GRef:=":
                    nexxim_data = list(nexxim[nexxim.index(el) + 1])
                    nexxim_data[1] = "\n".join(global_netlist_list).replace("\\", "/")
                    nexxim[nexxim.index(el) + 1] = nexxim_data
        self.o_component_manager.Edit(
            name,
            ["Name:" + assignment, ["NAME:CosimDefinitions", nexxim, "DefaultCosim:=", "DefaultNetlist"]],
        )
        return True

    @pyaedt_function_handler(symbol_name="name", pin_lists="pins")
    def create_symbol(self, name, pins):
        """Create a symbol.

        Parameters
        ----------
        name : str
            Name of the symbol.
        pins : list
            List of the pins.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oSymbolManager.Add
        """
        numpins = len(pins)
        h = int(numpins / 2)
        x1 = 0
        y2 = 0
        x2 = 0.00508
        y1 = 0.00254 * (h + 3)
        xp = -0.00254
        yp = 0.00254 * (h + 2)
        angle = 0
        arg = [
            "NAME:" + name,
            "ModTime:=",
            1591858230,
            "Library:=",
            "",
            "ModSinceLib:=",
            False,
            "LibLocation:=",
            "Project",
            "HighestLevel:=",
            1,
            "Normalize:=",
            True,
            "InitialLevels:=",
            [0, 1],
            ["NAME:Graphics"],
        ]
        self.o_symbol_manager.Add(arg)

        id = 2
        i = 1
        id += 2
        r = numpins - (h * 2)
        for pin in pins:
            arg.append(
                [
                    "NAME:PinDef",
                    "Pin:=",
                    [pin, xp, yp, angle, "N", 0, 0.00254, False, 0, True, "", False, False, pin, True],
                ]
            )
            if i == (h + r):
                yp = 0.00254 * (h + 2)
                xp = 0.00762
                angle = math.pi
            else:
                yp -= 0.00254
            id += 2
            i += 1

        arg.append(
            [
                "NAME:Graphics",
                ["NAME:1", "Rect:=", [0, 0, 0, 0, (x1 + x2) / 2, (y1 + y2) / 2, x2 - x1, y1 - y2, 0, 0, 8192]],
            ]
        )
        self.o_symbol_manager.EditWithComps(name, arg, [])
        return True

    @pyaedt_function_handler()
    def enable_use_instance_name(self, component_library="", component_name="RES_"):
        """Enable the use of the instance name.

        Parameters
        ----------
        component_library : str, optional
             Name of the component library. The default is ``""``.
        component_name : str, optional
             Name of the component. The default is ``"RES_"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oComponentManager.GetData
        >>> oComponentManager.Edit
        """
        if component_library:
            name = self.design_libray + "\\" + component_library + ":" + component_name
        else:
            name = component_name

        properties = self.o_component_manager.GetData(name)
        if len(properties) > 0:
            nexxim = list(properties[len(properties) - 1][1])
            for el in nexxim:
                if el == "Data:=":
                    nexxim_data = list(nexxim[nexxim.index(el) + 1])
                    netlist = nexxim_data[1]
                    if "@InstanceName" not in netlist[:15]:
                        newnetlist = "@InstanceName" + netlist[4:]
                        nexxim_data[1] = newnetlist
                    nexxim[nexxim.index(el) + 1] = nexxim_data
                elif el == "GRef:=":
                    nexxim_data = list(nexxim[nexxim.index(el) + 1])
                    nexxim[nexxim.index(el) + 1] = nexxim_data
        self.o_component_manager.Edit(
            name,
            ["Name:" + component_name, ["NAME:CosimDefinitions", nexxim, "DefaultCosim:=", "DefaultNetlist"]],
        )
        return True

    @pyaedt_function_handler()
    def refresh_all_ids(self):
        """Refresh all IDs and return the number of components.

        References
        ----------
        >>> oEditor.GetAllElements()
        """
        obj = self.oeditor.GetAllElements()
        if not obj:
            obj = []
        obj = [i for i in obj if "Wire" not in i[:4]]
        for el in obj:
            if not self.get_obj_id(el):
                name = el.split(";")
                if len(name) > 1:
                    o = CircuitComponent(self, tabname=self.tab_name)
                    o.name = name[0]
                    if len(name) == 2:
                        o.schematic_id = name[1]
                        objID = int(o.schematic_id)
                    else:
                        o.id = int(name[1])
                        o.schematic_id = name[2]
                        objID = o.id
                    self.components[objID] = o
        return len(self.components)

    @pyaedt_function_handler()
    def add_id_to_component(self, id):
        """Add an ID to a component.

        Parameters
        ----------
        id : int
            ID to assign to the component.

        Returns
        -------
        int
            Number of components.

        """
        obj = self.oeditor.GetAllElements()
        for el in obj:
            name = el.split(";")
            if len(name) > 1 and str(id) == name[1]:
                o = CircuitComponent(self, tabname=self.tab_name)
                o.name = name[0]
                if len(name) > 2:
                    o.id = int(name[1])
                    o.schematic_id = int(name[2])
                    objID = o.id
                else:
                    o.schematic_id = int(name[1])
                    objID = o.schematic_id
                self.components[objID] = o

        return len(self.components)

    @pyaedt_function_handler(objname="assignment")
    def get_obj_id(self, assignment):
        """Retrieve the ID of an object.

        Parameters
        ----------
        assignment : str
            Name of the object.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        for el in self.components:
            if self.components[el].name == assignment:
                return el
        return None

    @pyaedt_function_handler(partid="assignment")
    def get_pins(self, assignment):
        """Retrieve one or more pins.

        Parameters
        ----------
        assignment : int or str
            One or more IDs or names for the pins to retrieve.

        Returns
        -------
        type
            Pin with properties.

        References
        ----------
        >>> oEditor.GetComponentPins
        """
        if isinstance(assignment, CircuitComponent):
            pins = self.oeditor.GetComponentPins(assignment.composed_name)
        elif isinstance(assignment, str):
            pins = self.oeditor.GetComponentPins(assignment)
            # pins = self.oeditor.GetComponentPins(partid)
        else:
            pins = self.oeditor.GetComponentPins(self.components[assignment].composed_name)
            # pins = self.oeditor.GetComponentPins(self.components[partid].composed_name)
        return list(pins)

    @pyaedt_function_handler(partid="assignment", pinname="pin")
    def get_pin_location(self, assignment, pin):
        """Retrieve the location of a pin.

        Parameters
        ----------
        assignment : int
            ID of the part.
        pin :
            Name of the pin.

        Returns
        -------
        List
            List of axis values ``[x, y]``.

        References
        ----------
        >>> oEditor.GetComponentPinLocation

        """
        if isinstance(assignment, str):
            x = self.oeditor.GetComponentPinLocation(assignment, pin, True)
            y = self.oeditor.GetComponentPinLocation(assignment, pin, False)
        else:
            x = self.oeditor.GetComponentPinLocation(self.components[assignment].composed_name, pin, True)
            y = self.oeditor.GetComponentPinLocation(self.components[assignment].composed_name, pin, False)
        return self._convert_point_to_units([x, y])

    @pyaedt_function_handler()
    def number_with_units(self, value, units=None):
        """Convert a number to a string with units. If value is a string, it's returned as is.

        .. deprecated:: 0.14.0
           Use :func:`value_with_units` in Analysis class instead.

        Parameters
        ----------
        value : float, int, str
            Input  number or string.
        units : optional
            Units for formatting. The default is ``None``, which uses ``"meter"``.

        Returns
        -------
        str
           String concatenating the value and unit.

        """
        return self._app.value_with_units(value, units)

    @pyaedt_function_handler(points_array="points", line_width="width")
    def create_line(self, points, color=0, width=0):
        """Draw a graphical line.

        Parameters
        ----------
        points : list
            A nested list of point coordinates. For example,
            ``[[x1, y1], [x2, y2], ...]``.
        color : string or 3 item list, optional
            Color or the line. The default is ``"0"``.
        width : float, optional
            Width of the line. The default is ``0``.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.object_3dcircuit.Line`
            Line Object.

        >>> oEditor.CreateLine
        """
        points = [str(tuple(self._convert_point_to_meter(i))) for i in points]
        id = self.create_unique_id()
        return self.oeditor.CreateLine(
            ["NAME:LineData", "Points:=", points, "LineWidth:=", width, "Color:=", color, "Id:=", id],
            ["NAME:Attributes", "Page:=", 1],
        )

    @pyaedt_function_handler(points_array="points", wire_name="name")
    def create_wire(self, points, name="", page=1):
        """Create a wire.

        Parameters
        ----------
        points : list
            A nested list of point coordinates. For example,
            ``[[x1, y1], [x2, y2], ...]``.
        name : str, optional
            Name of the wire. Default value is ``""``.
        page: int, optional
            Schematics page number. The default value is ``1``.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.object_3dcircuit.Wire`
            Wire Object.

        References
        ----------
        >>> oEditor.CreateWire
        """
        points = [str(tuple(self._convert_point_to_meter(i))) for i in points]
        wire_id = self.create_unique_id()
        arg1 = ["NAME:WireData", "Name:=", name, "Id:=", wire_id, "Points:=", points]
        arg2 = ["NAME:Attributes", "Page:=", page]
        try:
            wire_id = self.oeditor.CreateWire(arg1, arg2)
            w = Wire(self._modeler, composed_name=wire_id)
            if ":" in wire_id.split(";")[1]:
                wire_id = int(wire_id.split(";")[1].split(":")[0])
            else:
                wire_id = int(wire_id.split(";")[1])
            if not name:
                name = generate_unique_name("Wire")
            w.name = name
            w.id = int(wire_id)
            return w
        except Exception:
            return False


class ComponentInfo(object):
    """Manages Circuit Catalog info."""

    def __init__(self, name, component_manager, file_name, component_library):
        self._component_manager = component_manager
        self.file_name = file_name
        self.name = name
        self.component_library = component_library
        self._props = None

    @property
    def props(self):
        """Retrieve the component properties."""
        if not self._props:
            self._props = load_keyword_in_aedt_file(self.file_name, self.name)
        return self._props

    @pyaedt_function_handler(inst_name="assignment")
    def place(self, assignment, location=None, angle=0, use_instance_id_netlist=False):
        """Create a component from a library.

        Parameters
        ----------
        assignment : str, optional
            Name of the instance. The default is ``None.``
        location : list of float, optional
            Position on the X axis and Y axis.
        angle : optional
            Angle rotation in degrees. The default is ``0``.
        use_instance_id_netlist : bool, optional
            Whether to enable the instance ID in the net list.
            The default is ``False``.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.circuits.object_3d_circuit.CircuitComponent`
            Circuit Component Object.

        References
        ----------
        >>> oEditor.CreateComponent
        """
        if location is None:
            location = []
        return self._component_manager.create_component(
            name=assignment,
            component_library=self.component_library,
            component_name=self.name,
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )


class ComponentCatalog(object):
    """Indexes Circuit Sys Catalog."""

    @pyaedt_function_handler()
    def __getitem__(self, compname):
        """Get component from name.

        Parameters
        ----------
        compname : str
            ID or name of the object.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.primitivesCircuit.ComponentInfo`
            Circuit Component Info.

        """
        items = self.find_components("*" + compname)
        if items and len(items) == 1:
            return self.components[items[0]]
        elif len(items) > 1:
            self._component_manager._logger.warning("Multiple components found.")
            return None
        else:
            self._component_manager._logger.warning("Component not found.")
            return None

    def __init__(self, component_manager):
        self._component_manager = component_manager
        self._app = self._component_manager._app
        self.components = {}
        self._index_components()

    @pyaedt_function_handler()
    def _index_components(self, library_path=None):
        if library_path:
            sys_files = recursive_glob(library_path, "*.aclb")
            root = os.path.normpath(library_path).split(os.path.sep)[-1]
        else:
            sys_files = recursive_glob(os.path.join(self._app.syslib, self._component_manager.design_libray), "*.aclb")
            root = os.path.normpath(self._app.syslib).split(os.path.sep)[-1]
        for file in sys_files:
            comps1 = load_keyword_in_aedt_file(file, "DefInfo")
            comps2 = load_keyword_in_aedt_file(file, "CompInfo")
            comps = comps1.get("DefInfo", {})
            comps.update(comps2.get("CompInfo", {}))
            for compname, comp_value in comps.items():
                root_name, ext = os.path.splitext(os.path.normpath(file))
                full_path = root_name.split(os.path.sep)
                id = full_path.index(root) + 1
                if self._component_manager.design_libray in full_path[id:]:
                    id += 1
                comp_lib = "\\".join(full_path[id:]) + ":" + compname
                self.components[comp_lib] = ComponentInfo(
                    compname, self._component_manager, file, comp_lib.split(":")[0]
                )

    @pyaedt_function_handler()
    def find_components(self, filter_str="*"):
        """Find all components with given filter wildcards.

        Parameters
        ----------
        filter_str : str
            Filter String to search.

        Returns
        -------
        list
            List of matching component names.

        """
        c = []
        for el in list(self.components.keys()):
            if filter_string(el, filter_str):
                c.append(el)
        return c
