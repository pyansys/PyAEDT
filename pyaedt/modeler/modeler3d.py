from __future__ import absolute_import  # noreorder

import datetime
import json
import os.path
import warnings

from pyaedt.generic.general_methods import _retry_ntimes
from pyaedt.generic.general_methods import generate_unique_name
from pyaedt.generic.general_methods import pyaedt_function_handler
from pyaedt.modeler.cad.Modeler import GeometryModeler
from pyaedt.modeler.cad.Primitives3D import Primitives3D
from pyaedt.modeler.geometry_operators import GeometryOperators


class Modeler3D(GeometryModeler, Primitives3D, object):
    """Provides the Modeler 3D application interface.

    This class is inherited in the caller application and is accessible through the modeler variable
    object. For example, ``hfss.modeler``.

    Parameters
    ----------
    application : :class:`pyaedt.application.Analysis3D.FieldAnalysis3D`

    Examples
    --------
    >>> from pyaedt import Hfss
    >>> hfss = Hfss()
    >>> my_modeler = hfss.modeler
    """

    def __init__(self, application):
        GeometryModeler.__init__(self, application, is3d=True)
        Primitives3D.__init__(self)

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
        :class:`pyaedt.modeler.Primitives3D.Primitives3D`

        """
        mess = "The property `primitives` is deprecated.\n"
        mess += " Use `app.modeler` directly to instantiate primitives methods."
        warnings.warn(mess, DeprecationWarning)
        return self

    @pyaedt_function_handler()
    def create_3dcomponent(
        self,
        component_file,
        component_name=None,
        variables_to_include=[],
        object_list=None,
        boundaries_list=None,
        excitation_list=None,
        included_cs=None,
        reference_cs="Global",
        is_encrypted=False,
        allow_edit=False,
        security_message="",
        password="",
        edit_password="",
        password_type="UserSuppliedPassword",
        hide_contents=False,
        replace_names=False,
        component_outline="BoundingBox",
        auxiliary_dict_file=False,
        monitor_objects=None,
        datasets=None,
        native_components=None,
    ):
        """Create a 3D component file.

        Parameters
        ----------
        component_file : str
            Full path to the A3DCOMP file.
        component_name : str, optional
            Name of the component. The default is ``None``.
        variables_to_include : list, optional
            List of variables to include. The default is ``[]``.
        object_list : list, optional
            List of object names to export. The default is all object names.
        boundaries_list : list, optional
            List of Boundaries names to export. The default is all boundaries.
        excitation_list : list, optional
            List of Excitation names to export. The default is all excitations.
        included_cs : list, optional
            List of Coordinate Systems to export. The default is all coordinate systems.
        reference_cs : str, optional
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
            The default value is an empty string.
        edit_password : str, optional
            Edit password.
            The default value is an empty string.
        password_type : str, optional
            Password type. Options are ``UserSuppliedPassword`` and ``InternalPassword``.
            The default is ``UserSuppliedPassword``.
        hide_contents : bool, optional
            Whether to hide contents. The default is ``False``.
        replace_names : bool, optional
            Whether to replace objects and material names.
            The default is ``False``.
        component_outline : str, optional
            Component outline. Value can either be ``BoundingBox`` or ``None``.
            The default is ``BoundingBox``.
        auxiliary_dict_file : bool or str, optional
            Whether to export the auxiliary file containing information about defined datasets and Icepak monitor
            objects. A destination file can be specified using a string.
            The default is ``False``.
        monitor_objects : list, optional
            List of monitor objects' names to export. The default is the names of all monitor objects. This argument is
            relevant only if ``auxiliary_dict_file`` is not set to ``False``.
        datasets : list, optional
            List of dataset names to export. The default is all datasets. This argument is relevant only if
            ``auxiliary_dict_file`` is not set to ``False``.
        native_components : list, optional
            List of native_components names to export. The default is all native_components. This argument is relevant
            only if ``auxiliary_dict_file`` is not set to ``False``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.Create3DComponent
        """
        if not component_name:
            component_name = self._app.design_name
        dt_string = datetime.datetime.now().strftime("%H:%M:%S %p %b %d, %Y")
        if password_type not in ["UserSuppliedPassword", "InternalPassword"]:
            return False
        if component_outline not in ["BoundingBox", "None"]:
            return False
        arg = [
            "NAME:CreateData",
            "ComponentName:=",
            component_name,
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
            hide_contents,
            "ReplaceNames:=",
            replace_names,
            "ComponentOutline:=",
            component_outline,
        ]
        if object_list:
            objs = object_list
        else:
            native_objs = [
                obj.name for _, v in self.modeler.user_defined_components.items() for _, obj in v.parts.items()
            ]
            objs = [obj for obj in self.object_names if obj not in native_objs]
            if not native_components and native_objs:
                self.logger.warning(
                    "Native component objects cannot be exported. Use native_components argument to"
                    " export an auxiliary dictionary file containing 3D components information"
                )
        for el in objs:
            if "CreateRegion:1" in self.oeditor.GetChildObject(el).GetChildNames():
                objs.remove(el)
        arg.append("IncludedParts:="), arg.append(objs)
        arg.append("HiddenParts:="), arg.append([])
        if included_cs:
            allcs = included_cs
        else:
            allcs = self.oeditor.GetCoordinateSystems()
        arg.append("IncludedCS:="), arg.append(allcs)
        arg.append("ReferenceCS:="), arg.append(reference_cs)
        par_description = []
        if variables_to_include:
            variables = variables_to_include
        else:
            variables = self._app._variable_manager.independent_variable_names
        for el in variables:
            par_description.append(el + ":=")
            par_description.append("")
        arg.append("IncludedParameters:="), arg.append(variables)
        variables = self._app._variable_manager.dependent_variable_names
        arg.append("IncludedDependentParameters:="), arg.append(variables)
        for el in variables:
            par_description.append(el + ":=")
            par_description.append("")
        arg.append("ParameterDescription:="), arg.append(par_description)
        arg.append("IsLicensed:="), arg.append(False)
        arg.append("LicensingDllName:="), arg.append("")
        arg.append("VendorComponentIdentifier:="), arg.append("")
        arg.append("PublicKeyFile:="), arg.append("")
        arg2 = ["NAME:DesignData"]
        if boundaries_list:
            boundaries = boundaries_list
        else:
            boundaries = self.get_boundaries_name()
        if boundaries:
            arg2.append("Boundaries:="), arg2.append(boundaries)
        if self._app.design_type == "Icepak":
            meshregions = [mr.name for mr in self._app.mesh.meshregions]
            try:
                meshregions.remove("Global")
            except:
                pass
            if meshregions:
                arg2.append("MeshRegions:="), arg2.append(meshregions)
        else:
            if excitation_list:
                excitations = excitation_list
            else:
                excitations = self._app.excitations
                if self._app.design_type == "HFSS":
                    exc = self._app.get_oo_name(self._app.odesign, "Excitations")
                    if exc and exc[0] not in self._app.excitations:
                        excitations.extend(exc)
            excitations = list(set([i.split(":")[0] for i in excitations]))
            if excitations:
                arg2.append("Excitations:="), arg2.append(excitations)
        meshops = [el.name for el in self._app.mesh.meshoperations]
        arg2.append("MeshOperations:="), arg2.append(meshops)
        arg3 = ["NAME:ImageFile", "ImageFile:=", ""]
        if auxiliary_dict_file:
            if isinstance(auxiliary_dict_file, bool):
                auxiliary_dict_file = component_file + ".json"
            cachesettings = {
                prop: getattr(self._app.configurations.options, prop)
                for prop in vars(self._app.configurations.options)
                if prop.startswith("_export_")
            }
            self._app.configurations.options.unset_all_export()
            self._app.configurations.options.export_monitor = True
            self._app.configurations.options.export_datasets = True
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
            with open(configfile) as f:
                config_dict = json.load(f)
            out_dict = {}
            if monitor_objects:
                out_dict["monitor"] = config_dict["monitor"]
                for i in list(out_dict["monitor"]):
                    if i not in monitor_objects:
                        del out_dict["monitor"][i]
                    else:
                        if out_dict["monitor"][i]["Type"] in ["Object", "Surface"]:
                            out_dict["monitor"][i]["ID"] = self._app.modeler.get_obj_id(out_dict["monitor"][i]["ID"])
            if datasets:
                out_dict["datasets"] = config_dict["datasets"]
                for i in list(out_dict["datasets"]):
                    if i not in datasets:
                        del out_dict["datasets"][i]
                out_dict["datasets"] = config_dict["datasets"]
            if native_components:
                out_dict["native components"] = {}
                coordinatesystems_set = set()
                for _, nc in self._app.native_components.items():
                    nc_name = nc.props["SubmodelDefinitionName"]
                    nc_props = dict(nc.props).copy()
                    nc_type = nc.props["NativeComponentDefinitionProvider"]["Type"]
                    if (
                        nc_type == "PCB"
                        and nc_props["NativeComponentDefinitionProvider"]["DefnLink"]["Project"] == "This Project*"
                    ):
                        nc_props["NativeComponentDefinitionProvider"]["DefnLink"]["Project"] = self._app.project_file
                    CSs = [
                        v.target_coordinate_system
                        for i, v in self._app.modeler.user_defined_components.items()
                        if v.definition_name == nc_name
                        and "Target Coordinate System" in self._app.oeditor.GetChildObject(i).GetPropNames()
                    ]
                    out_dict["native components"][nc_name] = {"Type": nc_type, "Props": nc_props, "CS": CSs}
                    for cs in CSs:
                        while cs != "Global":
                            coordinatesystems_set.update(cs)
                            cs = config_dict["coordinatesystems"][cs]["Reference CS"]
                if config_dict.get("coordinatesystems", None):
                    out_dict["coordinatesystems"] = config_dict["coordinatesystems"]
            with open(auxiliary_dict_file, "w") as outfile:
                json.dump(out_dict, outfile)
        return _retry_ntimes(3, self.oeditor.Create3DComponent, arg, arg2, component_file, arg3)

    @pyaedt_function_handler()
    def create_coaxial(
        self,
        startingposition,
        axis,
        innerradius=1,
        outerradius=2,
        dielradius=1.8,
        length=10,
        matinner="copper",
        matouter="copper",
        matdiel="teflon_based",
    ):
        """Create a coaxial.

        Parameters
        ----------
        startingposition : list
            List of ``[x, y, z]`` coordinates for the starting position.
        axis : int
            Coordinate system AXIS (integer ``0`` for X, ``1`` for Y, ``2`` for Z) or
            the :class:`Application.CoordinateSystemAxis` enumerator.
        innerradius : float, optional
            Inner coax radius. The default is ``1``.
        outerradius : float, optional
            Outer coax radius. The default is ``2``.
        dielradius : float, optional
            Dielectric coax radius. The default is ``1.8``.
        length : float, optional
            Coaxial length. The default is ``10``.
        matinner : str, optional
            Material for the inner coaxial. The default is ``"copper"``.
        matouter : str, optional
            Material for the outer coaxial. The default is ``"copper"``.
        matdiel : str, optional
            Material for the dielectric. The default is ``"teflon_based"``.

        Returns
        -------
        tuple
            Contains the inner, outer, and dielectric coax as
            :class:`pyaedt.modeler.Object3d.Object3d` objects.

        References
        ----------

        >>> oEditor.CreateCylinder
        >>> oEditor.AssignMaterial


        Examples
        --------

        This example shows how to create a Coaxial Along X Axis waveguide.

        >>> from pyaedt import Hfss
        >>> app = Hfss()
        >>> position = [0,0,0]
        >>> coax = app.modeler.create_coaxial(
        ...    position, app.AXIS.X, innerradius=0.5, outerradius=0.8, dielradius=0.78, length=50
        ... )

        """
        if not (outerradius > dielradius and dielradius > innerradius):
            raise ValueError("Error in coaxial radius.")
        inner = self.create_cylinder(axis, startingposition, innerradius, length, 0)
        outer = self.create_cylinder(axis, startingposition, outerradius, length, 0)
        diel = self.create_cylinder(axis, startingposition, dielradius, length, 0)
        self.subtract(outer, inner)
        self.subtract(outer, diel)
        inner.material_name = matinner
        outer.material_name = matouter
        diel.material_name = matdiel

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
            the :class:`Application.CoordinateSystemAxis` enumerator.
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
        tuple
            Tuple of :class:`Object3d <pyaedt.modeler.Object3d.Object3d>`
            objects created by the waveguide.

        References
        ----------

        >>> oEditor.CreateBox
        >>> oEditor.AssignMaterial


        Examples
        --------

        This example shows how to create a WG9 waveguide.

        >>> from pyaedt import Hfss
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
            wgwidth = WG[wgmodel][0]
            wgheight = WG[wgmodel][1]
            if not wg_thickness:
                wg_thickness = wgheight / 20
            if parametrize_h:
                self._app[wgmodel + "_H"] = self._arg_with_dim(wgheight)
                h = wgmodel + "_H"
                hb = wgmodel + "_H + 2*" + self._arg_with_dim(wg_thickness)
            else:
                h = self._arg_with_dim(wgheight)
                hb = self._arg_with_dim(wgheight) + " + 2*" + self._arg_with_dim(wg_thickness)

            if parametrize_w:
                self._app[wgmodel + "_W"] = self._arg_with_dim(wgwidth)
                w = wgmodel + "_W"
                wb = wgmodel + "_W + " + self._arg_with_dim(2 * wg_thickness)
            else:
                w = self._arg_with_dim(wgwidth)
                wb = self._arg_with_dim(wgwidth) + " + 2*" + self._arg_with_dim(wg_thickness)
            if wg_direction_axis == self._app.AXIS.Z:
                airbox = self.create_box(origin, [w, h, wg_length])

                if type(wg_thickness) is str:
                    origin[0] = str(origin[0]) + "-" + wg_thickness
                    origin[1] = str(origin[1]) + "-" + wg_thickness
                else:
                    origin[0] -= wg_thickness
                    origin[1] -= wg_thickness

            elif wg_direction_axis == self._app.AXIS.Y:
                airbox = self.create_box(origin, [w, wg_length, h])

                if type(wg_thickness) is str:
                    origin[0] = str(origin[0]) + "-" + wg_thickness
                    origin[2] = str(origin[2]) + "-" + wg_thickness
                else:
                    origin[0] -= wg_thickness
                    origin[2] -= wg_thickness
            else:
                airbox = self.create_box(origin, [wg_length, w, h])

                if type(wg_thickness) is str:
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

            return wgbox, p1, p2
        else:
            return None

    @pyaedt_function_handler()
    def objects_in_bounding_box(self, bounding_box, check_solids=True, check_lines=True, check_sheets=True):
        """Given a bounding box checks if objects, sheets and lines are inside it.

        Parameters
        ----------
        bounding_box : list.
            List of coordinates of bounding box vertices.
        check_solids : bool, optional.
            Check solid objects.
        check_lines : bool, optional.
            Check line objects.
        check_sheets : bool, optional.
            Check sheet objects.

        Returns
        -------
        list of :class:`pyaedt.modeler.object3d`
        """

        if len(bounding_box) != 6:
            raise ValueError("Bounding box list must have dimension 6.")

        objects = []

        if check_solids:
            for obj in self.solid_objects:
                if (
                    bounding_box[3] <= obj.bounding_box[0] <= bounding_box[0]
                    and bounding_box[4] <= obj.bounding_box[1] <= bounding_box[1]
                    and bounding_box[5] <= obj.bounding_box[2] <= bounding_box[2]
                    and bounding_box[3] <= obj.bounding_box[3] <= bounding_box[0]
                    and bounding_box[4] <= obj.bounding_box[4] <= bounding_box[1]
                    and bounding_box[5] <= obj.bounding_box[5] <= bounding_box[2]
                ):
                    objects.append(obj)

        if check_lines:
            for obj in self.line_objects:
                if (
                    bounding_box[3] <= obj.bounding_box[0] <= bounding_box[0]
                    and bounding_box[4] <= obj.bounding_box[1] <= bounding_box[1]
                    and bounding_box[5] <= obj.bounding_box[2] <= bounding_box[2]
                    and bounding_box[3] <= obj.bounding_box[3] <= bounding_box[0]
                    and bounding_box[4] <= obj.bounding_box[4] <= bounding_box[1]
                    and bounding_box[5] <= obj.bounding_box[5] <= bounding_box[2]
                ):
                    objects.append(obj)

        if check_sheets:
            for obj in self.sheet_objects:
                if (
                    bounding_box[3] <= obj.bounding_box[0] <= bounding_box[0]
                    and bounding_box[4] <= obj.bounding_box[1] <= bounding_box[1]
                    and bounding_box[5] <= obj.bounding_box[2] <= bounding_box[2]
                    and bounding_box[3] <= obj.bounding_box[3] <= bounding_box[0]
                    and bounding_box[4] <= obj.bounding_box[4] <= bounding_box[1]
                    and bounding_box[5] <= obj.bounding_box[5] <= bounding_box[2]
                ):
                    objects.append(obj)

        return objects

    @pyaedt_function_handler()
    def import_nastran(self, file_path, import_lines=True, lines_thickness=0):
        """Import Nastran file into 3D Modeler by converting it to stl and reading it.

        Parameters
        ----------
        file_path : str
            Path to .nas file.
        import_lines : bool, optional
            Whether to import the lines or only triangles. Default is ``True``.
        lines_thickness : float, optional
            Whether to thicken lines after creation and it's default value.
            Every line will be parametrized with a design variable called ``xsection_linename``.

        Returns
        -------
        List of :class:`pyaedt.modeler.Object3d.Object3d`
        """
        nas_to_dict = {"Points": {}, "PointsId": {}, "Triangles": {}, "Lines": {}}
        with open(file_path, "r") as f:
            lines = f.read().splitlines()
            id = 0
            for line in lines:
                line_split = [line[i : i + 8] for i in range(0, len(line), 8)]
                if len(line_split) < 5:
                    continue
                if line_split[0].startswith("GRID"):
                    try:
                        n_1_3 = line[24:48]
                        import re

                        out = re.findall("^.{24}(.{8})(.{8})(.{8})", line)[0]
                        n1 = out[0].replace(".-", ".e-").strip()
                        n2 = out[1].replace(".-", ".e-").strip()
                        n3 = out[2].replace(".-", ".e-").strip()

                        if "-" in n1[1:]:
                            n1 = n1[0] + n1[1:].replace("-", "e-")
                        n1 = float(n1)
                        if "-" in n2[1:]:
                            n2 = n2[0] + n2[1:].replace("-", "e-")
                        n2 = float(n2)
                        if "-" in n3[1:]:
                            n3 = n3[0] + n3[1:].replace("-", "e-")
                        n3 = float(n3)

                        nas_to_dict["Points"][int(line_split[1])] = [n1, n2, n3]
                        nas_to_dict["PointsId"][int(line_split[1])] = id
                        id += 1
                    except:
                        pass
                elif line_split[0].startswith("CTRIA3"):
                    if int(line_split[2]) in nas_to_dict["Triangles"]:
                        nas_to_dict["Triangles"][int(line_split[2])].append(
                            [
                                int(line_split[3]),
                                int(line_split[4]),
                                int(line_split[5]),
                            ]
                        )
                    else:
                        nas_to_dict["Triangles"][int(line_split[2])] = [
                            [
                                int(line_split[3]),
                                int(line_split[4]),
                                int(line_split[5]),
                            ]
                        ]
                elif line_split[0].startswith("CROD") or line_split[0].startswith("CBEAM"):
                    if int(line_split[2]) in nas_to_dict["Lines"]:
                        nas_to_dict["Lines"][int(line_split[2])].append([int(line_split[3]), int(line_split[4])])
                    else:
                        nas_to_dict["Lines"][int(line_split[2])] = [[int(line_split[3]), int(line_split[4])]]
        objs_before = [i for i in self.object_names]
        f = open(os.path.join(self._app.working_directory, self._app.design_name + "_test.stl"), "w")
        f.write("solid PyaedtStl\n")
        for triangles in nas_to_dict["Triangles"].values():
            for triangle in triangles:
                try:
                    points = [nas_to_dict["Points"][id] for id in triangle]
                except KeyError:
                    continue
                fc = GeometryOperators.get_polygon_centroid(points)
                v1 = points[0]
                v2 = points[1]
                cv1 = GeometryOperators.v_points(fc, v1)
                cv2 = GeometryOperators.v_points(fc, v2)
                if cv2[0] == cv1[0] == 0.0 and cv2[1] == cv1[1] == 0.0:
                    n = [0, 0, 1]
                elif cv2[0] == cv1[0] == 0.0 and cv2[2] == cv1[2] == 0.0:
                    n = [0, 1, 0]
                elif cv2[1] == cv1[1] == 0.0 and cv2[2] == cv1[2] == 0.0:
                    n = [1, 0, 0]
                else:
                    n = GeometryOperators.v_cross(cv1, cv2)
                normal = GeometryOperators.normalize_vector(n)
                if normal:
                    f.write(" facet normal {} {} {}\n".format(normal[0], normal[1], normal[2]))
                    f.write("  outer loop\n")
                    f.write("   vertex {} {} {}\n".format(points[0][0], points[0][1], points[0][2]))
                    f.write("   vertex {} {} {}\n".format(points[1][0], points[1][1], points[1][2]))
                    f.write("   vertex {} {} {}\n".format(points[2][0], points[2][1], points[2][2]))
                    f.write("  endloop\n")
                    f.write(" endfacet\n")

        f.write("endsolid\n")
        f.close()
        self.import_3d_cad(os.path.join(self._app.working_directory, self._app.design_name + "_test.stl"))
        if not import_lines:
            return True

        for line_name, lines in nas_to_dict["Lines"].items():
            if lines_thickness:
                self._app["x_section_{}".format(line_name)] = lines_thickness
            polys = []
            id = 0
            for line in lines:
                try:
                    points = [nas_to_dict["Points"][line[0]], nas_to_dict["Points"][line[1]]]
                except KeyError:
                    continue
                if lines_thickness:
                    polys.append(
                        self.create_polyline(
                            points,
                            name="Poly_{}_{}".format(line_name, id),
                            xsection_type="Circle",
                            xsection_width="x_section_{}".format(line_name),
                            xsection_num_seg=6,
                        )
                    )
                else:
                    polys.append(self.create_polyline(points, name="Poly_{}_{}".format(line_name, id)))
                id += 1

            if len(polys) > 1:
                out_poly = self.unite(polys, purge=not lines_thickness)
                if not lines_thickness and out_poly:
                    self.generate_object_history(out_poly)

        objs_after = [i for i in self.object_names]
        new_objects = [self[i] for i in objs_after if i not in objs_before]
        return new_objects

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

        """
        from pyaedt.modeler.advanced_cad.oms import BuildingsPrep
        from pyaedt.modeler.advanced_cad.oms import RoadPrep
        from pyaedt.modeler.advanced_cad.oms import TerrainPrep

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

        with open(json_path, "w", encoding="utf-8") as f:
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
                obj_names = [i for i in self.object_names]
                self.import_3d_cad(
                    parts_dict[part]["file_name"],
                    create_lightweigth_part=create_lightweigth_part,
                )
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
