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
from abc import abstractmethod
import copy

from ansys.aedt.core.generic.general_methods import generate_unique_name
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.generic.numbers import decompose_variable_value
from ansys.aedt.core.modules.boundary.common import BoundaryObject


class BoundaryDictionary:
    """Handles Icepak transient and temperature-dependent boundary condition assignments.

    Parameters
    ----------
    assignment_type : str
        Type of assignment represented by the class. Options are `"Temp Dep"``
        and ``"Transient"``.
    function_type : str
        Variation function to assign. If ``assignment_type=="Temp Dep"``,
        the function can only be ``"Piecewise Linear"``. Otherwise, the function can be
        ``"Exponential"``, ``"Linear"``, ``"Piecewise Linear"``, ``"Power Law"``,
        ``"Sinusoidal"``, and ``"Square Wave"``.
    """

    def __init__(self, assignment_type, function_type):
        if assignment_type not in ["Temp Dep", "Transient"]:  # pragma : no cover
            raise AttributeError(f"The argument {assignment_type} for ``assignment_type`` is not valid.")
        if assignment_type == "Temp Dep" and function_type != "Piecewise Linear":  # pragma : no cover
            raise AttributeError(
                "Temperature dependent assignments only support"
                ' ``"Piecewise Linear"`` as ``function_type`` argument.'
            )
        self.assignment_type = assignment_type
        self.function_type = function_type

    @property
    def props(self):
        """Dictionary that defines all the boundary condition properties."""
        return {
            "Type": self.assignment_type,
            "Function": self.function_type,
            "Values": self._parse_value(),
        }

    @abstractmethod
    def _parse_value(self):
        pass  # pragma : no cover

    @pyaedt_function_handler()
    def __getitem__(self, k):
        return self.props.get(k)


class LinearDictionary(BoundaryDictionary):
    """Manages linear conditions assignments, which are children of the ``BoundaryDictionary`` class.

    This class applies a condition ``y`` dependent on the time ``t``:
        ``y=a+b*t``

    Parameters
    ----------
    intercept : str
        Value of the assignment condition at the initial time, which
        corresponds to the coefficient ``a`` in the formula.
    slope : str
        Slope of the assignment condition, which
        corresponds to the coefficient ``b`` in the formula.
    """

    def __init__(self, intercept, slope):
        super().__init__("Transient", "Linear")
        self.intercept = intercept
        self.slope = slope

    @pyaedt_function_handler()
    def _parse_value(self):
        return [self.slope, self.intercept]


class PowerLawDictionary(BoundaryDictionary):
    """Manages power law condition assignments, which are children of the ``BoundaryDictionary`` class.

    This class applies a condition ``y`` dependent on the time ``t``:
         ``y=a+b*t^c``

     Parameters
     ----------
     intercept : str
         Value of the assignment condition at the initial time, which
         corresponds to the coefficient ``a`` in the formula.
     coefficient : str
         Coefficient that multiplies the power term, which
         corresponds to the coefficient ``b`` in the formula.
     scaling_exponent : str
         Exponent of the power term, which
         corresponds to the coefficient ``c`` in the formula.
    """

    def __init__(self, intercept, coefficient, scaling_exponent):
        super().__init__("Transient", "Power Law")
        self.intercept = intercept
        self.coefficient = coefficient
        self.scaling_exponent = scaling_exponent

    @pyaedt_function_handler()
    def _parse_value(self):
        return [self.intercept, self.coefficient, self.scaling_exponent]


class ExponentialDictionary(BoundaryDictionary):
    """Manages exponential condition assignments, which are children of the ``BoundaryDictionary`` class.

    This class applies a condition ``y`` dependent on the time ``t``:
        ``y=a+b*exp(c*t)``

    Parameters
    ----------
    vertical_offset : str
        Vertical offset summed to the exponential law, which
        corresponds to the coefficient ``a`` in the formula.
    coefficient : str
        Coefficient that multiplies the exponential term, which
        corresponds to the coefficient ``b`` in the formula.
    exponent_coefficient : str
        Coefficient in the exponential term, which
        corresponds to the coefficient ``c`` in the formula.
    """

    def __init__(self, vertical_offset, coefficient, exponent_coefficient):
        super().__init__("Transient", "Exponential")
        self.vertical_offset = vertical_offset
        self.coefficient = coefficient
        self.exponent_coefficient = exponent_coefficient

    @pyaedt_function_handler()
    def _parse_value(self):
        return [self.vertical_offset, self.coefficient, self.exponent_coefficient]


