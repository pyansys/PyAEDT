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
import warnings

from ansys.aedt.core.generic.constants import unit_converter
from ansys.aedt.core.generic.general_methods import generate_unique_name
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.visualization.post.common import PostProcessorCommon

try:
    import pandas as pd
except ImportError:
    pd = None
    warnings.warn(
        "The Pandas module is required to run some functionalities of PostProcess.\n"
        "Install with \n\npip install pandas"
    )


class PostProcessorCircuit(PostProcessorCommon):
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
        PostProcessorCommon.__init__(self, app)

    @pyaedt_function_handler()
    def export_model_picture(
        self,
        output_file=None,
        page=1,
        width=1920,
        height=1080,
    ):
        """Export a snapshot of the schematic to a ``JPG`` file.

        Parameters
        ----------
        output_file : str, optional
            Full Path for exporting the image file. The default is ``None``, in which case working_dir is used.
        page : int, optional
            Page number of the schematic. The default is ``1``.
        width : int, optional
            Export image picture width size in pixels. Default is 1920 which takes the desktop size.
        height : int, optional
            Export image picture height size in pixels. Default is 10800 which takes the desktop size.

        Returns
        -------
        str
            File path of the generated JPG file.

        References
        ----------
        >>> oEditor.ExportImage

        Examples
        --------
        >>> from ansys.aedt.core import Circuit
        >>> app = Circuit(non_graphical=False)
        >>> output_file = app.post.export_model_picture(full_name=os.path.join(app.working_directory, "images1.jpg"))
        """
        if not output_file:
            output_file = os.path.join(
                self._app.working_directory, generate_unique_name(self._app.design_name) + ".jpg"
            )
        if page >= self.oeditor.GetNumPages():
            self.logger.error("Page number out of range")
            return ""
        self.oeditor.ExportImage(output_file, page, width, height)
        return output_file

    @pyaedt_function_handler(setupname="setup", plotname="plot_name")
    def create_ami_initial_response_plot(
        self,
        setup,
        ami_name,
        variation_list_w_value,
        plot_type="Rectangular Plot",
        plot_initial_response=True,
        plot_intermediate_response=False,
        plot_final_response=False,
        plot_name=None,
    ):
        """Create an AMI initial response plot.

        Parameters
        ----------
        setup : str
            Name of the setup.
        ami_name : str
            AMI probe name to use.
        variation_list_w_value : list
            List of variations with relative values.
        plot_type : str
            String containing the report type. Default is ``"Rectangular Plot"``. It can be ``"Data Table"``,
            ``"Rectangular Stacked Plot"``or any of the other valid AEDT Report types.
            The default is ``"Rectangular Plot"``.
        plot_initial_response : bool, optional
            Set either to plot the initial input response.  Default is ``True``.
        plot_intermediate_response : bool, optional
            Set whether to plot the intermediate input response.  Default is ``False``.
        plot_final_response : bool, optional
            Set whether to plot the final input response.  Default is ``False``.
        plot_name : str, optional
            Plot name.  The default is ``None``, in which case
            a unique name is automatically assigned.

        Returns
        -------
        str
            Name of the plot.
        """
        if not plot_name:
            plot_name = generate_unique_name("AMIAnalysis")
        variations = ["__InitialTime:=", ["All"]]
        i = 0
        for a in variation_list_w_value:
            if (i % 2) == 0:
                if ":=" in a:
                    variations.append(a)
                else:
                    variations.append(a + ":=")
            else:
                if isinstance(a, list):
                    variations.append(a)
                else:
                    variations.append([a])
            i += 1
        ycomponents = []
        if plot_initial_response:
            ycomponents.append(f"InitialImpulseResponse<{ami_name}.int_ami_rx>")
        if plot_intermediate_response:
            ycomponents.append(f"IntermediateImpulseResponse<{ami_name}.int_ami_rx>")
        if plot_final_response:
            ycomponents.append(f"FinalImpulseResponse<{ami_name}.int_ami_rx>")
        self.oreportsetup.CreateReport(
            plot_name,
            "Standard",
            plot_type,
            setup,
            [
                "NAME:Context",
                "SimValueContext:=",
                [
                    55824,
                    0,
                    2,
                    0,
                    False,
                    False,
                    -1,
                    1,
                    0,
                    1,
                    1,
                    "",
                    0,
                    0,
                    "NUMLEVELS",
                    False,
                    "1",
                    "PCID",
                    False,
                    "-1",
                    "PID",
                    False,
                    "1",
                    "SCID",
                    False,
                    "-1",
                    "SID",
                    False,
                    "0",
                ],
            ],
            variations,
            ["X Component:=", "__InitialTime", "Y Component:=", ycomponents],
        )
        return plot_name

    @pyaedt_function_handler(setupname="setup", plotname="plot_name")
    def create_ami_statistical_eye_plot(
        self, setup, ami_name, variation_list_w_value, ami_plot_type="InitialEye", plot_name=None
    ):
        """Create an AMI statistical eye plot.

        Parameters
        ----------
        setup : str
            Name of the setup.
        ami_name : str
            AMI probe name to use.
        variation_list_w_value : list
            Variations with relative values.
        ami_plot_type : str, optional
            String containing the report AMI type. The default is ``"InitialEye"``.
            Options are ``"EyeAfterChannel"``, ``"EyeAfterProbe"````"EyeAfterSource"``,
            and ``"InitialEye"``..
        plot_name : str, optional
            Plot name.  The default is ``None``, in which case
            a unique name starting with ``"Plot"`` is automatically assigned.

        Returns
        -------
        str
           The name of the plot.

        References
        ----------
        >>> oModule.CreateReport
        """
        if not plot_name:
            plot_name = generate_unique_name("AMYAanalysis")
        variations = [
            "__UnitInterval:=",
            ["All"],
            "__Amplitude:=",
            ["All"],
        ]
        i = 0
        for a in variation_list_w_value:
            if (i % 2) == 0:
                if ":=" in a:
                    variations.append(a)
                else:
                    variations.append(a + ":=")
            else:
                if isinstance(a, list):
                    variations.append(a)
                else:
                    variations.append([a])
            i += 1
        ycomponents = []
        if ami_plot_type == "InitialEye" or ami_plot_type == "EyeAfterSource":
            ibs_type = "tx"
        else:
            ibs_type = "rx"
        ycomponents.append(f"{ami_plot_type}<{ami_name}.int_ami_{ibs_type}>")

        ami_id = "0"
        if ami_plot_type == "EyeAfterSource":
            ami_id = "1"
        elif ami_plot_type == "EyeAfterChannel":
            ami_id = "2"
        elif ami_plot_type == "EyeAfterProbe":
            ami_id = "3"
        self.oreportsetup.CreateReport(
            plot_name,
            "Statistical Eye",
            "Statistical Eye Plot",
            setup,
            [
                "NAME:Context",
                "SimValueContext:=",
                [
                    55819,
                    0,
                    2,
                    0,
                    False,
                    False,
                    -1,
                    1,
                    0,
                    1,
                    1,
                    "",
                    0,
                    0,
                    "NUMLEVELS",
                    False,
                    "1",
                    "QTID",
                    False,
                    ami_id,
                    "SCID",
                    False,
                    "-1",
                    "SID",
                    False,
                    "0",
                ],
            ],
            variations,
            ["X Component:=", "__UnitInterval", "Y Component:=", "__Amplitude", "Eye Diagram Component:=", ycomponents],
        )
        return plot_name

    @pyaedt_function_handler(setupname="setup", plotname="plot_name")
    def create_statistical_eye_plot(self, setup, probe_names, variation_list_w_value, plot_name=None):
        """Create a statistical QuickEye, VerifEye, and/or Statistical Eye plot.

        Parameters
        ----------
        setup : str
            Name of the setup.
        probe_names : str or list
            One or more names of the probes to plot in the eye diagram.
        variation_list_w_value : list
            List of variations with relative values.
        plot_name : str, optional
            Plot name. The default is ``None``, in which case a name is automatically assigned.

        Returns
        -------
        str
            The name of the plot.

        References
        ----------
        >>> oModule.CreateReport
        """
        if not plot_name:
            plot_name = generate_unique_name("AMIAanalysis")
        variations = [
            "__UnitInterval:=",
            ["All"],
            "__Amplitude:=",
            ["All"],
        ]
        i = 0
        for a in variation_list_w_value:
            if (i % 2) == 0:
                if ":=" in a:
                    variations.append(a)
                else:
                    variations.append(a + ":=")
            else:
                if isinstance(a, list):
                    variations.append(a)
                else:
                    variations.append([a])
            i += 1
        if isinstance(probe_names, list):
            ycomponents = probe_names
        else:
            ycomponents = [probe_names]

        self.oreportsetup.CreateReport(
            plot_name,
            "Statistical Eye",
            "Statistical Eye Plot",
            setup,
            [
                "NAME:Context",
                "SimValueContext:=",
                [
                    55819,
                    0,
                    2,
                    0,
                    False,
                    False,
                    -1,
                    1,
                    0,
                    1,
                    1,
                    "",
                    0,
                    0,
                    "NUMLEVELS",
                    False,
                    "1",
                    "QTID",
                    False,
                    "1",
                    "SCID",
                    False,
                    "-1",
                    "SID",
                    False,
                    "0",
                ],
            ],
            variations,
            ["X Component:=", "__UnitInterval", "Y Component:=", "__Amplitude", "Eye Diagram Component:=", ycomponents],
        )
        return plot_name

    @pyaedt_function_handler()
    def sample_waveform(
        self,
        waveform_data,
        waveform_sweep,
        waveform_unit="V",
        waveform_sweep_unit="s",
        unit_interval=1e-9,
        clock_tics=None,
        pandas_enabled=False,
    ):
        """Sampling a waveform at clock times plus half unit interval.

        Parameters
        ----------
        waveform_data : list
            Waveform data.
        waveform_sweep : list
            Waveform sweep data.
        waveform_unit : str, optional
            Waveform units. The default values is ``V``.
        waveform_sweep_unit : str, optional
            Time units. The default value is ``s``.
        unit_interval : float, optional
            Unit interval in seconds. The default is ``1e-9``.
        clock_tics : list, optional
            List with clock tics. The default is ``None``, in which case the clock tics from
            the AMI receiver are used.
        pandas_enabled : bool, optional
            Whether to enable the Pandas data format. The default is ``False``.

        Returns
        -------
        list or :class:`pandas.Series`
            Sampled waveform in ``Volts`` at different times in ``seconds``.

        Examples
        --------
        >>> from ansys.aedt.core import Circuit
        >>> circuit = Circuit()
        >>> circuit.post.sample_ami_waveform(name,probe_name,source_name,circuit.available_variations.nominal)
        """
        new_tic = []
        for tic in clock_tics:
            new_tic.append(unit_converter(tic, unit_system="Time", input_units="s", output_units=waveform_sweep_unit))
        new_ui = unit_converter(unit_interval, unit_system="Time", input_units="s", output_units=waveform_sweep_unit)

        zipped_lists = zip(new_tic, [new_ui / 2] * len(new_tic))
        extraction_tic = [x + y for (x, y) in zipped_lists]

        if pandas_enabled:
            sweep_filtered = waveform_sweep.values
            filtered_tic = list(filter(lambda num: num >= waveform_sweep.values[0], extraction_tic))
        else:
            sweep_filtered = waveform_sweep
            filtered_tic = list(filter(lambda num: num >= waveform_sweep[0], extraction_tic))

        outputdata = []
        new_voltage = []
        tic_in_s = []
        for tic in filtered_tic:
            if tic >= sweep_filtered[0]:
                sweep_filtered = list(filter(lambda num: num >= tic, sweep_filtered))
                if sweep_filtered:
                    if pandas_enabled:
                        waveform_index = waveform_sweep[waveform_sweep.values == sweep_filtered[0]].index.values
                    else:
                        waveform_index = waveform_sweep.index(sweep_filtered[0])
                    if not isinstance(waveform_data[waveform_index], float):
                        voltage = waveform_data[waveform_index].values[0]
                    else:
                        voltage = waveform_data[waveform_index]
                    new_voltage.append(
                        unit_converter(voltage, unit_system="Voltage", input_units=waveform_unit, output_units="V")
                    )
                    tic_in_s.append(
                        unit_converter(tic, unit_system="Time", input_units=waveform_sweep_unit, output_units="s")
                    )
                    if not pandas_enabled:
                        outputdata.append([tic_in_s[-1:][0], new_voltage[-1:][0]])
                    del sweep_filtered[0]
                else:
                    break
        if pandas_enabled:
            return pd.Series(new_voltage, index=tic_in_s)
        return outputdata

    @pyaedt_function_handler(setupname="setup", probe_name="probe", source_name="source")
    def sample_ami_waveform(
        self,
        setup,
        probe,
        source,
        variation_list_w_value,
        unit_interval=1e-9,
        ignore_bits=0,
        plot_type=None,
        clock_tics=None,
    ):
        """Sampling a waveform at clock times plus half unit interval.

        Parameters
        ----------
        setup : str
            Name of the setup.
        probe : str
            Name of the AMI probe.
        source : str
            Name of the AMI source.
        variation_list_w_value : list
            Variations with relative values.
        unit_interval : float, optional
            Unit interval in seconds. The default is ``1e-9``.
        ignore_bits : int, optional
            Number of initial bits to ignore. The default is ``0``.
        plot_type : str, optional
            Report type. The default is ``None``, in which case all report types are generated.
            Options for a specific report type are ``"InitialWave"``, ``"WaveAfterSource"``,
            ``"WaveAfterChannel"``, and ``"WaveAfterProbe"``.
        clock_tics : list, optional
            List with clock tics. The default is ``None``, in which case the clock tics from
            the AMI receiver are used.

        Returns
        -------
        list
            Sampled waveform in ``Volts`` at different times in ``seconds``.

        Examples
        --------
        >>> circuit = Circuit()
        >>> circuit.post.sample_ami_waveform(setupname,probe_name,source_name,circuit.available_variations.nominal)

        """
        initial_solution_type = self.post_solution_type
        self._app.solution_type = "NexximAMI"

        if plot_type == "InitialWave" or plot_type == "WaveAfterSource":
            plot_expression = [plot_type + "<" + source + ".int_ami_tx>"]
        elif plot_type == "WaveAfterChannel" or plot_type == "WaveAfterProbe":
            plot_expression = [plot_type + "<" + probe + ".int_ami_rx>"]
        else:
            plot_expression = [
                "InitialWave<" + source + ".int_ami_tx>",
                "WaveAfterSource<" + source + ".int_ami_tx>",
                "WaveAfterChannel<" + probe + ".int_ami_rx>",
                "WaveAfterProbe<" + probe + ".int_ami_rx>",
            ]
        waveform = []
        waveform_sweep = []
        waveform_unit = []
        waveform_sweep_unit = []
        waveform_data = None
        for exp in plot_expression:
            waveform_data = self.get_solution_data(
                expressions=exp, setup_sweep_name=setup, domain="Time", variations=variation_list_w_value
            )
            samples_per_bit = 0
            for sample in waveform_data.primary_sweep_values:
                sample_seconds = unit_converter(
                    sample, unit_system="Time", input_units=waveform_data.units_sweeps["Time"], output_units="s"
                )
                if sample_seconds > unit_interval:
                    samples_per_bit -= 1
                    break
                else:
                    samples_per_bit += 1
            if samples_per_bit * ignore_bits > len(waveform_data.data_real()):
                self._app.solution_type = initial_solution_type
                self.logger.warning("Ignored bits are greater than generated bits.")
                return None
            waveform.append(waveform_data.data_real()[samples_per_bit * ignore_bits :])
            waveform_sweep.append(waveform_data.primary_sweep_values[samples_per_bit * ignore_bits :])
            waveform_unit.append(waveform_data.units_data[exp])
            waveform_sweep_unit.append(waveform_data.units_sweeps["Time"])

        tics = clock_tics
        if not clock_tics:
            clock_expression = "ClockTics<" + probe + ".int_ami_rx>"
            clock_tic = self.get_solution_data(
                expressions=clock_expression,
                setup_sweep_name=setup,
                domain="Clock Times",
                variations=variation_list_w_value,
            )
            tics = clock_tic.data_real()

        outputdata = [[] for i in range(len(waveform))]
        is_pandas_enabled = False
        if waveform_data:
            is_pandas_enabled = waveform_data.enable_pandas_output
        for waveform_cont, waveform_real in enumerate(waveform):
            outputdata[waveform_cont] = self.sample_waveform(
                waveform_data=waveform_real,
                waveform_sweep=waveform_sweep[waveform_cont],
                waveform_unit=waveform_unit[waveform_cont],
                waveform_sweep_unit=waveform_sweep_unit[waveform_cont],
                unit_interval=unit_interval,
                clock_tics=tics,
                pandas_enabled=is_pandas_enabled,
            )
        return outputdata
