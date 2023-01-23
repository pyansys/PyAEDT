from __future__ import absolute_import

from collections import OrderedDict

from pyaedt.generic.general_methods import _dim_arg
from pyaedt.generic.general_methods import _retry_ntimes
from pyaedt.generic.general_methods import clamp
from pyaedt.generic.general_methods import pyaedt_function_handler
from pyaedt.generic.general_methods import rgb_color_codes
from pyaedt.generic.general_methods import settings
from pyaedt.modeler.geometry_operators import GeometryOperators


@pyaedt_function_handler()
def _dict2arg(d, arg_out):
    """

    Parameters
    ----------
    d :

    arg_out :


    Returns
    -------

    """
    for k, v in d.items():
        if "_pyaedt" in k:
            continue
        if k == "Point" or k == "DimUnits":
            if isinstance(v[0], (list, tuple)):
                for e in v:
                    arg = ["NAME:" + k, e[0], e[1]]
                    arg_out.append(arg)
            else:
                arg = ["NAME:" + k, v[0], v[1]]
                arg_out.append(arg)
        elif k == "Range":
            if isinstance(v[0], (list, tuple)):
                for e in v:
                    arg_out.append(k + ":=")
                    arg_out.append([i for i in e])
            else:
                arg_out.append(k + ":=")
                arg_out.append([i for i in v])
        elif isinstance(v, (OrderedDict, dict)):
            arg = ["NAME:" + k]
            _dict2arg(v, arg)
            arg_out.append(arg)
        elif v is None:
            arg_out.append(["NAME:" + k])
        elif type(v) is list and len(v) > 0 and isinstance(v[0], (OrderedDict, dict)):
            for el in v:
                arg = ["NAME:" + k]
                _dict2arg(el, arg)
                arg_out.append(arg)

        else:
            arg_out.append(k + ":=")
            if type(v) is EdgePrimitive or type(v) is FacePrimitive or type(v) is VertexPrimitive:
                arg_out.append(v.id)
            else:
                arg_out.append(v)


class EdgeTypePrimitive(object):
    """Provides common methods for EdgePrimitive and FacePrimitive."""

    @pyaedt_function_handler()
    def fillet(self, radius=0.1, setback=0.0):
        """Add a fillet to the selected edge.

        Parameters
        ----------
        radius : float, optional
            Radius of the fillet. The default is ``0.1``.
        setback : float, optional
            Setback value for the file. The default is ``0.0``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.Fillet

        """
        edge_id_list = []
        vertex_id_list = []

        if isinstance(self, VertexPrimitive):
            vertex_id_list = [self.id]
        else:
            if self._object3d.is3d:
                edge_id_list = [self.id]
            else:
                self._object3d.logger.error("Filet is possible only on a vertex in 2D designs.")
                return False

        vArg1 = ["NAME:Selections", "Selections:=", self._object3d.name, "NewPartsModelFlag:=", "Model"]
        vArg2 = ["NAME:FilletParameters"]
        vArg2.append("Edges:="), vArg2.append(edge_id_list)
        vArg2.append("Vertices:="), vArg2.append(vertex_id_list)
        vArg2.append("Radius:="), vArg2.append(self._object3d._primitives._arg_with_dim(radius))
        vArg2.append("Setback:="), vArg2.append(self._object3d._primitives._arg_with_dim(setback))
        self._object3d.m_Editor.Fillet(vArg1, ["NAME:Parameters", vArg2])
        if self._object3d.name in list(self._object3d.m_Editor.GetObjectsInGroup("UnClassified")):
            self._object3d._primitives._odesign.Undo()
            self._object3d.logger.error("Operation failed, generating an unclassified object. Check and retry.")
            return False
        return True

    @pyaedt_function_handler()
    def chamfer(self, left_distance=1, right_distance=None, angle=45, chamfer_type=0):
        """Add a chamfer to the selected edge.

        Parameters
        ----------
        left_distance : float, optional
            Left distance from the edge. The default is ``1``.
        right_distance : float, optional
            Right distance from the edge. The default is ``None``.
        angle : float, optional.
            Angle value for chamfer types 2 and 3. The default is ``0``.
        chamfer_type : int, optional
            Type of the chamfer. Options are:
                * 0 - Symmetric
                * 1 - Left Distance-Right Distance
                * 2 - Left Distance-Angle
                * 3 - Right Distance-Angle

            The default is ``0``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.Chamfer

        """
        edge_id_list = []
        vertex_id_list = []

        if isinstance(self, VertexPrimitive):
            vertex_id_list = [self.id]
        else:
            if self._object3d.is3d:
                edge_id_list = [self.id]
            else:
                self._object3d.logger.error("chamfer is possible only on Vertex in 2D Designs ")
                return False
        vArg1 = ["NAME:Selections", "Selections:=", self._object3d.name, "NewPartsModelFlag:=", "Model"]
        vArg2 = ["NAME:ChamferParameters"]
        vArg2.append("Edges:="), vArg2.append(edge_id_list)
        vArg2.append("Vertices:="), vArg2.append(vertex_id_list)
        vArg2.append("LeftDistance:="), vArg2.append(self._object3d._primitives._arg_with_dim(left_distance))
        if not right_distance:
            right_distance = left_distance
        if chamfer_type == 0:
            vArg2.append("RightDistance:="), vArg2.append(self._object3d._primitives._arg_with_dim(right_distance))
            vArg2.append("ChamferType:="), vArg2.append("Symmetric")
        elif chamfer_type == 1:
            vArg2.append("RightDistance:="), vArg2.append(self._object3d._primitives._arg_with_dim(right_distance))
            vArg2.append("ChamferType:="), vArg2.append("Left Distance-Right Distance")
        elif chamfer_type == 2:
            vArg2.append("Angle:="), vArg2.append(str(angle) + "deg")
            vArg2.append("ChamferType:="), vArg2.append("Left Distance-Right Distance")
        elif chamfer_type == 3:
            vArg2.append("LeftDistance:="), vArg2.append(str(angle) + "deg")
            vArg2.append("RightDistance:="), vArg2.append(self._object3d._primitives._arg_with_dim(right_distance))
            vArg2.append("ChamferType:="), vArg2.append("Right Distance-Angle")
        else:
            self._object3d.logger.error("Wrong Type Entered. Type must be integer from 0 to 3")
            return False
        self._object3d.m_Editor.Chamfer(vArg1, ["NAME:Parameters", vArg2])
        if self._object3d.name in list(self._object3d.m_Editor.GetObjectsInGroup("UnClassified")):
            self._object3d.odesign.Undo()
            self._object3d.logger.error("Operation Failed generating Unclassified object. Check and retry")
            return False
        return True


