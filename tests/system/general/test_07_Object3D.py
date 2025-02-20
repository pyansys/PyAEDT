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

import math

from ansys.aedt.core.generic.general_methods import _to_boolean
from ansys.aedt.core.generic.general_methods import _uname
from ansys.aedt.core.generic.general_methods import is_linux
from ansys.aedt.core.generic.general_methods import time_fn
from ansys.aedt.core.generic.numbers import isclose
from ansys.aedt.core.modeler.cad.elements_3d import EdgePrimitive
from ansys.aedt.core.modeler.cad.elements_3d import FacePrimitive
import pytest


@pytest.fixture(scope="class")
def aedtapp(add_app):
    app = add_app(project_name="Test07")
    return app


class TestClass:
    @pytest.fixture(autouse=True)
    def init(self, aedtapp, local_scratch):
        self.aedtapp = aedtapp
        self.local_scratch = local_scratch

    def create_example_coil(self, name=None):
        if not name:
            name = "test_coil"
        RI = 10
        RO = 18
        HT = 9
        N = 1.5
        tetarad = 4 * math.pi / 180

        pointsList1 = [
            [RI * math.cos(tetarad), -RI * math.sin(tetarad), HT / 2 - N],
            [(RI + N) * math.cos(tetarad), -(RI + N) * math.sin(tetarad), HT / 2],
            [RO - N, 0, HT / 2],
            [RO, 0, HT / 2 - N],
            [RO, 0, -HT / 2 + N],
            [RO - N, 0, -HT / 2],
            [(RI + N) * math.cos(tetarad), (RI + N) * math.sin(tetarad), -HT / 2],
            [RI * math.cos(tetarad), RI * math.sin(tetarad), -HT / 2 + N],
            [RI * math.cos(tetarad), RI * math.sin(tetarad), HT / 2 - N],
            [(RI + N) * math.cos(tetarad), (RI + N) * math.sin(tetarad), HT / 2],
        ]

        if self.aedtapp.modeler[name]:
            self.aedtapp.modeler.delete(name)
        return self.aedtapp.modeler.create_polyline(points=pointsList1, name=name)

    def create_copper_box(self, name=None):
        if not name:
            name = "MyBox"
        o = self.aedtapp.modeler[name]
        if not o:
            o = self.aedtapp.modeler.create_box([0, 0, 0], [10, 10, 5], name, "Copper")
        return o

    def create_copper_box_test_performance(self):
        for o in range(10):
            o = self.aedtapp.modeler.create_box([0, 0, 0], [10, 10, 5], "MyboxLoop", "Copper")

    def create_copper_sphere(self, name=None):
        if not name:
            name = "Mysphere"
        if self.aedtapp.modeler[name]:
            self.aedtapp.modeler.delete(name)
        return self.aedtapp.modeler.create_sphere([0, 0, 0], radius=4, name=name, material="Copper")

    def create_copper_cylinder(self, name=None):
        if not name:
            name = "MyCyl"
        if self.aedtapp.modeler[name]:
            self.aedtapp.modeler.delete(name)
        return self.aedtapp.modeler.create_cylinder(
            orientation="Y", origin=[0, 0, 0], radius=1, height=20, num_sides=8, name=name, material="Copper"
        )

    def test_00_uname(self):
        test = _uname()
        assert test.startswith("NewObject")

    def test_00_object_performance(self):
        time_fn(self.create_copper_box_test_performance)

    def test_01_bounding_box(self):
        l1 = len(self.aedtapp.modeler.solid_objects)
        o = self.create_copper_box()
        assert len(self.aedtapp.modeler.solid_objects) == l1 + 1
        assert len(self.aedtapp.modeler.sheet_objects) == 0
        assert len(self.aedtapp.modeler.line_objects) == 0
        assert isinstance(o.color, tuple)
        bb = o.bounding_box
        assert len(bb) == 6

    def test_01_bounding_dimension(self):
        o = self.create_copper_box()
        bd = o.bounding_dimension
        assert len(bd) == 3

    def test_01_delete_object(self):
        o = self.create_copper_box("DeleteBox")
        name = o.name
        o.delete()
        assert not self.aedtapp.modeler[name]
        assert not o.__dict__

        # 1 body and 1 sheet
        o1 = self.aedtapp.modeler.create_circle(orientation=0, origin=[0, 0, 0], radius=5)
        name1 = o1.name
        o2 = self.aedtapp.modeler.create_box(origin=[0, 0, 0], sizes=[10, 10, 10], material="vacuum")
        name2 = o2.name
        o2.delete()
        assert not self.aedtapp.modeler[name2]
        o1.delete()
        assert not self.aedtapp.modeler[name1]

    def test_01_subtract_object(self):
        o1 = self.create_copper_box("subtract_box")
        o2 = self.create_copper_sphere("subtract_sphere")
        o3 = self.create_copper_cylinder("subtract_cylinder")

        a = o1.clone()
        a.subtract(o2)

        b = o1.clone()
        b.subtract([o2, o3])

        assert len(a.faces) == 7
        assert len(b.faces) == 9

    def test_02_face_edge_vertex(self):
        o = self.create_copper_box("faces_box")
        object_faces = o.faces
        assert len(object_faces) == 6
        for face in object_faces:
            assert len(face.edges) == 4
            assert len(face.normal) == 3

        object_edges = o.edges
        for edge in object_edges:
            assert len(edge.vertices) == 2
            assert len(edge.midpoint) == 3
        assert o.edges[0].segment_info
        object_vertices = o.vertices
        for vertex in object_vertices:
            assert len(vertex.position) == 3
        circle = self.aedtapp.modeler.create_circle("Z", [0, 0, 0], 2)
        assert len(circle.faces) == 1
        circle2 = self.aedtapp.modeler.create_circle("Z", [0, 0, 0], 2, non_model=True)
        assert not circle2.model

    def test_03_FacePrimitive(self):
        o_box = self.create_copper_box("PrimitiveBox")
        o_sphere = self.create_copper_sphere("PrimitiveSphere")
        planar_face = o_box.faces[0]
        assert planar_face.center == [5.0, 5.0, 5.0]
        planar_face.move_with_offset(1)
        assert planar_face.center == [5.0, 5.0, 6.0]
        assert planar_face.normal == [0, 0, 1]
        assert isclose(planar_face.area, 100)
        non_planar_face = o_sphere.faces[0]
        assert isclose(non_planar_face.area, 201.06192982974676)
        assert non_planar_face.move_with_offset(1)
        assert isclose(non_planar_face.area, 314.1592653589793)
        assert not non_planar_face.normal
        o_box2 = self.aedtapp.modeler.create_box([300, 300, 300], [10, 10, 5], "BoxBounding", "Copper")
        for face in o_box2.faces:
            assert isinstance(face.is_on_bounding(), bool)
        assert len(o_box2.faces_on_bounding_box) == 3
        assert o_box2.face_closest_to_bounding_box.id in [i.id for i in o_box2.faces_on_bounding_box]
        assert not o_sphere.faces[0].is_planar
        assert o_box.faces[0].is_planar
        assert isinstance(o_box.largest_face()[0], FacePrimitive)
        assert isinstance(o_box.smallest_face(2), list)
        assert isinstance(o_box.longest_edge()[0], EdgePrimitive)
        assert isinstance(o_box.shortest_edge()[0], EdgePrimitive)

    def test_04a_object_material_property_invalid(self):
        o_box = self.create_copper_box("Invalid1")
        o_box.material_name = "Copper1234Invalid"
        assert o_box.material_name == "copper"

    def test_04b_object_material_property_valid(self):
        o_box = self.create_copper_box("Valid2")
        o_box.material_name = "aluminum"
        assert o_box.material_name == "aluminum"

    def test_04c_material_name_setter(self):
        self.aedtapp.materials.add_material("myMat")
        self.aedtapp.materials.add_material("myMat2")
        self.aedtapp["mat_sweep_test"] = '["myMat", "myMat2"]'
        box = self.aedtapp.modeler["MyBox"]
        box.material_name = "mat_sweep_test[0]"
        assert self.aedtapp.modeler.get_objects_by_material(material="myMat")[0].name == "MyBox"

    def test_05_object3d_properties_transparency(self):
        o = self.create_copper_box("TransparencyBox")

        o.transparency = 50
        assert o.transparency == 1.0

        o.transparency = 0.67
        assert o.transparency == 0.67

        o.transparency = 0.0
        assert o.transparency == 0.0

        o.transparency = 1.0
        assert o.transparency == 1.0

        o.transparency = -1
        assert o.transparency == 0.0

    def test_06_object3d_properties_color(self):
        o = self.create_copper_box("color_box")
        o.color = (0, 0, 255)
        assert o.color == (0, 0, 255)

    def test_07_object_clone_and_get_properties(self):
        o = self.create_copper_box("Properties_Box")
        initial_object = o
        initial_object.transparency = 0.76
        new_object = initial_object.clone()
        assert new_object.name != initial_object.name
        assert new_object.material_name == initial_object.material_name
        assert new_object.solve_inside == initial_object.solve_inside
        assert new_object.model == initial_object.model
        assert new_object.display_wireframe == initial_object.display_wireframe
        assert new_object.material_appearance == initial_object.material_appearance
        assert new_object.part_coordinate_system == initial_object.part_coordinate_system
        assert new_object.transparency == 0.76
        assert new_object.color == initial_object.color
        assert new_object.bounding_box == initial_object.bounding_box
        assert len(new_object.vertices) == 8
        assert len(new_object.faces) == 6
        assert len(new_object.edges) == 12
        new_object.name = "Properties_Box"
        assert not new_object.name == "Properties_Box"

    def test_08_set_model(self):
        o = self.create_copper_box()
        initial_object = o
        initial_object.model = False
        initial_object.draw_wireframe = True

    def test_08A_top_face(self):
        o = self.create_copper_box()
        assert isinstance(o.top_face_x, FacePrimitive)
        assert isinstance(o.top_face_y, FacePrimitive)
        assert isinstance(o.top_face_z, FacePrimitive)

    def test_08B_bottom_face(self):
        o = self.create_copper_box()
        assert isinstance(o.bottom_face_x, FacePrimitive)
        assert isinstance(o.bottom_face_y, FacePrimitive)
        assert isinstance(o.bottom_face_z, FacePrimitive)

    def test_08C_top_edge(self):
        o = self.create_copper_box()
        assert isinstance(o.faces[0].top_edge_x, EdgePrimitive)
        assert isinstance(o.faces[0].top_edge_y, EdgePrimitive)
        assert isinstance(o.faces[0].top_edge_z, EdgePrimitive)
        assert isinstance(o.top_edge_x, EdgePrimitive)
        assert isinstance(o.top_edge_y, EdgePrimitive)
        assert isinstance(o.top_edge_z, EdgePrimitive)

    def test_08D_bottom_edge(self):
        o = self.create_copper_cylinder()
        assert isinstance(o.bottom_edge_x, EdgePrimitive)
        assert isinstance(o.bottom_edge_y, EdgePrimitive)
        assert isinstance(o.bottom_edge_z, EdgePrimitive)
        for edge in o.edges:
            assert edge.segment_info

    def test_09_to_boolean(self):
        assert _to_boolean(True)
        assert not _to_boolean(False)
        assert _to_boolean("d")
        assert not _to_boolean("f")
        assert not _to_boolean("no")

    def test_10_chamfer_called_on_edge(self):
        NEW_VERTICES_POSITION = [[10.0, 0.0, 3.0], [0.0, 0.0, 3.0], [0.0, 2.0, 5.0], [10.0, 2.0, 5.0]]
        box = self.aedtapp.modeler.create_box([0, 0, 0], [10, 10, 5], "ChamferOnEdge", "Copper")

        # Chamfer type 0 (default)
        assert not (any(position in (v.position for v in box.vertices) for position in NEW_VERTICES_POSITION))
        assert box.edges[0].chamfer(left_distance=2)
        assert all(position in (v.position for v in box.vertices) for position in NEW_VERTICES_POSITION)
        self.aedtapp._odesign.Undo()

        assert box.edges[0].chamfer(left_distance=2, right_distance=3)
        self.aedtapp._odesign.Undo()

        # Chamfer type 1
        assert not (any(position in (v.position for v in box.vertices) for position in NEW_VERTICES_POSITION))
        assert box.edges[0].chamfer(left_distance=2, chamfer_type=1)
        assert all(position in (v.position for v in box.vertices) for position in NEW_VERTICES_POSITION)
        self.aedtapp._odesign.Undo()

        # Chamfer type 2
        assert not (any(position in (v.position for v in box.vertices) for position in NEW_VERTICES_POSITION))
        assert box.edges[0].chamfer(left_distance=2, angle=45, chamfer_type=2)
        assert all(position in (v.position for v in box.vertices) for position in NEW_VERTICES_POSITION)
        self.aedtapp._odesign.Undo()

        # Chamfer type 3
        assert not (any(position in (v.position for v in box.vertices) for position in NEW_VERTICES_POSITION))
        assert box.edges[0].chamfer(right_distance=2, angle=45, chamfer_type=3)
        assert all(position in (v.position for v in box.vertices) for position in NEW_VERTICES_POSITION)
        self.aedtapp._odesign.Undo()

        # Chamfer type 4 - not valid
        assert not box.edges[0].chamfer(chamfer_type=4)

    def test_10_chamfer_called_on_box(self):
        NEW_VERTICES_POSITION = [[10.0, 0.0, 3.0], [0.0, 0.0, 3.0], [0.0, 2.0, 5.0], [10.0, 2.0, 5.0]]
        box = self.aedtapp.modeler.create_box([0, 0, 0], [10, 10, 5], "ChamferOnBox", "Copper")

        # Chamfer type 0 (default)
        assert not (any(position in (v.position for v in box.vertices) for position in NEW_VERTICES_POSITION))
        box.chamfer(edges=box.faces[0].edges[0], left_distance=2)
        assert all(position in (v.position for v in box.vertices) for position in NEW_VERTICES_POSITION)
        self.aedtapp._odesign.Undo()

        assert box.chamfer(edges=box.faces[0].edges[0], left_distance=2, right_distance=3)
        self.aedtapp._odesign.Undo()

        # Chamfer type 1
        assert not (any(position in (v.position for v in box.vertices) for position in NEW_VERTICES_POSITION))
        assert box.chamfer(edges=box.faces[0].edges[0], left_distance=2, chamfer_type=1)
        assert all(position in (v.position for v in box.vertices) for position in NEW_VERTICES_POSITION)
        self.aedtapp._odesign.Undo()

        # Chamfer type 2
        assert not (any(position in (v.position for v in box.vertices) for position in NEW_VERTICES_POSITION))
        assert box.chamfer(edges=box.faces[0].edges[0], left_distance=2, angle=45, chamfer_type=2)
        assert all(position in (v.position for v in box.vertices) for position in NEW_VERTICES_POSITION)
        self.aedtapp._odesign.Undo()

        # Chamfer type 3
        assert not (any(position in (v.position for v in box.vertices) for position in NEW_VERTICES_POSITION))
        assert box.chamfer(edges=box.faces[0].edges[0], right_distance=2, angle=45, chamfer_type=3)
        assert all(position in (v.position for v in box.vertices) for position in NEW_VERTICES_POSITION)
        self.aedtapp._odesign.Undo()

        # Chamfer type 4 - not valid
        assert not box.chamfer(edges=box.faces[0].edges[0], right_distance=2, chamfer_type=4)

    def test_11_fillet(self):
        initial_object = self.aedtapp.modeler.create_box([0, 0, 0], [10, 10, 5], "FilletTest", "Copper")
        object_edges = initial_object.edges
        assert len(object_edges) == 12
        test = initial_object.edges[0].fillet(radius=0.2)
        assert test
        test = initial_object.edges[1].fillet(radius=0.2, setback=0.1)
        self.aedtapp.modeler.delete(
            initial_object,
        )

    def test_object_length(self):
        initial_object = self.aedtapp.modeler.create_box([0, 0, 0], [10, 10, 5], "FilletTest", "Copper")
        test_edge = initial_object.edges[0]
        assert isinstance(test_edge.length, float)

        start_point = initial_object.edges[0].vertices[0]
        end_point = initial_object.edges[0].vertices[1]
        sum_sq = 0
        for i in range(0, 3):
            sum_sq += (end_point.position[i] - start_point.position[i]) ** 2
        assert isclose(math.sqrt(sum_sq), test_edge.length)
        self.aedtapp.modeler.delete(
            initial_object,
        )

    def test_12_set_color(self):
        initial_object = self.aedtapp.modeler.create_box([0, 0, 0], [10, 10, 5], "ColorTest")
        initial_object.color = "Red"
        assert initial_object.color == (255, 0, 0)
        initial_object.color = "Green"
        assert initial_object.color == (0, 128, 0)
        initial_object.color = "Blue"
        assert initial_object.color == (0, 0, 255)
        initial_object.color = (255, 0, 0)
        assert initial_object.color == (255, 0, 0)
        initial_object.color = "(255 0 0)"
        assert initial_object.color == (255, 0, 0)

        initial_object.color = "(300 0 0)"
        assert initial_object.color == (255, 0, 0)

        initial_object.color = "(123 0 0 55)"
        assert initial_object.color == (255, 0, 0)

        initial_object.color = "InvalidString"
        assert initial_object.color == (255, 0, 0)

        initial_object.color = (255, "Invalid", 0)
        assert initial_object.color == (255, 0, 0)

        self.aedtapp.modeler.delete(
            "ColorTest",
        )

    def test_print_object(self):
        o = self.create_copper_box()
        assert o.name in o.__str__()
        test_face = o.faces[0]
        assert isinstance(int(test_face.__str__()), int)
        assert isinstance(int(test_face.__repr__()), int)
        test_edge = test_face.edges[0]
        assert isinstance(int(test_edge.__str__()), int)
        assert isinstance(int(test_edge.__repr__()), int)
        test_vertex = test_face.vertices[0]
        assert isinstance(int(test_vertex.__str__()), int)
        assert isinstance(int(test_vertex.__repr__()), int)

    def test_13_delete_self(self):
        o = self.create_copper_box()
        my_name = o.name
        assert my_name in self.aedtapp.modeler.object_names
        o.delete()
        assert my_name not in self.aedtapp.modeler.object_names

    def test_14_translate_delete_self(self):
        o = self.create_copper_box()
        v0 = o.vertices[0].position
        o.move(
            [1, 0, 0],
        )
        v1 = o.vertices[0].position
        assert v1[0] == v0[0] + 1.0
        assert v1[1] == v0[1]
        assert v1[2] == v0[2]
        assert o.move(
            [1, 0, 0],
        )

    def test_15_duplicate_around_axis_and_unite(self):
        turn = self.create_example_coil("single_turn")
        added_objects = turn.duplicate_around_axis(axis="Z", angle=8, clones=19)
        turn.unite(added_objects)
        assert len(added_objects) == 18
        assert "single_turn" in self.aedtapp.modeler.line_names

    def test_16_duplicate_around_axis_and_unite(self):
        turn = self.create_example_coil("single_turn")
        added_objects = turn.duplicate_along_line([0, 0, 15], nclones=3, attachObject=False)
        assert len(added_objects) == 2
        assert "single_turn" in self.aedtapp.modeler.line_names

    def test_17_section_object(self):
        o = self.aedtapp.modeler.create_box([-10, 0, 0], [10, 10, 5], "SectionBox", "Copper")
        o.section(plane="YZ", create_new=True, section_cross_object=False)

    def test_18_create_spiral(self):
        sp1 = self.aedtapp.modeler.create_spiral(name="ind")
        assert sp1
        assert sp1.name == "ind"
        assert len(sp1.points) == 78

    def test_19_rotate(self):
        o = self.aedtapp.modeler.create_box([-10, 0, 0], [10, 10, 5], "RotateBox", "Copper")
        assert o.rotate(axis="Y", angle=180)

    def test_20_mirror(self):
        o = self.aedtapp.modeler.create_box([-10, 0, 0], [10, 10, 5], "MirrorBox", "Copper")
        assert o.mirror(position=[-10, 0, 0], vector=[0, 1, 0])

    def test_21_groups(self):
        o1 = self.aedtapp.modeler.create_box([-10, 0, 0], [10, 10, 5], "GroupB1", "Copper")
        o2 = self.aedtapp.modeler.create_box([-10, 0, 0], [10, 10, 5], "GroupB2", "Copper")
        assert o1.group_name == "Model"
        o1.group_name = "NewGroup"
        assert o1.group_name == "NewGroup"
        o2.group_name = "NewGroup"
        assert o2.group_name == "NewGroup"
        o2.group_name = "NewGroup2"
        assert o2.group_name == "NewGroup2"
        assert o1.group_name == "NewGroup"

    def test_22_mass(self):
        self.aedtapp.modeler.model_units = "meter"
        box1 = self.aedtapp.modeler.create_box([0, 0, 0], [5, 10, 2], material="Copper")
        assert box1.mass == 893300.0
        new_material = self.aedtapp.materials.add_material("MyMaterial")
        box2 = self.aedtapp.modeler.create_box([0, 0, 0], [10, 10, 10], material="MyMaterial")
        assert box2.mass == 0.0
        new_material.mass_density = 1
        assert isclose(box2.mass, 1000.0)
        box2.model = False
        assert box2.mass == 0.0
        rec = self.aedtapp.modeler.create_rectangle(0, [0, 0, 0], [5, 10])
        assert rec.mass == 0.0

    def test_23_volume(self):
        box3 = self.aedtapp.modeler.create_box([10, 10, 10], [5, 10, 2], material="Copper")
        assert isclose(box3.volume, 100)
        rec = self.aedtapp.modeler.create_rectangle(0, [0, 0, 0], [5, 10])
        assert rec.volume == 0.0

    def test_24_filter_faces_by_area(self):
        faces_equal = []
        for obj in self.aedtapp.modeler.object_list:
            if obj.faces_by_area(100):
                faces_equal.append(obj.faces_by_area(100))
        if faces_equal:
            for face_object in faces_equal:
                for face in face_object:
                    assert abs(face.area - 100) < 1e-12

        faces_greater_equal = []
        for obj in self.aedtapp.modeler.object_list:
            if obj.faces_by_area(100, ">="):
                faces_greater_equal.append(obj.faces_by_area(100, ">="))
        if faces_greater_equal:
            for face_object in faces_greater_equal:
                for face in face_object:
                    assert (face.area - 100) >= -1e-12

        faces_smaller_equal = []
        for obj in self.aedtapp.modeler.object_list:
            if obj.faces_by_area(100, "<="):
                faces_smaller_equal.append(obj.faces_by_area(100, "<="))
        if faces_smaller_equal:
            for face_object in faces_smaller_equal:
                for face in face_object:
                    assert (face.area - 100) <= 1e-12

        faces_greater = []
        for obj in self.aedtapp.modeler.object_list:
            if obj.faces_by_area(99, ">"):
                faces_greater.append(obj.faces_by_area(99, ">"))
        if faces_greater:
            for face_object in faces_greater:
                for face in face_object:
                    assert (face.area - 99) > 0

        faces_smaller = []
        for obj in self.aedtapp.modeler.object_list:
            if obj.faces_by_area(105, "<"):
                faces_smaller.append(obj.faces_by_area(105, "<"))
        if faces_smaller:
            for face_object in faces_smaller:
                for face in face_object:
                    assert (face.area - 105) < 0

        with pytest.raises(ValueError):
            self.aedtapp.modeler.object_list[0].faces_by_area(100, "<<")

    def test_25_edges_by_length(self):
        edges_equal = []
        for obj in self.aedtapp.modeler.object_list:
            if obj.edges_by_length(10):
                edges_equal.append(obj.edges_by_length(10))
        if edges_equal:
            for edge_object in edges_equal:
                for edge in edge_object:
                    assert abs(edge.length - 10) < 1e-12

        edges_greater_equal = []
        for obj in self.aedtapp.modeler.object_list:
            if obj.edges_by_length(10, ">="):
                edges_greater_equal.append(obj.edges_by_length(10, ">="))
        if edges_greater_equal:
            for edge_object in edges_greater_equal:
                for edge in edge_object:
                    assert (edge.length - 10) >= -1e-12

        edges_smaller_equal = []
        for obj in self.aedtapp.modeler.object_list:
            if obj.edges_by_length(10, "<="):
                edges_smaller_equal.append(obj.edges_by_length(10, "<="))
        if edges_smaller_equal:
            for edge_object in edges_smaller_equal:
                for edge in edge_object:
                    assert (edge.length - 10) <= 1e-12

        edges_greater = []
        for obj in self.aedtapp.modeler.object_list:
            if obj.edges_by_length(9, ">"):
                edges_greater.append(obj.edges_by_length(9, ">"))
        if edges_greater:
            for edge_object in edges_greater:
                for edge in edge_object:
                    assert (edge.length - 9) > 0

        edges_smaller = []
        for obj in self.aedtapp.modeler.object_list:
            if obj.edges_by_length(15, "<"):
                edges_smaller.append(obj.edges_by_length(15, "<"))
        if edges_smaller:
            for edge_object in edges_smaller:
                for edge in edge_object:
                    assert (edge.length - 15) < 0

        with pytest.raises(ValueError):
            self.aedtapp.modeler.object_list[0].edges_by_length(10, "<<")

    def test_26_unclassified_object(self):
        box1 = self.aedtapp.modeler.create_box([0, 0, 0], [2, 2, 2])
        box2 = self.aedtapp.modeler.create_box([2, 2, 2], [2, 2, 2])
        self.aedtapp.modeler.intersect(
            [box1, box2],
        )
        vArg1 = ["NAME:Selections", "Selections:=", ", ".join([box1.name, box2.name])]
        vArg2 = ["NAME:IntersectParameters", "KeepOriginals:=", False]

        self.aedtapp.modeler.oeditor.Intersect(vArg1, vArg2)
        assert box1.name in self.aedtapp.modeler.unclassified_names

    def test_26a_delete_unclassified_object(self):
        unclassified = self.aedtapp.modeler.unclassified_objects
        assert self.aedtapp.modeler.delete(
            unclassified,
        )
        assert len(self.aedtapp.modeler.unclassified_objects) != unclassified
        assert len(self.aedtapp.modeler.unclassified_objects) == 0

    def test_27_get_object_history_properties(self):
        box = self.aedtapp.modeler.create_box([10, 10, 10], [15, 15, 15], "box_history", material="Copper")
        cylinder = self.aedtapp.modeler.create_cylinder(
            orientation="Y",
            origin=[10, 10, 10],
            radius=5,
            height=20,
            num_sides=4,
            name="cylinder_history",
            material="Copper",
        )

        box_clone = box.clone()
        box_subtract = box_clone.subtract(cylinder)
        box_subtract.rotate(axis="Y", angle=180)
        box_subtract.split("XY")
        box_history = box.history()
        box_clone_history = box_clone.history()
        assert box_history._node == "box_history"
        assert box_history.command == "CreateBox"
        assert box_history.properties["Command"] == "CreateBox"
        assert box_history.children == {}
        assert box_clone_history._node == "box_history1"
        assert box_clone_history.command == box_history.command
        assert box_clone_history.properties["Command"] == box_history.properties["Command"]
        assert box_clone_history.properties["Position/X"] == box_history.properties["Position/X"]
        assert box_clone_history.properties["Position/Y"] == box_history.properties["Position/Y"]
        assert box_clone_history.properties["Position/Z"] == box_history.properties["Position/Z"]
        assert box_clone_history.properties["XSize"] == box_history.properties["XSize"]
        assert box_clone_history.properties["YSize"] == box_history.properties["YSize"]
        assert box_clone_history.properties["ZSize"] == box_history.properties["ZSize"]
        assert len(box_clone_history.children) == 3
        assert "Subtract:1" in box_clone_history.children.keys()
        assert "Rotate:1" in box_clone_history.children.keys()
        assert "SplitEdit:1" in box_clone_history.children.keys()
        assert box_clone_history.children["Subtract:1"].command == "Subtract"
        assert box_clone_history.children["Rotate:1"].command == "Rotate"
        assert box_clone_history.children["SplitEdit:1"].command == "SplitEdit"
        project_path = self.aedtapp.project_file
        self.aedtapp.close_project(save=True)
        self.aedtapp.load_project(project_path)
        subtract = self.aedtapp.modeler["box_history1"].history().children["Subtract:1"].children
        assert len(subtract) == 1
        for key in subtract.keys():
            assert subtract[key].command == subtract[key].properties["Command"]
            subtract_child = subtract[key].children
            for child in subtract_child.keys():
                assert subtract_child[child].command == subtract_child[child].properties["Command"]
                assert len(subtract_child[child].children) == 0

    def test_27b_object_suppress(self):
        box = self.aedtapp.modeler.get_object_from_name("box_history1")
        assert box.history().suppress_all(self.aedtapp)
        assert box.history().unsuppress_all(self.aedtapp)

    def test_27c_object_jsonalize(self):
        box = self.aedtapp.modeler.get_object_from_name("box_history1")
        assert box.history().jsonalize_tree()

    def test_28_set_object_history_properties(self):
        history = self.aedtapp.modeler["box_history1"].history()
        assert history.properties["Position/X"] == "10meter"
        history.properties["Position/X"] = "15meter"
        assert history.properties["Position/X"] == "15meter"
        assert history.properties["ZSize"] == "15meter"
        history.properties["ZSize"] = "10meter"
        assert history.properties["ZSize"] == "10meter"
        subtract = history.children["Subtract:1"].children
        for key in subtract.keys():
            subtract_child = subtract[key].children
            for child in subtract_child.keys():
                if "CreateCylinder" in child:
                    assert subtract_child[child].properties["Center Position/X"] == "10meter"
                    subtract_child[child].properties["Center Position/X"] = "15meter"
                    assert subtract_child[child].properties["Center Position/X"] == "15meter"
                    assert subtract_child[child].properties["Axis"] == "Y"
                    subtract_child[child].properties["Axis"] = "Z"
                    assert subtract_child[child].properties["Axis"] == "Z"
                    assert subtract_child[child].properties["Radius"] == "5meter"
                    subtract_child[child].properties["Radius"] = "8meter"
                    assert subtract_child[child].properties["Radius"] == "8meter"
                    assert subtract_child[child].properties["Height"] == "20meter"
                    subtract_child[child].properties["Height"] = "24meter"
                    assert subtract_child[child].properties["Height"] == "24meter"

    def test_29_test_nets(self):
        self.aedtapp.insert_design("nets")
        self.aedtapp.modeler.create_box([0, 0, 0], [5, 10, 10], material="copper")
        self.aedtapp.modeler.create_box([30, 0, 0], [5, 10, 10], material="copper")
        self.aedtapp.modeler.create_box([60, 0, 0], [5, 10, 10], material="vacuum")
        nets = self.aedtapp.identify_touching_conductors()
        assert len(nets) == 2

    def test_62_heal_objects(self):
        self.aedtapp.insert_design("Heal_Objects")
        self.aedtapp.modeler.create_box([0, 1.5, 0], [1, 2.5, 5], name="box_1")
        self.aedtapp.modeler.create_box([0, 1.5, 0], [1, 2.5, 5], name="box_2")
        assert self.aedtapp.modeler.heal_objects(assignment="box_1")
        assert self.aedtapp.modeler.heal_objects(assignment="box_1,box_2")
        assert self.aedtapp.modeler.heal_objects(assignment="box_1, box_2 ")
        assert not self.aedtapp.modeler.heal_objects(assignment=["box_1", "box_2"])
        assert not self.aedtapp.modeler.heal_objects(assignment="box_1", simplify_type=3)
        assert self.aedtapp.modeler.heal_objects(assignment="box_1", max_stitch_tolerance="0.01")
        assert self.aedtapp.modeler.heal_objects(assignment="box_1", max_stitch_tolerance=0.01)
        assert self.aedtapp.modeler.heal_objects(assignment="box_1", geometry_simplification_tolerance=1.2)
        assert self.aedtapp.modeler.heal_objects(assignment="box_1", geometry_simplification_tolerance="1.2")
        assert self.aedtapp.modeler.heal_objects(assignment="box_1", tighten_gaps_width=0.001)
        assert self.aedtapp.modeler.heal_objects(assignment="box_1", tighten_gaps_width="0.001")
        assert self.aedtapp.modeler.heal_objects(assignment="box_1", silver_face_tolerance=1.2)
        assert self.aedtapp.modeler.heal_objects(assignment="box_1", silver_face_tolerance="1.2")
        assert not self.aedtapp.modeler.heal_objects(assignment=None)
        assert not self.aedtapp.modeler.heal_objects(assignment=1)

    @pytest.mark.skipif(is_linux, reason="Crashing in linux")
    def test_20_simplify_objects(self):
        assert self.aedtapp.modeler.simplify_objects(assignment="box_1")
        assert self.aedtapp.modeler.simplify_objects(assignment="box_1,box_2")
        assert self.aedtapp.modeler.simplify_objects(assignment="box_1, box_2")
        assert not self.aedtapp.modeler.simplify_objects(assignment=["box_1", "box_2"])
        assert self.aedtapp.modeler.simplify_objects(assignment="box_1", simplify_type="Primitive Fit")
        assert not self.aedtapp.modeler.simplify_objects(assignment="box_1", simplify_type="Invalid")
        assert not self.aedtapp.modeler.simplify_objects(
            assignment="box_1", simplify_type="Polygon Fit", extrusion_axis="U"
        )
        assert not self.aedtapp.modeler.simplify_objects(assignment=None)
        assert not self.aedtapp.modeler.simplify_objects(assignment=1)

    def test_30_rescale(self):
        self.aedtapp.modeler.model_units = "meter"
        box1 = self.aedtapp.modeler.create_box([0, 0, 0], [5, 10, 2], material="Copper")
        assert box1.mass == 893300.0
        self.aedtapp.modeler.rescale_model = True
        self.aedtapp.modeler.model_units = "mm"
        assert round(box1.mass, 5) == 0.00089