class SinusoidalDictionary(BoundaryDictionary):
    """Manages sinusoidal condition assignments, which are children of the ``BoundaryDictionary`` class.

    This class applies a condition ``y`` dependent on the time ``t``:
        ``y=a+b*sin(2*pi(t-t0)/T)``

    Parameters
    ----------
    vertical_offset : str
        Vertical offset summed to the sinusoidal law, which
        corresponds to the coefficient ``a`` in the formula.
    vertical_scaling : str
        Coefficient that multiplies the sinusoidal term, which
        corresponds to the coefficient ``b`` in the formula.
    period : str
        Period of the sinusoid, which
        corresponds to the coefficient ``T`` in the formula.
    period_offset : str
        Offset of the sinusoid, which
        corresponds to the coefficient ``t0`` in the formula.
    """

    def __init__(self, vertical_offset, vertical_scaling, period, period_offset):
        super().__init__("Transient", "Sinusoidal")
        self.vertical_offset = vertical_offset
        self.vertical_scaling = vertical_scaling
        self.period = period
        self.period_offset = period_offset

    @pyaedt_function_handler()
    def _parse_value(self):
        return [self.vertical_offset, self.vertical_scaling, self.period, self.period_offset]


class SquareWaveDictionary(BoundaryDictionary):
    """Manages square wave condition assignments, which are children of the ``BoundaryDictionary`` class.

    Parameters
    ----------
    on_value : str
        Maximum value of the square wave.
    initial_time_off : str
        Time after which the square wave assignment starts.
    on_time : str
        Time for which the square wave keeps the maximum value during one period.
    off_time : str
        Time for which the square wave keeps the minimum value during one period.
    off_value : str
        Minimum value of the square wave.
    """

    def __init__(self, on_value, initial_time_off, on_time, off_time, off_value):
        super().__init__("Transient", "Square Wave")
        self.on_value = on_value
        self.initial_time_off = initial_time_off
        self.on_time = on_time
        self.off_time = off_time
        self.off_value = off_value

    @pyaedt_function_handler()
    def _parse_value(self):
        return [self.on_value, self.initial_time_off, self.on_time, self.off_time, self.off_value]


class PieceWiseLinearDictionary(BoundaryDictionary):
    """
    Manages dataset condition assignments, which are children of the ``BoundaryDictionary`` class.

    Parameters
    ----------
    assignment_type : str
        Type of assignment represented by the class.
        Options are ``"Temp Dep"`` and ``"Transient"``.
    ds : str
        Dataset name to assign.
    scale : str
        Scaling factor for the y values of the dataset.
    """

    def __init__(self, assignment_type, ds, scale):
        super().__init__(assignment_type, "Piecewise Linear")
        self.scale = scale
        self._assignment_type = assignment_type
        self.dataset = ds

    @pyaedt_function_handler()
    def _parse_value(self):
        return [self.scale, self.dataset.name]

    @property
    def dataset_name(self):
        """Dataset name that defines the piecewise assignment."""
        return self.dataset.name


