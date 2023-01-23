# standard imports
import os
import sys
import time

try:
    import pytest
except ImportError:
    import _unittest_ironpython.conf_unittest as pytest

# Setup paths for module imports
from _unittest.conftest import BasisTest
from _unittest.conftest import config
from _unittest.conftest import local_path
from pyaedt.generic.constants import AXIS
from pyaedt.generic.general_methods import is_ironpython
from pyaedt.modeler.cad.components_3d import UserDefinedComponent
from pyaedt.modeler.cad.object3d import Object3d
from pyaedt.modeler.cad.polylines import Polyline
from pyaedt.modeler.cad.Primitives import PolylineSegment
from pyaedt.modeler.geometry_operators import GeometryOperators

test = sys.modules.keys()

scdoc = "input.scdoc"
step = "input.stp"
component3d = "new.a3dcomp"
encrypted_cylinder = "encrypted_cylinder.a3dcomp"
test_subfolder = "T08"
if config["desktopVersion"] > "2022.2":
    assembly = "assembly_231"
    assembly2 = "assembly2_231"
    components_flatten = "components_flatten_231"
else:
    assembly = "assembly"
    assembly2 = "assembly2"
    components_flatten = "components_flatten"


class TestClass(BasisTest, object):
    def setup_class(self):
        BasisTest.my_setup(self)
        self.aedtapp = BasisTest.add_app(self, project_name="test_primitives", design_name="3D_Primitives")
        scdoc_file = os.path.join(local_path, "example_models", test_subfolder, scdoc)
        self.local_scratch.copyfile(scdoc_file)
        self.step_file = os.path.join(local_path, "example_models", test_subfolder, step)
        self.component3d_file = os.path.join(self.local_scratch.path, component3d)
        self.encrypted_cylinder = os.path.join(local_path, "example_models", test_subfolder, encrypted_cylinder)
        test_98_project = os.path.join(local_path, "example_models", test_subfolder, assembly2 + ".aedt")
        self.test_98_project = self.local_scratch.copyfile(test_98_project)
        test_99_project = os.path.join(local_path, "example_models", test_subfolder, assembly + ".aedt")
        self.test_99_project = self.local_scratch.copyfile(test_99_project)
        self.flatten = BasisTest.add_app(self, project_name=components_flatten, subfolder=test_subfolder)

    def teardown_class(self):
        BasisTest.my_teardown(self)

    def create_copper_box(self, name=None):
        if not name:
            name = "MyBox"
        if self.aedtapp.modeler[name]:
            self.aedtapp.modeler.delete(name)
        else:
            pass
        new_object = self.aedtapp.modeler.create_box([0, 0, 0], [10, 10, 5], name, "Copper")
        return new_object

    def create_copper_sphere(self, name=None):
        if not name:
            name = "Mysphere"
        if self.aedtapp.modeler[name]:
            self.aedtapp.modeler.delete(name)
        return self.aedtapp.modeler.create_sphere([0, 0, 0], radius="1mm", name=name, matname="Copper")

    def create_copper_cylinder(self, name=None):
        if not name:
            name = "MyCyl"
        if self.aedtapp.modeler[name]:
            self.aedtapp.modeler.delete(name)
        return self.aedtapp.modeler.create_cylinder(
            cs_axis="Y", position=[20, 20, 0], radius=5, height=20, numSides=8, name=name, matname="Copper"
        )

    def create_rectangle(self, name=None):
        if not name:
            name = "MyRectangle"
        if self.aedtapp.modeler[name]:
            self.aedtapp.modeler.delete(name)
        plane = self.aedtapp.PLANE.XY
        return self.aedtapp.modeler.create_rectangle(plane, [5, 3, 8], [4, 5], name=name)

    def create_copper_torus(self, name=None):
        if not name:
            name = "MyTorus"
        if self.aedtapp.modeler[name]:
            self.aedtapp.modeler.delete(name)
        return self.aedtapp.modeler.create_torus(
            [30, 30, 0], major_radius=1.2, minor_radius=0.5, axis="Z", name=name, material_name="Copper"
        )

    def create_polylines(self, name=None):
        if not name:
            name = "Poly_"

        test_points = [[0, 100, 0], [-100, 0, 0], [-50, -50, 0], [0, 0, 0]]

        if self.aedtapp.modeler[name + "segmented"]:
            self.aedtapp.modeler.delete(name + "segmented")

        if self.aedtapp.modeler[name + "compound"]:
            self.aedtapp.modeler.delete(name + "compound")

        p1 = self.aedtapp.modeler.create_polyline(position_list=test_points, name=name + "segmented")
        p2 = self.aedtapp.modeler.create_polyline(
            position_list=test_points, segment_type=["Line", "Arc"], name=name + "compound"
        )
        return p1, p2, test_points

    def test_01_resolve_object(self):
        o = self.aedtapp.modeler.create_box([0, 0, 0], [10, 10, 5], "MyCreatedBox", "Copper")
        o1 = self.aedtapp.modeler._resolve_object(o)
        o2 = self.aedtapp.modeler._resolve_object(o.id)
        o3 = self.aedtapp.modeler._resolve_object(o.name)

        assert isinstance(o1, Object3d)
        assert isinstance(o2, Object3d)
        assert isinstance(o3, Object3d)
        assert o1.id == o.id
        assert o2.id == o.id
        assert o3.id == o.id
        oinvalid1 = self.aedtapp.modeler._resolve_object(-1)
        oinvalid2 = self.aedtapp.modeler._resolve_object("FrankInvalid")
        assert not oinvalid1
        assert not oinvalid2

    def test_02_create_box(self):
        o = self.aedtapp.modeler.create_box([0, 0, 0], [10, 10, 5], "MyCreatedBox_11", "Copper")
        assert o.id > 0
        assert o.name.startswith("MyCreatedBox_11")
        assert o.object_type == "Solid"
        assert o.is3d == True
        assert o.material_name == "copper"
        assert "MyCreatedBox_11" in self.aedtapp.modeler.solid_names
        assert len(self.aedtapp.modeler.object_names) == len(self.aedtapp.modeler.objects)

    def test_03_create_box_assertions(self):
        try:
            invalid_entry = "Frank"
            self.aedtapp.modeler.create_box([0, 0, 0], invalid_entry, "MyCreatedBox", "Copper")
            assert False
        except AssertionError:
            pass

    def test_04_create_polyhedron(self):

        o1 = self.aedtapp.modeler.create_polyhedron()
        assert o1.id > 0
        assert o1.name.startswith("New")
        assert o1.object_type == "Solid"
        assert o1.is3d == True
        assert o1.material_name == "vacuum"
        assert o1.solve_inside

        o2 = self.aedtapp.modeler.create_polyhedron(
            cs_axis=AXIS.Z,
            center_position=[0, 0, 0],
            start_position=[0, 1, 0],
            height=2.0,
            num_sides=5,
            name="MyPolyhedron",
            matname="Aluminum",
        )
        assert o2.id > 0
        assert o2.object_type == "Solid"
        assert o2.is3d == True
        assert o2.material_name == "aluminum"
        assert o2.solve_inside == False

        assert o1.name in self.aedtapp.modeler.solid_names
        assert o2.name in self.aedtapp.modeler.solid_names
        assert len(self.aedtapp.modeler.object_names) == len(self.aedtapp.modeler.objects)
        pass

    def test_05_center_and_centroid(self):
        o = self.create_copper_box()
        tol = 1e-9
        assert GeometryOperators.v_norm(o.faces[0].center_from_aedt) - GeometryOperators.v_norm(o.faces[0].center) < tol

    def test_11_get_object_name_from_edge(self):
        o = self.create_copper_box()
        edge = o.edges[0].id
        assert self.aedtapp.modeler.get_object_name_from_edge_id(edge) == o.name

        udp = self.aedtapp.modeler.Position(0, 0, 0)
        dimensions = [10, 10, 5]
        o = self.aedtapp.modeler.create_box(udp, dimensions)
        assert len(o.name) == 16
        assert o.material_name == "vacuum"

    def test_11a_get_faces_from_mat(self):
        self.create_copper_box()
        faces = self.aedtapp.modeler.get_faces_from_materials("Copper")
        assert len(faces) >= 6

    def test_11b_check_object_faces(self):
        o = self.create_copper_box()
        face_list = o.faces
        assert len(face_list) == 6
        f = o.faces[0]
        assert isinstance(f.center, list) and len(f.center) == 3
        assert isinstance(f.area, float) and f.area > 0
        assert o.faces[0].move_with_offset(0.1)
        assert o.faces[0].move_with_vector([0, 0, 0.01])
        assert type(f.normal) is list

    def test_11c_check_object_edges(self):
        o = self.create_copper_box(name="MyBox")
        e = o.edges[1]
        assert isinstance(e.midpoint, list) and len(e.midpoint) == 3
        assert isinstance(e.length, float) and e.length > 0

    def test_11d_check_object_vertices(self):
        o = self.create_copper_box(name="MyBox")
        assert len(o.vertices) == 8
        v = o.vertices[0]
        assert isinstance(v.position, list) and len(v.position) == 3

    def test_12_get_objects_in_group(self):
        objs = self.aedtapp.modeler.get_objects_in_group("Solids")
        assert type(objs) is list

    def test_13_create_circle(self):
        udp = self.aedtapp.modeler.Position(5, 3, 8)
        plane = self.aedtapp.PLANE.XY
        o = self.aedtapp.modeler.create_circle(plane, udp, 2, name="MyCircle", matname="Copper")
        assert o.id > 0
        assert o.name.startswith("MyCircle")
        assert o.object_type == "Sheet"
        assert o.is3d is False
        assert not o.solve_inside

    def test_14_create_sphere(self):
        udp = self.aedtapp.modeler.Position(20, 20, 0)
        radius = 5
        o = self.aedtapp.modeler.create_sphere(udp, radius, "MySphere", "Copper")
        assert o.id > 0
        assert o.name.startswith("MySphere")
        assert o.object_type == "Solid"
        assert o.is3d is True

    def test_15_create_cylinder(self):
        udp = self.aedtapp.modeler.Position(20, 20, 0)
        axis = self.aedtapp.AXIS.Y
        radius = 5
        height = 50
        o = self.aedtapp.modeler.create_cylinder(axis, udp, radius, height, 8, "MyCyl", "Copper")
        assert o.id > 0
        assert o.name.startswith("MyCyl")
        assert o.object_type == "Solid"
        assert o.is3d is True
        pass

    def test_16_create_ellipse(self):
        udp = self.aedtapp.modeler.Position(5, 3, 8)
        plane = self.aedtapp.PLANE.XY
        o1 = self.aedtapp.modeler.create_ellipse(plane, udp, 5, 1.5, True, name="MyEllpise01", matname="Copper")
        assert o1.id > 0
        assert o1.name.startswith("MyEllpise01")
        assert o1.object_type == "Sheet"
        assert o1.is3d is False
        assert not o1.solve_inside

        o2 = self.aedtapp.modeler.create_ellipse(plane, udp, 5, 1.5, True, name="MyEllpise01", matname="Vacuum")
        assert o2.id > 0
        assert o2.name.startswith("MyEllpise01")
        assert o2.object_type == "Sheet"
        assert o2.is3d is False
        assert not o2.solve_inside

        o3 = self.aedtapp.modeler.create_ellipse(plane, udp, 5, 1.5, False, name="MyEllpise02")
        assert o3.id > 0
        assert o3.name.startswith("MyEllpise02")
        assert o3.object_type == "Line"
        assert o3.is3d is False
        assert not o3.solve_inside

    def test_17_create_object_from_edge(self):
        o = self.create_copper_cylinder()
        edges = o.edges
        o1 = self.aedtapp.modeler.create_object_from_edge(edges[0])
        assert o1.id > 0
        assert o1.object_type == "Line"
        assert o1.is3d is False
        assert o1.model
        o2 = self.aedtapp.modeler[o.name].edges[0].create_object(non_model=True)
        assert o2.id > 0
        assert o2.object_type == "Line"
        assert o2.is3d is False
        assert o2.model is False
        o3 = self.create_copper_cylinder("cyl_e1")
        o4 = self.create_copper_cylinder("cyl_e2")
        of = self.aedtapp.modeler.create_object_from_edge([o4.edges[0], o3.edges[1], o4.edges[1]])
        assert of
        assert len(of) == 3
        pass

    def test_18_create_object_from_face(self):
        o = self.create_copper_cylinder()
        faces = o.faces
        o1 = self.aedtapp.modeler.create_object_from_face(faces[0])
        assert o1.id > 0
        assert o1.object_type == "Sheet"
        assert o1.is3d is False
        o2 = self.aedtapp.modeler[o.name].faces[0].create_object(non_model=True)
        assert o2.id > 0
        assert o2.object_type == "Sheet"
        assert o2.is3d is False
        assert o2.model is False
        o3s = self.aedtapp.modeler.create_object_from_face(faces)
        assert isinstance(o3s, list)
        assert o3s[0].id > 0
        o3 = self.create_copper_cylinder("cyl_f1")
        o4 = self.create_copper_cylinder("cyl_f2")
        of = self.aedtapp.modeler.create_object_from_face([o3.faces[0], o4.faces[1], o4.faces[1], o3.faces[2]])
        assert of
        assert len(of) == 4
        pass

    def test_19_create_polyline(self):
        udp1 = [0, 0, 0]
        udp2 = [5, 0, 0]
        udp3 = [5, 5, 0]
        udp4 = [2, 5, 3]
        arrofpos = [udp1, udp4, udp2, udp3, udp1]
        P = self.aedtapp.modeler.create_polyline(arrofpos, cover_surface=True, name="Poly1", matname="Copper")
        assert isinstance(P, Polyline)
        assert isinstance(P, Object3d)
        assert P.object_type == "Sheet"
        assert P.is3d == False
        assert isinstance(P.color, tuple)
        get_P = self.aedtapp.modeler["Poly1"]
        assert isinstance(get_P, Polyline)
        P2 = self.aedtapp.modeler.create_polyline(
            arrofpos, cover_surface=False, name="Poly_nonmodel", matname="Copper", non_model=True
        )
        assert P2.model == False

    def test_20_create_polyline_with_crosssection(self):
        udp1 = [0, 0, 0]
        udp2 = [5, 0, 0]
        udp3 = [5, 5, 0]
        udp4 = [2, 5, 3]
        arrofpos = [udp1, udp2, udp3]
        P = self.aedtapp.modeler.create_polyline(arrofpos, name="Poly_xsection", xsection_type="Rectangle")
        assert isinstance(P, Polyline)
        assert self.aedtapp.modeler[P.id].object_type == "Solid"
        assert self.aedtapp.modeler[P.id].is3d == True

    def test_21_sweep_along_path(self):
        udp1 = [0, 0, 0]
        udp2 = [5, 0, 0]
        udp3 = [5, 5, 0]
        arrofpos = [udp1, udp2, udp3]
        path = self.aedtapp.modeler.create_polyline(arrofpos, name="poly_vector")
        my_name = path.name
        assert my_name in self.aedtapp.modeler.line_names
        assert my_name in self.aedtapp.modeler.model_objects
        assert my_name in self.aedtapp.modeler.object_names
        assert isinstance(self.aedtapp.modeler.get_vertices_of_line(my_name), list)
        rect = self.aedtapp.modeler.create_rectangle(self.aedtapp.PLANE.YZ, [0, -2, -2], [4, 3], name="rect_1")
        swept = self.aedtapp.modeler.sweep_along_path(rect, path)
        assert swept
        assert rect.name in self.aedtapp.modeler.solid_names

    def test_22_sweep_along_vector(self):
        rect2 = self.aedtapp.modeler.create_rectangle(self.aedtapp.PLANE.YZ, [0, -2, -2], [4, 3], name="rect_2")
        assert self.aedtapp.modeler.sweep_along_vector(rect2, [10, 20, 20])
        assert rect2.name in self.aedtapp.modeler.solid_names

    def test_23_create_rectangle(self):
        udp = self.aedtapp.modeler.Position(5, 3, 8)
        plane = self.aedtapp.PLANE.XY
        o = self.aedtapp.modeler.create_rectangle(plane, udp, [4, 5], name="MyRectangle", matname="Copper")
        assert o.id > 0
        assert o.name.startswith("MyRectangle")
        assert o.object_type == "Sheet"
        assert o.is3d is False

    def test_24_create_cone(self):
        udp = self.aedtapp.modeler.Position(5, 3, 8)
        axis = self.aedtapp.AXIS.Z
        o = self.aedtapp.modeler.create_cone(axis, udp, 20, 10, 5, name="MyCone", matname="Copper")
        assert o.id > 0
        assert o.name.startswith("MyCone")
        assert o.object_type == "Solid"
        assert o.is3d is True

    def test_25_get_object_id(self):
        udp = self.aedtapp.modeler.Position(5, 3, 8)
        plane = self.aedtapp.PLANE.XY
        o = self.aedtapp.modeler.create_rectangle(plane, udp, [4, 5], name="MyRectangle5")
        assert self.aedtapp.modeler.get_obj_id(o.name) == o.id

    def test_26_get_object_names(self):

        p1, p2, points = self.create_polylines()
        c1 = self.create_copper_box()
        r1 = self.create_rectangle()
        solid_list = self.aedtapp.modeler.solid_names
        sheet_list = self.aedtapp.modeler.sheet_names
        line_list = self.aedtapp.modeler.line_names
        all_objects_list = self.aedtapp.modeler.object_names

        assert c1.name in solid_list
        assert r1.name in sheet_list
        assert p1.name in line_list
        assert p2.name in line_list
        assert c1.name in all_objects_list
        assert r1.name in all_objects_list
        assert p1.name in all_objects_list
        assert p2.name in all_objects_list

        print("Solids")
        for solid in solid_list:
            solid_object = self.aedtapp.modeler[solid]

            print(solid)
            print(solid_object.name)

            assert solid_object.is3d
            assert solid_object.object_type == "Solid"

        print("Sheets")
        for sheet in sheet_list:
            sheet_object = self.aedtapp.modeler[sheet]
            print(sheet)
            print(sheet_object.name)
            assert self.aedtapp.modeler[sheet].is3d is False
            assert self.aedtapp.modeler[sheet].object_type == "Sheet"

        print("Lines")
        for line in line_list:
            line_object = self.aedtapp.modeler[line]
            print(line)
            print(line_object.name)
            assert self.aedtapp.modeler[line].is3d is False
            assert self.aedtapp.modeler[line].object_type == "Line"

        assert len(all_objects_list) == len(solid_list) + len(line_list) + len(sheet_list)

    def test_27_get_object_by_material(self):
        self.create_polylines()
        self.create_copper_box()
        self.create_rectangle()
        listsobj = self.aedtapp.modeler.get_objects_by_material("vacuum")
        assert len(listsobj) > 0
        listsobj = self.aedtapp.modeler.get_objects_by_material("FR4")
        assert len(listsobj) == 0

    def test_28_get_object_faces(self):
        self.create_rectangle()
        o = self.aedtapp.modeler["MyRectangle"]
        assert len(o.faces) == 1
        assert len(o.edges) == 4
        assert len(o.vertices) == 4

    def test_29_get_edges_from_position(self):
        o = self.create_rectangle(name="MyRectangle_for_primitives")
        udp = self.aedtapp.modeler.Position(5, 3, 8)
        edge_id = self.aedtapp.modeler.get_edgeid_from_position(udp, o.name)
        assert edge_id > 0
        edge_id = self.aedtapp.modeler.get_edgeid_from_position(udp)
        assert edge_id > 0

    def test_30_get_faces_from_position(self):
        o = self.create_rectangle("New_Rectangle1")
        edge_id = self.aedtapp.modeler.get_faceid_from_position([5, 3, 8], "New_Rectangle1")
        assert edge_id > 0
        udp = self.aedtapp.modeler.Position(100, 100, 100)
        edge_id = self.aedtapp.modeler.get_faceid_from_position(udp)
        assert not edge_id

    def test_31_delete_object(self):
        self.create_rectangle(name="MyRectangle")
        assert "MyRectangle" in self.aedtapp.modeler.object_names
        deleted = self.aedtapp.modeler.delete("MyRectangle")
        assert deleted
        assert "MyRectangle" not in self.aedtapp.modeler.object_names

    def test_32_get_face_vertices(self):
        plane = self.aedtapp.PLANE.XY
        rectid = self.aedtapp.modeler.create_rectangle(plane, [1, 2, 3], [7, 13], name="rect_for_get")
        listfaces = self.aedtapp.modeler.get_object_faces("rect_for_get")
        vertices = self.aedtapp.modeler.get_face_vertices(listfaces[0])
        assert len(vertices) == 4

    def test_33_get_edge_vertices(self):
        listedges = self.aedtapp.modeler.get_object_edges("rect_for_get")
        vertices = self.aedtapp.modeler.get_edge_vertices(listedges[0])
        assert len(vertices) == 2

    def test_34_get_vertex_position(self):
        listedges = self.aedtapp.modeler.get_object_edges("rect_for_get")
        vertices = self.aedtapp.modeler.get_edge_vertices(listedges[0])
        pos1 = self.aedtapp.modeler.get_vertex_position(vertices[0])
        assert len(pos1) == 3
        pos2 = self.aedtapp.modeler.get_vertex_position(vertices[1])
        assert len(pos2) == 3
        edge_length = ((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2 + (pos1[2] - pos2[2]) ** 2) ** 0.5
        assert edge_length == 7

    def test_35_get_face_area(self):
        listfaces = self.aedtapp.modeler.get_object_faces("rect_for_get")
        area = self.aedtapp.modeler.get_face_area(listfaces[0])
        assert area == 7 * 13

    def test_36_get_face_center(self):
        listfaces = self.aedtapp.modeler.get_object_faces("rect_for_get")
        center = self.aedtapp.modeler.get_face_center(listfaces[0])
        assert center == [4.5, 8.5, 3.0]

    def test_37_get_edge_midpoint(self):
        polyline = self.aedtapp.modeler.create_polyline([[0, 0, 0], [10, 5, 3]])
        point = self.aedtapp.modeler.get_edge_midpoint(polyline.id)
        assert point == [5.0, 2.5, 1.5]

    def test_38_get_bodynames_from_position(self):
        center = [20, 20, 0]
        radius = 1
        id = self.aedtapp.modeler.create_sphere(center, radius, "fred")
        spherename = self.aedtapp.modeler.get_bodynames_from_position(center)
        assert "fred" in spherename

        plane = self.aedtapp.PLANE.XY
        rectid = self.aedtapp.modeler.create_rectangle(plane, [-50, -50, -50], [2, 2], name="bob")
        rectname = self.aedtapp.modeler.get_bodynames_from_position([-49.0, -49.0, -50.0])
        assert "bob" in rectname

        udp1 = self.aedtapp.modeler.Position(-23, -23, 13)
        udp2 = self.aedtapp.modeler.Position(-27, -27, 11)
        udp3 = self.aedtapp.modeler.Position(-31, -31, 7)
        udp4 = self.aedtapp.modeler.Position(2, 5, 3)
        arrofpos = [udp1, udp2, udp3, udp4]
        P = self.aedtapp.modeler.create_polyline(arrofpos, cover_surface=False, name="bill")
        polyname = self.aedtapp.modeler.get_bodynames_from_position([-27, -27, 11])
        assert "bill" in polyname

    def test_39_getobjects_with_strings(self):
        list1 = self.aedtapp.modeler.get_objects_w_string("MyCone")
        list2 = self.aedtapp.modeler.get_objects_w_string("my", False)

        assert len(list1) > 0
        assert len(list2) > 0

    def test_40_getmodel_objects(self):
        list1 = self.aedtapp.modeler.model_objects
        list2 = self.aedtapp.modeler.non_model_objects
        list3 = self.aedtapp.modeler.object_names
        for el in list1:
            if el not in list3:
                print("Missing {}".format(el))
        assert len(list1) + len(list2) == len(list3)

    def test_41a_create_rect_sheet_to_region(self):
        assert self.aedtapp.modeler.create_region("20mm", False)
        self.aedtapp.modeler["Region"].delete()
        assert self.aedtapp.modeler.create_region()
        self.create_copper_box(name="MyBox_to_gnd")
        groundplane = self.aedtapp.modeler.create_sheet_to_ground("MyBox_to_gnd")
        assert groundplane.id > 0

    def test_41b_create_rect_sheet_to_groundplane(self):
        rect = self.create_rectangle()
        box = self.create_copper_box()
        plane = self.aedtapp.modeler.create_sheet_to_ground(box.name, rect.name, self.aedtapp.AxisDir.ZNeg)
        assert isinstance(plane, Object3d)

    def test_41b_get_edges_for_circuit_port(self):
        udp = self.aedtapp.modeler.Position(0, 0, 8)
        plane = self.aedtapp.PLANE.XY
        o = self.aedtapp.modeler.create_rectangle(plane, udp, [3, 10], name="MyGND", matname="Copper")
        face_id = o.faces[0].id
        edges1 = self.aedtapp.modeler.get_edges_for_circuit_port(
            face_id, XY_plane=True, YZ_plane=False, XZ_plane=False, allow_perpendicular=True, tol=1e-6
        )
        edges2 = self.aedtapp.modeler.get_edges_for_circuit_port_from_sheet(
            "MyGND", XY_plane=True, YZ_plane=False, XZ_plane=False, allow_perpendicular=True, tol=1e-6
        )

    def test_42_chamfer(self):
        o = self.create_copper_box(name="MyBox")
        assert o.edges[0].chamfer()
        self.aedtapp._odesign.Undo()
        assert o.edges[0].chamfer(chamfer_type=1)
        self.aedtapp._odesign.Undo()
        assert o.edges[0].chamfer(chamfer_type=2)
        self.aedtapp._odesign.Undo()
        assert o.edges[0].chamfer(chamfer_type=3)
        self.aedtapp._odesign.Undo()
        assert not o.edges[0].chamfer(chamfer_type=4)

    def test_43_fillet_and_undo(self):
        o = self.create_copper_box(name="MyBox")
        assert o.edges[0].fillet()
        self.aedtapp._odesign.Undo()
        assert o.edges[0].fillet()

    def test_44_create_polyline_basic_segments(self):
        prim3D = self.aedtapp.modeler
        self.aedtapp["p1"] = "100mm"
        self.aedtapp["p2"] = "71mm"
        test_points = [["0mm", "p1", "0mm"], ["-p1", "0mm", "0mm"], ["-p1/2", "-p1/2", "0mm"], ["0mm", "0mm", "0mm"]]

        p1 = prim3D.create_polyline(position_list=test_points[0:2], name="PL01_line")
        assert len(p1.start_point) == 3
        assert len(p1.end_point) == 3
        assert prim3D.create_polyline(position_list=test_points[0:3], segment_type="Arc", name="PL02_arc")

        assert prim3D.create_polyline(
            position_list=test_points, segment_type=PolylineSegment("Spline", num_points=4), name="PL03_spline_4pt"
        )
        assert prim3D.create_polyline(
            position_list=test_points, segment_type=PolylineSegment("Spline", num_points=3), name="PL03_spline_3pt"
        )
        assert prim3D.create_polyline(position_list=test_points[0:3], segment_type="Spline", name="PL03_spline_str_3pt")
        assert prim3D.create_polyline(position_list=test_points[0:2], segment_type="Spline", name="PL03_spline_str_2pt")
        assert prim3D.create_polyline(
            position_list=[[100, 100, 0]],
            segment_type=PolylineSegment("AngularArc", arc_center=[0, 0, 0], arc_angle="30deg"),
            name="PL04_center_point_arc",
        )
        assert prim3D.create_polyline(
            position_list=[[100, 100, 0]],
            segment_type=PolylineSegment("AngularArc", arc_angle="30deg"),
            name="PL04_center_point_arc",
        )

    def test_45_create_circle_from_2_arc_segments(self):
        prim3D = self.aedtapp.modeler
        assert prim3D.create_polyline(
            position_list=[[34.1004, 14.1248, 0], [27.646, 16.7984, 0], [24.9725, 10.3439, 0], [31.4269, 7.6704, 0]],
            segment_type=["Arc", "Arc"],
            cover_surface=True,
            close_surface=True,
            name="Rotor_Subtract_25_0",
            matname="vacuum",
        )

    def test_46_compound_polylines_segments(self):
        prim3D = self.aedtapp.modeler
        self.aedtapp["p1"] = "100mm"
        self.aedtapp["p2"] = "71mm"
        test_points = [["0mm", "p1", "0mm"], ["-p1", "0mm", "0mm"], ["-p1/2", "-p1/2", "0mm"], ["0mm", "0mm", "0mm"]]

        assert prim3D.create_polyline(position_list=test_points, name="PL06_segmented_compound_line")
        assert prim3D.create_polyline(
            position_list=test_points, segment_type=["Line", "Arc"], name="PL05_compound_line_arc"
        )
        assert prim3D.create_polyline(
            position_list=test_points, close_surface=True, name="PL07_segmented_compound_line_closed"
        )
        assert prim3D.create_polyline(
            position_list=test_points, cover_surface=True, name="SPL01_segmented_compound_line"
        )

    def test_47_insert_polylines_segments_test1(self):
        self.aedtapp["p1"] = "100mm"
        self.aedtapp["p2"] = "71mm"
        test_points = [["0mm", "p1", "0mm"], ["-p1", "0mm", "0mm"], ["-p1/2", "-p1/2", "0mm"], ["0mm", "0mm", "0mm"]]
        P = self.aedtapp.modeler.create_polyline(
            position_list=test_points, close_surface=False, name="PL08_segmented_compound_insert_segment"
        )
        assert P
        start_point = P.start_point
        insert_point = ["90mm", "20mm", "0mm"]
        insert_point2 = ["95mm", "20mm", "0mm"]
        assert P.insert_segment(position_list=[start_point, insert_point])
        assert P.insert_segment(position_list=[insert_point, insert_point2])

    def test_48_insert_polylines_segments_test2(self):
        prim3D = self.aedtapp.modeler
        self.aedtapp["p1"] = "100mm"
        self.aedtapp["p2"] = "71mm"
        test_points = [["0mm", "p1", "0mm"], ["-p1", "0mm", "0mm"], ["-p1/2", "-p1/2", "0mm"], ["0mm", "0mm", "0mm"]]

        P = prim3D.create_polyline(
            position_list=test_points, close_surface=False, name="PL08_segmented_compound_insert_arc"
        )
        start_point = P.vertex_positions[1]
        insert_point1 = ["90mm", "20mm", "0mm"]
        insert_point2 = [40, 40, 0]

        P.insert_segment(position_list=[start_point, insert_point1, insert_point2], segment="Arc")

    def test_49_modify_crossection(self):

        P = self.aedtapp.modeler.create_polyline(
            position_list=[[34.1004, 14.1248, 0], [27.646, 16.7984, 0], [24.9725, 10.3439, 0]],
            name="Rotor_Subtract_25_0",
            matname="copper",
        )
        P1 = P.clone()
        P2 = P.clone()
        P3 = P.clone()
        P4 = P.clone()

        P1.set_crosssection_properties(type="Line", width="1mm")
        a = P1.object_type

        P2.set_crosssection_properties(type="Circle", width="1mm", num_seg=5)
        P3.set_crosssection_properties(type="Rectangle", width="1mm", height="1mm")
        P4.set_crosssection_properties(type="Isosceles Trapezoid", width="1mm", height="1mm", topwidth="4mm")

        assert P.object_type == "Line"
        assert P1.object_type == "Sheet"
        assert P2.object_type == "Solid"
        assert P3.object_type == "Solid"
        assert P4.object_type == "Solid"

    def test_50_remove_vertex_from_polyline(self):

        p1, p2, test_points = self.create_polylines("Poly_remove_")

        P = self.aedtapp.modeler["Poly_remove_segmented"]
        P.remove_vertex(test_points[2])
        time.sleep(0.1)
        P1 = self.aedtapp.modeler.create_polyline([[0, 1, 2], [0, 2, 3], [2, 1, 4]])
        P1.remove_vertex([0, 1, 2])
        time.sleep(0.1)

        P2 = self.aedtapp.modeler.create_polyline([[0, 1, 2], [0, 2, 3], [2, 1, 4]])
        P2.remove_vertex(["0mm", "1mm", "2mm"])
        time.sleep(0.1)

        P3 = self.aedtapp.modeler.create_polyline([[0, 1, 2], [0, 2, 3], [2, 1, 4]])
        P3.remove_vertex(["0mm", "1mm", "2mm"], abstol=1e-6)

    def test_51_remove_edges_from_polyline(self):

        modeler = self.aedtapp.modeler
        P = modeler.create_polyline([[0, 1, 2], [0, 2, 3], [2, 1, 4]])
        P.remove_edges(edge_id=0)
        assert P.name in self.aedtapp.modeler.line_names
        P = modeler.create_polyline([[0, 1, 2], [0, 2, 3], [2, 1, 4], [3, 1, 6]])
        P.remove_edges(edge_id=[0, 1])
        assert P.name in self.aedtapp.modeler.line_names
        P = modeler.create_polyline([[0, 1, 2], [0, 2, 3], [2, 1, 4], [3, 1, 6]])
        P.remove_edges(edge_id=[1, 2])
        assert P.name in self.aedtapp.modeler.line_names
        P = modeler.create_polyline([[0, 1, 2], [0, 2, 3], [2, 1, 4], [3, 1, 6]])
        P.remove_edges(edge_id=2)
        assert P.name in self.aedtapp.modeler.line_names

    def test_52_remove_edges_from_polyline_invalid(self):
        P = self.aedtapp.modeler.create_polyline([[0, 1, 2], [0, 2, 3], [2, 1, 4]])
        P.remove_edges(edge_id=[0, 1])
        assert not P.name in self.aedtapp.modeler.line_names

    def test_53_duplicate_polyline_and_manipulate(self):
        P1 = self.aedtapp.modeler.create_polyline([[0, 1, 2], [0, 2, 3], [2, 1, 4]])
        P2 = P1.clone()
        assert P2.id != P1.id

    def test_54_create_bond_wires(self):
        b0 = self.aedtapp.modeler.create_bondwire(
            [0, 0, 0], [10, 10, 2], h1=0.15, h2=0, diameter=0.034, facets=8, matname="copper", name="jedec51"
        )
        assert b0
        b1 = self.aedtapp.modeler.create_bondwire(
            [0, 0, 0], [10, 10, 2], h1=0.15, h2=0, diameter=0.034, bond_type=1, matname="copper", name="jedec41"
        )
        assert b1
        b2 = self.aedtapp.modeler.create_bondwire(
            [0, 0, 0], [10, 10, 2], h1=0.15, h2=0, diameter=0.034, bond_type=2, matname="copper", name="low"
        )
        assert b2
        b3 = self.aedtapp.modeler.create_bondwire(
            [0, 0, 0], [10, 10, 2], h1=0.15, h2=0, diameter=0.034, bond_type=3, matname="copper", name="jedec41"
        )
        assert not b3
        b4 = self.aedtapp.modeler.create_bondwire(
            (2, 2, 0), (0, 0, 0), h1=0.15, h2=0, diameter=0.034, bond_type=1, matname="copper", name="jedec41"
        )
        assert b4

    def test_56_create_group(self):
        assert self.aedtapp.modeler.create_group(["jedec51", "jedec41"], "mygroup")
        assert self.aedtapp.modeler.ungroup("mygroup")

    def test_57_flatten_assembly(self):
        assert self.aedtapp.modeler.flatten_assembly()

    def test_58_solving_volume(self):
        vol = self.aedtapp.modeler.get_solving_volume()
        assert float(vol) > 0

    def test_59_lines(self):
        assert self.aedtapp.modeler.vertex_data_of_lines()

    @pytest.mark.skipif("UNITTEST_CURRENT_TEST" in os.environ, reason="Issue in IronPython")
    def test_60_get_edges_on_bounding_box(self):
        self.aedtapp.close_project(name=self.aedtapp.project_name, save_project=False)
        self.aedtapp.load_project(self.test_99_project)
        edges = self.aedtapp.modeler.get_edges_on_bounding_box(["Port1", "Port2"], return_colinear=True, tol=1e-6)
        assert len(edges) == 2
        edges = self.aedtapp.modeler.get_edges_on_bounding_box(["Port1", "Port2"], return_colinear=False, tol=1e-6)
        assert len(edges) == 4

    def test_61_get_closest_edge_to_position(self):
        my_box = self.create_copper_box("test_closest_edge")
        assert isinstance(self.aedtapp.modeler.get_closest_edgeid_to_position([0.2, 0, 0]), int)
        pass

    @pytest.mark.skipif(config["NonGraphical"] or is_ironpython, reason="Not running in non-graphical mode")
    def test_62_import_space_claim(self):
        self.aedtapp.insert_design("SCImport")
        assert self.aedtapp.modeler.import_spaceclaim_document(os.path.join(self.local_scratch.path, scdoc))
        assert len(self.aedtapp.modeler.objects) == 1

    def test_63_import_step(self):
        self.aedtapp.insert_design("StepImport")
        assert self.aedtapp.modeler.import_3d_cad(self.step_file)
        assert len(self.aedtapp.modeler.object_names) == 1

    def test_64_create_3dcomponent(self):
        for i in list(self.aedtapp.modeler.objects.keys()):
            self.aedtapp.modeler.objects[i].material_name = "copper"
        assert self.aedtapp.modeler.create_3dcomponent(self.component3d_file)
        assert os.path.exists(self.component3d_file)
        new_obj = self.aedtapp.modeler.duplicate_along_line("Solid", [100, 0, 0])
        rad = self.aedtapp.assign_radiation_boundary_to_objects("Solid")
        obj1 = self.aedtapp.modeler[new_obj[1][0]]
        exc = self.aedtapp.create_wave_port_from_sheet(obj1.faces[0])
        assert self.aedtapp.modeler.create_3dcomponent(
            self.component3d_file,
            object_list=["Solid", new_obj[1][0]],
            boundaries_list=[rad.name],
            excitation_list=[exc.name],
            included_cs="Global",
        )
        assert os.path.exists(self.component3d_file)

    def test_64_create_3d_component_encrypted(self):
        assert self.aedtapp.modeler.create_3dcomponent(
            self.component3d_file,
            included_cs="Global",
            is_encrypted=True,
            password="password_test",
        )
        assert not self.aedtapp.modeler.create_3dcomponent(
            self.component3d_file,
            included_cs="Global",
            is_encrypted=True,
            password="password_test",
            password_type="Invalid",
        )
        assert not self.aedtapp.modeler.create_3dcomponent(
            self.component3d_file,
            included_cs="Global",
            is_encrypted=True,
            password="password_test",
            component_outline="Invalid",
        )

    def test_65_create_equationbased_curve(self):
        self.aedtapp.insert_design("Equations")
        eq_line = self.aedtapp.modeler.create_equationbased_curve(x_t="_t", y_t="_t*2", num_points=0)
        assert len(eq_line.edges) == 1
        eq_segmented = self.aedtapp.modeler.create_equationbased_curve(x_t="_t", y_t="_t*2", num_points=5)
        assert len(eq_segmented.edges) == 4
        eq_xsection = self.aedtapp.modeler.create_equationbased_curve(x_t="_t", y_t="_t*2", xsection_type="Circle")
        assert eq_xsection.name in self.aedtapp.modeler.solid_names

    def test_66_insert_3dcomponent(self):
        self.aedtapp.solution_type = "Modal"
        self.aedtapp["l_dipole"] = "13.5cm"
        compfile = self.aedtapp.components3d["Dipole_Antenna_DM"]
        geometryparams = self.aedtapp.get_components3d_vars("Dipole_Antenna_DM")
        geometryparams["dipole_length"] = "l_dipole"
        obj_3dcomp = self.aedtapp.modeler.insert_3d_component(compfile, geometryparams)
        assert isinstance(obj_3dcomp, UserDefinedComponent)

    @pytest.mark.skipif(config["use_grpc"] and config["desktopVersion"] < "2023.1", reason="Failing in grpc 2022.2")
    def test_66a_insert_encrypted_3dcomp(self):
        assert not self.aedtapp.modeler.insert_3d_component(self.encrypted_cylinder)
        # assert not self.aedtapp.modeler.insert_3d_component(self.encrypted_cylinder, password="dfgdg")
        assert self.aedtapp.modeler.insert_3d_component(self.encrypted_cylinder, password="test")

    def test_66b_group_components(self):
        self.aedtapp["l_dipole"] = "13.5cm"

        compfile = self.aedtapp.components3d["Dipole_Antenna_DM"]
        geometryparams = self.aedtapp.get_components3d_vars("Dipole_Antenna_DM")
        geometryparams["dipole_length"] = "l_dipole"
        obj_3dcomp1 = self.aedtapp.modeler.insert_3d_component(compfile, geometryparams)
        obj_3dcomp2 = self.aedtapp.modeler.insert_3d_component(compfile, geometryparams)
        assert (
            self.aedtapp.modeler.create_group(components=[obj_3dcomp1.name, obj_3dcomp2.name], group_name="test_group")
            == "test_group"
        )

    def test_67_assign_material(self):
        box1 = self.aedtapp.modeler.create_box([60, 60, 60], [4, 5, 5])
        box2 = self.aedtapp.modeler.create_box([50, 50, 50], [2, 3, 4])
        cyl1 = self.aedtapp.modeler.create_cylinder(cs_axis="X", position=[50, 0, 0], radius=1, height=20)
        cyl2 = self.aedtapp.modeler.create_cylinder(cs_axis="Z", position=[0, 0, 50], radius=1, height=10)

        objects_list = [box1, box2, cyl1, cyl2]
        self.aedtapp.assign_material(objects_list, "copper")
        assert self.aedtapp.modeler[box1].material_name == "copper"
        assert self.aedtapp.modeler[box2].material_name == "copper"
        assert self.aedtapp.modeler[cyl1].material_name == "copper"
        assert self.aedtapp.modeler[cyl2].material_name == "copper"

        obj_names_list = [box1.name, box2.name, cyl1.name, cyl2.name]
        self.aedtapp.assign_material(obj_names_list, "aluminum")
        assert self.aedtapp.modeler[box1].material_name == "aluminum"
        assert self.aedtapp.modeler[box2].material_name == "aluminum"
        assert self.aedtapp.modeler[cyl1].material_name == "aluminum"
        assert self.aedtapp.modeler[cyl2].material_name == "aluminum"

    def test_68_cover_lines(self):
        P1 = self.aedtapp.modeler.create_polyline([[0, 1, 2], [0, 2, 3], [2, 1, 4]], close_surface=True)
        assert self.aedtapp.modeler.cover_lines(P1)

    def test_69_create_torus(self):
        torus = self.create_copper_torus()
        assert torus.id > 0
        assert torus.name.startswith("MyTorus")
        assert torus.object_type == "Solid"
        assert torus.is3d is True

    @pytest.mark.skipif(is_ironpython, reason="pytest is not supported with IronPython.")
    def test_70_create_torus_exceptions(self):

        with pytest.raises(ValueError) as excinfo:
            self.aedtapp.modeler.create_torus(
                [30, 30], major_radius=-0.3, minor_radius=0.5, axis="Z", name="torus", material_name="Copper"
            )
            assert "Center argument must be a valid 3 element sequence." in str(excinfo.value)

        # with pytest.raises(ValueError) as excinfo:
        #     self.aedtapp.modeler.create_torus(
        #         [30, 30, 0], major_radius=-0.3, minor_radius=0.5, axis="Z", name="torus", material_name="Copper"
        #     )
        #     assert "Both major and minor radius must be greater than 0" in str(excinfo.value)

        # with pytest.raises(ValueError) as excinfo:
        #     self.aedtapp.modeler.create_torus(
        #         [30, 30, 0], major_radius=1, minor_radius=0, axis="Z", name="torus", material_name="Copper"
        #     )
        #     assert "Both major and minor radius must be greater than 0" in str(excinfo.value)

        # with pytest.raises(ValueError) as excinfo:
        #     self.aedtapp.modeler.create_torus(
        #         [30, 30, 0], major_radius=1, minor_radius=1.2, axis="Z", name="torus", material_name="Copper"
        #     )
        #     assert "Major radius must be greater than minor radius." in str(excinfo.value)

    def test_71_create_point(self):
        name = "mypoint"
        if self.aedtapp.modeler[name]:
            self.aedtapp.modeler.delete(name)
        point = self.aedtapp.modeler.create_point([30, 30, 0], name)
        point.set_color("(143 175 158)")
        point2 = self.aedtapp.modeler.create_point([50, 30, 0], "mypoint2", "(100 100 100)")
        point.logger.info("Creation and testing of a point.")

        assert point.name == "mypoint"
        assert point.coordinate_system == "Global"
        assert point2.name == "mypoint2"
        assert point2.coordinate_system == "Global"

        assert self.aedtapp.modeler.points[point.name] == point
        assert self.aedtapp.modeler.points[point2.name] == point2

        # Delete the first point
        assert len(self.aedtapp.modeler.points) == 2
        self.aedtapp.modeler.points[point.name].delete()
        assert name not in self.aedtapp.modeler.points
        self.aedtapp.modeler.points
        assert len(self.aedtapp.modeler.point_objects) == 1
        assert len(self.aedtapp.modeler.point_names) == 1
        assert self.aedtapp.modeler.point_objects[0].name == "mypoint2"

    def test_71_create_plane(self):
        self.aedtapp.set_active_design("3D_Primitives")
        name = "my_plane"
        if self.aedtapp.modeler[name]:
            self.aedtapp.modeler.delete(name)
        plane = self.aedtapp.modeler.create_plane(name, "-0.7mm", "0.3mm", "0mm", "0.7mm", "-0.3mm", "0mm")
        assert name in self.aedtapp.modeler.planes
        plane.set_color("(143 75 158)")
        assert plane.name == name
        plane.name = "my_plane1"
        assert plane.name == "my_plane1"

        plane2 = self.aedtapp.modeler.create_plane(
            plane_base_x="-0.7mm",
            plane_base_z="0.3mm",
            plane_normal_x="-0.7mm",
            plane_normal_z="0.3mm",
            name="my_plane2",
            color="(100 100 100)",
        )
        plane.logger.info("Creation and testing of a plane.")

        assert plane.name == "my_plane1"
        assert plane.coordinate_system == "Global"
        assert plane2.name == "my_plane2"
        assert plane2.coordinate_system == "Global"

        assert self.aedtapp.modeler.planes["my_plane1"].name == plane.name
        assert self.aedtapp.modeler.planes["my_plane2"].name == plane2.name

        # Delete the first plane
        if config["desktopVersion"] < "2023.1" and not is_ironpython:
            assert len(self.aedtapp.modeler.planes) == 2
        else:
            assert len(self.aedtapp.modeler.planes) == 5
        self.aedtapp.modeler.planes["my_plane1"].delete()
        assert name not in self.aedtapp.modeler.planes

    def test_71_create_choke(self):
        choke_file1 = os.path.join(
            local_path, "example_models", "choke_json_file", "choke_1winding_1Layer_Corrected.json"
        )
        choke_file2 = os.path.join(
            local_path, "example_models", "choke_json_file", "choke_2winding_1Layer_Common_Corrected.json"
        )
        choke_file3 = os.path.join(
            local_path, "example_models", "choke_json_file", "choke_2winding_2Layer_Linked_Differential_Corrected.json"
        )
        choke_file4 = os.path.join(
            local_path, "example_models", "choke_json_file", "choke_3winding_3Layer_Separate_Corrected.json"
        )
        choke_file5 = os.path.join(
            local_path, "example_models", "choke_json_file", "choke_4winding_3Layer_Linked_Corrected.json"
        )
        choke_file6 = os.path.join(
            local_path, "example_models", "choke_json_file", "choke_2winding_2Layer_Common_Corrected.json"
        )
        resolve1 = self.aedtapp.modeler.create_choke(choke_file1)
        resolve2 = self.aedtapp.modeler.create_choke(choke_file2)
        resolve3 = self.aedtapp.modeler.create_choke(choke_file3)
        resolve4 = self.aedtapp.modeler.create_choke(choke_file4)
        resolve5 = self.aedtapp.modeler.create_choke(choke_file5)
        resolve6 = self.aedtapp.modeler.create_choke(choke_file6)
        assert isinstance(resolve1, list)
        assert resolve1[0]
        assert isinstance(resolve1[1], Object3d)
        for i in range(2, len(resolve1)):
            assert isinstance(resolve1[i][0], Object3d)
            assert isinstance(resolve1[i][1], list)
        assert isinstance(resolve2, list)
        assert resolve2[0]
        assert isinstance(resolve2[1], Object3d)
        for i in range(2, len(resolve2)):
            assert isinstance(resolve2[i][0], Object3d)
            assert isinstance(resolve2[i][1], list)
        assert isinstance(resolve3, list)
        assert resolve3[0]
        assert isinstance(resolve3[1], Object3d)
        for i in range(2, len(resolve3)):
            assert isinstance(resolve3[i][0], Object3d)
            assert isinstance(resolve3[i][1], list)
        assert isinstance(resolve4, list)
        assert resolve4[0]
        assert isinstance(resolve4[1], Object3d)
        for i in range(2, len(resolve4)):
            assert isinstance(resolve4[i][0], Object3d)
            assert isinstance(resolve4[i][1], list)
        assert isinstance(resolve5, list)
        assert resolve5[0]
        assert isinstance(resolve5[1], Object3d)
        for i in range(2, len(resolve5)):
            assert isinstance(resolve5[i][0], Object3d)
            assert isinstance(resolve5[i][1], list)
        assert isinstance(resolve6, list)
        assert resolve6[0]
        assert isinstance(resolve6[1], Object3d)
        for i in range(2, len(resolve6)):
            assert isinstance(resolve6[i][0], Object3d)
            assert isinstance(resolve6[i][1], list)

    def test_72_check_choke_values(self):
        choke_file1 = os.path.join(local_path, "example_models", "choke_json_file", "choke_1winding_1Layer.json")
        choke_file2 = os.path.join(local_path, "example_models", "choke_json_file", "choke_2winding_1Layer_Common.json")
        choke_file3 = os.path.join(
            local_path, "example_models", "choke_json_file", "choke_2winding_2Layer_Linked_Differential.json"
        )
        choke_file4 = os.path.join(
            local_path, "example_models", "choke_json_file", "choke_3winding_3Layer_Separate.json"
        )
        choke_file5 = os.path.join(local_path, "example_models", "choke_json_file", "choke_4winding_3Layer_Linked.json")
        choke_file6 = os.path.join(local_path, "example_models", "choke_json_file", "choke_1winding_3Layer_Linked.json")
        choke_file7 = os.path.join(local_path, "example_models", "choke_json_file", "choke_2winding_2Layer_Common.json")
        scratch_choke_file1 = self.local_scratch.copyfile(choke_file1)
        scratch_choke_file2 = self.local_scratch.copyfile(choke_file2)
        scratch_choke_file3 = self.local_scratch.copyfile(choke_file3)
        scratch_choke_file4 = self.local_scratch.copyfile(choke_file4)
        scratch_choke_file5 = self.local_scratch.copyfile(choke_file5)
        scratch_choke_file6 = self.local_scratch.copyfile(choke_file6)
        scratch_choke_file7 = self.local_scratch.copyfile(choke_file7)
        resolve1 = self.aedtapp.modeler.check_choke_values(scratch_choke_file1, create_another_file=True)
        resolve2 = self.aedtapp.modeler.check_choke_values(scratch_choke_file2, create_another_file=True)
        resolve3 = self.aedtapp.modeler.check_choke_values(scratch_choke_file3, create_another_file=True)
        resolve4 = self.aedtapp.modeler.check_choke_values(scratch_choke_file4, create_another_file=True)
        resolve5 = self.aedtapp.modeler.check_choke_values(scratch_choke_file5, create_another_file=True)
        resolve6 = self.aedtapp.modeler.check_choke_values(scratch_choke_file6, create_another_file=True)
        resolve7 = self.aedtapp.modeler.check_choke_values(scratch_choke_file7, create_another_file=True)
        assert isinstance(resolve1, list)
        assert resolve1[0]
        assert isinstance(resolve1[1], dict)
        assert isinstance(resolve2, list)
        assert resolve2[0]
        assert isinstance(resolve2[1], dict)
        assert isinstance(resolve3, list)
        assert resolve3[0]
        assert isinstance(resolve3[1], dict)
        assert isinstance(resolve4, list)
        assert resolve4[0]
        assert isinstance(resolve4[1], dict)
        assert isinstance(resolve5, list)
        assert resolve5[0]
        assert isinstance(resolve5[1], dict)
        assert isinstance(resolve6, list)
        assert resolve6[0]
        assert isinstance(resolve6[1], dict)
        assert isinstance(resolve7, list)
        assert resolve7[0]
        assert isinstance(resolve7[1], dict)

    def test_73_make_winding(self):
        chamfer = self.aedtapp.modeler._make_winding_follow_chamfer(0.8, 1.1, 2, 1)
        winding_list = self.aedtapp.modeler._make_winding("Winding", "copper", 29.9, 52.1, 22.2, 5, 15, chamfer, True)
        assert isinstance(winding_list, list)
        assert isinstance(winding_list[0], Object3d)
        assert isinstance(winding_list[1], list)

    def test_74_make_double_linked_winding(self):
        chamfer = self.aedtapp.modeler._make_winding_follow_chamfer(0.8, 1.1, 2, 1)
        winding_list = self.aedtapp.modeler._make_double_linked_winding(
            "Double_Winding",
            "copper",
            27.7,
            54.3,
            26.6,
            2,
            3,
            3,
            15,
            16,
            0.8,
            chamfer,
            1.1,
        )
        assert isinstance(winding_list, list)
        assert isinstance(winding_list[0], Object3d)
        assert isinstance(winding_list[1], list)

    def test_75_make_triple_linked_winding(self):
        chamfer = self.aedtapp.modeler._make_winding_follow_chamfer(0.8, 1.1, 2, 1)
        winding_list = self.aedtapp.modeler._make_triple_linked_winding(
            "Triple_Winding",
            "copper",
            25.5,
            56.5,
            31.0,
            2,
            2.5,
            2.5,
            2.5,
            10,
            12,
            14,
            0.8,
            chamfer,
            1.1,
        )
        assert isinstance(winding_list, list)
        assert isinstance(winding_list[0], Object3d)
        assert isinstance(winding_list[1], list)

    def test_76_check_value_type(self):
        resolve1, boolean1 = self.aedtapp.modeler._check_value_type(2, float, True, "SUCCESS", "SUCCESS")
        resolve2, boolean2 = self.aedtapp.modeler._check_value_type(1, int, True, "SUCCESS", "SUCCESS")
        resolve3, boolean3 = self.aedtapp.modeler._check_value_type(1.1, float, False, "SUCCESS", "SUCCESS")
        assert isinstance(resolve1, float)
        assert boolean1
        assert isinstance(resolve2, int)
        assert boolean2
        assert isinstance(resolve3, float)
        assert not boolean3

    def test_77_create_helix(self):
        udp1 = [0, 0, 0]
        udp2 = [5, 0, 0]
        udp3 = [10, 5, 0]
        udp4 = [15, 3, 0]
        polyline = self.aedtapp.modeler.create_polyline(
            [udp1, udp2, udp3, udp4], cover_surface=False, name="helix_polyline"
        )

        helix_right_turn = self.aedtapp.modeler.create_helix(
            polyline_name="helix_polyline",
            position=[0, 0, 0],
            x_start_dir=0,
            y_start_dir=1.0,
            z_start_dir=1.0,
            num_thread=1,
            right_hand=True,
            radius_increment=0.0,
            thread=1.0,
        )

        assert helix_right_turn.object_units == "mm"

        # Test left turn without providing argument value for default parameters.
        udp1 = [-45, 0, 0]
        udp2 = [-50, 0, 0]
        udp3 = [-105, 5, 0]
        udp4 = [-110, 3, 0]
        polyline_left = self.aedtapp.modeler.create_polyline(
            [udp1, udp2, udp3, udp4], cover_surface=False, name="helix_polyline_left"
        )

        assert self.aedtapp.modeler.create_helix(
            polyline_name="helix_polyline_left",
            position=[0, 0, 0],
            x_start_dir=1.0,
            y_start_dir=1.0,
            z_start_dir=1.0,
            right_hand=False,
        )

        # Test that an exception is raised if the name of the polyline is not provided.
        # We can't use with.pytest.raises pattern below because IronPython does not support pytest.
        try:
            self.aedtapp.modeler.create_helix(
                polyline_name="",
                position=[0, 0, 0],
                x_start_dir=1.0,
                y_start_dir=1.0,
                z_start_dir=1.0,
            )
        except ValueError as exc_info:
            assert "The name of the polyline cannot be an empty string." in str(exc_info.args[0])
        else:
            assert False

    def test_78_get_touching_objects(self):
        box1 = self.aedtapp.modeler.create_box([-20, -20, -20], [1, 1, 1])
        box2 = self.aedtapp.modeler.create_box([-20, -20, -19], [0.2, 0.2, 0.2])
        assert box2.name in box1.touching_objects
        assert box1.name in box2.touching_objects
        assert box2.name in box1.faces[0].touching_objects
        if config["desktopVersion"] > "2022.2":
            assert box2.name not in box1.faces[3].touching_objects
        else:
            assert box2.name not in box1.faces[1].touching_objects
        assert box2.get_touching_faces(box1)

    @pytest.mark.skipif(config["desktopVersion"] < "2023.1", reason="Method failing 2022.2")
    def test_79_3dcomponent_operations(self):
        self.aedtapp.solution_type = "Modal"
        self.aedtapp["l_dipole"] = "13.5cm"
        compfile = self.aedtapp.components3d["Dipole_Antenna_DM"]
        geometryparams = self.aedtapp.get_components3d_vars("Dipole_Antenna_DM")
        geometryparams["dipole_length"] = "l_dipole"
        obj_3dcomp = self.aedtapp.modeler.insert_3d_component(compfile, geometryparams)
        assert isinstance(obj_3dcomp, UserDefinedComponent)
        assert obj_3dcomp.group_name == "Model"
        obj_3dcomp.group_name = "test_group1"
        assert obj_3dcomp.group_name == "test_group1"
        obj_3dcomp.group_name = "test_group"
        assert obj_3dcomp.group_name == "test_group"
        assert obj_3dcomp.is3dcomponent
        assert not obj_3dcomp.mesh_assembly
        obj_3dcomp.mesh_assembly = True
        assert obj_3dcomp.mesh_assembly
        obj_3dcomp.name = "Dipole_pyaedt"
        assert "Dipole_pyaedt" in self.aedtapp.modeler.user_defined_component_names
        assert obj_3dcomp.name == "Dipole_pyaedt"
        if config["desktopVersion"] < "2023.1":
            assert obj_3dcomp.parameters["dipole_length"] == "l_dipole"
            self.aedtapp["l_dipole2"] = "15.5cm"
            obj_3dcomp.parameters["dipole_length"] = "l_dipole2"
            assert obj_3dcomp.parameters["dipole_length"] == "l_dipole2"
        cs = self.aedtapp.modeler.create_coordinate_system()
        obj_3dcomp.target_coordinate_system = cs.name
        assert obj_3dcomp.target_coordinate_system == cs.name
        obj_3dcomp.delete()
        self.aedtapp.save_project()
        self.aedtapp._project_dictionary = None
        assert "Dipole_pyaedt" not in self.aedtapp.modeler.user_defined_component_names
        udp = self.aedtapp.modeler.Position(0, 0, 0)
        udp2 = self.aedtapp.modeler.Position(30, 40, 40)
        self.aedtapp.modeler.set_working_coordinate_system("Global")
        obj_3dcomp = self.aedtapp.modeler["Dipole_Antenna2"]
        assert obj_3dcomp.mirror(udp, udp2)
        assert obj_3dcomp.rotate(cs_axis="Y", angle=180)
        assert obj_3dcomp.move(udp2)

        new_comps = obj_3dcomp.duplicate_around_axis(cs_axis="Z", angle=8, nclones=3)
        assert new_comps[0] in self.aedtapp.modeler.user_defined_component_names

        udp = self.aedtapp.modeler.Position(5, 5, 5)
        num_clones = 5
        attached_clones = obj_3dcomp.duplicate_along_line(udp, num_clones)
        assert attached_clones[0] in self.aedtapp.modeler.user_defined_component_names

        attached_clones = obj_3dcomp.duplicate_along_line(
            self.aedtapp.modeler.Position(-5, -5, -5), 2, attach_object=True
        )
        assert attached_clones[0] in self.aedtapp.modeler.user_defined_component_names

    @pytest.mark.skipif(config["desktopVersion"] < "2023.1", reason="Method failing 2022.2")
    def test_80_udm_operations(self):
        my_udmPairs = []
        mypair = ["OuterRadius", "20.2mm"]
        my_udmPairs.append(mypair)
        mypair = ["Tau", "0.65"]
        my_udmPairs.append(mypair)
        mypair = ["Sigma", "0.81"]
        my_udmPairs.append(mypair)
        mypair = ["Delta_Angle", "45deg"]
        my_udmPairs.append(mypair)
        mypair = ["Beta_Angle", "45deg"]
        my_udmPairs.append(mypair)
        mypair = ["Port_Gap_Width", "8.1mm"]
        my_udmPairs.append(mypair)
        obj_udm = self.aedtapp.modeler.create_udm(
            udmfullname="HFSS/Antenna Toolkit/Log Periodic/Log Tooth.py",
            udm_params_list=my_udmPairs,
            udm_library="syslib",
            name="test_udm",
        )
        assert isinstance(obj_udm, UserDefinedComponent)
        assert len(self.aedtapp.modeler.user_defined_component_names) == len(
            self.aedtapp.modeler.user_defined_components
        )
        assert obj_udm.group_name == "Model"
        obj_udm.group_name = "test_group1"
        assert obj_udm.group_name == "test_group1"
        obj_udm.group_name = "test_group"
        assert obj_udm.group_name == "test_group"
        assert not obj_udm.is3dcomponent
        assert not obj_udm.mesh_assembly
        obj_udm.mesh_assembly = True
        assert not obj_udm.mesh_assembly
        obj_udm.name = "antenna_pyaedt"
        assert "antenna_pyaedt" in self.aedtapp.modeler.user_defined_component_names
        obj_udm.name = "MyTorus"
        assert obj_udm.name == "antenna_pyaedt"
        assert obj_udm.parameters["OuterRadius"] == "20.2mm"
        obj_udm.parameters["OuterRadius"] = "21mm"
        assert obj_udm.parameters["OuterRadius"] == "21mm"
        cs = self.aedtapp.modeler.create_coordinate_system()
        obj_udm.target_coordinate_system = cs.name
        assert obj_udm.target_coordinate_system == cs.name
        obj_udm.delete()
        self.aedtapp.save_project()
        self.aedtapp._project_dictionary = None
        assert "antenna_pyaedt" not in self.aedtapp.modeler.user_defined_component_names
        udp = self.aedtapp.modeler.Position(0, 0, 0)
        udp2 = self.aedtapp.modeler.Position(30, 40, 40)
        obj_udm = self.aedtapp.modeler.create_udm(
            udmfullname="HFSS/Antenna Toolkit/Log Periodic/Log Tooth.py",
            udm_params_list=my_udmPairs,
            udm_library="syslib",
            name="test_udm",
        )
        assert obj_udm.mirror(udp, udp2)
        assert obj_udm.rotate(cs_axis="Y", angle=180)
        assert obj_udm.move(udp2)
        assert not obj_udm.duplicate_around_axis(cs_axis="Z", angle=8, nclones=3)
        udp = self.aedtapp.modeler.Position(5, 5, 5)
        num_clones = 5
        assert not obj_udm.duplicate_along_line(udp, num_clones)

    @pytest.mark.skipif(config["desktopVersion"] < "2023.1", reason="Not working in 2022.2 GRPC")
    def test_81_duplicate_and_mirror_3dcomponent(self):
        assert self.aedtapp.modeler.duplicate_and_mirror(
            self.aedtapp.modeler.user_defined_component_names[0], [0, 0, 0], [1, 0, 0], is_3d_comp=True
        )

    def test_82_flatten_3d_components(self):
        assert self.flatten.flatten_3d_components()
