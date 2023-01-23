import csv
import ntpath
import os
import warnings

from pyaedt import settings
from pyaedt.application.Analysis import Analysis
from pyaedt.generic.configurations import Configurations
from pyaedt.generic.general_methods import _retry_ntimes
from pyaedt.generic.general_methods import generate_unique_name
from pyaedt.generic.general_methods import is_ironpython
from pyaedt.generic.general_methods import open_file
from pyaedt.generic.general_methods import pyaedt_function_handler
from pyaedt.modeler.advanced_cad.stackup_3d import Stackup3D
from pyaedt.modeler.modeler2d import Modeler2D
from pyaedt.modeler.modeler3d import Modeler3D
from pyaedt.modules.Mesh import Mesh
from pyaedt.modules.MeshIcepak import IcepakMesh

if is_ironpython:
    from pyaedt.modules.PostProcessor import PostProcessor
else:
    from pyaedt.modules.AdvancedPostProcessing import PostProcessor


class FieldAnalysis3D(Analysis, object):
    """Manages 3D field analysis setup in HFSS, Maxwell 3D, and Q3D.

    This class is automatically initialized by an application call from one of
    the 3D tools. See the application function for parameter definitions.

    Parameters
    ----------
    application : str
        3D application that is to initialize the call.
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
        Version of AEDT  to use. The default is ``None``, in which case
        the active version or latest installed version is used.
    non_graphical : bool, optional
        Whether to run AEDT in non-graphical mode. The default
        is ``False``, in which case AEDT is launched in the graphical mode.
    new_desktop_session : bool, optional
        Whether to launch an instance of AEDT in a new thread, even if
        another instance of the ``specified_version`` is active on the
        machine. The default is ``True``.
    close_on_exit : bool, optional
        Whether to release AEDT on exit. The default is ``False``.
    student_version : bool, optional
        Whether to enable the student version of AEDT. The default
        is ``False``.
    aedt_process_id : int, optional
        Only used when ``new_desktop_session = False``, specifies by process ID which instance
        of Electronics Desktop to point PyAEDT at.
    """

    def __init__(
        self,
        application,
        projectname,
        designname,
        solution_type,
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
        Analysis.__init__(
            self,
            application,
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
        self._modeler = Modeler2D(self) if application in ["Maxwell 2D", "2D Extractor"] else Modeler3D(self)
        self._mesh = IcepakMesh(self) if application == "Icepak" else Mesh(self)
        self._post = PostProcessor(self)
        self._configurations = Configurations(self)

    @property
    def configurations(self):
        """Property to import and export configuration files.

        Returns
        -------
        :class:`pyaedt.generic.configurations.Configurations`
        """
        return self._configurations

    @property
    def modeler(self):
        """Modeler.

        Returns
        -------
        :class:`pyaedt.modeler.modeler3d.Modeler3D` or :class:`pyaedt.modeler.modeler2d.Modeler2D`
        """
        return self._modeler

    @property
    def mesh(self):
        """Mesh.

        Returns
        -------
        :class:`pyaedt.modules.Mesh.Mesh` or :class:`pyaedt.modules.MeshIcepak.IcepakMesh`
        """
        return self._mesh

    @property
    def components3d(self):
        """3D components.

        Returns
        -------
        dict
            Dictionary of 3D components with their absolute paths.

        """
        components_dict = {}

        # Define libraries where 3d components may exist.
        # libs = [syslib, userlib]

        libs = [
            os.path.join(self.syslib, "3DComponents", self._design_type),
            os.path.join(self.userlib, "3DComponents", self._design_type),
        ]

        for lib in libs:
            if os.path.exists(lib):
                listfiles = []
                for root, _, files in os.walk(lib):
                    for file in files:
                        if file.endswith(".a3dcomp"):
                            listfiles.append(os.path.join(root, file))
                # listfiles = glob.glob(syspath + "/**/*.a3dcomp", recursive=True)
                for el in listfiles:
                    head, tail = ntpath.split(el)
                    components_dict[tail[:-8]] = el
        return components_dict

    @pyaedt_function_handler()
    def plot(
        self,
        objects=None,
        show=True,
        export_path=None,
        plot_as_separate_objects=True,
        plot_air_objects=True,
        force_opacity_value=None,
        clean_files=False,
        view="isometric",
    ):
        """Plot the model or a subset of objects.

        Parameters
        ----------
        objects : list, optional
            List of objects to plot. The default is ``None``, in which case all objects
            are exported.
        show : bool, optional
            Whether to show the plot after generation. The default is ``True``. If
            ``False``, the generated class is returned for more customization before
            plot generation.
        export_path : str, optional
            If available, an image is saved to file. If ``None`` no image will be saved.
        plot_as_separate_objects : bool, optional
            Whether to plot each object separately. The default is ``True``, which may
            require more time to export from AEDT.
        plot_air_objects : bool, optional
            Whether to also plot air and vacuum objects. The default is ``True``.
        force_opacity_value : float, optional
            Opacity value between 0 and 1 to applied to all of the model. The
            default is ``None``, which means the AEDT opacity is applied to each object.
        clean_files : bool, optional
            Whether to clean created files after plot generation. The default is ``False``,
            which means that the cache is maintained in the model object that is returned.
        view : str, optional
           View to export. Options are ``"isometric"``, ``"xy"``, ``"xz"``, ``"yz"``.
           The default is ``"isometric"``.

        Returns
        -------
        :class:`pyaedt.generic.plot.ModelPlotter`
            Model Object.
        """
        if is_ironpython:
            self.logger.warning("Plot is available only on CPython")
        elif self._aedt_version < "2021.2":
            self.logger.warning("Plot is supported from AEDT 2021 R2.")
        else:
            return self.post.plot_model_obj(
                objects=objects,
                show=show,
                export_path=export_path,
                plot_as_separate_objects=plot_as_separate_objects,
                plot_air_objects=plot_air_objects,
                force_opacity_value=force_opacity_value,
                clean_files=clean_files,
                view=view,
            )

    @pyaedt_function_handler()
    def export_mesh_stats(self, setup_name, variation_string="", mesh_path=None):
        """Export mesh statistics to a file.

        Parameters
        ----------
        setup_name : str
            Setup name.
        variation_string : str, optional
            Variation list. The default is ``""``.
        mesh_path : str, optional
            Full path to the mesh statistics file. The default is ``None``, in which
            caswe the working directory is used.

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
        self.odesign.ExportMeshStats(setup_name, variation_string, mesh_path)
        return mesh_path

    @pyaedt_function_handler()
    def get_components3d_vars(self, component3dname):
        """Read the A3DCOMP file and check for variables.

        Parameters
        ----------
        component3dname :
            Name of the 3D component, which must be in the ``syslib`` or ``userlib`` directory. Otherwise,
            you must specify the full absolute path to the AEDCOMP file with the file name and the extension.

        Returns
        -------
        dict
            Dictionary of variables in the A3DCOMP file.

        """
        vars = {}
        if component3dname not in self.components3d:
            aedt_fh = open_file(component3dname, "rb")
            if aedt_fh:
                temp = aedt_fh.read().splitlines()
                _all_lines = []
                for line in temp:
                    try:
                        _all_lines.append(line.decode("utf-8").lstrip("\t"))
                    except UnicodeDecodeError:
                        break
                for line in _all_lines:
                    if "VariableProp(" in line:
                        line_list = line.split("'")
                        vars[line_list[1]] = line_list[len(line_list) - 2]
                aedt_fh.close()
                return vars
            else:
                return False
        with open_file(self.components3d[component3dname], "rb") as aedt_fh:
            temp = aedt_fh.read().splitlines()
        _all_lines = []
        for line in temp:
            try:
                _all_lines.append(line.decode("utf-8").lstrip("\t"))
            except UnicodeDecodeError:
                break
        for line in _all_lines:
            if "VariableProp(" in line:
                line_list = line.split("'")
                vars[line_list[1]] = line_list[len(line_list) - 2]
        return vars

    @pyaedt_function_handler()
    def get_property_value(self, objectname, property, type=None):
        """Retrieve a property value.

        Parameters
        ----------
        objectname : str
            Name of the object.
        property : str
            Name of the property.
        type : str, optional
            Type of the property. Options are ``"boundary"``, ``"excitation"``,
            ``"setup",`` and ``"mesh"``. The default is ``None``.

        Returns
        -------
        type
            Value of the property.

        References
        ----------

        >>> oDesign.GetPropertyValue
        """

        boundary = {"HFSS": "HfssTab", "Icepak": "Icepak", "Q3D": "Q3D", "Maxwell3D": "Maxwell3D"}
        excitation = {"HFSS": "HfssTab", "Icepak": "Icepak", "Q3D": "Q3D", "Maxwell3D": "Maxwell3D"}
        setup = {"HFSS": "HfssTab", "Icepak": "Icepak", "Q3D": "General", "Maxwell3D": "General"}
        mesh = {"HFSS": "MeshSetupTab", "Icepak": "Icepak", "Q3D": "Q3D", "Maxwell3D": "Maxwell3D"}
        all = {
            "HFSS": ["HfssTab", "MeshSetupTab"],
            "Icepak": ["Icepak"],
            "Q3D": ["Q3D", "General"],
            "Maxwell3D": ["Maxwell3D", "General"],
        }
        if type == "Boundary":
            propserv = boundary[self._design_type]
            val = _retry_ntimes(10, self.odesign.GetPropertyValue, propserv, objectname, property)
            return val
        elif type == "Setup":
            propserv = setup[self._design_type]
            val = _retry_ntimes(10, self.odesign.GetPropertyValue, propserv, objectname, property)
            return val

        elif type == "Excitation":
            propserv = excitation[self._design_type]
            val = _retry_ntimes(10, self.odesign.GetPropertyValue, propserv, objectname, property)
            return val

        elif type == "Mesh":
            propserv = mesh[self._design_type]
            val = _retry_ntimes(10, self.odesign.GetPropertyValue, propserv, objectname, property)
            return val
        else:
            propservs = all[self._design_type]
            for propserv in propservs:
                properties = list(self.odesign.GetProperties(propserv, objectname))
                if property in properties:
                    val = _retry_ntimes(10, self.odesign.GetPropertyValue, propserv, objectname, property)
                    return val
        return None

    @pyaedt_function_handler()
    def copy_solid_bodies_from(self, design, object_list=None, no_vacuum=True, no_pec=True, include_sheets=False):
        """Copy a list of objects and user defined models from one design to the active design.
        If user defined models are selected, the project will be saved automatically.

        Parameters
        ----------
        design :
            Starting application object. For example, ``hfss1= HFSS3DLayout``.
        object_list : list, optional
            List of objects and user defined components to copy. The default is ``None``.
        no_vacuum : bool, optional
            Whether to include vacuum objects for the copied objects.
            The default is ``True``.
        no_pec :
            Whether to include pec objects for the copied objects. The
            default is ``True``.
        include_sheets :
            Whether to include sheets for the copied objects. The
            default is ``False``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.Copy
        >>> oEditor.Paste
        """
        body_list = design.modeler.solid_names
        udc_list = design.modeler.user_defined_component_names
        original_design_type = design.design_type
        dest_design_type = self.design_type
        new_udc_list = []
        if include_sheets:
            body_list += design.modeler.sheet_names
        if udc_list:
            for udc in udc_list:
                if (
                    original_design_type != dest_design_type
                    and not design.modeler.user_defined_components[udc].is3dcomponent
                    or original_design_type == dest_design_type
                ):
                    new_udc_list.append(udc)
                for part_id in design.modeler.user_defined_components[udc].parts:
                    if design.modeler.user_defined_components[udc].parts[part_id].name in body_list:
                        body_list.remove(design.modeler.user_defined_components[udc].parts[part_id].name)

        selection_list = []
        udc_selection = []
        material_properties = design.modeler.objects
        selections = self.modeler.convert_to_selections(object_list, True)

        if selections:
            selection_list = [i for i in selections if i in body_list]
            for udc in new_udc_list:
                if udc in selections:
                    udc_selection.append(udc)
        else:
            for body in body_list:
                include_object = True
                for key, val in material_properties.items():
                    if val.name == body:
                        if no_vacuum and val.material_name.lower() == "vacuum":
                            include_object = False
                        if no_pec and val.material_name == "pec":
                            include_object = False
                if include_object:
                    selection_list.append(body)
            for udm in new_udc_list:
                udc_selection.append(udm)
        selection_list = selection_list + udc_selection
        design.modeler.oeditor.Copy(["NAME:Selections", "Selections:=", ",".join(selection_list)])
        self.modeler.oeditor.Paste()
        if udc_selection:
            self.save_project()
            self._project_dictionary = None
        self.modeler.refresh_all_ids()
        return True

    @pyaedt_function_handler()
    def export3DModel(self, fileName, filePath, fileFormat=".step", object_list=[], removed_objects=[]):
        """Export the 3D model.

        .. deprecated:: 0.5.0
           Use :func:`pyaedt.application.Analysis3D.modeler.export_3d_model` instead.

        """
        warnings.warn("`export3DModel` is deprecated. Use `export_3d_model` instead.", DeprecationWarning)
        return self.export_3d_model(fileName, filePath, fileFormat, object_list, removed_objects)

    @pyaedt_function_handler()
    def export_3d_model(
        self, file_name="", file_path="", file_format=".step", object_list=None, removed_objects=None, **kwargs
    ):
        """Export the 3D model.

        Parameters
        ----------
        file_name : str, optional
            Name of the file.
        file_path : str, optional
            Path for the file.
        file_format : str, optional
            Format of the file. The default is ``".step"``.
        object_list : list, optional
            List of objects to export. The default is ``None``.
        removed_objects : list, optional
            The default is ``None``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.Export
        """
        if "fileName" in kwargs:
            warnings.warn(
                "`fileName` is deprecated. Use `file_name` instead.",
                DeprecationWarning,
            )

            file_name = kwargs["fileName"]
        if "filePath" in kwargs:
            warnings.warn(
                "`filePath` is deprecated. Use `file_path` instead.",
                DeprecationWarning,
            )

            file_path = kwargs["filePath"]
        if "fileFormat" in kwargs:
            warnings.warn(
                "`fileFormat` is deprecated. Use `file_format` instead.",
                DeprecationWarning,
            )

            file_format = kwargs["fileFormat"]
        if not file_name:
            file_name = self.project_name + "_" + self.design_name
        if not file_path:
            file_path = self.working_directory
        if object_list is None:
            object_list = []
        if removed_objects is None:
            removed_objects = []

        if not object_list:
            allObjects = self.modeler.object_names
            if removed_objects:
                for rem in removed_objects:
                    allObjects.remove(rem)
            else:
                if "Region" in allObjects:
                    allObjects.remove("Region")
        else:
            allObjects = object_list[:]

        self.logger.debug("Exporting {} objects".format(len(allObjects)))
        major = -1
        minor = -1
        # actual version supported by AEDT is 29.0
        if file_format in [".sm3", ".sat", ".sab"]:
            major = 29
            minor = 0
        stringa = ",".join(allObjects)
        arg = [
            "NAME:ExportParameters",
            "AllowRegionDependentPartSelectionForPMLCreation:=",
            True,
            "AllowRegionSelectionForPMLCreation:=",
            True,
            "Selections:=",
            stringa,
            "File Name:=",
            os.path.join(file_path, file_name + file_format).replace("\\", "/"),
            "Major Version:=",
            major,
            "Minor Version:=",
            minor,
        ]

        self.modeler.oeditor.Export(arg)
        return True

    @pyaedt_function_handler()
    def get_all_sources(self):
        """Retrieve all setup sources.

        Returns
        -------
        list of str
            List of all setup sources.

        References
        ----------

        >>> oModule.GetAllSources
        """
        return list(self.osolution.GetAllSources())

    @pyaedt_function_handler()
    def set_source_context(self, sources, number_of_modes=1):
        """Set the source context.

        Parameters
        ----------
        sources : list
            List of source names.
        number_of_modes : int, optional
            Number of modes. The default is ``1``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oModule.SetSourceContexts
        """

        contexts = []
        for s in sources:
            value = s
            if number_of_modes > 0:
                for i in range(number_of_modes):
                    value += ":" + str(i + 1)
            contexts.append(value)  # use one based indexing
        self.osolution.SetSourceContexts(contexts)
        return True

    @pyaedt_function_handler()
    def assign_material(self, obj, mat):
        """Assign a material to one or more objects.

        Parameters
        ----------
        obj : str, list
            One or more objects to assign materials to.
        mat : str
            Material to assign. If this material is not present, it is
            created.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.AssignMaterial

        Examples
        --------
        The method :func:`assign_material` is used to assign a material to a list of objects.

        Open a design and create the objects.

        >>> from pyaedt import Hfss
        >>> hfss = Hfss()
        >>> box1 = hfss.modeler.create_box([10, 10, 10], [4, 5, 5])
        >>> box2 = hfss.modeler.create_box([0, 0, 0], [2, 3, 4])
        >>> cylinder1 = hfss.modeler.create_cylinder(cs_axis="X", position=[5, 0, 0], radius=1, height=20)
        >>> cylinder2 = hfss.modeler.create_cylinder(cs_axis="Z", position=[0, 0, 5], radius=1, height=10)

        Assign the material ``"copper"`` to all the objects.

        >>> objects_list = [box1, box2, cylinder1, cylinder2]
        >>> hfss.assign_material(objects_list, "copper")

        The method also accepts a list of object names.

        >>> obj_names_list = [box1.name, box2.name, cylinder1.name, cylinder2.name]
        >>> hfss.assign_material(obj_names_list, "aluminum")
        """
        matobj = None
        selections = self.modeler.convert_to_selections(obj, True)

        if mat.lower() in self.materials.material_keys:
            matobj = self.materials.material_keys[mat.lower()]
        elif self.materials._get_aedt_case_name(mat) or settings.remote_api:
            matobj = self.materials._aedmattolibrary(mat)
        if matobj:
            if self.design_type == "HFSS":
                solve_inside = matobj.is_dielectric()
            else:
                solve_inside = True
            slice_sel = min(50, len(selections))
            num_objects = len(selections)
            remaining = num_objects
            while remaining >= 1:
                objs = selections[:slice_sel]
                szSelections = self.modeler.convert_to_selections(objs)
                vArg1 = [
                    "NAME:Selections",
                    "AllowRegionDependentPartSelectionForPMLCreation:=",
                    True,
                    "AllowRegionSelectionForPMLCreation:=",
                    True,
                    "Selections:=",
                    szSelections,
                ]
                vArg2 = [
                    "NAME:Attributes",
                    "MaterialValue:=",
                    '"{}"'.format(matobj.name),
                    "SolveInside:=",
                    solve_inside,
                    "ShellElement:=",
                    False,
                    "ShellElementThickness:=",
                    "nan ",
                    "IsMaterialEditable:=",
                    True,
                    "UseMaterialAppearance:=",
                    True,
                    "IsLightweight:=",
                    False,
                ]
                self.oeditor.AssignMaterial(vArg1, vArg2)
                for el in objs:
                    self.modeler[el]._material_name = matobj.name
                    self.modeler[el]._color = matobj.material_appearance
                    self.modeler[el]._solve_inside = solve_inside
                remaining -= slice_sel
                if remaining > 0:
                    selections = selections[slice_sel:]

            return True
        else:
            self.logger.error("Material does not exist.")
            return False

    @pyaedt_function_handler()
    def get_all_conductors_names(self):
        """Retrieve all conductors in the active design.

        Returns
        -------
        list of str
            List of all conductors.

        References
        ----------

        >>> oEditor.GetObjectsByMaterial
        """
        if len(self.modeler.objects) != len(self.modeler.object_names):
            self.modeler.refresh_all_ids()
        cond = self.materials.conductors
        obj_names = []
        for mat in cond:
            obj_names.extend(self.modeler.get_objects_by_material(mat))
            obj_names.extend(self.modeler.get_objects_by_material(self.materials[mat].name))
        return list(set(obj_names))

    @pyaedt_function_handler()
    def get_all_dielectrics_names(self):
        """Retrieve all dielectrics in the active design.

        Returns
        -------
        list of str
           List of all dielectrics.

        References
        ----------
        >>> oEditor.GetObjectsByMaterial
        """
        if len(self.modeler.objects) != len(self.modeler.object_names):
            self.modeler.refresh_all_ids()
        diel = self.materials.dielectrics
        obj_names = []
        for mat in diel:
            obj_names.extend(self.modeler.get_objects_by_material(mat))
            obj_names.extend(self.modeler.get_objects_by_material(self.materials[mat].name))
        return list(set(obj_names))

    @pyaedt_function_handler()
    def _create_dataset_from_sherlock(self, material_string, property_name="Mass_Density"):
        mats = material_string.split(",")
        mat_temp = [[i.split("@")[0], i.split("@")[1]] for i in mats]
        nominal_id = int(len(mat_temp) / 2)
        nominal_val = float(mat_temp[nominal_id - 1][0])
        ds_name = generate_unique_name(property_name)
        self.create_dataset(
            ds_name,
            [float(i[1].replace("C", "").replace("K", "").replace("F", "")) for i in mat_temp],
            [float(i[0]) / nominal_val for i in mat_temp],
        )
        return nominal_val, "$" + ds_name

    @pyaedt_function_handler()
    def assignmaterial_from_sherlock_files(self, csv_component, csv_material):
        """Assign material to objects in a design based on a CSV file obtained from Sherlock.

        Parameters
        ----------
        csv_component :  str
            Name of the CSV file containing the component properties, including the
            material name.
        csv_material : str
            Name of the CSV file containing the material properties.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.AssignMaterial
        """
        with open_file(csv_material) as csvfile:
            csv_input = csv.reader(csvfile)
            material_header = next(csv_input)
            data = list(csv_input)
            k = 0
            material_data = {}
            for el in material_header:
                material_data[el] = [i[k] for i in data]
                k += 1
        with open_file(csv_component) as csvfile:
            csv_input = csv.reader(csvfile)
            component_header = next(csv_input)
            data = list(csv_input)
            k = 0
            component_data = {}
            for el in component_header:
                component_data[el] = [i[k] for i in data]
                k += 1
        all_objs = self.modeler.object_names
        i = 0
        for mat in material_data["Name"]:
            list_mat_obj = [
                "COMP_" + rd for rd, md in zip(component_data["Ref Des"], component_data["Material"]) if md == mat
            ]
            list_mat_obj += [rd for rd, md in zip(component_data["Ref Des"], component_data["Material"]) if md == mat]
            list_mat_obj = [mo for mo in list_mat_obj if mo in all_objs]
            if list_mat_obj:
                newmat = self.materials.checkifmaterialexists(mat)
                if not newmat:
                    newmat = self.materials.add_material(mat.lower())
                if "Material Density" in material_data:
                    if "@" in material_data["Material Density"][i] and "," in material_data["Material Density"][i]:
                        nominal_val, dataset_name = self._create_dataset_from_sherlock(
                            material_data["Material Density"][i], "Mass_Density"
                        )
                        newmat.mass_density = nominal_val
                        newmat.mass_density.thermalmodifier = "pwl({}, Temp)".format(dataset_name)
                    else:
                        value = material_data["Material Density"][i]
                        newmat.mass_density = value
                if "Thermal Conductivity" in material_data:
                    if (
                        "@" in material_data["Thermal Conductivity"][i]
                        and "," in material_data["Thermal Conductivity"][i]
                    ):
                        nominal_val, dataset_name = self._create_dataset_from_sherlock(
                            material_data["Thermal Conductivity"][i], "Thermal_Conductivity"
                        )
                        newmat.thermal_conductivity = nominal_val
                        newmat.thermal_conductivity.thermalmodifier = "pwl({}, Temp)".format(dataset_name)
                    else:
                        value = material_data["Thermal Conductivity"][i]
                        newmat.thermal_conductivity = value
                if "Material CTE" in material_data:
                    if "@" in material_data["Material CTE"][i] and "," in material_data["Material CTE"][i]:
                        nominal_val, dataset_name = self._create_dataset_from_sherlock(
                            material_data["Material CTE"][i], "CTE"
                        )
                        newmat.thermal_expansion_coefficient = nominal_val
                        newmat.thermal_expansion_coefficient.thermalmodifier = "pwl({}, Temp)".format(dataset_name)
                    else:
                        value = material_data["Material CTE"][i]
                        newmat.thermal_expansion_coefficient = value
                if "Poisson Ratio" in material_data:
                    if "@" in material_data["Poisson Ratio"][i] and "," in material_data["Poisson Ratio"][i]:
                        nominal_val, dataset_name = self._create_dataset_from_sherlock(
                            material_data["Poisson Ratio"][i], "Poisson_Ratio"
                        )
                        newmat.poissons_ratio = nominal_val
                        newmat.poissons_ratio.thermalmodifier = "pwl({}, Temp)".format(dataset_name)
                    else:
                        value = material_data["Poisson Ratio"][i]
                        newmat.poissons_ratio = value
                if "Elastic Modulus" in material_data:
                    if "@" in material_data["Elastic Modulus"][i] and "," in material_data["Elastic Modulus"][i]:
                        nominal_val, dataset_name = self._create_dataset_from_sherlock(
                            material_data["Elastic Modulus"][i], "Youngs_Modulus"
                        )
                        newmat.youngs_modulus = nominal_val
                        newmat.youngs_modulus.thermalmodifier = "pwl({}, Temp)".format(dataset_name)
                    else:
                        value = material_data["Elastic Modulus"][i]
                        newmat.youngs_modulus = value
                self.assign_material(list_mat_obj, mat)

                for obj_name in list_mat_obj:
                    if not self.modeler[obj_name].surface_material_name:
                        self.modeler[obj_name].surface_material_name = "Steel-oxidised-surface"
            i += 1
            all_objs = [ao for ao in all_objs if ao not in list_mat_obj]
        return True

    @pyaedt_function_handler()
    def cleanup_solution(self, variations="All", entire_solution=True, field=True, mesh=True, linked_data=True):
        """Delete a set of Solution Variations or part of them.

        Parameters
        ----------
        variations : List, str, optional
            All variations to delete. Default is `"All"` which deletes all available solutions.
        entire_solution : bool, optional
            Either if delete entire Solution or part of it. If `True` other booleans will be ignored
            as solution will be entirely deleted.
        field : bool, optional
            Either if delete entire Fields of variation or not. Default is `True`.
        mesh : bool, optional
            Either if delete entire Mesh of variation or not. Default is `True`.
        linked_data : bool, optional
            Either if delete entire Linked Data of variation or not. Default is `True`.

        Returns
        -------
        bool
            `True` if Delete operation succeeded.
        """
        if isinstance(variations, str):
            variations = [variations]
        if entire_solution:
            self.odesign.DeleteFullVariation(variations, linked_data)
        elif field:
            self.odesign.DeleteFieldVariation(variations, mesh, linked_data)
        elif linked_data:
            self.odesign.DeleteLinkedDataVariation(variations)
        return True

    @pyaedt_function_handler
    def add_stackup_3d(self):
        """Create a stackup 3D object.

        Returns
        -------
        :class:`pyaedt.modeler.stackup_3d.Stackup3D`
            Stackup class.
        """
        return Stackup3D(self)

    @pyaedt_function_handler()
    def flatten_3d_components(self, component_name=None, purge_history=True, password=""):
        """Flatten one or multiple 3d components in the actual layout. Each 3d Component is replaced with objects.
        This function will work only if the reference coordinate system of the 3d component is the global one.

        Parameters
        ----------
        component_name : str, list, optional
            List of user defined components. Default is `None` for all 3d Components.
        purge_history : bool, optional
            Define if the 3D Component will be purged before copied.
            This is needed when more than 1 component with the same definition is present.
        password : str, optional
            Password for encrypted 3d component.

        Returns
        -------
        bool
            `True` if succeeded.
        """
        native_comp_names = [i.props["BasicComponentInfo"]["ComponentName"] for _, i in self.native_components.items()]
        if not component_name:
            component_name = [
                key
                for key, val in self.modeler.user_defined_components.items()
                if val.definition_name not in native_comp_names
            ]
        else:
            if isinstance(component_name, str):
                component_name = [component_name]
            for cmp in component_name:
                assert cmp in self.modeler.user_defined_component_names, "Component Definition not found."
        for cmp in component_name:
            comp = self.modeler.user_defined_components[cmp]
            app = comp.edit_definition(password=password)
            for var, val in comp.parameters.items():
                app[var] = val
            if purge_history:
                app.modeler.purge_history(app.modeler._all_object_names)
            self.modeler.set_working_coordinate_system(comp.target_coordinate_system)
            if self.design_type == "Icepak":
                objs_monitors = [part.name for _, part in comp.parts.items()]
                monitor_cache = {}
                for mon_name, mon_obj in self.monitor.all_monitors.items():
                    obj_name = mon_obj.properties["Geometry Assignment"]
                    if obj_name in objs_monitors:
                        monitor_cache.update({mon_obj.name: mon_obj.properties})
            oldcs = self.oeditor.GetActiveCoordinateSystem()
            self.modeler.set_working_coordinate_system(
                self.modeler.user_defined_components[cmp].target_coordinate_system
            )
            comp.delete()
            self.copy_solid_bodies_from(app, no_vacuum=False, no_pec=False, include_sheets=True)
            self.modeler.set_working_coordinate_system(oldcs)
            if self.design_type == "Icepak":
                for _, mon_dict in monitor_cache.items():
                    self.monitor.insert_monitor_object_from_dict(mon_dict, mode=1)
            app.close_project(save_project=False)
            self.modeler.refresh_all_ids()
        return True
