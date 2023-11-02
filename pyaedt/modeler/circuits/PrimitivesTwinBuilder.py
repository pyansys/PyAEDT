from pyaedt.generic.general_methods import pyaedt_function_handler
from pyaedt.modeler.circuits.PrimitivesCircuit import CircuitComponents, ComponentCatalog


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

    >>> from pyaedt import Twin Builder
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
    def create_resistor(self, compname=None, value=50, location=None, angle=0, use_instance_id_netlist=False):
        """Create a resistor.

        Parameters
        ----------
        compname : str, optional
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
            component_library="Basic Elements\\Circuit\\Passive Elements",
            component_name="R",
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )

        id.set_property("R", value)

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
            component_library="Basic Elements\\Circuit\\Passive Elements",
            component_name="L",
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )

        id.set_property("L", value)
        return id

    @pyaedt_function_handler()
    def create_capacitor(self, compname=None, value=50, location=None, angle=0, use_instance_id_netlist=False):
        """Create a capacitor.

        Parameters
        ----------
        compname : str, optional
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
            component_library="Basic Elements\\Circuit\\Passive Elements",
            component_name="C",
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )

        id.set_property("C", value)
        id.set_property("UseInitialConditions", True)
        return id

    @pyaedt_function_handler()
    def create_voltage_source(
        self, compname=None, type="E", amplitude=326, freq=50, location=None, angle=0, use_instance_id_netlist=False
    ):
        """Create a voltage source (conservative electrical output).

        Parameters
        ----------
        compname : str, optional
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

    @pyaedt_function_handler()
    def create_diode(self, compname=None, location=None, angle=0, use_instance_id_netlist=False):
        """Create a diode.

        Parameters
        ----------
        compname : str, optional
            Name of the diode. The default is ``None``.
        location : list of float, optional
            Position on the X axis and Y axis. The default value is ``None``.
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
        if location == None:
            location = []

        id = self.create_component(
            compname,
            component_library="Basic Elements\\Circuit\\Semiconductors System Level",
            component_name="D",
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )
        return id

    @pyaedt_function_handler()
    def create_npn(self, compname=None, location=None, angle=0, use_instance_id_netlist=False):
        """Create an NPN transistor.

        Parameters
        ----------
        compname : str, optional
            Name of the NPN transistor. The default value is ``None``.
        location : list of float, optional
            Position on the X axis and Y axis. The default value is ``None``.
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
        if location == None:
            location = []

        id = self.create_component(
            compname,
            component_library="Basic Elements\\Circuit\\Semiconductors System Level",
            component_name="BJT",
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )
        return id

    @pyaedt_function_handler()
    def create_pnp(self, compname=None, location=None, angle=0, use_instance_id_netlist=False):
        """Create a PNP transistor.

        Parameters
        ----------
        compname : str, optional
            Name of the PNP transistor. The default is ``None``.
        location : list of float, optional
            Position on the X axis and Y axis. The default value is ``None``.
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
        if location == None:
            location = []

        id = self.create_component(
            compname,
            component_library="Basic Elements\\Circuit\\Semiconductors System Level",
            component_name="BJT",
            location=location,
            angle=angle,
            use_instance_id_netlist=use_instance_id_netlist,
        )

        return id

    @pyaedt_function_handler()
    def create_periodic_waveform_source(
        self,
        compname=None,
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
        """Create a periodic waveform source (non conservative real output).

        Parameters
        ----------
        compname : str, optional
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
