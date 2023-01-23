# -*- coding: utf-8 -*-
import os
import random
import re
import warnings

from pyaedt.generic.general_methods import generate_unique_name
from pyaedt.generic.general_methods import open_file
from pyaedt.generic.general_methods import pyaedt_function_handler
from pyaedt.generic.LoadAEDTFile import load_entire_aedt_file
from pyaedt.modeler.circuits.object3dcircuit import CircuitComponent
from pyaedt.modeler.circuits.PrimitivesCircuit import CircuitComponents
from pyaedt.modeler.circuits.PrimitivesCircuit import ComponentCatalog


class NexximComponents(CircuitComponents):
    """Manages circuit components for Nexxim.

    Parameters
    ----------
    modeler : :class:`pyaedt.modeler.schematic.ModelerNexxim`
        Inherited parent object.
    Examples
    --------

    >>> from pyaedt import Circuit
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
        :class:`pyaedt.modeler.object3dcircuit.CircuitComponent`
            Circuit Component Object.
        """
        if type(partname) is int:
            return self.components[partname]
        for el in self.components:
            if self.components[el].name == partname or self.components[el].composed_name == partname or el == partname:
                return self.components[el]

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

    @property
    def components_catalog(self):
        """Return the syslib component catalog with all info.

        Returns
        -------
        :class:`pyaedt.modeler.PrimitivesCircuit.ComponentCatalog`
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
        :class:`pyaedt.modeler.object3dcircuit.CircuitComponent`
            Circuit Component Object when successful or ``False`` when failed.

        Examples
        --------
        >>> from pyaedt import Circuit
        >>> cir = Circuit()
        """
        if not name:
            name = generate_unique_name("Circuit")

        if nested_subcircuit_id:
            parent_name = "{}:{}:{}".format(
                self._app.design_name.split("/")[0], nested_subcircuit_id, random.randint(1, 10000)
            )
        else:
            parent_name = "{}:{}".format(self._app.design_name.split("/")[0], ":U" + str(random.randint(1, 10000)))

        self._app.odesign.InsertDesign("Circuit Design", name, "", parent_name)
        if nested_subcircuit_id:
            pname = "{}:{}".format(self._app.design_name.split("/")[0], nested_subcircuit_id)
            odes = self._app.oproject.SetActiveDesign(pname)
            oed = odes.SetActiveEditor("SchematicEditor")
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
                    self.components[el].location = location
                if angle is not None:
                    self.components[el].angle = self.arg_with_dim(angle, "°")
                return self.components[el]
        return False

    @pyaedt_function_handler()
    def duplicate(self, component, location=None, angle=0, flip=False):  # pragma: no cover
        """Add a new subcircuit to the design.

        .. note::
            This works only in graphical mode.

        Parameters
        ----------
        component : class:`pyaedt.modeler.Object3d.CircuitComponent` Circuit Component Object
            Component to duplicate.
        location : list of float, optional
            Position on the X axis and Y axis.
        angle : float, optional
            Angle rotation in degrees. The default is ``0``.
        flip : bool, optional
            Whether the component should be flipped. The default value is ``False``.

        Returns
        -------
        :class:`pyaedt.modeler.Object3d.CircuitComponent` Circuit Component Object
        when successful or ``False`` when failed.
        """
        comp_names = []
        if isinstance(component, CircuitComponent):
            comp_names.append(component.composed_name)
        else:
            comp_names.append(component)
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

    @pyaedt_function_handler()
    def connect_components_in_series(self, components_to_connect):
        """Connect schematic components in series.

        Parameters
        ----------
        components_to_connect : list of :class:`pyaedt.modeler.object3dcircuit.CircuitComponent`
           List of Components to connect. It can be a list of objects or component names.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------
        >>> from pyaedt import Circuit
        >>> circuit = Circuit()
        >>> myind = circuit.modeler.schematic.create_inductor(compname="L100", value=1e-9, location=[0,0])
        >>> myres = circuit.modeler.schematic.create_resistor(compname="R100", value=50, location=[0.002, 0.05])
        >>> circuit.modeler.schematic.connect_components_in_series([myind, myres])
        """
        comps = []
        for component in components_to_connect:
            if isinstance(component, CircuitComponent):
                comps.append(component)
            else:
                for id, cmp in self.components.items():
                    if component in [cmp.id, cmp.name, cmp.composed_name]:
                        comps.append(cmp)
                        break
        i = 0
        assert len(comps) > 1, "At least two components have to be passed."
        while i < (len(comps) - 1):
            comps[i].pins[-1].connect_to_component(comps[i + 1].pins[0])
            i += 1
        return True

    @pyaedt_function_handler()
    def connect_components_in_parallel(self, components_to_connect):
        """Connect schematic components in parallel.

        Parameters
        ----------
        components_to_connect : list of :class:`pyaedt.modeler.object3dcircuit.CircuitComponent`
           List of Components to connect. It can be a list of objects or component names.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------
        >>> from pyaedt import Circuit
        >>> circuit = Circuit()
        >>> myind = circuit.modeler.schematic.create_inductor("L100", 1e-9)
        >>> myres = circuit.modeler.schematic.create_resistor("R100", 50)
        >>> circuit.modeler.schematic.connect_components_in_parallel([myind, myres.composed_name])
        """
        comps = []
        for component in components_to_connect:
            if isinstance(component, CircuitComponent):
                comps.append(component)
            else:
                for id, cmp in self.components.items():
                    if component in [cmp.id, cmp.name, cmp.composed_name]:
                        comps.append(cmp)
                        break
        assert len(comps) > 1, "At least two components have to be passed."
        comps[0].pins[0].connect_to_component([i.pins[0] for i in comps[1:]])
        terminal_to_connect = [cmp for cmp in comps if len(cmp.pins) >= 2]
        if len(terminal_to_connect) > 1:
            terminal_to_connect[0].pins[1].connect_to_component([i.pins[1] for i in terminal_to_connect[1:]])
        return True

    @pyaedt_function_handler()
    def create_3dlayout_subcircuit(self, sourcename):
        """Add a subcircuit from a HFSS 3DLayout.

        .. deprecated:: 0.4.0
           Use :func:`Circuit.modeler.schematic.add_subcircuit_3dlayout` instead.
        """
        warnings.warn(
            "`create_3dlayout_subcircuit` is deprecated. Use `add_subcircuit_3dlayout` instead.", DeprecationWarning
        )
        return self.add_subcircuit_3dlayout(sourcename)

    @pyaedt_function_handler()
    def add_subcircuit_3dlayout(self, sourcename):
        """Add a subcircuit from a HFSS 3DLayout.

        Parameters
        ----------
        sourcename : str
            Name of the source design.

        Returns
        -------
        :class:`pyaedt.modeler.object3dcircuit.CircuitComponent`
            Circuit Component Object.

        References
        ----------

        >>> oProject.CopyDesign
        >>> oEditor.PasteDesign
        """
        self._app._oproject.CopyDesign(sourcename)
        self.oeditor.PasteDesign(0, ["NAME:Attributes", "Page:=", 1, "X:=", 0, "Y:=", 0, "Angle:=", 0, "Flip:=", False])
        self.refresh_all_ids()
        for el in self.components:
            if sourcename in self.components[el].composed_name:
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

    @pyaedt_function_handler()
    def create_resistor(self, compname=None, value=50, location=[], angle=0, use_instance_id_netlist=False):
        """Create a resistor.

        Parameters
        ----------
        compname : str, optional
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
        :class:`pyaedt.modeler.object3dcircuit.CircuitComponent`
            Circuit Component Object.

        References
        ----------

        >>> oEditor.CreateComponent
        """
        cmpid = self.create_component(
            compname, location=location, angle=angle, use_instance_id_netlist=use_instance_id_netlist
        )

        cmpid.set_property("R", value)
        return cmpid

    @pyaedt_function_handler()
    def create_inductor(self, compname=None, value=50, location=[], angle=0, use_instance_id_netlist=False):
        """Create an inductor.

        Parameters
        ----------
        compname : str, optional
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
        :class:`pyaedt.modeler.object3dcircuit.CircuitComponent`
            Circuit Component Object.

        References
        ----------

        >>> oEditor.CreateComponent
        """
        cmpid = self.create_component(
            compname,
            component_library="Inductors",
            component_name="IND_",
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )

        cmpid.set_property("L", value)

        return cmpid

    @pyaedt_function_handler()
    def create_capacitor(self, compname=None, value=50, location=None, angle=0, use_instance_id_netlist=False):
        """Create a capacitor.

        Parameters
        ----------
        compname : str, optional
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
        :class:`pyaedt.modeler.object3dcircuit.CircuitComponent`
            Circuit Component Object.

        References
        ----------

        >>> oEditor.CreateComponent
        """

        if location == None:
            location = []

        cmpid = self.create_component(
            compname,
            component_library="Capacitors",
            component_name="CAP_",
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )

        cmpid.set_property("C", value)
        return cmpid

    @pyaedt_function_handler()
    def create_voltage_dc(self, compname=None, value=1, location=None, angle=0, use_instance_id_netlist=False):
        """Create a voltage DC source.

        Parameters
        ----------
        compname : str, optional
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
        :class:`pyaedt.modeler.object3dcircuit.CircuitComponent`
            Circuit Component Object.

        References
        ----------

        >>> oEditor.CreateComponent
        """
        if location == None:
            location = []

        cmpid = self.create_component(
            compname,
            component_library="Independent Sources",
            component_name="V_DC",
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )

        cmpid.set_property("DC", value)
        return cmpid

    @pyaedt_function_handler()
    def create_voltage_probe(self, probe_name=None, location=None, angle=0, use_instance_id_netlist=False):
        """Create a voltage probe.

        Parameters
        ----------
        probe_name :
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
        :class:`pyaedt.modeler.object3dcircuit.CircuitComponent`
            Circuit Component Object.

        References
        ----------

        >>> oEditor.CreateComponent
        """
        if location is None:
            location = []
        else:
            location = [location[0] + 0.2 * 24.4 / 1000, location[1] + 0.2 * 24.4 / 1000]

        cmpid = self.create_component(
            None,
            component_library="Probes",
            component_name="VPROBE",
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )

        cmpid.set_property("Name", probe_name)
        return cmpid

    @pyaedt_function_handler()
    def create_current_pulse(self, compname=None, value_lists=[], location=[], angle=0, use_instance_id_netlist=False):
        """Create a current pulse.

        Parameters
        ----------
        compname : str, optional
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
        :class:`pyaedt.modeler.object3dcircuit.CircuitComponent`
            Circuit Component Object.

        References
        ----------

        >>> oEditor.CreateComponent
        """
        cmpid = self.create_component(
            compname,
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

    @pyaedt_function_handler()
    def create_voltage_pulse(self, compname=None, value_lists=[], location=[], angle=0, use_instance_id_netlist=False):
        """Create a voltage pulse.

        Parameters
        ----------
        compname : str, optional
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
        :class:`pyaedt.modeler.object3dcircuit.CircuitComponent`
            Circuit Component Object.

        References
        ----------

        >>> oEditor.CreateComponent
        """
        cmpid = self.create_component(
            compname,
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

    @pyaedt_function_handler()
    def create_current_dc(self, compname=None, value=1, location=[], angle=0, use_instance_id_netlist=False):
        """Create a current DC source.

        Parameters
        ----------
        compname : str, optional
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
        :class:`pyaedt.modeler.object3dcircuit.CircuitComponent`
            Circuit Component Object.

        References
        ----------

        >>> oEditor.CreateComponent
        """
        cmpid = self.create_component(
            compname,
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
        :class:`pyaedt.modeler.object3dcircuit.CircuitComponent`
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

    @pyaedt_function_handler()
    def create_diode(self, compname=None, model_name="required", location=[], angle=0, use_instance_id_netlist=False):
        """Create a diode.

        Parameters
        ----------
        compname : str
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
        :class:`pyaedt.modeler.object3dcircuit.CircuitComponent`
            Circuit Component Object.

        References
        ----------

        >>> oEditor.CreateComponent
        """
        cmpid = self.create_component(
            compname,
            component_library="Diodes",
            component_name="DIODE_Level1",
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )

        cmpid.set_property("MOD", model_name)
        return cmpid

    @pyaedt_function_handler()
    def create_npn(self, compname=None, value=None, location=[], angle=0, use_instance_id_netlist=False):
        """Create an NPN transistor.

        Parameters
        ----------
        compname : str
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
        :class:`pyaedt.modeler.object3dcircuit.CircuitComponent`
            Circuit Component Object.

        References
        ----------

        >>> oEditor.CreateComponent
        """
        id = self.create_component(
            compname,
            component_library="BJTs",
            component_name="Level01_NPN",
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )
        if value:
            id.set_property("MOD", value)
        return id

    @pyaedt_function_handler()
    def create_pnp(self, compname=None, value=50, location=[], angle=0, use_instance_id_netlist=False):
        """Create a PNP transistor.

        Parameters
        ----------
        compname : str
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
        :class:`pyaedt.modeler.object3dcircuit.CircuitComponent`
            Circuit Component Object.

        References
        ----------

        >>> oEditor.CreateComponent
        """
        id = self.create_component(
            compname,
            component_library="BJTs",
            component_name="Level01_PNP",
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )
        if value:
            id.set_property("MOD", value)

        return id

    @pyaedt_function_handler()
    def create_new_component_from_symbol(
        self,
        symbol_name,
        pin_lists,
        time_stamp=1591858313,
        description="",
        refbase="x",
        parameter_list=[],
        parameter_value=[],
        gref="",
    ):
        """Create a component from a symbol.

        Parameters
        ----------
        symbol_name : str
            Name of the symbol.
        pin_lists : list
            List of pin names.
        time_stamp : int, optional
            UTC time stamp.
        description : str, optional
            Component description.
        refbase : str, optional
            Reference base. The default is ``"U"``.
        parameter_list : list
            List of parameters. The default is ``[]``.
        parameter_value : list
            List of parameter values. The default is ``[]``.
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
        arg = [
            "NAME:" + symbol_name,
            "Info:=",
            [
                "Type:=",
                0,
                "NumTerminals:=",
                len(pin_lists),
                "DataSource:=",
                "",
                "ModifiedOn:=",
                time_stamp,
                "Manufacturer:=",
                "",
                "Symbol:=",
                symbol_name,
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

        for pin in pin_lists:
            arg.append("Terminal:=")
            arg.append([pin, pin, "A", False, 0, 1, "", "Electrical", "0"])
        arg.append("CompExtID:=")
        arg.append(1)
        arg2 = ["NAME:Parameters"]

        for el, val in zip(parameter_list, parameter_value):
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
        while id < len(pin_lists):
            spicesintax += "%" + str(id) + " "
            id += 1
            spicesintax += symbol_name + " "
        for el, val in zip(parameter_list, parameter_value):
            if "MOD" in el:
                spicesintax += "@{} ".format(el)
            else:
                spicesintax += "{}=@{} ".format(el, el)

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

    @pyaedt_function_handler()
    def get_comp_custom_settings(
        self, toolNum, dc=0, interp=0, extrap=1, conv=0, passivity=0, reciprocal="False", opt="", data_type=1
    ):
        """Retrieve custom settings for a resistor.

        Parameters
        ----------
        toolNum :

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
        if toolNum == 1:
            custom = "NAME:DesignerCustomization"
        elif toolNum == 2:
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

    @pyaedt_function_handler()
    def add_subcircuit_hfss_link(
        self,
        comp_name,
        pin_names,
        source_project_path,
        source_design_name,
        solution_name="Setup1 : Sweep",
        image_subcircuit_path=None,
        variables=None,
    ):
        """Add a subcircuit HFSS link.

        .. deprecated:: 0.4.27
           Use :func:`pyaedt.modeler.PrimitivesNexxim.NexximComponents.add_subcircuit_dynamic_link.` instead.

        Parameters
        ----------
        comp_name : str
            Name of the subcircuit HFSS link.
        pin_names : list
            List of the pin names.
        source_project_path : str
            Path to the source project.
        source_design_name : str
            Name of the design.
        solution_name : str, optional
            Name of the solution and sweep. The
            default is ``"Setup1 : Sweep"``.
        image_subcircuit_path : str, optional
            Path of the Picture used in Circuit.
            Default is an HFSS Picture exported automatically.
        variables : dict, optional.
            Dictionary of design variables of linked object if any. Key is name, value is default value.

        Returns
        -------
        :class:`pyaedt.modeler.object3dcircuit.CircuitComponent`
            Circuit Component Object.

        References
        ----------

        >>> oModelManager.Add
        >>> oComponentManager.Add
        >>> oDesign.AddCompInstance
        """
        warnings.warn(
            "`add_subcircuit_hfss_link` is deprecated. Use `add_subcircuit_dynamic_link` instead.",
            DeprecationWarning,
        )
        return self._add_subcircuit_link(
            comp_name=comp_name,
            pin_names=pin_names,
            source_project_path=source_project_path,
            source_design_name=source_design_name,
            solution_name=solution_name,
            image_subcircuit_path=image_subcircuit_path,
            model_type="Hfss",
            variables=variables,
        )

    @pyaedt_function_handler()
    def add_subcircuit_dynamic_link(
        self,
        pyaedt_app=None,
        solution_name=None,
        extrusion_length=None,
        enable_cable_modeling=True,
        default_matrix="Original",
        tline_port="",
        comp_name=None,
    ):
        """Add a subcircuit from `HFSS`, `Q3d` or `2D Extractor` in circuit design.

        Parameters
        ----------
        pyaedt_app : :class:`pyaedt.q3d.Q3d` or :class:`pyaedt.q3d.Q2d` or :class:`pyaedt.q3d.Hfss`.
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
        comp_name : str, optional
            Component name.

        Returns
        -------
        :class:`pyaedt.modeler.object3dcircuit.CircuitComponent`
            Circuit Component Object.

        References
        ----------

        >>> oModelManager.Add
        >>> oComponentManager.Add
        >>> oDesign.AddCompInstance
        >>> oDesign.AddDynamicLink
        """
        if not comp_name:
            comp_name = generate_unique_name(pyaedt_app.design_name)
        source_project_path = pyaedt_app.project_file
        source_design_name = pyaedt_app.design_name
        # matrix = None
        # if pyaedt_app.design_type == "HFSS":
        #     pin_names = pyaedt_app.get_excitations_name()
        # elif pyaedt_app.design_type == "Q3D Extractor":
        #     excts = list(pyaedt_app.oboundary.GetExcitations())
        #     i = 0
        #     sources = []
        #     sinks = []
        #     while i < len(excts):
        #         if excts[i + 1] == "Source":
        #             sources.append(excts[i])
        #         elif excts[i + 1] == "Sink":
        #             sinks.append(excts[i])
        #         i += 2
        #     pin_names = sources + sinks
        #     matrix = ["NAME:Reduce Matrix Choices"] + list(pyaedt_app.omatrix.ListReduceMatrixes())
        # elif pyaedt_app.design_type == "2D Extractor":
        #     excts = list(pyaedt_app.oboundary.GetExcitations())
        #     pins = []
        #     i = 0
        #     while i < len(excts):
        #         if excts[i + 1] != "ReferenceGround":
        #             pins.append(excts[i])
        #         i += 2
        #     pin_names = [i + "_in" for i in pins]
        #     pin_names.append("Input_ref")
        #     pin_names.extend([i + "_out" for i in pins])
        #     pin_names.append("Output_ref")
        #     matrix = ["NAME:Reduce Matrix Choices"] + list(pyaedt_app.omatrix.ListReduceMatrixes())
        # variables = {}
        # for k, v in pyaedt_app.variable_manager.variables.items():
        #     variables[k] = v.evaluated_value
        if not solution_name:
            solution_name = pyaedt_app.nominal_sweep
        # comp = self._add_subcircuit_link(
        #     comp_name=comp_name,
        #     pin_names=pin_names,
        #     source_project_path=source_project_path,
        #     source_design_name=source_design_name,
        #     solution_name=solution_name,
        #     image_subcircuit_path="",
        #     model_type=pyaedt_app.design_type,
        #     variables=variables,
        #     extrusion_length_q2d=extrusion_length,
        #     matrix=matrix,
        #     enable_cable_modeling=enable_cable_modeling,
        #     default_matrix=default_matrix,
        # )

        self._app.odesign.AddDynamicLink(
            source_design_name,
            source_project_path,
            comp_name,
            solution_name,
            tline_port,
            default_matrix,
            enable_cable_modeling,
            "Pyaedt Dynamic Link",
        )
        self.refresh_all_ids()
        for el in self.components:
            if comp_name in self.components[el].composed_name:
                if extrusion_length:
                    self.components[el].set_property("Length", self.arg_with_dim(extrusion_length))
                if tline_port and extrusion_length:
                    self.components[el].set_property("TLineLength", self.arg_with_dim(extrusion_length))
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
        source_project_path : str
            Path to the source project.
        source_design_name : str
            Name of the design.
        solution_name : str, optional
            Name of the solution and sweep. The
            default is ``"Setup1 : Sweep"``.
        image_subcircuit_path : str, optional
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
        :class:`pyaedt.modeler.object3dcircuit.CircuitComponent`
            Circuit Component Object.

        References
        ----------

        >>> oModelManager.Add
        >>> oComponentManager.Add
        >>> oDesign.AddCompInstance
        """
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
        designer_customization = self.get_comp_custom_settings(1, 0, 0, 1, 0, 0, "False", "", 1)
        nexxim_customization = self.get_comp_custom_settings(2, 3, 1, 3, 0, 0, "False", "", 2)
        hspice_customization = self.get_comp_custom_settings(3, 1, 2, 3, 0, 0, "False", "", 3)

        if image_subcircuit_path:
            _, file_extension = os.path.splitext(image_subcircuit_path)
            if file_extension != ".gif" or file_extension != ".bmp" or file_extension != ".jpg":
                image_subcircuit_path = None
                warnings.warn("Image extension is not valid. Use default image instead.")
        if not image_subcircuit_path:
            image_subcircuit_path = os.path.normpath(
                os.path.join(self._modeler._app.desktop_install_dir, "syslib", "Bitmaps", icon_file)
            )
        filename = ""
        comp_name_aux = generate_unique_name(source_design_name)
        WB_SystemID = source_design_name
        if not self._app.project_file == source_project_path:
            filename = source_project_path
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
            image_subcircuit_path,
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
            variable_args.append(["Length", "D", "", self.arg_with_dim(extrusion_length_q2d)])
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
            Address of the component instance. For example, ``"Inst@Galileo_cutout3;87;1"``.
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
            Address of the component instance. For example, ``"Inst@Galileo_cutout3;87;1"``.
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
        """Generic function to set the link definition for an hfss subcircuit."""
        if isinstance(component, str):
            complist = component.split(";")
        elif isinstance(component, CircuitComponent):
            complist = component.composed_name.split(";")
        elif isinstance(component, int):
            complist = self.components[component].composed_name.split(";")
        else:
            raise AttributeError("Wrong Component Input")
        complist2 = complist[0].split("@")
        arg = ["NAME:AllTabs"]
        arg1 = ["NAME:Model"]
        arg2 = ["NAME:PropServers", "Component@" + str(complist2[1])]
        arg3 = ["NAME:ChangedProps", edited_prop]

        arg1.append(arg2)
        arg1.append(arg3)
        arg.append(arg1)

        self._app._oproject.ChangeProperty(arg)
        return True

    @pyaedt_function_handler()
    def refresh_dynamic_link(self, component_name):
        """Refresh a dynamic link component.  This method is adapted from the native API.
        ```
            oDefinitionManager = oProject.GetDefinitionManager()
            oComponentManager = oDefinitionManager.GetManager("Component")
            oComponentManager.UpdateDynamicLink("TeeModel_L1")
        ```

        Parameters
        ----------
        component_name : str
            Name of the dynamic link component.


        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oComponentManager.UpdateDynamicLink
        """
        if "@" in component_name:
            component_name = component_name.split("@")[1]
        component_name = component_name.split(";")[0]
        self.o_component_manager.UpdateDynamicLink(component_name)
        return True

    @pyaedt_function_handler()
    def push_excitations(self, instance_name, thevenin_calculation=False, setup_name="LinearFrequency"):
        """Push excitations.

        .. deprecated:: 0.4.0
           Use :func:`Circuit.push_excitations` instead.
        """
        warnings.warn(
            "`circuit.modeler.schematic.push_excitation` is deprecated. " "Use `circuit.push_excitation` instead.",
            DeprecationWarning,
        )
        return self._app.push_excitations(instance_name, thevenin_calculation, setup_name)

    @pyaedt_function_handler()
    def assign_sin_excitation2ports(self, ports, settings):
        """Assign a voltage sinusoidal excitation to circuit ports.

        .. deprecated:: 0.4.0
           Use :func:`Circuit.modeler.schematic.assign_voltage_sinusoidal_excitation_to_ports` instead.
        """
        warnings.warn(
            "`assign_sin_excitation2ports` is deprecated. "
            "Use `assign_voltage_sinusoidal_excitation_to_ports` instead.",
            DeprecationWarning,
        )
        return self._app.assign_voltage_sinusoidal_excitation_to_ports(ports)

    @pyaedt_function_handler()
    def _parse_spice_model(self, model_path):
        models = []
        with open_file(model_path, "r") as f:
            for line in f:
                if ".subckt" in line.lower():
                    pinNames = [i.strip() for i in re.split(" |\t", line) if i]
                    models.append(pinNames[1])
        return models

    @pyaedt_function_handler()
    def create_component_from_spicemodel(self, model_path, model_name=None, create_component=True, location=None):
        """Create and place a new component based on a spice .lib file.

        Parameters
        ----------
        model_path : str
            Path to .lib file.
        model_name : str, optional
            Model name to import. If `None` the first subckt in the lib file will be placed.
        create_component : bool, optional
            If set to ``True``, create a spice model component. Otherwise, only import the spice model.
        location : list, optional
            Position in the schematic of the new component.

        Returns
        -------
        :class:`pyaedt.modeler.object3dcircuit.CircuitComponent`
            Circuit Component Object.
        """
        models = self._parse_spice_model(model_path)
        if not model_name and models:
            model_name = models[0]
        elif model_name not in models:
            return False
        arg = ["NAME:Options", "Mode:=", 2, "Overwrite:=", False, "SupportsSimModels:=", False, "LoadOnly:=", False]
        arg2 = ["NAME:Models"]
        for el in models:
            arg2.append(el + ":=")
            if el == model_name:
                arg2.append([True, "", "", False])
            else:
                arg2.append([False, "", "", False])
        arg.append(arg2)
        self.o_component_manager.ImportModelsFromFile(model_path.replace("\\", "/"), arg)

        if create_component:
            return self.create_component(
                None,
                component_library=None,
                component_name=model_name,
                location=location,
            )
        else:
            return True

    @pyaedt_function_handler()
    def add_siwave_dynamic_link(self, model_path, solution_name=None, simulate_solutions=False):
        """Add a siwave dinamyc link object.

        Parameters
        ----------
        model_path : str
            Full path to the .siw file.
        solution_name : str, optional
            Solution name.
        simulate_solutions : bool, optional
            Either if simulate or interpolate existing solutions.

        Returns
        -------
        :class:`pyaedt.modeler.object3dcircuit.CircuitComponent`
            Circuit Component Object.
        """
        assert os.path.exists(model_path), "Project file doesn't exist"
        comp_name = os.path.splitext(os.path.basename(model_path))[0]
        results_path = model_path + "averesults"
        solution = os.path.join(results_path, comp_name + ".asol")
        out = load_entire_aedt_file(solution)
        if not solution_name:
            solution_name = list(out["Solutions"]["SYZSolutions"].keys())[0]
        results_folder = os.path.join(
            results_path,
            out["Solutions"]["SYZSolutions"][solution_name]["DiskName"],
            out["Solutions"]["SYZSolutions"][solution_name]["DiskName"] + ".syzinfo",
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
            model_path,
            comp_name,
            solution_name=solution_name,
            model_type="siwave",
            simulate_solutions=simulate_solutions,
        )
