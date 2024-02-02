import json
import os.path
import time

from pyaedt.generic.design_types import get_pyaedt_app
from pyaedt.generic.filesystem import search_files
from pyaedt.generic.general_methods import generate_unique_name
from pyaedt.generic.general_methods import read_csv
from pyaedt.generic.pdf import AnsysReport
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


class VirtualCompliance:
    def __init__(self, desktop, template):
        self._add_project_info = True
        self._add_specs_info = False
        self._specs_folder = None
        self._template = template
        self._template_name = "Compliance"
        self._template_folder = os.path.dirname(template)
        self._reports = {}
        self._parse_template()
        self._desktop_class = desktop
        if self._project_file:
            self._desktop_class.load_project(self._project_file)
        project = self._desktop_class.odesktop.GetActiveProject()
        self._project_name = project.GetName()
        self._output_folder = os.path.join(
            project.GetPath(), self._project_name + ".pyaedt", generate_unique_name(self._template_name)
        )
        os.makedirs(self._output_folder, exist_ok=True)

    def _parse_template(self):
        if self._template:
            with open(self._template) as f:
                self.local_config = json.load(f)
                if "general" in self.local_config:
                    self._add_project_info = self.local_config["general"].get("add_project_info", True)
                    self._add_specs_info = self.local_config["general"].get("add_specs_info", False)
                    self._specs_folder = self.local_config["general"].get("specs_folder", "")
                    if self._specs_folder and os.path.exists(os.path.join(self._template_folder, self._specs_folder)):
                        self._specs_folder = os.path.join(self._template_folder, self._specs_folder)
                    self._template_name = self.local_config["general"].get("name", "Compliance")
                    self._project_file = self.local_config["general"].get("project", None)

    def _parse_reports(self):
        if "reports" in self.local_config:
            for report in self.local_config["reports"]:
                self._create_aedt_report(
                    report["name"],
                    report["type"],
                    report["config"],
                    report["design_name"],
                    report["traces"],
                    report["pass_fail"],
                )

    def _get_frequency_range(self, data_list, f1, f2):
        filtered_range = [(freq, db_value) for freq, db_value in data_list if f1 <= freq <= f2]
        return filtered_range

    def _check_test_value(self, filtered_range, test_value, hatch_above):
        for _, db_value in filtered_range:
            if hatch_above:
                if db_value >= test_value:
                    return db_value
            elif db_value <= test_value:
                return db_value
        return None

    def add_aedt_report(self, name, report_type, config_file, design_name, traces, setup_name=None, pass_fail=True):
        """Add a new custom aedt report to the compliance.

        Parameters
        ----------
        name : str
            Name of the report.
        report_type : str
            Report type. It can be "frequency", "eye diagram", "statistical eye", "contour eye diagram", "transient".
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
        self.local_config.reports.append(
            {
                "name": name,
                "type": report_type,
                "config": config_file,
                "design_name": design_name,
                "traces": traces,
                "setup_name": setup_name,
                "pass_fail": pass_fail,
            }
        )

    def _get_sweep_name(self, design, solution_name):
        sweep_name = None
        if solution_name:
            solution_names = [
                i for i in design.existing_analysis_sweeps if solution_name == i or i.startswith(solution_name + " ")
            ]
            if solution_names:
                sweep_name = solution_names[0]
        return sweep_name

    def _create_aedt_reports(self, pdf_report):
        start = True
        _design = None
        first_trace = True
        for template_report in self.local_config["reports"]:
            config_file = template_report["config"]
            name = template_report["name"]
            traces = template_report["traces"]
            pass_fail = template_report["pass_fail"]
            design_name = template_report["design_name"]
            report_type = template_report["type"]
            if _design and _design.design_name != design_name or _design is None:
                _design = get_pyaedt_app(self._project_name, design_name)

            if os.path.exists(os.path.join(self._template_folder, config_file)):
                config_file = os.path.join(self._template_folder, config_file)
            if not os.path.exists(config_file):
                continue
            with open(config_file) as f:
                local_config = json.load(f)
            if start:
                pdf_report.add_section(portrait=False)
                pdf_report.add_chapter("Compliance Results")
                start = False
            for trace in traces:
                local_config["expressions"] = {trace: {}}
                image_name = name + f"_{trace}"
                sw_name = self._get_sweep_name(_design, local_config.get("solution_name", None))
                aedt_report = _design.post.create_report_from_configuration(
                    input_dict=local_config, solution_name=sw_name
                )
                if report_type != "contour eye diagram":
                    aedt_report.hide_legend()
                out = _design.post.export_report_to_jpg(self._output_folder, aedt_report.plot_name)
                time.sleep(1)
                if out:
                    if not first_trace:
                        pdf_report.add_section(portrait=False)
                    else:
                        first_trace = False
                    pdf_report.add_sub_chapter(f"{name} for trace {trace}")
                    sleep_time = 10
                    while sleep_time > 0:
                        # noinspection PyBroadException
                        try:
                            pdf_report.add_image(
                                os.path.join(self._output_folder, aedt_report.plot_name + ".jpg"),
                                f"Plot {report_type} for trace {trace}",
                                width=pdf_report.epw - 10,
                            )
                            sleep_time = 0
                        except Exception:
                            time.sleep(1)
                            sleep_time -= 1
                    if pass_fail:
                        if report_type == "frequency" and local_config["limitLines"]:
                            self._add_lna_violations(aedt_report, pdf_report, image_name, local_config)
                        elif report_type == "statistical eye" and local_config["eye_mask"]:
                            self._add_statistical_violations(aedt_report, pdf_report, image_name, local_config)
                        elif report_type == "eye diagram" and local_config["eye_mask"]:
                            self._add_eye_diagram_violations(aedt_report, pdf_report, image_name)
                        elif report_type == "contour eye diagram":
                            self._add_contour_eye_diagram_violations(aedt_report, pdf_report, image_name, local_config)

                    if report_type in ["eye diagram", "statistical eye"]:
                        self._add_eye_measurement(aedt_report, pdf_report, image_name)

                    if self.local_config.get("delete_after_export", True):
                        aedt_report.delete()
                else:  # pragma: no cover
                    msg = f"Failed to create the report. Check {config_file} configuration file."
                    self._desktop_class.logger.error(msg)

    def _add_lna_violations(self, report, pdf_report, image_name, local_config):
        font_table = [["", None]]
        trace_data = report.get_solution_data()
        if not trace_data:  # pragma: no cover
            msg = "Failed to get Solution Data. Check if the design is solved or the report data are correct."
            self._desktop_class.logger.error(msg)
            return
        trace_values = [(k[0], v) for k, v in trace_data.full_matrix_real_imag[0][trace_data.expressions[0]].items()]
        pass_fail_table = [["Pass Fail Criteria", "Result"]]
        for limit_v in local_config["limitLines"].values():
            yy = 0
            while yy < len(limit_v["xpoints"]) - 1:
                if limit_v["xpoints"][yy] != limit_v["xpoints"][yy + 1]:
                    result_range = self._get_frequency_range(
                        trace_values, limit_v["xpoints"][yy], limit_v["xpoints"][yy + 1]
                    )
                    hatch_above = False
                    if limit_v.get("hatch_above", True):
                        hatch_above = True
                    test_value = limit_v["ypoints"][yy]
                    sim_value = self._check_test_value(result_range, test_value, hatch_above)
                    if sim_value:
                        mystr = f"Failed Zone {yy}: Crossing limitline {test_value} dB."
                        result_value = "FAIL"
                    else:
                        mystr = f"Passed Zone  {yy}: Limitline {test_value} dB."
                        result_value = "PASS"
                    font_table.append([None, [255, 0, 0]] if result_value == "FAIL" else ["", None])
                    pass_fail_table.append([mystr, result_value])
                yy += 1
        pdf_report.add_section(portrait=True)
        pdf_report.add_table(f"Pass Fail Criteria on {image_name}", pass_fail_table, font_table)

    def _add_statistical_violations(self, report, pdf_report, image_name, local_config):
        font_table = [["", None]]
        pass_fail_table = [["Pass Fail Criteria", "Result"]]
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
        if result_value == "FAIL":
            result_value = f"Failed on {num_failed} points."
        font_table.append([None, [255, 0, 0]] if result_value == "FAIL" else ["", None])
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
        pdf_report.add_section(portrait=True)
        pdf_report.add_table(f"Pass Fail Criteria on {image_name}", pass_fail_table, font_table)

    def _add_eye_diagram_violations(self, report, pdf_report, image_name):
        # noinspection PyBroadException
        try:
            out_eye = os.path.join(self._output_folder, "violations.tab")
            viol = report.export_mask_violation(out_eye)
        except Exception:
            viol = None
        font_table = [["", None]]
        pass_fail_table = [["Pass Fail Criteria", "Result"]]
        mystr1 = "Eye Mask Violation:"
        result_value_mask = "PASS"
        mystr2 = "Upper/Lower Mask Violation:"
        result_value_upper = "PASS"
        if os.path.exists(viol):
            try:  # pragma: no cover
                import pandas as pd
            except ImportError:
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
        pdf_report.add_section(portrait=True)
        pdf_report.add_table(f"Pass Fail Criteria on {image_name}", pass_fail_table, font_table)

    def _add_contour_eye_diagram_violations(self, report, pdf_report, image_name, local_config):
        pass_fail_table = [["Pass Fail Criteria", "Result"]]
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
        pdf_report.add_section(portrait=True)
        pdf_report.add_table(f"Pass Fail Criteria on {image_name}", pass_fail_table, font_table)

    def _add_eye_measurement(self, report, pdf_report, image_name):
        report.add_all_eye_measurements()
        out_eye = os.path.join(self._output_folder, "eye_measurements_{}.csv".format(image_name))
        report._post.oreportsetup.ExportTableToFile(report.plot_name, out_eye, "Legend")
        report.clear_all_eye_measurements()
        table = read_csv(out_eye)
        new_table = []
        for line in table:
            new_table.append(line)
        pdf_report.add_section(portrait=True)
        pdf_report.add_table(f"Eye Measurements on {image_name}", new_table)

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

    def _create_project_info(self, report):
        report.add_section()
        report.add_chapter("Project Info")
        designs = []
        _design = None
        for template_report in self.local_config["reports"]:
            design_name = template_report["design_name"]
            if design_name in designs:
                continue
            designs.append(design_name)
            if _design and _design.design_name != design_name or _design is None:
                _design = get_pyaedt_app(self._project_name, design_name)
            report.add_empty_line(3)
            report.add_sub_chapter(f"Design Information: {_design.design_name}")
            msg = f"This design contains {len(_design.setups)} setups."
            report.add_text(msg)
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
                report.add_table("Components", components, col_widths=[75, 275])

    def create_compliance_report(self, file_name="compliance_test.pdf"):
        """Create the Virtual Compliance report.

        Parameters
        ----------
        file_name : str
            Output file name.

        Returns
        -------
        str
            Path to the output file.
        """
        report = AnsysReport()
        report.aedt_version = self._desktop_class.aedt_version_id
        report.design_name = self._template_name
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
                    report.add_image(file, caption=caption)

        self._create_aedt_reports(report)
        if self._add_project_info:
            self._create_project_info(report)
        report.add_toc()
        return report.save_pdf(self._output_folder, file_name=file_name)
