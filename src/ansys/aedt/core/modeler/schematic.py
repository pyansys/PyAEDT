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

import random
import sys
import warnings

from ansys.aedt.core.generic.constants import AEDT_UNITS
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.modeler.cad.modeler import Modeler
from ansys.aedt.core.modeler.circuits.object_3d_circuit import CircuitComponent
from ansys.aedt.core.modeler.circuits.object_3d_circuit import Wire

if (3, 7) < sys.version_info < (3, 13):
    from ansys.aedt.core.modeler.circuits.primitives_emit import EmitComponent
    from ansys.aedt.core.modeler.circuits.primitives_emit import EmitComponents
else:  # pragma: no cover
    warnings.warn("EMIT API is only available for Python 3.8-3.12.")

from ansys.aedt.core.modeler.circuits.primitives_maxwell_circuit import MaxwellCircuitComponents
from ansys.aedt.core.modeler.circuits.primitives_nexxim import NexximComponents
from ansys.aedt.core.modeler.circuits.primitives_twin_builder import TwinBuilderComponents
from ansys.aedt.core.modeler.pcb.primitives_3d_layout import Primitives3DLayout
from ansys.aedt.core.modules.layer_stackup import Layers


class ModelerCircuit(Modeler):
    """ModelerCircuit class.

    Parameters
    ----------
    app : :class:`ansys.aedt.core.application.analysis_nexxim.FieldAnalysisCircuit`

    Examples
    --------
    >>> from ansys.aedt.core import Circuit
    >>> app = Circuit()
    >>> my_modeler = app.modeler
    """

    def __init__(self, app):
        app.logger.reset_timer()
        self._app = app
        self._schematic_units = "meter"
        Modeler.__init__(self, app)
        self.wire = Wire(self)
        app.logger.info_timer("ModelerCircuit class has been initialized!")

    @property
    def o_def_manager(self):
        """AEDT Definition manager."""
        return self._app.odefinition_manager

    @property
    def schematic_units(self):
        """Schematic units.

        Options are ``"mm"``, ``"mil"``, ``"cm"`` and all other metric and imperial units.
        The default is ``"meter"``.
        """
        return self._schematic_units

    @schematic_units.setter
    def schematic_units(self, value):
        if value in list(AEDT_UNITS["Length"].keys()):
            self._schematic_units = value
        else:
            self.logger.error("The unit %s is not supported.", value)

    @property
    def o_component_manager(self):
        """Component manager object."""
        return self._app.o_component_manager

    @property
    def o_model_manager(self):
        """Model manager object."""
        return self._app.o_model_manager

    @property
    def oeditor(self):
        """Oeditor Module.

        References
        ----------
        >>> oEditor = oDesign.SetActiveEditor("SchematicEditor")"""
        return self._app.oeditor

    @pyaedt_function_handler()
    def zoom_to_fit(self):
        """Zoom To Fit.

        References
        ----------
        >>> oEditor.ZoomToFit
        """
        self.oeditor.ZoomToFit()

    @pyaedt_function_handler(
        firstcomponent="starting_component",
        secondcomponent="ending_component",
        pinnum_first="pin_starting",
        pinnum_second="pin_ending",
    )
    def connect_schematic_components(
        self, starting_component, ending_component, pin_starting=2, pin_ending=1, use_wire=True
    ):
        """Connect schematic components.

        Parameters
        ----------
        starting_component : str
           Starting (right) component.
        ending_component : str
           Ending (left) component for the connection line.
        pin_starting : int, str, list optional
             Number or name of the pins at which to terminate the connection from the right end of the
             starting component. The default is ``2``.
        pin_ending : int, str, list optional
             Number or name of the pins at which to terminate the connection from the left end of the
             ending component. The default is ``1``.
        use_wire : bool, optional
            Whether to use wires or a page port to connect the pins.
            The default is ``True``, in which case wires are used. Note
            that if wires are not well placed, shorts can result.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.CreateWire
        """
        if self._app.design_type == "Maxwell Circuit":
            components = self.schematic.components
        else:
            components = self.components
        start = components[starting_component]
        end = components[ending_component]
        if isinstance(pin_starting, (int, str)):
            pin_starting = [pin_starting]
        if isinstance(pin_ending, (int, str)):
            pin_ending = [pin_ending]
        for pstart, pend in zip(pin_starting, pin_ending):
            try:
                start[pstart].connect_to_component(end[pend], use_wire=use_wire)
            except Exception:
                self.logger.error(f"Failed to connect pin {pstart} with {pend}")
                return False
        return True

    @pyaedt_function_handler()
    def create_text(
        self,
        text,
        x_origin=0,
        y_origin=0,
        text_size=12,
        text_angle=0,
        text_color=0,
        show_rect=False,
        x1=0,
        y1=0,
        x2=0,
        y2=0,
        rect_line_width=0,
        rect_border_color=0,
        rect_fill=0,
        rect_color=0,
    ):
        """Draw Text.

        Parameters
        ----------
        text : string
            Text to display.
        x_origin : float, optional
            x origin coordinate of the text box.
            Default value is ``0``.
        y_origin : float, optional
            y origin coordinate of the text box .
            Default value is ``0``.
        text_size : int, optional
            Size of text.
            Default value is ``12``.
        text_angle : float, optional
            Angle of text.
            Default value is ``0``.
        text_color : int, optional
            The RGB value of the text color.
            Default value is ``0``.
        show_rect : bool, optional
            Show rectangle.
            Default value is ``False``.
        x1 : float, optional
            The text rectangle left X value, in meters.
            Default value is ``0``.
        y1 : float, optional
            The text rectangle upper Y value, in meters.
            Default value is ``0``.
        x2 : float, optional
            The text rectangle right X value, in meters.
            Default value is ``0``.
        y2 : float, optional
            The text rectangle lower Y value, in meters.
            Default value is ``0``.
        rect_line_width : float, optional
            The width of the rectangle border, in meters.
            Default value is ``0``.
        rect_border_color : int, optional
            The RGB value of the rectangle border color.
            Default value is ``0``.
        rect_fill : int, optional
            The rectangle fill pattern id.
            Available values are: 0 = hollow, 1 = solid, 2 = NEDiagonal, 3 = OrthoCross,
            4 = DiagCross, 5 = NWDiagonal, 6 = Horizontal, 7 = Vertical.
            Default value is ``0``.
        rect_color : int, optional
            The RGB value of the rectangle fill color.
            Default value is ``0``.


        Returns
        -------
        str
             Unique id of the created object when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.CreateText

        """
        fill = {
            0: "Hollow",
            1: "Solid",
            2: "NE Diagonal",
            3: "Orthogonal Cross",
            4: "Diagonal Cross",
            5: "NW Diagonal",
            6: "Horizontal",
            7: "Vertical",
        }
        x_origin, y_origin = self.schematic._convert_point_to_meter([x_origin, y_origin])
        x1, y1 = self.schematic._convert_point_to_meter([x1, y1])
        x2, y2 = self.schematic._convert_point_to_meter([x2, y2])

        element_ids = []
        for el in self.oeditor.GetAllGraphics():
            element_ids.append(int(el.split("@")[1]))
        system_random = random.SystemRandom()
        text_id = system_random.randint(20000, 23000)
        while text_id in element_ids:
            text_id = system_random.randint(20000, 23000)
        args = [
            "NAME:TextData",
            "X:=",
            x_origin,
            "Y:=",
            y_origin,
            "Size:=",
            12,
            "Angle:=",
            0,
            "Text:=",
            text,
            "Color:=",
            0,
            "Id:=",
            text_id,
            "ShowRect:=",
            show_rect,
            "X1:=",
            x1,
            "Y1:=",
            y1,
            "X2:=",
            x2,
            "Y2:=",
            y2,
            "RectLineWidth:=",
            0,
            "RectBorderColor:=",
            0,
            "RectFill:=",
            0,
            "RectColor:=",
            0,
        ]
        a = ["NAME:Attributes", "Page:=", 1]
        try:
            text_out = self.oeditor.CreateText(args, a)
            if isinstance(text_color, (tuple, list)):
                r, g, b = text_color
            else:
                r = (text_color >> 16) & 0xFF
                g = (text_color >> 8) & 0xFF
                b = (text_color >> 0) & 0xFF
            if isinstance(rect_color, (tuple, list)):
                r2, g2, b2 = rect_color
            else:
                r2 = (rect_color >> 16) & 0xFF
                g2 = (rect_color >> 8) & 0xFF
                b2 = (rect_color >> 0) & 0xFF
            if isinstance(rect_border_color, (tuple, list)):
                r3, g3, b3 = rect_border_color
            else:
                r3 = (rect_border_color >> 16) & 0xFF
                g3 = (rect_border_color >> 8) & 0xFF
                b3 = (rect_border_color >> 0) & 0xFF
            self.change_text_property(str(text_id), "Color", [r, g, b])
            self.change_text_property(str(text_id), "Angle", self._arg_with_dim(text_angle, "deg"))
            self.change_text_property(str(text_id), "DisplayRectangle", show_rect)
            if show_rect:
                self.change_text_property(str(text_id), "Rectangle Color", [r2, g2, b2])
                self.change_text_property(
                    str(text_id), "Rectangle BorderWidth", self._arg_with_dim(rect_line_width, "mil")
                )
                self.change_text_property(str(text_id), "Rectangle BorderColor", [r3, g3, b3])
                self.change_text_property(str(text_id), "Rectangle FillStyle", fill[rect_fill])
            return text_out
        except Exception:
            return False

    @pyaedt_function_handler(property_id="assignment", property_name="name", property_value="value")
    def change_text_property(self, assignment, name, value):
        """Change an oeditor property.

        Parameters
        ----------
        assignment : str
            Object id.
        name : str
            Name of the property. For example, ``Text``.
        value : str, list, int
            Value of the property. It can be a string, an int for a single value, a list of three elements for
            ``[r,g,b]`` color values or a list of two elements for ``[x, y]`` coordinates.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.ChangeProperty
        """
        graphics_id = [id.split("@")[1] for id in self.oeditor.GetAllGraphics()]
        if assignment not in graphics_id:
            self.logger.error("Invalid id.")
            return False
        if isinstance(value, list) and len(value) == 3:
            if not isinstance(value[0], int) or not isinstance(value[1], int) or not isinstance(value[2], int):
                self.logger.error("Invalid RGB values for color")
                return False
            self.oeditor.ChangeProperty(
                [
                    "NAME:AllTabs",
                    [
                        "NAME:BaseElementTab",
                        ["NAME:PropServers", "SchObj@" + assignment],
                        [
                            "NAME:ChangedProps",
                            [
                                "NAME:" + name,
                                "R:=",
                                value[0],
                                "G:=",
                                value[1],
                                "B:=",
                                value[2],
                            ],
                        ],
                    ],
                ]
            )
        elif isinstance(value, list) and len(value) == 2:
            xpos = self._arg_with_dim(value[0])
            ypos = self._arg_with_dim(value[1])
            self.oeditor.ChangeProperty(
                [
                    "NAME:AllTabs",
                    [
                        "NAME:BaseElementTab",
                        ["NAME:PropServers", "SchObj@" + assignment],
                        ["NAME:ChangedProps", ["NAME:" + name, "X:=", xpos, "Y:=", ypos]],
                    ],
                ]
            )
        elif isinstance(value, bool):
            self.oeditor.ChangeProperty(
                [
                    "NAME:AllTabs",
                    [
                        "NAME:BaseElementTab",
                        ["NAME:PropServers", "SchObj@" + assignment],
                        ["NAME:ChangedProps", ["NAME:" + name, "Value:=", value]],
                    ],
                ]
            )
        elif isinstance(value, (str, float, int)):
            self.oeditor.ChangeProperty(
                [
                    "NAME:AllTabs",
                    [
                        "NAME:BaseElementTab",
                        ["NAME:PropServers", "SchObj@" + assignment],
                        ["NAME:ChangedProps", ["NAME:" + name, "Value:=", value]],
                    ],
                ]
            )
        else:
            self.logger.error("Wrong Property Value")
            return False
        self.logger.debug(f"Property {name} Changed correctly.")
        return True

    @pyaedt_function_handler()
    def _get_components_selections(self, selections, return_as_list=True):
        sels = []
        if not isinstance(selections, list):
            selections = [selections]
        for sel in selections:
            if isinstance(sel, int):
                sels.append(self.schematic.components[sel].composed_name)
            elif isinstance(sel, CircuitComponent):
                sels.append(sel.composed_name)
            else:
                for el in list(self.schematic.components.values()):
                    if sel in [el.InstanceName, el.composed_name, el.name]:
                        sels.append(el.composed_name)
        if not return_as_list:
            return ", ".join(sels)
        return sels

    @pyaedt_function_handler()
    def _arg_with_dim(self, value, units=None):
        if units is None:
            units = self.schematic_units
        if isinstance(value, str):
            try:
                float(value)
                val = f"{value}{units}"
            except Exception:
                val = value
        else:
            val = f"{value}{units}"
        return val


