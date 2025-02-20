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

"""
This module contains these classes: `BaseCoordinateSystem`, `FaceCoordinateSystem`, `CoordinateSystem`, `Modeler`,
`Position`, and `SweepOptions`.

This modules provides functionalities for the 3D Modeler, 2D Modeler,
3D Layout Modeler, and Circuit Modeler.
"""

from ansys.aedt.core.generic.data_handlers import _dict2arg
from ansys.aedt.core.generic.general_methods import PropsManager
from ansys.aedt.core.generic.general_methods import generate_unique_name
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.generic.general_methods import settings
from ansys.aedt.core.modeler.cad.elements_3d import EdgePrimitive
from ansys.aedt.core.modeler.cad.elements_3d import FacePrimitive
from ansys.aedt.core.modeler.cad.elements_3d import VertexPrimitive
from ansys.aedt.core.modeler.cad.object_3d import Object3d
from ansys.aedt.core.modeler.geometry_operators import GeometryOperators


class CsProps(dict):
    """AEDT Cooardinate System Internal Parameters."""

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        if self._pyaedt_cs.auto_update:
            res = self._pyaedt_cs.update()
            if not res:
                self._pyaedt_cs._app.logger.warning("Update of %s Failed. Check needed arguments", key)

    def __init__(self, cs_object, props):
        dict.__init__(self)
        if props:
            for key, value in props.items():
                if isinstance(value, dict):
                    dict.__setitem__(self, key, CsProps(cs_object, value))
                else:
                    dict.__setitem__(self, key, value)
        self._pyaedt_cs = cs_object

    def _setitem_without_update(self, key, value):
        dict.__setitem__(self, key, value)


class ListsProps(dict):
    """AEDT Lists Internal Parameters."""

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        if self._pyaedt_lists.auto_update:
            res = self._pyaedt_lists.update()
            if not res:
                self._pyaedt_lists._app.logger.warning("Update of %s Failed. Check needed arguments", key)

    def __init__(self, cs_object, props):
        dict.__init__(self)
        if props:
            for key, value in props.items():
                if isinstance(value, dict):
                    dict.__setitem__(self, key, CsProps(cs_object, value))
                else:
                    dict.__setitem__(self, key, value)
        self._pyaedt_lists = cs_object

    def _setitem_without_update(self, key, value):
        dict.__setitem__(self, key, value)


class BaseCoordinateSystem(PropsManager, object):
    """Base methods common to FaceCoordinateSystem and CoordinateSystem.

    Parameters
    ----------
    modeler :
        Inherited parent object.
    props : dict, optional
        Dictionary of properties. The default is ``None``.
    name : optional
        The default is ``None``.

    """

    def __init__(self, modeler, name=None):
        self.auto_update = True
        self._modeler = modeler
        self.model_units = self._modeler.model_units
        self.name = name

    def _get_coordinates_data(self):
        self._props = {}
        id2name = {1: "Global"}
        name2refid = {}
        if self._modeler._app.design_properties and "ModelSetup" in self._modeler._app.design_properties:
            cs = self._modeler._app.design_properties["ModelSetup"]["GeometryCore"]["GeometryOperations"][
                "CoordinateSystems"
            ]
            for ds in cs:
                try:
                    if isinstance(cs[ds], dict):
                        if cs[ds]["OperationType"] == "CreateRelativeCoordinateSystem":
                            props = cs[ds]["RelativeCSParameters"]
                            name = cs[ds]["Attributes"]["Name"]
                            if name != self.name:
                                continue
                            cs_id = cs[ds]["ID"]
                            id2name[cs_id] = name
                            name2refid[name] = cs[ds]["ReferenceCoordSystemID"]
                            self._props = CsProps(self, props)
                            if "ZXZ" in props["Mode"]:
                                self.mode = "zxz"
                            elif "ZYZ" in props["Mode"]:
                                self.mode = "zyz"
                            else:
                                self.mode = "axis"
                        elif cs[ds]["OperationType"] == "CreateFaceCoordinateSystem":
                            name = cs[ds]["Attributes"]["Name"]
                            if name != self.name:
                                continue
                            cs_id = cs[ds]["ID"]
                            id2name[cs_id] = name
                            op_id = cs[ds]["PlaceHolderOperationID"]
                            geometry_part = self._modeler._app.design_properties["ModelSetup"]["GeometryCore"][
                                "GeometryOperations"
                            ]["ToplevelParts"]["GeometryPart"]
                            if isinstance(geometry_part, dict):
                                op = geometry_part["Operations"]["FaceCSHolderOperation"]
                                if isinstance(op, dict):
                                    if op["ID"] == op_id:
                                        props = op["FaceCSParameters"]
                                        self._props = CsProps(self, props)
                                elif isinstance(op, list):
                                    for iop in op:
                                        if iop["ID"] == op_id:
                                            props = iop["FaceCSParameters"]
                                            self._props = CsProps(self, props)
                                            break
                            elif isinstance(geometry_part, list):
                                for gp in geometry_part:
                                    op = gp["Operations"]["FaceCSHolderOperation"]
                                    if isinstance(op, dict):
                                        if op["ID"] == op_id:
                                            props = op["FaceCSParameters"]
                                            self._props = CsProps(self, props)
                                    elif isinstance(op, list):
                                        for iop in op:
                                            if iop["ID"] == op_id:
                                                props = iop["FaceCSParameters"]
                                                self._props = CsProps(self, props)
                                                break
                        elif cs[ds]["OperationType"] == "CreateObjectCoordinateSystem":
                            name = cs[ds]["Attributes"]["Name"]
                            if name != self.name:
                                continue
                            cs_id = cs[ds]["ID"]
                            id2name[cs_id] = name
                            op_id = cs[ds]["PlaceHolderOperationID"]
                            geometry_part = self._modeler._app.design_properties["ModelSetup"]["GeometryCore"][
                                "GeometryOperations"
                            ]["ToplevelParts"]["GeometryPart"]
                            if isinstance(geometry_part, dict):
                                op = geometry_part["Operations"]["ObjectCSHolderOperation"]
                                if isinstance(op, dict):
                                    if op["ID"] == op_id:
                                        props = op["ObjectCSParameters"]
                                        self._props = CsProps(self, props)
                                elif isinstance(op, list):
                                    for iop in op:
                                        if iop["ID"] == op_id:
                                            props = iop["ObjectCSParameters"]
                                            self._props = CsProps(self, props)
                                            break
                            elif isinstance(geometry_part, list):
                                for gp in geometry_part:
                                    op = gp["Operations"]["ObjectCSHolderOperation"]
                                    if isinstance(op, dict):
                                        if op["ID"] == op_id:
                                            props = op["ObjectCSParameters"]
                                            self._props = CsProps(self, props)
                                    elif isinstance(op, list):
                                        for iop in op:
                                            if iop["ID"] == op_id:
                                                props = iop["ObjectCSParameters"]
                                                self._props = CsProps(self, props)
                                                break
                    elif isinstance(cs[ds], list):
                        for el in cs[ds]:
                            if el["OperationType"] == "CreateRelativeCoordinateSystem":
                                props = el["RelativeCSParameters"]
                                name = el["Attributes"]["Name"]
                                if name != self.name:
                                    continue
                                cs_id = el["ID"]
                                id2name[cs_id] = name
                                name2refid[name] = el["ReferenceCoordSystemID"]
                                self._props = CsProps(self, props)
                                if "ZXZ" in props["Mode"]:
                                    self.mode = "zxz"
                                elif "ZYZ" in props["Mode"]:
                                    self.mode = "zyz"
                                else:
                                    self.mode = "axis"
                            elif el["OperationType"] == "CreateFaceCoordinateSystem":
                                name = el["Attributes"]["Name"]
                                if name != self.name:
                                    continue
                                cs_id = el["ID"]
                                id2name[cs_id] = name
                                op_id = el["PlaceHolderOperationID"]
                                geometry_part = self._modeler._app.design_properties["ModelSetup"]["GeometryCore"][
                                    "GeometryOperations"
                                ]["ToplevelParts"]["GeometryPart"]
                                if isinstance(geometry_part, dict):
                                    op = geometry_part["Operations"]["FaceCSHolderOperation"]
                                    if isinstance(op, dict):
                                        if op["ID"] == op_id:
                                            props = op["FaceCSParameters"]
                                            self._props = CsProps(self, props)
                                    elif isinstance(op, list):
                                        for iop in op:
                                            if iop["ID"] == op_id:
                                                props = iop["FaceCSParameters"]
                                                self._props = CsProps(self, props)
                                                break
                                elif isinstance(geometry_part, list):
                                    for gp in geometry_part:
                                        try:
                                            op = gp["Operations"]["FaceCSHolderOperation"]
                                        except KeyError:
                                            continue
                                        if isinstance(op, dict):
                                            if op["ID"] == op_id:
                                                props = op["FaceCSParameters"]
                                                self._props = CsProps(self, props)
                                        elif isinstance(op, list):
                                            for iop in op:
                                                if iop["ID"] == op_id:
                                                    props = iop["FaceCSParameters"]
                                                    self._props = CsProps(self, props)
                                                    break
                            elif el["OperationType"] == "CreateObjectCoordinateSystem":
                                name = el["Attributes"]["Name"]
                                if name != self.name:
                                    continue
                                cs_id = el["ID"]
                                id2name[cs_id] = name
                                op_id = el["PlaceHolderOperationID"]
                                geometry_part = self._modeler._app.design_properties["ModelSetup"]["GeometryCore"][
                                    "GeometryOperations"
                                ]["ToplevelParts"]["GeometryPart"]
                                if isinstance(geometry_part, dict):
                                    op = geometry_part["Operations"]["ObjectCSHolderOperation"]
                                    if isinstance(op, dict):
                                        if op["ID"] == op_id:
                                            props = op["ObjectCSParameters"]
                                            self._props = CsProps(self, props)
                                    elif isinstance(op, list):
                                        for iop in op:
                                            if iop["ID"] == op_id:
                                                props = iop["ObjectCSParameters"]
                                                self._props = CsProps(self, props)
                                                break
                                elif isinstance(geometry_part, list):
                                    for gp in geometry_part:
                                        try:
                                            op = gp["Operations"]["ObjectCSHolderOperation"]
                                        except KeyError:
                                            continue
                                        if isinstance(op, dict):
                                            if op["ID"] == op_id:
                                                props = op["ObjectCSParameters"]
                                                self._props = CsProps(self, props)
                                        elif isinstance(op, list):
                                            for iop in op:
                                                if iop["ID"] == op_id:
                                                    props = iop["ObjectCSParameters"]
                                                    self._props = CsProps(self, props)
                                                    break
                except Exception:
                    self._modeler._app.logger.debug(f"Failed to get coordinate data using {ds}")

    @pyaedt_function_handler()
    def set_as_working_cs(self):
        """Set the coordinate system as the working coordinate system.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        self._modeler.oeditor.SetWCS(
            ["NAME:SetWCS Parameter", "Working Coordinate System:=", self.name, "RegionDepCSOk:=", False]
        )
        return True

    @pyaedt_function_handler()
    def _change_property(self, name, arg):
        """Update properties of the coordinate system.

        Parameters
        ----------
        name : str
            Name of the coordinate system.
        arg : list
            List of the properties to update. For example,
            ``["NAME:ChangedProps", ["NAME:Mode", "Value:=", "Axis/Position"]]``.

        Returns
        -------
        list
            List of changed properties of the coordinate system.

        """
        arguments = ["NAME:AllTabs", ["NAME:Geometry3DCSTab", ["NAME:PropServers", name], arg]]
        self._modeler.oeditor.ChangeProperty(arguments)

    @pyaedt_function_handler(newname="name")
    def rename(self, name):
        """Rename the coordinate system.

        Parameters
        ----------
        name : str
            New name for the coordinate system.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        self._change_property(self.name, ["NAME:ChangedProps", ["NAME:Name", "Value:=", name]])
        self.name = name
        return True

    @pyaedt_function_handler()
    def delete(self):
        """Delete the coordinate system.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------
        Delete all coordinate systems in the design.

        >>> from ansys.aedt.core import Maxwell2d
        >>> app = Maxwell2d()
        >>> cs_copy = [i for i in app.modeler.coordinate_systems]
        >>> [i.delete() for i in cs_copy]
        """
        try:
            self._modeler.oeditor.Delete(["NAME:Selections", "Selections:=", self.name])
            self._modeler.coordinate_systems.pop(self._modeler.coordinate_systems.index(self))
            coordinate_systems = self._modeler._app.oeditor.GetCoordinateSystems()
            for cs in self._modeler.coordinate_systems[:]:
                if cs.name not in coordinate_systems:
                    self._modeler.coordinate_systems.pop(self._modeler.coordinate_systems.index(cs))
            self._modeler.cleanup_objects()
        except Exception:
            self._modeler._app.logger.warning("Coordinate system does not exist")
        return True


