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

"""This module contains these classes: ``Q2d``, ``Q3d``, and ``QExtractor``."""

from __future__ import absolute_import  # noreorder

import os
import re
import warnings

from ansys.aedt.core.application.analysis_3d import FieldAnalysis3D
from ansys.aedt.core.application.variables import decompose_variable_value
from ansys.aedt.core.generic.constants import MATRIXOPERATIONSQ2D
from ansys.aedt.core.generic.constants import MATRIXOPERATIONSQ3D
from ansys.aedt.core.generic.general_methods import generate_unique_name
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.generic.settings import settings
from ansys.aedt.core.mixins import CreateBoundaryMixin
from ansys.aedt.core.modeler.geometry_operators import GeometryOperators as go
from ansys.aedt.core.modules.boundary.common import BoundaryObject
from ansys.aedt.core.modules.boundary.q3d_boundary import Matrix
from ansys.aedt.core.modules.setup_templates import SetupKeys


class QExtractor(FieldAnalysis3D, object):
    """Extracts a 2D or 3D field analysis.

    Parameters
    ----------
    FieldAnalysis3D :

    FieldAnalysis2D :

    object :


    """

    @property
    def design_file(self):
        """Design file."""
        design_file = os.path.join(self.working_directory, "design_data.json")
        return design_file

    def __init__(
        self,
        Q3DType,
        project=None,
        design=None,
        solution_type=None,
        setup_name=None,
        version=None,
        non_graphical=False,
        new_desktop=False,
        close_on_exit=False,
        student_version=False,
        machine="",
        port=0,
        aedt_process_id=None,
        remove_lock=False,
    ):
        FieldAnalysis3D.__init__(
            self,
            Q3DType,
            project,
            design,
            solution_type,
            setup_name,
            version,
            non_graphical,
            new_desktop,
            close_on_exit,
            student_version,
            machine,
            port,
            aedt_process_id,
            remove_lock=remove_lock,
        )
        self.matrices = []
        for el in list(self.omatrix.ListReduceMatrixes()):
            self.matrices.append(Matrix(self, el))

    @pyaedt_function_handler()
    def sources(self, matrix_index=0, is_gc_sources=True):
        """List of matrix sources.

        Parameters
        ----------
        matrix_index : int, optional
            Matrix index in matrices list. Default is ``0`` to use main matrix with no reduction.
        is_gc_sources : bool,
            In Q3d, define if to return GC sources or RL sources. Default `True`.

        Returns
        -------
        List
        """
        return self.matrices[matrix_index].sources(is_gc_sources=is_gc_sources)

    @pyaedt_function_handler(source_names="assignment", rm_name="reduced_matrix")
    def insert_reduced_matrix(
        self,
        operation_name,
        assignment=None,
        reduced_matrix=None,
        new_net_name=None,
        new_source_name=None,
        new_sink_name=None,
    ):
        """Insert a new reduced matrix.

        Parameters
        ----------
        operation_name : str
            Name of the operation to create.
        assignment : list, str, optional
            List of sources or nets or arguments needed for the operation. The default
            is ``None``.
        reduced_matrix : str, optional
            Name of the reduced matrix. The default is ``None``.
        new_net_name : str, optional
            Name of the new net. The default is ``None``.
        new_source_name : str, optional
            Name of the new source. The default is ``None``.
        new_sink_name : str, optional
            Name of the new sink. The default is ``None``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.q3d_boundary.Matrix`
            Matrix object.
        """
        if not reduced_matrix:
            reduced_matrix = generate_unique_name(operation_name)
        matrix = Matrix(self, reduced_matrix, operation_name)

        if not new_net_name:
            new_net_name = generate_unique_name("Net")

        if not new_source_name:
            new_source_name = generate_unique_name("Source")

        if not new_sink_name:
            new_sink_name = generate_unique_name("Sink")

        if matrix.create(assignment, new_net_name, new_source_name, new_sink_name):
            self.matrices.append(matrix)
        return matrix

    @pyaedt_function_handler()
    def get_all_sources(self):
        """Get all setup sources.

        Returns
        -------
        list of str
            List of all setup sources.

        References
        ----------
        >>> oModule.GetAllSources
        """
        return self.sources(0, False)

    @pyaedt_function_handler()
    def get_traces_for_plot(
        self,
        get_self_terms=True,
        get_mutual_terms=True,
        first_element_filter=None,
        second_element_filter=None,
        category="C",
    ):
        """Get a list of traces of specified designs ready to use in plot reports.

        Parameters
        ----------
        get_self_terms : bool, optional
            Whether to get self terms. The default is ``True``.
        get_mutual_terms : bool, optional
            Whether to get mutual terms. The default is ``True``.
        first_element_filter : str, optional
            Filter to apply to the first element of the equation.
            This parameter accepts ``*`` and ``?`` as special characters. The default is ``None``.
        second_element_filter : str, optional
            Filter to apply to the second element of the equation.
            This parameter accepts ``*`` and ``?`` as special characters. The default is ``None``.
        category : str
            Plot category name as in the report, including operator.
            The default is ``"C"``, which is the plot category name for capacitance.

        Returns
        -------
        list
            Traces of specified designs ready to use in plot reports.

        Examples
        --------
        >>> from ansys.aedt.core import Q3d
        >>> hfss = Q3d(project_path)
        >>> hfss.get_traces_for_plot(first_element_filter="Bo?1",
        ...                           second_element_filter="GND*", category="C")
        """
        return self.matrices[0].get_sources_for_plot(
            get_self_terms=get_self_terms,
            get_mutual_terms=get_mutual_terms,
            first_element_filter=first_element_filter,
            second_element_filter=second_element_filter,
            category=category,
        )

    @pyaedt_function_handler(setup_name="setup")
    def export_mesh_stats(self, setup, variations="", mesh_path=None, setup_type="CG"):
        """Export mesh statistics to a file.

        Parameters
        ----------
        setup : str
            Setup name.
        variations : str, optional
            Variation list. The default is ``""``.
        mesh_path : str, optional
            Full path to the mesh statistics file. The default is ``None``, in which
            case the working directory is used.
        setup_type : str, optional
            Setup type in Q3D. Options are ``"CG"``, ``"AC RL"``, and ``"DC RL"``. The
            default is ``"CG"``.

        Returns
        -------
        str
            File path.

        References
        ----------
        >>> oDesign.ExportMeshStats
        """
        if not mesh_path:
            mesh_path = os.path.join(self.working_directory, "meshstats.ms")
        self.odesign.ExportMeshStats(setup, variations, setup_type, mesh_path)
        return mesh_path

    @pyaedt_function_handler()
    def edit_sources(
        self,
        cg=None,
        acrl=None,
        dcrl=None,
    ):
        """Set up the source loaded for Q3D or Q2D in multiple sources simultaneously.

        Parameters
        ----------
        cg : dict, optional
            Dictionary of input sources to modify the module and phase of a CG solution.
            Dictionary values can be:
            - 1 Value to set up ``0deg`` as the default
            - 2 Values tuple or list (magnitude and phase)
        acrl : dict, optional
            Dictionary of input sources to modify the module and phase of an ACRL solution.
            Dictionary values can be:
            - 1 Value to set up 0deg as the default
            - 2 Values tuple or list (magnitude and phase)
        dcrl : dict, optional
            Dictionary of input sources to modify the module and phase of a DCRL solution, This
            parameter is only available for Q3D. Dictionary values can be:
            - 1 Value to set up ``0deg`` as the default
            - 2 Values tuple or list (magnitude and phase)

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------
        >>> sources_cg = {"Box1": ("1V", "0deg"), "Box1_2": "1V"}
        >>> sources_acrl = {"Box1:Source1": ("5A", "0deg")}
        >>> sources_dcrl = {"Box1_1:Source2": ("5V", "0deg")}
        >>> hfss.edit_sources(sources_cg,sources_acrl,sources_dcrl)
        """
        setting_AC = []
        setting_CG = []
        setting_DC = []
        if cg:
            net_list = ["NAME:Source Names"]

            excitation = self.excitations

            for key, value in cg.items():
                if key not in excitation:
                    self.logger.error("Not existing net " + key)
                    return False
                else:
                    net_list.append(key)

            if self.default_solution_type == "Q3D Extractor":
                value_list = ["NAME:Source Values"]
                phase_list = ["NAME:Source Values"]
            else:
                value_list = ["NAME:Magnitude"]
                phase_list = ["NAME:Phase"]

            for key, vals in cg.items():
                if isinstance(vals, str):
                    value = vals
                    phase = "0deg"
                else:
                    value = vals[0]
                    if len(vals) == 1:
                        phase = "0deg"
                    else:
                        phase = vals[1]
                value_list.append(value)
                phase_list.append(phase)
            if self.default_solution_type == "Q3D Extractor":
                setting_CG = ["NAME:Cap", "Value Type:=", "N", net_list, value_list, phase_list]
            else:
                setting_CG = ["NAME:CGSources", net_list, value_list, phase_list]
        if acrl:
            source_list = ["NAME:Source Names"]
            unit = "V"
            excitation = self.sources(0, False)
            for key, value in acrl.items():
                if key not in excitation:
                    self.logger.error("Not existing excitation " + key)
                    return False
                else:
                    source_list.append(key)
            if self.default_solution_type == "Q3D Extractor":
                value_list = ["NAME:Source Values"]
                phase_list = ["NAME:Source Values"]
            else:
                value_list = ["NAME:Magnitude"]
                phase_list = ["NAME:Phase"]
            for key, vals in acrl.items():
                if isinstance(vals, str):
                    magnitude = decompose_variable_value(vals)
                    value = vals
                    phase = "0deg"
                else:
                    value = vals[0]
                    magnitude = decompose_variable_value(value)
                    if len(vals) == 1:
                        phase = "0deg"
                    else:
                        phase = vals[1]
                if magnitude[1]:
                    unit = magnitude[1]
                else:
                    value += unit

                value_list.append(value)
                phase_list.append(phase)

            if self.default_solution_type == "Q3D Extractor":
                setting_AC = ["NAME:AC", "Value Type:=", unit, source_list, value_list]
            else:
                setting_AC = ["NAME:RLSources", source_list, value_list, phase_list]
        if dcrl and self.default_solution_type == "Q3D Extractor":
            unit = "V"
            source_list = ["NAME:Source Names"]
            excitation = self.sources(0, False)
            for key, value in dcrl.items():
                if key not in excitation:  # pragma: no cover
                    self.logger.error("Not existing excitation " + key)
                    return False
                else:
                    source_list.append(key)
            if self.default_solution_type == "Q3D Extractor":
                value_list = ["NAME:Source Values"]
            else:  # pragma: no cover
                value_list = ["NAME:Magnitude"]
            for key, vals in dcrl.items():
                magnitude = decompose_variable_value(vals)
                if magnitude[1]:
                    unit = magnitude[1]
                else:
                    vals += unit
                if isinstance(vals, str):
                    value = vals
                else:
                    value = vals[0]
                value_list.append(value)
            setting_DC = ["NAME:DC", "Value Type:=", unit, source_list, value_list]

        if self.default_solution_type == "Q3D Extractor":
            self.osolution.EditSources(setting_AC, setting_CG, setting_DC)
        else:
            self.osolution.EditSources(setting_CG, setting_AC)

        return True

    @pyaedt_function_handler(setup_name="setup")
    def export_matrix_data(
        self,
        file_name,
        problem_type=None,
        variations=None,
        setup=None,
        sweep=None,
        reduce_matrix=None,
        r_unit="ohm",
        l_unit="nH",
        c_unit="pF",
        g_unit="mho",
        freq=None,
        freq_unit=None,
        matrix_type=None,
        export_ac_dc_res=False,
        precision=None,
        field_width=None,
        use_sci_notation=True,
        length_setting="Distributed",
        length="1meter",
    ):
        """Export matrix data.

        Parameters
        ----------
        file_name : str
            Full path to save the matrix data to.
            Options for file extensions are: ``*.m``, ``*.lvl``, ``*.csv``,
            and ``*.txt``.
        problem_type : str, optional
            Problem type. The default value is ``None``, in which case ``"C"`` is
            used. Options are ``"C"``, ``"AC RL"``, and ``"DC RL"``.
        variations : str, optional
            Design variation. The default is ``None``, in which case the
            current nominal variation is used.
        setup : str, optional
            Setup name. The default value is ``None``, in which case the first
            analysis setup is used.
        sweep : str, optional
            Solution frequency. The default is ``None``, in which case
            the default adaptive is used.
        reduce_matrix : str, optional
            Name of the matrix to display.
            Default value is ``"Original"``.
        r_unit : str, optional
            Resistance unit value.
            The default value is ``"ohm"``.
        l_unit : str, optional
            Inductance unit value.
            The default value is ``"nH"``.
        c_unit : str, optional
            Capacitance unit value.
            Default value is ``"pF"``.
        g_unit : str, optional
            Conductance unit value.
            The default value is ``"mho"``.
        freq : str, optional
            Selected frequency.
            The default value is ``"0Hz"``.
        freq_unit : str, optional
            Frequency unit. The default value is ``None``, in which case the
            default unit is used.
        matrix_type : str, optional
            Matrix type. The default is ``None``.
            Options are ``"Couple"``, ``"Maxwell"``, and ``"Spice"``.
        export_ac_dc_res : bool, optional
            Whether to add the AC and DC resistance.
            The default is ``False``.
        precision : int, optional
            Precision format.
            The default value is ``15``.
        field_width : int, optional
            Field Width.
            The default value is ``20``.
        use_sci_notation : bool, optional
            Use sci notation.
            Whether to use scientific notation.
            The default value is ``True``.  When ``False``, the display format is used.
        length_setting : str, optional
            Length setting if the design si 2D.
            The default value is ``"Distributed"``.
        length : str, optional
            Length.
            The default value is ``"1meter"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if os.path.splitext(file_name)[1] not in [".m", ".lvl", ".csv", ".txt"]:
            self.logger.error("Extension is invalid. Possible extensions are *.m, *.lvl, *.csv, and *.txt.")
            return False

        if not self.modeler._is3d:
            if problem_type is None:
                problem_type = "CG"
                if matrix_type is None:
                    matrix_type = "Maxwell, Spice, Couple"
                else:
                    matrix_type_array = matrix_type.split(", ")
                    if not [x for x in matrix_type_array if x in ["Maxwell", "Spice", "Couple"]]:
                        self.logger.error("Invalid input matrix type. Possible values are Maxwell, Spice, and Couple.")
                        return False
            else:
                problem_type_array = problem_type.split(", ")
                if [x for x in problem_type_array if x in ["CG", "RL"]]:
                    if "CG" in problem_type_array:
                        if matrix_type is None:
                            matrix_type = "Maxwell, Spice, Couple"
                    else:
                        if matrix_type is None:
                            matrix_type = "Maxwell, Couple"
                        else:
                            matrix_type_array = matrix_type.split(", ")
                            if [x for x in matrix_type_array if x == "Spice"]:
                                self.logger.error("Spice can't be a matrix type if problem type is RL.")
                                return False
                else:
                    self.logger.error("Invalid problem type. Possible values are CG and RL.")
                    return False

        else:
            if problem_type is None:
                problem_type = "C"
                if matrix_type is None:
                    matrix_type = "Maxwell, Spice, Couple"
                else:
                    matrix_type_array = matrix_type.split(", ")
                    if not [x for x in matrix_type_array if x in ["Maxwell", "Spice", "Couple"]]:
                        self.logger.error("Invalid input matrix type. Possible values are Maxwell, Spice, and Couple.")
                        return False
            else:
                problem_type_array = problem_type.split(", ")
                if [x for x in problem_type_array if x in ["C", "AC RL", "DC RL"]]:
                    if "C" in problem_type_array:
                        if matrix_type is None:
                            matrix_type = "Maxwell, Spice, Couple"
                    else:
                        if matrix_type is None:
                            matrix_type = "Maxwell, Couple"
                        else:
                            matrix_type_array = matrix_type.split(", ")
                            if [x for x in matrix_type_array if x == "Spice"]:
                                self.logger.error("Spice can't be a matrix type if problem type is AC RL or DC RL.")
                                return False
                else:
                    self.logger.error("Invalid problem type. Possible values are C, AC RL, and DC RL.")
                    return False

        if variations is None:
            nominal_values = self.available_variations.get_independent_nominal_values()
            if not nominal_values:
                variations = ""
            else:
                variations_list = []
                for x in range(0, len(nominal_values)):
                    variation = f"{list(nominal_values.keys())[x]}=" f"'{list(nominal_values.values())[x]}'"
                    variations_list.append(variation)
                variations = ",".join(variations_list)

        if setup is None:
            setup = self.active_setup
        elif setup != self.active_setup:
            self.logger.error("Setup named: %s is invalid. Provide a valid analysis setup name.", setup)
            return False
        if sweep is None:
            sweep = self.design_solutions.default_adaptive
        else:
            sweep_array = [x.split(": ")[1] for x in self.existing_analysis_sweeps]
            if sweep.replace(" ", "") not in sweep_array:
                self.logger.error("Sweep is invalid. Provide a valid sweep.")
                return False
        analysis_setup = setup + " : " + sweep.replace(" ", "")

        if reduce_matrix is None:
            reduce_matrix = "Original"
        else:
            if self.matrices:
                if not [matrix for matrix in self.matrices if matrix.name == reduce_matrix]:
                    self.logger.error("Matrix doesn't exist. Provide an existing matrix.")
                    return False
            else:  # pragma: no cover
                self.logger.error("List of matrix parameters is empty. Cannot export a valid matrix.")
                return False

        if r_unit is None:
            r_unit = "ohm"
        else:
            if not r_unit.endswith("ohm"):
                self.logger.error("Provide a valid unit for resistor.")
                return False

        if not l_unit.endswith("H"):
            self.logger.error("Provide a valid unit for inductor.")
            return False

        if c_unit not in ["fF", "pF", "nF", "uF", "mF", "farad"]:
            self.logger.error("Provide a valid unit for capacitance.")
            return False

        if g_unit is None:
            g_unit = "mho"
        else:
            if g_unit not in [
                "fSie",
                "pSie",
                "nSie",
                "uSie",
                "mSie",
                "Sie",
                "kSie",
                "megSie",
                "mho",
                "perohm",
                "apV",
            ]:
                self.logger.error("Provide a valid unit for conductance.")
                return False

        if freq is None:
            freq = (
                re.compile(r"(\d+)\s*(\w+)")
                .match(
                    self.modeler._odesign.GetChildObject("Analysis").GetChildObject(setup).GetPropValue("Adaptive Freq")
                )
                .groups()[0]
            )
        else:
            if freq_unit != self.odesktop.GetDefaultUnit("Frequency") and freq_unit is not None:
                freq = go.parse_dim_arg(f"{freq}{freq_unit}", self.odesktop.GetDefaultUnit("Frequency"))

        if export_ac_dc_res is None:
            export_ac_dc_res = False

        if precision is None:
            precision = 15
        else:
            if not isinstance(precision, int):
                self.logger.error("Precision type must be integer.")
                return False

        if field_width is None:
            field_width = 20
        else:
            if not isinstance(field_width, int):
                self.logger.error("Field width type must be integer.")
                return False

        if use_sci_notation is None:
            use_sci_notation = 1
        else:
            if use_sci_notation:
                use_sci_notation = 1
            else:
                use_sci_notation = 0

        if not self.modeler._is3d:
            if length_setting not in ["Distributed", "Lumped"]:
                self.logger.error("Length setting is invalid.")
                return False
            if length is None:
                length = "1meter"
            else:
                if re.compile(r"(\d+)\s*(\w+)").match(length).groups()[1] not in [
                    "fm",
                    "pm",
                    "nm",
                    "um",
                    "mm",
                    "cm",
                    "dm",
                    "meter",
                    "km",
                    "copper_oz",
                    "ft",
                    "in",
                    "mil",
                    "mile",
                    "mileNaut",
                    "mileTerr",
                    "uin",
                    "yd",
                ]:
                    self.logger.error("Unit length is invalid.")
                    return False
            try:
                self.odesign.ExportMatrixData(
                    file_name,
                    problem_type,
                    variations,
                    analysis_setup,
                    reduce_matrix,
                    r_unit,
                    l_unit,
                    c_unit,
                    g_unit,
                    freq,
                    length_setting,
                    length,
                    matrix_type,
                    0,
                    precision,
                    field_width,
                    use_sci_notation,
                )
                return True
            except Exception:  # pragma: no cover
                self.logger.error("Export of matrix data was unsuccessful.")
                return False
        else:
            try:
                self.odesign.ExportMatrixData(
                    file_name,
                    problem_type,
                    variations,
                    analysis_setup,
                    reduce_matrix,
                    r_unit,
                    l_unit,
                    c_unit,
                    g_unit,
                    freq,
                    matrix_type,
                    0,
                    export_ac_dc_res,
                    precision,
                    field_width,
                    use_sci_notation,
                )
                return True
            except Exception:  # pragma: no cover
                self.logger.error("Export of matrix data was unsuccessful.")
                return False

    @pyaedt_function_handler(
        file_name="output_file",
        setup_name="setup",
        matrix_name="matrix",
        num_cells="cells",
        freq="frequency",
        model_name="model",
    )
    def export_equivalent_circuit(
        self,
        output_file,
        setup=None,
        sweep=None,
        variations=None,
        matrix=None,
        cells=2,
        user_changed_settings=True,
        include_cap=True,
        include_cond=True,
        include_dcr=False,
        include_dcl=False,
        include_acr=False,
        include_acl=False,
        include_r=True,
        include_l=True,
        add_resistance=False,
        parse_pin_names=False,
        export_distributed=True,
        lumped_length="1meter",
        rise_time_value=None,
        rise_time_unit=None,
        coupling_limit_type=None,
        cap_limit=None,
        ind_limit=None,
        res_limit=None,
        cond_limit=None,
        model=None,
        frequency=0,
        file_type="HSPICE",
        include_cpp=False,
    ):
        """Export matrix data.

        Parameters
        ----------
        output_file : str
            Full path for saving the matrix data to.
            Options for file extensions are CIR, SML, SP, PKG, SPC, LIB, CKT, BSP,
            DML, and ICM.
        setup : str, optional
            Setup name.
            The default value is ``None``, in which case the first analysis setup is used.
        sweep : str, optional
            Solution frequency. The default is ``None``, in which case
            the default adaptive is used.
        variations : list or str, optional
            Design variation. The default is ``None``, in which case the
            current nominal variation is used. If you provide a
            design variation, use the format ``{Name}:{Value}``.
        matrix : str, optional
            Name of the matrix to show. The default is ``"Original"``.
        cells : int, optional
            Number of cells in export.
            Default value is 2.
        user_changed_settings : bool, optional
            Whether user has changed settings or not, defaulted to True.
            Default value is False.
        include_cap : bool, optional
            Include Capacitance.
            Default value is True.
        include_cond : bool, optional
            Include Conductance.
            Default value is True.
        coupling_limit_type : int, optional
            Coupling limit types.
            Values can be: ``"By Value" -> 0`` or ``"By Fraction Of Self Term" -> 1``.
            If None, no coupling limits are set.
            Default value is None.
        include_dcr : bool, optional
            Flag indicates whether to export DC resistance matrix.
            Default value is ``False``.
        include_dcl : bool, optional
            Flag indicates whether to export DC Inductance matrix.
            Default value is ``False``.
        include_acr : bool, optional
            Flag indicates whether to export AC resistance matrix.
            Default value is ``False``.
        include_acl : bool, optional
            Flag indicates whether to export AC inductance matrix.
            Default value is ``False``.
        include_r : bool, optional
            Flag indicates whether to export resistance.
            Default value is True.
        include_l : bool, optional
            Flag indicates whether to export inductance.
            Default value is True.
        add_resistance : bool, optional
            Adds the DC and AC resistance.
            Default value is True.
        parse_pin_names : bool, optional
            Parse pin names.
            Default value is False.
        export_distributed : bool, optional
            Flag to tell whether to export in distributed mode or Lumped mode.
            Default value is True.
        lumped_length : str, optional
            Length of the design.
            Default value is 1 meter.
        rise_time_value : str, optional
            Rise time to calculate the number of cells.
            Default value is 1e-09.
        rise_time_unit : str, optional
            Rise time unit.
            Default is s.
        cap_limit : str, optional
            Capacitance limit.
            Default value is 1pF if coupling_limit_type is 0.
            Default value is 0.01 if coupling_limit_type is 1.
        cond_limit : str, optional
            Conductance limit.
            Default value is 1mSie if coupling_limit_type is 0.
            Default value is 0.01 if coupling_limit_type is 1.
        res_limit : str, optional
            Resistance limit.
            Default value is 1ohm if coupling_limit_type is 0.
            Default value is 0.01 if coupling_limit_type is 1.
        ind_limit : str, optional
            Inductance limit.
            Default value is 1nH if coupling_limit_type is 0.
            Default value is 0.01 if coupling_limit_type is 1.
        model : str, optional
            Model name or name of the sub circuit (Optional).
            If None then file_name is considered as model name.
        frequency : str, optional
            Sweep frequency in Hz.
            Default value is 0.
        file_type : str, optional
            The type of file format.
            Type of HSPICE file format. (All HSPICE file formats have the same extension,
            which is ``*.sp``.) Options are:
            "Hspice": simple HSPICE file format.
            "Welement": Nexxim/HSPICE W Element file format
            "RLGC": Nexxim/HSPICE RLGC W Element file format
            Default value is Hspice.
        include_cpp : bool, optional
            Whether to include chip package control.
            Default value is False.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.ExportCircuit

        Examples
        --------
        >>> from ansys.aedt.core import Q3d
        >>> aedtapp = Q3d()
        >>> box = aedtapp.modeler.create_box([30, 30, 30],[10, 10, 10],name="mybox")
        >>> net = aedtapp.assign_net(box,"my_net")
        >>> source = aedtapp.assign_source_to_objectface(box.bottom_face_z.id, axisdir=0,
        ...     source_name="Source1", net_name=net.name)
        >>> sink = aedtapp.assign_sink_to_objectface(box.top_face_z.id,direction=0,name="Sink1",net_name=net.name)
        >>> aedtapp["d"] = "20mm"
        >>> aedtapp.modeler.duplicate_along_line(objid="Box1",vector=[0, "d", 0])
        >>> mysetup = aedtapp.create_setup()
        >>> aedtapp.analyze_setup(mysetup.name)
        >>> aedtapp.export_equivalent_circuit(output_file="test_export_circuit.cir",
        ...                                   setup=mysetup.name,sweep="LastAdaptive", variations=["d: 20mm"])
        """
        if os.path.splitext(output_file)[1] not in [
            ".cir",
            ".sml",
            ".sp",
            ".pkg",
            ".spc",
            ".lib",
            ".ckt",
            ".bsp",
            ".dml",
            ".icm",
        ]:
            self.logger.error(
                "Extension is invalid. Possible extensions are .cir, .sml, .sp, .pkg, .spc,"
                " .lib, .ckt, .bsp, .dml, .icm."
            )
            return False

        if setup is None:
            setup = self.active_setup
        elif setup != self.active_setup:
            self.logger.error("Setup named: %s is invalid. Provide a valid analysis setup name.", setup)
            return False
        if sweep is None:
            sweep = self.design_solutions.default_adaptive
        else:
            sweep_array = [x.split(": ")[1] for x in self.existing_analysis_sweeps]
            if sweep.replace(" ", "") not in sweep_array:
                self.logger.error("Sweep is invalid. Provide a valid sweep.")
                return False
        analysis_setup = setup + " : " + sweep.replace(" ", "")

        if variations is None:
            nominal_values = self.available_variations.get_independent_nominal_values()

            if not nominal_values:
                variations = ""
            else:
                variations_list = []
                for x in range(0, len(nominal_values)):
                    variation = f"{list(nominal_values.keys())[x]}=" f"'{list(nominal_values.values())[x]}'"
                    variations_list.append(variation)
                variations = ",".join(variations_list)
        else:
            variations_list = []
            if not isinstance(variations, list):
                self.logger.error("Variations must be provided as a list.")
                return False
            for x in range(0, len(variations)):
                name = variations[x].replace(" ", "").split(":")[0]
                value = variations[x].replace(" ", "").split(":")[1]
                solved_variations = self.post.get_solution_data(variations={name: [value]})

                if not solved_variations or not solved_variations.variations[0]:
                    self.logger.error("Provided variation doesn't exist.")
                    return False
                variation = f"{name}='{value}'"
                variations_list.append(variation)
            variations = ",".join(variations_list)

        if matrix is None:
            matrix = "Original"
        else:
            if self.matrices:
                if not [matrix_object for matrix_object in self.matrices if matrix_object.name == matrix]:
                    self.logger.error("Matrix doesn't exist. Provide an existing matrix.")
                    return False
            else:
                self.logger.error("List of matrix parameters is empty. Cannot export a valid matrix.")
                return False

        coupling_limits = ["NAME:CouplingLimits", "CouplingLimitType:="]
        coupling_limit_value = "None"
        if coupling_limit_type:
            if coupling_limit_type not in [0, 1]:
                self.logger.error('Possible values are 0 = "By Value" or 1 = "By Fraction Of Self Term".')
                return False
            elif coupling_limit_type == 0:
                coupling_limit_value = "By Value"
            elif coupling_limit_type == 1:
                coupling_limit_value = "By Fraction Of Self Term"

            coupling_limits.append(coupling_limit_value)

            if cond_limit is None and coupling_limit_type == 0:
                cond_limit = "1mSie"
            elif cond_limit is None and coupling_limit_type == 1:
                cond_limit = "0.01"
            elif cond_limit is not None:
                if decompose_variable_value(cond_limit)[1] not in [
                    "fSie",
                    "pSie",
                    "nSie",
                    "uSie",
                    "mSie",
                    "sie",
                    "kSie",
                    "megSie",
                    "mho",
                    "perohm",
                ]:
                    self.logger.error("Invalid conductance unit.")
                    return False

            coupling_limits.append("CondLimit:=")
            coupling_limits.append(cond_limit)

            if cap_limit is None and coupling_limit_type == 0:
                cap_limit = "1pF"
            elif cap_limit is None and coupling_limit_type == 1:
                cap_limit = "0.01"
            elif cap_limit is not None:
                if decompose_variable_value(cap_limit)[1] not in ["fF", "pF", "nF", "uF", "mF", "farad"]:
                    self.logger.error("Invalid capacitance unit.")
                    return False

            coupling_limits.append("CapLimit:=")
            coupling_limits.append(cap_limit)

            if ind_limit is None and coupling_limit_type == 0:
                ind_limit = "1nH"
            elif ind_limit is None and coupling_limit_type == 1:
                ind_limit = "0.01"
            elif ind_limit is not None:
                if decompose_variable_value(ind_limit)[1] not in ["fH", "pH", "nH", "uH", "mH", "H"]:
                    self.logger.error("Invalid inductance unit.")
                    return False

            coupling_limits.append("IndLimit:=")
            coupling_limits.append(ind_limit)

            if res_limit is None and coupling_limit_type == 0:
                res_limit = "1ohm"
            elif res_limit is None and coupling_limit_type == 1:
                res_limit = "0.01"
            elif res_limit is not None:
                if decompose_variable_value(res_limit)[1] not in ["uOhm", "mOhm", "ohm", "kOhm", "megOhm", "GOhm"]:
                    self.logger.error("Invalid resistance unit.")
                    return False

            coupling_limits.append("ResLimit:=")
            coupling_limits.append(res_limit)
        else:
            coupling_limits.append(coupling_limit_value)

        if model is None:
            model = self.project_name

        if decompose_variable_value(lumped_length)[1] not in [
            "cm",
            "dm",
            "fm",
            "ft",
            "in",
            "km",
            "light year",
            "meter",
            "mil",
            "mile",
            "mileNaut",
            "mileTerr",
            "mm",
            "nm",
            "pm",
            "uin",
            "um",
            "yd",
        ]:
            self.logger.error("Invalid lumped length unit.")
            return False

        if rise_time_value is None:
            rise_time_value = "1e-9"

        if rise_time_unit:
            if rise_time_unit not in ["fs", "ps", "ns", "us", "ms", "s", "min", "hour", "day"]:
                self.logger.error("Invalid rise time unit.")
                return False
        else:
            rise_time_unit = "s"

        rise_time = rise_time_value + rise_time_unit

        if file_type.lower() not in ["hspice", "welement", "rlgc"]:
            self.logger.error("Invalid file type, possible solutions are Hspice, Welement, RLGC.")
            return False

        cpp_settings = []
        if include_cpp:
            if settings.aedt_version >= "2023.2":
                if not [x for x in [include_dcr, include_dcl, include_acr, include_acl, add_resistance] if x]:
                    self.logger.error(
                        "Select DC/AC resistance/inductance to include "
                        "the chip package control data in export circuit."
                    )
                    return False
                else:
                    circuit_settings = self.oanalysis.GetCircuitSettings()
                    for setting in circuit_settings:
                        if isinstance(setting, tuple):
                            if setting[0] == "NAME:CPPInfo":
                                cpp_settings = setting

        if self.modeler._is3d:
            try:
                self.oanalysis.ExportCircuit(
                    analysis_setup,
                    variations,
                    output_file,
                    [
                        "NAME:CircuitData",
                        "MatrixName:=",
                        matrix,
                        "NumberOfCells:=",
                        str(cells),
                        "UserHasChangedSettings:=",
                        user_changed_settings,
                        "IncludeCap:=",
                        include_cap,
                        "IncludeCond:=",
                        include_cond,
                        [coupling_limits],
                        "IncludeDCR:=",
                        include_dcr,
                        "IncudeDCL:=",
                        include_dcl,
                        "IncludeACR:=",
                        include_acr,
                        "IncludeACL:=",
                        include_acl,
                        "ADDResistance:=",
                        add_resistance,
                        "ParsePinNames:=",
                        parse_pin_names,
                        "IncludeCPP:=",
                        include_cpp,
                        cpp_settings,
                    ],
                    model,
                    frequency,
                )
                return True
            except Exception:
                self.logger.error("Export of equivalent circuit was unsuccessful.")
                return False
        else:
            try:
                self.oanalysis.ExportCircuit(
                    analysis_setup,
                    variations,
                    output_file,
                    [
                        "NAME:CircuitData",
                        "MatrixName:=",
                        matrix,
                        "NumberOfCells:=",
                        str(cells),
                        "UserHasChangedSettings:=",
                        user_changed_settings,
                        "IncludeCap:=",
                        include_cap,
                        "IncludeCond:=",
                        include_cond,
                        [coupling_limits],
                        "IncludeR:=",
                        include_r,
                        "IncludeL:=",
                        include_l,
                        "ExportDistributed:=",
                        export_distributed,
                        "LumpedLength:=",
                        lumped_length,
                        "RiseTime:=",
                        rise_time,
                    ],
                    model,
                    file_type,
                    frequency,
                )
                return True
            except Exception:
                self.logger.error("Export of equivalent circuit was unsuccessful.")
                return False


class Q3d(QExtractor, CreateBoundaryMixin):
    """Provides the Q3D app interface.

    This class allows you to create an instance of Q3D and link to an
    existing project or create a new one.

    Parameters
    ----------
    project : str, optional
        Name of the project to select or the full path to the project
        or AEDTZ archive to open. The default is ``None``, in which
        case an attempt is made to get an active project. If no
        projects are present, an empty project is created.
    design : str, optional
        Name of the design to select. The default is ``None``, in
        which case an attempt is made to get an active design. If no
        designs are present, an empty design is created.
    solution_type : str, optional
        Solution type to apply to the design. The default is
        ``None``, in which case the default type is applied.
    setup : str, optional
        Name of the setup to use as the nominal. The default is
        ``None``, in which case the active setup is used or nothing
        is used.
    version : str, int, float, optional
        Version of AEDT to use. The default is ``None``, in which case
        the active version or latest installed version is used.
        This parameter is ignored when Script is launched within AEDT.
        Examples of input values are ``251``, ``25.1``, ``2025.1``, ``"2025.1"``.
    non_graphical : bool, optional
        Whether to launch AEDT in non-graphical mode. The default
        is ``False``, in which case AEDT is launched in graphical mode.
        This parameter is ignored when a script is launched within AEDT.
    new_desktop : bool, optional
        Whether to launch an instance of AEDT in a new thread, even if
        another instance of the ``specified_version`` is active on the
        machine. The default is ``False``. This parameter is ignored when
        a script is launched within AEDT.
    close_on_exit : bool, optional
        Whether to release AEDT on exit. The default is ``False``.
    student_version : bool, optional
        Whether to open the AEDT student version. The default is ``False``.
        This parameter is ignored when a script is launched within AEDT.
    machine : str, optional
        Machine name to connect the oDesktop session to. This works only in
        2022 R2 and later. The remote server must be up and running with the
        command `"ansysedt.exe -grpcsrv portnum"`. If the machine is `"localhost"`,
        the server also starts if not present.
    port : int, optional
        Port number on which to start the oDesktop communication on an already
        existing server. This parameter is ignored when a new server is created.
        It works only in 2022 R2 and later. The remote server must be up and
        running with the command `"ansysedt.exe -grpcsrv portnum"`.
    aedt_process_id : int, optional
        Process ID for the instance of AEDT to point PyAEDT at. The default is
        ``None``. This parameter is only used when ``new_desktop = False``.
    remove_lock : bool, optional
        Whether to remove lock to project before opening it or not.
        The default is ``False``, which means to not unlock
        the existing project if needed and raise an exception.

    Examples
    --------
    Create an instance of Q3D and connect to an existing Q3D
    design or create a new Q3D design if one does not exist.

    >>> from ansys.aedt.core import Q3d
    >>> app = Q3d()

    """

    @pyaedt_function_handler(
        designname="design",
        projectname="project",
        specified_version="version",
        setup_name="setup",
        new_desktop_session="new_desktop",
    )
    def __init__(
        self,
        project=None,
        design=None,
        solution_type=None,
        setup=None,
        version=None,
        non_graphical=False,
        new_desktop=False,
        close_on_exit=False,
        student_version=False,
        machine="",
        port=0,
        aedt_process_id=None,
        remove_lock=False,
    ):
        self.is3d = True
        QExtractor.__init__(
            self,
            "Q3D Extractor",
            project,
            design,
            solution_type,
            setup,
            version,
            non_graphical,
            new_desktop,
            close_on_exit,
            student_version,
            machine,
            port,
            aedt_process_id,
            remove_lock=remove_lock,
        )
        self.MATRIXOPERATIONS = MATRIXOPERATIONSQ3D()

    def _init_from_design(self, *args, **kwargs):
        self.__init__(*args, **kwargs)

    @property
    def nets(self):
        """Nets in a Q3D project.

        Returns
        -------
        List of nets in a Q3D project.

        References
        ----------
        >>> oModule.ListNets
        """
        nets_data = list(self.oboundary.ListNets())
        net_names = []
        for i in nets_data:
            if isinstance(i, (list, tuple)):
                net_names.append(i[0].split(":")[1])
        return net_names

    @pyaedt_function_handler()
    def delete_all_nets(self):
        """Delete all nets in the design."""
        net_names = self.nets[::]
        for i in self.boundaries[::]:
            if i.name in net_names:
                i.delete()
        return True

    @pyaedt_function_handler(nets="assignment")
    def objects_from_nets(self, assignment, materials=None):
        """Find the objects that belong to one or more nets. You can filter by materials.

        Parameters
        ----------
        assignment : str, list
            One or more nets to search for. The search is case-insensitive.
        materials : str, list, optional
            One or more materials for filtering the net objects. The default
            is ``None``. The search is case insensitive.

        Returns
        -------
        dict
            Dictionary of net name and objects that belongs to it.
        """
        if isinstance(assignment, str):
            assignment = [assignment]
        if isinstance(materials, str):
            materials = [materials]
        elif not materials:
            materials = []
        materials = [i.lower() for i in materials]
        objects = {}
        for net in assignment:
            for bound in self.boundaries:
                if net.lower() == bound.name.lower() and "Net" in bound.type:
                    obj_list = self.modeler.convert_to_selections(bound.props.get("Objects", []), True)
                    if materials:
                        obj_list = [
                            self.modeler[i].name for i in obj_list if self.modeler[i].material_name.lower() in materials
                        ]
                    objects[net] = obj_list
        return objects

    @pyaedt_function_handler()
    def net_sources(self, net_name):
        """Check if a net has sources and return a list of source names.

        Parameters
        ----------
        net_name : str
            Name of the net to search for.

        Returns
        -------
        List
            List of source names.

        Examples
        --------
        >>> from ansys.aedt.core import Q3d
        >>> q3d = Q3d("my_project")
        >>> net = q3d.net_sources("Net1")
        """
        sources = []
        net_id = -1
        for i in self.boundaries:
            if i.type == "SignalNet" and i.name == net_name and i.props.get("ID", None) is not None:  # pragma: no cover
                net_id = i.props.get("ID", None)
                break
        for i in self.boundaries:
            if i.type == "Source":
                if i.props.get("Net", None) == net_name or i.props.get("Net", None) == net_id:
                    sources.append(i.name)

        return sources

    @pyaedt_function_handler()
    def net_sinks(self, net_name):
        """Check if a net has sinks and return a list of sink names.

        Parameters
        ----------
        net_name : str
            Name of the net to search for.

        Returns
        -------
        List
            List of sink names.

        Examples
        --------
        >>> from ansys.aedt.core import Q3d
        >>> q3d = Q3d("my_project")
        >>> net = q3d.net_sinks("Net1")
        """
        sinks = []
        net_id = -1
        for i in self.boundaries:
            if i.type == "SignalNet" and i.name == net_name and i.props.get("ID", None) is not None:
                net_id = i.props.get("ID", None)  # pragma: no cover
                break  # pragma: no cover
        for i in self.boundaries:
            if i.type == "Sink" and any(map(lambda val: i.props.get("Net", None) == val, [net_name, net_id])):
                sinks.append(i.name)
        return sinks

    @pyaedt_function_handler()
    def auto_identify_nets(self):
        """Identify nets automatically.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.AutoIdentifyNets
        """
        original_nets = [i for i in self.nets]
        has_conductor = False
        for _, val in self.modeler.objects.items():
            if val.material_name and self.materials[val.material_name].is_conductor():
                has_conductor = True
                break
        if not has_conductor:
            self.logger.warning("Nets not identified because no conductor material was found.")
            return True
        self.oboundary.AutoIdentifyNets()
        new_nets = [i for i in self.nets if i not in original_nets]
        for net in new_nets:
            objects = self.modeler.convert_to_selections(
                [int(i) for i in list(self.oboundary.GetExcitationAssignment(net))], True
            )
            props = dict({"Objects": objects})
            bound = BoundaryObject(self, net, props, "SignalNet")
            self._boundaries[bound.name] = bound
        if new_nets:
            self.logger.info(f"{len(new_nets)} Nets have been identified: {', '.join(new_nets)}")
        else:
            self.logger.info("No new nets identified")
        return True

    @pyaedt_function_handler(objects="assignment")
    def assign_net(self, assignment, net_name=None, net_type="Signal"):
        """Assign a net to a list of objects.

        Parameters
        ----------
        assignment : list, str
            List of objects to assign the net to. It can be a single object.
        net_name : str, optional
            Name of the net. The default is ```None``, in which case the
            default name is used.
        net_type : str, bool
            Type of net to create. Options are ``"Signal"``, ``"Ground"`` and ``"Floating"``.
            The default is ``"Signal"``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Source object.

        References
        ----------
        >>> oModule.AssignSignalNet
        >>> oModule.AssignGroundNet
        >>> oModule.AssignFloatingNet

        Examples
        --------
        >>> from ansys.aedt.core import Q3d
        >>> q3d = Q3d()
        >>> box = q3d.modeler.create_box([30, 30, 30],[10, 10, 10],name="mybox")
        >>> net_name = "my_net"
        >>> net = q3d.assign_net(box,net_name)
        """
        assignment = self.modeler.convert_to_selections(assignment, True)
        if not net_name:
            net_name = generate_unique_name("Net")
        props = dict({"Objects": assignment})
        type_bound = "SignalNet"
        if net_type.lower() == "ground":
            type_bound = "GroundNet"
        elif net_type.lower() == "floating":
            type_bound = "FloatingNet"

        return self._create_boundary(net_name, props, type_bound)

    @pyaedt_function_handler(objects="assignment", axisdir="direction")
    def source(self, assignment=None, direction=0, name=None, net_name=None, terminal_type="voltage"):
        """Generate a source on a face of an object or a group of faces or face ids.

        The face ID is selected based on the axis direction. It is the face that
        has the maximum/minimum in this axis direction.

        Parameters
        ----------
        assignment : str, int or list or :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
            Name of the object or face ID or face ID list.
        direction : int, optional
            Initial axis direction. Options are ``0`` to ``5``. The default is ``0``.
        name : str, optional
            Name of the source. The default is ``None``.
        net_name : str, optional
            Name of the net. The default is ``None``, in which case the ``object_name`` is considered.
        terminal_type : str
            Type of the terminal. Options are ``voltage`` and ``current``. The default is ``voltage``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Source object.

        References
        ----------
        >>> oModule.AssignSource
        """
        return self._assign_source_or_sink(assignment, direction, name, net_name, terminal_type, "Source")

    @pyaedt_function_handler(objects="assignment", axisdir="direction")
    def sink(self, assignment=None, direction=0, name=None, net_name=None, terminal_type="voltage"):
        """Generate a sink on a face of an object or a group of faces or face ids.

        The face ID is selected based on the axis direction. It is the face that
        has the maximum/minimum in this axis direction.

        Parameters
        ----------
        assignment : str, int or list or :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
            Name of the object or face ID or face ID list.
        direction : int, optional
            Initial axis direction. Options are ``0`` to ``5``. The default is ``0``.
        name : str, optional
            Name of the source. The default is ``None``.
        net_name : str, optional
            Name of the net. The default is ``None``, in which case the ``object_name`` is considered.
        terminal_type : str
            Type of the terminal. Options are ``voltage`` and ``current``. The default is ``voltage``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Sink object.

        References
        ----------
        >>> oModule.AssignSource
        """
        return self._assign_source_or_sink(assignment, direction, name, net_name, terminal_type, "Sink")

    @pyaedt_function_handler(objects="assignment", axisdir="direction")
    def _assign_source_or_sink(self, assignment, direction, name, net_name, terminal_type, exc_type):
        if not name:
            name = generate_unique_name(exc_type)
        assignment = self.modeler.convert_to_selections(assignment, True)
        sheets = []
        is_face = True
        for object_name in assignment:
            if isinstance(object_name, str) and object_name in self.modeler.solid_names:
                sheets.append(self.modeler._get_faceid_on_axis(object_name, direction))
                if not net_name:
                    for net in self.nets:
                        if object_name in self.objects_from_nets(net):
                            net_name = net
            elif isinstance(object_name, str):
                is_face = False
                sheets.append(object_name)
            else:
                sheets.append(object_name)

        if is_face:
            props = dict({"Faces": sheets})
        else:
            props = dict({"Objects": sheets})

        if terminal_type == "current":
            terminal_str = "UniformCurrent"
        else:
            terminal_str = "ConstantVoltage"

        props["TerminalType"] = terminal_str
        if net_name:
            props["Net"] = net_name
        return self._create_boundary(name, props, exc_type)

    @pyaedt_function_handler(
        object_name="assignment",
        axisdir="direction",
        sink_name="name",
    )
    def assign_sink_to_objectface(self, assignment, direction=0, name=None, net_name=None):
        """Generate a sink on a face of an object.

        .. deprecated:: 0.8.9
            This method is deprecated. Use the ``sink()`` method instead.

        The face ID is selected based on the axis direction. It is the face that has
        the maximum or minimum in this axis direction.

        Parameters
        ----------
        assignment : str, int
            Name of the object or face ID.
        direction : int, optional
            Initial axis direction. Options are ``0`` to ``5``. The default is ``0``.
        name : str, optional
            Name of the sink. The default is ``None``.
        net_name : str, optional
            Name of the net. The default is ``None``, in which case the ``object_name`` is considered.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Sink object.

        References
        ----------
        >>> oModule.AssignSink
        """
        warnings.warn(
            "This method is deprecated in 0.8.9. Use the ``sink()`` method.",
            DeprecationWarning,
        )

        assignment = self.modeler.convert_to_selections(assignment, True)[0]
        if isinstance(assignment, int):
            a = assignment
            assignment = self.modeler.oeditor.GetObjectNameByFaceID(a)
        else:
            a = self.modeler._get_faceid_on_axis(assignment, direction)
        if not name:
            name = generate_unique_name("Sink")
        if not net_name:
            net_name = assignment
        if a:
            props = dict({"Faces": [a], "ParentBndID": assignment, "TerminalType": "ConstantVoltage", "Net": net_name})
            return self._create_boundary(name, props, "Sink")
        return False

    @pyaedt_function_handler(sheetname="assignment", objectname="object_name", netname="net_name", sinkname="sink_name")
    def assign_sink_to_sheet(
        self, assignment, object_name=None, net_name=None, sink_name=None, terminal_type="voltage"
    ):
        """Generate a sink on a sheet.

        .. deprecated:: 0.8.9
            This method is deprecated. Use the ``sink()`` method instead.

        Parameters
        ----------
        assignment :
            Name of the sheet to create the sink on.
        object_name : str, optional
            Name of the parent object. The default is ``None``.
        net_name : str, optional
            Name of the net. The default is ``None``.
        sink_name : str, optional
            Name of the sink. The default is ``None``.
        terminal_type : str
            Type of the terminal. Options are ``voltage`` and ``current``. The default is ``voltage``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Source object.

        References
        ----------
        >>> oModule.AssignSink
        """
        warnings.warn(
            "This method is deprecated in 0.8.9. Use the ``sink()`` method.",
            DeprecationWarning,
        )

        if not sink_name:
            sink_name = generate_unique_name("Sink")
        assignment = self.modeler.convert_to_selections(assignment, True)[0]
        if isinstance(assignment, int):
            props = dict({"Faces": [assignment]})
        else:
            props = dict({"Objects": [assignment]})
        if object_name:
            props["ParentBndID"] = object_name

        if terminal_type == "current":
            terminal_str = "UniformCurrent"
        else:
            terminal_str = "ConstantVoltage"

        props["TerminalType"] = terminal_str

        if net_name:
            props["Net"] = net_name

        return self._create_boundary(sink_name, props, "Sink")

    @pyaedt_function_handler()
    def create_frequency_sweep(self, setupname, units=None, freqstart=0, freqstop=1, freqstep=None, sweepname=None):
        """Create a frequency sweep.

        .. deprecated:: 0.7.12
            This method is deprecated. To create a frequency sweep use ``create_frequency_sweep()``
            from setup object.
            Example
            -------
            >>> from ansys.aedt.core import Q3d
            >>> q3d = Q3d()
            >>> setup1 = q3d.create_setup(name="Setup1")
            >>> sweep1 = setup1.create_frequency_sweep(unit="GHz", freqstart=0.5, freqstop=1.5, sweepname="Sweep1")
            >>> q3d.release_desktop(True, True)

        Parameters
        ----------
        setupname : str
            Name of the setup that is attached to the sweep.
        units : str, optional
            Units of the frequency. For example, ``"MHz"`` or
            ``"GHz"``. The default is ``None`` which takes the Default Desktop units.
        freqstart : float, str, optional
            Starting frequency of the sweep. The default is ``0``.
             If a unit is passed with the number, such as ``"1MHz"``, the unit is ignored.
        freqstop : float, str, optional
            Stopping frequency of the sweep. The default is ``1``.
            If a unit is passed with the number, such as``"1MHz"``, the unit is ignored.
        freqstep : optional
            Frequency step point.
        sweepname : str, optional
            Name of the sweep. The default is ``None``, in which case the
            default name is used.

        Returns
        -------
        :class:`ansys.aedt.core.modules.solve_sweeps.SweepHFSS3DLayout`
            Sweep object when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.InsertSweep
        """
        if sweepname is None:
            sweepname = generate_unique_name("Sweep")

        if setupname not in self.setup_names:
            return False
        for i in self.setups:
            if i.name == setupname:
                setupdata = i
                for sw in setupdata.sweeps:
                    if sweepname == sw.name:
                        self.logger.warning("Sweep %s is already present. Rename and retry.", sweepname)
                        return False
                sweepdata = setupdata.add_sweep(sweepname, "Discrete")
                sweepdata.props["RangeStart"] = self.value_with_units(freqstart, units, "Frequency")
                sweepdata.props["RangeEnd"] = self.value_with_units(freqstop, units, "Frequency")
                sweepdata.props["RangeStep"] = self.value_with_units(freqstep, units, "Frequency")

                sweepdata.props["SaveFields"] = False
                sweepdata.props["SaveRadFields"] = False
                sweepdata.props["Type"] = "Interpolating"
                sweepdata.props["RangeType"] = "LinearStep"
                sweepdata.update()
                return sweepdata
        return False

    @pyaedt_function_handler()
    def create_discrete_sweep(
        self, setupname, freqstart, freqstop=None, freqstep=None, units="GHz", sweepname=None, savefields=False
    ):
        """Create a discrete sweep with a single frequency value.

        .. deprecated:: 0.7.12
            This method is deprecated. To create a discrete frequency sweep use ``create_frequency_sweep()``
            from setup object.
            Example
            -------
            >>> from ansys.aedt.core import Q3d
            >>> q3d = Q3d()
            >>> setup1 = q3d.create_setup(name="Setup1")
            >>> sweep1 = setup1.create_frequency_sweep(unit="GHz",
            ...                                        freqstart=0.5,
            ...                                        freqstop=1.5,
            ...                                        sweepname="Sweep1",
            ...                                        sweep_type="Discrete")
            >>> q3d.release_desktop(True, True)

        Parameters
        ----------
        setupname : str
            Name of the setup that the sweeps belongs to.
        freqstart : float
            Starting point for the discrete frequency.
        freqstop : float, optional
            Stopping point for the discrete frequency. If ``None``,
            a single-point sweep is performed.
        freqstep : float, optional
            Step point for the discrete frequency. If ``None``,
            11 points are created.
        units : str, optional
            Units of the discrete frequency. For example, ``"MHz"`` or
            ``"GHz"``. The default is ``"GHz"``.
        sweepname : str, optional
            Name of the sweep. The default is ``None``, in which case
            the default name is used.
        savefields : bool, optional
            Whether to save fields. The default is ``False``.

        Returns
        -------
        SweepMatrix
            Sweep option.

        References
        ----------
        >>> oModule.InsertSweep
        """
        if sweepname is None:
            sweepname = generate_unique_name("Sweep")

        if setupname not in self.setup_names:
            return False
        for i in self.setups:
            if i.name == setupname:
                setupdata = i
                for sw in setupdata.sweeps:
                    if sweepname == sw.name:
                        self.logger.warning("Sweep %s already present. Rename and retry.", sweepname)
                        return False
                sweepdata = setupdata.add_sweep(sweepname, "Discrete")
                sweepdata.props["RangeStart"] = str(freqstart) + "GHz"
                if not freqstop:
                    freqstop = freqstart
                if not freqstep:
                    freqstep = (freqstop - freqstart) / 11
                    if freqstep == 0:
                        freqstep = freqstart
                sweepdata.props["RangeEnd"] = str(freqstop) + "GHz"
                sweepdata.props["RangeStep"] = str(freqstep) + "GHz"
                sweepdata.props["SaveFields"] = savefields
                sweepdata.props["SaveRadFields"] = False
                sweepdata.props["Type"] = "Discrete"
                sweepdata.props["RangeType"] = "LinearStep"
                sweepdata.update()
                return sweepdata
        return False

    @pyaedt_function_handler()
    def set_material_thresholds(
        self, insulator_threshold=None, perfect_conductor_threshold=None, magnetic_threshold=None
    ):
        """Set material threshold.

        Parameters
        ----------
        insulator_threshold : float, optional
            Threshold for the insulator or conductor. The default is "None", in which
            case the threshold is set to 10000.
        perfect_conductor_threshold : float, optional
            Threshold that decides whether a conductor is perfectly conducting. This value
            must be higher than the value for the insulator threshold. The default is ``None``,
            in which case the value is set to 1E+030.
        magnetic_threshold : float, optional
            Threshold that decides whether a material is magnetic. The default is "None",
            in which case the value is set to 1.01.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        try:
            import numpy as np

            if not insulator_threshold:
                insulator_threshold = 10000
            if not perfect_conductor_threshold:
                perfect_conductor_threshold = float("1E+30")
            else:
                if perfect_conductor_threshold < insulator_threshold:
                    msg = "Perfect conductor threshold must be higher than insulator threshold."
                    raise ValueError(msg)
            if not magnetic_threshold:
                magnetic_threshold = 1.01

            if not self.desktop_class.is_grpc_api:
                insulator_threshold = np.longdouble(insulator_threshold)
                perfect_conductor_threshold = np.longdouble(perfect_conductor_threshold)
                magnetic_threshold = np.longdouble(magnetic_threshold)

            self.oboundary.SetMaterialThresholds(insulator_threshold, perfect_conductor_threshold, magnetic_threshold)
            return True
        except ImportError:  # pragma: no cover
            warnings.warn(
                "The NumPy module is required to use functionalities provided by the module ansys.edt.core.q3d.\n"
                "Install with \n\npip install numpy"
            )
        except Exception:
            return False

    @pyaedt_function_handler(setupname="name")
    def create_setup(self, name="MySetupAuto", **kwargs):
        """Create an analysis setup for Q3D Extractor.

        Optional arguments are passed along with the ``name`` parameter.

        Parameters
        ----------
        name : str, optional
            Name of the setup. The default is "Setup1".
        **kwargs : dict, optional
            Available keys depend on the setup chosen.
            For more information, see :doc:`../SetupTemplatesQ3D`.

        Returns
        -------
        :class:`ansys.aedt.core.modules.solve_setup.SetupQ3D`
            3D Solver Setup object.

        References
        ----------
        >>> oModule.InsertSetup

        Examples
        --------

        >>> from ansys.aedt.core import Q3d
        >>> app = Q3d()
        >>> app.create_setup(name="Setup1",DC__MinPass=2)

        """
        setup_type = self.design_solutions.default_setup

        if "props" in kwargs:
            return self._create_setup(name=name, setup_type=setup_type, props=kwargs["props"])
        else:
            setup = self._create_setup(name=name, setup_type=setup_type)
        setup.auto_update = False
        for arg_name, arg_value in kwargs.items():
            if setup[arg_name] is not None:
                setup[arg_name] = arg_value
        setup.auto_update = True
        setup.update()
        return setup

    @pyaedt_function_handler()
    def assign_thin_conductor(self, assignment, material="copper", thickness=1, name=""):
        """Assign a thin conductor to a sheet.

        The method accepts both a sheet name or a face id.
        If a face it is provided, then a sheet will be created and the boundary assigned to it.

        Parameters
        ----------
        assignment : str or int or :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d` or list
            Object assignment.
        material : str, optional
            Material. Default is ``"copper"``.
        thickness : float, str, optional
            Conductor thickness. It can be as number of a string with units. Default is ``1``.
        name : str, optional
            Name of the boundary. Default is ``""``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Source object.
        """
        assignment = self.modeler.convert_to_selections(assignment, True)
        new_ass = []
        for ass in assignment:
            if isinstance(ass, int):
                try:
                    new_ass.append(self.modeler.create_object_from_face(ass)._m_name)
                except Exception:  # pragma: no cover
                    self.logger.error("Thin conductor can be applied only to sheet objects or faces.")
            elif ass in self.modeler.sheet_names:
                new_ass.append(ass)
            else:
                self.logger.error("Thin conductor can be applied only to sheet objects.")
        if not new_ass:
            return False
        if not name:
            name = generate_unique_name("Thin_Cond")
        if isinstance(thickness, (float, int)):
            thickness = str(thickness) + self.modeler.model_units
        props = dict({"Objects": new_ass, "Material": material, "Thickness": thickness})

        return self._create_boundary(name, props, "ThinConductor")

    @pyaedt_function_handler()
    def get_mutual_coupling(
        self, source1, sink1, source2, sink2, calculation="ACL", setup_sweep_name=None, variations=None
    ):
        """Get mutual coupling between two terminals.

        User has to provide the pair, source and sink of each terminal. If the provided sinks are not part of the
        original matrix, a new matrix will be created.

        Parameters
        ----------
        source1 : str
            First element source.
        sink1 : str
            First element sink.
        source2 : str
            Second element source.
        sink2 : str
            Second element sink.
        calculation : str, optional
            Calculation type.
            Available options are: ``"ACL"``, ``"ACR"``, ``"DCL"``, ``"DCR"``.
            The default is ``"ACL"``.
        setup_sweep_name : str, optional
            Name of the setup. The default is ``None``, in which case the ``nominal_adaptive``
            setup is used. Be sure to build a setup string in the form of
            ``"SetupName : SetupSweep"``, where ``SetupSweep`` is the sweep name to
            use in the export or ``LastAdaptive``.
        variations : dict, optional
            Dictionary of all families including the primary sweep.
            The default is ``None`` which uses all variations of the setup.

        Returns
        -------
        :class:`pyaedt.modules.solutions.SolutionData` or bool
            Solution Data object if successful, ``False`` otherwise.

        Examples
        --------
        >>> from pyaedt import Q3d
        >>> aedtapp = Q3d()
        >>> data = aedtapp.modeler.get_mutual_coupling("a1", "a2", "b1", "b2", calculation="DCL")
        """
        if setup_sweep_name is None:
            setup_sweep_name = self.nominal_sweep

        if calculation not in ["ACL", "ACR", "DCL", "DCR"]:
            self.logger.error("Calculation type not valid.")
            return False

        if not variations:
            variations = self.available_variations.all

        assignment = {}

        for net in self.nets:
            source_name = "source_1"
            sources = self.net_sources(net)
            sinks = self.net_sinks(net)
            assignment[net] = {}

            if source1 in sources or source1 in sinks:
                assignment[net][source_name] = source1
                source_name = "source_2"
            if sink1 in sources or sink1 in sinks:
                assignment[net]["sink"] = sink1
            if source2 in sources or source2 in sinks:
                assignment[net][source_name] = source2
            if sink2 in sources or sink2 in sinks:
                assignment[net]["sink"] = sink2

        move_sink = []
        is_new_matrix = True
        matrix_name = "Original"

        sources = []
        sinks = []

        expression = calculation + "("

        for net_name, net_props in assignment.items():

            expression += net_name

            if "source_1" not in net_props or "sink" not in net_props:
                self.logger.error("Sources and sinks passed not valid.")
                return False

            sources.append(self.net_sources(net_name))
            sinks.append(self.net_sinks(net_name))

            source = net_props["source_1"]
            sink = net_props["sink"]

            expression += ":"
            expression += source
            expression += ","

            if "Sink" not in [self.excitation_objects[source].type, self.excitation_objects[sink].type]:
                move_sink.append(sink)
            elif self.excitation_objects[sink].type == "Source":
                move_sink.append(sink)

            if "source_2" in net_props:
                # Both sources in the same net
                source = net_props["source_2"]
                expression += net_name
                expression += ":"
                expression += source
                expression += ","
                break
        expression = expression[:-1]
        expression += ")"

        if move_sink:
            sources = [item for sublist in sources for item in sublist]
            sinks = [item for sublist in sinks for item in sublist]
            all_terminals = sources + sinks
            for q3d_matrix in self.matrices:
                matrix_available_sources = self.omatrix.ListReduceMatrixReducedSources(q3d_matrix.name, False)
                matrix_source_list = [element.split(":")[1] for element in matrix_available_sources]
                matrix_sink_list = list(set(all_terminals).symmetric_difference(set(matrix_source_list)))
                for initial_sink in sinks:
                    if initial_sink in matrix_sink_list:
                        matrix_sink_list.remove(initial_sink)
                if sorted(matrix_sink_list) == sorted(move_sink):
                    is_new_matrix = False
                    matrix_name = q3d_matrix.name
                    break
        else:
            is_new_matrix = False

        if is_new_matrix:
            matrix = self.insert_reduced_matrix("MoveSink", move_sink)
            matrix_name = matrix.name

        data = self.post.get_solution_data(
            expressions=expression, context=matrix_name, variations=variations, setup_sweep_name=setup_sweep_name
        )
        return data


class Q2d(QExtractor, CreateBoundaryMixin):
    """Provides the Q2D app interface.

    This class allows you to create an instance of Q2D and link to an
    existing project or create a new one.

    Parameters
    ----------
    project : str, optional
        Name of the project to select or the full path to the project
        or AEDTZ archive to open. The default is ``None``, in which
        case an attempt is made to get an active project. If no
        projects are present, an empty project is created.
    design : str, optional
        Name of the design to select. The default is ``None``, in
        which case an attempt is made to get an active design. If no
        designs are present, an empty design is created.
    solution_type : str, optional
        Solution type to apply to the design. The default is
        ``None``, in which case the default type is applied.
    setup : str, optional
        Name of the setup to use as the nominal. The default is
        ``None``, in which case the active setup is used or
        nothing is used.
    version : str, int, float, optional
        Version of AEDT to use. The default is ``None``, in which case
        the active version or latest installed version is used.  This
        parameter is ignored when a script is launched within AEDT.
        Examples of input values are ``251``, ``25.1``, ``2025.1``, ``"2025.1"``.
    non_graphical : bool, optional
        Whether to launch AEDT in non-graphical mode. The default
        is ``False``, in which case AEDT is launched in graphical mode.
        This parameter is ignored when a script is launched within AEDT.
    new_desktop : bool, optional
        Whether to launch an instance of AEDT in a new thread, even if
        another instance of the ``specified_version`` is active on the
        machine. The default is ``False``. This parameter is ignored
        when a script is launched within AEDT.
    close_on_exit : bool, optional
        Whether to release AEDT on exit. The default is ``False``.
    student_version : bool, optional
        Whether to open the AEDT student version. This parameter is
        ignored when a script is launched within AEDT.
    machine : str, optional
        Machine name to connect the oDesktop session to. This works only in 2022 R2
        and later. The remote server must be up and running with the command
        `"ansysedt.exe -grpcsrv portnum"`. If the machine is `"localhost"`,
        the server also starts if not present.
    port : int, optional
        Port number on which to start the oDesktop communication on an already existing server.
        This parameter is ignored when creating a new server. It works only in 2022 R2 or later.
        The remote server must be up and running with the command `"ansysedt.exe -grpcsrv portnum"`.
    aedt_process_id : int, optional
        Process ID for the instance of AEDT to point PyAEDT at. The default is
        ``None``. This parameter is only used when ``new_desktop = False``.
    remove_lock : bool, optional
        Whether to remove lock to project before opening it or not.
        The default is ``False``, which means to not unlock
        the existing project if needed and raise an exception.

    Examples
    --------
    Create an instance of Q2D and link to a project named
    ``projectname``. If this project does not exist, create one with
    this name.

    >>> from ansys.aedt.core import Q2d
    >>> app = Q2d(projectname)

    Create an instance of Q2D and link to a design named
    ``designname`` in a project named ``projectname``.

    >>> app = Q2d(projectname,designame)

    Create an instance of Q2D and open the specified project,
    which is named ``myfile.aedt``.

    >>> app = Q2d("myfile.aedt")

    """

    @property  # for legacy purposes
    def dim(self):
        """Dimension."""
        return self.modeler.dimension

    @pyaedt_function_handler(
        designname="design",
        projectname="project",
        specified_version="version",
        setup_name="setup",
        new_desktop_session="new_desktop",
    )
    def __init__(
        self,
        project=None,
        design=None,
        solution_type=None,
        setup=None,
        version=None,
        non_graphical=False,
        new_desktop=False,
        close_on_exit=False,
        student_version=False,
        machine="",
        port=0,
        aedt_process_id=None,
        remove_lock=False,
    ):
        self.is3d = False
        QExtractor.__init__(
            self,
            "2D Extractor",
            project,
            design,
            solution_type,
            setup,
            version,
            non_graphical,
            new_desktop,
            close_on_exit,
            student_version,
            machine,
            port,
            aedt_process_id,
            remove_lock=remove_lock,
        )
        self.MATRIXOPERATIONS = MATRIXOPERATIONSQ2D()

    def _init_from_design(self, *args, **kwargs):
        self.__init__(*args, **kwargs)

    @pyaedt_function_handler(position="origin", dimension_list="sizes", matname="material")
    def create_rectangle(self, origin, sizes, name="", material=""):
        """Create a rectangle.

        Parameters
        ----------
        origin : list
            List of ``[x, y]`` coordinates for the starting point of the rectangle.
        sizes : list
            List of ``[width, height]`` dimensions.
        name : str, optional
            Name of the rectangle. The default is ``None``, in which case
            the default name is assigned.
        material : str, optional
            Name of the material. The default is ``None``, in which case
            the default material is used.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
            3D object.

        References
        ----------
        >>> oEditor.CreateRectangle
        """
        return self.modeler.create_rectangle(origin=origin, sizes=sizes, name=name, material=material)

    @pyaedt_function_handler(target_objects="assignment", unit="units")
    def assign_single_signal_line(self, assignment, name="", solve_option="SolveInside", thickness=None, units="um"):
        """Assign the conductor type to sheets.

        Parameters
        ----------
        assignment : list
            List of Object3D.
        name : str, optional
            Name of the conductor. The default is ``""``, in which case the default name is used.
        solve_option : str, optional
            Method for solving. Options are ``"SolveInside"``, ``"SolveOnBoundary"``, and ``"Automatic"``.
            The default is ``"SolveInside"``.
        thickness : float, optional
            Conductor thickness. The default is ``None``, in which case the conductor thickness
            is obtained by dividing the conductor's area by its perimeter (A/p). If multiple
            conductors are selected, the average conductor thickness is used.
        units : str, optional
            Thickness unit. The default is ``"um"``.

        References
        ----------
        >>> oModule.AssignSingleSignalLine
        >>> oModule.AssignSingleReferenceGround
        """

        warnings.warn(
            "`assign_single_signal_line` is deprecated. Use `assign_single_conductor` instead.", DeprecationWarning
        )
        self.assign_single_conductor(assignment, name, "SignalLine", solve_option, thickness, units)

    @pyaedt_function_handler(target_objects="assignment", unit="units")
    def assign_single_conductor(
        self,
        assignment,
        name="",
        conductor_type="SignalLine",
        solve_option="SolveInside",
        thickness=None,
        units="um",
    ):
        """
        Assign the conductor type to sheets.

        Parameters
        ----------
        assignment : list
            List of Object3D.
        name : str, optional
            Name of the conductor. The default is ``""``, in which case the default name is used.
        conductor_type : str
            Type of the conductor. Options are ``"SignalLine"`` and ``"ReferenceGround"``. The default is
            ``"SignalLine"``.
        solve_option : str, optional
            Method for solving. Options are ``"SolveInside"``, ``"SolveOnBoundary"``, and ``"Automatic"``.
            The default is ``"SolveInside"``.
        thickness : float, optional
            Conductor thickness. The default is ``None``, in which case the conductor thickness is obtained by dividing
            the conductor's area by its perimeter (A/p). If multiple conductors are selected, the average conductor
            thickness is used.
        units : str, optional
            Thickness unit. The default is ``"um"``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Source object.

        References
        ----------
        >>> oModule.AssignSingleSignalLine
        >>> oModule.AssignSingleReferenceGround
        """
        if not name:
            name = generate_unique_name(name)

        if isinstance(assignment, list):
            a = assignment
            obj_names = [i.name for i in assignment]
        else:
            a = [assignment]
            obj_names = [assignment.name]

        if not thickness:
            t_list = []
            for t_obj in a:
                perimeter = 0
                for edge in t_obj.edges:
                    perimeter = perimeter + edge.length
                t_list.append(t_obj.faces[0].area / perimeter)
            thickness = sum(t_list) / len(t_list)

        props = dict({"Objects": obj_names, "SolveOption": solve_option, "Thickness": str(thickness) + units})

        return self._create_boundary(name, props, conductor_type)

    @pyaedt_function_handler(edges="assignment", unit="units")
    def assign_huray_finitecond_to_edges(self, assignment, radius, ratio, units="um", name=""):
        """
        Assign the Huray surface roughness model to edges.

        Parameters
        ----------
        assignment :
        radius :
        ratio :
        units : str, optional
            The default is ``"um"``.
        name : str, optional
            The default is ``""``, in which case the default name is used.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Source object.

        References
        ----------
        >>> oMdoule.AssignFiniteCond
        """
        if not name:
            name = generate_unique_name(name)

        if not isinstance(radius, str):
            ra = str(radius) + units
        else:
            ra = radius

        a = self.modeler.convert_to_selections(assignment, True)

        props = dict({"Edges": a, "UseCoating": False, "Radius": ra, "Ratio": str(ratio)})

        return self._create_boundary(name, props, "Finite Conductivity")

    @pyaedt_function_handler()
    def auto_assign_conductors(self):
        """Automatically assign conductors to signal lines.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        original_nets = list(self.oboundary.GetExcitations())
        self.oboundary.AutoAssignSignals()
        new_nets = [i for i in list(self.oboundary.GetExcitations()) if i not in original_nets]
        i = 0
        while i < len(new_nets):
            objects = self.modeler.convert_to_selections(
                [int(k) for k in list(self.oboundary.GetExcitationAssignment(new_nets[i]))], True
            )
            props = dict({"Objects": objects})
            bound = BoundaryObject(self, new_nets[i], props, new_nets[i + 1])
            self._boundaries[bound.name] = bound
            i += 2
        if new_nets:
            self.logger.info(f"{len(new_nets)} Nets have been identified: {', '.join(new_nets)}")
        else:
            self.logger.info("No new nets identified")
        return True

    @pyaedt_function_handler()
    def export_w_elements(self, analyze=False, export_folder=None):
        """Export all W-elements to files.

        Parameters
        ----------
        analyze : bool, optional
            Whether to analyze before export. Solutions must be present for the design.
            The default is ``False``.
        export_folder : str, optional
            Full path to the folder to export files to. The default is ``None``, in
            which case the working directory is used.

        Returns
        -------
        list
            List of all exported files.
        """
        exported_files = []
        if not export_folder:
            export_folder = self.working_directory
        if not os.path.exists(export_folder):
            os.makedirs(export_folder)
        if analyze:
            self.analyze()
        setups = self.oanalysis.GetSetups()

        for s in setups:
            sweeps = self.oanalysis.GetSweeps(s)
            if not sweeps:
                sweeps = ["LastAdaptive"]
            for sweep in sweeps:
                variation_array = self.list_of_variations(s, sweep)
                solution_name = f"{s} : {sweep}"
                if len(variation_array) == 1:
                    try:
                        export_file = f"{self.project_name}_{s}_{sweep}.sp"
                        export_path = os.path.join(export_folder, export_file)
                        subckt_name = f"w_{self.project_name}"
                        self.oanalysis.ExportCircuit(
                            solution_name,
                            variation_array[0],
                            export_path,
                            [
                                "NAME:CircuitData",
                                "MatrixName:=",
                                "Original",
                                "NumberOfCells:=",
                                "1",
                                "UserHasChangedSettings:=",
                                True,
                                "IncludeCap:=",
                                False,
                                "IncludeCond:=",
                                False,
                                ["NAME:CouplingLimits", "CouplingLimitType:=", "None"],
                                "IncludeR:=",
                                False,
                                "IncludeL:=",
                                False,
                                "ExportDistributed:=",
                                True,
                                "LumpedLength:=",
                                "1meter",
                                "RiseTime:=",
                                "1e-09s",
                            ],
                            subckt_name,
                            "WElement",
                            0,
                        )
                        exported_files.append(export_path)
                        self.logger.info("Exported W-element: %s", export_path)
                    except Exception:  # pragma: no cover
                        self.logger.warning("Export W-element failed")
                else:
                    varCount = 0
                    for variation in variation_array:
                        varCount += 1
                        try:
                            export_file = f"{self.project_name}_{s}_{sweep}_{varCount}.sp"
                            export_path = os.path.join(export_folder, export_file)
                            subckt_name = f"w_{self.project_name}_{varCount}"
                            self.oanalysis.ExportCircuit(
                                solution_name,
                                variation,
                                export_path,
                                [
                                    "NAME:CircuitData",
                                    "MatrixName:=",
                                    "Original",
                                    "NumberOfCells:=",
                                    "1",
                                    "UserHasChangedSettings:=",
                                    True,
                                    "IncludeCap:=",
                                    False,
                                    "IncludeCond:=",
                                    False,
                                    ["NAME:CouplingLimits", "CouplingLimitType:=", "None"],
                                    "IncludeR:=",
                                    False,
                                    "IncludeL:=",
                                    False,
                                    "ExportDistributed:=",
                                    True,
                                    "LumpedLength:=",
                                    "1meter",
                                    "RiseTime:=",
                                    "1e-09s",
                                ],
                                subckt_name,
                                "WElement",
                                0,
                            )
                            exported_files.append(export_path)
                            self.logger.info("Exported W-element: %s", export_path)
                        except Exception:  # pragma: no cover
                            self.logger.warning("Export W-element failed")
        return exported_files

    @pyaedt_function_handler(conductor_name="assignment")
    def toggle_conductor_type(self, assignment, new_type):
        """Change the conductor type.

        Parameters
        ----------
        assignment : str
            Name of the conductor to update.
        new_type : str
            New conductor type.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        try:
            self.oboundary.ToggleConductor(assignment, new_type)
            for bound in self.boundaries:
                if bound.name == assignment:
                    bound.type = new_type
            self.logger.info("Conductor type correctly updated")
            return True
        except Exception:
            self.logger.error("Error in updating conductor type")
            return False

    @pyaedt_function_handler(setup_name="name", setuptype="setup_type")
    def create_setup(self, name="MySetupAuto", setup_type=None, **kwargs):
        """Create an analysis setup for 2D Extractor.

        Optional arguments are passed along with the ``setup_type`` and ``name``
        parameters.  Keyword names correspond to the ``setup_type``
        corresponding to the native AEDT API.  The list of
        keywords here is not exhaustive.

        Parameters
        ----------
        name : str, optional
            Name of the setup. The default is "Setup1".
        setup_type : int, str, optional
            Type of the setup. Options are "IcepakSteadyState"
            and "IcepakTransient". The default is "IcepakSteadyState".
        **kwargs : dict, optional
            Available keys depend on the setup chosen.
            For more information, see :doc:`../SetupTemplatesQ3D`.

        Returns
        -------
        :class:`ansys.aedt.core.modules.solve_setup.SetupHFSS`
            Solver Setup object.

        References
        ----------
        >>> oModule.InsertSetup

        Examples
        --------

        >>> from ansys.aedt.core import Q2d
        >>> app = Q2d()
        >>> app.create_setup(name="Setup1",RLDataBlock__MinPass=2)

        """
        if setup_type is None:
            setup_type = self.design_solutions.default_setup
        elif setup_type in SetupKeys.SetupNames:
            setup_type = SetupKeys.SetupNames.index(setup_type)
        if "props" in kwargs:
            return self._create_setup(name=name, setup_type=setup_type, props=kwargs["props"])
        else:
            setup = self._create_setup(name=name, setup_type=setup_type)
        setup.auto_update = False
        for arg_name, arg_value in kwargs.items():
            if setup[arg_name] is not None:
                setup[arg_name] = arg_value
        setup.auto_update = True
        setup.update()
        return setup