class ModelerNexxim(ModelerCircuit):
    """ModelerNexxim class.

    Parameters
    ----------
    app : :class:`ansys.aedt.core.application.analysis_nexxim.FieldAnalysisCircuit`

    """

    def __init__(self, app):
        self._app = app
        ModelerCircuit.__init__(self, app)
        self._schematic = NexximComponents(self)
        self._layouteditor = None
        self.layers = Layers(self, roughnessunits="um")
        self._primitives = Primitives3DLayout(app)
        self.logger.info("ModelerNexxim class has been initialized!")

    @property
    def layouteditor(self):
        """Return the Circuit Layout Editor.

        References
        ----------
        >>> oDesign.SetActiveEditor("Layout")
        """
        return self._app.layouteditor

    @property
    def schematic(self):
        """Schematic Component.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.circuits.primitives_nexxim.NexximComponents`
        """
        return self._schematic

    @property
    def components(self):
        """Schematic Component.

        .. deprecated:: 0.4.13
           Use :func:`Circuit.modeler.schematic` instead.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.circuits.primitives_nexxim.NexximComponents`
        """
        return self._schematic

    @property
    def pages(self):
        """Return the number of pages of the current schematic.

        Returns
        -------
        int
        """
        return self.oeditor.GetNumPages()

    @property
    def edb(self):
        """EDB.

        Returns
        -------
        :class:`ansys.aedt.core.Edb`
            edb_core object if it exists.

        """
        # TODO Check why it crashes when multiple circuits are created
        return None

    @property
    def model_units(self):
        """Layout model units.

        References
        ----------
        >>> oEditor.GetActiveUnits
        >>> oEditor.SetActiveUnits
        """
        return self._app.units.length

    @property
    def layout(self):
        """Primitives.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.primitives_3d_layout.Primitives3DLayout`

        """
        if self._app.design_type == "Twin Builder":
            return
        return self._primitives

    @property
    def primitives(self):
        """Primitives.

        .. deprecated:: 0.4.13
           Use :func:`Circuit.modeler.layout` instead.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.primitives_3d_layout.Primitives3DLayout`

        """
        return self._primitives

    @model_units.setter
    def model_units(self, units):
        """Set the model units as a string e.g. "mm"."""
        self._app.units.length = units

    @pyaedt_function_handler(selections="assignment", pos="offset")
    def move(self, assignment, offset, units=None):
        """Move the selections by the specified ``[x, y]`` coordinates.

        Parameters
        ----------
        assignment : list
            List of the selections.
        offset : list
            Offset for the ``[x, y]`` axis.
        units : str
            Units of the movement. The default is ``meter``. If ``None``, ``schematic_units`` are used.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.Move
        """
        sels = self._get_components_selections(assignment)
        if not sels:
            self.logger.error("No Component Found.")
            return False
        if units:
            x_location = AEDT_UNITS["Length"][units] * float(offset[0])
            y_location = AEDT_UNITS["Length"][units] * float(offset[1])
        else:
            x_location = AEDT_UNITS["Length"][self.schematic_units] * float(offset[0])
            y_location = AEDT_UNITS["Length"][self.schematic_units] * float(offset[1])
        self.oeditor.Move(
            ["NAME:Selections", "Selections:=", sels],
            [
                "NAME:MoveParameters",
                "xdelta:=",
                x_location,
                "ydelta:=",
                y_location,
                "Disconnect:=",
                False,
                "Rubberband:=",
                False,
            ],
        )
        return True

    @pyaedt_function_handler(selections="assignment")
    def rotate(self, assignment, degrees=90):
        """Rotate the selections by degrees.

        Parameters
        ----------
        assignment : list
            List of the selections.
        degrees : optional
            Angle rotation in degrees. The default is ``90``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.Rotate
        """
        sels = self._get_components_selections(assignment)
        if not sels:
            self.logger.error("No Component Found.")
            return False

        self.oeditor.Rotate(
            ["NAME:Selections", "Selections:=", sels],
            [
                "NAME:RotateParameters",
                "Degrees:=",
                degrees,
                "Disconnect:=",
                False,
                "Rubberband:=",
                False,
            ],
        )
        return True


