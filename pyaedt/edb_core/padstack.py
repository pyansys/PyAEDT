"""
This module contains the `EdbPadstacks` class.
"""
import math

from pyaedt.edb_core.edb_data.padstacks_data import EDBPadstack
from pyaedt.edb_core.edb_data.padstacks_data import EDBPadstackInstance
from pyaedt.edb_core.general import convert_py_list_to_net_list
from pyaedt.generic.clr_module import Array
from pyaedt.generic.general_methods import generate_unique_name
from pyaedt.generic.general_methods import pyaedt_function_handler


class EdbPadstacks(object):
    """Manages EDB methods for nets management accessible from `Edb.core_padstack` property.

    Examples
    --------
    >>> from pyaedt import Edb
    >>> edbapp = Edb("myaedbfolder", edbversion="2021.2")
    >>> edb_padstacks = edbapp.core_padstack
    """

    def __init__(self, p_edb):
        self._pedb = p_edb

    @property
    def _builder(self):
        """ """
        return self._pedb.builder

    @property
    def _edb(self):
        """ """
        return self._pedb.edb

    def _get_edb_value(self, value):
        return self._pedb.edb_value(value)

    @property
    def _active_layout(self):
        """ """
        return self._pedb.active_layout

    @property
    def db(self):
        """Db object."""
        return self._pedb.db

    @property
    def _logger(self):
        """ """
        return self._pedb.logger

    @property
    def _layers(self):
        """ """
        return self._pedb.stackup.stackup_layers

    @pyaedt_function_handler()
    def int_to_pad_type(self, val=0):
        """Convert an integer to an EDB.PadGeometryType.

        Parameters
        ----------
        val : int

        Returns
        -------
        object
            EDB.PadType enumerator value.
        """

        if val == 0:
            return self._edb.Definition.PadType.RegularPad
        elif val == 1:
            return self._edb.Definition.PadType.AntiPad
        elif val == 2:
            return self._edb.Definition.PadType.ThermalPad
        elif val == 3:
            return self._edb.Definition.PadType.Hole
        elif val == 4:
            return self._edb.Definition.PadType.UnknownGeomType
        else:
            return val

    @pyaedt_function_handler()
    def int_to_geometry_type(self, val=0):
        """Convert an integer to an EDB.PadGeometryType.

        Parameters
        ----------
        val : int

        Returns
        -------
        object
            EDB.PadGeometryType enumerator value.
        """
        if val == 0:
            return self._edb.Definition.PadGeometryType.NoGeometry
        elif val == 1:
            return self._edb.Definition.PadGeometryType.Circle
        elif val == 2:
            return self._edb.Definition.PadGeometryType.Square
        elif val == 3:
            return self._edb.Definition.PadGeometryType.Rectangle
        elif val == 4:
            return self._edb.Definition.PadGeometryType.Oval
        elif val == 5:
            return self._edb.Definition.PadGeometryType.Bullet
        elif val == 6:
            return self._edb.Definition.PadGeometryType.NSidedPolygon
        elif val == 7:
            return self._edb.Definition.PadGeometryType.Polygon
        elif val == 8:
            return self._edb.Definition.PadGeometryType.Round45
        elif val == 9:
            return self._edb.Definition.PadGeometryType.Round90
        elif val == 10:
            return self._edb.Definition.PadGeometryType.Square45
        elif val == 11:
            return self._edb.Definition.PadGeometryType.Square90
        elif val == 12:
            return self._edb.Definition.PadGeometryType.InvalidGeometry
        else:
            return val

    @property
    def padstacks(self):
        """Padstacks via padstack definitions.

        Returns
        -------
        dict[str, :class:`pyaedt.edb_core.edb_data.EdbPadstack`]
            List of padstacks via padstack definitions.

        """
        _padstacks = {}
        for padstackdef in self.db.PadstackDefs:
            PadStackData = padstackdef.GetData()
            if len(PadStackData.GetLayerNames()) >= 1:
                _padstacks[padstackdef.GetName()] = EDBPadstack(padstackdef, self)
        return _padstacks

    @property
    def padstack_instances(self):
        """List of padstack instances.

        Returns
        -------
        dict[str, :class:`pyaedt.edb_core.edb_data.padstacks_data.EDBPadstackInstance`]
            List of padstack instances.

        """
        padstack_instances = {}
        edb_padstack_inst_list = list(self._active_layout.PadstackInstances)
        for edb_padstack_instance in edb_padstack_inst_list:
            padstack_instances[edb_padstack_instance.GetId()] = EDBPadstackInstance(edb_padstack_instance, self._pedb)
        return padstack_instances

    @property
    def pingroups(self):
        """All Layout Pin groups.

        Returns
        -------
        list
            List of all layout pin groups.
        """
        pingroups = []
        for el in self._active_layout.PinGroups:
            pingroups.append(el)
        return pingroups

    @property
    def pad_type(self):
        """Return a PadType Enumerator."""

        class PadType:
            (RegularPad, AntiPad, ThermalPad, Hole, UnknownGeomType) = (
                self._edb.Definition.PadType.RegularPad,
                self._edb.Definition.PadType.AntiPad,
                self._edb.Definition.PadType.ThermalPad,
                self._edb.Definition.PadType.Hole,
                self._edb.Definition.PadType.UnknownGeomType,
            )

        return PadType

    @pyaedt_function_handler()
    def create_circular_padstack(
        self,
        padstackname=None,
        holediam="300um",
        paddiam="400um",
        antipaddiam="600um",
        startlayer=None,
        endlayer=None,
    ):
        """Create a circular padstack.

        Parameters
        ----------
        padstackname : str, optional
            Name of the padstack. The default is ``None``.
        holediam : str, optional
            Diameter of the hole with units. The default is ``"300um"``.
        paddiam : str, optional
            Diameter of the pad with units. The default is ``"400um"``.
        antipaddiam : str, optional
            Diameter of the antipad with units. The default is ``"600um"``.
        startlayer : str, optional
            Starting layer. The default is ``None``, in which case the top
            is the starting layer.
        endlayer : str, optional
            Ending layer. The default is ``None``, in which case the bottom
            is the ending layer.

        Returns
        -------
        str
            Name of the padstack if the operation is successful.
        """

        PadStack = self._edb.Definition.PadstackDef.Create(self._active_layout.GetCell().GetDatabase(), padstackname)
        new_PadStackData = self._edb.Definition.PadstackDefData.Create()
        list_values = convert_py_list_to_net_list(
            [self._get_edb_value(holediam), self._get_edb_value(paddiam), self._get_edb_value(antipaddiam)]
        )
        value0 = self._get_edb_value(0.0)
        new_PadStackData.SetHoleParameters(
            self._edb.Definition.PadGeometryType.Circle,
            list_values,
            value0,
            value0,
            value0,
        )
        new_PadStackData.SetHoleRange(self._edb.Definition.PadstackHoleRange.UpperPadToLowerPad)
        layers = list(self._pedb.stackup.signal_layers.keys())
        if not startlayer:
            startlayer = layers[0]
        if not endlayer:
            endlayer = layers[len(layers) - 1]

        antipad_shape = self._edb.Definition.PadGeometryType.Circle
        started = False
        new_PadStackData.SetPadParameters(
            "Default",
            self._edb.Definition.PadType.RegularPad,
            self._edb.Definition.PadGeometryType.Circle,
            convert_py_list_to_net_list([self._get_edb_value(paddiam)]),
            value0,
            value0,
            value0,
        )

        new_PadStackData.SetPadParameters(
            "Default",
            self._edb.Definition.PadType.AntiPad,
            antipad_shape,
            convert_py_list_to_net_list([self._get_edb_value(antipaddiam)]),
            value0,
            value0,
            value0,
        )
        for layer in layers:
            if layer == startlayer:
                started = True
            if layer == endlayer:
                started = False
            if started:
                new_PadStackData.SetPadParameters(
                    layer,
                    self._edb.Definition.PadType.RegularPad,
                    self._edb.Definition.PadGeometryType.Circle,
                    convert_py_list_to_net_list([self._get_edb_value(paddiam)]),
                    value0,
                    value0,
                    value0,
                )
                new_PadStackData.SetPadParameters(
                    layer,
                    self._edb.Definition.PadType.AntiPad,
                    antipad_shape,
                    convert_py_list_to_net_list([self._get_edb_value(antipaddiam)]),
                    value0,
                    value0,
                    value0,
                )
        PadStack.SetData(new_PadStackData)

    @pyaedt_function_handler
    def delete_padstack_instances(self, net_names):  # pragma: no cover
        """Delete padstack instances by net names.

        Parameters
        ----------
        net_names : str, list
            Names of the nets to delete.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> Edb.core_padstack.delete_padstack_instances(net_names=["GND"])
        """
        if not isinstance(net_names, list):  # pragma: no cover
            net_names = [net_names]

        for p_id, p in self.padstack_instances.items():
            if p.name in net_names:
                if not p.delete():  # pragma: no cover
                    return False
        return True

    @pyaedt_function_handler()
    def set_solderball(self, padstackInst, sballLayer_name, isTopPlaced=True, ballDiam=100e-6):
        """Set solderball for the given PadstackInstance.

        Parameters
        ----------
        padstackInst : Edb.Cell.Primitive.PadstackInstance or int
            Padstack instance id or object.
        sballLayer_name : str,
            Name of the layer where the solder ball is placed. No default values.
        isTopPlaced : bool, optional.
            Bollean triggering is the solder ball is placed on Top or Bottom of the layer stackup.
        ballDiam : double, optional,
            Solder ball diameter value.

        Returns
        -------
        bool

        """
        if isinstance(padstackInst, int):
            psdef = self.padstacks[self.padstack_instances[padstackInst].padstack_definition].edb_padstack
            padstackInst = self.padstack_instances[padstackInst]._edb_padstackinstance

        else:
            psdef = padstackInst.GetPadstackDef()
        newdefdata = self._edb.Definition.PadstackDefData(psdef.GetData())
        newdefdata.SetSolderBallShape(self._edb.Definition.SolderballShape.Cylinder)
        newdefdata.SetSolderBallParameter(self._get_edb_value(ballDiam), self._get_edb_value(ballDiam))
        sball_placement = (
            self._edb.Definition.SolderballPlacement.AbovePadstack
            if isTopPlaced
            else self._edb.Definition.SolderballPlacement.BelowPadstack
        )
        newdefdata.SetSolderBallPlacement(sball_placement)
        psdef.SetData(newdefdata)
        sball_layer = [lay._edb_layer for lay in list(self._layers.values()) if lay.name == sballLayer_name][0]
        if sball_layer is not None:
            padstackInst.SetSolderBallLayer(sball_layer)
            return True

        return False

    @pyaedt_function_handler()
    def create_coax_port(self, padstackinstance, use_dot_separator=True):
        """Create HFSS 3Dlayout coaxial lumped port on a pastack
        Requires to have solder ball defined before calling this method.

        Parameters
        ----------
        padstackinstance : `Edb.Cell.Primitive.PadstackInstance` or int
            Padstack instance object.

        Returns
        -------
        str
            Terminal name.

        """
        if isinstance(padstackinstance, int):
            padstackinstance = self.padstack_instances[padstackinstance]._edb_padstackinstance
        elif isinstance(padstackinstance, EDBPadstackInstance):
            padstackinstance = padstackinstance._edb_padstackinstance
        cmp_name = padstackinstance.GetComponent().GetName()
        if cmp_name == "":
            cmp_name = "no_comp"

        net_name = padstackinstance.GetNet().GetName()
        if net_name == "":
            net_name = "no_net"

        pin_name = padstackinstance.GetName()
        if pin_name == "":
            pin_name = "no_pin_name"
        if use_dot_separator:
            port_name = "{0}.{1}.{2}".format(net_name, cmp_name, pin_name)
        else:
            port_name = "{0}_{1}_{2}".format(net_name, cmp_name, pin_name)
        if not padstackinstance.IsLayoutPin():
            padstackinstance.SetIsLayoutPin(True)

        res = padstackinstance.GetLayerRange()
        self._edb.Cell.Terminal.PadstackInstanceTerminal.Create(
            self._active_layout,
            padstackinstance.GetNet(),
            port_name,
            padstackinstance,
            res[2],
        )
        if res[0]:
            return port_name
        return ""

    @pyaedt_function_handler()
    def get_pinlist_from_component_and_net(self, refdes=None, netname=None):
        """Retrieve pins given a component's reference designator and net name.

        Parameters
        ----------
        refdes : str, optional
            Reference designator of the component. The default is ``None``.
        netname : str optional
            Name of the net. The default is ``None``.

        Returns
        -------
        dict
            Dictionary of pins if the operation is successful.
            ``False`` is returned if the net does not belong to the component.

        """
        pinlist = []
        if refdes:
            if refdes in self._pedb.core_components.components:
                if netname:
                    for pin, val in self._pedb.core_components.components[refdes].pins.items():
                        if val.net_name == netname:
                            pinlist.append(val)
                else:
                    for pin in self._pedb.core_components.components[refdes].pins.values():
                        pinlist.append(pin)
            elif netname:
                for pin in self._pedb.pins:
                    if pin.net_name == netname:
                        pinlist.append(pin)
            else:
                self._logger.error("At least a component or a net name has to be provided")

        return pinlist

    @pyaedt_function_handler()
    def get_pad_parameters(self, pin, layername, pad_type=0):
        """Get Padstack Parameters from Pin or Padstack Definition.

        Parameters
        ----------
        pin : Edb.Definition.PadstackDef or Edb.Definition.PadstackInstance
            Pin or PadstackDef on which get values.
        layername : str
            Layer on which get properties.
        pad_type : int
            Pad Type.

        Returns
        -------
        tuple
            Tuple of (GeometryType, ParameterList, OffsetX, OffsetY, Rot).
        """

        if "PadstackDef" in str(type(pin)):
            padparams = pin.GetData().GetPadParametersValue(layername, self.int_to_pad_type(pad_type))
        else:
            padparams = self._edb.Definition.PadstackDefData(pin.GetPadstackDef().GetData()).GetPadParametersValue(
                layername, self.int_to_pad_type(pad_type)
            )
        geom_type = int(padparams[1])
        parameters = [i.ToString() for i in padparams[2]]
        offset_x = padparams[3].ToDouble()
        offset_y = padparams[4].ToDouble()
        rot = padparams[5].ToDouble()
        return geom_type, parameters, offset_x, offset_y, rot

    @pyaedt_function_handler
    def set_all_antipad_value(self, value):
        """Set all anti-pads from all pad-stack definition to the given value.

        Parameters
        ----------
        value : float, str
            Anti-pad value.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` if an anti-pad value fails to be assigned.
        """
        if self.padstacks:
            for padstack in list(self.padstacks.values()):
                cloned_padstack_data = self._edb.Definition.PadstackDefData(padstack.edb_padstack.GetData())
                layers_name = cloned_padstack_data.GetLayerNames()
                all_succeed = True
                for layer in layers_name:
                    geom_type, parameters, offset_x, offset_y, rot = self.get_pad_parameters(
                        padstack.edb_padstack, layer, 1
                    )
                    if geom_type == 1:  # pragma no cover
                        params = convert_py_list_to_net_list(
                            [self._pedb.edb_value(value)] * len(parameters)
                        )  # pragma no cover
                        geom = self._edb.Definition.PadGeometryType.Circle
                        offset_x = self._pedb.edb_value(offset_x)
                        offset_y = self._pedb.edb_value(offset_y)
                        rot = self._pedb.edb_value(rot)
                        antipad = self._edb.Definition.PadType.AntiPad
                        if cloned_padstack_data.SetPadParameters(
                            layer, antipad, geom, params, offset_x, offset_y, rot
                        ):  # pragma no cover
                            self._logger.info(
                                "Pad-stack definition {}, anti-pad on layer {}, has been set to {}".format(
                                    padstack.edb_padstack.GetName(), layer, str(value)
                                )
                            )
                        else:  # pragma no cover
                            self._logger.error(
                                "Failed to reassign anti-pad value {} on Pads-stack definition {},"
                                " layer{}".format(str(value), padstack.edb_padstack.GetName(), layer)
                            )
                            all_succeed = False
                padstack.edb_padstack.SetData(cloned_padstack_data)
            return all_succeed

    @pyaedt_function_handler
    def check_and_fix_via_plating(self, minimum_value_to_replace=0.0, default_plating_ratio=0.2):
        """Check for minimum via plating ration value, values found below the minimum one are replaced by default
        plating ratio.

        Parameters
        ----------
        minimum_value_to_replace : float
            Plating ratio that is below or equal to this value is to be replaced
            with the value specified for the next parameter. Default value ``0.0``.
        default_plating_ratio : float
            Default value to use for plating ratio. The default value is ``0.2``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` if an anti-pad value fails to be assigned.
        """
        for padstack_def in list(self.padstacks.values()):
            if padstack_def.hole_plating_ratio <= minimum_value_to_replace:
                padstack_def.hole_plating_ratio = default_plating_ratio
                self._logger.info(
                    "Padstack definition with zero plating ratio, defaulting to 20%".format(padstack_def.name)
                )
        return True

    @pyaedt_function_handler()
    def get_via_instance_from_net(self, net_list=None):
        """Get the list for EDB vias from a net name list.

        Parameters
        ----------
        net_list : str or list
            The list of the net name to be used for filtering vias. If no net is provided the command will
            return an all vias list.

        Returns
        -------
        list of Edb.Cell.Primitive.PadstackInstance
            List of EDB vias.
        """
        if net_list == None:
            net_list = []

        if not isinstance(net_list, list):
            net_list = [net_list]
        layout_lobj_collection = list(self._active_layout.PadstackInstances)
        via_list = []
        for lobj in layout_lobj_collection:
            pad_layers_name = lobj.GetPadstackDef().GetData().GetLayerNames()
            if len(pad_layers_name) > 1:
                if not net_list:
                    via_list.append(lobj)
                elif lobj.GetNet().GetName() in net_list:
                    via_list.append(lobj)
        return via_list

    @pyaedt_function_handler()
    def create_padstack(
        self,
        padstackname=None,
        holediam="300um",
        paddiam="400um",
        antipaddiam="600um",
        startlayer=None,
        endlayer=None,
        antipad_shape="Circle",
        x_size="600um",
        y_size="600um",
        corner_radius="300um",
        offset_x="0.0",
        offset_y="0.0",
        rotation="0.0",
        has_hole=True,
        pad_offset_x="0.0",
        pad_offset_y="0.0",
        pad_rotation="0.0",
    ):
        """Create a padstack.

        Parameters
        ----------
        padstackname : str, optional
            Name of the padstack. The default is ``None``.
        holediam : str, optional
            Diameter of the hole with units. The default is ``"300um"``.
        paddiam : str, optional
            Diameter of the pad with units. The default is ``"400um"``.
        antipaddiam : str, optional
            Diameter of the antipad with units. The default is ``"600um"``.
        startlayer : str, optional
            Starting layer. The default is ``None``, in which case the top
            is the starting layer.
        endlayer : str, optional
            Ending layer. The default is ``None``, in which case the bottom
            is the ending layer.
        antipad_shape : str, optional
            Shape of the antipad. The default is ``"Circle"``. Options are ``"Circle"`` and ``"Bullet"``.
        x_size : str, optional
            Only applicable to bullet shape. The default is ``"600um"``.
        y_size : str, optional
            Only applicable to bullet shape. The default is ``"600um"``.
        corner_radius :
            Only applicable to bullet shape. The default is ``"300um"``.
        offset_x : str, optional
            X offset of antipad. The default is ``"0.0"``.
        offset_y : str, optional
            Y offset of antipad. The default is ``"0.0"``.
        rotation : str, optional
            rotation of antipad. The default is ``"0.0"``.
        has_hole : bool, optional
            Whether this padstack has a hole.
        Returns
        -------
        str
            Name of the padstack if the operation is successful.
        """
        holediam = self._get_edb_value(holediam)
        paddiam = self._get_edb_value(paddiam)
        antipaddiam = self._get_edb_value(antipaddiam)

        if not padstackname:
            padstackname = generate_unique_name("VIA")
        # assert not self.isreadonly, "Write Functions are not available within AEDT"
        padstackData = self._edb.Definition.PadstackDefData.Create()
        if has_hole:
            ptype = self._edb.Definition.PadGeometryType.Circle
        else:
            ptype = self._edb.Definition.PadGeometryType.NoGeometry
        holparam = Array[type(holediam)]([holediam])
        value0 = self._get_edb_value("0.0")
        x_size = self._get_edb_value(x_size)
        y_size = self._get_edb_value(y_size)
        corner_radius = self._get_edb_value(corner_radius)
        offset_x = self._get_edb_value(offset_x)
        offset_y = self._get_edb_value(offset_y)
        rotation = self._get_edb_value(rotation)

        pad_offset_x = self._get_edb_value(pad_offset_x)
        pad_offset_y = self._get_edb_value(pad_offset_y)
        pad_rotation = self._get_edb_value(pad_rotation)

        padstackData.SetHoleParameters(ptype, holparam, value0, value0, value0)

        padstackData.SetHolePlatingPercentage(self._get_edb_value(20.0))
        padstackData.SetHoleRange(self._edb.Definition.PadstackHoleRange.UpperPadToLowerPad)
        padstackData.SetMaterial("copper")
        layers = list(self._pedb.stackup.signal_layers.keys())
        if not startlayer:
            startlayer = layers[0]
        if not endlayer:
            endlayer = layers[len(layers) - 1]

        if antipad_shape == "Bullet":
            antipad_array = Array[type(x_size)]([x_size, y_size, corner_radius])
            antipad_shape = self._edb.Definition.PadGeometryType.Bullet
        else:
            antipad_array = Array[type(antipaddiam)]([antipaddiam])
            antipad_shape = self._edb.Definition.PadGeometryType.Circle

        for layer in ["Default"] + layers:
            padparam_array = Array[type(paddiam)]([paddiam])
            padstackData.SetPadParameters(
                layer,
                self._edb.Definition.PadType.RegularPad,
                self._edb.Definition.PadGeometryType.Circle,
                padparam_array,
                pad_offset_x,
                pad_offset_y,
                pad_rotation,
            )

            padstackData.SetPadParameters(
                layer,
                self._edb.Definition.PadType.AntiPad,
                antipad_shape,
                antipad_array,
                offset_x,
                offset_y,
                rotation,
            )

        padstackLayerIdMap = {k: v for k, v in zip(padstackData.GetLayerNames(), padstackData.GetLayerIds())}
        padstackLayerMap = self._edb.Utility.LayerMap(self._edb.Utility.UniqueDirection.ForwardUnique)
        for layer, padstackLayerName in zip(
            self._active_layout.GetLayerCollection().Layers(self._edb.Cell.LayerTypeSet.SignalLayerSet),
            [startlayer, "Default", endlayer],
        ):
            padstackLayerMap.SetMapping(layer.GetLayerId(), padstackLayerIdMap[padstackLayerName])
        padstackDefinition = self._edb.Definition.PadstackDef.Create(self.db, padstackname)
        padstackDefinition.SetData(padstackData)
        self._logger.info("Padstack %s create correctly", padstackname)
        return padstackname

    @pyaedt_function_handler()
    def _get_pin_layer_range(self, pin):

        res, fromlayer, tolayer = pin.GetLayerRange()
        if res:
            return fromlayer, tolayer
        else:
            return False

    @pyaedt_function_handler()
    def duplicate_padstack(self, target_padstack_name, new_padstack_name=""):
        """Duplicate a padstack.

        Parameters
        ----------
        target_padstack_name : str
            Name of the padstack to be duplicated.
        new_padstack_name : str, optional
            Name of the new padstack.
        Returns
        -------
        str
            Name of the new padstack.
        """
        p1 = self.padstacks[target_padstack_name].edb_padstack.GetData()
        new_padstack_definition_data = self._edb.Definition.PadstackDefData(p1)

        if not new_padstack_name:
            new_padstack_name = generate_unique_name(target_padstack_name)

        padstack_definition = self._edb.Definition.PadstackDef.Create(self.db, new_padstack_name)
        padstack_definition.SetData(new_padstack_definition_data)

        return new_padstack_name

    @pyaedt_function_handler()
    def place_padstack(
        self,
        position,
        definition_name,
        net_name="",
        via_name="",
        rotation=0.0,
        fromlayer=None,
        tolayer=None,
        solderlayer=None,
        is_pin=False,
    ):
        """Place the padstack.

        Parameters
        ----------
        position : list
            List of float values for the [x,y] positions where the via is to be placed.
        definition_name : str
            Name of the padstack definition.
        net_name : str, optional
            Name of the net. The default is ``""``.
        via_name : str, optional
            The default is ``""``.
        rotation : float, optional
            Rotation of the padstack in degrees. The default
            is ``0``.
        fromlayer :
            The default is ``None``.
        tolayer :
            The default is ``None``.
        solderlayer :
            The default is ``None``.

        Returns
        -------

        """
        padstack = None
        for pad in list(self.padstacks.keys()):
            if pad == definition_name:
                padstack = self.padstacks[pad].edb_padstack
        position = self._edb.Geometry.PointData(self._get_edb_value(position[0]), self._get_edb_value(position[1]))
        net = self._pedb.core_nets.find_or_create_net(net_name)
        rotation = self._get_edb_value(rotation * math.pi / 180)
        sign_layers = list(self._pedb.stackup.signal_layers.keys())
        if not fromlayer:
            fromlayer = self._pedb.stackup.signal_layers[sign_layers[0]]._edb_layer
        else:
            fromlayer = self._pedb.stackup.signal_layers[fromlayer]._edb_layer

        if not tolayer:
            tolayer = self._pedb.stackup.signal_layers[sign_layers[-1]]._edb_layer
        else:
            tolayer = self._pedb.stackup.signal_layers[tolayer]._edb_layer
        if solderlayer:
            solderlayer = self._pedb.stackup.signal_layers[solderlayer]._edb_layer
        if padstack:
            padstack_instance = self._edb.Cell.Primitive.PadstackInstance.Create(
                self._active_layout,
                net,
                via_name,
                padstack,
                position,
                rotation,
                fromlayer,
                tolayer,
                solderlayer,
                None,
            )
            padstack_instance.SetIsLayoutPin(is_pin)
            py_padstack_instance = EDBPadstackInstance(padstack_instance, self._pedb)

            return py_padstack_instance
        else:
            return False

    @pyaedt_function_handler()
    def remove_pads_from_padstack(self, padstack_name, layer_name=None):
        """Remove the Pad from a padstack on a specific layer by setting it as a 0 thickness circle.

        Parameters
        ----------
        padstack_name : str
            padstack name
        layer_name : str, optional
            Layer name on which remove the PadParameters. If None, all layers will be taken.

        Returns
        -------
        bool
            ``True`` if successful.
        """
        pad_type = self._edb.Definition.PadType.RegularPad
        pad_geo = self._edb.Definition.PadGeometryType.Circle
        vals = self._get_edb_value(0)
        params = convert_py_list_to_net_list([self._get_edb_value(0)])
        p1 = self.padstacks[padstack_name].edb_padstack.GetData()
        newPadstackDefinitionData = self._edb.Definition.PadstackDefData(p1)

        if not layer_name:
            layer_name = list(self._pedb.stackup.signal_layers.keys())
        elif isinstance(layer_name, str):
            layer_name = [layer_name]
        for lay in layer_name:
            newPadstackDefinitionData.SetPadParameters(lay, pad_type, pad_geo, params, vals, vals, vals)

        self.padstacks[padstack_name].edb_padstack.SetData(newPadstackDefinitionData)
        return True

    @pyaedt_function_handler()
    def set_pad_property(
        self,
        padstack_name,
        layer_name=None,
        pad_shape="Circle",
        pad_params=0,
        pad_x_offset=0,
        pad_y_offset=0,
        pad_rotation=0,
        antipad_shape="Circle",
        antipad_params=0,
        antipad_x_offset=0,
        antipad_y_offset=0,
        antipad_rotation=0,
    ):
        """Set pad and antipad properties of the padstack.

        Parameters
        ----------
        padstack_name : str
            Name of the padstack.
        layer_name : str, optional
            Name of the layer. If None, all layers will be taken.
        pad_shape : str, optional
            Shape of the pad. The default is ``"Circle"``. Options are ``"Circle"``,  ``"Square"``, ``"Rectangle"``,
            ``"Oval"`` and ``"Bullet"``.
        pad_params : str, optional
            Dimension of the pad. The default is ``"0"``.
        pad_x_offset : str, optional
            X offset of the pad. The default is ``"0"``.
        pad_y_offset : str, optional
            Y offset of the pad. The default is ``"0"``.
        pad_rotation : str, optional
            Rotation of the pad. The default is ``"0"``.
        antipad_shape : str, optional
            Shape of the antipad. The default is ``"0"``.
        antipad_params : str, optional
            Dimension of the antipad. The default is ``"0"``.
        antipad_x_offset : str, optional
            X offset of the antipad. The default is ``"0"``.
        antipad_y_offset : str, optional
            Y offset of the antipad. The default is ``"0"``.
        antipad_rotation : str, optional
            Rotation of the antipad. The default is ``"0"``.

        Returns
        -------
        bool
            ``True`` if successful.
        """
        shape_dict = {
            "Circle": self._edb.Definition.PadGeometryType.Circle,
            "Square": self._edb.Definition.PadGeometryType.Square,
            "Rectangle": self._edb.Definition.PadGeometryType.Rectangle,
            "Oval": self._edb.Definition.PadGeometryType.Oval,
            "Bullet": self._edb.Definition.PadGeometryType.Bullet,
        }
        pad_shape = shape_dict[pad_shape]
        if not isinstance(pad_params, list):
            pad_params = [pad_params]
        pad_params = convert_py_list_to_net_list([self._get_edb_value(i) for i in pad_params])
        pad_x_offset = self._get_edb_value(pad_x_offset)
        pad_y_offset = self._get_edb_value(pad_y_offset)
        pad_rotation = self._get_edb_value(pad_rotation)

        antipad_shape = shape_dict[antipad_shape]
        if not isinstance(antipad_params, list):
            antipad_params = [antipad_params]
        antipad_params = convert_py_list_to_net_list([self._get_edb_value(i) for i in antipad_params])
        antipad_x_offset = self._get_edb_value(antipad_x_offset)
        antipad_y_offset = self._get_edb_value(antipad_y_offset)
        antipad_rotation = self._get_edb_value(antipad_rotation)

        p1 = self.padstacks[padstack_name].edb_padstack.GetData()
        new_padstack_def = self._edb.Definition.PadstackDefData(p1)
        if not layer_name:
            layer_name = list(self._pedb.stackup.signal_layers.keys())
        elif isinstance(layer_name, str):
            layer_name = [layer_name]
        for layer in layer_name:
            new_padstack_def.SetPadParameters(
                layer,
                self._edb.Definition.PadType.RegularPad,
                pad_shape,
                pad_params,
                pad_x_offset,
                pad_y_offset,
                pad_rotation,
            )
            new_padstack_def.SetPadParameters(
                layer,
                self._edb.Definition.PadType.AntiPad,
                antipad_shape,
                antipad_params,
                antipad_x_offset,
                antipad_y_offset,
                antipad_rotation,
            )
        self.padstacks[padstack_name].edb_padstack.SetData(new_padstack_def)
        return True

    @pyaedt_function_handler()
    def get_padstack_instance_by_net_name(self, net_name):
        """Get a list of padstack instances by net name.

        Parameters
        ----------
        net_name : str
            The net name to be used for filtering padstack instances.
        Returns
        -------
        list of Edb.Cell.Primitive.PadstackInstance
        """
        padstack_instances = {}
        for inst_id, inst in self.padstack_instances.items():
            if inst.net_name == net_name:
                padstack_instances[inst_id] = inst
        return padstack_instances
