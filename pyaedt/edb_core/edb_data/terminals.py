import re

from pyaedt import pyaedt_function_handler
from pyaedt.edb_core.edb_data.connectable import Connectable
from pyaedt.edb_core.edb_data.padstacks_data import EDBPadstackInstance
from pyaedt.edb_core.edb_data.primitives_data import cast
from pyaedt.edb_core.general import BoundaryType, TerminalType, convert_py_list_to_net_list
from pyaedt.generic.general_methods import generate_unique_name


class Terminal(Connectable):
    def __init__(self, pedb, edb_object):
        super().__init__(pedb, edb_object)
        self._reference_object = None

    @property
    def _hfss_port_property(self):
        hfss_prop = re.search(r"HFSS\(.*?\)", self._edb_properties)
        p = {}
        if hfss_prop:
            hfss_type = re.search(r"'HFSS Type'='([^']+)'", hfss_prop.group())
            orientation = re.search(r"'Orientation'='([^']+)'", hfss_prop.group())
            horizontal_ef = re.search(r"'Horizontal Extent Factor'='([^']+)'", hfss_prop.group())
            vertical_ef = re.search(r"'Vertical Extent Factor'='([^']+)'", hfss_prop.group())
            radial_ef = re.search(r"'Radial Extent Factor'='([^']+)'", hfss_prop.group())
            pec_w = re.search(r"'PEC Launch Width'='([^']+)'", hfss_prop.group())

            p["HFSS Type"] = hfss_type.group(1) if hfss_type else ""
            p["Orientation"] = orientation.group(1) if orientation else ""
            p["Horizontal Extent Factor"] = float(horizontal_ef.group(1)) if horizontal_ef else ""
            p["Vertical Extent Factor"] = float(vertical_ef.group(1)) if vertical_ef else ""
            p["Radial Extent Factor"] = float(radial_ef.group(1)) if radial_ef else ""
            p["PEC Launch Width"] = pec_w.group(1) if pec_w else ""
        else:
            p["HFSS Type"] = ""
            p["Orientation"] = ""
            p["Horizontal Extent Factor"] = ""
            p["Vertical Extent Factor"] = ""
            p["Radial Extent Factor"] = ""
            p["PEC Launch Width"] = ""
        return p

    @_hfss_port_property.setter
    def _hfss_port_property(self, value):
        txt = []
        for k, v in value.items():
            txt.append("'{}'='{}'".format(k, v))
        txt = ",".join(txt)
        self._edb_properties = "HFSS({})".format(txt)

    @property
    def hfss_type(self):
        """HFSS port type."""
        return self._hfss_port_property["HFSS Type"]

    @hfss_type.setter
    def hfss_type(self, value):
        p = self._hfss_port_property
        p["HFSS Type"] = value
        self._hfss_port_property = p

    @property
    def is_circuit_port(self):
        """Whether it is a circuit port."""
        return self._edb_object.GetIsCircuitPort()

    @is_circuit_port.setter
    def is_circuit_port(self, value):
        self._edb_object.SetIsCircuitPort(value)

    @property
    def _port_post_processing_prop(self):
        """Get port post processing properties."""
        return self._edb_object.GetPortPostProcessingProp()

    @_port_post_processing_prop.setter
    def _port_post_processing_prop(self, value):
        self._edb_object.SetPortPostProcessingProp(value)

    @property
    def do_renormalize(self):
        """Determine whether port renormalization is enabled."""
        return self._port_post_processing_prop.DoRenormalize

    @do_renormalize.setter
    def do_renormalize(self, value):
        ppp = self._port_post_processing_prop
        ppp.DoRenormalize = value
        self._port_post_processing_prop = ppp

    @property
    def name(self):
        """Port Name.

        Returns
        -------
        str
        """
        return self._edb_object.GetName()

    @name.setter
    def name(self, value):
        if isinstance(value, str):
            if not any(port for port in list(self._pedb.excitations.keys()) if port == value):
                self._edb_object.SetName(value)
            else:
                self._pedb.logger.warning("An existing port already has this same name. A port name must be unique.")

    @property
    def net_name(self):
        """Net name.

        Returns
        -------
        str
        """
        return self.net.name

    @property
    def terminal_type(self):
        """Terminal Type.

        Returns
        -------
        int
        """
        return self._edb_object.GetTerminalType().ToString()

    @property
    def boundary_type(self):
        """Boundary Type.

        Returns
        -------
        int
        """
        return self._edb_object.GetBoundaryType().ToString()

    @boundary_type.setter
    def boundary_type(self, value):
        if value not in [i.name for i in BoundaryType]:  # pragma : no cover
            self._pedb.logger.warning("Invalid Boundary Type={}".format(value))
        if value == self._pedb.edb_api.cell.terminal.BoundaryType.kVoltageProbe.ToString():
            temp = self._pedb.edb_api.cell.terminal.BoundaryType.kVoltageProbe
        else:  # pragma : no cover
            temp = self._pedb.edb_api.cell.terminal.BoundaryType.InvalidBoundary
        self._edb_object.SetBoundaryType(temp)

    @property
    def impedance(self):
        """Impedance of the port."""
        return self._edb_object.GetImpedance().ToDouble()

    @impedance.setter
    def impedance(self, value):
        self._edb_object.SetImpedance(self._pedb.edb_value(value))

    @property
    def is_reference_terminal(self):
        """Whether it is a reference terminal."""
        return self._edb_object.IsReferenceTerminal()

    @property
    def ref_terminal(self):
        """Get reference terminal."""
        terminal = Terminal(self._pedb, self._edb_object.GetReferenceTerminal())
        if not terminal.is_null:
            if terminal.terminal_type == TerminalType.PointTerminal.name:
                return PointTerminal(self._pedb, terminal._edb_object)
            elif terminal.terminal_type == TerminalType.EdgeTerminal.name:
                return EdgeTerminal(self._pedb, terminal._edb_object)
            elif terminal.terminal_type == TerminalType.InvalidTerminal.name:  # pragma : no cover
                return None

    @ref_terminal.setter
    def ref_terminal(self, value):
        self._edb_object.SetReferenceTerminal(value._edb_object)

    @property
    def reference_object(self):  # pragma : no cover
        """This returns the object assigned as reference. It can be a primitive or a padstack instance.

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.padstacks_data.EDBPadstackInstance` or
        :class:`pyaedt.edb_core.edb_data.primitives_data.EDBPrimitives`
        """
        if not self._reference_object:
            term = self._edb_object

            if self.terminal_type == self._pedb.edb_api.cell.terminal.TerminalType.EdgeTerminal:
                edges = self._edb_object.GetEdges()
                edgeType = edges[0].GetEdgeType()
                if edgeType == self._pedb.edb_api.cell.terminal.EdgeType.PadEdge:
                    self._reference_object = self.get_pad_edge_terminal_reference_pin()
                else:
                    self._reference_object = self.get_edge_terminal_reference_primitive()
            elif self.terminal_type == TerminalType.PinGroupTerminal.name:
                self._reference_object = self.get_pin_group_terminal_reference_pin()
            elif self.terminal_type == TerminalType.PointTerminal.name:
                self._reference_object = self.get_point_terminal_reference_primitive()
            elif self.terminal_type == TerminalType.PadstackInstanceTerminal.name:
                self._reference_object = self.get_padstack_terminal_reference_pin()
            else:
                self._pedb.logger.warning("Invalid Terminal Type={}".format(term.GetTerminalType()))

        return self._reference_object

    @property
    def reference_net_name(self):
        """Net name to which reference_object belongs."""
        ref_obj = self._reference_object if self._reference_object else self.reference_object
        if ref_obj:
            return ref_obj.net_name

        return ""

    @pyaedt_function_handler()
    def get_padstack_terminal_reference_pin(self, gnd_net_name_preference=None):  # pragma : no cover
        """Get a list of pad stacks instances and serves Coax wave ports,
        pingroup terminals, PadEdge terminals.

        Parameters
        ----------
        gnd_net_name_preference : str, optional
            Preferred reference net name.

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.padstack_data.EDBPadstackInstance`
        """
        if self._edb_object.GetIsCircuitPort():
            return self.get_pin_group_terminal_reference_pin()
        _, padStackInstance, _ = self._edb_object.GetParameters()

        # Get the pastack instance of the terminal
        compInst = self._edb_object.GetComponent()
        pins = self._pedb.components.get_pin_from_component(compInst.GetName())
        return self._get_closest_pin(padStackInstance, pins, gnd_net_name_preference)

    @pyaedt_function_handler()
    def get_pin_group_terminal_reference_pin(self, gnd_net_name_preference=None):  # pragma : no cover
        """Return a list of pins and serves terminals connected to pingroups.

        Parameters
        ----------
        gnd_net_name_preference : str, optional
            Preferred reference net name.

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.padstack_data.EDBPadstackInstance`
        """
        refTerm = self._edb_object.GetReferenceTerminal()
        if self._edb_object.GetTerminalType() == self._pedb.edb_api.cell.terminal.TerminalType.PinGroupTerminal:
            padStackInstance = self._edb_object.GetPinGroup().GetPins()[0]
            pingroup = refTerm.GetPinGroup()
            refPinList = pingroup.GetPins()
            return self._get_closest_pin(padStackInstance, refPinList, gnd_net_name_preference)
        elif (
            self._edb_object.GetTerminalType() == self._pedb.edb_api.cell.terminal.TerminalType.PadstackInstanceTerminal
        ):
            _, padStackInstance, _ = self._edb_object.GetParameters()
            if refTerm.GetTerminalType() == self._pedb.edb_api.cell.terminal.TerminalType.PinGroupTerminal:
                pingroup = refTerm.GetPinGroup()
                refPinList = pingroup.GetPins()
                return self._get_closest_pin(padStackInstance, refPinList, gnd_net_name_preference)
            else:
                try:
                    _, refTermPSI, _ = refTerm.GetParameters()
                    return EDBPadstackInstance(refTermPSI, self._pedb)
                except AttributeError:
                    return None
        return None

    @pyaedt_function_handler()
    def get_edge_terminal_reference_primitive(self):  # pragma : no cover
        """Check and  return a primitive instance that serves Edge ports,
        wave ports and coupled edge ports that are directly connedted to primitives.

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.primitives_data.EDBPrimitives`
        """
        ref_layer = self._edb_object.GetReferenceLayer()
        edges = self._edb_object.GetEdges()
        _, _, point_data = edges[0].GetParameters()
        X = point_data.X
        Y = point_data.Y
        shape_pd = self._pedb.edb_api.geometry.point_data(X, Y)
        layer_name = ref_layer.GetName()
        for primitive in self._pedb.layout.primitives:
            if primitive.GetLayer().GetName() == layer_name or not layer_name:
                prim_shape_data = primitive.GetPolygonData()
                if prim_shape_data.PointInPolygon(shape_pd):
                    return cast(primitive, self._pedb)
        return None

    @pyaedt_function_handler()
    def get_point_terminal_reference_primitive(self):  # pragma : no cover
        """Find and return the primitive reference for the point terminal or the padstack instance.

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.padstacks_data.EDBPadstackInstance` or
        :class:`pyaedt.edb_core.edb_data.primitives_data.EDBPrimitives`
        """
        ref_term = self._edb_object.GetReferenceTerminal()  # return value is type terminal
        _, point_data, layer = ref_term.GetParameters()
        X = point_data.X
        Y = point_data.Y
        shape_pd = self._pedb.edb_api.geometry.point_data(X, Y)
        layer_name = layer.GetName()
        for primitive in self._pedb.layout.primitives:
            if primitive.GetLayer().GetName() == layer_name:
                prim_shape_data = primitive.GetPolygonData()
                if prim_shape_data.PointInPolygon(shape_pd):
                    return cast(primitive, self._pedb)
        for vias in self._pedb.padstacks.instances.values():
            if layer_name in vias.layer_range_names:
                plane = self._pedb.modeler.Shape(
                    "rectangle", pointA=vias.position, pointB=vias.padstack_definition.bounding_box[1]
                )
                rectangle_data = vias._pedb.modeler.shape_to_polygon_data(plane)
                if rectangle_data.PointInPolygon(shape_pd):
                    return vias
        return None

    @pyaedt_function_handler()
    def get_pad_edge_terminal_reference_pin(self, gnd_net_name_preference=None):
        """Get the closest pin padstack instances and serves any edge terminal connected to a pad.

        Parameters
        ----------
        gnd_net_name_preference : str, optional
            Preferred reference net name. Optianal, default is `None` which will auto compute the gnd name.

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.padstacks_data.EDBPadstackInstance`
        """
        comp_inst = self._edb_object.GetComponent()
        pins = self._pedb.components.get_pin_from_component(comp_inst.GetName())
        try:
            edges = self._edb_object.GetEdges()
        except AttributeError:
            return None
        _, pad_edge_pstack_inst, _, _ = edges[0].GetParameters()
        return self._get_closest_pin(pad_edge_pstack_inst, pins, gnd_net_name_preference)

    @pyaedt_function_handler()
    def _get_closest_pin(self, ref_pin, pin_list, gnd_net=None):
        _, pad_stack_inst_point, _ = ref_pin.GetPositionAndRotation()  # get the xy of the padstack
        if gnd_net is not None:
            power_ground_net_names = [gnd_net]
        else:
            power_ground_net_names = [net for net in self._pedb.nets.power_nets.keys()]
        comp_ref_pins = [i for i in pin_list if i.GetNet().GetName() in power_ground_net_names]
        if len(comp_ref_pins) == 0:  # pragma: no cover
            self._pedb.logger.error(
                "Terminal with PadStack Instance Name {} component has no reference pins.".format(ref_pin.GetName())
            )
            return None
        closest_pin_distance = None
        pin_obj = None
        for pin in comp_ref_pins:  # find the distance to all the pins to the terminal pin
            if pin.GetName() == ref_pin.GetName():  # skip the reference psi
                continue  # pragma: no cover
            _, pin_point, _ = pin.GetPositionAndRotation()
            distance = pad_stack_inst_point.Distance(pin_point)
            if closest_pin_distance is None:
                closest_pin_distance = distance
                pin_obj = pin
            elif closest_pin_distance < distance:
                continue
            else:
                closest_pin_distance = distance
                pin_obj = pin
        if pin_obj:
            return EDBPadstackInstance(pin_obj, self._pedb)


