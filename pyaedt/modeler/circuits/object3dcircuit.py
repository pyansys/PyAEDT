# -*- coding: utf-8 -*-
from __future__ import absolute_import

from collections import OrderedDict
import math

from pyaedt import pyaedt_function_handler
from pyaedt.application.Variables import decompose_variable_value
from pyaedt.generic.constants import AEDT_UNITS
from pyaedt.generic.general_methods import _arg2dict, _dim_arg
from pyaedt.modeler.cad.elements3d import _dict2arg
from pyaedt.modeler.geometry_operators import GeometryOperators as go


class CircuitPins(object):
    """Manages circuit component pins."""

    def __init__(self, circuit_comp, pinname):
        self._circuit_comp = circuit_comp
        self.name = pinname
        self._oeditor = circuit_comp._oeditor

    @property
    def units(self):
        """Length units."""
        return self._circuit_comp.units

    @property
    def location(self):
        """Pin Position in [x,y] format.

        References
        ----------
        >>> oPadstackManager.GetComponentPinLocation
        """
        if "Port" in self._circuit_comp.composed_name:
            pos1 = self._oeditor.GetPropertyValue(
                "BaseElementTab",
                self._circuit_comp.composed_name,
                "Component Location",
            )
            if isinstance(pos1, str):
                pos1 = pos1.split(", ")
                pos1 = [float(i.strip()[:-3]) * 0.0000254 for i in pos1]
                if "GPort" in self._circuit_comp.composed_name:
                    pos1[1] += 0.00254
                pos1 = [round(i / AEDT_UNITS["Length"][self.units], 8) for i in pos1]
                return pos1
            return []
        return [
            round(
                self._oeditor.GetComponentPinLocation(self._circuit_comp.composed_name, self.name, True)
                / AEDT_UNITS["Length"][self.units],
                8,
            ),
            round(
                self._oeditor.GetComponentPinLocation(self._circuit_comp.composed_name, self.name, False)
                / AEDT_UNITS["Length"][self.units],
                8,
            ),
        ]

    @property
    def net(self):
        """Get pin net."""
        if "PagePort@" in self.name:
            return self._circuit_comp.name.split("@")[1]
        for net in self._circuit_comp._circuit_components.nets:
            conns = self._oeditor.GetNetConnections(net)
            for conn in conns:
                if conn.endswith(self.name) and (
                    ";{};".format(self._circuit_comp.id) in conn or ";{} ".format(self._circuit_comp.id) in conn
                ):
                    return net
        return ""

    @property
    def angle(self):
        """Pin angle."""
        props = list(self._oeditor.GetComponentPinInfo(self._circuit_comp.composed_name, self.name))
        for i in props:
            if "Angle=" in i:
                return round(float(i[6:]))
        return 0.0

    @staticmethod
    def _is_inside_point(plist, pa, pb):
        for p in plist:
            if pa < p < pb or pa > p > pb:
                return True
        return False

    def _add_point(
        self,
        pins,
        points,
        delta,
        target,
    ):
        inside = False
        pa = points[-1] + [0]
        pb = target + [0]
        for pin in pins:
            if go.is_between_points(pin, pa, pb):
                inside = True
        if not inside:
            points.append(target)
        elif pa[0] == pb[0]:
            deltax = target[0] + delta
            points.append([deltax, points[-1][1]])
            points.append([deltax, target[1]])
        else:
            deltay = target[1] + delta
            points.append([points[-1][0], deltay])
            points.append([target[0], deltay])

    def _get_deltas(self, point, move_x=True, move_y=True, positive=True, units=1):
        if positive:
            delta = +units * 0.00254 / AEDT_UNITS["Length"][self._circuit_comp._circuit_components.schematic_units]
        else:
            delta = -units * 0.00254 / AEDT_UNITS["Length"][self._circuit_comp._circuit_components.schematic_units]
        if move_x:
            deltax = point[0] + delta
        else:
            deltax = point[0]
        if move_y:
            deltay = point[1] + delta
        else:
            deltay = point[1]
        return deltax, deltay

    @pyaedt_function_handler()
    def connect_to_component(self, component_pin, page_name=None, use_wire=False, wire_name="", clearance_units=1):
        """Connect schematic components.

        Parameters
        ----------
        component_pin : :class:`pyaedt.modeler.circuits.PrimitivesNexxim.CircuitPins`
           Component pin to attach.
        page_name : str, optional
            Page port name. The default value is ``None``, in which case
            a name is automatically generated.
        use_wire : bool, optional
            Whether to use wires or a page port to connect the pins.
            The default is ``False``, in which case a page port is used. Note
            that if wires are used but not well placed, shorts can result.
        wire_name : str, optional
            Wire name used only when user_wire is ``True``. Default value is ``""``.
        clearance_units : int, optional
            Number of snap units (100mil each) around the object to overcome pins and wires.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oPadstackManager.CreatePagePort
        """
        tol = 1e-8
        if not isinstance(component_pin, list):
            component_pin = [component_pin]
        if use_wire:
            direction = (180 + self.angle + self._circuit_comp.angle) * math.pi / 180
            points = [self.location]
            cangles = [self._circuit_comp.angle]
            negative = 0.0 >= direction >= (math.pi)
            for cpin in component_pin:
                prev = [i for i in points[-1]]
                act = [i for i in cpin.location]
                pins_x = [i.location[0] for i in self._circuit_comp.pins if i.name != self.name]
                pins_x += [i.location[0] for i in cpin._circuit_comp.pins if i.name != cpin.name]
                pins_y = [i.location[1] for i in self._circuit_comp.pins if i.name != self.name]
                pins_y += [i.location[1] for i in cpin._circuit_comp.pins if i.name != cpin.name]
                pins = [[i, j, 0] for i, j in zip(pins_x, pins_y)]
                delta, _ = self._get_deltas([0, 0], move_y=False, positive=not negative, units=clearance_units)
                if abs(points[-1][0] - cpin.location[0]) < tol:
                    dx = round((prev[0] + act[0]) / 2, -2)

                    self._add_point(pins, points, delta, act)
                    if points[-1][0] != act[0] and points[-1][1] != act[1]:
                        points.append([points[-1][0], act[1]])
                        points.append(act)
                    if points[-1][0] != act[0] or points[-1][1] != act[1]:
                        points.append(act)

                elif abs(points[-1][1] - cpin.location[1]) < tol:
                    dy = round((prev[1] + act[1]) / 2, -2)
                    self._add_point(pins, points, delta, act)
                    if points[-1][0] != act[0] and points[-1][1] != act[1]:
                        points.append([act[0], points[-1][1]])
                        points.append(act)
                    if points[-1][0] != act[0] or points[-1][1] != act[1]:
                        points.append(act)

                elif cangles[-1] in [0.0, 180.0]:
                    dx = round((prev[0] + act[0]) / 2, -2)
                    p2 = act[1]

                    self._add_point(
                        pins,
                        points,
                        delta,
                        [prev[0], p2],
                    )
                    p2 = points[-1][1]

                    self._add_point(pins, points, delta, [dx, p2])
                    if points[-1][0] != dx:
                        dx = points[-1][0]

                    if p2 == act[1]:
                        self._add_point(pins, points, delta, [act[0], p2])
                    else:
                        points.append([act[0], p2])
                    if points[-1][0] != act[0] or points[-1][1] != act[1]:
                        points.append(act)

                else:
                    dy = round((prev[1] + act[1]) / 2, -2)
                    p1 = act[0]
                    self._add_point(pins, points, delta, [p1, prev[1]])
                    p1 = points[-1][0]

                    self._add_point(
                        pins,
                        points,
                        delta,
                        [act[0], dy],
                    )
                    if points[-1][1] != dy:
                        dy = points[-1][0]

                    if p1 == act[0]:
                        self._add_point(pins, points, delta, [p1, act[1]])
                    else:
                        points.append([p1, act[1]])
                    if points[-1][0] != act[0] or points[-1][1] != act[1]:
                        points.append(act)

                cangles.append(cpin._circuit_comp.angle)
            self._circuit_comp._circuit_components.create_wire(points, wire_name=wire_name)
            return True
        comp_angle = self._circuit_comp.angle * math.pi / 180
        if len(self._circuit_comp.pins) == 2:
            comp_angle += math.pi / 2
        if page_name is None:
            page_name = "{}_{}".format(
                self._circuit_comp.composed_name.replace("CompInst@", "").replace(";", "_"), self.name
            )

        if "Port" in self._circuit_comp.composed_name:
            try:
                page_name = self._circuit_comp.name.split("@")[1].replace(";", "_")
            except:
                pass
        else:
            for cmp in component_pin:
                if "Port" in cmp._circuit_comp.composed_name:
                    try:
                        page_name = cmp._circuit_comp.name.split("@")[1].replace(";", "_")
                        break
                    except:
                        continue
        try:
            x_loc = AEDT_UNITS["Length"][decompose_variable_value(self._circuit_comp.location[0])[1]] * float(
                decompose_variable_value(self._circuit_comp.location[1])[0]
            )
        except:
            x_loc = float(self._circuit_comp.location[0])
        if self.location[0] < x_loc:
            angle = comp_angle
        else:
            angle = math.pi + comp_angle
        ret1 = self._circuit_comp._circuit_components.create_page_port(page_name, self.location, angle=angle)
        for cmp in component_pin:
            try:
                x_loc = AEDT_UNITS["Length"][decompose_variable_value(cmp._circuit_comp.location[0])[1]] * float(
                    decompose_variable_value(cmp._circuit_comp.location[0])[0]
                )
            except:
                x_loc = float(cmp._circuit_comp.location[0])
            comp_pin_angle = cmp._circuit_comp.angle * math.pi / 180
            if len(cmp._circuit_comp.pins) == 2:
                comp_pin_angle += math.pi / 2
            if cmp.location[0] < x_loc:
                angle = comp_pin_angle
            else:
                angle = math.pi + comp_pin_angle
            ret2 = self._circuit_comp._circuit_components.create_page_port(
                page_name, location=cmp.location, angle=angle
            )
        if ret1 and ret2:
            return True
        else:
            return False


