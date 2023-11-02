import logging
import re
import warnings

from pyaedt.edb_core.edb_data.padstacks_data import EDBPadstackInstance
from pyaedt.generic.general_methods import is_ironpython

if not is_ironpython:
    try:
        import numpy as np
    except ImportError:
        warnings.warn(
            "The NumPy module is required to run some functionalities of EDB.\n"
            "Install with \n\npip install numpy\n\nRequires CPython."
        )
from pyaedt.generic.general_methods import get_filename_without_extension, pyaedt_function_handler


class EDBComponentDef(object):
    """Manages EDB functionalities for component definitions.

    Parameters
    ----------
    parent : :class:`pyaedt.edb_core.components.Components`
        Inherited AEDT object.
    comp_def : object
        Edb ComponentDef Object
    """

    def __init__(self, pedb, comp_def):
        self._pedb = pedb
        self._edb_comp_def = comp_def

    @property
    def _comp_model(self):
        return list(self._edb_comp_def.GetComponentModels())  # pragma: no cover

    @property
    def part_name(self):
        """Retrieve component definition name."""
        return self._edb_comp_def.GetName()

    @part_name.setter
    def part_name(self, name):
        self._edb_comp_def.SetName(name)

    @property
    def type(self):
        """Retrieve the component definition type.

        Returns
        -------
        str
        """
        num = len(set(comp.type for refdes, comp in self.components.items()))
        if num == 0:  # pragma: no cover
            return None
        elif num == 1:
            return list(self.components.values())[0].type
        else:
            return "mixed"  # pragma: no cover

    @type.setter
    def type(self, value):
        for comp in list(self.components.values()):
            comp.type = value

    @property
    def components(self):
        """Get the list of components belonging to this component definition.

        Returns
        -------
        dict of :class:`pyaedt.edb_core.edb_data.components_data.EDBComponent`
        """
        comp_list = [
            EDBComponent(self._pedb, l)
            for l in self._pedb.edb_api.cell.hierarchy.component.FindByComponentDef(
                self._pedb.active_layout, self.part_name
            )
        ]
        return {comp.refdes: comp for comp in comp_list}

    @pyaedt_function_handler
    def assign_rlc_model(self, res=None, ind=None, cap=None, is_parallel=False):
        """Assign RLC to all components under this part name.

        Parameters
        ----------
        res : int, float
            Resistance. Default is ``None``.
        ind : int, float
            Inductance. Default is ``None``.
        cap : int, float
            Capacitance. Default is ``None``.
        is_parallel : bool, optional
            Whether it is parallel or series RLC component.
        """
        for comp in list(self.components.values()):
            res, ind, cap = res, ind, cap
            comp.assign_rlc_model(res, ind, cap, is_parallel)
        return True

    @pyaedt_function_handler
    def assign_s_param_model(self, file_path, model_name=None, reference_net=None):
        """Assign S-parameter to all components under this part name.

        Parameters
        ----------
        file_path : str
            File path of the S-parameter model.
        name : str, optional
            Name of the S-parameter model.

        Returns
        -------

        """
        for comp in list(self.components.values()):
            comp.assign_s_param_model(file_path, model_name, reference_net)
        return True

    @pyaedt_function_handler
    def assign_spice_model(self, file_path, model_name=None):
        """Assign Spice model to all components under this part name.

        Parameters
        ----------
        file_path : str
            File path of the Spice model.
        name : str, optional
            Name of the Spice model.

        Returns
        -------

        """
        for comp in list(self.components.values()):
            comp.assign_spice_model(file_path, model_name)
        return True


