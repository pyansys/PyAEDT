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
import time

from ansys.aedt.core import Circuit
from ansys.aedt.core.generic.settings import is_linux
import pytest

from tests import TESTS_GENERAL_PATH
from tests.system.general.conftest import config

test_subfolder = "T21"

if config["desktopVersion"] > "2022.2":
    diff_proj_name = "differential_pairs_231"
else:
    diff_proj_name = "differential_pairs"
netlist1 = "netlist_small.cir"
netlist2 = "Schematic1.qcv"
touchstone = "SSN_1.5_ssn.s6p"
touchstone_custom = "SSN_custom.s6p"
touchstone2 = "V3P3S0.ts"
ami_project = "AMI_Example"


@pytest.fixture(scope="class")
def aedtapp(add_app):
    app = add_app(application=Circuit, subfolder=test_subfolder)
    app.modeler.schematic_units = "mil"
    return app


@pytest.fixture(scope="class")
def circuitprj(add_app):
    app = add_app(diff_proj_name, application=Circuit, subfolder=test_subfolder)
    return app


@pytest.fixture(scope="class", autouse=True)
def examples(local_scratch):
    netlist_file1 = os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, netlist1)
    netlist_file2 = os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, netlist2)
    touchstone_file = os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, touchstone)
    touchstone_file2 = os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, touchstone2)
    netlist_file1 = local_scratch.copyfile(netlist_file1)
    netlist_file2 = local_scratch.copyfile(netlist_file2)
    touchstone_file = local_scratch.copyfile(touchstone_file)
    touchstone_file2 = local_scratch.copyfile(touchstone_file2)
    return netlist_file1, netlist_file2, touchstone_file, touchstone_file2


