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

from collections import defaultdict
import warnings

from ansys.aedt.core.emit_core import emit_constants as emit_consts
import ansys.aedt.core.generic.constants as consts
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler


class EmitComponents(object):
    """EmitComponents class.

    This is the class for managing all EMIT components.
    """

    @property
    def oeditor(self):
        """Oeditor Module."""
        return self.modeler.oeditor

    @property
    def odesign(self):
        """Odesign module."""
        return self._parent.odesign

    @property
    def messenger(self):
        """Messenger."""
        return self._parent._messenger

    @property
    def version(self):
        """Version."""
        return self._parent._aedt_version

    @property
    def model_units(self):
        """Model units."""
        return self.modeler.model_units

    @property
    def omodel_manager(self):
        """AEDT model manager."""
        return self.modeler.o_model_manager

    @property
    def o_model_manager(self):
        """AEDT model manager.

        .. deprecated:: 0.15.0
           Use :func:`omodel_manager` method instead.

        """
        warnings.warn(
            "`o_model_manager` is deprecated. Use `omodel_manager` instead.",
            DeprecationWarning,
        )
        return self.omodel_manager

    @property
    def o_definition_manager(self):
        """Aedt Definition Manager.

        References
        ----------
        >>> oDefinitionManager = oProject.GetDefinitionManager()
        """
        return self._parent._oproject.GetDefinitionManager()

    @property
    def osymbol_manager(self):
        """AEDT Symbol Manager.

        References
        ----------
        >>> oSymbolManager = oDefinitionManager.GetManager("Symbol")
        """
        return self._parent.osymbol_manager

    @property
    def o_symbol_manager(self):
        """AEDT Symbol Manager.

        .. deprecated:: 0.15.0
           Use :func:`osymbol_manager` method instead.

        References
        ----------
        >>> oSymbolManager = oDefinitionManager.GetManager("Symbol")
        """
        warnings.warn(
            "`o_symbol_manager` is deprecated. Use `osymbol_manager` instead.",
            DeprecationWarning,
        )
        return self.osymbol_manager

    @property
    def ocomponent_manager(self):
        """AEDT Component Manager.

        References
        ----------
        >>> oComponentManager = oDefinitionManager.GetManager("Component")
        """

        return self._parent.ocomponent_manager

    @property
    def o_component_manager(self):
        """AEDT Component Manager.

        .. deprecated:: 0.15.0
           Use :func:`ocomponent_manager` method instead.

        References
        ----------
        >>> oComponentManager = oDefinitionManager.GetManager("Component")
        """
        warnings.warn(
            "`o_component_manager` is deprecated. Use `ocomponent_manager` instead.",
            DeprecationWarning,
        )
        return self.ocomponent_manager

    @property
    def design_type(self):
        """Design type."""
        return self._parent.design_type

    @pyaedt_function_handler()
    def __getitem__(self, compname):
        """Get a component by its name.

        Parameters
        ----------
        compname : str
           Name of the component.

        Returns
        -------
        EmitComponent
            The Component or ``None`` if a component with the given name is not
            found.
        """
        if compname in self.components:
            return self.components[compname]

        return None

    def __len__(self):
        return len(self.components)

    def __iter__(self):
        return self.components.keys().__iter__()

    def __init__(self, parent, modeler):
        self._parent = parent
        self.modeler = modeler
        self._currentId = 0
        self.components = defaultdict(EmitComponent)
        self.refresh_all_ids()

    @pyaedt_function_handler()
    def create_component(self, component_type, name=None, library=None):
        """Create a new component from a library.

        Parameters
        ----------
        component_type : str
            Type of component to create. For example, "Antenna".
        name : str, optional
            Name to assign to the new component. If ``None``, then an instance
            name is assigned automatically. The default is ``None.``
        library : str, optional
            Name of the component library. If ``None``, the syslib is used. The
            default is ``None``.

        Returns
        -------
        EmitComponent
            The newly created component.

        References
        ----------
        >>> oEditor.CreateComponent
        """
        # Pass an empty string to allow name to be automatically assigned.
        if name is None:
            name = ""
        # Pass an empty string to use syslib EMIT library.
        if library is None:
            library = ""
        new_comp_name = self.oeditor.CreateComponent(name, component_type, library)
        o = EmitComponent.create(self, new_comp_name)
        o.name = new_comp_name
        o_update = self.update_object_properties(o)
        self.components[new_comp_name] = o_update
        return o_update

    @pyaedt_function_handler()
    def create_radio_antenna(self, radio_type, radio_name=None, antenna_name=None, library=None):
        """Create a new radio and antenna and connect them.

        Parameters
        ----------
        radio_type : str
            Type of radio to create. For example, "Bluetooth". Must match
            a radio name in the specified library.
        radio_name : str, optional
            Name to assign to the new radio. If ``None``, then an instance
            name is assigned automatically. The default is ``None.``
        antenna_name : str, optional
            Name to assign to the new antenna. If ``None``, then an instance
            name is assigned automatically. The default is ``None.``
        library : str, optional
            Name of the component library. If ``None``, the syslib is used. The
            default is ``None``.

        Returns
        -------
        EmitComponent
            The newly created radio.
        EmitComponent
            The newly created antenna.

        References
        ----------
        >>> oEditor.CreateComponent
        """
        # Pass an empty string to allow name to be automatically assigned.
        if radio_name is None:
            radio_name = ""
        if antenna_name is None:
            antenna_name = ""
        # Pass an empty string to use syslib EMIT library.
        if library is None:
            library = ""
        # Create the radio.
        new_radio_name = self.oeditor.CreateComponent(radio_name, radio_type, library)
        rad = EmitComponent.create(self, new_radio_name)
        rad.name = new_radio_name
        rad_update = self.update_object_properties(rad)
        self.components[new_radio_name] = rad_update
        # Create the antenna.
        new_ant_name = self.oeditor.CreateComponent(antenna_name, "Antenna", library)
        ant = EmitComponent.create(self, new_ant_name)
        ant.name = new_ant_name
        ant_update = self.update_object_properties(ant)
        self.components[new_ant_name] = ant_update
        # Connect the radio and antenna.
        if rad_update and ant_update:
            ant_update.move_and_connect_to(rad_update)
        return rad_update, ant_update

    @pyaedt_function_handler()
    def get_radios(self):
        """Get all radios in the design.

        Returns
        -------
        Dict : radio_name : EmitRadioComponents
            Dict of all the radio_name and EmitRadioComponents in the
            design.
        """
        return {k: v for k, v in self.components.items() if v.get_type() == "RadioNode"}

    @pyaedt_function_handler()
    def get_antennas(self):
        """Get all antennas in the design.

        Returns
        -------
        Dict : antenna_name : EmitAntennaComponents
            Dict of all the antenna_name and EmitAntennaComponents in the
            design.
        """
        return {k: v for k, v in self.components.items() if v.get_type() == "AntennaNode"}

    @pyaedt_function_handler()
    def refresh_all_ids(self):
        """Refresh all IDs and return the number of components."""
        all_comps = self.oeditor.GetAllComponents()
        for comp_name in all_comps:
            if not self.get_obj_id(comp_name):
                o = EmitComponent.create(self, comp_name)
                o_update = self.update_object_properties(o)
                self.components[comp_name] = o_update
        return len(self.components)

    @pyaedt_function_handler()
    def get_obj_id(self, object_name):
        """Get object ID.

        Parameters
        ----------
        object_name : str
            Name of the object.

        Returns
        -------
        EmitComponent
            The component when successful, None when failed.

        """
        for el in self.components:
            if self.components[el].name == object_name:
                return el
        return None

    @pyaedt_function_handler()
    def update_object_properties(self, o):
        """Update the properties of an EMIT component.

        Parameters
        ----------
        o :
            Object (component) to update.

        Returns
        -------
        type
            Object with properties.
        """
        o.update_property_tree()
        comp_type = o.root_prop_node.props["Type"]
        o._add_property("Type", comp_type)
        return o


