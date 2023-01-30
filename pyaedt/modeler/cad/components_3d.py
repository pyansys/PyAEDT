from __future__ import absolute_import

import random
import re
import warnings
from collections import OrderedDict

from pyaedt import pyaedt_function_handler
from pyaedt.generic.general_methods import _uname
from pyaedt.modeler.cad.elements3d import _dict2arg


class UserDefinedComponentParameters(dict):
    def __setitem__(self, key, value):
        try:
            self._component._m_Editor.ChangeProperty(
                [
                    "NAME:AllTabs",
                    [
                        "NAME:Parameters",
                        ["NAME:PropServers", self._component.name],
                        ["NAME:ChangedProps", ["NAME:" + key, "Value:=", str(value)]],
                    ],
                ]
            )
            dict.__setitem__(self, key, value)
        except:
            self._component._logger.warning("Property %s has not been edited.Check if readonly", key)

    def __init__(self, component, *args, **kw):
        dict.__init__(self, *args, **kw)
        self._component = component


class UserDefinedComponentProps(OrderedDict):
    """User Defined Component Internal Parameters."""

    def __setitem__(self, key, value):
        OrderedDict.__setitem__(self, key, value)
        if self._pyaedt_user_defined_component.auto_update:
            res = self._pyaedt_user_defined_component.update_native()
            if not res:
                self._pyaedt_user_defined_component._logger.warning("Update of %s failed. Check needed arguments", key)

    def __init__(self, user_defined_components, props):
        OrderedDict.__init__(self)
        if props:
            for key, value in props.items():
                if isinstance(value, (dict, OrderedDict)):
                    OrderedDict.__setitem__(self, key, UserDefinedComponentProps(user_defined_components, value))
                else:
                    OrderedDict.__setitem__(self, key, value)
        self._pyaedt_user_defined_component = user_defined_components

    def _setitem_without_update(self, key, value):
        OrderedDict.__setitem__(self, key, value)


