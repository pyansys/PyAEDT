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

import copy
from difflib import SequenceMatcher
import json
import os
import sys
import warnings

from ansys.aedt.core.generic.constants import unit_converter
from ansys.aedt.core.generic.data_handlers import _dict2arg
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.generic.load_aedt_file import load_entire_aedt_file
from ansys.aedt.core.generic.numbers import _units_assignment
from ansys.aedt.core.generic.settings import settings
from ansys.aedt.core.modules.setup_templates import Sweep3DLayout
from ansys.aedt.core.modules.setup_templates import SweepEddyCurrent
from ansys.aedt.core.modules.setup_templates import SweepHfss3D
from ansys.aedt.core.modules.setup_templates import SweepQ3D
from ansys.aedt.core.modules.setup_templates import SweepSiwave

open3 = open
if sys.version_info < (3, 0):
    import io

    open3 = io.open


@pyaedt_function_handler()
def identify_setup(props):
    """Identify if a setup's properties is based on a time or frequency domain.

    Parameters
    ----------
    props : dict
        Dictionary of the properties.

    Returns
    -------
    bool
        `True` if domain is a time. `False` if the domain is for a frequency and sweeps.
    """
    keys = [
        "Transient",
        "TimeStep",
        "Data/InitialStep",
        "TransientData",
        "QuickEyeAnalysis",
        "VerifEyeAnalysis",
        "AMIAnalysis",
        "HSPICETransientData",
        "SystemFDAnalysis",
        "Start Time:=",
    ]
    for key in keys:
        if "/" in key:
            if key.split("/")[0] in props and key.split("/")[1] in props[key.split("/")[0]]:
                return True
        elif key in props:
            return True
    return False