class NetworkObject(BoundaryObject):
    """Manages networks in Icepak projects."""

    def __init__(self, app, name=None, props=None, create=False):
        if not app.design_type == "Icepak":  # pragma: no cover
            raise NotImplementedError("Networks object works only with Icepak projects ")
        if name is None:
            self._name = generate_unique_name("Network")
        else:
            self._name = name
        super(NetworkObject, self).__init__(app, self._name, props, "Network", False)

        self._nodes = []
        self._links = []
        self._schematic_data = {}
        self._update_from_props()
        if create:
            self.create()

    def _clean_list(self, arg):
        new_list = []
        for item in arg:
            if isinstance(item, list):
                if item[0] == "NAME:PageNet":
                    page_net_list = []
                    for i in item:
                        if isinstance(i, list):
                            name = page_net_list[-1]
                            page_net_list.pop(-1)
                            for j in i:
                                page_net_list.append(name)
                                page_net_list.append(j)
                        else:
                            page_net_list.append(i)
                    new_list.append(page_net_list)
                else:
                    new_list.append(self._clean_list(item))
            else:
                new_list.append(item)
        return new_list

    @pyaedt_function_handler()
    def create(self):
        """
        Create network in AEDT.

        Returns
        -------
        bool:
            True if successful.
        """
        if not self.props.get("Faces", None):
            self.props["Faces"] = [node.props["FaceID"] for _, node in self.face_nodes.items()]
        if not self.props.get("SchematicData", None):
            self.props["SchematicData"] = {}

        if self.props.get("Links", None):
            self.props["Links"] = {link_name: link_values.props for link_name, link_values in self.links.items()}
        else:  # pragma : no cover
            raise KeyError("Links information is missing.")
        if self.props.get("Nodes", None):
            self.props["Nodes"] = {node_name: node_values.props for node_name, node_values in self.nodes.items()}
        else:  # pragma : no cover
            raise KeyError("Nodes information is missing.")

        args = self._get_args()

        clean_args = self._clean_list(args)
        self._app.oboundary.AssignNetworkBoundary(clean_args)
        return True

    @pyaedt_function_handler()
    def _update_from_props(self):
        nodes = self.props.get("Nodes", None)
        if nodes is not None:
            nd_name_list = [node.name for node in self._nodes]
            for node_name, node_dict in nodes.items():
                if node_name not in nd_name_list:
                    nd_type = node_dict.get("NodeType", None)
                    if nd_type == "InternalNode":
                        self.add_internal_node(
                            node_name,
                            node_dict.get("Power", node_dict.get("Power Variation Data", None)),
                            mass=node_dict.get("Mass", None),
                            specific_heat=node_dict.get("SpecificHeat", None),
                        )
                    elif nd_type == "BoundaryNode":
                        self.add_boundary_node(
                            node_name,
                            assignment_type=node_dict["ValueType"].replace("Value", ""),
                            value=node_dict[node_dict["ValueType"].replace("Value", "")],
                        )
                    else:
                        if (
                            node_dict["ThermalResistance"] == "NoResistance"
                            or node_dict["ThermalResistance"] == "Specified"
                        ):
                            node_material, node_thickness = None, None
                            node_resistance = node_dict["Resistance"]
                        else:
                            node_thickness, node_material = node_dict["Thickness"], node_dict["Material"]
                            node_resistance = None
                        self.add_face_node(
                            node_dict["FaceID"],
                            name=node_name,
                            thermal_resistance=node_dict["ThermalResistance"],
                            material=node_material,
                            thickness=node_thickness,
                            resistance=node_resistance,
                        )
        links = self.props.get("Links", None)
        if links is not None:
            l_name_list = [l.name for l in self._links]
            for link_name, link_dict in links.items():
                if link_name not in l_name_list:
                    self.add_link(link_dict[0], link_dict[1], link_dict[-1], link_name)

    @property
    def auto_update(self):
        """
        Get if auto-update is enabled.

        Returns
        -------
        bool:
            Whether auto-update is enabled.
        """
        return False

    @auto_update.setter
    def auto_update(self, b):
        """
        Set auto-update on or off.

        Parameters
        ----------
        b : bool
            Whether to enable auto-update.

        """
        if b:
            self._app.logger.warning(
                "Network objects auto_update property is False by default" " and cannot be set to True."
            )

    @property
    def links(self):
        """
        Get links of the network.

        Returns
        -------
        dict:
            Links dictionary.

        """
        self._update_from_props()
        return {link.name: link for link in self._links}

    @property
    def r_links(self):
        """
        Get r-links of the network.

        Returns
        -------
        dict:
            R-links dictionary.

        """
        self._update_from_props()
        return {link.name: link for link in self._links if link._link_type[0] == "R-Link"}

    @property
    def c_links(self):
        """
        Get c-links of the network.

        Returns
        -------
        dict:
            C-links dictionary.

        """
        self._update_from_props()
        return {link.name: link for link in self._links if link._link_type[0] == "C-Link"}

    @property
    def nodes(self):
        """
        Get nodes of the network.

        Returns
        -------
        dict:
            Nodes dictionary.

        """
        self._update_from_props()
        return {node.name: node for node in self._nodes}

    @property
    def face_nodes(self):
        """
        Get face nodes of the network.

        Returns
        -------
        dict:
            Face nodes dictionary.

        """
        self._update_from_props()
        return {node.name: node for node in self._nodes if node.node_type == "FaceNode"}

    @property
    def faces_ids_in_network(self):
        """
        Get ID of faces included in the network.

        Returns
        -------
        list:
            Face IDs.

        """
        out_arr = []
        for _, node_dict in self.face_nodes.items():
            out_arr.append(node_dict.props["FaceID"])
        return out_arr

    @property
    def objects_in_network(self):
        """
        Get objects included in the network.

        Returns
        -------
        list:
            Objects names.

        """
        out_arr = []
        for face_id in self.faces_ids_in_network:
            out_arr.append(self._app.oeditor.GetObjectNameByFaceID(face_id))
        return out_arr

    @property
    def internal_nodes(self):
        """
        Get internal nodes.

        Returns
        -------
        dict:
            Internal nodes.

        """
        self._update_from_props()
        return {node.name: node for node in self._nodes if node.node_type == "InternalNode"}

    @property
    def boundary_nodes(self):
        """
        Get boundary nodes.

        Returns
        -------
        dict:
            Boundary nodes.

        """
        self._update_from_props()
        return {node.name: node for node in self._nodes if node.node_type == "BoundaryNode"}

    @property
    def name(self):
        """
        Get network name.

        Returns
        -------
        str
            Network name.
        """
        return self._name

    @name.setter
    def name(self, new_network_name):
        """
        Set new name of the network.

        Parameters
        ----------
        new_network_name : str
            New name of the network.
        """
        bound_names = [b.name for b in self._app.boundaries]
        if self.name in bound_names:
            if new_network_name not in bound_names:
                if new_network_name != self._name:
                    self._app._oboundary.RenameBoundary(self._name, new_network_name)
                    self._name = new_network_name
            else:
                self._app.logger.warning("Name %s already assigned in the design", new_network_name)
        else:
            self._name = new_network_name

    @pyaedt_function_handler()
    def add_internal_node(self, name, power, mass=None, specific_heat=None):
        """Add an internal node to the network.

        Parameters
        ----------
        name : str
            Name of the node.
        power : str or float or dict
            String, float, or dictionary containing the value of the assignment.
            If a float is passed, the ``"W"`` unit is used. A dictionary can be
            passed to use temperature-dependent or transient
            assignments.
        mass : str or float, optional
            Value of the mass assignment. This parameter is relevant only
            if the solution is transient. If a float is passed, the ``"Kg"`` unit
            is used. The default is ``None``, in which case ``"0.001kg"`` is used.
        specific_heat : str or float, optional
            Value of the specific heat assignment. This parameter is
            relevant only if the solution is transient. If a float is passed,
            the ``"J_per_Kelkg"`` unit is used. The default is ``None`, in
            which case ``"1000J_per_Kelkg"`` is used.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------
        >>> import ansys.aedt.core
        >>> app = ansys.aedt.core.Icepak()
        >>> network = ansys.aedt.core.modules.boundary.Network(app)
        >>> network.add_internal_node("TestNode", {"Type": "Transient",
        >>>                                        "Function": "Linear", "Values": ["0.01W", "1"]})
        """
        if self._app.solution_type != "SteadyState" and mass is None and specific_heat is None:
            self._app.logger.warning("The solution is transient but neither mass nor specific heat is assigned.")
        if self._app.solution_type == "SteadyState" and (
            mass is not None or specific_heat is not None
        ):  # pragma: no cover
            self._app.logger.warning(
                "Because the solution is steady state, neither mass nor specific heat assignment is relevant."
            )
        if isinstance(power, (int, float)):
            power = str(power) + "W"
        props_dict = {"Power": power}
        if mass is not None:
            if isinstance(mass, (int, float)):
                mass = str(mass) + "kg"
            props_dict.update({"Mass": mass})
        if specific_heat is not None:
            if isinstance(specific_heat, (int, float)):
                specific_heat = str(specific_heat) + "J_per_Kelkg"
            props_dict.update({"SpecificHeat": specific_heat})
        new_node = self._Node(name, self._app, node_type="InternalNode", props=props_dict, network=self)
        self._nodes.append(new_node)
        self._add_to_props(new_node)
        return new_node

    @pyaedt_function_handler()
    def add_boundary_node(self, name, assignment_type, value):
        """
        Add a boundary node to the network.

        Parameters
        ----------
        name : str
            Name of the node.
        assignment_type : str
            Type assignment. Options are ``"Power"`` and ``"Temperature"``.
        value : str or float or dict
            String, float, or dictionary containing the value of the assignment.
            If a float is passed the ``"W"`` or ``"cel"`` unit is used, depending on
            the selection for the ``assignment_type`` parameter. If ``"Power"``
            is selected for the type, a dictionary can be passed to use
            temperature-dependent or transient assignment.

        Returns
        -------
        bool
            ``True`` if successful.

        Examples
        --------
        >>> import ansys.aedt.core
        >>> app = ansys.aedt.core.Icepak()
        >>> network = ansys.aedt.core.modules.boundary.Network(app)
        >>> network.add_boundary_node("TestNode", "Temperature", 2)
        >>> ds = app.create_dataset1d_design("Test_DataSet",[1, 2, 3],[3, 4, 5])
        >>> network.add_boundary_node("TestNode", "Power", {"Type": "Temp Dep",
        >>>                                                       "Function": "Piecewise Linear",
        >>>                                                       "Values": "Test_DataSet"})
        """
        if assignment_type not in ["Power", "Temperature", "PowerValue", "TemperatureValue"]:  # pragma: no cover
            raise AttributeError('``type`` can be only ``"Power"`` or ``"Temperature"``.')
        if isinstance(value, (float, int)):
            if assignment_type == "Power" or assignment_type == "PowerValue":
                value = str(value) + "W"
            else:
                value = str(value) + "cel"
        if isinstance(value, dict) and (
            assignment_type == "Temperature" or assignment_type == "TemperatureValue"
        ):  # pragma: no cover
            raise AttributeError(
                "Temperature-dependent or transient assignment is not supported in a temperature boundary node."
            )
        if not assignment_type.endswith("Value"):
            assignment_type += "Value"
        new_node = self._Node(
            name,
            self._app,
            node_type="BoundaryNode",
            props={"ValueType": assignment_type, assignment_type.removesuffix("Value"): value},
            network=self,
        )
        self._nodes.append(new_node)
        self._add_to_props(new_node)
        return new_node

    @pyaedt_function_handler()
    def _add_to_props(self, new_node, type_dict="Nodes"):
        try:
            self.props[type_dict].update({new_node.name: new_node.props})
        except KeyError:
            self.props[type_dict] = {new_node.name: new_node.props}

    @pyaedt_function_handler(face_id="assignment")
    def add_face_node(
        self, assignment, name=None, thermal_resistance="NoResistance", material=None, thickness=None, resistance=None
    ):
        """
        Create a face node in the network.

        Parameters
        ----------
        assignment : int
            Face ID.
        name : str, optional
            Name of the node. Default is ``None``.
        thermal_resistance : str
            Thermal resistance value and unit. Default is ``"NoResistance"``.
        material : str, optional
            Material specification (required if ``thermal_resistance="Compute"``).
            Default is ``None``.
        thickness : str or float, optional
            Thickness value and unit (required if ``thermal_resistance="Compute"``).
            If a float is passed, ``"mm"`` unit is automatically used. Default is ``None``.
        resistance : str or float, optional
            Resistance value and unit (required if ``thermal_resistance="Specified"``).
            If a float is passed, ``"cel_per_w"`` unit is automatically used. Default is ``None``.

        Returns
        -------
        bool
            True if successful.

        Examples
        --------
        >>> import ansys.aedt.core
        >>> app = ansys.aedt.core.Icepak()
        >>> network = ansys.aedt.core.modules.boundary.Network(app)
        >>> box = app.modeler.create_box([5, 5, 5],[20, 50, 80])
        >>> faces_ids = [face.id for face in box.faces]
        >>> network.add_face_node(faces_ids[0])
        >>> network.add_face_node(faces_ids[1],name="TestNode",thermal_resistance="Compute",
        ...                       material="Al-Extruded",thickness="2mm")
        >>> network.add_face_node(faces_ids[2],name="TestNode",thermal_resistance="Specified",resistance=2)
        """
        props_dict = {}
        props_dict["FaceID"] = assignment
        if thermal_resistance is not None:
            if thermal_resistance == "Compute":
                if resistance is not None:
                    self._app.logger.info(
                        '``resistance`` assignment is incompatible with ``thermal_resistance="Compute"``'
                        "and it is ignored."
                    )
                if material is not None or thickness is not None:
                    props_dict["ThermalResistance"] = thermal_resistance
                    props_dict["Material"] = material
                    if not isinstance(thickness, str):
                        thickness = str(thickness) + "mm"
                    props_dict["Thickness"] = thickness
                else:  # pragma: no cover
                    raise AttributeError(
                        'If ``thermal_resistance="Compute"`` both ``material`` and ``thickness``'
                        "arguments must be prescribed."
                    )
            if thermal_resistance == "Specified":
                if material is not None or thickness is not None:
                    self._app.logger.warning(
                        "Because ``material`` and ``thickness`` assignments are incompatible with"
                        '``thermal_resistance="Specified"``, they are ignored.'
                    )
                if resistance is not None:
                    props_dict["ThermalResistance"] = thermal_resistance
                    if not isinstance(resistance, str):
                        resistance = str(resistance) + "cel_per_w"
                    props_dict["Resistance"] = resistance
                else:  # pragma : no cover
                    raise AttributeError(
                        'If ``thermal_resistance="Specified"``, ``resistance`` argument must be prescribed.'
                    )

        if name is None:
            name = "FaceID" + str(assignment)
        new_node = self._Node(name, self._app, node_type="FaceNode", props=props_dict, network=self)
        self._nodes.append(new_node)
        self._add_to_props(new_node)
        return new_node

    @pyaedt_function_handler(nodes_dict="nodes")
    def add_nodes_from_dictionaries(self, nodes):
        """
        Add nodes to the network from dictionary.

        Parameters
        ----------
        nodes : list or dict
            A dictionary or list of dictionaries containing nodes to add to the network. Different
            node types require different key and value pairs:

            - Face nodes must contain the ``"ID"`` key associated with an integer containing the face ID.
              Optional keys and values pairs are:

              - ``"ThermalResistance"``: a string specifying the type of thermal resistance.
                 Options are ``"NoResistance"`` (default), ``"Compute"``, and ``"Specified"``.
              - ``"Thickness"``: a string with the thickness value and unit (required if ``"Compute"``
              is selected for ``"ThermalResistance"``).
              - ``"Material"``: a string with the name of the material (required if ``"Compute"`` is
              selected for ``"ThermalResistance"``).
              - ``"Resistance"``: a string with the resistance value and unit (required if
                 ``"Specified"`` is selected for ``"ThermalResistance"``).
              - ``"Name"``: a string with the name of the node. If not
                 specified, a name is generated automatically.


            - Internal nodes must contain the following keys and values pairs:

              - ``"Name"``: a string with the node name
              - ``"Power"``: a string with the assigned power or a dictionary for transient or
              temperature-dependent assignment
              Optional keys and values pairs:
              - ``"Mass"``: a string with the mass value and unit
              - ``"SpecificHeat"``: a string with the specific heat value and unit

            - Boundary nodes must contain the following keys and values pairs:

              - ``"Name"``: a string with the node name
              - ``"ValueType"``: a string specifying the type of value (``"Power"`` or
              ``"Temperature"``)
              Depending on the ``"ValueType"`` choice, one of the following keys and values pairs must
              be used:
              - ``"Power"``: a string with the power value and unit or a dictionary for transient or
              temperature-dependent assignment
              - ``"Temperature"``: a string with the temperature value and unit or a dictionary for
              transient or temperature-dependent assignment
              According to the ``"ValueType"`` choice, ``"Power"`` or ``"Temperature"`` key must be
              used. Their associated value a string with the value and unit of the quantity prescribed or
              a dictionary for transient or temperature dependent assignment.


            All the temperature dependent or thermal dictionaries should contain three keys:
            ``"Type"``, ``"Function"``, and ``"Values"``. Accepted ``"Type"`` values are:
            ``"Temp Dep"`` and ``"Transient"``. Accepted ``"Function"`` are: ``"Linear"``,
            ``"Power Law"``, ``"Exponential"``, ``"Sinusoidal"``, ``"Square Wave"``, and
            ``"Piecewise Linear"``. ``"Temp Dep"`` only support the latter. ``"Values"``
            contains a list of strings containing the parameters required by the ``"Function"``
            selection (e.g. ``"Linear"`` requires two parameters: the value of the variable at t=0
            and the slope of the line). The parameters required by each ``Function`` option is in
            Icepak documentation. The parameters must contain the units where needed.

        Returns
        -------
        bool
            ``True`` if successful. ``False`` otherwise.

        Examples
        --------
        >>> import ansys.aedt.core
        >>> app = ansys.aedt.core.Icepak()
        >>> network = ansys.aedt.core.modules.boundary.Network(app)
        >>> box = app.modeler.create_box([5, 5, 5],[20, 50, 80])
        >>> faces_ids = [face.id for face in box.faces]
        >>> nodes_dict = [
        >>>         {"FaceID": faces_ids[0]},
        >>>         {"Name": "TestNode", "FaceID": faces_ids[1],
        >>>          "ThermalResistance": "Compute", "Thickness": "2mm"},
        >>>         {"FaceID": faces_ids[2], "ThermalResistance": "Specified", "Resistance": "2cel_per_w"},
        >>>         {"Name": "Junction", "Power": "1W"}]
        >>> network.add_nodes_from_dictionaries(nodes_dict)
        """
        if isinstance(nodes, dict):
            nodes = [nodes]
        for node_dict in nodes:
            if "FaceID" in node_dict.keys():
                self.add_face_node(
                    assignment=node_dict["FaceID"],
                    name=node_dict.get("Name", None),
                    thermal_resistance=node_dict.get("ThermalResistance", None),
                    material=node_dict.get("Material", None),
                    thickness=node_dict.get("Thickness", None),
                    resistance=node_dict.get("Resistance", None),
                )
            elif "ValueType" in node_dict.keys():
                if node_dict["ValueType"].endswith("Value"):
                    value = node_dict[node_dict["ValueType"].removesuffix("Value")]
                else:
                    value = node_dict[node_dict["ValueType"]]
                self.add_boundary_node(name=node_dict["Name"], assignment_type=node_dict["ValueType"], value=value)
            else:
                self.add_internal_node(
                    name=node_dict["Name"],
                    power=node_dict.get("Power", None),
                    mass=node_dict.get("Mass", None),
                    specific_heat=node_dict.get("SpecificHeat", None),
                )
        return True

    @pyaedt_function_handler()
    def add_link(self, node1, node2, value, name=None):
        """Create links in the network object.

        Parameters
        ----------
        node1 : str or int
            String containing one of the node names that the link is connecting or an integer
            containing the ID of the face. If an ID is used and the node associated with the
            corresponding face is not created yet, it is added automatically.
        node2 : str or int
            String containing one of the node names that the link is connecting or an integer
            containing the ID of the face. If an ID is used and the node associated with the
            corresponding face is not created yet, it is added atuomatically.
        value : str or float
            String containing the value and unit of the connection. If a float is passed, an
            R-Link is added to the network and the ``"cel_per_w"`` unit is used.
        name : str, optional
            Name of the link. The default is ``None``, in which case a name is
            automatically generated.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------
        >>> import ansys.aedt.core
        >>> app = ansys.aedt.core.Icepak()
        >>> network = ansys.aedt.core.modules.boundary.Network(app)
        >>> box = app.modeler.create_box([5, 5, 5],[20, 50, 80])
        >>> faces_ids = [face.id for face in box.faces]
        >>> connection = {"Name": "LinkTest", "Connection": [faces_ids[1], faces_ids[0]], "Value": "1cel_per_w"}
        >>> network.add_links_from_dictionaries(connection)
        """
        if name is None:
            new_name = True
            while new_name:
                name = generate_unique_name("Link")
                if name not in self.links.keys():
                    new_name = False
        new_link = self._Link(node1, node2, value, name, self)
        self._links.append(new_link)
        self._add_to_props(new_link, "Links")
        return True

    @pyaedt_function_handler()
    def add_links_from_dictionaries(self, connections):
        """Create links in the network object.

        Parameters
        ----------
        connections : dict or list of dict
            Dictionary or list of dictionaries containing the links between nodes. Each dictionary
            consists of these elements:

            - ``"Link"``: a three-item list consisting of the two nodes that the link is connecting and
               the value with unit of the link. The node of the connection can be referred to with the
               name (str) or face ID (int). The link type (resistance, heat transfer coefficient, or
               mass flow) is determined automatically from the unit.
            - ``"Name"`` (optional): a string specifying the name of the link.


        Returns
        -------
        bool
            ``True`` if successful.

        Examples
        --------
        >>> import ansys.aedt.core
        >>> app = ansys.aedt.core.Icepak()
        >>> network = ansys.aedt.core.modules.boundary.Network(app)
        >>> box = app.modeler.create_box([5, 5, 5],[20, 50, 80])
        >>> faces_ids = [face.id for face in box.faces]
        >>> [network.add_face_node(faces_ids[i]) for i in range(2)]
        >>> connection = {"Name": "LinkTest", "Link": [faces_ids[1], faces_ids[0], "1cel_per_w"]}
        >>> network.add_links_from_dictionaries(connection)
        """
        if isinstance(connections, dict):
            connections = [connections]
        for connection in connections:
            name = connection.get("Name", None)
            try:
                self.add_link(connection["Link"][0], connection["Link"][1], connection["Link"][2], name)
            except Exception:  # pragma : no cover
                if name:
                    self._app.logger.error("Failed to add " + name + " link.")
                else:
                    self._app.logger.error(
                        "Failed to add link associated with the following dictionary:\n" + str(connection)
                    )
        return True

    @pyaedt_function_handler()
    def update(self):
        """Update the network in AEDT.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        if self.name in [b.name for b in self._app.boundaries]:
            self.delete()
            try:
                self.create()
                self._app._boundaries[self.name] = self
                return True
            except Exception:  # pragma : no cover
                self._app.odesign.Undo()
                self._app.logger.error("Update of network object failed.")
                return False
        else:  # pragma : no cover
            self._app.logger.warning("Network object not yet created in design.")
            return False

    @pyaedt_function_handler()
    def update_assignment(self):
        """Update assignments of the network."""
        return self.update()

    class _Link:
        def __init__(self, node_1, node_2, value, name, network):
            self.name = name
            if not isinstance(node_1, str):
                node_1 = "FaceID" + str(node_1)
            if not isinstance(node_2, str):
                node_2 = "FaceID" + str(node_2)
            if not isinstance(value, str):
                value = str(value) + "cel_per_w"
            self.node_1 = node_1
            self.node_2 = node_2
            self.value = value
            self._network = network

        @property
        def _link_type(self):
            unit2type_conversion = {
                "g_per_s": ["C-Link", "Node1ToNode2"],
                "kg_per_s": ["C-Link", "Node1ToNode2"],
                "lbm_per_min": ["C-Link", "Node1ToNode2"],
                "lbm_per_s": ["C-Link", "Node1ToNode2"],
                "Kel_per_W": ["R-Link", "R"],
                "cel_per_w": ["R-Link", "R"],
                "FahSec_per_btu": ["R-Link", "R"],
                "Kels_per_J": ["R-Link", "R"],
                "w_per_m2kel": ["R-Link", "HTC"],
                "w_per_m2Cel": ["R-Link", "HTC"],
                "btu_per_rankHrFt2": ["R-Link", "HTC"],
                "btu_per_fahHrFt2": ["R-Link", "HTC"],
                "btu_per_rankSecFt2": ["R-Link", "HTC"],
                "btu_per_fahSecFt2": ["R-Link", "HTC"],
                "w_per_cm2kel": ["R-Link", "HTC"],
            }
            _, unit = decompose_variable_value(self.value)
            return unit2type_conversion[unit]

        @property
        def props(self):
            """
            Get link properties.

            Returns
            -------
            list
                First two elements of the list are the node names that the link connects,
                the third element is the link type while the fourth contains the value
                associated with the link.
            """
            return [self.node_1, self.node_2] + self._link_type + [self.value]

        @pyaedt_function_handler()
        def delete_link(self):
            """Delete link from network."""
            self._network.props["Links"].pop(self.name)
            self._network._links.remove(self)

    class _Node:
        def __init__(self, name, app, network, node_type=None, props=None):
            self.name = name
            self._type = node_type
            self._app = app
            self._props = props
            self._node_props()
            self._network = network

        @pyaedt_function_handler()
        def delete_node(self):
            """Delete node from network."""
            self._network.props["Nodes"].pop(self.name)
            self._network._nodes.remove(self)

        @property
        def node_type(self):
            """Get node type.

            Returns
            -------
            str
                Node type.
            """
            if self._type is None:  # pragma: no cover
                if self.props is None:
                    self._app.logger.error(
                        "Cannot define node_type. Both its assignment and properties assignment are missing."
                    )
                    return None
                else:
                    type_in_dict = self.props.get("NodeType", None)
                    if type_in_dict is None:
                        self._type = "FaceNode"
                    else:
                        self._type = type_in_dict
            return self._type

        @property
        def props(self):
            """Get properties of the node.

            Returns
            -------
            dict
                Node properties.
            """
            return self._props

        @props.setter
        def props(self, props):
            """Set properties of the node.

            Parameters
            ----------
            props : dict
                Node properties.
            """
            self._props = props
            self._node_props()

        def _node_props(self):
            face_node_default_dict = {
                "FaceID": None,
                "ThermalResistance": "NoResistance",
                "Thickness": "1mm",
                "Material": "Al-Extruded",
                "Resistance": "0cel_per_w",
            }
            boundary_node_default_dict = {
                "NodeType": "BoundaryNode",
                "ValueType": "PowerValue",
                "Power": "0W",
                "Temperature": "25cel",
            }
            internal_node_default_dict = {
                "NodeType": "InternalNode",
                "Power": "0W",
                "Mass": "0.001kg",
                "SpecificHeat": "1000J_per_Kelkg",
            }
            if self.props is None:
                if self.node_type == "InternalNode":
                    self._props = internal_node_default_dict
                elif self.node_type == "FaceNode":
                    self._props = face_node_default_dict
                elif self.node_type == "BoundaryNode":
                    self._props = boundary_node_default_dict
            else:
                if self.node_type == "InternalNode":
                    self._props = self._create_node_dict(internal_node_default_dict)
                elif self.node_type == "FaceNode":
                    self._props = self._create_node_dict(face_node_default_dict)
                elif self.node_type == "BoundaryNode":
                    self._props = self._create_node_dict(boundary_node_default_dict)

        @pyaedt_function_handler()
        def _create_node_dict(self, default_dict):
            node_dict = self.props
            node_name = node_dict.get("Name", self.name)
            if not node_name:
                try:
                    self.name = "Face" + str(node_dict["FaceID"])
                except KeyError:  # pragma: no cover
                    raise KeyError('"Name" key is needed for "BoundaryNodes" and "InternalNodes" dictionaries.')
            else:
                self.name = node_name
                node_dict.pop("Name", None)
            node_args = copy.deepcopy(default_dict)
            for k in node_dict.keys():
                val = node_dict[k]
                if isinstance(val, dict):  # pragma : no cover
                    val = self._app._parse_variation_data(
                        k, val["Type"], variation_value=val["Values"], function=val["Function"]
                    )
                    node_args.pop(k)
                    node_args.update(val)
                else:
                    node_args[k] = val

            return node_args