class MeshFusion(object):
    def __init__(self, parent):
        self._parent = parent
        self._primitives = self._parent._primitives
        self._m_Editor = self._parent._m_Editor
        self.name = self._parent.name
        self._use_slider = None
        self._slider_value = None
        self._surface_dev = None
        self._normal_deviation = None
        self._aspect_ratio = None
        self._use_curvilinear = None
        self._mesh_method = None
        self._dynamic_surface_resolution = None
        self._use_flex_mesh = None
        self._use_fallback_mesh = None
        self._allow_phi_mesh = None
        self._model_resolution = None
        self._use_auto_simplify = None
        self._priority_mesh = False
        self._volume = [0, 0, 0, 0, 0, 0]
        self._override_mesh = False

    @property
    def override_mesh(self):
        return self._override_mesh

    @override_mesh.setter
    def override_mesh(self, val):
        self._override_mesh = True
        self._set_mesh_fusion()

    @property
    def do_mesh_assembly(self):
        """Get/Set the Mesh fusion on the 3D Component.

        Returns
        -------
        bool
        """
        return self._get_prop("Do Mesh Assembly")

    @do_mesh_assembly.setter
    def do_mesh_assembly(self, value):

        c_obj = self._m_Editor.GetChildObject(self.name)
        c_obj_props = c_obj.GetPropNames()
        if "Do Mesh Assembly" in c_obj_props:
            c_obj.SetPropValue("Do Mesh Assembly", value)

    @property
    def use_slider(self):
        """Get the mesh settings on the 3D Component to use slider.

        Returns
        -------
        bool
        """
        if self._use_slider is not None:
            return self._use_slider
        prop = self._get_prop("Surface Approximation")
        self._use_slider = True if "Use Slider" in prop else False
        return self._use_slider

    @use_slider.setter
    def use_slider(self, val):
        self._use_slider = val
        if val is True and not self._slider_value:
            self._slider_value = 5
        self._override_mesh = True
        self._set_mesh_fusion()

    @property
    def slider_value(self):
        """Get the mesh settings on the 3D Component to use slider.

        Returns
        -------
        int
        """
        if self._slider_value is not None:
            return self._slider_value
        self._slider_value = 5
        prop = self._get_prop("Surface Approximation")
        if "Use Slider" in prop:
            self._slider_value = int(prop.split(" = ")[-1])
        return self._slider_value

    @slider_value.setter
    def slider_value(self, val):
        self._slider_value = val
        self._use_slider = True
        self._override_mesh = True
        self._set_mesh_fusion()

    @property
    def mesh_method(self):
        """Get the mesh method on the 3D Component.

        Returns
        -------
        str
        """
        if self._mesh_method is not None:
            return self._mesh_method
        self._mesh_method = self._get_prop("Initial Mesh Method")
        return self._mesh_method

    @mesh_method.setter
    def mesh_method(self, val):
        if val in ["auto", "classic", "tau"]:
            self._mesh_method = val
            self._override_mesh = True
            self._set_mesh_fusion()

    @property
    def dynamic_surface_resolution(self):
        """Get the mesh method on the 3D Component.

        Returns
        -------
        str
        """
        if self._dynamic_surface_resolution is not None:
            return self._dynamic_surface_resolution
        self._dynamic_surface_resolution = self._get_prop("Dynamic Surface Resolution")
        return self._dynamic_surface_resolution

    @dynamic_surface_resolution.setter
    def dynamic_surface_resolution(self, val):
        self._dynamic_surface_resolution = val
        self._override_mesh = True
        self._set_mesh_fusion()

    @property
    def use_flex_mesh(self):
        """Get the mesh method on the 3D Component.

        Returns
        -------
        str
        """
        if self._use_flex_mesh is not None:
            return self._use_flex_mesh
        self._use_flex_mesh = self._get_prop("Use Flex meshing for TAU volume mesh")
        return self._use_flex_mesh

    @use_flex_mesh.setter
    def use_flex_mesh(self, val):
        self._use_flex_mesh = val
        self._override_mesh = True
        self._set_mesh_fusion()

    @property
    def use_fallback_mesh(self):
        """Get the mesh method on the 3D Component.

        Returns
        -------
        str
        """
        if self._use_fallback_mesh is not None:
            return self._use_fallback_mesh
        self._use_fallback_mesh = self._get_prop("Use alternative mesh methods as fall back")
        return self._use_fallback_mesh

    @use_fallback_mesh.setter
    def use_fallback_mesh(self, val):
        self._use_fallback_mesh = val
        self._override_mesh = True
        self._set_mesh_fusion()

    @property
    def allow_phi_mesh(self):
        """Get the mesh method on the 3D Component.

        Returns
        -------
        str
        """
        if self._allow_phi_mesh is not None:
            return self._allow_phi_mesh
        self._allow_phi_mesh = self._get_prop("Allow Phi for layered geometry (Classic only)")
        return self._allow_phi_mesh

    @allow_phi_mesh.setter
    def allow_phi_mesh(self, val):
        self._allow_phi_mesh = val
        self._override_mesh = True
        self._set_mesh_fusion()

    @property
    def use_curvilinear(self):
        """Get the mesh method on the 3D Component.

        Returns
        -------
        str
        """
        if self._use_curvilinear is not None:
            return self._use_curvilinear
        self._use_curvilinear = self._get_prop("Apply Curvilinear Elements")
        return self._use_curvilinear

    @use_curvilinear.setter
    def use_curvilinear(self, val):
        self._use_curvilinear = val
        self._override_mesh = True
        self._set_mesh_fusion()

    @property
    def use_auto_simplify(self):
        """Get the mesh method on the 3D Component.

        Returns
        -------
        str
        """
        if self._use_auto_simplify is not None:
            return self._use_auto_simplify
        prop = self._get_prop("Model Resolution Length")
        if prop:
            self._use_auto_simplify = True if prop.split(" = ")[-1] == "true" else False
        return self._use_auto_simplify

    @use_auto_simplify.setter
    def use_auto_simplify(self, val):
        self._use_auto_simplify = val
        if val is False and not self._model_resolution:
            self._model_resolution = "0.001mm"
        self._override_mesh = True
        self._set_mesh_fusion()

    @property
    def model_resolution(self):
        """Get the mesh method on the 3D Component.

        Returns
        -------
        str
        """
        if self._model_resolution is not None:
            return self._model_resolution
        prop = self._get_prop("Model Resolution Length")
        if prop:
            self._model_resolution = prop.split(",")[0].split(" = ")[1]
        return self._model_resolution

    @model_resolution.setter
    def model_resolution(self, val):
        self._model_resolution = val
        self._use_auto_simplify = False
        self._override_mesh = True
        self._set_mesh_fusion()

    @property
    def aspect_ratio(self):
        """Get the mesh method on the 3D Component.

        Returns
        -------
        str
        """
        if self._aspect_ratio is not None:
            return self._aspect_ratio
        prop = self._get_prop("Surface Approximation")
        ps = [i for i in prop.split(", ")]
        ps_with_values = {}
        for i in ps:
            i_splitted = i.split(" = ")
            try:
                ps_with_values[i_splitted[0]] = i_splitted[1]
            except IndexError:
                pass
        if "Aspect Ratio" in ps_with_values:
            self._aspect_ratio = ps_with_values["Aspect Ratio"]
        return self._aspect_ratio

    @aspect_ratio.setter
    def aspect_ratio(self, val):
        self._aspect_ratio = val
        self._use_slider = False
        self._override_mesh = True
        self._set_mesh_fusion()

    @property
    def surface_deviation(self):
        """Get the mesh method on the 3D Component.

        Returns
        -------
        str
        """
        if self._surface_dev is not None:
            return self._surface_dev
        prop = self._get_prop("Surface Approximation")
        ps = [i for i in prop.split(", ")]
        ps_with_values = {}
        for i in ps:
            i_splitted = i.split(" = ")
            try:
                ps_with_values[i_splitted[0]] = i_splitted[1]
            except IndexError:
                pass
        if "Surface Deviation" in ps_with_values:
            self._surface_dev = ps_with_values["Surface Deviation"]
        return self._surface_dev

    @surface_deviation.setter
    def surface_deviation(self, val):
        self._surface_deviation = val
        self._use_slider = False
        self._override_mesh = True
        self._set_mesh_fusion()

    @property
    def normal_deviation(self):
        """Get the mesh method on the 3D Component.

        Returns
        -------
        str
        """
        if self._normal_deviation is not None:
            return self._normal_deviation
        prop = self._get_prop("Surface Approximation")
        ps = [i for i in prop.split(", ")]
        ps_with_values = {}
        for i in ps:
            i_splitted = i.split(" = ")
            try:
                ps_with_values[i_splitted[0]] = i_splitted[1]
            except IndexError:
                pass
        if "Normal Deviation" in ps_with_values:
            self._normal_deviation = ps_with_values["Normal Deviation"]
        return self._normal_deviation

    @normal_deviation.setter
    def normal_deviation(self, val):
        self._normal_deviation = val
        self._use_slider = False
        self._override_mesh = True
        self._set_mesh_fusion()

    @pyaedt_function_handler()
    def _get_prop(self, propname):
        c_obj = self._m_Editor.GetChildObject(self.name)
        c_obj_props = c_obj.GetPropNames()
        if propname in c_obj_props:
            return c_obj.GetPropValue(propname)
        return ""

    @property
    def priority_mesh(self):
        return self._priority_mesh

    @priority_mesh.setter
    def priority_mesh(self, val):
        self._priority_mesh = val
        self._set_mesh_fusion()

    @property
    def volume(self):
        return self._volume

    @volume.setter
    def volume(self, val):
        self._volume = val
        self._set_mesh_fusion()

    @pyaedt_function_handler()
    def _set_mesh_fusion(self):

        arg = ["NAME:AllSettings"]
        arg_ma = [
            "NAME:MeshAssembly",
        ]
        priority_3d_component_list = []
        for c3d, c3dobj in self._primitives.user_defined_components.items():
            if self.name == c3d or c3dobj.mesh_fusion.do_mesh_assembly:
                if c3dobj.mesh_fusion.priority_mesh:
                    priority_3d_component_list.append(c3d)
                arg_cmp = [
                    "NAME:{}".format(c3d),
                ]
                arg_cmp_mesh_settings = [
                    "NAME:MeshSetting",
                ]
                if self.name == c3d:
                    _use_slider = self.use_slider
                    _slider_value = self.slider_value
                    _surface_dev = self.surface_deviation
                    _normal_deviation = self.normal_deviation
                    _aspect_ratio = self.aspect_ratio
                    _use_curvilinear = self.use_curvilinear
                    _mesh_method = self.mesh_method
                    _dynamic_surface_resolution = self.dynamic_surface_resolution
                    _use_flex_mesh = self.use_flex_mesh
                    _use_fallback_mesh = self.use_fallback_mesh
                    _allow_phi_mesh = self.allow_phi_mesh
                    _model_resolution = self.model_resolution
                    _auto_simplify = self.use_auto_simplify
                else:
                    _use_slider = c3dobj.mesh_fusion.use_slider
                    _slider_value = c3dobj.mesh_fusion.slider_value
                    _surface_dev = c3dobj.mesh_fusion.surface_deviation
                    _normal_deviation = c3dobj.mesh_fusion.normal_deviation
                    _aspect_ratio = c3dobj.mesh_fusion.aspect_ratio
                    _use_curvilinear = c3dobj.mesh_fusion.use_curvilinear
                    _mesh_method = c3dobj.mesh_fusion.mesh_method
                    _dynamic_surface_resolution = c3dobj.mesh_fusion.dynamic_surface_resolution
                    _use_flex_mesh = c3dobj.mesh_fusion.use_flex_mesh
                    _use_fallback_mesh = c3dobj.mesh_fusion.se_fallback_mesh
                    _allow_phi_mesh = c3dobj.mesh_fusion.allow_phi_mesh
                    _model_resolution = c3dobj.mesh_fusion.model_resolution
                    _auto_simplify = c3dobj.mesh_fusion.use_auto_simplify

                if self.override_mesh:
                    if _use_slider:
                        arg_cmp_mesh_settings.append(
                            [
                                "NAME:GlobalSurfApproximation",
                                "CurvedSurfaceApproxChoice:=",
                                "UseSlider",
                                "SliderMeshSettings:=",
                                _slider_value,
                            ]
                        )
                    else:
                        arg_cmp_mesh_settings.append(
                            [
                                "NAME:GlobalSurfApproximation",
                                "CurvedSurfaceApproxChoice:=",
                                "ManualSettings",
                                "SurfDevChoice:=",
                                2 if _surface_dev else 0,
                                "SurfDev:=",
                                self._primitives._arg_with_dim(_surface_dev) if _surface_dev else "0.01mm",
                                "NormalDevChoice:=",
                                2 if _normal_deviation else 1,
                                "NormalDev:=",
                                self._primitives._arg_with_dim(_normal_deviation, "deg")
                                if _normal_deviation
                                else "22.5deg",
                                "AspectRatioChoice:=",
                                2 if _aspect_ratio else 1,
                                "AspectRatio:=",
                                str(_aspect_ratio),
                            ]
                        )
                    arg_cmp_mesh_settings.append(["NAME:GlobalCurvilinear", "Apply:=", _use_curvilinear])
                    if not _auto_simplify:
                        mr = [
                            "NAME:GlobalModelRes",
                            "UseAutoLength:=",
                            False,
                            "DefeatureLength:=",
                            self._primitives._arg_with_dim(_model_resolution),
                        ]
                    else:
                        mr = ["NAME:GlobalModelRes", "UseAutoLength:=", True]
                    arg_cmp_mesh_settings.append(mr)
                    arg_cmp_mesh_settings.append("MeshMethod:=")
                    if _mesh_method.lower() == "tau":
                        arg_cmp_mesh_settings.append("AnsoftTAU")
                    elif _mesh_method.lower() == "classic":
                        arg_cmp_mesh_settings.append("AnsoftClassic")
                    else:
                        arg_cmp_mesh_settings.append("Auto")
                    arg_cmp_mesh_settings.append("UseLegacyFaceterForTauVolumeMesh:=")
                    arg_cmp_mesh_settings.append(False)

                    arg_cmp_mesh_settings.append("DynamicSurfaceResolution:=")
                    arg_cmp_mesh_settings.append(_dynamic_surface_resolution)

                    arg_cmp_mesh_settings.append("UseFlexMeshingForTAUvolumeMesh:=")
                    arg_cmp_mesh_settings.append(_use_flex_mesh)

                    arg_cmp_mesh_settings.append("UseAlternativeMeshMethodsAsFallBack:=")
                    arg_cmp_mesh_settings.append(_use_fallback_mesh)

                    arg_cmp_mesh_settings.append("AllowPhiForLayeredGeometry:=")
                    arg_cmp_mesh_settings.append(_allow_phi_mesh)
                    arg_cmp.append(arg_cmp_mesh_settings)
                    arg_cmp.append("MeshAssemblyBoundingVolumePadding:=")
                    arg_cmp.append([str(i) for i in c3dobj.mesh_fusion.volume])

                arg_ma.append(arg_cmp)
        arg.append(arg_ma)
        arg_prio = ["NAME:Priority Components"]
        if priority_3d_component_list:
            arg_prio.extend(priority_3d_component_list)
        arg.append(arg_prio)
        try:
            self._primitives._app.odesign.SetDoMeshAssembly(arg)
        except:
            self._primitives.logger.error(
                "Failed to Setup mesh fusion. Check if it can be used or settings are correct."
            )
            return False
        return True


