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


import copy
import os

from ansys.aedt.core.generic.constants import LineStyle
from ansys.aedt.core.generic.constants import SymbolStyle
from ansys.aedt.core.generic.constants import TraceType
from ansys.aedt.core.generic.general_methods import generate_unique_name
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.generic.general_methods import write_configuration_file
from ansys.aedt.core.modeler.cad.elements_3d import BinaryTreeNode
from ansys.aedt.core.modeler.geometry_operators import GeometryOperators


class LimitLine(BinaryTreeNode):
    """Line Limit Management Class."""

    def __init__(self, report_setup, trace_name, oo=None):
        self._oo = oo
        self._oreport_setup = report_setup
        self.line_name = trace_name
        self.LINESTYLE = LineStyle()
        self._initialize_tree_node()

    @pyaedt_function_handler()
    def _initialize_tree_node(self):
        BinaryTreeNode.__init__(self, self.line_name, self._oo, False)
        return True

    @pyaedt_function_handler()
    def _change_property(self, props_value):
        self._oreport_setup.ChangeProperty(
            ["NAME:AllTabs", ["NAME:Limit Line", ["NAME:PropServers", self.line_name], props_value]]
        )
        return True

    @pyaedt_function_handler()
    def set_line_properties(
        self, style=None, width=None, hatch_above=None, violation_emphasis=None, hatch_pixels=None, color=None
    ):
        """Set trace properties.

        Parameters
        ----------
        style : str, optional
            Style for the limit line. The default is ``None``. You can also use
            the ``LIFESTYLE`` property.
        width : int, optional
            Width of the limit line. The default is ``None``.
        hatch_above : bool
           Whether the hatch is above the limit line. The default is ``None``.
        violation_emphasis : bool
            Whether to add violation emphasis. The default is ``None``.
        hatch_pixels : int
            Number of pixels for the hatch. The default is ``None``.
        color : tuple, list
            Trace color as a tuple (R,G,B) or a list of integers [0,255].
            The default is ``None``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        props = ["NAME:ChangedProps"]
        if style:
            props.append(["NAME:Line Style", "Value:=", style])
        if width and isinstance(width, (int, float, str)):
            props.append(["NAME:Line Width", "Value:=", str(width)])
        if hatch_above is not None and isinstance(hatch_pixels, (int, str)):
            props.append(["NAME:Hatch Above", "Value:=", hatch_above])
        if hatch_pixels and isinstance(hatch_pixels, (int, str)):
            props.append(["NAME:Hatch Pixels", "Value:=", str(hatch_pixels)])
        if violation_emphasis:
            props.append(["NAME:Violation Emphasis", "Value:=", violation_emphasis])
        if color and isinstance(color, (list, tuple)) and len(color) == 3:
            props.append(["NAME:Color", "R:=", color[0], "G:=", color[1], "B:=", color[2]])
        return self._change_property(props)


class Note(BinaryTreeNode):
    """Note Management Class."""

    def __init__(self, report_setup, plot_note_name, oo=None):
        self._oo = oo
        self._oreport_setup = report_setup
        self.plot_note_name = plot_note_name
        BinaryTreeNode.__init__(self, self.plot_note_name, self._oo, False)

    @pyaedt_function_handler()
    def _change_property(self, props_value):
        prop_server_name = self.plot_note_name
        self._oreport_setup.ChangeProperty(
            ["NAME:AllTabs", ["NAME:Note", ["NAME:PropServers", prop_server_name], props_value]]
        )
        return True

    @pyaedt_function_handler()
    def set_note_properties(
        self,
        text=None,
        back_color=None,
        background_visibility=None,
        border_color=None,
        border_visibility=None,
        border_width=None,
        font="Arial",
        font_size=12,
        italic=False,
        bold=False,
        color=(0, 0, 0),
    ):
        """Set note properties.

        Parameters
        ----------
        text : str, optional
            Style for the limit line. The default is ``None``. You can also use
            the ``LIFESTYLE`` property.
        back_color : int
            Background color specified as a tuple (R,G,B) or a list of integers [0,255].
            The default is ``None``.
        background_visibility : bool
            Whether to view background. The default is ``None``.
        border_color : int
            Trace color specified as a tuple (R,G,B) or a list of integers [0,255].
            The default is ``None``.
        border_visibility : bool
            Whether to view text border. The default is ``None``.
            The default is ``None``.
        border_width : int
            Text boarder width.
            The default is ``None``.
        font : str, optional
            The default is ``None``.
        font_size : int, optional
            The default is ``None``.
        italic : bool
            Whether the text is italic.
            The default is ``None``.
        bold : bool
            Whether the text is bold.
            The default is ``None``.
        color : int =(0, 0, 0)
            Trace color specified as a tuple (R,G,B) or a list of integers [0,255].
            The default is ``None``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        props = ["NAME:ChangedProps"]
        if text:
            props.append(["NAME:Note Text", "Value:=", text])
        if back_color and isinstance(back_color, (list, tuple)) and len(back_color) == 3:
            props.append(["NAME:Back Color", "R:=", back_color[0], "G:=", back_color[1], "B:=", back_color[2]])
        if background_visibility is not None:
            props.append(["NAME:Background Visibility", "Value:=", background_visibility])
        if border_color and isinstance(border_color, (list, tuple)) and len(border_color) == 3:
            props.append(["NAME:Border Color", "R:=", border_color[0], "G:=", border_color[1], "B:=", border_color[2]])
        if border_visibility is not None:
            props.append(["NAME:Border Visibility", "Value:=", border_visibility])
        if border_width and isinstance(border_width, (int, float)):
            props.append(["NAME:Border Width", "Value:=", str(border_width)])

        font_props = [
            "NAME:Note Font",
            "Height:=",
            -1 * font_size - 2,
            "Width:=",
            0,
            "Escapement:=",
            0,
            "Orientation:=",
            0,
            "Weight:=",
            700 if bold else 400,
            "Italic:=",
            255 if italic else 0,
            "Underline:=",
            0,
            "StrikeOut:=",
            0,
            "CharSet:=",
            0,
            "OutPrecision:=",
            3,
            "ClipPrecision:=",
            2,
            "Quality:=",
            1,
            "PitchAndFamily:=",
            34,
            "FaceName:=",
            font,
            "R:=",
            color[0],
            "G:=",
            color[1],
            "B:=",
            color[2],
        ]
        props.append(font_props)
        return self._change_property(props)


class Trace(BinaryTreeNode):
    """Provides trace management."""

    def __init__(
        self,
        report_setup,
        aedt_name,
        trace_name,
        oo=None,
    ):
        self._oo = oo
        self._oreport_setup = report_setup
        self.aedt_name = aedt_name
        self._name = trace_name
        self.LINESTYLE = LineStyle()
        self.TRACETYPE = TraceType()
        self.SYMBOLSTYLE = SymbolStyle()
        self._trace_style = None
        self._trace_width = None
        self._trace_color = None
        self._symbol_style = None
        self._show_arrows = None
        self._fill_symbol = None
        self._symbol_color = None
        self._show_symbol = False
        self._available_props = []
        self._initialize_tree_node()

    @pyaedt_function_handler()
    def _initialize_tree_node(self):
        BinaryTreeNode.__init__(self, self.aedt_name, self._oo, False)
        return True

    @property
    def curve_properties(self):
        """All curve graphical properties. It includes colors, trace and symbol settings.

        Returns
        -------
            :class:`ansys.aedt.core.modeler.cad.elements_3d.BinaryTree` when successful,
            ``False`` when failed.

        """
        if self.aedt_name.split(":")[-1] in self.children:
            return self.children[self.aedt_name.split(":")[-1]].properties
        return {}

    @property
    def name(self):
        """Trace name.

        Returns
        -------
        str
            Trace name.
        """
        return self._name

    @name.setter
    def name(self, value):
        report_name = self.aedt_name.split(":")[0]
        prop_name = report_name + ":" + self.name

        self._oreport_setup.ChangeProperty(
            [
                "NAME:AllTabs",
                [
                    "NAME:Trace",
                    ["NAME:PropServers", prop_name],
                    ["NAME:ChangedProps", ["NAME:Specify Name", "Value:=", True]],
                ],
            ]
        )
        self._oreport_setup.ChangeProperty(
            [
                "NAME:AllTabs",
                ["NAME:Trace", ["NAME:PropServers", prop_name], ["NAME:ChangedProps", ["NAME:Name", "Value:=", value]]],
            ]
        )
        self.aedt_name = self.aedt_name.replace(self.name, value)
        self.trace_name = value

    @pyaedt_function_handler()
    def _change_property(self, props_value):
        self._oreport_setup.ChangeProperty(
            ["NAME:AllTabs", ["NAME:Attributes", ["NAME:PropServers", self.aedt_name], props_value]]
        )
        return True

    @pyaedt_function_handler(trace_style="style")
    def set_trace_properties(self, style=None, width=None, trace_type=None, color=None):
        """Set trace properties.

        Parameters
        ----------
        style : str, optional
            Style for the trace line. The default is ``None``. You can also use
            the ``LINESTYLE`` property.
        width : int, optional
            Width of the trace line. The default is ``None``.
        trace_type : str
            Type of the trace line. The default is ``None``. You can also use the ``TRACETYPE``
            property.
        color : tuple, list
            Trace line color specified as a tuple (R,G,B) or a list of integers [0,255].
            The default is ``None``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        props = ["NAME:ChangedProps"]
        if style:
            props.append(["NAME:Line Style", "Value:=", style])
        if width and isinstance(width, (int, float, str)):
            props.append(["NAME:Line Width", "Value:=", str(width)])
        if trace_type:
            props.append(["NAME:Trace Type", "Value:=", trace_type])
        if color and isinstance(color, (list, tuple)) and len(color) == 3:
            props.append(["NAME:Color", "R:=", color[0], "G:=", color[1], "B:=", color[2]])
        return self._change_property(props)

    @pyaedt_function_handler()
    def set_symbol_properties(self, show=True, style=None, show_arrows=None, fill=None, color=None):
        """Set symbol properties.

        Parameters
        ----------
        show : bool, optional
            Whether to show the symbol. The default is ``True``.
        style : str, optional
           Style of the style. The default is ``None``. You can also use the ``SYMBOLSTYLE``
           property.
        show_arrows : bool, optional
            Whether to show arrows. The default is ``None``.
        fill : bool, optional
            Whether to fill the symbol with a color. The default is ``None``.
        color : tuple, list
            Symbol fill color specified as a tuple (R,G,B) or a list of integers [0,255].
            The default is ``None``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        props = ["NAME:ChangedProps", ["NAME:Show Symbol", "Value:=", show]]
        if style:
            props.append(["NAME:Symbol Style", "Value:=", style])
        if show_arrows:
            props.append(["NAME:Show Arrows", "Value:=", show_arrows])
        if fill:
            props.append(["NAME:Fill Symbol", "Value:=", fill])
        if color and isinstance(color, (list, tuple)) and len(color) == 3:
            props.append(["NAME:Symbol Color", "R:=", color[0], "G:=", color[1], "B:=", color[2]])
        return self._change_property(props)


