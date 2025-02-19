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

"""This module contains the ``Mechanical`` class."""

from __future__ import absolute_import  # noreorder

from ansys.aedt.core.application.analysis_3d import FieldAnalysis3D
from ansys.aedt.core.generic.constants import SOLUTIONS
from ansys.aedt.core.generic.errors import AEDTRuntimeError
from ansys.aedt.core.generic.general_methods import generate_unique_name
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.mixins import CreateBoundaryMixin
from ansys.aedt.core.modules.setup_templates import SetupKeys


class Mechanical(FieldAnalysis3D, CreateBoundaryMixin):
    """Provides the Mechanical application interface.

    Parameters
    ----------
    project : str, optional
        Name of the project to select or the full path to the project
        or AEDTZ archive to open.  The default is ``None``, in which
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
        Whether to launch AEDT in the non-graphical mode. The default
        is ``False``, in which case AEDT is launched in the graphical mode.
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
        Machine name to connect the oDesktop session to. Works only in 2022R2 and
        later. The remote server must be up and running with the command
        `"ansysedt.exe -grpcsrv portnum"`. If the machine is `"localhost"`,
        the server also starts if not present.
    port : int, optional
        Port number on which to start the oDesktop communication on an already existing server.
        This parameter is ignored when creating a new server. It works only in 2022 R2 or
        later. The remote server must be up and running with the command `"ansysedt.exe -grpcsrv portnum"`.
    aedt_process_id : int, optional
        Process ID for the instance of AEDT to point PyAEDT at. The default is
        ``None``. This parameter is only used when ``new_desktop = False``.
    remove_lock : bool, optional
        Whether to remove lock to project before opening it or not.
        The default is ``False``, which means to not unlock
        the existing project if needed and raise an exception.

    Examples
    --------
    Create an instance of Mechanical and connect to an existing
    HFSS design or create a new HFSS design if one does not exist.

    >>> from ansys.aedt.core import Mechanical
    >>> aedtapp = Mechanical()

    Create an instance of Mechanical and link to a project named
    ``"projectname"``. If this project does not exist, create one with
    this name.

    >>> aedtapp = Mechanical(projectname)

    Create an instance of Mechanical and link to a design named
    ``"designname"`` in a project named ``"projectname"``.

    >>> aedtapp = Mechanical(projectname,designame)

    Create an instance of Mechanical and open the specified
    project, which is named ``"myfile.aedt"``.

    >>> aedtapp = Mechanical("myfile.aedt")

    Create a ``Desktop on 2025 R1`` object and then create an
    ``Mechanical`` object and open the specified project, which is
    named ``"myfile.aedt"``.

    >>> aedtapp = Mechanical(version=25.1, project="myfile.aedt")

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
        FieldAnalysis3D.__init__(
            self,
            "Mechanical",
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

    def _init_from_design(self, *args, **kwargs):
        self.__init__(*args, **kwargs)

    @pyaedt_function_handler(
        designname="design",
        setupname="setup",
        sweepname="sweep",
        paramlist="parameters",
        object_list="assignment",
    )
    def assign_em_losses(
        self,
        design="HFSSDesign1",
        setup="Setup1",
        sweep="LastAdaptive",
        map_frequency=None,
        surface_objects=None,
        source_project_name=None,
        parameters=None,
        assignment=None,
    ):
        """Map EM losses to a Mechanical design.

        Parameters
        ----------
        design : str, optional
            Name of the design of the source mapping. The default is ``"HFSSDesign1"``.
        setup : str, optional
            Name of the EM setup. The default is ``"Setup1"``.
        sweep : str, optional
            Name of the EM sweep to use for the mapping. The default is ``"LastAdaptive"``.
        map_frequency : str, optional
            Frequency to map. The default is ``None``. The value must be ``None`` for
            Eigenmode analysis.
        surface_objects : list, optional
            List objects in the source that are metals. The default is ``None``.
        source_project_name : str, optional
            Name of the source project. The default is ``None``, in which case
            the source from the same project is used.
        parameters : list, optional
            List of all parameters in the EM to map. The default is ``None``.
        assignment : list, optional
             The default is ``None``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryObject`

        References
        ----------
        >>> oModule.AssignEMLoss
        """
        if self.solution_type not in (SOLUTIONS.Mechanical.Thermal, SOLUTIONS.Mechanical.SteadyStateThermal):
            raise AEDTRuntimeError("This method works only in a Mechanical Thermal analysis.")

        if surface_objects is None:
            surface_objects = []
        if parameters is None:
            parameters = []
        if assignment is None:
            assignment = []

        self.logger.info("Mapping HFSS EM Loss")
        oName = self.project_name
        if oName == source_project_name or source_project_name is None:
            projname = "This Project*"
        else:
            projname = source_project_name + ".aedt"
        #
        # Generate a list of model objects from the lists made previously and use to map the HFSS losses into Icepak.
        #
        if not assignment:
            allObjects = self.modeler.object_names
        else:
            allObjects = surface_objects + assignment[:]
        surfaces = surface_objects
        if map_frequency:
            intr = [map_frequency]
        else:
            intr = []

        argparam = {}

        variations = self.available_variations.get_independent_nominal_values()

        for key, value in variations.items():
            argparam[key] = value

        for el in parameters:
            argparam[el] = el

        props = {
            "Objects": allObjects,
            "allObjects": False,
            "Project": projname,
            "projname": "ElectronicsDesktop",
            "Design": design,
            "Soln": setup + " : " + sweep,
            "Params": argparam,
            "ForceSourceToSolve": True,
            "PreservePartnerSoln": True,
            "PathRelativeTo": "TargetProject",
        }
        if intr:
            props["Intrinsics"] = intr
            props["SurfaceOnly"] = surfaces

        name = generate_unique_name("EMLoss")
        return self._create_boundary(name, props, "EMLoss")

    @pyaedt_function_handler(
        designname="design",
        setupname="setup",
        sweepname="sweep",
        paramlist="parameters",
        object_list="assignment",
    )
    def assign_thermal_map(
        self,
        assignment,
        design="IcepakDesign1",
        setup="Setup1",
        sweep="SteadyState",
        source_project_name=None,
        parameters=None,
    ):
        """Map thermal losses to a Mechanical design.

        .. note::
           This method works in 2021 R2 only when coupled with Icepak.

        Parameters
        ----------
        assignment : list

        design : str, optional
            Name of the design with the source mapping. The default is ``"IcepakDesign1"``.
        setup : str, optional
            Name of the EM setup. The default is ``"Setup1"``.
        sweep : str, optional
            Name of the EM sweep to use for the mapping. The default is ``"SteadyState"``.
        source_project_name : str, optional
            Name of the source project. The default is ``None``, in which case the
            source from the same project is used.
        parameters : list, optional
            List of all parameters in the EM to map. The default is ``None``.

        Returns
        -------
        :class:`aedt.modules.boundary.Boundary object`
            Boundary object.

        References
        ----------
        >>> oModule.AssignThermalCondition
        """
        if self.solution_type != SOLUTIONS.Mechanical.Structural:
            raise AEDTRuntimeError("This method works only in a Mechanical Structural analysis.")

        if parameters is None:
            parameters = []

        self.logger.info("Mapping HFSS EM Loss")
        oName = self.project_name
        if oName == source_project_name or source_project_name is None:
            projname = "This Project*"
        else:
            projname = source_project_name + ".aedt"
        #
        # Generate a list of model objects from the lists made previously and use to map the HFSS losses into Icepak.
        #
        assignment = self.modeler.convert_to_selections(assignment, True)
        if not assignment:
            all_objects = self.modeler.object_names
        else:
            all_objects = assignment[:]
        argparam = {}

        variations = self.available_variations.get_independent_nominal_values()
        for key, value in variations.items():
            argparam[key] = value

        for el in parameters:
            argparam[el] = el

        props = {
            "Objects": all_objects,
            "Uniform": False,
            "Project": projname,
            "Product": "ElectronicsDesktop",
            "Design": design,
            "Soln": setup + " : " + sweep,
            "Params": argparam,
            "ForceSourceToSolve": True,
            "PreservePartnerSoln": True,
            "PathRelativeTo": "TargetProject",
        }

        name = generate_unique_name("ThermalLink")
        return self._create_boundary(name, props, "ThermalCondition")

    @pyaedt_function_handler(objects_list="assignment", boundary_name="name")
    def assign_uniform_convection(
        self,
        assignment,
        convection_value=1.0,
        convection_unit="w_per_m2kel",
        temperature="AmbientTemp",
        name="",
    ):
        """Assign a uniform convection to the face list.

        Parameters
        ----------
        assignment : list
            List of objects, faces, or both.
        convection_value : float, optional
            Convection value. The default is ``"1.0"``.
        convection_unit : str, optional
            Units for the convection value. The default is ``"w_per_m2kel"``.
        temperature : str, optional
            Temperature. The default is ``"AmbientTemp"``.
        name : str, optional
            Name of the boundary. The default is ``""``, in which case the default
            name is used.

        Returns
        -------
        :class:`aedt.modules.boundary.Boundary object`
            Boundary object.

        References
        ----------
        >>> oModule.AssignConvection
        """
        if self.solution_type not in (SOLUTIONS.Mechanical.Thermal, SOLUTIONS.Mechanical.SteadyStateThermal):
            raise AEDTRuntimeError("This method works only in a Mechanical Thermal analysis.")

        props = {}
        assignment = self.modeler.convert_to_selections(assignment, True)

        if isinstance(assignment, list):
            if isinstance(assignment[0], str):
                props["Objects"] = assignment
            else:
                props["Faces"] = assignment

        props["Temperature"] = temperature
        props["Uniform"] = True
        props["FilmCoeff"] = str(convection_value) + convection_unit

        if not name:
            name = generate_unique_name("Convection")
        return self._create_boundary(name, props, "Convection")

    @pyaedt_function_handler(objects_list="assignment", boundary_name="name")
    def assign_uniform_temperature(self, assignment, temperature="AmbientTemp", name=""):
        """Assign a uniform temperature boundary.

        .. note::
            This method works only in a Mechanical Thermal analysis.

        Parameters
        ----------
        assignment : list
            List of objects, faces, or both.
        temperature : str, optional.
            Type of the temperature. The default is ``"AmbientTemp"``.
        name : str, optional
            Name of the boundary. The default is ``""``.

        Returns
        -------
        :class:`aedt.modules.boundary.Boundary object`
            Boundary object.

        References
        ----------
        >>> oModule.AssignTemperature
        """
        if self.solution_type not in (SOLUTIONS.Mechanical.Thermal, SOLUTIONS.Mechanical.SteadyStateThermal):
            raise AEDTRuntimeError("This method works only in a Mechanical Thermal analysis.")

        props = {}
        assignment = self.modeler.convert_to_selections(assignment, True)

        if isinstance(assignment, list):
            if isinstance(assignment[0], str):
                props["Objects"] = assignment
            else:
                props["Faces"] = assignment

        props["Temperature"] = temperature

        if not name:
            name = generate_unique_name("Temp")
        return self._create_boundary(name, props, "Temperature")

    @pyaedt_function_handler(objects_list="assignment", boundary_name="name")
    def assign_frictionless_support(self, assignment, name=""):
        """Assign a Mechanical frictionless support.

        .. note::
            This method works only in a Mechanical Structural analysis.

        Parameters
        ----------
        assignment : list
            List of faces to apply to the frictionless support.
        name : str, optional
            Name of the boundary. The default is ``""``, in which case the
            default name is used.

        Returns
        -------
        :class:`aedt.modules.boundary.Boundary object`
            Boundary object.

        References
        ----------
        >>> oModule.AssignFrictionlessSupport
        """
        if self.solution_type not in (SOLUTIONS.Mechanical.Structural, SOLUTIONS.Mechanical.Modal):
            raise AEDTRuntimeError("This method works only in a Mechanical Structural analysis.")

        props = {}
        assignment = self.modeler.convert_to_selections(assignment, True)
        if type(assignment) is list:
            if type(assignment[0]) is str:
                props["Objects"] = assignment
            else:
                props["Faces"] = assignment

        if not name:
            name = generate_unique_name("Temp")
        return self._create_boundary(name, props, "Frictionless")

    @pyaedt_function_handler(objects_list="assignment", boundary_name="name")
    def assign_fixed_support(self, assignment, name=""):
        """Assign a Mechanical fixed support.

        .. note::
           This method works only in a Mechanical Structural analysis.

        Parameters
        ----------
        assignment : list
            List of faces to apply to the fixed support.
        name : str, optional
            Name of the boundary. The default is ``""``, in which case
            the default name is used.

        Returns
        -------
        aedt.modules.boundary.Boundary
            Boundary object.

        References
        ----------
        >>> oModule.AssignFixedSupport
        """
        if self.solution_type not in (SOLUTIONS.Mechanical.Structural, SOLUTIONS.Mechanical.Modal):
            raise AEDTRuntimeError("This method works only in a Mechanical Structural analysis.")

        props = {}
        assignment = self.modeler.convert_to_selections(assignment, True)

        if type(assignment) is list:
            props["Faces"] = assignment

        if not name:
            name = generate_unique_name("Temp")
        return self._create_boundary(name, props, "FixedSupport")

    @property
    def existing_analysis_sweeps(self):
        """Existing analysis sweeps in the design.

        Returns
        -------
        list
            List of existing analysis sweeps.

        References
        ----------
        >>> oModule.GetSetups
        """
        setup_list = self.existing_analysis_setups
        sweep_list = []
        for el in setup_list:
            sweep_list.append(el + " : Solution")
        return sweep_list

    @pyaedt_function_handler(objects_list="assignment", boundary_name="name")
    def assign_heat_flux(self, assignment, heat_flux_type, value, name=""):
        """Assign heat flux boundary condition to an object or face list.

        Parameters
        ----------
        assignment : list
            List of objects, faces, or both.
        heat_flux_type : str
            Type of the heat flux. Options are ``"Total Power"`` or ``"Surface Flux"``.
        value : str
            Value of heat flux with units.
        name : str, optional
            Name of the boundary. The default is ``""``, in which case the default
            name is used.

        Returns
        -------
        :class:`aedt.modules.boundary.Boundary object`
            Boundary object.

        References
        ----------
        >>> oModule.AssignHeatFlux
        """
        if self.solution_type not in (SOLUTIONS.Mechanical.Thermal, SOLUTIONS.Mechanical.SteadyStateThermal):
            raise AEDTRuntimeError("This method works only in a Mechanical Thermal analysis.")

        props = {}
        assignment = self.modeler.convert_to_selections(assignment, True)
        if type(assignment) is list:
            if type(assignment[0]) is str:
                props["Objects"] = assignment
            else:
                props["Faces"] = assignment

        if heat_flux_type == "Total Power":
            props["TotalPower"] = value
        else:
            props["SurfaceFlux"] = value

        if not name:
            name = generate_unique_name("HeatFlux")
        return self._create_boundary(name, props, "HeatFlux")

    @pyaedt_function_handler(objects_list="assignment", boundary_name="name")
    def assign_heat_generation(self, assignment, value, name=""):
        """Assign a heat generation boundary condition to an object list.

        Parameters
        ----------
        assignment : list
            List of objects.
        value : str
            Value of heat generation with units.
        name : str, optional
            Name of the boundary. The default is ``""``, in which case the default
            name is used.

        Returns
        -------
        :class:`aedt.modules.boundary.Boundary object`
            Boundary object.

        References
        ----------
        >>> oModule.AssignHeatGeneration
        """
        if self.solution_type not in (SOLUTIONS.Mechanical.Thermal, SOLUTIONS.Mechanical.SteadyStateThermal):
            raise AEDTRuntimeError("This method works only in a Mechanical Thermal analysis.")

        props = {}
        assignment = self.modeler.convert_to_selections(assignment, True)
        if type(assignment) is list:
            props["Objects"] = assignment

        props["TotalPower"] = value

        if not name:
            name = generate_unique_name("HeatGeneration")
        return self._create_boundary(name, props, "HeatGeneration")

    @pyaedt_function_handler()
    def assign_2way_coupling(self, setup=None, number_of_iterations=2):
        """Assign two-way coupling to a setup.

        Parameters
        ----------
        setup : str, optional
            Name of the setup. The default is ``None``, in which case the active setup is used.
        number_of_iterations : int, optional
            Number of iterations. The default is ``2``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.AddTwoWayCoupling

        Examples
        --------
        >>> from ansys.aedt.core import Mechanical
        >>> mech = Mechanical()
        >>> setup = mech.create_setup()
        >>> mech.assign_2way_coupling(setup.name, 1)
        >>> mech.release_desktop()

        """
        if not setup:
            if self.setups:
                setup = self.setups[0].name
            else:
                self.logger.error("Setup is not defined.")
                return False

        self.oanalysis.AddTwoWayCoupling(
            setup,
            [
                "NAME:Options",
                "NumCouplingIters:=",
                number_of_iterations,
            ],
        )
        return True

    @pyaedt_function_handler(setupname="name", setuptype="setup_type")
    def create_setup(self, name="MySetupAuto", setup_type=None, **kwargs):
        """Create an analysis setup for Mechanical.

        Optional arguments are passed along with ``setup_type`` and ``name``. Keyword
        names correspond to the ``setup_type`` corresponding to the native AEDT API.  The list of
        keywords here is not exhaustive.

        Parameters
        ----------
        name : str, optional
            Name of the setup. The default is ``"Setup1"``.
        setup_type : int, str, optional
            Type of the setup. Options are  ``"IcepakSteadyState"`` and
            ``"IcepakTransient"``. The default is ``"IcepakSteadyState"``.
        **kwargs : dict, optional
            Available keys depend on the setup chosen.
            For more information, see :doc:`../SetupTemplatesMechanical`.

        Returns
        -------
        :class:`ansys.aedt.core.modules.solve_setup.SetupHFSS`
            Solver Setup object.

        References
        ----------
        >>> oModule.InsertSetup

        Examples
        --------

        >>> from ansys.aedt.core import Mechanical
        >>> app = Mechanical()
        >>> app.create_setup(name="Setup1",MaxModes=6)

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
