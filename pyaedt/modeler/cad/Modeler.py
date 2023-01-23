# -*- coding: utf-8 -*-
"""
This module contains these classes: `BaseCoordinateSystem`, `FaceCoordinateSystem`, `CoordinateSystem`, `Modeler`,
`Position`, and `SweepOptions`.

This modules provides functionalities for the 3D Modeler, 2D Modeler,
3D Layout Modeler, and Circuit Modeler.
"""

from __future__ import absolute_import  # noreorder

import copy
import math
import os
import warnings
from collections import OrderedDict

from pyaedt.generic.constants import AEDT_UNITS
from pyaedt.generic.DataHandlers import _dict2arg
from pyaedt.generic.general_methods import PropsManager
from pyaedt.generic.general_methods import _retry_ntimes
from pyaedt.generic.general_methods import generate_unique_name
from pyaedt.generic.general_methods import pyaedt_function_handler
from pyaedt.generic.general_methods import settings
from pyaedt.modeler.cad.elements3d import EdgePrimitive
from pyaedt.modeler.cad.elements3d import FacePrimitive
from pyaedt.modeler.cad.elements3d import VertexPrimitive
from pyaedt.modeler.cad.object3d import Object3d
from pyaedt.modeler.geometry_operators import GeometryOperators


class CsProps(OrderedDict):
    """AEDT Cooardinate System Internal Parameters."""

    def __setitem__(self, key, value):
        OrderedDict.__setitem__(self, key, value)
        if self._pyaedt_cs.auto_update:
            res = self._pyaedt_cs.update()
            if not res:
                self._pyaedt_cs._app.logger.warning("Update of %s Failed. Check needed arguments", key)

    def __init__(self, cs_object, props):
        OrderedDict.__init__(self)
        if props:
            for key, value in props.items():
                if isinstance(value, (dict, OrderedDict)):
                    OrderedDict.__setitem__(self, key, CsProps(cs_object, value))
                else:
                    OrderedDict.__setitem__(self, key, value)
        self._pyaedt_cs = cs_object

    def _setitem_without_update(self, key, value):
        OrderedDict.__setitem__(self, key, value)


class ListsProps(OrderedDict):
    """AEDT Lists Internal Parameters."""

    def __setitem__(self, key, value):
        OrderedDict.__setitem__(self, key, value)
        if self._pyaedt_lists.auto_update:
            res = self._pyaedt_lists.update()
            if not res:
                self._pyaedt_lists._app.logger.warning("Update of %s Failed. Check needed arguments", key)

    def __init__(self, cs_object, props):
        OrderedDict.__init__(self)
        if props:
            for key, value in props.items():
                if isinstance(value, (dict, OrderedDict)):
                    OrderedDict.__setitem__(self, key, CsProps(cs_object, value))
                else:
                    OrderedDict.__setitem__(self, key, value)
        self._pyaedt_lists = cs_object

    def _setitem_without_update(self, key, value):
        OrderedDict.__setitem__(self, key, value)


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

    @pyaedt_function_handler()
    def _dim_arg(self, value, units=None):
        """Dimension argument.

        Parameters
        ----------
        value :

        units : optional
             The default is ``None``.

        Returns
        -------
        str
        """
        if units is None:
            units = self.model_units
        if type(value) is str:
            try:
                float(value)
                val = "{0}{1}".format(value, units)
            except:
                val = value
        else:
            val = "{0}{1}".format(value, units)
        return val

    @pyaedt_function_handler()
    def delete(self):
        """Delete the coordinate system.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------
        Clean all coordinate systems of the design.

        >>> from pyaedt import Maxwell2d
        >>> app = Maxwell2d()
        >>> cs_copy = [i for i in app.modeler.coordinate_systems]
        >>> [i.delete() for i in cs_copy]
        """
        try:
            self._modeler.oeditor.Delete(["NAME:Selections", "Selections:=", self.name])
            if "ref_cs" in dir(self):
                for cs in range(0, len(self._modeler.coordinate_systems)):
                    if self._modeler.coordinate_systems[cs].ref_cs == self.name:
                        self._modeler.coordinate_systems.pop(cs)
            self._modeler.coordinate_systems.pop(self._modeler.coordinate_systems.index(self))
            self._modeler.cleanup_objects()
        except:
            self._modeler._app.logger.warning("Coordinate system does not exist")
        return True

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
        _retry_ntimes(5, self._modeler.oeditor.ChangeProperty, arguments)

    @pyaedt_function_handler()
    def rename(self, newname):
        """Rename the coordinate system.

        Parameters
        ----------
        newname : str
            New name for the coordinate system.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        self._change_property(self.name, ["NAME:ChangedProps", ["NAME:Name", "Value:=", newname]])
        self.name = newname
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
        self.props = CsProps(self, props)
        try:  # pragma: no cover
            if "KernelVersion" in self.props:
                del self.props["KernelVersion"]
        except:
            pass

    @property
    def _part_name(self):
        """Internally get the part name which the face belongs to"""
        if not self.face_id:
            # face_id has not been defined yet
            return None
        for obj in self._modeler.objects.values():
            for face in obj.faces:
                if face.id == self.face_id:
                    return obj.name
        return None  # part has not been found

    @property
    def _face_paramenters(self):
        """Internal named array for paramenteers of the face coordinate system."""
        arg = ["Name:FaceCSParameters"]
        _dict2arg(self.props, arg)
        return arg

    @property
    def _attributes(self):
        """Internal named array for attributes of the face coordinate system."""
        coordinateSystemAttributes = ["NAME:Attributes", "Name:=", self.name, "PartName:=", self._part_name]
        return coordinateSystemAttributes

    @pyaedt_function_handler()
    def create(
        self, face, origin, axis_position, axis="X", name=None, offset=None, rotation=0, always_move_to_end=True
    ):
        """Create a face coordinate system.
        The face coordinate has always the Z axis parallel to face normal.
        The X and Y axis lie on the face plane.

        Parameters
        ----------
        face : int, FacePrimitive
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
            Select which axis is considered with the option ``axix``.
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

        face_id = self._modeler.convert_to_selections(face, True)[0]
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

        originParameters = OrderedDict()
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

        positioningParameters = OrderedDict()
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

        parameters = OrderedDict()
        parameters["Origin"] = originParameters
        parameters["MoveToEnd"] = always_move_to_end
        parameters["FaceID"] = face_id
        parameters["AxisPosn"] = positioningParameters
        parameters["WhichAxis"] = axis
        parameters["ZRotationAngle"] = str(rotation) + "deg"
        parameters["XOffset"] = self._dim_arg((offset[0]), self.model_units)
        parameters["YOffset"] = self._dim_arg((offset[1]), self.model_units)
        parameters["AutoAxis"] = False

        self.props = CsProps(self, parameters)
        self._modeler.oeditor.CreateFaceCS(self._face_paramenters, self._attributes)
        self._modeler.coordinate_systems.insert(0, self)
        return True

    @pyaedt_function_handler()
    def _get_type_from_id(self, obj_id):
        """Get the entity type from the id"""
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
        raise ValueError("Cannot find entity id {}".format(obj_id))  # pragma: no cover

    @pyaedt_function_handler()
    def _get_type_from_object(self, obj):
        """Get the entity type from the object"""
        if type(obj) is FacePrimitive:
            return "Face"
        elif type(obj) is EdgePrimitive:
            return "Edge"
        elif type(obj) is VertexPrimitive:
            return "Vertex"
        elif type(obj) is Object3d:
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
        except:  # pragma: no cover
            raise ValueError("'Z Rotation angle' parameter must be a string in the format '10deg'")

        try:
            self._change_property(
                self.name,
                [
                    "NAME:ChangedProps",
                    ["NAME:Position Offset XY", "X:=", self.props["XOffset"], "Y:=", self.props["YOffset"]],
                ],
            )
        except:  # pragma: no cover
            raise ValueError("'XOffset' and 'YOffset' parameters must be a string in the format '1.3mm'")

        try:
            self._change_property(self.name, ["NAME:ChangedProps", ["NAME:Axis", "Value:=", self.props["WhichAxis"]]])
        except:  # pragma: no cover
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
        self.props = CsProps(self, props)
        self.ref_cs = None
        self._quaternion = None
        self.mode = None
        try:  # pragma: no cover
            if "KernelVersion" in self.props:
                del self.props["KernelVersion"]
        except:
            pass

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
        except:  # pragma: no cover
            raise ValueError(
                "Mode must be 'Axis/Position', 'Euler Angle ZYZ' or 'Euler Angle ZXZ', not {}.".format(
                    self.props["Mode"]
                )
            )

        props = ["NAME:ChangedProps"]

        props.append(
            [
                "NAME:Origin",
                "X:=",
                self._dim_arg(self.props["OriginX"]),
                "Y:=",
                self._dim_arg(self.props["OriginY"]),
                "Z:=",
                self._dim_arg(self.props["OriginZ"]),
            ]
        )

        if self.props["Mode"] == "Axis/Position":
            props.append(
                [
                    "NAME:X Axis",
                    "X:=",
                    self._dim_arg(self.props["XAxisXvec"]),
                    "Y:=",
                    self._dim_arg(self.props["XAxisYvec"]),
                    "Z:=",
                    self._dim_arg(self.props["XAxisZvec"]),
                ]
            )
            props.append(
                [
                    "NAME:Y Point",
                    "X:=",
                    self._dim_arg(self.props["YAxisXvec"]),
                    "Y:=",
                    self._dim_arg(self.props["YAxisYvec"]),
                    "Z:=",
                    self._dim_arg(self.props["YAxisZvec"]),
                ]
            )
        else:
            props.append(["NAME:Phi", "Value:=", self._dim_arg(self.props["Phi"], "deg")])

            props.append(["NAME:Theta", "Value:=", self._dim_arg(self.props["Theta"], "deg")])

            props.append(["NAME:Psi", "Value:=", self._dim_arg(self.props["Psi"], "deg")])

        self._change_property(self.name, props)
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
                self.props["Phi"] = "{}deg".format(phi)
                self.props["Theta"] = "{}deg".format(theta)
                self.props["Psi"] = "{}deg".format(psi)
                self.mode = "zxz"
                self.update()
            elif self.props and self.props["Mode"] == "Axis/Position":
                self.props["Mode"] = "Euler Angle ZXZ"
                a, b, g = GeometryOperators.quaternion_to_euler_zxz(self.quaternion)
                phi = GeometryOperators.rad2deg(a)
                theta = GeometryOperators.rad2deg(b)
                psi = GeometryOperators.rad2deg(g)
                self.props["Phi"] = "{}deg".format(phi)
                self.props["Theta"] = "{}deg".format(theta)
                self.props["Psi"] = "{}deg".format(psi)
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
                self.props["Phi"] = "{}deg".format(phi)
                self.props["Theta"] = "{}deg".format(theta)
                self.props["Psi"] = "{}deg".format(psi)
                self.mode = "zyz"
                self.update()
            elif self.props and self.props["Mode"] == "Axis/Position":
                self.props["Mode"] = "Euler Angle ZYZ"
                a, b, g = GeometryOperators.quaternion_to_euler_zyz(self.quaternion)
                phi = GeometryOperators.rad2deg(a)
                theta = GeometryOperators.rad2deg(b)
                psi = GeometryOperators.rad2deg(g)
                self.props["Phi"] = "{}deg".format(phi)
                self.props["Theta"] = "{}deg".format(theta)
                self.props["Psi"] = "{}deg".format(psi)
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

        originX = self._dim_arg(origin[0], self.model_units)
        originY = self._dim_arg(origin[1], self.model_units)
        originZ = self._dim_arg(origin[2], self.model_units)
        orientationParameters = OrderedDict({"OriginX": originX, "OriginY": originY, "OriginZ": originZ})
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
            orientationParameters["XAxisXvec"] = self._dim_arg((x_pointing[0]), self.model_units)
            orientationParameters["XAxisYvec"] = self._dim_arg((x_pointing[1]), self.model_units)
            orientationParameters["XAxisZvec"] = self._dim_arg((x_pointing[2]), self.model_units)
            orientationParameters["YAxisXvec"] = self._dim_arg((y_pointing[0]), self.model_units)
            orientationParameters["YAxisYvec"] = self._dim_arg((y_pointing[1]), self.model_units)
            orientationParameters["YAxisZvec"] = self._dim_arg((y_pointing[2]), self.model_units)

        elif mode == "zxz":
            orientationParameters["Mode"] = "Euler Angle ZXZ"
            orientationParameters["Phi"] = self._dim_arg(phi, "deg")
            orientationParameters["Theta"] = self._dim_arg(theta, "deg")
            orientationParameters["Psi"] = self._dim_arg(psi, "deg")

        elif mode == "zyz":
            orientationParameters["Mode"] = "Euler Angle ZYZ"
            orientationParameters["Phi"] = self._dim_arg(phi, "deg")
            orientationParameters["Theta"] = self._dim_arg(theta, "deg")
            orientationParameters["Psi"] = self._dim_arg(psi, "deg")

        elif mode == "axisrotation":
            th = GeometryOperators.deg2rad(theta)
            q = GeometryOperators.axis_angle_to_quaternion(u, th)
            a, b, c = GeometryOperators.quaternion_to_euler_zyz(q)
            phi = GeometryOperators.rad2deg(a)
            theta = GeometryOperators.rad2deg(b)
            psi = GeometryOperators.rad2deg(c)
            orientationParameters["Mode"] = "Euler Angle ZYZ"
            orientationParameters["Phi"] = self._dim_arg(phi, "deg")
            orientationParameters["Theta"] = self._dim_arg(theta, "deg")
            orientationParameters["Psi"] = self._dim_arg(psi, "deg")
        else:  # pragma: no cover
            raise ValueError("Specify the mode = 'view', 'axis', 'zxz', 'zyz', 'axisrotation' ")

        self.props = CsProps(self, orientationParameters)
        self._modeler.oeditor.CreateRelativeCS(self._orientation, self._attributes)
        self._modeler.coordinate_systems.insert(0, self)
        # this workaround is necessary because the reference CS is ignored at creation, it needs to be modified later
        self.ref_cs = reference_cs
        return self.update()

    @property
    def quaternion(self):
        """Quaternion computed based on specific axis mode.

        Returns
        -------
        list
        """
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


class Lists(PropsManager, object):
    """Manages Lists data and execution.

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
        except:  # pragma: no cover
            raise ValueError("Input List not correct for the type " + self.props["Type"])

        return True

    @pyaedt_function_handler()
    def create(
        self,
        object_list,
        name=None,
        type="Object",
    ):
        """Create a List.

        Parameters
        ----------
        object_list : list
            List of ``["Obj1", "Obj2"]`` objects or face ID if type is "Face".
            The default is ``None``, in which case all objects are selected.
        name : list, str
            List of names. The default is ``None``.
        type : str, optional
            List type. Options are ``"Object"``, ``"Face"``. The default is ``"Object"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """

        if not name:
            name = generate_unique_name(type + "List")

        object_list_new = self._list_verification(object_list, type)

        if object_list_new:
            olist = object_list_new
            if type == "Object":
                olist = ",".join(object_list_new)

            self.name = self._modeler.oeditor.CreateEntityList(
                ["NAME:GeometryEntityListParameters", "EntityType:=", type, "EntityList:=", olist],
                ["NAME:Attributes", "Name:=", name],
            )
            props = {}
            props["List"] = object_list_new

            props["ID"] = self._modeler.get_entitylist_id(self.name)
            props["Type"] = type

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

    @pyaedt_function_handler()
    def rename(self, newname):
        """Rename the List.

        Parameters
        ----------
        newname : str
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
                ["NAME:ChangedProps", ["NAME:Name", "Value:=", newname]],
            ],
        ]
        self._modeler.oeditor.ChangeProperty(argument)
        self.name = newname
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
                            obj_id = self._modeler.object_id_dict[element]
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
    >>> from pyaedt import Maxwell2d
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