class CommonReport(BinaryTreeNode):
    """Provides common reports."""

    def __init__(self, app, report_category, setup_name, expressions=None):
        self._post = app
        self._legacy_props = {}
        self._legacy_props["report_category"] = report_category
        self.setup = setup_name
        self._legacy_props["report_type"] = "Rectangular Plot"
        self._legacy_props["context"] = {}
        self._legacy_props["context"]["domain"] = "Sweep"
        self._legacy_props["context"]["primary_sweep"] = "Freq"
        self._legacy_props["context"]["primary_sweep_range"] = ["All"]
        self._legacy_props["context"]["secondary_sweep_range"] = ["All"]
        self._legacy_props["context"]["variations"] = {"Freq": ["All"]}
        if hasattr(self._post._app, "available_variations") and self._post._app.available_variations:
            nominal_variation = self._post._app.available_variations.get_independent_nominal_values()
            for el, k in nominal_variation.items():
                self._legacy_props["context"]["variations"][el] = k
        self._legacy_props["expressions"] = None
        self._legacy_props["plot_name"] = None
        if expressions:
            self.expressions = expressions
        self._is_created = False
        self.siwave_dc_category = 0
        self._traces = []
        self._initialize_tree_node()

    @pyaedt_function_handler()
    def _initialize_tree_node(self):
        if self._is_created:
            oo = self._post.oreportsetup.GetChildObject(self._legacy_props["plot_name"])
            if oo:
                BinaryTreeNode.__init__(self, self._legacy_props["plot_name"], oo, False)
                return True
        return False

    @property
    def __all_props(self):
        from ansys.aedt.core.modeler.cad.elements_3d import BinaryTreeNode

        try:
            oo = self._post.oreportsetup.GetChildObject(self._legacy_props["plot_name"])
            _child_object = BinaryTreeNode(self.plot_name, oo, False)
            for var in [i.split(" ,")[-1] for i in list(_child_object.properties.values())[4:]]:
                if var in _child_object.children:
                    del _child_object.children[var]
            els = [i for i in _child_object.children.keys() if i.startswith("LimitLine") or i.startswith("Note")]
            for var in els:
                del _child_object.children[var]
            return _child_object
        except Exception:
            return {}

    @pyaedt_function_handler()
    def delete(self):
        """Delete current report."""
        self._post.oreportsetup.DeleteReports([self.plot_name])
        for i in self._post.plots:
            if i.plot_name == self.plot_name:
                del i
                break
        return True

    @property
    def differential_pairs(self):
        """Differential pairs flag.

        Returns
        -------
        bool
            ``True`` when differential pairs is enabled, ``False`` otherwise.
        """
        return self._legacy_props["context"].get("differential_pairs", False)

    @differential_pairs.setter
    def differential_pairs(self, value):
        self._legacy_props["context"]["differential_pairs"] = value

    @property
    def matrix(self):
        """Maxwell 2D/3D or Q2D/Q3D matrix name.

        Returns
        -------
        str
            Matrix name.
        """
        if self._is_created and (
            self._post._app.design_type in ["Q3D Extractor", "2D Extractor"]
            or (
                self._post._app.design_type in ["Maxwell 2D", "Maxwell 3D"]
                and self._post._app.solution_type == "EddyCurrent"
            )
        ):
            try:
                if "Parameter" in self.traces[0].properties:
                    self._legacy_props["context"]["matrix"] = self.traces[0].properties["Parameter"]
                elif "Matrix" in self.traces[0].properties:
                    self._legacy_props["context"]["matrix"] = self.traces[0].properties["Matrix"]
            except Exception:
                self._post._app.logger.warning("Property `matrix` not found.")
        return self._legacy_props["context"].get("matrix", None)

    @matrix.setter
    def matrix(self, value):
        self._legacy_props["context"]["matrix"] = value

    @property
    def reduced_matrix(self):
        """Maxwell 2D/3D reduced matrix name for eddy current solvers.

        Returns
        -------
        str
            Reduced matrix name.
        """
        return self._legacy_props["context"].get("reduced_matrix", None)

    @reduced_matrix.setter
    def reduced_matrix(self, value):
        self._legacy_props["context"]["reduced_matrix"] = value

    @property
    def polyline(self):
        """Polyline name for the field report.

        Returns
        -------
        str
            Polyline name.
        """
        if self._is_created and self.report_category != "Far Fields" and self.report_category.endswith("Fields"):
            try:
                self._legacy_props["context"]["polyline"] = self.traces[0].properties["Geometry"]
            except Exception:
                self._post._app.logger.debug("Something went wrong while processing polyline.")
        return self._legacy_props["context"].get("polyline", None)

    @polyline.setter
    def polyline(self, value):
        self._legacy_props["context"]["polyline"] = value

    @property
    def expressions(self):
        """Expressions.

        Returns
        -------
        list
            Expressions.
        """
        self._initialize_tree_node()
        if self._is_created:
            return [i.split(" ,")[-1] for i in list(self.properties.values())[4:]]
        if self._legacy_props.get("expressions", None) is None:
            return []
        return [k.get("name", None) for k in self._legacy_props["expressions"] if k.get("name", None) is not None]

    @expressions.setter
    def expressions(self, value):
        if isinstance(value, dict):
            self._legacy_props["expressions"].append(value)
        elif isinstance(value, list):
            self._legacy_props["expressions"] = []
            for el in value:
                if isinstance(el, dict):
                    self._legacy_props["expressions"].append(el)
                else:
                    self._legacy_props["expressions"].append({"name": el})
        elif isinstance(value, str):
            if isinstance(self._legacy_props["expressions"], list):
                self._legacy_props["expressions"].append({"name": value})
            else:
                self._legacy_props["expressions"] = [{"name": value}]

    @property
    def report_category(self):
        """Report category.

        Returns
        -------
        str
            Report category.
        """
        if self._is_created:
            try:
                return self.properties["Report Type"]
            except Exception:
                return self._legacy_props["report_category"]
        return self._legacy_props["report_category"]

    @report_category.setter
    def report_category(self, value):
        if not self._is_created:
            self._legacy_props["report_category"] = value

    @property
    def report_type(self):
        """Report type. Options are ``"3D Polar Plot"``, ``"3D Spherical Plot"``,
        ``"Radiation Pattern"``, ``"Rectangular Plot"``, ``"Data Table"``,
        ``"Smith Chart"``, and ``"Rectangular Contour Plot"``.

        Returns
        -------
        str
            Report type.
        """
        if self._is_created:
            try:
                return self.properties["Display Type"]
            except Exception:
                return self._legacy_props["report_type"]
        return self._legacy_props["report_type"]

    @report_type.setter
    def report_type(self, report):
        if not self._is_created:
            self._legacy_props["report_type"] = report
            if not self.primary_sweep:
                if self._legacy_props["report_type"] in ["3D Polar Plot", "3D Spherical Plot"]:
                    self.primary_sweep = "Phi"
                    self.secondary_sweep = "Theta"
                elif self._legacy_props["report_type"] == "Radiation Pattern":
                    self.primary_sweep = "Phi"
                elif self.domain == "Sweep":
                    self.primary_sweep = "Freq"
                elif self.domain == "Time":
                    self.primary_sweep = "Time"

    @property
    def traces(self):
        """List of available traces in the report.

        .. note::
            This property works in version 2022 R1 and later. However, it works only in
            non-graphical mode in version 2022 R2 and later.

        Returns
        -------
        List of :class:`ansys.aedt.core.modules.report_templates.Trace`
        """
        _ = self.expressions[::]
        _traces = []
        try:
            oo = self._post.oreportsetup.GetChildObject(self.plot_name)
            oo_names = self._post.oreportsetup.GetChildObject(self.plot_name).GetChildNames()
        except Exception:
            return _traces
        for el in oo_names:
            if "Families" not in oo.GetChildObject(el).GetPropNames():
                continue
            try:
                oo1 = oo.GetChildObject(el)
                oo1_name = oo1.GetChildNames()
                if not oo1_name:
                    aedt_name = f"{self.plot_name}:{el}"
                    _traces.append(Trace(self._post.oreportsetup, aedt_name, el, oo1))
                else:
                    for i in oo1_name:
                        aedt_name = f"{self.plot_name}:{el}:{i}"
                        _traces.append(Trace(self._post.oreportsetup, aedt_name, el, oo1))
            except Exception:
                self._post._app.logger.debug(f"Something went wrong while processing element {el}.")
        return _traces

    @pyaedt_function_handler()
    def _update_traces(self):
        for trace in self.traces[::]:
            trace_name = trace.name
            for trace_val in self._legacy_props["expressions"]:
                if trace_val["name"] == trace_name:
                    trace_style = self.__props_with_default(trace_val, "trace_style")
                    trace_width = self.__props_with_default(trace_val, "width")
                    trace_type = self.__props_with_default(trace_val, "trace_type")
                    trace_color = self.__props_with_default(trace_val, "color")

                    if trace_style or trace_width or trace_type or trace_color:
                        trace.set_trace_properties(
                            style=trace_style, width=trace_width, trace_type=trace_type, color=trace_color
                        )
        for trace in self.traces[::]:
            trace_name = trace.name
            for trace_val in self._legacy_props["expressions"]:
                if trace_val["name"] == trace_name:
                    if self.report_category in ["Eye Diagram", "Spectrum"]:
                        continue
                    symbol_show = self.__props_with_default(trace_val, "show_symbols", False)
                    symbol_style = self.__props_with_default(trace_val, "symbol_style", None)
                    symbol_arrows = self.__props_with_default(trace_val, "show_arrows", None)
                    symbol_fill = self.__props_with_default(trace_val, "symbol_fill", False)
                    symbol_color = self.__props_with_default(trace_val, "symbol_color", None)
                    if symbol_style or symbol_color or symbol_fill or symbol_arrows:
                        trace.set_symbol_properties(
                            show=symbol_show,
                            style=symbol_style,
                            show_arrows=symbol_arrows,
                            fill=symbol_fill,
                            color=symbol_color,
                        )
        for trace in self.traces[::]:
            trace_name = trace.name
            for trace_val in self._legacy_props["expressions"]:
                if trace_val["name"] == trace_name:
                    y_axis = self.__props_with_default(trace_val, "y_axis", "Y1")
                    if y_axis != "Y1":
                        self._change_property(
                            "Trace",
                            trace_name,
                            [
                                "NAME:ChangedProps",
                                [
                                    "NAME:Y Axis",
                                    "Value:=",
                                    y_axis,
                                ],
                            ],
                        )

        if (
            "eye_mask" in self._legacy_props
            and self.report_category in ["Eye Diagram", "Statistical Eye"]
            or ("quantity_type" in self._legacy_props and self.report_type == "Rectangular Contour Plot")
        ):
            eye_xunits = self.__props_with_default(self._legacy_props["eye_mask"], "xunits", "ns")
            eye_yunits = self.__props_with_default(self._legacy_props["eye_mask"], "yunits", "mV")
            eye_points = self.__props_with_default(self._legacy_props["eye_mask"], "points")
            eye_enable = self.__props_with_default(self._legacy_props["eye_mask"], "enable_limits", False)
            eye_upper = self.__props_with_default(self._legacy_props["eye_mask"], "upper_limit", 500)
            eye_lower = self.__props_with_default(self._legacy_props["eye_mask"], "lower_limit", 0.3)
            eye_transparency = self.__props_with_default(self._legacy_props["eye_mask"], "transparency", 0.3)
            eye_color = self.__props_with_default(self._legacy_props["eye_mask"], "color", (0, 128, 0))
            eye_xoffset = self.__props_with_default(self._legacy_props["eye_mask"], "X Offset", "0ns")
            eye_yoffset = self.__props_with_default(self._legacy_props["eye_mask"], "Y Offset", "0V")
            if "quantity_type" in self._legacy_props and self.report_type == "Rectangular Contour Plot":
                if "contours_number" in self._legacy_props.get("general", {}):
                    self._change_property(
                        "Contour",
                        f" Plot {self.traces[0].name}",
                        [
                            "NAME:ChangedProps",
                            ["NAME:Num. Contours", "Value:=", str(self._legacy_props["general"]["contours_number"])],
                        ],
                    )
                if "contours_scale" in self._legacy_props.get("general", {}):
                    self._change_property(
                        "Contour",
                        f" Plot {self.traces[0].name}",
                        [
                            "NAME:ChangedProps",
                            ["NAME:Axis Scale", "Value:=", str(self._legacy_props["general"]["contours_scale"])],
                        ],
                    )
                if "enable_contours_auto_limit" in self._legacy_props.get("general", {}):
                    self._change_property(
                        "Contour",
                        f" Plot {self.traces[0].name}",
                        ["NAME:ChangedProps", ["NAME:Scale Type", "Value:=", "Auto Limits"]],
                    )
                elif "contours_min_limit" in self._legacy_props.get("general", {}):
                    self._change_property(
                        "Contour",
                        f" Plot {self.traces[0].name}",
                        [
                            "NAME:ChangedProps",
                            ["NAME:Min", "Value:=", str(self._legacy_props["general"]["contours_min_limit"])],
                        ],
                    )
                elif "contours_max_limit" in self._legacy_props.get("general", {}):
                    self._change_property(
                        "Contour",
                        f" Plot {self.traces[0].name}",
                        [
                            "NAME:ChangedProps",
                            ["NAME:Max", "Value:=", str(self._legacy_props["general"]["contours_max_limit"])],
                        ],
                    )
            self.eye_mask(
                points=eye_points,
                x_units=eye_xunits,
                y_units=eye_yunits,
                enable_limits=eye_enable,
                upper_limit=eye_upper,
                lower_limit=eye_lower,
                color=eye_color,
                transparency=eye_transparency,
                x_offset=eye_xoffset,
                y_offset=eye_yoffset,
            )
        if "limitLines" in self._legacy_props and self.report_category not in ["Eye Diagram", "Statistical Eye"]:
            for line in self._legacy_props["limitLines"].values():
                if "equation" in line:
                    line_start = self.__props_with_default(line, "start")
                    line_stop = self.__props_with_default(line, "stop")
                    line_step = self.__props_with_default(line, "step")
                    line_equation = self.__props_with_default(line, "equation")
                    line_axis = self.__props_with_default(line, "y_axis", 1)
                    if not line_start or not line_step or not line_stop or not line_equation:
                        self._post._app.logger.error(
                            "Equation Limit Lines needs Start, Stop, Step and Equation fields."
                        )
                        continue
                    self.add_limit_line_from_equation(
                        start_x=line_start, stop_x=line_stop, step=line_step, equation=line_equation, y_axis=line_axis
                    )
                else:
                    line_x = self.__props_with_default(line, "xpoints")
                    line_y = self.__props_with_default(line, "ypoints")
                    line_xunits = self.__props_with_default(line, "xunits")
                    line_yunits = self.__props_with_default(line, "yunits", "")
                    line_axis = self.__props_with_default(line, "y_axis", "Y1")
                    self.add_limit_line_from_points(line_x, line_y, line_xunits, line_yunits, line_axis)
                line_style = self.__props_with_default(line, "trace_style")
                line_width = self.__props_with_default(line, "width")
                line_hatchabove = self.__props_with_default(line, "hatch_above")
                line_viol = self.__props_with_default(line, "violation_emphasis")
                line_hatchpix = self.__props_with_default(line, "hatch_pixels")
                line_color = self.__props_with_default(line, "color")
                self.limit_lines[-1].set_line_properties(
                    style=line_style,
                    width=line_width,
                    hatch_above=line_hatchabove,
                    violation_emphasis=line_viol,
                    hatch_pixels=line_hatchpix,
                    color=line_color,
                )
        if "notes" in self._legacy_props:
            for note in self._legacy_props["notes"].values():
                note_text = self.__props_with_default(note, "text")
                note_position = self.__props_with_default(note, "position", [0, 0])
                self.add_note(note_text, note_position[0], note_position[1])
                note_back_color = self.__props_with_default(note, "background_color")
                note_background_visibility = self.__props_with_default(note, "background_visibility")
                note_border_color = self.__props_with_default(note, "border_color")
                note_border_visibility = self.__props_with_default(note, "border_visibility")
                note_border_width = self.__props_with_default(note, "border_width")
                note_font = self.__props_with_default(note, "font", "Arial")
                note_font_size = self.__props_with_default(note, "font_size", 12)
                note_italic = self.__props_with_default(note, "italic")
                note_bold = self.__props_with_default(note, "bold")
                note_color = self.__props_with_default(note, "color", (0, 0, 0))

                self.notes[-1].set_note_properties(
                    back_color=note_back_color,
                    background_visibility=note_background_visibility,
                    border_color=note_border_color,
                    border_visibility=note_border_visibility,
                    border_width=note_border_width,
                    font=note_font,
                    font_size=note_font_size,
                    italic=note_italic,
                    bold=note_bold,
                    color=note_color,
                )
        if "general" in self._legacy_props:
            if "show_rectangular_plot" in self._legacy_props["general"] and self.report_category in ["Eye Diagram"]:
                eye_rectangular = self.__props_with_default(
                    self._legacy_props["general"], "show_rectangular_plot", True
                )
                self.rectangular_plot(eye_rectangular)
            if "legend" in self._legacy_props["general"] and self.report_type != "Rectangular Contour Plot":
                legend = self._legacy_props["general"]["legend"]
                legend_sol_name = self.__props_with_default(legend, "show_solution_name", True)
                legend_var_keys = self.__props_with_default(legend, "show_variation_key", True)
                leend_trace_names = self.__props_with_default(legend, "show_trace_name", True)
                legend_color = self.__props_with_default(legend, "back_color", (255, 255, 255))
                legend_font_color = self.__props_with_default(legend, "font_color", (0, 0, 0))
                self.edit_legend(
                    show_solution_name=legend_sol_name,
                    show_variation_key=legend_var_keys,
                    show_trace_name=leend_trace_names,
                    back_color=legend_color,
                    font_color=legend_font_color,
                )
            if "grid" in self._legacy_props["general"]:
                grid = self._legacy_props["general"]["grid"]
                grid_major_color = self.__props_with_default(grid, "major_color", (200, 200, 200))
                grid_minor_color = self.__props_with_default(grid, "minor_color", (230, 230, 230))
                grid_enable_major_x = self.__props_with_default(grid, "major_x", True)
                grid_enable_major_y = self.__props_with_default(grid, "major_y", True)
                grid_enable_minor_x = self.__props_with_default(grid, "minor_x", True)
                grid_enable_minor_y = self.__props_with_default(grid, "minor_y", True)
                grid_style_minor = self.__props_with_default(grid, "style_minor", "Solid")
                grid_style_major = self.__props_with_default(grid, "style_major", "Solid")
                self.edit_grid(
                    minor_x=grid_enable_minor_x,
                    minor_y=grid_enable_minor_y,
                    major_x=grid_enable_major_x,
                    major_y=grid_enable_major_y,
                    minor_color=grid_minor_color,
                    major_color=grid_major_color,
                    style_minor=grid_style_minor,
                    style_major=grid_style_major,
                )
            if "appearance" in self._legacy_props["general"]:
                general = self._legacy_props["general"]["appearance"]
                general_back_color = self.__props_with_default(general, "background_color", (255, 255, 255))
                general_plot_color = self.__props_with_default(general, "plot_color", (255, 255, 255))
                enable_y_stripes = self.__props_with_default(general, "enable_y_stripes", True)
                if self._legacy_props["report_type"] == "Radiation Pattern":
                    enable_y_stripes = None
                general_field_width = self.__props_with_default(general, "field_width", 4)
                general_precision = self.__props_with_default(general, "precision", 4)
                general_use_scientific_notation = self.__props_with_default(general, "use_scientific_notation", True)
                self.edit_general_settings(
                    background_color=general_back_color,
                    plot_color=general_plot_color,
                    enable_y_stripes=enable_y_stripes,
                    field_width=general_field_width,
                    precision=general_precision,
                    use_scientific_notation=general_use_scientific_notation,
                )
            if "header" in self._legacy_props["general"]:
                header = self._legacy_props["general"]["header"]
                company_name = self.__props_with_default(header, "company_name", "")
                show_design_name = self.__props_with_default(header, "show_design_name", True)
                header_font = self.__props_with_default(header, "font", "Arial")
                header_title_size = self.__props_with_default(header, "title_size", 12)
                header_subtitle_size = self.__props_with_default(header, "subtitle_size", 12)
                header_italic = self.__props_with_default(header, "italic", False)
                header_bold = self.__props_with_default(header, "bold", False)
                header_color = self.__props_with_default(header, "color", (0, 0, 0))
                self.edit_header(
                    company_name=company_name,
                    show_design_name=show_design_name,
                    font=header_font,
                    title_size=header_title_size,
                    subtitle_size=header_subtitle_size,
                    italic=header_italic,
                    bold=header_bold,
                    color=header_color,
                )

            for i in list(self._legacy_props["general"].keys()):
                if "axis" in i:
                    axis = self._legacy_props["general"][i]
                    axis_font = self.__props_with_default(axis, "font", "Arial")
                    axis_size = self.__props_with_default(axis, "font_size", 12)
                    axis_italic = self.__props_with_default(axis, "italic", False)
                    axis_bold = self.__props_with_default(axis, "bold", False)
                    axis_color = self.__props_with_default(axis, "color", (0, 0, 0))
                    axis_label = self.__props_with_default(axis, "label")
                    axis_linear_scaling = self.__props_with_default(axis, "linear_scaling", True)
                    axis_min_scale = self.__props_with_default(axis, "min_scale")
                    axis_max_scale = self.__props_with_default(axis, "max_scale")
                    axis_min_trick_div = self.__props_with_default(axis, "minor_tick_divs", 5)
                    specify_spacing = self.__props_with_default(axis, "specify_spacing", True)
                    if not specify_spacing:
                        axis_min_spacing = None
                    else:
                        axis_min_spacing = self.__props_with_default(axis, "min_spacing")
                    axis_units = self.__props_with_default(axis, "units")
                    if i == "axisx":
                        self.edit_x_axis(
                            font=axis_font,
                            font_size=axis_size,
                            italic=axis_italic,
                            bold=axis_bold,
                            color=axis_color,
                            label=axis_label,
                        )
                        if self.report_category in ["Eye Diagram", "Statistical Eye"]:
                            continue
                        self.edit_x_axis_scaling(
                            linear_scaling=axis_linear_scaling,
                            min_scale=axis_min_scale,
                            max_scale=axis_max_scale,
                            minor_tick_divs=axis_min_trick_div,
                            min_spacing=axis_min_spacing,
                            units=axis_units,
                        )
                    else:
                        self.edit_y_axis(
                            font=axis_font,
                            font_size=axis_size,
                            italic=axis_italic,
                            bold=axis_bold,
                            color=axis_color,
                            label=axis_label,
                        )
                        if self.report_category in ["Eye Diagram", "Statistical Eye"]:
                            continue
                        self.edit_y_axis_scaling(
                            name=i.replace("axis", "").upper(),
                            linear_scaling=axis_linear_scaling,
                            min_scale=axis_min_scale,
                            max_scale=axis_max_scale,
                            minor_tick_divs=axis_min_trick_div,
                            min_spacing=axis_min_spacing,
                            units=axis_units,
                        )

    @property
    def limit_lines(self):
        """List of available limit lines in the report.

        .. note::
            This property works in version 2022 R1 and later. However, it works only in
            non-graphical mode in version 2022 R2 and later.

        Returns
        -------
        List of :class:`ansys.aedt.core.modules.report_templates.LimitLine`
        """
        _traces = []
        oo_names = self._post._app.get_oo_name(self._post.oreportsetup, self.plot_name)
        for el in oo_names:
            if "LimitLine" in el:
                _traces.append(
                    LimitLine(
                        self._post.oreportsetup,
                        f"{self.plot_name}:{el}",
                        self._post.oreportsetup.GetChildObject(self.plot_name).GetChildObject(el),
                    )
                )

        return _traces

    @property
    def notes(self):
        """List of available notes in the report.

        .. note::
            This property works in version 2022 R1 and later. However, it works only in
            non-graphical mode in version 2022 R2 and later.

        Returns
        -------
        List of :class:`ansys.aedt.core.modules.report_templates.Note`
        """
        _notes = []
        try:
            oo_names = self._post.oreportsetup.GetChildObject(self.plot_name).GetChildNames()
        except Exception:
            return _notes
        for el in oo_names:
            if "Note" in el:
                _notes.append(
                    Note(
                        self._post.oreportsetup,
                        f"{self.plot_name}:{el}",
                        self._post.oreportsetup.GetChildObject(self.plot_name).GetChildObject(el),
                    )
                )

        return _notes

    @property
    def plot_name(self):
        """Plot name.

        Returns
        -------
        str
            Plot name.
        """
        return self._legacy_props["plot_name"]

    @plot_name.setter
    def plot_name(self, name):
        if self._is_created:
            if name not in self._post.oreportsetup.GetAllReportNames():
                self._post.oreportsetup.RenameReport(self._legacy_props["plot_name"], name)
        self._legacy_props["plot_name"] = name

    @property
    def variations(self):
        """Variations.

        Returns
        -------
        str
            Variations.
        """
        if self._is_created:
            try:
                variations = {}
                for tr in self.traces:
                    for fam in tr.properties["Families"]:
                        k = 0
                        while k < len(fam):
                            key = fam[k][:-2]
                            v = fam[k + 1]
                            if key in variations:
                                variations[key].extend(v)
                                variations[key] = list(set(variations[key]))
                            else:
                                variations[key] = v
                            k += 2
                    variations[tr.properties["Primary Sweep"]] = ["All"]
                    if tr.properties.get("Secondary Sweep", None):
                        variations[tr.properties["Secondary Sweep"]] = ["All"]
                self._legacy_props["context"]["variations"] = variations
            except Exception:
                self._post._app.logger.debug("Something went wrong while processing variations.")
        return self._legacy_props["context"]["variations"]

    @variations.setter
    def variations(self, value):

        self._legacy_props["context"]["variations"] = value

    @property
    def primary_sweep(self):
        """Primary sweep report.

        Returns
        -------
        str
            Primary sweep.
        """
        if self._is_created:
            return list(self.properties.values())[4].split(" ,")[0]
        return self._legacy_props["context"]["primary_sweep"]

    @primary_sweep.setter
    def primary_sweep(self, value):
        if value == self._legacy_props["context"].get("secondary_sweep", None):
            self._legacy_props["context"]["secondary_sweep"] = self._legacy_props["context"]["primary_sweep"]
        self._legacy_props["context"]["primary_sweep"] = value
        if value == "Time":
            self.variations.pop("Freq", None)
            self.variations["Time"] = ["All"]
        elif value == "Freq":
            self.variations.pop("Time", None)
            self.variations["Freq"] = ["All"]

    @property
    def secondary_sweep(self):
        """Secondary sweep report.

        Returns
        -------
        str
            Secondary sweep.
        """
        if self._is_created:
            els = list(self.properties.values())[4].split(" ,")

            return els[1] if len(els) == 3 else None
        return self._legacy_props["context"].get("secondary_sweep", None)

    @secondary_sweep.setter
    def secondary_sweep(self, value):
        if value == self._legacy_props["context"]["primary_sweep"]:
            self._legacy_props["context"]["primary_sweep"] = self._legacy_props["context"]["secondary_sweep"]
        self._legacy_props["context"]["secondary_sweep"] = value
        if value == "Time":
            self.variations.pop("Freq", None)
            self.variations["Time"] = ["All"]
        elif value == "Freq":
            self.variations.pop("Time", None)
            self.variations["Freq"] = ["All"]

    @property
    def primary_sweep_range(self):
        """Primary sweep range report.

        Returns
        -------
        str
            Primary sweep range.
        """
        return self._legacy_props["context"]["primary_sweep_range"]

    @primary_sweep_range.setter
    def primary_sweep_range(self, value):
        self._legacy_props["context"]["primary_sweep_range"] = value

    @property
    def secondary_sweep_range(self):
        """Secondary sweep range report.

        Returns
        -------
        str
            Secondary sweep range.
        """
        return self._legacy_props["context"]["secondary_sweep_range"]

    @secondary_sweep_range.setter
    def secondary_sweep_range(self, value):
        self._legacy_props["context"]["secondary_sweep_range"] = value

    @property
    def _context(self):
        return []

    @pyaedt_function_handler()
    def update_expressions_with_defaults(self, quantities_category=None):
        """Update the list of expressions by taking all quantities from a given category.

        Parameters
        ----------
        quantities_category : str, optional
            Quantities category to use. The default is ``None``, in which case the default
            category for the specified report is used.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        self.expressions = self._post.available_report_quantities(
            self.report_category, self.report_type, self.setup, quantities_category
        )

    @property
    def _trace_info(self):
        if not self.expressions:
            self.update_expressions_with_defaults()
        if isinstance(self.expressions, list):
            expr = self.expressions
        else:
            expr = [self.expressions]
        arg = ["X Component:=", self.primary_sweep, "Y Component:=", expr]
        if self.report_type in ["3D Polar Plot", "3D Spherical Plot"]:
            arg = [
                "Phi Component:=",
                self.primary_sweep,
                "Theta Component:=",
                self.secondary_sweep,
                "Mag Component:=",
                expr,
            ]
        elif self.report_type == "Radiation Pattern":
            arg = ["Ang Component:=", self.primary_sweep, "Mag Component:=", expr]
        elif self.report_type in ["Smith Chart", "Polar Plot"]:
            arg = ["Polar Component:=", expr]
        elif self.report_type == "Rectangular Contour Plot":
            arg = [
                "X Component:=",
                self.primary_sweep,
                "Y Component:=",
                self.secondary_sweep,
                "Z Component:=",
                expr,
            ]
        return arg

    @property
    def domain(self):
        """Plot domain.

        Returns
        -------
        str
            Plot domain.
        """
        if self._is_created:
            try:
                return self.traces[0].properties["Domain"]
            except Exception:
                self._post._app.logger.debug("Something went wrong while accessing trace's Domain property.")
        return self._legacy_props["context"]["domain"]

    @domain.setter
    def domain(self, domain):
        self._legacy_props["context"]["domain"] = domain
        if self._post._app.design_type in ["Maxwell 3D", "Maxwell 2D"]:
            return
        if self.primary_sweep == "Freq" and domain == "Time":
            self.primary_sweep = "Time"
            self.variations.pop("Freq", None)
            self.variations["Time"] = ["All"]
        elif self.primary_sweep == "Time" and domain == "Sweep":
            self.primary_sweep = "Freq"
            self.variations.pop("Time", None)
            self.variations["Freq"] = ["All"]

    @property
    def use_pulse_in_tdr(self):
        """Defines if the TDR should use a pulse or step.

        Returns
        -------
        bool
            ``True`` when option is enabled, ``False`` otherwise.
        """
        return self._legacy_props["context"].get("use_pulse_in_tdr", False)

    @use_pulse_in_tdr.setter
    def use_pulse_in_tdr(self, val):
        self._legacy_props["context"]["use_pulse_in_tdr"] = val

    @pyaedt_function_handler()
    def _convert_dict_to_report_sel(self, sweeps):
        if not sweeps:
            return []
        sweep_list = []
        if self.primary_sweep:
            sweep_list.append(self.primary_sweep + ":=")
            if self.primary_sweep_range == ["All"] and self.primary_sweep in self.variations:
                sweep_list.append(self.variations[self.primary_sweep])
            else:
                sweep_list.append(self.primary_sweep_range)
        if self.secondary_sweep:
            sweep_list.append(self.secondary_sweep + ":=")
            if self.secondary_sweep_range == ["All"] and self.secondary_sweep in self.variations:
                sweep_list.append(self.variations[self.secondary_sweep])
            else:
                sweep_list.append(self.secondary_sweep_range)
        for el in sweeps:
            if el in [self.primary_sweep, self.secondary_sweep]:
                continue
            sweep_list.append(el + ":=")
            if isinstance(sweeps[el], list):
                sweep_list.append(sweeps[el])
            else:
                sweep_list.append([sweeps[el]])
        nominal_values = self._post._app.available_variations.get_independent_nominal_values()
        for el in list(nominal_values.keys()):
            if el not in sweeps:
                sweep_list.append(el + ":=")
                sweep_list.append(["Nominal"])
        return sweep_list

    @pyaedt_function_handler(plot_name="name")
    def create(self, name=None):
        """Create a report.

        Parameters
        ----------
        name : str, optional
            Name for the plot. The default is ``None``, in which case the
            default name is used.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        self._is_created = False
        if not name:
            self.plot_name = generate_unique_name("Plot")
        else:
            self.plot_name = name
        if (
            self.setup not in self._post._app.existing_analysis_sweeps
            and "AdaptivePass" not in self.setup
            and " : Table" not in self.setup
        ):
            self._post._app.logger.error("Setup doesn't exist in this design.")
            return False
        self._post.oreportsetup.CreateReport(
            self.plot_name,
            self.report_category,
            self.report_type,
            self.setup,
            self._context,
            self._convert_dict_to_report_sel(self.variations),
            self._trace_info,
        )
        self._post.plots.append(self)
        self._is_created = True
        self._initialize_tree_node()
        return True

    @pyaedt_function_handler()
    def _export_context(self, output_dict):
        from ansys.aedt.core.visualization.report.eye import AMIEyeDiagram
        from ansys.aedt.core.visualization.report.eye import EyeDiagram
        from ansys.aedt.core.visualization.report.field import AntennaParameters
        from ansys.aedt.core.visualization.report.field import FarField
        from ansys.aedt.core.visualization.report.field import Fields

        output_dict["context"] = {
            "domain": self.domain,
            "primary_sweep": self.primary_sweep,
            "primary_sweep_range": self.primary_sweep_range if self.primary_sweep_range else ["All"],
        }
        if isinstance(self, (FarField, AntennaParameters)):
            output_dict["context"]["far_field_sphere"] = self.far_field_sphere
        elif isinstance(self, Fields) and self.polyline:
            output_dict["context"]["polyline"] = self.polyline
            output_dict["context"]["point_number"] = self.point_number
        elif self._post._app.design_type in ["Q3D Extractor", "2D Extractor"] or (
            self._post._app.design_type in ["Maxwell 2D", "Maxwell 3D"]
            and self._post._app.solution_type == "EddyCurrent"
        ):
            output_dict["context"]["matrix"] = self.matrix
        elif self.traces and any(
            [i for i in self._post.available_report_quantities(differential_pairs=True) if i in self.traces[0].name]
        ):
            output_dict["context"]["differential_pairs"] = True
        if self.secondary_sweep:
            output_dict["context"]["secondary_sweep"] = self.secondary_sweep
            output_dict["context"]["secondary_sweep_range"] = (
                self.secondary_sweep_range if self.secondary_sweep_range else ["All"]
            )
        output_dict["context"]["variations"] = self.variations

        if isinstance(self, (AMIEyeDiagram, EyeDiagram)):
            output_dict["context"]["unit_interval"] = self.unit_interval
            output_dict["context"]["offset"] = self.offset
            output_dict["context"]["auto_delay"] = self.auto_delay
            output_dict["context"]["manual_delay"] = self.manual_delay
            output_dict["context"]["auto_cross_amplitude"] = self.auto_cross_amplitude
            output_dict["context"]["cross_amplitude"] = self.cross_amplitude
            output_dict["context"]["auto_compute_eye_meas"] = self.auto_compute_eye_meas
            output_dict["context"]["eye_measurement_point"] = self.eye_measurement_point
            try:
                trace_name = self.traces[0].name
                if "Initial" in trace_name:
                    output_dict["quantity_type"] = 0
                elif "AfterSource" in trace_name:
                    output_dict["quantity_type"] = 1
                elif "AfterChannel" in trace_name:
                    output_dict["quantity_type"] = 2
                elif "AfterProbe" in trace_name:
                    output_dict["quantity_type"] = 3
                else:
                    output_dict["quantity_type"] = 0
            except Exception:
                output_dict["quantity_type"] = 0
            if isinstance(self, EyeDiagram):
                output_dict["context"]["time_start"] = self.time_start
                output_dict["context"]["time_stop"] = self.time_stop
                output_dict["context"]["thinning"] = self.thinning
                output_dict["context"]["dy_dx_tolerance"] = self.dy_dx_tolerance
                output_dict["context"]["thinning_points"] = self.thinning_points

    @pyaedt_function_handler()
    def _export_expressions(self, output_dict):
        output_dict["expressions"] = {}
        for expr in self.traces:
            name = self.properties[expr.name].split(" ,")[-1]
            pr = expr.curve_properties
            output_dict["expressions"][name] = {}
            if "Trace Type" in pr:
                output_dict["expressions"][name] = {
                    "color": [pr["Color/Red"], pr["Color/Green"], pr["Color/Blue"]],
                    "trace_style": pr["Line Style"],
                    "width": pr["Line Width"],
                }
            if "Y Axis" in expr.properties:
                output_dict["expressions"][name]["y_axis"] = expr.properties["Y Axis"]
            if "Show Symbol" in pr:
                symbol_dict = {
                    "symbol_color": [pr["Symbol Color/Red"], pr["Symbol Color/Green"], pr["Symbol Color/Blue"]],
                    "show_symbols": pr["Show Symbol"],
                    "symbol_style": pr["Symbol Style"],
                    "symbol_fill": pr["Fill Symbol"],
                    "show_arrows": pr["Show Arrows"],
                    "symbol_frequency": pr["Symbol Frequency"],
                }
                output_dict["expressions"][name].update(symbol_dict)

    @pyaedt_function_handler()
    def _export_graphical_objects(self, output_dict):
        from ansys.aedt.core.visualization.report.eye import AMIEyeDiagram
        from ansys.aedt.core.visualization.report.eye import EyeDiagram

        if isinstance(self, (AMIEyeDiagram, EyeDiagram)) and "EyeDisplayTypeProperty" in self.children:
            pr = self.children["EyeDisplayTypeProperty"].properties
            if pr.get("Mask/MaskPoints", None) and len(pr["Mask/MaskPoints"]) > 1:
                pts_x = pr["Mask/MaskPoints"][1::2]
                pts_y = pr["Mask/MaskPoints"][2::2]

                output_dict["eye_mask"] = {
                    "xunits": pr["Mask/XUnits"],
                    "yunits": pr["Mask/YUnits"],
                    "points": [[i, j] for i, j in zip(pts_x, pts_y)],
                    "enable_limits": pr["Mask/ShowLimits"],
                    "upper_limit": pr["Mask/UpperLimit"],
                    "lower_limit": pr["Mask/LowerLimit"],
                    "color": [pr["Mask Fill Color/Red"], pr["Mask Fill Color/Green"], pr["Mask Fill Color/Blue"]],
                    "transparency": pr["Mask Trans/Transparency"],
                }

        output_dict["limitLines"] = {}
        for expr in self.limit_lines:
            pr = expr.properties
            name = expr.line_name
            output_dict["limitLines"][name] = {
                "color": [pr["Color/Red"], pr["Color/Green"], pr["Color/Blue"]],
                "trace_style": pr["Line Style"],
                "width": pr["Line Width"],
                "hatch_above": pr["Hatch Above"],
                "violation_emphasis": pr["Violation Emphasis"],
                "hatch_pixels": pr["Hatch Pixels"],
                "y_axis": pr["Y Axis"],
            }
            if "Point Data" in pr:  # supported only point data
                pdata = pr["Point Data"]
                output_dict["limitLines"][name]["xunits"] = ""
                output_dict["limitLines"][name]["yunits"] = ""
                output_dict["limitLines"][name]["xpoints"] = pdata[-1][1::2]
                output_dict["limitLines"][name]["ypoints"] = pdata[-1][2::2]
            else:
                output_dict["limitLines"][name]["start"] = pr["Start"]
                output_dict["limitLines"][name]["stop"] = pr["Stop"]
                output_dict["limitLines"][name]["step"] = pr["Step"]
                output_dict["limitLines"][name]["equation"] = pr["Equation"]
                output_dict["limitLines"][name]["y_axis"] = pr["Y Axis"]

        output_dict["notes"] = {}
        position = [1000, 1000]  # no way to retrieve position of notes
        for expr in self.notes:
            pr = expr.properties
            name = expr.plot_note_name
            output_dict["notes"][name] = {
                "text": pr["Note Text"][1],
                "color": [pr["Note Font/R"], pr["Note Font/G"], pr["Note Font/B"]],
                "font": pr["Note Font/FaceName"],
                "font_size": pr["Note Font/Height"],
                "italic": True if pr["Note Font/Italic"] else False,
                "background_color": [pr["Back Color/Red"], pr["Back Color/Green"], pr["Back Color/Blue"]],
                "background_visibility": pr["Background Visibility"],
                "border_color": [pr["Border Color/Red"], pr["Border Color/Green"], pr["Border Color/Blue"]],
                "border_visibiliy": pr["Border Visibility"],
                "border_width": pr["Border Width"],
                "position": position,
            }

    @pyaedt_function_handler()
    def _export_general_appearance(self, output_dict):
        from ansys.aedt.core.visualization.report.eye import AMIEyeDiagram
        from ansys.aedt.core.visualization.report.eye import EyeDiagram

        output_dict["general"] = {}
        if "AxisX" in self.children:
            axis = self.children["AxisX"].properties
            output_dict["general"]["axisx"] = {
                "label": axis["Name"],
                "font": axis["Text Font/FaceName"],
                "font_size": axis["Text Font/Height"],
                "italic": True if axis["Text Font/Italic"] else False,
                "color": [axis["Text Font/R"], axis["Text Font/G"], axis["Text Font/B"]],
                "specify_spacing": axis.get("Specify Spacing", False),
                "spacing": axis.get("Spacing", "1GHz"),
                "minor_tick_divs": axis.get("Minor Tick Divs", None),
                "auto_units": axis["Auto Units"],
                "units": axis["Units"],
            }
            if not isinstance(self, (AMIEyeDiagram, EyeDiagram)):
                output_dict["general"]["axisx"]["linear_scaling"] = True if axis["Axis Scaling"] == "Linear" else False
            y_axis_available = [i for i in self.children.keys() if i.startswith("AxisY")]
            for yaxis in y_axis_available:
                axis = self.children[yaxis].properties
                output_dict["general"][yaxis.lower()] = {
                    "label": axis["Name"],
                    "font": axis["Text Font/FaceName"],
                    "font_size": axis["Text Font/Height"],
                    "italic": True if axis["Text Font/Italic"] else False,
                    "color": [axis["Text Font/R"], axis["Text Font/G"], axis["Text Font/B"]],
                    "specify_spacing": axis.get("Specify Spacing", False),
                    "minor_tick_divs": axis.get("Minor Tick Divs", None),
                    "auto_units": axis["Auto Units"],
                    "units": axis["Units"],
                }
                if not isinstance(self, (AMIEyeDiagram, EyeDiagram)):
                    output_dict["general"][yaxis.lower()]["linear_scaling"] = (
                        True if axis["Axis Scaling"] == "Linear" else False
                    )
        if "General" in self.children:
            props = self.children["General"].properties
            output_dict["general"]["appearance"] = {
                "background_color": [
                    props["Back Color/Red"],
                    props["Back Color/Green"],
                    props["Back Color/Blue"],
                ],
                "plot_color": [
                    props["Plot Area Color/Red"],
                    props["Plot Area Color/Green"],
                    props["Plot Area Color/Blue"],
                ],
                "enable_y_stripes": props.get("Enable Y Axis Stripes", None),
                "Auto Scale Fonts": props["Auto Scale Fonts"],
                "field_width": props["Field Width"],
                "precision": props["Precision"],
                "use_scientific_notation": props["Use Scientific Notation"],
            }

        if "Grid" in self.children:
            props = self.children["Grid"].properties
            output_dict["general"]["grid"] = {
                "major_color": [
                    props["Major grid line color/Red"],
                    props["Major grid line color/Green"],
                    props["Major grid line color/Blue"],
                ],
                "minor_color": [
                    props["Minor grid line color/Red"],
                    props["Minor grid line color/Green"],
                    props["Minor grid line color/Blue"],
                ],
                "major_x": props["Show major X grid"],
                "major_y": props["Show major Y grid"],
                "minor_x": props["Show minor X grid"],
                "minor_y": props["Show minor Y grid"],
                "style_major": props["Major grid line style"],
                "style_minor": props["Minor grid line style"],
            }
        if "Legend" in self.children:
            props = self.children["Legend"].properties
            output_dict["general"]["legend"] = {
                "back_color": [
                    props["Back Color/Red"],
                    props["Back Color/Green"],
                    props["Back Color/Blue"],
                ],
                "font_color": [
                    props["Font/R"],
                    props["Font/G"],
                    props["Font/B"],
                ],
                "show_solution_name": props["Show Solution Name"],
                "show_variation_key": props["Show Variation Key"],
                "show_trace_name": props["Show Trace Name"],
            }
        if "Header" in self.children:
            props = self.children["Header"].properties
            output_dict["general"]["header"] = {
                "font": props["Title Font/FaceName"],
                "title_size": props["Title Font/Height"],
                "color": [
                    props["Title Font/R"],
                    props["Title Font/G"],
                    props["Title Font/B"],
                ],
                "italic": True if props["Title Font/Italic"] else False,
                "subtitle_size": props["Sub Title Font/Height"],
                "company_name": props["Company Name"],
                "show_design_name": props["Show Design Name"],
            }

    @pyaedt_function_handler()
    def export_config(self, output_file):
        """Generate a configuration file from active report.

        Parameters
        ----------
        output_file : str
            Full path to json file.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        output_dict = {}
        output_dict["Help"] = "Report Generated automatically by PyAEDT"
        output_dict["report_category"] = self.report_category
        output_dict["report_type"] = self.report_type
        output_dict["plot_name"] = self.plot_name

        self._export_context(output_dict)
        self._export_expressions(output_dict)
        self._export_graphical_objects(output_dict)
        self._export_general_appearance(output_dict)

        return write_configuration_file(output_dict, output_file)

    @pyaedt_function_handler()
    def get_solution_data(self):
        """Get the report solution data.

        Returns
        -------
        :class:`ansys.aedt.core.modules.solutions.SolutionData`
            Solution data object.
        """
        if self._is_created:
            expr = [i.name for i in self.traces]
        elif not self.expressions:
            self.update_expressions_with_defaults()
            expr = [i for i in self.expressions]
        else:
            expr = [i for i in self.expressions]
        if not expr:
            self._post._app.logger.warning("No Expressions Available. Check inputs")
            return False
        solution_data = self._post.get_solution_data_per_variation(
            self.report_category, self.setup, self._context, self.variations, expr
        )
        if not solution_data:
            self._post._app.logger.warning("No Data Available. Check inputs")
            return False
        if self.primary_sweep:
            solution_data.primary_sweep = self.primary_sweep
        return solution_data

    @pyaedt_function_handler()
    def add_limit_line_from_points(self, x_list, y_list, x_units="", y_units="", y_axis="Y1"):  # pragma: no cover
        """Add a Cartesian limit line from point lists. This method works only in graphical mode.

        Parameters
        ----------
        x_list : list
            List of float inputs.
        y_list : list
            List of float y values.
        x_units : str, optional
            Units for the ``x_list`` parameter. The default is ``""``.
        y_units : str, optional
            Units for the ``y_list`` parameter. The default is ``""``.
        y_axis : int, optional
            Y axis. The default is `"Y1"`.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        x_list = [GeometryOperators.parse_dim_arg(str(i) + x_units) for i in x_list]
        y_list = [GeometryOperators.parse_dim_arg(str(i) + y_units) for i in y_list]
        if self.plot_name and self._is_created:
            xvals = ["NAME:XValues"]
            xvals.extend(x_list)
            yvals = ["NAME:YValues"]
            yvals.extend(y_list)
            self._post.oreportsetup.AddCartesianLimitLine(
                self.plot_name,
                [
                    "NAME:CartesianLimitLine",
                    xvals,
                    "XUnits:=",
                    x_units,
                    yvals,
                    "YUnits:=",
                    y_units,
                    "YAxis:=",
                    y_axis,
                ],
            )
            return True
        return False

    @pyaedt_function_handler()
    def add_limit_line_from_equation(
        self, start_x, stop_x, step, equation="x", units="GHz", y_axis=1
    ):  # pragma: no cover
        """Add a Cartesian limit line from point lists. This method works only in graphical mode.

        Parameters
        ----------
        start_x : float
            Start X value.
        stop_x : float
            Stop X value.
        step : float
            X step value.
        equation : str, optional
            Y equation to apply. The default is Y=X.
        units : str
            Units for the X axis. The default is ``"GHz"``.
        y_axis : str, int, optional
            Y axis. The default is ``1``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if self.plot_name and self._is_created:
            self._post.oreportsetup.AddCartesianLimitLineFromEquation(
                self.plot_name,
                [
                    "NAME:CartesianLimitLineFromEquation",
                    "YAxis:=",
                    int(str(y_axis).replace("Y", "")),
                    "Start:=",
                    self._post._app.value_with_units(start_x, units),
                    "Stop:=",
                    self._post._app.value_with_units(stop_x, units),
                    "Step:=",
                    self._post._app.value_with_units(step, units),
                    "Equation:=",
                    equation,
                ],
            )
            return True
        return False

    @pyaedt_function_handler()
    def add_note(self, text, x_position=0, y_position=0):  # pragma: no cover
        """Add a note at a position.

        Parameters
        ----------
        text : string
            Text of the note.
        x_position : float, optional
            x position of the note. The default is ``0.0``.
        y_position : float, optional
            y position of the note. The default is ``0.0``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        note_name = generate_unique_name("Note", n=3)
        if self.plot_name and self._is_created:
            self._post.oreportsetup.AddNote(
                self.plot_name,
                [
                    "NAME:NoteDataSource",
                    [
                        "NAME:NoteDataSource",
                        "SourceName:=",
                        note_name,
                        "HaveDefaultPos:=",
                        True,
                        "DefaultXPos:=",
                        x_position,
                        "DefaultYPos:=",
                        y_position,
                        "String:=",
                        text,
                    ],
                ],
            )
            return True
        return False

    @pyaedt_function_handler(val="value")
    def add_cartesian_x_marker(self, value, name=None):  # pragma: no cover
        """Add a cartesian X marker.

        .. note::
           This method only works in graphical mode.

        Parameters
        ----------
        value : str
            Value to apply with units.
        name : str, optional
            Marker name. The default is ``None``.

        Returns
        -------
        str
            Marker name if created.
        """
        if not name:
            name = generate_unique_name("MX")
            self._post.oreportsetup.AddCartesianXMarker(self.plot_name, name, GeometryOperators.parse_dim_arg(value))
            return name
        return ""

    @pyaedt_function_handler(val="value")
    def add_cartesian_y_marker(self, value, name=None, y_axis=1):  # pragma: no cover
        """Add a cartesian Y marker.

        .. note::
           This method only works in graphical mode.

        Parameters
        ----------
        value : str, float
            Value to apply with units.
        name : str, optional
            Marker name. The default is ``None``.
        y_axis : str, optional
            Y axis. The default is ``"Y1"``.

        Returns
        -------
        str
            Marker name if created.
        """
        if not name:
            name = generate_unique_name("MY")
            self._post.oreportsetup.AddCartesianYMarker(
                self.plot_name, name, f"Y{y_axis}", GeometryOperators.parse_dim_arg(value), ""
            )
            return name
        return ""

    @pyaedt_function_handler(tabname="tab_name")
    def _change_property(self, tab_name, property_name, property_val):
        if not self._is_created:
            self._post._app.logger.error("Plot has not been created. Create it and then change the properties.")
            return False
        arg = [
            "NAME:AllTabs",
            ["NAME:" + tab_name, ["NAME:PropServers", f"{self.plot_name}:{property_name}"], property_val],
        ]
        self._post.oreportsetup.ChangeProperty(arg)
        return True

    @pyaedt_function_handler()
    def edit_grid(
        self,
        minor_x=True,
        minor_y=True,
        major_x=True,
        major_y=True,
        style_minor="Solid",
        style_major="Solid",
        minor_color=(0, 0, 0),
        major_color=(0, 0, 0),
    ):
        """Edit the grid settings for the plot.

        Parameters
        ----------
        minor_x : bool, optional
            Whether to enable the minor X grid. The default is ``True``.
        minor_y : bool, optional
            Whether to enable the minor Y grid. The default is ``True``.
        major_x : bool, optional
            Whether to enable the major X grid. The default is ``True``.
        major_y : bool, optional
            Whether to enable the major Y grid. The default is ``True``.
        style_minor : str, optional
            Minor grid style. The default is ``"Solid"``.
        style_major : str, optional
            Major grid style. The default is ``"Solid"``.
        minor_color : tuple, optional
            Minor grid (R, G, B) color. The default is ``(0, 0, 0)``.
            Each color value must be an integer in a range from 0 to 255.
        major_color : tuple, optional
            Major grid (R, G, B) color. The default is ``(0, 0, 0)``.
            Each color value must be an integer in a range from 0 to 255.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        props = [
            "NAME:ChangedProps",
            ["NAME:Show minor X grid", "Value:=", minor_x],
            ["NAME:Show minor Y grid", "Value:=", minor_y],
            ["NAME:Show major X grid", "Value:=", major_x],
            ["NAME:Show major Y grid", "Value:=", major_y],
            ["NAME:Minor grid line style", "Value:=", style_minor],
            ["NAME:Major grid line style", "Value:=", style_major],
            ["NAME:Minor grid line color", "R:=", minor_color[0], "G:=", minor_color[1], "B:=", minor_color[2]],
            ["NAME:Major grid line color", "R:=", major_color[0], "G:=", major_color[1], "B:=", major_color[2]],
        ]
        return self._change_property("Grid", "Grid", props)

    @pyaedt_function_handler()
    def edit_x_axis(
        self, font="Arial", font_size=12, italic=False, bold=False, color=(0, 0, 0), label=None, display_units=True
    ):
        """Edit the X-axis settings.

        Parameters
        ----------
        font : str, optional
            Font name. The default is ``"Arial"``.
        font_size : int, optional
            Font size. The default is ``12``.
        italic : bool, optional
            Whether to use italic type. The default is ``False``.
        bold : bool, optional
            Whether to use bold type. The default is ``False``.
        color : tuple, optional
            Font (R, G, B) color. The default is ``(0, 0, 0)``. Each color value
            must be an integer in a range from 0 to 255.
        label : str, optional
            Label for the Y axis. The default is ``None``.
        display_units : bool, optional
            Whether to display units. The default is ``True``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        props = [
            "NAME:ChangedProps",
            [
                "NAME:Text Font",
                "Height:=",
                -1 * font_size - 2,
                "Width:=",
                0,
                "Escapement:=",
                0,
                "Orientation:=",
                0,
                "Weight:=",
                700 if bold else 400,
                "Italic:=",
                255 if italic else 0,
                "Underline:=",
                0,
                "StrikeOut:=",
                0,
                "CharSet:=",
                0,
                "OutPrecision:=",
                3,
                "ClipPrecision:=",
                2,
                "Quality:=",
                1,
                "PitchAndFamily:=",
                34,
                "FaceName:=",
                font,
                "R:=",
                color[0],
                "G:=",
                color[1],
                "B:=",
                color[2],
            ],
        ]
        if label:
            props.append(["NAME:Name", "Value:=", label])
        props.append(["NAME:Axis Color", "R:=", color[0], "G:=", color[1], "B:=", color[2]])
        props.append(["NAME:Display Units", "Value:=", display_units])

        return self._change_property("Axis", "AxisX", props)

    @pyaedt_function_handler()
    def edit_x_axis_scaling(
        self, linear_scaling=True, min_scale=None, max_scale=None, minor_tick_divs=5, min_spacing=None, units=None
    ):
        """Edit the X-axis scaling settings.

        Parameters
        ----------
        linear_scaling : bool, optional
            Whether to use the linear scale. The default is ``True``.
            When ``False``, the log scale is used.
        min_scale : str, optional
            Minimum scale value with units. The default is ``None``.
        max_scale : str, optional
            Maximum scale value with units. The default is ``None``.
        minor_tick_divs : int, optional
            Minor tick division. The default is ``5``.
        min_spacing : str, optional
            Minimum spacing with units. The default is ``None``.
        units : str, optional
            Units in the plot. The default is ``None``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if linear_scaling:
            props = ["NAME:ChangedProps", ["NAME:Axis Scaling", "Value:=", "Linear"]]
        else:
            props = ["NAME:ChangedProps", ["NAME:Axis Scaling", "Value:=", "Log"]]
        if min_scale:
            props.append(["NAME:Min", "Value:=", min_scale])
        if max_scale:
            props.append(["NAME:Max", "Value:=", max_scale])
        if minor_tick_divs and linear_scaling:
            props.append(["NAME:Minor Tick Divs", "Value:=", str(minor_tick_divs)])
        if min_spacing:
            props.append(["NAME:Spacing", "Value:=", min_spacing])
        if units:
            props.append((["NAME:Auto Units", "Value:=", False]))
            props.append(["NAME:Units", "Value:=", units])
        return self._change_property("Scaling", "AxisX", props)

    @pyaedt_function_handler()
    def edit_legend(
        self,
        show_solution_name=True,
        show_variation_key=True,
        show_trace_name=True,
        back_color=(255, 255, 255),
        font_color=(0, 0, 0),
    ):
        """Edit the plot legend.

        Parameters
        ----------
        show_solution_name : bool, optional
            Whether to show the solution name. The default is ``True``.
        show_variation_key : bool, optional
            Whether to show the variation key. The default is ``True``.
        show_trace_name : bool, optional
            Whether to show the trace name. The default is ``True``.
        back_color : tuple, optional
            Background (R, G, B) color. The default is ``(255, 255, 255)``. Each color value
            must be an integer in a range from 0 to 255.
        font_color : tuple, optional
            Legend font (R, G, B) color. The default is ``(0, 0, 0)``. Each color value
            must be an integer in a range from 0 to 255.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        props = [
            "NAME:ChangedProps",
            ["NAME:Show Solution Name", "Value:=", show_solution_name],
            ["NAME:Show Variation Key", "Value:=", show_variation_key],
            ["NAME:Show Trace Name", "Value:=", show_trace_name],
            ["NAME:Back Color", "R:=", back_color[0], "G:=", back_color[1], "B:=", back_color[2]],
            ["NAME:Font", "R:=", font_color[0], "G:=", font_color[1], "B:=", font_color[2]],
        ]
        return self._change_property("legend", "legend", props)

    @pyaedt_function_handler(font_height="font_size")
    def hide_legend(self, solution_name=True, trace_name=True, variation_key=True, font_size=1):
        """Hide the Legend.

        Parameters
        ----------
        solution_name : bool, optional
            Whether to show or hide the solution name. Default is ``True``.
        trace_name : bool, optional
            Whether to show or hide the trace name. Default is ``True``.
        variation_key : bool, optional
            Whether to show or hide the variations. Default is ``True``.
        font_size : int
            Font size. The default is ``1``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        try:
            legend = self._post.oreportsetup.GetChildObject(self.plot_name).GetChildObject("Legend")
            legend.Show_Solution_Name = not solution_name
            legend.Show_Trace_Name = not trace_name
            legend.Show_Variation_Key = not variation_key
            legend.SetPropValue("Font/Height", font_size)
            legend.SetPropValue("Header Row Font/Height", font_size)
            return True
        except Exception:
            self._post._app.logger.error("Failed to hide legend.")
            return False

    @pyaedt_function_handler(axis_name="name")
    def edit_y_axis(
        self,
        name="Y1",
        font="Arial",
        font_size=12,
        italic=False,
        bold=False,
        color=(0, 0, 0),
        label=None,
        display_units=True,
    ):
        """Edit the Y-axis settings.

        Parameters
        ----------
        name : str, optional
            Name for the main Y axis. The default is ``"Y1"``.
        font : str, optional
            Font name. The default is ``"Arial"``.
        font_size : int, optional
            Font size. The default is ``12``.
        italic : bool, optional
            Whether to use italic type. The default is ``False``.
        bold : bool, optional
            Whether to use bold type. The default is ``False``.
        color : tuple, optional
            Font (R, G, B) color. The default is ``(0, 0, 0)``. Each color value
            must be an integer in a range from 0 to 255.
        label : str, optional
            Label for the Y axis. The default is ``None``.
        display_units : bool, optional
            Whether to display units. The default is ``True``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        props = [
            "NAME:ChangedProps",
            [
                "NAME:Text Font",
                "Height:=",
                -1 * font_size - 2,
                "Width:=",
                0,
                "Escapement:=",
                0,
                "Orientation:=",
                0,
                "Weight:=",
                700 if bold else 400,
                "Italic:=",
                255 if italic else 0,
                "Underline:=",
                0,
                "StrikeOut:=",
                0,
                "CharSet:=",
                0,
                "OutPrecision:=",
                3,
                "ClipPrecision:=",
                2,
                "Quality:=",
                1,
                "PitchAndFamily:=",
                34,
                "FaceName:=",
                font,
                "R:=",
                color[0],
                "G:=",
                color[1],
                "B:=",
                color[2],
            ],
        ]
        if label:
            props.append(["NAME:Name", "Value:=", label])
        props.append(["NAME:Axis Color", "R:=", color[0], "G:=", color[1], "B:=", color[2]])
        props.append(["NAME:Display Units", "Value:=", display_units])
        return self._change_property("Axis", "Axis" + name, props)

    @pyaedt_function_handler(axis_name="name")
    def edit_y_axis_scaling(
        self,
        name="Y1",
        linear_scaling=True,
        min_scale=None,
        max_scale=None,
        minor_tick_divs=5,
        min_spacing=None,
        units=None,
    ):
        """Edit the Y-axis scaling settings.

        Parameters
        ----------
        axis name : str, optional
            Axis name. The default is ``Y``.
        linear_scaling : bool, optional
            Whether to use the linear scale. The default is ``True``.
            When ``False``, the log scale is used.
        min_scale : str, optional
            Minimum scale value with units. The default is ``None``.
        max_scale : str, optional
            Maximum scale value with units. The default is ``None``.
        minor_tick_divs : int, optional
            Minor tick division. The default is ``5``.
        min_spacing : str, optional
            Minimum spacing with units. The default is ``None``.
        units : str, optional
            Units in the plot. The default is ``None``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if linear_scaling:
            props = ["NAME:ChangedProps", ["NAME:Axis Scaling", "Value:=", "Linear"]]
        else:
            props = ["NAME:ChangedProps", ["NAME:Axis Scaling", "Value:=", "Log"]]
        if min_scale:
            props.append(["NAME:Min", "Value:=", min_scale])
        if max_scale:
            props.append(["NAME:Max", "Value:=", max_scale])
        if minor_tick_divs and linear_scaling:
            props.append(["NAME:Minor Tick Divs", "Value:=", str(minor_tick_divs)])
        if min_spacing:
            props.append(["NAME:Spacing", "Value:=", min_spacing])
        if units:
            props.append((["NAME:Auto Units", "Value:=", False]))
            props.append(["NAME:Units", "Value:=", units])
        return self._change_property("Scaling", "Axis" + name, props)

    @pyaedt_function_handler()
    def edit_general_settings(
        self,
        background_color=(255, 255, 255),
        plot_color=(255, 255, 255),
        enable_y_stripes=True,
        field_width=4,
        precision=4,
        use_scientific_notation=True,
    ):
        """Edit general settings for the plot.

        Parameters
        ----------
        background_color : tuple, optional
            Backgoround (R, G, B) color. The default is ``(255, 255, 255)``. Each color value
            must be an integer in a range from 0 to 255.
        plot_color : tuple, optional
            Plot (R, G, B) color. The default is ``(255, 255, 255)``. Each color value
            must be an integer in a range from 0 to 255.
        enable_y_stripes : bool, optional
            Whether to enable Y stripes. The default is ``True``.
        field_width : int, optional
            Field width. The default is ``4``.
        precision : int, optional
            Field precision. The default is ``4``.
        use_scientific_notation : bool, optional
            Whether to enable scientific notation. The default is ``True``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if enable_y_stripes is None:
            props = [
                "NAME:ChangedProps",
                ["NAME:Back Color", "R:=", background_color[0], "G:=", background_color[1], "B:=", background_color[2]],
                ["NAME:Plot Area Color", "R:=", plot_color[0], "G:=", plot_color[1], "B:=", plot_color[2]],
                ["NAME:Field Width", "Value:=", str(field_width)],
                ["NAME:Precision", "Value:=", str(precision)],
                ["NAME:Use Scientific Notation", "Value:=", use_scientific_notation],
            ]
        else:
            props = [
                "NAME:ChangedProps",
                ["NAME:Back Color", "R:=", background_color[0], "G:=", background_color[1], "B:=", background_color[2]],
                ["NAME:Plot Area Color", "R:=", plot_color[0], "G:=", plot_color[1], "B:=", plot_color[2]],
                ["NAME:Enable Y Axis Stripes", "Value:=", enable_y_stripes],
                ["NAME:Field Width", "Value:=", str(field_width)],
                ["NAME:Precision", "Value:=", str(precision)],
                ["NAME:Use Scientific Notation", "Value:=", use_scientific_notation],
            ]
        return self._change_property("general", "general", props)

    @pyaedt_function_handler()
    def edit_header(
        self,
        company_name="PyAEDT",
        show_design_name=True,
        font="Arial",
        title_size=12,
        subtitle_size=12,
        italic=False,
        bold=False,
        color=(0, 0, 0),
    ):
        """Edit the plot header.

        Parameters
        ----------
        company_name : str, optional
            Company name. The default is ``PyAEDT``.
        show_design_name : bool, optional
            Whether to show the design name in the plot. The default is ``True``.
        font : str, optional
            Font name. The default is ``"Arial"``.
        title_size : int, optional
            Title font size. The default is ``12``.
        subtitle_size : int, optional
            Subtitle font size. The default is ``12``.
        italic : bool, optional
            Whether to use italic type. The default is ``False``.
        bold : bool, optional
            Whether to use bold type. The default is ``False``.
        color : tuple, optional
            Title (R, G, B) color. The default is ``(0, 0, 0)``.
            Each color value must be an integer in a range from 0 to 255.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        props = [
            "NAME:ChangedProps",
            [
                "NAME:Title Font",
                "Height:=",
                -1 * title_size - 2,
                "Width:=",
                0,
                "Escapement:=",
                0,
                "Orientation:=",
                0,
                "Weight:=",
                700 if bold else 400,
                "Italic:=",
                255 if italic else 0,
                "Underline:=",
                0,
                "StrikeOut:=",
                0,
                "CharSet:=",
                0,
                "OutPrecision:=",
                3,
                "ClipPrecision:=",
                2,
                "Quality:=",
                1,
                "PitchAndFamily:=",
                34,
                "FaceName:=",
                font,
                "R:=",
                color[0],
                "G:=",
                color[1],
                "B:=",
                color[2],
            ],
            [
                "NAME:Sub Title Font",
                "Height:=",
                -1 * subtitle_size - 2,
                "Width:=",
                0,
                "Escapement:=",
                0,
                "Orientation:=",
                0,
                "Weight:=",
                700 if bold else 400,
                "Italic:=",
                255 if italic else 0,
                "Underline:=",
                0,
                "StrikeOut:=",
                0,
                "CharSet:=",
                0,
                "OutPrecision:=",
                3,
                "ClipPrecision:=",
                2,
                "Quality:=",
                1,
                "PitchAndFamily:=",
                34,
                "FaceName:=",
                font,
                "R:=",
                color[0],
                "G:=",
                color[1],
                "B:=",
                color[2],
            ],
            ["NAME:Company Name", "Value:=", company_name],
            ["NAME:Show Design Name", "Value:=", show_design_name],
        ]
        return self._change_property("Header", "Header", props)

    @pyaedt_function_handler(file_path="input_file")
    def import_traces(self, input_file, plot_name):
        """Import report data from a file into a specified report.

        Parameters
        ----------
        input_file : str
            Path for the file to import. The extensions supported are ``".csv"``,
            ``".tab"``, ``".dat"``, and ``".rdat"``.
        plot_name : str
            Name of the plot to import the file data into.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if not os.path.exists(input_file):
            msg = "File does not exist."
            raise FileExistsError(msg)

        if not plot_name:
            msg = "Plot name can't be None."
            raise ValueError(msg)
        else:
            if plot_name not in self._post.all_report_names:
                msg = "Plot name provided doesn't exists in current report."
                raise ValueError(msg)
            self.plot_name = plot_name

        split_path = os.path.splitext(input_file)
        extension = split_path[1]

        supported_ext = [".csv", ".tab", ".dat", ".rdat"]
        if extension not in supported_ext:
            msg = f"Extension {extension} is not supported. Use one of {', '.join(supported_ext)}"
            raise ValueError(msg)

        try:
            if extension == ".rdat":
                self._post.oreportsetup.ImportReportDataIntoReport(self.plot_name, input_file)
            else:
                self._post.oreportsetup.ImportIntoReport(self.plot_name, input_file)
            return True
        except Exception:
            return False

    @pyaedt_function_handler()
    def delete_traces(self, plot_name, traces_list):
        """Delete an existing trace or traces.

        Parameters
        ----------
        plot_name : str
            Plot name.
        traces_list : list
            List of one or more traces to delete.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if plot_name not in self._post.all_report_names:
            raise ValueError("Plot does not exist in current project.")

        for trace in traces_list:
            if trace not in self._trace_info[3]:
                raise ValueError("Trace does not exist in the selected plot.")

        props = [f"{plot_name}:=", traces_list]
        try:
            self._post.oreportsetup.DeleteTraces(props)
            self._initialize_tree_node()
            return True
        except Exception:
            return False

    @pyaedt_function_handler()
    def add_trace_to_report(self, traces, setup_name=None, variations=None, context=None):
        """Add a trace to a specific report.

        Parameters
        ----------
        traces : list
            List of traces to add.
        setup_name : str, optional
            Name of the setup. The default is ``None`` which automatically take ``nominal_adaptive`` setup.
            Please make sure to build a setup string in the form of ``"SetupName : SetupSweep"``
            where ``SetupSweep`` is the Sweep name to use in the export or ``LastAdaptive``.
        variations : dict, optional
            Dictionary of variations. The default is ``None``.
        context : list, optional
            List of solution context.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        expr = copy.deepcopy(self.expressions)
        self.expressions = traces

        try:
            self._post.oreportsetup.AddTraces(
                self.plot_name,
                setup_name if setup_name else self.setup,
                context if context else self._context,
                self._convert_dict_to_report_sel(variations if variations else self.variations),
                self._trace_info,
            )
            self._initialize_tree_node()
            return True
        except Exception:
            return False
        finally:
            self.expressions = expr

    @pyaedt_function_handler()
    def update_trace_in_report(self, traces, setup_name=None, variations=None, context=None):
        """Update a trace in a specific report.

        Parameters
        ----------
        traces : list
            List of traces to add.
        setup_name : str, optional
            Name of the setup. The default is ``None``.
        variations : dict, optional
            Dictionary of variations. The default is ``None``.
        context : list, optional
            List of solution context.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        expr = copy.deepcopy(self.expressions)
        self.expressions = traces

        try:
            self._post.oreportsetup.UpdateTraces(
                self.plot_name,
                traces,
                setup_name if setup_name else self.setup,
                context if context else self._context,
                self._convert_dict_to_report_sel(variations if variations else self.variations),
                self._trace_info,
            )
            return True
        except Exception:
            return False
        finally:
            self.expressions = expr

    @pyaedt_function_handler()
    def apply_report_template(self, input_file, property_type="Graphical"):  # pragma: no cover
        """Apply report template.

        .. note::
            This method works in only in graphical mode.

        Parameters
        ----------
        input_file : str
            Path for the file to import. The extension supported is ``".rpt"``.
        property_type : str, optional
            Property types to apply. Options are ``"Graphical"``, ``"Data"``, and ``"All"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.ApplyReportTemplate
        """
        if not os.path.exists(input_file):  # pragma: no cover
            msg = "File does not exist."
            self._post.logger.error(msg)
            return False

        split_path = os.path.splitext(input_file)
        extension = split_path[1]

        supported_ext = [".rpt"]
        if extension not in supported_ext:  # pragma: no cover
            msg = f"Extension {extension} is not supported."
            self._post.logger.error(msg)
            return False

        if property_type not in ["Graphical", "Data", "All"]:  # pragma: no cover
            msg = "Invalid value for `property_type`. The value must be 'Graphical', 'Data', or 'All'."
            self._post.logger.error(msg)
            return False
        self._post.oreportsetup.ApplyReportTemplate(self.plot_name, input_file, property_type)
        return True

    @staticmethod
    @pyaedt_function_handler()
    def __props_with_default(dict_in, key, default_value=None):
        """Update dictionary value."""
        return dict_in[key] if dict_in.get(key, None) is not None else default_value
