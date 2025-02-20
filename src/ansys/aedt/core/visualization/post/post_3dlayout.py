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
from pathlib import Path
import re

from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.generic.settings import settings
from ansys.aedt.core.visualization.post.post_common_3d import PostProcessor3D


class PostProcessor3DLayout(PostProcessor3D):
    """Manages the main schematic postprocessing functions.

    .. note::
       Some functionalities are available only when AEDT is running in the graphical mode.

    Parameters
    ----------
    app : :class:`ansys.aedt.core.application.analysis_nexxim.FieldAnalysisCircuit`
        Inherited parent object. The parent object must provide the members
        `_modeler`, `_desktop`, `_odesign`, and `logger`.

    """

    def __init__(self, app):
        PostProcessor3D.__init__(self, app)

    @pyaedt_function_handler
    def _compute_power_loss(self, net_filter=None, layer_filter=None, solution=None):
        if solution is None:
            for setup in self._app.setups:
                if setup.solver_type == "SIwaveDCIR":
                    solution = setup.name
                    break
            if solution is None:  # pragma: no cover
                self._app.logger.error("No SIwave DC IR setup exist.")
                return
        else:
            solution_obj = [i for i in self._app.setups if i.name == solution]
            if len(solution_obj):
                if solution_obj[0].solver_type != "SIwaveDCIR":  # pragma: no cover
                    self._app.logger.error(f"Solution {solution} is not a SIwave DC IR setup.")
                    return
            else:  # pragma: no cover
                self._app.logger.error(f"Solution {solution} doesn't exist.")
                return

        aedt_results = Path(self._app.project_file).with_suffix(".aedtresults")
        solution_data_dir = aedt_results / "main"
        if not solution_data_dir.exists():  # pragma: no cover
            solution_data_dir = aedt_results / self._app.design_name
        subfolders = [f for f in solution_data_dir.iterdir() if f.is_dir()]
        dcir_solution_folder = None
        for folder in subfolders:
            file_exec = folder / "SIwave.exec"
            if not file_exec.exists():
                continue  # pragma: no cover
            with open(file_exec, "r") as f:
                siwave_exec = f.read()
                match = re.search(r'SetupName\s+"(.*?)"', siwave_exec)
                if match.group(1) == solution:
                    dcir_solution_folder = folder
                    break
        if dcir_solution_folder is None:  # pragma: no cover
            self._app.logger.error(f"Solution {solution} has no result.")
        else:
            file_net = None
            for i in dcir_solution_folder.iterdir():
                if i.suffix == ".net":
                    file_net = i
                    break
            with open(file_net, "r") as f:
                file_net_text = f.read()
                match = re.search(r"B_NET_CLASSIFICATION\s+(.*?)\s+E_NET_CLASSIFICATION", file_net_text, re.DOTALL)
                nets = []
                for i in match.group(1).split("\n"):
                    net_name = i.lstrip(" ").split(" ")[1]
                    nets.append(net_name)

        if net_filter is not None:
            nets = [i for i in nets if i in net_filter]

        edbapp = self._app.modeler.edb

        if layer_filter is None:
            net_per_layer_names = {i: [] for i in edbapp.stackup.signal_layers.keys()}
        else:
            net_per_layer_names = {i: [] for i in edbapp.stackup.signal_layers.keys() if i in layer_filter}

        for net_name in nets:
            net_obj = edbapp.nets[net_name]
            layer_names = [i.layer_name for i in net_obj.primitives]
            layer_names = list(set(layer_names))
            for i in layer_names:
                if i in net_per_layer_names:
                    net_per_layer_names[i].append(net_name)

        power_loss_per_layer = []
        operations = []
        for layer_name, net_names in net_per_layer_names.items():
            if not net_names:
                continue
            thickness = edbapp.stackup[layer_name].thickness
            for net_name in net_names:
                assignment = f"{layer_name}_{net_name}"
                operations.extend(
                    [
                        "Fundamental_Quantity('P')",
                        f"EnterSurface('{assignment}')",
                        "Operation('SurfaceValue')",
                        "Operation('Integrate')",
                    ]
                )

                operations.extend([f"Scalar_Constant({thickness})", "Operation('*')"])

                solution_type = ["DC Fields"] if settings.aedt_version < "2025.1" else ["DCIR Fields"]
                my_expression = {
                    "name": f"Power_{layer_name}",
                    "description": "Power Density",
                    "design_type": ["HFSS 3D Layout Design"],
                    "fields_type": solution_type,
                    "solution_type": "",
                    "primary_sweep": "",
                    "assignment": "",
                    "assignment_type": ["Surface"],
                    "operations": operations,
                    "report": ["Data Table", "Rectangular Plot"],
                }
                if self._app.post.fields_calculator.is_expression_defined(my_expression["name"]):
                    self._app.post.fields_calculator.delete_expression(my_expression["name"])
                self._app.post.fields_calculator.add_expression(my_expression, "")

                loss = self._app.post.fields_calculator.evaluate(my_expression["name"], solution, intrinsics={})

                power_loss_per_layer.append({"layer": layer_name, "net": net_name, "loss": float(loss)})

        return power_loss_per_layer

    @pyaedt_function_handler()
    def compute_power_by_layer(self, layers=None, solution=None):
        """Computes the power by layer. This applies only to SIwave DC Analysis.

        Parameters
        ----------
        layers : list, optional
            Layers to include in power calculation.
        solution : str, optional
            SIwave DCIR solution.

        Returns
        -------
        dict
            Power by layer.
        """
        power_by_layers = {}
        power_loss = self._compute_power_loss(layer_filter=layers, solution=solution)
        for i in power_loss:
            layer_name = i["layer"]
            loss = i["loss"]
            if layer_name not in power_by_layers:
                power_by_layers[layer_name] = loss
            else:
                power_by_layers[layer_name] += loss
        return power_by_layers

    @pyaedt_function_handler()
    def compute_power_by_net(self, nets=None, solution=None):
        """Compute the power by nets. This applies only to SIwave DC Analysis.

        Parameters
        ----------
        nets : list, optional
            Layers to include in power calculation.
        solution : str, optional
            SIwave DCIR solution.

        Returns
        -------
        dict
            Power by nets.
        """
        power_by_nets = {}
        power_loss = self._compute_power_loss(net_filter=nets, solution=solution)
        for i in power_loss:
            net_name = i["net"]
            loss = i["loss"]
            if net_name not in power_by_nets:
                power_by_nets[net_name] = loss
            else:
                power_by_nets[net_name] += loss
        return power_by_nets