class SweepHFSS(object):
    """Initializes, creates, and updates sweeps in HFSS.

    Parameters
    ----------
    setup : :class 'from ansys.aedt.core.modules.solve_setup.Setup'
        Setup to use for the analysis.
    name : str
        Name of the sweep.
    sweep_type : str, optional
        Type of the sweep. Options are ``"Fast"``, ``"Interpolating"``,
        and ``"Discrete"``. The default is ``"Interpolating"``.
    props : dict, optional
        Dictionary of the properties. The default is ``None``, in which case
        the default properties are retrieved.

    Examples
    --------
    >>> hfss = Hfss(version=version, project=proj, design=gtemDesign, solution_type=solutiontype,
                    name=name, new_desktop=False, close_on_exit=False)
    >>> hfss_setup = hfss.setups[0]
    >>> hfss_sweep = SweepHFSS(hfss_setup, 'Sweep', sweep_type ='Interpolating', props=None)

    """

    def __init__(self, setup, name, sweep_type="Interpolating", props=None):
        self._app = setup
        self.oanalysis = setup.omodule
        self.setup_name = setup.name
        self.name = name
        self.props = copy.deepcopy(SweepHfss3D)
        if props:
            if "RangeStep" in props.keys():  # LinearCount is the default sweep type. Change it if RangeStep is passed.
                if "RangeCount" in props.keys():
                    self._app._app.logger.info(
                        "Inconsistent arguments 'RangeCount' and 'RangeStep' passed to 'SweepHFSS',"
                    )
                    self._app._app.logger.info("Default remains 'LinearCount' sweep type.")
                else:
                    self.props["RangeType"] = "LinearStep"
            for key, value in props.items():
                if key in self.props.keys():
                    self.props[key] = value
                else:
                    error_message = f"Parameter '{key}' is invalid and will be ignored."
                    self._app._app.logger.warning(error_message)

        if SequenceMatcher(None, sweep_type.lower(), "interpolating").ratio() > 0.8:
            sweep_type = "Interpolating"
        elif SequenceMatcher(None, sweep_type.lower(), "discrete").ratio() > 0.8:
            sweep_type = "Discrete"
        elif SequenceMatcher(None, sweep_type.lower(), "fast").ratio() > 0.8:
            sweep_type = "Fast"
        else:
            warnings.warn("Invalid sweep type. `Interpolating` will be set as the default.")
            sweep_type = "Interpolating"
        self.props["Type"] = sweep_type

    @property
    def is_solved(self):
        """Verify if solutions are available for the sweep.

        Returns
        -------
        bool
            `True` if solutions are available.
        """
        sol = self._app._app.post.reports_by_category.standard(setup=f"{self.setup_name} : {self.name}")
        if identify_setup(self.props):
            sol.domain = "Time"
        return True if sol.get_solution_data() else False

    @property
    def frequencies(self):
        """List of all frequencies of the active sweep.

        To see values, the project must be saved and solved.

        Returns
        -------
        list of float
            Frequency points.
        """
        sol = self._app._app.post.reports_by_category.standard(setup=f"{self.setup_name} : {self.name}")
        soldata = sol.get_solution_data()
        if soldata and "Freq" in soldata.intrinsics:
            return soldata.intrinsics["Freq"]
        return []

    @property
    def basis_frequencies(self):
        """List of all frequencies that have fields available.

        To see values, the project must be saved and solved.

        Returns
        -------
        list of float
            Frequency points.
        """
        solutions_file = os.path.join(self._app._app.results_directory, f"{self._app._app.design_name}.asol")
        fr = []
        if os.path.exists(solutions_file):
            solutions = load_entire_aedt_file(solutions_file)
            for k, v in solutions.items():
                if "SolutionBlock" in k and "SolutionName" in v and v["SolutionName"] == self.name and "Fields" in v:
                    try:
                        new_list = [float(i) for i in v["Fields"]["IDDblMap"][1::2]]

                        new_list.sort()
                        new_list = unit_converter(
                            values=new_list,
                            unit_system="Freq",
                            input_units="Hz",
                            output_units=self._app._app.units.frequency,
                        )
                        fr.append(new_list)
                    except (KeyError, NameError, IndexError):
                        pass

        count = 0
        for el in self._app._app.setups:
            if el.name == self.setup_name:
                for sweep in el.sweeps:
                    if sweep.name == self.name:
                        return fr[count] if len(fr) >= count + 1 else []
            else:
                for sweep in el.sweeps:
                    if sweep.name == self.name:
                        count += 1
        return []

    @pyaedt_function_handler(rangetype="range_type")
    def add_subrange(self, range_type, start, end=None, count=None, unit="GHz", save_single_fields=False, clear=False):
        """Add a range to the sweep.

        Parameters
        ----------
        range_type : str
            Type of the range. Options are ``"LinearCount"``,
            ``"LinearStep"``, ``"LogScale"``, and ``"SinglePoints"``.
        start : float
            Starting frequency.
        end : float, optional
            Stopping frequency. The default value is ``None``. A value is required for
            ``range_type="LinearCount"|"LinearStep"|"LogScale"``.
        count : int or float, optional
            Frequency count or frequency step. The default is ``None``. A value is required for
            ``range_type="LinearCount"|"LinearStep"|"LogScale"``.
        unit : str, optional
            Unit of the frequency. For example, ``"MHz`` or ``"GHz"``. The default is ``"GHz"``.
        save_single_fields : bool, optional
            Whether to save the fields of the single point. The default is ``False``.
            This parameter is used only for ``range_type="SinglePoints"``.
        clear : bool, optional
            Whether to suppress all other subranges except the current one under creation.
            The default value is ``False``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------
        Create a setup in an HFSS design and add multiple sweep ranges.

        >>> setup = hfss.create_setup(name="MySetup")
        >>> sweep = setup.add_sweep()
        >>> sweep.change_type("Interpolating")
        >>> sweep.change_range("LinearStep", 1.1, 2.1, 0.4, "GHz")
        >>> sweep.add_subrange("LinearCount",1,1.5,5,"MHz")
        >>> sweep.add_subrange("LogScale",1,3,10,"GHz")

        """
        if range_type == "LinearCount" or range_type == "LinearStep" or range_type == "LogScale":
            if not end or not count:
                raise AttributeError("Parameters 'end' and 'count' must be present.")

        if clear:
            self.props["RangeType"] = range_type
            self.props["RangeStart"] = str(start) + unit
            if range_type == "LinearCount":
                self.props["RangeEnd"] = str(end) + unit
                self.props["RangeCount"] = count
            elif range_type == "LinearStep":
                self.props["RangeEnd"] = str(end) + unit
                self.props["RangeStep"] = str(count) + unit
            elif range_type == "LogScale":
                self.props["RangeEnd"] = str(end) + unit
                self.props["RangeSamples"] = count
            elif range_type == "SinglePoints":
                self.props["RangeEnd"] = str(start) + unit
                self.props["SaveSingleField"] = save_single_fields
            self.props["SweepRanges"] = {"Subrange": []}
            return self.update()

        interval = {"RangeType": range_type, "RangeStart": str(start) + unit}
        if range_type == "LinearCount":
            interval["RangeEnd"] = str(end) + unit
            interval["RangeCount"] = count
        elif range_type == "LinearStep":
            interval["RangeEnd"] = str(end) + unit
            interval["RangeStep"] = str(count) + unit
        elif range_type == "LogScale":
            interval["RangeEnd"] = str(end) + unit
            interval["RangeCount"] = self.props["RangeCount"]
            interval["RangeSamples"] = count
        elif range_type == "SinglePoints":
            interval["RangeEnd"] = str(start) + unit
            interval["SaveSingleField"] = save_single_fields
        if not self.props.get("SweepRanges", None):
            self.props["SweepRanges"] = {"Subrange": []}

        if not isinstance(self.props["SweepRanges"]["Subrange"], list):
            self.props["SweepRanges"]["Subrange"] = [self.props["SweepRanges"]["Subrange"]]
        self.props["SweepRanges"]["Subrange"].append(interval)

        return self.update()

    @pyaedt_function_handler()
    def create(self):
        """Create a sweep.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        self.oanalysis.InsertFrequencySweep(self.setup_name, self._get_args())
        return True

    @pyaedt_function_handler()
    def update(self):
        """Update a sweep.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        self.oanalysis.EditFrequencySweep(self.setup_name, self.name, self._get_args())

        return True

    @pyaedt_function_handler()
    def _get_args(self, props=None):
        """Get arguments.

        Parameters
        ----------
        props : dict, optional
             Dictionary of the properties. The default is ``None``, in which
             case the default properties are retrieved.

        Returns
        -------
        dict
            Dictionary of the properties.

        """
        if props is None:
            props = self.props
        arg = ["NAME:" + self.name]
        _dict2arg(props, arg)
        return arg


