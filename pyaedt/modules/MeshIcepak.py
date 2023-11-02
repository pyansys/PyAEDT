from collections import OrderedDict

from pyaedt import settings
from pyaedt.generic.general_methods import generate_unique_name, pyaedt_function_handler
from pyaedt.modules.Mesh import MeshOperation, meshers


class IcepakMesh(object):
    """Manages Icepak meshes.

    Parameters
    ----------
    app : :class:`pyaedt.application.Analysis3D.FieldAnalysis3D`
    """

    def __init__(self, app):
        self._app = app

        self._odesign = self._app._odesign
        self.modeler = self._app.modeler
        design_type = self._odesign.GetDesignType()
        assert design_type in meshers, "Invalid design type {}".format(design_type)
        self.id = 0
        self._oeditor = self.modeler.oeditor
        self._model_units = self.modeler.model_units
        self.global_mesh_region = self.MeshRegion(
            self.omeshmodule, self.boundingdimension, self._model_units, self._app
        )
        self.meshoperations = self._get_design_mesh_operations()
        self.meshregions = self._get_design_mesh_regions()
        self._priorities_args = []

    @property
    def meshregions_dict(self):
        """Get mesh regions in the design.

        Returns
        -------
        dict
            Dictionary with mesh region names as keys and mesh region objects as values.
        """
        return {mr.name: mr for mr in self.meshregions}

    @pyaedt_function_handler()
    def _refresh_mesh_operations(self):
        """Refresh all mesh operations."""
        self._meshoperations = self._get_design_mesh_operations()
        return len(self.meshoperations)

    @property
    def omeshmodule(self):
        """Icepak Mesh Module.

        References
        ----------
        >>> oDesign.GetModule("MeshRegion")
        """
        return self._app.omeshmodule

    class MeshRegion(object):
        """Manages Icepak mesh region settings.

        Attributes
        ----------
            name : str
                Name of the mesh region.
            UserSpecifiedSettings : bool
                Whether to use manual settings. Default is ``False``.
            ComputeGap : bool
                Whether to enable minimum gap override. Default is ``True``.
            Level : int
                Automatic mesh detail level. Default is 3.
            MaxElementSizeX : str
                Maximum element size along the X-axis. Default is 1/20 of the region
                X-dimension.
            MaxElementSizeY : str
                Maximum element size along the Y-axis. Default is 1/20 of the region
                Y-dimension.
            MaxElementSizeZ : str
                Maximum element size along the Z-axis. Default is 1/20 of the region
                Z-dimension.
            MinElementsInGap : str
                Minimum number of elements in gaps between adjacent objects. Default is "3".
            MinElementsOnEdge : str
                Minimum number of elements on each edge of each object. Default is "2".
            MaxSizeRatio : str
                Maximum ratio of the sizes of adjacent elements. Default is "2".
            NoOGrids : bool
                Whether objects will have O-grids around them. Default is ``False``.
            EnableMLM : bool
                Enable Multi-Level Mesh (MLM). Default is ``True``.
            EnforceMLMType : str
                Type of MLM to use, ``"2D"`` or ``"3D"``. Default is ``"3D"``.
            MaxLevels : str
                Maximum number of refinement level for Multi-Level Mesh. Default is ``"0"``.
            BufferLayers : str
                Number of buffer layers between refinement level. Default is ``"0"``.
            UniformMeshParametersType : str
                Whether to create a creates a uniform mesh with the same mesh size in all
                coordinate directions (``"Average"``) or different spacing in each
                direction (``"XYZ Max Sizes"``). Default is ``"Average"``.
            StairStepMeshing : bool
                Whether to disable vertices projection step used to obtain conformal mesh.
                Default is ``False``.
            DMLMType : str
                If ``EnforceMLMType`` is ``"2D"``, in which 2D plane mesh refinement is
                constrained. Available options are ``"2DMLM_None"``, ``"2DMLM_YZ"``,
                ``"2DMLM_XZ"`` or ``"2DMLM_XY"``. Default is ``"2DMLM_None"``
                which means ``Auto``.
            MinGapX : str
                Minimum gap size along the X-axis. Default is ``"1"``.
            MinGapY : str
                Minimum gap size along the Y-axis. Default is ``"1"``.
            MinGapZ : str
                Minimum gap size along the Z-axis. Default is ``"1"``.
            Objects : list
                Objects to which meshing settings are applied.
            SubModels : bool
                SubModels to which meshing settings are applied.
                Default is ``False``, so ``Objects`` attribute will be used.
            Enable : bool
                Enable mesh region. Default is ``True``.
            ProximitySizeFunction : bool
                Whether to use proximity-based size function. Default is ``True``.
            CurvatureSizeFunction : bool
                Whether to use curvature-based size function. Default is ``True``.
            EnableTransition : bool
                Whether to enable mesh transition. Default is ``False``.
            OptimizePCBMesh : bool
                Whether to optimize PCB mesh. Default is ``True``.
            Enable2DCutCell : bool
                Whether to enable 2D cut cell meshing. Default is ``False``.
            EnforceCutCellMeshing : bool
                Whether to enforce cut cell meshing. Default is ``False``.
            Enforce2dot5DCutCell : bool
                Whether to enforce 2.5D cut cell meshing. Default is ``False``.
            SlackMinX : str
                Slack along the negative X-axis. Default is ``"0mm"``.
            SlackMinY : str
                Slack along the negative Y-axis. Default is ``"0mm"``.
            SlackMinZ : str
                Slack along the negative Z-axis. Default is ``"0mm"``.
            SlackMaxX : str
                Slack along the positive X-axis. Default is ``"0mm"``.
            SlackMaxY : str
                Slack along the positive Y-axis. Default is ``"0mm"``.
            SlackMaxZ : str
                Slack along the positive Z-axis. Default is ``"0mm"``.
            CoordCS : str
                Coordinate system of the mesh region. Default is ``"Global"``.
            virtual_region: bool
                Whether to use virtual region. In order to use it, Icepak version must be 22R2 or
                newer and the corresponding beta feature must be enabled.
        """

        def __init__(self, meshmodule, dimension, units, app, name=None):
            if name is None:
                name = "Settings"
            self.name = name
            self.meshmodule = meshmodule
            self.model_units = units
            self.UserSpecifiedSettings = False
            self.ComputeGap = True
            self.Level = 3
            self.MaxElementSizeX = str(float(dimension[0]) / 20)
            self.MaxElementSizeY = str(float(dimension[1]) / 20)
            self.MaxElementSizeZ = str(float(dimension[2]) / 20)
            self.MinElementsInGap = "3"
            self.MinElementsOnEdge = "2"
            self.MaxSizeRatio = "2"
            self.NoOGrids = False
            self.EnableMLM = True
            self.EnforeMLMType = "3D"
            self.MaxLevels = "0"
            self.BufferLayers = "0"
            self.UniformMeshParametersType = "Average"
            self.StairStepMeshing = False
            self.DMLMType = "2DMLM_None"
            self.MinGapX = "1"
            self.MinGapY = "1"
            self.MinGapZ = "1"
            self.Objects = ["Region"]
            self.SubModels = False
            self.Enable = True
            self.ProximitySizeFunction = True
            self.CurvatureSizeFunction = True
            self.EnableTransition = False
            self.OptimizePCBMesh = True
            self.Enable2DCutCell = False
            self.EnforceCutCellMeshing = False
            self.Enforce2dot5DCutCell = False
            self.SlackMinX = "0mm"
            self.SlackMinY = "0mm"
            self.SlackMinZ = "0mm"
            self.SlackMaxX = "0mm"
            self.SlackMaxY = "0mm"
            self.SlackMaxZ = "0mm"
            self.CoordCS = "Global"
            self.virtual_region = False
            self._app = app

        @pyaedt_function_handler()
        def _dim_arg(self, value):
            from pyaedt.generic.general_methods import _dim_arg

            return _dim_arg(value, self.model_units)

        @property
        def _new_versions_fields(self):
            arg = []
            if settings.aedt_version > "2021.2":
                arg = [
                    "ProximitySizeFunction:=",
                    self.ProximitySizeFunction,
                    "CurvatureSizeFunction:=",
                    self.CurvatureSizeFunction,
                    "EnableTransition:=",
                    self.EnableTransition,
                    "OptimizePCBMesh:=",
                    self.OptimizePCBMesh,
                    "Enable2DCutCell:=",
                    self.Enable2DCutCell,
                    "EnforceCutCellMeshing:=",
                    self.EnforceCutCellMeshing,
                    "Enforce2dot5DCutCell:=",
                    self.Enforce2dot5DCutCell,
                ]
            if self.virtual_region:
                if self._app.check_beta_option_enabled("S544753_ICEPAK_VIRTUALMESHREGION_PARADIGM"):
                    arg.extend(
                        [
                            "SlackMinX:=",
                            self.SlackMinX,
                            "SlackMinY:=",
                            self.SlackMinY,
                            "SlackMinZ:=",
                            self.SlackMinZ,
                            "SlackMaxX:=",
                            self.SlackMaxX,
                            "SlackMaxY:=",
                            self.SlackMaxY,
                            "SlackMaxZ:=",
                            self.SlackMaxZ,
                            "CoordCS:=",
                            self.CoordCS,
                        ]
                    )
                else:
                    if settings.aedt_version < "2022.2":
                        self._app.logger.warning("Virtual Mesh Region feature is not available in this version.")
                    else:
                        self._app.logger.warning("Virtual Mesh Region beta feature is not enabled.")

            return arg

        @property
        def autosettings(self):
            """Automatic mesh settings."""
            arg = [
                "MeshMethod:=",
                "MesherHD",
                "UserSpecifiedSettings:=",
                self.UserSpecifiedSettings,
                "ComputeGap:=",
                self.ComputeGap,
                "MeshRegionResolution:=",
                self.Level,
                "MinGapX:=",
                self._dim_arg(self.MinGapX),
                "MinGapY:=",
                self._dim_arg(self.MinGapY),
                "MinGapZ:=",
                self._dim_arg(self.MinGapZ),
            ]
            if self.SubModels:
                arg.append("SubModels:=")
                arg.append(self.SubModels)
            if self.Objects:
                arg.append("Objects:=")
                arg.append(self.Objects)
            arg.extend(self._new_versions_fields)
            return arg

        @property
        def manualsettings(self):
            """Manual mesh settings."""
            arg = [
                "MeshMethod:=",
                "MesherHD",
                "UserSpecifiedSettings:=",
                self.UserSpecifiedSettings,
                "ComputeGap:=",
                self.ComputeGap,
                "MaxElementSizeX:=",
                self._dim_arg(self.MaxElementSizeX),
                "MaxElementSizeY:=",
                self._dim_arg(self.MaxElementSizeY),
                "MaxElementSizeZ:=",
                self._dim_arg(self.MaxElementSizeZ),
                "MinElementsInGap:=",
                self.MinElementsInGap,
                "MinElementsOnEdge:=",
                self.MinElementsOnEdge,
                "MaxSizeRatio:=",
                self.MaxSizeRatio,
                "NoOGrids:=",
                self.NoOGrids,
                "EnableMLM:=",
                self.EnableMLM,
                "EnforeMLMType:=",
                self.EnforeMLMType,
                "MaxLevels:=",
                self.MaxLevels,
                "BufferLayers:=",
                self.BufferLayers,
                "UniformMeshParametersType:=",
                self.UniformMeshParametersType,
                "StairStepMeshing:=",
                self.StairStepMeshing,
                "2DMLMType:=",
                self.DMLMType,
                "MinGapX:=",
                self._dim_arg(self.MinGapX),
                "MinGapY:=",
                self._dim_arg(self.MinGapY),
                "MinGapZ:=",
                self._dim_arg(self.MinGapZ),
            ]
            if self.SubModels:
                arg.append("SubModels:=")
                arg.append(self.SubModels)
            if self.Objects:
                arg.append("Objects:=")
                arg.append(self.Objects)
            arg.extend(self._new_versions_fields)
            return arg

        @property
        def _odesign(self):
            """Instance of a design in a project."""
            return self._app._odesign

        @pyaedt_function_handler()
        def update(self):
            """Update mesh region settings with the settings in the object variable.

            Returns
            -------
            bool
                ``True`` when successful, ``False`` when failed.

            References
            ----------
            >>> oModule.EditGlobalMeshRegion
            >>> oModule.EditMeshRegion
            """
            if self.name == "Settings":
                args = ["NAME:Settings"]
            else:
                args = ["NAME:" + self.name, "Enable:=", self.Enable]
            if self.UserSpecifiedSettings:
                args += self.manualsettings
            else:
                args += self.autosettings
            if self.name == "Settings":
                try:
                    self.meshmodule.EditGlobalMeshRegion(args)
                    return True
                except Exception:  # pragma : no cover
                    return False
            else:
                try:
                    self.meshmodule.EditMeshRegion(self.name, args)
                    return True
                except Exception:  # pragma : no cover
                    return False

        @pyaedt_function_handler()
        def create(self):
            """Create a new mesh region.

            Returns
            -------
            bool
                ``True`` when successful, ``False`` when failed.

            References
            ----------
            >>> oModule.AssignMeshRegion
            >>> oModule.AssignVirtualMeshRegion
            """
            assert self.name != "Settings", "Cannot create a new mesh region with this Name"
            args = ["NAME:" + self.name, "Enable:=", self.Enable]
            if self.UserSpecifiedSettings:
                args += self.manualsettings
            else:
                args += self.autosettings
            if self.virtual_region and self._app.check_beta_option_enabled("S544753_ICEPAK_VIRTUALMESHREGION_PARADIGM"):
                self.meshmodule.AssignVirtualMeshRegion(args)
            else:
                self.meshmodule.AssignMeshRegion(args)
            self._app.mesh.meshregions.append(self)
            self._app.modeler.refresh_all_ids()
            return True

        @pyaedt_function_handler()
        def delete(self):
            """Delete mesh region.

            Returns
            -------
            bool
                ``True`` when successful, ``False`` when failed.

            References
            ----------
            >>> oModule.DeleteMeshRegions()
            """
            self.meshmodule.DeleteMeshRegions([self.name])
            return True

    @property
    def boundingdimension(self):
        """Bounding dimension."""
        return self.modeler.get_bounding_dimension()

    @pyaedt_function_handler()
    def _get_design_mesh_operations(self):
        """Retrieve design mesh operations."""
        meshops = []
        try:
            for ds in self._app.design_properties["MeshRegion"]["MeshSetup"]["MeshOperations"]:
                if isinstance(
                    self._app.design_properties["MeshRegion"]["MeshSetup"]["MeshOperations"][ds], (OrderedDict, dict)
                ):
                    meshops.append(
                        MeshOperation(
                            self,
                            ds,
                            self._app.design_properties["MeshRegion"]["MeshSetup"]["MeshOperations"][ds],
                            "Icepak",
                        )
                    )
        except:
            pass
        return meshops

    @pyaedt_function_handler()
    def _get_design_mesh_regions(self):
        """Retrieve design mesh regions."""
        meshops = []
        try:
            for ds in self._app.design_properties["MeshRegion"]["MeshSetup"]["MeshRegions"]:
                if isinstance(
                    self._app.design_properties["MeshRegion"]["MeshSetup"]["MeshRegions"][ds], (OrderedDict, dict)
                ):
                    dict_prop = self._app.design_properties["MeshRegion"]["MeshSetup"]["MeshRegions"][ds]
                    if ds == "Global":
                        ds = "Settings"
                    meshop = self.MeshRegion(
                        self.omeshmodule, self.boundingdimension, self.modeler.model_units, self._app, ds
                    )
                    for el in dict_prop:
                        if el in meshop.__dict__:
                            meshop.__dict__[el] = dict_prop[el]
                    meshops.append(meshop)
        except:
            pass
        return meshops

    @pyaedt_function_handler()
    def assign_mesh_level(self, mesh_order, meshop_name=None):
        """Assign a mesh level to objects.

        Parameters
        ----------
        mesh_order : dict
            Dictionary where the key is the object name and the value is
            the mesh level.
        meshop_name :  str, optional
            Name of the mesh operation. The default is ``None``.

        Returns
        -------
        list of :class:`pyaedt.modules.Mesh.MeshOperation`
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.AssignMeshOperation
        """
        level_order = {}
        for obj in mesh_order:
            if mesh_order[obj] not in level_order.keys():
                level_order[mesh_order[obj]] = []
            level_order[mesh_order[obj]].append(obj)
        list_meshops = []
        for level in level_order:
            if meshop_name:
                meshop_name = generate_unique_name(meshop_name, "L_" + str(level))
            else:
                meshop_name = generate_unique_name("Icepak", "L_" + str(level))
            props = OrderedDict({"Enable": True, "Level": str(level), "Objects": level_order[level]})
            mop = MeshOperation(self, meshop_name, props, "Icepak")
            mop.create()
            self.meshoperations.append(mop)
            list_meshops.append(meshop_name)
        return list_meshops

    @pyaedt_function_handler()
    def assign_mesh_from_file(self, objects, filename, meshop_name=None):
        """Assign a mesh from file to objects.

        Parameters
        ----------
        objects : list
            List of objects to which apply the mesh file.
        filename :  str
            Full path to .msh file.
        meshop_name :  str, optional
            Name of the mesh operations. Default is ``None``.

        Returns
        -------
         :class:`pyaedt.modules.Mesh.MeshOperation`
            Mesh Operation object. ``False`` when failed.

        References
        ----------
        >>> oModule.AssignMeshOperation
        """
        objs = self._app.modeler.convert_to_selections(objects, True)
        if meshop_name:
            meshop_name = generate_unique_name("MeshFile")
        else:
            meshop_name = generate_unique_name("MeshFile")
        props = OrderedDict({"Enable": True, "MaxLevel": str(0), "MinLevel": str(0), "Objects": objs})
        props["Local Mesh Parameters Enabled"] = False
        props["Mesh Reuse Enabled"] = True
        props["Mesh Reuse File"] = filename
        props["Local Mesh Parameters Type"] = "3DPolygon Local Mesh Parameters"
        props["Height count"] = "0"
        props["Top height"] = "0mm"
        props["Top ratio"] = "0"
        props["Bottom height"] = "0mm"
        props["Bottom ratio"] = "0"
        mop = MeshOperation(self, meshop_name, props, "Icepak")
        if mop.create():
            self.meshoperations.append(mop)
            return mop
        return False

    @pyaedt_function_handler()
    def automatic_mesh_pcb(self, accuracy=2):
        """Create a custom mesh tailored on a PCB design.

        Parameters
        ----------
        accuracy : int, optional
            Type of the mesh. Options are ``1``, ``2``, and ``3``, which represent
            respectively a coarse, standard, or very accurate mesh. The default is ``2``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.EditMeshOperation
        """
        xsize = self.boundingdimension[0] / (15 * accuracy * accuracy)
        ysize = self.boundingdimension[1] / (15 * accuracy * accuracy)
        zsize = self.boundingdimension[2] / (10 * accuracy)
        MaxSizeRatio = 1 + (accuracy / 2)
        self.global_mesh_region.MaxElementSizeX = xsize
        self.global_mesh_region.MaxElementSizeY = ysize
        self.global_mesh_region.MaxElementSizeZ = zsize
        self.global_mesh_region.MaxSizeRatio = MaxSizeRatio
        self.global_mesh_region.UserSpecifiedSettings = True
        self.global_mesh_region.UniformMeshParametersType = "XYZ Max Sizes"
        self.global_mesh_region.MaxLevels = 2
        self.global_mesh_region.BufferLayers = 1
        self.global_mesh_region.MinGapX = str(xsize / 10)
        self.global_mesh_region.MinGapY = str(ysize / 10)
        self.global_mesh_region.MinGapZ = str(zsize / 10)
        self.global_mesh_region.update()
        return True

    @pyaedt_function_handler()
    def automatic_mesh_3D(self, accuracy2, stairStep=True):
        """Create a generic custom mesh for a custom 3D object.

        Parameters
        ----------
        accuracy2 : int
            Type of the mesh. Options are ``1``, ``2``, and ``3``, which represent respectively
            a coarse, standard, or very accurate mesh.
        stairStep : bool, optional
            Whether to enable a stair step. The default is ``True``.

        Returns
        -------
         bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.EditMeshOperation
        """
        xsize = self.boundingdimension[0] / (10 * accuracy2 * accuracy2)
        ysize = self.boundingdimension[1] / (10 * accuracy2 * accuracy2)
        zsize = self.boundingdimension[2] / (10 * accuracy2)
        self.global_mesh_region.MaxElementSizeX = xsize
        self.global_mesh_region.MaxElementSizeY = ysize
        self.global_mesh_region.MaxElementSizeZ = zsize
        self.global_mesh_region.UserSpecifiedSettings = True
        self.global_mesh_region.MinGapX = str(xsize / 100)
        self.global_mesh_region.MinGapY = str(ysize / 100)
        self.global_mesh_region.MinGapZ = str(zsize / 100)
        self.global_mesh_region.StairStepMeshing = stairStep
        self.global_mesh_region.update()
        return True

    @pyaedt_function_handler()
    def add_priority(self, entity_type, obj_list=None, comp_name=None, priority=3):
        """Add priority to objects.

        Parameters
        ----------
        entity_type : int
            Type of the entity. Options are ``1`` and ``2``, which represent respectively
            an object and a component.
        obj_list : list
            List of 3D objects, which can include conductors and dielectrics.
            If the user pass a non 3D object, it will be excluded.
        comp_name : str, optional
            Name of the component. The default is ``None``.
        priority : int, optional
            Level of priority. The default is ``3``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.UpdatePriorityList

        Examples
        --------
        >>> from pyaedt import Icepak
        >>> app = Icepak()
        >>> app.mesh.add_priority(entity_type=1, obj_list=app.modeler.object_names, priority=3)
        >>> app.mesh.add_priority(entity_type=2, comp_name=app.modeler.user_defined_component_names[0], priority=2)
        """
        i = priority

        args = ["NAME:UpdatePriorityListData"]
        if entity_type == 1:
            non_user_defined_component_parts = self._app.modeler.oeditor.GetChildNames()
            new_obj_list = []
            for comp in obj_list:
                if comp != "Region" and comp in non_user_defined_component_parts:
                    new_obj_list.append(comp)

            objects = ", ".join(new_obj_list)
            if not new_obj_list:
                return False
            prio = [
                "NAME:PriorityListParameters",
                "EntityType:=",
                "Object",
                "EntityList:=",
                objects,
                "PriorityNumber:=",
                i,
                "PriorityListType:=",
                ["2D", "3D"][int(self._app.modeler[new_obj_list[0]].is3d)],
            ]
            self._priorities_args.append(prio)
            args += self._priorities_args
        elif entity_type == 2:
            prio = [
                "NAME:PriorityListParameters",
                "EntityType:=",
                "Component",
                "EntityList:=",
                comp_name,
                "PriorityNumber:=",
                i,
                "PriorityListType:=",
                "3D",
            ]
            self._priorities_args.append(prio)
            args += self._priorities_args
        self.modeler.oeditor.UpdatePriorityList(["NAME:UpdatePriorityListData"])
        self.modeler.oeditor.UpdatePriorityList(args)
        return True

    @pyaedt_function_handler()
    def assign_mesh_region(self, objectlist=[], level=5, is_submodel=False, name=None, virtual_region=False):
        """Assign a predefined surface mesh level to an object.

        Parameters
        ----------
        objectlist : list, optional
            List of objects to apply the mesh region to. The default
            is ``[]``.
        level : int, optional
            Level of the surface mesh. Options are ``1`` through ``5``. The default
            is ``5``.
        is_submodel : bool
            Define if the object list is made by component models
        name : str, optional
            Name of the mesh region. The default is ``"MeshRegion1"``.
        virtual_region : bool, optional
            Whether to use the virtual mesh region beta feature (available from version 22.2). The default is ``False``.

        Returns
        -------
        :class:`pyaedt.modules.MeshIcepak.IcepakMesh.MeshRegion`

        References
        ----------
        >>> oModule.AssignMeshRegion
        """
        if not name:
            name = generate_unique_name("MeshRegion")
        meshregion = self.MeshRegion(self.omeshmodule, self.boundingdimension, self.modeler.model_units, self._app)
        meshregion.UserSpecifiedSettings = False
        meshregion.Level = level
        meshregion.name = name
        meshregion.virtual_region = virtual_region
        if not objectlist:
            objectlist = [i for i in self.modeler.object_names]
        if is_submodel:
            meshregion.SubModels = objectlist
        else:
            meshregion.Objects = objectlist
        all_objs = [i for i in self.modeler.object_names]
        try:
            meshregion.create()
            created = True
        except Exception:  # pragma : no cover
            created = False
        if created:
            if virtual_region and self._app.check_beta_option_enabled(
                "S544753_ICEPAK_VIRTUALMESHREGION_PARADIGM"
            ):  # pragma : no cover
                if is_submodel:
                    meshregion.Objects = [i for i in objectlist if i in all_objs]
                    meshregion.SubModels = [i for i in objectlist if i not in all_objs]
                else:
                    meshregion.Objects = objectlist
                    meshregion.SubModels = None
            else:
                objectlist2 = self.modeler.object_names
                added_obj = [i for i in objectlist2 if i not in all_objs]
                if not added_obj:
                    added_obj = [i for i in objectlist2 if i not in all_objs or i in objectlist]
                meshregion.Objects = added_obj
                meshregion.SubModels = None

            meshregion.update()
            return meshregion
        else:
            return False

    @pyaedt_function_handler()
    def generate_mesh(self, name=None):
        """Generate the mesh for a given setup name.

        Parameters
        ----------
        name : str, optional
            Name of the design to mesh. Default is ``None`` in which case the first available setup will be selected.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesign.GenerateMesh
        """
        if name is None:
            name = []
        return self._odesign.GenerateMesh(name) == 0

    @pyaedt_function_handler()
    def assign_mesh_level_to_group(
        self,
        mesh_level,
        groupName,
        localMeshParamEn=False,
        localMeshParameters="No local mesh parameters",
        meshop_name=None,
    ):
        """Assign a mesh level to a group.

        Parameters
        ----------
        mesh_level : int
            Level of mesh to assign. Options are ``1`` through ``5``.
        groupName : str
            Name of the group.
        localMeshParamEn : bool, optional
            The default is ``False``.
        localMeshParameters : str, optional
            The default is ``"No Local Mesh Parameters"``.
        meshop_name : str, optional
            Name of the mesh operation. The default is ``None``.

        Returns
        -------
        :class:`pyaedt.modules.Mesh.MeshOperation`

        References
        ----------
        >>> oModule.AssignMeshOperation
        """
        if meshop_name:
            for el in self.meshoperations:
                if el.name == meshop_name:
                    meshop_name = generate_unique_name(meshop_name)
        else:
            meshop_name = generate_unique_name("MeshLevel")
        props = OrderedDict(
            {
                "Enable": True,
                "Level": mesh_level,
                "Local Mesh Parameters Enabled": localMeshParamEn,
                "Groups": [str(groupName)],
                "Local Mesh Parameters Type": localMeshParameters,
            }
        )
        mop = MeshOperation(self, meshop_name, props, "Icepak")
        mop.create()
        self.meshoperations.append(mop)
        return mop
