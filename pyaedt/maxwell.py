"""This module contains these Maxwell classes: ``Maxwell``, ``Maxwell2d``, and ``Maxwell3d``."""

from __future__ import absolute_import  # noreorder

from collections import OrderedDict
import io
import json
import os
import re

from pyaedt.application.Analysis3D import FieldAnalysis3D
from pyaedt.application.Variables import decompose_variable_value
from pyaedt.generic.constants import SOLUTIONS
from pyaedt.generic.general_methods import generate_unique_name, open_file, pyaedt_function_handler
from pyaedt.modeler.geometry_operators import GeometryOperators
from pyaedt.modules.Boundary import BoundaryObject, MaxwellParameters
from pyaedt.modules.SetupTemplates import SetupKeys


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
        >>> oModule.GetExcitationsOfType("Winding Group")
        """
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
        if skew_type not in ["Continuous", "Step", "V-Shape", "User Defined"]:
            self.logger.error("Invalid skew type.")
            return False
        if skew_part not in ["Rotor", "Stator"]:
            self.logger.error("Invalid skew part.")
            return False
        if skew_angle_unit not in ["deg", "rad", "degsec", "degmin"]:
            self.logger.error("Invalid skew angle unit.")
            return False
        if skew_type != "User Defined":
            arg = {
                "UseSkewModel": True,
                "SkewType": skew_type,
                "SkewPart": skew_part,
                "SkewAngle": "{}{}".format(skew_angle, skew_angle_unit),
                "NumberOfSlices": number_of_slices,
            }
            return self.change_design_settings(arg)
        else:
            if not custom_slices_skew_angles or len(custom_slices_skew_angles) != int(number_of_slices):
                self.logger.error("Please provide skew angles for each slice.")
                return False
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

    @pyaedt_function_handler()
    def set_core_losses(self, objects, value=False):
        """Whether to enable core losses for a set of objects.

        For ``EddyCurrent`` and ``Transient`` solver designs, core losses calulcations
        may be included in the simulation on any object that has a corresponding
        core loss definition (with core loss coefficient settings) in the material library.

        Parameters
        ----------
        objects : list, str
            List of object to apply core losses to.
        value : bool, optional
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

        Matrix assignment can be calculated based upon the solver type.
        For 2D/3D solvers the available solution types are: ``Magnetostatic``,
        ``Electrostatic``, ``Eddy Current``, ``DC Conduction`` and ``AC Conduction``.


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
        Set matrix in a Maxwell magnetostatic analysis.

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

        Set matrix in a Maxwell DC Conduction analysis.
        >>> m2d.assign_voltage(["Port1"], amplitude=1, name="1V")
        >>> m2d.assign_voltage(["Port2"], amplitude=0, name="0V")
        >>> m2d.assign_matrix(sources=['1V'], group_sources=['0V'], matrix_name="Matrix1")

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
                self._boundaries[bound.name] = bound
                return bound
        else:
            self.logger.error("Solution type does not have matrix parameters")
            return False

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
        if self.solution_type not in ["Transient"]:
            self.logger.error("Control Program is only available in Maxwell 2D and 3D Transient solutions.")
            return False

        self._py_file = setupname + ".py"
        ctl_file_path = os.path.join(self.working_directory, self._py_file)

        if aedt_lib_dir:
            source_dir = aedt_lib_dir
        else:
            source_dir = self.pyaedt_dir

        if os.path.exists(ctl_file_path) and keep_modifications:
            with open(ctl_file_path, "r") as fi:
                existing_data = fi.readlines()
            with open(ctl_file_path, "w") as fo:
                first_line = True
                for line in existing_data:
                    if first_line:
                        first_line = False
                        if python_interpreter:
                            fo.write("#!{0}\n".format(python_interpreter))
                    if line.startswith("work_dir"):
                        fo.write("work_dir = r'{0}'\n".format(self.working_directory))
                    elif line.startswith("lib_dir"):
                        fo.write("lib_dir = r'{0}'\n".format(source_dir))
                    else:
                        fo.write(line)
        else:
            if file_str is not None:
                with io.open(ctl_file_path, "w", newline="\n") as fo:
                    fo.write(file_str)
                assert os.path.exists(ctl_file_path), "Control program file could not be created."

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

    @pyaedt_function_handler()
    def eddy_effects_on(self, object_list, activate_eddy_effects=True, activate_displacement_current=True):
        """Assign eddy effects on a list of objects.

        For Eddy Current solvers only, you must specify the displacement current on the model objects.

        Parameters
        ----------
        object_list : list
            List of objects.
        activate_eddy_effects : bool, optional
            Whether to activate eddy effects. The default is ``True``.
        activate_displacement_current : bool, optional
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
        windings_name : list, optional
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
        if self.solution_type not in ["Transient"]:
            self.logger.error("Y connections only available for Transient solutions.")
            return False

        if windings_name:
            connection = ["NAME:YConnection", "Windings:=", ",".join(windings_name)]
            windings = ["NAME:YConnection", connection]
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
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        References
        ----------
        >>> oModule.AssignCurrent

        Examples
        --------
        >>> from pyaedt import Maxwell3d
        >>> app = pyaedt.Maxwell3d(solution_type="ElectroDCConduction")
        >>> cylinder= app.modeler.create_cylinder("X", [0,0,0],10, 100, 250)
        >>> current = app.assign_current(cylinder.top_face_x.id, amplitude= "2mA")
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
                "ElectroDCConduction",
            ]:
                props["Phase"] = phase
            if self.solution_type not in ["DCConduction", "ElectricTransient", "ElectroDCConduction"]:
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
            self._boundaries[bound.name] = bound
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

        For both rotational and translational problems, the band objects must always enclose all the moving objects.

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
            self._boundaries[bound.name] = bound
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

        For both rotational and translational problems, the band objects must always enclose all the moving objects.

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
            Load torque sign is determined based on the moving vector, using the right-hand rule.
            The default is ``"0NewtonMeter"``. If a float value is used "NewtonMeter" units are applied.

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
            self._boundaries[bound.name] = bound
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
            ``False`` when failed.

        References
        ----------
        >>> oModule.AssignVoltage
        """
        if isinstance(amplitude, (int, float)):
            amplitude = str(amplitude) + "mV"

        if not name:
            name = generate_unique_name("Voltage")
        face_list = self.modeler.convert_to_selections(face_list, True)

        if self.design_type == "Maxwell 2D":
            props = OrderedDict({"Objects": face_list, "Value": amplitude})
        else:
            props = OrderedDict({"Faces": face_list, "Voltage": amplitude})
        bound = BoundaryObject(self, name, props, "Voltage")
        if bound.create():
            self._boundaries[bound.name] = bound
            return bound
        return False

    @pyaedt_function_handler()
    def assign_voltage_drop(self, face_list, amplitude=1, swap_direction=False, name=None):
        """Assign a voltage drop across a list of faces to a specific value.

        The voltage drop applies only to sheet objects.

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
            ``False`` when failed.

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
            self._boundaries[bound.name] = bound
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
        phase=0,
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
        phase : float, optional
            Value of the phase delay in degrees. The default is ``0``.
        name : str, optional
            Name of the boundary. The default is ``None``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Bounding object for the winding, otherwise only the bounding object.
            ``False`` when failed.

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
                "Phase": self.modeler._arg_with_dim(phase, "deg"),
            }
        )
        bound = BoundaryObject(self, name, props, "Winding")
        if bound.create():
            self._boundaries[bound.name] = bound
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
        :class:`pyaedt.modules.Boundary.BoundaryObject`
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
            self._boundaries[bound.name] = bound
            return bound
        return False

    @pyaedt_function_handler()
    def assign_force(self, input_object, reference_cs="Global", is_virtual=True, force_name=None):
        """Assign a force to one or more objects.

        Force assignment can be calculated based upon the solver type.
        For 3D solvers the available solution types are: ``Magnetostatic``,
        ``Electrostatic``, ``Eddy Current``, ``Transient`` and ``Electric Transient``.
        For 2D solvers the available solution types are: ``Magnetostatic``,
        ``Electrostatic``, ``Eddy Current`` and ``Transient``.

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

        Examples
        --------
        Assign virtual force to a magnetic object:

        >>> iron_object = m3d.modeler.create_box([0, 0, 0], [2, 10, 10], name="iron")
        >>> magnet_object = m3d.modeler.create_box([10, 0, 0], [2, 10, 10], name="magnet")
        >>> m3d.assign_material(iron_object, "iron")
        >>> m3d.assign_material(magnet_object, "NdFe30")
        >>> m3d.assign_force("iron", force_name="force_iron", is_virtual=True)

        Assign Lorentz force to a conductor:

        >>> conductor1 = m3d.modeler.create_box([0, 0, 0], [1, 1, 10], name="conductor1")
        >>> conductor2 = m3d.modeler.create_box([10, 0, 0], [1, 1, 10], name="conductor2")
        >>> m3d.assign_material(conductor1, "copper")
        >>> m3d.assign_material(conductor2, "copper")
        >>> m3d.assign_force("conductor1", force_name="force_copper", is_virtual=False) # conductor, use Lorentz force
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
                self._boundaries[bound.name] = bound
                return bound
        else:
            self.logger.error("Solution Type has not Matrix Parameter")
            return False

    @pyaedt_function_handler()
    def assign_torque(
        self, input_object, reference_cs="Global", is_positive=True, is_virtual=True, axis="Z", torque_name=None
    ):
        """Assign a torque to one or more objects.

        Torque assignment can be calculated based upon the solver type.
        For 3D solvers the available solution types are: ``Magnetostatic``,
        ``Electrostatic``, ``Eddy Current``, ``Transient`` and ``Electric Transient``.
        For 2D solvers the available solution types are: ``Magnetostatic``,
        ``Electrostatic``, ``Eddy Current`` and ``Transient``.

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
                self._boundaries[bound.name] = bound
                return bound
        else:
            self.logger.error("Solution Type has not Matrix Parameter")
            return False

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
        if self.solution_type != "Transient":
            self.logger.error("This methods work only with Maxwell Transient Analysis.")
            return False
        self.oanalysis.ResetSetupToTimeZero(self._setup)
        self.analyze()
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

        This boundary condition defines a plane of geometric or magnetic symmetry in a structure.
        Assign it only to the outer surfaces of the problem region.

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
                self._boundaries[bound.name] = bound
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

        This method specifies the x-, y-, and z-components of the current density in a conduction path.

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
                    self._boundaries[bound.name] = bound
                    return bound
                return True
            except:
                self.logger.error("Couldn't assign current density to desired list of objects.")
                return False
        else:
            self.logger.error("Current density can only be applied to Eddy current or magnetostatic solution types.")
            return False

    @pyaedt_function_handler()
    def assign_radiation(self, input_object, radiation_name=None):
        """Assign radiation boundary to one or more objects.

        Radiation assignment can be calculated based upon the solver type.
        Available solution type is: ``Eddy Current``.

        Parameters
        ----------
        input_object : str, list
            One or more objects to assign the radiation to.
        radiation_name : str, optional
            Name of the force. The default is ``None``, in which case the default
            name is used.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Radiation objects. If the method fails to execute it returns ``False``.

        References
        ----------
        >>> oModule.Radiation

        Examples
        --------
        Assign radiation boundary to one box and one face:

        >>> box1 = m3d.modeler.create_box([0, 0, 0], [2, 10, 10])
        >>> box2 = m3d.modeler.create_box([10, 0, 0], [2, 10, 10])
        >>> m3d.assign_radiation([box1, box2.faces[0]], force_name="radiation_boundary")
        """
        if self.solution_type in ["EddyCurrent"]:
            if not radiation_name:
                radiation_name = generate_unique_name("Radiation")
            elif radiation_name in self.modeler.get_boundaries_name():
                radiation_name = generate_unique_name(radiation_name)

            listobj = self.modeler.convert_to_selections(input_object, True)
            props = {"Objects": [], "Faces": []}
            for sel in listobj:
                if isinstance(sel, str):
                    props["Objects"].append(sel)
                elif isinstance(sel, int):
                    props["Faces"].append(sel)
            bound = BoundaryObject(self, radiation_name, props, "Radiation")
            if bound.create():
                self._boundaries[bound.name] = bound
                return bound
        self.logger.error("Excitation applicable only to Eddy current.")
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
        """Enable the harmonic force calculation for the transient analysis.

        Parameters
        ----------
        objects : list
            List of object names for force calculations.
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
        calculate_force : sr, optional
            How to calculate force. The default is ``"Harmonic"``.
            Options are ``"Harmonic"`` and ``"Transient"``.


        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

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
    def enable_harmonic_force_on_layout_component(
        self,
        layout_component_name,
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
        layout_component_name : str
            Name of layout component to apply harmonic forces.
        nets : dict
            Dictionary containing nets and layers on which enable harmonic forces.
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
        if self.solution_type != "TransientAPhiFormulation":
            self.logger.error("This methods work only with Maxwell TransientAPhiFormulation Analysis.")
            return False
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
                "NAME:" + layout_component_name,
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

    @pyaedt_function_handler()
    def export_element_based_harmonic_force(
        self,
        output_directory=None,
        setup_name=None,
        start_frequency=None,
        stop_frequency=None,
        number_of_frequency=None,
    ):
        """Export an element-based harmonic force data to a .csv file.

        Parameters
        ----------
        output_directory : str, optional
            The path for the output directory. If ``None`` pyaedt working dir will be used.
        setup_name : str, optional
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
        if self.solution_type != "Transient" and self.solution_type != "TransientAPhiFormulation":
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

    @pyaedt_function_handler
    def edit_external_circuit(self, netlist_file_path, schematic_design_name):
        """Edit the external circuit for the winding.

        Parameters
        ----------
        netlist_file_path : str
            Circuit netlist file path.
        schematic_design_name : str
            Name of the schematic design.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if schematic_design_name not in self.design_list:
            return False
        odesign = self.oproject.SetActiveDesign(schematic_design_name)
        oeditor = odesign.SetActiveEditor("SchematicEditor")
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
        self.oboundary.EditExternalCircuit(netlist_file_path, sources_array, sources_type_array, [], [])
        return True

    @pyaedt_function_handler()
    def create_setup(self, setupname="MySetupAuto", setuptype=None, **kwargs):
        """Create an analysis setup for Maxwell 3D or 2D.
        Optional arguments are passed along with ``setuptype`` and ``setupname``.  Keyword
        names correspond to the ``setuptype``
        corresponding to the native AEDT API.  The list of
        keywords here is not exhaustive.

        .. note::
           This method overrides the ``Analysis.setup()`` method for the HFSS app.

        Parameters
        ----------
        setuptype : int, str, optional
            Type of the setup. Based on the solution type, options are
            ``"HFSSDrivenAuto"``, ``"HFSSDrivenDefault"``,
            ``"HFSSEigen"``, ``"HFSSTransient"`` and ``"HFSSSBR"``.
            The default is ``"HFSSDrivenAuto"``.
        setupname : str, optional
            Name of the setup. The default is ``"Setup1"``.
        **kwargs : dict, optional
            Available keys depend on the setup chosen.
            For more information, see :doc:`../SetupTemplatesMaxwell`.

        Returns
        -------
        :class:`pyaedt.modules.SolveSetup.SetupMaxwell`
            3D Solver Setup object.

        References
        ----------
        >>> oModule.InsertSetup

        Examples
        --------
        >>> from pyaedt import Maxwell3d
        >>> app = Maxwell3d()
        >>> app.create_setup(setupname="Setup1", setuptype="EddyCurrent", MaximumPasses=10,PercentError=2 )

        """
        if setuptype is None:
            setuptype = self.design_solutions.default_setup
        elif setuptype in SetupKeys.SetupNames:
            setuptype = SetupKeys.SetupNames.index(setuptype)
        if "props" in kwargs:
            return self._create_setup(setupname=setupname, setuptype=setuptype, props=kwargs["props"])
        else:
            setup = self._create_setup(setupname=setupname, setuptype=setuptype)
        setup.auto_update = False
        for arg_name, arg_value in kwargs.items():
            if setup[arg_name] is not None:
                setup[arg_name] = arg_value
        setup.auto_update = True
        setup.update()
        return setup


class Maxwell3d(Maxwell, FieldAnalysis3D, object):
    """Provides the Maxwell 3D app interface.

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
    specified_version : str, int, float, optional
        Version of AEDT to use. The default is ``None``, in which case
        the active version or latest installed version is used. This
        parameter is ignored when a script is launched within AEDT.
        Examples of input values are ``232``, ``23.2``,``2023.2``,``"2023.2"``.
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
    PyAEDT INFO: Added design ...

    Create an instance of Maxwell 3D using the 2023 R2 release and open
    the specified project, which is named ``mymaxwell2.aedt``.

    >>> aedtapp = Maxwell3d(specified_version="2023.2", projectname="mymaxwell2.aedt")
    PyAEDT INFO: Added design ...

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
        """Initialize the ``Maxwell`` class.
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

    def _init_from_design(self, *args, **kwargs):
        self.__init__(*args, **kwargs)

    @pyaedt_function_handler()
    def assign_insulating(self, geometry_selection, insulation_name=None):
        """Create an insulating boundary condition.

        This boundary condition is used to model very thin sheets of perfectly insulating material between
        touching conductors. Current cannot cross an insulating boundary.

        Parameters
        ----------
        geometry_selection : str or int
            Objects or faces to apply the insulating boundary to.
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
            props = {"Objects": [], "Faces": []}
            for sel in listobj:
                if isinstance(sel, str):
                    props["Objects"].append(sel)
                elif isinstance(sel, int):
                    props["Faces"].append(sel)

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
        """Create an impedance boundary condition for Transient or Eddy Current solvers.

        This boundary condition is used to simulate the effect of induced currents in a conductor without
        explicitly computing them.

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
        """Assign current density terminal to a single or list of entities for an Eddy Current or Magnetostatic solver.

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
                    self._boundaries[bound.name] = bound
                    return bound
                return False
            except:
                return False
        else:
            self.logger.error("Current density can only be applied to Eddy current or magnetostatic solution types.")
            return False

    @pyaedt_function_handler()
    def _create_boundary(self, name, props, boundary_type):
        """Create a boundary.

        Parameters
        ----------
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
            self._boundaries[bound.name] = bound
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
        """Assign dependent and independent boundary conditions to two faces of the same object.

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
            Master and slave objects. If the method fails to execute it returns ``False``.

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
                self._boundaries[bound.name] = bound

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
                    self._boundaries[bound2.name] = bound2
                    return bound, bound2
                else:
                    return bound, False
        except:
            return False, False

    @pyaedt_function_handler
    def assign_flux_tangential(self, objects_list, flux_name=None):
        # type : (list, str = None) -> pyaedt.modules.Boundary.BoundaryObject
        """Assign a flux tangential boundary for a transient A-Phi solver.

        Parameters
        ----------
        objects_list : list
            List of objects to assign the flux tangential boundary condition to.
        flux_name : str, optional
            Name of the flux tangential boundary. The default is ``None``,
            in which case a random name is automatically generated.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object if successful, ``False`` otherwise.

        References
        ----------
        >>> oModule.AssignFluxTangential

        Examples
        --------
        Create a box and assign a flux tangential boundary to one of its faces.

        >>> box = maxwell3d_app.modeler.create_box([50, 0, 50], [294, 294, 19], name="Box")
        >>> flux_tangential = maxwell3d_app.assign_flux_tangential(box.faces[0], "FluxExample")
        """
        if self.solution_type != "TransientAPhiFormulation":
            self.logger.error("Flux tangential boundary can only be assigned to a transient APhi solution type.")
            return False

        objects_list = self.modeler.convert_to_selections(objects_list, True)

        if not flux_name:
            flux_name = generate_unique_name("FluxTangential")
        elif flux_name in self.modeler.get_boundaries_name():
            flux_name = generate_unique_name(flux_name)

        props = {"NAME": flux_name, "Faces": []}
        for sel in objects_list:
            props["Faces"].append(sel)

        return self._create_boundary(flux_name, props, "FluxTangential")

    @pyaedt_function_handler
    def assign_layout_force(
        self, nets_layers_mapping, component_name, reference_cs="Global", force_name=None, include_no_layer=True
    ):
        # type: (dict, str, str, str, bool) -> bool
        """Assign the layout force to a component in a Transient A-Phi solver.
        To access layout component features the Beta option has to be enabled first.

        Parameters
        ----------
        nets_layers_mapping : dict
            Each <layer, net> pair represents the object(s) in the intersection of corresponding layer and net.
            Net name is dictionary's key, layers name is the list of layer names.
        component_name : str
            Name of the 3d component to assign the layout force to.
        reference_cs : str, optional
            Reference coordinate system.
            If not provided the global one will be set.
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
        >>> nets_layers = {}
        >>> nets_layers["<no-net>"] = ["PWR","TOP","UNNAMED_000","UNNAMED_002"]
        >>> nets_layers["GND"] = ["LYR_1","LYR_2","UNNAMED_006"]

        Assign layout force to a component.
        >>> m3d = Maxwell3d()
        >>> m3d.assign_layout_force(nets_layers_mapping=nets_layers, component_name="LC1_1")
        """
        for key in nets_layers_mapping.keys():
            if not isinstance(nets_layers_mapping[key], list):
                nets_layers_mapping[key] = list(nets_layers_mapping[key])

        if component_name not in self.modeler.user_defined_component_names:
            self.logger.error("Provided component name doesn't exist in current design.")
            return False

        if not force_name:
            force_name = generate_unique_name("Layout_Force")

        nets_layers_props = None
        for key, valy in nets_layers_mapping.items():
            layers = valy[:]
            if include_no_layer:
                layers = layers[:] + ["<no-layer>"]
            if nets_layers_props:
                nets_layers_props.append(OrderedDict({key: OrderedDict({"LayerSet": layers})}))
            else:
                nets_layers_props = [OrderedDict({key: OrderedDict({"LayerSet": layers})})]

        props = OrderedDict(
            {
                "Reference CS": reference_cs,
                "NetsAndLayersChoices": OrderedDict(
                    {component_name: OrderedDict({"NetLayerSetMap": nets_layers_props})}
                ),
            }
        )
        bound = MaxwellParameters(self, force_name, props, "LayoutForce")
        if bound.create():
            self._boundaries[bound.name] = bound
            return bound

    @pyaedt_function_handler()
    def assign_tangential_h_field(
        self,
        faces,
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
        faces : list of int  or :class:`pyaedt.modeler.cad.object3d.Object3d`
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
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Newly created object when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.AssignTangentialHField
        """
        if self.solution_type not in ["EddyCurrent", "Magnetostatic"]:
            self.logger.error("Tangential H Field is applicable only to Eddy current.")
            return False
        objects = self.modeler.convert_to_selections(faces, True)
        if not bound_name:
            bound_name = generate_unique_name("TangentialHField")
        props = OrderedDict(
            {
                "Faces": objects,
            }
        )
        if isinstance(objects[0], str):
            props = OrderedDict(
                {
                    "Objects": objects,
                }
            )
        props["ComponentXReal"] = x_component_real
        if self.solution_type == "EddyCurrent":
            props["ComponentXImag"] = x_component_imag
        props["ComponentYReal"] = y_component_real
        if self.solution_type == "EddyCurrent":
            props["ComponentYImag"] = y_component_imag
        if not origin and isinstance(objects[0], int):
            edges = self.modeler.get_face_edges(objects[0])
            origin = self.oeditor.GetEdgePositionAtNormalizedParameter(edges[0], 0)
            if not u_pos:
                u_pos = self.oeditor.GetEdgePositionAtNormalizedParameter(edges[0], 1)

        props["CoordSysVector"] = OrderedDict({"Coordinate System": coordinate_system, "Origin": origin, "UPos": u_pos})
        props["ReverseV"] = reverse
        bound = BoundaryObject(self, bound_name, props, "Tangential H Field")
        if bound.create():
            self._boundaries[bound.name] = bound
            return bound
        return False

    @pyaedt_function_handler()
    def assign_zero_tangential_h_field(self, faces, bound_name=None):
        """Assign a zero tangential H field boundary to a list of faces.

        Parameters
        ----------
        faces : list of int or :class:`pyaedt.modeler.cad.object3d.Object3d`
            List of objects to assign an end connection to.
        bound_name : str, optional
            Name of the end connection boundary. The default is ``None``, in which case the
            default name is used.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Newly created object. ``False`` if it fails.

        References
        ----------
        >>> oModule.AssignZeroTangentialHField
        """
        if self.solution_type not in ["EddyCurrent"]:
            self.logger.error("Tangential H Field is applicable only to Eddy current.")
            return False
        objects = self.modeler.convert_to_selections(faces, True)
        if not bound_name:
            bound_name = generate_unique_name("ZeroTangentialHField")
        props = OrderedDict(
            {
                "Faces": objects,
            }
        )
        bound = BoundaryObject(self, bound_name, props, "Zero Tangential H Field")
        if bound.create():
            self._boundaries[bound.name] = bound
            return bound
        return False


class Maxwell2d(Maxwell, FieldAnalysis3D, object):
    """Provides the Maxwell 2D app interface.

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
    specified_version : str, int, float, optional
        Version of AEDT to use. The default is ``None``, in which case
        the active version or latest installed version is used.
        This parameter is ignored when a script is launched within AEDT.
        Examples of input values are ``232``, ``23.2``,``2023.2``,``"2023.2"``.
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
        >>> oDesign.GetGeometryMode
        """
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

    def _init_from_design(self, *args, **kwargs):
        self.__init__(*args, **kwargs)

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
        design_settings = self.design_settings()
        if "ModelDepth" in design_settings:
            value_str = design_settings["ModelDepth"]
            return value_str
        else:
            return None

    @model_depth.setter
    def model_depth(self, value):
        """Set model depth."""
        if isinstance(value, float) or isinstance(value, int):
            value = self.modeler._arg_with_dim(value, self.modeler.model_units)
        self.change_design_settings({"ModelDepth": value})

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
            solid_ids = [i for i, j in self.modeler._object_names_to_ids.items() if j.name in objectfilter]
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
            Boundary object. If the method fails to execute it returns ``False``.

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
            self._boundaries[bound.name] = bound
            return bound
        return False

    @pyaedt_function_handler()
    def assign_vector_potential(self, input_edge, vectorvalue=0, bound_name=None):
        """Assign a vector potential boundary condition to specified edges.

        This method is valid for Maxwell 2D Eddy Current, Magnetostatic, and Transient solvers.

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
            Vector Potential Object. ``False`` if it fails.

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
            self._boundaries[bound.name] = bound
            return bound
        return False

    @pyaedt_function_handler()
    def assign_master_slave(
        self, master_edge, slave_edge, reverse_master=False, reverse_slave=False, same_as_master=True, bound_name=None
    ):
        """Assign dependent and independent boundary conditions to two edges of the same object.

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
            Master and slave objects. If the method fails to execute it returns ``False``.

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
            self._boundaries[bound.name] = bound

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
                self._boundaries[bound2.name] = bound2
                return bound, bound2
            else:
                return bound, False
        return False, False

    @pyaedt_function_handler()
    def assign_end_connection(self, objects, resistance=0, inductance=0, bound_name=None):
        """Assign an end connection to a list of objects.

        Parameters
        ----------
        objects : list of int or str or :class:`pyaedt.modeler.cad.object3d.Object3d`
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
            Newly created object. ``False`` if it fails.

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
            self._boundaries[bound.name] = bound
            return bound
        return False
