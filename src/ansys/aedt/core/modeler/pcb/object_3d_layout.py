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

"""This module provides methods and data structures for managing all properties of
objects (points, lines, sheeets, and solids) within the AEDT 3D Layout Modeler.
"""

import math
import re
from typing import Optional
from typing import Tuple

from ansys.aedt.core.generic.constants import unit_converter
from ansys.aedt.core.generic.general_methods import _arg_with_dim
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.modeler.geometry_operators import GeometryOperators


class Object3DLayout(object):
    """Manages properties of objects in HFSS 3D Layout.

    Parameters
    -----------
    primitives : :class:`ansys.aedt.core.modeler.Model3DLayout.Modeler3dLayout`
    """

    def __init__(self, primitives, prim_type=None):
        self._primitives = primitives
        self.logger = self._primitives.logger
        self._oeditor = self._primitives.oeditor
        self._n = 10
        self.prim_type = prim_type
        self._points = []

    @property
    def object_units(self):
        """Object units.

        Returns
        -------
        str
        """
        return self._primitives.model_units

    @pyaedt_function_handler(property_val="value", names_list="names")
    def change_property(self, value, names=None):
        """Modify a property.

        Parameters
        ----------
        value : list

        names : list, optional
             The default is ``None``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.ChangeProperty
        """
        vChangedProps = ["NAME:ChangedProps", value]
        if names:  # pragma: no cover
            vPropServers = ["NAME:PropServers"]
            for el in names:
                vPropServers.append(el)
        else:
            vPropServers = ["NAME:PropServers", self.name]
        vGeo3dlayout = ["NAME:BaseElementTab", vPropServers, vChangedProps]
        vOut = ["NAME:AllTabs", vGeo3dlayout]

        self._oeditor.ChangeProperty(vOut)
        return True

    @pyaedt_function_handler(property_name="name", property_value="value")
    def set_property_value(self, name, value):
        """Set a property value.

        Parameters
        ----------
        name : str
            Name of the property.
        value :
            Value of the property.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.ChangeProperty
        """
        if "Pt" in name:
            coordinates = value.split(",")
            vProp = ["NAME:" + name, "X:=", coordinates[0], "Y:=", coordinates[1]]
        else:
            vProp = ["NAME:" + name, "Value:=", value]
        return self.change_property(vProp)

    @property
    def angle(self):
        """Get/Set the circle radius.

        Returns
        -------
        str
            placement layer.

        References
        ----------
        >>> oEditor.GetPropertyValue
        """
        if self.prim_type in ["component", "pin", "via"]:
            return self._oeditor.GetPropertyValue("BaseElementTab", self.name, "Angle")

    @angle.setter
    def angle(self, value):
        if self.prim_type in ["component", "pin", "via"]:
            vMaterial = ["NAME:Angle", "Value:=", value]
            self.change_property(vMaterial)

    @property
    def absolute_angle(self):
        """Get the absolute angle location for 2 pins components.

        Returns
        -------
        float
        """
        if self.prim_type != "component":
            return 0.0
        comp_pins = self._oeditor.GetComponentPins(self.name)
        if len(comp_pins) == 2:
            pin_1_name = comp_pins[0]
            pin_2_name = comp_pins[1]
            pin1_info = self._oeditor.GetComponentPinInfo(self.name, pin_1_name)
            pin2_info = self._oeditor.GetComponentPinInfo(self.name, pin_2_name)
            pin1_x = pin1_info[1].split("=")[1]
            pin1_y = pin1_info[2].split("=")[1]
            pin2_x = pin2_info[1].split("=")[1]
            pin2_y = pin2_info[2].split("=")[1]
            p1x = float(pin1_x)
            p1y = float(pin1_y)
            p2x = float(pin2_x)
            p2y = float(pin2_y)
            dy = float(p2y - p1y)
            dx = float(p2x - p1x)
            angle_deg = math.atan2(dy, dx) * 180.0 / math.pi
            if abs(angle_deg - 90.0) < 1:
                angle_deg = 90.0
            if abs(angle_deg) < 1:
                angle_deg = 0.0
            return angle_deg
        return 0.0

    @property
    def net_name(self):
        """Get/Set the net name.

        Returns
        -------
        str
            Name of the net.

        References
        ----------
        >>> oEditor.GetPropertyValue
        """
        if self.prim_type not in ["component"]:
            return self._oeditor.GetPropertyValue("BaseElementTab", self.name, "Net")

    @net_name.setter
    def net_name(self, netname=""):
        if self.prim_type not in ["component"]:
            vMaterial = ["NAME:Net", "Value:=", netname]
            self.change_property(vMaterial)

    @property
    def placement_layer(self):
        """Get/Set the placement layer of the object.

        Returns
        -------
        str
            placement layer.

        References
        ----------
        >>> oEditor.GetPropertyValue
        """
        if self.prim_type not in ["pin", "via"]:
            return self._oeditor.GetPropertyValue("BaseElementTab", self.name, "PlacementLayer")

    @placement_layer.setter
    def placement_layer(self, layer_name):
        if self.prim_type not in ["pin", "via"]:
            vMaterial = ["NAME:PlacementLayer", "Value:=", layer_name]
            self.change_property(vMaterial)

    @property
    def bounding_box(self):
        """Get component bounding box.

        Returns
        -------
        list
            [BB_lower_left_X, BB_lower_left_Y, BB_upper_right_X, BB_upper_right_Y].
        """
        info = self._oeditor.GetComponentInfo(self.name)
        bbllx = bblly = bburx = bbury = 0
        for i in info:
            if "BBoxLLx" in i:
                bbllx = float(i.split("=")[1])
            elif "BBoxLLy" in i:
                bblly = float(i.split("=")[1])
            elif "BBoxURx" in i:
                bburx = float(i.split("=")[1])
            elif "BBoxURy" in i:
                bbury = float(i.split("=")[1])
        bbllx = round(unit_converter(bbllx, output_units=self._primitives.model_units), 9)
        bblly = round(unit_converter(bblly, output_units=self._primitives.model_units), 9)
        bburx = round(unit_converter(bburx, output_units=self._primitives.model_units), 9)
        bbury = round(unit_converter(bbury, output_units=self._primitives.model_units), 9)
        return [bbllx, bblly, bburx, bbury]

    @pyaedt_function_handler()
    def create_clearance_on_component(self, extra_soldermask_clearance=5e-3):
        """Create a Clearance on Soldermask layer by drawing a rectangle.

        Parameters
        ----------
        extra_soldermask_clearance : float, optional
            Extra Soldermask value in model units to be applied on component bounding box.

        Returns
        -------
            bool
        """
        if self.prim_type != "component":
            self.logger.error("Clearance applies only to components.")
            return False
        bbox = self.bounding_box
        start_points = [bbox[0] - extra_soldermask_clearance, bbox[1] - extra_soldermask_clearance]

        dims = [bbox[2] - bbox[0] + 2 * extra_soldermask_clearance, bbox[3] - bbox[1] + 2 * extra_soldermask_clearance]
        drawings = []
        if self.placement_layer == self._primitives.layers.all_signal_layers[0].name:
            for lay in self._primitives.layers.stackup_layers:
                if lay.name != self.placement_layer:
                    drawings.append(lay.name)
                else:
                    break
        else:
            for lay in reversed(self._primitives.layers.stackup_layers):
                if lay.name != self.placement_layer:
                    drawings.append(lay.name)
                else:
                    break
        for layername in drawings:
            rect = self._primitives.create_rectangle(
                layername,
                [
                    self._primitives._app.value_with_units(start_points[0]),
                    self._primitives._app.value_with_units(start_points[1]),
                ],
                [self._primitives._app.value_with_units(dims[0]), self._primitives._app.value_with_units(dims[1])],
            )
            self._primitives.rectangles[rect.name].negative = True
        return True

    @property
    def location(self):
        """Retrieve/Set the absolute location in model units.

        Location is computed with combination of 3d Layout location and model center.

        Returns
        -------
        list
           List of ``(x, y)`` coordinates for the component location.

        References
        ----------
        >>> oEditor.GetPropertyValue
        """
        if self.prim_type == "component":
            info = self._oeditor.GetComponentInfo(self.name)
            bbllx = bblly = bburx = bbury = 0
            for i in info:
                if "BBoxLLx" in i:
                    bbllx = float(i.split("=")[1])
                elif "BBoxLLy" in i:
                    bblly = float(i.split("=")[1])
                elif "BBoxURx" in i:
                    bburx = float(i.split("=")[1])
                elif "BBoxURy" in i:
                    bbury = float(i.split("=")[1])
            loc_x = (bburx + bbllx) / 2
            loc_y = (bbury + bblly) / 2
            loc_x = round(unit_converter(loc_x, output_units=self._primitives.model_units), 9)
            loc_y = round(unit_converter(loc_y, output_units=self._primitives.model_units), 9)
            return [loc_x, loc_y]
        elif self.prim_type in ["pin", "via"]:
            location = self._oeditor.GetPropertyValue("BaseElementTab", self.name, "Location").split(",")
            locs = []
            for i in location:
                try:
                    locs.append(float(i))
                except ValueError:  # pragma: no cover
                    locs.append(i)
            return locs
        else:
            return None

    @location.setter
    def location(self, position):
        if self.prim_type in ["component", "pin", "via"]:
            props = [
                "NAME:Location",
                "X:=",
                self._primitives._app.value_with_units(position[0]),
                "Y:=",
                self._primitives._app.value_with_units(position[1]),
            ]
            self.change_property(props)
        if self.prim_type == "component":
            info = self._oeditor.GetComponentInfo(self.name)
            bbllx = bblly = bburx = bbury = 0
            for i in info:
                if "BBoxLLx" in i:
                    bbllx = float(i.split("=")[1])
                elif "BBoxLLy" in i:
                    bblly = float(i.split("=")[1])
                elif "BBoxURx" in i:
                    bburx = float(i.split("=")[1])
                elif "BBoxURy" in i:
                    bbury = float(i.split("=")[1])
            position[0] -= self.location[0] - unit_converter(
                (bburx + bbllx) / 2, output_units=self._primitives.model_units
            )
            position[1] -= self.location[1] - unit_converter(
                (bbury + bblly) / 2, output_units=self._primitives.model_units
            )
            if abs(position[0]) > 1e-12 or abs(position[1]) > 1e-12:
                props = [
                    "NAME:Location",
                    "X:=",
                    self._primitives._app.value_with_units(position[0]),
                    "Y:=",
                    self._primitives._app.value_with_units(position[1]),
                ]
                self.change_property(props)

    @property
    def lock_position(self):
        """Get/Set the lock position.

        Parameters
        ----------
        lock_position : bool, optional
            The default value is ``True``.

        Returns
        -------
        type

        References
        ----------
        >>> oEditor.ChangeProperty
        """
        return (
            True
            if self._oeditor.GetPropertyValue("BaseElementTab", self.name, "LockPosition") in [True, "true"]
            else False
        )

    @lock_position.setter
    def lock_position(self, lock_position=True):
        vMaterial = ["NAME:LockPosition", "Value:=", lock_position]
        self.change_property(vMaterial)


