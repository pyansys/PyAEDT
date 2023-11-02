from pyaedt.edb_core.dotnet.database import NetDotNet
from pyaedt.edb_core.dotnet.primitive import cast
from pyaedt.edb_core.general import convert_py_list_to_net_list


class LayoutDotNet:
    """Layout."""

    def __init__(self, app):
        """Initialize a new layout.

        Parameters
        ----------
        msg : EDBObjMessage
        """
        self._app = app
        self._cell = app._active_cell
        self._edb_api = app._edb
        self._layout = self._cell.GetLayout()
        self._layout_instance = None

    @property
    def cell(self):
        """:class:`Cell <ansys.edb.layout.Cell>`: Owning cell for this layout.

        Read-Only.
        """
        return self._cell

    @property
    def layer_collection(self):
        """:class:`LayerCollection <ansys.edb.layer.LayerCollection>` : Layer collection of this layout."""
        return self._layout.GetLayerCollection()

    @layer_collection.setter
    def layer_collection(self, layer_collection):
        """Set layer collection."""
        self._layout.SetLayerCollection(layer_collection)

    @property
    def primitives(self):
        """List of primitives.Read-Only.

        Returns
        -------
        list of :class:`pyaedt.edb_core.dotnet.primitive.PrimitiveDotNet` cast objects.
        """
        return [cast(self._app, i) for i in list(self._layout.Primitives)]

    @property
    def padstack_instances(self):
        """:obj:`list` of :class:`PadstackInstance <ansys.edb.primitive.PadstackInstance>` : List of all padstack \
        instances in this layout.

        Read-Only.
        """
        return list(self._layout.PadstackInstances)

    @property
    def terminals(self):
        """:obj:`list` of :class:`Terminal <ansys.edb.terminal.Terminal>` : List of all the terminals in this layout.

        Read-Only.
        """
        return list(self._layout.Terminals)

    @property
    def cell_instances(self):
        """:obj:`list` of :class:`CellInstance <ansys.edb.hierarchy.CellInstances>` : List of the cell instances in \
        this layout.

        Read-Only.
        """
        return list(self._layout.CellInstances)

    @property
    def nets(self):
        """:obj:`list` of :class:`Net <ansys.edb.net.Net>` : List of all the nets in this layout.

        Read-Only.
        """
        return [NetDotNet(self._app, i) for i in self._layout.Nets]

    @property
    def groups(self):
        """:obj:`list` of :class:`Group <ansys.edb.hierarchy.Group>` : List of all the groups in this layout.

        Read-Only.
        """
        return list(self._layout.Groups)

    @property
    def net_classes(self):
        """:obj:`list` of :class:`NetClass <ansys.edb.net.NetClass>` : List of all the netclasses in this layout.

        Read-Only.
        """
        return list(self._layout.NetClasses)

    @property
    def differential_pairs(self):
        """:obj:`list` of :class:`DifferentialPair <ansys.edb.net.DifferentialPair>` : List of all the differential \
         pairs in this layout.

        Read-Only.
        """
        return list(self._layout.DifferentialPairs)

    @property
    def pin_groups(self):
        """:obj:`list` of :class:`PinGroup <ansys.edb.hierarchy.PinGroup>` : List of all the pin groups in this \
        layout.

        Read-Only.
        """
        return list(self._layout.PinGroups)

    @property
    def voltage_regulators(self):
        """:obj:`list` of :class:`VoltageRegulator <ansys.edb.hierarchy.VoltageRegulator>` : List of all the voltage \
         regulators in this layout.

        Read-Only.
        """
        return list(self._layout.VoltageRegulators)

    @property
    def extended_nets(self):
        """Get the list of extended nets in the layout. Read-Only.

        Returns
        -------
        List[:class:`ExtendedNet <ansys.edb.net.ExtendedNet>`]
            A list of extended nets.

        """
        return list(self._layout.ExtendedNets)

    def expanded_extent(self, nets, extent, expansion_factor, expansion_unitless, use_round_corner, num_increments):
        """Get an expanded polygon for the Nets collection.

        Parameters
        ----------
        nets : list[:class:`Net <ansys.edb.net.Net>`]
            A list of nets.
        extent : :class:`ExtentType <ansys.edb.geometry.ExtentType>`
            Geometry extent type for expansion.
        expansion_factor : float
            Expansion factor for the polygon union. No expansion occurs if the `expansion_factor` is less than or \
            equal to 0.
        expansion_unitless : bool
            When unitless, the distance by which the extent expands is the factor multiplied by the longer dimension\
            (X or Y distance) of the expanded object/net.
        use_round_corner : bool
            Whether to use round or sharp corners.
            For round corners, this returns a bounding box if its area is within 10% of the rounded expansion's area.
        num_increments : int
            Number of iterations desired to reach the full expansion.

        Returns
        -------
        :class:`PolygonData <ansys.edb.geometry.PolygonData>`

        Notes
        -----
        Method returns the expansion of the contour, so any voids within expanded objects are ignored.
        """
        return self._layout.GetExpandedExtentFromNets(
            convert_py_list_to_net_list(nets),
            extent,
            expansion_factor,
            expansion_unitless,
            use_round_corner,
            num_increments,
        )

    def convert_primitives_to_vias(self, primitives, is_pins=False):
        """Convert a list of primitives into vias or pins.

        Parameters
        ----------
        primitives : list[:class:`Primitive <ansys.edb.primitive.Primitive>`]
            List of primitives to convert.
        is_pins : bool, optional
            True for pins, false for vias (default).
        """
        self._layout.ConvertPrimitivesToVias(convert_py_list_to_net_list(primitives), is_pins)

    @property
    def port_reference_terminals_connected(self):
        """:obj:`bool`: Determine if port reference terminals are connected, applies to lumped ports and circuit ports.

        True if they are connected, False otherwise.
        Read-Only.
        """
        return self._layout.ArePortReferenceTerminalsConnected()

    @property
    def zone_primitives(self):
        """:obj:`list` of :class:`Primitive <ansys.edb.primitive.Primitive>` : List of all the primitives in \
        :term:`zones <Zone>`.

        Read-Only.
        """
        return list(self._layout.GetZonePrimitives())

    @property
    def fixed_zone_primitive(self):
        """:class:`Primitive <ansys.edb.primitive.Primitive>` : Fixed :term:`zones <Zone>` primitive."""
        return list(self._layout.GetFixedZonePrimitive())

    @fixed_zone_primitive.setter
    def fixed_zone_primitive(self, value):
        self._layout.SetFixedZonePrimitives(value)

    @property
    def board_bend_defs(self):
        """:obj:`list` of :class:`BoardBendDef <ansys.edb.primitive.BoardBendDef>` : List of all the board bend \
        definitions in this layout.

        Read-Only.
        """
        return list(self._layout.GetBoardBendDefs())

    def synchronize_bend_manager(self):
        """Synchronize bend manager."""
        self._layout.SynchronizeBendManager()

    @property
    def layout_instance(self):
        """:class:`LayoutInstance <ansys.edb.layout_instance.LayoutInstance>` : Layout instance of this layout.

        Read-Only.
        """
        if not self._layout_instance:
            self._layout_instance = self._layout.GetLayoutInstance()
        return self._layout_instance
