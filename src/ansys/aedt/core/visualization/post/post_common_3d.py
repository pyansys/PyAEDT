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
Module containing the class: `PostProcessor3D`.

This module provides all functionalities for creating and editing plots in the 3D tools.

"""
from __future__ import absolute_import

import ast
import os
import random
import string
import warnings

from ansys.aedt.core.generic.constants import unit_converter
from ansys.aedt.core.generic.general_methods import check_and_download_file
from ansys.aedt.core.generic.general_methods import generate_unique_name
from ansys.aedt.core.generic.general_methods import open_file
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.generic.numbers import decompose_variable_value
from ansys.aedt.core.generic.settings import settings
from ansys.aedt.core.modeler.cad.elements_3d import FacePrimitive
from ansys.aedt.core.visualization.plot.pyvista import ModelPlotter
from ansys.aedt.core.visualization.post.common import PostProcessorCommon
from ansys.aedt.core.visualization.post.fields_calculator import FieldsCalculator

try:
    import numpy as np
except ImportError:
    np = None
    warnings.warn(
        "The NumPy module is required to run some functionalities of PostProcess.\n"
        "Install with \n\npip install numpy"
    )

from ansys.aedt.core.visualization.post.field_data import FieldPlot
from ansys.aedt.core.visualization.post.vrt_data import VRTFieldPlot
from ansys.aedt.core.visualization.report.constants import ORIENTATION_TO_VIEW


class PostProcessor3D(PostProcessorCommon):
    """Manages the main AEDT postprocessing functions.

    The inherited ``AEDTConfig`` class contains all ``_desktop``
    hierarchical calls needed for the class initialization data
    ``_desktop`` and the design types ``"HFSS"``, ``"Icepak"``, and
    ``"HFSS3DLayout"``.

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
    Basic usage demonstrated with an HFSS, Maxwell, or any other design:

    >>> from ansys.aedt.core import Hfss
    >>> hfss = Hfss()
    >>> post = hfss.post
    """

    def __init__(self, app):
        app.logger.reset_timer()
        self._app = app
        self._post_osolution = self._app.osolution
        self.field_plots = self._get_fields_plot()
        PostProcessorCommon.__init__(self, app)
        self.fields_calculator = FieldsCalculator(app)
        app.logger.info_timer("PostProcessor class has been initialized!")

    @property
    def _primitives(self):  # pragma: no cover
        """Primitives.

        Returns
        -------
        ansys.aedt.core.modeler.cad.primitives
            Primitives object.

        """
        return self._app.modeler

    @property
    def model_units(self):
        """Model units.

        Returns
        -------
        str
           Model units, such as ``"mm"``.
        """
        return self._app.units.length

    @property
    def post_osolution(self):
        """Solution.

        Returns
        -------
        type
            Solution module.
        """
        return self._post_osolution

    @property
    def ofieldsreporter(self):
        """Fields reporter.

        Returns
        -------
        :attr:`ansys.aedt.core.modules.post_general.PostProcessor.ofieldsreporter`

        References
        ----------
        >>> oDesign.GetModule("FieldsReporter")
        """
        return self._app.ofieldsreporter

    @property
    def field_plot_names(self):
        """Fields plot names.

        Returns
        -------
        str
            Field plot names.
        """
        return self._app.ofieldsreporter.GetChildNames()

    @pyaedt_function_handler()
    def _get_base_name(self, setup):
        setups_data = self._app.design_properties["FieldsReporter"]["FieldsPlotManagerID"]
        if "SimDataExtractors" in self._app.design_properties["SolutionManager"]:
            sim_data = self._app.design_properties["SolutionManager"]["SimDataExtractors"]
        else:
            sim_data = self._app.design_properties["SolutionManager"]
        if "SimSetup" in sim_data:
            if isinstance(sim_data["SimSetup"], list):  # pragma: no cover
                for solution in sim_data["SimSetup"]:
                    base_name = solution["Name"]
                    if isinstance(solution["Solution"], dict):
                        sols = [solution["Solution"]]
                    else:
                        sols = solution["Solution"]
                    for sol in sols:
                        if sol["ID"] == setups_data[setup]["SolutionId"]:
                            base_name += " : " + sol["Name"]
                            return base_name
            else:
                base_name = sim_data["SimSetup"]["Name"]
                if isinstance(sim_data["SimSetup"]["Solution"], list):
                    for sol in sim_data["SimSetup"]["Solution"]:
                        if sol["ID"] == setups_data[setup]["SolutionId"]:
                            base_name += " : " + sol["Name"]
                            return base_name
                else:
                    sol = sim_data["SimSetup"]["Solution"]
                    if sol["ID"] == setups_data[setup]["SolutionId"]:
                        base_name += " : " + sol["Name"]
                        return base_name
        return ""  # pragma: no cover

    @pyaedt_function_handler()
    def _get_intrinsic(self, setup):
        setups_data = self._app.design_properties["FieldsReporter"]["FieldsPlotManagerID"]
        intrinsics = [i.split("=") for i in setups_data[setup]["IntrinsicVar"].split(" ")]
        intr_dict = {}
        if intrinsics:
            for intr in intrinsics:
                if isinstance(intr, list) and len(intr) == 2:
                    intr_dict[intr[0]] = intr[1].replace("\\", "").replace("'", "")
        return intr_dict  # pragma: no cover

    @pyaedt_function_handler(list_objs="assignment")
    def _get_volume_objects(self, assignment):
        obj_list = []
        if self._app.solution_type not in ["HFSS3DLayout", "HFSS 3D Layout Design"]:
            obj_list = []
            editor = self._app._odesign.SetActiveEditor("3D Modeler")
            for obj in assignment:
                obj_list.append(editor.GetObjectNameByID(int(obj)))
        if obj_list:
            return obj_list
        else:
            return assignment

    @pyaedt_function_handler(list_objs="assignment")
    def _get_surface_objects(self, assignment):
        faces = [int(i) for i in assignment]
        if self._app.solution_type not in ["HFSS3DLayout", "HFSS 3D Layout Design"]:
            planes = self._get_cs_plane_ids()
            objs = []
            for face in faces:
                if face in list(planes.keys()):
                    objs.append(planes[face])
            if objs:
                return "CutPlane", objs
        return "FacesList", faces

    @pyaedt_function_handler()
    def _get_cs_plane_ids(self):
        name2refid = {-4: "Global:XY", -3: "Global:YZ", -2: "Global:XZ"}
        if self._app.design_properties and "ModelSetup" in self._app.design_properties:  # pragma: no cover
            cs = self._app.design_properties["ModelSetup"]["GeometryCore"]["GeometryOperations"]["CoordinateSystems"]
            for ds in cs:
                try:
                    if isinstance(cs[ds], dict):
                        name = cs[ds]["Attributes"]["Name"]
                        cs_id = cs[ds]["XYPlaneID"]
                        name2refid[cs_id] = name + ":XY"
                        name2refid[cs_id + 1] = name + ":YZ"
                        name2refid[cs_id + 2] = name + ":XZ"
                    elif isinstance(cs[ds], list):
                        for el in cs[ds]:
                            cs_id = el["XYPlaneID"]
                            name = el["Attributes"]["Name"]
                            name2refid[cs_id] = name + ":XY"
                            name2refid[cs_id + 1] = name + ":YZ"
                            name2refid[cs_id + 2] = name + ":XZ"
                except Exception:
                    self.logger.debug(
                        f"Something went wrong with key {ds} while retrieving coordinate systems plane ids."
                    )  # pragma: no cover
        return name2refid

    @pyaedt_function_handler()
    def _get_fields_plot(self):
        plots = {}
        if (
            self._app.design_properties
            and "FieldsReporter" in self._app.design_properties
            and "FieldsPlotManagerID" in self._app.design_properties["FieldsReporter"]
        ):
            setups_data = self._app.design_properties["FieldsReporter"]["FieldsPlotManagerID"]
            for setup in setups_data:
                try:
                    if isinstance(setups_data[setup], dict) and "PlotDefinition" in setup:
                        plot_name = setups_data[setup]["PlotName"]
                        plots[plot_name] = FieldPlot(self)
                        plots[plot_name].solution = self._get_base_name(setup)
                        plots[plot_name].quantity = self.ofieldsreporter.GetFieldPlotQuantityName(
                            setups_data[setup]["PlotName"]
                        )
                        plots[plot_name].intrinsics = self._get_intrinsic(setup)
                        list_objs = setups_data[setup]["FieldPlotGeometry"][1:]
                        while list_objs:
                            id = list_objs[0]
                            num_objects = list_objs[2]
                            if id == 64:
                                plots[plot_name].volumes = self._get_volume_objects(list_objs[3 : num_objects + 3])
                            elif id == 128:
                                out, faces = self._get_surface_objects(list_objs[3 : num_objects + 3])
                                if out == "CutPlane":
                                    plots[plot_name].cutplanes = faces
                                else:
                                    plots[plot_name].surfaces = faces
                            elif id == 256:
                                plots[plot_name].lines = self._get_volume_objects(list_objs[3 : num_objects + 3])
                            list_objs = list_objs[num_objects + 3 :]
                        plots[plot_name].name = setups_data[setup]["PlotName"]
                        plots[plot_name].plot_folder = setups_data[setup]["PlotFolder"]
                        surf_setts = setups_data[setup]["PlotOnSurfaceSettings"]
                        plots[plot_name].Filled = surf_setts["Filled"]
                        plots[plot_name].IsoVal = surf_setts["IsoValType"]
                        plots[plot_name].AddGrid = surf_setts["AddGrid"]
                        plots[plot_name].MapTransparency = surf_setts["MapTransparency"]
                        plots[plot_name].Refinement = surf_setts["Refinement"]
                        plots[plot_name].Transparency = surf_setts["Transparency"]
                        plots[plot_name].SmoothingLevel = surf_setts["SmoothingLevel"]
                        arrow_setts = surf_setts["Arrow3DSpacingSettings"]
                        plots[plot_name].ArrowUniform = arrow_setts["ArrowUniform"]
                        plots[plot_name].ArrowSpacing = arrow_setts["ArrowSpacing"]
                        plots[plot_name].MinArrowSpacing = arrow_setts["MinArrowSpacing"]
                        plots[plot_name].MaxArrowSpacing = arrow_setts["MaxArrowSpacing"]
                        plots[plot_name].GridColor = surf_setts["GridColor"]
                except Exception:
                    self.logger.debug(
                        f"Something went wrong with setup {setup} while retrieving fields plot."
                    )  # pragma: no cover
        return plots

    # TODO: define a fields calculator module and make robust !!
    @pyaedt_function_handler(object_name="assignment")
    def volumetric_loss(self, assignment):
        """Use the field calculator to create a variable for volumetric losses.

        Parameters
        ----------
        assignment : str
            Name of the object to compute volumetric losses on.

        Returns
        -------
        str
            Name of the variable created.

        References
        ----------
        >>> oModule.EnterQty
        >>> oModule.EnterVol
        >>> oModule.CalcOp
        >>> oModule.AddNamedExpression
        """
        oModule = self.ofieldsreporter
        oModule.EnterQty("OhmicLoss")
        oModule.EnterVol(assignment)
        oModule.CalcOp("Integrate")
        name = f"P_{assignment}"  # Need to check for uniqueness !
        oModule.AddNamedExpression(name, "Fields")
        return name

    @pyaedt_function_handler(plotname="plot_name", propertyname="property_name", propertyval="property_value")
    def change_field_property(self, plot_name, property_name, property_value):
        """Modify a field plot property.

        Parameters
        ----------
        plot_name : str
            Name of the field plot.
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
        >>> oDesign.ChangeProperty
        """
        self._odesign.ChangeProperty(
            [
                "NAME:AllTabs",
                [
                    "NAME:FieldsPostProcessorTab",
                    ["NAME:PropServers", "FieldsReporter:" + plot_name],
                    ["NAME:ChangedProps", ["NAME:" + property_name, "Value:=", property_value]],
                ],
            ]
        )

    @pyaedt_function_handler(quantity_name="quantity", variation_dict="variations", isvector="is_vector")
    def get_scalar_field_value(
        self,
        quantity,
        scalar_function="Maximum",
        solution=None,
        variations=None,
        is_vector=False,
        intrinsics=None,
        phase=None,
        object_name="AllObjects",
        object_type="volume",
        adjacent_side=False,
    ):
        """Use the field calculator to Compute Scalar of a Field.

        Parameters
        ----------
        quantity : str
            Name of the quantity to export. For example, ``"Temp"``.
        scalar_function : str, optional
            The name of the scalar function. For example, ``"Maximum"``, ``"Integrate"``.
            The default is ``"Maximum"``.
        solution : str, optional
            Name of the solution in the format ``"solution : sweep"``. The default is ``None``.
        variations : dict, optional
            Dictionary of all variation variables with their values.
            e.g. ``['power_block:=', ['0.6W'], 'power_source:=', ['0.15W']]``
            The default is ``None``.
        is_vector : bool, optional
            Whether the quantity is a vector. The  default is ``False``.
        intrinsics : dict, str, optional
            Intrinsic variables required to compute the field before the export.
            These are typically: frequency, time and phase.
            It can be provided either as a dictionary or as a string.

            If it is a dictionary, keys depend on the solution type and can be expressed as:
            - ``"Freq"`` or ``"Frequency"``.
            - ``"Time"``.
            - ``"Phase"``.

            If it is a string, it can either be ``"Freq"`` or ``"Time"`` depending on the solution type.
            The default is ``None`` in which case the intrinsics value is automatically computed based on the setup.
        phase : str, optional
            Field phase. The default is ``None``.
        object_name : str, optional
            Name of the object. For example, ``"Box1"``.
            The default is ``"AllObjects"``.
        object_type : str, optional
            Type of the object - ``"volume"``, ``"surface"``, ``"point"``.
            The default is ``"volume"``.
        adjacent_side : bool, optional
            To query quantity value on adjacent side for object_type = "surface", pass ``True``.
            The default is ``False``.

        Returns
        -------
        float
            Scalar field value.

        References
        ----------
        >>> oModule.EnterQty
        >>> oModule.CopyNamedExprToStack
        >>> oModule.CalcOp
        >>> oModule.EnterQty
        >>> oModule.EnterVol
        >>> oModule.ClcEval
        >>> GetTopEntryValue

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> aedtapp = Hfss()
        >>> # Intrinsics is explicitly provided as a dictionary.
        >>> intrinsics = {"Freq": "5GHz", "Phase": "180deg"}
        >>> min_value = aedtapp.post.get_scalar_field_value(quantity_name, "Minimum", setup_name, intrinsics=intrinsics)
        >>> plot1 = aedtapp.post.create_fieldplot_cutplane(cutlist, quantity_name, setup_name, intrinsics=intrinsics)
        >>> # Intrinsics is provided as a string. Phase is automatically assigned to 0deg.
        >>> min_value = aedtapp.post.get_scalar_field_value(quantity_name, "Minimum", setup_name, intrinsics="5GHz")
        >>> plot1 = aedtapp.post.create_fieldplot_cutplane(cutlist, quantity_name, setup_name, intrinsics="5GHz")
        >>> # Intrinsics is provided as a dictionary. Phase is automatically assigned to 0deg.
        >>> intrinsics = {"Freq": "5GHz"}
        >>> min_value = aedtapp.post.get_scalar_field_value(quantity_name, "Minimum", setup_name, intrinsics=intrinsics)
        >>> plot1 = aedtapp.post.create_fieldplot_cutplane(cutlist, quantity_name, setup_name, intrinsics=intrinsics)
        >>> # Intrinsics is not provided and is automatically computed from the setup.
        >>> min_value = aedtapp.post.get_scalar_field_value(quantity_name, "Minimum", setup_name)
        >>> plot1 = aedtapp.post.create_fieldplot_cutplane(cutlist, quantity_name, setup_name)
        """
        intrinsics = self._app._check_intrinsics(intrinsics, phase, solution, return_list=True)
        self.logger.info(f"Exporting {quantity} field. Be patient")
        if not solution:
            solution = self._app.existing_analysis_sweeps[0]
        self.ofieldsreporter.CalcStack("clear")
        if is_vector:
            try:
                self.ofieldsreporter.EnterQty(quantity)
            except Exception:
                self.ofieldsreporter.CopyNamedExprToStack(quantity)
            self.ofieldsreporter.CalcOp("Smooth")
            self.ofieldsreporter.EnterScalar(0)
            self.ofieldsreporter.CalcOp("AtPhase")
            self.ofieldsreporter.CalcOp("Mag")
        else:
            try:
                self.ofieldsreporter.EnterQty(quantity)
            except Exception:
                self.logger.info(f"Quantity {quantity} not present. Trying to get it from Stack")
                self.ofieldsreporter.CopyNamedExprToStack(quantity)
        obj_list = object_name
        if scalar_function:
            if object_type == "volume":
                self.ofieldsreporter.EnterVol(obj_list)
            elif object_type == "surface":
                if adjacent_side:
                    self.ofieldsreporter.EnterAdjacentSurf(obj_list)
                else:
                    self.ofieldsreporter.EnterSurf(obj_list)
            elif object_type == "point":
                self.ofieldsreporter.EnterPoint(obj_list)
            self.ofieldsreporter.CalcOp(scalar_function)

        if not variations:
            variations = self._app.available_variations.nominal_w_values_dict

        variation = []
        for el, value in variations.items():
            if self._app.variable_manager.variables[el].sweep:
                variation.append(el + ":=")
                variation.append(value)

        variation.extend(intrinsics)

        file_name = os.path.join(self._app.working_directory, generate_unique_name("temp_fld") + ".fld")
        self.ofieldsreporter.CalculatorWrite(file_name, ["Solution:=", solution], variation)
        value = None
        if os.path.exists(file_name) or settings.remote_rpc_session:
            with open_file(file_name, "r") as f:
                lines = f.readlines()
                lines = [line.strip() for line in lines]
                value = lines[-1]
            os.remove(file_name)
        self.ofieldsreporter.CalcStack("clear")
        return float(value)

    @pyaedt_function_handler(
        quantity_name="quantity",
        variation_dict="variations",
        filename="file_name",
        gridtype="grid_type",
        isvector="is_vector",
    )
    def export_field_file_on_grid(
        self,
        quantity,
        solution=None,
        variations=None,
        file_name=None,
        grid_type="Cartesian",
        grid_center=None,
        grid_start=None,
        grid_stop=None,
        grid_step=None,
        is_vector=False,
        intrinsics=None,
        phase=None,
        export_with_sample_points=True,
        reference_coordinate_system="Global",
        export_in_si_system=True,
        export_field_in_reference=True,
    ):
        """Use the field calculator to create a field file on a grid based on a solution and variation.

        Parameters
        ----------
        quantity : str
            Name of the quantity to export. For example, ``"Temp"``.
        solution : str, optional
            Name of the solution in the format ``"solution : sweep"``. The default is ``None``.
        variations : dict, optional
            Dictionary of all variation variables with their values.
            The default is ``None``.
        file_name : str, optional
            Full path and name to save the file to.
            The default is ``None``, in which case the file is exported
            to the working directory.
        grid_type : str, optional
            Type of the grid to export. The default is ``"Cartesian"``.
        grid_center : list, optional
            The ``[x, y, z]`` coordinates for the center of the grid.
            The default is ``[0, 0, 0]``. This parameter is disabled if ``gridtype=
            "Cartesian"``.
        grid_start : list, optional
            The ``[x, y, z]`` coordinates for the starting point of the grid.
            The default is ``[0, 0, 0]``.
        grid_stop : list, optional
            The ``[x, y, z]`` coordinates for the stopping point of the grid.
            The default is ``[0, 0, 0]``.
        grid_step : list, optional
            The ``[x, y, z]`` coordinates for the step size of the grid.
            The default is ``[0, 0, 0]``.
        is_vector : bool, optional
            Whether the quantity is a vector. The  default is ``False``.
        intrinsics : dict, str, optional
            Intrinsic variables required to compute the field before the export.
            These are typically: frequency, time and phase.
            It can be provided either as a dictionary or as a string.
            If it is a dictionary, keys depend on the solution type and can be expressed in lower or camel case as:
            - ``"Freq"`` or ``"Frequency"``.
            - ``"Time"``.
            - ``"Phase"``.
            If it is a string, it can either be ``"Freq"`` or ``"Time"`` depending on the solution type.
            The default is ``None`` in which case the intrinsics value is automatically computed based on the setup.
        phase : str, optional
            Field phase. The default is ``None``.
        export_with_sample_points : bool, optional
            Whether to include the sample points in the file to export.
            The default is ``True``.
        reference_coordinate_system : str, optional
            Reference coordinate system in the file to export.
            The default is ``"Global"``.
        export_in_si_system : bool, optional
            Whether the provided sample points are defined in the SI system or model units.
            The default is ``True``.
        export_field_in_reference : bool, optional
            Whether to export the field in reference coordinate system.
            The default is ``True``.

        Returns
        -------
        str
            Field file path when succeeded.

        References
        ----------
        >>> oModule.EnterQty
        >>> oModule.CopyNamedExprToStack
        >>> oModule.CalcOp
        >>> oModule.EnterQty
        >>> oModule.EnterVol
        >>> oModule.ExportOnGrid

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> var = hfss.available_variations.nominal_w_values
        >>> setup = "Setup1 : LastAdaptive"
        >>> path = "Field.fld"
        >>> hfss.post.export_field_file_on_grid("E",setup,var,path,'Cartesian',[0, 0, 0],intrinsics="8GHz")
        """
        intrinsics = self._app._check_intrinsics(intrinsics, phase, solution, return_list=True)
        self.logger.info("Exporting %s field. Be patient", quantity)
        if grid_step is None:
            grid_step = [0, 0, 0]
        if grid_start is None:
            grid_start = [0, 0, 0]
        if grid_stop is None:
            grid_stop = [0, 0, 0]
        if grid_center is None:
            grid_center = [0, 0, 0]
        self.logger.info("Exporting %s field. Be patient", quantity)
        if not solution:
            solution = self._app.existing_analysis_sweeps[0]
        if not file_name:
            file_name = os.path.join(self._app.working_directory, f"{quantity}_{solution.replace(' : ', '_')}.fld")
        elif os.path.isdir(file_name):
            file_name = os.path.join(file_name, f"{quantity}_{solution.replace(' : ', '_')}.fld")
        self.ofieldsreporter.CalcStack("clear")
        try:
            self.ofieldsreporter.EnterQty(quantity)
        except Exception:
            self.ofieldsreporter.CopyNamedExprToStack(quantity)
        if is_vector:
            self.ofieldsreporter.CalcOp("Smooth")
            if phase:
                self.ofieldsreporter.EnterScalar(0)
                self.ofieldsreporter.CalcOp("AtPhase")
                self.ofieldsreporter.CalcOp("Mag")
        units = self._app.modeler.model_units
        ang_units = "deg"
        if grid_type == "Cartesian":
            grid_center = ["0mm", "0mm", "0mm"]
            grid_start_wu = [str(i) + units for i in grid_start]
            grid_stop_wu = [str(i) + units for i in grid_stop]
            grid_step_wu = [str(i) + units for i in grid_step]
        elif grid_type == "Cylindrical":
            grid_center = [str(i) + units for i in grid_center]
            grid_start_wu = [str(grid_start[0]) + units, str(grid_start[1]) + ang_units, str(grid_start[2]) + units]
            grid_stop_wu = [str(grid_stop[0]) + units, str(grid_stop[1]) + ang_units, str(grid_stop[2]) + units]
            grid_step_wu = [str(grid_step[0]) + units, str(grid_step[1]) + ang_units, str(grid_step[2]) + units]
        elif grid_type == "Spherical":
            grid_center = [str(i) + units for i in grid_center]
            grid_start_wu = [str(grid_start[0]) + units, str(grid_start[1]) + ang_units, str(grid_start[2]) + ang_units]
            grid_stop_wu = [str(grid_stop[0]) + units, str(grid_stop[1]) + ang_units, str(grid_stop[2]) + ang_units]
            grid_step_wu = [str(grid_step[0]) + units, str(grid_step[1]) + ang_units, str(grid_step[2]) + ang_units]
        else:
            self.logger.error("Error in the type of the grid.")
            return False

        if not variations:
            variations = self._app.available_variations.nominal_w_values_dict

        variation = []
        for el, value in variations.items():
            if self._app.variable_manager.variables[el].sweep:
                variation.append(el + ":=")
                variation.append(value)
        variation.extend(intrinsics)

        export_options = [
            "NAME:ExportOption",
            "IncludePtInOutput:=",
            export_with_sample_points,
            "RefCSName:=",
            reference_coordinate_system,
            "PtInSI:=",
            export_in_si_system,
            "FieldInRefCS:=",
            export_field_in_reference,
        ]

        self.ofieldsreporter.ExportOnGrid(
            file_name,
            grid_start_wu,
            grid_stop_wu,
            grid_step_wu,
            solution,
            variation,
            export_options,
            grid_type,
            grid_center,
            False,
        )
        if os.path.exists(file_name):
            return file_name
        return False  # pragma: no cover

    @pyaedt_function_handler(
        quantity_name="quantity",
        variation_dict="variations",
        filename="output_file",
        obj_list="assignment",
        obj_type="objects_type",
        sample_points_lists="sample_points",
    )
    def export_field_file(
        self,
        quantity,
        solution=None,
        variations=None,
        output_file=None,
        assignment="AllObjects",
        objects_type="Vol",
        intrinsics=None,
        phase=None,
        sample_points_file=None,
        sample_points=None,
        export_with_sample_points=True,
        reference_coordinate_system="Global",
        export_in_si_system=True,
        export_field_in_reference=True,
    ):
        """Use the field calculator to create a field file based on a solution and variation.

        Parameters
        ----------
        quantity : str
            Name of the quantity to export. For example, ``"Temp"``.
        solution : str, optional
            Name of the solution in the format ``"solution: sweep"``.
            The default is ``None``.
        variations : dict, optional
            Dictionary of all variation variables with their values.
            The default is ``None``.
        output_file : str, optional
            Full path and name to save the file to.
            The default is ``None`` which export a file named ``"<setup_name>.fld"`` in working_directory.
        assignment : str, optional
            List of objects to export. The default is ``"AllObjects"``.
        objects_type : str, optional
            Type of objects to export. The default is ``"Vol"``.
            Options are ``"Surf"`` for surface and ``"Vol"`` for
            volume.
        intrinsics : dict, str, optional
            Intrinsic variables required to compute the field before the export.
            These are typically: frequency, time and phase.
            It can be provided either as a dictionary or as a string.
            If it is a dictionary, keys depend on the solution type and can be expressed in lower or camel case as:
            - ``"Freq"`` or ``"Frequency"``
            - ``"Time"``
            - ``"Phase"``
            If it is a string, it can either be ``"Freq"`` or ``"Time"`` depending on the solution type.
            The default is ``None`` in which case the intrinsics value is automatically computed based on the setup.
        phase : str, optional
            Field phase. The default is ``None``.
            This argument is deprecated. Please use ``intrinsics`` and provide the phase as a dictionary key instead.
        sample_points_file : str, optional
            Name of the file with sample points. The default is ``None``.
        sample_points : list, optional
            List of the sample points. The default is ``None``.
        export_with_sample_points : bool, optional
            Whether to include the sample points in the file to export.
            The default is ``True``.
        reference_coordinate_system : str, optional
            Reference coordinate system in the file to export.
            The default is ``"Global"``.
        export_in_si_system : bool, optional
            Whether the provided sample points are defined in the SI system or model units.
            The default is ``True``.
        export_field_in_reference : bool, optional
            Whether to export the field in reference coordinate system.
            The default is ``True``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.EnterQty
        >>> oModule.CopyNamedExprToStack
        >>> oModule.CalcOp
        >>> oModule.EnterQty
        >>> oModule.EnterVol
        >>> oModule.CalculatorWrite
        >>> oModule.ExportToFile

        Examples
        --------

        >>> from ansys.aedt.core import Maxwell3d
        >>> m3d = Maxwell3d()
        >>> # Intrinsics is provided as a string.
        >>> fld_file1 = "test_fld_hfss1.fld"
        >>> hfss_app.post.export_field_file(quantity="Mag_E", output_file=fld_file1, assignment="Box1",
        >>>                                 intrinsics="1GHz", phase="5deg")
        >>> # Intrinsics is provided as dictionary. Phase is automatically assigned to 0deg.
        >>> fld_file2 =  "test_fld_hfss2.fld"
        >>> hfss_app.post.export_field_file(quantity="Mag_E", output_file=fld_file2, assignment="Box1",
        >>>                                intrinsics={"frequency":"1GHz"})
        >>> # Intrinsics is provided as dictionary. Phase is provided.
        >>> hfss_app.post.export_field_file(quantity="Mag_E", output_file=fld_file2, assignment="Box1",
        >>>                                 intrinsics={"frequency":"1GHz", "phase":"30deg"})
        >>> # Intrinsics is not provided. It is computed from the setup arguments.
        >>>  hfss_app.post.export_field_file(quantity="Mag_E", output_file=fld_file2, assignment="Box1",
        >>>                                     )
        """
        intrinsics = self._app._check_intrinsics(intrinsics, phase, solution, return_list=True)
        self.logger.info("Exporting %s field. Be patient", quantity)
        if not solution:
            if not self._app.existing_analysis_sweeps:
                self.logger.error("There are no existing sweeps.")
                return False
            solution = self._app.existing_analysis_sweeps[0]
        if not output_file:
            appendix = ""
            ext = ".fld"
            output_file = os.path.join(self._app.working_directory, solution.replace(" : ", "_") + appendix + ext)
        else:
            output_file = output_file.replace("//", "/").replace("\\", "/")
        self.ofieldsreporter.CalcStack("clear")
        try:
            self.ofieldsreporter.EnterQty(quantity)
        except Exception:
            self.ofieldsreporter.CopyNamedExprToStack(quantity)

        if not variations:
            variations = self._app.available_variations.nominal_w_values_dict

        variation = []
        for el, value in variations.items():
            if self._app.variable_manager.variables[el].sweep:
                variation.append(el + ":=")
                variation.append(value)
        variation.extend(intrinsics)

        if not sample_points_file and not sample_points:
            if objects_type == "Vol":
                self.ofieldsreporter.EnterVol(assignment)
            elif objects_type == "Surf":
                self.ofieldsreporter.EnterSurf(assignment)
            elif objects_type == "Line":
                self.ofieldsreporter.EnterLine(assignment)
            else:
                self.logger.error("No correct choice.")
                return False
            self.ofieldsreporter.CalcOp("Value")
            if objects_type == "Line":
                args = ["Solution:=", solution, "Geometry:=", assignment, "GeometryType:=", objects_type]
            else:
                args = ["Solution:=", solution]
            self.ofieldsreporter.CalculatorWrite(output_file, args, variation)
        elif sample_points_file:
            export_options = [
                "NAME:ExportOption",
                "IncludePtInOutput:=",
                export_with_sample_points,
                "RefCSName:=",
                reference_coordinate_system,
                "PtInSI:=",
                export_in_si_system,
                "FieldInRefCS:=",
                export_field_in_reference,
            ]
            self.ofieldsreporter.ExportToFile(
                output_file,
                sample_points_file,
                solution,
                variation,
                export_options,
            )
        else:
            sample_points_file = os.path.join(self._app.working_directory, "temp_points.pts")
            with open_file(sample_points_file, "w") as f:
                f.write(f"Unit={self.model_units}\n")
                for point in sample_points:
                    f.write(" ".join([str(i) for i in point]) + "\n")
            export_options = [
                "NAME:ExportOption",
                "IncludePtInOutput:=",
                export_with_sample_points,
                "RefCSName:=",
                reference_coordinate_system,
                "PtInSI:=",
                export_in_si_system,
                "FieldInRefCS:=",
                export_field_in_reference,
            ]
            self.ofieldsreporter.ExportToFile(
                output_file,
                sample_points_file,
                solution,
                variation,
                export_options,
            )

        if os.path.exists(output_file):
            return output_file
        return False  # pragma: no cover

    @pyaedt_function_handler(plotname="plot_name", filepath="output_dir", filename="file_name")
    def export_field_plot(self, plot_name, output_dir, file_name="", file_format="aedtplt"):
        """Export a field plot.

        .. note:
           This method works only when the plot is active when it is run.

        Parameters
        ----------
        plot_name : str
            Name of the plot.
        output_dir : str
            Path for saving the file.
        file_name : str, optional
            Name of the file. The default is ``""``, in which case a name is automatically assigned.
        file_format : str, optional
            Name of the file extension. The default is ``"aedtplt"``. Options are ``"case"`` and ``"fldplt"``.

        Returns
        -------
        str or bool
            File path when successful or ``False`` when it fails.

        References
        ----------
        >>> oModule.ExportFieldPlot
        """
        if not file_name:
            file_name = plot_name
        output_dir = os.path.join(output_dir, file_name + "." + file_format)
        try:
            self.ofieldsreporter.ExportFieldPlot(plot_name, False, output_dir)
            if settings.remote_rpc_session_temp_folder:  # pragma: no cover
                local_path = os.path.join(settings.remote_rpc_session_temp_folder, file_name + "." + file_format)
                output_dir = check_and_download_file(local_path, output_dir)
            return output_dir
        except Exception:  # pragma: no cover
            self.logger.error(f"{file_format} file format is not supported for this plot.")
            return False

    @pyaedt_function_handler()
    def change_field_plot_scale(
        self, plot_name, minimum_value, maximum_value, is_log=False, is_db=False, scale_levels=None
    ):
        """Change Field Plot Scale.

        .. deprecated:: 0.10.1
           Use :class:`FieldPlot.folder_settings` methods instead.

        Parameters
        ----------
        plot_name : str
            Name of the Plot Folder to update.
        minimum_value : str, float
            Minimum value of the scale.
        maximum_value : str, float
            Maximum value of the scale.
        is_log : bool, optional
            Set to ``True`` if Log Scale is setup.
        is_db : bool, optional
            Set to ``True`` if dB Scale is setup.
        scale_levels : int, optional
            Set number of color levels. The default is ``None``, in which case the
            setting is not changed.

        Returns
        -------
        bool
            ``True`` if successful.

        References
        ----------
        >>> oModule.SetPlotFolderSettings
        """
        args = ["NAME:FieldsPlotSettings", "Real Time mode:=", True]
        args += [
            [
                "NAME:ColorMaPSettings",
                "ColorMapType:=",
                "Spectrum",
                "SpectrumType:=",
                "Rainbow",
                "UniformColor:=",
                [127, 255, 255],
                "RampColor:=",
                [255, 127, 127],
            ]
        ]
        scale_args = [
            "NAME:Scale3DSettings",
            "minvalue:=",
            minimum_value,
            "maxvalue:=",
            maximum_value,
            "log:=",
            is_log,
            "dB:=",
            is_db,
            "ScaleType:=",
            1,
        ]
        if scale_levels is not None:
            scale_args += ["m_nLevels:=", scale_levels]
        args += [scale_args]
        self.ofieldsreporter.SetPlotFolderSettings(plot_name, args)
        return True

    @pyaedt_function_handler(objlist="assignment", quantityName="quantity", listtype="list_type", setup_name="setup")
    def _create_fieldplot(
        self,
        assignment,
        quantity,
        setup,
        intrinsics,
        list_type,
        plot_name=None,
        filter_boxes=None,
        field_type=None,
        create_plot=True,
    ):
        intrinsics = self._app._check_intrinsics(intrinsics, None, setup)
        if not list_type.startswith("Layer") and self._app.design_type != "HFSS 3D Layout Design":
            assignment = self._app.modeler.convert_to_selections(assignment, True)
        if not setup:
            setup = self._app.existing_analysis_sweeps[0]

        self._app.desktop_class.close_windows()
        try:
            self._app.modeler.fit_all()
        except Exception:
            self.logger.debug("Something went wrong with `fit_all` while creating field plot.")  # pragma: no cover
        self._desktop.TileWindows(0)
        self._app.desktop_class.active_design(self._oproject, self._app.design_name)

        char_set = string.ascii_uppercase + string.digits
        if not plot_name:
            plot_name = quantity + "_" + "".join(random.sample(char_set, 6))
        filter_boxes = [] if filter_boxes is None else filter_boxes
        if list_type == "CutPlane":
            plot = FieldPlot(self, cutplanes=assignment, solution=setup, quantity=quantity, intrinsics=intrinsics)
        elif list_type == "FacesList":
            plot = FieldPlot(self, surfaces=assignment, solution=setup, quantity=quantity, intrinsics=intrinsics)
        elif list_type == "ObjList":
            plot = FieldPlot(self, objects=assignment, solution=setup, quantity=quantity, intrinsics=intrinsics)
        elif list_type == "Line":
            plot = FieldPlot(self, lines=assignment, solution=setup, quantity=quantity, intrinsics=intrinsics)
        elif list_type.startswith("Layer"):
            plot = FieldPlot(
                self,
                solution=setup,
                quantity=quantity,
                intrinsics=intrinsics,
                layer_nets=assignment,
                layer_plot_type=list_type,
            )
        if self._app.design_type == "Q3D Extractor":  # pragma: no cover
            plot.field_type = field_type
        plot.name = plot_name
        plot.plot_folder = plot_name
        plot.filter_boxes = filter_boxes
        if create_plot:
            plt = plot.create()
            if plt:
                return plot
            else:
                return False
        return plot

    @pyaedt_function_handler(quantityName="quantity", setup_name="setup")
    def _create_fieldplot_line_traces(
        self,
        seeding_faces_ids,
        in_volume_tracing_ids,
        surface_tracing_ids,
        quantity,
        setup,
        intrinsics,
        plot_name=None,
        field_type="",
    ):
        if not setup:
            setup = self._app.existing_analysis_sweeps[0]
        if not intrinsics:
            for i in self._app.setups:
                if i.name == setup.split(" : ")[0]:
                    intrinsics = i.default_intrinsics
        self._app.desktop_class.close_windows()
        try:
            self._app.modeler.fit_all()
        except Exception:
            self.logger.debug(
                "Something went wrong with `fit_all` while creating field plot with line traces."
            )  # pragma: no cover
        self._desktop.TileWindows(0)
        self._app.desktop_class.active_design(self._oproject, self._app.design_name)

        char_set = string.ascii_uppercase + string.digits
        if not plot_name:
            plot_name = quantity + "_" + "".join(random.sample(char_set, 6))
        plot = FieldPlot(
            self,
            objects=in_volume_tracing_ids,
            surfaces=surface_tracing_ids,
            solution=setup,
            quantity=quantity,
            intrinsics=intrinsics,
            seeding_faces=seeding_faces_ids,
        )
        if field_type:
            plot.field_type = field_type
        plot.name = plot_name
        plot.plot_folder = plot_name

        plt = plot.create()
        if "Maxwell" in self._app.design_type and self.post_solution_type == "Transient":
            self.ofieldsreporter.SetPlotsViewSolutionContext([plot_name], setup, "Time:" + intrinsics["Time"])
        if plt:
            self.field_plots[plot_name] = plot
            return plot
        else:
            return False

    @pyaedt_function_handler(objlist="assignment", quantityName="quantity", setup_name="setup")
    def create_fieldplot_line(
        self, assignment, quantity, setup=None, intrinsics=None, plot_name=None, field_type="DC R/L Fields"
    ):
        """Create a field plot of the line.

        Parameters
        ----------
        assignment : list
            List of polylines to plot.
        quantity : str
            Name of the quantity to plot.
        setup : str, optional
            Name of the setup. The default is ``None``, in which case the ``nominal_adaptive``
            setup is used. Be sure to build a setup string in the form of
            ``"SetupName : SetupSweep"``, where ``SetupSweep`` is the sweep name to
            use in the export or ``LastAdaptive``.
        intrinsics : dict, str, optional
            Intrinsic variables required to compute the field before the export.
            These are typically: frequency, time and phase.
            It can be provided either as a dictionary or as a string.
            If it is a dictionary, keys depend on the solution type and can be expressed in lower or camel case as:
            - ``"Freq"`` or ``"Frequency"``.
            - ``"Time"``.
            - ``"Phase"``.
            If it is a string, it can either be ``"Freq"`` or ``"Time"`` depending on the solution type.
            The default is ``None`` in which case the intrinsics value is automatically computed based on the setup.
        plot_name : str, optional
            Name of the field plot to create.
        field_type : str, optional
            Field type to plot. Valid only for Q3D Field plots.

        Returns
        -------
        type
            Plot object.

        References
        ----------
        >>> oModule.CreateFieldPlot

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> aedtapp = Hfss()
        >>> # Intrinsics is provided as a dictionary.
        >>> intrinsics = {"Freq": "5GHz", "Phase": "180deg"}
        >>> min_value = aedtapp.post.get_scalar_field_value(quantity_name, "Minimum", setup_name, intrinsics=intrinsics)
        >>> plot1 = aedtapp.post.create_fieldplot_line("Polyline1", quantity_name, setup_name, intrinsics=intrinsics)
        >>> # Intrinsics is provided as a string. Phase is automatically assigned to 0deg.
        >>> min_value = aedtapp.post.get_scalar_field_value(quantity_name, "Minimum", setup_name, intrinsics="5GHz")
        >>> plot1 = aedtapp.post.create_fieldplot_line("Polyline1", quantity_name, setup_name, intrinsics="5GHz")
        >>> # Intrinsics is provided as a dictionary. Phase is automatically assigned to 0deg.
        >>> intrinsics = {"Freq": "5GHz"}
        >>> min_value = aedtapp.post.get_scalar_field_value(quantity_name, "Minimum", setup_name, intrinsics=intrinsics)
        >>> plot1 = aedtapp.post.create_fieldplot_line("Polyline1", quantity_name, setup_name, intrinsics=intrinsics)
        >>> # Intrinsics is not provided and is computed from the setup.
        >>> min_value = aedtapp.post.get_scalar_field_value(quantity_name, "Minimum", setup_name)
        >>> plot1 = aedtapp.post.create_fieldplot_line("Polyline1", quantity_name, setup_name)
        """
        intrinsics = self._app._check_intrinsics(intrinsics, setup=setup)
        if plot_name and plot_name in list(self.field_plots.keys()):
            self.logger.info(f"Plot {plot_name} exists. returning the object.")
            return self.field_plots[plot_name]
        return self._create_fieldplot(assignment, quantity, setup, intrinsics, "Line", plot_name, field_type=field_type)

    @pyaedt_function_handler(IntrinsincDict="intrinsics", setup_name="setup")
    def create_fieldplot_line_traces(
        self,
        seeding_faces,
        in_volume_tracing_objs=None,
        surface_tracing_objs=None,
        setup=None,
        intrinsics=None,
        plot_name=None,
        field_type="DC R/L Fields",
    ):
        """
        Create a field plot of the line.

        Parameters
        ----------
        seeding_faces : list
            List of seeding faces.
        in_volume_tracing_objs : list
            List of the in-volume tracing objects.
        surface_tracing_objs : list
            List of the surface tracing objects.
        setup : str, optional
            Name of the setup in the format ``"setupName : sweepName"``. The default
            is ``None``.
        intrinsics : dict, str, optional
            Intrinsic variables required to compute the field before the export.
            These are typically: frequency, time and phase.
            It can be provided either as a dictionary or as a string.
            If it is a dictionary, keys depend on the solution type and can be expressed in lower or camel case as:
            - ``"Freq"`` or ``"Frequency"``.
            - ``"Time"``.
            - ``"Phase"``.
            If it is a string, it can either be ``"Freq"`` or ``"Time"`` depending on the solution type.
            The default is ``None`` in which case the intrinsics value is automatically computed based on the setup.
        plot_name : str, optional
            Name of the field plot to create. The default is ``None``.
        field_type : str, optional
            Field type to plot. Valid only for Q3D Field plots.

        Returns
        -------
        type
            Plot object.

        References
        ----------
        >>> oModule.CreateFieldPlot

        Examples
        --------
        >>> from ansys.aedt.core import Maxwell2d
        >>> aedtapp = Maxwell2d()
        >>> # Intrinsics is provided as a dictionary.
        >>> intrinsics = {"Freq": "5GHz", "Phase": "180deg"}
        >>> min_value = aedtapp.post.get_scalar_field_value(quantity_name, "Minimum", setup_name, intrinsics=intrinsics)
        >>> plot1 = aedtapp.post.create_fieldplot_line_traces(seeding_faces=["Ground", "Electrode", "Region"],
        >>>                                                   in_volume_tracing_objs="Region",
        >>>                                                   plot_name="LineTracesTest",
        >>>                                                   intrinsics=intrinsics)
        >>> # Intrinsics is provided as a string. Phase is automatically assigned to 0deg.
        >>> min_value = aedtapp.post.get_scalar_field_value(quantity_name, "Minimum", setup_name, intrinsics="5GHz")
        >>> plot1 = aedtapp.post.create_fieldplot_line_traces(seeding_faces=["Ground", "Electrode", "Region"],
        >>>                                                   in_volume_tracing_objs="Region",
        >>>                                                   plot_name="LineTracesTest",
        >>>                                                   intrinsics="200Hz")
        """
        intrinsics = self._app._check_intrinsics(intrinsics, setup=setup)
        if self._app.solution_type != "Electrostatic":
            self.logger.error("Field line traces is valid only for electrostatic solution")
            return False
        if plot_name and plot_name in list(self.field_plots.keys()):
            self.logger.info(f"Plot {plot_name} exists. returning the object.")
            return self.field_plots[plot_name]
        if not isinstance(seeding_faces, list):
            seeding_faces = [seeding_faces]
        seeding_faces_ids = []
        for face in seeding_faces:
            if self._app.modeler[face]:
                seeding_faces_ids.append(self._app.modeler[face].id)
            else:
                self.logger.error(f"Object {face} doesn't exist in current design")
                return False
        in_volume_tracing_ids = []
        if not in_volume_tracing_objs:
            in_volume_tracing_ids.append(0)
        elif not isinstance(in_volume_tracing_objs, list):
            in_volume_tracing_objs = [in_volume_tracing_objs]
            for obj in in_volume_tracing_objs:
                if self._app.modeler[obj]:
                    in_volume_tracing_ids.append(self._app.modeler[obj].id)
                else:
                    self.logger.error(f"Object {obj} doesn't exist in current design")
                    return False
        elif isinstance(in_volume_tracing_objs, list):
            for obj in in_volume_tracing_objs:
                if not self._app.modeler[obj]:
                    self.logger.error(f"Object {obj} doesn't exist in current design")
                    return False
        surface_tracing_ids = []
        if not surface_tracing_objs:
            surface_tracing_ids.append(0)
        elif not isinstance(surface_tracing_objs, list):
            surface_tracing_objs = [surface_tracing_objs]
            for obj in surface_tracing_objs:
                if self._app.modeler[obj]:
                    surface_tracing_ids.append(self._app.modeler[obj].id)
                else:
                    self.logger.error(f"Object {obj} doesn't exist in current design")
                    return False
        elif isinstance(surface_tracing_objs, list):
            for obj in surface_tracing_objs:
                if not self._app.modeler[obj]:
                    self.logger.error(f"Object {obj} doesn't exist in current design")
                    return False
        seeding_faces_ids.insert(0, len(seeding_faces_ids))
        if in_volume_tracing_ids != [0]:
            in_volume_tracing_ids.insert(0, len(in_volume_tracing_ids))
        if surface_tracing_ids != [0]:
            surface_tracing_ids.insert(0, len(surface_tracing_ids))
        return self._create_fieldplot_line_traces(
            seeding_faces_ids,
            in_volume_tracing_ids,
            surface_tracing_ids,
            "FieldLineTrace",
            setup,
            intrinsics,
            plot_name,
            field_type=field_type,
        )

    @pyaedt_function_handler()
    def _get_all_3dl_layers_nets(self, setup):
        try:
            get_ids = self._odesign.GetGeometryIdsForAllNetLayerCombinations(setup)
        except Exception:  # pragma no cover
            get_ids = []
        k = 0
        get_ids_dict = {}
        key = ""
        list_to_add = []
        while k < len(get_ids):
            if get_ids[k].startswith("PlotGeomInfo"):
                if key:
                    get_ids_dict[key] = list_to_add
                key = get_ids[k].replace("PlotGeomInfo for ", "").replace(" (net/layer combination):", "")
                list_to_add = []
            else:
                try:
                    list_to_add.append(int(get_ids[k]))
                except ValueError:
                    pass
            k = k + 1
        return get_ids_dict

    @pyaedt_function_handler()
    def _get_3dl_layers_nets(self, layers, nets, setup, include_dielectrics):
        lst_faces = []
        new_layers = []
        ids_dict = self._get_all_3dl_layers_nets(setup)
        if not layers:
            if include_dielectrics:
                new_layers.extend([f"{i}" for i in self._app.modeler.edb.stackup.dielectric_layers.keys()])
            for layer in self._app.modeler.edb.stackup.signal_layers.keys():
                if not nets:
                    nets = list(self._app.modeler.edb.nets.nets.keys())
                for el in nets:
                    if f"{el}/{layer}" in ids_dict:
                        lst_faces.extend(ids_dict[f"{el}/{layer}"])
        else:
            for layer in layers:
                if layer in self._app.modeler.edb.stackup.dielectric_layers and include_dielectrics:
                    new_layers.append(f"{layer}")
                elif layer in self._app.modeler.edb.stackup.signal_layers:
                    if not nets:
                        nets = list(self._app.modeler.edb.nets.nets.keys())
                    for el in nets:
                        if f"{el}/{layer}" in ids_dict:
                            lst_faces.extend(ids_dict[f"{el}/{layer}"])
        return lst_faces, new_layers

    @pyaedt_function_handler()
    def _get_3d_layers_nets(self, layers, nets):
        dielectrics = []
        new_layers = []
        for k, v in self._app.modeler.user_defined_components.items():
            if v.layout_component:
                if not layers:
                    layers = [i for i in v.layout_component.edb_object.stackup.stackup_layers.keys()]
                if not nets:
                    nets = [""] + [i for i in v.layout_component.edb_object.nets.nets.keys()]
                for layer in layers:
                    if layer in v.layout_component.edb_object.stackup.signal_layers:
                        new_layers.append([layer] + nets)
                    elif layer in v.layout_component.edb_object.stackup.dielectric_layers:
                        dielectrics.append(f"{k}:{layer}")
        return dielectrics, new_layers

    @pyaedt_function_handler()
    def create_fieldplot_layers(
        self, layers, quantity, setup=None, nets=None, plot_on_surface=True, intrinsics=None, name=None
    ):
        # type: (list, str, str, list, bool, dict, str) -> FieldPlot
        """Create a field plot of stacked layer plot.

        This plot is valid from AEDT 2023 R2 and later in HFSS 3D Layout. Nets can be used as a filter.
        Dielectrics will be included into the plot.
        It works when a layout components in 3d modeler is used.

        Parameters
        ----------
        layers : list
            List of layers to plot. For example:
            ``["Layer1","Layer2"]``. If empty list is provided
            all layers are considered.
        quantity : str
            Name of the quantity to plot.
        setup : str, optional
            Name of the setup. The default is ``None``, in which case the ``nominal_adaptive``
            setup is used. Make sure to build a setup string in the form of
            ``"SetupName : SetupSweep"``, where ``SetupSweep`` is the sweep name to
            use in the export or ``LastAdaptive``.
        nets : list, optional
            List of nets to filter the field plot. Optional.
        plot_on_surface : bool, optional
            Whether if the plot has to be on surfaces or inside the objects.
            It is applicable only to layout components. Default is ``True``.
        intrinsics : dict, str, optional
            Intrinsic variables required to compute the field before the export.
            These are typically: frequency, time and phase.
            It can be provided either as a dictionary or as a string.
            If it is a dictionary, keys depend on the solution type and can be expressed in lower or camel case as:

            - ``"Freq"`` or ``"Frequency"``.
            - ``"Time"``.
            - ``"Phase"``.

            If it is a string, it can either be ``"Freq"`` or ``"Time"`` depending on the solution type.
            The default is ``None`` in which case the intrinsics value is automatically computed based on the setup.
        name : str, optional
            Name of the field plot to create.

        Returns
        -------
        :class:``ansys.aedt.core.modules.solutions.FieldPlot`` or bool
            Plot object.

        References
        ----------
        >>> oModule.CreateFieldPlot
        """
        intrinsics = self._app._check_intrinsics(intrinsics, setup=setup)
        if not setup:
            setup = self._app.existing_analysis_sweeps[0]
        if nets is None:
            nets = []
        if not (
            "APhi" in self.post_solution_type and settings.aedt_version >= "2023.2"
        ) and not self._app.design_type in ["HFSS", "HFSS 3D Layout Design"]:
            self.logger.error("This method requires AEDT 2023 R2 and Maxwell 3D Transient APhi Formulation.")
            return False
        if name and name in list(self.field_plots.keys()):
            self.logger.info(f"Plot {name} exists. returning the object.")
            return self.field_plots[name]

        if self._app.design_type in ["HFSS 3D Layout Design"]:
            lst_faces, new_layers = self._get_3dl_layers_nets(layers, nets, setup, include_dielectrics=True)
            if new_layers:
                plt = self._create_fieldplot(
                    new_layers, quantity, setup, intrinsics, "ObjList", name, create_plot=False
                )
                plt.surfaces = lst_faces
                out = plt.create()
                if out:
                    return plt
                return False
            else:
                return self._create_fieldplot(lst_faces, quantity, setup, intrinsics, "FacesList", name)
        else:
            dielectrics, new_layers = self._get_3d_layers_nets(layers, nets)
            if plot_on_surface:
                plot_type = "LayerNetsExtFace"
            else:
                plot_type = "LayerNets"
            if new_layers:
                plt = self._create_fieldplot(
                    new_layers, quantity, setup, intrinsics, plot_type, name, create_plot=False
                )
                if dielectrics:
                    plt.volumes = dielectrics
                out = plt.create()
                if out:
                    return plt
            elif dielectrics:
                return self._create_fieldplot(dielectrics, quantity, setup, intrinsics, "ObjList", name)
            return False

    @pyaedt_function_handler()
    def create_fieldplot_nets(
        self, nets, quantity, setup=None, layers=None, plot_on_surface=True, intrinsics=None, name=None
    ):
        # type: (list, str, str, list, bool, dict, str) -> FieldPlot
        """Create a field plot of stacked layer plot based on a net selections.

        Layers can be used as a filter.
        Dielectrics will be excluded from the plot.
        This plot is valid from AEDT 2023 R2 and later in HFSS 3D Layout.
        It works when a layout components in 3d modeler is used.

        Parameters
        ----------
        nets : list, optional
            List of nets to filter the field plot.
        quantity : str
            Name of the quantity to plot.
        setup : str, optional
            Name of the setup. The default is ``None``, in which case the ``nominal_adaptive``
            setup is used. Make sure to build a setup string in the form of
            ``"SetupName : SetupSweep"``, where ``SetupSweep`` is the sweep name to
            use in the export or ``LastAdaptive``.
        layers : list, optional
            List of layers to plot. For example:
            ``["Layer1","Layer2"]``. If empty list is provided
            all layers are considered.
        intrinsics : dict, str, optional
            Intrinsic variables required to compute the field before the export.
            These are typically: frequency, time and phase.
            It can be provided either as a dictionary or as a string.
            If it is a dictionary, keys depend on the solution type and can be expressed in lower or camel case as:

            - ``"Freq"`` or ``"Frequency"``.
            - ``"Time"``.
            - ``"Phase"``.

            If it is a string, it can either be ``"Freq"`` or ``"Time"`` depending on the solution type.
            The default is ``None`` in which case the intrinsics value is automatically computed based on the setup.
        plot_on_surface : bool, optional
            Whether if the plot has to be on surfaces or inside the objects.
            It is applicable only to layout components. Default is ``True``.
        name : str, optional
            Name of the field plot to create.

        Returns
        -------
        :class:``ansys.aedt.core.modules.solutions.FieldPlot`` or bool
            Plot object.

        References
        ----------
        >>> oModule.CreateFieldPlot
        """
        intrinsics = self._app._check_intrinsics(intrinsics, setup=setup)
        if not setup:
            setup = self._app.existing_analysis_sweeps[0]
        if nets is None:
            nets = []
        if not (
            "APhi" in self.post_solution_type and settings.aedt_version >= "2023.2"
        ) and not self._app.design_type in ["HFSS", "HFSS 3D Layout Design"]:
            self.logger.error("This method requires AEDT 2023 R2 and Maxwell 3D Transient APhi Formulation.")
            return False
        if name and name in list(self.field_plots.keys()):
            self.logger.info(f"Plot {name} exists. returning the object.")
            return self.field_plots[name]

        if self._app.design_type in ["HFSS 3D Layout Design"]:
            lst_faces, new_layers = self._get_3dl_layers_nets(layers, nets, setup, include_dielectrics=False)
            return self._create_fieldplot(lst_faces, quantity, setup, intrinsics, "FacesList", name)
        else:
            _, new_layers = self._get_3d_layers_nets(layers, nets)
            if plot_on_surface:
                plot_type = "LayerNetsExtFace"
            else:
                plot_type = "LayerNets"
            return self._create_fieldplot(new_layers, quantity, setup, intrinsics, plot_type, name)

    @pyaedt_function_handler(quantity_name="quantity", setup_name="setup")
    def create_fieldplot_layers_nets(
        self, layers_nets, quantity, setup=None, intrinsics=None, plot_on_surface=True, plot_name=None
    ):
        # type: (list, str, str, dict, bool, str) -> FieldPlot
        """Create a field plot of stacked layer plot on specified matrix of layers and nets.

        This plot is valid from AEDT 2023 R2 and later in HFSS 3D Layout
        and any modeler where a layout component is used.

        Parameters
        ----------
        layers_nets : list
            List of layers and nets to plot. For example:
            ``[["Layer1", "GND", "PWR"], ["Layer2", "VCC"], ...]``. If ``"no-layer"`` is provided as first argument,
            all layers are considered. If ``"no-net"`` is provided or the list contains only layer name, all the
            nets are automatically considered.
        quantity : str
            Name of the quantity to plot.
        setup : str, optional
            Name of the setup. The default is ``None``, in which case the ``nominal_adaptive``
            setup is used. Make sure to build a setup string in the form of
            ``"SetupName : SetupSweep"``, where ``SetupSweep`` is the sweep name to
            use in the export or ``LastAdaptive``.
        intrinsics : dict, str, optional
            Intrinsic variables required to compute the field before the export.
            These are typically: frequency, time and phase.
            It can be provided either as a dictionary or as a string.
            If it is a dictionary, keys depend on the solution type and can be expressed in lower or camel case as:

            - ``"Freq"`` or ``"Frequency"``.
            - ``"Time"``.
            - ``"Phase"``.

            If it is a string, it can either be ``"Freq"`` or ``"Time"`` depending on the solution type.
            The default is ``None`` in which case the intrinsics value is automatically computed based on the setup.
        plot_on_surface : bool, optional
            Whether if the plot has to be on surfaces or inside the objects.
            It is applicable only to layout components. Default is ``True``.
        plot_name : str, optional
            Name of the field plot to create.

        Returns
        -------
        :class:``ansys.aedt.core.modules.solutions.FieldPlot``
            Plot object.

        References
        ----------
        >>> oModule.CreateFieldPlot
        """
        intrinsics = self._app._check_intrinsics(intrinsics, setup=setup)
        if not (
            "APhi" in self.post_solution_type and settings.aedt_version >= "2023.2"
        ) and not self._app.design_type in ["HFSS", "HFSS 3D Layout Design"]:
            self.logger.error("This method requires AEDT 2023 R2 and Maxwell 3D Transient APhi Formulation.")
            return False
        if intrinsics is None:
            intrinsics = {}
        if plot_name and plot_name in list(self.field_plots.keys()):
            self.logger.info(f"Plot {plot_name} exists. returning the object.")
            return self.field_plots[plot_name]
        if self._app.design_type == "HFSS 3D Layout Design":
            if not setup:
                setup = self._app.existing_analysis_sweeps[0]
            lst = []
            if len(layers_nets) == 0:

                dicts_in = self._get_all_3dl_layers_nets(setup)
                for _, v in dicts_in.items():
                    lst.extend(v)
            for layer in layers_nets:
                if len(layer) == 1:
                    dicts_in = self._get_all_3dl_layers_nets(setup)
                    for v, i in dicts_in.items():
                        if v.split("/")[1] == layer[0] or v.split("/")[0] == layer[0]:
                            lst.extend(i)
                for el in layer[1:]:
                    el = "<no-net>" if el == "no-net" else el
                    try:
                        get_ids = self._odesign.GetGeometryIdsForNetLayerCombination(el, layer[0], setup)
                    except Exception:  # pragma no cover
                        get_ids = []
                    if isinstance(get_ids, (tuple, list)) and len(get_ids) > 2:
                        lst.extend([int(i) for i in get_ids[2:]])
            return self._create_fieldplot(lst, quantity, setup, intrinsics, "FacesList", plot_name)
        else:
            new_list = []
            for layer in layers_nets:
                if "no-layer" in layer[0]:
                    for v in self._app.modeler.user_defined_components.values():
                        new_list.extend(
                            [[i] + layer[1:] for i in v.layout_component.edb_object.stackup.signal_layers.keys()]
                        )
                else:
                    new_list.append(layer)
            layers_nets = new_list
            for layer in layers_nets:
                if len(layer) == 1 or "no-net" in layer[1]:
                    for v in self._app.modeler.user_defined_components.values():
                        if layer[0] in v.layout_component.edb_object.stackup.stackup_layers:
                            layer.extend(list(v.layout_component.edb_object.nets.nets.keys()))
            if plot_on_surface:
                plot_type = "LayerNetsExtFace"
            else:
                plot_type = "LayerNets"
            return self._create_fieldplot(layers_nets, quantity, setup, intrinsics, plot_type, plot_name)

    @pyaedt_function_handler(
        objlist="assignment", quantityName="quantity", IntrinsincDict="intrinsics", setup_name="setup"
    )
    def create_fieldplot_surface(
        self, assignment, quantity, setup=None, intrinsics=None, plot_name=None, field_type="DC R/L Fields"
    ):
        """Create a field plot of surfaces.

        Parameters
        ----------
        assignment : list
            List of surfaces to plot.
        quantity : str
            Name of the quantity to plot.
        setup : str, optional
            Name of the setup. The default is ``None``, in which case the ``nominal_adaptive``
            setup is used. Be sure to build a setup string in the form of
            ``"SetupName : SetupSweep"``, where ``SetupSweep`` is the sweep name to
            use in the export or ``LastAdaptive``.
        intrinsics : dict, str, optional
            Intrinsic variables required to compute the field before the export.
            These are typically: frequency, time and phase.
            It can be provided either as a dictionary or as a string.
            If it is a dictionary, keys depend on the solution type and can be expressed in lower or camel case as:
            - ``"Freq"`` or ``"Frequency"``.
            - ``"Time"``.
            - ``"Phase"``.
            If it is a string, it can either be ``"Freq"`` or ``"Time"`` depending on the solution type.
            The default is ``None`` in which case the intrinsics value is automatically computed based on the setup.
        plot_name : str, optional
            Name of the field plot to create.
        field_type : str, optional
            Field type to plot. Valid only for Q3D Field plots.

        Returns
        -------
        :class:``ansys.aedt.core.modules.solutions.FieldPlot``
            Plot object.

        References
        ----------
        >>> oModule.CreateFieldPlot
        """
        if plot_name and plot_name in list(self.field_plots.keys()):
            self.logger.info(f"Plot {plot_name} exists. returning the object.")
            return self.field_plots[plot_name]
        if not isinstance(assignment, (list, tuple)):
            assignment = [assignment]
        new_obj_list = []
        for obj in assignment:
            if isinstance(obj, (int, FacePrimitive)):
                new_obj_list.append(obj)
            elif self._app.modeler[obj]:
                new_obj_list.extend([face for face in self._app.modeler[obj].faces if face.id not in new_obj_list])
        return self._create_fieldplot(
            new_obj_list, quantity, setup, intrinsics, "FacesList", plot_name, field_type=field_type
        )

    @pyaedt_function_handler(
        objlist="assignment", quantityName="quantity", IntrinsincDict="intrinsics", setup_name="setup"
    )
    def create_fieldplot_cutplane(
        self,
        assignment,
        quantity,
        setup=None,
        intrinsics=None,
        plot_name=None,
        filter_objects=None,
        field_type="DC R/L Fields",
    ):
        """Create a field plot of cut planes.

        Parameters
        ----------
        assignment : list
            List of cut planes to plot.
        quantity : str
            Name of the quantity to plot.
        setup : str, optional
            Name of the setup. The default is ``None``, in which case the ``nominal_adaptive`` setup
            is used. Be sure to build a setup string in the form of ``"SetupName : SetupSweep"``,
            where ``SetupSweep`` is the sweep name to use in the export or ``LastAdaptive``.
        intrinsics : dict, str, optional
            Intrinsic variables required to compute the field before the export.
            These are typically: frequency, time and phase.
            It can be provided either as a dictionary or as a string.
            If it is a dictionary, keys depend on the solution type and can be expressed in lower or camel case as:

            - ``"Freq"`` or ``"Frequency"``.
            - ``"Time"``.
            - ``"Phase"``.

            If it is a string, it can either be ``"Freq"`` or ``"Time"`` depending on the solution type.
            The default is ``None`` in which case the intrinsics value is automatically computed based on the setup.
        plot_name : str, optional
            Name of the field plot to create.
        filter_objects : list, optional
            Objects list on which filter the plot.
            The default value is ``None``, in which case an empty list is passed.
        field_type : str, optional
            Field type to plot. This parameter is valid only for Q3D field plots.

        Returns
        -------
        :class:``ansys.aedt.core.modules.solutions.FieldPlot``
            Plot object.

        References
        ----------
        >>> oModule.CreateFieldPlot

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> aedtapp = Hfss()
        >>> # Intrinsics is provided as a dictionary.
        >>> intrinsics = {"Freq": "5GHz", "Phase": "180deg"}
        >>> min_value = aedtapp.post.get_scalar_field_value(quantity_name, "Minimum", setup_name, intrinsics=intrinsics)
        >>> plot1 = aedtapp.post.create_fieldplot_cutplane(cutlist, quantity_name, setup_name, intrinsics=intrinsics)
        >>> # Intrinsics is provided as a string. Phase is automatically assigned to 0deg.
        >>> min_value = aedtapp.post.get_scalar_field_value(quantity_name, "Minimum", setup_name, intrinsics="5GHz")
        >>> plot1 = aedtapp.post.create_fieldplot_cutplane(cutlist, quantity_name, setup_name, intrinsics="5GHz")
        >>> # Intrinsics is provided as a dictionary. Phase is automatically assigned to 0deg.
        >>> intrinsics = {"Freq": "5GHz"}
        >>> min_value = aedtapp.post.get_scalar_field_value(quantity_name, "Minimum", setup_name, intrinsics=intrinsics)
        >>> plot1 = aedtapp.post.create_fieldplot_cutplane(cutlist, quantity_name, setup_name, intrinsics=intrinsics)
        >>> # Intrinsics is not provided and is computed from the setup.
        >>> min_value = aedtapp.post.get_scalar_field_value(quantity_name, "Minimum", setup_name)
        >>> plot1 = aedtapp.post.create_fieldplot_cutplane(cutlist, quantity_name, setup_name)
        """
        if intrinsics is None:
            intrinsics = {}
        if plot_name and plot_name in list(self.field_plots.keys()):
            self.logger.info(f"Plot {plot_name} exists. returning the object.")
            return self.field_plots[plot_name]
        if filter_objects:
            filter_objects = self._app.modeler.convert_to_selections(filter_objects, True)
        return self._create_fieldplot(
            assignment,
            quantity,
            setup,
            intrinsics,
            "CutPlane",
            plot_name,
            filter_boxes=filter_objects,
            field_type=field_type,
        )

    @pyaedt_function_handler(
        objlist="assignment", quantityName="quantity", IntrinsincDict="intrinsics", setup_name="setup"
    )
    def create_fieldplot_volume(
        self, assignment, quantity, setup=None, intrinsics=None, plot_name=None, field_type="DC R/L Fields"
    ):
        """Create a field plot of volumes.

        Parameters
        ----------
        assignment : list
            List of volumes to plot.
        quantity :
            Name of the quantity to plot.
        setup : str, optional
            Name of the setup. The default is ``None``, in which case the ``nominal_adaptive``
            setup is used. Be sure to build a setup string in the form of
            ``"SetupName : SetupSweep"``, where ``SetupSweep`` is the sweep name to
            use in the export or ``LastAdaptive``.
        intrinsics : dict, str, optional
            Intrinsic variables required to compute the field before the export.
            These are typically: frequency, time and phase.
            It can be provided either as a dictionary or as a string.
            If it is a dictionary, keys depend on the solution type and can be expressed in lower or camel case as:
            - ``"Freq"`` or ``"Frequency"``.
            - ``"Time"``.
            - ``"Phase"``.
            If it is a string, it can either be ``"Freq"`` or ``"Time"`` depending on the solution type.
            The default is ``None`` in which case the intrinsics value is automatically computed based on the setup.
        plot_name : str, optional
            Name of the field plot to create.

        Returns
        -------
        :class:``ansys.aedt.core.modules.solutions.FieldPlot``
            Plot object.

        References
        ----------
        >>> oModule.CreateFieldPlot
        """
        assignment = self._app.modeler.convert_to_selections(assignment, True)

        list_type = "ObjList"
        obj_list = []
        for element in assignment:
            if element not in list(self._app.modeler.objects_by_name.keys()):
                self.logger.error(f"{element} does not exist in current design")
                return False
            elif (
                self._app.modeler.objects_by_name[element].is_conductor
                and not self._app.modeler.objects_by_name[element].solve_inside
            ):
                self.logger.warning(f"Solve inside is unchecked for {element} object. Creating a surface plot instead.")
                list_type = "FacesList"
                obj_list.extend([face for face in self._app.modeler[element].faces if face.id not in obj_list])
            else:
                obj_list.append(element)
        intrinsics = self._app._check_intrinsics(intrinsics, setup=setup)

        if plot_name and plot_name in list(self.field_plots.keys()):
            self.logger.info(f"Plot {plot_name} exists. returning the object.")
            return self.field_plots[plot_name]
        return self._create_fieldplot(
            obj_list, quantity, setup, intrinsics, list_type, plot_name, field_type=field_type
        )

    @pyaedt_function_handler(fileName="file_name", plotName="plot_name", foldername="folder_name")
    def export_field_jpg(
        self,
        file_name,
        plot_name,
        folder_name,
        orientation="isometric",
        width=1920,
        height=1080,
        display_wireframe=True,
        selections=None,
        show_axis=True,
        show_grid=True,
        show_ruler=True,
        show_region="Default",
    ):
        """Export a field plot and coordinate system to a JPG file.

        Parameters
        ----------
        file_name : str
            Full path and name to save the JPG file to.
        plot_name : str
            Name of the plot.
        folder_name : str
            Name of the folder plot.
        orientation : str, optional
            Name of the orientation to apply. The default is ``"isometric"``.
        width : int, optional
            Plot Width. The default is ``1920``.
        height : int, optional
            Plot Height. The default is ``1080``.
        display_wireframe : bool, optional
            Display wireframe. The default is ``True``.
        selections : list, optional
            List of objects to include in the plot.
             Supported in 3D Field Plots only starting from 23R1.
        show_axis : bool, optional
            Whether to show the axes. The default is ``True``.
            Supported in 3D Field Plots only starting from 23R1.
        show_grid : bool, optional
            Whether to show the grid. The default is ``True``.
            Supported in 3D Field Plots only starting from 23R1.
        show_ruler : bool, optional
            Whether to show the ruler. The default is ``True``.
            Supported in 3D Field Plots only starting from 23R1.
        show_region : bool, optional
            Whether to show the region or not. The default is ``Default``.
            Supported in 3D Field Plots only starting from 23R1.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.ExportPlotImageToFile
        >>> oModule.ExportModelImageToFile
        """
        if self.post_solution_type not in ["HFSS3DLayout", "HFSS 3D Layout Design"]:
            wireframes = []
            if display_wireframe:
                names = self._primitives.object_names
                for el in names:
                    if not self._primitives[el].display_wireframe:
                        wireframes.append(el)
                        self._primitives[el].display_wireframe = True
            if self._app._aedt_version < "2021.2":
                bound = self._app.modeler.get_model_bounding_box()
                center = [
                    (float(bound[0]) + float(bound[3])) / 2,
                    (float(bound[1]) + float(bound[4])) / 2,
                    (float(bound[2]) + float(bound[5])) / 2,
                ]
                view = ORIENTATION_TO_VIEW.get(orientation, "iso")
                cs = self._app.modeler.create_coordinate_system(origin=center, mode="view", view=view)
                self.ofieldsreporter.ExportPlotImageToFile(file_name, folder_name, plot_name, cs.name)
                cs.delete()
            else:
                self.export_model_picture(
                    full_name=file_name,
                    width=width,
                    height=height,
                    orientation=orientation,
                    field_selections=plot_name,
                    selections=selections,
                    show_axis=show_axis,
                    show_grid=show_grid,
                    show_ruler=show_ruler,
                    show_region=show_region,
                )

            for solid in wireframes:
                self._primitives[solid].display_wireframe = False
        else:
            self.ofieldsreporter.ExportPlotImageWithViewToFile(
                file_name, folder_name, plot_name, width, height, orientation
            )
        return True

    @pyaedt_function_handler()
    def delete_field_plot(self, name):
        """Delete a field plot.

        Parameters
        ----------
        name : str
            Name of the field plot.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.DeleteFieldPlot
        """
        self.ofieldsreporter.DeleteFieldPlot([name])
        self.field_plots.pop(name, None)
        return True

    @pyaedt_function_handler()
    def export_model_picture(
        self,
        full_name=None,
        show_axis=True,
        show_grid=True,
        show_ruler=True,
        show_region="Default",
        selections=None,
        field_selections=None,
        orientation="isometric",
        width=0,
        height=0,
    ):
        """Export a snapshot of the model to a ``JPG`` file.

        .. note::
           This method works only when AEDT is running in the graphical mode.

        Parameters
        ----------
        full_name : str, optional
            Full Path for exporting the image file. The default is ``None``, in which case working_dir is used.
        show_axis : bool, optional
            Whether to show the axes. The default is ``True``.
        show_grid : bool, optional
            Whether to show the grid. The default is ``True``.
        show_ruler : bool, optional
            Whether to show the ruler. The default is ``True``.
        show_region : bool, optional
            Whether to show the region or not. The default is ``Default``.
        selections : list, optional
            Whether to export image of a selection or not. Default is `None`.
        field_selections : str, list, optional
            List of Fields plots to add to the image. Default is `None`. `"all"` for all field plots.
        orientation : str, optional
            Picture orientation. Orientation can be one of `"top"`, `"bottom"`, `"right"`, `"left"`,
            `"front"`, `"back"`, `"trimetric"`, `"dimetric"`, `"isometric"`, or a custom
            orientation that you added to the Orientation List.
        width : int, optional
            Export image picture width size in pixels. Default is 0 which takes the desktop size.
        height : int, optional
            Export image picture height size in pixels. Default is 0 which takes the desktop size.

        Returns
        -------
        str
            File path of the generated JPG file.

        References
        ----------
        >>> oEditor.ExportModelImageToFile

        Examples
        --------
        >>> from ansys.aedt.core import Q3d
        >>> q3d = Q3d(non_graphical=False)
        >>> output_file = q3d.post.export_model_picture(full_name=os.path.join(q3d.working_directory, "images1.jpg"))
        """
        if selections:
            selections = self._app.modeler.convert_to_selections(selections, False)
        else:
            selections = ""
        if not full_name:
            full_name = os.path.join(self._app.working_directory, generate_unique_name(self._app.design_name) + ".jpg")

        # open the 3D modeler and remove the selection on other objects
        if not self._app.desktop_class.non_graphical:  # pragma: no cover
            if self._app.design_type not in [
                "HFSS 3D Layout Design",
                "Circuit Design",
                "Maxwell Circuit",
                "Twin Builder",
            ]:
                self.oeditor.ShowWindow()
                self.steal_focus_oneditor()
            self._app.modeler.fit_all()
        # export the image
        if field_selections:
            if isinstance(field_selections, str):
                if field_selections.lower() == "all":
                    field_selections = [""]
                else:
                    field_selections = [field_selections]

        else:
            field_selections = ["none"]
        arg = [
            "NAME:SaveImageParams",
            "ShowAxis:=",
            str(show_axis),
            "ShowGrid:=",
            str(show_grid),
            "ShowRuler:=",
            str(show_ruler),
            "ShowRegion:=",
            str(show_region),
            "Selections:=",
            selections,
            "FieldPlotSelections:=",
            ",".join(field_selections),
            "Orientation:=",
            orientation,
        ]
        if self._app.design_type in ["HFSS 3D Layout Design", "Circuit Design", "Maxwell Circuit", "Twin Builder"]:
            if width == 0:
                width = 1920
            if height == 0:
                height = 1080
            self.oeditor.ExportImage(full_name, width, height)
        else:
            if self._app.desktop_class.non_graphical:
                if width == 0:
                    width = 500
                if height == 0:
                    height = 500
            self.oeditor.ExportModelImageToFile(full_name, width, height, arg)
        return full_name

    @pyaedt_function_handler(expression="expressions", families_dict="sweeps")
    def get_far_field_data(self, expressions="GainTotal", setup_sweep_name="", domain="Infinite Sphere1", sweeps=None):
        """Generate far field data using the ``GetSolutionDataPerVariation()`` method.

        This method returns the data ``solData``, ``ThetaVals``,
        ``PhiVals``, ``ScanPhiVals``, ``ScanThetaVals``, and
        ``FreqVals``.

        Parameters
        ----------
        expressions : str or list, optional
            One or more formulas to add to the report. The default is ``"GainTotal"``.
        setup_sweep_name : str, optional
            Name of the setup for computing the report. The default is ``""``,
            in which case the nominal sweep is used.
        domain : str, dict, optional
            Context type (sweep or time). The default is ``"Infinite Sphere1"``.
        sweeps : dict, optional
            Dictionary of variables and values. The default is ``{"Freq": ["All"]}``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.solutions.SolutionData`

        References
        ----------
        >>> oModule.GetSolutionDataPerVariation
        """
        if not isinstance(expressions, list):
            expressions = [expressions]
        if not setup_sweep_name:
            setup_sweep_name = self._app.nominal_adaptive
        if sweeps is None:
            sweeps = {"Theta": ["All"], "Phi": ["All"], "Freq": ["All"]}
        context = ["Context:=", domain]
        if isinstance(domain, dict):
            if "Context" in domain.keys() and "SourceContext" in domain.keys():
                context = ["Context:=", domain["Context"], "Context:=", domain["SourceContext"]]

        solution_data = self.get_solution_data_per_variation(
            "Far Fields", setup_sweep_name, context, sweeps, expressions
        )
        if not solution_data:
            print("No Data Available. Check inputs")
            return False
        return solution_data

    @pyaedt_function_handler(obj_list="assignment", export_as_single_objects="export_as_multiple_objects")
    def export_model_obj(self, assignment=None, export_path=None, export_as_multiple_objects=False, air_objects=False):
        """Export the model.

        Parameters
        ----------
        assignment : list of str, optional
            List of strings with names of objects to export. Default is ``None`` in which
            case export every model object except 3D ones and vacuum and air objects.
        export_path : str, optional
            Full path of the exported OBJ file.
        export_as_multiple_objects : bool, optional
           Whether to export the model as multiple objects or not. Default is ``False``
           in which case the model is exported as single object.
        air_objects : bool, optional
            Whether to export air and vacuum objects. The default is ``False``.

        Returns
        -------
        list
            Paths for OBJ files.
        """
        if assignment and not isinstance(assignment, (list, tuple)):
            assignment = [assignment]
        if self._app._aedt_version < "2021.2":
            raise RuntimeError("Object is supported from AEDT 2021 R2.")  # pragma: no cover
        if not export_path:
            export_path = self._app.working_directory
        if not assignment:
            self._app.modeler.refresh_all_ids()
            non_model = self._app.modeler.non_model_objects[:]
            assignment = [i for i in self._app.modeler.object_names if i not in non_model and "PML_" not in i]
            if not air_objects:
                assignment = [
                    i
                    for i in assignment
                    if not self._app.modeler[i].is3d
                    or (
                        self._app.modeler[i].material_name.lower() != "vacuum"
                        and self._app.modeler[i].material_name.lower() != "air"
                    )
                ]
        if export_as_multiple_objects:
            files_exported = []
            for el in assignment:
                fname = os.path.join(export_path, f"{el}.obj")
                self._app.modeler.oeditor.ExportModelMeshToFile(fname, [el])

                fname = check_and_download_file(fname)

                if not self._app.modeler[el].display_wireframe:
                    transp = 0.6
                    t = self._app.modeler[el].transparency
                    if t is not None:
                        transp = t
                    files_exported.append([fname, self._app.modeler[el].color, 1 - transp])
                else:
                    files_exported.append([fname, self._app.modeler[el].color, 0.05])
            return files_exported
        else:
            fname = os.path.join(export_path, "Model_AllObjs_AllMats.obj")
            self._app.modeler.oeditor.ExportModelMeshToFile(fname, assignment)
            return [[fname, "aquamarine", 0.3]]

    @pyaedt_function_handler(setup_name="setup")
    def export_mesh_obj(self, setup=None, intrinsics=None, export_air_objects=False, on_surfaces=True):
        """Export the mesh in AEDTPLT format.

        The mesh has to be available in the selected setup.
        If a parametric model is provided, you can choose the mesh to export by providing a specific set of variations.
        This method applies only to ``Hfss``, ``Q3d``, ``Q2D``, ``Maxwell3d``, ``Maxwell2d``, ``Icepak``
        and ``Mechanical`` objects. This method is calling ``create_fieldplot_surface`` to create a mesh plot and
        ``export_field_plot`` to export it as ``aedtplt`` file.

        Parameters
        ----------
        setup : str, optional
            Name of the setup. The default is ``None``, in which case the ``nominal_adaptive``
            setup is used. Be sure to build a setup string in the form of
            ``"SetupName : SetupSweep"``, where ``SetupSweep`` is the sweep name to
            use in the export or ``LastAdaptive``.
        intrinsics : dict, str, optional
            Intrinsic variables required to compute the field before the export.
            These are typically: frequency, time and phase.
            It can be provided either as a dictionary or as a string.
            If it is a dictionary, keys depend on the solution type and can be expressed in lower or camel case as:
            - ``"Freq"`` or ``"Frequency"``.
            - ``"Time"``.
            - ``"Phase"``.
            If it is a string, it can either be ``"Freq"`` or ``"Time"`` depending on the solution type.
            The default is ``None`` in which case the intrinsics value is automatically computed based on the setup.
        export_air_objects : bool, optional
            Whether to include vacuum objects for the copied objects.
            The default is ``False``.
        on_surfaces : bool, optional
            Whether to create a mesh on surfaces or on the volume.  The default is ``True``.

        Returns
        -------
        str
            File Generated with full path.

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss.analyze()
        >>> # Export report using defaults.
        >>> hfss.post.export_mesh_obj(setup=None,intrinsics=None)
        >>> # Export report using arguments.
        >>> hfss.post.export_mesh_obj(setup="MySetup : LastAdaptive",intrinsics={"w1":"5mm", "l1":"3mm"})
        """
        project_path = self._app.working_directory

        if not setup:
            setup = self._app.nominal_adaptive
        intrinsics = self._app._check_intrinsics(intrinsics, setup=setup)

        mesh_list = []
        obj_list = self._app.modeler.object_names
        for el in obj_list:
            object3d = self._app.modeler[el]
            if on_surfaces:
                if not object3d.is3d or (not export_air_objects and object3d.material_name not in ["vacuum", "air"]):
                    mesh_list += [i.id for i in object3d.faces]
            else:
                if not object3d.is3d or (not export_air_objects and object3d.material_name not in ["vacuum", "air"]):
                    mesh_list.append(el)
        if on_surfaces:
            plot = self.create_fieldplot_surface(mesh_list, "Mesh", setup, intrinsics)
        else:
            plot = self.create_fieldplot_volume(mesh_list, "Mesh", setup, intrinsics)

        if plot:
            file_to_add = self.export_field_plot(plot.name, project_path)
            plot.delete()
            return file_to_add
        return None

    @pyaedt_function_handler()
    def power_budget(self, units="W", temperature=22, output_type="component"):
        """Power budget calculation.

        Parameters
        ----------
        units : str, optional
            Output power units. The default is ``"W"``.
        temperature : float, optional
            Temperature to calculate the power. The default is ``22``.
        output_type : str, optional
            Output data presentation. The default is ``"component"``.
            The options are ``"component"``, or ``"boundary"``.
            ``"component"`` returns the power based on each component.
            ``"boundary"`` returns the power based on each boundary.

        Returns
        -------
        dict, float
            Dictionary with the power introduced on each boundary and total power.

        References
        ----------
        >>> oEditor.ChangeProperty
        """
        available_bcs = self._app.boundaries
        power_dict = {}
        power_dict_obj = {}
        group_hierarchy = {}

        groups = list(self._app.oeditor.GetChildNames("Groups"))
        self._app.modeler.add_new_user_defined_component()
        for g in groups:
            g1 = self._app.oeditor.GetChildObject(g)
            if g1:
                group_hierarchy[g] = list(g1.GetChildNames())

        def multiplier_from_dataset(expression, valuein):
            multiplier = 0
            if expression in self._app.design_datasets:
                dataset = self._app.design_datasets[expression]
            elif expression in self._app.project_datasets:
                dataset = self._app.design_datasets[expression]
            else:
                return multiplier
            if valuein >= max(dataset.x):
                multiplier = dataset.y[-1]
            elif valuein <= min(dataset.x):
                multiplier = dataset.y[0]
            else:
                start_x = 0
                start_y = 0
                end_x = 0
                end_y = 0
                for i, y in enumerate(dataset.x):
                    if y > valuein:
                        start_x = dataset.x[i - 1]
                        start_y = dataset.y[i - 1]
                        end_x = dataset.x[i]
                        end_y = dataset.y[i]
                if end_x - start_x == 0:
                    multiplier = 0
                else:
                    multiplier = start_y + (valuein - start_x) * ((end_y - start_y) / (end_x - start_x))
            return multiplier

        def extract_dataset_info(boundary_obj, units_input="W", boundary="Power"):
            if boundary == "Power":
                prop = "Total Power Variation Data"
            else:
                prop = "Surface Heat Variation Data"
                units_input = "irrad_W_per_m2"
            value_bound = ast.literal_eval(boundary_obj.props[prop]["Variation Value"])[0]
            expression = ast.literal_eval(boundary_obj.props[prop]["Variation Value"])[1]
            value = list(decompose_variable_value(value_bound))
            if isinstance(value[0], str):
                new_value = self._app[value[0]]
                value = list(decompose_variable_value(new_value))
            value = unit_converter(
                value[0],
                unit_system=boundary,
                input_units=value[1],
                output_units=units_input,
            )
            expression = expression.split(",")[0].split("(")[1]
            return value, expression

        if not available_bcs:
            self.logger.warning("No boundaries defined")
            return True
        for bc_obj in available_bcs:
            if bc_obj.type == "Solid Block" or bc_obj.type == "Block":
                n = len(bc_obj.props["Objects"])
                if "Total Power Variation Data" not in bc_obj.props:
                    mult = 1
                    power_value = list(decompose_variable_value(bc_obj.props["Total Power"]))
                    power_value = unit_converter(
                        power_value[0], unit_system="Power", input_units=power_value[1], output_units=units
                    )

                else:
                    power_value, exp = extract_dataset_info(bc_obj, units_input=units, boundary="Power")
                    mult = multiplier_from_dataset(exp, temperature)

                for objs in bc_obj.props["Objects"]:
                    obj_name = self._app.modeler[objs].name
                    power_dict_obj[obj_name] = power_value * mult

                power_dict[bc_obj.name] = power_value * n * mult

            elif bc_obj.type == "SourceIcepak":
                if bc_obj.props["Thermal Condition"] == "Total Power":
                    n = 0
                    if "Faces" in bc_obj.props:
                        n += len(bc_obj.props["Faces"])
                    elif "Objects" in bc_obj.props:
                        n += len(bc_obj.props["Objects"])

                    if "Total Power Variation Data" not in bc_obj.props:
                        mult = 1
                        power_value = list(decompose_variable_value(bc_obj.props["Total Power"]))
                        power_value = unit_converter(
                            power_value[0], unit_system="Power", input_units=power_value[1], output_units=units
                        )
                    else:
                        power_value, exp = extract_dataset_info(bc_obj, units_input=units, boundary="Power")
                        mult = multiplier_from_dataset(exp, temperature)

                    if "Objects" in bc_obj.props:
                        for objs in bc_obj.props["Objects"]:
                            obj_name = self._app.modeler[objs].name
                            power_dict_obj[obj_name] = power_value * mult

                    elif "Faces" in bc_obj.props:
                        for facs in bc_obj.props["Faces"]:
                            obj_name = self._app.modeler.oeditor.GetObjectNameByFaceID(facs) + "_FaceID" + str(facs)
                            power_dict_obj[obj_name] = power_value * mult

                    power_dict[bc_obj.name] = power_value * n * mult

                elif bc_obj.props["Thermal Condition"] == "Surface Flux":
                    if "Surface Heat Variation Data" not in bc_obj.props:
                        mult = 1
                        heat_value = list(decompose_variable_value(bc_obj.props["Surface Heat"]))
                        if isinstance(heat_value[0], str):
                            new_value = self._app[heat_value[0]]
                            heat_value = list(decompose_variable_value(new_value))
                        heat_value = unit_converter(
                            heat_value[0],
                            unit_system="SurfaceHeat",
                            input_units=heat_value[1],
                            output_units="irrad_W_per_m2",
                        )
                    else:
                        mult = 1
                        if bc_obj.props["Surface Heat Variation Data"]["Variation Type"] == "Temp Dep":
                            heat_value, exp = extract_dataset_info(bc_obj, boundary="SurfaceHeat")
                            mult = multiplier_from_dataset(exp, temperature)
                        else:
                            heat_value = 0

                    power_value = 0.0
                    if "Faces" in bc_obj.props:
                        for component in bc_obj.props["Faces"]:
                            area = self._app.modeler.get_face_area(component)
                            area = unit_converter(
                                area,
                                unit_system="Area",
                                input_units=self._app.modeler.model_units + "2",
                                output_units="m2",
                            )
                            power_value += heat_value * area * mult
                    elif "Objects" in bc_obj.props:
                        for component in bc_obj.props["Objects"]:
                            object_assigned = self._app.modeler[component]
                            for f in object_assigned.faces:
                                area = unit_converter(
                                    f.area,
                                    unit_system="Area",
                                    input_units=self._app.modeler.model_units + "2",
                                    output_units="m2",
                                )
                                power_value += heat_value * area * mult

                    power_value = unit_converter(power_value, unit_system="Power", input_units="W", output_units=units)

                    if "Objects" in bc_obj.props:
                        for objs in bc_obj.props["Objects"]:
                            obj_name = self._app.modeler[objs].name
                            power_dict_obj[obj_name] = power_value

                    elif "Faces" in bc_obj.props:
                        for facs in bc_obj.props["Faces"]:
                            obj_name = self._app.modeler.oeditor.GetObjectNameByFaceID(facs) + "_FaceID" + str(facs)
                            power_dict_obj[obj_name] = power_value

                    power_dict[bc_obj.name] = power_value

            elif bc_obj.type == "Network":
                nodes = bc_obj.props["Nodes"]
                power_value = 0
                for node in nodes:
                    if "Power" in nodes[node]:
                        value = nodes[node]["Power"]
                        value = list(decompose_variable_value(value))
                        value = unit_converter(value[0], unit_system="Power", input_units=value[1], output_units=units)
                        power_value += value

                obj_name = self._app.modeler.oeditor.GetObjectNameByFaceID(bc_obj.props["Faces"][0])
                for facs in bc_obj.props["Faces"]:
                    obj_name += "_FaceID" + str(facs)
                power_dict_obj[obj_name] = power_value

                power_dict[bc_obj.name] = power_value

            elif bc_obj.type == "Conducting Plate":
                n = 0
                if "Faces" in bc_obj.props:
                    n += len(bc_obj.props["Faces"])
                elif "Objects" in bc_obj.props:
                    n += len(bc_obj.props["Objects"])

                if "Total Power Variation Data" not in bc_obj.props:
                    mult = 1
                    power_value = list(decompose_variable_value(bc_obj.props["Total Power"]))
                    power_value = unit_converter(
                        power_value[0], unit_system="Power", input_units=power_value[1], output_units=units
                    )

                else:
                    power_value, exp = extract_dataset_info(bc_obj, units_input=units, boundary="Power")
                    mult = multiplier_from_dataset(exp, temperature)

                if "Objects" in bc_obj.props:
                    for objs in bc_obj.props["Objects"]:
                        obj_name = self._app.modeler[objs].name
                        power_dict_obj[obj_name] = power_value * mult

                elif "Faces" in bc_obj.props:
                    for facs in bc_obj.props["Faces"]:
                        obj_name = self._app.modeler.oeditor.GetObjectNameByFaceID(facs) + "_FaceID" + str(facs)
                        power_dict_obj[obj_name] = power_value * mult

                power_dict[bc_obj.name] = power_value * n * mult

            elif bc_obj.type == "Stationary Wall":
                if bc_obj.props["External Condition"] == "Heat Flux":
                    mult = 1
                    heat_value = list(decompose_variable_value(bc_obj.props["Heat Flux"]))
                    heat_value = unit_converter(
                        heat_value[0],
                        unit_system="SurfaceHeat",
                        input_units=heat_value[1],
                        output_units="irrad_W_per_m2",
                    )

                    power_value = 0.0
                    if "Faces" in bc_obj.props:
                        for component in bc_obj.props["Faces"]:
                            area = self._app.modeler.get_face_area(component)
                            area = unit_converter(
                                area,
                                unit_system="Area",
                                input_units=self._app.modeler.model_units + "2",
                                output_units="m2",
                            )
                            power_value += heat_value * area * mult
                    if "Objects" in bc_obj.props:
                        for component in bc_obj.props["Objects"]:
                            object_assigned = self._app.modeler[component]
                            for f in object_assigned.faces:
                                area = unit_converter(
                                    f.area,
                                    unit_system="Area",
                                    input_units=self._app.modeler.model_units + "2",
                                    output_units="m2",
                                )
                                power_value += heat_value * area * mult

                    power_value = unit_converter(power_value, unit_system="Power", input_units="W", output_units=units)

                    if "Objects" in bc_obj.props:
                        for objs in bc_obj.props["Objects"]:
                            obj_name = self._app.modeler[objs].name
                            power_dict_obj[obj_name] = power_value

                    elif "Faces" in bc_obj.props:
                        for facs in bc_obj.props["Faces"]:
                            obj_name = self._app.modeler.oeditor.GetObjectNameByFaceID(facs) + "_FaceID" + str(facs)
                            power_dict_obj[obj_name] = power_value

                    power_dict[bc_obj.name] = power_value

            elif bc_obj.type == "Resistance":
                n = len(bc_obj.props["Objects"])
                mult = 1
                power_value = list(decompose_variable_value(bc_obj.props["Thermal Power"]))
                power_value = unit_converter(
                    power_value[0], unit_system="Power", input_units=power_value[1], output_units=units
                )

                for objs in bc_obj.props["Objects"]:
                    obj_name = self._app.modeler[objs].name
                    power_dict_obj[obj_name] = power_value * mult

                power_dict[bc_obj.name] = power_value * n * mult

            elif bc_obj.type == "Blower":
                power_value = list(decompose_variable_value(bc_obj.props["Blower Power"]))
                power_value = unit_converter(
                    power_value[0], unit_system="Power", input_units=power_value[1], output_units=units
                )

                obj_name = bc_obj.name
                power_dict_obj[obj_name] = power_value

                power_dict[bc_obj.name] = power_value

        for native_comps in self._app.modeler.user_defined_components.keys():
            if hasattr(self._app.modeler.user_defined_components[native_comps], "native_properties"):
                native_key = "NativeComponentDefinitionProvider"
                if native_key in self._app.modeler.user_defined_components[native_comps].native_properties:
                    power_key = self._app.modeler.user_defined_components[native_comps].native_properties[native_key]
                else:
                    power_key = self._app.modeler.user_defined_components[native_comps].native_properties
                power_value = None
                if "Power" in power_key:
                    power_value = list(decompose_variable_value(power_key["Power"]))
                elif "HubPower" in power_key:
                    power_value = list(decompose_variable_value(power_key["HubPower"]))

                if power_value:
                    power_value = unit_converter(
                        power_value[0], unit_system="Power", input_units=power_value[1], output_units=units
                    )

                    power_dict_obj[native_comps] = power_value
                    power_dict[native_comps] = power_value

        for group in reversed(list(group_hierarchy.keys())):
            for comp in group_hierarchy[group]:
                for power_comp in list(power_dict_obj.keys())[:]:
                    if power_comp.find(comp) >= 0:
                        if group not in power_dict_obj.keys():
                            power_dict_obj[group] = 0.0
                        power_dict_obj[group] += power_dict_obj[power_comp]

        if output_type == "boundary":
            for comp, value in power_dict.items():
                if round(value, 3) != 0.0:
                    self.logger.info(f"The power of {comp} is {str(round(value, 3))} {units}")
            self.logger.info(f"The total power is {str(round(sum(power_dict.values()), 3))} {units}")
            return power_dict, sum(power_dict.values())

        elif output_type == "component":  # pragma: no cover
            for comp, value in power_dict_obj.items():
                if round(value, 3) != 0.0:
                    self.logger.info(f"The power of {comp} is {str(round(value, 3))} {units}")
            self.logger.info(f"The total power is {str(round(sum(power_dict_obj.values()), 3))} {units}")
            return power_dict_obj, sum(power_dict_obj.values())

        else:  # pragma: no cover
            for comp, value in power_dict.items():
                if round(value, 3) != 0.0:
                    self.logger.info(f"The power of {comp} is {str(round(value, 3))} {units}")
            self.logger.info(f"The total power is {str(round(sum(power_dict.values()), 3))} {units}")
            for comp, value in power_dict_obj.items():
                if round(value, 3) != 0.0:
                    self.logger.info(f"The power of {comp} is {str(round(value, 3))} {units}")
            self.logger.info(f"The total power is {str(round(sum(power_dict_obj.values()), 3))} {units}")
            return power_dict_obj, sum(power_dict_obj.values()), power_dict, sum(power_dict.values())

    @pyaedt_function_handler()
    def create_creeping_plane_visual_ray_tracing(
        self,
        max_frequency="1GHz",
        ray_density=1,
        sample_density=10,
        ray_cutoff=40,
        irregular_surface_tolerance=50,
        incident_theta=0,
        incident_phi=0,
        is_vertical_polarization=False,
    ):
        """Create a Creeping Wave Plane Wave Visual Ray Tracing and return the class object.

        Parameters
        ----------
        max_frequency : str, optional
            Maximum Frequency. Default is ``"1GHz"``.
        ray_density : int, optional
            Ray Density. Default is ``2``.
        sample_density : int, optional
            Sample density. Default is ``10``.
        ray_cutoff : int, optional
            Ray Cutoff number. Default is ``40``.
        irregular_surface_tolerance : int, optional
            Irregular Surface Tolerance value. Default is ``50``.
        incident_theta : str, optional
            Incident plane wave theta. Default is ``"0deg"``.
        incident_phi : str, optional
            Incident plane wave phi. Default is ``"0deg"``.
        is_vertical_polarization : bool, optional
            Whether if enable or Vertical Polarization or not. Default is ``False``.

        Returns
        -------
        :class:` from ansys.aedt.core.modules.solutions.VRTFieldPlot`
        """
        vrt = VRTFieldPlot(self, is_creeping_wave=True)
        vrt.max_frequency = max_frequency
        vrt.sample_density = sample_density
        vrt.ray_density = ray_density
        vrt.ray_cutoff = ray_cutoff
        vrt.irregular_surface_tolerance = irregular_surface_tolerance
        vrt.is_plane_wave = True
        vrt.incident_theta = incident_theta
        vrt.incident_phi = incident_phi
        vrt.vertical_polarization = is_vertical_polarization
        vrt.create()
        return vrt

    @pyaedt_function_handler()
    def create_creeping_point_visual_ray_tracing(
        self,
        max_frequency="1GHz",
        ray_density=1,
        sample_density=10,
        ray_cutoff=40,
        irregular_surface_tolerance=50,
        custom_location=None,
    ):
        """Create a Creeping Wave Point Source Visual Ray Tracing and return the class object.

        Parameters
        ----------
        max_frequency : str, optional
            Maximum Frequency. Default is ``"1GHz"``.
        ray_density : int, optional
            Ray Density. Default is ``2``.
        sample_density : int, optional
            Sample density. Default is ``10``.
        ray_cutoff : int, optional
            Ray Cutoff number. Default is ``40``.
        irregular_surface_tolerance : int, optional
            Irregular Surface Tolerance value. Default is ``50``.
        custom_location : list, optional
            List of x, y,z position of point source. Default is ``None``.

        Returns
        -------
        :class:` from ansys.aedt.core.modules.solutions.VRTFieldPlot`
        """
        if custom_location is None:
            custom_location = [0, 0, 0]
        vrt = VRTFieldPlot(self, is_creeping_wave=True)
        vrt.max_frequency = max_frequency
        vrt.sample_density = sample_density
        vrt.ray_density = ray_density
        vrt.ray_cutoff = ray_cutoff
        vrt.irregular_surface_tolerance = irregular_surface_tolerance
        vrt.is_plane_wave = False
        vrt.custom_location = custom_location
        vrt.create()
        return vrt

    @pyaedt_function_handler()
    def create_sbr_plane_visual_ray_tracing(
        self,
        max_frequency="1GHz",
        ray_density=2,
        number_of_bounces=5,
        multi_bounce=False,
        mbrd_max_sub_division=2,
        shoot_utd=False,
        incident_theta=0,
        incident_phi=0,
        is_vertical_polarization=False,
        shoot_filter_type="All Rays",
        ray_index_start=0,
        ray_index_stop=1,
        ray_index_step=1,
        ray_box=None,
    ):
        """Create an SBR Plane Wave Visual Ray Tracing and return the class object.

        Parameters
        ----------
        max_frequency : str, optional
            Maximum Frequency. Default is ``"1GHz"``.
        ray_density : int, optional
            Ray Density. Default is ``2``.
        number_of_bounces : int, optional
            Maximum number of bounces. Default is ``5``.
        multi_bounce : bool, optional
            Whether if enable or not Multi-Bounce ray density control. Default is ``False``.
        mbrd_max_sub_division : int, optional
            Maximum number of MBRD subdivisions. Default is ``2``.
        shoot_utd : bool, optional
            Whether if enable or UTD Rays shooting or not. Default is ``False``.
        incident_theta : str, optional
            Incident plane wave theta. Default is ``"0deg"``.
        incident_phi : str, optional
            Incident plane wave phi. Default is ``"0deg"``.
        is_vertical_polarization : bool, optional
            Whether if enable or Vertical Polarization or not. Default is ``False``.
        shoot_filter_type : str, optional
            Shooter Type. Default is ``"All Rays"``. Options are  ``"Rays by index"``,  ``"Rays in box"``.
        ray_index_start : int, optional
            Ray index start. Valid only if ``"Rays by index"`` is chosen.  Default is ``0``.
        ray_index_stop : int, optional
            Ray index stop. Valid only if ``"Rays by index"`` is chosen.  Default is ``1``.
        ray_index_step : int, optional
            Ray index step. Valid only if ``"Rays by index"`` is chosen.  Default is ``1``.
        ray_box : int or str optional
            Ray box name or id. Valid only if ``"Rays by box"`` is chosen.  Default is ``None``.

        Returns
        -------
        :class:` from ansys.aedt.core.modules.solutions.VRTFieldPlot`
        """
        vrt = VRTFieldPlot(self, is_creeping_wave=False)
        vrt.max_frequency = max_frequency
        vrt.ray_density = ray_density
        vrt.number_of_bounces = number_of_bounces
        vrt.multi_bounce_ray_density_control = multi_bounce
        vrt.mbrd_max_subdivision = mbrd_max_sub_division
        vrt.shoot_utd_rays = shoot_utd
        vrt.shoot_type = shoot_filter_type
        vrt.is_plane_wave = True
        vrt.incident_theta = incident_theta
        vrt.incident_phi = incident_phi
        vrt.vertical_polarization = is_vertical_polarization
        vrt.start_index = ray_index_start
        vrt.stop_index = ray_index_stop
        vrt.step_index = ray_index_step
        vrt.ray_box = ray_box
        vrt.create()
        return vrt

    @pyaedt_function_handler()
    def create_sbr_point_visual_ray_tracing(
        self,
        max_frequency="1GHz",
        ray_density=2,
        number_of_bounces=5,
        multi_bounce=False,
        mbrd_max_sub_division=2,
        shoot_utd=False,
        custom_location=None,
        shoot_filter_type="All Rays",
        ray_index_start=0,
        ray_index_stop=1,
        ray_index_step=1,
        ray_box=None,
    ):
        """Create an SBR Point Source Visual Ray Tracing and return the class object.

        Parameters
        ----------
        max_frequency : str, optional
            Maximum Frequency. Default is ``1GHz``.
        ray_density : int, optional
            Ray Density. Default is ``2``.
        number_of_bounces : int, optional
            Maximum number of bounces. Default is ``5``.
        multi_bounce : bool, optional
            Whether if enable or not Multi-Bounce ray density control. Default is ``False``.
        mbrd_max_sub_division : int, optional
            Maximum number of MBRD subdivisions. Default is ``2``.
        shoot_utd : bool, optional
            Whether if enable or UTD Rays shooting or not. Default is ``False``.
        custom_location : list, optional
            List of x, y,z position of point source. Default is ``None``.
        shoot_filter_type : str, optional
            Shooter Type. Default is ``"All Rays"``. Options are ``Rays by index``, ``Rays in box``.
        ray_index_start : int, optional
            Ray index start. Valid only if ``Rays by index`` is chosen.  Default is ``0``.
        ray_index_stop : int, optional
            Ray index stop. Valid only if ``Rays by index`` is chosen.  Default is ``1``.
        ray_index_step : int, optional
            Ray index step. Valid only if ``Rays by index`` is chosen.  Default is ``1``.
        ray_box : int or str optional
            Ray box name or id. Valid only if ``Rays by box`` is chosen.  Default is ``None``.

        Returns
        -------
        :class:` from ansys.aedt.core.modules.solutions.VRTFieldPlot`

        """
        if custom_location is None:
            custom_location = [0, 0, 0]
        vrt = VRTFieldPlot(self, is_creeping_wave=False)
        vrt.max_frequency = max_frequency
        vrt.ray_density = ray_density
        vrt.number_of_bounces = number_of_bounces
        vrt.multi_bounce_ray_density_control = multi_bounce
        vrt.mbrd_max_subdivision = mbrd_max_sub_division
        vrt.shoot_utd_rays = shoot_utd
        vrt.shoot_type = shoot_filter_type
        vrt.is_plane_wave = False
        vrt.custom_location = custom_location
        vrt.start_index = ray_index_start
        vrt.stop_index = ray_index_stop
        vrt.step_index = ray_index_step
        vrt.ray_box = ray_box
        vrt.create()
        return vrt

    @pyaedt_function_handler()
    def set_tuning_offset(self, setup, offsets):
        """Set derivative variable to a specific offset value.

        Parameters
        ----------
        setup : str
            Setup name.
        offsets : dict
            Dictionary containing the variable name and it's offset value.

        Returns
        -------
        bool
        """
        setup_obj = self._app.get_setup(setup)
        if setup_obj and "set_tuning_offset" in dir(setup_obj):
            return setup_obj.set_tuning_offset(offsets)
        self.logger.error("Tuning offset applies only to solved setup with derivatives enabled.")
        return False

    @pyaedt_function_handler()
    def nb_display(self, show_axis=True, show_grid=True, show_ruler=True):
        """Show the Jupyter Notebook display.

          .. note::
              .assign_curvature_extraction Jupyter Notebook is not supported by IronPython.

        Parameters
        ----------
        show_axis : bool, optional
            Whether to show the axes. The default is ``True``.
        show_grid : bool, optional
            Whether to show the grid. The default is ``True``.
        show_ruler : bool, optional
            Whether to show the ruler. The default is ``True``.

        Returns
        -------
        :class:`IPython.core.display.Image`
            Jupyter notebook image.
        """
        try:
            from IPython.display import Image

            ipython_available = True
        except ImportError:
            ipython_available = False
            Image = None
        if ipython_available:
            file_name = self.export_model_picture(show_axis=show_axis, show_grid=show_grid, show_ruler=show_ruler)
            return Image(file_name, width=500)
        else:
            warnings.warn("The Ipython package is missing and must be installed.")

    @pyaedt_function_handler()
    def get_efields_data(self, setup_sweep_name="", ff_setup="Infinite Sphere1", freq="All"):
        """Compute Etheta and EPhi.

        .. warning::
           This method requires NumPy to be installed on your machine.


        Parameters
        ----------
        setup_sweep_name : str, optional
            Name of the setup for computing the report. The default is ``""``, in
            which case the nominal adaptive is applied.
        ff_setup : str, optional
            Far field setup. The default is ``"Infinite Sphere1"``.
        freq : str, optional
            The default is ``"All"``.

        Returns
        -------
        np.ndarray
            Numpy array containing ``[theta_range, phi_range, Etheta, Ephi]``.
        """
        if not setup_sweep_name:
            setup_sweep_name = self._app.nominal_adaptive
        results_dict = {}
        all_sources = self.post_osolution.GetAllSources()
        # assuming only 1 mode
        all_sources_with_modes = [s + ":1" for s in all_sources]

        for n, source in enumerate(all_sources_with_modes):
            edit_sources_ctxt = [["IncludePortPostProcessing:=", False, "SpecifySystemPower:=", False]]
            for m, each in enumerate(all_sources_with_modes):
                if n == m:  # set only 1 source to 1W, all the rest to 0
                    mag = 1
                else:
                    mag = 0
                phase = 0
                edit_sources_ctxt.append(["Name:=", f"{each}", "Magnitude:=", f"{mag}W", "Phase:=", f"{phase}deg"])
            self.post_osolution.EditSources(edit_sources_ctxt)

            trace_name = "rETheta"
            solnData = self.get_far_field_data(
                expressions=trace_name, setup_sweep_name=setup_sweep_name, domain=ff_setup
            )

            data = solnData.nominal_variation

            theta_vals = np.degrees(np.array(data.GetSweepValues("Theta")))
            phi_vals = np.degrees(np.array(data.GetSweepValues("Phi")))
            # phi is outer loop
            theta_unique = np.unique(theta_vals)
            phi_unique = np.unique(phi_vals)
            theta_range = np.linspace(np.min(theta_vals), np.max(theta_vals), np.size(theta_unique))
            phi_range = np.linspace(np.min(phi_vals), np.max(phi_vals), np.size(phi_unique))
            real_theta = np.array(data.GetRealDataValues(trace_name))
            imag_theta = np.array(data.GetImagDataValues(trace_name))

            trace_name = "rEPhi"
            solnData = self.get_far_field_data(
                expressions=trace_name, setup_sweep_name=setup_sweep_name, domain=ff_setup
            )
            data = solnData.nominal_variation

            real_phi = np.array(data.GetRealDataValues(trace_name))
            imag_phi = np.array(data.GetImagDataValues(trace_name))

            Etheta = np.vectorize(complex)(real_theta, imag_theta)
            Ephi = np.vectorize(complex)(real_phi, imag_phi)
            source_name_without_mode = source.replace(":1", "")
            results_dict[source_name_without_mode] = [theta_range, phi_range, Etheta, Ephi]
        return results_dict

    @pyaedt_function_handler()
    def get_model_plotter_geometries(
        self,
        objects=None,
        plot_as_separate_objects=True,
        plot_air_objects=False,
        force_opacity_value=None,
        array_coordinates=None,
        generate_mesh=True,
        get_objects_from_aedt=True,
    ):
        """Initialize the Model Plotter object with actual modeler objects and return it.

        Parameters
        ----------
        objects : list, optional
            Optional list of objects to plot. If `None` all objects will be exported.
        plot_as_separate_objects : bool, optional
            Plot each object separately. It may require more time to export from AEDT.
        plot_air_objects : bool, optional
            Plot also air and vacuum objects.
        force_opacity_value : float, optional
            Opacity value between 0 and 1 to be applied to all model.
            If `None` aedt opacity will be applied to each object.
        array_coordinates : list of list
            List of array element centers. The modeler objects will be duplicated and translated.
            List of [[x1,y1,z1], [x2,y2,z2]...].
        generate_mesh : bool, optional
            Whether to generate the mesh after importing objects. The default is ``True``.
        get_objects_from_aedt : bool, optional
            Whether to export objects from AEDT and initialize them. The default is ``True``.

        Returns
        -------
        :class:`ansys.aedt.core.generic.plot.ModelPlotter`
            Model Object.
        """
        if self._app._aedt_version < "2021.2":
            raise RuntimeError("Object is supported from AEDT 2021 R2.")  # pragma: no cover

        files = []
        if get_objects_from_aedt and self._app.solution_type not in ["HFSS3DLayout", "HFSS 3D Layout Design"]:
            files = self.export_model_obj(
                assignment=objects, export_as_multiple_objects=plot_as_separate_objects, air_objects=plot_air_objects
            )

        model = ModelPlotter()
        model.off_screen = True
        units = self._app.modeler.model_units
        for file in files:
            if force_opacity_value:
                model.add_object(file[0], file[1], force_opacity_value, units)
            else:
                model.add_object(file[0], file[1], file[2], units)
        model.array_coordinates = array_coordinates
        if generate_mesh:
            model.generate_geometry_mesh()
        return model

    @pyaedt_function_handler()
    def plot_model_obj(
        self,
        objects=None,
        show=True,
        export_path=None,
        plot_as_separate_objects=True,
        plot_air_objects=False,
        force_opacity_value=None,
        clean_files=False,
        array_coordinates=None,
        view="isometric",
        show_legend=True,
        dark_mode=False,
        show_bounding=False,
        show_grid=False,
    ):
        """Plot the model or a substet of objects.

        Parameters
        ----------
        objects : list, optional
            Optional list of objects to plot. If `None` all objects will be exported.
        show : bool, optional
            Show the plot after generation or simply return the
            generated Class for more customization before plot.
        export_path : str, optional
            If available, an image is saved to file. If `None` no image will be saved.
        plot_as_separate_objects : bool, optional
            Plot each object separately. It may require more time to export from AEDT.
        plot_air_objects : bool, optional
            Plot also air and vacuum objects.
        force_opacity_value : float, optional
            Opacity value between 0 and 1 to be applied to all model.
            If `None` aedt opacity will be applied to each object.
        clean_files : bool, optional
            Clean created files after plot. Cache is mainteined into the model object returned.
        array_coordinates : list of list
            List of array element centers. The modeler objects will be duplicated and translated.
            List of [[x1,y1,z1], [x2,y2,z2]...].
        view : str, optional
           View to export. Options are ``"isometric"``, ``"xy"``, ``"xz"``, ``"yz"``.
            The default is ``"isometric"``.
        show_legend : bool, optional
            Whether to display the legend or not. The default is ``True``.
        dark_mode : bool, optional
            Whether to display the model in dark mode or not. The default is ``False``.
        show_grid : bool, optional
            Whether to display the axes grid or not. The default is ``False``.
        show_bounding : bool, optional
            Whether to display the axes bounding box or not. The default is ``False``.

        Returns
        -------
        :class:`ansys.aedt.core.generic.plot.ModelPlotter`
            Model Object.
        """
        model = self.get_model_plotter_geometries(
            objects=objects,
            plot_as_separate_objects=plot_as_separate_objects,
            plot_air_objects=plot_air_objects,
            force_opacity_value=force_opacity_value,
            array_coordinates=array_coordinates,
            generate_mesh=False,
        )

        model.show_legend = show_legend
        model.off_screen = not show
        if dark_mode:
            model.background_color = [40, 40, 40]
        model.bounding_box = show_bounding
        model.show_grid = show_grid
        if view != "isometric" and view in ["xy", "xz", "yz"]:
            model.camera_position = view
        elif view != "isometric":
            self.logger.warning("Wrong view setup. It has to be one of xy, xz, yz, isometric.")
        if export_path:
            model.plot(export_path)
        elif show:
            model.plot()
        if clean_files:
            model.clean_cache_and_files(clean_cache=False)
        return model

    @pyaedt_function_handler(plotname="plot_name", meshplot="mesh_plot", imageformat="image_format")
    def plot_field_from_fieldplot(
        self,
        plot_name,
        project_path="",
        mesh_plot=False,
        image_format="jpg",
        view="isometric",
        plot_label="Temperature",
        plot_folder=None,
        show=True,
        scale_min=None,
        scale_max=None,
        plot_cad_objs=True,
        log_scale=True,
        dark_mode=False,
        show_grid=False,
        show_bounding=False,
        show_legend=True,
        plot_as_separate_objects=True,
        file_format="case",
    ):
        """Export a field plot to an image file (JPG or PNG) using Python PyVista.

        This method does not support streamlines plot.

        .. note::
           The PyVista module rebuilds the mesh and the overlap fields on the mesh.

        Parameters
        ----------
        plot_name : str
            Name of the field plot to export.
        project_path : str, optional
            Path for saving the image file. The default is ``""``.
        mesh_plot : bool, optional
            Whether to create and plot the mesh over the fields. The default is ``False``.
        image_format : str, optional
            Format of the image file. Options are ``"jpg"``, ``"png"``, ``"svg"``, and ``"webp"``.
            The default is ``"jpg"``.
        view : str, optional
           View to export. Options are ``"isometric"``, ``"xy"``, ``"xz"``, ``"yz"``.
        plot_label : str, optional
            Type of the plot. The default is ``"Temperature"``.
        plot_folder : str, optional
            Plot folder to update before exporting the field.
            The default is ``None``, in which case all plot folders are updated.
        show : bool, optional
            Export Image without plotting on UI.
        scale_min : float, optional
            Fix the Scale Minimum value.
        scale_max : float, optional
            Fix the Scale Maximum value.
        plot_cad_objs : bool, optional
            Whether to include objects in the plot. The default is ``True``.
        log_scale : bool, optional
            Whether to plot fields in log scale. The default is ``True``.
        dark_mode : bool, optional
            Whether to display the model in dark mode or not. The default is ``False``.
        show_grid : bool, optional
            Whether to display the axes grid or not. The default is ``False``.
        show_bounding : bool, optional
            Whether to display the axes bounding box or not. The default is ``False``.
        show_legend : bool, optional
            Whether to display the legend. The default is ``True``.
        plot_as_separate_objects : bool, optional
            Whether to plot each object separately, which can require
            more time to export from AEDT. The default is ``True``.
        file_format : str, optional
            File format to export the plot to. The default is ``"case".
            Options are ``"aedtplt"`` and ``"case"``.
            If the active design is a Q3D design, the file format is automatically
            set to ``"fldplt"``.

        Returns
        -------
        :class:`ansys.aedt.core.generic.plot.ModelPlotter`
            Model Object.
        """
        is_pcb = False
        if self._app.solution_type in ["HFSS3DLayout", "HFSS 3D Layout Design"]:
            is_pcb = True
        if not plot_folder:
            self.ofieldsreporter.UpdateAllFieldsPlots()
        else:
            self.ofieldsreporter.UpdateQuantityFieldsPlots(plot_folder)

        file_to_add = self.export_field_plot(plot_name, self._app.working_directory, file_format=file_format)
        model = self.get_model_plotter_geometries(
            generate_mesh=False,
            get_objects_from_aedt=plot_cad_objs,
            plot_as_separate_objects=plot_as_separate_objects,
        )
        model.show_legend = show_legend
        model.off_screen = not show
        if dark_mode:
            model.background_color = [40, 40, 40]
        model.bounding_box = show_bounding
        model.show_grid = show_grid
        if file_to_add:
            model.add_field_from_file(
                file_to_add,
                coordinate_units=self._app.modeler.model_units,
                show_edges=mesh_plot,
                log_scale=log_scale,
            )
            if plot_label:
                model.fields[0].label = plot_label

        if view != "isometric" and view in ["xy", "xz", "yz"]:
            model.camera_position = view
        elif view != "isometric":
            self.logger.warning("Wrong view setup. It has to be one of xy, xz, yz, isometric.")
        if is_pcb:
            model.z_scale = 5

        if scale_min is not None and scale_max is None or scale_min is None and scale_max is not None:
            self.logger.warning("Invalid scale values: both values must be None or different from None.")
        elif scale_min is not None and scale_max is not None and not 0 <= scale_min < scale_max:
            self.logger.warning("Invalid scale values: scale_min must be greater than zero and less than scale_max.")
        elif log_scale and scale_min == 0:
            self.logger.warning("Invalid scale minimum value for logarithm scale.")
        else:
            model.range_min = scale_min
            model.range_max = scale_max
        if project_path:
            model.plot(os.path.join(project_path, plot_name + "." + image_format))
        elif show:
            model.plot()
        return model

    @pyaedt_function_handler(object_list="assignment", imageformat="image_format", setup_name="setup")
    def plot_field(
        self,
        quantity,
        assignment,
        plot_type="Surface",
        setup=None,
        intrinsics=None,
        mesh_on_fields=False,
        view="isometric",
        plot_label=None,
        show=True,
        scale_min=None,
        scale_max=None,
        plot_cad_objs=True,
        log_scale=False,
        export_path="",
        image_format="jpg",
        keep_plot_after_generation=False,
        dark_mode=False,
        show_bounding=False,
        show_grid=False,
        show_legend=True,
        filter_objects=None,
        plot_as_separate_objects=True,
    ):
        """Create a field plot  using Python PyVista and export to an image file (JPG or PNG).

        .. note::
           The PyVista module rebuilds the mesh and the overlap fields on the mesh.

        Parameters
        ----------
        quantity : str
            Quantity to plot. For example, ``"Mag_E"``.
        assignment : str, list
            One or more objects or faces to apply the field plot to.
        plot_type  : str, optional
            Plot type. The default is ``Surface``. Options are
            ``"CutPlane"``, ``"Surface"``, and ``"Volume"``.
        setup : str, optional
            Setup and sweep name on which create the field plot. Default is None for nominal setup usage.
        intrinsics : dict, str, optional
            Intrinsic variables required to compute the field before the export.
            These are typically: frequency, time and phase.
            It can be provided either as a dictionary or as a string.
            If it is a dictionary, keys depend on the solution type and can be expressed as:

            - ``"Freq"`` or ``"Frequency"``.
            - ``"Time"``.
            - ``"Phase"``.

            If it is a string, it can either be ``"Freq"`` or ``"Time"`` depending on the solution type.
            The default is ``None`` in which case the intrinsics value is automatically computed based on the setup.
        mesh_on_fields : bool, optional
            Whether to create and plot the mesh over the fields. The
            default is ``False``.
        view : str, optional
           View to export. Options are ``"isometric"``, ``"xy"``, ``"xz"``, ``"yz"``.
        plot_label : str, optional
            Type of the plot. The default is ``"Temperature"``.
        show : bool, optional
            Export Image without plotting on UI.
        scale_min : float, optional
            Fix the Scale Minimum value.
        scale_max : float, optional
            Fix the Scale Maximum value.
        plot_cad_objs : bool, optional
            Whether to include objects in the plot. The default is ``True``.
        log_scale : bool, optional
            Whether to plot fields in log scale. The default is ``False``.
        export_path : str, optional
            Image export path. Default is ``None`` to not export the image.
        image_format : str, optional
            Format of the image file. Options are ``"jpg"``, ``"png"``, ``"svg"``, and ``"webp"``.
            The default is ``"jpg"``.
        keep_plot_after_generation : bool, optional
            Either to keep the Field Plot in AEDT after the generation is completed. Default is ``False``.
        dark_mode : bool, optional
            Whether to display the model in dark mode or not. The default is ``False``.
        show_grid : bool, optional
            Whether to display the axes grid or not. The default is ``False``.
        show_bounding : bool, optional
            Whether to display the axes bounding box or not. The default is ``False``.
        show_legend : bool, optional
            Whether to display the legend or not. The default is ``True``.
        filter_objects : list, optional
            Objects list for filtering the ``CutPlane`` plots.
        plot_as_separate_objects : bool, optional
            Plot each object separately. It may require more time to export from AEDT.

        Returns
        -------
        :class:`ansys.aedt.core.visualization.plot.pyvista.ModelPlotter`
            Model Object.
        """
        intrinsics = self._app._check_intrinsics(intrinsics, setup=setup)
        if filter_objects is None:
            filter_objects = []
        if os.getenv("PYAEDT_DOC_GENERATION", "False").lower() in ("true", "1", "t"):  # pragma: no cover
            show = False
        if not setup:
            setup = self._app.existing_analysis_sweeps[0]

        # file_to_add = []
        if plot_type == "Surface":
            plotf = self.create_fieldplot_surface(assignment, quantity, setup, intrinsics)
        elif plot_type == "Volume":
            plotf = self.create_fieldplot_volume(assignment, quantity, setup, intrinsics)
        else:
            plotf = self.create_fieldplot_cutplane(
                assignment, quantity, setup, intrinsics, filter_objects=filter_objects
            )
        # if plotf:
        #     file_to_add = self.export_field_plot(plotf.name, self._app.working_directory, plotf.name)

        model = self.plot_field_from_fieldplot(
            plotf.name,
            export_path,
            mesh_on_fields,
            image_format,
            view,
            plot_label if plot_label else quantity,
            None,
            show,
            scale_min,
            scale_max,
            plot_cad_objs,
            log_scale,
            dark_mode=dark_mode,
            show_grid=show_grid,
            show_bounding=show_bounding,
            show_legend=show_legend,
            plot_as_separate_objects=plot_as_separate_objects,
        )
        if not keep_plot_after_generation:
            plotf.delete()
        return model

    @pyaedt_function_handler(object_list="assignment", variation_list="variations", setup_name="setup")
    def plot_animated_field(
        self,
        quantity,
        assignment,
        plot_type="Surface",
        setup=None,
        intrinsics=None,
        variation_variable="Phi",
        variations=None,
        view="isometric",
        show=True,
        scale_min=None,
        scale_max=None,
        plot_cad_objs=True,
        log_scale=True,
        zoom=None,
        export_gif=False,
        export_path="",
        force_opacity_value=0.1,
        dark_mode=False,
        show_grid=False,
        show_bounding=False,
        show_legend=True,
        filter_objects=None,
    ):
        """Create an animated field plot using Python PyVista and export to a gif file.

        .. note::
           The PyVista module rebuilds the mesh and the overlap fields on the mesh.

        Parameters
        ----------
        quantity : str
            Quantity to plot (for example, ``"Mag_E"``).
        assignment : list, str
            One or more objects or faces to apply the field plot to.
        plot_type  : str, optional
            Plot type. The default is ``Surface``. Options are
            ``"CutPlane"``, ``"Surface"``, and ``"Volume"``.
        setup : str, optional
            Setup and sweep name on which create the field plot. Default is None for nominal setup usage.
        intrinsics : dict, str, optional
            Intrinsic variables required to compute the field before the export.
            These are typically: frequency, time and phase.
            It can be provided either as a dictionary or as a string.
            If it is a dictionary, keys depend on the solution type and can be expressed as:
            - ``"Freq"`` or ``"Frequency"``
            - ``"Time"``
            - ``"Phase"``

            If it is a string, it can either be ``"Freq"`` or ``"Time"`` depending on the solution type.
            The default is ``None`` in which case the intrinsics value is automatically computed based on the setup.
        variation_variable : str, optional
            Variable to vary. The default is ``"Phi"``.
        variations : list, optional
            List of variation values with units. The default is ``["0deg"]``.
        view : str, optional
           View to export. Options are ``"isometric"``, ``"xy"``, ``"xz"``, ``"yz"``.
        show : bool, optional
            Export Image without plotting on UI.
        scale_min : float, optional
            Fix the Scale Minimum value.
        scale_max : float, optional
            Fix the Scale Maximum value.
        plot_cad_objs : bool, optional
            Whether to include objects in the plot. The default is ``True``.
        log_scale : bool, optional
            Whether to plot fields in log scale. The default is ``True``.
        zoom : float, optional
            Zoom factor.
        export_gif : bool, optional
             Whether to export an animated gif or not. The default is ``False``.
        export_path : str, optional
            Image export path. Default is ``None`` to not ``working_directory`` will be used to save the image.
        force_opacity_value : float, optional
            Opacity value between 0 and 1 to be applied to all model.
            If `None` aedt opacity will be applied to each object.
        dark_mode : bool, optional
            Whether to display the model in dark mode or not. The default is ``False``.
        show_grid : bool, optional
            Whether to display the axes grid or not. The default is ``False``.
        show_bounding : bool, optional
            Whether to display the axes bounding box or not. The default is ``False``.
        show_legend : bool, optional
            Whether to display the legend or not. The default is ``True``.
        filter_objects : list, optional
            Objects list for filtering the ``CutPlane`` plots.
            The default is ``None`` in which case an empty list is passed.

        Returns
        -------
        :class:`ansys.aedt.core.generic.plot.ModelPlotter`
            Model Object.
        """
        intrinsics = self._app._check_intrinsics(intrinsics, setup=setup)
        if variations is None:
            variations = ["0deg"]
        if os.getenv("PYAEDT_DOC_GENERATION", "False").lower() in ("true", "1", "t"):  # pragma: no cover
            show = False
        if not export_path:
            export_path = self._app.working_directory
        if not filter_objects:
            filter_objects = []

        v = 0
        fields_to_add = []
        is_intrinsics = True
        if variation_variable in self._app.variable_manager.independent_variables:
            is_intrinsics = False
        for el in variations:
            if is_intrinsics:
                intrinsics[variation_variable] = el
            else:
                self._app[variation_variable] = el
            if plot_type == "Surface":
                plotf = self.create_fieldplot_surface(assignment, quantity, setup, intrinsics)
            elif plot_type == "Volume":
                plotf = self.create_fieldplot_volume(assignment, quantity, setup, intrinsics)
            else:
                plotf = self.create_fieldplot_cutplane(
                    assignment, quantity, setup, intrinsics, filter_objects=filter_objects
                )
            if plotf:
                file_to_add = self.export_field_plot(plotf.name, export_path, plotf.name + str(v))
                if file_to_add:
                    fields_to_add.append(file_to_add)
                plotf.delete()
            v += 1
        model = self.get_model_plotter_geometries(
            generate_mesh=False, get_objects_from_aedt=plot_cad_objs, force_opacity_value=force_opacity_value
        )
        model.off_screen = not show
        if dark_mode:
            model.background_color = [40, 40, 40]
        model.bounding_box = show_bounding
        model.show_grid = show_grid
        model.show_legend = show_legend
        if fields_to_add:
            model.add_frames_from_file(fields_to_add, log_scale=log_scale)
        if export_gif:
            model.gif_file = os.path.join(self._app.working_directory, self._app.project_name + ".gif")
        if view != "isometric" and view in ["xy", "xz", "yz"]:
            model.camera_position = view
        elif view != "isometric":
            self.logger.warning("Wrong view setup. It has to be one of xy, xz, yz, isometric.")

        if scale_min and scale_max:
            model.range_min = scale_min
            model.range_max = scale_max
        if zoom:
            model.zoom = zoom
        if show or export_gif:
            model.animate()
        return model

    @pyaedt_function_handler(plotname="plot_name", variation_list="variations")
    def animate_fields_from_aedtplt(
        self,
        plot_name,
        plot_folder=None,
        variation_variable="Phase",
        variations=["0deg"],
        project_path="",
        export_gif=False,
        show=True,
        dark_mode=False,
        show_bounding=False,
        show_grid=False,
    ):
        """Generate a field plot to an image file (JPG or PNG) using PyVista.

        .. note::
           The PyVista module rebuilds the mesh and the overlap fields on the mesh.

        Parameters
        ----------
        plot_name : str
            Name of the plot or the name of the object.
        plot_folder : str, optional
            Name of the folder in which the plot resides. The default
            is ``None``.
        variation_variable : str, optional
            Variable to vary. The default is ``"Phase"``.
        variations : list, optional
            List of variation values with units. The default is
            ``["0deg"]``.
        project_path : str, optional
            Path for the export. The default is ``""``, in which case the file is exported
            to the working directory.
        export_gif : bool, optional
             Whether to export the GIF file. The default is ``False``.
        show : bool, optional
             Generate the animation without showing an interactive plot.  The default is ``True``.
        dark_mode : bool, optional
            Whether to display the model in dark mode or not. The default is ``False``.
        show_grid : bool, optional
            Whether to display the axes grid or not. The default is ``False``.
        show_bounding : bool, optional
            Whether to display the axes bounding box or not. The default is ``False``.

        Returns
        -------
        :class:`ansys.aedt.core.generic.plot.ModelPlotter`
            Model Object.
        """
        if not plot_folder:
            self.ofieldsreporter.UpdateAllFieldsPlots()
        else:
            self.ofieldsreporter.UpdateQuantityFieldsPlots(plot_folder)

        fields_to_add = []
        if not project_path:
            project_path = self._app.working_directory
        for el in variations:
            if plot_name in self.field_plots and variation_variable in self.field_plots[plot_name].intrinsics:
                self.field_plots[plot_name].intrinsics[variation_variable] = el
                self.field_plots[plot_name].update()
            else:
                self._app._odesign.ChangeProperty(
                    [
                        "NAME:AllTabs",
                        [
                            "NAME:FieldsPostProcessorTab",
                            ["NAME:PropServers", "FieldsReporter:" + plot_name],
                            ["NAME:ChangedProps", ["NAME:" + variation_variable, "Value:=", el]],
                        ],
                    ]
                )
            fields_to_add.append(
                self.export_field_plot(
                    plot_name, project_path, plot_name + variation_variable + str(el), file_format="case"
                )
            )

        model = self.get_model_plotter_geometries(generate_mesh=False)
        model.off_screen = not show
        if dark_mode:
            model.background_color = [40, 40, 40]
        model.bounding_box = show_bounding
        model.show_grid = show_grid
        if fields_to_add:
            model.add_frames_from_file(fields_to_add)
        if export_gif:
            model.gif_file = os.path.join(self._app.working_directory, self._app.project_name + ".gif")

        if show or export_gif:
            model.animate()
        return model

    @pyaedt_function_handler()
    def create_3d_plot(
        self,
        solution_data,
        nominal_sweep=None,
        nominal_value=None,
        primary_sweep="Theta",
        secondary_sweep="Phi",
        snapshot_path=None,
        show=True,
    ):
        """Create a 3D plot using Matplotlib.

        Parameters
        ----------
        solution_data : :class:`ansys.aedt.core.modules.solutions.SolutionData`
            Input data for the solution.
        nominal_sweep : str, optional
            Name of the nominal sweep. The default is ``None``.
        nominal_value : str, optional
            Value for the nominal sweep. The default is ``None``.
        primary_sweep : str, optional
            Primary sweep. The default is ``"Theta"``.
        secondary_sweep : str, optional
            Secondary sweep. The default is ``"Phi"``.
        snapshot_path : str, optional
            Full path to image file if a snapshot is needed.
            The default is ``None``.
        show : bool, optional
            Whether if show the plot or not. Default is set to `True`.

        Returns
        -------
         bool
             ``True`` when successful, ``False`` when failed.
        """
        if nominal_value:
            solution_data.intrinsics[nominal_sweep] = nominal_value
        if nominal_value:
            solution_data.primary_sweep = primary_sweep
        return solution_data.plot_3d(
            x_axis=primary_sweep, y_axis=secondary_sweep, snapshot_path=snapshot_path, show=show
        )

    @pyaedt_function_handler(frames_list="frames", output_gif_path="gif_path")
    def plot_scene(
        self,
        frames,
        gif_path,
        norm_index=0,
        dy_rng=0,
        fps=30,
        show=True,
        view="yz",
        zoom=2.0,
        convert_fields_in_db=False,
        log_multiplier=10.0,
    ):
        """Plot the current model 3D scene with overlapping animation coming from a file list and save the gif.

        Parameters
        ----------
        frames : list or str
            File list containing animation frames to plot in CSV format or
            path to a text index file containing the full path to CSV files.
        gif_path : str
            Full path for outputting the GIF file.
        norm_index : int, optional
            Frame to use to normalize your images.
            Data is already saved as dB : 100 for usual traffic scenes.
        dy_rng : int, optional
            Specify how many dB below you would like to specify the range_min.
            Tweak this a couple of times with small number of frames.
        fps : int, optional
            Frames per Second.
        show : bool, optional
            Either if show or only export gif.
        view : str, optional
           View to export. Options are ``"isometric"``, ``"xy"``, ``"xz"``, and ``"yz"``.
           The default is ``"isometric"``.
        zoom : float, optional
            Default zoom. Default Value is `2`.
        convert_fields_in_db : bool, optional
            Either if convert the fields before plotting in dB. Default Value is `False`.
        log_multiplier : float, optional
            Field multiplier if field in dB. Default Value is `10.0`.

        Returns
        -------
        """
        if isinstance(frames, str) and os.path.exists(frames):
            with open_file(frames, "r") as f:
                lines = f.read()
                temp_list = lines.splitlines()
            frames_paths_list = [i for i in temp_list]
        elif isinstance(frames, str):
            self.logger.error("Path doesn't exists")
            return False
        else:
            frames_paths_list = frames
        scene = self.get_model_plotter_geometries(generate_mesh=False)

        norm_data = np.loadtxt(frames_paths_list[norm_index], skiprows=1, delimiter=",")
        norm_val = norm_data[:, -1]
        v_max = np.max(norm_val)
        v_min = v_max - dy_rng
        scene.add_frames_from_file(frames_paths_list, log_scale=False, color_map="jet", header_lines=1, opacity=0.8)

        # Specifying the attributes of the scene through the ModelPlotter object
        scene.off_screen = not show
        if view != "isometric" and view in ["xy", "xz", "yz"]:
            scene.camera_position = view
        scene.range_min = v_min
        scene.range_max = v_max
        scene.show_grid = False
        scene.windows_size = [1920, 1080]
        scene.show_legend = False
        scene.show_boundingbox = False
        scene.legend = False
        scene.frame_per_seconds = fps
        scene.zoom = zoom
        scene.bounding_box = False
        scene.color_bar = False
        scene.gif_file = gif_path  # This GIF file may be a bit slower so it can be speed it up a bit
        scene.convert_fields_in_db = convert_fields_in_db
        scene.log_multiplier = log_multiplier
        scene.animate()
