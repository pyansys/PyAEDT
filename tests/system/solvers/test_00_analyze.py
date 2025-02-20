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

import csv
import os
from pathlib import Path
import sys
import time

from ansys.aedt.core import Circuit
from ansys.aedt.core import Hfss3dLayout
from ansys.aedt.core import Icepak
from ansys.aedt.core import Maxwell3d
from ansys.aedt.core import Rmxprt
from ansys.aedt.core.generic.errors import AEDTRuntimeError
from ansys.aedt.core.generic.settings import is_linux
from ansys.aedt.core.visualization.post.spisim import SpiSim
import pytest

from tests.system.solvers.conftest import desktop_version
from tests.system.solvers.conftest import local_path

sbr_platform_name = "satellite_231"
icepak_solved_name = "icepak_summary_solved"
sbr_platform_solved_name = "satellite_solved"
array_name = "array_231"
test_solve = "test_solve"
test_3dl_solve = "h3dl_test_solved"
original_project_name = "ANSYS-HSD_V1"
transient = "Transient_StrandedWindings"

component = "Circ_Patch_5GHz_232.a3dcomp"


test_subfolder = "T00"
erl_project_name = "erl_unit_test"
com_project_name = "com_unit_test_23r2"


@pytest.fixture()
def icepak_solved(add_app):
    app = add_app(project_name=icepak_solved_name, subfolder=test_subfolder, application=Icepak)
    yield app
    app.close_project(save=False)


@pytest.fixture()
def sbr_platform(add_app):
    app = add_app(project_name=sbr_platform_name, subfolder=test_subfolder)
    yield app
    app.close_project(save=False)


@pytest.fixture()
def sbr_platform_solved(add_app):
    app = add_app(project_name=sbr_platform_solved_name, subfolder=test_subfolder)
    yield app
    app.close_project(save=False)


@pytest.fixture()
def array(add_app):
    app = add_app(project_name=array_name, subfolder=test_subfolder)
    yield app
    app.close_project(save=False)


@pytest.fixture()
def sbr_app(add_app):
    app = add_app(project_name="SBR_test", solution_type="SBR+")
    yield app
    app.close_project(save=False)


@pytest.fixture()
def hfss_app(add_app):
    app = add_app(project_name="Hfss_test")
    yield app
    app.close_project(save=False)


@pytest.fixture(scope="class")
def icepak_app(add_app):
    app = add_app(application=Icepak, design_name="SolveTest")
    return app


@pytest.fixture(scope="class")
def hfss3dl_solve(add_app):
    app = add_app(project_name=test_solve, application=Hfss3dLayout, subfolder=test_subfolder)
    yield app
    app.close_project(save=False)


@pytest.fixture(scope="class")
def hfss3dl_solved(add_app):
    app = add_app(project_name=test_3dl_solve, application=Hfss3dLayout, subfolder=test_subfolder)
    yield app
    app.close_project(save=False)


@pytest.fixture(scope="class")
def circuit_app(add_app):
    app = add_app(original_project_name, application=Circuit, subfolder=test_subfolder)
    app.modeler.schematic_units = "mil"
    return app


@pytest.fixture(scope="class")
def circuit_erl(add_app):
    app = add_app(erl_project_name, design_name="2ports", application=Circuit, subfolder=test_subfolder)
    return app


@pytest.fixture(scope="class")
def circuit_com(add_app):
    app = add_app(com_project_name, design_name="0_simple_channel", application=Circuit, subfolder=test_subfolder)
    return app


@pytest.fixture(scope="class")
def m3dtransient(add_app):
    app = add_app(application=Maxwell3d, project_name=transient, subfolder=test_subfolder)
    yield app
    app.close_project(app.project_name)