class EdgeTerminal(Terminal):
    def __init__(self, pedb, edb_object):
        super().__init__(pedb, edb_object)

    @pyaedt_function_handler
    def couple_ports(self, port):
        """Create a bundle wave port.

        Parameters
        ----------
        port : :class:`pyaedt.edb_core.ports.WavePort`, :class:`pyaedt.edb_core.ports.GapPort`, list, optional
            Ports to be added.

        Returns
        -------
        :class:`pyaedt.edb_core.ports.BundleWavePort`

        """
        if not isinstance(port, (list, tuple)):
            port = [port]
        temp = [self._edb_object]
        temp.extend([i._edb_object for i in port])
        edb_list = convert_py_list_to_net_list(temp, self._edb.cell.terminal.Terminal)
        _edb_bundle_terminal = self._edb.cell.terminal.BundleTerminal.Create(edb_list)
        return self._pedb.ports[self.name]


class BundleTerminal(Terminal):
    """Manages bundle terminal properties.

    Parameters
    ----------
    pedb : pyaedt.edb.Edb
        EDB object from the ``Edblib`` library.
    edb_object : Ansys.Ansoft.Edb.Cell.Terminal.BundleTerminal
        BundleTerminal instance from EDB.
    """

    def __init__(self, pedb, edb_object):
        super().__init__(pedb, edb_object)

    @property
    def terminals(self):
        """Get terminals belonging to this excitation."""
        return [EdgeTerminal(self._pedb, i) for i in list(self._edb_object.GetTerminals())]

    @property
    def name(self):
        return self.terminals[0].name

    @pyaedt_function_handler
    def decouple(self):
        """Ungroup a bundle of terminals."""
        return self._edb_object.Ungroup()


