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

from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.modeler.circuits.primitives_circuit import CircuitComponents
from ansys.aedt.core.modeler.circuits.primitives_circuit import ComponentCatalog


class TwinBuilderComponents(CircuitComponents):
    """TwinBuilderComponents class.

    This class is for managing all circuit components for Twin Builder.

    Parameters
    ----------
    parent :

    modeler :

    Examples
    --------
    Basic usage demonstrated with a Twin Builder design:

    >>> from ansys.aedt.core import Twin Builder
    >>> aedtapp = TwinBuilder()
    >>> prim = aedtapp.modeler.schematic
    """

    @property
    def _logger(self):
        return self._app.logger

    @property
    def design_libray(self):
        """Design Library."""
        return "Simplorer Elements"

    @property
    def tab_name(self):
        """Tab name."""
        return "Quantities"

    @pyaedt_function_handler()
    def __getitem__(self, partname):
        """Get object id from a string or integer.

        Parameters
        ----------
        partname : int or str
            ID or name of the object.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.circuits.object_3d_circuit.CircuitComponent`
            Circuit Component Object.

        """
        if isinstance(partname, int):
            return self.components[partname]
        for el in self.components:
            if self.components[el].name == partname or self.components[el].composed_name == partname or el == partname:
                return self.components[el]

        return None

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
        :class:`ansys.aedt.core.modeler.cad.primitivesCircuit.ComponentCatalog`
        """
        if not self._components_catalog:
            self._components_catalog = ComponentCatalog(self)
        return self._components_catalog

    @property
    def o_simmodel_manager(self):
        """Simulation models manager object."""
        return self.o_definition_manager.GetManager("SimModel")

    @pyaedt_function_handler(compname="name")
    def create_resistor(self, name=None, value=50, location=None, angle=0, use_instance_id_netlist=False):
        """Create a resistor.

        Parameters
        ----------
        name : str, optional
            Name of the resistor. The default value is ``None``.
        value : float, optional
            Value for the resistor. The default value is ``50``.
        location : list of float, optional
            Position on the X axis and Y axis. The default value is ``None``.
        angle : float, optional
            Angle rotation in degrees. The default value is ``0``.
        use_instance_id_netlist : bool, optional
            Whether to use the instance ID in the net list. The default value is ``False``.

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

        id = self.create_component(
            name,
            component_library="Basic Elements\\Circuit\\Passive Elements",
            component_name="R",
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )

        id.set_property("R", value)

        return id

    @pyaedt_function_handler(compname="name")
    def create_inductor(self, name=None, value=50, location=None, angle=0, use_instance_id_netlist=False):
        """Create an inductor.

        Parameters
        ----------
        name : str, optional
            Name of the inductor. The default is ``None``.
        value : float, optional
            Value for the inductor. The default is ``50``.
        location : list of float, optional
            Position on the X axis and Y axis. The default is ``None``.
        angle : float, optional
            Angle rotation in degrees. The default is ``0``.
        use_instance_id_netlist : bool, optional
            Whether to use the instance ID in the net list. The default is ``False``.

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

        id = self.create_component(
            name,
            component_library="Basic Elements\\Circuit\\Passive Elements",
            component_name="L",
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )

        id.set_property("L", value)
        return id

    @pyaedt_function_handler(compname="name")
    def create_capacitor(self, name=None, value=50, location=None, angle=0, use_instance_id_netlist=False):
        """Create a capacitor.

        Parameters
        ----------
        name : str, optional
            Name of the capacitor. The default value is ``None``.
        value : float, optional
            Value for the capacitor. The default value is ``50``.
        location : list of float, optional
            Position on the X axis and Y axis. The default value is ``None``.
        angle : float, optional
            Angle rotation in degrees. The default value is ``0``.
        use_instance_id_netlist : bool, optional
            Whether to use the instance ID in the net list. The default value is ``False``.

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

        id = self.create_component(
            name,
            component_library="Basic Elements\\Circuit\\Passive Elements",
            component_name="C",
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )

        id.set_property("C", value)
        id.set_property("UseInitialConditions", True)
        return id

    @pyaedt_function_handler(compname="name")
    def create_voltage_source(
        self, name=None, type="E", amplitude=326, freq=50, location=None, angle=0, use_instance_id_netlist=False
    ):
        """Create a voltage source (conservative electrical output).

        Parameters
        ----------
        name : str, optional
            Name of the voltage source. The default is ``None``.
        type  : str, optional
            Type of the source. The default is ``E``.
        amplitude : float, optional
            Amplitude of the waveform if periodic. The default is ``326V``
        freq : float, optional
            Frequency of the periodic waveform. The default is ``50Hz``.
        location : list of float, optional
            Position on the X axis and Y axis. The default value is ``None``.
        angle : float, optional
            Angle of rotation in degrees. The default is ``0``.
        use_instance_id_netlist : bool, optional
            Whether to use the instance ID in the net list or not. The default is ``False``.

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

        id = self.create_component(
            name,
            component_library="Basic Elements\\Circuit\\Sources",
            component_name="E",
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )

        id.set_property("Type", type)

        if type == "E":
            id.set_property("EMF", amplitude)
        if type == "ESINE" or type == "EPULSE" or type == "ETRIANG":
            id.set_property("AMPL", amplitude)
            id.set_property("FREQ", freq)
            id.set_property("TPERIO", "Tend+1")
            id.set_property("PERIO", 1)

        return id

    @pyaedt_function_handler(compname="name")
    def create_diode(self, name=None, location=None, angle=0, use_instance_id_netlist=False):
        """Create a diode.

        Parameters
        ----------
        name : str, optional
            Name of the diode. The default is ``None``.
        location : list of float, optional
            Position on the X axis and Y axis. The default value is ``None``.
        angle : float, optional
            Angle rotation in degrees. The default is ``0``.
        use_instance_id_netlist : bool, optional
            Whether to use the instance ID in the net list. The default is ``False``.

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

        id = self.create_component(
            name,
            component_library="Basic Elements\\Circuit\\Semiconductors System Level",
            component_name="D",
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )
        return id

    @pyaedt_function_handler(compname="name")
    def create_npn(self, name=None, location=None, angle=0, use_instance_id_netlist=False):
        """Create an NPN transistor.

        Parameters
        ----------
        name : str, optional
            Name of the NPN transistor. The default value is ``None``.
        location : list of float, optional
            Position on the X axis and Y axis. The default value is ``None``.
        angle : float, optional
            Angle rotation in degrees. The default is ``0``.
        use_instance_id_netlist : bool, optional
            Whether to use the instance ID in the net list. The default is ``False``.

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

        id = self.create_component(
            name,
            component_library="Basic Elements\\Circuit\\Semiconductors System Level",
            component_name="BJT",
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )
        return id

    @pyaedt_function_handler(compname="name")
    def create_pnp(self, name=None, location=None, angle=0, use_instance_id_netlist=False):
        """Create a PNP transistor.

        Parameters
        ----------
        name : str, optional
            Name of the PNP transistor. The default is ``None``.
        location : list of float, optional
            Position on the X axis and Y axis. The default value is ``None``.
        angle : float, optional
            Angle rotation in degrees. The default is ``0``.
        use_instance_id_netlist : bool, optional
            Whether to use the instance ID in the net list. The default is ``False``.

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

        id = self.create_component(
            name,
            component_library="Basic Elements\\Circuit\\Semiconductors System Level",
            component_name="BJT",
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )

        return id

    @pyaedt_function_handler(compname="name")
    def create_periodic_waveform_source(
        self,
        name=None,
        type="SINE",
        amplitude=100,
        freq=50,
        phase=0,
        offset=0,
        delay=0,
        location=None,
        angle=0,
        use_instance_id_netlist=False,
    ):
        """
        Create a periodic waveform source (non conservative real output).

        Parameters
        ----------
        name : str, optional
            Name of the voltage source. The default is ``None``.
        type  : str, optional
            Type of the source [SINE, PULSE, TRAING, SAWTOOTH]. The default is ``SINE``.
        amplitude : float, optional
            Amplitude of the waveform if periodic. The default is ``100V``
        freq : float, optional
            Frequency of the periodic waveform. The default is ``50Hz``.
        phase : float, optional
            Phase of the  periodic waveform. The default is ``0deg``.
        offset : float, optional
            Offset added to the amplitude of the periodic waveform. The default is ``0``.
        delay : float, optional
            Delay before starting of the periodic waveform. The default is ``0``.
        location : list of float, optional
            Position on the X axis and Y axis. The default value is ``None``.
        angle : float, optional
            Angle of rotation in degrees. The default is ``0``.
        use_instance_id_netlist : bool, optional
            Whether to use the instance ID in the net list or not. The default is ``False``.

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

        id = self.create_component(
            name,
            component_library="Basic Elements\\Tools\\Time Functions",
            component_name=type,
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )

        if type in ["SINE", "PULSE", "TRIANG", "SAWTOOTH"]:
            id.set_property("AMPL", amplitude)
            id.set_property("FREQ", freq)
            id.set_property("PHASE", phase)
            id.set_property("OFF", offset)
            id.set_property("TDELAY", delay)
            id.set_property("TPERIO", "Tend+1")
            id.set_property("PERIO", 1)

        return id

    @pyaedt_function_handler()
    def create_component_from_sml(
        self,
        input_file,
        model,
        pins_names,
    ):
        """Create and place a new component based on a .sml file.

        Parameters
        ----------
        input_file : str
            Path to .sml file.
        model : str
            Model name to import.
        pins_names : list
            List of model pins names.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------
        >>> from ansys.aedt.core import TwinBuilder
        >>> tb = TwinBuilder(version="2025.1")
        >>> input_file = os.path.join("Your path", "test.sml")
        >>> model = "Thermal_ROM_SML"
        >>> pins_names = ["Input1_InternalHeatGeneration", "Input2_HeatFlow", "Output1_Temp1,Output2_Temp2"]
        >>> tb.modeler.schematic.create_component_from_sml(input_file=model, model=model, pins_names=pins_names)
        >>> tb.release_desktop(False, False)
        """
        pins_names_str = ",".join(pins_names)
        arg = ["NAME:Options", "Mode:=", 1]
        arg2 = ["NAME:Models", model + ":=", [True]]

        arg3 = [
            "NAME:Components",
            model + ":=",
            [True, True, model, True, pins_names_str.lower(), pins_names_str.lower()],
        ]

        arg.append(arg2)
        arg.append(arg3)
        self.ocomponent_manager.ImportModelsFromFile(input_file, arg)
        return True

    @pyaedt_function_handler()
    def update_quantity_value(self, component_name, name, value, netlist_units=""):
        """Change the quantity value of a component.

        Parameters
        ----------
        component_name : str
            Component name.
        name : str
            Quantity name.
        value : str
            Value of the quantity.
        netlist_units : str, optional
            Value of the netlist unit.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------
        >>> from ansys.aedt.core import TwinBuilder
        >>> tb = TwinBuilder(version="2025.1")
        >>> G = 0.00254
        >>> modelpath = "Simplorer Elements\\Basic Elements\\Tools\\Time Functions:DATAPAIRS"
        >>> source1 = tb.modeler.schematic.create_component("source1", "", modelpath, [20 * G, 29 * G])
        >>> tb.modeler.schematic.update_quantity_value(source1.composed_name, "PERIO", "0")
        >>> tb.release_desktop(False, False)
        """
        try:
            self.oeditor.ChangeProperty(
                [
                    "NAME:AllTabs",
                    [
                        "NAME:Quantities",
                        ["NAME:PropServers", component_name],
                        [
                            "NAME:ChangedProps",
                            [
                                "NAME:" + name,
                                "OverridingDef:=",
                                True,
                                "Value:=",
                                value,
                                "NetlistUnits:=",
                                netlist_units,
                                "ShowPin:=",
                                False,
                                "Display:=",
                                False,
                                "Sweep:=",
                                False,
                                "SDB:=",
                                False,
                            ],
                        ],
                    ],
                ]
            )
            return True
        except Exception:  # pragma: no cover
            self.logger.warning(f"Quantity {name} has not been edited. Check if readonly.")
            return False
