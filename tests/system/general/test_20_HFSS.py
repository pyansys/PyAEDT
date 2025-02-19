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
import os
import re
import shutil

from ansys.aedt.core.generic.errors import AEDTRuntimeError
import pytest

from tests import TESTS_GENERAL_PATH
from tests.system.general.conftest import config
from tests.system.general.conftest import settings

small_number = 1e-10  # Used for checking equivalence.

from ansys.aedt.core.visualization.advanced.misc import convert_nearfield_data

test_subfolder = "T20"

component = "Circ_Patch_5GHz_232.a3dcomp"


if config["desktopVersion"] > "2023.1":
    diff_proj_name = "differential_pairs_231"
else:
    diff_proj_name = "differential_pairs"

component_array = "Array_232"


@pytest.fixture(scope="class")
def aedtapp(add_app):
    app = add_app(project_name="Test_20", design_name="test_20")
    return app


@pytest.fixture(scope="class")
def fall_back_name(aedtapp):
    name = aedtapp.design_name
    return name


class TestClass:
    @pytest.fixture(autouse=True)
    def init(self, aedtapp, fall_back_name, local_scratch):
        self.aedtapp = aedtapp
        self.fall_back_name = fall_back_name
        self.local_scratch = local_scratch

    def test_01_save(self):
        project_name = "Test_Exercse201119"
        test_project = os.path.join(self.local_scratch.path, project_name + ".aedt")
        self.aedtapp.save_project(test_project)
        assert os.path.exists(test_project)

    def test_01A_check_setup(self):
        setup_auto = self.aedtapp.create_setup(name="auto", setup_type="HFSSDrivenAuto")
        assert self.aedtapp.setups[0].name == "auto"
        assert setup_auto.properties["Auto Solver Setting"] == "Balanced"
        assert setup_auto.properties["Type"] == "Discrete"
        assert setup_auto.delete()

    def test_02_create_primitive(self):
        coax1_len = 200
        coax2_len = 70
        r1 = 3.0
        r2 = 10.0
        r1_sq = 9.0  # Used to test area later.
        coax1_origin = self.aedtapp.modeler.Position(0, 0, 0)  # Thru coax origin.
        coax2_origin = self.aedtapp.modeler.Position(125, 0, -coax2_len)  # Perpendicular coax 1.

        inner_1 = self.aedtapp.modeler.create_cylinder(self.aedtapp.AXIS.X, coax1_origin, r1, coax1_len, 0, "inner_1")
        assert isinstance(inner_1.id, int)
        inner_2 = self.aedtapp.modeler.create_cylinder(
            self.aedtapp.AXIS.Z, coax2_origin, r1, coax2_len, 0, "inner_2", material="copper"
        )
        assert len(inner_2.faces) == 3  # Cylinder has 3 faces.
        # Check area of circular face.
        assert abs(min([f.area for f in inner_2.faces]) - math.pi * r1_sq) < small_number
        outer_1 = self.aedtapp.modeler.create_cylinder(self.aedtapp.AXIS.X, coax1_origin, r2, coax1_len, 0, "outer_1")
        assert isinstance(outer_1.id, int)
        outer_2 = self.aedtapp.modeler.create_cylinder(self.aedtapp.AXIS.Z, coax2_origin, r2, coax2_len, 0, "outer_2")

        # Check the area of the outer surface of the cylinder "outer_2".
        assert abs(max([f.area for f in outer_2.faces]) - 2 * coax2_len * r2 * math.pi) < small_number
        inner = self.aedtapp.modeler.unite(
            ["inner_1", "inner_2"],
        )
        outer = self.aedtapp.modeler.unite(
            ["outer_1", "outer_2"],
        )
        assert outer == "outer_1"
        assert inner == "inner_1"
        assert self.aedtapp.modeler.subtract(outer_1, inner_1, keep_originals=True)

    def test_03_2_assign_material(self):
        udp = self.aedtapp.modeler.Position(0, 0, 0)
        coax_length = 80
        cyl_1 = self.aedtapp.modeler.create_cylinder(self.aedtapp.AXIS.X, udp, 10, coax_length, 0, "insulator")
        self.aedtapp.modeler.subtract(cyl_1, "inner_1", keep_originals=True)
        self.aedtapp.modeler["inner_1"].material_name = "Copper"
        cyl_1.material_name = "teflon_based"
        assert self.aedtapp.modeler["inner_1"].material_name == "copper"
        assert cyl_1.material_name == "teflon_based"

    def test_04_assign_coating(self):
        id = self.aedtapp.modeler.get_obj_id(
            "inner_1",
        )
        args = {
            "material": "aluminum",
            "use_thickness": True,
            "thickness": "0.5mm",
            "is_two_side": True,
            "is_shell_element": True,  # TODO: Is "sheelElement" a typo in native API?
            "use_huray": True,
            "radius": "0.75um",
            "ratio": "3",
        }
        coat = self.aedtapp.assign_coating([id, "inner_1", 41], **args)
        coat.name = "Coating1inner"
        assert coat.update()
        assert coat.properties
        material = coat.props.get("Material", "")
        assert material == "aluminum"
        with pytest.raises(AEDTRuntimeError, match="Objects or Faces selected do not exist in the design."):
            self.aedtapp.assign_coating(["insulator2", 45])

    def test_05_create_wave_port_from_sheets(self):
        udp = self.aedtapp.modeler.Position(0, 0, 0)
        o5 = self.aedtapp.modeler.create_circle(self.aedtapp.PLANE.YZ, udp, 10, name="sheet1")
        self.aedtapp.solution_type = "Terminal"
        outer_1 = self.aedtapp.modeler["outer_1"]
        # TODO: Consider allowing a TEM port to be created.
        with pytest.raises(AEDTRuntimeError, match="Reference conductors are missing."):
            self.aedtapp.wave_port(o5)

        port = self.aedtapp.wave_port(
            assignment=o5,
            reference=[outer_1.name],
            integration_line=self.aedtapp.AxisDir.XNeg,
            modes=2,
            impedance=40,
            name="sheet1_Port",
            renormalize=False,
            deembed=5,
            terminals_rename=False,
        )

        assert port.properties
        assert port.name == "sheet1_Port"
        assert port.name in [i.name for i in self.aedtapp.boundaries]
        assert port.props["RenormalizeAllTerminals"] is False

        udp = self.aedtapp.modeler.Position(80, 0, 0)
        o6 = self.aedtapp.modeler.create_circle(self.aedtapp.PLANE.YZ, udp, 10, name="sheet1a")
        self.aedtapp.modeler.subtract(o6, "inner_1", keep_originals=True)

        port = self.aedtapp.wave_port(
            assignment=o6,
            reference=[outer_1.name],
            create_pec_cap=True,
            integration_line=self.aedtapp.AxisDir.XNeg,
            modes=2,
            impedance=40,
            name="sheet1a_Port",
            renormalize=True,
            deembed=0,
        )
        assert port.name == "sheet1a_Port"
        assert port.name in [i.name for i in self.aedtapp.boundaries]
        assert port.props["DoDeembed"] is False

        # Get the object for "outer_1".
        outer_1 = self.aedtapp.modeler["outer_1"]
        bottom_port = self.aedtapp.wave_port(
            outer_1.bottom_face_z, reference=outer_1.name, create_pec_cap=True, name="bottom_probe_port"
        )
        assert bottom_port.name == "bottom_probe_port"
        pec_objects = self.aedtapp.modeler.get_objects_by_material("pec")
        assert len(pec_objects) == 2  # PEC cap created.
        self.aedtapp.solution_type = "Modal"
        assert len(self.aedtapp.boundaries) == 4
        udp = self.aedtapp.modeler.Position(200, 0, 0)
        o6 = self.aedtapp.modeler.create_circle(self.aedtapp.PLANE.YZ, udp, 10, name="sheet2")
        port = self.aedtapp.wave_port(
            assignment=o6,
            integration_line=self.aedtapp.AxisDir.XPos,
            modes=2,
            impedance=40,
            name="sheet2_Port",
            renormalize=True,
            deembed=5,
        )
        assert port.name == "sheet2_Port"
        assert port.name in [i.name for i in self.aedtapp.boundaries]
        assert port.props["RenormalizeAllTerminals"] is True

        id6 = self.aedtapp.modeler.create_box([20, 20, 20], [10, 10, 2], name="My_Box", material="Copper")
        id7 = self.aedtapp.modeler.create_box([20, 25, 30], [10, 2, 2], material="Copper")
        rect = self.aedtapp.modeler.create_rectangle(self.aedtapp.PLANE.YZ, [20, 25, 20], [2, 10])
        port3 = self.aedtapp.wave_port(
            assignment=rect,
            integration_line=self.aedtapp.AxisDir.ZNeg,
            modes=1,
            impedance=30,
            name="sheet3_Port",
            renormalize=False,
            deembed=5,
        )
        assert port3.name in [i.name for i in self.aedtapp.boundaries]

    def test_06a_create_linear_count_sweep(self):
        # Newer, simplified notation to pass native API keywords
        setup = self.aedtapp.create_setup("MySetup", Frequency="1GHz", BasisOrder=2)
        assert setup.props["Frequency"] == "1GHz"
        assert setup.props["BasisOrder"] == 2
        # Legacy notation using setup.props followed by setup.update()
        setup.props["MaximumPasses"] = 1
        assert setup.update()
        assert self.aedtapp.create_linear_count_sweep("MySetup", "GHz", 0.8, 1.2, 401)
        assert not self.aedtapp.setups[0].sweeps[0].is_solved
        assert self.aedtapp.create_linear_count_sweep("MySetup", "GHz", 0.8, 1.2, 401)
        assert self.aedtapp.create_linear_count_sweep(
            setup="MySetup",
            units="GHz",
            start_frequency=1.1e3,
            stop_frequency=1200.1,
            num_of_freq_points=1234,
            sweep_type="Interpolating",
        )
        assert self.aedtapp.create_linear_count_sweep(
            setup="MySetup",
            units="MHz",
            start_frequency=1.1e3,
            stop_frequency=1200.1,
            num_of_freq_points=1234,
            sweep_type="Interpolating",
        )
        assert self.aedtapp.create_linear_count_sweep(
            setup="MySetup",
            units="MHz",
            start_frequency=1.1e3,
            stop_frequency=1200.1,
            num_of_freq_points=1234,
            sweep_type="Fast",
        )
        num_points = 1752
        freq_start = 1.1e3
        freq_stop = 1200.1
        units = "MHz"
        sweep = self.aedtapp.create_linear_count_sweep(
            setup="MySetup",
            units="MHz",
            start_frequency=freq_start,
            stop_frequency=freq_stop,
            num_of_freq_points=num_points,
        )
        assert sweep.props["RangeCount"] == num_points
        assert sweep.props["RangeStart"] == str(freq_start) + units
        assert sweep.props["RangeEnd"] == str(freq_stop) + units
        assert sweep.props["Type"] == "Discrete"

        # Create a linear count sweep with the incorrect sweep type.
        with pytest.raises(AttributeError) as execinfo:
            self.aedtapp.create_linear_count_sweep(
                setup="MySetup",
                units="MHz",
                start_frequency=1.1e3,
                stop_frequency=1200.1,
                num_of_freq_points=1234,
                sweep_type="Incorrect",
            )
            assert (
                execinfo.args[0]
                == "Invalid value for `sweep_type`. The value must be 'Discrete', 'Interpolating', or 'Fast'."
            )
        self.aedtapp["der_var"] = "1mm"
        self.aedtapp["der_var2"] = "2mm"
        setup2 = self.aedtapp.create_setup("MySetup_2", setup_type=0)
        assert setup2.add_derivatives("der_var")
        assert not setup2.set_tuning_offset({"der_var": 0.05})
        assert "der_var" in setup2.get_derivative_variables()
        assert setup2.add_derivatives("der_var2")
        assert "der_var2" in setup2.get_derivative_variables()
        assert "der_var" in setup2.get_derivative_variables()
        setup2.delete()
        setup3 = self.aedtapp.create_setup("MySetup_3", setup_type=1)
        assert setup3.add_derivatives("der_var")
        assert "der_var" in setup3.get_derivative_variables()
        assert setup3.add_derivatives("der_var2")
        assert not self.aedtapp.post.set_tuning_offset(setup3.name, {"der_var": 0.05})
        assert "der_var2" in setup3.get_derivative_variables()
        assert "der_var" in setup3.get_derivative_variables()
        setup3.delete()

    def test_06b_setup_exists(self):
        with pytest.raises(ValueError):
            self.aedtapp.active_setup = "invalid"
        assert self.aedtapp.active_setup is not None
        assert self.aedtapp.nominal_sweep is not None

    def test_06c_create_linear_step_sweep(self):
        step_size = 153.8
        freq_start = 1.1e3
        freq_stop = 1200.1
        units = "MHz"
        sweep = self.aedtapp.create_linear_step_sweep(
            setup="MySetup",
            name=None,
            unit=units,
            start_frequency=freq_start,
            stop_frequency=freq_stop,
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
            setup="MySetup",
            name="StepFast",
            unit=units,
            start_frequency=freq_start,
            stop_frequency=freq_stop,
            step_size=step_size,
            sweep_type="Fast",
        )
        assert sweep.props["RangeStep"] == str(step_size) + units
        assert sweep.props["RangeStart"] == str(freq_start) + units
        assert sweep.props["RangeEnd"] == str(freq_stop) + units
        assert sweep.props["Type"] == "Fast"

        # Create a linear step sweep with the incorrect sweep type.
        with pytest.raises(AttributeError) as execinfo:
            self.aedtapp.create_linear_step_sweep(
                setup="MySetup",
                name="StepFast",
                unit=units,
                start_frequency=freq_start,
                stop_frequency=freq_stop,
                step_size=step_size,
                sweep_type="Incorrect",
            )
            assert (
                execinfo.args[0]
                == "Invalid value for 'sweep_type'. The value must be 'Discrete', 'Interpolating', or 'Fast'."
            )

    def test_06d_create_single_point_sweep(self):
        assert self.aedtapp.create_single_point_sweep(
            setup="MySetup",
            unit="MHz",
            freq=1.2e3,
        )
        setup = self.aedtapp.get_setup("MySetup")
        assert setup.create_single_point_sweep(
            unit="GHz",
            freq=1.2,
            save_single_field=False,
        )
        assert self.aedtapp.create_single_point_sweep(
            setup="MySetup",
            unit="GHz",
            freq=[1.1, 1.2, 1.3],
        )
        assert self.aedtapp.create_single_point_sweep(
            setup="MySetup", unit="GHz", freq=[1.1e1, 1.2e1, 1.3e1], save_single_field=[True, False, True]
        )
        settings.enable_error_handler = True
        assert not self.aedtapp.create_single_point_sweep(
            setup="MySetup", unit="GHz", freq=[1, 2e2, 3.4], save_single_field=[True, False]
        )
        settings.enable_error_handler = False

    def test_06e_delete_setup(self):
        setup_name = "SetupToDelete"
        setuptd = self.aedtapp.create_setup(name=setup_name)
        assert setuptd.name in self.aedtapp.existing_analysis_setups
        assert self.aedtapp.delete_setup(setup_name)
        assert setuptd.name not in self.aedtapp.existing_analysis_setups

    def test_06f_sweep_add_subrange(self):
        self.aedtapp.modeler.create_box([0, 0, 20], [10, 10, 5], "box_sweep", "Copper")
        self.aedtapp.modeler.create_box([0, 0, 30], [10, 10, 5], "box_sweep2", "Copper")
        self.aedtapp.wave_port(
            assignment="box_sweep",
            reference="box_sweep2",
            create_port_sheet=True,
            integration_line=self.aedtapp.AxisDir.XNeg,
            modes=1,
            impedance=75,
            name="WaveForSweep",
            renormalize=False,
        )
        setup = self.aedtapp.create_setup(name="MySetupForSweep")
        assert not setup.get_sweep()
        sweep = setup.add_sweep()
        sweep1 = setup.get_sweep(sweep.name)
        assert sweep1 == sweep
        sweep2 = setup.get_sweep()
        assert sweep2 == sweep1
        assert sweep.add_subrange("LinearCount", 1, 3, 10, "GHz")
        assert sweep.add_subrange("LinearCount", 2, 4, 10, "GHz")
        assert sweep.add_subrange("LinearStep", 1.1, 2.1, 0.4, "GHz")
        assert sweep.add_subrange("LinearCount", 1, 1.5, 5, "MHz")
        assert sweep.add_subrange("LogScale", 1, 3, 10, "GHz")

    def test_06g_sweep_clear_subrange(self):
        self.aedtapp.modeler.create_box([0, 0, 50], [10, 10, 5], "box_sweep3", "Copper")
        self.aedtapp.modeler.create_box([0, 0, 60], [10, 10, 5], "box_sweep4", "Copper")
        self.aedtapp.wave_port(
            assignment="box_sweep3",
            reference="box_sweep4",
            create_port_sheet=True,
            integration_line=self.aedtapp.AxisDir.XNeg,
            modes=1,
            impedance=50,
            name="WaveForSweepWithClear",
            renormalize=False,
        )

        setup = self.aedtapp.create_setup(name="MySetupClearSweep")
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
        list, ok = self.aedtapp.validate_full_design(ports=len(self.aedtapp.excitations))
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
            self.aedtapp.circuit_port(
                e1, e2, impedance=50.1, name="port10", renormalize=False, renorm_impedance="50"
            ).name
            == "port10"
        )
        assert (
            self.aedtapp.circuit_port(
                e1, e2, impedance="50+1i*55", name="port11", renormalize=True, renorm_impedance=15.4
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
            self.aedtapp.circuit_port(
                e1, e2, impedance=50.1, name="port20", renormalize=False, renorm_impedance="50+1i*55"
            ).name
            == "port20"
        )
        bound = self.aedtapp.circuit_port(e1, e2, impedance="50.1", name="port32", renormalize=True)
        assert bound
        bound.name = "port21"
        assert bound.update()
        self.aedtapp.solution_type = "Modal"

    def test_09_create_waveport_on_objects(self):
        box1 = self.aedtapp.modeler.create_box([0, 0, 0], [10, 10, 5], "BoxWG1", "Copper")
        box2 = self.aedtapp.modeler.create_box([0, 0, 10], [10, 10, 5], "BoxWG2", "copper")
        box2.material_name = "Copper"
        port = self.aedtapp.wave_port(
            assignment="BoxWG1",
            reference="BoxWG2",
            create_port_sheet=True,
            integration_line=self.aedtapp.AxisDir.XNeg,
            modes=1,
            impedance=50,
            name="Wave1",
            renormalize=False,
        )
        assert port.name == "Wave1"
        port2 = self.aedtapp.wave_port(
            assignment="BoxWG1",
            reference="BoxWG2",
            create_port_sheet=True,
            integration_line=self.aedtapp.AxisDir.XPos,
            modes=2,
            impedance=25,
            name="Wave1",
            renormalize=True,
            deembed=5,
        )

        assert port2.name != "Wave1" and "Wave1" in port2.name
        self.aedtapp.solution_type = "Terminal"
        assert self.aedtapp.wave_port(
            assignment="BoxWG1",
            reference="BoxWG2",
            create_port_sheet=True,
            integration_line=self.aedtapp.AxisDir.XPos,
            modes=2,
            impedance=25,
            name="Wave3",
            renormalize=True,
        )

        self.aedtapp.solution_type = "Modal"
        assert self.aedtapp.wave_port(
            assignment="BoxWG1",
            reference="BoxWG2",
            create_port_sheet=True,
            integration_line=self.aedtapp.AxisDir.XPos,
            modes=2,
            impedance=25,
            name="Wave4",
            renormalize=True,
            deembed=5,
        )

    def test_09a_create_waveport_on_true_surface_objects(self):
        cs = self.aedtapp.PLANE.XY
        o1 = self.aedtapp.modeler.create_cylinder(
            cs, [0, 0, 0], radius=5, height=100, num_sides=0, name="inner", material="Copper"
        )
        o3 = self.aedtapp.modeler.create_cylinder(
            cs, [0, 0, 0], radius=10, height=100, num_sides=0, name="outer", material="Copper"
        )
        port1 = self.aedtapp.wave_port(
            assignment=o1.name,
            reference=o3.name,
            create_port_sheet=True,
            create_pec_cap=True,
            integration_line=self.aedtapp.AxisDir.XNeg,
            name="P1",
        )
        assert port1.name.startswith("P1")

    def test_10_create_lumped_on_objects(self):
        box1 = self.aedtapp.modeler.create_box([0, 0, 50], [10, 10, 5], "BoxLumped1")
        box1.material_name = "Copper"
        box2 = self.aedtapp.modeler.create_box([0, 0, 60], [10, 10, 5], "BoxLumped2")
        box2.material_name = "Copper"
        port = self.aedtapp.lumped_port(
            assignment="BoxLumped1",
            reference="BoxLumped2",
            create_port_sheet=True,
            integration_line=self.aedtapp.AxisDir.XNeg,
            impedance=50,
            name="Lump1xx",
            renormalize=True,
        )
        with pytest.raises(AEDTRuntimeError, match="One or both objects do not exist. Check and retry."):
            self.aedtapp.lumped_port(
                assignment="BoxLumped1111",
                reference="BoxLumped2",
                create_port_sheet=True,
                integration_line=self.aedtapp.AxisDir.XNeg,
                impedance=50,
                name="Lump1xx",
                renormalize=True,
            )

        assert self.aedtapp.lumped_port(
            assignment="BoxLumped1",
            reference="BoxLumped2",
            create_port_sheet=True,
            integration_line=self.aedtapp.AxisDir.XPos,
            impedance=50,
        )

        assert port.name == "Lump1xx"
        port.name = "Lump1"
        assert port.update()
        port = self.aedtapp.lumped_port(
            assignment="BoxLumped1",
            reference="BoxLumped2",
            create_port_sheet=True,
            integration_line=self.aedtapp.AxisDir.XNeg,
            impedance=50,
            name="Lump2",
            renormalize=False,
            deembed=True,
        )

    def test_11_create_circuit_on_objects(self):
        self.aedtapp.insert_design("test_11")
        box1 = self.aedtapp.modeler.create_box([0, 0, 80], [10, 10, 5], "BoxCircuit1", "Copper")
        box2 = self.aedtapp.modeler.create_box([0, 0, 100], [10, 10, 5], "BoxCircuit2", "copper")
        box2.material_name = "Copper"
        port = self.aedtapp.circuit_port(
            "BoxCircuit1", "BoxCircuit2", self.aedtapp.AxisDir.XNeg, 50, "Circ1", True, 50, False
        )
        assert port.name == "Circ1"
        with pytest.raises(AEDTRuntimeError, match="Failed to create circuit port."):
            self.aedtapp.circuit_port(
                "BoxCircuit44", "BoxCircuit2", self.aedtapp.AxisDir.XNeg, 50, "Circ1", True, 50, False
            )
        self.aedtapp.delete_design("test_11", self.fall_back_name)

    def test_12_create_perfects_on_objects(self):
        self.aedtapp.insert_design("test_12")
        box1 = self.aedtapp.modeler.create_box([0, 0, 0], [10, 10, 5], "perfect1", "Copper")
        box2 = self.aedtapp.modeler.create_box([0, 0, 10], [10, 10, 5], "perfect2", "copper")

        ph = self.aedtapp.create_perfecth_from_objects(
            box1.name, box2.name, self.aedtapp.AxisDir.ZNeg, is_boundary_on_plane=False
        )

        pe = self.aedtapp.create_perfecte_from_objects(
            box1.name, box2.name, self.aedtapp.AxisDir.ZNeg, is_boundary_on_plane=False
        )
        assert pe.name in self.aedtapp.modeler.get_boundaries_name()
        assert pe.update()
        assert ph.name in self.aedtapp.modeler.get_boundaries_name()
        assert ph.update()
        self.aedtapp.delete_design("test_12", self.fall_back_name)

    def test_13_create_impedance_on_objects(self):
        box1 = self.aedtapp.modeler.create_box([0, 0, 0], [10, 10, 5], "imp1", "Copper")
        box2 = self.aedtapp.modeler.create_box([0, 0, 10], [10, 10, 5], "imp2", "copper")
        imp = self.aedtapp.create_impedance_between_objects(
            box1.name, box2.name, self.aedtapp.AxisDir.XPos, "TL1", 50, 25
        )
        assert imp.name in self.aedtapp.modeler.get_boundaries_name()
        assert imp.update()

    pytest.mark.skipif(config["desktopVersion"] > "2023.2", reason="Crashing Desktop")

    def test_14_create_lumpedrlc_on_objects(self):
        box1 = self.aedtapp.modeler.create_box([0, 0, 0], [10, 10, 5], "rlc1", "Copper")
        box2 = self.aedtapp.modeler.create_box([0, 0, 10], [10, 10, 5], "rlc2", "copper")
        imp = self.aedtapp.create_lumped_rlc_between_objects(
            box1.name, box2.name, self.aedtapp.AxisDir.XPos, resistance=50, inductance=1e-9
        )
        assert imp.name in self.aedtapp.modeler.get_boundaries_name()
        assert imp.update()

        box3 = self.aedtapp.modeler.create_box([0, 0, 20], [10, 10, 5], "rlc3", "copper")
        lumped_rlc2 = self.aedtapp.create_lumped_rlc_between_objects(
            box2.name, box3.name, self.aedtapp.AxisDir.XPos, resistance=50, inductance=1e-9, capacitance=1e-9
        )
        assert lumped_rlc2.name in self.aedtapp.modeler.get_boundaries_name()
        assert lumped_rlc2.update()

    def test_15_create_perfects_on_sheets(self):
        rect = self.aedtapp.modeler.create_rectangle(
            self.aedtapp.PLANE.XY, [0, 0, 0], [10, 2], name="RectBound", material="Copper"
        )
        pe = self.aedtapp.assign_perfecte_to_sheets(rect.name)
        assert pe.name in self.aedtapp.modeler.get_boundaries_name()
        ph = self.aedtapp.assign_perfecth_to_sheets(rect.name)
        assert ph.name in self.aedtapp.modeler.get_boundaries_name()
        solution_type = self.aedtapp.solution_type

        self.aedtapp.solution_type = "Eigen Mode"
        perfect_h_eigen = self.aedtapp.assign_perfecth_to_sheets(rect.name)
        assert perfect_h_eigen.name in self.aedtapp.modeler.get_boundaries_name()
        perfect_e_eigen = self.aedtapp.assign_perfecte_to_sheets(rect.name)
        assert perfect_e_eigen.name in self.aedtapp.modeler.get_boundaries_name()
        self.aedtapp.solution_type = "solution_type"

    def test_16_a_create_impedance_on_sheets(self):
        rect = self.aedtapp.modeler.create_rectangle(
            self.aedtapp.PLANE.XY, [0, 0, 0], [10, 2], name="ImpBound", material="Copper"
        )
        imp1 = self.aedtapp.assign_impedance_to_sheet(rect.name, "TL2", 50, 25)
        assert imp1.name in self.aedtapp.modeler.get_boundaries_name()
        assert imp1.update()

        impedance_box = self.aedtapp.modeler.create_box([0, -100, 0], [200, 200, 200], "ImpedanceBox")
        ids = self.aedtapp.modeler.get_object_faces(impedance_box.name)[:3]

        imp2 = self.aedtapp.assign_impedance_to_sheet(ids, resistance=60, reactance=-20)
        assert imp2.name in self.aedtapp.modeler.get_boundaries_name()

        rect2 = self.aedtapp.modeler.create_rectangle(
            self.aedtapp.PLANE.XY, [0, 0, 0], [10, 2], name="AniImpBound", material="Copper"
        )
        with pytest.raises(AEDTRuntimeError, match="Number of elements in resistance and reactance must be four."):
            self.aedtapp.assign_impedance_to_sheet(rect2.name, "TL3", [50, 20, 0, 0], [25, 0, 5])

        imp2 = self.aedtapp.assign_impedance_to_sheet(rect2.name, "TL3", [50, 20, 0, 0], [25, 0, 5, 0])
        assert imp2.name in self.aedtapp.modeler.get_boundaries_name()
        imp3 = self.aedtapp.assign_impedance_to_sheet(impedance_box.top_face_z.id, "TL4", [50, 20, 0, 0], [25, 0, 5, 0])
        assert imp3.name in self.aedtapp.modeler.get_boundaries_name()

    def test_16_b_create_impedance_on_sheets_eigenmode(self, add_app):
        aedtapp = add_app(solution_type="Eigenmode", project_name="test_16_b")
        rect = aedtapp.modeler.create_rectangle(
            aedtapp.PLANE.XY, [0, 0, 0], [10, 2], name="ImpBound", material="Copper"
        )
        imp1 = aedtapp.assign_impedance_to_sheet(rect.name, "TL2", 50, 25)
        assert imp1.name in aedtapp.modeler.get_boundaries_name()

    def test_17_create_lumpedrlc_on_sheets(self):
        rect = self.aedtapp.modeler.create_rectangle(
            self.aedtapp.PLANE.XY, [0, 0, 0], [10, 2], name="rlcBound", material="Copper"
        )
        imp = self.aedtapp.assign_lumped_rlc_to_sheet(
            rect.name, self.aedtapp.AxisDir.XPos, resistance=50, inductance=1e-9
        )
        names = self.aedtapp.modeler.get_boundaries_name()
        assert imp.name in self.aedtapp.modeler.get_boundaries_name()

        rect2 = self.aedtapp.modeler.create_rectangle(
            self.aedtapp.PLANE.XY, [0, 0, 10], [10, 2], name="rlcBound2", material="Copper"
        )
        imp = self.aedtapp.assign_lumped_rlc_to_sheet(
            rect.name, self.aedtapp.AxisDir.XPos, rlc_type="Serial", resistance=50, inductance=1e-9
        )
        names = self.aedtapp.modeler.get_boundaries_name()
        assert imp.name in self.aedtapp.modeler.get_boundaries_name()
        assert self.aedtapp.assign_lumped_rlc_to_sheet(
            rect.name, [rect.bottom_edge_x.midpoint, rect.bottom_edge_y.midpoint], inductance=1e-9
        )
        with pytest.raises(AEDTRuntimeError, match="List of coordinates is not set correctly"):
            self.aedtapp.assign_lumped_rlc_to_sheet(rect.name, [rect.bottom_edge_x.midpoint], inductance=1e-9)

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
            self.aedtapp.PLANE.XY, [0, 0, 0], [10, 2], name="lump_port", material="Copper"
        )
        port = self.aedtapp.lumped_port(
            assignment=rect.name,
            create_port_sheet=False,
            integration_line=self.aedtapp.AxisDir.XNeg,
            impedance=50,
            name="Lump_sheet",
            renormalize=True,
        )

        assert port.name + ":1" in self.aedtapp.excitations
        port2 = self.aedtapp.lumped_port(
            assignment=rect.name,
            create_port_sheet=False,
            integration_line=self.aedtapp.AxisDir.XNeg,
            impedance=50,
            name="Lump_sheet2",
            renormalize=True,
            deembed=True,
        )

        assert port2.name + ":1" in self.aedtapp.excitations
        port3 = self.aedtapp.lumped_port(
            assignment=rect.name,
            create_port_sheet=False,
            integration_line=[rect.bottom_edge_x.midpoint, rect.bottom_edge_y.midpoint],
            impedance=50,
            name="Lump_sheet3",
            renormalize=True,
            deembed=True,
        )

        assert port3.name + ":1" in self.aedtapp.excitations
        with pytest.raises(ValueError, match="List of coordinates is not set correctly."):
            self.aedtapp.lumped_port(
                assignment=rect.name,
                create_port_sheet=False,
                integration_line=[rect.bottom_edge_x.midpoint],
                impedance=50,
                name="Lump_sheet4",
                renormalize=True,
                deembed=True,
            )

    def test_20_create_voltage_on_sheet(self):
        rect = self.aedtapp.modeler.create_rectangle(
            self.aedtapp.PLANE.XY, [0, 0, 0], [10, 2], name="lump_volt", material="Copper"
        )
        port = self.aedtapp.assign_voltage_source_to_sheet(rect.name, self.aedtapp.AxisDir.XNeg, "LumpVolt1")
        assert port.name in self.aedtapp.excitations
        assert self.aedtapp.get_property_value("BoundarySetup:LumpVolt1", "VoltageMag", "Excitation") == "1V"
        port = self.aedtapp.assign_voltage_source_to_sheet(
            rect.name, [rect.bottom_edge_x.midpoint, rect.bottom_edge_y.midpoint], "LumpVolt2"
        )
        assert port.name in self.aedtapp.excitations
        with pytest.raises(AEDTRuntimeError, match="List of coordinates is not set correctly"):
            self.aedtapp.assign_voltage_source_to_sheet(rect.name, [rect.bottom_edge_x.midpoint], "LumpVolt2")

    def test_21_create_open_region(self):
        assert self.aedtapp.create_open_region("1GHz")
        assert len(self.aedtapp.field_setups) == 3
        assert self.aedtapp.create_open_region("1GHz", "FEBI")
        assert self.aedtapp.create_open_region("1GHz", "PML", True, "-z")

    def test_22_create_length_mesh(self):
        box1 = self.aedtapp.modeler.create_box([30, 0, 0], [40, 10, 5], "BoxCircuit1", "Copper")
        mesh = self.aedtapp.mesh.assign_length_mesh(["BoxCircuit1"])
        assert mesh
        mesh.props["NumMaxElem"] = "100"
        assert mesh.props["NumMaxElem"] == self.aedtapp.odesign.GetChildObject("Mesh").GetChildObject(
            mesh.name
        ).GetPropValue("Max Elems")

    def test_23_create_skin_depth(self):
        box1 = self.aedtapp.modeler.create_box([30, 0, 0], [40, 10, 5], "BoxCircuit2", "Copper")
        mesh = self.aedtapp.mesh.assign_skin_depth(["BoxCircuit2"], "1mm")
        assert mesh
        mesh.props["SkinDepth"] = "3mm"
        assert mesh.props["SkinDepth"] == self.aedtapp.odesign.GetChildObject("Mesh").GetChildObject(
            mesh.name
        ).GetPropValue("Skin Depth")

    def test_24_create_curvilinear(self):
        box1 = self.aedtapp.modeler.create_box([30, 0, 0], [40, 10, 5], "BoxCircuit3", "Copper")
        mesh = self.aedtapp.mesh.assign_curvilinear_elements(["BoxCircuit3"])
        assert mesh
        mesh.props["Apply"] = False
        assert mesh.props["Apply"] == self.aedtapp.odesign.GetChildObject("Mesh").GetChildObject(
            mesh.name
        ).GetPropValue("Apply Curvilinear Elements")
        mesh.delete()
        assert len(self.aedtapp.mesh.meshoperations) == 2

    def test_30a_assign_initial_mesh(self):
        assert self.aedtapp.mesh.assign_initial_mesh_from_slider(6)

    def test_03b_assign_initial_mesh(self):
        assert self.aedtapp.mesh.assign_initial_mesh()
        assert self.aedtapp.mesh.assign_initial_mesh(normal_deviation="25deg", surface_deviation=0.2, aspect_ratio=20)

    def test_30a_add_mesh_link(self):
        design_name = self.aedtapp.design_name
        nominal_adaptive = self.aedtapp.nominal_adaptive
        self.aedtapp.duplicate_design(self.aedtapp.design_name)
        self.aedtapp._setups = None
        assert self.aedtapp.setups[0].add_mesh_link(design=design_name)
        meshlink_props = self.aedtapp.setups[0].props["MeshLink"]
        assert meshlink_props["Project"] == "This Project*"
        assert meshlink_props["PathRelativeTo"] == "TargetProject"
        assert meshlink_props["Design"] == design_name
        assert meshlink_props["Soln"] == nominal_adaptive

        # Deprecated
        assert sorted(list(meshlink_props["Params"].keys())) == sorted(self.aedtapp.available_variations.variables)
        assert sorted(list(meshlink_props["Params"].values())) == sorted(self.aedtapp.available_variations.variables)

        assert not self.aedtapp.setups[0].add_mesh_link(design="")
        assert self.aedtapp.setups[0].add_mesh_link(design=design_name, solution="MySetup : LastAdaptive")
        assert not self.aedtapp.setups[0].add_mesh_link(design=design_name, solution="Setup_Test : LastAdaptive")
        assert self.aedtapp.setups[0].add_mesh_link(
            design=design_name, parameters=self.aedtapp.available_variations.nominal_w_values_dict
        )
        example_project = os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, diff_proj_name + ".aedt")
        example_project_copy = os.path.join(self.local_scratch.path, diff_proj_name + "_copy.aedt")
        shutil.copyfile(example_project, example_project_copy)
        assert self.aedtapp.setups[0].add_mesh_link(design=design_name, project=example_project_copy)

    def test_31_create_microstrip_port(self):
        self.aedtapp.insert_design("Microstrip")
        self.aedtapp.solution_type = "Modal"
        ms = self.aedtapp.modeler.create_box([4, 5, 0], [1, 100, 0.2], name="MS1", material="copper")
        sub = self.aedtapp.modeler.create_box([0, 5, -2], [20, 100, 2], name="SUB1", material="FR4_epoxy")
        gnd = self.aedtapp.modeler.create_box([0, 5, -2.2], [20, 100, 0.2], name="GND1", material="FR4_epoxy")
        port = self.aedtapp.wave_port(
            assignment=gnd.name,
            reference=ms.name,
            create_port_sheet=True,
            integration_line=1,
            name="MS1",
            is_microstrip=True,
        )
        assert port.name == "MS1"
        assert port.update()
        self.aedtapp.solution_type = "Terminal"
        assert self.aedtapp.wave_port(
            assignment=gnd.name,
            reference=ms.name,
            create_port_sheet=True,
            integration_line=1,
            name="MS2",
            is_microstrip=True,
        )
        assert self.aedtapp.wave_port(
            assignment=gnd.name,
            reference=ms.name,
            create_port_sheet=True,
            integration_line=1,
            impedance=77,
            name="MS3",
            deembed=1,
            is_microstrip=True,
        )

    def test_32_get_property_value(self):
        rect = self.aedtapp.modeler.create_rectangle(
            self.aedtapp.PLANE.XY, [0, 0, 0], [10, 2], name="RectProp", material="Copper"
        )
        pe = self.aedtapp.assign_perfecte_to_sheets(rect.name, "PerfectE_1")
        setup = self.aedtapp.create_setup("MySetup2")
        setup.props["Frequency"] = "1GHz"
        assert self.aedtapp.get_property_value("BoundarySetup:PerfectE_1", "Inf Ground Plane", "Boundary") == "false"
        assert self.aedtapp.get_property_value("AnalysisSetup:MySetup2", "Solution Freq", "Setup") == "1GHz"

    def test_33_copy_solid_bodies(self, add_app):
        project_name = "HfssCopiedProject"
        design_name = "HfssCopiedBodies"
        new_design = add_app(project_name=project_name, design_name=design_name)
        num_orig_bodies = len(self.aedtapp.modeler.solid_names)
        assert new_design.copy_solid_bodies_from(self.aedtapp, no_vacuum=False, no_pec=False)
        assert len(new_design.modeler.solid_bodies) == num_orig_bodies
        new_design.delete_design(design_name)
        new_design.close_project(project_name)

    def test_34_object_material_properties(self):
        self.aedtapp.insert_design("ObjMat")
        self.aedtapp.solution_type = "Modal"
        ms = self.aedtapp.modeler.create_box([4, 5, 0], [1, 100, 0.2], name="MS1", material="copper")
        props = self.aedtapp.get_object_material_properties("MS1", "conductivity")
        assert props

    def test_35_set_export_touchstone(self):
        assert self.aedtapp.export_touchstone_on_completion(True)
        assert self.aedtapp.export_touchstone_on_completion(False)

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
        sources2 = self.aedtapp.get_all_source_modes()
        assert isinstance(sources2, list)

    def test_40_assign_current_source_to_sheet(self):
        sheet = self.aedtapp.modeler.create_rectangle(
            self.aedtapp.PLANE.XY, [0, 0, 0], [5, 1], name="RectangleForSource", material="Copper"
        )
        assert self.aedtapp.assign_current_source_to_sheet(sheet.name)
        assert self.aedtapp.assign_current_source_to_sheet(
            sheet.name, [sheet.bottom_edge_x.midpoint, sheet.bottom_edge_y.midpoint]
        )
        with pytest.raises(AEDTRuntimeError, match="List of coordinates is not set correctly"):
            self.aedtapp.assign_current_source_to_sheet(sheet.name, [sheet.bottom_edge_x.midpoint])

    def test_41_export_step(self):
        file_name = "test"
        self.aedtapp.modeler.create_box([0, 0, 0], [10, 10, 10])
        assert self.aedtapp.export_3d_model(file_name, self.aedtapp.working_directory, ".x_t", [], [])
        assert os.path.exists(os.path.join(self.aedtapp.working_directory, file_name + ".x_t"))

    def test_42_floquet_port(self):
        self.aedtapp.insert_design("floquet")
        self.aedtapp.solution_type = "Modal"

        box1 = self.aedtapp.modeler.create_box([-100, -100, -100], [200, 200, 200], name="Rad_box2")
        assert self.aedtapp.create_floquet_port(
            box1.faces[0], modes=7, deembed_distance=1, reporter_filter=[False, True, False, False, False, False, False]
        )
        assert self.aedtapp.create_floquet_port(
            box1.faces[1], modes=7, deembed_distance=1, reporter_filter=[False, True, False, False, False, False, False]
        )
        sheet = self.aedtapp.modeler.create_rectangle(
            self.aedtapp.PLANE.XY, [-100, -100, -100], [200, 200], name="RectangleForSource", material="Copper"
        )
        bound = self.aedtapp.create_floquet_port(sheet, modes=4, deembed_distance=1, reporter_filter=False)
        assert bound
        bound.name = "Floquet1"
        assert bound.update()
        self.aedtapp.delete_design("floquet", self.fall_back_name)

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
        self.aedtapp.delete_design("lattice", self.fall_back_name)

    def test_44_create_infinite_sphere(self):
        self.aedtapp.insert_design("InfSphere")
        air = self.aedtapp.modeler.create_box([0, 0, 0], [20, 20, 20], name="rad", material="vacuum")
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

    def test_45_set_autoopen(self):
        assert self.aedtapp.set_auto_open(True, "PML")

    def test_45_terminal_port(self):
        self.aedtapp.insert_design("Design_Terminal")
        self.aedtapp.solution_type = "Terminal"
        box1 = self.aedtapp.modeler.create_box([-100, -100, 0], [200, 200, 5], name="gnd", material="copper")
        box2 = self.aedtapp.modeler.create_box([-100, -100, 20], [200, 200, 25], name="sig", material="copper")
        sheet = self.aedtapp.modeler.create_rectangle(self.aedtapp.PLANE.YZ, [-100, -100, 5], [200, 15], "port")
        port = self.aedtapp.lumped_port(
            assignment=box1,
            reference=box2.name,
            create_port_sheet=True,
            integration_line=self.aedtapp.AxisDir.XNeg,
            impedance=75,
            name="Lump1",
            renormalize=True,
        )

        assert "Lump1_T1" in self.aedtapp.excitations
        port2 = self.aedtapp.lumped_port(
            assignment=sheet.name,
            reference=box1,
            create_port_sheet=False,
            integration_line=self.aedtapp.AxisDir.XNeg,
            impedance=33,
            name="Lump_sheet",
            renormalize=True,
        )
        assert port2.name + "_T1" in self.aedtapp.excitations
        port3 = self.aedtapp.lumped_port(
            assignment=box1,
            reference=box2.name,
            create_port_sheet=True,
            integration_line=self.aedtapp.AxisDir.XNeg,
            impedance=50,
            name="Lump3",
            renormalize=False,
            deembed=True,
        )
        assert port3.name + "_T1" in self.aedtapp.excitations
        self.aedtapp.delete_design("Design_Terminal", self.fall_back_name)

    def test_45B_terminal_port(self):
        self.aedtapp.insert_design("Design_Terminal_2")
        self.aedtapp.solution_type = "Terminal"
        box1 = self.aedtapp.modeler.create_box([-100, -100, 0], [200, 200, 5], name="gnd2z", material="copper")
        box2 = self.aedtapp.modeler.create_box([-100, -100, 20], [200, 200, 25], name="sig2z", material="copper")
        box3 = self.aedtapp.modeler.create_box([-40, -40, -20], [80, 80, 10], name="box3", material="copper")
        box4 = self.aedtapp.modeler.create_box([-40, -40, 10], [80, 80, 10], name="box4", material="copper")
        box1.display_wireframe = True
        box2.display_wireframe = True
        box3.display_wireframe = True
        box4.display_wireframe = True
        self.aedtapp.modeler.fit_all()
        portz = self.aedtapp.create_spiral_lumped_port(box1, box2)
        assert portz

        n_boundaries = len(self.aedtapp.boundaries)
        assert n_boundaries == 4

        box5 = self.aedtapp.modeler.create_box([-50, -15, 200], [150, -10, 200], name="gnd2y", material="copper")
        box6 = self.aedtapp.modeler.create_box([-50, 10, 200], [150, 15, 200], name="sig2y", material="copper")
        box5.display_wireframe = True
        box6.display_wireframe = True
        self.aedtapp.modeler.fit_all()
        porty = self.aedtapp.create_spiral_lumped_port(box5, box6)
        assert porty

        n_boundaries = len(self.aedtapp.boundaries)
        assert n_boundaries == 8

        box7 = self.aedtapp.modeler.create_box([-15, 300, 0], [-10, 200, 100], name="gnd2x", material="copper")
        box8 = self.aedtapp.modeler.create_box([15, 300, 0], [10, 200, 100], name="sig2x", material="copper")
        box7.display_wireframe = True
        box8.display_wireframe = True
        self.aedtapp.modeler.fit_all()
        portx = self.aedtapp.create_spiral_lumped_port(box7, box8)
        assert portx

        n_boundaries = len(self.aedtapp.boundaries)
        assert n_boundaries == 12

        # Use two boxes with different dimensions.
        with pytest.raises(AttributeError) as execinfo:
            self.aedtapp.create_spiral_lumped_port(box1, box3)
            assert execinfo.args[0] == "The closest faces of the two objects must be identical in shape."

        # Rotate box3 so that, box3 and box4 are not collinear anymore.
        # Spiral lumped port can only be created based on 2 collinear objects.
        box3.rotate(axis="X", angle=90)
        with pytest.raises(AttributeError) as execinfo:
            self.aedtapp.create_spiral_lumped_port(box3, box4)
            assert execinfo.args[0] == "The two objects must have parallel adjacent faces."

        # Rotate back box3
        # rotate them slightly so that they are still parallel, but not aligned anymore with main planes.
        box3.rotate(axis="X", angle=-90)
        box3.rotate(axis="Y", angle=5)
        box4.rotate(axis="Y", angle=5)
        with pytest.raises(AttributeError) as execinfo:
            self.aedtapp.create_spiral_lumped_port(box3, box4)
            assert (
                execinfo.args[0]
                == "The closest faces of the two objects must be aligned with the main planes of the reference system."
            )
        self.aedtapp.delete_design("Design_Terminal_2", self.fall_back_name)

    def test_46_mesh_settings(self):
        assert self.aedtapp.mesh.initial_mesh_settings
        assert self.aedtapp.mesh.initial_mesh_settings.props

    def test_47_convert_near_field(self):
        example_project = os.path.join(TESTS_GENERAL_PATH, "example_models", "nf_test")
        assert os.path.exists(convert_nearfield_data(example_project, output_folder=self.local_scratch.path))

    def test_48_traces(self):
        assert len(self.aedtapp.excitations) > 0
        assert len(self.aedtapp.get_traces_for_plot()) > 0

    def test_49_port_creation_exception(self):
        box1 = self.aedtapp.modeler.create_box([-400, -40, -20], [80, 80, 10], name="gnd49", material="copper")
        box2 = self.aedtapp.modeler.create_box([-400, -40, 10], [80, 80, 10], name="sig49", material="copper")

        self.aedtapp.solution_type = "Modal"
        # Spiral lumped port can only be created in a 'Terminal' solution.
        with pytest.raises(Exception) as execinfo:
            self.aedtapp.create_spiral_lumped_port(box1, box2)
            assert execinfo.args[0] == "This method can be used only in 'Terminal' solutions."
        self.aedtapp.solution_type = "Terminal"

        # Try to modify SBR+ TX RX antenna settings in a solution that is different from SBR+
        # should not be possible.
        with pytest.raises(AEDTRuntimeError, match=re.escape("This boundary only applies to a SBR+ solution.")):
            self.aedtapp.set_sbr_txrx_settings({"TX1": "RX1"})

        # SBR linked antenna can only be created within an SBR+ solution.
        with pytest.raises(AEDTRuntimeError, match=re.escape("Native components only apply to the SBR+ solution.")):
            self.aedtapp.create_sbr_linked_antenna(self.aedtapp, field_type="farfield")

        # Chirp I doppler setup only works within an SBR+ solution.
        with pytest.raises(AEDTRuntimeError, match=re.escape("Method applies only to the SBR+ solution.")):
            self.aedtapp.create_sbr_chirp_i_doppler_setup(sweep_time_duration=20)

        # Chirp IQ doppler setup only works within an SBR+ solution.
        with pytest.raises(AEDTRuntimeError, match=re.escape("Method applies only to the SBR+ solution.")):
            self.aedtapp.create_sbr_chirp_iq_doppler_setup(sweep_time_duration=10)

    def test_50_set_differential_pair(self, add_app):
        hfss1 = add_app(project_name=diff_proj_name, design_name="Hfss_Terminal", subfolder=test_subfolder)
        assert hfss1.set_differential_pair(
            assignment="P2_T1",
            reference="P2_T2",
            differential_mode=None,
            common_reference=34,
            differential_reference=123,
            active=True,
            matched=False,
        )
        assert not hfss1.set_differential_pair(assignment="P2_T1", reference="P2_T3")
        hfss2 = add_app(design_name="Hfss_Transient")
        assert hfss2.set_differential_pair(
            assignment="P2_T1",
            reference="P2_T2",
            differential_mode=None,
            common_reference=34,
            differential_reference=123,
            active=True,
            matched=False,
        )
        assert not hfss2.set_differential_pair(assignment="P2_T1", reference="P2_T3")
        hfss2.close_project()

    @pytest.mark.skipif(
        config["desktopVersion"] < "2022.2",
        reason="Not working in non-graphical in version lower than 2022.2",
    )
    def test_51a_array(self):
        self.aedtapp.insert_design("Array_simple", "Modal")
        from ansys.aedt.core.generic.general_methods import read_json

        if config["desktopVersion"] > "2023.1":
            dict_in = read_json(
                os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, "array_simple_232.json")
            )
            dict_in["Circ_Patch_5GHz_232_1"] = os.path.join(
                TESTS_GENERAL_PATH, "example_models", test_subfolder, component
            )
            dict_in["cells"][(3, 3)] = {"name": "Circ_Patch_5GHz_232_1"}
        else:
            dict_in = read_json(os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, "array_simple.json"))
            dict_in["Circ_Patch_5GHz1"] = os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, component)
            dict_in["cells"][(3, 3)] = {"name": "Circ_Patch_5GHz1"}

        assert self.aedtapp.add_3d_component_array_from_json(dict_in)
        array_name = self.aedtapp.component_array_names[0]
        assert self.aedtapp.component_array[array_name].cells[2][2].rotation == 0
        assert self.aedtapp.component_array_names
        dict_in["cells"][(3, 3)]["rotation"] = 90
        component_array = self.aedtapp.add_3d_component_array_from_json(dict_in)
        assert component_array.cells[2][2].rotation == 90
        component_array.cells[2][2].rotation = 0
        assert component_array.cells[2][2].rotation == 0

    def test_51b_set_material_threshold(self):
        assert self.aedtapp.set_material_threshold()
        threshold = 123123123
        assert self.aedtapp.set_material_threshold(threshold)
        assert self.aedtapp.set_material_threshold(str(threshold))
        with pytest.raises(AEDTRuntimeError, match="Material conductivity threshold could not be set."):
            self.aedtapp.set_material_threshold("e")

    def test_52_crate_setup_hybrid_sbr(self, add_app):
        aedtapp = add_app(project_name="test_52")
        udp = aedtapp.modeler.Position(0, 0, 0)
        coax_dimension = 200
        aedtapp.modeler.create_cylinder(aedtapp.AXIS.X, udp, 3, coax_dimension, 0, "inner")
        aedtapp.modeler.create_cylinder(aedtapp.AXIS.X, udp, 10, coax_dimension, 0, "outer")
        aedtapp.hybrid = True
        assert aedtapp.assign_hybrid_region(["inner"])
        bound = aedtapp.assign_hybrid_region("outer", name="new_hybrid", hybrid_region="IE")
        assert bound.props["Type"] == "IE"
        bound.props["Type"] = "PO"
        assert bound.props["Type"] == "PO"
        aedtapp.close_project(save=False)

    def test_53_import_source_excitation(self, add_app):
        aedtapp = add_app(solution_type="Modal", project_name="test_53")
        freq_domain = os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, "S Parameter Table 1.csv")
        time_domain = os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, "Sinusoidal.csv")

        box1 = aedtapp.modeler.create_box([0, 0, 0], [10, 20, 20])
        aedtapp.wave_port(assignment=box1.bottom_face_x, create_port_sheet=False, name="Port1")
        aedtapp.create_setup()
        assert aedtapp.edit_source_from_file(
            assignment=aedtapp.excitations[0], input_file=freq_domain, is_time_domain=False, x_scale=1e9
        )
        assert aedtapp.edit_source_from_file(
            assignment=aedtapp.excitations[0],
            input_file=time_domain,
            is_time_domain=True,
            x_scale=1e-6,
            y_scale=1e-3,
            data_format="Voltage",
        )
        aedtapp.close_project(save=False)

    def test_54_assign_symmetry(self, add_app):
        aedtapp = add_app(project_name="test_54", solution_type="Modal")
        aedtapp.modeler.create_box([0, -100, 0], [200, 200, 200], name="SymmetryForFaces")
        ids = [i.id for i in aedtapp.modeler["SymmetryForFaces"].faces]
        assert aedtapp.assign_symmetry(ids)
        assert aedtapp.assign_symmetry([ids[0], ids[1], ids[2]])
        with pytest.raises(TypeError, match="Entities have to be provided as a list."):
            aedtapp.assign_symmetry(aedtapp.modeler.object_list[0].faces[0])
        assert aedtapp.assign_symmetry([aedtapp.modeler.object_list[0].faces[0]])
        assert aedtapp.assign_symmetry(
            [
                aedtapp.modeler.object_list[0].faces[0],
                aedtapp.modeler.object_list[0].faces[1],
                aedtapp.modeler.object_list[0].faces[2],
            ]
        )
        with pytest.raises(TypeError, match="Entities have to be provided as a list."):
            aedtapp.assign_symmetry(ids[0])
        with pytest.raises(TypeError, match="Entities have to be provided as a list."):
            aedtapp.assign_symmetry("test")
        assert aedtapp.set_impedance_multiplier(2)
        aedtapp.close_project(save=False)

    def test_55_create_near_field_sphere(self):
        air = self.aedtapp.modeler.create_box([0, 0, 0], [20, 20, 20], name="rad", material="vacuum")
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
            assignment=line.name, points=1000, custom_radiation_faces=None, name=None
        )
        bound.props["NumPts"] = "200"
        assert bound

    def test_59_test_nastran(self):
        self.aedtapp.insert_design("Nas_teest")
        example_project = os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, "test_cad.nas")
        example_project2 = os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, "test_cad_2.nas")

        cads, _ = self.aedtapp.modeler.import_nastran(example_project, lines_thickness=0.1)
        assert len(cads) > 0
        stl, _ = self.aedtapp.modeler.import_nastran(example_project, decimation=0.3, preview=True, save_only_stl=True)
        assert os.path.exists(stl[0])
        assert self.aedtapp.modeler.import_nastran(example_project2, decimation=0.1, preview=True, save_only_stl=True)
        assert self.aedtapp.modeler.import_nastran(example_project2, decimation=0.5)
        example_project = os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, "sphere.stl")
        from ansys.aedt.core.visualization.advanced.misc import simplify_stl

        out = simplify_stl(example_project, decimation=0.8)
        assert os.path.exists(out)
        out = simplify_stl(example_project, decimation=0.8, preview=True)
        assert out

    def test_60_set_variable(self):
        self.aedtapp.variable_manager.set_variable("var_test", expression="123")
        self.aedtapp["var_test"] = "234"
        assert "var_test" in self.aedtapp.variable_manager.design_variable_names
        assert self.aedtapp.variable_manager.design_variables["var_test"].expression == "234"

    def test_61_create_lumped_ports_on_object_driven_terminal(self):
        self.aedtapp.insert_design("test_61")
        self.aedtapp.solution_type = "Terminal"
        box1 = self.aedtapp.modeler.create_box([0, 0, 50], [10, 10, 5], "BoxLumped1")
        box1.material_name = "Copper"
        box2 = self.aedtapp.modeler.create_box([0, 0, 60], [10, 10, 5], "BoxLumped2")
        box2.material_name = "Copper"

        _ = self.aedtapp.lumped_port(
            assignment=box1.name,
            reference=box2.name,
            create_port_sheet=True,
            port_on_plane=True,
            integration_line=self.aedtapp.AxisDir.XNeg,
            impedance=50,
            name="Lump1xx",
            renormalize=True,
            deembed=False,
        )

        term = [term for term in self.aedtapp.boundaries if term.type == "Terminal"][0]
        assert term.type == "Terminal"
        term.name = "test"
        assert term.name == "test"
        term.props["TerminalResistance"] = "1ohm"
        assert term.props["TerminalResistance"] == "1ohm"
        with pytest.raises(AEDTRuntimeError, match="Symmetry is only available with 'Modal' solution type."):
            self.aedtapp.set_impedance_multiplier(2)

    def test_62_set_power_calc(self):
        assert self.aedtapp.set_radiated_power_calc_method()
        assert self.aedtapp.set_radiated_power_calc_method("Radiation Surface Integral")
        assert self.aedtapp.set_radiated_power_calc_method("Far Field Integral")

    def test_63_set_phase_center_per_port(self):
        self.aedtapp.insert_design("PhaseCenter")
        self.aedtapp.solution_type = "Modal"
        box1 = self.aedtapp.modeler.create_box([0, 0, 0], [10, 10, 5], "BoxWG1", "Copper")
        box2 = self.aedtapp.modeler.create_box([0, 0, 10], [10, 10, 5], "BoxWG2", "copper")
        box2.material_name = "Copper"
        port = self.aedtapp.wave_port(
            assignment="BoxWG1",
            reference="BoxWG2",
            create_port_sheet=True,
            integration_line=self.aedtapp.AxisDir.XNeg,
            modes=1,
            impedance=50,
            name="Wave1",
            renormalize=False,
        )
        port2 = self.aedtapp.wave_port(
            assignment="BoxWG1",
            reference="BoxWG2",
            create_port_sheet=True,
            integration_line=self.aedtapp.AxisDir.XNeg,
            modes=1,
            impedance=50,
            name="Wave2",
            renormalize=False,
        )
        if self.aedtapp.desktop_class.is_grpc_api:
            assert self.aedtapp.set_phase_center_per_port()
            assert self.aedtapp.set_phase_center_per_port(["Global", "Global"])
        else:
            assert not self.aedtapp.set_phase_center_per_port()
            assert not self.aedtapp.set_phase_center_per_port(["Global", "Global"])

        assert not self.aedtapp.set_phase_center_per_port(["Global"])
        assert not self.aedtapp.set_phase_center_per_port("Global")

    @pytest.mark.skipif(
        config["NonGraphical"] and config["desktopVersion"] < "2024.2",
        reason="Not working in non graphical before version 2024.2",
    )
    @pytest.mark.parametrize(
        ("dxf_file", "object_count", "self_stitch_tolerance"),
        (
            (os.path.join(TESTS_GENERAL_PATH, "example_models", "cad", "DXF", "dxf2.dxf"), 1, 0.0),
            (os.path.join(TESTS_GENERAL_PATH, "example_models", "cad", "DXF", "dxf_r12.dxf"), 4, -1),
        ),
    )
    def test_64_import_dxf(self, dxf_file: str, object_count: int, self_stitch_tolerance: float):
        from pyedb.generic.general_methods import generate_unique_name

        design_name = self.aedtapp.insert_design(generate_unique_name("test_64_import_dxf"))
        self.aedtapp.set_active_design(design_name)
        dxf_layers = self.aedtapp.get_dxf_layers(dxf_file)
        assert isinstance(dxf_layers, list)
        assert self.aedtapp.import_dxf(dxf_file, dxf_layers, self_stitch_tolerance=self_stitch_tolerance)
        assert len(self.aedtapp.modeler.objects) == object_count

    def test_65_component_array(self, add_app):
        hfss_array = add_app(project_name=component_array, subfolder=test_subfolder)
        assert len(hfss_array.component_array) == 1

        array = hfss_array.component_array["A1"]
        assert array.name == hfss_array.component_array_names[0]

        cell1 = array.get_cell(1, 1)
        cell2 = array[1, 1]
        assert cell2
        assert cell1.rotation == 0

        assert not array.get_cell(0, 0)
        assert not array.get_cell(10, 0)

        lc = array.lattice_vector()
        assert len(lc) == 6

        assert len(array.component_names) == 4

        assert len(array.post_processing_cells) == 4
        post_cells = array.post_processing_cells
        post_cells["Radome_Corner1"] = [8, 1]
        array.post_processing_cells = post_cells
        assert array.post_processing_cells["Radome_Corner1"] == [8, 1]

        array.cells[0][1].component = None
        assert not array.cells[0][1].component

        array.cells[1][1].rotation = 90
        assert array.cells[1][1].rotation == 90

        array.cells[1][1].rotation = 10
        assert not array.cells[1][1].rotation == 10

        array.cells[1][1].is_active = False
        array.cells[1][1].is_active = 1
        assert not array.cells[1][1].is_active

        assert array.cells[1][2].component == array.component_names[2]
        assert not array.cells[1][2].component == "test"

        array.cells[0][1].component = array.component_names[3]
        assert array.cells[0][1].component == array.component_names[3]

        name = "Array_new"
        hfss_array.component_array["A1"].name = name
        assert hfss_array.component_array_names[0] == name

        if config["desktopVersion"] < "2025.1":
            name = "A1"
            hfss_array.component_array["Array_new"].name = name
        omodel = hfss_array.get_oo_object(hfss_array.odesign, "Model")
        oarray = hfss_array.get_oo_object(omodel, name)

        assert array.visible
        array.visible = False
        assert not oarray.GetPropValue("Visible")
        array.visible = True
        assert oarray.GetPropValue("Visible")

        assert array.show_cell_number
        array.show_cell_number = False
        assert not oarray.GetPropValue("Show Cell Number")
        array.show_cell_number = True
        assert oarray.GetPropValue("Show Cell Number")

        assert array.render == "Shaded"
        array.render = "Wireframe"
        assert oarray.GetPropValue("Render") == "Wireframe"
        array.render = "Shaded"
        assert oarray.GetPropValue("Render") == "Shaded"
        array.render = "Shaded1"
        assert not array.render == "Shaded1"

        a_choices = array.a_vector_choices
        assert array.a_vector_name in a_choices
        array.a_vector_name = a_choices[0]
        assert oarray.GetPropValue("A Vector") == a_choices[0]
        array.a_vector_name = "Test"
        assert not array.a_vector_name == "Test"

        b_choices = array.b_vector_choices
        assert array.b_vector_name in b_choices
        array.b_vector_name = b_choices[1]
        assert oarray.GetPropValue("B Vector") == b_choices[1]
        array.b_vector_name = "Test"
        assert not array.b_vector_name == "Test"

        assert array.a_size == 8

        assert array.b_size == 8

        assert array.a_length == 0.64

        assert array.b_length == 0.64

        assert len(array.lattice_vector()) == 6

        assert array.padding_cells == 0
        array.padding_cells = 2
        assert oarray.GetPropValue("Padding") == "2"
        array.padding_cells = 0

        assert array.coordinate_system == "Global"
        array.coordinate_system = "Corner"
        array.coordinate_system = "Global"

        array_csv = os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, "array_info.csv")
        array_info = array.parse_array_info_from_csv(array_csv)
        assert len(array_info) == 4
        assert array_info["component"][1] == "02_Patch1"

        assert len(array.get_component_objects()) == 4

        assert len(array.get_cell_position()) == array.a_size

        # Delete 3D Component
        hfss_array.modeler.user_defined_components["03_Radome_Side1"].delete()
        array.update_properties()
        assert len(array.component_names) == 3
        assert len(array.post_processing_cells) == 3

        array.delete()
        assert not hfss_array.component_array

    def test_66_assign_febi(self, add_app):
        aedtapp = add_app(project_name="test_66")
        udp = aedtapp.modeler.Position(0, 0, 0)
        coax_dimension = 200
        aedtapp.modeler.create_cylinder(aedtapp.AXIS.X, udp, 3, coax_dimension, 0, "inner")
        aedtapp.modeler.create_cylinder(aedtapp.AXIS.X, udp, 10, coax_dimension, 0, "outer")
        aedtapp.hybrid = True
        assert aedtapp.assign_febi(["inner"])
        assert len(aedtapp.boundaries) == 1
        aedtapp.close_project(save=False)

    def test_67_transient_composite(self, add_app):
        aedtapp = add_app(project_name="test_66")
        aedtapp.solution_type = "Transient Composite"
        assert aedtapp.solution_type == "Transient Composite"
        aedtapp.close_project(save=False)

    def test_68_import_gds_3d(self):
        self.aedtapp.insert_design("gds_import_H3D")
        gds_file = os.path.join(TESTS_GENERAL_PATH, "example_models", "cad", "GDS", "gds1.gds")
        assert self.aedtapp.import_gds_3d(gds_file, {7: (100, 10), 9: (110, 5)})
        assert len(self.aedtapp.modeler.solid_names) == 3
        assert len(self.aedtapp.modeler.sheet_names) == 0
        assert self.aedtapp.import_gds_3d(gds_file, {7: (0, 0), 9: (0, 0)})
        assert len(self.aedtapp.modeler.sheet_names) == 3
        assert self.aedtapp.import_gds_3d(gds_file, {7: (100e-3, 10e-3), 9: (110e-3, 5e-3)}, "mm", 0)
        assert len(self.aedtapp.modeler.solid_names) == 6
        assert not self.aedtapp.import_gds_3d(gds_file, {})
        gds_file = os.path.join(TESTS_GENERAL_PATH, "example_models", "cad", "GDS", "gds1not.gds")
        assert not self.aedtapp.import_gds_3d(gds_file, {7: (100, 10), 9: (110, 5)})

    def test_69_plane_wave(self, add_app):
        aedtapp = add_app(project_name="test_69")
        with pytest.raises(
            ValueError, match="Invalid value for `vector_format`. The value must be 'Spherical', or 'Cartesian'."
        ):
            aedtapp.plane_wave(vector_format="invented")
        with pytest.raises(ValueError, match="Invalid value for `origin`."):
            aedtapp.plane_wave(origin=[0, 0])
        with pytest.raises(
            ValueError,
            match=re.escape(
                "Invalid value for `wave_type`." " The value must be 'Propagating', Evanescent, or 'Elliptical'."
            ),
        ):
            aedtapp.plane_wave(wave_type="dummy")
        with pytest.raises(ValueError, match=re.escape("Invalid value for `wave_type_properties`.")):
            aedtapp.plane_wave(wave_type="evanescent", wave_type_properties=[1])
        with pytest.raises(ValueError, match=re.escape("Invalid value for `wave_type_properties`.")):
            aedtapp.plane_wave(wave_type="elliptical", wave_type_properties=[1])
        with pytest.raises(ValueError, match=re.escape("Invalid value for `polarization`.")):
            aedtapp.plane_wave(vector_format="Cartesian", polarization=[1, 0])
        with pytest.raises(ValueError, match=re.escape("Invalid value for `propagation_vector`.")):
            aedtapp.plane_wave(vector_format="Cartesian", propagation_vector=[1, 0])
        with pytest.raises(ValueError, match=re.escape("Invalid value for `polarization`.")):
            aedtapp.plane_wave(polarization=[1])
        with pytest.raises(ValueError, match=re.escape("Invalid value for `propagation_vector`.")):
            aedtapp.plane_wave(propagation_vector=[1, 0, 0])

        assert aedtapp.plane_wave(wave_type="Evanescent")
        assert aedtapp.plane_wave(wave_type="Elliptical")
        assert aedtapp.plane_wave()
        assert aedtapp.plane_wave(vector_format="Cartesian")
        assert aedtapp.plane_wave()
        assert aedtapp.plane_wave(polarization="Horizontal")
        assert aedtapp.plane_wave(vector_format="Cartesian", polarization="Horizontal")

        assert aedtapp.plane_wave(polarization=[1, 0])
        assert aedtapp.plane_wave(vector_format="Cartesian", polarization=[1, 0, 0])

        aedtapp.solution_type = "SBR+"
        new_plane_wave = aedtapp.plane_wave()
        assert len(aedtapp.boundaries) == 10
        new_plane_wave.name = "new_plane_wave"
        assert new_plane_wave.name in aedtapp.excitations

        aedtapp.close_project(save=False)

    def test_70_export_on_completion(self, add_app, local_scratch):
        aedtapp = add_app(project_name="test_70")
        assert aedtapp.export_touchstone_on_completion()
        assert aedtapp.export_touchstone_on_completion(export=True, output_dir=self.local_scratch.path)
        assert aedtapp.export_touchstone_on_completion()

    def test_71_import_source_excitation(self, add_app):
        aedtapp = add_app(solution_type="Eigenmode", project_name="test_71")
        _ = aedtapp.modeler.create_box([0, 0, 0], [10, 20, 20])
        setup = aedtapp.create_setup()
        setup.props["NumModes"] = 2
        sources = {"1": "10", "2": "0"}
        assert aedtapp.edit_sources(sources, eigenmode_stored_energy=True)
        sources = {"1": ("0", "0deg"), "2": ("2", "90deg")}
        assert aedtapp.edit_sources(sources, eigenmode_stored_energy=False)
        sources = {"1": "20", "2": "0"}
        assert aedtapp.edit_sources(sources, eigenmode_stored_energy=False)
        input_file = os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, "source_eigen.csv")
        assert aedtapp.edit_source_from_file(input_file=input_file)
        aedtapp.close_project(save=False)

    def test_72_import_table(self, add_app):
        file_header = os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, "table_header.csv")
        file_no_header = os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, "table_no_header.csv")
        file_invented = "invented.csv"
        file_format = os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, "sphere.stl")

        aedtapp = add_app(solution_type="Terminal", project_name="test_72")
        assert not aedtapp.table_names
        aedtapp.create_setup()
        assert not aedtapp.table_names

        with pytest.raises(FileNotFoundError, match="File does not exist."):
            aedtapp.import_table(input_file=file_invented, name="Table1")
        with pytest.raises(ValueError, match=re.escape("Invalid file extension. It must be ``.csv``.")):
            aedtapp.import_table(input_file=file_format, name="Table1")

        assert aedtapp.import_table(input_file=file_header, name="Table1")
        assert "Table1" in aedtapp.table_names
        with pytest.raises(AEDTRuntimeError, match="Table name already assigned."):
            aedtapp.import_table(input_file=file_header, name="Table1")

        assert aedtapp.import_table(input_file=file_no_header, name="Table2")
        assert "Table2" in aedtapp.table_names

        assert aedtapp.import_table(
            input_file=file_no_header,
            name="Table3",
            is_real_imag=False,
            is_field=True,
            column_names=["col1_test", "col2_test"],
            independent_columns=[True, False],
        )
        assert "Table3" in aedtapp.table_names

        assert aedtapp.delete_table("Table2")
        assert "Table2" not in aedtapp.table_names

        assert aedtapp.import_table(input_file=file_no_header, name="Table2")
        assert "Table2" in aedtapp.table_names

    def test_73_plane_wave(self, add_app):
        aedtapp = add_app(project_name="test_73")
        with pytest.raises(ValueError, match=re.escape("Invalid value for `origin`.")):
            aedtapp.hertzian_dipole_wave(origin=[0, 0])
        with pytest.raises(ValueError, match=re.escape("Invalid value for `polarization`.")):
            aedtapp.hertzian_dipole_wave(polarization=[1])

        sphere = aedtapp.modeler.create_sphere([0, 0, 0], 10)
        sphere2 = aedtapp.modeler.create_sphere([10, 100, 0], 10)

        assignment = [sphere, sphere2.faces[0].id]

        exc = aedtapp.hertzian_dipole_wave(assignment=assignment, is_electric=True)
        assert len(aedtapp.excitations) == 1
        assert exc.properties["Electric Dipole"]
        exc.props["IsElectricDipole"] = False
        assert not exc.properties["Electric Dipole"]

        exc2 = aedtapp.hertzian_dipole_wave(polarization=[1, 0, 0], name="dipole", radius=20)
        assert len(aedtapp.excitations) == 2
        assert exc2.name == "dipole"
        aedtapp.close_project(save=False)

    def test_74_wave_port_integration_line(self, add_app):
        aedtapp = add_app(project_name="test_74", solution_type="Modal")
        c = aedtapp.modeler.create_circle("XY", [-1.4, -1.6, 0], 1, name="wave_port")
        start = [["-1.4mm", "-1.6mm", "0mm"], ["-1.4mm", "-1.6mm", "0mm"]]
        end = [["-1.4mm", "-0.6mm", "0mm"], ["-1.4mm", "-2.6mm", "0mm"]]

        with pytest.raises(ValueError, match=re.escape("List of characteristic impedance is not set correctly.")):
            aedtapp.wave_port(c.name, integration_line=[start, end], characteristic_impedance=["Zwave"], modes=2)

        assert aedtapp.wave_port(
            c.name, integration_line=[start, end], characteristic_impedance=["Zwave", "Zpv"], modes=2
        )

        assert aedtapp.wave_port(c.name, integration_line=[start, end], modes=2)

        start = [["-1.4mm", "-1.6mm", "0mm"], None, ["-1.4mm", "-1.6mm", "0mm"]]
        end = [["-1.4mm", "-0.6mm", "0mm"], None, ["-1.4mm", "-2.6mm", "0mm"]]

        assert aedtapp.wave_port(c.name, integration_line=[start, end], modes=3)

        aedtapp.close_project(save=False)
