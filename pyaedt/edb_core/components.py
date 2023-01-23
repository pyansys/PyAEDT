"""This module contains the `Components` class.

"""
import codecs
import json
import math
import re

from pyaedt import _retry_ntimes
from pyaedt.edb_core.edb_data.components_data import EDBComponent
from pyaedt.edb_core.edb_data.components_data import EDBComponentDef
from pyaedt.edb_core.edb_data.padstacks_data import EDBPadstackInstance
from pyaedt.edb_core.edb_data.sources import Source
from pyaedt.edb_core.edb_data.sources import SourceType
from pyaedt.edb_core.general import convert_py_list_to_net_list
from pyaedt.edb_core.padstack import EdbPadstacks
from pyaedt.generic.clr_module import String
from pyaedt.generic.clr_module import _clr
from pyaedt.generic.general_methods import get_filename_without_extension
from pyaedt.generic.general_methods import is_ironpython
from pyaedt.generic.general_methods import pyaedt_function_handler
from pyaedt.modeler.geometry_operators import GeometryOperators


def resistor_value_parser(RValue):
    """Convert a resistor value.

    Parameters
    ----------
    RValue : float
        Resistor value.

    Returns
    -------
    float
        Resistor value.

    """
    if isinstance(RValue, str):
        RValue = RValue.replace(" ", "")
        RValue = RValue.replace("meg", "m")
        RValue = RValue.replace("Ohm", "")
        RValue = RValue.replace("ohm", "")
        RValue = RValue.replace("k", "e3")
        RValue = RValue.replace("m", "e-3")
        RValue = RValue.replace("M", "e6")
    RValue = float(RValue)
    return RValue


