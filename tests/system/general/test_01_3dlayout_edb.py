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

import os

from ansys.aedt.core import Hfss3dLayout
from ansys.aedt.core.generic.settings import is_linux
from ansys.aedt.core.modeler.pcb.object_3d_layout import Components3DLayout
import pytest

from tests import TESTS_GENERAL_PATH
from tests.system.general.conftest import config

test_subfolder = "T40"
original_project_name = "ANSYS-HSD_V1"


@pytest.fixture()
def aedtapp(add_app):
    app = add_app(project_name=original_project_name, application=Hfss3dLayout, subfolder=test_subfolder)
    yield app
    app.close_project(app.project_name)


@pytest.fixture()
def flipchip(add_app):
    app = add_app(
        project_name="Package", design_name="FlipChip_TopBot", application=Hfss3dLayout, subfolder=test_subfolder
    )
    yield app
    app.close_project(app.project_name)


@pytest.fixture()
def dcir_example_project(add_app):
    app = add_app(project_name="ANSYS-HSD_V1_dcir", application=Hfss3dLayout, subfolder=test_subfolder)
    yield app
    app.close_project(app.project_name)


@pytest.fixture()
def ic_mode_design(add_app):
    app = add_app(project_name="ic_mode_design", application=Hfss3dLayout, subfolder=test_subfolder)
    yield app
    app.close_project(app.project_name)