class UserDefinedComponent(object):
    """Manages object attributes for 3DComponent and User Defined Model.

    Parameters
    ----------
    primitives : :class:`pyaedt.modeler.Primitives3D.Primitives3D`
        Inherited parent object.
    name : str, optional
        Name of the component. The default value is ``None``.
    props : dict, optional
        Dictionary of properties. The default value is ``None``.
    component_type : str, optional
        Type of the component. The default value is ``None``.

    Examples
    --------
    Basic usage demonstrated with an HFSS design:

    >>> from pyaedt import Hfss
    >>> aedtapp = Hfss()
    >>> prim = aedtapp.modeler.user_defined_components

    Obtain user defined component names, to return a :class:`pyaedt.modeler.cad.components_3d.UserDefinedComponent`.

    >>> component_names = aedtapp.modeler.user_defined_components
    >>> component = aedtapp.modeler[component_names["3DC_Cell_Radome_In1"]]
    """

    def __init__(self, primitives, name=None, props=None, component_type=None):
        self._fix_udm_props = [
            "General[Name]",
            "Group",
            "Target Coordinate System",
            "Target Coordinate System/Choices",
            "Info[Name]",
            "Location",
            "Location/Choices",
            "Company",
            "Date",
            "Purpose",
            "Version",
        ]
        self._group_name = None
        self._is3dcomponent = None
        self._mesh_assembly = None
        if name:
            self._m_name = name
        else:
            self._m_name = _uname()
        self._parameters = {}
        self._parts = None
        self._primitives = primitives
        self._target_coordinate_system = "Global"
        self._is_updated = False
        self._all_props = None
        self._mesh_fusion = None
        defined_components = self._primitives.oeditor.Get3DComponentDefinitionNames()
        for component in defined_components:
            if self._m_name in self._primitives.oeditor.Get3DComponentInstanceNames(component):
                self.definition_name = component
                break
        if component_type:
            self.auto_update = False
            self._props = UserDefinedComponentProps(
                self,
                OrderedDict(
                    {
                        "TargetCS": self._target_coordinate_system,
                        "SubmodelDefinitionName": self.definition_name,
                        "ComponentPriorityLists": OrderedDict({}),
                        "NextUniqueID": 0,
                        "MoveBackwards": False,
                        "DatasetType": "ComponentDatasetType",
                        "DatasetDefinitions": OrderedDict({}),
                        "BasicComponentInfo": OrderedDict(
                            {
                                "ComponentName": self.definition_name,
                                "Company": "",
                                "Company URL": "",
                                "Model Number": "",
                                "Help URL": "",
                                "Version": "1.0",
                                "Notes": "",
                                "IconType": "",
                            }
                        ),
                        "GeometryDefinitionParameters": OrderedDict({"VariableOrders": OrderedDict({})}),
                        "DesignDefinitionParameters": OrderedDict({"VariableOrders": OrderedDict({})}),
                        "MaterialDefinitionParameters": OrderedDict({"VariableOrders": OrderedDict({})}),
                        "MapInstanceParameters": "DesignVariable",
                        "UniqueDefinitionIdentifier": "89d26167-fb77-480e-a7ab-"
                        + "".join(random.choice("abcdef0123456789") for _ in range(int(12))),
                        "OriginFilePath": "",
                        "IsLocal": False,
                        "ChecksumString": "",
                        "ChecksumHistory": [],
                        "VersionHistory": [],
                        "NativeComponentDefinitionProvider": OrderedDict({"Type": component_type}),
                        "InstanceParameters": OrderedDict(
                            {"GeometryParameters": "", "MaterialParameters": "", "DesignParameters": ""}
                        ),
                    }
                ),
            )
            if props:
                self._update_props(self._props["NativeComponentDefinitionProvider"], props)
            self.native_properties = self._props["NativeComponentDefinitionProvider"]
            self.auto_update = True

    @property
    def group_name(self):
        """Group the component belongs to.

        Returns
        -------
        str
            Name of the group.

        References
        ----------

        >>> oEditor.GetPropertyValue
        >>> oEditor.ChangeProperty

        """
        group = None
        if "Group" in self._primitives.oeditor.GetChildObject(self.name).GetPropNames():
            group = self._primitives.oeditor.GetChildObject(self.name).GetPropValue("Group")
        return group

    @group_name.setter
    def group_name(self, name):
        """Assign component to a specific group. A new group is created if the specified group doesn't exist.

        Parameters
        ----------
        name : str
            Name of the group to assign the component to. A group is created if the one
            specified does not exist.

        Returns
        -------
        str
            Name of the group.

        References
        ----------

        >>> oEditor.GetPropertyValue
        >>> oEditor.ChangeProperty

        """
        if "Group" in self._primitives.oeditor.GetChildObject(self.name).GetPropNames() and name not in list(
            self._primitives.oeditor.GetChildNames("Groups")
        ):
            arg = [
                "NAME:GroupParameter",
                "ParentGroupID:=",
                "Model",
                "Parts:=",
                "",
                "SubmodelInstances:=",
                "",
                "Groups:=",
                "",
            ]
            assigned_name = self._primitives.oeditor.CreateGroup(arg)
            self._primitives.oeditor.ChangeProperty(
                [
                    "NAME:AllTabs",
                    [
                        "NAME:Attributes",
                        ["NAME:PropServers", assigned_name],
                        ["NAME:ChangedProps", ["NAME:Name", "Value:=", name]],
                    ],
                ]
            )

        pcs = ["NAME:Group", "Value:=", name]
        self._change_property(pcs)
        self._group_name = name

    @property
    def is3dcomponent(self):
        """3DComponent flag.

        Returns
        -------
        bool
           ``True`` if a 3DComponent, ``False`` if a user-defined model.

        """
        definitions = list(self._primitives.oeditor.Get3DComponentDefinitionNames())
        for comp in definitions:
            if self.name in self._primitives.oeditor.Get3DComponentInstanceNames(comp):
                self._is3dcomponent = True
                return True
        self._is3dcomponent = False
        return False

    @property
    def mesh_assembly(self):
        """Mesh assembly flag.

        Returns
        -------
        bool
           ``True`` if mesh assembly is checked, ``None`` if a user-defined model.

        """
        key = "Do Mesh Assembly"
        if self.is3dcomponent and key in self._primitives.oeditor.GetChildObject(self.name).GetPropNames():
            ma = self._primitives.oeditor.GetChildObject(self.name).GetPropValue(key)
            self._mesh_assembly = ma
            return ma
        else:
            return None

    @mesh_assembly.setter
    def mesh_assembly(self, ma):
        key = "Do Mesh Assembly"
        if (
            self._parent.is3dcomponent
            and isinstance(ma, bool)
            and key in self._primitives.oeditor.GetChildObject(self.name).GetPropNames()
        ):
            self._primitives.oeditor.GetChildObject(self.name).SetPropValue(key, ma)
            self._mesh_assembly = ma

    @property
    def name(self):
        """Name of the object.

        Returns
        -------
        str
           Name of the object.

        References
        ----------

        >>> oEditor.GetPropertyValue
        >>> oEditor.ChangeProperty

        """
        return self._m_name

    @name.setter
    def name(self, component_name):
        if component_name not in self._primitives.user_defined_component_names + self._primitives.object_names + list(
            self._primitives.oeditor.Get3DComponentDefinitionNames()
        ):
            if component_name != self._m_name:
                pcs = ["NAME:Name", "Value:=", component_name]
                self._change_property(pcs)
                self._primitives.user_defined_components.update({component_name: self})
                del self._primitives.user_defined_components[self._m_name]
                self._project_dictionary = None
                self._m_name = component_name
        else:
            self._logger.warning("Name %s already assigned in the design", component_name)

    @property
    def parameters(self):
        """Component parameters.

        Returns
        -------
        dict
            :class:`pyaedt.modeler.cad.components_3d.UserDefinedComponentParameters`.

        References
        ----------

        >>> oEditor.GetPropertyValue
        >>> oEditor.ChangeProperty

        """
        self._parameters = None
        if self.is3dcomponent:
            parameters_tuple = list(self._primitives.oeditor.Get3DComponentParameters(self.name))
            parameters = {}
            for parameter in parameters_tuple:
                value = self._primitives.oeditor.GetChildObject(self.name).GetPropValue(parameter[0])
                parameters[parameter[0]] = value
            self._parameters = UserDefinedComponentParameters(self, parameters)
        else:
            props = list(self._primitives.oeditor.GetChildObject(self.name).GetPropNames())
            parameters_aedt = list(set(props) - set(self._fix_udm_props))
            parameter_name = [par for par in parameters_aedt if not re.findall(r"/", par)]
            parameters = {}
            for parameter in parameter_name:
                value = self._primitives.oeditor.GetChildObject(self.name).GetPropValue(parameter)
                parameters[parameter] = value
            self._parameters = UserDefinedComponentParameters(self, parameters)
        return self._parameters

    @property
    def parts(self):
        """Dictionary of objects that belong to the user-defined component.

        Returns
        -------
        dict
           :class:`pyaedt.modeler.Object3d`

        """
        component_parts = list(self._primitives.oeditor.GetChildObject(self.name).GetChildNames())
        parts_id = [
            self._primitives.object_id_dict[part] for part in self._primitives.object_id_dict if part in component_parts
        ]
        parts_dict = {part_id: self._primitives.objects[part_id] for part_id in parts_id}
        return parts_dict

    @property
    def target_coordinate_system(self):
        """Target coordinate system.

        Returns
        -------
        str
            Name of the target coordinate system.

        References
        ----------

        >>> oEditor.GetPropertyValue
        >>> oEditor.ChangeProperty

        """
        self._target_coordinate_system = None
        if "Target Coordinate System" in self._primitives.oeditor.GetChildObject(self.name).GetPropNames():
            tCS = self._primitives.oeditor.GetChildObject(self.name).GetPropValue("Target Coordinate System")
            self._target_coordinate_system = tCS
        return self._target_coordinate_system

    @target_coordinate_system.setter
    def target_coordinate_system(self, tCS):
        if (
            "Target Coordinate System" in self._primitives.oeditor.GetChildObject(self.name).GetPropNames()
            and "Target Coordinate System/Choices" in self._primitives.oeditor.GetChildObject(self.name).GetPropNames()
        ):
            tCS_options = list(
                self._primitives.oeditor.GetChildObject(self.name).GetPropValue("Target Coordinate System/Choices")
            )
            if tCS in tCS_options:
                pcs = ["NAME:Target Coordinate System", "Value:=", tCS]
                self._change_property(pcs)
                self._target_coordinate_system = tCS

    @pyaedt_function_handler()
    def delete(self):
        """Delete the object. The project must be saved after the operation to update the list
        of names for user-defined components.

        References
        ----------

        >>> oEditor.Delete

        Examples
        --------

        >>> from pyaedt import hfss
        >>> hfss = Hfss()
        >>> hfss.modeler["UDM"].delete()
        >>> hfss.save_project()
        >>> hfss._project_dictionary = None
        >>> udc = hfss.modeler.user_defined_component_names

        """
        arg = ["NAME:Selections", "Selections:=", self._m_name]
        self._m_Editor.Delete(arg)
        del self._primitives.modeler.user_defined_components[self.name]
        self._primitives.cleanup_objects()
        self.__dict__ = {}

    @pyaedt_function_handler()
    def mirror(self, position, vector):
        """Mirror a selection.

        Parameters
        ----------
        position : list, Position
            List of the ``[x, y, z]`` coordinates or
            the Application.Position object for the selection.
        vector : float
            List of the ``[x1, y1, z1]`` coordinates or
            the Application.Position object for the vector.

        Returns
        -------
        pyaedt.modeler.cad.components_3d.UserDefinedComponent, bool
            3D object when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.Mirror
        """
        if self.is3dcomponent:
            if self._primitives.modeler.mirror(self.name, position=position, vector=vector):
                return self
        else:
            for part in self.parts:
                self._primitives.modeler.mirror(part, position=position, vector=vector)
            return self
        return False

    @pyaedt_function_handler()
    def rotate(self, cs_axis, angle=90.0, unit="deg"):
        """Rotate the selection.

        Parameters
        ----------
        cs_axis
            Coordinate system axis or the Application.CoordinateSystemAxis object.
        angle : float, optional
            Angle of rotation. The units, defined by ``unit``, can be either
            degrees or radians. The default is ``90.0``.
        unit : text, optional
             Units for the angle. Options are ``"deg"`` or ``"rad"``.
             The default is ``"deg"``.

        Returns
        -------
        pyaedt.modeler.cad.components_3d.UserDefinedComponent, bool
            3D object when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.Rotate
        """
        if self.is3dcomponent:
            if self._primitives.modeler.rotate(self.name, cs_axis=cs_axis, angle=angle, unit=unit):
                return self
        else:
            for part in self.parts:
                self._primitives.modeler.rotate(part, cs_axis=cs_axis, angle=angle, unit=unit)
            return self
        return False

    @pyaedt_function_handler()
    def move(self, vector):
        """Move component from a list.

        Parameters
        ----------
        vector : list
            Vector of the direction move. It can be a list of the ``[x, y, z]``
            coordinates or a ``Position`` object.

        Returns
        -------
        pyaedt.modeler.cad.components_3d.UserDefinedComponent, bool
            3D object when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.Move
        """
        if self.is3dcomponent:
            if self._primitives.modeler.move(self.name, vector=vector):
                return self
        else:
            for part in self.parts:
                self._primitives.modeler.move(part, vector=vector)
            return self

        return False

    @pyaedt_function_handler()
    def duplicate_around_axis(self, cs_axis, angle=90, nclones=2, create_new_objects=True):
        """Duplicate the component around the axis.

        Parameters
        ----------
        cs_axis : Application.CoordinateSystemAxis object
            Coordinate system axis of the object.
        angle : float, optional
            Angle of rotation in degrees. The default is ``90``.
        nclones : int, optional
            Number of clones. The default is ``2``.
        create_new_objects : bool, optional
            Whether to create copies as new objects. The default is ``True``.

        Returns
        -------
        list
            List of names of the newly added objects.

        References
        ----------

        >>> oEditor.DuplicateAroundAxis

        """
        if self.is3dcomponent:
            ret, added_objects = self._primitives.modeler.duplicate_around_axis(
                self.name, cs_axis, angle, nclones, create_new_objects, True
            )
            return added_objects
        self._logger.warning("User-defined models do not support this operation.")
        return False

    @pyaedt_function_handler()
    def duplicate_along_line(self, vector, nclones=2, attach_object=False, **kwargs):
        """Duplicate the object along a line.

        Parameters
        ----------
        vector : list
            List of ``[x1 ,y1, z1]`` coordinates for the vector or the Application.Position object.
        nclones : int, optional
            Number of clones. The default is ``2``.
        attach_object : bool, optional
            Whether to attach the object. The default is ``False``.

        Returns
        -------
        list
            List of names of the newly added objects.

        References
        ----------

        >>> oEditor.DuplicateAlongLine

        """
        if "attachObject" in kwargs:
            warnings.warn(
                "``attachObject`` is deprecated. Use ``attach_object`` instead.",
                DeprecationWarning,
            )
            attach_object = kwargs["attachObject"]

        if self.is3dcomponent:
            _, added_objects = self._primitives.modeler.duplicate_along_line(
                self.name, vector, nclones, attach_object, True
            )
            return added_objects
        self._logger.warning("User-defined models do not support this operation.")
        return False

    @pyaedt_function_handler()
    def update_native(self):
        """Update the Native Component in AEDT.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """

        self.update_props = OrderedDict({})
        self.update_props["DefinitionName"] = self._props["SubmodelDefinitionName"]
        self.update_props["GeometryDefinitionParameters"] = self._props["GeometryDefinitionParameters"]
        self.update_props["DesignDefinitionParameters"] = self._props["DesignDefinitionParameters"]
        self.update_props["MaterialDefinitionParameters"] = self._props["MaterialDefinitionParameters"]
        self.update_props["NextUniqueID"] = self._props["NextUniqueID"]
        self.update_props["MoveBackwards"] = self._props["MoveBackwards"]
        self.update_props["DatasetType"] = self._props["DatasetType"]
        self.update_props["DatasetDefinitions"] = self._props["DatasetDefinitions"]
        self.update_props["NativeComponentDefinitionProvider"] = self._props["NativeComponentDefinitionProvider"]
        self.update_props["ComponentName"] = self._props["BasicComponentInfo"]["ComponentName"]
        self.update_props["Company"] = self._props["BasicComponentInfo"]["Company"]
        self.update_props["Model Number"] = self._props["BasicComponentInfo"]["Model Number"]
        self.update_props["Help URL"] = self._props["BasicComponentInfo"]["Help URL"]
        self.update_props["Version"] = self._props["BasicComponentInfo"]["Version"]
        self.update_props["Notes"] = self._props["BasicComponentInfo"]["Notes"]
        self.update_props["IconType"] = self._props["BasicComponentInfo"]["IconType"]
        self._primitives.oeditor.EditNativeComponentDefinition(self._get_args(self.update_props))

        return True

    @property
    def _logger(self):
        """Logger."""
        return self._primitives.logger

    @pyaedt_function_handler()
    def _get_args(self, props=None):
        if props is None:
            props = self.props
        arg = ["NAME:" + self.name]
        _dict2arg(props, arg)
        return arg

    @pyaedt_function_handler()
    def _change_property(self, vPropChange):
        return self._primitives._change_component_property(vPropChange, self._m_name)

    @pyaedt_function_handler()
    def _update_props(self, d, u):
        for k, v in u.items():
            if isinstance(v, (dict, OrderedDict)):
                if k not in d:
                    d[k] = OrderedDict({})
                d[k] = self._update_props(d[k], v)
            else:
                d[k] = v
        return d

    @property
    def _m_Editor(self):
        """Pointer to the oEditor object in the AEDT API. This property is
        intended primarily to be used by FacePrimitive, EdgePrimitive, and
        VertexPrimitive child objects.

        Returns
        -------
        oEditor COM Object

        """
        return self._primitives.oeditor

    def __str__(self):
        return """
         {}
         is3dcomponent: {}   parts: {}
         --- read/write properties  ----
         name: {}
         group_name: {}
         mesh_assembly: {}
         parameters: {}
         target_coordinate_system: {}
         """.format(
            type(self),
            self.is3dcomponent,
            self.parts,
            self.name,
            self.group_name,
            self.mesh_assembly,
            self.parameters,
            self.target_coordinate_system,
        )

    @pyaedt_function_handler()
    def edit_definition(self, password=""):
        """Edit 3d Definition. Open AEDT Project and return Pyaedt Object.

        Parameters
        ----------
        password : str, optional
            Password for encrypted models. The default value is ``""``.

        Returns
        -------
        :class:`pyaedt.hfss.Hfss` or :class:`pyaedt.Icepak.Icepak`
            Pyaedt object.
        """
        from pyaedt.generic.design_types import get_pyaedt_app

        self._primitives.oeditor.Edit3DComponentDefinition(
            [
                "NAME:EditDefinitionData",
                ["NAME:DefinitionAndPassword", "Definition:=", self.definition_name, "Password:=", password],
            ]
        )
        project = self._primitives._app.odesktop.GetActiveProject()
        project_name = project.GetName()
        design_name = project.GetActiveDesign().GetName()
        return get_pyaedt_app(project_name, design_name)

    @property
    def mesh_fusion(self):
        if not self._mesh_fusion:
            self._mesh_fusion = MeshFusion(self)
        return self._mesh_fusion
