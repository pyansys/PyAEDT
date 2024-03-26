import os.path
from pathlib import Path
import time

from pyaedt.generic.design_types import get_pyaedt_app
from pyaedt.generic.filesystem import search_files
from pyaedt.generic.general_methods import generate_unique_name
from pyaedt.generic.general_methods import pyaedt_function_handler
from pyaedt.generic.general_methods import read_configuration_file
from pyaedt.generic.general_methods import read_csv
from pyaedt.generic.general_methods import write_csv
from pyaedt.generic.pdf import AnsysReport
from pyaedt.generic.spisim import SpiSim
from pyaedt.modeler.geometry_operators import GeometryOperators

default_keys = [
    "file",
    "power",
    "buffer",
    "trise",
    "tfall",
    "UIorBPSValue",
    "BitPattern",
    "R",
    "L",
    "C",
    "DC",
    "V1",
    "V2",
    "TD",
]


class CommonTemplate:
    def __init__(self, report):
        self._name = report["name"]
        self.report_type = report.get("type", "frequency")
        self.config_file = report.get("config", "")
        self.design_name = report.get("design_name", "")
        self.traces = report.get("traces", [])
        self.pass_fail = report.get("pass_fail", False)
        self.group_plots = report.get("group_plots", False)

    @property
    def name(self):
        """Report name.

        Returns
        -------
        str
        """
        return self._name

    @property
    def report_type(self):
        """Report type.

        Returns
        -------
        str
        """
        return self._report_type

    @report_type.setter
    def report_type(self, val):
        self._report_type = val

    @property
    def config_file(self):
        """Configuration file.

        Returns
        -------
        str
        """
        return self._config_file

    @config_file.setter
    def config_file(self, val):
        self._config_file = val

    @property
    def design_name(self):
        """Design name in AEDT.

        Returns
        -------
        str
        """
        return self._design_name

    @design_name.setter
    def design_name(self, val):
        self._design_name = val

    @property
    def traces(self):
        """Trace list.

        Returns
        -------
        list
        """
        return self._traces

    @traces.setter
    def traces(self, val):
        if not isinstance(val, list):
            self._traces = [val]
        else:
            self._traces = val

    @property
    def pass_fail(self):
        """Flag indicating if pass/fail criteria is applied.

        Returns
        -------
        bool
        """
        return self._pass_fail

    @pass_fail.setter
    def pass_fail(self, val):
        self._pass_fail = val


class ReportTemplate(CommonTemplate):
    def __init__(self, report):
        CommonTemplate.__init__(self, report)
        self.group_plots = report.get("group_plots", False)

    @property
    def group_plots(self):
        """Flag indicating if plots are grouped into a single chart or kept independent.

        Returns
        -------
        bool
        """
        return self._group_plots

    @group_plots.setter
    def group_plots(self, val):
        self._group_plots = val


class ParametersTemplate(CommonTemplate):
    def __init__(self, report):
        CommonTemplate.__init__(self, report)
        self.trace_pins = report.get("trace_pins", [])
        self.pass_fail_criteria = report.get("pass_fail", 0)

    @property
    def trace_pins(self):
        """Trace pin coupling list.

        Returns
        -------
        list
        """
        return self._trace_pins

    @trace_pins.setter
    def trace_pins(self, val):
        self._trace_pins = val

    @property
    def pass_fail_criteria(self):
        """Pass/fail criteria.

        Returns
        -------
        float, int
        """
        return self._pass_fail_criteria

    @pass_fail_criteria.setter
    def pass_fail_criteria(self, val):
        self._pass_fail_criteria = val