class EmitComponent(object):
    """A component in the EMIT schematic."""

    # Dictionary of subclass types. Register each subclass types with
    # class decorator and use EmitComponent.create to create the correct
    # object type.
    subclasses = {}

    @classmethod
    def register_subclass(cls, root_node_type):
        def decorator(subclass):
            cls.subclasses[root_node_type] = subclass
            return subclass

        return decorator

    @classmethod
    def create(cls, components, component_name):
        """Create an EMIT component.

        Parameters
        ----------
        components : list
            List of components in the design.
        component_name : str
            Name of the component.

        Returns
        -------
        EmitComponent
            An instance of the new component.
        """
        nodes = components.odesign.GetComponentNodeNames(component_name)
        root_node = nodes[0]
        prop_list = components.odesign.GetComponentNodeProperties(component_name, root_node)
        props = dict(p.split("=", 1) for p in prop_list)
        root_node_type = props["Type"]
        if root_node_type.endswith("Node"):
            root_node_type = root_node_type[: -len("Node")]
        if root_node_type not in cls.subclasses:
            return EmitComponent(components, component_name)
        return cls.subclasses[root_node_type](components, component_name)

    def __init__(self, components, component_name):
        self.name = component_name
        """Name of the component."""

        self.components = components
        """List of components in the design."""

        self.oeditor = components.oeditor
        """Oeditor module."""

        self.odesign = components.odesign
        """Odesign module."""

        self.root_prop_node = None
        """Root node of the component."""

        self.units = components._parent.get_units()
        """Units for the component."""

    @property
    def composed_name(self):
        """Component name. Needed for compatibility."""
        return self.name

    @pyaedt_function_handler()
    def move_and_connect_to(self, component):
        """Move and connect this component to another component.

        Parameters
        ----------
        component : EmitComponent or str
            The component or name of component to move this component to
            and connect. For example, "Radio1"

        """
        if isinstance(component, EmitComponent):
            self.oeditor.PlaceComponent(self.name, component.name)
        else:
            self.oeditor.PlaceComponent(self.name, component)

    @pyaedt_function_handler()
    def port_names(self):
        """Get the names of the component's ports.

        Returns
        -------
        List
            List of port names.

        References
        ----------
        >>> oEditor.GetComponentPorts
        """
        return self.oeditor.GetComponentPorts(self.name)

    @pyaedt_function_handler()
    def port_connection(self, port_name):
        """Get the name component and port connected to the given port.

        Parameters
        ----------
        port_name : str
            The name of the port to interrogate for connection information.

        Returns
        -------
        str
            Connected component name. Returns None if no connection at given
            port.
        str
            Port name on connected component. Returns None if no connection
            at given port.

        References
        ----------
        >>> oEditor.GetWireAtPort
        >>> oEditor.GetWireConnections
        """
        wire_name = self.oeditor.GetWireAtPort(self.name, port_name)
        wire_connections = self.oeditor.GetWireConnections(wire_name)
        # One end of the wire will be this component. The other end will be
        # the other component. Return component and port names for the other
        # end.
        for wc_comp_name, wc_port_name in wire_connections:
            if wc_comp_name != self.name:
                return wc_comp_name, wc_port_name
        return None, None

    @pyaedt_function_handler()
    def update_property_tree(self):
        """Update the nodes (property groups) for this component.

        Returns
        -------
        EmitComponentPropNode
            The root node of the updated property tree.

        References
        ----------
        >>> oDesign.GetComponentNodeNames
        """
        node_names = sorted(self.odesign.GetComponentNodeNames(self.name))
        root_node_name = node_names[0]
        nodes = {}
        for node_name in node_names:
            new_node = EmitComponentPropNode(self.oeditor, self.odesign, self, node_name)
            parent_name = node_name.rpartition("-*-")[0]
            if parent_name in nodes:
                parent_node = nodes[parent_name]
                parent_node.children.append(new_node)
                new_node.parent = parent_node
            nodes[node_name] = new_node
        self.root_prop_node = nodes[root_node_name]
        return self.root_prop_node

    @pyaedt_function_handler()
    def get_node_properties(self, node=None):
        """Return the properties of the given node (property group).

        Parameters
        ----------
        node : str
            The name of the node (property group) whose properties will
            be returned. If node is None, the root node properties will be
            returned. (Default value = None)

        Returns
        -------
        dict
            Dictionary of property names (keys) and property values.

        References
        ----------
        >>> oDesign.GetComponentNodeNames
        >>> oDesign.GetComponentNodeProperties
        """
        nodes = sorted(self.odesign.GetComponentNodeNames(self.name))
        root_node = nodes[0]
        node_name = root_node
        if node is not None:
            node_name = root_node + "-*-" + "-*-".join(node.split("/")[1:])
        props_list = self.odesign.GetComponentNodeProperties(self.name, node_name)
        props = dict(p.split("=", 1) for p in props_list)
        return props

    @pyaedt_function_handler()
    def _add_property(self, property_name, property_value):
        """Add a property or update existing property value.

        Parameters
        ----------
        property_name : str
            Name of property.
        property_value : str
            Value to assign to property.


        Returns
        -------
        True.
        """
        self.__dict__[property_name] = property_value
        return True

    def get_prop_nodes(self, property_filter=None):
        """Get all property nodes that match a set of key,value pairs.

        Parameters
        ----------
        property_filter : dict, optional
        Only return nodes with all the property name, value pairs of this dict.
            Defaults to ``None`` which returns all nodes.

        Returns
        -------
        List
            List of all matching nodes (EmitComponentPropNode).
        """
        if property_filter is None:
            property_filter = {}

        filtered_nodes = []
        nodes_to_expand = [self.root_prop_node]
        while nodes_to_expand:
            node = nodes_to_expand.pop()
            nodes_to_expand.extend(node.children)
            # <= checks if subset; {} is subset of all dicts
            if property_filter.items() <= node.props.items():
                filtered_nodes.append(node)
        return filtered_nodes

    @pyaedt_function_handler()
    def get_connected_components(self):
        """Get all EMIT components that are connected (directly or indirectly) to this component.

        Parameters
        ----------
        None

        Returns
        -------
        List
            List containing all EMIT components that are connected to this component.
        """
        component_names = []
        to_search = [self.name]
        while to_search:
            cursor = self.components[to_search.pop()]
            ports = cursor.port_names()

            for port in ports:
                connection_name, _ = cursor.port_connection(port)
                if connection_name not in component_names and connection_name not in to_search:
                    to_search.append(connection_name)

            component_names.append(cursor.name)

        components = map(lambda component_name: self.components[component_name], component_names)
        return list(components)

    @pyaedt_function_handler()
    def get_type(self):
        """Get the property ``Type`` of a component.

        Parameters
        ----------
        None

        Returns
        -------
        str
            Type property of self.
        """
        properties = self.get_node_properties()

        return properties["Type"]


