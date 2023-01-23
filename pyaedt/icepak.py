"""This module contains the ``Icepak`` class."""

from __future__ import absolute_import  # noreorder

import csv
import math
import os
import warnings
from collections import OrderedDict

from pyaedt import is_ironpython

if os.name == "posix" and is_ironpython:
    import subprocessdotnet as subprocess
else:
    import subprocess

import re

from pyaedt.application.Analysis3D import FieldAnalysis3D
from pyaedt.generic.configurations import ConfigurationsIcepak
from pyaedt.generic.DataHandlers import _arg2dict
from pyaedt.generic.DataHandlers import random_string
from pyaedt.generic.general_methods import generate_unique_name
from pyaedt.generic.general_methods import open_file
from pyaedt.generic.general_methods import pyaedt_function_handler
from pyaedt.modeler.cad.components_3d import UserDefinedComponent
from pyaedt.modeler.geometry_operators import GeometryOperators
from pyaedt.modules.Boundary import BoundaryObject
from pyaedt.modules.Boundary import NativeComponentObject
from pyaedt.modules.monitor_icepak import Monitor


class Icepak(FieldAnalysis3D):
    """Provides the Icepak application interface.

    This class allows you to connect to an existing Icepak design or create a
    new Icepak design if one does not exist.

    Parameters
    ----------
    projectname : str, optional
        Name of the project to select or the full path to the project
        or AEDTZ archive to open.  The default is ``None``, in which
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
        the active version or latest installed version is  used.
        This parameter is ignored when Script is launched within AEDT.
    non-graphical : bool, optional
        Whether to launch AEDT in non-graphical mode. The default
        is ``False``, in which case AEDT is launched in graphical mode.
        This parameter is ignored when a script is launched within AEDT.
    new_desktop_session : bool, optional
        Whether to launch an instance of AEDT in a new thread, even if
        another instance of the ``specified_version`` is active on the
        machine.  The default is ``True``.
    close_on_exit : bool, optional
        Whether to release AEDT on exit. The default is ``False``.
    student_version : bool, optional
        Whether to open the AEDT student version. The default is ``False``.
        This parameter is ignored when a script is launched within AEDT.
    machine : str, optional
        Machine name to connect the oDesktop session to. This works only in 2022 R2 or later.
        The remote server must be up and running with the command `"ansysedt.exe -grpcsrv portnum"`.
        If the machine is `"localhost"`, the server also starts if not present.
    port : int, optional
        Port number of which to start the oDesktop communication on an already existing server.
        This parameter is ignored when creating a new server. It works only in 2022 R2 or later.
        The remote server must be up and running with the command `"ansysedt.exe -grpcsrv portnum"`.
    aedt_process_id : int, optional
        Process ID for the instance of AEDT to point PyAEDT at. The default is
        ``None``. This parameter is only used when ``new_desktop_session = False``.

    Examples
    --------

    Create an instance of Icepak and connect to an existing Icepak
    design or create a new Icepak design if one does not exist.

    >>> from pyaedt import Icepak
    >>> icepak = Icepak()
    pyaedt INFO: No project is defined. Project ...
    pyaedt INFO: Active design is set to ...

    Create an instance of Icepak and link to a project named
    ``IcepakProject``. If this project does not exist, create one with
    this name.

    >>> icepak = Icepak("IcepakProject")
    pyaedt INFO: Project ...
    pyaedt INFO: Added design ...

    Create an instance of Icepak and link to a design named
    ``IcepakDesign1`` in a project named ``IcepakProject``.

    >>> icepak = Icepak("IcepakProject", "IcepakDesign1")
    pyaedt INFO: Added design 'IcepakDesign1' of type Icepak.

    Create an instance of Icepak and open the specified project,
    which is ``myipk.aedt``.

    >>> icepak = Icepak("myipk.aedt")
    pyaedt INFO: Project myipk has been created.
    pyaedt INFO: No design is present. Inserting a new design.
    pyaedt INFO: Added design ...

    Create an instance of Icepak using the 2021 R1 release and
    open the specified project, which is ``myipk2.aedt``.

    >>> icepak = Icepak(specified_version="2021.2", projectname="myipk2.aedt")
    pyaedt INFO: Project...
    pyaedt INFO: No design is present. Inserting a new design.
    pyaedt INFO: Added design...
    """

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
        FieldAnalysis3D.__init__(
            self,
            "Icepak",
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
        self._monitor = Monitor(self)
        self._configurations = ConfigurationsIcepak(self)

    def __enter__(self):
        return self

    @property
    def problem_type(self):
        """Problem type of the Icepak design. Options are ``"TemperatureAndFlow"``, ``"TemperatureOnly"``,
        and ``"FlowOnly"``.
        """
        return self.design_solutions.problem_type

    @problem_type.setter
    @pyaedt_function_handler()
    def problem_type(self, value="TemperatureAndFlow"):
        self.design_solutions.problem_type = value

    @property
    def existing_analysis_sweeps(self):
        """Existing analysis setups.

        Returns
        -------
        list of str
            List of all analysis setups in the design.

        """
        setup_list = self.existing_analysis_setups
        sweep_list = []
        s_type = self.solution_type
        for el in setup_list:
            sweep_list.append(el + " : " + s_type)
        return sweep_list

    @property
    def monitor(self):
        """Property to handle monitor objects.

        Returns
        -------
        :class:`pyaedt.modules.monitor_icepak.Monitor`
        """
        self._monitor._delete_removed_monitors()  # force update. some operations may delete monitors
        return self._monitor

    @pyaedt_function_handler()
    def assign_grille(
        self,
        air_faces,
        free_loss_coeff=True,
        free_area_ratio=0.8,
        resistance_type=0,
        external_temp="AmbientTemp",
        expternal_pressure="AmbientPressure",
        x_curve=["0", "1", "2"],
        y_curve=["0", "1", "2"],
    ):
        """Assign grille to a face or list of faces.

        Parameters
        ----------
        air_faces : str, list
            List of face names.
        free_loss_coeff : bool
            Whether to use the free loss coefficient. The default is ``True``. If ``False``,
            the free loss coefficient is not used.
        free_area_ratio : float, str
            Free loss coefficient value. The default is ``0.8``.
        resistance_type : int, optional
            Type of the resistance. Options are:

            - ``0`` for ``"Perforated Thin Vent"``
            - ``1`` for ``"Circular Metal Wire Screen"``
            - ``2`` for ``"Two-Plane Screen Cyl. Bars"``

            The default is ``0`` for ``"Perforated Thin Vent"``.
        external_temp : str, optional
            External temperature. The default is ``"AmbientTemp"``.
        expternal_pressure : str, optional
            External pressure. The default is ``"AmbientPressure"``.
        x_curve : list, optional
            List of X curves in m_per_sec. The default is ``["0", "1", "2"]``.
        y_curve : list
            List of Y curves in n_per_meter_q. The default is ``["0", "1", "2"]``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object when successful or ``None`` when failed.

        References
        ----------

        >>> oModule.AssignGrilleBoundary
        """
        boundary_name = generate_unique_name("Grille")

        self.modeler.create_face_list(air_faces, "boundary_faces" + boundary_name)
        props = {}
        air_faces = self.modeler.convert_to_selections(air_faces, True)

        props["Faces"] = air_faces
        if free_loss_coeff:
            props["Pressure Loss Type"] = "Coeff"
            props["Free Area Ratio"] = str(free_area_ratio)
            props["External Rad. Temperature"] = external_temp
            props["External Total Pressure"] = expternal_pressure

        else:
            props["Pressure Loss Type"] = "Curve"
            props["External Rad. Temperature"] = external_temp
            props["External Total Pressure"] = expternal_pressure

        props["X"] = x_curve
        props["Y"] = y_curve
        bound = BoundaryObject(self, boundary_name, props, "Grille")
        if bound.create():
            self.boundaries.append(bound)
            self.logger.info("Grille Assigned")
            return bound
        return None

    @pyaedt_function_handler()
    def assign_openings(self, air_faces):
        """Assign openings to a list of faces.

        Parameters
        ----------
        air_faces : list
            List of face names.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object when successful or ``None`` when failed.

        References
        ----------

        >>> oModule.AssignOpeningBoundary

        Examples
        --------

        Create an opening boundary for the faces of the ``"USB_GND"`` object.

        >>> faces = icepak.modeler["USB_GND"].faces
        >>> face_names = [face.id for face in faces]
        >>> boundary = icepak.assign_openings(face_names)
        pyaedt INFO: Face List boundary_faces created
        pyaedt INFO: Opening Assigned
        """
        boundary_name = generate_unique_name("Opening")
        self.modeler.create_face_list(air_faces, "boundary_faces" + boundary_name)
        props = {}
        air_faces = self.modeler.convert_to_selections(air_faces, True)

        props["Faces"] = air_faces
        props["Temperature"] = "AmbientTemp"
        props["External Rad. Temperature"] = "AmbientRadTemp"
        props["Inlet Type"] = "Pressure"
        props["Total Pressure"] = "AmbientPressure"
        bound = BoundaryObject(self, boundary_name, props, "Opening")
        if bound.create():
            self.boundaries.append(bound)
            self.logger.info("Opening Assigned")
            return bound
        return None

    @pyaedt_function_handler()
    def assign_2way_coupling(
        self, setup_name=None, number_of_iterations=2, continue_ipk_iterations=True, ipk_iterations_per_coupling=20
    ):
        """Assign two-way coupling to a setup.

        Parameters
        ----------
        setup_name : str, optional
            Name of the setup. The default is ``None``, in which case the active setup is used.
        number_of_iterations : int, optional
            Number of iterations. The default is ``2``.
        continue_ipk_iterations : bool, optional
           Whether to continue Icepak iterations. The default is ``True``.
        ipk_iterations_per_coupling : int, optional
            Additional iterations per coupling. The default is ``20``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oModule.AddTwoWayCoupling

        Examples
        --------

        >>> icepak.assign_2way_coupling("Setup1", 1, True, 10)
        True

        """
        if not setup_name:
            if self.setups:
                setup_name = self.setups[0].name
            else:
                self.logger.error("No setup is defined.")
                return False
        self.oanalysis.AddTwoWayCoupling(
            setup_name,
            [
                "NAME:Options",
                "NumCouplingIters:=",
                number_of_iterations,
                "ContinueIcepakIterations:=",
                continue_ipk_iterations,
                "IcepakIterationsPerCoupling:=",
                ipk_iterations_per_coupling,
            ],
        )
        return True

    @pyaedt_function_handler()
    def create_source_blocks_from_list(self, list_powers, assign_material=True, default_material="Ceramic_material"):
        """Assign to a box in Icepak the sources that come from the CSV file.

        Assignment is made by name.

        Parameters
        ----------
        list_powers : list
            List of input powers. It is a list of lists. For example,
            ``[["Obj1", 1], ["Obj2", 3]]``. The list can contain multiple
            columns for power inputs.
        assign_material : bool, optional
            Whether to assign a material. The default is ``True``.
        default_material : str, optional
            Default material to assign when ``assign_material=True``.
            The default is ``"Ceramic_material"``.

        Returns
        -------
        list of :class:`pyaedt.modules.Boundary.BoundaryObject`
            List of boundaries inserted.

        References
        ----------

        >>> oModule.AssignBlockBoundary

        Examples
        --------

        Create block boundaries from each box in the list.

        >>> box1 = icepak.modeler.create_box([1, 1, 1], [3, 3, 3], "BlockBox1", "copper")
        >>> box2 = icepak.modeler.create_box([2, 2, 2], [4, 4, 4], "BlockBox2", "copper")
        >>> blocks = icepak.create_source_blocks_from_list([["BlockBox1", 2], ["BlockBox2", 4]])
        pyaedt INFO: Block on ...
        >>> blocks[1].props
        {'Objects': ['BlockBox1'], 'Block Type': 'Solid', 'Use External Conditions': False, 'Total Power': '2W'}
        >>> blocks[3].props
        {'Objects': ['BlockBox2'], 'Block Type': 'Solid', 'Use External Conditions': False, 'Total Power': '4W'}
        """
        oObjects = self.modeler.solid_names
        listmcad = []
        num_power = None
        for row in list_powers:
            if not num_power:
                num_power = len(row) - 1
                self["P_index"] = 0
            if row[0] in oObjects:
                listmcad.append(row)
                if num_power > 1:
                    self[row[0] + "_P"] = str(row[1:])
                    out = self.create_source_block(row[0], row[0] + "_P[P_index]", assign_material, default_material)

                else:
                    out = self.create_source_block(row[0], str(row[1]) + "W", assign_material, default_material)
                if out:
                    listmcad.append(out)

        return listmcad

    @pyaedt_function_handler()
    def create_source_block(
        self, object_name, input_power, assign_material=True, material_name="Ceramic_material", use_object_for_name=True
    ):
        """Create a source block for an object.

        Parameters
        ----------
        object_name : str, list
            Name of the object.
        input_power : str or var
            Input power.
        assign_material : bool, optional
            Whether to assign a material. The default is ``True``.
        material_name :
            Material to assign if ``assign_material=True``. The default is ``"Ceramic_material"``.
        use_object_for_name : bool, optional
            Whether to use the object name for the source block name. The default is ``True``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object when successful or ``None`` when failed.

        References
        ----------

        >>> oModule.AssignBlockBoundary

        Examples
        --------

        >>> box = icepak.modeler.create_box([5, 5, 5], [1, 2, 3], "BlockBox3", "copper")
        >>> block = icepak.create_source_block("BlockBox3", "1W", False)
        pyaedt INFO: Block on ...
        >>> block.props
        {'Objects': ['BlockBox3'], 'Block Type': 'Solid', 'Use External Conditions': False, 'Total Power': '1W'}

        """
        if assign_material:
            if isinstance(object_name, list):
                for el in object_name:
                    self.modeler[el].material_name = material_name
            else:
                self.modeler[object_name].material_name = material_name
        props = {}
        if not isinstance(object_name, list):
            object_name = [object_name]
        object_name = self.modeler.convert_to_selections(object_name, True)
        props["Objects"] = object_name

        props["Block Type"] = "Solid"
        props["Use External Conditions"] = False
        props["Total Power"] = input_power
        if use_object_for_name:
            boundary_name = object_name[0]
        else:
            boundary_name = generate_unique_name("Block")

        bound = BoundaryObject(self, boundary_name, props, "Block")
        if bound.create():
            self.boundaries.append(bound)
            self.logger.info("Block on {} with {} power created correctly.".format(object_name, input_power))
            return bound
        return None

    @pyaedt_function_handler()
    def create_conduting_plate(
        self,
        face_id,
        thermal_specification,
        thermal_dependent_dataset=None,
        input_power="0W",
        radiate_low=False,
        low_surf_material="Steel-oxidised-surface",
        radiate_high=False,
        high_surf_material="Steel-oxidised-surface",
        shell_conduction=False,
        thickness="1mm",
        solid_material="Al-Extruded",
        thermal_conductance="0W_per_Cel",
        thermal_resistance="0Kel_per_W",
        thermal_impedance="0celm2_per_w",
        bc_name=None,
    ):
        """Add a conductive plate thermal assignment on a face.

        Parameters
        ----------
        face_id : int or str
            If int, Face ID. If str, object name.
        thermal_specification : str
            Select what thermal specification is to be applied. The possible choices are ``"Thickness"``,
            ``"Conductance"``, ``"Thermal Impedance"`` and ``"Thermal Resistance"``
        thermal_dependent_dataset : str, optional
            Name of the dataset if a thermal dependent power source is to be assigned. The default is ``None``.
        input_power : str, float, or int, optional
            Input power. The default is ``"0W"``. Ignored if thermal_dependent_dataset is set
        radiate_low : bool, optional
            Whether to enable radiation on the lower face. The default is ``False``.
        low_surf_material : str, optional
            Low surface material. The default is ``"Steel-oxidised-surface"``.
        radiate_high : bool, optional
            Whether to enable radiation on the higher face. The default is ``False``.
        high_surf_material : str, optional
            High surface material. The default is ``"Steel-oxidised-surface"``.
        shell_conduction : str, optional
            Whether to enable shell conduction. The default is ``False``.
        thickness : str, optional
            Thickness value, relevant only if ``thermal_specification="Thickness"``. The default is ``"1mm"``.
        thermal_conductance : str, optional
            Thermal Conductance value, relevant only if ``thermal_specification="Conductance"``.
            The default is ``"0W_per_Cel"``.
        thermal_resistance : str, optional
            Thermal resistance value, relevant only if ``thermal_specification="Thermal Resistance"``.
            The default is ``"0Kel_per_W"``.
        thermal_impedance : str, optional
            Thermal impedance value, relevant only if ``thermal_specification="Thermal Impedance"``.
            The default is ``"0celm2_per_w"``.
        solid_material : str, optional
            Material type for the wall. The default is ``"Al-Extruded"``.
        bc_name : str, optional
            Name of the plate. The default is ``None``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object when successful or ``None`` when failed.

        """
        if not bc_name:
            bc_name = generate_unique_name("Source")
        props = {}
        if isinstance(face_id, int):
            props["Faces"] = [face_id]
        elif isinstance(face_id, str):
            props["Objects"] = [face_id]
        if radiate_low:
            props["LowSide"] = OrderedDict(
                {"Radiate": True, "RadiateTo": "AllObjects", "Surface Material": low_surf_material}
            )
        else:
            props["LowSide"] = OrderedDict({"Radiate": False})
        if radiate_high:
            props["HighSide"] = OrderedDict(
                {"Radiate": True, "RadiateTo": "AllObjects - High", "Surface Material - High": high_surf_material}
            )
        else:
            props["HighSide"] = OrderedDict({"Radiate": False})
        props["Thermal Specification"] = thermal_specification
        props["Thickness"] = thickness
        props["Solid Material"] = solid_material
        props["Conductance"] = thermal_conductance
        props["Thermal Resistance"] = thermal_resistance
        props["Thermal Impedance"] = thermal_impedance
        if thermal_dependent_dataset is None:
            props["Total Power"] = input_power
        else:
            props["Total Power Variation Data"] = OrderedDict(
                {
                    "Variation Type": "Temp Dep",
                    "Variation Function": "Piecewise Linear",
                    "Variation Value": '["1W", "pwl({},Temp)"]'.format(thermal_dependent_dataset),
                }
            )
        props["Shell Conduction"] = shell_conduction
        bound = BoundaryObject(self, bc_name, props, "Conducting Plate")
        if bound.create():
            self.boundaries.append(bound)
            return bound

    @pyaedt_function_handler()
    def create_source_power(
        self,
        face_id,
        thermal_dependent_dataset=None,
        input_power=None,
        thermal_condtion="Total Power",
        surface_heat="0irrad_W_per_m2",
        temperature="AmbientTemp",
        radiate=False,
        source_name=None,
    ):
        """Create a source power for a face.

        Parameters
        ----------
        face_id : int or str
            If int, Face ID. If str, object name.
        thermal_dependent_dataset : str, optional
            Name of the dataset if a thermal dependent power source is to be assigned. The default is ``None``.
        input_power : str, float, or int, optional
            Input power. The default is ``"0W"``.
        thermal_condtion : str, optional
            Thermal condition. The default is ``"Total Power"``.
        surface_heat : str, optional
            Surface heat. The default is ``"0irrad_W_per_m2"``.
        temperature : str, optional
            Type of the temperature. The default is ``"AmbientTemp"``.
        radiate : bool, optional
            Whether to enable radiation. The default is ``False``.
        source_name : str, optional
            Name of the source. The default is ``None``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object when successful or ``None`` when failed.

        References
        ----------

        >>> oModule.AssignSourceBoundary

        Examples
        --------

        Create two source boundaries from one box, one on the top face and one on the bottom face.

        >>> box = icepak.modeler.create_box([0, 0, 0], [20, 20, 20], name="SourceBox")
        >>> source1 = icepak.create_source_power(box.top_face_z.id, input_power="2W")
        >>> source1.props["Total Power"]
        '2W'
        >>> source2 = icepak.create_source_power(box.bottom_face_z.id,
        ...                                      thermal_condtion="Fixed Temperature",
        ...                                      temperature="28cel")
        >>> source2.props["Temperature"]
        '28cel'

        """
        if input_power == 0:
            input_power = "0W"
        if not bool(input_power) ^ bool(thermal_dependent_dataset):
            self.logger.error("Please assigned one input between ``thermal_dependent_dataset`` and  ``input_power``")
        if not source_name:
            source_name = generate_unique_name("Source")
        props = {}
        if isinstance(face_id, int):
            props["Faces"] = [face_id]
        elif isinstance(face_id, str):
            props["Objects"] = [face_id]
        props["Thermal Condition"] = thermal_condtion
        if thermal_dependent_dataset is None:
            props["Total Power"] = input_power
        else:
            props["Total Power Variation Data"] = OrderedDict(
                {
                    "Variation Type": "Temp Dep",
                    "Variation Function": "Piecewise Linear",
                    "Variation Value": '["1W", "pwl({},Temp)"]'.format(thermal_dependent_dataset),
                }
            )
        props["Surface Heat"] = surface_heat
        props["Temperature"] = temperature
        props["Radiation"] = OrderedDict({"Radiate": radiate})
        bound = BoundaryObject(self, source_name, props, "SourceIcepak")
        if bound.create():
            self.boundaries.append(bound)
            return bound

    @pyaedt_function_handler()
    def create_network_block(
        self,
        object_name,
        power,
        rjc,
        rjb,
        gravity_dir,
        top,
        assign_material=True,
        default_material="Ceramic_material",
        use_object_for_name=True,
    ):
        """Create a network block.

        .. deprecated:: 0.6.27
            This method will be replaced by `create_two_resistor_network_block`.

        Parameters
        ----------
        object_name : str
            Name of the object to create the block for.
        power : str or var
            Input power.
        rjc :
            RJC value.
        rjb :
            RJB value.
        gravity_dir :
            Gravity direction from -X to +Z. Options are ``0`` to ``5``.
        top :
            Board bounding value in millimeters of the top face.
        assign_material : bool, optional
            Whether to assign a material. The default is ``True``.
        default_material : str, optional
            Default material if ``assign_material=True``. The default is ``"Ceramic_material"``.
        use_object_for_name : bool, optional
             The default is ``True``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        References
        ----------

        >>> oModule.AssignNetworkBoundary

        Examples
        --------

        >>> box = icepak.modeler.create_box([4, 5, 6], [5, 5, 5], "NetworkBox1", "copper")
        >>> block = icepak.create_network_block("NetworkBox1", "2W", 20, 10, icepak.GravityDirection.ZNeg, 1.05918)
        >>> block.props["Nodes"]["Internal"][0]
        '2W'
        """
        warnings.warn(
            "This method is deprecated in 0.6.27. Please use create_two_resistor_network_block", DeprecationWarning
        )
        if object_name in self.modeler.object_names:
            if gravity_dir > 2:
                gravity_dir = gravity_dir - 3
            faces_dict = self.modeler[object_name].faces
            faceCenter = {}
            for f in faces_dict:
                faceCenter[f.id] = f.center
            fcmax = -1e9
            fcmin = 1e9
            fcrjc = None
            fcrjb = None
            for fc in faceCenter:
                fc1 = faceCenter[fc]
                if fc1[gravity_dir] < fcmin:
                    fcmin = fc1[gravity_dir]
                    fcrjb = int(fc)
                if fc1[gravity_dir] > fcmax:
                    fcmax = fc1[gravity_dir]
                    fcrjc = int(fc)
            if fcmax < float(top):
                app = fcrjc
                fcrjc = fcrjb
                fcrjb = app
            if assign_material:
                self.modeler[object_name].material_name = default_material
            props = {}
            if use_object_for_name:
                boundary_name = object_name
            else:
                boundary_name = generate_unique_name("Block")
            props["Faces"] = [fcrjc, fcrjb]
            props["Nodes"] = OrderedDict(
                {
                    "Face" + str(fcrjc): [fcrjc, "NoResistance"],
                    "Face" + str(fcrjb): [fcrjb, "NoResistance"],
                    "Internal": [power],
                }
            )
            props["Links"] = OrderedDict(
                {
                    "Link1": ["Face" + str(fcrjc), "Internal", "R", str(rjc) + "cel_per_w"],
                    "Link2": ["Face" + str(fcrjb), "Internal", "R", str(rjb) + "cel_per_w"],
                }
            )
            props["SchematicData"] = OrderedDict({})
            bound = BoundaryObject(self, boundary_name, props, "Network")
            if bound.create():
                self.boundaries.append(bound)
                self.modeler[object_name].solve_inside = False
                return bound
            return None

    @pyaedt_function_handler()
    def create_network_blocks(
        self, input_list, gravity_dir, top, assign_material=True, default_material="Ceramic_material"
    ):
        """Create network blocks from CSV files.

        Parameters
        ----------
        input_list : list
            List of sources with inputs ``rjc``, ``rjb``, and ``power``.
            For example, ``[[Objname1, rjc, rjb, power1, power2, ...], [Objname2, rjc2, rbj2, power1, power2, ...]]``.
        gravity_dir : int
            Gravity direction from -X to +Z. Options are ``0`` to ``5``.
        top :
            Board bounding value in millimeters of the top face.
        assign_material : bool, optional
            Whether to assign a material. The default is ``True``.
        default_material : str, optional
            Default material if ``assign_material=True``. The default is ``"Ceramic_material"``.

        Returns
        -------
        list of :class:`pyaedt.modules.Boundary.BoundaryObject`
            List of boundary objects created.

        References
        ----------

        >>> oModule.AssignNetworkBoundary

        Examples
        --------

        Create network boundaries from each box in the list.

        >>> box1 = icepak.modeler.create_box([1, 2, 3], [10, 10, 10], "NetworkBox2", "copper")
        >>> box2 = icepak.modeler.create_box([4, 5, 6], [5, 5, 5], "NetworkBox3", "copper")
        >>> blocks = icepak.create_network_blocks([["NetworkBox2", 20, 10, 3], ["NetworkBox3", 4, 10, 2]],
        ...                                        icepak.GravityDirection.ZNeg, 1.05918, False)
        >>> blocks[0].props["Nodes"]["Internal"]
        ['3W']
        """
        objs = self.modeler.solid_names
        countpow = len(input_list[0]) - 3
        networks = []
        for row in input_list:
            if row[0] in objs:
                if countpow > 1:
                    self[row[0] + "_P"] = str(row[3:])
                    self["P_index"] = 0
                    out = self.create_network_block(
                        row[0],
                        row[0] + "_P[P_index]",
                        row[1],
                        row[2],
                        gravity_dir,
                        top,
                        assign_material,
                        default_material,
                    )
                else:
                    if not row[3]:
                        pow = "0W"
                    else:
                        pow = str(row[3]) + "W"
                    out = self.create_network_block(
                        row[0], pow, row[1], row[2], gravity_dir, top, assign_material, default_material
                    )
                if out:
                    networks.append(out)
        return networks

    @pyaedt_function_handler()
    def assign_surface_monitor(self, face_name, monitor_type="Temperature", monitor_name=None):
        """Assign a surface monitor.

        Parameters
        ----------
        face_name : str
            Name of the face.
        monitor_type : str, optional
            Type of the monitor.  The default is ``"Temperature"``.
        monitor_name : str, optional
            Name of the monitor. The default is ``None``, in which case
            the default name is used.

        Returns
        -------
        str
            Monitor name when successful, ``False`` when failed.

        References
        ----------

        >>> oModule.AssignFaceMonitor

        Examples
        --------

        Create a rectangle named ``"Surface1"`` and assign a temperature monitor to that surface.

        >>> surface = icepak.modeler.create_rectangle(icepak.PLANE.XY,
        ...                                           [0, 0, 0], [10, 20], name="Surface1")
        >>> icepak.assign_surface_monitor("Surface1", monitor_name="monitor")
        'monitor'
        """
        return self._monitor.assign_surface_monitor(face_name, monitor_quantity=monitor_type, monitor_name=monitor_name)

    @pyaedt_function_handler()
    def assign_point_monitor(self, point_position, monitor_type="Temperature", monitor_name=None):
        """Create and assign a point monitor.

        Parameters
        ----------
        point_position : list
            List of the ``[x, y, z]`` coordinates for the point.
        monitor_type : str, optional
            Type of the monitor. The default is ``"Temperature"``.
        monitor_name : str, optional
            Name of the monitor. The default is ``None``, in which case
            the default name is used.

        Returns
        -------
        str
            Monitor name when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.AssignPointMonitor

        Examples
        --------
        Create a temperature monitor at the point ``[1, 1, 1]``.

        >>> icepak.assign_point_monitor([1, 1, 1], monitor_name="monitor1")
        'monitor1'

        """
        return self._monitor.assign_point_monitor(
            point_position, monitor_quantity=monitor_type, monitor_name=monitor_name
        )

    @pyaedt_function_handler()
    def assign_point_monitor_in_object(self, name, monitor_type="Temperature", monitor_name=None):
        """Assign a point monitor in the centroid of a specific object.

        Parameters
        ----------
        name : str
            Name of the object to assign monitor point to.
        monitor_type : str, optional
            Type of the monitor.  The default is ``"Temperature"``.
        monitor_name : str, optional
            Name of the monitor. The default is ``None``, in which case
            the default name is used.

        Returns
        -------
        str
            Monitor name when successful, ``False`` when failed.

        References
        ----------

        >>> oModule.AssignPointMonitor

        Examples
        --------

        Create a box named ``"BlockBox1"`` and assign a temperature monitor point to that object.

        >>> box = icepak.modeler.create_box([1, 1, 1], [3, 3, 3], "BlockBox1", "copper")
        >>> icepak.assign_point_monitor(box.name, monitor_name="monitor2")
        "'monitor2'
        """
        return self._monitor.assign_point_monitor_in_object(
            name, monitor_quantity=monitor_type, monitor_name=monitor_name
        )

    @pyaedt_function_handler()
    def assign_block_from_sherlock_file(self, csv_name):
        """Assign block power to components based on a CSV file from Sherlock.

        Parameters
        ----------
        csv_name : str
            Name of the CSV file.

        Returns
        -------
        type
            Total power applied.

        References
        ----------

        >>> oModule.AssignBlockBoundary
        """
        with open_file(csv_name) as csvfile:
            csv_input = csv.reader(csvfile)
            component_header = next(csv_input)
            data = list(csv_input)
            k = 0
            component_data = {}
            for el in component_header:
                component_data[el] = [i[k] for i in data]
                k += 1
        total_power = 0
        i = 0
        all_objects = self.modeler.object_names
        for power in component_data["Applied Power (W)"]:
            try:
                float(power)
                if "COMP_" + component_data["Ref Des"][i] in all_objects:
                    status = self.create_source_block(
                        "COMP_" + component_data["Ref Des"][i], str(power) + "W", assign_material=False
                    )
                    if not status:
                        self.logger.warning(
                            "Warning. Block %s skipped with %sW power.", component_data["Ref Des"][i], power
                        )
                    else:
                        total_power += float(power)
                elif component_data["Ref Des"][i] in all_objects:
                    status = self.create_source_block(
                        component_data["Ref Des"][i], str(power) + "W", assign_material=False
                    )
                    if not status:
                        self.logger.warning(
                            "Warning. Block %s skipped with %sW power.", component_data["Ref Des"][i], power
                        )
                    else:
                        total_power += float(power)
            except:
                pass
            i += 1
        self.logger.info("Blocks inserted with total power %sW.", total_power)
        return total_power

    @pyaedt_function_handler()
    def assign_priority_on_intersections(self, component_prefix="COMP_"):
        """Validate an Icepak design.

        If there are intersections, priorities are automatically applied to overcome simulation issues.

        Parameters
        ----------
        component_prefix : str, optional
            Component prefix to search for. The default is ``"COMP_"``.

        Returns
        -------
        bool
             ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.UpdatePriorityList
        """
        temp_log = os.path.join(self.working_directory, "validation.log")
        validate = self.odesign.ValidateDesign(temp_log)
        self.save_project()
        i = 2
        if validate == 0:
            priority_list = []
            with open_file(temp_log, "r") as f:
                lines = f.readlines()
                for line in lines:
                    if "[error]" in line and component_prefix in line and "intersect" in line:
                        id1 = line.find(component_prefix)
                        id2 = line[id1:].find('"')
                        name = line[id1 : id1 + id2]
                        if name not in priority_list:
                            priority_list.append(name)
            self.logger.info("{} Intersections have been found. Applying Priorities".format(len(priority_list)))
            for objname in priority_list:
                self.mesh.add_priority(1, [objname], priority=i)
                i += 1
        return True

    @pyaedt_function_handler()
    def find_top(self, gravityDir):
        """Find the top location of the layout given a gravity.

        Parameters
        ----------
        gravityDir :
            Gravity direction from -X to +Z. Options are ``0`` to ``5``.

        Returns
        -------
        float
            Top position.

        References
        ----------

        >>> oEditor.GetModelBoundingBox
        """
        dirs = ["-X", "+X", "-Y", "+Y", "-Z", "+Z"]
        for dir in dirs:
            argsval = ["NAME:" + dir + " Padding Data", "Value:=", "0"]
            args = [
                "NAME:AllTabs",
                [
                    "NAME:Geometry3DCmdTab",
                    ["NAME:PropServers", "Region:CreateRegion:1"],
                    ["NAME:ChangedProps", argsval],
                ],
            ]
            self.modeler.oeditor.ChangeProperty(args)
        oBoundingBox = self.modeler.get_model_bounding_box()
        if gravityDir < 3:
            return oBoundingBox[gravityDir + 3]
        else:
            return oBoundingBox[gravityDir - 3]

    @pyaedt_function_handler()
    def create_parametric_fin_heat_sink(
        self,
        hs_height=100,
        hs_width=100,
        hs_basethick=10,
        pitch=20,
        thick=10,
        length=40,
        height=40,
        draftangle=0,
        patternangle=10,
        separation=5,
        symmetric=True,
        symmetric_separation=20,
        numcolumn_perside=2,
        vertical_separation=10,
        matname="Al-Extruded",
        center=[0, 0, 0],
        plane_enum=0,
        rotation=0,
        tolerance=1e-3,
    ):
        """Create a parametric heat sink.

        Parameters
        ----------
        hs_height : int, optional
            Height of the heat sink. The default is ``100``.
        hs_width : int, optional
            Width of the heat sink. The default is ``100``.
        hs_basethick : int, optional
            Thickness of the heat sink base. The default is ``10``.
        pitch : optional
            Pitch of the heat sink. The default is ``10``.
        thick : optional
            Thickness of the heat sink. The default is ``10``.
        length : optional
            Length of the heat sink. The default is ``40``.
        height : optional
            Height of the heat sink. The default is ``40``.
        draftangle : int, float, optional
            Draft angle in degrees. The default is ``0``.
        patternangle : int, float, optional
            Pattern angle in degrees. The default is ``10``.
        separation : optional
            The default is ``5``.
        symmetric : bool, optional
            Whether the heat sink is symmetric. The default is ``True``.
        symmetric_separation : optional
            The default is ``20``.
        numcolumn_perside : int, optional
            Number of columns per side. The default is ``2``.
        vertical_separation : optional
            The default is ``10``.
        matname : str, optional
            Name of the material. The default is ``Al-Extruded``.
        center : list, optional
           List of ``[x, y, z]`` coordinates for the center of
           the heatsink. The default is ``[0, 0, 0]``.
        plane_enum : str, int, optional
            Plane for orienting the heat sink.
            :class:`pyaedt.constants.PLANE` Enumerator can be used as input.
            The default is ``0``.
        rotation : int, float, optional
            The default is ``0``.
        tolerance : int, float, optional
            Tolerance value. The default is ``0.001``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------
        Create a symmetric fin heat sink.

        >>> from pyaedt import Icepak
        >>> icepak = Icepak()
        >>> icepak.insert_design("Heat_Sink_Example")
        >>> icepak.create_parametric_fin_heat_sink(draftangle=1.5, patternangle=8, numcolumn_perside=3,
        ...                                        vertical_separation=5.5, matname="Steel", center=[10, 0, 0],
        ...                                        plane_enum=icepak.PLANE.XY, rotation=45, tolerance=0.005)

        """
        all_objs = self.modeler.object_names
        self["FinPitch"] = self.modeler._arg_with_dim(pitch)
        self["FinThickness"] = self.modeler._arg_with_dim(thick)
        self["FinLength"] = self.modeler._arg_with_dim(length)
        self["FinHeight"] = self.modeler._arg_with_dim(height)
        self["DraftAngle"] = draftangle
        self["PatternAngle"] = patternangle
        self["FinSeparation"] = self.modeler._arg_with_dim(separation)
        self["VerticalSeparation"] = self.modeler._arg_with_dim(vertical_separation)
        self["HSHeight"] = self.modeler._arg_with_dim(hs_height)
        self["HSWidth"] = self.modeler._arg_with_dim(hs_width)
        self["HSBaseThick"] = self.modeler._arg_with_dim(hs_basethick)
        if numcolumn_perside > 1:
            self["NumColumnsPerSide"] = numcolumn_perside
        if symmetric:
            self["SymSeparation"] = self.modeler._arg_with_dim(symmetric_separation)
        self["Tolerance"] = self.modeler._arg_with_dim(tolerance)

        self.modeler.create_box(
            ["-HSWidth/200", "-HSHeight/200", "-HSBaseThick"],
            ["HSWidth*1.01", "HSHeight*1.01", "HSBaseThick+Tolerance"],
            "HSBase",
            matname,
        )
        fin_line = []
        fin_line.append(self.Position(0, 0, 0))
        fin_line.append(self.Position(0, "FinThickness", 0))
        fin_line.append(self.Position("FinLength", "FinThickness + FinLength*sin(PatternAngle*3.14/180)", 0))
        fin_line.append(self.Position("FinLength", "FinLength*sin(PatternAngle*3.14/180)", 0))
        fin_line.append(self.Position(0, 0, 0))
        self.modeler.create_polyline(fin_line, cover_surface=True, name="Fin")
        fin_line2 = []
        fin_line2.append(self.Position(0, "sin(DraftAngle*3.14/180)*FinThickness", "FinHeight"))
        fin_line2.append(self.Position(0, "FinThickness-sin(DraftAngle*3.14/180)*FinThickness", "FinHeight"))
        fin_line2.append(
            self.Position(
                "FinLength",
                "FinThickness + FinLength*sin(PatternAngle*3.14/180)-sin(DraftAngle*3.14/180)*FinThickness",
                "FinHeight",
            )
        )
        fin_line2.append(
            self.Position(
                "FinLength", "FinLength*sin(PatternAngle*3.14/180)+sin(DraftAngle*3.14/180)*FinThickness", "FinHeight"
            )
        )
        fin_line2.append(self.Position(0, "sin(DraftAngle*3.14/180)*FinThickness", "FinHeight"))
        self.modeler.create_polyline(fin_line2, cover_surface=True, name="Fin_top")
        self.modeler.connect(["Fin", "Fin_top"])
        self.modeler["Fin"].material_name = matname
        num = int((hs_width * 1.25 / (separation + thick)) / (max(1 - math.sin(patternangle * 3.14 / 180), 0.1)))
        self.modeler.move("Fin", self.Position(0, "-FinSeparation-FinThickness", 0))
        self.modeler.duplicate_along_line("Fin", self.Position(0, "FinSeparation+FinThickness", 0), num, True)
        all_names = self.modeler.object_names
        list = [i for i in all_names if "Fin" in i]
        if numcolumn_perside > 0:
            self.modeler.duplicate_along_line(
                list,
                self.Position("FinLength+VerticalSeparation", "FinLength*sin(PatternAngle*3.14/180)", 0),
                "NumColumnsPerSide",
                True,
            )

        all_names = self.modeler.object_names
        list = [i for i in all_names if "Fin" in i]
        self.modeler.split(list, self.PLANE.ZX, "PositiveOnly")
        all_names = self.modeler.object_names
        list = [i for i in all_names if "Fin" in i]
        self.modeler.create_coordinate_system(self.Position(0, "HSHeight", 0), mode="view", view="XY", name="TopRight")
        self.modeler.set_working_coordinate_system("TopRight")
        self.modeler.split(list, self.PLANE.ZX, "NegativeOnly")

        if symmetric:

            self.modeler.create_coordinate_system(
                self.Position("(HSWidth-SymSeparation)/2", 0, 0),
                mode="view",
                view="XY",
                name="CenterRightSep",
                reference_cs="TopRight",
            )

            self.modeler.split(list, self.PLANE.YZ, "NegativeOnly")
            self.modeler.create_coordinate_system(
                self.Position("SymSeparation/2", 0, 0),
                mode="view",
                view="XY",
                name="CenterRight",
                reference_cs="CenterRightSep",
            )
            self.modeler.duplicate_and_mirror(list, self.Position(0, 0, 0), self.Position(1, 0, 0))
            center_line = []
            center_line.append(self.Position("-SymSeparation", "Tolerance", "-Tolerance"))
            center_line.append(self.Position("SymSeparation", "Tolerance", "-Tolerance"))
            center_line.append(self.Position("VerticalSeparation", "-HSHeight-Tolerance", "-Tolerance"))
            center_line.append(self.Position("-VerticalSeparation", "-HSHeight-Tolerance", "-Tolerance"))
            center_line.append(self.Position("-SymSeparation", "Tolerance", "-Tolerance"))
            self.modeler.create_polyline(center_line, cover_surface=True, name="Center")
            self.modeler.thicken_sheet("Center", "-FinHeight-2*Tolerance")
            all_names = self.modeler.object_names
            list = [i for i in all_names if "Fin" in i]
            self.modeler.subtract(list, "Center", False)
        else:
            self.modeler.create_coordinate_system(
                self.Position("HSWidth", 0, 0), mode="view", view="XY", name="BottomRight", reference_cs="TopRight"
            )
            self.modeler.split(list, self.PLANE.YZ, "NegativeOnly")
        all_objs2 = self.modeler.object_names
        list_to_move = [i for i in all_objs2 if i not in all_objs]
        center[0] -= hs_width / 2
        center[1] -= hs_height / 2
        center[2] += hs_basethick
        self.modeler.set_working_coordinate_system("Global")
        self.modeler.move(list_to_move, center)
        if plane_enum == self.PLANE.XY:
            self.modeler.rotate(list_to_move, self.AXIS.X, rotation)
        elif plane_enum == self.PLANE.ZX:
            self.modeler.rotate(list_to_move, self.AXIS.X, 90)
            self.modeler.rotate(list_to_move, self.AXIS.Y, rotation)
        elif plane_enum == self.PLANE.YZ:
            self.modeler.rotate(list_to_move, self.AXIS.Y, 90)
            self.modeler.rotate(list_to_move, self.AXIS.Z, rotation)
        self.modeler.unite(list_to_move)
        self.modeler[list_to_move[0]].name = "HeatSink1"
        return True

    @pyaedt_function_handler()
    def edit_design_settings(
        self,
        gravityDir=0,
        ambtemp=20,
        performvalidation=False,
        CheckLevel="None",
        defaultfluid="air",
        defaultsolid="Al-Extruded",
        export_monitor=False,
        export_directory=os.getcwd(),
    ):
        """Update the main settings of the design.

        Parameters
        ----------
        gravityDir : int, optional
            Gravity direction from -X to +Z. Options are ``0`` to ``5``.
            The default is ``0``.
        ambtemp : optional
            Ambient temperature. The default is ``22``.
        performvalidation : bool, optional
            Whether to perform validation. The default is ``False``.
        CheckLevel : str, optional
            Level of check to perform during validation. The default
            is ``"None"``.
        defaultfluid : str, optional
            Default fluid material. The default is ``"air"``.
        defaultsolid : str, optional
            Default solid material. The default is ``"Al-Extruded"``.
        export_monitor : bool, optional
            Whether to use the default export directory for monitor point data.
            The default value is ``False``.
        export_directory : str, optional
            Default export directory for monitor point data. The default value is the current working directory.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oDesign.SetDesignSettings
        """
        AmbientTemp = str(ambtemp) + "cel"
        #
        # Configure design settings for gravity etc
        IceGravity = ["X", "Y", "Z"]
        GVPos = False
        if int(gravityDir) > 2:
            GVPos = True
        GVA = IceGravity[int(gravityDir) - 3]
        self._odesign.SetDesignSettings(
            [
                "NAME:Design Settings Data",
                "Perform Minimal validation:=",
                performvalidation,
                "Default Fluid Material:=",
                defaultfluid,
                "Default Solid Material:=",
                defaultsolid,
                "Default Surface Material:=",
                "Steel-oxidised-surface",
                "AmbientTemperature:=",
                AmbientTemp,
                "AmbientPressure:=",
                "0n_per_meter_sq",
                "AmbientRadiationTemperature:=",
                AmbientTemp,
                "Gravity Vector CS ID:=",
                1,
                "Gravity Vector Axis:=",
                GVA,
                "Positive:=",
                GVPos,
                "ExportOnSimulationComplete:=",
                export_monitor,
                "ExportDirectory:=",
                export_directory,
            ],
            [
                "NAME:Model Validation Settings",
                "EntityCheckLevel:=",
                CheckLevel,
                "IgnoreUnclassifiedObjects:=",
                False,
                "SkipIntersectionChecks:=",
                False,
            ],
        )
        return True

    @pyaedt_function_handler()
    def assign_em_losses(
        self,
        designname="HFSSDesign1",
        setupname="Setup1",
        sweepname="LastAdaptive",
        map_frequency=None,
        surface_objects=None,
        source_project_name=None,
        paramlist=None,
        object_list=None,
    ):
        """Map EM losses to an Icepak design.

        Parameters
        ----------
        designname : string, optional
            Name of the design with the source mapping. The default is ``"HFSSDesign1"``.
        setupname : str, optional
            Name of the EM setup. The default is ``"Setup1"``.
        sweepname : str, optional
            Name of the EM sweep to use for the mapping. The default is ``"LastAdaptive"``.
        map_frequency : str, optional
            String containing the frequency to map. The default is ``None``.
            The value must be ``None`` for Eigenmode analysis.
        surface_objects : list, optional
            List of objects in the source that are metals. The default is ``None``.
        source_project_name : str, optional
            Name of the source project. The default is ``None``, in which case the
            source from the same project is used.
        paramlist : list, dict, optional
            List of all parameters to map from source and Icepak design. The default is ``None``.
            If ``None`` the variables are set to their values (no mapping).
            If it is a list, the specified variables in the icepak design are mapped to variables
            in the source design having the same name.
            If it is a dictionary, it is possible to map variables to the source design having a different name.
            The dictionary structure is {"source_design_variable": "icepak_variable"}.
        object_list : list, optional
            List of objects. The default is ``None``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oModule.AssignEMLoss
        """
        if surface_objects is None:
            surface_objects = []
        if object_list is None:
            object_list = []

        self.logger.info("Mapping HFSS EM losses.")

        if self.project_name == source_project_name or source_project_name is None:
            project_name = "This Project*"
        else:
            project_name = source_project_name + ".aedt"
        #
        # Generate a list of model objects from the lists made previously and use to map the HFSS losses into Icepak
        #
        if not object_list:
            all_objects = self.modeler.object_names
            if "Region" in all_objects:
                all_objects.remove("Region")
        else:
            all_objects = object_list[:]

        surfaces = surface_objects
        if map_frequency:
            intr = [map_frequency]
        else:
            intr = []

        argparam = OrderedDict({})
        for el in self.available_variations.nominal_w_values_dict:
            argparam[el] = self.available_variations.nominal_w_values_dict[el]

        if paramlist and isinstance(paramlist, list):
            for el in paramlist:
                argparam[el] = el
        elif paramlist and isinstance(paramlist, dict):
            for el in paramlist:
                argparam[el] = paramlist[el]

        props = OrderedDict(
            {
                "Objects": all_objects,
                "Project": project_name,
                "Product": "ElectronicsDesktop",
                "Design": designname,
                "Soln": setupname + " : " + sweepname,
                "Params": argparam,
                "ForceSourceToSolve": True,
                "PreservePartnerSoln": True,
                "PathRelativeTo": "TargetProject",
            }
        )
        props["Intrinsics"] = intr
        props["SurfaceOnly"] = surfaces

        name = generate_unique_name("EMLoss")
        bound = BoundaryObject(self, name, props, "EMLoss")
        if bound.create():
            self.boundaries.append(bound)
            self.logger.info("EM losses mapped from design: %s.", designname)
            return bound
        return False

    @pyaedt_function_handler()
    def eval_surface_quantity_from_field_summary(
        self,
        faces_list,
        quantity_name="HeatTransCoeff",
        savedir=None,
        filename=None,
        sweep_name=None,
        parameter_dict_with_values={},
    ):
        """Export the field surface output.

        This method exports one CSV file for the specified variation.

        Parameters
        ----------
        faces_list : list
            List of faces to apply.
        quantity_name : str, optional
            Name of the quantity to export. The default is ``"HeatTransCoeff"``.
        savedir : str, optional
            Directory to save the CSV file to. The default is ``None``, in which
            case the file is exported to the working directory.
        filename : str, optional
            Name of the CSV file. The default is ``None``, in which case the default
            name is used.
        sweep_name : str, optional
            Name of the setup and name of the sweep. For example, ``"IcepakSetup1 : SteatyState"``.
            The default is ``None``, in which case the active setup and active sweep are used.
        parameter_dict_with_values : dict, optional
            Dictionary of parameters defined for the specific setup with values. The default is ``{}``.

        Returns
        -------
        str
            Name of the file.

        References
        ----------

        >>> oModule.ExportFieldsSummary
        """
        name = generate_unique_name(quantity_name)
        self.modeler.create_face_list(faces_list, name)
        if not savedir:
            savedir = self.working_directory
        if not filename:
            filename = generate_unique_name(self.project_name + quantity_name)
        if not sweep_name:
            sweep_name = self.nominal_sweep
        self.osolution.EditFieldsSummarySetting(
            [
                "Calculation:=",
                ["Object", "Surface", name, quantity_name, "", "Default", "AmbientTemp"],
            ]
        )
        string = ""
        for el in parameter_dict_with_values:
            string += el + "='" + parameter_dict_with_values[el] + "' "
        filename = os.path.join(savedir, filename + ".csv")
        self.osolution.ExportFieldsSummary(
            [
                "SolutionName:=",
                sweep_name,
                "DesignVariationKey:=",
                string,
                "ExportFileName:=",
                filename,
                "IntrinsicValue:=",
                "",
            ]
        )
        return filename

    def eval_volume_quantity_from_field_summary(
        self,
        object_list,
        quantity_name="HeatTransCoeff",
        savedir=None,
        filename=None,
        sweep_name=None,
        parameter_dict_with_values={},
    ):
        """Export the field volume output.

        This method exports one CSV file for the specified variation.

        Parameters
        ----------
        object_list : list
            List of faces to apply.
        quantity_name : str, optional
            Name of the quantity to export. The default is ``"HeatTransCoeff"``.
        savedir : str, optional
            Directory to save the CSV file to. The default is ``None``, in which
            case the file is exported to the working directory.
        filename :  str, optional
            Name of the CSV file. The default is ``None``, in which case the default name
            is used.
        sweep_name :
            Name of the setup and name of the sweep. For example, ``"IcepakSetup1 : SteatyState"``.
            The default is ``None``, in which case the active setup and active sweep are used.
        parameter_dict_with_values : dict, optional
            Dictionary of parameters defined for the specific setup with values. The default is ``{}``

        Returns
        -------
        str
           Name of the file.

        References
        ----------

        >>> oModule.ExportFieldsSummary
        """
        if not savedir:
            savedir = self.working_directory
        if not filename:
            filename = generate_unique_name(self.project_name + quantity_name)
        if not sweep_name:
            sweep_name = self.nominal_sweep
        self.osolution.EditFieldsSummarySetting(
            [
                "Calculation:=",
                ["Object", "Volume", ",".join(object_list), quantity_name, "", "Default", "AmbientTemp"],
            ]
        )
        string = ""
        for el in parameter_dict_with_values:
            string += el + "='" + parameter_dict_with_values[el] + "' "
        filename = os.path.join(savedir, filename + ".csv")
        self.osolution.ExportFieldsSummary(
            [
                "SolutionName:=",
                sweep_name,
                "DesignVariationKey:=",
                string,
                "ExportFileName:=",
                filename,
                "IntrinsicValue:=",
                "",
            ]
        )
        return filename

    def export_summary(
        self,
        output_dir=None,
        solution_name=None,
        type="Object",
        geometryType="Volume",
        quantity="Temperature",
        variation="",
        variationlist=None,
    ):
        """Export a fields summary of all objects.

        Parameters
        ----------
        output_dir : str, optional
            Name of directory for exporting the fields summary.
            The default is ``None``, in which case the fields summary
            is exported to the working directory.
        solution_name : str, optional
            Name of the solution. The default is ``None``, in which case the
            the default name is used.
        type : string, optional
            The default is ``"Object"``.
        geometryType : str, optional
            Type of the geometry. The default is ``"Volume"``.
        quantity : str, optional
            The default is ``"Temperature"``.
        variation : str, optional
            The default is ``""``.
        variationlist : list, optional
            The default is ``None``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oModule.EditFieldsSummarySetting
        >>> oModule.ExportFieldsSummary
        """
        if variationlist == None:
            variationlist = []

        all_objs = list(self.modeler.oeditor.GetObjectsInGroup("Solids"))
        all_objs_NonModeled = list(self.modeler.oeditor.GetObjectsInGroup("Non Model"))
        all_objs_model = [item for item in all_objs if item not in all_objs_NonModeled]
        arg = []
        self.logger.info("Objects lists " + str(all_objs_model))
        for el in all_objs_model:
            try:
                self.osolution.EditFieldsSummarySetting(
                    ["Calculation:=", [type, geometryType, el, quantity, "", "Default"]]
                )
                arg.append("Calculation:=")
                arg.append([type, geometryType, el, quantity, "", "Default"])
            except Exception as e:
                self.logger.error("Object " + el + " not added.")
                self.logger.error(str(e))
        if not output_dir:
            output_dir = self.working_directory
        self.osolution.EditFieldsSummarySetting(arg)
        if not os.path.exists(output_dir):
            os.mkdir(output_dir)
        if not solution_name:
            solution_name = self.nominal_sweep
        if variation:
            for l in variationlist:
                self.osolution.ExportFieldsSummary(
                    [
                        "SolutionName:=",
                        solution_name,
                        "DesignVariationKey:=",
                        variation + "='" + str(l) + "'",
                        "ExportFileName:=",
                        os.path.join(output_dir, "IPKsummaryReport" + quantity + "_" + str(l) + ".csv"),
                    ]
                )
        else:
            self.osolution.ExportFieldsSummary(
                [
                    "SolutionName:=",
                    solution_name,
                    "DesignVariationKey:=",
                    "",
                    "ExportFileName:=",
                    os.path.join(output_dir, "IPKsummaryReport" + quantity + ".csv"),
                ]
            )
        return True

    @pyaedt_function_handler()
    def get_radiation_settings(self, radiation):
        """Get radiation settings.

        Parameters
        ----------
        radiation : str
            Type of the radiation. Options are:

            * ``"Nothing"``
            * ``"Low"``
            * ``"High"``
            * ``"Both"``

        Returns
        -------
        (bool, bool)
            Tuple containing the low side radiation and the high side radiation.
        """
        if radiation == "Nothing":
            low_side_radiation = False
            high_side_radiation = False
        elif radiation == "Low":
            low_side_radiation = True
            high_side_radiation = False
        elif radiation == "High":
            low_side_radiation = False
            high_side_radiation = True
        elif radiation == "Both":
            low_side_radiation = True
            high_side_radiation = True
        return low_side_radiation, high_side_radiation

    @pyaedt_function_handler()
    def get_link_data(self, links_data, **kwargs):
        """Get a list of linked data.

        Parameters
        ----------
        linkData : list
            List of the data to retrieve for links. Options are:

            * Project name, if ``None`` use the active project
            * Design name
            * HFSS solution name, such as ``"HFSS Setup 1 : Last Adaptive"``
            * Force source design simulation, ``True`` or ``False``
            * Preserve source design solution, ``True`` or ``False``

        Returns
        -------
        list
            List containing the requested link data.

        """

        if "linkData" in kwargs:
            warnings.warn(
                "The ``linkData`` parameter was deprecated in 0.6.43. Use the ``links_data`` parameter instead.",
                DeprecationWarning,
            )
            links_data = kwargs["linkData"]

        if links_data[0] is None:
            project_name = "This Project*"
        else:
            project_name = links_data[0].replace("\\", "/")

        design_name = links_data[1]
        hfss_solution_name = links_data[2]
        force_source_sim_enabler = links_data[3]
        preserve_src_res_enabler = links_data[4]

        arg = [
            "NAME:DefnLink",
            "Project:=",
            project_name,
            "Product:=",
            "ElectronicsDesktop",
            "Design:=",
            design_name,
            "Soln:=",
            hfss_solution_name,
            ["NAME:Params"],
            "ForceSourceToSolve:=",
            force_source_sim_enabler,
            "PreservePartnerSoln:=",
            preserve_src_res_enabler,
            "PathRelativeTo:=",
            "TargetProject",
        ]

        return arg

    @pyaedt_function_handler()
    def create_fan(
        self,
        name=None,
        is_2d=False,
        shape="Circular",
        cross_section="XY",
        radius="0.008mm",
        hub_radius="0mm",
        origin=None,
    ):
        """Create a fan component in Icepak that is linked to an HFSS 3D Layout object.

        Parameters
        ----------
        name : str, optional
            Fan name. The default is ``None``, in which case the default name is used.
        is_2d : bool, optional
            Whether the fan is modeled as 2D. The default is ``False``, in which
            case the fan is modeled as 3D.
        shape : str, optional
            Fan shape. Options are ``"Circular"`` and ``"Rectangular"``. The default
            is ``"Circular"``.
        cross_section : str, optional
            Cross section plane of the fan. The default is ``"XY"``.
        radius : str, float, optional
            Radius of the fan in modeler units. The default is ``"0.008mm"``.
        hub_radius : str, float, optional
            Hub radius of the fan in modeler units. The default is ``"0mm"``,
        origin : list, optional
            List of ``[x,y,z]`` coordinates for the position of the fan in the modeler.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.NativeComponentObject`
            NativeComponentObject object.

        References
        ----------

        >>> oModule.InsertNativeComponent
        """
        if not name:
            name = generate_unique_name("Fan")

        basic_component = OrderedDict(
            {
                "ComponentName": name,
                "Company": "",
                "Company URL": "",
                "Model Number": "",
                "Help URL": "",
                "Version": "1.0",
                "Notes": "",
                "IconType": "Fan",
            }
        )
        if is_2d:
            model = "2D"
        else:
            model = "3D"
        cross_section = GeometryOperators.cs_plane_to_plane_str(cross_section)
        native_component = OrderedDict(
            {
                "Type": "Fan",
                "Unit": self.modeler.model_units,
                "ModelAs": model,
                "Shape": shape,
                "MovePlane": cross_section,
                "Radius": self._arg_with_units(radius),
                "HubRadius": self._arg_with_units(hub_radius),
                "CaseSide": True,
                "FlowDirChoice": "NormalPositive",
                "FlowType": "Curve",
                "SwirlType": "Magnitude",
                "FailedFan": False,
                "DimUnits": ["m3_per_s", "n_per_meter_sq"],
                "X": ["0", "0.01"],
                "Y": ["3", "0"],
                "Pressure Loss Curve": OrderedDict(
                    {"DimUnits": ["m_per_sec", "n_per_meter_sq"], "X": ["", "", "", "3"], "Y": ["", "1", "10", "0"]}
                ),
                "IntakeTemp": "AmbientTemp",
                "Swirl": "0",
                "OperatingRPM": "0",
                "Magnitude": "1",
            }
        )
        native_props = OrderedDict(
            {
                "TargetCS": "Global",
                "SubmodelDefinitionName": name,
                "ComponentPriorityLists": OrderedDict({}),
                "NextUniqueID": 0,
                "MoveBackwards": False,
                "DatasetType": "ComponentDatasetType",
                "DatasetDefinitions": OrderedDict({}),
                "BasicComponentInfo": basic_component,
                "GeometryDefinitionParameters": OrderedDict({"VariableOrders": OrderedDict()}),
                "DesignDefinitionParameters": OrderedDict({"VariableOrders": OrderedDict()}),
                "MaterialDefinitionParameters": OrderedDict({"VariableOrders": OrderedDict()}),
                "MapInstanceParameters": "DesignVariable",
                "UniqueDefinitionIdentifier": "57c8ab4e-4db9-4881-b6bb-"
                + random_string(12, char_set="abcdef0123456789"),
                "OriginFilePath": "",
                "IsLocal": False,
                "ChecksumString": "",
                "ChecksumHistory": [],
                "VersionHistory": [],
                "NativeComponentDefinitionProvider": native_component,
                "InstanceParameters": OrderedDict(
                    {"GeometryParameters": "", "MaterialParameters": "", "DesignParameters": ""}
                ),
            }
        )

        component3d_names = list(self.modeler.oeditor.Get3DComponentInstanceNames(name))

        native = NativeComponentObject(self, "Fan", name, native_props)
        if native.create():
            user_defined_component = UserDefinedComponent(
                self.modeler, native.name, native_props["NativeComponentDefinitionProvider"], "Fan"
            )
            self.modeler.user_defined_components[native.name] = user_defined_component
            new_name = [
                i for i in list(self.modeler.oeditor.Get3DComponentInstanceNames(name)) if i not in component3d_names
            ][0]
            self.modeler.refresh_all_ids()
            self.materials._load_from_project()
            self._native_components.append(native)
            if origin:
                self.modeler.move(new_name, origin)
            return native
        return False

    @pyaedt_function_handler()
    def create_ipk_3dcomponent_pcb(
        self,
        compName,
        setupLinkInfo,
        solutionFreq,
        resolution,
        PCB_CS="Global",
        rad="Nothing",
        extent_type="Bounding Box",
        outline_polygon="",
        powerin="0W",
        custom_x_resolution=None,
        custom_y_resolution=None,
        **kwargs
    ):
        """Create a PCB component in Icepak that is linked to an HFSS 3D Layout object.

        Parameters
        ----------
        compName : str
            Name of the new PCB component.
        setupLinkInfo : list
            List of the five elements needed to set up the link in this format:
            ``[projectname, designname, solution name, forcesimulation (bool), preserve results (bool)]``.
        solutionFreq :
            Frequency of the solution if cosimulation is requested.
        resolution : int
            Resolution of the mapping.
        PCB_CS : str, optional
            Coordinate system for the PCB. The default is ``"Global"``.
        rad : str, optional
            Radiating faces. The default is ``"Nothing"``.
        extent_type : str, optional
            Type of the extent. Options are ``"Bounding Box"`` and ``"Polygon"``.
            The default is ``"Bounding Box"``.
        outline_polygon : str, optional
            Name of the polygon if ``extentype="Polygon"``. The default is ``""``.
        powerin : str, optional
            Power to dissipate if cosimulation is disabled. The default is ``"0W"``.
        custom_x_resolution
            The default is ``None``.
        custom_y_resolution
            The default is ``None``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.NativeComponentObject`
            NativeComponentObject object.

        References
        ----------

        >>> oModule.InsertNativeComponent
        """

        if "extenttype" in kwargs:
            warnings.warn(
                "The ``extenttype`` parameter was deprecated in 0.6.43. Use the ``extent_type`` parameter instead.",
                DeprecationWarning,
            )
            extent_type = kwargs["extenttype"]

        if "outlinepolygon" in kwargs:
            warnings.warn(
                """The ``outlinepolygon`` parameter was deprecated in 0.6.43.
                Use the ``outline_polygon`` parameter instead.""",
                DeprecationWarning,
            )
            outline_polygon = kwargs["outlinepolygon"]

        low_radiation, high_radiation = self.get_radiation_settings(rad)
        hfss_link_info = OrderedDict({})
        _arg2dict(self.get_link_data(setupLinkInfo), hfss_link_info)

        native_props = OrderedDict(
            {
                "NativeComponentDefinitionProvider": OrderedDict(
                    {
                        "Type": "PCB",
                        "Unit": self.modeler.model_units,
                        "MovePlane": "XY",
                        "Use3DLayoutExtents": False,
                        "ExtentsType": extent_type,
                        "OutlinePolygon": outline_polygon,
                        "CreateDevices": False,
                        "CreateTopSolderballs": False,
                        "CreateBottomSolderballs": False,
                        "Resolution": int(resolution),
                        "LowSide": OrderedDict({"Radiate": low_radiation}),
                        "HighSide": OrderedDict({"Radiate": high_radiation}),
                    }
                )
            }
        )
        native_props["BasicComponentInfo"] = OrderedDict({"IconType": "PCB"})

        if custom_x_resolution and custom_y_resolution:
            native_props["NativeComponentDefinitionProvider"]["UseThermalLink"] = solutionFreq != ""
            native_props["NativeComponentDefinitionProvider"]["CustomResolution"] = True
            native_props["NativeComponentDefinitionProvider"]["CustomResolutionRow"] = custom_x_resolution
            native_props["NativeComponentDefinitionProvider"]["CustomResolutionCol"] = 600
            # compDefinition += ["UseThermalLink:=", solutionFreq!="",
            #                    "CustomResolution:=", True, "CustomResolutionRow:=", custom_x_resolution,
            #                    "CustomResolutionCol:=", 600]
        else:
            native_props["NativeComponentDefinitionProvider"]["UseThermalLink"] = solutionFreq != ""
            native_props["NativeComponentDefinitionProvider"]["CustomResolution"] = False
            # compDefinition += ["UseThermalLink:=", solutionFreq != "",
            #                    "CustomResolution:=", False]
        if solutionFreq:
            native_props["NativeComponentDefinitionProvider"]["Frequency"] = solutionFreq
            native_props["NativeComponentDefinitionProvider"]["DefnLink"] = hfss_link_info["DefnLink"]
            # compDefinition += ["Frequency:=", solutionFreq, hfssLinkInfo]
        else:
            native_props["NativeComponentDefinitionProvider"]["Power"] = powerin
            native_props["NativeComponentDefinitionProvider"]["DefnLink"] = hfss_link_info["DefnLink"]
            # compDefinition += ["Power:=", powerin, hfssLinkInfo]

        native_props["TargetCS"] = PCB_CS
        native = NativeComponentObject(self, "PCB", compName, native_props)
        if native.create():
            user_defined_component = UserDefinedComponent(
                self.modeler, native.name, native_props["NativeComponentDefinitionProvider"], "PCB"
            )
            self.modeler.user_defined_components[native.name] = user_defined_component
            self.modeler.refresh_all_ids()
            self.materials._load_from_project()
            self._native_components.append(native)
            return native
        return False

    @pyaedt_function_handler()
    def create_pcb_from_3dlayout(
        self,
        component_name,
        project_name,
        design_name,
        resolution=2,
        extent_type="Bounding Box",
        outline_polygon="",
        close_linked_project_after_import=True,
        custom_x_resolution=None,
        custom_y_resolution=None,
        power_in=0,
        **kwargs
    ):
        """Create a PCB component in Icepak that is linked to an HFSS 3DLayout object linking only to the geometry file.

        .. note::
           No solution is linked.

        Parameters
        ----------
        component_name : str
            Name of the new PCB component to create in Icepak.
        project_name : str
            Name of the project or the full path to the project.
        design_name : str
            Name of the design.
        resolution : int, optional
            Resolution of the mapping. The default is ``2``.
        extent_type :
            Type of the extent. Options are ``"Polygon"`` and ``"Bounding Box"``. The default
            is ``"Bounding Box"``.
        outline_polygon : str, optional
            Name of the outline polygon if ``extent_type="Polygon"``. The default is ``""``.
        close_linked_project_after_import : bool, optional
            Whether to close the linked AEDT project after the import. The default is ``True``.
        custom_x_resolution :
            The default is ``None``.
        custom_y_resolution :
            The default is ``None``.
        power_in : float, optional
            Power in in Watt.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oModule.InsertNativeComponent
        """

        if "extenttype" in kwargs:
            warnings.warn(
                "``extenttype`` was deprecated in 0.6.43. Use ``extent_type`` instead.",
                DeprecationWarning,
            )
            extent_type = kwargs["extenttype"]

        if "outlinepolygon" in kwargs:
            warnings.warn(
                "``outlinepolygon`` was deprecated in 0.6.43. Use ``outline_polygon`` instead.",
                DeprecationWarning,
            )
            outline_polygon = kwargs["outlinepolygon"]

        if project_name == self.project_name:
            project_name = "This Project*"
        link_data = [project_name, design_name, "<--EDB Layout Data-->", False, False]
        status = self.create_ipk_3dcomponent_pcb(
            component_name,
            link_data,
            "",
            resolution,
            extent_type=extent_type,
            outline_polygon=outline_polygon,
            custom_x_resolution=custom_x_resolution,
            custom_y_resolution=custom_y_resolution,
            powerin=self.modeler._arg_with_dim(power_in, "W"),
        )

        if close_linked_project_after_import and ".aedt" in project_name:
            prjname = os.path.splitext(os.path.basename(project_name))[0]
            self.close_project(prjname, save_project=False)
        self.logger.info("PCB component correctly created in Icepak.")
        return status

    @pyaedt_function_handler()
    def copyGroupFrom(self, group_name, source_design, source_project_name=None, source_project_path=None, **kwargs):
        """Copy a group from another design.

        Parameters
        ----------
        group_name : str
            Name of the group.
        source_design : str
            Name of the source design.
        source_project_name : str, optional
            Name of the source project. The default is ``None`` in which case, the current active project will be used.
        source_project_path : str, optional
            Path to the source project. The default is ``None``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.Copy
        >>> oeditor.Paste
        """

        if "groupName" in kwargs:
            warnings.warn(
                "The ``groupName`` parameter was deprecated in 0.6.43. Use the ``group_name`` parameter instead.",
                DeprecationWarning,
            )
            group_name = kwargs["groupName"]

        if "sourceDesign" in kwargs:
            warnings.warn(
                "The ``sourceDesign`` parameter was deprecated in 0.6.43. Use the ``source_design`` parameter instead.",
                DeprecationWarning,
            )
            source_design = kwargs["sourceDesign"]

        if "sourceProject" in kwargs:
            warnings.warn(
                """The ``sourceProject`` parameter was deprecated in 0.6.43.
                Use the ``source_project_name`` parameter instead.""",
                DeprecationWarning,
            )
            source_project_name = kwargs["sourceProject"]

        if "sourceProjectPath" in kwargs:
            warnings.warn(
                """The ``sourceProjectPath`` parameter was deprecated in 0.6.43.
                Use the ``source_project_path`` parameter instead.""",
                DeprecationWarning,
            )
            source_project_path = kwargs["sourceProjectPath"]

        if source_project_name == self.project_name or source_project_name is None:
            active_project = self._desktop.GetActiveProject()
        else:
            self._desktop.OpenProject(source_project_path)
            active_project = self._desktop.SetActiveProject(source_project_name)

        active_design = active_project.SetActiveDesign(source_design)
        active_editor = active_design.SetActiveEditor("3D Modeler")
        active_editor.Copy(["NAME:Selections", "Selections:=", group_name])

        self.modeler.oeditor.Paste()
        self.modeler.refresh_all_ids()
        self.materials._load_from_project()
        return True

    @pyaedt_function_handler()
    def globalMeshSettings(
        self,
        meshtype,
        gap_min_elements="1",
        noOgrids=False,
        MLM_en=True,
        MLM_Type="3D",
        stairStep_en=False,
        edge_min_elements="1",
        object="Region",
    ):
        """Create a custom mesh tailored on a PCB design.

        Parameters
        ----------
        meshtype : int
            Type of the mesh. Options are ``1``, ``2``, and ``3``, which represent
            respectively a coarse, standard, and very accurate mesh.
        gap_min_elements : str, optional
            The default is ``"1"``.
        noOgrids : bool, optional
            The default is ``False``.
        MLM_en : bool, optional
            The default is ``True``.
        MLM_Type : str, optional
            The default is ``"3D"``.
        stairStep_en : bool, optional
            The default is ``False``.
        edge_min_elements : str, optional
            The default is ``"1"``.
        object : str, optional
            The default is ``"Region"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oModule.EditGlobalMeshRegion
        """

        bounding_box = self.modeler.oeditor.GetModelBoundingBox()
        xsize = abs(float(bounding_box[0]) - float(bounding_box[3])) / (15 * meshtype * meshtype)
        ysize = abs(float(bounding_box[1]) - float(bounding_box[4])) / (15 * meshtype * meshtype)
        zsize = abs(float(bounding_box[2]) - float(bounding_box[5])) / (10 * meshtype)
        MaxSizeRatio = 1 + (meshtype / 2)

        self.omeshmodule.EditGlobalMeshRegion(
            [
                "NAME:Settings",
                "MeshMethod:=",
                "MesherHD",
                "UserSpecifiedSettings:=",
                True,
                "ComputeGap:=",
                True,
                "MaxElementSizeX:=",
                str(xsize) + self.modeler.model_units,
                "MaxElementSizeY:=",
                str(ysize) + self.modeler.model_units,
                "MaxElementSizeZ:=",
                str(zsize) + self.modeler.model_units,
                "MinElementsInGap:=",
                gap_min_elements,
                "MinElementsOnEdge:=",
                edge_min_elements,
                "MaxSizeRatio:=",
                str(MaxSizeRatio),
                "NoOGrids:=",
                noOgrids,
                "EnableMLM:=",
                MLM_en,
                "EnforeMLMType:=",
                MLM_Type,
                "MaxLevels:=",
                "0",
                "BufferLayers:=",
                "0",
                "UniformMeshParametersType:=",
                "Average",
                "StairStepMeshing:=",
                stairStep_en,
                "MinGapX:=",
                str(xsize / 10) + self.modeler.model_units,
                "MinGapY:=",
                str(xsize / 10) + self.modeler.model_units,
                "MinGapZ:=",
                str(xsize / 10) + self.modeler.model_units,
                "Objects:=",
                [object],
            ]
        )
        return True

    @pyaedt_function_handler()
    def create_meshregion_component(
        self, scale_factor=1.0, name="Component_Region", restore_padding_values=[50, 50, 50, 50, 50, 50]
    ):
        """Create a bounding box to use as a mesh region in Icepak.

        Parameters
        ----------
        scale_factor : float, optional
            The default is ``1.0``.
        name : str, optional
            Name of the bounding box. The default is ``"Component_Region"``.
        restore_padding_values : list, optional
            The default is ``[50,50,50,50,50,50]``.

        Returns
        -------
        tuple
            Tuple containing the ``(x, y, z)`` distances of the region.

        References
        ----------

        >>> oeditor.ChangeProperty
        """
        self.modeler.edit_region_dimensions([0, 0, 0, 0, 0, 0])

        vertex_ids = self.modeler.oeditor.GetVertexIDsFromObject("Region")

        x_values = []
        y_values = []
        z_values = []

        for vertex_id in vertex_ids:
            tmp = self.modeler.oeditor.GetVertexPosition(vertex_id)
            x_values.append(tmp[0])
            y_values.append(tmp[1])
            z_values.append(tmp[2])

        scale_factor = scale_factor - 1
        delta_x = (float(max(x_values)) - float(min(x_values))) * scale_factor
        x_max = float(max(x_values)) + delta_x / 2.0
        x_min = float(min(x_values)) - delta_x / 2.0

        delta_y = (float(max(y_values)) - float(min(y_values))) * scale_factor
        y_max = float(max(y_values)) + delta_y / 2.0
        y_min = float(min(y_values)) - delta_y / 2.0

        delta_z = (float(max(z_values)) - float(min(z_values))) * scale_factor
        z_max = float(max(z_values)) + delta_z / 2.0
        z_min = float(min(z_values)) - delta_z / 2.0

        dis_x = str(float(x_max) - float(x_min))
        dis_y = str(float(y_max) - float(y_min))
        dis_z = str(float(z_max) - float(z_min))

        min_position = self.modeler.Position(str(x_min) + "mm", str(y_min) + "mm", str(z_min) + "mm")
        mesh_box = self.modeler.create_box(min_position, [dis_x + "mm", dis_y + "mm", dis_z + "mm"], name)

        self.modeler[name].model = False

        self.modeler.edit_region_dimensions(restore_padding_values)
        return dis_x, dis_y, dis_z

    @pyaedt_function_handler()
    def delete_em_losses(self, bound_name):
        """Delete the EM losses boundary.

        Parameters
        ----------
        bound_name : str
            Name of the boundary.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oModule.DeleteBoundaries
        """
        self.oboundary.DeleteBoundaries([bound_name])
        return True

    @pyaedt_function_handler()
    def delete_pcb_component(self, comp_name):
        """Delete a PCB component.

        Parameters
        ----------
        comp_name : str
            Name of the PCB component.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.Delete
        """
        arg = ["NAME:Selections", "Selections:=", comp_name]

        self.modeler.oeditor.Delete(arg)
        return True

    @pyaedt_function_handler()
    def get_liquid_objects(self):
        """Get liquid material objects.

        Returns
        -------
        list
            List of all liquid material objects.
        """
        mats = []
        for el in self.materials.liquids:
            mats.extend(self.modeler.convert_to_selections(self.modeler.get_objects_by_material(el), True))
        return mats

    @pyaedt_function_handler()
    def get_gas_objects(self):
        """Get gas objects.

        Returns
        -------
        list
            List of all gas objects.
        """
        mats = []
        for el in self.materials.gases:
            mats.extend(self.modeler.convert_to_selections(self.modeler.get_objects_by_material(el), True))
        return mats

    @pyaedt_function_handler()
    def generate_fluent_mesh(self, object_lists=None):
        """Generate a Fluent mesh for a list of selected objects and assign the mesh automatically to the objects.

        Parameters
        ----------
        object_lists : list, optional
            List of objects to compute the Fluent mesh on. The default is ``None``, in which case
            all fluids objects are used to compute the mesh.

        Returns
        -------
        :class:`pyaedt.modules.Mesh.MeshOperation`
        """
        version = self.aedt_version_id[-3:]
        ansys_install_dir = os.environ.get("ANSYS{}_DIR".format(version), "")
        if not ansys_install_dir:
            ansys_install_dir = os.environ.get("AWP_ROOT{}".format(version), "")
        assert ansys_install_dir, "Fluent {} has to be installed on to generate mesh.".format(version)
        assert os.getenv("ANSYS{}_DIR".format(version))
        if not object_lists:
            object_lists = self.get_liquid_objects()
            assert object_lists, "No Fluids objects found."
        object_lists = self.modeler.convert_to_selections(object_lists, True)
        file_name = self.project_name
        sab_file_pointer = os.path.join(self.working_directory, file_name + ".sab")
        mesh_file_pointer = os.path.join(self.working_directory, file_name + ".msh")
        fl_uscript_file_pointer = os.path.join(self.working_directory, "FLUscript.jou")
        if os.path.exists(mesh_file_pointer):
            os.remove(mesh_file_pointer)
        if os.path.exists(sab_file_pointer):
            os.remove(sab_file_pointer)
        if os.path.exists(fl_uscript_file_pointer):
            os.remove(fl_uscript_file_pointer)
        if os.path.exists(mesh_file_pointer + ".trn"):
            os.remove(mesh_file_pointer + ".trn")
        assert self.export_3d_model(file_name, self.working_directory, ".sab", object_lists), "Failed to export .sab"

        # Building Fluent journal script file *.jou
        fluent_script = open(fl_uscript_file_pointer, "w")
        fluent_script.write("/file/start-transcript " + '"' + mesh_file_pointer + '.trn"\n')
        fluent_script.write(
            '/file/set-tui-version "{}"\n'.format(self.aedt_version_id[-3:-1] + "." + self.aedt_version_id[-1:])
        )
        fluent_script.write("(enable-feature 'serial-hexcore-without-poly)\n")
        fluent_script.write('(cx-gui-do cx-activate-tab-index "NavigationPane*Frame1(TreeTab)" 0)\n')
        fluent_script.write("(%py-exec \"workflow.InitializeWorkflow(WorkflowType=r'Watertight Geometry')\")\n")
        cmd = "(%py-exec \"workflow.TaskObject['Import Geometry']."
        cmd += "Arguments.setState({r'FileName': r'" + sab_file_pointer + "',})\")\n"
        fluent_script.write(cmd)
        fluent_script.write("(%py-exec \"workflow.TaskObject['Import Geometry'].Execute()\")\n")
        fluent_script.write("(%py-exec \"workflow.TaskObject['Add Local Sizing'].AddChildToTask()\")\n")
        fluent_script.write("(%py-exec \"workflow.TaskObject['Add Local Sizing'].Execute()\")\n")
        fluent_script.write("(%py-exec \"workflow.TaskObject['Generate the Surface Mesh'].Execute()\")\n")
        cmd = "(%py-exec \"workflow.TaskObject['Describe Geometry'].UpdateChildTasks(SetupTypeChanged=False)\")\n"
        fluent_script.write(cmd)
        cmd = "(%py-exec \"workflow.TaskObject['Describe Geometry']."
        cmd += "Arguments.setState({r'SetupType': r'The geometry consists of only fluid regions with no voids',})\")\n"
        fluent_script.write(cmd)
        cmd = "(%py-exec \"workflow.TaskObject['Describe Geometry'].UpdateChildTasks(SetupTypeChanged=True)\")\n"
        fluent_script.write(cmd)
        cmd = "(%py-exec \"workflow.TaskObject['Describe Geometry'].Arguments.setState({r'InvokeShareTopology': r'Yes',"
        cmd += "r'SetupType': r'The geometry consists of only fluid regions with no voids',r'WallToInternal': "
        cmd += "r'Yes',})\")\n"
        fluent_script.write(cmd)
        cmd = "(%py-exec \"workflow.TaskObject['Describe Geometry'].UpdateChildTasks(SetupTypeChanged=False)\")\n"
        fluent_script.write(cmd)
        fluent_script.write("(%py-exec \"workflow.TaskObject['Describe Geometry'].Execute()\")\n")
        fluent_script.write("(%py-exec \"workflow.TaskObject['Apply Share Topology'].Execute()\")\n")
        fluent_script.write("(%py-exec \"workflow.TaskObject['Update Boundaries'].Execute()\")\n")
        fluent_script.write("(%py-exec \"workflow.TaskObject['Update Regions'].Execute()\")\n")
        fluent_script.write("(%py-exec \"workflow.TaskObject['Add Boundary Layers'].AddChildToTask()\")\n")
        fluent_script.write("(%py-exec \"workflow.TaskObject['Add Boundary Layers'].InsertCompoundChildTask()\")\n")
        cmd = "(%py-exec \"workflow.TaskObject['smooth-transition_1']."
        cmd += "Arguments.setState({r'BLControlName': r'smooth-transition_1',})\")\n"
        fluent_script.write(cmd)
        fluent_script.write("(%py-exec \"workflow.TaskObject['Add Boundary Layers'].Arguments.setState({})\")\n")
        fluent_script.write("(%py-exec \"workflow.TaskObject['smooth-transition_1'].Execute()\")\n")
        # r'VolumeFill': r'hexcore' / r'tetrahedral'
        cmd = "(%py-exec \"workflow.TaskObject['Generate the Volume Mesh'].Arguments.setState({r'VolumeFill': "
        cmd += "r'hexcore', r'VolumeMeshPreferences': {r'MergeBodyLabels': r'yes',},})\")\n"
        fluent_script.write(cmd)
        fluent_script.write("(%py-exec \"workflow.TaskObject['Generate the Volume Mesh'].Execute()\")\n")
        fluent_script.write("/file/hdf no\n")
        fluent_script.write('/file/write-mesh "' + mesh_file_pointer + '"\n')
        fluent_script.write("/file/stop-transcript\n")
        fluent_script.write("/exit,\n")
        fluent_script.close()

        # Fluent command line parameters: -meshing -i <journal> -hidden -tm<x> (# processors for meshing) -wait
        fl_ucommand = [
            os.path.join(self.desktop_install_dir, "fluent", "ntbin", "win64", "fluent.exe"),
            "3d",
            "-meshing",
            "-hidden",
            "-i" + '"' + fl_uscript_file_pointer + '"',
        ]
        self.logger.info("Fluent is starting in BG.")
        subprocess.call(fl_ucommand)
        if os.path.exists(mesh_file_pointer + ".trn"):
            os.remove(mesh_file_pointer + ".trn")
        if os.path.exists(fl_uscript_file_pointer):
            os.remove(fl_uscript_file_pointer)
        if os.path.exists(sab_file_pointer):
            os.remove(sab_file_pointer)
        if os.path.exists(mesh_file_pointer):
            self.logger.info("'" + mesh_file_pointer + "' has been created.")
            return self.mesh.assign_mesh_from_file(object_lists, mesh_file_pointer)
        self.logger.error("Failed to create msh file")

        return False

    @pyaedt_function_handler()
    def apply_icepak_settings(
        self,
        ambienttemp=20,
        gravityDir=5,
        perform_minimal_val=True,
        default_fluid="air",
        default_solid="Al-Extruded",
        default_surface="Steel-oxidised-surface",
    ):
        """Apply Icepak default design settings.

        Parameters
        ----------
        ambienttemp : float, str, optional
            Ambient temperature, which can be an integer or a parameter already
            created in AEDT. The default is ``20``.
        gravityDir : int, optional
            Gravity direction index in the range ``[0, 5]``. The default is ``5``.
        perform_minimal_val : bool, optional
            Whether to perform minimal validation. The default is ``True``.
            If ``False``, full validation is performed.
        default_fluid : str, optional
            Type of fluid. The default is ``"Air"``.
        default_solid :
            Type of solid. The default is ``"Al-Extruded"``.
        default_surface :
            Type of surface. The default is ``"Steel-oxidised-surface"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oDesign.SetDesignSettings
        """

        ambient_temperature = self.modeler._arg_with_dim(ambienttemp, "cel")

        axes = ["X", "Y", "Z"]
        GVPos = False
        if int(gravityDir) > 2:
            GVPos = True
        gravity_axis = axes[int(gravityDir) - 3]
        self.odesign.SetDesignSettings(
            [
                "NAME:Design Settings Data",
                "Perform Minimal validation:=",
                perform_minimal_val,
                "Default Fluid Material:=",
                default_fluid,
                "Default Solid Material:=",
                default_solid,
                "Default Surface Material:=",
                default_surface,
                "AmbientTemperature:=",
                ambient_temperature,
                "AmbientPressure:=",
                "0n_per_meter_sq",
                "AmbientRadiationTemperature:=",
                ambient_temperature,
                "Gravity Vector CS ID:=",
                1,
                "Gravity Vector Axis:=",
                gravity_axis,
                "Positive:=",
                GVPos,
            ],
            ["NAME:Model Validation Settings"],
        )
        return True

    @pyaedt_function_handler()
    def assign_surface_material(self, obj, mat):
        """Assign a surface material to one or more objects.

        Parameters
        ----------
        obj : str, list
            One or more objects to assign surface materials to.
        mat : str
            Material to assign. The material must be present in the database.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.ChangeProperty
        """
        objs = ["NAME:PropServers"]
        objs.extend(self.modeler.convert_to_selections(obj, True))
        try:
            self.modeler.oeditor.ChangeProperty(
                [
                    "NAME:AllTabs",
                    [
                        "NAME:Geometry3DAttributeTab",
                        objs,
                        ["NAME:ChangedProps", ["NAME:Surface Material", "Value:=", '"' + mat + '"']],
                    ],
                ]
            )
        except:
            self.logger.warning("Warning. The material is not the database. Use add_surface_material.")
            return False
        if mat.lower() not in self.materials.surface_material_keys:
            oo = self.get_oo_object(self.oproject, "Surface Materials/{}".format(mat))
            if oo:
                from pyaedt.modules.Material import SurfaceMaterial

                sm = SurfaceMaterial(self.materials, mat)
                sm.coordinate_system = oo.GetPropEvaluatedValue("Coordinate System Type")
                props = oo.GetPropNames()
                if "Surface Emissivity" in props:
                    sm.emissivity = oo.GetPropEvaluatedValue("Surface Emissivity")
                if "Surface Roughness" in props:
                    sm.surface_roughness = oo.GetPropEvaluatedValue("Surface Roughness")
                if "Solar Behavior" in props:
                    sm.surface_clarity_type = oo.GetPropEvaluatedValue("Solar Behavior")
                if "Solar Diffuse Absorptance" in props:
                    sm.surface_diffuse_absorptance = oo.GetPropEvaluatedValue("Solar Diffuse Absorptance")
                if "Solar Normal Absorptance" in props:
                    sm.surface_incident_absorptance = oo.GetPropEvaluatedValue("Solar Normal Absorptance")
                self.materials.surface_material_keys[mat.lower()] = sm
        return True

    @pyaedt_function_handler()
    def create_two_resistor_network_block_depr(self, object_name, power, rjb, rjc, placement):
        """Create a two-resistor network block.

        .. deprecated:: 0.6.30
            This method is replaced by the ``create_two_resistor_network_block`` method.

        Parameters
        ----------
        object_name : str
            Name of the object (3D block primitive) on which to create the two-resistor
            network.
        power : float
            Junction power in [W].
        rjb : float
            Junction-to-board thermal resistance in [K/W].
        rjc : float
            Junction-to-case thermal resistance in [K/W].
        placement : str
            Placement of the network block. Options are:
            - ``top``: Network block is placed on top of the board.
            - "bottom" : Network block is placed on bottom of the board.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        References
        ----------

        >>> oModule.AssignNetworkBoundary

        Examples
        --------

        >>> box = icepak.modeler.create_box([4, 5, 6], [5, 5, 5], "NetworkBox1", "copper")
        >>> block = icepak.create_two_resistor_network_block("NetworkBox1", "2W", 20, 10, "top")
        >>> block.props["Nodes"]["Internal"][0]
        '2W'
        """
        warnings.warn(
            "This method is deprecated in 0.6.29. Use the ``create_two_resistor_network_block`` method instead.",
            DeprecationWarning,
        )
        object_handle = self.modeler.get_object_from_name(object_name)
        placement = placement.lower()
        if placement == "top":
            board_face_id = object_handle.top_face_z.id
            case_face_id = object_handle.bottom_face_z.id
            board_side = "bottom"
            case_side = "top"
        else:
            board_face_id = object_handle.bottom_face_z.id
            case_face_id = object_handle.top_face_z.id
            board_side = "top"
            case_side = "bottom"

        # Define network properties in props directory
        props = {
            "Faces": [board_face_id, case_face_id],
            "Nodes": OrderedDict(
                {
                    "Case_side(" + case_side + ")": [case_face_id, "NoResistance"],
                    "Board_side(" + board_side + ")": [board_face_id, "NoResistance"],
                    "Internal": [power],
                }
            ),
            "Links": OrderedDict(
                {
                    "Rjc": ["Case_side(" + case_side + ")", "Internal", "R", str(rjc) + "cel_per_w"],
                    "Rjb": ["Board_side(" + board_side + ")", "Internal", "R", str(rjb) + "cel_per_w"],
                }
            ),
            "SchematicData": ({}),
        }

        # Default material is Ceramic_material
        self.modeler[object_name].material_name = "Ceramic_material"

        # Create boundary condition and set solve_inside = False
        bound = BoundaryObject(self, object_name, props, "Network")
        if bound.create():
            self.boundaries.append(bound)
            self.modeler.primitives[object_name].solve_inside = False
            return bound
        return None

    @pyaedt_function_handler()
    def import_idf(
        self,
        board_path,
        library_path=None,
        control_path=None,
        filter_cap=False,
        filter_ind=False,
        filter_res=False,
        filter_height_under=None,
        filter_height_exclude_2d=False,
        power_under=None,
        create_filtered_as_non_model=False,
        high_surface_thick="0.07mm",
        low_surface_thick="0.07mm",
        internal_thick="0.07mm",
        internal_layer_number=2,
        high_surface_coverage=30,
        low_surface_coverage=30,
        internal_layer_coverage=30,
        trace_material="Cu-Pure",
        substrate_material="FR-4",
        create_board=True,
        model_board_as_rect=False,
        model_device_as_rect=True,
        cutoff_height="5mm",
        component_lib="",
    ):
        """Import an IDF file into an Icepak design.

        Parameters
        ----------
        board_path : str
            Full path to the EMN/BDF file.
        library_path : str
            Full path to the EMP/LDF file. The default is ``None``, in which case a search for an EMP/LDF file
            with the same name as the EMN/BDF file is performed in the folder with the EMN/BDF file.
        control_path : str
            Full path to the XML file. The default is ``None``, in which case a search for an XML file
            with the same name as the EMN/BDF file is performed in the folder with the EMN/BDF file.
        filter_cap : bool, optional
            Whether to filter capacitors from the IDF file. The default is ``False``.
        filter_ind : bool, optional
            Whether to filter inductors from the IDF file. The default is ``False``.
        filter_res : bool, optional
            Whether to filter resistors from the IDF file. The default is ``False``.
        filter_height_under : float or str, optional
            Filter components under a given height. The default is ``None``, in which case
            no components are filtered based on height.
        filter_height_exclude_2d : bool, optional
            Whether to filter 2D components from the IDF file. The default is ``False``.
        power_under : float or str, optional
            Filter components with power under a given mW. The default is ``None``, in which
            case no components are filtered based on power.
        create_filtered_as_non_model : bool, optional
            Whether to set imported filtered components as ``Non-Model``. The default is ``False``.
        high_surface_thick : float or str optional
            High surface thickness. The default is ``"0.07mm"``.
        low_surface_thick : float or str, optional
            Low surface thickness. The default is ``"0.07mm"``.
        internal_thick : float or str, optional
            Internal layer thickness. The default is ``"0.07mm"``.
        internal_layer_number : int, optional
            Number of internal layers. The default is ``2``.
        high_surface_coverage : float, optional
            High surface material coverage. The default is ``30``.
        low_surface_coverage : float, optional
            Low surface material coverage. The default is ``30``.
        internal_layer_coverage : float, optional
            Internal layer material coverage. The default is ``30``.
        trace_material : str, optional
            Trace material. The default is ``"Cu-Pure"``.
        substrate_material : str, optional
            Substrate material. The default is ``"FR-4"``.
        create_board : bool, optional
            Whether to create the board. The default is ``True``.
        model_board_as_rect : bool, optional
            Whether to create the board as a rectangle. The default is ``False``.
        model_device_as_rect : bool, optional
            Whether to create the components as rectangles. The default is ``True``.
        cutoff_height : str or float, optional
            Cutoff height. The default is ``None``.
        component_lib : str, optional
            Full path to the component library.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oDesign.ImportIDF
        """
        if not library_path:
            if board_path.endswith(".emn"):
                library_path = board_path[:-3] + "emp"
            if board_path.endswith(".bdf"):
                library_path = board_path[:-3] + "ldf"
        if not control_path and os.path.exists(board_path[:-3] + "xml"):
            control_path = board_path[:-3] + "xml"
        else:
            control_path = ""
        filters = []
        if filter_cap:
            filters.append("Cap")
        if filter_ind:
            filters.append("Ind")
        if filter_res:
            filters.append("Res")
        if filter_height_under:
            filters.append("Height")
        else:
            filter_height_under = "0.1mm"
        if power_under:
            filters.append("Power")
        else:
            power_under = "10mW"
        if filter_height_exclude_2d:
            filters.append("HeightExclude2D")
        if cutoff_height:
            cutoff = True
        else:
            cutoff = False
        if component_lib:
            replace_device = True
        else:
            replace_device = False
        self.odesign.ImportIDF(
            [
                "NAME:Settings",
                "Board:=",
                board_path.replace("\\", "\\\\"),
                "Library:=",
                library_path.replace("\\", "\\\\"),
                "Control:=",
                control_path.replace("\\", "\\\\"),
                "Filters:=",
                filters,
                "CreateFilteredAsNonModel:=",
                create_filtered_as_non_model,
                "HeightVal:=",
                self._arg_with_units(filter_height_under),
                "PowerVal:=",
                self._arg_with_units(power_under, "mW"),
                [
                    "NAME:definitionOverridesMap",
                ],
                ["NAME:instanceOverridesMap"],
                "HighSurfThickness:=",
                self._arg_with_units(high_surface_thick),
                "LowSurfThickness:=",
                self._arg_with_units(low_surface_thick),
                "InternalLayerThickness:=",
                self._arg_with_units(internal_thick),
                "NumInternalLayer:=",
                internal_layer_number,
                "HighSurfaceCopper:=",
                high_surface_coverage,
                "LowSurfaceCopper:=",
                low_surface_coverage,
                "InternalLayerCopper:=",
                internal_layer_coverage,
                "TraceMaterial:=",
                trace_material,
                "SubstrateMaterial:=",
                substrate_material,
                "CreateBoard:=",
                create_board,
                "ModelBoardAsRect:=",
                model_board_as_rect,
                "ModelDeviceAsRect:=",
                model_device_as_rect,
                "Cutoff:=",
                cutoff,
                "CutoffHeight:=",
                self._arg_with_units(cutoff_height),
                "ReplaceDevices:=",
                replace_device,
                "CompLibDir:=",
                component_lib,
            ]
        )
        self.modeler.add_new_objects()
        return True

    @pyaedt_function_handler()
    def create_two_resistor_network_block(self, object_name, pcb, power, rjb, rjc):
        """Function to create 2-Resistor network object.
        This method is going to replace create_network_block method.

        Parameters
        ----------
        object_name : str
            name of the object (3D block primitive) on which 2-R network is to be created
        pcb : str
            name of board touching the network block. If the board is a PCB 3D component, enter name of
            3D component instance
        power : float
            junction power in [W]
        rjb : float
            Junction to board thermal resistance in [K/W]
        rjc : float
            Junction to case thermal resistance in [K/W]

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        References
        ----------

        >>> oModule.AssignNetworkBoundary

        Examples
        --------
        >>> board = icepak.modeler.create_box([0, 0, 0], [50, 100, 2], "board", "copper")
        >>> box = icepak.modeler.create_box([20, 20, 2], [10, 10, 3], "network_box1", "copper")
        >>> network_block = icepak.create_two_resistor_network_block_new("network_box1", "board", "5W", 2.5, 5)
        >>> network_block.props["Nodes"]["Internal"][0]
        '5W'
        """

        def get_face_normal(obj_face):
            vertex1 = obj_face.vertices[0].position
            vertex2 = obj_face.vertices[1].position
            face_center = obj_face.center_from_aedt
            v1 = [i - j for i, j in zip(vertex1, face_center)]
            v2 = [i - j for i, j in zip(vertex2, face_center)]
            n = GeometryOperators.v_cross(v1, v2)
            normalized_n = GeometryOperators.normalize_vector(n)
            return normalized_n

        net_handle = self.modeler.get_object_from_name(object_name)
        if pcb in self.modeler.user_defined_component_names:
            part_names = sorted(
                [
                    pcb_layer
                    for pcb_layer in self.modeler.get_3d_component_object_list(componentname=pcb)
                    if re.search(self.modeler.user_defined_components[pcb].definition_name + r"_\d\d\d.*", pcb_layer)
                ]
            )

            pcb_layers = [part_names[0], part_names[-1]]
            for layer in pcb_layers:
                x = self.modeler.get_object_from_name(object_name).get_touching_faces(layer)
                if x:
                    board_side = x[0]
                    board_side_normal = get_face_normal(board_side)
                    pcb_handle = self.modeler.get_object_from_name(layer)
            pcb_faces = pcb_handle.faces_by_area(area=1e-5, area_filter=">=")
            for face in pcb_faces:
                pcb_normal = get_face_normal(face)
                dot_product = round(sum([x * y for x, y in zip(board_side_normal, pcb_normal)]))
                if dot_product == -1:
                    pcb_face = face
            pcb_face_normal = get_face_normal(pcb_face)
        else:
            pcb_handle = self.modeler.get_object_from_name(pcb)
            board_side = self.modeler.get_object_from_name(object_name).get_touching_faces(pcb)[0]
            board_side_normal = get_face_normal(board_side)
            for face in pcb_handle.faces:
                pcb_normal = get_face_normal(face)
                dot_product = round(sum([x * y for x, y in zip(board_side_normal, pcb_normal)]))
                if dot_product == -1:
                    pcb_face = face
            pcb_face_normal = get_face_normal(pcb_face)

        for face in net_handle.faces:
            net_face_normal = get_face_normal(face)
            dot_product = round(sum([x * y for x, y in zip(net_face_normal, pcb_face_normal)]))
            if dot_product == 1:
                case_side = face

        props = {
            "Faces": [board_side.id, case_side.id],
            "Nodes": OrderedDict(
                {
                    "Case_side(" + str(case_side) + ")": [case_side.id, "NoResistance"],
                    "Board_side(" + str(board_side) + ")": [board_side.id, "NoResistance"],
                    "Internal": [power],
                }
            ),
            "Links": OrderedDict(
                {
                    "Rjc": ["Case_side(" + str(case_side) + ")", "Internal", "R", str(rjc) + "cel_per_w"],
                    "Rjb": ["Board_side(" + str(board_side) + ")", "Internal", "R", str(rjb) + "cel_per_w"],
                }
            ),
            "SchematicData": ({}),
        }

        self.modeler.primitives[object_name].material_name = "Ceramic_material"
        boundary = BoundaryObject(self, object_name, props, "Network")
        if boundary.create():
            self.boundaries.append(boundary)
            self.modeler.primitives[object_name].solve_inside = False
            return boundary
        return None

    @pyaedt_function_handler()
    def assign_stationary_wall(
        self,
        geometry,
        boundary_condition,
        name=None,
        temperature="0cel",
        heat_flux="0irrad_W_per_m2",
        thickness="0mm",
        htc="0w_per_m2kel",
        htc_dataset=None,
        ref_temperature="AmbientTemp",
        material="Al-Extruded",  # relevant if th>0
        radiate=False,
        radiate_surf_mat="Steel-oxidised-surface",  # relevant if radiate = False
        ht_correlation=False,
        ht_correlation_type="Natural Convection",
        ht_correlation_fluid="air",
        ht_correlation_flow_type="Turbulent",
        ht_correlation_flow_direction="X",
        ht_correlation_value_type="Average Values",  # "Local Values"
        ht_correlation_free_stream_velocity="1m_per_sec",
        ht_correlation_surface="Vertical",  # Top, Bottom, Vertical
        ht_correlation_amb_temperature="AmbientTemp",
        shell_conduction=False,
        ext_surf_rad=False,
        ext_surf_rad_material="Stainless-steel-cleaned",
        ext_surf_rad_ref_temp="AmbientTemp",
        ext_surf_rad_view_factor="1",
    ):
        """Assign surface wall boundary condition.

        Parameters
        ----------
        geometry : str or int
            Name of the surface object or ID of the face.
        boundary_condition : str
            Type of the boundary condition. Options are ``"Temperature"``, ``"Heat Flux"``,
            or ``"Heat Transfer Coefficient"``.
        name : str, optional
            Name of the boundary condition. The default is ``None``.
        temperature : str or float, optional
            Temperature to assign to the wall. This parameter is relevant if
            ``ext_condition="Temperature"``. If a float value is specified, the
            unit is degrees Celsius. The default is ``"0cel"``.
        heat_flux : str or float, optional
            Heat flux to assign to the wall. This parameter is relevant if
            ``ext_condition="Temperature"``. If a float value is specified,
            the unit is irrad_W_per_m2. The default is ``"0irrad_W_per_m2"``.
        htc : str or float, optional
            Heat transfer coefficient to assign to the wall. This parameter
            is relevant if ``ext_condition="Heat Transfer Coefficient"``. If a
            float value is specified, the unit is w_per_m2kel. The default
            is ``"0w_per_m2kel"``.
        thickness : str or float, optional
            Thickness of the wall. If a float value is specified, the unit is
            the current unit system set in Icepak. The default is ``"0mm"``.
        htc_dataset : str, optional
            Dataset that represents the dependency of the heat transfer
            coefficient on temperature. This parameter is relevant if
            ``ext_condition="Heat Transfer Coefficient"``. The default is ``None``.
        ref_temperature : str or float, optional
            Reference temperature for the definition of the heat transfer
            coefficient. This parameter is relevant if
            ``ext_condition="Heat Transfer Coefficient"``. The default
            is ``"AmbientTemp"``.
        material : str, optional
            Solid material of the wall. This parameter is relevant if
            the thickness is a non-zero value. The default is ``"Al-Extruded"``.
        radiate : bool, optional
            Whether to enable the inner surface radiation option. The default is ``False``.
        radiate_surf_mat : str, optional
            Surface material used for inner surface radiation. Relevant if it is enabled.
            The default is ``"Steel-oxidised-surface``.
        ht_correlation : bool, optional
            Whether to use the correlation option to compute the heat transfer coefficient.
            The default is ``False``.
        ht_correlation_type : str, optional
            The correlation type for the heat transfer coefficient. Options are
            "Natural Convection" and "Forced Convection". This parameter is
            relevant if ``ht_correlation=True``. The default is ``"Natural Convection"``.
        ht_correlation_fluid : str, optional
            Fluid for the correlation option. This parameter is relevant if
            ``ht_correlation=True``. The default is ``"air"``.
        ht_correlation_flow_type : str, optional
            Type of flow for the correlation option. This parameter
            is relevant if ``ht_correlation=True``. Options are ``"Turbulent"``
            and ``"Laminar"``. The default is ``"Turbulent"``.
        ht_correlation_flow_direction : str, optional
            Flow direction for the correlation option. This parameter is relevant if
            ``ht_correlation_type="Forced Convection"``. The default is ``"X"``.
        ht_correlation_value_type : str, optional
             Value type for the forced convection correlation option.
             This parameter is relevant if ``ht_correlation_type="Forced Convection"``.
             Options are "Average Values" and "Local Values". The default is
             ``"Average Values"``.
        ht_correlation_free_stream_velocity : str or float, optional
             Free stream flow velocity. This parameter is relevant if
             ``ht_correlation_type="Forced Convection"``. If a float value
             is specified, the default unit is ``m_per_sec``. The default is
             ``"1m_per_sec"``.
        ht_correlation_surface : str, optional
            Surface type for the natural convection correlation option.
            This parameter is relevant if ``ht_correlation_type="Natural Convection"``.
            Options are "Top", "Bottom", and "Vertical". The default is ``"Vertical"``.
        ht_correlation_amb_temperature : str or float, optional
            Ambient temperature for the natural convection correlation option.
            This parameter is relevant if ``ht_correlation_type="Natural Convection"``.
            If a float value is specified, the default unit is degrees Celsius.
            The default is ``"AmbientTemp"``.
        shell_conduction : bool, optional
            Whether to use the shell conduction option. The default is ``False``.
        ext_surf_rad : bool, optional
            Whether to use the external surface radiation option. This parameter
            is relevant if ``ext_condition="Heat Transfer Coefficient"``. The
            default is ``False``.
        ext_surf_rad_material : str, optional
            Surface material for the external surface radiation option. This parameter
            is relevant if ``ext_surf_rad=True``. The default is ``"Stainless-steel-cleaned"``.
        ext_surf_rad_ref_temp : str or float, optional
             Reference temperature for the external surface radiation option. This parameter
             is relevant if  ``ext_surf_rad=True``.  If a float value is specified, the default
             unit is degrees Celsius. The default is ``"AmbientTemp"``.
        ext_surf_rad_view_factor : str or float, optional
            View factor for the external surface radiation option. The default is ``"1"``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        References
        ----------

        >>> oModule.AssignStationaryWallBoundary
        """
        if not name:
            name = generate_unique_name("StationaryWall")
        if isinstance(geometry, str):
            geometry = [geometry]
        elif isinstance(geometry, int):
            geometry = [geometry]
        if not isinstance(thickness, str):
            thickness = "{}{}".format(thickness, self.modeler.model_units)
        if not isinstance(heat_flux, str):
            heat_flux = "{}irrad_W_per_m2".format(heat_flux)
        if not isinstance(temperature, str):
            temperature = "{}cel".format(temperature)
        if not isinstance(htc, str):
            htc = "{}w_per_m2kel".format(htc)
        if not isinstance(ref_temperature, str):
            ref_temperature = "{}cel".format(ref_temperature)
        if not isinstance(ht_correlation_free_stream_velocity, str):
            ht_correlation_free_stream_velocity = "{}m_per_sec".format(ht_correlation_free_stream_velocity)
        if not isinstance(ht_correlation_amb_temperature, str):
            ht_correlation_amb_temperature = "{}cel".format(ht_correlation_amb_temperature)
        if not isinstance(ext_surf_rad_view_factor, str):
            ext_surf_rad_view_factor = str(ext_surf_rad_view_factor)

        props = {}
        if isinstance(geometry[0], int):
            props["Faces"] = geometry
        else:
            props["Objects"] = geometry
        props["Thickness"] = (thickness,)
        props["Solid Material"] = material
        props["External Condition"] = boundary_condition
        props["Heat Flux"] = heat_flux
        props["Temperature"] = temperature
        if htc_dataset is None:
            props["Heat Transfer Coefficient"] = htc
        else:
            props["Heat Transfer Coefficient Variation Data"] = {
                "Variation Type": "Temp Dep",
                "Variation Function": "Piecewise Linear",
                "Variation Value": '["1w_per_m2kel", "pwl({},Temp)"]'.format(htc_dataset),
            }
        props["Reference Temperature"] = ref_temperature
        props["Heat Transfer Data"] = {
            "Heat Transfer Correlation": ht_correlation,
            "Heat Transfer Convection Type": "Forced Convection",
        }
        if ht_correlation:
            props["Heat Transfer Data"].update(
                {
                    "Heat Transfer Correlation": True,
                    "Heat Transfer Convection Type": ht_correlation_type,
                    "Heat Transfer Convection Fluid Material": ht_correlation_fluid,
                }
            )
            if ht_correlation_type == "Forced Convection":
                props["Heat Transfer Data"].update(
                    {
                        "Flow Type": ht_correlation_flow_type,
                        "Flow Direction": ht_correlation_flow_direction,
                        "Heat Transfer Coeff Value Type": ht_correlation_value_type,
                        "Stream Velocity": ht_correlation_free_stream_velocity,
                    }
                )
            elif ht_correlation_type == "Natural Convection":
                props["Heat Transfer Data"].update(
                    {"Surface": ht_correlation_surface, "Ambient Temperature": ht_correlation_amb_temperature}
                )
        props["Radiation"] = {"Radiate": radiate, "RadiateTo": "AllObjects", "Surface Material": radiate_surf_mat}
        props["Shell Conduction"] = shell_conduction
        props["External Surface Radiation"] = ext_surf_rad
        props["External Material"] = ext_surf_rad_material
        props["External Radiation Reference Temperature"] = ext_surf_rad_ref_temp
        props["External Radiation View Factor"] = ext_surf_rad_view_factor
        bound = BoundaryObject(self, name, props, "Stationary Wall")
        if bound.create():
            self.boundaries.append(bound)
        return bound

    @pyaedt_function_handler()
    def assign_stationary_wall_with_heat_flux(
        self,
        geometry,
        name=None,
        heat_flux="0irrad_W_per_m2",
        thickness="0mm",
        material="Al-Extruded",
        radiate=False,
        radiate_surf_mat="Steel-oxidised-surface",
        shell_conduction=False,
    ):
        """Assign a surface wall boundary condition with specified heat flux.

        Parameters
        ----------
        geometry : str or int
            Name of the surface object or ID of the face.
        name : str, optional
            Name of the boundary condition. The default is ``None``.
        heat_flux : str or float, optional
            Heat flux to assign to the wall. If a float value is
            specified, the unit is ``irrad_W_per_m2``. The default is
            ``"0irrad_W_per_m2"``.
        thickness : str or float, optional
            Thickness of the wall. If a float value is specified, the unit is the
            current unit system set in Icepak. The default is ``"0mm"``.
        material : str, optional
            Solid material of the wall. This parameter is relevant if the thickness
            is non-zero. The default is ``"Al-Extruded"``.
        radiate : bool, optional
            Whether to enable the inner surface radiation option. The default is ``False``.
        radiate_surf_mat : str, optional
            Surface material for the inner surface radiation. This parameter is
            relevant if ``radiate`` is enabled. The default is ``"Steel-oxidised-surface``.
        shell_conduction : bool, optional
            Whether to use the shell conduction option. The default is ``False``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        References
        ----------

        >>> oModule.AssignStationaryWallBoundary
        """
        return self.assign_stationary_wall(
            geometry,
            "Heat Flux",
            name=name,
            heat_flux=heat_flux,
            thickness=thickness,
            material=material,
            radiate=radiate,
            radiate_surf_mat=radiate_surf_mat,
            shell_conduction=shell_conduction,
        )

    @pyaedt_function_handler()
    def assign_stationary_wall_with_temperature(
        self,
        geometry,
        name=None,
        temperature="0cel",
        thickness="0mm",
        material="Al-Extruded",
        radiate=False,
        radiate_surf_mat="Steel-oxidised-surface",
        shell_conduction=False,
    ):
        """Assign a surface wall boundary condition with specified temperature.

        Parameters
        ----------
        geometry : str or int
            Name of the surface object or ID of the face.
        name : str, optional
            Name of the boundary condition. The default is ``None``.
        temperature : str or float, optional
            Temperature to assign to the wall. If a float value is specified,
            the unit is degrees Celsius. The default is ``"0cel"``.
        thickness : str or float, optional
            Thickness of the wall. If a float value is specified used, the unit is the
            current unit system set in Icepak. The default is ``"0mm"``.
        material : str, optional
            Solid material of the wall. This parameter is relevant if the
            thickness is a non-zero value. The default is ``"Al-Extruded"``.
        radiate : bool, optional
            Whether to enable the inner surface radiation option. The default is ``False``.
        radiate_surf_mat : str, optional
            Surface material to use for inner surface radiation. This parameter is relevant
            if ``radiate`` is enabled. The default is ``"Steel-oxidised-surface``.
        shell_conduction : bool, optional
            Whether to use the shell conduction option. The default is ``False``.


        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        References
        ----------

        >>> oModule.AssignStationaryWallBoundary
        """
        return self.assign_stationary_wall(
            geometry,
            "Temperature",
            name=name,
            temperature=temperature,
            thickness=thickness,
            material=material,
            radiate=radiate,
            radiate_surf_mat=radiate_surf_mat,
            shell_conduction=shell_conduction,
        )

    @pyaedt_function_handler()
    def assign_stationary_wall_with_htc(
        self,
        geometry,
        name=None,
        thickness="0mm",
        material="Al-Extruded",
        htc="0w_per_m2kel",
        htc_dataset=None,
        ref_temperature="AmbientTemp",
        ht_correlation=False,
        ht_correlation_type="Natural Convection",
        ht_correlation_fluid="air",
        ht_correlation_flow_type="Turbulent",
        ht_correlation_flow_direction="X",
        ht_correlation_value_type="Average Values",
        ht_correlation_free_stream_velocity="1m_per_sec",
        ht_correlation_surface="Vertical",
        ht_correlation_amb_temperature="AmbientTemp",
        ext_surf_rad=False,
        ext_surf_rad_material="Stainless-steel-cleaned",
        ext_surf_rad_ref_temp="AmbientTemp",
        ext_surf_rad_view_factor="1",
        radiate=False,
        radiate_surf_mat="Steel-oxidised-surface",
        shell_conduction=False,
    ):
        """Assign a surface wall boundary condition with specified heat transfer coefficient.

        Parameters
        ----------
        geometry : str or int
            Name of the surface object or id of the face.
        name : str, optional
            Name of the boundary condition. The default is ``None``.
        htc : str or float, optional
            Heat transfer coefficient to assign to the wall. If a float value
            is specified, the unit is ``w_per_m2kel``. The default is
            ``"0w_per_m2kel"``.
        thickness : str or float, optional
            Thickness of the wall. If a float value is specified, the unit is the
            current unit system set in Icepak. The default is ``"0mm"``.
        htc_dataset : str, optional
            Dataset that represents the dependency of the heat transfer
            coefficient on temperature. This parameter is relevant if
            ``ext_condition="Heat Transfer Coefficient"``. The default is ``None``.
        ref_temperature : str or float, optional
            Reference temperature for the definition of the heat transfer
            coefficient. This parameter is relevant if
            ``ext_condition="Heat Transfer Coefficient"``. The default is ``"AmbientTemp"``.
        material : str, optional
            Solid material of the wall. This parameter is relevant if the thickness
            is non-zero. The default is ``"Al-Extruded"``.
        radiate : bool, optional
            Whether to enable the inner surface radiation option. The default is ``False``.
        radiate_surf_mat : str, optional
            Surface material for inner surface radiation. This parameter is relevant
            if ``radiate`` is enabled. The default is ``"Steel-oxidised-surface``.
        ht_correlation : bool, optional
            Whether to use the correlation option to compute the heat transfer
            coefficient. The default is ``False``.
        ht_correlation_type : str, optional
            Correlation type for the correlation option. This parameter is
            relevant if ``ht_correlation=True``. Options are "Natural Convection"
            and "Forced Convection". The default is ``"Natural Convection"``.
        ht_correlation_fluid : str, optional
            Fluid for the correlation option. This parameter is relevant if
            ``ht_correlation=True``. The default is ``"air"``.
        ht_correlation_flow_type : str, optional
            Type of flow for the correlation option. This parameter is relevant
            if ``ht_correlation=True``. Options are ``"Turbulent"`` and ``"Laminar"``.
            The default is ``"Turbulent"``.
        ht_correlation_flow_direction : str, optional
            Flow direction for the correlation option. This parameter is relevant
            if ``ht_correlation_type="Forced Convection"``. The default is ``"X"``.
        ht_correlation_value_type : str, optional
             Value type for the forced convection correlation option. This
             parameter is relevant if ``ht_correlation_type="Forced Convection"``.
             Options are "Average Values" and "Local Values". The default
             is ``"Average Values"``.
        ht_correlation_free_stream_velocity : str or float, optional
             Free stream flow velocity. This parameter is relevant if
             ``ht_correlation_type="Forced Convection"``.  If a float
             value is specified, ``m_per_sec`` is the unit. The default
             is ``"1m_per_sec"``.
        ht_correlation_surface : str, optional
            Surface for the natural convection correlation option. This parameter is
            relevant if ``ht_correlation_type="Natural Convection"``. Options are "Top",
            "Bottom", and "Vertical". The default is ``"Vertical"``.
        ht_correlation_amb_temperature : str or float, optional
            Ambient temperature for the natural convection correlation option.
            This parameter is relevant if ``ht_correlation_type="Natural Convection"``.
            If a float value is specified, the default unit is degrees Celsius. The
            default is ``"AmbientTemp"``.
        shell_conduction : bool, optional
            Whether to use the shell conduction option. The default is ``False``.
        ext_surf_rad : bool, optional
            Whether to use the external surface radiation option. This parameter
            is relevant if ``ext_condition="Heat Transfer Coefficient"``. The default
            is ``False``.
        ext_surf_rad_material : str, optional
            Surface material for the external surface radiation option. This parameter is
            relevant if ``ext_surf_rad=True``. The default is ``"Stainless-steel-cleaned"``.
        ext_surf_rad_ref_temp : str or float, optional
             Reference temperature for the external surface radiation option. This
             parameter is relevant if ``ext_surf_rad=True``. If a float value is
             specified, the default unit is degrees Celsius. The default is
             ``"AmbientTemp"``.
        ext_surf_rad_view_factor : str or float, optional
            View factor for the external surface radiation option. The default is ``"1"``.


        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        References
        ----------

        >>> oModule.AssignStationaryWallBoundary
        """
        return self.assign_stationary_wall(
            geometry,
            "Heat Transfer Coefficient",
            name=name,
            thickness=thickness,
            material=material,
            htc=htc,
            htc_dataset=htc_dataset,
            ref_temperature=ref_temperature,
            ht_correlation=ht_correlation,
            ht_correlation_type=ht_correlation_type,
            ht_correlation_fluid=ht_correlation_fluid,
            ht_correlation_flow_type=ht_correlation_flow_type,
            ht_correlation_flow_direction=ht_correlation_flow_direction,
            ht_correlation_value_type=ht_correlation_value_type,
            ht_correlation_free_stream_velocity=ht_correlation_free_stream_velocity,
            ht_correlation_surface=ht_correlation_amb_temperature,
            ht_correlation_amb_temperature=ht_correlation_surface,
            ext_surf_rad=ext_surf_rad,
            ext_surf_rad_material=ext_surf_rad_material,
            ext_surf_rad_ref_temp=ext_surf_rad_ref_temp,
            ext_surf_rad_view_factor=ext_surf_rad_view_factor,
            radiate=radiate,
            radiate_surf_mat=radiate_surf_mat,
            shell_conduction=shell_conduction,
        )
