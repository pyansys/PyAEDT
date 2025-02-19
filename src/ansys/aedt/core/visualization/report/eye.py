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

"""
This module contains these classes: `AMIConturEyeDiagram`, `AMIEyeDiagram`, and `EyeDiagram`.

This module provides all functionalities for creating and editing reports.

"""
import os

from ansys.aedt.core.generic.general_methods import generate_unique_name
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.modeler.cad.elements_3d import BinaryTreeNode
from ansys.aedt.core.visualization.report.common import CommonReport


class AMIConturEyeDiagram(CommonReport):
    """Provides for managing eye contour diagram reports in AMI analysis."""

    def __init__(self, app, report_category, setup_name, expressions=None):
        CommonReport.__init__(self, app, report_category, setup_name, expressions)
        self.domain = "Time"
        self._legacy_props["report_type"] = "Rectangular Contour Plot"
        self.variations.pop("Time", None)
        self._legacy_props["context"]["variations"]["__UnitInterval"] = ["All"]
        self._legacy_props["context"]["variations"]["__Amplitude"] = ["All"]
        self._legacy_props["context"]["variations"]["__EyeOpening"] = ["0"]
        self._legacy_props["context"]["primary_sweep"] = "__UnitInterval"
        self._legacy_props["context"]["secondary_sweep"] = "__Amplitude"
        self.quantity_type = 0
        self.min_latch_overlay = "0"
        self.noise_floor = "1e-16"
        self.enable_jitter_distribution = False
        self.rx_rj = "0"
        self.rx_dj = "0"
        self.rx_sj = "0"
        self.rx_dcd = "0"
        self.rx_gaussian_noise = "0"
        self.rx_uniform_noise = "0"

    @property
    def expressions(self):
        """Expressions.

        Returns
        -------
        list
            Expressions.
        """
        if self._is_created:
            return [i.split(" ,")[-1] for i in list(self.properties.values())[4:]]
        if self._legacy_props.get("expressions", None) is None:
            return []
        expr_head = "Eye"
        new_exprs = []
        for expr_dict in self._legacy_props["expressions"]:
            expr = expr_dict["name"]
            if not ".int_ami" in expr:
                qtype = int(self.quantity_type)
                if qtype == 0:
                    new_exprs.append(f"Initial{expr_head}(" + expr + ".int_ami_tx)<Bit Error Rate>")
                elif qtype == 1:
                    new_exprs.append(f"{expr_head}AfterSource(" + expr + ".int_ami_tx)<Bit Error Rate>")
                elif qtype == 2:
                    new_exprs.append(f"{expr_head}AfterChannel(" + expr + ".int_ami_rx)<Bit Error Rate>")
                elif qtype == 3:
                    new_exprs.append(f"{expr_head}AfterProbe(" + expr + ".int_ami_rx)<Bit Error Rate>")
            else:
                new_exprs.append(expr)
        return new_exprs

    @expressions.setter
    def expressions(self, value):
        if isinstance(value, dict):
            self._legacy_props["expressions"].append = value
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
    def quantity_type(self):
        """Quantity type used in the AMI analysis plot.

        Returns
        -------
        int
            Quantity type.
        """
        return self._legacy_props.get("quantity_type", 0)

    @quantity_type.setter
    def quantity_type(self, value):
        self._legacy_props["quantity_type"] = value

    @property
    def _context(self):
        if self.primary_sweep == "__InitialTime":
            cid = 55824
        else:
            cid = 55819
        sim_context = [
            cid,
            0,
            2,
            0,
            False,
            False,
            -1,
            1,
            0,
            1,
            1,
            "",
            0,
            0,
            "MLO",
            False,
            str(self.min_latch_overlay),
            "NUMLEVELS",
            False,
            "1",
            "ORJ",
            False,
            "1",
            "PCID",
            False,
            "-1",
            "PID",
            False,
            "0",
            "PRIDIST",
            False,
            "0",
            "QTID",
            False,
            str(self.quantity_type),
            "USE_PRI_DIST",
            False,
            "0" if not self.enable_jitter_distribution else "1",
            "SID",
            False,
            "0",
        ]
        if self.enable_jitter_distribution and str(self.quantity_type) == "3":
            sim_context = [
                55819,
                0,
                2,
                0,
                False,
                False,
                -1,
                1,
                0,
                1,
                1,
                "",
                0,
                0,
                "DCD",
                False,
                str(self.rx_dcd),
                "DJ",
                False,
                str(self.rx_dj),
                "GNOI",
                False,
                "3.5",
                "MLO",
                False,
                str(self.min_latch_overlay),
                "NF",
                False,
                str(self.noise_floor),
                "NUMLEVELS",
                False,
                "1",
                "ORJ",
                False,
                "1",
                "PCID",
                False,
                "-1",
                "PID",
                False,
                "0",
                "SID",
                False,
                "0",
                "PRIDIST",
                False,
                "0",
                "QTID",
                False,
                str(self.quantity_type),
                "RJ",
                False,
                str(self.rx_rj),
                "SJ",
                False,
                str(self.rx_sj),
                "UNOI",
                False,
                str(self.rx_uniform_noise),
                "USE_PRI_DIST",
                False,
                "0" if not self.enable_jitter_distribution else "1",
            ]

        arg = [
            "NAME:Context",
            "SimValueContext:=",
            sim_context,
        ]
        if len(self.expressions) == 1:
            sid = 0
            pid = 0
            expr = self.expressions[0]
            category = "Eye"
            found = False
            while not found:
                available_quantities = self._post.available_report_quantities(
                    self.report_category, self.report_type, self.setup, category, arg
                )
                if len(available_quantities) == 1 and available_quantities[0].lower() == expr.lower():
                    found = True
                else:
                    sid += 1
                    pid += 1
                    arg[2][arg[2].index("SID") + 2] = str(sid)
                    arg[2][arg[2].index("PID") + 2] = str(pid)
                # Limited maximum iterations to 1000 in While loop (Too many probes to analyze even in a single design)
                if sid > 1000:
                    self._post.logger.error(
                        f"Failed to find right context for expression : {','.join(self.expressions)}"
                    )
                    # arg[2][arg[2].index("SID") + 2] = "0"
                    # arg[2][arg[2].index("PID") + 2] = "0"
                    break
        return arg

    @property
    def _trace_info(self):
        new_exprs = self.expressions if isinstance(self.expressions, list) else [self.expressions]
        if self.secondary_sweep:
            return ["X Component:=", self.primary_sweep, "Y Component:=", "__Amplitude", "Z Component:=", new_exprs]
        else:
            return ["X Component:=", self.primary_sweep, "Y Component:=", new_exprs]

    @pyaedt_function_handler()
    def create(self, name=None):
        """Create an eye diagram report.

        Parameters
        ----------
        name : str, optional
            Plot name. The default is ``None``, in which case
            the default name is used.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if not name:
            self.plot_name = generate_unique_name("Plot")
        else:
            self.plot_name = name
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
        oo = self._post.oreportsetup.GetChildObject(self._legacy_props["plot_name"])
        if oo:
            BinaryTreeNode.__init__(self, self.plot_name, oo, False)
        return True

    @pyaedt_function_handler(xunits="x_units", yunits="y_units", xoffset="x_offset", yoffset="y_offset")
    def eye_mask(
        self,
        points,
        x_units="ns",
        y_units="mV",
        enable_limits=False,
        upper_limit=500,
        lower_limit=-500,
        color=(0, 255, 0),
        x_offset="0ns",
        y_offset="0V",
        transparency=0.3,
    ):
        """Create an eye diagram in the plot.

        Parameters
        ----------
        points : list
            Points of the eye mask in the format ``[[x1,y1,],[x2,y2],...]``.
        x_units : str, optional
            X points units. The default is ``"ns"``.
        y_units : str, optional
            Y points units. The default is ``"mV"``.
        enable_limits : bool, optional
            Whether to enable the upper and lower limits. The default is ``False``.
        upper_limit : float, optional
            Upper limit if limits are enabled. The default is ``500``.
        lower_limit : str, optional
            Lower limit if limits are enabled. The default is ``-500``.
        color : tuple, optional
            Mask in (R, G, B) color. The default is ``(0, 255, 0)``.
            Each color value must be an integer in a range from 0 to 255.
        x_offset : str, optional
            Mask time offset with units. The default is ``"0ns"``.
        y_offset : str, optional
            Mask value offset with units. The default is ``"0V"``.
        transparency : float, optional
            Mask transparency. The default is ``0.3``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if "quantity_type" in dir(self) and self.report_type == "Rectangular Contour Plot":
            props = [
                "NAME:AllTabs",
                ["NAME:Mask", ["NAME:PropServers", f"{self.plot_name}: Plot {self.traces[0].name}"]],
            ]
        else:
            props = [
                "NAME:AllTabs",
                ["NAME:Mask", ["NAME:PropServers", f"{self.plot_name}:EyeDisplayTypeProperty"]],
            ]
        arg = [
            "NAME:Mask",
            "Version:=",
            1,
            "ShowLimits:=",
            enable_limits,
            "UpperLimit:=",
            upper_limit if upper_limit else 1,
            "LowerLimit:=",
            lower_limit if lower_limit else 0,
            "XUnits:=",
            x_units,
            "YUnits:=",
            y_units,
        ]
        mask_points = ["NAME:MaskPoints"]
        for point in points:
            mask_points.append(point[0])
            mask_points.append(point[1])
        arg.append(mask_points)
        args = ["NAME:ChangedProps", arg]
        if not ("quantity_type" in dir(self) and self.report_type == "Rectangular Contour Plot"):
            args.append(["NAME:Mask Fill Color", "R:=", color[0], "G:=", color[1], "B:=", color[2]])
            args.append(["NAME:X Offset", "Value:=", x_offset])
            args.append(["NAME:Y Offset", "Value:=", y_offset])
            args.append(["NAME:Mask Trans", "Transparency:=", transparency])
        props[1].append(args)
        self._post.oreportsetup.ChangeProperty(props)

        return True

    @pyaedt_function_handler(value="enable")
    def rectangular_plot(self, enable=True):
        """Enable or disable the rectangular plot on the chart.

        Parameters
        ----------
        enable : bool
            Whether to enable the rectangular plot. The default is ``True``. If
            ``False``, the rectangular plot is disabled.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        props = [
            "NAME:AllTabs",
            ["NAME:Eye", ["NAME:PropServers", f"{self.plot_name}:EyeDisplayTypeProperty"]],
        ]
        args = ["NAME:ChangedProps", ["NAME:Rectangular Plot", "Value:=", enable]]
        props[1].append(args)
        self._post.oreportsetup.ChangeProperty(props)

        return True

    @pyaedt_function_handler()
    def add_all_eye_measurements(self):
        """Add all eye measurements to the plot.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        self._post.oreportsetup.AddAllEyeMeasurements(self.plot_name)
        return True

    @pyaedt_function_handler()
    def clear_all_eye_measurements(self):
        """Clear all eye measurements from the plot.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        self._post.oreportsetup.ClearAllTraceCharacteristics(self.plot_name)
        return True

    @pyaedt_function_handler(out_file="output_file")
    def export_mask_violation(self, output_file=None):
        """Export the eye diagram mask violations to a TAB file.

        Parameters
        ----------
        output_file : str, optional
            Full path to the TAB file. The default is ``None``, in which case
            the violations are exported to a TAB file in the working directory.

        Returns
        -------
        str
            Output file path if a TAB file is created.
        """
        if not output_file:
            output_file = os.path.join(self._post._app.working_directory, f"{self.plot_name}_violations.tab")
        self._post.oreportsetup.ExportEyeMaskViolation(self.plot_name, output_file)
        return output_file


class AMIEyeDiagram(CommonReport):
    """Provides for managing eye diagram reports."""

    def __init__(self, app, report_category, setup_name, expressions=None):
        CommonReport.__init__(self, app, report_category, setup_name, expressions)
        self.domain = "Time"
        if report_category == "Statistical Eye":
            self._legacy_props["report_type"] = "Statistical Eye Plot"
            self.variations.pop("Time", None)
            self.variations["__UnitInterval"] = "All"
            self.variations["__Amplitude"] = "All"
        self.unit_interval = "0s"
        self.offset = "0ms"
        self.auto_delay = True
        self.manual_delay = "0ps"
        self.auto_cross_amplitude = True
        self.cross_amplitude = "0mV"
        self.auto_compute_eye_meas = True
        self.eye_measurement_point = "5e-10s"
        self.quantity_type = 0

    @property
    def expressions(self):
        """Expressions.

        Returns
        -------
        list
            Expressions.
        """
        if self._is_created:
            return [i.split(" ,")[-1] for i in list(self.properties.values())[4:]]
        if self._legacy_props.get("expressions", None) is None:
            return []
        expr_head = "Wave"
        if self.report_category == "Statistical Eye":
            expr_head = "Eye"
        new_exprs = []
        for expr_dict in self._legacy_props["expressions"]:
            expr = expr_dict["name"]
            if not ".int_ami" in expr:
                qtype = int(self.quantity_type)
                if qtype == 0:
                    new_exprs.append(f"Initial{expr_head}<" + expr + ".int_ami_tx>")
                elif qtype == 1:
                    new_exprs.append(f"{expr_head}AfterSource<" + expr + ".int_ami_tx>")
                elif qtype == 2:
                    new_exprs.append(f"{expr_head}AfterChannel<" + expr + ".int_ami_rx>")
                elif qtype == 3:
                    new_exprs.append(f"{expr_head}AfterProbe<" + expr + ".int_ami_rx>")
                else:
                    new_exprs.append(expr)
            else:
                new_exprs.append(expr)
        return new_exprs

    @property
    def quantity_type(self):
        """Quantity type used in the AMI analysis plot.

        Returns
        -------
        int
            Quantity type.
        """
        return self._legacy_props.get("quantity_type", 0)

    @quantity_type.setter
    def quantity_type(self, value):
        self._legacy_props["quantity_type"] = value

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
                return self.properties.props["Report Type"]
            except Exception:
                return self._legacy_props["report_category"]
        return self._legacy_props["report_category"]

    @report_category.setter
    def report_category(self, value):
        self._legacy_props["report_category"] = value
        if self._legacy_props["report_category"] == "Statistical Eye" and self.report_type == "Rectangular Plot":
            self._legacy_props["report_type"] = "Statistical Eye Plot"
            self.variations.pop("Time", None)
            self.variations["__UnitInterval"] = "All"
            self.variations["__Amplitude"] = "All"
        elif self._legacy_props["report_category"] == "Eye Diagram" and self.report_type == "Statistical Eye Plot":
            self._legacy_props["report_type"] = "Rectangular Plot"
            self.variations.pop("__UnitInterval", None)
            self.variations.pop("__Amplitude", None)
            self.variations["Time"] = "All"

    @property
    def unit_interval(self):
        """Unit interval value.

        Returns
        -------
        str
            Unit interval.
        """
        return self._legacy_props["context"].get("unit_interval", None)

    @unit_interval.setter
    def unit_interval(self, value):
        self._legacy_props["context"]["unit_interval"] = value

    @property
    def offset(self):
        """Offset value.

        Returns
        -------
        str
            Offset value.
        """
        return self._legacy_props["context"].get("offset", None)

    @offset.setter
    def offset(self, value):
        self._legacy_props["context"]["offset"] = value

    @property
    def auto_delay(self):
        """Auto-delay flag.

        Returns
        -------
        bool
            ``True`` if auto-delay is enabled, ``False`` otherwise.
        """
        return self._legacy_props["context"].get("auto_delay", None)

    @auto_delay.setter
    def auto_delay(self, value):
        self._legacy_props["context"]["auto_delay"] = value

    @property
    def manual_delay(self):
        """Manual delay value when ``auto_delay=False``.

        Returns
        -------
        str
            ``True`` if manual-delay is enabled, ``False`` otherwise.
        """
        return self._legacy_props["context"].get("manual_delay", None)

    @manual_delay.setter
    def manual_delay(self, value):
        self._legacy_props["context"]["manual_delay"] = value

    @property
    def auto_cross_amplitude(self):
        """Auto-cross amplitude flag.

        Returns
        -------
        bool
            ``True`` if auto-cross amplitude is enabled, ``False`` otherwise.
        """
        return self._legacy_props["context"].get("auto_cross_amplitude", None)

    @auto_cross_amplitude.setter
    def auto_cross_amplitude(self, value):
        self._legacy_props["context"]["auto_cross_amplitude"] = value

    @property
    def cross_amplitude(self):
        """Cross-amplitude value when ``auto_cross_amplitude=False``.

        Returns
        -------
        str
            Cross-amplitude.
        """
        return self._legacy_props["context"].get("cross_amplitude", None)

    @cross_amplitude.setter
    def cross_amplitude(self, value):
        self._legacy_props["context"]["cross_amplitude"] = value

    @property
    def auto_compute_eye_meas(self):
        """Flag for automatically computing eye measurements.

        Returns
        -------
        bool
            ``True`` to compute eye measurements, ``False`` otherwise.
        """
        return self._legacy_props["context"].get("auto_compute_eye_meas", None)

    @auto_compute_eye_meas.setter
    def auto_compute_eye_meas(self, value):
        self._legacy_props["context"]["auto_compute_eye_meas"] = value

    @property
    def eye_measurement_point(self):
        """Eye measurement point.

        Returns
        -------
        str
            Eye measurement point.
        """
        return self._legacy_props["context"].get("eye_measurement_point", None)

    @eye_measurement_point.setter
    def eye_measurement_point(self, value):
        self._legacy_props["context"]["eye_measurement_point"] = value

    @property
    def _context(self):
        arg = [
            "NAME:Context",
            "SimValueContext:=",
            [
                1,
                0,
                2,
                0,
                False,
                False,
                -1,
                1,
                0,
                1,
                1,
                "",
                0,
                0,
                "-1",
                False,
                "0",
                "NUMLEVELS",
                False,
                "1",
                "PCID",
                False,
                "-1",
                "PID",
                False,
                "0",
                "QTID",
                False,
                str(self.quantity_type),
                "SCID",
                False,
                "-1",
                "SID",
                False,
                "0",
            ],
        ]
        if self.report_category == "Statistical Eye":
            arg = [
                "NAME:Context",
                "SimValueContext:=",
                [
                    55819,
                    0,
                    2,
                    0,
                    False,
                    False,
                    -1,
                    1,
                    0,
                    1,
                    1,
                    "",
                    0,
                    0,
                    "NUMLEVELS",
                    False,
                    "1",
                    "PCID",
                    False,
                    "-1",
                    "PID",
                    False,
                    "0",
                    "QTID",
                    False,
                    str(self.quantity_type),
                    "SCID",
                    False,
                    "-1",
                    "SID",
                    False,
                    "0",
                ],
            ]
        if len(self.expressions) == 1:
            sid = 0
            pid = 0
            expr = self.expressions[0]
            category = "Wave"
            if self.report_category == "Statistical Eye":
                category = "Eye"
            if self.report_category == "Eye Diagram" and self.report_type == "Rectangular Plot":
                category = "Voltage"
            found = False
            while not found:
                available_quantities = self._post.available_report_quantities(
                    self.report_category, self.report_type, self.setup, category, arg
                )
                if len(available_quantities) == 1 and available_quantities[0].lower() == expr.lower():
                    found = True
                else:
                    sid += 1
                    pid += 1
                    arg[2][arg[2].index("SID") + 2] = str(sid)
                    arg[2][arg[2].index("PID") + 2] = str(pid)
                # Limited maximum iterations to 1000 in While loop (Too many probes to analyze even in a single design)
                if sid > 1000:
                    self._post.logger.error(
                        f"Failed to find right context for expression : {','.join(self.expressions)}"
                    )
                    # arg[2][arg[2].index("SID") + 2] = "0"
                    # arg[2][arg[2].index("PID") + 2] = "0"
                    break
        return arg

    @property
    def _trace_info(self):
        new_exprs = self.expressions if isinstance(self.expressions, list) else [self.expressions]
        if self.report_category == "Statistical Eye":
            return [
                "X Component:=",
                "__UnitInterval",
                "Y Component:=",
                "__Amplitude",
                "Eye Diagram Component:=",
                new_exprs,
            ]
        return ["Component:=", new_exprs]

    @pyaedt_function_handler()
    def create(self, name=None):
        """Create an eye diagram report.

        Parameters
        ----------
        name : str, optional
            Plot name. The default is ``None``, in which case
            the default name is used.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if not name:
            self.plot_name = generate_unique_name("Plot")
        else:
            self.plot_name = name
        options = [
            "Unit Interval:=",
            self.unit_interval,
            "Offset:=",
            self.offset,
            "Auto Delay:=",
            self.auto_delay,
            "Manual Delay:=",
            self.manual_delay,
            "AutoCompCrossAmplitude:=",
            self.auto_cross_amplitude,
            "CrossingAmplitude:=",
            self.cross_amplitude,
            "AutoCompEyeMeasurementPoint:=",
            self.auto_compute_eye_meas,
            "EyeMeasurementPoint:=",
            self.eye_measurement_point,
        ]
        if self.report_category == "Statistical Eye":
            self._post.oreportsetup.CreateReport(
                self.plot_name,
                self.report_category,
                self.report_type,
                self.setup,
                self._context,
                self._convert_dict_to_report_sel(self.variations),
                self._trace_info,
            )
        else:
            self._post.oreportsetup.CreateReport(
                self.plot_name,
                self.report_category,
                self.report_type,
                self.setup,
                self._context,
                self._convert_dict_to_report_sel(self.variations),
                self._trace_info,
                options,
            )
        self._post.plots.append(self)
        self._is_created = True
        oo = self._post.oreportsetup.GetChildObject(self._legacy_props["plot_name"])
        if oo:
            BinaryTreeNode.__init__(self, self.plot_name, oo, False)
        return True

    @pyaedt_function_handler(xunits="x_units", yunits="y_units", xoffset="x_offset", yoffset="y_offset")
    def eye_mask(
        self,
        points,
        x_units="ns",
        y_units="mV",
        enable_limits=False,
        upper_limit=500,
        lower_limit=-500,
        color=(0, 255, 0),
        x_offset="0ns",
        y_offset="0V",
        transparency=0.3,
    ):
        """Create an eye diagram in the plot.

        Parameters
        ----------
        points : list
            Points of the eye mask in the format ``[[x1,y1,],[x2,y2],...]``.
        x_units : str, optional
            X points units. The default is ``"ns"``.
        y_units : str, optional
            Y points units. The default is ``"mV"``.
        enable_limits : bool, optional
            Whether to enable the upper and lower limits. The default is ``False``.
        upper_limit : float, optional
            Upper limit if limits are enabled. The default is ``500``.
        lower_limit : str, optional
            Lower limit if limits are enabled. The default is ``-500``.
        color : tuple, optional
            Mask in (R, G, B) color. The default is ``(0, 255, 0)``.
            Each color value must be an integer in a range from 0 to 255.
        x_offset : str, optional
            Mask time offset with units. The default is ``"0ns"``.
        y_offset : str, optional
            Mask value offset with units. The default is ``"0V"``.
        transparency : float, optional
            Mask transparency. The default is ``0.3``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        props = [
            "NAME:AllTabs",
            ["NAME:Mask", ["NAME:PropServers", f"{self.plot_name}:EyeDisplayTypeProperty"]],
        ]
        arg = [
            "NAME:Mask",
            "Version:=",
            1,
            "ShowLimits:=",
            enable_limits,
            "UpperLimit:=",
            upper_limit if upper_limit else 1,
            "LowerLimit:=",
            lower_limit if lower_limit else 0,
            "XUnits:=",
            x_units,
            "YUnits:=",
            y_units,
        ]
        mask_points = ["NAME:MaskPoints"]
        for point in points:
            mask_points.append(point[0])
            mask_points.append(point[1])
        arg.append(mask_points)
        args = ["NAME:ChangedProps", arg]
        args.append(["NAME:Mask Fill Color", "R:=", color[0], "G:=", color[1], "B:=", color[2]])
        args.append(["NAME:X Offset", "Value:=", x_offset])
        args.append(["NAME:Y Offset", "Value:=", y_offset])
        args.append(["NAME:Mask Trans", "Transparency:=", transparency])
        props[1].append(args)
        self._post.oreportsetup.ChangeProperty(props)

        return True

    @pyaedt_function_handler(value="enable")
    def rectangular_plot(self, enable=True):
        """Enable or disable the rectangular plot on the chart.

        Parameters
        ----------
        enable : bool
            Whether to enable the rectangular plot. The default is ``True``. When
            ``False``, the rectangular plot is disabled.

        Returns
        -------
        bool
        """
        props = [
            "NAME:AllTabs",
            ["NAME:Eye", ["NAME:PropServers", f"{self.plot_name}:EyeDisplayTypeProperty"]],
        ]
        args = ["NAME:ChangedProps", ["NAME:Rectangular Plot", "Value:=", enable]]
        props[1].append(args)
        self._post.oreportsetup.ChangeProperty(props)

        return True

    @pyaedt_function_handler()
    def add_all_eye_measurements(self):
        """Add all eye measurements to the plot.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        self._post.oreportsetup.AddAllEyeMeasurements(self.plot_name)
        return True

    @pyaedt_function_handler()
    def clear_all_eye_measurements(self):
        """Clear all eye measurements from the plot.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        self._post.oreportsetup.ClearAllTraceCharacteristics(self.plot_name)
        return True

    @pyaedt_function_handler(out_file="output_file")
    def export_mask_violation(self, output_file=None):
        """Export the eye diagram mask violations to a TAB file.

        Parameters
        ----------
        output_file : str, optional
            Full path to the TAB file. The default is ``None``, in which case
            the violations are exported to a TAB file in the working directory.

        Returns
        -------
        str
            Output file path if a TAB file is created.
        """
        if not output_file:
            output_file = os.path.join(self._post._app.working_directory, f"{self.plot_name}_violations.tab")
        self._post.oreportsetup.ExportEyeMaskViolation(self.plot_name, output_file)
        return output_file


class EyeDiagram(AMIEyeDiagram):
    """Provides for managing eye diagram reports."""

    def __init__(self, app, report_category, setup_name, expressions=None):
        AMIEyeDiagram.__init__(self, app, report_category, setup_name, expressions)
        self.time_start = "0ns"
        self.time_stop = "200ns"
        self.thinning = False
        self.dy_dx_tolerance = 0.001
        self.thinning_points = 500000000

    @property
    def expressions(self):
        """Expressions.

        Returns
        -------
        list
            Expressions.
        """
        if self._is_created:
            return [i.split(" ,")[-1] for i in list(self.properties.values())[4:]]
        if self._legacy_props.get("expressions", None) is None:
            return []
        return [k.get("name", None) for k in self._legacy_props["expressions"] if k.get("name", None) is not None]

    @expressions.setter
    def expressions(self, value):
        if isinstance(value, dict):
            self._legacy_props["expressions"].append = value
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
    def time_start(self):
        """Time start value.

        Returns
        -------
        str
            Time start.
        """
        return self._legacy_props["context"].get("time_start", None)

    @time_start.setter
    def time_start(self, value):
        self._legacy_props["context"]["time_start"] = value

    @property
    def time_stop(self):
        """Time stop value.

        Returns
        -------
        str
            Time stop.
        """
        return self._legacy_props["context"].get("time_stop", None)

    @time_stop.setter
    def time_stop(self, value):
        self._legacy_props["context"]["time_stop"] = value

    @property
    def thinning(self):
        """Thinning flag.

        Returns
        -------
        bool
            ``True`` if thinning is enabled, ``False`` otherwise.
        """
        return self._legacy_props["context"].get("thinning", None)

    @thinning.setter
    def thinning(self, value):
        self._legacy_props["context"]["thinning"] = value

    @property
    def dy_dx_tolerance(self):
        """DY DX tolerance.

        Returns
        -------
        float
            DY DX tolerance.
        """
        return self._legacy_props["context"].get("dy_dx_tolerance", None)

    @dy_dx_tolerance.setter
    def dy_dx_tolerance(self, value):
        self._legacy_props["context"]["dy_dx_tolerance"] = value

    @property
    def thinning_points(self):
        """Number of thinning points.

        Returns
        -------
        int
            Number of thinning points.
        """
        return self._legacy_props["context"].get("thinning_points", None)

    @thinning_points.setter
    def thinning_points(self, value):
        self._legacy_props["context"]["thinning_points"] = value

    @property
    def _context(self):
        if self.thinning:
            val = "1"
        else:
            val = "0"
        arg = [
            "NAME:Context",
            "SimValueContext:=",
            [
                1,
                0,
                2,
                0,
                False,
                False,
                -1,
                1,
                0,
                1,
                1,
                "",
                0,
                0,
                "DE",
                False,
                val,
                "DP",
                False,
                str(self.thinning_points),
                "DT",
                False,
                str(self.dy_dx_tolerance),
                "NUMLEVELS",
                False,
                "0",
                "WE",
                False,
                self.time_stop,
                "WM",
                False,
                "200ns",
                "WN",
                False,
                "0ps",
                "WS",
                False,
                self.time_start,
            ],
        ]
        return arg

    @property
    def _trace_info(self):
        if isinstance(self.expressions, list):
            return ["Component:=", self.expressions]
        else:
            return ["Component:=", [self.expressions]]
