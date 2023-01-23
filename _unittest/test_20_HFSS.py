import os
import shutil

from _unittest.conftest import config

try:
    import pytest
except ImportError:
    import _unittest_ironpython.conf_unittest as pytest
# Setup paths for module imports
from _unittest.conftest import BasisTest
from _unittest.conftest import desktop_version
from _unittest.conftest import is_ironpython
from _unittest.conftest import local_path
from _unittest.conftest import settings

# Import required modules
from pyaedt import Hfss
from pyaedt.generic.near_field_import import convert_nearfield_data

test_subfolder = "T20"

if config["desktopVersion"] > "2022.2":
    diff_proj_name = "differential_pairs_231"
else:
    diff_proj_name = "differential_pairs"


class TestClass(BasisTest, object):
    def setup_class(self):
        BasisTest.my_setup(self)
        self.aedtapp = BasisTest.add_app(self, "Test_20")

    def teardown_class(self):
        BasisTest.my_teardown(self)

    def test_01_save(self):
        project_name = "Test_Exercse201119"
        test_project = os.path.join(self.local_scratch.path, project_name + ".aedt")
        self.aedtapp.save_project(test_project)
        assert os.path.exists(test_project)

    def test_01A_check_setup(self):
        assert self.aedtapp.analysis_setup is None

    def test_02_create_primitive(self):
        udp = self.aedtapp.modeler.Position(0, 0, 0)
        coax_dimension = 200
        o1 = self.aedtapp.modeler.create_cylinder(self.aedtapp.AXIS.X, udp, 3, coax_dimension, 0, "inner")
        assert isinstance(o1.id, int)
        o2 = self.aedtapp.modeler.create_cylinder(self.aedtapp.AXIS.X, udp, 10, coax_dimension, 0, "outer")
        assert isinstance(o2.id, int)
        assert self.aedtapp.modeler.subtract(o2, o1, True)

    def test_03_2_assign_material(self):
        udp = self.aedtapp.modeler.Position(0, 0, 0)
        coax_dimension = 200
        cyl_1 = self.aedtapp.modeler.create_cylinder(self.aedtapp.AXIS.X, udp, 10, coax_dimension, 0, "die")
        self.aedtapp.modeler.subtract(cyl_1, "inner", True)
        self.aedtapp.modeler["inner"].material_name = "Copper"
        cyl_1.material_name = "teflon_based"
        assert self.aedtapp.modeler["inner"].material_name == "copper"
        assert cyl_1.material_name == "teflon_based"

    @pytest.mark.parametrize(
        "object_name, kwargs",
        [
            ("inner", {"mat": "copper"}),
            (
                "outer",
                {
                    "mat": "aluminum",
                    "usethickness": True,
                    "thickness": "0.5mm",
                    "istwoside": True,
                    "issheelElement": True,
                    "usehuray": True,
                    "radius": "0.75um",
                    "ratio": "3",
                },
            ),
            ("die", {}),
        ],
    )
    def test_04_assign_coating(self, object_name, kwargs):
        id = self.aedtapp.modeler.get_obj_id(object_name)
        coat = self.aedtapp.assign_coating([id, "die", 41], **kwargs)
        coat.name = "Coating1" + object_name
        assert coat.update()
        material = coat.props.get("Material", "")
        assert material == kwargs.get("mat", "")
        assert not self.aedtapp.assign_coating(["die2", 45], **kwargs)

    def test_05_create_wave_port_from_sheets(self):
        udp = self.aedtapp.modeler.Position(0, 0, 0)
        o5 = self.aedtapp.modeler.create_circle(self.aedtapp.PLANE.YZ, udp, 10, name="sheet1")
        self.aedtapp.solution_type = "Terminal"

        # Wave port cannot be created if the reference conductors are missing.
        assert not self.aedtapp.create_wave_port_from_sheet(o5)

        port = self.aedtapp.create_wave_port_from_sheet(
            o5, 5, self.aedtapp.AxisDir.XNeg, 40, 2, "sheet1_Port", renorm=False, terminal_references=["outer"]
        )
        assert port.name == "sheet1_Port"
        assert port.name in [i.name for i in self.aedtapp.boundaries]
        assert port.props["RenormalizeAllTerminals"] is False

        udp = self.aedtapp.modeler.Position(100, 0, 0)
        o6 = self.aedtapp.modeler.create_circle(self.aedtapp.PLANE.YZ, udp, 10, name="sheet1a")
        port = self.aedtapp.create_wave_port_from_sheet(
            o6, 0, self.aedtapp.AxisDir.XNeg, 40, 2, "sheet1a_Port", renorm=True, terminal_references=["outer"]
        )
        assert port.name == "sheet1a_Port"
        assert port.name in [i.name for i in self.aedtapp.boundaries]
        assert port.props["DoDeembed"] is False

        self.aedtapp.solution_type = "Modal"
        udp = self.aedtapp.modeler.Position(200, 0, 0)
        o6 = self.aedtapp.modeler.create_circle(self.aedtapp.PLANE.YZ, udp, 10, name="sheet2")
        port = self.aedtapp.create_wave_port_from_sheet(o6, 5, self.aedtapp.AxisDir.XPos, 40, 2, "sheet2_Port", True)
        assert port.name == "sheet2_Port"
        assert port.name in [i.name for i in self.aedtapp.boundaries]
        assert port.props["RenormalizeAllTerminals"] is True

        id6 = self.aedtapp.modeler.create_box([20, 20, 20], [10, 10, 2], matname="Copper", name="My_Box")
        id7 = self.aedtapp.modeler.create_box([20, 25, 30], [10, 2, 2], matname="Copper")
        rect = self.aedtapp.modeler.create_rectangle(self.aedtapp.PLANE.YZ, [20, 25, 20], [2, 10])
        ports = self.aedtapp.create_wave_port_from_sheet(
            rect, 5, self.aedtapp.AxisDir.ZNeg, 40, 2, "sheet3_Port", False
        )
        assert ports.name in [i.name for i in self.aedtapp.boundaries]

    def test_06a_create_linear_count_sweep(self):
        setup = self.aedtapp.create_setup("MySetup")
        setup.props["Frequency"] = "1GHz"
        setup.props["BasisOrder"] = 2
        setup.props["MaximumPasses"] = 1
        assert setup.update()
        assert self.aedtapp.create_linear_count_sweep("MySetup", "GHz", 0.8, 1.2, 401)
        assert not self.aedtapp.setups[0].sweeps[0].is_solved
        assert self.aedtapp.create_linear_count_sweep("MySetup", "GHz", 0.8, 1.2, 401)
        assert self.aedtapp.create_linear_count_sweep(
            setupname="MySetup",
            sweepname="MySweep",
            unit="MHz",
            freqstart=1.1e3,
            freqstop=1200.1,
            num_of_freq_points=1234,
            sweep_type="Interpolating",
        )
        assert self.aedtapp.create_linear_count_sweep(
            setupname="MySetup",
            sweepname="MySweep",
            unit="MHz",
            freqstart=1.1e3,
            freqstop=1200.1,
            num_of_freq_points=1234,
            sweep_type="Interpolating",
        )
        assert self.aedtapp.create_linear_count_sweep(
            setupname="MySetup",
            sweepname="MySweepFast",
            unit="MHz",
            freqstart=1.1e3,
            freqstop=1200.1,
            num_of_freq_points=1234,
            sweep_type="Fast",
        )
        num_points = 1752
        freq_start = 1.1e3
        freq_stop = 1200.1
        units = "MHz"
        sweep = self.aedtapp.create_linear_count_sweep(
            setupname="MySetup",
            sweepname=None,
            unit=units,
            freqstart=freq_start,
            freqstop=freq_stop,
            num_of_freq_points=num_points,
        )
        assert sweep.props["RangeCount"] == num_points
        assert sweep.props["RangeStart"] == str(freq_start) + units
        assert sweep.props["RangeEnd"] == str(freq_stop) + units
        assert sweep.props["Type"] == "Discrete"

        # Create a linear count sweep with the incorrect sweep type.
        try:
            sweep = self.aedtapp.create_linear_count_sweep(
                setupname="MySetup",
                sweepname="IncorrectStep",
                unit="MHz",
                freqstart=1.1e3,
                freqstop=1200.1,
                num_of_freq_points=1234,
                sweep_type="Incorrect",
            )
        except AttributeError as e:
            exception_raised = True
            assert (
                e.args[0] == "Invalid value for `sweep_type`. The value must be 'Discrete', 'Interpolating', or 'Fast'."
            )
        assert exception_raised
        self.aedtapp["der_var"] = "1mm"
        self.aedtapp["der_var2"] = "2mm"
        setup2 = self.aedtapp.create_setup("MySetup_2", setuptype=0)
        assert setup2.add_derivatives("der_var")
        assert "der_var" in setup2.get_derivative_variables()
        assert setup2.add_derivatives("der_var2")
        assert "der_var2" in setup2.get_derivative_variables()
        assert "der_var" in setup2.get_derivative_variables()
        setup2.delete()
        setup3 = self.aedtapp.create_setup("MySetup_3", setuptype=0)
        assert setup3.add_derivatives("der_var")
        assert "der_var" in setup3.get_derivative_variables()
        assert setup3.add_derivatives("der_var2")
        assert "der_var2" in setup3.get_derivative_variables()
        assert "der_var" in setup3.get_derivative_variables()
        setup3.delete()

    def test_06b_setup_exists(self):
        assert self.aedtapp.analysis_setup is not None
        assert self.aedtapp.nominal_sweep is not None

    def test_06c_create_linear_step_sweep(self):
        step_size = 153.8
        freq_start = 1.1e3
        freq_stop = 1200.1
        units = "MHz"
        sweep = self.aedtapp.create_linear_step_sweep(
            setupname="MySetup",
            sweepname=None,
            unit=units,
            freqstart=freq_start,
            freqstop=freq_stop,
            step_size=step_size,
        )
        assert sweep.props["RangeStep"] == str(step_size) + units
        assert sweep.props["RangeStart"] == str(freq_start) + units
        assert sweep.props["RangeEnd"] == str(freq_stop) + units
        assert sweep.props["Type"] == "Discrete"

        step_size = 53.8
        freq_start = 1.2e3
        freq_stop = 1305.1
        units = "MHz"
        sweep = self.aedtapp.create_linear_step_sweep(
            setupname="MySetup",
            sweepname="StepFast",
            unit=units,
            freqstart=freq_start,
            freqstop=freq_stop,
            step_size=step_size,
            sweep_type="Fast",
        )
        assert sweep.props["RangeStep"] == str(step_size) + units
        assert sweep.props["RangeStart"] == str(freq_start) + units
        assert sweep.props["RangeEnd"] == str(freq_stop) + units
        assert sweep.props["Type"] == "Fast"

        # Create a linear step sweep with the incorrect sweep type.
        try:
            sweep = self.aedtapp.create_linear_step_sweep(
                setupname="MySetup",
                sweepname="StepFast",
                unit=units,
                freqstart=freq_start,
                freqstop=freq_stop,
                step_size=step_size,
                sweep_type="Incorrect",
            )
        except AttributeError as e:
            exception_raised = True
            assert (
                e.args[0] == "Invalid value for `sweep_type`. The value must be 'Discrete', 'Interpolating', or 'Fast'."
            )
        assert exception_raised

    def test_06d_create_single_point_sweep(self):
        assert self.aedtapp.create_single_point_sweep(
            setupname="MySetup",
            unit="MHz",
            freq=1.2e3,
        )
        assert self.aedtapp.create_single_point_sweep(
            setupname="MySetup",
            unit="GHz",
            freq=1.2,
            save_single_field=False,
        )
        assert self.aedtapp.create_single_point_sweep(
            setupname="MySetup",
            unit="GHz",
            freq=[1.1, 1.2, 1.3],
        )
        assert self.aedtapp.create_single_point_sweep(
            setupname="MySetup", unit="GHz", freq=[1.1e1, 1.2e1, 1.3e1], save_single_field=[True, False, True]
        )
        settings.enable_error_handler = True
        assert not self.aedtapp.create_single_point_sweep(
            setupname="MySetup", unit="GHz", freq=[1, 2e2, 3.4], save_single_field=[True, False]
        )
        settings.enable_error_handler = False

    def test_06e_delete_setup(self):
        setup_name = "SetupToDelete"
        setuptd = self.aedtapp.create_setup(setupname=setup_name)
        assert setuptd.name in self.aedtapp.existing_analysis_setups
        assert self.aedtapp.delete_setup(setup_name)
        assert setuptd.name not in self.aedtapp.existing_analysis_setups

    def test_06f_sweep_add_subrange(self):
        self.aedtapp.modeler.create_box([0, 0, 20], [10, 10, 5], "box_sweep", "Copper")
        self.aedtapp.modeler.create_box([0, 0, 30], [10, 10, 5], "box_sweep2", "Copper")
        self.aedtapp.create_wave_port_between_objects(
            "box_sweep", "box_sweep2", self.aedtapp.AxisDir.XNeg, 75, 1, "WaveForSweep", False
        )
        setup = self.aedtapp.create_setup(setupname="MySetupForSweep")
        sweep = setup.add_sweep()
        assert sweep.add_subrange("LinearCount", 1, 3, 10, "GHz")
        assert sweep.add_subrange("LinearCount", 2, 4, 10, "GHz")
        assert sweep.add_subrange("LinearStep", 1.1, 2.1, 0.4, "GHz")
        assert sweep.add_subrange("LinearCount", 1, 1.5, 5, "MHz")
        assert sweep.add_subrange("LogScale", 1, 3, 10, "GHz")

    def test_06g_sweep_clear_subrange(self):
        self.aedtapp.modeler.create_box([0, 0, 50], [10, 10, 5], "box_sweep3", "Copper")
        self.aedtapp.modeler.create_box([0, 0, 60], [10, 10, 5], "box_sweep4", "Copper")
        self.aedtapp.create_wave_port_between_objects(
            "box_sweep3", "box_sweep4", self.aedtapp.AxisDir.XNeg, 50, 1, "WaveForSweepWithClear", False
        )
        setup = self.aedtapp.create_setup(setupname="MySetupClearSweep")
        sweep = setup.add_sweep()
        assert sweep.add_subrange("LinearCount", 1.1, 3.6, 10, "GHz", clear=True)
        assert sweep.props["RangeType"] == "LinearCount"
        assert sweep.props["RangeStart"] == "1.1GHz"
        assert sweep.props["RangeEnd"] == "3.6GHz"
        assert sweep.props["RangeCount"] == 10
        assert sweep.add_subrange("LinearCount", 2, 5, 10, "GHz")
        setup.update()
        sweep.update()
        assert sweep.add_subrange("LinearCount", 3, 8, 10, "GHz", clear=True)
        assert sweep.props["RangeType"] == "LinearCount"
        assert sweep.props["RangeStart"] == "3GHz"
        assert sweep.props["RangeEnd"] == "8GHz"
        assert sweep.props["RangeCount"] == 10
        assert sweep.add_subrange("LinearStep", 1.1, 2.1, 0.4, "GHz", clear=True)
        assert sweep.props["RangeType"] == "LinearStep"
        assert sweep.props["RangeStart"] == "1.1GHz"
        assert sweep.props["RangeEnd"] == "2.1GHz"
        assert sweep.props["RangeStep"] == "0.4GHz"
        assert sweep.add_subrange("LogScale", 1, 3, 10, clear=True)
        assert sweep.props["RangeType"] == "LogScale"
        assert sweep.props["RangeStart"] == "1GHz"
        assert sweep.props["RangeEnd"] == "3GHz"
        assert sweep.props["RangeSamples"] == 10
        sweep.props["Type"] = "Discrete"
        sweep.update()
        assert sweep.add_subrange("SinglePoints", 23, clear=True)
        assert sweep.props["RangeType"] == "SinglePoints"
        assert sweep.props["RangeStart"] == "23GHz"
        assert sweep.props["RangeEnd"] == "23GHz"
        assert sweep.props["SaveSingleField"] == False

    def test_06z_validate_setup(self):
        list, ok = self.aedtapp.validate_full_design(ports=8)
        assert ok

    def test_07_set_power(self):
        assert self.aedtapp.edit_source("sheet1_Port" + ":1", "10W")
        assert self.aedtapp.edit_sources(
            {"sheet1_Port" + ":1": "10W", "sheet2_Port:1": ("20W", "20deg")},
            include_port_post_processing=True,
            max_available_power="40W",
        )
        assert self.aedtapp.edit_sources(
            {"sheet1_Port" + ":1": "10W", "sheet2_Port:1": ("20W", "0deg", True)},
            include_port_post_processing=True,
            use_incident_voltage=True,
        )

    def test_08_create_circuit_port_from_edges(self):
        plane = self.aedtapp.PLANE.XY
        rect_1 = self.aedtapp.modeler.create_rectangle(plane, [10, 10, 10], [10, 10], name="rect1_for_port")
        edges1 = self.aedtapp.modeler.get_object_edges(rect_1.id)
        e1 = edges1[0]
        rect_2 = self.aedtapp.modeler.create_rectangle(plane, [30, 10, 10], [10, 10], name="rect2_for_port")
        edges2 = self.aedtapp.modeler.get_object_edges(rect_2.id)
        e2 = edges2[0]

        self.aedtapp.solution_type = "Modal"
        assert self.aedtapp.composite is False
        self.aedtapp.composite = True
        assert self.aedtapp.composite is True
        self.aedtapp.composite = False
        self.aedtapp.hybrid = False
        assert self.aedtapp.hybrid is False
        self.aedtapp.hybrid = True
        assert self.aedtapp.hybrid is True

        assert (
            self.aedtapp.create_circuit_port_from_edges(
                e1, e2, port_name="port10", port_impedance=50.1, renormalize=False, renorm_impedance="50"
            ).name
            == "port10"
        )
        assert (
            self.aedtapp.create_circuit_port_from_edges(
                e1, e2, port_name="port11", port_impedance="50+1i*55", renormalize=True, renorm_impedance=15.4
            ).name
            == "port11"
        )
        assert self.aedtapp.set_source_context(["port10", "port11"])

        assert self.aedtapp.set_source_context([])

        assert self.aedtapp.set_source_context(["port10", "port11"], 0)

        assert self.aedtapp.set_source_context(["port10", "port11", "sheet1_Port"])

        assert self.aedtapp.set_source_context(["port10", "port11", "sheet1_Port"], 0)

        self.aedtapp.solution_type = "Terminal"
        assert (
            self.aedtapp.create_circuit_port_from_edges(
                e1, e2, port_name="port20", port_impedance=50.1, renormalize=False, renorm_impedance="50+1i*55"
            ).name
            == "port20"
        )
        bound = self.aedtapp.create_circuit_port_from_edges(
            e1, e2, port_name="port32", port_impedance="50.1", renormalize=True
        )
        assert bound
        bound.name = "port21"
        assert bound.update()
        self.aedtapp.solution_type = "Modal"

    def test_09_create_waveport_on_objects(self):
        box1 = self.aedtapp.modeler.create_box([0, 0, 0], [10, 10, 5], "BoxWG1", "Copper")
        box2 = self.aedtapp.modeler.create_box([0, 0, 10], [10, 10, 5], "BoxWG2", "copper")
        box2.material_name = "Copper"
        port = self.aedtapp.create_wave_port_between_objects(
            "BoxWG1", "BoxWG2", self.aedtapp.AxisDir.XNeg, 50, 1, "Wave1", False
        )
        assert port.name == "Wave1"
        port2 = self.aedtapp.create_wave_port_between_objects(
            "BoxWG1", "BoxWG2", self.aedtapp.AxisDir.XPos, 25, 2, "Wave1", True, 5
        )
        assert port2.name != "Wave1" and "Wave1" in port2.name
        self.aedtapp.solution_type = "Terminal"
        assert self.aedtapp.create_wave_port_between_objects(
            "BoxWG1", "BoxWG2", self.aedtapp.AxisDir.XPos, 25, 2, "Wave3", True
        )
        assert self.aedtapp.create_wave_port_between_objects(
            "BoxWG1", "BoxWG2", self.aedtapp.AxisDir.XPos, 25, 2, "Wave4", True, 5
        )
        self.aedtapp.solution_type = "Modal"

    def test_09a_create_waveport_on_true_surface_objects(self):
        cs = self.aedtapp.PLANE.XY
        o1 = self.aedtapp.modeler.create_cylinder(
            cs, [0, 0, 0], radius=5, height=100, numSides=0, name="inner", matname="Copper"
        )
        o3 = self.aedtapp.modeler.create_cylinder(
            cs, [0, 0, 0], radius=10, height=100, numSides=0, name="outer", matname="Copper"
        )

        port1 = self.aedtapp.create_wave_port_between_objects(
            o1.name, o3.name, axisdir=0, add_pec_cap=True, portname="P1"
        )
        assert port1.name.startswith("P1")

    def test_10_create_lumped_on_objects(self):
        box1 = self.aedtapp.modeler.create_box([0, 0, 50], [10, 10, 5], "BoxLumped1")
        box1.material_name = "Copper"
        box2 = self.aedtapp.modeler.create_box([0, 0, 60], [10, 10, 5], "BoxLumped2")
        box2.material_name = "Copper"
        port = self.aedtapp.create_lumped_port_between_objects(
            "BoxLumped1", "BoxLumped2", self.aedtapp.AxisDir.XNeg, 50, "Lump1xx", True, False
        )
        assert not self.aedtapp.create_lumped_port_between_objects(
            "BoxLumped1111", "BoxLumped2", self.aedtapp.AxisDir.XNeg, 50, "Lump1", True, False
        )
        assert self.aedtapp.create_lumped_port_between_objects(
            "BoxLumped1", "BoxLumped2", self.aedtapp.AxisDir.XPos, 50
        )
        assert port.name == "Lump1xx"
        port.name = "Lump1"
        assert port.update()
        port = self.aedtapp.create_lumped_port_between_objects(
            "BoxLumped1", "BoxLumped2", self.aedtapp.AxisDir.XNeg, 50, "Lump2", False, True
        )

    def test_11_create_circuit_on_objects(self):
        box1 = self.aedtapp.modeler.create_box([0, 0, 80], [10, 10, 5], "BoxCircuit1", "Copper")
        box2 = self.aedtapp.modeler.create_box([0, 0, 100], [10, 10, 5], "BoxCircuit2", "copper")
        box2.material_name = "Copper"
        port = self.aedtapp.create_circuit_port_between_objects(
            "BoxCircuit1", "BoxCircuit2", self.aedtapp.AxisDir.XNeg, 50, "Circ1", True, 50, False
        )
        assert port.name == "Circ1"
        assert not self.aedtapp.create_circuit_port_between_objects(
            "BoxCircuit44", "BoxCircuit2", self.aedtapp.AxisDir.XNeg, 50, "Circ1", True, 50, False
        )

    def test_12_create_perfects_on_objects(self):
        box1 = self.aedtapp.modeler.create_box([0, 0, 0], [10, 10, 5], "perfect1", "Copper")
        box2 = self.aedtapp.modeler.create_box([0, 0, 10], [10, 10, 5], "perfect2", "copper")
        pe = self.aedtapp.create_perfecth_from_objects(
            "perfect1",
            "perfect2",
            self.aedtapp.AxisDir.ZPos,
        )
        ph = self.aedtapp.create_perfecte_from_objects("perfect1", "perfect2", self.aedtapp.AxisDir.ZNeg)
        assert pe.name in self.aedtapp.modeler.get_boundaries_name()
        assert pe.update()
        assert ph.name in self.aedtapp.modeler.get_boundaries_name()
        assert ph.update()

    def test_13_create_impedance_on_objects(self):
        box1 = self.aedtapp.modeler.create_box([0, 0, 0], [10, 10, 5], "imp1", "Copper")
        box2 = self.aedtapp.modeler.create_box([0, 0, 10], [10, 10, 5], "imp2", "copper")
        imp = self.aedtapp.create_impedance_between_objects("imp1", "imp2", self.aedtapp.AxisDir.XPos, "TL2", 50, 25)
        assert imp.name in self.aedtapp.modeler.get_boundaries_name()
        assert imp.update()

    def test_14_create_lumpedrlc_on_objects(self):
        box1 = self.aedtapp.modeler.create_box([0, 0, 0], [10, 10, 5], "rlc1", "Copper")
        box2 = self.aedtapp.modeler.create_box([0, 0, 10], [10, 10, 5], "rlc2", "copper")
        imp = self.aedtapp.create_lumped_rlc_between_objects(
            "rlc1", "rlc2", self.aedtapp.AxisDir.XPos, Rvalue=50, Lvalue=1e-9
        )
        assert imp.name in self.aedtapp.modeler.get_boundaries_name()
        assert imp.update()

        box3 = self.aedtapp.modeler.create_box([0, 0, 20], [10, 10, 5], "rlc3", "copper")
        lumped_rlc2 = self.aedtapp.create_lumped_rlc_between_objects(
            "rlc2", "rlc3", self.aedtapp.AxisDir.XPos, Rvalue=50, Lvalue=1e-9, Cvalue=1e-9
        )
        assert lumped_rlc2.name in self.aedtapp.modeler.get_boundaries_name()
        assert lumped_rlc2.update()

    def test_15_create_perfects_on_sheets(self):
        rect = self.aedtapp.modeler.create_rectangle(
            self.aedtapp.PLANE.XY, [0, 0, 0], [10, 2], name="RectBound", matname="Copper"
        )
        pe = self.aedtapp.assign_perfecte_to_sheets(rect.name)
        assert pe.name in self.aedtapp.modeler.get_boundaries_name()
        ph = self.aedtapp.assign_perfecth_to_sheets(rect.name)
        assert ph.name in self.aedtapp.modeler.get_boundaries_name()

    def test_16_create_impedance_on_sheets(self):
        rect = self.aedtapp.modeler.create_rectangle(
            self.aedtapp.PLANE.XY, [0, 0, 0], [10, 2], name="ImpBound", matname="Copper"
        )
        imp = self.aedtapp.assign_impedance_to_sheet("imp1", "TL2", 50, 25)
        assert imp.name in self.aedtapp.modeler.get_boundaries_name()
        assert imp.update()

    def test_17_create_lumpedrlc_on_sheets(self):
        rect = self.aedtapp.modeler.create_rectangle(
            self.aedtapp.PLANE.XY, [0, 0, 0], [10, 2], name="rlcBound", matname="Copper"
        )
        imp = self.aedtapp.assign_lumped_rlc_to_sheet(rect.name, self.aedtapp.AxisDir.XPos, Rvalue=50, Lvalue=1e-9)
        names = self.aedtapp.modeler.get_boundaries_name()
        assert imp.name in self.aedtapp.modeler.get_boundaries_name()

        rect2 = self.aedtapp.modeler.create_rectangle(
            self.aedtapp.PLANE.XY, [0, 0, 10], [10, 2], name="rlcBound2", matname="Copper"
        )
        imp = self.aedtapp.assign_lumped_rlc_to_sheet(
            rect.name, self.aedtapp.AxisDir.XPos, rlctype="Serial", Rvalue=50, Lvalue=1e-9
        )
        names = self.aedtapp.modeler.get_boundaries_name()
        assert imp.name in self.aedtapp.modeler.get_boundaries_name()
        assert self.aedtapp.assign_lumped_rlc_to_sheet(
            rect.name, [rect.bottom_edge_x.midpoint, rect.bottom_edge_y.midpoint], Lvalue=1e-9
        )
        assert not self.aedtapp.assign_lumped_rlc_to_sheet(rect.name, [rect.bottom_edge_x.midpoint], Lvalue=1e-9)

    def test_17B_update_assignment(self):
        bound = self.aedtapp.assign_perfecth_to_sheets(self.aedtapp.modeler["My_Box"].faces[0].id)
        assert bound
        bound.props["Faces"].append(self.aedtapp.modeler["My_Box"].faces[1])
        assert bound.update_assignment()

    def test_18_create_sources_on_objects(self):
        box1 = self.aedtapp.modeler.create_box([30, 0, 0], [40, 10, 5], "BoxVolt1", "Copper")
        box2 = self.aedtapp.modeler.create_box([30, 0, 10], [40, 10, 5], "BoxVolt2", "Copper")
        port = self.aedtapp.create_voltage_source_from_objects(
            box1.name, "BoxVolt2", self.aedtapp.AxisDir.XNeg, "Volt1"
        )
        assert port.name in self.aedtapp.excitations
        port = self.aedtapp.create_current_source_from_objects("BoxVolt1", "BoxVolt2", self.aedtapp.AxisDir.XPos)
        assert port.name in self.aedtapp.excitations

    def test_19_create_lumped_on_sheet(self):
        rect = self.aedtapp.modeler.create_rectangle(
            self.aedtapp.PLANE.XY, [0, 0, 0], [10, 2], name="lump_port", matname="Copper"
        )
        port = self.aedtapp.create_lumped_port_to_sheet(
            rect.name, self.aedtapp.AxisDir.XNeg, 50, "Lump_sheet", True, False
        )
        assert port.name + ":1" in self.aedtapp.excitations
        port2 = self.aedtapp.create_lumped_port_to_sheet(
            rect.name, self.aedtapp.AxisDir.XNeg, 50, "Lump_sheet2", True, True
        )
        assert port2.name + ":1" in self.aedtapp.excitations
        port3 = self.aedtapp.create_lumped_port_to_sheet(
            rect.name, [rect.bottom_edge_x.midpoint, rect.bottom_edge_y.midpoint], 50, "Lump_sheet3", True, True
        )
        assert port3.name + ":1" in self.aedtapp.excitations
        port4 = self.aedtapp.create_lumped_port_to_sheet(
            rect.name, [rect.bottom_edge_x.midpoint], 50, "Lump_sheet4", True, True
        )
        assert not port4

    def test_20_create_voltage_on_sheet(self):
        rect = self.aedtapp.modeler.create_rectangle(
            self.aedtapp.PLANE.XY, [0, 0, 0], [10, 2], name="lump_volt", matname="Copper"
        )
        port = self.aedtapp.assign_voltage_source_to_sheet(rect.name, self.aedtapp.AxisDir.XNeg, "LumpVolt1")
        assert port.name in self.aedtapp.excitations
        assert self.aedtapp.get_property_value("BoundarySetup:LumpVolt1", "VoltageMag", "Excitation") == "1V"
        port = self.aedtapp.assign_voltage_source_to_sheet(
            rect.name, [rect.bottom_edge_x.midpoint, rect.bottom_edge_y.midpoint], "LumpVolt2"
        )
        assert port.name in self.aedtapp.excitations
        port = self.aedtapp.assign_voltage_source_to_sheet(rect.name, [rect.bottom_edge_x.midpoint], "LumpVolt2")
        assert not port

    def test_21_create_open_region(self):
        assert self.aedtapp.create_open_region("1GHz")
        assert self.aedtapp.create_open_region("1GHz", "FEBI")
        assert self.aedtapp.create_open_region("1GHz", "PML", True, "-z")

    def test_22_create_length_mesh(self):
        mesh = self.aedtapp.mesh.assign_length_mesh(["BoxCircuit1"])
        assert mesh
        mesh.props["NumMaxElem"] = "10000"
        assert mesh.update()

    def test_23_create_skin_depth(self):
        mesh = self.aedtapp.mesh.assign_skin_depth(["BoxCircuit2"], "1mm")
        assert mesh
        mesh.props["SkinDepth"] = "3mm"
        assert mesh.update()

    def test_24_create_curvilinear(self):
        mesh = self.aedtapp.mesh.assign_curvilinear_elements(["BoxCircuit2"])
        assert mesh
        mesh.props["Apply"] = False
        assert mesh.update()
        assert mesh.delete()
        pass

    def test_25a_create_parametrics(self):
        self.aedtapp["w1"] = "10mm"
        self.aedtapp["w2"] = "2mm"
        setup1 = self.aedtapp.parametrics.add("w1", 0.1, 20, 0.2, "LinearStep")
        assert setup1
        assert setup1.add_variation("w2", "0.1mm", 10, 11)
        assert setup1.add_variation("w2", start_point="0.2mm", variation_type="SingleValue")
        assert setup1.add_variation("w1", start_point="0.3mm", end_point=5, step=0.2, variation_type="LinearStep")
        assert setup1.add_calculation(
            calculation="dB(S(1,1))", ranges={"Freq": "5GHz"}, solution="MySetupForSweep : LastAdaptive"
        )
        assert setup1.name in self.aedtapp.get_oo_name(
            self.aedtapp.odesign, r"Optimetrics".format(self.aedtapp.design_name)
        )
        oo = self.aedtapp.get_oo_object(self.aedtapp.odesign, r"Optimetrics\{}".format(setup1.name))
        oo_calculation = oo.GetCalculationInfo()[0]
        assert "Modal Solution Data" in oo_calculation
        assert setup1.export_to_csv(os.path.join(self.local_scratch.path, "test.csv"))
        assert os.path.exists(os.path.join(self.local_scratch.path, "test.csv"))
        assert self.aedtapp.parametrics.add_from_file(
            os.path.join(self.local_scratch.path, "test.csv"), "ParametricsfromFile"
        )
        oo = self.aedtapp.get_oo_object(self.aedtapp.odesign, r"Optimetrics\ParametricsfromFile")
        assert oo
        assert self.aedtapp.parametrics.delete("ParametricsfromFile")

    def test_25b_create_parametrics_sync(self):
        self.aedtapp["a1"] = "10mm"
        self.aedtapp["a2"] = "2mm"
        setup1 = self.aedtapp.parametrics.add(
            "a1", start_point=0.1, end_point=20, step=10, variation_type="LinearCount"
        )
        assert setup1
        assert setup1.add_variation("a2", start_point="0.3mm", end_point=5, step=10, variation_type="LinearCount")
        assert setup1.sync_variables(["a1", "a2"], sync_n=1)
        assert setup1.sync_variables(["a1", "a2"], sync_n=0)
        setup1.add_variation("a1", start_point="13mm", variation_type="SingleValue")

    def test_26_create_optimization(self):
        calculation = "db(S(Cir1,Cir1))"
        setup2 = self.aedtapp.optimizations.add(calculation, ranges={"Freq": "2.5GHz"})
        assert setup2
        assert setup2.name in self.aedtapp.get_oo_name(
            self.aedtapp.odesign, r"Optimetrics".format(self.aedtapp.design_name)
        )
        oo = self.aedtapp.get_oo_object(self.aedtapp.odesign, r"Optimetrics\{}".format(setup2.name))
        oo_calculation = oo.GetCalculationInfo()[0]
        assert calculation in oo_calculation
        assert self.aedtapp.nominal_sweep in oo_calculation
        for el in oo_calculation:
            if "NAME:Ranges" in el:
                break
        assert len(el) == 3
        assert setup2.add_goal(calculation=calculation, ranges={"Freq": "2.6GHz"})
        oo_calculation = oo.GetCalculationInfo()[0]
        for el in reversed(oo_calculation):
            if "NAME:Ranges" in el:
                break
        assert "2.6GHz" in el[2]
        assert setup2.add_goal(calculation=calculation, ranges={"Freq": ("2.6GHz", "5GHZ")})
        oo = self.aedtapp.get_oo_object(self.aedtapp.odesign, r"Optimetrics\{}".format(setup2.name))
        oo_calculation = oo.GetCalculationInfo()[0]
        for el in reversed(oo_calculation):
            if "NAME:Ranges" in el:
                break
        assert "rd" in el[2]
        assert self.aedtapp.optimizations.delete(setup2.name)

    def test_27_create_doe(self):
        setup2 = self.aedtapp.optimizations.add("db(S(1,1))", ranges={"Freq": "2.5GHz"}, optim_type="DXDOE")
        assert setup2.add_variation("w1", 0.1, 10, 51)
        assert setup2
        assert setup2.add_goal(calculation="dB(S(1,1))", ranges={"Freq": "2.6GHz"})
        assert setup2.add_calculation(calculation="dB(S(1,1))", ranges={"Freq": "2.5GHz"})
        assert setup2.delete()

    def test_28A_create_dx(self):
        setup2 = self.aedtapp.optimizations.add(None, {"w1": "1mm", "w2": "2mm"}, optim_type="optiSLang")
        assert setup2.add_variation("w1", 0.1, 10, 51)
        assert not setup2.add_variation("w3", 0.1, 10, 51)
        assert setup2
        assert setup2.add_goal(calculation="dB(S(1,1))", ranges={"Freq": "2.6GHz"})

    def test_28B_create_dx(self):
        setup2 = self.aedtapp.optimizations.add(None, {"w1": "1mm", "w2": "2mm"}, optim_type="DesignExplorer")
        assert setup2.add_variation("w1", 0.1, 10, 51)
        assert setup2
        assert setup2.add_goal(calculation="dB(S(1,1))", ranges={"Freq": "2.6GHz"})

    def test_29_create_sensitivity(self):
        setup2 = self.aedtapp.optimizations.add("db(S(1,1))", ranges={"Freq": "2.5GHz"}, optim_type="Sensitivity")
        assert setup2.add_variation("w1", 0.1, 10, 51)
        assert setup2
        assert setup2.add_calculation(calculation="dB(S(1,1))", ranges={"Freq": "2.6GHz"})

    def test_29_create_statistical(self):
        setup2 = self.aedtapp.optimizations.add("db(S(1,1))", ranges={"Freq": "2.5GHz"}, optim_type="Statistical")
        assert setup2.add_variation("w1", 0.1, 10, 0.1, "LinearStep")
        assert setup2
        assert setup2.add_calculation(calculation="dB(S(1,1))", ranges={"Freq": "2.6GHz"})

    def test_30_assign_initial_mesh(self):
        assert self.aedtapp.mesh.assign_initial_mesh_from_slider(6)

    def test_30a_add_mesh_link(self):
        self.aedtapp.duplicate_design(self.aedtapp.design_name)
        self.aedtapp.set_active_design(self.aedtapp.design_list[0])
        assert self.aedtapp.setups[0].add_mesh_link(design_name=self.aedtapp.design_list[1])
        meshlink_props = self.aedtapp.setups[0].props["MeshLink"]
        assert meshlink_props["Project"] == "This Project*"
        assert meshlink_props["PathRelativeTo"] == "TargetProject"
        assert meshlink_props["Design"] == self.aedtapp.design_list[1]
        assert meshlink_props["Soln"] == "MySetup : LastAdaptive"
        assert sorted(list(meshlink_props["Params"].keys())) == sorted(self.aedtapp.available_variations.variables)
        assert sorted(list(meshlink_props["Params"].values())) == sorted(self.aedtapp.available_variations.variables)
        assert not self.aedtapp.setups[0].add_mesh_link(design_name="")
        assert self.aedtapp.setups[0].add_mesh_link(
            design_name=self.aedtapp.design_list[1], solution_name="MySetup : LastAdaptive"
        )
        assert not self.aedtapp.setups[0].add_mesh_link(
            design_name=self.aedtapp.design_list[1], solution_name="Setup_Test : LastAdaptive"
        )
        assert self.aedtapp.setups[0].add_mesh_link(
            design_name=self.aedtapp.design_list[1],
            parameters_dict=self.aedtapp.available_variations.nominal_w_values_dict,
        )
        example_project = os.path.join(local_path, "example_models", test_subfolder, diff_proj_name + ".aedt")
        example_project_copy = os.path.join(self.local_scratch.path, diff_proj_name + "_copy.aedt")
        shutil.copyfile(example_project, example_project_copy)
        assert self.aedtapp.setups[0].add_mesh_link(
            design_name=self.aedtapp.design_list[1], project_name=example_project_copy
        )

    def test_31_create_microstrip_port(self):
        self.aedtapp.insert_design("Microstrip")
        self.aedtapp.solution_type = "Modal"
        ms = self.aedtapp.modeler.create_box([4, 5, 0], [1, 100, 0.2], name="MS1", matname="copper")
        sub = self.aedtapp.modeler.create_box([0, 5, -2], [20, 100, 2], name="SUB1", matname="FR4_epoxy")
        gnd = self.aedtapp.modeler.create_box([0, 5, -2.2], [20, 100, 0.2], name="GND1", matname="FR4_epoxy")
        port = self.aedtapp.create_wave_port_microstrip_between_objects(gnd.name, ms.name, portname="MS1", axisdir=1)
        assert port.name == "MS1"
        assert port.update()
        self.aedtapp.solution_type = "Terminal"
        assert self.aedtapp.create_wave_port_microstrip_between_objects(gnd.name, ms.name, portname="MS2", axisdir=1)
        assert self.aedtapp.create_wave_port_microstrip_between_objects(
            gnd.name, ms.name, portname="MS3", axisdir=1, deembed_dist=1, impedance=77
        )

    def test_32_get_property_value(self):
        rect = self.aedtapp.modeler.create_rectangle(
            self.aedtapp.PLANE.XY, [0, 0, 0], [10, 2], name="RectProp", matname="Copper"
        )
        pe = self.aedtapp.assign_perfecte_to_sheets(rect.name, "PerfectE_1")
        setup = self.aedtapp.create_setup("MySetup2")
        setup.props["Frequency"] = "1GHz"
        assert self.aedtapp.get_property_value("BoundarySetup:PerfectE_1", "Inf Ground Plane", "Boundary") == "false"
        assert self.aedtapp.get_property_value("AnalysisSetup:MySetup2", "Solution Freq", "Setup") == "1GHz"

    def test_33_copy_solid_bodies(self):
        project_name = "HfssCopiedProject"
        design_name = "HfssCopiedBodies"
        new_design = Hfss(projectname=project_name, designname=design_name, specified_version=desktop_version)
        num_orig_bodies = len(self.aedtapp.modeler.solid_names)
        assert new_design.copy_solid_bodies_from(self.aedtapp, no_vacuum=False, no_pec=False)
        assert len(new_design.modeler.solid_bodies) == num_orig_bodies
        new_design.delete_design(design_name)
        new_design.close_project(project_name)

    def test_34_object_material_properties(self):
        self.aedtapp.insert_design("ObjMat")
        self.aedtapp.solution_type = "Modal"
        ms = self.aedtapp.modeler.create_box([4, 5, 0], [1, 100, 0.2], name="MS1", matname="copper")
        props = self.aedtapp.get_object_material_properties("MS1", "conductivity")
        assert props

    def test_35_set_export_touchstone(self):
        assert self.aedtapp.set_export_touchstone(True)
        assert self.aedtapp.set_export_touchstone(False)

    def test_36_assign_radiation_to_objects(self):
        self.aedtapp.modeler.create_box([-100, -100, -100], [200, 200, 200], name="Rad_box")
        rad = self.aedtapp.assign_radiation_boundary_to_objects("Rad_box")
        rad.name = "Radiation1"
        assert rad.update()

    def test_37_assign_radiation_to_objects(self):
        self.aedtapp.modeler.create_box([-100, -100, -100], [200, 200, 200], name="Rad_box2")
        ids = [i.id for i in self.aedtapp.modeler["Rad_box2"].faces]
        assert self.aedtapp.assign_radiation_boundary_to_faces(ids)

    def test_38_get_all_sources(self):
        sources = self.aedtapp.get_all_sources()
        assert isinstance(sources, list)

    def test_40_assign_current_source_to_sheet(self):
        sheet = self.aedtapp.modeler.create_rectangle(
            self.aedtapp.PLANE.XY, [0, 0, 0], [5, 1], name="RectangleForSource", matname="Copper"
        )
        assert self.aedtapp.assign_current_source_to_sheet(sheet.name)
        assert self.aedtapp.assign_current_source_to_sheet(
            sheet.name, [sheet.bottom_edge_x.midpoint, sheet.bottom_edge_y.midpoint]
        )
        assert not self.aedtapp.assign_current_source_to_sheet(sheet.name, [sheet.bottom_edge_x.midpoint])

    @pytest.mark.skipif(is_ironpython, reason="Float overflow in Ironpython")
    def test_41_export_step(self):
        file_name = "test"
        self.aedtapp.modeler.create_box([0, 0, 0], [10, 10, 10])
        assert self.aedtapp.export_3d_model(file_name, self.aedtapp.working_directory, ".step", [], [])
        assert os.path.exists(os.path.join(self.aedtapp.working_directory, file_name + ".step"))

    def test_42_floquet_port(self):
        self.aedtapp.insert_design("floquet")
        self.aedtapp.solution_type = "Modal"

        box1 = self.aedtapp.modeler.create_box([-100, -100, -100], [200, 200, 200], name="Rad_box2")
        assert self.aedtapp.create_floquet_port(
            box1.faces[0], deembed_dist=1, nummodes=7, reporter_filter=[False, True, False, False, False, False, False]
        )
        assert self.aedtapp.create_floquet_port(
            box1.faces[1], deembed_dist=1, nummodes=7, reporter_filter=[False, True, False, False, False, False, False]
        )
        sheet = self.aedtapp.modeler.create_rectangle(
            self.aedtapp.PLANE.XY, [-100, -100, -100], [200, 200], name="RectangleForSource", matname="Copper"
        )
        bound = self.aedtapp.create_floquet_port(sheet, deembed_dist=1, nummodes=4, reporter_filter=False)
        assert bound
        bound.name = "Floquet1"
        assert bound.update()

    def test_43_autoassign_pairs(self):
        self.aedtapp.insert_design("lattice")
        box1 = self.aedtapp.modeler.create_box([-100, -100, -100], [200, 200, 200], name="Rad_box2")
        assert len(self.aedtapp.auto_assign_lattice_pairs(box1)) == 2
        box1.delete()
        box1 = self.aedtapp.modeler.create_box([-100, -100, -100], [200, 200, 200], name="Rad_box2")
        if config["desktopVersion"] > "2022.2":
            assert self.aedtapp.assign_lattice_pair([box1.faces[2], box1.faces[5]])
            primary = self.aedtapp.assign_primary(box1.faces[4], [100, -100, -100], [100, 100, -100])

        else:
            assert self.aedtapp.assign_lattice_pair([box1.faces[2], box1.faces[4]])
            primary = self.aedtapp.assign_primary(box1.faces[1], [100, -100, -100], [100, 100, -100])
        assert primary
        primary.name = "Prim1"
        assert primary.update()
        sec = self.aedtapp.assign_secondary(
            box1.faces[0], primary.name, [100, -100, 100], [100, 100, 100], reverse_v=True
        )
        sec.name = "Sec1"
        assert sec.update()

    def test_44_create_infinite_sphere(self):
        self.aedtapp.insert_design("InfSphere")
        air = self.aedtapp.modeler.create_box([0, 0, 0], [20, 20, 20], name="rad", matname="vacuum")
        self.aedtapp.assign_radiation_boundary_to_objects(air)
        bound = self.aedtapp.insert_infinite_sphere(
            definition="El Over Az",
            x_start=1,
            x_stop=91,
            x_step=45,
            y_start=2,
            y_stop=92,
            y_step=10,
            use_slant_polarization=True,
            polarization_angle=30,
        )
        assert bound
        assert bound.azimuth_start == "1deg"
        assert bound.azimuth_stop == "91deg"
        assert bound.azimuth_step == "45deg"
        assert bound.elevation_start == "2deg"
        assert bound.elevation_stop == "92deg"
        assert bound.elevation_step == "10deg"
        assert bound.slant_angle == "30deg"
        assert bound.polarization == "Slant"
        bound.azimuth_start = 20
        assert bound.azimuth_start == "20deg"
        assert bound.delete()
        bound = self.aedtapp.insert_infinite_sphere(
            definition="Az Over El",
            x_start=1,
            x_stop=91,
            x_step=45,
            y_start=2,
            y_stop=92,
            y_step=10,
            use_slant_polarization=True,
            polarization_angle=30,
        )
        assert bound.azimuth_start == "2deg"
        self.aedtapp.create_setup()
        sweep6 = self.aedtapp.optimizations.add(
            calculation="RealizedGainTotal",
            solution=self.aedtapp.nominal_adaptive,
            ranges={"Freq": "5GHz", "Theta": "0deg", "Phi": "0deg"},
            context=bound.name,
        )
        assert sweep6

    def test_45_set_autoopen(self):
        assert self.aedtapp.set_auto_open(True, "PML")

    def test_45_terminal_port(self):
        self.aedtapp.insert_design("Design_Terminal")
        self.aedtapp.solution_type = "Terminal"
        box1 = self.aedtapp.modeler.create_box([-100, -100, 0], [200, 200, 5], name="gnd", matname="copper")
        box2 = self.aedtapp.modeler.create_box([-100, -100, 20], [200, 200, 25], name="sig", matname="copper")
        sheet = self.aedtapp.modeler.create_rectangle(self.aedtapp.PLANE.YZ, [-100, -100, 5], [200, 15], "port")
        port = self.aedtapp.create_lumped_port_between_objects(
            box1, box2.name, self.aedtapp.AxisDir.XNeg, 75, "Lump1", True, False
        )
        assert "Lump1_T1" in self.aedtapp.excitations
        port2 = self.aedtapp.create_lumped_port_to_sheet(
            sheet.name, self.aedtapp.AxisDir.XNeg, 33, "Lump_sheet", True, False, reference_object_list=[box1]
        )
        assert port2.name + "_T1" in self.aedtapp.excitations
        port3 = self.aedtapp.create_lumped_port_between_objects(
            box1, box2.name, self.aedtapp.AxisDir.XNeg, 50, "Lump3", False, True
        )
        assert port3.name + "_T1" in self.aedtapp.excitations

    @pytest.mark.skipif(desktop_version > "2022.2", reason="To Be fixed in 23R1.")
    def test_45B_terminal_port(self):
        self.aedtapp.insert_design("Design_Terminal_2")
        self.aedtapp.solution_type = "Terminal"
        box1 = self.aedtapp.modeler.create_box([-100, -100, 0], [200, 200, 5], name="gnd2", matname="copper")
        box2 = self.aedtapp.modeler.create_box([-100, -100, 20], [200, 200, 25], name="sig2", matname="copper")
        box3 = self.aedtapp.modeler.create_box([-40, -40, -20], [80, 80, 10], name="box3", matname="copper")
        box4 = self.aedtapp.modeler.create_box([-40, -40, 10], [80, 80, 10], name="box4", matname="copper")
        boundaries = len(self.aedtapp.boundaries)

        assert self.aedtapp.create_spiral_lumped_port(box1, box2)

        # Rotate box2 so that, box3 and box4 are not collinear anymore.
        # Spiral lumped port can only be created based on 2 collinear objects.
        box3.rotate(cs_axis="X", angle=90)
        try:
            self.aedtapp.create_spiral_lumped_port(box3, box4)
        except AttributeError as e:
            exception_raised = True
            assert e.args[0] == "The two objects must have parallel adjacent faces."
        assert exception_raised

    def test_46_mesh_settings(self):
        assert self.aedtapp.mesh.initial_mesh_settings
        assert self.aedtapp.mesh.initial_mesh_settings.props

    def test_47_convert_near_field(self):
        example_project = os.path.join(local_path, "example_models", "nf_test")
        assert os.path.exists(convert_nearfield_data(example_project, output_folder=self.local_scratch.path))

    def test_48_traces(self):
        assert len(self.aedtapp.excitations) > 0
        assert len(self.aedtapp.get_traces_for_plot()) > 0

    def test_49_port_creation_exception(self):
        box1 = self.aedtapp.modeler.create_box([-400, -40, -20], [80, 80, 10], name="gnd49", matname="copper")
        box2 = self.aedtapp.modeler.create_box([-400, -40, 10], [80, 80, 10], name="sig49", matname="copper")

        self.aedtapp.solution_type = "Modal"
        # Spiral lumped port can only be created in a 'Terminal' solution.
        try:
            self.aedtapp.create_spiral_lumped_port(box1, box2)
        except Exception as e:
            exception_raised = True
            assert e.args[0] == "This method can be used only in Terminal solutions."
        assert exception_raised
        self.aedtapp.solution_type = "Terminal"

        # Try to modify SBR+ TX RX antenna settings in a solution that is different from SBR+
        # should not be possible.
        assert not self.aedtapp.set_sbr_txrx_settings({"TX1": "RX1"})

        # SBR linked antenna can only be created within an SBR+ solution.
        assert not self.aedtapp.create_sbr_linked_antenna(self.aedtapp, fieldtype="farfield")

        # Chirp I doppler setup only works within an SBR+ solution.
        assert self.aedtapp.create_sbr_chirp_i_doppler_setup(sweep_time_duration=20) == (False, False)

        # Chirp IQ doppler setup only works within an SBR+ solution.
        assert self.aedtapp.create_sbr_chirp_iq_doppler_setup(sweep_time_duration=10) == (False, False)

    def test_50_set_differential_pair(self):
        example_project = os.path.join(local_path, "example_models", test_subfolder, diff_proj_name + ".aedt")
        test_project = self.local_scratch.copyfile(example_project)
        self.local_scratch.copyfolder(
            os.path.join(local_path, "example_models", test_subfolder, diff_proj_name + ".aedb"),
            os.path.join(self.local_scratch.path, diff_proj_name + ".aedb"),
        )
        hfss1 = Hfss(projectname=test_project, designname="Hfss_Terminal", specified_version=desktop_version)
        assert hfss1.set_differential_pair(
            positive_terminal="P2_T1",
            negative_terminal="P2_T2",
            common_name=None,
            diff_name=None,
            common_ref_z=34,
            diff_ref_z=123,
            active=True,
            matched=False,
        )
        assert not hfss1.set_differential_pair(positive_terminal="P2_T1", negative_terminal="P2_T3")
        hfss2 = Hfss(designname="Hfss_Transient", specified_version=desktop_version)
        assert hfss2.set_differential_pair(
            positive_terminal="P2_T1",
            negative_terminal="P2_T2",
            common_name=None,
            diff_name=None,
            common_ref_z=34,
            diff_ref_z=123,
            active=True,
            matched=False,
        )
        assert not hfss2.set_differential_pair(positive_terminal="P2_T1", negative_terminal="P2_T3")
        hfss2.close_project()

    @pytest.mark.skipif(
        is_ironpython or config["desktopVersion"] < "2022.2",
        reason="Not working in non-graphical in version lower than 2022.2",
    )
    def test_51a_array(self):
        self.aedtapp.insert_design("Array_simple", "Modal")
        from pyaedt.generic.DataHandlers import json_to_dict

        dict_in = json_to_dict(os.path.join(local_path, "example_models", test_subfolder, "array_simple.json"))
        dict_in["Circ_Patch_5GHz1"] = os.path.join(
            local_path, "example_models", test_subfolder, "Circ_Patch_5GHz.a3dcomp"
        )
        dict_in["cells"][(3, 3)] = {"name": "Circ_Patch_5GHz1"}
        assert self.aedtapp.add_3d_component_array_from_json(dict_in)
        dict_in["cells"][(3, 3)]["rotation"] = 90
        assert self.aedtapp.add_3d_component_array_from_json(dict_in)

    def test_51b_set_material_threshold(self):
        assert self.aedtapp.set_material_threshold()
        threshold = 123123123
        assert self.aedtapp.set_material_threshold(threshold)
        assert self.aedtapp.set_material_threshold(str(threshold))
        assert not self.aedtapp.set_material_threshold("e")

    @pytest.mark.skipif(
        is_ironpython or config["desktopVersion"] < "2022.2",
        reason="Not working in non-graphical in version lower than 2022.2",
    )
    def test_51c_export_results(self):
        self.aedtapp.set_active_design("Array_simple")
        exported_files = self.aedtapp.export_results()
        assert len(exported_files) == 0
        setup = self.aedtapp.create_setup(setupname="test")
        setup.props["Frequency"] = "1GHz"
        exported_files = self.aedtapp.export_results()
        assert len(exported_files) == 0
        self.aedtapp.analyze_setup(name="test")
        exported_files = self.aedtapp.export_results()
        assert len(exported_files) > 0

    def test_52_crate_setup_hybrid_sbr(self):
        self.aedtapp.insert_design()
        udp = self.aedtapp.modeler.Position(0, 0, 0)
        coax_dimension = 200
        self.aedtapp.modeler.create_cylinder(self.aedtapp.AXIS.X, udp, 3, coax_dimension, 0, "inner")
        self.aedtapp.modeler.create_cylinder(self.aedtapp.AXIS.X, udp, 10, coax_dimension, 0, "outer")
        self.aedtapp.hybrid = True
        assert self.aedtapp.assign_hybrid_region(["inner"])
        bound = self.aedtapp.assign_hybrid_region("outer", hybrid_region="IE", boundary_name="new_hybrid")
        assert bound.props["Type"] == "IE"
        bound.props["Type"] = "PO"
        assert bound.props["Type"] == "PO"
        self.aedtapp.close_project(name=self.aedtapp.project_name, save_project=False)

    @pytest.mark.skipif(is_ironpython, reason="Method usese Pandas")
    def test_53_import_source_excitation(self):
        self.aedtapp.insert_design()
        self.aedtapp.solution_type = "Modal"
        freq_domain = os.path.join(local_path, "example_models", test_subfolder, "S Parameter Table 1.csv")
        time_domain = os.path.join(local_path, "example_models", test_subfolder, "Sinusoidal.csv")

        box1 = self.aedtapp.modeler.create_box([0, 0, 0], [10, 20, 20])
        self.aedtapp.create_wave_port_from_sheet(box1.bottom_face_x)
        self.aedtapp.create_setup()
        assert self.aedtapp.edit_source_from_file(
            self.aedtapp.excitations[0], freq_domain, is_time_domain=False, x_scale=1e9
        )
        assert self.aedtapp.edit_source_from_file(
            self.aedtapp.excitations[0],
            time_domain,
            is_time_domain=True,
            data_format="Voltage",
            x_scale=1e-6,
            y_scale=1e-3,
        )

    def test_54_assign_symmetry(self):
        self.aedtapp.insert_design()
        self.aedtapp.modeler.create_box([0, -100, 0], [200, 200, 200], name="SymmetryForFaces")
        ids = [i.id for i in self.aedtapp.modeler["SymmetryForFaces"].faces]
        if is_ironpython:
            assert not self.aedtapp.assign_symmetry(ids)
            self.aedtapp.solution_type = "Modal"
        assert self.aedtapp.assign_symmetry(ids)
        assert self.aedtapp.assign_symmetry([ids[0], ids[1], ids[2]])
        assert not self.aedtapp.assign_symmetry(self.aedtapp.modeler.object_list[0].faces[0])
        assert self.aedtapp.assign_symmetry([self.aedtapp.modeler.object_list[0].faces[0]])
        assert self.aedtapp.assign_symmetry(
            [
                self.aedtapp.modeler.object_list[0].faces[0],
                self.aedtapp.modeler.object_list[0].faces[1],
                self.aedtapp.modeler.object_list[0].faces[2],
            ]
        )
        assert not self.aedtapp.assign_symmetry(ids[0])
        assert not self.aedtapp.assign_symmetry("test")

    def test_55_create_near_field_sphere(self):
        air = self.aedtapp.modeler.create_box([0, 0, 0], [20, 20, 20], name="rad", matname="vacuum")
        self.aedtapp.assign_radiation_boundary_to_objects(air)
        bound = self.aedtapp.insert_near_field_sphere(
            radius=20,
            radius_units="cm",
            x_start=-180,
            x_stop=180,
            x_step=10,
            y_start=0,
            y_stop=180,
            y_step=10,
            angle_units="deg",
            custom_radiation_faces=None,
            custom_coordinate_system=None,
            name=None,
        )
        bound.name = "Test_Sphere"
        assert self.aedtapp.field_setup_names[0] == bound.name

    def test_56_create_near_field_box(self):
        bound = self.aedtapp.insert_near_field_box(
            u_length=20,
            u_samples=21,
            v_length=20,
            v_samples=21,
            w_length=20,
            w_samples=21,
            units="mm",
            custom_radiation_faces=None,
            custom_coordinate_system=None,
            name=None,
        )

        assert bound

    def test_57_create_near_field_rectangle(self):
        bound = self.aedtapp.insert_near_field_rectangle(
            u_length=20,
            u_samples=21,
            v_length=20,
            v_samples=21,
            units="mm",
            custom_radiation_faces=None,
            custom_coordinate_system=None,
            name=None,
        )
        bound.props["Length"] = "50mm"
        assert bound

    def test_58_create_near_field_line(self):
        test_points = [
            ["0mm", "0mm", "0mm"],
            ["100mm", "20mm", "0mm"],
            ["71mm", "71mm", "0mm"],
            ["0mm", "100mm", "0mm"],
        ]
        line = self.aedtapp.modeler.create_polyline(test_points)
        bound = self.aedtapp.insert_near_field_line(
            line=line.name,
            points=1000,
            custom_radiation_faces=None,
            name=None,
        )
        bound.props["NumPts"] = "200"
        assert bound

    def test_59_test_nastran(self):
        self.aedtapp.insert_design("Nas_teest")
        example_project = os.path.join(local_path, "example_models", test_subfolder, "test_cad.nas")

        cads = self.aedtapp.modeler.import_nastran(example_project)
        assert len(cads) > 0

    def test_60_set_variable(self):
        self.aedtapp.variable_manager.set_variable("var_test", expression="123")
        self.aedtapp["var_test"] = "234"
        assert "var_test" in self.aedtapp.variable_manager.design_variable_names
        assert self.aedtapp.variable_manager.design_variables["var_test"].expression == "234"
