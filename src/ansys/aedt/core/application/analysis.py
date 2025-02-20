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
This module contains the ``analysis`` class.

It includes common classes for file management and messaging and all
calls to AEDT modules like the modeler, mesh, postprocessing, and setup.
"""

import os
import re
import shutil
import subprocess  # nosec
import tempfile
import time

from ansys.aedt.core.application.design import Design
from ansys.aedt.core.application.job_manager import update_hpc_option
from ansys.aedt.core.application.variables import Variable
from ansys.aedt.core.application.variables import decompose_variable_value
from ansys.aedt.core.generic.constants import AXIS
from ansys.aedt.core.generic.constants import GRAVITY
from ansys.aedt.core.generic.constants import PLANE
from ansys.aedt.core.generic.constants import SETUPS
from ansys.aedt.core.generic.constants import SOLUTIONS
from ansys.aedt.core.generic.constants import VIEW
from ansys.aedt.core.generic.general_methods import _arg_with_dim
from ansys.aedt.core.generic.general_methods import filter_tuple
from ansys.aedt.core.generic.general_methods import generate_unique_name
from ansys.aedt.core.generic.general_methods import is_linux
from ansys.aedt.core.generic.general_methods import is_windows
from ansys.aedt.core.generic.general_methods import open_file
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.generic.settings import settings
from ansys.aedt.core.modules.boundary.layout_boundary import NativeComponentObject
from ansys.aedt.core.modules.boundary.layout_boundary import NativeComponentPCB
from ansys.aedt.core.modules.design_xploration import OptimizationSetups
from ansys.aedt.core.modules.design_xploration import ParametricSetups
from ansys.aedt.core.modules.solve_setup import Setup
from ansys.aedt.core.modules.solve_setup import SetupHFSS
from ansys.aedt.core.modules.solve_setup import SetupHFSSAuto
from ansys.aedt.core.modules.solve_setup import SetupIcepak
from ansys.aedt.core.modules.solve_setup import SetupMaxwell
from ansys.aedt.core.modules.solve_setup import SetupQ3D
from ansys.aedt.core.modules.solve_setup import SetupSBR
from ansys.aedt.core.modules.solve_sweeps import SetupProps


class Analysis(Design, object):
    """Contains all common analysis functions.

    This class is inherited in the caller application and is accessible through it ( eg. ``hfss.method_name``).


    It is automatically initialized by a call from an application, such as HFSS or Q3D.
    See the application function for its parameter descriptions.

    Parameters
    ----------
    application : str
        Application that is to initialize the call.
    projectname : str
        Name of the project to select or the full path to the project
        or AEDTZ archive to open.
    designname : str
        Name of the design to select.
    solution_type : str
        Solution type to apply to the design.
    setup_name : str
        Name of the setup to use as the nominal.
    specified_version : str
        Version of AEDT  to use.
    NG : bool
        Whether to run AEDT in the non-graphical mode.
    new_desktop : bool, optional
        Whether to launch an instance of AEDT in a new thread, even if
        another instance of the ``specified_version`` is active on the
        machine.
    close_on_exit : bool
        Whether to release  AEDT on exit.
    student_version : bool
        Whether to enable the student version of AEDT.
    aedt_process_id : int, optional
        Only used when ``new_desktop = False``, specifies by process ID which instance
        of Electronics Desktop to point PyAEDT at.
    ic_mode : bool, optional
        Whether to set the design to IC mode. The default is ``None``, which means to retain the
        existing setting. This parameter applies only to HFSS 3D Layout.
    remove_lock : bool, optional
        Whether to remove lock to project before opening it or not.
        The default is ``False``, which means to not unlock
        the existing project if needed and raise an exception.
    """

    def __init__(
        self,
        application,
        projectname,
        designname,
        solution_type,
        setup_name,
        specified_version,
        non_graphical,
        new_desktop,
        close_on_exit,
        student_version,
        machine="",
        port=0,
        aedt_process_id=None,
        ic_mode=None,
        remove_lock=False,
    ):
        Design.__init__(
            self,
            application,
            projectname,
            designname,
            solution_type,
            specified_version,
            non_graphical,
            new_desktop,
            close_on_exit,
            student_version,
            machine,
            port,
            aedt_process_id,
            ic_mode,
            remove_lock,
        )
        self._excitation_objects = {}
        self._setup = None
        if setup_name:
            self.active_setup = setup_name
        self._materials = None
        self._available_variations = self.AvailableVariations(self)
        self._setups = []
        self._parametrics = []
        self._optimizations = []
        self._native_components = []
        self.SOLUTIONS = SOLUTIONS()
        self.SETUPS = SETUPS()
        self.AXIS = AXIS()
        self.PLANE = PLANE()
        self.VIEW = VIEW()
        self.GRAVITY = GRAVITY()

        if not settings.lazy_load:
            self._materials = self.materials
            self._setups = self.setups
            self._parametrics = self.parametrics
            self._optimizations = self.optimizations

    @property
    def native_components(self):
        """Native Component dictionary.

        Returns
        -------
        dict[str, :class:`ansys.aedt.core.modules.Boundaries.NativeComponentObject`]
        """
        if not self._native_components:
            self._native_components = self._get_native_data()
        return {nc.name: nc for nc in self._native_components}

    @property
    def native_component_names(self):
        """Native component names.

        Returns
        -------
        list
        """
        return self.modeler.user_defined_component_names

    @property
    def output_variables(self):
        """List of output variables.

        Returns
        -------
        list of str

        References
        ----------
        >>> oModule.GetOutputVariables()
        """
        return self.ooutput_variable.GetOutputVariables()

    @property
    def materials(self):
        """Materials in the project.

        Returns
        -------
        :class:`ansys.aedt.core.modules.material_lib.Materials`
           Materials in the project.

        """
        if self._materials is None and self._odesign:
            self.logger.reset_timer()
            from ansys.aedt.core.modules.material_lib import Materials

            self._materials = Materials(self)
            for material in self._materials.material_keys:
                self._materials.material_keys[material]._material_update = True
            self.logger.info_timer("Materials class has been initialized!")

        return self._materials

    @property
    def setups(self):
        """Setups in the project.

        Returns
        -------
        list[:class:`ansys.aedt.core.modules.solve_setup.Setup`]
            Setups in the project.

        """
        if not self._setups:
            if self.design_type not in ["Maxwell Circuit", "Circuit Netlist"]:
                self._setups = [self.get_setup(setup_name) for setup_name in self.setup_names]
        return self._setups

    @property
    def parametrics(self):
        """Setups in the project.

        Returns
        -------
        :class:`ansys.aedt.core.modules.design_xploration.ParametricSetups`
            Parametric setups in the project.

        """
        if not self._parametrics:
            self._parametrics = ParametricSetups(self)
        return self._parametrics

    @property
    def optimizations(self):
        """Optimizations in the project.

        Returns
        -------
        :class:`ansys.aedt.core.modules.design_xploration.OptimizationSetups`
            Parametric setups in the project.

        """
        if not self._optimizations:
            self._optimizations = OptimizationSetups(self)
        return self._optimizations

    @property
    def Position(self):
        """Position of the object.

        Returns
        -------
        type
            Position object.

        """
        if self.modeler:
            return self.modeler.Position
        return

    @property
    def available_variations(self):
        """Available variation object.

        Returns
        -------
        :class:`ansys.aedt.core.application.analysis.Analysis.AvailableVariations`
            Available variation object.

        """
        return self._available_variations

    @property
    def active_setup(self):
        """Get or Set the name of the active setup. If not set it will be the first analysis setup.

        Returns
        -------
        str
            Name of the active or first analysis setup.

        References
        ----------
        >>> oModule.GetAllSolutionSetups()
        """
        if self._setup:
            return self._setup
        elif self.existing_analysis_setups:
            return self.existing_analysis_setups[0]
        else:
            self._setup = None
            return self._setup

    @active_setup.setter
    @pyaedt_function_handler(setup_name="name")
    def active_setup(self, name):
        setup_list = self.existing_analysis_setups
        if setup_list:
            if name not in setup_list:
                raise ValueError(f"Setup name {name} is invalid.")
            self._setup = name
        else:
            raise AttributeError("No setup is defined.")

    @property
    def existing_analysis_sweeps(self):
        """Existing analysis sweeps.

        Returns
        -------
        list of str
            List of all analysis sweeps in the design.

        References
        ----------
        >>> oModule.GelAllSolutionNames
        >>> oModule.GetSweeps
        """
        setup_list = self.existing_analysis_setups
        sweep_list = []
        if self.solution_type == "HFSS3DLayout" or self.solution_type == "HFSS 3D Layout Design":
            sweep_list = self.oanalysis.GetAllSolutionNames()
            sweep_list = [i for i in sweep_list if "Adaptive Pass" not in i]
            sweep_list.reverse()
        else:
            for el in setup_list:
                sweeps = []
                setuptype = self.design_solutions.default_adaptive
                if setuptype:
                    sweep_list.append(el + " : " + setuptype)
                else:
                    sweep_list.append(el)
                if self.design_type in ["HFSS 3D Layout Design"]:
                    sweeps = self.oanalysis.GelAllSolutionNames()
                elif self.solution_type not in ["Eigenmode"]:
                    try:
                        sweeps = list(self.oanalysis.GetSweeps(el))
                    except Exception:
                        sweeps = []
                for sw in sweeps:
                    if el + " : " + sw not in sweep_list:
                        sweep_list.append(el + " : " + sw)
        return sweep_list

    @property
    def nominal_adaptive(self):
        """Nominal adaptive sweep.

        Returns
        -------
        str
            Name of the nominal adaptive sweep.

        References
        ----------
        >>> oModule.GelAllSolutionNames
        >>> oModule.GetSweeps
        """
        if len(self.existing_analysis_sweeps) > 0:
            return self.existing_analysis_sweeps[0]
        else:
            return ""

    @property
    def nominal_sweep(self):
        """Nominal sweep.

        Returns
        -------
        str
            Name of the last adaptive sweep if a sweep is available or
            the name of the nominal adaptive sweep if present.

        References
        ----------
        >>> oModule.GelAllSolutionNames
        >>> oModule.GetSweeps
        """
        if len(self.existing_analysis_sweeps) > 1:
            return self.existing_analysis_sweeps[1]
        else:
            return self.nominal_adaptive

    @property
    def existing_analysis_setups(self):
        """Existing analysis setups.

        Returns
        -------
        list of str
            List of all analysis setups in the design.

        References
        ----------
        >>> oModule.GetSetups
        """
        setups = []
        if self.oanalysis and "GetSetups" in self.oanalysis.__dir__():
            setups = self.oanalysis.GetSetups()
        if setups:
            return list(setups)
        return []

    @property
    def setup_names(self):
        """Setup names.

        Returns
        -------
        list of str
            List of names of all analysis setups in the design.

        References
        ----------
        >>> oModule.GetSetups
        """
        setup_names = []
        if self.oanalysis and "GetSetups" in self.oanalysis.__dir__():
            setup_names = self.oanalysis.GetSetups()
        return setup_names

    @property
    def SimulationSetupTypes(self):
        """Simulation setup types.

        Returns
        -------
        SETUPS
            List of all simulation setup types categorized by application.
        """
        return SETUPS()

    @property
    def SolutionTypes(self):
        """Solution types.

        Returns
        -------
        SOLUTIONS
            List of all solution type categorized by application.
        """
        return SOLUTIONS()

    @property
    def excitations(self):
        """Get all excitation names.

        Returns
        -------
        list
            List of excitation names. Excitations with multiple modes will return one
            excitation for each mode.

        References
        ----------
        >>> oModule.GetExcitations
        """
        try:
            list_names = list(self.oboundary.GetExcitations())
            del list_names[1::2]
            list_names = list(set(list_names))
            return list_names
        except Exception:
            return []

    @property
    def excitations_by_type(self):
        """Design excitations by type.

        Returns
        -------
        dict
            Dictionary of excitations.
        """
        _dict_out = {}
        for bound in self.excitation_objects.values():
            if bound.type in _dict_out:
                _dict_out[bound.type].append(bound)
            else:
                _dict_out[bound.type] = [bound]
        return _dict_out

    @property
    def excitation_objects(self):
        """Get all excitation.

        Returns
        -------
        dict
            List of excitation boundaries. Excitations with multiple modes will return one
            excitation for each mode.

        References
        ----------
        >>> oModule.GetExcitations
        """
        exc_names = self.excitations[::]

        for el in self.boundaries:
            if el.name in exc_names:
                self._excitation_objects[el.name] = el

        # Delete objects that are not anymore available
        keys_to_remove = [
            internal_excitation
            for internal_excitation in self._excitation_objects
            if internal_excitation not in self.excitations
        ]

        for key in keys_to_remove:
            del self._excitation_objects[key]

        return self._excitation_objects

    @pyaedt_function_handler()
    def _check_intrinsics(self, input_data, input_phase=None, setup=None, return_list=False):
        intrinsics = {}
        if input_data is None:
            if setup is None:
                try:
                    setup = self.existing_analysis_sweeps[0].split(":")[0].strip()
                except Exception:
                    setup = None
            else:
                setup = setup.split(":")[0].strip()
            for set_obj in self.setups:
                if set_obj.name == setup:
                    intrinsics = set_obj.default_intrinsics
                    break

        elif isinstance(input_data, str):
            if "Freq" in self.design_solutions.intrinsics:
                intrinsics["Freq"] = input_data
                if "Phase" in self.design_solutions.intrinsics:
                    intrinsics["Phase"] = input_phase if input_phase else "0deg"
            elif "Time" in self.design_solutions.intrinsics:
                intrinsics["Time"] = input_data
        elif isinstance(input_data, dict):
            for k, v in input_data.items():
                if k in ["Freq", "freq", "frequency", "Frequency"]:
                    intrinsics["Freq"] = v
                elif k in ["Phase", "phase"]:
                    intrinsics["Phase"] = v
                elif k in ["Time", "time"]:
                    intrinsics["Time"] = v
                if input_phase:
                    intrinsics["Phase"] = input_phase
                if "Phase" in self.design_solutions.intrinsics and "Phase" not in intrinsics:
                    intrinsics["Phase"] = "0deg"
        else:
            raise AttributeError("Intrinsics has to be a string or list.")
        if return_list:
            intrinsics_list = []
            for k, v in intrinsics.items():
                intrinsics_list.append(f"{k}:=")
                intrinsics_list.append(v)
            return intrinsics_list
        return intrinsics

    @pyaedt_function_handler()
    def get_traces_for_plot(
        self,
        get_self_terms=True,
        get_mutual_terms=True,
        first_element_filter=None,
        second_element_filter=None,
        category="dB(S",
        differential_pairs=None,
    ):
        # type: (bool, bool, str, str, str, list) -> list
        """Retrieve a list of traces of specified designs ready to use in plot reports.

        Parameters
        ----------
        get_self_terms : bool, optional
            Whether to return self terms. The default is ``True``.
        get_mutual_terms : bool, optional
            Whether to return mutual terms. The default is ``True``.
        first_element_filter : str, optional
            Filter to apply to the first element of the equation.
            This parameter accepts ``*`` and ``?`` as special characters. The default is ``None``.
        second_element_filter : str, optional
            Filter to apply to the second element of the equation.
            This parameter accepts ``*`` and ``?`` as special characters. The default is ``None``.
        category : str, optional
            Plot category name as in the report (including operator).
            The default is ``"dB(S)"``,  which is the plot category name for capacitance.
        differential_pairs : list, optional
            Differential pairs defined. The default is ``None`` in which case an empty list is set.

        Returns
        -------
        list
            List of traces of specified designs ready to use in plot reports.

        Examples
        --------
        >>> from ansys.aedt.core import Hfss3dLayout
        >>> hfss = Hfss3dLayout(project_path)
        >>> hfss.get_traces_for_plot(first_element_filter="Bo?1",
        ...                          second_element_filter="GND*", category="dB(S")
        >>> hfss.get_traces_for_plot(differential_pairs=['Diff_U0_data0','Diff_U1_data0','Diff_U1_data1'],
        ...                          first_element_filter="*_U1_data?",
        ...                          second_element_filter="*_U0_*", category="dB(S")
        """
        differential_pairs = [] if differential_pairs is None else differential_pairs
        if not first_element_filter:
            first_element_filter = "*"
        if not second_element_filter:
            second_element_filter = "*"
        list_output = []
        end_str = ")" * (category.count("(") + 1)
        if differential_pairs:
            excitations = differential_pairs
        else:
            excitations = self.excitations
        if get_self_terms:
            for el in excitations:
                value = f"{category}({el},{el}{end_str}"
                if filter_tuple(value, first_element_filter, second_element_filter):
                    list_output.append(value)
        if get_mutual_terms:
            for el1 in excitations:
                for el2 in excitations:
                    if el1 != el2:
                        value = f"{category}({el1},{el2}{end_str}"
                        if filter_tuple(value, first_element_filter, second_element_filter):
                            list_output.append(value)
        return list_output

    @pyaedt_function_handler(setup_name="setup", sweep_name="sweep")
    def list_of_variations(self, setup=None, sweep=None):
        """Retrieve a list of active variations for input setup.

        Parameters
        ----------
        setup : str, optional
            Setup name. The default is ``None``, in which case the nominal adaptive
            is used.
        sweep : str, optional
            Sweep name. The default is``None``, in which case the nominal adaptive
            is used.

        Returns
        -------
        list
            List of active variations for input setup.

        References
        ----------
        >>> oModule.ListVariations
        """

        if not setup and ":" in self.nominal_sweep:
            setup = self.nominal_adaptive.split(":")[0].strip()
        elif not setup:
            self.logger.warning("No Setup defined.")
            return False
        if not sweep and ":" in self.nominal_sweep:
            sweep = self.nominal_adaptive.split(":")[1].strip()
        elif not sweep:
            self.logger.warning("No Sweep defined.")
            return False
        if (
            self.solution_type == "HFSS3DLayout"
            or self.solution_type == "HFSS 3D Layout Design"
            or self.design_type == "2D Extractor"
        ):
            try:
                return list(self.osolution.ListVariations(f"{setup} : {sweep}"))
            except Exception:
                return [""]
        else:
            try:
                return list(self.odesign.ListVariations(f"{setup} : {sweep}"))
            except Exception:
                return [""]

    @pyaedt_function_handler()
    def export_results(
        self,
        analyze=False,
        export_folder=None,
        matrix_name="Original",
        matrix_type="S",
        touchstone_format="MagPhase",
        touchstone_number_precision=15,
        length="1meter",
        impedance=50,
        include_gamma_comment=True,
        support_non_standard_touchstone_extension=False,
        variations=None,
    ):
        """Export all available reports to a file, including profile, and convergence and sNp when applicable.

        Parameters
        ----------
        analyze : bool
            Whether to analyze before export. Solutions must be present for the design.
        export_folder : str, optional
            Full path to the project folder. The default is ``None``, in which case the
            working directory is used.
        matrix_name : str, optional
            Matrix to specify to export touchstone file.
            The default is ``Original``, in which case default matrix is taken.
            This argument applies only to 2DExtractor and Q3D setups where Matrix reduction is computed
            and needed to export touchstone file.
        matrix_type : str, optional
            Type of matrix to export. The default is ``S`` to export a touchstone file.
            Available values are ``S``, ``Y``, ``Z``.  ``Y`` and ``Z`` matrices will be exported as tab file.
        touchstone_format : str, optional
            Touchstone format. The default is ``MagPahse``.
            Available values are: ``MagPahse``, ``DbPhase``, ``RealImag``.
        length : str, optional
            Length of the model to export. The default is ``1meter``.
        impedance : float, optional
            Real impedance value in ohms, for renormalization. The default is ``50``.
        touchstone_number_precision : int, optional
            Touchstone number of digits precision. The default is ``15``.
        include_gamma_comment : bool, optional
            Specifies whether to include Gamma and Impedance comments. The default is ``True``.
        support_non_standard_touchstone_extension : bool, optional
            Specifies whether to support non-standard Touchstone extensions for mixed reference impedance.
            The default is ``False``.
        variations : list, optional
            List of variation values with units. The default is all variations.

        Returns
        -------
        list
            List of all exported files.

        References
        ----------
        >>> oModule.GetAllPortsList
        >>> oDesign.ExportProfile
        >>> oModule.ExportToFile
        >>> oModule.ExportConvergence
        >>> oModule.ExportNetworkData

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> aedtapp = Hfss()
        >>> aedtapp.analyze()
        >>> exported_files = aedtapp.export_results()
        """
        exported_files = []
        if not export_folder:
            export_folder = self.working_directory
        if analyze:
            self.analyze()
        # excitations
        if self.design_type == "HFSS3DLayout" or self.design_type == "HFSS 3D Layout Design":
            excitations = len(self.oexcitation.GetAllPortsList())
        elif self.design_type == "2D Extractor":
            excitations = self.oboundary.GetNumExcitations("SignalLine")
        elif self.design_type == "Q3D Extractor":
            excitations = self.oboundary.GetNumExcitations("Source")
        elif self.design_type == "Circuit Design":
            excitations = len(self.excitations)
        else:
            excitations = len(self.osolution.GetAllSources())
        # reports
        for report_name in self.post.all_report_names:
            name_no_space = report_name.replace(" ", "_")
            self.post.oreportsetup.UpdateReports([str(report_name)])
            export_path = os.path.join(export_folder, f"{self.project_name}_{self.design_name}_{name_no_space}.csv")
            try:
                self.post.oreportsetup.ExportToFile(str(report_name), export_path)
                self.logger.info(f"Export Data: {export_path}")
            except Exception:
                self.logger.info("Failed to export to file.")
            exported_files.append(export_path)

        if touchstone_format == "MagPhase":
            touchstone_format_value = 0
        elif touchstone_format == "RealImag":
            touchstone_format_value = 1
        elif touchstone_format == "DbPhase":
            touchstone_format_value = 2
        else:
            self.logger.warning("Touchstone format not valid. ``MagPhase`` will be set as default")
            touchstone_format_value = 0

        # setups
        setups = self.setups
        for s in setups:
            if self.design_type == "Circuit Design":
                exported_files.append(self.browse_log_file(export_folder))
            else:
                if s.is_solved:
                    setup_name = s.name
                    sweeps = s.sweeps
                    if len(sweeps) == 0:
                        sweeps = ["LastAdaptive"]
                    # variations
                    variations_list = variations
                    if not variations:
                        variations_list = []
                        if not self.available_variations.nominal_w_values_dict:
                            variations_list.append("")
                        else:
                            for x in range(0, len(self.available_variations.nominal_w_values_dict)):
                                variation = (
                                    f"{list(self.available_variations.nominal_w_values_dict.keys())[x]}="
                                    f"'{list(self.available_variations.nominal_w_values_dict.values())[x]}'"
                                )
                                variations_list.append(variation)
                    # sweeps
                    for sweep in sweeps:
                        if sweep == "LastAdaptive":
                            sweep_name = sweep
                        else:
                            sweep_name = sweep.name
                        varCount = 0
                        for variation in variations_list:
                            varCount += 1
                            export_path = os.path.join(export_folder, f"{self.project_name}_{varCount}.prof")
                            result = self.export_profile(setup_name, variation, export_path)
                            if result:
                                exported_files.append(export_path)
                            export_path = os.path.join(export_folder, f"{self.project_name}_{varCount}.conv")
                            self.logger.info("Export Convergence: %s", export_path)
                            result = self.export_convergence(setup_name, variation, export_path)
                            if result:
                                exported_files.append(export_path)

                            freq_array = []
                            if self.design_type in ["2D Extractor", "Q3D Extractor"]:
                                freq_model_unit = decompose_variable_value(s.props["AdaptiveFreq"])[1]
                                if sweep == "LastAdaptive":
                                    # If sweep is Last Adaptive for Q2D and Q3D
                                    # the default range freq is [10MHz, 100MHz, step: 10MHz]
                                    # Q2D and Q3D don't accept in ExportNetworkData ["All"]
                                    # as frequency array
                                    freq_range = range(10, 100, 10)
                                    for freq in freq_range:
                                        v = Variable(f"{freq}MHz")
                                        freq_array.append(v.rescale_to("Hz").numeric_value)
                                else:
                                    for freq in sweep.frequencies:
                                        v = Variable(f"{freq:.12f}{freq_model_unit}")
                                        freq_array.append(v.rescale_to("Hz").numeric_value)

                            # export touchstone as .sNp file
                            if self.design_type in ["HFSS3DLayout", "HFSS 3D Layout Design", "HFSS"]:
                                if matrix_type != "S":
                                    export_path = os.path.join(export_folder, f"{self.project_name}_{varCount}.tab")
                                else:
                                    export_path = os.path.join(
                                        export_folder, f"{self.project_name}_{varCount}.s{excitations}p"
                                    )
                                self.logger.info(f"Export SnP: {export_path}")
                                if self.design_type == "HFSS 3D Layout Design":
                                    module = self.odesign
                                else:
                                    module = self.osolution
                                try:
                                    self.logger.info(f"Export SnP: {export_path}")
                                    module.ExportNetworkData(
                                        variation,
                                        [f"{setup_name}:{sweep_name}"],
                                        3 if matrix_type == "S" else 2,
                                        export_path,
                                        ["All"],
                                        True,
                                        impedance,
                                        matrix_type,
                                        -1,
                                        touchstone_format_value,
                                        touchstone_number_precision,
                                        True,
                                        include_gamma_comment,
                                        support_non_standard_touchstone_extension,
                                    )
                                    exported_files.append(export_path)
                                    self.logger.info("Exported Touchstone: %s", export_path)
                                except Exception:
                                    self.logger.warning("Export SnP failed: no solutions found")
                            elif self.design_type == "2D Extractor":
                                export_path = os.path.join(
                                    export_folder, f"{self.project_name}_{varCount}.s{2 * excitations}p"
                                )
                                self.logger.info(f"Export SnP: {export_path}")
                                try:
                                    self.logger.info(f"Export SnP: {export_path}")
                                    self.odesign.ExportNetworkData(
                                        variation,
                                        f"{setup_name}:{sweep_name}",
                                        export_path,
                                        matrix_name,
                                        impedance,
                                        freq_array,
                                        touchstone_format,
                                        length,
                                        0,
                                    )
                                    exported_files.append(export_path)
                                    self.logger.info("Exported Touchstone: %s", export_path)
                                except Exception:
                                    self.logger.warning("Export SnP failed: no solutions found")
                            elif self.design_type == "Q3D Extractor":
                                export_path = os.path.join(
                                    export_folder, f"{self.project_name}_{varCount}.s{2 * excitations}p"
                                )
                                self.logger.info(f"Export SnP: {export_path}")
                                try:
                                    self.logger.info(f"Export SnP: {export_path}")
                                    self.odesign.ExportNetworkData(
                                        variation,
                                        f"{setup_name}:{sweep_name}",
                                        export_path,
                                        matrix_name,
                                        impedance,
                                        freq_array,
                                        touchstone_format,
                                        0,
                                    )
                                    exported_files.append(export_path)
                                    self.logger.info("Exported Touchstone: %s", export_path)
                                except Exception:
                                    self.logger.warning("Export SnP failed: no solutions found")
                else:
                    self.logger.warning("Setup is not solved. To export results please analyze setup first.")
        return exported_files

    @pyaedt_function_handler(setup_name="setup", variation_string="variations", file_path="output_file")
    def export_convergence(self, setup, variations="", output_file=None):
        """Export a solution convergence to a file.

        Parameters
        ----------
        setup : str
            Setup name. For example, ``'Setup1'``.
        variations : str
            Variation string with values. For example, ``'radius=3mm'``.
        output_file : str, optional
            Full path to the PROF file. The default is ``None``, in which
            case the working directory is used.


        Returns
        -------
        str
            Output file path if created.

        References
        ----------
        >>> oModule.ExportConvergence
        """
        if " : " in setup:
            setup = setup.split(" : ")[0]
        if not output_file:
            output_file = os.path.join(self.working_directory, generate_unique_name("Convergence") + ".prop")
        if not variations:
            val_str = []
            for el, val in self.available_variations.nominal_w_values_dict.items():
                val_str.append(f"{el}={val}")
            variations = ",".join(val_str)
        if self.design_type == "2D Extractor":
            for s in self.setups:
                if s.name == setup:
                    if "CGDataBlock" in s.props:
                        output_file = os.path.splitext(output_file)[0] + "CG" + os.path.splitext(output_file)[1]
                        self.odesign.ExportConvergence(setup, variations, "CG", output_file, True)
                        self.logger.info("Export Convergence to  %s", output_file)
                    if "RLDataBlock" in s.props:
                        output_file = os.path.splitext(output_file)[0] + "RL" + os.path.splitext(output_file)[1]
                        self.odesign.ExportConvergence(setup, variations, "RL", output_file, True)
                        self.logger.info("Export Convergence to  %s", output_file)

                    break
        elif self.design_type == "Q3D Extractor":
            for s in self.setups:
                if s.name == setup:
                    if "Cap" in s.props:
                        output_file = os.path.splitext(output_file)[0] + "CG" + os.path.splitext(output_file)[1]
                        self.odesign.ExportConvergence(setup, variations, "CG", output_file, True)
                        self.logger.info("Export Convergence to  %s", output_file)
                    if "AC" in s.props:
                        output_file = os.path.splitext(output_file)[0] + "ACRL" + os.path.splitext(output_file)[1]
                        self.odesign.ExportConvergence(setup, variations, "AC RL", output_file, True)
                        self.logger.info("Export Convergence to  %s", output_file)
                    if "DC" in s.props:
                        output_file = os.path.splitext(output_file)[0] + "DC" + os.path.splitext(output_file)[1]
                        self.odesign.ExportConvergence(setup, variations, "DC RL", output_file, True)
                        self.logger.info("Export Convergence to  %s", output_file)
                    break
        else:
            self.odesign.ExportConvergence(setup, variations, output_file)
            self.logger.info("Export Convergence to  %s", output_file)
        return output_file

    @pyaedt_function_handler()
    def _get_native_data(self):
        """Retrieve Native Components data."""
        boundaries = []
        try:
            data_vals = self.design_properties["ModelSetup"]["GeometryCore"]["GeometryOperations"][
                "SubModelDefinitions"
            ]["NativeComponentDefinition"]
            if not isinstance(data_vals, list) and isinstance(data_vals, dict):
                data_vals = [data_vals]
            for ds in data_vals:
                try:
                    component_name = "undefined"
                    if isinstance(ds, dict):
                        component_type = ds["NativeComponentDefinitionProvider"]["Type"]
                        component_name = ds["BasicComponentInfo"]["ComponentName"]
                        if component_type == "PCB":
                            native_component_object = NativeComponentPCB(self, component_type, component_name, ds)
                        else:
                            native_component_object = NativeComponentObject(self, component_type, component_name, ds)
                        boundaries.append(native_component_object)
                except Exception:
                    msg = "Failed to add native component object."
                    msg_end = "." if component_name == "undefined" else f"(named {component_name})."
                    self.logger.debug(msg + msg_end)
        except Exception:
            self.logger.debug("Failed to add native component object.")
        return boundaries

    class AvailableVariations(object):
        def __init__(self, app):
            """Contains available variations.

            Parameters
            ----------
            app :
                Inherited parent object.

            Returns
            -------
            object
                Parent object.

            """
            self._app = app

        @property
        def variables(self):
            """Variables.

            Returns
            -------
            list of str
                List of names of independent variables.
            """
            return self._app.variable_manager.independent_variable_names

        @pyaedt_function_handler()
        def variations(self, setup_sweep=None, output_as_dict=False):
            """Variations.

            Parameters
            ----------
            setup_sweep : str, optional
                Setup name with the sweep to search for variations on. The default is ``None``.
            output_as_dict : bool, optional
                Whether to output the variations as a dict. The default is ``False``.

            Returns
            -------
            list of lists, List of dicts
                List of variation families.

            References
            ----------
            >>> oModule.GetAvailableVariations
            """
            variations_string = self.get_variation_strings(setup_sweep)
            variables = [k for k, v in self._app.variable_manager.variables.items() if not v.post_processing]
            families = []
            if variations_string:
                for vs in variations_string:
                    vsplit = vs.split(" ")
                    variation = []
                    for v in vsplit:
                        m = re.search(r"(.+?)='(.+?)'", v)
                        if m and len(m.groups()) == 2:
                            variation.append([m.group(1), m.group(2)])
                        else:  # pragma: no cover
                            raise Exception("Error in splitting the variation variable.")
                    family_list = []
                    family_dict = {}
                    count = 0
                    for var in variables:
                        family_list.append(var + ":=")
                        for v in variation:
                            if var == v[0]:
                                family_list.append([v[1]])
                                family_dict[v[0]] = v[1]
                                count += 1
                                break
                    if count != len(variation):  # pragma: no cover
                        raise IndexError("Not all variations were found in variables.")
                    if output_as_dict:
                        families.append(family_dict)
                    else:
                        families.append(family_list)
            return families

        @pyaedt_function_handler()
        def get_variation_strings(self, setup_sweep=None):
            """Return variation strings.

            Parameters
            ----------
            setup_sweep : str, optional
                Setup name with the sweep to search for variations on.
                The default is ``None`` in which case the first of the existing analysis setups is taken.

            Returns
            -------
            list of str
                List of variation families.

            References
            ----------
            >>> oModule.GetAvailableVariations
            """
            if not setup_sweep:
                setup_sweep = self._app.existing_analysis_sweeps[0]
            return self._app.osolution.GetAvailableVariations(setup_sweep)

        @property
        def nominal(self):
            """Nominal."""
            families = []
            for el in self.variables:
                families.append(el + ":=")
                families.append(["Nominal"])
            return families

        @property
        def nominal_w_values(self):
            """Nominal independent with values in a list.

            Returns
            -------
            list
                List of nominal independent variations with expressions.

            References
            ----------
            >>> oDesign.GetChildObject('Variables').GetChildNames
            >>> oDesign.GetVariables
            >>> oDesign.GetVariableValue
            >>> oDesign.GetNominalVariation
            """
            families = []
            for k, v in list(self._app.variable_manager.independent_variables.items()):
                families.append(k + ":=")
                families.append([v.expression])
            return families

        @property
        def nominal_w_values_dict(self):
            """Nominal independent with values in a dictionary.

            Returns
            -------
            dict
                Dictionary of nominal independent variations with values.

            References
            ----------
            >>> oDesign.GetChildObject('Variables').GetChildNames
            >>> oDesign.GetVariables
            >>> oDesign.GetVariableValue
            >>> oDesign.GetNominalVariation
            """
            families = {}
            for k, v in list(self._app.variable_manager.independent_variables.items()):
                families[k] = v.expression

            return families

        @property
        def nominal_w_values_dict_w_dependent(self):
            """Nominal independent and dependent with values in a dictionary.

            Returns
            -------
            dict
                Dictionary of nominal independent and dependent variations with values.

            References
            ----------
            >>> oDesign.GetChildObject('Variables').GetChildNames
            >>> oDesign.GetVariables
            >>> oDesign.GetVariableValue
            >>> oDesign.GetNominalVariation"""
            families = {}
            for k, v in list(self._app.variable_manager.variables.items()):
                families[k] = v.expression

            return families

        @property
        def all(self):
            """List of all independent variables with `["All"]` value."""
            families = []
            for el in self.variables:
                families.append(el + ":=")
                families.append(["All"])
            return families

    class AxisDir(object):
        """Contains constants for the axis directions."""

        (XNeg, YNeg, ZNeg, XPos, YPos, ZPos) = range(0, 6)

    @pyaedt_function_handler()
    def get_setups(self):
        """Retrieve setups.

        Returns
        -------
        list of str
            List of names of all setups.

        References
        ----------
        >>> oModule.GetSetups
        """
        setups = self.oanalysis.GetSetups()
        return list(setups)

    @pyaedt_function_handler()
    def get_nominal_variation(self, with_values=False):
        """Retrieve the nominal variation.

        Parameters
        ----------
        with_values : bool
            Whether to return nominal variation or nominal variation with values.
            The default is ``False``.

        Returns
        -------
        list of str
            List of nominal variations.
        """
        if not with_values:
            return self.available_variations.nominal
        else:
            return self.available_variations.nominal_w_values

    @pyaedt_function_handler()
    def get_sweeps(self, name):
        """Retrieve all sweeps for a setup.

        Parameters
        ----------
        name : str
            Name of the setup.

        Returns
        -------
        list of str
            List of names of all sweeps for the setup.

        References
        ----------
        >>> oModule.GetSweeps
        """
        sweeps = self.oanalysis.GetSweeps(name)
        return list(sweeps)

    @pyaedt_function_handler(sweepname="sweep", filename="output_file", exportunits="export_units")
    def export_parametric_results(self, sweep, output_file, export_units=True):
        """Export a list of all parametric variations solved for a sweep to a CSV file.

        Parameters
        ----------
        sweep : str
            Name of the optimetrics sweep.
        output_file : str
            Full path and name of the CSV file to export the results to.
        export_units : bool, optional
            Whether to export units with the value. The default is ``True``. When ``False``,
            only the value is exported.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.ExportParametricResults
        """
        self.ooptimetrics.ExportParametricResults(sweep, output_file, export_units)
        return True

    @pyaedt_function_handler(setup_name="name")
    def generate_unique_setup_name(self, name=None):
        """Generate a new setup with a unique name.

        Parameters
        ----------
        name : str, optional
            Name of the setup. The default is ``None``.

        Returns
        -------
        str
            Name of the setup.

        """
        if not name:
            name = "Setup"
        index = 2
        while name in self.existing_analysis_setups:
            name = name + f"_{index}"
            index += 1
        return name

    @pyaedt_function_handler(setupname="name", setuptype="setup_type")
    def _create_setup(self, name="MySetupAuto", setup_type=None, props=None):
        if props is None:
            props = {}

        if setup_type is None:
            setup_type = self.design_solutions.default_setup
        name = self.generate_unique_setup_name(name)
        if setup_type == 0:
            setup = SetupHFSSAuto(self, setup_type, name)
        elif setup_type == 4:
            setup = SetupSBR(self, setup_type, name)
        elif setup_type in [5, 6, 7, 8, 9, 10, 56, 58, 59, 60]:
            setup = SetupMaxwell(self, setup_type, name)
        elif setup_type in [14, 30]:
            setup = SetupQ3D(self, setup_type, name)
        elif setup_type in [11, 36]:
            setup = SetupIcepak(self, setup_type, name)
        else:
            setup = SetupHFSS(self, setup_type, name)

        if self.design_type == "HFSS":
            # Handle the situation when ports have not been defined.

            if not self.excitations and "MaxDeltaS" in setup.props:
                new_dict = {}
                setup.auto_update = False
                for k, v in setup.props.items():
                    if k == "MaxDeltaS":
                        new_dict["MaxDeltaE"] = 0.01
                    else:
                        new_dict[k] = v
                setup.props = SetupProps(setup, new_dict)
                setup.auto_update = True

            if self.solution_type == "SBR+":
                setup.auto_update = False
                default_sbr_setup = {
                    "RayDensityPerWavelength": 4,
                    "MaxNumberOfBounces": 5,
                    "EnableCWRays": False,
                    "EnableSBRSelfCoupling": False,
                    "UseSBRAdvOptionsGOBlockage": False,
                    "UseSBRAdvOptionsWedges": False,
                    "PTDUTDSimulationSettings": "None",
                    "SkipSBRSolveDuringAdaptivePasses": True,
                    "UseSBREnhancedRadiatedPowerCalculation": False,
                    "AdaptFEBIWithRadiation": False,
                }
                if settings.aedt_version >= "2024.2":
                    default_sbr_setup["IsMonostaticRCS"] = True
                    default_sbr_setup["FastFrequencyLooping"] = False
                user_domain = None
                if props:
                    if "RadiationSetup" in props:
                        user_domain = props["RadiationSetup"]
                if self.field_setups:
                    for field_setup in self.field_setups:
                        if user_domain and user_domain in field_setup.name:
                            domain = user_domain
                            default_sbr_setup["RadiationSetup"] = domain
                            break
                    if not user_domain and self.field_setups:
                        domain = self.field_setups[0].name
                        default_sbr_setup["RadiationSetup"] = domain

                elif user_domain:
                    domain = user_domain
                    default_sbr_setup["RadiationSetup"] = domain

                else:
                    self.logger.warning("Field Observation Domain not defined")
                    default_sbr_setup["RadiationSetup"] = ""
                    default_sbr_setup["ComputeFarFields"] = False

                new_dict = setup.props
                for k, v in default_sbr_setup.items():
                    new_dict[k] = v
                setup.props = SetupProps(setup, new_dict)
                setup.auto_update = True

        tmp_setups = self.setups
        setup.create()
        if props:
            for el in props:
                setup.props[el] = props[el]
            setup.update()

        self.active_setup = name

        self._setups = tmp_setups + [setup]

        return setup

    @pyaedt_function_handler(setupname="name")
    def delete_setup(self, name):
        """Delete a setup.

        Parameters
        ----------
        name : str
            Name of the setup.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.DeleteSetups

        Examples
        --------
        Create a setup and then delete it.

        >>> import ansys.aedt.core
        >>> hfss = ansys.aedt.core.Hfss()
        >>> setup1 = hfss.create_setup(name='Setup1')
        >>> hfss.delete_setup()
        ...
        PyAEDT INFO: Sweep was deleted correctly.
        """
        if name in self.existing_analysis_setups:
            self.oanalysis.DeleteSetups([name])
            for s in self._setups:
                if s.name == name:
                    self._setups.remove(s)
            return True
        return False

    @pyaedt_function_handler(setupname="name", properties_dict="properties")
    def edit_setup(self, name, properties):
        """Modify a setup.

        Parameters
        ----------
        name : str
            Name of the setup.
        properties : dict
            Dictionary containing the property to update with the value.

        Returns
        -------
        :class:`ansys.aedt.core.modules.solve_setup.Setup`

        References
        ----------
        >>> oModule.EditSetup
        """

        setuptype = self.design_solutions.default_setup
        setup = Setup(self, setuptype, name)
        setup.update(properties)
        self.active_setup = name
        return setup

    @pyaedt_function_handler(setupname="name")
    def get_setup(self, name):
        """Get the setup from the current design.

        Parameters
        ----------
        name : str
            Name of the setup.

        Returns
        -------
        :class:`ansys.aedt.core.modules.solve_setup.Setup`

        """
        setuptype = self.design_solutions.default_setup

        if self.solution_type == "SBR+":
            setuptype = 4
            setup = SetupSBR(self, setuptype, name, is_new_setup=False)
        elif self.design_type == "HFSS":
            setup = SetupHFSS(self, setuptype, name, is_new_setup=False)
            if setup.properties:
                if "Auto Solver Setting" in setup.properties:
                    setup = SetupHFSSAuto(self, 0, name, is_new_setup=False)
            elif setup.props and setup.props.get("SetupType", "") == "HfssDrivenAuto":
                setup = SetupHFSSAuto(self, 0, name, is_new_setup=False)
        elif self.design_type in ["Q3D Extractor", "2D Extractor"]:
            setup = SetupQ3D(self, setuptype, name, is_new_setup=False)
        elif self.design_type in ["Maxwell 2D", "Maxwell 3D"]:
            setup = SetupMaxwell(self, setuptype, name, is_new_setup=False)
        else:
            setup = Setup(self, setuptype, name, is_new_setup=False)
        self.active_setup = name
        return setup

    @pyaedt_function_handler()
    def create_output_variable(self, variable, expression, solution=None, context=None):
        """Create or modify an output variable.

        Parameters
        ----------
        variable : str, optional
            Name of the variable.
        expression : str, optional
            Value for the variable.
        solution : str, optional
            Name of the solution in the format `"name : sweep_name"`.
            If `None`, the first available solution is used. Default is `None`.
        context : list, str, optional
            Context under which the output variable will produce results.

        Returns
        -------
        bool
           ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.CreateOutputVariable
        """
        if context is None:
            context = []
        if not context and self.solution_type == "Q3D Extractor":
            context = ["Context:=", "Original"]

        oModule = self.ooutput_variable
        if solution is None:
            solution = self.existing_analysis_sweeps[0]
        if variable in self.output_variables:
            oModule.EditOutputVariable(
                variable, expression, variable, solution, self.design_solutions.report_type, context
            )
        else:
            oModule.CreateOutputVariable(variable, expression, solution, self.design_solutions.report_type, context)
        return True

    @pyaedt_function_handler()
    def get_output_variable(self, variable, solution=None):
        """Retrieve the value of the output variable.

        Parameters
        ----------
        variable : str
            Name of the variable.
        solution :
            Name of the solution in the format `"name : sweep_name"`.
            If `None`, the first available solution is used. Default is `None`.

        Returns
        -------
        type
            Value of the output variable.

        References
        ----------
        >>> oDesign.GetNominalVariation
        >>> oModule.GetOutputVariableValue
        """
        if variable not in self.output_variables:
            raise KeyError(f"Output variable {variable} does not exist.")
        nominal_variation = self.odesign.GetNominalVariation()
        if solution is None:
            solution = self.existing_analysis_sweeps[0]
        value = self.ooutput_variable.GetOutputVariableValue(
            variable, nominal_variation, solution, self.solution_type, []
        )
        return value

    @pyaedt_function_handler(object_list="assignment")
    def get_object_material_properties(self, assignment=None, prop_names=None):
        """Retrieve the material properties for a list of objects and return them in a dictionary.

        This high-level function ignores objects with no defined material properties.

        Parameters
        ----------
        assignment : list, optional
            List of objects to get material properties for. The default is ``None``,
            in which case material properties are retrieved for all objects.
        prop_names : str or list
            Property or list of properties to export. The default is ``None``, in
            which case all properties are exported.

        Returns
        -------
        dict
            Dictionary of objects with material properties.
        """
        if assignment:
            if not isinstance(assignment, list):
                assignment = [assignment]
        else:
            assignment = self.modeler.object_names

        if prop_names:
            if not isinstance(prop_names, list):
                prop_names = [prop_names]

        dict = {}
        for entry in assignment:
            mat_name = self.modeler[entry].material_name.casefold()
            mat_props = self.materials.material_keys[mat_name]
            if prop_names is None:
                dict[entry] = mat_props._props
            else:
                dict[entry] = {}
                for prop_name in prop_names:
                    dict[entry][prop_name] = mat_props._props[prop_name]
        return dict

    @pyaedt_function_handler(setup_name="setup", num_cores="cores", num_tasks="tasks", num_gpu="gpus")
    def analyze(
        self,
        setup=None,
        cores=4,
        tasks=1,
        gpus=1,
        acf_file=None,
        use_auto_settings=True,
        solve_in_batch=False,
        machine="localhost",
        run_in_thread=False,
        revert_to_initial_mesh=False,
        blocking=True,
    ):
        """Solve the active design.

        Parameters
        ----------
        setup : str, optional
            Setup to analyze. The default is ``None``, in which case all
            setups are solved.
        cores : int, optional
            Number of simulation cores. Default is ``4`` which is the number of cores available in license.
        tasks : int, optional
            Number of simulation tasks. The default is ``1``.
            In bach solve, set ``tasks`` to ``-1`` to apply auto settings and distributed mode.
        gpus : int, optional
            Number of simulation graphic processing units to use. The default is ``0``.
        acf_file : str, optional
            Full path to the custom ACF file.
        use_auto_settings : bool, optional
            Set ``True`` to use automatic settings for HPC. The option is only considered for setups
            that support automatic settings.
        solve_in_batch : bool, optional
            Whether to solve the project in batch or not.
            If ``True`` the project will be saved, closed, solved and repened.
        machine : str, optional
            Name of the machine if remote.  The default is ``"localhost"``.
        run_in_thread : bool, optional
            Whether to submit the batch command as a thread. The default is
            ``False``.
        revert_to_initial_mesh : bool, optional
            Whether to revert to initial mesh before solving or not. Default is ``False``.
        blocking : bool, optional
            Whether to block script while analysis is completed or not. It works from AEDT 2023 R2.
            Default is ``True``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesign.Analyze
        """
        if solve_in_batch:
            return self.solve_in_batch(
                file_name=None,
                machine=machine,
                run_in_thread=run_in_thread,
                cores=cores,
                tasks=tasks,
                revert_to_initial_mesh=revert_to_initial_mesh,
            )
        else:
            return self.analyze_setup(
                setup,
                cores,
                tasks,
                gpus,
                acf_file,
                use_auto_settings,
                revert_to_initial_mesh=revert_to_initial_mesh,
                blocking=blocking,
            )

    @pyaedt_function_handler(num_cores="cores", num_tasks="tasks", num_gpu="gpus")
    def analyze_setup(
        self,
        name=None,
        cores=4,
        tasks=1,
        gpus=0,
        acf_file=None,
        use_auto_settings=True,
        num_variations_to_distribute=None,
        allowed_distribution_types=None,
        revert_to_initial_mesh=False,
        blocking=True,
    ):
        """Analyze a design setup.

        Parameters
        ----------
        name : str, optional
            Name of the setup, which can be an optimetric setup or a simple setup.
            The default is ``None``, in which case all setups are solved.
        cores : int, optional
            Number of simulation cores.  The default is ``4``.
        tasks : int, optional
            Number of simulation tasks.  The default is ``1``.
        gpus : int, optional
            Number of simulation graphics processing units.  The default is ``0``.
        acf_file : str, optional
            Full path to the custom ACF file. The default is ``None``.
        use_auto_settings : bool, optional
            Either use or not auto settings in task/cores. It is not supported by all Setup.
        num_variations_to_distribute : int, optional
            Number of variations to distribute. For this to take effect ``use_auto_settings`` must be set to ``True``.
        allowed_distribution_types : list, optional
            List of strings. Each string represents a distribution type. The default value ``None`` does nothing.
            An empty list ``[]`` disables all types.
        revert_to_initial_mesh : bool, optional
            Whether to revert to initial mesh before solving or not. Default is ``False``.
        blocking : bool, optional
            Whether to block script while analysis is completed or not. It works from AEDT 2023 R2.
            Default is ``True``.

        Returns
        -------
        bool
           ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesign.Analyze
        """
        start = time.time()
        set_custom_dso = False
        active_config = self._desktop.GetRegistryString(r"Desktop/ActiveDSOConfigurations/" + self.design_type)
        if acf_file:  # pragma: no cover
            self._desktop.SetRegistryFromFile(acf_file)
            acf_name = ""
            with open_file(acf_file, "r") as f:
                lines = f.readlines()
                for line in lines:
                    if "ConfigName" in line:
                        acf_name = line.strip().split("=")[1].strip("'")
                        break
            if acf_name:
                success = self.set_registry_key(r"Desktop/ActiveDSOConfigurations/" + self.design_type, acf_name)
                if success:
                    set_custom_dso = True
        elif self.design_type not in ["RMxprtSolution", "ModelCreation"] and (gpus or tasks or cores):
            config_name = "pyaedt_config"
            source_name = os.path.join(self.pyaedt_dir, "misc", "pyaedt_local_config.acf")
            if settings.remote_rpc_session:
                target_name = os.path.join(tempfile.gettempdir(), generate_unique_name("config") + ".acf")
            else:
                target_name = (
                    os.path.join(self.working_directory, config_name + ".acf").replace("\\", "/")
                    if self.working_directory[0] != "\\"
                    else os.path.join(self.working_directory, config_name + ".acf")
                )
            skip_files = False
            try:
                shutil.copy2(source_name, target_name)

            # If source and destination are same
            except shutil.SameFileError:
                self.logger.warning("Source and destination represents the same file.")
            # If there is any permission issue
            except PermissionError:
                self.logger.error("Permission denied.")
                skip_files = True
            # For other errors
            except Exception:
                self.logger.error("Error occurred while copying file.")
                skip_files = True
            if not skip_files:
                if cores:
                    succeeded = update_hpc_option(target_name, "NumCores", cores, False)
                    skip_files = True if not succeeded else skip_files
                if gpus:
                    succeeded = update_hpc_option(target_name, "NumGPUs", gpus, False)
                    skip_files = True if not succeeded else skip_files
                if tasks:
                    succeeded = update_hpc_option(target_name, "NumEngines", tasks, False)
                    skip_files = True if not succeeded else skip_files
                succeeded = update_hpc_option(target_name, "ConfigName", config_name, True)
                skip_files = True if not succeeded else skip_files
                succeeded = update_hpc_option(target_name, "DesignType", self.design_type, True)
                skip_files = True if not succeeded else skip_files
                if self.design_type == "Icepak":
                    use_auto_settings = False
                succeeded = update_hpc_option(target_name, "UseAutoSettings", use_auto_settings, False)
                skip_files = True if not succeeded else skip_files
                if num_variations_to_distribute:
                    succeeded = update_hpc_option(
                        target_name, "NumVariationsToDistribute", num_variations_to_distribute, False
                    )
                    skip_files = True if not succeeded else skip_files
                if isinstance(allowed_distribution_types, list):
                    num_adt = len(allowed_distribution_types)
                    adt_string = "', '".join(allowed_distribution_types)
                    adt_string = f"[{num_adt}: '{adt_string}']"

                    succeeded = update_hpc_option(
                        target_name, "AllowedDistributionTypes", adt_string, False, separator=""
                    )
                    skip_files = True if not succeeded else skip_files

            if settings.remote_rpc_session:
                remote_name = (
                    os.path.join(self.working_directory, config_name + ".acf").replace("\\", "/")
                    if self.working_directory[0] != "\\"
                    else os.path.join(self.working_directory, config_name + ".acf")
                )
                settings.remote_rpc_session.filemanager.upload(target_name, remote_name)
                target_name = remote_name
            if not skip_files:
                try:
                    self._desktop.SetRegistryFromFile(target_name)
                    self.set_registry_key(r"Desktop/ActiveDSOConfigurations/" + self.design_type, config_name)
                    set_custom_dso = True
                except Exception:
                    self.logger.info(f"Failed to set registry from file {target_name}.")
        if not name:
            try:
                self.logger.info("Solving all design setups.")
                if self.desktop_class.aedt_version_id > "2023.1" and self.design_type not in [
                    "RMxprtSolution",
                    "ModelCreation",
                ]:
                    self.odesign.AnalyzeAll(blocking)
                else:
                    self.odesign.AnalyzeAll()
            except Exception:  # pragma: no cover
                if set_custom_dso and active_config:
                    self.set_registry_key(r"Desktop/ActiveDSOConfigurations/" + self.design_type, active_config)
                self.logger.error("Error in solving all setups (AnalyzeAll).")
                return False
        elif name in self.existing_analysis_setups:
            try:
                if revert_to_initial_mesh:
                    self.oanalysis.RevertSetupToInitial(name)
                self.logger.info("Solving design setup %s", name)
                if self.desktop_class.aedt_version_id > "2023.1" and self.design_type not in [
                    "RMxprtSolution",
                    "ModelCreation",
                ]:
                    self.odesign.Analyze(name, blocking)
                else:
                    self.odesign.Analyze(name)
            except Exception:  # pragma: no cover
                if set_custom_dso and active_config:
                    self.set_registry_key(r"Desktop/ActiveDSOConfigurations/" + self.design_type, active_config)
                self.logger.error("Error in Solving Setup %s", name)
                return False
        else:
            try:
                self.logger.info("Solving Optimetrics")
                self.ooptimetrics.SolveSetup(name)
            except Exception:  # pragma: no cover
                if set_custom_dso and active_config:
                    self.set_registry_key(r"Desktop/ActiveDSOConfigurations/" + self.design_type, active_config)
                self.logger.error("Error in Solving or Missing Setup  %s", name)
                return False
        if set_custom_dso and active_config:
            self.set_registry_key(r"Desktop/ActiveDSOConfigurations/" + self.design_type, active_config)
        m, s = divmod(time.time() - start, 60)
        h, m = divmod(m, 60)
        self.logger.info(f"Design setup {name} solved correctly in {round(h, 0)}h {round(m, 0)}m {round(s, 0)}s")
        return True

    @property
    def are_there_simulations_running(self):
        """Check if there are simulation running.

        .. note::
           It works only for AEDT >= ``"2023.2"``.

        Returns
        -------
        float

        """
        return self.desktop_class.are_there_simulations_running

    @pyaedt_function_handler()
    def get_monitor_data(self):
        """Check and get monitor data of an existing analysis.

        .. note::
           It works only for AEDT >= ``"2023.2"``.

        Returns
        -------
        dict

        """
        return self.desktop_class.get_monitor_data()

    @pyaedt_function_handler()
    def stop_simulations(self, clean_stop=True):
        """Check if there are simulation running and stops them.

        .. note::
           It works only for AEDT >= ``"2023.2"``.

        Returns
        -------
        str

        """
        return self.desktop_class.stop_simulations(clean_stop=clean_stop)

    @pyaedt_function_handler(filename="file_name", numcores="cores", num_tasks="tasks", setup_name="setup")
    def solve_in_batch(
        self,
        file_name=None,
        machine="localhost",
        run_in_thread=False,
        cores=4,
        tasks=1,
        setup=None,
        revert_to_initial_mesh=False,
    ):  # pragma: no cover
        """Analyze a design setup in batch mode.

        .. note::
           To use this function, the project must be closed.

        Parameters
        ----------
        file_name : str, optional
            Name of the setup. The default is ``None``, which means that the active project
            is to be solved.
        machine : str, optional
            Name of the machine if remote.  The default is ``"localhost"``.
        run_in_thread : bool, optional
            Whether to submit the batch command as a thread. The default is
            ``False``.
        cores : int, optional
            Number of cores to use in the simulation.
        tasks : int, optional
            Number of tasks to use in the simulation.
            Set ``num_tasks`` to ``-1`` to apply auto settings and distributed mode.
        setup : str
            Name of the setup, which can be an optimetrics setup or a simple setup.
            The default is ``None``, in which case all setups are solved.
        revert_to_initial_mesh : bool, optional
            Whether to revert to the initial mesh before solving. The default is ``False``.

        Returns
        -------
         bool
           ``True`` when successful, ``False`` when failed.
        """
        inst_dir = self.desktop_install_dir
        self.last_run_log = ""
        self.last_run_job = ""
        design_name = None
        if not file_name:
            file_name = self.project_file
            project_name = self.project_name
            design_name = self.design_name
            if revert_to_initial_mesh:
                for setup in self.setup_names:
                    self.oanalysis.RevertSetupToInitial(setup)
            self.close_project()
        else:
            project_name = os.path.splitext(os.path.split(file_name)[-1])[0]
        queue_file = file_name + ".q"
        queue_file_completed = file_name + ".q.completed"
        if os.path.exists(queue_file):
            os.unlink(queue_file)
        if os.path.exists(queue_file_completed):
            os.unlink(queue_file_completed)

        options = [
            "-ng",
            "-BatchSolve",
            "-machinelist",
            f"list={machine}:{tasks}:{cores}:90%:1",
            "-Monitor",
        ]
        if is_linux and settings.use_lsf_scheduler and tasks == -1:
            options.append("-distributed")
            options.append("-auto")
        if setup and design_name:
            options.append(f'{design_name}:{"Nominal" if setup in self.setup_names else "Optimetrics"}:{setup}')
        if is_linux and not settings.use_lsf_scheduler:
            batch_run = [inst_dir + "/ansysedt"]
        elif is_linux and settings.use_lsf_scheduler:  # pragma: no cover
            if settings.lsf_queue:
                batch_run = [
                    "bsub",
                    "-n",
                    str(cores),
                    "-R",
                    f"span[ptile={cores}]",
                    "-R",
                    f"rusage[mem={settings.lsf_ram}]",
                    f"-queue {settings.lsf_queue}",
                    settings.lsf_aedt_command,
                ]
            else:
                batch_run = [
                    "bsub",
                    "-n",
                    str(cores),
                    "-R",
                    f"span[ptile={cores}]",
                    "-R",
                    f"rusage[mem={settings.lsf_ram}]",
                    settings.lsf_aedt_command,
                ]
        else:
            batch_run = [inst_dir + "/ansysedt.exe"]
        batch_run.extend(options)
        batch_run.append(file_name)

        # check for existing solution directory and delete it if it exists so we
        # don't have old .asol files etc

        self.logger.info("Solving model in batch mode on " + machine)
        if run_in_thread and is_windows:
            DETACHED_PROCESS = 0x00000008
            subprocess.Popen(batch_run, creationflags=DETACHED_PROCESS)
            self.logger.info("Batch job launched.")
        else:
            subprocess.Popen(batch_run)
            self.logger.info("Batch job finished.")

        if machine == "localhost":
            while not os.path.exists(queue_file):
                time.sleep(0.5)
            with open_file(queue_file, "r") as f:
                lines = f.readlines()
                for line in lines:
                    if "JobID" in line:
                        ls = line.split("=")[1].strip().strip("'")
                        self.last_run_job = ls
                        self.last_run_log = os.path.join(file_name + ".batchinfo", project_name + "-" + ls + ".log")
            while not os.path.exists(queue_file_completed):
                time.sleep(0.5)
        return True

    @pyaedt_function_handler(clustername="cluster_name", numnodes="nodes", numcores="cores")
    def submit_job(
        self, cluster_name, aedt_full_exe_path=None, nodes=1, cores=32, wait_for_license=True, setting_file=None
    ):  # pragma: no cover
        """Submit a job to be solved on a cluster.

        Parameters
        ----------
        cluster_name : str
            Name of the cluster to submit the job to.
        aedt_full_exe_path : str, optional
            Full path to the AEDT executable file. The default is ``None``, in which
            case ``"/clustername/AnsysEM/AnsysEM2x.x/Win64/ansysedt.exe"`` is used.
        nodes : int, optional
            Number of nodes. The default is ``1``.
        cores : int, optional
            Number of cores. The default is ``32``.
        wait_for_license : bool, optional
             Whether to wait for the license to be validated. The default is ``True``.
        setting_file : str, optional
            Name of the file to use as a template. The default value is ``None``.

        Returns
        -------
        type
            ID of the job.

        References
        ----------
        >>> oDesktop.SubmitJob
        """
        return self.desktop_class.submit_job(
            self.project_file, cluster_name, aedt_full_exe_path, nodes, cores, wait_for_license, setting_file
        )

    @pyaedt_function_handler()
    def _export_touchstone(
        self,
        setup_name=None,
        sweep_name=None,
        file_name=None,
        variations=None,
        variations_value=None,
        renormalization=False,
        impedance=None,
        comments=False,
    ):
        """Export the Touchstone file to a local folder.

        Parameters
        ----------
        setup_name : str, optional
            Name of the setup that has been solved.
        sweep_name : str, optional
            Name of the sweep that has been solved.
            This parameter has to be ignored or set with same value as name
        file_name : str, optional
            Full path and name for the Touchstone file. The default is ``None``,
            which exports the file to the working directory.
        variations : list, optional
            List of all parameter variations. For example, ``["$AmbientTemp", "$PowerIn"]``.
            The default is ``None``.
        variations_value : list, optional
            List of all parameter variation values. For example, ``["22cel", "100"]``.
            The default is ``None``.
        renormalization : bool, optional
            Perform renormalization before export.
            The default is ``False``.
        impedance : float, optional
            Real impedance value in ohm, for renormalization, if not specified considered 50 ohm.
            The default is ``None``.
        comments : bool, optional
            Include Gamma and Impedance values in comments.
            The default is ``False``.

        Returns
        -------
        str
            file name when successful, ``False`` when failed.
        """
        if variations is None:
            variations = list(self.available_variations.nominal_w_values_dict.keys())
            if variations_value is None:
                variations_value = [str(x) for x in list(self.available_variations.nominal_w_values_dict.values())]

        if setup_name is None:
            nominal_sweep_list = [x.strip() for x in self.nominal_sweep.split(":")]
            setup_name = nominal_sweep_list[0]
        if impedance is None:
            impedance = 50
        if self.design_type == "Circuit Design":
            sweep_name = setup_name
        else:
            if sweep_name is None:
                for sol in self.existing_analysis_sweeps:
                    if setup_name == sol.split(":")[0].strip():
                        sweep_name = sol.split(":")[1].strip()
                        break

        if self.design_type == "HFSS 3D Layout Design":
            n = str(len(self.port_list))
        else:
            n = str(len(self.excitations))
        # Normalize the save path
        if not file_name:
            appendix = ""
            for v, vv in zip(variations, variations_value):
                appendix += "_" + v + vv.replace("'", "")
            ext = ".S" + n + "p"
            filename = os.path.join(self.working_directory, setup_name + "_" + sweep_name + appendix + ext)
        else:
            filename = file_name.replace("//", "/").replace("\\", "/")
        self.logger.info("Exporting Touchstone " + filename)
        DesignVariations = ""
        for i in range(len(variations)):
            DesignVariations += str(variations[i]) + "='" + str(variations_value[i].replace("'", "")) + "' "
            # DesignVariations = "$AmbientTemp=\'22cel\' $PowerIn=\'100\'"
        # array containing "SetupName:SolutionName" pairs (note that setup and solution are separated by a colon)
        SolutionSelectionArray = [setup_name + ":" + sweep_name]
        # 2=tab delimited spreadsheet (.tab), 3= touchstone (.sNp), 4= CitiFile (.cit),
        # 7=Matlab (.m), 8=Terminal Z0 spreadsheet
        FileFormat = 3
        OutFile = filename  # full path of output file
        # array containing the frequencies to export, use ["all"] for all frequencies
        FreqsArray = ["all"]
        DoRenorm = renormalization  # perform renormalization before export
        RenormImped = impedance  # Real impedance value in ohm, for renormalization
        DataType = "S"  # Type: "S", "Y", or "Z" matrix to export
        Pass = -1  # The pass to export. -1 = export all passes.
        ComplexFormat = 0  # 0=Magnitude/Phase, 1=Real/Immaginary, 2=dB/Phase
        DigitsPrecision = 15  # Touchstone number of digits precision
        IncludeGammaImpedance = comments  # Include Gamma and Impedance in comments
        NonStandardExtensions = False  # Support for non-standard Touchstone extensions

        if self.design_type == "HFSS":
            self.osolution.ExportNetworkData(
                DesignVariations,
                SolutionSelectionArray,
                FileFormat,
                OutFile,
                FreqsArray,
                DoRenorm,
                RenormImped,
                DataType,
                Pass,
                ComplexFormat,
                DigitsPrecision,
                False,
                IncludeGammaImpedance,
                NonStandardExtensions,
            )
        else:
            self.odesign.ExportNetworkData(
                DesignVariations,
                SolutionSelectionArray,
                FileFormat,
                OutFile,
                FreqsArray,
                DoRenorm,
                RenormImped,
                DataType,
                Pass,
                ComplexFormat,
                DigitsPrecision,
                False,
                IncludeGammaImpedance,
                NonStandardExtensions,
            )
        self.logger.info("Touchstone correctly exported to %s", filename)
        return OutFile

    @pyaedt_function_handler(unit_system="units_system")
    def value_with_units(
        self,
        value,
        units=None,
        units_system="Length",
    ):
        """Combine a number and a string containing the modeler length unit in a single
        string e.g. "1.2mm".
        If the units are not specified, the model units are used.
        If value is a string (like containing an expression), it is returned as is.

        Parameters
        ----------
        value : float, int, str
            Value of the number or string containing an expression.
        units : str, optional
            Units to combine with value. Valid values are defined in the native API documentation.
            Some common examples are:
            "in": inches
            "cm": centimeter
            "um": micron
            "mm": millimeter
            "meter": meters
            "mil": 0.001 inches (mils)
            "km": kilometer
            "ft": feet
        units_system : str, optional
            Unit system. Default is `"Length"`.

        Returns
        -------
        str
            String that combines the value and the units (e.g. "1.2mm").
        """
        v, u = decompose_variable_value(value)
        if u:
            return value

        if units is None:
            if units_system == "Length":
                if "GetModelUnits" in dir(self.oeditor):
                    units = self.oeditor.GetModelUnits()
                elif "GetActiveUnits" in dir(self.oeditor):
                    units = self.oeditor.GetActiveUnits()
                else:
                    units = self.odesktop.GetDefaultUnit(units_system)
            else:
                try:
                    units = self.odesktop.GetDefaultUnit(units_system)
                except Exception:
                    self.logger.warning("Defined unit system is incorrect.")
                    units = ""

        return _arg_with_dim(value, units)

    @pyaedt_function_handler()
    def change_property(self, aedt_object, tab_name, property_object, property_name, property_value):
        """Change a property.

        Parameters
        ----------
        aedt_object :
            Aedt object. It can be oproject, odesign, oeditor or any of the objects to which the property belongs.
        tab_name : str
            Name of the tab to update. Options are ``BaseElementTab``, ``EM Design``, and
            ``FieldsPostProcessorTab``. The default is ``BaseElementTab``.
        property_object : str
            Name of the property object. It can be the name of an excitation or field reporter.
            For example, ``Excitations:Port1`` or ``FieldsReporter:Mag_H``.
        property_name : str
            Name of the property. For example, ``Rotation Angle``.
        property_value : str, list
            Value of the property. It is a string for a single value and a list of three elements for
            ``[x,y,z]`` coordianates.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.ChangeProperty
        """
        if isinstance(property_value, list) and len(property_value) == 3:
            xpos, ypos, zpos = self.modeler._pos_with_arg(property_value)
            aedt_object.ChangeProperty(
                [
                    "NAME:AllTabs",
                    [
                        "NAME:" + tab_name,
                        ["NAME:PropServers", property_object],
                        ["NAME:ChangedProps", ["NAME:" + property_name, "X:=", xpos, "Y:=", ypos, "Z:=", zpos]],
                    ],
                ]
            )
        elif isinstance(property_value, bool):
            aedt_object.ChangeProperty(
                [
                    "NAME:AllTabs",
                    [
                        "NAME:" + tab_name,
                        ["NAME:PropServers", property_object],
                        ["NAME:ChangedProps", ["NAME:" + property_name, "Value:=", property_value]],
                    ],
                ]
            )
        elif isinstance(property_value, (str, float, int)):
            xpos = self.value_with_units(property_value, self.modeler.model_units)
            aedt_object.ChangeProperty(
                [
                    "NAME:AllTabs",
                    [
                        "NAME:" + tab_name,
                        ["NAME:PropServers", property_object],
                        ["NAME:ChangedProps", ["NAME:" + property_name, "Value:=", xpos]],
                    ],
                ]
            )
        else:
            self.logger.error("Wrong Property Value")
            return False
        self.logger.info(f"Property {property_name} changed correctly.")
        return True

    @pyaedt_function_handler()
    def number_with_units(self, value, units=None):
        """Convert a number to a string with units. If value is a string, it's returned as is.

        .. deprecated:: 0.14.0
            Use :func:`value_with_units` instead.

        Parameters
        ----------
        value : float, int, str
            Input  number or string.
        units : optional
            Units for formatting. The default is ``None`` which uses modeler units.

        Returns
        -------
        str
           String concatenating the value and unit.

        """
        return self.value_with_units(value, units)
