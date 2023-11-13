import json
import os

# Setup paths for module imports
# Import required modules
import sys

import pytest

from pyaedt import Edb
from pyaedt import settings

if not settings.use_grpc_edb_api:
    from pyedb.legacy.edb_core.components import resistor_value_parser
    from pyedb.legacy.edb_core.edb_data.edbvalue import EdbValue
    from pyedb.legacy.edb_core.edb_data.simulation_configuration import SimulationConfiguration
    from pyedb.legacy.edb_core.edb_data.sources import Source
else:
    raise Exception("gRPC Not yet available.")

from pyaedt.generic.constants import RadiationBoxType
from pyaedt.generic.general_methods import check_numeric_equivalence

test_project_name = "ANSYS-HSD_V1"
bom_example = "bom_example.csv"
# from _unittest.conftest import is_ironpython
from _unittest.conftest import config
from _unittest.conftest import desktop_version
from _unittest.conftest import local_path
from _unittest.conftest import settings

from pyaedt.generic.constants import SolverType
from pyaedt.generic.constants import SourceType

# try:
#     import pytest
# except ImportError:  # pragma: no cover
#     import _unittest_ironpython.conf_unittest as pytest

test_subfolder = "TEDB"

MATERIALS = """
$begin 'Polyflon CuFlon (tm)'
  $begin 'AttachedData'
    $begin 'MatAppearanceData'
      property_data='appearance_data'
      Red=230
      Green=225
      Blue=220
    $end 'MatAppearanceData'
  $end 'AttachedData'
  simple('permittivity', 2.1)
  simple('dielectric_loss_tangent', 0.00045)
  ModTime=1499970477
$end 'Polyflon CuFlon (tm)'
$begin 'Water(@360K)'
  $begin 'MaterialDef'
    $begin 'Water(@360K)'
      CoordinateSystemType='Cartesian'
      BulkOrSurfaceType=1
      $begin 'PhysicsTypes'
        set('Thermal')
      $end 'PhysicsTypes'
      $begin 'AttachedData'
        $begin 'MatAppearanceData'
          property_data='appearance_data'
          Red=0
          Green=128
          Blue=255
          Transparency=0.8
        $end 'MatAppearanceData'
      $end 'AttachedData'
      thermal_conductivity='0.6743'
      mass_density='967.4'
      specific_heat='4206'
      thermal_expansion_coeffcient='0.0006979'
      $begin 'thermal_material_type'
        property_type='ChoiceProperty'
        Choice='Fluid'
      $end 'thermal_material_type'
      $begin 'clarity_type'
        property_type='ChoiceProperty'
        Choice='Transparent'
      $end 'clarity_type'
      material_refractive_index='1.333'
      diffusivity='1.657e-007'
      molecular_mass='0.018015'
      viscosity='0.000324'
      ModTime=1592011950
    $end 'Water(@360K)'
  $end 'MaterialDef'
$end 'Water(@360K)'
"""


@pytest.fixture(scope="class")
def edbapp(add_edb):
    app = add_edb(test_project_name, subfolder=test_subfolder)
    return app


@pytest.fixture(scope="class", autouse=True)
def target_path(local_scratch):
    example_project = os.path.join(local_path, "example_models", test_subfolder, "example_package.aedb")
    target_path = os.path.join(local_scratch.path, "example_package.aedb")
    local_scratch.copyfolder(example_project, target_path)
    return target_path


@pytest.fixture(scope="class", autouse=True)
def target_path2(local_scratch):
    example_project2 = os.path.join(local_path, "example_models", test_subfolder, "simple.aedb")
    target_path2 = os.path.join(local_scratch.path, "simple_00.aedb")
    local_scratch.copyfolder(example_project2, target_path2)
    return target_path2


@pytest.fixture(scope="class", autouse=True)
def target_path4(local_scratch):
    example_project4 = os.path.join(local_path, "example_models", test_subfolder, "Package.aedb")
    target_path4 = os.path.join(local_scratch.path, "Package_00.aedb")
    local_scratch.copyfolder(example_project4, target_path4)
    return target_path4


@pytest.fixture(scope="module", autouse=True)
def desktop():
    return