class SweepHFSS3DLayout(object):
    """Initializes, creates, and updates sweeps in HFSS 3D Layout.

    Parameters
    ----------
    setup : :class 'from ansys.aedt.core.modules.solve_setup.Setup'
        Setup to use for the analysis.
    name : str
        Name of the sweep.
    sweep_type : str, optional
        Type of the sweep. Options are ``"Interpolating"`` and ``"Discrete"``. The default is ``"Interpolating"``.
    save_fields : bool, optional
        Whether to save the fields. The default is ``True``.
    props : dict, optional
        Dictionary of the properties. The default is ``None``, in which
        case the default properties are retrieved.

    """

    def __init__(self, setup, name, sweep_type="Interpolating", save_fields=True, props=None, **kwargs):
        self._app = setup
        self.oanalysis = setup.omodule
        self.props = {}
        self.setup_name = setup.name
        self.name = name
        if props:
            self.props = props
        else:
            if setup.setuptype in [40, 41]:
                self.props = copy.deepcopy(SweepSiwave)
            else:
                self.props = copy.deepcopy(Sweep3DLayout)
            # for t in props:
            #    _tuple2dict(t, self.props)
            if SequenceMatcher(None, sweep_type.lower(), "interpolating").ratio() > 0.8:
                sweep_type = "kInterpolating"
            elif SequenceMatcher(None, sweep_type.lower(), "discrete").ratio() > 0.8:
                sweep_type = "kDiscrete"
            elif SequenceMatcher(None, sweep_type.lower(), "fast").ratio() > 0.8:
                sweep_type = "kBroadbandFast"
            else:
                warnings.warn("Sweep type is invalid. `kInterpolating` is set as the default.")
                sweep_type = "kInterpolating"
            self.props["FreqSweepType"] = sweep_type
            self.props["GenerateSurfaceCurrent"] = save_fields

    @property
    def combined_name(self):
        """Compute the name : sweep_name string.

        Returns
        -------
        str
        """
        return f"{self.setup_name} : {self.name}"

    @property
    def is_solved(self):
        """Verify if solutions are available for the sweep.

        Returns
        -------
        bool
            `True` if solutions are available.
        """
        expressions = [i for i in self._app.post.available_report_quantities(solution=self.combined_name)]
        sol = self._app._app.post.reports_by_category.standard(expressions=expressions[0], setup=self.combined_name)
        if identify_setup(self.props):
            sol.domain = "Time"
        return True if sol.get_solution_data() else False

    @pyaedt_function_handler(sweeptype="sweep_type")
    def change_type(self, sweep_type):
        """Change the type of the sweep.

        Parameters
        ----------
        sweep_type : str
            Type of the sweep. Options are ``"Interpolating"`` and ``"Discrete"``.
            The default is ``"Interpolating"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if sweep_type == "Interpolating":
            self.props["FastSweep"] = True
        elif sweep_type == "Discrete":
            self.props["FastSweep"] = False
        else:
            raise AttributeError("Allowed sweep type options are 'Interpolating' and 'Discrete'.")
        return self.update()

    @pyaedt_function_handler()
    def set_save_fields(self, save_fields, save_rad_fields=False):
        """Choose whether to save fields.

        Parameters
        ----------
        save_fields : bool
            Whether to save the fields.
        save_rad_fields : bool, optional
            Whether to save the radiating fields. The default is ``False``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        self.props["GenerateSurfaceCurrent"] = save_fields
        self.props["SaveRadFieldsOnly"] = save_rad_fields
        return self.update()

    @pyaedt_function_handler(rangetype="range_type")
    def add_subrange(self, range_type, start, end=None, count=None, unit="GHz"):
        """Add a subrange to the sweep.

        Parameters
        ----------
        range_type : str
            Type of the subrange. Options are ``"LinearCount"``, ``"SinglePoint"``,
            ``"LinearStep"``, and ``"LogScale"``.
        start : float
            Starting frequency.
        end : float, optional
            Stopping frequency. The default is ``None``. A value is
            required for these subranges: ``"LinearCount"``, ``"LinearStep"``, and ``"LogScale"``.
        count : int or float, optional
            Frequency count or frequency step. The default is ``None``.
            A value is required for these subranges: ``"LinearCount"``, ``"LinearStep"``,
            and ``"LogScale"``.
        unit : str
            Unit of the frequency. For example, ``"MHz`` or ``"GHz"``. The default is ``"GHz"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        try:
            if range_type == "SinglePoint" and self.props["FreqSweepType"] == "kInterpolating":
                raise AttributeError("'SinglePoint is allowed only when sweep_type is 'Discrete'.'")
            if range_type == "LinearCount" or range_type == "LinearStep" or range_type == "LogScale":
                if not end or not count:
                    raise AttributeError("Parameters 'end' and 'count' must be present.")

            if range_type == "LinearCount":
                sweep_range = " LINC " + str(start) + unit + " " + str(end) + unit + " " + str(count)
            elif range_type == "LinearStep":
                sweep_range = " LIN " + str(start) + unit + " " + str(end) + unit + " " + str(count) + unit
            elif range_type == "LogScale":
                sweep_range = " DEC " + str(start) + unit + " " + str(end) + unit + " " + str(count)
            elif range_type == "SinglePoint":
                sweep_range = " " + str(start) + unit
            else:
                raise AttributeError(
                    'Allowed range_type are "LinearCount", "SinglePoint", "LinearStep", and "LogScale".'
                )
            self.props["Sweeps"]["Data"] += sweep_range
            return self.update()
        except Exception:
            return False

    @pyaedt_function_handler(rangetype="range_type")
    def change_range(self, range_type, start, end=None, count=None, unit="GHz"):
        """Change the range of the sweep.

        Parameters
        ----------
        range_type : str
            Type of the subrange. Options are ``"LinearCount"``, ``"SinglePoint"``,
            ``"LinearStep"``, and ``"LogScale"``.
        start : float
            Starting frequency.
        end : float, optional
            Stopping frequency. The default is ``None``.  A value is required
            for these subranges: ``"LinearCount"``, ``"LinearStep"``, and ``"LogScale"``.
        count : int or float, optional
            Frequency count or frequency step. The default is ``None``.
            A value is required for these subranges: ``"LinearCount"``,
            ``"LinearStep"``, and ``"LogScale"``.
        unit : str, optional
            Unit of the frequency. For example, ``"MHz`` or ``"GHz"``. The default is ``"GHz"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        if range_type == "LinearCount":
            sweep_range = "LINC " + str(start) + unit + " " + str(end) + unit + " " + str(count)
        elif range_type == "LinearStep":
            sweep_range = "LIN " + str(start) + unit + " " + str(end) + unit + " " + str(count) + unit
        elif range_type == "LogScale":
            sweep_range = "DEC " + str(start) + unit + " " + str(end) + unit + " " + str(count)
        elif range_type == "SinglePoint":
            sweep_range = str(start) + unit
        else:
            raise AttributeError('Allowed range_type are "LinearCount", "SinglePoint", "LinearStep", and "LogScale".')
        self.props["Sweeps"]["Data"] = sweep_range
        return self.update()

    @pyaedt_function_handler()
    def create(self):
        """Create a sweep.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        self.oanalysis.AddSweep(self.setup_name, self._get_args())
        return True

    @pyaedt_function_handler()
    def update(self):
        """Update the sweep.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        self.oanalysis.EditSweep(self.setup_name, self.name, self._get_args())
        return True

    @pyaedt_function_handler()
    def _get_args(self, props=None):
        """Retrieve properties.

        Parameters
        ----------
        props : dict
             Dictionary of the properties. The default is ``None``, in which case
             the default properties are retrieved.

        Returns
        -------
        dict
            Dictionary of the properties.

        """
        if props is None:
            props = self.props
        arg = ["NAME:" + self.name]
        _dict2arg(props, arg)
        return arg