class PadstackInstanceTerminal(Terminal):
    """Manages bundle terminal properties."""

    def __init__(self, pedb, edb_object):
        super().__init__(pedb, edb_object)

    def create(self, padstack_instance, name=None, layer=None, is_ref=False):
        """Create an edge terminal.

        Parameters
        ----------
        prim_id : int
            Primitive ID.
        point_on_edge : list
            Coordinate of the point to define the edge terminal.
            The point must be on the target edge but not on the two
            ends of the edge.
        terminal_name : str, optional
            Name of the terminal. The default is ``None``, in which case the
            default name is assigned.
        is_ref : bool, optional
            Whether it is a reference terminal. The default is ``False``.

        Returns
        -------
        Edb.Cell.Terminal.EdgeTerminal
        """
        if not name:
            name = generate_unique_name("Terminal")

        if not layer:
            layer = padstack_instance.start_layer

        layer_obj = self._pedb.stackup.signal_layers[layer]

        terminal = self._edb.cell.terminal.PadstackInstanceTerminal.Create(
            self._pedb.active_layout,
            self.net.net_object,
            name,
            padstack_instance._edb_object,
            layer_obj._edb_layer,
            isRef=is_ref,
        )
        terminal = PadstackInstanceTerminal(self._pedb, terminal)

        return terminal if not terminal.is_null else False