class VertexPrimitive(EdgeTypePrimitive, object):
    """Contains the vertex object within the AEDT Desktop Modeler.

    Parameters
    ----------
    object3d : :class:`pyaedt.modeler.object3d.Object3d`
        Pointer to the calling object that provides additional functionality.
    objid : int
        Object ID as determined by the parent object.

    """

    def __init__(self, object3d, objid):
        self.id = objid
        self._object3d = object3d
        self.oeditor = object3d.m_Editor

    @property
    def position(self):
        """Position of the vertex.

        Returns
        -------
        list of float values or ''None``
            List of ``[x, y, z]`` coordinates of the vertex
            in model units when the data from AEDT is valid, ``None``
            otherwise.

        References
        ----------

        >>> oEditor.GetVertexPosition

        """
        try:
            vertex_data = list(self.oeditor.GetVertexPosition(self.id))
            return [float(i) for i in vertex_data]
        except Exception as e:
            return None

    def __repr__(self):
        return "Vertex " + str(self.id)

    def __str__(self):
        return "Vertex " + str(self.id)


class EdgePrimitive(EdgeTypePrimitive, object):
    """Contains the edge object within the AEDT Desktop Modeler.

    Parameters
    ----------
    object3d : :class:`pyaedt.modeler.object3d.Object3d`
        Pointer to the calling object that provides additional functionality.
    edge_id : int
        Object ID as determined by the parent object.

    """

    def __init__(self, object3d, edge_id):
        self.id = edge_id
        self._object3d = object3d
        self.oeditor = object3d.m_Editor

    @property
    def segment_info(self):
        """Compute segment information using the object-oriented method (from AEDT 2021 R2
        with beta options). The method manages segment info for lines, circles and ellipse
        providing information about all of those.


        Returns
        -------
            list
                Segment info if available."""
        try:
            self.oeditor.GetChildNames()
        except:  # pragma: no cover
            return {}
        ll = list(self.oeditor.GetObjectsInGroup("Lines"))
        self.oeditor.CreateObjectFromEdges(
            ["NAME:Selections", "Selections:=", self._object3d.name, "NewPartsModelFlag:=", "NonModel"],
            ["NAME:Parameters", ["NAME:BodyFromEdgeToParameters", "Edges:=", [self.id]]],
            ["CreateGroupsForNewObjects:=", False],
        )
        new_line = [i for i in list(self.oeditor.GetObjectsInGroup("Lines")) if i not in ll]
        self.oeditor.GenerateHistory(
            ["NAME:Selections", "Selections:=", new_line[0], "NewPartsModelFlag:=", "NonModel", "UseCurrentCS:=", True]
        )
        oo = self.oeditor.GetChildObject(new_line[0])
        segment = {}
        if len(self.vertices) == 2:
            oo1 = oo.GetChildObject(oo.GetChildNames()[0]).GetChildObject("Segment0")
        else:
            oo1 = oo.GetChildObject(oo.GetChildNames()[0])
        for prop in oo1.GetPropNames():
            if "/" not in prop:
                val = oo1.GetPropValue(prop)
                if "X:=" in val and len(val) == 6:
                    segment[prop] = [val[1], val[3], val[5]]
                else:
                    segment[prop] = val
        self._object3d._primitives._odesign.Undo()
        self._object3d._primitives._odesign.Undo()
        return segment

    @property
    def vertices(self):
        """Vertices list.

        Returns
        -------
        list of :class:`pyaedt.modeler.object3d.VertexPrimitive`
            List of vertices.

        References
        ----------

        >>> oEditor.GetVertexIDsFromEdge

        """
        vertices = []
        v = [i for i in self.oeditor.GetVertexIDsFromEdge(self.id)]
        if settings.aedt_version > "2022.2":
            v = v[::-1]
        for vertex in v:
            vertex = int(vertex)
            vertices.append(VertexPrimitive(self._object3d, vertex))
        return vertices

    @property
    def midpoint(self):
        """Midpoint coordinates of the edge.

        Returns
        -------
        list of float values or ``None``
            Midpoint in ``[x, y, z]`` coordinates when the edge
            is a circle with only one vertex, ``None`` otherwise.

        References
        ----------

        >>> oEditor.GetVertexPosition

        """

        if len(self.vertices) == 2:
            midpoint = GeometryOperators.get_mid_point(self.vertices[0].position, self.vertices[1].position)
            return list(midpoint)
        elif len(self.vertices) == 1:
            return self.vertices[0].position
        else:
            return [float(i) for i in self.oeditor.GetEdgePositionAtNormalizedParameter(self.id, 0)]

    @property
    def length(self):
        """Length of the edge.

        Returns
        -------
        float or bool
            Edge length in model units when edge has two vertices, ``False`` otherwise.

        References
        ----------

        >>> oEditor.GetEdgeLength

        """
        try:
            return float(self.oeditor.GetEdgeLength(self.id))
        except:
            return False

    def __repr__(self):
        return "EdgeId " + str(self.id)

    def __str__(self):
        return "EdgeId " + str(self.id)

    @pyaedt_function_handler()
    def create_object(self, non_model=False, create_group_for_new_objects=False):
        """Return a new object from the selected edge.

        Returns
        -------
        :class:`pyaedt.modeler.object3d.Object3d`
            3D object.
        non_model : bool, optional
            Either if create the new object as model or non-model. The default is `False`.

        References
        ----------

        >>> oEditor.CreateObjectFromEdges
        """
        return self._object3d._primitives.create_object_from_edge(self, non_model)

    @pyaedt_function_handler()
    def move_along_normal(self, offset=1.0):
        """Move this edge.
        This method moves an edge which belong to the same solid.

        Parameters
        ----------
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
        if self._object3d.object_type == "Solid":
            self._object3d.logger.error("Edge Movement applies only to 2D objects.")
            return False
        return self._object3d._primitives.move_edge(self, offset)


class FacePrimitive(object):
    """Contains the face object within the AEDT Desktop Modeler."""

    def __repr__(self):
        return "FaceId " + str(self.id)

    def __str__(self):
        return "FaceId " + str(self.id)

    def __init__(self, object3d, obj_id):
        """

        Parameters
        ----------
        object3d : :class:`pyaedt.modeler.object3d.Object3d`
        obj_id : int
        """
        self._id = obj_id
        self._object3d = object3d

    @property
    def oeditor(self):
        """Oeditor Module."""
        return self._object3d.m_Editor

    @property
    def logger(self):
        """Logger."""
        return self._object3d.logger

    @property
    def _units(self):
        return self._object3d.object_units

    @property
    def touching_objects(self):
        """Get the objects that touch one of the vertex, edge midpoint or the actual face.

        Returns
        -------
        list
            Object names touching that face.
        """
        list_names = []
        for vertex in self.vertices:
            body_names = self._object3d._primitives.get_bodynames_from_position(
                vertex.position, include_non_model=False
            )
            a = [i for i in body_names if i != self._object3d.name and i not in list_names]
            if a:
                list_names.extend(a)
        for edge in self.edges:
            body_names = self._object3d._primitives.get_bodynames_from_position(edge.midpoint, include_non_model=False)
            a = [i for i in body_names if i != self._object3d.name and i not in list_names]
            if a:
                list_names.extend(a)
        body_names = self._object3d._primitives.get_bodynames_from_position(self.center, include_non_model=False)
        a = [i for i in body_names if i != self._object3d.name and i not in list_names]
        if a:
            list_names.extend(a)
        return list_names

    @property
    def edges(self):
        """Edges lists.

        Returns
        -------
        list of :class:`pyaedt.modeler.object3d.EdgePrimitive`
            List of Edges.

        References
        ----------

        >>> oEditor.GetEdgeIDsFromFace

        """
        edges = []
        for edge in list(self.oeditor.GetEdgeIDsFromFace(self.id)):
            edges.append(EdgePrimitive(self._object3d, int(edge)))
        return edges

    @property
    def vertices(self):
        """Vertices lists.

        Returns
        -------
        list of :class:`pyaedt.modeler.object3d.VertexPrimitive`
            List of Vertices.

        References
        ----------

        >>> oEditor.GetVertexIDsFromFace

        """
        vertices = []
        v = [i for i in self.oeditor.GetVertexIDsFromFace(self.id)]
        if settings.aedt_version > "2022.2":
            v = v[::-1]
        for vertex in v:
            vertex = int(vertex)
            vertices.append(VertexPrimitive(self._object3d, int(vertex)))
        return vertices

    @property
    def id(self):
        """Face ID."""
        return self._id

    @property
    def center_from_aedt(self):
        """Face center for a planar face in model units.

        Returns
        -------
        list or bool
            Center position in ``[x, y, z]`` coordinates for the planar face, ``False`` otherwise.

        References
        ----------

        >>> oEditor.GetFaceCenter

        """
        try:
            c = self.oeditor.GetFaceCenter(self.id)
        except:
            self.logger.warning("Non-planar face does not provide a face center.")
            return False
        center = [float(i) for i in c]
        return center

    @property
    def is_planar(self):
        """Check if a face is planar or not.

        Returns
        -------
        bool
        """

        try:
            self.oeditor.GetFaceCenter(self.id)
            return True
        except:
            return False

    @property
    def center(self):
        """Face center in model units.

        .. note::
           It returns the face centroid if number of face vertex is >1.
           It tries to get AEDT Face Center in case of single vertex face
           and returns the vertex position otherwise.

        Returns
        -------
        list of float values
            Centroid of all vertices of the face.

        References
        ----------

        >>> oEditor.GetFaceCenter

        """
        if len(self.vertices) > 1:
            return GeometryOperators.get_polygon_centroid([pos.position for pos in self.vertices])
        else:
            center = self.center_from_aedt
            if center:
                return center
            else:
                return self.vertices[0].position

    @property
    def area(self):
        """Face area.

        Returns
        -------
        float
            Face area in model units.

        References
        ----------

        >>> oEditor.GetFaceArea

        """
        area = self.oeditor.GetFaceArea(self.id)
        return area

    @property
    def top_edge_z(self):
        """Top edge in the Z direction of the object. Midpoint is used as criteria to find the edge.

        Returns
        -------
        :class:`pyaedt.modeler.object3d.EdgePrimitive`

        References
        ----------

        >>> oEditor.FaceCenter

        """
        try:
            result = [(float(edge.midpoint[2]), edge) for edge in self.edges]
            result = sorted(result, key=lambda tup: tup[0])
            return result[-1][1]
        except:
            return None

    @property
    def bottom_edge_z(self):
        """Bottom edge in the Z direction of the object. Midpoint is used as criteria to find the edge.

        Returns
        -------
        :class:`pyaedt.modeler.object3d.EdgePrimitive`

        """
        try:
            result = [(float(edge.midpoint[2]), edge) for edge in self.edges]
            result = sorted(result, key=lambda tup: tup[0])
            return result[0][1]
        except:
            return None

    @property
    def top_edge_x(self):
        """Top edge in the X direction of the object. Midpoint is used as criteria to find the edge.

        Returns
        -------
        :class:`pyaedt.modeler.object3d.EdgePrimitive`

        """
        try:
            result = [(float(edge.midpoint[0]), edge) for edge in self.edges]
            result = sorted(result, key=lambda tup: tup[0])
            return result[-1][1]
        except:
            return None

    @property
    def bottom_edge_x(self):
        """Bottom edge in the X direction of the object. Midpoint is used as criteria to find the edge.

        Returns
        -------
        :class:`pyaedt.modeler.object3d.EdgePrimitive`

        """
        try:
            result = [(float(edge.midpoint[0]), edge) for edge in self.edges]
            result = sorted(result, key=lambda tup: tup[0])
            return result[0][1]
        except:
            return None

    @property
    def top_edge_y(self):
        """Top edge in the Y direction of the object. Midpoint is used as criteria to find the edge.

        Returns
        -------
        :class:`pyaedt.modeler.object3d.EdgePrimitive`

        """
        try:
            result = [(float(edge.midpoint[1]), edge) for edge in self.edges]
            result = sorted(result, key=lambda tup: tup[0])
            return result[-1][1]
        except:
            return None

    @property
    def bottom_edge_y(self):
        """Bottom edge in the X direction of the object. Midpoint is used as criteria to find the edge.

        Returns
        -------
        :class:`pyaedt.modeler.object3d.EdgePrimitive`

        """
        try:
            result = [(float(edge.midpoint[1]), edge) for edge in self.edges]
            result = sorted(result, key=lambda tup: tup[0])
            return result[0][1]
        except:
            return None

    @pyaedt_function_handler()
    def is_on_bounding(self, tol=1e-9):
        """Check if the face is on bounding box or Not.

        Parameters
        ----------
        tolerance : float, optional
            Tolerance of check between face center and bounding box.

        Returns
        -------
        bool
            `True` if the face is on bounding box. `False` otherwise.
        """
        b = [float(i) for i in list(self.oeditor.GetModelBoundingBox())]
        c = self.center
        if (
            abs(c[0] - b[0]) < tol
            or abs(c[1] - b[1]) < tol
            or abs(c[2] - b[2]) < tol
            or abs(c[0] - b[3]) < tol
            or abs(c[1] - b[4]) < tol
            or abs(c[2] - b[5]) < tol
        ):
            return True
        return False

    @pyaedt_function_handler()
    def move_with_offset(self, offset=1.0):
        """Move the face along the normal.

        Parameters
        ----------
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
        self.oeditor.MoveFaces(
            ["NAME:Selections", "Selections:=", self._object3d.name, "NewPartsModelFlag:=", "Model"],
            [
                "NAME:Parameters",
                [
                    "NAME:MoveFacesParameters",
                    "MoveAlongNormalFlag:=",
                    True,
                    "OffsetDistance:=",
                    _dim_arg(offset, self._object3d.object_units),
                    "MoveVectorX:=",
                    "0mm",
                    "MoveVectorY:=",
                    "0mm",
                    "MoveVectorZ:=",
                    "0mm",
                    "FacesToMove:=",
                    [self.id],
                ],
            ],
        )
        return True

    @pyaedt_function_handler()
    def move_with_vector(self, vector):
        """Move the face along a vector.

        Parameters
        ----------
        vector : list
            List of ``[x, y, z]`` coordinates for the vector.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.MoveFaces

        """
        self.oeditor.MoveFaces(
            ["NAME:Selections", "Selections:=", self._object3d.name, "NewPartsModelFlag:=", "Model"],
            [
                "NAME:Parameters",
                [
                    "NAME:MoveFacesParameters",
                    "MoveAlongNormalFlag:=",
                    False,
                    "OffsetDistance:=",
                    "0mm",
                    "MoveVectorX:=",
                    _dim_arg(vector[0], self._object3d.object_units),
                    "MoveVectorY:=",
                    _dim_arg(vector[1], self._object3d.object_units),
                    "MoveVectorZ:=",
                    _dim_arg(vector[2], self._object3d.object_units),
                    "FacesToMove:=",
                    [self.id],
                ],
            ],
        )
        return True

    @property
    def normal(self):
        """Face normal.

        Limitations:
        #. The face must be planar.
        #. Currently it works only if the face has at least two vertices. Notable excluded items are circles and
        ellipses that have only one vertex.
        #. If a bounding box is specified, the normal is orientated outwards with respect to the bounding box.
        Usually the bounding box refers to a volume where the face lies.
        If no bounding box is specified, the normal can be inward or outward the volume.

        Returns
        -------
        list of float values or ``None``
            Normal vector (normalized ``[x, y, z]`` coordinates) or ``None``.

        References
        ----------

        >>> oEditor.GetVertexPosition

        """
        vertices_ids = self.vertices
        if len(vertices_ids) < 2 or not self.center:
            self._object3d.logger.warning("Not enough vertices or non-planar face")
            return None
        # elif len(vertices_ids)<2:
        #     v1 = vertices_ids[0].position
        #     offset = [(a-b)/2 for a,b in zip(v1,self.center)]
        #     v2 = [a+b for a,b in zip(self.center, offset)]
        else:
            v1 = vertices_ids[0].position
            v2 = vertices_ids[1].position
        fc = self.center
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

        """
        Try to move the face center twice, the first with the normal vector, and the second with its inverse.
        Measures which is closer to the center point of the bounding box.
        """
        inv_norm = [-i for i in normal]
        mv1 = GeometryOperators.v_sum(fc, normal)
        mv2 = GeometryOperators.v_sum(fc, inv_norm)
        bb_center = GeometryOperators.get_mid_point(self._object3d.bounding_box[0:3], self._object3d.bounding_box[3:6])
        d1 = GeometryOperators.points_distance(mv1, bb_center)
        d2 = GeometryOperators.points_distance(mv2, bb_center)
        if d1 > d2:
            return normal
        else:
            return inv_norm

    @pyaedt_function_handler()
    def create_object(self, non_model=False):
        """Return a new object from the selected face.

        Returns
        -------
        :class:`pyaedt.modeler.object3d.Object3d`
            3D object.
        non_model : bool, optional
            Either if create the new object as model or non-model. Default is `False`.

        References
        ----------

        >>> oEditor.CreateObjectFromFaces
        """
        return self._object3d._primitives.create_object_from_face(self, non_model)