@EmitComponent.register_subclass("Antenna")
class EmitAntennaComponent(EmitComponent):
    """An Antenna component in the EMIT schematic."""

    def __init__(self, components, component_name):
        super(EmitAntennaComponent, self).__init__(components, component_name)

    def get_pattern_filename(self):
        """Get the filename of the antenna pattern defining this antenna.

        Parameters
        ----------
        None

        Returns
        -------
        Str
            Filename of the antenna pattern.
        """
        properties = self.get_node_properties()
        return properties["Filename"]

    def get_orientation_rpy(self):
        """Get the RPY orientation of this antenna.

        Parameters
        ----------
        None

        Returns
        -------
            Tuple containing the roll, pitch, and yaw values in degrees defining this orientation.
        """
        properties = self.get_node_properties()

        orientation_string = properties["Orientation"]
        orientation_type = properties["OrientationMode"]

        if orientation_string is None or orientation_type is None:
            return None

        if orientation_type != "rpyDeg":
            # Handle other orientations by fixing up `orientation_string`.
            print("Unhandled orientation type: " + orientation_type)
            return None

        # Build a tuple of the orientation values.
        parts = orientation_string.split()
        orientation = (float(parts[0]), float(parts[1]), float(parts[2]))

        return orientation

    def get_position(self, units=""):
        """Get the position of this antenna.

        Parameters
        ----------
        units : str, optional
            Units of the antenna position. If None specified, units are meters.

        Returns
        -------
        Tuple containing the X, Y, and Z offset values in specified units.

        """
        properties = self.get_node_properties()
        position_string = properties["Position"]

        if position_string is None:
            return None

        # Build a tuple of the position
        parts = position_string.split()

        # Check the units specified are a valid EMIT length
        if not units or units not in emit_consts.EMIT_VALID_UNITS["Length"]:
            units = self.units["Length"]
        position = (
            consts.unit_converter(float(parts[0]), "Length", "meter", units),
            consts.unit_converter(float(parts[1]), "Length", "meter", units),
            consts.unit_converter(float(parts[2]), "Length", "meter", units),
        )

        return position


