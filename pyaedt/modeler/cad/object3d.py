# -*- coding: utf-8 -*-
"""
This module contains these classes: `Components3DLayout`,`CircuitComponent',
`EdgePrimitive`, `EdgeTypePrimitive`, `FacePrimitive`, `Geometries3DLayout`,
`Nets3DLayout`, `Objec3DLayout`, `Object3d`, `Padstack`, `PDSHole`, `PDSLayer`,
`Pins3DLayout', and `VertexPrimitive`.

This module provides methods and data structures for managing all properties of
objects (points, lines, sheeets, and solids) within the AEDT 3D Modeler.

"""
from __future__ import absolute_import  # noreorder

import os
import re
import warnings

from pyaedt.generic.constants import AEDT_UNITS
from pyaedt.generic.general_methods import _retry_ntimes
from pyaedt.generic.general_methods import _to_boolean
from pyaedt.generic.general_methods import _uname
from pyaedt.generic.general_methods import clamp
from pyaedt.generic.general_methods import is_ironpython
from pyaedt.generic.general_methods import open_file
from pyaedt.generic.general_methods import pyaedt_function_handler
from pyaedt.generic.general_methods import rgb_color_codes
from pyaedt.generic.general_methods import settings
from pyaedt.modeler.cad.elements3d import BinaryTreeNode
from pyaedt.modeler.cad.elements3d import EdgePrimitive
from pyaedt.modeler.cad.elements3d import FacePrimitive
from pyaedt.modeler.cad.elements3d import VertexPrimitive