class VirtualCompliance:
    """Provides automatic report generation with pass/fail criteria on virtual compliance.

    Parameters
    ----------
    desktop : :class:``pyaedt.desktop.Desktop``
        Desktop object.
    template : str
        Full path to the template. Supported formats are JSON and TOML.
    project_path : str, optional
        Full path to the project. If a path is provided, the project field inside the template is ignored.
    """

    def __init__(self, desktop, template, pdf_template=None, report_logo=None):
        self._add_project_info = True
        self._add_specs_info = False
        self._specs_folder = None
        self._use_portrait = True
        self._template = template
        self._template_name = "Compliance"
        self._template_folder = os.path.dirname(template)
        self._project_file = None
        self._reports = {}
        self._parameters = {}
        self._project_name = None
        self._output_folder = None
        self._pdf_template = pdf_template
        self._report_logo = report_logo
        self._parse_template()
        self._desktop_class = desktop

    @pyaedt_function_handler()
    def load_project(self):
        """Open the aedt project in Electronics Desktop.

        Returns
        -------
        bool
        """
        if not self._project_file:
            self._desktop_class.logger.error("Project path has not been provided.")
            return False
        self._desktop_class.load_project(self._project_file)
        project = self._desktop_class.odesktop.GetActiveProject()
        self._project_name = project.GetName()
        self._output_folder = os.path.join(
            project.GetPath(), self._project_name + ".pyaedt", generate_unique_name(self._template_name)
        )
        os.makedirs(self._output_folder, exist_ok=True)
        return True

    @property
    def pdf_template(self):
        """Template file to use to generate pdf report.

        Returns
        -------
        str
        """
        return self._pdf_template

    @pdf_template.setter
    def pdf_template(self, val):
        self._pdf_template = val

    @property
    def report_logo(self):
        """Report company logo.

        Returns
        -------
        str
        """
        return self._report_logo

    @report_logo.setter
    def report_logo(self, val):
        self._report_logo = val

    @property
    def reports(self):
        """Reports available in the virtual compliance.

        Returns
        -------
        Dict[str, :class:`pyaedt.generic.compliance.ReportTemplate`]
        """
        return self._reports

    @reports.setter
    def reports(self, val):
        self._reports = val

    @property
    def parameters(self):
        """Parameters available in the Virtual complaince.

        Returns
        -------
        Dict[str, :class:`pyaedt.generic.compliance.ParametersTemplate`]
        """
        return self._parameters

    @parameters.setter
    def parameters(self, val):
        self._parameters = val

    @property
    def add_project_info(self):
        return self._add_project_info

    @add_project_info.setter
    def add_project_info(self, val):
        self._add_project_info = val

    @property
    def add_specs_info(self):
        return self._add_specs_info

    @add_specs_info.setter
    def add_specs_info(self, val):
        self._add_specs_info = val

    @property
    def specs_folder(self):
        return self._specs_folder

    @specs_folder.setter
    def specs_folder(self, val):
        self._specs_folder = val
        if self._specs_folder and os.path.exists(os.path.join(self._template_folder, self._specs_folder)):
            self._specs_folder = os.path.join(self._template_folder, self._specs_folder)

    @property
    def template_name(self):
        return self._template_name

    @template_name.setter
    def template_name(self, val):
        self._template_name = val

    @property
    def project_file(self):
        return self._project_file

    @project_file.setter
    def project_file(self, val):
        self._project_file = val

    @property
    def project_name(self):
        return Path(self.project_file).stem

    @property
    def use_portrait(self):
        return self._use_portrait

    @use_portrait.setter
    def use_portrait(self, val):
        self._use_portrait = val

    @pyaedt_function_handler()
    def _parse_template(self):
        if self._template:
            self.local_config = read_configuration_file(self._template)
            if "general" in self.local_config:
                self._add_project_info = self.local_config["general"].get("add_project_info", True)
                self._add_specs_info = self.local_config["general"].get("add_specs_info", False)
                self._specs_folder = self.local_config["general"].get("specs_folder", "")
                self._template_name = self.local_config["general"].get("name", "Compliance")
                self._project_file = self.local_config["general"].get("project", None)
                self._use_portrait = self.local_config["general"].get("use_portrait", True)
            if "reports" in self.local_config:
                for report in self.local_config["reports"]:
                    self._parse_reports(report)
            if "parameters" in self.local_config:
                for parameter in self.local_config["parameters"]:
                    self._parse_reports(parameter, True)

    @pyaedt_function_handler()
    def _parse_reports(self, report, is_parameter=False):
        name = report["name"]

        if name in self._reports.values():
            self._desktop_class.logger.warning(f"{name} already exists. The name must be unique.")
        else:
            if is_parameter:
                self._parameters[report["name"]] = ParametersTemplate(report)
            else:
                self._reports[report["name"]] = ReportTemplate(report)

    @pyaedt_function_handler()
    def _get_frequency_range(self, data_list, f1, f2):
        filtered_range = [(freq, db_value) for freq, db_value in data_list if f1 <= freq <= f2]
        return filtered_range

    @pyaedt_function_handler()
    def _check_test_value(self, filtered_range, test_value, hatch_above):
        worst = 1e9
        worst_f = 0
        val = None
        for filt, t in zip(filtered_range, test_value):

            if hatch_above:
                if t - filt[1] < worst:
                    worst = t - filt[1]
                    worst_f = filt[0]
                    val = filt[1]
            else:
                if filt[1] - t < worst:
                    worst = filt[1] - t
                    worst_f = filt[0]
                    val = filt[1]
        if worst < 0:
            result = "FAIL"
        else:
            result = "PASS"
        return round(val, 5), round(worst_f, 5), result

    @pyaedt_function_handler()
    def add_aedt_report(self, name, report_type, config_file, design_name, traces, setup_name=None, pass_fail=True):
        """Add a new custom aedt report to the compliance.

        Parameters
        ----------
        name : str
            Name of the report.
        report_type : str
            Report type. Options are "contour eye diagram", "eye diagram", "frequency", "statistical eye", and "time".
        config_file : str
            Path to the config file.
        design_name : str
            Name of the AEDT design to be used to create the project.
        traces : list
           Traces to be added.
        setup_name : str, optional
            Name of the setup to use. If None, the nominal sweep will be used.
        pass_fail : bool, optional
            Whether if the pass/fail criteria has to be used to check the compliance or not.

        Returns
        -------

        """
        new_rep = {
            "name": name,
            "type": report_type,
            "config": config_file,
            "design_name": design_name,
            "traces": traces,
            "setup_name": setup_name,
            "pass_fail": pass_fail,
        }
        self._reports[name] = ReportTemplate(new_rep)

    @pyaedt_function_handler()
    def _get_sweep_name(self, design, solution_name):
        sweep_name = None
        if solution_name:
            solution_names = [
                i for i in design.existing_analysis_sweeps if solution_name == i or i.startswith(solution_name + " ")
            ]
            if solution_names:  # pragma: no cover
                sweep_name = solution_names[0]
        return sweep_name

    @pyaedt_function_handler()
    def _create_aedt_reports(self, pdf_report):
        start = True
        _design = None
        first_trace = True
        for template_report in self._reports.values():
            config_file = template_report.config_file
            if not os.path.exists(config_file) and not os.path.exists(os.path.join(self._template_folder, config_file)):
                self._desktop_class.logger.error(f"{config_file} is not found.")
                continue
            name = template_report.name
            traces = template_report.traces
            pass_fail = template_report.pass_fail
            design_name = template_report.design_name
            report_type = template_report.report_type
            group = template_report.group_plots
            if _design and _design.design_name != design_name or _design is None:
                try:
                    _design = get_pyaedt_app(self._project_name, design_name)
                except Exception:  # pragma: no cover
                    self._desktop_class.logger.error(f"Failed to retrieve design {design_name}")
                    continue
            if os.path.exists(os.path.join(self._template_folder, config_file)):
                config_file = os.path.join(self._template_folder, config_file)
            if not os.path.exists(config_file):
                continue
            local_config = read_configuration_file(config_file)
            if start:
                pdf_report.add_section()
                pdf_report.add_chapter("Compliance Results")
                start = False
            if group and report_type in ["frequency", "time"]:
                local_config["expressions"] = {trace: {} for trace in traces}
                image_name = name
                sw_name = self._get_sweep_name(_design, local_config.get("solution_name", None))
                _design.logger.info(f"Creating report {name}")
                aedt_report = _design.post.create_report_from_configuration(
                    input_dict=local_config, solution_name=sw_name
                )
                if not aedt_report:  # pragma: no cover
                    _design.logger.error(f"Failed to create report {name}")
                    continue
                aedt_report.hide_legend()
                time.sleep(1)
                if _design.post.export_report_to_jpg(self._output_folder, aedt_report.plot_name):
                    time.sleep(1)
                    if not first_trace:
                        pdf_report.add_page_break()
                    else:
                        first_trace = False
                    pdf_report.add_sub_chapter(f"{name}")
                    sleep_time = 10
                    while sleep_time > 0:
                        # noinspection PyBroadException
                        try:
                            if self.use_portrait:
                                pdf_report.add_image(
                                    os.path.join(self._output_folder, aedt_report.plot_name + ".jpg"),
                                    f"Plot {report_type} for {name}",
                                    width=pdf_report.epw - 50,
                                )
                            else:
                                pdf_report.add_image(
                                    os.path.join(self._output_folder, aedt_report.plot_name + ".jpg"),
                                    f"Plot {report_type} for {name}",
                                    height=pdf_report.eph - 100,
                                )

                            sleep_time = 0
                        except Exception:  # pragma: no cover
                            time.sleep(1)
                            sleep_time -= 1
                if (
                    pass_fail and report_type in ["frequency", "time"] and local_config.get("limitLines", None)
                ):  # pragma: no cover
                    _design.logger.info(f"Checking lines violations")
                    table = self._add_lna_violations(aedt_report, pdf_report, image_name, local_config)
                    write_csv(os.path.join(self._output_folder, f"{name}_pass_fail.csv"), table)
                if self.local_config.get("delete_after_export", True):
                    aedt_report.delete()
                _design.logger.info(f"Successfully parsed report {name}")
            else:
                for trace in traces:
                    local_config["expressions"] = {trace: {}}
                    image_name = name + f"_{trace}"
                    sw_name = self._get_sweep_name(_design, local_config.get("solution_name", None))
                    _design.logger.info(f"Creating report {name} for trace {trace}")
                    aedt_report = _design.post.create_report_from_configuration(
                        input_dict=local_config, solution_name=sw_name
                    )
                    if report_type != "contour eye diagram":
                        aedt_report.hide_legend()
                    time.sleep(1)
                    out = _design.post.export_report_to_jpg(self._output_folder, aedt_report.plot_name)
                    time.sleep(1)
                    if out:
                        if not first_trace:
                            pdf_report.add_page_break()
                        else:
                            first_trace = False

                        pdf_report.add_sub_chapter(f"{name} for trace {trace}")
                        sleep_time = 10
                        while sleep_time > 0:
                            # noinspection PyBroadException
                            try:
                                if self.use_portrait:
                                    pdf_report.add_image(
                                        os.path.join(self._output_folder, aedt_report.plot_name + ".jpg"),
                                        f"Plot {report_type} for trace {trace}",
                                        width=pdf_report.epw - 40,
                                    )
                                else:
                                    pdf_report.add_image(
                                        os.path.join(self._output_folder, aedt_report.plot_name + ".jpg"),
                                        f"Plot {report_type} for trace {trace}",
                                        height=pdf_report.eph - 100,
                                    )

                                sleep_time = 0
                            except Exception:  # pragma: no cover
                                time.sleep(1)
                                sleep_time -= 1
                        if pass_fail:
                            if report_type in ["frequency", "time"] and local_config.get("limitLines", None):
                                _design.logger.info(f"Checking lines violations")
                                table = self._add_lna_violations(aedt_report, pdf_report, image_name, local_config)
                            elif report_type == "statistical eye" and local_config["eye_mask"]:
                                _design.logger.info(f"Checking eye violations")
                                table = self._add_statistical_violations(
                                    aedt_report, pdf_report, image_name, local_config
                                )
                            elif report_type == "eye diagram" and local_config["eye_mask"]:
                                _design.logger.info(f"Checking eye violations")
                                table = self._add_eye_diagram_violations(aedt_report, pdf_report, image_name)
                            elif report_type == "contour eye diagram":
                                _design.logger.info(f"Checking eye violations")
                                table = self._add_contour_eye_diagram_violations(
                                    aedt_report, pdf_report, image_name, local_config
                                )
                            write_csv(os.path.join(self._output_folder, f"{name}{trace}_pass_fail.csv"), table)

                        if report_type in ["eye diagram", "statistical eye"]:
                            _design.logger.info(f"Adding eye measurements")
                            table = self._add_eye_measurement(aedt_report, pdf_report, image_name)
                            write_csv(os.path.join(self._output_folder, f"{name}{trace}_eye_meas.csv"), table)
                        if self.local_config.get("delete_after_export", True):
                            aedt_report.delete()
                        _design.logger.info(f"Successfully parsed report {name} for trace {trace}")

                    else:  # pragma: no cover
                        msg = f"Failed to create the report. Check {config_file} configuration file."
                        self._desktop_class.logger.error(msg)

    @pyaedt_function_handler()
    def _create_parameters(self, pdf_report):
        start = True
        _design = None

        for template_report in self._parameters.values():
            config_file = template_report.config_file
            if not os.path.exists(config_file):
                config_file = os.path.join(self._template_folder, config_file)
            if not os.path.exists(config_file):
                self._desktop_class.logger.error(f"{config_file} not found.")
                continue
            name = template_report.name
            pass_fail_criteria = template_report.pass_fail_criteria
            design_name = template_report.design_name
            if _design and _design.design_name != design_name or _design is None:
                _design = get_pyaedt_app(self._project_name, design_name)

            if start:
                pdf_report.add_section()
                pdf_report.add_chapter("Parameters Results")
                start = False
            spisim = SpiSim(None)
            if name == "erl":
                pdf_report.add_sub_chapter("Effective Return Loss")
                table_out = [["ERL", "Value", "Pass/Fail"]]
                traces = template_report.traces
                trace_pins = template_report.trace_pins
                for trace_name, trace_pin in zip(traces, trace_pins):
                    spisim.touchstone_file = _design.export_touchstone()
                    if not isinstance(trace_pin[0], int):
                        try:
                            ports = list(_design.excitations.keys())
                            thrus4p = [ports.index(i) for i in trace_pin]
                            trace_pin = thrus4p
                        except IndexError:
                            _design.logger.error("Port not found.")
                    erl_value = spisim.compute_erl(specify_through_ports=trace_pin, config_file=config_file)
                    if erl_value:
                        table_out.append([trace_name, erl_value, "PASS" if pass_fail_criteria else "FAIL"])
                pdf_report.add_table(
                    "Effective Return Losses",
                    table_out,
                )

    @pyaedt_function_handler()
    def _add_lna_violations(self, report, pdf_report, image_name, local_config):
        font_table = [["", None]]
        trace_data = report.get_solution_data()
        pass_fail_table = [
            [
                "Check Zone",
                "Trace Name",
                "Criteria",
                "Pass/Fail limit value",
                "Worst simulated value",
                "X at worst value",
                "Test Result",
            ]
        ]
        if not trace_data:  # pragma: no cover
            msg = "Failed to get solution data. Check if the design is solved or if the report data is correct."
            self._desktop_class.logger.error(msg)
            return pass_fail_table
        for trace_name in trace_data.expressions:
            trace_values = [(k[0], v) for k, v in trace_data.full_matrix_real_imag[0][trace_name].items()]
            for limit_v in local_config["limitLines"].values():
                yy = 0
                zones = 0
                while yy < len(limit_v["xpoints"]) - 1:
                    if limit_v["xpoints"][yy] != limit_v["xpoints"][yy + 1]:
                        zones += 1
                        result_range = self._get_frequency_range(
                            trace_values, limit_v["xpoints"][yy], limit_v["xpoints"][yy + 1]
                        )
                        freq = [i[0] for i in result_range]
                        slope = (limit_v["ypoints"][yy + 1] - limit_v["ypoints"][yy]) / (freq[-1] - freq[0])
                        ypoints = []
                        for i in range(len(freq)):
                            if slope != 0:
                                ypoints.append(limit_v["ypoints"][yy] + (freq[i] - freq[0]) / slope)
                            else:
                                ypoints.append(limit_v["ypoints"][yy])
                        hatch_above = False
                        if limit_v.get("hatch_above", True):
                            hatch_above = True
                        test_value = limit_v["ypoints"][yy]
                        range_value, x_value, result_value = self._check_test_value(result_range, ypoints, hatch_above)
                        units = limit_v.get("y_units", "")
                        xunits = limit_v.get("x_units", "")
                        mystr = f"Zone  {zones}"
                        font_table.append([None, [255, 0, 0]] if result_value == "FAIL" else ["", None])
                        pass_fail_table.append(
                            [
                                mystr,
                                trace_name,
                                "Upper Limit" if hatch_above else "Lower Limit",
                                f"{test_value}{units}",
                                f"{range_value}{units}",
                                f"{x_value}{xunits}",
                                result_value,
                            ]
                        )
                    yy += 1
        if not self._use_portrait:
            pdf_report.add_section()
        pdf_report.add_table(
            f"Pass Fail Criteria on {image_name}", pass_fail_table, font_table, col_widths=[20, 45, 25, 25, 25, 25, 25]
        )
        return pass_fail_table

    @pyaedt_function_handler()
    def _add_statistical_violations(self, report, pdf_report, image_name, local_config):
        font_table = [["", None]]
        pass_fail_table = [["Pass Fail Criteria", "Test Result"]]
        sols = report.get_solution_data()
        if not sols:  # pragma: no cover
            msg = "Failed to get Solution Data. Check if the design is solved or the report data are correct."
            self._desktop_class.logger.error(msg)
            return
        mag_data = {i: k for i, k in sols.full_matrix_real_imag[0][sols.expressions[0]].items() if k > 0}
        mystr = "Eye Mask Violation:"
        result_value = "PASS"
        points_to_check = [i[::-1] for i in local_config["eye_mask"]["points"]]
        points_to_check = [[i[0] for i in points_to_check], [i[1] for i in points_to_check]]
        num_failed = 0
        min_x = min(points_to_check[0])
        max_x = max(points_to_check[0])
        min_y = min(points_to_check[1])
        max_y = max(points_to_check[1])
        for point in mag_data:
            if not (min_x < point[0] < max_x and min_y < point[1] < max_y):
                continue
            if GeometryOperators.point_in_polygon(point, points_to_check) >= 0:
                result_value = "FAIL"
                num_failed += 1
                # break
        font_table.append([None, [255, 0, 0]] if result_value == "FAIL" else ["", None])
        if result_value == "FAIL":
            result_value = f"FAIL on {num_failed} points."
        pass_fail_table.append([mystr, result_value])

        if local_config["eye_mask"]["enable_limits"]:
            mystr = "Upper/Lower Mask Violation:"
            for point in mag_data:
                if (
                    point[1] > local_config["eye_mask"]["upper_limit"]
                    or point[1] < local_config["eye_mask"]["lower_limit"]
                ):
                    result_value = "FAIL"
                    break
            font_table.append([None, [255, 0, 0]] if result_value == "FAIL" else ["", None])
            pass_fail_table.append([mystr, result_value])
        if not self._use_portrait:
            pdf_report.add_section()
        pdf_report.add_table(f"Pass Fail Criteria on {image_name}", pass_fail_table, font_table)
        return pass_fail_table

    @pyaedt_function_handler()
    def _add_eye_diagram_violations(self, report, pdf_report, image_name):
        try:
            out_eye = os.path.join(self._output_folder, "violations.tab")
            viol = report.export_mask_violation(out_eye)
        except Exception:  # pragma: no cover
            viol = None
        font_table = [["", None]]
        pass_fail_table = [["Pass Fail Criteria", "Test Result"]]
        mystr1 = "Eye Mask Violation:"
        result_value_mask = "PASS"
        mystr2 = "Upper/Lower Mask Violation:"
        result_value_upper = "PASS"
        if os.path.exists(viol):
            try:  # pragma: no cover
                import pandas as pd
            except ImportError:  # pragma: no cover
                return
            file_in = pd.read_table(viol, header=0)

            for k in file_in.values:
                if k[3].strip() == "Central":
                    result_value_mask = "FAIL"
                elif k[3].strip() in ["Upper", "Lower"]:
                    result_value_upper = "FAIL"
        pass_fail_table.append([mystr1, result_value_mask])
        font_table.append([None, [255, 0, 0]] if result_value_mask == "FAIL" else ["", None])
        pass_fail_table.append([mystr2, result_value_upper])
        font_table.append([None, [255, 0, 0]] if result_value_upper == "FAIL" else ["", None])
        if not self._use_portrait:
            pdf_report.add_section()
        pdf_report.add_table(f"Pass Fail Criteria on {image_name}", pass_fail_table, font_table)
        return pass_fail_table

    @pyaedt_function_handler()
    def _add_contour_eye_diagram_violations(self, report, pdf_report, image_name, local_config):
        pass_fail_table = [["Pass Fail Criteria", "Test Result"]]
        sols = report.get_solution_data()
        if not sols:  # pragma: no cover
            msg = "Failed to get Solution Data. Check if the design is solved or the report data are correct."
            self._desktop_class.logger.error(msg)
            return
        bit_error_rates = [1e-3, 1e-6, 1e-9, 1e-12]
        font_table = [["", None]]
        points_to_check = [i[::-1] for i in local_config["eye_mask"]["points"]]
        points_to_check = [[i[0] for i in points_to_check], [i[1] for i in points_to_check]]
        for ber in bit_error_rates:
            mag_data = [
                k for k, i in sols.full_matrix_real_imag[0][sols.expressions[0]].items() if ber / 990 < abs(i) <= ber
            ]
            mystr = f"Eye Mask Violation BER at {ber}:"
            result_value = "PASS"
            if not mag_data:
                result_value = "FAILED. No BER obtained"
            for point in mag_data:
                if GeometryOperators.point_in_polygon(point, points_to_check) >= 0:
                    result_value = "FAILED. Mask Violation"
                    break
            font_table.append([None, [255, 0, 0]] if "FAIL" in result_value else ["", None])
            pass_fail_table.append([mystr, result_value])
        if not self._use_portrait:
            pdf_report.add_section()
        pdf_report.add_table(f"Pass Fail Criteria on {image_name}", pass_fail_table, font_table)
        return pass_fail_table

    @pyaedt_function_handler()
    def _add_eye_measurement(self, report, pdf_report, image_name):
        report.add_all_eye_measurements()
        out_eye = os.path.join(self._output_folder, "eye_measurements_{}.csv".format(image_name))
        report._post.oreportsetup.ExportTableToFile(report.plot_name, out_eye, "Legend")
        report.clear_all_eye_measurements()
        table = read_csv(out_eye)
        new_table = []
        for line in table:
            new_table.append(line)
        if not self._use_portrait:
            pdf_report.add_section()
        pdf_report.add_table(f"Eye Measurements on {image_name}", new_table)
        return new_table

    @pyaedt_function_handler()
    def add_specs_to_report(self, folder):
        """Add specs to the report from a given folder.
        All images in such folder will be added to the report.

        Parameters
        ----------
        folder : str
            Folder relative path to compliance report or absolute path.
        """
        if folder:
            self._specs_folder = folder
            self._add_specs_info = True

    @pyaedt_function_handler()
    def _create_project_info(self, report):
        report.add_section()
        designs = []
        _design = None
        for template_report in self.reports.values():
            design_name = template_report.design_name
            if design_name in designs:
                continue
            designs.append(design_name)
            if _design and _design.design_name != design_name or _design is None:
                _design = get_pyaedt_app(self._project_name, design_name)
            report.add_project_info(_design)

            report.add_empty_line(3)

            if _design.design_type == "Circuit Design":
                components = [["Reference Designator", "Parameters"]]
                for element in _design.modeler.components.components.values():
                    if "refdes" in dir(element):
                        pars = []
                        for el, val in element.parameters.items():
                            if el in self.local_config.get("project_info_keys", default_keys) and el not in [
                                "DefaultNetlist",
                                "CoSimulator",
                                "NexximNetList",
                                "CosimDefinition",
                            ]:
                                pars.append(f"{el}={val}")
                        if pars:
                            components.append([element.refdes, ", ".join(pars)])
                if len(components) > 1:
                    report.add_sub_chapter(f"Design Information: {_design.design_name}")
                    report.add_table("Components", components, col_widths=[75, 275])

    @pyaedt_function_handler()
    def create_compliance_report(self, file_name="compliance_test.pdf", close_project=True):
        """Create the Virtual Compliance report.

        Parameters
        ----------
        file_name : str
            Output file name.
        close_project : bool, optional
            Whether to close the project at the end of the report generation or not. Default is `True`.

        Returns
        -------
        str
            Path to the output file.
        """
        if not self._project_name:
            self.load_project()

        report = AnsysReport(tempplate_json_file=self.pdf_template)
        if self.report_logo and os.path.exists(self.report_logo):
            report.logo_name = self.report_logo
        report.aedt_version = self._desktop_class.aedt_version_id
        report.design_name = self._template_name
        report.report_specs.table_font_size = 7
        report.use_portrait = self._use_portrait
        report.create()
        if self._specs_folder and self._add_specs_info:
            report.add_chapter("Specifications Info")
            file_list = search_files(
                self._specs_folder,
            )
            for file in file_list:
                if os.path.splitext(file)[1] in [".jpg", ".png", ".gif"]:
                    # noinspection PyBroadException
                    try:
                        caption = " ".join(os.path.splitext(os.path.split(file)[-1])[0].split("_"))
                    except Exception:  # pragma: no cover
                        caption = os.path.split(file)[-1]
                    if self.use_portrait:
                        report.add_image(file, caption=caption, width=report.epw - 50)
                    else:
                        report.add_image(file, caption=caption, height=report.eph - 100)

        self._create_parameters(report)
        self._create_aedt_reports(report)
        if self._add_project_info:
            self._create_project_info(report)
        report.add_toc()
        output = report.save_pdf(self._output_folder, file_name=file_name)
        if close_project:
            self._desktop_class.odesktop.CloseProject(self.project_name)
        if output:
            self._desktop_class.logger.info(f"Report has been saved in {output}")
        return output
