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
import json
from pathlib import Path
import shutil

from ansys.aedt.core.generic.constants import unit_converter
from ansys.aedt.core.generic.errors import AEDTRuntimeError
from ansys.aedt.core.generic.general_methods import check_and_download_folder
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.generic.settings import settings
from ansys.aedt.core.visualization.advanced.rcs_visualization import MonostaticRCSData

DEFAULT_EXPRESSION = "ComplexMonostaticRCSTheta"


class MonostaticRCSExporter:
    """Class to enable export of radar cross-section (RCS) data from HFSS.

    An instance of this class is returned from the
    :meth:`pyaedt.Hfss.get_monostatic_rcs` method. This class creates a
    ``metadata_file`` that can be passed as argument to instantiate an instance of the
    :class:`pyaedt.generic.rcs_visualization.MonostaticRCSData` class for subsequent analysis and postprocessing.

    Note that this class is derived from the :class:`MonostaticRCSData` class and can be used directly for
    RCS postprocessing, but it remains as a property of the :class:`pyaedt.Hfss` application.

    Parameters
    ----------
    app : :class:`pyaedt.Hfss`
        HFSS application instance.
    setup_name : str, optional
        Name of the setup. Make sure to build a setup string in the form of ``"SetupName : SetupSweep"``.
        The default is ``None``, in which case only the geometry is exported.
    frequencies : list, optional
        Frequency list to export. Specify either a list of strings with units or a list of floats in Hertz units.
        For example, ``["9GHz", 9e9]``. The default is ``None``, in which case only the geometry is exported.
    expression : str, optional
        Monostatic expression name. The default value is ``"ComplexMonostaticRCSTheta"``.
    variations : dict, optional
        Dictionary of all families including the primary sweep. The default value is ``None``.
    overwrite : bool, optional
        Whether to overwrite the existing far field solution data. The default is ``True``.

    Examples
    --------
    >>> import ansys.aedt.core
    >>> app = ansys.aedt.core.Hfss(version="2025.1", design="Antenna")
    >>> setup_name = "Setup1 : LastAdaptive"
    >>> frequencies = [77e9]
    >>> sphere = "3D"
    >>> data = app.get_monostatic_rcs(frequencies,setup_name,sphere)
    >>> data.plot_3d(quantity_format="dB10")
    """

    def __init__(
        self,
        app,
        setup_name=None,
        frequencies=None,
        expression=None,
        variations=None,
        overwrite=True,
    ):
        # Public
        self.setup_name = setup_name
        self.solution = ""
        self.expression = expression
        if not self.expression:
            self.expression = "ComplexMonostaticRCSTheta"

        if not variations:
            variations = app.available_variations.nominal_w_values_dict_w_dependent
        else:
            # Set variation to Nominal
            for var_name, var_value in variations.items():
                app[var_name] = var_value

        self.variations = variations
        self.overwrite = overwrite

        if frequencies and not isinstance(frequencies, list):
            self.frequencies = [frequencies]
        else:
            self.frequencies = frequencies
        self.data_file = None

        # Private
        self.__app = app
        self.__model_info = {}
        self.__rcs_data = None
        self.__metadata_file = ""
        self.__frequency_unit = self.__app.units.frequency

        self.__column_name = copy.deepcopy(self.expression)

    @property
    def model_info(self):
        """List of models."""
        return self.__model_info

    @property
    def rcs_data(self):
        """Monostatic RCS data."""
        return self.__rcs_data

    @property
    def metadata_file(self):
        """Metadata file."""
        return self.__metadata_file

    @property
    def column_name(self):
        """Column name."""
        return self.__column_name

    @column_name.setter
    def column_name(self, value):
        """Column name."""
        self.__column_name = value

    @pyaedt_function_handler()
    def get_monostatic_rcs(self):
        """Get RCS solution data.

        Returns
        -------
        :class:`ansys.aedt.core.modules.solutions.SolutionData`
            Solution Data object.
        """
        variations = self.variations
        variations["IWaveTheta"] = ["All"]
        variations["IWavePhi"] = ["All"]
        variations["Freq"] = self.frequencies

        solution_data = self.__app.post.get_solution_data(
            expressions=self.expression,
            variations=variations,
            setup_sweep_name=self.setup_name,
            report_category="Monostatic RCS",
        )

        self.__frequency_unit = solution_data.units_sweeps["Freq"]
        solution_data.enable_pandas_output = True
        return solution_data

    @pyaedt_function_handler()
    def export_rcs(self, name="rcs_data", metadata_name="pyaedt_rcs_metadata", only_geometry=False):
        """Export RCS solution data.

        Parameters
        ----------
        name : str, optional
            Name of the RCS data file. The default is ``"rcs_data"``.
        metadata_name : str, optional
            Name of the metadata file. The default is ``"pyaedt_rcs_metadata"``.
        only_geometry : bool, optional
           Export only the geometry. The default is ``False``.

        Returns
        -------
        str
            Metadata file.

        """
        # Output directory
        if not self.setup_name:
            self.setup_name = "Nominal"
        solution_setup_name = self.setup_name.replace(":", "_").replace(" ", "")
        full_setup = f"{solution_setup_name}"
        export_path = Path(self.__app.working_directory) / full_setup
        local_path = Path(settings.remote_rpc_session_temp_folder) / full_setup
        export_path = Path(check_and_download_folder(str(local_path), str(export_path))).resolve()

        if not self.solution:
            self.solution = self.__app.design_name

        file_name = f"{name}_{self.solution}.h5"
        self.data_file = export_path / file_name
        pyaedt_metadata_file = export_path / f"{metadata_name}_{self.solution}.json"

        # Create directory or check if files already exist
        if settings.remote_rpc_session:
            settings.remote_rpc_session.filemanager.makedirs(export_path)
            file_exists = settings.remote_rpc_session.filemanager.pathexists(pyaedt_metadata_file)
        elif not export_path.exists():
            export_path.mkdir(parents=True, exist_ok=True)
            file_exists = False
        else:
            file_exists = pyaedt_metadata_file.exists()

        # Export monostatic RCS
        if self.overwrite or not file_exists:
            # Export geometry
            geometry_path = export_path / "geometry"

            if settings.remote_rpc_session:
                settings.remote_rpc_session.filemanager.makedirs(geometry_path)
            elif not geometry_path.exists():
                geometry_path.mkdir()

            obj_list = self.__create_geometries(geometry_path)
            if obj_list:
                self.__model_info["object_list"] = obj_list

            if only_geometry:
                file_name = None
            else:
                data = self.get_monostatic_rcs()
                if not data or data.number_of_variations != 1:  # pragma: no cover
                    raise AEDTRuntimeError("Data can not be obtained.")

                df = data.full_matrix_real_imag[0] + complex(0, 1) * data.full_matrix_real_imag[1]
                df.index.names = [*data.variations[0].keys(), *data.intrinsics.keys()]
                df = df.reset_index(level=[*data.variations[0].keys()], drop=True)
                df = unit_converter(
                    df, unit_system="Length", input_units=data.units_data[self.expression], output_units="meter"
                )
                df.rename(
                    columns={
                        self.expression: self.column_name,
                    },
                    inplace=True,
                )
                try:
                    df.to_hdf(self.data_file, key="df", mode="w", format="table")
                except ImportError as e:  # pragma: no cover
                    raise AEDTRuntimeError("PyTables is not installed") from e

                if not self.data_file.is_file():
                    raise AEDTRuntimeError("RCS data file not exported.")

        else:
            self.__app.logger.info("Using existing RCS file.")

        items = {
            "solution": self.solution,
            "monostatic_file": file_name,
            "model_units": self.__app.modeler.model_units,
            "frequency_units": self.__frequency_unit,
            "model_info": [],
        }

        if self.model_info and "object_list" in self.model_info:
            items["model_info"] = self.model_info["object_list"]

        try:
            with pyaedt_metadata_file.open("w") as f:
                json.dump(items, f, indent=2)
        except Exception as e:
            raise AEDTRuntimeError(f"An error occurred when writing metadata") from e

        self.__metadata_file = pyaedt_metadata_file
        if not only_geometry:
            self.__rcs_data = MonostaticRCSData(str(pyaedt_metadata_file))
        return pyaedt_metadata_file

    @pyaedt_function_handler()
    def __create_geometries(self, export_path):
        """Export the geometry in OBJ format."""
        self.__app.logger.info("Exporting geometry...")
        export_path = Path(export_path).resolve()
        model_pv = self.__app.post.get_model_plotter_geometries(plot_air_objects=False)
        obj_list = {}
        for obj in model_pv.objects:
            object_name = Path(obj.path).name
            name = Path(object_name).stem
            original_path = Path(obj.path).parent
            new_path = export_path / object_name

            if not new_path.exists():
                shutil.move(str(obj.path), str(export_path))
            else:
                new_path.unlink()
                shutil.move(str(obj.path), str(export_path))

            mtl_file = original_path / f"{name}.mtl"
            if mtl_file.exists():  # pragma: no cover
                mtl_file.unlink()

            obj_list[obj.name] = [
                object_name,
                obj.color,
                obj.opacity,
                obj.units,
            ]
        return obj_list
