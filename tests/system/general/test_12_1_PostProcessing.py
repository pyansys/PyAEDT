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
import sys
import uuid

from ansys.aedt.core import Quantity
from ansys.aedt.core.generic.general_methods import is_linux
from ansys.aedt.core.generic.general_methods import read_json
from ansys.aedt.core.generic.settings import settings
from ansys.aedt.core.visualization.plot.pyvista import _parse_aedtplt
from ansys.aedt.core.visualization.plot.pyvista import _parse_streamline
import pytest

from tests import TESTS_GENERAL_PATH
from tests.system.general.conftest import config

test_field_name = "Potter_Horn_231"
test_project_name = "coax_setup_solved_231"
array = "array_simple_231"
sbr_file = "poc_scat_small_solved"
q3d_file = "via_gsg_231"
m2d_file = "m2d_field_lines_test_231"


test_circuit_name = "Switching_Speed_FET_And_Diode"
eye_diagram = "SimpleChannel"
ami = "ami"
test_subfolder = "T12"
settings.enable_pandas_output = True


@pytest.fixture(scope="class")
def aedtapp(add_app):
    app = add_app(project_name=test_project_name, subfolder=test_subfolder)
    yield app
    app.close_project(app.project_name)


class TestClass:

    @pytest.mark.skipif(config["NonGraphical"], reason="Failing on build machine when running in parallel.")
    def test_01_export_model_picture(self, aedtapp, local_scratch):
        path = aedtapp.post.export_model_picture(full_name=os.path.join(local_scratch.path, "images2.jpg"))
        assert path
        path = aedtapp.post.export_model_picture(
            full_name=os.path.join(local_scratch.path, "images3.jpg"),
            show_axis=True,
            show_grid=False,
            show_ruler=True,
        )
        assert os.path.exists(path)
        path = aedtapp.post.export_model_picture(full_name=os.path.join(local_scratch.path, "images4.jpg"))
        assert path

    def test_01B_Field_Plot(self, aedtapp, local_scratch):
        aedtapp.analyze(aedtapp.active_setup)
        assert len(aedtapp.post.available_display_types()) > 0
        assert len(aedtapp.post.available_report_types) > 0
        assert len(aedtapp.post.available_report_quantities()) > 0
        assert isinstance(aedtapp.post.get_all_report_quantities(solution="Setup1 : LastAdaptive"), dict)
        assert len(aedtapp.post.available_report_solutions()) > 0
        cutlist = ["Global:XY", "Global:XZ", "Global:YZ"]
        setup_name = aedtapp.existing_analysis_sweeps[0]
        assert aedtapp.setups[0].is_solved
        quantity_name = "ComplexMag_E"
        frequency = Quantity("5GHz")
        phase = Quantity("180deg")
        intrinsic = {"Freq": frequency, "Phase": phase}
        min_value = aedtapp.post.get_scalar_field_value(quantity_name, "Minimum", setup_name, intrinsics="5GHz")
        plot1 = aedtapp.post.create_fieldplot_cutplane(cutlist, quantity_name, setup_name, intrinsic)
        plot1.IsoVal = "Tone"
        plot1.update_field_plot_settings()
        plot1.update()
        assert aedtapp.post.field_plots[plot1.name].IsoVal == "Tone"
        assert plot1.change_plot_scale(min_value, "30000", scale_levels=50)
        assert aedtapp.post.create_fieldplot_cutplane(cutlist, quantity_name, setup_name, intrinsic, plot1.name)
        assert not aedtapp.post.create_fieldplot_volume("invalid", "Vector_E", setup_name, intrinsic)
        field_plot = aedtapp.post.create_fieldplot_volume("inner", quantity_name, setup_name, intrinsic)
        assert field_plot
        assert aedtapp.post.create_fieldplot_volume("inner", quantity_name, setup_name, intrinsic, field_plot.name)

        volume_plot = aedtapp.post.create_fieldplot_volume("NewObject_IJD39Q", "Vector_E", setup_name, intrinsic)

        export_status = aedtapp.post.export_field_plot(
            plot_name=volume_plot.name, output_dir=aedtapp.working_directory, file_format="case"
        )
        assert export_status
        assert os.path.splitext(export_status)[1] == ".case"
        field_plot = aedtapp.post.create_fieldplot_surface(
            aedtapp.modeler["outer"].faces[0].id, "Mag_E", setup_name, intrinsic
        )
        assert field_plot
        assert aedtapp.post.create_fieldplot_surface(
            aedtapp.modeler["outer"].faces[0].id, "Mag_E", setup_name, intrinsic, field_plot.name
        )
        assert aedtapp.post.create_fieldplot_surface(aedtapp.modeler["outer"], "Mag_E", setup_name, intrinsic)
        assert aedtapp.post.create_fieldplot_surface(aedtapp.modeler["outer"].faces, "Mag_E", setup_name, intrinsic)
        assert not aedtapp.post.create_fieldplot_surface(123123123, "Mag_E", setup_name, intrinsic)
        assert len(aedtapp.setups[0].sweeps[0].frequencies) > 0
        assert isinstance(aedtapp.setups[0].sweeps[0].basis_frequencies, list)
        mesh_file_path = aedtapp.post.export_mesh_obj(setup_name, intrinsic)
        assert os.path.exists(mesh_file_path)
        mesh_file_path2 = aedtapp.post.export_mesh_obj(
            setup_name, intrinsic, export_air_objects=True, on_surfaces=False
        )
        assert os.path.exists(mesh_file_path2)

        min_value = aedtapp.post.get_scalar_field_value("E", "Minimum", setup_name, intrinsics="5GHz", is_vector=True)
        assert isinstance(min_value, float)

    @pytest.mark.skipif(is_linux or sys.version_info < (3, 8), reason="Not running in ironpython")
    def test_01_Animate_plt(self, aedtapp, local_scratch):
        cutlist = ["Global:XY"]
        phases = [str(i * 5) + "deg" for i in range(2)]
        model_gif = aedtapp.post.plot_animated_field(
            quantity="Mag_E",
            assignment=cutlist,
            plot_type="CutPlane",
            setup=aedtapp.nominal_adaptive,
            intrinsics={"Freq": "5GHz", "Phase": "0deg"},
            variation_variable="Phase",
            variations=phases,
            show=False,
            export_gif=True,
            export_path=local_scratch.path,
        )
        assert os.path.exists(model_gif.gif_file)
        setup_name = aedtapp.existing_analysis_sweeps[0]
        intrinsic = {"Freq": "5GHz", "Phase": "180deg"}
        pl1 = aedtapp.post.create_fieldplot_volume("NewObject_IJD39Q", "Mag_E", setup_name, intrinsic)
        model_gif2 = aedtapp.post.animate_fields_from_aedtplt(
            plot_name=pl1.name,
            plot_folder=None,
            variation_variable="Phase",
            variations=phases,
            project_path="",
            export_gif=False,
            show=False,
        )
        model_gif2.gif_file = os.path.join(aedtapp.working_directory, "test2.gif")
        model_gif2.camera_position = [0, 50, 200]
        model_gif2.focal_point = [0, 50, 0]
        model_gif2.animate()
        assert os.path.exists(model_gif2.gif_file)

    @pytest.mark.skipif(config["NonGraphical"], reason="Not running in non-graphical mode")
    def test_02_export_fields(self, aedtapp, local_scratch):
        quantity_name2 = "ComplexMag_H"
        setup_name = "Setup1 : LastAdaptive"
        intrinsic = {"Freq": "5GHz", "Phase": "180deg"}
        vollist = ["NewObject_IJD39Q"]
        plot2 = aedtapp.post.create_fieldplot_volume(vollist, quantity_name2, setup_name, intrinsic)

        aedtapp.post.export_field_jpg(os.path.join(local_scratch.path, "prova2.jpg"), plot2.name, plot2.plot_folder)
        assert os.path.exists(os.path.join(local_scratch.path, "prova2.jpg"))
        assert os.path.exists(plot2.export_image(os.path.join(local_scratch.path, "test_x.jpg")))

    def test_03_create_scattering(self, aedtapp):
        portnames = ["1", "2"]
        assert aedtapp.create_scattering("MyTestScattering")
        setup_name = "Setup2 : Sweep"
        assert not aedtapp.create_scattering("MyTestScattering2", setup_name, portnames, portnames)

    def test_03_get_solution_data(self, aedtapp, local_scratch):
        trace_names = []
        portnames = ["1", "2"]
        for el in portnames:
            for el2 in portnames:
                trace_names.append("S(" + el + "," + el2 + ")")
        families = {"Freq": ["All"]}
        for el in aedtapp.available_variations.nominal_w_values_dict:
            families[el] = aedtapp.available_variations.nominal_w_values_dict[el]

        my_data = aedtapp.post.get_solution_data(expressions=trace_names, variations=families)
        assert my_data
        assert my_data.expressions
        assert len(my_data.data_db10(trace_names[0])) > 0
        assert len(my_data.data_imag(trace_names[0])) > 0
        assert len(my_data.data_real(trace_names[0])) > 0
        assert len(my_data.data_magnitude(trace_names[0])) > 0
        assert my_data.export_data_to_csv(os.path.join(local_scratch.path, "output.csv"))
        assert os.path.exists(os.path.join(local_scratch.path, "output.csv"))
        assert aedtapp.get_touchstone_data("Setup1")

    def test_04_export_touchstone(self, aedtapp, local_scratch):
        setup_name = "Setup1"
        sweep_name = "Sweep"
        aedtapp.export_touchstone(setup_name, sweep_name, os.path.join(local_scratch.path, "Setup1_Sweep.S2p"))
        assert os.path.exists(os.path.join(local_scratch.path, "Setup1_Sweep.S2p"))

        sweep_name = None
        aedtapp.export_touchstone(setup_name, sweep_name, os.path.join(local_scratch.path, "Setup1_Sweep2.S2p"))
        assert os.path.exists(os.path.join(local_scratch.path, "Setup1_Sweep2.S2p"))
        setup_name = None
        aedtapp.export_touchstone(setup_name, sweep_name, os.path.join(local_scratch.path, "Setup1_Sweep3.S2p"))
        assert os.path.exists(os.path.join(local_scratch.path, "Setup1_Sweep3.S2p"))

        assert aedtapp.export_touchstone(setup_name, sweep_name)

    @pytest.mark.skipif(config["desktopVersion"] != "2023.1", reason="Not running in non-graphical mode")
    def test_05_export_report_to_jpg(self, aedtapp, local_scratch):
        aedtapp.post.export_report_to_jpg(local_scratch.path, "MyTestScattering")
        assert os.path.exists(os.path.join(local_scratch.path, "MyTestScattering.jpg"))

    def test_06_export_report_to_csv(self, aedtapp, local_scratch):
        aedtapp.post.export_report_to_csv(
            local_scratch.path,
            "MyTestScattering",
            start="3GHz",
            end="6GHz",
            step="0.12GHz",
            uniform=True,
            use_trace_number_format=False,
        )
        assert os.path.exists(os.path.join(local_scratch.path, "MyTestScattering.csv"))

    def test_06_export_report_to_rdat(self, aedtapp, local_scratch):
        aedtapp.post.export_report_to_file(local_scratch.path, "MyTestScattering", ".rdat")
        assert os.path.exists(os.path.join(local_scratch.path, "MyTestScattering.rdat"))

    def test_07_export_fields_from_Calculator(self, aedtapp, local_scratch):
        file_path = aedtapp.post.export_field_file_on_grid(
            "E",
            "Setup1 : LastAdaptive",
            aedtapp.available_variations.nominal_w_values_dict,
            local_scratch.path,
            grid_stop=[5, 5, 5],
            grid_step=[0.5, 0.5, 0.5],
            is_vector=True,
            intrinsics="5GHz",
        )
        assert os.path.exists(file_path)

        file_path = aedtapp.post.export_field_file_on_grid(
            "E",
            "Setup1 : LastAdaptive",
            aedtapp.available_variations.nominal_w_values_dict,
            grid_stop=[5, 5, 5],
            grid_step=[0.5, 0.5, 0.5],
            is_vector=True,
            intrinsics="5GHz",
        )
        assert os.path.exists(file_path)

        aedtapp.post.export_field_file_on_grid(
            "E",
            "Setup1 : LastAdaptive",
            aedtapp.available_variations.nominal_w_values_dict,
            os.path.join(local_scratch.path, "Efield.fld"),
            grid_stop=[5, 5, 5],
            grid_step=[0.5, 0.5, 0.5],
            is_vector=True,
            intrinsics="5GHz",
        )
        assert os.path.exists(os.path.join(local_scratch.path, "Efield.fld"))

        aedtapp.post.export_field_file_on_grid(
            "Mag_E",
            "Setup1 : LastAdaptive",
            aedtapp.available_variations.nominal_w_values_dict,
            os.path.join(local_scratch.path, "MagEfieldSph.fld"),
            grid_type="Spherical",
            grid_stop=[5, 300, 300],
            grid_step=[5, 50, 50],
            is_vector=False,
            intrinsics="5GHz",
        )
        assert os.path.exists(os.path.join(local_scratch.path, "MagEfieldSph.fld"))

        aedtapp.post.export_field_file_on_grid(
            "Mag_E",
            "Setup1 : LastAdaptive",
            aedtapp.available_variations.nominal_w_values_dict,
            os.path.join(local_scratch.path, "MagEfieldCyl.fld"),
            grid_type="Cylindrical",
            grid_stop=[5, 300, 5],
            grid_step=[5, 50, 5],
            is_vector=False,
            intrinsics="5GHz",
        )
        assert os.path.exists(os.path.join(local_scratch.path, "MagEfieldCyl.fld"))

    def test_07_copydata(self, aedtapp, local_scratch):
        assert aedtapp.post.copy_report_data("MyTestScattering")

    def test_08_manipulate_report(self, aedtapp, local_scratch):
        assert aedtapp.post.rename_report("MyTestScattering", "MyNewScattering")
        assert [plot for plot in aedtapp.post.plots if plot.plot_name == "MyNewScattering"]
        assert not aedtapp.post.rename_report("invalid", "MyNewScattering")

    def test_09_manipulate_report(self, aedtapp, local_scratch):
        plot = aedtapp.post.create_report("dB(S(1,1))")
        assert plot
        assert plot.export_config(os.path.join(local_scratch.path, f"{plot.plot_name}.json"))
        assert aedtapp.post.create_report_from_configuration(
            os.path.join(local_scratch.path, f"{plot.plot_name}.json"), solution_name=aedtapp.nominal_sweep
        )
        assert aedtapp.post.create_report_from_configuration(
            os.path.join(local_scratch.path, f"{plot.plot_name}.json"),
            solution_name=aedtapp.nominal_sweep,
            matplotlib=True,
        )
        assert aedtapp.post.create_report(
            expressions="MaxMagDeltaS",
            variations={"Pass": ["All"]},
            primary_sweep_variable="Pass",
            report_category="Modal Solution Data",
            plot_type="Rectangular Plot",
        )
        new_report = aedtapp.post.reports_by_category.modal_solution("dB(S(1,1))")
        assert new_report.create()

        data = aedtapp.post.get_solution_data("S(1,1)")
        assert data.primary_sweep == "Freq"
        assert data.expressions[0] == "S(1,1)"
        assert len(aedtapp.post.all_report_names) > 0

        new_report = aedtapp.post.reports_by_category.modal_solution("dB(S(1,1))", setup=aedtapp.nominal_sweep)
        assert new_report.create()

    def test_09c_import_into_report(self, aedtapp, local_scratch):
        new_report = aedtapp.create_scattering("import_test")
        csv_file_path = aedtapp.post.export_report_to_csv(local_scratch.path, "import_test")
        rdat_file_path = aedtapp.post.export_report_to_file(local_scratch.path, "import_test", ".rdat")
        plot_name = new_report.plot_name

        trace_names = []
        trace_names.append(new_report.expressions[0])
        families = {"Freq": ["All"]}
        for el in aedtapp.available_variations.nominal_w_values_dict:
            families[el] = aedtapp.available_variations.nominal_w_values_dict[el]

        # get solution data and save in .csv file
        my_data = aedtapp.post.get_solution_data(expressions=trace_names, variations=families)
        my_data.export_data_to_csv(os.path.join(local_scratch.path, "output.csv"))
        csv_solution_data_file_path = os.path.join(local_scratch.path, "output.csv")
        assert not new_report.import_traces(csv_solution_data_file_path, plot_name)

        # test import with correct inputs from csv
        assert new_report.import_traces(csv_file_path, plot_name)
        # test import with correct inputs from rdat
        assert new_report.import_traces(rdat_file_path, plot_name)
        # test import with not existing plot_name
        with pytest.raises(ValueError):
            new_report.import_traces(csv_file_path, "plot_name")
        # test import with random file path
        with pytest.raises(FileExistsError):
            new_report.import_traces(str(uuid.uuid4()), plot_name)
        # test import without plot_name
        with pytest.raises(ValueError):
            new_report.import_traces(csv_file_path, None)

    def test_09d_delete_traces_from_report(self, aedtapp, local_scratch):
        new_report = aedtapp.create_scattering("delete_traces_test")
        traces_to_delete = [new_report.expressions[0]]
        plot_name = new_report.plot_name
        assert new_report.delete_traces(plot_name, traces_to_delete)
        with pytest.raises(ValueError):
            new_report.delete_traces("plot_name", traces_to_delete)
        with pytest.raises(ValueError):
            new_report.delete_traces(plot_name, ["V(out)_Test"])

    def test_09e_add_traces_to_report(self, aedtapp):
        new_report = aedtapp.create_scattering("add_traces_test")
        traces = new_report.get_solution_data().expressions
        assert new_report.add_trace_to_report(traces)
        setup = aedtapp.post.plots[0].setup
        variations = aedtapp.post.plots[0].variations["height"] = "10mm"
        assert not new_report.add_trace_to_report(traces, setup, variations)
        variations = aedtapp.post.plots[0].variations
        assert new_report.add_trace_to_report(traces, setup, variations)
        setup = "Transient"
        assert not new_report.add_trace_to_report(traces, setup, variations)

    def test_09f_update_trace_name(self, aedtapp):
        report = aedtapp.create_scattering("add_traces_test_2")
        old_trace_name = report.traces[0].name
        assert old_trace_name in report.traces[0].aedt_name
        new_name = "update_trace_name_test"
        report.traces[0].name = new_name
        assert new_name in report.traces[0].aedt_name

    def test_09g_update_traces_in_report(self, aedtapp):
        new_report = aedtapp.create_scattering("update_traces_test")
        traces = new_report.get_solution_data().expressions
        assert new_report.update_trace_in_report(traces)
        setup = aedtapp.post.plots[0].setup
        variations = aedtapp.post.plots[0].variations["height"] = "10mm"
        assert not new_report.add_trace_to_report(traces, setup, variations)
        variations = aedtapp.post.plots[0].variations
        assert new_report.update_trace_in_report(traces, setup, variations)

    @pytest.mark.skipif(
        config["desktopVersion"] < "2022.2", reason="Not working in non-graphical mode in version earlier than 2022.2."
    )
    def test_09h_create_monitor(self, aedtapp):  # pragma: no cover
        assert aedtapp.post.create_report("dB(S(1,1))")
        new_report = aedtapp.post.reports_by_category.modal_solution("dB(S(1,1))")
        assert new_report.create()

        assert new_report.add_cartesian_x_marker("3GHz")
        assert new_report.add_cartesian_y_marker("-55")

    @pytest.mark.skipif(
        config["desktopVersion"] < "2022.2",
        reason="Skipped because it cannot run on build machine in non-graphical mode",
    )
    def test_09i_add_line_from_point(self, aedtapp):  # pragma: no cover
        new_report = aedtapp.post.reports_by_category.modal_solution("dB(S(1,1))")
        assert new_report.create()
        assert new_report.add_limit_line_from_points([3, 5, 5, 3], [-50, -50, -60, -60], "GHz")

    @pytest.mark.skipif(
        config["desktopVersion"] < "2022.2", reason="Not working in non-graphical mode in version earlier than 2022.2."
    )
    def test_09l_add_line_from_equation(self, aedtapp):
        new_report = aedtapp.post.reports_by_category.modal_solution("dB(S(1,1))")
        assert new_report.create()
        assert new_report.add_limit_line_from_equation(start_x=1, stop_x=20, step=0.5, units="GHz")

    @pytest.mark.skipif(
        config["desktopVersion"] < "2022.2", reason="Not working in non-graphical mode in version earlier than 2022.2."
    )
    def test_09m_edit_properties(self, aedtapp):
        report = aedtapp.post.create_report("dB(S(1,1))")
        assert report.edit_grid()
        assert report.edit_grid(minor_x=False)
        assert report.edit_grid(major_y=False)
        assert report.edit_grid(major_color=(0, 0, 125))
        assert report.edit_grid(major_color=(0, 255, 0))
        assert report.edit_grid(style_major="Dot")
        assert report.edit_x_axis(
            font="Bangers", font_size=14, italic=True, bold=False, color=(0, 128, 0), display_units=False
        )
        assert report.edit_y_axis(
            font="Bangers", font_size=14, italic=True, bold=False, color=(0, 128, 0), display_units=False
        )
        assert report.edit_x_axis(
            font="Courier", font_size=14, italic=True, bold=False, color=(0, 128, 0), label="Freq"
        )
        assert report.edit_y_axis(
            font="Courier", font_size=14, italic=True, bold=False, color=(0, 128, 0), label="Touchstone"
        )

        assert report.edit_x_axis_scaling(
            linear_scaling=True,
            min_scale="1GHz",
            max_scale="5GHz",
            minor_tick_divs=10,
            min_spacing="0.5GHz",
            units="MHz",
        )
        assert report.edit_y_axis_scaling(
            linear_scaling=False, min_scale="-50", max_scale="10", minor_tick_divs=10, min_spacing="5"
        )
        assert report.edit_legend(
            show_solution_name=True, show_variation_key=False, show_trace_name=False, back_color=(255, 255, 255)
        )
        assert report.edit_header(
            company_name="PyAEDT",
            show_design_name=True,
            font="Arial",
            title_size=12,
            subtitle_size=12,
            italic=False,
            bold=False,
            color=(0, 125, 125),
        )
        assert report.edit_general_settings(
            background_color=(128, 255, 255),
            plot_color=(255, 0, 255),
            enable_y_stripes=True,
            field_width=6,
            precision=6,
            use_scientific_notation=True,
        )

    @pytest.mark.skipif(
        config["desktopVersion"] < "2022.2", reason="Not working in non-graphical mode in version earlier than 2022.2."
    )
    def test_09n_add_line_from_point(self, aedtapp):  # pragma: no cover
        new_report = aedtapp.post.reports_by_category.modal_solution("dB(S(1,1))")
        new_report.create()
        style = new_report.traces[0].LINESTYLE
        trace = new_report.traces[0].TRACETYPE
        symbols = new_report.traces[0].SYMBOLSTYLE

        assert new_report.traces[0].set_trace_properties(
            style=style.Dot, width=5, trace_type=trace.Digital, color=(0, 255, 0)
        )
        assert new_report.traces[0].set_symbol_properties(
            show=True, style=symbols.Box, show_arrows=False, fill=False, color=(0, 0, 255)
        )
        new_report.add_limit_line_from_points([3, 5, 5, 3], [-50, -50, -60, -60], "GHz")
        assert new_report.limit_lines[0].set_line_properties(
            style=style.Dot, width=4, hatch_above=False, violation_emphasis=True, hatch_pixels=1, color=(255, 255, 0)
        )

    @pytest.mark.skipif(
        config["desktopVersion"] < "2022.2", reason="Not working in non-graphical mode in version earlier than 2022.2."
    )
    def test_09o_add_note(self, aedtapp):  # pragma: no cover
        new_report = aedtapp.post.reports_by_category.modal_solution()
        new_report.create()

        new_report.add_note("Test", 8000, 1500)
        assert new_report.notes[0].set_note_properties(
            back_color=(0, 0, 255),
            border_visibility=False,
            border_width=3,
            font="Cambria",
            italic=True,
            bold=True,
            font_size=10,
            color=(255, 0, 0),
        )

    def test_10_delete_report(self, aedtapp):
        plots_number = len(aedtapp.post.plots)
        assert aedtapp.post.delete_report("MyNewScattering")
        assert len(aedtapp.post.plots) == plots_number - 1
        assert aedtapp.post.delete_report()
        assert len(aedtapp.post.plots) == 0

    def test_12_steal_on_focus(self, aedtapp):
        assert aedtapp.post.steal_focus_oneditor()

    @pytest.mark.skipif(is_linux or sys.version_info < (3, 8), reason="Not running in ironpython")
    def test_14_Field_Ploton_cutplanedesignname(self, aedtapp, local_scratch):
        cutlist = ["Global:XY"]
        setup_name = aedtapp.existing_analysis_sweeps[0]
        quantity_name = "ComplexMag_E"
        intrinsic = {"Freq": "5GHz", "Phase": "180deg"}
        aedtapp.logger.info("Generating the plot")
        plot1 = aedtapp.post.create_fieldplot_cutplane(cutlist, quantity_name, setup_name, intrinsic)
        plot1.IsoVal = "Tone"
        assert plot1.update_field_plot_settings()
        aedtapp.logger.info("Generating the image")
        plot_obj = aedtapp.post.plot_field_from_fieldplot(
            plot_name=plot1.name,
            project_path=local_scratch.path,
            mesh_plot=False,
            image_format="jpg",
            view="xy",
            plot_label=plot1.name + " label",
            show=False,
        )
        assert os.path.exists(plot_obj.image_file)
        os.unlink(plot_obj.image_file)
        plot_obj.x_scale = 1.1
        plot_obj.y_scale = 0.9
        plot_obj.z_scale = 0.3
        assert plot_obj.x_scale == 1.1
        assert plot_obj.y_scale == 0.9
        assert plot_obj.z_scale == 0.3

        plot_obj.background_image = os.path.join(local_scratch.path, "file_not_exists.jpg")
        assert not plot_obj.background_image
        plot_obj.convert_fields_in_db = True
        plot_obj.log_multiplier = 20
        plot_obj.plot(plot_obj.image_file, show=False)
        assert os.path.exists(plot_obj.image_file)

        plot_obj = aedtapp.post.plot_field_from_fieldplot(
            plot_name=plot1.name,
            project_path=local_scratch.path,
            mesh_plot=False,
            image_format="jpg",
            view="xy",
            plot_label=plot1.name + " label",
            show=False,
            file_format="aedtplt",
        )
        assert os.path.exists(plot_obj.image_file)
        plot_obj.plot(plot_obj.image_file, show=False)

    @pytest.mark.skipif(is_linux or sys.version_info < (3, 8), reason="Not running in IronPython.")
    def test_14B_Field_Ploton_Vector(self, aedtapp, local_scratch):
        cutlist = ["Global:XY"]
        setup_name = aedtapp.existing_analysis_sweeps[0]
        quantity_name = "Vector_E"
        intrinsic = {"Freq": "5GHz", "Phase": "180deg"}
        aedtapp.logger.info("Generating the plot")
        plot1 = aedtapp.post.create_fieldplot_cutplane(
            cutlist, quantity_name, setup_name, intrinsic, filter_objects=aedtapp.modeler.object_names
        )
        plot1.IsoVal = "Tone"
        assert plot1.update_field_plot_settings()
        aedtapp.logger.info("Generating the image")
        plot_obj = aedtapp.post.plot_field(
            "Vector_E",
            cutlist,
            "CutPlane",
            setup=setup_name,
            intrinsics=intrinsic,
            mesh_on_fields=False,
            view="isometric",
            show=False,
            export_path=local_scratch.path,
            image_format="jpg",
        )
        assert os.path.exists(plot_obj.image_file)
        assert plot_obj.range_min is None
        assert plot_obj.range_max is None
        plot_obj_1 = aedtapp.post.plot_field(
            "Vector_E",
            cutlist,
            "CutPlane",
            setup=setup_name,
            intrinsics=intrinsic,
            mesh_on_fields=False,
            view="isometric",
            show=False,
            export_path=local_scratch.path,
            image_format="jpg",
            log_scale=False,
        )
        assert os.path.exists(plot_obj_1.image_file)
        assert plot_obj_1.range_min is None
        assert plot_obj_1.range_max is None
        plot_obj_2 = aedtapp.post.plot_field(
            "Vector_E",
            cutlist,
            "CutPlane",
            setup=setup_name,
            intrinsics=intrinsic,
            mesh_on_fields=False,
            view="isometric",
            show=False,
            export_path=local_scratch.path,
            image_format="jpg",
            log_scale=False,
            scale_min=0,
            scale_max=10e6,
        )
        assert os.path.exists(plot_obj_2.image_file)
        assert plot_obj_2.range_min == 0
        assert plot_obj_2.range_max == 10e6
        plot_obj_3 = aedtapp.post.plot_field(
            "Vector_E",
            cutlist,
            "CutPlane",
            setup=setup_name,
            intrinsics=intrinsic,
            mesh_on_fields=False,
            view="isometric",
            show=False,
            export_path=local_scratch.path,
            image_format="jpg",
            log_scale=True,
            scale_min=0,
            scale_max=10e6,
        )
        assert os.path.exists(plot_obj_3.image_file)
        assert plot_obj_3.range_min is None
        assert plot_obj_3.range_max is None
        plot_obj_4 = aedtapp.post.plot_field(
            "Vector_E",
            cutlist,
            "CutPlane",
            setup=setup_name,
            intrinsics=intrinsic,
            mesh_on_fields=False,
            view="isometric",
            show=False,
            export_path=local_scratch.path,
            image_format="jpg",
            log_scale=True,
            scale_min=10e6,
            scale_max=0,
        )
        assert os.path.exists(plot_obj_4.image_file)
        assert plot_obj_4.range_min is None
        assert plot_obj_4.range_max is None
        plot_obj_5 = aedtapp.post.plot_field(
            "Vector_E",
            cutlist,
            "CutPlane",
            setup=setup_name,
            intrinsics=intrinsic,
            mesh_on_fields=False,
            view="isometric",
            show=False,
            export_path=local_scratch.path,
            image_format="jpg",
            log_scale=False,
            scale_min=0,
        )
        assert os.path.exists(plot_obj_5.image_file)
        assert plot_obj_5.range_min is None
        assert plot_obj_5.range_max is None

    @pytest.mark.skipif(is_linux or sys.version_info < (3, 8), reason="Not running in ironpython")
    def test_15_export_plot(self, aedtapp, local_scratch):
        obj = aedtapp.post.plot_model_obj(show=False, export_path=os.path.join(local_scratch.path, "image.jpg"))
        assert os.path.exists(obj.image_file)
        obj2 = aedtapp.post.plot_model_obj(
            show=False, export_path=os.path.join(local_scratch.path, "image2.jpg"), plot_as_separate_objects=False
        )
        assert os.path.exists(obj2.image_file)

    @pytest.mark.skipif(is_linux or sys.version_info < (3, 8), reason="Not running in ironpython")
    def test_16_create_field_plot(self, aedtapp):
        cutlist = ["Global:XY"]
        plot = aedtapp.post._create_fieldplot(
            assignment=cutlist,
            quantity="Mag_E",
            setup=aedtapp.nominal_adaptive,
            intrinsics={},
            list_type="CutPlane",
        )
        assert plot

    def test_53_line_plot(self, aedtapp):
        udp1 = [0, 0, 0]
        udp2 = [1, 0, 0]
        setup_name = "Setup1 : LastAdaptive"
        intrinsic = {"Freq": "5GHz", "Phase": "180deg"}
        aedtapp.modeler.create_polyline([udp1, udp2], name="Poly1", non_model=True)
        field_line_plot = aedtapp.post.create_fieldplot_line("Poly1", "Mag_E", setup_name, intrinsic)
        assert field_line_plot
        aedtapp.post.create_fieldplot_line("Poly1", "Mag_E", setup_name, intrinsic, field_line_plot.name)

    def test_55_reload(self, aedtapp, add_app):
        aedtapp.save_project()
        app2 = add_app(project_name=aedtapp.project_name, just_open=True)
        assert len(app2.post.field_plots) == len(aedtapp.post.field_plots)

    def test_58_test_no_report(self, aedtapp):
        assert not aedtapp.post.reports_by_category.eye_diagram()
        assert aedtapp.post.reports_by_category.eigenmode()

    def test_59_test_parse_vector(self):
        out = _parse_aedtplt(os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, "test_vector.aedtplt"))
        assert isinstance(out[0], list)
        assert isinstance(out[1], list)
        assert isinstance(out[2], list)
        assert isinstance(out[3], bool)
        assert _parse_aedtplt(
            os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, "test_vector_no_solutions.aedtplt")
        )

    def test_60_test_parse_vector(self):
        out = _parse_streamline(
            os.path.join(TESTS_GENERAL_PATH, "example_models", test_subfolder, "test_streamline.fldplt")
        )
        assert isinstance(out, list)

    def test_61_export_mesh(self, aedtapp):
        assert os.path.exists(aedtapp.export_mesh_stats("Setup1"))

    def test_67_sweep_from_json(self, aedtapp):
        dict_vals = read_json(
            os.path.join(TESTS_GENERAL_PATH, "example_models", "report_json", "Modal_Report_Simple.json")
        )
        assert aedtapp.post.create_report_from_configuration(report_settings=dict_vals)
        assert aedtapp.post.create_report_from_configuration(report_settings=dict_vals, matplotlib=True)

    @pytest.mark.skipif(
        config["desktopVersion"] < "2022.2", reason="Not working in non graphical in version lower than 2022.2"
    )
    def test_70_sweep_from_json(self, aedtapp):
        assert aedtapp.post.create_report_from_configuration(
            os.path.join(TESTS_GENERAL_PATH, "example_models", "report_json", "Modal_Report.json")
        )
        assert aedtapp.post.create_report_from_configuration(
            os.path.join(TESTS_GENERAL_PATH, "example_models", "report_json", "Modal_Report.json"), matplotlib=True
        )

    def test_74_dynamic_update(self, aedtapp):
        val = aedtapp.post.update_report_dynamically
        aedtapp.post.update_report_dynamically = not val
        assert aedtapp.post.update_report_dynamically != val

    def test_75_tune_derivative(self, aedtapp):
        setup_derivative = aedtapp.setups[1]
        setup_derivative_auto = aedtapp.setups[2]
        assert setup_derivative.set_tuning_offset({"inner_radius": 0.1})
        assert setup_derivative_auto.set_tuning_offset({"inner_radius": 0.1})