class EDBComponent(object):
    """Manages EDB functionalities for components.

    Parameters
    ----------
    parent : :class:`pyaedt.edb_core.components.Components`
        Inherited AEDT object.
    component : object
        Edb Component Object

    """

    class _PinPair(object):  # pragma: no cover
        def __init__(self, pcomp, edb_comp, edb_comp_prop, edb_model, edb_pin_pair):
            self._pedb_comp = pcomp
            self._edb_comp = edb_comp
            self._edb_comp_prop = edb_comp_prop
            self._edb_model = edb_model
            self._edb_pin_pair = edb_pin_pair

        def _edb_value(self, value):
            return self._pedb_comp._get_edb_value(value)  # pragma: no cover

        @property
        def is_parallel(self):
            return self._pin_pair_rlc.IsParallel  # pragma: no cover

        @is_parallel.setter
        def is_parallel(self, value):
            rlc = self._pin_pair_rlc
            rlc.IsParallel = value
            self._set_comp_prop()  # pragma: no cover

        @property
        def _pin_pair_rlc(self):
            return self._edb_model.GetPinPairRlc(self._edb_pin_pair)

        @property
        def rlc_enable(self):
            rlc = self._pin_pair_rlc
            return [rlc.REnabled, rlc.LEnabled, rlc.CEnabled]

        @rlc_enable.setter
        def rlc_enable(self, value):
            rlc = self._pin_pair_rlc
            rlc.REnabled = value[0]
            rlc.LEnabled = value[1]
            rlc.CEnabled = value[2]
            self._set_comp_prop()  # pragma: no cover

        @property
        def resistance(self):
            return self._pin_pair_rlc.R.ToDouble()  # pragma: no cover

        @resistance.setter
        def resistance(self, value):
            self._pin_pair_rlc.R = value
            self._set_comp_prop(self._pin_pair_rlc)  # pragma: no cover

        @property
        def inductance(self):
            return self._pin_pair_rlc.L.ToDouble()  # pragma: no cover

        @inductance.setter
        def inductance(self, value):
            self._pin_pair_rlc.L = value
            self._set_comp_prop(self._pin_pair_rlc)  # pragma: no cover

        @property
        def capacitance(self):
            return self._pin_pair_rlc.C.ToDouble()  # pragma: no cover

        @capacitance.setter
        def capacitance(self, value):
            self._pin_pair_rlc.C = value
            self._set_comp_prop(self._pin_pair_rlc)  # pragma: no cover

        @property
        def rlc_values(self):  # pragma: no cover
            rlc = self._pin_pair_rlc
            return [rlc.R.ToDouble(), rlc.L.ToDouble(), rlc.C.ToDouble()]

        @rlc_values.setter
        def rlc_values(self, values):  # pragma: no cover
            rlc = self._pin_pair_rlc
            rlc.R = self._edb_value(values[0])
            rlc.L = self._edb_value(values[1])
            rlc.C = self._edb_value(values[2])
            self._set_comp_prop()  # pragma: no cover

        def _set_comp_prop(self):  # pragma: no cover
            self._edb_model.SetPinPairRlc(self._edb_pin_pair, self._pin_pair_rlc)
            self._edb_comp_prop.SetModel(self._edb_model)
            self._edb_comp.SetComponentProperty(self._edb_comp_prop)

    class _SpiceModel(object):  # pragma: no cover
        def __init__(self, edb_model):
            self._edb_model = edb_model

        @property
        def file_path(self):
            return self._edb_model.GetSPICEFilePath()

        @property
        def name(self):
            return self._edb_model.GetSPICEName()

    class _SparamModel(object):  # pragma: no cover
        def __init__(self, edb_model):
            self._edb_model = edb_model

        @property
        def name(self):
            return self._edb_model.GetComponentModelName()

        @property
        def reference_net(self):
            return self._edb_model.GetReferenceNet()

    class _NetlistModel(object):  # pragma: no cover
        def __init__(self, edb_model):
            self._edb_model = edb_model

        @property
        def netlist(self):
            return self._edb_model.GetNetlist()

    def __init__(self, pedb, cmp):
        self._pedb = pedb
        self.edbcomponent = cmp
        self._layout_instance = None
        self._comp_instance = None

    @property
    def layout_instance(self):
        """EDB layout instance object."""
        return self._pedb.layout_instance

    @property
    def component_instance(self):
        """Edb component instance."""
        if self._comp_instance is None:
            self._comp_instance = self.layout_instance.GetLayoutObjInstance(self.edbcomponent, None)
        return self._comp_instance

    @property
    def _active_layout(self):  # pragma: no cover
        return self._pedb.active_layout

    @property
    def component_property(self):
        """``ComponentProperty`` object."""
        return self.edbcomponent.GetComponentProperty().Clone()

    @property
    def _edb_model(self):  # pragma: no cover
        return self.component_property.GetModel().Clone()

    @property  # pragma: no cover
    def _pin_pairs(self):
        edb_comp_prop = self.component_property
        edb_model = self._edb_model
        return [
            self._PinPair(self, self.edbcomponent, edb_comp_prop, edb_model, pin_pair)
            for pin_pair in list(edb_model.PinPairs)
        ]

    @property
    def is_enabled(self):
        """Get or Set the component to active mode.

        Returns
        -------
        bool
            ``True`` if component is active, ``False`` if is disabled..
        """
        return self.component_property.IsEnabled()

    @is_enabled.setter
    def is_enabled(self, value):
        cmp_prop = self.component_property.Clone()
        cmp_prop.SetEnabled(value)
        self.edbcomponent.SetComponentProperty(cmp_prop)

    @property
    def spice_model(self):
        """Get assigned Spice model properties."""
        if not self.model_type == "SPICEModel":
            return None
        else:
            return self._SpiceModel(self._edb_model)

    @property
    def s_param_model(self):
        """Get assigned S-parameter model properties."""
        if not self.model_type == "SParameterModel":
            return None
        else:
            return self._SparamModel(self._edb_model)

    @property
    def netlist_model(self):
        """Get assigned netlist model properties."""
        if not self.model_type == "NetlistModel":
            return None
        else:
            return self._NetlistModel(self._edb_model)

    @property
    def solder_ball_height(self):
        """Solder ball height if available."""
        if "GetSolderBallProperty" in dir(self.component_property):
            return self.component_property.GetSolderBallProperty().GetHeight()
        return None

    @property
    def solder_ball_placement(self):
        """Solder ball placement if available.."""
        if "GetSolderBallProperty" in dir(self.component_property):
            return int(self.component_property.GetSolderBallProperty().GetPlacement())
        return 2

    @property
    def refdes(self):
        """Reference Designator Name.

        Returns
        -------
        str
            Reference Designator Name.
        """
        return self.edbcomponent.GetName()

    @refdes.setter
    def refdes(self, name):
        self.edbcomponent.SetName(name)

    @property
    def is_null(self):
        """Flag indicating if the current object exists."""
        return self.edbcomponent.IsNull()

    @property
    def is_enabled(self):
        """Flag indicating if the current object is enabled.

        Returns
        -------
        bool
            ``True`` if current object is enabled, ``False`` otherwise.
        """
        if self.type in ["Resistor", "Capacitor", "Inductor"]:
            return self.component_property.IsEnabled()
        else:  # pragma: no cover
            return True

    @is_enabled.setter
    def is_enabled(self, enabled):
        """Enables the current object."""
        if self.type in ["Resistor", "Capacitor", "Inductor"]:
            component_property = self.component_property
            component_property.SetEnabled(enabled)
            self.edbcomponent.SetComponentProperty(component_property)

    @property
    def model_type(self):
        """Retrieve assigned model type."""
        _model_type = self._edb_model.ToString().split(".")[-1]
        if _model_type == "PinPairModel":
            return "RLC"
        else:
            return _model_type

    @property
    def rlc_values(self):
        """Get component rlc values."""
        if not len(self._pin_pairs):
            return [None, None, None]
        pin_pair = self._pin_pairs[0]
        return pin_pair.rlc_values

    @rlc_values.setter
    def rlc_values(self, value):
        if isinstance(value, list):  # pragma no cover
            rlc_enabled = [True if i else False for i in value]
            rlc_values = [self._get_edb_value(i) for i in value]
            model = self._edb.cell.hierarchy._hierarchy.PinPairModel()
            pin_names = list(self.pins.keys())
            for idx, i in enumerate(np.arange(len(pin_names) // 2)):
                pin_pair = self._edb.utility.utility.PinPair(pin_names[idx], pin_names[idx + 1])
                rlc = self._edb.utility.utility.Rlc(
                    rlc_values[0], rlc_enabled[0], rlc_values[1], rlc_enabled[1], rlc_values[2], rlc_enabled[2], False
                )
                model.SetPinPairRlc(pin_pair, rlc)
            self._set_model(model)

    @property
    def value(self):
        """Retrieve discrete component value.

        Returns
        -------
        str
            Value. ``None`` if not an RLC Type.
        """
        if self.model_type == "RLC":
            if not self._pin_pairs:
                if self.type == "Inductor":
                    return 1e-9
                elif self.type == "Resistor":
                    return 1e6
                else:
                    return 1
            else:
                pin_pair = self._pin_pairs[0]
            if len([i for i in pin_pair.rlc_enable if i]) == 1:
                return [pin_pair.rlc_values[idx] for idx, val in enumerate(pin_pair.rlc_enable) if val][0]
            else:
                return pin_pair.rlc_values
        elif self.model_type == "SPICEModel":
            return self.spice_model.file_path
        elif self.model_type == "SParameterModel":
            return self.s_param_model.name
        else:
            return self.netlist_model.netlist

    @value.setter
    def value(self, value):
        rlc_enabled = [True if i == self.type else False for i in ["Resistor", "Inductor", "Capacitor"]]
        rlc_values = [value if i == self.type else 0 for i in ["Resistor", "Inductor", "Capacitor"]]
        rlc_values = [self._get_edb_value(i) for i in rlc_values]

        model = self._edb.cell.hierarchy._hierarchy.PinPairModel()
        pin_names = list(self.pins.keys())
        for idx, i in enumerate(np.arange(len(pin_names) // 2)):
            pin_pair = self._edb.utility.utility.PinPair(pin_names[idx], pin_names[idx + 1])
            rlc = self._edb.utility.utility.Rlc(
                rlc_values[0], rlc_enabled[0], rlc_values[1], rlc_enabled[1], rlc_values[2], rlc_enabled[2], False
            )
            model.SetPinPairRlc(pin_pair, rlc)
        self._set_model(model)

    @property
    def res_value(self):
        """Resistance value.

        Returns
        -------
        str
            Resistance value or ``None`` if not an RLC type.
        """
        cmp_type = int(self.edbcomponent.GetComponentType())
        if 0 < cmp_type < 4:
            componentProperty = self.edbcomponent.GetComponentProperty()
            model = componentProperty.GetModel().Clone()
            pinpairs = model.PinPairs
            if not list(pinpairs):
                return "0"
            for pinpair in pinpairs:
                pair = model.GetPinPairRlc(pinpair)
                return pair.R.ToString()
        return None

    @res_value.setter
    def res_value(self, value):  # pragma no cover
        if value:
            if self.rlc_values == [None, None, None]:
                self.rlc_values = [value, 0, 0]
            else:
                self.rlc_values = [value, self.rlc_values[1], self.rlc_values[2]]

    @property
    def cap_value(self):
        """Capacitance Value.

        Returns
        -------
        str
            Capacitance Value. ``None`` if not an RLC Type.
        """
        cmp_type = int(self.edbcomponent.GetComponentType())
        if 0 < cmp_type < 4:
            componentProperty = self.edbcomponent.GetComponentProperty()
            model = componentProperty.GetModel().Clone()
            pinpairs = model.PinPairs
            if not list(pinpairs):
                return "0"
            for pinpair in pinpairs:
                pair = model.GetPinPairRlc(pinpair)
                return pair.C.ToString()
        return None

    @cap_value.setter
    def cap_value(self, value):  # pragma no cover
        if value:
            if self.rlc_values == [None, None, None]:
                self.rlc_values = [0, 0, value]
            else:
                self.rlc_values = [self.rlc_values[1], self.rlc_values[2], value]

    @property
    def ind_value(self):
        """Inductance Value.

        Returns
        -------
        str
            Inductance Value. ``None`` if not an RLC Type.
        """
        cmp_type = int(self.edbcomponent.GetComponentType())
        if 0 < cmp_type < 4:
            componentProperty = self.edbcomponent.GetComponentProperty()
            model = componentProperty.GetModel().Clone()
            pinpairs = model.PinPairs
            if not list(pinpairs):
                return "0"
            for pinpair in pinpairs:
                pair = model.GetPinPairRlc(pinpair)
                return pair.L.ToString()
        return None

    @ind_value.setter
    def ind_value(self, value):  # pragma no cover
        if value:
            if self.rlc_values == [None, None, None]:
                self.rlc_values = [0, value, 0]
            else:
                self.rlc_values = [self.rlc_values[1], value, self.rlc_values[2]]

    @property
    def is_parallel_rlc(self):
        """Define if model is Parallel or Series.

        Returns
        -------
        bool
            ``True`` if it is a parallel rlc model. ``False`` for series RLC. ``None`` if not an RLC Type.
        """
        cmp_type = int(self.edbcomponent.GetComponentType())
        if 0 < cmp_type < 4:
            model = self.component_property.GetModel().Clone()
            pinpairs = model.PinPairs
            for pinpair in pinpairs:
                pair = model.GetPinPairRlc(pinpair)
                return pair.IsParallel
        return None

    @is_parallel_rlc.setter
    def is_parallel_rlc(self, value):  # pragma no cover
        if not len(self._pin_pairs):
            logging.warning(self.refdes, " has no pin pair.")
        else:
            if isinstance(value, bool):
                componentProperty = self.edbcomponent.GetComponentProperty()
                model = componentProperty.GetModel().Clone()
                pinpairs = model.PinPairs
                if not list(pinpairs):
                    return "0"
                for pin_pair in pinpairs:
                    pin_pair_rlc = model.GetPinPairRlc(pin_pair)
                    pin_pair_rlc.IsParallel = value
                    pin_pair_model = self._edb_model
                    pin_pair_model.SetPinPairRlc(pin_pair, pin_pair_rlc)
                    comp_prop = self.component_property
                    comp_prop.SetModel(pin_pair_model)
                    self.edbcomponent.SetComponentProperty(comp_prop)

    @property
    def center(self):
        """Compute the component center.

        Returns
        -------
        list
        """
        center = self.component_instance.GetCenter()
        return [center.X.ToDouble(), center.Y.ToDouble()]

    @property
    def bounding_box(self):
        """Component's bounding box.

        Returns
        -------
        List[float]
            List of coordinates for the component's bounding box, with the list of
            coordinates in this order: [X lower left corner, Y lower left corner,
            X upper right corner, Y upper right corner].
        """
        bbox = self.component_instance.GetBBox()
        pt1 = bbox.Item1
        pt2 = bbox.Item2
        return [pt1.X.ToDouble(), pt1.Y.ToDouble(), pt2.X.ToDouble(), pt2.Y.ToDouble()]

    @property
    def rotation(self):
        """Compute the component rotation in radian.

        Returns
        -------
        float
        """
        return self.edbcomponent.GetTransform().Rotation.ToDouble()

    @property
    def pinlist(self):
        """Pins of the component.

        Returns
        -------
        list
            List of Pins of Component.
        """
        pins = [
            p
            for p in self.edbcomponent.LayoutObjs
            if p.GetObjType() == self._edb.cell.layout_object_type.PadstackInstance
            and p.IsLayoutPin()
            and p.GetComponent().GetName() == self.refdes
        ]
        return pins

    @property
    def nets(self):
        """Nets of Component.

        Returns
        -------
        list
            List of Nets of Component.
        """
        netlist = []
        for pin in self.pinlist:
            netlist.append(pin.GetNet().GetName())
        return list(set(netlist))

    @property
    def pins(self):
        """EDBPadstackInstance of Component.

        Returns
        -------
        dic[str, :class:`pyaedt.edb_core.edb_data.definitions.EDBPadstackInstance`]
            Dictionary of EDBPadstackInstance Components.
        """
        pins = {}
        for el in self.pinlist:
            pins[el.GetName()] = EDBPadstackInstance(el, self._pedb)
        return pins

    @property
    def type(self):
        """Component type.

        Returns
        -------
        str
            Component type.
        """
        cmp_type = int(self.edbcomponent.GetComponentType())
        if cmp_type == 1:
            return "Resistor"
        elif cmp_type == 2:
            return "Inductor"
        elif cmp_type == 3:
            return "Capacitor"
        elif cmp_type == 4:
            return "IC"
        elif cmp_type == 5:
            return "IO"
        elif cmp_type == 0:
            return "Other"

    @type.setter
    def type(self, new_type):
        """Set component type

        Parameters
        ----------
        new_type : str
            Type of the component. Options are ``"Resistor"``,  ``"Inductor"``, ``"Capacitor"``,
            ``"IC"``, ``"IO"`` and ``"Other"``.
        """
        if new_type == "Resistor":
            type_id = self._pedb.definition.ComponentType.Resistor
        elif new_type == "Inductor":
            type_id = self._pedb.definition.ComponentType.Inductor
        elif new_type == "Capacitor":
            type_id = self._pedb.definition.ComponentType.Capacitor
        elif new_type == "IC":
            type_id = self._pedb.definition.ComponentType.IC
        elif new_type == "IO":
            type_id = self._pedb.definition.ComponentType.IO
        elif new_type == "Other":
            type_id = self._pedb.definition.ComponentType.Other
        else:
            return
        self.edbcomponent.SetComponentType(type_id)

    @property
    def numpins(self):
        """Number of Pins of Component.

        Returns
        -------
        int
            Number of Pins of Component.
        """
        return self.edbcomponent.GetNumberOfPins()

    @property
    def partname(self):  # pragma: no cover
        """Component part name.

        Returns
        -------
        str
            Component Part Name.
        """
        return self.part_name

    @partname.setter
    def partname(self, name):  # pragma: no cover
        """Set component part name."""
        self.part_name = name

    @property
    def part_name(self):
        """Component part name.

        Returns
        -------
        str
            Component part name.
        """
        return self.edbcomponent.GetComponentDef().GetName()

    @part_name.setter
    def part_name(self, name):  # pragma: no cover
        """Set component part name."""
        self.edbcomponent.GetComponentDef().SetName(name)

    @property
    def _edb(self):
        return self._pedb.edb_api

    @property
    def placement_layer(self):
        """Placement layer.

        Returns
        -------
        str
           Name of the placement layer.
        """
        return self.edbcomponent.GetPlacementLayer().Clone().GetName()

    @property
    def lower_elevation(self):
        """Lower elevation of the placement layer.

        Returns
        -------
        float
            Lower elevation of the placement layer.
        """
        return self.edbcomponent.GetPlacementLayer().Clone().GetLowerElevation()

    @property
    def upper_elevation(self):
        """Upper elevation of the placement layer.

        Returns
        -------
        float
            Upper elevation of the placement layer.

        """
        return self.edbcomponent.GetPlacementLayer().Clone().GetUpperElevation()

    @property
    def top_bottom_association(self):
        """Top/bottom association of the placement layer.

        Returns
        -------
        int
            Top/bottom association of the placement layer, where:

            * 0 - Top associated
            * 1 - No association
            * 2 - Bottom associated
            * 4 - Number of top/bottom associations.
            * -1 - Undefined
        """
        return int(self.edbcomponent.GetPlacementLayer().GetTopBottomAssociation())

    @pyaedt_function_handler
    def _get_edb_value(self, value):
        return self._pedb.edb_value(value)

    @pyaedt_function_handler
    def _set_model(self, model):  # pragma: no cover
        comp_prop = self.component_property
        comp_prop.SetModel(model)
        if not self.edbcomponent.SetComponentProperty(comp_prop):
            logging.error("Fail to assign model on {}.".format(self.refdes))
            return False
        return True

    @pyaedt_function_handler
    def assign_spice_model(self, file_path, name=None):
        """Assign Spice model to this component.

        Parameters
        ----------
        file_path : str
            File path of the Spice model.
        name : str, optional
            Name of the Spice model.

        Returns
        -------

        """
        if not name:
            name = get_filename_without_extension(file_path)

        with open(file_path, "r") as f:
            for line in f:
                if "subckt" in line.lower():
                    pinNames = [i.strip() for i in re.split(" |\t", line) if i]
                    pinNames.remove(pinNames[0])
                    pinNames.remove(pinNames[0])
                    break
        if len(pinNames) == self.numpins:
            model = self._edb.cell.hierarchy._hierarchy.SPICEModel()
            model.SetModelPath(file_path)
            model.SetModelName(name)
            terminal = 1
            for pn in pinNames:
                model.AddTerminalPinPair(pn, str(terminal))
                terminal += 1
        else:  # pragma: no cover
            logging.error("Wrong number of Pins")
            return False
        return self._set_model(model)

    @pyaedt_function_handler
    def assign_s_param_model(self, file_path, name=None, reference_net=None):
        """Assign S-parameter to this component.

        Parameters
        ----------
        file_path : str
            File path of the S-parameter model.
        name : str, optional
            Name of the S-parameter model.

        Returns
        -------

        """
        if not name:
            name = get_filename_without_extension(file_path)

        edbComponentDef = self.edbcomponent.GetComponentDef()
        nPortModel = self._edb.definition.NPortComponentModel.FindByName(edbComponentDef, name)
        if nPortModel.IsNull():
            nPortModel = self._edb.definition.NPortComponentModel.Create(name)
            nPortModel.SetReferenceFile(file_path)
            edbComponentDef.AddComponentModel(nPortModel)

        model = self._edb.cell.hierarchy._hierarchy.SParameterModel()
        model.SetComponentModelName(name)
        if reference_net:
            model.SetReferenceNet(reference_net)
        return self._set_model(model)

    @pyaedt_function_handler
    def assign_rlc_model(self, res=None, ind=None, cap=None, is_parallel=False):
        """Assign RLC to this component.

        Parameters
        ----------
        res : int, float
            Resistance. Default is ``None``.
        ind : int, float
            Inductance. Default is ``None``.
        cap : int, float
            Capacitance. Default is ``None``.
        is_parallel : bool, optional
            Whether it is a parallel or series RLC component. The default is ``False``.
        """
        if res is None and ind is None and cap is None:
            self._pedb.logger.error("At least one value has to be provided.")
            return False
        r_enabled = True if res else False
        l_enabled = True if ind else False
        c_enabled = True if cap else False
        res = 0 if res is None else res
        ind = 0 if ind is None else ind
        cap = 0 if cap is None else cap
        res, ind, cap = self._get_edb_value(res), self._get_edb_value(ind), self._get_edb_value(cap)
        model = self._edb.cell.hierarchy._hierarchy.PinPairModel()

        pin_names = list(self.pins.keys())
        for idx, i in enumerate(np.arange(len(pin_names) // 2)):
            pin_pair = self._edb.utility.utility.PinPair(pin_names[idx], pin_names[idx + 1])

            rlc = self._edb.utility.utility.Rlc(res, r_enabled, ind, l_enabled, cap, c_enabled, is_parallel)
            model.SetPinPairRlc(pin_pair, rlc)
        return self._set_model(model)

    @pyaedt_function_handler
    def create_clearance_on_component(self, extra_soldermask_clearance=1e-4):
        """Create a Clearance on Soldermask layer by drawing a rectangle.

        Parameters
        ----------
        extra_soldermask_clearance : float, optional
            Extra Soldermask value in meter to be applied on component bounding box.

        Returns
        -------
            bool
        """
        bounding_box = self.bounding_box
        opening = [bounding_box[0] - extra_soldermask_clearance]
        opening.append(bounding_box[1] - extra_soldermask_clearance)
        opening.append(bounding_box[2] + extra_soldermask_clearance)
        opening.append(bounding_box[3] + extra_soldermask_clearance)

        comp_layer = self.placement_layer
        layer_names = list(self._pedb.stackup.stackup_layers.keys())
        layer_index = layer_names.index(comp_layer)
        if comp_layer in [layer_names[0] + layer_names[-1]]:
            return False
        elif layer_index < len(layer_names) / 2:
            soldermask_layer = layer_names[layer_index - 1]
        else:
            soldermask_layer = layer_names[layer_index + 1]

        if not self._pedb.modeler.get_primitives(layer_name=soldermask_layer):
            all_nets = list(self._pedb.nets.nets.values())
            poly = self._pedb._create_conformal(all_nets, 0, 1e-12, False, 0)
            self._pedb.modeler.create_polygon(poly, soldermask_layer, [], "")

        void = self._pedb.modeler.create_rectangle(
            soldermask_layer,
            "{}_opening".format(self.refdes),
            lower_left_point=opening[:2],
            upper_right_point=opening[2:],
        )
        void.is_negative = True
        return True
