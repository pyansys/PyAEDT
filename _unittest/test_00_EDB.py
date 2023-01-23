import os

from pyaedt import Edb
from pyaedt.edb_core.components import resistor_value_parser
from pyaedt.edb_core.edb_data.simulation_configuration import SimulationConfiguration
from pyaedt.edb_core.edb_data.sources import Source
from pyaedt.generic.constants import RadiationBoxType

# Setup paths for module imports
# Import required modules

test_project_name = "Galileo_edb"
bom_example = "bom_example.csv"
from _unittest.conftest import BasisTest
from _unittest.conftest import config
from _unittest.conftest import desktop_version
from _unittest.conftest import is_ironpython
from _unittest.conftest import local_path
from _unittest.conftest import settings
from pyaedt.generic.constants import SolverType
from pyaedt.generic.constants import SourceType

try:
    import pytest
except ImportError:  # pragma: no cover
    import _unittest_ironpython.conf_unittest as pytest

test_subfolder = "TEDB"


if not config["skip_edb"]:

    class TestClass(BasisTest, object):
        def setup_class(self):
            BasisTest.my_setup(self)
            self.edbapp = BasisTest.add_edb(self, test_project_name, subfolder=test_subfolder)
            example_project = os.path.join(local_path, "example_models", test_subfolder, "example_package.aedb")
            self.target_path = os.path.join(self.local_scratch.path, "example_package.aedb")
            self.local_scratch.copyfolder(example_project, self.target_path)
            example_project2 = os.path.join(local_path, "example_models", test_subfolder, "simple.aedb")
            self.target_path2 = os.path.join(self.local_scratch.path, "simple_00.aedb")
            self.local_scratch.copyfolder(example_project2, self.target_path2)
            example_project3 = os.path.join(local_path, "example_models", test_subfolder, "Galileo_edb_plot.aedb")
            self.target_path3 = os.path.join(self.local_scratch.path, "Galileo_edb_plot_00.aedb")
            self.local_scratch.copyfolder(example_project3, self.target_path3)
            example_project4 = os.path.join(local_path, "example_models", test_subfolder, "Package.aedb")
            self.target_path4 = os.path.join(self.local_scratch.path, "Package_00.aedb")
            self.local_scratch.copyfolder(example_project4, self.target_path4)

        def teardown_class(self):
            self.edbapp.close_edb()
            self.local_scratch.remove()
            del self.edbapp

        @pytest.mark.skipif(is_ironpython, reason="Method not supported anymore in Ironpython")
        def test_000_export_ipc2581(self):
            ipc_path = os.path.join(self.local_scratch.path, "test.xml")
            self.edbapp.export_to_ipc2581(ipc_path)
            assert os.path.exists(ipc_path)

            # Export should be made with units set to default -millimeter-.
            self.edbapp.export_to_ipc2581(ipc_path, "mm")
            assert os.path.exists(ipc_path)

        def test_001_find_by_name(self):
            comp = self.edbapp.core_components.get_component_by_name("J1")
            assert comp is not None
            pin = self.edbapp.core_components.get_pin_from_component("J1", pinName="1")
            assert pin is not False
            parameters = self.edbapp.core_padstack.get_pad_parameters(
                pin[0], "TOP", self.edbapp.core_padstack.pad_type.RegularPad
            )
            assert isinstance(parameters[1], list)
            assert isinstance(parameters[0], int)

        def test_002_get_vias_from_nets(self):
            assert self.edbapp.core_padstack.get_via_instance_from_net("GND")
            assert not self.edbapp.core_padstack.get_via_instance_from_net(["GND2"])

        def test_003_create_coax_port_on_component(self):
            assert self.edbapp.core_hfss.create_coax_port_on_component("U1A1", "M_DQ<14>")

        def test_004_get_properties(self):
            assert len(self.edbapp.core_components.components) > 0
            assert len(self.edbapp.core_components.inductors) > 0
            assert len(self.edbapp.core_components.resistors) > 0
            assert len(self.edbapp.core_components.capacitors) > 0
            assert len(self.edbapp.core_components.ICs) > 0
            assert len(self.edbapp.core_components.IOs) > 0
            assert len(self.edbapp.core_components.Others) > 0
            assert len(self.edbapp.get_bounding_box()) == 2

        def test_005_get_primitives(self):
            assert len(self.edbapp.core_primitives.polygons) > 0
            assert len(self.edbapp.core_primitives.paths) > 0
            assert len(self.edbapp.core_primitives.rectangles) > 0
            assert len(self.edbapp.core_primitives.circles) > 0
            assert len(self.edbapp.core_primitives.bondwires) == 0
            assert "TOP" in self.edbapp.core_primitives.polygons_by_layer.keys()
            assert len(self.edbapp.core_primitives.polygons_by_layer["TOP"]) > 0
            assert len(self.edbapp.core_primitives.polygons_by_layer["UNNAMED_000"]) == 0
            assert self.edbapp.core_primitives.polygons[0].is_void == self.edbapp.core_primitives.polygons[0].IsVoid()
            poly0 = self.edbapp.core_primitives.polygons[0]
            assert self.edbapp.core_primitives.polygons[0].clone()
            poly1 = self.edbapp.core_primitives.polygons[0]
            assert isinstance(poly0.voids, list)
            assert isinstance(poly0.points_raw(), list)
            assert isinstance(poly0.points(), tuple)
            assert isinstance(poly0.points()[0], list)
            assert poly0.points()[0][0] >= 0.0
            assert poly0.points_raw()[0].X.ToDouble() >= 0.0
            assert poly0.type == "Polygon"
            assert self.edbapp.core_primitives.paths[0].type == "Path"
            assert self.edbapp.core_primitives.paths[0].clone()
            assert self.edbapp.core_primitives.rectangles[0].type == "Rectangle"
            assert self.edbapp.core_primitives.circles[0].type == "Circle"
            assert not poly0.is_arc(poly0.points_raw()[0])
            assert isinstance(poly0.voids, list)
            assert self.edbapp.core_primitives.primitives_by_layer["TOP"][0].layer_name == "TOP"
            assert isinstance(poly0.intersection_type(poly1), int)
            assert poly0.is_intersecting(poly1)
            assert isinstance(poly0.get_closest_point([0, 0]), list)
            assert isinstance(poly0.get_closest_arc_midpoint([0, 0]), list)
            assert isinstance(poly0.arcs, list)
            assert isinstance(poly0.longest_arc.length, float)
            assert isinstance(poly0.shortest_arc.length, float)
            assert not poly0.in_polygon([0, 0])
            assert isinstance(poly0.arcs[0].center, list)
            assert isinstance(poly0.arcs[0].radius, float)
            assert poly0.arcs[0].is_segment
            assert not poly0.arcs[0].is_point
            assert not poly0.arcs[0].is_ccw
            assert isinstance(poly0.arcs[0].points_raw, list)
            assert isinstance(poly0.arcs[0].points, tuple)

        def test_006_get_stackup(self):
            stackup = self.edbapp.core_stackup.stackup_layers
            assert len(stackup.layers) > 2
            assert self.edbapp.core_stackup.stackup_layers["TOP"]._builder
            assert self.edbapp.core_stackup.stackup_layers["TOP"].id
            assert (
                isinstance(self.edbapp.core_stackup.stackup_layers["TOP"].layer_type, int)
                or str(type(self.edbapp.core_stackup.stackup_layers["TOP"].layer_type)) == "<type 'LayerType'>"
            )

        def test_007_get_signal_layers(self):
            signal_layers = self.edbapp.core_stackup.signal_layers
            assert len(list(signal_layers.values()))
            assert self.edbapp.stackup.residual_copper_area_per_layer()

        def test_008_component_lists(self):
            component_list = self.edbapp.core_components.components
            assert len(component_list) > 2

        def test_009_vias_creation(self):
            self.edbapp.core_padstack.create_padstack(padstackname="myVia")
            assert "myVia" in list(self.edbapp.core_padstack.padstacks.keys())
            self.edbapp.core_padstack.create_padstack(padstackname="myVia_bullet", antipad_shape="Bullet")
            assert "myVia_bullet" in list(self.edbapp.core_padstack.padstacks.keys())

            self.edbapp.add_design_variable("via_x", 5e-3)
            self.edbapp.add_design_variable("via_y", 1e-3)

            assert self.edbapp.core_padstack.place_padstack(["via_x", "via_x+via_y"], "myVia")
            assert self.edbapp.core_padstack.place_padstack(["via_x", "via_x+via_y*2"], "myVia_bullet")

            padstack = self.edbapp.core_padstack.place_padstack(["via_x", "via_x+via_y*3"], "myVia", is_pin=True)
            padstack_instance = self.edbapp.core_padstack.padstack_instances[padstack.id]
            assert padstack_instance.is_pin
            assert padstack_instance.position
            if not is_ironpython:
                assert padstack_instance.start_layer in padstack_instance.layer_range_names
                assert padstack_instance.stop_layer in padstack_instance.layer_range_names
            padstack_instance.position = [0.001, 0.002]
            assert padstack_instance.position == [0.001, 0.002]
            assert padstack_instance.parametrize_position()
            assert isinstance(padstack_instance.rotation, float)
            self.edbapp.core_padstack.create_circular_padstack(padstackname="mycircularvia")
            assert "mycircularvia" in list(self.edbapp.core_padstack.padstacks.keys())
            assert not padstack_instance.backdrill_top
            assert not padstack_instance.backdrill_bottom
            assert padstack_instance.delete()
            via = self.edbapp.core_padstack.place_padstack([0, 0], "myVia")
            assert via.set_backdrill_top("LYR_1", 0.5e-3)
            assert via.backdrill_top
            assert via.set_backdrill_bottom("GND", 0.5e-3)
            assert via.backdrill_bottom

        def test_010_nets_query(self):
            signalnets = self.edbapp.core_nets.signal_nets
            powernets = self.edbapp.core_nets.power_nets
            assert len(signalnets) > 2
            assert len(powernets) > 2
            assert powernets["V3P3_S0"].is_power_ground
            assert powernets["V3P3_S0"].IsPowerGround()
            assert len(list(powernets["V3P3_S0"].components.keys())) > 0
            assert len(powernets["V3P3_S0"].primitives) > 0

            assert not signalnets[list(signalnets.keys())[0]].is_power_ground
            assert not signalnets[list(signalnets.keys())[0]].IsPowerGround()
            assert len(list(signalnets[list(signalnets.keys())[0]].primitives)) > 0

            assert self.edbapp.core_nets.find_or_create_net("GND")
            assert self.edbapp.core_nets.find_or_create_net(start_with="gn")
            assert self.edbapp.core_nets.find_or_create_net(start_with="g", end_with="d")
            assert self.edbapp.core_nets.find_or_create_net(end_with="d")
            assert self.edbapp.core_nets.find_or_create_net(contain="usb")

        def test_011_assign_rlc(self):
            assert self.edbapp.core_components.set_component_rlc(
                "C3B14", res_value=1e-3, cap_value="10e-6", isparallel=False
            )
            assert self.edbapp.core_components.set_component_rlc(
                "L3A1", res_value=1e-3, ind_value="10e-6", isparallel=True
            )

        def test_012_add_layer(self):
            layers = self.edbapp.core_stackup.stackup_layers
            assert layers.add_layer("NewLayer", "TOP", "copper", "air", "10um", 0, roughness_enabled=True)
            assert layers.add_layer("NewLayer2", None, "pec", "air", "0um", 0)
            assert layers.add_layer("NewLayer3", None, "copper", "air", "0um", 0, negative_layer=True)
            top = layers.layers["TOP"]
            top.roughness_enabled = True
            assert top.assign_roughness_model_top(huray_radius="1um")
            assert top.assign_roughness_model_bottom(model_type="groisse")
            assert top.assign_roughness_model_side(huray_surface_ratio=5)

        def test_013_add_dielectric(self):
            diel = self.edbapp.core_stackup.create_dielectric("MyDiel", 3.3, 0.02)
            assert diel

        def test_014_add_conductor(self):
            cond = self.edbapp.core_stackup.create_conductor("MyCond", 55e8)
            assert cond

        def test_015_add_djordievic(self):
            diel = self.edbapp.core_stackup.create_djordjevicsarkar_material("MyDjord", 3.3, 0.02, 3.3)
            assert diel

        def test_016_add_debye(self):
            diel = self.edbapp.core_stackup.create_debye_material("My_Debye", 3, 2.5, 0.02, 0.04, 1e6, 1e9)
            assert diel

        def test_017_add_multipole_debye(self):
            freq = [0, 2, 3, 4, 5, 6]
            rel_perm = [1e9, 1.1e9, 1.2e9, 1.3e9, 1.5e9, 1.6e9]
            loss_tan = [0.025, 0.026, 0.027, 0.028, 0.029, 0.030]
            diel = self.edbapp.core_stackup.create_multipole_debye_material("My_MP_Debye", freq, rel_perm, loss_tan)
            assert diel

        def test_018_update_layer(self):
            tol = 1e-12
            assert "LYR_1" in self.edbapp.core_stackup.stackup_layers.layers.keys()
            assert self.edbapp.core_stackup.stackup_layers["LYR_1"].name
            self.edbapp.core_stackup.stackup_layers["LYR_1"].thickness_value = "100um"
            assert abs(self.edbapp.core_stackup.stackup_layers["LYR_1"].thickness_value - 10e-5) < tol
            self.edbapp.core_stackup.stackup_layers["LYR_2"].material_name = "MyCond"
            assert self.edbapp.core_stackup.stackup_layers["LYR_2"].material_name == "MyCond"
            assert self.edbapp.core_stackup.stackup_layers["LYR_1"].filling_material_name is not None or False
            assert self.edbapp.core_stackup.stackup_layers["LYR_1"].top_bottom_association is not None or False
            assert self.edbapp.core_stackup.stackup_layers["LYR_1"].lower_elevation is not None or False
            assert self.edbapp.core_stackup.stackup_layers["LYR_1"].upper_elevation is not None or False
            assert self.edbapp.core_stackup.stackup_layers["LYR_1"].etch_factor is not None or False

        def test_019_remove_layer(self):
            layers = self.edbapp.core_stackup.stackup_layers
            assert layers.remove_layer("BOTTOM")

        def test_020_components(self):
            assert "R1" in list(self.edbapp.core_components.components.keys())
            assert self.edbapp.core_components.components["R1"].res_value
            assert self.edbapp.core_components.components["R1"].placement_layer
            assert isinstance(self.edbapp.core_components.components["R1"].lower_elevation, float)
            assert isinstance(self.edbapp.core_components.components["R1"].upper_elevation, float)
            assert self.edbapp.core_components.components["R1"].top_bottom_association == 0
            assert self.edbapp.core_components.components["R1"].pinlist
            assert self.edbapp.core_components.components["R1"].pins
            assert self.edbapp.core_components.components["R1"].pins["1"].pin_number
            assert self.edbapp.core_components.components["R1"].pins["1"].component
            assert (
                self.edbapp.core_components.components["R1"].pins["1"].lower_elevation
                == self.edbapp.core_components.components["R1"].lower_elevation
            )
            assert (
                self.edbapp.core_components.components["R1"].pins["1"].placement_layer
                == self.edbapp.core_components.components["R1"].placement_layer
            )
            assert (
                self.edbapp.core_components.components["R1"].pins["1"].upper_elevation
                == self.edbapp.core_components.components["R1"].upper_elevation
            )
            assert (
                self.edbapp.core_components.components["R1"].pins["1"].top_bottom_association
                == self.edbapp.core_components.components["R1"].top_bottom_association
            )
            assert self.edbapp.core_components.components["R1"].pins["1"].position
            assert self.edbapp.core_components.components["R1"].pins["1"].rotation

        def test_021_components_from_net(self):
            assert self.edbapp.core_components.get_components_from_nets("A0_N")

        def test_022_resistors(self):
            assert "R1" in list(self.edbapp.core_components.resistors.keys())
            assert "C1" not in list(self.edbapp.core_components.resistors.keys())

        def test_023_capacitors(self):
            assert "C1" in list(self.edbapp.core_components.capacitors.keys())
            assert "R1" not in list(self.edbapp.core_components.capacitors.keys())

        def test_024_inductors(self):
            assert "L3M1" in list(self.edbapp.core_components.inductors.keys())
            assert "R1" not in list(self.edbapp.core_components.inductors.keys())

        def test_025_ICs(self):
            assert "U8" in list(self.edbapp.core_components.ICs.keys())
            assert "R1" not in list(self.edbapp.core_components.ICs.keys())

        def test_026_IOs(self):
            assert "J1" in list(self.edbapp.core_components.IOs.keys())
            assert "R1" not in list(self.edbapp.core_components.IOs.keys())

        def test_027_Others(self):
            assert "EU1" in self.edbapp.core_components.Others
            assert "R1" not in self.edbapp.core_components.Others

        def test_028_Components_by_PartName(self):
            comp = self.edbapp.core_components.components_by_partname
            assert "A93549-020" in comp
            assert len(comp["A93549-020"]) > 1

        def test_029_get_through_resistor_list(self):
            assert self.edbapp.core_components.get_through_resistor_list(10)

        def test_030_get_rats(self):
            assert len(self.edbapp.core_components.get_rats()) > 0

        def test_031_get_component_connections(self):
            assert len(self.edbapp.core_components.get_component_net_connection_info("U2A5")) > 0

        def test_032_get_power_tree(self):
            OUTPUT_NET = "BST_V1P0_S0"
            GROUND_NETS = ["GND", "PGND"]
            (
                component_list,
                component_list_columns,
                net_group,
            ) = self.edbapp.core_nets.get_powertree(OUTPUT_NET, GROUND_NETS)
            assert component_list
            assert component_list_columns
            assert net_group

        def test_033_aedt_pinname_pin_position(self):
            cmp_pinlist = self.edbapp.core_padstack.get_pinlist_from_component_and_net("U2A5", "GND")
            pin_name = self.edbapp.core_components.get_aedt_pin_name(cmp_pinlist[0])
            assert type(pin_name) is str
            assert len(pin_name) > 0
            assert len(cmp_pinlist[0].position) == 2
            assert len(self.edbapp.core_components.get_pin_position(cmp_pinlist[0])) == 2

        def test_034_get_pins_name_from_net(self):
            cmp_pinlist = self.edbapp.core_components.get_pin_from_component("U2A5")
            assert len(self.edbapp.core_components.get_pins_name_from_net(cmp_pinlist, "GND")) > 0
            assert len(self.edbapp.core_components.get_pins_name_from_net(cmp_pinlist, "VCCC")) == 0

        def test_035_delete_single_pin_rlc(self):
            assert len(self.edbapp.core_components.delete_single_pin_rlc()) > 0

        def test_036_component_rlc(self):
            assert self.edbapp.core_components.set_component_rlc("R1", 30, 1e-9, 1e-12)

        def test_037_disable_component(self):
            assert self.edbapp.core_components.disable_rlc_component("R1")

        def test_038_delete_component(self):
            assert self.edbapp.core_components.delete_component("R1")

        def test_039_create_coax_port(self):
            assert self.edbapp.core_hfss.create_coax_port_on_component("U2A5", ["RSVD_0", "V1P0_S0"])

        def test_040_create_circuit_port(self):
            initial_len = len(self.edbapp.core_padstack.pingroups)
            assert (
                self.edbapp.core_siwave.create_circuit_port_on_net("U2A5", "V1P5_S3", "U2A5", "GND", 50, "test")
                == "test"
            )
            p2 = self.edbapp.core_siwave.create_circuit_port_on_net("U2A5", "V3P3_S0", "U2A5", "GND", 50, "test")
            assert p2 != "test" and "test" in p2
            pins = self.edbapp.core_components.get_pin_from_component("U2A5")
            p3 = self.edbapp.core_siwave.create_circuit_port_on_pin(pins[200], pins[0], 45)
            assert p3 != ""
            p4 = self.edbapp.core_hfss.create_circuit_port_on_net("U2A5", "RSVD_9")
            assert len(self.edbapp.core_padstack.pingroups) == initial_len + 6
            assert "GND" in p4 and "RSVD_9" in p4
            assert self.edbapp.core_siwave.create_pin_group_on_net("U2A5", "V1P0_S0", "PG_V1P0_S0")
            assert self.edbapp.core_siwave.create_circuit_port_on_pin_group(
                "PG_V1P0_S0", "PinGroup_2", impedance=50, name="test_port"
            )

        def test_041_create_voltage_source(self):
            assert "Vsource_" in self.edbapp.core_siwave.create_voltage_source_on_net(
                "U2A5", "PCIE_RBIAS", "U2A5", "GND", 3.3, 0
            )
            pins = self.edbapp.core_components.get_pin_from_component("U2A5")
            assert "VSource_" in self.edbapp.core_siwave.create_voltage_source_on_pin(pins[300], pins[10], 3.3, 0)
            if not is_ironpython:
                assert len(self.edbapp.sources) > 0
                assert len(self.edbapp.probes) == 0
                assert list(self.edbapp.sources.values())[0].magnitude == 3.3
                assert list(self.edbapp.sources.values())[0].phase == 0

        def test_042_create_current_source(self):
            assert self.edbapp.core_siwave.create_current_source_on_net("U2A5", "DDR3_DM1", "U2A5", "GND", 0.1, 0) != ""
            pins = self.edbapp.core_components.get_pin_from_component("U2A5")
            assert "I22" == self.edbapp.core_siwave.create_current_source_on_pin(pins[301], pins[10], 0.1, 0, "I22")

            assert self.edbapp.core_siwave.create_pin_group_on_net(
                reference_designator="U3A1", net_name="GND", group_name="gnd"
            )
            self.edbapp.core_siwave.create_pin_group(
                reference_designator="U3A1", pin_numbers=[16, 17], group_name="vrm_pos"
            )
            self.edbapp.core_siwave.create_current_source_on_pin_group(
                pos_pin_group_name="vrm_pos", neg_pin_group_name="gnd", name="vrm_current_source"
            )

            self.edbapp.core_siwave.create_pin_group(
                reference_designator="U3A1", pin_numbers=[14, 15], group_name="sink_pos"
            )

            self.edbapp.core_siwave.create_voltage_source_on_pin_group("sink_pos", "gnd", "vrm_voltage_source")

        def test_043_create_dc_terminal(self):
            assert self.edbapp.core_siwave.create_dc_terminal("U2A5", "DDR3_DM1", "dc_terminal1") == "dc_terminal1"

        def test_044_create_resistors(self):
            pins = self.edbapp.core_components.get_pin_from_component("U2A5")
            assert "RST4000" == self.edbapp.core_siwave.create_resistor_on_pin(pins[302], pins[10], 40, "RST4000")

        def test_045_create_siwave_ac_analsyis(self):
            assert self.edbapp.core_siwave.add_siwave_syz_analysis()

        def test_046_create_siwave_dc_analsyis(self):
            setup = self.edbapp.core_siwave.add_siwave_dc_analysis()
            assert setup.add_source_terminal_to_ground(list(self.edbapp.sources.keys())[0], 2)

        def test_047_get_nets_from_pin_list(self):
            cmp_pinlist = self.edbapp.core_padstack.get_pinlist_from_component_and_net("U2A5", "GND")
            if cmp_pinlist:
                assert cmp_pinlist[0].GetNet().GetName()

        def test_048_mesh_operations(self):
            mesh_ops = self.edbapp.core_hfss.get_trace_width_for_traces_with_ports()
            assert len(mesh_ops) > 0

        def test_049_assign_model(self):
            assert self.edbapp.core_components.set_component_model(
                "C1A14",
                modelpath=os.path.join(
                    self.local_scratch.path,
                    test_project_name + ".aedb",
                    "GRM32ER72A225KA35_25C_0V.sp",
                ),
                modelname="GRM32ER72A225KA35_25C_0V",
            )
            assert not self.edbapp.core_components.set_component_model(
                "C10000",
                modelpath=os.path.join(
                    self.local_scratch.path,
                    test_project_name + ".aedb",
                    "GRM32ER72A225KA35_25C_0V.sp",
                ),
                modelname="GRM32ER72A225KA35_25C_0V",
            )

        def test_050_assign_variable(self):
            result, var_server = self.edbapp.add_design_variable("my_variable", "1mm")
            assert result
            assert var_server
            result, var_server = self.edbapp.add_design_variable("my_variable", "1mm")
            assert not result
            assert self.edbapp.core_primitives.parametrize_trace_width("A0_N")
            assert self.edbapp.core_primitives.parametrize_trace_width("A0_N_R")
            result, var_server = self.edbapp.add_design_variable("my_parameter", "2mm", True)
            assert result
            assert var_server.IsVariableParameter("my_parameter")
            result, var_server = self.edbapp.add_design_variable("my_parameter", "2mm", True)
            assert not result
            result, var_server = self.edbapp.add_design_variable("$my_project_variable", "3mm")
            assert result
            assert var_server
            result, var_server = self.edbapp.add_design_variable("$my_project_variable", "3mm")
            assert not result

        def test_051_delete_net(self):
            self.edbapp.core_nets.nets["M_MA<6>"].delete()
            nets_deleted = self.edbapp.core_nets.delete_nets("M_MA<7>")
            assert "M_MA<7>" in nets_deleted

        def test_052_get_polygons_bounding(self):
            polys = self.edbapp.core_primitives.get_polygons_by_layer("GND")
            for poly in polys:
                bounding = self.edbapp.core_primitives.get_polygon_bounding_box(poly)
                assert len(bounding) == 4

        def test_053_get_polygons_bbylayerandnets(self):
            nets = ["GND", "IO2"]
            polys = self.edbapp.core_primitives.get_polygons_by_layer("BOTTOM", nets)
            assert polys

        def test_0548_get_polygons_points(self):
            polys = self.edbapp.core_primitives.get_polygons_by_layer("GND")
            for poly in polys:
                points = self.edbapp.core_primitives.get_polygon_points(poly)
                assert points

        def test_055_get_padstack(self):
            for el in self.edbapp.core_padstack.padstacks:
                pad = self.edbapp.core_padstack.padstacks[el]
                assert pad.hole_plating_thickness is not None or False
                assert pad.hole_properties is not None or False
                assert pad.hole_plating_thickness is not None or False
                assert pad.hole_plating_ratio is not None or False
                assert pad.via_start_layer is not None or False
                assert pad.via_stop_layer is not None or False
                assert pad.material is not None or False
                assert pad.hole_finished_size is not None or False
                assert pad.hole_rotation is not None or False
                assert pad.hole_offset_x is not None or False
                assert pad.hole_offset_y is not None or False
                assert pad.hole_type is not None or False
                assert pad.pad_by_layer[pad.via_stop_layer].parameters is not None or False
                assert pad.pad_by_layer[pad.via_stop_layer].parameters_values is not None or False
                assert pad.pad_by_layer[pad.via_stop_layer].offset_x is not None or False
                assert pad.pad_by_layer[pad.via_stop_layer].offset_y is not None or False
                assert isinstance(pad.pad_by_layer[pad.via_stop_layer].geometry_type, int)
                polygon = pad.pad_by_layer[pad.via_stop_layer].polygon_data
                if polygon:
                    assert polygon.GetBBox()

        def test_056_set_padstack(self):
            pad = self.edbapp.core_padstack.padstacks["C10N116"]
            hole_pad = 8
            tol = 1e-12
            pad.hole_properties = hole_pad
            pad.hole_offset_x = 0
            pad.hole_offset_y = 1
            pad.hole_rotation = 0
            pad.hole_plating_ratio = 90
            assert pad.hole_plating_ratio == 90
            pad.hole_plating_thickness = 0.3
            assert abs(pad.hole_plating_thickness - 0.3) <= tol
            pad.material = "copper"
            assert abs(pad.hole_properties[0] - hole_pad) < tol
            offset_x = 7
            offset_y = 1
            param = 7
            pad.pad_by_layer[pad.via_stop_layer].parameters = param
            pad.pad_by_layer[pad.via_stop_layer].offset_x = offset_x
            pad.pad_by_layer[pad.via_stop_layer].offset_y = offset_y
            assert pad.pad_by_layer[pad.via_stop_layer].offset_x == str(offset_x)
            assert pad.pad_by_layer[pad.via_stop_layer].offset_y == str(offset_y)
            assert pad.pad_by_layer[pad.via_stop_layer].parameters[0] == str(param)

        def test_057_save_edb_as(self):
            assert self.edbapp.save_edb_as(os.path.join(self.local_scratch.path, "Gelileo_new.aedb"))
            assert os.path.exists(os.path.join(self.local_scratch.path, "Gelileo_new.aedb", "edb.def"))

        def test_058_parametrize_layout(self):
            assert len(self.edbapp.core_primitives.polygons) > 0
            for el in self.edbapp.core_primitives.polygons:
                if el.GetId() == 2647:
                    poly = el
            for el in self.edbapp.core_primitives.polygons:
                if el.GetId() == 2742:
                    selection_poly = el
            for el in self.edbapp.core_primitives.polygons:
                if el.GetId() == 2647:
                    poly = el
            assert self.edbapp.core_primitives.parametrize_polygon(poly, selection_poly)

        def test_059_import_bom(self):
            assert self.edbapp.core_components.update_rlc_from_bom(
                os.path.join(local_path, "example_models", test_subfolder, bom_example),
                delimiter=",",
                valuefield="Value",
                comptype="Prod name",
                refdes="RefDes",
            )
            assert not self.edbapp.core_components.components["R2L2"].is_enabled
            self.edbapp.core_components.components["R2L2"].is_enabled = True
            assert self.edbapp.core_components.components["R2L2"].is_enabled

        def test_060_import_bom(self):
            target_path = os.path.join(local_path, "example_models", test_subfolder, "Galileo.aedb")
            edbapp = Edb(target_path, edbversion=desktop_version)
            edbapp.core_components.import_bom(
                os.path.join(local_path, "example_models", test_subfolder, "bom_example_2.csv")
            )
            assert not edbapp.core_components.components["R2L2"].is_enabled
            assert edbapp.core_components.components["U2A5"].partname == "IPD031-201x"

            export_bom_path = os.path.join(self.local_scratch.path, "export_bom.csv")
            assert edbapp.core_components.export_bom(export_bom_path)
            edbapp.close_edb()

        def test_061_create_component_from_pins(self):
            pins = self.edbapp.core_components.get_pin_from_component("R13")
            component = self.edbapp.core_components.create_component_from_pins(pins, "newcomp")
            assert component
            assert component.GetName() == "newcomp"
            assert len(list(component.LayoutObjs)) == 2

        def test_062_create_cutout(self):
            source_path = os.path.join(local_path, "example_models", test_subfolder, "Galileo.aedb")
            target_path = os.path.join(self.local_scratch.path, "Galileo_cutout_1.aedb")
            self.local_scratch.copyfolder(source_path, target_path)
            edbapp = Edb(target_path, edbversion=desktop_version)
            output = os.path.join(self.local_scratch.path, "cutout.aedb")
            assert edbapp.create_cutout(
                ["A0_N", "A0_P"],
                ["GND"],
                output_aedb_path=output,
                open_cutout_at_end=False,
                use_pyaedt_extent_computing=True,
            )
            assert edbapp.create_cutout(
                ["A0_N", "A0_P"],
                ["GND"],
                output_aedb_path=output,
                open_cutout_at_end=False,
            )
            assert os.path.exists(os.path.join(output, "edb.def"))
            bounding = edbapp.get_bounding_box()
            cutout_line_x = 41
            cutout_line_y = 30
            points = [[bounding[0][0], bounding[0][1]]]
            points.append([cutout_line_x, bounding[0][1]])
            points.append([cutout_line_x, cutout_line_y])
            points.append([bounding[0][0], cutout_line_y])
            points.append([bounding[0][0], bounding[0][1]])
            output = os.path.join(self.local_scratch.path, "cutout2.aedb")

            assert edbapp.create_cutout_on_point_list(
                points,
                nets_to_include=["GND", "V3P3_S0"],
                output_aedb_path=output,
                open_cutout_at_end=False,
                include_partial_instances=True,
            )
            assert os.path.exists(os.path.join(output, "edb.def"))
            edbapp.close_edb()

        def test_063_create_custom_cutout(self):

            source_path = os.path.join(local_path, "example_models", test_subfolder, "Galileo.aedb")
            target_path = os.path.join(self.local_scratch.path, "Galileo_cutout_2.aedb")
            self.local_scratch.copyfolder(source_path, target_path)
            edbapp = Edb(target_path, edbversion=desktop_version)
            if is_ironpython:
                assert not edbapp.create_cutout_multithread(
                    signal_list=["V3P3_S0"],
                    reference_list=["GND"],
                    extent_type="Bounding",
                    number_of_threads=4,
                )
            else:
                assert edbapp.create_cutout_multithread(
                    signal_list=["V3P3_S0"],
                    reference_list=["GND"],
                    extent_type="Bounding",
                    number_of_threads=4,
                    extent_defeature=0.001,
                )
                assert "A0_N" not in edbapp.core_nets.nets
                assert isinstance(edbapp.core_nets.find_and_fix_disjoint_nets("GND"), list)
                assert isinstance(edbapp.core_nets.find_and_fix_disjoint_nets("GND", keep_only_main_net=True), list)
                assert isinstance(
                    edbapp.core_nets.find_and_fix_disjoint_nets("GND", clean_disjoints_less_than=0.005), list
                )
            edbapp.close_edb()
            target_path = os.path.join(self.local_scratch.path, "Galileo_cutout_3.aedb")
            self.local_scratch.copyfolder(source_path, target_path)

        @pytest.mark.skipif(is_ironpython, reason="Method works in CPython only")
        def test_064_create_custom_cutout(self):
            source_path = os.path.join(local_path, "example_models", test_subfolder, "Galileo.aedb")
            target_path = os.path.join(self.local_scratch.path, "Galileo_cutout_3.aedb")
            self.local_scratch.copyfolder(source_path, target_path)

            edbapp = Edb(target_path, edbversion=desktop_version)
            bounding = edbapp.get_bounding_box()
            cutout_line_x = 41
            cutout_line_y = 30
            points = [[bounding[0][0], bounding[0][1]]]
            points.append([cutout_line_x, bounding[0][1]])
            points.append([cutout_line_x, cutout_line_y])
            points.append([bounding[0][0], cutout_line_y])
            points.append([bounding[0][0], bounding[0][1]])
            assert edbapp.create_cutout_multithread(
                signal_list=["V3P3_S0"],
                reference_list=["GND"],
                number_of_threads=4,
                extent_type="ConvexHull",
                custom_extent=points,
            )
            edbapp.close_edb()

        @pytest.mark.skipif(is_ironpython, reason="Method works in CPython only")
        def test_065_create_custom_cutout(self):
            source_path = os.path.join(local_path, "example_models", test_subfolder, "Galileo.aedb")
            target_path = os.path.join(self.local_scratch.path, "Galileo_cutout_4.aedb")
            self.local_scratch.copyfolder(source_path, target_path)

            edbapp = Edb(target_path, edbversion=desktop_version)

            assert edbapp.create_cutout_multithread(
                signal_list=["V3P3_S0"],
                reference_list=["GND"],
                number_of_threads=4,
                extent_type="ConvexHull",
                use_pyaedt_extent_computing=True,
            )
            edbapp.close_edb()

        def test_066_rvalue(self):
            assert resistor_value_parser("100meg")

        def test_067_stackup_limits(self):
            assert self.edbapp.core_stackup.stackup_limits()

        def test_068_create_polygon(self):
            settings.enable_error_handler = True
            points = [
                [-0.025, -0.02],
                [0.025, -0.02],
                [0.025, 0.02],
                [-0.025, 0.02],
                [-0.025, -0.02],
            ]
            plane = self.edbapp.core_primitives.Shape("polygon", points=points)
            points = [
                [-0.001, -0.001],
                [0.001, -0.001, "ccw", 0.0, -0.0012],
                [0.001, 0.001],
                [-0.001, 0.001],
                [-0.001, -0.001],
            ]
            void1 = self.edbapp.core_primitives.Shape("polygon", points=points)
            void2 = self.edbapp.core_primitives.Shape("rectangle", [-0.002, 0.0], [-0.015, 0.0005])
            assert self.edbapp.core_primitives.create_polygon(plane, "TOP", [void1, void2])
            points = [
                [0, 0, 1],
            ]
            assert not self.edbapp.core_primitives.create_polygon_from_points(points, "TOP")
            points = [
                [0.1, "s"],
            ]
            plane = self.edbapp.core_primitives.Shape("polygon", points=points)
            assert not self.edbapp.core_primitives.create_polygon(plane, "TOP")
            points = [[0.001, -0.001, "ccn", 0.0, -0.0012]]
            plane = self.edbapp.core_primitives.Shape("polygon", points=points)
            assert not self.edbapp.core_primitives.create_polygon(plane, "TOP")
            settings.enable_error_handler = False

        def test_069_create_path(self):
            points = [
                [-0.025, -0.02],
                [0.025, -0.02],
                [0.025, 0.02],
            ]
            assert self.edbapp.core_primitives.create_trace(points, "TOP")

        def test_070_create_outline(self):
            assert self.edbapp.core_stackup.stackup_layers.add_outline_layer("Outline1")
            assert not self.edbapp.core_stackup.stackup_layers.add_outline_layer("Outline1")
            self.edbapp.stackup.add_layer("new_layer_1", "TOP", "insert_below")
            assert self.edbapp.stackup.layers["TOP"].thickness == 4.826e-05
            self.edbapp.stackup.layers["TOP"].thickness = 4e-5
            assert self.edbapp.stackup.layers["TOP"].thickness == 4e-05

        def test_071_create_edb(self):
            edb = Edb(os.path.join(self.local_scratch.path, "temp.aedb"))
            assert edb
            assert edb.active_layout
            edb.close_edb()

        @pytest.mark.skipif(config["build_machine"], reason="Not running in non-graphical mode")
        def test_072_export_to_hfss(self):
            edb = Edb(
                edbpath=os.path.join(local_path, "example_models", test_subfolder, "simple.aedb"),
                edbversion=desktop_version,
            )
            options_config = {"UNITE_NETS": 1, "LAUNCH_Q3D": 0}
            out = edb.write_export3d_option_config_file(self.local_scratch, options_config)
            assert os.path.exists(out)
            out = edb.export_hfss(self.local_scratch)
            assert os.path.exists(out)
            edb.close_edb()

        @pytest.mark.skipif(config["build_machine"], reason="Not running in non-graphical mode")
        def test_073_export_to_q3d(self):
            edb = Edb(
                edbpath=os.path.join(local_path, "example_models", test_subfolder, "simple.aedb"),
                edbversion=desktop_version,
            )
            options_config = {"UNITE_NETS": 1, "LAUNCH_Q3D": 0}
            out = edb.write_export3d_option_config_file(self.local_scratch, options_config)
            assert os.path.exists(out)
            out = edb.export_q3d(self.local_scratch, net_list=["ANALOG_A0", "ANALOG_A1", "ANALOG_A2"], hidden=True)
            assert os.path.exists(out)
            edb.close_edb()

        @pytest.mark.skipif(config["build_machine"], reason="Not running in non-graphical mode")
        def test_074_export_to_maxwell(self):
            edb = Edb(
                edbpath=os.path.join(local_path, "example_models", test_subfolder, "simple.aedb"),
                edbversion=desktop_version,
            )
            options_config = {"UNITE_NETS": 1, "LAUNCH_MAXWELL": 0}
            out = edb.write_export3d_option_config_file(self.local_scratch, options_config)
            assert os.path.exists(out)
            out = edb.export_maxwell(self.local_scratch, num_cores=6)
            assert os.path.exists(out)
            edb.close_edb()

        def test_075_flatten_planes(self):
            assert self.edbapp.core_primitives.unite_polygons_on_layer("TOP")

        def test_076_create_solder_ball_on_component(self):
            assert self.edbapp.core_components.set_solder_ball("U1A1")

        def test_077_add_void(self):
            plane_shape = self.edbapp.core_primitives.Shape("rectangle", pointA=["-5mm", "-5mm"], pointB=["5mm", "5mm"])
            plane = self.edbapp.core_primitives.create_polygon(plane_shape, "TOP", net_name="GND")
            void = self.edbapp.core_primitives.create_trace([["0", "0"], ["0", "1mm"]], layer_name="TOP", width="0.1mm")
            assert self.edbapp.core_primitives.add_void(plane, void)

        def test_078_create_solder_balls_on_component(self):
            assert self.edbapp.core_components.set_solder_ball("U2A5")

        def test_080_fix_circle_voids(self):
            assert self.edbapp.core_primitives.fix_circle_void_for_clipping()

        def test_081_padstack_instance(self):
            padstack_instances = self.edbapp.core_padstack.get_padstack_instance_by_net_name("GND")
            assert len(padstack_instances)
            padstack_1 = list(padstack_instances.values())[0]
            assert padstack_1.id
            assert isinstance(padstack_1.bounding_box, list)
            for v in list(padstack_instances.values()):
                if not v.is_pin:
                    v.name = "TestInst"
                    assert v.name == "TestInst"
                    break

        def test_082_duplicate_padstack(self):
            self.edbapp.core_padstack.duplicate_padstack(
                target_padstack_name="VIA_20-10-28_SMB",
                new_padstack_name="VIA_20-10-28_SMB_NEW",
            )
            assert self.edbapp.core_padstack.padstacks["VIA_20-10-28_SMB_NEW"]

        def test_83_set_padstack_property(self):
            self.edbapp.core_padstack.set_pad_property(
                padstack_name="VIA_18-10-28_SMB",
                layer_name="new",
                pad_shape="Circle",
                pad_params="800um",
            )
            assert self.edbapp.core_padstack.padstacks["VIA_18-10-28_SMB"].pad_by_layer["new"]

        def test_084_primitives_area(self):
            i = 0
            while i < 10:
                assert self.edbapp.core_primitives.primitives[i].area(False) > 0
                assert self.edbapp.core_primitives.primitives[i].area(True) > 0
                i += 1

        def test_085_short_component(self):
            assert self.edbapp.core_components.short_component_pins("EU1", width=0.2e-3)
            assert self.edbapp.core_components.short_component_pins("U10", ["2", "5"])

        def test_086_set_component_type(self):
            comp = self.edbapp.core_components.components["R2L18"]
            comp.type = "Resistor"
            assert comp.type == "Resistor"
            comp.type = "Inductor"
            assert comp.type == "Inductor"
            comp.type = "Capacitor"
            assert comp.type == "Capacitor"
            comp.type = "IO"
            assert comp.type == "IO"
            comp.type = "IC"
            assert comp.type == "IC"
            comp.type = "Other"
            assert comp.type == "Other"

        def test_087_deactivate_rlc(self):
            assert self.edbapp.core_components.deactivate_rlc_component(component="C1", create_circuit_port=True)
            assert self.edbapp.core_components.deactivate_rlc_component(component="C2", create_circuit_port=False)

        def test_088_create_symmetric_stackup(self):
            if not is_ironpython:
                app_edb = Edb(edbversion=desktop_version)
                assert not app_edb.core_stackup.create_symmetric_stackup(9)
                assert app_edb.core_stackup.create_symmetric_stackup(8)
                app_edb.close_edb()

                app_edb = Edb(edbversion=desktop_version)
                assert app_edb.core_stackup.create_symmetric_stackup(8, soldermask=False)
                app_edb.close_edb()

                app_edb = Edb(edbversion=desktop_version)
                assert not app_edb.stackup.create_symmetric_stackup(9)
                assert app_edb.stackup.create_symmetric_stackup(8)
                app_edb.close_edb()

                app_edb = Edb(edbversion=desktop_version)
                assert app_edb.stackup.create_symmetric_stackup(8, soldermask=False)
                app_edb.close_edb()

        def test_089_create_rectangle(self):
            assert self.edbapp.core_primitives.create_rectangle("TOP", "SIG1", ["0", "0"], ["2mm", "3mm"])
            assert self.edbapp.core_primitives.create_rectangle(
                "TOP",
                "SIG2",
                center_point=["0", "0"],
                width="4mm",
                height="5mm",
                representation_type="CenterWidthHeight",
            )

        @pytest.mark.skipif(is_ironpython, reason="Failing Subtract")
        def test_089B_circle_boolean(self):
            poly = self.edbapp.core_primitives.create_polygon_from_points(
                [[0, 0], [100, 0], [100, 100], [0, 100]], "TOP"
            )
            assert poly
            poly.add_void([[20, 20], [20, 30], [100, 30], [100, 20]])
            poly2 = self.edbapp.core_primitives.create_polygon_from_points(
                [[60, 60], [60, 150], [150, 150], [150, 60]], "TOP"
            )
            new_polys = poly.subtract(poly2)
            assert len(new_polys) == 1
            circle = self.edbapp.core_primitives.create_circle("TOP", 40, 40, 15)
            assert circle
            intersection = new_polys[0].intersect(circle)
            assert len(intersection) == 1
            circle2 = self.edbapp.core_primitives.create_circle("TOP", 20, 20, 15)
            assert circle2.unite(intersection)

        def test_090_negative_properties(self):
            layer = self.edbapp.core_stackup.stackup_layers.layers["TOP"]
            layer.negative_layer = True
            assert layer.negative_layer

        def test_091_roughness_property(self):
            layer = self.edbapp.core_stackup.stackup_layers.layers["TOP"]
            layer.roughness_enabled = True
            assert layer.roughness_enabled

        def test_092_thickness_property(self):
            layer = self.edbapp.core_stackup.stackup_layers.layers["TOP"]
            layer.thickness_value = 35e-6
            assert layer.thickness_value == 35e-6

        def test_093_filling_material_property(self):
            layer = self.edbapp.core_stackup.stackup_layers.layers["TOP"]
            layer.filling_material_name = "air"
            assert layer.filling_material_name == "air"

        def test_094_material_property(self):
            layer = self.edbapp.core_stackup.stackup_layers.layers["TOP"]
            layer.material_name = "copper"
            assert layer.material_name == "copper"

        def test_095_layer_type_property(self):
            layer = self.edbapp.core_stackup.stackup_layers.layers["TOP"]
            layer.layer_type = 1
            assert layer.layer_type == 1
            layer.layer_type = 0
            assert layer.layer_type == 0

        def test_096_loggers(self):
            core_stackup = self.edbapp.core_stackup
            layers = self.edbapp.core_stackup.stackup_layers
            layer = self.edbapp.core_stackup.stackup_layers.layers["TOP"]
            self.edbapp.logger.warning("Is it working?")
            core_stackup._logger.warning("Is it working?")
            layers._logger.warning("Is it working?")
            layer._logger.warning("Is it working?")

        def test_097_change_design_variable_value(self):
            self.edbapp.add_design_variable("ant_length", "1cm")
            self.edbapp.add_design_variable("my_parameter_default", "1mm", is_parameter=True)
            self.edbapp.add_design_variable("$my_project_variable", "1mm")
            changed_variable_1 = self.edbapp.change_design_variable_value("ant_length", "1m")
            if isinstance(changed_variable_1, tuple):
                changed_variable_done, ant_length_value = changed_variable_1
                assert changed_variable_done
            else:
                assert changed_variable_1
            changed_variable_2 = self.edbapp.change_design_variable_value("elephant_length", "1m")
            if isinstance(changed_variable_2, tuple):
                changed_variable_done, elephant_length_value = changed_variable_2
                assert not changed_variable_done
            else:
                assert not changed_variable_2
            changed_variable_3 = self.edbapp.change_design_variable_value("my_parameter_default", "1m")
            if isinstance(changed_variable_3, tuple):
                changed_variable_done, my_parameter_value = changed_variable_3
                assert changed_variable_done
            else:
                assert changed_variable_3
            changed_variable_4 = self.edbapp.change_design_variable_value("$my_project_variable", "1m")
            if isinstance(changed_variable_4, tuple):
                changed_variable_done, my_project_variable_value = changed_variable_4
                assert changed_variable_done
            else:
                assert changed_variable_4
            changed_variable_5 = self.edbapp.change_design_variable_value("$my_parameter", "1m")
            if isinstance(changed_variable_5, tuple):
                changed_variable_done, my_project_variable_value = changed_variable_4
                assert not changed_variable_done
            else:
                assert not changed_variable_5

        def test_098_etch_factor(self):
            layer = self.edbapp.core_stackup.stackup_layers.layers["TOP"]
            added_layer = self.edbapp.core_stackup.stackup_layers.add_layer(layerName="added_layer", etchMap=1.1)
            assert layer.etch_factor == 0
            layer.etch_factor = "1"
            print(type(layer._etch_factor))
            assert layer.etch_factor == 1
            layer.etch_factor = 1.1
            assert layer.etch_factor == 1.1
            layer.etch_factor = None
            assert layer.etch_factor == 0.00000
            assert added_layer.etch_factor == 1.1

        def test_099_int_to_layer_types(self):
            stackup = self.edbapp.core_stackup.stackup_layers
            signal_layer = stackup._int_to_layer_types(0)
            assert signal_layer == stackup.layer_types.SignalLayer
            dielectric_layer = stackup._int_to_layer_types(1)
            assert dielectric_layer == stackup.layer_types.DielectricLayer
            conducting_layer = stackup._int_to_layer_types(2)
            assert conducting_layer == stackup.layer_types.ConductingLayer
            airlines_layer = stackup._int_to_layer_types(3)
            assert airlines_layer == stackup.layer_types.AirlinesLayer
            errors_layer = stackup._int_to_layer_types(4)
            assert errors_layer == stackup.layer_types.ErrorsLayer
            symbol_layer = stackup._int_to_layer_types(5)
            assert symbol_layer == stackup.layer_types.SymbolLayer
            measure_layer = stackup._int_to_layer_types(6)
            assert measure_layer == stackup.layer_types.MeasureLayer
            assembly_layer = stackup._int_to_layer_types(8)
            assert assembly_layer == stackup.layer_types.AssemblyLayer
            silkscreen_layer = stackup._int_to_layer_types(9)
            assert silkscreen_layer == stackup.layer_types.SilkscreenLayer
            solder_mask_layer = stackup._int_to_layer_types(10)
            assert solder_mask_layer == stackup.layer_types.SolderMaskLayer
            solder_paste_layer = stackup._int_to_layer_types(11)
            assert solder_paste_layer == stackup.layer_types.SolderPasteLayer
            glue_layer = stackup._int_to_layer_types(12)
            assert glue_layer == stackup.layer_types.GlueLayer
            wirebond_layer = stackup._int_to_layer_types(13)
            assert wirebond_layer == stackup.layer_types.WirebondLayer
            user_layer = stackup._int_to_layer_types(14)
            assert user_layer == stackup.layer_types.UserLayer
            siwave_hfss_solver_regions = stackup._int_to_layer_types(16)
            assert siwave_hfss_solver_regions == stackup.layer_types.SIwaveHFSSSolverRegions
            outline_layer = stackup._int_to_layer_types(18)
            assert outline_layer == stackup.layer_types.OutlineLayer

        def test_100_layer_types_to_int(self):
            stackup = self.edbapp.core_stackup.stackup_layers
            signal_layer = stackup._layer_types_to_int(stackup.layer_types.SignalLayer)
            assert signal_layer == 0
            dielectric_layer = stackup._layer_types_to_int(stackup.layer_types.DielectricLayer)
            assert dielectric_layer == 1
            conducting_layer = stackup._layer_types_to_int(stackup.layer_types.ConductingLayer)
            assert conducting_layer == 2
            airlines_layer = stackup._layer_types_to_int(stackup.layer_types.AirlinesLayer)
            assert airlines_layer == 3
            errors_layer = stackup._layer_types_to_int(stackup.layer_types.ErrorsLayer)
            assert errors_layer == 4
            symbol_layer = stackup._layer_types_to_int(stackup.layer_types.SymbolLayer)
            assert symbol_layer == 5
            measure_layer = stackup._layer_types_to_int(stackup.layer_types.MeasureLayer)
            assert measure_layer == 6
            assembly_layer = stackup._layer_types_to_int(stackup.layer_types.AssemblyLayer)
            assert assembly_layer == 8
            silkscreen_layer = stackup._layer_types_to_int(stackup.layer_types.SilkscreenLayer)
            assert silkscreen_layer == 9
            solder_mask_layer = stackup._layer_types_to_int(stackup.layer_types.SolderMaskLayer)
            assert solder_mask_layer == 10
            solder_paste_layer = stackup._layer_types_to_int(stackup.layer_types.SolderPasteLayer)
            assert solder_paste_layer == 11
            glue_layer = stackup._layer_types_to_int(stackup.layer_types.GlueLayer)
            assert glue_layer == 12
            wirebond_layer = stackup._layer_types_to_int(stackup.layer_types.WirebondLayer)
            assert wirebond_layer == 13
            user_layer = stackup._layer_types_to_int(stackup.layer_types.UserLayer)
            assert user_layer == 14
            siwave_hfss_solver_regions = stackup._layer_types_to_int(stackup.layer_types.SIwaveHFSSSolverRegions)
            assert siwave_hfss_solver_regions == 16
            outline_layer = stackup._layer_types_to_int(stackup.layer_types.OutlineLayer)
            assert outline_layer == 18

        def test_101_export_import_json_for_config(self):
            sim_config = SimulationConfiguration()
            assert sim_config.output_aedb is None
            sim_config.output_aedb = os.path.join(self.local_scratch.path, "test.aedb")
            assert sim_config.output_aedb == os.path.join(self.local_scratch.path, "test.aedb")
            json_file = os.path.join(self.local_scratch.path, "test.json")
            sim_config._filename = json_file
            sim_config.arc_angle = "90deg"
            assert sim_config.export_json(json_file)
            test_0import = SimulationConfiguration()
            assert test_0import.import_json(json_file)
            assert test_0import.arc_angle == "90deg"
            assert test_0import._filename == json_file

        def test_102_duplicate_material(self):
            stack_up = self.edbapp.core_stackup
            duplicated_copper = stack_up.duplicate_material("copper", "my_new_copper")
            assert duplicated_copper
            duplicated_fr4_epoxy = stack_up.duplicate_material("FR4_epoxy", "my_new_FR4")
            assert duplicated_fr4_epoxy
            duplicated_pec = stack_up.duplicate_material("pec", "my_new_pec")
            assert duplicated_pec
            cloned_permittivity = stack_up.get_property_by_material_name("permittivity", "my_new_pec")
            permittivity = stack_up.get_property_by_material_name("permittivity", "pec")
            cloned_permeability = stack_up.get_property_by_material_name("permeability", "my_new_pec")
            permeability = stack_up.get_property_by_material_name("permeability", "pec")
            cloned_conductivity = stack_up.get_property_by_material_name("conductivity", "my_new_pec")
            conductivity = stack_up.get_property_by_material_name("conductivity", "pec")
            cloned_dielectric_loss = stack_up.get_property_by_material_name("dielectric_loss_tangent", "my_new_pec")
            dielectric_loss = stack_up.get_property_by_material_name("dielectric_loss_tangent", "pec")
            cloned_magnetic_loss = stack_up.get_property_by_material_name("magnetic_loss_tangent", "my_new_pec")
            magnetic_loss = stack_up.get_property_by_material_name("magnetic_loss_tangent", "pec")
            assert cloned_permittivity == permittivity
            assert cloned_permeability == permeability
            assert cloned_conductivity == conductivity
            assert cloned_dielectric_loss == dielectric_loss
            assert cloned_magnetic_loss == magnetic_loss
            non_duplicated = stack_up.duplicate_material("my_nonexistent_mat", "nothing")
            assert not non_duplicated

        def test_103_get_property_by_material_name(self):
            stack_up = self.edbapp.core_stackup
            permittivity = stack_up.get_property_by_material_name("permittivity", "FR4_epoxy")
            permeability = stack_up.get_property_by_material_name("permeability", "FR4_epoxy")
            conductivity = stack_up.get_property_by_material_name("conductivity", "copper")
            dielectric_loss = stack_up.get_property_by_material_name("dielectric_loss_tangent", "FR4_epoxy")
            magnetic_loss = stack_up.get_property_by_material_name("magnetic_loss_tangent", "FR4_epoxy")
            assert permittivity == 4.4
            assert permeability == 0
            assert conductivity == 59590000
            assert dielectric_loss == 0.02
            assert magnetic_loss == 0
            failing_test_01 = stack_up.get_property_by_material_name("magnetic_loss_tangent", "inexistent_material")
            assert not failing_test_01
            failing_test_02 = stack_up.get_property_by_material_name("none_property", "copper")
            assert not failing_test_02

        def test_104_classify_nets(self):
            assert self.edbapp.core_nets.classify_nets(["RSVD_0", "RSVD_1"], ["V3P3_S0"])

        def test_105_place_a3dcomp_3d_placement(self):
            source_path = os.path.join(local_path, "example_models", test_subfolder, "lam_for_bottom_place.aedb")
            target_path = os.path.join(self.local_scratch.path, "output.aedb")
            self.local_scratch.copyfolder(source_path, target_path)
            laminate_edb = Edb(target_path, edbversion=desktop_version)
            chip_a3dcomp = os.path.join(local_path, "example_models", test_subfolder, "chip.a3dcomp")
            try:
                layout = laminate_edb.active_layout
                cell_instances = list(layout.CellInstances)
                assert len(cell_instances) == 0
                assert laminate_edb.core_stackup.place_a3dcomp_3d_placement(
                    chip_a3dcomp,
                    angle=0.0,
                    offset_x=0.0,
                    offset_y=0.0,
                    place_on_top=True,
                )
                cell_instances = list(layout.CellInstances)
                assert len(cell_instances) == 1
                cell_instance = cell_instances[0]
                assert cell_instance.Is3DPlacement()
                if is_ironpython:
                    (
                        res,
                        local_origin,
                        rotation_axis_from,
                        rotation_axis_to,
                        angle,
                        loc,
                    ) = cell_instance.Get3DTransformation()
                else:
                    (
                        res,
                        local_origin,
                        rotation_axis_from,
                        rotation_axis_to,
                        angle,
                        loc,
                    ) = cell_instance.Get3DTransformation(None, None, None, None, None)
                assert res
                zero_value = laminate_edb.edb_value(0)
                one_value = laminate_edb.edb_value(1)
                origin_point = laminate_edb.edb.Geometry.Point3DData(zero_value, zero_value, zero_value)
                x_axis_point = laminate_edb.edb.Geometry.Point3DData(one_value, zero_value, zero_value)
                assert local_origin.IsEqual(origin_point)
                assert rotation_axis_from.IsEqual(x_axis_point)
                assert rotation_axis_to.IsEqual(x_axis_point)
                assert angle.IsEqual(zero_value)
                assert loc.IsEqual(
                    laminate_edb.edb.Geometry.Point3DData(zero_value, zero_value, laminate_edb.edb_value(170e-6))
                )
                assert laminate_edb.save_edb()
            finally:
                laminate_edb.close_edb()

        def test_106_place_a3dcomp_3d_placement_on_bottom(self):
            source_path = os.path.join(local_path, "example_models", test_subfolder, "lam_for_bottom_place.aedb")
            target_path = os.path.join(self.local_scratch.path, "output.aedb")
            self.local_scratch.copyfolder(source_path, target_path)
            laminate_edb = Edb(target_path, edbversion=desktop_version)
            chip_a3dcomp = os.path.join(local_path, "example_models", test_subfolder, "chip.a3dcomp")
            try:
                layout = laminate_edb.active_layout
                cell_instances = list(layout.CellInstances)
                assert len(cell_instances) == 0
                assert laminate_edb.core_stackup.place_a3dcomp_3d_placement(
                    chip_a3dcomp,
                    angle=90.0,
                    offset_x=0.5e-3,
                    offset_y=-0.5e-3,
                    place_on_top=False,
                )
                cell_instances = list(layout.CellInstances)
                assert len(cell_instances) == 1
                cell_instance = cell_instances[0]
                assert cell_instance.Is3DPlacement()
                if is_ironpython:
                    (
                        res,
                        local_origin,
                        rotation_axis_from,
                        rotation_axis_to,
                        angle,
                        loc,
                    ) = cell_instance.Get3DTransformation()
                else:
                    (
                        res,
                        local_origin,
                        rotation_axis_from,
                        rotation_axis_to,
                        angle,
                        loc,
                    ) = cell_instance.Get3DTransformation(None, None, None, None, None)
                assert res
                zero_value = laminate_edb.edb_value(0)
                one_value = laminate_edb.edb_value(1)
                flip_angle_value = laminate_edb.edb_value("180deg")
                origin_point = laminate_edb.edb.Geometry.Point3DData(zero_value, zero_value, zero_value)
                x_axis_point = laminate_edb.edb.Geometry.Point3DData(one_value, zero_value, zero_value)
                assert local_origin.IsEqual(origin_point)
                assert rotation_axis_from.IsEqual(x_axis_point)
                assert rotation_axis_to.IsEqual(
                    laminate_edb.edb.Geometry.Point3DData(zero_value, laminate_edb.edb_value(-1.0), zero_value)
                )
                assert angle.IsEqual(flip_angle_value)
                assert loc.IsEqual(
                    laminate_edb.edb.Geometry.Point3DData(
                        laminate_edb.edb_value(0.5e-3),
                        laminate_edb.edb_value(-0.5e-3),
                        zero_value,
                    )
                )
                assert laminate_edb.save_edb()
            finally:
                laminate_edb.close_edb()

        def test_107_create_edge_ports(self):
            edb = Edb(
                edbpath=os.path.join(local_path, "example_models", test_subfolder, "edge_ports.aedb"),
                edbversion=desktop_version,
            )
            poly_list = [poly for poly in list(edb.active_layout.Primitives) if int(poly.GetPrimitiveType()) == 2]
            port_poly = [poly for poly in poly_list if poly.GetId() == 17][0]
            ref_poly = [poly for poly in poly_list if poly.GetId() == 19][0]
            port_location = [-65e-3, -13e-3]
            ref_location = [-63e-3, -13e-3]
            assert edb.core_hfss.create_edge_port_on_polygon(
                polygon=port_poly,
                reference_polygon=ref_poly,
                terminal_point=port_location,
                reference_point=ref_location,
            )
            port_poly = [poly for poly in poly_list if poly.GetId() == 23][0]
            ref_poly = [poly for poly in poly_list if poly.GetId() == 22][0]
            port_location = [-65e-3, -10e-3]
            ref_location = [-65e-3, -10e-3]
            assert edb.core_hfss.create_edge_port_on_polygon(
                polygon=port_poly,
                reference_polygon=ref_poly,
                terminal_point=port_location,
                reference_point=ref_location,
            )
            port_poly = [poly for poly in poly_list if poly.GetId() == 25][0]
            port_location = [-65e-3, -7e-3]
            assert edb.core_hfss.create_edge_port_on_polygon(
                polygon=port_poly, terminal_point=port_location, reference_layer="gnd"
            )
            edb.close_edb()

        def test_108_create_dc_simulation(self):

            edb = Edb(
                edbpath=os.path.join(local_path, "example_models", test_subfolder, "dc_flow.aedb"),
                edbversion=desktop_version,
            )
            sim_setup = edb.new_simulation_configuration()
            sim_setup.do_cutout_subdesign = False
            sim_setup.solver_type = SolverType.SiwaveDC
            sim_setup.add_voltage_source(
                positive_node_component="Q3",
                positive_node_net="SOURCE_HBA_PHASEA",
                negative_node_component="Q3",
                negative_node_net="HV_DC+",
            )
            sim_setup.add_current_source(
                name="I25",
                positive_node_component="Q5",
                positive_node_net="SOURCE_HBB_PHASEB",
                negative_node_component="Q5",
                negative_node_net="HV_DC+",
            )
            assert len(sim_setup.sources) == 2
            sim_setup.open_edb_after_build = False
            sim_setup.batch_solve_settings.output_aedb = os.path.join(self.local_scratch.path, "build.aedb")
            original_path = edb.edbpath
            assert sim_setup.build_simulation_project()
            assert edb.edbpath == original_path
            sim_setup.open_edb_after_build = True
            assert sim_setup.build_simulation_project()
            assert edb.edbpath == os.path.join(self.local_scratch.path, "build.aedb")

            edb.close_edb()

        def test_109_add_soure(self):
            example_project = os.path.join(local_path, "example_models", test_subfolder, "Galileo.aedb")
            target_path = os.path.join(self.local_scratch.path, "test_0create_source", "Galileo.aedb")
            self.local_scratch.copyfolder(example_project, target_path)
            sim_config = SimulationConfiguration()
            sim_config.add_voltage_source(
                name="test_0v_source",
                positive_node_component="U2A5",
                positive_node_net="V3P3_S0",
                negative_node_component="U2A5",
                negative_node_net="GND",
            )
            sim_config.add_current_source(
                positive_node_component="U2A5",
                positive_node_net="V1P5_S0",
                negative_node_component="U2A5",
                negative_node_net="GND",
            )
            sim_config.add_dc_ground_source_term("test_0v_source", 1)
            assert sim_config.dc_source_terms_to_ground["test_0v_source"] == 1
            assert len(sim_config.sources) == 2

        def test_110_layout_tchickness(self):
            assert self.edbapp.core_stackup.get_layout_thickness()

        def test_111_get_layout_stats(self):
            assert self.edbapp.get_statistics()

        def test_112_edb_stats(self):
            example_project = os.path.join(local_path, "example_models", test_subfolder, "Galileo.aedb")
            target_path = os.path.join(self.local_scratch.path, "Galileo_110.aedb")
            self.local_scratch.copyfolder(example_project, target_path)
            edb = Edb(target_path, edbversion=desktop_version)
            edb_stats = edb.get_statistics(compute_area=True)
            assert edb_stats
            assert edb_stats.num_layers
            assert edb_stats.stackup_thickness
            assert edb_stats.num_vias
            assert edb_stats.occupying_ratio
            assert edb_stats.occupying_surface
            assert edb_stats.layout_size
            assert edb_stats.num_polygons
            assert edb_stats.num_traces
            assert edb_stats.num_nets
            assert edb_stats.num_discrete_components
            assert edb_stats.num_inductors
            assert edb_stats.num_capacitors
            assert edb_stats.num_resistors

        def test_113_set_bounding_box_extent(self):
            source_path = os.path.join(local_path, "example_models", test_subfolder, "test_107.aedb")
            target_path = os.path.join(self.local_scratch.path, "test_113.aedb")
            self.local_scratch.copyfolder(source_path, target_path)
            edb = Edb(target_path)
            initial_extent_info = edb.active_cell.GetHFSSExtentInfo()
            assert initial_extent_info.ExtentType == edb.edb.Utility.HFSSExtentInfoType.Conforming
            config = SimulationConfiguration()
            config.radiation_box = RadiationBoxType.BoundingBox
            assert edb.core_hfss.configure_hfss_extents(config)
            final_extent_info = edb.active_cell.GetHFSSExtentInfo()
            assert final_extent_info.ExtentType == edb.edb.Utility.HFSSExtentInfoType.BoundingBox

        def test_114_create_source(self):
            source = Source()
            source.l_value = 1e-9
            assert source.l_value == 1e-9
            source.r_value = 1.3
            assert source.r_value == 1.3
            source.c_value = 1e-13
            assert source.c_value == 1e-13
            source.create_physical_resistor = True
            assert source.create_physical_resistor

        def test_115_create_rlc(self):
            sim_config = SimulationConfiguration()
            sim_config.add_rlc(
                "test",
                r_value=1.5,
                c_value=1e-13,
                l_value=1e-10,
                positive_node_net="test_0net",
                positive_node_component="U2",
                negative_node_net="neg_net",
                negative_node_component="U2",
            )
            assert sim_config.sources
            assert sim_config.sources[0].source_type == SourceType.Rlc
            assert sim_config.sources[0].r_value == 1.5
            assert sim_config.sources[0].l_value == 1e-10
            assert sim_config.sources[0].c_value == 1e-13

        def test_116_create_rlc_component(self):
            example_project = os.path.join(local_path, "example_models", test_subfolder, "Galileo.aedb")
            target_path = os.path.join(self.local_scratch.path, "Galileo_114.aedb")
            self.local_scratch.copyfolder(example_project, target_path)
            edb = Edb(target_path, edbversion=desktop_version)
            pins = edb.core_components.get_pin_from_component("U2A5", "V1P5_S0")
            ref_pins = edb.core_components.get_pin_from_component("U2A5", "GND")
            assert edb.core_components.create_rlc_component(
                [pins[0], ref_pins[0]], "test_0rlc", r_value=1.67, l_value=1e-13, c_value=1e-11
            )
            edb.close_edb()

        def test_117_create_rlc_boundary(self):
            example_project = os.path.join(local_path, "example_models", test_subfolder, "Galileo.aedb")
            target_path = os.path.join(self.local_scratch.path, "Galileo_115.aedb")
            if not os.path.exists(self.local_scratch.path):
                os.mkdir(self.local_scratch.path)
            self.local_scratch.copyfolder(example_project, target_path)
            edb = Edb(target_path, edbversion=desktop_version)
            pins = edb.core_components.get_pin_from_component("U2A5", "V1P5_S0")
            ref_pins = edb.core_components.get_pin_from_component("U2A5", "GND")
            assert edb.core_hfss.create_rlc_boundary_on_pins(
                pins[0], ref_pins[0], rvalue=1.05, lvalue=1.05e-12, cvalue=1.78e-13
            )
            edb.close_edb()

        def test_118_configure_hfss_analysis_setup_enforce_causality(self):
            source_path = os.path.join(local_path, "example_models", test_subfolder, "lam_for_top_place_no_setups.aedb")
            target_path = os.path.join(self.local_scratch.path, "lam_for_top_place_no_setups_t116.aedb")
            if not os.path.exists(self.local_scratch.path):
                os.mkdir(self.local_scratch.path)
            self.local_scratch.copyfolder(source_path, target_path)
            edb = Edb(target_path)
            assert len(list(edb.active_cell.SimulationSetups)) == 0
            sim_config = SimulationConfiguration()
            sim_config.enforce_causality = False
            assert sim_config.do_lambda_refinement
            sim_config.mesh_sizefactor = 0.1
            assert sim_config.mesh_sizefactor == 0.1
            assert not sim_config.do_lambda_refinement
            sim_config.start_freq = "1GHz"
            edb.core_hfss.configure_hfss_analysis_setup(sim_config)
            assert len(list(edb.active_cell.SimulationSetups)) == 1
            setup = list(edb.active_cell.SimulationSetups)[0]
            ssi = setup.GetSimSetupInfo()
            assert len(list(ssi.SweepDataList)) == 1
            sweep = list(ssi.SweepDataList)[0]
            assert not sweep.EnforceCausality

        def test_119_add_hfss_config(self):
            source_path = os.path.join(local_path, "example_models", test_subfolder, "Galileo.aedb")
            target_path = os.path.join(self.local_scratch.path, "test_0117.aedb")
            self.local_scratch.copyfolder(source_path, target_path)
            edb = Edb(target_path)
            sim_setup = SimulationConfiguration()
            sim_setup.mesh_sizefactor = 1.9
            assert not sim_setup.do_lambda_refinement
            edb.core_hfss.configure_hfss_analysis_setup(sim_setup)
            if is_ironpython:
                mesh_size_factor = (
                    list(edb.active_cell.SimulationSetups)[0]
                    .GetSimSetupInfo()
                    .SimulationSettings.InitialMeshSettings.MeshSizefactor
                )
            else:
                mesh_size_factor = (
                    list(edb.active_cell.SimulationSetups)[0]
                    .GetSimSetupInfo()
                    .get_SimulationSettings()
                    .get_InitialMeshSettings()
                    .get_MeshSizefactor()
                )
            assert mesh_size_factor == 1.9

        def test_120_edb_create_port(self):
            edb = Edb(
                edbpath=os.path.join(local_path, "example_models", "edb_edge_ports.aedb"),
                edbversion=desktop_version,
            )
            prim_1_id = [i.id for i in edb.core_primitives.primitives if i.net_name == "trace_2"][0]
            assert edb.core_hfss.create_edge_port_vertical(prim_1_id, ["-66mm", "-4mm"], "port_ver")

            prim_2_id = [i.id for i in edb.core_primitives.primitives if i.net_name == "trace_3"][0]
            assert edb.core_hfss.create_edge_port_horizontal(
                prim_1_id, ["-60mm", "-4mm"], prim_2_id, ["-59mm", "-4mm"], "port_hori", 30, "Lower"
            )
            assert edb.core_hfss.get_ports_number() == 2
            port_ver = edb.core_hfss.excitations["port_ver"]
            assert port_ver.hfss_type == "Gap"
            assert isinstance(port_ver.horizontal_extent_factor, float)
            assert isinstance(port_ver.vertical_extent_factor, float)
            assert port_ver.pec_launch_width
            p = edb.core_primitives.create_trace(
                path_list=[["-40mm", "-10mm"], ["-30mm", "-10mm"]],
                layer_name="TOP",
                net_name="SIGP",
                width="0.1mm",
                start_cap_style="Flat",
                end_cap_style="Flat",
            )

            n = edb.core_primitives.create_trace(
                path_list=[["-40mm", "-10.2mm"], ["-30mm", "-10.2mm"]],
                layer_name="TOP",
                net_name="SIGN",
                width="0.1mm",
                start_cap_style="Flat",
                end_cap_style="Flat",
            )
            assert edb.core_hfss.create_wave_port(p.id, ["-30mm", "-10mm"], "p_port")

            assert edb.core_hfss.create_differential_wave_port(
                p.id,
                ["-40mm", "-10mm"],
                n.id,
                ["-40mm", "-10.2mm"],
                horizontal_extent_factor=8,
            )
            assert not edb.are_port_reference_terminals_connected()
            edb.close_edb()

        def test_121_insert_layer(self):
            layers = self.edbapp.core_stackup.stackup_layers
            layer = layers.insert_layer_above("NewLayer", "TOP", "copper", "air", "10um", 0, roughness_enabled=True)
            assert layer.name in layers.layers

        def test_122_build_hfss_project_from_config_file(self):
            cfg_file = os.path.join(os.path.dirname(self.edbapp.edbpath), "test.cfg")
            with open(cfg_file, "w") as f:
                f.writelines("SolverType = 'Hfss3dLayout'\n")
                f.writelines("PowerNets = ['GND']\n")
                f.writelines("Components = ['U2A5', 'U1B5']")

            sim_config = SimulationConfiguration(cfg_file)
            assert self.edbapp.build_simulation_project(sim_config)

        def test_123_set_all_antipad_values(self):
            source_path = os.path.join(local_path, "example_models", test_subfolder, "Galileo.aedb")
            target_path = os.path.join(self.local_scratch.path, "test_0120.aedb")
            self.local_scratch.copyfolder(source_path, target_path)
            edbapp = Edb(target_path, edbversion=desktop_version)
            assert edbapp.core_padstack.set_all_antipad_value(0.0)
            edbapp.close_edb()

        def test_124_stackup(self):
            source_path = os.path.join(local_path, "example_models", test_subfolder, "Galileo.aedb")
            target_path = os.path.join(self.local_scratch.path, "test_0122.aedb")
            self.local_scratch.copyfolder(source_path, target_path)
            edbapp = Edb(target_path, edbversion=desktop_version)
            assert isinstance(edbapp.stackup.layers, dict)
            assert isinstance(edbapp.stackup.signal_layers, dict)
            assert isinstance(edbapp.stackup.stackup_layers, dict)
            assert isinstance(edbapp.stackup.non_stackup_layers, dict)
            assert not edbapp.stackup["Outline"].is_stackup_layer
            assert edbapp.stackup["TOP"].conductivity
            assert edbapp.stackup["UNNAMED_002"].permittivity
            assert edbapp.stackup.add_layer("new_layer")
            new_layer = edbapp.stackup["new_layer"]
            assert new_layer.is_stackup_layer
            new_layer.name = "renamed_layer"
            assert new_layer.name == "renamed_layer"
            rename_layer = edbapp.stackup["renamed_layer"]
            rename_layer.thickness = 50e-6
            assert rename_layer.thickness == 50e-6
            rename_layer.etch_factor = 0
            rename_layer.etch_factor = 2
            assert rename_layer.etch_factor == 2
            assert rename_layer.material
            assert rename_layer.type
            assert rename_layer.dielectric_fill

            rename_layer.roughness_enabled = True
            assert rename_layer.roughness_enabled
            rename_layer.roughness_enabled = False
            assert not rename_layer.roughness_enabled
            assert rename_layer.assign_roughness_model("groisse", groisse_roughness="2um")
            assert rename_layer.assign_roughness_model(apply_on_surface="top")
            assert rename_layer.assign_roughness_model(apply_on_surface="bottom")
            assert rename_layer.assign_roughness_model(apply_on_surface="side")
            assert edbapp.stackup.add_layer("new_above", "TOP", "insert_above")
            assert edbapp.stackup.add_layer("new_below", "TOP", "insert_below")
            assert edbapp.stackup.add_layer("new_bottom", "TOP", "add_on_bottom", "dielectric")
            assert edbapp.stackup.remove_layer("new_bottom")
            assert "new_bottom" not in edbapp.stackup.layers

            assert edbapp.stackup["TOP"].color
            edbapp.stackup["TOP"].color = [0, 120, 0]
            assert edbapp.stackup["TOP"].color == (0, 120, 0)
            edbapp.stackup["TOP"].transparency = 10
            assert edbapp.stackup["TOP"].transparency == 10
            edbapp.close_edb()

        @pytest.mark.skipif(is_ironpython, reason="Requires Pandas")
        def test_125_stackup(self):
            edbapp = Edb(edbversion=desktop_version)
            assert edbapp.stackup.add_layer("TOP", None, "add_on_top", material="iron")
            assert edbapp.stackup.import_stackup(
                os.path.join(local_path, "example_models", test_subfolder, "galileo_stackup.csv")
            )
            assert "TOP" in edbapp.stackup.layers.keys()
            assert edbapp.stackup.layers["TOP"].material == "COPPER"
            assert edbapp.stackup.layers["TOP"].thickness == 6e-5
            export_stackup_path = os.path.join(self.local_scratch.path, "export_galileo_stackup.csv")
            assert edbapp.stackup.export_stackup(export_stackup_path)
            assert os.path.exists(export_stackup_path)
            edbapp.close_edb()

        @pytest.mark.skipif(is_ironpython, reason="Requires Numpy")
        def test_126_comp_def(self):
            source_path = os.path.join(local_path, "example_models", test_subfolder, "Galileo.aedb")
            target_path = os.path.join(self.local_scratch.path, "test_0123.aedb")
            self.local_scratch.copyfolder(source_path, target_path)
            edbapp = Edb(target_path, edbversion=desktop_version)
            assert edbapp.core_components.components
            assert edbapp.core_components.definitions
            comp_def = edbapp.core_components.definitions["G83568-001"]
            assert comp_def
            comp_def.part_name = "G83568-001x"
            assert comp_def.part_name == "G83568-001x"
            assert len(comp_def.components) > 0
            cap = edbapp.core_components.definitions["602431-005"]
            assert cap.type == "Capacitor"
            cap.type = "Resistor"
            assert cap.type == "Resistor"

            export_path = os.path.join(self.local_scratch.path, "comp_definition.csv")
            assert edbapp.core_components.export_definition(export_path)
            assert edbapp.core_components.import_definition(export_path)

            assert edbapp.core_components.definitions["602431-005"].assign_rlc_model(1, 2, 3)
            sparam_path = os.path.join(local_path, "example_models", test_subfolder, "GRM32_DC0V_25degC_series.s2p")
            assert edbapp.core_components.definitions["602433-026"].assign_s_param_model(sparam_path)
            spice_path = os.path.join(local_path, "example_models", test_subfolder, "GRM32_DC0V_25degC.mod")
            assert edbapp.core_components.definitions["602433-038"].assign_spice_model(spice_path)
            edbapp.close_edb()

        def test_127_material(self):
            source_path = os.path.join(local_path, "example_models", test_subfolder, "Galileo.aedb")
            target_path = os.path.join(self.local_scratch.path, "test_0122.aedb")
            self.local_scratch.copyfolder(source_path, target_path)
            edbapp = Edb(target_path, edbversion=desktop_version)
            assert isinstance(edbapp.materials.materials, dict)
            edbapp.materials["FR4_epoxy"].conductivity = 1
            assert edbapp.materials["FR4_epoxy"].conductivity == 1
            edbapp.materials["FR4_epoxy"].permittivity = 1
            assert edbapp.materials["FR4_epoxy"].permittivity == 1
            edbapp.materials["FR4_epoxy"].loss_tangent = 1
            assert edbapp.materials["FR4_epoxy"].loss_tangent == 1
            edbapp.materials.add_conductor_material("new_conductor", 1)
            assert not edbapp.materials.add_conductor_material("new_conductor", 1)
            edbapp.materials.add_dielectric_material("new_dielectric", 1, 2)
            assert not edbapp.materials.add_dielectric_material("new_dielectric", 1, 2)
            edbapp.materials["FR4_epoxy"].magnetic_loss_tangent = 0.01
            assert edbapp.materials["FR4_epoxy"].magnetic_loss_tangent == 0.01
            edbapp.materials["FR4_epoxy"].youngs_modulus = 5000
            assert edbapp.materials["FR4_epoxy"].youngs_modulus == 5000
            edbapp.materials["FR4_epoxy"].mass_density = 50

            assert edbapp.materials["FR4_epoxy"].mass_density == 50
            edbapp.materials["FR4_epoxy"].thermal_conductivity = 1e-5

            assert edbapp.materials["FR4_epoxy"].thermal_conductivity == 1e-5
            edbapp.materials["FR4_epoxy"].thermal_expansion_coefficient = 1e-7

            assert edbapp.materials["FR4_epoxy"].thermal_expansion_coefficient == 1e-7
            edbapp.materials["FR4_epoxy"].poisson_ratio = 1e-3
            assert edbapp.materials["FR4_epoxy"].poisson_ratio == 1e-3
            assert edbapp.materials["new_conductor"]
            assert edbapp.materials.duplicate("FR4_epoxy", "FR41")
            assert edbapp.materials["FR41"]
            assert edbapp.materials["FR4_epoxy"].conductivity == edbapp.materials["FR41"].conductivity
            assert edbapp.materials["FR4_epoxy"].permittivity == edbapp.materials["FR41"].permittivity
            assert edbapp.materials["FR4_epoxy"].loss_tangent == edbapp.materials["FR41"].loss_tangent
            assert edbapp.materials["FR4_epoxy"].magnetic_loss_tangent == edbapp.materials["FR41"].magnetic_loss_tangent
            assert edbapp.materials["FR4_epoxy"].youngs_modulus == edbapp.materials["FR41"].youngs_modulus
            assert edbapp.materials["FR4_epoxy"].mass_density == edbapp.materials["FR41"].mass_density
            assert edbapp.materials["FR4_epoxy"].thermal_conductivity == edbapp.materials["FR41"].thermal_conductivity
            assert (
                edbapp.materials["FR4_epoxy"].thermal_expansion_coefficient
                == edbapp.materials["FR41"].thermal_expansion_coefficient
            )
            assert edbapp.materials["FR4_epoxy"].poisson_ratio == edbapp.materials["FR41"].poisson_ratio
            assert edbapp.materials.add_debye_material("My_Debye2", 5, 3, 0.02, 0.05, 1e5, 1e9)
            assert edbapp.materials.add_djordjevicsarkar_material("MyDjord2", 3.3, 0.02, 3.3)
            freq = [0, 2, 3, 4, 5, 6]
            rel_perm = [1e9, 1.1e9, 1.2e9, 1.3e9, 1.5e9, 1.6e9]
            loss_tan = [0.025, 0.026, 0.027, 0.028, 0.029, 0.030]
            assert edbapp.materials.add_multipole_debye_material("My_MP_Debye2", freq, rel_perm, loss_tan)
            edbapp.close_edb()
            edbapp = Edb(edbversion=desktop_version)
            assert "air" in edbapp.materials.materials
            edbapp.close_edb()

        def test_128_microvias(self):
            source_path = os.path.join(local_path, "example_models", test_subfolder, "padstacks.aedb")
            target_path = os.path.join(self.local_scratch.path, "test_128_microvias.aedb")
            self.local_scratch.copyfolder(source_path, target_path)
            edbapp = Edb(target_path, edbversion=desktop_version)
            assert edbapp.core_padstack.padstacks["Padstack_Circle"].convert_to_3d_microvias(False)
            assert edbapp.core_padstack.padstacks["Padstack_Rectangle"].convert_to_3d_microvias(
                False, hole_wall_angle=10
            )
            assert edbapp.core_padstack.padstacks["Padstack_Polygon_p12"].convert_to_3d_microvias(False)
            edbapp.close_edb()

        def test_129_split_microvias(self):
            edbapp = Edb(self.target_path4, edbversion=desktop_version)
            assert len(edbapp.core_padstack.padstacks["C4_POWER_1"].split_to_microvias()) > 0
            edbapp.close_edb()

        def test_129_hfss_simulation_setup(self):
            setup1 = self.edbapp.create_hfss_setup("setup1")
            assert setup1.set_solution_single_frequency()
            assert setup1.set_solution_multi_frequencies()
            assert setup1.set_solution_broadband()

            setup1.hfss_solver_settings.enhanced_low_freq_accuracy = True
            setup1.hfss_solver_settings.order_basis = "first"
            setup1.hfss_solver_settings.relative_residual = 0.0002
            setup1.hfss_solver_settings.use_shell_elements = True

            hfss_solver_settings = self.edbapp.setups["setup1"].hfss_solver_settings
            assert hfss_solver_settings.order_basis == "first"
            assert hfss_solver_settings.relative_residual == 0.0002
            assert hfss_solver_settings.solver_type
            assert hfss_solver_settings.enhanced_low_freq_accuracy
            assert not hfss_solver_settings.use_shell_elements

            assert setup1.adaptive_settings.add_adaptive_frequency_data("5GHz", 8, "0.01")
            assert setup1.adaptive_settings.adaptive_frequency_data_list
            setup1.adaptive_settings.adapt_type = "kBroadband"
            setup1.adaptive_settings.basic = False
            setup1.adaptive_settings.max_refinement = 1000001
            setup1.adaptive_settings.max_refine_per_pass = 20
            setup1.adaptive_settings.min_passes = 2
            setup1.adaptive_settings.save_fields = True
            setup1.adaptive_settings.save_rad_field_only = True
            setup1.adaptive_settings.use_convergence_matrix = True
            setup1.adaptive_settings.use_max_refinement = True

            assert self.edbapp.setups["setup1"].adaptive_settings.adapt_type == "kBroadband"
            assert not self.edbapp.setups["setup1"].adaptive_settings.basic
            assert self.edbapp.setups["setup1"].adaptive_settings.max_refinement == 1000001
            assert self.edbapp.setups["setup1"].adaptive_settings.max_refine_per_pass == 20
            assert self.edbapp.setups["setup1"].adaptive_settings.min_passes == 2
            assert self.edbapp.setups["setup1"].adaptive_settings.save_fields
            assert self.edbapp.setups["setup1"].adaptive_settings.save_rad_field_only
            # assert adaptive_settings.use_convergence_matrix
            assert self.edbapp.setups["setup1"].adaptive_settings.use_max_refinement

            setup1.defeature_settings.defeature_abs_length = "1um"
            setup1.defeature_settings.defeature_ratio = 1e-5
            setup1.defeature_settings.healing_option = 0
            setup1.defeature_settings.model_type = 1
            setup1.defeature_settings.remove_floating_geometry = True
            setup1.defeature_settings.small_void_area = 0.1
            setup1.defeature_settings.union_polygons = False
            setup1.defeature_settings.use_defeature = False
            setup1.defeature_settings.use_defeature_abs_length = True

            defeature_settings = self.edbapp.setups["setup1"].defeature_settings
            assert defeature_settings.defeature_abs_length == "1um"
            assert defeature_settings.defeature_ratio == 1e-5
            # assert defeature_settings.healing_option == 0
            # assert defeature_settings.model_type == 1
            assert defeature_settings.remove_floating_geometry
            assert defeature_settings.small_void_area == 0.1
            assert not defeature_settings.union_polygons
            assert not defeature_settings.use_defeature
            assert defeature_settings.use_defeature_abs_length

            via_settings = setup1.via_settings
            via_settings.via_density = 1
            via_settings.via_material = "pec"
            via_settings.via_num_sides = 8
            via_settings.via_style = "kNum25DViaStyle"

            via_settings = self.edbapp.setups["setup1"].via_settings
            assert via_settings.via_density == 1
            assert via_settings.via_material == "pec"
            assert via_settings.via_num_sides == 8
            # assert via_settings.via_style == "kNum25DViaStyle"

            advanced_mesh_settings = setup1.advanced_mesh_settings
            advanced_mesh_settings.layer_snap_tol = "1e-6"
            advanced_mesh_settings.mesh_display_attributes = "#0000001"
            advanced_mesh_settings.replace_3d_triangles = False

            advanced_mesh_settings = self.edbapp.setups["setup1"].advanced_mesh_settings
            assert advanced_mesh_settings.layer_snap_tol == "1e-6"
            assert advanced_mesh_settings.mesh_display_attributes == "#0000001"
            assert not advanced_mesh_settings.replace_3d_triangles

            curve_approx_settings = setup1.curve_approx_settings
            curve_approx_settings.arc_angle = "15deg"
            curve_approx_settings.arc_to_chord_error = "0.1"
            curve_approx_settings.max_arc_points = 12
            curve_approx_settings.start_azimuth = "1"
            curve_approx_settings.use_arc_to_chord_error = True

            curve_approx_settings = self.edbapp.setups["setup1"].curve_approx_settings
            assert curve_approx_settings.arc_to_chord_error == "0.1"
            assert curve_approx_settings.max_arc_points == 12
            assert curve_approx_settings.start_azimuth == "1"
            assert curve_approx_settings.use_arc_to_chord_error

            dcr_settings = setup1.dcr_settings
            dcr_settings.conduction_max_passes = 11
            dcr_settings.conduction_min_converged_passes = 2
            dcr_settings.conduction_min_passes = 2
            dcr_settings.conduction_per_error = 2.0
            dcr_settings.conduction_per_refine = 33.0

            dcr_settings = self.edbapp.setups["setup1"].dcr_settings
            assert dcr_settings.conduction_max_passes == 11
            assert dcr_settings.conduction_min_converged_passes == 2
            assert dcr_settings.conduction_min_passes == 2
            assert dcr_settings.conduction_per_error == 2.0
            assert dcr_settings.conduction_per_refine == 33.0

            hfss_port_settings = setup1.hfss_port_settings
            hfss_port_settings.max_delta_z0 = 0.5
            assert hfss_port_settings.max_delta_z0 == 0.5
            hfss_port_settings.max_triangles_wave_port = 1000
            assert hfss_port_settings.max_triangles_wave_port == 1000
            hfss_port_settings.min_triangles_wave_port = 200
            assert hfss_port_settings.min_triangles_wave_port == 200
            hfss_port_settings.set_triangles_wave_port = True
            assert hfss_port_settings.set_triangles_wave_port

            # mesh_operations = setup1.mesh_operations
            # setup1.mesh_operations = mesh_operations

            setup1.add_frequency_sweep(
                "sweep1",
                frequency_sweep=[
                    ["linear count", "0", "1kHz", 1],
                    ["log scale", "1kHz", "0.1GHz", 10],
                    ["linear scale", "0.1GHz", "10GHz", "0.1GHz"],
                ],
            )
            assert "sweep1" in setup1.frequency_sweeps
            sweep1 = setup1.frequency_sweeps["sweep1"]
            sweep1.adaptive_sampling = True
            assert sweep1.adaptive_sampling

            self.edbapp.setups["setup1"].name = "setup1a"
            assert "setup1" not in self.edbapp.setups
            assert "setup1a" in self.edbapp.setups

            mop = self.edbapp.setups["setup1a"].add_length_mesh_operation({"GND": ["TOP", "BOTTOM"]}, "m1")
            assert mop.name == "m1"
            assert mop.max_elements == "1000"
            assert mop.restrict_max_elements
            assert mop.restrict_length
            assert mop.max_length == "1mm"

            mop.name = "m2"
            mop.max_elements = 2000
            mop.restrict_max_elements = False
            mop.restrict_length = False
            mop.max_length = "2mm"

            assert mop.name == "m2"
            assert mop.max_elements == "2000"
            assert not mop.restrict_max_elements
            assert not mop.restrict_length
            assert mop.max_length == "2mm"

            mop = self.edbapp.setups["setup1a"].add_skin_depth_mesh_operation({"GND": ["TOP", "BOTTOM"]})
            assert mop.max_elements == "1000"
            assert mop.restrict_max_elements
            assert mop.skin_depth == "1um"
            assert mop.surface_triangle_length == "1mm"
            assert mop.number_of_layer_elements == "2"

            mop.skin_depth = "5um"
            mop.surface_triangle_length = "2mm"
            mop.number_of_layer_elements = "3"

            assert mop.skin_depth == "5um"
            assert mop.surface_triangle_length == "2mm"
            assert mop.number_of_layer_elements == "3"

        def test_130_siwave_dc_simulation_setup(self):
            setup1 = self.edbapp.create_siwave_dc_setup("DC1")
            assert setup1.name == "DC1"
            assert not setup1.compute_inductance
            assert setup1.contact_radius == "0.1mm"
            assert setup1.dc_slider_position == 1
            assert setup1.enabled
            assert setup1.energy_error == 3.0
            assert setup1.max_init_mesh_edge_length == "2.5mm"
            assert setup1.max_num_pass == 5
            assert setup1.min_num_pass == 1
            assert setup1.mesh_bondwires
            assert setup1.mesh_vias
            assert setup1.min_plane_area == "0.25mm2"
            assert setup1.min_void_area == "0.01mm2"
            assert setup1.num_bondwire_sides == 8
            assert setup1.num_via_sides == 8
            assert setup1.percent_local_refinement == 20.0
            assert setup1.perform_adaptive_refinement
            assert setup1.plot_jv
            assert not setup1.refine_bondwires
            assert not setup1.refine_vias
            setup1.name = "DC2"
            setup1.compute_inductance = True
            setup1.contact_radius = "0.2mm"
            setup1.dc_slider_position = 2
            setup1.energy_error = 2.0
            setup1.max_init_mesh_edge_length = "5.5mm"
            setup1.max_num_pass = 3
            setup1.min_num_pass = 2
            setup1.mesh_bondwires = False
            setup1.mesh_vias = False
            assert not setup1.mesh_bondwires
            assert not setup1.mesh_vias
            setup1.min_plane_area = "0.5mm2"
            setup1.min_void_area = "0.021mm2"
            setup1.num_bondwire_sides = 6
            setup1.num_via_sides = 10
            setup1.percent_local_refinement = 10.0
            setup1.perform_adaptive_refinement = False
            setup1.plot_jv = False
            setup1.refine_bondwires = True
            setup1.refine_vias = True

            assert setup1.name == "DC2"
            assert setup1.compute_inductance
            assert setup1.contact_radius == "0.2mm"
            assert setup1.dc_slider_position == 2
            assert setup1.energy_error == 2.0
            assert setup1.max_init_mesh_edge_length == "5.5mm"
            assert setup1.max_num_pass == 3
            assert setup1.min_num_pass == 2
            assert setup1.mesh_bondwires
            assert setup1.mesh_vias
            assert setup1.min_plane_area == "0.5mm2"
            assert setup1.min_void_area == "0.021mm2"
            assert setup1.num_bondwire_sides == 6
            assert setup1.num_via_sides == 10
            assert setup1.percent_local_refinement == 10.0
            assert not setup1.perform_adaptive_refinement
            assert not setup1.plot_jv
            assert setup1.refine_bondwires
            assert setup1.refine_vias

        def test_131_siwave_ac_simulation_setup(self):
            setup1 = self.edbapp.create_siwave_syz_setup("AC1")
            assert setup1.name == "AC1"
            assert setup1.enabled
            sweep = setup1.add_frequency_sweep(
                "sweep1",
                frequency_sweep=[
                    ["linear count", "0", "1kHz", 1],
                    ["log scale", "1kHz", "0.1GHz", 10],
                    ["linear scale", "0.1GHz", "10GHz", "0.1GHz"],
                ],
            )
            assert "sweep1" in setup1.frequency_sweeps
            assert "0" in sweep.frequencies
            assert not sweep.adaptive_sampling
            assert not sweep.adv_dc_extrapolation
            assert sweep.auto_s_mat_only_solve
            assert not sweep.enforce_causality
            assert not sweep.enforce_dc_and_causality
            assert sweep.enforce_passivity
            assert sweep.freq_sweep_type == "kInterpolatingSweep"
            assert sweep.interp_use_full_basis
            assert sweep.interp_use_port_impedance
            assert sweep.interp_use_prop_const
            assert sweep.max_solutions == 250
            assert sweep.min_freq_s_mat_only_solve == "1MHz"
            assert not sweep.min_solved_freq
            assert sweep.passivity_tolerance == 0.0001
            assert sweep.relative_s_error == 0.005
            assert not sweep.save_fields
            assert not sweep.save_rad_fields_only
            assert not sweep.use_q3d_for_dc

            sweep.adaptive_sampling = True
            sweep.adv_dc_extrapolation = True
            sweep.auto_s_mat_only_solve = False
            sweep.enforce_causality = True
            sweep.enforce_dc_and_causality = True
            sweep.enforce_passivity = False
            sweep.freq_sweep_type = "kDiscreteSweep"
            sweep.interp_use_full_basis = False
            sweep.interp_use_port_impedance = False
            sweep.interp_use_prop_const = False
            sweep.max_solutions = 200
            sweep.min_freq_s_mat_only_solve = "2MHz"
            sweep.min_solved_freq = "1Hz"
            sweep.passivity_tolerance = 0.0002
            sweep.relative_s_error = 0.004
            sweep.save_fields = True
            sweep.save_rad_fields_only = True
            sweep.use_q3d_for_dc = True

            assert sweep.adaptive_sampling
            assert sweep.adv_dc_extrapolation
            assert not sweep.auto_s_mat_only_solve
            assert sweep.enforce_causality
            assert sweep.enforce_dc_and_causality
            assert not sweep.enforce_passivity
            assert sweep.freq_sweep_type == "kDiscreteSweep"
            assert not sweep.interp_use_full_basis
            assert not sweep.interp_use_port_impedance
            assert not sweep.interp_use_prop_const
            assert sweep.max_solutions == 200
            assert sweep.min_freq_s_mat_only_solve == "2MHz"
            assert sweep.min_solved_freq == "1Hz"
            assert sweep.passivity_tolerance == 0.0002
            assert sweep.relative_s_error == 0.004
            assert sweep.save_fields
            assert sweep.save_rad_fields_only
            assert sweep.use_q3d_for_dc

            assert setup1.automatic_mesh
            assert setup1.enabled
            assert setup1.dc_settings
            assert setup1.ignore_non_functional_pads
            assert setup1.include_coplane_coupling
            assert setup1.include_fringe_coupling
            assert not setup1.include_infinite_ground
            assert not setup1.include_inter_plane_coupling
            assert setup1.include_split_plane_coupling
            assert setup1.include_trace_coupling
            assert not setup1.include_vi_sources
            assert setup1.infinite_ground_location == "0"
            assert setup1.max_coupled_lines == 12
            assert setup1.mesh_frequency == "4GHz"
            assert setup1.min_pad_area_to_mesh == "1mm2"
            assert setup1.min_plane_area_to_mesh == "6.25e-6mm2"
            assert setup1.min_void_area == "2mm2"
            assert setup1.name == "AC1"
            assert setup1.perform_erc
            assert setup1.pi_slider_postion == 1
            assert setup1.si_slider_postion == 1
            assert not setup1.return_current_distribution
            assert setup1.snap_length_threshold == "2.5um"
            assert setup1.use_si_settings
            assert setup1.use_custom_settings
            assert setup1.xtalk_threshold == "-34"

            setup1.automatic_mesh = False
            setup1.enabled = False
            setup1.ignore_non_functional_pads = False
            setup1.include_coplane_coupling = False
            setup1.include_fringe_coupling = False
            setup1.include_infinite_ground = True
            setup1.include_inter_plane_coupling = True
            setup1.include_split_plane_coupling = False
            setup1.include_trace_coupling = False
            assert setup1.use_custom_settings
            setup1.include_vi_sources = True
            setup1.infinite_ground_location = "0.1"
            setup1.max_coupled_lines = 10
            setup1.mesh_frequency = "3GHz"
            setup1.min_pad_area_to_mesh = "2mm2"
            setup1.min_plane_area_to_mesh = "5.25e-6mm2"
            setup1.min_void_area = "1mm2"
            setup1.name = "AC2"
            setup1.perform_erc = False
            setup1.pi_slider_postion = 0
            setup1.si_slider_postion = 2
            setup1.return_current_distribution = True
            setup1.snap_length_threshold = "3.5um"
            setup1.use_si_settings = False
            assert not setup1.use_custom_settings
            setup1.xtalk_threshold = "-44"

            assert not setup1.automatic_mesh
            assert not setup1.enabled
            assert not setup1.ignore_non_functional_pads
            assert not setup1.include_coplane_coupling
            assert not setup1.include_fringe_coupling
            assert setup1.include_infinite_ground
            assert setup1.include_inter_plane_coupling
            assert not setup1.include_split_plane_coupling
            assert not setup1.include_trace_coupling
            assert setup1.include_vi_sources
            assert setup1.infinite_ground_location == "0.1"
            assert setup1.max_coupled_lines == 10
            assert setup1.mesh_frequency == "3GHz"
            assert setup1.min_pad_area_to_mesh == "2mm2"
            assert setup1.min_plane_area_to_mesh == "5.25e-6mm2"
            assert setup1.min_void_area == "1mm2"
            assert setup1.name == "AC2"
            assert not setup1.perform_erc
            assert setup1.pi_slider_postion == 0
            assert setup1.si_slider_postion == 2
            assert setup1.return_current_distribution
            assert setup1.snap_length_threshold == "3.5um"
            assert not setup1.use_si_settings
            assert setup1.xtalk_threshold == "-44"

        def test_132_via_plating_ratio_check(self):
            assert self.edbapp.core_padstack.check_and_fix_via_plating()