class Point(object):
    """Manages point attributes for the AEDT 3D Modeler.

    Parameters
    ----------
    primitives : :class:`pyaedt.modeler.Primitives3D.Primitives3D`
        Inherited parent object.
    name : str
        Name of the point.

    Examples
    --------
    Basic usage demonstrated with an HFSS design:

    >>> from pyaedt import Hfss
    >>> aedtapp = Hfss()
    >>> primitives = aedtapp.modeler

    Create a point, to return an :class:`pyaedt.modeler.Object3d.Point`.

    >>> point = primitives.create_point([30, 30, 0], "my_point", (0, 195, 255))
    >>> my_point = primitives.points[point.name]
    """

    def __init__(self, primitives, name):
        self._name = name
        self._point_coordinate_system = "Global"
        self._color = None
        self._position = None
        self._primitives = primitives
        self._all_props = None

    @property
    def m_Editor(self):
        """Pointer to the oEditor object in the AEDT API. This property is
        intended primarily for use by FacePrimitive, EdgePrimitive, and
        VertexPrimitive child objects.

        Returns
        -------
        oEditor COM Object

        """
        return self._primitives.oeditor

    @property
    def logger(self):
        """Logger."""
        return self._primitives.logger

    @property
    def name(self):
        """Name of the point as a string value.

        Returns
        -------
        str
           Name of object as a string value.

        References
        ----------

        >>> oEditor.GetPropertyValue
        >>> oEditor.ChangeProperty

        """
        return self._name

    @name.setter
    def name(self, point_name):
        if point_name not in self._primitives.points.keys:
            if point_name != self._name:
                name_property = []
                name_property.append("NAME:Name")
                name_property.append("Value:=")
                name_property.append(point_name)
                changed_property = ["NAME:ChangedProps", name_property]
                property_servers = ["NAME:PropServers"]
                property_servers.append(self._name)
                point_tab = ["NAME:Geometry3DPointTab", property_servers, changed_property]
                all_tabs = ["NAME:AllTabs", point_tab]
                _retry_ntimes(10, self._primitives.oeditor.ChangeProperty, all_tabs)
                self._name = point_name
                self._primitives.cleanup_objects()
        else:
            self.logger.warning("A point named '%s' already exists.", point_name)

    @property
    def valid_properties(self):
        """Valid properties.

        References
        ----------

        >>> oEditor.GetProperties
        """
        if not self._all_props:
            self._all_props = _retry_ntimes(10, self.m_Editor.GetProperties, "Geometry3DPointTab", self._name)
        return self._all_props

    # Note: We currently cannot get the color property value because
    # when we try to access it, we only get access to the 'edit' button.
    # Following is the line that we would use but it currently returns 'edit'.
    # color = _retry_ntimes(10, self.m_Editor.GetPropertyValue, "Geometry3DPointTab", self._name, "Color")
    def set_color(self, color_value):
        """Set symbol color.

        Parameters
        ----------
        color_value : string
            String exposing the new color of the point in the format of "(001 255 255)".

        References
        ----------

        >>> oEditor.ChangeProperty

        Examples
        --------
        >>> point = self.aedtapp.modeler.create_point([30, 30, 0], "demo_point")
        >>> point.set_color("(143 175 158)")

        """
        color_tuple = None
        if isinstance(color_value, str):
            try:
                color_tuple = rgb_color_codes[color_value]
            except KeyError:
                parse_string = color_value.replace(")", "").replace("(", "").split()
                if len(parse_string) == 3:
                    color_tuple = tuple([int(x) for x in parse_string])
        else:
            try:
                color_tuple = tuple([int(x) for x in color_value])
            except ValueError:
                pass

        if color_tuple:
            try:
                R = clamp(color_tuple[0], 0, 255)
                G = clamp(color_tuple[1], 0, 255)
                B = clamp(color_tuple[2], 0, 255)
                vColor = ["NAME:Color", "R:=", str(R), "G:=", str(G), "B:=", str(B)]
                self._change_property(vColor)
                self._color = (R, G, B)
            except TypeError:
                color_tuple = None
        else:
            msg_text = "Invalid color input {} for object {}.".format(color_value, self._name)
            self._primitives.logger.warning(msg_text)

    @property
    def coordinate_system(self):
        """Coordinate system of the point.

        Returns
        -------
        str
            Name of the point's coordinate system.

        References
        ----------

        >>> oEditor.GetPropertyValue
        >>> oEditor.ChangeProperty

        """
        if self._point_coordinate_system is not None:
            return self._point_coordinate_system
        if "Orientation" in self.valid_properties:
            self._point_coordinate_system = _retry_ntimes(
                10, self.m_Editor.GetPropertyValue, "Geometry3DPointTab", self._name, "Orientation"
            )
            return self._point_coordinate_system

    @coordinate_system.setter
    def coordinate_system(self, new_coordinate_system):

        coordinate_system = ["NAME:Orientation", "Value:=", new_coordinate_system]
        self._change_property(coordinate_system)
        self._point_coordinate_system = new_coordinate_system
        return True

    @pyaedt_function_handler()
    def delete(self):
        """Delete the point.

        References
        ----------

        >>> oEditor.Delete
        """
        arg = ["NAME:Selections", "Selections:=", self._name]
        self.m_Editor.Delete(arg)
        self._primitives.cleanup_objects()
        self.__dict__ = {}

    @pyaedt_function_handler()
    def _change_property(self, vPropChange):
        return self._primitives._change_point_property(vPropChange, self.name)