class GeometryModeler(Modeler, object):
    """Manages the main AEDT Modeler functionalities for geometry-based designs.

    Parameters
    ----------
    app :
        Inherited parent object.
    is3d : bool, optional
        Whether the model is 3D. The default is ``True``.
    """

    def __init__(self, app, is3d=True):
        self._app = app
        self._odefinition_manager = self._app.odefinition_manager
        self._omaterial_manager = self._app.omaterial_manager
        Modeler.__init__(self, app)
        # TODO Refactor this as a dictionary with names as key
        self._coordinate_systems = None
        self._user_lists = None
        self._planes = None
        self._is3d = is3d

    @property
    def coordinate_systems(self):
        """Coordinate Systems."""
        if self._coordinate_systems is None:
            self._coordinate_systems = self._get_coordinates_data()
        return self._coordinate_systems

    @property
    def user_lists(self):
        """User Lists."""
        if not self._user_lists:
            self._user_lists = self._get_lists_data()
        return self._user_lists

    @property
    def planes(self):
        """Planes."""
        if not self._planes:
            self._planes = self._get_planes_data()
        return self._planes

    @property
    def oeditor(self):
        """Aedt oEditor Module.

        References
        ----------

        >>> oEditor = oDesign.SetActiveEditor("3D Modeler")"""

        return self._app.oeditor

    @property
    def materials(self):
        """Material library used in the project.

        Returns
        -------
        :class:`pyaedt.modules.MaterialLib.Materials`

        """
        return self._app.materials

    @pyaedt_function_handler()
    def _convert_list_to_ids(self, input_list, convert_objects_ids_to_name=True):
        """Convert a list to IDs.

        .. deprecated:: 0.5.0
           Use :func:`pyaedt.application.modeler.convert_to_selections` instead.

        Parameters
        ----------
        input_list : list
           List of object IDs.
        convert_objects_ids_to_name : bool, optional
             Whether to convert the object IDs to object names.
             The default is ``True``.

        Returns
        -------
        list
            List of object names.

        """
        warnings.warn("`_convert_list_to_ids` is deprecated. Use `convert_to_selections` instead.", DeprecationWarning)

        output_list = []
        if type(input_list) is not list:
            input_list = [input_list]
        for el in input_list:
            if type(el) is Object3d:
                output_list = [i.name for i in input_list]
            elif type(el) is EdgePrimitive or type(el) is FacePrimitive or type(el) is VertexPrimitive:
                output_list = [i.id for i in input_list]
            elif type(el) is int and convert_objects_ids_to_name:
                if el in list(self.objects.keys()):
                    output_list.append(self.objects[el].name)
                else:
                    output_list.append(el)
            else:
                output_list.append(el)
        return output_list

    def _get_coordinates_data(self):
        coord = []
        id2name = {1: "Global"}
        name2refid = {}
        if self._app.design_properties and "ModelSetup" in self._app.design_properties:
            cs = self._app.design_properties["ModelSetup"]["GeometryCore"]["GeometryOperations"]["CoordinateSystems"]
            for ds in cs:
                try:
                    if isinstance(cs[ds], (OrderedDict, dict)):
                        if cs[ds]["OperationType"] == "CreateRelativeCoordinateSystem":
                            props = cs[ds]["RelativeCSParameters"]
                            name = cs[ds]["Attributes"]["Name"]
                            cs_id = cs[ds]["ID"]
                            id2name[cs_id] = name
                            name2refid[name] = cs[ds]["ReferenceCoordSystemID"]
                            coord.append(CoordinateSystem(self, props, name))
                            if "ZXZ" in props["Mode"]:
                                coord[-1].mode = "zxz"
                            elif "ZYZ" in props["Mode"]:
                                coord[-1].mode = "zyz"
                            else:
                                coord[-1].mode = "axis"
                        elif cs[ds]["OperationType"] == "CreateFaceCoordinateSystem":
                            name = cs[ds]["Attributes"]["Name"]
                            cs_id = cs[ds]["ID"]
                            id2name[cs_id] = name
                            op_id = cs[ds]["PlaceHolderOperationID"]
                            geometry_part = self._app.design_properties["ModelSetup"]["GeometryCore"][
                                "GeometryOperations"
                            ]["ToplevelParts"]["GeometryPart"]
                            if isinstance(geometry_part, (OrderedDict, dict)):
                                op = geometry_part["Operations"]["FaceCSHolderOperation"]
                                if isinstance(op, (OrderedDict, dict)):
                                    if op["ID"] == op_id:
                                        props = op["FaceCSParameters"]
                                        coord.append(FaceCoordinateSystem(self, props, name))
                                elif isinstance(op, list):
                                    for iop in op:
                                        if iop["ID"] == op_id:
                                            props = iop["FaceCSParameters"]
                                            coord.append(FaceCoordinateSystem(self, props, name))
                                            break
                            elif isinstance(geometry_part, list):
                                for gp in geometry_part:
                                    op = gp["Operations"]["FaceCSHolderOperation"]
                                    if isinstance(op, (OrderedDict, dict)):
                                        if op["ID"] == op_id:
                                            props = op["FaceCSParameters"]
                                            coord.append(FaceCoordinateSystem(self, props, name))
                                    elif isinstance(op, list):
                                        for iop in op:
                                            if iop["ID"] == op_id:
                                                props = iop["FaceCSParameters"]
                                                coord.append(FaceCoordinateSystem(self, props, name))
                                                break
                    elif isinstance(cs[ds], list):
                        for el in cs[ds]:
                            if el["OperationType"] == "CreateRelativeCoordinateSystem":
                                props = el["RelativeCSParameters"]
                                name = el["Attributes"]["Name"]
                                cs_id = el["ID"]
                                id2name[cs_id] = name
                                name2refid[name] = el["ReferenceCoordSystemID"]
                                coord.append(CoordinateSystem(self, props, name))
                                if "ZXZ" in props["Mode"]:
                                    coord[-1].mode = "zxz"
                                elif "ZYZ" in props["Mode"]:
                                    coord[-1].mode = "zyz"
                                else:
                                    coord[-1].mode = "axis"
                            elif el["OperationType"] == "CreateFaceCoordinateSystem":
                                name = el["Attributes"]["Name"]
                                cs_id = el["ID"]
                                id2name[cs_id] = name
                                op_id = el["PlaceHolderOperationID"]
                                geometry_part = self._app.design_properties["ModelSetup"]["GeometryCore"][
                                    "GeometryOperations"
                                ]["ToplevelParts"]["GeometryPart"]
                                if isinstance(geometry_part, (OrderedDict, dict)):
                                    op = geometry_part["Operations"]["FaceCSHolderOperation"]
                                    if isinstance(op, (OrderedDict, dict)):
                                        if op["ID"] == op_id:
                                            props = op["FaceCSParameters"]
                                            coord.append(FaceCoordinateSystem(self, props, name))
                                    elif isinstance(op, list):
                                        for iop in op:
                                            if iop["ID"] == op_id:
                                                props = iop["FaceCSParameters"]
                                                coord.append(FaceCoordinateSystem(self, props, name))
                                                break
                                elif isinstance(geometry_part, list):
                                    for gp in geometry_part:
                                        try:
                                            op = gp["Operations"]["FaceCSHolderOperation"]
                                        except KeyError:
                                            continue
                                        if isinstance(op, (OrderedDict, dict)):
                                            if op["ID"] == op_id:
                                                props = op["FaceCSParameters"]
                                                coord.append(FaceCoordinateSystem(self, props, name))
                                        elif isinstance(op, list):
                                            for iop in op:
                                                if iop["ID"] == op_id:
                                                    props = iop["FaceCSParameters"]
                                                    coord.append(FaceCoordinateSystem(self, props, name))
                                                    break
                except:
                    pass
            for cs in coord:
                if isinstance(cs, CoordinateSystem):
                    try:
                        cs.ref_cs = id2name[name2refid[cs.name]]
                    except:
                        pass
        coord.reverse()
        return coord

    def _get_lists_data(self):
        """Retrieve user object list data.

        Returns
        -------
        [Dict with List information]
        """
        design_lists = []
        if self._app.design_properties and self._app.design_properties.get("ModelSetup", None):
            key1 = "GeometryOperations"
            key2 = "GeometryEntityLists"
            key3 = "GeometryEntityListOperation"
            try:
                entity_list = self._app.design_properties["ModelSetup"]["GeometryCore"][key1][key2]
                if entity_list:
                    geom_entry = copy.deepcopy(entity_list[key3])
                    if isinstance(geom_entry, (dict, OrderedDict)):
                        geom_entry = [geom_entry]
                    for data in geom_entry:
                        props = {}
                        name = data["Attributes"]["Name"]
                        props["ID"] = data["ID"]
                        props["Type"] = data["GeometryEntityListParameters"]["EntityType"]
                        if props["Type"] == "Object":
                            name_list = []
                            for element in data["GeometryEntityListParameters"]["EntityList"]:
                                element_name = self.oeditor.GetObjectNameByID(int(element))
                                name_list.append(element_name)
                            props["List"] = name_list
                        else:
                            props["List"] = data["GeometryEntityListParameters"]["EntityList"]
                        design_lists.append(Lists(self, props, name))
            except:
                self.logger.info("Lists were not retrieved from AEDT file")
        return design_lists

    def _get_planes_data(self):
        """Retrieve planes data.

        Returns
        -------
        [Dict with List information]
        """
        try:
            return {
                plane_name: self.oeditor.GetChildObject(plane_name)
                for plane_name in self.oeditor.GetChildNames("Planes")
            }
        except TypeError:
            return {}

    def __get__(self, instance, owner):
        self._app = instance
        return self

    @property
    def model_units(self):
        """Model units as a string. For example ``"mm"``.

        References
        ----------

        >>> oEditor.GetModelUnits
        >>> oEditor.SetModelUnits
        """
        return _retry_ntimes(10, self.oeditor.GetModelUnits)

    @model_units.setter
    def model_units(self, units):
        assert units in AEDT_UNITS["Length"], "Invalid units string {0}.".format(units)
        self.oeditor.SetModelUnits(["NAME:Units Parameter", "Units:=", units, "Rescale:=", False])

    @property
    def selections(self):
        """Selections.

        References
        ----------

        >>> oEditor.GetSelections
        """
        return self.oeditor.GetSelections()

    @property
    def obounding_box(self):
        """Bounding box.

        References
        ----------

        >>> oEditor.GetModelBoundingBox
        """
        return self.oeditor.GetModelBoundingBox()

    @pyaedt_function_handler()
    def fit_all(self):
        """Fit all.

        References
        ----------

        >>> oEditor.FitAll
        """
        self.oeditor.FitAll()

    @property
    def dimension(self):
        """Dimensions.

        Returns
        -------
        str
            Dimensionality, which is either ``"2D"`` or ``"3D"``.

        References
        ----------

        >>> oDesign.Is2D
        """
        try:
            if self._odesign.Is2D():
                return "2D"
            else:
                return "3D"
        except:
            if self.design_type == "2D Extractor":
                return "2D"
            else:
                return "3D"

    @property
    def design_type(self):
        """Design type.

        References
        ----------

        >>> oDesign.GetDesignType
        """
        return self._app.design_type

    @property
    def geometry_mode(self):
        """Geometry mode.

        References
        ----------

        >>> oDesign.GetGeometryMode"""
        return self._odesign.GetGeometryMode()

    @property
    def solid_bodies(self):
        """List of Object Names.

        .. note::
            Non-model objects are also returned.

        Returns
        -------
        list os str
            List of object names with the object name as the key.

        References
        ----------

        >>> oEditor.GetObjectsInGroup
        """
        if self.dimension == "3D":
            objects = self.oeditor.GetObjectsInGroup("Solids")
        else:
            objects = self.oeditor.GetObjectsInGroup("Sheets")
        return list(objects)

    @pyaedt_function_handler()
    def _find_perpendicular_points(self, face):

        if isinstance(face, str):
            vertices = [i.position for i in self[face].vertices]
        else:
            vertices = []
            for vertex in list(self.oeditor.GetVertexIDsFromFace(face)):
                vertices.append([float(i) for i in list(self.oeditor.GetVertexPosition(vertex))])
        assert len(vertices) > 2, "Automatic A-B Assignment can be done only on face with more than 2 vertices."
        origin = vertices[0]
        a_end = []
        b_end = []
        tol = 1e-10
        for v in vertices[1:]:
            edge1 = GeometryOperators.v_points(origin, v)
            for v2 in vertices[1:]:
                if v2 != v:
                    edge2 = GeometryOperators.v_points(origin, v2)
                    if abs(GeometryOperators.v_dot(edge1, edge2)) < tol:
                        a_end = v
                        b_end = v2
                        break
            if a_end:
                break
        if not a_end:
            a_end = vertices[1]
            b_end = vertices[2]
            return False, (origin, a_end, b_end)
        return True, (origin, a_end, b_end)

    @pyaedt_function_handler()
    def cover_lines(self, selection):
        """Cover a closed line and transform it to sheet.

        Parameters
        ----------
        selection : str, int
            Polyline object to cover.
        Returns
        -------
        bool

        References
        ----------

        >>> oEditor.CoverLines
        """
        obj_to_cover = self.convert_to_selections(selection, False)
        self.oeditor.CoverLines(["NAME:Selections", "Selections:=", obj_to_cover, "NewPartsModelFlag:=", "Model"])
        return True

    @pyaedt_function_handler()
    def create_coordinate_system(
        self,
        origin=None,
        reference_cs="Global",
        name=None,
        mode="axis",
        view="iso",
        x_pointing=None,
        y_pointing=None,
        psi=0,
        theta=0,
        phi=0,
        u=None,
    ):
        """Create a coordinate system.

        Parameters
        ----------
        origin : list
            List of ``[x, y, z]`` coordinates for the origin of the
            coordinate system.  The default is ``None``, in which case
            ``[0, 0, 0]`` is used.
        reference_cs : str, optional
            Name of the reference coordinate system. The default is
            ``"Global"``.
        name : str
            Name of the coordinate system. The default is ``None``.
        mode : str, optional
            Definition mode. Options are ``"view"``, ``"axis"``,
            ``"zxz"``, ``"zyz"``, and ``"axisrotation"``. The default
            is ``"axis"``.  Enumerator ``pyaedt.generic.constants.CSMODE`` can be used.

            * If ``mode="view"``, specify ``view``.
            * If ``mode="axis"``, specify ``x_pointing`` and ``y_pointing``.
            * If ``mode="zxz"`` or ``mode="zyz"``, specify ``phi``, ``theta``, and ``psi``.
            * If ``mode="axisrotation"``, specify ``theta`` and ``u``.

            Parameters not needed by the specified mode are ignored.
            For back compatibility, ``view="rotate"`` is the same as
            ``mode="axis"``.  The default mode, ``"axisrotation"``, is
            a coordinate system parallel to the global coordinate
            system centered in the global origin.

        view : str, int optional
            View for the coordinate system if ``mode="view"``. Options
            are ``"XY"``, ``"XZ"``, ``"XY"``, ``"iso"``, ``None``, and
            ``"rotate"`` (obsolete). The default is ``"iso"``.
            Enumerator ``pyaedt.generic.constants.VIEW`` can be used.

            .. note::
               Because the ``"rotate"`` option is obsolete, use
               ``mode="axis"`` instead.

        x_pointing : list, optional
            List of the ``[x, y, z]`` coordinates specifying the X axis
            pointing in the global coordinate system if ``mode="axis"``.
            The default is ``[1, 0, 0]``.
        y_pointing : list, optional
            List of the ``[x, y, z]`` coordinates specifying the Y axis
            pointing in the global coordinate system if ``mode="axis"``.
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
        :class:`pyaedt.modeler.Modeler.CoordinateSystem`
            Coordinate System Object.

        References
        ----------

        >>> oEditor.CreateRelativeCS
        """
        if name:
            cs_names = [i.name for i in self.coordinate_systems]
            if name in cs_names:
                raise AttributeError("A coordinate system with the specified name already exists!")

        cs = CoordinateSystem(self)
        if cs:
            result = cs.create(
                origin=origin,
                reference_cs=reference_cs,
                name=name,
                mode=mode,
                view=view,
                x_pointing=x_pointing,
                y_pointing=y_pointing,
                phi=phi,
                theta=theta,
                psi=psi,
                u=u,
            )
            if result:
                return cs
        return False

    @pyaedt_function_handler()
    def create_face_coordinate_system(
        self, face, origin, axis_position, axis="X", name=None, offset=None, rotation=0, always_move_to_end=True
    ):
        """Create a face coordinate system.
        The face coordinate has always the Z axis parallel to face normal.
        The X and Y axis lie on the face plane.

        Parameters
        ----------
        face : int, FacePrimitive
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
            Select which axis is considered with the option ``axix``.
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
        :class:`pyaedt.modeler.Modeler.FaceCoordinateSystem`

        """

        if name:
            cs_names = [i.name for i in self.coordinate_systems]
            if name in cs_names:  # pragma: no cover
                raise AttributeError("A coordinate system with the specified name already exists!")

        cs = FaceCoordinateSystem(self)
        if cs:
            result = cs.create(
                face=face,
                origin=origin,
                axis_position=axis_position,
                axis=axis,
                name=name,
                offset=offset,
                rotation=rotation,
                always_move_to_end=always_move_to_end,
            )

            if result:
                return cs
        return False

    @pyaedt_function_handler()
    def global_to_cs(self, point, ref_cs):
        """Transform a point from the global coordinate system to another coordinate system.

        Parameters
        ----------
        point : list
            List of the ``[x, y, z]`` coordinates to transform.
        ref_cs : str
            Name of the destination reference system.

        Returns
        -------
        list
            List of the transformed ``[x, y, z]`` coordinates.

        """
        if type(point) is not list or len(point) != 3:
            raise AttributeError("Point must be in format [x, y, z].")
        try:
            point = [float(i) for i in point]
        except:
            raise AttributeError("Point must be in format [x, y, z].")
        if ref_cs == "Global":
            return point
        cs_names = [i.name for i in self.coordinate_systems]
        if ref_cs not in cs_names:
            raise AttributeError("Specified coordinate system does not exist in the design.")

        def get_total_transformation(p, cs):
            idx = cs_names.index(cs)
            q = self.coordinate_systems[idx].quaternion
            ox = GeometryOperators.parse_dim_arg(
                self.coordinate_systems[idx].props["OriginX"],
                self.model_units,
                variable_manager=self._app.variable_manager,
            )
            oy = GeometryOperators.parse_dim_arg(
                self.coordinate_systems[idx].props["OriginY"],
                self.model_units,
                variable_manager=self._app.variable_manager,
            )
            oz = GeometryOperators.parse_dim_arg(
                self.coordinate_systems[idx].props["OriginZ"],
                self.model_units,
                variable_manager=self._app.variable_manager,
            )
            o = [ox, oy, oz]
            refcs = self.coordinate_systems[idx].ref_cs
            if refcs == "Global":
                p1 = p
            else:
                p1 = get_total_transformation(p, refcs)
            p2 = GeometryOperators.q_rotation_inv(GeometryOperators.v_sub(p1, o), q)
            return p2

        return get_total_transformation(point, ref_cs)

    @pyaedt_function_handler()
    def set_working_coordinate_system(self, name):
        """Set the working coordinate system to another coordinate system.

        Parameters
        ----------
        name : str, FaceCoordinateSystem, CoordinateSystem
            Name of the coordinate system to set as the working coordinate system.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.SetWCS
        """
        if isinstance(name, BaseCoordinateSystem):
            self.oeditor.SetWCS(
                ["NAME:SetWCS Parameter", "Working Coordinate System:=", name.name, "RegionDepCSOk:=", False]
            )
        else:
            self.oeditor.SetWCS(
                ["NAME:SetWCS Parameter", "Working Coordinate System:=", name, "RegionDepCSOk:=", False]
            )
        return True

    @pyaedt_function_handler()
    def set_objects_deformation(self, objects):
        """Assign deformation objects to a Workbench link.

        Parameters
        ----------
        objects : list
            List of the deformation objects to assign to the Workbench link.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oDesign.SetObjectDeformation
        """
        self.logger.info("Enabling deformation feedback")
        try:
            self._odesign.SetObjectDeformation(["EnabledObjects:=", objects])
        except:
            self.logger.error("Failed to enable the deformation dependence")
            return False
        else:
            self.logger.info("Successfully enabled deformation feedback")
            return True

    @pyaedt_function_handler()
    def set_objects_temperature(self, objects, ambient_temp=22, create_project_var=False):
        """Assign temperatures to objects.

        The materials assigned to the objects must have a thermal modifier.

        Parameters
        ----------
        objects : list
            List of objects.
        ambient_temp : float, optional
            Ambient temperature. The default is ``22``.
        create_project_var : bool, optional
            Whether to create a project variable for the ambient temperature.
            The default is ``False``. If ``True,`` ``$AmbientTemp`` is created.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oDesign.SetObjectTemperature
        """
        self.logger.info("Set model temperature and enabling Thermal Feedback")
        if create_project_var:
            self._app.variable_manager["$AmbientTemp"] = str(ambient_temp) + "cel"
            var = "$AmbientTemp"
        else:
            var = str(ambient_temp) + "cel"
        vargs1 = [
            "NAME:TemperatureSettings",
            "IncludeTemperatureDependence:=",
            True,
            "EnableFeedback:=",
            True,
            "Temperatures:=",
        ]
        vargs2 = []
        for obj in objects:
            mat = self[obj].material_name
            th = self._app.materials.check_thermal_modifier(mat)
            if th:
                vargs2.append(obj)
                vargs2.append(var)
        if not vargs2:
            return False
        else:
            vargs1.append(vargs2)
        try:
            self._odesign.SetObjectTemperature(vargs1)
        except:
            self.logger.error("Failed to enable the temperature dependence")
            return False
        else:
            self.logger.info("Assigned Objects Temperature")
            return True

    @pyaedt_function_handler()
    def _create_sheet_from_object_closest_edge(self, startobj, endobject, axisdir, portonplane):
        """Create a sheet from the edge closest to the object.

        Parameters
        ----------
        startobj : str
            Name of the starting object.
        endobject : str
            Name of the ending object.
        axisdir : int
           Axis direction. Options are ``0`` through ``5``.
        portonplane : bool
            Whether edges are to be on the plane orthogonal to the axis
            direction.

        Returns
        -------
        str
            Name of the sheet.
        list
            List of float values of the first edge midpoint.
            Point in ``[x, y, z]`` coordinates.
        list
            List of float values of the second edge midpoint.
            Point in ``[x, y, z]`` coordinates.

        """
        out, parallel = self.find_closest_edges(startobj, endobject, axisdir)
        port_edges = self.get_equivalent_parallel_edges(out, portonplane, axisdir, startobj, endobject)
        if port_edges is None or port_edges is False:
            port_edges = []
            for e in out:
                edge = self.create_object_from_edge(e)
                port_edges.append(edge)
        edge_0 = port_edges[0].edges[0]
        edge_1 = port_edges[1].edges[0]
        sheet_name = port_edges[0].name
        point0 = edge_0.midpoint
        point1 = edge_1.midpoint
        self.connect(port_edges)
        return sheet_name, point0, point1

    @pyaedt_function_handler()
    def find_point_around(self, objectname, startposition, offset, plane):
        """Find the point around an object.

        Parameters
        ----------
        objectname : str
            Name of the object.
        startposition : list
            List of the ``[x, y, z]`` coordinates for the starting
            position of the object.
        offset :
            Offset to apply.
        plane : str
            Coordinate plane of the arc. Choices are ``"YZ"``,
            ``"ZX"``, and ``"XY"``.


        Returns
        -------
        list
            List of the ``[x, y, z]`` coordinates for the point.

        """
        position = [0, 0, 0]
        angle = 0
        if plane == 0:
            while angle <= 360:
                position[0] = startposition[0] + offset * math.cos(math.pi * angle / 180)
                position[1] = startposition[1] + offset * math.sin(math.pi * angle / 180)
                if objectname in self.get_bodynames_from_position(startposition):
                    angle = 400
                else:
                    angle += 90
        elif plane == 1:
            while angle <= 360:
                position[1] = startposition[1] + offset * math.cos(math.pi * angle / 180)
                position[2] = startposition[2] + offset * math.sin(math.pi * angle / 180)
                if objectname in self.get_bodynames_from_position(startposition):
                    angle = 400
                else:
                    angle += 90
        elif plane == 2:
            while angle <= 360:
                position[0] = startposition[0] + offset * math.cos(math.pi * angle / 180)
                position[2] = startposition[2] + offset * math.sin(math.pi * angle / 180)
                if objectname in self.get_bodynames_from_position(startposition):
                    angle = 400
                else:
                    angle += 90
        return position

    @pyaedt_function_handler()
    def create_sheet_to_ground(self, objectname, groundname=None, axisdir=0, sheet_dim=1):
        """Create a sheet between an object and a ground plane.

        The ground plane must be bigger than the object and perpendicular
        to one of the three axes.

        Parameters
        ----------
        objectname : str
            Name of the object.
        groundname : str, optional
            Name of the ground. The default is ``None``, in which case the
            bounding box is used.
        axisdir : int, optional
            Axis direction. Options are ``0`` through ``5``. The default is ``0``.
        sheet_dim : optional
            Sheet dimension in millimeters. The default is ``1``.

        Returns
        -------
        int
            ID of the sheet created.

        References
        ----------

        >>> oEditor.CreatePolyline
        """
        if axisdir > 2:
            obj_cent = [-1e6, -1e6, -1e6]
        else:
            obj_cent = [1e6, 1e6, 1e6]
        face_ob = None
        for face in self[objectname].faces:
            center = face.center
            if not center:
                continue
            if axisdir > 2 and center[axisdir - 3] > obj_cent[axisdir - 3]:
                obj_cent = center
                face_ob = face
            elif axisdir <= 2 and center[axisdir] < obj_cent[axisdir]:
                obj_cent = center
                face_ob = face
        vertex = face_ob.vertices
        start = vertex[0].position

        if not groundname:
            gnd_cent = []
            bounding = self.get_model_bounding_box()
            if axisdir < 3:
                for i in bounding[0:3]:
                    gnd_cent.append(float(i))
            else:
                for i in bounding[3:]:
                    gnd_cent.append(float(i))
        else:
            ground_plate = self[groundname]
            if axisdir > 2:
                gnd_cent = [1e6, 1e6, 1e6]
            else:
                gnd_cent = [-1e6, -1e6, -1e6]
            face_gnd = ground_plate.faces
            for face in face_gnd:
                center = face.center
                if not center:
                    continue
                if axisdir > 2 and center[axisdir - 3] < gnd_cent[axisdir - 3]:
                    gnd_cent = center
                elif axisdir <= 2 and center[axisdir] > gnd_cent[axisdir]:
                    gnd_cent = center

        axisdist = obj_cent[divmod(axisdir, 3)[1]] - gnd_cent[divmod(axisdir, 3)[1]]
        if axisdir < 3:
            axisdist = -axisdist

        if divmod(axisdir, 3)[1] == 0:
            cs = self._app.PLANE.YZ
            vector = [axisdist, 0, 0]
        elif divmod(axisdir, 3)[1] == 1:
            cs = self._app.PLANE.ZX
            vector = [0, axisdist, 0]
        elif divmod(axisdir, 3)[1] == 2:
            cs = self._app.PLANE.XY
            vector = [0, 0, axisdist]

        offset = self.find_point_around(objectname, start, sheet_dim, cs)
        p1 = self.create_polyline([start, offset])
        p2 = p1.clone().move(vector)
        self.connect([p1, p2])

        return p1

    @pyaedt_function_handler()
    def _get_faceid_on_axis(self, objname, axisdir):
        """Get the ID of the face on the axis.

        Parameters
        ----------
        objname : str
            Name of the object.
        axisdir : int
            Axis direction. Options are ``1`` through ``5``.

        Returns
        -------
        int
            ID of the face.

        """
        faces = self.get_object_faces(objname)
        face = None
        center = None
        for f in faces:
            try:
                c = self.get_face_center(f)
                if not face and c:
                    face = f
                    center = c
                elif axisdir < 3 and c[axisdir] < center[axisdir]:
                    face = f
                    center = c
                elif axisdir > 2 and c[axisdir - 3] > center[axisdir - 3]:
                    face = f
                    center = c
            except:
                pass
        return face

    @pyaedt_function_handler()
    def _create_microstrip_sheet_from_object_closest_edge(self, startobj, endobject, axisdir, vfactor=3, hfactor=5):
        def duplicate_and_unite(sheet_name, array1, array2, dup_factor):
            status, list = self.duplicate_along_line(sheet_name, array1, dup_factor + 1)
            status, list2 = self.duplicate_along_line(sheet_name, array2, dup_factor + 1)
            list_unite.extend(list)
            list_unite.extend(list2)
            self.unite(list_unite)

        tol = 1e-6
        out, parallel = self.find_closest_edges(startobj, endobject, axisdir)
        port_edges = self.get_equivalent_parallel_edges(out, True, axisdir, startobj, endobject)
        if port_edges is None:
            return False
        sheet_name = port_edges[0].name
        point0 = port_edges[0].edges[0].midpoint
        point1 = port_edges[1].edges[0].midpoint
        len = port_edges[0].edges[0].length
        vect = GeometryOperators.v_points(point1, point0)
        l1 = out[0].length
        l2 = out[1].length
        if l1 < l2:
            vect_t = [i * (vfactor - 1) for i in vect]
            self.move(port_edges[0], vect_t)
        else:
            vect_t = [i * (1 - vfactor) for i in vect]
            self.move(port_edges[1], vect_t)

        self.connect(port_edges)
        list_unite = [sheet_name]
        dup_factor = divmod((hfactor + 1), 2)[0]
        coeff = float(hfactor - 1) / 2 / dup_factor

        if divmod(axisdir, 3)[1] == 0 and abs(vect[1]) < tol:
            duplicate_and_unite(sheet_name, [0, len * coeff, 0], [0, -len * coeff, 0], dup_factor)
        elif divmod(axisdir, 3)[1] == 0 and abs(vect[2]) < tol:
            duplicate_and_unite(sheet_name, [0, 0, len * coeff], [0, 0, -len * coeff], dup_factor)
        elif divmod(axisdir, 3)[1] == 1 and abs(vect[0]) < tol:
            duplicate_and_unite(sheet_name, [len * coeff, 0, 0], [-len * coeff, 0, 0], dup_factor)
        elif divmod(axisdir, 3)[1] == 1 and abs(vect[2]) < tol:
            duplicate_and_unite(sheet_name, [0, 0, len * coeff], [0, 0, -len * coeff], dup_factor)
        elif divmod(axisdir, 3)[1] == 2 and abs(vect[0]) < tol:
            duplicate_and_unite(sheet_name, [len * coeff, 0, 0], [-len * coeff, 0, 0], dup_factor)
        elif divmod(axisdir, 3)[1] == 2 and abs(vect[1]) < tol:
            duplicate_and_unite(sheet_name, [0, len * coeff, 0], [0, -len * coeff, 0], dup_factor)

        return sheet_name, point0, point1

    @pyaedt_function_handler()
    def get_boundaries_name(self):
        """Retrieve all boundary names.

        Returns
        -------
        list
            List of boundary names. Boundaries with multiple modes will return one
            boundary for each mode.

        References
        ----------

        >>> oModule.GetBoundaries
        """
        if self._app.design_type == "Icepak":
            return list(self._app.odesign.GetChildObject("Thermal").GetChildNames())
        else:
            list_names = list(self._app.oboundary.GetBoundaries())
            del list_names[1::2]
            return list_names

    @pyaedt_function_handler()
    def set_object_model_state(self, obj_list, model=True):
        """Set a list of objects to either models or non-models.

        Parameters
        ----------
        obj_list : list
            List of objects IDs or names.
        model : bool, optional
            Whether to set the objects as models. The default is ``True``.
            If ``False``, the objects are set as non-models.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.ChangeProperty
        """
        selections = self.convert_to_selections(obj_list, True)
        for obj in selections:
            self[obj].model = model
        return True

    @pyaedt_function_handler()
    def get_objects_in_group(self, group):
        """Retrieve a list of objects belonging to a group.

        Parameters
        ----------
        group : str
            Name of the group.

        Returns
        -------
        list
            List of objects belonging to the group.

        References
        ----------

        >>> oEditor.GetObjectsInGroup
        """
        if type(group) is not str:
            raise ValueError("Group name must be a string")
        group_objs = list(self.oeditor.GetObjectsInGroup(group))
        if not group_objs:
            return None
        return group_objs

    @pyaedt_function_handler()
    def get_group_bounding_box(self, group):
        """Retrieve the bounding box of a group.

        Parameters
        ----------
        group : str
            Name of the group.

        Returns
        -------
        list
            List of six float values representing the bounding box
            in the form ``[min_x, min_y, min_z, max_x, max_y, max_z]``.

        References
        ----------

        >>> oEditor.GetObjectsInGroup
        >>> oEditor.GetModelBoundingBox
        """
        if type(group) is not str:
            raise ValueError("Group name must be a string")
        group_objs = list(self.oeditor.GetObjectsInGroup(group))
        if not group_objs:
            return None
        all_objs = self.object_names
        objs_to_unmodel = [i for i in all_objs if i not in group_objs]
        if objs_to_unmodel:
            vArg1 = ["NAME:Model", "Value:=", False]
            self._change_geometry_property(vArg1, objs_to_unmodel)
            bounding = self.get_model_bounding_box()
            self._odesign.Undo()
        else:
            bounding = self.get_model_bounding_box()
        return bounding

    @pyaedt_function_handler()
    def convert_to_selections(self, objtosplit, return_list=False):
        """Convert one or more object to selections.

        Parameters
        ----------
        objtosplit : str, int, list
            One or more objects to convert to selections. A list can contain
            both strings (object names) and integers (object IDs).
        return_list : bool, option
            Whether to return a list of the selections. The default is
            ``False``, in which case a string of the selections is returned.
            If ``True``, a list of the selections is returned.

        Returns
        -------
        str or list
           String or list of the selections.

        """
        if "netref.builtins.list" in str(type(objtosplit)):
            list_new = []
            for i in range(len(objtosplit)):
                list_new.append(objtosplit[i])
        elif not isinstance(objtosplit, list):
            objtosplit = [objtosplit]
        objnames = []
        for el in objtosplit:
            if isinstance(el, int) and el in list(self.objects.keys()):
                objnames.append(self.objects[el].name)
            elif isinstance(el, int):
                objnames.append(el)
            elif isinstance(el, Object3d):
                objnames.append(el.name)
            elif isinstance(el, FacePrimitive) or isinstance(el, EdgePrimitive) or isinstance(el, VertexPrimitive):
                objnames.append(el.id)
            elif isinstance(el, str):
                objnames.append(el)
            else:
                return False
        if return_list:
            return objnames
        else:
            return ",".join(objnames)

    @pyaedt_function_handler()
    def split(self, objects, plane, sides="Both"):
        """Split a list of objects.

        Parameters
        ----------
        objects : str, int, or list
            One or more objects to split. A list can contain
            both strings (object names) and integers (object IDs).
        plane : str
            Coordinate plane of the cut or the Application.PLANE object.
            Choices for the coordinate plane are ``"XY"``, ``"YZ"``, and ``"ZX"``.
        sides : str
            Which side to keep. Options are ``"Both"``, ``"PositiveOnly"``,
            and ``"NegativeOnly"``. The default is ``"Both"``, in which case
            all objects are kept after the split.

        Returns
        -------
        list of :class:`pyaedt.modeler.object3d.Object3d`
            List of split objects.

        References
        ----------

        >>> oEditor.Split
        """
        planes = GeometryOperators.cs_plane_to_plane_str(plane)
        selections = self.convert_to_selections(objects)
        all_objs = [i for i in self.object_names]
        self.oeditor.Split(
            ["NAME:Selections", "Selections:=", selections, "NewPartsModelFlag:=", "Model"],
            [
                "NAME:SplitToParameters",
                "SplitPlane:=",
                planes,
                "WhichSide:=",
                sides,
                "ToolType:=",
                "PlaneTool",
                "ToolEntityID:=",
                -1,
                "SplitCrossingObjectsOnly:=",
                False,
                "DeleteInvalidObjects:=",
                True,
            ],
        )
        self.refresh_all_ids()
        return [selections] + [i for i in self.object_names if i not in all_objs]

    @pyaedt_function_handler()
    def duplicate_and_mirror(
        self,
        objid,
        position,
        vector,
        is_3d_comp=False,
        duplicate_assignment=True,
    ):
        """Duplicate and mirror a selection.

        Parameters
        ----------
        objid : str, int, or  Object3d
            Name or ID of the object.
        position : float
            List of the ``[x, y, z]`` coordinates or
            Application.Position object for the selection.
        vector : float
            List of the ``[x1, y1, z1]`` coordinates or
            Application.Position object for the vector.
        is_3d_comp : bool, optional
            If ``True``, the method will try to return the duplicated list of 3dcomponents. The default is ``False``.
        duplicate_assignment : bool, optional
            If True, the method duplicates selection assignments. The default value is ``True``.

        Returns
        -------
        list
            List of objects created or an empty list.

        References
        ----------

        >>> oEditor.DuplicateMirror
        """
        selections = self.convert_to_selections(objid)
        Xpos, Ypos, Zpos = self._pos_with_arg(position)
        Xnorm, Ynorm, Znorm = self._pos_with_arg(vector)

        vArg1 = ["NAME:Selections", "Selections:=", selections, "NewPartsModelFlag:=", "Model"]
        vArg2 = ["NAME:DuplicateToMirrorParameters"]
        vArg2.append("DuplicateMirrorBaseX:="), vArg2.append(Xpos)
        vArg2.append("DuplicateMirrorBaseY:="), vArg2.append(Ypos)
        vArg2.append("DuplicateMirrorBaseZ:="), vArg2.append(Zpos)
        vArg2.append("DuplicateMirrorNormalX:="), vArg2.append(Xnorm)
        vArg2.append("DuplicateMirrorNormalY:="), vArg2.append(Ynorm)
        vArg2.append("DuplicateMirrorNormalZ:="), vArg2.append(Znorm)
        vArg3 = ["NAME:Options", "DuplicateAssignments:=", duplicate_assignment]
        if is_3d_comp:
            orig_3d = [i for i in self.user_defined_component_names]
        added_objs = _retry_ntimes(10, self.oeditor.DuplicateMirror, vArg1, vArg2, vArg3)
        self.add_new_objects()
        if is_3d_comp:
            added_3d_comps = [i for i in self.user_defined_component_names if i not in orig_3d]
            if added_3d_comps:
                self.logger.info("Found 3D Components Duplication")
                return added_3d_comps
        return added_objs

    @pyaedt_function_handler()
    def mirror(self, objid, position, vector):
        """Mirror a selection.

        Parameters
        ----------
        objid : str, int, or Object3d
            Name or ID of the object.
        position : int or float
            List of the ``[x, y, z]`` coordinates or the
            Application.Position object for the selection.
        vector : float
            List of the ``[x1, y1, z1]`` coordinates or
            the Application.Position object for the vector.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.Mirror
        """
        selections = self.convert_to_selections(objid)
        Xpos, Ypos, Zpos = self._pos_with_arg(position)
        Xnorm, Ynorm, Znorm = self._pos_with_arg(vector)

        vArg1 = ["NAME:Selections", "Selections:=", selections, "NewPartsModelFlag:=", "Model"]
        vArg2 = ["NAME:MirrorParameters"]
        vArg2.append("MirrorBaseX:="), vArg2.append(Xpos)
        vArg2.append("MirrorBaseY:="), vArg2.append(Ypos)
        vArg2.append("MirrorBaseZ:="), vArg2.append(Zpos)
        vArg2.append("MirrorNormalX:="), vArg2.append(Xnorm)
        vArg2.append("MirrorNormalY:="), vArg2.append(Ynorm)
        vArg2.append("MirrorNormalZ:="), vArg2.append(Znorm)

        self.oeditor.Mirror(vArg1, vArg2)

        return True

    @pyaedt_function_handler()
    def move(self, objid, vector):
        """Move objects from a list.

        Parameters
        ----------
        objid : list, Position object
            List of object IDs.
        vector : list
            Vector of the direction move. It can be a list of the ``[x, y, z]``
            coordinates or a Position object.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.Move
        """
        Xvec, Yvec, Zvec = self._pos_with_arg(vector)
        szSelections = self.convert_to_selections(objid)

        vArg1 = ["NAME:Selections", "Selections:=", szSelections, "NewPartsModelFlag:=", "Model"]
        vArg2 = ["NAME:TranslateParameters"]
        vArg2.append("TranslateVectorX:="), vArg2.append(Xvec)
        vArg2.append("TranslateVectorY:="), vArg2.append(Yvec)
        vArg2.append("TranslateVectorZ:="), vArg2.append(Zvec)

        if self.oeditor is not None:
            self.oeditor.Move(vArg1, vArg2)
        return True

    @pyaedt_function_handler()
    def duplicate_around_axis(
        self,
        objid,
        cs_axis,
        angle=90,
        nclones=2,
        create_new_objects=True,
        is_3d_comp=False,
        duplicate_assignment=True,
    ):
        """Duplicate a selection around an axis.

        Parameters
        ----------
        objid : list, str, int, Object3d or UserDefinedComponent
            Name or ID of the object.
        cs_axis :
            Coordinate system axis or the Application.CoordinateSystemAxis object.
        angle : float, optional
            Angle rotation in degees. The default is ``90``.
        nclones : int, optional
            Number of clones. The default is ``2``.
        create_new_objects :
            Whether to create the copies as new objects. The
            default is ``True``.
        is_3d_comp : bool, optional
            If ``True``, the method will try to return the duplicated list of 3dcomponents. The default is ``False``.
        duplicate_assignment : bool, optional
            If True, the method duplicates selection assignments. The default value is ``True``.

        Returns
        -------
        tuple

        References
        ----------

        >>> oEditor.DuplicateAroundAxis
        """
        selections = self.convert_to_selections(objid)

        vArg1 = ["NAME:Selections", "Selections:=", selections, "NewPartsModelFlag:=", "Model"]
        vArg2 = [
            "NAME:DuplicateAroundAxisParameters",
            "CreateNewObjects:=",
            create_new_objects,
            "WhichAxis:=",
            GeometryOperators.cs_axis_str(cs_axis),
            "AngleStr:=",
            self._arg_with_dim(angle, "deg"),
            "Numclones:=",
            str(nclones),
        ]
        vArg3 = ["NAME:Options", "DuplicateAssignments:=", duplicate_assignment]
        added_objs = self.oeditor.DuplicateAroundAxis(vArg1, vArg2, vArg3)
        self._duplicate_added_objects_tuple()
        if is_3d_comp:
            return self._duplicate_added_components_tuple()
        return True, list(added_objs)

    def _duplicate_added_objects_tuple(self):
        added_objects = self.add_new_objects()
        if added_objects:
            return True, added_objects
        else:
            return False, []

    def _duplicate_added_components_tuple(self):
        added_component = self.add_new_user_defined_component()
        if added_component:
            return True, added_component
        else:
            return False, []

    @pyaedt_function_handler()
    def duplicate_along_line(
        self,
        objid,
        vector,
        nclones=2,
        attachObject=False,
        is_3d_comp=False,
        duplicate_assignment=True,
    ):
        """Duplicate a selection along a line.

        Parameters
        ----------
        objid : list, str, int, :class:`pyaedt.modeler.Object3d.Object3d`
            Name or ID of the object.
        vector : list
            List of ``[x1,y1,z1]`` coordinates or the Application.Position object for
            the vector.
        attachObject : bool, optional
            The default is ``False``.
        nclones : int, optional
            Number of clones. The default is ``2``.
        is_3d_comp : bool, optional
            If True, the method will try to return the duplicated list of 3dcomponents. The default is ``False``.
        duplicate_assignment : bool, optional
            If True, the method duplicates selection assignments. The default value is ``True``.

        Returns
        -------
        tuple

        References
        ----------

        >>> oEditor.DuplicateAlongLine
        """
        selections = self.convert_to_selections(objid)
        Xpos, Ypos, Zpos = self._pos_with_arg(vector)

        vArg1 = ["NAME:Selections", "Selections:=", selections, "NewPartsModelFlag:=", "Model"]
        vArg2 = ["NAME:DuplicateToAlongLineParameters"]
        vArg2.append("CreateNewObjects:="), vArg2.append(not attachObject)
        vArg2.append("XComponent:="), vArg2.append(Xpos)
        vArg2.append("YComponent:="), vArg2.append(Ypos)
        vArg2.append("ZComponent:="), vArg2.append(Zpos)
        vArg2.append("Numclones:="), vArg2.append(str(nclones))
        vArg3 = ["NAME:Options", "DuplicateAssignments:=", duplicate_assignment]
        added_objs = self.oeditor.DuplicateAlongLine(vArg1, vArg2, vArg3)
        self._duplicate_added_objects_tuple()
        if is_3d_comp:
            return self._duplicate_added_components_tuple()
        return True, list(added_objs)

    @pyaedt_function_handler()
    def thicken_sheet(self, objid, thickness, bBothSides=False):
        """Thicken the sheet of the selection.

        Parameters
        ----------
        objid : list, str, int, :class:`pyaedt.modeler.Object3d.Object3d`
            Name or ID of the object.
        thickness : float, str
            Amount to thicken the sheet by.
        bBothSides : bool, optional
            Whether to thicken the sheet on both side. The default is ``False``.

        Returns
        -------
        pyaedt.modeler.object3d.Object3d

        References
        ----------

        >>> oEditor.ThickenSheet
        """
        selections = self.convert_to_selections(objid)

        vArg1 = ["NAME:Selections", "Selections:=", selections, "NewPartsModelFlag:=", "Model"]
        vArg2 = ["NAME:SheetThickenParameters"]
        vArg2.append("Thickness:="), vArg2.append(self._arg_with_dim(thickness))
        vArg2.append("BothSides:="), vArg2.append(bBothSides)

        self.oeditor.ThickenSheet(vArg1, vArg2)
        return self.update_object(objid)

    @pyaedt_function_handler()
    def sweep_along_normal(self, obj_name, face_id, sweep_value=0.1):
        """Sweep the selection along the vector.

        Parameters
        ----------
        obj_name : list, str, int, :class:`pyaedt.modeler.Object3d.Object3d`
            Name or ID of the object.
        face_id : int
            Face to sweep.
        sweep_value : float, optional
            Sweep value. The default is ``0.1``.

        Returns
        -------
        pyaedt.modeler.object3d.Object3d

        References
        ----------

        >>> oEditor.SweepFacesAlongNormal
        """
        selections = self.convert_to_selections(obj_name)
        vArg1 = ["NAME:Selections", "Selections:=", selections, "NewPartsModelFlag:=", "Model"]
        vArg2 = ["NAME:Parameters"]
        vArg2.append(
            [
                "NAME:SweepFaceAlongNormalToParameters",
                "FacesToDetach:=",
                [face_id],
                "LengthOfSweep:=",
                self._arg_with_dim(sweep_value),
            ]
        )

        objs = self._all_object_names
        self.oeditor.SweepFacesAlongNormal(vArg1, vArg2)
        self.cleanup_objects()
        objs2 = self._all_object_names
        obj = [i for i in objs2 if i not in objs]
        for el in obj:
            self._create_object(el)
        if obj:
            return self.update_object(self[obj[0]])
        return False

    @pyaedt_function_handler()
    def sweep_along_vector(self, objid, sweep_vector, draft_angle=0, draft_type="Round"):
        """Sweep the selection along a vector.

        Parameters
        ----------
        objid : list, str, int, :class:`pyaedt.modeler.Object3d.Object3d`
            Name or ID of the object.
        sweep_vector : float
            List of ``[x1, y1, z1]`` coordinates or Application.Position object for
            the vector.
        draft_angle : float, optional
            Draft angle in degrees. The default is ``0``.
        draft_type : str
            Type of the draft. Options are ``"Round"``, ``"Natural"``,
            and ``"Extended"``. The default is ``"Round"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.SweepAlongVector
        """
        selections = self.convert_to_selections(objid)
        vectorx, vectory, vectorz = self._pos_with_arg(sweep_vector)
        vArg1 = ["NAME:Selections", "Selections:=", selections, "NewPartsModelFlag:=", "Model"]
        vArg2 = ["NAME:VectorSweepParameters"]
        vArg2.append("DraftAngle:="), vArg2.append(self._arg_with_dim(draft_angle, "deg"))
        vArg2.append("DraftType:="), vArg2.append(GeometryOperators.draft_type_str(draft_type))
        vArg2.append("SweepVectorX:="), vArg2.append(vectorx)
        vArg2.append("SweepVectorY:="), vArg2.append(vectory)
        vArg2.append("SweepVectorZ:="), vArg2.append(vectorz)

        self.oeditor.SweepAlongVector(vArg1, vArg2)

        return self.update_object(objid)

    @pyaedt_function_handler()
    def sweep_along_path(
        self, objid, sweep_object, draft_angle=0, draft_type="Round", is_check_face_intersection=False, twist_angle=0
    ):
        """Sweep the selection along a path.

        Parameters
        ----------
        objid : list, str, int, :class:`pyaedt.modeler.Object3d.Object3d`
            Name or ID of the object.
        sweep_object : str, int
            Name or ID of the sweep.
        draft_angle : float, optional
            Draft angle in degrees. The default is ``0``.
        draft_type : str
            Type of the draft. Options are ``"Round"``, ``"Natural"``,
            and ``"Extended"``. The default is ``"Round"``.
        is_check_face_intersection : bool, optional
            The default is ``False``.
        twist_angle : float, optional
           Twist angle in degrees. The default is ``0``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.SweepAlongPath
        """
        selections = self.convert_to_selections(objid) + "," + self.convert_to_selections(sweep_object)
        vArg1 = ["NAME:Selections", "Selections:=", selections, "NewPartsModelFlag:=", "Model"]
        vArg2 = ["NAME:PathSweepParameters"]
        vArg2.append("DraftAngle:="), vArg2.append(self._arg_with_dim(draft_angle, "deg"))
        vArg2.append("DraftType:="), vArg2.append(GeometryOperators.draft_type_str(draft_type))
        vArg2.append("CheckFaceFaceIntersection:="), vArg2.append(is_check_face_intersection)
        vArg2.append("TwistAngle:="), vArg2.append(str(twist_angle) + "deg")

        self.oeditor.SweepAlongPath(vArg1, vArg2)

        return self.update_object(objid)

    @pyaedt_function_handler()
    def sweep_around_axis(self, objid, cs_axis, sweep_angle=360, draft_angle=0, number_of_segments=0):
        """Sweep the selection around the axis.

        Parameters
        ----------
        objid : list, str, int, :class:`pyaedt.modeler.Object3d.Object3d`
            Name or ID of the object.
        cs_axis :
            Coordinate system axis or the Application.CoordinateSystemAxis object.
        sweep_angle : float
            Sweep angle in degrees. The default is ``360``.
        draft_angle : float
            Draft angle in degrees. The default is ``0``.
        number_of_segments : int, optional
            Number of segments of the sweep operation. Default is ``0``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.SweepAroundAxis
        """
        selections = self.convert_to_selections(objid)

        vArg1 = ["NAME:Selections", "Selections:=", selections, "NewPartsModelFlag:=", "Model"]
        vArg2 = [
            "NAME:AxisSweepParameters",
            "DraftAngle:=",
            self._arg_with_dim(draft_angle, "deg"),
            "DraftType:=",
            "Round",
            "CheckFaceFaceIntersection:=",
            False,
            "SweepAxis:=",
            GeometryOperators.cs_axis_str(cs_axis),
            "SweepAngle:=",
            self._arg_with_dim(sweep_angle, "deg"),
            "NumOfSegments:=",
            str(number_of_segments),
        ]

        self.oeditor.SweepAroundAxis(vArg1, vArg2)

        return self.update_object(objid)

    @pyaedt_function_handler()
    def section(self, object_list, plane, create_new=True, section_cross_object=False):
        """Section the selection.

        Parameters
        ----------
        object_list : list, str, int, or  :class:`pyaedt.modeler.Object3d.Object3d`
            One or more objects to section.
        plane : str
            Coordinate plane or Application.PLANE object.
            Choices for the coordinate plane are ``"XY"``, ``"YZ"``, and ``"ZX"``.'
        create_new : bool, optional
            The default is ``True``, but this parameter has no effect.
        section_cross_object : bool, optional
            The default is ``False``, but this parameter has no effect.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.Section
        """
        section_plane = GeometryOperators.cs_plane_to_plane_str(plane)

        selections = self.convert_to_selections(object_list)

        self.oeditor.Section(
            ["NAME:Selections", "Selections:=", selections, "NewPartsModelFlag:=", "Model"],
            [
                "NAME:SectionToParameters",
                "CreateNewObjects:=",
                create_new,
                "SectionPlane:=",
                section_plane,
                "SectionCrossObject:=",
                section_cross_object,
            ],
        )
        self.refresh_all_ids()
        return True

    @pyaedt_function_handler()
    def separate_bodies(self, object_list, create_group=False):
        """Separate bodies of the selection.

        Parameters
        ----------
        object_list : list
            List of objects to separate.
        create_group : bool, optional
            Whether to create a group. The default is ``False``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.SeparateBody
        """
        selections = self.convert_to_selections(object_list)
        self.oeditor.SeparateBody(
            ["NAME:Selections", "Selections:=", selections, "NewPartsModelFlag:=", "Model"],
            ["CreateGroupsForNewObjects:=", create_group],
        )
        self.refresh_all_ids()
        return True

    @pyaedt_function_handler()
    def rotate(self, objid, cs_axis, angle=90.0, unit="deg"):
        """Rotate the selection.

        Parameters
        ----------
        objid :  list, str, int, or  :class:`pyaedt.modeler.Object3d.Object3d`
             ID of the object.
        cs_axis
            Coordinate system axis or the Application.CoordinateSystemAxis object.
        angle : float
            Angle of rotation. The units, defined by ``unit``, can be either
            degrees or radians. The default is ``90.0``.
        unit : text, optional
             Units for the angle. Options are ``"deg"`` or ``"rad"``.
             The default is ``"deg"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.Rotate
        """
        selections = self.convert_to_selections(objid)
        vArg1 = ["NAME:Selections", "Selections:=", selections, "NewPartsModelFlag:=", "Model"]
        vArg2 = ["NAME:RotateParameters"]
        vArg2.append("RotateAxis:="), vArg2.append(GeometryOperators.cs_axis_str(cs_axis))
        vArg2.append("RotateAngle:="), vArg2.append(self._arg_with_dim(angle, unit))

        if self.oeditor is not None:
            self.oeditor.Rotate(vArg1, vArg2)

        return True

    @pyaedt_function_handler()
    def subtract(self, blank_list, tool_list, keep_originals=True, **kwargs):
        """Subtract objects.

        Parameters
        ----------
        blank_list : list of Object3d or list of int
            List of objects to subtract from. The list can be of
            either :class:`pyaedt.modeler.Object3d.Object3d` objects or object IDs.
        tool_list : list
            List of objects to subtract. The list can be of
            either Object3d objects or object IDs.
        keep_originals : bool, optional
            Whether to keep the original objects. The default is ``True``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.Subtract
        """
        if "keepOriginals" in kwargs:
            warnings.warn("keepOriginals has been deprecated. use keep_originals.", DeprecationWarning)
            keep_originals = kwargs["keepOriginals"]
        szList = self.convert_to_selections(blank_list)
        szList1 = self.convert_to_selections(tool_list)

        vArg1 = ["NAME:Selections", "Blank Parts:=", szList, "Tool Parts:=", szList1]
        vArg2 = ["NAME:SubtractParameters", "KeepOriginals:=", keep_originals]

        self.oeditor.Subtract(vArg1, vArg2)
        if not keep_originals:
            self.cleanup_objects()

        return True

    @pyaedt_function_handler()
    def imprint(self, blank_list, tool_list, keep_originals=True):
        """Imprin an object list on another object list.

        Parameters
        ----------
        blank_list : list of Object3d or list of int
            List of objects to imprint from. The list can be of
            either :class:`pyaedt.modeler.Object3d.Object3d` objects or object IDs.
        tool_list : list of Object3d or list of int
            List of objects to imprint. The list can be of
            either Object3d objects or object IDs.
        keep_originals : bool, optional
            Whether to keep the original objects. The default is ``True``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.Imprint
        """
        szList = self.convert_to_selections(blank_list)
        szList1 = self.convert_to_selections(tool_list)

        vArg1 = ["NAME:Selections", "Blank Parts:=", szList, "Tool Parts:=", szList1]
        vArg2 = ["NAME:ImprintParameters", "KeepOriginals:=", keep_originals]

        self.oeditor.Imprint(vArg1, vArg2)
        if not keep_originals:
            self.cleanup_objects()
        return True

    @pyaedt_function_handler()
    def _imprint_projection(self, tool_list, keep_originals=True, normal=True, vector_direction=None, distance="1mm"):

        szList1 = self.convert_to_selections(tool_list)

        varg1 = ["NAME:Selections", "Selections:=", szList1]
        varg2 = [
            "NAME:ImprintProjectionParameters",
            "KeepOriginals:=",
            keep_originals,
            "NormalProjection:=",
            normal,
        ]
        if not normal:
            varg2.append("Distance:=")
            varg2.append(self._app.value_with_units(distance))
            varg2.append("DirectionX:=")
            varg2.append(self._app.value_with_units(vector_direction[0]))
            varg2.append("DirectionY:=")
            varg2.append(self._app.value_with_units(vector_direction[1]))
            varg2.append("DirectionZ:=")
            varg2.append(self._app.value_with_units(vector_direction[2]))

        self.oeditor.ImprintProjection(varg1, varg2)
        if not keep_originals:
            self.cleanup_objects()
        return True

    @pyaedt_function_handler
    def imprint_normal_projection(
        self,
        tool_list,
        keep_originals=True,
    ):
        """Imprint the normal projection of objects over a sheet.

        Parameters
        ----------
        tool_list : list
            List of objects to imprint. The list can be of
            either Object3d objects or object IDs.
        keep_originals : bool, optional
            Whether to keep the original objects. The default is ``True``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.ImprintProjection
        """
        return self._imprint_projection(tool_list, keep_originals, True)

    @pyaedt_function_handler
    def imprint_vector_projection(
        self,
        tool_list,
        vector_points,
        distance,
        keep_originals=True,
    ):
        """Imprint the projection of objects over a sheet with a specified vector and distance.

        Parameters
        ----------
        tool_list : list
            List of objects to imprint. The list can be of
            either Object3d objects or object IDs.
        vector_points : list
            List of [x,y,z] vector projection.
        distance : str, int
            Distance of Projection.
        keep_originals : bool, optional
            Whether to keep the original objects. The default is ``True``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.ImprintProjection
        """
        return self._imprint_projection(tool_list, keep_originals, False, vector_points, distance)

    @pyaedt_function_handler()
    def purge_history(self, theList):
        """Purge history objects from object names.

        Parameters
        ----------
        theList : list
            List of object names to purge.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.PurgeHistory
        """
        szList = self.convert_to_selections(theList)

        vArg1 = ["NAME:Selections", "Selections:=", szList, "NewPartsModelFlag:=", "Model"]

        self.oeditor.PurgeHistory(vArg1)
        return True

    @pyaedt_function_handler()
    def get_model_bounding_box(self):
        """Retrieve the model bounding box.


        Returns
        -------
        List
            List of six float values representing the bounding box
            in the form ``[min_x, min_y, min_z, max_x, max_y, max_z]``.

        References
        ----------

        >>> oEditor.GetModelBoundingBox
        """
        bb = list(self.oeditor.GetModelBoundingBox())
        bound = [float(b) for b in bb]
        return bound

    @pyaedt_function_handler()
    def unite(self, theList, purge=False):
        """Unite objects from a list.

        Parameters
        ----------
        theList : list
            List of objects.
        purge : bool, optional
            Purge history after unite.

        Returns
        -------
        str
            The united object that is the first in the list.

        References
        ----------

        >>> oEditor.Unite
        """
        slice = min(100, len(theList))
        num_objects = len(theList)
        remaining = num_objects
        objs_groups = []
        while remaining > 1:
            objs = theList[:slice]
            szSelections = self.convert_to_selections(objs)
            vArg1 = ["NAME:Selections", "Selections:=", szSelections]
            vArg2 = ["NAME:UniteParameters", "KeepOriginals:=", False]
            self.oeditor.Unite(vArg1, vArg2)
            if szSelections.split(",")[0] in self.unclassified_names:
                self.logger.error("Error in uniting objects.")
                self._odesign.Undo()
                self.cleanup_objects()
                return False
            elif purge:
                self.purge_history(objs[0])
            objs_groups.append(objs[0])
            remaining -= slice
            if remaining > 0:
                theList = theList[slice:]
        if remaining > 0:
            objs_groups.extend(theList)
        self.cleanup_objects()
        if len(objs_groups) > 1:
            return self.unite(objs_groups, purge=purge)
        self.logger.info("Union of {} objects has been executed.".format(num_objects))
        return self.convert_to_selections(theList[0], False)

    @pyaedt_function_handler()
    def clone(self, objid):
        """Clone objects from a list of object IDs.

        Parameters
        ----------
        objid : list
            List of object IDs.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        List
            List of names of objects cloned when successful.

        References
        ----------

        >>> oEditor.Copy
        >>> oEditor.Paste
        """

        szSelections = self.convert_to_selections(objid)
        vArg1 = ["NAME:Selections", "Selections:=", szSelections]

        self.oeditor.Copy(vArg1)
        self.oeditor.Paste()
        new_objects = self.add_new_objects()
        return True, new_objects

    @pyaedt_function_handler()
    def intersect(self, theList, keep_originals=False, **kwargs):
        """Intersect objects from a list.

        Parameters
        ----------
        theList : list
            List of objects.
        keep_originals : bool, optional
            Whether to keep the original object. The default is ``False``.

        Returns
        -------
        str
            Retrieve the resulting 3D Object when succeeded.

        References
        ----------

        >>> oEditor.Intersect
        """
        if "keeporiginal" in kwargs:
            warnings.warn("keeporiginal has been deprecated. use keep_originals.", DeprecationWarning)
            keep_originals = kwargs["keeporiginal"]
        unclassified = list(self.oeditor.GetObjectsInGroup("Unclassified"))
        szSelections = self.convert_to_selections(theList)

        vArg1 = ["NAME:Selections", "Selections:=", szSelections]
        vArg2 = ["NAME:IntersectParameters", "KeepOriginals:=", keep_originals]

        self.oeditor.Intersect(vArg1, vArg2)
        unclassified1 = list(self.oeditor.GetObjectsInGroup("Unclassified"))
        if unclassified != unclassified1:
            self._odesign.Undo()
            self.logger.error("Error in intersection. Reverting Operation")
            return
        self.cleanup_objects()
        self.logger.info("Intersection Succeeded")
        return self.convert_to_selections(theList[0], False)

    @pyaedt_function_handler()
    def connect(self, theList):
        """Connect objects from a list.

        Parameters
        ----------
        theList : list
            List of objects.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.Connect
        """
        unclassified_before = list(self.unclassified_names)
        szSelections = self.convert_to_selections(theList)

        vArg1 = ["NAME:Selections", "Selections:=", szSelections]

        self.oeditor.Connect(vArg1)
        if unclassified_before != self.unclassified_names:
            self._odesign.Undo()
            self.logger.error("Error in connection. Reverting Operation")
            return False

        self.cleanup_objects()
        self.logger.info("Connection Correctly created")
        return True

    @pyaedt_function_handler()
    def translate(self, objid, vector):
        """Translate objects from a list.

        .. deprecated:: 0.4.0
           Use :func:`move` instead.

        Parameters
        ----------
        objid : list, Position object
            List of object IDs.
        vector : list
            Vector of the direction move. It can be a list of the ``[x, y, z]``
            coordinates or a Position object.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.Move
        """
        warnings.warn("`translate` is deprecated. Use `move` instead.", DeprecationWarning)
        Xvec, Yvec, Zvec = self._pos_with_arg(vector)
        szSelections = self.convert_to_selections(objid)

        vArg1 = ["NAME:Selections", "Selections:=", szSelections, "NewPartsModelFlag:=", "Model"]
        vArg2 = ["NAME:TranslateParameters"]
        vArg2.append("TranslateVectorX:="), vArg2.append(Xvec)
        vArg2.append("TranslateVectorY:="), vArg2.append(Yvec)
        vArg2.append("TranslateVectorZ:="), vArg2.append(Zvec)

        if self.oeditor is not None:
            self.oeditor.Move(vArg1, vArg2)
        return True

    @pyaedt_function_handler()
    def chassis_subtraction(self, chassis_part):
        """Subtract all non-vacuum objects from the main chassis object.

        Parameters
        ----------
        chassis_part : str
            Name of the main chassis object.

        References
        ----------

        >>> oEditor.Subtract
        """
        self.logger.info("Subtract all objects from Chassis object - exclude vacuum objs")
        mat_names = self._omaterial_manager.GetNames()
        num_obj_start = self.oeditor.GetNumObjects()
        blank_part = chassis_part
        # in main code this object will need to be determined automatically eg by name such as chassis or sheer size
        self.logger.info("Blank Part in Subtraction = " + str(blank_part))
        """
        check if blank part exists, if not, skip subtraction
        """
        tool_parts = list(self.oeditor.GetObjectsInGroup("Solids"))
        tool_parts.remove(blank_part)
        for mat in mat_names:
            if str(mat).lower() == "vacuum":
                objnames = self.oeditor.GetObjectsByMaterial(mat)
                for obj in objnames:
                    tool_parts.remove(obj)
                # tool_parts_final=list(set(tool_parts).difference(set(objnames)))
        tool_parts = ",".join(tool_parts)
        num_obj_end = self.oeditor.GetNumObjects()
        self.subtract(blank_part, tool_parts, True)

        self.logger.info("Subtraction Objs - Initial: " + str(num_obj_start) + "  ,  Final: " + str(num_obj_end))

    @pyaedt_function_handler()
    def _offset_on_plane(self, i, offset):
        """Offset the object on a plane.

        Parameters
        ----------
        i :

        offset :
            Offset to apply.

        Returns
        -------
        tuple
           Position of object after offset is applied.

        """
        if i > 7:
            off1 = 0
        elif i % 4 == 0 or i % 4 == 1:
            off1 = offset
        else:
            off1 = -offset
        if 3 < i < 8:
            off2 = 0
        elif i % 2 == 0:
            off2 = offset
        else:
            off2 = -offset
        if i < 4:
            off3 = 0
        elif i != 4 and i != 7 and i != 8 and i != 11:
            off3 = -offset
        else:
            off3 = +offset
        return off1, off2, off3

    @pyaedt_function_handler()
    def check_plane(self, obj, faceposition, offset=1):
        """Check for the plane that is defined as the face for an object.

        Parameters
        ----------
        obj : str
            Name of the object.
        faceposition : list
            List of the ``[x, y, z]`` coordinates for the position of the face.
        offset : optional
            Offset to apply. The default is ``1``.

        Returns
        -------
        str
            Name of the plane. It can be "XY", "XZ" or "YZ".

        """

        Xvec, Yvec, Zvec = self._pos_with_arg(faceposition)

        if isinstance(obj, int):
            obj = self.objects[obj].name
        plane = None
        found = False
        i = 0
        while not found:
            off1, off2, off3 = self._offset_on_plane(i, offset)
            vArg1 = ["NAME:FaceParameters"]
            vArg1.append("BodyName:="), vArg1.append(obj)
            vArg1.append("XPosition:="), vArg1.append(Xvec + "+" + self._arg_with_dim(off1))
            vArg1.append("YPosition:="), vArg1.append(Yvec + "+" + self._arg_with_dim(off2))
            vArg1.append("ZPosition:="), vArg1.append(Zvec + "+" + self._arg_with_dim(off3))
            try:
                face_id = self.oeditor.GetFaceByPosition(vArg1)
                if i < 4:
                    plane = "XY"
                elif i < 8:
                    plane = "XZ"
                else:
                    plane = "YZ"
                found = True
            except:
                i = i + 1
                if i > 11:
                    found = True

        return plane

    @pyaedt_function_handler()
    def get_matched_object_name(self, search_string):
        """Retrieve the name of the matched object.

        Parameters
        ----------
        search_string : str
            Text string to search for.


        Returns
        -------
        str
            Name of the matched object.

        References
        ----------

        >>> oEditor.GetMatchedObjectName
        """
        return self.oeditor.GetMatchedObjectName(search_string)

    @pyaedt_function_handler()
    def clean_objects_name(self, main_part_name):
        """Clean the names of the objects for a main part.

        Parameters
        ----------
        main_part_name : str
            Name of the main part.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.RenamePart
        """
        # import os.path
        # (CADPath, CADFilename) = os.path.split(CADFile)
        # (CADName, CADExt) = os.path.splitext(CADFilename)
        CADSuffix = main_part_name + "_"
        objNames = self.oeditor.GetMatchedObjectName(CADSuffix + "*")
        for name in objNames:
            RenameArgs = {}
            RenameArgs["NAME"] = "Rename Data"
            RenameArgs["Old Name"] = name
            RenameArgs["New Name"] = name.replace(CADSuffix, "")
            self.oeditor.RenamePart(RenameArgs)
        return True

    @pyaedt_function_handler()
    def create_airbox(self, offset=0, offset_type="Absolute", defname="AirBox_Auto"):
        """Create an airbox that is as big as the bounding extension of the project.

        Parameters
        ----------
        offset :
            Double offset value to apply on the airbox faces versus the bounding box.
            The default is ``0``.
        offset_type : str
            Type of the offset. Options are ``"Absolute"`` and ``"Relative"``.
            The default is ``"Absolute"``. If ``"Relative"``, the offset input
            is between 0 and 100.
        defname : str, optional
            Name of the airbox. The default is ``"AirBox_Auto"``.

        Returns
        -------
        int
            ID of the airbox created.

        References
        ----------

        >>> oEditor.CreateBox
        """
        self.logger.info("Adding Airbox to the Bounding ")

        bound = self.get_model_bounding_box()
        if offset_type == "Absolute":
            offset1 = offset2 = offset3 = offset
        else:
            offset1 = (bound[3] - bound[0]) * offset / 100
            offset2 = (bound[4] - bound[1]) * offset / 100
            offset3 = (bound[5] - bound[2]) * offset / 100
        startpos = self.Position(bound[0] - offset1, bound[1] - offset2, bound[2] - offset3)

        dim = []
        dim.append(bound[3] - bound[0] + 2 * offset1)
        dim.append(bound[4] - bound[1] + 2 * offset2)
        dim.append(bound[5] - bound[2] + 2 * offset3)
        airid = self.create_box(startpos, dim, defname)
        return airid

    @pyaedt_function_handler()
    def create_air_region(self, x_pos=0, y_pos=0, z_pos=0, x_neg=0, y_neg=0, z_neg=0, is_percentage=True):
        """Create an air region.

        Parameters
        ----------
        x_pos : float or str, optional
            If float, padding in the +X direction in modeler units.
            If str, padding with units in the +X direction.
            The default is ``0``.
        y_pos : float or str, optional
            If float, padding in the +Y direction in modeler units.
            If str, padding with units in the +Y direction.
            The default is ``0``.
        z_pos : float or str, optional
            If float, padding in the +Z direction in modeler units.
            If str, padding with units in the +Z direction.
            The default is ``0``.
        x_neg : float or str, optional
            If float, padding in the -X direction in modeler units.
            If str, padding with units in the -X direction.
            The default is ``0``.
        y_neg : float or str, optional
            If float, padding in the -Y direction in modeler units.
            If str, padding with units in the -Y direction.
            The default is ``0``.
        z_neg : float or str, optional
            If float, padding in the -Z direction in modeler units.
            If str, padding with units in the -Z direction.
            The default is ``0``.
        is_percentage : bool, optional
            Region definition in percentage or absolute value. The default is `True``.

        Returns
        -------
        :class:`pyaedt.modeler.object3d.Object3d`
            3D object.

        References
        ----------

        >>> oEditor.CreateRegion
        """
        return self.create_region([x_pos, y_pos, z_pos, x_neg, y_neg, z_neg], is_percentage)

    @pyaedt_function_handler()
    def edit_region_dimensions(self, listvalues):
        """Modify the dimensions of the region.

        Parameters
        ----------
        listvalues : list
            List of the padding percentages along all six directions in
            the form ``[+X, -X, +Y, -Y, +Z, -Z]``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.ChangeProperty
        """
        arg = ["NAME:AllTabs"]
        arg2 = ["NAME:Geometry3DCmdTab", ["NAME:PropServers", "Region:CreateRegion:1"]]
        arg3 = ["NAME:ChangedProps"]
        p = ["+X", "-X", "+Y", "-Y", "+Z", "-Z"]
        for label, value in zip(p, listvalues):
            padding = []
            padding.append("NAME:" + label + " Padding Data")
            padding.append("Value:=")
            padding.append(str(value))
            arg3.append(padding)
        arg2.append(arg3)
        arg.append(arg2)
        self.oeditor.ChangeProperty(arg)
        return True

    @pyaedt_function_handler()
    def create_face_list(self, face_list, name=None):
        """Create a list of faces given a list of face ID or a list of objects.

        Parameters
        ----------
        face_list : list
            List of face ID or list of objects

        name : str, optional
           Name of the new list.

        Returns
        -------
        :class:`pyaedt.modeler.Modeler.Lists`
            List object when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.CreateEntityList
        """
        if name:
            for i in self.user_lists:
                if i.name == name:
                    self.logger.warning("A List with the specified name already exists!")
                    return i
        face_list = self.convert_to_selections(face_list, True)
        user_list = Lists(self)
        list_type = "Face"
        if user_list:
            result = user_list.create(
                object_list=face_list,
                name=name,
                type=list_type,
            )
            if result:
                return user_list
            else:
                self._app.logger.error("Wrong object definition. Review object list and type")
                return False
        else:
            self._app.logger.error("User list object could not be created")
            return False

    @pyaedt_function_handler()
    def create_object_list(self, object_list, name=None):
        """Create an object list given a list of object names.

        Parameters
        ----------
        object_list : list
            List of object names.
        name : str, optional
            Name of the new object list.

        Returns
        -------
        :class:`pyaedt.modeler.Modeler.Lists`
            List object when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.CreateEntityList
        """
        if name:
            for i in self.user_lists:
                if i.name == name:
                    self.logger.warning("A List with the specified name already exists!")
                    return i
        object_list = self.convert_to_selections(object_list, True)
        user_list = Lists(self)
        list_type = "Object"
        if user_list:
            result = user_list.create(
                object_list=object_list,
                name=name,
                type=list_type,
            )
            if result:
                return user_list
            else:
                self._app.logger.error("Wrong object definition. Review object list and type")
                return False
        else:
            self._app.logger.error("User list object could not be created")
            return False

    @pyaedt_function_handler()
    def generate_object_history(self, objectname):
        """Generate history for the object.

        Parameters
        ----------
        objectname : str
            Name of the history object.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.GenerateHistory
        """
        objectname = self.convert_to_selections(objectname)
        self.oeditor.GenerateHistory(
            ["NAME:Selections", "Selections:=", objectname, "NewPartsModelFlag:=", "Model", "UseCurrentCS:=", True]
        )
        self.cleanup_objects()
        return True

    @pyaedt_function_handler()
    def create_faceted_bondwire_from_true_surface(self, bondname, bond_direction, min_size=0.2, numberofsegments=8):
        """Create a faceted bondwire from an existing true surface bondwire.

        Parameters
        ----------
        bondname : str
            Name of the bondwire to replace.
        bond_direction : list
            List of the ``[x, y, z]`` coordinates for the axis direction
            of the bondwire. For example, ``[0, 1, 2]``.
        min_size : float
            Minimum size of the subsegment of the new polyline. The default is ``0.2``.
        numberofsegments : int, optional
            Number of segments. The default is ``8``.

        Returns
        -------
        str
            Name of the bondwire created.
        """
        old_bondwire = self.get_object_from_name(bondname)
        if not old_bondwire:
            return False
        edges = old_bondwire.edges
        faces = old_bondwire.faces
        centers = []
        for el in faces:
            center = el.center
            if center:
                centers.append(center)
        edgelist = []
        verlist = []
        for el in edges:
            ver = el.vertices
            if len(ver) < 2:
                continue
            p1 = ver[0].position
            p2 = ver[1].position
            p3 = [abs(i - j) for i, j in zip(p1, p2)]

            dir = p3.index(max(p3))
            if dir == bond_direction:
                edgelist.append(el)
                verlist.append([p1, p2])
        if not edgelist:
            self.logger.error("No edges found specified direction. Check again")
            return False
        connected = [edgelist[0]]
        tol = 1e-6
        for edge in edgelist[1:]:
            ver = edge.vertices
            p1 = ver[0].position
            p2 = ver[1].position
            for el in connected:
                ver1 = el.vertices
                p3 = ver1[0].position
                p4 = ver1[1].position
                dist = GeometryOperators.points_distance(p1, p3)
                if dist < tol:
                    connected.append(edge)
                    break
                dist = GeometryOperators.points_distance(p1, p4)
                if dist < tol:
                    connected.append(edge)
                    break
                dist = GeometryOperators.points_distance(p2, p3)
                if dist < tol:
                    connected.append(edge)
                    break
                dist = GeometryOperators.points_distance(p2, p4)
                if dist < tol:
                    connected.append(edge)
                    break
        new_edges = []
        for edge in connected:
            edge_object = self.create_object_from_edge(edge)
            new_edges.append(edge_object)

        self.unite(new_edges)
        self.generate_object_history(new_edges[0])
        self.convert_segments_to_line(new_edges[0].name)

        edges = new_edges[0].edges
        i = 0
        edge_to_delete = []
        first_vert = None
        for edge in edges:
            ver = edge.vertices
            p1 = ver[0].position
            p2 = ver[1].position
            if not first_vert:
                first_vert = p1
            dist = GeometryOperators.points_distance(p1, p2)
            if dist < min_size:
                edge_to_delete.append(i)
            i += 1

        rad = 1e6
        move_vector = None
        for fc in centers:
            dist = GeometryOperators.points_distance(fc, first_vert)
            if dist < rad:
                rad = dist
                move_vector = GeometryOperators.v_sub(fc, first_vert)

        P = self.get_existing_polyline(object=new_edges[0])

        if edge_to_delete:
            P.remove_edges(edge_to_delete)

        angle = math.pi * (180 - 360 / numberofsegments) / 360

        status = P.set_crosssection_properties(
            type="Circle", num_seg=numberofsegments, width=(rad * (2 - math.sin(angle))) * 2
        )
        if status:
            self.move(new_edges[0], move_vector)
            old_bondwire.model = False
            return new_edges[0]
        else:
            return False

    @pyaedt_function_handler()
    def get_entitylist_id(self, name):
        """Retrieve the ID of an entity list.

        Parameters
        ----------
        name : str
            Name of the entity list.

        Returns
        -------
        int
            ID of the entity list.

        References
        ----------

        >>> oEditor.GetEntityListIDByName
        """
        id = self.oeditor.GetEntityListIDByName(name)
        return id

    @pyaedt_function_handler()
    def create_outer_facelist(self, externalobjects, name="outer_faces"):
        """Create a face list from a list of outer objects.

        Parameters
        ----------
        externalobjects : list
            List of outer objects.
        name : str, optional
            Name of the new list. The default is ``"outer_faces"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        list2 = self.select_allfaces_fromobjects(externalobjects)  # find ALL faces of outer objects
        self.create_face_list(list2, name)
        self.logger.info("Extfaces of thermal model = " + str(len(list2)))
        return True

    @pyaedt_function_handler()
    def explicitly_subtract(self, diellist, metallist):
        """Explicitly subtract all elements in a SolveInside list and a SolveSurface list.

        Parameters
        ----------
        diellist : list
            List of dielectrics.
        metallist : list
            List of metals.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.Subtract
        >>> oEditor.PurgeHistory
        """
        self.logger.info("Creating explicit subtraction between objects.")
        for el in diellist:
            list1 = el
            list2 = ""
            for el1 in metallist:
                list2 = list2 + el1 + ","
            for el1 in diellist:
                if el1 is not el:
                    list2 = list2 + el1 + ","
            if list2:
                list2 = list2[:-1]
                self.subtract(list1, list2, True)
                self.purge_history(list1)
                self.purge_history(list2)
        for el in metallist:
            list1 = el
            list2 = ""
            for el1 in metallist:
                if el1 is not el:
                    list2 = list2 + el1 + ","
            if list2:
                list2 = list2[:-1]
                self.subtract(list1, list2, True)
                self.purge_history(list1)
                self.purge_history(list2)
        self.logger.info("Explicit subtraction is completed.")
        return True

    @pyaedt_function_handler()
    def find_port_faces(self, port_sheets):
        """Find the vaccums given a list of input sheets.

        Starting from a list of input sheets, this method creates a list of output sheets
        that represent the blank parts (vacuums) and the tool parts of all the intersections
        of solids on the sheets. After a vacuum on a sheet is found, a port can be
        created on it.

        Parameters
        ----------
        port_sheets : list
            List of input sheets names.

        Returns
        -------
        List
            List of output sheets (`2x len(port_sheets)`).

        """
        faces = []
        solids = [s for s in self.solid_objects if s.material_name not in ["vacuum", "air"] and s.model]
        for sheet_name in port_sheets:
            sheet = self[sheet_name]  # get the sheet object
            _, cloned = self.clone(sheet)
            cloned = self[cloned[0]]
            cloned.subtract(solids)
            sheet.subtract(cloned)
            cloned.name = sheet.name + "_Face1Vacuum"
            faces.append(sheet.name)
            faces.append(cloned.name)
        return faces

    @pyaedt_function_handler()
    def load_objects_bytype(self, obj_type):
        """Load all objects of a specified type.

        .. deprecated:: 0.5.0
           Use :func:`get_objects_in_group` property instead.

        Parameters
        ----------
        obj_type : str
            Type of the objects to load. Options are
            ``"Solids"`` and ``"Sheets"``.

        Returns
        -------
        list
            List of the object names for the specified type.

        References
        ----------

        >>> oEditor.GetObjectsInGroup
        """

        warnings.warn(
            "`load_objects_bytype` is deprecated and will be removed in version 0.5.0. "
            "Use `get_objects_in_group` method instead.",
            DeprecationWarning,
        )

        objNames = list(self.oeditor.GetObjectsInGroup(obj_type))
        return objNames

    @pyaedt_function_handler()
    def get_line_ids(self):
        """Create a dictionary of object IDs for the lines in the design with the line name as the key."""
        line_ids = {}
        line_list = list(self.oeditor.GetObjectsInGroup("Lines"))
        for line_object in line_list:
            # TODO Problem with GetObjectIDByName
            try:
                line_ids[line_object] = str(self.oeditor.GetObjectIDByName(line_object))
            except:
                self.logger.warning("Line {} has an invalid ID!".format(line_object))
        return line_ids

    @pyaedt_function_handler()
    def get_bounding_dimension(self):
        """Retrieve the dimension array of the bounding box.

        Returns
        -------
        list
            List of three float values representing the bounding box dimensions
            in the form ``[dim_x, dim_y, dim_z]``.

        References
        ----------

        >>> oEditor.GetModelBoundingBox
        """
        oBoundingBox = list(self.oeditor.GetModelBoundingBox())
        dimensions = []
        dimensions.append(abs(float(oBoundingBox[0]) - float(oBoundingBox[3])))
        dimensions.append(abs(float(oBoundingBox[1]) - float(oBoundingBox[4])))
        dimensions.append(abs(float(oBoundingBox[2]) - float(oBoundingBox[5])))
        return dimensions

    @pyaedt_function_handler()
    def get_object_name_from_edge_id(self, edge_id):
        """Retrieve the object name for a predefined edge ID.

        Parameters
        ----------
        edge_id : int
            ID of the edge.

        Returns
        -------
        str
            Name of the edge if it exists, ``False`` otherwise.

        References
        ----------

        >>> oEditor.GetEdgeIDsFromObject
        """
        for object in list(self.object_id_dict.keys()):
            try:
                oEdgeIDs = self.oeditor.GetEdgeIDsFromObject(object)
                if str(edge_id) in oEdgeIDs:
                    return object
            except:
                return False
        return False

    @pyaedt_function_handler()
    def get_solving_volume(self):
        """Generate a mesh for a setup.

        Returns
        -------
        int
            ``1`` when successful, ``0`` when failed.

        References
        ----------

        >>> oEditor.GetModelBoundingBox
        """
        bound = self.get_model_bounding_box()
        volume = abs(bound[3] - bound[0]) * abs(bound[4] - bound[1]) * abs(bound[5] - bound[2])
        volume = str(round(volume, 0))
        return volume

    @pyaedt_function_handler()
    def vertex_data_of_lines(self, txtfilter=None):
        """Generate a dictionary of line vertex data for all lines contained within the design.

        Parameters
        ----------
        txtfilter : str, optional
            Text string for filtering. The default is ``None``. When a text string is specified,
            line data is generated only if this text string is contained within the line name.

        Returns
        -------
        dict
            Dictionary of the line name with a list of vertex positions in either 2D or 3D.

        """
        line_data = {}
        lines = self.get_line_ids()
        if txtfilter is not None:
            lines = [n for n in lines if txtfilter in n]
        for x in lines:
            line_data[x] = self.get_vertices_of_line(x)

        return line_data

    @pyaedt_function_handler()
    def get_vertices_of_line(self, sLineName):
        """Generate a list of vertex positions for a line object from AEDT in model units.

        Parameters
        ----------
        sLineName : str
            Name of the line object in AEDT.

        Returns
        -------
        list
            List of the ``[x, y, (z)]`` coordinates for the 2D or 3D line object.

        References
        ----------

        >>> oEditor.GetVertexIDsFromObject
        """
        position_list = []

        # Get all vertices in the line
        vertices_on_line = self.oeditor.GetVertexIDsFromObject(sLineName)

        if settings.aedt_version > "2022.2":
            vertices_on_line = vertices_on_line[::-1]

        for x in vertices_on_line:
            pos = self.oeditor.GetVertexPosition(x)
            if self.design_type == "Maxwell 2D":
                if self.geometry_mode == "XY":
                    position_list.append([float(pos[0]), float(pos[1])])
                else:
                    position_list.append([float(pos[0]), float(pos[2])])
            else:
                position_list.append([float(pos[0]), float(pos[1]), float(pos[2])])

        return position_list

    @pyaedt_function_handler()
    def import_3d_cad(
        self,
        filename,
        healing=False,
        refresh_all_ids=True,
        import_materials=False,
        create_lightweigth_part=False,
    ):
        """Import a CAD model.

        Parameters
        ----------
        filename : str
            Full path and name of the CAD file.
        healing : bool, optional
            Whether to perform healing. The default is ``False``, in which
            case healing is not performed.
        healing : int, optional
            Whether to perform healing. The default is ``0``, in which
            case healing is not performed.
        refresh_all_ids : bool, optional
            Whether to refresh all IDs after the CAD file is loaded. The
            default is ``True``. Refreshing IDs can take a lot of time in
            a big project.
        import_materials : bool optional
            Either to import material names from the file or not if presents.
        create_lightweigth_part : bool ,optional
            Either to import lightweight or not.

        Returns
        -------
         bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.Import
        """

        if str(healing) in ["0", "1"]:
            warnings.warn(
                "Assigning `0` or `1` to `healing` option is deprecated. Assign `True` or `False` instead.",
                DeprecationWarning,
            )
        vArg1 = ["NAME:NativeBodyParameters"]
        vArg1.append("HealOption:="), vArg1.append(int(healing))
        vArg1.append("Options:="), vArg1.append("-1")
        vArg1.append("FileType:="), vArg1.append("UnRecognized")
        vArg1.append("MaxStitchTol:="), vArg1.append(-1)
        vArg1.append("ImportFreeSurfaces:="), vArg1.append(False)
        vArg1.append("GroupByAssembly:="), vArg1.append(False)
        vArg1.append("CreateGroup:="), vArg1.append(True)
        vArg1.append("STLFileUnit:="), vArg1.append("Auto")
        vArg1.append("MergeFacesAngle:="), vArg1.append(-1)
        vArg1.append("PointCoincidenceTol:="), vArg1.append(1e-06)
        vArg1.append("CreateLightweightPart:="), vArg1.append(create_lightweigth_part)
        vArg1.append("ImportMaterialNames:="), vArg1.append(import_materials)
        vArg1.append("SeparateDisjointLumps:="), vArg1.append(False)
        vArg1.append("SourceFile:="), vArg1.append(filename)
        self.oeditor.Import(vArg1)
        if refresh_all_ids:
            self.refresh_all_ids()
        self.logger.info("Step file {} imported".format(filename))
        return True

    @pyaedt_function_handler()
    def import_spaceclaim_document(self, SCFile):
        """Import a SpaceClaim document.

        Parameters
        ----------
        SCFile :
            Full path and name of the SpaceClaim file.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.CreateUserDefinedModel
        """
        environlist = os.environ
        latestversion = ""
        for l in environlist:
            if "AWP_ROOT" in l:
                if l > latestversion:
                    latestversion = l
        if not latestversion:
            self.logger.error("SpaceClaim is not found.")
        else:
            scdm_path = os.path.join(os.environ[latestversion], "scdm")
        self.oeditor.CreateUserDefinedModel(
            [
                "NAME:UserDefinedModelParameters",
                [
                    "NAME:Definition",
                    [
                        "NAME:UDMParam",
                        "Name:=",
                        "GeometryFilePath",
                        "Value:=",
                        '"' + SCFile + '"',
                        "DataType:=",
                        "String",
                        "PropType2:=",
                        0,
                        "PropFlag2:=",
                        1,
                    ],
                    [
                        "NAME:UDMParam",
                        "Name:=",
                        "IsSpaceClaimLinkUDM",
                        "Value:=",
                        "1",
                        "DataType:=",
                        "Int",
                        "PropType2:=",
                        5,
                        "PropFlag2:=",
                        8,
                    ],
                ],
                [
                    "NAME:Options",
                    [
                        "NAME:UDMParam",
                        "Name:=",
                        "Solid Bodies",
                        "Value:=",
                        "1",
                        "DataType:=",
                        "Int",
                        "PropType2:=",
                        5,
                        "PropFlag2:=",
                        0,
                    ],
                    [
                        "NAME:UDMParam",
                        "Name:=",
                        "Surface Bodies",
                        "Value:=",
                        "1",
                        "DataType:=",
                        "Int",
                        "PropType2:=",
                        5,
                        "PropFlag2:=",
                        0,
                    ],
                    [
                        "NAME:UDMParam",
                        "Name:=",
                        "Parameters",
                        "Value:=",
                        "1",
                        "DataType:=",
                        "Int",
                        "PropType2:=",
                        5,
                        "PropFlag2:=",
                        0,
                    ],
                    [
                        "NAME:UDMParam",
                        "Name:=",
                        "Parameter Key",
                        "Value:=",
                        '""',
                        "DataType:=",
                        "String",
                        "PropType2:=",
                        0,
                        "PropFlag2:=",
                        0,
                    ],
                    [
                        "NAME:UDMParam",
                        "Name:=",
                        "Named Selections",
                        "Value:=",
                        "1",
                        "DataType:=",
                        "Int",
                        "PropType2:=",
                        5,
                        "PropFlag2:=",
                        8,
                    ],
                    [
                        "NAME:UDMParam",
                        "Name:=",
                        "Rendering Attributes",
                        "Value:=",
                        "1",
                        "DataType:=",
                        "Int",
                        "PropType2:=",
                        5,
                        "PropFlag2:=",
                        0,
                    ],
                    [
                        "NAME:UDMParam",
                        "Name:=",
                        "Material Assignment",
                        "Value:=",
                        "1",
                        "DataType:=",
                        "Int",
                        "PropType2:=",
                        5,
                        "PropFlag2:=",
                        0,
                    ],
                    [
                        "NAME:UDMParam",
                        "Name:=",
                        "Import suppressed for physics objects",
                        "Value:=",
                        "0",
                        "DataType:=",
                        "Int",
                        "PropType2:=",
                        5,
                        "PropFlag2:=",
                        0,
                    ],
                    [
                        "NAME:UDMParam",
                        "Name:=",
                        "Explode Multi-Body Parts",
                        "Value:=",
                        "1",
                        "DataType:=",
                        "Int",
                        "PropType2:=",
                        5,
                        "PropFlag2:=",
                        8,
                    ],
                    [
                        "NAME:UDMParam",
                        "Name:=",
                        "SpaceClaim Installation Path",
                        "Value:=",
                        '"' + scdm_path + '"',
                        "DataType:=",
                        "String",
                        "PropType2:=",
                        0,
                        "PropFlag2:=",
                        8,
                    ],
                    [
                        "NAME:UDMParam",
                        "Name:=",
                        "Smart CAD Update",
                        "Value:=",
                        "1",
                        "DataType:=",
                        "Int",
                        "PropType2:=",
                        5,
                        "PropFlag2:=",
                        8,
                    ],
                ],
                ["NAME:GeometryParams"],
                "DllName:=",
                "SCIntegUDM",
                "Library:=",
                "installLib",
                "Version:=",
                "2.0",
                "ConnectionID:=",
                "",
            ]
        )
        self.refresh_all_ids()
        return True

    @pyaedt_function_handler()
    def modeler_variable(self, value):
        """Modeler variable.

        Parameters
        ----------
        value :


        Returns
        -------

        """
        if isinstance(value, str):
            return value
        else:
            return str(value) + self.model_units

    @pyaedt_function_handler()
    def break_spaceclaim_connection(self):
        """Break the connection with SpaceClaim.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.BreakUDMConnection
        """
        args = ["NAME:Selections", "Selections:=", "SpaceClaim1"]
        self.oeditor.BreakUDMConnection(args)
        return True

    @pyaedt_function_handler()
    def load_scdm_in_hfss(self, SpaceClaimFile):
        """Load a SpaceClaim file in HFSS.

        Parameters
        ----------
        SpaceClaimFile : str
            Full path and name of the SpaceClaim file.


        Returns
        -------
         bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.CreateUserDefinedModel
        >>> oEditor.BreakUDMConnection
        """
        self.import_spaceclaim_document(SpaceClaimFile)
        self.break_spaceclaim_connection()
        return True

    @pyaedt_function_handler()
    def load_hfss(self, cadfile):
        """Load HFSS.

        .. deprecated:: 0.4.41
           Use :func:`import_3d_cad` property instead.

        Parameters
        ----------
        cadfile : str
            Name of the CAD file to load in HFSS.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.Import
        """
        warnings.warn("`load_hfss` is deprecated. Use `import_3d_cad` method instead.", DeprecationWarning)
        self.import_3d_cad(cadfile, healing=True)
        return True

    @pyaedt_function_handler()
    def get_faces_from_materials(self, mats):
        """Select all outer faces given a list of materials.

        Parameters
        ----------
        mats : list
            List of materials to include in the search for outer
            faces.

        Returns
        -------
        list
            List of all outer faces of the specified materials.

        References
        ----------

        >>> oEditor.GetObjectsByMaterial
        >>> oEditor.GetFaceIDs
        """
        self.logger.info("Selecting outer faces.")

        sel = []
        if type(mats) is str:
            mats = [mats]
        for mat in mats:
            objs = list(self.oeditor.GetObjectsByMaterial(mat))
            objs.extend(list(self.oeditor.GetObjectsByMaterial(mat.lower())))

            for i in objs:

                oFaceIDs = self.oeditor.GetFaceIDs(i)

                for face in oFaceIDs:
                    sel.append(int(face))
        return sel

    @pyaedt_function_handler()
    def scale(self, obj_list, x=2.0, y=2.0, z=2.0):
        """Scale a list of objects.

        Parameters
        ----------
        obj_list : list
            List of objects IDs or names.
        x : float, optional
            Scale factor for X.
        y : float, optional
            Scale factor for Y.
        z : float, optional
            Scale factor for Z.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.Scale
        """
        selections = self.convert_to_selections(obj_list, True)
        arg1 = ["NAME:Selections", "Selections:=", ", ".join(selections), "NewPartsModelFlag:=", "Model"]
        arg2 = ["NAME:ScaleParameters", "ScaleX:=", str(x), "ScaleY:=", str(y), "ScaleZ:=", str(z)]
        self.oeditor.Scale(arg1, arg2)
        return True

    @pyaedt_function_handler()
    def select_allfaces_fromobjects(self, elements):
        """Select all outer faces given a list of objects.

        Parameters
        ----------
        elements : list
            List of objects to include in the search for outer faces.

        Returns
        -------
        List
            List of outer faces in the given list of objects.

        References
        ----------

        >>> oEditor.GetFaceIDs
        """
        self.logger.info("Selecting outer faces.")

        sel = []

        for i in elements:

            oFaceIDs = self.oeditor.GetFaceIDs(i)

            for face in oFaceIDs:
                sel.append(int(face))
        return sel

    @pyaedt_function_handler()
    def setunassigned_mats(self):
        """Find unassagned objects and set them to non-model.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.SetPropertyValue
        """
        oObjects = list(self.oeditor.GetObjectsInGroup("Solids"))
        for obj in oObjects:
            pro = self.oeditor.GetPropertyValue("Geometry3DAttributeTab", obj, "Material")
            if pro == '""':
                self.oeditor.SetPropertyValue("Geometry3DAttributeTab", obj, "Model", False)
        return True

    @pyaedt_function_handler()
    def automatic_thicken_sheets(self, inputlist, value, internalExtr=True, internalvalue=1):
        """Create thickened sheets for a list of input faces.

        This method automatically checks the direction in which to thicken the sheets.

        Parameters
        ----------
        inputlist : list
            List of faces.
        value : float
            Value in millimeters to thicken the sheets.
        internalExtr : bool, optional
            Whether to extrude sheets internally. The default is ``True``.
        internalvalue : float, optional
            Value in millimeters to thicken the sheets internally (vgoing into the model).
            The default is ``1``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.ThickenSheet
        """
        aedt_bounding_box = self.get_model_bounding_box()
        directions = {}
        inputlist = self.convert_to_selections(inputlist, True)
        for el in inputlist:
            objID = self.oeditor.GetFaceIDs(el)
            faceCenter = self.oeditor.GetFaceCenter(int(objID[0]))
            directionfound = False
            l = 10
            while not directionfound:
                self.oeditor.ThickenSheet(
                    ["NAME:Selections", "Selections:=", el, "NewPartsModelFlag:=", "Model"],
                    ["NAME:SheetThickenParameters", "Thickness:=", str(l) + "mm", "BothSides:=", False],
                )
                aedt_bounding_box2 = self.get_model_bounding_box()
                self._odesign.Undo()
                if aedt_bounding_box != aedt_bounding_box2:
                    directions[el] = "External"
                    directionfound = True
                self.oeditor.ThickenSheet(
                    ["NAME:Selections", "Selections:=", el, "NewPartsModelFlag:=", "Model"],
                    ["NAME:SheetThickenParameters", "Thickness:=", "-" + str(l) + "mm", "BothSides:=", False],
                )
                aedt_bounding_box2 = self.get_model_bounding_box()

                self._odesign.Undo()

                if aedt_bounding_box != aedt_bounding_box2:
                    directions[el] = "Internal"
                    directionfound = True
                else:
                    l = l + 10
        for el in inputlist:
            objID = self.oeditor.GetFaceIDs(el)
            faceCenter = self.oeditor.GetFaceCenter(int(objID[0]))
            if directions[el] == "Internal":
                self.oeditor.ThickenSheet(
                    ["NAME:Selections", "Selections:=", el, "NewPartsModelFlag:=", "Model"],
                    ["NAME:SheetThickenParameters", "Thickness:=", "-" + str(value) + "mm", "BothSides:=", False],
                )
            else:
                self.oeditor.ThickenSheet(
                    ["NAME:Selections", "Selections:=", el, "NewPartsModelFlag:=", "Model"],
                    ["NAME:SheetThickenParameters", "Thickness:=", str(value) + "mm", "BothSides:=", False],
                )
            if internalExtr:
                objID2 = self.oeditor.GetFaceIDs(el)
                for fid in objID2:
                    try:
                        faceCenter2 = self.oeditor.GetFaceCenter(int(fid))
                        if faceCenter2 == faceCenter:
                            self.oeditor.MoveFaces(
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
        return True

    @pyaedt_function_handler()
    def move_face(self, faces, offset=1.0):
        """Move an input face or a list of input faces of a specific object.

        This method moves a face or a list of faces which belong to the same solid.

        Parameters
        ----------
        faces : list
            List of Face ID or List of :class:`pyaedt.modeler.Object3d.FacePrimitive` object or mixed.
        offset : float, optional
             Offset to apply in model units. The default is ``1.0``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.MoveFaces

        """

        face_selection = self.convert_to_selections(faces, True)
        selection = {}
        for f in face_selection:
            if self.oeditor.GetObjectNameByFaceID(f) in selection:
                selection[self.oeditor.GetObjectNameByFaceID(f)].append(f)
            else:
                selection[self.oeditor.GetObjectNameByFaceID(f)] = [f]

        arg1 = [
            "NAME:Selections",
            "Selections:=",
            self.convert_to_selections(list(selection.keys()), False),
            "NewPartsModelFlag:=",
            "Model",
        ]
        arg2 = ["NAME:Parameters"]
        for el in list(selection.keys()):
            arg2.append(
                [
                    "NAME:MoveFacesParameters",
                    "MoveAlongNormalFlag:=",
                    True,
                    "OffsetDistance:=",
                    str(offset) + self.model_units,
                    "MoveVectorX:=",
                    "0mm",
                    "MoveVectorY:=",
                    "0mm",
                    "MoveVectorZ:=",
                    "0mm",
                    "FacesToMove:=",
                    selection[el],
                ]
            )
        self.oeditor.MoveFaces(arg1, arg2)
        return True

    @pyaedt_function_handler()
    def move_edge(self, edges, offset=1.0):
        """Move an input edge or a list of input edges of a specific object.

        This method moves an edge or a list of edges which belong to the same solid.

        Parameters
        ----------
        edges : list
            List of Edge ID or List of :class:`pyaedt.modeler.Object3d.EdgePrimitive` object or mixed.
        offset : float, optional
             Offset to apply in model units. The default is ``1.0``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.MoveEdges

        """

        edge_selection = self.convert_to_selections(edges, True)
        selection = {}
        for f in edge_selection:
            if self.oeditor.GetObjectNameByEdgeID(f) in selection:
                selection[self.oeditor.GetObjectNameByEdgeID(f)].append(f)
            else:
                selection[self.oeditor.GetObjectNameByEdgeID(f)] = [f]

        arg1 = [
            "NAME:Selections",
            "Selections:=",
            self.convert_to_selections(list(selection.keys()), False),
            "NewPartsModelFlag:=",
            "Model",
        ]
        arg2 = ["NAME:Parameters"]
        for el in list(selection.keys()):
            arg2.append(
                [
                    "NAME:MoveEdgesParameters",
                    "MoveAlongNormalFlag:=",
                    True,
                    "OffsetDistance:=",
                    str(offset) + self.model_units,
                    "MoveVectorX:=",
                    "0mm",
                    "MoveVectorY:=",
                    "0mm",
                    "MoveVectorZ:=",
                    "0mm",
                    "EdgesToMove:=",
                    selection[el],
                ]
            )
        self.oeditor.MoveEdges(arg1, arg2)
        return True

    class Position:
        """Position.

        Parameters
        ----------
        args : list or int
            Position of the item as either a list of the ``[x, y, z]`` coordinates
            or three separate values. If no or insufficient arguments
            are specified, ``0`` is applied.

        """

        @pyaedt_function_handler()
        def __getitem__(self, item):
            if item == 0:
                return self.X
            elif item == 1:
                return self.Y
            elif item == 2:
                return self.Z

        @pyaedt_function_handler()
        def __setitem__(self, item, value):
            if item == 0:
                self.X = value
            elif item == 1:
                self.Y = value
            elif item == 2:
                self.Z = value

        def __iter__(self):
            return self

        def __len__(self):
            return 3

        def __init__(self, *args):
            if len(args) == 1 and type(args[0]) is list:
                try:
                    self.X = args[0][0]
                except:
                    self.X = 0
                try:
                    self.Y = args[0][1]
                except:
                    self.Y = 0
                try:
                    self.Z = args[0][2]
                except:
                    self.Z = 0
            else:
                try:
                    self.X = args[0]
                except:
                    self.X = 0
                try:
                    self.Y = args[1]
                except:
                    self.Y = 0
                try:
                    self.Z = args[2]
                except:
                    self.Z = 0

    class SweepOptions(object):
        """Manages sweep options.

        Parameters
        ----------
        draftType : str, optional
            Type of the draft. Options are ``"Round"``, ``"Natural"``,
            and ``"Extended"``. The default is ``"Round"``.
        draftAngle : str, optional
            Draft angle with units. The default is ``"0deg"``.
        twistAngle : str, optional
            Twist angle with units. The default is ``"0deg"``.

        """

        @pyaedt_function_handler()
        def __init__(self, draftType="Round", draftAngle="0deg", twistAngle="0deg"):
            self.DraftType = draftType
            self.DraftAngle = draftAngle
            self.TwistAngle = twistAngle

    @pyaedt_function_handler()
    def create_group(self, objects=None, components=None, groups=None, group_name=None):
        """Group objects or groups into one group.

        At least one between ``objects``, ``components``, ``groups`` has to be defined.

        Parameters
        ----------
        objects : list, optional
            List of objects. The default is ``None``, in which case a group
            with all objects is created.
        components : list, optional
            List of 3d components to group. The default is ``None``.
        groups : list, optional
            List of groups. The default is ``None``.
        group_name : str, optional
            Name of the new group. The default is ``None``.
            It is not possible to choose the name but a name is
            assigned automatically.

        Returns
        -------
        str
           Name assigned to the new group.

        References
        ----------

        >>> oEditor.CreateGroup
        """
        if components is None and groups is None and objects is None:
            raise AttributeError("At least one between ``objects``, ``components``, ``groups`` has to be defined.")

        all_objects = self.object_names
        if objects:
            object_selection = self.convert_to_selections(objects, return_list=False)
        else:
            object_selection = ""
        if groups:
            group_selection = self.convert_to_selections(groups, return_list=False)
        else:
            group_selection = ""
        if components:
            component_selection = self.convert_to_selections(components, return_list=False)
        else:
            component_selection = ""

        arg = [
            "NAME:GroupParameter",
            "ParentGroupID:=",
            "Model",
            "Parts:=",
            object_selection,
            "SubmodelInstances:=",
            component_selection,
            "Groups:=",
            group_selection,
        ]
        assigned_name = self.oeditor.CreateGroup(arg)
        if group_name and group_name not in all_objects:
            self.oeditor.ChangeProperty(
                [
                    "NAME:AllTabs",
                    [
                        "NAME:Attributes",
                        ["NAME:PropServers", assigned_name],
                        ["NAME:ChangedProps", ["NAME:Name", "Value:=", group_name]],
                    ],
                ]
            )
            return group_name
        else:
            return assigned_name

    @pyaedt_function_handler()
    def ungroup(self, groups):
        """Ungroup one or more groups.

        Parameters
        ----------
        groups : list
            List of group names.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.Ungroup
        """
        group_list = self.convert_to_selections(groups, return_list=True)
        arg = ["Groups:=", group_list]
        self.oeditor.Ungroup(arg)
        return True

    @pyaedt_function_handler()
    def flatten_assembly(self):
        """Flatten the assembly, removing all group trees.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.FlattenGroup
        """
        self.oeditor.FlattenGroup(["Groups:=", ["Model"]])
        return True

    @pyaedt_function_handler()
    def wrap_sheet(self, sheet_name, object_name, imprinted=False):
        """Execute the sheet wrapping around an object.
        If wrapping produces an unclassified operation it will be reverted.

        Parameters
        ----------
        sheet_name : str, :class:`pyaedt.modeler.Object3d.Object3d`
            Sheet name or sheet object.
        object_name : str, :class:`pyaedt.modeler.Object3d.Object3d`
            Object name or solid object.
        imprinted : bool, optional
            Either if imprint or not over the sheet. Default is ``False``.

        Returns
        -------
        bool
            Command execution status.
        """
        sheet_name = self.convert_to_selections(sheet_name, False)
        object_name = self.convert_to_selections(object_name, False)

        if sheet_name not in self.sheet_names:
            self.logger.error("{} is not a valid sheet.".format(sheet_name))
            return False
        if object_name not in self.solid_names:
            self.logger.error("{} is not a valid solid body.".format(object_name))
            return False
        unclassified = [i for i in self.unclassified_objects]
        self.oeditor.WrapSheet(
            ["NAME:Selections", "Selections:=", "{},{}".format(sheet_name, object_name)],
            ["NAME:WrapSheetParameters", "Imprinted:=", imprinted],
        )
        is_unclassified = [i for i in self.unclassified_objects if i not in unclassified]
        if is_unclassified:
            self.logger.error("Failed to Wrap sheet. Reverting to original objects.")
            self._odesign.Undo()
            return False
        if imprinted:
            self.cleanup_objects()
        return True
