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
import shutil

import ansys.aedt.core
from ansys.aedt.core.generic.settings import is_linux
import pytest

from tests.system.general.conftest import local_path
from tests.system.solvers.conftest import desktop_version
from tests.system.solvers.conftest import local_path as solver_local_path

push_project = "push_excitation"
export_3d_project = "export"
twinbuilder_circuit = "TB_test"
report = "report"
fields_calculator = "fields_calculator_solved"
m2d_electrostatic = "maxwell_fields_calculator"

test_subfolder = "T45"
TEST_REVIEW_FLAG = True


class TestClass:
    @pytest.fixture(autouse=True)
    def init(self, desktop):
        os.environ["PYAEDT_SCRIPT_PORT"] = str(desktop.port)
        os.environ["PYAEDT_SCRIPT_VERSION"] = desktop.aedt_version_id

    def test_01_template(self, add_app):
        aedtapp = add_app(application=ansys.aedt.core.Hfss, project_name="workflow_test")

        from ansys.aedt.core.workflows.templates.template_get_started import main

        assert main({"is_test": True, "origin_x": 2})
        assert len(aedtapp.modeler.object_list) == 1

        file_path = os.path.join(solver_local_path, "example_models", "T00", "test_solve.aedt")
        assert main({"is_test": True, "file_path": file_path})
        assert len(aedtapp.project_list) == 2

        aedtapp.close_project(aedtapp.project_name)

    def test_02_hfss_push(self, add_app):
        aedtapp = add_app(project_name=push_project, subfolder=test_subfolder)

        from ansys.aedt.core.workflows.hfss.push_excitation_from_file import main

        # No choice
        file_path = os.path.join(local_path, "example_models", "T20", "Sinusoidal.csv")
        assert main({"is_test": True, "file_path": file_path, "choice": ""})
        aedtapp.save_project()
        assert not aedtapp.design_datasets

        # Correct choice
        assert main({"is_test": True, "file_path": file_path, "choice": "1:1"})
        aedtapp.save_project()
        assert aedtapp.design_datasets
        aedtapp.close_project(aedtapp.project_name)

    def test_03_hfss3dlayout_export_3d_q3d(self, local_scratch, add_app):
        aedtapp = add_app(
            application=ansys.aedt.core.Hfss3dLayout, project_name=export_3d_project, subfolder=test_subfolder
        )

        aedtapp.save_project(os.path.join(local_scratch.path, "test_03_hfss3dlayout_export_3d_q3d.aedt"))

        from ansys.aedt.core.workflows.hfss3dlayout.export_to_3d import main

        assert main({"is_test": True, "choice": "Export to Q3D"})

        assert os.path.isfile(os.path.join(local_scratch.path, "test_03_hfss3dlayout_export_3d_q3d_Q3D.aedt"))
        aedtapp.close_project(os.path.basename(aedtapp.project_file[:-5]) + "_Q3D")
        aedtapp.close_project(aedtapp.project_name)

    def test_03_hfss3dlayout_export_3d_icepak(self, local_scratch, add_app):
        aedtapp = add_app(
            application=ansys.aedt.core.Hfss3dLayout, project_name=export_3d_project, subfolder=test_subfolder
        )

        aedtapp.save_project(os.path.join(local_scratch.path, "test_03_hfss3dlayout_export_3d_icepak.aedt"))

        from ansys.aedt.core.workflows.hfss3dlayout.export_to_3d import main

        assert main({"is_test": True, "choice": "Export to Icepak"})

        assert os.path.isfile(os.path.join(local_scratch.path, "test_03_hfss3dlayout_export_3d_icepak_IPK.aedt"))
        aedtapp.close_project(os.path.basename(aedtapp.project_file[:-5]) + "_IPK")
        aedtapp.close_project(aedtapp.project_name)

    def test_03_hfss3dlayout_export_3d_maxwell(self, local_scratch, add_app):
        aedtapp = add_app(
            application=ansys.aedt.core.Hfss3dLayout, project_name=export_3d_project, subfolder=test_subfolder
        )

        aedtapp.save_project(os.path.join(local_scratch.path, "test_03_hfss3dlayout_export_3d_maxwell.aedt"))

        from ansys.aedt.core.workflows.hfss3dlayout.export_to_3d import main

        assert main({"is_test": True, "choice": "Export to Maxwell 3D"})

        assert os.path.isfile(os.path.join(local_scratch.path, "test_03_hfss3dlayout_export_3d_maxwell_M3D.aedt"))
        aedtapp.close_project(os.path.basename(aedtapp.project_file[:-5]) + "_M3D")
        aedtapp.close_project(aedtapp.project_name)

    def test_04_project_report(self, add_app):
        aedtapp = add_app(application=ansys.aedt.core.Hfss, project_name=report, subfolder=test_subfolder)

        from ansys.aedt.core.workflows.project.create_report import main

        assert main({"is_test": True})

        assert os.path.isfile(os.path.join(aedtapp.working_directory, "AEDT_Results.pdf"))
        aedtapp.close_project(aedtapp.project_name)

    def test_05_project_import_nastran(self, add_app, local_scratch):
        aedtapp = add_app(application=ansys.aedt.core.Hfss, project_name="workflow_nastran")

        from ansys.aedt.core.workflows.project.import_nastran import main

        # Non-existing file
        file_path = os.path.join(local_scratch.path, "test_cad_invented.nas")

        assert main({"is_test": True, "file_path": file_path, "lightweight": True, "decimate": 0.0, "planar": True})

        assert len(aedtapp.modeler.object_list) == 0

        file_path = shutil.copy(
            os.path.join(local_path, "example_models", "T20", "test_cad.nas"),
            os.path.join(local_scratch.path, "test_cad.nas"),
        )
        shutil.copy(
            os.path.join(local_path, "example_models", "T20", "assembly1.key"),
            os.path.join(local_scratch.path, "assembly1.key"),
        )
        shutil.copy(
            os.path.join(local_path, "example_models", "T20", "assembly2.key"),
            os.path.join(local_scratch.path, "assembly2.key"),
        )
        assert main({"is_test": True, "file_path": file_path, "lightweight": True, "decimate": 0.0, "planar": True})

        assert len(aedtapp.modeler.object_list) == 4
        aedtapp.close_project(aedtapp.project_name)

    def test_06_project_import_stl(self, add_app, local_scratch):
        aedtapp = add_app(application=ansys.aedt.core.Hfss, project_name="workflow_stl")

        from ansys.aedt.core.workflows.project.import_nastran import main

        file_path = shutil.copy(
            os.path.join(local_path, "example_models", "T20", "sphere.stl"),
            os.path.join(local_scratch.path, "sphere.stl"),
        )

        assert main({"is_test": True, "file_path": file_path, "lightweight": True, "decimate": 0.0, "planar": True})

        assert len(aedtapp.modeler.object_list) == 1
        aedtapp.close_project(aedtapp.project_name)

    @pytest.mark.skipif(is_linux, reason="Not supported in Linux.")
    def test_07_twinbuilder_convert_circuit(self, add_app):
        aedtapp = add_app(
            application=ansys.aedt.core.TwinBuilder, project_name=twinbuilder_circuit, subfolder=test_subfolder
        )

        from ansys.aedt.core.workflows.twinbuilder.convert_to_circuit import main

        assert main({"is_test": True})

    def test_08_configure_a3d(self, local_scratch):
        from ansys.aedt.core.workflows.project.configure_edb import main

        configuration_path = shutil.copy(
            os.path.join(solver_local_path, "example_models", "T45", "ports.json"),
            os.path.join(local_scratch.path, "ports.json"),
        )
        file_path = os.path.join(local_scratch.path, "ANSYS-HSD_V1.aedb")
        local_scratch.copyfolder(
            os.path.join(solver_local_path, "example_models", "T45", "ANSYS-HSD_V1.aedb"), file_path
        )

        main(
            is_test=True,
            execute={
                "aedt_load": [
                    {
                        "project_file": file_path,
                        "file_cfg_path": configuration_path,
                        "file_save_path": file_path.replace(".aedb", "_1.aedt"),
                    }
                ],
                "aedt_export": [
                    {"project_file": file_path, "file_path_save": configuration_path.replace(".json", "_1.json")}
                ],
                "active_load": [],
                "active_export": [],
                "siwave_load": [],
                "siwave_export": [],
            },
        )

        main(
            is_test=True,
            execute={
                "aedt_load": [],
                "aedt_export": [],
                "active_load": [
                    {
                        "project_file": file_path,
                        "file_cfg_path": configuration_path,
                        "file_save_path": file_path.replace(".aedb", "_1.aedt"),
                    }
                ],
                "active_export": [
                    {"project_file": file_path, "file_path_save": configuration_path.replace(".json", "_1.json")}
                ],
                "siwave_load": [],
                "siwave_export": [],
            },
        )

    def test_08_advanced_fields_calculator_non_general(self, add_app):
        aedtapp = add_app(application=ansys.aedt.core.Hfss, project_name=fields_calculator, subfolder=test_subfolder)

        my_expression = {
            "name": "test",
            "description": "Voltage drop along a line",
            "design_type": ["HFSS", "Q3D Extractor"],
            "fields_type": ["Fields", "CG Fields"],
            "solution_type": "",
            "primary_sweep": "Freq",
            "assignment": "",
            "assignment_type": ["Line"],
            "operations": [
                "Fundamental_Quantity('E')",
                "Operation('Real')",
                "Operation('Tangent')",
                "Operation('Dot')",
                "EnterLine('assignment')",
                "Operation('LineValue')",
                "Operation('Integrate')",
                "Operation('CmplxR')",
            ],
            "report": ["Data Table", "Rectangular Plot"],
        }

        name = aedtapp.post.fields_calculator.add_expression(my_expression, "Polyline1")
        assert name == "test"

        my_invalid_expression = {
            "name": "test2",
            "description": "Voltage drop along a line",
            "design_type": ["HFSS"],
            "fields_type": ["Fields", "CG Fields"],
            "solution_type": "",
            "primary_sweep": "Freq",
            "assignment": "",
            "assignment_type": ["Line"],
            "report": ["Data Table", "Rectangular Plot"],
        }

        assert not aedtapp.post.fields_calculator.add_expression(my_invalid_expression, "Polyline1")

        assert isinstance(aedtapp.post.fields_calculator.expression_names, list)
        name = aedtapp.post.fields_calculator.add_expression("voltage_line", "Polyline1")
        assert name == "Voltage_Line"
        file_path = os.path.join(aedtapp.working_directory, "my_expr.fld")
        assert aedtapp.post.fields_calculator.write("voltage_line", file_path, aedtapp.nominal_adaptive)
        points_path = os.path.join(solver_local_path, "example_models", "T00", "temp_points.pts")
        output_file = aedtapp.post.fields_calculator.export("voltage_line", sample_points=points_path)
        assert os.path.exists(output_file)
        output_file = aedtapp.post.fields_calculator.export(
            "voltage_line", sample_points=[[0, 0, 0], [3, 6, 8], [4, 7, 9]]
        )
        assert os.path.exists(output_file)
        assert not aedtapp.post.fields_calculator.export("voltage_line", sample_points=1)
        output_file = aedtapp.post.fields_calculator.export("voltage_line", grid_type="Cartesian")
        assert os.path.exists(output_file)
        assert not aedtapp.post.fields_calculator.export("voltage_line", grid_type="invalid")
        assert not aedtapp.post.fields_calculator.export("voltage_line")
        assert not aedtapp.post.fields_calculator.write("voltage_line", file_path, "invalid_setup")
        assert not aedtapp.post.fields_calculator.write("invalid", file_path, aedtapp.nominal_adaptive)
        invalid_file_path = os.path.join(aedtapp.working_directory, "my_expr.invalid")
        assert not aedtapp.post.fields_calculator.write("voltage_line", invalid_file_path, aedtapp.nominal_adaptive)
        name2 = aedtapp.post.fields_calculator.add_expression("voltage_line", "Polyline1")
        assert name == name2
        assert not aedtapp.post.fields_calculator.expression_plot("voltage_line_invented", "Polyline1", [name])
        assert aedtapp.post.fields_calculator.expression_plot("voltage_line", "Polyline1", [name])
        current_expr = aedtapp.post.fields_calculator.add_expression("current_line", "Polyline1")
        assert aedtapp.post.fields_calculator.delete_expression(current_expr)
        assert aedtapp.post.fields_calculator.delete_expression()
        assert not aedtapp.post.fields_calculator.is_expression_defined(name)
        assert not aedtapp.post.fields_calculator.add_expression("voltage_line", "Polyline1_invented")
        assert not aedtapp.post.fields_calculator.add_expression("voltage_line", "inner")
        assert not aedtapp.post.fields_calculator.add_expression("voltage_line", 500)

        from ansys.aedt.core.workflows.project.advanced_fields_calculator import main

        assert main(
            {
                "is_test": True,
                "setup": "Setup1 : LastAdaptive",
                "calculation": "voltage_line",
                "assignment": ["Polyline1", "Polyline2"],
            }
        )

        assert len(aedtapp.post.all_report_names) == 6

        assert not main(
            {
                "is_test": True,
                "setup": "Setup1 : LastAdaptive",
                "calculation": "",
                "assignment": ["Polyline1", "Polyline2"],
            }
        )

        assert not main(
            {
                "is_test": True,
                "setup": "Setup1 : LastAdaptive",
                "calculation": "voltage_line_invented",
                "assignment": ["Polyline1", "Polyline2"],
            }
        )

        aedtapp.close_project(aedtapp.project_name)

    def test_09_advanced_fields_calculator_general(self, add_app):
        aedtapp = add_app(application=ansys.aedt.core.Q3d, project_name=fields_calculator, subfolder=test_subfolder)

        initial_catalog = len(aedtapp.post.fields_calculator.expression_names)
        example_file = os.path.join(
            solver_local_path, "example_models", test_subfolder, "expression_catalog_custom.toml"
        )
        new_catalog = aedtapp.post.fields_calculator.load_expression_file(example_file)
        assert initial_catalog != len(new_catalog)
        assert new_catalog == aedtapp.post.fields_calculator.expression_catalog
        assert not aedtapp.post.fields_calculator.add_expression("e_field_magnitude", "Polyline1")
        assert not aedtapp.post.fields_calculator.load_expression_file("invented.toml")

        from ansys.aedt.core.workflows.project.advanced_fields_calculator import main

        if desktop_version > "2024.2":
            assert main(
                {
                    "is_test": True,
                    "setup": "Setup1 : LastAdaptive",
                    "calculation": "voltage_drop_2025",
                    "assignment": ["Face9", "inner"],
                }
            )
        else:
            assert main(
                {
                    "is_test": True,
                    "setup": "Setup1 : LastAdaptive",
                    "calculation": "voltage_drop",
                    "assignment": ["Face9", "inner"],
                }
            )
        assert len(aedtapp.post.ofieldsreporter.GetChildNames()) == 2

        aedtapp.close_project(aedtapp.project_name)

        aedtapp = add_app(
            application=ansys.aedt.core.Maxwell2d,
            project_name=m2d_electrostatic,
            design_name="e_tangential",
            subfolder=test_subfolder,
        )
        name = aedtapp.post.fields_calculator.add_expression("e_line", None)
        assert name
        assert aedtapp.post.fields_calculator.expression_plot("e_line", "Poly1", [name])

        assert main(
            {"is_test": True, "setup": "MySetupAuto : LastAdaptive", "calculation": "e_line", "assignment": ["Polyl1"]}
        )

        aedtapp.close_project(aedtapp.project_name)

        aedtapp = add_app(
            application=ansys.aedt.core.Maxwell2d,
            project_name=m2d_electrostatic,
            design_name="stress_tensor",
            subfolder=test_subfolder,
        )
        name = aedtapp.post.fields_calculator.add_expression("radial_stress_tensor", None)
        assert name
        assert aedtapp.post.fields_calculator.expression_plot("radial_stress_tensor", "Polyline1", [name])
        name = aedtapp.post.fields_calculator.add_expression("tangential_stress_tensor", None)
        assert name
        assert aedtapp.post.fields_calculator.expression_plot("tangential_stress_tensor", "Polyline1", [name])

        aedtapp.close_project(aedtapp.project_name)

    def test_10_push_excitation_3dl(self, local_scratch, desktop):
        from ansys.aedt.core.workflows.hfss3dlayout.push_excitation_from_file_3dl import main

        project_path = shutil.copy(
            os.path.join(local_path, "example_models", "T41", "test_post_3d_layout_solved_23R2.aedtz"),
            os.path.join(local_scratch.path, "test_post_3d_layout_solved_23R2.aedtz"),
        )

        h3d = ansys.aedt.core.Hfss3dLayout(project_path, version=desktop.aedt_version_id, port=str(desktop.port))

        file_path = os.path.join(local_path, "example_models", "T20", "Sinusoidal.csv")
        assert main({"is_test": True, "file_path": file_path, "choice": ""})
        h3d.save_project()
        assert not h3d.design_datasets

        # Correct choice
        assert main({"is_test": True, "file_path": file_path, "choice": "Port1"})
        h3d.save_project()
        # In 3D Layout datasets are not retrieved
        # assert h3d.design_datasets
        h3d.close_project(h3d.project_name)

    def test_11_cutout(self, add_app, local_scratch):
        from ansys.aedt.core.workflows.hfss3dlayout.cutout import main

        app = add_app("ANSYS-HSD_V1", application=ansys.aedt.core.Hfss3dLayout, subfolder=test_subfolder)

        assert main(
            {
                "is_test": True,
                "choice": "ConvexHull",
                "signals": ["DDR4_A0"],
                "reference": ["GND"],
                "expansion_factor": 3,
                "fix_disjoints": True,
            }
        )
        app.close_project()

    def test_12_export_layout(self, add_app, local_scratch):
        from ansys.aedt.core.workflows.hfss3dlayout.export_layout import main

        app = add_app("ANSYS-HSD_V1", application=ansys.aedt.core.Hfss3dLayout, subfolder=test_subfolder)

        assert main({"is_test": True, "export_ipc": True, "export_configuration": True, "export_bom": True})
        app.close_project()

    def test_13_parametrize_layout(self, local_scratch):
        from ansys.aedt.core.workflows.hfss3dlayout.parametrize_edb import main

        file_path = os.path.join(local_scratch.path, "ANSYS-HSD_V1_param.aedb")

        local_scratch.copyfolder(
            os.path.join(solver_local_path, "example_models", "T45", "ANSYS-HSD_V1.aedb"), file_path
        )

        assert main(
            {
                "is_test": True,
                "aedb_path": file_path,
                "parametrize_layers": True,
                "parametrize_materials": True,
                "parametrize_padstacks": True,
                "parametrize_traces": True,
                "nets_filter": ["GND"],
                "expansion_polygon_mm": 0.1,
                "expansion_void_mm": 0.1,
                "relative_parametric": True,
                "project_name": "new_parametrized",
            }
        )

    def test_14_power_map_creation_ipk(self, local_scratch, add_app):
        from ansys.aedt.core.workflows.icepak.power_map_from_csv import main

        file_path = os.path.join(solver_local_path, "example_models", "T45", "icepak_classic_powermap.csv")
        aedtapp = add_app("PowerMap", application=ansys.aedt.core.Icepak, subfolder=test_subfolder)
        assert main({"is_test": True, "file_path": file_path})
        assert len(aedtapp.modeler.object_list) == 3
        aedtapp.close_project()

    def test_15_import_asc(self, local_scratch, add_app):
        aedtapp = add_app("Circuit", application=ansys.aedt.core.Circuit)

        from ansys.aedt.core.workflows.circuit.import_schematic import main

        file_path = os.path.join(local_path, "example_models", "T21", "butter.asc")
        assert main({"is_test": True, "asc_file": file_path})

        file_path = os.path.join(local_path, "example_models", "T21", "netlist_small.cir")
        assert main({"is_test": True, "asc_file": file_path})

        file_path = os.path.join(local_path, "example_models", "T21", "Schematic1.qcv")
        assert main({"is_test": True, "asc_file": file_path})

        file_path_invented = os.path.join(local_path, "example_models", "T21", "butter_invented.asc")
        with pytest.raises(Exception) as execinfo:
            main({"is_test": True, "asc_file": file_path_invented})
            assert execinfo.args[0] == "File does not exist."
        aedtapp.close_project()

    @pytest.mark.skipif(is_linux, reason="Not supported in Linux.")
    def test_16_arbitrary_waveport(self, local_scratch):
        import tempfile

        from ansys.aedt.core.workflows.hfss3dlayout.generate_arbitrary_wave_ports import main

        file_path = os.path.join(local_scratch.path, "waveport.aedb")

        temp_dir = tempfile.TemporaryDirectory(suffix=".arbitrary_waveport_test")

        local_scratch.copyfolder(os.path.join(solver_local_path, "example_models", "T45", "waveport.aedb"), file_path)

        assert main({"is_test": True, "working_path": temp_dir.name, "source_path": file_path, "mounting_side": "top"})

        assert os.path.isfile(os.path.join(temp_dir.name, "wave_port.a3dcomp"))

        temp_dir.cleanup()

    def test_17_choke_designer(self, local_scratch):
        from ansys.aedt.core.workflows.hfss.choke_designer import main

        choke_config = {
            "Number of Windings": {"1": True, "2": False, "3": False, "4": False},
            "Layer": {"Simple": True, "Double": False, "Triple": False},
            "Layer Type": {"Separate": True, "Linked": False},
            "Similar Layer": {"Similar": True, "Different": False},
            "Mode": {"Differential": True, "Common": False},
            "Wire Section": {"None": False, "Hexagon": False, "Octagon": False, "Circle": True},
            "Core": {
                "Name": "Core",
                "Material": "ferrite",
                "Inner Radius": 20,
                "Outer Radius": 30,
                "Height": 10,
                "Chamfer": 0.8,
            },
            "Outer Winding": {
                "Name": "Winding",
                "Material": "copper",
                "Inner Radius": 20,
                "Outer Radius": 30,
                "Height": 10,
                "Wire Diameter": 1.5,
                "Turns": 20,
                "Coil Pit(deg)": 0.1,
                "Occupation(%)": 0,
            },
            "Mid Winding": {"Turns": 25, "Coil Pit(deg)": 0.1, "Occupation(%)": 0},
            "Inner Winding": {"Turns": 4, "Coil Pit(deg)": 0.1, "Occupation(%)": 0},
            "Settings": {"Units": "mm"},
            "Create Component": {"True": True, "False": False},
        }
        extension_args = {"is_test": True, "choke_config": choke_config}
        assert main(extension_args)

    @pytest.mark.skipif(is_linux, reason="Not supported in Linux.")
    def test_18_via_merging(self, local_scratch):
        from ansys.aedt.core.workflows.hfss3dlayout.via_clustering_extension import main

        file_path = os.path.join(local_scratch.path, "test_via_merging.aedb")
        new_file = os.path.join(local_scratch.path, "__test_via_merging.aedb")
        local_scratch.copyfolder(
            os.path.join(solver_local_path, "example_models", "T45", "test_via_merging.aedb"), file_path
        )
        _input_ = {
            "contour_list": [[[0.143, 0.04], [0.1476, 0.04], [0.1476, 0.03618], [0.143, 0.036]]],
            "is_batch": True,
            "start_layer": "TOP",
            "stop_layer": "INT5",
            "design_name": "test",
            "aedb_path": file_path,
            "new_aedb_path": new_file,
            "test_mode": True,
        }
        assert main(_input_)

    @pytest.mark.skipif(is_linux, reason="Simulation takes too long in Linux machine.")
    def test_19_shielding_effectiveness(self, add_app, local_scratch):
        aedtapp = add_app(application=ansys.aedt.core.Hfss, project_name="se")

        from ansys.aedt.core.workflows.hfss.shielding_effectiveness import main

        assert not main(
            {
                "is_test": True,
                "sphere_size": 0.01,
                "x_pol": 0.0,
                "y_pol": 0.1,
                "z_pol": 1.0,
                "dipole_type": "Electric",
                "frequency_units": "GHz",
                "start_frequency": 0.1,
                "stop_frequency": 1,
                "points": 5,
                "cores": 4,
            }
        )

        aedtapp.modeler.create_waveguide(origin=[0, 0, 0], wg_direction_axis=0)

        assert main(
            {
                "is_test": True,
                "sphere_size": 0.01,
                "x_pol": 0.0,
                "y_pol": 0.1,
                "z_pol": 1.0,
                "dipole_type": "Electric",
                "frequency_units": "GHz",
                "start_frequency": 0.1,
                "stop_frequency": 0.2,
                "points": 2,
                "cores": 2,
            }
        )

        assert len(aedtapp.post.all_report_names) == 2
        aedtapp.close_project(aedtapp.project_name)

    def test_20_layout_design_toolkit_antipad_1(self, add_app, local_scratch):
        from ansys.aedt.core.workflows.hfss3dlayout.layout_design_toolkit import BackendAntipad

        h3d = add_app("ANSYS-HSD_V1", application=ansys.aedt.core.Hfss3dLayout, subfolder=test_subfolder)
        h3d.save_project()
        app_antipad = BackendAntipad(h3d)
        app_antipad.create(selections=["Via79", "Via78"], radius="1mm", race_track=True)
        h3d.close_project()

    def test_20_layout_design_toolkit_antipad_2(self, add_app, local_scratch):
        from ansys.aedt.core.workflows.hfss3dlayout.layout_design_toolkit import BackendAntipad

        h3d = add_app("ANSYS-HSD_V1", application=ansys.aedt.core.Hfss3dLayout, subfolder=test_subfolder)
        h3d.save_project()

        app_antipad = BackendAntipad(h3d)
        app_antipad.create(selections=["Via1", "Via2"], radius="1mm", race_track=False)
        h3d.close_project()

    def test_20_layout_design_toolkit_micro_via(self, add_app, local_scratch):
        from ansys.aedt.core.workflows.hfss3dlayout.layout_design_toolkit import BackendMircoVia

        h3d = add_app("ANSYS-HSD_V1", application=ansys.aedt.core.Hfss3dLayout, subfolder=test_subfolder)
        h3d.save_project()

        app_microvia = BackendMircoVia(h3d)
        app_microvia.create(selection=["v40h20-1"], signal_only=True, angle=15)
        h3d.close_project()