class TestClass:
    @pytest.fixture(autouse=True)
    def init(self, local_scratch):
        self.local_scratch = local_scratch

    def test_3dl_generate_mesh(self, hfss3dl_solve):
        assert hfss3dl_solve.mesh.generate_mesh("Setup1")

    @pytest.mark.skipif(desktop_version < "2023.2", reason="Working only from 2023 R2")
    def test_3dl_analyze_setup(self, hfss3dl_solve):
        assert hfss3dl_solve.export_touchstone_on_completion(export=False)
        assert hfss3dl_solve.export_touchstone_on_completion(export=True)
        if desktop_version > "2024.2":
            assert hfss3dl_solve.set_export_touchstone()
        else:
            with pytest.raises(AEDTRuntimeError):
                hfss3dl_solve.set_export_touchstone()
        assert hfss3dl_solve.analyze_setup("Setup1", cores=4, blocking=False)
        assert hfss3dl_solve.are_there_simulations_running
        assert hfss3dl_solve.stop_simulations()
        while hfss3dl_solve.are_there_simulations_running:
            time.sleep(1)

    @pytest.mark.skipif(is_linux or sys.version_info < (3, 8), reason="Not supported.")
    def test_01a_sbr_link_array(self, sbr_platform, array):
        assert sbr_platform.create_sbr_linked_antenna(array, target_cs="antenna_CS", field_type="farfield")
        profile = sbr_platform.setups[0].get_profile()
        assert profile is None

    @pytest.mark.skipif(is_linux or sys.version_info < (3, 8), reason="Not supported.")
    def test_01b_sbr_link_array(self, sbr_platform_solved):
        profile = sbr_platform_solved.setups[0].get_profile()
        assert isinstance(profile, dict)
        assert not sbr_platform_solved.get_profile("Invented_setup")
        solution_data = sbr_platform_solved.setups[0].get_solution_data()

        ffdata = sbr_platform_solved.get_antenna_data(frequencies=solution_data.intrinsics["Freq"], sphere="3D")
        sbr_platform_solved.get_antenna_data(frequencies=solution_data.intrinsics["Freq"], sphere="3D", overwrite=False)

        ffdata.farfield_data.plot_cut(
            quantity="RealizedGain",
            primary_sweep="theta",
            secondary_sweep_value=[75],
            theta=20,
            title=f"Azimuth at {ffdata.farfield_data.frequency}Hz",
            quantity_format="dB10",
            show=False,
            output_file=os.path.join(self.local_scratch.path, "2d1_array.jpg"),
        )
        assert os.path.exists(os.path.join(self.local_scratch.path, "2d1_array.jpg"))

    def test_01b_sbr_create_vrt(self, sbr_app):
        sbr_app.rename_design("vtr")
        sbr_app.modeler.create_sphere([10, 10, 10], 5, material="copper")
        vrt = sbr_app.post.create_sbr_plane_visual_ray_tracing(max_frequency="10GHz", incident_theta="40deg")
        assert vrt
        vrt.incident_phi = "30deg"
        assert vrt.update()
        assert vrt.delete()
        vrt = sbr_app.post.create_sbr_point_visual_ray_tracing(max_frequency="10GHz")
        assert vrt
        vrt.custom_location = [10, 10, 0]
        assert vrt.update()
        assert vrt.delete()

    def test_01c_sbr_create_vrt_creeping(self, sbr_app):
        sbr_app.rename_design("vtr_creeping")
        sbr_app.modeler.create_sphere([10, 10, 10], 5, material="copper")
        vrt = sbr_app.post.create_creeping_plane_visual_ray_tracing(max_frequency="10GHz")
        assert vrt
        vrt.incident_phi = "30deg"
        assert vrt.update()
        assert vrt.delete()
        vrt = sbr_app.post.create_creeping_point_visual_ray_tracing(max_frequency="10GHz")
        assert vrt
        vrt.custom_location = [10, 10, 0]
        assert vrt.update()
        assert vrt.delete()

    @pytest.mark.skipif(
        desktop_version < "2022.2",
        reason="Not working in non-graphical in version lower than 2022.2",
    )
    def test_02_hfss_export_results(self, hfss_app):
        hfss_app.insert_design("Array_simple_resuts", "Modal")
        from ansys.aedt.core.generic.general_methods import read_json

        if desktop_version > "2023.1":
            dict_in = read_json(os.path.join(local_path, "example_models", test_subfolder, "array_simple_232.json"))
            dict_in["Circ_Patch_5GHz_232_1"] = os.path.join(local_path, "example_models", test_subfolder, component)
            dict_in["cells"][(3, 3)] = {"name": "Circ_Patch_5GHz_232_1"}
            dict_in["cells"][(3, 3)]["rotation"] = 90
        else:
            dict_in = read_json(os.path.join(local_path, "example_models", test_subfolder, "array_simple.json"))
            dict_in["Circ_Patch_5GHz1"] = os.path.join(local_path, "example_models", test_subfolder, component)
            dict_in["cells"][(3, 3)] = {"name": "Circ_Patch_5GHz1"}
            dict_in["cells"][(3, 3)]["rotation"] = 90
        hfss_app.add_3d_component_array_from_json(dict_in)
        exported_files = hfss_app.export_results()
        assert len(exported_files) == 0
        setup_driven = hfss_app.create_setup(name="test", setup_type="HFSSDriven", MaximumPasses=1)
        exported_files = hfss_app.export_results()
        solve_freq = setup_driven.props["Frequency"]
        assert len(exported_files) == 0
        hfss_app.analyze_setup(name="test", cores=4)
        assert setup_driven.is_solved
        exported_files = hfss_app.export_results()
        assert len(exported_files) == 39
        exported_files = hfss_app.export_results(
            matrix_type="Y",
        )
        assert len(exported_files) > 0
        fld_file1 = os.path.join(self.local_scratch.path, "test_fld_hfss1.fld")
        assert hfss_app.post.export_field_file(
            quantity="Mag_E", output_file=fld_file1, assignment="Box1", intrinsics=solve_freq, phase="5deg"
        )
        assert os.path.exists(fld_file1)
        fld_file2 = os.path.join(self.local_scratch.path, "test_fld_hfss2.fld")
        assert hfss_app.post.export_field_file(
            quantity="Mag_E", output_file=fld_file2, assignment="Box1", intrinsics={"frequency": solve_freq}
        )
        assert os.path.exists(fld_file2)
        fld_file2 = os.path.join(self.local_scratch.path, "test_fld_hfss3.fld")
        assert hfss_app.post.export_field_file(
            quantity="Mag_E",
            output_file=fld_file2,
            assignment="Box1",
            intrinsics={"frequency": solve_freq, "phase": "30deg"},
        )
        assert os.path.exists(fld_file2)
        fld_file2 = os.path.join(self.local_scratch.path, "test_fld_hfss4.fld")
        assert hfss_app.post.export_field_file(
            quantity="Mag_E",
            output_file=fld_file2,
            assignment="Box1",
            intrinsics={"frequency": solve_freq},
            phase="30deg",
        )
        assert os.path.exists(fld_file2)
        fld_file2 = os.path.join(self.local_scratch.path, "test_fld_hfss5.fld")
        assert hfss_app.post.export_field_file(
            quantity="Mag_E",
            output_file=fld_file2,
            assignment="Box1",
        )
        assert os.path.exists(fld_file2)
        fld_file2 = os.path.join(self.local_scratch.path, "test_fld_hfss6.fld")
        with pytest.raises(AttributeError):
            hfss_app.post.export_field_file(quantity="Mag_E", output_file=fld_file2, assignment="Box1", intrinsics=[])
        assert not os.path.exists(fld_file2)

        hfss_app.variable_manager.set_variable(name="dummy", expression=1, is_post_processing=True)
        sweep = hfss_app.parametrics.add(variable="dummy", start_point=0, end_point=1, step=2)
        assert hfss_app.export_touchstone_on_completion(export=False)
        assert hfss_app.export_touchstone_on_completion(export=True)

    def test_03a_icepak_analyze_and_export_summary(self, icepak_solved):

        assert icepak_solved.create_output_variable("OutputVariable2", "abs(Variable1)")  # test creation
        assert icepak_solved.create_output_variable("OutputVariable2", "asin(Variable1)")  # test update
        icepak_solved.save_project()
        assert icepak_solved.export_summary(
            icepak_solved.working_directory, geometryType="Surface", variationlist=[], filename="A"
        )  # check usage of deprecated arguments
        assert icepak_solved.export_summary(
            icepak_solved.working_directory, geometry_type="Surface", variation_list=[], filename="B"
        )
        assert icepak_solved.export_summary(
            icepak_solved.working_directory, geometry_type="Volume", type="Boundary", filename="C"
        )
        for file_name, entities in [
            ("A_Temperature.csv", ["box", "Region"]),
            ("B_Temperature.csv", ["box", "Region"]),
            ("C_Temperature.csv", ["box"]),
        ]:
            with open(os.path.join(icepak_solved.working_directory, file_name), "r", newline="") as csv_file:
                csv_reader = csv.reader(csv_file)
                for _ in range(4):
                    _ = next(csv_reader)
                header = next(csv_reader)
                entity_index = header.index("Entity")
                csv_entities = [row[entity_index] for row in csv_reader]
                assert all(e in csv_entities for e in entities)

        box = [i.id for i in icepak_solved.modeler["box"].faces]
        assert os.path.exists(
            icepak_solved.eval_surface_quantity_from_field_summary(box, savedir=icepak_solved.working_directory)
        )
        opening = [i for i in icepak_solved.boundaries if i.type == "Opening"][0]
        # new post class
        out = icepak_solved.post.evaluate_faces_quantity(box, "HeatFlowRate")
        assert out["Total"]
        with pytest.raises(AttributeError):
            icepak_solved.post.evaluate_faces_quantity(box, "HeatFlowwwRate")
        out = icepak_solved.post.evaluate_object_quantity("box", "Temperature", volume=True)
        assert out["Mean"]
        out = icepak_solved.post.evaluate_boundary_quantity(opening.name, "Ux")
        assert out["Mean"]
        if icepak_solved.settings.aedt_version < "2024.1":
            with pytest.raises(AEDTRuntimeError):
                icepak_solved.post.evaluate_monitor_quantity("test_monitor2", "Temperature")
        else:
            out = icepak_solved.post.evaluate_monitor_quantity("test_monitor2", "Temperature")
            assert out["Mean"]
            with pytest.raises(AttributeError):
                icepak_solved.post.evaluate_monitor_quantity("no_test_monitor2", "Temperature")
        fs = icepak_solved.post.create_field_summary()
        fs.add_calculation("Boundary", "Surface", opening.name, "Ux")
        fs.add_calculation("Object", "Volume", "box", "Temperature")
        df = fs.get_field_summary_data(pandas_output=True)
        assert not df["Mean"].empty
        d = fs.get_field_summary_data()
        assert d["Mean"]

    def test_03b_icepak_get_output_variable(self, icepak_solved):
        with pytest.raises(KeyError):
            icepak_solved.get_output_variable("invalid")
        value = icepak_solved.get_output_variable("OutputVariable1")
        tol = 1e-9
        assert abs(value - 0.5235987755982988) < tol

    def test_03c_icepak_get_monitor_output(self, icepak_solved):
        assert icepak_solved.monitor.all_monitors["test_monitor"].value()
        assert icepak_solved.monitor.all_monitors["test_monitor"].value(quantity="Temperature")
        assert icepak_solved.monitor.all_monitors["test_monitor"].value(setup=icepak_solved.existing_analysis_sweeps[0])
        assert icepak_solved.monitor.all_monitors["test_monitor2"].value(quantity="HeatFlowRate")

    def test_03d_icepak_eval_tempc(self, icepak_solved):
        assert os.path.exists(
            icepak_solved.eval_volume_quantity_from_field_summary(
                ["box"], "Temperature", savedir=icepak_solved.working_directory
            )
        )

    def test_03e_icepak_ExportFLDFil(self, icepak_solved):
        fld_file = os.path.join(self.local_scratch.path, "test_fld.fld")
        icepak_solved.post.export_field_file(
            quantity="Temp",
            solution=icepak_solved.nominal_sweep,
            variations={},
            output_file=fld_file,
            assignment="box",
        )
        assert os.path.exists(fld_file)
        fld_file_1 = os.path.join(self.local_scratch.path, "test_fld_1.fld")
        sample_points_file = os.path.join(local_path, "example_models", test_subfolder, "temp_points.pts")
        icepak_solved.post.export_field_file(
            quantity="Temp",
            solution=icepak_solved.nominal_sweep,
            variations=icepak_solved.available_variations.nominal_w_values_dict,
            output_file=fld_file_1,
            assignment="box",
            sample_points_file=sample_points_file,
        )
        assert os.path.exists(fld_file_1)
        fld_file_2 = os.path.join(self.local_scratch.path, "test_fld_2.fld")
        icepak_solved.post.export_field_file(
            quantity="Temp",
            solution=icepak_solved.nominal_sweep,
            variations=icepak_solved.available_variations.nominal_w_values_dict,
            output_file=fld_file_2,
            assignment="box",
            sample_points=[[0, 0, 0], [3, 6, 8], [4, 7, 9]],
        )
        assert os.path.exists(fld_file_2)
        cs = icepak_solved.modeler.create_coordinate_system()
        fld_file_3 = os.path.join(self.local_scratch.path, "test_fld_3.fld")
        icepak_solved.post.export_field_file(
            quantity="Temp",
            solution=icepak_solved.nominal_sweep,
            variations=icepak_solved.available_variations.nominal_w_values_dict,
            output_file=fld_file_3,
            assignment="box",
            sample_points=[[0, 0, 0], [3, 6, 8], [4, 7, 9]],
            reference_coordinate_system=cs.name,
            export_in_si_system=False,
            export_field_in_reference=False,
        )
        assert os.path.exists(fld_file_3)

    def test_04c_3dl_analyze_setup(self, hfss3dl_solved):
        assert os.path.exists(hfss3dl_solved.export_profile("Setup1"))
        assert os.path.exists(hfss3dl_solved.export_mesh_stats("Setup1"))

    @pytest.mark.skipif(is_linux, reason="To be investigated on linux.")
    def test_04d_3dl_export_touchstone(self, hfss3dl_solved):
        filename = os.path.join(self.local_scratch.path, "touchstone.s2p")
        solution_name = "Setup1"
        sweep_name = "Sweep1"
        assert hfss3dl_solved.export_touchstone(solution_name, sweep_name, filename)
        assert os.path.exists(filename)
        assert hfss3dl_solved.export_touchstone(solution_name)
        sweep_name = None
        assert hfss3dl_solved.export_touchstone(solution_name, sweep_name)

    def test_04e_3dl_export_results(self, hfss3dl_solved):
        files = hfss3dl_solved.export_results()
        assert len(files) > 0

    def test_04f_3dl_set_export_touchstone(self, hfss3dl_solved):
        assert hfss3dl_solved.export_touchstone_on_completion(True)
        assert hfss3dl_solved.export_touchstone_on_completion(False)
        if desktop_version > "2024.2":
            assert hfss3dl_solved.set_export_touchstone()

    def test_04g_3dl_get_all_sparameter_list(self, hfss3dl_solved):
        assert hfss3dl_solved.get_all_sparameter_list == ["S(Port1,Port1)", "S(Port1,Port2)", "S(Port2,Port2)"]

    def test_04h_3dl_get_all_return_loss_list(self, hfss3dl_solved):
        assert hfss3dl_solved.get_all_return_loss_list() == ["S(Port1,Port1)", "S(Port2,Port2)"]

    def test_04i_3dl_get_all_insertion_loss_list(self, hfss3dl_solved):
        assert hfss3dl_solved.get_all_insertion_loss_list(
            drivers_prefix_name="Port1", receivers_prefix_name="Port2"
        ) == ["S(Port1,Port2)"]

    def test_04j_3dl_get_next_xtalk_list(self, hfss3dl_solved):
        assert hfss3dl_solved.get_next_xtalk_list() == ["S(Port1,Port2)"]

    def test_04k_3dl_get_fext_xtalk_list(self, hfss3dl_solved):
        assert hfss3dl_solved.get_fext_xtalk_list() == ["S(Port1,Port2)", "S(Port2,Port1)"]

    def test_05a_circuit_add_3dlayout_component(self, circuit_app):
        setup = circuit_app.create_setup("test_06b_LNA")
        setup.add_sweep_step(start=0, stop=5, step_size=0.01)
        myedb = circuit_app.modeler.schematic.add_subcircuit_3dlayout("main")
        assert type(myedb.id) is int
        ports = myedb.pins
        tx = ports
        rx = ports
        insertions = [f"dB(S({i.name},{j.name}))" for i, j in zip(tx, rx)]
        assert circuit_app.post.create_report(
            insertions,
            circuit_app.nominal_adaptive,
            report_category="Standard",
            plot_type="Rectangular Plot",
            subdesign_id=myedb.id,
        )
        new_report = circuit_app.post.reports_by_category.standard(insertions)
        new_report.sub_design_id = myedb.id
        assert new_report.create()

    def test_05b_circuit_add_hfss_component(self, circuit_app):
        my_model, myname = circuit_app.modeler.schematic.create_field_model(
            "uUSB", "Setup1 : Sweep", ["usb_N_conn", "usb_N_pcb", "usb_P_conn", "usb_P_pcb"]
        )
        assert type(my_model) is int

    def test_05c_circuit_push_excitation(self, circuit_app):
        setup_name = "test_07a_LNA"
        setup = circuit_app.create_setup(setup_name)
        setup.add_sweep_step(start=0, stop=5, step_size=0.01)
        assert circuit_app.push_excitations(instance="U1", thevenin_calculation=False, setup=setup_name)
        assert circuit_app.push_excitations(instance="U1", thevenin_calculation=True, setup=setup_name)

    def test_05d_circuit_push_excitation_time(self, circuit_app):
        setup_name = "test_07b_Transient"
        setup = circuit_app.create_setup(setup_name, setup_type="NexximTransient")
        assert circuit_app.push_time_excitations(instance="U1", setup=setup_name)

    def test_06_m3d_harmonic_forces(self, m3dtransient):
        assert m3dtransient.enable_harmonic_force(
            ["Stator"],
            force_type=2,
            window_function="Rectangular",
            use_number_of_cycles_from_stop_time=True,
            number_of_cycles_from_stop_time=3,
            calculate_force=0,
        )
        m3dtransient.solution_type = m3dtransient.SOLUTIONS.Maxwell3d.EddyCurrent
        assert m3dtransient.enable_harmonic_force(assignment=["Stator"])
        m3dtransient.solution_type = m3dtransient.SOLUTIONS.Maxwell3d.TransientAPhiFormulation
        assert m3dtransient.enable_harmonic_force(assignment=["Stator"], calculate_force=1)

    def test_06_export_element_based_harmonic_force(self, m3dtransient):
        assert m3dtransient.export_element_based_harmonic_force(
            start_frequency=1, stop_frequency=100, number_of_frequency=None
        )
        assert m3dtransient.export_element_based_harmonic_force(number_of_frequency=5)

    def test_07_export_maxwell_fields(self, m3dtransient):
        fld_file_3 = os.path.join(self.local_scratch.path, "test_fld_3.fld")
        assert m3dtransient.post.export_field_file(
            quantity="Mag_B",
            solution=m3dtransient.nominal_sweep,
            variations={},
            output_file=fld_file_3,
            assignment="Coil_A2",
            objects_type="Surf",
            intrinsics="10ms",
        )
        assert os.path.exists(fld_file_3)
        fld_file_4 = os.path.join(self.local_scratch.path, "test_fld_4.fld")
        assert not m3dtransient.post.export_field_file(
            quantity="Mag_B",
            solution=m3dtransient.nominal_sweep,
            variations=m3dtransient.available_variations.nominal_w_values_dict,
            output_file=fld_file_4,
            assignment="Coil_A2",
            objects_type="invalid",
        )
        setup = m3dtransient.setups[0]
        m3dtransient.setups[0].delete()
        assert not m3dtransient.post.export_field_file(
            quantity="Mag_B", variations={}, output_file=fld_file_4, assignment="Coil_A2"
        )

        new_setup = m3dtransient.create_setup(name=setup.name, setup_type=setup.setuptype)
        new_setup.props = setup.props
        new_setup.update()

    def test_08_compute_erl(self, circuit_erl):
        touchstone_file = circuit_erl.export_touchstone()
        spisim = SpiSim(touchstone_file)

        erl_data2 = spisim.compute_erl(
            port_order="EvenOdd",
            bandwidth="40g",
            tdr_duration=4,
            z_terminations=50,
            transition_time="10p",
            fixture_delay=400e-12,
            input_amplitude=1.0,
            ber=1e-4,
        )
        assert erl_data2
        circuit_erl.set_active_design("4_ports")
        touchstone_file2 = circuit_erl.export_touchstone()
        spisim.touchstone_file = touchstone_file2
        erl_data_3 = spisim.compute_erl(specify_through_ports=[1, 2, 3, 4])
        assert erl_data_3

    def test_09a_compute_com(self, local_scratch, circuit_com):
        touchstone_file = circuit_com.export_touchstone()
        spisim = SpiSim(touchstone_file)

        report_dir = os.path.join(spisim.working_directory, "50GAUI-1_C2C")
        os.mkdir(report_dir)
        com = spisim.compute_com(
            standard=1,
            out_folder=report_dir,
        )
        assert com

    def test_09b_compute_com(self, local_scratch):
        com_example_file_folder = os.path.join(local_path, "example_models", test_subfolder, "com_unit_test_sparam")
        thru_s4p = local_scratch.copyfile(os.path.join(com_example_file_folder, "SerDes_Demo_02_Thru.s4p"))
        fext_s4p = local_scratch.copyfile(
            os.path.join(com_example_file_folder, "FCI_CC_Long_Link_Pair_2_to_Pair_9_FEXT.s4p")
        )
        next_s4p = local_scratch.copyfile(
            os.path.join(com_example_file_folder, "FCI_CC_Long_Link_Pair_11_to_Pair_9_NEXT.s4p")
        )
        report_dir = os.path.join(local_scratch.path, "custom")
        os.mkdir(report_dir)
        spisim = SpiSim(thru_s4p)
        spisim.working_directory = local_scratch.path

        com_0, com_1 = spisim.compute_com(
            standard=3,
            port_order="EvenOdd",
            fext_s4p=fext_s4p,
            next_s4p=next_s4p,
            out_folder=report_dir,
        )
        assert com_0 and com_1

    def test_09c_compute_com(self, local_scratch):
        com_example_file_folder = Path(local_path) / "example_models" / test_subfolder / "com_unit_test_sparam"
        thru_s4p = local_scratch.copyfile(com_example_file_folder / "SerDes_Demo_02_Thru.s4p")
        spisim = SpiSim(thru_s4p)

        spisim.export_com_configure_file(os.path.join(spisim.working_directory, "custom.json"))

        from ansys.aedt.core.visualization.post.spisim_com_configuration_files.com_parameters import COMParametersVer3p4

        com_param = COMParametersVer3p4()
        com_param.load(
            os.path.join(spisim.working_directory, "custom.json"),
        )
        com_param.export_spisim_cfg(str(Path(local_scratch.path) / "test.cfg"))
        com_0, com_1 = spisim.compute_com(0, Path(local_scratch.path) / "test.cfg")
        assert com_0 and com_1

    def test_10_export_to_maxwell(self, add_app):
        app = add_app("assm_test", application=Rmxprt, subfolder="T00")
        app.analyze(cores=1)
        m2d = app.create_maxwell_design("Setup1")
        assert m2d.design_type == "Maxwell 2D"
        m3d = app.create_maxwell_design("Setup1", maxwell_2d=False)
        assert m3d.design_type == "Maxwell 3D"
        config = app.export_configuration(os.path.join(self.local_scratch.path, "assm.json"))
        app2 = add_app("assm_test2", application=Rmxprt, solution_type="ASSM")
        app2.import_configuration(config)
        assert app2.circuit
