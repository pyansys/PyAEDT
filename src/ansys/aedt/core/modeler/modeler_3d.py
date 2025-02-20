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
import datetime
import json
import os.path
import warnings

from ansys.aedt.core.application.variables import generate_validation_errors
from ansys.aedt.core.generic.errors import GrpcApiError
from ansys.aedt.core.generic.general_methods import generate_unique_name
from ansys.aedt.core.generic.general_methods import open_file
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.modeler.cad.primitives_3d import Primitives3D
from ansys.aedt.core.modeler.geometry_operators import GeometryOperators
from ansys.aedt.core.visualization.advanced.misc import nastran_to_stl


class Modeler3D(Primitives3D):
    """Provides the Modeler 3D application interface.

    This class is inherited in the caller application and is accessible through the modeler variable
    object. For example, ``hfss.modeler``.

    Parameters
    ----------
    application : :class:`ansys.aedt.core.application.analysis_3d.FieldAnalysis3D`

    Examples
    --------
    >>> from ansys.aedt.core import Hfss
    >>> hfss = Hfss()
    >>> my_modeler = hfss.modeler
    """

    def __init__(self, application):
        Primitives3D.__init__(self, application)

    def __get__(self, instance, owner):
        self._app = instance
        return self

    @property
    def primitives(self):
        """Primitives.

        .. deprecated:: 0.4.15
            No need to use primitives anymore. You can instantiate primitives methods directly from modeler instead.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.primitives_3d.Primitives3D`

        """
        mess = "The property `primitives` is deprecated.\n"
        mess += " Use `app.modeler` directly to instantiate primitives methods."
        warnings.warn(mess, DeprecationWarning)
        return self

    @pyaedt_function_handler(
        component_file="input_file",
        component_name="name",
        object_list="assignment",
        boundaries_list="boundaries",
        excitation_list="excitations",
        included_cs="coordinate_systems",
        reference_cs="reference_coordinate_system",
        auxiliary_dict="export_auxiliary",
    )
    def create_3dcomponent(
        self,
        input_file,
        name=None,
        variables_to_include=None,
        assignment=None,
        boundaries=None,
        excitations=None,
        coordinate_systems=None,
        reference_coordinate_system="Global",
        is_encrypted=False,
        allow_edit=False,
        security_message="",
        password=None,  # nosec
        edit_password=None,
        password_type="UserSuppliedPassword",
        hide_contents=False,
        replace_names=False,
        component_outline="BoundingBox",
        export_auxiliary=False,
        monitor_objects=None,
        datasets=None,
        native_components=None,
        create_folder=True,
    ):
        """Create a 3D component file.

        Parameters
        ----------
        input_file : str
            Full path to the A3DCOMP file.
        name : str, optional
            Name of the component. The default is ``None``.
        variables_to_include : list, optional
            List of variables to include. The default is all variables.
        assignment : list, optional
            List of object names to export. The default is all object names.
        boundaries : list, optional
            List of Boundaries names to export. The default is all boundaries.
        excitations : list, optional
            List of Excitation names to export. The default is all excitations.
        coordinate_systems : list, optional
            List of Coordinate Systems to export. The default is the ``reference_cs``.
        reference_coordinate_system : str, optional
            The Coordinate System reference. The default is ``"Global"``.
        is_encrypted : bool, optional
            Whether the component has encrypted protection. The default is ``False``.
        allow_edit : bool, optional
            Whether the component is editable with encrypted protection.
            The default is ``False``.
        security_message : str, optional
            Security message to display when component is inserted.
            The default value is an empty string.
        password : str, optional
            Security password needed when adding the component.
            The default value is ``None``.
        edit_password : str, optional
            Edit password.
            The default value is ``None``.
        password_type : str, optional
            Password type. Options are ``UserSuppliedPassword`` and ``InternalPassword``.
            The default is ``UserSuppliedPassword``.
        hide_contents : bool or list, optional
            List of object names to hide when the component is encrypted.
            If set to an empty list or ``False``, all objects are visible.
        replace_names : bool, optional
            Whether to replace objects and material names.
            The default is ``False``.
        component_outline : str, optional
            Component outline. Value can either be ``BoundingBox`` or ``None``.
            The default is ``BoundingBox``.
        export_auxiliary : bool or str, optional
            Whether to export the auxiliary file containing information about defined
            datasets and Icepak monitor objects. A destination file can be specified
            using a string.
            The default is ``False``.
        monitor_objects : list, optional
            List of monitor objects' names to export. The default is the names of all
            monitor objects. This argument is relevant only if ``auxiliary_dict_file``
            is not set to ``False``.
        datasets : list, optional
            List of dataset names to export. The default is all datasets. This argument
             is relevant only if ``auxiliary_dict_file`` is set to ``True``.
        native_components : list, optional
            List of native_components names to export. The default is all
            native_components. This argument is relevant only if ``auxiliary_dict_file``
            is set to ``True``.
        create_folder : Bool, optional
            If the specified path to the folder where the 3D component should be saved
            does not exist, then create the folder. Default is ``True``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.Create3DComponent
        """
        if not name:
            name = self._app.design_name
        dt_string = datetime.datetime.now().strftime("%H:%M:%S %p %b %d, %Y")
        if password_type not in ["UserSuppliedPassword", "InternalPassword"]:
            self.logger.error("Password type must be 'UserSuppliedPassword' or 'InternalPassword'")
            return False
        if component_outline not in ["BoundingBox", "None"]:
            self.logger.error("Component outline must be 'BoundingBox' or 'None'")
            return False
        if password is None:
            password = os.getenv("PYAEDT_ENCRYPTED_PASSWORD", "")
        if not edit_password:
            edit_password = os.getenv("PYAEDT_ENCRYPTED_EDIT_PASSWORD", "")

        hide_contents_flag = is_encrypted and isinstance(hide_contents, list)
        arg = [
            "NAME:CreateData",
            "ComponentName:=",
            name,
            "Company:=",
            "",
            "Company URL:=",
            "",
            "Model Number:=",
            "",
            "Help URL:=",
            "",
            "Version:=",
            "1.0",
            "Notes:=",
            "",
            "IconType:=",
            "",
            "Owner:=",
            "pyaedt",
            "Email:=",
            "",
            "Date:=",
            dt_string,
            "HasLabel:=",
            False,
            "IsEncrypted:=",
            is_encrypted,
            "AllowEdit:=",
            allow_edit,
            "SecurityMessage:=",
            security_message,
            "Password:=",
            password,
            "EditPassword:=",
            edit_password,
            "PasswordType:=",
            password_type,
            "HideContents:=",
            hide_contents_flag,
            "ReplaceNames:=",
            replace_names,
            "ComponentOutline:=",
            component_outline,
        ]
        if assignment:
            objs = assignment
        else:
            native_objs = [obj.name for _, v in self.user_defined_components.items() for _, obj in v.parts.items()]
            objs = [obj for obj in self.object_names if obj not in native_objs]
            if not native_components and native_objs and not export_auxiliary:
                self.logger.warning(
                    "Native component objects cannot be exported. Use native_components argument to"
                    " export an auxiliary dictionary file containing 3D components information"
                )
        for el in objs:
            if "CreateRegion:1" in self.oeditor.GetChildObject(el).GetChildNames():
                objs.remove(el)
        arg += [
            "IncludedParts:=",
            objs,
            "HiddenParts:=",
            hide_contents if hide_contents_flag else [],
            "IncludedCS:=",
            coordinate_systems if coordinate_systems else list(self.oeditor.GetCoordinateSystems()),
            "ReferenceCS:=",
            reference_coordinate_system,
        ]
        variables = []
        dependent_variables = []
        if variables_to_include is not None and not variables_to_include == []:
            ind_variables = [i for i in self._app._variable_manager.independent_variable_names]
            dep_variables = [i for i in self._app._variable_manager.dependent_variable_names]
            for param in variables_to_include:
                if self._app[param] in ind_variables:
                    variables.append(self._app[param])
                    dependent_variables.append(param)
                elif self._app[param] not in dep_variables:
                    variables.append(param)
        elif variables_to_include is None:
            variables = self._app._variable_manager.independent_variable_names
            dependent_variables = self._app._variable_manager.dependent_variable_names
        arg += [
            "IncludedParameters:=",
            variables,
            "IncludedDependentParameters:=",
            dependent_variables,
            "ParameterDescription:=",
            [item for el in variables for item in (el + ":=", "")],
            "IsLicensed:=",
            False,
            "LicensingDllName:=",
            "",
            "VendorComponentIdentifier:=",
            "",
            "PublicKeyFile:=",
            "",
        ]

        arg2 = ["NAME:DesignData"]
        if not boundaries:
            boundaries = self.get_boundaries_name()
        if boundaries:
            arg2 += ["Boundaries:=", boundaries]
        if self._app.design_type == "Icepak":
            mesh_regions = [mr.name for mr in self._app.mesh.meshregions if mr.name != "Global"]
            if mesh_regions:
                arg2 += ["MeshRegions:=", mesh_regions]
        else:
            if excitations is None:
                excitations = self._app.excitations
                if self._app.design_type == "HFSS":
                    exc = self._app.get_oo_name(self._app.odesign, "Excitations")
                    if exc and exc[0] not in self._app.excitations:
                        excitations.extend(exc)
            excitations = list(set([i.split(":")[0] for i in excitations]))
            if excitations:
                arg2 += ["Excitations:=", excitations]
        meshops = [el.name for el in self._app.mesh.meshoperations]
        if meshops:
            used_mesh_ops = []
            for mesh in range(0, len(meshops)):
                mesh_comp = []
                for item in self._app.mesh.meshoperations[mesh].props["Objects"]:
                    if isinstance(item, str):
                        mesh_comp.append(item)
                    else:
                        mesh_comp.append(self.objects[item].name)
                if all(included_obj in objs for included_obj in mesh_comp):
                    used_mesh_ops.append(self._app.mesh.meshoperations[mesh].name)
            arg2 += ["MeshOperations:=", used_mesh_ops]
        else:
            arg2 += ["MeshOperations:=", meshops]
        arg3 = ["NAME:ImageFile", "ImageFile:=", ""]
        if export_auxiliary:
            if isinstance(export_auxiliary, bool):
                export_auxiliary = input_file + ".json"
            cachesettings = {
                prop: getattr(self._app.configurations.options, prop)
                for prop in vars(self._app.configurations.options)
                if prop.startswith("_export_")
            }
            self._app.configurations.options.unset_all_export()
            self._app.configurations.options.export_monitor = True
            self._app.configurations.options.export_datasets = True
            self._app.configurations.options.export_native_components = True
            self._app.configurations.options.export_coordinate_systems = True
            configfile = self._app.configurations.export_config()
            for prop in cachesettings:  # restore user settings
                setattr(self._app.configurations.options, prop, cachesettings[prop])
            if monitor_objects is None:
                monitor_objects = self._app.odesign.GetChildObject("Monitor").GetChildNames()
            if datasets is None:
                datasets = {}
                datasets.update(self._app.project_datasets)
                datasets.update(self._app.design_datasets)
            if native_components is None:
                native_components = self._app.native_components
            with open_file(configfile) as f:
                config_dict = json.load(f)
            out_dict = {}
            if monitor_objects:
                out_dict["monitors"] = config_dict["monitors"]
                to_remove = []
                for i, mon in enumerate(out_dict["monitors"]):
                    if mon["Name"] not in monitor_objects:
                        to_remove.append(mon)
                    else:
                        if mon["Type"] in ["Object", "Surface"]:
                            self._app.modeler.refresh_all_ids()
                            out_dict["monitors"][i]["ID"] = self._app.modeler.get_obj_id(mon["ID"])
            for mon in to_remove:
                out_dict["monitors"].remove(mon)
            if datasets:
                out_dict["datasets"] = config_dict["datasets"]
                to_remove = []
                for dat in out_dict["datasets"]:
                    if dat["Name"] not in datasets:
                        to_remove.append(dat)
                for dat in to_remove:
                    out_dict["datasets"].remove(dat)
                out_dict["datasets"] = config_dict["datasets"]
            if native_components:
                out_dict["native components"] = config_dict["native components"]
                cs_set = set()
                for _, native_dict in out_dict["native components"].items():
                    for _, instance_dict in native_dict["Instances"].items():
                        if instance_dict["CS"] and instance_dict["CS"] != "Global":
                            cs = instance_dict["CS"]
                            cs_set.add(cs)
                            if cs in config_dict["coordinatesystems"]:
                                while config_dict["coordinatesystems"][cs]["Reference CS"] != "Global":
                                    cs = config_dict["coordinatesystems"][cs]["Reference CS"]
                                    cs_set.add(cs)
                out_dict["coordinatesystems"] = copy.deepcopy(config_dict["coordinatesystems"])
                for cs in list(out_dict["coordinatesystems"]):
                    if cs not in cs_set:
                        del out_dict["coordinatesystems"][cs]
            with open_file(export_auxiliary, "w") as outfile:
                json.dump(out_dict, outfile)
        if not os.path.isdir(os.path.dirname(input_file)):
            self.logger.warning("Folder '" + os.path.dirname(input_file) + "' doesn't exist.")
            if create_folder:  # Folder doesn't exist.
                os.mkdir(os.path.dirname(input_file))
                self.logger.warning("Created folder '" + os.path.dirname(input_file) + "'")
            else:
                self.logger.warning("Unable to create 3D Component: '" + input_file + "'")
                return False
        self.oeditor.Create3DComponent(arg, arg2, input_file, arg3)
        return True

    @pyaedt_function_handler(
        component_name="name",
        object_list="assignment",
        boundaries_list="boundaries",
        excitation_list="excitations",
        included_cs="coordinate_systems",
        reference_cs="reference_coordinate_system",
    )
    def replace_3dcomponent(
        self,
        name=None,
        variables_to_include=None,
        assignment=None,
        boundaries=None,
        excitations=None,
        coordinate_systems=None,
        reference_coordinate_system="Global",
    ):
        """Replace with 3D component.

        Parameters
        ----------
        name : str, optional
            Name of the component. The default is ``None``.
        variables_to_include : list, optional
            List of variables to include. The default is ``None``.
        assignment : list, optional
            List of object names to export. The default is all object names.
        boundaries : list, optional
            List of Boundaries names to export. The default is all boundaries.
        excitations : list, optional
            List of Excitation names to export. The default is all excitations.
        coordinate_systems : list, optional
            List of coordinate systems to export. The default is all coordinate systems.
        reference_coordinate_system : str, optional
            The coordinate system reference. The default is ``"Global"``.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.components_3d.UserDefinedComponent`
            User-defined component object.

        References
        ----------
        >>> oEditor.ReplaceWith3DComponent
        """
        if not variables_to_include:
            variables_to_include = []
        if not name:
            name = generate_unique_name(self._app.design_name)
        dt_string = datetime.datetime.now().strftime("%H:%M:%S %p %b %d, %Y")
        arg = [
            "NAME:CreateData",
            "ComponentName:=",
            name,
            "Company:=",
            "",
            "Company URL:=",
            "",
            "Model Number:=",
            "",
            "Help URL:=",
            "",
            "Version:=",
            "1.0",
            "Notes:=",
            "",
            "IconType:=",
            "",
            "Owner:=",
            "pyaedt",
            "Email:=",
            "",
            "Date:=",
            dt_string,
            "HasLabel:=",
            False,
        ]
        if assignment:
            objs = assignment
        else:
            native_objs = [obj.name for _, v in self.user_defined_components.items() for _, obj in v.parts.items()]
            objs = [obj for obj in self.object_names if obj not in native_objs]
            if native_objs:
                self.logger.warning(
                    "Native component objects cannot be exported. Use native_components argument to"
                    " export an auxiliary dictionary file containing 3D components information"
                )
        for el in objs:
            if "CreateRegion:1" in self.oeditor.GetChildObject(el).GetChildNames():
                objs.remove(el)
        arg += [
            "IncludedParts:=",
            objs,
            "HiddenParts:=",
            [],
            "IncludedCS:=",
            coordinate_systems if coordinate_systems else list(self.oeditor.GetCoordinateSystems()),
            "ReferenceCS:=",
            reference_coordinate_system,
        ]
        variables = []
        if variables_to_include:
            dependent_variables = []
            ind_variables = [i for i in self._app._variable_manager.independent_variable_names]
            dep_variables = [i for i in self._app._variable_manager.dependent_variable_names]
            for param in variables_to_include:
                if self._app[param] in ind_variables:
                    variables.append(self._app[param])
                    dependent_variables.append(param)
                elif self._app[param] not in dep_variables:
                    variables.append(param)
        else:
            variables = self._app._variable_manager.independent_variable_names
            dependent_variables = self._app._variable_manager.dependent_variable_names
        arg += [
            "IncludedParameters:=",
            variables,
            "IncludedDependentParameters:=",
            dependent_variables,
            "ParameterDescription:=",
            [item for el in variables for item in (el + ":=", "")],
        ]

        arg2 = ["NAME:DesignData"]
        if not boundaries:
            boundaries = self.get_boundaries_name()
        if boundaries:
            arg2 += ["Boundaries:=", boundaries]
        if self._app.design_type == "Icepak":
            mesh_regions = [mr.name for mr in self._app.mesh.meshregions if mr.name != "Global"]
            if mesh_regions:
                arg2 += ["MeshRegions:=", mesh_regions]
        else:
            if excitations:
                excitations = excitations
            else:
                excitations = self._app.excitations
                if self._app.design_type == "HFSS":
                    exc = self._app.get_oo_name(self._app.odesign, "Excitations")
                    if exc and exc[0] not in self._app.excitations:
                        excitations.extend(exc)
            excitations = list(set([i.split(":")[0] for i in excitations]))
            if excitations:
                arg2 += ["Excitations:=", excitations]
        meshops = [el.name for el in self._app.mesh.meshoperations]
        if meshops:
            used_mesh_ops = []
            for mesh in range(0, len(meshops)):
                mesh_comp = []
                for item in self._app.mesh.meshoperations[mesh].props["Objects"]:
                    if isinstance(item, str):
                        mesh_comp.append(item)
                    else:
                        mesh_comp.append(self.objects[item].name)
                if all(included_obj in objs for included_obj in mesh_comp):
                    used_mesh_ops.append(self._app.mesh.meshoperations[mesh].name)
            arg2 += ["MeshOperations:=", used_mesh_ops]
        else:
            arg2 += ["MeshOperations:=", meshops]
        arg3 = ["NAME:ImageFile", "ImageFile:=", ""]
        old_components = self.user_defined_component_names
        self.oeditor.ReplaceWith3DComponent(arg, arg2, arg3)
        self.refresh_all_ids()
        new_name = list(set(self.user_defined_component_names) - set(old_components))
        return self.user_defined_components[new_name[0]]

    @pyaedt_function_handler(
        startingposition="origin",
        innerradius="inner_radius",
        outerradius="outer_radius",
        dielradius="diel_radius",
        matinner="mat_inner",
        matouter="mat_outer",
        matdiel="mat_diel",
    )
    def create_coaxial(
        self,
        origin,
        axis,
        inner_radius=1,
        outer_radius=2,
        diel_radius=1.8,
        length=10,
        mat_inner="copper",
        mat_outer="copper",
        mat_diel="teflon_based",
    ):
        """Create a coaxial.

        Parameters
        ----------
        origin : list
            List of ``[x, y, z]`` coordinates for the starting position.
        axis : int
            Coordinate system AXIS (integer ``0`` for X, ``1`` for Y, ``2`` for Z) or
            the :class:`Application.AXIS` enumerator.
        inner_radius : float, optional
            Inner coax radius. The default is ``1``.
        outer_radius : float, optional
            Outer coax radius. The default is ``2``.
        diel_radius : float, optional
            Dielectric coax radius. The default is ``1.8``.
        length : float, optional
            Coaxial length. The default is ``10``.
        mat_inner : str, optional
            Material for the inner coaxial. The default is ``"copper"``.
        mat_outer : str, optional
            Material for the outer coaxial. The default is ``"copper"``.
        mat_diel : str, optional
            Material for the dielectric. The default is ``"teflon_based"``.

        Returns
        -------
        tuple
            Contains the inner, outer, and dielectric coax as
            :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d` objects.

        References
        ----------
        >>> oEditor.CreateCylinder
        >>> oEditor.AssignMaterial

        Examples
        --------
        This example shows how to create a Coaxial Along X Axis waveguide.

        >>> from ansys.aedt.core import Hfss
        >>> app = Hfss()
        >>> position = [0,0,0]
        >>> coax = app.modeler.create_coaxial(position,app.AXIS.X,inner_radius=0.5,outer_radius=0.8,diel_radius=0.78,
        ... length=50)

        """
        if not (outer_radius > diel_radius and diel_radius > inner_radius):
            raise ValueError("Error in coaxial radius.")
        inner = self.create_cylinder(axis, origin, inner_radius, length, 0)
        outer = self.create_cylinder(axis, origin, outer_radius, length, 0)
        diel = self.create_cylinder(axis, origin, diel_radius, length, 0)
        self.subtract(outer, inner)
        self.subtract(outer, diel)
        inner.material_name = mat_inner
        outer.material_name = mat_outer
        diel.material_name = mat_diel

        return inner, outer, diel

    @pyaedt_function_handler()
    def create_waveguide(
        self,
        origin,
        wg_direction_axis,
        wgmodel="WG0",
        wg_length=100,
        wg_thickness=None,
        wg_material="aluminum",
        parametrize_w=False,
        parametrize_h=False,
        create_sheets_on_openings=False,
        name=None,
    ):
        """Create a standard waveguide and optionally parametrize `W` and `H`.

        Available models are WG0.0, WG0, WG1, WG2, WG3, WG4, WG5, WG6,
        WG7, WG8, WG9, WG9A, WG10, WG11, WG11A, WG12, WG13, WG14,
        WG15, WR102, WG16, WG17, WG18, WG19, WG20, WG21, WG22, WG24,
        WG25, WG26, WG27, WG28, WG29, WG29, WG30, WG31, and WG32.

        Parameters
        ----------
        origin : list
            List of ``[x, y, z]`` coordinates for the original position.
        wg_direction_axis : int
            Coordinate system axis (integer ``0`` for X, ``1`` for Y, ``2`` for Z) or
            the :class:`Application.AXIS` enumerator.
        wgmodel : str, optional
            Waveguide model. The default is ``"WG0"``.
        wg_length : float, optional
            Waveguide length. The default is ``100``.
        wg_thickness : float, optional
            Waveguide thickness. The default is ``None``, in which case the
            thickness is `wg_height/20`.
        wg_material : str, optional
            Waveguide material. The default is ``"aluminum"``.
        parametrize_w : bool, optional
            Whether to parametrize `W`. The default is ``False``.
        parametrize_h : bool, optional
            Whether to parametrize `H`. The default is ``False``.
        create_sheets_on_openings : bool, optional
            Whether to create sheets on both openings. The default is ``False``.
        name : str, optional
            Name of the waveguide. The default is ``None``.

        Returns
        -------
        Tuple[:class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`]
            Objects created by the waveguide.

        References
        ----------
        >>> oEditor.CreateBox
        >>> oEditor.AssignMaterial


        Examples
        --------
        This example shows how to create a WG9 waveguide.

        >>> from ansys.aedt.core import Hfss
        >>> app = Hfss()
        >>> position = [0, 0, 0]
        >>> wg1 = app.modeler.create_waveguide(position, app.AXIS.,
        ...                                    wgmodel="WG9", wg_length=2000)


        """
        p1 = -1
        p2 = -1
        WG = {
            "WG0.0": [584.2, 292.1],
            "WG0": [533.4, 266.7],
            "WG1": [457.2, 228.6],
            "WG2": [381, 190.5],
            "WG3": [292.1, 146.05],
            "WG4": [247.65, 123.825],
            "WG5": [195.58, 97.79],
            "WG6": [165.1, 82.55],
            "WG7": [129.54, 64.77],
            "WG8": [109.22, 54.61],
            "WG9": [88.9, 44.45],
            "WG9A": [86.36, 43.18],
            "WG10": [72.136, 34.036],
            "WG11": [60.2488, 28.4988],
            "WG11A": [58.166, 29.083],
            "WG12": [47.5488, 22.1488],
            "WG13": [40.386, 20.193],
            "WG14": [34.8488, 15.7988],
            "WG15": [28.4988, 12.6238],
            "WR102": [25.908, 12.954],
            "WG16": [22.86, 10.16],
            "WG17": [19.05, 9.525],
            "WG18": [15.7988, 7.8994],
            "WG19": [12.954, 6.477],
            "WG20": [0.668, 4.318],
            "WG21": [8.636, 4.318],
            "WG22": [7.112, 3.556],
            "WG23": [5.6896, 2.8448],
            "WG24": [4.7752, 2.3876],
            "WG25": [3.7592, 1.8796],
            "WG26": [3.0988, 1.5494],
            "WG27": [2.54, 1.27],
            "WG28": [2.032, 1.016],
            "WG29": [1.651, 0.8255],
            "WG30": [1.2954, 0.6477],
            "WG31": [1.0922, 0.5461],
            "WG32": [0.8636, 0.4318],
        }

        if wgmodel in WG:
            original_model_units = self.model_units
            self.model_units = "mm"

            wgwidth = WG[wgmodel][0]
            wgheight = WG[wgmodel][1]
            if not wg_thickness:
                wg_thickness = wgheight / 20
            if parametrize_h:
                self._app[wgmodel + "_H"] = self._app.value_with_units(wgheight)
                h = wgmodel + "_H"
                hb = wgmodel + "_H + 2*" + self._app.value_with_units(wg_thickness)
            else:
                h = self._app.value_with_units(wgheight)
                hb = self._app.value_with_units(wgheight) + " + 2*" + self._app.value_with_units(wg_thickness)

            if parametrize_w:
                self._app[wgmodel + "_W"] = self._app.value_with_units(wgwidth)
                w = wgmodel + "_W"
                wb = wgmodel + "_W + " + self._app.value_with_units(2 * wg_thickness)
            else:
                w = self._app.value_with_units(wgwidth)
                wb = self._app.value_with_units(wgwidth) + " + 2*" + self._app.value_with_units(wg_thickness)
            if wg_direction_axis == self._app.AXIS.Z:
                airbox = self.create_box(origin, [w, h, wg_length])

                if isinstance(wg_thickness, str):
                    origin[0] = str(origin[0]) + "-" + wg_thickness
                    origin[1] = str(origin[1]) + "-" + wg_thickness
                else:
                    origin[0] -= wg_thickness
                    origin[1] -= wg_thickness

            elif wg_direction_axis == self._app.AXIS.Y:
                airbox = self.create_box(origin, [w, wg_length, h])

                if isinstance(wg_thickness, str):
                    origin[0] = str(origin[0]) + "-" + wg_thickness
                    origin[2] = str(origin[2]) + "-" + wg_thickness
                else:
                    origin[0] -= wg_thickness
                    origin[2] -= wg_thickness
            else:
                airbox = self.create_box(origin, [wg_length, w, h])

                if isinstance(wg_thickness, str):
                    origin[2] = str(origin[2]) + "-" + wg_thickness
                    origin[1] = str(origin[1]) + "-" + wg_thickness
                else:
                    origin[2] -= wg_thickness
                    origin[1] -= wg_thickness
            centers = [f.center for f in airbox.faces]
            xpos = [i[wg_direction_axis] for i in centers]
            mini = xpos.index(min(xpos))
            maxi = xpos.index(max(xpos))
            if create_sheets_on_openings:
                p1 = self.create_object_from_face(airbox.faces[mini].id)
                p2 = self.create_object_from_face(airbox.faces[maxi].id)
            if not name:
                name = generate_unique_name(wgmodel)
            if wg_direction_axis == self._app.AXIS.Z:
                wgbox = self.create_box(origin, [wb, hb, wg_length], name=name)
            elif wg_direction_axis == self._app.AXIS.Y:
                wgbox = self.create_box(origin, [wb, wg_length, hb], name=name)
            else:
                wgbox = self.create_box(origin, [wg_length, wb, hb], name=name)
            self.subtract(wgbox, airbox, False)
            wgbox.material_name = wg_material
            self.model_units = original_model_units
            return wgbox, p1, p2
        else:
            return None

    @pyaedt_function_handler()
    def create_conical_rings(
        self,
        axis,
        origin,
        bottom_radius,
        top_radius,
        cone_height,
        ring_height,
        thickness=None,
        name=None,
    ):
        """Create rings in a conical shape.

        Parameters
        ----------
        axis : str
            Coordinate system of the axis.
        origin : list, optional
            List of ``[x, y, z]`` coordinates for the center position
            of the bottom of the cone.
        bottom_radius : float
            Bottom radius of the cone.
        top_radius : float
            Top radius of the cone.
        cone_height : float
            Height of the cone.
        ring_height : float
            Ring height.
        thickness : float, optional
            Ring thickness. The default is ``None``, in which case a 2D sheet is created.
        name : str, optional
            Name of the cone. The default is ``None``, in which case
            the default name is assigned.

        Returns
        -------
        list[:class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`] or bool
            List of 3D object or ``False`` if it fails.

        References
        ----------
        >>> oEditor.CreatePolyline
        >>> oEditor.SweepAroundAxis
        >>> oEditor.ThickenSheet

        Examples
        --------
        This example shows how to create rings along Z axis with a cone shape.

        >>> from ansys.aedt.core import Hfss
        >>> app = Hfss()
        >>> position = [0,0,0]
        >>> cone_object = aedtapp.modeler.create_conical_rings(axis='Z', origin=[0, 0, 0],
        ...                                           bottom_radius=2, top_radius=3, cone_height=4, ring_height=0.1)

        """
        if bottom_radius <= top_radius:
            self.logger.error("the ``bottom_radius`` argument must must be bigger than ``top_radius``.")
            return False
        if isinstance(bottom_radius, (int, float)) and bottom_radius < 0:
            self.logger.error("The ``bottom_radius`` argument must be greater than 0.")
            return False
        if isinstance(top_radius, (int, float)) and top_radius < 0:
            self.logger.error("The ``top_radius`` argument must be greater than 0.")
            return False
        if isinstance(cone_height, (int, float)) and cone_height <= 0:
            self.logger.error("The ``cone_height`` argument must be greater than 0.")
            return False
        if isinstance(ring_height, (int, float)) and ring_height <= 0:
            self.logger.error("The ``ring_height`` argument must be greater than 0.")
            return False
        if len(origin) != 3:
            self.logger.error("The ``origin`` argument must be a valid three-element list.")
            return False

        if not name:
            name = generate_unique_name("ring_cone")

        n_strips = int(cone_height / ring_height)

        if not thickness:
            thickness = 0.0

        solids = []
        for strip in range(n_strips):
            if strip % 2 == 0:
                z = strip * ring_height
                r_ini = top_radius + z * (bottom_radius - top_radius) / cone_height
                r_end = top_radius + (z + ring_height) * (bottom_radius - top_radius) / cone_height
                polyline_points = [[r_ini, 0, cone_height - z], [r_end, 0, cone_height - z - ring_height]]
                pol = self.create_polyline(polyline_points, name=name)
                pol.sweep_around_axis("Z")
                solid = self.thicken_sheet(pol.name, thickness=thickness)

                if axis == "X":
                    solid.rotate(axis=1, angle=90.0)
                elif axis == "Y":
                    solid.rotate(axis=0, angle=-90.0)
                solids.append(solid)
        return solids

    @pyaedt_function_handler()
    def objects_in_bounding_box(self, bounding_box, check_solids=True, check_lines=True, check_sheets=True):
        """Given a bounding box checks if objects, sheets and lines are inside it.

        Parameters
        ----------
        bounding_box : list
            List of coordinates of bounding box vertices.
            Bounding box is provided as [xmin, ymin, zmin, xmax, ymax, zmax].
        check_solids : bool, optional
            Check solid objects.
        check_lines : bool, optional
            Check line objects.
        check_sheets : bool, optional
            Check sheet objects.

        Returns
        -------
        list[:class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`]
        """
        if len(bounding_box) != 6:
            raise ValueError("Bounding box list must have dimension 6.")

        objects = []
        if check_solids:
            for obj in self.solid_objects:
                bound = obj.bounding_box
                if (
                    bounding_box[0] <= bound[0] <= bounding_box[3]
                    and bounding_box[1] <= bound[1] <= bounding_box[4]
                    and bounding_box[2] <= bound[2] <= bounding_box[5]
                    and bounding_box[0] <= bound[3] <= bounding_box[3]
                    and bounding_box[1] <= bound[4] <= bounding_box[4]
                    and bounding_box[2] <= bound[5] <= bounding_box[5]
                ):
                    objects.append(obj)

        if check_lines:
            for obj in self.line_objects:
                bound = obj.bounding_box
                if (
                    bounding_box[0] <= bound[0] <= bounding_box[3]
                    and bounding_box[1] <= bound[1] <= bounding_box[4]
                    and bounding_box[2] <= bound[2] <= bounding_box[5]
                    and bounding_box[0] <= bound[3] <= bounding_box[3]
                    and bounding_box[1] <= bound[4] <= bounding_box[4]
                    and bounding_box[2] <= bound[5] <= bounding_box[5]
                ):
                    objects.append(obj)

        if check_sheets:
            for obj in self.sheet_objects:
                bound = obj.bounding_box
                if (
                    bounding_box[0] <= bound[0] <= bounding_box[3]
                    and bounding_box[1] <= bound[1] <= bounding_box[4]
                    and bounding_box[2] <= bound[2] <= bounding_box[5]
                    and bounding_box[0] <= bound[3] <= bounding_box[3]
                    and bounding_box[1] <= bound[4] <= bounding_box[4]
                    and bounding_box[2] <= bound[5] <= bounding_box[5]
                ):
                    objects.append(obj)

        return objects

    @pyaedt_function_handler()
    def import_nastran(
        self,
        file_path,
        import_lines=True,
        lines_thickness=0,
        import_as_light_weight=False,
        decimation=0,
        group_parts=True,
        enable_planar_merge="True",
        save_only_stl=False,
        preview=False,
        merge_angle=1e-3,
    ):
        """Import Nastran file into 3D Modeler by converting the faces to stl and reading it.

        The solids are translated directly to AEDT format.

        Parameters
        ----------
        file_path : str
            Path to .nas file.
        import_lines : bool, optional
            Whether to import the lines or only triangles. Default is ``True``.
        lines_thickness : float, optional
            Whether to thicken lines after creation and it's default value.
            Every line will be parametrized with a design variable called ``xsection_linename``.
        import_as_light_weight : bool, optional
            Import the stl generatated as light weight. It works only on SBR+ and HFSS Regions. Default is ``False``.
        decimation : float, optional
            Fraction of the original mesh to remove before creating the stl file.  If set to ``0.9``,
            this function tries to reduce the data set to 10% of its
            original size and removes 90% of the input triangles.
        group_parts : bool, optional
            Whether to group imported parts by object ID. The default is ``True``.
        enable_planar_merge : str, optional
            Whether to enable or not planar merge. It can be ``"True"``, ``"False"`` or ``"Auto"``.
            ``"Auto"`` will disable the planar merge if stl contains more than 50000 triangles.
        save_only_stl : bool, optional
            Whether to import the model in HFSS or only generate the stl file.
        preview : bool, optional
            Whether to preview the model in pyvista or skip it.
        merge_angle : float, optional
            Angle in radians for which faces will be considered planar. Default is ``1e-3``.

        Returns
        -------
        List of :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`, dict
            New object created and nastran dictionary.
        """
        autosave = (
            True if self._app.odesktop.GetRegistryInt("Desktop/Settings/ProjectOptions/DoAutoSave") == 1 else False
        )
        self._app.odesktop.EnableAutoSave(False)
        objs_before = [i for i in self.object_names]

        output_stls, nas_to_dict, enable_stl_merge = nastran_to_stl(
            input_file=file_path,
            decimation=decimation,
            output_folder=self._app.working_directory,
            enable_planar_merge=enable_planar_merge,
            preview=preview,
        )
        if save_only_stl:
            return output_stls, nas_to_dict

        self._app.desktop_class.close_windows()
        self.logger.info("Importing STL in 3D Modeler")
        if output_stls:
            for output_stl in output_stls:
                self.import_3d_cad(
                    output_stl,
                    create_lightweigth_part=import_as_light_weight,
                    healing=False,
                    merge_planar_faces=enable_stl_merge,
                    merge_angle=merge_angle,
                )
                self.logger.info(f"Model {os.path.split(output_stl)[-1]} imported")
            self._app.save_project()
            if group_parts:
                self.logger.info("Grouping parts...")
                aedt_objs = self.object_names[::]
                for assembly, _ in nas_to_dict["Assemblies"].items():
                    assembly_group_name = assembly
                    if assembly in list(self.oeditor.GetChildNames("Groups")):
                        assembly_group_name = generate_unique_name(assembly, n=2)
                    new_group = []
                    for el in nas_to_dict["Assemblies"][assembly]["Solids"].keys():
                        obj_names = [i for i in aedt_objs if i.startswith(f"Solid_{el}")]
                        if obj_names:
                            new_group.append(self.create_group(obj_names, group_name=str(el)))
                    for el in nas_to_dict["Assemblies"][assembly]["Triangles"].keys():
                        obj_names = [i for i in aedt_objs if i == f"Sheet_{el}" or i.startswith(f"Sheet_{el}_")]
                        if obj_names:
                            new_group.append(self.create_group(obj_names, group_name=str(el)))
                    if assembly_group_name in list(self.oeditor.GetChildNames("Groups")):
                        self.oeditor.MoveEntityToGroup(
                            [
                                "Groups:=",
                                new_group,
                            ],
                            ["ParentGroup:=", assembly_group_name],
                        )
                    else:
                        new_name = self.create_group(new_group, group_name=assembly_group_name)
                        self.oeditor.MoveEntityToGroup(
                            [
                                "Groups:=",
                                new_group,
                            ],
                            ["ParentGroup:=", new_name],
                        )
                self.logger.info("Parts grouped")
                self._app.save_project()

        if import_lines:
            if lines_thickness:
                self._app["x_section_thickness"] = self._app.value_with_units(lines_thickness)
            self.logger.info("Importing lines. This operation can take time....")
            for assembly_name, assembly in nas_to_dict["Assemblies"].items():
                if assembly["Lines"]:
                    for line_name, lines in assembly["Lines"].items():
                        polys = []
                        id = 0
                        for line in lines:
                            try:
                                # points = [nas_to_dict["Points"][line[0]], nas_to_dict["Points"][line[1]]]
                                points = [nas_to_dict["Points"][i] for i in line]
                            except KeyError:
                                continue
                            p_line = self.create_polyline(
                                points,
                                name=f"Poly_{line_name}_{id}",
                                xsection_type="Circle" if lines_thickness else None,
                                xsection_width="x_section_thickness" if lines_thickness else 1,
                            )

                            if p_line:
                                polys.append(p_line)
                            else:
                                self.logger.warning("Failed to create Polyline as a union of segments.")
                                self.logger.warning("Trying to create single segments.")
                                for i in range(len(points) - 1):
                                    p_line = self.create_polyline(
                                        points[i : i + 2],
                                        name=generate_unique_name(f"Poly_{line_name}_{id}"),
                                        xsection_type="Circle" if lines_thickness else None,
                                        xsection_width="x_section_thickness" if lines_thickness else 1,
                                    )
                                    if p_line:
                                        polys.append(p_line)
                            id += 1
                        if group_parts:
                            pids = [i.name for i in polys]
                            if assembly_name in list(self.oeditor.GetChildNames("Groups")):
                                self.oeditor.MoveEntityToGroup(
                                    [
                                        "Objects:=",
                                        pids,
                                    ],
                                    ["ParentGroup:=", assembly_name],
                                )
                            else:
                                group_name = self.create_group(pids, group_name=assembly_name)
                                self.oeditor.MoveEntityToGroup(
                                    [
                                        "Objects:=",
                                        pids,
                                    ],
                                    ["ParentGroup:=", group_name],
                                )
            self.logger.info("Lines imported")

        objs_after = [i for i in self.object_names]
        new_objects = [self[i] for i in objs_after if i not in objs_before]
        self._app.oproject.SetActiveDesign(self._app.design_name)
        self._app.odesktop.EnableAutoSave(autosave)
        self.logger.info_timer("Nastran model correctly imported.")
        return new_objects, nas_to_dict

    @pyaedt_function_handler()
    def import_from_openstreet_map(
        self,
        latitude_longitude,
        env_name="default",
        terrain_radius=500,
        include_osm_buildings=True,
        including_osm_roads=True,
        import_in_aedt=True,
        plot_before_importing=False,
        z_offset=2,
        road_step=3,
        road_width=8,
        create_lightweigth_part=True,
    ):
        """Import OpenStreet Maps into AEDT.

        Parameters
        ----------
        latitude_longitude : list
            Latitude and longitude.
        env_name : str, optional
            Name of the environment used to create the scene. The default value is ``"default"``.
        terrain_radius : float, int
            Radius to take around center. The default value is ``500``.
        include_osm_buildings : bool
            Either if include or not 3D Buildings. Default is ``True``.
        including_osm_roads : bool
            Either if include or not road. Default is ``True``.
        import_in_aedt : bool
            Either if import stl after generation or not. Default is ``True``.
        plot_before_importing : bool
            Either if plot before importing or not. Default is ``True``.
        z_offset : float
            Road elevation offset. Default is ``0``.
        road_step : float
            Road simplification steps in meter. Default is ``3``.
        road_width : float
            Road width  in meter. Default is ``8``.
        create_lightweigth_part : bool
            Either if import as lightweight object or not. Default is ``True``.

        Returns
        -------
        dict
            Dictionary of generated infos.

        Notes
        -----
        Please note that elevation is not computed anymore in this method.
        Please check the example
        ``https://examples.aedt.docs.pyansys.com/version/dev/examples/high_frequency/antenna/large_scenarios/city.html``
        to compute also elevation.

        """
        from ansys.aedt.core.modeler.advanced_cad.oms import BuildingsPrep
        from ansys.aedt.core.modeler.advanced_cad.oms import RoadPrep
        from ansys.aedt.core.modeler.advanced_cad.oms import TerrainPrep

        output_path = self._app.working_directory

        parts_dict = {}
        # instantiate terrain module
        terrain_prep = TerrainPrep(cad_path=output_path)
        terrain_geo = terrain_prep.get_terrain(latitude_longitude, max_radius=terrain_radius, grid_size=30)
        terrain_stl = terrain_geo["file_name"]
        terrain_mesh = terrain_geo["mesh"]
        terrain_dict = {"file_name": terrain_stl, "color": "brown", "material": "earth"}
        parts_dict["terrain"] = terrain_dict
        building_mesh = None
        road_mesh = None
        if include_osm_buildings:
            self.logger.info("Generating Building Geometry")
            building_prep = BuildingsPrep(cad_path=output_path)
            building_geo = building_prep.generate_buildings(
                latitude_longitude, terrain_mesh, max_radius=terrain_radius * 0.8
            )
            building_stl = building_geo["file_name"]
            building_mesh = building_geo["mesh"]
            building_dict = {"file_name": building_stl, "color": "grey", "material": "concrete"}
            parts_dict["buildings"] = building_dict
        if including_osm_roads:
            self.logger.info("Generating Road Geometry")
            road_prep = RoadPrep(cad_path=output_path)
            road_geo = road_prep.create_roads(
                latitude_longitude,
                terrain_mesh,
                max_radius=terrain_radius,
                z_offset=z_offset,
                road_step=road_step,
                road_width=road_width,
            )

            road_stl = road_geo["file_name"]
            road_mesh = road_geo["mesh"]
            road_dict = {"file_name": road_stl, "color": "black", "material": "asphalt"}
            parts_dict["roads"] = road_dict

        json_path = os.path.join(output_path, env_name + ".json")

        scene = {
            "name": env_name,
            "version": 1,
            "type": "environment",
            "center_lat_lon": latitude_longitude,
            "radius": terrain_radius,
            "include_buildings": include_osm_buildings,
            "include_roads": including_osm_roads,
            "parts": parts_dict,
        }

        with open_file(json_path, "w", encoding="utf-8") as f:
            json.dump(scene, f, indent=4)

        self.logger.info("Done...")
        if plot_before_importing:
            import pyvista as pv

            self.logger.info("Viewing Geometry...")
            # view results
            plt = pv.Plotter()
            if building_mesh:
                plt.add_mesh(building_mesh, cmap="gray", label=r"Buildings")
            if road_mesh:
                plt.add_mesh(road_mesh, cmap="bone", label=r"Roads")
            if terrain_mesh:
                plt.add_mesh(terrain_mesh, cmap="terrain", label=r"Terrain")  # clim=[00, 100]
            plt.add_legend()
            plt.add_axes(line_width=2, xlabel="X", ylabel="Y", zlabel="Z")
            plt.add_axes_at_origin(x_color=None, y_color=None, z_color=None, line_width=2, labels_off=True)
            plt.show(interactive=True)

        if import_in_aedt:
            self.model_units = "meter"
            for part in parts_dict:
                if not os.path.exists(parts_dict[part]["file_name"]):
                    continue
                obj_names = [i for i in self.object_names]
                self.import_3d_cad(parts_dict[part]["file_name"], create_lightweigth_part=create_lightweigth_part)
                added_objs = [i for i in self.object_names if i not in obj_names]
                if part == "terrain":
                    transparency = 0.2
                    color = [0, 125, 0]
                elif part == "buildings":
                    transparency = 0.6
                    color = [0, 0, 255]
                else:
                    transparency = 0.0
                    color = [40, 40, 40]
                for obj in added_objs:
                    self[obj].transparency = transparency
                    self[obj].color = color
        return scene

    @pyaedt_function_handler(objects_list="assignment", segments_number="segments", mesh_sheets_number="mesh_sheets")
    def objects_segmentation(
        self,
        assignment,
        segmentation_thickness=None,
        segments=None,
        apply_mesh_sheets=False,
        mesh_sheets=2,
    ):
        """Get segmentation of an object given the segmentation thickness or number of segments.

        Parameters
        ----------
        assignment : list, str
            List of objects to apply the segmentation to.
            It can either be a list of strings (object names), integers (object IDs), or
            a list[:class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`] classes.
        segmentation_thickness : float, optional
            Segmentation thickness.
            Model units are automatically assigned. The default is ``None``.
        segments : int, optional
            Number of segments to segment the object to. The default is ``None``.
        apply_mesh_sheets : bool, optional
            Whether to apply mesh sheets to selected objects.
            Mesh sheets are needed in case the user would like to have additional layers
            inside the objects for a finer mesh and more accurate results. The default is ``False``.
        mesh_sheets : int, optional
            Number of mesh sheets within one magnet segment.
            If nothing is provided and ``apply_mesh_sheets=True``, the default value is ``2``.

        Returns
        -------
        dict or tuple
            Depending on value ``apply_mesh_sheets`` it returns either a dictionary or a tuple.
            If mesh sheets are applied the method returns a tuple where:
            - First dictionary is the segments that the object has been divided into.
            - Second dictionary is the mesh sheets eventually needed to apply the mesh.
            to inside the object. Keys are the object names, and values are respectively
            segments sheets and mesh sheets of the
            :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d` class.
            If mesh sheets are not applied the method returns only the dictionary of
            segments that the object has been divided into.
            ``False`` is returned if the method fails.
        """
        if not segmentation_thickness and not segments:
            self.logger.error("Provide at least one option to segment the objects in the list.")
            return False
        elif segmentation_thickness and segments:
            self.logger.error("Only one segmentation option can be selected.")
            return False

        assignment = self.convert_to_selections(assignment, True)

        segment_sheets = {}
        segment_objects = {}
        for obj_name in assignment:
            obj = self[obj_name]
            obj_axial_length = GeometryOperators.points_distance(obj.top_face_z.center, obj.bottom_face_z.center)
            if segments:
                segmentation_thickness = obj_axial_length / segments
            elif segmentation_thickness:
                segments = round(obj_axial_length / segmentation_thickness)
            face_object = self.create_object_from_face(obj.bottom_face_z)
            # segment sheets
            segment_sheets[obj.name] = face_object.duplicate_along_line(["0", "0", segmentation_thickness], segments)
            segment_objects[obj.name] = []
            for value in segment_sheets[obj.name]:
                segment_objects[obj.name].append([x for x in self.sheet_objects if x.name == value][0])
            if apply_mesh_sheets:
                sheets = {}
                mesh_objects = {}
                # mesh sheets
                mesh_sheet_position = segmentation_thickness / (mesh_sheets + 1)
                for i in range(len(segment_objects[obj.name]) + 1):
                    if i == 0:
                        face = obj.bottom_face_z
                    else:
                        face = segment_objects[obj.name][i - 1].faces[0]
                    mesh_face_object = self.create_object_from_face(face)
                    self.move(mesh_face_object, [0, 0, mesh_sheet_position])
                    sheets[obj.name] = mesh_face_object.duplicate_along_line([0, 0, mesh_sheet_position], mesh_sheets)
                mesh_objects[obj.name] = [mesh_face_object]
                for value in sheets[obj.name]:
                    mesh_objects[obj.name].append([x for x in self.sheet_objects if x.name == value][0])
        face_object.delete()
        if apply_mesh_sheets:
            return segment_objects, mesh_objects
        else:
            return segment_objects

    @pyaedt_function_handler
    def change_region_padding(self, padding_data, padding_type, direction=None, region_name="Region"):
        """
        Change region padding settings.

        Parameters
        ----------
        padding_data : str or list of str
            Padding value (with unit if necessary). A list of padding values must have corresponding
            elements in ``padding_type`` and ``direction`` arguments.
        padding_type : str or list of str
            Padding type. Available options are ``"Percentage Offset"``, ``"Transverse Percentage Offset"``,
            ``"Absolute Offset"``, ``"Absolute Position"``.
        direction : str or list of str, optional
            Direction to which apply the padding settings. A direction can be ``"+X"``, ``"-X"``,
            `"+Y"``, ``"-Y"``, ``"+Z"`` or ``"-Z"``. Default is ``None``, in which case all the
            directions are used (in the order written in the previous sentence).
        region_name : str optional
            Region name. Default is ``Region``.

        Returns
        -------
        bool
            ``True`` if successful, else ``None``.

        Examples
        --------
        >>> import ansys.aedt.core
        >>> app = ansys.aedt.core.Icepak()
        >>> app.modeler.change_region_padding("10mm", padding_type="Absolute Offset", direction="-X")
        """
        available_directions = ["+X", "-X", "+Y", "-Y", "+Z", "-Z"]
        available_paddings = [
            "Percentage Offset",
            "Transverse Percentage Offset",
            "Absolute Offset",
            "Absolute Position",
        ]
        if not isinstance(padding_data, list):
            padding_data = [padding_data]
        if not isinstance(padding_type, list):
            padding_type = [padding_type]
        if direction is None:
            direction = available_directions
        else:
            if not isinstance(direction, list):
                direction = [direction]
            if not all(dire in available_directions for dire in direction):
                raise Exception("Check ``axes`` input.")
        if not all(pad in available_paddings for pad in padding_type):
            raise Exception("Check ``padding_type`` input.")

        modify_props = []
        for i in range(len(padding_data)):
            modify_props.append(["NAME:" + direction[i] + " Padding Type", "Value:=", padding_type[i]])
            modify_props.append(["NAME:" + direction[i] + " Padding Data", "Value:=", padding_data[i]])

        try:
            region = self._app.get_oo_object(self._app.oeditor, region_name)
            if not region:
                self.logger.error(f"{region} does not exist.")
                return False
            create_region_name = region.GetChildNames()[0]
            self.oeditor.ChangeProperty(
                list(
                    [
                        "NAME:AllTabs",
                        list(
                            [
                                "NAME:Geometry3DCmdTab",
                                list(["NAME:PropServers", region_name + ":" + create_region_name]),
                                list(["NAME:ChangedProps"] + modify_props),
                            ]
                        ),
                    ]
                )
            )
            create_region = self._app.get_oo_object(self._app.oeditor, region_name + "/" + create_region_name)

            property_names = [lst[0].strip("NAME:") for lst in modify_props]
            actual_settings = [create_region.GetPropValue(property_name) for property_name in property_names]
            expected_settings = [lst[-1] for lst in modify_props]
            validation_errors = generate_validation_errors(property_names, expected_settings, actual_settings)

            if validation_errors:
                message = ",".join(validation_errors)
                self.logger.error(f"Settings update failed. {message}")
                return False
            return True
        except (GrpcApiError, SystemExit):
            return False

    @pyaedt_function_handler(region_cs="assignment", region_name="name")
    def change_region_coordinate_system(self, assignment="Global", name="Region"):
        """
        Change region coordinate system.

        Parameters
        ----------
        assignment : str, optional
            Region coordinate system. Default is ``Global``.
        name : str optional
            Region name. Default is ``Region``.

        Returns
        -------
        bool
            ``True`` if successful, else ``None``.

        Examples
        --------
        >>> import ansys.aedt.core
        >>> app = ansys.aedt.core.Icepak()
        >>> app.modeler.create_coordinate_system(origin=[1, 1, 1], name="NewCS")
        >>> app.modeler.change_region_coordinate_system(assignment="NewCS")
        """
        try:
            create_region_name = self._app.get_oo_object(self._app.oeditor, name).GetChildNames()[0]
            create_region = self._app.get_oo_object(self._app.oeditor, name + "/" + create_region_name)
            return create_region.SetPropValue("Coordinate System", assignment)
        except (GrpcApiError, SystemExit):
            return False
