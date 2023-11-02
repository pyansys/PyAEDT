from __future__ import absolute_import

from collections import OrderedDict
import os
import random
import re
import warnings

from pyaedt import Edb, pyaedt_function_handler
from pyaedt.generic.general_methods import _uname
from pyaedt.modeler.cad.elements3d import BinaryTreeNode, _dict2arg


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
        defined_components = self._primitives.oeditor.Get3DComponentDefinitionNames()
        defined_components = defined_components if defined_components else []
        for component in defined_components:
            if self._m_name in self._primitives.oeditor.Get3DComponentInstanceNames(component):
                self.definition_name = component
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

        self._layout_component = None

    @property
    def layout_component(self):
        """Layout component object.

        Returns
        -------
        :class:`LayoutComponent`
            Layout Component.

        References
        ----------
        >>> oEditor.GetPropertyValue
        >>> oEditor.ChangeProperty

        """
        if not self._layout_component and "Show Layout" in self._primitives._app.get_oo_properties(
            self._primitives.oeditor, self.name
        ):
            self._layout_component = LayoutComponent(self)
        return self._layout_component

    @pyaedt_function_handler()
    def history(self):
        """Component history.

        Returns
        -------
            :class:`pyaedt.modeler.cad.elements3d.BinaryTree` when successful,
            ``False`` when failed.

        """
        try:
            child_object = self._primitives.oeditor.GetChildObject(self.name)
            return BinaryTreeNode(list(child_object.GetChildNames("Operations"))[0], child_object, True, "Operations")
        except:
            return False

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
            self.is3dcomponent
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
        else:  # pragma: no cover
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
        if self.is3dcomponent:
            component_parts = list(self._primitives.oeditor.Get3DComponentPartNames(self.name))
        else:
            component_parts = list(self._primitives.oeditor.GetChildObject(self.name).GetChildNames())

        parts_id = [
            self._primitives._object_names_to_ids[part]
            for part in self._primitives._object_names_to_ids
            if part in component_parts
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
    def duplicate_and_mirror(self, position, vector):
        """Duplicate and mirror a selection.

        Parameters
        ----------
        position : float
            List of the ``[x, y, z]`` coordinates or
            Application.Position object for the selection.
        vector : float
            List of the ``[x1, y1, z1]`` coordinates or
            Application.Position object for the vector.

        Returns
        -------
        list
            List of objects created or an empty list.

        References
        ----------
        >>> oEditor.DuplicateMirror
        """
        return self._primitives.modeler.duplicate_and_mirror(
            self.name, position, vector, is_3d_comp=True, duplicate_assignment=True
        )

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
            Coordinate system axis or the Application.AXIS object.
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
        cs_axis : Application.AXIS object
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
            old_component_list = self._primitives.modeler.user_defined_component_names
            _, added_objects = self._primitives.modeler.duplicate_along_line(
                self.name, vector, nclones, attach_object, True
            )
            return list(set(added_objects) - set(old_component_list))
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
    def bounding_box(self):
        """Get bounding dimension of a user defined model.

        Returns
        -------
        list
            List of floats containing [x_min, y_min, z_min, x_max, y_max, z_max].

        """
        bb = [float("inf")] * 3 + [float("-inf")] * 3
        for _, obj in self.parts.items():
            bbox = obj.bounding_box
            bb = [min(bb[i], bbox[i]) for i in range(3)] + [max(bb[i + 3], bbox[i + 3]) for i in range(3)]
        return bb

    @property
    def center(self):
        """Get center coordinates of a user defined model.

        Returns
        -------
        list
            List of floats containing [x_center, y_center, z_center].

        """
        x_min, y_min, z_min, x_max, y_max, z_max = self.bounding_box
        x_center = (x_min + x_max) / 2
        y_center = (y_min + y_max) / 2
        z_center = (z_min + z_max) / 2
        return [x_center, y_center, z_center]

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
            self._is3dcomponent,
            self._parts,
            self._m_name,
            self._group_name,
            self._mesh_assembly,
            self._parameters,
            self._target_coordinate_system,
        )

    @pyaedt_function_handler()
    def get_component_filepath(self):
        """Get 3d component file path.

        Returns
        -------
        str
            Path of the 3d component file.
        """
        return self._primitives._app.get_oo_object(self._primitives._app.oeditor, self.definition_name).GetPropValue(
            "3D Component File Path"
        )

    @pyaedt_function_handler()
    def update_definition(self, password="", new_filepath=""):
        """Update 3d component definition.

        Parameters
        ----------
        password : str, optional
            Password for encrypted models. The default value is ``""``.
        new_filepath : str, optional
            New path containing the 3d component file. The default value is ``""``, which means
            that the 3d component file has not changed.

        Returns
        -------
        bool
            True if successful.
        """
        self._primitives._app.oeditor.UpdateComponentDefinition(
            [
                "NAME:UpdateDefinitionData",
                "ForLocalEdit:=",
                False,
                "DefinitionNames:=",
                self.definition_name,
                "Passwords:=",
                [password],
                "NewFilePath:=",
                new_filepath,
            ]
        )
        self._primitives._app.modeler.refresh_all_ids()
        return True

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
        # TODO: Edit documentation to include all supported returned classes.

        from pyaedt.generic.design_types import get_pyaedt_app

        # from pyaedt.generic.general_methods import is_linux

        project_list = [i for i in self._primitives._app.project_list]

        self._primitives.oeditor.Edit3DComponentDefinition(
            [
                "NAME:EditDefinitionData",
                ["NAME:DefinitionAndPassword", "Definition:=", self.definition_name, "Password:=", password],
            ]
        )

        new_project = [i for i in self._primitives._app.project_list if i not in project_list]

        if new_project:
            project = self._primitives._app.odesktop.SetActiveProject(new_project[0])
            # project = self._primitives._app.odesktop.GetActiveProject()
            project_name = project.GetName()
            project.GetDesigns()[0].GetName()
            design_name = project.GetDesigns()[0].GetName()
            # if is_linux:
            #     design_name = project.GetDesigns()[0].GetName()
            # else:
            #     design_name = project.GetActiveDesign().GetName()
            return get_pyaedt_app(project_name, design_name)
        return False