@EmitComponent.register_subclass("Radio")
class EmitRadioComponent(EmitComponent):
    """A Radio component in the EMIT schematic."""

    def __init__(self, components, component_name):
        super(EmitRadioComponent, self).__init__(components, component_name)

    def is_emitter(self):
        """Check if the radio component is an emitter

        Parameters
        ----------
        None

        Return
        ------
        Bool
            ``True`` if it is an emitter, ``False`` otherwise.
        """
        properties = self.get_node_properties()

        if "IsEmitter" in properties:
            return properties["IsEmitter"]
        return False

    def bands(self):
        """Get the bands of this radio.

        Parameters
        ----------
        None

        Returns
        -------
        List
            List of the band nodes in the radio."""
        band_nodes = self.get_prop_nodes({"Type": "Band"})
        return band_nodes

    def band_node(self, band_name):
        """Get the specified band node from this radio.

        Parameters
        ----------
        band_name : name of the desired band node.

        Returns
        -------
        band_node : Instance of the band node."""
        band_nodes = self.bands()
        for node in band_nodes:
            if band_name == node.props["Name"]:
                return node
        return None

    def band_start_frequency(self, band_node, units=""):
        """Get the start frequency of the band node.

        Parameters
        ----------
        band_node : Instance of the band node.
        units : str, optional
            If ``None`` specified, global units are used.

        Returns
        -------
        Float
            Start frequency of the band node."""
        if not units or units not in emit_consts.EMIT_VALID_UNITS["Frequency"]:
            units = self.units["Frequency"]
        return consts.unit_converter(float(band_node.props["StartFrequency"]), "Freq", "Hz", units)

    def band_stop_frequency(self, band_node, units=""):
        """Get the stop frequency of the band node.

        Parameters
        ----------
        band_node : Instance of the band node.
        units : str, optional
            If ``None`` specified, global units are used.

        Returns
        -------
        Float
            Stop frequency of the band node."""
        if not units or units not in emit_consts.EMIT_VALID_UNITS["Frequency"]:
            units = self.units["Frequency"]
        return consts.unit_converter(float(band_node.props["StopFrequency"]), "Freq", "Hz", units)

    def set_band_start_frequency(self, band_node, band_start_freq, units=""):
        """Set start frequency of the band.

        Parameters
        ----------
        band_node : ansys.aedt.core.modeler.circuits.primitives_emit.EmitComponentPropNode object
            Instance of the band node
        band_start_freq : float
            Start frequency of the band.
        units : str, optional
            Units of the start frequency. If no units are specified or the units
            specified are invalid, then `"Hz"`` is assumed.

        Returns
        ------
        None

        Examples
        --------
        >>> from ansys.aedt.core import Emit
        >>> aedtapp = Emit(new_desktop=False)
        >>> radio = aedtapp.modeler.components.create_component("New Radio")
        >>> band =  radio.bands()[0]
        >>> start_freq = 10
        >>> units = 'MHz'
        >>> radio.set_band_start_frequency(band, start_freq, units=units)
        """

        # if "Band" not in band_node.props["Type"]:
        #     raise TypeError("{} must be a band.".format(band_node.node_name))

        if not units or units not in emit_consts.EMIT_VALID_UNITS["Frequency"]:
            units = "Hz"

        # convert to Hz
        freq_float_in_Hz = consts.unit_converter(band_start_freq, "Freq", units, "Hz")
        freq_string = f"{freq_float_in_Hz}"
        if not (1 <= freq_float_in_Hz <= 100000000000):  # pragma: no cover
            raise ValueError("Frequency should be within 1Hz to 100 GHz.")
        if float(band_node.props["StopFrequency"]) < freq_float_in_Hz:  # pragma: no cover
            stop_freq = freq_float_in_Hz + 1
            band_node._set_prop_value({"StopFrequency": str(stop_freq)})
        else:
            prop_list = {"StartFrequency": freq_string}
            band_node._set_prop_value(prop_list)

    def set_band_stop_frequency(self, band_node, band_stop_freq, units=""):
        """Set stop frequency of the band.

        Parameters
        ----------
        band_node : ansys.aedt.core.modeler.circuits.primitives_emit.EmitComponentPropNode object
            Instance of the band node
        band_stop_freq : float
            Stop frequency of the band.
        units : str, optional
            Units of the stop frequency. If no units are specified or the units
            specified are invalid, then `"Hz"`` is assumed.

        Returns
        ------
        None

        Examples
        --------
        >>> from ansys.aedt.core import Emit
        >>> aedtapp = Emit(new_desktop=False)
        >>> radio = aedtapp.modeler.components.create_component("New Radio")
        >>> band =  radio.bands()[0]
        >>> stop_freq = 10
        >>> units = 'MHz'
        >>> radio.set_band_stop_frequency(band, stop_freq, units=units)
        """
        # if "Band" not in band_node.props["Type"]:
        #     raise TypeError("{} must be a band.".format(band_node.node_name))
        if not units or units not in emit_consts.EMIT_VALID_UNITS["Frequency"]:
            units = "Hz"
        # convert to Hz
        freq_float_in_Hz = consts.unit_converter(band_stop_freq, "Freq", units, "Hz")
        if not (1 <= freq_float_in_Hz <= 100000000000):  # pragma: no cover
            raise ValueError("Frequency should be within 1Hz to 100 GHz.")
        if float(band_node.props["StartFrequency"]) > freq_float_in_Hz:  # pragma: no cover
            if freq_float_in_Hz > 1:
                band_node._set_prop_value({"StartFrequency": str(freq_float_in_Hz - 1)})
            else:  # pragma: no cover
                raise ValueError("Band stop frequency is less than start frequency.")
        freq_string = f"{freq_float_in_Hz}"
        prop_list = {"StopFrequency": freq_string}
        band_node._set_prop_value(prop_list)

    # def duplicate_band(self, band_node_to_duplicate):
    #     """
    #     [Incomplete 10/19/2023]
    #     Parameters
    #     ----------
    #     band_node_to_duplicate
    #
    #     Returns
    #     -------
    #
    #     """
    #     # append number to the name of the band to duplicate.
    #     print('Duplicating...')
    #
    #
    #     # return band node
    # def convert_channels_to_multi_bands(self, band_node):
    #     """
    #     [Incomplete 10/19/2023]
    #     Parameters
    #     ----------
    #     band_node
    #
    #     Returns
    #     -------
    #
    #     """
    #     # get the channels. Say returns 10 channels in the band_node
    #     # Name = r.bands()[0].children[0].props['Name']
    #     # band_node.props['Name']
    #     # Start = r.bands()[0].props['StartFrequency']
    #     band_start_frequency = float(band_node.props['StartFrequency'])
    #     # Stop = r.bands()[0].props['StopFrequency']
    #     band_stop_frequency = float(band_node.props['StopFrequency'])
    #     # Spacing = r.bands()[0].props['ChannelSpacing']
    #     channel_spacing = float(band_node.props['ChannelSpacing'])
    #     # for each channel
    #     # 1) create a band (duplicate original one)
    #     # 2) set band start and stop frequencies
    #     for channel in list(range(int(band_start_frequency), int(band_stop_frequency), int(channel_spacing))):
    #         baby_band_start = channel
    #         baby_band_stop = channel+channel_spacing
    #         baby_band_node = self.duplicate_band(band_node) # return band name or some handle to it
    #         self.set_band_start_frequency(baby_band_node, baby_band_start)
    #         self.set_band_stop_frequency(baby_band_node, baby_band_stop)
    #         # set start and stop freq for that band name
    #     # to be

    def band_channel_bandwidth(self, band_node, units=""):
        """Get the channel bandwidth of the band node.

        Parameters
        ----------
        band_node : Instance of the band node.
        units : str, optional
            If ``None`` specified, global units are used.

        Returns
        -------
        Float
            Channel bandwidth of the band node."""
        if not units or units not in emit_consts.EMIT_VALID_UNITS["Frequency"]:
            units = self.units["Frequency"]
        return consts.unit_converter(float(band_node.props["ChannelBandwidth"]), "Freq", "Hz", units)

    def band_tx_power(self, band_node, units=""):
        """Get the transmit power of the band node.

        Parameters
        ----------
        band_node : Instance of the band node.
        units : str
            Units to use for the tx power.

        Returns
        -------
        Float
            Transmit power of the band node."""
        if not units or units not in emit_consts.EMIT_VALID_UNITS["Power"]:
            units = self.units["Power"]
        for child in band_node.children:
            if child.props["Type"] == "TxSpectralProfNode":
                return consts.unit_converter(float(child.props["FundamentalAmplitude"]), "Power", "dBm", units)

    def has_tx_channels(self):
        """Check the radio for enabled transmit channels.

        Parameters
        ----------
        None

        Returns
        -------
        Bool
            ``True`` if the radio has enabled transmit channels and
            ``False`` if there are no enabled transmit channels."""
        nodes = self.get_prop_nodes({"Type": "TxSpectralProfNode", "Enabled": "true"})
        return len(nodes) > 0

    def has_rx_channels(self):
        """Check the radio for enabled receive channels.

        Parameters
        ----------
        None

        Returns
        -------
        Bool
            ''True'' if the radio has enabled receive channels and
            ''False'' if there are no enabled receive channels."""
        nodes = self.get_prop_nodes({"Type": "RxSusceptibilityProfNode", "Enabled": "true"})
        return len(nodes) > 0

    def get_connected_antennas(self):
        """Return a list of antennas connected to this radio instance.

        Parameters
        ----------
        None

        Returns
        -------
        List
            List of antennas connected to this radio."""
        components = super().get_connected_components()
        antennas = filter(lambda component: component.get_node_properties()["Type"] == "AntennaNode", components)
        return list(antennas)

    def get_sampling(self):
        """Returns the sampling for the radio.

        Parameters
        ----------
        None

        Return
        ------
        EmitComponentPropNode
            Sampling node for the radio.
        """
        samp_node = self.get_prop_nodes({"Type": "SamplingNode"})
        return samp_node[0]