class ComponentParameters(dict):
    """Manages component parameters."""

    def __setitem__(self, key, value):
        try:
            self._component._oeditor.SetPropertyValue(self._tab, self._component.composed_name, key, str(value))
            dict.__setitem__(self, key, value)
        except:
            try:
                self._component._oeditor.ChangeProperty(
                    [
                        "NAME:AllTabs",
                        [
                            "NAME:" + self._tab,
                            ["NAME:PropServers", self._component.composed_name],
                            ["NAME:ChangedProps", ["NAME:" + key, "ButtonText:=", str(value)]],
                        ],
                    ]
                )
                dict.__setitem__(self, key, value)
            except:
                self._component._circuit_components.logger.warning(
                    "Property %s has not been edited.Check if readonly", key
                )

    def __init__(self, component, tab, *args, **kw):
        dict.__init__(self, *args, **kw)
        self._component = component
        self._tab = tab


class ModelParameters(object):
    """Manages model parameters."""

    def update(self):
        """Update the model properties.

        Returns
        -------
        bool
        """
        try:
            a = OrderedDict({})
            a[self.name] = self.props
            arg = ["NAME:" + self.name]
            _dict2arg(self.props, arg)
            self._component._circuit_components.o_model_manager.EditWithComps(self.name, arg, [])
            return True
        except:
            self._component._circuit_components.logger.warning("Failed to update model %s ", self.name)
            return False

    def __init__(self, component, name, props):
        self.props = props
        self._component = component
        self.name = name


