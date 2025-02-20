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

from pathlib import Path
import re
import secrets
import time
import warnings

from ansys.aedt.core.application.variables import decompose_variable_value
from ansys.aedt.core.generic.constants import AEDT_UNITS
from ansys.aedt.core.generic.general_methods import generate_unique_name
from ansys.aedt.core.generic.general_methods import is_linux
from ansys.aedt.core.generic.general_methods import open_file
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.generic.load_aedt_file import load_keyword_in_aedt_file
from ansys.aedt.core.generic.settings import settings
from ansys.aedt.core.modeler.circuits.object_3d_circuit import CircuitComponent
from ansys.aedt.core.modeler.circuits.primitives_circuit import CircuitComponents
from ansys.aedt.core.modeler.circuits.primitives_circuit import ComponentCatalog
from ansys.aedt.core.modules.boundary.circuit_boundary import Excitations


class NexximComponents(CircuitComponents):
    """Manages circuit components for Nexxim.

    Parameters
    ----------
    modeler : :class:`ansys.aedt.core.modeler.schematic.ModelerNexxim`
        Inherited parent object.

    Examples
    --------
    >>> from ansys.aedt.core import Circuit
    >>> aedtapp = Circuit()
    >>> prim = aedtapp.modeler.schematic
    """

    @property
    def design_libray(self):
        """Design library."""
        return "Nexxim Circuit Elements"

    @property
    def tab_name(self):
        """Tab name."""
        return "PassedParameterTab"

    @pyaedt_function_handler()
    def __getitem__(self, partname):
        """Get the object ID if the part name is an integer or the object name if it is a string.

        Parameters
        ----------
        partname : int or str
            Part ID or object name.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.circuits.object_3d_circuit.CircuitComponent`
            Circuit Component Object.
        """
        if isinstance(partname, int):
            return self.components[partname]
        for el in self.components:
            cmp = self.components[el]
            if (
                cmp.name == partname
                or cmp.composed_name == partname
                or el == partname
                or cmp.refdes == partname
                or cmp.parameters.get("InstanceName", "") == partname
            ):
                return self.components[el]
        if isinstance(partname, CircuitComponent):
            return partname
        return None

    @property
    def _logger(self):
        return self._app.logger

    def __init__(self, modeler):
        CircuitComponents.__init__(self, modeler)
        self._app = modeler._app
        self._modeler = modeler
        self._currentId = 0
        self._components_catalog = None

    @pyaedt_function_handler()
    def get_component(self, name):
        """Get a component.

        Parameters
        ----------
        name : str, int
            Name of the component.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.circuits.object_3d_circuit.CircuitComponent`
             Circuit Component Object.
        """
        if name in self.components:
            return self.components[name]
        else:
            for comp in self.components.values():
                if (
                    comp.name == name
                    or comp.name.split("@")[-1] == name
                    or comp.composed_name == name
                    or comp.schematic_id == name
                    or comp.id == name
                ):
                    return comp
        self.logger.error("Component not found : %s", name)
        return False

    @pyaedt_function_handler()
    def delete_component(self, name):
        """Get and delete a component.

        Parameters
        ----------
        name : str, int
            Name of the component.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        cmp = self.get_component(name)
        if cmp:
            cmp.delete()
            return True
        return False

    @property
    def components_catalog(self):
        """System library component catalog with all information.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.primitivesCircuit.ComponentCatalog`
        """
        if not self._components_catalog:
            self._components_catalog = ComponentCatalog(self)
        return self._components_catalog

    @pyaedt_function_handler()
    def create_subcircuit(self, location=None, angle=None, name=None, nested_subcircuit_id=None):
        """Add a new Circuit subcircuit to the design.

        Parameters
        ----------
        location : list of float, optional
            Position on the X axis and Y axis.
        angle : float, optional
            Angle rotation in degrees. The default is ``None``.
        name : str, optional
            Name of the design. The default is ``None``, in which case
            a unique name is generated.
        nested_subcircuit_id : str, optional
            ID of the nested subcircuit.
            Example `"U1"`.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.circuits.object_3d_circuit.CircuitComponent`
            Circuit Component Object when successful or ``False`` when failed.

        Examples
        --------
        >>> from ansys.aedt.core import Circuit
        >>> cir = Circuit()
        """
        if not name:
            name = generate_unique_name("Circuit")

        secure_random = secrets.SystemRandom()
        if nested_subcircuit_id:
            parent_name = (
                f"{self._app.design_name.split('/')[0]}:{nested_subcircuit_id}:{secure_random.randint(1, 10000)}"
            )
        else:
            parent_name = f'{self._app.design_name.split("/")[0]}:{":U" + str(secure_random.randint(1, 10000))}'

        self._app.odesign.InsertDesign("Circuit Design", name, "", parent_name)
        if is_linux and settings.aedt_version == "2024.1":  # pragma: no cover
            time.sleep(1)
            self._app.desktop_class.close_windows()
        if nested_subcircuit_id:
            pname = f"{self._app.design_name.split('/')[0]}:{nested_subcircuit_id}"
            odes = self._app.desktop_class.active_design(self._app.oproject, pname)
            oed = odes.SetActiveEditor("SchematicEditor")
            if is_linux and settings.aedt_version == "2024.1":  # pragma: no cover
                time.sleep(1)
                self._app.desktop_class.close_windows()
            objs = oed.GetAllElements()
            match = [i for i in objs if name in i]
            o = CircuitComponent(self, tabname=self.tab_name, custom_editor=oed)
            name = match[0].split(";")
            o.name = name[0]
            o.schematic_id = name[2]
            o.id = int(name[1])
            return o
        self.refresh_all_ids()
        for el in self.components:
            if name in self.components[el].composed_name:
                if location:
                    self.components[el].location = [
                        i / AEDT_UNITS["Length"][self.schematic_units] for i in self._get_location(location)
                    ]
                if angle is not None:
                    self.components[el].angle = angle
                return self.components[el]
        return False

    @pyaedt_function_handler(component="assignment")
    def duplicate(self, assignment, location=None, angle=0, flip=False):  # pragma: no cover
        """Add a new subcircuit to the design.

        .. note::
            This works only in graphical mode.

        Parameters
        ----------
        assignment : :class:`ansys.aedt.core.modeler.circuits.object_3d_circuit.CircuitComponent`
            Component to duplicate.
        location : list of float, optional
            Position on the X axis and Y axis.
        angle : float, optional
            Angle rotation in degrees. The default is ``0``.
        flip : bool, optional
            Whether the component should be flipped. The default value is ``False``.

        Returns
        -------
        ::class:`ansys.aedt.core.modeler.circuits.object_3d_circuit.CircuitComponent` Circuit Component Object
        when successful or ``False`` when failed.
        """
        comp_names = []
        if isinstance(assignment, CircuitComponent):
            comp_names.append(assignment.composed_name)
        else:
            comp_names.append(assignment)
        self._modeler.oeditor.Copy(["NAME:Selections", "Selections:=", comp_names])
        location = self._get_location(location)
        self._modeler.oeditor.Paste(
            ["NAME:Attributes", "Page:=", 1, "X:=", location[0], "Y:=", location[1], "Angle:=", angle, "Flip:=", flip]
        )
        ids = [id for id in list(self.components.keys())]
        self.refresh_all_ids()
        new_ids = [id for id in list(self.components.keys()) if id not in ids]
        if new_ids:
            return self.components[new_ids[0]]
        return False

    @pyaedt_function_handler(components_to_connect="assignment")
    def connect_components_in_series(self, assignment, use_wire=True):
        """Connect schematic components in series.

        Parameters
        ----------
        assignment : list[:class:`ansys.aedt.core.modeler.circuits.object_3d_circuit.CircuitComponent`]
           List of Components to connect. It can be a list of objects or component names.
        use_wire : bool, optional
            Whether to use wires or a page port to connect the pins.
            The default is ``True``, in which case wires are used. Note
            that if wires are not well placed, shorts can result.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------
        >>> from ansys.aedt.core import Circuit
        >>> circuit = Circuit()
        >>> circuit.modeler.schematic_units = "mil"
        >>> myind = circuit.modeler.schematic.create_inductor(value=1e-9,location=[0,0])
        >>> myres = circuit.modeler.schematic.create_resistor(value=50,location=[100, 2000])
        >>> circuit.modeler.schematic.connect_components_in_series([myind, myres])
        """
        comps = []
        for component in assignment:
            if isinstance(component, (CircuitComponent, Excitations)):
                comps.append(component)
            else:
                for id, cmp in self.components.items():
                    if component in [cmp.id, cmp.name, cmp.composed_name]:
                        comps.append(cmp)
                        break
        if len(comps) < 2:
            raise RuntimeError("At least two components have to be passed.")
        i = 0
        while i < (len(comps) - 1):
            comps[i].pins[-1].connect_to_component(comps[i + 1].pins[0], use_wire=use_wire)
            i += 1
        return True

    @pyaedt_function_handler(components_to_connect="assignment")
    def connect_components_in_parallel(self, assignment):
        """Connect schematic components in parallel.

        Parameters
        ----------
        assignment : list[:class:`ansys.aedt.core.modeler.circuits.object_3d_circuit.CircuitComponent`]
           List of Components to connect. It can be a list of objects or component names.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------
        >>> from ansys.aedt.core import Circuit
        >>> circuit = Circuit()
        >>> myind = circuit.modeler.schematic.create_inductor("L100",1e-9)
        >>> myres = circuit.modeler.schematic.create_resistor("R100",50)
        >>> circuit.modeler.schematic.connect_components_in_parallel([myind, myres.composed_name])
        """
        comps = []
        for component in assignment:
            if isinstance(component, CircuitComponent):
                comps.append(component)
            else:
                for id, cmp in self.components.items():
                    if component in [cmp.id, cmp.name, cmp.composed_name]:
                        comps.append(cmp)
                        break
        if len(comps) < 2:
            raise RuntimeError("At least two components have to be passed.")
        comps[0].pins[0].connect_to_component([i.pins[0] for i in comps[1:]])
        terminal_to_connect = [cmp for cmp in comps if len(cmp.pins) >= 2]
        if len(terminal_to_connect) > 1:
            terminal_to_connect[0].pins[1].connect_to_component([i.pins[1] for i in terminal_to_connect[1:]])
        return True

    @pyaedt_function_handler(sourcename="name")
    def add_subcircuit_3dlayout(self, name):
        """Add a subcircuit from a HFSS 3DLayout.

        Parameters
        ----------
        name : str
            Name of the source design.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.circuits.object_3d_circuit.CircuitComponent`
            Circuit Component Object.

        References
        ----------
        >>> oProject.CopyDesign
        >>> oEditor.PasteDesign
        """
        self._app._oproject.CopyDesign(name)
        self.oeditor.PasteDesign(
            0,
            ["NAME:Attributes", "Page:=", 1, "X:=", 0, "Y:=", 0, "Angle:=", 0, "Flip:=", False],
        )
        self.refresh_all_ids()
        for el in self.components:
            if name in self.components[el].composed_name:
                return self.components[el]
        return False

    @pyaedt_function_handler()
    def create_field_model(self, design_name, solution_name, pin_names, model_type="hfss"):
        """Create a field model.

        Parameters
        ----------
        design_name : str
            Name of the design.
        solution_name : str
            Name  of the solution.
        pin_names : list
            List of the pin names.
        model_type : str, optional
            Type of the model. The default is ``"hfss"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModelManager.Add
        >>> oComponentManager.Add
        """
        id = self.create_unique_id()
        component_name = design_name + "_" + str(id)
        arg = [
            "NAME: " + component_name,
            "Name:=",
            component_name,
            "ModTime:=",
            1589868932,
            "Library:=",
            "",
            "LibLocation:=",
            "Project",
            "ModelType:=",
            model_type,
            "Description:=",
            "",
            "ImageFile:=",
            "",
            "SymbolPinConfiguration:=",
            0,
            ["NAME:PortInfoBlk"],
            ["NAME:PortOrderBlk"],
            "DesignName:=",
            design_name,
            "SolutionName:=",
            solution_name,
            "NewToOldMap:=",
            [],
            "OldToNewMap:=",
            [],
            "PinNames:=",
            pin_names,
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
            "WB_SystemID:=",
            design_name,
            "IsWBModel:=",
            False,
            "filename:=",
            "",
            "numberofports:=",
            len(pin_names),
            "Simulate:=",
            False,
            "CloseProject:=",
            False,
            "SaveProject:=",
            True,
            "InterpY:=",
            True,
            "InterpAlg:=",
            "auto",
            "IgnoreDepVars:=",
            False,
            "Renormalize:=",
            False,
            "RenormImpedance:=",
            50,
        ]
        self.o_model_manager.Add(arg)
        arg = [
            "NAME:" + component_name,
            "Info:=",
            [
                "Type:=",
                8,
                "NumTerminals:=",
                len(pin_names),
                "DataSource:=",
                "",
                "ModifiedOn:=",
                1589868933,
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
                "",
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
                1589868933,
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
        id = 2
        for pn in pin_names:
            arg.append("Terminal:=")
            arg.append([pn, pn, "A", False, id, 1, "", "Electrical", "0"])
            id += 1
        arg.append(["NAME:Properties", "TextProp:=", ["Owner", "RD", "", model_type.upper()]])
        arg.append("CompExtID:="), arg.append(5)
        arg.append(
            [
                "NAME:Parameters",
                "TextProp:=",
                ["ModelName", "RD", "", "FieldSolver"],
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
                    103,
                    "CosimDefName:=",
                    "Default",
                    "IsDefinition:=",
                    True,
                    "Connect:=",
                    True,
                    "ModelDefinitionName:=",
                    component_name,
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
        self._app._odesign.AddCompInstance(component_name)
        self.refresh_all_ids()
        for el in self.components:
            if component_name in self.components[el].composed_name:
                return el, self.components[el].composed_name
        return False

    @pyaedt_function_handler(compname="name")
    def create_resistor(self, name=None, value=50, location=None, angle=0, use_instance_id_netlist=False):
        """Create a resistor.

        Parameters
        ----------
        name : str, optional
            Name of the resistor. The default is ``None``.
        value : float, optional
            Resistance in ohms. The default is ``50``.
        location : list of float, optional
            Position on the X axis and Y axis.
        angle : float, optional
            Angle rotation in degrees. The default is ``0``.
        use_instance_id_netlist : bool, optional
            Whether to use the instance ID in the net list.
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
        cmpid = self.create_component(
            name, location=location, angle=angle, use_instance_id_netlist=use_instance_id_netlist
        )

        cmpid.set_property("R", value)
        return cmpid

    @pyaedt_function_handler(compname="name")
    def create_inductor(self, name=None, value=50, location=None, angle=0, use_instance_id_netlist=False):
        """Create an inductor.

        Parameters
        ----------
        name : str, optional
            Name of the inductor. The default is ``None``.
        value : float, optional
            Inductance value. The default is ``50``.
        location : list of float, optional
            Position on the X axis and Y axis.
        angle : float, optional
            Angle rotation in degrees. The default is ``0``.
        use_instance_id_netlist : bool, optional
            Whether to use the instance ID in the net list.
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
        cmpid = self.create_component(
            name,
            component_library="Inductors",
            component_name="IND_",
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )

        cmpid.set_property("L", value)

        return cmpid

    @pyaedt_function_handler(compname="name")
    def create_capacitor(self, name=None, value=50, location=None, angle=0, use_instance_id_netlist=False):
        """Create a capacitor.

        Parameters
        ----------
        name : str, optional
            Name of the capacitor. The default is ``None``.
        value : float, optional
            Capacitor value. The default is ``50``.
        location : list of float, optional
            Position on the X axis and Y axis. The default is ``None``.
        angle : float, optional
            Angle rotation in degrees. The default is ``0``.
        use_instance_id_netlist : bool, optional
            Whether to use the instance ID in the net list.
            The default is ``False``.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.circuits.object_3d_circuit.CircuitComponent`
            Circuit Component Object.

        References
        ----------
        >>> oEditor.CreateComponent
        """
        if location == None:
            location = []

        cmpid = self.create_component(
            name,
            component_library="Capacitors",
            component_name="CAP_",
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )

        cmpid.set_property("C", value)
        return cmpid

    @pyaedt_function_handler(compname="name")
    def create_voltage_dc(self, name=None, value=1, location=None, angle=0, use_instance_id_netlist=False):
        """Create a voltage DC source.

        Parameters
        ----------
        name : str, optional
            Name of the voltage DC source. The default is ``None``.
        value : float, optional
            Voltage value. The default is ``50``.
        location : list of float, optional
            Position on the X axis and Y axis. The default is ``None``.
        angle : float, optional
            Angle rotation in degrees. The default is ``0``.
        use_instance_id_netlist : bool, optional
            Whether to use the instance ID in the net list.
            The default is ``False``.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.circuits.object_3d_circuit.CircuitComponent`
            Circuit Component Object.

        References
        ----------
        >>> oEditor.CreateComponent
        """
        if location == None:
            location = []

        cmpid = self.create_component(
            name,
            component_library="Independent Sources",
            component_name="V_DC",
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )

        cmpid.set_property("DC", value)
        return cmpid

    @pyaedt_function_handler(probe_name="name")
    def create_voltage_probe(self, name=None, location=None, angle=0, use_instance_id_netlist=False):
        """Create a voltage probe.

        Parameters
        ----------
        name : str, optional
            Name of the voltage probe. The default is ``None``.
        location : list of float, optional
            Position on the X axis and Y axis. The default is ``None``.
        angle : float, optional
            Angle rotation in degrees. The default is ``0``.
        use_instance_id_netlist : bool, optional
            Whether to use the instance ID in the net list.
            The default is ``False``.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.circuits.object_3d_circuit.CircuitComponent`
            Circuit Component Object.

        References
        ----------
        >>> oEditor.CreateComponent

        Examples
        --------
        >>> from ansys.aedt.core import Circuit
        >>> cir = Circuit()
        >>> cir.modeler.components.create_voltage_probe(name="probe")
        >>> cir.release_desktop(False, False)
        """
        return self.__create_probe(
            name=name,
            probe_type="voltage",
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )

    @pyaedt_function_handler()
    def create_current_probe(self, name=None, location=None, angle=0, use_instance_id_netlist=False):
        """Create a current probe.

        Parameters
        ----------
        name : str, optional
            Name of the current probe. The default is ``None``.
        location : list of float, optional
            Position on the X axis and Y axis. The default is ``None``.
        angle : float, optional
            Angle rotation in degrees. The default is ``0``.
        use_instance_id_netlist : bool, optional
            Whether to use the instance ID in the net list.
            The default is ``False``.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.circuits.object_3d_circuit.CircuitComponent`
            Circuit Component Object.

        References
        ----------
        >>> oEditor.CreateComponent

        Examples
        --------
        >>> from ansys.aedt.core import Circuit
        >>> cir = Circuit()
        >>> cir.modeler.components.create_current_probe(name="probe")
        >>> cir.release_desktop(False, False)
        """
        return self.__create_probe(
            name=name,
            probe_type="current",
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )

    def __create_probe(self, name=None, probe_type="voltage", location=None, angle=0.0, use_instance_id_netlist=False):
        if probe_type == "voltage":
            component_name = "VPROBE"
        elif probe_type == "current":
            component_name = "IPROBE"
        else:  # pragma: no cover
            self.logger.error("Wrong probe type assigned.")
            return False

        if location is None:
            location = []
        else:
            location = [location[0] + 0.2 * 24.4 / 1000, location[1] + 0.2 * 24.4 / 1000]

        cmpid = self.create_component(
            name,
            component_library="Probes",
            component_name=component_name,
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )
        if name:
            cmpid.set_property("InstanceName", name)
        return cmpid

    @pyaedt_function_handler(compname="name")
    def create_current_pulse(self, name=None, value_lists=None, location=None, angle=0, use_instance_id_netlist=False):
        """Create a current pulse.

        Parameters
        ----------
        name : str, optional
            Name of the current pulse. The default is ``None``.
        value_lists : list, optional
            List of values for the current pulse. The default is ``[]``.
        location : list of float, optional
            Position on the X axis and Y axis.
        angle : float, optional
            Angle rotation in degrees. The default is ``0``.
        use_instance_id_netlist : bool, optional
            Whether to use the instance ID in the net list.
            The default is ``False``.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.circuits.object_3d_circuit.CircuitComponent`
            Circuit Component Object.

        References
        ----------
        >>> oEditor.CreateComponent
        """
        if value_lists is None:
            value_lists = []
        if location is None:
            location = []
        cmpid = self.create_component(
            name,
            component_library="Independent Sources",
            component_name="I_PULSE",
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )

        if len(value_lists) > 0:
            cmpid.set_property("I1", value_lists[0])
        if len(value_lists) > 1:
            cmpid.set_property("I2", value_lists[1])
        if len(value_lists) > 2:
            cmpid.set_property("TD", value_lists[2])
        if len(value_lists) > 3:
            cmpid.set_property("TR", value_lists[3])
        if len(value_lists) > 4:
            cmpid.set_property("TF", value_lists[4])
        if len(value_lists) > 5:
            cmpid.set_property("PW", value_lists[5])
        if len(value_lists) > 6:
            cmpid.set_property("PER", value_lists[6])

        return cmpid

    @pyaedt_function_handler(compname="name")
    def create_voltage_pulse(self, name=None, value_lists=None, location=None, angle=0, use_instance_id_netlist=False):
        """Create a voltage pulse.

        Parameters
        ----------
        name : str, optional
            Name of the voltage pulse. The default is ``None``.
        value_lists : list, optional
            List of values for the voltage pulse. The default is ``[]``.
        location : list of float, optional
            Position on the X axis and Y axis.
        angle : float, optional
            Angle rotation in degrees. The default is ``0``.
        use_instance_id_netlist : bool, optional
            Whether to use the instance ID in the net list.
            The default is ``False``.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.circuits.object_3d_circuit.CircuitComponent`
            Circuit Component Object.

        References
        ----------
        >>> oEditor.CreateComponent
        """
        if value_lists is None:
            value_lists = []
        if location is None:
            location = []
        cmpid = self.create_component(
            name,
            component_library="Independent Sources",
            component_name="V_PULSE",
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )

        if len(value_lists) > 0:
            cmpid.set_property("V1", value_lists[0])
        if len(value_lists) > 1:
            cmpid.set_property("V2", value_lists[1])
        if len(value_lists) > 2:
            cmpid.set_property("TD", value_lists[2])
        if len(value_lists) > 3:
            cmpid.set_property("TR", value_lists[3])
        if len(value_lists) > 4:
            cmpid.set_property("TF", value_lists[4])
        if len(value_lists) > 5:
            cmpid.set_property("PW", value_lists[5])
        if len(value_lists) > 6:
            cmpid.set_property("PER", value_lists[6])

        return cmpid

    @pyaedt_function_handler(compname="name")
    def create_voltage_pwl(
        self, name=None, time_list=None, voltage_list=None, location=None, angle=0, use_instance_id_netlist=False
    ):
        """Create a pwl voltage source.

        Parameters
        ----------
        name : str, optional
            Name of the voltage pulse. The default is ``None``.
        time_list : list, optional
            List of time points for the pwl voltage source. The default is ``[0]``.
        voltage_list : list, optional
            List of voltages for the pwl voltage source. The default is ``[0]``.
        location : list of float, optional
            Position on the x-axis and y-xis.
        angle : float, optional
            Angle rotation in degrees. The default is ``0``.
        use_instance_id_netlist : bool, optional
            Whether to use the instance ID in the net list.
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

        cmpid = self.create_component(
            name,
            component_library="Independent Sources",
            component_name="V_PWL",
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )

        if (time_list is not None) and (voltage_list is not None):

            if len(time_list) != len(voltage_list):
                self.logger.error("The number of time points is different than the number of voltages.")
                return False
            else:
                for nr, pair in enumerate(zip(time_list, voltage_list)):
                    cmpid.set_property(name="time" + str(nr + 1), value=pair[0])
                    cmpid.set_property(name="val" + str(nr + 1), value=pair[1])

        return cmpid

    @pyaedt_function_handler(compname="name")
    def create_current_dc(self, name=None, value=1, location=None, angle=0, use_instance_id_netlist=False):
        """Create a current DC source.

        Parameters
        ----------
        name : str, optional
            Name of the current DC source. The default is ``None``.
        value : float, optional
            Current value. The default is ``1``.
        location : list of float, optional
            Position on the X axis and Y axis.
        angle : float, optional
            Angle rotation in degrees. The default is ``0``.
        use_instance_id_netlist : bool, optional
            Whether to use the instance ID in the net list.
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
        cmpid = self.create_component(
            name,
            component_library="Independent Sources",
            component_name="I_DC",
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )

        cmpid.set_property("DC", value)
        return cmpid

    def create_coupling_inductors(
        self, compname, l1, l2, value=1, location=None, angle=0, use_instance_id_netlist=False
    ):
        """Create a coupling inductor.

        Parameters
        ----------
        compname : str
            Name of the coupling inductor.
        l1 : float, optional
            Value for the first inductor.
        l2 : float, optional
            Value for the second inductor.
        value : float, optional
            Value for the coupling inductor. The default is ``1``.
        location : list of float, optional
            Position on the X axis and Y axis. The default is ``None``.
        angle : float, optional
            Angle rotation in degrees. The default is ``0``.
        use_instance_id_netlist : bool, optional
            Whether to use the instance ID in the net list.
            The default is ``False``.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.circuits.object_3d_circuit.CircuitComponent`
            Circuit Component Object.

        References
        ----------
        >>> oEditor.CreateComponent
        """
        if location == None:
            location = []

        cmpid = self.create_component(
            compname,
            component_library="Inductors",
            component_name="K_IND",
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )

        cmpid.set_property("Inductor1", l1)
        cmpid.set_property("Inductor2", l2)
        cmpid.set_property("CouplingFactor", value)
        return cmpid

    @pyaedt_function_handler(compname="name")
    def create_diode(self, name=None, model_name="required", location=None, angle=0, use_instance_id_netlist=False):
        """Create a diode.

        Parameters
        ----------
        name : str
            Name of the diode. The default is ``None``.
        model_name : str, optional
            Name of the model. The default is ``"required"``.
        location : list of float, optional
            Position on the X axis and Y axis.
        angle : float, optional
            Angle rotation in degrees. The default is ``0``.
        use_instance_id_netlist : bool, optional
            Whether to use the instance ID in the net list.
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
        cmpid = self.create_component(
            name,
            component_library="Diodes",
            component_name="DIODE_Level1",
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )

        cmpid.set_property("MOD", model_name)
        return cmpid

    @pyaedt_function_handler(compname="name")
    def create_npn(self, name=None, value=None, location=None, angle=0, use_instance_id_netlist=False):
        """Create an NPN transistor.

        Parameters
        ----------
        name : str
            Name of the NPN transistor. The default is ``None``.
        value : float, optional
            Value for the NPN transistor. The default is ``None``.
        location : list of float, optional
            Position on the X axis and Y axis.
        angle : float, optional
            Angle rotation in degrees. The default is ``0``.
        use_instance_id_netlist : bool, optional
            Whether to use the instance ID in the net list.
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
        id = self.create_component(
            name,
            component_library="BJTs",
            component_name="Level01_NPN",
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )
        if value:
            id.set_property("MOD", value)
        return id

    @pyaedt_function_handler(compname="name")
    def create_pnp(self, name=None, value=50, location=None, angle=0, use_instance_id_netlist=False):
        """Create a PNP transistor.

        Parameters
        ----------
        name : str
            Name of the PNP transistor. The default is ``None``.
        value : float, optional
            Value for the PNP transistor. The default is ``None``.
        location : list of float, optional
            Position on the X axis and Y axis.
        angle : float, optional
            Angle rotation in degrees. The default is ``0``.
        use_instance_id_netlist : bool, optional
            Whether to use the instance ID in the net list.
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
        id = self.create_component(
            name,
            component_library="BJTs",
            component_name="Level01_PNP",
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )
        if value:
            id.set_property("MOD", value)

        return id

    @pyaedt_function_handler(
        symbol_name="name", pin_lists="pins", parameter_list="parameters", parameter_value="values"
    )
    def create_new_component_from_symbol(
        self,
        name,
        pins,
        time_stamp=1591858313,
        description="",
        refbase="x",
        parameters=None,
        values=None,
        gref="",
    ):
        """Create a component from a symbol.

        Parameters
        ----------
        name : str
            Name of the symbol.
        pins : list
            List of pin names.
        time_stamp : int, optional
            UTC time stamp.
        description : str, optional
            Component description.
        refbase : str, optional
            Reference base. The default is ``"U"``.
        parameters : list
            List of parameters.
            If not provided the default is ``None``, in which case an empty list is set.
        values : list
            List of parameter values.
            If not provided the default is ``None``, in which case an empty list is set.
        gref : str, optional
            Global Reference

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModelManager.Add
        >>> oComponentManager.Add
        """
        parameters = [] if parameters is None else parameters
        values = [] if values is None else values
        arg = [
            "NAME:" + name,
            "Info:=",
            [
                "Type:=",
                0,
                "NumTerminals:=",
                len(pins),
                "DataSource:=",
                "",
                "ModifiedOn:=",
                time_stamp,
                "Manufacturer:=",
                "",
                "Symbol:=",
                name,
                "ModelNames:=",
                "",
                "Footprint:=",
                "",
                "Description:=",
                description,
                "InfoTopic:=",
                "",
                "InfoHelpFile:=",
                "",
                "IconFile:=",
                "",
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
                time_stamp,
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
            refbase,
            "NumParts:=",
            1,
            "ModSinceLib:=",
            True,
        ]

        for pin in pins:
            arg.append("Terminal:=")
            arg.append([pin, pin, "A", False, 0, 1, "", "Electrical", "0"])
        arg.append("CompExtID:=")
        arg.append(1)
        arg2 = ["NAME:Parameters"]

        for el, val in zip(parameters, values):
            if "MOD" in el:
                arg2.append("TextValueProp:=")
                arg2.append([el, "D", "", val])
            else:
                arg2.append("ValuePropNU:=")
                arg2.append([el, "D", "", str(val), 0, ""])

        arg2.append("ButtonProp:=")
        arg2.append(["CosimDefinition", "D", "", "Edit", "Edit", 40501, "ButtonPropClientData:=", []])
        arg2.append("MenuProp:=")
        arg2.append(["CoSimulator", "D", "", "DefaultNetlist", 0])

        arg.append(arg2)
        spicesintax = refbase + "@ID "
        id = 0
        while id < len(pins):
            spicesintax += "%" + str(id) + " "
            id += 1
            spicesintax += name + " "
        for el, val in zip(parameters, values):
            if "MOD" in el:
                spicesintax += f"@{el} "
            else:
                spicesintax += f"{el}=@{el} "

        arg3 = [
            "NAME:CosimDefinitions",
            [
                "NAME:CosimDefinition",
                "CosimulatorType:=",
                4,
                "CosimDefName:=",
                "DefaultNetlist",
                "IsDefinition:=",
                True,
                "Connect:=",
                True,
                "Data:=",
                ["Nexxim Circuit:=", spicesintax],
                "GRef:=",
                ["Nexxim Circuit:=", gref],
            ],
            "DefaultCosim:=",
            "DefaultNetlist",
        ]
        arg.append(arg3)
        print(arg)
        self.o_component_manager.Add(arg)
        return True

    @pyaedt_function_handler(toolNum="tool_index")
    def _get_comp_custom_settings(
        self, tool_index, dc=0, interp=0, extrap=1, conv=0, passivity=0, reciprocal="False", opt="", data_type=1
    ):
        """Retrieve custom settings for a resistor.

        Parameters
        ----------
        tool_index : int
            Tool index.

        dc :
            The default is ``0``.
        interp :
            The default is ``0``.
        extrap :
            The default is ``1``.
        conv :
            The default is ``0``.
        passivity : optional
            The default is ``0``.
        reciprocal : bool, optional
            The default is ``False``.
        opt : str, optional
            The default is ``""``.
        data_type : optional
            Type of the data. The default is ``1``.

        Returns
        -------
        list
            List of the custom settings for the resistor.

        """
        if tool_index == 1:
            custom = "NAME:DesignerCustomization"
        elif tool_index == 2:
            custom = "NAME:NexximCustomization"
        else:
            custom = "NAME:HSpiceCustomization"

        res = [
            custom,
            "DCOption:=",
            dc,
            "InterpOption:=",
            interp,
            "ExtrapOption:=",
            extrap,
            "Convolution:=",
            conv,
            "Passivity:=",
            passivity,
            "Reciprocal:=",
            reciprocal,
            "ModelOption:=",
            opt,
            "DataType:=",
            data_type,
        ]

        return res

    @pyaedt_function_handler(comp_name="name")
    def add_subcircuit_dynamic_link(
        self,
        pyaedt_app=None,
        solution_name=None,
        extrusion_length=None,
        enable_cable_modeling=True,
        default_matrix="Original",
        tline_port="",
        name=None,
    ):
        """Add a subcircuit from `HFSS`, `Q3d` or `2D Extractor` in circuit design.

        Parameters
        ----------
        pyaedt_app : :class:`ansys.aedt.core.q3d.Q3d` or :class:`ansys.aedt.core.q3d.Q2d` or
            :class:`ansys.aedt.core.q3d.Hfss`.
            pyaedt application object to include. It could be an Hfss object, a Q3d object or a Q2d.
        solution_name : str, optional
            Name of the solution and sweep. The default is ``"Setup1 : Sweep"``.
        extrusion_length : float, str, optional
            Extrusion length for 2D Models (q2d or Hfss) in model units. Default is `None`.
        enable_cable_modeling : bool, optional
            Either if the Hfss Cable modeling has to be enabled for 2D subcircuits.
        default_matrix : str, optional
            Matrix to link to the subcircuit. Default to `"Original"`. It only applies to 2D Extractor and Q3D.
        tline_port : str, optional
            Port to be used for tramsission line. Only applies to Hfss.
        name : str, optional
            Component name.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.circuits.object_3d_circuit.CircuitComponent`
            Circuit Component Object.

        References
        ----------
        >>> oModelManager.Add
        >>> oComponentManager.Add
        >>> oDesign.AddCompInstance
        >>> oDesign.AddDynamicLink
        """
        if not name:
            name = generate_unique_name(pyaedt_app.design_name)
        source_project_path = pyaedt_app.project_file
        source_design_name = pyaedt_app.design_name
        if not solution_name:
            solution_name = pyaedt_app.nominal_sweep
        self._app.odesign.AddDynamicLink(
            source_design_name,
            source_project_path,
            name,
            solution_name,
            tline_port,
            default_matrix,
            enable_cable_modeling,
            "Pyaedt Dynamic Link",
        )
        self.refresh_all_ids()
        for el in self.components:
            if name in self.components[el].composed_name:
                if extrusion_length:
                    _, units = decompose_variable_value(self.components[el].parameters["Length"])
                    self.components[el].set_property("Length", self._app.value_with_units(extrusion_length, units))
                if tline_port and extrusion_length:
                    _, units = decompose_variable_value(self.components[el].parameters["TLineLength"])
                    self.components[el].set_property("TLineLength", self._app.value_with_units(extrusion_length, units))
                return self.components[el]
        return False

    @pyaedt_function_handler()
    def _add_subcircuit_link(
        self,
        comp_name,
        pin_names,
        source_project_path,
        source_design_name,
        solution_name="Setup1 : Sweep",
        image_subcircuit_path=None,
        model_type="hfss",
        variables=None,
        extrusion_length_q2d=10,
        matrix=None,
        enable_cable_modeling=False,
        default_matrix="Original",
        simulate_solutions=False,
    ):
        """Add a subcircuit HFSS link.

        Parameters
        ----------
        comp_name : str
            Name of the subcircuit HFSS link.
        pin_names : list
            List of the pin names.
        source_project_path : str or Path
            Path to the source project.
        source_design_name : str
            Name of the design.
        solution_name : str, optional
            Name of the solution and sweep. The
            default is ``"Setup1 : Sweep"``.
        image_subcircuit_path : str or Path or None
            Path of the Picture used in Circuit.
            Default is an HFSS Picture exported automatically.
        model_type : str, optional
            Dynamick Link type. Options are `Hfss`, `Q3d`, `Q2d`.
        variables : dict, optional
            Dictionary of variables and default values of original design, if exists.
        extrusion_length_q2d : str, float optional
            Extrusion length for 2D Models. Default is 10 (in model units).
        matrix : list, optional
        simulate_solutions : bool, optional
            Either if simulate or interpolate solutions.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.circuits.object_3d_circuit.CircuitComponent`
            Circuit Component Object.

        References
        ----------
        >>> oModelManager.Add
        >>> oComponentManager.Add
        >>> oDesign.AddCompInstance
        """
        if isinstance(source_project_path, str):
            source_project_path = Path(source_project_path)
        model = "hfss"
        owner = "HFSS"
        icon_file = "hfss.bmp"
        if model_type.lower() == "q3d extractor":
            model = "q3d"
            owner = "Q3D"
            icon_file = "q3d.bmp"

        elif model_type.lower() == "2d extractor":
            model = "2dext"
            owner = "2DExtractor"
            icon_file = "2dextractor.bmp"
        elif model_type.lower() == "siwave":
            model = "siwave"
            owner = "Siwave"
            icon_file = ""
        designer_customization = self._get_comp_custom_settings(1, 0, 0, 1, 0, 0, "False", "", 1)
        nexxim_customization = self._get_comp_custom_settings(2, 3, 1, 3, 0, 0, "False", "", 2)
        hspice_customization = self._get_comp_custom_settings(3, 1, 2, 3, 0, 0, "False", "", 3)

        if image_subcircuit_path:
            if isinstance(image_subcircuit_path, str):
                image_subcircuit_path = Path(image_subcircuit_path)
            if image_subcircuit_path.suffix not in [".gif", ".bmp", ".jpg"]:
                image_subcircuit_path = None
                warnings.warn("Image extension is not valid. Use default image instead.")
        if not image_subcircuit_path:
            image_subcircuit_path = (
                Path(self._modeler._app.desktop_install_dir) / "syslib" / "Bitmaps" / icon_file
            ).resolve()
        filename = ""
        comp_name_aux = generate_unique_name(source_design_name)
        WB_SystemID = source_design_name
        if Path(self._app.project_file) != source_project_path:
            filename = str(source_project_path)
            comp_name_aux = comp_name
            WB_SystemID = ""

        compInfo = [
            "NAME:" + str(comp_name_aux),
            "Name:=",
            comp_name_aux,
            "ModTime:=",
            1591855779,
            "Library:=",
            "",
            "LibLocation:=",
            "Project",
            "ModelType:=",
            model,
            "Description:=",
            "",
            "ImageFile:=",
            str(image_subcircuit_path),
            "SymbolPinConfiguration:=",
            0,
            ["NAME:PortInfoBlk"],
            ["NAME:PortOrderBlk"],
            "DesignName:=",
            source_design_name,
            "SolutionName:=",
            solution_name,
            "NewToOldMap:=",
            [],
            "OldToNewMap:=",
            [],
            "PinNames:=",
            pin_names,
            designer_customization,
            nexxim_customization,
            hspice_customization,
            "NoiseModelOption:=",
            "External",
            "WB_SystemID:=",
            WB_SystemID,
            "IsWBModel:=",
            False,
            "filename:=",
            filename,
            "numberofports:=",
            len(pin_names),
            "Simulate:=",
            simulate_solutions,
            "CloseProject:=",
            model_type.lower() == "siwave",
            "SaveProject:=",
            True,
            "InterpY:=",
            True,
            "InterpAlg:=",
            "auto",
            "IgnoreDepVars:=",
            False,
        ]
        if owner in ["HFSS", "Siwave"]:
            compInfo.extend(
                [
                    "Renormalize:=",
                    False,
                    "RenormImpedance:=",
                    50,
                ]
            )
        elif owner == "Q3D":
            compInfo.extend(
                [
                    "Renormalize:=",
                    False,
                    "RenormImpedance:=",
                    50,
                ]
            )
            if not matrix:
                matrix = ["NAME:Reduce Matrix Choices", default_matrix]
            compInfo.extend(["Reduce Matrix:=", "Original", matrix])
        else:
            if not matrix:
                matrix = ["NAME:Reduce Matrix Choices", "Original"]
            compInfo.extend(["Reduce Matrix:=", default_matrix, matrix, "EnableCableModeling:=", enable_cable_modeling])

        self.o_model_manager.Add(compInfo)

        info = [
            "Type:=",
            8,
            "NumTerminals:=",
            len(pin_names),
            "DataSource:=",
            "",
            "ModifiedOn:=",
            1591855894,
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
            icon_file,
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
            1591855894,
            "ExampleFile:=",
            "",
            "HiddenComponent:=",
            0,
            "CircuitEnv:=",
            0,
            "GroupID:=",
            0,
        ]

        compInfo2 = [
            "NAME:" + str(comp_name),
            "Info:=",
            info,
            "CircuitEnv:=",
            0,
            "Refbase:=",
            "S",
            "NumParts:=",
            1,
            "ModSinceLib:=",
            False,
        ]

        id = 0
        for pin in pin_names:
            compInfo2.append("Terminal:=")
            compInfo2.append([pin, pin, "A", False, id, 1, "", "Electrical", "0"])
            id += 1

        compInfo2.append(["NAME:Properties", "TextProp:=", ["Owner", "RD", "", owner]])
        compInfo2.append("CompExtID:=")
        compInfo2.append(5)
        variable_args = [
            "NAME:Parameters",
            "TextProp:=",
            ["ModelName", "RD", "", "FieldSolver"],
        ]
        if owner == "2DExtractor":
            variable_args.append("VariableProp:=")
            variable_args.append(["Length", "D", "", self._app.value_with_units(extrusion_length_q2d)])
        if variables:
            for k, v in variables.items():
                variable_args.append("VariableProp:=")
                variable_args.append([k, "D", "", str(v)])
        variable_args.append("MenuProp:=")
        variable_args.append(["CoSimulator", "SD", "", "Default", 0])
        variable_args.append("ButtonProp:=")
        variable_args.append(["CosimDefinition", "SD", "", "Edit", "Edit", 40501, "ButtonPropClientData:=", []])

        compInfo2.append(variable_args)
        compInfo2.append(
            [
                "NAME:CosimDefinitions",
                [
                    "NAME:CosimDefinition",
                    "CosimulatorType:=",
                    103,
                    "CosimDefName:=",
                    "Default",
                    "IsDefinition:=",
                    True,
                    "Connect:=",
                    True,
                    "ModelDefinitionName:=",
                    comp_name_aux,
                    "ShowRefPin2:=",
                    2,
                    "LenPropName:=",
                    "",
                ],
                "DefaultCosim:=",
                "Default",
            ]
        )

        self.o_component_manager.Add(compInfo2)
        self._app._odesign.AddCompInstance(comp_name)
        self.refresh_all_ids()
        for el in self.components:
            item = comp_name
            item2 = self.components[el].composed_name
            if comp_name in self.components[el].composed_name:
                return self.components[el]
        return False

    @pyaedt_function_handler()
    def set_sim_option_on_hfss_subcircuit(self, component, option="simulate"):
        """Set the simulation option on the HFSS subscircuit.

        Parameters
        ----------
        component : str
            Address of the component instance. For example, ``"Inst@layout_cutout;87;1"``.
        option : str
            Set the simulation strategy. Options are ``"simulate"`` and ``"interpolate"``. The default
            is ``"simulate"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oProject.ChangeProperty
        """
        if option == "simulate":
            setting = "Simulate missing solutions"
        elif option == "interpolate":
            setting = "Interpolate existing solutions"
        else:
            return False
        arg = ["NAME:Simulation option", "Value:=", setting]
        return self._edit_link_definition_hfss_subcircuit(component, arg)

    @pyaedt_function_handler()
    def set_sim_solution_on_hfss_subcircuit(self, component, solution_name="Setup1 : Sweep"):
        """Set the simulation solution on the HFSS subcircuit.

        Parameters
        ----------
        component : str
            Address of the component instance. For example, ``"Inst@layout_cutout;87;1"``.
        solution_name : str, optional
            Name of the solution and sweep. The default is ``"Setup1 : Sweep"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oProject.ChangeProperty
        """
        arg = ["NAME:Solution", "Value:=", solution_name]
        return self._edit_link_definition_hfss_subcircuit(component, arg)

    @pyaedt_function_handler()
    def _edit_link_definition_hfss_subcircuit(self, component, edited_prop):
        """Generic function to set the link definition for a HFSS subcircuit."""
        if isinstance(component, str):
            complist = component.split(";")
        elif isinstance(component, CircuitComponent):
            complist = component.composed_name.split(";")
        elif isinstance(component, int):
            complist = self.components[component].composed_name.split(";")
        else:
            raise AttributeError("Wrong Component Input")

        arg = [
            "NAME:AllTabs",
            [
                "NAME:Model",
                [
                    "NAME:PropServers",
                    "Component@" + str(complist[0].split("@")[1]),
                ],
                [
                    "NAME:ChangedProps",
                    edited_prop,
                ],
            ],
        ]
        self._app._oproject.ChangeProperty(arg)
        return True

    @pyaedt_function_handler(component_name="name")
    def refresh_dynamic_link(self, name):
        """Refresh a dynamic link component.

        Parameters
        ----------
        name : str
            Name of the dynamic link component.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oComponentManager.UpdateDynamicLink
        """
        if "@" in name:
            name = name.split("@")[1]
        name = name.split(";")[0]
        self.o_component_manager.UpdateDynamicLink(name)
        return True

    @pyaedt_function_handler()
    def _parse_spice_model(self, model_path):
        models = []
        with open_file(model_path, "r") as f:
            for line in f:
                if ".subckt" in line.lower():
                    pinNames = [i.strip() for i in re.split(" |\t", line) if i]
                    models.append(pinNames[1])
        return models

    @pyaedt_function_handler(model_path="input_file", model_name="model", symbol_name="symbol")
    def create_component_from_spicemodel(
        self,
        input_file,
        model=None,
        create_component=True,
        location=None,
        symbol_path="Nexxim Circuit Elements\\Nexxim_symbols:",
        symbol="",
    ):
        """Create and place a new component based on a spice .lib file.

        Parameters
        ----------
        input_file : str or Path
            Path to .lib file.
        model : str, optional
            Model name to import. If `None` the first subckt in the lib file will be placed.
        create_component : bool, optional
            If set to ``True``, create a spice model component. Otherwise, only import the spice model.
        location : list, optional
            Position in the schematic of the new component.
        symbol_path : str, optional
            Path to the symbol library.
            Default value is ``"Nexxim Circuit Elements\\Nexxim_symbols:"``.
        symbol : str, optional
            Symbol name to replace the spice model with.
            Default value is an empty string which means the default symbol for spice is used.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.circuits.object_3d_circuit.CircuitComponent`
            Circuit Component Object.

        Examples
        --------
        >>> from pathlib import Path
        >>> from ansys.aedt.core import Circuit
        >>> cir = Circuit(version="2025.1")
        >>> model = Path("Your path") / "test.lib"
        >>> cir.modeler.schematic.create_component_from_spicemodel(input_file=model,model="GRM1234",symbol="nexx_cap")
        >>> cir.release_desktop(False, False)
        """
        if isinstance(input_file, str):
            input_file = Path(input_file)
        models = self._parse_spice_model(input_file)
        if not model and models:
            model = models[0]
        elif model not in models:
            return False
        arg = ["NAME:Options", "Mode:=", 2, "Overwrite:=", False, "SupportsSimModels:=", False, "LoadOnly:=", False]
        arg2 = ["NAME:Models"]
        for el in models:
            arg2.append(el + ":=")
            if el == model:
                if symbol_path and symbol:
                    arg2.append([True, symbol_path + symbol, "", False])
                else:
                    arg2.append([True, "", "", False])
            else:
                arg2.append([False, "", "", False])
        arg.append(arg2)
        self.o_component_manager.ImportModelsFromFile(input_file.as_posix(), arg)

        if create_component:
            return self.create_component(None, component_library=None, component_name=model, location=location)
        return True

    @pyaedt_function_handler(model_path="input_file", solution_name="solution")
    def add_siwave_dynamic_link(self, input_file, solution=None, simulate_solutions=False):
        """Add a siwave dinamyc link object.

        Parameters
        ----------
        input_file : str or Path
            Full path to the .siw file.
        solution : str, optional
            Solution name.
        simulate_solutions : bool, optional
            Either if simulate or interpolate existing solutions.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.circuits.object_3d_circuit.CircuitComponent`
            Circuit Component Object.
        """
        if isinstance(input_file, str):
            input_file = Path(input_file)
        if not input_file.exists():
            raise FileNotFoundError(f"Project file '{input_file}' doesn't exist")
        comp_name = Path(input_file).stem
        results_path = input_file.parent / f"{comp_name}.siwaveresults"
        solution_path = results_path / f"{comp_name}.asol"
        out = load_keyword_in_aedt_file(solution_path, "Solutions")
        if not solution:
            solution = list(out["Solutions"]["SYZSolutions"].keys())[0]
        results_folder = (
            results_path
            / out["Solutions"]["SYZSolutions"][solution]["DiskName"]
            / f"{out['Solutions']['SYZSolutions'][solution]['DiskName']}.syzinfo"
        )

        pin_names = []
        with open_file(results_folder, "r") as f:
            lines = f.read().splitlines()
            for line in lines:
                if line[:4] == "PORT":
                    line_spit = line.split(" ")
                    pin_names.append(line_spit[1].strip('"'))

        return self._add_subcircuit_link(
            comp_name,
            pin_names,
            input_file,
            comp_name,
            solution_name=solution,
            model_type="siwave",
            simulate_solutions=simulate_solutions,
        )
