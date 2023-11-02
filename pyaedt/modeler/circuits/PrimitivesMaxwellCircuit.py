from pyaedt.generic.general_methods import pyaedt_function_handler
from pyaedt.modeler.circuits.PrimitivesCircuit import CircuitComponents


class MaxwellCircuitComponents(CircuitComponents):
    """MaxwellCircuitComponents class.

    This class is for managing all circuit components for MaxwellCircuit.

    Examples
    --------
    Basic usage demonstrated with a MaxwellCircuit design:

    >>> from pyaedt import MaxwellCircuit
    >>> aedtapp = MaxwellCircuit()
    >>> prim = aedtapp.modeler.schematic
    """

    @property
    def design_libray(self):
        """Design Library."""
        return "Maxwell Circuit Elements"

    @property
    def tab_name(self):
        """Tab name."""
        return "PassedParameterTab"

    @pyaedt_function_handler()
    def __getitem__(self, partname):
        """Get object id from a string or integer.

        Parameters
        ----------
        partname : int or str
            ID or name of the object.

        Returns
        -------
        :class:`pyaedt.modeler.cad.object3dcircuit.CircuitComponent`
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

    @pyaedt_function_handler()
    def create_resistor(self, compname=None, value=50, location=None, angle=0, use_instance_id_netlist=False):
        """Create a resistor.

        Parameters
        ----------
        compname : str, optional
            Name of the resistor. The default is ``None``.
        value : float, optional
            Value for the resistor. The default is ``50``.
        location : list of float, optional
            Position on the X axis and Y axis. The default is ``None``.
        angle : float, optional
            Angle of rotation in degrees. The default is ``0``.
        use_instance_id_netlist : bool, optional
            Whether to use the instance ID in the net list or not. The default is ``False``.

        Returns
        -------
        :class:`pyaedt.modeler.cad.object3dcircuit.CircuitComponent`
            Circuit Component Object.

        References
        ----------
        >>> oEditor.CreateComponent
        """
        if location == None:
            location = []

        id = self.create_component(
            compname,
            component_library="Passive Elements",
            component_name="Res",
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )

        id.set_property("R", value)
        id.set_property("Name", compname)
        return id

    @pyaedt_function_handler()
    def create_inductor(self, compname=None, value=50, location=None, angle=0, use_instance_id_netlist=False):
        """Create an inductor.

        Parameters
        ----------
        compname : str, optional
            Name of the inductor. The default is ``None``.
        value : float, optional
            Value for the inductor. The default is ``50``.
        location : list of float, optional
            Position on the X axis and Y axis. The default is ``None``.
        angle : float, optional
            Angle rotation in degrees. The default is ``0``.
        use_instance_id_netlist : bool, optional
            Whether to use the instance ID in the net list or not. The default is ``False``.

        Returns
        -------
        :class:`pyaedt.modeler.cad.object3dcircuit.CircuitComponent`
            Circuit Component Object.

        References
        ----------
        >>> oEditor.CreateComponent
        """
        if location == None:
            location = []

        id = self.create_component(
            compname,
            component_library="Passive Elements",
            component_name="Ind",
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )

        id.set_property("L", value)
        id.set_property("Name", compname)
        return id

    @pyaedt_function_handler()
    def create_capacitor(self, compname=None, value=50, location=[], angle=0, use_instance_id_netlist=False):
        """Create a capacitor.

        Parameters
        ----------
        compname : str, optional
            Name of the capacitor. The default is ``None``.
        value : float, optional
            Value for the capacitor. The default is ``50``.
        location : list of float, optional
            Position on the X axis and Y axis.
        angle : float, optional
            Angle of rotation in degrees. The default is ``0``.
        use_instance_id_netlist : bool, optional
            Whether to use the instance ID in the net list or not. The default is ``False``.

        Returns
        -------
        :class:`pyaedt.modeler.cad.object3dcircuit.CircuitComponent`
            Circuit Component Object.

        References
        ----------
        >>> oEditor.CreateComponent
        """
        id = self.create_component(
            compname,
            component_library="Passive Elements",
            component_name="Cap",
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )

        id.set_property("C", value)
        id.set_property("Name", compname)
        return id

    @pyaedt_function_handler()
    def create_diode(self, compname=None, location=None, angle=0, use_instance_id_netlist=False):
        """Create a diode.

        Parameters
        ----------
        compname : str, optional
            Name of the diode. The default is ``None``.
        location : list of float, optional
            Position on the X axis and Y axis. The default is ``None``.
        angle : float, optional
            Angle of rotation in degrees. The default is ``0``.
        use_instance_id_netlist : bool, optional
            Whether to use the instance ID in the net list. The default is ``False``.

        Returns
        -------
        :class:`pyaedt.modeler.cad.object3dcircuit.CircuitComponent`
            Circuit Component Object.

        References
        ----------
        >>> oEditor.CreateComponent
        """
        if location == None:
            location = []

        id = self.create_component(
            compname,
            component_library="Passive Elements",
            component_name="DIODE",
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )

        id.set_property("Name", compname)
        return id

    @pyaedt_function_handler()
    def create_winding(self, compname=None, location=[], angle=0, use_instance_id_netlist=False):
        """Create an NPN transistor.

        Parameters
        ----------
        compname : str, optional
            Name of the NPN transistor. The default is ``None``.
        location : list of float, optional
            Position on the X axis and Y axis.
        angle : float, optional
            Angle rotation in degrees. The default is ``0``.
        use_instance_id_netlist : bool, optional
            Whether to use the instance ID in the net list. The default is ``False``.

        Returns
        -------
        :class:`pyaedt.modeler.cad.object3dcircuit.CircuitComponent`
            Circuit Component Object.

        References
        ----------
        >>> oEditor.CreateComponent
        """
        id = self.create_component(
            compname,
            component_library="Dedicated Elements",
            component_name="Winding",
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )
        id.set_property("Name", compname)
        return id
