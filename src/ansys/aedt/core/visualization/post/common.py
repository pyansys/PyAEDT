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
This module contains this class: `PostProcessorCommon`.

This module provides all functionalities for common AEDT post processing.

"""

from __future__ import absolute_import  # noreorder

import os
import re

from ansys.aedt.core.generic.data_handlers import _dict_items_to_list_items
from ansys.aedt.core.generic.general_methods import generate_unique_name
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.generic.general_methods import read_configuration_file
from ansys.aedt.core.visualization.plot.matplotlib import ReportPlotter
from ansys.aedt.core.visualization.post.solution_data import SolutionData
from ansys.aedt.core.visualization.report.constants import TEMPLATES_BY_DESIGN
import ansys.aedt.core.visualization.report.emi
import ansys.aedt.core.visualization.report.eye
import ansys.aedt.core.visualization.report.field
import ansys.aedt.core.visualization.report.standard

TEMPLATES_BY_NAME = {
    "Standard": ansys.aedt.core.visualization.report.standard.Standard,
    "EddyCurrent": ansys.aedt.core.visualization.report.standard.Standard,
    "Modal Solution Data": ansys.aedt.core.visualization.report.standard.Standard,
    "Terminal Solution Data": ansys.aedt.core.visualization.report.standard.Standard,
    "Fields": ansys.aedt.core.visualization.report.field.Fields,
    "CG Fields": ansys.aedt.core.visualization.report.field.Fields,
    "DC R/L Fields": ansys.aedt.core.visualization.report.field.Fields,
    "AC R/L Fields": ansys.aedt.core.visualization.report.field.Fields,
    "Matrix": ansys.aedt.core.visualization.report.standard.Standard,
    "Monitor": ansys.aedt.core.visualization.report.standard.Standard,
    "Far Fields": ansys.aedt.core.visualization.report.field.FarField,
    "Near Fields": ansys.aedt.core.visualization.report.field.NearField,
    "Eye Diagram": ansys.aedt.core.visualization.report.eye.EyeDiagram,
    "Statistical Eye": ansys.aedt.core.visualization.report.eye.AMIEyeDiagram,
    "AMI Contour": ansys.aedt.core.visualization.report.eye.AMIConturEyeDiagram,
    "Eigenmode Parameters": ansys.aedt.core.visualization.report.standard.Standard,
    "Spectrum": ansys.aedt.core.visualization.report.standard.Spectral,
    "EMIReceiver": ansys.aedt.core.visualization.report.emi.EMIReceiver,
}


class PostProcessorCommon(object):
    """Manages the main AEDT postprocessing functions.

    This class is inherited in the caller application and is accessible through the post variable( eg. ``hfss.post`` or
    ``q3d.post``).

    .. note::
       Some functionalities are available only when AEDT is running in
       the graphical mode.

    Parameters
    ----------
    app : :class:`ansys.aedt.core.application.analysis_3d.FieldAnalysis3D`
        Inherited parent object. The parent object must provide the members
        ``_modeler``, ``_desktop``, ``_odesign``, and ``logger``.

    Examples
    --------
    >>> from ansys.aedt.core import Q3d
    >>> q3d = Q3d()
    >>> q.post.get_solution_data(domain="Original")
    """

    def __init__(self, app):
        self._app = app
        self._scratch = self._app.working_directory
        self.plots = self._get_plot_inputs()
        self.reports_by_category = Reports(self, self._app.design_type)

    @property
    def available_report_types(self):
        """Report types.

        References
        ----------
        >>> oModule.GetAvailableReportTypes
        """
        return list(self.oreportsetup.GetAvailableReportTypes())

    @property
    def update_report_dynamically(self):
        """Get/Set the boolean to automatically update reports on edits.

        Returns
        -------
        bool
        """
        return (
            True
            if self._app.odesktop.GetRegistryInt(
                f"Desktop/Settings/ProjectOptions/{self._app.design_type}/UpdateReportsDynamicallyOnEdits"
            )
            == 1
            else False
        )

    @update_report_dynamically.setter
    def update_report_dynamically(self, value):
        if value:
            self._app.odesktop.SetRegistryInt(
                f"Desktop/Settings/ProjectOptions/{self._app.design_type}/UpdateReportsDynamicallyOnEdits", 1
            )
        else:  # pragma: no cover
            self._app.odesktop.SetRegistryInt(
                f"Desktop/Settings/ProjectOptions/{self._app.design_type}/UpdateReportsDynamicallyOnEdits", 0
            )

    @pyaedt_function_handler()
    def available_display_types(self, report_category=None) -> list:
        """Retrieve display types for a report categories.

        Parameters
        ----------
        report_category : str, optional
            Type of the report. The default value is ``None``.

        Returns
        -------
        list
            List of available report categories.

        References
        ----------
        >>> oModule.GetAvailableDisplayTypes
        """
        if not report_category:
            report_category = self.available_report_types[0]
        if report_category:
            return list(self.oreportsetup.GetAvailableDisplayTypes(report_category))
        return []  # pragma: no cover

    @pyaedt_function_handler()
    def available_quantities_categories(
        self, report_category=None, display_type=None, solution=None, context=None, is_siwave_dc=False
    ):
        """Compute the list of all available report categories.

        Parameters
        ----------
        report_category : str, optional
            Report category. The default is ``None``, in which case the first default category is used.
        display_type : str, optional
            Report display type. The default is ``None``, in which case the first default type
             is used. In most cases, this default type is ``"Rectangular Plot"``.
        solution : str, optional
            Report setup. The default is ``None``, in which case the first
            nominal adaptive solution is used.
        context : str, dict, optional
            Report category. The default is ``None``, in which case the first default context
            is used. For Maxwell 2D/3D eddy current solution types, the report category
            can be provided as a dictionary, where the key is the matrix name and the value
            the reduced matrix.
        is_siwave_dc : bool, optional
            Whether the setup is SIwave DCIR. The default is ``False``.

        Returns
        -------
        list

        References
        ----------
        >>> oModule.GetAllCategories
        """
        if not report_category:
            report_category = self.available_report_types[0]
        if not display_type:
            display_type = self.available_display_types(report_category)[0]
        if not solution and hasattr(self._app, "nominal_adaptive"):
            solution = self._app.nominal_adaptive
        if is_siwave_dc:  # pragma: no cover
            id_ = "0"
            if context:
                id_ = str(
                    [
                        "RL",
                        "Sources",
                        "Vias",
                        "Bondwires",
                        "Probes",
                    ].index(context)
                )
            context = [
                "NAME:Context",
                "SimValueContext:=",
                [37010, 0, 2, 0, False, False, -1, 1, 0, 1, 1, "", 0, 0, "DCIRID", False, id_, "IDIID", False, "1"],
            ]
        elif self._app.design_type in ["Maxwell 2D", "Maxwell 3D"] and self._app.solution_type in [
            "EddyCurrent",
            "Electrostatic",
        ]:
            if isinstance(context, dict):
                for k, v in context.items():
                    context = ["Context:=", k, "Matrix:=", v]
            elif context and isinstance(context, str):
                context = ["Context:=", context]
            elif not context:
                context = ""
        elif not context:  # pragma: no cover
            context = ""

        if solution and report_category and display_type:
            return list(self.oreportsetup.GetAllCategories(report_category, display_type, solution, context))
        return []  # pragma: no cover

    @pyaedt_function_handler()
    def available_report_quantities(
        self,
        report_category=None,
        display_type=None,
        solution=None,
        quantities_category=None,
        context=None,
        is_siwave_dc=False,
        differential_pairs=False,
    ):
        """Compute the list of all available report quantities of a given report quantity category.

        Parameters
        ----------
        report_category : str, optional
            Report Category. The default is ``None``, in which case the default category is used.
        display_type : str, optional
            Report Display Type.
            The default is ``None``, in which case the default type is used.
            In most of the cases the default type is "Rectangular Plot".
        solution : str, optional
            Report Setup.
            The default is ``None``, in which case the first nominal adaptive solution is used.
        quantities_category : str, optional
            The category that the quantities belong to.
            It must be one of the ``available_quantities_categories`` method.
            The default is ``None``, in which case the first default quantity is used.
        context : str, dict, optional
            Report Context.
            The default is ``None``, in which case the default context is used.
            For Maxwell 2D/3D Eddy Current solution types this can be provided as a dictionary
            where the key is the matrix name and value the reduced matrix.
        is_siwave_dc : bool, optional
            Whether if the setup is SIwave DCIR or not. Default is ``False``.
        differential_pairs : bool, optional
            Whether if return differential pairs traces or not. Default is ``False``.

        Returns
        -------
        list

        References
        ----------
        >>> oModule.GetAllQuantities

        Examples
        --------
        The example shows how to get report expressions for a Maxwell design with Eddy current solution.
        The context has to be provided as a dictionary where the key is the name of the original matrix
        and the value is the name of the reduced matrix.
        >>> from ansys.aedt.core import Maxwell3d
        >>> m3d = Maxwell3d(solution_type="EddyCurrent")
        >>> rectangle1 = m3d.modeler.create_rectangle(0, [0.5, 1.5, 0], [2.5, 5], name="Sheet1")
        >>> rectangle2 = m3d.modeler.create_rectangle(0, [9, 1.5, 0], [2.5, 5], name="Sheet2")
        >>> rectangle3 = m3d.modeler.create_rectangle(0, [16.5, 1.5, 0], [2.5, 5], name="Sheet3")
        >>> m3d.assign_current(rectangle1.faces[0], amplitude=1, name="Cur1")
        >>> m3d.assign_current(rectangle2.faces[0], amplitude=1, name="Cur2")
        >>> m3d.assign_current(rectangle3.faces[0], amplitude=1, name="Cur3")
        >>> L = m3d.assign_matrix(assignment=["Cur1", "Cur2", "Cur3"], matrix_name="Matrix1")
        >>> out = L.join_series(sources=["Cur1", "Cur2"], matrix_name="ReducedMatrix1")
        >>> expressions = m3d.post.available_report_quantities(report_category="EddyCurrent",
        ...                                                    display_type="Data Table",
        ...                                                    context={"Matrix1": "ReducedMatrix1"})
        >>> m3d.release_desktop(False, False)
        """
        if not report_category:
            report_category = self.available_report_types[0]
        if not display_type:
            display_type = self.available_display_types(report_category)[0]
        if not solution and hasattr(self._app, "nominal_adaptive"):
            solution = self._app.nominal_adaptive
        if is_siwave_dc:
            context_id = "0"
            if context:
                context_id = str(
                    [
                        "RL",
                        "Sources",
                        "Vias",
                        "Bondwires",
                        "Probes",
                    ].index(context)
                )
            context = [
                "NAME:Context",
                "SimValueContext:=",
                [
                    37010,
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
                    "DCIRID",
                    False,
                    context_id,
                    "IDIID",
                    False,
                    "1",
                ],
            ]
        elif differential_pairs:
            if self.post_solution_type in ["HFSS3DLayout"]:
                context = [
                    "NAME:Context",
                    "SimValueContext:=",
                    [
                        3,
                        0,
                        2,
                        3,
                        True,
                        False,
                        -1,
                        1,
                        0,
                        1,
                        1,
                        "",
                        0,
                        0,
                        "EnsDiffPairKey",
                        False,
                        "1",
                        "IDIID",
                        False,
                        "1",
                    ],
                ]
            elif self.post_solution_type in ["NexximLNA", "NexximTransient"]:
                context = [
                    "NAME:Context",
                    "SimValueContext:=",
                    [
                        3,
                        0,
                        2,
                        3,
                        True,
                        False,
                        -1,
                        1,
                        0,
                        1,
                        1,
                        "",
                        0,
                        0,
                        "USE_DIFF_PAIRS",
                        False,
                        "1",
                        "IDIID",
                        False,
                        "1",
                    ],
                ]
            else:
                context = ["Diff:=", "differential_pairs", "Domain:=", "Sweep"]
        elif self._app.design_type in ["Maxwell 2D", "Maxwell 3D"] and self._app.solution_type in [
            "EddyCurrent",
            "Electrostatic",
        ]:
            if isinstance(context, dict):
                for k, v in context.items():
                    context = ["Context:=", k, "Matrix:=", v]
            elif context and isinstance(context, str):
                context = ["Context:=", context]
            elif not context:
                context = ""
        elif not context:
            context = ""
        if not quantities_category:
            categories = self.available_quantities_categories(report_category, display_type, solution, context)
            if categories and display_type and report_category and solution:
                for el in categories:
                    res = list(self.oreportsetup.GetAllQuantities(report_category, display_type, solution, context, el))
                    if res:
                        return res
        if quantities_category and display_type and report_category and solution:
            return list(
                self.oreportsetup.GetAllQuantities(
                    report_category, display_type, solution, context, quantities_category
                )
            )
        return []  # pragma: no cover

    @pyaedt_function_handler()
    def get_all_report_quantities(
        self,
        solution=None,
        context=None,
        is_siwave_dc=False,
    ):
        """Return all the possible report categories organized by report types, solution and categories.

        Parameters
        ----------
        solution : str optional
            Solution to get the report quantities.
            The default is ``None``, in which case the all solutions are used.
        context : str, dict, optional
            Report Context.
            The default is ``None``, in which case the default context is used.
            For Maxwell 2D/3D Eddy Current solution types this can be provided as a dictionary
            where the key is the matrix name and value the reduced matrix.
        is_siwave_dc : bool, optional
            Whether if the setup is SIwave DCIR or not. Default is ``False``.

        Returns
        -------
        dict
            A dictionary with primary key the report type, secondary key the solution type and
            third key the report categories.
        """
        rep_quantities = {}
        for rep in self.available_report_types:
            rep_quantities[rep] = {}
            solutions = [solution] if isinstance(solution, str) else self.available_report_solutions(rep)
            for solution in solutions:
                rep_quantities[rep][solution] = {}
                for quant in self.available_quantities_categories(
                    rep, context=context, solution=solution, is_siwave_dc=is_siwave_dc
                ):
                    rep_quantities[rep][solution][quant] = self.available_report_quantities(
                        rep, quantities_category=quant, context=context, solution=solution, is_siwave_dc=is_siwave_dc
                    )

        return rep_quantities

    @pyaedt_function_handler()
    def available_report_solutions(self, report_category=None):
        """Get the list of available solutions that can be used for the reports.

        This list differs from the one obtained with ``app.existing_analysis_sweeps``,
        because it includes additional elements like "AdaptivePass".

        Parameters
        ----------
        report_category : str, optional
            Report Category. Default is ``None`` which takes default category.

        Returns
        -------
        list

        References
        ----------
        >>> oModule.GetAvailableSolutions
        """
        if not report_category:
            report_category = self.available_report_types[0]
        if report_category:
            return list(self.oreportsetup.GetAvailableSolutions(report_category))
        return None

    @pyaedt_function_handler()  # pragma: no cover
    def _get_setup_from_sweep_name(self, sweep_name):
        if ":" not in sweep_name:
            sweep_names = []  # Look for sweep name in setups if the setup is not
            for s in self._app.setups:  # passed explicitly in setup_sweep_name.
                for sweep in s.sweeps:
                    this_name = s.name + " : " + sweep.name if sweep.name == sweep_name else None
                    if this_name:
                        sweep_names.append(this_name)
            if len(sweep_names) > 1:
                warning_str = "More than one sweep with name '{setup_sweep_name}' found. "
                warning_str += f"Returning '{sweep_names[0]}'."
                self.logger.warning(warning_str)
                return sweep_names[0]
            elif len(sweep_names) == 1:
                return sweep_names[0]
            else:
                return sweep_name  # Nothing found, pass the sweep name through.
        else:
            return sweep_name

    @pyaedt_function_handler()
    def _get_plot_inputs(self):
        names = self._app.get_oo_name(self.oreportsetup)
        plots = []
        skip_plot = False
        if self._app.design_type == "Circuit Netlist" and self._app.desktop_class.non_graphical:
            skip_plot = True
        if names and not skip_plot:
            for name in names:
                obj = self._app.get_oo_object(self.oreportsetup, name)
                report_type = obj.GetPropValue("Report Type")

                report = TEMPLATES_BY_NAME.get(report_type, TEMPLATES_BY_NAME["Standard"])

                plots.append(report(self, report_type, None))
                plots[-1]._legacy_props["plot_name"] = name
                plots[-1]._is_created = True
                plots[-1].report_type = obj.GetPropValue("Display Type")
        return plots

    @property
    def oreportsetup(self):
        """Report setup.

        Returns
        -------
        :attr:`ansys.aedt.core.modules.post_general.PostProcessor.oreportsetup`

        References
        ----------
        >>> oDesign.GetModule("ReportSetup")
        """
        return self._app.oreportsetup

    @property
    def logger(self):
        """Logger."""
        return self._app.logger

    @property
    def _desktop(self):
        """Desktop."""
        return self._app._desktop

    @property
    def _odesign(self):
        """Design."""
        return self._app._odesign

    @property
    def _oproject(self):
        """Project."""
        return self._app._oproject

    @property
    def oeditor(self):
        try:
            return self._app.modeler.oeditor
        except AttributeError:
            return

    @property
    def post_solution_type(self):
        """Design solution type.

        Returns
        -------
        type
            Design solution type.
        """
        return self._app.solution_type

    @property
    def all_report_names(self):
        """List of all report names.

        Returns
        -------
        list

        References
        ----------
        >>> oModule.GetAllReportNames()
        """
        return list(self.oreportsetup.GetAllReportNames())

    @pyaedt_function_handler(PlotName="plot_name")
    def copy_report_data(self, plot_name, paste=True):
        """Copy report data as static data.

        Parameters
        ----------
        plot_name : str
            Name of the report.
        paste : bool, optional
            Whether to paste the report. The default is ``True``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.CopyReportsData
        >>> oModule.PasteReports
        """
        self.oreportsetup.CopyReportsData([plot_name])
        if paste:
            self.paste_report_data()
        return True

    @pyaedt_function_handler()
    def paste_report_data(self):
        """Paste report data as static data.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.PasteReports
        """
        self.oreportsetup.PasteReports()
        return True

    @pyaedt_function_handler()
    def delete_report(self, plot_name=None):
        """Delete all reports or specific report.

        Parameters
        ----------
        plot_name : str, optional
            Name of the plot to delete. The default  value is ``None`` and in this case, all reports are deleted.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.DeleteReports
        """
        try:
            if plot_name:
                self.oreportsetup.DeleteReports([plot_name])
                for plot in self.plots:
                    if plot.plot_name == plot_name:
                        self.plots.remove(plot)
            else:
                self.oreportsetup.DeleteAllReports()
                self.plots.clear()
            return True
        except Exception:  # pragma: no cover
            return False

    @pyaedt_function_handler()
    def rename_report(self, plot_name, new_name):
        """Rename a plot.

        Parameters
        ----------
        plot_name : str
            Name of the plot.
        new_name : str
            New name of the plot.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.RenameReport
        """
        try:
            self.oreportsetup.RenameReport(plot_name, new_name)
            for plot in self.plots:
                if plot.plot_name == plot_name:
                    plot.plot_name = self.oreportsetup.GetChildObject(new_name).GetPropValue("Name")
            return True
        except Exception:
            return False

    @pyaedt_function_handler(soltype="solution_type", ctxt="context", expression="expressions")
    def get_solution_data_per_variation(
        self, solution_type="Far Fields", setup_sweep_name="", context=None, sweeps=None, expressions=""
    ):
        """Retrieve solution data for each variation.

        Parameters
        ----------
        solution_type : str, optional
            Type of the solution. For example, ``"Far Fields"`` or ``"Modal Solution Data"``. The default
            is ``"Far Fields"``.
        setup_sweep_name : str, optional
            Name of the setup for computing the report. The default is ``""``,
            in which case ``"nominal adaptive"`` is used.
        context : list, optional
            List of context variables. The default is ``None``.
        sweeps : dict, optional
            Dictionary of variables and values. The default is ``None``,
            in which case this list is used:
            ``{'Theta': 'All', 'Phi': 'All', 'Freq': 'All'}``.
        expressions : str or list, optional
            One or more traces to include. The default is ``""``.

        Returns
        -------
        from ansys.aedt.core.modules.solutions.SolutionData


        References
        ----------
        >>> oModule.GetSolutionDataPerVariation
        """
        if sweeps is None:
            sweeps = {"Theta": "All", "Phi": "All", "Freq": "All"}
        if not context:
            context = []
        if not isinstance(expressions, list):
            expressions = [expressions]
        if not setup_sweep_name:
            setup_sweep_name = self._app.nominal_adaptive
        sweep_list = self.__convert_dict_to_report_sel(sweeps)
        try:
            data = list(
                self.oreportsetup.GetSolutionDataPerVariation(
                    solution_type, setup_sweep_name, context, sweep_list, expressions
                )
            )
            self.logger.info("Solution Data Correctly Loaded.")
            return SolutionData(data)
        except Exception:
            self.logger.warning("Solution Data failed to load. Check solution, context or expression.")
            return None

    @pyaedt_function_handler()
    def steal_focus_oneditor(self):
        """Remove the selection of an object that would prevent the image from exporting correctly.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesktop.RestoreWindow
        """
        self._desktop.RestoreWindow()
        param = ["NAME:SphereParameters", "XCenter:=", "0mm", "YCenter:=", "0mm", "ZCenter:=", "0mm", "Radius:=", "1mm"]
        attr = ["NAME:Attributes", "Name:=", "DUMMYSPHERE1", "Flags:=", "NonModel#"]
        self.oeditor.CreateSphere(param, attr)
        self.oeditor.Delete(["NAME:Selections", "Selections:=", "DUMMYSPHERE1"])
        return True

    @pyaedt_function_handler()
    def export_report_to_file(
        self,
        output_dir,
        plot_name,
        extension,
        unique_file=False,
        uniform=False,
        start=None,
        end=None,
        step=None,
        use_trace_number_format=False,
    ):
        r"""
        Export a 2D Plot data to a file.

        This method leaves the data in the plot (as data) as a reference
        for the Plot after the loops.

        Parameters
        ----------
        output_dir : str
            Path to the directory of exported report
        plot_name : str
            Name of the plot to export.
        extension : str
            Extension of export , one of
                * (CSV) .csv
                * (Tab delimited) .tab
                * (Post processor format) .txt
                * (Ensight XY data) .exy
                * (Anosft Plot Data) .dat
                * (Ansoft Report Data Files) .rdat
        unique_file : bool
            If set to True, generates unique file in output_dit
        uniform : bool, optional
            Whether the export uniform points to the file. The
            default is ``False``.
        start : str, optional
            Start range with units for the sweep if the ``uniform`` parameter
            is set to ``True``.
        end : str, optional
            End range with units for the sweep if the ``uniform`` parameter
            is set to ``True``.
        step : str, optional
            Step range with units for the sweep if the ``uniform`` parameter is
            set to ``True``.
        use_trace_number_format : bool, optional
            Whether to use trace number formats and use separate columns for curve. The default is ``False``.

        Returns
        -------
        str
            Path of exported file.

        References
        ----------
        >>> oModule.ExportReportDataToFile
        >>> oModule.ExportUniformPointsToFile
        >>> oModule.ExportToFile

        Examples
        --------
        >>> from ansys.aedt.core import Circuit
        >>> cir = Circuit("my_project.aedt")
        >>> report = cir.post.create_report("MyScattering")
        >>> cir.post.export_report_to_file("C:\\temp", "MyTestScattering", ".csv")
        """
        npath = output_dir

        if "." not in extension:  # pragma: no cover
            extension = "." + extension

        supported_ext = [".csv", ".tab", ".txt", ".exy", ".dat", ".rdat"]
        if extension not in supported_ext:  # pragma: no cover
            msg = f"Extension {extension} is not supported. Use one of {', '.join(supported_ext)}"
            raise ValueError(msg)

        file_path = os.path.join(npath, plot_name + extension)
        if unique_file:  # pragma: no cover
            while os.path.exists(file_path):
                file_name = generate_unique_name(plot_name)
                file_path = os.path.join(npath, file_name + extension)

        if extension == ".rdat":
            self.oreportsetup.ExportReportDataToFile(plot_name, file_path)
        elif uniform:
            self.oreportsetup.ExportUniformPointsToFile(plot_name, file_path, start, end, step, use_trace_number_format)
        else:
            self.oreportsetup.ExportToFile(plot_name, file_path, use_trace_number_format)
        return file_path

    @pyaedt_function_handler()
    def export_report_to_csv(
        self, project_dir, plot_name, uniform=False, start=None, end=None, step=None, use_trace_number_format=False
    ):
        """Export the 2D Plot data to a CSV file.

        This method leaves the data in the plot (as data) as a reference
        for the Plot after the loops.

        Parameters
        ----------
        project_dir : str
            Path to the project directory. The CSV file is plot_name.csv.
        plot_name : str
            Name of the plot to export.
        uniform : bool, optional
            Whether the export uniform points to the file. The
            default is ``False``.
        start : str, optional
            Start range with units for the sweep if the ``uniform`` parameter
            is set to ``True``.
        end : str, optional
            End range with units for the sweep if the ``uniform`` parameter
            is set to ``True``.
        step : str, optional
            Step range with units for the sweep if the ``uniform`` parameter is
            set to ``True``.
        use_trace_number_format : bool, optional
            Whether to use trace number formats. The default is ``False``.

        Returns
        -------
        str
            Path of exported file.

        References
        ----------
        >>> oModule.ExportReportDataToFile
        >>> oModule.ExportToFile
        >>> oModule.ExportUniformPointsToFile
        """
        return self.export_report_to_file(
            project_dir,
            plot_name,
            extension=".csv",
            uniform=uniform,
            start=start,
            end=end,
            step=step,
            use_trace_number_format=use_trace_number_format,
        )

    @pyaedt_function_handler(project_dir="project_path")
    def export_report_to_jpg(self, project_path, plot_name, width=0, height=0, image_format="jpg"):
        """Export plot to an image file.

        Parameters
        ----------
        project_path : str
            Path to the project directory.
        plot_name : str
            Name of the plot to export.
        width : int, optional
            Image width. Default is ``0`` which takes Desktop size or 1980 pixel in case of non-graphical mode.
        height : int, optional
            Image height. Default is ``0`` which takes Desktop size or 1020 pixel in case of non-graphical mode.
        image_format : str, optional
            Format of the image file. The default is ``"jpg"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.ExportImageToFile
        """
        file_name = os.path.join(project_path, plot_name + "." + image_format)  # name of the image file
        if self._app.desktop_class.non_graphical:  # pragma: no cover
            if width == 0:
                width = 1980
            if height == 0:
                height = 1020
        self.oreportsetup.ExportImageToFile(plot_name, file_name, width, height)
        return True

    @pyaedt_function_handler(plotname="plot_name")
    def _get_report_inputs(
        self,
        expressions,
        setup_sweep_name=None,
        domain="Sweep",
        variations=None,
        primary_sweep_variable=None,
        secondary_sweep_variable=None,
        report_category=None,
        plot_type="Rectangular Plot",
        context=None,
        subdesign_id=None,
        polyline_points=0,
        plot_name=None,
        only_get_method=False,
    ):
        ctxt = []
        if not setup_sweep_name:
            setup_sweep_name = self._app.nominal_sweep
        elif setup_sweep_name not in self._app.existing_analysis_sweeps:
            self.logger.error("Sweep not Available.")
            return False
        families_input = {}
        did = 3
        if domain == "Sweep" and not primary_sweep_variable:
            primary_sweep_variable = "Freq"
        elif not primary_sweep_variable:
            primary_sweep_variable = "Time"
            did = 1
        if not variations or primary_sweep_variable not in variations:
            families_input[primary_sweep_variable] = ["All"]
        elif isinstance(variations[primary_sweep_variable], list):
            families_input[primary_sweep_variable] = variations[primary_sweep_variable]
        else:
            families_input[primary_sweep_variable] = [variations[primary_sweep_variable]]
        if not variations:
            variations = self._app.available_variations.get_independent_nominal_values()
        for el in list(variations.keys()):
            if el == primary_sweep_variable:
                continue
            if isinstance(variations[el], list):
                families_input[el] = variations[el]
            else:
                families_input[el] = [variations[el]]
        if only_get_method and domain == "Sweep":
            if "Phi" not in families_input:
                families_input["Phi"] = ["All"]
            if "Theta" not in families_input:
                families_input["Theta"] = ["All"]

        if self.post_solution_type in ["TR", "AC", "DC"]:
            ctxt = [
                "NAME:Context",
                "SimValueContext:=",
                [did, 0, 2, 0, False, False, -1, 1, 0, 1, 1, "", 0, 0],
            ]
            setup_sweep_name = self.post_solution_type
        elif self.post_solution_type in ["HFSS3DLayout"]:
            if context == "Differential Pairs":
                ctxt = [
                    "NAME:Context",
                    "SimValueContext:=",
                    [
                        did,
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
                        "EnsDiffPairKey",
                        False,
                        "1",
                        "IDIID",
                        False,
                        "1",
                    ],
                ]
            else:
                ctxt = [
                    "NAME:Context",
                    "SimValueContext:=",
                    [did, 0, 2, 0, False, False, -1, 1, 0, 1, 1, "", 0, 0, "IDIID", False, "1"],
                ]
        elif self.post_solution_type in ["NexximLNA", "NexximTransient"]:
            ctxt = ["NAME:Context", "SimValueContext:=", [did, 0, 2, 0, False, False, -1, 1, 0, 1, 1, "", 0, 0]]
            if subdesign_id:
                ctxt_temp = ["NUMLEVELS", False, "1", "SUBDESIGNID", False, str(subdesign_id)]
                for el in ctxt_temp:
                    ctxt[2].append(el)
            if context == "Differential Pairs":
                ctxt_temp = ["USE_DIFF_PAIRS", False, "1"]
                for el in ctxt_temp:
                    ctxt[2].append(el)
        elif context == "Differential Pairs":
            ctxt = ["Diff:=", "Differential Pairs", "Domain:=", domain]
        elif self.post_solution_type in ["Q3D Extractor", "2D Extractor"]:
            if not context:
                ctxt = ["Context:=", "Original"]
            else:
                ctxt = ["Context:=", context]
        elif context:
            ctxt = ["Context:=", context]
            if context in self._app.modeler.line_names:
                ctxt.append("PointCount:=")
                ctxt.append(polyline_points)

        if not isinstance(expressions, list):
            expressions = [expressions]

        if not report_category and not self._app.design_solutions.report_type:
            self.logger.error("Solution not supported")
            return False
        if not report_category:
            modal_data = self._app.design_solutions.report_type
        else:
            modal_data = report_category
        if not plot_name:
            plot_name = generate_unique_name("Plot")

        arg = ["X Component:=", primary_sweep_variable, "Y Component:=", expressions]
        if plot_type in ["3D Polar Plot", "3D Spherical Plot"]:
            if not primary_sweep_variable:
                primary_sweep_variable = "Phi"
            if not secondary_sweep_variable:
                secondary_sweep_variable = "Theta"
            arg = [
                "Phi Component:=",
                primary_sweep_variable,
                "Theta Component:=",
                secondary_sweep_variable,
                "Mag Component:=",
                expressions,
            ]
        elif plot_type == "Radiation Pattern":
            if not primary_sweep_variable:
                primary_sweep_variable = "Phi"
            arg = ["Ang Component:=", primary_sweep_variable, "Mag Component:=", expressions]
        elif plot_type in ["Smith Chart", "Polar Plot"]:
            arg = ["Polar Component:=", expressions]
        elif plot_type == "Rectangular Contour Plot":
            arg = [
                "X Component:=",
                primary_sweep_variable,
                "Y Component:=",
                secondary_sweep_variable,
                "Z Component:=",
                expressions,
            ]
        return [plot_name, modal_data, plot_type, setup_sweep_name, ctxt, families_input, arg]

    @pyaedt_function_handler(plotname="plot_name")
    def create_report(
        self,
        expressions=None,
        setup_sweep_name=None,
        domain="Sweep",
        variations=None,
        primary_sweep_variable=None,
        secondary_sweep_variable=None,
        report_category=None,
        plot_type="Rectangular Plot",
        context=None,
        subdesign_id=None,
        polyline_points=1001,
        plot_name=None,
    ):
        """Create a report in AEDT. It can be a 2D plot, 3D plot, polar plot, or a data table.

        Parameters
        ----------
        expressions : str or list, optional
            One or more formulas to add to the report. Example is value = ``"dB(S(1,1))"``.
        setup_sweep_name : str, optional
            Setup name with the sweep. The default is ``""``.
        domain : str, optional
            Plot Domain. Options are "Sweep", "Time", "DCIR".
        variations : dict, optional
            Dictionary of all families including the primary sweep. The default is ``{"Freq": ["All"]}``.
        primary_sweep_variable : str, optional
            Name of the primary sweep. The default is ``"Freq"``.
        secondary_sweep_variable : str, optional
            Name of the secondary sweep variable in 3D Plots.
        report_category : str, optional
            Category of the Report to be created. If `None` default data Report is used.
            The Report Category can be one of the types available for creating a report depend on the simulation setup.
            For example for a Far Field Plot in HFSS the UI shows the report category as "Create Far Fields Report".
            The report category is "Far Fields" in this case.
            Depending on the setup different categories are available.
            If ``None`` default category is used (the first item in the Results drop down menu in AEDT).
        plot_type : str, optional
            The format of Data Visualization. Default is ``Rectangular Plot``.
        context : str, dict, optional
            The default is ``None``.
            - For HFSS 3D Layout, options are ``"Bondwires"``, ``"Differential Pairs"``,
            ``None``, ``"Probes"``, ``"RL"``, ``"Sources"``, and ``"Vias"``.
            - For Q2D or Q3D, specify the name of a reduced matrix.
            - For a far fields plot, specify the name of an infinite sphere.
            - For Maxwell 2D/3D Eddy Current solution types this can be provided as a dictionary
            where the key is the matrix name and value the reduced matrix.
        plot_name : str, optional
            Name of the plot. The default is ``None``.
        polyline_points : int, optional,
            Number of points to create the report for plots on polylines on.
        subdesign_id : int, optional
            Specify a subdesign ID to export a Touchstone file of this subdesign. Valid for Circuit Only.
            The default value is ``None``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.report_templates.Standard`
            ``True`` when successful, ``False`` when failed.


        References
        ----------
        >>> oModule.CreateReport

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss.post.create_report("dB(S(1,1))")
        >>> variations = hfss.available_variations.nominal_values
        >>> variations["Theta"] = ["All"]
        >>> variations["Phi"] = ["All"]
        >>> variations["Freq"] = ["30GHz"]
        >>> hfss.post.create_report(expressions="db(GainTotal)",
        ...                            setup_sweep_name=hfss.nominal_adaptive,
        ...                            variations=variations,
        ...                            primary_sweep_variable="Phi",
        ...                            secondary_sweep_variable="Theta",
        ...                            report_category="Far Fields",
        ...                            plot_type="3D Polar Plot",
        ...                            context="3D")
        >>> hfss.post.create_report("S(1,1)",hfss.nominal_sweep,variations=variations,plot_type="Smith Chart")
        >>> hfss.release_desktop(False, False)

        >>> from ansys.aedt.core import Maxwell2d
        >>> m2d = Maxwell2d()
        >>> m2d.post.create_report(expressions="InputCurrent(PHA)",
        ...                               domain="Time",
        ...                               primary_sweep_variable="Time",
        ...                               plot_name="Winding Plot 1")
        >>> m2d.release_desktop(False, False)

        >>> from ansys.aedt.core import Maxwell3d
        >>> m3d = Maxwell3d(solution_type="EddyCurrent")
        >>> rectangle1 = m3d.modeler.create_rectangle(0, [0.5, 1.5, 0], [2.5, 5], name="Sheet1")
        >>> rectangle2 = m3d.modeler.create_rectangle(0, [9, 1.5, 0], [2.5, 5], name="Sheet2")
        >>> rectangle3 = m3d.modeler.create_rectangle(0, [16.5, 1.5, 0], [2.5, 5], name="Sheet3")
        >>> m3d.assign_current(rectangle1.faces[0], amplitude=1, name="Cur1")
        >>> m3d.assign_current(rectangle2.faces[0], amplitude=1, name="Cur2")
        >>> m3d.assign_current(rectangle3.faces[0], amplitude=1, name="Cur3")
        >>> L = m3d.assign_matrix(assignment=["Cur1", "Cur2", "Cur3"], matrix_name="Matrix1")
        >>> out = L.join_series(sources=["Cur1", "Cur2"], matrix_name="ReducedMatrix1")
        >>> expressions = m3d.post.available_report_quantities(report_category="EddyCurrent",
        ...                                                    display_type="Data Table",
        ...                                                    context={"Matrix1": "ReducedMatrix1"})
        >>> report = m3d.post.create_report(
        ...    expressions=expressions,
        ...    context={"Matrix1": "ReducedMatrix1"},
        ...    plot_type="Data Table",
        ...    plot_name="reduced_matrix")
        >>> m3d.release_desktop(False, False)
        """
        if not setup_sweep_name:
            if report_category == "Fields":
                setup_sweep_name = self._app.nominal_adaptive  # Field report and no sweep name passed.
            else:
                setup_sweep_name = self._app.nominal_sweep
        elif domain == "Sweep":
            setup_sweep_name = self._get_setup_from_sweep_name(setup_sweep_name)
        if not domain:
            domain = "Sweep"
            setup_name = setup_sweep_name.split(":")[0]
            if setup_name:
                for setup in self._app.setups:
                    if setup.name == setup_name and "Time" in setup.default_intrinsics:
                        domain = "Time"
        if domain in ["Spectral", "Spectrum"]:
            report_category = "Spectrum"
        elif not report_category and not self._app.design_solutions.report_type:
            self.logger.error("Solution not supported")
            return False
        elif not report_category:
            report_category = self._app.design_solutions.report_type
        if report_category in TEMPLATES_BY_NAME:
            report_class = TEMPLATES_BY_NAME[report_category]
        elif "Fields" in report_category:
            report_class = TEMPLATES_BY_NAME["Fields"]
        else:
            report_class = TEMPLATES_BY_NAME["Standard"]

        report = report_class(self, report_category, setup_sweep_name)
        if not expressions:
            expressions = [
                i for i in self.available_report_quantities(report_category=report_category, context=context)
            ]
        report.expressions = expressions
        report.domain = domain
        if not variations and domain == "Sweep":
            variations = self._app.available_variations.get_independent_nominal_values()
            if variations:
                variations["Freq"] = "All"
            else:
                variations = {"Freq": ["All"]}
        elif not variations and domain != "Sweep":
            variations = self._app.available_variations.get_independent_nominal_values()
        report.variations = variations
        if primary_sweep_variable:
            report.primary_sweep = primary_sweep_variable
        elif domain == "DCIR":  # pragma: no cover
            report.primary_sweep = "Index"
            if variations:
                variations["Index"] = ["All"]
            else:  # pragma: no cover
                variations = {"Index": "All"}
        if secondary_sweep_variable:
            report.secondary_sweep = secondary_sweep_variable

        report.variations = variations
        report.report_type = plot_type
        report.sub_design_id = subdesign_id
        report.point_number = polyline_points
        if context == "Differential Pairs":
            report.differential_pairs = True
        elif context in [
            "RL",
            "Sources",
            "Vias",
            "Bondwires",
            "Probes",
        ]:
            report.siwave_dc_category = [
                "RL",
                "Sources",
                "Vias",
                "Bondwires",
                "Probes",
            ].index(context)
        elif self._app.design_type in ["Q3D Extractor", "2D Extractor"] and context:
            report.matrix = context
        elif (
            self._app.design_type in ["Maxwell 2D", "Maxwell 3D"]
            and context
            and self._app.solution_type in ["EddyCurrent", "Electrostatic"]
        ):
            if isinstance(context, dict):
                for k, v in context.items():
                    report.matrix = k
                    report.reduced_matrix = v
            elif context in self._app.modeler.line_names or context in self._app.modeler.point_names:
                report.polyline = context
            else:
                report.matrix = context
        elif report_category == "Far Fields":
            if not context and self._app.field_setups:
                report.far_field_sphere = self._app.field_setups[0].name
            else:
                if isinstance(context, dict):
                    if "Context" in context.keys() and "SourceContext" in context.keys():
                        report.far_field_sphere = context["Context"]
                        report.source_context = context["SourceContext"]
                    if "Context" in context.keys() and "Source Group" in context.keys():
                        report.far_field_sphere = context["Context"]
                        report.source_group = context["Source Group"]
                else:
                    report.far_field_sphere = context
        elif report_category == "Near Fields":
            report.near_field = context
        elif context:
            if context in self._app.modeler.line_names or context in self._app.modeler.point_names:
                report.polyline = context

        result = report.create(plot_name)
        if result:
            return report
        return False

    @pyaedt_function_handler()
    def get_solution_data(
        self,
        expressions=None,
        setup_sweep_name=None,
        domain=None,
        variations=None,
        primary_sweep_variable=None,
        report_category=None,
        context=None,
        subdesign_id=None,
        polyline_points=1001,
        math_formula=None,
    ):
        """Get a simulation result from a solved setup and cast it in a ``SolutionData`` object.

        Data to be retrieved from Electronics Desktop are any simulation results available in that
        specific simulation context.
        Most of the argument have some defaults which works for most of the ``Standard`` report quantities.

        Parameters
        ----------
        expressions : str or list, optional
            One or more formulas to add to the report. Example is value ``"dB(S(1,1))"`` or a list of values.
            Default is ``None`` which returns all traces.
        setup_sweep_name : str, optional
            Name of the setup. The default is ``None``, in which case the ``nominal_adaptive``
            setup is used. Be sure to build a setup string in the form of
            ``"SetupName : SetupSweep"``, where ``SetupSweep`` is the sweep name to
            use in the export or ``LastAdaptive``.
        domain : str, optional
            Plot Domain. Options are "Sweep" for frequency domain related results and "Time" for transient related data.
        variations : dict, optional
            Dictionary of all families including the primary sweep.
            The default is ``None`` which uses the nominal variations of the setup.
        primary_sweep_variable : str, optional
            Name of the primary sweep. The default is ``"None"`` which, depending on the context,
            internally assigns the primary sweep to:
            1. ``Freq`` for frequency domain results,
            2. ``Time`` for transient results,
            3. ``Theta`` for radiation patterns,
            4. ``distance`` for field plot over a polyline.
        report_category : str, optional
            Category of the Report to be created. If ``None`` default data Report is used.
            The Report Category can be one of the types available for creating a report depend on the simulation setup.
            For example for a Far Field Plot in HFSS the UI shows the report category as "Create Far Fields Report".
            The report category is "Far Fields" in this case.
            Depending on the setup different categories are available.
            If ``None`` default category is used (the first item in the Results drop down menu in AEDT).
            To get the list of available categories user can use method ``available_report_types``.
        context : str, dict, optional
            This is the context of the report.
            The default is ``None``. It can be:
            1. `None`
            2. ``"Differential Pairs"``
            3. Reduce Matrix Name for Q2d/Q3d solution
            4. Infinite Sphere name for Far Fields Plot.
            5. Dictionary. If dictionary is passed, key is the report property name and value is property value.
            6. For Maxwell 2D/3D eddy current solution types, this can be provided as a dictionary,
            where the key is the matrix name and value the reduced matrix.
        subdesign_id : int, optional
            Subdesign ID for exporting a Touchstone file of this subdesign.
            This parameter is valid for ``Circuit`` only.
            The default value is ``None``.
        polyline_points : int, optional
            Number of points on which to create the report for plots on polylines.
            This parameter is valid for ``Fields`` plot only.
        math_formula : str, optional
            One of the available AEDT mathematical formulas to apply. For example, ``abs, dB``.


        Returns
        -------
        :class:`ansys.aedt.core.modules.solutions.SolutionData`
            Solution Data object.

        References
        ----------
        >>> oModule.GetSolutionDataPerVariation

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss.post.create_report("dB(S(1,1))")
        >>> variations = hfss.available_variations.nominal_values
        >>> variations["Theta"] = ["All"]
        >>> variations["Phi"] = ["All"]
        >>> variations["Freq"] = ["30GHz"]
        >>> data1 = hfss.post.get_solution_data(
        ...    "GainTotal",
        ...    hfss.nominal_adaptive,
        ...    variations=variations,
        ...    primary_sweep_variable="Phi",
        ...    secondary_sweep_variable="Theta",
        ...    context="3D",
        ...    report_category="Far Fields",
        ...)

        >>> data2 =hfss.post.get_solution_data(
        ...    "S(1,1)",
        ...    hfss.nominal_sweep,
        ...    variations=variations,
        ...)
        >>> data2.plot()
        >>> hfss.release_desktop(False, False)

        >>> from ansys.aedt.core import Maxwell2d
        >>> m2d = Maxwell2d()
        >>> data3 = m2d.post.get_solution_data(
        ...     "InputCurrent(PHA)", domain="Time", primary_sweep_variable="Time",
        ... )
        >>> data3.plot("InputCurrent(PHA)")
        >>> m2d.release_desktop(False, False)

        >>> from ansys.aedt.core import Circuit
        >>> circuit = Circuit()
        >>> context = {"algorithm": "FFT", "max_frequency": "100MHz", "time_stop": "2.5us", "time_start": "0ps"}
        >>> spectralPlotData = circuit.post.get_solution_data(expressions="V(Vprobe1)", domain="Spectral",
        ...                                                   primary_sweep_variable="Spectrum", context=context)
        >>> circuit.release_desktop(False, False)

        >>> from ansys.aedt.core import Maxwell3d
        >>> m3d = Maxwell3d(solution_type="EddyCurrent")
        >>> rectangle1 = m3d.modeler.create_rectangle(0, [0.5, 1.5, 0], [2.5, 5], name="Sheet1")
        >>> rectangle2 = m3d.modeler.create_rectangle(0, [9, 1.5, 0], [2.5, 5], name="Sheet2")
        >>> rectangle3 = m3d.modeler.create_rectangle(0, [16.5, 1.5, 0], [2.5, 5], name="Sheet3")
        >>> m3d.assign_current(rectangle1.faces[0], amplitude=1, name="Cur1")
        >>> m3d.assign_current(rectangle2.faces[0], amplitude=1, name="Cur2")
        >>> m3d.assign_current(rectangle3.faces[0], amplitude=1, name="Cur3")
        >>> L = m3d.assign_matrix(assignment=["Cur1", "Cur2", "Cur3"], matrix_name="Matrix1")
        >>> out = L.join_series(sources=["Cur1", "Cur2"], matrix_name="ReducedMatrix1")
        >>> expressions = m3d.post.available_report_quantities(report_category="EddyCurrent",
        ...                                                    display_type="Data Table",
        ...                                                    context={"Matrix1": "ReducedMatrix1"})
        >>> data = m2d.post.get_solution_data(expressions=expressions, context={"Matrix1": "ReducedMatrix1"})
        >>> m3d.release_desktop(False, False)
        """
        expressions = [expressions] if isinstance(expressions, str) else expressions
        if not setup_sweep_name:
            setup_sweep_name = self._app.nominal_sweep
        if not domain:
            domain = "Sweep"
            setup_name = setup_sweep_name.split(":")[0]
            if setup_name:
                for setup in self._app.setups:
                    if setup.name == setup_name and "Time" in setup.default_intrinsics:
                        domain = "Time"
        if domain in ["Spectral", "Spectrum"]:
            report_category = "Spectrum"
        if not report_category and not self._app.design_solutions.report_type:
            self.logger.error("Solution not supported")
            return False
        elif not report_category:
            report_category = self._app.design_solutions.report_type
        if report_category in TEMPLATES_BY_NAME:
            report_class = TEMPLATES_BY_NAME[report_category]
        elif "Fields" in report_category:
            report_class = TEMPLATES_BY_NAME["Fields"]
        else:
            report_class = TEMPLATES_BY_NAME["Standard"]

        report = report_class(self, report_category, setup_sweep_name)
        if not expressions:
            expressions = [
                i for i in self.available_report_quantities(report_category=report_category, context=context)
            ]
        if math_formula:
            expressions = [f"{math_formula}({i})" for i in expressions]
        report.expressions = expressions
        report.domain = domain
        if primary_sweep_variable:
            report.primary_sweep = primary_sweep_variable
        if not variations and domain == "Sweep":
            variations = self._app.available_variations.get_independent_nominal_values()
            if variations:
                variations["Freq"] = "All"
            else:
                variations = {"Freq": ["All"]}
        elif not variations and domain != "Sweep":
            variations = self._app.available_variations.get_independent_nominal_values()
        report.variations = variations
        report.sub_design_id = subdesign_id
        report.point_number = polyline_points
        if context == "Differential Pairs":
            report.differential_pairs = True
        elif self._app.design_type in ["Q3D Extractor", "2D Extractor"] and context:
            report.matrix = context
        elif (
            self._app.design_type in ["Maxwell 2D", "Maxwell 3D"]
            and context
            and self._app.solution_type in ["EddyCurrent", "Electrostatic"]
        ):
            if isinstance(context, dict):
                for k, v in context.items():
                    report.matrix = k
                    report.reduced_matrix = v
            elif (
                hasattr(self._app.modeler, "line_names")
                and hasattr(self._app.modeler, "point_names")
                and context in self._app.modeler.point_names + self._app.modeler.line_names
            ):
                report.polyline = context
            else:
                report.matrix = context
        elif report_category == "Far Fields":
            if not context and self._app.field_setups:
                report.far_field_sphere = self._app.field_setups[0].name
                if "Theta" not in report.variations:
                    report.variations["Theta"] = ["All"]
                if "Phi" not in report.variations:
                    report.variations["Phi"] = ["All"]
                report.primary_sweep = "Theta"
            else:
                if isinstance(context, dict):
                    if "Context" in context.keys() and "SourceContext" in context.keys():
                        report.far_field_sphere = context["Context"]
                        report.source_context = context["SourceContext"]
                else:
                    report.far_field_sphere = context
        elif report_category == "Near Fields":
            report.near_field = context
        elif context and isinstance(context, dict):
            for attribute in context:
                if hasattr(report, attribute):
                    report.__setattr__(attribute, context[attribute])
                else:
                    self.logger.warning(f"Parameter {attribute} is not available, check syntax.")
        elif context:
            if (
                hasattr(self._app.modeler, "line_names")
                and hasattr(self._app.modeler, "point_names")
                and context in self._app.modeler.point_names + self._app.modeler.line_names
            ):
                report.polyline = context
            elif context in [
                "RL",
                "Sources",
                "Vias",
                "Bondwires",
                "Probes",
            ]:
                report.siwave_dc_category = [
                    "RL",
                    "Sources",
                    "Vias",
                    "Bondwires",
                    "Probes",
                ].index(context)
        solution_data = report.get_solution_data()
        return solution_data

    @pyaedt_function_handler(input_dict="report_settings")
    def create_report_from_configuration(
        self, input_file=None, report_settings=None, solution_name=None, name=None, matplotlib=False
    ):
        """Create a report based on a JSON file, TOML file, RPT file, or dictionary of properties.

        Parameters
        ----------
        input_file : str, optional
            Path to the JSON, TOML, or RPT file containing report settings.
        report_settings : dict, optional
            Dictionary containing report settings.
        solution_name : str, optional
            Setup name to use.
        matplotlib : bool, optional
            Whether if use AEDT or ReportPlotter to generate the plot. Eye diagrams are not supported.

        Returns
        -------
        :class:`ansys.aedt.core.modules.report_templates.Standard`
            Report object if succeeded.

        Examples
        --------
        Create report from JSON file.
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss.post.create_report_from_configuration(r'C:\\temp\\my_report.json',
        ...                                            solution_name="Setup1 : LastAdpative")

        Create report from RPT file.
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss.post.create_report_from_configuration(r'C:\\temp\\my_report.rpt')

        Create report from dictionary.
        >>> from ansys.aedt.core import Hfss
        >>> from ansys.aedt.core.generic.general_methods import read_json
        >>> hfss = Hfss()
        >>> dict_vals = read_json("Report_Simple.json")
        >>> hfss.post.create_report_from_configuration(report_settings=dict_vals)
        """
        if not report_settings and not input_file:  # pragma: no cover
            self.logger.error("Either a file or a dictionary must be passed as input.")
            return False
        props = {}
        if input_file:
            _, file_extension = os.path.splitext(input_file)
            if file_extension == ".rpt":
                old_expressions = self.all_report_names
                self.oreportsetup.CreateReportFromTemplate(input_file)
                new_expressions = [item for item in self.all_report_names if item not in old_expressions]
                if new_expressions:
                    report_name = new_expressions[0]
                    self.plots = self._get_plot_inputs()
                    report = None
                    for plot in self.plots:
                        if plot.plot_name == report_name:
                            report = plot
                            break
                    return report
            else:
                props = read_configuration_file(input_file)
            if report_settings:
                props = self.__apply_settings(props, report_settings)

        else:
            props = report_settings

        if (
            isinstance(props.get("expressions", {}), list)
            and props["expressions"]
            and isinstance(props["expressions"][0], str)
        ):  # pragma: no cover
            props["expressions"] = {i: {} for i in props["expressions"]}
        elif isinstance(props.get("expressions", {}), str):  # pragma: no cover
            props["expressions"] = {props["expressions"]: {}}
        _dict_items_to_list_items(props, "expressions")
        if not solution_name:
            if "Fields" not in props.get("report_category", ""):
                solution_name = self._app.nominal_sweep
            else:
                solution_name = self._app.nominal_adaptive
        else:
            solution_name = self._get_setup_from_sweep_name(solution_name)  # If only the sweep name is passed.
        if props.get("report_category", None) and props["report_category"] in TEMPLATES_BY_NAME:
            if props.get("context", {"context": {}}).get("domain", "") == "Spectral":
                report_temp = TEMPLATES_BY_NAME["Spectrum"]
            elif (
                "AMIAnalysis" in self._app.get_setup(solution_name.split(":")[0].strip()).props
                and props["report_category"] == "Standard"
            ):
                report_temp = TEMPLATES_BY_NAME["AMI Contour"]
            elif "AMIAnalysis" in self._app.get_setup(solution_name.split(":")[0].strip()).props:
                report_temp = TEMPLATES_BY_NAME["Statistical Eye"]
            else:
                report_temp = TEMPLATES_BY_NAME[props["report_category"]]
            report = report_temp(self, props["report_category"], solution_name)

            def _update_props(prop_in, props_out):
                for k, v in prop_in.items():
                    if isinstance(v, dict):
                        if k not in props_out:
                            props_out[k] = {}
                        _update_props(v, props_out[k])
                    else:
                        props_out[k] = v

            if (
                props.get("context", {"context": {}}).get("secondary_sweep", "") == ""
                and props.get("report_type", "") != "Rectangular Contour Plot"
            ):
                report._legacy_props["context"]["secondary_sweep"] = ""
            _update_props(props, report._legacy_props)
            for el, k in self._app.available_variations.nominal_w_values_dict.items():
                if (
                    report._legacy_props.get("context", None)
                    and report._legacy_props["context"].get("variations", None)
                    and el not in report._legacy_props["context"]["variations"]
                ):
                    report._legacy_props["context"]["variations"][el] = k
            _ = report.expressions
            if matplotlib:
                if props.get("report_type", "").lower() in ["eye diagram", "statistical eye"]:  # pragma: no cover
                    self.logger.warning("Eye Diagrams are not supported by Matplotlib.")
                else:
                    return self._report_plotter(report)
            report.create(name)
            if report.report_type != "Data Table":
                report._update_traces()
                self.oreportsetup.UpdateReports(report.plot_name)
            self.logger.info(f"Report {report.plot_name} created successfully.")
            return report
        self.logger.error("Failed to create report.")
        return False  # pragma: no cover

    @pyaedt_function_handler()
    def _report_plotter(self, report):
        sols = report.get_solution_data()
        report_plotter = ReportPlotter()
        report_plotter.title = report._legacy_props.get("plot_name", "PyAEDT Report")
        try:
            report_plotter.general_back_color = [
                i / 255 for i in report._legacy_props["general"]["appearance"]["background_color"]
            ]
        except KeyError:
            pass
        try:

            report_plotter.general_plot_color = [
                i / 255 for i in report._legacy_props["general"]["appearance"]["plot_color"]
            ]
        except KeyError:
            pass
        try:
            report_plotter.grid_enable_major_x = report._legacy_props["general"]["grid"]["major_x"]
        except KeyError:
            pass
        try:
            report_plotter.grid_enable_minor_x = report._legacy_props["general"]["grid"]["minor_x"]
        except KeyError:
            pass
        try:
            report_plotter.grid_enable_major_y = report._legacy_props["general"]["grid"]["major_y"]
        except KeyError:
            pass
        try:
            report_plotter.grid_enable_minor_yi = report._legacy_props["general"]["grid"]["minor_y"]
        except KeyError:
            pass
        try:
            report_plotter.grid_color = [i / 255 for i in report._legacy_props["general"]["grid"]["major_color"]]
        except KeyError:
            pass
        try:
            report_plotter.show_legend = True if report._legacy_props["general"]["legend"] else False
        except KeyError:
            pass
        sw = sols.primary_sweep_values
        for curve in sols.expressions:
            props = {
                "x_label": sols.primary_sweep,
                "y_label": curve,
            }
            pp = [i for i in report._legacy_props["expressions"] if i["name"] == curve]
            if pp:
                pp = pp[0]
                try:
                    props["trace_width"] = pp["width"]
                except KeyError:
                    pass
                try:
                    props["trace_color"] = [i / 255 for i in pp["color"]]
                except KeyError:
                    pass
                try:
                    props["fill_symbol"] = pp["fill_symbol"]
                except KeyError:
                    pass
                try:
                    props["symbol_color"] = [i / 255 for i in pp["symbol_color"]]
                except KeyError:
                    pass
                try:
                    styles = {"Solid": "-", "Dash": "--", "DotDash": "-.", "DotDot": ":"}
                    props["trace_style"] = styles[pp["trace_style"]]
                except KeyError:
                    pass
                try:
                    markers = {
                        "Box": ",",
                        "Circle": "o",
                        "VerticalUpTriangle": "^",
                        "VerticalDownTriangle": "v",
                        "HorizontalLeftTriangle": "<",
                        "HorizontalRightTriangle": ">",
                    }
                    props["symbol_style"] = markers[pp["symbol_style"]]
                except KeyError:
                    pass
            report_plotter.add_trace([sw, sols.data_real(curve)], 0, properties=props, name=curve)
        for name, line in report._legacy_props.get("limitLines", {}).items():
            props = {}
            try:
                props["trace_width"] = line["width"]
            except KeyError:
                pass
            try:
                props["trace_color"] = [i / 255 for i in line["color"]]
            except KeyError:
                pass
            try:
                report_plotter.add_limit_line([line["xpoints"], line["ypoints"]], 0, properties=props, name=name)
            except KeyError:
                self.logger.warning("Equation lines not supported yet.")
        if report._legacy_props.get("report_type", "Rectangular Plot") == "Rectangular Plot":
            _ = report_plotter.plot_2d()
            return report_plotter
        elif report._legacy_props.get("report_type", "Rectangular Plot") == "Polar Plot":
            _ = report_plotter.plot_polar()
            return report_plotter
        elif report._legacy_props.get("report_type", "Rectangular Plot") == "Rectangular Contour Plot":
            _ = report_plotter.plot_contour()
            return report_plotter
        elif report._legacy_props.get("report_type", "Rectangular Plot") in ["3D Polar Plot", "3D Spherical Plot"]:
            _ = report_plotter.plot_3d()
            return report_plotter

    @staticmethod
    @pyaedt_function_handler()
    def __convert_dict_to_report_sel(sweeps):
        if isinstance(sweeps, list):
            return sweeps
        sweep_list = []
        for el in sweeps:
            sweep_list.append(el + ":=")
            if isinstance(sweeps[el], list):
                sweep_list.append(sweeps[el])
            else:
                sweep_list.append([sweeps[el]])
        return sweep_list

    @staticmethod
    @pyaedt_function_handler()
    def __apply_settings(props, report_settings):
        for k, v in report_settings.items():
            if k in props:
                if isinstance(v, dict):
                    props[k] = apply_settings(props[k], v)
                else:
                    props[k] = v
            else:
                props[k] = v
        return props


class Reports(object):
    """Provides the names of default solution types."""

    def __init__(self, post_app, design_type):
        self._post_app = post_app
        self._design_type = design_type
        self._templates = TEMPLATES_BY_DESIGN.get(self._design_type, None)

    @pyaedt_function_handler()
    def _retrieve_default_expressions(self, expressions, report, setup_sweep_name):
        if expressions:
            return expressions
        setup_only_name = setup_sweep_name.split(":")[0].strip()
        get_setup = self._post_app._app.get_setup(setup_only_name)
        is_siwave_dc = False
        if (
            "SolveSetupType" in get_setup.props and get_setup.props["SolveSetupType"] == "SiwaveDCIR"
        ):  # pragma: no cover
            is_siwave_dc = True
        return self._post_app.available_report_quantities(
            solution=setup_sweep_name, context=report._context, is_siwave_dc=is_siwave_dc
        )

    @pyaedt_function_handler(setup_name="setup")
    def standard(self, expressions=None, setup=None):
        """Create a standard or default report object.

        Parameters
        ----------
        expressions : str or list
            Expression List to add into the report. The expression can be any of the available formula
            you can enter into the Electronics Desktop Report Editor.
        setup : str, optional
            Name of the setup. The default is ``None``, in which case the ``nominal_adaptive``
            setup is used. Be sure to build a setup string in the form of
            ``"SetupName : SetupSweep"``, where ``SetupSweep`` is the sweep name to
            use in the export or ``LastAdaptive``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.report_templates.Standard`

        Examples
        --------

        >>> from ansys.aedt.core import Circuit
        >>> cir = Circuit(my_project)
        >>> report = cir.post.reports_by_category.standard("dB(S(1,1))","LNA")
        >>> report.create()
        >>> solutions = report.get_solution_data()
        >>> report2 = cir.post.reports_by_category.standard(["dB(S(2,1))", "dB(S(2,2))"],"LNA")

        """
        if not setup:
            setup = self._post_app._app.nominal_sweep
        rep = None
        if "Standard" in self._templates:
            rep = ansys.aedt.core.visualization.report.standard.Standard(self._post_app, "Standard", setup)

        elif self._post_app._app.design_solutions.report_type:
            rep = ansys.aedt.core.visualization.report.standard.Standard(
                self._post_app, self._post_app._app.design_solutions.report_type, setup
            )
        rep.expressions = self._retrieve_default_expressions(expressions, rep, setup)
        return rep

    @pyaedt_function_handler(setup_name="setup")
    def monitor(self, expressions=None, setup=None):
        """Create an Icepak Monitor Report object.

        Parameters
        ----------
        expressions : str or list
            One or more expressions to add to the report. The expression can be any of the available formula
            you can enter into the Electronics Desktop Report Editor.
        setup : str, optional
            Name of the setup. The default is ``None``, in which case the ``nominal_adaptive``
            setup is used. Be sure to build a setup string in the form of
            ``"SetupName : SetupSweep"``, where ``SetupSweep`` is the sweep name to
            use in the export or ``LastAdaptive``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.report_templates.Standard`

        Examples
        --------

        >>> from ansys.aedt.core import Icepak
        >>> ipk = Icepak(my_project)
        >>> report = ipk.post.reports_by_category.monitor(["monitor_surf.Temperature","monitor_point.Temperature"])
        >>> report = report.create()
        """
        if not setup:
            setup = self._post_app._app.nominal_sweep
        rep = None
        if "Monitor" in self._templates:
            rep = ansys.aedt.core.visualization.report.standard.Standard(self._post_app, "Monitor", setup)
            rep.expressions = self._retrieve_default_expressions(expressions, rep, setup)
        return rep

    @pyaedt_function_handler(setup_name="setup")
    def fields(self, expressions=None, setup=None, polyline=None):
        """Create a Field Report object.

        Parameters
        ----------
        expressions : str or list
            One or more expressions to add to the report. The expression can be any of the available formula
            you can enter into the Electronics Desktop Report Editor.
        setup : str, optional
            Name of the setup. The default is ``None``, in which case the ``nominal_adaptive``
            setup is used. Be sure to build a setup string in the form of
            ``"SetupName : SetupSweep"``, where ``SetupSweep`` is the sweep name to
            use in the export or ``LastAdaptive``.
        polyline : str, optional
            Name of the polyline to plot the field on.
            If a name is not provided, the report might be incorrect.
            The default value is ``None``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.report_templates.Fields`

        Examples
        --------

        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss(my_project)
        >>> report = hfss.post.reports_by_category.fields("Mag_E", "Setup : LastAdaptive", "Polyline1")
        >>> report.create()
        >>> solutions = report.get_solution_data()
        """
        if not setup:
            # setup = self._post_app._app.nominal_sweep
            setup = self._post_app._app.nominal_adaptive
        rep = None
        if "Fields" in self._templates:
            rep = ansys.aedt.core.visualization.report.field.Fields(self._post_app, "Fields", setup)
            rep.polyline = polyline
            rep.expressions = self._retrieve_default_expressions(expressions, rep, setup)
        return rep

    @pyaedt_function_handler(setup_name="setup")
    def cg_fields(self, expressions=None, setup=None, polyline=None):
        """Create a CG Field Report object in Q3D and Q2D.

        Parameters
        ----------
        expressions : str or list
            Expression List to add into the report. The expression can be any of the available formula
            you can enter into the Electronics Desktop Report Editor.
        setup : str, optional
            Name of the setup. The default is ``None``, in which case the ``nominal_adaptive``
            setup is used. Be sure to build a setup string in the form of
            ``"SetupName : SetupSweep"``, where ``SetupSweep`` is the sweep name to
            use in the export or ``LastAdaptive``.
        polyline : str, optional
            Name of the polyline to plot the field on.
            If a name is not provided, the report might be incorrect.
            The default value is ``None``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.report_templates.Fields`

        Examples
        --------
        >>> from ansys.aedt.core import Q3d
        >>> q3d = Q3d(my_project)
        >>> report = q3d.post.reports_by_category.cg_fields("SmoothQ", "Setup : LastAdaptive", "Polyline1")
        >>> report.create()
        >>> solutions = report.get_solution_data()
        """
        if not setup:
            setup = self._post_app._app.nominal_sweep
        rep = None
        if "CG Fields" in self._templates:
            rep = ansys.aedt.core.visualization.report.field.Fields(self._post_app, "CG Fields", setup)
            rep.polyline = polyline
            rep.expressions = self._retrieve_default_expressions(expressions, rep, setup)
        return rep

    @pyaedt_function_handler(setup_name="setup")
    def dc_fields(self, expressions=None, setup=None, polyline=None):
        """Create a DC Field Report object in Q3D.

        Parameters
        ----------
        expressions : str or list
            Expression List to add into the report. The expression can be any of the available formula
            you can enter into the Electronics Desktop Report Editor.
        setup : str, optional
            Name of the setup. The default is ``None``, in which case the ``nominal_adaptive``
            setup is used. Be sure to build a setup string in the form of
            ``"SetupName : SetupSweep"``, where ``SetupSweep`` is the sweep name to
            use in the export or ``LastAdaptive``.
        polyline : str, optional
            Name of the polyline to plot the field on.
            If a name is not provided, the report might be incorrect.
            The default value is ``None``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.report_templates.Fields`

        Examples
        --------
        >>> from ansys.aedt.core import Q3d
        >>> q3d = Q3d(my_project)
        >>> report = q3d.post.reports_by_category.dc_fields("Mag_VolumeJdc", "Setup : LastAdaptive", "Polyline1")
        >>> report.create()
        >>> solutions = report.get_solution_data()
        """
        if not setup:
            setup = self._post_app._app.nominal_sweep
        rep = None
        if "DC R/L Fields" in self._templates:
            rep = ansys.aedt.core.visualization.report.field.Fields(self._post_app, "DC R/L Fields", setup)
            rep.polyline = polyline
            rep.expressions = self._retrieve_default_expressions(expressions, rep, setup)
        return rep

    @pyaedt_function_handler(setup_name="setup")
    def rl_fields(self, expressions=None, setup=None, polyline=None):
        """Create an AC RL Field Report object in Q3D and Q2D.

        Parameters
        ----------
        expressions : str or list
            Expression List to add into the report. The expression can be any of the available formula
            you can enter into the Electronics Desktop Report Editor.
        setup : str, optional
            Name of the setup. The default is ``None``, in which case the ``nominal_adaptive``
            setup is used. Be sure to build a setup string in the form of
            ``"SetupName : SetupSweep"``, where ``SetupSweep`` is the sweep name to
            use in the export or ``LastAdaptive``.
        polyline : str, optional
            Name of the polyline to plot the field on.
            If a name is not provided, the report might be incorrect.
            The default value is ``None``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.report_templates.Fields`

        Examples
        --------
        >>> from ansys.aedt.core import Q3d
        >>> q3d = Q3d(my_project)
        >>> report = q3d.post.reports_by_category.rl_fields("Mag_SurfaceJac", "Setup : LastAdaptive", "Polyline1")
        >>> report.create()
        >>> solutions = report.get_solution_data()
        """
        if not setup:
            setup = self._post_app._app.nominal_sweep
        rep = None
        if "AC R/L Fields" in self._templates or "RL Fields" in self._templates:
            if self._post_app._app.design_type == "Q3D Extractor":
                rep = ansys.aedt.core.visualization.report.field.Fields(self._post_app, "AC R/L Fields", setup)
            else:
                rep = ansys.aedt.core.visualization.report.field.Fields(self._post_app, "RL Fields", setup)
            rep.polyline = polyline
            rep.expressions = self._retrieve_default_expressions(expressions, rep, setup)
        return rep

    @pyaedt_function_handler(setup_name="setup")
    def far_field(self, expressions=None, setup=None, sphere_name=None, source_context=None, **variations):
        """Create a Far Field Report object.

        Parameters
        ----------
        expressions : str or list
            Expression List to add into the report. The expression can be any of the available formula
            you can enter into the Electronics Desktop Report Editor.
        setup : str, optional
            Name of the setup. The default is ``None``, in which case the ``nominal_adaptive``
            setup is used. Be sure to build a setup string in the form of
            ``"SetupName : SetupSweep"``, where ``SetupSweep`` is the sweep name to
            use in the export or ``LastAdaptive``.
        sphere_name : str, optional
            Name of the sphere to create the far field on.
        source_context : str, optional
            Name of the active source to create the far field on.

        Returns
        -------
        :class:`ansys.aedt.core.modules.report_templates.FarField`

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss(my_project)
        >>> report = hfss.post.reports_by_category.far_field("GainTotal", "Setup : LastAdaptive", "3D_Sphere")
        >>> report.primary_sweep = "Phi"
        >>> report.create()
        >>> solutions = report.get_solution_data()
        """
        if not setup:
            setup = self._post_app._app.nominal_sweep
        rep = None
        if "Far Fields" in self._templates:
            setup = self._post_app._get_setup_from_sweep_name(setup)
            rep = ansys.aedt.core.visualization.report.field.FarField(self._post_app, "Far Fields", setup, **variations)
            rep.far_field_sphere = sphere_name
            rep.source_context = source_context
            rep.report_type = "Radiation Pattern"
            if expressions:
                if type(expressions) == list:
                    rep.expressions = expressions
                else:
                    rep.expressions = [expressions]
            else:
                rep.expressions = self._retrieve_default_expressions(expressions, rep, setup)
        return rep

    @pyaedt_function_handler(setup_name="setup", sphere_name="infinite_sphere")
    def antenna_parameters(self, expressions=None, setup=None, infinite_sphere=None):
        """Create an Antenna Parameters Report object.

        Parameters
        ----------
        expressions : str or list
            Expression List to add into the report. The expression can be any of the available formula
            you can enter into the Electronics Desktop Report Editor.
        setup : str, optional
            Name of the setup. The default is ``None``, in which case the ``nominal_adaptive``
            setup is used. Be sure to build a setup string in the form of
            ``"SetupName : SetupSweep"``, where ``SetupSweep`` is the sweep name to
            use in the export or ``LastAdaptive``.
        infinite_sphere : str, optional
            Name of the sphere to compute antenna parameters on.

        Returns
        -------
        :class:`ansys.aedt.core.modules.report_templates.AntennaParameters`

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss(my_project)
        >>> report = hfss.post.reports_by_category.antenna_parameters("GainTotal", "Setup : LastAdaptive", "3D_Sphere")
        >>> report.create()
        >>> solutions = report.get_solution_data()
        """
        if not setup:
            setup = self._post_app._app.nominal_sweep
        rep = None
        if "Antenna Parameters" in self._templates:
            rep = ansys.aedt.core.visualization.report.field.AntennaParameters(
                self._post_app, "Antenna Parameters", setup, infinite_sphere
            )
            rep.expressions = self._retrieve_default_expressions(expressions, rep, setup)
        return rep

    @pyaedt_function_handler(setup_name="setup")
    def near_field(self, expressions=None, setup=None):
        """Create a Field Report object.

        Parameters
        ----------
        expressions : str or list
            Expression List to add into the report. The expression can be any of the available formula
            you can enter into the Electronics Desktop Report Editor.
        setup : str, optional
            Name of the setup. The default is ``None``, in which case the ``nominal_adaptive``
            setup is used. Be sure to build a setup string in the form of
            ``"SetupName : SetupSweep"``, where ``SetupSweep`` is the sweep name to
            use in the export or ``LastAdaptive``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.report_templates.NearField`

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss(my_project)
        >>> report = hfss.post.reports_by_category.near_field("GainTotal", "Setup : LastAdaptive", "NF_1")
        >>> report.primary_sweep = "Phi"
        >>> report.create()
        >>> solutions = report.get_solution_data()
        """
        if not setup:
            setup = self._post_app._app.nominal_sweep
        rep = None
        if "Near Fields" in self._templates:
            rep = ansys.aedt.core.visualization.report.field.NearField(self._post_app, "Near Fields", setup)
            rep.expressions = self._retrieve_default_expressions(expressions, rep, setup)
        return rep

    @pyaedt_function_handler(setup_name="setup")
    def modal_solution(self, expressions=None, setup=None):
        """Create a Standard or Default Report object.

        Parameters
        ----------
        expressions : str or list
            Expression List to add into the report. The expression can be any of the available formula
            you can enter into the Electronics Desktop Report Editor.
        setup : str, optional
            Name of the setup. The default is ``None``, in which case the ``nominal_adaptive``
            setup is used. Be sure to build a setup string in the form of
            ``"SetupName : SetupSweep"``, where ``SetupSweep`` is the sweep name to
            use in the export or ``LastAdaptive``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.report_templates.Standard`

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss(my_project)
        >>> report = hfss.post.reports_by_category.modal_solution("dB(S(1,1))")
        >>> report.create()
        >>> solutions = report.get_solution_data()
        """
        if not setup:
            setup = self._post_app._app.nominal_sweep
        rep = None
        if "Modal Solution Data" in self._templates:
            rep = ansys.aedt.core.visualization.report.standard.Standard(self._post_app, "Modal Solution Data", setup)
            rep.expressions = self._retrieve_default_expressions(expressions, rep, setup)
        return rep

    @pyaedt_function_handler(setup_name="setup")
    def terminal_solution(self, expressions=None, setup=None):
        """Create a Standard or Default Report object.

        Parameters
        ----------
        expressions : str or list
            Expression List to add into the report. The expression can be any of the available formula
            you can enter into the Electronics Desktop Report Editor.
        setup : str, optional
            Name of the setup. The default is ``None``, in which case the ``nominal_adaptive``
            setup is used. Be sure to build a setup string in the form of
            ``"SetupName : SetupSweep"``, where ``SetupSweep`` is the sweep name to
            use in the export or ``LastAdaptive``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.report_templates.Standard`

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss(my_project)
        >>> report = hfss.post.reports_by_category.terminal_solution("dB(S(1,1))")
        >>> report.create()
        >>> solutions = report.get_solution_data()
        """
        if not setup:
            setup = self._post_app._app.nominal_sweep
        rep = None
        if "Terminal Solution Data" in self._templates:
            rep = ansys.aedt.core.visualization.report.standard.Standard(
                self._post_app, "Terminal Solution Data", setup
            )
            rep.expressions = self._retrieve_default_expressions(expressions, rep, setup)
        return rep

    @pyaedt_function_handler(setup_name="setup")
    def eigenmode(self, expressions=None, setup=None):
        """Create a Standard or Default Report object.

        Parameters
        ----------
        expressions : str or list
            Expression List to add into the report. The expression can be any of the available formula
            you can enter into the Electronics Desktop Report Editor.
        setup : str, optional
            Name of the setup. The default is ``None``, in which case the ``nominal_adaptive``
            setup is used. Be sure to build a setup string in the form of
            ``"SetupName : SetupSweep"``, where ``SetupSweep`` is the sweep name to
            use in the export or ``LastAdaptive``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.report_templates.Standard`

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss(my_project)
        >>> report = hfss.post.reports_by_category.eigenmode("dB(S(1,1))")
        >>> report.create()
        >>> solutions = report.get_solution_data()
        """
        if not setup:
            setup = self._post_app._app.nominal_sweep
        rep = None
        if "Eigenmode Parameters" in self._templates:
            rep = ansys.aedt.core.visualization.report.standard.Standard(self._post_app, "Eigenmode Parameters", setup)
            rep.expressions = self._retrieve_default_expressions(expressions, rep, setup)
        return rep

    @pyaedt_function_handler(setup_name="setup")
    def statistical_eye_contour(self, expressions=None, setup=None, quantity_type=3):
        """Create a standard statistical AMI contour plot.

        Parameters
        ----------
        expressions : str
            Expression to add into the report. The expression can be any of the available formula
            you can enter into the Electronics Desktop Report Editor.
        setup : str, optional
            Name of the setup. The default is ``None``, in which case the ``nominal_adaptive``
            setup is used. Be sure to build a setup string in the form of
            ``"SetupName : SetupSweep"``, where ``SetupSweep`` is either the sweep
             name to use in the export or ``LastAdaptive``.
        quantity_type : int, optional
            For AMI analysis only, the quantity type. The default is ``3``. Options are:

            - ``0`` for Initial Wave
            - ``1`` for Wave after Source
            - ``2`` for Wave after Channel
            - ``3`` for Wave after Probe.

        Returns
        -------
        :class:`ansys.aedt.core.modules.report_templates.AMIConturEyeDiagram`

        Examples
        --------
        >>> from ansys.aedt.core import Circuit
        >>> cir= Circuit()
        >>> new_eye = cir.post.reports_by_category.statistical_eye_contour("V(Vout)")
        >>> new_eye.unit_interval = "1e-9s"
        >>> new_eye.time_stop = "100ns"
        >>> new_eye.create()

        """
        if not setup:
            for setup in self._post_app._app.setups:
                if "AMIAnalysis" in setup.props:
                    setup = setup.name
            if not setup:
                self._post_app._app.logger.error("AMI analysis is needed to create this report.")
                return False

            if isinstance(expressions, list):
                expressions = expressions[0]
            report_cat = "Standard"
            rep = ansys.aedt.core.visualization.report.eye.AMIConturEyeDiagram(self._post_app, report_cat, setup)
            rep.quantity_type = quantity_type
            rep.expressions = self._retrieve_default_expressions(expressions, rep, setup)

            return rep
        return

    @pyaedt_function_handler(setup_name="setup")
    def eye_diagram(
        self, expressions=None, setup=None, quantity_type=3, statistical_analysis=True, unit_interval="1ns"
    ):
        """Create a Standard or Default Report object.

        Parameters
        ----------
        expressions : str
            Expression to add into the report. The expression can be any of the available formula
            you can enter into the Electronics Desktop Report Editor.
        setup : str, optional
            Name of the setup. The default is ``None``, in which case the ``nominal_adaptive``
            setup is used. Be sure to build a setup string in the form of
            ``"SetupName : SetupSweep"``, where ``SetupSweep`` is the sweep name to
            use in the export or ``LastAdaptive``.
        quantity_type : int, optional
            For AMI Analysis only, specify the quantity type. Options are: 0 for Initial Wave,
            1 for Wave after Source, 2 for Wave after Channel and 3 for Wave after Probe. Default is 3.
        statistical_analysis : bool, optional
            For AMI Analysis only, whether to plot the statistical eye plot or transient eye plot.
            The default is ``True``.
        unit_interval : str, optional
            Unit interval for the eye diagram.

        Returns
        -------
        :class:`ansys.aedt.core.modules.report_templates.Standard`

        Examples
        --------
        >>> from ansys.aedt.core import Circuit
        >>> cir= Circuit()
        >>> new_eye = cir.post.reports_by_category.eye_diagram("V(Vout)")
        >>> new_eye.unit_interval = "1e-9s"
        >>> new_eye.time_stop = "100ns"
        >>> new_eye.create()
        """
        if not setup:
            setup = self._post_app._app.nominal_sweep
        if "Eye Diagram" in self._templates:
            if "AMIAnalysis" in self._post_app._app.get_setup(setup).props:

                report_cat = "Eye Diagram"
                if statistical_analysis:
                    report_cat = "Statistical Eye"
                rep = ansys.aedt.core.visualization.report.eye.AMIEyeDiagram(self._post_app, report_cat, setup)
                rep.quantity_type = quantity_type
                expressions = self._retrieve_default_expressions(expressions, rep, setup)
                if isinstance(expressions, list):
                    rep.expressions = expressions[0]
                return rep

            else:
                rep = ansys.aedt.core.visualization.report.eye.EyeDiagram(self._post_app, "Eye Diagram", setup)
            rep.unit_interval = unit_interval
            rep.expressions = self._retrieve_default_expressions(expressions, rep, setup)
            return rep

        return

    @pyaedt_function_handler(setup_name="setup")
    def spectral(self, expressions=None, setup=None):
        """Create a Spectral Report object.

        Parameters
        ----------
        expressions : str or list, optional
            Expression List to add into the report. The expression can be any of the available formula
            you can enter into the Electronics Desktop Report Editor.
        setup : str, optional
            Name of the setup. The default is ``None``, in which case the ``nominal_adaptive``
            setup is used. Be sure to build a setup string in the form of
            ``"SetupName : SetupSweep"``, where ``SetupSweep`` is the sweep name to
            use in the export or ``LastAdaptive``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.report_templates.Spectrum`

        Examples
        --------
        >>> from ansys.aedt.core import Circuit
        >>> cir= Circuit()
        >>> new_eye = cir.post.reports_by_category.spectral("V(Vout)")
        >>> new_eye.create()

        """
        if not setup:
            setup = self._post_app._app.nominal_sweep
        rep = None
        if "Spectrum" in self._templates:
            rep = ansys.aedt.core.visualization.report.standard.Spectral(self._post_app, "Spectrum", setup)
            rep.expressions = self._retrieve_default_expressions(expressions, rep, setup)
        return rep

    @pyaedt_function_handler()
    def emi_receiver(self, expressions=None, setup_name=None):
        """Create an EMI receiver report.

        Parameters
        ----------
        expressions : str or list, optional
            One or more expressions to add into the report. An expression can be any of the formulas that
            can be entered into the Electronics Desktop Report Editor.
        setup_name : str, optional
            Name of the setup. The default is ``None``, in which case the ``nominal_adaptive``
            setup is used. Be sure to build a setup string in the form of
            ``"SetupName : SetupSweep"``, where ``SetupSweep`` is either the sweep name
            to use in the export or ``LastAdaptive``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.report_templates.EMIReceiver`

        Examples
        --------
        >>> from ansys.aedt.core import Circuit
        >>> cir= Circuit()
        >>> new_eye = cir.post.emi_receiver()
        >>> new_eye.create()
        """
        if not setup_name:
            setup_name = self._post_app._app.nominal_sweep
        rep = None
        if "EMIReceiver" in self._templates and self._post_app._app.desktop_class.aedt_version_id > "2023.2":
            rep = ansys.aedt.core.visualization.report.emi.EMIReceiver(self._post_app, setup_name)
            if not expressions:
                expressions = f"Average[{rep.net}]"
            else:
                if not isinstance(expressions, list):
                    expressions = [expressions]
                pattern = r"\w+\[(.*?)\]"
                for expression in expressions:
                    match = re.search(pattern, expression)
                    if match:
                        net_name = match.group(1)
                        rep.net = net_name
            rep.expressions = self._retrieve_default_expressions(expressions, rep, setup_name)

        return rep