class ModelerTwinBuilder(ModelerCircuit):
    """ModelerTwinBuilder class.

    Parameters
    ----------
    app : :class:`ansys.aedt.core.application.analysis_twin_builder.AnalysisTwinBuilder`

    """

    def __init__(self, app):
        self._app = app
        ModelerCircuit.__init__(self, app)
        self._components = TwinBuilderComponents(self)
        self.logger.info("ModelerTwinBuilder class has been initialized!")

    @property
    def components(self):
        """
        .. deprecated:: 0.4.13
           Use :func:`TwinBuilder.modeler.schematic` instead.

        """
        return self._components

    @property
    def schematic(self):
        """Schematic Object.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.primitivesTwinBuilder.TwinBuilderComponents`

        """
        return self._components


class ModelerEmit(ModelerCircuit):
    """ModelerEmit class.

    Parameters
    ----------
    app : :class:`ansys.aedt.core.application.analysis_emit`

    """

    def __init__(self, app):
        self._app = app
        ModelerCircuit.__init__(self, app)
        self.components = EmitComponents(app, self)
        self.logger.info("ModelerEmit class has been initialized!")

    @pyaedt_function_handler()
    def _get_components_selections(self, selections, return_as_list=True):  # pragma: no cover
        sels = []
        if not isinstance(selections, list):
            selections = [selections]
        for sel in selections:
            if isinstance(sel, int):
                sels.append(self.schematic.components[sel].composed_name)
            elif isinstance(sel, (CircuitComponent, EmitComponent)):
                sels.append(sel.composed_name)
            else:
                for el in list(self.schematic.components.values()):
                    if sel in [el.InstanceName, el.composed_name, el.name]:
                        sels.append(el.composed_name)
        if not return_as_list:
            return ", ".join(sels)
        return sels


class ModelerMaxwellCircuit(ModelerCircuit):
    """ModelerMaxwellCircuit class.

    Parameters
    ----------
    app : :class:`ansys.aedt.core.application.analysis_maxwell_circuit`

    """

    def __init__(self, app):
        self._app = app
        ModelerCircuit.__init__(self, app)
        self._components = MaxwellCircuitComponents(self)
        self.logger.info("ModelerMaxwellCircuit class has been initialized!")

    @property
    def schematic(self):
        """Schematic Object.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.primitivesMaxwellCircuit.MaxwellCircuitComponents`

        """
        return self._components