class CircuitComponent(object):
    """Manages circuit components."""

    @property
    def composed_name(self):
        """Composed names."""
        if self.id:
            return self.name + ";" + str(self.id) + ";" + str(self.schematic_id)
        else:
            return self.name + ";" + str(self.schematic_id)

    def __init__(self, circuit_components, tabname="PassedParameterTab", custom_editor=None):
        self.name = ""
        self._circuit_components = circuit_components
        if custom_editor:
            self._oeditor = custom_editor
        else:
            self._oeditor = self._circuit_components.oeditor
        self._modelName = None
        self.status = "Active"
        self.component = None
        self.id = 0
        self.schematic_id = 0
        self.levels = 0.1
        self._angle = None
        self._location = []
        self._mirror = None
        self.usesymbolcolor = True
        self.tabname = tabname
        self.InstanceName = None
        self._pins = None
        self._parameters = {}
        self._component_info = {}
        self._model_data = {}

    @property
    def refdes(self):
        """Reference designator."""
        try:
            return self._oeditor.GetPropertyValue("Component", self.composed_name, "RefDes")
        except:
            return ""

    @property
    def units(self):
        """Length units."""
        return self._circuit_components.schematic_units

    @property
    def _property_data(self):
        """Property Data List."""
        try:
            return list(self._circuit_components.o_component_manager.GetData(self.name.split("@")[1]))
        except:
            return []

    @property
    def model_name(self):
        """Return Model Name if present.

        Returns
        -------
        str
        """
        if self._property_data and "ModelDefName:=" in self._property_data:
            return self._property_data[self._property_data.index("ModelDefName:=") + 1]
        return None

    @property
    def model_data(self):
        """Return the model data if the component has one.

        Returns
        -------
        :class:`pyaedt.modeler.Object3d.ModelParameters`
        """
        """Return the model data if the component has one.
        """
        if self._model_data:
            return self._model_data
        if self.model_name:
            _parameters = OrderedDict({})
            _arg2dict(list(self._circuit_components.o_model_manager.GetData(self.model_name)), _parameters)
            self._model_data = ModelParameters(self, self.model_name, _parameters[self.model_name])
        return self._model_data

    @property
    def parameters(self):
        """Circuit Parameters.

        References
        ----------
        >>> oEditor.GetProperties
        >>> oEditor.GetPropertyValue
        """
        if self._parameters:
            return self._parameters
        _parameters = {}
        if self._circuit_components._app.design_type == "Circuit Design":
            tab = "PassedParameterTab"
        elif self._circuit_components._app.design_type == "Maxwell Circuit":
            tab = "PassedParameterTab"
        else:
            tab = "Quantities"
        try:
            proparray = self._oeditor.GetProperties(tab, self.composed_name)
        except:
            proparray = []

        for j in proparray:
            propval = self._oeditor.GetPropertyValue(tab, self.composed_name, j)
            _parameters[j] = propval
        self._parameters = ComponentParameters(self, tab, _parameters)
        return self._parameters

    @property
    def component_info(self):
        """Component parameters.

        References
        ----------
        >>> oEditor.GetProperties
        >>> oEditor.GetPropertyValue
        """
        if self._component_info or self._circuit_components._app.design_type != "Circuit Design":
            return self._component_info
        _component_info = {}
        tab = "Component"
        proparray = self._oeditor.GetProperties(tab, self.composed_name)

        for j in proparray:
            propval = self._oeditor.GetPropertyValue(tab, self.composed_name, j)
            _component_info[j] = propval
        self._component_info = ComponentParameters(self, tab, _component_info)
        return self._component_info

    @property
    def bounding_box(self):
        """Component bounding box."""
        comp_info = self._oeditor.GetComponentInfo(self.composed_name)
        if not comp_info:
            if len(self.pins) == 1:
                return [
                    self.pins[0].location[0] - 0.00254 / AEDT_UNITS["Length"][self._circuit_components.schematic_units],
                    self.pins[0].location[-1]
                    + 0.00254 / AEDT_UNITS["Length"][self._circuit_components.schematic_units],
                    self.pins[0].location[0] + 0.00254 / AEDT_UNITS["Length"][self._circuit_components.schematic_units],
                    self.pins[0].location[1] + 0.00254 / AEDT_UNITS["Length"][self._circuit_components.schematic_units],
                ]
            return [0, 0, 0, 0]
        i = 0
        for cp in comp_info:
            if "BBoxLLx" in cp:
                break
            i += 1
        bounding_box = [
            float(comp_info[i][8:]),
            float(comp_info[i + 1][8:]),
            float(comp_info[i + 2][8:]),
            float(comp_info[i + 3][8:]),
        ]
        return [i / AEDT_UNITS["Length"][self._circuit_components.schematic_units] for i in bounding_box]

    @property
    def pins(self):
        """Pins of the component.

        Returns
        -------
        list of :class:`pyaedt.modeler.Object3d.CircuitPins`

        """
        if self._pins:
            return self._pins
        self._pins = []

        try:
            pins = list(self._oeditor.GetComponentPins(self.composed_name))
            if "Port@" in self.composed_name and pins == []:
                self._pins.append(CircuitPins(self, self.composed_name))
                return self._pins
            elif not pins:
                return []
            for pin in pins:
                if self._circuit_components._app.design_type != "Twin Builder":
                    self._pins.append(CircuitPins(self, pin))
                elif pin not in list(self.parameters.keys()):
                    self._pins.append(CircuitPins(self, pin))
        except AttributeError:
            self._pins.append(CircuitPins(self, self.composed_name))
        return self._pins

    @property
    def location(self):
        """Get the part location.

        References
        ----------
        >>> oEditor.GetPropertyValue
        >>> oEditor.ChangeProperty
        """
        self._location = []
        try:
            loc = self._oeditor.GetPropertyValue("BaseElementTab", self.composed_name, "Component Location")
            loc = [loc.split(",")[0].strip(), loc.split(",")[1].strip()]
            loc = [decompose_variable_value(i) for i in loc]

            self._location = [
                round(i[0] * AEDT_UNITS["Length"][i[1]] / AEDT_UNITS["Length"][self.units], 10) for i in loc
            ]
        except:
            self._location = []
        return self._location

    @location.setter
    def location(self, location_xy):
        """Set the part location.

        Parameters
        ----------
        location_xy : list
            List of x and y coordinates. If float values are provided, the default units are used.
        """
        x, y = [
            int(i / AEDT_UNITS["Length"]["mil"]) for i in self._circuit_components._convert_point_to_meter(location_xy)
        ]
        x_location = _dim_arg(x, "mil")
        y_location = _dim_arg(y, "mil")

        vMaterial = ["NAME:Component Location", "X:=", x_location, "Y:=", y_location]
        self.change_property(vMaterial)

    @property
    def angle(self):
        """Get the part angle.

        References
        ----------
        >>> oEditor.GetPropertyValue
        >>> oEditor.ChangeProperty
        """
        comp_info = self._oeditor.GetComponentInfo(self.composed_name)
        self._angle = 0.0
        if comp_info:
            for info in comp_info:
                if "Angle=" in info:
                    self._angle = float(info[6:])
                    break
        return self._angle

    @angle.setter
    def angle(self, angle=None):
        """Set the part angle."""
        from pyaedt.generic.settings import settings

        if isinstance(angle, (float, int)):
            angle = int(angle)
            if angle not in [0, 90, 180, 270]:  # pragma: no cover
                self._circuit_components._app.logger.error("Supported angle values are 0,90,180,270.")
        self._angle = 0 if angle is None else angle
        if settings.aedt_version > "2023.2":  # pragma: no cover
            angle = _dim_arg(self._angle, "deg")
            vMaterial = ["NAME:Component Angle", "Value:=", angle]
            self.change_property(vMaterial)
        elif not self._circuit_components._app.desktop_class.is_grpc_api:
            if not angle:
                angle = str(self._angle) + "°"
            else:
                angle = _dim_arg(angle, "°")
            vMaterial = ["NAME:Component Angle", "Value:=", angle]
            self.change_property(vMaterial)
        else:
            self._circuit_components._app.logger.warning(
                "Grpc doesn't support angle settings because special characters are not supported."
            )

    @property
    def mirror(self):
        """Get the part mirror.

        References
        ----------
        >>> oEditor.GetPropertyValue
        >>> oEditor.ChangeProperty
        """
        if self._mirror is not None:
            return self._mirror
        try:
            self._mirror = (
                self._oeditor.GetPropertyValue("BaseElementTab", self.composed_name, "Component Mirror") == "true"
            )
        except:
            self._mirror = False
        return self._mirror

    @mirror.setter
    def mirror(self, mirror_value=True):
        """Mirror part.

        Parameters
        ----------
        mirror_value : bool
            Either to mirror the part. The default is ``True``.

        Returns
        -------

        """
        vMaterial = ["NAME:Component Mirror", "Value:=", mirror_value]
        self.change_property(vMaterial)

    @pyaedt_function_handler()
    def set_use_symbol_color(self, symbol_color=None):
        """Set symbol color usage.

        Parameters
        ----------
        symbol_color : bool, optional
            The default is ``None``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.ChangeProperty
        """
        if not symbol_color:
            symbol_color = self.usesymbolcolor
        vMaterial = ["NAME:Use Symbol Color", "Value:=", symbol_color]
        self.change_property(vMaterial)
        return True

    @pyaedt_function_handler()
    def set_color(self, R=255, G=128, B=0):
        """Set symbol color.

        Parameters
        ----------
        R : int, optional
            Red color value. The default is ``255``.
        G : int, optional
            Green color value. The default is ``128``.
        B : int, optional
            Blue color value. The default is ``0``

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.ChangeProperty
        """
        vMaterial = ["NAME:Component Color", "R:=", R, "G:=", G, "B:=", B]
        self.change_property(vMaterial)
        return True

    @pyaedt_function_handler()
    def set_property(self, property_name, property_value):
        """Set a part property.

        Parameters
        ----------
        property_name : str
            Name of the property.
        property_value :
            Value for the property.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.ChangeProperty
        """
        if type(property_name) is list:
            for p, v in zip(property_name, property_value):
                v_prop = ["NAME:" + p, "Value:=", v]
                self.change_property(v_prop)
                if self.__dict__.get("_parameters", None) and p in self.__dict__["_parameters"]:
                    self.__dict__["_parameters"][p] = v
                else:
                    self.__dict__[p] = v
        else:
            v_prop = ["NAME:" + property_name, "Value:=", property_value]
            self.change_property(v_prop)
            if self.__dict__.get("_parameters", None) and property_name in self.__dict__["_parameters"]:
                self.__dict__["_parameters"][property_name] = property_value
            elif self.__dict__.get("_component_info", None) and property_name in self.__dict__.get(
                "_component_info", None
            ):
                self.__dict__["_component_info"][property_name] = property_value
            else:
                self.__dict__[property_name] = property_value
        return True

    @pyaedt_function_handler()
    def _add_property(self, property_name, property_value):
        """Add a property.

        Parameters
        ----------
        property_name : str
            Name of the property.
        property_value :
            Value for the property.


        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        self.__dict__[property_name] = property_value
        return True

    @pyaedt_function_handler()
    def change_property(self, vPropChange, names_list=None):
        """Modify a property.

        Parameters
        ----------
        vPropChange :

        names_list : list, optional
             The default is ``None``.

        Returns
        -------
        bool

        References
        ----------
        >>> oEditor.GetPropertyValue
        >>> oEditor.ChangeProperty
        """
        vChangedProps = ["NAME:ChangedProps", vPropChange]
        if names_list:
            vPropServers = ["NAME:PropServers"]
            for el in names_list:
                vPropServers.append(el)
        else:
            vPropServers = ["NAME:PropServers", self.composed_name]
        tabname = None
        if vPropChange[0][5:] in self._oeditor.GetProperties(self.tabname, self.composed_name):
            tabname = self.tabname
        elif vPropChange[0][5:] in self._oeditor.GetProperties("PassedParameterTab", self.composed_name):
            tabname = "PassedParameterTab"
        elif vPropChange[0][5:] in self._oeditor.GetProperties("BaseElementTab", self.composed_name):
            tabname = "BaseElementTab"
        if tabname:
            vGeo3dlayout = ["NAME:" + tabname, vPropServers, vChangedProps]
            vOut = ["NAME:AllTabs", vGeo3dlayout]
            if "NAME:Component Location" in str(vChangedProps) and "PagePort" not in self.composed_name:
                self._oeditor.ChangeProperty(vOut)
            return self._oeditor.ChangeProperty(vOut)
        return False


class Wire(object):
    """Creates and manipulates a wire."""

    def __init__(self, modeler):
        self._app = modeler._app
        self._modeler = modeler
        self.name = ""
        self.id = 0
        self.points_in_segment = {}

    @property
    def _oeditor(self):
        return self._modeler.oeditor

    @property
    def logger(self):
        """Logger."""
        return self._app.logger

    @property
    def wires(self):
        """List of all schematic wires in the design."""
        wire_names = []
        for wire in self._oeditor.GetAllElements():
            if "Wire" in wire:
                wire_names.append(wire)
        return wire_names

    @pyaedt_function_handler()
    def display_wire_properties(self, wire_name="", property_to_display="NetName", visibility="Name", location="Top"):
        """Display wire properties.

        Parameters
        ----------
        wire_name : str, optional
            Wire name to display.
            Default value is ``""``.
        property_to_display : str, optional
            Property to display. Choices are: ``"NetName"``, ``"PinCount"``, ``"AlignMicrowavePorts"``,
            ``"SchematicID"``, ``"Segment0"``.
            Default value is ``"NetName"``.
        visibility : str, optional
            Visibility type. Choices are ``"Name"``, ``"Value"``, ``"Both"``, ``"Evaluated Value"``,
            ``"Evaluated Both"``.
            Default value is ``"Name"``.
        location : str, optional
            Wire name location. Choices are ``"Left"``, ``"Top"``, ``"Right"``, ``"Bottom"``, ``"Center"``.
            Default value is ``"Top"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        try:
            wire_exists = False
            for wire in self.wires:
                if wire_name == wire.split("@")[1].split(";")[0]:
                    wire_id = wire.split("@")[1].split(";")[1].split(":")[0]
                    wire_exists = True
                    break
                else:
                    continue
            if not wire_exists:
                raise ValueError("Invalid wire name provided.")

            self._oeditor.ChangeProperty(
                [
                    "NAME:AllTabs",
                    [
                        "NAME:PropDisplayPropTab",
                        ["NAME:PropServers", "Wire@{};{};{}".format(wire_name, wire_id, 1)],
                        [
                            "NAME:NewProps",
                            ["NAME:" + property_to_display, "Format:=", visibility, "Location:=", location],
                        ],
                    ],
                ]
            )
            return True
        except ValueError as e:
            self.logger.error(str(e))
            return False