class SweepMatrix(object):
    """Initializes, creates, and updates sweeps in Q3D.

    Parameters
    ----------
    setup : :class 'from ansys.aedt.core.modules.solve_setup.Setup'
        Setup used for the analysis.
    name : str
        Name of the sweep.
    sweep_type : str, optional
        Type of the sweep. Options are ``"Fast"``, ``"Interpolating"``,
        and ``"Discrete"``. The default is ``"Interpolating"``.
    props : dict
        Dictionary of the properties.  The default is ``None``, in which case
        the default properties are retrieved.
    """

    def __init__(self, setup, name, sweep_type="Interpolating", props=None):
        self._app = setup  # TODO: Remove sweep_type as an argument as it can be passed in props
        self.oanalysis = setup.omodule
        self.setup_name = setup.name
        self.name = name
        self.props = copy.deepcopy(SweepQ3D)
        if props:
            for key, value in props.items():
                if key in self.props:
                    self.props[key] = value
        else:
            self.props["Type"] = sweep_type
            if sweep_type == "Discrete":
                self.props["IsEnabled"] = True
                self.props["RangeType"] = "LinearCount"
                self.props["RangeStart"] = "2.5GHz"
                self.props["RangeStep"] = "1GHz"
                self.props["RangeEnd"] = "7.5GHz"
                self.props["SaveSingleField"] = False
                self.props["RangeSamples"] = 3
                self.props["RangeCount"] = 401
                self.props["SaveFields"] = False
                self.props["SaveRadFields"] = False
                self.props["SweepRanges"] = []
            else:
                self.props["IsEnabled"] = True
                self.props["RangeType"] = "LinearStep"
                self.props["RangeStart"] = "1GHz"
                self.props["RangeStep"] = "1GHz"
                self.props["RangeEnd"] = "20GHz"
                self.props["SaveFields"] = False
                self.props["SaveRadFields"] = False
                self.props["InterpTolerance"] = 0.5
                self.props["InterpMaxSolns"] = 50
                self.props["InterpMinSolns"] = 0
                self.props["InterpMinSubranges"] = 1

    @property
    def is_solved(self):
        """Verify if solutions are available for given sweep.

        Returns
        -------
        bool
            `True` if solutions are available.
        """
        sol = self._app._app.post.reports_by_category.standard(setup=f"{self.setup_name} : {self.name}")
        return True if sol.get_solution_data() else False

    @property
    def frequencies(self):
        """List of all frequencies of the active sweep.

        To see values, the project must be saved and solved.

        Returns
        -------
        list of float
            Frequency points.
        """
        sol = self._app._app.post.reports_by_category.standard(setup=f"{self.setup_name} : {self.name}")
        soldata = sol.get_solution_data()
        if soldata and "Freq" in soldata.intrinsics:
            return soldata.intrinsics["Freq"]
        return []

    @property
    def basis_frequencies(self):
        """Get the list of all frequencies that have fields available.

        The project has to be saved and solved to see values.

        Returns
        -------
        list of float
            Frequency points.
        """
        solutions_file = os.path.join(self._app._app.results_directory, f"{self._app._app.design_name}.asol")
        fr = []
        if os.path.exists(solutions_file):
            solutions = load_entire_aedt_file(solutions_file)
            for k, v in solutions.items():
                if "SolutionBlock" in k and "SolutionName" in v and v["SolutionName"] == self.name and "Fields" in v:
                    try:  # pragma: no cover
                        new_list = [float(i) for i in v["Fields"]["IDDblMap"][1::2]]
                        new_list.sort()
                        new_list = unit_converter(
                            values=new_list,
                            unit_system="Freq",
                            input_units="Hz",
                            output_units=self._app._app.units.frequency,
                        )
                        fr.append(new_list)
                    except (KeyError, NameError, IndexError):
                        pass

        count = 0
        for el in self._app._app.setups:
            if el.name == self.setup_name:
                for sweep in el.sweeps:
                    if sweep.name == self.name:
                        return fr[count] if len(fr) >= count + 1 else []
            else:
                for sweep in el.sweeps:
                    if sweep.name == self.name:
                        count += 1
        return []

    @pyaedt_function_handler(rangetype="range_type")
    def add_subrange(self, range_type, start, end=None, count=None, unit="GHz", clear=False, **kwargs):
        """Add a subrange to the sweep.

        Parameters
        ----------
        range_type : str
            Type of the subrange. Options are ``"LinearCount"``,
            ``"LinearStep"``, and ``"LogScale"``.
        start : float
            Starting frequency.
        end : float
            Stopping frequency. The default is ``None``.
        count : int or float
            Frequency count or frequency step. The default is ``None``.
        unit : str, optional
            Frequency units.
        clear : bool, optional
            Whether to replace the subrange. The default is ``False``, in which case
            subranges are appended.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        if "type" in kwargs:
            warnings.warn("'type' has been deprecated. Use 'range_type' instead.", DeprecationWarning)
            range_type = kwargs["type"]
        if clear:
            self.props["RangeType"] = range_type
            self.props["RangeStart"] = str(start) + unit
            if range_type == "LinearCount":
                self.props["RangeEnd"] = str(end) + unit
                self.props["RangeCount"] = count
            elif range_type == "LinearStep":
                self.props["RangeEnd"] = str(end) + unit
                self.props["RangeStep"] = str(count) + unit
            elif range_type == "LogScale":
                self.props["RangeEnd"] = str(end) + unit
                self.props["RangeSamples"] = count
            self.props["SweepRanges"] = {"Subrange": []}
            return self.update()
        sweep_range = {"RangeType": range_type, "RangeStart": str(start) + unit}
        if range_type == "LinearCount":
            sweep_range["RangeEnd"] = str(end) + unit
            sweep_range["RangeCount"] = count
        elif range_type == "LinearStep":
            sweep_range["RangeEnd"] = str(end) + unit
            sweep_range["RangeStep"] = str(count) + unit
        elif range_type == "LogScale":
            sweep_range["RangeEnd"] = str(end) + unit
            sweep_range["RangeCount"] = self.props["RangeCount"]
            sweep_range["RangeSamples"] = count
        if not self.props.get("SweepRanges") or not self.props["SweepRanges"].get("Subrange"):
            self.props["SweepRanges"] = {"Subrange": []}
        self.props["SweepRanges"]["Subrange"].append(sweep_range)
        return self.update()

    @pyaedt_function_handler()
    def create(self):
        """Create a sweep.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        self.oanalysis.InsertSweep(self.setup_name, self._get_args())
        return True

    @pyaedt_function_handler()
    def update(self):
        """Update the sweep.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        self.oanalysis.EditSweep(self.setup_name, self.name, self._get_args())

        return True

    @pyaedt_function_handler()
    def _get_args(self, props=None):
        """Get properties.

        Parameters
        ----------
        props : dict
             Dictionary of the properties. The default is ``None``, in which case
             the default properties are retrieved.

        Returns
        -------
        dict
            Dictionary of the properties.

        """
        if props is None:
            props = self.props
        arg = ["NAME:" + self.name]
        _dict2arg(props, arg)
        return arg


class SweepMaxwellEC(object):
    """Initializes, creates, and updates sweeps in Maxwell Eddy Current.

    Parameters
    ----------
    setup : :class 'from ansys.aedt.core.modules.solve_setup.Setup'
        Setup used for the analysis.
    name : str
        Name of the sweep.
    sweep_type : str, optional
        Type of the sweep. Options are ``"LinearStep"``, ``"LinearCount"``,
         ``"LogScale"`` and ``"SinglePoints"``. The default is ``"LinearStep"``.
    props : dict
        Dictionary of the properties.  The default is ``None``, in which case
        the default properties are retrieved.
    """

    def __init__(self, setup, sweep_type="LinearStep", props=None):
        self._setup = setup
        self.oanalysis = setup.omodule
        self.setup_name = setup.name
        self.props = {}
        if props:
            self.props = props
        else:
            self.props = copy.deepcopy(SweepEddyCurrent)
            self.props["RangeType"] = sweep_type
            if sweep_type == "LinearStep":
                self.props["RangeStep"] = "10Hz"
            elif sweep_type == "LinearCount":
                self.props["RangeCount"] = "10"
            elif sweep_type == "LogScale":
                self.props["RangeSamples"] = "2"
            elif sweep_type == "SinglePoints":
                self.props["RangeEnd"] = self.props["RangeStart"]

    @property
    def is_solved(self):
        """Verify if solutions are available for the sweep.

        Returns
        -------
        bool
            `True` if solutions are available.
        """
        expressions = [
            i for i in self._setup._app.post.available_report_quantities(solution=self._setup._app.nominal_sweep)
        ]
        sol = self._setup._app.post.reports_by_category.standard(
            expressions=expressions[0], setup=self._setup._app.nominal_sweep
        )
        if identify_setup(self.props):
            sol.domain = "Time"
        return True if sol.get_solution_data() else False

    @property
    def frequencies(self):
        """List of all frequencies of the active sweep.

        To see values, the project must be saved and solved.

        Returns
        -------
        list of float
            Frequency points.
        """
        expressions = [
            i for i in self._setup._app.post.available_report_quantities(solution=self._setup._app.nominal_sweep)
        ]
        sol = self._setup._app.post.reports_by_category.standard(
            expressions=expressions[0], setup=self._setup._app.nominal_sweep
        )
        soldata = sol.get_solution_data()
        if soldata and "Freq" in soldata.intrinsics:
            return soldata.intrinsics["Freq"]
        return []

    @pyaedt_function_handler()
    def create(self):
        """Create a Maxwell Eddy Current sweep.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        self.oanalysis.EditSetup(self.setup_name, self._get_args(self._setup.props))
        return True

    @pyaedt_function_handler()
    def update(self):
        """Update a Maxwell Eddy Current sweep.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        self.oanalysis.EditSetup(self.setup_name, self._get_args(self._setup.props))
        return True

    @pyaedt_function_handler()
    def delete(self):
        """Delete a Maxwell Eddy Current sweep.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        setup_sweeps = self._setup.props["SweepRanges"]["Subrange"].copy()
        if isinstance(self._setup.props["SweepRanges"]["Subrange"], list):
            for sweep in setup_sweeps:
                if self.props == sweep:
                    self._setup.props["SweepRanges"]["Subrange"].remove(self.props)
                    [self._setup._sweeps.remove(s) for s in self._setup._sweeps if s.props == sweep]
        else:
            pass
        self._setup.update()
        return True

    @pyaedt_function_handler()
    def _get_args(self, props=None):
        """Get arguments.

        Parameters
        ----------
        props : dict, optional
             Dictionary of the properties. The default is ``None``, in which
             case the default properties are retrieved.

        Returns
        -------
        dict
            Dictionary of the properties.

        """
        if props is None:
            props = self.props
        arg = ["NAME:" + self.setup_name]
        _dict2arg(props, arg)
        return arg