class Plane(object):
    """Manages plane attributes for the AEDT 3D Modeler.

    Parameters
    ----------
    primitives : :class:`pyaedt.modeler.Primitives3D.Primitives3D`
        Inherited parent object.
    name : str
        Name of the point.

    Examples
    --------
    Basic usage demonstrated with an HFSS design:

    >>> from pyaedt import Hfss
    >>> aedtapp = Hfss()
    >>> primitives = aedtapp.modeler

    Create a plane, to return an :class:`pyaedt.modeler.Object3d.Plane`.

    >>> plane = primitives.create_plane("my_plane", "-0.7mm", "0.3mm", "0mm", "0.7mm", "-0.3mm", "0mm", "(0, 195, 255)")
    >>> my_plane = primitives.planes[plane.name]
    """

    def __init__(self, primitives, name):
        self._name = name
        self._plane_coordinate_system = "Global"
        self._color = None
        self._root_point = None
        self._normal = None
        self._primitives = primitives
        self._all_props = None

    @property
    def m_Editor(self):
        """Pointer to the oEditor object in the AEDT API. This property is
        intended primarily for use by FacePrimitive, EdgePrimitive, and
        VertexPrimitive child objects.

        Returns
        -------
        oEditor COM Object

        """
        return self._primitives.oeditor

    @property
    def logger(self):
        """Logger."""
        return self._primitives.logger

    @property
    def name(self):
        """Name of the plane as a string value.

        Returns
        -------
        str
           Name of object as a string value.

        References
        ----------

        >>> oEditor.GetPropertyValue
        >>> oEditor.ChangeProperty

        """
        return self._name

    @name.setter
    def name(self, plane_name):
        if plane_name not in self._primitives.planes.keys():
            plane_old_name = self._name
            if plane_name != self._name:
                name_property = []
                name_property.append("NAME:Name")
                name_property.append("Value:=")
                name_property.append(plane_name)
                changed_property = ["NAME:ChangedProps", name_property]
                property_servers = ["NAME:PropServers"]
                property_servers.append(self._name)
                plane_tab = ["NAME:Geometry3DPlaneTab", property_servers, changed_property]
                all_tabs = ["NAME:AllTabs", plane_tab]
                _retry_ntimes(10, self._primitives.oeditor.ChangeProperty, all_tabs)
                self._name = plane_name
                # TO BE DELETED self._primitives.cleanup_objects()
                # Update the name of the plane in the ``planes`` dictionary listing all existing planes.
                self._primitives.planes[plane_name] = self._primitives.planes.pop(plane_old_name)
        else:
            self.logger.warning("A plane named '%s' already exists.", plane_name)

    @property
    def valid_properties(self):
        """Valid properties.

        References
        ----------

        >>> oEditor.GetProperties
        """
        if not self._all_props:
            self._all_props = _retry_ntimes(10, self.m_Editor.GetProperties, "Geometry3DPlaneTab", self._name)
        return self._all_props

    # Note: You currently cannot get the color property value because
    # when you try to access it, you only get access to the 'edit' button.
    # Following is the line that you would use, but it currently returns 'edit'.
    # color = _retry_ntimes(10, self.m_Editor.GetPropertyValue, "Geometry3DPlaneTab", self._name, "Color")
    @pyaedt_function_handler()
    def set_color(self, color_value):
        """Set symbol color.

        Parameters
        ----------
        color_value : string
            String exposing the new color of the plane in the format of "(001 255 255)".

        References
        ----------

        >>> oEditor.ChangeProperty

        Examples
        --------
        >>> plane = self.aedtapp.modeler.create_plane("-0.7mm","0.3mm", "0mm", "0.7mm", "-0.3mm", "0mm", "demo_plane")
        >>> plane.set_color("(143 175 158)")

        """
        color_tuple = None
        if isinstance(color_value, str):
            try:
                color_tuple = rgb_color_codes[color_value]
            except KeyError:
                parse_string = color_value.replace(")", "").replace("(", "").split()
                if len(parse_string) == 3:
                    color_tuple = tuple([int(x) for x in parse_string])
        else:
            try:
                color_tuple = tuple([int(x) for x in color_value])
            except ValueError:
                pass

        if color_tuple:
            try:
                R = clamp(color_tuple[0], 0, 255)
                G = clamp(color_tuple[1], 0, 255)
                B = clamp(color_tuple[2], 0, 255)
                vColor = ["NAME:Color", "R:=", str(R), "G:=", str(G), "B:=", str(B)]
                self._change_property(vColor)
                self._color = (R, G, B)
            except TypeError:
                color_tuple = None
        else:
            msg_text = "Invalid color input {} for object {}.".format(color_value, self._name)
            self._primitives.logger.warning(msg_text)

    @property
    def coordinate_system(self):
        """Coordinate system of the plane.

        Returns
        -------
        str
            Name of the plane's coordinate system.

        References
        ----------

        >>> oEditor.GetPropertyValue
        >>> oEditor.ChangeProperty

        """
        if self._plane_coordinate_system is not None:
            return self._plane_coordinate_system
        if "Orientation" in self.valid_properties:
            self._plane_coordinate_system = _retry_ntimes(
                10, self.m_Editor.GetPropertyValue, "Geometry3DPlaneTab", self._name, "Orientation"
            )
            return self._plane_coordinate_system

    @coordinate_system.setter
    def coordinate_system(self, new_coordinate_system):
        coordinate_system = ["NAME:Orientation", "Value:=", new_coordinate_system]
        self._change_property(coordinate_system)
        self._plane_coordinate_system = new_coordinate_system
        return True

    @pyaedt_function_handler()
    def delete(self):
        """Delete the plane.

        References
        ----------

        >>> oEditor.Delete
        """
        arg = ["NAME:Selections", "Selections:=", self._name]
        self.m_Editor.Delete(arg)
        self._primitives.cleanup_objects()
        self.__dict__ = {}

    @pyaedt_function_handler()
    def _change_property(self, vPropChange):
        return self._primitives._change_plane_property(vPropChange, self.name)


