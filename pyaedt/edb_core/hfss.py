"""
This module contains the ``EdbHfss`` class.
"""
import math

from pyaedt.edb_core.edb_data.simulation_configuration import SimulationConfiguration
from pyaedt.edb_core.edb_data.sources import ExcitationDifferential
from pyaedt.edb_core.general import convert_py_list_to_net_list
from pyaedt.edb_core.general import convert_pytuple_to_nettuple
from pyaedt.generic.constants import RadiationBoxType
from pyaedt.generic.constants import SweepType
from pyaedt.generic.general_methods import generate_unique_name
from pyaedt.generic.general_methods import is_ironpython
from pyaedt.generic.general_methods import pyaedt_function_handler
from pyaedt.modeler.geometry_operators import GeometryOperators


class EdbHfss(object):
    """Manages EDB method to configure Hfss setup accessible from `Edb.core_hfss` property.

    Examples
    --------
    >>> from pyaedt import Edb
    >>> edbapp = Edb("myaedbfolder")
    >>> edb_hfss = edb_3dedbapp.core_hfss
    """

    def __init__(self, p_edb):
        self._pedb = p_edb

    @property
    def _logger(self):
        return self._pedb.logger

    @property
    def _edb(self):
        return self._pedb.edb

    @property
    def _active_layout(self):
        return self._pedb.active_layout

    @property
    def _cell(self):
        return self._pedb.cell

    @property
    def _db(self):
        return self._pedb.db

    @property
    def _builder(self):
        return self._pedb.builder

    @property
    def excitations(self):
        """Get all excitations."""
        return self._pedb.excitations

    @property
    def sources(self):
        """Get all sources."""
        return self._pedb.sources

    @property
    def probes(self):
        """Get all probes."""
        return self._pedb.probes

    def _get_edb_value(self, value):
        return self._pedb.edb_value(value)

    @pyaedt_function_handler()
    def _create_edge_terminal(self, prim_id, point_on_edge, terminal_name=None, is_ref=False):
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
        if not terminal_name:
            terminal_name = generate_unique_name("Terminal_")
        if not isinstance(point_on_edge, self._edb.Geometry.PointData):
            point_on_edge = self._edb.Geometry.PointData(
                self._get_edb_value(point_on_edge[0]), self._get_edb_value(point_on_edge[1])
            )
        if hasattr(prim_id, "GetId"):
            prim = prim_id
        else:
            prim = [i for i in self._pedb.core_primitives.primitives if i.id == prim_id][0].primitive_object
        pos_edge = self._edb.Cell.Terminal.PrimitiveEdge.Create(prim, point_on_edge)
        pos_edge = convert_py_list_to_net_list(pos_edge, self._edb.Cell.Terminal.Edge)
        return self._edb.Cell.Terminal.EdgeTerminal.Create(
            prim.GetLayout(), prim.GetNet(), terminal_name, pos_edge, isRef=is_ref
        )

    @pyaedt_function_handler()
    def get_trace_width_for_traces_with_ports(self):
        """Retrieve the trace width for traces with ports.

        Returns
        -------<
        dict
            Dictionary of trace width data.
        """
        nets = {}
        for net in self._pedb.excitations_nets:
            smallest = self._pedb.core_nets.nets[net].get_smallest_trace_width()
            if smallest < 1e10:
                nets[net] = self._pedb.core_nets.nets[net].get_smallest_trace_width()
        return nets

    @pyaedt_function_handler()
    def create_circuit_port_on_pin(self, pos_pin, neg_pin, impedance=50, port_name=None):
        """Create Circuit Port on Pin.

        Parameters
        ----------
        pos_pin : Object
            Edb Pin
        neg_pin : Object
            Edb Pin
        impedance : float
            Port Impedance
        port_name : str, optional
            Port Name

        >>> from pyaedt import Edb
        >>> edbapp = Edb("myaedbfolder", "project name", "release version")
        >>> pins =edbapp.core_components.get_pin_from_component("U2A5")
        >>> edbapp.core_hfss.create_circuit_port_on_pin(pins[0], pins[1],50,"port_name")

        Returns
        -------
        str
            Port Name.

        """
        return self._pedb.core_siwave.create_circuit_port_on_pin(pos_pin, neg_pin, impedance, port_name)

    @pyaedt_function_handler()
    def create_voltage_source_on_pin(self, pos_pin, neg_pin, voltage_value=3.3, phase_value=0, source_name=""):
        """Create a voltage source.

        Parameters
        ----------
        pos_pin : Object
            Positive Pin.
        neg_pin : Object
            Negative Pin.
        voltage_value : float, optional
            Value for the voltage. The default is ``3.3``.
        phase_value : optional
            Value for the phase. The default is ``0``.
        source_name : str, optional
            Name of the source. The default is ``""``.

        Returns
        -------
        str
            Source Name.

        Examples
        --------

        >>> from pyaedt import Edb
        >>> edbapp = Edb("myaedbfolder", "project name", "release version")
        >>> pins =edbapp.core_components.get_pin_from_component("U2A5")
        >>> edbapp.core_hfss.create_voltage_source_on_pin(pins[0], pins[1],50,"source_name")
        """
        return self._pedb.core_siwave.create_voltage_source_on_pin(
            pos_pin, neg_pin, voltage_value, phase_value, source_name
        )

    @pyaedt_function_handler()
    def create_current_source_on_pin(self, pos_pin, neg_pin, current_value=0.1, phase_value=0, source_name=""):
        """Create a current source.

        Parameters
        ----------
        pos_pin : Object
            Positive Pin.
        neg_pin : Object
            Negative Pin.
        current_value : float, optional
            Value for the current. The default is ``0.1``.
        phase_value : optional
            Value for the phase. The default is ``0``.
        source_name : str, optional
            Name of the source. The default is ``""``.

        Returns
        -------
        str
            Source Name.

        Examples
        --------

        >>> from pyaedt import Edb
        >>> edbapp = Edb("myaedbfolder", "project name", "release version")
        >>> pins =edbapp.core_components.get_pin_from_component("U2A5")
        >>> edbapp.core_hfss.create_current_source_on_pin(pins[0], pins[1],50,"source_name")
        """

        return self._pedb.core_siwave.create_current_source_on_pin(
            pos_pin, neg_pin, current_value, phase_value, source_name
        )

    @pyaedt_function_handler()
    def create_resistor_on_pin(self, pos_pin, neg_pin, rvalue=1, resistor_name=""):
        """Create a Resistor boundary between two given pins.

        Parameters
        ----------
        pos_pin : Object
            Positive Pin.
        neg_pin : Object
            Negative Pin.
        rvalue : float, optional
            Resistance value. The default is ``1``.
        resistor_name : str, optional
            Name of the resistor. The default is ``""``.

        Returns
        -------
        str
            Name of the Resistor.

        Examples
        --------

        >>> from pyaedt import Edb
        >>> edbapp = Edb("myaedbfolder", "project name", "release version")
        >>> pins =edbapp.core_components.get_pin_from_component("U2A5")
        >>> edbapp.core_hfss.create_resistor_on_pin(pins[0], pins[1],50,"res_name")
        """
        return self._pedb.core_siwave.create_resistor_on_pin(pos_pin, neg_pin, rvalue, resistor_name)

    @pyaedt_function_handler()
    def create_circuit_port_on_net(
        self,
        positive_component_name,
        positive_net_name,
        negative_component_name=None,
        negative_net_name="GND",
        impedance_value=50,
        port_name="",
    ):
        """Create a circuit port on a NET.
        It groups all pins belonging to the specified net and then applies the port on PinGroups.

        Parameters
        ----------
        positive_component_name : str
            Name of the positive component.
        positive_net_name : str
            Name of the positive net.
        negative_component_name : str, optional
            Name of the negative component. The default is ``None``, in which case the name of
            the positive net is assigned.
        negative_net_name : str, optional
            Name of the negative net name. The default is ``"GND"``.
        impedance_value : float, optional
            Port impedance value. The default is ``50``.
        port_name : str, optional
            Name of the port. The default is ``""``.

        Returns
        -------
        str
            The name of the port.

        Examples
        --------
        >>> from pyaedt import Edb
        >>> edbapp = Edb("myaedbfolder", "project name", "release version")
        >>> edbapp.core_hfss.create_circuit_port_on_net("U2A5", "V1P5_S3", "U2A5", "GND", 50, "port_name")
        """
        return self._pedb.core_siwave.create_circuit_port_on_net(
            positive_component_name,
            positive_net_name,
            negative_component_name,
            negative_net_name,
            impedance_value,
            port_name,
        )

    @pyaedt_function_handler()
    def create_voltage_source_on_net(
        self,
        positive_component_name,
        positive_net_name,
        negative_component_name=None,
        negative_net_name="GND",
        voltage_value=3.3,
        phase_value=0,
        source_name="",
    ):
        """Create a voltage source.

        Parameters
        ----------
        positive_component_name : str
            Name of the positive component.
        positive_net_name : str
            Name of the positive net.
        negative_component_name : str, optional
            Name of the negative component. The default is ``None``, in which case the name of
            the positive net is assigned.
        negative_net_name : str, optional
            Name of the negative net. The default is ``"GND"``.
        voltage_value : float, optional
            Value for the voltage. The default is ``3.3``.
        phase_value : optional
            Value for the phase. The default is ``0``.
        source_name : str, optional
            Name of the source. The default is ``""``.

        Returns
        -------
        str
            Source Name.

        Examples
        --------

        >>> from pyaedt import Edb
        >>> edbapp = Edb("myaedbfolder", "project name", "release version")
        >>> edb.core_hfss.create_voltage_source_on_net("U2A5", "V1P5_S3", "U2A5", "GND", 3.3, 0, "source_name")
        """
        return self._pedb.core_siwave.create_voltage_source_on_net(
            positive_component_name,
            positive_net_name,
            negative_component_name,
            negative_net_name,
            voltage_value,
            phase_value,
            source_name,
        )

    @pyaedt_function_handler()
    def create_current_source_on_net(
        self,
        positive_component_name,
        positive_net_name,
        negative_component_name=None,
        negative_net_name="GND",
        current_value=0.1,
        phase_value=0,
        source_name="",
    ):
        """Create a current source.

        Parameters
        ----------
        positive_component_name : str
            Name of the positive component.
        positive_net_name : str
            Name of the positive net.
        negative_component_name : str, optional
            Name of the negative component. The default is ``None``, in which case the name of
            the positive net is assigned.
        negative_net_name : str, optional
            Name of the negative net. The default is ``"GND"``.
        current_value : float, optional
            Value for the current. The default is ``0.1``.
        phase_value : optional
            Value for the phase. The default is ``0``.
        source_name : str, optional
            Name of the source. The default is ``""``.

        Returns
        -------
        str
            Source Name.

        Examples
        --------

        >>> from pyaedt import Edb
        >>> edbapp = Edb("myaedbfolder", "project name", "release version")
        >>> edb.core_hfss.create_current_source_on_net("U2A5", "V1P5_S3", "U2A5", "GND", 0.1, 0, "source_name")
        """
        return self._pedb.core_siwave.create_current_source_on_net(
            positive_component_name,
            positive_net_name,
            negative_component_name,
            negative_net_name,
            current_value,
            phase_value,
            source_name,
        )

    @pyaedt_function_handler()
    def create_coax_port_on_component(self, ref_des_list, net_list):
        """Create a coaxial port on a component or component list on a net or net list.

        .. note::
           The name of the new coaxial port is automatically assigned.

        Parameters
        ----------
        ref_des_list : list, str
            List of one or more reference designators.

        net_list : list, str
            List of one or more nets.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        coax = []
        if not isinstance(ref_des_list, list):
            ref_des_list = [ref_des_list]
        if not isinstance(net_list, list):
            net_list = [net_list]
        for ref in ref_des_list:
            for _, py_inst in self._pedb.core_components.components[ref].pins.items():
                if py_inst.net_name in net_list and py_inst.is_pin:
                    port_name = "{}_{}_{}".format(ref, py_inst.net_name, py_inst.pin.GetName())
                    (
                        res,
                        from_layer_pos,
                        to_layer_pos,
                    ) = py_inst.pin.GetLayerRange()
                    if (
                        res
                        and from_layer_pos
                        and self._edb.Cell.Terminal.PadstackInstanceTerminal.Create(
                            self._active_layout,
                            py_inst.pin.GetNet(),
                            port_name,
                            py_inst.pin,
                            to_layer_pos,
                        )
                    ):
                        coax.append(port_name)
        return coax

    @pyaedt_function_handler
    def create_differential_wave_port(
        self,
        positive_primitive_id,
        positive_points_on_edge,
        negative_primitive_id,
        negative_points_on_edge,
        port_name=None,
        horizontal_extent_factor=5,
        vertical_extent_factor=3,
        pec_launch_width="0.01mm",
    ):
        """Create a differential wave port.

        Parameters
        ----------
        positive_primitive_id : int
            Primitive ID of the positive terminal.
        positive_points_on_edge : list
            Coordinate of the point to define the edge terminal.
            The point must be close to the target edge but not on the two
            ends of the edge.
        negative_primitive_id : int
            Primitive ID of the negative terminal.
        negative_points_on_edge : list
            Coordinate of the point to define the edge terminal.
            The point must be close to the target edge but not on the two
            ends of the edge.
        port_name : str, optional
            Name of the port. The default is ``None``.
        horizontal_extent_factor : int, float, optional
            Horizontal extent factor. The default value is ``5``.
        vertical_extent_factor : int, float, optional
            Vertical extent factor. The default value is ``3``.
        pec_launch_width : str, optional
            Launch Width of PEC. The default value is ``"0.01mm"``.

        Returns
        -------
        tuple
            The tuple contains: (port_name, pyaedt.edb_core.edb_data.sources.ExcitationDifferential).

        Examples
        --------
        >>> edb.core_hfss.create_differential_wave_port(0, ["-50mm", "-0mm"], 1, ["-50mm", "-0.2mm"])
        """
        if not port_name:
            port_name = generate_unique_name("diff")

        _, pos_term = self.create_wave_port(
            positive_primitive_id,
            positive_points_on_edge,
            port_name=port_name,
            horizontal_extent_factor=horizontal_extent_factor,
            vertical_extent_factor=vertical_extent_factor,
            pec_launch_width=pec_launch_width,
        )
        _, neg_term = self.create_edge_port_vertical(
            negative_primitive_id,
            negative_points_on_edge,
            horizontal_extent_factor=horizontal_extent_factor,
            vertical_extent_factor=vertical_extent_factor,
            pec_launch_width=pec_launch_width,
        )
        edb_list = convert_py_list_to_net_list(
            [pos_term._edb_terminal, neg_term._edb_terminal], self._edb.Cell.Terminal.Terminal
        )
        _edb_boundle_terminal = self._edb.Cell.Terminal.BundleTerminal.Create(edb_list)
        return port_name, ExcitationDifferential(self._pedb, _edb_boundle_terminal)

    @pyaedt_function_handler()
    def create_hfss_ports_on_padstack(self, pinpos, portname=None):
        """Create an HFSS port on a padstack.

        Parameters
        ----------
        pinpos :
            Position of the pin.

        portname : str, optional
             Name of the port. The default is ``None``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        res, fromLayer_pos, toLayer_pos = pinpos.GetLayerRange()

        if not portname:
            portname = generate_unique_name("Port_" + pinpos.GetNet().GetName())
        edbpointTerm_pos = self._edb.Cell.Terminal.PadstackInstanceTerminal.Create(
            self._active_layout, pinpos.GetNet(), portname, pinpos, toLayer_pos
        )
        if edbpointTerm_pos:
            return True
        else:
            return False

    @pyaedt_function_handler()
    def create_edge_port_on_polygon(
        self,
        polygon=None,
        reference_polygon=None,
        terminal_point=None,
        reference_point=None,
        reference_layer=None,
        port_name=None,
        port_impedance=50.0,
        force_circuit_port=False,
    ):
        """Create lumped port between two edges from two different polygons. Can also create a vertical port when
        the reference layer name is only provided. When a port is created between two edge from two polygons which don't
        belong to the same layer, a circuit port will be automatically created instead of lumped. To enforce the circuit
        port instead of lumped,use the boolean force_circuit_port.

        Parameters
        ----------
        polygon : The EDB polygon object used to assign the port.
            Edb.Cell.Primitive.Polygon object.

        reference_polygon : The EDB polygon object used to define the port reference.
            Edb.Cell.Primitive.Polygon object.

        terminal_point : The coordinate of the point to define the edge terminal of the port. This point must be
        located on the edge of the polygon where the port has to be placed. For instance taking the middle point
        of an edge is a good practice but any point of the edge should be valid. Taking a corner might cause unwanted
        port location.
            list[float, float] with values provided in meter.

        reference_point : same as terminal_point but used for defining the reference location on the edge.
            list[float, float] with values provided in meter.

        reference_layer : Name used to define port reference for vertical ports.
            str the layer name.

        port_name : Name of the port.
            str.

        port_impedance : port impedance value. Default value is 50 Ohms.
            float, impedance value.

        force_circuit_port ; used to force circuit port creation instead of lumped. Works for vertical and coplanar
        ports.

        Examples
        --------

        >>> edb_path = path_to_edb
        >>> edb = Edb(edb_path)
        >>> poly_list = [poly for poly in list(edb.active_layout.Primitives) if poly.GetPrimitiveType() == 2]
        >>> port_poly = [poly for poly in poly_list if poly.GetId() == 17][0]
        >>> ref_poly = [poly for poly in poly_list if poly.GetId() == 19][0]
        >>> port_location = [-65e-3, -13e-3]
        >>> ref_location = [-63e-3, -13e-3]
        >>> edb.core_hfss.create_edge_port_on_polygon(polygon=port_poly, reference_polygon=ref_poly,
        >>> terminal_point=port_location, reference_point=ref_location)

        """
        if not polygon:
            self._logger.error("No polygon provided for port {} creation".format(port_name))
            return False
        if reference_layer:
            reference_layer = self._pedb.stackup.signal_layers[reference_layer]._edb_layer
            if not reference_layer:
                self._logger.error("Specified layer for port {} creation was not found".format(port_name))
        if not isinstance(terminal_point, list):
            self._logger.error("Terminal point must be a list of float with providing the point location in meter")
            return False
        terminal_point = self._edb.Geometry.PointData(
            self._get_edb_value(terminal_point[0]), self._get_edb_value(terminal_point[1])
        )
        if reference_point and isinstance(reference_point, list):
            reference_point = self._edb.Geometry.PointData(
                self._get_edb_value(reference_point[0]), self._get_edb_value(reference_point[1])
            )
        if not port_name:
            port_name = generate_unique_name("Port_")
        edge = self._edb.Cell.Terminal.PrimitiveEdge.Create(polygon, terminal_point)
        edges = convert_py_list_to_net_list(edge, self._edb.Cell.Terminal.Edge)
        edge_term = self._edb.Cell.Terminal.EdgeTerminal.Create(
            polygon.GetLayout(), polygon.GetNet(), port_name, edges, isRef=False
        )
        if force_circuit_port:
            edge_term.SetIsCircuitPort(True)
        if port_impedance:
            edge_term.SetImpedance(self._pedb.edb_value(port_impedance))
        edge_term.SetName(port_name)
        if reference_polygon and reference_point:
            ref_edge = self._edb.Cell.Terminal.PrimitiveEdge.Create(reference_polygon, reference_point)
            ref_edges = convert_py_list_to_net_list(ref_edge, self._edb.Cell.Terminal.Edge)
            ref_edge_term = self._edb.Cell.Terminal.EdgeTerminal.Create(
                reference_polygon.GetLayout(), reference_polygon.GetNet(), port_name + "_ref", ref_edges, isRef=True
            )
            if reference_layer:
                ref_edge_term.SetReferenceLayer(reference_layer)
            if force_circuit_port:
                ref_edge_term.SetIsCircuitPort(True)
            if port_impedance:
                ref_edge_term.SetImpedance(self._pedb.edb_value(port_impedance))
            edge_term.SetReferenceTerminal(ref_edge_term)
        return True

    @pyaedt_function_handler()
    def create_wave_port(
        self,
        prim_id,
        point_on_edge,
        port_name=None,
        impedance=50,
        horizontal_extent_factor=5,
        vertical_extent_factor=3,
        pec_launch_width="0.01mm",
    ):
        """Create a wave port.

        Parameters
        ----------
        prim_id : int
            Primitive ID.
        point_on_edge : list
            Coordinate of the point to define the edge terminal.
            The point must be on the target edge but not on the two
            ends of the edge.
        port_name : str, optional
            Name of the port. The default is ``None``.
        impedance : int, float, optional
            Impedance of the port. The default value is ``50``.
        horizontal_extent_factor : int, float, optional
            Horizontal extent factor. The default value is ``5``.
        vertical_extent_factor : int, float, optional
            Vertical extent factor. The default value is ``3``.
        pec_launch_width : str, optional
            Launch Width of PEC. The default value is ``"0.01mm"``.

        Returns
        -------
        tuple
            The tuple contains: (Port name, pyaedt.edb_core.edb_data.sources.Excitation).

        Examples
        --------
        >>> edb.core_hfss.create_wave_port(0, ["-50mm", "-0mm"])
        """
        if not port_name:
            port_name = generate_unique_name("Terminal_")
        pos_edge_term = self._create_edge_terminal(prim_id, point_on_edge, port_name)
        pos_edge_term.SetImpedance(self._pedb.edb_value(impedance))

        prop = ", ".join(
            [
                "HFSS('HFSS Type'='Wave'",
                " 'Horizontal Extent Factor'='{}'".format(horizontal_extent_factor),
                " 'Vertical Extent Factor'='{}'".format(vertical_extent_factor),
                " 'PEC Launch Width'='{}')".format(pec_launch_width),
            ]
        )
        pos_edge_term.SetProductSolverOption(
            self._pedb.edb.ProductId.Designer,
            "HFSS",
            prop,
        )
        if pos_edge_term:
            return port_name, self._pedb.core_hfss.excitations[port_name]
        else:
            return False

    @pyaedt_function_handler()
    def create_edge_port_vertical(
        self,
        prim_id,
        point_on_edge,
        port_name=None,
        impedance=50,
        reference_layer=None,
        hfss_type="Gap",
        horizontal_extent_factor=5,
        vertical_extent_factor=3,
        pec_launch_width="0.01mm",
    ):
        """Create a vertical edge port.

        Parameters
        ----------
        prim_id : int
            Primitive ID.
        point_on_edge : list
            Coordinate of the point to define the edge terminal.
            The point must be on the target edge but not on the two
            ends of the edge.
        port_name : str, optional
            Name of the port. The default is ``None``.
        impedance : int, float, optional
            Impedance of the port. The default value is ``50``.
        reference_layer : str, optional
            Reference layer of the port. The default is ``None``.
        hfss_type : str, optional
            Type of the port. The default value is ``"Gap"``. Options are ``"Gap"``, ``"Wave"``.
        horizontal_extent_factor : int, float, optional
            Horizontal extent factor. The default value is ``5``.
        vertical_extent_factor : int, float, optional
            Vertical extent factor. The default value is ``3``.
        radial_extent_factor : int, float, optional
            Radial extent factor. The default value is ``0``.
        pec_launch_width : str, optional
            Launch Width of PEC. The default value is ``"0.01mm"``.
        Returns
        -------
        str
            Port name.
        """
        if not port_name:
            port_name = generate_unique_name("Terminal_")
        pos_edge_term = self._create_edge_terminal(prim_id, point_on_edge, port_name)
        pos_edge_term.SetImpedance(self._pedb.edb_value(impedance))
        if reference_layer:
            reference_layer = self._pedb.stackup.signal_layers[reference_layer]._edb_layer
            pos_edge_term.SetReferenceLayer(reference_layer)

        prop = ", ".join(
            [
                "HFSS('HFSS Type'='{}'".format(hfss_type),
                " Orientation='Vertical'",
                " 'Layer Alignment'='Upper'",
                " 'Horizontal Extent Factor'='{}'".format(horizontal_extent_factor),
                " 'Vertical Extent Factor'='{}'".format(vertical_extent_factor),
                " 'PEC Launch Width'='{}')".format(pec_launch_width),
            ]
        )
        pos_edge_term.SetProductSolverOption(
            self._pedb.edb.ProductId.Designer,
            "HFSS",
            prop,
        )
        if pos_edge_term:
            return port_name, self._pedb.core_hfss.excitations[port_name]
        else:
            return False

    @pyaedt_function_handler()
    def create_edge_port_horizontal(
        self,
        prim_id,
        point_on_edge,
        ref_prim_id=None,
        point_on_ref_edge=None,
        port_name=None,
        impedance=50,
        layer_alignment="Upper",
    ):
        """Create a horizontal edge port.

        Parameters
        ----------
        prim_id : int
            Primitive ID.
        point_on_edge : list
            Coordinate of the point to define the edge terminal.
            The point must be on the target edge but not on the two
            ends of the edge.
        ref_prim_id : int, optional
            Reference primitive ID. The default is ``None``.
        point_on_ref_edge : list, optional
            Coordinate of the point to define the reference edge
            terminal. The point must be on the target edge but not
            on the two ends of the edge. The default is ``None``.
        port_name : str, optional
            Name of the port. The default is ``None``.
        impedance : int, float, optional
            Impedance of the port. The default value is ``50``.
        layer_alignment : str, optional
            Layer alignment. The default value is ``Upper``. Options are ``"Upper"``, ``"Lower"``.
        Returns
        -------
        str
            Name of the port.
        """
        pos_edge_term = self._create_edge_terminal(prim_id, point_on_edge, port_name)
        neg_edge_term = self._create_edge_terminal(ref_prim_id, point_on_ref_edge, port_name + "_ref", is_ref=True)

        pos_edge_term.SetImpedance(self._pedb.edb_value(impedance))
        pos_edge_term.SetReferenceTerminal(neg_edge_term)
        if not layer_alignment == "Upper":
            layer_alignment = "Lower"
        pos_edge_term.SetProductSolverOption(
            self._pedb.edb.ProductId.Designer,
            "HFSS",
            "HFSS('HFSS Type'='Gap(coax)', Orientation='Horizontal', 'Layer Alignment'='{}')".format(layer_alignment),
        )
        if pos_edge_term:
            return port_name
        else:
            return False

    @pyaedt_function_handler()
    def create_lumped_port_on_net(
        self, nets=None, reference_layer=None, return_points_only=False, digit_resolution=6, at_bounding_box=True
    ):
        """Create an edge port on nets. Only ports on traces (e.g. Path) are currently supported.
        The command will look for traces on the nets and will try to assign vertical lumped port on first and last
        point from the trace. To be used with cautious.

        Parameters
        ----------
        nets : list, optional
            List of nets, str or Edb net.

        reference_layer : str, Edb layer.
             Name or Edb layer object.

        return_points_only : bool, optional
            Use this boolean when you want to return only the points from the edges and not creating ports. Default
            value is ``False``.

        digit_resolution : int, optional
            The number of digits carried for the edge location accuracy. The default value is ``6``.

        at_bounding_box : bool
            When ``True`` will keep the edges from traces at the layout bounding box location. This is recommended when
             a cutout has been performed before and lumped ports have to be created on ending traces. Default value is
             ``True``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if not isinstance(nets, list):
            if isinstance(nets, str):
                nets = [self._edb.Cell.Net.FindByName(self._active_layout, nets)]
            elif isinstance(nets, self._edb.Cell.Net):
                nets = [nets]
        else:
            temp_nets = []
            for nn in nets:
                if isinstance(nn, str):
                    temp_nets.append(self._edb.Cell.Net.FindByName(self._active_layout, nn))
                elif isinstance(nn, self._edb.Cell.Net):
                    temp_nets.append(nn)
            nets = temp_nets
        if nets:
            edges_pts = []
            if isinstance(reference_layer, str):
                try:
                    reference_layer = self._pedb.stackup.signal_layers[reference_layer]._edb_layer
                except:
                    raise Exception("Failed to get the layer {}".format(reference_layer))
            if not isinstance(reference_layer, self._edb.Cell.ILayerReadOnly):
                return False
            layout = nets[0].GetLayout()
            layout_bbox = self.get_layout_bounding_box(layout, digit_resolution)
            for net in nets:
                net_primitives = list(net.Primitives)
                net_paths = [
                    pp for pp in net_primitives if pp.GetPrimitiveType() == self._edb.Cell.Primitive.PrimitiveType.Path
                ]
                for path in net_paths:
                    trace_path_pts = list(path.GetCenterLine().Points)
                    port_name = "{}_{}".format(net.GetName(), path.GetId())
                    for pt in trace_path_pts:
                        _pt = [
                            round(pt.X.ToDouble(), digit_resolution),
                            round(pt.Y.ToDouble(), digit_resolution),
                        ]
                        if at_bounding_box:
                            if not set(layout_bbox).isdisjoint(_pt):
                                if return_points_only:
                                    edges_pts.append(_pt)
                                else:
                                    term = self._create_edge_terminal(path, pt, port_name)  # pragma no cover
                                    term.SetReferenceLayer(reference_layer)  # pragma no cover
                        else:
                            if return_points_only:  # pragma: no cover
                                edges_pts.append(_pt)
                            else:
                                term = self._create_edge_terminal(path, pt, port_name)
                                term.SetReferenceLayer(reference_layer)

            if return_points_only:
                return edges_pts
        return True

    @pyaedt_function_handler()
    def get_layout_bounding_box(self, layout=None, digit_resolution=6):
        """Evaluate the layout bounding box.

        Parameters
        ----------
        layout :
            Edb layout.

        digit_resolution : int, optional
            Digit Resolution. The default value is ``6``.
        Returns
        -------
        list
            [lower left corner X, lower left corner, upper right corner X, upper right corner Y]
        """
        if layout == None:
            return False
        layout_obj_instances = layout.GetLayoutInstance().GetAllLayoutObjInstances()
        tuple_list = []
        for lobj in layout_obj_instances.Items:
            lobj_bbox = lobj.GetLayoutInstanceContext().GetBBox(False)
            tuple_list.append(lobj_bbox)
        _bbox = self._edb.Geometry.PolygonData.GetBBoxOfBoxes(convert_py_list_to_net_list(tuple_list))
        layout_bbox = [
            round(_bbox.Item1.X.ToDouble(), digit_resolution),
            round(_bbox.Item1.Y.ToDouble(), digit_resolution),
            round(_bbox.Item2.X.ToDouble(), digit_resolution),
            round(_bbox.Item2.Y.ToDouble(), digit_resolution),
        ]
        return layout_bbox

    @pyaedt_function_handler()
    def create_circuit_ports_on_components_no_pin_group(
        self,
        signal_nets=None,
        power_nets=None,
        simulation_setup=None,
        component_list=None,
    ):
        """Create circuit ports on given components.
        For each component, create a coplanar circuit port at each signalNet pin.
        Use the closest powerNet pin as a reference, regardless of component.

        Parameters
        ----------
        signal_nets : list, optional if simulation_setup is provided
            List of signal net names. This list is ignored if a ``simulation_setup`` object is provided.

        power_nets : list, optional if a ``simulatiom_setup`` object is provided
            List of power net names. This list is ignored if a ``simulation_setup`` object
            is provided.

        component_list : list optional if simulatiom_setup provided.
            The list of component names. will be ignored if simulation_setup object is provided

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if simulation_setup:
            if not isinstance(simulation_setup, SimulationConfiguration):
                self._logger.error(
                    "simulation setup was provided but must be an instance of \
                    edb_data.simulation_configuration.SimulationConfiguration"
                )
                return False
            signal_nets = simulation_setup.signal_nets
            power_nets = simulation_setup.power_nets
            component_list = simulation_setup.coplanar_instances
        else:
            if not component_list:
                return False

        if not simulation_setup.coplanar_instances:
            return False

        layout = self._active_layout
        l_inst = layout.GetLayoutInstance()
        edb_power_nets = [self._pedb.core_nets.find_or_create_net(net) for net in power_nets]
        for inst in component_list:
            comp = self._edb.Cell.Hierarchy.Component.FindByName(layout, inst)
            if comp.IsNull():
                self._logger.warning("SetupCoplanarInstances: could not find {0}".format(inst))
                continue
            # Get the portLayer based on the component's pin placement
            cmp_layer = self._edb.Cell.Hierarchy.Component.GetPlacementLayer(comp)
            # Get the bbox of the comp
            bb = self._edb.Geometry.PolygonData.CreateFromBBox(l_inst.GetLayoutObjInstance(comp, None).GetBBox())
            bb_c = bb.GetBoundingCircleCenter()
            # Expand x5 to create testing polygon...
            bb.Scale(5, bb_c)
            # Find the closest pin in the Ground/Power nets...
            hit = l_inst.FindLayoutObjInstance(bb, cmp_layer, convert_py_list_to_net_list(edb_power_nets))
            all_hits = [list(hit.Item1.Items) + list(hit.Item2.Items)]
            hit_pinsts = [
                obj
                for obj in all_hits
                if obj.GetLayoutObj().GetObjType() == self._edb.Cell.LayoutObjType.PadstackInstance
            ]
            if not hit_pinsts:
                self._logger.error("SetupCoplanarInstances: could not find a pin in the vicinity of {0}".format(inst))
                continue
            # Iterate each pin in the component that's on the signal nets and create a circuit port
            pin_list = [
                obj
                for obj in list(comp.LayoutObjs)
                if obj.GetObjType() == self._edb.Cell.LayoutObjType.PadstackInstance
                and obj.GetNet().GetName() in signal_nets
            ]
            for ii, pin in enumerate(pin_list):
                pin_c = l_inst.GetLayoutObjInstance(pin, None).GetCenter()
                ref_pinst = None
                ref_pt = None
                ref_dist = None
                for hhLoi in hit_pinsts:
                    this_c = hhLoi.GetCenter()
                    this_dist = this_c.Distance(pin_c)
                    if ref_pt is None or this_dist < ref_dist:
                        ref_pinst = hhLoi.GetLayoutObj()
                        ref_pt = this_c
                        ref_dist = this_dist

                port_nm = "PORT_{0}_{1}@{2}".format(comp.GetName(), ii, pin.GetNet().GetName())
                ## TO complete and check for embefing in create_port_on_component
                ###########################
                ###########################
                self._edbutils.HfssUtilities.CreateCircuitPortFromPoints(
                    port_nm,
                    layout,
                    pin_c,
                    cmp_layer,
                    pin.GetNet(),
                    ref_pt,
                    cmp_layer,
                    ref_pinst.GetNet(),
                )
        return True

    @pyaedt_function_handler()
    def configure_hfss_extents(self, simulation_setup=None):
        """Configure the HFSS extent box.

        Parameters
        ----------
        simulation_setup :
            Edb_DATA.SimulationConfiguration object

        Returns
        -------
        bool
            True when succeeded, False when failed.
        """

        if not isinstance(simulation_setup, SimulationConfiguration):
            self._logger.error(
                "Configure HFSS extent requires edb_data.simulation_configuration.SimulationConfiguration object"
            )
            return False
        hfss_extent = self._edb.Utility.HFSSExtentInfo()
        if simulation_setup.radiation_box == RadiationBoxType.BoundingBox:
            hfss_extent.ExtentType = self._edb.Utility.HFSSExtentInfoType.BoundingBox
        elif simulation_setup.radiation_box == RadiationBoxType.Conformal:
            hfss_extent.ExtentType = self._edb.Utility.HFSSExtentInfoType.Conforming
        else:
            hfss_extent.ExtentType = self._edb.Utility.HFSSExtentInfoType.ConvexHull
        hfss_extent.DielectricExtentSize = convert_pytuple_to_nettuple((simulation_setup.dielectric_extent, True))
        hfss_extent.AirBoxHorizontalExtent = convert_pytuple_to_nettuple(
            (simulation_setup.airbox_horizontal_extent, True)
        )
        hfss_extent.AirBoxNegativeVerticalExtent = convert_pytuple_to_nettuple(
            (simulation_setup.airbox_negative_vertical_extent, True)
        )
        hfss_extent.AirBoxPositiveVerticalExtent = convert_pytuple_to_nettuple(
            (simulation_setup.airbox_positive_vertical_extent, True)
        )
        hfss_extent.HonorUserDielectric = simulation_setup.honor_user_dielectric
        hfss_extent.TruncateAirBoxAtGround = simulation_setup.truncate_airbox_at_ground
        hfss_extent.UseOpenRegion = simulation_setup.use_radiation_boundary
        self._active_layout.GetCell().SetHFSSExtentInfo(hfss_extent)  # returns void
        return True

    @pyaedt_function_handler()
    def configure_hfss_analysis_setup(self, simulation_setup=None):
        """
        Configure HFSS analysis setup.

        Parameters
        ----------
        simulation_setup :
            Edb_DATA.SimulationConfiguration object

        Returns
        -------
        bool
            True when succeeded, False when failed.
        """
        if not isinstance(simulation_setup, SimulationConfiguration):
            self._logger.error(
                "Configure HFSS analysis requires and edb_data.simulation_configuration.SimulationConfiguration object \
                               as argument"
            )
            return False
        adapt = self._pedb.simsetupdata.AdaptiveFrequencyData()
        adapt.AdaptiveFrequency = simulation_setup.mesh_freq
        adapt.MaxPasses = int(simulation_setup.max_num_passes)
        adapt.MaxDelta = str(simulation_setup.max_mag_delta_s)
        simsetup_info = self._pedb.simsetupdata.SimSetupInfo[self._pedb.simsetupdata.HFSSSimulationSettings]()
        simsetup_info.Name = simulation_setup.setup_name

        simsetup_info.SimulationSettings.CurveApproxSettings.ArcAngle = simulation_setup.arc_angle
        simsetup_info.SimulationSettings.CurveApproxSettings.UseArcToChordError = (
            simulation_setup.use_arc_to_chord_error
        )
        simsetup_info.SimulationSettings.CurveApproxSettings.ArcToChordError = simulation_setup.arc_to_chord_error
        if is_ironpython:
            simsetup_info.SimulationSettings.AdaptiveSettings.AdaptiveFrequencyDataList.Clear()
            simsetup_info.SimulationSettings.AdaptiveSettings.AdaptiveFrequencyDataList.Add(adapt)
        else:
            simsetup_info.SimulationSettings.AdaptiveSettings.AdaptiveFrequencyDataList = convert_py_list_to_net_list(
                [adapt]
            )
        simsetup_info.SimulationSettings.InitialMeshSettings.LambdaRefine = simulation_setup.do_lambda_refinement
        if simulation_setup.mesh_sizefactor > 0.0:
            simsetup_info.SimulationSettings.InitialMeshSettings.MeshSizefactor = simulation_setup.mesh_sizefactor
            simsetup_info.SimulationSettings.InitialMeshSettings.LambdaRefine = False
        simsetup_info.SimulationSettings.AdaptiveSettings.MaxRefinePerPass = 30
        simsetup_info.SimulationSettings.AdaptiveSettings.MinPasses = simulation_setup.min_num_passes
        simsetup_info.SimulationSettings.AdaptiveSettings.MinConvergedPasses = 1
        simsetup_info.SimulationSettings.HFSSSolverSettings.OrderBasis = simulation_setup.basis_order
        simsetup_info.SimulationSettings.HFSSSolverSettings.UseHFSSIterativeSolver = False
        simsetup_info.SimulationSettings.DefeatureSettings.UseDefeature = False  # set True when using defeature ratio
        simsetup_info.SimulationSettings.DefeatureSettings.UseDefeatureAbsLength = simulation_setup.defeature_layout
        simsetup_info.SimulationSettings.DefeatureSettings.DefeatureAbsLength = simulation_setup.defeature_abs_length

        try:
            sweep = self._pedb.simsetupdata.SweepData(simulation_setup.sweep_name)
            sweep.IsDiscrete = False
            sweep.UseQ3DForDC = simulation_setup.use_q3d_for_dc
            sweep.RelativeSError = simulation_setup.relative_error
            sweep.InterpUsePortImpedance = False
            sweep.EnforceCausality = simulation_setup.enforce_causality
            # sweep.EnforceCausality = False
            sweep.EnforcePassivity = simulation_setup.enforce_passivity
            sweep.PassivityTolerance = simulation_setup.passivity_tolerance
            sweep.Frequencies.Clear()

            if simulation_setup.sweep_type == SweepType.LogCount:  # setup_info.SweepType == 'DecadeCount'
                self._setup_decade_count_sweep(
                    sweep,
                    str(simulation_setup.start_freq),
                    str(simulation_setup.stop_freq),
                    str(simulation_setup.decade_count),
                )  # Added DecadeCount as a new attribute

            else:
                sweep.Frequencies = self._pedb.simsetupdata.SweepData.SetFrequencies(
                    simulation_setup.start_freq,
                    simulation_setup.stop_freq,
                    simulation_setup.step_freq,
                )

            simsetup_info.SweepDataList.Add(sweep)

        except Exception as err:
            self._logger.error("Exception in Sweep configuration: {0}".format(err))

        sim_setup = self._edb.Utility.HFSSSimulationSetup(simsetup_info)
        for setup in self._active_layout.GetCell().SimulationSetups:
            self._active_layout.GetCell().DeleteSimulationSetup(setup.GetName())
            self._logger.warning("Setup {} has been deleted".format(setup.GetName()))
        return self._active_layout.GetCell().AddSimulationSetup(sim_setup)

    def _setup_decade_count_sweep(self, sweep, start_freq="1", stop_freq="1MHz", decade_count="10"):
        start_f = GeometryOperators.parse_dim_arg(start_freq)
        if start_f == 0.0:
            start_f = 10
            self._logger.warning("Decade Count sweep does not support DC value, defaulting starting frequency to 10Hz")

        stop_f = GeometryOperators.parse_dim_arg(stop_freq)
        decade_cnt = GeometryOperators.parse_dim_arg(decade_count)
        freq = start_f
        sweep.Frequencies.Add(str(freq))

        while freq < stop_f:
            freq = freq * math.pow(10, 1.0 / decade_cnt)
            sweep.Frequencies.Add(str(freq))

    @pyaedt_function_handler()
    def trim_component_reference_size(self, simulation_setup=None, trim_to_terminals=False):
        """Trim the common component reference to the minimally acceptable size.

        Parameters
        ----------
        simulation_setup :
            Edb_DATA.SimulationConfiguration object

        trim_to_terminals :
            bool.
                True, reduce the reference to a box covering only the active terminals (i.e. those with
        ports).
                False, reduce the reference to the minimal size needed to cover all pins

        Returns
        -------
        bool
            True when succeeded, False when failed.
        """

        if not isinstance(simulation_setup, SimulationConfiguration):
            self._logger.error(
                "Trim component reference size requires an edb_data.simulation_configuration.SimulationConfiguration \
                    object as argument"
            )
            return False

        if not simulation_setup.components:  # pragma: no cover
            return

        layout = self._cell.GetLayout()
        l_inst = layout.GetLayoutInstance()

        for inst in simulation_setup.components:  # pragma: no cover
            comp = self._edb.Cell.Hierarchy.Component.FindByName(layout, inst)
            if comp.IsNull():
                continue

            terms_bbox_pts = self._get_terminals_bbox(comp, l_inst, trim_to_terminals)
            if not terms_bbox_pts:
                continue

            terms_bbox = self._edb.Geometry.PolygonData.CreateFromBBox(terms_bbox_pts)

            if trim_to_terminals:
                # Remove any pins that aren't interior to the Terminals bbox
                pin_list = [
                    obj
                    for obj in list(comp.LayoutObjs)
                    if obj.GetObjType() == self._edb.Cell.LayoutObjType.PadstackInstance
                ]
                for pin in pin_list:
                    loi = l_inst.GetLayoutObjInstance(pin, None)
                    bb_c = loi.GetCenter()
                    if not terms_bbox.PointInPolygon(bb_c):
                        comp.RemoveMember(pin)

            # Set the port property reference size
            cmp_prop = comp.GetComponentProperty().Clone()
            port_prop = cmp_prop.GetPortProperty().Clone()
            port_prop.SetReferenceSizeAuto(False)
            port_prop.SetReferenceSize(
                terms_bbox_pts.Item2.X.ToDouble() - terms_bbox_pts.Item1.X.ToDouble(),
                terms_bbox_pts.Item2.Y.ToDouble() - terms_bbox_pts.Item1.Y.ToDouble(),
            )
            cmp_prop.SetPortProperty(port_prop)
            comp.SetComponentProperty(cmp_prop)
            return True

    @pyaedt_function_handler()
    def set_coax_port_attributes(self, simulation_setup=None):
        """Set coaxial port attribute with forcing default impedance to 50 Ohms and adjusting the coaxial extent radius.

        Parameters
        ----------
        simulation_setup :
            Edb_DATA.SimulationConfiguration object.

        Returns
        -------
        bool
            True when succeeded, False when failed.
        """

        if not isinstance(simulation_setup, SimulationConfiguration):
            self._logger.error(
                "Set coax port attribute requires an edb_data.simulation_configuration.SimulationConfiguration object \
            as argument."
            )
            return False
        net_names = [net.GetName() for net in list(self._active_layout.Nets) if not net.IsPowerGround()]
        cmp_names = (
            simulation_setup.components
            if simulation_setup.components
            else [gg.GetName() for gg in self._active_layout.Groups]
        )
        ii = 0
        for cc in cmp_names:
            cmp = self._edb.Cell.Hierarchy.Component.FindByName(self._active_layout, cc)
            if cmp.IsNull():
                self._logger.warning("RenamePorts: could not find component {0}".format(cc))
                continue
            terms = [obj for obj in list(cmp.LayoutObjs) if obj.GetObjType() == self._edb.Cell.LayoutObjType.Terminal]
            for nn in net_names:
                for tt in [term for term in terms if term.GetNet().GetName() == nn]:
                    if not tt.SetImpedance(self._pedb.edb_value("50ohm")):
                        self._logger.warning("Could not set terminal {0} impedance as 50ohm".format(tt.GetName()))
                        continue
                    ii += 1

            if not simulation_setup.use_default_coax_port_radial_extension:
                # Set the Radial Extent Factor
                typ = cmp.GetComponentType()
                if typ in [
                    self._edb.Definition.ComponentType.Other,
                    self._edb.Definition.ComponentType.IC,
                    self._edb.Definition.ComponentType.IO,
                ]:
                    cmp_prop = cmp.GetComponentProperty().Clone()
                    (
                        success,
                        diam1,
                        diam2,
                    ) = cmp_prop.GetSolderBallProperty().GetDiameter()
                    if success and diam1 and diam2 > 0:  # pragma: no cover
                        option = (
                            "HFSS('HFSS Type'='**Invalid**', "
                            "Orientation='**Invalid**', "
                            "'Layer Alignment'='Upper', "
                            "'Horizontal Extent Factor'='5', "
                            "'Vertical Extent Factor'='3', "
                            "'Radial Extent Factor'='0.25', "
                            "'PEC Launch Width'='0mm')"
                        )
                        for tt in terms:
                            tt.SetProductSolverOption(self._edb.ProductId.Designer, "HFSS", option)
        return True

    @pyaedt_function_handler()
    def _get_terminals_bbox(self, comp, l_inst, terminals_only):
        terms_loi = []
        if terminals_only:
            term_list = [
                obj for obj in list(comp.LayoutObjs) if obj.GetObjType() == self._edb.Cell.LayoutObjType.Terminal
            ]
            for tt in term_list:
                success, p_inst, lyr = tt.GetParameters()
                if success and lyr:
                    loi = l_inst.GetLayoutObjInstance(p_inst, None)
                    terms_loi.append(loi)
        else:
            pin_list = [
                obj
                for obj in list(comp.LayoutObjs)
                if obj.GetObjType() == self._edb.Cell.LayoutObjType.PadstackInstance
            ]
            for pi in pin_list:
                loi = l_inst.GetLayoutObjInstance(pi, None)
                terms_loi.append(loi)

        if len(terms_loi) == 0:
            return None

        terms_bbox = []
        for loi in terms_loi:
            # Need to account for the coax port dimension
            bb = loi.GetBBox()
            ll = [bb.Item1.X.ToDouble(), bb.Item1.Y.ToDouble()]
            ur = [bb.Item2.X.ToDouble(), bb.Item2.Y.ToDouble()]
            # dim = 0.26 * max(abs(UR[0]-LL[0]), abs(UR[1]-LL[1]))  # 0.25 corresponds to the default 0.5
            # Radial Extent Factor, so set slightly larger to avoid validation errors
            dim = 0.30 * max(abs(ur[0] - ll[0]), abs(ur[1] - ll[1]))  # 0.25 corresponds to the default 0.5
            terms_bbox.append(self._edb.Geometry.PolygonData(ll[0] - dim, ll[1] - dim, ur[0] + dim, ur[1] + dim))
        return self._edb.Geometry.PolygonData.GetBBoxOfPolygons(convert_py_list_to_net_list(terms_bbox))

    @pyaedt_function_handler()
    def get_ports_number(self):
        """Return the total number of excitation ports in a layout.

        Parameters
        ----------
        None

        Returns
        -------
        int
           Number of ports.

        """
        terms = [term for term in list(self._active_layout.Terminals) if int(term.GetBoundaryType()) == 0]
        return len([i for i in terms if not i.IsReferenceTerminal()])

    @pyaedt_function_handler()
    def layout_defeaturing(self, simulation_setup=None):
        """Defeature the layout by reducing the number of points for polygons based on surface deviation criteria.

        Parameters
        ----------
        simulation_setup : Edb_DATA.SimulationConfiguration object

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        if not isinstance(simulation_setup, SimulationConfiguration):
            self._logger.error(
                "Layout defeaturing requires an edb_data.simulation_configuration.SimulationConfiguration object."
            )
            return False
        self._logger.info("Starting Layout Defeaturing")
        polygon_list = self._pedb.core_primitives.polygons
        polygon_with_voids = self._pedb.core_layout.get_poly_with_voids(polygon_list)
        self._logger.info("Number of polygons with voids found: {0}".format(str(polygon_with_voids.Count)))
        for _poly in polygon_list:
            voids_from_current_poly = _poly.Voids
            new_poly_data = self._pedb.core_layout.defeature_polygon(setup_info=simulation_setup, poly=_poly)
            _poly.SetPolygonData(new_poly_data)
            if len(voids_from_current_poly) > 0:
                for void in voids_from_current_poly:
                    void_data = void.GetPolygonData()
                    if void_data.Area() < float(simulation_setup.minimum_void_surface):
                        void.Delete()
                        self._logger.warning(
                            "Defeaturing Polygon {0}: Deleting Void {1} area is lower than the minimum criteria".format(
                                str(_poly.GetId()), str(void.GetId())
                            )
                        )
                    else:
                        self._logger.info(
                            "Defeaturing polygon {0}: void {1}".format(str(_poly.GetId()), str(void.GetId()))
                        )
                        new_void_data = self._pedb.core_layout.defeature_polygon(
                            setup_info=simulation_setup, poly=void_data
                        )
                        void.SetPolygonData(new_void_data)

        return True

    @pyaedt_function_handler()
    def create_rlc_boundary_on_pins(self, positive_pin=None, negative_pin=None, rvalue=0.0, lvalue=0.0, cvalue=0.0):
        """Create hfss rlc boundary on pins.

        Parameters
        ----------
        positive_pin : Positive pin.
            Edb.Cell.Primitive.PadstackInstance

        negative_pin : Negative pin.
            Edb.Cell.Primitive.PadstackInstance

        rvalue : Resistance value

        lvalue : Inductance value

        cvalue . Capacitance value.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """

        if positive_pin and negative_pin:
            positive_pin_term = self._pedb.core_components._create_terminal(positive_pin)
            negative_pin_term = self._pedb.core_components._create_terminal(negative_pin)
            positive_pin_term.SetBoundaryType(self._edb.Cell.Terminal.BoundaryType.RlcBoundary)
            negative_pin_term.SetBoundaryType(self._edb.Cell.Terminal.BoundaryType.RlcBoundary)
            rlc = self._edb.Utility.Rlc()
            rlc.IsParallel = True
            rlc.REnabled = True
            rlc.LEnabled = True
            rlc.CEnabled = True
            rlc.R = self._get_edb_value(rvalue)
            rlc.L = self._get_edb_value(lvalue)
            rlc.C = self._get_edb_value(cvalue)
            positive_pin_term.SetRlcBoundaryParameters(rlc)
            term_name = "{}_{}_{}".format(
                positive_pin.GetComponent().GetName(), positive_pin.GetNet().GetName(), positive_pin.GetName()
            )
            positive_pin_term.SetName(term_name)
            negative_pin_term.SetName("{}_ref".format(term_name))
            positive_pin_term.SetReferenceTerminal(negative_pin_term)
            return True
        return False  # pragma no cover