class LayoutComponent(object):
    """Manages object attributes for Layout components.

    Parameters
    ----------
    primitives : :class:`pyaedt.modeler.Primitives3D.Primitives3D`
        Inherited parent object.
    name : str, optional
        Name of the component. The default value is ``None``.

    """

    def __init__(self, component):
        self._primitives = component._primitives
        self._name = component.name
        self._component = component
        self._edb_definition = None
        self._show_layout = None
        self._fast_transformation = None
        self._show_dielectric = None
        self._display_mode = None
        self.layers = {}
        self.nets = {}
        self.objects = {}
        if self.edb_definition:
            self._get_edb_info()

    @property
    def edb_definition(self):
        """Edb definition.

        Returns
        -------
        str
           EDB definition.

        """
        key = "EDB Definition"
        if key in self._primitives._app.get_oo_properties(self._primitives.oeditor, self._component.definition_name):
            edb_definition = self._primitives._app.get_oo_property_value(
                self._primitives.oeditor, self._component.definition_name, key
            )
            self._edb_definition = edb_definition
            return edb_definition
        else:
            return None

    @property
    def show_layout(self):
        """Show layout flag.

        Returns
        -------
        bool
           `Show layout check box.

        """
        key = "Show Layout"
        if key in self._primitives._app.get_oo_properties(self._primitives.oeditor, self._name):
            show_layout = self._primitives._app.get_oo_property_value(self._primitives.oeditor, self._name, key)
            self._show_layout = show_layout
            return show_layout
        else:  # pragma: no cover
            return None

    @show_layout.setter
    def show_layout(self, show_layout):
        key = "Show Layout"
        if isinstance(show_layout, bool) and key in self._primitives._app.get_oo_properties(
            self._primitives.oeditor, self._name
        ):
            self._primitives.oeditor.GetChildObject(self._name).SetPropValue(key, show_layout)
            self._show_layout = show_layout

    @property
    def fast_transformation(self):
        """Show layout flag.

        Returns
        -------
        bool
           Fast transformation check box.

        """
        key = "Fast Transformation"
        if key in self._primitives._app.get_oo_properties(self._primitives.oeditor, self._name):
            fast_transformation = self._primitives._app.get_oo_property_value(self._primitives.oeditor, self._name, key)
            self._fast_transformation = fast_transformation
            return fast_transformation
        else:  # pragma: no cover
            return None

    @fast_transformation.setter
    def fast_transformation(self, fast_transformation):
        key = "Fast Transformation"
        if isinstance(fast_transformation, bool) and key in self._primitives._app.get_oo_properties(
            self._primitives.oeditor, self._name
        ):
            self._primitives.oeditor.GetChildObject(self._name).SetPropValue(key, fast_transformation)
            self._fast_transformation = fast_transformation

    @property
    def show_dielectric(self):
        """Show dielectric flag.

        Returns
        -------
        bool
           Show dielectric check box.

        """
        key = "Object Attributes/ShowDielectric"

        if key in self._primitives._app.get_oo_properties(self._primitives.oeditor, self._name):
            show_dielectric = self._primitives._app.get_oo_property_value(self._primitives.oeditor, self._name, key)
            self._show_dielectric = show_dielectric
            return show_dielectric
        else:  # pragma: no cover
            return None

    @show_dielectric.setter
    def show_dielectric(self, show_dielectric):
        key = "Object Attributes/ShowDielectric"
        if isinstance(show_dielectric, bool) and key in self._primitives._app.get_oo_properties(
            self._primitives.oeditor, self._name
        ):
            self._primitives.oeditor.GetChildObject(self._name).SetPropValue(key, show_dielectric)
            self._show_dielectric = show_dielectric

    @property
    def display_mode(self):
        """Show layout flag.

        Returns
        -------
        int
           Layout display mode. Available modes are:
            * 0 : Layer.
            * 1 : Net.
            * 2 : Object.

        """
        key = "Object Attributes/DisplayMode"

        if key in self._primitives._app.get_oo_properties(self._primitives.oeditor, self._name):
            display_mode = self._primitives._app.get_oo_property_value(self._primitives.oeditor, self._name, key)
            self._display_mode = display_mode
            return display_mode
        else:  # pragma: no cover
            return None

    @display_mode.setter
    def display_mode(self, display_mode):
        key = "Object Attributes/DisplayMode"
        if isinstance(display_mode, int) and key in self._primitives._app.get_oo_properties(
            self._primitives.oeditor, self._name
        ):
            self._primitives.oeditor.GetChildObject(self._name).SetPropValue(key, display_mode)
            self._display_mode = display_mode

    @pyaedt_function_handler()
    def _get_edb_info(self):
        """Get Edb information."""
        # Open Layout component and get information
        aedb_component_path = os.path.join(
            self._primitives._app.project_file[:-1] + "b",
            "LayoutComponents",
            self._edb_definition,
            self._edb_definition + ".aedb",
        )

        if not os.path.exists(aedb_component_path):  # pragma: no cover
            return False

        component_obj = Edb(
            edbpath=aedb_component_path,
            isreadonly=True,
            edbversion=self._primitives._app._aedt_version,
            student_version=self._primitives._app.student_version,
        )

        # Get objects, nets and layers
        self.nets = {key: [True, False, 60] for key in component_obj.nets.netlist}
        self.layers = {key: [True, False, 60] for key in list(component_obj.stackup.stackup_layers.keys())}
        self.objects = {key: [True, False, 60] for key in list(component_obj.components.instances.keys())}

        component_obj.close_edb()

        return True

    @pyaedt_function_handler()
    def update_visibility(self):
        """Update layer visibility.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.ChangeProperty
        """
        vPropChange = [
            "NAME:Object Attributes",
            "ShowDielectric:=",
            self.show_dielectric,
            "DisplayMode:=",
            self.display_mode,
        ]

        if self.layers:
            layer_mode = ["NAME:ObjectAttributesInLayerMode"]
            for layer in self.layers:
                layer_mode.append(layer + ":=")
                layer_mode.append(self.layers[layer])
            vPropChange.append(layer_mode)
        if self.nets:
            net_mode = ["NAME:ObjectAttributesInNetMode"]
            for net in self.nets:
                net_mode.append(layer + ":=")
                net_mode.append(self.nets[net])
            vPropChange.append(net_mode)
        if self.objects:
            objects_mode = ["NAME:ObjectAttributesInObjectMode"]
            for objects in self.objects:
                objects_mode.append(objects + ":=")
                objects_mode.append(self.objects[objects])
            vPropChange.append(objects_mode)

        vChangedProps = ["NAME:ChangedProps", vPropChange]
        vPropServers = ["NAME:PropServers", self._name]
        vGeo3d = ["NAME:Visualization", vPropServers, vChangedProps]
        vOut = ["NAME:AllTabs", vGeo3d]
        self._primitives.oeditor.ChangeProperty(vOut)

        return True
