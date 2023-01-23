# standard imports
import math

from _unittest.conftest import BasisTest
from pyaedt.generic.general_methods import _to_boolean
from pyaedt.generic.general_methods import _uname
from pyaedt.generic.general_methods import is_ironpython
from pyaedt.generic.general_methods import isclose
from pyaedt.generic.general_methods import time_fn
from pyaedt.modeler.cad.elements3d import EdgePrimitive
from pyaedt.modeler.cad.elements3d import FacePrimitive

try:
    import pytest
except ImportError:
    import _unittest_ironpython.conf_unittest as pytest


class TestClass(BasisTest, object):
    def setup_class(self):
        BasisTest.my_setup(self)
        self.aedtapp = BasisTest.add_app(self, project_name="Test07")

    def teardown_class(self):
        BasisTest.my_teardown(self)

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
        return self.aedtapp.modeler.create_polyline(position_list=pointsList1, name=name)

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
        return self.aedtapp.modeler.create_sphere([0, 0, 0], radius=4, name=name, matname="Copper")

    def create_copper_cylinder(self, name=None):
        if not name:
            name = "MyCyl"
        if self.aedtapp.modeler[name]:
            self.aedtapp.modeler.delete(name)
        return self.aedtapp.modeler.create_cylinder(
            cs_axis="Y", position=[0, 0, 0], radius=1, height=20, numSides=8, name=name, matname="Copper"
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
        # assert circle.edges[0].segment_info["Command"] == "CreateCircle"

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

    def test_04_object_material_property_invalid(self):
        o_box = self.create_copper_box("Invalid1")
        o_box.material_name = "Copper1234Invalid"
        assert o_box.material_name == "copper"

    def test_04_object_material_property_valid(self):
        o_box = self.create_copper_box("Valid2")
        o_box.material_name = "aluminum"
        assert o_box.material_name == "aluminum"

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
        assert new_object.part_coordinate_system == initial_object.part_coordinate_system
        assert new_object.transparency == 0.76
        assert new_object.color == initial_object.color
        assert new_object.bounding_box == initial_object.bounding_box
        assert len(new_object.vertices) == 8
        assert len(new_object.faces) == 6
        assert len(new_object.edges) == 12
        assert new_object.display_wireframe == initial_object.display_wireframe

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

    def test_10_chamfer(self):
        initial_object = self.aedtapp.modeler.create_box([0, 0, 0], [10, 10, 5], "ChamferTest", "Copper")
        object_edges = initial_object.edges
        assert len(object_edges) == 12
        test = initial_object.edges[0].chamfer(left_distance=0.2)
        assert test
        test = initial_object.edges[1].chamfer(left_distance=0.2, right_distance=0.4, angle=34, chamfer_type=2)
        assert test
        test = initial_object.edges[2].chamfer(left_distance=0.2, right_distance=0.4, chamfer_type=1)
        assert test
        # TODO Angle as string - general refactor !
        test = initial_object.edges[6].chamfer(left_distance=1, angle=45, chamfer_type=3)
        assert test
        test = initial_object.edges[4].chamfer(chamfer_type=4)
        assert not test

        self.aedtapp.modeler.delete(initial_object)

    def test_11_fillet(self):
        initial_object = self.aedtapp.modeler.create_box([0, 0, 0], [10, 10, 5], "FilletTest", "Copper")
        object_edges = initial_object.edges
        assert len(object_edges) == 12
        test = initial_object.edges[0].fillet(radius=0.2)
        assert test
        test = initial_object.edges[1].fillet(radius=0.2, setback=0.1)
        self.aedtapp.modeler.delete(initial_object)

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
        self.aedtapp.modeler.delete(initial_object)

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

        self.aedtapp.modeler.delete("ColorTest")

    def test_print_object(self):
        o = self.create_copper_box()
        assert o.name in o.__str__()
        test_face = o.faces[0]
        assert "FaceId" in test_face.__repr__()
        assert "FaceId" in test_face.__str__()
        test_edge = test_face.edges[0]
        assert "EdgeId" in test_edge.__repr__()
        assert "EdgeId" in test_edge.__str__()
        test_vertex = test_face.vertices[0]
        assert "Vertex" in test_vertex.__repr__()
        assert "Vertex" in test_vertex.__str__()

    def test_13_delete_self(self):
        o = self.create_copper_box()
        my_name = o.name
        assert my_name in self.aedtapp.modeler.object_names
        o.delete()
        assert my_name not in self.aedtapp.modeler.object_names

    def test_14_translate_delete_self(self):
        o = self.create_copper_box()
        v0 = o.vertices[0].position
        o.translate([1, 0, 0])
        v1 = o.vertices[0].position
        assert v1[0] == v0[0] + 1.0
        assert v1[1] == v0[1]
        assert v1[2] == v0[2]
        assert o.move([1, 0, 0])

    def test_15_duplicate_around_axis_and_unite(self):
        turn = self.create_example_coil("single_turn")
        added_objects = turn.duplicate_around_axis(cs_axis="Z", angle=8, nclones=19)
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
        assert o.rotate(cs_axis="Y", angle=180)

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
        box1 = self.aedtapp.modeler.create_box([0, 0, 0], [5, 10, 2], matname="Copper")
        assert box1.mass == 893300.0
        new_material = self.aedtapp.materials.add_material("MyMaterial")
        box2 = self.aedtapp.modeler.create_box([0, 0, 0], [10, 10, 10], matname="MyMaterial")
        assert box2.mass == 0.0
        new_material.mass_density = 1
        assert isclose(box2.mass, 1000.0)
        box2.model = False
        assert box2.mass == 0.0
        rec = self.aedtapp.modeler.create_rectangle(0, [0, 0, 0], [5, 10])
        assert rec.mass == 0.0

    def test_23_volume(self):
        box3 = self.aedtapp.modeler.create_box([10, 10, 10], [5, 10, 2], matname="Copper")
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

        if not is_ironpython:
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

        if not is_ironpython:
            with pytest.raises(ValueError):
                self.aedtapp.modeler.object_list[0].edges_by_length(10, "<<")

    def test_26_unclassified_object(self):
        box1 = self.aedtapp.modeler.create_box([0, 0, 0], [2, 2, 2])
        box2 = self.aedtapp.modeler.create_box([2, 2, 2], [2, 2, 2])
        self.aedtapp.modeler.intersect([box1, box2])
        vArg1 = ["NAME:Selections", "Selections:=", ", ".join([box1.name, box2.name])]
        vArg2 = ["NAME:IntersectParameters", "KeepOriginals:=", False]

        self.aedtapp.modeler.oeditor.Intersect(vArg1, vArg2)
        assert box1 in self.aedtapp.modeler.unclassified_objects

    def test_27_get_object_history_properties(self):
        box = self.aedtapp.modeler.create_box([10, 10, 10], [15, 15, 15], "box_history", matname="Copper")
        cylinder = self.aedtapp.modeler.create_cylinder(
            cs_axis="Y",
            position=[10, 10, 10],
            radius=5,
            height=20,
            numSides=4,
            name="cylinder_history",
            matname="Copper",
        )

        box_clone = box.clone()
        box_subtract = box_clone.subtract(cylinder)
        box_subtract.rotate(cs_axis="Y", angle=180)
        box_subtract.split("XY")

        assert box.history.node == "box_history"
        assert box.history.command == "CreateBox"
        assert box.history.props["Command"] == "CreateBox"
        assert box.history.children == {}
        assert box_clone.history.node == "box_history1"
        assert box_clone.history.command == box.history.command
        assert box_clone.history.props["Command"] == box.history.props["Command"]
        assert box_clone.history.props["Position/X"] == box.history.props["Position/X"]
        assert box_clone.history.props["Position/Y"] == box.history.props["Position/Y"]
        assert box_clone.history.props["Position/Z"] == box.history.props["Position/Z"]
        assert box_clone.history.props["XSize"] == box.history.props["XSize"]
        assert box_clone.history.props["YSize"] == box_clone.history.props["YSize"]
        assert box_clone.history.props["ZSize"] == box.history.props["ZSize"]
        assert len(box_clone.history.children) == 3
        assert "Subtract:1" in box_clone.history.children.keys()
        assert "Rotate:1" in box_clone.history.children.keys()
        assert "SplitEdit:1" in box_clone.history.children.keys()
        assert box_clone.history.children["Subtract:1"].command == "Subtract"
        assert box_clone.history.children["Rotate:1"].command == "Rotate"
        assert box_clone.history.children["SplitEdit:1"].command == "SplitEdit"
        project_path = self.aedtapp.project_file
        self.aedtapp.close_project(save_project=True)
        self.aedtapp.load_project(project_path)
        subtract = self.aedtapp.modeler["box_history1"].history.children["Subtract:1"].children
        assert len(subtract) == 1
        for key in subtract.keys():
            assert subtract[key].command == subtract[key].props["Command"]
            subtract_child = subtract[key].children
            for child in subtract_child.keys():
                assert subtract_child[child].command == subtract_child[child].props["Command"]
                assert len(subtract_child[child].children) == 0

    def test_28_set_object_history_properties(self):
        assert self.aedtapp.modeler["box_history1"].history.props["Position/X"] == "10meter"
        self.aedtapp.modeler["box_history1"].history.props["Position/X"] = "15meter"
        assert self.aedtapp.modeler["box_history1"].history.props["Position/X"] == "15meter"
        assert self.aedtapp.modeler["box_history1"].history.props["ZSize"] == "15meter"
        self.aedtapp.modeler["box_history1"].history.props["ZSize"] = "10meter"
        assert self.aedtapp.modeler["box_history1"].history.props["ZSize"] == "10meter"
        subtract = self.aedtapp.modeler["box_history1"].history.children["Subtract:1"].children
        for key in subtract.keys():
            subtract_child = subtract[key].children
            for child in subtract_child.keys():
                if "CreateCylinder" in child:
                    assert subtract_child[child].props["Center Position/X"] == "10meter"
                    subtract_child[child].props["Center Position/X"] = "15meter"
                    assert subtract_child[child].props["Center Position/X"] == "15meter"
                    assert subtract_child[child].props["Axis"] == "Y"
                    subtract_child[child].props["Axis"] = "Z"
                    assert subtract_child[child].props["Axis"] == "Z"
                    assert subtract_child[child].props["Radius"] == "5meter"
                    subtract_child[child].props["Radius"] = "8meter"
                    assert subtract_child[child].props["Radius"] == "8meter"
                    assert subtract_child[child].props["Height"] == "20meter"
                    subtract_child[child].props["Height"] = "24meter"
                    assert subtract_child[child].props["Height"] == "24meter"