class SetupProps(dict):
    """Provides internal parameters for the AEDT boundary component."""

    def __setitem__(self, key, value):
        if isinstance(value, dict):
            dict.__setitem__(self, key, SetupProps(self._pyaedt_setup, value))
        else:
            value = _units_assignment(value)
            dict.__setitem__(self, key, value)
        if self._pyaedt_setup.auto_update:
            res = self._pyaedt_setup.update()
            if not res:
                self._pyaedt_setup._app.logger.warning("Update of %s failed. Check needed arguments", key)

    def __init__(self, setup, props):
        dict.__init__(self)
        if props:
            for key, value in props.items():
                if isinstance(value, dict):
                    dict.__setitem__(self, key, SetupProps(setup, value))
                else:
                    dict.__setitem__(self, key, value)
        self._pyaedt_setup = setup

    def _setitem_without_update(self, key, value):
        dict.__setitem__(self, key, value)

    def _export_properties_to_json(self, file_path, overwrite=False):
        """Export all setup properties to a JSON file.

        Parameters
        ----------
        file_path : str
            File path for the JSON file.
        """
        FILTER_KEYS = {"DataId", "SimSetupID", "ProdMajVerID", "ProjDesignSetup", "ProdMinVerID", "NumberOfProcessors"}
        if not file_path.endswith(".json"):
            file_path = file_path + ".json"
        export_dict = {}
        for k, v in self.items():
            if k not in FILTER_KEYS:
                export_dict[k] = v
        if os.path.isfile(file_path) and not overwrite:
            settings.logger.warning("Unable to overwrite file: %s." % (file_path))
            return False
        else:
            with open3(file_path, "w", encoding="utf-8") as f:
                f.write(json.dumps(export_dict, indent=4, ensure_ascii=False))
            return True

    def _import_properties_from_json(self, file_path):
        """Import setup properties from a JSON file.

        Parameters
        ----------
        file_path : str
            File path for the JSON file.
        """

        def set_props(target, source):
            for k, v in source.items():
                if k not in target:
                    self._pyaedt_setup._app.logger.warning(f"{k} is not a valid property name.")
                if not isinstance(v, dict):
                    target[k] = v
                else:
                    if k not in target:
                        target[k] = {}
                    set_props(target[k], v)

        with open3(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            set_props(self, data)
        return True

    def delete_all(self):
        for item in list(self.keys()):
            if item != "_pyaedt_setup":
                dict.__delitem__(self, item)