class TestClass:
    @pytest.fixture(autouse=True)
    def init(self, aedtapp, circuitprj, local_scratch, examples):
        self.aedtapp = aedtapp
        self.circuitprj = circuitprj
        self.local_scratch = local_scratch
        self.netlist_file1 = examples[0]
        self.netlist_file2 = examples[1]
        self.touchstone_file = examples[2]
        self.touchstone_file2 = examples[3]

    def test_01a_create_inductor(self):
        myind = self.aedtapp.modeler.schematic.create_inductor(value=1e-9, location=[1000, 1000])
        assert type(myind.id) is int
        assert myind.parameters["L"] == "1e-09"

    def test_02_create_resistor(self):
        myres = self.aedtapp.modeler.schematic.create_resistor(value=50, location=[2000, 1000])
        assert myres.refdes != ""
        assert type(myres.id) is int
        assert myres.parameters["R"] == "50"

    def test_03_create_capacitor(self):
        mycap = self.aedtapp.modeler.schematic.create_capacitor(value=1e-12, location=[1000, 2000])
        assert type(mycap.id) is int
        assert mycap.parameters["C"] == "1e-12"
        tol = 1e-12
        assert abs(mycap.pins[0].location[1] - 2000) < tol
        assert abs(mycap.pins[0].location[0] - 800) < tol

    def test_04_getpin_names(self):
        mycap2 = self.aedtapp.modeler.schematic.create_capacitor(value=1e-12)
        pinnames = self.aedtapp.modeler.schematic.get_pins(mycap2)
        pinnames2 = self.aedtapp.modeler.schematic.get_pins(mycap2.id)
        pinnames3 = self.aedtapp.modeler.schematic.get_pins(mycap2.composed_name)
        assert pinnames2 == pinnames3
        assert type(pinnames) is list
        assert len(pinnames) == 2

    def test_05a_getpin_location(self):
        for el in self.aedtapp.modeler.schematic.components:
            pinnames = self.aedtapp.modeler.schematic.get_pins(el)
            for pinname in pinnames:
                pinlocation = self.aedtapp.modeler.schematic.get_pin_location(el, pinname)
                assert len(pinlocation) == 2

    def test_05b_add_pin_iport(self):
        mycap3 = self.aedtapp.modeler.schematic.create_capacitor(value=1e-12)
        assert self.aedtapp.modeler.schematic.add_pin_iports(mycap3.name, mycap3.id)
        assert len(self.aedtapp.get_all_sparameter_list) == 3
        assert len(self.aedtapp.get_all_return_loss_list()) == 2
        assert len(self.aedtapp.get_all_return_loss_list(math_formula="abs")) == 2
        assert len(self.aedtapp.get_all_insertion_loss_list()) == 2
        assert len(self.aedtapp.get_all_insertion_loss_list(math_formula="abs")) == 2
        assert len(self.aedtapp.get_all_insertion_loss_list(math_formula="abs", nets=self.aedtapp.excitations)) == 2
        assert len(self.aedtapp.get_next_xtalk_list()) == 1
        assert len(self.aedtapp.get_next_xtalk_list(math_formula="abs")) == 1
        assert len(self.aedtapp.get_fext_xtalk_list()) == 2
        assert len(self.aedtapp.get_fext_xtalk_list(math_formula="abs")) == 2

    def test_05c_create_component(self):
        assert self.aedtapp.modeler.schematic.create_new_component_from_symbol("Test", ["1", "2"])
        assert self.aedtapp.modeler.schematic.create_new_component_from_symbol(
            "Test1", [1, 2], parameters=["Author:=", "NumTerminals:="], values=["pyaedt", 2]
        )

    def test_06a_create_setup(self):
        setup_name = "LNA"
        LNA_setup = self.aedtapp.create_setup(setup_name)
        assert LNA_setup.name == "LNA"

    def test_08_import_mentor_netlist(self):
        self.aedtapp.insert_design("MentorSchematicImport")
        assert self.aedtapp.create_schematic_from_mentor_netlist(self.netlist_file2)

    def test_09_import_netlist(self):
        self.aedtapp.insert_design("SchematicImport")
        self.aedtapp.modeler.schematic.limits_mils = 5000
        assert self.aedtapp.create_schematic_from_netlist(self.netlist_file1)

    def test_10_import_touchstone(self):
        self.aedtapp.insert_design("Touchstone_import")
        self.aedtapp.modeler.schematic_units = "mils"
        ports = self.aedtapp.import_touchstone_solution(self.touchstone_file)
        ports2 = self.aedtapp.import_touchstone_solution(self.touchstone_file2)
        numports = len(ports)
        assert numports == 6
        numports2 = len(ports2)
        assert numports2 == 3
        tx = ports[: int(numports / 2)]
        rx = ports[int(numports / 2) :]
        insertions = [f"dB(S({i},{j}))" for i, j in zip(tx, rx)]
        assert self.aedtapp.create_touchstone_report("Insertion Losses", insertions)
        touchstone_data = self.aedtapp.get_touchstone_data()
        assert touchstone_data

    def test_11_export_fullwave(self):
        output = self.aedtapp.export_fullwave_spice(self.touchstone_file, is_solution_file=True)
        assert output

    def test_12_connect_components(self):
        myind = self.aedtapp.modeler.schematic.create_inductor("L100", 1e-9)
        myind2 = self.aedtapp.modeler.schematic.create_inductor("L1001", 1e-9)
        myind3 = self.aedtapp.modeler.schematic.create_inductor("L1002", 1e-9)
        myres = self.aedtapp.modeler.schematic.create_resistor("R100", 50)
        mycap = self.aedtapp.modeler.schematic.create_capacitor("C100", 1e-12)
        portname = self.aedtapp.modeler.schematic.create_interface_port("Port1")
        assert len(self.aedtapp.excitations) > 0
        assert "Port1" in portname.name
        assert myind.pins[0].connect_to_component(portname.pins[0])
        assert myind.pins[1].connect_to_component(myres.pins[1], use_wire=True)
        assert self.aedtapp.modeler.connect_schematic_components(myres.id, mycap.id, pin_starting=1)
        assert self.aedtapp.modeler.connect_schematic_components(
            myind2, myind3, pin_starting=["n1", "n2"], pin_ending=["n2", "n1"], use_wire=False
        )
        gnd = self.aedtapp.modeler.schematic.create_gnd()
        assert mycap.pins[1].connect_to_component(gnd.pins[0])
        # create_interface_port
        L1_pins = myind.pins
        L1_pin2location = {}
        for pin in L1_pins:
            L1_pin2location[pin.name] = pin.location

    def test_12a_connect_components(self):
        myind = self.aedtapp.modeler.schematic.create_inductor("L101", 1e-9)
        myres = self.aedtapp.modeler.schematic.create_resistor("R101", 50)
        self.aedtapp.modeler.schematic.create_interface_port("Port2")
        assert "Port2" in self.aedtapp.modeler.schematic.nets
        assert myind.pins[1].connect_to_component(myres.pins[1], "port_name_test")
        assert "port_name_test" in self.aedtapp.modeler.schematic.nets

    def test_13_properties(self):
        assert self.aedtapp.modeler.model_units

    def test_14_move(self):
        self.aedtapp.modeler.schematic_units = "mil"
        myind = self.aedtapp.modeler.schematic.create_inductor("L14", 1e-9, [400, 400])
        self.aedtapp.modeler.schematic_units = "meter"
        assert self.aedtapp.modeler.move("L14", [0, -0.00508])
        assert myind.location == [0.01016, 0.00508]
        self.aedtapp.modeler.schematic_units = "mil"
        assert self.aedtapp.modeler.move("L14", [0, 200])
        assert myind.location == [400.0, 400.0]

    def test_15_rotate(self):
        assert self.aedtapp.modeler.rotate(
            "IPort@Port1",
        )

    def test_16_read_touchstone(self):
        from ansys.aedt.core.visualization.advanced.touchstone_parser import read_touchstone

        data = read_touchstone(self.touchstone_file)
        assert len(data.port_names) > 0

    def test_17_create_setup(self):
        setup_name = "Dom_LNA"
        LNA_setup = self.aedtapp.create_setup(setup_name)
        LNA_setup.SweepDefinition = [
            ("Variable", "Freq"),
            ("Data", "LIN 1GHz 5GHz 1001"),
            ("OffsetF1", False),
            ("Synchronize", 0),
        ]
        assert LNA_setup.update()

    def test_18_export_touchstone(self):
        assert self.aedtapp.analyze("Dom_LNA")
        time.sleep(2)
        solution_name = "Dom_LNA"
        sweep_name = None
        file_name = os.path.join(self.local_scratch.path, "new.s2p")
        assert self.aedtapp.export_touchstone(solution_name, sweep_name, file_name)
        assert os.path.exists(file_name)
        assert self.aedtapp.existing_analysis_sweeps[0] == solution_name
        assert self.aedtapp.setup_names[0] == solution_name
        assert self.aedtapp.export_touchstone(solution_name, sweep_name)

    def test_19a_create_sweeps(self):
        setup_name = "Sweep_LNA"
        LNA_setup = self.aedtapp.create_setup(setup_name)
        LNA_setup.add_sweep_step("Freq", 1, 2, 0.01, "GHz", override_existing_sweep=True)
        assert LNA_setup.props["SweepDefinition"]["Data"] == "LIN 1GHz 2GHz 0.01GHz"
        LNA_setup.add_sweep_points("Freq", [11, 12, 13.4], "GHz", override_existing_sweep=False)
        assert "13.4GHz" in LNA_setup.props["SweepDefinition"]["Data"]
        assert "LIN 1GHz 2GHz 0.01GHz" in LNA_setup.props["SweepDefinition"]["Data"]
        LNA_setup.add_sweep_count("Temp", 20, 100, 81, "cel", count_type="Decade", override_existing_sweep=True)
        assert isinstance(LNA_setup.props["SweepDefinition"], list)
        assert LNA_setup.props["SweepDefinition"][1]["Variable"] == "Temp"
        assert LNA_setup.props["SweepDefinition"][1]["Data"] == "DEC 20cel 100cel 81"

    def test_19b_create_eye_setups(self):
        setup_name = "Dom_Verify"
        assert self.aedtapp.create_setup(setup_name, "NexximVerifEye")
        setup_name = "Dom_Quick"
        assert self.aedtapp.create_setup(setup_name, "NexximQuickEye")
        setup_name = "Dom_AMI"
        assert self.aedtapp.create_setup(setup_name, "NexximAMI")

    @pytest.mark.skipif(
        is_linux and config["desktopVersion"] == "2024.1",
        reason="Project with multiple circuit designs is not working.",
    )
    def test_20a_create_ami_plots(self, add_app):
        ami_design = add_app(ami_project, design_name="Models Init Only", application=Circuit, subfolder=test_subfolder)

        report_name = "MyReport"
        assert (
            ami_design.post.create_ami_initial_response_plot(
                "AMIAnalysis",
                "b_input_15",
                ami_design.available_variations.nominal,
                plot_type="Rectangular Stacked Plot",
                plot_intermediate_response=True,
                plot_final_response=True,
                plot_name=report_name,
            )
            == report_name
        )
        setup_name = "Dom_Verify"
        assert ami_design.create_setup(setup_name, "NexximVerifEye")
        setup_name = "Dom_Quick"
        assert ami_design.create_setup(setup_name, "NexximQuickEye")
        assert (
            ami_design.post.create_ami_statistical_eye_plot(
                "AMIAnalysis", "b_output4_14", ami_design.available_variations.nominal, plot_name="MyReport1"
            )
            == "MyReport1"
        )
        assert (
            ami_design.post.create_statistical_eye_plot(
                "Dom_Quick",
                "b_input_15.int_ami_rx.eye_probe",
                ami_design.available_variations.nominal,
                plot_name="MyReportQ",
            )
            == "MyReportQ"
        )

    @pytest.mark.skipif(config["desktopVersion"] > "2021.2", reason="Skipped on versions higher than 2021.2")
    def test_20b_create_ami_plots(self):
        assert (
            self.aedtapp.post.create_statistical_eye_plot(
                "Dom_Verify",
                "b_input_15.int_ami_rx.eye_probe",
                self.aedtapp.available_variations.nominal,
                plot_name="MyReportV",
            )
            == "MyReportV"
        )

    def test_21_assign_voltage_sinusoidal_excitation_to_ports(self):
        ports_list = ["Port1", "Port2"]
        assert self.aedtapp.assign_voltage_sinusoidal_excitation_to_ports(ports_list)

    def test_22_assign_current_sinusoidal_excitation_to_ports(self):
        ports_list = ["Port1"]
        assert self.aedtapp.assign_current_sinusoidal_excitation_to_ports(ports_list)

    def test_23_assign_power_sinusoidal_excitation_to_ports(self):
        ports_list = ["Port2"]
        assert self.aedtapp.assign_power_sinusoidal_excitation_to_ports(ports_list)

    def test_24_new_connect_components(self):
        self.aedtapp.insert_design("Components")
        myind = self.aedtapp.modeler.schematic.create_inductor("L100", 1e-9)
        myres = self.aedtapp.modeler.components.create_resistor("R100", 50)
        mycap = self.aedtapp.modeler.components.create_capacitor("C100", 1e-12)
        myind2 = self.aedtapp.modeler.components.create_inductor("L101", 1e-9)
        port = self.aedtapp.modeler.components.create_interface_port("Port1")
        assert not myind2.model_name
        assert not myind2.model_data
        assert self.aedtapp.modeler.schematic.connect_components_in_series([myind, myres.composed_name])
        assert self.aedtapp.modeler.schematic.connect_components_in_parallel([mycap, port, myind2.id])

    def test_25_import_model(self):
        self.aedtapp.insert_design("Touch_import")
        touch = os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, touchstone)
        t1 = self.aedtapp.modeler.schematic.create_touchstone_component(touch)
        assert t1
        assert len(t1.pins) == 6
        assert t1.model_data
        t1.model_data.props["NexximCustomization"]["Passivity"] = 7
        assert t1.model_data.update()
        t2 = self.aedtapp.modeler.schematic.create_touchstone_component(touch)
        assert t2
        t2.model_data.props["NexximCustomization"]["Passivity"] = 0
        assert t2.model_data.update()
        touch = os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, "y4bm_rdl_dq_byte0.s26p")
        t1 = self.aedtapp.modeler.schematic.create_touchstone_component(touch)
        assert t1
        assert len(t1.pins) == 26

    def test_25_zoom_to_fit(self):
        self.aedtapp.insert_design("zoom_test")
        myind = self.aedtapp.modeler.schematic.create_inductor("L100", 1e-9)
        myres = self.aedtapp.modeler.components.create_resistor("R100", 50)
        mycap = self.aedtapp.modeler.components.create_capacitor("C100", 1e-12)
        self.aedtapp.modeler.zoom_to_fit()

    def test_26_component_catalog(self):
        comp_catalog = self.aedtapp.modeler.components.components_catalog
        assert comp_catalog["Capacitors:Cap_"]
        assert comp_catalog["capacitors:cAp_"]
        assert isinstance(comp_catalog.find_components("cap"), list)
        assert comp_catalog["LISN:CISPR25_LISN"].place("Lisn1")
        assert not comp_catalog["Capacitors"]
        assert comp_catalog["LISN:CISPR25_LISN"].props

    def test_27_set_differential_pairs(self):
        assert self.circuitprj.set_differential_pair(
            assignment="Port3",
            reference="Port4",
            common_mode=None,
            differential_mode=None,
            common_reference=34,
            differential_reference=123,
        )
        assert self.circuitprj.set_differential_pair(assignment="Port3", reference="Port5")

    def test_28_load_and_save_diff_pair_file(self):
        diff_def_file = os.path.join(
            TESTS_GENERAL_PATH, "example_models", test_subfolder, "differential_pairs_definition.txt"
        )
        diff_file = self.local_scratch.copyfile(diff_def_file)
        assert self.circuitprj.load_diff_pairs_from_file(diff_file)

        diff_file2 = os.path.join(self.local_scratch.path, "diff_file2.txt")
        assert self.circuitprj.save_diff_pairs_to_file(diff_file2)
        with open(diff_file2, "r") as fh:
            lines = fh.read().splitlines()
        assert len(lines) == 3

    def test_29_create_circuit_from_spice(self):
        model = os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, "test.lib")
        assert self.aedtapp.modeler.schematic.create_component_from_spicemodel(model)
        assert self.aedtapp.modeler.schematic.create_component_from_spicemodel(model, "GRM2345", False)
        assert not self.aedtapp.modeler.schematic.create_component_from_spicemodel(model, "GRM2346")

    def test_29a_create_circuit_from_spice_edit_symbol(self):
        model = os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, "test.lib")
        assert self.aedtapp.modeler.schematic.create_component_from_spicemodel(
            input_file=model, model="GRM5678", symbol="nexx_cap"
        )
        assert self.aedtapp.modeler.schematic.create_component_from_spicemodel(
            input_file=model, model="GRM6789", symbol="nexx_inductor"
        )
        assert self.aedtapp.modeler.schematic.create_component_from_spicemodel(
            input_file=model, model="GRM9012", symbol="nexx_res"
        )

    def test_30_create_subcircuit(self):
        subcircuit = self.aedtapp.modeler.schematic.create_subcircuit(location=[0.0, 0.0], angle=0)
        assert type(subcircuit.location) is list
        assert type(subcircuit.id) is int
        assert subcircuit.component_info
        assert subcircuit.location[0] == 0.0
        assert subcircuit.location[1] == 0.0
        assert subcircuit.angle == 0.0

    @pytest.mark.skipif(
        config["NonGraphical"] and config["desktopVersion"] < "2023.1",
        reason="Duplicate doesn't work in non-graphical mode.",
    )
    def test_31_duplicate(self):  # pragma: no cover
        subcircuit = self.aedtapp.modeler.schematic.create_subcircuit(location=[0.0, 0.0])
        self.aedtapp.modeler.schematic_units = "meter"
        new_subcircuit = self.aedtapp.modeler.schematic.duplicate(
            subcircuit.composed_name, location=[0.0508, 0.0], angle=0
        )

        assert type(new_subcircuit.location) is list
        assert type(new_subcircuit.id) is int
        assert new_subcircuit.location[0] == 0.04826
        assert new_subcircuit.location[1] == -0.00254
        assert new_subcircuit.angle == 0.0

    def test_32_push_down(self):
        self.aedtapp.insert_design("Circuit_Design_Push_Down")
        subcircuit_1 = self.aedtapp.modeler.schematic.create_subcircuit(location=[0.0, 0.0])
        active_project = self.aedtapp.oproject.GetActiveDesign()
        if is_linux and config["desktopVersion"] == "2024.1":
            time.sleep(1)
            self.aedtapp.desktop_class.close_windows()
        active_project_name_1 = active_project.GetName()
        self.aedtapp.pop_up()
        subcircuit_2 = self.aedtapp.modeler.schematic.create_subcircuit(
            location=[0.0, 0.0], nested_subcircuit_id=subcircuit_1.component_info["RefDes"]
        )
        active_project = self.aedtapp.oproject.GetActiveDesign()
        if is_linux and config["desktopVersion"] == "2024.1":
            time.sleep(1)
            self.aedtapp.desktop_class.close_windows()
        active_project_name_3 = active_project.GetName()
        assert active_project_name_1 == active_project_name_3
        assert subcircuit_2.component_info["RefDes"] == "U2"
        assert self.aedtapp.push_down(subcircuit_1)

    def test_33_pop_up(self):
        self.aedtapp.insert_design("Circuit_Design_Pop_Up")
        assert self.aedtapp.pop_up()
        active_project = self.aedtapp.oproject.GetActiveDesign()
        if is_linux and config["desktopVersion"] == "2024.1":
            time.sleep(1)
            self.aedtapp.desktop_class.close_windows()
        active_project_name_1 = active_project.GetName()
        self.aedtapp.modeler.schematic.create_subcircuit(location=[0.0, 0.0])
        assert self.aedtapp.pop_up()
        active_project = self.aedtapp.oproject.GetActiveDesign()
        if is_linux and config["desktopVersion"] == "2024.1":
            time.sleep(1)
            self.aedtapp.desktop_class.close_windows()
        active_project_name_2 = active_project.GetName()
        assert active_project_name_1 == active_project_name_2

    def test_34_activate_variables(self):
        self.aedtapp["desvar"] = "1mm"
        self.aedtapp["$prjvar"] = "2mm"
        assert self.aedtapp["desvar"] == "1mm"
        assert self.aedtapp["$prjvar"] == "2mm"
        assert self.aedtapp.activate_variable_tuning("desvar")
        assert self.aedtapp.activate_variable_tuning("$prjvar")
        assert self.aedtapp.deactivate_variable_tuning("desvar")
        assert self.aedtapp.deactivate_variable_tuning("$prjvar")
        try:
            self.aedtapp.activate_variable_tuning("Idontexist")
            assert False
        except Exception:
            assert True

    def test_35_netlist_data_block(self):
        self.aedtapp.insert_design("data_block")
        with open(os.path.join(self.local_scratch.path, "lc.net"), "w") as f:
            for i in range(10):
                f.write(f"L{i} net_{i} net_{i+1} 1e-9\n")
                f.write(f"C{i} net_{i+1} 0 5e-12\n")
        assert self.aedtapp.add_netlist_datablock(os.path.join(self.local_scratch.path, "lc.net"))
        self.aedtapp.modeler.components.create_interface_port("net_0", (0, 0))
        self.aedtapp.modeler.components.create_interface_port("net_10", (0.01, 0))

        lna = self.aedtapp.create_setup("mylna", self.aedtapp.SETUPS.NexximLNA)
        lna.props["SweepDefinition"]["Data"] = "LINC 0Hz 1GHz 101"
        assert self.aedtapp.analyze()

    def test_36_create_voltage_probe(self):
        myprobe = self.aedtapp.modeler.components.create_voltage_probe(name="voltage_probe")
        assert type(myprobe.id) is int

    def test_37_draw_graphical_primitives(self):
        line = self.aedtapp.modeler.components.create_line([[0, 0], [1, 1]])
        assert line

    def test_38_browse_log_file(self):
        self.aedtapp.insert_design("data_block1")
        with open(os.path.join(self.local_scratch.path, "lc.net"), "w") as f:
            for i in range(10):
                f.write(f"L{i} net_{i} net_{i+1} 1e-9\n")
                f.write(f"C{i} net_{i+1} 0 5e-12\n")
        self.aedtapp.modeler.components.create_interface_port("net_0", (0, 0), angle=90)
        self.aedtapp.modeler.components.create_interface_port("net_10", (0.01, 0))
        lna = self.aedtapp.create_setup("mylna", self.aedtapp.SETUPS.NexximLNA)
        lna.props["SweepDefinition"]["Data"] = "LINC 0Hz 1GHz 101"
        assert not self.aedtapp.browse_log_file()
        self.aedtapp.analyze()
        time.sleep(2)
        assert self.aedtapp.browse_log_file()
        if not is_linux:
            self.aedtapp.save_project()
            assert self.aedtapp.browse_log_file()
            assert not self.aedtapp.browse_log_file(os.path.join(self.aedtapp.working_directory, "logfiles"))
            assert self.aedtapp.browse_log_file(self.aedtapp.working_directory)

    def test_39_export_results_circuit(self):
        exported_files = self.aedtapp.export_results()
        assert len(exported_files) > 0

    def test_40_assign_sources(self):
        self.aedtapp.insert_design("sources")
        c = self.aedtapp
        filepath = os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, "frequency_dependent_source.fds")
        name = "PowerSinusoidal3"
        assert c.create_source(source_type="PowerSin", name=name)
        c.sources[name].ac_magnitude = "2V"
        c.sources[name].ac_phase = "2deg"
        c.sources[name].dc_magnitude = "2V"
        c.sources[name].power_offset = "2W"
        c.sources[name].power_magnitude = "20W"
        c.sources[name].frequency = "20GHz"
        c.sources[name].delay = "20ns"
        c.sources[name].damping_factor = "200"
        c.sources[name].phase_delay = "100deg"
        c.sources[name].tone = "100Hz"

        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("Name") == name
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("ACMAG") == "2V"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("ACPHASE") == "2deg"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("DC") == "2V"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("VO") == "2W"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("POWER") == "20W"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("FREQ") == "20GHz"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("TD") == "20ns"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("ALPHA") == "200"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("THETA") == "100deg"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("TONE") == "100Hz"

        name = "PowerIQ"
        assert c.create_source(source_type="PowerIQ", name="PowerIQ")
        c.sources[name].carrier_frequency = "2GHz"
        c.sources[name].sampling_time = "2s"
        c.sources[name].dc_magnitude = "2V"
        c.sources[name].repeat_from = "22s"
        c.sources[name].delay = "20ns"
        c.sources[name].carrier_amplitude_voltage = "20V"
        c.sources[name].carrier_amplitude_power = "20W"
        c.sources[name].carrier_offset = "100V"
        c.sources[name].real_impedance = "100ohm"
        c.sources[name].imaginary_impedance = "1000ohm"
        c.sources[name].damping_factor = "200"
        c.sources[name].phase_delay = "100deg"
        c.sources[name].tone = "100Hz"
        c.sources[name].i_q_values = [["0s", "1V", "2V"], ["1s", "3V", "2V"]]
        c.sources[name].file = filepath

        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("Name") == name
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("FC") == "2GHz"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("TS") == "2s"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("DC") == "2V"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("R") == "22s"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("TD") == "20ns"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("V") == "20V"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("VA") == "20W"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("VO") == "100V"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("RZ") == "100ohm"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("IZ") == "1000ohm"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("ALPHA") == "200"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("THETA") == "100deg"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("TONE") == "100Hz"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("time1") == "0s"

        source_freq = c.create_source(source_type="VoltageFrequencyDependent", name="freq_pyaedt")
        # Data can not be obtained from GetPropValue
        source_freq.magnitude_angle = True
        assert source_freq.magnitude_angle
        source_freq.frequencies = [2000000000, 3000000000]
        assert source_freq.frequencies[0] == 2000000000
        source_freq.vmag = [0.001, 0.02]
        assert len(source_freq.vmag) == 2
        source_freq.vang = [0.0349065850398866, 0.0872664625997165]
        assert source_freq.vang == [0.0349065850398866, 0.0872664625997165]
        source_freq.vreal = [2, 1]
        assert source_freq.vreal == [2, 1]
        source_freq.vimag = ["0.2", "0.1"]
        assert source_freq.vimag == [0.2, 0.1]
        source_freq.magnitude_angle = False
        assert not source_freq.magnitude_angle
        source_freq.fds_filename = filepath
        assert source_freq.fds_filename == filepath
        source_freq.fds_filename = None

        assert c.create_source(source_type="VoltageDC", name="dc_pyaedt")
        c.sources["dc_pyaedt"].ac_magnitude = "2V"
        assert c.odesign.GetChildObject("Excitations").GetChildObject("dc_pyaedt").GetPropValue("Name") == "dc_pyaedt"
        c.sources["dc_pyaedt"].ac_phase = "2deg"
        c.sources["dc_pyaedt"].dc_magnitude = "2V"
        c.sources["dc_pyaedt"].name = "dc_pyaedt2"
        assert c.odesign.GetChildObject("Excitations").GetChildObject("dc_pyaedt2").GetPropValue("Name") == "dc_pyaedt2"
        assert c.odesign.GetChildObject("Excitations").GetChildObject("dc_pyaedt2").GetPropValue("ACMAG") == "2V"
        assert c.odesign.GetChildObject("Excitations").GetChildObject("dc_pyaedt2").GetPropValue("ACPHASE") == "2deg"
        assert c.odesign.GetChildObject("Excitations").GetChildObject("dc_pyaedt2").GetPropValue("DC") == "2V"

        name = "VoltageSinusoidal1"
        assert c.create_source(source_type="VoltageSin", name=name)
        c.sources[name].ac_magnitude = "2V"
        c.sources[name].ac_phase = "2deg"
        c.sources[name].dc_magnitude = "2V"
        c.sources[name].voltage_offset = "2V"
        c.sources[name].voltage_amplitude = "5V"
        c.sources[name].frequency = "20GHz"
        c.sources[name].delay = "20ns"
        c.sources[name].damping_factor = "200"
        c.sources[name].phase_delay = "100deg"
        c.sources[name].tone = "100Hz"

        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("Name") == name
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("ACMAG") == "2V"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("ACPHASE") == "2deg"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("DC") == "2V"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("VO") == "2V"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("VA") == "5V"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("FREQ") == "20GHz"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("TD") == "20ns"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("ALPHA") == "200"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("THETA") == "100deg"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("TONE") == "100Hz"

        name = "CurrentSinusoidal1"
        source_isin = c.create_source(source_type="CurrentSin", name="CurrentSinusoidal1")
        source_isin.ac_magnitude = "2A"
        source_isin.ac_phase = "2deg"
        source_isin.dc_magnitude = "2A"
        source_isin.current_offset = "2A"
        source_isin.current_amplitude = "5A"
        source_isin.multiplier = "5V"
        source_isin.frequency = "20GHz"
        source_isin.delay = "20ns"
        source_isin.damping_factor = "200"
        source_isin.phase_delay = "100deg"
        source_isin.tone = "100Hz"

        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("Name") == name
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("ACMAG") == "2A"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("ACPHASE") == "2deg"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("DC") == "2A"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("VO") == "2A"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("VA") == "5A"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("M") == "5V"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("FREQ") == "20GHz"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("TD") == "20ns"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("ALPHA") == "200"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("THETA") == "100deg"
        assert c.odesign.GetChildObject("Excitations").GetChildObject(name).GetPropValue("TONE") == "100Hz"

        assert "PowerSinusoidal3" in c.sources

        c.sources["PowerSinusoidal3"].name = "PowerTest"
        assert "PowerTest" in c.source_names
        c.sources["freq_pyaedt"].delete()
        assert len(c.source_objects) == 5

    def test_41_assign_excitations(self, add_app):
        c = self.aedtapp
        port = c.modeler.schematic.create_interface_port(name="Port1")

        # Port angle not working in 2023.1
        port.angle = 90.0

        port.location = ["100mil", "200mil"]
        assert port.location == ["100mil", "200mil"]
        port.mirror = True
        assert port.mirror
        port.name = "Port3"
        assert port.name == "Port3"
        port.use_symbol_color = False
        assert not port.use_symbol_color
        port.impedance = [50, 50]
        assert port.impedance[0] == 50
        port.enable_noise = True
        assert port.enable_noise
        port.noise_temperature = "18 cel"
        assert port.noise_temperature == "18 cel"
        port.microwave_symbol = True
        assert port.microwave_symbol

        port.reference_node = "Port3"
        port.reference_node = "Ground"
        port.reference_node = "NoNet"
        port.reference_node = "Z"

        assert c.excitation_objects

        setup = c.create_setup()

        c.excitation_objects["Port3"].enabled_sources = ["PowerTest"]
        assert len(c.excitation_objects["Port3"].enabled_sources) == 1
        setup1 = c.create_setup()
        setup2 = c.create_setup()
        c.excitation_objects["Port3"].enabled_analyses = {"PowerTest": [setup.name, setup2.name]}
        assert c.excitation_objects["Port3"].enabled_analyses["PowerTest"][0] == setup.name

        c.excitation_objects["Port3"].name = "PortTest"
        assert "PortTest" in c.excitations
        c.excitation_objects["PortTest"].delete()
        assert len(c.excitation_objects) == 0
        if not is_linux:
            self.aedtapp.save_project()
            c = add_app(application=Circuit, design_name="sources")
            assert c.sources

    def test_41_set_variable(self):
        self.aedtapp.variable_manager.set_variable("var_test", expression="123")
        self.aedtapp["var_test"] = "234"
        assert "var_test" in self.aedtapp.variable_manager.design_variable_names
        assert self.aedtapp.variable_manager.design_variables["var_test"].expression == "234"

    def test_42_create_wire(self):
        self.aedtapp.insert_design("CreateWireTest")
        myind = self.aedtapp.modeler.schematic.create_inductor("L101", location=[0.02, 0.0])
        myres = self.aedtapp.modeler.schematic.create_resistor("R101", location=[0.0, 0.0])
        myres2 = self.aedtapp.modeler.components.get_component(myres.composed_name)
        self.aedtapp.modeler.schematic.create_wire(
            [myind.pins[0].location, myres.pins[1].location], name="wire_name_test"
        )
        wire_names = []
        for key in self.aedtapp.modeler.schematic.wires.keys():
            wire_names.append(self.aedtapp.modeler.schematic.wires[key].name)
        assert "wire_name_test" in wire_names
        assert not self.aedtapp.modeler.schematic.create_wire(
            [["100mil", "0"], ["100mil", "100mil"]], name="wire_name_test1"
        )
        self.aedtapp.modeler.schematic.create_wire([[0.02, 0.02], [0.04, 0.02]], name="wire_test1")
        wire_keys = [key for key in self.aedtapp.modeler.schematic.wires]
        for key in wire_keys:
            if self.aedtapp.modeler.schematic.wires[key].name == "wire_test1":
                assert len(self.aedtapp.modeler.schematic.wires[key].points_in_segment) == 1
                assert self.aedtapp.modeler.schematic.wires[key].id == key
                for seg_key in list(self.aedtapp.modeler.schematic.wires[key].points_in_segment.keys()):
                    point_list = [
                        round(x, 2)
                        for y in self.aedtapp.modeler.schematic.wires[key].points_in_segment[seg_key]
                        for x in y
                    ]
                    assert point_list[0] == 0.02
                    assert point_list[1] == 0.02
                    assert point_list[2] == 0.04
                    assert point_list[3] == 0.02

    def test_43_display_wire_properties(self):
        self.aedtapp.set_active_design("CreateWireTest")
        wire = self.aedtapp.modeler.components.get_wire_by_name("wire_name_test")
        assert wire.display_wire_properties(
            name="wire_name_test", property_to_display="NetName", visibility="Value", location="Top"
        )

        assert not self.aedtapp.modeler.wire.display_wire_properties(
            name="invalid", property_to_display="NetName", visibility="Value", location="Top"
        )
        assert not self.aedtapp.modeler.wire.display_wire_properties(
            name="invalid", property_to_display="NetName", visibility="Value", location="invalid"
        )

    def test_44_auto_wire(self):
        self.aedtapp.insert_design("wires")
        self.aedtapp.modeler.schematic_units = "mil"
        p1 = self.aedtapp.modeler.schematic.create_interface_port(name="In", location=[200, 300])
        r1 = self.aedtapp.modeler.schematic.create_resistor(value=50, location=[3700, "3mm"])
        l1 = self.aedtapp.modeler.schematic.create_inductor(value=1e-9, location=[1400, 3000], angle=90)
        l3 = self.aedtapp.modeler.schematic.create_inductor(value=1e-9, location=[1600, 2500], angle=90)
        l4 = self.aedtapp.modeler.schematic.create_inductor(value=1e-9, location=[1600, 500], angle=90)
        l2 = self.aedtapp.modeler.schematic.create_inductor(value=1e-9, location=[1400, 4000], angle=0)
        r2 = self.aedtapp.modeler.schematic.create_resistor(value=50, location=[3100, 3200])

        assert p1.pins[0].connect_to_component(r1.pins[1], use_wire=True)
        assert l1.pins[0].connect_to_component(l2.pins[0], use_wire=True)
        assert l3.pins[0].connect_to_component(l2.pins[1], use_wire=True, clearance_units=2)
        assert l4.pins[1].connect_to_component(l3.pins[0], use_wire=True, clearance_units=2)
        assert l4.pins[0].connect_to_component(l3.pins[1], use_wire=True)
        assert r1.pins[0].connect_to_component(l2.pins[0], use_wire=True)

    def test_43_create_and_change_prop_text(self):
        self.aedtapp.insert_design("text")
        self.aedtapp.modeler.schematic_units = "mil"
        text = self.aedtapp.modeler.create_text("text test", 100, 300)
        assert isinstance(text, str)
        assert text in self.aedtapp.oeditor.GetAllGraphics()
        assert self.aedtapp.modeler.create_text("text test", "1000mil", "-2000mil")

    @pytest.mark.skipif(config["NonGraphical"], reason="Change property doesn't work in non-graphical mode.")
    @pytest.mark.skipif(is_linux and config["desktopVersion"] == "2024.1", reason="Schematic has to be closed.")
    def test_44_change_text_property(self):
        self.aedtapp.set_active_design("text")
        text_id = self.aedtapp.oeditor.GetAllGraphics()[0].split("@")[1]
        assert self.aedtapp.modeler.change_text_property(text_id, "Font", "Calibri")
        assert self.aedtapp.modeler.change_text_property(text_id, "DisplayRectangle", True)
        assert self.aedtapp.modeler.change_text_property(text_id, "Color", [255, 120, 0])
        assert not self.aedtapp.modeler.change_text_property(text_id, "Color", ["255", 120, 0])
        assert self.aedtapp.modeler.change_text_property(text_id, "Location", ["-5000mil", "2000mil"])
        assert self.aedtapp.modeler.change_text_property(text_id, "Location", [5000, 2000])
        assert not self.aedtapp.modeler.change_text_property(1, "Color", [255, 120, 0])
        assert not self.aedtapp.modeler.change_text_property(text_id, "Invalid", {})

    @pytest.mark.skipif(config["NonGraphical"], reason="Change property doesn't work in non-graphical mode.")
    @pytest.mark.skipif(is_linux and config["desktopVersion"] == "2024.1", reason="Schematic has to be closed.")
    def test_45_create_circuit_from_multizone_layout(self, add_edb):
        edb = add_edb(project_name="multi_zone_project")
        common_reference_net = "gnd"
        edb_zones = edb.copy_zones()
        assert edb_zones
        defined_ports, project_connexions = edb.cutout_multizone_layout(edb_zones, common_reference_net)
        edb.close_edb()
        assert project_connexions
        self.aedtapp.insert_design("test_45")
        self.aedtapp.connect_circuit_models_from_multi_zone_cutout(project_connexions, edb_zones, defined_ports)
        assert [mod for mod in list(self.aedtapp.modeler.schematic.components.values()) if "PagePort" in mod.name]
        assert self.aedtapp.remove_all_unused_definitions()

    def test_46_create_vpwl(self):
        # default inputs
        myres = self.aedtapp.modeler.schematic.create_voltage_pwl(name="V1")
        assert myres.refdes != ""
        assert type(myres.id) is int
        assert myres.parameters["time1"] == "0s"
        assert myres.parameters["time2"] == "0s"
        assert myres.parameters["val1"] == "0V"
        assert myres.parameters["val2"] == "0V"
        # time and voltage input list
        myres = self.aedtapp.modeler.schematic.create_voltage_pwl(name="V2", time_list=[0, "1u"], voltage_list=[0, 1])
        assert myres.refdes != ""
        assert type(myres.id) is int
        assert myres.parameters["time1"] == "0"
        assert myres.parameters["time2"] == "1u"
        assert myres.parameters["val1"] == "0"
        assert myres.parameters["val2"] == "1"
        # time and voltage different length
        myres = self.aedtapp.modeler.schematic.create_voltage_pwl(name="V3", time_list=[0], voltage_list=[0, 1])
        assert myres is False

    def test_47_automatic_lna(self):
        touchstone_file = os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, touchstone_custom)

        status, diff_pairs, comm_pairs = self.aedtapp.create_lna_schematic_from_snp(
            input_file=touchstone_file,
            start_frequency=0,
            stop_frequency=70,
            auto_assign_diff_pairs=True,
            separation=".",
            pattern=["component", "pin", "net"],
            analyze=False,
        )
        assert status

    @pytest.mark.skipif(
        config["NonGraphical"] and is_linux, reason="Method is not working in Linux and non-graphical mode."
    )
    def test_48_automatic_tdr(self):
        touchstone_file = os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, touchstone_custom)

        result, tdr_probe_name = self.aedtapp.create_tdr_schematic_from_snp(
            input_file=touchstone_file,
            tx_schematic_pins=["A-MII-RXD1_30.SQFP28X28_208.P"],
            tx_schematic_differential_pins=["A-MII-RXD1_65.SQFP20X20_144.N"],
            termination_pins=["A-MII-RXD2_32.SQFP28X28_208.P", "A-MII-RXD2_66.SQFP20X20_144.N"],
            differential=True,
            rise_time=35,
            use_convolution=True,
            analyze=False,
            design_name="TDR",
        )
        assert result

    @pytest.mark.skipif(config["NonGraphical"] and is_linux, reason="Method not working in Linux and Non graphical.")
    def test_49_automatic_ami(self):
        touchstone_file = os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, touchstone_custom)
        ami_file = os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, "pcieg5_32gt.ibs")
        result, eye_curve_tx, eye_curve_rx = self.aedtapp.create_ami_schematic_from_snp(
            input_file=touchstone_file,
            ibis_tx_file=ami_file,
            tx_buffer_name="1p",
            rx_buffer_name="2p",
            tx_schematic_pins=["A-MII-RXD1_30.SQFP28X28_208.P"],
            rx_schematic_pins=["A-MII-RXD2_32.SQFP28X28_208.P"],
            tx_schematic_differential_pins=["A-MII-RXD1_65.SQFP20X20_144.N"],
            rx_schematic_differentialial_pins=["A-MII-RXD2_66.SQFP20X20_144.N"],
            use_ibis_buffer=False,
            differential=True,
            bit_pattern="random_bit_count=2.5e3 random_seed=1",
            unit_interval="31.25ps",
            use_convolution=True,
            analyze=False,
            design_name="AMI",
        )
        assert result

    @pytest.mark.skipif(config["NonGraphical"] and is_linux, reason="Method not working in Linux and Non graphical.")
    def test_49_automatic_ibis(self):
        touchstone_file = os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, touchstone_custom)
        ibis_file = os.path.join(TESTS_GENERAL_PATH, "example_models", "T15", "u26a_800_modified.ibs")
        result, eye_curve_tx, eye_curve_rx = self.aedtapp.create_ibis_schematic_from_snp(
            input_file=touchstone_file,
            ibis_tx_file=ibis_file,
            tx_buffer_name="DQ_FULL_800",
            rx_buffer_name="DQ_FULL_800",
            tx_schematic_pins=["A-MII-RXD1_30.SQFP28X28_208.P"],
            rx_schematic_pins=["A-MII-RXD2_32.SQFP28X28_208.P"],
            ibis_rx_file=ibis_file,
            use_ibis_buffer=True,
            differential=False,
            bit_pattern="random_bit_count=2.5e3 random_seed=1",
            unit_interval="31.25ps",
            use_convolution=True,
            analyze=False,
            design_name="AMI",
        )
        assert result

    def test_50_enforce_touchstone_passive(self):
        self.aedtapp.insert_design("Touchstone_passive")
        self.aedtapp.modeler.schematic_units = "mil"
        s_parameter_component = self.aedtapp.modeler.schematic.create_touchstone_component(self.touchstone_file)
        assert s_parameter_component.enforce_touchstone_model_passive()
        nexxim_customization = s_parameter_component.model_data.props["NexximCustomization"]
        assert -1 == nexxim_customization["DCOption"]
        assert 1 == nexxim_customization["InterpOption"]
        assert 3 == nexxim_customization["ExtrapOption"]
        assert 0 == nexxim_customization["Convolution"]
        assert 6 == nexxim_customization["Passivity"]
        assert not nexxim_customization["Reciprocal"]
        assert "" == nexxim_customization["ModelOption"]
        assert 2 == nexxim_customization["DataType"]

    def test_51_change_symbol_pin_location(self):
        self.aedtapp.insert_design("Pin_location")
        self.aedtapp.modeler.schematic_units = "mil"
        ts_component = self.aedtapp.modeler.schematic.create_touchstone_component(self.touchstone_file)
        pins = ts_component.pins
        pin_locations = {
            "left": [pins[0].name, pins[1].name, pins[2].name, pins[3].name, pins[4].name],
            "right": [pins[5].name],
        }
        assert ts_component.change_symbol_pin_locations(pin_locations)
        pin_locations = {"left": [pins[0].name, pins[1].name, pins[2].name], "right": [pins[5].name]}
        assert not ts_component.change_symbol_pin_locations(pin_locations)

    def test_51_import_asc(self):
        self.aedtapp.insert_design("ASC")
        asc_file = os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, "butter.asc")
        assert self.aedtapp.create_schematic_from_asc_file(asc_file)

    def test_52_create_current_probe(self):
        iprobe = self.aedtapp.modeler.schematic.create_current_probe(name="test_probe", location=[0.4, 0.2])
        assert type(iprobe.id) is int
        assert iprobe.InstanceName == "test_probe"
        iprobe2 = self.aedtapp.modeler.schematic.create_current_probe(location=[0.8, 0.2])
        assert type(iprobe2.id) is int

    def test_53_import_table(self):
        self.aedtapp.insert_design("import_table")
        file_header = os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, "table_header.csv")
        file_invented = "invented.csv"

        assert not self.aedtapp.import_table(file_header, column_separator="dummy")
        assert not self.aedtapp.import_table(file_invented)

        table = self.aedtapp.import_table(file_header)
        assert table in self.aedtapp.existing_analysis_sweeps

        assert not self.aedtapp.delete_imported_data("invented")

        assert self.aedtapp.delete_imported_data(table)
        assert table not in self.aedtapp.existing_analysis_sweeps

    def test_54_value_with_units(self):
        assert self.aedtapp.value_with_units("10mm") == "10mm"
        assert self.aedtapp.value_with_units("10") == "10mm"