class PointTerminal(Terminal):
    """Manages point terminal properties."""

    def __init__(self, pedb, edb_object=None):
        super().__init__(pedb, edb_object)

    @pyaedt_function_handler
    def create(self, name, net, location, layer, is_ref=False):
        """Create a point terminal.

        Parameters
        ----------
        name : str
            Name of the terminal.
        net : str
            Name of the net.
        location : list
            Location of the terminal.
        layer : str
            Name of the layer.
        is_ref : bool, optional
            Whether it is a reference terminal.

        Returns
        -------

        """
        terminal = self._pedb.edb_api.cell.terminal.PointTerminal.Create(
            self._pedb.active_layout,
            self._pedb.nets[net].net_object,
            name,
            self._pedb.point_data(*location),
            self._pedb.stackup[layer]._edb_layer,
            is_ref,
        )
        terminal = PointTerminal(self._pedb, terminal)
        return terminal if not terminal.is_null else False

    @property
    def location(self):
        """Get location of the terminal."""
        point_data = self._pedb.point_data(0, 0)
        layer = list(self._pedb.stackup.layers.values())[0]._edb_layer
        if self._edb_object.GetParameters(point_data, layer):
            return [point_data.X.ToDouble(), point_data.Y.ToDouble()]

    @location.setter
    def location(self, value):
        layer = self.layer
        self._edb_object.SetParameters(self._pedb.point_data(*value), layer)

    @property
    def layer(self):
        """Get layer of the terminal."""
        point_data = self._pedb.point_data(0, 0)
        layer = list(self._pedb.stackup.layers.values())[0]._edb_layer
        if self._edb_object.GetParameters(point_data, layer):
            return layer

    @layer.setter
    def layer(self, value):
        layer = self._pedb.stackup.layers[value]._edb_layer
        point_data = self._pedb.point_data(*self.location)
        self._edb_object.SetParameters(point_data, layer)


class PinGroupTerminal(Terminal):
    """Manages pin group terminal properties."""

    def __init__(self, pedb, edb_object=None):
        super().__init__(pedb, edb_object)