class Object3d(object):
    """Manages object attributes for the AEDT 3D Modeler.

    Parameters
    ----------
    primitives : :class:`pyaedt.modeler.Primitives3D.Primitives3D`
        Inherited parent object.
    name : str

    Examples
    --------
    Basic usage demonstrated with an HFSS design:

    >>> from pyaedt import Hfss
    >>> aedtapp = Hfss()
    >>> prim = aedtapp.modeler

    Create a part, such as box, to return an :class:`pyaedt.modeler.Object3d.Object3d`.

    >>> id = prim.create_box([0, 0, 0], [10, 10, 5], "Mybox", "Copper")
    >>> part = prim[id]
    """

    def __init__(self, primitives, name=None):
        """
        Parameters
        ----------
        primitives : :class:`pyaedt.modeler.Primitives3D.Primitives3D`
            Inherited parent object.
        name : str
        """
        self._id = None
        if name:
            self._m_name = name
        else:
            self._m_name = _uname()
        self._primitives = primitives
        self.flags = ""
        self._part_coordinate_system = "Global"
        self._material_name = None
        self._transparency = None
        self._solve_inside = None
        self._is_updated = False
        self._all_props = None
        self._surface_material = None
        self._color = None
        self._wireframe = None
        self._part_coordinate_system = None
        self._model = None
        self._m_groupName = None
        self._object_type = None
        self._mass = 0.0
        self._volume = 0.0

    @pyaedt_function_handler()
    def _bounding_box_unmodel(self):
        """Bounding box of a part, unmodel/undo method.

        This is done by setting all other objects as unmodel and getting the model bounding box.
        Then an undo operation restore the design.

        Returns
        -------
        list of [list of float]
            List of six ``[x, y, z]`` positions of the bounding box containing
            Xmin, Ymin, Zmin, Xmax, Ymax, and Zmax values.

        """
        objs_to_unmodel = [
            val.name for i, val in self._primitives.objects.items() if val.model and val.name != self.name
        ]
        if objs_to_unmodel:
            vArg1 = ["NAME:Model", "Value:=", False]
            self._primitives._change_geometry_property(vArg1, objs_to_unmodel)
        modeled = True
        if not self.model:
            vArg1 = ["NAME:Model", "Value:=", True]
            self._primitives._change_geometry_property(vArg1, self.name)
            modeled = False
        bounding = self._primitives.get_model_bounding_box()
        if objs_to_unmodel:
            self._odesign.Undo()
        if not modeled:
            self._odesign.Undo()
        if not settings.non_graphical:
            self._primitives._app.odesktop.ClearMessages(
                self._primitives._app.project_name, self._primitives._app.design_name, 1
            )
        return bounding

    @pyaedt_function_handler()
    def _bounding_box_sat(self):
        """Bounding box of a part.

        This is done by exporting a part as a SAT file and reading the bounding box information from the SAT file.
        A list of six 3D position vectors is returned.

        Returns
        -------
        list of [list of float]
            List of six ``[x, y, z]`` positions of the bounding box containing
            Xmin, Ymin, Zmin, Xmax, Ymax, and Zmax values.

        References
        ----------

        >>> oEditor.GetModelBoundingBox

        """
        tmp_path = self._primitives._app.working_directory
        filename = os.path.join(tmp_path, self.name + ".sat")

        self._primitives._app.export_3d_model(self.name, tmp_path, ".sat", [self.name])

        if not os.path.isfile(filename):
            raise Exception("Cannot export the ACIS SAT file for object {}".format(self.name))

        with open_file(filename, "r") as fh:
            temp = fh.read().splitlines()
        all_lines = [s for s in temp if s.startswith("body ")]

        bb = []
        if len(all_lines) == 1:
            line = all_lines[0]
            pattern = r".+ (.+) (.+) (.+) (.+) (.+) (.+) #$"
            m = re.search(pattern, line)
            if m:
                try:
                    for i in range(1, 7):
                        bb.append(float(m.group(i)))
                except:
                    return False
            else:
                return False
        else:
            return False

        try:
            os.remove(filename)
        except:
            self.logger.warning("ERROR: Cannot remove temp file.")
        return bb

    @property
    def bounding_box(self):
        """Bounding box of a part.

        A list of six 3D position vectors is returned.

        Returns
        -------
        list of [list of float]
            List of six ``[x, y, z]`` positions of the bounding box containing
            Xmin, Ymin, Zmin, Xmax, Ymax, and Zmax values.

        References
        ----------

        >>> oEditor.GetModelBoundingBox

        """
        if self.object_type == "Unclassified":
            return [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        if not settings.disable_bounding_box_sat:
            bounding = self._bounding_box_sat()
            if bounding:
                return bounding
            else:
                return self._bounding_box_unmodel()
        else:
            return self._bounding_box_unmodel()

    @property
    def bounding_dimension(self):
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
        oBoundingBox = self.bounding_box
        dimensions = []
        dimensions.append(abs(float(oBoundingBox[0]) - float(oBoundingBox[3])))
        dimensions.append(abs(float(oBoundingBox[1]) - float(oBoundingBox[4])))
        dimensions.append(abs(float(oBoundingBox[2]) - float(oBoundingBox[5])))
        return dimensions

    @property
    def _odesign(self):
        """Design."""
        return self._primitives._modeler._app._odesign

    @pyaedt_function_handler()
    def plot(self, show=True):
        """Plot model with PyVista.

        Parameters
        ----------
        show : bool, optional
            Show the plot after generation.  The default value is ``True``.

        Returns
        -------
        :class:`pyaedt.generic.plot.ModelPlotter`
            Model Object.

        Notes
        -----
        Works from AEDT 2021.2 in CPython only. PyVista has to be installed.
        """
        if not is_ironpython and self._primitives._app._aedt_version >= "2021.2":
            return self._primitives._app.post.plot_model_obj(
                objects=[self.name],
                plot_as_separate_objects=True,
                plot_air_objects=True,
                show=show,
            )

    @pyaedt_function_handler()
    def export_image(self, file_path=None):

        """Export the model to path.

        .. note::
           Works from AEDT 2021.2 in CPython only. PyVista has to be installed.

        Parameters
        ----------
        file_path : str, optional
            File name with full path. If `None` Project directory will be used.

        Returns
        -------
        str
            File path.
        """
        if not is_ironpython and self._primitives._app._aedt_version >= "2021.2":
            if not file_path:
                file_path = os.path.join(self._primitives._app.working_directory, self.name + ".png")
            model_obj = self._primitives._app.post.plot_model_obj(
                objects=[self.name],
                show=False,
                export_path=file_path,
                plot_as_separate_objects=True,
                clean_files=True,
            )
            if model_obj:
                return model_obj.image_file
        return False

    @property
    def touching_objects(self):
        """Get the objects that touch one of the vertex, edge midpoint or face of the object."""
        if self.object_type == "Unclassified":
            return []
        list_names = []
        for vertex in self.vertices:
            body_names = self._primitives.get_bodynames_from_position(vertex.position)
            a = [i for i in body_names if i != self.name and i not in list_names]
            if a:
                list_names.extend(a)
        for edge in self.edges:
            body_names = self._primitives.get_bodynames_from_position(edge.midpoint)
            a = [i for i in body_names if i != self.name and i not in list_names]
            if a:
                list_names.extend(a)
        for face in self.faces:
            body_names = self._primitives.get_bodynames_from_position(face.center)
            a = [i for i in body_names if i != self.name and i not in list_names]
            if a:
                list_names.extend(a)
        return list_names

    @pyaedt_function_handler()
    def get_touching_faces(self, object_name):
        """Get the objects that touch one of the face center of each face of the object.

        Parameters
        ----------
        object_name : str, :class:`Object3d`
            Object to check.
        Returns
        -------
        list
            list of objects and faces touching."""

        _names = []
        if isinstance(object_name, Object3d):
            object_name = object_name.name
        for face in self.faces:
            body_names = self._primitives.get_bodynames_from_position(face.center)
            if object_name in body_names:
                _names.append(face)
        return _names

    @property
    def faces(self):
        """Information for each face in the given part.

        Returns
        -------
        list of :class:`pyaedt.modeler.elements3d.FacePrimitive`

        References
        ----------

        >>> oEditor.GetFaceIDs

        """
        if self.object_type == "Unclassified":
            return []
        faces = []
        for face in list(self.m_Editor.GetFaceIDs(self.name)):
            face = int(face)
            faces.append(FacePrimitive(self, face))
        return faces

    @property
    def faces_on_bounding_box(self):
        """Return only the face ids of the faces touching the bounding box.

        Returns
        -------
        List of :class:`pyaedt.modeler.Object3d.FacePrimitive`
        """
        f_list = []
        for face in self.faces:
            if face.is_on_bounding():
                f_list.append(face)
        return f_list

    @property
    def face_closest_to_bounding_box(self):
        """Return only the face ids of the face closest to the bounding box.

        Returns
        -------
        :class:`pyaedt.modeler.elements3d.FacePrimitive`
        """
        b = [float(i) for i in list(self.m_Editor.GetModelBoundingBox())]
        f_id = None
        f_val = None
        for face in self.faces:
            c = face.center
            p_dist = min(
                [
                    abs(c[0] - b[0]),
                    abs(c[1] - b[1]),
                    abs(c[2] - b[2]),
                    abs(c[0] - b[3]),
                    abs(c[1] - b[4]),
                    abs(c[2] - b[5]),
                ]
            )

            if f_val and p_dist < f_val or not f_val:
                f_id = face
                f_val = p_dist
        return f_id

    @pyaedt_function_handler()
    def largest_face(self, n=1):
        """Return only the face with the greatest area.

        Returns
        -------
        List of :class:`pyaedt.modeler.Object3d.FacePrimitive`
        """
        f = []
        for face in self.faces:
            f.append((face.area, face))
        f.sort(key=lambda tup: tup[0], reverse=True)
        f_sorted = [x for y, x in f]
        return f_sorted[:n]

    @pyaedt_function_handler()
    def longest_edge(self, n=1):
        """Return only the edge with the greatest length.

        Returns
        -------
        List of :class:`pyaedt.modeler.Object3d.EdgePrimitive`
        """
        e = []
        for edge in self.edges:
            e.append((edge.length, edge))
        e.sort(key=lambda tup: tup[0], reverse=True)
        e_sorted = [x for y, x in e]
        return e_sorted[:n]

    @pyaedt_function_handler()
    def smallest_face(self, n=1):
        """Return only the face with the smallest area.

        Returns
        -------
        List of :class:`pyaedt.modeler.Object3d.FacePrimitive`
        """
        f = []
        for face in self.faces:
            f.append((face.area, face))
        f.sort(key=lambda tup: tup[0])
        f_sorted = [x for y, x in f]
        return f_sorted[:n]

    @pyaedt_function_handler()
    def shortest_edge(self, n=1):
        """Return only the edge with the smallest length.

        Returns
        -------
        List of :class:`pyaedt.modeler.Object3d.EdgePrimitive`
        """
        e = []
        for edge in self.edges:
            e.append((edge.length, edge))
        e.sort(
            key=lambda tup: tup[0],
        )
        e_sorted = [x for y, x in e]
        return e_sorted[:n]

    @property
    def top_face_z(self):
        """Top face in the Z direction of the object.

        Returns
        -------
        :class:`pyaedt.modeler.elements3d.FacePrimitive`

        References
        ----------

        >>> oEditor.FaceCenter

        """
        try:
            result = [(float(face.center[2]), face) for face in self.faces]
            result = sorted(result, key=lambda tup: tup[0])
            return result[-1][1]
        except:
            return None

    @property
    def bottom_face_z(self):
        """Bottom face in the Z direction of the object.

        Returns
        -------
        :class:`pyaedt.modeler.elements3d.FacePrimitive`

        References
        ----------

        >>> oEditor.FaceCenter

        """
        try:
            result = [(float(face.center[2]), face) for face in self.faces]
            result = sorted(result, key=lambda tup: tup[0])
            return result[0][1]
        except:
            return None

    @property
    def top_face_x(self):
        """Top face in the X direction of the object.

        Returns
        -------
        :class:`pyaedt.modeler.elements3d.FacePrimitive`

        References
        ----------

        >>> oEditor.FaceCenter

        """
        try:
            result = [(float(face.center[0]), face) for face in self.faces]
            result = sorted(result, key=lambda tup: tup[0])
            return result[-1][1]
        except:
            return None

    @property
    def bottom_face_x(self):
        """Bottom face in the X direction of the object.

        Returns
        -------
        :class:`pyaedt.modeler.elements3d.FacePrimitive`

        References
        ----------

        >>> oEditor.FaceCenter

        """
        try:
            result = [(float(face.center[0]), face) for face in self.faces]
            result = sorted(result, key=lambda tup: tup[0])
            return result[0][1]
        except:
            return None

    @property
    def top_face_y(self):
        """Top face in the Y direction of the object.

        Returns
        -------
        :class:`pyaedt.modeler.elements3d.FacePrimitive`

        References
        ----------

        >>> oEditor.FaceCenter

        """
        try:
            result = [(float(face.center[1]), face) for face in self.faces]
            result = sorted(result, key=lambda tup: tup[0])
            return result[-1][1]
        except:
            return None

    @property
    def bottom_face_y(self):
        """Bottom face in the X direction of the object.

        Returns
        -------
        :class:`pyaedt.modeler.elements3d.FacePrimitive`

        References
        ----------

        >>> oEditor.FaceCenter

        """
        try:
            result = [(float(face.center[1]), face) for face in self.faces]
            result = sorted(result, key=lambda tup: tup[0])
            return result[0][1]
        except:
            return None

    @property
    def top_edge_z(self):
        """Top edge in the Z direction of the object. Midpoint is used as criteria to find the edge.

        Returns
        -------
        :class:`pyaedt.modeler.elements3d.EdgePrimitive`

        References
        ----------

        >>> oEditor.FaceCenter

        """
        try:
            result = [(float(face.top_edge_z.midpoint[2]), face.top_edge_z) for face in self.faces]
            result = sorted(result, key=lambda tup: tup[0])
            return result[-1][1]
        except:
            return None

    @property
    def bottom_edge_z(self):
        """Bottom edge in the Z direction of the object. Midpoint is used as criteria to find the edge.

        Returns
        -------
        :class:`pyaedt.modeler.elements3d.EdgePrimitive`

        """
        try:
            result = [(float(face.bottom_edge_z.midpoint[2]), face.bottom_edge_z) for face in self.faces]
            result = sorted(result, key=lambda tup: tup[0])
            return result[0][1]
        except:
            return None

    @property
    def top_edge_x(self):
        """Top edge in the X direction of the object. Midpoint is used as criteria to find the edge.

        Returns
        -------
        :class:`pyaedt.modeler.elements3d.EdgePrimitive`

        """
        try:
            result = [(float(face.top_edge_x.midpoint[0]), face.top_edge_x) for face in self.faces]
            result = sorted(result, key=lambda tup: tup[0])
            return result[-1][1]
        except:
            return None

    @property
    def bottom_edge_x(self):
        """Bottom edge in the X direction of the object. Midpoint is used as criteria to find the edge.

        Returns
        -------
        :class:`pyaedt.modeler.elements3d.EdgePrimitive`

        """
        try:
            result = [(float(face.bottom_edge_x.midpoint[0]), face.bottom_edge_x) for face in self.faces]
            result = sorted(result, key=lambda tup: tup[0])
            return result[0][1]
        except:
            return None

    @property
    def top_edge_y(self):
        """Top edge in the Y direction of the object. Midpoint is used as criteria to find the edge.

        Returns
        -------
        :class:`pyaedt.modeler.elements3d.EdgePrimitive`

        """
        try:
            result = [(float(face.top_edge_y.midpoint[1]), face.top_edge_y) for face in self.faces]
            result = sorted(result, key=lambda tup: tup[0])
            return result[-1][1]
        except:
            return None

    @property
    def bottom_edge_y(self):
        """Bottom edge in the X direction of the object. Midpoint is used as criteria to find the edge.

        Returns
        -------
        :class:`pyaedt.modeler.elements3d.EdgePrimitive`

        """
        try:
            result = [(float(face.bottom_edge_y.midpoint[1]), face.bottom_edge_y) for face in self.faces]
            result = sorted(result, key=lambda tup: tup[0])
            return result[0][1]
        except:
            return None

    @property
    def edges(self):
        """Information for each edge in the given part.

        Returns
        -------
        list of :class:`pyaedt.modeler.elements3d.EdgePrimitive`

        References
        ----------

        >>> oEditor.GetEdgeIDsFromObject

        """
        if self.object_type == "Unclassified":
            return []
        edges = []
        for edge in self._primitives.get_object_edges(self.name):
            edge = int(edge)
            edges.append(EdgePrimitive(self, edge))
        return edges

    @property
    def vertices(self):
        """Information for each vertex in the given part.

        Returns
        -------
        list of :class:`pyaedt.modeler.elements3d.VertexPrimitive`

        References
        ----------

        >>> oEditor.GetVertexIDsFromObject

        """
        if self.object_type == "Unclassified":
            return []
        vertices = []
        v = [i for i in self._primitives.get_object_vertices(self.name)]
        if settings.aedt_version > "2022.2":
            v = v[::-1]
        for vertex in v:
            vertex = int(vertex)
            vertices.append(VertexPrimitive(self, vertex))
        return vertices

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
    def surface_material_name(self):
        """Surface material name of the object.

        Returns
        -------
        str or None
            Name of the surface material when successful, ``None`` and a warning message otherwise.

        References
        ----------

        >>> oEditor.GetPropertyValue
        >>> oEditor.ChangeProperty

        """
        if self._surface_material is not None:
            return self._surface_material
        if "Surface Material" in self.valid_properties and self.model:
            self._surface_material = _retry_ntimes(
                10, self.m_Editor.GetPropertyValue, "Geometry3DAttributeTab", self._m_name, "Surface Material"
            )
            return self._surface_material.strip('"')

    @property
    def group_name(self):
        """Group the object belongs to.

        Returns
        -------
        str
            Name of the group.

        References
        ----------

        >>> oEditor.GetPropertyValue
        >>> oEditor.ChangeProperty

        """
        if self._m_groupName is not None:
            return self._m_groupName
        if "Group" in self.valid_properties:
            self._m_groupName = _retry_ntimes(
                10, self.m_Editor.GetPropertyValue, "Geometry3DAttributeTab", self._m_name, "Group"
            )
            return self._m_groupName

    @group_name.setter
    def group_name(self, name):
        """Assign Object to a specific group. it creates a new group if the group doesn't exist.

        Parameters
        ----------
        name : str
            Name of the group to assign. Group will be created if it does not exist.

        Returns
        -------
        str
            Name of the group.

        References
        ----------

        >>> oEditor.GetPropertyValue
        >>> oEditor.ChangeProperty

        """

        if not list(self.m_Editor.GetObjectsInGroup(name)):
            self.m_Editor.CreateGroup(
                [
                    "NAME:GroupParameter",
                    "ParentGroupID:=",
                    "Model",
                    "Parts:=",
                    self._m_name,
                    "SubmodelInstances:=",
                    "",
                    "Groups:=",
                    "",
                ]
            )
            groupName = _retry_ntimes(
                10, self.m_Editor.GetPropertyValue, "Geometry3DAttributeTab", self._m_name, "Group"
            )
            self.m_Editor.ChangeProperty(
                [
                    "NAME:AllTabs",
                    [
                        "NAME:Attributes",
                        ["NAME:PropServers", groupName],
                        ["NAME:ChangedProps", ["NAME:Name", "Value:=", name]],
                    ],
                ]
            )
            self._m_groupName = name
        else:
            vgroup = ["NAME:Group", "Value:=", name]
            self._change_property(vgroup)
            self._m_groupName = name

    @property
    def material_name(self):
        """Material name of the object.

        Returns
        -------
        str or None
            Name of the material when successful, ``None`` and a warning message otherwise.

        References
        ----------

        >>> oEditor.GetPropertyValue
        >>> oEditor.ChangeProperty

        """
        if self._material_name is not None:
            return self._material_name
        if "Material" in self.valid_properties and self.model:
            mat = _retry_ntimes(10, self.m_Editor.GetPropertyValue, "Geometry3DAttributeTab", self._m_name, "Material")
            self._material_name = ""
            if mat:
                self._material_name = mat.strip('"').lower()
            return self._material_name
        return ""

    @material_name.setter
    def material_name(self, mat):
        matobj = self._primitives._materials.checkifmaterialexists(mat)
        if matobj:
            if not self.model:
                self.model = True
            vMaterial = ["NAME:Material", "Value:=", chr(34) + matobj.name + chr(34)]
            self._change_property(vMaterial)
            self._material_name = matobj.name.lower()
            self._solve_inside = None
        else:
            self.logger.warning("Material %s does not exist.", mat)

    @surface_material_name.setter
    def surface_material_name(self, mat):
        try:
            if not self.model:
                self.model = True
            self._surface_material = mat
            vMaterial = ["NAME:Surface Material", "Value:=", '"' + mat + '"']
            self._change_property(vMaterial)
            self._surface_material = mat
        except:
            self.logger.warning("Material %s does not exist", mat)

    @property
    def id(self):
        """ID of the object.

        Returns
        -------
        int or None
            ID of the object when successful, ``None`` otherwise.

        References
        ----------

        >>> oEditor.GetObjectIDByName

        """
        if not self._id:
            try:
                self._id = self._primitives.oeditor.GetObjectIDByName(self._m_name)
            except:
                return None
        return self._id

    @property
    def object_type(self):
        """Type of the object.

        Options are:
             * Solid
             * Sheet
             * Line

        Returns
        -------
        str
            Type of the object.

        """
        if self._object_type:
            return self._object_type
        if self._m_name in list(self.m_Editor.GetObjectsInGroup("Solids")):
            self._object_type = "Solid"
        elif self._m_name in list(self.m_Editor.GetObjectsInGroup("Sheets")):
            self._object_type = "Sheet"
        elif self._m_name in list(self.m_Editor.GetObjectsInGroup("Lines")):
            self._object_type = "Line"
        elif self._m_name in list(self.m_Editor.GetObjectsInGroup("Unclassified")):  # pragma: no cover
            self._object_type = "Unclassified"  # pragma: no cover
        return self._object_type

    @property
    def is3d(self):
        """Check for if the object is 3D.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        if self.object_type == "Solid":
            return True
        else:
            return False

    @property
    def mass(self):
        """Object mass.

        Returns
        -------
        float or None
            Mass of the object when successful, 0.0 otherwise. Mass of the volume in kg since AEDT mass density is
            always in kg/m^3

        References
        ----------

        >>> oEditor.GetObjectVolume

        """
        if self.model and self.material_name:
            volume = self._primitives.oeditor.GetObjectVolume(self._m_name)
            units = self.object_units
            mass_density = (
                float(self._primitives._materials[self.material_name].mass_density.value)
                * float(volume)
                * float(AEDT_UNITS["Length"][str(units)]) ** 3
            )
            self._mass = mass_density
        else:
            self._mass = 0.0
        return self._mass

    @property
    def volume(self):
        """Object volume.

        Returns
        -------
        float
            Volume of the object when successful, 0.0 otherwise.

        References
        ----------

        >>> oEditor.GetObjectVolume

        """
        if self.object_type == "Solid":
            self._volume = float(self._primitives.oeditor.GetObjectVolume(self._m_name))
        else:
            self._volume = 0.0
        return self._volume

    @property
    def name(self):
        """Name of the object as a string value.

        Returns
        -------
        str
           Name of object as a string value.

        References
        ----------

        >>> oEditor.GetPropertyValue
        >>> oEditor.ChangeProperty

        """
        return self._m_name

    @name.setter
    def name(self, obj_name):
        if obj_name not in self._primitives.object_names:
            if obj_name != self._m_name:
                vName = []
                vName.append("NAME:Name")
                vName.append("Value:=")
                vName.append(obj_name)
                vChangedProps = ["NAME:ChangedProps", vName]
                vPropServers = ["NAME:PropServers"]
                vPropServers.append(self._m_name)
                vGeo3d = ["NAME:Geometry3DAttributeTab", vPropServers, vChangedProps]
                vOut = ["NAME:AllTabs", vGeo3d]
                _retry_ntimes(10, self._primitives.oeditor.ChangeProperty, vOut)
                self._m_name = obj_name
                self._primitives.cleanup_objects()
        else:
            pass

    @property
    def valid_properties(self):
        """Valid properties.

        References
        ----------

        >>> oEditor.GetProperties
        """
        if not self._all_props:
            self._all_props = _retry_ntimes(10, self.m_Editor.GetProperties, "Geometry3DAttributeTab", self._m_name)
        return self._all_props

    @property
    def color(self):
        """Part color as a tuple of integer values for `(Red, Green, Blue)` color values.

        If the integer values are outside the range 0-255, then limit the values. Invalid inputs are ignored.

        References
        ----------

        >>> oEditor.GetPropertyValue
        >>> oEditor.ChangeProperty

        Examples
        --------
        >>> part.color = (255,255,0)

        """
        if self._color is not None:
            return self._color
        if "Color" in self.valid_properties:
            color = _retry_ntimes(10, self.m_Editor.GetPropertyValue, "Geometry3DAttributeTab", self._m_name, "Color")
            if color:
                b = (int(color) >> 16) & 255
                g = (int(color) >> 8) & 255
                r = int(color) & 255
                self._color = (r, g, b)
            else:
                self._color = (0, 195, 255)
            return self._color

    @property
    def color_string(self):
        """Color tuple as a string in the format '(Red, Green, Blue)'.

        References
        ----------

        >>> oEditor.GetPropertyValue
        >>> oEditor.ChangeProperty
        """
        return "({} {} {})".format(self.color[0], self.color[1], self.color[2])

    @color.setter
    def color(self, color_value):
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
            msg_text = "Invalid color input {} for object {}.".format(color_value, self._m_name)
            self._primitives.logger.warning(msg_text)

    @property
    def transparency(self):
        """Part transparency as a value between 0.0 and 1.0.

        If the value is outside the range, then apply a limit. If the value is not a valid number, set to ``0.0``.

        References
        ----------

        >>> oEditor.GetPropertyValue
        >>> oEditor.ChangeProperty

        """
        if self._transparency is not None:
            return self._transparency
        if "Transparent" in self.valid_properties:
            transp = _retry_ntimes(
                10, self.m_Editor.GetPropertyValue, "Geometry3DAttributeTab", self._m_name, "Transparent"
            )
            try:
                self._transparency = float(transp)
            except:
                self._transparency = 0.3
            return self._transparency

    @transparency.setter
    def transparency(self, T):
        try:
            trans_float = float(T)
            if trans_float < 0.0:
                trans_float = 0.0
            elif trans_float > 1.0:
                trans_float = 1.0
        except ValueError:
            trans_float = 0.0
        vTrans = ["NAME:Transparent", "Value:=", str(trans_float)]

        self._change_property(vTrans)

        self._transparency = trans_float

    @property
    def object_units(self):
        """Object units."""
        return self._primitives.model_units

    @property
    def part_coordinate_system(self):
        """Part coordinate system.

        Returns
        -------
        str
            Name of the part coordinate system.

        References
        ----------

        >>> oEditor.GetPropertyValue
        >>> oEditor.ChangeProperty

        """
        if self._part_coordinate_system is not None and not isinstance(self._part_coordinate_system, int):
            return self._part_coordinate_system
        if "Orientation" in self.valid_properties:
            self._part_coordinate_system = _retry_ntimes(
                10, self.m_Editor.GetPropertyValue, "Geometry3DAttributeTab", self._m_name, "Orientation"
            )
            return self._part_coordinate_system

    @part_coordinate_system.setter
    def part_coordinate_system(self, sCS):

        pcs = ["NAME:Orientation", "Value:=", sCS]
        self._change_property(pcs)
        self._part_coordinate_system = sCS
        return True

    @property
    def solve_inside(self):
        """Part solve inside flag.

        Returns
        -------
        bool
            ``True`` when ``"solve-inside"`` is activated for the part, ``False`` otherwise.

        References
        ----------

        >>> oEditor.GetPropertyValue
        >>> oEditor.ChangeProperty

        """
        if self._solve_inside is not None:
            return self._solve_inside
        if "Solve Inside" in self.valid_properties and self.model:
            solveinside = _retry_ntimes(
                10, self.m_Editor.GetPropertyValue, "Geometry3DAttributeTab", self._m_name, "Solve Inside"
            )
            if solveinside == "false" or solveinside == "False":
                self._solve_inside = False
            else:
                self._solve_inside = True
            return self._solve_inside
        return None

    @solve_inside.setter
    def solve_inside(self, S):
        if not self.model:
            self.model = True
        vSolveInside = []
        # fS = self._to_boolean(S)
        fs = S
        vSolveInside.append("NAME:Solve Inside")
        vSolveInside.append("Value:=")
        vSolveInside.append(fs)
        self._change_property(vSolveInside)
        self._solve_inside = fs

    @property
    def display_wireframe(self):
        """Wireframe property of the part.

        Returns
        -------
        bool
            ``True`` when wirefame is activated for the part, ``False`` otherwise.

        References
        ----------

        >>> oEditor.GetPropertyValue
        >>> oEditor.ChangeProperty

        """
        if self._wireframe is not None:
            return self._wireframe
        if "Display Wireframe" in self.valid_properties:
            wireframe = _retry_ntimes(
                10, self.m_Editor.GetPropertyValue, "Geometry3DAttributeTab", self._m_name, "Display Wireframe"
            )
            if wireframe == "true" or wireframe == "True":
                self._wireframe = True
            else:
                self._wireframe = False
            return self._wireframe

    @display_wireframe.setter
    def display_wireframe(self, fWireframe):
        vWireframe = ["NAME:Display Wireframe", "Value:=", fWireframe]
        # fwf = self._to_boolean(wf)

        self._change_property(vWireframe)
        self._wireframe = fWireframe

    @property
    def history(self):
        """Object history.

        Returns
        -------
            :class:`pyaedt.modeler.cad.elements3d.BinaryTree` when successful,
            ``False`` when failed.

        """
        try:
            child_object = self.m_Editor.GetChildObject(self.name)
            parent = BinaryTreeNode(self.name, child_object, True)
            return parent
        except:
            return False

    @property
    def model(self):
        """Part model or non-model property.

        Returns
        -------
        bool
            ``True`` when model, ``False`` otherwise.

        References
        ----------

        >>> oEditor.GetPropertyValue
        >>> oEditor.ChangeProperty

        """
        if self._model is not None:
            return self._model
        if "Model" in self.valid_properties:
            mod = _retry_ntimes(10, self.m_Editor.GetPropertyValue, "Geometry3DAttributeTab", self._m_name, "Model")
            if mod == "false" or mod == "False":
                self._model = False
            else:
                self._model = True
            return self._model

    @model.setter
    def model(self, fModel):
        vArg1 = ["NAME:Model", "Value:=", fModel]
        fModel = _to_boolean(fModel)
        self._change_property(vArg1)
        self._model = fModel

    @pyaedt_function_handler()
    def unite(self, object_list):
        """Unite a list of objects with this object.

        Parameters
        ----------
        object_list : list of str or list of pyaedt.modeler.object3d.Object3d
            List of objects.

        Returns
        -------
        pyaedt.modeler.object3d.Object3d
           Object 3D object.

        References
        ----------

        >>> oEditor.Unite

        """
        unite_list = [self.name] + self._primitives.modeler.convert_to_selections(object_list, return_list=True)
        self._primitives.modeler.unite(unite_list)
        return self

    @pyaedt_function_handler()
    def intersect(self, theList, keep_originals=False):
        """Intersect the active object with a given list.

        Parameters
        ----------
        theList : list
            List of objects.
        keep_originals : bool, optional
            Whether to keep the original object. The default is ``False``.

        Returns
        -------
        :class:`pyaedt.modeler.object3d.Object3d`
            Retrieve the resulting 3D Object when succeeded.

        References
        ----------

        >>> oEditor.Intersect
        """
        theList = [self.name] + self._primitives.modeler.convert_to_selections(theList, return_list=True)
        self._primitives.modeler.intersect(theList, keep_originals)
        return self

    @pyaedt_function_handler()
    def split(self, plane, sides="Both"):
        """Split the active object.

        Parameters
        ----------
        plane : str
            Coordinate plane of the cut or the Application.PLANE object.
            Choices for the coordinate plane are ``"XY"``, ``"YZ"``, and ``"ZX"``.
        sides : str, optional
            Which side to keep. Options are ``"Both"``, ``"PositiveOnly"``,
            and ``"NegativeOnly"``. The default is ``"Both"``, in which case
            all objects are kept after the split.

        Returns
        -------
        list of str
            List of split objects.

        References
        ----------

        >>> oEditor.Split
        """
        return self._primitives.modeler.split(self.name, plane, sides)

    @pyaedt_function_handler()
    def mirror(self, position, vector):
        """Mirror a selection.

        Parameters
        ----------
        position : int or float
            List of the ``[x, y, z]`` coordinates or
            the Application.Position object for the selection.
        vector : float
            List of the ``[x1, y1, z1]`` coordinates or
            the Application.Position object for the vector.

        Returns
        -------
        pyaedt.modeler.Object3d.Object3d, bool
            3D object.
            ``False`` when failed.

        References
        ----------

        >>> oEditor.Mirror
        """
        if self._primitives.modeler.mirror(self.id, position=position, vector=vector):
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
        pyaedt.modeler.Object3d.Object3d, bool
            3D object.
            ``False`` when failed.

        References
        ----------

        >>> oEditor.Rotate
        """
        if self._primitives.modeler.rotate(self.id, cs_axis=cs_axis, angle=angle, unit=unit):
            return self
        return False

    @pyaedt_function_handler()
    def move(self, vector):
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
        pyaedt.modeler.Object3d.Object3d, bool
            3D object.
            ``False`` when failed.

        References
        ----------
        >>> oEditor.Move
        """
        if self._primitives.modeler.move(self.id, vector=vector):
            return self
        return False

    def duplicate_around_axis(self, cs_axis, angle=90, nclones=2, create_new_objects=True):
        """Duplicate the object around the axis.

        Parameters
        ----------
        cs_axis : Application.CoordinateSystemAxis object
            Coordinate system axis of the object.
        angle : float
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
        ret, added_objects = self._primitives.modeler.duplicate_around_axis(
            self, cs_axis, angle, nclones, create_new_objects
        )
        return added_objects

    @pyaedt_function_handler()
    def duplicate_along_line(self, vector, nclones=2, attachObject=False):
        """Duplicate the object along a line.

        Parameters
        ----------
        vector : list
            List of ``[x1 ,y1, z1]`` coordinates for the vector or the Application.Position object.
        nclones : int, optional
            Number of clones. The default is ``2``.
        attachObject : bool, optional
            Whether to attach the object. The default is ``False``.

        Returns
        -------
        list
            List of names of the newly added objects.

        References
        ----------

        >>> oEditor.DuplicateAlongLine

        """
        ret, added_objects = self._primitives.modeler.duplicate_along_line(self, vector, nclones, attachObject)
        return added_objects

    @pyaedt_function_handler()
    def translate(self, vector):
        """Translate the object and return the 3D object.

        .. deprecated:: 0.4.0
           Use :func:`move` instead.

        Returns
        -------
        pyaedt.modeler.object3d.Object3d
            3D object.

        References
        ----------

        >>> oEditor.Move

        """
        warnings.warn("`translate` is deprecated. Use `move` instead.", DeprecationWarning)
        self.move(vector)
        return self

    @pyaedt_function_handler()
    def sweep_along_vector(self, sweep_vector, draft_angle=0, draft_type="Round"):
        """Sweep the selection along a vector.

        Parameters
        ----------
        sweep_vector : list
            Application.Position object.
        draft_angle : float, optional
            Angle of the draft in degrees. The default is ``0``.
        draft_type : str, optional
            Type of the draft. Options are ``"Extended"``, ``"Round"``,
            and ``"Natural"``. The default value is ``"Round``.

        Returns
        -------
        bool
            ``True`` when model, ``False`` otherwise.

        References
        ----------

        >>> oEditor.SweepAlongVector

        """
        self._primitives.modeler.sweep_along_vector(self, sweep_vector, draft_angle, draft_type)
        return self

    @pyaedt_function_handler()
    def sweep_along_path(
        self, sweep_object, draft_angle=0, draft_type="Round", is_check_face_intersection=False, twist_angle=0
    ):
        """Sweep the selection along a vector.

        Parameters
        ----------
        sweep_object : :class:`pyaedt.modeler.object3d.Object3d`
            Application.Position object.
        draft_angle : float, optional
            Angle of the draft in degrees. The default is ``0``.
        draft_type : str
            Type of the draft. Options are ``"Extended"``, ``"Round"``,
            and ``"Natural"``. The default is ``"Round``.
        is_check_face_intersection : bool, optional
           The default value is ``False``.
        twist_angle : float, optional
            Angle at which to twist or rotate in degrees. The default value is ``0``.

        Returns
        -------
        pyaedt.modeler.object3d.Object3d
            Swept object.

        References
        ----------

        >>> oEditor.SweepAlongPath

        """
        self._primitives.modeler.sweep_along_path(
            self, sweep_object, draft_angle, draft_type, is_check_face_intersection, twist_angle
        )
        return self

    @pyaedt_function_handler()
    def sweep_around_axis(self, cs_axis, sweep_angle=360, draft_angle=0):
        """Sweep around an axis.

        Parameters
        ----------
        cs_axis : :class:`pyaedt.generic.constants.CoordinateSystemAxis`
            Coordinate system of the axis.
        sweep_angle : float, optional
             Sweep angle in degrees. The default is ``360``.
        draft_angle : float, optional
            Angle of the draft. The default is ``0``.

        Returns
        -------
        pyaedt.modeler.object3d.Object3d
            Swept object.

        References
        ----------

        >>> oEditor.SweepAroundAxis

        """
        self._primitives.modeler.sweep_around_axis(self, cs_axis, sweep_angle, draft_angle)
        return self

    @pyaedt_function_handler()
    def section(self, plane, create_new=True, section_cross_object=False):
        """Section the object.

        Parameters
        ----------
        plane : pyaedt.generic.constants.PLANE
            Coordinate system of the plane object. Application.PLANE object
        create_new : bool, optional
            Whether to create an object. The default is ``True``.
        section_cross_object : bool, optional
            The default is ``False``.

        Returns
        -------
        pyaedt.modeler.object3d.Object3d
            3D object.

        References
        ----------

        >>> oEditor.Section

        """
        self._primitives.modeler.section(self, plane, create_new, section_cross_object)
        return self

    @pyaedt_function_handler()
    def clone(self):
        """Clone the object and return the new 3D object.

        Returns
        -------
        pyaedt.modeler.object3d.Object3d
            3D object that was added.

        References
        ----------

        >>> oEditor.Clone

        """
        new_obj_tuple = self._primitives.modeler.clone(self.id)
        success = new_obj_tuple[0]
        assert success, "Could not clone the object {}.".format(self.name)
        new_name = new_obj_tuple[1][0]
        return self._primitives[new_name]

    @pyaedt_function_handler()
    def subtract(self, tool_list, keep_originals=True):
        """Subtract one or more parts from the object.

        Parameters
        ----------
        tool_list : str, Object3d, or list of str and Object3d.
            List of parts to subtract from this part.
        keep_originals : bool, optional
            Whether to keep the tool parts after subtraction. The default
            is ``True``. If ``False``, the parts are deleted.

        Returns
        -------
        pyaedt.modeler.object3d.Object3d
            Modified 3D object following the subtraction.

        References
        ----------

        >>> oEditor.Subtract

        """
        self._primitives.modeler.subtract(self.name, tool_list, keep_originals)
        return self

    @pyaedt_function_handler()
    def wrap_sheet(self, object_name, imprinted=False):
        """Execute the sheet wrapping around an object. This object can be either the sheet or the object.
        If wrapping produces an unclassified operation it will be reverted.

        Parameters
        ----------
        object_name : str, :class:`pyaedt.modeler.Object3d.Object3d`
            Object name or solid object or sheet name.
        imprinted : bool, optional
            Either if imprint or not over the sheet. Default is `False`.

        Returns
        -------
        bool
            Command execution status.
        """
        object_name = self._primitives.convert_to_selections(object_name, False)
        if self.object_type == "Sheet" and object_name in self._primitives.solid_names:
            return self._primitives.wrap_sheet(self.name, object_name, imprinted)
        elif self.object_type == "Solid" and object_name in self._primitives.sheet_names:
            return self._primitives.wrap_sheet(object_name, self.name, imprinted)
        else:
            msg = "Error in command execution."
            msg += " Either one of the two objects has to be a sheet and the other an object."
            self.logger.error(msg)
            return False

    @pyaedt_function_handler()
    def delete(self):
        """Delete the object.

        References
        ----------

        >>> oEditor.Delete
        """
        arg = ["NAME:Selections", "Selections:=", self._m_name]
        self.m_Editor.Delete(arg)
        self._primitives.cleanup_objects()
        self.__dict__ = {}

    @pyaedt_function_handler()
    def faces_by_area(self, area, area_filter="==", tolerance=1e-12):
        """Filter faces by area.

        Parameters
        ----------
        area : float
            Value of the area to filter in model units.
        area_filter : str, optional
            Comparer symbol.
            Default value is "==".
        tolerance : float, optional
            tolerance for comparison.

        Returns
        -------
        list of :class:`pyaedt.modeler.elements3d.FacePrimitive`
            List of face primitives.
        """

        filters = ["==", "<=", ">=", "<", ">"]
        if area_filter not in filters:
            raise ValueError('Symbol not valid, enter one of the following: "==", "<=", ">=", "<", ">"')

        faces = []
        for face in self.faces:
            if area_filter == "==":
                if abs(face.area - area) < tolerance:
                    faces.append(face)
            if area_filter == ">=":
                if (face.area - area) >= -tolerance:
                    faces.append(face)
            if area_filter == "<=":
                if (face.area - area) <= tolerance:
                    faces.append(face)
            if area_filter == ">":
                if (face.area - area) > 0:
                    faces.append(face)
            if area_filter == "<":
                if (face.area - area) < 0:
                    faces.append(face)

        return faces

    @pyaedt_function_handler()
    def edges_by_length(self, length, length_filter="==", tolerance=1e-12):
        """Filter edges by length.

        Parameters
        ----------
        length : float
            Value of the length to filter.
        length_filter : str, optional
            Comparer symbol.
            Default value is "==".
        tolerance : float, optional
            tolerance for comparison.

        Returns
        -------
        list of :class:`pyaedt.modeler.elements3d.EdgePrimitive`
            List of edge primitives.
        """
        filters = ["==", "<=", ">=", "<", ">"]
        if length_filter not in filters:
            raise ValueError('Symbol not valid, enter one of the following: "==", "<=", ">=", "<", ">"')

        edges = []
        for edge in self.edges:
            if length_filter == "==":
                if abs(edge.length - length) < tolerance:
                    edges.append(edge)
            if length_filter == ">=":
                if (edge.length - length) >= -tolerance:
                    edges.append(edge)
            if length_filter == "<=":
                if (edge.length - length) <= tolerance:
                    edges.append(edge)
            if length_filter == ">":
                if (edge.length - length) > 0:
                    edges.append(edge)
            if length_filter == "<":
                if (edge.length - length) < 0:
                    edges.append(edge)

        return edges

    @pyaedt_function_handler()
    def _change_property(self, vPropChange):
        return self._primitives._change_geometry_property(vPropChange, self._m_name)

    def _update(self):
        # self._object3d._refresh_object_types()
        self._primitives.cleanup_objects()

    def __str__(self):
        return """
         {}
         name: {}    id: {}    object_type: {}
         --- read/write properties  ----
         solve_inside: {}
         model: {}
         material_name: {}
         color: {}
         transparency: {}
         display_wireframe {}
         part_coordinate_system: {}
         """.format(
            type(self),
            self.name,
            self.id,
            self.object_type,
            self.solve_inside,
            self.model,
            self.material_name,
            self.color,
            self.transparency,
            self.display_wireframe,
            self.part_coordinate_system,
        )
