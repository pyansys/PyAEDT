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
This module contains the `PostProcessor` class.

It contains all advanced postprocessing functionalities that require Python 3.x packages like NumPy and Matplotlib.
"""

import csv
import os
import re

from ansys.aedt.core.generic.checks import min_aedt_version
from ansys.aedt.core.generic.general_methods import generate_unique_name
from ansys.aedt.core.generic.general_methods import open_file
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.visualization.post.field_summary import FieldSummary
from ansys.aedt.core.visualization.post.field_summary import TOTAL_QUANTITIES
from ansys.aedt.core.visualization.post.post_common_3d import PostProcessor3D


class PostProcessorIcepak(PostProcessor3D):
    """Manages the specific Icepak postprocessing functions.

    .. note::
       Some functionalities are available only when AEDT is running in the graphical mode.

    Parameters
    ----------
    app : :class:`ansys.aedt.core.application.analysis_3d.FieldAnalysis3D`
        Inherited parent object. The parent object must provide the members
        `_modeler`, `_desktop`, `_odesign`, and `logger`.

    """

    def __init__(self, app):
        PostProcessor3D.__init__(self, app)

    @pyaedt_function_handler()
    def create_field_summary(self):
        """
        Create field summary object.

        Returns
        -------
        :class:`ansys.aedt.core.visualization.post.field_summary.FieldSummary`

        """
        return FieldSummary(self._app)

    @pyaedt_function_handler(timestep="time_step", design_variation="variation")
    def get_fans_operating_point(self, export_file=None, setup_name=None, time_step=None, variation=None):
        """Get the operating point of the fans in the design.

        Parameters
        ----------
        export_file : str, optional
            Name of the file to save the operating point of the fans to. The default is
            ``None``, in which case the filename is automatically generated.
        setup_name : str, optional
            Setup name to determine the operating point of the fans. The default is
            ``None``, in which case the first available setup is used.
        time_step : str, optional
            Time, with units, at which to determine the operating point of the fans. The default
            is ``None``, in which case the first available timestep is used. This parameter is
            only relevant in transient simulations.
        variation : str, optional
            Design variation to determine the operating point of the fans from. The default is
            ``None``, in which case the nominal variation is used.

        Returns
        -------
        list
            First element of the list is the CSV filename. The second and third elements
            are the quantities with units describing the operating point of the fans.
            The fourth element is a dictionary with the names of the fan instances
            as keys and lists with volumetric flow rates and pressure rise floats associated
            with the operating point as values.

        References
        ----------
        >>> oModule.ExportFanOperatingPoint

        Examples
        --------
        >>> from ansys.aedt.core import Icepak
        >>> ipk = Icepak()
        >>> ipk.create_fan()
        >>> filename, vol_flow_name, p_rise_name, op_dict= ipk.get_fans_operating_point()
        """
        if export_file is None:
            path = self._app.temp_directory
            base_name = f"{self._app.project_name}_{self._app.design_name}_FanOpPoint"
            export_file = os.path.join(path, base_name + ".csv")
            while os.path.exists(export_file):
                file_name = generate_unique_name(base_name)
                export_file = os.path.join(path, file_name + ".csv")
        if setup_name is None:
            setup_name = f"{self._app.get_setups()[0]} : {self._app.solution_type}"
        if time_step is None:
            time_step = ""
            if self._app.solution_type == "Transient":
                self._app.logger.warning("No timestep is specified. First timestep is exported.")
        else:
            if not self._app.solution_type == "Transient":
                self._app.logger.warning("Simulation is steady-state. Timestep argument is ignored.")
                time_step = ""
        if variation is None:
            variation = ""
        self._app.osolution.ExportFanOperatingPoint(
            [
                "SolutionName:=",
                setup_name,
                "DesignVariationKey:=",
                variation,
                "ExportFilePath:=",
                export_file,
                "Overwrite:=",
                True,
                "TimeStep:=",
                time_step,
            ]
        )
        with open_file(export_file, "r") as f:
            reader = csv.reader(f)
            for line in reader:
                if "Fan Instances" in line:
                    vol_flow = line[1]
                    p_rise = line[2]
                    break
            var = {line[0]: [float(line[1]), float(line[2])] for line in reader}
        return [export_file, vol_flow, p_rise, var]

    @pyaedt_function_handler
    def _parse_field_summary_content(self, fs, setup_name, design_variation, quantity_name):
        content = fs.get_field_summary_data(setup=setup_name, variation=design_variation)
        pattern = r"\[([^]]*)\]"
        match = re.search(pattern, content["Quantity"][0])
        if match:
            content["Unit"] = [match.group(1)]
        else:  # pragma: no cover
            content["Unit"] = [None]

        if quantity_name in TOTAL_QUANTITIES:
            return {i: content[i][0] for i in ["Total", "Unit"]}
        return {i: content[i][0] for i in ["Min", "Max", "Mean", "Stdev", "Unit"]}

    @pyaedt_function_handler(faces_list="faces", quantity_name="quantity", design_variation="variation")
    def evaluate_faces_quantity(
        self, faces, quantity, side="Default", setup_name=None, variations=None, ref_temperature="", time="0s"
    ):
        """Export the field surface output.

        Parameters
        ----------
        faces : list
            List of faces to apply.
        quantity : str
            Name of the quantity to export.
        side : str, optional
            Which side of the mesh face to use. The default is ``Default``.
            Options are ``"Adjacent"``, ``"Combined"``, and ``"Default"``.
        setup_name : str, optional
            Name of the setup and name of the sweep. For example, ``"IcepakSetup1 : SteatyState"``.
            The default is ``None``, in which case the active setup and active sweep are used.
        variations : dict, optional
            Dictionary of parameters defined for the specific setup with values. The default is ``{}``.
        ref_temperature : str, optional
            Reference temperature to use for heat transfer coefficient computation. The default is ``""``.
        time : str, optional
            Timestep to get the data from. Default is ``"0s"``.

        Returns
        -------
        dict
            Output dictionary, which depending on the quantity chosen, contains one
            of these sets of keys:

            - ``"Min"``, ``"Max"``, ``"Mean"``, ``"Stdev"``, and ``"Unit"``
            - ``"Total"`` and ``"Unit"``

        References
        ----------
        >>> oModule.ExportFieldsSummary
        """
        if variations is None:
            variations = {}
        facelist_name = generate_unique_name(quantity)
        self._app.modeler.create_face_list(faces, facelist_name)
        fs = self.create_field_summary()
        fs.add_calculation(
            "Object", "Surface", facelist_name, quantity, side=side, ref_temperature=ref_temperature, time=time
        )
        out = self._parse_field_summary_content(fs, setup_name, variations, quantity)
        self._app.oeditor.Delete(["NAME:Selections", "Selections:=", facelist_name])
        return out

    @pyaedt_function_handler(boundary_name="boundary", quantity_name="quantity", design_variation="variations")
    def evaluate_boundary_quantity(
        self,
        boundary,
        quantity,
        side="Default",
        volume=False,
        setup_name=None,
        variations=None,
        ref_temperature="",
        time="0s",
    ):
        """Export the field output on a boundary.

        Parameters
        ----------
        boundary : str
            Name of boundary to perform the computation on.
        quantity : str
            Name of the quantity to export.
        side : str, optional
            Side of the mesh face to use. The default is ``"Default"``.
            Options are ``"Adjacent"``, ``"Combined"``, and ``"Default"``.
        volume : bool, optional
            Whether to compute the quantity on the volume or on the surface.
            The default is ``False``, in which case the quantity will be evaluated
            only on the surface .
        setup_name : str, optional
            Name of the setup and name of the sweep. For example, ``"IcepakSetup1 : SteatyState"``.
            The default is ``None``, in which case the active setup and active sweep are used.
        variations : dict, optional
            Dictionary of parameters defined for the specific setup with values. The default is ``{}``.
        ref_temperature : str, optional
            Reference temperature to use for heat transfer coefficient computation. The default is ``""``.
        time : str, optional
            Timestep to get the data from. Default is ``"0s"``.

        Returns
        -------
        dict
            Output dictionary, which depending on the quantity chosen, contains one
            of these sets of keys:
            - ``"Min"``, ``"Max"``, ``"Mean"``, ``"Stdev"``, and ``"Unit"``
            - ``"Total"`` and ``"Unit"``

        References
        ----------
        >>> oModule.ExportFieldsSummary
        """
        if variations is None:
            variations = {}
        fs = self.create_field_summary()
        fs.add_calculation(
            "Boundary",
            ["Surface", "Volume"][int(volume)],
            boundary,
            quantity,
            side=side,
            ref_temperature=ref_temperature,
            time=time,
        )
        return self._parse_field_summary_content(fs, setup_name, variations, quantity)

    @pyaedt_function_handler(monitor_name="monitor", quantity_name="quantity", design_variation="variations")
    @min_aedt_version("2024.1")
    def evaluate_monitor_quantity(
        self, monitor, quantity, side="Default", setup_name=None, variations=None, ref_temperature="", time="0s"
    ):
        """Export monitor field output.

        Parameters
        ----------
        monitor : str
            Name of monitor to perform the computation on.
        quantity : str
            Name of the quantity to export.
        side : str, optional
            Side of the mesh face to use. The default is ``"Default"``.
            Options are ``"Adjacent"``, ``"Combined"``, and ``"Default"``.
        setup_name : str, optional
            Name of the setup and name of the sweep. For example, ``"IcepakSetup1 : SteatyState"``.
            The default is ``None``, in which case the active setup and active sweep are used.
        variations : dict, optional
            Dictionary of parameters defined for the specific setup with values. The default is ``{}``.
        ref_temperature : str, optional
            Reference temperature to use for heat transfer coefficient computation. The default is ``""``.
        time : str, optional
            Timestep to get the data from. Default is ``"0s"``.

        Returns
        -------
        dict
            Output dictionary, which depending on the quantity chosen, contains one
            of these sets of keys:

            - ``"Min"``, ``"Max"``, ``"Mean"``, ``"Stdev"``, and ``"Unit"``
            - ``"Total"`` and ``"Unit"``

        References
        ----------
        >>> oModule.ExportFieldsSummary
        """
        if variations is None:
            variations = {}
        if self._app.monitor.face_monitors.get(monitor, None):
            field_type = "Surface"
        elif self._app.monitor.point_monitors.get(monitor, None):
            field_type = "Volume"
        else:
            raise AttributeError(f"Monitor {monitor} is not found in the design.")
        fs = self.create_field_summary()
        fs.add_calculation(
            "Monitor", field_type, monitor, quantity, side=side, ref_temperature=ref_temperature, time=time
        )
        return self._parse_field_summary_content(fs, setup_name, variations, quantity)

    @pyaedt_function_handler(design_variation="variations")
    def evaluate_object_quantity(
        self,
        object_name,
        quantity_name,
        side="Default",
        volume=False,
        setup_name=None,
        variations=None,
        ref_temperature="",
        time="0s",
    ):
        """Export the field output on or in an object.

        Parameters
        ----------
        object_name : str
            Name of object to perform the computation on.
        quantity_name : str
            Name of the quantity to export.
        side : str, optional
            Side of the mesh face to use. The default is ``"Default"``.
            Options are ``"Adjacent"``, ``"Combined"``, and ``"Default"``.
        volume : bool, optional
            Whether to compute the quantity on the volume or on the surface. The default is ``False``.
        setup_name : str, optional
            Name of the setup and name of the sweep. For example, ``"IcepakSetup1 : SteatyState"``.
            The default is ``None``, in which case the active setup and active sweep are used.
        variations : dict, optional
            Dictionary of parameters defined for the specific setup with values. The default is ``{}``.
        ref_temperature : str, optional
            Reference temperature to use for heat transfer coefficient computation. The default is ``""``.
        time : str, optional
            Timestep to get the data from. Default is ``"0s"``.

        Returns
        -------
        dict
            Output dictionary, which depending on the quantity chosen, contains one
            of these sets of keys:

            - ``"Min"``, ``"Max"``, ``"Mean"``, ``"Stdev"``, and ``"Unit"``
            - ``"Total"`` and ``"Unit"``

        References
        ----------
        >>> oModule.ExportFieldsSummary
        """
        if variations is None:
            variations = {}
        fs = self.create_field_summary()
        fs.add_calculation(
            "Object",
            ["Surface", "Volume"][int(volume)],
            object_name,
            quantity_name,
            side=side,
            ref_temperature=ref_temperature,
            time=time,
        )
        return self._parse_field_summary_content(fs, setup_name, variations, quantity_name)