class HistoryProps(OrderedDict):
    """Manages an object's history properties."""

    def __setitem__(self, key, value):
        OrderedDict.__setitem__(self, key, value)
        if self._pyaedt_child.auto_update:
            self._pyaedt_child.update_property(key, value)

    def __init__(self, child_object, props):
        OrderedDict.__init__(self)
        if props:
            for key, value in props.items():
                OrderedDict.__setitem__(self, key, value)
        self._pyaedt_child = child_object

    def _setitem_without_update(self, key, value):
        OrderedDict.__setitem__(self, key, value)


class BinaryTreeNode:
    """Manages an object's history structure."""

    def __init__(self, node, child_object, first_level=False):
        self.node = node
        self.child_object = child_object
        self.children = {}
        self.auto_update = True
        name = None
        for i in list(child_object.GetChildNames()):
            if not name:
                name = i
            if not i.startswith("OperandPart_"):
                self.children[i] = BinaryTreeNode(i, self.child_object.GetChildObject(i))
            else:
                names = self.child_object.GetChildObject(i).GetChildNames()
                for name in names:
                    self.children[name] = BinaryTreeNode(name, self.child_object.GetChildObject(i).GetChildObject(name))
        self.props = {}
        if first_level:
            self.child_object = self.children[name].child_object
            del self.children[name]
        for i in self.child_object.GetPropNames():
            self.props[i] = self.child_object.GetPropValue(i)
        self.props = HistoryProps(self, self.props)
        self.command = self.props.get("Command", "")

    def update_property(self, prop_name, prop_value):
        """Update the property of the binary tree node.

        Parameters
        ----------
        prop_name : str
             Name of the property.
        prop_value : str
             Value of the property.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        try:
            self.child_object.SetPropValue(prop_name, prop_value)
            return True
        except:
            return False