class TestClass:
    def test_01_get_components(self, aedtapp):
        comp = aedtapp.modeler.components
        assert len(comp) > 0
        assert comp["L10"].object_units == "mm"
        assert comp["L10"].angle == "4.71238898038469"
        comp["L10"].angle = "90deg"
        assert comp["L10"].angle == "90deg"
        comp["L10"].angle = "4.71238898038469"
        assert comp["L10"].location[0] == 105.99999882
        assert comp["L10"].location[1] == 44.0000009
        comp["L10"].location = [1.0, 0.0]
        assert comp["L10"].location[0] == 1.0  # bug in component location
        comp["L10"].location = [105.99999882, 44.0000009]
        assert comp["L10"].placement_layer == "1_Top"
        assert comp["L10"].part == "WE-Coil-PD4-S"
        assert comp["L10"].part_type == "Inductor"
        assert comp["L10"].set_property_value("Angle", "0deg")
        assert comp["L10"].create_clearance_on_component(1e-6)
        assert comp["L10"].absolute_angle == 0.0
        comp["L10"].enabled = False
        assert not comp["L10"].enabled
        comp["L10"].enabled = True
        assert comp["L10"].enabled
        comp["R13"].enabled = False
        assert not comp["R13"].enabled
        comp["R13"].enabled = True
        assert comp["R13"].enabled
        comp["C10"].enabled = False
        assert not comp["C10"].enabled
        comp["C10"].enabled = True

        assert comp["U1"].enabled
        assert comp["J1"].enabled

        r5 = comp["R13"]
        assert r5.model
        assert r5.model.res == "3.57kOhm"
        assert r5.model.cap == "0"
        assert r5.model.ind == "0"
        assert r5.model.is_parallel == False

    def test_02a_get_geometries(self, aedtapp):
        line = aedtapp.modeler.geometries["line_209"]
        assert line.edges
        assert isinstance(line.edge_by_point([0, 0]), int)
        assert line.points
        assert line.points
        assert line.is_closed
        poly = aedtapp.modeler.geometries["poly_1872"]
        assert poly.edges
        assert poly.points
        assert poly.bottom_edge_x == 0
        assert poly.bottom_edge_y == 1
        assert poly.top_edge_x == 2
        assert poly.top_edge_y == 3
        assert poly.placement_layer == "1_Top"
        assert poly.obounding_box
        poly.placement_layer = "16_Bottom"
        assert poly.placement_layer == "16_Bottom"
        poly.placement_layer = "1_Top"
        assert poly.net_name == "----"
        assert not poly.negative
        assert not poly.is_void
        assert not poly.lock_position
        assert poly.is_closed
        assert len(aedtapp.modeler.geometries) > 0
        rect = aedtapp.modeler.rectangles["rect_5951"]
        assert rect.point_a
        assert rect.point_b
        assert rect.two_point_description
        assert not rect.center
        rect.two_point_description = False
        assert rect.center
        assert rect.height
        rect.two_point_description = True
        assert rect.point_a
        circle = aedtapp.modeler.circles["circle_5952"]
        assert circle.center
        assert circle.radius
        circle.radius = "2.5mm"
        assert circle.radius == "2.5mm"

    def test_02b_geo_units(self, aedtapp):
        assert aedtapp.modeler.geometries["line_209"].object_units == "mm"

    def test_02c_geo_layer(self, aedtapp):
        assert aedtapp.modeler.geometries["line_209"].placement_layer
        assert len(aedtapp.modeler.layers.drawing_layers) > 0
        assert len(aedtapp.modeler.layers.all_signal_layers) > 0
        assert len(aedtapp.modeler.layers.all_diel_layers) > 0
        assert len(aedtapp.modeler.stackup.all_signal_layers) == len(aedtapp.modeler.stackup.signals)
        assert len(aedtapp.modeler.stackup.all_diel_layers) == len(aedtapp.modeler.stackup.dielectrics)
        assert len(aedtapp.modeler.stackup.stackup_layers) == len(aedtapp.modeler.stackup.drawings)
        assert len(aedtapp.modeler.layers.all_signal_layers) + len(aedtapp.modeler.layers.all_diel_layers) == len(
            aedtapp.modeler.layers.stackup_layers
        )
        assert isinstance(aedtapp.modeler.layers.all_signal_layers[0].name, str)
        assert isinstance(aedtapp.modeler.layers.all_diel_layers[0].name, str)

    def test_02d_geo_lock(self, aedtapp):
        aedtapp.modeler.geometries["line_209"].lock_position = True
        assert aedtapp.modeler.geometries["line_209"].lock_position == True
        aedtapp.modeler.geometries["line_209"].lock_position = False
        assert aedtapp.modeler.geometries["line_209"].lock_position == False

    def test_02e_geo_setter(self, aedtapp):
        aedtapp.modeler.geometries["line_209"].layer = "PWR"
        assert aedtapp.modeler.geometries["line_209"].layer == "PWR"
        aedtapp.modeler.geometries["line_209"].net_name = "VCC"
        assert aedtapp.modeler.geometries["line_209"].net_name == "VCC"

    def test_03_get_pins(self, aedtapp):
        pins = aedtapp.modeler.pins
        assert len(pins) > 0
        assert pins["L10-1"].object_units == "mm"
        assert pins["L10-1"].componentname == "L10"
        assert pins["L10-1"].is_pin
        assert pins["L10-1"].angle == "0deg"
        assert pins["L10-1"].location[0] != 0
        assert pins["L10-1"].start_layer == "1_Top"
        assert pins["L10-1"].stop_layer == "1_Top"

    def test_03B_get_vias(self, aedtapp):
        vias = aedtapp.modeler.vias
        assert len(vias) > 0
        assert vias["Via1920"].object_units == "mm"
        assert not vias["Via1920"].is_pin
        assert vias["Via1920"].angle == "0deg"
        assert vias["Via1920"].location[0] > 0
        assert vias["Via1920"].start_layer == "1_Top"
        assert vias["Via1920"].stop_layer == "16_Bottom"
        assert vias["Via1920"].holediam == "0.1499997mm"

    def test_03C_voids(self, aedtapp):
        assert len(aedtapp.modeler.voids) > 0
        poly = aedtapp.modeler.polygons["poly_2084"]
        assert len(poly.polygon_voids) > 0

    def test_04_add_mesh_operations(self, aedtapp):
        aedtapp.create_setup("HFSS")
        setup1 = aedtapp.mesh.assign_length_mesh("HFSS", "PWR", "GND")
        setup2 = aedtapp.mesh.assign_skin_depth("HFSS", "PWR", "GND")
        assert setup1
        assert setup2
        setup1.props["RestrictElem"] = False
        assert setup1.update()
        assert aedtapp.mesh.delete_mesh_operations(
            "HFSS",
            setup1.name,
        )

    def test_05_change_property(self, aedtapp):
        ports = aedtapp.create_ports_on_component_by_nets("U1", "DDR4_DQS0_P")
        assert aedtapp.modeler.change_property(f"Excitations:{ports[0].name}", "Impedance", "49ohm", "EM Design")

    def test_06_assign_touchstone_model(self, aedtapp):
        model_path = os.path.join(TESTS_GENERAL_PATH, "example_models", "TEDB", "GRM32_DC0V_25degC_series.s2p")
        assert aedtapp.modeler.set_touchstone_model(assignment="C217", input_file=model_path, model_name="Test1")

    def test_07_assign_spice_model(self, aedtapp):
        model_path = os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, "GRM32ER72A225KA35_25C_0V.sp")
        assert aedtapp.modeler.set_spice_model(
            assignment="C1", input_file=model_path, subcircuit_name="GRM32ER72A225KA35_25C_0V"
        )

    def test_07_nets(self, aedtapp, local_scratch):
        nets = aedtapp.modeler.nets
        assert nets["GND"].name == "GND"
        assert len(nets) > 0
        assert len(nets["GND"].components) > 0
        local_png1 = os.path.join(local_scratch.path, "test1.png")
        nets["AVCC_1V3"].plot(save_plot=local_png1, show=False)
        assert os.path.exists(local_png1)

    def test_07a_nets_count(self, aedtapp):
        nets = aedtapp.modeler.nets
        power_nets = aedtapp.modeler.power_nets
        signal_nets = aedtapp.modeler.signal_nets
        no_nets = aedtapp.modeler.no_nets
        assert len(nets) == len(power_nets) + len(signal_nets) + len(no_nets)

    def test_08_merge(self, flipchip):
        tol = 1e-12
        brd = Hfss3dLayout(project=flipchip.project_name, design="Dummy_Board")
        comp = brd.modeler.merge_design(flipchip, rotation=90)
        assert comp.location[0] == 0.0
        assert comp.rotation_axis == "Z"
        comp.rotation_axis = "X"
        assert comp.rotation_axis == "X"
        comp.rotation_axis = "Z"
        comp.rotation_axis_direction = [0, 0, 1.2]
        assert comp.rotation_axis_direction == [0, 0, 1.2]
        assert not comp.is_flipped
        comp.is_flipped = True
        assert comp.is_flipped
        comp.is_flipped = False
        assert comp.location[0] == 0.0
        assert comp.location[1] == 0.0
        assert comp.angle == "90deg"
        comp.location = [0.1, 0.2]
        if config["desktopVersion"] > "2022.2":
            assert (comp.location[0] - 100.0) < tol
            assert (comp.location[1] - 200.0) < tol
        else:
            assert (comp.location[0] - 0.1) < tol
            assert (comp.location[1] - 0.2) < tol

    def test_10_change_stackup(self, aedtapp):
        if config["NonGraphical"]:
            assert aedtapp.modeler.layers.change_stackup_type("Multizone", 4)
            assert len(aedtapp.modeler.layers.zones) == 3
        assert aedtapp.modeler.layers.change_stackup_type("Overlap")
        assert aedtapp.modeler.layers.change_stackup_type("Laminate")
        assert not aedtapp.modeler.layers.change_stackup_type("lami")

    @pytest.mark.skipif(config["NonGraphical"], reason="Not running in non-graphical mode")
    def test_11_export_picture(self, aedtapp):
        assert os.path.exists(aedtapp.post.export_model_picture(orientation="top"))

    def test_12_objects_by_net(self, aedtapp):
        poly_on_gnd = aedtapp.modeler.objects_by_net("GND", "poly")
        assert len(poly_on_gnd) > 0
        assert aedtapp.modeler.geometries[poly_on_gnd[0]].net_name == "GND"

    def test_13_objects_by_layer(self, aedtapp):
        lines_on_top = aedtapp.modeler.objects_by_layer("1_Top", "line")
        assert len(lines_on_top) > 0
        assert aedtapp.modeler.geometries[lines_on_top[0]].placement_layer == "1_Top"

    def test_14_set_solderball(self, aedtapp):
        assert not aedtapp.modeler.components["U1"].die_enabled
        assert not aedtapp.modeler.components["U1"].die_type
        assert aedtapp.modeler.components["U1"].set_die_type()
        assert aedtapp.modeler.components["U1"].set_solderball("Cyl")
        assert aedtapp.modeler.components["U1"].solderball_enabled
        assert aedtapp.modeler.components["U1"].set_solderball(None)
        assert not aedtapp.modeler.components["U1"].solderball_enabled
        assert not aedtapp.modeler.components["L10"].set_solderball(None)
        assert aedtapp.modeler.components["J1"].set_solderball("Sph")

    def test_15_3dplacement(self, aedtapp):
        aedtapp.insert_design("placement_3d")
        l1 = aedtapp.modeler.layers.add_layer("BOTTOM", "signal")
        aedtapp.modeler.layers.add_layer("diel", "dielectric")
        aedtapp.modeler.layers.add_layer("TOP", "signal")
        tol = 1e-12
        encrypted_model_path = os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, "SMA_RF_Jack.a3dcomp")
        comp = aedtapp.modeler.place_3d_component(
            encrypted_model_path, 1, placement_layer="TOP", component_name="my_connector", pos_x=0.001, pos_y=0.002
        )
        assert (comp.location[0] - 1.017) < tol
        assert (comp.location[1] - 2) < tol
        assert comp.angle == "0deg"
        assert comp.placement_layer == "TOP"
        comp.placement_layer = "bottom"
        assert comp.placement_layer == "BOTTOM"
        comp.angle = "10deg"
        assert comp.angle == "10deg"
        assert comp.component_name == "my_connector"
        assert len(aedtapp.modeler.components_3d) == 1
        comp2 = aedtapp.modeler.place_3d_component(
            encrypted_model_path, 1, component_name="my_connector2", pos_x=0.001, pos_y=0.002, pos_z=1
        )
        assert comp2.location[2] == 1.0

    def test_16_differential_ports(self, aedtapp):
        pins = list(aedtapp.modeler.components["R3"].pins.keys())
        assert aedtapp.create_differential_port(pins[0], pins[1], "test_differential", deembed=True)
        assert "test_differential" in aedtapp.port_list

    def test_17_ports_on_components_nets(self, aedtapp):
        component = aedtapp.modeler.components["J1"]
        nets = [
            aedtapp.modeler.pins[i].net_name
            for i in component.pins
            if "GND" not in aedtapp.modeler.pins[i].net_name and aedtapp.modeler.pins[i].net_name != ""
        ]
        ports_before = len(aedtapp.port_list)
        ports = aedtapp.create_ports_on_component_by_nets("J1", nets)
        assert ports
        ports_after = len(aedtapp.port_list)
        assert ports_after - ports_before == len(nets)
        ports[0].name = "port_test"
        assert ports[0].name == "port_test"
        assert ports[0].props["Port"] == "port_test"
        ports[0].props["Port"] = "port_test2"
        assert ports[0].name == "port_test2"

    def test_18_set_variable(self, aedtapp):
        aedtapp.variable_manager.set_variable("var_test", expression="123")
        aedtapp["var_test"] = "234"
        assert "var_test" in aedtapp.variable_manager.design_variable_names
        assert aedtapp.variable_manager.design_variables["var_test"].expression == "234"

    @pytest.mark.skipif(is_linux, reason="Not Supported on Linux.")
    def test_19_dcir(self, dcir_example_project):
        import pandas as pd

        setup = dcir_example_project.get_setup("SIwaveDCIR1")
        assert setup.is_solved
        assert dcir_example_project.get_dcir_solution_data("SIwaveDCIR1", "RL", "Path Resistance")
        assert dcir_example_project.get_dcir_solution_data("SIwaveDCIR1", "Vias", "Current")
        solution_data = dcir_example_project.get_dcir_solution_data("SIwaveDCIR1", "Sources", "Voltage")
        assert dcir_example_project.post.available_report_quantities(is_siwave_dc=True, context="")
        assert dcir_example_project.post.create_report(
            dcir_example_project.post.available_report_quantities(is_siwave_dc=True, context="Vias")[0],
            domain="DCIR",
            context="RL",
        )
        assert isinstance(dcir_example_project.get_dcir_element_data_current_source("SIwaveDCIR1"), pd.DataFrame)
        assert dcir_example_project.post.compute_power_by_layer()
        assert dcir_example_project.post.compute_power_by_layer(layers=["1_Top"])
        assert dcir_example_project.post.compute_power_by_net()
        assert dcir_example_project.post.compute_power_by_net(nets=["5V", "GND"])
        assert dcir_example_project.post.compute_power_by_layer(solution="SIwaveDCIR1")

    def test_20_change_options(self, aedtapp):
        assert aedtapp.change_options()
        assert aedtapp.change_options(color_by_net=False)
        assert not aedtapp.change_options(color_by_net=None)

    def test_21_show_extent(self, aedtapp):
        assert aedtapp.show_extent()
        assert aedtapp.show_extent(show=False)
        assert not aedtapp.show_extent(show=None)

    def test_22_change_design_settings(self, aedtapp):
        assert aedtapp.get_oo_property_value(aedtapp.odesign, "Design Settings", "DCExtrapolation") == "Standard"
        assert aedtapp.change_design_settings({"UseAdvancedDCExtrap": True})
        assert aedtapp.get_oo_property_value(aedtapp.odesign, "Design Settings", "DCExtrapolation") == "Advanced"

    def test_23_dissolve_element(self, aedtapp):
        comp = aedtapp.modeler.components["D1"]
        pins = {name: pin for name, pin in comp.pins.items() if name in ["D1-1", "D1-2", "D1-7"]}
        aedtapp.dissolve_component("D1")
        comp = aedtapp.modeler.create_component_on_pins(list(pins.keys()))
        nets = [
            list(pins.values())[0].net_name,
            list(pins.values())[1].net_name,
        ]
        assert aedtapp.create_ports_on_component_by_nets(comp.name, nets)
        assert aedtapp.create_pec_on_component_by_nets(comp.name, "GND")

    @pytest.mark.skipif(config["desktopVersion"] <= "2024.1", reason="Introduced in 2024R1")
    def test_24_open_ic_mode_design(self, ic_mode_design):
        assert ic_mode_design.ic_mode

    def test_25a_set_port_properties(self, aedtapp):
        component: Components3DLayout = aedtapp.modeler.components["Q1"]
        assert component.port_properties == ("0", True, "0", "0")
        new_values = ("10um", False, "0um", "0um")
        component.port_properties = new_values
        assert component.port_properties == new_values

    def test_25b_set_port_properties_on_ic_component(self, aedtapp):
        component: Components3DLayout = aedtapp.modeler.components["U10"]
        original_die_properties = component.die_properties
        assert component.port_properties == ("0", True, "0", "0")
        new_values = ("10um", False, "0um", "0um")
        component.port_properties = new_values
        assert component.port_properties == new_values
        assert component.die_properties == original_die_properties

    def test_25c_get_properties_on_rlc_component(self, aedtapp):
        component: Components3DLayout = aedtapp.modeler.components["C1"]
        assert component.die_properties is None
        assert component.port_properties is None

    def test_25d_set_port_properties_on_rlc_component(self, aedtapp):
        component: Components3DLayout = aedtapp.modeler.components["C1"]
        component.port_properties = ("10um", False, "0um", "0um")
        assert component.port_properties is None

    def test_26_import_table(self, aedtapp):
        aedtapp.insert_design("import_table")
        file_header = os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, "table_header.csv")
        file_invented = "invented.csv"

        assert not aedtapp.import_table(file_header, column_separator="dummy")
        assert not aedtapp.import_table(file_invented)

        table = aedtapp.import_table(file_header)
        assert table in aedtapp.existing_analysis_sweeps

        assert not aedtapp.delete_imported_data("invented")

        assert aedtapp.delete_imported_data(table)
        assert table not in aedtapp.existing_analysis_sweeps

    def test_27_value_with_units(self, aedtapp):
        assert aedtapp.value_with_units("10mm") == "10mm"
        assert aedtapp.value_with_units("10") == "10mm"
