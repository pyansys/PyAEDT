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
This module contains these classes: `FieldPlot`, `PostProcessor`, and `SolutionData`.

This module provides all functionalities for creating and editing plots in the 3D tools.

"""


from collections import defaultdict
import csv
import os
import tempfile
import warnings

from ansys.aedt.core.generic.general_methods import open_file
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler

try:
    import pandas as pd
except ImportError:  # pragma: no cover
    warnings.warn(
        "The Matplotlib module is required to run functionalities of FieldSummary.\n"
        "Install with \n\npip install matplotlib"
    )
    pd = None

TOTAL_QUANTITIES = [
    "HeatFlowRate",
    "RadiationFlow",
    "ConductionHeatFlow",
    "ConvectiveHeatFlow",
    "MassFlowRate",
    "VolumeFlowRate",
    "SurfJouleHeatingDensity",
]
AVAILABLE_QUANTITIES = [
    "Temperature",
    "SurfTemperature",
    "HeatFlowRate",
    "RadiationFlow",
    "ConductionHeatFlow",
    "ConvectiveHeatFlow",
    "HeatTransCoeff",
    "HeatFlux",
    "RadiationFlux",
    "Speed",
    "Ux",
    "Uy",
    "Uz",
    "SurfUx",
    "SurfUy",
    "SurfUz",
    "Pressure",
    "SurfPressure",
    "MassFlowRate",
    "VolumeFlowRate",
    "MassFlux",
    "ViscosityRatio",
    "WallYPlus",
    "TKE",
    "Epsilon",
    "Kx",
    "Ky",
    "Kz",
    "SurfElectricPotential",
    "ElectricPotential",
    "SurfCurrentDensity",
    "CurrentDensity",
    "SurfCurrentDensityX",
    "SurfCurrentDensityY",
    "SurfCurrentDensityZ",
    "CurrentDensityX",
    "CurrentDensityY",
    "CurrentDensityZ",
    "SurfJouleHeatingDensity",
    "JouleHeatingDensity",
]


class FieldSummary:
    """Provides Icepak field summary methods."""

    def __init__(self, app):
        self._app = app
        self.calculations = []

    @pyaedt_function_handler()
    def add_calculation(
        self,
        entity,
        geometry,
        geometry_name,
        quantity,
        normal="",
        side="Default",
        mesh="All",
        ref_temperature="AmbientTemp",
        time="0s",
    ):
        """
        Add an entry in the field summary calculation requests.

        Parameters
        ----------
        entity : str
            Type of entity to perform the calculation on. Options are
             ``"Boundary"``, ``"Monitor``", and ``"Object"``.
             (``"Monitor"`` is available in AEDT 2024 R1 and later.)
        geometry : str
            Location to perform the calculation on. Options are
            ``"Surface"`` and ``"Volume"``.
        geometry_name : str or list of str
            Objects to perform the calculation on. If a list is provided,
            the calculation is performed on the combination of those
            objects.
        quantity : str
            Quantity to compute.
        normal : list of floats
            Coordinate values for direction relative to normal. The default is ``""``,
            in which case the normal to the face is used.
        side : str, optional
            String containing which side of the face to use. The default is
            ``"Default"``. Options are ``"Adjacent"``, ``"Combined"``, and
            `"Default"``.
        mesh : str, optional
            Surface meshes to use. The default is ``"All"``. Options are ``"All"`` and
            ``"Reduced"``.
        ref_temperature : str, optional
            Reference temperature to use in the calculation of the heat transfer
            coefficient. The default is ``"AmbientTemp"``.
        time : str, optional
            Timestep to get the data from. Default is ``"0s"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if quantity not in AVAILABLE_QUANTITIES:
            raise AttributeError(
                f"Quantity {quantity} is not supported. Available quantities are:\n{', '.join(AVAILABLE_QUANTITIES)}"
            )
        if isinstance(normal, list):
            if not isinstance(normal[0], str):
                normal = [str(i) for i in normal]
            normal = ",".join(normal)
        if isinstance(geometry_name, str):
            geometry_name = [geometry_name]
        calc_args = [
            entity,
            geometry,
            ",".join(geometry_name),
            quantity,
            normal,
            side,
            mesh,
            ref_temperature,
            False,
        ]  # TODO : last argument not documented
        if self._app.solution_type == "Transient":
            calc_args = [time] + calc_args
        self.calculations.append(calc_args)
        return True

    @pyaedt_function_handler(IntrinsincDict="intrinsics", setup_name="setup", design_variation="variation")
    def get_field_summary_data(self, setup=None, variation=None, intrinsics="", pandas_output=False):
        """
        Get  field summary output computation.

        Parameters
        ----------
        setup : str, optional
            Setup name to use for the computation. The
            default is ``None``, in which case the nominal variation is used.
        variation : dict, optional
            Dictionary containing the design variation to use for the computation.
            The default is  ``{}``, in which case nominal variation is used.
        intrinsics : str, optional
            Intrinsic values to use for the computation. The default is ``""``,
            which is suitable when no frequency needs to be selected.
        pandas_output : bool, optional
            Whether to use pandas output. The default is ``False``, in
            which case the dictionary output is used.

        Returns
        -------
        dict or pandas.DataFrame
            Output type depending on the Boolean ``pandas_output`` parameter.
            The output consists of information exported from the field summary.
        """
        if variation is None:
            variation = {}
        with tempfile.NamedTemporaryFile(mode="w+", delete=False) as temp_file:
            temp_file.close()
            self.export_csv(temp_file.name, setup, variation, intrinsics)
            with open_file(temp_file.name, "r") as f:
                for _ in range(4):
                    _ = next(f)
                reader = csv.DictReader(f)
                out_dict = defaultdict(list)
                for row in reader:
                    for key in row.keys():
                        out_dict[key].append(row[key])
            os.remove(temp_file.name)
            if pandas_output:
                if pd is None:
                    raise ImportError("pandas package is needed.")
                df = pd.DataFrame.from_dict(out_dict)
                for col in ["Min", "Max", "Mean", "Stdev", "Total"]:
                    if col in df.columns:
                        df[col] = df[col].astype(float)
                return df
        return out_dict

    @pyaedt_function_handler(filename="output_file", design_variation="variations", setup_name="setup")
    def export_csv(self, output_file, setup=None, variations=None, intrinsics=""):
        """
        Get the field summary output computation.

        Parameters
        ----------
        output_file : str
            Path and filename to write the output file to.
        setup : str, optional
            Setup name to use for the computation. The
            default is ``None``, in which case the nominal variation is used.
        variations : dict, optional
            Dictionary containing the design variation to use for the computation.
            The default is  ``{}``, in which case the nominal variation is used.
        intrinsics : str, optional
            Intrinsic values to use for the computation. The default is ``""``,
            which is suitable when no frequency needs to be selected.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if variations is None:
            variations = {}
        if not setup:
            setup = self._app.nominal_sweep
        dv_string = ""
        for el in variations:
            dv_string += el + "='" + variations[el] + "' "
        self._create_field_summary(setup, dv_string)
        self._app.osolution.ExportFieldsSummary(
            [
                "SolutionName:=",
                setup,
                "DesignVariationKey:=",
                dv_string,
                "ExportFileName:=",
                output_file,
                "IntrinsicValue:=",
                intrinsics,
            ]
        )
        return True

    @pyaedt_function_handler()
    def _create_field_summary(self, setup, variation):
        arg = ["SolutionName:=", setup, "Variation:=", variation]
        for i in self.calculations:
            arg.append("Calculation:=")
            arg.append(i)
        self._app.osolution.EditFieldsSummarySetting(arg)
