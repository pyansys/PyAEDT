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

"""This module contains these Maxwell classes: ``Maxwell``, ``Maxwell2d``, and ``Maxwell3d``."""

import io
import os
import re
import time

from ansys.aedt.core.application.analysis_3d import FieldAnalysis3D
from ansys.aedt.core.application.variables import decompose_variable_value
from ansys.aedt.core.generic.constants import SOLUTIONS
from ansys.aedt.core.generic.errors import AEDTRuntimeError
from ansys.aedt.core.generic.errors import GrpcApiError
from ansys.aedt.core.generic.general_methods import generate_unique_name
from ansys.aedt.core.generic.general_methods import is_linux
from ansys.aedt.core.generic.general_methods import open_file
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.generic.general_methods import read_configuration_file
from ansys.aedt.core.generic.general_methods import write_configuration_file
from ansys.aedt.core.generic.settings import settings
from ansys.aedt.core.mixins import CreateBoundaryMixin
from ansys.aedt.core.modeler.cad.elements_3d import FacePrimitive
from ansys.aedt.core.modeler.geometry_operators import GeometryOperators
from ansys.aedt.core.modules.boundary.maxwell_boundary import MaxwellParameters
from ansys.aedt.core.modules.setup_templates import SetupKeys


class Maxwell(CreateBoundaryMixin):
    def __init__(self):
        pass

    @property
    def symmetry_multiplier(self):
        """Symmetry multiplier.

        References
        ----------
        >>> oModule.GetSymmetryMultiplier()
        """
        return int(self.omodelsetup.GetSymmetryMultiplier())

    @property
    def windings(self):
        """Windings.

        References
        ----------
        >>> oModule.GetExcitationsOfType("Winding Group")"""
        windings = self.oboundary.GetExcitationsOfType("Winding Group")
        return list(windings)

    @property
    def design_file(self):
        """Design file."""
        design_file = os.path.join(self.working_directory, "design_data.json")
        return design_file

    @pyaedt_function_handler()
    def change_symmetry_multiplier(self, value=1):
        """Set the design symmetry multiplier to a specified value.

        The symmetry multiplier is automatically applied to all input quantities.

        Parameters
        ----------
        value : int, optional
            Value to use as the Design Symmetry Multiplier coefficient. The default value is ``1``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesign.SetDesignSettings
        """
        return self.change_design_settings({"Multiplier": value})

    @pyaedt_function_handler()
    def change_inductance_computation(self, compute_transient_inductance=True, incremental_matrix=False):
        """Enable the inductance computation for the transient analysis and set the incremental matrix.

        Parameters
        ----------
        compute_transient_inductance : bool, optional
            Whether to enable the inductance calculation for the transient analysis.
            The default is ``True``.
        incremental_matrix : bool, optional
            Whether to set the inductance calculation to ``Incremental`` if
            ``compute_transient_inductance=True``. The default is ``False``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesign.SetDesignSettings
        """
        return self.change_design_settings(
            {"ComputeTransientInductance": compute_transient_inductance, "ComputeIncrementalMatrix": incremental_matrix}
        )

    @pyaedt_function_handler
    def apply_skew(
        self,
        skew_type="Continuous",
        skew_part="Rotor",
        skew_angle="1",
        skew_angle_unit="deg",
        number_of_slices=2,
        custom_slices_skew_angles=None,
    ):
        """Apply skew to 2D model.

        Parameters
        ----------
        skew_type : str, optional
            Skew type.
            Possible choices are ``Continuous``, ``Step``, ``V-Shape``, ``User Defined``.
            The default value is ``Continuous``.
        skew_part : str, optional
            Part to skew.
            Possible choices are ``Rotor`` or ``Stator``.
            The default value is ``Rotor``.
        skew_angle : str, optional
            Skew angle.
            The default value is ``1``.
        skew_angle_unit : str, optional
            Skew angle unit.
            Possible choices are ``deg``, ``rad``, ``degsec``, ``degmin``.
            The default value is ``deg``.
        number_of_slices : str, optional
            Number of slices to split the selected part into.
            The default value is ``2``.
        custom_slices_skew_angles : list, optional
            List of custom angles to apply to slices.
            Only available if skew_type is ``User Defined``.
            The length of this list must be equal to number_of_slices.
            The default value is ``None``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if skew_type not in ("Continuous", "Step", "V-Shape", "User Defined"):
            raise ValueError("Invalid skew type.")
        if skew_part not in ("Rotor", "Stator"):
            raise ValueError("Invalid skew part.")
        if skew_angle_unit not in ("deg", "rad", "degsec", "degmin"):
            raise ValueError("Invalid skew angle unit.")
        if skew_type != "User Defined":
            arg = {
                "UseSkewModel": True,
                "SkewType": skew_type,
                "SkewPart": skew_part,
                "SkewAngle": f"{skew_angle}{skew_angle_unit}",
                "NumberOfSlices": number_of_slices,
            }
            return self.change_design_settings(arg)
        else:
            if not custom_slices_skew_angles or len(custom_slices_skew_angles) != int(number_of_slices):
                raise ValueError("Please provide skew angles for each slice.")
            arg_slice_table = {"NAME:SkewSliceTable": []}
            slice_length = decompose_variable_value(self.design_properties["ModelDepth"])[0] / int(number_of_slices)
            for i in range(int(number_of_slices)):
                arg_slice_info = []
                arg_slice_info.append("NAME:OneSliceInfo")
                arg_slice_info.append("SkewAngle:=")
                arg_slice_info.append(str(custom_slices_skew_angles[i]))
                arg_slice_info.append("SliceLength:=")
                arg_slice_info.append(str(slice_length))
                arg_slice_table["NAME:SkewSliceTable"].append(arg_slice_info)
            props = {
                "UseSkewModel": True,
                "SkewType": skew_type,
                "SkewPart": skew_part,
                "SkewAngleUnit": skew_angle_unit,
                "NumberOfSlices": number_of_slices,
            }
            props.update(arg_slice_table)
            return self.change_design_settings(props)

    @pyaedt_function_handler(objects="assignment", value="core_loss_on_field")
    def set_core_losses(self, assignment, core_loss_on_field=False):
        """Whether to enable core losses for a set of objects.

        For ``EddyCurrent`` and ``Transient`` solver designs, core losses calculations
        may be included in the simulation on any object that has a corresponding
        core loss definition (with core loss coefficient settings) in the material library.

        Parameters
        ----------
        assignment : list, str
            List of object to apply core losses to.
        core_loss_on_field : bool, optional
            Whether to enable ``Consider core loss effect on field`` for the given list. The default is
            ``False``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.SetCoreLoss

        Examples
        --------
        Set core losses in Maxwell 3D.

        >>> from ansys.aedt.core import Maxwell3d
        >>> m3d = Maxwell3d()
        >>> m3d.set_core_losses(assignment=["PQ_Core_Bottom", "PQ_Core_Top"],core_loss_on_field=True)
        >>> m3d.release_desktop(True, True)
        """
        if self.solution_type not in (SOLUTIONS.Maxwell3d.EddyCurrent, SOLUTIONS.Maxwell3d.Transient):
            raise AEDTRuntimeError("Core losses is only available with `EddyCurrent` and `Transient` solutions.")

        assignment = self.modeler.convert_to_selections(assignment, True)
        self.oboundary.SetCoreLoss(assignment, core_loss_on_field)
        return True

    # TODO: Check this method
    @pyaedt_function_handler(sources="assignment")
    def assign_matrix(
        self,
        assignment,
        matrix_name=None,
        turns=None,
        return_path=None,
        group_sources=None,
        branches=None,
    ):
        """Assign a matrix to the selection.

        Matrix assignment can be calculated based upon the solver type.
        For 2D/3D solvers the available solution types are: ``Magnetostatic``,
        ``Electrostatic``, ``Eddy Current``, ``DC Conduction`` and ``AC Conduction``.


        Parameters
        ----------
        assignment : list, str
            List of sources to assign a matrix to.
        matrix_name : str, optional
            Name of the matrix. The default is ``None``.
        turns : list, int, optional
            Number of turns. The default is 1.
        return_path : list, str, optional
            Return path. The default is ``infinite``
        group_sources : dict, list optional
            Dictionary consisting of ``{Group Name: list of source names}`` to add
            multiple groups. You can also define a list of strings. The default is ``None``.
        branches : : list, int, optional
            Number of branches. The default is ``None``, which indicates that only one
            branch exists.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Boundary object.

        References
        ----------
        >>> oModule.AssignMatrix

        Examples
        --------
        Set matrix in a Maxwell magnetostatic analysis.

        >>> from ansys.aedt.core import Maxwell2d
        >>> m2d = Maxwell2d(solution_type="MagnetostaticXY",version="2025.1",close_on_exit=True)
        >>> coil1 = m2d.modeler.create_rectangle([0, 1.5, 0], [8, 3], is_covered=True, name="Coil_1")
        >>> coil2 = m2d.modeler.create_rectangle([8.5, 1.5, 0], [8, 3], is_covered=True, name="Coil_2")
        >>> coil3 = m2d.modeler.create_rectangle([16, 1.5, 0], [8, 3], is_covered=True, name="Coil_3")
        >>> coil4 = m2d.modeler.create_rectangle([32, 1.5, 0], [8, 3], is_covered=True, name="Coil_4")
        >>> current1 = m2d.assign_current(assignment="Coil_1",amplitude=1,swap_direction=False,name="Current1")
        >>> current2 = m2d.assign_current(assignment="Coil_2",amplitude=1,swap_direction=True,name="Current2")
        >>> current3 = m2d.assign_current(assignment="Coil_3",amplitude=1,swap_direction=True,name="Current3")
        >>> current4 = m2d.assign_current(assignment="Coil_4",amplitude=1,swap_direction=True,name="Current4")
        >>> group_sources = {"Group1_Test": ["Current1", "Current3"], "Group2_Test": ["Current2", "Current4"]}
        >>> selection = ['Current1', 'Current2', 'Current3', 'Current4']
        >>> turns = [5, 1, 2, 3]
        >>> L = m2d.assign_matrix(assignment=selection,matrix_name="Test2",turns=turns,group_sources=group_sources)

        Set matrix in a Maxwell DC Conduction analysis.
        >>> m2d.assign_voltage(["Port1"],amplitude=1,name="1V")
        >>> m2d.assign_voltage(["Port2"],amplitude=0,name="0V")
        >>> m2d.assign_matrix(assignment=['1V'],matrix_name="Matrix1",group_sources=['0V'])
        >>> m2d.release_desktop(True, True)
        """

        assignment = self.modeler.convert_to_selections(assignment, True)
        if self.solution_type in (
            SOLUTIONS.Maxwell3d.ElectroStatic,
            SOLUTIONS.Maxwell3d.ACConduction,
            SOLUTIONS.Maxwell3d.DCConduction,
        ):
            turns = ["1"] * len(assignment)
            branches = None
            if self.design_type == "Maxwell 2D":
                if group_sources:
                    if isinstance(group_sources, dict):
                        first_key = next(iter(group_sources))
                        group_sources = group_sources[first_key]
                        self.logger.warning("First Ground is selected")
                    group_sources = self.modeler.convert_to_selections(group_sources, True)
                    if any(item in group_sources for item in assignment):
                        raise AEDTRuntimeError("Ground must be different than selected sources")
            else:
                group_sources = None

        elif self.solution_type == SOLUTIONS.Maxwell3d.Magnetostatic:
            if group_sources:
                if isinstance(group_sources, dict):
                    new_group = group_sources.copy()
                    for element in new_group:
                        if not all(item in assignment for item in group_sources[element]):
                            self.logger.warning("Sources in group " + element + " are not selected")
                            group_sources.pop(element)
                    if not branches or len(group_sources) != len(self.modeler.convert_to_selections(branches, True)):
                        if branches:
                            branches = self.modeler.convert_to_selections(branches, True)
                            num = abs(len(group_sources) - len(self.modeler.convert_to_selections(branches, True)))
                            if len(group_sources) < len(self.modeler.convert_to_selections(branches, True)):
                                branches = branches[:-num]
                            else:
                                new_element = [branches[0]] * num
                                branches.extend(new_element)
                        else:
                            branches = [1] * len(group_sources)
                elif isinstance(group_sources, list):
                    group_name = generate_unique_name("Group")
                    group_sources = {group_name: group_sources}
                else:
                    self.logger.warning("Group of sources is not a dictionary")
                    group_sources = None
        elif self.solution_type == SOLUTIONS.Maxwell3d.EddyCurrent:
            group_sources = None
            branches = None
            turns = ["1"] * len(assignment)
            self.logger.info("Infinite is the only return path option in EddyCurrent.")
            return_path = ["infinite"] * len(assignment)

        if self.solution_type not in (SOLUTIONS.Maxwell3d.Transient, SOLUTIONS.Maxwell3d.ElectricTransient):
            if not matrix_name:
                matrix_name = generate_unique_name("Matrix")
            if not turns or len(assignment) != len(self.modeler.convert_to_selections(turns, True)):
                if turns:
                    turns = self.modeler.convert_to_selections(turns, True)
                    num = abs(len(assignment) - len(self.modeler.convert_to_selections(turns, True)))
                    if len(assignment) < len(self.modeler.convert_to_selections(turns, True)):
                        turns = turns[:-num]
                    else:
                        new_element = [turns[0]] * num
                        turns.extend(new_element)
                else:
                    turns = ["1"] * len(assignment)
            else:
                turns = self.modeler.convert_to_selections(turns, True)
            if not return_path or len(assignment) != len(self.modeler.convert_to_selections(return_path, True)):
                return_path = ["infinite"] * len(assignment)
            else:
                return_path = self.modeler.convert_to_selections(return_path, True)
            if any(item in return_path for item in assignment):
                raise AEDTRuntimeError("Return path specified must not be included in sources")

            if group_sources and self.solution_type in ["EddyCurrent", "Magnetostatic"]:
                props = dict({"MatrixEntry": dict({"MatrixEntry": []}), "MatrixGroup": dict({"MatrixGroup": []})})
            else:
                props = dict({"MatrixEntry": dict({"MatrixEntry": []}), "MatrixGroup": []})

            for element in range(len(assignment)):
                if self.solution_type == SOLUTIONS.Maxwell3d.Magnetostatic and self.design_type == "Maxwell 2D":
                    prop = dict(
                        {
                            "Source": assignment[element],
                            "NumberOfTurns": turns[element],
                            "ReturnPath": return_path[element],
                        }
                    )
                elif self.solution_type == SOLUTIONS.Maxwell3d.EddyCurrent:
                    prop = dict({"Source": assignment[element], "ReturnPath": return_path[element]})
                else:
                    prop = dict({"Source": assignment[element], "NumberOfTurns": turns[element]})
                props["MatrixEntry"]["MatrixEntry"].append(prop)

            if group_sources:
                if self.solution_type in (
                    SOLUTIONS.Maxwell3d.ElectroStatic,
                    SOLUTIONS.Maxwell3d.ACConduction,
                    SOLUTIONS.Maxwell3d.DCConduction,
                ):
                    source_list = ",".join(group_sources)
                    props["GroundSources"] = source_list
                else:
                    cont = 0
                    for element in group_sources:
                        source_list = ",".join(group_sources[element])
                        # GroundSources
                        prop = dict({"GroupName": element, "NumberOfBranches": branches[cont], "Sources": source_list})
                        props["MatrixGroup"]["MatrixGroup"].append(prop)
                        cont += 1
            return self._create_boundary(matrix_name, props, "Matrix")
        else:
            raise AEDTRuntimeError("Solution type does not have matrix parameters")

    @pyaedt_function_handler()
    def setup_ctrlprog(
        self, setupname, file_str=None, keep_modifications=False, python_interpreter=None, aedt_lib_dir=None
    ):
        """Configure the transient design setup to run a specific control program.

        The control program is executed from a temporary directory that Maxwell creates for every setup run.

        .. deprecated:: 0.6.71
        Use :func:`enable_control_program` method instead.

        Parameters
        ----------
        setupname : str
            Name of the setup.
            It will become the name of the Python file.
        file_str : str, optional
            Name of the file. The default value is ``None``.
        keep_modifications : bool, optional
            Whether to save the changes. The default value is ``False``.
        python_interpreter : str, optional
             Python interpreter to use. The default value is ``None``.
        aedt_lib_dir : str, optional
             Full path to the ``pyaedt`` directory. The default value is ``None``.

        Returns
        -------
        bool
            ``True`` when successful and ``False`` when failed.
        """
        if self.solution_type != SOLUTIONS.Maxwell3d.Transient:
            raise AEDTRuntimeError("Control Program is only available in Maxwell 2D and 3D Transient solutions.")

        self._py_file = setupname + ".py"
        ctl_file_path = os.path.join(self.working_directory, self._py_file)

        if aedt_lib_dir:
            source_dir = aedt_lib_dir
        else:
            source_dir = self.pyaedt_dir

        if os.path.exists(ctl_file_path) and keep_modifications:
            with open_file(ctl_file_path, "r") as fi:
                existing_data = fi.readlines()
            with open_file(ctl_file_path, "w") as fo:
                first_line = True
                for line in existing_data:
                    if first_line:
                        first_line = False
                        if python_interpreter:
                            fo.write(f"#!{python_interpreter}\n")
                    if line.startswith("work_dir"):
                        fo.write(f"work_dir = r'{self.working_directory}'\n")
                    elif line.startswith("lib_dir"):
                        fo.write(f"lib_dir = r'{source_dir}'\n")
                    else:
                        fo.write(line)
        else:
            if file_str is not None:
                with io.open(ctl_file_path, "w", newline="\n") as fo:
                    fo.write(file_str)
                if not os.path.exists(ctl_file_path):
                    raise FileNotFoundError("Control program file could not be created.")

        self.oanalysis.EditSetup(
            setupname,
            [
                "NAME:" + setupname,
                "Enabled:=",
                True,
                "UseControlProgram:=",
                True,
                "ControlProgramName:=",
                ctl_file_path,
                "ControlProgramArg:=",
                "",
                "CallCtrlProgAfterLastStep:=",
                True,
            ],
        )
        return True

    @pyaedt_function_handler(
        object_list="assignment",
        activate_eddy_effects="enable_eddy_effects",
        activate_displacement_current="enable_displacement_current",
    )
    def eddy_effects_on(self, assignment, enable_eddy_effects=True, enable_displacement_current=True):
        """Assign eddy effects on a list of objects.

        For Eddy Current solvers only, you must specify the displacement current on the model objects.

        Parameters
        ----------
        assignment : list, str
            List of objects to assign eddy effects to.
        enable_eddy_effects : bool, optional
            Whether to activate eddy effects. The default is ``True``.
        enable_displacement_current : bool, optional
            Whether to activate the displacement current. The default is ``True``.
            Valid only for Eddy Current solvers.

        Returns
        -------
        bool
            ``True`` when successful and ``False`` when failed.

        References
        ----------
        >>> oModule.SetEddyEffect
        """
        solid_objects_names = self.get_all_conductors_names()
        if not solid_objects_names:
            raise AEDTRuntimeError("No conductors defined in active design.")
        assignment = self.modeler.convert_to_selections(assignment, True)

        EddyVector = ["NAME:EddyEffectVector"]
        if self.modeler._is3d:
            if not enable_eddy_effects:
                enable_displacement_current = False
            for obj in solid_objects_names:
                if self.solution_type == SOLUTIONS.Maxwell3d.EddyCurrent:
                    if obj in assignment:
                        EddyVector.append(
                            [
                                "NAME:Data",
                                "Object Name:=",
                                obj,
                                "Eddy Effect:=",
                                enable_eddy_effects,
                                "Displacement Current:=",
                                enable_displacement_current,
                            ]
                        )
                    else:
                        EddyVector.append(
                            [
                                "NAME:Data",
                                "Object Name:=",
                                obj,
                                "Eddy Effect:=",
                                bool(self.oboundary.GetEddyEffect(obj)),
                                "Displacement Current:=",
                                bool(self.oboundary.GetDisplacementCurrent(obj)),
                            ]
                        )
                if self.solution_type == SOLUTIONS.Maxwell3d.Transient:
                    if obj in assignment:
                        EddyVector.append(
                            [
                                "NAME:Data",
                                "Object Name:=",
                                obj,
                                "Eddy Effect:=",
                                enable_eddy_effects,
                            ]
                        )
                    else:
                        EddyVector.append(
                            [
                                "NAME:Data",
                                "Object Name:=",
                                obj,
                                "Eddy Effect:=",
                                bool(self.oboundary.GetEddyEffect(obj)),
                            ]
                        )
        else:
            for obj in solid_objects_names:
                if obj in assignment:
                    EddyVector.append(
                        [
                            "NAME:Data",
                            "Object Name:=",
                            obj,
                            "Eddy Effect:=",
                            enable_eddy_effects,
                        ]
                    )
                else:
                    EddyVector.append(
                        [
                            "NAME:Data",
                            "Object Name:=",
                            obj,
                            "Eddy Effect:=",
                            bool(self.oboundary.GetEddyEffect(obj)),
                        ]
                    )
        self.oboundary.SetEddyEffect(["NAME:Eddy Effect Setting", EddyVector])
        return True

    @pyaedt_function_handler(windings_name="assignment")
    def setup_y_connection(self, assignment=None):
        """Set up the Y connection.

        Parameters
        ----------
        assignment : list, optional
            List of windings. For example, ``["PhaseA", "PhaseB", "PhaseC"]``.
            The default is ``None``, in which case the design has no Y connection.

        Returns
        -------
        bool
            ``True`` when successful and ``False`` when failed.

        References
        ----------
        >>> oModule.SetupYConnection

        Examples
        --------
        Set up the Y connection for three existing windings named ``PhaseA``, ``PhaseB``, and ``PhaseC``.
        This creates one ``YConnection`` group containing these three phases.

        >>> from ansys.aedt.core import Maxwell2d
        >>> m2d = Maxwell2d("Motor_EM_R2019R3.aedt")
        >>> m2d.set_active_design("Basis_Model_For_Test")
        >>> m2d.setup_y_connection(["PhaseA", "PhaseB", "PhaseC"])
        >>> m2d.release_desktop(True, True)
        """

        if self.solution_type != SOLUTIONS.Maxwell3d.Transient:
            raise AEDTRuntimeError("Y connections only available for Transient solutions.")

        if assignment:
            connection = ["NAME:YConnection", "Windings:=", ",".join(assignment)]
            assignment = ["NAME:YConnection", connection]
            self.oboundary.SetupYConnection(assignment)
        else:
            self.oboundary.SetupYConnection()
        return True

    @pyaedt_function_handler(object_list="assignment")
    def assign_current(self, assignment, amplitude=1, phase="0deg", solid=True, swap_direction=False, name=None):
        """Assign the source of the current.

        Parameters
        ----------
        assignment : list, str
            List of objects to assign the current source to.
        amplitude : float or str, optional
            Current amplitude. The default is ``1A``.
        phase : str, optional
            Current phase.
            The default is ``"0deg"``.
        solid : bool, optional
            Specifies the type of conductor, which can be solid or stranded.
            The default is ``True``, which means the conductor is solid``.
            When ``False``, it means the conductor is stranded.
        swap_direction : bool, optional
            Reference direction.
            The default is ``False`` which means that current is flowing inside the object.
        name : str, optional
            Name of the current excitation.
            The default is ``None`` in which case a generic name will be given.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Boundary object.

        References
        ----------
        >>> oModule.AssignCurrent

        Examples
        --------

        >>> from ansys.aedt.core import Maxwell3d
        >>> m3d = Maxwell3d(solution_type="ElectroDCConduction")
        >>> cylinder= m3d.modeler.create_cylinder("X",[0,0,0],10,100,250)
        >>> current = m3d.assign_current(cylinder.top_face_x.id,amplitude="2mA")
        >>> m3d.release_desktop(True, True)
        """
        if isinstance(amplitude, (int, float)):
            amplitude = str(amplitude) + "A"

        if not name:
            name = generate_unique_name("Current")

        assignment = self.modeler.convert_to_selections(assignment, True)
        if self.is3d:
            if type(assignment[0]) is int:
                props = dict(
                    {
                        "Faces": assignment,
                        "Current": amplitude,
                    }
                )
            else:
                props = dict(
                    {
                        "Objects": assignment,
                        "Current": amplitude,
                    }
                )
            if self.solution_type not in (
                SOLUTIONS.Maxwell3d.Magnetostatic,
                SOLUTIONS.Maxwell3d.DCConduction,
                SOLUTIONS.Maxwell3d.ElectricTransient,
                SOLUTIONS.Maxwell3d.TransientAPhiFormulation,
                SOLUTIONS.Maxwell3d.ElectroDCConduction,
            ):
                props["Phase"] = phase
            if self.solution_type not in (
                SOLUTIONS.Maxwell3d.DCConduction,
                SOLUTIONS.Maxwell3d.ElectricTransient,
                SOLUTIONS.Maxwell3d.ElectroDCConduction,
            ):
                props["IsSolid"] = solid
            props["Point out of terminal"] = swap_direction
        else:
            if type(assignment[0]) is str:
                props = dict({"Objects": assignment, "Current": amplitude, "IsPositive": swap_direction})
            else:
                raise ValueError("Input must be a 2D object.")
        return self._create_boundary(name, props, "Current")

    @pyaedt_function_handler(band_object="assignment")
    def assign_translate_motion(
        self,
        assignment,
        coordinate_system="Global",
        axis="Z",
        positive_movement=True,
        start_position=0,
        periodic_translate=True,
        negative_limit=0,
        positive_limit=0,
        velocity=0,
        mechanical_transient=False,
        mass=1,
        damping=0,
        load_force=0,
        motion_name=None,
    ):
        """Assign a translation motion to an object container.

        For both rotational and translational problems, the band objects must always enclose all the moving objects.

        Parameters
        ----------
        assignment : str
            Object container.
        coordinate_system : str, optional
            Coordinate system name. The default is ``"Global"``.
        axis : str or int, optional
            Coordinate system axis. The default is ``"Z"``.
            It can be a ``ansys.aedt.core.generic.constants.AXIS`` enumerator value.
        positive_movement : bool, optional
            Whether movement is positive. The default is ``True``.
        start_position : float or str, optional
            Starting position of the movement. The default is ``0``. If a float
            value is used, default modeler units are applied.
        periodic_translate : bool, optional
            Whether movement is periodic. The default is ``False``.
        negative_limit : float or str, optional
            Negative limit of the movement. The default is ``0``. If a float
            value is used, the default modeler units are applied.
        positive_limit : float or str, optional
            Positive limit of the movement. The default is ``0``. If a float
            value is used, the default modeler units are applied.
        velocity : float or str, optional
            Initial velocity.
            The default is ``0``. If a float value is used, "m_per_sec" units are applied.
        mechanical_transient : bool, optional
            Whether to consider the mechanical movement. The default is ``False``.
        mass : float or str, optional
            Mechanical mass. The default is ``1``. If a float value is used, "Kg" units
            are applied.
        damping : float, optional
            Damping factor. The default is ``0``.
        load_force : float or str, optional
            Load force is positive if it's applied in the same direction as the moving vector and negative
            in the opposite direction.
            The default is ``0``. If a float value is used, "newton" units are applied.
        motion_name : str, optional
            Motion name. The default is ``None``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject` or ``False``
            Boundary object or bool if not successful.

        References
        ----------
        >>> oModule.AssignBand
        """
        if self.solution_type != SOLUTIONS.Maxwell3d.Transient:
            raise AEDTRuntimeError("Motion applies only to the Transient setup.")

        if not motion_name:
            motion_name = generate_unique_name("Motion")
        object_list = self.modeler.convert_to_selections(assignment, True)
        props = dict(
            {
                "Move Type": "Translate",
                "Coordinate System": coordinate_system,
                "PostProcessing Coordinate System": coordinate_system,
                "Axis": GeometryOperators.cs_axis_str(axis),
                "Is Positive": positive_movement,
                "InitPos": self._arg_with_units(start_position),
                "TranslatePeriodic": periodic_translate,
                "NegativePos": self._arg_with_units(negative_limit),
                "PositivePos": self._arg_with_units(positive_limit),
                "Consider Mechanical Transient": mechanical_transient,
                "Velocity": self._arg_with_units(velocity, "m_per_sec"),
                "Mass": self._arg_with_units(mass, "Kg"),
                "Damping": str(damping),
                "Load Force": self._arg_with_units(load_force, "newton"),
                "Objects": object_list,
            }
        )
        return self._create_boundary(motion_name, props, "Band")

    @pyaedt_function_handler(band_object="assignment")
    def assign_rotate_motion(
        self,
        assignment,
        coordinate_system="Global",
        axis="Z",
        positive_movement=True,
        start_position=0,
        has_rotation_limits=True,
        negative_limit=0,
        positive_limit=360,
        non_cylindrical=False,
        mechanical_transient=False,
        angular_velocity="0rpm",
        inertia="1",
        damping=0,
        load_torque="0newton",
    ):
        """Assign a rotation motion to an object container.

        For both rotational and translational problems, the band objects must always enclose all the moving objects.

        Parameters
        ----------
        assignment : str,
            Object container.
        coordinate_system : str, optional
            Coordinate system name. The default is ``"Global"``.
        axis : str or int, optional
            Coordinate system axis. The default is ``"Z"``.
            It can be a ``ansys.aedt.core.generic.constants.AXIS`` enumerator value.
        positive_movement : bool, optional
            Whether the movement is positive. The default is ``True``.
        start_position : float or str, optional
            Starting position of the movement. The default is ``0``. If a float value
            is used, "deg" units are applied.
        has_rotation_limits : bool, optional
            Whether there is a limit in rotation. The default is ``False``.
        negative_limit : float or str, optional
            Negative limit of the movement. The default is ``0``. If a float value is
            used, "deg" units are applied.
        positive_limit : float or str, optional
            Positive limit of the movement. The default is ``360``. If a float value is used,
            "deg" units are applied.
        non_cylindrical : bool, optional
            Whether to consider non-cylindrical rotation. The default is ``False``.
        angular_velocity : float or str, optional
            Movement velocity. The default is ``"0rpm"``. If a float value is used,
            "rpm" units are applied.
        mechanical_transient : bool, optional
            Whether to consider mechanical movement. The default is ``False``.
        inertia : float, optional
            Mechanical inertia. The default is ``1``.
        damping : float, optional
            Damping factor. The default is ``0``.
        load_torque : float or str, optional
            Load torque sign is determined based on the moving vector, using the right-hand rule.
            The default is ``"0NewtonMeter"``. If a float value is used "NewtonMeter" units are applied.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Boundary object.

        References
        ----------
        >>> oModule.AssignBand
        """
        if self.solution_type != SOLUTIONS.Maxwell3d.Transient:
            raise AEDTRuntimeError("Motion applies only to the Transient setup.")

        names = list(self.omodelsetup.GetMotionSetupNames())
        motion_name = "MotionSetup" + str(len(names) + 1)
        object_list = self.modeler.convert_to_selections(assignment, True)
        props = dict(
            {
                "Move Type": "Rotate",
                "Coordinate System": coordinate_system,
                "Axis": GeometryOperators.cs_axis_str(axis),
                "Is Positive": positive_movement,
                "InitPos": self._arg_with_units(start_position, "deg"),
                "HasRotateLimit": has_rotation_limits,
                "NegativePos": self._arg_with_units(negative_limit, "deg"),
                "PositivePos": self._arg_with_units(positive_limit, "deg"),
                "NonCylindrical": non_cylindrical,
                "Consider Mechanical Transient": mechanical_transient,
                "Angular Velocity": self._arg_with_units(angular_velocity, "rpm"),
                "Moment of Inertia": str(inertia),
                "Damping": str(damping),
                "Load Torque": self._arg_with_units(load_torque, "NewtonMeter"),
                "Objects": object_list,
            }
        )
        return self._create_boundary(motion_name, props, "Band")

    @pyaedt_function_handler(face_list="assignment")
    def assign_voltage(self, assignment, amplitude=1, name=None):
        """Assign a voltage source to a list of faces in Maxwell 3D or a list of objects or edges in Maxwell 2D.

        Parameters
        ----------
        assignment : list
            List of faces, objects or edges to assign a voltage source to.
        amplitude : float, optional
            Voltage amplitude in mV. The default is ``1``.
        name : str, optional
            Name of the boundary. The default is ``None``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Boundary object.
            ``False`` when failed.

        References
        ----------
        >>> oModule.AssignVoltage

        Examples
        --------

        Create a region in Maxwell 2D and assign voltage to its edges.
        >>> from ansys.aedt.core import Maxwell2d
        >>> m2d = Maxwell2d(version="2025.1", solution_type="ElectrostaticZ")
        >>> region_id = m2d.modeler.create_region(pad_value=[500,50,50])
        >>> voltage = m2d.assign_voltage(assignment=region_id.edges, amplitude=0, name = "GRD")
        >>> m2d.release_desktop()

        Create a region in Maxwell 3D and assign voltage to its edges.
        >>> from ansys.aedt.core import Maxwell3d
        >>> m3d = Maxwell3d(version="2025.1", solution_type="Electrostatic")
        >>> region_id = m3d.modeler.create_box([0, 0, 0], [10, 10, 10])
        >>> voltage = m3d.assign_voltage(assignment=region_id.faces, amplitude=0, name = "GRD")
        >>> m3d.release_desktop()

        """
        if isinstance(amplitude, (int, float)):
            amplitude = f"{amplitude}mV"

        name = name or generate_unique_name("Voltage")
        assignment = self.modeler.convert_to_selections(assignment, True)
        is_maxwell_2d = self.design_type == "Maxwell 2D"
        object_names_set = set(self.modeler.object_names)

        props = {
            "Voltage" if not is_maxwell_2d else "Value": amplitude,
            "Objects": [],
            "Faces": [] if not is_maxwell_2d else None,
            "Edges": [] if is_maxwell_2d else None,
        }

        for element in assignment:
            if isinstance(element, str) and element in object_names_set:
                props["Objects"].append(element)
            else:
                key = "Edges" if is_maxwell_2d else "Faces"
                props[key].append(element)

        return self._create_boundary(name, props, "Voltage")

    @pyaedt_function_handler(face_list="assignment")
    def assign_voltage_drop(self, assignment, amplitude=1, swap_direction=False, name=None):
        """Assign a voltage drop across a list of faces to a specific value.

        The voltage drop applies only to sheet objects.

        Parameters
        ----------
        assignment : list
            List of faces to assign a voltage drop to.
        amplitude : float, optional
            Voltage amplitude in mV. The default is ``1``.
        swap_direction : bool, optional
            Whether to swap the direction. The default value is ``False``.
        name : str, optional
            Name of the boundary. The default is ``None``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Boundary object.
            ``False`` when failed.

        References
        ----------
        >>> oModule.AssignVoltageDrop
        """
        if isinstance(amplitude, (int, float)):
            amplitude = str(amplitude) + "mV"

        if not name:
            name = generate_unique_name("VoltageDrop")
        assignment = self.modeler.convert_to_selections(assignment, True)

        props = dict({"Faces": assignment, "Voltage Drop": amplitude, "Point out of terminal": swap_direction})
        return self._create_boundary(name, props, "VoltageDrop")

    @pyaedt_function_handler()
    def assign_floating(self, assignment, charge_value=0, name=None):
        """Assign floating excitation to model conductors at unknown potentials
        and specify the total charge on the conductor.

        Parameters
        ----------
        assignment : list of int, :class:`ansys.aedt.core.modeler.cad.object3d.Object3d`,
                    :class:`ansys.aedt.core.modeler.elements_3d.FacePrimitive` or str
            List of objects or faces to assign the excitation to.
        charge_value : int, float, optional
            Charge value.
            If not provided, The default is ``0``.
        name : str, optional
            Name of the excitation.
            If not provided, a random name with prefix "Floating" will be generated.

        Returns
        -------
        :class:`ansys.aedt.core.modules.Boundary.BoundaryObject`
            Boundary object.
            ``False`` when failed.

        References
        ----------
        >>> oModule.AssignFloating

        Examples
        --------
        Assign a floating excitation for a Maxwell 2d Electrostatic design

        >>> from ansys.aedt.core import Maxwell2d
        >>> m2d = Maxwell2d(version="2025.1")
        >>> m2d.solution_type = SOLUTIONS.Maxwell2d.ElectroStaticXY
        >>> rect = m2d.modeler.create_rectangle([0, 0, 0], [3, 1], name="Rectangle1")
        >>> floating = m2d.assign_floating(assignment=rect, charge_value=3, name="floating_test")
        >>> m2d.release_desktop(True, True)

        Assign a floating excitation for a Maxwell 3d Electrostatic design providing an object
        >>> from ansys.aedt.core import Maxwell3d
        >>> m3d = Maxwell3d(version="2025.1")
        >>> m3d.solution_type = SOLUTIONS.Maxwell3d.ElectroStatic
        >>> box = m3d.modeler.create_box([0, 0, 0], [10, 10, 10], name="Box1")
        >>> floating = m3d.assign_floating(assignment=box, charge_value=3)
        Assign a floating excitation providing a list of faces
        >>> floating1 = m3d.assign_floating(assignment=[box.faces[0], box.faces[1]], charge_value=3)
        >>> m3d.release_desktop(True, True)
        """
        if self.solution_type not in (SOLUTIONS.Maxwell3d.ElectroStatic, SOLUTIONS.Maxwell3d.ElectricTransient):
            raise AEDTRuntimeError(
                "Assign floating excitation is only valid for electrostatic or electric transient solvers."
            )

        if not isinstance(assignment, list):
            assignment = [assignment]

        if isinstance(charge_value, (int, float)):
            charge_value = str(charge_value)

        if self.dim == "3D" and all([isinstance(a, FacePrimitive) for a in assignment]):
            assignment_type = "Faces"
        else:
            assignment_type = "Objects"

        assignment = self.modeler.convert_to_selections(assignment, True)

        props = dict({assignment_type: assignment, "Value": charge_value})

        if not name:
            name = generate_unique_name("Floating")

        return self._create_boundary(name, props, "Floating")

    @pyaedt_function_handler(coil_terminals="assignment", current_value="current", res="resistance", ind="inductance")
    def assign_winding(
        self,
        assignment=None,
        winding_type="Current",
        is_solid=True,
        current=1,
        resistance=0,
        inductance=0,
        voltage=0,
        parallel_branches=1,
        phase=0,
        name=None,
    ):
        """Assign a winding to a Maxwell design.

        Parameters
        ----------
        assignment : list, optional
            List of faces to create the coil terminal on.
            The default is ``None``.
        winding_type : str, optional
            Type of the winding. Options are ``"Current"``, ``"Voltage"``,
            and ``"External"``. The default is ``"Current"``.
        is_solid : bool, optional
            Whether the winding is the solid type. The default is ``True``. If ``False``,
            the winding is the stranded type.
        current : float, optional
            Value of the current in amperes. The default is ``1``.
        resistance : float, optional
            Resistance in ohms. The default is ``0``.
        inductance : float, optional
            Inductance in Henry (H). The default is ``0``.
        voltage : float, optional
            Voltage value. The default is ``0``.
        parallel_branches : int, optional
            Number of parallel branches. The default is ``1``.
        phase : float, optional
            Value of the phase delay in degrees. The default is ``0``.
        name : str, optional
            Name of the boundary. The default is ``None``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Bounding object for the winding, otherwise only the bounding object.
            ``False`` when failed.

        References
        ----------
        >>> oModule.AssignWindingGroup
        """

        if not name:
            name = generate_unique_name("Winding")

        props = dict(
            {
                "Type": winding_type,
                "IsSolid": is_solid,
                "Current": self.value_with_units(current, "A"),
                "Resistance": self.value_with_units(resistance, "ohm"),
                "Inductance": self.value_with_units(inductance, "H"),
                "Voltage": self.value_with_units(voltage, "V"),
                "ParallelBranchesNum": str(parallel_branches),
                "Phase": self.value_with_units(phase, "deg"),
            }
        )
        bound = self._create_boundary(name, props, "Winding")
        if bound:
            if assignment is None:
                assignment = []
            if type(assignment) is not list:
                assignment = [assignment]
            coil_names = []
            for coil in assignment:
                c = self.assign_coil(coil)
                if c:
                    coil_names.append(c.name)

            if coil_names:
                self.add_winding_coils(bound.name, coil_names)
            return bound
        return False

    @pyaedt_function_handler(windingname="assignment", coil_names="coils")
    def add_winding_coils(self, assignment, coils):
        """Add coils to the winding.

        Parameters
        ----------
        assignment : str
            Name of the winding.
        coils : list
            List of the coil names.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.AddWindingTerminals
        >>> oModule.AddWindingCoils
        """
        if self.modeler._is3d:
            self.oboundary.AddWindingTerminals(assignment, coils)
        else:
            self.oboundary.AddWindingCoils(assignment, coils)
        return True

    @pyaedt_function_handler(input_object="assignment", conductor_number="conductors_number")
    def assign_coil(self, assignment, conductors_number=1, polarity="Positive", name=None):
        """Assign coils to a list of objects or face IDs.

        Parameters
        ----------
        assignment : list
            List of objects or face IDs.
        conductors_number : int, optional
            Number of conductors. The default is ``1``.
        polarity : str, optional
            Type of the polarity. The default is ``"Positive"``.
        name : str, optional
            The default is ``None``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Bounding object for the winding, otherwise only the bounding object.
            ``False`` when failed.

        References
        ----------
        >>> oModule.AssignCoil
        """
        if polarity.lower() == "positive":
            point = False
        else:
            point = True

        assignment = self.modeler.convert_to_selections(assignment, True)

        if not name:
            name = generate_unique_name("Coil")

        if isinstance(assignment[0], str):
            if self.modeler._is3d:
                props = dict(
                    {"Objects": assignment, "Conductor number": str(conductors_number), "Point out of terminal": point}
                )
                bound_type = "CoilTerminal"
            else:
                props = dict(
                    {
                        "Objects": assignment,
                        "Conductor number": str(conductors_number),
                        "PolarityType": polarity.lower(),
                    }
                )
                bound_type = "Coil"
        else:
            if self.modeler._is3d:
                props = dict(
                    {"Faces": assignment, "Conductor number": str(conductors_number), "Point out of terminal": point}
                )
                bound_type = "CoilTerminal"
            else:
                raise AEDTRuntimeError("Face Selection is not allowed in Maxwell 2D. Provide a 2D object.")

        return self._create_boundary(name, props, bound_type)

    @pyaedt_function_handler(input_object="assignment", reference_cs="coordinate_system")
    def assign_force(self, assignment, coordinate_system="Global", is_virtual=True, force_name=None):
        """Assign a force to one or more objects.

        Force assignment can be calculated based upon the solver type.
        For 3D solvers the available solution types are: ``Magnetostatic``,
        ``Electrostatic``, ``Eddy Current``, ``Transient`` and ``Electric Transient``.
        For 2D solvers the available solution types are: ``Magnetostatic``,
        ``Electrostatic``, ``Eddy Current`` and ``Transient``.

        Parameters
        ----------
        assignment : str, list
            One or more objects to assign the force to.
        coordinate_system : str, optional
            Name of the reference coordinate system. The default is ``"Global"``.
        is_virtual : bool, optional
            Whether the force is virtual. The default is ``True.``
        force_name : str, optional
            Name of the force. The default is ``None``, in which case the default
            name is used.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.AssignForce

        Examples
        --------

        Assign virtual force to a magnetic object:

        >>> from ansys.aedt.core import Maxwell3d
        >>> m3d = Maxwell3d()
        >>> iron_object = m3d.modeler.create_box([0, 0, 0],[2, 10, 10],name="iron")
        >>> magnet_object = m3d.modeler.create_box([10, 0, 0],[2, 10, 10],name="magnet")
        >>> m3d.assign_material(iron_object,"iron")
        >>> m3d.assign_material(magnet_object,"NdFe30")
        >>> m3d.assign_force("iron",is_virtual=True,force_name="force_iron")

        Assign Lorentz force to a conductor:

        >>> conductor1 = m3d.modeler.create_box([0, 0, 0],[1, 1, 10],name="conductor1")
        >>> conductor2 = m3d.modeler.create_box([10, 0, 0],[1, 1, 10],name="conductor2")
        >>> m3d.assign_material(conductor1,"copper")
        >>> m3d.assign_material(conductor2,"copper")
        >>> m3d.assign_force("conductor1",is_virtual=False,force_name="force_copper") # conductor, use Lorentz force
        >>> m3d.release_desktop(True, True)
        """
        if self.solution_type in (SOLUTIONS.Maxwell3d.ACConduction, SOLUTIONS.Maxwell3d.DCConduction):
            raise AEDTRuntimeError("Solution type has no 'Matrix' parameter.")

        assignment = self.modeler.convert_to_selections(assignment, True)
        if not force_name:
            force_name = generate_unique_name("Force")
        if self.design_type == "Maxwell 3D":
            prop = dict(
                {
                    "Name": force_name,
                    "Reference CS": coordinate_system,
                    "Is Virtual": is_virtual,
                    "Objects": assignment,
                }
            )
        else:
            prop = dict(
                {
                    "Name": force_name,
                    "Reference CS": coordinate_system,
                    "Objects": assignment,
                }
            )
        return self._create_boundary(force_name, prop, "Force")

    @pyaedt_function_handler(input_object="assignment", reference_cs="coordinate_system")
    def assign_torque(
        self, assignment, coordinate_system="Global", is_positive=True, is_virtual=True, axis="Z", torque_name=None
    ):
        """Assign a torque to one or more objects.

        Torque assignment can be calculated based upon the solver type.
        For 3D solvers the available solution types are: ``Magnetostatic``,
        ``Electrostatic``, ``Eddy Current``, ``Transient`` and ``Electric Transient``.
        For 2D solvers the available solution types are: ``Magnetostatic``,
        ``Electrostatic``, ``Eddy Current`` and ``Transient``.

        Parameters
        ----------
        assignment : str or list
           One or more objects to assign the torque to.
        coordinate_system : str, optional
            Name of the reference coordinate system. The default is ``"Global"``.
        is_positive : bool, optional
            Whether the torque is positive. The default is ``True``.
        is_virtual : bool, optional
            Whether the torque is virtual. The default is ``True``.
        axis : str, optional
            Axis to apply the torque to. The default is ``"Z"``.
        torque_name : str, optional
            Name of the torque. The default is ``None``, in which
            case the default name is used.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.AssignTorque
        """
        if self.solution_type in (SOLUTIONS.Maxwell3d.ACConduction, SOLUTIONS.Maxwell3d.DCConduction):
            raise AEDTRuntimeError("Solution Type has not Matrix Parameter")

        if self.solution_type == SOLUTIONS.Maxwell3d.Transient:
            is_virtual = True
        assignment = self.modeler.convert_to_selections(assignment, True)
        if not torque_name:
            torque_name = generate_unique_name("Torque")
        if self.design_type == "Maxwell 3D":
            prop = dict(
                {
                    "Name": torque_name,
                    "Is Virtual": is_virtual,
                    "Coordinate System": coordinate_system,
                    "Axis": axis,
                    "Is Positive": is_positive,
                    "Objects": assignment,
                }
            )
        else:
            prop = dict(
                {
                    "Name": torque_name,
                    "Coordinate System": coordinate_system,
                    "Is Positive": is_positive,
                    "Objects": assignment,
                }
            )
        return self._create_boundary(torque_name, prop, "Torque")

    @pyaedt_function_handler()
    def solve_inside(self, name, activate=True):
        """Solve inside to generate a solution inside an object.

        With this method, Maxwell will create a mesh inside the object and generate the solution from the mesh.

        Parameters
        ----------
        name : str
            Name of the object to generate the solution into.

        activate : bool, optional
            The default value is ``True``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.ChangeProperty
        """
        self.modeler[name].solve_inside = activate
        return True

    @pyaedt_function_handler()
    def analyze_from_zero(self):
        """Force the next solve to start from time 0 for a given setup.

        This method applies only to the Transient solution type.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.ResetSetupToTimeZero
        """
        if self.solution_type != SOLUTIONS.Maxwell3d.Transient:
            raise AEDTRuntimeError("This methods work only with Maxwell Transient Analysis.")

        self.oanalysis.ResetSetupToTimeZero(self._setup)
        self.analyze()
        return True

    @pyaedt_function_handler(val="angle")
    def set_initial_angle(self, motion_setup, angle):
        """Set the initial angle.

        Parameters
        ----------
        motion_setup : str
            Name of the motion setup.
        angle : float
            Value of the angle in degrees.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesign.ChangeProperty
        """
        self.odesign.ChangeProperty(
            [
                "NAME:AllTabs",
                [
                    "NAME:Maxwell2D",
                    ["NAME:PropServers", "ModelSetup:" + motion_setup],
                    ["NAME:ChangedProps", ["NAME:Initial Position", "Value:=", angle]],
                ],
            ]
        )
        return True

    @pyaedt_function_handler(entity_list="assignment")
    def assign_symmetry(self, assignment, symmetry_name=None, is_odd=True):
        """Assign symmetry boundary.

        This boundary condition defines a plane of geometric or magnetic symmetry in a structure.
        Assign it only to the outer surfaces of the problem region.

        Parameters
        ----------
        assignment : list
            List IDs or :class:`ansys.aedt.core.modeler.elements_3d.EdgePrimitive` or
            :class:`ansys.aedt.core.modeler.elements_3d.FacePrimitive`.
        symmetry_name : str, optional
            Name of the symmetry.
        is_odd : bool, optional
            Type of the symmetry. The default is ``True`,` in which case the H field
            is tangential to the boundary. If ``False``, the H field is normal to
            the boundary.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.AssignSymmetry
        """
        if symmetry_name is None:
            symmetry_name = generate_unique_name("Symmetry")

        prop = {}
        if assignment:
            if self.design_type == "Maxwell 2D":
                assignment = self.modeler.convert_to_selections(assignment, True)
                prop = dict({"Name": symmetry_name, "Edges": assignment, "IsOdd": is_odd})
            else:
                assignment = self.modeler.convert_to_selections(assignment, True)
                prop = dict({"Name": symmetry_name, "Faces": assignment, "IsOdd": is_odd})
        else:
            raise ValueError("At least one edge must be provided.")
        return self._create_boundary(symmetry_name, prop, "Symmetry")

    @pyaedt_function_handler(
        entities="assignment",
        coordinate_system_name="coordinate_system",
        coordinate_system_cartesian="coordinate_system_type",
    )
    def assign_current_density(
        self,
        assignment,
        current_density_name=None,
        phase="0deg",
        current_density_x="0",
        current_density_y="0",
        current_density_z="0",
        current_density_2d="0",
        coordinate_system="Global",
        coordinate_system_type="Cartesian",
    ):
        """Assign current density to a single or list of entities.

        This method specifies the x-, y-, and z-components of the current density in a conduction path.

        Parameters
        ----------
        assignment : list
            Objects to assign the current to.
        current_density_name : str, optional
            Current density name.
            If no name is provided a random name is generated.
        phase : str, optional
            Current density phase.
            Available units are 'deg', 'degmin', 'degsec' and 'rad'.
            Default value is 0deg.
        current_density_x : str, optional
            Current density X coordinate value.
            Default value is 0 A/m2.
        current_density_y : str, optional
            Current density Y coordinate value.
            Default value is 0 A/m2.
        current_density_z : str, optional
            Current density Z coordinate value.
            Default value is 0 A/m2.
        current_density_2d : str, optional
            Current density 2D value.
            Default value is 0 A/m2.
        coordinate_system : str, optional
            Coordinate system name.
            Default value is 'Global'.
        coordinate_system_type : str, optional
            Coordinate system cartesian.
            Possible values can be ``"Cartesian"``, ``"Cylindrical"``, and ``"Spherical"``.
            Default value is ``"Cartesian"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if self.solution_type not in (
            SOLUTIONS.Maxwell3d.EddyCurrent,
            SOLUTIONS.Maxwell3d.Magnetostatic,
            SOLUTIONS.Maxwell3d.Transient,
        ):
            raise AEDTRuntimeError(
                "Current density can only be applied to Eddy Current, Magnetostatic and 2D Transient solution types."
            )
        if re.compile(r"(\d+)\s*(\w+)").match(phase).groups()[1] not in ["deg", "degmin", "degsec", "rad"]:
            raise ValueError("Invalid phase unit.")
        if coordinate_system_type not in ("Cartesian", "Cylindrical", "Spherical"):
            raise ValueError("Invalid coordinate system.")

        if current_density_name is None:
            current_density_name = generate_unique_name("CurrentDensity")
        objects_list = self.modeler.convert_to_selections(assignment, True)

        try:
            if self.modeler._is3d:
                if self.solution_type == SOLUTIONS.Maxwell3d.Transient:
                    raise AEDTRuntimeError(
                        "Current density can only be applied to Eddy Current or Magnetostatic solution types."
                    )

                common_props = {
                    "Objects": objects_list,
                    "CurrentDensityX": current_density_x,
                    "CurrentDensityY": current_density_y,
                    "CurrentDensityZ": current_density_z,
                    "CoordinateSystem Name": coordinate_system,
                    "CoordinateSystem Type": coordinate_system_type,
                }

                if len(objects_list) > 1:
                    current_density_group_names = []
                    for x in range(0, len(objects_list)):
                        current_density_group_names.append(current_density_name + f"_{str(x + 1)}")
                    bound_props = {"items": current_density_group_names}
                    if self.solution_type == SOLUTIONS.Maxwell3d.EddyCurrent:
                        common_props["Phase"] = phase
                    bound_props[current_density_group_names[0]] = common_props.copy()
                    bound_name = current_density_group_names[0]
                    bound_type = "CurrentDensityGroup"
                else:
                    if self.solution_type == SOLUTIONS.Maxwell3d.EddyCurrent:
                        common_props["Phase"] = phase
                    bound_props = common_props
                    bound_name = current_density_name
                    bound_type = "CurrentDensity"
            else:
                common_props = {
                    "Objects": objects_list,
                    "Value": current_density_2d,
                    "CoordinateSystem": "",
                }
                if len(objects_list) > 1:
                    current_density_group_names = []
                    for x in range(0, len(objects_list)):
                        current_density_group_names.append(current_density_name + f"_{str(x + 1)}")
                    bound_props = {"items": current_density_group_names}
                    if self.solution_type == SOLUTIONS.Maxwell3d.EddyCurrent:
                        common_props["Phase"] = phase
                    bound_props[current_density_group_names[0]] = common_props.copy()
                    bound_name = current_density_group_names[0]
                    bound_type = "CurrentDensityGroup"
                else:
                    if self.solution_type == SOLUTIONS.Maxwell3d.EddyCurrent:
                        common_props["Phase"] = phase
                    bound_props = common_props
                    bound_name = current_density_name
                    bound_type = "CurrentDensity"

            return self._create_boundary(bound_name, bound_props, bound_type)
        except Exception:
            raise AEDTRuntimeError("Couldn't assign current density to desired list of objects.")

    @pyaedt_function_handler(input_object="assignment", radiation_name="radiation")
    def assign_radiation(self, assignment, radiation=None):
        """Assign radiation boundary to one or more objects.

        Radiation assignment can be calculated based upon the solver type.
        Available solution type is: ``Eddy Current``.

        Parameters
        ----------
        assignment : str, list
            One or more objects to assign the radiation to.
        radiation : str, optional
            Name of the force. The default is ``None``, in which case the default
            name is used.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Radiation objects. If the method fails to execute it returns ``False``.

        References
        ----------
        >>> oModule.Radiation

        Examples
        --------

        Assign radiation boundary to one box and one face:

        >>> from ansys.aedt.core import Maxwell3d
        >>> m3d = Maxwell3d()
        >>> box1 = m3d.modeler.create_box([0, 0, 0],[2, 10, 10])
        >>> box2 = m3d.modeler.create_box([10, 0, 0],[2, 10, 10])
        >>> m3d.assign_radiation([box1, box2.faces[0]])
        >>> m3d.release_desktop(True, True)
        """
        if self.solution_type != SOLUTIONS.Maxwell3d.EddyCurrent:
            raise AEDTRuntimeError("Excitation applicable only to Eddy Current.")
        if not radiation:
            radiation = generate_unique_name("Radiation")
        elif radiation in self.modeler.get_boundaries_name():
            radiation = generate_unique_name(radiation)

        listobj = self.modeler.convert_to_selections(assignment, True)
        props = {"Objects": [], "Faces": []}
        for sel in listobj:
            if isinstance(sel, str):
                props["Objects"].append(sel)
            elif isinstance(sel, int):
                props["Faces"].append(sel)
        return self._create_boundary(radiation, props, "Radiation")

    @pyaedt_function_handler(objects="assignment")
    def enable_harmonic_force(
        self,
        assignment,
        force_type=0,
        window_function="Rectangular",
        use_number_of_last_cycles=True,
        last_cycles_number=1,
        calculate_force="Harmonic",
    ):
        """Enable the harmonic force calculation for the transient analysis.

        Parameters
        ----------
        assignment : list
            List of object names for force calculations.
        force_type : int, optional
            Force type. Options are ``0`` for objects, ``1`` for surface, and ``2`` for volumetric.
        window_function : str, optional
            Windowing function. Default is ``"Rectangular"``.
            Available options are: ``"Rectangular"``, ``"Tri"``, ``"Van Hann"``, ``"Hamming"``,
            ``"Blackman"``, ``"Lanczos"``, ``"Welch"``.
        use_number_of_last_cycles : bool, optional
            Use number of last cycles for force calculations. Default is ``True``.
        last_cycles_number : int, optional
            Defines the number of cycles to compute if `use_number_of_last_cycle` is ``True``.
        calculate_force : sr, optional
            How to calculate force. The default is ``"Harmonic"``.
            Options are ``"Harmonic"`` and ``"Transient"``.


        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        if self.solution_type != SOLUTIONS.Maxwell3d.Transient:
            raise AEDTRuntimeError("This methods work only with Maxwell Transient Analysis.")

        assignment = self.modeler.convert_to_selections(assignment, True)
        self.odesign.EnableHarmonicForceCalculation(
            [
                "EnabledObjects:=",
                assignment,
                "ForceType:=",
                force_type,
                "WindowFunctionType:=",
                window_function,
                "UseNumberOfLastCycles:=",
                use_number_of_last_cycles,
                "NumberOfLastCycles:=",
                last_cycles_number,
                "StartTime:=",
                "0s",
                "UseNumberOfCyclesForStopTime:=",
                True,
                "NumberOfCyclesForStopTime:=",
                1,
                "StopTime:=",
                "0.01s",
                "OutputFreqRangeType:=",
                "Use All",
                "CaculateForceType:=",
                calculate_force + " Force",
            ]
        )
        return True

    @pyaedt_function_handler(layout_component_name="assignment")
    def enable_harmonic_force_on_layout_component(
        self,
        assignment,
        nets,
        force_type=0,
        window_function="Rectangular",
        use_number_of_last_cycles=True,
        last_cycles_number=1,
        calculate_force="Harmonic",
        start_time="0s",
        stop_time="2ms",
        use_number_of_cycles_for_stop_time=True,
        number_of_cycles_for_stop_time=1,
        include_no_layer=True,
    ):
        # type: (str, dict, int, str,bool, int, str, str, str, bool, int, bool) -> bool
        """Enable the harmonic force calculation for the transient analysis.

        Parameters
        ----------
        assignment : str
            Name of layout component to apply harmonic forces to.
        nets : dict
            Dictionary containing nets and layers to enable harmonic forces on.
        force_type : int, optional
            Force Type. ``0`` for Objects, ``1`` for Surface, ``2`` for volumetric.
        window_function : str, optional
            Windowing function. Default is ``"Rectangular"``.
            Available options are: ``"Rectangular"``, ``"Tri"``, ``"Van Hann"``, ``"Hamming"``,
            ``"Blackman"``, ``"Lanczos"``, ``"Welch"``.
        use_number_of_last_cycles : bool, optional
            Use number Of last cycles for force calculations. Default is ``True``.
        last_cycles_number : int, optional
            Defines the number of cycles to compute if `use_number_of_last_cycle` is ``True``.
        calculate_force : str, optional
            How to calculate force. The default is ``"Harmonic"``.
            Options are ``"Harmonic"`` and ``"Transient"``.
        start_time : str, optional
            Harmonic Force Start Time. Default is ``"0s"``.
        stop_time : str, optional
            Harmonic Force Stop Time. Default is ``"2ms"``.
        use_number_of_cycles_for_stop_time : bool, optional
            Use number of cycles for force stop time calculations. Default is ``True``.
        number_of_cycles_for_stop_time : int, optional
            Number of cycles for force stop time calculations. Default is ``1``.
        include_no_layer : bool, optional
            Whether to include ``"<no-layer>"`` layer or not (used for vias). Default is ``True``.


        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if self.solution_type != SOLUTIONS.Maxwell3d.TransientAPhiFormulation:
            raise AEDTRuntimeError("This methods work only with Maxwell TransientAPhiFormulation Analysis.")

        args = [
            "ForceType:=",
            force_type,
            "WindowFunctionType:=",
            window_function,
            "UseNumberOfLastCycles:=",
            use_number_of_last_cycles,
            "NumberOfLastCycles:=",
            last_cycles_number,
            "StartTime:=",
            start_time,
            "UseNumberOfCyclesForStopTime:=",
            use_number_of_cycles_for_stop_time,
            "NumberOfCyclesForStopTime:=",
            number_of_cycles_for_stop_time,
            "StopTime:=",
            stop_time,
            "OutputFreqRangeType:=",
            "Use All",
            "CaculateForceType:=",
            calculate_force + " Force",
        ]
        args2 = [
            "NAME:NetsAndLayersChoices",
            [
                "NAME:" + assignment,
                [
                    "NAME:NetLayerSetMap",
                ],
            ],
        ]
        for net, layers in nets.items():
            if include_no_layer:
                args2[1][1].append(["Name:" + net, "LayerSet:=", ["<no-layer>"] + layers])
            else:
                args2[1][1].append(["Name:" + net, "LayerSet:=", layers])
        args.append(args2)
        self.odesign.EnableHarmonicForceCalculation(args)
        return True

    @pyaedt_function_handler(setup_name="setup")
    def export_element_based_harmonic_force(
        self,
        output_directory=None,
        setup=None,
        start_frequency=None,
        stop_frequency=None,
        number_of_frequency=None,
    ):
        """Export an element-based harmonic force data to a .csv file.

        Parameters
        ----------
        output_directory : str, optional
            Path for the output directory. If ``None`` pyaedt working dir will be used.
        setup : str, optional
            Name of the solution setup. If ``None``, the nominal setup is used.
        start_frequency : float, optional
            When a float is entered the Start-Stop Frequency approach is used.
        stop_frequency : float, optional
            When a float is entered, the Start-Stop Frequency approach is used.
        number_of_frequency : int, optional
            When a number is entered, the number of frequencies approach is used.

        Returns
        -------
        str
            Path to the export directory.
        """
        if self.solution_type not in (SOLUTIONS.Maxwell3d.Transient, SOLUTIONS.Maxwell3d.TransientAPhiFormulation):
            raise AEDTRuntimeError("This methods work only with Maxwell Transient Analysis.")

        if not output_directory:
            output_directory = self.working_directory
        if not setup:
            setup = self.setups[0].name
        freq_option = 1
        f1 = -1
        f2 = -1
        if start_frequency and stop_frequency:
            freq_option = 2
            f1 = start_frequency
            f2 = stop_frequency
        elif number_of_frequency:
            freq_option = 3
            f1 = number_of_frequency
        self.odesign.ExportElementBasedHarmonicForce(output_directory, setup, freq_option, f1, f2)
        return output_directory

    @pyaedt_function_handler()
    def create_external_circuit(self, circuit_design=None):
        """
        Create the external circuit including all the windings of type ``External`` in the Maxwell design.

        Parameters
        ----------
        circuit_design : str, optional
            Name of the created circuit design.
            If not provided the design name + ``_ckt`` is used.

        Returns
        -------
        :class:`ansys.aedt.core.maxwellcircuit.MaxwellCircuit`
            MaxwellCircuit object if successful, ``False`` otherwise.

        Examples
        --------
        >>> from ansys.aedt.core import Maxwell2d
        >>> m2d = Maxwell2d()
        >>> m2d.modeler.create_circle([0, 0, 0], 10, name="Coil1")
        >>> m2d.assign_coil(assignment=["Coil1"])
        >>> m2d.assign_winding(assignment=["Coil1"], winding_type="External", name="Winding1")
        >>> cir = m2d.create_external_circuit()
        >>> m2d.release_desktop(True, True)
        """
        if self.solution_type not in (SOLUTIONS.Maxwell3d.EddyCurrent, SOLUTIONS.Maxwell3d.Transient):
            raise AEDTRuntimeError(
                "External circuit excitation for windings is available only for Eddy Current or Transient solutions."
            )

        if not circuit_design:
            circuit_design = self.design_name + "_ckt"

        from ansys.aedt.core.maxwellcircuit import MaxwellCircuit

        circuit = MaxwellCircuit(design=circuit_design)

        wdg_keys = ["Winding", "Winding Group"]
        wdgs = []
        for wdg_key in wdg_keys:
            if wdg_key in self.excitations_by_type.keys():
                [wdgs.append(w) for w in self.excitations_by_type[wdg_key]]
        if not wdgs:
            raise AEDTRuntimeError("No windings in the Maxwell design.")

        external_wdgs = [w for w in wdgs if w.props["Type"] == "External"]

        for w in external_wdgs:
            circuit.modeler.schematic.create_winding(name=w.name)

        return circuit

    @pyaedt_function_handler()
    def edit_external_circuit(self, netlist_file_path, schematic_design_name, parameters=None):
        """
        Edit the external circuit for the winding and allow editing of the circuit parameters.

        Parameters
        ----------
        netlist_file_path : str
            Path to the circuit netlist file.
        schematic_design_name : str
            Name of the schematic design.
        parameters : dict, optional
            Name and value of the circuit parameters.
            Parameters must be provided as a dictionary, where the key is the parameter name
            and the value is the parameter value.
            If the dictionary is provided, the ``netlist_file_path`` parameter is automatically
            set to an empty string.
            The default is ``None``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if schematic_design_name not in self.design_list:
            raise AEDTRuntimeError(f"Schematic design '{schematic_design_name}' is not in design list.")

        odesign = self.desktop_class.active_design(self.oproject, schematic_design_name)
        oeditor = odesign.SetActiveEditor("SchematicEditor")
        if is_linux and settings.aedt_version == "2024.1":  # pragma: no cover
            time.sleep(1)
            self.desktop_class.close_windows()
        comps = oeditor.GetAllComponents()
        sources_array = []
        sources_type_array = []
        for comp in comps:
            if "Voltage Source" in oeditor.GetPropertyValue("ComponentTab", comp, "Description"):
                comp_id = "V" + comp.split("@")[1].split(";")[1]
            elif "Current Source" in oeditor.GetPropertyValue("ComponentTab", comp, "Description"):
                comp_id = "I" + comp.split("@")[1].split(";")[1]
            else:
                continue
            sources_array.append(comp_id)
            refdes = oeditor.GetPropertyValue("ComponentTab", comp, "RefDes")
            comp_instance = oeditor.GetCompInstanceFromRefDes(refdes)
            if "DC" in oeditor.GetPropertyValue("ComponentTab", comp, "Description"):
                sources_type_array.append(1)
            else:
                source_type = comp_instance.GetPropHost().GetText("Type")
                if source_type == "TIME":
                    sources_type_array.append(1)
                elif source_type == "POS":
                    sources_type_array.append(2)
                elif source_type == "SPEED":
                    sources_type_array.append(3)
        names = []
        values = []
        if parameters:
            names = list(parameters.keys())
            values = list(parameters.values())
            netlist_file_path = ""
        self.oboundary.EditExternalCircuit(netlist_file_path, sources_array, sources_type_array, names, values)
        return True

    @pyaedt_function_handler(setupname="name", setuptype="setup_type")
    def create_setup(self, name="MySetupAuto", setup_type=None, **kwargs):
        """Create an analysis setup for Maxwell 3D or 2D.

        Optional arguments are passed using the ``setup_type`` and ``name``
        parameters.
        Keyword names correspond to the ``setuptype`` corresponding to the native AEDT API.
        The list of keywords here is not exhaustive.

        Parameters
        ----------
        setup_type : int, str, optional
            Type of the setup. Depending on the solution type, options are
            ``"AC Conduction"``, ``"DC Conduction"``, ``"EddyCurrent"``,
            ``"Electric Transient"``, ``"Electrostatic"``, ``"Magnetostatic"``,
            and ``Transient"``.
        name : str, optional
            Name of the setup. The default is ``"Setup1"``.
        **kwargs : dict, optional
            Available keys depend on the setup chosen.
            For more information, see :doc:`../SetupTemplatesMaxwell`.

        Returns
        -------
        :class:`ansys.aedt.core.modules.solve_setup.SetupMaxwell`
            3D Solver Setup object.

        References
        ----------
        >>> oModule.InsertSetup

        Examples
        --------
        >>> from ansys.aedt.core import Maxwell3d
        >>> m3d = Maxwell3d()
        >>> m3d.create_setup(name="My_Setup",setup_type="EddyCurrent",MaximumPasses=10,PercentError=2)
        >>> m3d.release_desktop(True, True)
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

    @pyaedt_function_handler(file_path="output_file", setup_name="setup")
    def export_rl_matrix(
        self,
        matrix_name,
        output_file,
        is_format_default=True,
        width=8,
        precision=2,
        is_exponential=False,
        setup=None,
        default_adaptive="LastAdaptive",
        is_post_processed=False,
    ):
        """Export R/L matrix after solving.

        Parameters
        ----------
        matrix_name : str
            Matrix name to be exported.
        output_file : str
            Output file path to export R/L matrix file to.
            Extension must be ``.txt``.
        is_format_default : bool, optional
            Whether the exported format is default or not.
            If False the custom format is set (no exponential).
        width : int, optional
            Column width in exported .txt file.
        precision : int, optional
            Decimal precision number in exported \\*.txt file.
        is_exponential : bool, optional
            Whether the format number is exponential or not.
        setup : str, optional
            Name of the setup.
            If not provided, the active setup is used.
        default_adaptive : str, optional
            Adaptive type.
            The default is ``"LastAdaptive"``.
        is_post_processed : bool, optional
            Boolean to check if it is post processed. Default value is ``False``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if self.solution_type not in [
            SOLUTIONS.Maxwell2d.EddyCurrentXY,
            SOLUTIONS.Maxwell2d.EddyCurrentZ,
            SOLUTIONS.Maxwell3d.EddyCurrent,
        ]:
            raise AEDTRuntimeError("RL Matrix can only be exported if solution type is Eddy Current.")

        matrix_names_list = [matrix.name for matrix in self.boundaries if isinstance(matrix, MaxwellParameters)]
        if not matrix_names_list:
            raise AEDTRuntimeError("Matrix list is empty, can't export a valid matrix.")
        elif matrix_name not in matrix_names_list:
            raise AEDTRuntimeError("Matrix name doesn't exist, provide and existing matrix name.")

        if os.path.splitext(output_file)[1] != ".txt":
            raise AEDTRuntimeError("File extension must be .txt")

        if setup is None:
            setup = self.active_setup

        analysis_setup = setup + " : " + default_adaptive

        if not self.available_variations.nominal_w_values_dict:
            variations = ""
        else:
            variations = " ".join(
                f"{key}=\\'{value}\\'" for key, value in self.available_variations.nominal_w_values_dict.items()
            )

        if not is_format_default:
            try:
                self.oanalysis.ExportSolnData(
                    analysis_setup,
                    matrix_name,
                    is_post_processed,
                    variations,
                    output_file,
                    -1,
                    is_format_default,
                    width,
                    precision,
                    is_exponential,
                )
            except Exception as e:
                raise AEDTRuntimeError("Solutions are empty. Solve before exporting.") from e
        else:
            try:
                self.oanalysis.ExportSolnData(analysis_setup, matrix_name, is_post_processed, variations, output_file)
            except Exception as e:
                raise AEDTRuntimeError("Solutions are empty. Solve before exporting.") from e

        return True

    @pyaedt_function_handler()
    def export_c_matrix(
        self,
        matrix_name,
        output_file,
        setup=None,
        default_adaptive="LastAdaptive",
        is_post_processed=False,
    ):
        """Export Capacitance matrix after solving.

        Parameters
        ----------
        matrix_name : str
            Matrix name to be exported.
        output_file : str
            Output file path to export R/L matrix file to.
            Extension must be ``.txt``.
        setup : str, optional
            Name of the setup.
            If not provided, the active setup is used.
        default_adaptive : str, optional
            Adaptive type.
            The default is ``"LastAdaptive"``.
        is_post_processed : bool, optional
            Boolean to check if it is post processed. Default value is ``False``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if self.solution_type not in [
            SOLUTIONS.Maxwell2d.ElectroStaticXY,
            SOLUTIONS.Maxwell2d.ElectroStaticZ,
            SOLUTIONS.Maxwell3d.ElectroStatic,
        ]:
            raise AEDTRuntimeError("C Matrix can only be exported if solution type is Electrostatic.")

        matrix_names_list = [matrix.name for matrix in self.boundaries if isinstance(matrix, MaxwellParameters)]
        if not matrix_names_list:
            raise AEDTRuntimeError("Matrix list is empty, can't export a valid matrix.")
        elif matrix_name not in matrix_names_list:
            raise AEDTRuntimeError("Matrix name doesn't exist, provide and existing matrix name.")

        if os.path.splitext(output_file)[1] != ".txt":
            raise AEDTRuntimeError("File extension must be .txt")

        if setup is None:
            setup = self.active_setup

        analysis_setup = setup + " : " + default_adaptive

        if not self.available_variations.nominal_w_values_dict:
            variations = ""
        else:
            variations = " ".join(
                f"{key}=\\'{value}\\'" for key, value in self.available_variations.nominal_w_values_dict.items()
            )

        self.oanalysis.ExportSolnData(analysis_setup, matrix_name, is_post_processed, variations, output_file)

        return True

    @pyaedt_function_handler
    # NOTE: Extend Mixin behaviour to handle Maxwell parameters
    def _create_boundary(self, name, props, boundary_type):
        # Non Maxwell parameters cases
        if boundary_type not in ("Force", "Torque", "Matrix", "LayoutForce"):
            return super()._create_boundary(name, props, boundary_type)

        # Maxwell parameters cases
        bound = MaxwellParameters(self, name, props, boundary_type)
        result = bound.create()
        if result:
            self._boundaries[bound.name] = bound
            self.logger.info(f"Boundary {boundary_type} {name} has been created.")
            return bound
        raise AEDTRuntimeError(f"Failed to create boundary {boundary_type} {name}")


class Maxwell3d(Maxwell, FieldAnalysis3D, object):
    """Provides the Maxwell 3D app interface.

    This class allows you to connect to an existing Maxwell 3D design or create a
    new Maxwell 3D design if one does not exist.

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
        the active version or latest installed version is used. This
        parameter is ignored when a script is launched within AEDT.
        Examples of input values are ``251``, ``25.1``, ``2025.1``, ``"2025.1"``.
    non_graphical : bool, optional
        Whether to launch AEDT in non-graphical mode. The default
        is ``False``, in which case AEDT is launched in graphical
        mode. This parameter is ignored when a script is launched within
        AEDT.
    new_desktop : bool, optional
        Whether to launch an instance of AEDT in a new thread, even if
        another instance of the ``specified_version`` is active on the
        machine. The default is ``False``. This parameter is ignored
        when a script is launched within AEDT.
    close_on_exit : bool, optional
        Whether to release AEDT on exit. The default is ``False``.
    student_version : bool, optional
        Whether to open the AEDT student version. The default is
        ``False``. This parameter is ignored when a script is launched
        within AEDT.
    machine : str, optional
        Machine name to connect the oDesktop session to. This works only in 2022 R2
        or later. The remote server must be up and running with the command
        `"ansysedt.exe -grpcsrv portnum"`. If the machine is `"localhost"`, the
        server also starts if not present.
    port : int, optional
        Port number on which to start the oDesktop communication on an already existing server.
        This parameter is ignored when a new server is created. It works only in 2022 R2 or later.
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
    Create an instance of Maxwell 3D and open the specified
    project, which is named ``mymaxwell.aedt``.

    >>> from ansys.aedt.core import Maxwell3d
    >>> m3d = Maxwell3d("mymaxwell.aedt")
    PyAEDT INFO: Added design ...

    Create an instance of Maxwell 3D using the 2025 R1 release and open
    the specified project, which is named ``mymaxwell2.aedt``.

    >>> m3d = Maxwell3d(version="2025.1", project="mymaxwell2.aedt")
    PyAEDT INFO: Added design ...

    """

    @property  # for legacy purposes
    def dim(self):
        """Dimensions."""
        return "3D"

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
        """Initialize the ``Maxwell`` class."""
        self.is3d = True
        FieldAnalysis3D.__init__(
            self,
            "Maxwell 3D",
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
        Maxwell.__init__(self)

    def _init_from_design(self, *args, **kwargs):
        self.__init__(**kwargs)

    @pyaedt_function_handler(geometry_selection="assignment", insulation_name="insulation")
    def assign_insulating(self, assignment, insulation=None):
        """Create an insulating boundary condition.

        This boundary condition is used to model very thin sheets of perfectly insulating material between
        touching conductors. Current cannot cross an insulating boundary.

        Parameters
        ----------
        assignment : str or int
            Objects or faces to apply the insulating boundary to.
        insulation : str, optional
            Name of the insulation. The default is ``None``, in which case a unique name is assigned.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Boundary object if successful, ``False`` otherwise.

        References
        ----------
        >>> oModule.AssignInsulating

        Examples
        --------

        Create a box and assign insulating boundary to it.

        >>> from ansys.aedt.core import Maxwell3d
        >>> m3d = Maxwell3d()
        >>> insulated_box = m3d.modeler.create_box([50, 0, 50],[294, 294, 19],name="InsulatedBox")
        >>> insulating_assignment = m3d.assign_insulating(assignment=insulated_box,insulation="InsulatingExample")
        >>> m3d.release_desktop(True, True)
        """

        if self.solution_type not in (
            SOLUTIONS.Maxwell3d.Magnetostatic,
            SOLUTIONS.Maxwell3d.EddyCurrent,
            SOLUTIONS.Maxwell3d.Transient,
            SOLUTIONS.Maxwell3d.TransientAPhiFormulation,
            SOLUTIONS.Maxwell3d.DCConduction,
            SOLUTIONS.Maxwell3d.ACConduction,
            SOLUTIONS.Maxwell3d.ElectroDCConduction,
        ):
            raise AEDTRuntimeError(f"This method does not work with solution type '{self.solution_type}'")

        if not insulation:
            insulation = generate_unique_name("Insulation")
        elif insulation in self.modeler.get_boundaries_name():
            insulation = generate_unique_name(insulation)

        listobj = self.modeler.convert_to_selections(assignment, True)
        props = {"Objects": [], "Faces": []}
        for sel in listobj:
            if isinstance(sel, str):
                props["Objects"].append(sel)
            elif isinstance(sel, int):
                props["Faces"].append(sel)
        return self._create_boundary(insulation, props, "Insulating")

    @pyaedt_function_handler(geometry_selection="assignment", impedance_name="impedance")
    def assign_impedance(
        self,
        assignment,
        material_name=None,
        permeability=0.0,
        conductivity=None,
        non_linear_permeability=False,
        impedance=None,
    ):
        """Create an impedance boundary condition for Transient or Eddy Current solvers.

        This boundary condition is used to simulate the effect of induced currents in a conductor without
        explicitly computing them.

        Parameters
        ----------
        assignment : str
            Faces or objects to apply the impedance boundary to.
        material_name : str, optional
            Material name. The default is ``None``. If other than ``None``, material properties values are extracted
            from the named material in the list of materials available. The default value is ``None``.
        permeability : float, optional
            Permeability of the material.The default value is ``0.0``.
        conductivity : float, optional
            Conductivity of the material. The default value is ``None``.
        non_linear_permeability : bool, optional
            If the option ``material_name`` is activated, the permeability can either be linear or not.
            The default value is ``False``.
        impedance : str, optional
            Name of the impedance. The default is ``None``, in which case a unique name is assigned.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Boundary object if successful, ``False`` otherwise.

        References
        ----------
        >>> oModule.AssignImpedance

        Examples
        --------

        Create a box and assign impedance boundary to the faces.

        >>> from ansys.aedt.core import Maxwell3d
        >>> m3d = Maxwell3d()
        >>> shield = m3d.modeler.create_box([-50, -50, -50],[294, 294, 19],name="shield")
        >>> shield_faces = m3d.modeler.select_allfaces_fromobjects(["shield"])
        >>> impedance_assignment = m3d.assign_impedance(assignment=shield_faces,impedance="ShieldImpedance")
        >>> m3d.release_desktop(True, True)
        """
        if self.solution_type not in (SOLUTIONS.Maxwell3d.Transient, SOLUTIONS.Maxwell3d.EddyCurrent):
            raise AEDTRuntimeError(f"This method does not work with solution type '{self.solution_type}'")

        if not impedance:
            impedance = generate_unique_name("Impedance")
        elif impedance in self.modeler.get_boundaries_name():
            impedance = generate_unique_name(impedance)

        listobj = self.modeler.convert_to_selections(assignment, True)
        props = {"Objects": [], "Faces": []}
        for sel in listobj:
            if isinstance(sel, str):
                props["Objects"].append(sel)
            elif isinstance(sel, int):
                props["Faces"].append(sel)

        if material_name is not None:
            props["UseMaterial"] = True
            props["MaterialName"] = material_name
            props["IsPermeabilityNonlinear"] = non_linear_permeability
            if conductivity is not None:
                props["Conductivity"] = conductivity
        else:
            props["UseMaterial"] = False
            props["Permeability"] = permeability
            props["Conductivity"] = conductivity
        return self._create_boundary(impedance, props, "Impedance")

    @pyaedt_function_handler(entities="assignment")
    def assign_current_density_terminal(self, assignment, current_density_name=None):
        """Assign current density terminal to a single or list of entities for an Eddy Current or Magnetostatic solver.

        Parameters
        ----------
        assignment : list of int or :class:`ansys.aedt.core.modeler.elements_3d.FacePrimitive`
            Faces or sheet objects to assign the current density terminal to.
        current_density_name : str, optional
            Current density name.
            If no name is provided a random name is generated.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if self.solution_type not in (SOLUTIONS.Maxwell3d.EddyCurrent, SOLUTIONS.Maxwell3d.Magnetostatic):
            raise AEDTRuntimeError(
                "Current density can only be applied to Eddy Current or Magnetostatic solution types."
            )

        try:
            if current_density_name is None:
                current_density_name = generate_unique_name("CurrentDensity")

            objects_list = self.modeler.convert_to_selections(assignment, True)

            if self.modeler._is3d:
                bound_objects = {"Faces": objects_list}
            else:
                bound_objects = {"Objects": objects_list}
            if len(objects_list) > 1:
                current_density_group_names = []
                for x in range(0, len(objects_list)):
                    current_density_group_names.append(current_density_name + f"_{str(x + 1)}")
                bound_name = current_density_group_names[0]
                props = {"items": current_density_group_names, bound_name: bound_objects}
                bound_type = "CurrentDensityTerminalGroup"
            else:
                props = bound_objects
                bound_name = current_density_name
                bound_type = "CurrentDensityTerminal"

            boundary = self._create_boundary(bound_name, props, bound_type)
            if boundary:
                return True
        except GrpcApiError as e:
            raise AEDTRuntimeError("Current density terminal could not be assigned.") from e
        return False

    @pyaedt_function_handler()
    def get_conduction_paths(self):
        """Get a dictionary of all conduction paths with relative objects. It works from AEDT 23R1.

        Returns
        -------
        dict
            Dictionary of all conduction paths with relative objects.

        """
        conduction_paths = {}

        try:
            paths = list(self.oboundary.GetConductionPaths())
            for path in paths:
                conduction_paths[path] = list(self.oboundary.GetConductionPathObjects(path))
            return conduction_paths
        except Exception:
            return conduction_paths

    @pyaedt_function_handler(master_entity="independent", slave_entity="dependent")
    def assign_master_slave(
        self,
        independent,
        dependent,
        u_vector_origin_coordinates_master,
        u_vector_pos_coordinates_master,
        u_vector_origin_coordinates_slave,
        u_vector_pos_coordinates_slave,
        reverse_master=False,
        reverse_slave=False,
        same_as_master=True,
        bound_name=None,
    ):
        """Assign dependent and independent boundary conditions to two faces of the same object.

        Parameters
        ----------
        independent : int
            ID of the master entity.
        dependent : int
            ID of the slave entity.
        u_vector_origin_coordinates_master : list
            Master's list of U vector origin coordinates.
        u_vector_pos_coordinates_master : list
            Master's list of U vector position coordinates.
        u_vector_origin_coordinates_slave : list
            Slave's list of U vector origin coordinates.
        u_vector_pos_coordinates_slave : list
            Slave's list of U vector position coordinates.
        reverse_master : bool, optional
            Whether to reverse the master edge to the V direction. The default is ``False``.
        reverse_slave : bool, optional
            Whether to reverse the master edge to the U direction. The default is ``False``.
        same_as_master : bool, optional
            Whether the B-Field of the slave edge and master edge are the same. The default is ``True``.
        bound_name : str, optional
            Name of the master boundary. The default is ``None``, in which case the default name
            is used. The name of the slave boundary has a ``_dep`` suffix.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`,
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Master and slave objects. If the method fails to execute it returns ``False``.

        References
        ----------
        >>> oModule.AssignIndependent
        >>> oModule.AssignDependent
        """
        try:
            independent = self.modeler.convert_to_selections(independent, True)
            dependent = self.modeler.convert_to_selections(dependent, True)
            if not bound_name:
                bound_name_m = generate_unique_name("Independent")
                bound_name_s = generate_unique_name("Dependent")
            else:
                bound_name_m = bound_name
                bound_name_s = bound_name + "_dep"
            list_coordinates = [
                u_vector_origin_coordinates_master,
                u_vector_origin_coordinates_slave,
                u_vector_pos_coordinates_master,
                u_vector_pos_coordinates_slave,
            ]
            if any(not isinstance(coordinates, list) for coordinates in list_coordinates):
                raise ValueError("Please provide a list of coordinates for U vectors.")
            for coordinates in list_coordinates:
                if any(not isinstance(x, str) for x in coordinates):
                    raise ValueError("Elements of coordinates system must be strings in the form of ``value+unit``.")
            if any(len(coordinates) != 3 for coordinates in list_coordinates):
                raise ValueError("Vector must contain 3 elements for x, y, and z coordinates.")
            u_master_vector_coordinates = dict(
                {
                    "Coordinate System": "Global",
                    "Origin": u_vector_origin_coordinates_master,
                    "UPos": u_vector_pos_coordinates_master,
                }
            )
            master_props = dict(
                {"Faces": independent, "CoordSysVector": u_master_vector_coordinates, "ReverseV": reverse_master}
            )
            master = self._create_boundary(bound_name_m, master_props, "Independent")
            if master:
                u_slave_vector_coordinates = dict(
                    {
                        "Coordinate System": "Global",
                        "Origin": u_vector_origin_coordinates_slave,
                        "UPos": u_vector_pos_coordinates_slave,
                    }
                )

                slave_props = dict(
                    {
                        "Faces": dependent,
                        "CoordSysVector": u_slave_vector_coordinates,
                        "ReverseU": reverse_slave,
                        "Independent": bound_name_m,
                        "RelationIsSame": same_as_master,
                    }
                )
                slave = self._create_boundary(bound_name_s, slave_props, "Dependent")
                if slave:
                    return master, slave
        except GrpcApiError as e:
            raise AEDTRuntimeError("Slave boundary could not be created.") from e
        return False

    @pyaedt_function_handler(objects_list="assignment")
    def assign_flux_tangential(self, assignment, flux_name=None):
        # type : (list, str = None) -> from ansys.aedt.core.modules.boundary.common.BoundaryObject
        """Assign a flux tangential boundary for a transient A-Phi solver.

        Parameters
        ----------
        assignment : list
            List of objects to assign the flux tangential boundary condition to.
        flux_name : str, optional
            Name of the flux tangential boundary. The default is ``None``,
            in which case a random name is automatically generated.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Boundary object if successful, ``False`` otherwise.

        References
        ----------
        >>> oModule.AssignFluxTangential

        Examples
        --------
        Create a box and assign a flux tangential boundary to one of its faces.

        >>> from ansys.aedt.core import Maxwell3d
        >>> m3d = Maxwell3d()
        >>> box = m3d.modeler.create_box([50, 0, 50],[294, 294, 19],name="Box")
        >>> flux_tangential = m3d.assign_flux_tangential(box.faces[0],"FluxExample")
        >>> m3d.release_desktop(True, True)
        """
        if self.solution_type != SOLUTIONS.Maxwell3d.TransientAPhiFormulation:
            raise AEDTRuntimeError("Flux tangential boundary can only be assigned to a transient APhi solution type.")

        assignment = self.modeler.convert_to_selections(assignment, True)

        if not flux_name:
            flux_name = generate_unique_name("FluxTangential")
        elif flux_name in self.modeler.get_boundaries_name():
            flux_name = generate_unique_name(flux_name)

        props = {"NAME": flux_name, "Faces": []}
        for sel in assignment:
            props["Faces"].append(sel)
        return self._create_boundary(flux_name, props, "FluxTangential")

    @pyaedt_function_handler(nets_layers_mapping="net_layers", reference_cs="coordinate_system")
    def assign_layout_force(
        self, net_layers, component_name, coordinate_system="Global", force_name=None, include_no_layer=True
    ):
        # type: (dict, str, str, str, bool) -> bool
        """Assign the layout force to a component in a Transient A-Phi solver.

        To access layout component features the Beta option has to be enabled first.

        Parameters
        ----------
        net_layers : dict
            Each <net, layer> pair represents the objects in the intersection of the corresponding net and layer.
            The layer name is from the list of layer names. The net name is the dictionary's key.
        component_name : str
            Name of the 3D component to assign the layout force to.
        coordinate_system : str, optional
            Reference coordinate system.
            If not provided, the global one is used.
        force_name : str, optional
            Name of the layout force.
            If not provided a random name will be generated.
        include_no_layer : bool, optional
            Whether to include ``"<no-layer>"`` layer or not (used for vias). Default is ``True``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.AssignLayoutForce

        Examples
        --------
        Create a dictionary to give as an input to assign_layout_force method.
        >>> nets_layers = {"<no-net>": ["PWR","TOP","UNNAMED_000","UNNAMED_002"],
        >>>                "GND": ["LYR_1","LYR_2","UNNAMED_006"]}
        >>>

        Assign layout force to a component.
        >>> from ansys.aedt.core import Maxwell3d
        >>> m3d = Maxwell3d()
        >>> m3d.assign_layout_force(net_layers=nets_layers,component_name="LC1_1")
        >>> m3d.release_desktop(True, True)
        """
        if component_name not in self.modeler.user_defined_component_names:
            raise AEDTRuntimeError("Provided component name doesn't exist in current design.")

        for key in net_layers.keys():
            if not isinstance(net_layers[key], list):
                net_layers[key] = list(net_layers[key])

        if not force_name:
            force_name = generate_unique_name("Layout_Force")

        nets_layers_props = None
        for key, valy in net_layers.items():
            layers = valy[:]
            if include_no_layer:
                layers = layers[:] + ["<no-layer>"]
            if nets_layers_props:
                nets_layers_props.append(dict({key: dict({"LayerSet": layers})}))
            else:
                nets_layers_props = [dict({key: dict({"LayerSet": layers})})]

        props = dict(
            {
                "Reference CS": coordinate_system,
                "NetsAndLayersChoices": dict({component_name: dict({"NetLayerSetMap": nets_layers_props})}),
            }
        )
        return self._create_boundary(force_name, props, "LayoutForce")

    @pyaedt_function_handler(faces="assignment")
    def assign_tangential_h_field(
        self,
        assignment,
        x_component_real=0,
        x_component_imag=0,
        y_component_real=0,
        y_component_imag=0,
        coordinate_system="Global",
        origin=None,
        u_pos=None,
        reverse=False,
        bound_name=None,
    ):
        """Assign a tangential H field boundary to a list of faces.

        Parameters
        ----------
        assignment : list of int  or :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
            List of objects to assign an end connection to.
        x_component_real : float, str, optional
            X component value real part. The default is ``0``.
        x_component_imag : float, str, optional
            X component value imaginary part. The default is ``0``.
        y_component_real : float, str, optional
            Y component value real part. The default is ``0``.
        y_component_imag : float, str, optional
            Y component value imaginary part. The default is ``0``.
        coordinate_system : str, optional
            Coordinate system to use for the UV vector.
        origin : list, optional
            Origin of the UV vector.
            The default is ``None`, in which case the bottom left vertex is used.
        u_pos : list, optional
            Direction of the U vector.
            The default is ``None``, in which case the top left vertex is used.
        reverse : bool, optional
            Whether the vector is reversed. The default is ``False``.
        bound_name : str, optional
            Name of the end connection boundary.
            The default is ``None``, in which case the default name is used.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Newly created object when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.AssignTangentialHField
        """
        if self.solution_type not in (SOLUTIONS.Maxwell3d.EddyCurrent, SOLUTIONS.Maxwell3d.Magnetostatic):
            raise AEDTRuntimeError("Tangential H Field is applicable only to Eddy Current.")

        assignment = self.modeler.convert_to_selections(assignment, True)
        if not bound_name:
            bound_name = generate_unique_name("TangentialHField")
        props = dict(
            {
                "Faces": assignment,
            }
        )
        if isinstance(assignment[0], str):
            props = dict(
                {
                    "Objects": assignment,
                }
            )
        props["ComponentXReal"] = x_component_real
        if self.solution_type == SOLUTIONS.Maxwell3d.EddyCurrent:
            props["ComponentXImag"] = x_component_imag
        props["ComponentYReal"] = y_component_real
        if self.solution_type == SOLUTIONS.Maxwell3d.EddyCurrent:
            props["ComponentYImag"] = y_component_imag
        if not origin and isinstance(assignment[0], int):
            edges = self.modeler.get_face_edges(assignment[0])
            origin = self.oeditor.GetEdgePositionAtNormalizedParameter(edges[0], 0)
            if not u_pos:
                u_pos = self.oeditor.GetEdgePositionAtNormalizedParameter(edges[0], 1)

        props["CoordSysVector"] = dict({"Coordinate System": coordinate_system, "Origin": origin, "UPos": u_pos})
        props["ReverseV"] = reverse
        return self._create_boundary(bound_name, props, "Tangential H Field")

    @pyaedt_function_handler(faces="assignment", bound_name="boundary")
    def assign_zero_tangential_h_field(self, assignment, boundary=None):
        """Assign a zero tangential H field boundary to a list of faces.

        Parameters
        ----------
        assignment : list of int or :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
            List of objects to assign an end connection to.
        boundary : str, optional
            Name of the end connection boundary. The default is ``None``, in which case the
            default name is used.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Newly created object. ``False`` if it fails.

        References
        ----------
        >>> oModule.AssignZeroTangentialHField
        """
        if self.solution_type != SOLUTIONS.Maxwell3d.EddyCurrent:
            raise AEDTRuntimeError("Tangential H Field is applicable only to Eddy Current.")

        assignment = self.modeler.convert_to_selections(assignment, True)
        if not boundary:
            boundary = generate_unique_name("ZeroTangentialHField")
        props = dict(
            {
                "Faces": assignment,
            }
        )
        return self._create_boundary(boundary, props, "Zero Tangential H Field")

    @pyaedt_function_handler()
    def assign_resistive_sheet(
        self,
        assignment,
        resistance="1ohm",
        name=None,
        non_linear=False,
        anode_a="300000000",
        anode_b="5",
        anode_c="110000000000000",
        anode_d="2",
        cathode_a="300000000",
        cathode_b="10",
        cathode_c="110000000000000",
        cathode_d="2",
    ):
        """Assign a resistive sheet boundary between two conductors.

        Available for Maxwell 3D Magnetostatic, Eddy Current and Transient designs.
        For 3D Magnetostatic designs, the user can specify the nonlinear anode and cathode coefficients.
        To understand the nonlinear relationship used by AEDT between the conductivity and current density,
        please refer to Maxwell Help guide.

        Parameters
        ----------
        assignment : list of int or :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
            List of objects to assign an end connection to.
        resistance : str, optional
            Resistance value with unit.
            For 3D Magnetostatic designs if non_linear is ``True``, it is not available.
            The default is ``1ohm``.
        name : str, optional
            Name of the boundary. The default is ``None``, in which case the default name is used.
        non_linear: bool, optional
            Whether the boundary is non-linear. The default is ``False``.
            Valid for 3D Magnetostatic designs only.
        anode_a : str, optional
            Anode a value that corresponds to the a coefficient in the non-linear relationship
            between conductivity and current density.
            The default value is ``"300000000"``.
        anode_b : str, optional
            Anode b value that corresponds to the b coefficient in the non-linear relationship
            between conductivity and current density.
            The default value is ``"10"``.
        anode_c : str, optional
            Anode c value that corresponds to the c coefficient in the non-linear relationship
            between conductivity and current density.
            The default value is ``"110000000000000"``.
        anode_d : str, optional
            Anode d value that corresponds to the d coefficient in the non-linear relationship
            between conductivity and current density.
            The default value is ``"2"``.
        cathode_a : str, optional
            Cathode a value that corresponds to the a coefficient in the non-linear relationship
            between conductivity and current density.
            The default value is ``"300000000"``.
        cathode_b : str, optional
            Cathode b value that corresponds to the b coefficient in the non-linear relationship
            between conductivity and current density.
            The default value is ``"10"``.
        cathode_c : str, optional
            Cathode c value that corresponds to the c coefficient in the non-linear relationship
            between conductivity and current density.
            The default value is ``"110000000000000"``.
        cathode_d : str, optional
            Cathode d value that corresponds to the d coefficient in the non-linear relationship
            between conductivity and current density.
            The default value is ``"2"``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Newly created object. ``False`` if it fails.

        References
        ----------
        >>> oModule.AssignResistiveSheet

        Examples
        --------
        >>> import ansys.aedt.core
        >>> from ansys.aedt.core.generic.constants import SOLUTIONS
        >>> m3d = ansys.aedt.core.Maxwell3d(solution_type="Transient")
        >>> my_box = m3d.modeler.create_box(origin=[0, 0, 0], sizes=[0.4, -1, 0.8], material="copper")
        >>> resistive_face = my_box.faces[0]
        >>> bound = m3d.assign_resistive_sheet(assignment=resistive_face, resistance="3ohm")
        >>> m3d.solution_type = SOLUTIONS.Maxwell3d.Magnetostatic
        >>> bound = m3d.assign_resistive_sheet(assignment=resistive_face, non_linear=True)
        >>> m3d.release_desktop()
        """
        if self.solution_type not in (
            SOLUTIONS.Maxwell3d.EddyCurrent,
            SOLUTIONS.Maxwell3d.Transient,
            SOLUTIONS.Maxwell3d.Magnetostatic,
        ):
            raise AEDTRuntimeError(
                "Resistive sheet is applicable only to Eddy Current, transient and magnetostatic solvers."
            )

        assignment = self.modeler.convert_to_selections(assignment, True)

        if not name:
            name = generate_unique_name("ResistiveSheet")

        listobj = self.modeler.convert_to_selections(assignment, True)

        props = {"Objects": [], "Faces": []}
        for sel in listobj:
            if isinstance(sel, str):
                props["Objects"].append(sel)
            elif isinstance(sel, int):
                props["Faces"].append(sel)

        if self.solution_type in (SOLUTIONS.Maxwell3d.EddyCurrent, SOLUTIONS.Maxwell3d.Transient):
            props["Resistance"] = resistance
        elif self.solution_type == SOLUTIONS.Maxwell3d.Magnetostatic:
            props["Nonlinear"] = non_linear
            props["AnodeParA"] = anode_a
            props["AnodeParB"] = anode_b
            props["AnodeParC"] = anode_c
            props["AnodeParD"] = anode_d
            props["CathodeParA"] = cathode_a
            props["CathodeParB"] = cathode_b
            props["CathodeParC"] = cathode_c
            props["CathodeParD"] = cathode_d

        return self._create_boundary(name, props, "ResistiveSheet")


class Maxwell2d(Maxwell, FieldAnalysis3D, object):
    """Provides the Maxwell 2D app interface.

    This class allows you to connect to an existing Maxwell 2D design or create a
    new Maxwell 2D design if one does not exist.

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
        the active version or latest installed version is used.
        This parameter is ignored when a script is launched within AEDT.
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
        Machine name to connect the oDesktop session to. This works only in 2022 R2
        or later. The remote server must be up and running with the command
        `"ansysedt.exe -grpcsrv portnum"`. If the machine is `"localhost"`,
        the server also starts if not present.
    port : int, optional
        Port number of which to start the oDesktop communication on an already existing
        server. This parameter is ignored when creating a new server. It works only in 2022
        R2 or later. The remote server must be up and running with the command `"ansysedt.exe -grpcsrv portnum"`.
    aedt_process_id : int, optional
        Process ID for the instance of AEDT to point PyAEDT at. The default is
        ``None``. This parameter is only used when ``new_desktop = False``.
    remove_lock : bool, optional
        Whether to remove lock to project before opening it or not.
        The default is ``False``, which means to not unlock
        the existing project if needed and raise an exception.

    Examples
    --------
    Create an instance of Maxwell 2D and connect to an existing
    Maxwell 2D design or create a new Maxwell 2D design if one does
    not exist.

    >>> from ansys.aedt.core import Maxwell2d
    >>> m2d = Maxwell2d()

    Create an instance of Maxwell 2D and link to a project named
    ``projectname``. If this project does not exist, create one with
    this name.

    >>> m2d = Maxwell2d(projectname)

    Create an instance of Maxwell 2D and link to a design named
    ``designname`` in a project named ``projectname``.

    >>> m2d = Maxwell2d(projectname,designname)
    """

    @property  # for legacy purposes
    def dim(self):
        """Dimensions."""
        return self.modeler.dimension

    @property
    def geometry_mode(self):
        """Geometry mode.

        References
        ----------
        >>> oDesign.GetGeometryMode"""
        return self.odesign.GetGeometryMode()

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
        FieldAnalysis3D.__init__(
            self,
            "Maxwell 2D",
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
        Maxwell.__init__(self)

    def _init_from_design(self, *args, **kwargs):
        self.__init__(**kwargs)

    @property
    def xy_plane(self):
        """Maxwell 2D plane between ``True`` and ``False``."""
        return self.design_solutions.xy_plane

    @xy_plane.setter
    def xy_plane(self, value=True):
        self.design_solutions.xy_plane = value

    @property
    def model_depth(self):
        """Model depth."""
        design_settings = self.design_settings
        if "ModelDepth" in design_settings:
            value_str = design_settings["ModelDepth"]
            return value_str
        else:
            return None

    @model_depth.setter
    def model_depth(self, value):
        """Set model depth."""
        if isinstance(value, float) or isinstance(value, int):
            value = self.value_with_units(value, self.modeler.model_units)
        self.change_design_settings({"ModelDepth": value})

    @pyaedt_function_handler(linefilter="line_filter", objectfilter="object_filter")
    def generate_design_data(self, line_filter=None, object_filter=None):
        """Generate a generic set of design data and store it in the extension directory in a ``design_data.json`` file.

        Parameters
        ----------
        line_filter : optional
            The default is ``None``.
        object_filter : optional
            The default is ``None``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """

        def convert(obj):
            if isinstance(obj, bool):
                return str(obj).lower()
            if isinstance(obj, (list, tuple)):
                return [convert(item) for item in obj]
            if isinstance(obj, dict):
                return {convert(key): convert(value) for key, value in obj.items()}
            return obj

        solid_bodies = self.modeler.solid_bodies
        if object_filter:
            solid_ids = [i for i, j in self.modeler._object_names_to_ids.items() if j.name in object_filter]
        else:
            solid_ids = [i for i in list(self.modeler._object_names_to_ids.keys())]
        self.design_data = {
            "Project Directory": self.project_path,
            "Working Directory": self.working_directory,
            "Library Directories": self.library_list,
            "Dimension": self.modeler.dimension,
            "GeoMode": self.geometry_mode,
            "ModelUnits": self.modeler.model_units,
            "Symmetry": self.symmetry_multiplier,
            "ModelDepth": self.model_depth,
            "ObjectList": solid_ids,
            "LineList": self.modeler.vertex_data_of_lines(line_filter),
            "VarList": self.variable_manager.variable_names,
            "Setups": self.existing_analysis_setups,
            "MaterialProperties": self.get_object_material_properties(solid_bodies),
        }

        design_file = os.path.join(self.working_directory, "design_data.json")
        write_configuration_file(self.design_data, design_file)
        return True

    @pyaedt_function_handler()
    def read_design_data(self):
        """Read back the design data as a dictionary.

        Returns
        -------
        dict
            Dictionary of design data.

        """
        design_file = os.path.join(self.working_directory, "design_data.json")
        return read_configuration_file(design_file)

    @pyaedt_function_handler(edge_list="assignment", bound_name="boundary")
    def assign_balloon(self, assignment, boundary=None):
        """Assign a balloon boundary to a list of edges.

        Parameters
        ----------
        assignment : list
            List of edges.
        boundary : str, optional
            Name of the boundary. The default is ``None``, in which
            case the default name is used.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Boundary object. If the method fails to execute it returns ``False``.

        References
        ----------
        >>> oModule.AssignBalloon


        Examples
        --------
        Set balloon boundary condition in Maxwell 2D.

        >>> from ansys.aedt.core import Maxwell2d
        >>> m2d = Maxwell2d()
        >>> region_id = m2d.modeler.create_region()
        >>> region_edges = region_id.edges
        >>> m2d.assign_balloon(edge_list=region_edges)
        """
        assignment = self.modeler.convert_to_selections(assignment, True)

        if not boundary:
            boundary = generate_unique_name("Balloon")

        props = dict({"Edges": assignment})
        return self._create_boundary(boundary, props, "Balloon")

    @pyaedt_function_handler(input_edge="assignment", vectorvalue="vector_value", bound_name="boundary")
    def assign_vector_potential(self, assignment, vector_value=0, boundary=None):
        """Assign a vector potential boundary condition to specified edges.

        This method is valid for Maxwell 2D Eddy Current, Magnetostatic, and Transient solvers.

        Parameters
        ----------
        assignment : list
            List of edge names or edge IDs to assign a vector to.
        vector_value : float, optional
            Value of the vector. The default is ``0``.
        boundary : str, optional
            Name of the boundary. The default is ``None``, in which
            case the default name is used.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Vector Potential Object. ``False`` if it fails.

        References
        ----------
        >>> oModule.AssignVectorPotential


        Examples
        --------
        Set vector potential to zero at the boundary edges in Maxwell 2D.

        >>> from ansys.aedt.core import Maxwell2d
        >>> m2d = Maxwell2d()
        >>> region_id = m2d.modeler.create_region()
        >>> region_edges = region_id.edges
        >>> m2d.assign_vector_potential(input_edge=region_edges)
        """
        assignment = self.modeler.convert_to_selections(assignment, True)

        if not boundary:
            boundary = generate_unique_name("Vector")
        if type(assignment[0]) is str:
            props2 = dict({"Objects": assignment, "Value": str(vector_value), "CoordinateSystem": ""})
        else:
            props2 = dict({"Edges": assignment, "Value": str(vector_value), "CoordinateSystem": ""})

        return self._create_boundary(boundary, props2, "Vector Potential")

    @pyaedt_function_handler(master_edge="independent", slave_edge="dependent", bound_name="boundary")
    def assign_master_slave(
        self, independent, dependent, reverse_master=False, reverse_slave=False, same_as_master=True, boundary=None
    ):
        """Assign dependent and independent boundary conditions to two edges of the same object.

        Parameters
        ----------
        independent : int
            ID of the master edge.
        dependent : int
            ID of the slave edge.
        reverse_master : bool, optional
            Whether to reverse the master edge to the V direction. The default is ``False``.
        reverse_slave : bool, optional
            Whether to reverse the master edge to the U direction. The default is ``False``.
        same_as_master : bool, optional
            Whether the B-Field of the slave edge and master edge are the same. The default is ``True``.
        boundary : str, optional
            Name of the master boundary. The default is ``None``, in which case the default name
            is used. The name of the slave boundary has a ``_dep`` suffix.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`,
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Master and slave objects. If the method fails to execute it returns ``False``.

        References
        ----------
        >>> oModule.AssignIndependent
        >>> oModule.AssignDependent
        """
        try:
            independent = self.modeler.convert_to_selections(independent, True)
            dependent = self.modeler.convert_to_selections(dependent, True)
            if not boundary:
                bound_name_m = generate_unique_name("Independent")
                bound_name_s = generate_unique_name("Dependent")
            else:
                bound_name_m = boundary
                bound_name_s = boundary + "_dep"
            master_props = dict({"Edges": independent, "ReverseV": reverse_master})
            master = self._create_boundary(bound_name_m, master_props, "Independent")
            if master:
                slave_props = dict(
                    {
                        "Edges": dependent,
                        "ReverseU": reverse_slave,
                        "Independent": bound_name_m,
                        "SameAsMaster": same_as_master,
                    }
                )
                slave = self._create_boundary(bound_name_s, slave_props, "Dependent")
                if slave:
                    return master, slave
        except GrpcApiError as e:
            raise AEDTRuntimeError("Slave boundary could not be created.") from e
        return False

    @pyaedt_function_handler(objects="assignment", bound_name="boundary")
    def assign_end_connection(self, assignment, resistance=0, inductance=0, boundary=None):
        """Assign an end connection to a list of objects.

        Parameters
        ----------
        assignment : list of int or str or :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
            List of objects to assign an end connection to.
        resistance : float or str, optional
            Resistance value. If float is provided, the units are assumed to be ohms.
            The default value is ``0``,
        inductance : float or str, optional
            Inductance value. If a float is provided, the units are assumed to Henry (H).
            The default value is ``0``.
        boundary : str, optional
            Name of the end connection boundary. The default is ``None``, in which case the
            default name is used.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`
            Newly created object. ``False`` if it fails.

        References
        ----------
        >>> oModule.AssignEndConnection
        """
        if self.solution_type not in (SOLUTIONS.Maxwell3d.EddyCurrent, SOLUTIONS.Maxwell3d.Transient):
            raise AEDTRuntimeError("Excitation applicable only to Eddy Current or Transient Solver.")
        if len(assignment) < 2:
            raise AEDTRuntimeError("At least 2 objects are needed.")

        assignment = self.modeler.convert_to_selections(assignment, True)
        if not boundary:
            boundary = generate_unique_name("EndConnection")

        props = dict(
            {
                "Objects": assignment,
                "ResistanceValue": self.value_with_units(resistance, "ohm"),
                "InductanceValue": self.value_with_units(inductance, "H"),
            }
        )
        return self._create_boundary(boundary, props, "EndConnection")
