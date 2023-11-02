from pyaedt.edb_core.dotnet.database import DifferentialPairDotNet, ExtendedNetDotNet, NetClassDotNet, NetDotNet
from pyaedt.edb_core.edb_data.padstacks_data import EDBPadstackInstance
from pyaedt.edb_core.edb_data.primitives_data import cast
from pyaedt.generic.general_methods import pyaedt_function_handler


class EDBNetsData(NetDotNet):
    """Manages EDB functionalities for a primitives.
    It Inherits EDB Object properties.

    Examples
    --------
    >>> from pyaedt import Edb
    >>> edb = Edb(myedb, edbversion="2021.2")
    >>> edb_net = edb.nets.nets["GND"]
    >>> edb_net.name # Class Property
    >>> edb_net.name # EDB Object Property
    """

    def __getattr__(self, key):
        try:
            return self[key]
        except:
            try:
                return getattr(self.net_object, key)
            except AttributeError:
                raise AttributeError("Attribute not present")

    def __init__(self, raw_net, core_app):
        self._app = core_app
        self._core_components = core_app.components
        self._core_primitive = core_app.modeler
        self.net_object = raw_net
        NetDotNet.__init__(self, self._app, raw_net)

    @property
    def primitives(self):
        """Return the list of primitives that belongs to the net.

        Returns
        -------
        list of :class:`pyaedt.edb_core.edb_data.primitives_data.EDBPrimitives`
        """
        return [cast(i, self._app) for i in self.net_object.Primitives]

    @property
    def padstack_instances(self):
        """Return the list of primitives that belongs to the net.

        Returns
        -------
        list of :class:`pyaedt.edb_core.edb_data.padstacks_data.EDBPadstackInstance`
        """
        name = self.name
        return [
            EDBPadstackInstance(i, self._app) for i in self.net_object.PadstackInstances if i.GetNet().GetName() == name
        ]

    @property
    def components(self):
        """Return the list of components that touch the net.

        Returns
        -------
        dict[str, :class:`pyaedt.edb_core.edb_data.components_data.EDBComponent`]
        """
        comps = {}
        for p in self.padstack_instances:
            comp = p.component
            if comp:
                if comp.refdes not in comps:
                    comps[comp.refdes] = comp
        return comps

    @pyaedt_function_handler
    def find_dc_short(self, fix=False):
        """Find DC-shorted nets.

        Parameters
        ----------
        fix : bool, optional
            If `True`, rename all the nets. (default)
            If `False`, only report dc shorts.

        Returns
        -------
        List[List[str, str]]
            [[net name, net name]].
        """
        return self._app.layout_validation.dc_shorts(self.name, fix)

    @pyaedt_function_handler()
    def plot(
        self,
        layers=None,
        show_legend=True,
        save_plot=None,
        outline=None,
        size=(2000, 1000),
    ):
        """Plot a net to Matplotlib 2D chart.

        Parameters
        ----------
        layers : str, list, optional
            Name of the layers to include in the plot. If `None` all the signal layers will be considered.
        show_legend : bool, optional
            If `True` the legend is shown in the plot. (default)
            If `False` the legend is not shown.
        save_plot : str, optional
            If `None` the plot will be shown.
            If a file path is specified the plot will be saved to such file.
        outline : list, optional
            List of points of the outline to plot.
        size : tuple, optional
            Image size in pixel (width, height).
        """
        self._app.nets.plot(
            self.name,
            layers=layers,
            show_legend=show_legend,
            save_plot=save_plot,
            outline=outline,
            size=size,
        )

    @pyaedt_function_handler()
    def get_smallest_trace_width(self):
        """Retrieve the smallest trace width from paths.

        Returns
        -------
        float
            Trace smallest width.
        """
        current_value = 1e10
        for prim in self.net_object.Primitives:
            if "GetWidth" in dir(prim):
                width = prim.GetWidth()
                if width < current_value:
                    current_value = width
        return current_value

    @property
    def extended_net(self):
        """Get extended net and associated components.

        Returns
        -------
        :class:` :class:`pyaedt.edb_core.edb_data.nets_data.EDBExtendedNetData`

        Examples
        --------
        >>> from pyaedt import Edb
        >>> app = Edb()
        >>> app.nets["BST_V3P3_S5"].extended_net
        """
        api_extended_net = self._api_get_extended_net
        obj = EDBExtendedNetData(self._app, api_extended_net)

        if not obj.is_null:
            return obj
        else:  # pragma: no cover
            return


class EDBNetClassData(NetClassDotNet):
    """Manages EDB functionalities for a primitives.
    It inherits EDB Object properties.

    Examples
    --------
    >>> from pyaedt import Edb
    >>> edb = Edb(myedb, edbversion="2021.2")
    >>> edb.net_classes
    """

    def __init__(self, core_app, raw_extended_net=None):
        super().__init__(core_app, raw_extended_net)
        self._app = core_app
        self._core_components = core_app.components
        self._core_primitive = core_app.modeler
        self._core_nets = core_app.nets

    @property
    def nets(self):
        """Get nets belong to this net class."""
        return {name: self._core_nets[name] for name in self.api_nets}


class EDBExtendedNetData(ExtendedNetDotNet):
    """Manages EDB functionalities for a primitives.
    It Inherits EDB Object properties.

    Examples
    --------
    >>> from pyaedt import Edb
    >>> edb = Edb(myedb, edbversion="2021.2")
    >>> edb_extended_net = edb.nets.extended_nets["GND"]
    >>> edb_extended_net.name # Class Property
    """

    def __init__(self, core_app, raw_extended_net=None):
        self._app = core_app
        self._core_components = core_app.components
        self._core_primitive = core_app.modeler
        self._core_nets = core_app.nets
        ExtendedNetDotNet.__init__(self, self._app, raw_extended_net)

    @property
    def nets(self):
        """Nets dictionary."""
        return {name: self._core_nets[name] for name in self.api_nets}

    @property
    def components(self):
        """Dictionary of components."""
        comps = {}
        for _, obj in self.nets.items():
            comps.update(obj.components)
        return comps

    @property
    def rlc(self):
        """Dictionary of rlc components."""
        return {
            name: comp for name, comp in self.components.items() if comp.type in ["Inductor", "Resistor", "Capacitor"]
        }

    @property
    def serial_rlc(self):
        """Dictionary of series components."""
        comps_common = {}
        nets = self.nets
        for net in nets:
            comps_common.update(
                {
                    i: v
                    for i, v in self._app._nets[net].components.items()
                    if list(set(v.nets).intersection(nets)) != [net]
                }
            )
        return comps_common


class EDBDifferentialPairData(DifferentialPairDotNet):
    """Manages EDB functionalities for a primitive.
    It inherits EDB object properties.

    Examples
    --------
    >>> from pyaedt import Edb
    >>> edb = Edb(myedb, edbversion="2021.2")
    >>> diff_pair = edb.differential_pairs["DQ4"]
    >>> diff_pair.positive_net
    >>> diff_pair.negative_net
    """

    def __init__(self, core_app, api_object=None):
        self._app = core_app
        self._core_components = core_app.components
        self._core_primitive = core_app.modeler
        self._core_nets = core_app.nets
        DifferentialPairDotNet.__init__(self, self._app, api_object)

    @property
    def positive_net(self):
        # type: ()->EDBNetsData
        """Positive Net."""
        return EDBNetsData(self.api_positive_net, self._app)

    @property
    def negative_net(self):
        # type: ()->EDBNetsData
        """Negative Net."""
        return EDBNetsData(self.api_negative_net, self._app)