@pytest.mark.skipif(config["skip_edb"], reason="Skipping on IPY and optionally on CPython.")
class TestClass:
    @pytest.fixture(autouse=True)
    def init(self, edbapp, local_scratch, target_path, target_path2, target_path4):
        self.edbapp = edbapp
        self.local_scratch = local_scratch
        self.target_path = target_path
        self.target_path2 = target_path2
        self.target_path4 = target_path4

    def test_000_export_ipc2581(self):
        source_path = os.path.join(local_path, "example_models", test_subfolder, "ANSYS-HSD_V1_cut.aedb")
        target_path = os.path.join(self.local_scratch.path, "ANSYS-HSD_V1_ipc.aedb")
        self.local_scratch.copyfolder(source_path, target_path)
        edbapp = Edb(target_path, edbversion=desktop_version)
        ipc_path = os.path.join(self.local_scratch.path, "test.xml")
        edbapp.export_to_ipc2581(ipc_path)
        assert os.path.exists(ipc_path)

        # Export should be made with units set to default -millimeter-.
        edbapp.export_to_ipc2581(ipc_path, "mm")
        assert os.path.exists(ipc_path)
        edbapp.close()

    def test_001_find_by_name(self):
        comp = self.edbapp.components.get_component_by_name("J1")
        assert comp is not None
        pin = self.edbapp.components.get_pin_from_component("J1", pinName="1")
        assert pin is not False
        parameters = self.edbapp.padstacks.get_pad_parameters(
            pin[0], "1_Top", self.edbapp.padstacks.pad_type.RegularPad
        )
        assert isinstance(parameters[1], list)
        assert isinstance(parameters[0], int)

    def test_002_get_vias_from_nets(self):
        assert self.edbapp.padstacks.get_via_instance_from_net("GND")
        assert not self.edbapp.padstacks.get_via_instance_from_net(["GND2"])

    def test_003_create_coax_port_on_component(self):
        assert self.edbapp.hfss.create_coax_port_on_component("U1", "DDR4_DQS0_P")
        coax_port = self.edbapp.components["U6"].pins["R3"].create_coax_port("coax_port")
        coax_port.radial_extent_factor = 3
        assert coax_port.radial_extent_factor == 3
        assert coax_port.component
        assert self.edbapp.components["U6"].pins["R3"].get_terminal()
        assert self.edbapp.components["U6"].pins["R3"].id
        assert self.edbapp.terminals
        assert self.edbapp.ports
        assert self.edbapp.components["U6"].pins["R3"].get_connected_objects()

    def test_004_get_properties(self):
        assert len(self.edbapp.components.components) > 0
        assert len(self.edbapp.components.inductors) > 0
        assert len(self.edbapp.components.resistors) > 0
        assert len(self.edbapp.components.capacitors) > 0
        assert len(self.edbapp.components.ICs) > 0
        assert len(self.edbapp.components.IOs) > 0
        assert len(self.edbapp.components.Others) > 0
        assert len(self.edbapp.get_bounding_box()) == 2

    def test_005_get_primitives(self):
        assert len(self.edbapp.modeler.polygons) > 0
        assert len(self.edbapp.modeler.paths) > 0
        assert len(self.edbapp.modeler.rectangles) > 0
        assert len(self.edbapp.modeler.circles) > 0
        assert len(self.edbapp.modeler.bondwires) == 0
        assert "1_Top" in self.edbapp.modeler.polygons_by_layer.keys()
        assert len(self.edbapp.modeler.polygons_by_layer["1_Top"]) > 0
        assert len(self.edbapp.modeler.polygons_by_layer["DE1"]) == 0
        assert self.edbapp.modeler.polygons[0].is_void == self.edbapp.modeler.polygons[0].IsVoid()
        poly0 = self.edbapp.modeler.polygons[0]
        assert self.edbapp.modeler.polygons[0].clone()
        poly1 = self.edbapp.modeler.polygons[0]
        assert isinstance(poly0.voids, list)
        assert isinstance(poly0.points_raw(), list)
        assert isinstance(poly0.points(), tuple)
        assert isinstance(poly0.points()[0], list)
        assert poly0.points()[0][0] >= 0.0
        assert poly0.points_raw()[0].X.ToDouble() >= 0.0
        assert poly0.type == "Polygon"
        assert self.edbapp.modeler.paths[0].type == "Path"
        assert self.edbapp.modeler.paths[0].clone()
        assert isinstance(self.edbapp.modeler.paths[0].width, float)
        self.edbapp.modeler.paths[0].width = "1mm"
        assert self.edbapp.modeler.paths[0].width == 0.001
        assert self.edbapp.modeler.rectangles[0].type == "Rectangle"
        assert self.edbapp.modeler.circles[0].type == "Circle"
        assert not poly0.is_arc(poly0.points_raw()[0])
        assert isinstance(poly0.voids, list)
        assert self.edbapp.modeler.primitives_by_layer["1_Top"][0].layer_name == "1_Top"
        assert self.edbapp.modeler.primitives_by_layer["1_Top"][0].layer.GetName() == "1_Top"
        assert not self.edbapp.modeler.primitives_by_layer["1_Top"][0].is_negative
        assert not self.edbapp.modeler.primitives_by_layer["1_Top"][0].is_void
        self.edbapp.modeler.primitives_by_layer["1_Top"][0].is_negative = True
        assert self.edbapp.modeler.primitives_by_layer["1_Top"][0].is_negative
        self.edbapp.modeler.primitives_by_layer["1_Top"][0].is_negative = False
        assert not self.edbapp.modeler.primitives_by_layer["1_Top"][0].has_voids
        assert not self.edbapp.modeler.primitives_by_layer["1_Top"][0].is_parameterized
        assert isinstance(self.edbapp.modeler.primitives_by_layer["1_Top"][0].get_hfss_prop(), tuple)

        assert not self.edbapp.modeler.primitives_by_layer["1_Top"][0].is_zone_primitive
        assert self.edbapp.modeler.primitives_by_layer["1_Top"][0].can_be_zone_primitive

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

    def test_007_get_signal_layers(self):
        assert self.edbapp.stackup.residual_copper_area_per_layer()

    def test_008_component_lists(self):
        component_list = self.edbapp.components.components
        assert len(component_list) > 2

    def test_009_vias_creation(self):
        self.edbapp.padstacks.create(padstackname="myVia")
        assert "myVia" in list(self.edbapp.padstacks.definitions.keys())
        self.edbapp.padstacks.definitions["myVia"].hole_range = "begin_on_upper_pad"
        assert self.edbapp.padstacks.definitions["myVia"].hole_range == "begin_on_upper_pad"
        self.edbapp.padstacks.definitions["myVia"].hole_range = "through"
        assert self.edbapp.padstacks.definitions["myVia"].hole_range == "through"
        self.edbapp.padstacks.create(padstackname="myVia_bullet", antipad_shape="Bullet")
        assert "myVia_bullet" in list(self.edbapp.padstacks.definitions.keys())
        self.edbapp.add_design_variable("via_x", 5e-3)
        self.edbapp["via_y"] = "1mm"
        assert self.edbapp["via_y"].value == 1e-3
        assert self.edbapp["via_y"].value_string == "1mm"
        assert self.edbapp.padstacks.place(["via_x", "via_x+via_y"], "myVia", via_name="via_test1")
        assert self.edbapp.padstacks.place(["via_x", "via_x+via_y*2"], "myVia_bullet")
        self.edbapp.padstacks["via_test1"].net_name = "GND"
        assert self.edbapp.padstacks["via_test1"].net_name == "GND"
        padstack = self.edbapp.padstacks.place(["via_x", "via_x+via_y*3"], "myVia", is_pin=True)
        for test_prop in (self.edbapp.padstacks.padstack_instances, self.edbapp.padstacks.instances):
            padstack_instance = test_prop[padstack.id]
            assert padstack_instance.is_pin
            assert padstack_instance.position
            assert padstack_instance.start_layer in padstack_instance.layer_range_names
            assert padstack_instance.stop_layer in padstack_instance.layer_range_names
            padstack_instance.position = [0.001, 0.002]
            assert padstack_instance.position == [0.001, 0.002]
            assert padstack_instance.parametrize_position()
            assert isinstance(padstack_instance.rotation, float)
            self.edbapp.padstacks.create_circular_padstack(padstackname="mycircularvia")
            assert "mycircularvia" in list(self.edbapp.padstacks.definitions.keys())
            assert not padstack_instance.backdrill_top
            assert not padstack_instance.backdrill_bottom
            assert padstack_instance.delete()
            via = self.edbapp.padstacks.place([0, 0], "myVia")
            assert via.set_backdrill_top("Inner4(Sig2)", 0.5e-3)
            assert via.backdrill_top
            assert via.set_backdrill_bottom("16_Bottom", 0.5e-3)
            assert via.backdrill_bottom

    def test_010_nets_query(self):
        signalnets = self.edbapp.nets.signal
        powernets = self.edbapp.nets.power
        assert len(signalnets) > 2
        assert len(powernets) > 2
        assert len(self.edbapp.nets.netlist) > 0
        assert powernets["AVCC_1V3"].is_power_ground
        powernets["AVCC_1V3"].is_power_ground = False
        assert not powernets["AVCC_1V3"].is_power_ground
        powernets["AVCC_1V3"].is_power_ground = True
        assert powernets["AVCC_1V3"].name == "AVCC_1V3"
        assert powernets["AVCC_1V3"].IsPowerGround()
        assert len(list(powernets["AVCC_1V3"].components.keys())) > 0
        assert len(powernets["AVCC_1V3"].primitives) > 0

        assert not signalnets[list(signalnets.keys())[0]].is_power_ground
        assert not signalnets[list(signalnets.keys())[0]].IsPowerGround()
        assert len(list(signalnets[list(signalnets.keys())[0]].primitives)) > 0

        assert self.edbapp.nets.find_or_create_net("GND")
        assert self.edbapp.nets.find_or_create_net(start_with="gn")
        assert self.edbapp.nets.find_or_create_net(start_with="g", end_with="d")
        assert self.edbapp.nets.find_or_create_net(end_with="d")
        assert self.edbapp.nets.find_or_create_net(contain="usb")
        assert self.edbapp.extended_nets.auto_identify_signal()
        assert self.edbapp.extended_nets.auto_identify_power()
        extended_net_name, extended_net_obj = next(iter(self.edbapp.extended_nets.items.items()))
        assert self.edbapp.extended_nets[extended_net_name]
        assert self.edbapp.extended_nets[extended_net_name].nets
        assert self.edbapp.extended_nets[extended_net_name].components
        assert self.edbapp.extended_nets[extended_net_name].rlc
        assert self.edbapp.extended_nets[extended_net_name].serial_rlc

        assert self.edbapp.nets["AVCC_1V3"].extended_net

        assert self.edbapp.extended_nets.create("new_ex_net", "DDR4_A1")

        self.edbapp.differential_pairs.auto_identify()
        diff_pair = self.edbapp.differential_pairs.create("new_pair1", "PCIe_Gen4_RX1_P", "PCIe_Gen4_RX1_N")
        assert diff_pair.positive_net.name == "PCIe_Gen4_RX1_P"
        assert diff_pair.negative_net.name == "PCIe_Gen4_RX1_N"
        assert self.edbapp.differential_pairs["new_pair1"]

        assert self.edbapp.net_classes.items
        assert self.edbapp.net_classes.create("DDR4_ADD", ["DDR4_A0", "DDR4_A1"])
        assert self.edbapp.net_classes["DDR4_ADD"].name == "DDR4_ADD"
        assert self.edbapp.net_classes["DDR4_ADD"].nets
        self.edbapp.net_classes["DDR4_ADD"].name = "DDR4_ADD_RENAMED"
        assert not self.edbapp.net_classes["DDR4_ADD_RENAMED"].is_null

    def test_011_assign_rlc(self):
        assert self.edbapp.components.set_component_rlc("C1", res_value=1e-3, cap_value="10e-6", isparallel=False)
        assert self.edbapp.components.set_component_rlc("L10", res_value=1e-3, ind_value="10e-6", isparallel=True)

    def test_020_components(self):
        assert "R1" in list(self.edbapp.components.components.keys())
        assert not self.edbapp.components.components["R1"].is_null
        assert self.edbapp.components.components["R1"].res_value
        assert self.edbapp.components.components["R1"].placement_layer
        assert isinstance(self.edbapp.components.components["R1"].lower_elevation, float)
        assert isinstance(self.edbapp.components.components["R1"].upper_elevation, float)
        assert self.edbapp.components.components["R1"].top_bottom_association == 2
        assert self.edbapp.components.components["R1"].pinlist
        assert self.edbapp.components.components["R1"].pins
        assert self.edbapp.components.components["R1"].pins["1"].pin_number
        assert self.edbapp.components.components["R1"].pins["1"].component
        assert (
            self.edbapp.components.components["R1"].pins["1"].lower_elevation
            == self.edbapp.components.components["R1"].lower_elevation
        )
        assert (
            self.edbapp.components.components["R1"].pins["1"].placement_layer
            == self.edbapp.components.components["R1"].placement_layer
        )
        assert (
            self.edbapp.components.components["R1"].pins["1"].upper_elevation
            == self.edbapp.components.components["R1"].upper_elevation
        )
        assert (
            self.edbapp.components.components["R1"].pins["1"].top_bottom_association
            == self.edbapp.components.components["R1"].top_bottom_association
        )
        assert self.edbapp.components.components["R1"].pins["1"].position
        assert self.edbapp.components.components["R1"].pins["1"].rotation

    def test_021b_components(self):
        comp = self.edbapp.components.components["U1"]
        comp.create_clearance_on_component()

    def test_021_components_from_net(self):
        assert self.edbapp.components.get_components_from_nets("DDR4_DQS0_P")

    def test_022_resistors(self):
        assert "R1" in list(self.edbapp.components.resistors.keys())
        assert "C1" not in list(self.edbapp.components.resistors.keys())

    def test_023_capacitors(self):
        assert "C1" in list(self.edbapp.components.capacitors.keys())
        assert "R1" not in list(self.edbapp.components.capacitors.keys())

    def test_024_inductors(self):
        assert "L10" in list(self.edbapp.components.inductors.keys())
        assert "R1" not in list(self.edbapp.components.inductors.keys())

    def test_025_ICs(self):
        assert "U1" in list(self.edbapp.components.ICs.keys())
        assert "R1" not in list(self.edbapp.components.ICs.keys())

    def test_026_IOs(self):
        assert "X1" in list(self.edbapp.components.IOs.keys())
        assert "R1" not in list(self.edbapp.components.IOs.keys())

    def test_027_Others(self):
        assert "B1" in self.edbapp.components.Others
        assert "R1" not in self.edbapp.components.Others

    def test_028_Components_by_PartName(self):
        comp = self.edbapp.components.components_by_partname
        assert "ALTR-FBGA24_A-130" in comp
        assert len(comp["ALTR-FBGA24_A-130"]) == 1

    def test_029_get_through_resistor_list(self):
        assert self.edbapp.components.get_through_resistor_list(10)

    def test_030_get_rats(self):
        assert len(self.edbapp.components.get_rats()) > 0

    def test_031_get_component_connections(self):
        assert len(self.edbapp.components.get_component_net_connection_info("U1")) > 0

    def test_032_get_power_tree(self):
        OUTPUT_NET = "5V"
        GROUND_NETS = ["GND", "PGND"]
        (
            component_list,
            component_list_columns,
            net_group,
        ) = self.edbapp.nets.get_powertree(OUTPUT_NET, GROUND_NETS)
        assert component_list
        assert component_list_columns
        assert net_group

    def test_033_aedt_pinname_pin_position(self):
        cmp_pinlist = self.edbapp.padstacks.get_pinlist_from_component_and_net("U6", "GND")
        pin_name = self.edbapp.components.get_aedt_pin_name(cmp_pinlist[0])
        assert type(pin_name) is str
        assert len(pin_name) > 0
        assert len(cmp_pinlist[0].position) == 2
        assert len(self.edbapp.components.get_pin_position(cmp_pinlist[0])) == 2

    def test_034_get_pins_name_from_net(self):
        cmp_pinlist = self.edbapp.components.get_pin_from_component("U6")
        assert len(self.edbapp.components.get_pins_name_from_net(cmp_pinlist, "GND")) > 0
        assert len(self.edbapp.components.get_pins_name_from_net(cmp_pinlist, "5V")) == 0

    def test_035_delete_single_pin_rlc(self):
        assert len(self.edbapp.components.delete_single_pin_rlc()) == 0

    def test_036_component_rlc(self):
        assert self.edbapp.components.set_component_rlc("R1", 30, 1e-9, 1e-12)

    def test_037_disable_component(self):
        assert self.edbapp.components.disable_rlc_component("R1")

    def test_038_delete_component(self):
        assert self.edbapp.components.delete("R1")

    def test_039_create_coax_port(self):
        assert self.edbapp.hfss.create_coax_port_on_component("U1", ["DDR4_DQS0_P", "DDR4_DQS0_N"])

    def test_040_create_circuit_port(self):
        initial_len = len(self.edbapp.padstacks.pingroups)
        assert self.edbapp.siwave.create_circuit_port_on_net("U1", "1V0", "U1", "GND", 50, "test") == "test"
        p2 = self.edbapp.siwave.create_circuit_port_on_net("U1", "PLL_1V8", "U1", "GND", 50, "test")
        assert p2 != "test" and "test" in p2
        pins = self.edbapp.components.get_pin_from_component("U1")
        p3 = self.edbapp.siwave.create_circuit_port_on_pin(pins[200], pins[0], 45)
        assert p3 != ""
        p4 = self.edbapp.hfss.create_circuit_port_on_net("U1", "USB3_D_P")
        assert len(self.edbapp.padstacks.pingroups) == initial_len + 6
        assert "GND" in p4 and "USB3_D_P" in p4
        assert "test" in self.edbapp.terminals
        assert self.edbapp.siwave.create_pin_group_on_net("U1", "1V0", "PG_V1P0_S0")
        assert self.edbapp.siwave.create_circuit_port_on_pin_group(
            "PG_V1P0_S0", "PinGroup_2", impedance=50, name="test_port"
        )
        self.edbapp.excitations["test_port"].name = "test_rename"
        assert any(port for port in list(self.edbapp.excitations) if port == "test_rename")

    def test_041_create_voltage_source(self):
        assert "Vsource_" in self.edbapp.siwave.create_voltage_source_on_net("U1", "USB3_D_P", "U1", "GND", 3.3, 0)
        pins = self.edbapp.components.get_pin_from_component("U1")
        assert "VSource_" in self.edbapp.siwave.create_voltage_source_on_pin(pins[300], pins[10], 3.3, 0)
        assert len(self.edbapp.sources) > 0
        assert len(self.edbapp.probes) == 0
        assert list(self.edbapp.sources.values())[0].magnitude == 3.3
        list(self.edbapp.sources.values())[0].phase = 1
        assert list(self.edbapp.sources.values())[0].phase == 1
        u6 = self.edbapp.components["U6"]
        self.edbapp.create_voltage_source(
            u6.pins["F2"].get_terminal(create_new_terminal=True), u6.pins["F1"].get_terminal(create_new_terminal=True)
        )

    def test_042_create_current_source(self):
        assert self.edbapp.siwave.create_current_source_on_net("U1", "USB3_D_N", "U1", "GND", 0.1, 0) != ""
        pins = self.edbapp.components.get_pin_from_component("U1")
        assert "I22" == self.edbapp.siwave.create_current_source_on_pin(pins[301], pins[10], 0.1, 0, "I22")

        assert self.edbapp.siwave.create_pin_group_on_net(reference_designator="U1", net_name="GND", group_name="gnd")
        self.edbapp.siwave.create_pin_group(reference_designator="U1", pin_numbers=["A27", "A28"], group_name="vrm_pos")
        self.edbapp.siwave.create_current_source_on_pin_group(
            pos_pin_group_name="vrm_pos", neg_pin_group_name="gnd", name="vrm_current_source"
        )

        self.edbapp.siwave.create_pin_group(
            reference_designator="U1", pin_numbers=["R23", "P23"], group_name="sink_pos"
        )

        assert self.edbapp.siwave.create_voltage_source_on_pin_group("sink_pos", "gnd", name="vrm_voltage_source")
        self.edbapp.siwave.create_pin_group(reference_designator="U1", pin_numbers=["A27", "A28"], group_name="vp_pos")
        self.edbapp.siwave.create_pin_group(reference_designator="U1", pin_numbers=["R23", "P23"], group_name="vp_neg")
        assert self.edbapp.siwave.create_voltage_probe_on_pin_group("vprobe", "vp_pos", "vp_neg")
        assert self.edbapp.probes["vprobe"]
        self.edbapp.siwave.place_voltage_probe(
            "vprobe_2", "1V0", ["112mm", "24mm"], "1_Top", "GND", ["112mm", "27mm"], "Inner1(GND1)"
        )
        vprobe_2 = self.edbapp.probes["vprobe_2"]
        ref_term = vprobe_2.ref_terminal
        assert isinstance(ref_term.location, list)
        ref_term.location = [0, 0]
        assert ref_term.layer
        ref_term.layer = "1_Top"
        u6 = self.edbapp.components["U6"]
        self.edbapp.create_current_source(
            u6.pins["H8"].get_terminal(create_new_terminal=True), u6.pins["G9"].get_terminal(create_new_terminal=True)
        )

    def test_043_create_dc_terminal(self):
        assert self.edbapp.siwave.create_dc_terminal("U1", "DDR4_DQ40", "dc_terminal1") == "dc_terminal1"

    def test_044_create_resistors(self):
        pins = self.edbapp.components.get_pin_from_component("U1")
        assert "RST4000" == self.edbapp.siwave.create_resistor_on_pin(pins[302], pins[10], 40, "RST4000")

    def test_045_create_siwave_ac_analsyis(self):
        assert self.edbapp.siwave.add_siwave_syz_analysis()

    def test_046_create_siwave_dc_analsyis(self):
        setup = self.edbapp.siwave.add_siwave_dc_analysis()
        assert setup.add_source_terminal_to_ground(list(self.edbapp.sources.keys())[0], 2)

    def test_047_get_nets_from_pin_list(self):
        cmp_pinlist = self.edbapp.padstacks.get_pinlist_from_component_and_net("U1", "GND")
        if cmp_pinlist:
            assert cmp_pinlist[0].GetNet().GetName()

    def test_048_mesh_operations(self):
        self.edbapp.components.create_port_on_component(
            "U1",
            ["VDD_DDR"],
            reference_net="GND",
            port_type=SourceType.CircPort,
        )
        mesh_ops = self.edbapp.hfss.get_trace_width_for_traces_with_ports()
        assert len(mesh_ops) > 0

    def test_049_assign_model(self):
        assert self.edbapp.components.set_component_model(
            "C10",
            modelpath=os.path.join(
                local_path,
                "example_models",
                test_subfolder,
                "GRM32ER72A225KA35_25C_0V.sp",
            ),
            modelname="GRM32ER72A225KA35_25C_0V",
        )
        assert not self.edbapp.components.set_component_model(
            "C100000",
            modelpath=os.path.join(
                local_path,
                test_subfolder,
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
        assert self.edbapp.modeler.parametrize_trace_width("A0_N")
        assert self.edbapp.modeler.parametrize_trace_width("A0_N_R")
        result, var_server = self.edbapp.add_design_variable("my_parameter", "2mm", True)
        assert result
        assert var_server.IsVariableParameter("my_parameter")
        result, var_server = self.edbapp.add_design_variable("my_parameter", "2mm", True)
        assert not result
        result, var_server = self.edbapp.add_project_variable("$my_project_variable", "3mm")
        assert result
        assert var_server
        result, var_server = self.edbapp.add_project_variable("$my_project_variable", "3mm")
        assert not result

    def test_051_delete_net(self):
        self.edbapp.nets["JTAG_TCK"].delete()
        nets_deleted = self.edbapp.nets.delete("JTAG_TDI")
        assert "JTAG_TDI" in nets_deleted

    def test_052_get_polygons_bounding(self):
        polys = self.edbapp.modeler.get_polygons_by_layer("GND")
        for poly in polys:
            bounding = self.edbapp.modeler.get_polygon_bounding_box(poly)
            assert len(bounding) == 4

    def test_053_get_polygons_bbylayerandnets(self):
        nets = ["GND", "1V0"]
        polys = self.edbapp.modeler.get_polygons_by_layer("16_Bottom", nets)
        assert polys

    def test_0548_get_polygons_points(self):
        polys = self.edbapp.modeler.get_polygons_by_layer("GND")
        for poly in polys:
            points = self.edbapp.modeler.get_polygon_points(poly)
            assert points

    def test_055_get_padstack(self):
        for el in self.edbapp.padstacks.definitions:
            padstack = self.edbapp.padstacks.definitions[el]
            assert padstack.hole_plating_thickness is not None or False
            assert padstack.hole_properties is not None or False
            assert padstack.hole_plating_thickness is not None or False
            assert padstack.hole_plating_ratio is not None or False
            assert padstack.via_start_layer is not None or False
            assert padstack.via_stop_layer is not None or False
            assert padstack.material is not None or False
            assert padstack.hole_finished_size is not None or False
            assert padstack.hole_rotation is not None or False
            assert padstack.hole_offset_x is not None or False
            assert padstack.hole_offset_y is not None or False
            assert padstack.hole_type is not None or False
            pad = padstack.pad_by_layer[padstack.via_stop_layer]
            if not pad.shape == "NoGeometry":
                assert pad.parameters is not None or False
                assert pad.parameters_values is not None or False
                assert pad.offset_x is not None or False
                assert pad.offset_y is not None or False
                assert isinstance(pad.geometry_type, int)
            polygon = pad.polygon_data
            if polygon:
                assert polygon.GetBBox()

    def test_056_set_padstack(self):
        pad = self.edbapp.padstacks.definitions["c180h127"]
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
        pad.pad_by_layer[pad.via_stop_layer].shape = "Circle"
        pad.pad_by_layer[pad.via_stop_layer].parameters = 7
        pad.pad_by_layer[pad.via_stop_layer].offset_x = offset_x
        pad.pad_by_layer[pad.via_stop_layer].offset_y = offset_y
        assert pad.pad_by_layer[pad.via_stop_layer].parameters["Diameter"].tofloat == 7
        assert pad.pad_by_layer[pad.via_stop_layer].offset_x == str(offset_x)
        assert pad.pad_by_layer[pad.via_stop_layer].offset_y == str(offset_y)
        pad.pad_by_layer[pad.via_stop_layer].parameters = {"Diameter": 8}
        assert pad.pad_by_layer[pad.via_stop_layer].parameters["Diameter"].tofloat == 8
        pad.pad_by_layer[pad.via_stop_layer].parameters = {"Diameter": 1}
        pad.pad_by_layer[pad.via_stop_layer].shape = "Square"
        pad.pad_by_layer[pad.via_stop_layer].parameters = {"Size": 1}
        pad.pad_by_layer[pad.via_stop_layer].shape = "Rectangle"
        pad.pad_by_layer[pad.via_stop_layer].parameters = {"XSize": 1, "YSize": 1}
        pad.pad_by_layer[pad.via_stop_layer].shape = "Oval"
        pad.pad_by_layer[pad.via_stop_layer].parameters = {"XSize": 1, "YSize": 1, "CornerRadius": 1}
        pad.pad_by_layer[pad.via_stop_layer].parameters = {"XSize": 1, "YSize": 1, "CornerRadius": 1}
        pad.pad_by_layer[pad.via_stop_layer].parameters = [1, 1, 1]

    def test_057_save_edb_as(self):
        assert self.edbapp.save_edb_as(os.path.join(self.local_scratch.path, "Gelileo_new.aedb"))
        assert os.path.exists(os.path.join(self.local_scratch.path, "Gelileo_new.aedb", "edb.def"))

    def test_058_parametrize_layout(self):
        assert len(self.edbapp.modeler.polygons) > 0
        for el in self.edbapp.modeler.polygons:
            if el.GetId() == 5953:
                poly = el
        for el in self.edbapp.modeler.polygons:
            if el.GetId() == 5954:
                selection_poly = el
        assert self.edbapp.modeler.parametrize_polygon(poly, selection_poly)

    def test_059_import_bom(self):
        assert self.edbapp.components.update_rlc_from_bom(
            os.path.join(local_path, "example_models", test_subfolder, bom_example),
            delimiter=",",
            valuefield="Value",
            comptype="Prod name",
            refdes="RefDes",
        )
        assert not self.edbapp.components.components["R2"].is_enabled
        self.edbapp.components.components["R2"].is_enabled = True
        assert self.edbapp.components.components["R2"].is_enabled

    def test_060_import_bom(self):
        source_path = os.path.join(local_path, "example_models", test_subfolder, "ANSYS-HSD_V1.aedb")
        target_path = os.path.join(self.local_scratch.path, "ANSYS-HSD_V1_bom.aedb")
        self.local_scratch.copyfolder(source_path, target_path)
        edbapp = Edb(target_path, edbversion=desktop_version)
        edbapp.components.import_bom(os.path.join(local_path, "example_models", test_subfolder, "bom_example_2.csv"))
        assert not edbapp.components.instances["R2"].is_enabled
        assert edbapp.components.instances["U13"].partname == "SLAB-QFN-24-2550x2550TP_V"

        export_bom_path = os.path.join(self.local_scratch.path, "export_bom.csv")
        assert edbapp.components.export_bom(export_bom_path)
        edbapp.close()

    def test_061_create_component_from_pins(self):
        pins = self.edbapp.components.get_pin_from_component("R13")
        component = self.edbapp.components.create(pins, "newcomp")
        assert component
        assert component.part_name == "newcomp"
        assert len(component.pins) == 2

    def test_062_create_cutout(self):
        source_path = os.path.join(local_path, "example_models", test_subfolder, "ANSYS-HSD_V1_cut.aedb")
        target_path = os.path.join(self.local_scratch.path, "ANSYS-HSD_V1_cutou1.aedb")
        self.local_scratch.copyfolder(source_path, target_path)
        edbapp = Edb(target_path, edbversion=desktop_version)
        output = os.path.join(self.local_scratch.path, "cutout.aedb")
        assert edbapp.cutout(
            ["DDR4_DQS0_P", "DDR4_DQS0_N"],
            ["GND"],
            output_aedb_path=output,
            open_cutout_at_end=False,
            use_pyaedt_extent_computing=True,
            use_pyaedt_cutout=False,
        )
        assert edbapp.cutout(
            ["DDR4_DQS0_P", "DDR4_DQS0_N"],
            ["GND"],
            output_aedb_path=output,
            open_cutout_at_end=False,
            remove_single_pin_components=True,
            use_pyaedt_cutout=False,
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

        assert edbapp.cutout(
            custom_extent=points,
            signal_list=["GND", "1V0"],
            output_aedb_path=output,
            open_cutout_at_end=False,
            include_partial_instances=True,
            use_pyaedt_cutout=False,
        )
        assert os.path.exists(os.path.join(output, "edb.def"))
        output = os.path.join(self.local_scratch.path, "cutout3.aedb")

        assert edbapp.cutout(
            custom_extent=points,
            signal_list=["GND", "1V0"],
            output_aedb_path=output,
            open_cutout_at_end=False,
            include_partial_instances=True,
            use_pyaedt_cutout=False,
        )
        assert os.path.exists(os.path.join(output, "edb.def"))
        edbapp.close()

    def test_063_create_custom_cutout(self):
        source_path = os.path.join(local_path, "example_models", test_subfolder, "ANSYS-HSD_V1.aedb")
        target_path = os.path.join(self.local_scratch.path, "ANSYS-HSD_V1_cutou2.aedb")
        self.local_scratch.copyfolder(source_path, target_path)
        edbapp = Edb(target_path, edbversion=desktop_version)
        spice_path = os.path.join(local_path, "example_models", test_subfolder, "GRM32_DC0V_25degC.mod")
        edbapp.components.instances["R8"].assign_spice_model(spice_path)
        edbapp.nets.nets
        assert edbapp.cutout(
            signal_list=["1V0"],
            reference_list=[
                "GND",
                "LVDS_CH08_N",
                "LVDS_CH08_P",
                "LVDS_CH10_N",
                "LVDS_CH10_P",
                "LVDS_CH04_P",
                "LVDS_CH04_N",
            ],
            extent_type="Bounding",
            number_of_threads=4,
            extent_defeature=0.001,
            preserve_components_with_model=True,
            keep_lines_as_path=True,
        )
        assert "A0_N" not in edbapp.nets.nets
        assert isinstance(edbapp.nets.find_and_fix_disjoint_nets("GND", order_by_area=True), list)
        assert isinstance(edbapp.nets.find_and_fix_disjoint_nets("GND", keep_only_main_net=True), list)
        assert isinstance(edbapp.nets.find_and_fix_disjoint_nets("GND", clean_disjoints_less_than=0.005), list)

        edbapp.close()

    @pytest.mark.skipif(sys.version_info < (3, 8), reason="Method works in CPython only")
    def test_064_create_custom_cutout(self):
        source_path = os.path.join(local_path, "example_models", test_subfolder, "ANSYS-HSD_V1.aedb")
        target_path = os.path.join(self.local_scratch.path, "ANSYS-HSD_V1_cutou3.aedb")
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
        assert edbapp.cutout(
            signal_list=["1V0"],
            reference_list=["GND"],
            number_of_threads=4,
            extent_type="ConvexHull",
            custom_extent=points,
            simple_pad_check=False,
        )
        edbapp.close()

    @pytest.mark.skipif(sys.version_info < (3, 8), reason="Method works in CPython only")
    def test_065_create_custom_cutout(self):
        source_path = os.path.join(local_path, "example_models", test_subfolder, "ANSYS-HSD_V1.aedb")
        target_path = os.path.join(self.local_scratch.path, "ANSYS-HSD_V1_cutou5.aedb")
        self.local_scratch.copyfolder(source_path, target_path)

        edbapp = Edb(target_path, edbversion=desktop_version)
        edbapp.components.create_port_on_component(
            "U1",
            ["5V"],
            reference_net="GND",
            port_type=SourceType.CircPort,
        )
        edbapp.components.create_port_on_component("U2", ["5V"], reference_net="GND")
        edbapp.hfss.create_voltage_source_on_net("U4", "5V", "U4", "GND")
        legacy_name = edbapp.edbpath
        assert edbapp.cutout(
            signal_list=["5V"],
            reference_list=["GND"],
            number_of_threads=4,
            extent_type="ConvexHull",
            use_pyaedt_extent_computing=True,
            check_terminals=True,
        )
        assert edbapp.edbpath == legacy_name
        assert edbapp.are_port_reference_terminals_connected(common_reference="GND")

        edbapp.close()

    @pytest.mark.skipif(sys.version_info < (3, 8), reason="Method works in CPython only")
    def test_065B_smart_cutout(self):
        source_path = os.path.join(local_path, "example_models", test_subfolder, "ANSYS-HSD_V1_cut.aedb")
        target_path = os.path.join(self.local_scratch.path, "ANSYS-HSD_V1_cut_smart.aedb")
        self.local_scratch.copyfolder(source_path, target_path)

        edbapp = Edb(target_path, edbversion=desktop_version)

        assert edbapp.cutout(
            signal_list=["DDR4_DQS0_P", "DDR4_DQS0_N"],
            reference_list=["GND"],
            number_of_threads=4,
            extent_type="ConvexHull",
            use_pyaedt_extent_computing=True,
            check_terminals=True,
            expansion_factor=4,
        )
        edbapp.close()
        source_path = os.path.join(local_path, "example_models", test_subfolder, "MicrostripSpliGnd.aedb")
        target_path = os.path.join(self.local_scratch.path, "MicrostripSpliGnd.aedb")
        self.local_scratch.copyfolder(source_path, target_path)

        edbapp = Edb(target_path, edbversion=desktop_version)

        assert edbapp.cutout(
            signal_list=["trace_n"],
            reference_list=["ground"],
            number_of_threads=4,
            extent_type="Conformal",
            use_pyaedt_extent_computing=True,
            check_terminals=True,
            expansion_factor=2,
        )
        edbapp.close()
        source_path = os.path.join(local_path, "example_models", test_subfolder, "Multizone_GroundVoids.aedb")
        target_path = os.path.join(self.local_scratch.path, "Multizone_GroundVoids.aedb")
        self.local_scratch.copyfolder(source_path, target_path)

        edbapp = Edb(target_path, edbversion=desktop_version)

        assert edbapp.cutout(
            signal_list=["DIFF_N", "DIFF_P"],
            reference_list=["GND"],
            number_of_threads=4,
            extent_type="Conformal",
            use_pyaedt_extent_computing=True,
            check_terminals=True,
            expansion_factor=3,
        )
        edbapp.close()

    def test_066_rvalue(self):
        assert resistor_value_parser("100meg")

    def test_067_stackup_limits(self):
        assert self.edbapp.stackup.limits()

    def test_068_create_polygon(self):
        settings.enable_error_handler = True
        points = [
            [-0.025, -0.02],
            [0.025, -0.02],
            [0.025, 0.02],
            [-0.025, 0.02],
            [-0.025, -0.02],
        ]
        plane = self.edbapp.modeler.Shape("polygon", points=points)
        points = [
            [-0.001, -0.001],
            [0.001, -0.001, "ccw", 0.0, -0.0012],
            [0.001, 0.001],
            [0.0015, 0.0015, 0.0001],
            [-0.001, 0.0015],
            [-0.001, -0.001],
        ]
        void1 = self.edbapp.modeler.Shape("polygon", points=points)
        void2 = self.edbapp.modeler.Shape("rectangle", [-0.002, 0.0], [-0.015, 0.0005])
        assert self.edbapp.modeler.create_polygon(plane, "1_Top", [void1, void2])
        self.edbapp["polygon_pts_x"] = -1.025
        self.edbapp["polygon_pts_y"] = -1.02
        points = [
            ["polygon_pts_x", "polygon_pts_y"],
            [1.025, -1.02],
            [1.025, 1.02],
            [-1.025, 1.02],
            [-1.025, -1.02],
        ]
        assert self.edbapp.modeler.create_polygon(points, "1_Top")
        settings.enable_error_handler = False

    def test_069_create_path(self):
        points = [
            [-0.025, -0.02],
            [0.025, -0.02],
            [0.025, 0.02],
        ]
        trace = self.edbapp.modeler.create_trace(points, "1_Top")
        assert trace
        assert isinstance(trace.get_center_line(), list)
        assert isinstance(trace.get_center_line(True), list)
        self.edbapp["delta_x"] = "1mm"
        assert trace.add_point("delta_x", "1mm", True)
        assert trace.get_center_line(True)[-1][0] == "(delta_x)+(0.025)"
        assert trace.add_point(0.001, 0.002)
        assert trace.get_center_line()[-1] == [0.001, 0.002]

    def test_070_create_outline(self):
        edbapp = Edb(
            edbversion=desktop_version,
        )
        assert edbapp.stackup.add_outline_layer("Outline1")
        assert not edbapp.stackup.add_outline_layer("Outline1")
        edbapp.stackup.add_layer("1_Top")
        assert edbapp.stackup.layers["1_Top"].thickness == 3.5e-05
        edbapp.stackup.layers["1_Top"].thickness = 4e-5
        assert edbapp.stackup.layers["1_Top"].thickness == 4e-05
        edbapp.close()

    def test_071_create_edb(self):
        edb = Edb(os.path.join(self.local_scratch.path, "temp.aedb"), edbversion=desktop_version)
        assert edb
        assert edb.active_layout
        edb.close()

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
        edb.close()

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
        edb.close()

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
        edb.close()

    def test_075_flatten_planes(self):
        assert self.edbapp.modeler.unite_polygons_on_layer("1_Top")

    def test_076_create_solder_ball_on_component(self):
        assert self.edbapp.components.set_solder_ball("U1", shape="Spheroid")
        assert self.edbapp.components.set_solder_ball("U6", sball_height=None)
        assert self.edbapp.components.set_solder_ball(
            "U6", sball_height="100um", auto_reference_size=False, chip_orientation="chip_up"
        )

    def test_077_add_void(self):
        plane_shape = self.edbapp.modeler.Shape("rectangle", pointA=["-5mm", "-5mm"], pointB=["5mm", "5mm"])
        plane = self.edbapp.modeler.create_polygon(plane_shape, "1_Top", net_name="GND")
        void = self.edbapp.modeler.create_trace([["0", "0"], ["0", "1mm"]], layer_name="1_Top", width="0.1mm")
        assert self.edbapp.modeler.add_void(plane, void)
        assert plane.add_void(void)

    def test_078_create_solder_balls_on_component(self):
        assert self.edbapp.components.set_solder_ball("U1")

    def test_080_fix_circle_voids(self):
        assert self.edbapp.modeler.fix_circle_void_for_clipping()

    def test_081_padstack_instance(self):
        padstack_instances = self.edbapp.padstacks.get_padstack_instance_by_net_name("GND")
        assert len(padstack_instances)
        padstack_1 = padstack_instances[0]
        assert padstack_1.id
        assert isinstance(padstack_1.bounding_box, list)
        for v in padstack_instances:
            if not v.is_pin:
                v.name = "TestInst"
                assert v.name == "TestInst"
                break

    def test_082_duplicate_padstack(self):
        self.edbapp.padstacks.duplicate(
            target_padstack_name="c180h127",
            new_padstack_name="c180h127_NEW",
        )
        assert self.edbapp.padstacks.definitions["c180h127_NEW"]

    def test_83_set_padstack_property(self):
        self.edbapp.padstacks.set_pad_property(
            padstack_name="c180h127",
            layer_name="new",
            pad_shape="Circle",
            pad_params="800um",
        )
        assert self.edbapp.padstacks.definitions["c180h127"].pad_by_layer["new"]

    def test_084_primitives_area(self):
        i = 0
        while i < 10:
            assert self.edbapp.modeler.primitives[i].area(False) > 0
            assert self.edbapp.modeler.primitives[i].area(True) > 0
            i += 1
        assert self.edbapp.modeler.primitives[i].bbox
        assert self.edbapp.modeler.primitives[i].center
        assert self.edbapp.modeler.primitives[i].get_closest_point((0, 0))
        assert self.edbapp.modeler.primitives[i].polygon_data
        assert self.edbapp.modeler.paths[0].length

    def test_085_short_component(self):
        assert self.edbapp.components.short_component_pins("U12", width=0.2e-3)
        assert self.edbapp.components.short_component_pins("U10", ["2", "5"])

    def test_086_set_component_type(self):
        comp = self.edbapp.components["R4"]
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
        assert self.edbapp.components.deactivate_rlc_component(component="C1", create_circuit_port=False)
        assert self.edbapp.ports["C1"]
        assert self.edbapp.components["C1"].is_enabled is False
        assert self.edbapp.components.deactivate_rlc_component(component="C2", create_circuit_port=True)
        self.edbapp.components["C2"].is_enabled = False
        assert self.edbapp.components["C2"].is_enabled is False
        self.edbapp.components["C2"].is_enabled = True
        assert self.edbapp.components["C2"].is_enabled is True

    def test_088_create_symmetric_stackup(self):
        app_edb = Edb(edbversion=desktop_version)
        assert not app_edb.stackup.create_symmetric_stackup(9)
        assert app_edb.stackup.create_symmetric_stackup(8)
        app_edb.close()

        app_edb = Edb(edbversion=desktop_version)
        assert app_edb.stackup.create_symmetric_stackup(8, soldermask=False)
        app_edb.close()

    def test_089_create_rectangle(self):
        rect = self.edbapp.modeler.create_rectangle("1_Top", "SIG1", ["0", "0"], ["2mm", "3mm"])
        assert rect
        rect.is_negative = True
        assert rect.is_negative
        rect.is_negative = False
        assert not rect.is_negative
        assert self.edbapp.modeler.create_rectangle(
            "1_Top",
            "SIG2",
            center_point=["0", "0"],
            width="4mm",
            height="5mm",
            representation_type="CenterWidthHeight",
        )

    def test_089B_circle_boolean(self):
        poly = self.edbapp.modeler.create_polygon_from_points([[0, 0], [100, 0], [100, 100], [0, 100]], "1_Top")
        assert poly
        poly.add_void([[20, 20], [20, 30], [100, 30], [100, 20]])
        poly2 = self.edbapp.modeler.create_polygon_from_points([[60, 60], [60, 150], [150, 150], [150, 60]], "1_Top")
        new_polys = poly.subtract(poly2)
        assert len(new_polys) == 1
        circle = self.edbapp.modeler.create_circle("1_Top", 40, 40, 15)
        assert circle
        intersection = new_polys[0].intersect(circle)
        assert len(intersection) == 1
        circle2 = self.edbapp.modeler.create_circle("1_Top", 20, 20, 15)
        assert circle2.unite(intersection)

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
            changed_variable_done, my_project_variable_value = changed_variable_5
            assert not changed_variable_done
        else:
            assert not changed_variable_5

    def test_097b_variables(self):
        variables = {
            "var1": 0.01,
            "var2": "10um",
            "var3": [0.03, "test description"],
            "$var4": ["1mm", "Project variable."],
            "$var5": 0.1,
        }
        for key, val in variables.items():
            self.edbapp[key] = val
            if key == "var1":
                assert self.edbapp[key].value == val
            elif key == "var2":
                assert check_numeric_equivalence(self.edbapp[key].value, 1.0e-5)
            elif key == "var3":
                assert self.edbapp[key].value == val[0]
                assert self.edbapp[key].description == val[1]
            elif key == "$var4":
                assert self.edbapp[key].value == 0.001
                assert self.edbapp[key].description == val[1]
            elif key == "$var5":
                assert self.edbapp[key].value == 0.1
                assert self.edbapp.project_variables[key].delete()

    def test_099_int_to_layer_types(self):
        stackup = self.edbapp.stackup
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
        stackup = self.edbapp.stackup
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

    def test_104_classify_nets(self):
        assert self.edbapp.nets.classify_nets(["RSVD_0", "RSVD_1"], ["V3P3_S0"])

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
            assert laminate_edb.stackup.place_a3dcomp_3d_placement(
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
            if config["desktopVersion"] > "2023.1":
                (
                    res,
                    local_origin,
                    rotation_axis_from,
                    rotation_axis_to,
                    angle,
                    loc,
                    mirror,
                ) = cell_instance.Get3DTransformation()
            else:
                (
                    res,
                    local_origin,
                    rotation_axis_from,
                    rotation_axis_to,
                    angle,
                    loc,
                ) = cell_instance.Get3DTransformation()
            assert res
            zero_value = laminate_edb.edb_value(0)
            one_value = laminate_edb.edb_value(1)
            origin_point = laminate_edb.edb_api.geometry.point3d_data(zero_value, zero_value, zero_value)
            x_axis_point = laminate_edb.edb_api.geometry.point3d_data(one_value, zero_value, zero_value)
            assert local_origin.IsEqual(origin_point)
            assert rotation_axis_from.IsEqual(x_axis_point)
            assert rotation_axis_to.IsEqual(x_axis_point)
            assert angle.IsEqual(zero_value)
            assert loc.IsEqual(
                laminate_edb.edb_api.geometry.point3d_data(zero_value, zero_value, laminate_edb.edb_value(170e-6))
            )
            assert laminate_edb.save_edb()
        finally:
            laminate_edb.close()

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
            assert laminate_edb.stackup.place_a3dcomp_3d_placement(
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
            if config["desktopVersion"] > "2023.1":
                (
                    res,
                    local_origin,
                    rotation_axis_from,
                    rotation_axis_to,
                    angle,
                    loc,
                    mirror,
                ) = cell_instance.Get3DTransformation()
            else:
                (
                    res,
                    local_origin,
                    rotation_axis_from,
                    rotation_axis_to,
                    angle,
                    loc,
                ) = cell_instance.Get3DTransformation()
            assert res
            zero_value = laminate_edb.edb_value(0)
            one_value = laminate_edb.edb_value(1)
            flip_angle_value = laminate_edb.edb_value("180deg")
            origin_point = laminate_edb.edb_api.geometry.point3d_data(zero_value, zero_value, zero_value)
            x_axis_point = laminate_edb.edb_api.geometry.point3d_data(one_value, zero_value, zero_value)
            assert local_origin.IsEqual(origin_point)
            assert rotation_axis_from.IsEqual(x_axis_point)
            assert rotation_axis_to.IsEqual(
                laminate_edb.edb_api.geometry.point3d_data(zero_value, laminate_edb.edb_value(-1.0), zero_value)
            )
            assert angle.IsEqual(flip_angle_value)
            assert loc.IsEqual(
                laminate_edb.edb_api.geometry.point3d_data(
                    laminate_edb.edb_value(0.5e-3),
                    laminate_edb.edb_value(-0.5e-3),
                    zero_value,
                )
            )
            assert laminate_edb.save_edb()
        finally:
            laminate_edb.close()

    def test_107_create_edge_ports(self):
        edb = Edb(
            edbpath=os.path.join(local_path, "example_models", test_subfolder, "edge_ports.aedb"),
            edbversion=desktop_version,
        )
        poly_list = [poly for poly in edb.layout.primitives if int(poly.GetPrimitiveType()) == 2]
        port_poly = [poly for poly in poly_list if poly.GetId() == 17][0]
        ref_poly = [poly for poly in poly_list if poly.GetId() == 19][0]
        port_location = [-65e-3, -13e-3]
        ref_location = [-63e-3, -13e-3]
        assert edb.hfss.create_edge_port_on_polygon(
            polygon=port_poly,
            reference_polygon=ref_poly,
            terminal_point=port_location,
            reference_point=ref_location,
        )
        port_poly = [poly for poly in poly_list if poly.GetId() == 23][0]
        ref_poly = [poly for poly in poly_list if poly.GetId() == 22][0]
        port_location = [-65e-3, -10e-3]
        ref_location = [-65e-3, -10e-3]
        assert edb.hfss.create_edge_port_on_polygon(
            polygon=port_poly,
            reference_polygon=ref_poly,
            terminal_point=port_location,
            reference_point=ref_location,
        )
        port_poly = [poly for poly in poly_list if poly.GetId() == 25][0]
        port_location = [-65e-3, -7e-3]
        assert edb.hfss.create_edge_port_on_polygon(
            polygon=port_poly, terminal_point=port_location, reference_layer="gnd"
        )
        sig = edb.modeler.create_trace([[0, 0], ["9mm", 0]], "TOP", "1mm", "SIG", "Flat", "Flat")
        assert sig.create_edge_port("pcb_port_1", "end", "Wave", None, 8, 8)
        assert sig.create_edge_port("pcb_port_2", "start", "gap")
        gap_port = edb.ports["pcb_port_2"]
        assert gap_port.component is None
        assert gap_port.magnitude == 0.0
        assert gap_port.phase == 0.0
        assert gap_port.impedance
        assert not gap_port.deembed
        gap_port.name = "gap_port"
        assert gap_port.name == "gap_port"
        assert isinstance(gap_port.renormalize_z0, tuple)
        gap_port.is_circuit_port = True
        assert gap_port.is_circuit_port
        edb.close()

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
        assert sim_setup.batch_solve_settings.use_pyaedt_cutout
        assert not sim_setup.batch_solve_settings.use_default_cutout
        sim_setup.batch_solve_settings.use_pyaedt_cutout = True
        assert sim_setup.batch_solve_settings.use_pyaedt_cutout
        assert not sim_setup.batch_solve_settings.use_default_cutout
        assert sim_setup.build_simulation_project()
        assert edb.edbpath == original_path
        sim_setup.open_edb_after_build = True
        assert sim_setup.build_simulation_project()
        assert edb.edbpath == os.path.join(self.local_scratch.path, "build.aedb")

        edb.close()

    def test_109_add_soure(self):
        example_project = os.path.join(local_path, "example_models", test_subfolder, "ANSYS-HSD_V1.aedb")
        target_path = os.path.join(self.local_scratch.path, "test_0create_source", "ANSYS-HSD_V1_add_source.aedb")
        self.local_scratch.copyfolder(example_project, target_path)
        sim_config = SimulationConfiguration()
        sim_config.add_voltage_source(
            name="test_0v_source",
            positive_node_component="U1",
            positive_node_net="V3P3_S0",
            negative_node_component="U1",
            negative_node_net="GND",
        )
        sim_config.add_current_source(
            positive_node_component="U1",
            positive_node_net="V1P5_S0",
            negative_node_component="U1",
            negative_node_net="GND",
        )
        sim_config.add_dc_ground_source_term("test_0v_source", 1)
        assert sim_config.dc_source_terms_to_ground["test_0v_source"] == 1
        assert len(sim_config.sources) == 2

    def test_110_layout_tchickness(self):
        assert self.edbapp.stackup.get_layout_thickness()

    def test_112_edb_stats(self):
        example_project = os.path.join(local_path, "example_models", test_subfolder, "ANSYS-HSD_V1.aedb")
        target_path = os.path.join(self.local_scratch.path, "ANSYS-HSD_V1_110.aedb")
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
        edb.close()

    def test_113_set_bounding_box_extent(self):
        source_path = os.path.join(local_path, "example_models", test_subfolder, "test_107.aedb")
        target_path = os.path.join(self.local_scratch.path, "test_113.aedb")
        self.local_scratch.copyfolder(source_path, target_path)
        edb = Edb(target_path, edbversion=desktop_version)
        initial_extent_info = edb.active_cell.GetHFSSExtentInfo()
        assert initial_extent_info.ExtentType == edb.edb_api.utility.utility.HFSSExtentInfoType.Conforming
        config = SimulationConfiguration()
        config.radiation_box = RadiationBoxType.BoundingBox
        assert edb.hfss.configure_hfss_extents(config)
        final_extent_info = edb.active_cell.GetHFSSExtentInfo()
        assert final_extent_info.ExtentType == edb.edb_api.utility.utility.HFSSExtentInfoType.BoundingBox
        edb.close()

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
        example_project = os.path.join(local_path, "example_models", test_subfolder, "ANSYS-HSD_V1.aedb")
        target_path = os.path.join(self.local_scratch.path, "ANSYS_114.aedb")
        self.local_scratch.copyfolder(example_project, target_path)
        edb = Edb(target_path, edbversion=desktop_version)
        pins = edb.components.get_pin_from_component("U1", "1V0")
        ref_pins = edb.components.get_pin_from_component("U1", "GND")
        assert edb.components.create([pins[0], ref_pins[0]], "test_0rlc", r_value=1.67, l_value=1e-13, c_value=1e-11)
        assert edb.components.create([pins[0], ref_pins[0]], "test_1rlc", r_value=None, l_value=1e-13, c_value=1e-11)
        assert edb.components.create([pins[0], ref_pins[0]], "test_2rlc", r_value=None, c_value=1e-13)
        edb.close()

    def test_117_create_rlc_boundary(self):
        example_project = os.path.join(local_path, "example_models", test_subfolder, "ANSYS-HSD_V1.aedb")
        target_path = os.path.join(self.local_scratch.path, "ANSYS-HSD_V1_115.aedb")
        if not os.path.exists(self.local_scratch.path):
            os.mkdir(self.local_scratch.path)
        self.local_scratch.copyfolder(example_project, target_path)
        edb = Edb(target_path, edbversion=desktop_version)
        pins = edb.components.get_pin_from_component("U1", "1V0")
        ref_pins = edb.components.get_pin_from_component("U1", "GND")
        assert edb.hfss.create_rlc_boundary_on_pins(pins[0], ref_pins[0], rvalue=1.05, lvalue=1.05e-12, cvalue=1.78e-13)
        edb.close()

    def test_118_configure_hfss_analysis_setup_enforce_causality(self):
        source_path = os.path.join(local_path, "example_models", test_subfolder, "lam_for_top_place_no_setups.aedb")
        target_path = os.path.join(self.local_scratch.path, "lam_for_top_place_no_setups_t116.aedb")
        if not os.path.exists(self.local_scratch.path):
            os.mkdir(self.local_scratch.path)
        self.local_scratch.copyfolder(source_path, target_path)
        edb = Edb(target_path, edbversion=desktop_version)
        assert len(list(edb.active_cell.SimulationSetups)) == 0
        sim_config = SimulationConfiguration()
        sim_config.enforce_causality = False
        assert sim_config.do_lambda_refinement
        sim_config.mesh_sizefactor = 0.1
        assert sim_config.mesh_sizefactor == 0.1
        assert not sim_config.do_lambda_refinement
        sim_config.start_freq = "1GHz"
        edb.hfss.configure_hfss_analysis_setup(sim_config)
        assert len(list(edb.active_cell.SimulationSetups)) == 1
        setup = list(edb.active_cell.SimulationSetups)[0]
        ssi = setup.GetSimSetupInfo()
        assert len(list(ssi.SweepDataList)) == 1
        sweep = list(ssi.SweepDataList)[0]
        assert not sweep.EnforceCausality
        edb.close()

    def test_119_add_hfss_config(self):
        source_path = os.path.join(local_path, "example_models", test_subfolder, "ANSYS-HSD_V1.aedb")
        target_path = os.path.join(self.local_scratch.path, "test_0117.aedb")
        self.local_scratch.copyfolder(source_path, target_path)
        edb = Edb(target_path, edbversion=desktop_version)
        sim_setup = SimulationConfiguration()
        sim_setup.mesh_sizefactor = 1.9
        assert not sim_setup.do_lambda_refinement
        edb.hfss.configure_hfss_analysis_setup(sim_setup)
        mesh_size_factor = (
            list(edb.active_cell.SimulationSetups)[0]
            .GetSimSetupInfo()
            .get_SimulationSettings()
            .get_InitialMeshSettings()
            .get_MeshSizefactor()
        )
        assert mesh_size_factor == 1.9
        edb.close()

    def test_120_edb_create_port(self):
        edb = Edb(
            edbpath=os.path.join(local_path, "example_models", "edb_edge_ports.aedb"),
            edbversion=desktop_version,
        )
        prim_1_id = [i.id for i in edb.modeler.primitives if i.net_name == "trace_2"][0]
        assert edb.hfss.create_edge_port_vertical(prim_1_id, ["-66mm", "-4mm"], "port_ver")

        prim_2_id = [i.id for i in edb.modeler.primitives if i.net_name == "trace_3"][0]
        assert edb.hfss.create_edge_port_horizontal(
            prim_1_id, ["-60mm", "-4mm"], prim_2_id, ["-59mm", "-4mm"], "port_hori", 30, "Lower"
        )
        assert edb.hfss.get_ports_number() == 2
        port_ver = edb.ports["port_ver"]
        assert not port_ver.is_null
        assert port_ver.hfss_type == "Gap"
        port_hori = edb.ports["port_hori"]
        assert port_hori.ref_terminal

        args = {
            "layer_name": "1_Top",
            "net_name": "SIGP",
            "width": "0.1mm",
            "start_cap_style": "Flat",
            "end_cap_style": "Flat",
        }
        traces = []
        trace_paths = [
            [["-40mm", "-10mm"], ["-30mm", "-10mm"]],
            [["-40mm", "-10.2mm"], ["-30mm", "-10.2mm"]],
            [["-40mm", "-10.4mm"], ["-30mm", "-10.4mm"]],
        ]
        for p in trace_paths:
            t = edb.modeler.create_trace(path_list=p, **args)
            traces.append(t)

        assert edb.hfss.create_wave_port(traces[0].id, trace_paths[0][0], "wave_port")
        wave_port = edb.ports["wave_port"]
        wave_port.horizontal_extent_factor = 10
        wave_port.vertical_extent_factor = 10
        assert wave_port.horizontal_extent_factor == 10
        assert wave_port.vertical_extent_factor == 10
        wave_port.radial_extent_factor = 1
        assert wave_port.radial_extent_factor == 1
        assert wave_port.pec_launch_width
        assert not wave_port.deembed
        assert wave_port.deembed_length == 0.0
        assert wave_port.do_renormalize
        wave_port.do_renormalize = False
        assert not wave_port.do_renormalize
        assert edb.hfss.create_differential_wave_port(
            traces[0].id,
            trace_paths[0][0],
            traces[1].id,
            trace_paths[1][0],
            horizontal_extent_factor=8,
            port_name="df_port",
        )
        assert edb.ports["df_port"]
        p, n = edb.ports["df_port"].terminals
        assert edb.ports["df_port"].decouple()
        p.couple_ports(n)

        traces_id = [i.id for i in traces]
        paths = [i[1] for i in trace_paths]
        _, df_port = edb.hfss.create_bundle_wave_port(traces_id, paths)
        assert df_port.name
        assert df_port.terminals
        df_port.horizontal_extent_factor = 10
        df_port.vertical_extent_factor = 10
        df_port.deembed = True
        df_port.deembed_length = "1mm"
        assert df_port.horizontal_extent_factor == 10
        assert df_port.vertical_extent_factor == 10
        assert df_port.deembed
        assert df_port.deembed_length == 1e-3
        edb.close()

    def test_120b_edb_create_port(self):
        edb = Edb(
            edbpath=os.path.join(local_path, "example_models", "edb_edge_ports.aedb"),
            edbversion=desktop_version,
        )
        args = {
            "layer_name": "1_Top",
            "net_name": "SIGP",
            "width": "0.1mm",
            "start_cap_style": "Flat",
            "end_cap_style": "Flat",
        }
        traces = []
        trace_pathes = [
            [["-40mm", "-10mm"], ["-30mm", "-10mm"]],
            [["-40mm", "-10.2mm"], ["-30mm", "-10.2mm"]],
            [["-40mm", "-10.4mm"], ["-30mm", "-10.4mm"]],
        ]
        for p in trace_pathes:
            t = edb.modeler.create_trace(path_list=p, **args)
            traces.append(t)

        assert edb.hfss.create_wave_port(traces[0], trace_pathes[0][0], "wave_port")

        assert edb.hfss.create_differential_wave_port(
            traces[0],
            trace_pathes[0][0],
            traces[1],
            trace_pathes[1][0],
            horizontal_extent_factor=8,
        )

        paths = [i[1] for i in trace_pathes]
        assert edb.hfss.create_bundle_wave_port(traces, paths)
        p = edb.excitations["wave_port"]
        p.horizontal_extent_factor = 6
        p.vertical_extent_factor = 5
        p.pec_launch_width = "0.02mm"
        p.radial_extent_factor = 1
        assert p.horizontal_extent_factor == 6
        assert p.vertical_extent_factor == 5
        assert p.pec_launch_width == "0.02mm"
        assert p.radial_extent_factor == 1
        edb.close()

    def test_122_build_hfss_project_from_config_file(self):
        source_path = os.path.join(local_path, "example_models", test_subfolder, "ANSYS-HSD_V1.aedb")
        target_path = os.path.join(self.local_scratch.path, "test_0122.aedb")
        self.local_scratch.copyfolder(source_path, target_path)
        edbapp = Edb(target_path, edbversion=desktop_version)
        cfg_file = os.path.join(os.path.dirname(edbapp.edbpath), "test.cfg")
        with open(cfg_file, "w") as f:
            f.writelines("SolverType = 'Hfss3dLayout'\n")
            f.writelines("PowerNets = ['GND']\n")
            f.writelines("Components = ['U1', 'U7']")

        sim_config = SimulationConfiguration(cfg_file)
        assert edbapp.build_simulation_project(sim_config)
        edbapp.close()

    def test_123_set_all_antipad_values(self):
        source_path = os.path.join(local_path, "example_models", test_subfolder, "ANSYS-HSD_V1.aedb")
        target_path = os.path.join(self.local_scratch.path, "test_0120.aedb")
        self.local_scratch.copyfolder(source_path, target_path)
        edbapp = Edb(target_path, edbversion=desktop_version)
        assert edbapp.padstacks.set_all_antipad_value(0.0)
        edbapp.close()

    def test_124_stackup(self):
        source_path = os.path.join(local_path, "example_models", test_subfolder, "ANSYS-HSD_V1.aedb")
        target_path = os.path.join(self.local_scratch.path, "test_0124.aedb")
        self.local_scratch.copyfolder(source_path, target_path)
        edbapp = Edb(target_path, edbversion=desktop_version)
        assert isinstance(edbapp.stackup.layers, dict)
        assert isinstance(edbapp.stackup.signal_layers, dict)
        assert isinstance(edbapp.stackup.dielectric_layers, dict)
        assert isinstance(edbapp.stackup.stackup_layers, dict)
        assert isinstance(edbapp.stackup.non_stackup_layers, dict)
        assert not edbapp.stackup["Outline"].is_stackup_layer
        assert edbapp.stackup["1_Top"].conductivity
        assert edbapp.stackup["DE1"].permittivity
        assert edbapp.stackup.add_layer("new_layer")
        new_layer = edbapp.stackup["new_layer"]
        assert new_layer.is_stackup_layer
        assert not new_layer.is_negative
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
        assert rename_layer.assign_roughness_model(apply_on_surface="1_Top")
        assert rename_layer.assign_roughness_model(apply_on_surface="bottom")
        assert rename_layer.assign_roughness_model(apply_on_surface="side")
        assert edbapp.stackup.add_layer("new_above", "1_Top", "insert_above")
        assert edbapp.stackup.add_layer("new_below", "1_Top", "insert_below")
        assert edbapp.stackup.add_layer("new_bottom", "1_Top", "add_on_bottom", "dielectric")
        assert edbapp.stackup.remove_layer("new_bottom")
        assert "new_bottom" not in edbapp.stackup.layers

        assert edbapp.stackup["1_Top"].color
        edbapp.stackup["1_Top"].color = [0, 120, 0]
        assert edbapp.stackup["1_Top"].color == (0, 120, 0)
        edbapp.stackup["1_Top"].transparency = 10
        assert edbapp.stackup["1_Top"].transparency == 10
        assert edbapp.stackup.mode == "Laminate"
        edbapp.stackup.mode = "Overlapping"
        assert edbapp.stackup.mode == "Overlapping"
        edbapp.stackup.mode = "MultiZone"
        assert edbapp.stackup.mode == "MultiZone"
        edbapp.stackup.mode = "Overlapping"
        assert edbapp.stackup.mode == "Overlapping"
        assert edbapp.stackup.add_layer("new_bottom", "1_Top", "add_at_elevation", "dielectric", elevation=0.0003)
        edbapp.close()

    def test_125_stackup(self):
        edbapp = Edb(edbversion=desktop_version)
        import_method = edbapp.stackup.load
        export_method = edbapp.stackup.export

        assert import_method(os.path.join(local_path, "example_models", test_subfolder, "ansys_pcb_stackup.xml"))
        assert "17_Bottom" in edbapp.stackup.layers.keys()
        xml_export = os.path.join(self.local_scratch.path, "stackup.xml")
        assert export_method(xml_export)
        assert os.path.exists(xml_export)
        assert import_method(os.path.join(local_path, "example_models", test_subfolder, "ansys_pcb_stackup.csv"))
        assert "18_Bottom" in edbapp.stackup.layers.keys()
        assert edbapp.stackup.add_layer("19_Bottom", None, "add_on_top", material="iron")
        export_stackup_path = os.path.join(self.local_scratch.path, "export_galileo_stackup.csv")
        assert export_method(export_stackup_path)
        assert os.path.exists(export_stackup_path)

        edbapp.close()

    def test_125b_stackup(self):
        edbapp = Edb(edbversion=desktop_version)
        import_method = edbapp.stackup.import_stackup
        export_method = edbapp.stackup.export_stackup

        assert import_method(os.path.join(local_path, "example_models", test_subfolder, "ansys_pcb_stackup.xml"))
        assert "17_Bottom" in edbapp.stackup.layers.keys()
        xml_export = os.path.join(self.local_scratch.path, "stackup.xml")
        assert export_method(xml_export)
        assert os.path.exists(xml_export)
        assert import_method(os.path.join(local_path, "example_models", test_subfolder, "ansys_pcb_stackup.csv"))
        assert "18_Bottom" in edbapp.stackup.layers.keys()
        assert edbapp.stackup.add_layer("19_Bottom", None, "add_on_top", material="iron")
        export_stackup_path = os.path.join(self.local_scratch.path, "export_galileo_stackup.csv")
        assert export_method(export_stackup_path)
        assert os.path.exists(export_stackup_path)
        edbapp.close()

    def test_125c_layer(self):
        source_path = os.path.join(local_path, "example_models", test_subfolder, "ANSYS-HSD_V1.aedb")
        target_path = os.path.join(self.local_scratch.path, "test_0126.aedb")
        self.local_scratch.copyfolder(source_path, target_path)
        edbapp = Edb(target_path, edbversion=desktop_version)
        edbapp.stackup.load(os.path.join(local_path, "example_models", test_subfolder, "ansys_pcb_stackup.xml"))
        layer = edbapp.stackup["1_Top"]
        layer.name = "TOP"
        assert layer.name == "TOP"
        layer.type = "dielectric"
        assert layer.type == "dielectric"
        layer.type = "signal"
        layer.color = (0, 0, 0)
        assert layer.color == (0, 0, 0)
        layer.transparency = 0
        assert layer.transparency == 0
        layer.etch_factor = 2
        assert layer.etch_factor == 2
        layer.thickness = 50e-6
        assert layer.thickness == 50e-6
        assert layer.lower_elevation
        assert layer.upper_elevation
        layer.is_negative = True
        assert layer.is_negative
        assert not layer.is_via_layer
        assert layer.material == "copper"
        edbapp.close()

    def test_125d_stackup(self):
        fpath = os.path.join(local_path, "example_models", test_subfolder, "stackup.json")
        stackup_json = json.load(open(fpath, "r"))

        edbapp = Edb(edbversion=desktop_version)
        edbapp.stackup.load(fpath)
        edbapp.close()

        edbapp = Edb(edbversion=desktop_version)
        edbapp.stackup.load(stackup_json)
        edbapp.close()

    def test_126_comp_def(self):
        source_path = os.path.join(local_path, "example_models", test_subfolder, "ANSYS-HSD_V1.aedb")
        target_path = os.path.join(self.local_scratch.path, "test_0126.aedb")
        self.local_scratch.copyfolder(source_path, target_path)
        edbapp = Edb(target_path, edbversion=desktop_version)
        assert edbapp.components.components
        assert edbapp.components.definitions
        comp_def = edbapp.components.definitions["CAPC2012X12N"]
        assert comp_def
        comp_def.part_name = "CAPC2012X12N_new"
        assert comp_def.part_name == "CAPC2012X12N_new"
        assert len(comp_def.components) > 0
        cap = edbapp.components.definitions["CAPC2012X12N_new"]
        assert cap.type == "Capacitor"
        cap.type = "Resistor"
        assert cap.type == "Resistor"

        export_path = os.path.join(self.local_scratch.path, "comp_definition.csv")
        assert edbapp.components.export_definition(export_path)
        assert edbapp.components.import_definition(export_path)

        assert edbapp.components.definitions["CAPC3216X180X20ML20"].assign_rlc_model(1, 2, 3)
        sparam_path = os.path.join(local_path, "example_models", test_subfolder, "GRM32_DC0V_25degC_series.s2p")
        assert edbapp.components.definitions["CAPC3216X180X55ML20T25"].assign_s_param_model(sparam_path)
        spice_path = os.path.join(local_path, "example_models", test_subfolder, "GRM32_DC0V_25degC.mod")
        assert edbapp.components.definitions["CAPMP7343X31N"].assign_spice_model(spice_path)
        edbapp.close()

    def test_127_material(self):
        source_path = os.path.join(local_path, "example_models", test_subfolder, "ANSYS-HSD_V1.aedb")
        target_path = os.path.join(self.local_scratch.path, "test_0127.aedb")
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
        edbapp.close()
        edbapp = Edb(edbversion=desktop_version)
        assert "air" in edbapp.materials.materials
        edbapp.close()

    def test_128_microvias(self):
        source_path = os.path.join(local_path, "example_models", test_subfolder, "padstacks.aedb")
        target_path = os.path.join(self.local_scratch.path, "test_128_microvias.aedb")
        self.local_scratch.copyfolder(source_path, target_path)
        edbapp = Edb(target_path, edbversion=desktop_version)
        assert edbapp.padstacks.definitions["Padstack_Circle"].convert_to_3d_microvias(False)
        assert edbapp.padstacks.definitions["Padstack_Rectangle"].convert_to_3d_microvias(False, hole_wall_angle=10)
        assert edbapp.padstacks.definitions["Padstack_Polygon_p12"].convert_to_3d_microvias(False)
        edbapp.close()

    def test_129_split_microvias(self):
        edbapp = Edb(self.target_path4, edbversion=desktop_version)
        assert len(edbapp.padstacks.definitions["C4_POWER_1"].split_to_microvias()) > 0
        edbapp.close()

    def test_129_hfss_simulation_setup(self):
        source_path = os.path.join(local_path, "example_models", test_subfolder, "ANSYS-HSD_V1.aedb")
        target_path = os.path.join(self.local_scratch.path, "test_0129.aedb")
        self.local_scratch.copyfolder(source_path, target_path)
        edbapp = Edb(target_path, edbversion=desktop_version)
        setup1 = edbapp.create_hfss_setup("setup1")
        assert setup1.set_solution_single_frequency()
        assert setup1.set_solution_multi_frequencies()
        assert setup1.set_solution_broadband()

        setup1.hfss_solver_settings.enhanced_low_freq_accuracy = True
        setup1.hfss_solver_settings.order_basis = "first"
        setup1.hfss_solver_settings.relative_residual = 0.0002
        setup1.hfss_solver_settings.use_shell_elements = True

        setup1b = edbapp.setups["setup1"]
        hfss_solver_settings = edbapp.setups["setup1"].hfss_solver_settings
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

        assert edbapp.setups["setup1"].adaptive_settings.adapt_type == "kBroadband"
        assert not edbapp.setups["setup1"].adaptive_settings.basic
        assert edbapp.setups["setup1"].adaptive_settings.max_refinement == 1000001
        assert edbapp.setups["setup1"].adaptive_settings.max_refine_per_pass == 20
        assert edbapp.setups["setup1"].adaptive_settings.min_passes == 2
        assert edbapp.setups["setup1"].adaptive_settings.save_fields
        assert edbapp.setups["setup1"].adaptive_settings.save_rad_field_only
        # assert adaptive_settings.use_convergence_matrix
        assert edbapp.setups["setup1"].adaptive_settings.use_max_refinement

        setup1.defeature_settings.defeature_abs_length = "1um"
        setup1.defeature_settings.defeature_ratio = 1e-5
        setup1.defeature_settings.healing_option = 0
        setup1.defeature_settings.model_type = 1
        setup1.defeature_settings.remove_floating_geometry = True
        setup1.defeature_settings.small_void_area = 0.1
        setup1.defeature_settings.union_polygons = False
        setup1.defeature_settings.use_defeature = False
        setup1.defeature_settings.use_defeature_abs_length = True

        defeature_settings = edbapp.setups["setup1"].defeature_settings
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

        via_settings = edbapp.setups["setup1"].via_settings
        assert via_settings.via_density == 1
        assert via_settings.via_material == "pec"
        assert via_settings.via_num_sides == 8
        # assert via_settings.via_style == "kNum25DViaStyle"

        advanced_mesh_settings = setup1.advanced_mesh_settings
        advanced_mesh_settings.layer_snap_tol = "1e-6"
        advanced_mesh_settings.mesh_display_attributes = "#0000001"
        advanced_mesh_settings.replace_3d_triangles = False

        advanced_mesh_settings = edbapp.setups["setup1"].advanced_mesh_settings
        assert advanced_mesh_settings.layer_snap_tol == "1e-6"
        assert advanced_mesh_settings.mesh_display_attributes == "#0000001"
        assert not advanced_mesh_settings.replace_3d_triangles

        curve_approx_settings = setup1.curve_approx_settings
        curve_approx_settings.arc_angle = "15deg"
        curve_approx_settings.arc_to_chord_error = "0.1"
        curve_approx_settings.max_arc_points = 12
        curve_approx_settings.start_azimuth = "1"
        curve_approx_settings.use_arc_to_chord_error = True

        curve_approx_settings = edbapp.setups["setup1"].curve_approx_settings
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

        dcr_settings = edbapp.setups["setup1"].dcr_settings
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

        edbapp.setups["setup1"].name = "setup1a"
        assert "setup1" not in edbapp.setups
        assert "setup1a" in edbapp.setups

        mop = edbapp.setups["setup1a"].add_length_mesh_operation({"GND": ["1_Top", "16_Bottom"]}, "m1")
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

        mop = edbapp.setups["setup1a"].add_skin_depth_mesh_operation({"GND": ["1_Top", "16_Bottom"]})
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
        edbapp.close()

    def test_130_siwave_dc_simulation_setup(self):
        setup1 = self.edbapp.create_siwave_dc_setup("DC1")
        setup1.dc_settings.restore_default()
        setup1.dc_advanced_settings.restore_default()

        settings = self.edbapp.setups["DC1"].get_configurations()
        for k, v in setup1.dc_settings.defaults.items():
            if k in ["compute_inductance", "plot_jv"]:
                continue
            print(k)
            assert settings["dc_settings"][k] == v

        for k, v in setup1.dc_advanced_settings.defaults.items():
            print(k)
            assert settings["dc_advanced_settings"][k] == v

        for p in [0, 1, 2]:
            setup1.set_dc_slider(p)
            settings = self.edbapp.setups["DC1"].get_configurations()
            for k, v in setup1.dc_settings.dc_defaults.items():
                print(k)
                assert settings["dc_settings"][k] == v[p]

            for k, v in setup1.dc_advanced_settings.dc_defaults.items():
                print(k)
                assert settings["dc_advanced_settings"][k] == v[p]

    def test_131_siwave_ac_simulation_setup(self):
        setup1 = self.edbapp.create_siwave_syz_setup("AC1")
        assert setup1.name == "AC1"
        assert setup1.enabled
        setup1.advanced_settings.restore_default()

        settings = self.edbapp.setups["AC1"].get_configurations()
        for k, v in setup1.advanced_settings.defaults.items():
            if k in ["min_plane_area_to_mesh"]:
                continue
            assert settings["advanced_settings"][k] == v

        for p in [0, 1, 2]:
            setup1.set_si_slider(p)
            settings = self.edbapp.setups["AC1"].get_configurations()
            for k, v in setup1.advanced_settings.si_defaults.items():
                assert settings["advanced_settings"][k] == v[p]

        for p in [0, 1, 2]:
            setup1.set_pi_slider(p)
            settings = self.edbapp.setups["AC1"].get_configurations()
            for k, v in setup1.advanced_settings.pi_defaults.items():
                assert settings["advanced_settings"][k] == v[p]

        sweep = setup1.add_frequency_sweep(
            "sweep1",
            frequency_sweep=[
                ["linear count", "0", "1kHz", 1],
                ["log scale", "1kHz", "0.1GHz", 10],
                ["linear scale", "0.1GHz", "10GHz", "0.1GHz"],
            ],
        )
        assert "0" in sweep.frequencies
        assert not sweep.adaptive_sampling
        assert not sweep.adv_dc_extrapolation
        assert sweep.auto_s_mat_only_solve
        assert not sweep.enforce_causality
        assert not sweep.enforce_dc_and_causality
        assert sweep.enforce_passivity
        assert sweep.freq_sweep_type == "kInterpolatingSweep"
        assert sweep.interpolation_use_full_basis
        assert sweep.interpolation_use_port_impedance
        assert sweep.interpolation_use_prop_const
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
        sweep.compute_dc_point = True
        sweep.auto_s_mat_only_solve = False
        sweep.enforce_causality = True
        sweep.enforce_dc_and_causality = True
        sweep.enforce_passivity = False
        sweep.freq_sweep_type = "kDiscreteSweep"
        sweep.interpolation_use_full_basis = False
        sweep.interpolation_use_port_impedance = False
        sweep.interpolation_use_prop_const = False
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
        assert sweep.compute_dc_point
        assert not sweep.auto_s_mat_only_solve
        assert sweep.enforce_causality
        assert sweep.enforce_dc_and_causality
        assert not sweep.enforce_passivity
        assert sweep.freq_sweep_type == "kDiscreteSweep"
        assert not sweep.interpolation_use_full_basis
        assert not sweep.interpolation_use_port_impedance
        assert not sweep.interpolation_use_prop_const
        assert sweep.max_solutions == 200
        assert sweep.min_freq_s_mat_only_solve == "2MHz"
        assert sweep.min_solved_freq == "1Hz"
        assert sweep.passivity_tolerance == 0.0002
        assert sweep.relative_s_error == 0.004
        assert sweep.save_fields
        assert sweep.save_rad_fields_only
        assert sweep.use_q3d_for_dc

    def test_132_via_plating_ratio_check(self):
        assert self.edbapp.padstacks.check_and_fix_via_plating()

    def test_133_siwave_build_ac_prject(self):
        source_path = os.path.join(local_path, "example_models", test_subfolder, "padstacks.aedb")
        target_path = os.path.join(self.local_scratch.path, "test_133_simconfig.aedb")
        self.local_scratch.copyfolder(source_path, target_path)
        edbapp = Edb(target_path, edbversion=desktop_version)
        simconfig = edbapp.new_simulation_configuration()
        simconfig.solver_type = SolverType.SiwaveSYZ
        simconfig.mesh_freq = "40.25GHz"
        edbapp.build_simulation_project(simconfig)
        assert edbapp.siwave_ac_setups[simconfig.setup_name].advanced_settings.mesh_frequency == simconfig.mesh_freq
        edbapp.close()

    def test_134_create_port_between_pin_and_layer(self):
        source_path = os.path.join(local_path, "example_models", test_subfolder, "ANSYS-HSD_V1.aedb")
        target_path = os.path.join(self.local_scratch.path, "test_0134.aedb")
        self.local_scratch.copyfolder(source_path, target_path)
        edbapp = Edb(target_path, edbversion=desktop_version)
        edbapp.siwave.create_port_between_pin_and_layer(
            component_name="U1", pins_name="A27", layer_name="16_Bottom", reference_net="GND"
        )
        U7 = edbapp.components["U7"]
        U7.pins["G7"].create_port()
        port = U7.pins["F7"].create_port(reference=U7.pins["E7"])
        port.is_circuit_port = True
        _, pin_group = edbapp.siwave.create_pin_group_on_net(
            reference_designator="U7", net_name="GND", group_name="U7_GND"
        )
        U7.pins["F7"].create_port(reference=pin_group)
        padstack_instance_terminals = [
            term for term in list(edbapp.terminals.values()) if "PadstackInstanceTerminal" in str(term.type)
        ]
        for term in padstack_instance_terminals:
            assert term.position
        edbapp.close()

    def test_134_siwave_source_setter(self):
        # test needed for the setter with sources created in Siwave prior EDB import
        source_path = os.path.join(local_path, "example_models", test_subfolder, "test_sources.aedb")
        target_path = os.path.join(self.local_scratch.path, "test_134_source_setter.aedb")
        self.local_scratch.copyfolder(source_path, target_path)
        edbapp = Edb(target_path, edbversion=desktop_version)
        sources = list(edbapp.siwave.sources.values())
        sources[0].magnitude = 1.45
        assert sources[0].magnitude == 1.45
        sources[1].magnitude = 1.45
        assert sources[1].magnitude == 1.45
        sources[2].magnitude = 1.45
        assert sources[2].magnitude == 1.45
        edbapp.close()

    def test_135_delete_pingroup(self):
        source_path = os.path.join(local_path, "example_models", test_subfolder, "test_pin_group.aedb")
        target_path = os.path.join(self.local_scratch.path, "test_135_pin_group.aedb")
        self.local_scratch.copyfolder(source_path, target_path)
        edbapp = Edb(target_path, edbversion=desktop_version)
        for pingroup_name, pingroup in edbapp.siwave.pin_groups.items():
            assert pingroup.delete()
        assert not edbapp.siwave.pin_groups
        edbapp.close()

    def test_136_rlc_component_values_getter_setter(self):
        source_path = os.path.join(local_path, "example_models", test_subfolder, "ANSYS-HSD_V1.aedb")
        target_path = os.path.join(self.local_scratch.path, "test_0136.aedb")
        self.local_scratch.copyfolder(source_path, target_path)
        edbapp = Edb(target_path, edbversion=desktop_version)
        components_to_change = [res for res in list(edbapp.components.Others.values()) if res.partname == "A93549-027"]
        for res in components_to_change:
            res.type = "Resistor"
            res.res_value = [25, 0, 0]
            res.res_value = 10
            assert res.res_value == 10
            res.rlc_values = [20, 1e-9, 1e-12]
            assert res.res_value == 20
            assert res.ind_value == 1e-9
            assert res.cap_value == 1e-12
            res.res_value = 12.5
            assert res.res_value == 12.5 and res.ind_value == 1e-9 and res.cap_value == 1e-12
            res.ind_value = 5e-9
            assert res.res_value == 12.5 and res.ind_value == 5e-9 and res.cap_value == 1e-12
            res.cap_value = 8e-12
            assert res.res_value == 12.5 and res.ind_value == 5e-9 and res.cap_value == 8e-12
        edbapp.close()

    def test_137_design_options(self):
        self.edbapp.design_options.suppress_pads = False
        assert not self.edbapp.design_options.suppress_pads
        self.edbapp.design_options.antipads_always_on = True
        assert self.edbapp.design_options.antipads_always_on

    def test_138_pins(self):
        assert len(self.edbapp.pins) > 0

    def test_130_create_padstack_instance(self):
        edb = Edb(edbversion=desktop_version)
        edb.stackup.add_layer(layer_name="1_Top", fillMaterial="AIR", thickness="30um")
        edb.stackup.add_layer(layer_name="contact", fillMaterial="AIR", thickness="100um", base_layer="1_Top")

        pad = edb.padstacks.create(
            pad_shape="Rectangle",
            padstackname="pad",
            x_size="350um",
            y_size="500um",
            holediam=0,
        )
        pad_instance1 = edb.padstacks.place(position=["-0.65mm", "-0.665mm"], definition_name="pad")
        assert pad_instance1
        pad_instance1.start_layer = "1_Top"
        pad_instance1.stop_layer = "1_Top"
        assert pad_instance1.start_layer == "1_Top"
        assert pad_instance1.stop_layer == "1_Top"

        assert edb.padstacks.create(pad_shape="Circle", padstackname="pad2", paddiam="350um", holediam="15um")
        pad_instance2 = edb.padstacks.place(position=["-0.65mm", "-0.665mm"], definition_name="pad2")
        assert pad_instance2
        pad_instance2.start_layer = "1_Top"
        pad_instance2.stop_layer = "1_Top"
        assert pad_instance2.start_layer == "1_Top"
        assert pad_instance2.stop_layer == "1_Top"

        assert edb.padstacks.create(
            pad_shape="Circle",
            padstackname="test2",
            paddiam="400um",
            holediam="200um",
            antipad_shape="Rectangle",
            anti_pad_x_size="700um",
            anti_pad_y_size="800um",
            start_layer="1_Top",
            stop_layer="1_Top",
        )

        pad_instance3 = edb.padstacks.place(position=["-1.65mm", "-1.665mm"], definition_name="test2")
        assert pad_instance3.start_layer == "1_Top"
        assert pad_instance3.stop_layer == "1_Top"
        pad_instance3.dcir_equipotential_region = True
        assert pad_instance3.dcir_equipotential_region
        pad_instance3.dcir_equipotential_region = False
        assert not pad_instance3.dcir_equipotential_region

        trace = edb.modeler.create_trace([[0, 0], [0, 10e-3]], "1_Top", "0.1mm", "trace_with_via_fence")
        edb.padstacks.create_padstack("via_0")
        trace.create_via_fence("1mm", "1mm", "via_0")

        edb.close()

    def test_131_assign_hfss_extent_non_multiple_with_simconfig(self):
        edb = Edb()
        edb.stackup.add_layer(layer_name="GND", fillMaterial="AIR", thickness="30um")
        edb.stackup.add_layer(layer_name="FR4", base_layer="gnd", thickness="250um")
        edb.stackup.add_layer(layer_name="SIGNAL", base_layer="FR4", thickness="30um")
        edb.modeler.create_trace(layer_name="SIGNAL", width=0.02, net_name="net1", path_list=[[-1e3, 0, 1e-3, 0]])
        edb.modeler.create_rectangle(
            layer_name="GND",
            representation_type="CenterWidthHeight",
            center_point=["0mm", "0mm"],
            width="4mm",
            height="4mm",
            net_name="GND",
        )
        sim_setup = edb.new_simulation_configuration()
        sim_setup.signal_nets = ["net1"]
        # sim_setup.power_nets = ["GND"]
        sim_setup.use_dielectric_extent_multiple = False
        sim_setup.use_airbox_horizontal_extent_multiple = False
        sim_setup.use_airbox_negative_vertical_extent_multiple = False
        sim_setup.use_airbox_positive_vertical_extent_multiple = False
        sim_setup.dielectric_extent = 0.0005
        sim_setup.airbox_horizontal_extent = 0.001
        sim_setup.airbox_negative_vertical_extent = 0.05
        sim_setup.airbox_positive_vertical_extent = 0.04
        sim_setup.add_frequency_sweep = False
        sim_setup.include_only_selected_nets = True
        sim_setup.do_cutout_subdesign = False
        sim_setup.generate_excitations = False
        edb.build_simulation_project(sim_setup)
        hfss_ext_info = edb.active_cell.GetHFSSExtentInfo()
        assert list(edb.nets.nets.values())[0].name == "net1"
        assert not edb.setups["Pyaedt_setup"].frequency_sweeps
        assert hfss_ext_info
        assert hfss_ext_info.AirBoxHorizontalExtent.Item1 == 0.001
        assert not hfss_ext_info.AirBoxHorizontalExtent.Item2
        assert hfss_ext_info.AirBoxNegativeVerticalExtent.Item1 == 0.05
        assert not hfss_ext_info.AirBoxNegativeVerticalExtent.Item2
        assert hfss_ext_info.AirBoxPositiveVerticalExtent.Item1 == 0.04
        assert not hfss_ext_info.AirBoxPositiveVerticalExtent.Item2
        assert hfss_ext_info.DielectricExtentSize.Item1 == 0.0005
        assert not hfss_ext_info.AirBoxPositiveVerticalExtent.Item2
        edb.close()

    def test_132_assign_hfss_extent_multiple_with_simconfig(self):
        edb = Edb()
        edb.stackup.add_layer(layer_name="GND", fillMaterial="AIR", thickness="30um")
        edb.stackup.add_layer(layer_name="FR4", base_layer="gnd", thickness="250um")
        edb.stackup.add_layer(layer_name="SIGNAL", base_layer="FR4", thickness="30um")
        edb.modeler.create_trace(layer_name="SIGNAL", width=0.02, net_name="net1", path_list=[[-1e3, 0, 1e-3, 0]])
        edb.modeler.create_rectangle(
            layer_name="GND",
            representation_type="CenterWidthHeight",
            center_point=["0mm", "0mm"],
            width="4mm",
            height="4mm",
            net_name="GND",
        )
        sim_setup = edb.new_simulation_configuration()
        sim_setup.signal_nets = ["net1"]
        sim_setup.power_nets = ["GND"]
        sim_setup.use_dielectric_extent_multiple = True
        sim_setup.use_airbox_horizontal_extent_multiple = True
        sim_setup.use_airbox_negative_vertical_extent_multiple = True
        sim_setup.use_airbox_positive_vertical_extent_multiple = True
        sim_setup.dielectric_extent = 0.0005
        sim_setup.airbox_horizontal_extent = 0.001
        sim_setup.airbox_negative_vertical_extent = 0.05
        sim_setup.airbox_positive_vertical_extent = 0.04
        edb.build_simulation_project(sim_setup)
        hfss_ext_info = edb.active_cell.GetHFSSExtentInfo()
        assert hfss_ext_info
        assert hfss_ext_info.AirBoxHorizontalExtent.Item1 == 0.001
        assert hfss_ext_info.AirBoxHorizontalExtent.Item2
        assert hfss_ext_info.AirBoxNegativeVerticalExtent.Item1 == 0.05
        assert hfss_ext_info.AirBoxNegativeVerticalExtent.Item2
        assert hfss_ext_info.AirBoxPositiveVerticalExtent.Item1 == 0.04
        assert hfss_ext_info.AirBoxPositiveVerticalExtent.Item2
        assert hfss_ext_info.DielectricExtentSize.Item1 == 0.0005
        assert hfss_ext_info.AirBoxPositiveVerticalExtent.Item2
        edb.close()

    def test_133_stackup_properties(self):
        edb = Edb(edbversion=desktop_version)
        edb.stackup.add_layer(layer_name="gnd", fillMaterial="AIR", thickness="10um")
        edb.stackup.add_layer(layer_name="diel1", fillMaterial="AIR", thickness="200um", base_layer="gnd")
        edb.stackup.add_layer(layer_name="sig1", fillMaterial="AIR", thickness="10um", base_layer="diel1")
        edb.stackup.add_layer(layer_name="diel2", fillMaterial="AIR", thickness="200um", base_layer="sig1")
        edb.stackup.add_layer(layer_name="sig3", fillMaterial="AIR", thickness="10um", base_layer="diel2")
        assert edb.stackup.thickness == 0.00043
        assert edb.stackup.num_layers == 5
        edb.close()

    def test_134_hfss_extent_info(self):
        from pyaedt import settings

        if not settings.use_grpc_edb_api:
            from pyedb.legacy.edb_core.edb_data.primitives_data import EDBPrimitives as EDBPrimitives
        else:
            raise Exception("gRPC Not yet available.")

        config = {
            "air_box_horizontal_extent_enabled": False,
            "air_box_horizontal_extent": 0.01,
            "air_box_positive_vertical_extent": 0.3,
            "air_box_positive_vertical_extent_enabled": False,
            "air_box_negative_vertical_extent": 0.1,
            "air_box_negative_vertical_extent_enabled": False,
            "base_polygon": self.edbapp.modeler.polygons[0],
            "dielectric_base_polygon": self.edbapp.modeler.polygons[1],
            "dielectric_extent_size": 0.1,
            "dielectric_extent_size_enabled": False,
            "dielectric_extent_type": "Conforming",
            "extent_type": "Conforming",
            "honor_user_dielectric": False,
            "is_pml_visible": False,
            "open_region_type": "PML",
            "operating_freq": "2GHz",
            "radiation_level": 1,
            "sync_air_box_vertical_extent": False,
            "use_open_region": False,
            "use_xy_data_extent_for_vertical_expansion": False,
            "truncate_air_box_at_ground": True,
        }
        hfss_extent_info = self.edbapp.hfss.hfss_extent_info
        hfss_extent_info.load_config(config)
        exported_config = hfss_extent_info.export_config()
        for i, j in exported_config.items():
            if not i in config:
                continue
            if isinstance(j, EDBPrimitives):
                assert j.id == config[i].id
            elif isinstance(j, EdbValue):
                assert j.tofloat == hfss_extent_info._get_edb_value(config[i]).ToDouble()
            else:
                assert j == config[i]

    def test_134_create_port_on_pin(self):
        source_path = os.path.join(local_path, "example_models", test_subfolder, "ANSYS-HSD_V1.aedb")
        target_path = os.path.join(self.local_scratch.path, "test_0134b.aedb")
        self.local_scratch.copyfolder(source_path, target_path)
        edbapp = Edb(target_path, edbversion=desktop_version)
        pin = "A24"
        ref_pins = [pin for pin in list(edbapp.components["U1"].pins.values()) if pin.net_name == "GND"]
        assert edbapp.components.create_port_on_pins(refdes="U1", pins=pin, reference_pins=ref_pins)
        assert edbapp.components.create_port_on_pins(refdes="U1", pins="C1", reference_pins=["A11"])
        assert edbapp.components.create_port_on_pins(refdes="U1", pins="C2", reference_pins=["A11"])
        assert edbapp.components.create_port_on_pins(refdes="U1", pins=["A24"], reference_pins=["A11", "A16"])
        assert edbapp.components.create_port_on_pins(refdes="U1", pins=["A26"], reference_pins=["A11", "A16", "A17"])
        assert edbapp.components.create_port_on_pins(refdes="U1", pins=["A28"], reference_pins=["A11", "A16"])
        edbapp.close()

    def test_138_import_gds_from_tech(self):
        from pyaedt import settings

        if not settings.use_grpc_edb_api:
            from pyedb.legacy.edb_core.edb_data.control_file import ControlFile
        else:
            raise Exception("gRPC Not yet available.")

        c_file_in = os.path.join(
            local_path, "example_models", "cad", "GDS", "sky130_fictitious_dtc_example_control_no_map.xml"
        )
        c_map = os.path.join(local_path, "example_models", "cad", "GDS", "dummy_layermap.map")
        gds_in = os.path.join(local_path, "example_models", "cad", "GDS", "sky130_fictitious_dtc_example.gds")
        gds_out = os.path.join(self.local_scratch.path, "sky130_fictitious_dtc_example.gds")
        self.local_scratch.copyfile(gds_in, gds_out)

        c = ControlFile(c_file_in, layer_map=c_map)
        setup = c.setups.add_setup("Setup1", "1GHz")
        setup.add_sweep("Sweep1", "0.01GHz", "5GHz", "0.1GHz")
        c.boundaries.units = "um"
        c.stackup.units = "um"
        c.boundaries.add_port("P1", x1=223.7, y1=222.6, layer1="Metal6", x2=223.7, y2=100, layer2="Metal6")
        c.boundaries.add_extent()
        comp = c.components.add_component("B1", "BGA", "IC", "Flip chip", "Cylinder")
        comp.solder_diameter = "65um"
        comp.add_pin("1", "81.28", "84.6", "met2")
        comp.add_pin("2", "211.28", "84.6", "met2")
        comp.add_pin("3", "211.28", "214.6", "met2")
        comp.add_pin("4", "81.28", "214.6", "met2")
        for via in c.stackup.vias:
            via.create_via_group = True
            via.snap_via_group = True
        c.write_xml(os.path.join(self.local_scratch.path, "test_138.xml"))
        c.import_options.import_dummy_nets = True
        from pyaedt import Edb

        edb = Edb(
            gds_out, edbversion=desktop_version, technology_file=os.path.join(self.local_scratch.path, "test_138.xml")
        )

        assert edb
        assert "P1" in edb.excitations
        assert "Setup1" in edb.setups
        assert "B1" in edb.components.components
        edb.close()

    def test_139_test_database(self):
        assert isinstance(self.edbapp.dataset_defs, list)
        assert isinstance(self.edbapp.material_defs, list)
        assert isinstance(self.edbapp.component_defs, list)
        assert isinstance(self.edbapp.package_defs, list)

        assert isinstance(self.edbapp.padstack_defs, list)
        assert isinstance(self.edbapp.jedec5_bondwire_defs, list)
        assert isinstance(self.edbapp.jedec4_bondwire_defs, list)
        assert isinstance(self.edbapp.apd_bondwire_defs, list)
        assert self.edbapp.source_version == ""
        self.edbapp.source_version = "2022.2"
        assert self.edbapp.source == ""
        assert self.edbapp.scale(1.0)
        assert isinstance(self.edbapp.version, tuple)
        assert isinstance(self.edbapp.footprint_cells, list)

    def test_140_defeature(self):
        assert self.edbapp.modeler.defeature_polygon(self.edbapp.modeler.primitives_by_net["GND"][-1], 0.01)

    def test_141_primitives_boolean_operation(self):
        edb = Edb()
        edb.stackup.add_layer(layer_name="test")
        x = edb.modeler.create_polygon(
            layer_name="test", main_shape=[[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]]
        )
        assert x
        x_hole1 = edb.modeler.create_polygon(
            layer_name="test", main_shape=[[1.0, 1.0], [4.5, 1.0], [4.5, 9.0], [1.0, 9.0]]
        )
        x_hole2 = edb.modeler.create_polygon(
            layer_name="test", main_shape=[[4.5, 1.0], [9.0, 1.0], [9.0, 9.0], [4.5, 9.0]]
        )
        x = x.subtract([x_hole1, x_hole2])[0]
        assert x
        y = edb.modeler.create_polygon(layer_name="foo", main_shape=[[4.0, 3.0], [6.0, 3.0], [6.0, 6.0], [4.0, 6.0]])
        z = x.subtract(y)
        assert z
        edb.stackup.add_layer(layer_name="foo")
        x = edb.modeler.create_polygon(
            layer_name="foo", main_shape=[[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]]
        )
        x_hole = edb.modeler.create_polygon(
            layer_name="foo", main_shape=[[1.0, 1.0], [9.0, 1.0], [9.0, 9.0], [1.0, 9.0]]
        )
        y = x.subtract(x_hole)[0]
        z = edb.modeler.create_polygon(
            layer_name="foo", main_shape=[[-15.0, 5.0], [15.0, 5.0], [15.0, 6.0], [-15.0, 6.0]]
        )
        assert y.intersect(z)

        edb.stackup.add_layer(layer_name="test2")
        x = edb.modeler.create_polygon(
            layer_name="test2", main_shape=[[0.0, 0.0], [10.0, 0.0], [10.0, 10.0], [0.0, 10.0]]
        )
        x_hole = edb.modeler.create_polygon(
            layer_name="test2", main_shape=[[1.0, 1.0], [9.0, 1.0], [9.0, 9.0], [1.0, 9.0]]
        )
        y = x.subtract(x_hole)[0]
        assert y.voids
        y_clone = y.clone()
        assert y_clone.voids
        edb.close()

    def test_142_replace_rlc_by_gap_boundaries(self):
        source_path = os.path.join(local_path, "example_models", test_subfolder, "ANSYS-HSD_V1.aedb")
        target_path = os.path.join(self.local_scratch.path, "ANSYS-HSD_V1_boundaries.aedb")
        self.local_scratch.copyfolder(source_path, target_path)
        edbapp = Edb(target_path, edbversion=desktop_version)
        for refdes, cmp in edbapp.components.components.items():
            edbapp.components.replace_rlc_by_gap_boundaries(refdes)
        rlc_list = [
            term for term in list(edbapp.active_layout.Terminals) if str(term.GetBoundaryType()) == "RlcBoundary"
        ]
        assert len(rlc_list) == 944
        edbapp.close()

    def test_143_backdrill_via_with_offset(self):
        edb = Edb(edbversion=desktop_version)
        edb.stackup.add_layer(layer_name="bot")
        edb.stackup.add_layer(layer_name="diel1", base_layer="bot", layer_type="dielectric", thickness="127um")
        edb.stackup.add_layer(layer_name="signal1", base_layer="diel1")
        edb.stackup.add_layer(layer_name="diel2", base_layer="signal1", layer_type="dielectric", thickness="127um")
        edb.stackup.add_layer(layer_name="signal2", base_layer="diel2")
        edb.stackup.add_layer(layer_name="diel3", base_layer="signal2", layer_type="dielectric", thickness="127um")
        edb.stackup.add_layer(layer_name="top", base_layer="diel2")
        edb.padstacks.create(padstackname="test1")
        padstack_instance = edb.padstacks.place(position=[0, 0], net_name="test", definition_name="test1")
        edb.padstacks.definitions["test1"].hole_range = "through"
        padstack_instance.set_backdrill_top(drill_depth="signal1", drill_diameter="200um", offset="100um")
        assert len(padstack_instance.backdrill_top) == 3
        assert padstack_instance.backdrill_top[0] == "signal1"
        assert padstack_instance.backdrill_top[1] == "200um"
        assert padstack_instance.backdrill_top[2] == "100um"
        padstack_instance2 = edb.padstacks.place(position=[0.5, 0.5], net_name="test", definition_name="test1")
        padstack_instance2.set_backdrill_bottom(drill_depth="signal1", drill_diameter="200um", offset="100um")
        assert len(padstack_instance2.backdrill_bottom) == 3
        assert padstack_instance2.backdrill_bottom[0] == "signal1"
        assert padstack_instance2.backdrill_bottom[1] == "200um"
        assert padstack_instance2.backdrill_bottom[2] == "100um"
        edb.close()

    def test_143_add_layer_api_with_control_file(self):
        from pyaedt import settings

        if not settings.use_grpc_edb_api:
            from pyedb.legacy.edb_core.edb_data.control_file import ControlFile
        else:
            raise Exception("gRPC Not yet available.")

        ctrl = ControlFile()
        # Material
        ctrl.stackup.add_material(material_name="Copper", conductivity=5.56e7)
        ctrl.stackup.add_material(material_name="BCB", permittivity=2.7)
        ctrl.stackup.add_material(material_name="Silicon", conductivity=0.04)
        ctrl.stackup.add_material(material_name="SiliconOxide", conductivity=4.4)
        ctrl.stackup.units = "um"
        assert len(ctrl.stackup.materials) == 4
        assert ctrl.stackup.units == "um"
        # Dielectrics
        ctrl.stackup.add_dielectric(material="Silicon", layer_name="Silicon", thickness=180)
        ctrl.stackup.add_dielectric(layer_index=1, material="SiliconOxide", layer_name="USG1", thickness=1.2)
        assert next(diel for diel in ctrl.stackup.dielectrics if diel.name == "USG1").properties["Index"] == 1
        ctrl.stackup.add_dielectric(material="BCB", layer_name="BCB2", thickness=9.5, base_layer="USG1")
        ctrl.stackup.add_dielectric(
            material="BCB", layer_name="BCB1", thickness=4.1, base_layer="BCB2", add_on_top=False
        )
        ctrl.stackup.add_dielectric(layer_index=4, material="BCB", layer_name="BCB3", thickness=6.5)
        assert ctrl.stackup.dielectrics[0].properties["Index"] == 0
        assert ctrl.stackup.dielectrics[1].properties["Index"] == 1
        assert ctrl.stackup.dielectrics[2].properties["Index"] == 3
        assert ctrl.stackup.dielectrics[3].properties["Index"] == 2
        assert ctrl.stackup.dielectrics[4].properties["Index"] == 4
        # Metal layer
        ctrl.stackup.add_layer(
            layer_name="9", elevation=185.3, material="Copper", target_layer="meta2", gds_type=0, thickness=6
        )
        assert [layer for layer in ctrl.stackup.layers if layer.name == "9"]
        ctrl.stackup.add_layer(
            layer_name="15", elevation=194.8, material="Copper", target_layer="meta3", gds_type=0, thickness=3
        )
        assert [layer for layer in ctrl.stackup.layers if layer.name == "15"]
        # Via layer
        ctrl.stackup.add_via(
            layer_name="14", material="Copper", target_layer="via2", start_layer="meta2", stop_layer="meta3", gds_type=0
        )
        assert [layer for layer in ctrl.stackup.vias if layer.name == "14"]
        # Port
        ctrl.boundaries.add_port(
            "test_port", x1=-21.1, y1=-288.7, layer1="meta3", x2=21.1, y2=-288.7, layer2="meta3", z0=50
        )
        assert ctrl.boundaries.ports
        # setup using q3D for DC point
        setup = ctrl.setups.add_setup("test_setup", "10GHz")
        assert setup
        setup.add_sweep(
            name="test_sweep",
            start="0GHz",
            stop="20GHz",
            step="10MHz",
            sweep_type="Interpolating",
            step_type="LinearStep",
            use_q3d=True,
        )
        assert setup.sweeps

    def test_144_search_reference_pins(self):
        source_path = os.path.join(local_path, "example_models", test_subfolder, "ANSYS-HSD_V1.aedb")
        target_path = os.path.join(self.local_scratch.path, "ANSYS-HSD_V1_boundaries.aedb")
        self.local_scratch.copyfolder(source_path, target_path)
        edbapp = Edb(target_path, edbversion=desktop_version)
        pin = edbapp.components.instances["J5"].pins["19"]
        assert pin
        ref_pins = pin.get_reference_pins(reference_net="GND", search_radius=5e-3, max_limit=0, component_only=True)
        assert len(ref_pins) == 3
        reference_pins = edbapp.padstacks.get_reference_pins(
            positive_pin=pin, reference_net="GND", search_radius=5e-3, max_limit=0, component_only=True
        )
        assert len(reference_pins) == 3
        reference_pins = edbapp.padstacks.get_reference_pins(
            positive_pin=pin, reference_net="GND", search_radius=5e-3, max_limit=2, component_only=True
        )
        assert len(reference_pins) == 2
        reference_pins = edbapp.padstacks.get_reference_pins(
            positive_pin=pin, reference_net="GND", search_radius=5e-3, max_limit=0, component_only=False
        )
        assert len(reference_pins) == 11
        edbapp.close()

    def test_145_arc_data(self):
        assert len(self.edbapp.nets["1.2V_DVDDL"].primitives[0].arcs) > 0
        assert self.edbapp.nets["1.2V_DVDDL"].primitives[0].arcs[0].start
        assert self.edbapp.nets["1.2V_DVDDL"].primitives[0].arcs[0].end
        assert self.edbapp.nets["1.2V_DVDDL"].primitives[0].arcs[0].height

    def test_145_via_volume(self):
        #
        vias = [
            via
            for via in list(self.edbapp.padstacks.padstack_instances.values())
            if not via.start_layer == via.stop_layer
        ]
        assert vias[0].metal_volume
        assert vias[1].metal_volume

    def test_146_export_ipc(self):
        source_path = os.path.join(local_path, "example_models", test_subfolder, "ANSYS-HSD_V1.aedb")
        target_path = os.path.join(self.local_scratch.path, "test_ipc", "ANSYS-HSD_V1_boundaries.aedb")
        self.local_scratch.copyfolder(source_path, target_path)
        edbapp = Edb(target_path, edbversion=desktop_version)
        xml_file = os.path.join(target_path, "test.xml")
        edbapp.export_to_ipc2581(xml_file)
        assert os.path.isfile(xml_file)
        ipc_edb = Edb(xml_file, edbversion=desktop_version)
        ipc_stats = ipc_edb.get_statistics()
        assert ipc_stats.layout_size == (0.15, 0.0845)
        assert ipc_stats.num_capacitors == 380
        assert ipc_stats.num_discrete_components == 31
        assert ipc_stats.num_inductors == 10
        assert ipc_stats.num_layers == 15
        assert ipc_stats.num_nets == 348
        assert ipc_stats.num_polygons == 139
        assert ipc_stats.num_resistors == 82
        assert ipc_stats.num_traces == 1565
        assert ipc_stats.num_traces == 1565
        assert ipc_stats.num_vias == 4730
        assert ipc_stats.stackup_thickness == 0.001748
        edbapp.close()
        ipc_edb.close()

    def test_147_find_dc_shorts(self):
        source_path = os.path.join(local_path, "example_models", test_subfolder, "ANSYS-HSD_V1.aedb")
        target_path = os.path.join(self.local_scratch.path, "test_dc_shorts", "ANSYS-HSD_V1_dc_shorts.aedb")
        self.local_scratch.copyfolder(source_path, target_path)
        edbapp = Edb(target_path, edbversion=desktop_version)
        dc_shorts = edbapp.layout_validation.dc_shorts()
        assert dc_shorts
        edbapp.nets.nets["DDR4_A0"].name = "DDR4$A0"
        edbapp.layout_validation.illegal_net_names(True)
        edbapp.layout_validation.illegal_rlc_values(True)

        # assert len(dc_shorts) == 20
        assert ["SFPA_Tx_Fault", "PCIe_Gen4_CLKREQ_L"] in dc_shorts
        assert ["VDD_DDR", "GND"] in dc_shorts
        assert len(edbapp.nets["DDR4_DM3"].find_dc_short()) > 0
        edbapp.nets["DDR4_DM3"].find_dc_short(True)
        assert len(edbapp.nets["DDR4_DM3"].find_dc_short()) == 0
        edbapp.close()

    def test_150_material_load_amat(self):
        """Load material from an AMAT file."""
        mat_file = os.path.join(self.edbapp.base_path, "syslib", "Materials.amat")
        assert self.edbapp.materials.load_amat(mat_file)
        material_list = list(self.edbapp.materials.materials.keys())
        assert material_list
        assert len(material_list) > 0
        assert self.edbapp.materials.materials["Rogers RO3003 (tm)"].loss_tangent == 0.0013
        assert self.edbapp.materials.materials["Rogers RO3003 (tm)"].permittivity == 3.0

    def test_151_materials_read_materials(self):
        """Read materials."""
        path = os.path.join(local_path, "example_models", "syslib", "Materials.amat")
        mats = self.edbapp.materials.read_materials(path)
        key = "FC-78"
        assert key in mats
        assert mats[key]["thermal_conductivity"] == 0.062
        assert mats[key]["mass_density"] == 1700
        assert mats[key]["specific_heat"] == 1050
        assert mats[key]["thermal_expansion_coeffcient"] == 0.0016
        key = "Polyflon CuFlon (tm)"
        assert key in mats
        assert mats[key]["permittivity"] == 2.1
        assert mats[key]["tangent_delta"] == 0.00045
        key = "Water(@360K)"
        assert key in mats
        assert mats[key]["thermal_conductivity"] == 0.6743
        assert mats[key]["mass_density"] == 967.4
        assert mats[key]["specific_heat"] == 4206
        assert mats[key]["thermal_expansion_coeffcient"] == 0.0006979
        key = "steel_stainless"
        assert mats[key]["conductivity"] == 1100000
        assert mats[key]["thermal_conductivity"] == 13.8
        assert mats[key]["mass_density"] == 8055
        assert mats[key]["specific_heat"] == 480
        assert mats[key]["thermal_expansion_coeffcient"] == 1.08e-005

    def test_152_simconfig_built_custom_sballs_height(self):
        source_path = os.path.join(local_path, "example_models", test_subfolder, "ANSYS-HSD_V1.aedb")
        target_path = os.path.join(self.local_scratch.path, "test_custom_sball_height", "ANSYS-HSD_V1.aedb")
        self.local_scratch.copyfolder(source_path, target_path)
        json_file = os.path.join(target_path, "simsetup_custom_sballs.json")
        edbapp = Edb(target_path, edbversion=desktop_version)
        simconfig = edbapp.new_simulation_configuration()
        simconfig.import_json(json_file)
        edbapp.build_simulation_project(simconfig)
        assert round(edbapp.components["X1"].solder_ball_height, 6) == 0.00025
        assert round(edbapp.components["U1"].solder_ball_height, 6) == 0.00035
        edbapp.close_edb()

    def test_153_update_padstacks_after_layer_name_changed(self):
        source_path = os.path.join(local_path, "example_models", test_subfolder, "ANSYS-HSD_V1.aedb")
        target_path = os.path.join(self.local_scratch.path, "test_padstack_def_update", "ANSYS-HSD_V1.aedb")
        self.local_scratch.copyfolder(source_path, target_path)

        edbapp = Edb(target_path, edbversion=desktop_version)
        signal_layer_list = [layer for layer in list(edbapp.stackup.stackup_layers.values()) if layer.type == "signal"]
        old_layers = []
        for n_layer, layer in enumerate(signal_layer_list):
            new_name = f"new_signal_name_{n_layer}"
            old_layers.append(layer.name)
            layer.name = new_name
        for layer_name in list(edbapp.stackup.stackup_layers.keys()):
            print(f"New layer name is {layer_name}")
        for padstack_inst in list(edbapp.padstacks.instances.values()):
            assert not [lay for lay in padstack_inst.layer_range_names if lay in old_layers]
        edbapp.close_edb()

    def test_154_create_pec_boundary_ports(self):
        source_path = os.path.join(local_path, "example_models", test_subfolder, "ANSYS-HSD_V1.aedb")
        target_path = os.path.join(self.local_scratch.path, "test_custom_sball_height", "ANSYS-HSD_V1.aedb")
        self.local_scratch.copyfolder(source_path, target_path)
        edbapp = Edb(target_path, edbversion=desktop_version)
        edbapp.components.create_port_on_pins(refdes="U1", pins="AU38", reference_pins="AU37", pec_boundary=True)
        assert edbapp.terminals["Port_GND_U1-AU38"].boundary_type == "PecBoundary"
        assert edbapp.terminals["Port_GND_U1-AU38_ref"].boundary_type == "PecBoundary"
        edbapp.components.deactivate_rlc_component(component="C5", create_circuit_port=True, pec_boundary=True)
        edbapp.components.add_port_on_rlc_component(component="C65", circuit_ports=False, pec_boundary=True)
        assert edbapp.terminals["C5"].boundary_type == "PecBoundary"
        assert edbapp.terminals["C65"].boundary_type == "PecBoundary"

    def test_154_merge_polygon(self):
        source_path = os.path.join(local_path, "example_models", test_subfolder, "test_merge_polygon.aedb")
        target_path = os.path.join(self.local_scratch.path, "test_merge_polygon", "test.aedb")
        self.local_scratch.copyfolder(source_path, target_path)
        edbapp = Edb(target_path, desktop_version)
        assert edbapp.nets.merge_nets_polygons(["net1", "net2"])
        edbapp.close_edb()

    def test_155_layout_auto_parametrization(self):
        source_path = os.path.join(local_path, "example_models", test_subfolder, "ANSYS-HSD_V1.aedb")
        target_path = os.path.join(self.local_scratch.path, "test_auto_parameters", "test.aedb")
        self.local_scratch.copyfolder(source_path, target_path)
        edbapp = Edb(target_path, desktop_version)
        edbapp.auto_parametrize_design(
            layers=True,
            layer_filter="1_Top",
            materials=False,
            via_holes=False,
            pads=False,
            antipads=False,
            traces=False,
        )
        assert "$1_Top_thick" in edbapp.variables
        edbapp.auto_parametrize_design(
            layers=True, materials=False, via_holes=False, pads=False, antipads=False, traces=False
        )
        assert len(list(edbapp.variables.keys())) == len(list(edbapp.stackup.stackup_layers.keys()))
        edbapp.auto_parametrize_design(
            layers=False,
            materials=True,
            via_holes=False,
            pads=False,
            antipads=False,
            traces=False,
            material_filter=["copper"],
        )
        assert "$sigma_copper" in edbapp.variables
        edbapp.auto_parametrize_design(
            layers=False, materials=True, via_holes=False, pads=False, antipads=False, traces=False
        )
        assert len(list(edbapp.variables.values())) == 26
        edbapp.auto_parametrize_design(
            layers=False, materials=False, via_holes=True, pads=False, antipads=False, traces=False
        )
        assert len(list(edbapp.variables.values())) == 65
        edbapp.auto_parametrize_design(
            layers=False, materials=False, via_holes=False, pads=True, antipads=False, traces=False
        )
        assert len(list(edbapp.variables.values())) == 469
        edbapp.auto_parametrize_design(
            layers=False, materials=False, via_holes=False, pads=False, antipads=True, traces=False
        )
        assert len(list(edbapp.variables.values())) == 469
        edbapp.auto_parametrize_design(
            layers=False,
            materials=False,
            via_holes=False,
            pads=False,
            antipads=False,
            traces=True,
            trace_net_filter=["SFPA_Tx_Fault", "SFPA_Tx_Disable", "SFPA_SDA", "SFPA_SCL", "SFPA_Rx_LOS"],
        )
        assert len(list(edbapp.variables.keys())) == 474
        edbapp.auto_parametrize_design(
            layers=False, materials=False, via_holes=False, pads=False, antipads=False, traces=True
        )
        assert len(list(edbapp.variables.values())) == 2308
        edbapp.close_edb()
