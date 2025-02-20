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
This module contains these classes: `Components3DLayout`,`CircuitComponent',
`EdgePrimitive`, `EdgeTypePrimitive`, `FacePrimitive`, `Geometries3DLayout`,
`Nets3DLayout`, `Object3DLayout`, `Object3d`, `Padstack`, `PDSHole`, `PDSLayer`,
`Pins3DLayout', and `VertexPrimitive`.

This module provides methods and data structures for managing all properties of
objects (points, lines, sheets, and solids) within the AEDT 3D Modeler.

"""

import math
import os
import re

from ansys.aedt.core.application.variables import decompose_variable_value
from ansys.aedt.core.generic.checks import min_aedt_version
from ansys.aedt.core.generic.constants import AEDT_UNITS
from ansys.aedt.core.generic.constants import PLANE
from ansys.aedt.core.generic.constants import unit_converter
from ansys.aedt.core.generic.errors import AEDTRuntimeError
from ansys.aedt.core.generic.general_methods import _to_boolean
from ansys.aedt.core.generic.general_methods import _uname
from ansys.aedt.core.generic.general_methods import clamp
from ansys.aedt.core.generic.general_methods import open_file
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.generic.general_methods import rgb_color_codes
from ansys.aedt.core.generic.general_methods import settings
from ansys.aedt.core.modeler.cad.elements_3d import BinaryTreeNode
from ansys.aedt.core.modeler.cad.elements_3d import EdgePrimitive
from ansys.aedt.core.modeler.cad.elements_3d import FacePrimitive
from ansys.aedt.core.modeler.cad.elements_3d import VertexPrimitive
from ansys.aedt.core.modeler.geometry_operators import GeometryOperators


class Object3d(object):
    """Manages object attributes for the AEDT 3D Modeler.

    Parameters
    ----------
    primitives : :class:`ansys.aedt.core.modeler.cad.primitives_3d.Primitives3D`
        Inherited parent object.
    name : str

    Examples
    --------
    Basic usage demonstrated with an HFSS design:

    >>> from ansys.aedt.core import Hfss
    >>> aedtapp = Hfss()
    >>> prim = aedtapp.modeler

    Create a part, such as box, to return an :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`.

    >>> id = prim.create_box([0, 0, 0],[10, 10, 5],"Mybox","Copper")
    >>> part = prim[id]
    """

    def __init__(self, primitives, name=None):
        self._id = None
        self._positions = None
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
        self._material_appearance = None
        self._part_coordinate_system = None
        self._model = None
        self._m_groupName = None
        self._object_type = None
        self._mass = 0.0
        self._volume = 0.0
        self._faces = []
        self._face_ids = []
        self._is_polyline = None

    @property
    def is_polyline(self):
        """Get or set if the body is originated by a polyline.

        Returns
        -------
        bool
        """
        if self._is_polyline is None:
            hist = self.history()
            if hist.children and (hist.command == "CreatePolyline" or hist.properties.get("Segment Type", None)):
                self._is_polyline = True
            else:
                self._is_polyline = False
        return self._is_polyline

    @is_polyline.setter
    def is_polyline(self, value):
        self._is_polyline = value

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
        if not self._primitives._app.desktop_class.non_graphical:
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
            raise Exception(f"Cannot export the ACIS SAT file for object {self.name}")

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
                except Exception:
                    return False
            else:
                return False
        else:
            return False

        try:
            os.remove(filename)
        except Exception:
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
        if settings.aedt_version >= "2023.2":
            return [float(i) for i in self._oeditor.GetObjectBoundingBox(self.name)]
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
    @min_aedt_version("2021.2")
    def plot(self, show=True):
        """Plot model with PyVista.

        Parameters
        ----------
        show : bool, optional
            Show the plot after generation.  The default value is ``True``.

        Returns
        -------
        :class:`ansys.aedt.core.generic.plot.ModelPlotter`
            Model Object.

        Notes
        -----
        Works from AEDT 2021.2 in CPython only. PyVista has to be installed.
        """
        return self._primitives._app.post.plot_model_obj(
            objects=[self.name],
            plot_as_separate_objects=True,
            plot_air_objects=True,
            show=show,
        )

    @pyaedt_function_handler(file_path="output_file")
    @min_aedt_version("2021.2")
    def export_image(self, output_file=None):
        """Export the current object to a specified file path.

        .. note::
           Works from AEDT 2021.2 in CPython only. PyVista has to be installed.

        Parameters
        ----------
        output_file : str, optional
            File name with full path. If `None` the exported image will be a ``png`` file that
            will be saved in ``working_directory``.
            To access the ``working_directory`` the use ``app.working_directory`` property.

        Returns
        -------
        str
            File path.
        """
        if not output_file:
            output_file = os.path.join(self._primitives._app.working_directory, self.name + ".png")
        model_obj = self._primitives._app.post.plot_model_obj(
            objects=[self.name],
            show=False,
            export_path=output_file,
            plot_as_separate_objects=True,
            clean_files=True,
        )
        if model_obj:
            return model_obj.image_file

    @pyaedt_function_handler()
    def touching_conductors(self):
        """Get the conductors of given object.

        See :func:`ansys.aedt.core.application.analysis_3d.FieldAnalysis3D.identify_touching_conductors`.

        Returns
        -------
        list
            Name of all touching conductors.
        """
        return [i for i in self._primitives._app.identify_touching_conductors(self.name)["Net1"] if i != self.name]

    @property
    def touching_objects(self):
        """Get the objects that touch a vertex, edge midpoint, or face of the object."""
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

    @pyaedt_function_handler(object_name="assignment")
    def get_touching_faces(self, assignment):
        """Get the objects that touch one of the face center of each face of the object.

        Parameters
        ----------
        assignment : str, :class:`Object3d`
            Object to check.

        Returns
        -------
        list
            list of objects and faces touching.
        """
        _names = []
        if isinstance(assignment, Object3d):
            assignment = assignment.name
        for face in self.faces:
            body_names = self._primitives.get_bodynames_from_position(face.center)
            if assignment in body_names:
                _names.append(face)
        return _names

    @property
    def faces(self):
        """Information for each face in the given part.

        Returns
        -------
        list[:class:`ansys.aedt.core.modeler.cad.elements_3d.FacePrimitive`]

        References
        ----------
        >>> oEditor.GetFaceIDs

        """
        if self.object_type == "Unclassified":
            return []
        face_ids = list(self._oeditor.GetFaceIDs(self.name))
        if set(face_ids) == set(self._face_ids):
            return self._faces
        self._face_ids = face_ids
        self._faces = []
        for face in list(self._oeditor.GetFaceIDs(self.name)):
            face = int(face)
            self._faces.append(FacePrimitive(self, face))
        return self._faces

    @property
    def faces_on_bounding_box(self):
        """Return only the face ids of the faces touching the bounding box.

        Returns
        -------
        list[:class:`ansys.aedt.core.modeler.cad.elements_3d.FacePrimitive`]
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
        :class:`ansys.aedt.core.modeler.cad.elements_3d.FacePrimitive`
        """
        b = [float(i) for i in list(self._oeditor.GetModelBoundingBox())]
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
        list[:class:`ansys.aedt.core.modeler.cad.elements_3d.FacePrimitive`]
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
        list[:class:`ansys.aedt.core.modeler.cad.elements_3d.EdgePrimitive`]
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
        list[:class:`ansys.aedt.core.modeler.cad.elements_3d.FacePrimitive`]
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
        list[:class:`ansys.aedt.core.modeler.cad.elements_3d.EdgePrimitive`]
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
        :class:`ansys.aedt.core.modeler.cad.elements_3d.FacePrimitive`

        References
        ----------
        >>> oEditor.FaceCenter

        """
        try:
            result = [(float(face.center[2]), face) for face in self.faces]
            result = sorted(result, key=lambda tup: tup[0])
            return result[-1][1]
        except Exception:
            return None

    @property
    def bottom_face_z(self):
        """Bottom face in the Z direction of the object.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.elements_3d.FacePrimitive`

        References
        ----------
        >>> oEditor.FaceCenter

        """
        try:
            result = [(float(face.center[2]), face) for face in self.faces]
            result = sorted(result, key=lambda tup: tup[0])
            return result[0][1]
        except Exception:
            return None

    @property
    def top_face_x(self):
        """Top face in the X direction of the object.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.elements_3d.FacePrimitive`

        References
        ----------
        >>> oEditor.FaceCenter

        """
        try:
            result = [(float(face.center[0]), face) for face in self.faces]
            result = sorted(result, key=lambda tup: tup[0])
            return result[-1][1]
        except Exception:
            return None

    @property
    def bottom_face_x(self):
        """Bottom face in the X direction of the object.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.elements_3d.FacePrimitive`

        References
        ----------
        >>> oEditor.FaceCenter

        """
        try:
            result = [(float(face.center[0]), face) for face in self.faces]
            result = sorted(result, key=lambda tup: tup[0])
            return result[0][1]
        except Exception:
            return None

    @property
    def top_face_y(self):
        """Top face in the Y direction of the object.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.elements_3d.FacePrimitive`

        References
        ----------
        >>> oEditor.FaceCenter

        """
        try:
            result = [(float(face.center[1]), face) for face in self.faces]
            result = sorted(result, key=lambda tup: tup[0])
            return result[-1][1]
        except Exception:
            return None

    @property
    def bottom_face_y(self):
        """Bottom face in the X direction of the object.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.elements_3d.FacePrimitive`

        References
        ----------
        >>> oEditor.FaceCenter

        """
        try:
            result = [(float(face.center[1]), face) for face in self.faces]
            result = sorted(result, key=lambda tup: tup[0])
            return result[0][1]
        except Exception:
            return None

    @property
    def top_edge_z(self):
        """Top edge in the Z direction of the object. Midpoint is used as criteria to find the edge.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.elements_3d.EdgePrimitive`

        References
        ----------
        >>> oEditor.FaceCenter

        """
        try:
            result = [(float(face.top_edge_z.midpoint[2]), face.top_edge_z) for face in self.faces]
            result = sorted(result, key=lambda tup: tup[0])
            return result[-1][1]
        except Exception:
            return None

    @property
    def bottom_edge_z(self):
        """Bottom edge in the Z direction of the object. Midpoint is used as criteria to find the edge.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.elements_3d.EdgePrimitive`

        """
        try:
            result = [(float(face.bottom_edge_z.midpoint[2]), face.bottom_edge_z) for face in self.faces]
            result = sorted(result, key=lambda tup: tup[0])
            return result[0][1]
        except Exception:
            return None

    @property
    def top_edge_x(self):
        """Top edge in the X direction of the object. Midpoint is used as criteria to find the edge.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.elements_3d.EdgePrimitive`

        """
        try:
            result = [(float(face.top_edge_x.midpoint[0]), face.top_edge_x) for face in self.faces]
            result = sorted(result, key=lambda tup: tup[0])
            return result[-1][1]
        except Exception:
            return None

    @property
    def bottom_edge_x(self):
        """Bottom edge in the X direction of the object. Midpoint is used as criteria to find the edge.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.elements_3d.EdgePrimitive`

        """
        try:
            result = [(float(face.bottom_edge_x.midpoint[0]), face.bottom_edge_x) for face in self.faces]
            result = sorted(result, key=lambda tup: tup[0])
            return result[0][1]
        except Exception:
            return None

    @property
    def top_edge_y(self):
        """Top edge in the Y direction of the object. Midpoint is used as criteria to find the edge.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.elements_3d.EdgePrimitive`

        """
        try:
            result = [(float(face.top_edge_y.midpoint[1]), face.top_edge_y) for face in self.faces]
            result = sorted(result, key=lambda tup: tup[0])
            return result[-1][1]
        except Exception:
            return None

    @property
    def bottom_edge_y(self):
        """Bottom edge in the Y direction of the object. Midpoint is used as criteria to find the edge.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.elements_3d.EdgePrimitive`

        """
        try:
            result = [(float(face.bottom_edge_y.midpoint[1]), face.bottom_edge_y) for face in self.faces]
            result = sorted(result, key=lambda tup: tup[0])
            return result[0][1]
        except Exception:
            return None

    @property
    def edges(self):
        """Information for each edge in the given part.

        Returns
        -------
        list[:class:`ansys.aedt.core.modeler.cad.elements_3d.EdgePrimitive`]

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
        list[:class:`ansys.aedt.core.modeler.cad.elements_3d.VertexPrimitive`]

        References
        ----------
        >>> oEditor.GetVertexIDsFromObject

        """
        if self.object_type == "Unclassified":
            return []
        vertices = []

        v = [i for i in self._primitives.get_object_vertices(self.name)]
        if not v:
            for el in self.edges:
                pos = [float(p) for p in self._primitives.oeditor.GetEdgePositionAtNormalizedParameter(el.id, 0)]
                vertices.append(VertexPrimitive(self, -1, pos))
        if settings.aedt_version > "2022.2":
            v = v[::-1]
        for vertex in v:
            vertex = int(vertex)
            vertices.append(VertexPrimitive(self, vertex))
        return vertices

    @property
    def _oeditor(self):
        """Pointer to the oEditor object in the AEDT API.

        This property is intended primarily for use by FacePrimitive, EdgePrimitive, and
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
            self._surface_material = self._oeditor.GetPropertyValue(
                "Geometry3DAttributeTab", self._m_name, "Surface Material"
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
        group_name = None
        if "Group" in self.valid_properties:
            group_name = self._oeditor.GetPropertyValue("Geometry3DAttributeTab", self._m_name, "Group")
        if group_name is not None:
            self._m_groupName = group_name
        return self._m_groupName

    @group_name.setter
    def group_name(self, name):
        """Assign Object to a specific group. It creates a new group if the group doesn't exist.

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

        if not list(self._oeditor.GetObjectsInGroup(name)):
            self._oeditor.CreateGroup(
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
            groupName = self._oeditor.GetPropertyValue("Geometry3DAttributeTab", self._m_name, "Group")
            self._oeditor.ChangeProperty(
                [
                    "NAME:AllTabs",
                    [
                        "NAME:Attributes",
                        ["NAME:PropServers", groupName],
                        ["NAME:ChangedProps", ["NAME:Name", "Value:=", name]],
                    ],
                ]
            )
        else:
            vgroup = ["NAME:Group", "Value:=", name]
            self._change_property(vgroup)
        self._m_groupName = name

    @property
    def is_conductor(self):
        """Check if the object is a conductor."""
        if self.material_name and self._primitives._materials[self.material_name].is_conductor():
            return True
        return False

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
            mat = self._oeditor.GetPropertyValue("Geometry3DAttributeTab", self._m_name, "Material")
            self._material_name = ""
            if mat:
                self._material_name = mat.strip('"').lower()
            return self._material_name
        return ""

    @material_name.setter
    def material_name(self, mat):
        matobj = self._primitives._materials.exists_material(mat)
        mat_value = None
        if matobj:
            mat_value = chr(34) + matobj.name + chr(34)
        elif "[" in mat or "(" in mat:
            mat_value = mat
        if mat_value is not None:
            if not self.model:
                self.model = True
            vMaterial = ["NAME:Material", "Value:=", mat_value]
            self._change_property(vMaterial)
            self._material_name = mat_value.strip('"')
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
        except Exception:
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
            except Exception:
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
        if self._m_name in list(self._oeditor.GetObjectsInGroup("Solids")):
            self._object_type = "Solid"
        elif self._m_name in list(self._oeditor.GetObjectsInGroup("Sheets")):
            self._object_type = "Sheet"
        elif self._m_name in list(self._oeditor.GetObjectsInGroup("Lines")):
            self._object_type = "Line"
        elif self._m_name in list(self._oeditor.GetObjectsInGroup("Unclassified")):  # pragma: no cover
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
        if obj_name != self._m_name and obj_name not in self._primitives.object_names:
            vName = ["NAME:Name", "Value:=", obj_name]
            vChangedProps = ["NAME:ChangedProps", vName]
            vPropServers = ["NAME:PropServers", self._m_name]
            vGeo3d = ["NAME:Geometry3DAttributeTab", vPropServers, vChangedProps]
            vOut = ["NAME:AllTabs", vGeo3d]
            self._primitives.oeditor.ChangeProperty(vOut)
            self._m_name = obj_name
            self._primitives.add_new_objects()
            self._primitives.cleanup_objects()
        else:
            self.logger.warning(f"{obj_name} is already used in current design.")

    @property
    def valid_properties(self):
        """Valid properties.

        References
        ----------
        >>> oEditor.GetProperties
        """
        if not self._all_props:
            self._all_props = self._oeditor.GetProperties("Geometry3DAttributeTab", self._m_name)
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
            color = self._oeditor.GetPropertyValue("Geometry3DAttributeTab", self._m_name, "Color")
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
        return f"({self.color[0]} {self.color[1]} {self.color[2]})"

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
            msg_text = f"Invalid color input {color_value} for object {self._m_name}."
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
            try:
                transp = self._oeditor.GetPropertyValue("Geometry3DAttributeTab", self._m_name, "Transparent")
                self._transparency = float(transp)
            except Exception:
                self._all_props = None
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
            self._part_coordinate_system = self._oeditor.GetPropertyValue(
                "Geometry3DAttributeTab", self._m_name, "Orientation"
            )
            return self._part_coordinate_system

    @part_coordinate_system.setter
    def part_coordinate_system(self, sCS):
        pcs = ["NAME:Orientation", "Value:=", sCS]
        self._change_property(pcs)
        self._part_coordinate_system = sCS

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
            solveinside = self._oeditor.GetPropertyValue("Geometry3DAttributeTab", self._m_name, "Solve Inside")
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
            wireframe = self._oeditor.GetPropertyValue("Geometry3DAttributeTab", self._m_name, "Display Wireframe")
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
    def material_appearance(self):
        """Material appearance property of the part.

        Returns
        -------
        bool
            ``True`` when material appearance is activated for the part, ``False`` otherwise.

        References
        ----------
        >>> oEditor.GetPropertyValue
        >>> oEditor.ChangeProperty

        """
        if self._material_appearance is not None:
            return self._material_appearance
        if "Material Appearance" in self.valid_properties:
            material_appearance = self._oeditor.GetPropertyValue(
                "Geometry3DAttributeTab", self._m_name, "Material Appearance"
            )
            if material_appearance == "true" or material_appearance == "True":
                self._material_appearance = True
            else:
                self._material_appearance = False
            return self._material_appearance

    @material_appearance.setter
    def material_appearance(self, material_appearance):
        vMaterialAppearance = [
            "NAME:Material Appearance",
            "Value:=",
            material_appearance,
        ]

        self._change_property(vMaterialAppearance)
        self._material_appearance = material_appearance

    @pyaedt_function_handler()
    def history(self):
        """Object history.

        Returns
        -------
            :class:`ansys.aedt.core.modeler.cad.elements_3d.BinaryTree` when successful,
            ``False`` when failed.

        """
        try:
            child_object = self._oeditor.GetChildObject(self.name)
            parent = BinaryTreeNode(self.name, child_object, True)
            return parent
        except Exception:
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
            mod = self._oeditor.GetPropertyValue("Geometry3DAttributeTab", self._m_name, "Model")
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

    @pyaedt_function_handler(object_list="assignment")
    def unite(self, assignment):
        """Unite a list of objects with this object.

        Parameters
        ----------
        assignment : list of str or list of ansys.aedt.core.modeler.cad.object_3d.Object3d
            List of objects.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
           Object 3D object.

        References
        ----------
        >>> oEditor.Unite

        """
        unite_list = [self.name] + self._primitives.convert_to_selections(assignment, return_list=True)
        self._primitives.unite(unite_list)
        return self

    @pyaedt_function_handler(theList="assignment")
    def intersect(self, assignment, keep_originals=False):
        """Intersect the active object with a given list.

        Parameters
        ----------
        assignment : list
            List of objects.
        keep_originals : bool, optional
            Whether to keep the original object. The default is ``False``.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
            Retrieve the resulting 3D Object when succeeded.

        References
        ----------
        >>> oEditor.Intersect
        """
        assignment = [self.name] + self._primitives.convert_to_selections(assignment, return_list=True)
        self._primitives.intersect(assignment)
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
        return self._primitives.split(self.name, plane, sides)

    @pyaedt_function_handler(position="origin")
    def mirror(self, origin, vector, duplicate=False):
        """Mirror a selection.

        Parameters
        ----------
        origin : list of int or float
            Cartesian ``[x, y, z]`` coordinates or
            the ``Application.Position`` object of a point in the plane used for the mirror operation.
        vector : list of float
            Vector in Cartesian coordinates ``[x1, y1, z1]``  or
            the ``Application.Position`` object for the vector normal to the plane used for the mirror operation.
        duplicate : bool, optional
             Whether to duplicate the object after mirroring it .n. The default
             is ``False``, in which case AEDT is not duplicating the object.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
            3D object.
            ``False`` when failed.

        References
        ----------
        >>> oEditor.Mirror
        """
        if self._primitives.mirror(self.id, origin=origin, vector=vector, duplicate=duplicate):
            return self
        return False

    @pyaedt_function_handler(cs_axis="axis", unit="units")
    def rotate(self, axis, angle=90.0, units="deg"):
        """Rotate the selection.

        Parameters
        ----------
        axis : int
            Coordinate system axis or the Application.AXIS object.
        angle : float, optional
            Angle of rotation. The units, defined by ``unit``, can be either
            degrees or radians. The default is ``90.0``.
        units : text, optional
             Units for the angle. Options are ``"deg"`` or ``"rad"``.
             The default is ``"deg"``.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
            3D object. ``False`` when failed.

        References
        ----------
        >>> oEditor.Rotate
        """
        if self._primitives.rotate(self.id, axis=axis, angle=angle, units=units):
            return self
        return False

    @pyaedt_function_handler()
    def move(self, vector):
        """Move objects from a list.

        Parameters
        ----------
        vector : list
            Vector of the direction move. It can be a list of the ``[x, y, z]``
            coordinates or a Position object.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
            3D object.
            ``False`` when failed.

        References
        ----------
        >>> oEditor.Move
        """
        if self._primitives.move(self.id, vector):
            return self
        return False

    @pyaedt_function_handler(cs_axis="axis", nclones="clones")
    def duplicate_around_axis(self, axis, angle=90, clones=2, create_new_objects=True):
        """Duplicate the object around the axis.

        Parameters
        ----------
        axis : Application.AXIS object
            Coordinate system axis of the object.
        angle : float
            Angle of rotation in degrees. The default is ``90``.
        clones : int, optional
            Number of clones. The default is ``2``.
        create_new_objects : bool, optional
            Whether to create copies as new objects. The default is ``True``.

        Returns
        -------
        list[:class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`]
            List of names of the newly added objects.

        References
        ----------
        >>> oEditor.DuplicateAroundAxis

        """
        _, added_objects = self._primitives.duplicate_around_axis(
            self, axis, angle, clones, create_new_objects=create_new_objects
        )
        return added_objects

    @pyaedt_function_handler(nclones="clones", attachObject="attach")
    def duplicate_along_line(self, vector, clones=2, attach=False):
        """Duplicate the object along a line.

        Parameters
        ----------
        vector : list
            List of ``[x1 ,y1, z1]`` coordinates for the vector or the Application.Position object.
        clones : int, optional
            Number of clones. The default is ``2``.
        attach : bool, optional
            Whether to attach the object. The default is ``False``.

        Returns
        -------
        list of str
            List of names of the newly added objects.

        References
        ----------
        >>> oEditor.DuplicateAlongLine

        """
        _, added_objects = self._primitives.duplicate_along_line(self, vector, clones, attach=attach)
        return added_objects

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
        self._primitives.sweep_along_vector(self, sweep_vector, draft_angle, draft_type)
        return self

    @pyaedt_function_handler()
    def sweep_along_path(
        self, sweep_object, draft_angle=0, draft_type="Round", is_check_face_intersection=False, twist_angle=0
    ):
        """Sweep the selection along a vector.

        Parameters
        ----------
        sweep_object : :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
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
        :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
            Swept object.

        References
        ----------
        >>> oEditor.SweepAlongPath

        """
        self._primitives.sweep_along_path(
            self, sweep_object, draft_angle, draft_type, is_check_face_intersection, twist_angle
        )
        return self

    @pyaedt_function_handler(cs_axis="axis")
    def sweep_around_axis(self, axis, sweep_angle=360, draft_angle=0):
        """Sweep around an axis.

        Parameters
        ----------
        axis : :class:`ansys.aedt.core.generic.constants.AXIS`
            Coordinate system of the axis.
        sweep_angle : float, optional
             Sweep angle in degrees. The default is ``360``.
        draft_angle : float, optional
            Angle of the draft. The default is ``0``.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
            Swept object.

        References
        ----------
        >>> oEditor.SweepAroundAxis

        """
        self._primitives.sweep_around_axis(self, axis, sweep_angle, draft_angle)
        return self

    @pyaedt_function_handler()
    def section(self, plane, create_new=True, section_cross_object=False):
        """Section the object.

        Parameters
        ----------
        plane : from ansys.aedt.core.generic.constants.PLANE
            Coordinate system of the plane object. Application.PLANE object
        create_new : bool, optional
            Whether to create an object. The default is ``True``.
        section_cross_object : bool, optional
            The default is ``False``.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
            3D object.

        References
        ----------
        >>> oEditor.Section

        """
        self._primitives.section(self, plane, create_new, section_cross_object)
        return self

    @pyaedt_function_handler()
    def detach_faces(self, faces):
        """Section the object.

        Parameters
        ----------
        faces : List[FacePrimitive] or List[int] or int or FacePrimitive
            Face or faces to detach from the object.

        Returns
        -------
        list[:class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`]
            List of object resulting from the operation.

        References
        ----------
        >>> oEditor.DetachFaces

        """
        return self._primitives.detach_faces(self, faces)

    @pyaedt_function_handler()
    def clone(self):
        """Clone the object and return the new 3D object.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
            3D object that was added.

        References
        ----------
        >>> oEditor.Clone

        """
        new_obj_tuple = self._primitives.clone(self.id)
        success = new_obj_tuple[0]
        if not success:
            raise AEDTRuntimeError(f"Could not clone the object {self.name}")
        new_name = new_obj_tuple[1][0]
        self._primitives[new_name].is_polyline = self.is_polyline
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
        :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
            Modified 3D object following the subtraction.

        References
        ----------
        >>> oEditor.Subtract

        """
        self._primitives.subtract(self.name, tool_list, keep_originals)
        return self

    @pyaedt_function_handler()
    def wrap_sheet(self, object_name, imprinted=False):
        """Execute the sheet wrapping around an object. This object can be either the sheet or the object.
        If wrapping produces an unclassified operation it will be reverted.

        Parameters
        ----------
        object_name : str, :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
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
        self._oeditor.Delete(arg)
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
        list[:class:`ansys.aedt.core.modeler.cad.elements_3d.FacePrimitive`]
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
        list[:class:`ansys.aedt.core.modeler.cad.elements_3d.EdgePrimitive`]
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

    def __str__(self):
        return self.name

    @pyaedt_function_handler()
    def fillet(self, vertices=None, edges=None, radius=0.1, setback=0.0):
        """Add a fillet to the selected edges in 3D/vertices in 2D.

        Parameters
        ----------
        vertices : list, optional
            List of vertices to fillet. Default is ``None``.
        edges : list, optional
            List of edges to fillet. Default is ``None``.
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
        if not vertices and not edges:
            self.logger.error("Either vertices or edges have to be provided as input.")
            return False
        edge_id_list = []
        vertex_id_list = []
        if edges is not None:
            edge_id_list = self._primitives.convert_to_selections(edges, return_list=True)
        if vertices is not None:
            vertex_id_list = self._primitives.convert_to_selections(vertices, return_list=True)

        vArg1 = ["NAME:Selections", "Selections:=", self.name, "NewPartsModelFlag:=", "Model"]
        vArg2 = ["NAME:FilletParameters"]
        vArg2.append("Edges:="), vArg2.append(edge_id_list)
        vArg2.append("Vertices:="), vArg2.append(vertex_id_list)
        vArg2.append("Radius:="), vArg2.append(self._primitives._app.value_with_units(radius))
        vArg2.append("Setback:="), vArg2.append(self._primitives._app.value_with_units(setback))
        self._oeditor.Fillet(vArg1, ["NAME:Parameters", vArg2])
        if self.name in list(self._oeditor.GetObjectsInGroup("UnClassified")):
            self._primitives._odesign.Undo()
            self.logger.error("Operation failed, generating an unclassified object. Check and retry.")
            return False
        return True

    @pyaedt_function_handler()
    def chamfer(self, vertices=None, edges=None, left_distance=1, right_distance=None, angle=45, chamfer_type=0):
        """Add a chamfer to the selected edges in 3D/vertices in 2D.

        Parameters
        ----------
        vertices : list, optional
            List of vertices to chamfer.
        edges : list, optional
            List of edges to chamfer.
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
        if edges is not None:
            edge_id_list = self._primitives.convert_to_selections(edges, return_list=True)
        if vertices is not None:
            vertex_id_list = self._primitives.convert_to_selections(vertices, return_list=True)
        if vertex_id_list == edge_id_list == []:
            self.logger.error("Vertices or Edges have to be provided as input.")
            return False
        vArg1 = ["NAME:Selections", "Selections:=", self.name, "NewPartsModelFlag:=", "Model"]
        vArg2 = ["NAME:ChamferParameters"]
        vArg2.append("Edges:="), vArg2.append(edge_id_list)
        vArg2.append("Vertices:="), vArg2.append(vertex_id_list)
        if right_distance is None:
            right_distance = left_distance
        if chamfer_type == 0:
            if left_distance != right_distance:
                self.logger.error("Do not set right distance or ensure that left distance equals right distance.")
            vArg2.append("LeftDistance:="), vArg2.append(self._primitives._app.value_with_units(left_distance))
            vArg2.append("RightDistance:="), vArg2.append(self._primitives._app.value_with_units(right_distance))
            vArg2.append("ChamferType:="), vArg2.append("Symmetric")
        elif chamfer_type == 1:
            vArg2.append("LeftDistance:="), vArg2.append(self._primitives._app.value_with_units(left_distance))
            vArg2.append("RightDistance:="), vArg2.append(self._primitives._app.value_with_units(right_distance))
            vArg2.append("ChamferType:="), vArg2.append("Left Distance-Right Distance")
        elif chamfer_type == 2:
            vArg2.append("LeftDistance:="), vArg2.append(self._primitives._app.value_with_units(left_distance))
            # NOTE: Seems like there is a bug in the API as Angle can't be used
            vArg2.append("RightDistance:="), vArg2.append(f"{angle}deg")
            vArg2.append("ChamferType:="), vArg2.append("Left Distance-Angle")
        elif chamfer_type == 3:
            # NOTE: Seems like there is a bug in the API as Angle can't be used
            vArg2.append("LeftDistance:="), vArg2.append(f"{angle}deg")
            vArg2.append("RightDistance:="), vArg2.append(self._primitives._app.value_with_units(right_distance))
            vArg2.append("ChamferType:="), vArg2.append("Right Distance-Angle")
        else:
            self.logger.error("Wrong chamfer_type provided. Value must be an integer from 0 to 3.")
            return False
        self._oeditor.Chamfer(vArg1, ["NAME:Parameters", vArg2])
        if self.name in list(self._oeditor.GetObjectsInGroup("UnClassified")):
            self._primitives._odesign.Undo()
            self.logger.error("Operation Failed generating Unclassified object. Check and retry")
            return False
        return True

    @property
    def start_point(self):
        """Get the starting point in the polyline object.

        This is a list of the ``[x, y, z]`` coordinates for the starting point in the polyline
        object in the object's coordinate system

        Returns
        -------
        list
            List of the ``[x, y, z]`` coordinates for the starting point in the polyline
            object.
        """
        try:
            return self.points[0]
        except (TypeError, IndexError):
            return

    @property
    def end_point(self):
        """List of the ``[x, y, z]`` coordinates for the ending point in the polyline
        object in the object's coordinate system.

        Returns
        -------
        list
            List of the ``[x, y, z]`` coordinates for the ending point in the polyline
            object.

        References
        ----------
        >>> oEditor.GetVertexIDsFromObject
        >>> oEditor.GetVertexPosition

        """
        try:
            return self.points[-1]
        except (TypeError, IndexError):
            return

    def _update_segments_and_points(self):
        """Update the self._segment_types and the self._positions from the history.

        This internal method is called by properties ``points`` and ``segment_types``.
        It will be called only once after opening a new project, then the internal
        variables are maintained updated.
        It is a single update call for both properties because they are very similar,
        and we can access to the history only once.
        """

        def _convert_points(p_in, dest_unit):
            p_out = []
            for ip in p_in:
                v, u = decompose_variable_value(ip)
                if u == "":
                    p_out.append(v)
                else:
                    p_out.append(unit_converter(v, unit_system="Length", input_units=u, output_units=dest_unit))
            return p_out

        segments = []
        points = []
        try:
            history = self.history()
            h_segments = history.segments
        except Exception:  # pragma: no cover
            history = None
            h_segments = None
        if h_segments:
            for i, c in enumerate(h_segments.values()):
                # evaluate the number of points in the segment
                attrb = list(c.properties.keys())
                n_points = 0
                for j in range(1, len(attrb) + 1):
                    if "Point" + str(j) in attrb:
                        n_points += 1
                # get the segment type
                s_type = c.properties["Segment Type"]
                if i == 0:  # append the first point only for the first segment
                    if s_type != "Center Point Arc":
                        p = [
                            c.properties["Point1/X"],
                            c.properties["Point1/Y"],
                            c.properties["Point1/Z"],
                        ]
                        points.append(_convert_points(p, self._primitives.model_units))
                    else:
                        p = [
                            c.properties["Start Point/X"],
                            c.properties["Start Point/Y"],
                            c.properties["Start Point/Z"],
                        ]
                        points.append(_convert_points(p, self._primitives.model_units))
                if s_type == "Line":
                    segments.append(PolylineSegment("Line"))
                    p = [
                        c.properties["Point2/X"],
                        c.properties["Point2/Y"],
                        c.properties["Point2/Z"],
                    ]
                    points.append(_convert_points(p, self._primitives.model_units))
                elif s_type == "3 Point Arc":
                    segments.append(PolylineSegment("Arc"))
                    p2 = [
                        c.properties["Point2/X"],
                        c.properties["Point2/Y"],
                        c.properties["Point2/Z"],
                    ]
                    p3 = [
                        c.properties["Point3/X"],
                        c.properties["Point3/Y"],
                        c.properties["Point3/Z"],
                    ]

                    points.append(_convert_points(p2, self._primitives.model_units))
                    points.append(_convert_points(p3, self._primitives.model_units))
                elif s_type == "Spline":
                    segments.append(PolylineSegment("Spline", num_points=n_points))
                    for p in range(2, n_points + 1):
                        point_attr = "Point" + str(p)
                        p2 = [
                            c.properties[f"{point_attr}/X"],
                            c.properties[f"{point_attr}/Y"],
                            c.properties[f"{point_attr}/Z"],
                        ]

                        points.append(_convert_points(p2, self._primitives.model_units))
                elif s_type == "Center Point Arc":
                    p2 = [
                        c.properties["Start Point/X"],
                        c.properties["Start Point/Y"],
                        c.properties["Start Point/Z"],
                    ]
                    p3 = [
                        c.properties["Center Point/X"],
                        c.properties["Center Point/Y"],
                        c.properties["Center Point/Z"],
                    ]
                    start = _convert_points(p2, self._primitives.model_units)
                    center = _convert_points(p3, self._primitives.model_units)
                    plane = c.properties["Plane"]
                    angle = c.properties["Angle"]
                    arc_seg = PolylineSegment("AngularArc", arc_angle=angle, arc_center=center, arc_plane=plane)
                    segments.append(arc_seg)
                    self._evaluate_arc_angle_extra_points(arc_seg, start)
                    points.extend(arc_seg.extra_points[:])

        # perform validation
        if history:
            nn_segments = int(history.properties["Number of curves"])
            nn_points = int(history.properties["Number of points"])
        else:
            nn_segments = None
            nn_points = None
        if not len(segments) == nn_segments:
            raise AEDTRuntimeError("Failed to get the polyline segments from AEDT.")
        if not len(points) == nn_points:
            raise AEDTRuntimeError("Failed to get the polyline points from AEDT.")
        # if succeeded save the result
        self._segment_types = segments
        self._positions = points

    @property
    def points(self):
        """Polyline Points."""
        if not self.is_polyline:
            return
        if self._positions:
            return self._positions
        else:
            self._update_segments_and_points()
            return self._positions

    @property
    def segment_types(self):
        """List of the segment types of the polyline."""
        if not self.is_polyline:
            return
        if self._segment_types:
            return self._segment_types
        else:
            self._update_segments_and_points()
            return self._segment_types

    @property
    def vertex_positions(self):
        """List of the ``[x, y, z]`` coordinates for all vertex positions in the
        polyline object in the object's coordinate system.

        Returns
        -------
        list
            List of the ``[x, y, z]`` coordinates for all vertex positions in the
            polyline object.

        References
        ----------
        >>> oEditor.GetVertexIDsFromObject
        >>> oEditor.GetVertexPosition

        """
        if not self.is_polyline:
            return
        id_list = self._primitives.get_object_vertices(assignment=self.id)
        position_list = [self._primitives.get_vertex_position(id) for id in id_list]
        return position_list

    @pyaedt_function_handler()
    def _pl_point(self, pt):
        pt_data = ["NAME:PLPoint"]
        pt_data.append("X:=")
        pt_data.append(self._primitives._app.value_with_units(pt[0], self._primitives.model_units))
        pt_data.append("Y:=")
        pt_data.append(self._primitives._app.value_with_units(pt[1], self._primitives.model_units))
        pt_data.append("Z:=")
        pt_data.append(self._primitives._app.value_with_units(pt[2], self._primitives.model_units))
        return pt_data

    @pyaedt_function_handler()
    def _point_segment_string_array(self):
        """Retrieve the parameter arrays for specifying the points and segments of a polyline
        used in the :class:`ansys.aedt.core.modeler.cad.primitives.Polyline` constructor.

        Returns
        -------
        list
        """
        position_list = self.points
        segment_types = self.segment_types

        # Add a closing point if needed
        arg_1 = [
            "NAME:PolylineParameters",
            "IsPolylineCovered:=",
            self._is_covered,
            "IsPolylineClosed:=",
            self._is_closed,
        ]

        # PointsArray
        points_str = ["NAME:PolylinePoints"]
        points_str.append(self._pl_point(position_list[0]))

        # Segments Array
        segment_str = ["NAME:PolylineSegments"]

        pos_count = 0
        vertex_count = 0
        index_count = 0

        while vertex_count <= len(segment_types):
            try:
                current_segment = None
                if vertex_count == len(segment_types):
                    if self._is_closed:
                        # Check the special case of a closed polyline needing an additional Line segment
                        if position_list[0] != position_list[-1]:
                            position_list.append(position_list[0])
                            current_segment = PolylineSegment("Line")
                    else:
                        break
                else:
                    current_segment = segment_types[vertex_count]
            except Exception:
                raise IndexError("Number of segments inconsistent with the number of points!")

            if current_segment:
                seg_str = self._segment_array(
                    current_segment, start_index=index_count, start_point=position_list[pos_count]
                )
                segment_str.append(seg_str)

                pos_count_incr = 0
                for i in range(1, current_segment.num_points):
                    if current_segment.type == "AngularArc":
                        points_str.append(self._pl_point(current_segment.extra_points[i - 1]))
                        index_count += 1
                        pos_count_incr += 1
                    else:
                        if (pos_count + i) == len(position_list):
                            if current_segment.type == "Arc" and self._is_closed:
                                position_list.append(position_list[0])
                            else:
                                err_str = "Insufficient points in position_list to complete the specified segment list"
                                raise ValueError(err_str)
                        points_str.append(self._pl_point(position_list[pos_count + i]))
                        pos_count_incr += 1
                        index_count += 1
                pos_count += pos_count_incr
                vertex_count += 1
            else:
                break

        arg_1.append(points_str)
        arg_1.append(segment_str)

        # Poly Line Cross Section
        arg_1.append(self._xsection)

        return arg_1

    @pyaedt_function_handler()
    def _evaluate_arc_angle_extra_points(self, segment, start_point):
        """Evaluate the extra points for the ArcAngle segment type.

        It also auto evaluates the arc_plane if it was not specified by the user.
        segment.extra_points[0] contains the arc mid point (on the arc).
        segment.extra_points[1] contains the arc end point.
        Both are function of the arc center, arc angle and arc plane.
        """
        # from start-point and angle, calculate the mid-point and end-points
        # Also identify the plane of the arc ("YZ", "ZX", "XY")
        plane_axes = {"YZ": [1, 2], "ZX": [2, 0], "XY": [0, 1]}
        c_xyz = self._primitives.value_in_object_units(segment.arc_center)
        p0_xyz = self._primitives.value_in_object_units(start_point)

        if segment.arc_plane:
            # Accept the user input for the plane of rotation - let the modeler fail if invalid
            plane_def = (segment.arc_plane, plane_axes[segment.arc_plane])
        else:
            # Compare the numeric values of start-point and center-point to determine the orientation plane
            if c_xyz[0] == p0_xyz[0]:
                plane_def = ("YZ", plane_axes["YZ"])
            elif c_xyz[1] == p0_xyz[1]:
                plane_def = ("ZX", plane_axes["ZX"])
            elif c_xyz[2] == p0_xyz[2]:
                plane_def = ("XY", plane_axes["XY"])
            else:
                raise Exception("Start point and arc-center do not lie on a common base plane.")
            segment.arc_plane = plane_def[0]

        # Calculate the extra two points of the angular arc in the alpha-beta plane
        alph_index = plane_def[1][0]
        beta_index = plane_def[1][1]
        c_alph = c_xyz[alph_index]
        c_beta = c_xyz[beta_index]
        p0_alph = p0_xyz[alph_index] - c_alph
        p0_beta = p0_xyz[beta_index] - c_beta

        # rotate to generate the new points
        arc_ang = self._primitives._app.evaluate_expression(segment.arc_angle)  # in radians
        h_arc_ang = arc_ang * 0.5

        p1_alph = c_alph + p0_alph * math.cos(h_arc_ang) - p0_beta * math.sin(h_arc_ang)
        p1_beta = c_beta + p0_alph * math.sin(h_arc_ang) + p0_beta * math.cos(h_arc_ang)
        p2_alph = c_alph + p0_alph * math.cos(arc_ang) - p0_beta * math.sin(arc_ang)
        p2_beta = c_beta + p0_alph * math.sin(arc_ang) + p0_beta * math.cos(arc_ang)

        # Generate the 2 new points in XYZ
        p1 = list(p0_xyz)
        p1[alph_index] = p1_alph
        p1[beta_index] = p1_beta
        p2 = list(p0_xyz)
        p2[alph_index] = p2_alph
        p2[beta_index] = p2_beta
        segment.extra_points = [p1, p2]
        return True

    @pyaedt_function_handler()
    def _segment_array(self, segment_data, start_index=0, start_point=None):
        """Retrieve a property array for a polyline segment for use in the
        :class:`ansys.aedt.core.modeler.cad.primitives.Polyline` constructor.

        Parameters
        ----------
        segment_data : :class:`ansys.aedt.core.modeler.cad.primitives.PolylineSegment` or str
            Pointer to the calling object that provides additional functionality
            or a string with the segment type ``Line`` or ``Arc``.
        start_index : int, string
            Starting vertex index of the segment within a compound polyline. The
            default is ``0``.
        start_point : list, optional
            Position of the first point for type ``AngularArc``. The default is
            ``None``. Float values are considered in model units.

        Returns
        -------
        list
            List of properties defining a polyline segment.

        """
        if isinstance(segment_data, str):
            segment_data = PolylineSegment(segment_data)

        seg = [
            "NAME:PLSegment",
            "SegmentType:=",
            segment_data.type,
            "StartIndex:=",
            start_index,
            "NoOfPoints:=",
            segment_data.num_points,
        ]
        if segment_data.type != "Line":
            seg += ["NoOfSegments:=", f"{segment_data.num_seg}"]

        if segment_data.type == "AngularArc":
            # from start-point and angle, calculate the mid- and end-points
            if not start_point:
                raise ValueError("Start point must be defined for segment of type Angular Arc")
            self._evaluate_arc_angle_extra_points(segment_data, start_point)

            mod_units = self._primitives.model_units
            seg += [
                "ArcAngle:=",
                segment_data.arc_angle,
                "ArcCenterX:=",
                f"{self._primitives._app.value_with_units(segment_data.arc_center[0], mod_units)}",
                "ArcCenterY:=",
                f"{self._primitives._app.value_with_units(segment_data.arc_center[1], mod_units)}",
                "ArcCenterZ:=",
                f"{self._primitives._app.value_with_units(segment_data.arc_center[2], mod_units)}",
                "ArcPlane:=",
                segment_data.arc_plane,
            ]

        return seg

    @pyaedt_function_handler(abstol="tolerance")
    def remove_point(self, position, tolerance=1e-9):
        """Remove a point from an existing polyline by position.

        You must enter the exact position of the vertex as a list
        of ``[x, y, z]`` coordinates in the object's coordinate system.

        Parameters
        ----------
        position : list
            List of ``[x, y, z]`` coordinates specifying the vertex to remove.
        tolerance : float, optional
            Absolute tolerance of the comparison of a specified position to the
            vertex positions. The default is ``1e-9``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.DeletePolylinePoint

        Examples
        --------
        Use floating point values for the vertex positions.

        >>> P = modeler.create_polyline([[0, 1, 2], [0, 2, 3], [2, 1, 4]])
        >>> P.remove_point([0, 1, 2])

        Use string expressions for the vertex position.

        >>> P = modeler.create_polyline([[0, 1, 2], [0, 2, 3], [2, 1, 4]])
        >>> P.remove_point(["0mm", "1mm", "2mm"])

        Use string expressions for the vertex position and include an absolute
        tolerance when searching for the vertex to be removed.

        >>> P = modeler.create_polyline([[0, 1, 2], [0, 2, 3], [2, 1, 4]])
        >>> P.remove_point(["0mm", "1mm", "2mm"],tolerance=1e-6)
        """
        if not self.is_polyline:
            self.logger.error("Method remove_point applies only to Polyline objects.")
            return False
        found_vertex = False
        seg_id = None
        at_start = None
        pos_xyz = self._primitives.value_in_object_units(position)
        for ind, point_pos in enumerate(self.points):
            # compare the specified point with the vertex data using an absolute tolerance
            # (default of math.isclose is 1e-9 which should be ok in almost all cases)
            found_vertex = GeometryOperators.points_distance(point_pos, pos_xyz) <= tolerance
            if found_vertex:
                if ind == len(self.points) - 1:
                    at_start = False
                    seg_id = self._get_segment_id_from_point_n(ind, at_start, allow_inner_points=True)
                else:
                    at_start = True
                    seg_id = self._get_segment_id_from_point_n(ind, at_start, allow_inner_points=True)
                break

        if not found_vertex or seg_id is None or at_start is None:
            raise ValueError(f"Specified vertex {position} not found in polyline {self._m_name}.")

        try:
            self._primitives.oeditor.DeletePolylinePoint(
                [
                    "NAME:Delete Point",
                    "Selections:=",
                    self._m_name + ":CreatePolyline:1",
                    "Segment Indices:=",
                    [seg_id],
                    "At Start:=",
                    at_start,
                ]
            )
        except Exception:  # pragma: no cover
            raise ValueError(f"Invalid edge ID {seg_id} is specified on polyline {self.name}.")
        else:
            i_start, i_end = self._get_point_slice_from_segment_id(seg_id, at_start)
            del self._positions[i_start:i_end]
            del self._segment_types[seg_id]

        return True

    @pyaedt_function_handler(segment_id="assignment")
    def remove_segments(self, assignment):
        """Remove a segment from an existing polyline by segment id.

        You must enter the segment id or the list of the segment ids you want to remove.

        Parameters
        ----------
        assignment : int or List of int
            One or more edge IDs within the total number of edges of the polyline.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.DeletePolylinePoint

        Examples
        --------
        >>> P = modeler.create_polyline([[0, 1, 2], [0, 2, 3], [2, 1, 4]])
        >>> P.remove_segments(assignment=0)
        """
        if not self.is_polyline:
            self.logger.error("Method remove_point applies only to Polyline objects.")
            return False
        if isinstance(assignment, int):
            assignment = [assignment]
        elif isinstance(assignment, list):
            assignment.sort()
        else:
            raise TypeError("segment_id must be int or list of int.")
        try:
            self._primitives.oeditor.DeletePolylinePoint(
                [
                    "NAME:Delete Point",
                    "Selections:=",
                    self.name + ":CreatePolyline:1",
                    "Segment Indices:=",
                    assignment,
                    "At Start:=",
                    True,
                ]
            )
        except Exception:  # pragma: no cover
            raise ValueError(f"Invalid segment ID {assignment} is specified on polyline {self.name}.")
        else:
            assignment.reverse()
            for sid in assignment:
                if sid == len(self._segment_types) - 1:
                    # removing the last segment, AEDT removes ALWAYS the last polyline point
                    at_start = False
                else:
                    at_start = True
                i_start, i_end = self._get_point_slice_from_segment_id(sid, at_start)
                del self._positions[i_start:i_end]
                del self._segment_types[sid]
        return True

    @pyaedt_function_handler(type="section")
    def set_crosssection_properties(
        self, section=None, orient=None, width=0, topwidth=0, height=0, num_seg=0, bend_type=None
    ):
        """Set the properties of an existing polyline object.

        Parameters
        ----------
        section : str, optional
            Types of the cross-sections. Options are ``"Line"``, ``"Circle"``, ``"Rectangle"``,
            and ``"Isosceles Trapezoid"``. The default is ``None``.
        orient : str, optional
            Direction of the normal vector to the width of the cross-section.
            Options are ``"X"``, ``"Y"``, ``"Z"``, and ``"Auto"``. The default
            is ``None``, which sets the orientation to ``"Auto"``.
        width : float or str, optional
           Width or diameter of the cross-section for all types. The default is
           ``0``.
        topwidth : float or str
           Top width of the cross-section for the type ``"Isosceles Trapezoid"``
           only. The default is ``0``.
        height : float or str
            Height of the cross-section for the types ``"Rectangle"`` and `"Isosceles
            Trapezoid"`` only. The default is ``0``.
        num_seg : int, optional
            Number of segments in the cross-section surface for the types ``"Circle"``,
            ``"Rectangle"``, and ``"Isosceles Trapezoid"``. The default is ``0``.
            The value must be ``0`` or greater than ``2``.
        bend_type : str, optional
            Type of the bend. The default is ``None``, in which case the bend type
            is set to ``"Corner"``. For the type ``"Circle"``, the bend type should be
            set to ``"Curved"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.ChangeProperty

        Examples
        --------
        >>> P = modeler.create_polyline([[0, 1, 2], [0, 2, 3], [2, 1, 4]])
        >>> P.set_crosssection_properties(section="Circle",width="1mm")

        """
        if not self.is_polyline:
            self.logger.error("Method remove_point applies only to Polyline objects.")
            return False
        # Set the default section type to "None"
        section_type = section
        if not section_type:
            section_type = "None"

        # Set the default orientation to "Auto"
        section_orient = orient
        if not section_orient:
            section_orient = "Auto"

        # Set the default bend-type to "Corner"
        section_bend = bend_type
        if not section_bend:
            section_bend = "Corner"

        # Ensure number-of segments is valid
        if num_seg and num_seg < 3:
            raise ValueError("Number of segments for a cross-section must be 0 or greater than 2.")

        model_units = self._primitives.model_units

        arg1 = ["NAME:AllTabs"]
        arg2 = ["NAME:Geometry3DCmdTab", ["NAME:PropServers", self._m_name + ":CreatePolyline:1"]]
        arg3 = ["NAME:ChangedProps"]
        arg3.append(["NAME:Type", "Value:=", section_type])
        arg3.append(["NAME:Orientation", "Value:=", section_orient])
        arg3.append(["NAME:Bend Type", "Value:=", section_bend])
        arg3.append(["NAME:Width/Diameter", "Value:=", self._primitives._app.value_with_units(width, model_units)])
        if section_type == "Rectangle":
            arg3.append(["NAME:Height", "Value:=", self._primitives._app.value_with_units(height, model_units)])
        elif section_type == "Circle":
            arg3.append(["NAME:Number of Segments", "Value:=", num_seg])
        elif section_type == "Isosceles Trapezoid":
            arg3.append(["NAME:Top Width", "Value:=", self._primitives._app.value_with_units(topwidth, model_units)])
            arg3.append(["NAME:Height", "Value:=", self._primitives._app.value_with_units(height, model_units)])
        arg2.append(arg3)
        arg1.append(arg2)
        self._primitives.oeditor.ChangeProperty(arg1)
        return True

    @pyaedt_function_handler()
    def _get_point_slice_from_segment_id(self, segment_id, at_start=True):
        """Get the points belonging to the segment from the segment id.

        The points are returned as list slice by returning the indexes.

        Parameters
        ----------
        segment_id : int
            Segment id.

        at_start : bool
            if ``True`` the slice includes the start point of the segment and not the end point.
            If ``False`` the slice includes the end point of the segment and not the start point.

        Returns
        -------
        tuple of int, bool
            Indexes of the list slice. ``False`` when failed.
        """
        i_end = 0
        for i, s in enumerate(self.segment_types):
            i_start = i_end
            if s.type == "Line":
                i_end += 1
            elif s.type == "Arc":
                i_end += 2
            elif s.type == "AngularArc":
                i_end += 2
            elif s.type == "Spline":
                i_end += s.num_points - 1
            if i == segment_id:
                if at_start:
                    return i_start, i_end
                else:
                    return i_start + 1, i_end + 1
        return False

    @pyaedt_function_handler()
    def _get_segment_id_from_point_n(self, pn, at_start, allow_inner_points=False):
        """Get the segment id for a given point index considering the segment types in the polyline.

        If a segment cannot be found with the specified rules, the function returns False.

        Parameters
        ----------
        pn : int
            Point number along the polyline.
        at_start : bool
            If set to ``True`` the segment id that begins with the point pn is returned.
            If set to ``False`` the segment id that terminates with the point pn is returned.
        allow_inner_points : bool, optional
            If set to ``False`` only points that are at the extremities of the segments are considered.
            If pn is in the middle of a segment, the function returns False.
            If set to ``True`` also points in the middle of the segments are considered.

        Returns
        -------
        int, bool
            Segment id when successful. ``False`` when failed.
        """
        n_points = 0
        for i, s in enumerate(self.segment_types):
            if n_points == pn and at_start:
                return i
            n_points_imu = n_points
            if s.type == "Line":
                n_points += 1
            elif s.type == "Arc":
                n_points += 2
            elif s.type == "AngularArc":
                n_points += 2
            elif s.type == "Spline":
                n_points += s.num_points - 1
            if n_points == pn and not at_start:
                return i
            if n_points_imu < pn < n_points and allow_inner_points:
                return i
        return False

    @pyaedt_function_handler(position_list="points")
    def insert_segment(self, points, segment=None):
        """Add a segment to an existing polyline.

        Parameters
        ----------
        points : List
            List of positions of the points that define the segment to insert.
            Either the starting point or ending point of the segment list must
            match one of the vertices of the existing polyline.
        segment : str or :class:`ansys.aedt.core.modeler.cad.primitives.PolylineSegment`, optional
            Definition of the segment to insert. For the types ``"Line"`` and ``"Arc"``,
            use their string values ``"Line"`` and ``"Arc"``. For the types ``"AngularArc"``
            and ``"Spline"``, use the :class:`ansys.aedt.core.modeler.cad.primitives.PolylineSegment`
            object to define the segment precisely. The default is ``None``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.InsertPolylineSegment

        """
        # Check for a valid number of points
        if not self.is_polyline:
            self.logger.error("Method remove_point applies only to Polyline objects.")
            return False
        num_points = len(points)

        # define the segment type from the number of points given
        if not segment:
            if num_points < 2:
                raise ValueError("num_points must contain at least 2 points to auto-define a segment.")
            if num_points == 2:
                segment = PolylineSegment("Line")
            elif num_points == 3:
                segment = PolylineSegment("Arc")
            else:  # num_points>3
                segment = PolylineSegment("Spline", num_points=num_points)
        else:
            if isinstance(segment, str) and segment in ["Line", "Arc"]:
                segment = PolylineSegment(segment)
                num_points = segment.num_points
            elif isinstance(segment, PolylineSegment):
                num_points = segment.num_points
                if segment.type == "AngularArc":
                    self._evaluate_arc_angle_extra_points(segment, start_point=points[0])
            else:
                raise TypeError('segment must be either "Line", "Arc" or PolylineSegment object.')
            if segment.type != "AngularArc" and len(points) < num_points:
                raise ValueError("position_list must contain enough points for the specified segment type.")
            elif segment.type == "AngularArc" and len(points) < 1:
                raise ValueError("position_list must contain the start point for AngularArc segment.")

        # Check whether start-point and end-point of the segment is in the existing polylines points
        start_point = points[0]

        # End point does not exist for an AngularArc
        if segment.type != "AngularArc":
            end_point = points[-1]
        else:
            end_point = []

        at_start = None
        p_insert_position = None
        insert_points = None
        num_polyline_points = len(self.points)
        i = None
        for i, point in enumerate(self.points):
            if end_point and (
                GeometryOperators.points_distance(
                    self._primitives.value_in_object_units(point), self._primitives.value_in_object_units(end_point)
                )
                < 1e-8
            ):
                at_start = True
                p_insert_position = i
                insert_points = points[: num_points - 1]  # All points but last one.
                if i == num_polyline_points - 1:
                    if segment.type != "Line":
                        # Inserting a segment in this position is not allowed in AEDT.
                        # We can make it work only for "Line" segments.
                        return False
                    at_start = False
                    points = [self.points[-2], start_point]
                break
            elif (
                GeometryOperators.points_distance(
                    self._primitives.value_in_object_units(point), self._primitives.value_in_object_units(start_point)
                )
                < 1e-8
            ):
                # note that AngularArc can only be here
                at_start = False
                p_insert_position = i + 1
                if segment.type != "AngularArc":
                    insert_points = points[1:num_points]  # Insert all points but first one
                else:
                    insert_points = segment.extra_points[:]  # For AngularArc insert the extra points
                if i == 0:
                    if segment.type != "Line":
                        # Inserting a segment in this position is not allowed in AEDT.
                        # PyAEDT can make it work only for "Line" segments.
                        return False
                    at_start = True
                    points = [end_point, self.points[1]]
                break

        if p_insert_position is None or insert_points is None:
            raise RuntimeError("Point for the insert is not found.")

        if i is None:
            raise ValueError("The polyline contains no points. It is impossible to insert a segment.")
        segment_index = self._get_segment_id_from_point_n(i, at_start=at_start)

        if not isinstance(segment_index, int):
            raise ValueError("Segment for the insert is not found.")
        if at_start:
            s_insert_position = segment_index
        else:
            s_insert_position = segment_index + 1
        segment_type = segment.type

        arg_1 = [
            "NAME:Insert Polyline Segment",
            "Selections:=",
            self._m_name + ":CreatePolyline:1",
            "Segment Indices:=",
            [segment_index],
            "At Start:=",
            at_start,
            "SegmentType:=",
            segment_type,
        ]

        # Points and segment data
        arg_2 = ["NAME:PolylinePoints"]
        if segment.type in ("Line", "Spline", "Arc"):
            for pt in points[0:num_points]:
                arg_2.append(self._pl_point(pt))
            arg_1.append(arg_2)
        elif segment.type == "AngularArc":
            seg_str = self._segment_array(segment, start_point=start_point)
            arg_2.append(self._pl_point(start_point))
            arg_2.append(self._pl_point(segment.extra_points[0]))
            arg_2.append(self._pl_point(segment.extra_points[1]))
            arg_1.append(arg_2)
            arg_1 += seg_str[9:]
        self._primitives.oeditor.InsertPolylineSegment(arg_1)

        # check if the polyline has been modified correctly
        if self._check_polyline_health() is False:
            raise ValueError("Adding the segment result in an unclassified object. Undoing operation.")

        # add the points and the segment to the object
        self._positions[p_insert_position:p_insert_position] = insert_points
        self._segment_types[s_insert_position:s_insert_position] = [segment]

        return True

    @pyaedt_function_handler()
    def _check_polyline_health(self):
        # force re-evaluation of object_type
        self._object_type = None
        if self.object_type == "Unclassified":
            # Undo operation
            self._primitives._app.odesign.Undo()
            self._object_type = None
            if self.object_type == "Unclassified":
                raise RuntimeError("Undo operation failed.")
            return False
        return True


class PolylineSegment(object):
    """Creates and manipulates a segment of a polyline.

    Parameters
    ----------
    segment_type : str
        Type of the object. Choices are ``"Line"``, ``"Arc"``, ``"Spline"``,
        and ``"AngularArc"``.
    num_seg : int, optional
        Number of segments for the types ``"Arc"``, ``"Spline"``, and
        ``"AngularArc"``.  The default is ``0``. For the type
        ``Line``, this parameter is ignored.
    num_points : int, optional
        Number of control points for the type ``Spline``. For other
        types, this parameter is defined automatically.
    arc_angle : float or str, optional
        Sweep angle in radians or a valid value string. For example,
        ``"35deg"`` or ``0.25``.
        This argument is Specific to type AngularArc.
    arc_center : list or str, optional
        List of values in model units or a valid value string. For
        example, a list of ``[x, y, z]`` coordinates.
        This argument is Specific to type AngularArc.
    arc_plane : str, int optional
        Plane in which the arc sweep is performed in the active
        coordinate system ``"XY"``, ``"YZ"`` or ``"ZX"``. The default is
        ``None``, in which case the plane is determined automatically
        by the first coordinate for which the starting point and
        center point have the same value.
        This argument is Specific to type AngularArc.

    Examples
    --------
    See :class:`ansys.aedt.core.Primitives.Polyline`.

    """

    def __init__(self, segment_type, num_seg=0, num_points=0, arc_angle=0, arc_center=None, arc_plane=None):
        valid_types = ["Line", "Arc", "Spline", "AngularArc"]
        if segment_type not in valid_types:
            raise TypeError(f"Segment type must be one of {valid_types}.")
        self.type = segment_type
        if segment_type != "Line":
            self.num_seg = num_seg
        if segment_type == "Line":
            self.num_points = 2
        if segment_type == "Spline":
            self.num_points = num_points
        if "Arc" in segment_type:
            self.num_points = 3
        if segment_type == "AngularArc":
            self.arc_angle = arc_angle
            if not arc_center:
                arc_center = [0, 0, 0]
            if len(arc_center) != 3:
                raise ValueError("Arc center must be a list of length 3.")
            self.arc_center = arc_center
        if isinstance(arc_plane, int):
            if arc_plane == PLANE.XY:
                self.arc_plane = "XY"
            elif arc_plane == PLANE.ZX:
                self.arc_plane = "ZX"
            elif arc_plane == PLANE.YZ:
                self.arc_plane = "YZ"
            else:
                raise ValueError("arc_plane must be 0, 1, or 2 ")
        elif arc_plane:
            if arc_plane not in ["XY", "ZX", "YZ"]:
                raise ValueError('arc_plane must be "XY", "ZX", or "YZ" ')
            self.arc_plane = arc_plane
        else:
            self.arc_plane = None
        self.extra_points = None
