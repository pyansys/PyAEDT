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

import secrets
from sys import float_info

from ansys.aedt.core.generic.numbers import decompose_variable_value
from ansys.aedt.core.modeler.cad.elements_3d import FacePrimitive
from ansys.aedt.core.modeler.cad.modeler import FaceCoordinateSystem
from ansys.aedt.core.modeler.cad.object_3d import Object3d
from ansys.aedt.core.modeler.cad.primitives import PolylineSegment
import pytest

from tests.system.general.conftest import config

test_subfolder = "T02"
if config["desktopVersion"] > "2022.2":
    test_project_name = "Coax_HFSS_t02_231"
else:
    test_project_name = "Coax_HFSS_t02"

small_number = float_info.epsilon * 10
secure_random = secrets.SystemRandom()


@pytest.fixture(scope="class")
def aedtapp(add_app):
    app = add_app(project_name=test_project_name, subfolder=test_subfolder)
    return app


class TestClass:
    @pytest.fixture(autouse=True)
    def init(self, aedtapp, local_scratch):
        self.aedtapp = aedtapp
        self.local_scratch = local_scratch

    def restore_model(self):
        for name in self.aedtapp.modeler.get_matched_object_name("outer*"):
            self.aedtapp.modeler.delete(name)
        outer = self.aedtapp.modeler.create_cylinder(
            orientation="X", origin=[0, 0, 0], radius=1, height=20, name="outer", material="Aluminum"
        )
        for name in self.aedtapp.modeler.get_matched_object_name("Core*"):
            self.aedtapp.modeler.delete(name)
        core = self.aedtapp.modeler.create_cylinder(
            orientation="X", origin=[0, 0, 0], radius=0.8, height=20, name="Core", material="teflon_based"
        )
        for name in self.aedtapp.modeler.get_matched_object_name("inner*"):
            self.aedtapp.modeler.delete(name)
        inner = self.aedtapp.modeler.create_cylinder(
            orientation="X", origin=[0, 0, 0], radius=0.3, height=20, name="inner", material="Aluminum"
        )

        for name in self.aedtapp.modeler.get_matched_object_name("Poly1*"):
            self.aedtapp.modeler.delete(name)
        udp1 = [0, 0, 0]
        udp2 = [5, 0, 0]
        udp3 = [5, 5, 0]
        self.aedtapp.modeler.create_polyline([udp1, udp2, udp3], name="Poly1", xsection_type="Rectangle")

        self.aedtapp.modeler.subtract(outer, core)
        self.aedtapp.modeler.subtract(core, inner)

    def test_01_model_units(self):
        self.aedtapp.modeler.model_units = "cm"
        assert self.aedtapp.modeler.model_units == "cm"
        self.restore_model()

    def test_02_boundingbox(self):
        bounding = self.aedtapp.modeler.obounding_box
        assert len(bounding) == 6

    def test_04_convert_to_selection(self):
        assert type(self.aedtapp.modeler.convert_to_selections("inner", True)) is list
        assert type(self.aedtapp.modeler.convert_to_selections("inner", False)) is str

    def test_05_split(self):
        self.aedtapp.insert_design("split_test")
        box1 = self.aedtapp.modeler.create_box([-10, -10, -10], [20, 20, 20], "box_to_split", color=(255, 0, 0))
        assert box1.color == (255, 0, 0)
        box2 = self.aedtapp.modeler.create_box([-10, -10, -10], [20, 20, 20], "box_to_split2", transparency=1)
        assert box2.transparency == 1
        split = self.aedtapp.modeler.split(box1.name, 2)
        assert isinstance(split, list)
        assert isinstance(split[0], str)
        split2 = box2.split(
            1,
        )
        assert isinstance(split2, list)
        assert box2.name in split2[0]
        box3 = self.aedtapp.modeler.create_box([10, 10, 10], [20, 20, 20], "box_to_split3", display_wireframe=True)
        assert box3.display_wireframe
        rect1 = self.aedtapp.modeler.create_rectangle(
            self.aedtapp.PLANE.XY, [10, 8, 20], [20, 30], name="rect1", transparency=0.5, display_wireframe=True
        )
        assert rect1.transparency == 0.5
        assert rect1.display_wireframe
        assert rect1.name == "rect1"
        split = self.aedtapp.modeler.split(assignment=box3, sides="Both", tool=rect1.id)
        assert isinstance(split, list)
        assert isinstance(split[0], str)
        obj_split = [obj for obj in self.aedtapp.modeler.object_list if obj.name == split[1]][0]
        rect2 = self.aedtapp.modeler.create_rectangle(self.aedtapp.PLANE.XY, [10, 8, 14], [20, 30], name="rect2")
        split = self.aedtapp.modeler.split(assignment=obj_split, sides="Both", tool=rect2.faces[0])
        assert isinstance(split, list)
        assert isinstance(split[0], str)
        obj_split = [obj for obj in self.aedtapp.modeler.object_list if obj.name == split[1]][0]
        self.aedtapp.modeler.create_rectangle(self.aedtapp.PLANE.XY, [10, 8, 12], [20, 30], name="rect3")
        split = self.aedtapp.modeler.split(assignment=obj_split, sides="Both", tool="rect3")
        assert isinstance(split, list)
        assert isinstance(split[0], str)
        obj_split = [obj for obj in self.aedtapp.modeler.object_list if obj.name == split[1]][0]
        assert not self.aedtapp.modeler.split(assignment=obj_split)
        box4 = self.aedtapp.modeler.create_box([20, 20, 20], [20, 20, 20], "box_to_split4")
        poly2 = self.aedtapp.modeler.create_polyline(
            points=[[35, 16, 30], [30, 25, 30], [30, 45, 30]], segment_type="Arc"
        )
        split = self.aedtapp.modeler.split(assignment=box4, sides="Both", tool=poly2.name)
        assert isinstance(split, list)
        assert isinstance(split[0], str)
        obj_split = [obj for obj in self.aedtapp.modeler.object_list if obj.name == split[1]][0]
        poly3 = self.aedtapp.modeler.create_polyline(
            points=[[35, 16, 35], [30, 25, 35], [30, 45, 35]], segment_type="Arc"
        )
        split = self.aedtapp.modeler.split(assignment=obj_split, sides="Both", tool=poly3)
        assert isinstance(split, list)
        assert isinstance(split[0], str)
        obj_split = [obj for obj in self.aedtapp.modeler.object_list if obj.name == split[1]][0]
        poly4 = self.aedtapp.modeler.create_polyline(
            points=[[35, 16, 37], [30, 25, 37], [30, 45, 37]], segment_type="Arc"
        )
        split = self.aedtapp.modeler.split(assignment=obj_split, sides="Both", tool=poly4.edges[0])
        assert isinstance(split, list)
        assert isinstance(split[0], str)

    def test_06_duplicate_and_mirror(self):
        self.restore_model()
        udp = self.aedtapp.modeler.Position(20, 20, 20)
        udp2 = self.aedtapp.modeler.Position(30, 40, 40)
        out = self.aedtapp.modeler.duplicate_and_mirror("outer", udp, udp2)
        assert len(out) > 0

    def test_07_mirror(self):
        udp = self.aedtapp.modeler.Position(0, 0, 0)
        udp2 = self.aedtapp.modeler.Position(30, 40, 40)
        status = self.aedtapp.modeler.mirror("outer", udp, udp2)
        assert status

    def test_08_duplicate_around_axis(self):
        udp = self.aedtapp.modeler.Position(0, 0, 0)
        num_clones = 3
        status, mirror = self.aedtapp.modeler.duplicate_around_axis("outer", udp, 45, num_clones)
        assert status
        assert isinstance(mirror, list)
        assert len(mirror) == num_clones - 1

    def test_08_duplicate_along_line(self):
        udp = self.aedtapp.modeler.Position(5, 5, 5)
        num_clones = 5
        status, mirror = self.aedtapp.modeler.duplicate_along_line("outer", udp, num_clones)
        assert status
        assert isinstance(mirror, list)
        assert len(mirror) == num_clones - 1

    def test_09_thicken_sheet(self):
        udp = self.aedtapp.modeler.Position(0, 0, 0)
        id5 = self.aedtapp.modeler.create_circle(self.aedtapp.PLANE.XY, udp, 10, name="sheet1")
        udp = self.aedtapp.modeler.Position(100, 100, 100)
        id6 = self.aedtapp.modeler.create_circle(self.aedtapp.PLANE.XY, udp, 10, name="sheet2")
        status = self.aedtapp.modeler.thicken_sheet(id5, 3)
        assert status
        status = self.aedtapp.modeler.automatic_thicken_sheets(id6, 3, False)
        assert status
        status = self.aedtapp.modeler.move_face([id6.faces[0].id, id6.faces[2]])
        assert status
        status = self.aedtapp.modeler.move_face([id6.faces[0].id, id5.faces[0]])
        assert status

    def test_11_split(self):
        self.restore_model()
        assert self.aedtapp.modeler.split("Poly1", self.aedtapp.PLANE.XY)

    def test_12_separate_bodies(self):
        self.aedtapp.modeler.create_cylinder(
            orientation="Z", origin=[0, -20, 15], radius=40, height=20, name="SearchCoil", material="copper"
        )
        self.aedtapp.modeler.create_cylinder(
            orientation="Z", origin=[0, -20, 15], radius=20, height=20, name="Bore", material="copper"
        )
        self.aedtapp.modeler.subtract("SearchCoil", "Bore", keep_originals=False)
        self.aedtapp.modeler.section("SearchCoil", "YZ")
        object_list = self.aedtapp.modeler.separate_bodies("SearchCoil_Section1")
        assert isinstance(object_list, list)
        assert len(object_list) == 2

    def test_13_rotate(self):
        assert self.aedtapp.modeler.rotate("Poly1", self.aedtapp.AXIS.X, 30)

    def test_14_subtract(self):
        o1 = self.aedtapp.modeler["outer"].clone()
        o2 = self.aedtapp.modeler["inner"].clone()
        assert self.aedtapp.modeler.subtract(o1, o2)

    def test_15_purge_history(self):
        o1 = self.aedtapp.modeler["outer"].clone()
        o2 = self.aedtapp.modeler["inner"].clone()
        assert self.aedtapp.modeler.purge_history([o1, o2])

    def test_16_get_model_bounding_box(self):
        assert len(self.aedtapp.modeler.get_model_bounding_box()) == 6

    def test_17_unite(self):
        o1 = self.aedtapp.modeler["outer"].clone()
        o2 = self.aedtapp.modeler["inner"].clone()
        assert (
            self.aedtapp.modeler.unite(
                [o1, o2],
            )
            == o1.name
        )

    def test_18_chamfer(self):
        o1 = self.aedtapp.modeler["box_to_split"]
        assert abs(o1.volume - 4000.0) / 4000.0 < small_number
        assert o1.top_edge_x.chamfer(1)
        if config["desktopVersion"] == "2022.2":
            assert abs(o1.volume - 3995.0) / 3995.0 < small_number  # Volume decreased
        else:
            assert abs(o1.volume - 3990.0) / 3990.0 < small_number  # Volume decreased

    def test_19_clone(self):
        self.restore_model()
        status, _ = self.aedtapp.modeler.clone("Poly1")
        assert status

    def test_20_intersect(self):
        udp = [0, 0, 0]
        o1 = self.aedtapp.modeler.create_rectangle(self.aedtapp.PLANE.XY, udp, [5, 10], name="Rect1")
        o2 = self.aedtapp.modeler.create_rectangle(self.aedtapp.PLANE.XY, udp, [3, 12], name="Rect2")
        assert (
            self.aedtapp.modeler.intersect(
                [o1, o2],
            )
            == o1.name
        )

    def test_21_connect(self):
        udp = [0, 0, 0]
        id1 = self.aedtapp.modeler.create_rectangle(self.aedtapp.PLANE.XY, udp, [5, 10])
        udp = self.aedtapp.modeler.Position(0, 0, 10)
        id2 = self.aedtapp.modeler.create_rectangle(self.aedtapp.PLANE.XY, udp, [-3, 10])
        objects_after_connection = self.aedtapp.modeler.connect([id1, id2])
        assert isinstance(objects_after_connection, list)
        assert id1.name == objects_after_connection[0].name
        assert len(objects_after_connection) == 1

    def test_22_translate(self):
        udp = [0, 0, 0]
        id1 = self.aedtapp.modeler.create_rectangle(self.aedtapp.PLANE.XY, udp, [5, 10])
        id2 = self.aedtapp.modeler.create_rectangle(self.aedtapp.PLANE.XY, udp, [3, 12])
        udp2 = self.aedtapp.modeler.Position(0, 20, 5)
        assert self.aedtapp.modeler.move([id1, id2], udp2)

    def test_24_check_plane(self):
        udp = [0, 0, 0]
        o1 = self.aedtapp.modeler.create_box(udp, [4, 5, 5])
        plane = self.aedtapp.modeler.check_plane(o1.id, udp)
        planes = ["XY", "XZ", "YZ"]
        assert plane in planes

    def test_25_clean_object_name(self):
        # TODO
        assert True

    def test_26_create_airbox(self):
        o1 = self.aedtapp.modeler.create_airbox(10)
        o2 = self.aedtapp.modeler.create_airbox(50, "Relative", "Second_airbox")
        assert o1.id > 0
        assert o2.id > 0

    def test_27_create_region(self):
        x_pos = 20
        y_pos = 21
        z_pos = 32
        x_neg = 49
        y_neg = 50
        z_neg = 100

        bounding_dims_1 = self.aedtapp.modeler.get_bounding_dimension()
        assert not self.aedtapp.modeler.create_air_region(*["20mm", 20, "30mm", "50", 50, 100])
        assert self.aedtapp.modeler.create_air_region(x_pos, y_pos, z_pos, x_neg, y_neg, z_neg, False)
        bounding_dims_2 = self.aedtapp.modeler.get_bounding_dimension()
        assert abs(bounding_dims_2[0] - bounding_dims_1[0] - (x_pos + x_neg)) < small_number
        assert abs(bounding_dims_2[1] - bounding_dims_1[1] - (y_pos + y_neg)) < small_number
        assert abs(bounding_dims_2[2] - bounding_dims_1[2] - (z_pos + z_neg)) < small_number
        self.aedtapp.modeler["Region"].delete()
        self.aedtapp["region_param"] = "20mm"
        assert self.aedtapp.modeler.create_air_region("region_param", 20, "30", "50", 50, 100, False)
        assert self.aedtapp.modeler.edit_region_dimensions(["40mm", "30mm", 30, 50, 50, 100])
        self.aedtapp.modeler["Region"].delete()
        assert self.aedtapp.modeler.create_air_region("20", 20, 30, 50, 50, 100)
        assert self.aedtapp.modeler.edit_region_dimensions([40, 30, 30, 50, 50, 100])

    def test_28A_create_face_list(self):
        fl = self.aedtapp.modeler.get_object_faces("Second_airbox")
        fl2 = self.aedtapp.modeler.create_face_list(fl, "my_face_list")
        assert fl2
        assert self.aedtapp.modeler.create_face_list(fl, "my_face_list") == fl2
        assert self.aedtapp.modeler.create_face_list(fl)
        assert self.aedtapp.modeler.create_face_list([str(fl[0])])
        assert not self.aedtapp.modeler.create_face_list(["outer2"])

    def test_28B_create_object_list(self):
        fl1 = self.aedtapp.modeler.create_object_list(["Second_airbox"], "my_object_list")
        assert fl1
        assert self.aedtapp.modeler.create_object_list(["Second_airbox"], "my_object_list") == fl1
        assert self.aedtapp.modeler.create_object_list(["Core", "outer"])
        self.aedtapp.modeler.user_lists[4].props["List"] = ["outer", "Core", "inner"]
        self.aedtapp.modeler.user_lists[4].auto_update = False
        fl = self.aedtapp.modeler.get_object_faces("Core")
        self.aedtapp.modeler.user_lists[4].props["Type"] = "Face"
        self.aedtapp.modeler.user_lists[4].props["List"] = fl
        self.aedtapp.modeler.user_lists[4].update()
        assert self.aedtapp.modeler.user_lists[2].rename("new_list")
        assert self.aedtapp.modeler.user_lists[2].delete()
        assert self.aedtapp.modeler.create_object_list(["Core2", "outer"])
        assert not self.aedtapp.modeler.create_object_list(["Core2", "Core3"])

    def test_29_create_outer_face_list(self):
        assert self.aedtapp.modeler.create_outer_facelist(["Second_airbox"])

    def test_30_create_waveguide(self):
        position = self.aedtapp.modeler.Position(0, 0, 0)
        wg1 = self.aedtapp.modeler.create_waveguide(position, self.aedtapp.AXIS.X, wg_length=2000)
        assert isinstance(wg1, tuple)
        position = self.aedtapp.modeler.Position(0, 0, 0)
        wg9 = self.aedtapp.modeler.create_waveguide(
            position,
            self.aedtapp.AXIS.Z,
            wgmodel="WG9",
            wg_length=1500,
            parametrize_h=True,
            create_sheets_on_openings=True,
        )
        assert wg9[0].id > 0
        assert wg9[1].id > 0
        assert wg9[2].id > 0
        wgfail = self.aedtapp.modeler.create_waveguide(
            position, self.aedtapp.AXIS.Z, wgmodel="MYMODEL", wg_length=2000, parametrize_h=True
        )
        assert not wgfail

    def test_31_set_objects_unmodel(self):
        assert self.aedtapp.modeler.set_object_model_state("Second_airbox", False)
        assert self.aedtapp.modeler.set_object_model_state(["Second_airbox", "AirBox_Auto"], False)

    def test_32_find_port_faces(self):
        wg_x = self.aedtapp.modeler.create_waveguide([0, 5000, 0], self.aedtapp.AXIS.Y, wg_length=1000, wg_thickness=40)
        port1 = self.aedtapp.modeler.create_rectangle(self.aedtapp.PLANE.ZX, [-40, 5000, -40], [346.7, 613.4])
        port2 = self.aedtapp.modeler.create_rectangle(self.aedtapp.PLANE.ZX, [-40, 6000, -40], [346.7, 613.4])
        faces_created = self.aedtapp.modeler.find_port_faces([port1.name, port2.name])
        assert len(faces_created) == 4
        assert "_Face1Vacuum" in faces_created[1]
        assert "_Face1Vacuum" in faces_created[3]

    def test_33_duplicate_around_axis(self):
        id1 = self.aedtapp.modeler.create_box([10, 10, 10], [4, 5, 5])
        axis = self.aedtapp.AXIS.X
        _, obj_list = self.aedtapp.modeler.duplicate_around_axis(
            id1, axis=axis, angle="180deg", clones=2, create_new_objects=False
        )
        # if create_new_objects is set to False, there should be no new objects
        assert not obj_list

    def test_35_activate_variable_for_tuning(self):
        self.aedtapp["test_opti"] = "10mm"
        self.aedtapp["$test_opti1"] = "10mm"
        assert self.aedtapp.activate_variable_tuning("test_opti")
        assert self.aedtapp.activate_variable_tuning("$test_opti1", "1mm", "10mm")
        assert self.aedtapp.deactivate_variable_tuning("test_opti")
        try:
            self.aedtapp.activate_variable_tuning("Idontexist")
            assert False
        except Exception:
            assert True

    def test_36_activate_variable_for_optimization(self):
        assert self.aedtapp.activate_variable_optimization("test_opti")
        assert self.aedtapp.activate_variable_optimization("$test_opti1", "2mm", "5mm")
        assert self.aedtapp.deactivate_variable_optimization("test_opti")

    def test_37_activate_variable_for_sensitivity(self):
        assert self.aedtapp.activate_variable_sensitivity("test_opti")
        assert self.aedtapp.activate_variable_sensitivity("$test_opti1", "1mm", "10mm")
        assert self.aedtapp.deactivate_variable_sensitivity("$test_opti1")

    def test_38_activate_variable_for_statistical(self):
        assert self.aedtapp.activate_variable_statistical("test_opti")
        assert self.aedtapp.activate_variable_statistical("$test_opti1", "1mm", "10mm", "3%", mean="2mm")
        assert self.aedtapp.deactivate_variable_statistical("test_opti")

    def test_39_create_coaxial(self):
        coax = self.aedtapp.modeler.create_coaxial([0, 0, 0], self.aedtapp.AXIS.X)
        assert isinstance(coax[0].id, int)
        assert isinstance(coax[1].id, int)
        assert isinstance(coax[2].id, int)

    def test_40_create_coordinate_system(self):
        cs = self.aedtapp.modeler.create_coordinate_system()
        self.aedtapp.modeler.coordinate_systems
        cs1 = self.aedtapp.modeler.create_coordinate_system()
        assert cs
        assert cs.update()
        assert cs.change_cs_mode(1)
        assert cs.change_cs_mode(2)

        with pytest.raises(ValueError):
            cs.change_cs_mode(3)
        assert cs.change_cs_mode(0)
        assert cs.delete()
        assert len(self.aedtapp.modeler.coordinate_systems) == 1
        cs2 = self.aedtapp.modeler.create_coordinate_system(reference_cs=cs1.name)
        cs3 = self.aedtapp.modeler.create_coordinate_system(reference_cs=cs2.name)
        assert cs1.delete()
        assert not self.aedtapp.modeler.coordinate_systems
        cs4 = self.aedtapp.modeler.create_coordinate_system()
        cs5 = self.aedtapp.modeler.create_coordinate_system()
        cs6 = self.aedtapp.modeler.create_coordinate_system(reference_cs=cs4.name)
        assert cs4.delete()
        assert len(self.aedtapp.modeler.coordinate_systems) == 1
        assert cs5.delete()

    def test_40a_create_face_coordinate_system(self):
        box = self.aedtapp.modeler.create_box(origin=[0, 0, 0], sizes=[2, 2, 2], name="box_cs")
        face = box.faces[0]
        fcs = self.aedtapp.modeler.create_face_coordinate_system(face, face.edges[0], face.edges[1])
        assert fcs
        assert fcs.face_id == face.id
        assert fcs.update()
        assert fcs.delete()
        fcs2 = self.aedtapp.modeler.create_face_coordinate_system(face, face, face.edges[1].vertices[0])
        assert fcs2
        assert fcs2.delete()
        fcs2 = self.aedtapp.modeler.create_face_coordinate_system(
            face, face.edges[0].vertices[0], face.edges[1].vertices[1]
        )
        assert fcs2
        assert fcs2.delete()
        fcs3 = self.aedtapp.modeler.create_face_coordinate_system(
            face, face.edges[1].vertices[1], face.edges[1].vertices[0]
        )
        assert fcs3
        assert fcs3.delete()
        fcs4 = self.aedtapp.modeler.create_face_coordinate_system(face, face.edges[2], face.edges[3], name="test")
        assert fcs4
        assert fcs4.name == "test"
        assert fcs4.delete()
        fcs5 = self.aedtapp.modeler.create_face_coordinate_system(face, face.edges[2], face.edges[3], axis="Y")
        assert fcs5
        assert fcs5.props["WhichAxis"] == "Y"
        assert fcs5.delete()
        fcs6 = self.aedtapp.modeler.create_face_coordinate_system(face, face.edges[2], face.edges[3], rotation=14.3)
        assert fcs6
        assert fcs6.props["ZRotationAngle"] == "14.3deg"
        assert fcs6.delete()
        fcs7 = self.aedtapp.modeler.create_face_coordinate_system(face, face.edges[2], face.edges[3], offset=[0.2, 0.3])
        assert fcs7
        assert fcs7.props["XOffset"] == "0.2" + self.aedtapp.modeler.model_units
        assert fcs7.props["YOffset"] == "0.3" + self.aedtapp.modeler.model_units
        assert fcs7.delete()
        fcs8 = self.aedtapp.modeler.create_face_coordinate_system(face.id, face.edges[0].id, face.edges[1].id)
        assert fcs8
        assert fcs8.delete()
        fcs9 = self.aedtapp.modeler.create_face_coordinate_system(face.id, face.edges[0].vertices[0].id, face.id)
        assert fcs9
        assert fcs9.delete()
        fcs10 = self.aedtapp.modeler.create_face_coordinate_system(
            face, face.edges[2], face.edges[3], always_move_to_end=False
        )
        assert fcs10
        assert fcs10.props["MoveToEnd"] is False
        assert fcs10.delete()
        fcs = FaceCoordinateSystem(self.aedtapp.modeler)
        assert fcs._part_name is None
        assert fcs._get_type_from_id(box.id) == "3dObject"
        assert fcs._get_type_from_id(face.id) == "Face"
        assert fcs._get_type_from_id(face.edges[0].id) == "Edge"
        assert fcs._get_type_from_id(face.edges[0].vertices[0].id) == "Vertex"
        assert fcs._get_type_from_object(box) == "3dObject"
        assert fcs._get_type_from_object(face) == "Face"
        assert fcs._get_type_from_object(face.edges[0]) == "Edge"
        assert fcs._get_type_from_object(face.edges[0].vertices[0]) == "Vertex"

    def test_40b_create_object_coordinate_system(self):
        box = self.aedtapp.modeler.objects_by_name["box_cs"]
        cs = self.aedtapp.modeler.create_object_coordinate_system(
            assignment=box, origin=box.faces[0], x_axis=box.edges[0], y_axis=[0, 0, 0], name="obj_cs"
        )
        assert cs
        assert cs.name == "obj_cs"
        assert cs.entity_id == box.id
        if config["desktopVersion"] == "2022.2":
            assert not cs.ref_cs
        else:
            assert cs.ref_cs == "Global"
        cs.props["MoveToEnd"] = False
        assert not cs.props["MoveToEnd"]
        cs.props["yAxis"]["xDirection"] = 1
        cs.props["yAxis"]["xDirection"] = "1"
        cs.props["yAxis"]["xDirection"] = "1cm"
        assert cs.update()
        cs.delete()
        cs = self.aedtapp.modeler.create_object_coordinate_system(
            assignment=box.name, origin=box.edges[0], x_axis=[1, 0, 0], y_axis=[0, 1, 0], name="obj_cs"
        )
        assert cs
        assert cs.name == "obj_cs"
        assert cs.entity_id == box.id
        if config["desktopVersion"] == "2022.2":
            assert not cs.ref_cs
        else:
            assert cs.ref_cs == "Global"
        cs.props["MoveToEnd"] = False
        assert not cs.props["MoveToEnd"]
        cs.props["xAxis"]["xDirection"] = 1
        cs.props["xAxis"]["xDirection"] = "1"
        cs.props["xAxis"]["xDirection"] = "1cm"
        cs.props["yAxis"]["xDirection"] = 1
        cs.props["yAxis"]["xDirection"] = "1"
        cs.props["yAxis"]["xDirection"] = "1cm"
        assert cs.update()
        cs.delete()
        cs = self.aedtapp.modeler.create_object_coordinate_system(
            assignment=box.name, origin=[0, 0.8, 0], x_axis=[1, 0, 0], y_axis=[0, 1, 0], name="obj_cs"
        )
        cs.props["Origin"]["XPosition"] = 1
        cs.props["Origin"]["XPosition"] = "1"
        cs.props["Origin"]["XPosition"] = "1cm"
        cs.props["ReverseXAxis"] = True
        cs.props["ReverseYAxis"] = True
        assert cs.props["ReverseXAxis"]
        assert cs.props["ReverseYAxis"]
        assert cs.update()
        cs.delete()
        cs = self.aedtapp.modeler.create_object_coordinate_system(
            assignment=box.name, origin=box.vertices[1], x_axis=box.faces[2], y_axis=box.faces[4], name="obj_cs"
        )
        cs.props["Origin"]["XPosition"] = 1
        cs.props["Origin"]["XPosition"] = "1"
        cs.props["Origin"]["XPosition"] = "1cm"
        cs.props["ReverseXAxis"] = True
        cs.props["ReverseYAxis"] = True
        assert cs.props["ReverseXAxis"]
        assert cs.props["ReverseYAxis"]
        assert cs.update()
        cs.delete()

    def test_41_rename_coordinate(self):
        cs = self.aedtapp.modeler.create_coordinate_system(name="oldname")
        assert cs.name == "oldname"
        assert cs.rename("newname")
        assert cs.name == "newname"
        assert cs.delete()

    def test_41a_rename_face_coordinate(self):
        box = self.aedtapp.modeler.objects_by_name["box_cs"]
        face = box.faces[0]
        fcs = self.aedtapp.modeler.create_face_coordinate_system(face, face.edges[0], face.edges[1], name="oldname")
        assert fcs.name == "oldname"
        assert fcs.rename("newname")
        assert fcs.name == "newname"
        assert fcs.delete()

    def test_41b_rename_object_coordinate(self):
        box = self.aedtapp.modeler.create_box([0, 0, 0], [2, 2, 2])
        cs = self.aedtapp.modeler.create_object_coordinate_system(
            assignment=box, origin=box.faces[0], x_axis=box.edges[0], y_axis=[0, 0, 0], name="obj_cs"
        )
        assert cs.name == "obj_cs"
        assert cs.rename("new_obj_cs")
        assert cs.name == "new_obj_cs"
        assert cs.delete()

    def test_42a_update_coordinate_system(self):
        cs_list = self.aedtapp.modeler.coordinate_systems
        [l.delete() for l in cs_list]
        cs1 = self.aedtapp.modeler.create_coordinate_system(name="CS1", view="rotate")
        cs2 = self.aedtapp.modeler.create_coordinate_system(name="CS2", mode="view", view="iso")
        cs2.ref_cs = "CS1"
        assert cs2.update()
        cs1.props["OriginX"] = 10
        cs1.props["OriginY"] = 20
        cs1.props["OriginZ"] = 10
        assert cs1.update()
        cs1.origin = [10, 10, 10]
        assert cs2.change_cs_mode(2)
        cs2.props["Phi"] = 30
        cs2.props["Theta"] = 30
        assert cs2.update()
        cs2.ref_cs = "Global"
        assert cs2.update()
        assert tuple(self.aedtapp.modeler.oeditor.GetCoordinateSystems()) == ("Global", "CS1", "CS2")
        assert len(self.aedtapp.modeler.coordinate_systems) == 2
        assert cs2.delete()

    def test_42b_update_face_coordinate_system(self):
        CS_list = self.aedtapp.modeler.coordinate_systems
        [l.delete() for l in CS_list]
        box = self.aedtapp.modeler.create_box([0, 0, 0], [2, 2, 2])
        face = box.faces[0]
        fcs = self.aedtapp.modeler.create_face_coordinate_system(face, face.edges[0], face.edges[1], name="FCS1")
        assert fcs
        fcs.props["XOffset"] = "0.2mm"
        fcs.props["YOffset"] = "0.3mm"
        assert fcs.props["XOffset"] == "0.2mm"
        assert fcs.props["YOffset"] == "0.3mm"
        assert fcs.update()
        fcs.props["ZRotationAngle"] = "14.3deg"
        assert fcs.update()
        assert fcs.props["ZRotationAngle"] == "14.3deg"
        fcs.props["WhichAxis"] = "Y"
        assert fcs.update()
        assert fcs.props["WhichAxis"] == "Y"
        fcs.props["MoveToEnd"] = False
        assert fcs.update()
        assert fcs.props["MoveToEnd"] is False
        assert tuple(self.aedtapp.modeler.oeditor.GetCoordinateSystems()) == ("Global", "FCS1")
        assert len(self.aedtapp.modeler.coordinate_systems) == 1
        assert fcs.delete()

    def test_43_set_as_working_cs(self):
        for cs in self.aedtapp.modeler.coordinate_systems:
            cs.delete()
        cs1 = self.aedtapp.modeler.create_coordinate_system(name="first")
        cs2 = self.aedtapp.modeler.create_coordinate_system(name="second", mode="view", view="iso")
        assert cs1.set_as_working_cs()
        assert cs2.set_as_working_cs()

    def test_43b_set_as_working_face_cs(self):
        for cs in self.aedtapp.modeler.coordinate_systems:
            cs.delete()
        box = self.aedtapp.modeler.objects_by_name["box_cs"]
        face = box.faces[0]
        fcs1 = self.aedtapp.modeler.create_face_coordinate_system(face, face.edges[0], face.edges[1])
        fcs2 = self.aedtapp.modeler.create_face_coordinate_system(face, face, face.edges[1])
        assert fcs1.set_as_working_cs()
        assert fcs2.set_as_working_cs()

    def test_43c_set_as_working_object_cs(self):
        for cs in self.aedtapp.modeler.coordinate_systems:
            cs.delete()
        box = self.aedtapp.modeler.objects_by_name["box_cs"]
        obj_cs = self.aedtapp.modeler.create_object_coordinate_system(
            assignment=box.name, origin=box.edges[0], x_axis=[1, 0, 0], y_axis=[0, 1, 0], name="obj_cs"
        )
        obj_cs_1 = self.aedtapp.modeler.create_object_coordinate_system(
            assignment=box.name, origin=box.edges[0], x_axis=[1, 0, 0], y_axis=[0, 1, 0], name="obj_cs_1"
        )
        assert obj_cs.set_as_working_cs()
        assert obj_cs_1.set_as_working_cs()
        obj_cs.delete()
        obj_cs_1.delete()

    def test_43_set_working_coordinate_system(self):
        cs1 = self.aedtapp.modeler.create_coordinate_system(name="new1")
        assert self.aedtapp.modeler.set_working_coordinate_system("Global")
        assert self.aedtapp.modeler.get_working_coordinate_system() == "Global"

        assert self.aedtapp.modeler.set_working_coordinate_system("new1")
        assert self.aedtapp.modeler.get_working_coordinate_system() == "new1"

        assert self.aedtapp.modeler.set_working_coordinate_system("Global")
        assert self.aedtapp.modeler.get_working_coordinate_system() == "Global"

        assert self.aedtapp.modeler.set_working_coordinate_system(cs1)
        assert self.aedtapp.modeler.get_working_coordinate_system() == cs1.name

    def test_43_set_working_face_coordinate_system(self):
        box = self.aedtapp.modeler.create_box([0, 0, 0], [2, 2, 2])
        face = box.faces[0]
        fcs = self.aedtapp.modeler.create_face_coordinate_system(face, face, face.edges[1], name="new2")

        assert self.aedtapp.modeler.set_working_coordinate_system("Global")
        assert self.aedtapp.modeler.get_working_coordinate_system() == "Global"

        assert self.aedtapp.modeler.set_working_coordinate_system("new2")
        assert self.aedtapp.modeler.get_working_coordinate_system() == "new2"

        assert self.aedtapp.modeler.set_working_coordinate_system("Global")
        assert self.aedtapp.modeler.get_working_coordinate_system() == "Global"

        assert self.aedtapp.modeler.set_working_coordinate_system(fcs)
        assert self.aedtapp.modeler.get_working_coordinate_system() == fcs.name

    def test_44_sweep_around_axis(self):
        rect1 = self.aedtapp.modeler.create_rectangle(self.aedtapp.PLANE.YZ, [0, 0, 0], [20, 20], "rectangle_to_split")
        assert rect1.sweep_around_axis("Z", sweep_angle=360, draft_angle=0)

    def test_45_sweep_along_path(self):
        udp1 = [0, 0, 0]
        udp2 = [5, 0, 0]
        path = self.aedtapp.modeler.create_polyline([udp1, udp2], name="Poly1")
        rect1 = self.aedtapp.modeler.create_rectangle(self.aedtapp.PLANE.YZ, [0, 0, 0], [20, 20], "rectangle_to_sweep")
        assert rect1.sweep_along_path(path)

    def test_46_section_object(self):
        box1 = self.aedtapp.modeler.create_box([-10, -10, -10], [20, 20, 20], "box_to_split")
        assert self.aedtapp.modeler.section(box1, 0, create_new=True, section_cross_object=False)

    def test_47_sweep_along_vector(self):
        sweep_vector = [5, 0, 0]
        rect1 = self.aedtapp.modeler.create_rectangle(self.aedtapp.PLANE.YZ, [0, 0, 0], [20, 20], "rectangle_to_vector")
        assert rect1.sweep_along_vector(sweep_vector)
        rect2 = self.aedtapp.modeler.create_rectangle(
            self.aedtapp.PLANE.YZ, [0, 40, 0], [20, 20], "rectangle_to_vector2"
        )
        rect3 = self.aedtapp.modeler.create_rectangle(
            self.aedtapp.PLANE.YZ, [0, 80, 0], [20, 20], "rectangle_to_vector3"
        )
        rect_list = [rect2, rect3]
        assert self.aedtapp.modeler.sweep_along_vector(assignment=rect_list, sweep_vector=sweep_vector)

    def test_48_coordinate_systems_parametric(self):
        self.aedtapp["var1"] = "5mm"
        self.aedtapp["var2"] = "(3mm+var1)*2"
        cs1 = self.aedtapp.modeler.create_coordinate_system(name="CSP1", mode="axis", x_pointing=["var1", "var2", 0])
        cs2 = self.aedtapp.modeler.create_coordinate_system(name="CSP2", mode="axis", x_pointing=["5mm", "16mm", 0])
        assert cs1.quaternion == cs2.quaternion

        self.aedtapp["var3"] = "43deg"
        self.aedtapp["var4"] = "(20deg+var3)*2"
        cs3 = self.aedtapp.modeler.create_coordinate_system(name="CSP3", mode="zxz", phi="var3", theta="var4", psi=0)
        cs4 = self.aedtapp.modeler.create_coordinate_system(name="CSP4", mode="zxz", phi=43, theta="126deg", psi=0)
        tol = 1e-9
        assert sum([abs(x1 - x2) for (x1, x2) in zip(cs3.quaternion, cs4.quaternion)]) < tol

    def test_49_sweep_along_path(self):
        self.aedtapp.modeler.set_working_coordinate_system("Global")
        first_points = [[1.0, 1.0, 0], [1.0, 2.0, 1.0], [1.0, 3.0, 1.0]]
        first_line = self.aedtapp.modeler.create_polyline([[0.0, 0.0, 0.0], first_points[0]])
        assert first_line.insert_segment(points=first_points, segment=PolylineSegment("Spline", num_points=3))

        assert (
            self.aedtapp.get_oo_property_value(
                self.aedtapp.modeler.oeditor, first_line.name + "\\CreatePolyline:1", "Number of curves"
            )
            == "2"
        )
        assert (
            self.aedtapp.get_oo_property_value(
                self.aedtapp.modeler.oeditor, first_line.name + "\\CreatePolyline:1", "Number of segments"
            )
            == "0"
        )
        assert (
            self.aedtapp.get_oo_property_value(
                self.aedtapp.modeler.oeditor, first_line.name + "\\CreatePolyline:1", "Number of points"
            )
            == "4"
        )

        second_points = [[3.0, 2.0, 0], [3.0, 3.0, 1.0], [3.0, 4.0, 1.0]]
        second_line = self.aedtapp.modeler.create_polyline([[0, 0, 0], second_points[0]])
        assert second_line.insert_segment(points=second_points, segment=PolylineSegment("Spline", num_points=3))

        assert second_line.insert_segment(
            points=[[-3.0, 4.0, 1.0], [-3.0, 5.0, 3.0], [-3.0, 6.0, 1.0], [-3.0, 7.0, 2.0], [0, 0, 0]],
            segment=PolylineSegment("Spline", num_points=5),
        )

        assert (
            self.aedtapp.get_oo_property_value(
                self.aedtapp.modeler.oeditor, second_line.name + "\\CreatePolyline:1", "Number of curves"
            )
            == "3"
        )
        assert (
            self.aedtapp.get_oo_property_value(
                self.aedtapp.modeler.oeditor, second_line.name + "\\CreatePolyline:1", "Number of segments"
            )
            == "0"
        )
        assert (
            self.aedtapp.get_oo_property_value(
                self.aedtapp.modeler.oeditor, second_line.name + "\\CreatePolyline:1", "Number of points"
            )
            == "8"
        )

        assert (
            self.aedtapp.get_oo_property_value(
                self.aedtapp.modeler.oeditor, second_line.name + "\\CreatePolyline:1\\Segment0", "Segment Type"
            )
            == "Spline"
        )
        assert (
            self.aedtapp.get_oo_property_value(
                self.aedtapp.modeler.oeditor, second_line.name + "\\CreatePolyline:1\\Segment1", "Segment Type"
            )
            == "Line"
        )
        assert (
            self.aedtapp.get_oo_property_value(
                self.aedtapp.modeler.oeditor, second_line.name + "\\CreatePolyline:1\\Segment2", "Segment Type"
            )
            == "Spline"
        )

        assert (
            self.aedtapp.get_oo_property_value(
                self.aedtapp.modeler.oeditor, second_line.name + "\\CreatePolyline:1\\Segment0", "Number of segments"
            )
            == "0"
        )
        assert (
            self.aedtapp.get_oo_property_value(
                self.aedtapp.modeler.oeditor, second_line.name + "\\CreatePolyline:1\\Segment2", "Number of segments"
            )
            == "0"
        )

    def test_50_move_edge(self):
        box1 = self.aedtapp.modeler.create_box([-10, -10, -10], [20, 20, 20], "edge_movements")
        assert not box1.faces[0].edges[0].move_along_normal(1)
        rect = self.aedtapp.modeler.create_rectangle(self.aedtapp.PLANE.XY, [0, 10, 10], [20, 20], "edge_movements2")
        assert self.aedtapp.modeler.move_edge([rect.edges[0], rect.edges[2]])
        assert rect.faces[0].bottom_edge_x.move_along_normal()

    def test_51_imprint(self):
        rect = self.aedtapp.modeler.create_rectangle(self.aedtapp.PLANE.XY, [0, 10, 10], [20, 20], "imprint1")
        box1 = self.aedtapp.modeler.create_box([-10, -10, -10], [20, 20, 20], "imprint2")
        assert self.aedtapp.modeler.imprint(rect, box1)

    def test_51_imprint_projection(self):
        rect = self.aedtapp.modeler.create_rectangle(self.aedtapp.PLANE.XY, [0, 0, 10], [5, 20], "imprintn1")
        box1 = self.aedtapp.modeler.create_box([-10, -10, -10], [20, 20, 20], "imprintn2")
        assert self.aedtapp.modeler.imprint_normal_projection([rect, box1])
        rect = self.aedtapp.modeler.create_rectangle(self.aedtapp.PLANE.XY, [0, 0, 10], [6, 18], "imprintn3")
        box1 = self.aedtapp.modeler.create_box([-10, -10, -10], [20, 20, 20], "imprintn3")
        assert self.aedtapp.modeler.imprint_vector_projection([rect, box1], [0.2, -0.8, -5], 1)

    def test_52_objects_in_bounding_box(self):
        bounding_box = [-100, -300, -200, 100, 200, 100]
        objects_in_bounding_box = self.aedtapp.modeler.objects_in_bounding_box(bounding_box)
        assert isinstance(objects_in_bounding_box, list)

        bounding_box = [0, 0, 0, 0, 0, 0]
        objects_in_bounding_box = self.aedtapp.modeler.objects_in_bounding_box(bounding_box)
        assert len(objects_in_bounding_box) == 0

        with pytest.raises(ValueError):
            bounding_box = [100, 200, 100, -100, -300]
            self.aedtapp.modeler.objects_in_bounding_box(bounding_box)

    def test_53_wrap_sheet(self):
        rect = self.aedtapp.modeler.create_rectangle(self.aedtapp.PLANE.XY, [2.5, 0, 10], [5, 15], "wrap")
        box1 = self.aedtapp.modeler.create_box([-10, -10, -10], [20, 20, 20], "wrp2")
        box2 = self.aedtapp.modeler.create_box([-10, -10, -10], [20, 20, 20], "wrp3")
        assert self.aedtapp.modeler.wrap_sheet(rect, box1)
        self.aedtapp.odesign.Undo()
        assert rect.wrap_sheet(box1)
        self.aedtapp.odesign.Undo()
        assert box1.wrap_sheet(rect)
        self.aedtapp.odesign.Undo()
        assert not box1.wrap_sheet(box2)

    def test_54_set_variable(self):
        self.aedtapp.variable_manager.set_variable("var_test", expression="123")
        self.aedtapp["var_test"] = "234"
        assert "var_test" in self.aedtapp.variable_manager.design_variable_names
        assert self.aedtapp.variable_manager.design_variables["var_test"].expression == "234"

    def test_55_scale(self):
        assert self.aedtapp.modeler.scale([self.aedtapp.modeler.object_list[0], "Second_airbox"])

    def test_56_global_to_cs(self):
        self.aedtapp.modeler.create_coordinate_system(
            origin=[-1, -2.6, 1],
            name="CS_Test1",
            x_pointing=[-0.70710678118655, -0.70710678118655, 0],
            y_pointing=[-0.70710678118655, 0.70710678118655, 0],
        )
        cs2 = self.aedtapp.modeler.create_coordinate_system(
            origin=[-5.4, 1.4, -8],
            name="CS_Test2",
            reference_cs="CS_Test1",
            x_pointing=[0.83205029433784, 0.55470019622523, 0],
            y_pointing=[-0.55470019622523, 0.83205029433784, 0],
        )
        p1 = self.aedtapp.modeler.global_to_cs([0, 0, 0], "CS_Test1")
        p2 = self.aedtapp.modeler.global_to_cs([0, 0, 0], "CS_Test2")
        p3 = self.aedtapp.modeler.global_to_cs([0, 0, 0], cs2)
        assert all(abs(p1[i] - s) < small_number for i, s in enumerate([-2.5455844122716, 1.1313708498985, 1.0]))
        assert all(abs(p2[i] - s) < small_number for i, s in enumerate([2.2260086876588, -1.8068578500310, 9.0]))
        assert p2 == p3
        assert self.aedtapp.modeler.global_to_cs([0, 0, 0], "Global") == [0, 0, 0]

    def test_57_duplicate_coordinate_system_to_global(self):
        self.aedtapp.modeler.create_coordinate_system(
            origin=[-1, -2.6, 1],
            name="CS_Test3",
            x_pointing=[-0.70710678118655, -0.70710678118655, 0],
            y_pointing=[-0.70710678118655, 0.70710678118655, 0],
        )
        cs4 = self.aedtapp.modeler.create_coordinate_system(
            origin=[-5.4, 1.4, -8],
            name="CS_Test4",
            reference_cs="CS_Test3",
            x_pointing=[0.83205029433784, 0.55470019622523, 0],
            y_pointing=[-0.55470019622523, 0.83205029433784, 0],
        )
        assert self.aedtapp.modeler.duplicate_coordinate_system_to_global("CS_Test4")
        assert self.aedtapp.modeler.duplicate_coordinate_system_to_global(cs4)
        o, q = self.aedtapp.modeler.reference_cs_to_global("CS_Test4")
        assert all(abs(o[i] - s) < 10 * small_number for i, s in enumerate([1.82842712474619, 2.20832611206852, 9.0]))
        assert all(
            abs(q[i] - s) < 10 * small_number for i, s in enumerate([-0.0, -0.09853761796664, 0.99513332666807, 0.0])
        )
        assert self.aedtapp.modeler.reference_cs_to_global(cs4)
        box = self.aedtapp.modeler.create_box([0, 0, 0], [2, 2, 2])
        face = box.faces[0]
        fcs = self.aedtapp.modeler.create_face_coordinate_system(face, face.edges[0], face.edges[1])
        new_fcs = self.aedtapp.modeler.duplicate_coordinate_system_to_global(fcs)
        assert new_fcs
        assert new_fcs.props["Origin"] == fcs.props["Origin"]
        assert new_fcs.props["AxisPosn"] == fcs.props["AxisPosn"]
        assert new_fcs.props["MoveToEnd"] == fcs.props["MoveToEnd"]
        assert new_fcs.props["FaceID"] == fcs.props["FaceID"]
        assert new_fcs.props["WhichAxis"] == fcs.props["WhichAxis"]
        assert int(decompose_variable_value(new_fcs.props["ZRotationAngle"])[0]) == int(
            decompose_variable_value(fcs.props["ZRotationAngle"])[0]
        )
        assert (
            decompose_variable_value(new_fcs.props["ZRotationAngle"])[1]
            == decompose_variable_value(fcs.props["ZRotationAngle"])[1]
        )
        assert new_fcs.props["XOffset"] == fcs.props["XOffset"]
        assert new_fcs.props["YOffset"] == fcs.props["YOffset"]
        assert new_fcs.props["AutoAxis"] == fcs.props["AutoAxis"]
        fcs = self.aedtapp.modeler.create_face_coordinate_system(face, face, face.edges[1])
        new_fcs = self.aedtapp.modeler.duplicate_coordinate_system_to_global(fcs)
        assert new_fcs
        assert new_fcs.props["Origin"] == fcs.props["Origin"]
        assert new_fcs.props["AxisPosn"] == fcs.props["AxisPosn"]
        assert new_fcs.props["MoveToEnd"] == fcs.props["MoveToEnd"]
        assert new_fcs.props["FaceID"] == fcs.props["FaceID"]
        assert new_fcs.props["WhichAxis"] == fcs.props["WhichAxis"]
        assert int(decompose_variable_value(new_fcs.props["ZRotationAngle"])[0]) == int(
            decompose_variable_value(fcs.props["ZRotationAngle"])[0]
        )
        assert (
            decompose_variable_value(new_fcs.props["ZRotationAngle"])[1]
            == decompose_variable_value(fcs.props["ZRotationAngle"])[1]
        )
        assert new_fcs.props["XOffset"] == fcs.props["XOffset"]
        assert new_fcs.props["YOffset"] == fcs.props["YOffset"]
        assert new_fcs.props["AutoAxis"] == fcs.props["AutoAxis"]
        fcs = self.aedtapp.modeler.create_face_coordinate_system(face, face, face.edges[1].vertices[0])
        new_fcs = self.aedtapp.modeler.duplicate_coordinate_system_to_global(fcs)
        assert new_fcs
        assert new_fcs.props["Origin"] == fcs.props["Origin"]
        assert new_fcs.props["AxisPosn"] == fcs.props["AxisPosn"]
        assert new_fcs.props["MoveToEnd"] == fcs.props["MoveToEnd"]
        assert new_fcs.props["FaceID"] == fcs.props["FaceID"]
        assert new_fcs.props["WhichAxis"] == fcs.props["WhichAxis"]
        assert int(decompose_variable_value(new_fcs.props["ZRotationAngle"])[0]) == int(
            decompose_variable_value(fcs.props["ZRotationAngle"])[0]
        )
        assert (
            decompose_variable_value(new_fcs.props["ZRotationAngle"])[1]
            == decompose_variable_value(fcs.props["ZRotationAngle"])[1]
        )
        assert new_fcs.props["XOffset"] == fcs.props["XOffset"]
        assert new_fcs.props["YOffset"] == fcs.props["YOffset"]
        assert new_fcs.props["AutoAxis"] == fcs.props["AutoAxis"]
        fcs = self.aedtapp.modeler.create_face_coordinate_system(face, face.edges[1].vertices[0], face.edges[1])
        new_fcs = self.aedtapp.modeler.duplicate_coordinate_system_to_global(fcs)
        assert new_fcs
        assert new_fcs.props["Origin"] == fcs.props["Origin"]
        assert new_fcs.props["AxisPosn"] == fcs.props["AxisPosn"]
        assert new_fcs.props["MoveToEnd"] == fcs.props["MoveToEnd"]
        assert new_fcs.props["FaceID"] == fcs.props["FaceID"]
        assert new_fcs.props["WhichAxis"] == fcs.props["WhichAxis"]
        assert int(decompose_variable_value(new_fcs.props["ZRotationAngle"])[0]) == int(
            decompose_variable_value(fcs.props["ZRotationAngle"])[0]
        )
        assert (
            decompose_variable_value(new_fcs.props["ZRotationAngle"])[1]
            == decompose_variable_value(fcs.props["ZRotationAngle"])[1]
        )
        assert new_fcs.props["XOffset"] == fcs.props["XOffset"]
        assert new_fcs.props["YOffset"] == fcs.props["YOffset"]
        assert new_fcs.props["AutoAxis"] == fcs.props["AutoAxis"]
        obj_cs = self.aedtapp.modeler.create_object_coordinate_system(
            assignment=box, origin=box.faces[0], x_axis=box.edges[0], y_axis=[0, 0, 0], name="obj_cs"
        )
        new_obj_cs = self.aedtapp.modeler.duplicate_coordinate_system_to_global(obj_cs)
        assert new_obj_cs.props == obj_cs.props
        assert new_obj_cs.entity_id == obj_cs.entity_id
        obj_cs.delete()
        obj_cs = self.aedtapp.modeler.create_object_coordinate_system(
            assignment=box.name, origin=box.edges[0], x_axis=[1, 0, 0], y_axis=[0, 1, 0], name="obj_cs"
        )
        new_obj_cs = self.aedtapp.modeler.duplicate_coordinate_system_to_global(obj_cs)
        assert new_obj_cs.props == obj_cs.props
        assert new_obj_cs.entity_id == obj_cs.entity_id
        obj_cs.delete()
        obj_cs = self.aedtapp.modeler.create_object_coordinate_system(
            assignment=box.name, origin=[0, 0.8, 0], x_axis=[1, 0, 0], y_axis=[0, 1, 0], name="obj_cs"
        )
        new_obj_cs = self.aedtapp.modeler.duplicate_coordinate_system_to_global(obj_cs)
        assert new_obj_cs.props == obj_cs.props
        assert new_obj_cs.entity_id == obj_cs.entity_id
        obj_cs.delete()
        obj_cs = self.aedtapp.modeler.create_object_coordinate_system(
            assignment=box.name, origin=box.vertices[1], x_axis=box.faces[2], y_axis=box.faces[4], name="obj_cs"
        )
        new_obj_cs = self.aedtapp.modeler.duplicate_coordinate_system_to_global(obj_cs)
        assert new_obj_cs.props == obj_cs.props
        assert new_obj_cs.entity_id == obj_cs.entity_id

    def test_58_invert_cs(self):
        self.aedtapp.modeler.create_coordinate_system(
            origin=[-1, -2.6, 1],
            name="CS_Test5",
            x_pointing=[-0.70710678118655, -0.70710678118655, 0],
            y_pointing=[-0.70710678118655, 0.70710678118655, 0],
        )
        cs6 = self.aedtapp.modeler.create_coordinate_system(
            origin=[-5.4, 1.4, -8],
            name="CS_Test6",
            reference_cs="CS_Test5",
            x_pointing=[0.83205029433784, 0.55470019622523, 0],
            y_pointing=[-0.55470019622523, 0.83205029433784, 0],
        )
        o, q = self.aedtapp.modeler.invert_cs("CS_Test6", to_global=False)
        res = o + q
        sol = [3.716491314709036, -4.160251471689218, 8.0, 0.9570920264890529, -0.0, -0.0, -0.28978414868843005]
        assert all(abs(res[i] - sol[i]) < 10 * small_number for i in range(3))
        o, q = self.aedtapp.modeler.invert_cs("CS_Test6", to_global=True)
        res = o + q
        sol = [2.2260086876588385, -1.8068578500310104, 9.0, 0, 0.09853761796664223, -0.9951333266680702, 0]
        assert all(abs(res[i] - sol[i]) < 10 * small_number for i in range(3))
        assert self.aedtapp.modeler.invert_cs(cs6, to_global=True)

    def test_59a_region_property(self):
        self.aedtapp.modeler.create_air_region()
        cs_name = "TestCS"
        self.aedtapp.modeler.create_coordinate_system(
            origin=[1, 1, 1], name=cs_name, mode="zxz", phi=10, theta=30, psi=50
        )
        assert self.aedtapp.modeler.change_region_coordinate_system(assignment=cs_name)
        assert self.aedtapp.modeler.change_region_padding("10mm", padding_type="Absolute Offset", direction="-X")
        assert self.aedtapp.modeler.change_region_padding(
            ["1mm", "-2mm", "3mm", "-4mm", "5mm", "-6mm"],
            padding_type=[
                "Absolute Position",
                "Absolute Position",
                "Absolute Position",
                "Absolute Position",
                "Absolute Position",
                "Absolute Position",
            ],
        )

    def test_59b_region_property_failing(self):
        self.aedtapp.modeler.create_air_region()
        assert not self.aedtapp.modeler.change_region_coordinate_system(assignment="NoCS")
        assert not self.aedtapp.modeler.change_region_padding(
            "10mm", padding_type="Absolute Offset", direction="-X", region_name="NoRegion"
        )
        with pytest.raises(Exception, match="Check ``axes`` input."):
            self.aedtapp.modeler.change_region_padding("10mm", padding_type="Absolute Offset", direction="X")
        with pytest.raises(Exception, match="Check ``padding_type`` input."):
            self.aedtapp.modeler.change_region_padding("10mm", padding_type="Partial Offset", direction="+X")
        assert not self.aedtapp.modeler.change_region_padding(
            ["1mm", "-2mm", "3mm", "-4mm", "5mm", "-6mm"],
            padding_type=[
                "Absolute Position",
                "Percentage Offset",
                "Absolute Position",
                "Absolute Position",
                "Absolute Position",
                "Absolute Position",
            ],
        )

    def test_60_sweep_along_normal(self):
        selected_faces = [face for face in self.aedtapp.modeler["Core"].faces if face.is_planar]
        selected_faces = [selected_faces[0].id, selected_faces[1].id]
        a = self.aedtapp.modeler.sweep_along_normal("Core", selected_faces, sweep_value=100)
        b = self.aedtapp.modeler.sweep_along_normal("Core", selected_faces[0], sweep_value=200)
        assert isinstance(a, list)
        assert isinstance(b, Object3d)

    def test_61_get_face_by_id(self):
        self.aedtapp.insert_design("face_id_object")
        box1 = self.aedtapp.modeler.create_box([0, 0, 0], [10, 10, 10])
        face = self.aedtapp.modeler.get_face_by_id(box1.faces[0].id)
        assert isinstance(face, FacePrimitive)
        face = self.aedtapp.modeler.get_face_by_id(secure_random.randint(10000, 100000))
        assert not face

    def test_62_copy_solid_bodies_udm_3dcomponent(self, add_app):
        self.aedtapp.insert_design("udm")
        my_udmPairs = []
        mypair = ["ILD Thickness (ILD)", "0.006mm"]
        my_udmPairs.append(mypair)
        mypair = ["Line Spacing (LS)", "0.004mm"]
        my_udmPairs.append(mypair)
        mypair = ["Line Thickness (LT)", "0.005mm"]
        my_udmPairs.append(mypair)
        mypair = ["Line Width (LW)", "0.004mm"]
        my_udmPairs.append(mypair)
        mypair = ["No. of Turns (N)", 2]
        my_udmPairs.append(mypair)
        mypair = ["Outer Diameter (OD)", "0.15mm"]
        my_udmPairs.append(mypair)
        mypair = ["Substrate Thickness", "0.2mm"]
        my_udmPairs.append(mypair)
        mypair = [
            "Inductor Type",
            '"Square,Square,Octagonal,Circular,Square-Differential,Octagonal-Differential,Circular-Differential"',
        ]
        my_udmPairs.append(mypair)
        mypair = ["Underpass Thickness (UT)", "0.001mm"]
        my_udmPairs.append(mypair)
        mypair = ["Via Thickness (VT)", "0.001mm"]
        my_udmPairs.append(mypair)

        obj_udm = self.aedtapp.modeler.create_udm(
            udm_full_name="Maxwell3D/OnDieSpiralInductor.py", parameters=my_udmPairs, library="syslib"
        )
        assert len(obj_udm.parts) == 5
        names = [p.name for p in obj_udm.parts.values()]
        assert "Inductor" in names
        assert "Substrate" in names
        compfile = self.aedtapp.components3d["Bowtie_DM"]
        obj_3dcomp = self.aedtapp.modeler.insert_3d_component(compfile)
        assert len(obj_3dcomp.parts) == 4
        dest = add_app(design_name="IcepakDesign1", just_open=True)
        dest.copy_solid_bodies_from(self.aedtapp, [obj_udm.name, obj_3dcomp.name])
        assert len(dest.modeler.object_list) == 9
        assert "Arm" in dest.modeler.object_names
        dest.delete_design("IcepakDesign1")
        dest = add_app(design_name="IcepakDesign2", just_open=True)
        dest.copy_solid_bodies_from(self.aedtapp)
        dest2 = add_app(design_name="uUSB")
        dest2.copy_solid_bodies_from(self.aedtapp, [obj_udm.name, obj_3dcomp.name])
        assert len(dest2.modeler.objects) == 9
        assert "port1" in dest2.modeler.object_names

    def test_63_create_conical_rings(self, add_app):
        self.aedtapp.insert_design("rings")
        position = self.aedtapp.modeler.Position(0, 0, 0)
        rings1 = self.aedtapp.modeler.create_conical_rings("Z", position, 20, 10, 20, 1)
        assert isinstance(rings1, list)
        rings2 = self.aedtapp.modeler.create_conical_rings("X", position, 20, 10, 20, 1)
        assert isinstance(rings2, list)
        rings3 = self.aedtapp.modeler.create_conical_rings("Y", position, 20, 10, 20, 1)
        assert isinstance(rings3, list)
        assert not self.aedtapp.modeler.create_conical_rings("Y", position, 10, 20, 20, 1)
        assert not self.aedtapp.modeler.create_conical_rings("Z", position, -20, 10, 20, 1)
        assert not self.aedtapp.modeler.create_conical_rings("Z", position, 20, -10, 20, 1)
        assert not self.aedtapp.modeler.create_conical_rings("Z", position, 20, 10, 0, 1)
        assert not self.aedtapp.modeler.create_conical_rings("Z", position, 20, 10, 20, 0)
        assert not self.aedtapp.modeler.create_conical_rings("Z", [0], 20, 10, 20, 0)

    def test_get_group_bounding_box_with_non_existing_group_name(self):
        assert self.aedtapp.modeler.get_group_bounding_box("SomeUnknownGroupName") is None

    def test_get_group_bounding_box_with_wrong_input_type(self):
        with pytest.raises(ValueError):
            self.aedtapp.modeler.get_group_bounding_box(5)

    def test_get_group_bounding_box_with_existing_group_name(self):
        assert self.aedtapp.modeler.get_group_bounding_box("Sheets") is not None

    def test_chassis_subtraction(self):
        self.restore_model()
        chassis = self.aedtapp.modeler.create_box([0, 0, 0], [10, 10, 5], "chassis", "Copper")
        # Add vacuum to extend code coverage
        self.aedtapp.modeler.create_box([20, 20, 20], [1, 1, 1], "box", "Vacuum")
        assert self.aedtapp.modeler.chassis_subtraction(chassis.name)

    def test_explicitly_subtract(self):
        box_0 = self.aedtapp.modeler.create_box([0, 0, 0], [10, 10, 5], "box_0", "Copper")
        box_1 = self.aedtapp.modeler.create_box([0, 0, 0], [5, 5, 5], "box_1", "Copper")
        box_2 = self.aedtapp.modeler.create_box([0, 0, 0], [6, 6, 6], "box_2", "Copper")
        box_3 = self.aedtapp.modeler.create_box([0, 0, 0], [7, 7, 7], "box_3", "Copper")
        assert self.aedtapp.modeler.explicitly_subtract([box_0.name, box_1.name], [box_2.name, box_3.name])

    def test_clean_objects_name(self):
        box_0 = self.aedtapp.modeler.create_box([0, 0, 0], [10, 10, 10], name="Object_Part0")
        box_1 = self.aedtapp.modeler.create_box([5, 5, 0], [1, 1, 1], name="Object_Part1")
        self.aedtapp.modeler.unite([box_0, box_1], keep_originals=True)
        self.aedtapp.modeler.clean_objects_name("Object")

        assert self.aedtapp.modeler.get_matched_object_name("Part0")
        assert self.aedtapp.modeler.get_matched_object_name("Part1")
