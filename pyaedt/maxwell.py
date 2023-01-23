"""This module contains these Maxwell classes: ``Maxwell``, ``Maxwell2d``, and ``Maxwell3d``."""

from __future__ import absolute_import  # noreorder

import io
import json
import os
import re
from collections import OrderedDict

from pyaedt.application.Analysis3D import FieldAnalysis3D
from pyaedt.generic.constants import SOLUTIONS
from pyaedt.generic.DataHandlers import float_units
from pyaedt.generic.general_methods import generate_unique_name
from pyaedt.generic.general_methods import open_file
from pyaedt.generic.general_methods import pyaedt_function_handler
from pyaedt.modeler.geometry_operators import GeometryOperators
from pyaedt.modules.Boundary import BoundaryObject
from pyaedt.modules.Boundary import MaxwellParameters


class Maxwell(object):
    def __enter__(self):
        return self

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
        """Set the Design Symmetry Multiplier to a specified value.

        Parameters
        ----------
        value : int, optional
            Value to use as the Design Symmetry Multiplier coefficient. The default value is ``1``.

        Returns
        -------
        bool
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

    @pyaedt_function_handler()
    def set_core_losses(self, objects, value=True):
        """Whether to enable core losses for a set of objects.

        This method works only on ``EddyCurrent`` and ``Transient`` solutions.

        Parameters
        ----------
        objects : list, str
            List of object to apply core losses to.
        value : bool, optional
            Whether to enable core losses for the given list. The default is
            ``True``.

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

        >>> from pyaedt import Maxwell3d
        >>> maxwell_3d = Maxwell3d()
        >>> maxwell_3d.set_core_losses(["PQ_Core_Bottom", "PQ_Core_Top"], True)

        """
        if self.solution_type in ["EddyCurrent", "Transient"]:
            objects = self.modeler.convert_to_selections(objects, True)
            self.oboundary.SetCoreLoss(objects, value)
            return True
        else:
            raise Exception("Core losses is only available with `EddyCurrent` and `Transient` solutions.")
        return False

    @pyaedt_function_handler()
    def assign_matrix(
        self,
        sources,
        matrix_name=None,
        turns=None,
        return_path=None,
        group_sources=None,
        branches=None,
    ):
        """Assign a matrix to the selection.

        Parameters
        ----------
        sources : list, str
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
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        References
        ----------

        >>> oModule.AssignMatrix

        Examples
        --------
        Set matrix in a Maxwell analysis.

        >>> m2d = Maxwell2d(solution_type="MagnetostaticXY", close_on_exit=True, specified_version="2022.1")
        >>> coil1 = m2d.modeler.create_rectangle([0, 1.5, 0], [8, 3], is_covered=True, name="Coil_1")
        >>> coil2 = m2d.modeler.create_rectangle([8.5, 1.5, 0], [8, 3], is_covered=True, name="Coil_2")
        >>> coil3 = m2d.modeler.create_rectangle([16, 1.5, 0], [8, 3], is_covered=True, name="Coil_3")
        >>> coil4 = m2d.modeler.create_rectangle([32, 1.5, 0], [8, 3], is_covered=True, name="Coil_4")
        >>> current1 = m2d.assign_current("Coil_1", amplitude=1, swap_direction=False, name="Current1")
        >>> current2 = m2d.assign_current("Coil_2", amplitude=1, swap_direction=True, name="Current2")
        >>> current3 = m2d.assign_current("Coil_3", amplitude=1, swap_direction=True, name="Current3")
        >>> current4 = m2d.assign_current("Coil_4", amplitude=1, swap_direction=True, name="Current4")
        >>> group_sources = {"Group1_Test": ["Current1", "Current3"], "Group2_Test": ["Current2", "Current4"]}
        >>> selection = ['Current1', 'Current2', 'Current3', 'Current4']
        >>> turns = [5, 1, 2, 3]
        >>> L = m2d.assign_matrix(sources=selection, matrix_name="Test2", turns=turns, group_sources=group_sources)
        """
        sources = self.modeler.convert_to_selections(sources, True)
        if self.solution_type in ["Electrostatic", "ACConduction", "DCConduction"]:
            turns = ["1"] * len(sources)
            branches = None
            if self.design_type == "Maxwell 2D":
                if group_sources:
                    if isinstance(group_sources, dict):
                        first_key = next(iter(group_sources))
                        group_sources = group_sources[first_key]
                        self.logger.warning("First Ground is selected")
                    group_sources = self.modeler.convert_to_selections(group_sources, True)
                    if any(item in group_sources for item in sources):
                        self.logger.error("Ground must be different than selected sources")
                        return False
            else:
                group_sources = None

        elif self.solution_type in ["EddyCurrent", "Magnetostatic"]:
            if self.solution_type == "Magnetostatic":
                if group_sources:
                    if isinstance(group_sources, (dict, OrderedDict)):
                        new_group = group_sources.copy()
                        for element in new_group:
                            if not all(item in sources for item in group_sources[element]):
                                self.logger.warning("Sources in group " + element + " are not selected")
                                group_sources.pop(element)
                        if not branches or len(group_sources) != len(
                            self.modeler.convert_to_selections(branches, True)
                        ):
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
            else:
                group_sources = None
                branches = None
                turns = ["1"] * len(sources)
                self.logger.info("Infinite is the only return path option in EddyCurrent.")
                return_path = ["infinite"] * len(sources)

        if self.solution_type not in ["Transient", "ElectricTransient"]:
            if not matrix_name:
                matrix_name = generate_unique_name("Matrix")
            if not turns or len(sources) != len(self.modeler.convert_to_selections(turns, True)):
                if turns:
                    turns = self.modeler.convert_to_selections(turns, True)
                    num = abs(len(sources) - len(self.modeler.convert_to_selections(turns, True)))
                    if len(sources) < len(self.modeler.convert_to_selections(turns, True)):
                        turns = turns[:-num]
                    else:
                        new_element = [turns[0]] * num
                        turns.extend(new_element)
                else:
                    turns = ["1"] * len(sources)
            else:
                turns = self.modeler.convert_to_selections(turns, True)
            if not return_path or len(sources) != len(self.modeler.convert_to_selections(return_path, True)):
                return_path = ["infinite"] * len(sources)
            else:
                return_path = self.modeler.convert_to_selections(return_path, True)
            if any(item in return_path for item in sources):
                self.logger.error("Return path specified must not be included in sources")
                return False

            if group_sources and self.solution_type in ["EddyCurrent", "Magnetostatic"]:
                props = OrderedDict(
                    {"MatrixEntry": OrderedDict({"MatrixEntry": []}), "MatrixGroup": OrderedDict({"MatrixGroup": []})}
                )
            else:
                props = OrderedDict({"MatrixEntry": OrderedDict({"MatrixEntry": []}), "MatrixGroup": []})

            for element in range(len(sources)):
                if self.solution_type == "Magnetostatic" and self.design_type == "Maxwell 2D":
                    prop = OrderedDict(
                        {
                            "Source": sources[element],
                            "NumberOfTurns": turns[element],
                            "ReturnPath": return_path[element],
                        }
                    )
                elif self.solution_type == "EddyCurrent":
                    prop = OrderedDict({"Source": sources[element], "ReturnPath": return_path[element]})
                else:
                    prop = OrderedDict({"Source": sources[element], "NumberOfTurns": turns[element]})
                props["MatrixEntry"]["MatrixEntry"].append(prop)

            if group_sources:
                if self.solution_type in ["Electrostatic", "ACConduction", "DCConduction"]:
                    source_list = ",".join(group_sources)
                    props["GroundSources"] = source_list
                else:
                    cont = 0
                    for element in group_sources:
                        source_list = ",".join(group_sources[element])
                        # GroundSources
                        prop = OrderedDict(
                            {"GroupName": element, "NumberOfBranches": branches[cont], "Sources": source_list}
                        )
                        props["MatrixGroup"]["MatrixGroup"].append(prop)
                        cont += 1

            bound = MaxwellParameters(self, matrix_name, props, "Matrix")
            if bound.create():
                self.boundaries.append(bound)
                return bound
        else:
            self.logger.error("Solution type does not have matrix parameters")
            return False

    @pyaedt_function_handler()
    def setup_ctrlprog(
        self, setupname, file_str=None, keep_modifications=False, python_interpreter=None, aedt_lib_dir=None
    ):
        """Configure the transient design setup to run a specific control program.

        Parameters
        ----------
        setupname : str
            Name of the setup.
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

        self._py_file = setupname + ".py"
        ctl_path = self.working_directory
        ctl_file_compute = os.path.join(ctl_path, self._py_file)
        ctl_file = os.path.join(self.working_directory, self._py_file)

        if aedt_lib_dir:
            source_dir = aedt_lib_dir
        else:
            source_dir = self.pyaedt_dir

        if os.path.exists(ctl_file) and keep_modifications:
            with open(ctl_file, "r") as fi:
                existing_data = fi.readlines()
            with open(ctl_file, "w") as fo:
                first_line = True
                for line in existing_data:
                    if first_line:
                        first_line = False
                        if python_interpreter:
                            fo.write("#!{0}\n".format(python_interpreter))
                    if line.startswith("work_dir"):
                        fo.write("work_dir = r'{0}'\n".format(ctl_path))
                    elif line.startswith("lib_dir"):
                        fo.write("lib_dir = r'{0}'\n".format(source_dir))
                    else:
                        fo.write(line)
        else:
            if file_str is not None:
                with io.open(ctl_file, "w", newline="\n") as fo:
                    fo.write(file_str)
                assert os.path.exists(ctl_file), "Control program file could not be created."

        self.oanalysis.EditSetup(
            setupname,
            [
                "NAME:" + setupname,
                "Enabled:=",
                True,
                "UseControlProgram:=",
                True,
                "ControlProgramName:=",
                ctl_file_compute,
                "ControlProgramArg:=",
                "",
                "CallCtrlProgAfterLastStep:=",
                True,
            ],
        )

        return True

    # Set eddy effects
    @pyaedt_function_handler()
    def eddy_effects_on(self, object_list, activate_eddy_effects=True, activate_displacement_current=True):
        """Assign eddy effects on objects.

        Parameters
        ----------
        object_list : list
            List of objects.
        activate_eddy_effects : bool, optional
            Whether to activate eddy effects. The default is ``True``.
        activate_displacement_current : bool, optional
            Whether to activate the displacement current. The default is ``True``.

        Returns
        -------
        bool
            ``True`` when successful and ``False`` when failed.

        References
        ----------

        >>> oModule.SetEddyEffect
        """
        solid_objects_names = self.get_all_conductors_names()

        EddyVector = ["NAME:EddyEffectVector"]
        if self.modeler._is3d:
            if not activate_eddy_effects:
                activate_displacement_current = False
            for obj in solid_objects_names:
                if self.solution_type == "EddyCurrent":
                    if obj in object_list:
                        EddyVector.append(
                            [
                                "NAME:Data",
                                "Object Name:=",
                                obj,
                                "Eddy Effect:=",
                                activate_eddy_effects,
                                "Displacement Current:=",
                                activate_displacement_current,
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
                if self.solution_type == "Transient":
                    if obj in object_list:
                        EddyVector.append(
                            [
                                "NAME:Data",
                                "Object Name:=",
                                obj,
                                "Eddy Effect:=",
                                activate_eddy_effects,
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
                if obj in object_list:
                    EddyVector.append(
                        [
                            "NAME:Data",
                            "Object Name:=",
                            obj,
                            "Eddy Effect:=",
                            activate_eddy_effects,
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

    @pyaedt_function_handler()
    def setup_y_connection(self, windings_name=None):
        """Setup the Y connection.

        Parameters
        ----------
        winding_name : list, optional
            List of windings. For example, ``["PhaseA", "PhaseB", "PhaseC"]``.
            The default value is ``None``, in which case the design has no Y connection.

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

        >>> from pyaedt import Maxwell2d
        >>> aedtapp = Maxwell2d("Motor_EM_R2019R3.aedt")
        >>> aedtapp.set_active_design("Basis_Model_For_Test")
        >>> aedtapp.setup_y_connection(["PhaseA", "PhaseB", "PhaseC"])
        """

        if windings_name:
            connection = ["NAME:YConnection"]
            connection.append("Windings:=")
            connection.append(",".join(windings_name))
            windings = ["NAME:YConnection"]
            windings.append(connection)
            self.oboundary.SetupYConnection(windings)
        else:
            self.oboundary.SetupYConnection()
        return True

    @pyaedt_function_handler()
    def assign_current(self, object_list, amplitude=1, phase="0deg", solid=True, swap_direction=False, name=None):
        """Assign the source of the current.

        Parameters
        ----------
        object_list : list
            List of objects to assign the current source to.
        amplitude : float, optional
            Current amplitude in mA. The default is ``1``.
        phase : str, optional
            The default is ``"0deg"``.
        solid : bool, optional
            The default is ``True``.
        swap_direction : bool, optional
            The default is ``False``.
        name : str, optional
            The default is ``None``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        References
        ----------

        >>> oModule.AssignCurrent
        """

        if isinstance(amplitude, (int, float)):
            amplitude = str(amplitude) + "A"

        if not name:
            name = generate_unique_name("Current")

        object_list = self.modeler.convert_to_selections(object_list, True)
        if self.is3d:
            if type(object_list[0]) is int:
                props = OrderedDict(
                    {
                        "Faces": object_list,
                        "Current": amplitude,
                    }
                )
            else:
                props = OrderedDict(
                    {
                        "Objects": object_list,
                        "Current": amplitude,
                    }
                )
            if self.solution_type not in [
                "Magnetostatic",
                "DCConduction",
                "ElectricTransient",
                "TransientAPhiFormulation",
            ]:
                props["Phase"] = phase
            if self.solution_type not in ["DCConduction", "ElectricTransient"]:
                props["IsSolid"] = solid
            props["Point out of terminal"] = swap_direction
        else:
            if type(object_list[0]) is str:
                props = OrderedDict({"Objects": object_list, "Current": amplitude, "IsPositive": swap_direction})
            else:
                self.logger.warning("Input must be a 2D object.")
                return False
        bound = BoundaryObject(self, name, props, "Current")
        if bound.create():
            self.boundaries.append(bound)
            return bound
        return False

    @pyaedt_function_handler()
    def assign_translate_motion(
        self,
        band_object,
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

        Parameters
        ----------
        band_object : str
            Object container.
        coordinate_system : str, optional
            Coordinate system name. The default is ``"Global"``.
        axis : str or int, optional
            Coordinate system axis. The default is ``"Z"``.
            It can be a ``pyaedt.generic.constants.AXIS`` enumerator value.
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
            Movement velocity. The default is ``0``. If a float value
            is used, "m_per_sec" units are applied.
        mechanical_transient : bool, optional
            Whether to consider the mechanical movement. The default is ``False``.
        mass : float or str, optional
            Mechanical mass. The default is ``1``. If a float value is used, "Kg" units
            are applied.
        damping : float, optional
            Damping factor. The default is ``0``.
        load_force : float or str, optional
            Load force. The default is ``0``. If a float value is used, "newton"
            units are applied.
        motion_name : str, optional
            Motion name. The default is ``None``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        References
        ----------

        >>> oModule.AssignBand
        """
        assert self.solution_type == SOLUTIONS.Maxwell3d.Transient, "Motion applies only to the Transient setup."
        if not motion_name:
            motion_name = generate_unique_name("Motion")
        object_list = self.modeler.convert_to_selections(band_object, True)
        props = OrderedDict(
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
        bound = BoundaryObject(self, motion_name, props, "Band")
        if bound.create():
            self.boundaries.append(bound)
            return bound
        return False

    @pyaedt_function_handler()
    def assign_rotate_motion(
        self,
        band_object,
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

        Parameters
        ----------
        band_object : str,
            Object container.
        coordinate_system : str, optional
            Coordinate system name. The default is ``"Global"``.
        axis : str or int, optional
            Coordinate system axis. The default is ``"Z"``.
            It can be a ``pyaedt.generic.constants.AXIS`` enumerator value.
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
            Load force. The default is ``"0newton"``. If a float value is used,
            "NewtonMeter" units are applied.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        References
        ----------

        >>> oModule.AssignBand
        """
        assert self.solution_type == SOLUTIONS.Maxwell3d.Transient, "Motion applies only to the Transient setup."
        names = list(self.omodelsetup.GetMotionSetupNames())
        motion_name = "MotionSetup" + str(len(names) + 1)
        object_list = self.modeler.convert_to_selections(band_object, True)
        props = OrderedDict(
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
        bound = BoundaryObject(self, motion_name, props, "Band")
        if bound.create():
            self.boundaries.append(bound)
            return bound
        return False

    @pyaedt_function_handler()
    def assign_voltage(self, face_list, amplitude=1, name=None):
        """Assign a voltage source to a list of faces in Maxwell 3D or a list of Objects in Maxwell 2D.

        Parameters
        ----------
        face_list : list
            List of faces or objects to assign a voltage source to.
        amplitude : float, optional
            Voltage amplitude in mV. The default is ``1``.
        name : str, optional
            Name of the boundary. The default is ``None``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        References
        ----------

        >>> oModule.AssignVoltage
        """
        if isinstance(amplitude, (int, float)):
            amplitude = str(amplitude) + "mV"

        if not name:
            name = generate_unique_name("Voltage")
        face_list = self.modeler.convert_to_selections(face_list, True)

        # if type(face_list) is not list and type(face_list) is not tuple:
        #     face_list = [face_list]
        if self.design_type == "Maxwell 2D":
            props = OrderedDict({"Objects": face_list, "Value": amplitude})
        else:
            props = OrderedDict({"Faces": face_list, "Voltage": amplitude})
        bound = BoundaryObject(self, name, props, "Voltage")
        if bound.create():
            self.boundaries.append(bound)
            return bound
        return False

    @pyaedt_function_handler()
    def assign_voltage_drop(self, face_list, amplitude=1, swap_direction=False, name=None):
        """Assign a voltage drop to a list of faces.

        Parameters
        ----------
        face_list : list
            List of faces to assign a voltage drop to.
        amplitude : float, optional
            Voltage amplitude in mV. The default is ``1``.
        swap_direction : bool, optional
            Whether to swap the direction. The default value is ``False``.
        name : str, optional
            Name of the boundary. The default is ``None``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        References
        ----------

        >>> oModule.AssignVoltageDrop
        """
        if isinstance(amplitude, (int, float)):
            amplitude = str(amplitude) + "mV"

        if not name:
            name = generate_unique_name("VoltageDrop")
        face_list = self.modeler.convert_to_selections(face_list, True)

        props = OrderedDict({"Faces": face_list, "Voltage Drop": amplitude, "Point out of terminal": swap_direction})
        bound = BoundaryObject(self, name, props, "VoltageDrop")
        if bound.create():
            self.boundaries.append(bound)
            return bound
        return False

    @pyaedt_function_handler()
    def assign_winding(
        self,
        coil_terminals=None,
        winding_type="Current",
        is_solid=True,
        current_value=1,
        res=0,
        ind=0,
        voltage=0,
        parallel_branches=1,
        name=None,
    ):
        """Assign a winding to a Maxwell design.

        Parameters
        ----------
        coil_terminals : list, optional
            List of faces to create the coil terminal on.
            The default is ``None``.
        winding_type : str, optional
            Type of the winding. Options are ``"Current"``, ``"Voltage"``,
            and ``"External"``. The default is ``"Current"``.
        is_solid : bool, optional
            Whether the winding is the solid type. The default is ``True``. If ``False``,
            the winding is the stranded type.
        current_value : float, optional
            Value of the current in amperes. The default is ``1``.
        res : float, optional
            Resistance in ohms. The default is ``0``.
        ind : float, optional
            Henry (H). The default is ``0``.
        voltage : float, optional
            Voltage value. The default is ``0``.
        parallel_branches : int, optional
            Number of parallel branches. The default is ``1``.
        name : str, optional
            Name of the boundary. The default is ``None``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Bounding object for the winding, otherwise only the bounding object.

        References
        ----------

        >>> oModule.AssignWindingGroup
        """

        if not name:
            name = generate_unique_name("Winding")

        props = OrderedDict(
            {
                "Type": winding_type,
                "IsSolid": is_solid,
                "Current": self.modeler._arg_with_dim(current_value, "A"),
                "Resistance": self.modeler._arg_with_dim(res, "ohm"),
                "Inductance": self.modeler._arg_with_dim(ind, "H"),
                "Voltage": self.modeler._arg_with_dim(voltage, "V"),
                "ParallelBranchesNum": str(parallel_branches),
            }
        )
        bound = BoundaryObject(self, name, props, "Winding")
        if bound.create():
            self.boundaries.append(bound)
            if coil_terminals is None:
                coil_terminals = []
            if type(coil_terminals) is not list:
                coil_terminals = [coil_terminals]
            coil_names = []
            for coil in coil_terminals:
                c = self.assign_coil(coil)
                if c:
                    coil_names.append(c.name)

            if coil_names:
                self.add_winding_coils(bound.name, coil_names)
            return bound
        return False

    @pyaedt_function_handler()
    def add_winding_coils(self, windingname, coil_names):
        """Add coils to the winding.

        Parameters
        ----------
        windingname : str
            Name of the winding.
        coil_names : list
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
            self.oboundary.AddWindingTerminals(windingname, coil_names)
        else:
            self.oboundary.AddWindingCoils(windingname, coil_names)
        return True

    @pyaedt_function_handler()
    def assign_coil(self, input_object, conductor_number=1, polarity="Positive", name=None):
        """Assign coils to a list of objects or face IDs.

        Parameters
        ----------
        input_object : list
            List of objects or face IDs.
        conductor_number : int, optional
            Number of conductors. The default is ``1``.
        polarity : str, optional
            Type of the polarity. The default is ``"Positive"``.
        name : str, optional
            The default is ``None``.

        Returns
        -------
        CoilObject
            Coil object.

        References
        ----------

        >>> oModule.AssignCoil
        """
        if polarity.lower() == "positive":
            point = False
        else:
            point = True

        input_object = self.modeler.convert_to_selections(input_object, True)

        if not name:
            name = generate_unique_name("Coil")

        if type(input_object[0]) is str:
            if self.modeler._is3d:
                props2 = OrderedDict(
                    {"Objects": input_object, "Conductor number": str(conductor_number), "Point out of terminal": point}
                )
                bound = BoundaryObject(self, name, props2, "CoilTerminal")
            else:
                props2 = OrderedDict(
                    {
                        "Objects": input_object,
                        "Conductor number": str(conductor_number),
                        "PolarityType": polarity.lower(),
                    }
                )
                bound = BoundaryObject(self, name, props2, "Coil")
        else:
            if self.modeler._is3d:
                props2 = OrderedDict(
                    {"Faces": input_object, "Conductor number": str(conductor_number), "Point out of terminal": point}
                )
                bound = BoundaryObject(self, name, props2, "CoilTerminal")

            else:
                self.logger.warning("Face Selection is not allowed in Maxwell 2D. Provide a 2D object.")
                return False
        if bound.create():
            self.boundaries.append(bound)
            return bound
        return False

    @pyaedt_function_handler()
    def assign_force(self, input_object, reference_cs="Global", is_virtual=True, force_name=None):
        """Assign a force to one or more objects.

        Parameters
        ----------
        input_object : str, list
            One or more objects to assign the force to.
        reference_cs : str, optional
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
        """
        if self.solution_type not in ["ACConduction", "DCConduction"]:
            input_object = self.modeler.convert_to_selections(input_object, True)
            if not force_name:
                force_name = generate_unique_name("Force")
            if self.design_type == "Maxwell 3D":
                prop = OrderedDict(
                    {
                        "Name": force_name,
                        "Reference CS": reference_cs,
                        "Is Virtual": is_virtual,
                        "Objects": input_object,
                    }
                )
            else:
                prop = OrderedDict(
                    {
                        "Name": force_name,
                        "Reference CS": reference_cs,
                        "Objects": input_object,
                    }
                )

            bound = MaxwellParameters(self, force_name, prop, "Force")
            if bound.create():
                self.boundaries.append(bound)
                return bound
        else:
            self.logger.error("Solution Type has not Matrix Parameter")
            return False

    @pyaedt_function_handler()
    def assign_torque(
        self, input_object, reference_cs="Global", is_positive=True, is_virtual=True, axis="Z", torque_name=None
    ):
        """Assign a torque to one or more objects.

        Parameters
        ----------
        input_object : str or list
           One or more objects to assign the torque to.
        reference_cs : str, optional
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
        if self.solution_type not in ["ACConduction", "DCConduction"]:
            if self.solution_type == "Transient":
                is_virtual = True
            input_object = self.modeler.convert_to_selections(input_object, True)
            if not torque_name:
                torque_name = generate_unique_name("Torque")
            if self.design_type == "Maxwell 3D":
                prop = OrderedDict(
                    {
                        "Name": torque_name,
                        "Is Virtual": is_virtual,
                        "Coordinate System": reference_cs,
                        "Axis": axis,
                        "Is Positive": is_positive,
                        "Objects": input_object,
                    }
                )
            else:
                prop = OrderedDict(
                    {
                        "Name": torque_name,
                        "Coordinate System": reference_cs,
                        "Is Positive": is_positive,
                        "Objects": input_object,
                    }
                )

            bound = MaxwellParameters(self, torque_name, prop, "Torque")
            if bound.create():
                self.boundaries.append(bound)
                return bound
        else:
            self.logger.error("Solution Type has not Matrix Parameter")
            return False

    @pyaedt_function_handler()
    def solve_inside(self, name, activate=True):
        """Solve inside.

        Parameters
        ----------
        name : str

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
        """Analyze from zero.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oModule.ResetSetupToTimeZero
        """
        self.oanalysis.ResetSetupToTimeZero(self._setup)
        self.analyze_nominal()
        return True

    @pyaedt_function_handler()
    def set_initial_angle(self, motion_setup, val):
        """Set the initial angle.

        Parameters
        ----------
        motion_setup : str
            Name of the motion setup.
        val : float
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
                    ["NAME:ChangedProps", ["NAME:Initial Position", "Value:=", val]],
                ],
            ]
        )
        return True

    @pyaedt_function_handler()
    def assign_symmetry(self, entity_list, symmetry_name=None, is_odd=True):
        """Assign symmetry boundary.

        Parameters
        ----------
        entity_list : list
            List IDs or :class:`pyaedt.modeler.Object3d.EdgePrimitive` or
            :class:`pyaedt.modeler.Object3d.FacePrimitive`.
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
        try:
            if symmetry_name is None:
                symmetry_name = generate_unique_name("Symmetry")

            if entity_list:
                if self.design_type == "Maxwell 2D":
                    entity_list = self.modeler.convert_to_selections(entity_list, True)
                    prop = OrderedDict({"Name": symmetry_name, "Edges": entity_list, "IsOdd": is_odd})
                else:
                    entity_list = self.modeler.convert_to_selections(entity_list, True)
                    prop = OrderedDict({"Name": symmetry_name, "Faces": entity_list, "IsOdd": is_odd})
            else:
                msg = "At least one edge must be provided."
                ValueError(msg)

            bound = BoundaryObject(self, symmetry_name, prop, "Symmetry")
            if bound.create():
                self.boundaries.append(bound)
                return bound
            return True
        except:
            return False

    @pyaedt_function_handler()
    def assign_current_density(
        self,
        entities,
        current_density_name=None,
        phase="0deg",
        current_density_x="0",
        current_density_y="0",
        current_density_z="0",
        current_density_2d="0",
        coordinate_system_name="Global",
        coordinate_system_cartesian="Cartesian",
    ):
        """Assign current density to a single or list of entities.

        Parameters
        ----------
        entities : list
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
        coordinate_system_name : str, optional
            Coordinate system name.
            Default value is 'Global'.
        coordinate_system_cartesian : str, optional
            Coordinate system cartesian.
            Possible values can be ``"Cartesian"``, ``"Cylindrical"``, and ``"Spherical"``.
            Default value is ``"Cartesian"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if self.solution_type in ["EddyCurrent", "Magnetostatic"]:
            if current_density_name is None:
                current_density_name = generate_unique_name("CurrentDensity")
            if re.compile(r"(\d+)\s*(\w+)").match(phase).groups()[1] not in ["deg", "degmin", "degsec", "rad"]:
                self.logger.error("Invalid phase unit.")
                return False
            if coordinate_system_cartesian not in ["Cartesian", "Cylindrical", "Spherical"]:
                self.logger.error("Invalid coordinate system.")
                return False

            objects_list = self.modeler.convert_to_selections(entities, True)

            try:
                if self.modeler._is3d:
                    if len(objects_list) > 1:
                        current_density_group_names = []
                        for x in range(0, len(objects_list)):
                            current_density_group_names.append(current_density_name + "_{}".format(str(x + 1)))
                        props = OrderedDict({})
                        props["items"] = current_density_group_names
                        props[current_density_group_names[0]] = OrderedDict(
                            {
                                "Objects": objects_list,
                                "Phase": phase,
                                "CurrentDensityX": current_density_x,
                                "CurrentDensityY": current_density_y,
                                "CurrentDensityZ": current_density_z,
                                "CoordinateSystem Name": coordinate_system_name,
                                "CoordinateSystem Type": coordinate_system_cartesian,
                            }
                        )
                        bound = BoundaryObject(self, current_density_group_names[0], props, "CurrentDensityGroup")
                    else:
                        props = OrderedDict(
                            {
                                "Objects": objects_list,
                                "Phase": phase,
                                "CurrentDensityX": current_density_x,
                                "CurrentDensityY": current_density_y,
                                "CurrentDensityZ": current_density_z,
                                "CoordinateSystem Name": coordinate_system_name,
                                "CoordinateSystem Type": coordinate_system_cartesian,
                            }
                        )
                        bound = BoundaryObject(self, current_density_name, props, "CurrentDensity")
                else:
                    if len(objects_list) > 1:
                        current_density_group_names = []
                        for x in range(0, len(objects_list)):
                            current_density_group_names.append(current_density_name + "_{}".format(str(x + 1)))
                        props = OrderedDict({})
                        props["items"] = current_density_group_names
                        props[current_density_group_names[0]] = OrderedDict(
                            {
                                "Objects": objects_list,
                                "Phase": phase,
                                "Value": current_density_2d,
                                "CoordinateSystem": "",
                            }
                        )
                        bound = BoundaryObject(self, current_density_group_names[0], props, "CurrentDensityGroup")
                    else:
                        props = OrderedDict(
                            {
                                "Objects": objects_list,
                                "Phase": phase,
                                "Value": current_density_2d,
                                "CoordinateSystem": "",
                            }
                        )
                        bound = BoundaryObject(self, current_density_name, props, "CurrentDensity")

                if bound.create():
                    self.boundaries.append(bound)
                    return bound
                return True
            except:
                self.logger.error("Couldn't assign current density to desired list of objects.")
                return False
        else:
            self.logger.error("Current density can only be applied to Eddy current or magnetostatic solution types.")
            return False

    @pyaedt_function_handler()
    def enable_harmonic_force(
        self,
        objects,
        force_type=0,
        window_function="Rectangular",
        use_number_of_last_cycles=True,
        last_cycles_number=1,
        calculate_force="Harmonic",
    ):
        """Set the Harmonic Force for Transient Analysis.

        Parameters
        ----------
        objects : list
            Object list to enable force computation.
        force_type : int, optional
            Force Type. `0` for Objects, `1` for Surface, `2` for volumetric.
        window_function : str, optional
            Windowing function. Default is `"Rectangular"`.
        use_number_of_last_cycles : bool, optional
            Either to use or not the last cycle. Default is `True`.
        last_cycles_number : int, optional
            Defines the number of cycles to compute if `use_number_of_last_cycle` is `True`.
        calculate_force : sr, optional
            Either `"Harmonic"` or `"Transient"`. Default is `"Harmonic"`.

        Returns
        -------

        """
        if self.solution_type != "Transient":
            self.logger.error("This methods work only with Maxwell Transient Analysis.")
            return False
        objects = self.modeler.convert_to_selections(objects, True)
        self.odesign.EnableHarmonicForceCalculation(
            [
                "EnabledObjects:=",
                objects,
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

    @pyaedt_function_handler()
    def export_element_based_harmonic_force(
        self,
        output_directory=None,
        setup_name=None,
        start_frequency=None,
        stop_frequency=None,
        number_of_frequency=None,
    ):
        """Export Element Based Harmonic Forces csv to file.

        Parameters
        ----------
        output_directory : str, optional
            Path to export. If ``None`` pyaedt working dir will be used.
        setup_name : str, optional
            Setup name. If ``None`` pyaedt will use nominal setup.
        start_frequency : float, optional
            When a float is entered the Start-Stop Frequency approach is used.
        stop_frequency : float, optional
            A float must be entered when the Start-Stop Frequency approach is used.
        number_of_frequency : int, optional
            When a number is entered, the number of frequencies approach is used.

        Returns
        -------
        str
            Path to the export directory.
        """
        if self.solution_type != "Transient":
            self.logger.error("This methods work only with Maxwell Transient Analysis.")
            return False
        if not output_directory:
            output_directory = self.working_directory
        if not setup_name:
            setup_name = self.setups[0].name
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
        self.odesign.ExportElementBasedHarmonicForce(output_directory, setup_name, freq_option, f1, f2)
        return output_directory

    @pyaedt_function_handler()
    def heal_objects(
        self,
        input_objects_list,
        auto_heal=True,
        tolerant_stitch=True,
        simplify_geometry=True,
        tighten_gaps=True,
        heal_to_solid=False,
        stop_after_first_stitch_error=False,
        max_stitch_tolerance=0.001,
        explode_and_stitch=True,
        geometry_simplification_tolerance=1,
        maximum_generated_radius=1,
        simplify_type=0,
        tighten_gaps_width=0.00001,
        remove_silver_faces=True,
        remove_small_edges=True,
        remove_small_faces=True,
        silver_face_tolerance=1,
        small_edge_tolerance=1,
        small_face_area_tolerance=1,
        bounding_box_scale_factor=0,
        remove_holes=True,
        remove_chamfers=True,
        remove_blends=True,
        hole_radius_tolerance=1,
        chamfer_width_tolerance=1,
        blend_radius_tolerance=1,
        allowable_surface_area_change=5,
        allowable_volume_change=5,
    ):
        """Analyze healing objects options.

        Parameters
        ----------
        input_objects_list : str
            List of object names to analyze.
        auto_heal : bool, optional
            Auto heal option. Default value is ``True``.
        tolerant_stitch : bool, optional
            Tolerant stitch for manual healing. Default value is ``True``.
        simplify_geometry : bool, optional
            Simplify geometry for manual healing. Default value is ``True``.
        tighten_gaps : bool, optional
            Tighten gaps for manual healing. Default value is ``True``.
        heal_to_solid : bool, optional
            Heal to solid for manual healing. Default value is ``False``.
        stop_after_first_stitch_error : bool, optional
            Stop after first stitch error for manual healing. Default value is ``False``.
        max_stitch_tolerance : float, str, optional
            Max stitch tolerance for manual healing. Default value is ``0.001``.
        explode_and_stitch : bool, optional
            Explode and stitch for manual healing. Default value is ``True``.
        geometry_simplification_tolerance : float, str, optional
            Geometry simplification tolerance for manual healing in mm. Default value is ``1``.
        maximum_generated_radius : float, str, optional
            Maximum generated radius for manual healing in mm. Default value is ``1``.
        simplify_type : int, optional
            Simplify type for manual healing. Default value is ``0`` which refers to ``Curves``.
            Other available values are ``1`` for ``Surfaces`` and ``2`` for ``Both``.
        tighten_gaps_width : float, str, optional
            Tighten gaps width for manual healing in mm. Default value is ``0.00001``.
        remove_silver_faces : bool, optional
            Remove silver faces for manual healing. Default value is ``True``.
        remove_small_edges : bool, optional
            Remove small edges faces for manual healing. Default value is ``True``.
        remove_small_faces : bool, optional
            Remove small faces for manual healing. Default value is ``True``.
        silver_face_tolerance : float, str, optional
            Silver face tolerance for manual healing in mm. Default value is ``1``.
        small_edge_tolerance : float, str, optional
            Silver face tolerance for manual healing in mm. Default value is ``1``.
        small_face_area_tolerance : float, str, optional
            Silver face tolerance for manual healing in mm^2. Default value is ``1``.
        bounding_box_scale_factor : int, optional
            Bounding box scaling factor for manual healing. Default value is ``0``.
        remove_holes : bool, optional
            Remove holes for manual healing. Default value is ``True``.
        remove_chamfers : bool, optional
            Remove chamfers for manual healing. Default value is ``True``.
        remove_blends : bool, optional
            Remove blends for manual healing. Default value is ``True``.
        hole_radius_tolerance : float, str, optional
            Hole radius tolerance for manual healing in mm. Default value is ``1``.
        chamfer_width_tolerance : float, str, optional
            Chamfer width tolerance for manual healing in mm. Default value is ``1``.
        blend_radius_tolerance : float, str, optional
            Blend radius tolerance for manual healing in mm. Default value is ``1``.
        allowable_surface_area_change : float, str, optional
            Allowable surface area for manual healing in mm. Default value is ``1``.
        allowable_volume_change : float, str, optional
            Allowable volume change for manual healing in mm. Default value is ``1``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if not input_objects_list:
            self.logger.error("Provide an object name or a list of object names as a string.")
            return False
        elif not isinstance(input_objects_list, str):
            self.logger.error("Provide an object name or a list of object names as a string.")
            return False
        elif "," in input_objects_list:
            input_objects_list = input_objects_list.strip()
            if ", " in input_objects_list:
                input_objects_list_split = input_objects_list.split(", ")
            else:
                input_objects_list_split = input_objects_list.split(",")
            for obj in input_objects_list_split:
                if obj not in self.modeler.object_names:
                    self.logger.error("Provide an object name or a list of object names that exists in current design.")
                    return False
            objects_selection = ",".join(input_objects_list_split)
        else:
            objects_selection = input_objects_list

        if simplify_type not in [0, 1, 2]:
            self.logger.error("Invalid simplify type.")
            return False

        selections_args = ["NAME:Selections", "Selections:=", objects_selection, "NewPartsModelFlag:=", "Model"]
        healing_parameters = [
            "NAME:ObjectHealingParameters",
            "Version:=",
            1,
            "AutoHeal:=",
            auto_heal,
            "TolerantStitch:=",
            tolerant_stitch,
            "SimplifyGeom:=",
            simplify_geometry,
            "TightenGaps:=",
            tighten_gaps,
            "HealToSolid:=",
            heal_to_solid,
            "StopAfterFirstStitchError:=",
            stop_after_first_stitch_error,
            "MaxStitchTol:=",
            max_stitch_tolerance,
            "ExplodeAndStitch:=",
            explode_and_stitch,
            "GeomSimplificationTol:=",
            geometry_simplification_tolerance,
            "MaximumGeneratedRadiusForSimplification:=",
            maximum_generated_radius,
            "SimplifyType:=",
            simplify_type,
            "TightenGapsWidth:=",
            tighten_gaps_width,
            "RemoveSliverFaces:=",
            remove_silver_faces,
            "RemoveSmallEdges:=",
            remove_small_edges,
            "RemoveSmallFaces:=",
            remove_small_faces,
            "SliverFaceTol:=",
            silver_face_tolerance,
            "SmallEdgeTol:=",
            small_edge_tolerance,
            "SmallFaceAreaTol:=",
            small_face_area_tolerance,
            "SpikeTol:=",
            -1,
            "GashWidthBound:=",
            -1,
            "GashAspectBound:=",
            -1,
            "BoundingBoxScaleFactor:=",
            bounding_box_scale_factor,
            "RemoveHoles:=",
            remove_holes,
            "RemoveChamfers:=",
            remove_chamfers,
            "RemoveBlends:=",
            remove_blends,
            "HoleRadiusTol:=",
            hole_radius_tolerance,
            "ChamferWidthTol:=",
            chamfer_width_tolerance,
            "BlendRadiusTol:=",
            blend_radius_tolerance,
            "AllowableSurfaceAreaChange:=",
            allowable_surface_area_change,
            "AllowableVolumeChange:=",
            allowable_volume_change,
        ]
        try:
            self.oeditor.HealObject(selections_args, healing_parameters)
            return True
        except:
            self.logger.error("Heal objects failed.")
            return False

    @pyaedt_function_handler()
    def simplify_objects(
        self,
        input_objects_list,
        simplify_type="Polygon Fit",
        extrusion_axis="Auto",
        clean_up=True,
        allow_splitting=True,
        separate_bodies=True,
        clone_body=True,
        generate_primitive_history=False,
        interior_points_on_arc=5,
        length_threshold_percentage=25,
        create_group_for_new_objects=False,
    ):
        """Analyze healing objects options.

        Parameters
        ----------
        input_objects_list : str
            List of object names to simplify.
        simplify_type : str, optional
            Simplify type. Default value is ``Polygon Fit``.
            Available values are ``Polygon Fit`` ``Primitive Fit`` or ``Bounding Box``.
        extrusion_axis : str, optional
            Extrusion axis. Default value is ``Auto``.
            Available values are ``Auto`` ``X``, ``Y`` or ``Z``.
        clean_up : bool, optional
            Clean up. Default value is ``True``.
        allow_splitting : bool, optional
            Allow splitting. Default value is ``True``.
        separate_bodies : bool, optional
            Separate bodies. Default value is ``True``.
        clone_body : bool, optional
            Clone body. Default value is ``True``.
        generate_primitive_history : bool, optional
            Generate primitive history.
            This option will purge the history for selected objects.
            Default value is ``False``.
        interior_points_on_arc : float, optional
            Number points on curve. Default value is ``5``.
        length_threshold_percentage : float, optional
            Number points on curve. Default value is ``25``.
        create_group_for_new_objects : bool, optional
            Create group for new objects. Default value is ``False``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if not input_objects_list:
            self.logger.error("Provide an object name or a list of object names as a string.")
            return False
        elif not isinstance(input_objects_list, str):
            self.logger.error("Provide an object name or a list of object names as a string.")
            return False
        elif "," in input_objects_list:
            input_objects_list = input_objects_list.strip()
            if ", " in input_objects_list:
                input_objects_list_split = input_objects_list.split(", ")
            else:
                input_objects_list_split = input_objects_list.split(",")
            for obj in input_objects_list_split:
                if obj not in self.modeler.object_names:
                    self.logger.error("Provide an object name or a list of object names that exists in current design.")
                    return False
            objects_selection = ",".join(input_objects_list_split)
        else:
            objects_selection = input_objects_list

        if simplify_type not in ["Polygon Fit", "Primitive Fit", "Bounding Box"]:
            self.logger.error("Invalid simplify type.")
            return False

        if extrusion_axis not in ["Auto", "X", "Y", "Z"]:
            self.logger.error("Invalid extrusion axis.")
            return False

        selections_args = ["NAME:Selections", "Selections:=", objects_selection, "NewPartsModelFlag:=", "Model"]
        simplify_parameters = [
            "NAME:SimplifyParameters",
            "Type:=",
            simplify_type,
            "ExtrusionAxis:=",
            extrusion_axis,
            "Cleanup:=",
            clean_up,
            "Splitting:=",
            allow_splitting,
            "SeparateBodies:=",
            separate_bodies,
            "CloneBody:=",
            clone_body,
            "Generate Primitive History:=",
            generate_primitive_history,
            "NumberPointsCurve:=",
            interior_points_on_arc,
            "LengthThresholdCurve:=",
            length_threshold_percentage,
        ]
        groups_for_new_object = ["CreateGroupsForNewObjects:=", create_group_for_new_objects]

        try:
            self.oeditor.Simplify(selections_args, simplify_parameters, groups_for_new_object)
            return True
        except:
            self.logger.error("Simplify objects failed.")
            return False


class Maxwell3d(Maxwell, FieldAnalysis3D, object):
    """Provides the Maxwell 3D application interface.

    This class allows you to connect to an existing Maxwell 3D design or create a
    new Maxwell 3D design if one does not exist.

    Parameters
    ----------
    projectname : str, optional
        Name of the project to select or the full path to the project
        or AEDTZ archive to open. The default is ``None``, in which
        case an attempt is made to get an active project. If no
        projects are present, an empty project is created.
    designname : str, optional
        Name of the design to select. The default is ``None``, in
        which case an attempt is made to get an active design. If no
        designs are present, an empty design is created.
    solution_type : str, optional
        Solution type to apply to the design. The default is
        ``None``, in which case the default type is applied.
    setup_name : str, optional
        Name of the setup to use as the nominal. The default is
        ``None``, in which case the active setup is used or
        nothing is used.
    specified_version : str, optional
        Version of AEDT to use. The default is ``None``, in which case
        the active version or latest installed version is used. This
        parameter is ignored when a script is launched within AEDT.
    non_graphical : bool, optional
        Whether to launch AEDT in non-graphical mode. The default
        is ``False``, in which case AEDT is launched in graphical
        mode. This parameter is ignored when a script is launched within
        AEDT.
    new_desktop_session : bool, optional
        Whether to launch an instance of AEDT in a new thread, even if
        another instance of the ``specified_version`` is active on the
        machine. The default is ``True``. This parameter is ignored
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
        ``None``. This parameter is only used when ``new_desktop_session = False``.

    Examples
    --------
    Create an instance of Maxwell 3D and open the specified
    project, which is named ``mymaxwell.aedt``.

    >>> from pyaedt import Maxwell3d
    >>> aedtapp = Maxwell3d("mymaxwell.aedt")
    pyaedt INFO: Added design ...

    Create an instance of Maxwell 3D using the 2021 R1 release and open
    the specified project, which is named ``mymaxwell2.aedt``.

    >>> aedtapp = Maxwell3d(specified_version="2021.2", projectname="mymaxwell2.aedt")
    pyaedt INFO: Added design ...

    """

    @property  # for legacy purposes
    def dim(self):
        """Dimensions."""
        return "3D"

    def __init__(
        self,
        projectname=None,
        designname=None,
        solution_type=None,
        setup_name=None,
        specified_version=None,
        non_graphical=False,
        new_desktop_session=False,
        close_on_exit=False,
        student_version=False,
        machine="",
        port=0,
        aedt_process_id=None,
    ):
        """
        Initialize the ``Maxwell`` class.
        """
        self.is3d = True
        FieldAnalysis3D.__init__(
            self,
            "Maxwell 3D",
            projectname,
            designname,
            solution_type,
            setup_name,
            specified_version,
            non_graphical,
            new_desktop_session,
            close_on_exit,
            student_version,
            machine,
            port,
            aedt_process_id,
        )
        Maxwell.__init__(self)

    @pyaedt_function_handler()
    def assign_insulating(self, geometry_selection, insulation_name=None):
        """Create an insulating boundary condition.

        Parameters
        ----------
        geometry_selection : str
            Objects to apply the insulating boundary to.
        insulation_name : str, optional
            Name of the insulation. The default is ``None`` in which case a unique name is chosen.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object if successful, ``False`` otherwise.

        References
        ----------

        >>> oModule.AssignInsulating

        Examples
        --------

        Create a box and assign insulating boundary to it.

        >>> insulated_box = maxwell3d_app.modeler.create_box([50, 0, 50], [294, 294, 19], name="InsulatedBox")
        >>> insulating_assignment = maxwell3d_app.assign_insulating(insulated_box, "InsulatingExample")
        >>> type(insulating_assignment)
        <class 'pyaedt.modules.Boundary.BoundaryObject'>

        """

        if self.solution_type in [
            "EddyCurrent",
            "Transient",
            "TransientAPhiFormulation",
            "DCConduction",
            "ElectroDCConduction",
        ]:

            if not insulation_name:
                insulation_name = generate_unique_name("Insulation")
            elif insulation_name in self.modeler.get_boundaries_name():
                insulation_name = generate_unique_name(insulation_name)

            listobj = self.modeler.convert_to_selections(geometry_selection, True)
            props = {"Objects": listobj}

            return self._create_boundary(insulation_name, props, "Insulating")
        return False

    @pyaedt_function_handler()
    def assign_impedance(
        self,
        geometry_selection,
        material_name=None,
        permeability=0.0,
        conductivity=None,
        non_linear_permeability=False,
        impedance_name=None,
    ):
        """Create an impedance boundary condition.

        Parameters
        ----------
        geometry_selection : str
            Objects to apply the impedance boundary to.
        material_name : str, optional
            If it is different from ``None``, then material properties values will be extracted from
            the named material in the list of materials available. The default value is ``None``.
        permeability : float, optional
            Permeability of the material.The default value is ``0.0``.
        conductivity : float, optional
            Conductivity of the material. The default value is ``None``.
        non_linear_permeability : bool, optional
            If the option ``material_name`` is activated, the permeability can either be linear or not.
            The default value is ``False``.
        impedance_name : str, optional
            Name of the impedance. The default is ``None`` in which case a unique name is chosen.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object if successful, ``False`` otherwise.

        References
        ----------

        >>> oModule.AssignImpedance

        Examples
        --------

        Create a box and assign impedance boundary to it.

        >>> impedance_box = self.aedtapp.modeler.create_box([-50, -50, -50], [294, 294, 19], name="impedance_box")
        >>> impedance_assignment = self.aedtapp.assign_impedance(impedance_box.name, "InsulatingExample")
        >>> type(impedance_assignment)
        <class 'pyaedt.modules.Boundary.BoundaryObject'>

        """

        if self.solution_type in [
            "EddyCurrent",
            "Transient",
        ]:

            if not impedance_name:
                impedance_name = generate_unique_name("Impedance")
            elif impedance_name in self.modeler.get_boundaries_name():
                impedance_name = generate_unique_name(impedance_name)

            listobj = self.modeler.convert_to_selections(geometry_selection, True)
            props = {"Objects": listobj}

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

            return self._create_boundary(impedance_name, props, "Impedance")
        return False

    @pyaedt_function_handler()
    def assign_current_density_terminal(self, entities, current_density_name=None):
        """Assign current density terminal to a single or list of entities.

        Parameters
        ----------
        entities : list
            Objects to assign the current to.
        current_density_name : str, optional
            Current density name.
            If no name is provided a random name is generated.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if self.solution_type in ["EddyCurrent", "Magnetostatic"]:
            if current_density_name is None:
                current_density_name = generate_unique_name("CurrentDensity")

            objects_list = self.modeler.convert_to_selections(entities, True)

            existing_2d_objects_list = [x.name for x in self.modeler.object_list if not x.is3d]
            if [x for x in objects_list if x not in existing_2d_objects_list]:
                self.logger.error("Entity provided not a planar entity.")
                return False

            try:
                if len(objects_list) > 1:
                    current_density_group_names = []
                    for x in range(0, len(objects_list)):
                        current_density_group_names.append(current_density_name + "_{}".format(str(x + 1)))
                    props = OrderedDict({})
                    props["items"] = current_density_group_names
                    props[current_density_group_names[0]] = OrderedDict({"Objects": objects_list})
                    bound = BoundaryObject(self, current_density_group_names[0], props, "CurrentDensityTerminalGroup")
                else:
                    props = OrderedDict({"Objects": objects_list})
                    bound = BoundaryObject(self, current_density_name, props, "CurrentDensityTerminal")

                if bound.create():
                    self.boundaries.append(bound)
                    return bound
                return True
            except:
                pass
        else:
            self.logger.error("Current density can only be applied to Eddy current or magnetostatic solution types.")
            return False

    @pyaedt_function_handler()
    def _create_boundary(self, name, props, boundary_type):
        """Create a boundary.

        Parameters
        ---------
        name : str
            Name of the boundary.
        props : list
            List of properties for the boundary.
        boundary_type :
            Type of the boundary.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        """

        bound = BoundaryObject(self, name, props, boundary_type)
        result = bound.create()
        if result:
            self.boundaries.append(bound)
            self.logger.info("Boundary %s %s has been correctly created.", boundary_type, name)
            return bound

        self.logger.error("Error in boundary creation for %s %s.", boundary_type, name)
        return result

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
        except:
            return conduction_paths

    @pyaedt_function_handler()
    def assign_master_slave(
        self,
        master_entity,
        slave_entity,
        u_vector_origin_coordinates_master,
        u_vector_pos_coordinates_master,
        u_vector_origin_coordinates_slave,
        u_vector_pos_coordinates_slave,
        reverse_master=False,
        reverse_slave=False,
        same_as_master=True,
        bound_name=None,
    ):
        """Assign master and slave boundary conditions to two faces of the same object.

        Parameters
        ----------
        master_entity : int
            ID of the master entity.
        slave_entity : int
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
        :class:`pyaedt.modules.Boundary.BoundaryObject`, :class:`pyaedt.modules.Boundary.BoundaryObject`
            Master and slave objects.

        References
        ----------

        >>> oModule.AssignIndependent
        >>> oModule.AssignDependent
        """
        try:
            master_entity = self.modeler.convert_to_selections(master_entity, True)
            slave_entity = self.modeler.convert_to_selections(slave_entity, True)
            if not bound_name:
                bound_name_m = generate_unique_name("Independent")
                bound_name_s = generate_unique_name("Dependent")
            else:
                bound_name_m = bound_name
                bound_name_s = bound_name + "_dep"
            if (
                not isinstance(u_vector_origin_coordinates_master, list)
                or not isinstance(u_vector_origin_coordinates_slave, list)
                or not isinstance(u_vector_pos_coordinates_master, list)
                or not isinstance(u_vector_pos_coordinates_slave, list)
            ):
                raise ValueError("Please provide a list of coordinates for U vectors.")
            elif [x for x in u_vector_origin_coordinates_master if not isinstance(x, str)]:
                raise ValueError("Elements of coordinates system must be strings in the form of ``value+unit``.")
            elif [x for x in u_vector_origin_coordinates_slave if not isinstance(x, str)]:
                raise ValueError("Elements of coordinates system must be strings in the form of ``value+unit``.")
            elif [x for x in u_vector_pos_coordinates_master if not isinstance(x, str)]:
                raise ValueError("Elements of coordinates system must be strings in the form of ``value+unit``.")
            elif [x for x in u_vector_pos_coordinates_slave if not isinstance(x, str)]:
                raise ValueError("Elements of coordinates system must be strings in the form of ``value+unit``.")
            elif len(u_vector_origin_coordinates_master) != 3:
                raise ValueError("Vector must contain 3 elements for x, y and z coordinates.")
            elif len(u_vector_origin_coordinates_slave) != 3:
                raise ValueError("Vector must contain 3 elements for x, y and z coordinates.")
            elif len(u_vector_pos_coordinates_master) != 3:
                raise ValueError("Vector must contain 3 elements for x, y and z coordinates.")
            elif len(u_vector_pos_coordinates_slave) != 3:
                raise ValueError("Vector must contain 3 elements for x, y and z coordinates.")
            u_master_vector_coordinates = OrderedDict(
                {
                    "Coordinate System": "Global",
                    "Origin": u_vector_origin_coordinates_master,
                    "UPos": u_vector_pos_coordinates_master,
                }
            )
            props2 = OrderedDict(
                {"Faces": master_entity, "CoordSysVector": u_master_vector_coordinates, "ReverseV": reverse_master}
            )
            bound = BoundaryObject(self, bound_name_m, props2, "Independent")
            if bound.create():
                self.boundaries.append(bound)

                u_slave_vector_coordinates = OrderedDict(
                    {
                        "Coordinate System": "Global",
                        "Origin": u_vector_origin_coordinates_slave,
                        "UPos": u_vector_pos_coordinates_slave,
                    }
                )

                props2 = OrderedDict(
                    {
                        "Faces": slave_entity,
                        "CoordSysVector": u_slave_vector_coordinates,
                        "ReverseU": reverse_slave,
                        "Independent": bound_name_m,
                        "RelationIsSame": same_as_master,
                    }
                )
                bound2 = BoundaryObject(self, bound_name_s, props2, "Dependent")
                if bound2.create():
                    self.boundaries.append(bound2)
                    return bound, bound2
                else:
                    return bound, False
        except:
            return False, False


class Maxwell2d(Maxwell, FieldAnalysis3D, object):
    """Provides the Maxwell 2D application interface.

    This class allows you to connect to an existing Maxwell 2D design or create a
    new Maxwell 2D design if one does not exist.

    Parameters
    ----------
    projectname : str, optional
        Name of the project to select or the full path to the project
        or AEDTZ archive to open. The default is ``None``, in which
        case an attempt is made to get an active project. If no
        projects are present, an empty project is created.
    designname : str, optional
        Name of the design to select. The default is ``None``, in
        which case an attempt is made to get an active design. If no
        designs are present, an empty design is created.
    solution_type : str, optional
        Solution type to apply to the design. The default is
        ``None``, in which case the default type is applied.
    setup_name : str, optional
        Name of the setup to use as the nominal. The default is
        ``None``, in which case the active setup is used or
        nothing is used.
    specified_version : str, optional
        Version of AEDT to use. The default is ``None``, in which case
        the active version or latest installed version is used.
        This parameter is ignored when a script is launched within AEDT.
    non_graphical : bool, optional
        Whether to launch AEDT in non-graphical mode. The default
        is ``False``, in which case AEDT is launched in graphical mode.
        This parameter is ignored when a script is launched within AEDT.
    new_desktop_session : bool, optional
        Whether to launch an instance of AEDT in a new thread, even if
        another instance of the ``specified_version`` is active on the
        machine. The default is ``True``. This parameter is ignored when
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
        ``None``. This parameter is only used when ``new_desktop_session = False``.

    Examples
    --------
    Create an instance of Maxwell 2D and connect to an existing
    Maxwell 2D design or create a new Maxwell 2D design if one does
    not exist.

    >>> from pyaedt import Maxwell2d
    >>> aedtapp = Maxwell2d()

    Create an instance of Maxwell 2D and link to a project named
    ``projectname``. If this project does not exist, create one with
    this name.

    >>> aedtapp = Maxwell2d(projectname)

    Create an instance of Maxwell 2D and link to a design named
    ``designname`` in a project named ``projectname``.

    >>> aedtapp = Maxwell2d(projectname,designame)

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

    def __init__(
        self,
        projectname=None,
        designname=None,
        solution_type=None,
        setup_name=None,
        specified_version=None,
        non_graphical=False,
        new_desktop_session=False,
        close_on_exit=False,
        student_version=False,
        machine="",
        port=0,
        aedt_process_id=None,
    ):
        self.is3d = False
        FieldAnalysis3D.__init__(
            self,
            "Maxwell 2D",
            projectname,
            designname,
            solution_type,
            setup_name,
            specified_version,
            non_graphical,
            new_desktop_session,
            close_on_exit,
            student_version,
            machine,
            port,
            aedt_process_id,
        )
        Maxwell.__init__(self)

    @property
    def xy_plane(self):
        """Maxwell 2D plane between ``True`` and ``False``."""
        return self.design_solutions.xy_plane

    @xy_plane.setter
    @pyaedt_function_handler()
    def xy_plane(self, value=True):
        self.design_solutions.xy_plane = value

    @property
    def model_depth(self):
        """Model depth."""

        if "ModelDepth" in self.design_properties:
            value_str = self.design_properties["ModelDepth"]
            try:
                a = float_units(value_str)
            except:
                a = self.variable_manager[value_str].value
            finally:
                return a
        else:
            return None

    @model_depth.setter
    def model_depth(self, value):
        """Set model depth."""
        return self.change_design_settings(
            {"ModelDepth": self._modeler._arg_with_dim(value, self._modeler.model_units)}
        )

    @pyaedt_function_handler()
    def generate_design_data(self, linefilter=None, objectfilter=None):
        """Generate a generic set of design data and store it in the extension directory as ``design_data.json``.

        Parameters
        ----------
        linefilter : optional
            The default is ``None``.
        objectfilter : optional
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
        if objectfilter:
            solid_ids = [i for i, j in self.modeler.object_id_dict.items() if j.name in objectfilter]
        else:
            solid_ids = [i for i in list(self.modeler.object_id_dict.keys())]
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
            "LineList": self.modeler.vertex_data_of_lines(linefilter),
            "VarList": self.variable_manager.variable_names,
            "Setups": self.existing_analysis_setups,
            "MaterialProperties": self.get_object_material_properties(solid_bodies),
        }

        design_file = os.path.join(self.working_directory, "design_data.json")
        with open_file(design_file, "w") as fps:
            json.dump(convert(self.design_data), fps, indent=4)
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
        with open_file(design_file, "r") as fps:
            design_data = json.load(fps)
        return design_data

    @pyaedt_function_handler()
    def assign_balloon(self, edge_list, bound_name=None):
        """Assign a balloon boundary to a list of edges.

        Parameters
        ----------
        edge_list : list
            List of edges.
        bound_name : str, optional
            Name of the boundary. The default is ``None``, in which
            case the default name is used.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        References
        ----------

        >>> oModule.AssignBalloon
        """
        edge_list = self.modeler.convert_to_selections(edge_list, True)

        if not bound_name:
            bound_name = generate_unique_name("Balloon")

        props2 = OrderedDict({"Edges": edge_list})
        bound = BoundaryObject(self, bound_name, props2, "Balloon")

        if bound.create():
            self.boundaries.append(bound)
            return bound
        return False

    @pyaedt_function_handler()
    def assign_vector_potential(self, input_edge, vectorvalue=0, bound_name=None):
        """Assign a vector to a list of edges.

        Parameters
        ----------
        input_edge : list
            List of edge names or edge IDs to assign a vector to.
        vectorvalue : float, optional
            Value of the vector. The default is ``0``.
        bound_name : str, optional
            Name of the boundary. The default is ``None``, in which
            case the default name is used.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Vector Potential Object.

        References
        ----------

        >>> oModule.AssignVectorPotential
        """
        input_edge = self.modeler.convert_to_selections(input_edge, True)

        if not bound_name:
            bound_name = generate_unique_name("Vector")
        if type(input_edge[0]) is str:
            props2 = OrderedDict({"Objects": input_edge, "Value": str(vectorvalue), "CoordinateSystem": ""})
        else:
            props2 = OrderedDict({"Edges": input_edge, "Value": str(vectorvalue), "CoordinateSystem": ""})
        bound = BoundaryObject(self, bound_name, props2, "Vector Potential")

        if bound.create():
            self.boundaries.append(bound)
            return bound
        return False

    @pyaedt_function_handler()
    def assign_master_slave(
        self, master_edge, slave_edge, reverse_master=False, reverse_slave=False, same_as_master=True, bound_name=None
    ):
        """Assign master and slave boundary conditions to two edges of the same object.

        Parameters
        ----------
        master_edge : int
            ID of the master edge.
        slave_edge : int
            ID of the slave edge.
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
        :class:`pyaedt.modules.Boundary.BoundaryObject`, :class:`pyaedt.modules.Boundary.BoundaryObject`
            Master and slave objects.

        References
        ----------
        >>> oModule.AssignIndependent
        >>> oModule.AssignDependent
        """
        master_edge = self.modeler.convert_to_selections(master_edge, True)
        slave_edge = self.modeler.convert_to_selections(slave_edge, True)
        if not bound_name:
            bound_name_m = generate_unique_name("Independent")
            bound_name_s = generate_unique_name("Dependent")
        else:
            bound_name_m = bound_name
            bound_name_s = bound_name + "_dep"
        props2 = OrderedDict({"Edges": master_edge, "ReverseV": reverse_master})
        bound = BoundaryObject(self, bound_name_m, props2, "Independent")
        if bound.create():
            self.boundaries.append(bound)

            props2 = OrderedDict(
                {
                    "Edges": slave_edge,
                    "ReverseU": reverse_slave,
                    "Independent": bound_name_m,
                    "SameAsMaster": same_as_master,
                }
            )
            bound2 = BoundaryObject(self, bound_name_s, props2, "Dependent")
            if bound2.create():
                self.boundaries.append(bound2)
                return bound, bound2
            else:
                return bound, False
        return False, False

    @pyaedt_function_handler()
    def assign_end_connection(self, objects, resistance=0, inductance=0, bound_name=None):
        """Assign an end connection to a list of objects.

        Parameters
        ----------
        objects : list of int or str or :class:`pyaedt.modeler.object3d.Object3d`
            List of objects to assign an end connection to.
        resistance : float or str, optional
            Resistance value. If float is provided, the units are assumed to be ohms.
            The default value is ``0``,
        inductance : float or str, optional
            Inductance value. If a float is provided, the units are assumed to Henry (H).
            The default value is ``0``.
        bound_name : str, optional
            Name of the end connection boundary. The default is ``None``, in which case the
            default name is used.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            New created object.

        References
        ----------

        >>> oModule.AssignEndConnection
        """
        if self.solution_type not in ["EddyCurrent", "Transient"]:
            self.logger.error("Excitation applicable only to Eddy current or Transient Solver.")
            return False
        if len(objects) < 2:
            self.logger.error("At least 2 objects are needed.")
            return False
        objects = self.modeler.convert_to_selections(objects, True)
        if not bound_name:
            bound_name = generate_unique_name("EndConnection")

        props = OrderedDict(
            {
                "Objects": objects,
                "ResistanceValue": self.modeler._arg_with_dim(resistance, "ohm"),
                "InductanceValue": self.modeler._arg_with_dim(inductance, "H"),
            }
        )
        bound = BoundaryObject(self, bound_name, props, "EndConnection")
        if bound.create():
            self.boundaries.append(bound)
            return bound
        return False
