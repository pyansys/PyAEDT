"""This module contains these classes: ``Hfss`` and ``BoundaryType``."""

from __future__ import absolute_import  # noreorder

import ast
import math
import os
import tempfile
import warnings
from collections import OrderedDict

from pyaedt import settings
from pyaedt.application.Analysis3D import FieldAnalysis3D
from pyaedt.generic.constants import INFINITE_SPHERE_TYPE
from pyaedt.generic.DataHandlers import _dict2arg
from pyaedt.generic.DataHandlers import json_to_dict
from pyaedt.generic.general_methods import generate_unique_name
from pyaedt.generic.general_methods import open_file
from pyaedt.generic.general_methods import parse_excitation_file
from pyaedt.generic.general_methods import pyaedt_function_handler
from pyaedt.modeler.advanced_cad.actors import Radar
from pyaedt.modeler.cad.components_3d import UserDefinedComponent
from pyaedt.modeler.geometry_operators import GeometryOperators
from pyaedt.modules.Boundary import BoundaryObject
from pyaedt.modules.Boundary import FarFieldSetup
from pyaedt.modules.Boundary import NativeComponentObject
from pyaedt.modules.Boundary import NearFieldSetup
from pyaedt.modules.solutions import FfdSolutionData


class Hfss(FieldAnalysis3D, object):
    """Provides the HFSS application interface.

    This class allows you to create an interactive instance of HFSS and
    connect to an existing HFSS design or create a new HFSS design if
    one does not exist.

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
        Whether to run AEDT in non-graphical mode. The default
        is ``False``, in which case AEDT is launched in graphical mode.
        This parameter is ignored when a script is launched within AEDT.
    new_desktop_session : bool, optional
        Whether to launch an instance of AEDT in a new thread, even if
        another instance of the ``specified_version`` is active on the
        machine. The default is ``False``. This parameter is ignored when
        a script is launched within AEDT.
    close_on_exit : bool, optional
        Whether to release AEDT on exit. The default is ``False``.
    student_version : bool, optional
        Whether to open the AEDT student version. The default is
        ``False``. This parameter is ignored when a script is launched
        within AEDT.
    machine : str, optional
        Machine name to connect the oDesktop session to. This parameter works only on
        2022 R2 or later. The remote Server must be up and running with the command
        `"ansysedt.exe -grpcsrv portnum"`. If the machine is `"localhost"`, the server
        starts if it is not present.
    port : int, optional
        Port number on which to start the oDesktop communication on an already existing server.
        This parameter is ignored when creating a new server. It works only in 2022 R2 or later.
        The remote server must be up and running with the command `"ansysedt.exe -grpcsrv portnum"`.
    aedt_process_id : int, optional
        Process ID for the instance of AEDT to point PyAEDT at. The default is
        ``None``. This parameter is only used when ``new_desktop_session = False``.

    Examples
    --------
    Create an instance of HFSS and connect to an existing HFSS
    design or create a new HFSS design if one does not exist.

    >>> from pyaedt import Hfss
    >>> hfss = Hfss()
    pyaedt INFO: No project is defined...
    pyaedt INFO: Active design is set to...


    Create an instance of HFSS and link to a project named
    ``HfssProject``. If this project does not exist, create one with
    this name.

    >>> hfss = Hfss("HfssProject")
    pyaedt INFO: Project HfssProject has been created.
    pyaedt INFO: No design is present. Inserting a new design.
    pyaedt INFO: Added design ...


    Create an instance of HFSS and link to a design named
    ``HfssDesign1`` in a project named ``HfssProject``.

    >>> hfss = Hfss("HfssProject","HfssDesign1")
    pyaedt INFO: Added design 'HfssDesign1' of type HFSS.


    Create an instance of HFSS and open the specified project,
    which is named ``"myfile.aedt"``.

    >>> hfss = Hfss("myfile.aedt")
    pyaedt INFO: Project myfile has been created.
    pyaedt INFO: No design is present. Inserting a new design.
    pyaedt INFO: Added design...


    Create an instance of HFSS using the 2021 R1 release and open
    the specified project, which is named ``"myfile2.aedt"``.

    >>> hfss = Hfss(specified_version="2021.2", projectname="myfile2.aedt")
    pyaedt INFO: Project myfile2 has been created.
    pyaedt INFO: No design is present. Inserting a new design.
    pyaedt INFO: Added design...


    Create an instance of HFSS using the 2021 R2 student version and open
    the specified project, which is named ``"myfile3.aedt"``.

    >>> hfss = Hfss(specified_version="2021.2", projectname="myfile3.aedt", student_version=True)
    pyaedt INFO: Project myfile3 has been created.
    pyaedt INFO: No design is present. Inserting a new design.
    pyaedt INFO: Added design...

    """

    # def __repr__(self):
    #     try:
    #         return "HFSS {} {}. ProjectName:{} DesignName:{} ".format(
    #             self._aedt_version, self.solution_type, self.project_name, self.design_name
    #         )
    #     except:
    #         return "HFSS Module"

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
            "HFSS",
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
        self._field_setups = []

    def __enter__(self):
        return self

    @property
    def field_setups(self):
        """List of AEDT radiation fields.

        Returns
        -------
        List of :class:`pyaedt.modules.Boundary.FarFieldSetup` and :class:`pyaedt.modules.Boundary.NearFieldSetup`
        """
        if not self._field_setups:
            self._field_setups = self._get_rad_fields()
        return self._field_setups

    @property
    def field_setup_names(self):
        """List of AEDT radiation field names.

        Returns
        -------
        List of str
        """
        return self.odesign.GetChildObject("Radiation").GetChildNames()

    class BoundaryType(object):
        """Creates and manages boundaries."""

        (PerfectE, PerfectH, Aperture, Radiation, Impedance, LayeredImp, LumpedRLC, FiniteCond, Hybrid) = range(0, 9)

    @property
    def hybrid(self):
        """HFSS hybrid mode for the active solution."""
        return self.design_solutions.hybrid

    @hybrid.setter
    @pyaedt_function_handler()
    def hybrid(self, value):
        self.design_solutions.hybrid = value

    @property
    def composite(self):
        """HFSS composite mode for the active solution."""
        return self.design_solutions.composite

    @composite.setter
    @pyaedt_function_handler()
    def composite(self, value):
        self.design_solutions.composite = value

    @pyaedt_function_handler()
    def set_auto_open(self, enable=True, boundary_type="Radiation"):
        """Set the HFSS auto open type.

        Parameters
        ----------
        enable : bool, optional
            Whether to enable the HFSS auto open option. The default is ``True``.
        boundary_type : str, optional
            Boundary type to use with auto open. Options are ``"Radiation"``,
            ``"FEBI"``, and ``"PML"``. The default is ``"Radiation"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------
        Enable auto open type for the PML boundary.

        >>> hfss.set_auto_open(True, "PML")
        """
        if enable and boundary_type not in ["Radiation", "FEBI", "PML"]:
            raise AttributeError("Wrong boundary type. Check Documentation for valid inputs")
        return self.design_solutions.set_auto_open(enable=enable, boundary_type=boundary_type)

    @pyaedt_function_handler()
    def _get_unique_source_name(self, source_name, root_name):
        if not source_name:
            source_name = generate_unique_name(root_name)
        elif source_name in self.excitations or source_name + ":1" in self.excitations:
            source_name = generate_unique_name(source_name)
        return source_name

    @pyaedt_function_handler()
    def _get_rad_fields(self):
        if not self.design_properties:
            return []
        fields = []
        if self.design_properties.get("RadField"):
            if self.design_properties["RadField"].get("FarFieldSetups"):
                for val in self.design_properties["RadField"]["FarFieldSetups"]:
                    p = self.design_properties["RadField"]["FarFieldSetups"][val]
                    if isinstance(p, (dict, OrderedDict)) and p.get("Type") == "Infinite Sphere":
                        fields.append(FarFieldSetup(self, val, p, "FarFieldSphere"))
            if self.design_properties["RadField"].get("NearFieldSetups"):
                for val in self.design_properties["RadField"]["NearFieldSetups"]:
                    p = self.design_properties["RadField"]["NearFieldSetups"][val]
                    if isinstance(p, (dict, OrderedDict)):
                        if p["Type"] == "Near Rectangle":
                            fields.append(NearFieldSetup(self, val, p, "NearFieldRectangle"))
                        elif p["Type"] == "Near Line":
                            fields.append(NearFieldSetup(self, val, p, "NearFieldLine"))
                        elif p["Type"] == "Near Box":
                            fields.append(NearFieldSetup(self, val, p, "NearFieldBox"))
                        elif p["Type"] == "Near Sphere":
                            fields.append(NearFieldSetup(self, val, p, "NearFieldSphere"))
        return fields

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
    def _create_lumped_driven(self, objectname, int_line_start, int_line_stop, impedance, portname, renorm, deemb):
        start = [str(i) + self.modeler.model_units for i in int_line_start]
        stop = [str(i) + self.modeler.model_units for i in int_line_stop]
        props = OrderedDict({})
        if isinstance(objectname, str):
            props["Objects"] = [objectname]
        else:
            props["Faces"] = [objectname]
        props["DoDeembed"] = deemb
        props["RenormalizeAllTerminals"] = renorm
        if renorm:
            props["Modes"] = OrderedDict(
                {
                    "Mode1": OrderedDict(
                        {
                            "ModeNum": 1,
                            "UseIntLine": True,
                            "IntLine": OrderedDict({"Start": start, "End": stop}),
                            "AlignmentGroup": 0,
                            "CharImp": "Zpi",
                            "RenormImp": str(impedance) + "ohm",
                        }
                    )
                }
            )
        else:
            props["Modes"] = OrderedDict(
                {
                    "Mode1": OrderedDict(
                        {
                            "ModeNum": 1,
                            "UseIntLine": True,
                            "IntLine": OrderedDict({"Start": start, "End": stop}),
                            "AlignmentGroup": 0,
                            "CharImp": "Zpi",
                        }
                    )
                }
            )
        props["ShowReporterFilter"] = False
        props["ReporterFilter"] = [True]
        props["Impedance"] = str(impedance) + "ohm"
        return self._create_boundary(portname, props, "Lumped Port")

    @pyaedt_function_handler()
    def _create_port_terminal(
        self, objectname, int_line_stop, portname, renorm=True, deembed=None, iswaveport=False, impedance=None
    ):
        ref_conductors = self.modeler.convert_to_selections(int_line_stop, True)
        props = OrderedDict()
        props["Faces"] = int(objectname)
        props["IsWavePort"] = iswaveport
        props["ReferenceConductors"] = ref_conductors
        props["RenormalizeModes"] = True
        ports = list(self.oboundary.GetExcitationsOfType("Terminal"))
        boundary = self._create_boundary(portname, props, "AutoIdentify")
        if boundary:
            new_ports = list(self.oboundary.GetExcitationsOfType("Terminal"))
            terminals = [i for i in new_ports if i not in ports]
            for count, terminal in enumerate(terminals, start=1):
                if impedance:
                    properties = [
                        "NAME:AllTabs",
                        [
                            "NAME:HfssTab",
                            ["NAME:PropServers", "BoundarySetup:" + terminal],
                            [
                                "NAME:ChangedProps",
                                ["NAME:Terminal Renormalizing Impedance", "Value:=", str(impedance) + "ohm"],
                            ],
                        ],
                    ]
                    try:
                        self.odesign.ChangeProperty(properties)
                    except:  # pragma: no cover
                        self.logger.warning("Failed to change terminal impedance.")
                if not renorm:
                    properties = [
                        "NAME:AllTabs",
                        [
                            "NAME:HfssTab",
                            ["NAME:PropServers", "BoundarySetup:" + boundary.name],
                            [
                                "NAME:ChangedProps",
                                ["NAME:Renorm All Terminals", "Value:=", False],
                            ],
                        ],
                    ]
                    try:
                        self.odesign.ChangeProperty(properties)
                    except:  # pragma: no cover
                        self.logger.warning("Failed to change normalization.")

                new_name = portname + "_T" + str(count)
                properties = [
                    "NAME:AllTabs",
                    [
                        "NAME:HfssTab",
                        ["NAME:PropServers", "BoundarySetup:" + terminal],
                        ["NAME:ChangedProps", ["NAME:Name", "Value:=", new_name]],
                    ],
                ]
                try:
                    self.odesign.ChangeProperty(properties)
                except:  # pragma: no cover
                    self.logger.warning("Failed to rename terminal {}.".format(terminal))

            if iswaveport:
                boundary.type = "Wave Port"
            else:
                boundary.type = "Lumped Port"
            props["Faces"] = [objectname]
            if iswaveport:
                props["NumModes"] = 1
                props["UseLineModeAlignment"] = 1
            if deembed is None:
                props["DoDeembed"] = False
                if iswaveport:
                    props["DeembedDist"] = self.modeler._arg_with_dim(0)
            else:
                props["DoDeembed"] = True
                if iswaveport:
                    props["DeembedDist"] = self.modeler._arg_with_dim(deembed)
            props["RenormalizeAllTerminals"] = renorm
            props["ShowReporterFilter"] = False
            props["UseAnalyticAlignment"] = False
            boundary.props = props
            boundary.update()
        return boundary

    @pyaedt_function_handler()
    def _create_circuit_port(self, edgelist, impedance, name, renorm, deemb, renorm_impedance=""):
        edgelist = self.modeler.convert_to_selections(edgelist, True)
        props = OrderedDict(
            {
                "Edges": edgelist,
                "Impedance": str(impedance) + "ohm",
                "DoDeembed": deemb,
                "RenormalizeAllTerminals": renorm,
            }
        )

        if "Modal" in self.solution_type:

            if renorm:
                if isinstance(renorm_impedance, (int, float)) or "i" not in renorm_impedance:
                    renorm_imp = str(renorm_impedance) + "ohm"
                else:
                    renorm_imp = "(" + renorm_impedance + ") ohm"
            else:
                renorm_imp = "0ohm"
            props["RenormImp"] = renorm_imp
        else:
            props["TerminalIDList"] = []
        return self._create_boundary(name, props, "Circuit Port")

    @pyaedt_function_handler()
    def _create_waveport_driven(
        self,
        objectname,
        int_line_start=None,
        int_line_stop=None,
        impedance=50,
        portname="",
        renorm=True,
        nummodes=1,
        deemb_distance=0,
    ):
        start = None
        stop = None
        if int_line_start and int_line_stop:
            start = [str(i) + self.modeler.model_units for i in int_line_start]
            stop = [str(i) + self.modeler.model_units for i in int_line_stop]
            useintline = True
        else:
            useintline = False

        props = OrderedDict({})
        if isinstance(objectname, int):
            props["Faces"] = [objectname]
        else:
            props["Objects"] = [objectname]
        props["NumModes"] = nummodes
        props["UseLineModeAlignment"] = False

        if deemb_distance != 0:
            props["DoDeembed"] = True
            props["DeembedDist"] = self.modeler._arg_with_dim(deemb_distance)
        else:
            props["DoDeembed"] = False
        props["RenormalizeAllTerminals"] = renorm
        modes = OrderedDict({})
        arg2 = []
        arg2.append("NAME:Modes")
        i = 1
        report_filter = []
        while i <= nummodes:
            if i == 1:
                mode = OrderedDict({})
                mode["ModeNum"] = i
                mode["UseIntLine"] = useintline
                if useintline:
                    mode["IntLine"] = OrderedDict({"Start": start, "End": stop})
                mode["AlignmentGroup"] = 0
                mode["CharImp"] = "Zpi"
                if renorm:
                    mode["RenormImp"] = str(impedance) + "ohm"
                modes["Mode1"] = mode
            else:
                mode = OrderedDict({})

                mode["ModeNum"] = i
                mode["UseIntLine"] = False
                mode["AlignmentGroup"] = 0
                mode["CharImp"] = "Zpi"
                if renorm:
                    mode["RenormImp"] = str(impedance) + "ohm"
                modes["Mode" + str(i)] = mode
            report_filter.append(True)
            i += 1
        props["Modes"] = modes
        props["ShowReporterFilter"] = False
        props["ReporterFilter"] = report_filter
        props["UseAnalyticAlignment"] = False
        return self._create_boundary(portname, props, "Wave Port")

    @pyaedt_function_handler()
    def assigncoating(
        self,
        obj,
        mat=None,
        cond=58000000,
        perm=1,
        usethickness=False,
        thickness="0.1mm",
        roughness="0um",
        isinfgnd=False,
        istwoside=False,
        isInternal=True,
        issheelElement=False,
        usehuray=False,
        radius="0.5um",
        ratio="2.9",
    ):
        """Assign finite conductivity to one or more objects of a given material.

        .. deprecated:: 0.4.5
           Use :func:`Hfss.assign_coating` instead.

        """

        warnings.warn("`assigncoating` is deprecated. Use `assign_coating` instead.", DeprecationWarning)
        self.assign_coating(
            obj,
            mat,
            cond,
            perm,
            usethickness,
            thickness,
            roughness,
            isinfgnd,
            istwoside,
            isInternal,
            issheelElement,
            usehuray,
            radius,
            ratio,
        )

    @pyaedt_function_handler()
    def assign_coating(
        self,
        obj,
        mat=None,
        cond=58000000,
        perm=1,
        usethickness=False,
        thickness="0.1mm",
        roughness="0um",
        isinfgnd=False,
        istwoside=False,
        isInternal=True,
        issheelElement=False,
        usehuray=False,
        radius="0.5um",
        ratio="2.9",
    ):
        """Assign finite conductivity to one or more objects or faces of a given material.

        Parameters
        ----------
        obj : str or list
            One or more objects or faces to assign finite conductivity to.
        mat : str, optional
            Material to use. The default is ``None``.
        cond : float, optional
            If no material is provided, a conductivity value must be supplied. The default is ``58000000``.
        perm : float, optional
            If no material is provided, a permittivity value must be supplied. The default is ``1``.
        usethickness : bool, optional
            Whether to use thickness. The default is ``False``.
        thickness : str, optional
            Thickness value if ``usethickness=True``. The default is ``"0.1mm"``.
        roughness : str, optional
            Roughness value  with units. The default is ``"0um"``.
        isinfgnd : bool, optional
            Whether the finite conductivity is an infinite ground. The default is ``False``.
        istwoside : bool, optional
            Whether the finite conductivity is two-sided. The default is ``False``.
        isInternal : bool, optional
            Whether the finite conductivity is internal. The default is ``True``.
        issheelElement : bool, optional
            The default is ``False``.
        usehuray : bool, optional
            Whether to use an Huray coefficient. The default is ``False``.
        radius : str, optional
            Radius value if ``usehuray=True``. The default is ``"0.5um"``.
        ratio : str, optional
            Ratio value if ``usehuray=True``. The default is ``"2.9"``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        References
        ----------

        >>> oModule.AssignFiniteCond

        Examples
        --------

        Create two cylinders in the XY working plane and assign a copper coating of 0.2 mm to the inner cylinder and
        outer face.
        >>> from pyaedt import Hfss
        >>> hfss = Hfss()
        >>> origin = hfss.modeler.Position(0, 0, 0)
        >>> inner = hfss.modeler.create_cylinder(
        ...     hfss.PLANE.XY, origin, 3, 200, 0, "inner"
        ... )
        >>> outer = hfss.modeler.create_cylinder(
        ...     hfss.PLANE.XY, origin, 4, 200, 0, "outer"
        ... )
        >>> coat = hfss.assign_coating(["inner", outer.faces[2].id], "copper", usethickness=True, thickness="0.2mm")

        """

        userlst = self.modeler.convert_to_selections(obj, True)
        lstobj = []
        lstface = []
        for selection in userlst:
            if selection in self.modeler.model_objects:
                lstobj.append(selection)
            elif isinstance(selection, int) and self.modeler._find_object_from_face_id(selection):
                lstface.append(selection)

        if not lstface and not lstobj:
            self.logger.warning("Objects or Faces selected do not exist in the design.")
            return False
        listobjname = ""
        props = {}
        if lstobj:
            listobjname = listobjname + "_" + "_".join(lstobj)
            props["Objects"] = lstobj
        if lstface:
            props["Faces"] = lstface
            lstface = [str(i) for i in lstface]
            listobjname = listobjname + "_" + "_".join(lstface)
        if mat:
            if self.materials[mat]:
                props["UseMaterial"] = True
                props["Material"] = self.materials[mat].name
            else:
                return False
        else:
            props["UseMaterial"] = False
            props["Conductivity"] = str(cond)
            props["Permeability"] = str(str(perm))
        props["UseThickness"] = usethickness
        if usethickness:
            props["Thickness"] = thickness
        if usehuray:
            props["Radius"] = str(radius)
            props["Ratio"] = str(ratio)
            props["InfGroundPlane"] = False
        else:
            props["Roughness"] = roughness
            props["InfGroundPlane"] = isinfgnd
        props["IsTwoSided"] = istwoside

        if istwoside:
            props["IsShellElement"] = issheelElement
        else:
            props["IsInternal"] = isInternal
        return self._create_boundary("Coating_" + listobjname[1:], props, "Finite Conductivity")

    @pyaedt_function_handler()
    def create_frequency_sweep(
        self,
        setupname,
        unit="GHz",
        freqstart=1e-3,
        freqstop=10,
        sweepname=None,
        num_of_freq_points=451,
        sweeptype="Interpolating",
        interpolation_tol=0.5,
        interpolation_max_solutions=250,
        save_fields=True,
        save_rad_fields=False,
    ):
        """Create a frequency sweep.

        .. deprecated:: 0.4.0
           Use :func:`Hfss.create_linear_count_sweep` instead.

        """
        warnings.warn(
            "`create_frequency_sweep` is deprecated. Use `create_linear_count_sweep` instead.",
            DeprecationWarning,
        )

        return self.create_linear_count_sweep(
            setupname=setupname,
            unit=unit,
            freqstart=freqstart,
            freqstop=freqstop,
            num_of_freq_points=num_of_freq_points,
            sweepname=sweepname,
            save_fields=save_fields,
            save_rad_fields=save_rad_fields,
            sweep_type=sweeptype,
            interpolation_tol=interpolation_tol,
            interpolation_max_solutions=interpolation_max_solutions,
        )

    @pyaedt_function_handler()
    def create_linear_count_sweep(
        self,
        setupname,
        unit,
        freqstart,
        freqstop,
        num_of_freq_points,
        sweepname=None,
        save_fields=True,
        save_rad_fields=False,
        sweep_type="Discrete",
        interpolation_tol=0.5,
        interpolation_max_solutions=250,
    ):
        """Create a sweep with a specified number of points.

        Parameters
        ----------
        setupname : str
            Name of the setup.
        unit : str
            Unit of the frequency. For example, ``"MHz"`` or ``"GHz"``.
        freqstart : float
            Starting frequency of the sweep, such as ``1``.
        freqstop : float
            Stopping frequency of the sweep.
        num_of_freq_points : int
            Number of frequency points in the range.
        sweepname : str, optional
            Name of the sweep. The default is ``None``.
        save_fields : bool, optional
            Whether to save the fields. The default is ``True``.
        save_rad_fields : bool, optional
            Whether to save the radiating fields. The default is ``False``.
        sweep_type : str, optional
            Type of the sweep. Options are ``"Fast"``, ``"Interpolating"``,
            and ``"Discrete"``. The default is ``"Discrete"``.
        interpolation_tol : float, optional
            Error tolerance threshold for the interpolation process. The default
            is ``0.5``.
        interpolation_max_solutions : int, optional
            Maximum number of solutions evaluated for the interpolation process.
            The default is ``250``.

        Returns
        -------
        :class:`pyaedt.modules.SetupTemplates.SweepHFSS` or bool
            Sweep object if successful, ``False`` otherwise.

        References
        ----------

        >>> oModule.InsertFrequencySweep

        Examples
        --------

        Create a setup named ``"LinearCountSetup"`` and use it in a linear count sweep
        named ``"LinearCountSweep"``.

        >>> setup = hfss.create_setup("LinearCountSetup")
        >>> linear_count_sweep = hfss.create_linear_count_sweep(setupname="LinearCountSetup",
        ...                                                     sweepname="LinearCountSweep",
        ...                                                     unit="MHz", freqstart=1.1e3,
        ...                                                     freqstop=1200.1, num_of_freq_points=1658)
        >>> type(linear_count_sweep)
        <class 'pyaedt.modules.SetupTemplates.SweepHFSS'>

        """
        if sweep_type not in ["Discrete", "Interpolating", "Fast"]:
            raise AttributeError(
                "Invalid value for `sweep_type`. The value must be 'Discrete', 'Interpolating', or 'Fast'."
            )

        if sweepname is None:
            sweepname = generate_unique_name("Sweep")

        if setupname not in self.setup_names:
            return False
        for s in self.setups:
            if s.name == setupname:
                setupdata = s
                if sweepname in [sweep.name for sweep in setupdata.sweeps]:
                    oldname = sweepname
                    sweepname = generate_unique_name(oldname)
                    self.logger.warning(
                        "Sweep %s is already present. Sweep has been renamed in %s.", oldname, sweepname
                    )
                sweepdata = setupdata.add_sweep(sweepname, sweep_type)
                if not sweepdata:
                    return False
                sweepdata.props["RangeType"] = "LinearCount"
                sweepdata.props["RangeStart"] = str(freqstart) + unit
                sweepdata.props["RangeEnd"] = str(freqstop) + unit
                sweepdata.props["RangeCount"] = num_of_freq_points
                sweepdata.props["Type"] = sweep_type
                if sweep_type == "Interpolating":
                    sweepdata.props["InterpTolerance"] = interpolation_tol
                    sweepdata.props["InterpMaxSolns"] = interpolation_max_solutions
                    sweepdata.props["InterpMinSolns"] = 0
                    sweepdata.props["InterpMinSubranges"] = 1
                sweepdata.props["SaveFields"] = save_fields
                sweepdata.props["SaveRadFields"] = save_rad_fields
                sweepdata.update()
                self.logger.info("Linear count sweep {} has been correctly created.".format(sweepname))
                return sweepdata
        return False

    @pyaedt_function_handler()
    def create_linear_step_sweep(
        self,
        setupname,
        unit,
        freqstart,
        freqstop,
        step_size,
        sweepname=None,
        save_fields=True,
        save_rad_fields=False,
        sweep_type="Discrete",
    ):
        """Create a sweep with a specified frequency step.

        Parameters
        ----------
        setupname : str
            Name of the setup.
        unit : str
            Unit of the frequency. For example, ``"MHz"`` or ``"GHz"``.
        freqstart : float
            Starting frequency of the sweep.
        freqstop : float
            Stopping frequency of the sweep.
        step_size : float
            Frequency size of the step.
        sweepname : str, optional
            Name of the sweep. The default is ``None``.
        save_fields : bool, optional
            Whether to save fields. The default is ``True``.
        save_rad_fields : bool, optional
            Whether to save radiating fields. The default is ``False``.
        sweep_type : str, optional
            Type of the sweep. Options are ``"Discrete"``,``"Interpolating"`` and
            ``"Fast"``. The default is ``"Discrete"``.

        Returns
        -------
        :class:`pyaedt.modules.SetupTemplates.SweepHFSS` or bool
            Sweep object if successful, ``False`` otherwise.

        References
        ----------

        >>> oModule.InsertFrequencySweep

        Examples
        --------

        Create a setup named ``"LinearStepSetup"`` and use it in a linear step sweep
        named ``"LinearStepSweep"``.

        >>> setup = hfss.create_setup("LinearStepSetup")
        >>> linear_step_sweep = hfss.create_linear_step_sweep(setupname="LinearStepSetup",
        ...                                                   sweepname="LinearStepSweep",
        ...                                                   unit="MHz", freqstart=1.1e3,
        ...                                                   freqstop=1200.1, step_size=153.8)
        >>> type(linear_step_sweep)
        <class 'pyaedt.modules.SetupTemplates.SweepHFSS'>

        """
        if sweep_type not in ["Discrete", "Interpolating", "Fast"]:
            raise AttributeError(
                "Invalid value for `sweep_type`. The value must be 'Discrete', 'Interpolating', or 'Fast'."
            )
        if sweepname is None:
            sweepname = generate_unique_name("Sweep")

        if setupname not in self.setup_names:
            return False
        for s in self.setups:
            if s.name == setupname:
                setupdata = s
                if sweepname in [sweep.name for sweep in setupdata.sweeps]:
                    oldname = sweepname
                    sweepname = generate_unique_name(oldname)
                    self.logger.warning(
                        "Sweep %s is already present. Sweep has been renamed in %s.", oldname, sweepname
                    )
                sweepdata = setupdata.add_sweep(sweepname, sweep_type)
                if not sweepdata:
                    return False
                sweepdata.props["RangeType"] = "LinearStep"
                sweepdata.props["RangeStart"] = str(freqstart) + unit
                sweepdata.props["RangeEnd"] = str(freqstop) + unit
                sweepdata.props["RangeStep"] = str(step_size) + unit
                sweepdata.props["SaveFields"] = save_fields
                sweepdata.props["SaveRadFields"] = save_rad_fields
                sweepdata.props["ExtrapToDC"] = False
                sweepdata.props["Type"] = sweep_type
                if sweep_type == "Interpolating":
                    sweepdata.props["InterpTolerance"] = 0.5
                    sweepdata.props["InterpMaxSolns"] = 250
                    sweepdata.props["InterpMinSolns"] = 0
                    sweepdata.props["InterpMinSubranges"] = 1
                sweepdata.update()
                self.logger.info("Linear step sweep {} has been correctly created.".format(sweepname))
                return sweepdata
        return False

    @pyaedt_function_handler()
    def create_single_point_sweep(
        self,
        setupname,
        unit,
        freq,
        sweepname=None,
        save_single_field=True,
        save_fields=False,
        save_rad_fields=False,
    ):
        """Create a sweep with a single frequency point.

        Parameters
        ----------
        setupname : str
            Name of the setup.
        unit : str
            Unit of the frequency. For example, ``"MHz"`` or ``"GHz"``.
        freq : float, list
            Frequency of the single point or list of frequencies to create distinct single points.
        sweepname : str, optional
            Name of the sweep. The default is ``None``.
        save_single_field : bool, list, optional
            Whether to save the fields of the single point. The default is ``True``.
            If a list is specified, the length must be the same as the list of frequencies.
        save_fields : bool, optional
            Whether to save fields for all points and subranges defined in the sweep.
            The default is ``False``.
        save_rad_fields : bool, optional
            Whether to save only radiating fields. The default is ``False``.

        Returns
        -------
        :class:`pyaedt.modules.SetupTemplates.SweepHFSS` or bool
            Sweep object if successful, ``False`` otherwise.

        References
        ----------

        >>> oModule.InsertFrequencySweep

        Examples
        --------

        Create a setup named ``"LinearStepSetup"`` and use it in a single point sweep
        named ``"SinglePointSweep"``.

        >>> setup = hfss.create_setup("LinearStepSetup")
        >>> single_point_sweep = hfss.create_single_point_sweep(setupname="LinearStepSetup",
        ...                                                   sweepname="SinglePointSweep",
        ...                                                   unit="MHz", freq=1.1e3)
        >>> type(single_point_sweep)
        <class 'pyaedt.modules.SetupTemplates.SweepHFSS'>

        """
        if sweepname is None:
            sweepname = generate_unique_name("SinglePoint")

        if isinstance(save_single_field, list):
            if not isinstance(freq, list) or len(save_single_field) != len(freq):
                raise AttributeError("The length of save_single_field must be the same as the frequency length.")

        add_subranges = False
        if isinstance(freq, list):
            if not freq:
                raise AttributeError("Frequency list is empty. Specify at least one frequency point.")
            freq0 = freq.pop(0)
            if freq:
                add_subranges = True
        else:
            freq0 = freq

        if isinstance(save_single_field, list):
            save0 = save_single_field.pop(0)
        else:
            save0 = save_single_field
            if add_subranges:
                save_single_field = [save0] * len(freq)

        if setupname not in self.setup_names:
            return False
        for s in self.setups:
            if s.name == setupname:
                setupdata = s
                if sweepname in [sweep.name for sweep in setupdata.sweeps]:
                    oldname = sweepname
                    sweepname = generate_unique_name(oldname)
                    self.logger.warning(
                        "Sweep %s is already present. Sweep has been renamed in %s.", oldname, sweepname
                    )
                sweepdata = setupdata.add_sweep(sweepname, "Discrete")
                sweepdata.props["RangeType"] = "SinglePoints"
                sweepdata.props["RangeStart"] = str(freq0) + unit
                sweepdata.props["RangeEnd"] = str(freq0) + unit
                sweepdata.props["SaveSingleField"] = save0
                sweepdata.props["SaveFields"] = save_fields
                sweepdata.props["SaveRadFields"] = save_rad_fields
                sweepdata.props["SMatrixOnlySolveMode"] = "Auto"
                if add_subranges:
                    for f, s in zip(freq, save_single_field):
                        sweepdata.add_subrange(rangetype="SinglePoints", start=f, unit=unit, save_single_fields=s)
                sweepdata.update()
                self.logger.info("Single point sweep {} has been correctly created".format(sweepname))
                return sweepdata
        return False

    @pyaedt_function_handler()
    def create_sbr_linked_antenna(
        self,
        source_object,
        target_cs="Global",
        solution=None,
        fieldtype="nearfield",
        use_composite_ports=False,
        use_global_current=True,
        current_conformance="Disable",
        thin_sources=True,
        power_fraction="0.95",
    ):
        """Create a linked antenna.

        Parameters
        ----------
        source_object : pyaedt.Hfss
            Source object.
        target_cs : str, optional
            Target coordinate system. The default is ``"Global"``.
        solution : optional
            The default is ``None``.
        fieldtype : str, optional
            The default is ``"nearfield"``.
        use_composite_ports : bool, optional
            Whether to use composite ports. The default is ``False``.
        use_global_current : bool, optional
            Whether to use the global current. The default is ``True``.
        current_conformance, str optional
            The default is ``"Disable"``.
        thin_sources : bool, optional
             The default is ``True``.
        power_fraction : str, optional
             The default is ``"0.95"``.

        References
        ----------

        >>> oEditor.InsertNativeComponent

        Examples
        --------
        >>> from pyaedt import Hfss
        >>> target_project = "my/path/to/targetProject.aedt"
        >>> source_project = "my/path/to/sourceProject.aedt"
        >>> target = Hfss(projectname=target_project, solution_type="SBR+",
        ...               specified_version="2021.2", new_desktop_session=False)  # doctest: +SKIP
        >>> source = Hfss(projectname=source_project, designname="feeder",
        ...               specified_version="2021.2", new_desktop_session=False)  # doctest: +SKIP
        >>> target.create_sbr_linked_antenna(source, target_cs="feederPosition",
        ...                                  fieldtype="farfield")  # doctest: +SKIP

        """
        if self.solution_type != "SBR+":
            self.logger.error("Native components only apply to the SBR+ solution.")
            return False
        compName = source_object.design_name
        uniquename = generate_unique_name(compName)
        if source_object.project_name == self.project_name:
            project_name = "This Project*"
        else:
            project_name = os.path.join(source_object.project_path, source_object.project_name + ".aedt")
        design_name = source_object.design_name
        if not solution:
            solution = source_object.nominal_adaptive
        params = OrderedDict({})
        pars = source_object.available_variations.nominal_w_values_dict
        for el in pars:
            params[el] = pars[el]
        native_props = OrderedDict(
            {
                "Type": "Linked Antenna",
                "Unit": self.modeler.model_units,
                "Is Parametric Array": False,
                "Project": project_name,
                "Product": "HFSS",
                "Design": design_name,
                "Soln": solution,
                "Params": params,
                "ForceSourceToSolve": True,
                "PreservePartnerSoln": True,
                "PathRelativeTo": "TargetProject",
                "FieldType": fieldtype,
                "UseCompositePort": use_composite_ports,
                "SourceBlockageStructure": OrderedDict({"NonModelObject": []}),
            }
        )
        if fieldtype == "nearfield":
            native_props["UseGlobalCurrentSrcOption"] = use_global_current
            native_props["Current Source Conformance"] = current_conformance
            native_props["Thin Sources"] = thin_sources
            native_props["Power Fraction"] = power_fraction
        return self._create_native_component(
            "Linked Antenna", target_cs, self.modeler.model_units, native_props, uniquename
        )

    @pyaedt_function_handler()
    def _create_native_component(
        self, antenna_type, target_cs=None, model_units=None, parameters_dict=None, antenna_name=None
    ):
        if antenna_name is None:
            antenna_name = generate_unique_name(antenna_type.replace(" ", "").replace("-", ""))
        if not model_units:
            model_units = self.modeler.model_units

        native_props = OrderedDict(
            {"NativeComponentDefinitionProvider": OrderedDict({"Type": antenna_type, "Unit": model_units})}
        )
        native_props["TargetCS"] = target_cs
        if isinstance(parameters_dict, dict):
            for el in parameters_dict:
                if (
                    el not in ["antenna_type", "offset", "rotation", "rotation_axis", "mode"]
                    and parameters_dict[el] is not None
                ):
                    native_props["NativeComponentDefinitionProvider"][el.replace("_", " ").title()] = parameters_dict[
                        el
                    ]
        native = NativeComponentObject(self, antenna_type, antenna_name, native_props)
        if native.create():
            user_defined_component = UserDefinedComponent(
                self.modeler, native.name, native_props["NativeComponentDefinitionProvider"], antenna_type
            )
            self.modeler.user_defined_components[native.name] = user_defined_component
            self._native_components.append(native)
            self.logger.info("Native component %s %s has been correctly created.", antenna_type, antenna_name)
            return native
        self.logger.error("Error in native component creation for %s %s.", antenna_type, antenna_name)

        return None

    class SbrAntennas:
        (
            ConicalHorn,
            CrossDipole,
            HalfWaveDipole,
            HorizontalDipole,
            ParametricBeam,
            ParametricSlot,
            PyramidalHorn,
            QuarterWaveMonopole,
            ShortDipole,
            SmallLoop,
            WireDipole,
            WireMonopole,
        ) = (
            "Conical Horn",
            "Cross Dipole",
            "Half-Wave Dipole",
            "Horizontal Dipole",
            "Parametric Beam",
            "Parametric Slot",
            "Pyramidal Horn",
            "Quarter-Wave Monopole",
            "Short Dipole",
            "Small Loop",
            "Wire Dipole",
            "Wire Monopole",
        )

    class SBRAntennaDefaults:
        _conical = OrderedDict(
            {
                "Is Parametric Array": False,
                "MatchedPortImpedance": "50ohm",
                "Polarization": "Vertical",
                "Representation": "Far Field",
                "Mouth Diameter": "0.3meter",
                "Flare Half Angle": "20deg",
            }
        )
        _cross = OrderedDict(
            {
                "Is Parametric Array": False,
                "MatchedPortImpedance": "50ohm",
                "Polarization": "RHCP",
                "Representation": "Current Source",
                "Density": "1",
                "UseGlobalCurrentSrcOption": True,
                "Resonant Frequency": "0.3GHz",
                "Wire Length": "499.654096666667mm",
                "Mode": 0,
            }
        )
        _horizontal = OrderedDict(
            {
                "Is Parametric Array": False,
                "MatchedPortImpedance": "50ohm",
                "Polarization": "Vertical",
                "Representation": "Current Source",
                "Density": "1",
                "UseGlobalCurrentSrcOption": False,
                "Resonant Frequency": "0.3GHz",
                "Wire Length": "499.654096666667mm",
                "Height Over Ground Plane": "249.827048333333mm",
                "Use Default Height": True,
            }
        )
        _parametricbeam = OrderedDict(
            {
                "Is Parametric Array": False,
                "Size": "0.1meter",
                "MatchedPortImpedance": "50ohm",
                "Polarization": "Vertical",
                "Representation": "Far Field",
                "Vertical BeamWidth": "30deg",
                "Horizontal BeamWidth": "60deg",
            }
        )
        _slot = OrderedDict(
            {
                "Is Parametric Array": False,
                "MatchedPortImpedance": "50ohm",
                "Representation": "Far Field",
                "Resonant Frequency": "0.3GHz",
                "Slot Length": "499.654096666667mm",
            }
        )
        _horn = OrderedDict(
            {
                "Is Parametric Array": False,
                "MatchedPortImpedance": "50ohm",
                "Representation": "Far Field",
                "Mouth Width": "0.3meter",
                "Mouth Height": "0.5meter",
                "Waveguide Width": "0.15meter",
                "Width Flare Half Angle": "20deg",
                "Height Flare Half Angle": "35deg",
            }
        )
        _dipole = OrderedDict(
            {
                "Is Parametric Array": False,
                "Size": "1mm",
                "MatchedPortImpedance": "50ohm",
                "Representation": "Far Field",
            }
        )
        _smallloop = OrderedDict(
            {
                "Is Parametric Array": False,
                "MatchedPortImpedance": "50ohm",
                "Polarization": "Vertical",
                "Representation": "Current Source",
                "Density": "1",
                "UseGlobalCurrentSrcOption": False,
                "Current Source Conformance": "Disable",
                "Thin Sources": True,
                "Power Fraction": "0.95",
                "Mouth Diameter": "0.3meter",
                "Flare Half Angle": "20deg",
            }
        )
        _wiredipole = OrderedDict(
            {
                "Is Parametric Array": False,
                "MatchedPortImpedance": "50ohm",
                "Representation": "Far Field",
                "Resonant Frequency": "0.3GHz",
                "Wire Length": "499.654096666667mm",
            }
        )
        parameters = {
            "Conical Horn": _conical,
            "Cross Dipole": _cross,
            "Half-Wave Dipole": _dipole,
            "Horizontal Dipole": _horizontal,
            "Parametric Beam": _parametricbeam,
            "Parametric Slot": _slot,
            "Pyramidal Horn": _horn,
            "Quarter-Wave Monopole": _dipole,
            "Short Dipole": _dipole,
            "Small Loop": _dipole,
            "Wire Dipole": _wiredipole,
            "Wire Monopole": _wiredipole,
        }
        default_type_id = {
            "Conical Horn": 11,
            "Cross Dipole": 12,
            "Half-Wave Dipole": 3,
            "Horizontal Dipole": 13,
            "Parametric Beam": 0,
            "Parametric Slot": 7,
            "Pyramidal Horn": _horn,
            "Quarter-Wave Monopole": 4,
            "Short Dipole": 1,
            "Small Loop": 2,
            "Wire Dipole": 5,
            "Wire Monopole": 6,
            "File Based Antenna": 8,
        }

    @pyaedt_function_handler()
    def create_sbr_antenna(
        self,
        antenna_type=SbrAntennas.ConicalHorn,
        target_cs=None,
        model_units=None,
        parameters_dict=None,
        use_current_source_representation=False,
        is_array=False,
        antenna_name=None,
    ):
        """Create a parametric beam antenna in SBR+.

        Parameters
        ----------
        antenna_type : str, `SbrAntennas.ConicalHorn`
            Name of the antenna type. The enumerator ``SbrAntennas`` can also be used.
            The default is ``"SbrAntennas.Conical Horn"``.
        target_cs : str, optional
            Target coordinate system. The default is ``None``, in which case
            the active coodiante system is used.
        model_units : str, optional
            Model units to apply to the object. The default is
            ``None``, in which case the active modeler units are applied.
        parameters_dict : dict, optional
            Dictionary of parameters. The default is ``None``.
        use_current_source_representation : bool, optional
            Whether to use the current source representation. The default is ``False``.
        is_array : bool, optional
            The default is ``False``.
        antenna_name : str, optional
            Name of the 3D component. The default is ``None``, in which case the
            name is auto-generated based on the antenna type.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.NativeComponentObject`
            NativeComponentObject object.

        References
        ----------

        >>> oEditor.InsertNativeComponent

        Examples
        --------
        >>> from pyaedt import Hfss
        >>> hfss = Hfss(solution_type="SBR+")  # doctest: +SKIP
        pyaedt INFO: Added design 'HFSS_IPO' of type HFSS.
        >>> parm = {"polarization": "Vertical"}  # doctest: +SKIP
        >>> par_beam = hfss.create_sbr_antenna(hfss.SbrAntennas.ShortDipole,
        ...                                    parameters_dict=parm,
        ...                                    antenna_name="TX1")  # doctest: +SKIP

        """
        if self.solution_type != "SBR+":
            self.logger.error("This native component only applies to a SBR+ solution.")
            return False
        if target_cs is None:
            target_cs = self.modeler.oeditor.GetActiveCoordinateSystem()
        parameters_defaults = self.SBRAntennaDefaults.parameters[antenna_type].copy()
        if use_current_source_representation and antenna_type in [
            "Conical Horn",
            "Horizontal Dipole",
            "Parametric Slot",
            "Pyramidal Horn",
            "Wire Dipole",
            "Wire Monopole",
        ]:
            parameters_defaults["Representation"] = "Current Source"
            parameters_defaults["Density"] = "1"
            parameters_defaults["UseGlobalCurrentSrcOption"] = False
            parameters_defaults["Current Source Conformance"] = "Disable"
            parameters_defaults["Thin Sources"] = False
            parameters_defaults["Power Fraction"] = "0.95"
        if is_array:
            parameters_defaults["Is Parametric Array"] = True
            parameters_defaults["Array Element Type"] = self.SBRAntennaDefaults.default_type_id[antenna_type]
            parameters_defaults["Array Element Angle Phi"] = ("0deg",)
            parameters_defaults["Array Element Angle Theta"] = ("0deg",)
            parameters_defaults["Array Element Offset X"] = "0meter"
            parameters_defaults["Array Element Offset Y"] = "0meter"
            parameters_defaults["Array Element Offset Z"] = "0meter"
            parameters_defaults["Array Element Conformance Type"] = 0
            parameters_defaults["Array Element Conformance Type"] = 0
            parameters_defaults["Array Element Conformance Type"] = 0
            parameters_defaults["Array Element Conform Orientation"] = False
            parameters_defaults["Array Design Frequency"] = "1GHz"
            parameters_defaults["Array Layout Type"] = 1
            parameters_defaults["Array Specify Design In Wavelength"] = True
            parameters_defaults["Array Element Num"] = 5
            parameters_defaults["Array Length"] = "1meter"
            parameters_defaults["Array Width"] = "1meter"
            parameters_defaults["Array Length Spacing"] = "0.1meter"
            parameters_defaults["Array Width Spacing"] = "0.1meter"
            parameters_defaults["Array Length In Wavelength"] = "3"
            parameters_defaults["Array Width In Wavelength"] = "4"
            parameters_defaults["Array Length Spacing In Wavelength"] = "0.5"
            parameters_defaults["Array Stagger Type"] = 0
            parameters_defaults["Array Stagger Angle"] = "0deg"
            parameters_defaults["Array Symmetry Type"] = 0
            parameters_defaults["Array Weight Type"] = 3
            parameters_defaults["Array Beam Angle Theta"] = "0deg"
            parameters_defaults["Array Weight Edge TaperX"] = -200
            parameters_defaults["Array Weight Edge TaperY"] = -200
            parameters_defaults["Array Weight Cosine Exp"] = 1
            parameters_defaults["Array Differential Pattern Type"] = 0
            if is_array:
                antenna_name = generate_unique_name("pAntArray")
        if parameters_dict:
            for el, value in parameters_dict.items():
                parameters_defaults[el] = value
        return self._create_native_component(antenna_type, target_cs, model_units, parameters_defaults, antenna_name)

    @pyaedt_function_handler()
    def create_sbr_file_based_antenna(
        self,
        ffd_full_path,
        antenna_size="1mm",
        antenna_impedance="50ohm",
        representation_type="Far Field",
        target_cs=None,
        model_units=None,
        antenna_name=None,
    ):
        """Create a linked antenna.

        Parameters
        ----------
        ffd_full_path : str
            Full path to the FFD file.
        antenna_size : str, optional
            Antenna size with units. The default is ``"1mm"``.
        antenna_impedance : str, optional
            Antenna impedance with units. The default is ``"50ohm"``.
        representation_type : str, optional
            Type of the antenna. Options are ``"Far Field"`` and ``"Near Field"``.
            The default is ``"Far Field"``.
        target_cs : str, optional
            Target coordinate system. The default is ``None``, in which case the
            active coordinate system is used.
        model_units : str, optional
            Model units to apply to the object. The default is
            ``None``, in which case the active modeler units are applied.
        antenna_name : str, optional
            Name of the 3D component. The default is ``None``, in which case
            the name is auto-generated based on the antenna type.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.NativeComponentObject`

        References
        ----------

        >>> oEditor.InsertNativeComponent

        Examples
        --------
        >>> from pyaedt import Hfss
        >>> hfss = Hfss(solution_type="SBR+")  # doctest: +SKIP
        >>> ffd_file = "full_path/to/ffdfile.ffd"
        >>> par_beam = hfss.create_sbr_file_based_antenna(ffd_file)  # doctest: +SKIP

        """
        if self.solution_type != "SBR+":
            self.logger.error("This native component only applies to a SBR+ solution.")
            return False
        if target_cs is None:
            target_cs = self.modeler.oeditor.GetActiveCoordinateSystem()

        par_dicts = OrderedDict(
            {
                "Size": antenna_size,
                "MatchedPortImpedance": antenna_impedance,
                "Representation": representation_type,
                "ExternalFile": ffd_full_path,
            }
        )
        if not antenna_name:
            antenna_name = generate_unique_name(os.path.basename(ffd_full_path).split(".")[0])

        return self._create_native_component("File Based Antenna", target_cs, model_units, par_dicts, antenna_name)

    @pyaedt_function_handler()
    def set_sbr_txrx_settings(self, txrx_settings):
        """Set SBR+ TX RX antenna settings.

        Parameters
        ----------
        txrx_settings : dict
            Dictionary containing the TX as key and RX as values.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        References
        ----------

        >>> oModule.SetSBRTxRxSettings
        """
        if self.solution_type != "SBR+":
            self.logger.error("This boundary only applies to a SBR+ solution.")
            return False
        id = 0
        props = OrderedDict({})
        for el, val in txrx_settings.items():
            props["Tx/Rx List " + str(id)] = OrderedDict({"Tx Antenna": el, "Rx Antennas": txrx_settings[el]})
            id += 1
        return self._create_boundary("SBRTxRxSettings", props, "SBRTxRxSettings")

    @pyaedt_function_handler()
    def create_circuit_port_between_objects(
        self, startobj, endobject, axisdir=0, impedance=50, portname=None, renorm=True, renorm_impedance=50, deemb=False
    ):
        """Create a circuit port taking the closest edges of two objects.

        Parameters
        ----------
        startobj :
            Starting object for the integration line.
        endobject :
            Ending object for the integration line.
        axisdir : int or :class:`pyaedt.application.Analysis.Analysis.AxisDir`, optional
            Position of the port. It should be one of the values for ``Application.AxisDir``,
            which are: ``XNeg``, ``YNeg``, ``ZNeg``, ``XPos``, ``YPos``, and ``ZPos``.
            The default is ``Application.AxisDir.XNeg``.
        impedance : float, optional
            Port impedance. The default is ``50``.
        portname : str, optional
            Name of the port. The default is ``None``.
        renorm : bool, optional
            Whether to renormalize the mode. The default is ``True``.
        renorm_impedance : float or str, optional
            Renormalize impedance. The default is ``50``.
        deemb : bool, optional
            Whether to deembed the port. The default is ``False``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        References
        ----------

        >>> oModule.AssignCircuitPort

        Examples
        --------

        Create two boxes for creating a circuit port named ``'CircuitExample'``.

        >>> box1 = hfss.modeler.create_box([0, 0, 80], [10, 10, 5],
        ...                                "BoxCircuit1", "copper")
        >>> box2 = hfss.modeler.create_box([0, 0, 100], [10, 10, 5],
        ...                                "BoxCircuit2", "copper")
        >>> hfss.create_circuit_port_between_objects("BoxCircuit1", "BoxCircuit2",
        ...                                          hfss.AxisDir.XNeg, 50,
        ...                                          "CircuitExample", True, 50, False)
        'CircuitExample'

        """

        if not self.modeler.does_object_exists(startobj) or not self.modeler.does_object_exists(endobject):
            self.logger.error("One or both objects do not exist. Check and retry.")
            return False
        if self.solution_type in ["Modal", "Terminal", "Transient Network"]:
            out, parallel = self.modeler.find_closest_edges(startobj, endobject, axisdir)
            port_edges = []
            portname = self._get_unique_source_name(portname, "Port")

            return self._create_circuit_port(out, impedance, portname, renorm, deemb, renorm_impedance=renorm_impedance)
        return False  # pragma: no cover

    @pyaedt_function_handler()
    def create_lumped_port_between_objects(
        self, startobj, endobject, axisdir=0, impedance=50, portname=None, renorm=True, deemb=False, port_on_plane=True
    ):
        """Create a lumped port taking the closest edges of two objects.

        Parameters
        ----------
        startobj :
            Starting object for the integration line.
        endobject :
            Ending object for the integration line.
        axisdir : int or :class:`pyaedt.application.Analysis.Analysis.AxisDir`, optional
            Position of the port. It should be one of the values for ``Application.AxisDir``,
            which are: ``XNeg``, ``YNeg``, ``ZNeg``, ``XPos``, ``YPos``, and ``ZPos``.
            The default is ``Application.AxisDir.XNeg``.
        impedance : float, optional
            Port impedance. The default is ``50``.
        portname : str, optional
            Name of the port. The default is ``None``.
        renorm : bool, optional
            Whether to renormalize the mode. The default is ``True``.
        deemb : bool, optional
            Whether to deembed the port. The default is ``False``.
        port_on_plane : bool, optional
            Whether to create the source on the plane orthogonal to ``AxisDir``.
            The default is ``True``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        References
        ----------

        >>> oModule.AssignLumpedPort

        Examples
        --------

        Create two boxes that will be used to create a lumped port
        named ``'LumpedPort'``.

        >>> box1 = hfss.modeler.create_box([0, 0, 50], [10, 10, 5],
        ...                                "BoxLumped1","copper")
        >>> box2 = hfss.modeler.create_box([0, 0, 60], [10, 10, 5],
        ...                                "BoxLumped2", "copper")
        >>> hfss.create_lumped_port_between_objects("BoxLumped1", "BoxLumped2",
        ...                                         hfss.AxisDir.XNeg, 50,
        ...                                         "LumpedPort", True, False)
        pyaedt INFO: Connection Correctly created
        'LumpedPort'

        """
        startobj = self.modeler.convert_to_selections(startobj)
        endobject = self.modeler.convert_to_selections(endobject)
        if not self.modeler.does_object_exists(startobj) or not self.modeler.does_object_exists(endobject):
            self.logger.error("One or both objects do not exist. Check and retry.")
            return False

        if self.solution_type in ["Modal", "Terminal", "Transient Network"]:
            sheet_name, point0, point1 = self.modeler._create_sheet_from_object_closest_edge(
                startobj, endobject, axisdir, port_on_plane
            )

            portname = self._get_unique_source_name(portname, "Port")

            if "Modal" in self.solution_type:
                return self._create_lumped_driven(sheet_name, point0, point1, impedance, portname, renorm, deemb)
            else:
                faces = self.modeler.get_object_faces(sheet_name)
                if deemb:
                    deembed = 0
                else:
                    deembed = None
                return self._create_port_terminal(
                    faces[0],
                    endobject,
                    portname,
                    renorm=renorm,
                    deembed=deembed,
                    iswaveport=False,
                    impedance=impedance,
                )
        return False  # pragma: no cover

    @pyaedt_function_handler()
    def create_spiral_lumped_port(self, start_object, end_object, port_width=None):
        """Create a spiral lumped port between two adjacent objects.

        The two objects must have two adjacent, parallel, and identical faces.
        The faces must be a polygon (not a circle).

        Parameters
        ----------
        start_object : str or int or :class:`pyaedt.modeler.object3d.Object3d`
        end_object : str or int or :class:`pyaedt.modeler.object3d.Object3d`

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        """
        # fmt: off
        if not "Terminal" in self.solution_type:
            raise Exception("This method can be used only in Terminal solutions.")
        start_object = self.modeler.convert_to_selections(start_object)
        end_object = self.modeler.convert_to_selections(end_object)
        closest_distance = 1e9
        closest_faces = []
        for face1 in self.modeler[start_object].faces:
            for face2 in self.modeler[end_object].faces:
                facecenter_distance = GeometryOperators.points_distance(face1.center, face2.center)
                if facecenter_distance <= closest_distance:
                    closest_distance = facecenter_distance
                    closest_faces = [face1, face2]

        if not GeometryOperators.is_collinear(closest_faces[0].normal, closest_faces[1].normal):
            raise AttributeError('The two objects must have parallel adjacent faces.')
        if GeometryOperators.is_collinear(closest_faces[0].normal, [1, 0, 0]):
            plane = 0
        elif GeometryOperators.is_collinear(closest_faces[0].normal, [0, 1, 0]):
            plane = 1
        elif GeometryOperators.is_collinear(closest_faces[0].normal, [0, 0, 1]):
            plane = 2
        else:
            raise AttributeError('The two object must have the adjacent faces aligned with the main planes.')

        move_vector = GeometryOperators.v_sub(closest_faces[1].center, closest_faces[0].center)
        move_vector = GeometryOperators.v_prod(0.5, move_vector)

        if port_width:
            spiral_width = port_width
            filling = 1.5
        else:
            # get face bounding box
            face_bb = [1e15, 1e15, 1e15, -1e15, -1e15, -1e15]
            for i in range(3):
                for v in closest_faces[0].vertices:
                    face_bb[i] = min(face_bb[i], v.position[i])
                    face_bb[i+3] = max(face_bb[i+3], v.position[i])
            # get the ratio in 2D
            bb_dim = [abs(face_bb[i]-face_bb[i+3]) for i in range(3) if abs(face_bb[i]-face_bb[i+3]) > 1e-12]
            bb_ratio = max(bb_dim)/min(bb_dim)
            if bb_ratio > 2:
                spiral_width = min(bb_dim) / 12
                filling = -0.2828*bb_ratio**2 + 3.4141*bb_ratio - 4.197
                print(filling)
            else:
                vertex_coordinates = []
                for v in closest_faces[0].vertices:
                    vertex_coordinates.append(v.position)
                segments_lengths = []
                for vc in vertex_coordinates:
                    segments_lengths.append(GeometryOperators.points_distance(vc, closest_faces[0].center))
                spiral_width = min(segments_lengths) / 15
                filling = 1.5

        name = generate_unique_name("P", n=3)

        poly = self.modeler.create_spiral_on_face(closest_faces[0], spiral_width, filling_factor=filling)
        poly.name = name
        poly.translate(move_vector)

        vert_position_x = []
        vert_position_y = []
        for vert in poly.vertices:
            if plane == 0:
                vert_position_x.append(vert.position[1])
                vert_position_y.append(vert.position[2])
            elif plane == 1:
                vert_position_x.append(vert.position[0])
                vert_position_y.append(vert.position[2])
            elif plane == 2:
                vert_position_x.append(vert.position[0])
                vert_position_y.append(vert.position[1])

        x, y = GeometryOperators.orient_polygon(vert_position_x, vert_position_y)

        list_a_val = False
        x1 = []
        y1 = []
        x2 = []
        y2 = []
        for i in range(len(x) - 1):
            dist = GeometryOperators.points_distance([x[i], y[i], 0], [x[i + 1], y[i + 1], 0])
            if list_a_val:
                x1.append(x[i])
                y1.append(y[i])
            else:
                x2.append(x[i])
                y2.append(y[i])
            if abs(dist - spiral_width) < 1e-6:
                list_a_val = not list_a_val
        # set the last point
        if list_a_val:
            x1.append(x[-1])
            y1.append(y[-1])
        else:
            x2.append(x[-1])
            y2.append(y[-1])

        faces_mid_point = GeometryOperators.get_mid_point(closest_faces[1].center, closest_faces[0].center)

        x1, y1 = GeometryOperators.orient_polygon(x1, y1)
        coords = []
        for x, y in zip(x1, y1):
            if plane == 0:
                coords.append([faces_mid_point[0] - closest_distance/4, x, y])
            elif plane == 1:
                coords.append([x, faces_mid_point[1] - closest_distance/4, y])
            elif plane == 2:
                coords.append([x, y, faces_mid_point[2] - closest_distance/4])
        dx = abs(coords[0][0] - coords[1][0])
        dy = abs(coords[0][1] - coords[1][1])
        dz = abs(coords[0][2] - coords[1][2])
        v1 = GeometryOperators.v_points(coords[0], coords[1])
        v2 = GeometryOperators.v_points(coords[0], coords[2])
        norm = GeometryOperators.v_cross(v1, v2)

        if abs(norm[0]) > 1e-12:
            if dy < dz:
                orient = "Y"
            else:
                orient = "Z"
        elif abs(norm[1]) > 1e-12:
            if dx < dz:
                orient = "X"
            else:
                orient = "Z"
        else:
            if dx < dy:
                orient = "X"
            else:
                orient = "Y"
        poly1 = self.modeler.create_polyline(
            coords,
            xsection_type="Line",
            xsection_orient=orient,
            xsection_width=closest_distance / 2,
            name=start_object + "_sheet",
        )
        self.assign_perfecte_to_sheets(poly1, sourcename=start_object)

        x2, y2 = GeometryOperators.orient_polygon(x2, y2)
        coords = []
        faces_mid_point = GeometryOperators.get_mid_point(closest_faces[1].center, closest_faces[0].center)
        for x, y in zip(x2, y2):
            if plane == 0:
                coords.append([faces_mid_point[0] + closest_distance/4, x, y])
            elif plane == 1:
                coords.append([x, faces_mid_point[1] + closest_distance/4, y])
            elif plane == 2:
                coords.append([x, y, faces_mid_point[2] + closest_distance/4])
        dx = abs(coords[0][0] - coords[1][0])
        dy = abs(coords[0][1] - coords[1][1])
        dz = abs(coords[0][2] - coords[1][2])
        v1 = GeometryOperators.v_points(coords[0], coords[1])
        v2 = GeometryOperators.v_points(coords[0], coords[2])
        norm = GeometryOperators.v_cross(v1, v2)
        if abs(norm[0]) > 1e-12:
            if dy < dz:
                orient = "Y"
            else:
                orient = "Z"
        elif abs(norm[1]) > 1e-12:
            if dx < dz:
                orient = "X"
            else:
                orient = "Z"
        else:
            if dx < dy:
                orient = "X"
            else:
                orient = "Y"
        poly2 = self.modeler.create_polyline(
            coords,
            xsection_type="Line",
            xsection_orient=orient,
            xsection_width=closest_distance / 2,
            name=end_object + "_sheet",
        )

        self.assign_perfecte_to_sheets(poly2, sourcename=end_object)
        port = self.create_lumped_port_to_sheet(poly, reference_object_list=[poly2.name], portname=name)
        # fmt: on
        return port

    @pyaedt_function_handler()
    def create_voltage_source_from_objects(self, startobj, endobject, axisdir=0, sourcename=None, source_on_plane=True):
        """Create a voltage source taking the closest edges of two objects.

        Parameters
        ----------
        startobj :
            Starting object for the integration line.
        endobject :
            Ending object for the integration line.
        axisdir : int or :class:`pyaedt.application.Analysis.Analysis.AxisDir`, optional
            Position of the port. It should be one of the values for
            ``Application.AxisDir``, which are: ``XNeg``, ``YNeg``,
            ``ZNeg``, ``XPos``, ``YPos``, and ``ZPos``.  The default
            is ``Application.AxisDir.XNeg``.
        sourcename : str, optional
            Name of the source. The default is ``None``.
        source_on_plane : bool, optional
            Whether to create the source on the plane orthogonal to
            ``AxisDir``. The default is ``True``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        References
        ----------

        >>> oModule.AssignVoltage

        Examples
        --------

        Create two boxes for creating a voltage source named ``'VoltageSource'``.

        >>> box1 = hfss.modeler.create_box([30, 0, 0], [40, 10, 5],
        ...                                "BoxVolt1", "copper")
        >>> box2 = hfss.modeler.create_box([30, 0, 10], [40, 10, 5],
        ...                                "BoxVolt2", "copper")
        >>> v1 = hfss.create_voltage_source_from_objects("BoxVolt1", "BoxVolt2",
        ...                                         hfss.AxisDir.XNeg,
        ...                                         "VoltageSource")
        pyaedt INFO: Connection Correctly created

        """

        if not self.modeler.does_object_exists(startobj) or not self.modeler.does_object_exists(endobject):
            self.logger.error("One or both objects doesn't exists. Check and retry")
            return False
        if self.solution_type in ["Modal", "Terminal", "Transient Network"]:
            sheet_name, point0, point1 = self.modeler._create_sheet_from_object_closest_edge(
                startobj, endobject, axisdir, source_on_plane
            )
            sourcename = self._get_unique_source_name(sourcename, "Voltage")
            return self.create_source_excitation(sheet_name, point0, point1, sourcename, sourcetype="Voltage")
        return False  # pragma: no cover

    @pyaedt_function_handler()
    def create_current_source_from_objects(self, startobj, endobject, axisdir=0, sourcename=None, source_on_plane=True):
        """Create a current source taking the closest edges of two objects.

        Parameters
        ----------
        startobj :
            Starting object for the integration line.
        endobject :
            Ending object for the integration line.
        axisdir : int or :class:`pyaedt.application.Analysis.Analysis.AxisDir`, optional
            Position of the port. It should be one of the values for ``Application.AxisDir``,
            which are: ``XNeg``, ``YNeg``, ``ZNeg``, ``XPos``, ``YPos``, and ``ZPos``.
            The default is ``Application.AxisDir.XNeg``.
        sourcename : str, optional
            Name of the source. The default is ``None``.
        source_on_plane : bool, optional
            Whether to create the source on the plane orthogonal to ``axisdir``. The default is ``True``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        References
        ----------

        >>> oModule.AssignCurrent

        Examples
        --------

        Create two boxes for creating a current source named ``'CurrentSource'``.

        >>> box1 = hfss.modeler.create_box([30, 0, 20], [40, 10, 5],
        ...                                "BoxCurrent1", "copper")
        >>> box2 = hfss.modeler.create_box([30, 0, 30], [40, 10, 5],
        ...                                "BoxCurrent2", "copper")
        >>> i1 = hfss.create_current_source_from_objects("BoxCurrent1", "BoxCurrent2",
        ...                                         hfss.AxisDir.XPos,
        ...                                         "CurrentSource")
        pyaedt INFO: Connection created 'CurrentSource' correctly.

        """

        if not self.modeler.does_object_exists(startobj) or not self.modeler.does_object_exists(endobject):
            self.logger.error("One or both objects do not exist. Check and retry.")
            return False
        if self.solution_type in ["Modal", "Terminal", "Transient Network"]:
            sheet_name, point0, point1 = self.modeler._create_sheet_from_object_closest_edge(
                startobj, endobject, axisdir, source_on_plane
            )
            sourcename = self._get_unique_source_name(sourcename, "Current")
            return self.create_source_excitation(sheet_name, point0, point1, sourcename, sourcetype="Current")
        return False  # pragma: no cover

    @pyaedt_function_handler()
    def create_source_excitation(self, sheet_name, point1, point2, sourcename, sourcetype="Voltage"):
        """Create a source excitation.

        Parameters
        ----------
        sheet_name : str
            Name of the sheet.
        point1 :

        point2 :

        sourcename : str
            Name of the source.

        sourcetype : str, optional
            Type of the source. The default is ``"Voltage"``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        References
        ----------

        >>> oModule.AssignVoltage
        >>> oModule.AssignCurrent
        """

        props = OrderedDict({"Objects": [sheet_name], "Direction": OrderedDict({"Start": point1, "End": point2})})
        return self._create_boundary(sourcename, props, sourcetype)

    @pyaedt_function_handler()
    def create_wave_port_between_objects(
        self,
        startobj,
        endobject,
        axisdir=0,
        impedance=50,
        nummodes=1,
        portname=None,
        renorm=True,
        deembed_dist=0,
        port_on_plane=True,
        add_pec_cap=False,
    ):
        """Create a waveport taking the closest edges of two objects.

        Parameters
        ----------
        startobj :
            Starting object for the integration line.
        endobject :
            Ending object for the integration line.
        axisdir : int or :class:`pyaedt.application.Analysis.Analysis.AxisDir`, optional
            Position of the port. It should be one of the values for ``Application.AxisDir``,
            which are: ``XNeg``, ``YNeg``, ``ZNeg``, ``XPos``, ``YPos``, and ``ZPos``.
            The default is ``Application.AxisDir.XNeg``.
        impedance : float, optional
            Port impedance. The default is ``50``.
        nummodes : int, optional
            Number of modes. The default is ``1``.
        portname : str, optional
            Name of the port. The default is ``None``.
        renorm : bool, optional
            Whether to renormalize the mode. The default is ``True``.
        deembed_dist : float, optional
            Deembed distance in millimeters. The default is ``0``,
            in which case deembed is disabled.
        port_on_plane : bool, optional
            Whether to create the port on the plane orthogonal to ``AxisDir``. The default is ``True``.
        add_pec_cap : bool, optional
             The default is ``False``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        References
        ----------

        >>> oModule.AssignWavePort

        Examples
        --------

        Create two boxes that will be used to create a wave port
        named ``'Wave Port'``.

        >>> box1 = hfss.modeler.create_box([0,0,0], [10,10,5],
        ...                                           "BoxWave1", "copper")
        >>> box2 = hfss.modeler.create_box([0, 0, 10], [10, 10, 5],
        ...                                           "BoxWave2", "copper")
        >>> wave_port = hfss.create_wave_port_between_objects("BoxWave1", "BoxWave2",
        ...                                                   hfss.AxisDir.XNeg, 50, 1,
        ...                                                   "Wave Port", False)
        pyaedt INFO: Connection Correctly created

        """

        if not self.modeler.does_object_exists(startobj) or not self.modeler.does_object_exists(endobject):
            self.logger.error("One or both objects do not exist. Check and retry.")
            return False
        if self.solution_type in ["Modal", "Terminal", "Transient Network"]:
            sheet_name, point0, point1 = self.modeler._create_sheet_from_object_closest_edge(
                startobj, endobject, axisdir, port_on_plane
            )
            if add_pec_cap:
                dist = math.sqrt(self.modeler[sheet_name].faces[0].area)
                self._create_pec_cap(sheet_name, startobj, dist / 10)
            portname = self._get_unique_source_name(portname, "Port")

            if "Modal" in self.solution_type:
                return self._create_waveport_driven(
                    sheet_name, point0, point1, impedance, portname, renorm, nummodes, deembed_dist
                )
            else:
                faces = self.modeler.get_object_faces(sheet_name)
                if deembed_dist == 0:
                    deembed = None
                else:
                    deembed = deembed_dist
                return self._create_port_terminal(
                    faces[0],
                    endobject,
                    portname,
                    renorm=renorm,
                    deembed=deembed,
                    iswaveport=True,
                    impedance=impedance,
                )
        return False  # pragma: no cover

    @pyaedt_function_handler()
    def create_floquet_port(
        self,
        face,
        lattice_origin=None,
        lattice_a_end=None,
        lattice_b_end=None,
        nummodes=2,
        portname=None,
        renorm=True,
        deembed_dist=0,
        reporter_filter=True,
        lattice_cs="Global",
    ):
        """Create a floquet port on a face.

        Parameters
        ----------
        face :
            Face or sheet to apply the floquet port to.
        lattice_origin : list
            List of ``[x,y,z]`` coordinates for the lattice A-B origin. The default is ``None``,
            in which case the method tries to compute the A-B automatically.
        lattice_a_end : list
            List of ``[x,y,z]`` coordinates for the lattice A end point. The default is ``None``,
            in which case the method tries to compute the A-B automatically.
        lattice_b_end : list
            List of ``[x,y,z]`` coordinates for the lattice B end point. The default is ``None``,
            in which case the method tries to compute the A-B automatically.
        nummodes : int, optional
            Number of modes. The default is ``2``.
        portname : str, optional
            Name of the port. The default is ``None``.
        renorm : bool, optional
            Whether to renormalize the mode. The default is ``True``.
        deembed_dist : float, str, optional
            Deembed distance in millimeters. The default is ``0``,
            in which case deembed is disabled.
        reporter_filter : bool, list of bool
            Whether to include modes in the report. The default is ``True``. If a single
            Boolean value is specified, it applies to all modes. If a list of Boolean values is specified, it applies
            to each mode in the list. A list must have ``nummodes`` elements.
        lattice_cs : str, optional
            Coordinate system for the lattice A-B vector reference. The default is ``Global``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.


        References
        ----------

        >>> oModule.AssignFloquetPort
        """
        face_id = self.modeler.convert_to_selections(face, True)
        props = OrderedDict({})
        if isinstance(face_id[0], int):
            props["Faces"] = face_id
        else:
            props["Objects"] = face_id

        props["NumModes"] = nummodes
        if deembed_dist:
            props["DoDeembed"] = True
            props["DeembedDist"] = self.modeler._arg_with_dim(deembed_dist)
        else:
            props["DoDeembed"] = False
            props["DeembedDist"] = "0mm"
        props["RenormalizeAllTerminals"] = renorm
        props["Modes"] = OrderedDict({})
        for i in range(1, 1 + nummodes):
            props["Modes"]["Mode{}".format(i)] = OrderedDict({})
            props["Modes"]["Mode{}".format(i)]["ModeNum"] = i
            props["Modes"]["Mode{}".format(i)]["UseIntLine"] = False
            props["Modes"]["Mode{}".format(i)]["CharImp"] = "Zpi"
        props["ShowReporterFilter"] = True
        if isinstance(reporter_filter, bool):
            props["ReporterFilter"] = [reporter_filter for i in range(nummodes)]
        else:
            props["ReporterFilter"] = reporter_filter
        if not lattice_a_end or not lattice_origin or not lattice_b_end:
            result, output = self.modeler._find_perpendicular_points(face_id[0])
            lattice_origin = output[0]
            lattice_a_end = output[1]
            lattice_b_end = output[2]
        props["LatticeAVector"] = OrderedDict({})
        props["LatticeAVector"]["Coordinate System"] = lattice_cs
        props["LatticeAVector"]["Start"] = lattice_origin
        props["LatticeAVector"]["End"] = lattice_a_end
        props["LatticeBVector"] = OrderedDict({})
        props["LatticeBVector"]["Coordinate System"] = lattice_cs
        props["LatticeBVector"]["Start"] = lattice_origin
        props["LatticeBVector"]["End"] = lattice_b_end
        if not portname:
            portname = generate_unique_name("Floquet")
        return self._create_boundary(portname, props, "Floquet Port")

    @pyaedt_function_handler()
    def assign_lattice_pair(
        self,
        face_couple,
        reverse_v=False,
        phase_delay="UseScanAngle",
        phase_delay_param1="0deg",
        phase_delay_param2="0deg",
        pair_name=None,
    ):
        """Assign a lattice pair to a couple of faces.

        Parameters
        ----------
        face_couple : list
            List of two faces to assign the lattice pair to.
        reverse_v : bool, optional
            Whether to reverse the V vector. The default is `False`.
        phase_delay : str, optional
            Phase delay approach. Options are ``"UseScanAngle"``,
            ``"UseScanUV"``, and ``"InputPhaseDelay"``. The default is
            ``"UseScanAngle"``.
        phase_delay_param1 : str, optional
            Value for the first phase delay parameter, which depends on the approach:

            - Phi angle if the approach is ``"UseScanAngle"``.
            - U value if the approach is ``"UseScanUV"``.
            - Phase if the approach is ``"InputPhaseDelay"``.

            The default is ``0deg``.

        phase_delay_param2 :  str, optional
            Value for the second phase delay parameter, which depends on the approach:

            - Theta angle if the approach is "``UseScanAngle"``.
            - V value if the approach is ``"UseScanUV"``.

            The default is ``0deg``.
        pair_name : str, optional
            Boundary name.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        References
        ----------

        >>> oModule.AssignLatticePair
        """
        props = OrderedDict({})
        face_id = self.modeler.convert_to_selections(face_couple, True)
        props["Faces"] = face_id
        props["ReverseV"] = reverse_v

        props["PhaseDelay"] = phase_delay
        if phase_delay == "UseScanAngle":
            props["Phi"] = phase_delay_param1
            props["Theta"] = phase_delay_param2
        elif phase_delay == "UseScanUV":
            props["ScanU"] = phase_delay_param1
            props["ScanV"] = phase_delay_param2
        else:
            props["Phase"] = phase_delay_param1
        if not pair_name:
            pair_name = generate_unique_name("LatticePair")
        return self._create_boundary(pair_name, props, "Lattice Pair")

    @pyaedt_function_handler()
    def auto_assign_lattice_pairs(self, object_to_assign, coordinate_system="Global", coordinate_plane="XY"):
        """Assign lattice pairs to a geometry automatically.

        Parameters
        ----------
        object_to_assign : str, Object3d
            Object to assign a lattice to.
        coordinate_system : str, optional
            Coordinate system to look for the lattice on.
        coordinate_plane : str, optional
            Plane to look for the lattice on. Options are ``"XY"``, ``"XZ"``, and
            ``"YZ"``. The default is ``"XY"``.

        Returns
        -------
        list of str
            List of created pair names.

        References
        ----------

        >>> oModule.AutoIdentifyLatticePair
        """
        objectname = self.modeler.convert_to_selections(object_to_assign, True)
        boundaries = list(self.oboundary.GetBoundaries())
        self.oboundary.AutoIdentifyLatticePair("{}:{}".format(coordinate_system, coordinate_plane), objectname[0])
        boundaries = [i for i in list(self.oboundary.GetBoundaries()) if i not in boundaries]
        bounds = [i for i in boundaries if boundaries.index(i) % 2 == 0]
        return bounds

    @pyaedt_function_handler()
    def assign_secondary(
        self,
        face,
        primary_name,
        u_start,
        u_end,
        reverse_v=False,
        phase_delay="UseScanAngle",
        phase_delay_param1="0deg",
        phase_delay_param2="0deg",
        coord_name="Global",
        secondary_name=None,
    ):
        """Assign the secondary boundary condition.

        Parameters
        ----------
        face : int, FacePrimitive
            Face to assign the lattice pair to.
        primary_name : str
            Name of the primary boundary to couple.
        u_start : list
            List of ``[x,y,z]`` values for the starting point of the U vector.
        u_end : list
            List of ``[x,y,z]`` values for the ending point of the U vector.
        reverse_v : bool, optional
            Whether to reverse the V vector. The default is ``False``.
        phase_delay : str, optional
            Phase delay approach. Options are ``"UseScanAngle"``,
            ``"UseScanUV"``, and ``"InputPhaseDelay"``. The default is
            ``"UseScanAngle"``.
        phase_delay_param1 : str, optional
            Value for the first phase delay parameter, which depends on the approach:

            - Phi angle if the approach is ``"UseScanAngle"``.
            - U value if the approach is ``"UseScanUV"``.
            - Phase if the approach is ``"InputPhaseDelay"``.

            The default is ``0deg``.
        phase_delay_param2 :  str, optional
            Value for the second phase delay parameter, which depends on the approach:

            - Theta angle if the approach is "``UseScanAngle"``.
            - V value if the approach is ``"UseScanUV"``.

            The default is ``0deg``.
        coord_name : str, optional
            Name of the coordinate system for U coordinates.
        secondary_name : str, optional
            Name of the boundary. The default is ``None``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        References
        ----------

        >>> oModule.AssignSecondary
        """
        props = OrderedDict({})
        face_id = self.modeler.convert_to_selections(face, True)
        if isinstance(face_id[0], str):
            props["Objects"] = face_id

        else:
            props["Faces"] = face_id

        props["CoordSysVector"] = OrderedDict({})
        props["CoordSysVector"]["Coordinate System"] = coord_name
        props["CoordSysVector"]["Origin"] = u_start
        props["CoordSysVector"]["UPos"] = u_end
        props["ReverseV"] = reverse_v

        props["Primary"] = primary_name
        props["PhaseDelay"] = phase_delay
        if phase_delay == "UseScanAngle":
            props["Phi"] = phase_delay_param1
            props["Theta"] = phase_delay_param2
        elif phase_delay == "UseScanUV":
            props["ScanU"] = phase_delay_param1
            props["ScanV"] = phase_delay_param2
        else:
            props["Phase"] = phase_delay_param1
        if not secondary_name:
            secondary_name = generate_unique_name("Secondary")
        return self._create_boundary(secondary_name, props, "Secondary")

    @pyaedt_function_handler()
    def assign_primary(self, face, u_start, u_end, reverse_v=False, coord_name="Global", primary_name=None):
        """Assign the primary boundary condition.

        Parameters
        ----------
        face : int, FacePrimitive
            Face to assign the lattice pair to.
        u_start : list
            List of ``[x,y,z]`` values for the starting point of the U vector.
        u_end : list
            List of ``[x,y,z]`` values for the ending point of the U vector.
        reverse_v : bool, optional
            Whether to reverse the V vector. The default is `False`.
        coord_name : str, optional
            Name of the coordinate system for the U coordinates. The
            default is ``"Global"``.
        primary_name : str, optional
            Name of the boundary. The default is ``None``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        References
        ----------

        >>> oModule.AssignPrimary
        """
        props = OrderedDict({})
        face_id = self.modeler.convert_to_selections(face, True)
        if isinstance(face_id[0], str):
            props["Objects"] = face_id

        else:
            props["Faces"] = face_id
        props["ReverseV"] = reverse_v
        props["CoordSysVector"] = OrderedDict({})
        props["CoordSysVector"]["Coordinate System"] = coord_name
        props["CoordSysVector"]["Origin"] = u_start
        props["CoordSysVector"]["UPos"] = u_end
        if not primary_name:
            primary_name = generate_unique_name("Primary")
        return self._create_boundary(primary_name, props, "Primary")

    def _create_pec_cap(self, sheet_name, obj_name, pecthick):
        # TODO check method
        obj = self.modeler[sheet_name].clone()
        out_obj = self.modeler.thicken_sheet(obj, pecthick, False)
        bounding2 = out_obj.bounding_box
        bounding1 = self.modeler[obj_name].bounding_box
        tol = 1e-9
        i = 0
        internal = False
        for a, b in zip(bounding1, bounding2):
            if i < 3:
                if (b - a) > tol:
                    internal = True
            elif (b - a) < tol:
                internal = True
            i += 1
        if internal:
            self.odesign.Undo()
            self.modeler.cleanup_objects()
            out_obj = self.modeler.thicken_sheet(obj, -pecthick, False)

        out_obj.material_name = "pec"
        return True

    @pyaedt_function_handler()
    def create_wave_port_microstrip_between_objects(
        self,
        startobj,
        endobject,
        axisdir=0,
        impedance=50,
        nummodes=1,
        portname=None,
        renorm=True,
        deembed_dist=0,
        vfactor=3,
        hfactor=5,
    ):
        """Create a waveport taking the closest edges of two objects.

        Parameters
        ----------
        startobj :
            Starting object for the integration line. This is typically the reference plane.
        endobject :
            Ending object for the integration line.
        axisdir : int or :class:`pyaedt.application.Analysis.Analysis.AxisDir`, optional
            Position of the port. It should be one of the values for ``Application.AxisDir``,
            which are: ``XNeg``, ``YNeg``, ``ZNeg``, ``XPos``, ``YPos``, and ``ZPos``.
            The default is ``Application.AxisDir.XNeg``.
        impedance : float, optional
            Port impedance. The default is ``50``.
        nummodes : int, optional
            Number of modes. The default is ``1``.
        portname : str, optional
            Name of the port. The default is ``None``.
        renorm : bool, optional
            Whether to renormalize the mode. The default is ``True``.
        deembed_dist : float, optional
            Deembed distance in millimeters. The default is ``0``,
            in which case deembed is disabled.
        vfactor : int, optional
            Port vertical factor. The default is ``3``.
        hfactor : int, optional
            Port horizontal factor. The default is ``5``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Port object.

        References
        ----------

        >>> oModule.AssignWavePort

        Examples
        --------

        Create a wave port supported by a microstrip line.

        >>> ms = hfss.modeler.create_box([4, 5, 0], [1, 100, 0.2],
        ...                               name="MS1", matname="copper")
        >>> sub = hfss.modeler.create_box([0, 5, -2], [20, 100, 2],
        ...                               name="SUB1", matname="FR4_epoxy")
        >>> gnd = hfss.modeler.create_box([0, 5, -2.2], [20, 100, 0.2],
        ...                               name="GND1", matname="FR4_epoxy")
        >>> port = hfss.create_wave_port_microstrip_between_objects("GND1", "MS1",
        ...                                                         portname="MS1",
        ...                                                         axisdir=1)
        pyaedt INFO: Connection correctly created.

        """
        if not self.modeler.does_object_exists(startobj) or not self.modeler.does_object_exists(endobject):
            self.logger.error("One or both objects do not exist. Check and retry.")
            return False
        if self.solution_type in ["Modal", "Terminal", "Transient Network"]:
            sheet_name, point0, point1 = self.modeler._create_microstrip_sheet_from_object_closest_edge(
                startobj, endobject, axisdir, vfactor, hfactor
            )
            dist = GeometryOperators.points_distance(point0, point1)
            self._create_pec_cap(sheet_name, startobj, dist / 10)
            portname = self._get_unique_source_name(portname, "Port")

            if "Modal" in self.solution_type:
                return self._create_waveport_driven(
                    sheet_name, point0, point1, impedance, portname, renorm, nummodes, deembed_dist
                )
            else:
                faces = self.modeler.get_object_faces(sheet_name)
                if deembed_dist == 0:
                    deembed = None
                else:
                    deembed = deembed_dist
                return self._create_port_terminal(
                    faces[0],
                    endobject,
                    portname,
                    renorm=renorm,
                    deembed=deembed,
                    iswaveport=True,
                    impedance=impedance,
                )
        return False

    @pyaedt_function_handler()
    def create_perfecte_from_objects(
        self, startobj, endobject, axisdir=0, sourcename=None, is_infinite_gnd=False, bound_on_plane=True
    ):
        """Create a Perfect E taking the closest edges of two objects.

        Parameters
        ----------
        startobj :
            Starting object for the integration line.
        endobject :
           Ending object for the integration line.
        axisdir : int or :class:`pyaedt.application.Analysis.Analysis.AxisDir`, optional
            Position of the port. It should be one of the values for
            ``Application.AxisDir``, which are: ``XNeg``, ``YNeg``,
            ``ZNeg``, ``XPos``, ``YPos``, and ``ZPos``.  The default
            is ``Application.AxisDir.XNeg``.
        sourcename : str, optional
            Perfect E name. The default is ``None``.
        is_infinite_gnd : bool, optional
            Whether the Perfect E is an infinite ground. The default is ``False``.
        bound_on_plane : bool, optional
            Whether to create the Perfect E on the plane orthogonal to
            ``AxisDir``. The default is ``True``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject` or bool
            Boundary object if successful, ``False`` otherwise.

        References
        ----------

        >>> oModule.AssignPerfectE

        Examples
        --------

        Create two boxes for creating a Perfect E named ``'PerfectE'``.

        >>> box1 = hfss.modeler.create_box([0,0,0], [10,10,5],
        ...                                "perfect1", "Copper")
        >>> box2 = hfss.modeler.create_box([0, 0, 10], [10, 10, 5],
        ...                                "perfect2", "copper")
        >>> perfect_e = hfss.create_perfecte_from_objects("perfect1", "perfect2",
        ...                                               hfss.AxisDir.ZNeg, "PerfectE")
        pyaedt INFO: Connection Correctly created
        >>> type(perfect_e)
        <class 'pyaedt.modules.Boundary.BoundaryObject'>

        """

        if not self.modeler.does_object_exists(startobj) or not self.modeler.does_object_exists(endobject):
            self.logger.error("One or both objects do not exist. Check and retry.")
            return False
        if self.solution_type in ["Modal", "Terminal", "Transient Network"]:
            sheet_name, point0, point1 = self.modeler._create_sheet_from_object_closest_edge(
                startobj, endobject, axisdir, bound_on_plane
            )

            if not sourcename:
                sourcename = generate_unique_name("PerfE")
            elif sourcename in self.modeler.get_boundaries_name():
                sourcename = generate_unique_name(sourcename)
            return self.create_boundary(self.BoundaryType.PerfectE, sheet_name, sourcename, is_infinite_gnd)
        return False

    @pyaedt_function_handler()
    def create_perfecth_from_objects(self, startobj, endobject, axisdir=0, sourcename=None, bound_on_plane=True):
        """Create a Perfect H taking the closest edges of two objects.

        Parameters
        ----------
        startobj :
            Starting object for the integration line.
        endobject :
            Ending object for the integration line.
        axisdir : int or :class:`pyaedt.application.Analysis.Analysis.AxisDir`, optional
            Position of the port. It should be one of the values for ``Application.AxisDir``,
            which are: ``XNeg``, ``YNeg``, ``ZNeg``, ``XPos``, ``YPos``, and ``ZPos``.
            The default is ``Application.AxisDir.XNeg``.
        sourcename : str, optional
            Perfect H name. The default is ``None``.
        bound_on_plane : bool, optional
            Whether to create the Perfect H on the plane orthogonal to ``AxisDir``. The default is ``True``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject` or bool
            Boundary object if successful, ``False`` otherwise.

        References
        ----------

        >>> oModule.AssignPerfectH

        Examples
        --------

        Create two boxes for creating a Perfect H named ``'PerfectH'``.

        >>> box1 = hfss.modeler.create_box([0,0,20], [10,10,5],
        ...                                "perfect1", "Copper")
        >>> box2 = hfss.modeler.create_box([0, 0, 30], [10, 10, 5],
        ...                                "perfect2", "copper")
        >>> perfect_h = hfss.create_perfecth_from_objects("perfect1", "perfect2",
        ...                                               hfss.AxisDir.ZNeg, "Perfect H")
        pyaedt INFO: Connection Correctly created
        >>> type(perfect_h)
        <class 'pyaedt.modules.Boundary.BoundaryObject'>

        """

        if not self.modeler.does_object_exists(startobj) or not self.modeler.does_object_exists(endobject):
            self.logger.error("One or both objects do not exist. Check and retry.")
            return False
        if self.solution_type in ["Modal", "Terminal", "Transient Network"]:
            sheet_name, point0, point1 = self.modeler._create_sheet_from_object_closest_edge(
                startobj, endobject, axisdir, bound_on_plane
            )

            if not sourcename:
                sourcename = generate_unique_name("PerfH")
            elif sourcename in self.modeler.get_boundaries_name():
                sourcename = generate_unique_name(sourcename)
            return self.create_boundary(self.BoundaryType.PerfectH, sheet_name, sourcename)
        return None

    @pyaedt_function_handler()
    def SARSetup(self, Tissue_object_List_ID, TissueMass=1, MaterialDensity=1, voxel_size=1, Average_SAR_method=0):
        """Define SAR settings.

        .. deprecated:: 0.4.5
           Use :func:`Hfss.sar_setup` instead.

        """
        warnings.warn("`SARSetup` is deprecated. Use `sar_setup` instead.", DeprecationWarning)
        self.sar_setup(Tissue_object_List_ID, TissueMass, MaterialDensity, voxel_size, Average_SAR_method)

    @pyaedt_function_handler()
    def sar_setup(self, Tissue_object_List_ID, TissueMass=1, MaterialDensity=1, voxel_size=1, Average_SAR_method=0):
        """Define SAR settings.

        Parameters
        ----------
        Tissue_object_List_ID : int

        TissueMass : float, optional
            The default is ``1``.
        MaterialDensity : optional
            The default is ``1``.
        voxel_size : optional
            The default is ``1``.
        Average_SAR_method : optional
            The default is ``0``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oDesign.SARSetup
        """
        self.odesign.SARSetup(TissueMass, MaterialDensity, Tissue_object_List_ID, voxel_size, Average_SAR_method)
        self.logger.info("SAR Settings correctly applied.")
        return True

    @pyaedt_function_handler()
    def create_open_region(self, Frequency="1GHz", Boundary="Radiation", ApplyInfiniteGP=False, GPAXis="-z"):
        """Create an open region on the active editor.

        Parameters
        ----------
        Frequency : str, optional
            Frequency with units. The default is ``"1GHz"``.
        Boundary : str, optional
            Type of the boundary. The default is ``"Radiation"``.
        ApplyInfiniteGP : bool, optional
            Whether to apply an infinite ground plane. The default is ``False``.
        GPAXis : str, optional
            The default is ``"-z"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oModule.CreateOpenRegion
        """
        vars = ["NAME:Settings", "OpFreq:=", Frequency, "Boundary:=", Boundary, "ApplyInfiniteGP:=", ApplyInfiniteGP]
        if ApplyInfiniteGP:
            vars.append("Direction:=")
            vars.append(GPAXis)

        self.omodelsetup.CreateOpenRegion(vars)
        self.logger.info("Open Region correctly created.")
        return True

    @pyaedt_function_handler()
    def create_lumped_rlc_between_objects(
        self,
        startobj,
        endobject,
        axisdir=0,
        sourcename=None,
        rlctype="Parallel",
        Rvalue=None,
        Lvalue=None,
        Cvalue=None,
        bound_on_plane=True,
    ):
        """Create a lumped RLC taking the closest edges of two objects.

        Parameters
        ----------
        startobj :
            Starting object for the integration line.
        endobject :
            Ending object for the integration line.
        axisdir : int or :class:`pyaedt.application.Analysis.Analysis.AxisDir`, optional
            Position of the port. It should be one of the values for ``Application.AxisDir``,
            which are: ``XNeg``, ``YNeg``, ``ZNeg``, ``XPos``, ``YPos``, and ``ZPos``.
            The default is ``Application.AxisDir.XNeg``.
        sourcename : str, optional
            Perfect H name. The default is ``None``.
        rlctype : str, optional
            Type of the RLC. Options are ``"Parallel"`` and ``"Serial"``.
            The default is ``"Parallel"``.
        Rvalue : optional
            Resistance value in ohms. The default is ``None``,
            in which case this parameter is disabled.
        Lvalue : optional
            Inductance value in H. The default is ``None``,
            in which case this parameter is disabled.
        Cvalue : optional
            Capacitance value in F. The default is ``None``,
            in which case this parameter is disabled.
        bound_on_plane : bool, optional
            Whether to create the boundary on the plane orthogonal
            to ``AxisDir``. The default is ``True``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject` or bool
            Boundary object if successful, ``False`` otherwise.

        References
        ----------

        >>> oModule.AssignLumpedRLC

        Examples
        --------

        Create two boxes for creating a lumped RLC named ``'LumpedRLC'``.

        >>> box1 = hfss.modeler.create_box([0, 0, 50], [10, 10, 5],
        ...                                           "rlc1", "copper")
        >>> box2 = hfss.modeler.create_box([0, 0, 60], [10, 10, 5],
        ...                                           "rlc2", "copper")
        >>> rlc = hfss.create_lumped_rlc_between_objects("rlc1", "rlc2", hfss.AxisDir.XPos,
        ...                                              "Lumped RLC", Rvalue=50,
        ...                                              Lvalue=1e-9, Cvalue = 1e-6)
        pyaedt INFO: Connection Correctly created

        """

        if not self.modeler.does_object_exists(startobj) or not self.modeler.does_object_exists(endobject):
            self.logger.error("One or both objects do not exist. Check and retry.")
            return False
        if self.solution_type in ["Modal", "Terminal", "Transient Network"] and (Rvalue or Lvalue or Cvalue):
            sheet_name, point0, point1 = self.modeler._create_sheet_from_object_closest_edge(
                startobj, endobject, axisdir, bound_on_plane
            )

            if not sourcename:
                sourcename = generate_unique_name("Lump")
            elif sourcename in self.modeler.get_boundaries_name():
                sourcename = generate_unique_name(sourcename)
            start = [str(i) + self.modeler.model_units for i in point0]
            stop = [str(i) + self.modeler.model_units for i in point1]

            props = OrderedDict()
            props["Objects"] = [sheet_name]
            props["CurrentLine"] = OrderedDict({"Start": start, "End": stop})
            props["RLC Type"] = rlctype
            if Rvalue:
                props["UseResist"] = True
                props["Resistance"] = str(Rvalue) + "ohm"
            if Lvalue:
                props["UseInduct"] = True
                props["Inductance"] = str(Lvalue) + "H"
            if Cvalue:
                props["UseCap"] = True
                props["Capacitance"] = str(Cvalue) + "F"

            return self._create_boundary(sourcename, props, "Lumped RLC")
        return False

    @pyaedt_function_handler()
    def create_impedance_between_objects(
        self,
        startobj,
        endobject,
        axisdir=0,
        sourcename=None,
        resistance=50,
        reactance=0,
        is_infground=False,
        bound_on_plane=True,
    ):
        """Create an impedance taking the closest edges of two objects.

        Parameters
        ----------
        startobj :
            Starting object for the integration line.
        endobject :
            Ending object for the integration line.
        axisdir : int or :class:`pyaedt.application.Analysis.Analysis.AxisDir`, optional
            Position of the port. It should be one of the values for ``Application.AxisDir``,
            which are: ``XNeg``, ``YNeg``, ``ZNeg``, ``XPos``, ``YPos``, and ``ZPos``.
            The default is ``Application.AxisDir.XNeg``.
        sourcename : str, optional
            Name of the impedance. The default is ``None``.
        resistance : float, optional
            Resistance value in ohms. The default is ``50``. If ``None``,
            this parameter is disabled.
        reactance : optional
            Reactance value in ohms. The default is ``0``. If ``None``,
            this parameter is disabled.
        is_infground : bool, optional
            Whether the impendance is an infinite ground. The default is ``False``.
        bound_on_plane : bool, optional
            Whether to create the impedance on the plane orthogonal to ``AxisDir``.
            The default is ``True``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject` or bool
            Boundary object if successful, ``False`` otherwise.

        References
        ----------

        >>> oModule.AssignImpedance

        Examples
        --------

        Create two boxes for creating an impedance named ``'ImpedanceExample'``.

        >>> box1 = hfss.modeler.create_box([0, 0, 70], [10, 10, 5],
        ...                                           "box1", "copper")
        >>> box2 = hfss.modeler.create_box([0, 0, 80], [10, 10, 5],
        ...                                           "box2", "copper")
        >>> impedance = hfss.create_impedance_between_objects("box1", "box2", hfss.AxisDir.XPos,
        ...                                                   "ImpedanceExample", 100, 50)
        pyaedt INFO: Connection Correctly created

        """

        if not self.modeler.does_object_exists(startobj) or not self.modeler.does_object_exists(endobject):
            self.logger.error("One or both objects do not exist. Check and retry.")
            return False
        if self.solution_type in ["Modal", "Terminal", "Transient Network"]:
            sheet_name, point0, point1 = self.modeler._create_sheet_from_object_closest_edge(
                startobj, endobject, axisdir, bound_on_plane
            )

            if not sourcename:
                sourcename = generate_unique_name("Imped")
            elif sourcename in self.modeler.get_boundaries_name():
                sourcename = generate_unique_name(sourcename)
            props = OrderedDict(
                {
                    "Objects": [sheet_name],
                    "Resistance": str(resistance),
                    "Reactance": str(reactance),
                    "InfGroundPlane": is_infground,
                }
            )
            return self._create_boundary(sourcename, props, "Impedance")
        return False

    @pyaedt_function_handler()
    def create_boundary(
        self, boundary_type=BoundaryType.PerfectE, sheet_name=None, boundary_name="", is_infinite_gnd=False
    ):
        """Create a boundary given specific inputs.

        Parameters
        ----------
        boundary_type : str, optional
            Boundary type object. Options are ``"Perfect E"``, ``"Perfect H"``, ``"Aperture"``, and
            ``"Radiation"``. The default is ``PerfectE``.
        sheet_name : in, str, or list, optional
            Name of the sheet. It can be an integer (face ID), a string (sheet), or a list of integers
            and strings. The default is ``None``.
        boundary_name : str, optional
            Name of the boundary. The default is ``""``.
        is_infinite_gnd : bool, optional
            Whether the boundary is an infinite ground. The default is ``False``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        """

        props = {}
        sheet_name = self.modeler.convert_to_selections(sheet_name, True)
        if type(sheet_name) is list:
            if type(sheet_name[0]) is str:
                props["Objects"] = sheet_name
            else:
                props["Faces"] = sheet_name

        if boundary_type == self.BoundaryType.PerfectE:
            props["InfGroundPlane"] = is_infinite_gnd
            boundary_type = "Perfect E"
        elif boundary_type == self.BoundaryType.PerfectH:
            boundary_type = "Perfect H"
        elif boundary_type == self.BoundaryType.Aperture:
            boundary_type = "Aperture"
        elif boundary_type == self.BoundaryType.Radiation:
            props["IsFssReference"] = False
            props["IsForPML"] = False
            boundary_type = "Radiation"
        elif boundary_type == self.BoundaryType.Hybrid:
            props["IsLinkedRegion"] = False
            props["Type"] = "SBR+"
            boundary_type = "Hybrid"
        else:
            return None
        return self._create_boundary(boundary_name, props, boundary_type)

    @pyaedt_function_handler()
    def _get_reference_and_integration_points(self, sheet, axisdir, obj_name=None):
        if isinstance(sheet, int):
            objID = [sheet]
            sheet = obj_name
        else:
            objID = self.modeler.oeditor.GetFaceIDs(sheet)
        face_edges = self.modeler.get_face_edges(objID[0])
        mid_points = [self.modeler.get_edge_midpoint(i) for i in face_edges]
        if axisdir < 3:
            min_point = [1e6, 1e6, 1e6]
            max_point = [-1e6, -1e6, -1e6]
            for el in mid_points:
                if el[axisdir] < min_point[axisdir]:
                    min_point = el
                if el[axisdir] > max_point[axisdir]:
                    max_point = el
        else:
            min_point = [-1e6, -1e6, -1e6]
            max_point = [1e6, 1e6, 1e6]
            for el in mid_points:
                if el[axisdir - 3] > min_point[axisdir - 3]:
                    min_point = el
                if el[axisdir - 3] < max_point[axisdir - 3]:
                    max_point = el

        refid = self.modeler.get_bodynames_from_position(min_point)
        refid.remove(sheet)
        diels = self.get_all_dielectrics_names()
        for el in refid:
            if el in diels:
                refid.remove(el)

        int_start = None
        int_stop = None
        if min_point != max_point:
            int_start = min_point
            int_stop = max_point
        return refid, int_start, int_stop

    @pyaedt_function_handler()
    def create_wave_port_from_sheet(
        self,
        sheet,
        deemb=0,
        axisdir=None,
        impedance=50,
        nummodes=1,
        portname=None,
        renorm=True,
        terminal_references=None,
    ):
        """Create a waveport on sheet objects created starting from sheets.

        Parameters
        ----------
        sheet : str or int or list or :class:`pyaedt.modeler.object3d.Object3d`
            Name of the sheet.
        deemb : float, optional
            Deembedding value distance in model units. The default is ``0``.
        axisdir : int or :class:`pyaedt.application.Analysis.Analysis.AxisDir`, optional
            Position of the port. It is used to auto evaluate the integration line.
            If set to ``None`` the integration line is not defined.
            It should be one of the values for ``Application.AxisDir``,
            which are: ``XNeg``, ``YNeg``, ``ZNeg``, ``XPos``, ``YPos``, and ``ZPos``.
            The default is ``None`` and no integration line is defined.
        impedance : float, optional
            Port impedance. The default is ``50``.
        nummodes : int, optional
            Number of modes. The default is ``1``.
        portname : str, optional
            Name of the port. The default is ``None``.
        renorm : bool, optional
            Whether to renormalize the mode. The default is ``True``.
        terminal_references : list, optional
            For a driven-terminal simulation, list of conductors for port terminal definitions.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        References
        ----------

        >>> oModule.AssignWavePort

        Examples
        --------

        Create a circle sheet for creating a wave port named ``'WavePortFromSheet'``.

        >>> origin_position = hfss.modeler.Position(0, 0, 0)
        >>> circle = hfss.modeler.create_circle(hfss.PLANE.YZ,
        ...                                                origin_position, 10, name="WaveCircle")
        >>> hfss.solution_type = "Modal"
        >>> port = hfss.create_wave_port_from_sheet(circle, 5, hfss.AxisDir.XNeg, 40, 2,
        ...                                         "WavePortFromSheet", True)
        >>> port[0].name
        'WavePortFromSheet'

        """

        sheet = self.modeler.convert_to_selections(sheet, True)[0]
        if terminal_references:
            terminal_references = self.modeler.convert_to_selections(terminal_references, True)
        if isinstance(sheet, int):
            try:
                oname = self.modeler.oeditor.GetObjectNameByFaceID(sheet)
            except:
                oname = ""
        else:
            oname = ""
        if "Modal" in self.solution_type:
            if axisdir:
                try:
                    _, int_start, int_stop = self._get_reference_and_integration_points(sheet, axisdir, oname)
                except (IndexError, TypeError):
                    int_start = int_stop = None
            else:
                int_start = int_stop = None
            portname = self._get_unique_source_name(portname, "Port")

            return self._create_waveport_driven(
                sheet, int_start, int_stop, impedance, portname, renorm, nummodes, deemb
            )
        else:
            if isinstance(sheet, int):
                faces = sheet
            else:
                faces = self.modeler.get_object_faces(sheet)[0]
            if not faces:  # pragma: no cover
                self.logger.error("Wrong Input object. it has to be a face id or a sheet.")
                return False
            if not portname:
                portname = generate_unique_name("Port")
            elif portname in self.excitations:
                portname = generate_unique_name(portname)
            if terminal_references:
                if deemb == 0:
                    deembed = None
                else:
                    deembed = deemb
                return self._create_port_terminal(
                    faces,
                    terminal_references,
                    portname,
                    renorm=renorm,
                    deembed=deembed,
                    iswaveport=True,
                    impedance=impedance,
                )
            else:
                self.logger.error("Reference conductors are missing.")
                return False

    @pyaedt_function_handler()
    def create_lumped_port_to_sheet(
        self, sheet_name, axisdir=0, impedance=50, portname=None, renorm=True, deemb=False, reference_object_list=[]
    ):
        """Create a lumped port taking one sheet.

        Parameters
        ----------
        sheet_name : str
            Name of the sheet.
        axisdir : int, :class:`pyaedt.application.Analysis.Analysis.AxisDir` or list, optional
            Direction of the integration line. It should be one of the values for ``Application.AxisDir``,
            which are: ``XNeg``, ``YNeg``, ``ZNeg``, ``XPos``, ``YPos``, and ``ZPos``. It also accepts the list
            of the start point and end point with the format [[xstart, ystart, zstart], [xend, yend, zend]].
            The default is ``Application.AxisDir.XNeg``.
        impedance : float, optional
            Port impedance. The default is ``50``.
        portname : str, optional
            Name of the port. The default is ``None``.
        renorm : bool, optional
            Whether to renormalize the mode. The default is ``True``.
        deemb : bool, optional
            Whether to deembed the port. The default is ``False``.
        reference_object_list : list, optional
            For a driven terminal solution only, a list of reference conductors. The default is ``[]``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        References
        ----------

        >>> oModule.AssignLumpedPort

        Examples
        --------

        Create a rectangle sheet for creating a lumped port named ``'LumpedPortFromSheet'``.

        >>> rectangle = hfss.modeler.create_rectangle(hfss.PLANE.XY,
        ...                                                      [0, 0, 0], [10, 2], name="lump_port",
        ...                                                      matname="copper")
        >>> h1 = hfss.create_lumped_port_to_sheet(rectangle.name, hfss.AxisDir.XNeg, 50,
        ...                                  "LumpedPortFromSheet", True, False)
        >>> h2 = hfss.create_lumped_port_to_sheet(rectangle.name, [rectangle.bottom_edge_x.midpoint,
        ...                                     rectangle.bottom_edge_y.midpoint], 50, "LumpedPortFromSheet", True,
        ...                                     False)

        """
        sheet_name = self.modeler.convert_to_selections(sheet_name, False)
        if self.solution_type in ["Modal", "Terminal", "Transient Network"]:
            if isinstance(axisdir, list):
                if len(axisdir) != 2 or len(axisdir[0]) != len(axisdir[1]):
                    self.logger.error("List of coordinates is not set correctly")
                    return False
                point0 = axisdir[0]
                point1 = axisdir[1]
            else:
                point0, point1 = self.modeler.get_mid_points_on_dir(sheet_name, axisdir)

            portname = self._get_unique_source_name(portname, "Port")

            port = False
            if "Modal" in self.solution_type:
                port = self._create_lumped_driven(sheet_name, point0, point1, impedance, portname, renorm, deemb)
            else:
                if not reference_object_list:
                    cond = self.get_all_conductors_names()
                    touching = self.modeler.get_bodynames_from_position(point0)
                    reference_object_list = []
                    for el in touching:
                        if el in cond:
                            reference_object_list.append(el)
                if isinstance(sheet_name, int):
                    faces = sheet_name
                else:
                    faces = self.modeler.get_object_faces(sheet_name)[0]
                if not faces:  # pragma: no cover
                    self.logger.error("Wrong input object. It must be a face ID or a sheet.")
                    return False
                if deemb:
                    deembed = 0
                else:
                    deembed = None
                port = self._create_port_terminal(
                    faces,
                    reference_object_list,
                    portname,
                    renorm=renorm,
                    deembed=deembed,
                    iswaveport=False,
                    impedance=impedance,
                )

            return port
        return False

    @pyaedt_function_handler()
    def assig_voltage_source_to_sheet(self, sheet_name, axisdir=0, sourcename=None):
        """Create a voltage source taking one sheet.

        .. deprecated:: 0.4.0
           Use :func:`Hfss.assign_voltage_source_to_sheet` instead.

        """

        warnings.warn(
            "`assig_voltage_source_to_sheet` is deprecated. Use `assign_voltage_source_to_sheet` instead.",
            DeprecationWarning,
        )
        self.assign_voltage_source_to_sheet(sheet_name, axisdir, sourcename)

    @pyaedt_function_handler()
    def assign_voltage_source_to_sheet(self, sheet_name, axisdir=0, sourcename=None):
        """Create a voltage source taking one sheet.

        Parameters
        ----------
        sheet_name : str
            Name of the sheet to apply the boundary to.
        axisdir : int, :class:`pyaedt.application.Analysis.Analysis.AxisDir` or list, optional
            Direction of the integration line. It should be one of the values for ``Application.AxisDir``,
            which are: ``XNeg``, ``YNeg``, ``ZNeg``, ``XPos``, ``YPos``, and ``ZPos``. It also accepts the list
            of the start point and end point with the format [[xstart, ystart, zstart], [xend, yend, zend]]
            The default is ``Application.AxisDir.XNeg``.
        sourcename : str, optional
            Name of the source. The default is ``None``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        References
        ----------

        >>> oModule.AssignVoltage

        Examples
        --------

        Create a sheet and assign to it some voltage.

        >>> sheet = hfss.modeler.create_rectangle(hfss.PLANE.XY,
        ...                                                  [0, 0, -70], [10, 2], name="VoltageSheet",
        ...                                                  matname="copper")
        >>> v1 = hfss.assign_voltage_source_to_sheet(sheet.name, hfss.AxisDir.XNeg, "VoltageSheetExample")
        >>> v2 = hfss.assign_voltage_source_to_sheet(sheet.name, [sheet.bottom_edge_x.midpoint,
        ...                                     sheet.bottom_edge_y.midpoint], 50, "LumpedPortFromSheet", True,
        ...                                     False)

        """

        if self.solution_type in ["Modal", "Terminal", "Transient Network"]:
            if isinstance(axisdir, list):
                if len(axisdir) != 2 or len(axisdir[0]) != len(axisdir[1]):
                    self.logger.error("List of coordinates is not set correctly")
                    return False
                point0 = axisdir[0]
                point1 = axisdir[1]
            else:
                point0, point1 = self.modeler.get_mid_points_on_dir(sheet_name, axisdir)
            sourcename = self._get_unique_source_name(sourcename, "Voltage")
            return self.create_source_excitation(sheet_name, point0, point1, sourcename, sourcetype="Voltage")
        return False

    @pyaedt_function_handler()
    def assign_current_source_to_sheet(self, sheet_name, axisdir=0, sourcename=None):
        """Create a current source taking one sheet.

        Parameters
        ----------
        sheet_name : str
            Name of the sheet to apply the boundary to.
        axisdir : int, :class:`pyaedt.application.Analysis.Analysis.AxisDir` or list, optional
            Direction of the integration line. It should be one of the values for ``Application.AxisDir``,
            which are: ``XNeg``, ``YNeg``, ``ZNeg``, ``XPos``, ``YPos``, and ``ZPos``. It also accepts the list
            of the start point and end point with the format [[xstart, ystart, zstart], [xend, yend, zend]]
            The default is ``Application.AxisDir.XNeg``.
        sourcename : str, optional
            Name of the source. The default is ``None``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        References
        ----------

        >>> oModule.AssignCurrent

        Examples
        --------

        Create a sheet and assign some current to it.

        >>> sheet = hfss.modeler.create_rectangle(hfss.PLANE.XY, [0, 0, -50],
        ...                                                  [5, 1], name="CurrentSheet", matname="copper")
        >>> hfss.assign_current_source_to_sheet(sheet.name, hfss.AxisDir.XNeg, "CurrentSheetExample")
        'CurrentSheetExample'
        >>> c1 = hfss.assign_current_source_to_sheet(sheet.name, [sheet.bottom_edge_x.midpoint,
        ...                                     sheet.bottom_edge_y.midpoint])

        """

        if self.solution_type in ["Modal", "Terminal", "Transient Network"]:
            if isinstance(axisdir, list):
                if len(axisdir) != 2 or len(axisdir[0]) != len(axisdir[1]):
                    self.logger.error("List of coordinates is not set correctly")
                    return False
                point0 = axisdir[0]
                point1 = axisdir[1]
            else:
                point0, point1 = self.modeler.get_mid_points_on_dir(sheet_name, axisdir)
            sourcename = self._get_unique_source_name(sourcename, "Current")
            return self.create_source_excitation(sheet_name, point0, point1, sourcename, sourcetype="Current")
        return False

    @pyaedt_function_handler()
    def assign_perfecte_to_sheets(self, sheet_list, sourcename=None, is_infinite_gnd=False):
        """Create a Perfect E taking one sheet.

        Parameters
        ----------
        sheet_list : str or list
            Name of the sheet or list to apply the boundary to.
        sourcename : str, optional
            Name of the Perfect E source. The default is ``None``.
        is_infinite_gnd : bool, optional
            Whether the Perfect E is an infinite ground. The default is ``False``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        References
        ----------

        >>> oModule.AssignPerfectE

        Examples
        --------

        Create a sheet and use it to create a Perfect E.

        >>> sheet = hfss.modeler.create_rectangle(hfss.PLANE.XY, [0, 0, -90],
        ...                                       [10, 2], name="PerfectESheet", matname="Copper")
        >>> perfect_e_from_sheet = hfss.assign_perfecte_to_sheets(sheet.name, "PerfectEFromSheet")
        >>> type(perfect_e_from_sheet)
        <class 'pyaedt.modules.Boundary.BoundaryObject'>

        """
        sheet_list = self.modeler.convert_to_selections(sheet_list, True)
        if self.solution_type in ["Modal", "Terminal", "Transient Network", "SBR+"]:
            if not sourcename:
                sourcename = generate_unique_name("PerfE")
            elif sourcename in self.modeler.get_boundaries_name():
                sourcename = generate_unique_name(sourcename)
            return self.create_boundary(self.BoundaryType.PerfectE, sheet_list, sourcename, is_infinite_gnd)
        return None

    @pyaedt_function_handler()
    def assign_perfecth_to_sheets(self, sheet_list, sourcename=None):
        """Assign a Perfect H to sheets.

        Parameters
        ----------
        sheet_list : list
            List of sheets to apply the boundary to.
        sourcename : str, optional
            Perfect H name. The default is ``None``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        References
        ----------

        >>> oModule.AssignPerfectH

        Examples
        --------

        Create a sheet and use it to create a Perfect H.

        >>> sheet = hfss.modeler.create_rectangle(hfss.PLANE.XY, [0, 0, -90],
        ...                                       [10, 2], name="PerfectHSheet", matname="Copper")
        >>> perfect_h_from_sheet = hfss.assign_perfecth_to_sheets(sheet.name, "PerfectHFromSheet")
        >>> type(perfect_h_from_sheet)
        <class 'pyaedt.modules.Boundary.BoundaryObject'>

        """

        if self.solution_type in ["Modal", "Terminal", "Transient Network", "SBR+"]:

            if not sourcename:
                sourcename = generate_unique_name("PerfH")
            elif sourcename in self.modeler.get_boundaries_name():
                sourcename = generate_unique_name(sourcename)
            return self.create_boundary(self.BoundaryType.PerfectH, sheet_list, sourcename)
        return None

    @pyaedt_function_handler()
    def assign_lumped_rlc_to_sheet(
        self, sheet_name, axisdir=0, sourcename=None, rlctype="Parallel", Rvalue=None, Lvalue=None, Cvalue=None
    ):
        """Create a lumped RLC taking one sheet.

        Parameters
        ----------
        sheet_name : str
            Name of the sheet to apply the boundary to.
        axisdir : int, :class:`pyaedt.application.Analysis.Analysis.AxisDir` or list, optional
            Direction of the integration line. It should be one of the values for ``Application.AxisDir``,
            which are: ``XNeg``, ``YNeg``, ``ZNeg``, ``XPos``, ``YPos``, and ``ZPos``. It also accepts the list
            of the start point and end point with the format [[xstart, ystart, zstart], [xend, yend, zend]]
            The default is ``Application.AxisDir.XNeg``.
        sourcename : str, optional
            Lumped RLC name. The default is ``None``.
        rlctype : str, optional
            Type of the RLC. Options are ``"Parallel"`` and ``"Serial"``. The default is ``"Parallel"``.
        Rvalue : float, optional
            Resistance value in ohms. The default is ``None``, in which
            case this parameter is disabled.
        Lvalue : optional
            Inductance value in Henry (H). The default is ``None``, in which
            case this parameter is disabled.
        Cvalue : optional
            Capacitance value in  farads (F). The default is ``None``, in which
            case this parameter is disabled.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object if successful, ``False`` otherwise.

        References
        ----------

        >>> oModule.AssignLumpedRLC

        Examples
        --------

        Create a sheet and use it to create a lumped RLC.

        >>> sheet = hfss.modeler.create_rectangle(hfss.PLANE.XY,
        ...                                       [0, 0, -90], [10, 2], name="RLCSheet",
        ...                                        matname="Copper")
        >>> lumped_rlc_to_sheet = hfss.assign_lumped_rlc_to_sheet(sheet.name, hfss.AxisDir.XPos,
        ...                                                       Rvalue=50, Lvalue=1e-9,
        ...                                                       Cvalue=1e-6)
        >>> type(lumped_rlc_to_sheet)
        <class 'pyaedt.modules.Boundary.BoundaryObject'>
        >>> h2 = hfss.assign_lumped_rlc_to_sheet(sheet.name, [sheet.bottom_edge_x.midpoint,
        ...                                     sheet.bottom_edge_y.midpoint], Rvalue=50, Lvalue=1e-9, Cvalue=1e-6)

        """

        if self.solution_type in ["Eigenmode", "Modal", "Terminal", "Transient Network", "SBR+"] and (
            Rvalue or Lvalue or Cvalue
        ):
            if isinstance(axisdir, list):
                if len(axisdir) != 2 or len(axisdir[0]) != len(axisdir[1]):
                    self.logger.error("List of coordinates is not set correctly")
                    return False
                point0 = axisdir[0]
                point1 = axisdir[1]
            else:
                point0, point1 = self.modeler.get_mid_points_on_dir(sheet_name, axisdir)

            if not sourcename:
                sourcename = generate_unique_name("Lump")
            elif sourcename in self.modeler.get_boundaries_name():
                sourcename = generate_unique_name(sourcename)
            start = [str(i) + self.modeler.model_units for i in point0]
            stop = [str(i) + self.modeler.model_units for i in point1]
            props = OrderedDict()
            props["Objects"] = [sheet_name]
            props["CurrentLine"] = OrderedDict({"Start": start, "End": stop})
            props["RLC Type"] = rlctype
            if Rvalue:
                props["UseResist"] = True
                props["Resistance"] = str(Rvalue) + "ohm"
            if Lvalue:
                props["UseInduct"] = True
                props["Inductance"] = str(Lvalue) + "H"
            if Cvalue:
                props["UseCap"] = True
                props["Capacitance"] = str(Cvalue) + "F"
            return self._create_boundary(sourcename, props, "Lumped RLC")
        return False

    @pyaedt_function_handler()
    def assign_impedance_to_sheet(self, sheet_name, sourcename=None, resistance=50, reactance=0, is_infground=False):
        """Create an impedance taking one sheet.

        Parameters
        ----------
        sheet_name : str
            Name of the sheet to apply the boundary to.
        sourcename : str, optional
            Name of the impedance. The default is ``None``.
        resistance : optional
            Resistance value in ohms. The default is ``50``. If ``None``,
            this parameter is disabled.
        reactance : optional
            Reactance value in ohms. The default is ``0``. If ``None``,
            this parameter is disabled.
        is_infground : bool, optional
            Whether the impedance is an infinite ground. The default is ``False``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object if successful, ``False`` otherwise.

        References
        ----------

        >>> oModule.AssignImpedance

        Examples
        --------

        Create a sheet and use it to create an impedance.

        >>> sheet = hfss.modeler.create_rectangle(hfss.PLANE.XY,
        ...                                       [0, 0, -90], [10, 2], name="ImpedanceSheet",
        ...                                        matname="Copper")
        >>> impedance_to_sheet = hfss.assign_impedance_to_sheet(sheet.name, "ImpedanceFromSheet", 100, 50)
        >>> type(impedance_to_sheet)
        <class 'pyaedt.modules.Boundary.BoundaryObject'>

        """

        if self.solution_type in ["Modal", "Terminal", "Transient Network"]:

            if not sourcename:
                sourcename = generate_unique_name("Imped")
            elif sourcename in self.modeler.get_boundaries_name():
                sourcename = generate_unique_name(sourcename)
            props = OrderedDict(
                {
                    "Objects": [sheet_name],
                    "Resistance": str(resistance),
                    "Reactance": str(reactance),
                    "InfGroundPlane": is_infground,
                }
            )
            return self._create_boundary(sourcename, props, "Impedance")
        return False

    @pyaedt_function_handler()
    def create_circuit_port_from_edges(
        self,
        edge_signal,
        edge_gnd,
        port_name="",
        port_impedance="50",
        renormalize=False,
        renorm_impedance="50",
        deembed=False,
    ):
        """Create a circuit port from two edges.

        The integration line is from edge 2 to edge 1.

        Parameters
        ----------
        edge_signal : int
            Edge ID of the signal.
        edge_gnd : int
            Edge ID of the ground.
        port_name : str, optional
            Name of the port. The default is ``""``.
        port_impedance : int, str, or float, optional
            Impedance. The default is ``"50"``. You can also
            enter a string that looks like this: ``"50+1i*55"``.
        renormalize : bool, optional
            Whether to renormalize the mode. The default is ``False``.
            This parameter is ignored for a driven terminal.
        renorm_impedance :  str, optional
            Impedance. The default is ``50``.
        deembed : bool, optional
            Whether to deembed the port. The default is ``False``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        References
        ----------

        >>> oModule.AssignCircuitPort

        Examples
        --------

        Create two rectangles in the XY plane.
        Select the first edge of each rectangle created previously.
        Create a circuit port from the first edge of the first rectangle
        toward the first edge of the second rectangle.

        >>> plane = hfss.PLANE.XY
        >>> rectangle1 = hfss.modeler.create_rectangle(plane, [10, 10, 10], [10, 10],
        ...                                            name="rectangle1_for_port")
        >>> edges1 = hfss.modeler.get_object_edges(rectangle1.id)
        >>> first_edge = edges1[0]
        >>> rectangle2 = hfss.modeler.create_rectangle(plane, [30, 10, 10], [10, 10],
        ...                                            name="rectangle2_for_port")
        >>> edges2 = hfss.modeler.get_object_edges(rectangle2.id)
        >>> second_edge = edges2[0]
        >>> hfss.solution_type = "Modal"
        >>> hfss.create_circuit_port_from_edges(first_edge, second_edge, port_name="PortExample",
        ...                                     port_impedance=50.1, renormalize=False,
        ...                                     renorm_impedance="50")
        'PortExample'

        """

        edge_list = [edge_signal, edge_gnd]
        port_name = self._get_unique_source_name(port_name, "Port")

        return self._create_circuit_port(
            edge_list, port_impedance, port_name, renormalize, deembed, renorm_impedance=renorm_impedance
        )

    @pyaedt_function_handler()
    def edit_sources(
        self, excitations, include_port_post_processing=True, max_available_power=None, use_incident_voltage=False
    ):
        """Set up the power loaded for HFSS postprocessing in multiple sources simultaneously.

        Parameters
        ----------
        excitations : dict
            Dictionary of input sources to modify module and phase.
            Dictionary values can be:
            - 1 value to setup 0deg as default
            - 2 values tuple or list (magnitude and phase) or
            - 3 values (magnitude, phase, and termination flag) for Terminal solution in case of incident voltage usage.

        Returns
        -------
        bool

        Examples
        --------
        >>> sources = {"Port1:1": ("0W", "0deg"), "Port2:1": ("1W", "90deg")}
        >>> hfss.edit_sources(sources, include_port_post_processing=True)

        >>> sources = {"Box2_T1": ("0V", "0deg", True), "Box1_T1": ("1V", "90deg")}
        >>> hfss.edit_sources(sources, max_available_power="2W", use_incident_voltage=True)
        """
        data = {i: ("0W", "0deg", False) for i in self.excitations}
        for key, value in excitations.items():
            data[key] = value
        setting = []
        for key, vals in data.items():
            if isinstance(vals, str):
                power = vals
                phase = "0deg"
            else:
                power = vals[0]
                if len(vals) == 1:
                    phase = "0deg"
                else:
                    phase = vals[1]
            if isinstance(vals, (list, tuple)) and len(vals) == 3:
                terminated = vals[2]
            else:
                terminated = False
            if use_incident_voltage and self.solution_type == "Terminal":
                setting.append(["Name:=", key, "Terminated:=", terminated, "Magnitude:=", power, "Phase:=", phase])
            else:
                setting.append(["Name:=", key, "Magnitude:=", power, "Phase:=", phase])
        argument = []
        if self.solution_type == "Terminal":
            argument.extend(["UseIncidentVoltage:=", use_incident_voltage])

        argument.extend(
            [
                "IncludePortPostProcessing:=",
                include_port_post_processing,
                "SpecifySystemPower:=",
                True if max_available_power else False,
            ]
        )

        if max_available_power:
            argument.append("Incident Power:=")
            argument.append(max_available_power)

        args = [argument]
        args.extend(setting)
        for arg in args:
            self.osolution.EditSources(arg)
        return True

    @pyaedt_function_handler()
    def edit_source(self, portandmode=None, powerin="1W", phase="0deg"):
        """Set up the power loaded for HFSS postprocessing.

        Parameters
        ----------
        portandmode : str, optional
            Port name and mode. For example, ``"Port1:1"``.
            The port name must be defined if the solution type is other than Eigenmodal. This parameter
            is ignored if the solution type is Eigenmodal.
        powerin : str, optional
            Power in watts (W) or the project variable to put as stored energy in the project.
            The default is ``"1W"``.
        phase : str, optional
            Phase of the excitation. The default is ``"0deg"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oModule.EditSources

        Examples
        --------

        Create a circle sheet and use it to create a wave port.
        Set up the thermal power for this wave port.

        >>> sheet = hfss.modeler.create_circle(hfss.PLANE.YZ,
        ...                                    [-20, 0, 0], 10,
        ...                                    name="sheet_for_source")
        >>> hfss.solution_type = "Modal"
        >>> wave_port = hfss.create_wave_port_from_sheet(sheet, 5, hfss.AxisDir.XNeg, 40,
        ...                                              2, "SheetWavePort", True)
        >>> hfss.edit_source("SheetWavePort" + ":1", "10W")
        pyaedt INFO: Setting up power to "SheetWavePort:1" = 10W
        True

        """

        if self.solution_type != "Eigenmode":
            if portandmode is None:
                self.logger.error("Port and mode must be defined for solution type {}".format(self.solution_type))
                return False
            self.logger.info('Setting up power to "{}" = {}'.format(portandmode, powerin))
            self.osolution.EditSources(
                [
                    ["IncludePortPostProcessing:=", True, "SpecifySystemPower:=", False],
                    ["Name:=", portandmode, "Magnitude:=", powerin, "Phase:=", phase],
                ]
            )
        else:
            self.logger.info("Setting up power to Eigenmode = {}".format(powerin))
            self.osolution.EditSources(
                [["FieldType:=", "EigenStoredEnergy"], ["Name:=", "Modes", "Magnitudes:=", [powerin]]]
            )
        return True

    @pyaedt_function_handler()
    def edit_source_from_file(
        self,
        portandmode,
        file_name,
        is_time_domain=True,
        x_scale=1,
        y_scale=1,
        impedance=50,
        data_format="Power",
        encoding="utf-8",
    ):
        """Edit a source from file data.
        File data is a csv containing either frequency data or time domain data that will be converted through FFT.

        Parameters
        ----------
        portandmode : str
            Port name and mode. For example, ``"Port1:1"``.
            The port name must be defined if the solution type is other than Eigenmodal.
        file_name : str
            Full name of the input file.
        is_time_domain : bool, optional
            Either if the input data is Time based or Frequency Based. Frequency based data are Mag/Phase (deg).
        x_scale : float, optional
            Scaling factor for x axis.
        y_scale : float, optional
            Scaling factor for y axis.
        impedance : float, optional
            Excitation impedance. Default is `50`.
        data_format : str, optional
            Either `"Power"`, `"Current"` or `"Voltage"`.
        encoding : str, optional
            Csv file encoding.


        Returns
        -------
        bool
        """
        if self.solution_type == "Modal":
            out = "Power"
        else:
            out = "Voltage"
        freq, mag, phase = parse_excitation_file(
            file_name=file_name,
            is_time_domain=is_time_domain,
            x_scale=x_scale,
            y_scale=y_scale,
            impedance=impedance,
            data_format=data_format,
            encoding=encoding,
            out_mag=out,
        )
        ds_name_mag = "ds_" + portandmode.replace(":", "_mode_") + "_Mag"
        ds_name_phase = "ds_" + portandmode.replace(":", "_mode_") + "_Angle"
        if self.dataset_exists(ds_name_mag, False):
            self.design_datasets[ds_name_mag].x = freq
            self.design_datasets[ds_name_mag].y = mag
            self.design_datasets[ds_name_mag].update()
        else:
            self.create_dataset1d_design(ds_name_mag, freq, mag, xunit="Hz")
        if self.dataset_exists(ds_name_phase, False):
            self.design_datasets[ds_name_phase].x = freq
            self.design_datasets[ds_name_phase].y = phase
            self.design_datasets[ds_name_phase].update()

        else:
            self.create_dataset1d_design(ds_name_phase, freq, phase, xunit="Hz", yunit="deg")
        self.osolution.EditSources(
            [
                ["IncludePortPostProcessing:=", True, "SpecifySystemPower:=", False],
                [
                    "Name:=",
                    portandmode,
                    "Magnitude:=",
                    "pwl({}, Freq)".format(ds_name_mag),
                    "Phase:=",
                    "pwl({}, Freq)".format(ds_name_phase),
                ],
            ]
        )
        self.logger.info("Source Excitation updated with Dataset.")
        return True

    @pyaedt_function_handler()
    def thicken_port_sheets(self, inputlist, value, internalExtr=True, internalvalue=1):
        """Create thickened sheets over a list of input port sheets.

        This method is built to work with the output of ``modeler.find_port_faces``.

        Parameters
        ----------
        inputlist : list
            List of the sheets to thicken.
        value :
            Value in millimeters for thickening the faces.
        internalExtr : bool, optional
            Whether to extrude the sheets internally (vgoing into the model).
            The default is ``True``.
        internalvalue : optional
            Value in millimeters for thickening the sheets internally if ``internalExtr=True``.
            The default is ``1``.

        Returns
        -------
        Dict
            For each input sheet, returns the port IDs where thickened sheets were created
            if the name contains the word "Vacuum".

        References
        ----------

        >>> oEditor.ThickenSheet

        Examples
        --------

        Create a circle sheet and use it to create a wave port.
        Set the thickness of this circle sheet to ``"2 mm"``.

        >>> sheet_for_thickness = hfss.modeler.create_circle(hfss.PLANE.YZ,
        ...                                                  [60, 60, 60], 10,
        ...                                                  name="SheetForThickness")
        >>> port_for_thickness = hfss.create_wave_port_from_sheet(sheet_for_thickness, 5, hfss.AxisDir.XNeg,
        ...                                                       40, 2, "WavePortForThickness", True)
        >>> hfss.thicken_port_sheets(["SheetForThickness"], 2)
        pyaedt INFO: done
        {}

        """

        tol = 1e-6
        ports_ID = {}
        aedt_bounding_box = self.modeler.get_model_bounding_box()
        aedt_bounding_dim = self.modeler.get_bounding_dimension()
        directions = {}
        for el in inputlist:
            objID = self.modeler.oeditor.GetFaceIDs(el)
            faceCenter = self.modeler.oeditor.GetFaceCenter(int(objID[0]))
            directionfound = False
            l = min(aedt_bounding_dim) / 2
            while not directionfound:
                self.modeler.oeditor.ThickenSheet(
                    ["NAME:Selections", "Selections:=", el, "NewPartsModelFlag:=", "Model"],
                    ["NAME:SheetThickenParameters", "Thickness:=", str(l) + "mm", "BothSides:=", False],
                )
                # aedt_bounding_box2 = self.oeditor.GetModelBoundingBox()
                aedt_bounding_box2 = self.modeler.get_model_bounding_box()
                self._odesign.Undo()
                if aedt_bounding_box != aedt_bounding_box2:
                    directions[el] = "External"
                    directionfound = True
                self.modeler.oeditor.ThickenSheet(
                    ["NAME:Selections", "Selections:=", el, "NewPartsModelFlag:=", "Model"],
                    ["NAME:SheetThickenParameters", "Thickness:=", "-" + str(l) + "mm", "BothSides:=", False],
                )
                # aedt_bounding_box2 = self.oeditor.GetModelBoundingBox()
                aedt_bounding_box2 = self.modeler.get_model_bounding_box()

                self._odesign.Undo()

                if aedt_bounding_box != aedt_bounding_box2:
                    directions[el] = "Internal"
                    directionfound = True
                else:
                    l = l + min(aedt_bounding_dim) / 2
        for el in inputlist:
            objID = self.modeler.oeditor.GetFaceIDs(el)
            maxarea = 0
            for f in objID:
                faceArea = self.modeler.get_face_area(int(f))
                if faceArea > maxarea:
                    maxarea = faceArea
                    faceCenter = self.modeler.oeditor.GetFaceCenter(int(f))
            if directions[el] == "Internal":
                self.modeler.oeditor.ThickenSheet(
                    ["NAME:Selections", "Selections:=", el, "NewPartsModelFlag:=", "Model"],
                    ["NAME:SheetThickenParameters", "Thickness:=", "-" + str(value) + "mm", "BothSides:=", False],
                )
            else:
                self.modeler.oeditor.ThickenSheet(
                    ["NAME:Selections", "Selections:=", el, "NewPartsModelFlag:=", "Model"],
                    ["NAME:SheetThickenParameters", "Thickness:=", str(value) + "mm", "BothSides:=", False],
                )
            if "Vacuum" in el:
                newfaces = self.modeler.oeditor.GetFaceIDs(el)
                for f in newfaces:
                    try:
                        fc2 = self.modeler.oeditor.GetFaceCenter(f)
                        fc2 = [float(i) for i in fc2]
                        fa2 = self.modeler.get_face_area(int(f))
                        faceoriginal = [float(i) for i in faceCenter]
                        # dist = mat.sqrt(sum([(a*a-b*b) for a,b in zip(faceCenter, fc2)]))
                        if abs(fa2 - maxarea) < tol**2 and (
                            abs(faceoriginal[2] - fc2[2]) > tol
                            or abs(faceoriginal[1] - fc2[1]) > tol
                            or abs(faceoriginal[0] - fc2[0]) > tol
                        ):
                            ports_ID[el] = int(f)

                        # if (abs(faceoriginal[0] - fc2[0]) < tol and abs(faceoriginal[1] - fc2[1]) < tol and abs(
                        #         faceoriginal[2] - fc2[2]) > tol) or (
                        #         abs(faceoriginal[0] - fc2[0]) < tol and abs(faceoriginal[1] - fc2[1]) > tol and abs(
                        #         faceoriginal[2] - fc2[2]) < tol) or (
                        #         abs(faceoriginal[0] - fc2[0]) > tol and abs(faceoriginal[1] - fc2[1]) < tol and abs(
                        #         faceoriginal[2] - fc2[2]) < tol):
                        #     ports_ID[el] = int(f)
                    except:
                        pass
            if internalExtr:
                objID2 = self.modeler.oeditor.GetFaceIDs(el)
                for fid in objID2:
                    try:
                        faceCenter2 = self.modeler.oeditor.GetFaceCenter(int(fid))
                        if faceCenter2 == faceCenter:
                            self.modeler.oeditor.MoveFaces(
                                ["NAME:Selections", "Selections:=", el, "NewPartsModelFlag:=", "Model"],
                                [
                                    "NAME:Parameters",
                                    [
                                        "NAME:MoveFacesParameters",
                                        "MoveAlongNormalFlag:=",
                                        True,
                                        "OffsetDistance:=",
                                        str(internalvalue) + "mm",
                                        "MoveVectorX:=",
                                        "0mm",
                                        "MoveVectorY:=",
                                        "0mm",
                                        "MoveVectorZ:=",
                                        "0mm",
                                        "FacesToMove:=",
                                        [int(fid)],
                                    ],
                                ],
                            )
                    except:
                        self.logger.info("done")
                        # self.modeler_oproject.ClearMessages()
        return ports_ID

    @pyaedt_function_handler()
    def validate_full_design(self, dname=None, outputdir=None, ports=None):
        """Validate a design based on an expected value and save information to the log file.


        Parameters
        ----------
        dname : str,  optional
            Name of the design to validate. The default is ``None``, in which case
            the current design is used.
        outputdir : str, optional
            Directory to save the log file to. The default is ``None``,
            in which case the current project path is used.
        ports : int, optional
            Number of excitations (sum of modes) that is expected. The default is ``None``.

        Returns
        -------
        list of str
            List of all the validation information for later use.
        bool
            ``True`` if the validation was successful, ``False`` otherwise.

        References
        ----------

        >>> oDesign.ValidateDesign

        Examples
        --------

        Validate the current design and save the log file in the current project directory.

        >>> validation = hfss.validate_full_design()
        pyaedt INFO: Design Validation Checks
        >>> validation[1]
        False

        """

        self.logger.info("Design validation checks.")
        validation_ok = True
        val_list = []
        if not dname:
            dname = self.design_name
        if not outputdir:
            outputdir = self.working_directory
        pname = self.project_name
        validation_log_file = os.path.join(outputdir, pname + "_" + dname + "_validation.log")

        # Desktop Messages
        msg = "Desktop messages:"
        val_list.append(msg)
        temp_msg = list(self._desktop.GetMessages(pname, dname, 0))
        if temp_msg:
            temp2_msg = [i.strip("Project: " + pname + ", Design: " + dname + ", ").strip("\r\n") for i in temp_msg]
            val_list.extend(temp2_msg)

        # Run design validation and write out the lines to the log.
        temp_dir = tempfile.gettempdir()
        temp_val_file = os.path.join(temp_dir, "val_temp.log")
        simple_val_return = self.validate_simple(temp_val_file)
        if simple_val_return == 1:
            msg = "Design validation check PASSED."
        elif simple_val_return == 0:
            msg = "Design validation check ERROR."
            validation_ok = False
        val_list.append(msg)
        msg = "Design validation messages:"
        val_list.append(msg)
        if os.path.isfile(temp_val_file) or settings.remote_rpc_session:
            with open_file(temp_val_file, "r") as df:
                temp = df.read().splitlines()
                val_list.extend(temp)
            os.remove(temp_val_file)
        else:
            msg = "** No design validation file is found. **"
            self.logger.info(msg)
            val_list.append(msg)
        msg = "** End of design validation messages. **"
        val_list.append(msg)

        # Find the excitations and check or list them out
        msg = "Excitations check:"
        val_list.append(msg)
        if self.solution_type != "Eigenmode":
            detected_excitations = self.excitations
            if ports:
                if "Terminal" in self.solution_type:
                    # For each port, there is terminal and reference excitations.
                    ports_t = ports * 2
                else:
                    ports_t = ports
                if ports_t != len(detected_excitations):
                    msg = "** Port number error. Check the model. **"
                    self.logger.error(msg)
                    val_list.append(msg)
                    validation_ok = False
                else:
                    msg1 = "Solution type: " + str(self.solution_type)
                    msg2 = "Ports Requested: " + str(ports)
                    msg3 = "Defined excitations number: " + str(len(detected_excitations))
                    msg4 = "Defined excitations names: " + str(detected_excitations)
                    val_list.append(msg1)
                    val_list.append(msg2)
                    val_list.append(msg3)
                    val_list.append(msg4)
        else:
            msg = "Eigen model is detected. No excitatons are defined."
            self.logger.info(msg)
            val_list.append(msg)

        # Find the number of analysis setups and output the info.
        msg = "Analysis setup messages:"
        val_list.append(msg)
        setups = list(self.oanalysis.GetSetups())
        if setups:
            msg = "Detected setup and sweep: "
            val_list.append(msg)
            for setup in setups:
                msg = str(setup)
                val_list.append(msg)
                if self.solution_type.lower() != "eigenmode":
                    sweepsname = self.oanalysis.GetSweeps(setup)
                    if sweepsname:
                        for sw in sweepsname:
                            msg = " |__ " + sw
                            val_list.append(msg)
        else:
            msg = "No setup is detected."
            val_list.append(msg)

        with open_file(validation_log_file, "w") as f:
            for item in val_list:
                f.write("%s\n" % item)
        return val_list, validation_ok  # Return all the information in a list for later use.

    @pyaedt_function_handler()
    def create_scattering(
        self, plot_name="S Parameter Plot Nominal", sweep_name=None, port_names=None, port_excited=None, variations=None
    ):
        """Create a scattering report.

        Parameters
        ----------
        plot_name : str, optional
             Name of the plot. The default is ``"S Parameter Plot Nominal"``.
        sweep_name : str, optional
             Name of the sweep. The default is ``None``.
        port_names : list, optional
             List of port names. The default is ``None``.
        port_excited : list or str, optional
             The default is ``None``.
        variations : str, optional
             The default is ``None``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oModule.CreateReport

        Examples
        --------

        Create a scattering named ``"S Parameter Plot Nominal"`` using
        the default parameters.

        >>> hfss.create_scattering()
        True

        """

        solution_data = "Standard"
        if "Modal" in self.solution_type:
            solution_data = "Modal Solution Data"
        elif "Terminal" in self.solution_type:
            solution_data = "Terminal Solution Data"
        if not port_names:
            port_names = self.excitations
        if not port_excited:
            port_excited = port_names
        traces = ["dB(S(" + p + "," + q + "))" for p, q in zip(list(port_names), list(port_excited))]
        return self.post.create_report(
            traces, sweep_name, variations=variations, report_category=solution_data, plotname=plot_name
        )

    @pyaedt_function_handler()
    def create_qfactor_report(self, project_dir, outputlist, setupname, plotname, Xaxis="X"):
        """Export a CSV file of the EigenQ plot.

        Parameters
        ----------
        project_dir : str
            Directory to export the CSV file to.
        outputlist : list
            Output quantity, which in this case is the Q-factor.
        setupname : str
            Name of the setup to generate the report from.
        plotname : str
            Name of the plot.
        Xaxis : str, optional
            Value for the X axis. The default is ``"X"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oModule.CreateReport

        """
        npath = project_dir

        # Setup arguments list for createReport function
        args = [Xaxis + ":=", ["All"]]
        args2 = ["X Component:=", Xaxis, "Y Component:=", outputlist]

        self.post.post_oreport_setup.CreateReport(
            plotname, "Eigenmode Parameters", "Rectangular Plot", setupname + " : LastAdaptive", [], args, args2, []
        )
        return True

    @pyaedt_function_handler()
    def export_touchstone(
        self, solution_name=None, sweep_name=None, file_name=None, variations=None, variations_value=None
    ):
        """Export the Touchstone file to a local folder.

        Parameters
        ----------
        solution_name : str, optional
            Name of the solution that has been solved.
        sweep_name : str, optional
            Name of the sweep that has been solved.
        file_name : str, optional
            Full path and name for the Touchstone file.
            The default is ``None``, in which case the file is exported to the working directory.
        variations : list, optional
            List of all parameter variations. For example, ``["$AmbientTemp", "$PowerIn"]``.
            The default is ``None``.
        variations_value : list, optional
            List of all parameter variation values. For example, ``["22cel", "100"]``.
            The default is ``None``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        return self._export_touchstone(
            solution_name=solution_name,
            sweep_name=sweep_name,
            file_name=file_name,
            variations=variations,
            variations_value=variations_value,
        )

    @pyaedt_function_handler()
    def set_export_touchstone(self, activate, export_dir=""):
        """Set automatic export of the Touchstone file after simulation.

        Parameters
        ----------
        activate : bool
            Whether to export the Touchstone file after simulation finishes.
        export_dir : str, optional
            Directory to export the Touchstone file to. The default is ``""``,
            in which case the Touchstone file is exported to the working directory.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oDesign.SetDesignSettings
        """
        settings = []
        if activate:
            settings.append("NAME:Design Settings Data")
            settings.append("Export After Simulation:=")
            settings.append(True)
            settings.append("Export Dir:=")
            settings.append(export_dir)
        elif not activate:
            settings.append("NAME:Design Settings Data")
            settings.append("Export After Simulation:=")
            settings.append(False)
        self.odesign.SetDesignSettings(settings)
        return True

    @pyaedt_function_handler()
    def assign_radiation_boundary_to_objects(self, obj_names, boundary_name=""):
        """Assign a radiation boundary to one or more objects (usually airbox objects).

        Parameters
        ----------
        obj_names : str or list or int or :class:`pyaedt.modeler.object3d.Object3d`
            One or more object names or IDs.
        boundary_name : str, optional
            Name of the boundary. The default is ``""``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        References
        ----------

        >>> oModule.AssignRadiation

        Examples
        --------

        Create a box and assign a radiation boundary to it.

        >>> radiation_box = hfss.modeler.create_box([0, -200, -200], [200, 200, 200],
        ...                                         name="Radiation_box")
        >>> radiation = hfss.assign_radiation_boundary_to_objects("Radiation_box")
        >>> type(radiation)
        <class 'pyaedt.modules.Boundary.BoundaryObject'>

        """

        object_list = self.modeler.convert_to_selections(obj_names, return_list=True)
        if boundary_name:
            rad_name = boundary_name
        else:
            rad_name = generate_unique_name("Rad_")
        return self.create_boundary(self.BoundaryType.Radiation, object_list, rad_name)

    @pyaedt_function_handler()
    def assign_hybrid_region(self, obj_names, boundary_name="", hybrid_region="SBR+"):
        """Assign a hybrid region to one or more objects.

        Parameters
        ----------
        obj_names : str or list or int or :class:`pyaedt.modeler.object3d.Object3d`
            One or more object names or IDs.
        boundary_name : str, optional
            Name of the boundary. The default is ``""``.
        hybrid_region : str, optional
            Hybrid region to assign. Options are ``"SBR+"``, ``"IE"``, ``"PO"``. The default is `"SBR+"``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        References
        ----------

        >>> oModule.AssignHybridRegion

        Examples
        --------

        Create a box and assign a hybrid boundary to it.

        >>> box = hfss.modeler.create_box([0, -200, -200], [200, 200, 200],
        ...                                         name="Radiation_box")
        >>> sbr_box = hfss.assign_hybrid_region("Radiation_box")
        >>> type(sbr_box)
        <class 'pyaedt.modules.Boundary.BoundaryObject'>

        """

        object_list = self.modeler.convert_to_selections(obj_names, return_list=True)
        if boundary_name:
            region_name = boundary_name
        else:
            region_name = generate_unique_name("Hybrid_")
        bound = self.create_boundary(self.BoundaryType.Hybrid, object_list, region_name)
        if hybrid_region != "SBR+":
            bound.props["Type"] = hybrid_region
        return bound

    @pyaedt_function_handler()
    def assign_radiation_boundary_to_faces(self, faces_id, boundary_name=""):
        """Assign a radiation boundary to one or more faces.

        Parameters
        ----------
        faces_id :
            Face ID to assign the boundary condition to.
        boundary_name : str, optional
            Name of the boundary. The default is ``""``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        References
        ----------

        >>> oModule.AssignRadiation

        Examples
        --------

        Create a box. Select the faces of this box and assign a radiation
        boundary to them.

        >>> radiation_box = hfss.modeler.create_box([0 , -100, 0], [200, 200, 200],
        ...                                         name="RadiationForFaces")
        >>> ids = [i.id for i in hfss.modeler["RadiationForFaces"].faces]
        >>> radiation = hfss.assign_radiation_boundary_to_faces(ids)
        >>> type(radiation)
        <class 'pyaedt.modules.Boundary.BoundaryObject'>

        """
        faces_list = self.modeler.convert_to_selections(faces_id, True)
        if boundary_name:
            rad_name = boundary_name
        else:
            rad_name = generate_unique_name("Rad_")
        return self.create_boundary(self.BoundaryType.Radiation, faces_list, rad_name)

    @pyaedt_function_handler()
    def _create_sbr_doppler_setup(
        self,
        setup_type,
        time_var,
        center_freq,
        resolution,
        period,
        velocity_resolution,
        min_velocity,
        max_velocity,
        ray_density_per_wavelength,
        max_bounces,
        setup_name,
        include_coupling_effects=False,
        doppler_ad_sampling_rate=20,
    ):
        setup1 = self.create_setup(setup_name, 4)
        setup1.auto_update = False
        setup1.props["IsSbrRangeDoppler"] = True
        del setup1.props["PTDUTDSimulationSettings"]
        del setup1.props["ComputeFarFields"]
        del setup1.props["Sweeps"]
        if setup_type == "ChirpIQ":
            setup1.props["SbrRangeDopplerWaveformType"] = "ChirpSeqFmcw"
            setup1.props["ChannelConfiguration"] = "IQChannels"
        elif setup_type == "ChirpI":
            setup1.props["SbrRangeDopplerWaveformType"] = "ChirpSeqFmcw"
            setup1.props["ChannelConfiguration"] = "IChannelOnly"
        else:
            setup1.props["SbrRangeDopplerWaveformType"] = setup_type
        setup1.props["SbrRangeDopplerTimeVariable"] = time_var
        setup1.props["SbrRangeDopplerCenterFreq"] = self.modeler._arg_with_dim(center_freq, "GHz")
        setup1.props["SbrRangeDopplerRangeResolution"] = self.modeler._arg_with_dim(resolution, "meter")
        setup1.props["SbrRangeDopplerRangePeriod"] = self.modeler._arg_with_dim(period, "meter")
        setup1.props["SbrRangeDopplerVelocityResolution"] = self.modeler._arg_with_dim(velocity_resolution, "m_per_sec")
        setup1.props["SbrRangeDopplerVelocityMin"] = self.modeler._arg_with_dim(min_velocity, "m_per_sec")
        setup1.props["SbrRangeDopplerVelocityMax"] = self.modeler._arg_with_dim(max_velocity, "m_per_sec")
        setup1.props["DopplerRayDensityPerWavelength"] = ray_density_per_wavelength
        setup1.props["MaxNumberOfBounces"] = max_bounces
        if setup_type != "PulseDoppler":
            setup1.props["IncludeRangeVelocityCouplingEffect"] = include_coupling_effects
            setup1.props["SbrRangeDopplerA/DSamplingRate"] = self.modeler._arg_with_dim(doppler_ad_sampling_rate, "MHz")
        setup1.update()
        setup1.auto_update = True
        return setup1

    @pyaedt_function_handler()
    def _create_sbr_doppler_sweep(self, setupname, time_var, tstart, tstop, tsweep, parametric_name):
        time_start = self.modeler._arg_with_dim(tstart, "s")
        time_sweep = self.modeler._arg_with_dim(tsweep, "s")
        time_stop = self.modeler._arg_with_dim(tstop, "s")
        sweep_range = "LIN {} {} {}".format(time_start, time_stop, time_sweep)
        return self.parametrics.add(
            time_var, tstart, time_stop, tsweep, "LinearStep", setupname, parametricname=parametric_name
        )

    @pyaedt_function_handler()
    def create_sbr_chirp_i_doppler_setup(
        self,
        time_var=None,
        sweep_time_duration=0,
        center_freq=76.5,
        resolution=1,
        period=200,
        velocity_resolution=0.4,
        min_velocity=-20,
        max_velocity=20,
        ray_density_per_wavelength=0.2,
        max_bounces=5,
        include_coupling_effects=False,
        doppler_ad_sampling_rate=20,
        setup_name=None,
    ):
        """Create an SBR+ Chirp I Setup.

        Parameters
        ----------
        time_var : str, optional
            Name of the time variable. The default is ``None``, in which case
            a search for the first time variable is performed.
        sweep_time_duration : float, optional
            Duration for the sweep time. The default is ``0.`` If a value greater
            than ``0`` is specified, a parametric sweep is created.
        center_freq : float, optional
            Center frequency in gigahertz (GHz). The default is ``76.5``.
        resolution : float, optional
            Doppler resolution in meters (m). The default is ``1``.
        period : float, optional
            Period of analysis in meters (m). The default is ``200``.
        velocity_resolution : float, optional
            Doppler velocity resolution in meters per second (m/s). The default is ``0.4``.
        min_velocity : str, optional
            Minimum Doppler velocity in meters per second (m/s). The default is ``-20``.
        max_velocity : str, optional
            Maximum Doppler velocity in meters per second (m/s). The default is ``20``.
        ray_density_per_wavelength : float, optional
            Doppler ray density per wavelength. The default is ``0.2``.
        max_bounces : int, optional
            Maximum number of bounces. The default is ``5``.
        include_coupling_effects : float, optional
            Whether to include coupling effects. The default is ``False``.
        doppler_ad_sampling_rate : float, optional
            Doppler AD sampling rate to use if ``include_coupling_effects``
            is ``True``. The default is ``20``.
        setup_name : str, optional
            Name of the setup. The default is ``None``, in which case the active setup is used.

        Returns
        -------
        tuple
            The tuple contains: (:class:`pyaedt.modules.SolveSetup.Setup`,
            :class:`pyaedt.modules.DesignXPloration.ParametericsSetups.Optimetrics`).

        References
        ----------

        >>> oModule.InsertSetup

        """
        if self.solution_type != "SBR+":
            self.logger.error("Method applies only to the SBR+ solution.")
            return False, False
        if not setup_name:
            setup_name = generate_unique_name("ChirpI")
            parametric_name = generate_unique_name("PulseSweep")
        else:
            parametric_name = generate_unique_name(setup_name)

        if not time_var:
            for var_name, var in self.variable_manager.independent_variables.items():
                if var.unit_system == "Time":
                    time_var = var_name
                    break
            if not time_var:
                self.logger.error(
                    "No time variable is found. Set up or explicitly assign a time variable to the method."
                )
                raise ValueError("No time variable is found.")
        setup = self._create_sbr_doppler_setup(
            "ChirpI",
            time_var=time_var,
            center_freq=center_freq,
            resolution=resolution,
            period=period,
            velocity_resolution=velocity_resolution,
            min_velocity=min_velocity,
            max_velocity=max_velocity,
            ray_density_per_wavelength=ray_density_per_wavelength,
            max_bounces=max_bounces,
            include_coupling_effects=include_coupling_effects,
            doppler_ad_sampling_rate=doppler_ad_sampling_rate,
            setup_name=setup_name,
        )
        if sweep_time_duration > 0:
            sweeptime = math.ceil(300000000 / (2 * center_freq * 1000000000 * velocity_resolution) * 1000) / 1000
            sweep = self._create_sbr_doppler_sweep(
                setup.name, time_var, 0, sweep_time_duration, sweeptime, parametric_name
            )
            return setup, sweep
        return setup, False

    @pyaedt_function_handler()
    def create_sbr_chirp_iq_doppler_setup(
        self,
        time_var=None,
        sweep_time_duration=0,
        center_freq=76.5,
        resolution=1,
        period=200,
        velocity_resolution=0.4,
        min_velocity=-20,
        max_velocity=20,
        ray_density_per_wavelength=0.2,
        max_bounces=5,
        include_coupling_effects=False,
        doppler_ad_sampling_rate=20,
        setup_name=None,
    ):
        """Create an SBR+ Chirp IQ Setup.

        Parameters
        ----------
        time_var : str, optional
            Name of the time variable. The default is ``None``, in which case
            a search for the first time variable is performed.
        sweep_time_duration : float, optional
            Duration of the sweep time. The default is ``0``. If a value greater
            than ``0`` is specified, a parametric sweep is created.
        center_freq : float, optional
            Center frequency in gighertz (GHz). The default is ``76.5``.
        resolution : float, optional
            Doppler resolution in meters (m). The default is ``1``.
        period : float, optional
            Period of analysis in meters (m). The default is ``200``.
        velocity_resolution : float, optional
            Doppler velocity resolution in meters per second (m/s). The default is ``0.4``.
        min_velocity : str, optional
            Minimum Doppler velocity in meters per second (m/s). The default is ``-20``.
        max_velocity : str, optional
            Maximum Doppler velocity in meters per second (m/s). The default is ``20``.
        ray_density_per_wavelength : float, optional
            Doppler ray density per wavelength. The default is ``0.2``.
        max_bounces : int, optional
            Maximum number of bounces. The default is ``5``.
        include_coupling_effects : float, optional
            Whether to include coupling effects. The default is ``False``.
        doppler_ad_sampling_rate : float, optional
            Doppler AD sampling rate to use if ``include_coupling_effects`` is
            ``True``. The default is ``20``.
        setup_name : str, optional
            Name of the setup. The default is ``None``, in which case the active
            setup is used.

        Returns
        -------
        tuple
            The tuple contains: (:class:`pyaedt.modules.SolveSetup.Setup`,
            :class:`pyaedt.modules.DesignXPloration.ParametericsSetups.Optimetrics`).

        References
        ----------

        >>> oModule.InsertSetup
        """
        if self.solution_type != "SBR+":
            self.logger.error("Method applies only to the SBR+ solution.")
            return False, False
        if not setup_name:
            setup_name = generate_unique_name("ChirpIQ")
            parametric_name = generate_unique_name("PulseSweep")
        else:
            parametric_name = generate_unique_name(setup_name)
        if not time_var:
            for var_name, var in self.variable_manager.independent_variables.items():
                if var.unit_system == "Time":
                    time_var = var_name
                    break
            if not time_var:
                raise ValueError("No Time Variable Found")
        setup = self._create_sbr_doppler_setup(
            "ChirpIQ",
            time_var=time_var,
            center_freq=center_freq,
            resolution=resolution,
            period=period,
            velocity_resolution=velocity_resolution,
            min_velocity=min_velocity,
            max_velocity=max_velocity,
            ray_density_per_wavelength=ray_density_per_wavelength,
            max_bounces=max_bounces,
            include_coupling_effects=include_coupling_effects,
            doppler_ad_sampling_rate=doppler_ad_sampling_rate,
            setup_name=setup_name,
        )
        if sweep_time_duration > 0:
            sweeptime = math.ceil(300000000 / (2 * center_freq * 1000000000 * velocity_resolution) * 1000) / 1000
            sweep = self._create_sbr_doppler_sweep(
                setup.name, time_var, 0, sweep_time_duration, sweeptime, parametric_name
            )
            return setup, sweep
        return setup, False

    @pyaedt_function_handler()
    def create_sbr_pulse_doppler_setup(
        self,
        time_var=None,
        sweep_time_duration=0,
        center_freq=76.5,
        resolution=1,
        period=200,
        velocity_resolution=0.4,
        min_velocity=-20,
        max_velocity=20,
        ray_density_per_wavelength=0.2,
        max_bounces=5,
        setup_name=None,
    ):
        """Create an SBR+ pulse Doppler setup.

        Parameters
        ----------
        time_var : str, optional
            Name of the time variable. The default is ``None``, in which case
            a search for the first time variable is performed.
        sweep_time_duration : float, optional
            Duration of the sweep time. The default is ``0``. If a value greater
            than ``0`` is specified, a parametric sweep is created.
        center_freq : float, optional
            Center frequency in gigahertz (GHz). The default is ``76.5``.
        resolution : float, optional
            Doppler resolution in meters (m). The default is ``1``.
        period : float, optional
            Period of analysis in meters (m). The default is ``200``.
        velocity_resolution : float, optional
            Doppler velocity resolution in meters per second (m/s).
            The default is ``0.4``.
        min_velocity : str, optional
            Minimum Doppler velocity in meters per second (m/s). The default
            is ``-20``.
        max_velocity : str, optional
            Maximum Doppler velocity in meters per second (m/s). The default
            is ``20``.
        ray_density_per_wavelength : float, optional
            Doppler ray density per wavelength. The default is ``0.2``.
        max_bounces : int, optional
            Maximum number of bounces. The default is ``5``.
        setup_name : str, optional
            Name of the setup. The default is ``None``, in which case the active
            setup is used.

        Returns
        -------
        tuple
            The tuple contains: (:class:`pyaedt.modules.SolveSetup.Setup`,
            :class:`pyaedt.modules.DesignXPloration.ParametericsSetups.Optimetrics`).

        References
        ----------

        >>> oModule.InsertSetup
        """
        if self.solution_type != "SBR+":
            self.logger.error("Method Applies only to SBR+ Solution.")
            return False, False
        if not setup_name:
            setup_name = generate_unique_name("PulseSetup")
            parametric_name = generate_unique_name("PulseSweep")
        else:
            parametric_name = generate_unique_name(setup_name)

        if not time_var:
            for var_name, var in self.variable_manager.independent_variables.items():
                if var.unit_system == "Time":
                    time_var = var_name
                    break
            if not time_var:
                raise ValueError("No Time Variable Found")
        setup = self._create_sbr_doppler_setup(
            "PulseDoppler",
            time_var=time_var,
            center_freq=center_freq,
            resolution=resolution,
            period=period,
            velocity_resolution=velocity_resolution,
            min_velocity=min_velocity,
            max_velocity=max_velocity,
            ray_density_per_wavelength=ray_density_per_wavelength,
            max_bounces=max_bounces,
            setup_name=setup_name,
        )
        if sweep_time_duration > 0:
            sweeptime = math.ceil(300000000 / (2 * center_freq * 1000000000 * velocity_resolution) * 1000) / 1000
            sweep = self._create_sbr_doppler_sweep(
                setup.name, time_var, 0, sweep_time_duration, sweeptime, parametric_name
            )
            return setup, sweep
        return setup, False

    @pyaedt_function_handler()
    def create_sbr_radar_from_json(
        self, radar_file, radar_name, offset=[0, 0, 0], speed=0.0, use_relative_cs=False, relative_cs_name=None
    ):
        """Create an SBR+ radar from a JSON file.

        Example of input JSON file:

          .. code-block:: json

            {
                "name": "Example_1Tx_1Rx",
                "version": 1,
                "number_tx":"1",
                "number_rx":"1",
                "units":"mm",
                "antennas": {
                    "tx1": {
                        "antenna_type":"parametric",
                        "mode":"tx",
                        "offset":["0" ,"0" ,"0"],
                        "rotation_axis":null,
                        "rotation":null,
                        "beamwidth_elevation":"10deg",
                        "beamwidth_azimuth":"60deg",
                        "polarization":"Vertical"
                        },
                    "rx1": {
                        "antenna_type":"parametric",
                        "mode":"rx",
                        "offset":["0" ,"1.8" ,"0"],
                        "rotation_axis":null,
                        "rotation":null,
                        "beamwidth_elevation":"10deg",
                        "beamwidth_azimuth":"60deg",
                        "polarization":"Vertical"
                        }
                }
            }

        Parameters
        ----------
        radar_file : str
            Path to the directory with the radar file.
        radar_name : str
            Name of the radar file.
        offset : list, optional
            Offset relative to the global coordinate system.
        speed : float, optional
            Radar movement speed relative to the global coordinate system if greater than ``0``.
        use_relative_cs : bool, optional
            Whether to use the relative coordinate system. The default is ``False``.
        relative_cs_name : str
            Name of the relative coordinate system to link the radar to.
            The default is ``None``, in which case the global coordinate system is used.

        Returns
        -------
        :class:`pyaedt.modeler.actors.Radar`
            Radar  class object.

        References
        ----------
        AEDT API Commands.

        >>> oEditor.CreateRelativeCS
        >>> oModule.SetSBRTxRxSettings
        >>> oEditor.CreateGroup
        """
        self.modeler._initialize_multipart()
        if self.solution_type != "SBR+":
            self.logger.error("Method Applies only to SBR+ Solution.")
            return False
        use_motion = abs(speed) > 0.0
        r = Radar(
            radar_file,
            name=radar_name,
            motion=use_motion,
            offset=offset,
            speed=speed,
            use_relative_cs=(use_relative_cs or use_motion),
            relative_cs_name=relative_cs_name,
        )
        r.insert(self, abs(speed) > 0)
        return r

    @pyaedt_function_handler()
    def insert_infinite_sphere(
        self,
        definition=INFINITE_SPHERE_TYPE.ThetaPhi,
        x_start=0,
        x_stop=180,
        x_step=10,
        y_start=0,
        y_stop=180,
        y_step=10,
        units="deg",
        custom_radiation_faces=None,
        custom_coordinate_system=None,
        use_slant_polarization=False,
        polarization_angle=45,
        name=None,
    ):
        """Create an infinite sphere.

        .. note::
           This method is not supported by HFSS ``EigenMode`` and ``CharacteristicMode`` solution types.

        Parameters
        ----------
        definition : str
            Coordinate definition type. The default is ``"Theta-Phi"``.
            It can be a ``pyaedt.generic.constants.INFINITE_SPHERE_TYPE`` enumerator value.
        x_start : float, str, optional
            First angle start value. The default is ``0``.
        x_stop : float, str, optional
            First angle stop value. The default is ``180``.
        x_step : float, str, optional
            First angle step value. The default is ``10``.
        y_start : float, str, optional
            Second angle start value. The default is ``0``.
        y_stop : float, str, optional
            Second angle stop value. The default is ``180``.
        y_step : float, str, optional
            Second angle step value. The default is ``10``.
        units : str
            Angle units. The default is ``"deg"``.
        custom_radiation_faces : str, optional
            List of radiation faces to use for far field computation. The default is ``None``.
        custom_coordinate_system : str, optional
            Local coordinate system to use for far field computation. The default is
            ``None``.
        use_slant_polarization : bool, optional
            Whether to use slant polarization. The default is ``False``.
        polarization_angle : float, str, optional
            Slant angle value. The default is ``45``.
        name : str, optional
            Name of the sphere. The default is ``None``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.FarFieldSetup`
        """
        if not self.oradfield:
            self.logger.error("Radiation Field not available in this solution.")
        if not name:
            name = generate_unique_name("Infinite")

        props = OrderedDict({"UseCustomRadiationSurface": custom_radiation_faces is not None})
        if custom_radiation_faces:
            props["CustomRadiationSurface"] = custom_radiation_faces
        else:
            props["CustomRadiationSurface"] = ""
        props["CSDefinition"] = definition
        if use_slant_polarization:
            props["Polarization"] = "Slant"
        else:
            props["Polarization"] = "Linear"
        props["SlantAngle"] = self.modeler._arg_with_dim(polarization_angle, units)

        if definition == "Theta-Phi":
            defs = ["ThetaStart", "ThetaStop", "ThetaStep", "PhiStart", "PhiStop", "PhiStep"]
        elif definition == "El Over Az":
            defs = ["AzimuthStart", "AzimuthStop", "AzimuthStep", "ElevationStart", "ElevationStop", "ElevationStep"]
        else:
            defs = ["ElevationStart", "ElevationStop", "ElevationStep", "AzimuthStart", "AzimuthStop", "AzimuthStep"]
        props[defs[0]] = self.modeler._arg_with_dim(x_start, units)
        props[defs[1]] = self.modeler._arg_with_dim(x_stop, units)
        props[defs[2]] = self.modeler._arg_with_dim(x_step, units)
        props[defs[3]] = self.modeler._arg_with_dim(y_start, units)
        props[defs[4]] = self.modeler._arg_with_dim(y_stop, units)
        props[defs[5]] = self.modeler._arg_with_dim(y_step, units)
        props["UseLocalCS"] = custom_coordinate_system is not None
        if custom_coordinate_system:
            props["CoordSystem"] = custom_coordinate_system
        else:
            props["CoordSystem"] = ""
        bound = FarFieldSetup(self, name, props, "FarFieldSphere", units)
        if bound.create():
            self.field_setups.append(bound)
            return bound
        return False

    @pyaedt_function_handler()
    def insert_near_field_sphere(
        self,
        radius=20,
        radius_units="mm",
        x_start=0,
        x_stop=180,
        x_step=10,
        y_start=0,
        y_stop=180,
        y_step=10,
        angle_units="deg",
        custom_radiation_faces=None,
        custom_coordinate_system=None,
        name=None,
    ):
        """Create a near field sphere.

        .. note::
           This method is not supported by HFSS ``EigenMode`` and ``CharacteristicMode`` solution types.

        Parameters
        ----------
        radius : float, str, optional
            Sphere radius. The default is ``20``.
        radius_units : str
            Radius units. The default is ``"mm"``.
        x_start : float, str, optional
            First angle start value. The default is ``0``.
        x_stop : float, str, optional
            First angle stop value. The default is ``180``.
        x_step : float, str, optional
            First angle step value. The default is ``10``.
        y_start : float, str, optional
            Second angle start value. The default is ``0``.
        y_stop : float, str, optional
            Second angle stop value. The default is ``180``.
        y_step : float, str, optional
            Second angle step value. The default is ``10``.
        angle_units : str
            Angle units. The default is ``"deg"``.
        custom_radiation_faces : str, optional
            List of radiation faces to use for far field computation. The default is ``None``.
        custom_coordinate_system : str, optional
            Local coordinate system to use for far field computation. The default is ``None``.
        name : str, optional
            Name of the sphere. The default is ``None``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.NearFieldSetup`
        """
        if not self.oradfield:
            self.logger.error("Radiation Field not available in this solution.")
        if not name:
            name = generate_unique_name("Sphere")

        props = OrderedDict({"UseCustomRadiationSurface": custom_radiation_faces is not None})
        if custom_radiation_faces:
            props["CustomRadiationSurface"] = custom_radiation_faces
        else:
            props["CustomRadiationSurface"] = ""

        props["Radius"] = self.modeler._arg_with_dim(radius, radius_units)

        defs = ["ThetaStart", "ThetaStop", "ThetaStep", "PhiStart", "PhiStop", "PhiStep"]
        props[defs[0]] = self.modeler._arg_with_dim(x_start, angle_units)
        props[defs[1]] = self.modeler._arg_with_dim(x_stop, angle_units)
        props[defs[2]] = self.modeler._arg_with_dim(x_step, angle_units)
        props[defs[3]] = self.modeler._arg_with_dim(y_start, angle_units)
        props[defs[4]] = self.modeler._arg_with_dim(y_stop, angle_units)
        props[defs[5]] = self.modeler._arg_with_dim(y_step, angle_units)
        props["UseLocalCS"] = custom_coordinate_system is not None
        if custom_coordinate_system:
            props["CoordSystem"] = custom_coordinate_system
        else:
            props["CoordSystem"] = ""
        bound = NearFieldSetup(self, name, props, "NearFieldSphere")
        if bound.create():
            self.field_setups.append(bound)
            return bound
        return False

    @pyaedt_function_handler()
    def insert_near_field_box(
        self,
        u_length=20,
        u_samples=21,
        v_length=20,
        v_samples=21,
        w_length=20,
        w_samples=21,
        units="mm",
        custom_radiation_faces=None,
        custom_coordinate_system=None,
        name=None,
    ):
        """Create a near field box.

        .. note::
           This method is not supported by HFSS ``EigenMode`` and ``CharacteristicMode`` solution types.

        Parameters
        ----------
        u_length : float, str, optional
            U axis length. The default is ``20``.
        u_samples : float, str, optional
            U axis samples. The default is ``21``.
        v_length : float, str, optional
            V axis length. The default is ``20``.
        v_samples : float, str, optional
            V axis samples. The default is ``21``.
        w_length : float, str, optional
            W axis length. The default is ``20``.
        w_samples : float, str, optional
            W axis samples. The default is ``21``.
        units : str
            Length units. The default is ``"mm"``.
        custom_radiation_faces : str, optional
            List of radiation faces to use for far field computation. The default is ``None``.
        custom_coordinate_system : str, optional
            Local coordinate system to use for far field computation. The default is ``None``.
        name : str, optional
            Name of the sphere. The default is ``None``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.NearFieldSetup`
        """
        if not self.oradfield:
            self.logger.error("Radiation Field not available in this solution.")
        if not name:
            name = generate_unique_name("Box")

        props = OrderedDict({"UseCustomRadiationSurface": custom_radiation_faces is not None})
        if custom_radiation_faces:
            props["CustomRadiationSurface"] = custom_radiation_faces
        else:
            props["CustomRadiationSurface"] = ""

        defs = ["U Size", "V Size", "W Size", "U Samples", "V Samples", "W Samples"]
        props[defs[0]] = self.modeler._arg_with_dim(u_length, units)
        props[defs[1]] = self.modeler._arg_with_dim(v_length, units)
        props[defs[2]] = self.modeler._arg_with_dim(w_length, units)
        props[defs[3]] = self.modeler._arg_with_dim(u_samples, units)
        props[defs[4]] = self.modeler._arg_with_dim(v_samples, units)
        props[defs[5]] = self.modeler._arg_with_dim(w_samples, units)

        if custom_coordinate_system:
            props["CoordSystem"] = custom_coordinate_system
        else:
            props["CoordSystem"] = "Global"
        bound = NearFieldSetup(self, name, props, "NearFieldBox")
        if bound.create():
            self.field_setups.append(bound)
            return bound
        return False

    @pyaedt_function_handler()
    def insert_near_field_rectangle(
        self,
        u_length=20,
        u_samples=21,
        v_length=20,
        v_samples=21,
        units="mm",
        custom_radiation_faces=None,
        custom_coordinate_system=None,
        name=None,
    ):
        """Create a near field rectangle.

        .. note::
           This method is not supported by HFSS ``EigenMode`` and ``CharacteristicMode`` solution types.

        Parameters
        ----------
        u_length : float, str, optional
            U axis length. The default is ``20``.
        u_samples : float, str, optional
            U axis samples. The default is ``21``.
        v_length : float, str, optional
            V axis length. The default is ``20``.
        v_samples : float, str, optional
            V axis samples. The default is ``21``.
        units : str
            Length units. The default is ``"mm"``.
        custom_radiation_faces : str, optional
            List of radiation faces to use for far field computation. The default is ``None``.
        custom_coordinate_system : str, optional
            Local coordinate system to use for far field computation. The default is ``None``.
        name : str, optional
            Name of the sphere. The default is ``None``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.NearFieldSetup`
        """
        if not self.oradfield:
            self.logger.error("Radiation Field not available in this solution.")
        if not name:
            name = generate_unique_name("Rectangle")

        props = OrderedDict({"UseCustomRadiationSurface": custom_radiation_faces is not None})
        if custom_radiation_faces:
            props["CustomRadiationSurface"] = custom_radiation_faces
        else:
            props["CustomRadiationSurface"] = ""

        defs = ["Length", "Width", "LengthSamples", "WidthSamples"]
        props[defs[0]] = self.modeler._arg_with_dim(u_length, units)
        props[defs[1]] = self.modeler._arg_with_dim(v_length, units)
        props[defs[2]] = u_samples
        props[defs[3]] = v_samples

        if custom_coordinate_system:
            props["CoordSystem"] = custom_coordinate_system
        else:
            props["CoordSystem"] = "Global"
        bound = NearFieldSetup(self, name, props, "NearFieldRectangle")
        if bound.create():
            self.field_setups.append(bound)
            return bound
        return False

    @pyaedt_function_handler()
    def insert_near_field_line(
        self,
        line,
        points=1000,
        custom_radiation_faces=None,
        name=None,
    ):
        """Create a near field line.

        .. note::
           This method is not supported by HFSS ``EigenMode`` and ``CharacteristicMode`` solution types.

        Parameters
        ----------
        line : str
            Polyline name.
        points : float, str, optional
            Number of points. The default value is ``1000``.
        custom_radiation_faces : str, optional
            List of radiation faces to use for far field computation. The default is ``None``.
        name : str, optional
            Name of the sphere. The default is ``None``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.NearFieldSetup`
        """
        if not self.oradfield:
            self.logger.error("Radiation Field not available in this solution.")
        if not name:
            name = generate_unique_name("Line")

        props = OrderedDict({"UseCustomRadiationSurface": custom_radiation_faces is not None})
        if custom_radiation_faces:
            props["CustomRadiationSurface"] = custom_radiation_faces
        else:
            props["CustomRadiationSurface"] = ""

        props["NumPts"] = points
        props["Line"] = line

        bound = NearFieldSetup(self, name, props, "NearFieldLine")
        if bound.create():
            self.field_setups.append(bound)
            return bound
        return False

    @pyaedt_function_handler()
    def set_sbr_current_sources_options(self, conformance=False, thin_sources=False, power_fraction=0.95):
        """Set SBR+ setup options for the current source.

        Parameters
        ----------
        conformance : bool, optional
            Whether to enable current source conformance. The default is ``False``.
        thin_sources : bool, optional
            Whether to enable thin sources. The default is ``False``.
        power_fraction : float or str, optional
            Power fraction to use if ``thin_sources=True``. The default is ``0.95``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oModule.EditGlobalCurrentSourcesOption
        """
        if self.solution_type != "SBR+":
            self.logger.error("Method Applies only to SBR+ Solution.")
            return False
        current_conformance = "Disable"
        if conformance:
            current_conformance = "Enable"
        arg = [
            "NAME:CurrentSourceOption",
            "Current Source Conformance:=",
            current_conformance,
            "Thin Sources:=",
            thin_sources,
        ]
        if thin_sources:
            arg.append("Power Fraction:=")
            arg.append(str(power_fraction))
        self.oboundary.EditGlobalCurrentSourcesOption(arg)
        self.logger.info("SBR+ current source options correctly applied.")
        return True

    @pyaedt_function_handler()
    def set_differential_pair(
        self,
        positive_terminal,
        negative_terminal,
        common_name=None,
        diff_name=None,
        common_ref_z=25,
        diff_ref_z=100,
        active=True,
        matched=False,
    ):
        """Add a differential pair definition.

        Differential pairs can be defined only in Terminal and Transient solution types.

        Parameters
        ----------
        positive_terminal : str
            Name of the terminal to use as the positive terminal.
        negative_terminal : str
            Name of the terminal to use as the negative terminal.
        common_name : str, optional
            Name for the common mode. The default is ``None``, in which case a unique name is assigned.
        diff_name : str, optional
            Name for the differential mode. The default is ``None``, in which case a unique name is assigned.
        common_ref_z : float, optional
            Reference impedance for the common mode in ohms. The default is ``25``.
        diff_ref_z : float, optional
            Reference impedance for the differential mode in ohms. The default is ``100``.
        active : bool, optional
            Whether the differential pair is active. The default is ``True``.
        matched : bool, optional
            Whether the differential pair is matched. The default is ``False``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.EditDiffPairs
        """

        if self.solution_type not in ["Transient Network", "Terminal"]:  # pragma: no cover
            raise AttributeError("Differential pairs can be defined only in Terminal and Transient solution types.")

        props = OrderedDict()
        props["PosBoundary"] = positive_terminal
        props["NegBoundary"] = negative_terminal
        if not common_name:
            common_name = generate_unique_name("Comm")
        props["CommonName"] = common_name
        props["CommonRefZ"] = str(common_ref_z) + "ohm"
        if not diff_name:
            diff_name = generate_unique_name("Diff")
        props["DiffName"] = diff_name
        props["DiffRefZ"] = str(diff_ref_z) + "ohm"
        props["IsActive"] = active
        props["UseMatched"] = matched
        arg = ["NAME:" + generate_unique_name("Pair")]
        _dict2arg(props, arg)

        arg2 = ["NAME:EditDiffPairs", arg]

        existing_pairs = self.oboundary.GetDiffPairs()
        num_old_pairs = len(existing_pairs)
        if existing_pairs:
            for i, p in enumerate(existing_pairs):
                tmp_p = list(p)
                tmp_p.insert(0, "NAME:Pair_" + str(i))
                arg2.append(tmp_p)

        self.oboundary.EditDiffPairs(arg2)

        if len(self.oboundary.GetDiffPairs()) == num_old_pairs + 1:
            return True
        else:
            return False

    @pyaedt_function_handler()
    def add_3d_component_array_from_json(self, json_file, array_name=None):
        """Add or edit a new 3D component array from a JSON file.
        The 3D component is placed in the layout if it is not present.

        Parameters
        ----------
        json_file : str, dict
            Full path to either the JSON file or dictionary containing the array information.
        array_name : str, optional
            Name of the boundary to create or edit.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------
        Add a 3D component array from a json file.
        Below is the content of a json file that will be used in the following code sample.

        >>> {
        >>> "primarylattice": "MyFirstLattice",
        >>> "secondarylattice": "MySecondLattice",
        >>> "useairobjects": true,
        >>> "rowdimension": 4,
        >>> "columndimension": 4,
        >>> "visible": true,
        >>> "showcellnumber": true,
        >>> "paddingcells": 0,
        >>> "referencecsid": 1,
        >>> "MyFirstCell": "path/to/firstcell.a3dcomp", # optional to insert 3d comp
        >>> "MySecondCell": "path/to/secondcell.a3dcomp",# optional to insert 3d comp
        >>> "MyThirdCell": "path/to/thirdcell.a3dcomp",  # optional to insert 3d comp
        >>> "cells": { "(1,1)": {
        >>>            "name" : "MyFirstCell",
        >>>            "color" : "(255,0,20)", #optional
        >>>            "active" : true, #optional
        >>>            "postprocessing" : true #optional
        >>>            "rotation" : 0.0  #optional
        >>>             },
        >>>            "(1,2)": {
        >>>            "name" : "MySecondCell",
        >>>            "rotation" : 90.0
        >>>             }
        >>>             # continue
        >>> }

        >>> from pyaedt import Hfss
        >>> from pyaedt.generic.DataHandlers import json_to_dict
        >>> hfss_app = Hfss()
        >>> dict_in = json_to_dict(path\to\json_file)
        >>> hfss_app.add_3d_component_array_from_json(dict_in)
        """

        self.hybrid = True
        if isinstance(json_file, dict):
            json_dict = json_file
        else:
            json_dict = json_to_dict(json_file)
        if not array_name and self.omodelsetup.IsArrayDefined():
            array_name = self.omodelsetup.GetArrayNames()[0]
        elif not array_name:
            array_name = generate_unique_name("Array")

        cells_names = {}
        cells_color = {}
        cells_active = []
        cells_rotation = {}
        cells_post = {}
        for k, v in json_dict["cells"].items():
            if isinstance(k, (list, tuple)):
                k1 = str(list(k))
            else:
                k1 = str(list(ast.literal_eval(k)))
            if v["name"] in cells_names:
                cells_names[v["name"]].append(k1)
            else:
                def_names = self.oeditor.Get3DComponentDefinitionNames()
                if v["name"] not in def_names and v["name"][:-1] not in def_names:
                    if v["name"] not in json_dict:
                        self.logger.error("a3comp is not present in design and not define correctly in json.")
                        return False

                    geometryparams = self.get_components3d_vars(json_dict[v["name"]])

                    self.modeler.insert_3d_component(json_dict[v["name"]], geometryparams)
                cells_names[v["name"]] = [k1]
            if v.get("color", None):
                cells_color[v["name"]] = v.get("color", None)
            if str(v.get("rotation", "0.0")) in cells_rotation:
                cells_rotation[str(v.get("rotation", "0.0"))].append(k1)
            else:
                cells_rotation[str(v.get("rotation", "0.0"))] = [k1]
            if v.get("active", True) in cells_active:
                cells_active.append(k1)

            if v.get("postprocessing", False):
                cells_post[v["name"]] = k1

        primary_lattice = json_dict.get("primarylattice", None)
        secondary_lattice = json_dict.get("secondarylattice", None)
        if not primary_lattice:
            primary_lattice = self.omodelsetup.GetLatticeVectors()[0]
        if not secondary_lattice:
            secondary_lattice = self.omodelsetup.GetLatticeVectors()[1]

        args = [
            "NAME:" + array_name,
            "Name:=",
            array_name,
            "UseAirObjects:=",
            json_dict.get("useairobjects", True),
            "RowPrimaryBnd:=",
            primary_lattice,
            "ColumnPrimaryBnd:=",
            secondary_lattice,
            "RowDimension:=",
            json_dict.get("rowdimension", 4),
            "ColumnDimension:=",
            json_dict.get("columndimension", 4),
            "Visible:=",
            json_dict.get("visible", True),
            "ShowCellNumber:=",
            json_dict.get("showcellnumber", True),
            "RenderType:=",
            0,
            "Padding:=",
            json_dict.get("paddingcells", 0),
            "ReferenceCSID:=",
            json_dict.get("referencecsid", 1),
        ]

        cells = ["NAME:Cells"]
        for k, v in cells_names.items():
            cells.append(k + ":=")
            cells.append([", ".join(v)])
        rotations = ["NAME:Rotation"]
        for k, v in cells_rotation.items():
            if float(k) != 0.0:
                rotations.append(k + " deg:=")
                rotations.append([", ".join(v)])
        args.append(cells)
        args.append(rotations)
        args.append("Active:=")
        if cells_active:
            args.append(", ".join(cells_active))
        else:
            args.append("All")
        post = ["NAME:PostProcessingCells"]
        for k, v in cells_post.items():
            post.append(k + ":=")
            post.append(str(ast.literal_eval(v)))
        args.append(post)
        args.append("Colors:=")
        col = []
        for k, v in cells_color.items():
            col.append(k)
            col.append(str(v).replace(",", " "))
        args.append(col)
        if self.omodelsetup.IsArrayDefined():
            self.omodelsetup.EditArray(args)
        else:
            self.omodelsetup.AssignArray(args)
        return True

    @pyaedt_function_handler()
    def get_antenna_ffd_solution_data(
        self, frequencies, setup_name=None, sphere_name=None, variations=None, overwrite=True, taper="flat"
    ):
        """Export antenna parameters to Far Field Data (FFD) files and return the ``FfdSolutionData`` object.

        Parameters
        ----------
        frequencies : float, list
            Frequency value or list of frequencies to compute far field data.
        setup_name : str, optional
            Name of the setup to use. The default is ``None,`` in which case ``nominal_adaptive`` is used.
        sphere_name : str, optional
            Infinite sphere to use. The default is ``None``, in which case an existing sphere is used or a new
            one is created.
        variations : ditc, optional
            Variation dictionary.
        overwrite : bool, optional
            Whether to overwrite FFD files. The default is ``True``.
        taper : str, optional
            Type of taper to apply. The default is ``"flat"``. Options are
            ``"cosine"``, ``"triangular"``, ``"hamming"``, and ``"flat"``.

        Returns
        -------
        :class:`pyaedt.modules.solutions.FfdSolutionData`
            Solution Data Object.
        """
        if not variations:
            variations = self.available_variations.nominal_w_values_dict_w_dependent
        if not setup_name:
            setup_name = self.nominal_adaptive
        if sphere_name:
            names = [i.name for i in self.field_setups]
            if sphere_name in names:
                self.logger.info("Far field sphere %s is assigned", sphere_name)

            else:
                self.insert_infinite_sphere(
                    x_start=0, x_stop=180, x_step=5, y_start=-180, y_stop=180, y_step=5, name=sphere_name
                )
                self.logger.info("Far field sphere %s is created.", sphere_name)
        elif self.field_setups:
            sphere_name = self.field_setups[0].name
            self.logger.info("No far field sphere is defined. Using %s", sphere_name)
        else:
            sphere_name = "Infinite Sphere1"
            self.insert_infinite_sphere(
                x_start=0, x_stop=180, x_step=5, y_start=-180, y_stop=180, y_step=5, name=sphere_name
            )
            self.logger.info("Far field sphere %s is created.", setup_name)

        return FfdSolutionData(
            self,
            sphere_name=sphere_name,
            setup_name=setup_name,
            frequencies=frequencies,
            variations=variations,
            overwrite=overwrite,
            taper=taper,
        )

    @pyaedt_function_handler()
    def set_material_threshold(self, threshold=100000):
        """Set the material conductivity threshold.

        Parameters
        ----------
        threshold : float, optional
            Conductivity threshold. The default value is ``100000``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        try:
            self.odesign.SetSolveInsideThreshold(threshold)
            return True
        except:
            return False

    @pyaedt_function_handler()
    def assign_symmetry(self, entity_list, symmetry_name=None, is_perfect_e=True):
        """Assign symmetry to planar entities.

        Parameters
        ----------
        entity_list : list
            List of IDs or :class:`pyaedt.modeler.Object3d.FacePrimitive`.
        symmetry_name : str, optional
            Name of the boundary.
            If not provided it's automatically generated.
        is_perfect_e : bool, optional
            Type of symmetry plane the boundary represents: Perfect E or Perfect H.
            The default value is ``True`` (Perfect E).

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject`
            Boundary object.

        References
        ----------

        >>> oModule.AssignSymmetry

        Examples
        --------

        Create a box. Select the faces of this box and assign a symmetry.

        >>> symmetry_box = hfss.modeler.create_box([0 , -100, 0], [200, 200, 200],
        ...                                         name="SymmetryForFaces")
        >>> ids = [i.id for i in hfss.modeler["SymmetryForFaces"].faces]
        >>> symmetry = hfss.assign_symmetry(ids)
        >>> type(symmetry)
        <class 'pyaedt.modules.Boundary.BoundaryObject'>

        """
        try:
            if self.solution_type not in ["Modal", "Eigenmode"]:
                self.logger.error("Symmetry is only available with 'Modal' and 'Eigenmode' solution types.")
                return False

            if symmetry_name is None:
                symmetry_name = generate_unique_name("Symmetry")

            if not isinstance(entity_list, list):
                self.logger.error("Entities have to be provided as a list.")
                return False

            entity_list = self.modeler.convert_to_selections(entity_list, True)

            props = OrderedDict({"Name": symmetry_name, "Faces": entity_list, "IsPerfectE": is_perfect_e})
            return self._create_boundary(symmetry_name, props, "Symmetry")
        except:
            return False