class EmitComponentPropNode(object):
    def __init__(self, editor, design, parent_component, node_name):
        self.oeditor = editor
        """Oeditor module"""

        self.odesign = design
        """Odesign module"""

        self.parent_component = parent_component
        """Parent component of this node."""

        self.node_name = node_name
        """Full node name of this node."""

        self.node_name_as_list = node_name.split("-*-")
        """List of nodes for this instance."""

        self.children = []
        """List of children for this node instance."""

        self.parent = None
        """Initial parent of this node instance."""

    @property
    def props(self):
        """Returns a dictionary of all the properties for this node.

        Parameters
        ----------
        None

        Returns
        -------
        Dict
            Dictionary of all the properties for this node."""
        prop_list = self.odesign.GetComponentNodeProperties(self.parent_component.name, self.node_name)
        props = dict(p.split("=", 1) for p in prop_list)
        return props

    @property
    def enabled(self):
        """Returns ''True'' if the node is enabled and ''False'' if the node is disabled.

        Parameters
        ----------
        None

        Returns
        -------
        Bool
            Returns ``True`` if the node is enabled and
            ``False`` if the node is disabled."""
        return self.props["Enabled"] == "true"

    @pyaedt_function_handler()
    def set_band_power_level(self, power, units=""):
        """Set the power of the fundamental for the given band.

        Parameters
        ----------
        power : float
            Peak amplitude of the fundamental [dBm].
        units : str, optional
            Units of the input power. If None specified, global units are used.

        Return
        ------
        None
        """
        if "Band" not in self.props["Type"]:
            raise TypeError(f"{self.node_name} must be a band.")
        # Need to store power in dBm
        if not units or units not in emit_consts.EMIT_VALID_UNITS["Power"]:
            units = self.parent_component.units["Power"]
        power_string = f'{consts.unit_converter(power, "Power", units, "dBm")}'
        prop_list = {"FundamentalAmplitude": power_string}
        for child in self.children:
            if child.props["Type"] == "TxSpectralProfNode":
                child._set_prop_value(prop_list)
                return  # only one Tx Spectral Profile per Band

    @pyaedt_function_handler()
    def get_band_power_level(self, units=""):
        """Get the power of the fundamental for the given band.

        Parameters
        ----------
        units : str, optional
            Units to use for the power. If None specified, global units are used.

        Return
        ------
        Float
            Peak amplitude of the fundamental [units].
        """
        if "Band" not in self.props["Type"]:
            raise TypeError(f"{self.node_name} must be a band.")
        # Power is stored in dBm, convert to desired units
        if not units or units not in emit_consts.EMIT_VALID_UNITS["Power"]:
            units = self.parent_component.units["Power"]
        for child in self.children:
            if child.props["Type"] == "TxSpectralProfNode":
                power = child.props["FundamentalAmplitude"]
                break  # only one Tx Spectral Profile per Band

        return consts.unit_converter(float(power), "Power", "dBm", units)

    @pyaedt_function_handler()
    def set_channel_sampling(self, sampling_type="Uniform", percentage=None, max_channels=None, seed=None):
        """Set the channel sampling for the radio.

        If a percentage is specified, then it will be used instead of max_channels.

        Parameters
        ----------
        sampling_type : str, optional
            Type of sampling to use: Uniform, Random, or All.
        percentage : float, optional
            Percentage of channels to sample for the analysis.
        max_channels : float, optional
            Maximum number of channels to sample for the analysis.
        seed : float, optional
            Seed used for the random channel generator. Applies to
            random sampling only.

        Returns
        -------
        None
        """
        if "SamplingNode" not in self.props["Type"]:
            raise TypeError(f"{self.node_name} must be a sampling node.")
        sampling_type = sampling_type.lower()
        if sampling_type == "all":
            sampling_type = "SampleAllChannels"
        elif sampling_type == "random":
            sampling_type = "RandomSampling"
        else:
            sampling_type = "UniformSampling"
        sampling_props = {"SamplingType": f"{sampling_type}"}
        if percentage is not None:
            sampling_props["SpecifyPercentage"] = "true"
            sampling_props["PercentageChannels"] = f"{percentage}"
        elif max_channels is not None:
            sampling_props["SpecifyPercentage"] = "false"
            sampling_props["NumberChannels"] = f"{max_channels}"
        else:
            # If nothing specified for max_channels or percentage, use default
            sampling_props["SpecifyPercentage"] = "false"
            sampling_props["NumberChannels"] = "1000"
        if seed is not None:
            sampling_props["RandomSeed"] = f"{seed}"
        self._set_prop_value(sampling_props)

    @pyaedt_function_handler()
    def _set_prop_value(self, props=None):
        """Set the property values for this node.

        Parameters
        ----------
        props : dict
            Sets the property values for this node to the
            values specified in the dictionary.

        Returns
        -------
        None
        """
        if props is None:
            props = {}
        comp_name = self.parent_component.name
        prop_list = ["NAME:properties"]
        for prop_name, value in props.items():
            prop_list.append(f"{prop_name}:=")
            if not isinstance(value, str):
                raise TypeError(f"Value for key {prop_name} is not a string.")
            prop_list.append(value)
        properties_to_set = [
            ["NAME:node", "fullname:=", self.node_name, prop_list],
            [],  # Property does not get set without this empty list
        ]
        nodes_to_delete = []  # No nodes to delete
        self.odesign.EditComponentNodes(comp_name, properties_to_set, nodes_to_delete)

    @enabled.setter
    def enabled(self, value):
        """Set the node enabled or disabled.

        Parameters
        ----------
        value : bool
            If ''True'' sets the node enabled and if
            ''False'' sets the node disabled.

        Returns
        -------
        None
        """
        str_value = "true" if value else "false"
        self._set_prop_value({"Enabled": str_value})