class Components(object):
    """Manages EDB components and related method accessible from `Edb.core_components` property.

    Parameters
    ----------
    edb_class : :class:`pyaedt.edb.Edb`

    Examples
    --------
    >>> from pyaedt import Edb
    >>> edbapp = Edb("myaedbfolder")
    >>> edbapp.core_components
    """

    def __init__(self, p_edb):
        self._pedb = p_edb
        self._cmp = {}
        self._res = {}
        self._cap = {}
        self._ind = {}
        self._ios = {}
        self._ics = {}
        self._others = {}
        self._pins = {}
        self._comps_by_part = {}
        self._init_parts()
        self._padstack = EdbPadstacks(self._pedb)

    @property
    def _logger(self):
        """Logger."""
        return self._pedb.logger

    @property
    def _edb(self):
        return self._pedb.edb

    @pyaedt_function_handler()
    def _init_parts(self):
        a = self.components
        a = self.resistors
        a = self.ICs
        a = self.Others
        a = self.inductors
        a = self.IOs
        a = self.components_by_partname
        return True

    @property
    def _builder(self):
        return self._pedb.builder

    def _get_edb_value(self, value):
        return self._pedb.edb_value(value)

    @property
    def _edbutils(self):
        return self._pedb.edbutils

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
    def components(self):
        """Component setup information.

        Returns
        -------
        dict[str, :class:`pyaedt.edb_core.edb_data.components_data.EDBComponent`]
            Default dictionary for the EDB component.

        Examples
        --------

        >>> from pyaedt import Edb
        >>> edbapp = Edb("myaedbfolder")
        >>> edbapp.core_components.components

        """
        if not self._cmp:
            self.refresh_components()
        return self._cmp

    @property
    def definitions(self):
        """Retrieve component definition list.

        Returns
        -------
        dict of :class:`pyaedt.edb_core.edb_data.components_data.EDBComponentDef`"""
        return {l.GetName(): EDBComponentDef(self, l) for l in list(self._db.ComponentDefs)}

    @property
    def nport_comp_definition(self):
        """Retrieve Nport component definition list."""
        m = "Ansys.Ansoft.Edb.Definition.NPortComponentModel"
        return {name: l for name, l in self.definitions.items() if m in [i.ToString() for i in l._comp_model]}

    @pyaedt_function_handler()
    def import_definition(self, file_path):
        """Import component definition from json file.

        Parameters
        ----------
        file_path : str
            File path of json file.
        """
        with codecs.open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for part_name, p in data["Definitions"].items():
                model_type = p["Model_type"]
                comp_definition = self.definitions[part_name]
                comp_definition.type = p["Component_type"]

                if model_type == "RLC":
                    comp_definition.assign_rlc_model(p["Res"], p["Ind"], p["Cap"], p["Is_parallel"])
                else:
                    model_name = p["Model_name"]
                    file_path = data[model_type][model_name]
                    if model_type == "SParameterModel":
                        if "Reference_net" in p:
                            reference_net = p["Reference_net"]
                        else:
                            reference_net = None
                        comp_definition.assign_s_param_model(file_path, model_name, reference_net)
                    elif model_type == "SPICEModel":
                        comp_definition.assign_spice_model(file_path, model_name)
                    else:
                        pass
        return True

    @pyaedt_function_handler()
    def export_definition(self, file_path):
        """Export component definitions to json file.

        Parameters
        ----------
        file_path : str
            File path of json file.
        Returns
        -------

        """
        data = {
            "SParameterModel": {},
            "SPICEModel": {},
            "Definitions": {},
        }
        for part_name, props in self.definitions.items():
            comp_list = list(props.components.values())
            if comp_list:
                data["Definitions"][part_name] = {}
                data["Definitions"][part_name]["Component_type"] = props.type
                comp = comp_list[0]
                data["Definitions"][part_name]["Model_type"] = comp.model_type
                if comp.model_type == "RLC":
                    rlc_values = [i if i else 0 for i in comp.rlc_values]
                    data["Definitions"][part_name]["Res"] = rlc_values[0]
                    data["Definitions"][part_name]["Ind"] = rlc_values[1]
                    data["Definitions"][part_name]["Cap"] = rlc_values[2]
                    data["Definitions"][part_name]["Is_parallel"] = True if comp.is_parallel_rlc else False
                else:
                    if comp.model_type == "SParameterModel":
                        model = comp.s_param_model
                        data["Definitions"][part_name]["Model_name"] = model.name
                        data["Definitions"][part_name]["Reference_net"] = model.reference_net
                        if not model.name in data["SParameterModel"]:
                            data["SParameterModel"][model.name] = model.file_path
                    elif comp.model_type == "SPICEModel":
                        model = comp.spice_model
                        data["Definitions"][part_name]["Model_name"] = model.name
                        if not model.name in data["SPICEModel"]:
                            data["SPICEModel"][model.name] = model.file_path
                    else:
                        model = comp.netlist_model
                        data["Definitions"][part_name]["Model_name"] = model.netlist

        with codecs.open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return file_path

    @pyaedt_function_handler()
    def refresh_components(self):
        """Refresh the component dictionary."""
        self._logger.info("Refreshing the Components dictionary.")
        self._cmp = {
            l.GetName(): EDBComponent(self, l)
            for l in self._active_layout.Groups
            if l.ToString() == "Ansys.Ansoft.Edb.Cell.Hierarchy.Component"
        }
        return True

    @property
    def resistors(self):
        """Resistors.

        Returns
        -------
        dict[str, :class:`pyaedt.edb_core.edb_data.components_data.EDBComponent`]
            Dictionary of resistors.

        Examples
        --------

        >>> from pyaedt import Edb
        >>> edbapp = Edb("myaedbfolder")
        >>> edbapp.core_components.resistors
        """
        self._res = {}
        for el, val in self.components.items():
            if val.type == "Resistor":
                self._res[el] = val
        return self._res

    @property
    def capacitors(self):
        """Capacitors.

        Returns
        -------
        dict[str, :class:`pyaedt.edb_core.edb_data.components_data.EDBComponent`]
            Dictionary of capacitors.

        Examples
        --------

        >>> from pyaedt import Edb
        >>> edbapp = Edb("myaedbfolder")
        >>> edbapp.core_components.capacitors
        """
        self._cap = {}
        for el, val in self.components.items():
            if val.type == "Capacitor":
                self._cap[el] = val
        return self._cap

    @property
    def inductors(self):
        """Inductors.

        Returns
        -------
        dict[str, :class:`pyaedt.edb_core.edb_data.components_data.EDBComponent`]
            Dictionary of inductors.

        Examples
        --------

        >>> from pyaedt import Edb
        >>> edbapp = Edb("myaedbfolder")
        >>> edbapp.core_components.inductors

        """
        self._ind = {}
        for el, val in self.components.items():
            if val.type == "Inductor":
                self._ind[el] = val
        return self._ind

    @property
    def ICs(self):
        """Integrated circuits.

        Returns
        -------
        dict[str, :class:`pyaedt.edb_core.edb_data.components_data.EDBComponent`]
            Dictionary of integrated circuits.

        Examples
        --------

        >>> from pyaedt import Edb
        >>> edbapp = Edb("myaedbfolder")
        >>> edbapp.core_components.ICs

        """
        self._ics = {}
        for el, val in self.components.items():
            if val.type == "IC":
                self._ics[el] = val
        return self._ics

    @property
    def IOs(self):
        """Circuit inupts and outputs.

        Returns
        -------
        dict[str, :class:`pyaedt.edb_core.edb_data.components_data.EDBComponent`]
            Dictionary of circuit inputs and outputs.

        Examples
        --------

        >>> from pyaedt import Edb
        >>> edbapp = Edb("myaedbfolder")
        >>> edbapp.core_components.IOs

        """
        self._ios = {}
        for el, val in self.components.items():
            if val.type == "IO":
                self._ios[el] = val
        return self._ios

    @property
    def Others(self):
        """Other core components.

        Parameters
        ----------

        Returns
        -------
        dict[str, :class:`pyaedt.edb_core.edb_data.components_data.EDBComponent`]
            Dictionary of other core components.

        Examples
        --------

        >>> from pyaedt import Edb
        >>> edbapp = Edb("myaedbfolder")
        >>> edbapp.core_components.others

        """
        self._others = {}
        for el, val in self.components.items():
            if val.type == "Other":
                self._others[el] = val
        return self._others

    @property
    def components_by_partname(self):
        """Components by part name.

        Returns
        -------
        dict
            Dictionary of components by part name.

        Examples
        --------

        >>> from pyaedt import Edb
        >>> edbapp = Edb("myaedbfolder")
        >>> edbapp.core_components.components_by_partname

        """
        self._comps_by_part = {}
        for el, val in self.components.items():
            if val.partname in self._comps_by_part.keys():
                self._comps_by_part[val.partname].append(val)
            else:
                self._comps_by_part[val.partname] = [val]
        return self._comps_by_part

    @pyaedt_function_handler()
    def get_component_list(self):
        """Retrieve conponent setup information.

        Returns
        -------
        list
            List of component setup information.

        """
        cmp_setup_info_list = self._edbutils.ComponentSetupInfo.GetFromLayout(self._active_layout)
        cmp_list = []
        for comp in cmp_setup_info_list:
            cmp_list.append(comp)
        return cmp_list

    @pyaedt_function_handler()
    def get_component_by_name(self, name):
        """Retrieve a component by name.

        Parameters
        ----------
        name : str
            Name of the component.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        edbcmp = self._edb.Cell.Hierarchy.Component.FindByName(self._active_layout, name)
        if edbcmp is not None:
            return edbcmp
        else:
            pass

    @pyaedt_function_handler()
    def get_components_from_nets(self, netlist=None):
        """Retrieve components from a net list.

        Parameters
        ----------
        netlist : str, optional
            Name of the net list. The default is ``None``.

        Returns
        -------
        list
            List of components that belong to the signal nets.

        """
        cmp_list = []
        if isinstance(netlist, str):
            netlist = [netlist]
        components = list(self.components.keys())
        for refdes in components:
            cmpnets = self._cmp[refdes].nets
            if set(cmpnets).intersection(set(netlist)):
                cmp_list.append(refdes)
        return cmp_list

    @pyaedt_function_handler()
    def _get_edb_pin_from_pin_name(self, cmp, pin):
        if not isinstance(cmp, self._edb.Cell.Hierarchy.Component):
            return False
        if not isinstance(pin, str):
            pin = pin.GetName()
        pins = self.get_pin_from_component(component=cmp, pinName=pin)
        if pins:
            return pins[0]
        return False

    @pyaedt_function_handler()
    def get_component_placement_vector(
        self,
        mounted_component,
        hosting_component,
        mounted_component_pin1,
        mounted_component_pin2,
        hosting_component_pin1,
        hosting_component_pin2,
        flipped=False,
    ):
        """Get the placement vector between 2 components.

        Parameters
        ----------
        mounted_component : `edb.Cell.Hierarchy.Component`
            Mounted component name.
        hosting_component : `edb.Cell.Hierarchy.Component`
            Hosting component name.
        mounted_component_pin1 : str
            Mounted component Pin 1 name.
        mounted_component_pin2 : str
            Mounted component Pin 2 name.
        hosting_component_pin1 : str
            Hosted component Pin 1 name.
        hosting_component_pin2 : str
            Hosted component Pin 2 name.
        flipped : bool, optional
            Either if the mounted component will be flipped or not.

        Returns
        -------
        tuple
            Tuple of Vector offset, rotation and solder height.

        Examples
        --------
        >>> edb1 = Edb(edbpath=targetfile1,  edbversion="2021.2")
        >>> hosting_cmp = edb1.core_components.get_component_by_name("U100")
        >>> mounted_cmp = edb2.core_components.get_component_by_name("BGA")
        >>> vector, rotation, solder_ball_height = edb1.core_components.get_component_placement_vector(
        ...                                             mounted_component=mounted_cmp,
        ...                                             hosting_component=hosting_cmp,
        ...                                             mounted_component_pin1="A12",
        ...                                             mounted_component_pin2="A14",
        ...                                             hosting_component_pin1="A12",
        ...                                             hosting_component_pin2="A14")
        """
        m_pin1_pos = [0.0, 0.0]
        m_pin2_pos = [0.0, 0.0]
        h_pin1_pos = [0.0, 0.0]
        h_pin2_pos = [0.0, 0.0]
        if not isinstance(mounted_component, self._edb.Cell.Hierarchy.Component):
            return False
        if not isinstance(hosting_component, self._edb.Cell.Hierarchy.Component):
            return False

        if mounted_component_pin1:
            m_pin1 = self._get_edb_pin_from_pin_name(mounted_component, mounted_component_pin1)
            m_pin1_pos = self.get_pin_position(m_pin1)
        if mounted_component_pin2:
            m_pin2 = self._get_edb_pin_from_pin_name(mounted_component, mounted_component_pin2)
            m_pin2_pos = self.get_pin_position(m_pin2)

        if hosting_component_pin1:
            h_pin1 = self._get_edb_pin_from_pin_name(hosting_component, hosting_component_pin1)
            h_pin1_pos = self.get_pin_position(h_pin1)

        if hosting_component_pin2:
            h_pin2 = self._get_edb_pin_from_pin_name(hosting_component, hosting_component_pin2)
            h_pin2_pos = self.get_pin_position(h_pin2)
        #
        vector = [h_pin1_pos[0] - m_pin1_pos[0], h_pin1_pos[1] - m_pin1_pos[1]]
        vector1 = GeometryOperators.v_points(m_pin1_pos, m_pin2_pos)
        vector2 = GeometryOperators.v_points(h_pin1_pos, h_pin2_pos)
        multiplier = 1
        if flipped:
            multiplier = -1
        vector1[1] = multiplier * vector1[1]

        rotation = GeometryOperators.v_angle_sign_2D(vector1, vector2, False)
        if rotation != 0.0:
            layinst = mounted_component.GetLayout().GetLayoutInstance()
            cmpinst = layinst.GetLayoutObjInstance(mounted_component, None)
            center = cmpinst.GetCenter()
            center_double = [center.X.ToDouble(), center.Y.ToDouble()]
            vector_center = GeometryOperators.v_points(center_double, m_pin1_pos)
            x_v2 = vector_center[0] * math.cos(rotation) + multiplier * vector_center[1] * math.sin(rotation)
            y_v2 = -1 * vector_center[0] * math.sin(rotation) + multiplier * vector_center[1] * math.cos(rotation)
            new_vector = [x_v2 + center_double[0], y_v2 + center_double[1]]
            vector = [h_pin1_pos[0] - new_vector[0], h_pin1_pos[1] - new_vector[1]]

        if vector:
            solder_ball_height = self.get_solder_ball_height(mounted_component)
            return True, vector, rotation, solder_ball_height
        self._logger.warning("Failed to compute vector.")
        return False, [0, 0], 0, 0

    @pyaedt_function_handler()
    def get_solder_ball_height(self, cmp):
        """Get component solder ball height.

        Parameters
        ----------
        cmp : str or self._edb.Cell.Hierarchy.Component
            EDB component or str component name.

        Returns
        -------
        double, bool
            Salder ball height vale, ``False`` when failed.

        """
        if cmp is not None:
            if not (isinstance(cmp, self._edb.Cell.Hierarchy.Component)):
                cmp = self.get_component_by_name(cmp)
            cmp_prop = cmp.GetComponentProperty().Clone()
            return cmp_prop.GetSolderBallProperty().GetHeight()
        return False

    @pyaedt_function_handler()
    def create_source_on_component(self, sources=None):
        """Create voltage, current source, or resistor on component.

        Parameters
        ----------
        sources : list[Source]
            List of ``edb_data.sources.Source`` objects.

        Returns
        -------
        double, bool
            ``True`` when successful, ``False`` when failed.

        """

        if not sources:  # pragma: no cover
            return False
        if isinstance(sources, Source):  # pragma: no cover
            sources = [sources]
        if isinstance(sources, list):  # pragma: no cover
            for src in sources:
                if not isinstance(src, Source):  # pragma: no cover
                    self._logger.error("List of source objects must be passed as an argument.")
                    return False
        for source in sources:
            positive_pins = self.get_pin_from_component(source.positive_node.component, source.positive_node.net)
            negative_pins = self.get_pin_from_component(source.negative_node.component, source.negative_node.net)
            positive_pin_group = self.create_pingroup_from_pins(positive_pins)
            if not positive_pin_group:  # pragma: no cover
                return False
            negative_pin_group = self.create_pingroup_from_pins(negative_pins)
            if not negative_pin_group:  # pragma: no cover
                return False
            if source.source_type == SourceType.Vsource:  # pragma: no cover
                positive_pin_group_term = self._create_pin_group_terminal(
                    positive_pin_group, source.positive_node.component
                )
                negative_pin_group_term = self._create_pin_group_terminal(
                    negative_pin_group, source.negative_node.component, isref=True
                )
                positive_pin_group_term.SetBoundaryType(self._edb.Cell.Terminal.BoundaryType.kVoltageSource)
                negative_pin_group_term.SetBoundaryType(self._edb.Cell.Terminal.BoundaryType.kVoltageSource)
                term_name = source.name
                positive_pin_group_term.SetName(term_name)
                negative_pin_group_term.SetName("{}_ref".format(term_name))
                positive_pin_group_term.SetSourceAmplitude(self._get_edb_value(source.amplitude))
                negative_pin_group_term.SetSourceAmplitude(self._get_edb_value(source.amplitude))
                positive_pin_group_term.SetSourcePhase(self._get_edb_value(source.phase))
                negative_pin_group_term.SetSourcePhase(self._get_edb_value(source.phase))
                positive_pin_group_term.SetImpedance(self._get_edb_value(source.impedance))
                negative_pin_group_term.SetImpedance(self._get_edb_value(source.impedance))
                positive_pin_group_term.SetReferenceTerminal(negative_pin_group_term)
            elif source.source_type == SourceType.Isource:  # pragma: no cover
                positive_pin_group_term = self._create_pin_group_terminal(
                    positive_pin_group, source.positive_node.component
                )
                negative_pin_group_term = self._create_pin_group_terminal(
                    negative_pin_group, source.negative_node.component, isref=True
                )
                positive_pin_group_term.SetBoundaryType(self._edb.Cell.Terminal.BoundaryType.kCurrentSource)
                negative_pin_group_term.SetBoundaryType(self._edb.Cell.Terminal.BoundaryType.kCurrentSource)
                term_name = source.name
                positive_pin_group_term.SetName(term_name)
                negative_pin_group_term.SetName("{}_ref".format(term_name))
                positive_pin_group_term.SetSourceAmplitude(self._get_edb_value(source.amplitude))
                negative_pin_group_term.SetSourceAmplitude(self._get_edb_value(source.amplitude))
                positive_pin_group_term.SetSourcePhase(self._get_edb_value(source.phase))
                negative_pin_group_term.SetSourcePhase(self._get_edb_value(source.phase))
                positive_pin_group_term.SetImpedance(self._get_edb_value(source.impedance))
                negative_pin_group_term.SetImpedance(self._get_edb_value(source.impedance))
                positive_pin_group_term.SetReferenceTerminal(negative_pin_group_term)
            elif source.source_type == SourceType.Rlc:  # pragma: no cover
                self.create_rlc_component(
                    pins=[positive_pins[0], negative_pins[0]],
                    component_name=source.name,
                    r_value=source.r_value,
                    l_value=source.l_value,
                    c_value=source.c_value,
                )
        return True

    @pyaedt_function_handler()
    def create_port_on_component(
        self,
        component,
        net_list,
        port_type=SourceType.CoaxPort,
        do_pingroup=True,
        reference_net="gnd",
    ):
        """Create ports on given component.

        Parameters
        ----------
        component : str or self._edb.Cell.Hierarchy.Component
            EDB component or str component name.

        net_list : str or list of string.
            List of nets where ports must be created on the component.
            If the net is not part of the component, this parameter is skipped.

        port_type : SourceType enumerator, CoaxPort or CircuitPort
            Type of port to create. ``CoaxPort`` generates solder balls.
            ``CircuitPort`` generates circuit ports on pins belonging to the net list.

        do_pingroup : bool
            True activate pingroup during port creation (only used with combination of CoaxPort),
            False will take the closest reference pin and generate one port per signal pin.

        refnet : string or list of string.
            list of the reference net.

        Returns
        -------
        double, bool
            Salder ball height vale, ``False`` when failed.

        Examples
        --------

        >>> from pyaedt import Edb
        >>> edbapp = Edb("myaedbfolder")
        >>> net_list = ["M_DQ<1>", "M_DQ<2>", "M_DQ<3>", "M_DQ<4>", "M_DQ<5>"]
        >>> edbapp.core_components.create_port_on_component(cmp="U2A5", net_list=net_list,
        >>> port_type=SourceType.CoaxPort, do_pingroup=False, refnet="GND")

        """
        if isinstance(component, str):
            component = self.components[component].edbcomponent
        if not isinstance(net_list, list):
            net_list = [net_list]
        for net in net_list:
            if not isinstance(net, str):
                try:
                    net_name = net.GetName()
                    if net_name != "":
                        net_list.append(net_name)
                except:
                    pass
        if reference_net in net_list:
            net_list.remove(reference_net)
        cmp_pins = [
            p for p in list(component.LayoutObjs) if int(p.GetObjType()) == 1 and p.GetNet().GetName() in net_list
        ]
        for p in cmp_pins:  # pragma no cover
            if not p.IsLayoutPin():
                p.SetIsLayoutPin(True)
        if len(cmp_pins) == 0:
            self._logger.info(
                "No pins found on component {}, searching padstack instances instead".format(component.GetName())
            )
            return False
        pin_layers = cmp_pins[0].GetPadstackDef().GetData().GetLayerNames()
        if port_type == SourceType.CoaxPort:
            pad_params = self._padstack.get_pad_parameters(pin=cmp_pins[0], layername=pin_layers[0], pad_type=0)
            sball_diam = min([self._pedb.edb_value(val).ToDouble() for val in pad_params[1]])
            solder_ball_height = sball_diam
            self.set_solder_ball(component, solder_ball_height, sball_diam)
            for pin in cmp_pins:
                self._padstack.create_coax_port(pin)

        elif port_type == SourceType.CircPort:  # pragma no cover
            ref_pins = [
                p
                for p in list(component.LayoutObjs)
                if int(p.GetObjType()) == 1 and p.GetNet().GetName() in reference_net
            ]
            for p in ref_pins:
                if not p.IsLayoutPin():
                    p.SetIsLayoutPin(True)
            if len(ref_pins) == 0:
                self._logger.info("No reference pin found on component {}.".format(component.GetName()))
            if do_pingroup:
                if len(ref_pins) == 1:
                    self.create_terminal = self._create_terminal(ref_pins[0])
                    self.terminal = self.create_terminal
                    ref_pin_group_term = self.terminal
                else:
                    ref_pin_group = self.create_pingroup_from_pins(ref_pins)
                    if not ref_pin_group:
                        return False
                    ref_pin_group_term = self._create_pin_group_terminal(ref_pin_group, component, isref=True)
                    if not ref_pin_group_term:
                        return False
                for net in net_list:
                    pins = [pin for pin in cmp_pins if pin.GetNet().GetName() == net]
                    if pins:
                        pin_group = self.create_pingroup_from_pins(pins)
                        if not pin_group:
                            return False
                        pin_group_term = self._create_pin_group_terminal(pin_group, component)
                        if pin_group_term:
                            pin_group_term.SetReferenceTerminal(ref_pin_group_term)
                    else:
                        self._logger.info("No pins found on component {} for the net {}".format(component, net))

            else:
                ref_pin_group = self.create_pingroup_from_pins(ref_pins)
                if not ref_pin_group:
                    self._logger.warning("failed to create reference pin group")
                    return False
                for net in net_list:
                    pins = [pin for pin in cmp_pins if pin.GetNet().GetName() == net]
                    for pin in pins:
                        ref_pin = self._get_closest_pin_from(pin, ref_pins)
                        ref_pin_term = self._create_terminal(ref_pin)
                        term = self._create_terminal(pin)
                        ref_pin_term.SetBoundaryType(self._edb.Cell.Terminal.BoundaryType.PortBoundary)
                        ref_pin_term.SetIsCircuitPort(True)
                        term.SetBoundaryType(self._edb.Cell.Terminal.BoundaryType.PortBoundary)
                        term.SetIsCircuitPort(True)
                        term.SetReferenceTerminal(ref_pin_term)
        return True

    @pyaedt_function_handler()
    def _create_terminal(self, pin):
        """Create terminal on component pin.

        Parameters
        ----------
        pin : Edb padstack instance.

        Returns
        -------
        Edb terminal.
        """

        pin_position = self.get_pin_position(pin)  # pragma no cover
        pin_pos = self._edb.Geometry.PointData(
            self._get_edb_value(pin_position[0]), self._get_edb_value(pin_position[1])  # pragma no cover
        )
        res, from_layer, _ = pin.GetLayerRange()
        cmp_name = pin.GetComponent().GetName()
        net_name = pin.GetNet().GetName()
        pin_name = pin.GetName()
        term_name = "{}.{}.{}".format(cmp_name, net_name, pin_name)
        term = self._edb.Cell.Terminal.PointTerminal.Create(
            pin.GetLayout(), pin.GetNet(), term_name, pin_pos, from_layer
        )
        return term

    @pyaedt_function_handler()
    def _get_closest_pin_from(self, pin, ref_pinlist):
        """Returns the closest pin from given pin among the list of reference pins.

        Parameters
        ----------
        pin : Edb padstack instance.

        ref_pinlist : list of reference edb pins.

        Returns
        -------
        Edb pin.

        """
        res, pin_position, pin_rot = pin.GetPositionAndRotation(
            self._edb.Geometry.PointData(self._get_edb_value(0.0), self._get_edb_value(0.0)),
            0.0,
        )
        distance = 1e3
        closest_pin = ref_pinlist[0]
        for ref_pin in ref_pinlist:
            res, ref_pin_position, ref_pin_rot = ref_pin.GetPositionAndRotation(
                self._edb.Geometry.PointData(self._get_edb_value(0.0), self._get_edb_value(0.0)),
                0.0,
            )
            temp_distance = pin_position.Distance(ref_pin_position)
            if temp_distance < distance:
                distance = temp_distance
                closest_pin = ref_pin
        return closest_pin

    @pyaedt_function_handler()
    def deactivate_rlc_component(self, component=None, create_circuit_port=False):
        """Deactivate RLC component with a possibility to convert to a circuit port.

        Parameters
        ----------
        component : str
            Reference designator of the RLC component.

        create_circuit_port : bool, optional
            Whether to replace the deactivated RLC component with a circuit port. The default
            is ``False``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------
        >>> from pyaedt import Edb
        >>> edb_file = r'C:\my_edb_file.aedb'
        >>> edb = Edb(edb_file)
        >>> for cmp in list(edb.core_components.components.keys()):
        >>>     edb.core_components.deactivate_rlc_component(component=cmp, create_circuit_port=False)
        >>> edb.save_edb()
        >>> edb.close_edb()
        """
        if not component:
            return False
        if isinstance(component, str):
            component = self.components[component]
            if not component:
                self._logger.error("component %s not found.", component)
                return False
        component_type = component.edbcomponent.GetComponentType()
        if (
            component_type == self._edb.Definition.ComponentType.Other
            or component_type == self._edb.Definition.ComponentType.IC
            or component_type == self._edb.Definition.ComponentType.IO
        ):
            self._logger.info("Component %s passed to deactivate is not an RLC.", component.refdes)
            return False
        if create_circuit_port:
            self.add_port_on_rlc_component(component.refdes)
            return True
        else:
            return self.set_component_rlc(component.refdes)

    @pyaedt_function_handler()
    def add_port_on_rlc_component(self, component=None):
        """Deactivate RLC component and replace it with a circuit port.
        The circuit port supports only 2-pin components.

        Parameters
        ----------
        component : str
            Reference designator of the RLC component.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if isinstance(component, str):  # pragma: no cover
            component = self.components[component]
        if not isinstance(component, EDBComponent):  # pragma: no cover
            return False
        self.set_component_rlc(component.refdes)
        pins = self.get_pin_from_component(component.refdes)
        if len(pins) == 2:  # pragma: no cover
            pos_pin_loc = self.get_pin_position(pins[0])
            pt = self._pedb.edb.Geometry.PointData(
                self._get_edb_value(pos_pin_loc[0]), self._get_edb_value(pos_pin_loc[1])
            )
            pin_layers = self._padstack._get_pin_layer_range(pins[0])
            pos_pin_term = self._pedb.edb.Cell.Terminal.PointTerminal.Create(
                self._active_layout, pins[0].GetNet(), pins[0].GetName(), pt, pin_layers[0]
            )
            if not pos_pin_term:  # pragma: no cover
                return False
            neg_pin_loc = self.get_pin_position(pins[1])
            pt = self._pedb.edb.Geometry.PointData(
                self._get_edb_value(neg_pin_loc[0]), self._get_edb_value(neg_pin_loc[1])
            )
            neg_pin_term = self._pedb.edb.Cell.Terminal.PointTerminal.Create(
                self._active_layout, pins[1].GetNet(), pins[1].GetName() + "_ref", pt, pin_layers[0]
            )
            if not neg_pin_term:  # pragma: no cover
                return False
            pos_pin_term.SetBoundaryType(self._pedb.edb.Cell.Terminal.BoundaryType.PortBoundary)
            pos_pin_term.SetIsCircuitPort(True)
            pos_pin_term.SetName(component.refdes)
            neg_pin_term.SetBoundaryType(self._pedb.edb.Cell.Terminal.BoundaryType.PortBoundary)
            neg_pin_term.SetIsCircuitPort(True)
            pos_pin_term.SetReferenceTerminal(neg_pin_term)
            self._logger.info("Component {} has been replaced by port".format(component.refdes))
            return True

    @pyaedt_function_handler()
    def _create_pin_group_terminal(self, pingroup, component=None, isref=False):
        """Creates an EDB pin group terminal from a given EDB pin group.

        Parameters
        ----------
        pingroup : Edb pin group.

        component : str or EdbComponent

        isref : bool

        Returns
        -------
        Edb pin group terminal.
        """
        if component:
            if not isinstance(component, self._edb.Cell.Hierarchy.Component):
                cmp_name = component
            else:
                cmp_name = component.GetName()
        else:
            cmp_name = pingroup.GetComponent().GetName()
        net_name = pingroup.GetNet().GetName()
        pin_name = list(pingroup.GetPins())[0].GetName()  # taking first pin name as convention.
        if cmp_name:
            term_name = "{0}.{1}.{2}".format(net_name, cmp_name, pin_name)
        else:
            term_name = "{0}.{1}".format(net_name, pin_name)
        pingroup_term = self._edb.Cell.Terminal.PinGroupTerminal.Create(
            self._active_layout, pingroup.GetNet(), term_name, pingroup, isref
        )
        return pingroup_term

    @pyaedt_function_handler()
    def _is_top_component(self, cmp):
        """Test the component placment layer.

        Parameters
        ----------
        cmp : self._edb.Cell.Hierarchy.Component
             Edb component.

        Returns
        -------
        bool
            ``True`` when component placed on top layer, ``False`` on bottom layer.


        """
        signal_layers = cmp.GetLayout().GetLayerCollection().Layers(self._edb.Cell.LayerTypeSet.SignalLayerSet)
        if cmp.GetPlacementLayer() == signal_layers[0]:
            return True
        else:
            return False

    @pyaedt_function_handler()
    def _getComponentDefinition(self, name, pins):
        componentDefinition = self._edb.Definition.ComponentDef.FindByName(self._db, name)
        if componentDefinition.IsNull():
            componentDefinition = self._edb.Definition.ComponentDef.Create(self._db, name, None)
            if componentDefinition.IsNull():
                self._logger.error("Failed to create component definition {}".format(name))
                return None
            for pin in pins:
                componentDefinitionPin = self._edb.Definition.ComponentDefPin.Create(componentDefinition, pin.GetName())
                if componentDefinitionPin.IsNull():
                    self._logger.error("Failed to create component definition pin {}-{}".format(name, pin.GetName()))
                    return None
        else:
            self._logger.warning("Found existing component definition for footprint {}".format(name))
        return componentDefinition

    @pyaedt_function_handler()
    def create_rlc_component(self, pins, component_name="", r_value=1.0, c_value=1e-9, l_value=1e-9, is_parallel=False):
        """Create physical Rlc component.

        Parameters
        ----------
        pins : list[Edb.Primitive.PadstackInstance]
             List of EDB pins, length must be 2, since only 2 pins component are currently supported.

        component_name : str
            Component name.

        r_value : float
            Resistor value.

        c_value : float
            Capacitance value.

        l_value : float
            Inductor value.

        is_parallel : bool
            Using parallel model when ``True``, series when ``False``.

        Returns
        -------
        Component
            Created EDB component.

        """
        if not len(pins) == 2:  # pragma no cover
            self._logger.error("2 Pins must be provided to create an rlc component.")
            return False
        comp_def = self._getComponentDefinition(component_name, pins)
        if not comp_def:  # pragma no cover
            self._logger.error("Failed to create component definition")
            return False
        new_cmp = self._edb.Cell.Hierarchy.Component.Create(self._active_layout, component_name, comp_def.GetName())
        hosting_component_location = pins[0].GetComponent().GetTransform()
        for pin in pins:
            new_cmp.AddMember(pin)
        new_cmp_layer_name = pins[0].GetPadstackDef().GetData().GetLayerNames()[0]
        new_cmp_placement_layer = self._edb.Cell.Layer.FindByName(
            self._active_layout.GetLayerCollection(), new_cmp_layer_name
        )
        new_cmp.SetPlacementLayer(new_cmp_placement_layer)
        rlc = self._edb.Utility.Rlc()
        rlc.IsParallel = is_parallel
        if r_value:  # pragma no cover
            rlc.REnabled = True
            rlc.R = self._get_edb_value(r_value)
        else:  # pragma no cover
            rlc.REnabled = False
        if l_value:  # pragma no cover
            rlc.LEnabled = True
            rlc.L = self._get_edb_value(l_value)
        else:  # pragma no cover
            rlc.LEnabled = False
        if c_value:  # pragma no cover
            rlc.CEnabled = True
            rlc.C = self._get_edb_value(c_value)
        else:  # pragma no cover
            rlc.CEnabled = False
        if rlc.REnabled and not rlc.CEnabled and not rlc.CEnabled:  # pragma no cover
            new_cmp.SetComponentType(self._edb.Definition.ComponentType.Resistor)
        elif rlc.CEnabled and not rlc.REnabled and not rlc.LEnabled:  # pragma no cover
            new_cmp.SetComponentType(self._edb.Definition.ComponentType.Capacitor)
        elif rlc.LEnabled and not rlc.REnabled and not rlc.CEnabled:  # pragma no cover
            new_cmp.SetComponentType(self._edb.Definition.ComponentType.Inductor)
        else:  # pragma no cover
            new_cmp.SetComponentType(self._edb.Definition.ComponentType.Resistor)

        pin_pair = self._edb.Utility.PinPair(pins[0].GetName(), pins[1].GetName())  # pragma no cover
        rlc_model = self._edb.Cell.Hierarchy.PinPairModel()
        rlc_model.SetPinPairRlc(pin_pair, rlc)
        edb_rlc_component_property = self._edb.Cell.Hierarchy.RLCComponentProperty()
        if not edb_rlc_component_property.SetModel(rlc_model) or not new_cmp.SetComponentProperty(
            edb_rlc_component_property
        ):
            return False  # pragma no cover
        new_cmp.SetTransform(hosting_component_location)
        return new_cmp

    @pyaedt_function_handler()
    def create_component_from_pins(self, pins, component_name, placement_layer=None, component_part_name=None):
        """Create a component from pins.

        Parameters
        ----------
        pins : list
            List of EDB core pins.
        component_name : str
            Name of the reference designator for the component.
        placement_layer : str, optional
            Name of the layer used for placing the component.
        component_part_name : str, optional
            Part name of the component.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------

        >>> from pyaedt import Edb
        >>> edbapp = Edb("myaedbfolder")
        >>> pins = edbapp.core_components.get_pin_from_component("A1")
        >>> edbapp.core_components.create_component_from_pins(pins, "A1New")

        """
        if component_part_name:
            compdef = self._getComponentDefinition(component_part_name, pins)
        else:
            compdef = self._getComponentDefinition(component_name, pins)
        if not compdef:
            return False
        new_cmp = self._edb.Cell.Hierarchy.Component.Create(self._active_layout, component_name, compdef.GetName())

        if isinstance(pins[0], EDBPadstackInstance):
            pins = [i._edb_padstackinstance for i in pins]
        for pin in pins:
            pin.SetIsLayoutPin(True)
            new_cmp.AddMember(pin)
        new_cmp.SetComponentType(self._edb.Definition.ComponentType.Other)
        if not placement_layer:
            new_cmp_layer_name = pins[0].GetPadstackDef().GetData().GetLayerNames()[0]
        else:
            new_cmp_layer_name = placement_layer
        new_cmp_placement_layer = self._edb.Cell.Layer.FindByName(
            self._active_layout.GetLayerCollection(), new_cmp_layer_name
        )
        new_cmp.SetPlacementLayer(new_cmp_placement_layer)
        # cmp_transform = System.Activator.CreateInstance(self._edb.Utility.)
        # new_cmp.SetTransform(cmp_transform)
        self._cmp[new_cmp.GetName()] = EDBComponent(self, new_cmp)
        return new_cmp
        # except:
        #    return (False, None)

    @pyaedt_function_handler()
    def set_component_model(self, componentname, model_type="Spice", modelpath=None, modelname=None):
        """Assign a Spice or Touchstone model to a component.

        Parameters
        ----------
        componentname : str
            Name of the component.
        model_type : str, optional
            Type of the model. Options are ``"Spice"`` and
            ``"Touchstone"``.  The default is ``"Spice"``.
        modelpath : str, optional
            Full path to the model file. The default is ``None``.
        modelname : str, optional
            Name of the model. The default is ``None``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------

        >>> from pyaedt import Edb
        >>> edbapp = Edb("myaedbfolder")
        >>> edbapp.core_components.set_component_model("A1", model_type="Spice",
        ...                                            modelpath="pathtospfile",
        ...                                            modelname="spicemodelname")

        """
        if not modelname:
            modelname = get_filename_without_extension(modelpath)
        edbComponent = self.get_component_by_name(componentname)
        if str(edbComponent.EDBHandle) == "0":
            return False
        edbRlcComponentProperty = edbComponent.GetComponentProperty().Clone()

        componentPins = self.get_pin_from_component(componentname)
        componentNets = self.get_nets_from_pin_list(componentPins)
        pinNumber = len(componentPins)
        if model_type == "Spice":
            with open(modelpath, "r") as f:
                for line in f:
                    if "subckt" in line.lower():
                        pinNames = [i.strip() for i in re.split(" |\t", line) if i]
                        pinNames.remove(pinNames[0])
                        pinNames.remove(pinNames[0])
                        break
            if len(pinNames) == pinNumber:
                spiceMod = self._edb.Cell.Hierarchy.SPICEModel()
                spiceMod.SetModelPath(modelpath)
                spiceMod.SetModelName(modelname)
                terminal = 1
                for pn in pinNames:
                    spiceMod.AddTerminalPinPair(pn, str(terminal))
                    terminal += 1

                edbRlcComponentProperty.SetModel(spiceMod)
                if not edbComponent.SetComponentProperty(edbRlcComponentProperty):
                    self._logger.error("Error assigning the `Spice` model.")
                    return False
            else:
                self._logger.error("Wrong number of Pins")
                return False

        elif model_type == "Touchstone":  # pragma: no cover

            nPortModelName = modelname
            edbComponentDef = edbComponent.GetComponentDef()
            nPortModel = self._edb.Definition.NPortComponentModel.FindByName(edbComponentDef, nPortModelName)
            if nPortModel.IsNull():
                nPortModel = self._edb.Definition.NPortComponentModel.Create(nPortModelName)
                nPortModel.SetReferenceFile(modelpath)
                edbComponentDef.AddComponentModel(nPortModel)

            sParameterMod = self._edb.Cell.Hierarchy.SParameterModel()
            sParameterMod.SetComponentModelName(nPortModelName)
            gndnets = filter(lambda x: "gnd" in x.lower(), componentNets)
            if len(list(gndnets)) > 0:  # pragma: no cover
                net = gndnets[0]
            else:  # pragma: no cover
                net = componentNets[len(componentNets) - 1]
            sParameterMod.SetReferenceNet(net)
            edbRlcComponentProperty.SetModel(sParameterMod)
            if not edbComponent.SetComponentProperty(edbRlcComponentProperty):
                self._logger.error("Error assigning the `Touchstone` model")
                return False
        return True

    @pyaedt_function_handler()
    def create_pingroup_from_pins(self, pins, group_name=None):
        """Create a pin group on a component.

        Parameters
        ----------
        pins : list
            List of EDB core pins.
        group_name : str, optional
            Name for the group. The default is ``None``, in which case
            a default name is assigned as follows: ``[component Name] [NetName]``.

        Returns
        -------
        tuple
            The tuple is structured as: (bool, pingroup).

        Examples
        --------
        >>> from pyaedt import Edb
        >>> edbapp = Edb("myaedbfolder")
        >>> edbapp.core_components.create_pingroup_from_pins(gndpinlist, "MyGNDPingroup")

        """
        if len(pins) < 1:
            self._logger.error("No pins specified for pin group %s", group_name)
            return (False, None)
        if group_name is None:
            group_name = self._edb.Cell.Hierarchy.PinGroup.GetUniqueName(self._active_layout)
        pingroup = _retry_ntimes(
            10,
            self._edb.Cell.Hierarchy.PinGroup.Create,
            self._active_layout,
            group_name,
            convert_py_list_to_net_list(pins),
        )
        if pingroup.IsNull():
            return False
        else:
            pingroup.SetNet(pins[0].GetNet())
            return pingroup

    @pyaedt_function_handler()
    def delete_single_pin_rlc(self):
        """Delete all RLC components with a single pin.

        Returns
        -------
        list
            List of deleted RLC components.


        Examples
        --------

        >>> from pyaedt import Edb
        >>> edbapp = Edb("myaedbfolder")
        >>> list_of_deleted_rlcs = edbapp.core_components.delete_single_pin_rlc()
        >>> print(list_of_deleted_rlcs)

        """
        deleted_comps = []
        for comp, val in self.components.items():
            if val.numpins < 2 and val.type in ["Resistor", "Capacitor", "Inductor"]:
                val.edbcomponent.Delete()
                deleted_comps.append(comp)
        self.refresh_components()
        self._pedb._logger.info("Deleted {} components".format(len(deleted_comps)))

        return deleted_comps

    @pyaedt_function_handler()
    def delete_component(self, component_name):
        """Delete a component.

        Parameters
        ----------
        component_name : str
            Name of the component.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------

        >>> from pyaedt import Edb
        >>> edbapp = Edb("myaedbfolder")
        >>> edbapp.core_components.delete_component("A1")

        """
        edb_cmp = self.get_component_by_name(component_name)
        if edb_cmp is not None:
            edb_cmp.Delete()
            if edb_cmp in list(self.components.keys()):
                del self.components[edb_cmp]
            return True
        return False

    @pyaedt_function_handler()
    def disable_rlc_component(self, component_name):
        """Disable a RLC component.

        Parameters
        ----------
        component_name : str
            Name of the RLC component.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------

        >>> from pyaedt import Edb
        >>> edbapp = Edb("myaedbfolder")
        >>> edbapp.core_components.disable_rlc_component("A1")

        """
        edb_cmp = self.get_component_by_name(component_name)
        if edb_cmp is not None:
            rlc_property = edb_cmp.GetComponentProperty().Clone()
            pin_pair_model = rlc_property.GetModel().Clone()
            pprlc = pin_pair_model.GetPinPairRlc(list(pin_pair_model.PinPairs)[0])
            pprlc.CEnabled = False
            pprlc.LEnabled = False
            pprlc.REnabled = False
            pin_pair_model.SetPinPairRlc(list(pin_pair_model.PinPairs)[0], pprlc)
            rlc_property.SetModel(pin_pair_model)
            edb_cmp.SetComponentProperty(rlc_property)
            return True
        return False

    @pyaedt_function_handler()
    def set_solder_ball(
        self,
        component="",
        sball_diam="100um",
        sball_height="150um",
        shape="Cylinder",
        sball_mid_diam=None,
        chip_orientation="chip_down",
    ):
        """Set cylindrical solder balls on a given component.

        Parameters
        ----------
        component_name : str or EDB component
            Name of the discrete component.
        sball_diam  : str, float, optional
            Diameter of the solder ball.
        sball_height : str, float, optional
            Height of the solder ball.
        shape : str, optional
            Shape of solder ball. Options are ``"Cylinder"``,
            ``"Spheroid"``. The default is ``"Cylinder"``.
        sball_mid_diam : str, float, optional
            Mid diameter of the solder ball.
        chip_orientation : str
            Give the chip orientation, ``"chip_down"`` or ``"chip_up"``. Default is ``"chip_down"``. Only applicable on
            IC model.
        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------

        >>> from pyaedt import Edb
        >>> edbapp = Edb("myaedbfolder")
        >>> edbapp.core_components.set_solder_ball("A1")

        """
        if not isinstance(component, self._edb.Cell.Hierarchy.Component):
            edb_cmp = self.get_component_by_name(component)
            cmp = self.components[component]
        else:
            edb_cmp = component
            cmp = self.components[edb_cmp.GetName()]
        if edb_cmp:
            cmp_type = edb_cmp.GetComponentType()
            if bool(not sball_diam + sball_height):
                pin1 = list(cmp.pins.values())[0].pin
                pin_layers = pin1.GetPadstackDef().GetData().GetLayerNames()
                pad_params = self._padstack.get_pad_parameters(pin=pin1, layername=pin_layers[0], pad_type=0)
                _sb_diam = min([self._get_edb_value(val).ToDouble() for val in pad_params[1]])
                sball_diam = _sb_diam
                sball_height = sball_diam

            if not sball_mid_diam:
                sball_mid_diam = sball_diam

            if shape == "Cylinder":
                sball_shape = self._edb.Definition.SolderballShape.Cylinder
            else:
                sball_shape = self._edb.Definition.SolderballShape.Spheroid

            cmp_property = edb_cmp.GetComponentProperty().Clone()
            if cmp_type == self._edb.Definition.ComponentType.IC:
                ic_die_prop = cmp_property.GetDieProperty().Clone()
                ic_die_prop.SetType(self._edb.Definition.DieType.FlipChip)
                if chip_orientation.lower() == "chip_down":
                    ic_die_prop.SetOrientation(self._edb.Definition.DieOrientation.ChipDown)
                if chip_orientation.lower() == "chip_up":
                    ic_die_prop.SetOrientation(self._edb.Definition.DieOrientation.ChipUp)
                else:
                    ic_die_prop.SetOrientation(self._edb.Definition.DieOrientation.ChipDown)
                cmp_property.SetDieProperty(ic_die_prop)

            solder_ball_prop = cmp_property.GetSolderBallProperty().Clone()
            solder_ball_prop.SetDiameter(self._get_edb_value(sball_diam), self._get_edb_value(sball_mid_diam))
            solder_ball_prop.SetHeight(self._get_edb_value(sball_height))

            solder_ball_prop.SetShape(sball_shape)
            cmp_property.SetSolderBallProperty(solder_ball_prop)

            port_prop = cmp_property.GetPortProperty().Clone()
            port_prop.SetReferenceSizeAuto(True)
            cmp_property.SetPortProperty(port_prop)
            edb_cmp.SetComponentProperty(cmp_property)
            return True
        else:
            return False

    @pyaedt_function_handler()
    def set_component_rlc(
        self,
        componentname,
        res_value=None,
        ind_value=None,
        cap_value=None,
        isparallel=False,
    ):
        """Update values for an RLC component.

        Parameters
        ----------
        componentname :
            Name of the RLC component.
        res_value : float, optional
            Resistance value. The default is ``None``.
        ind_value : float, optional
            Inductor value.  The default is ``None``.
        cap_value : float optional
            Capacitor value.  The default is ``None``.
        isparallel : bool, optional
            Whether the RLC component is parallel. The default is ``False``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------

        >>> from pyaedt import Edb
        >>> edbapp = Edb("myaedbfolder")
        >>> edbapp.core_components.set_component_rlc(
        ...     "R1", res_value=50, ind_value=1e-9, cap_value=1e-12, isparallel=False
        ... )

        """
        edb_component = self.get_component_by_name(componentname)
        edb_rlc_component_property = self._edb.Cell.Hierarchy.RLCComponentProperty()
        component_pins = self.get_pin_from_component(componentname)
        pin_number = len(component_pins)
        if pin_number == 2:
            from_pin = component_pins[0]
            to_pin = component_pins[1]
            rlc = self._edb.Utility.Rlc()
            rlc.IsParallel = isparallel
            if res_value is not None:
                rlc.REnabled = True
                rlc.R = self._get_edb_value(res_value)
            else:
                rlc.REnabled = False
            if ind_value is not None:
                rlc.LEnabled = True
                rlc.L = self._get_edb_value(ind_value)
            else:
                rlc.LEnabled = False
            if cap_value is not None:
                rlc.CEnabled = True
                rlc.C = self._get_edb_value(cap_value)
            else:
                rlc.CEnabled = False
            pin_pair = self._edb.Utility.PinPair(from_pin.GetName(), to_pin.GetName())
            rlc_model = self._edb.Cell.Hierarchy.PinPairModel()
            rlc_model.SetPinPairRlc(pin_pair, rlc)
            if not edb_rlc_component_property.SetModel(rlc_model) or not edb_component.SetComponentProperty(
                edb_rlc_component_property
            ):
                self._logger.error("Failed to set RLC model on component")
                return False
        else:
            self._logger.warning(
                "Component %s has not been assigned because either it is not present in the layout "
                "or it contains a number of pins not equal to 2",
                componentname,
            )
            return False
        self._logger.warning("RLC properties for Component %s has been assigned.", componentname)
        return True

    @pyaedt_function_handler()
    def update_rlc_from_bom(
        self,
        bom_file,
        delimiter=";",
        valuefield="Func des",
        comptype="Prod name",
        refdes="Pos / Place",
    ):
        """Update the EDC core component values (RLCs) with values coming from a BOM file.

        Parameters
        ----------
        bom_file : str
            Full path to the BOM file, which is a delimited text file.
            Header values needed inside the BOM reader must
            be explicitly set if different from the defaults.
        delimiter : str, optional
            Value to use for the delimiter. The default is ``";"``.
        valuefield : str, optional
            Field header containing the value of the component. The default is ``"Func des"``.
            The value for this parameter must being with the value of the component
            followed by a space and then the rest of the value. For example, ``"22pF"``.
        comptype : str, optional
            Field header containing the type of component. The default is ``"Prod name"``. For
            example, you might enter ``"Inductor"``.
        refdes : str, optional
            Field header containing the reference designator of the component. The default is
            ``"Pos / Place"``. For example, you might enter ``"C100"``.

        Returns
        -------
        bool
            ``True`` if the file contains the header and it is correctly parsed. ``True`` is
            returned even if no values are assigned.

        """
        with open(bom_file, "r") as f:
            Lines = f.readlines()
            found = False
            refdescolumn = None
            comptypecolumn = None
            valuecolumn = None
            unmount_comp_list = list(self.components.keys())
            for line in Lines:
                content_line = [i.strip() for i in line.split(delimiter)]
                if valuefield in content_line:
                    valuecolumn = content_line.index(valuefield)
                if comptype in content_line:
                    comptypecolumn = content_line.index(comptype)
                if refdes in content_line:
                    refdescolumn = content_line.index(refdes)
                elif refdescolumn:
                    found = True
                    new_refdes = content_line[refdescolumn].split(" ")[0]
                    new_value = content_line[valuecolumn].split(" ")[0]
                    new_type = content_line[comptypecolumn]
                    if "resistor" in new_type.lower():
                        self.set_component_rlc(new_refdes, res_value=new_value)
                        unmount_comp_list.remove(new_refdes)
                    elif "capacitor" in new_type.lower():
                        self.set_component_rlc(new_refdes, cap_value=new_value)
                        unmount_comp_list.remove(new_refdes)
                    elif "inductor" in new_type.lower():
                        self.set_component_rlc(new_refdes, ind_value=new_value)
                        unmount_comp_list.remove(new_refdes)
            for comp in unmount_comp_list:
                self.components[comp].is_enabled = False
        return found

    @pyaedt_function_handler()
    def import_bom(
        self,
        bom_file,
        delimiter=",",
        refdes_col=0,
        part_name_col=1,
        comp_type_col=2,
        value_col=3,
    ):
        """Load external BOM file.

        Parameters
        ----------
        bom_file : str
            Full path to the BOM file, which is a delimited text file.
        delimiter : str, optional
            Value to use for the delimiter. The default is ``","``.
        refdes_col : int, optional
            Column index of reference designator. The default is ``"0"``.
        part_name_col : int, optional
             Column index of part name. The default is ``"1"``. Set to ``None`` if
             the column does not exist.
        comp_type_col : int, optional
            Column index of component type. The default is ``"2"``.
        value_col : int, optional
            Column index of value. The default is ``"3"``. Set to ``None``
            if the column does not exist.
        Returns
        -------
        bool
        """
        with open(bom_file, "r") as f:
            lines = f.readlines()
            unmount_comp_list = list(self.components.keys())
            for l in lines[1:]:
                l = l.replace(" ", "").replace("\n", "")
                if not l:
                    continue
                l = l.split(delimiter)

                refdes = l[refdes_col]
                comp = self.components[refdes]
                if not part_name_col == None:
                    part_name = l[part_name_col]
                    if comp.partname == part_name:
                        pass
                    else:
                        pinlist = self.get_pin_from_component(refdes)
                        if not part_name in self.definitions:
                            footprint_cell = self.definitions[comp.partname]._edb_comp_def.GetFootprintCell()
                            comp_def = self._edb.Definition.ComponentDef.Create(self._db, part_name, footprint_cell)
                            for pin in pinlist:
                                self._edb.Definition.ComponentDefPin.Create(comp_def, pin.GetName())

                        p_layer = comp.placement_layer
                        refdes_temp = comp.refdes + "_temp"
                        comp.refdes = refdes_temp

                        unmount_comp_list.remove(refdes)
                        comp.edbcomponent.Ungroup(True)

                        self.create_component_from_pins(pinlist, refdes, p_layer, part_name)
                        self.refresh_components()
                        comp = self.components[refdes]

                comp_type = l[comp_type_col]
                if comp_type.capitalize() in ["Resistor", "Capacitor", "Inductor", "Other"]:
                    comp.type = comp_type.capitalize()
                else:
                    comp.type = comp_type.upper()

                if comp_type.capitalize() in ["Resistor", "Capacitor", "Inductor"] and refdes in unmount_comp_list:
                    unmount_comp_list.remove(refdes)
                if not value_col == None:
                    try:
                        value = l[value_col]
                    except:
                        value = None
                    if value:
                        if comp_type == "Resistor":
                            self.set_component_rlc(refdes, res_value=value)
                        elif comp_type == "Capacitor":
                            self.set_component_rlc(refdes, cap_value=value)
                        elif comp_type == "Inductor":
                            self.set_component_rlc(refdes, ind_value=value)
            for comp in unmount_comp_list:
                self.components[comp].is_enabled = False
        return True

    @pyaedt_function_handler()
    def export_bom(self, bom_file, delimiter=","):
        """Export Bom file from layout.

        Parameters
        ----------
        bom_file : str
            Full path to the BOM file, which is a delimited text file.
        delimiter : str, optional
            Value to use for the delimiter. The default is ``","``.
        """
        with open(bom_file, "w") as f:
            f.writelines([delimiter.join(["RefDes", "Part name", "Type", "Value\n"])])
            for refdes, comp in self.components.items():
                if not comp.is_enabled and comp.type in ["Resistor", "Capacitor", "Inductor"]:
                    continue
                part_name = comp.partname
                comp_type = comp.type
                if comp_type == "Resistor":
                    value = comp.res_value
                elif comp_type == "Capacitor":
                    value = comp.cap_value
                elif comp_type == "Inductor":
                    value = comp.ind_value
                else:
                    value = ""
                if not value:
                    value = ""
                f.writelines([delimiter.join([refdes, part_name, comp_type, value + "\n"])])
        return True

    @pyaedt_function_handler()
    def get_pin_from_component(self, component, netName=None, pinName=None):
        """Retrieve the pins of a component.

        Parameters
        ----------
        component : str or EDB component
            Name of the component or the EDB component object.
        netName : str, optional
            Filter on the net name as an alternative to
            ``pinName``. The default is ``None``.
        pinName : str, optional
            Filter on the pin name an an alternative to
            ``netName``. The default is ``None``.

        Returns
        -------
        list
            List of pins when the component is found or ``[]`` otherwise.

        Examples
        --------

        >>> from pyaedt import Edb
        >>> edbapp = Edb("myaedbfolder", "project name", "release version")
        >>> edbapp.core_components.get_pin_from_component("R1", refdes)

        """
        if not isinstance(component, self._edb.Cell.Hierarchy.Component):
            component = self._edb.Cell.Hierarchy.Component.FindByName(self._active_layout, component)
        if netName:
            if not isinstance(netName, list):
                netName = [netName]
            # pins = []
            # cmp_obj = list(cmp.LayoutObjs)
            # for p in cmp_obj:
            #    if p.GetObjType() == 1:
            #        if p.IsLayoutPin():
            #            pin_net_name = p.GetNet().GetName()
            #            if pin_net_name in netName:
            #                pins.append(p)
            pins = [
                p
                for p in list(component.LayoutObjs)
                if int(p.GetObjType()) == 1 and p.IsLayoutPin() and p.GetNet().GetName() in netName
            ]
        elif pinName:
            if not isinstance(pinName, list):
                pinName = [pinName]
            pins = [
                p
                for p in list(component.LayoutObjs)
                if int(p.GetObjType()) == 1
                and p.IsLayoutPin()
                and (self.get_aedt_pin_name(p) in pinName or p.GetName() in pinName)
            ]
        else:
            pins = [p for p in list(component.LayoutObjs) if int(p.GetObjType()) == 1 and p.IsLayoutPin()]
        return pins

    @pyaedt_function_handler()
    def get_aedt_pin_name(self, pin):
        """Retrieve the pin name that is shown in AEDT.

        .. note::
           To obtain the EDB core pin name, use `pin.GetName()`.

        Parameters
        ----------
        pin : str
            Name of the pin in EDB core.

        Returns
        -------
        str
            Name of the pin in AEDT.

        Examples
        --------

        >>> from pyaedt import Edb
        >>> edbapp = Edb("myaedbfolder", "project name", "release version")
        >>> edbapp.core_components.get_aedt_pin_name(pin)

        """
        if isinstance(pin, EDBPadstackInstance):
            pin = pin._edb_padstackinstance
        if is_ironpython:
            name = _clr.Reference[String]()
            pin.GetProductProperty(self._edb.ProductId.Designer, 11, name)
        else:
            val = String("")
            _, name = pin.GetProductProperty(self._edb.ProductId.Designer, 11, val)
        name = str(name).strip("'")
        return name

    @pyaedt_function_handler()
    def get_pin_position(self, pin):
        """Retrieve the pin position in meters.

        Parameters
        ----------
        pin : str
            Name of the pin.

        Returns
        -------
        list
            Pin position as a list of float values in the form ``[x, y]``.

        Examples
        --------

        >>> from pyaedt import Edb
        >>> edbapp = Edb("myaedbfolder", "project name", "release version")
        >>> edbapp.core_components.get_pin_position(pin)

        """
        res, pt_pos, rot_pos = pin.GetPositionAndRotation()

        if pin.GetComponent().IsNull():
            transformed_pt_pos = pt_pos
        else:
            transformed_pt_pos = pin.GetComponent().GetTransform().TransformPoint(pt_pos)
        pin_xy = self._edb.Geometry.PointData(
            self._get_edb_value(str(transformed_pt_pos.X.ToDouble())),
            self._get_edb_value(str(transformed_pt_pos.Y.ToDouble())),
        )
        return [pin_xy.X.ToDouble(), pin_xy.Y.ToDouble()]

    @pyaedt_function_handler()
    def get_pins_name_from_net(self, pin_list, net_name):
        """Retrieve pins belonging to a net.

        Parameters
        ----------
        pin_list : list
            List of pins to check.
        net_name : str
            Name of the net.

        Returns
        -------
        list
            List of pins belong to the net.

        Examples
        --------

        >>> from pyaedt import Edb
        >>> edbapp = Edb("myaedbfolder", "project name", "release version")
        >>> edbapp.core_components.get_pins_name_from_net(pin_list, net_name)

        """
        pinlist = []
        for pin in pin_list:
            if pin.GetNet().GetName() == net_name:
                pinlist.append(pin.GetName())
        return pinlist

    @pyaedt_function_handler()
    def get_nets_from_pin_list(self, PinList):
        """Retrieve nets with one or more pins.

        Parameters
        ----------
        PinList : list
            List of pins.

        Returns
        -------
        list
            List of nets with one or more pins.

        Examples
        --------

        >>> from pyaedt import Edb
        >>> edbapp = Edb("myaedbfolder", "project name", "release version")
        >>> edbapp.core_components.get_nets_from_pin_list(pinlist)

        """
        netlist = []
        for pin in PinList:
            netlist.append(pin.GetNet().GetName())
        return list(set(netlist))

    @pyaedt_function_handler()
    def get_component_net_connection_info(self, refdes):
        """Retrieve net connection information.

        Parameters
        ----------
        refdes :
            Reference designator for the net.

        Returns
        -------
        dict
            Dictionary of the net connection information for the reference designator.

        Examples
        --------

        >>> from pyaedt import Edb
        >>> edbapp = Edb("myaedbfolder", "project name", "release version")
        >>> edbapp.core_components.get_component_net_connection_info(refdes)

        """
        component_pins = self.get_pin_from_component(refdes)
        data = {"refdes": [], "pin_name": [], "net_name": []}
        for pin_obj in component_pins:
            pin_name = pin_obj.GetName()
            net_name = pin_obj.GetNet().GetName()
            if pin_name is not None:
                data["refdes"].append(refdes)
                data["pin_name"].append(pin_name)
                data["net_name"].append(net_name)
        return data

    def get_rats(self):
        """Retrieve a list of dictionaries of the reference designator, pin names, and net names.

        Returns
        -------
        list
            List of dictionaries of the reference designator, pin names,
            and net names.

        Examples
        --------

        >>> from pyaedt import Edb
        >>> edbapp = Edb("myaedbfolder", "project name", "release version")
        >>> edbapp.core_components.get_rats()

        """
        df_list = []
        for refdes in self.components.keys():
            df = self.get_component_net_connection_info(refdes)
            df_list.append(df)
        return df_list

    def get_through_resistor_list(self, threshold=1):
        """Retrieve through resistors.

        Parameters
        ----------
        threshold : int, optional
            Threshold value. The default is ``1``.

        Returns
        -------
        list
            List of through resistors.

        Examples
        --------

        >>> from pyaedt import Edb
        >>> edbapp = Edb("myaedbfolder", "project name", "release version")
        >>> edbapp.core_components.get_through_resistor_list()

        """
        through_comp_list = []
        for refdes, comp_obj in self.resistors.items():

            numpins = comp_obj.numpins

            if numpins == 2:

                value = comp_obj.res_value
                value = resistor_value_parser(value)

                if value <= threshold:
                    through_comp_list.append(refdes)

        return through_comp_list

    @pyaedt_function_handler()
    def short_component_pins(self, component_name, pins_to_short=None, width=1e-3):
        """Short pins of component with a trace.

        Parameters
        ----------
        component_name : str
            Name of the component.
        pins_to_short : list, optional
            List of pins to short. If `None`, all pins will be shorted.
        width : float, optional
            Short Trace width. It will be used in trace computation algorithm

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------

        >>> from pyaedt import Edb
        >>> edbapp = Edb("myaedbfolder")
        >>> edbapp.core_components.short_component_pins("J4A2", ["G4", "9", "3"])

        """
        component = self.components[component_name]
        pins = component.pins
        pins_list = []

        component.center
        for pin_name, pin in pins.items():
            if pins_to_short:
                if pin_name in pins_to_short:
                    pins_list.append(pin)
            else:
                pins_list.append(pin)
        positions_to_short = []
        center = component.center
        c = [center[0], center[1], 0]
        delta_pins = []
        w = width
        for pin in pins_list:
            placement_layer = pin.placement_layer
            positions_to_short.append(pin.position)
            if placement_layer in self._pedb.core_padstack.padstacks[pin.pin.GetPadstackDef().GetName()].pad_by_layer:
                pad = self._pedb.core_padstack.padstacks[pin.pin.GetPadstackDef().GetName()].pad_by_layer[
                    placement_layer
                ]
            else:
                layer = list(
                    self._pedb.core_padstack.padstacks[pin.pin.GetPadstackDef().GetName()].pad_by_layer.keys()
                )[0]
                pad = self._pedb.core_padstack.padstacks[pin.pin.GetPadstackDef().GetName()].pad_by_layer[layer]
            pars = pad.parameters_values
            geom = pad.geometry_type
            if geom < 6 and pars:
                delta_pins.append(max(pars) + min(pars) / 2)
                w = min(min(pars), w)
            elif pars:
                delta_pins.append(1.5 * pars[0])
                w = min(pars[0], w)
            elif pad.polygon_data:
                bbox = pad.polygon_data.GetBBox()
                lower = [bbox.Item1.X.ToDouble(), bbox.Item1.Y.ToDouble()]
                upper = [bbox.Item2.X.ToDouble(), bbox.Item2.Y.ToDouble()]
                pars = [abs(lower[0] - upper[0]), abs(lower[1] - upper[1])]
                delta_pins.append(max(pars) + min(pars) / 2)
                w = min(min(pars), w)
            else:
                delta_pins.append(1.5 * width)
        i = 0

        while i < len(positions_to_short) - 1:
            p0 = []
            p0.append([positions_to_short[i][0] - delta_pins[i], positions_to_short[i][1], 0])
            p0.append([positions_to_short[i][0] + delta_pins[i], positions_to_short[i][1], 0])
            p0.append([positions_to_short[i][0], positions_to_short[i][1] - delta_pins[i], 0])
            p0.append([positions_to_short[i][0], positions_to_short[i][1] + delta_pins[i], 0])
            p0.append([positions_to_short[i][0], positions_to_short[i][1], 0])
            l0 = [
                GeometryOperators.points_distance(p0[0], c),
                GeometryOperators.points_distance(p0[1], c),
                GeometryOperators.points_distance(p0[2], c),
                GeometryOperators.points_distance(p0[3], c),
                GeometryOperators.points_distance(p0[4], c),
            ]
            l0_min = l0.index(min(l0))
            p1 = []
            p1.append(
                [
                    positions_to_short[i + 1][0] - delta_pins[i + 1],
                    positions_to_short[i + 1][1],
                    0,
                ]
            )
            p1.append(
                [
                    positions_to_short[i + 1][0] + delta_pins[i + 1],
                    positions_to_short[i + 1][1],
                    0,
                ]
            )
            p1.append(
                [
                    positions_to_short[i + 1][0],
                    positions_to_short[i + 1][1] - delta_pins[i + 1],
                    0,
                ]
            )
            p1.append(
                [
                    positions_to_short[i + 1][0],
                    positions_to_short[i + 1][1] + delta_pins[i + 1],
                    0,
                ]
            )
            p1.append([positions_to_short[i + 1][0], positions_to_short[i + 1][1], 0])

            l1 = [
                GeometryOperators.points_distance(p1[0], c),
                GeometryOperators.points_distance(p1[1], c),
                GeometryOperators.points_distance(p1[2], c),
                GeometryOperators.points_distance(p1[3], c),
                GeometryOperators.points_distance(p1[4], c),
            ]
            l1_min = l1.index(min(l1))

            trace_points = [positions_to_short[i]]

            trace_points.append(p0[l0_min][:2])
            trace_points.append(c[:2])
            trace_points.append(p1[l1_min][:2])

            trace_points.append(positions_to_short[i + 1])

            self._pedb.core_primitives.create_trace(
                trace_points,
                layer_name=placement_layer,
                net_name="short",
                width=w,
                start_cap_style="Flat",
                end_cap_style="Flat",
            )
            i += 1
        return True