class ModelInfoRlc(object):
    def __init__(self, component, name):
        self._comp = component
        self._name = name

    @property
    def rlc_model_type(self):
        props = self._comp._oeditor.GetComponentInfo(self._name)
        model = ""
        for p in props:
            if "ComponentProp=" in p:
                model = p
                break
        s = r".+rlc\(r='(.+?)', re=(.+?), l='(.+?)', le=(.+?), c='(.+?)', ce=(.+?), p=(.+?), lyr=(.+?)"
        m = re.search(s, model)
        vals = []
        if m:
            for i in range(1, 9):
                if m.group(i) == "false":
                    vals.append(False)
                elif m.group(i) == "true":
                    vals.append(True)
                else:
                    vals.append(m.group(i))
        return vals

    @property
    def res(self):
        if self.rlc_model_type:
            return self.rlc_model_type[0]

    @property
    def cap(self):
        if self.rlc_model_type:
            return self.rlc_model_type[4]

    @property
    def ind(self):
        if self.rlc_model_type:
            return self.rlc_model_type[2]

    @property
    def is_parallel(self):
        if self.rlc_model_type:
            return self.rlc_model_type[6]


class Components3DLayout(Object3DLayout, object):
    """Contains components in HFSS 3D Layout."""

    def __init__(self, primitives, name="", edb_object=None):
        Object3DLayout.__init__(self, primitives, "component")
        self.name = name
        self.edb_object = edb_object
        self._pins = {}

    @staticmethod
    def __get_die_properties(model_info):
        s = r".+DieProp\(dt=(.+?), do=(.+?), dh='(.+?)', lid=(.+?)\)"
        m = re.search(s, model_info)
        dt = 0
        do = 0
        dh = "0"
        lid = -100
        if m:
            dt = int(m.group(1))
            do = int(m.group(2))
            dh = str(m.group(3))
            lid = int(m.group(4))
        return dt, do, dh, lid

    @staticmethod
    def __get_port_properties(model_info):
        s = r".+PortProp\(rh='(.+?)', rsa=(.+?), rsx='(.+?)', rsy='(.+?)'\)"
        m = re.search(s, model_info)
        rsx = "0"
        rsy = "0"
        rsa = True
        rh = "0"
        if m:
            rh = m.group(1)
            rsx = m.group(3)
            rsy = m.group(4)
            if m.group(2) == "false":
                rsa = False
        return rh, rsa, rsx, rsy

    @property
    def part(self):
        """Retrieve the component part.

        Returns
        -------
        type
            Component part.

        References
        ----------
        >>> oEditor.GetPropertyValue
        """
        return self._oeditor.GetPropertyValue("BaseElementTab", self.name, "Part")

    @property
    def part_type(self):
        """Retrieve the component part type.

        Returns
        -------
        type
            Component part type.

        References
        ----------
        >>> oEditor.GetPropertyValue
        """
        return self._oeditor.GetPropertyValue("BaseElementTab", self.name, "Part Type")

    def __part_type_id(self):
        parts = {"Other": 0, "Resistor": 1, "Inductor": 2, "Capacitor": 3, "IC": 4, "IO": 5}
        if self.part_type in parts:
            return parts[self.part_type]
        return -1

    @property
    def enabled(self):
        """Enable or Disable the RLC Component.

        Parameters
        ----------
        status : bool, optional
            Set the RLC Component to Enable or Disable state.

        Returns
        -------
        bool
            `True` if succeeded.
        """
        comp_info = self._oeditor.GetComponentInfo(self.name)
        for el in comp_info:
            if "ComponentProp=" in el and "CompPropEnabled=false" in el:
                return False
            elif "ComponentProp=" in el and "CompPropEnabled=true" in el:
                return True
        return True

    @enabled.setter
    def enabled(self, status):
        if self.__part_type_id() in [0, 4, 5]:
            return False
        self._oeditor.EnableComponents(["NAME:Components", self.name], status)

    @property
    def die_properties(self) -> Optional[Tuple[int, int, str, int]]:
        """Get die properties from component.

        Returns
        -------
        Tuple[int, int, str, int]
            Tuple of die type (``0`` for None, ``1``, for FlipChip, or ``2`` for WireBond), die orientation (``0`` for
            Chip Top or ``1`` for Chip Bottom), die height as a string, and a reserved property as an integer.
        """
        if self.__part_type_id() != 4:
            return None
        return Components3DLayout.__get_die_properties(self.__get_model_info())

    def __has_port_properties(self) -> bool:
        return self.__part_type_id() in [0, 4, 5]

    @property
    def port_properties(self) -> Optional[Tuple[str, bool, str, str]]:
        """Get port properties from component.

        Returns
        -------
        Tuple[str, bool, str, str]
            Tuple of reference offset [str], reference size auto [bool], reference size X dimension [str], reference
            size Y dimension [str].
        """
        if not self.__has_port_properties():
            return None
        return Components3DLayout.__get_port_properties(self.__get_model_info())

    @port_properties.setter
    def port_properties(self, values: Tuple[str, bool, str, str]):
        rh, rsa, rsx, rsy = values
        if not self.__has_port_properties():
            self.logger.warning(
                f"Cannot set port_properties on {self.name!r} with part type ID {self.__part_type_id()!r}"
            )
            return
        if self.__part_type_id() == 4:
            prop_name = "ICProp:="
        else:
            prop_name = "IOProp:="
        port_properties = ["rh:=", rh, "rsa:=", rsa, "rsx:=", rsx, "rsy:=", rsy]

        args = [
            "NAME:Model Info",
            [
                "NAME:Model",
                prop_name,
                [
                    "PortProp:=",
                    port_properties,
                ],
            ],
        ]
        if self.__part_type_id() == 4:
            dt, do, dh, lid = self.die_properties
            args[1] = [
                "NAME:Model",
                prop_name,
                [
                    "DieProp:=",
                    ["dt:=", dt, "do:=", do, "dh:=", dh, "lid:=", lid],
                    "PortProp:=",
                    port_properties,
                ],
                "CompType:=",
                4,
            ]

        self.change_property(args)

    @property
    def solderball_enabled(self):
        """Check if solderball is enabled.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if not self.__has_port_properties():
            return False
        component_info = str(list(self._oeditor.GetComponentInfo(self.name))).replace("'", "").replace('"', "")
        if "sbsh=Cyl" in component_info or "sbsh=Sph" in component_info:
            return True
        return False

    @property
    def die_enabled(self):
        """Check if the die is enabled. This method is valid for integrated circuits only.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if not self.__has_port_properties():
            return False
        component_info = str(list(self._oeditor.GetComponentInfo(self.name))).replace("'", "").replace('"', "")
        if "dt=1" in component_info or "dt=2" in component_info:
            return True
        return False

    @property
    def die_type(self):
        """Die type.

        Returns
        -------
        str
        """
        if not self.__has_port_properties():
            return False
        component_info = str(list(self._oeditor.GetComponentInfo(self.name))).replace("'", "").replace('"', "")
        if "dt=1" in component_info:
            return "FlipChip"
        elif "dt=2" in component_info:
            return "WireBond"
        return None

    @pyaedt_function_handler()
    def set_die_type(
        self,
        die_type=1,
        orientation=0,
        height=0,
        reference_offset=0,
        auto_reference=True,
        reference_x="0.1mm",
        reference_y="0.1mm",
    ):
        """Set the die type.

        Parameters
        ----------
        die_type : int, optional
            Die type. The default is ``1``. Options are ``0`` for None, ``1`` for FlipChip, and
            ``2`` for WireBond.
        orientation : int, optional
            Die orientation. The default is ``0``. Options are ``0`` for Chip Top and ``1`` for
            Chip Bottom.
        height : float, optional
            Die height valid for port setup. The default is ``0``.
        reference_offset : str, float, optional
            Port reference offset. The default is ``0``.
        auto_reference : bool, optional
            Whether to automatically compute reference size. The default is ``True``.
        reference_x : str, float, optional
            Reference x size for when ``auto_reference=False``.
        reference_y : str, float, optional
            Reference y size for when ``auto_reference=False``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if not self.__has_port_properties():
            return False
        if auto_reference:
            reference_x = "0"
            reference_y = "0"
        if self.__part_type_id() == 4:
            prop_name = "ICProp:="
        else:
            prop_name = "IOProp:="
        args = [
            "NAME:Model Info",
            [
                "NAME:Model",
                prop_name,
                [
                    "DieProp:=",
                    ["dt:=", die_type, "do:=", orientation, "dh:=", str(height), "lid:=", -100],
                    "PortProp:=",
                    [
                        "rh:=",
                        str(reference_offset),
                        "rsa:=",
                        auto_reference,
                        "rsx:=",
                        reference_x,
                        "rsy:=",
                        reference_y,
                    ],
                ],
                "CompType:=",
                4,
            ],
        ]
        return self.change_property(args)

    @pyaedt_function_handler()
    def set_solderball(
        self,
        solderball_type="Cyl",
        diameter="0.1mm",
        mid_diameter="0.1mm",
        height="0.2mm",
        material="solder",
        reference_offset=None,
    ):
        """Set solderball on the active component.

        The method applies to these component types: ``Other``, ``IC`` and ``IO``.

        Parameters
        ----------
        solderball_type : str, optional
            Solderball type. The default is ``"Cyl"``. Options are ``"None"``, ``"Cyl"``,
            and ``"Sph"``.
        diameter : str, optional
            Ball diameter. The default is ``"0.1mm"``.
        mid_diameter : str, optional
            Ball mid diameter. The default is ``"0.1mm"``.
        height : str, optional
            Ball height. The default is height="0.2mm".
        material : str, optional
            Ball material. The default is ``"solder"``.
        reference_offset : str, optional.
            Reference offset for port creation.  The default is ``"0mm"``

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed or the wrong component type.
        """
        if not self.__has_port_properties():
            return False
        model_info = self.__get_model_info()
        rh, rsa, rsx, rsy = Components3DLayout.__get_port_properties(model_info)
        if reference_offset:
            rh = reference_offset
        if self.__part_type_id() == 4:
            prop_name = "ICProp:="
            if not self.die_enabled:
                self.set_die_type()
            dt, do, dh, lid = Components3DLayout.__get_die_properties(model_info)

            args = [
                "NAME:Model Info",
                [
                    "NAME:Model",
                    prop_name,
                    [
                        "SolderBallProp:=",
                        [
                            "sbsh:=",
                            str(solderball_type),
                            "sbh:=",
                            height,
                            "sbr:=",
                            diameter,
                            "sb2:=",
                            mid_diameter,
                            "sbn:=",
                            material,
                        ],
                        "DieProp:=",
                        ["dt:=", dt, "do:=", do, "dh:=", dh, "lid:=", lid],
                        "PortProp:=",
                        ["rh:=", rh, "rsa:=", rsa, "rsx:=", rsx, "rsy:=", rsy],
                    ],
                    "CompType:=",
                    4,
                ],
            ]
        else:
            prop_name = "IOProp:="
            args = [
                "NAME:Model Info",
                [
                    "NAME:Model",
                    prop_name,
                    [
                        "SolderBallProp:=",
                        [
                            "sbsh:=",
                            str(solderball_type),
                            "sbh:=",
                            height,
                            "sbr:=",
                            diameter,
                            "sb2:=",
                            mid_diameter,
                            "sbn:=",
                            material,
                        ],
                        "PortProp:=",
                        ["rh:=", rh, "rsa:=", rsa, "rsx:=", rsx, "rsy:=", rsy],
                    ],
                ],
            ]
        return self.change_property(args)

    def __get_model_info(self):
        props = self._oeditor.GetComponentInfo(self.name)
        model_info = ""
        for p in props:
            if "PortProp(" in p:
                model_info = p
                break
        return model_info

    @property
    def pins(self):
        """Component pins.

        Returns
        -------
        dict
            Dictionary of pins.
        """
        if self._pins:
            return self._pins
        self._pins = {i: Pins3DLayout(self._primitives, i) for i in list(self._oeditor.GetComponentPins(self.name))}
        return self._pins

    @property
    def model(self):
        """RLC model if available.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.object_3dlayout.ModelInfoRlc`
        """
        if self.__part_type_id() in [1, 2, 3]:
            return ModelInfoRlc(self, self.name)


class Nets3DLayout(object):
    """Contains Nets in HFSS 3D Layout."""

    def __init__(self, primitives, name=""):
        self._primitives = primitives
        self._oeditor = self._primitives.oeditor
        self._n = 10
        self.name = name

    @property
    def components(self):
        """Components that belongs to the Nets.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.object_3dlayout.Components3DLayout`
        """
        comps = {}
        for c in self._oeditor.FilterObjectList("Type", "component", self._oeditor.FindObjects("Net", self.name)):
            comps[c] = self._primitives.components[c]
        return comps

    @property
    def geometry_names(self):
        """List of geometry names.

        Returns
        -------
        list
            Geometries that belong to the selected net."""
        comps = self._primitives._get_names(["component", "pin", "via"])
        geo = [i for i in self._oeditor.FindObjects("Net", self.name) if i not in comps]
        return geo

    @pyaedt_function_handler()
    def plot(
        self,
        layers=None,
        show_legend=True,
        save_plot=None,
        outline=None,
        size=(1920, 1440),
        plot_components_on_top=False,
        plot_components_on_bottom=False,
        show=True,
    ):
        """Plot a Net to Matplotlib 2D Chart.

        Parameters
        ----------
        layers : str, list, optional
            Name of the layers to include in the plot. If ``None`` all the signal layers will be considered.
        show_legend : bool, optional
            If ``True`` the legend is shown in the plot. (default)
            If ``False`` the legend is not shown.
        save_plot : str, optional
            If a path is specified the plot will be saved in this location.
            If ``save_plot`` is provided, the ``show`` parameter is ignored.
        outline : list, optional
            List of points of the outline to plot.
        size : tuple, int, optional
            Image size in pixel (width, height). Default value is ``(2000, 1000)``
        plot_components_on_top : bool, optional
            If ``True``  the components placed on top layer are plotted.
            If ``False`` the components are not plotted. (default)
            If nets and/or layers is specified, only the components belonging to the specified nets/layers are plotted.
        plot_components_on_bottom : bool, optional
            If ``True``  the components placed on bottom layer are plotted.
            If ``False`` the components are not plotted. (default)
            If nets and/or layers is specified, only the components belonging to the specified nets/layers are plotted.
        show : bool, optional
            Whether to show the plot or not. Default is `True`.
        """
        return self._primitives.edb.nets.plot(
            self.name,
            layers=layers,
            color_by_net=False,
            show_legend=show_legend,
            save_plot=save_plot,
            outline=outline,
            size=size,
            plot_components_on_top=plot_components_on_top,
            plot_components_on_bottom=plot_components_on_bottom,
            show=show,
        )


class Pins3DLayout(Object3DLayout, object):
    """Contains the pins in HFSS 3D Layout."""

    def __init__(self, primitives, name="", component_name=None, is_pin=True):
        Object3DLayout.__init__(self, primitives, "pin" if is_pin else "via")
        self.componentname = "-".join(name.split("-")[:-1]) if not component_name else component_name
        self.name = name
        self.is_pin = is_pin

    @property
    def start_layer(self):
        """Retrieve the starting layer of the pin.

        Returns
        -------
        str
            Name of the starting layer of the pin.

        References
        ----------
        >>> oEditor.GetPropertyValue
        """
        return self._oeditor.GetPropertyValue("BaseElementTab", self.name, "Start Layer")

    @property
    def stop_layer(self):
        """Retrieve the starting layer of the pin.

        Returns
        -------
        str
            Name of the stopping layer of the pin.

        References
        ----------
        >>> oEditor.GetPropertyValue
        """
        return self._oeditor.GetPropertyValue("BaseElementTab", self.name, "Stop Layer")

    @property
    def holediam(self):
        """Retrieve the hole diameter of the pin.

        Returns
        -------
        float
           Hole diameter of the pin.

        References
        ----------
        >>> oEditor.GetPropertyValue
        """
        return self._oeditor.GetPropertyValue("BaseElementTab", self.name, "HoleDiameter")


class Geometries3DLayout(Object3DLayout, object):
    """Contains geometries in HFSS 3D Layout."""

    def __init__(self, primitives, name, prim_type="poly", is_void=False):
        Object3DLayout.__init__(self, primitives, prim_type)
        self.is_void = is_void
        self._name = name

    @property
    def obounding_box(self):
        """Bounding box of a specified object.

        Returns
        -------
        list
            List of [LLx, LLy, URx, URy] coordinates.

        References
        ----------
        >>> oEditor.GetBBox
        """
        return self._primitives.obounding_box(self.name)

    @property
    def name(self):
        """Name of Primitive."""
        return self._name

    @name.setter
    def name(self, value):
        try:
            del self._primitives._lines[self.name]
            args = ["NAME:Name", "Value:=", value]
            self.change_property(args)
            self._name = value
            self._primitives._lines[self._name] = self
        except Exception:
            self.logger.debug(f"Couldn't update geometry name into '{value}'.")

    @property
    def is_closed(self):
        """Either if the Geometry is closed or not.

        Returns
        -------
        bool
        """
        return True

    @property
    def points(self):
        """Provide the polygon points. For Lines it returns the center line.

        Returns
        -------
        List of :class:`ansys.aedt.core.modeler.cad.object_3dlayout.Points3dLayout`
        """
        if self._points:
            return self._points
        self._points = []
        obj = self._oeditor.GetPolygon(self.name)
        for oo in obj.GetPoints():
            self._points.append(Points3dLayout(self._primitives, oo))
        return self._points

    @property
    def edges(self):
        """Edges list.

        Returns
        -------
        List
        """
        info = self._oeditor.GetPolygonInfo(self.name)
        points = []
        for i in info:
            if i == "Poly:=":
                for k in info[info.index(i) + 1]:
                    if k == "pt:=":
                        source = info[info.index(i) + 1]
                        points = source[source.index(k) + 1][2:]
                        break
        xpoints = list(points[1::4])
        ypoints = list(points[3::4])
        if self.prim_type not in ["rect", "line"]:
            xt, yt = GeometryOperators.orient_polygon(xpoints, ypoints, clockwise=False)
        else:
            xt, yt = xpoints, ypoints
        edges = []
        p1 = None
        p2 = None
        for x, y in zip(xt, yt):
            if y < 1e100:
                if not p1:
                    p1 = [x, y]
                elif not p2:
                    p2 = [x, y]
                    edges.append([p1, p2])
                    p1 = p2
                else:
                    edges.append([p1, [x, y]])
                    p1 = [x, y]
        if self.prim_type == "rect":
            edges = [edges[2], edges[3], edges[0], edges[1]]
        return edges

    @pyaedt_function_handler()
    def edge_by_point(self, point):
        """Return the closest edge to specified point.

        Parameters
        ----------
        point : list
            List of [x,y] values.

        Returns
        -------
        int
            Edge id.
        """
        index_i = 0
        v_dist = None
        edge_id = None
        for edge in self.edges:
            v = GeometryOperators.v_norm(GeometryOperators.distance_vector(point, edge[0], edge[1]))
            if not v_dist or v < v_dist:
                v_dist = v
                edge_id = index_i
            index_i += 1
        return edge_id

    @property
    def bottom_edge_x(self):
        """Compute the lower edge in the layout on x direction.

        Returns
        -------
        int
            Edge number.
        """
        result = [(edge[0][0] + edge[1][0]) for edge in self.edges]
        return result.index(min(result))

    @property
    def top_edge_x(self):
        """Compute the upper edge in the layout on x direction.

        Returns
        -------
        int
            Edge number.
        """
        result = [(edge[0][0] + edge[1][0]) for edge in self.edges]
        return result.index(max(result))

    @property
    def bottom_edge_y(self):
        """Compute the lower edge in the layout on y direction.

        Returns
        -------
        int
            Edge number.
        """
        result = [(edge[0][1] + edge[1][1]) for edge in self.edges]
        return result.index(min(result))

    @property
    def top_edge_y(self):
        """Compute the upper edge in the layout on y direction.

        Returns
        -------
        int
            Edge number.
        """
        result = [(edge[0][1] + edge[1][1]) for edge in self.edges]
        return result.index(max(result))

    @pyaedt_function_handler(propertyname="name")
    def get_property_value(self, name):
        """Retrieve a property value.

        Parameters
        ----------
        name : str
            Name of the property

        Returns
        -------
        type
            Value of the property.

        References
        ----------
        >>> oEditor.GetPropertyValue
        """
        return self._oeditor.GetPropertyValue("BaseElementTab", self.name, name)

    @property
    def negative(self):
        """Get/Set the negative.

        Parameters
        ----------
        negative : bool, optional
            The default is ``False``.

        Returns
        -------
        type

        References
        ----------
        >>> oEditor.ChangeProperty
        """
        if self.is_void:
            return False
        return (
            True if self._oeditor.GetPropertyValue("BaseElementTab", self.name, "Negative") in [True, "true"] else False
        )

    @negative.setter
    def negative(self, negative=False):
        if not self.is_void:
            vMaterial = ["NAME:Negative", "Value:=", negative]
            self.change_property(vMaterial)

    @property
    def net_name(self):
        """Get/Set the net name.

        Returns
        -------
        str
            Name of the net.

        References
        ----------
        >>> oEditor.GetPropertyValue
        """
        if self.is_void:
            return None
        if self.prim_type not in ["component"]:
            return self._oeditor.GetPropertyValue("BaseElementTab", self.name, "Net")

    @net_name.setter
    def net_name(self, netname=""):
        if not self.is_void and self.prim_type not in ["component"]:
            vMaterial = ["NAME:Net", "Value:=", netname]
            self.change_property(vMaterial)


class Polygons3DLayout(Geometries3DLayout, object):
    """Manages Hfss 3D Layout polygons."""

    def __init__(self, primitives, name, prim_type="poly", is_void=False):
        Geometries3DLayout.__init__(self, primitives, name, prim_type, is_void)
        self._points = []

    @property
    def is_closed(self):
        """Either if the Geometry is closed or not.

        Returns
        -------
        bool
        """
        obj = self._oeditor.GetPolygon(self.name)
        return obj.IsClosed()

    @property
    def polygon_voids(self):
        """All Polygon Voids.

        Returns
        -------
        dict
            Dictionary of polygon voids.
        """
        voids = list(self._oeditor.GetPolygonVoids(self.name))
        pvoids = {}
        for void in voids:
            pvoids[void] = Polygons3DLayout(self._primitives, void, "poly", True)
        return pvoids


class Circle3dLayout(Geometries3DLayout, object):
    """Manages Hfss 3D Layout circles."""

    def __init__(self, primitives, name, is_void=False):
        Geometries3DLayout.__init__(self, primitives, name, "circle", is_void)

    @property
    def center(self):
        """Get/Set the circle center.

        Returns
        -------
        str
            placement layer.

        References
        ----------
        >>> oEditor.GetPropertyValue
        """
        cent = self._oeditor.GetPropertyValue("BaseElementTab", self.name, "Center")
        if cent:
            return cent.split(",")

    @center.setter
    def center(self, position):
        vMaterial = ["NAME:Center", "Value:=", position]
        self.change_property(vMaterial)

    @property
    def radius(self):
        """Get/Set the circle radius.

        Returns
        -------
        str
            placement layer.

        References
        ----------
        >>> oEditor.GetPropertyValue
        """
        return self._oeditor.GetPropertyValue("BaseElementTab", self.name, "Radius")

    @radius.setter
    def radius(self, value):
        vMaterial = ["NAME:Radius", "Value:=", value]
        self.change_property(vMaterial)


class Rect3dLayout(Geometries3DLayout, object):
    """Manages Hfss 3D Layout rectangles."""

    def __init__(self, primitives, name, is_void=False):
        Geometries3DLayout.__init__(self, primitives, name, "rect", is_void)

    @property
    def corner_radius(self):
        """Get/Set the circle radius.

        Returns
        -------
        str
            placement layer.

        References
        ----------
        >>> oEditor.GetPropertyValue
        """
        return self._oeditor.GetPropertyValue("BaseElementTab", self.name, "CornerRadius")

    @corner_radius.setter
    def corner_radius(self, value):
        vMaterial = ["NAME:CornerRadius", "Value:=", value]
        self.change_property(vMaterial)

    @property
    def two_point_description(self):
        """Get/Set the circle radius.

        Returns
        -------
        str
            placement layer.

        References
        ----------
        >>> oEditor.GetPropertyValue
        """
        return (
            True
            if self._oeditor.GetPropertyValue("BaseElementTab", self.name, "2 pt Description") in [True, "true"]
            else False
        )

    @two_point_description.setter
    def two_point_description(self, value):
        vMaterial = ["NAME:2 pt Description", "Value:=", value]
        self.change_property(vMaterial)

    @property
    def center(self):
        """Get/Set the rectangle center.

        Returns
        -------
        str
            placement layer.

        References
        ----------
        >>> oEditor.GetPropertyValue
        """
        if not self.two_point_description:
            cent = self._oeditor.GetPropertyValue("BaseElementTab", self.name, "Center")
            if cent:
                return cent.split(",")

    @center.setter
    def center(self, value):
        if not self.two_point_description:
            vMaterial = ["NAME:Center", "X:=", value[0], "Y:=", value[1]]
            self.change_property(vMaterial)

    @property
    def width(self):
        """Get/Set the circle radius.

        Returns
        -------
        str
            placement layer.

        References
        ----------
        >>> oEditor.GetPropertyValue
        """
        if not self.two_point_description:
            return self._oeditor.GetPropertyValue("BaseElementTab", self.name, "Width")

    @width.setter
    def width(self, value):
        if not self.two_point_description:
            vMaterial = ["NAME:Width", "Value:=", value]
            self.change_property(vMaterial)

    @property
    def height(self):
        """Get/Set the circle radius.

        Returns
        -------
        str
            placement layer.

        References
        ----------
        >>> oEditor.GetPropertyValue
        """
        if not self.two_point_description:
            return self._oeditor.GetPropertyValue("BaseElementTab", self.name, "Height")

    @height.setter
    def height(self, value):
        if not self.two_point_description:
            vMaterial = ["NAME:Height", "Value:=", value]
            self.change_property(vMaterial)

    @property
    def point_a(self):
        """Get/Set the Point A value if 2Point Description is enabled.

        Returns
        -------
        List
            Point A coordinates.

        References
        ----------
        >>> oEditor.GetPropertyValue
        """
        if self.two_point_description:
            pa = self._oeditor.GetPropertyValue("BaseElementTab", self.name, "Pt A")
            if pa:
                return pa.split(",")

    @point_a.setter
    def point_a(self, value):
        if self.two_point_description:
            vMaterial = ["NAME:Pt A", "X:=", value[0], "Y:=", value[1]]
            self.change_property(vMaterial)

    @property
    def point_b(self):
        """Get/Set the Point A value if 2Point Description is enabled.

        Returns
        -------
        List
            Point B coordinates

        References
        ----------
        >>> oEditor.GetPropertyValue
        """
        if self.two_point_description:
            pa = self._oeditor.GetPropertyValue("BaseElementTab", self.name, "Pt B")
            if pa:
                return pa.split(",")

    @point_b.setter
    def point_b(self, value):
        if self.two_point_description:
            vMaterial = ["NAME:Pt B", "X:=", value[0], "Y:=", value[1]]
            self.change_property(vMaterial)


class Line3dLayout(Geometries3DLayout, object):
    """Manages Hfss 3D Layout lines."""

    def __init__(self, primitives, name, is_void=False):
        Geometries3DLayout.__init__(self, primitives, name, "line", is_void)
        self._points = []
        self._center_line = {}

    @property
    def bend_type(self):
        """Get/Set the line bend type.

        Returns
        -------
        str
            Bend Type.

        References
        ----------
        >>> oEditor.GetPropertyValue
        """
        return self._oeditor.GetPropertyValue("BaseElementTab", self.name, "BendType")

    @bend_type.setter
    def bend_type(self, value):
        vMaterial = ["NAME:BendType", "Value:=", value]
        self.change_property(vMaterial)

    @property
    def start_cap_type(self):
        """Get/Set the line start type.

        Returns
        -------
        str
            Start Cap Type.

        References
        ----------
        >>> oEditor.GetPropertyValue
        """
        return self._oeditor.GetPropertyValue("BaseElementTab", self.name, "StartCapType")

    @start_cap_type.setter
    def start_cap_type(self, value):
        vMaterial = ["NAME:StartCap Type", "Value:=", value]
        self.change_property(vMaterial)

    @property
    def end_cap_type(self):
        """Get/Set the line end type.

        Returns
        -------
        str
            End Cap Type.

        References
        ----------
        >>> oEditor.GetPropertyValue
        """
        return self._oeditor.GetPropertyValue("BaseElementTab", self.name, "EndCapType")

    @end_cap_type.setter
    def end_cap_type(self, value):
        vMaterial = ["NAME:EndCap Type", "Value:=", value]
        self.change_property(vMaterial)

    @property
    def width(self):
        """Get/Set the line width.

        Returns
        -------
        str
            Line Width.

        References
        ----------
        >>> oEditor.GetPropertyValue
        """
        return self._oeditor.GetPropertyValue("BaseElementTab", self.name, "LineWidth")

    @width.setter
    def width(self, value):
        vMaterial = ["NAME:LineWidth", "Value:=", value]
        self.change_property(vMaterial)

    @property
    def length(self):
        """Get the line length.

        Returns
        -------
        str
            Line length.

        References
        ----------
        >>> oEditor.GetPropertyValue
        """
        return self._oeditor.GetPropertyValue("BaseElementTab", self.name, "TotalLength")

    @property
    def center_line(self):
        """Get the center line points and arc height.

        Returns
        -------
        dict
            Points.
        """
        props = [
            i
            for i in list(self._oeditor.GetProperties("BaseElementTab", self.name))
            if i.startswith("Pt") or i.startswith("ArcHeight")
        ]
        self._center_line = {}
        for i in props:
            self._center_line[i] = [
                i.strip() for i in self._oeditor.GetPropertyValue("BaseElementTab", self.name, i).split(",")
            ]
        return self._center_line

    @center_line.setter
    def center_line(self, points):
        u = self._primitives.model_units
        for point_name, value in points.items():
            if len(value) == 2:
                vpoint = [
                    f"NAME:{point_name}",
                    "X:=",
                    self._primitives._app.value_with_units(value[0], u),
                    "Y:=",
                    self._primitives._app.value_with_units(value[1], u),
                ]
            elif isinstance(value, list):
                vpoint = [f"NAME:{point_name}", "Value:=", self._primitives._app.value_with_units(value[0], u)]
            else:
                vpoint = [f"NAME:{point_name}", "Value:=", self._primitives._app.value_with_units(value, u)]
            self.change_property(vpoint)
        self._center_line = {}

    @pyaedt_function_handler()
    def add(self, point, position=0):
        """Add a new point to the center line.

        Parameters
        ----------
        point : list
            [x,y] coordinate point to add.
        position : int, optional
            Position of the new point in the geometry.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.pcb.object_3d_layout.Line3dLayout`
        """
        points = [
            [self._primitives._app.value_with_units(j, self.object_units) for j in i]
            for i in (self.center_line.values())
        ]
        points.insert(position, [self._primitives._app.value_with_units(j, self.object_units) for j in point])
        line = self._primitives.create_line(self.placement_layer, points)
        line_name = self.name
        self._primitives.oeditor.Delete([self.name])
        line.name = line_name
        self._primitives._lines[self.name] = line
        return line

    @pyaedt_function_handler()
    def remove(self, point):
        """Remove one or more points from the center line.

        Parameters
        ----------
        point : list, str
            Name of points to remove in the form of ``"Ptx"``.


        Returns
        -------
        :class:`ansys.aedt.core.modeler.pcb.object_3d_layout.Line3dLayout`
        """
        if isinstance(point, str):
            point = [point]
        points = [
            [self._primitives._app.value_with_units(j, self.object_units) for j in v]
            for i, v in self.center_line.items()
            if i not in point
        ]
        line = self._primitives.create_line(self.placement_layer, points)
        line_name = self.name
        self._primitives.oeditor.Delete([self.name])
        line.name = line_name
        self._primitives._lines[self.name] = line
        return line

    @pyaedt_function_handler()
    def _edit(self, points):
        name = self.name
        arg = ["NAME:Contents", "lineGeometry:="]
        arg2 = [
            "Name:=",
            name,
            "LayerName:=",
            self.placement_layer,
            "lw:=",
            self._primitives._app.value_with_units(self.width),
            "endstyle:=",
            self.end_cap_type,
            "StartCap:=",
            self.start_cap_type,
            "n:=",
            len(points),
            "U:=",
            self.object_units,
        ]
        i = 0
        for a in points:
            arg2.append(f"x{i}:=")
            arg2.append(a[0])
            arg2.append(f"y{i}:=")
            arg2.append(a[1])
            i += 1
        arg.append(arg2)
        arg_edit = ["NAME:items", ["NAME:item", "name:" + self.name]]
        arg_edit[1].append(arg)
        self._oeditor.Edit(arg_edit)


class Points3dLayout(object):
    """Manages HFSS 3D Layout points."""

    def __init__(self, primitives, point):
        self._primitives = primitives
        self.point = point

    @property
    def is_arc(self):
        """Either if the Point is an arc or not.

        Returns
        -------
        bool
        """
        return True if self.point.IsArc() != 0 else False

    @property
    def position(self):
        """Points x and y coordinate.

        Returns
        -------
        List
        """
        if self.is_arc:
            return [self.point.GetX()]
        else:
            return [self.point.GetX(), self.point.GetY()]

    @pyaedt_function_handler(new_position="location")
    def move(self, location):
        """Move actual point to new location.

        Parameters
        ----------
        location : List
            New point location.

        Returns
        -------
        bool
            ``True`` if the point was moved to the new location.

        """
        if self.point.Move(self._primitives.oeditor.Point().Set(location[0], location[1])):
            return True


class ComponentsSubCircuit3DLayout(Object3DLayout, object):
    """Contains 3d Components in HFSS 3D Layout.

    Parameters
    ----------
    parent :

    name : string, optional
        The default is ``""``.

    """

    def __init__(self, primitives, name=""):
        Object3DLayout.__init__(self, primitives, "component")
        self.name = name

    @property
    def component_info(self):
        """Retrieve all component info."""
        return self._oeditor.GetComponentInfo(self.name)

    @property
    def component_name(self):
        """Retrieve the component name."""
        try:
            return self.component_info[0].split("=")[1]
        except IndexError:
            return ""

    @property
    def angle(self):
        """Retrieve/Set the component angle.

        Returns
        -------
        str
            Component angle.

        References
        ----------
        >>> oEditor.GetPropertyValue
        """
        if self.is_3d_placement:
            ang = self._oeditor.GetPropertyValue("BaseElementTab", self.name, "Rotation Angle")
        else:
            ang = self._oeditor.GetPropertyValue("BaseElementTab", self.name, "Angle")
        try:
            return float(ang)
        except ValueError:
            return ang

    @angle.setter
    def angle(self, angle_val):
        if isinstance(angle_val, (int, float)):
            angle_val = f"{angle_val}deg"

        if not self.is_3d_placement:
            props = ["NAME:Angle", "Value:=", angle_val]
        else:
            props = ["NAME:Rotation Angle", "Value:=", angle_val]
        self.change_property(props)

    @property
    def is_3d_placement(self):
        """Retrieve if the component has 3d placement."""
        if self._oeditor.GetPropertyValue("BaseElementTab", self.name, "3D Placement") in ["true", "True"]:
            return True
        else:
            return False

    @is_3d_placement.setter
    def is_3d_placement(self, value):
        props = ["NAME:3D Placement", "Value:=", value]
        self.change_property(props)

    @property
    def is_flipped(self):
        """Retrieve if the component is flipped or not."""
        if self._oeditor.GetPropertyValue("BaseElementTab", self.name, "Flipped").lower() == "true":
            return True
        else:
            return False

    @is_flipped.setter
    def is_flipped(self, value):
        props = ["NAME:Flipped", "Value:=", value]
        self.change_property(props)

    @property
    def rotation_axis(self):
        """Rotation axis around which the component is rotated."""
        if self.is_3d_placement:
            return self._oeditor.GetPropertyValue("BaseElementTab", self.name, "Rotation Axis")
        return False

    @rotation_axis.setter
    def rotation_axis(self, value):
        if self.is_3d_placement and value in ["X", "Y", "Z"]:
            props = ["NAME:Rotation Axis", "Value:=", value]
            self.change_property(props)

    @property
    def rotation_axis_direction(self):
        """Axis direction of the rotation."""
        if self.is_3d_placement:
            return [
                float(i)
                for i in self._oeditor.GetPropertyValue("BaseElementTab", self.name, "Rotation Axis Direction").split(
                    ","
                )
            ]
        return [0, 0, 1]

    @rotation_axis_direction.setter
    def rotation_axis_direction(self, value):
        if self.is_3d_placement:
            props = ["NAME:Rotation Axis Direction", "X:=", str(value[0]), "Y:=", str(value[1]), "Z:=", str(value[2])]
            self.change_property(props)

    @property
    def local_origin(self):
        """Retrieve if the component has 3d placement, the local origin.

        Returns
        -------
        list
            [x, y, z] position.
        """
        if self.is_3d_placement:
            return [i for i in self._oeditor.GetPropertyValue("BaseElementTab", self.name, "Local Origin").split(",")]
        return [0, 0, 0]

    @local_origin.setter
    def local_origin(self, value):
        if self.is_3d_placement:
            value = [self._primitives._app.value_with_units(i) for i in value]
            props = ["NAME:Local Origin", "X:=", value[0], "Y:=", value[1], "Z:=", value[2]]
            self.change_property(props)

    @property
    def location(self):
        """Retrieve/Set the absolute location in model units.
        Location is computed with combination of 3d Layout location and model center.

        Returns
        -------
        list
           List of ``(x, y)`` coordinates for the component location.

        References
        ----------
        >>> oEditor.GetPropertyValue
        """
        location = self._oeditor.GetPropertyValue("BaseElementTab", self.name, "Location").split(",")
        locs = []
        for i in location:
            try:
                locs.append(float(i))
            except ValueError:  # pragma: no cover
                locs.append(i)
        return locs

    @location.setter
    def location(self, position):
        props = [
            "NAME:Location",
            "X:=",
            self._primitives._app.value_with_units(position[0]),
            "Y:=",
            self._primitives._app.value_with_units(position[1]),
            "Z:=",
            (
                self._primitives._app.value_with_units(self.location[2])
                if len(position) < 3
                else self._primitives._app.value_with_units(position[2])
            ),
        ]
        self.change_property(props)


class Padstack(object):
    """Manages properties of a padstack.

    Parameters
    ----------
    name : str, optional
        Name of the padstack. The default is ``"Padstack"``.
    padstackmanager : optional
        The default is ``None``.
    units : str, optional
        The default is ``mm``.

    """

    def __init__(self, name="Padstack", padstackmanager=None, units="mm"):
        self.name = name
        self.padstackmgr = padstackmanager
        self.units = units
        self.lib = ""
        self.mat = "copper"
        self.plating = 100
        self.layers = {}
        self.hole = self.PDSHole()
        self.holerange = "UTL"
        self.solder_shape = "None"
        self.solder_placement = "abv"
        self.solder_rad = "0mm"
        self.sb2 = "0mm"
        self.solder_mat = "solder"
        self.layerid = 1

    class PDSHole(object):
        """Manages properties of a padstack hole.

        Parameters
        ----------
        holetype : str, optional
            Type of the hole. The default is ``Circular``.
        sizes : str, optional
            Diameter of the hole with units. The default is ``"1mm"``.
        xpos : str, optional
            The default is ``"0mm"``.
        ypos : str, optional
            The default is ``"0mm"``.
        rot : str, optional
            Rotation in degrees. The default is ``"0deg"``.

        """

        def __init__(self, holetype="Cir", sizes=["1mm"], xpos="0mm", ypos="0mm", rot="0deg"):
            self.shape = holetype
            self.sizes = sizes
            self.x = xpos
            self.y = ypos
            self.rot = rot

    class PDSLayer(object):
        """Manages properties of a padstack layer."""

        def __init__(self, layername="Default", id=1):
            self.layername = layername
            self.id = id
            self._pad = None
            self._antipad = None
            self._thermal = None
            self.connectionx = 0
            self.connectiony = 0
            self.connectiondir = 0

        @property
        def pad(self):
            """Pad."""
            return self._pad

        @property
        def antipad(self):
            """Antipad."""
            return self._antipad

        @pad.setter
        def pad(self, value=None):
            if value:
                self._pad = value
            else:
                self._pad = Padstack.PDSHole(holetype="None", sizes=[])

        @antipad.setter
        def antipad(self, value=None):
            if value:
                self._antipad = value
            else:
                self._antipad = Padstack.PDSHole(holetype="None", sizes=[])

        @property
        def thermal(self):
            """Thermal."""
            return self._thermal

        @thermal.setter
        def thermal(self, value=None):
            if value:
                self._thermal = value
            else:
                self._thermal = Padstack.PDSHole(holetype="None", sizes=[])

    @property
    def pads_args(self):
        """Pad properties."""
        arg = [
            "NAME:" + self.name,
            "ModTime:=",
            1594101963,
            "Library:=",
            "",
            "ModSinceLib:=",
            False,
            "LibLocation:=",
            "Project",
        ]
        arg2 = ["NAME:psd", "nam:=", self.name, "lib:=", "", "mat:=", self.mat, "plt:=", self.plating]
        arg3 = ["NAME:pds"]
        id_ = 0
        for el in self.layers:
            arg4 = []
            id_ += 1
            arg4.append("NAME:lgm")
            arg4.append("lay:=")
            arg4.append(self.layers[el].layername)
            arg4.append("id:=")
            arg4.append(id_)
            arg4.append("pad:=")
            arg4.append(
                [
                    "shp:=",
                    self.layers[el].pad.shape,
                    "Szs:=",
                    self.layers[el].pad.sizes,
                    "X:=",
                    self.layers[el].pad.x,
                    "Y:=",
                    self.layers[el].pad.y,
                    "R:=",
                    self.layers[el].pad.rot,
                ]
            )
            arg4.append("ant:=")
            arg4.append(
                [
                    "shp:=",
                    self.layers[el].antipad.shape,
                    "Szs:=",
                    self.layers[el].antipad.sizes,
                    "X:=",
                    self.layers[el].antipad.x,
                    "Y:=",
                    self.layers[el].antipad.y,
                    "R:=",
                    self.layers[el].antipad.rot,
                ]
            )
            arg4.append("thm:=")
            arg4.append(
                [
                    "shp:=",
                    self.layers[el].thermal.shape,
                    "Szs:=",
                    self.layers[el].thermal.sizes,
                    "X:=",
                    self.layers[el].thermal.x,
                    "Y:=",
                    self.layers[el].thermal.y,
                    "R:=",
                    self.layers[el].thermal.rot,
                ]
            )
            arg4.append("X:=")
            arg4.append(self.layers[el].connectionx)
            arg4.append("Y:=")
            arg4.append(self.layers[el].connectiony)
            arg4.append("dir:=")
            arg4.append(self.layers[el].connectiondir)
            arg3.append(arg4)
        arg2.append(arg3)
        arg2.append("hle:=")
        arg2.append(
            [
                "shp:=",
                self.hole.shape,
                "Szs:=",
                self.hole.sizes,
                "X:=",
                self.hole.x,
                "Y:=",
                self.hole.y,
                "R:=",
                self.hole.rot,
            ]
        )
        arg2.append("hRg:=")
        arg2.append(self.holerange)
        arg2.append("sbsh:=")
        arg2.append(self.solder_shape)
        arg2.append("sbpl:=")
        arg2.append(self.solder_placement)
        arg2.append("sbr:=")
        arg2.append(self.solder_rad)
        arg2.append("sb2:=")
        arg2.append(self.sb2)
        arg2.append("sbn:=")
        arg2.append(self.solder_mat)
        arg.append(arg2)
        arg.append("ppl:=")
        arg.append([])
        return arg

    @pyaedt_function_handler(layername="layer")
    def add_layer(
        self,
        layer="Start",
        pad_hole=None,
        antipad_hole=None,
        thermal_hole=None,
        connx=0,
        conny=0,
        conndir=0,
        layer_id=None,
    ):
        """Create a layer in the padstack.

        Parameters
        ----------
        layer : str, optional
            Name of layer. The default is ``"Start"``.
        pad_hole : ansys.aedt.core.modeler.Object3d.Object3d.PDSHole
            Pad hole object, which you can create with the :func:`add_hole` method.
            The default is ``None``.
        antipad_hole :
            Antipad hole object, which you can create with the :func:`add_hole` method.
            The default is ``None``.
        thermal_hole :
            Thermal hole object, which you can create with the :func:`add_hole` method.
            The default is ``None``.
        connx : optional
            Connection in the X-axis direction. The default is ``0.``
        conny : optional
            Connection in the Y-axis direction. The default is ``0.``
        conndir :
            Connection attach angle. The default is ``0.``

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        if layer in self.layers:
            return False
        else:
            if not layer_id:
                layer_id = len(list(self.layers.keys())) + 1
            new_layer = self.PDSLayer(layer, layer_id)
            new_layer.pad = pad_hole
            new_layer.antipad = antipad_hole
            new_layer.thermal = thermal_hole
            new_layer.connectionx = connx
            new_layer.connectiony = conny
            new_layer.connectiondir = conndir
            self.layers[layer] = new_layer
            return True

    @pyaedt_function_handler(holetype="hole_type", xpos="x", ypos="y", rot="rotation")
    def add_hole(self, hole_type="Cir", sizes=None, x=0, y=0, rotation=0):
        """Add a hole.

        Parameters
        ----------
        hole_type : str, optional
            Type of the hole. Options are:

            * No" - no pad
            * "Cir" - Circle
            * "Sq" - Square
            * "Rct" - Rectangle
            * "Ov" - Oval
            * "Blt" - Bullet
            * "Ply" - Polygons
            * "R45" - Round 45 thermal
            * "R90" - Round 90 thermal
            * "S45" - Square 45 thermal
            * "S90" - Square 90 thermal

            The default is ``"Cir"``.
        sizes : array, optional
            Array of sizes, which depends on the object. For example, a circle ias an array
            of one element. The default is ``[1]``.
        x :
            Position on the X axis. The default is ``0``.
        y :
            Position on the Y axis. The default is ``0``.
        rotation : float, optional
            Angle rotation in degrees. The default is ``0``.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.Object3d.Object3d.PDSHole`
            Hole object to be passed to padstack or layer.

        """
        if sizes is None:
            sizes = [1]
        hole = self.PDSHole()
        hole.shape = hole_type
        sizes = [_arg_with_dim(i, self.units) for i in sizes if type(i) is int or float]
        hole.sizes = sizes
        hole.x = _arg_with_dim(x, self.units)
        hole.y = _arg_with_dim(y, self.units)
        hole.rot = _arg_with_dim(rotation, "deg")
        return hole

    @pyaedt_function_handler()
    def create(self):
        """Create a padstack in AEDT.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oPadstackManager.Add

        """
        self.padstackmgr.Add(self.pads_args)
        return True

    @pyaedt_function_handler()
    def update(self):
        """Update the padstack in AEDT.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oPadstackManager.Edit

        """
        self.padstackmgr.Edit(self.name, self.pads_args)

    @pyaedt_function_handler()
    def remove(self):
        """Remove the padstack in AEDT.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oPadstackManager.Remove

        """
        self.padstackmgr.Remove(self.name, True, "", "Project")