class FaceCoordinateSystem(BaseCoordinateSystem, object):
    """Manages face coordinate system data and execution.

    Parameters
    ----------
    modeler :
        Inherited parent object.
    props : dict, optional
        Dictionary of properties. The default is ``None``.
    name : optional
        The default is ``None``.
    face_id : int
        Id of the face where the Face Coordinate System is laying.

    """

    def __init__(self, modeler, props=None, name=None, face_id=None):
        BaseCoordinateSystem.__init__(self, modeler, name)
        self.face_id = face_id
        self._props = None
        if props:
            self._props = CsProps(self, props)
            if "KernelVersion" in self.props:
                del self.props["KernelVersion"]

    @property
    def props(self):
        """Properties of the coordinate system.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.Modeler.CSProps`
        """
        if self._props or settings.aedt_version <= "2022.2" or self.name is None:
            return self._props
        self._get_coordinates_data()
        return self._props

    @property
    def _part_name(self):
        """Internally get the part name which the face belongs to."""
        if not self.face_id:
            # face_id has not been defined yet
            return None
        for obj in self._modeler.objects.values():
            for face in obj.faces:
                if face.id == self.face_id:
                    return obj.name
        return None  # part has not been found

    @property
    def _face_parameters(self):
        """Internally named array with parameters of the face coordinate system."""
        arg = ["Name:FaceCSParameters"]
        _dict2arg(self.props, arg)
        return arg

    @property
    def _attributes(self):
        """Internal named array for attributes of the face coordinate system."""
        coordinateSystemAttributes = ["NAME:Attributes", "Name:=", self.name, "PartName:=", self._part_name]
        return coordinateSystemAttributes

    @pyaedt_function_handler(face="assignment")
    def create(
        self, assignment, origin, axis_position, axis="X", name=None, offset=None, rotation=0, always_move_to_end=True
    ):
        """Create a face coordinate system.

        The face coordinate has always the Z axis parallel to face normal.
        The X and Y axis lie on the face plane.

        Parameters
        ----------
        assignment : int, FacePrimitive
            Face where the coordinate system is defined.
        origin : int, FacePrimitive, EdgePrimitive, VertexPrimitive
            Specify the coordinate system origin. The origin must belong to the face where the
            coordinate system is defined.
            If a face is specified, the origin is placed on the face center. It must be the same as ``face``.
            If an edge is specified, the origin is placed on the edge midpoint.
            If a vertex is specified, the origin is placed on the vertex.
        axis_position : int, FacePrimitive, EdgePrimitive, VertexPrimitive
            Specify where the X or Y axis is pointing. The position must belong to the face where the
            coordinate system is defined.
            Select which axis is considered with the option ``axis``.
            If a face is specified, the position is placed on the face center. It must be the same as ``face``.
            If an edge is specified, the position is placed on the edce midpoint.
            If a vertex is specified, the position is placed on the vertex.
        axis : str, optional
            Select which axis is considered for positioning. Possible values are ``"X"`` and ``"Y"``.
            The default is ``"X"``.
        name : str, optional
            Name of the coordinate system. The default is ``None``.
        offset : list, optional
            List of the ``[x, y]`` coordinates specifying the offset of the coordinate system origin.
            The offset specified in the face coordinate system reference.
            The default is ``[0, 0]``.
        rotation : float, optional
            Rotation angle of the coordinate system around its Z axis. Angle is in degrees.
            The default is ``0``.
        always_move_to_end : bool, optional
            If ``True`` the Face Coordinate System creation operation will always be moved to the end of subsequent
            objects operation. This will guarantee that the coordinate system will remain solidal with the object
            face. If ``False`` the option "Always Move CS to End" is set to off. The default is ``True``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """

        face_id = self._modeler.convert_to_selections(assignment, True)[0]
        if not isinstance(face_id, int):  # pragma: no cover
            raise ValueError("Unable to find reference face.")
        else:
            self.face_id = face_id

        if isinstance(origin, int):
            origin_id = origin
            o_type = self._get_type_from_id(origin)
        else:
            origin_id = self._modeler.convert_to_selections(origin, True)[0]
            if not isinstance(origin_id, int):  # pragma: no cover
                raise ValueError("Unable to find origin reference.")
            o_type = self._get_type_from_object(origin)
        if o_type == "Face":
            origin_position_type = "FaceCenter"
        elif o_type == "Edge":
            origin_position_type = "EdgeCenter"
        elif o_type == "Vertex":
            origin_position_type = "OnVertex"
        else:  # pragma: no cover
            raise ValueError("origin must identify either Face or Edge or Vertex.")

        if isinstance(axis_position, int):
            axis_position_id = axis_position
            o_type = self._get_type_from_id(axis_position)
        else:
            axis_position_id = self._modeler.convert_to_selections(axis_position, True)[0]
            if not isinstance(axis_position_id, int):  # pragma: no cover
                raise ValueError("Unable to find origin reference.")
            o_type = self._get_type_from_object(axis_position)
        if o_type == "Face":
            axis_position_type = "FaceCenter"
        elif o_type == "Edge":
            axis_position_type = "EdgeCenter"
        elif o_type == "Vertex":
            axis_position_type = "OnVertex"
        else:  # pragma: no cover
            raise ValueError("axis_position must identify either Face or Edge or Vertex.")

        if axis != "X" and axis != "Y":  # pragma: no cover
            raise ValueError("axis must be either 'X' or 'Y'.")

        if name:
            self.name = name
        else:
            self.name = generate_unique_name("Face_CS")

        if not offset:
            offset = [0, 0]

        originParameters = {}
        originParameters["IsAttachedToEntity"] = True
        originParameters["EntityID"] = origin_id
        originParameters["FacetedBodyTriangleIndex"] = -1
        originParameters["TriangleVertexIndex"] = -1
        originParameters["PositionType"] = origin_position_type
        originParameters["UParam"] = 0
        originParameters["VParam"] = 0
        originParameters["XPosition"] = "0"
        originParameters["YPosition"] = "0"
        originParameters["ZPosition"] = "0"

        positioningParameters = {}
        positioningParameters["IsAttachedToEntity"] = True
        positioningParameters["EntityID"] = axis_position_id
        positioningParameters["FacetedBodyTriangleIndex"] = -1
        positioningParameters["TriangleVertexIndex"] = -1
        positioningParameters["PositionType"] = axis_position_type
        positioningParameters["UParam"] = 0
        positioningParameters["VParam"] = 0
        positioningParameters["XPosition"] = "0"
        positioningParameters["YPosition"] = "0"
        positioningParameters["ZPosition"] = "0"

        parameters = {}
        parameters["Origin"] = originParameters
        parameters["MoveToEnd"] = always_move_to_end
        parameters["FaceID"] = face_id
        parameters["AxisPosn"] = positioningParameters
        parameters["WhichAxis"] = axis
        parameters["ZRotationAngle"] = str(rotation) + "deg"
        parameters["XOffset"] = self._modeler._app.value_with_units((offset[0]), self.model_units)
        parameters["YOffset"] = self._modeler._app.value_with_units((offset[1]), self.model_units)
        parameters["AutoAxis"] = False

        self._props = CsProps(self, parameters)
        self._modeler.oeditor.CreateFaceCS(self._face_parameters, self._attributes)
        self._modeler._coordinate_systems.insert(0, self)
        return True

    @pyaedt_function_handler()
    def _get_type_from_id(self, obj_id):
        """Get the entity type from the id."""
        for obj in self._modeler.objects.values():
            if obj.id == obj_id:
                return "3dObject"
            for face in obj.faces:
                if face.id == obj_id:
                    return "Face"
                for edge in face.edges:
                    if edge.id == obj_id:
                        return "Edge"
                    for vertex in edge.vertices:
                        if vertex.id == obj_id:
                            return "Vertex"
        raise ValueError(f"Cannot find entity id {obj_id}")  # pragma: no cover

    @pyaedt_function_handler()
    def _get_type_from_object(self, obj):
        """Get the entity type from the object."""
        if isinstance(obj, FacePrimitive):
            return "Face"
        elif isinstance(obj, EdgePrimitive):
            return "Edge"
        elif isinstance(obj, VertexPrimitive):
            return "Vertex"
        elif isinstance(obj, Object3d):
            return "3dObject"
        else:  # pragma: no cover
            raise ValueError("Cannot detect the entity type.")

    @pyaedt_function_handler()
    def update(self):
        """Update the coordinate system.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        try:
            self._change_property(
                self.name, ["NAME:ChangedProps", ["NAME:Z Rotation angle", "Value:=", self.props["ZRotationAngle"]]]
            )
        except Exception:  # pragma: no cover
            raise ValueError("'Z Rotation angle' parameter must be a string in the format '10deg'")

        try:
            self._change_property(
                self.name,
                [
                    "NAME:ChangedProps",
                    ["NAME:Position Offset XY", "X:=", self.props["XOffset"], "Y:=", self.props["YOffset"]],
                ],
            )
        except Exception:  # pragma: no cover
            raise ValueError("'XOffset' and 'YOffset' parameters must be a string in the format '1.3mm'")

        try:
            self._change_property(self.name, ["NAME:ChangedProps", ["NAME:Axis", "Value:=", self.props["WhichAxis"]]])
        except Exception:  # pragma: no cover
            raise ValueError("'WhichAxis' parameter must be either 'X' or 'Y'")

        return True


class CoordinateSystem(BaseCoordinateSystem, object):
    """Manages coordinate system data and execution.

    Parameters
    ----------
    modeler :
        Inherited parent object.
    props : dict, optional
        Dictionary of properties. The default is ``None``.
    name : optional
        The default is ``None``.

    """

    def __init__(self, modeler, props=None, name=None):
        BaseCoordinateSystem.__init__(self, modeler, name)
        self.model_units = self._modeler.model_units
        self._props = None
        if props:
            self._props = CsProps(self, props)
            if "KernelVersion" in self.props:
                del self.props["KernelVersion"]
        self._ref_cs = None
        self._quaternion = None
        self._mode = None

    @property
    def mode(self):
        """Coordinate System mode."""
        if self._mode:
            return self._mode
        mode_parameter = self.props.get("Mode", "")
        if "Axis" in mode_parameter:
            self._mode = "axis"
        if "ZXZ" in mode_parameter:
            self._mode = "zxz"
        elif "ZYZ" in mode_parameter:
            self._mode = "zyz"
        return self._mode

    @mode.setter
    def mode(self, value):
        self._mode = value

    @property
    def props(self):
        """Coordinate System Properties.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.Modeler.CSProps`
        """
        if self._props or settings.aedt_version <= "2022.2" or self.name is None:
            return self._props
        self._get_coordinates_data()
        return self._props

    @property
    def ref_cs(self):
        """Reference coordinate system getter and setter.

        Returns
        -------
        str
        """
        if self._ref_cs or settings.aedt_version <= "2022.2":
            return self._ref_cs
        obj1 = self._modeler.oeditor.GetChildObject(self.name)
        self._ref_cs = obj1.GetPropValue("Reference CS")
        return self._ref_cs

    @ref_cs.setter
    def ref_cs(self, value):
        if settings.aedt_version <= "2022.2":
            self._ref_cs = value
            self.update()
        obj1 = self._modeler.oeditor.GetChildObject(self.name)
        try:
            obj1.SetPropValue("Reference CS", value)
            self._ref_cs = value
        except Exception:
            self._modeler.logger.error("Failed to set Coordinate CS Reference.")

    @pyaedt_function_handler()
    def update(self):
        """Update the coordinate system.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        self._change_property(self.name, ["NAME:ChangedProps", ["NAME:Reference CS", "Value:=", self.ref_cs]])

        try:
            self._change_property(self.name, ["NAME:ChangedProps", ["NAME:Mode", "Value:=", self.props["Mode"]]])
        except Exception:  # pragma: no cover
            raise ValueError(
                f"'Mode must be 'Axis/Position', 'Euler Angle ZYZ' or 'Euler Angle ZXZ', not {self.props['Mode']}."
            )

        props = ["NAME:ChangedProps"]

        props.append(
            [
                "NAME:Origin",
                "X:=",
                self._modeler._app.value_with_units(self.props["OriginX"]),
                "Y:=",
                self._modeler._app.value_with_units(self.props["OriginY"]),
                "Z:=",
                self._modeler._app.value_with_units(self.props["OriginZ"]),
            ]
        )

        if self.props["Mode"] == "Axis/Position":
            props.append(
                [
                    "NAME:X Axis",
                    "X:=",
                    self._modeler._app.value_with_units(self.props["XAxisXvec"]),
                    "Y:=",
                    self._modeler._app.value_with_units(self.props["XAxisYvec"]),
                    "Z:=",
                    self._modeler._app.value_with_units(self.props["XAxisZvec"]),
                ]
            )
            props.append(
                [
                    "NAME:Y Point",
                    "X:=",
                    self._modeler._app.value_with_units(self.props["YAxisXvec"]),
                    "Y:=",
                    self._modeler._app.value_with_units(self.props["YAxisYvec"]),
                    "Z:=",
                    self._modeler._app.value_with_units(self.props["YAxisZvec"]),
                ]
            )
        else:
            props.append(["NAME:Phi", "Value:=", self._modeler._app.value_with_units(self.props["Phi"], "deg")])

            props.append(["NAME:Theta", "Value:=", self._modeler._app.value_with_units(self.props["Theta"], "deg")])

            props.append(["NAME:Psi", "Value:=", self._modeler._app.value_with_units(self.props["Psi"], "deg")])

        self._change_property(self.name, props)
        self._quaternion = None
        return True

    @pyaedt_function_handler()
    def change_cs_mode(self, mode_type=0):
        """Change the mode of the coordinate system.

        Parameters
        ----------
        mode_type : int, optional
            Type of the mode. Options are:

            * ``0`` - Axis/Position
            * ``1`` - Euler Angle ZXZ
            * ``2`` - Euler Angle ZYZ

            The default is ``0``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        legacy_update = self.auto_update
        self.auto_update = False
        if mode_type == 0:  # "Axis/Position"
            if self.props and (self.props["Mode"] == "Euler Angle ZXZ" or self.props["Mode"] == "Euler Angle ZYZ"):
                self.props["Mode"] = "Axis/Position"
                x, y, z = GeometryOperators.quaternion_to_axis(self.quaternion)
                xaxis = x
                ypoint = y
                self.props["XAxisXvec"] = xaxis[0]
                self.props["XAxisYvec"] = xaxis[1]
                self.props["XAxisZvec"] = xaxis[2]
                self.props["YAxisXvec"] = ypoint[0]
                self.props["YAxisYvec"] = ypoint[1]
                self.props["YAxisZvec"] = ypoint[2]
                del self.props["Phi"]
                del self.props["Theta"]
                del self.props["Psi"]
                self.mode = "axis"
                self.update()
        elif mode_type == 1:  # "Euler Angle ZXZ"
            if self.props and self.props["Mode"] == "Euler Angle ZYZ":
                self.props["Mode"] = "Euler Angle ZXZ"
                a, b, g = GeometryOperators.quaternion_to_euler_zxz(self.quaternion)
                phi = GeometryOperators.rad2deg(a)
                theta = GeometryOperators.rad2deg(b)
                psi = GeometryOperators.rad2deg(g)
                self.props["Phi"] = f"{phi}deg"
                self.props["Theta"] = f"{theta}deg"
                self.props["Psi"] = f"{psi}deg"
                self.mode = "zxz"
                self.update()
            elif self.props and self.props["Mode"] == "Axis/Position":
                self.props["Mode"] = "Euler Angle ZXZ"
                a, b, g = GeometryOperators.quaternion_to_euler_zxz(self.quaternion)
                phi = GeometryOperators.rad2deg(a)
                theta = GeometryOperators.rad2deg(b)
                psi = GeometryOperators.rad2deg(g)
                self.props["Phi"] = f"{phi}deg"
                self.props["Theta"] = f"{theta}deg"
                self.props["Psi"] = f"{psi}deg"
                del self.props["XAxisXvec"]
                del self.props["XAxisYvec"]
                del self.props["XAxisZvec"]
                del self.props["YAxisXvec"]
                del self.props["YAxisYvec"]
                del self.props["YAxisZvec"]
                self.mode = "zxz"
                self.update()
        elif mode_type == 2:  # "Euler Angle ZYZ"
            if self.props and self.props["Mode"] == "Euler Angle ZXZ":
                self.props["Mode"] = "Euler Angle ZYZ"
                a, b, g = GeometryOperators.quaternion_to_euler_zyz(self.quaternion)
                phi = GeometryOperators.rad2deg(a)
                theta = GeometryOperators.rad2deg(b)
                psi = GeometryOperators.rad2deg(g)
                self.props["Phi"] = f"{phi}deg"
                self.props["Theta"] = f"{theta}deg"
                self.props["Psi"] = f"{psi}deg"
                self.mode = "zyz"
                self.update()
            elif self.props and self.props["Mode"] == "Axis/Position":
                self.props["Mode"] = "Euler Angle ZYZ"
                a, b, g = GeometryOperators.quaternion_to_euler_zyz(self.quaternion)
                phi = GeometryOperators.rad2deg(a)
                theta = GeometryOperators.rad2deg(b)
                psi = GeometryOperators.rad2deg(g)
                self.props["Phi"] = f"{phi}deg"
                self.props["Theta"] = f"{theta}deg"
                self.props["Psi"] = f"{psi}deg"
                del self.props["XAxisXvec"]
                del self.props["XAxisYvec"]
                del self.props["XAxisZvec"]
                del self.props["YAxisXvec"]
                del self.props["YAxisYvec"]
                del self.props["YAxisZvec"]
                self.mode = "zyz"
                self.update()
        else:  # pragma: no cover
            raise ValueError('mode_type=0 for "Axis/Position", =1 for "Euler Angle ZXZ", =2 for "Euler Angle ZYZ"')
        self.auto_update = legacy_update
        return True

    @pyaedt_function_handler()
    def create(
        self,
        origin=None,
        reference_cs="Global",
        name=None,
        mode="axis",
        view="iso",
        x_pointing=None,
        y_pointing=None,
        phi=0,
        theta=0,
        psi=0,
        u=None,
    ):
        """Create a coordinate system.

        Parameters
        ----------
        origin : list
            List of ``[x, y, z]`` coordinates for the origin of the coordinate system.
            The default is ``None``, in which case ``[0, 0, 0]`` is used.
        reference_cs : str, optional
            Name of the reference coordinate system. The default is ``"Global"``.
        name : str
            Name of the coordinate system. The default is ``None``.
        mode : str, optional
            Definition mode. Options are ``"view"``, ``"axis"``, ``"zxz"``, ``"zyz"``,
            and ``"axisrotation"``. The default is ``"axis"``.

            * If ``mode="view"``, specify ``view``.
            * If ``mode="axis"``, specify ``x_pointing`` and ``y_pointing``.
            * If ``mode="zxz"`` or ``mode="zyz"``, specify ``phi``, ``theta``, and ``psi``.
            * If ``mode="axisrotation"``, specify ``theta`` and ``u``.

            Parameters not needed by the specified mode are ignored.
            For back compatibility, ``view="rotate"`` is the same as ``mode="axis"``.
            The mode ``"axisrotation"`` is a coordinate system parallel
            to the global coordinate system centered in the global origin.

        view : str, optional
            View for the coordinate system if ``mode="view"``. Options are
            ``"XY"``, ``"XZ"``, ``"XY"``, ``"iso"``, ``None``, and ``"rotate"``
            (obsolete). The default is ``"iso"``.

            .. note::
               Because the ``"rotate"`` option is obsolete, use ``mode="axis"`` instead.

        x_pointing : list, optional
            List of the ``[x, y, z]`` coordinates specifying the X axis
            pointing in the local coordinate system if ``mode="axis"``.
            The default is ``[1, 0, 0]``.
        y_pointing : list, optional
            List of the ``[x, y, z]`` coordinates specifying the Y axis
            pointing in the local coordinate system if ``mode="axis"``.
            The default is ``[0, 1, 0]``.
        phi : float, optional
            Euler angle phi in degrees if ``mode="zxz"`` or ``mode="zyz"``.
            The default is ``0``.
        theta : float, optional
            Euler angle theta or rotation angle in degrees if ``mode="zxz"``,
            ``mode="zyz"``, or ``mode="axisrotation"``. The default is ``0``.
        psi : float, optional
            Euler angle psi in degrees if ``mode="zxz"`` or ``mode="zyz"``.
            The default is ``0``.
        u : list
            List of the ``[ux, uy, uz]`` coordinates for the rotation axis
            if ``mode="zxz"``. The default is ``[1, 0, 0]``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        if not origin:
            origin = [0, 0, 0]
        if not x_pointing:
            x_pointing = [1, 0, 0]
        if not y_pointing:
            y_pointing = [0, 1, 0]
        if not u:
            u = [1, 0, 0]
        if view == "rotate":
            # legacy compatibility
            mode = "axis"

        if name:
            self.name = name
        elif not self.name:
            self.name = generate_unique_name("CS")

        originX = self._modeler._app.value_with_units(origin[0], self.model_units)
        originY = self._modeler._app.value_with_units(origin[1], self.model_units)
        originZ = self._modeler._app.value_with_units(origin[2], self.model_units)
        orientationParameters = dict({"OriginX": originX, "OriginY": originY, "OriginZ": originZ})
        self.mode = mode
        if mode == "view":
            orientationParameters["Mode"] = "Axis/Position"
            if view == "YZ":
                orientationParameters["XAxisXvec"] = "0mm"
                orientationParameters["XAxisYvec"] = "0mm"
                orientationParameters["XAxisZvec"] = "-1mm"
                orientationParameters["YAxisXvec"] = "0mm"
                orientationParameters["YAxisYvec"] = "1mm"
                orientationParameters["YAxisZvec"] = "0mm"
            elif view == "XZ":
                orientationParameters["XAxisXvec"] = "1mm"
                orientationParameters["XAxisYvec"] = "0mm"
                orientationParameters["XAxisZvec"] = "0mm"
                orientationParameters["YAxisXvec"] = "0mm"
                orientationParameters["YAxisYvec"] = "-1mm"
                orientationParameters["YAxisZvec"] = "0mm"
            elif view == "XY":
                orientationParameters["XAxisXvec"] = "1mm"
                orientationParameters["XAxisYvec"] = "0mm"
                orientationParameters["XAxisZvec"] = "0mm"
                orientationParameters["YAxisXvec"] = "0mm"
                orientationParameters["YAxisYvec"] = "1mm"
                orientationParameters["YAxisZvec"] = "0mm"
            elif view == "iso":
                orientationParameters["XAxisXvec"] = "1mm"
                orientationParameters["XAxisYvec"] = "1mm"
                orientationParameters["XAxisZvec"] = "-2mm"
                orientationParameters["YAxisXvec"] = "-1mm"
                orientationParameters["YAxisYvec"] = "1mm"
                orientationParameters["YAxisZvec"] = "0mm"
            else:  # pragma: no cover
                raise ValueError("With mode = 'view', specify view = 'XY', 'XZ', 'XY', 'iso' ")

        elif mode == "axis":
            orientationParameters["Mode"] = "Axis/Position"
            orientationParameters["XAxisXvec"] = self._modeler._app.value_with_units((x_pointing[0]), self.model_units)
            orientationParameters["XAxisYvec"] = self._modeler._app.value_with_units((x_pointing[1]), self.model_units)
            orientationParameters["XAxisZvec"] = self._modeler._app.value_with_units((x_pointing[2]), self.model_units)
            orientationParameters["YAxisXvec"] = self._modeler._app.value_with_units((y_pointing[0]), self.model_units)
            orientationParameters["YAxisYvec"] = self._modeler._app.value_with_units((y_pointing[1]), self.model_units)
            orientationParameters["YAxisZvec"] = self._modeler._app.value_with_units((y_pointing[2]), self.model_units)

        elif mode == "zxz":
            orientationParameters["Mode"] = "Euler Angle ZXZ"
            orientationParameters["Phi"] = self._modeler._app.value_with_units(phi, "deg")
            orientationParameters["Theta"] = self._modeler._app.value_with_units(theta, "deg")
            orientationParameters["Psi"] = self._modeler._app.value_with_units(psi, "deg")

        elif mode == "zyz":
            orientationParameters["Mode"] = "Euler Angle ZYZ"
            orientationParameters["Phi"] = self._modeler._app.value_with_units(phi, "deg")
            orientationParameters["Theta"] = self._modeler._app.value_with_units(theta, "deg")
            orientationParameters["Psi"] = self._modeler._app.value_with_units(psi, "deg")

        elif mode == "axisrotation":
            th = GeometryOperators.deg2rad(theta)
            q = GeometryOperators.axis_angle_to_quaternion(u, th)
            a, b, c = GeometryOperators.quaternion_to_euler_zyz(q)
            phi = GeometryOperators.rad2deg(a)
            theta = GeometryOperators.rad2deg(b)
            psi = GeometryOperators.rad2deg(c)
            orientationParameters["Mode"] = "Euler Angle ZYZ"
            orientationParameters["Phi"] = self._modeler._app.value_with_units(phi, "deg")
            orientationParameters["Theta"] = self._modeler._app.value_with_units(theta, "deg")
            orientationParameters["Psi"] = self._modeler._app.value_with_units(psi, "deg")
        else:  # pragma: no cover
            raise ValueError("Specify the mode = 'view', 'axis', 'zxz', 'zyz', 'axisrotation' ")

        self._props = CsProps(self, orientationParameters)
        self._modeler.oeditor.CreateRelativeCS(self._orientation, self._attributes)
        self._modeler._coordinate_systems.insert(0, self)
        # this workaround is necessary because the reference CS is ignored at creation, it needs to be modified later
        self._ref_cs = reference_cs
        return self.update()

    @property
    def quaternion(self):
        """Quaternion computed based on specific axis mode.

        Returns
        -------
        list
        """
        if self._quaternion:
            return self._quaternion
        self._modeler._app.variable_manager["temp_var"] = 0
        if self.mode == "axis" or self.mode == "view":
            x1 = self.props["XAxisXvec"]
            x2 = self.props["XAxisYvec"]
            x3 = self.props["XAxisZvec"]
            y1 = self.props["YAxisXvec"]
            y2 = self.props["YAxisYvec"]
            y3 = self.props["YAxisZvec"]
            self._modeler._app.variable_manager["temp_var"] = x1
            x_pointing_num = [self._modeler._app.variable_manager["temp_var"].numeric_value]
            self._modeler._app.variable_manager["temp_var"] = x2
            x_pointing_num.append(self._modeler._app.variable_manager["temp_var"].numeric_value)
            self._modeler._app.variable_manager["temp_var"] = x3
            x_pointing_num.append(self._modeler._app.variable_manager["temp_var"].numeric_value)
            self._modeler._app.variable_manager["temp_var"] = y1
            y_pointing_num = [self._modeler._app.variable_manager["temp_var"].numeric_value]
            self._modeler._app.variable_manager["temp_var"] = y2
            y_pointing_num.append(self._modeler._app.variable_manager["temp_var"].numeric_value)
            self._modeler._app.variable_manager["temp_var"] = y3
            y_pointing_num.append(self._modeler._app.variable_manager["temp_var"].numeric_value)
            x, y, z = GeometryOperators.pointing_to_axis(x_pointing_num, y_pointing_num)
            a, b, g = GeometryOperators.axis_to_euler_zyz(x, y, z)
            self._quaternion = GeometryOperators.euler_zyz_to_quaternion(a, b, g)
            del self._modeler._app.variable_manager["temp_var"]
        elif self.mode == "zxz":
            self._modeler._app.variable_manager["temp_var"] = self.props["Phi"]
            a = GeometryOperators.deg2rad(self._modeler._app.variable_manager["temp_var"].numeric_value)
            self._modeler._app.variable_manager["temp_var"] = self.props["Theta"]
            b = GeometryOperators.deg2rad(self._modeler._app.variable_manager["temp_var"].numeric_value)
            self._modeler._app.variable_manager["temp_var"] = self.props["Psi"]
            g = GeometryOperators.deg2rad(self._modeler._app.variable_manager["temp_var"].numeric_value)
            self._quaternion = GeometryOperators.euler_zxz_to_quaternion(a, b, g)
            del self._modeler._app.variable_manager["temp_var"]
        elif self.mode == "zyz" or self.mode == "axisrotation":
            self._modeler._app.variable_manager["temp_var"] = self.props["Phi"]
            a = GeometryOperators.deg2rad(self._modeler._app.variable_manager["temp_var"].numeric_value)
            self._modeler._app.variable_manager["temp_var"] = self.props["Theta"]
            b = GeometryOperators.deg2rad(self._modeler._app.variable_manager["temp_var"].numeric_value)
            self._modeler._app.variable_manager["temp_var"] = self.props["Psi"]
            g = GeometryOperators.deg2rad(self._modeler._app.variable_manager["temp_var"].numeric_value)
            self._quaternion = GeometryOperators.euler_zyz_to_quaternion(a, b, g)
            del self._modeler._app.variable_manager["temp_var"]
        return self._quaternion

    @property
    def origin(self):
        """Coordinate system origin in model units.

        Returns
        -------
        list
        """
        self._modeler._app.variable_manager["temp_var"] = self.props["OriginX"]
        x = self._modeler._app.variable_manager["temp_var"].numeric_value
        self._modeler._app.variable_manager["temp_var"] = self.props["OriginY"]
        y = self._modeler._app.variable_manager["temp_var"].numeric_value
        self._modeler._app.variable_manager["temp_var"] = self.props["OriginZ"]
        z = self._modeler._app.variable_manager["temp_var"].numeric_value
        del self._modeler._app.variable_manager["temp_var"]
        return [x, y, z]

    @origin.setter
    def origin(self, origin):
        """Set the coordinate system origin in model units."""
        legacy_update = self.auto_update
        self.auto_update = False
        origin_x = self._modeler._app.value_with_units(origin[0], self.model_units)
        origin_y = self._modeler._app.value_with_units(origin[1], self.model_units)
        origin_z = self._modeler._app.value_with_units(origin[2], self.model_units)
        self.props["OriginX"] = origin_x
        self.props["OriginY"] = origin_y
        self.props["OriginZ"] = origin_z
        self.update()
        self.auto_update = legacy_update

    @property
    def _orientation(self):
        """Internal named array for orientation of the coordinate system."""
        arg = ["Name:RelativeCSParameters"]
        _dict2arg(self.props, arg)
        return arg

    @property
    def _attributes(self):
        """Internal named array for attributes of the coordinate system."""
        coordinateSystemAttributes = ["NAME:Attributes", "Name:=", self.name]
        return coordinateSystemAttributes


class ObjectCoordinateSystem(BaseCoordinateSystem, object):
    """Manages object coordinate system data and execution.

    Parameters
    ----------
    modeler :
        Inherited parent object.
    props : dict, optional
        Dictionary of properties. The default is ``None``.
    name : optional
        Name of the coordinate system.
        The default is ``None``.
    entity_id : int
        ID of the entity object where the object coordinate system is anchored.

    """

    def __init__(self, modeler, props=None, name=None, entity_id=None):
        BaseCoordinateSystem.__init__(self, modeler, name)
        self.entity_id = entity_id
        self._props = None
        if props:
            self._props = CsProps(self, props)
            if "KernelVersion" in self.props:
                del self.props["KernelVersion"]
        self._ref_cs = None

    @property
    def ref_cs(self):
        """Reference coordinate system.

        Returns
        -------
        str
        """
        if self._ref_cs or settings.aedt_version <= "2022.2":
            return self._ref_cs
        obj1 = self._modeler.oeditor.GetChildObject(self.name)
        self._ref_cs = obj1.GetPropValue("Reference CS")
        return self._ref_cs

    @ref_cs.setter
    def ref_cs(self, value):
        if settings.aedt_version <= "2022.2":
            self._ref_cs = value
            self.update()
        obj1 = self._modeler.oeditor.GetChildObject(self.name)
        try:
            obj1.SetPropValue("Reference CS", value)
            self._ref_cs = value
        except Exception:
            self._modeler.logger.error("Failed to set Coordinate CS Reference.")

    @property
    def props(self):
        """Properties of the coordinate system.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.Modeler.CSProps`
        """
        if self._props or settings.aedt_version <= "2022.2" or self.name is None:
            return self._props
        self._get_coordinates_data()
        return self._props

    @property
    def _part_name(self):
        """Internally named part name of the object where the coordinate system lays."""
        if not self.entity_id:
            # face_id has not been defined yet
            return None
        for obj in self._modeler.objects.values():
            if obj.id == self.entity_id:
                return obj.name
            for face in obj.faces:
                if face.id == self.entity_id:
                    return obj.name
                for edge in face.edges:
                    if edge.id == self.entity_id:
                        return obj.name
                    for vertex in edge.vertices:
                        if vertex.id == self.entity_id:
                            return obj.name
        return None  # part has not been found

    @property
    def _object_parameters(self):
        """Internally named array with parameters of the object coordinate system."""
        arg = ["Name:ObjectCSParameters"]
        _dict2arg(self.props, arg)
        return arg

    @property
    def _attributes(self):
        """Internally named array for attributes of the object coordinate system."""
        coordinateSystemAttributes = ["NAME:Attributes", "Name:=", self.name, "PartName:=", self._part_name]
        return coordinateSystemAttributes

    @pyaedt_function_handler(obj="assignment")
    def create(
        self,
        assignment,
        origin,
        x_axis,
        y_axis,
        move_to_end=True,
        reverse_x_axis=False,
        reverse_y_axis=False,
    ):
        """Create an object coordinate system.

        Parameters
        ----------
        assignment : str, :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
            Object to attach the object coordinate system to.
        origin : int, VertexPrimitive, EdgePrimitive, FacePrimitive, list
            Origin where the object coordinate system is anchored.
            The value can be:

             - An integer, in which case it refers to the entity ID.
             - A VertexPrimitive, EdgePrimitive, or FacePrimitive object, in which case it refers to the entity type.
             - A list, in which case it refers to the origin coordinate system ``[x, y, z]``.

        x_axis : int, VertexPrimitive, EdgePrimitive, FacePrimitive, list
            Entity that the x axis of the object coordinate system points to.
            The value can be:

             - An integer, in which case it refers to the entity IDd.
             - A VertexPrimitive, EdgePrimitive, or FacePrimitive object, in which case it refers to the entity type.
             - A list, in which case it refers to the point coordinate system ``[x, y, z]`` that the x axis points to.

        y_axis : int, VertexPrimitive, EdgePrimitive, FacePrimitive, list
            Entity that the y axis of the object coordinate system points to.
            The value can be:

             - An integer, in which case it refers to the entity ID.
             - A VertexPrimitive, EdgePrimitive, FacePrimitive object, in which case it refers to the entity type.
             - A list, in which case it refers to the point coordinate system ``[x, y, z]`` that the y axis points to.

        move_to_end : bool, optional
            Whether to always move the operation for creating the coordinate system to the
            end of subsequent objects operation. The default is ``True``.
        reverse_x_axis : bool, optional
            Whether the x-axis is in the reverse direction.
            The default is ``False``.
        reverse_y_axis : bool, optional
            Whether the y-axis is in the reverse direction.
            The default is ``False``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        if isinstance(assignment, str):
            self.entity_id = self._modeler.objects_by_name[assignment].id
        elif isinstance(assignment, Object3d):
            self.entity_id = assignment.id
        else:
            raise ValueError("Object provided is invalid.")

        # Origin
        if (
            isinstance(origin, int)
            or isinstance(origin, VertexPrimitive)
            or isinstance(origin, EdgePrimitive)
            or isinstance(origin, FacePrimitive)
        ):
            if isinstance(origin, int):
                id = origin
            else:
                id = origin.id
            is_attached_to_entity = True
            origin_entity_id = self._modeler.convert_to_selections(id, True)[0]
            if not isinstance(origin_entity_id, int):  # pragma: no cover
                raise ValueError("Unable to find reference entity.")
            else:
                o_type = self._get_type_from_id(origin_entity_id)
                if o_type == "Face":
                    origin_position_type = "FaceCenter"
                elif o_type == "Edge":
                    origin_position_type = "EdgeCenter"
                elif o_type == "Vertex":
                    origin_position_type = "OnVertex"
                else:  # pragma: no cover
                    raise ValueError("Origin must identify either `Face`, 'Edge', or 'Vertex'.")
            origin_x_position = "0"
            origin_y_position = "0"
            origin_z_position = "0"
        elif isinstance(origin, list):
            is_attached_to_entity = False
            origin_entity_id = -1
            origin_position_type = "AbsolutePosition"
            origin_x_position = self._position_parser(origin[0])
            origin_y_position = self._position_parser(origin[1])
            origin_z_position = self._position_parser(origin[2])

        originParameters = {}
        originParameters["IsAttachedToEntity"] = is_attached_to_entity
        originParameters["EntityID"] = origin_entity_id
        originParameters["FacetedBodyTriangleIndex"] = -1
        originParameters["TriangleVertexIndex"] = -1
        originParameters["PositionType"] = origin_position_type
        originParameters["UParam"] = 0
        originParameters["VParam"] = 0
        originParameters["XPosition"] = origin_x_position
        originParameters["YPosition"] = origin_y_position
        originParameters["ZPosition"] = origin_z_position

        # X-Axis
        if (
            isinstance(x_axis, int)
            or isinstance(x_axis, VertexPrimitive)
            or isinstance(x_axis, EdgePrimitive)
            or isinstance(x_axis, FacePrimitive)
        ):
            if isinstance(x_axis, int):
                id = x_axis
            else:
                id = x_axis.id
            is_attached_to_entity = True
            x_axis_entity_id = self._modeler.convert_to_selections(id, True)[0]
            if not isinstance(x_axis_entity_id, int):  # pragma: no cover
                raise ValueError("Unable to find reference entity.")
            else:
                o_type = self._get_type_from_id(x_axis_entity_id)
                if o_type == "Face":
                    x_axis_position_type = "FaceCenter"
                elif o_type == "Edge":
                    x_axis_position_type = "EdgeCenter"
                elif o_type == "Vertex":
                    x_axis_position_type = "OnVertex"
                else:  # pragma: no cover
                    raise ValueError("x axis must identify either Face or Edge or Vertex.")
            xAxisParameters = {}
            xAxisParameters["IsAttachedToEntity"] = True
            xAxisParameters["EntityID"] = x_axis_entity_id
            xAxisParameters["FacetedBodyTriangleIndex"] = -1
            xAxisParameters["TriangleVertexIndex"] = -1
            xAxisParameters["PositionType"] = x_axis_position_type
            xAxisParameters["UParam"] = 0
            xAxisParameters["VParam"] = 0
            xAxisParameters["XPosition"] = "0"
            xAxisParameters["YPosition"] = "0"
            xAxisParameters["ZPosition"] = "0"
            x_axis_dict_name = "xAxisPos"
        elif isinstance(x_axis, list):
            x_axis_x_direction = self._position_parser(x_axis[0])
            x_axis_y_direction = self._position_parser(x_axis[1])
            x_axis_z_direction = self._position_parser(x_axis[2])

            xAxisParameters = {}
            xAxisParameters["DirectionType"] = "AbsoluteDirection"
            xAxisParameters["EdgeID"] = -1
            xAxisParameters["FaceID"] = -1
            xAxisParameters["xDirection"] = x_axis_x_direction
            xAxisParameters["yDirection"] = x_axis_y_direction
            xAxisParameters["zDirection"] = x_axis_z_direction
            xAxisParameters["UParam"] = 0
            xAxisParameters["VParam"] = 0
            x_axis_dict_name = "xAxis"

        # Y-Axis
        if (
            isinstance(y_axis, int)
            or isinstance(y_axis, VertexPrimitive)
            or isinstance(y_axis, EdgePrimitive)
            or isinstance(y_axis, FacePrimitive)
        ):
            if isinstance(y_axis, int):
                id = y_axis
            else:
                id = y_axis.id
            is_attached_to_entity = True
            y_axis_entity_id = self._modeler.convert_to_selections(id, True)[0]
            if not isinstance(y_axis_entity_id, int):  # pragma: no cover
                raise ValueError("Unable to find reference entity.")
            else:
                o_type = self._get_type_from_id(y_axis_entity_id)
                if o_type == "Face":
                    y_axis_position_type = "FaceCenter"
                elif o_type == "Edge":
                    y_axis_position_type = "EdgeCenter"
                elif o_type == "Vertex":
                    y_axis_position_type = "OnVertex"
                else:  # pragma: no cover
                    raise ValueError("x axis must identify either Face or Edge or Vertex.")
            yAxisParameters = {}
            yAxisParameters["IsAttachedToEntity"] = True
            yAxisParameters["EntityID"] = y_axis_entity_id
            yAxisParameters["FacetedBodyTriangleIndex"] = -1
            yAxisParameters["TriangleVertexIndex"] = -1
            yAxisParameters["PositionType"] = y_axis_position_type
            yAxisParameters["UParam"] = 0
            yAxisParameters["VParam"] = 0
            yAxisParameters["XPosition"] = "0"
            yAxisParameters["YPosition"] = "0"
            yAxisParameters["ZPosition"] = "0"
            y_axis_dict_name = "yAxisPos"
        elif isinstance(y_axis, list):
            y_axis_x_direction = self._position_parser(y_axis[0])
            y_axis_y_direction = self._position_parser(y_axis[1])
            y_axis_z_direction = self._position_parser(y_axis[2])

            yAxisParameters = {}
            yAxisParameters["DirectionType"] = "AbsoluteDirection"
            yAxisParameters["EdgeID"] = -1
            yAxisParameters["FaceID"] = -1
            yAxisParameters["xDirection"] = y_axis_x_direction
            yAxisParameters["yDirection"] = y_axis_y_direction
            yAxisParameters["zDirection"] = y_axis_z_direction
            yAxisParameters["UParam"] = 0
            yAxisParameters["VParam"] = 0
            y_axis_dict_name = "yAxis"

        parameters = {}
        parameters["Origin"] = originParameters
        parameters["MoveToEnd"] = move_to_end
        parameters["ReverseXAxis"] = reverse_x_axis
        parameters["ReverseYAxis"] = reverse_y_axis
        parameters[x_axis_dict_name] = xAxisParameters
        parameters[y_axis_dict_name] = yAxisParameters

        self._props = CsProps(self, parameters)
        self._modeler.oeditor.CreateObjectCS(self._object_parameters, self._attributes)
        self._modeler._coordinate_systems.insert(0, self)
        return True

    @pyaedt_function_handler()
    def update(self):
        """Update the coordinate system.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        try:
            self._change_property(
                self.name,
                [
                    "NAME:ChangedProps",
                    ["NAME:Reference CS", "Value:=", self.ref_cs],
                ],
            )
        except Exception:  # pragma: no cover
            raise ValueError("Update of property reference coordinate system failed.")

        try:
            self._change_property(
                self.name, ["NAME:ChangedProps", ["NAME:Always Move CS To End", "Value:=", self.props["MoveToEnd"]]]
            )
        except Exception:  # pragma: no cover
            raise ValueError("Update of property move to end failed.")

        try:
            self._change_property(
                self.name, ["NAME:ChangedProps", ["NAME:Reverse X Axis", "Value:=", self.props["ReverseXAxis"]]]
            )
        except Exception:  # pragma: no cover
            raise ValueError("Update of property reverse x axis failed.")

        try:
            self._change_property(
                self.name, ["NAME:ChangedProps", ["NAME:Reverse Y Axis", "Value:=", self.props["ReverseYAxis"]]]
            )
        except Exception:  # pragma: no cover
            raise ValueError("Update of property reverse y axis failed.")

        if self.props["Origin"]["PositionType"] == "AbsolutePosition":
            origin_x_position = self._position_parser(self.props["Origin"]["XPosition"])
            origin_y_position = self._position_parser(self.props["Origin"]["YPosition"])
            origin_z_position = self._position_parser(self.props["Origin"]["ZPosition"])
            try:
                self._change_property(
                    self.name,
                    [
                        "NAME:ChangedProps",
                        [
                            "NAME:Origin",
                            "X:=",
                            origin_x_position,
                            "Y:=",
                            origin_y_position,
                            "Z:=",
                            origin_z_position,
                        ],
                    ],
                )
            except Exception:  # pragma: no cover
                raise ValueError("Update origin properties failed.")

        if "xAxis" in self.props:
            x_axis_x_direction = self._position_parser(self.props["xAxis"]["xDirection"])
            x_axis_y_direction = self._position_parser(self.props["xAxis"]["yDirection"])
            x_axis_z_direction = self._position_parser(self.props["xAxis"]["zDirection"])
            try:
                self._change_property(
                    self.name,
                    [
                        "NAME:ChangedProps",
                        [
                            "NAME:X Axis",
                            "X:=",
                            x_axis_x_direction,
                            "Y:=",
                            x_axis_y_direction,
                            "Z:=",
                            x_axis_z_direction,
                        ],
                    ],
                )
            except Exception:  # pragma: no cover
                raise ValueError("Update x axis properties failed.")

        if "yAxis" in self.props:
            y_axis_x_direction = self._position_parser(self.props["yAxis"]["xDirection"])
            y_axis_y_direction = self._position_parser(self.props["yAxis"]["yDirection"])
            y_axis_z_direction = self._position_parser(self.props["yAxis"]["zDirection"])
            try:
                self._change_property(
                    self.name,
                    [
                        "NAME:ChangedProps",
                        [
                            "NAME:Y Axis",
                            "X:=",
                            y_axis_x_direction,
                            "Y:=",
                            y_axis_y_direction,
                            "Z:=",
                            y_axis_z_direction,
                        ],
                    ],
                )
            except Exception:  # pragma: no cover
                raise ValueError("Update y axis properties failed.")

        return True

    @pyaedt_function_handler()
    def _get_type_from_id(self, obj_id):
        """Get the entity type from the id."""
        for obj in self._modeler.objects.values():
            if obj.id == obj_id:
                return "3dObject"
            for face in obj.faces:
                if face.id == obj_id:
                    return "Face"
                for edge in face.edges:
                    if edge.id == obj_id:
                        return "Edge"
                    for vertex in edge.vertices:
                        if vertex.id == obj_id:
                            return "Vertex"
        raise ValueError(f"Cannot find entity id {obj_id}")

    def _position_parser(self, pos):
        try:
            return self._modeler._app.value_with_units(float(pos), self.model_units)
        except Exception:
            return pos


class Lists(PropsManager, object):
    """Manages list data and execution.

    Parameters
    ----------
    modeler :
        Inherited parent object.
    props : dict, optional
        Dictionary of properties. The default is ``None``.
    name : optional
        The default is ``None``.

    """

    def __init__(self, modeler, props=None, name=None):
        self.auto_update = True
        self._modeler = modeler
        self.name = name
        self.props = ListsProps(self, props)

    @pyaedt_function_handler()
    def update(self):
        """Update the List.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        # self._change_property(self.name, ["NAME:ChangedProps", ["NAME:Reference CS", "Value:=", self.ref_cs]])
        object_list_new = self._list_verification(self.props["List"], self.props["Type"])
        if type == "Object":
            object_list_new = ",".join(object_list_new)
        argument1 = ["NAME:Selections", "Selections:=", self.name]
        argument2 = [
            "NAME:GeometryEntityListParameters",
            "EntityType:=",
            self.props["Type"],
            "EntityList:=",
            object_list_new,
        ]
        try:
            self._modeler.oeditor.EditEntityList(argument1, argument2)
        except Exception:  # pragma: no cover
            raise ValueError("Input List not correct for the type " + self.props["Type"])

        return True

    @pyaedt_function_handler(object_list="assignment", type="entity_type")
    def create(
        self,
        assignment,
        name=None,
        entity_type="Object",
    ):
        """Create a List.

        Parameters
        ----------
        assignment : list
            List of ``["Obj1", "Obj2"]`` objects or face ID if type is "Face".
            The default is ``None``, in which case all objects are selected.
        name : list, str
            List of names. The default is ``None``.
        entity_type : str, optional
            List type. Options are ``"Object"``, ``"Face"``. The default is ``"Object"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """

        if not name:
            name = generate_unique_name(entity_type + "List")

        object_list_new = self._list_verification(assignment, entity_type)

        if object_list_new:
            olist = object_list_new
            if entity_type == "Object":
                olist = ",".join(object_list_new)

            self.name = self._modeler.oeditor.CreateEntityList(
                ["NAME:GeometryEntityListParameters", "EntityType:=", entity_type, "EntityList:=", olist],
                ["NAME:Attributes", "Name:=", name],
            )
            props = {}
            props["List"] = object_list_new

            props["ID"] = self._modeler.get_entitylist_id(self.name)
            props["Type"] = entity_type

            self.props = ListsProps(self, props)
            self._modeler.user_lists.append(self)
            return True
        else:
            return False

    @pyaedt_function_handler()
    def delete(self):
        """Delete the List.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        self._modeler.oeditor.Delete(["NAME:Selections", "Selections:=", self.name])
        self._modeler.user_lists.remove(self)
        return True

    @pyaedt_function_handler(newname="name")
    def rename(self, name):
        """Rename the List.

        Parameters
        ----------
        name : str
            New name for the List.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        argument = [
            "NAME:AllTabs",
            [
                "NAME:Geometry3DListTab",
                ["NAME:PropServers", self.name],
                ["NAME:ChangedProps", ["NAME:Name", "Value:=", name]],
            ],
        ]
        self._modeler.oeditor.ChangeProperty(argument)
        self.name = name
        return True

    def _list_verification(self, object_list, list_type):
        object_list = self._modeler.convert_to_selections(object_list, True)
        object_list_new = []
        if list_type == "Object":
            obj_names = [i for i in self._modeler.object_names]
            check = [item for item in object_list if item in obj_names]
            if check:
                object_list_new = check
            else:
                return []

        elif list_type == "Face":
            object_list_new = []
            for element in object_list:
                if isinstance(element, str):
                    if element.isnumeric():
                        object_list_new.append(int(element))
                    else:
                        if element in self._modeler.object_names:
                            obj_id = self._modeler.objects[element].id
                            for sel in self._modeler.object_list:
                                if sel.id == obj_id:
                                    for f in sel.faces:
                                        object_list_new.append(f.id)
                                    break
                        else:
                            return []
                else:
                    object_list_new.append(int(element))
        return object_list_new


class Modeler(object):
    """Provides the `Modeler` application class that other `Modeler` classes inherit.

    This class is inherited in the caller application and is accessible through the modeler variable
    object( eg. ``hfss.modeler``).

    Parameters
    ----------
    app :
        Inherited parent object.

    Examples
    --------
    >>> from ansys.aedt.core import Maxwell2d
    >>> app = Maxwell2d()
    >>> my_modeler = app.modeler
    """

    def __init__(self, app):
        self._app = app

    # Properties derived from internal parent data
    @property
    def _desktop(self):
        """Desktop."""
        return self._app._desktop

    @property
    def logger(self):
        """Logger."""
        return self._app.logger

    @property
    def _odesign(self):
        """Design."""
        return self._app._odesign

    @property
    def _oimportexport(self):
        """Import/Export."""
        return self._app.oimport_export

    @property
    def projdir(self):
        """Project directory."""
        return self._app.project_path
