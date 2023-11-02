from collections import OrderedDict
import itertools
import math
import os
import sys
import time

from pyaedt import get_pyaedt_app, is_ironpython, pyaedt_function_handler, settings
from pyaedt.generic.constants import AEDT_UNITS, db10, db20, unit_converter
from pyaedt.generic.general_methods import check_and_download_folder, open_file, write_csv
from pyaedt.generic.plot import (
    get_structured_mesh,
    is_notebook,
    plot_2d_chart,
    plot_3d_chart,
    plot_contour,
    plot_polar_chart,
)
from pyaedt.modeler.cad.elements3d import FacePrimitive

np = None
pd = None
pv = None
if not is_ironpython:
    try:
        import numpy as np
    except ImportError:
        np = None
    try:
        import pandas as pd
    except ImportError:
        pd = None
    try:
        import pyvista as pv
    except ImportError:
        pv = None


class SolutionData(object):
    """Contains information from the :func:`GetSolutionDataPerVariation` method."""

    def __init__(self, aedtdata):
        self._original_data = aedtdata
        self.number_of_variations = len(aedtdata)
        self._enable_pandas_output = True if settings.enable_pandas_output and pd else False
        self._expressions = None
        self._intrinsics = None
        self._nominal_variation = None
        self._nominal_variation = self._original_data[0]
        self.active_expression = self.expressions[0]
        self._sweeps_names = []
        self.update_sweeps()
        self.variations = self._get_variations()
        self.active_intrinsic = OrderedDict({})
        for k, v in self.intrinsics.items():
            self.active_intrinsic[k] = v[0]
        if len(self.intrinsics) > 0:
            self._primary_sweep = list(self.intrinsics.keys())[0]
        else:
            self._primary_sweep = self._sweeps_names[0]
        self.active_variation = self.variations[0]
        self.units_sweeps = {}
        for intrinsic in self.intrinsics:
            try:
                self.units_sweeps[intrinsic] = self.nominal_variation.GetSweepUnits(intrinsic)
            except:
                self.units_sweeps[intrinsic] = None
        self.init_solutions_data()
        self._ifft = None

    @property
    def enable_pandas_output(self):
        """Set/Get a flag to use Pandas to export dict and lists. This applies to Solution data output.
        If ``True`` the property or method will return a pandas object in CPython environment.
        Default is ``False``.

        Returns
        -------
        bool
        """
        return True if self._enable_pandas_output and pd else False

    @enable_pandas_output.setter
    def enable_pandas_output(self, val):
        if val != self._enable_pandas_output and pd:
            self._enable_pandas_output = val
            self.init_solutions_data()

    @pyaedt_function_handler()
    def set_active_variation(self, var_id=0):
        """Set the active variations to one of available variations in self.variations.

        Parameters
        ----------
        var_id : int
            Index of Variations to assign.

        Returns
        -------
        bool
        """
        if var_id < len(self.variations):
            self.active_variation = self.variations[var_id]
            self.nominal_variation = var_id
            self._expressions = None
            self._intrinsics = None
            return True
        return False

    @pyaedt_function_handler()
    def _get_variations(self):
        variations_lists = []
        for data in self._original_data:
            variations = OrderedDict({})
            for v in data.GetDesignVariableNames():
                variations[v] = data.GetDesignVariableValue(v)
            variations_lists.append(variations)
        return variations_lists

    @pyaedt_function_handler()
    def variation_values(self, variation_name):
        """Get the list of the specific variation available values.

        Parameters
        ----------
        variation_name : str
            Name of variation to return.

        Returns
        -------
        list
        """
        if variation_name in self.intrinsics:
            return self.intrinsics[variation_name]
        else:
            vars_vals = []
            for el in self.variations:
                if variation_name in el and el[variation_name] not in vars_vals:
                    vars_vals.append(el[variation_name])
            return vars_vals

    @property
    def intrinsics(self):
        """Get intrinsics dictionary on active variation."""
        if not self._intrinsics:
            self._intrinsics = OrderedDict({})
            intrinsics = [i for i in self._sweeps_names if i not in self.nominal_variation.GetDesignVariableNames()]
            for el in intrinsics:
                values = list(self.nominal_variation.GetSweepValues(el, False))
                self._intrinsics[el] = [i for i in values]
                self._intrinsics[el] = list(OrderedDict.fromkeys(self._intrinsics[el]))
        return self._intrinsics

    @property
    def nominal_variation(self):
        """Nominal variation."""
        return self._nominal_variation

    @nominal_variation.setter
    def nominal_variation(self, val):
        if 0 <= val <= self.number_of_variations:
            self._nominal_variation = self._original_data[val]
        else:
            print(str(val) + " not in Variations")

    @property
    def primary_sweep(self):
        """Primary sweep.

        Parameters
        ----------
        ps : float
            Perimeter of the source.
        """
        return self._primary_sweep

    @primary_sweep.setter
    def primary_sweep(self, ps):
        if ps in self._sweeps_names:
            self._primary_sweep = ps

    @property
    def expressions(self):
        """Expressions."""
        if not self._expressions:
            mydata = [i for i in self._nominal_variation.GetDataExpressions()]
            self._expressions = list(dict.fromkeys(mydata))
        return self._expressions

    @pyaedt_function_handler()
    def update_sweeps(self):
        """Update sweeps.

        Returns
        -------
        dict
            Updated sweeps.
        """
        names = list(self.nominal_variation.GetSweepNames())
        for data in self._original_data:
            for v in data.GetDesignVariableNames():
                if v not in self._sweeps_names:
                    self._sweeps_names.append(v)
        self._sweeps_names.extend((reversed(names)))

    @staticmethod
    @pyaedt_function_handler()
    def _quantity(unit):
        """Get the corresponding AEDT units.

        Parameters
        ----------
        unit : str
            The unit to be looked among the available AEDT units.

        Returns
        -------
            str
            The AEDT units.

        """
        for el in AEDT_UNITS:
            keys_units = [i.lower() for i in list(AEDT_UNITS[el].keys())]
            if unit.lower() in keys_units:
                return el
        return None

    @pyaedt_function_handler()
    def init_solutions_data(self):
        """Initialize the database and store info in variables."""
        self._solutions_real = self._init_solution_data_real()
        self._solutions_imag = self._init_solution_data_imag()
        self._solutions_mag = self._init_solution_data_mag()
        self._solutions_phase = self._init_solution_data_phase()

    @pyaedt_function_handler()
    def _init_solution_data_mag(self):
        _solutions_mag = {}
        self.units_data = {}

        for expr in self.expressions:
            _solutions_mag[expr] = {}
            self.units_data[expr] = self.nominal_variation.GetDataUnits(expr)
            if self.enable_pandas_output:
                _solutions_mag[expr] = np.sqrt(
                    self._solutions_real[expr]
                    .mul(self._solutions_real[expr])
                    .add(self._solutions_imag[expr].mul(self._solutions_imag[expr]))
                )
            else:
                for i in self._solutions_real[expr]:
                    _solutions_mag[expr][i] = abs(complex(self._solutions_real[expr][i], self._solutions_imag[expr][i]))
        if self.enable_pandas_output:
            return pd.DataFrame.from_dict(_solutions_mag)
        else:
            return _solutions_mag

    @pyaedt_function_handler()
    def _init_solution_data_real(self):
        """ """
        sols_data = {}

        for expression in self.expressions:
            solution_Data = {}

            for data, comb in zip(self._original_data, self.variations):
                solution = list(data.GetRealDataValues(expression, False))
                values = []
                for el in list(self.intrinsics.keys()):
                    values.append(list(OrderedDict.fromkeys(data.GetSweepValues(el, False))))

                i = 0
                c = [comb[v] for v in list(comb.keys())]
                for t in itertools.product(*values):
                    solution_Data[tuple(c + list(t))] = solution[i]
                    i += 1
            sols_data[expression] = solution_Data
        if self.enable_pandas_output:
            return pd.DataFrame.from_dict(sols_data)
        else:
            return sols_data

    @pyaedt_function_handler()
    def _init_solution_data_imag(self):
        """ """
        sols_data = {}

        for expression in self.expressions:
            solution_Data = {}
            for data, comb in zip(self._original_data, self.variations):
                if data.IsDataComplex(expression):
                    solution = list(data.GetImagDataValues(expression, False))
                else:
                    l = len(list(data.GetRealDataValues(expression, False)))
                    solution = [0] * l
                values = []
                for el in list(self.intrinsics.keys()):
                    values.append(list(OrderedDict.fromkeys(data.GetSweepValues(el, False))))
                i = 0
                c = [comb[v] for v in list(comb.keys())]
                for t in itertools.product(*values):
                    solution_Data[tuple(c + list(t))] = solution[i]
                    i += 1
            sols_data[expression] = solution_Data
        if self.enable_pandas_output:
            return pd.DataFrame.from_dict(sols_data)
        else:
            return sols_data

    @pyaedt_function_handler()
    def _init_solution_data_phase(self):
        data_phase = {}
        for expr in self.expressions:
            data_phase[expr] = {}
            if self.enable_pandas_output:
                data_phase[expr] = np.arctan2(self._solutions_imag[expr], self._solutions_real[expr])
            else:
                for i in self._solutions_real[expr]:
                    data_phase[expr][i] = math.atan2(self._solutions_imag[expr][i], self._solutions_real[expr][i])
        if self.enable_pandas_output:
            return pd.DataFrame.from_dict(data_phase)
        else:
            return data_phase

    @property
    def full_matrix_real_imag(self):
        """Get the full available solution data in Real and Imaginary parts.

        Returns
        -------
        tuple of dicts
            (Real Dict, Imag Dict)
        """
        return self._solutions_real, self._solutions_imag

    @property
    def full_matrix_mag_phase(self):
        """Get the full available solution data magnitude and phase in radians.

        Returns
        -------
        tuple of dicts
            (Mag Dict, Phase Dict).
        """
        return self._solutions_mag, self._solutions_phase

    @staticmethod
    @pyaedt_function_handler()
    def to_degrees(input_list):
        """Convert an input list from radians to degrees.

        Parameters
        ----------
        input_list : list
            List of inputs in radians.

        Returns
        -------
        list
            List of inputs in degrees.

        """
        if isinstance(input_list, (tuple, list)):
            return [i * 360 / (2 * math.pi) for i in input_list]
        else:
            return input_list * 360 / (2 * math.pi)

    @staticmethod
    @pyaedt_function_handler()
    def to_radians(input_list):
        """Convert an input list from degrees to radians.

        Parameters
        ----------
        input_list : list
            List of inputs in degrees.

        Returns
        -------
        type
            List of inputs in radians.

        """
        if isinstance(input_list, (tuple, list)):
            return [i * 2 * math.pi / 360 for i in input_list]
        else:
            return input_list * 2 * math.pi / 360

    @pyaedt_function_handler()
    def _variation_tuple(self):
        temp = []
        for it in self._sweeps_names:
            try:
                temp.append(self.active_variation[it])
            except KeyError:
                temp.append(self.active_intrinsic[it])
        return temp

    @pyaedt_function_handler()
    def data_magnitude(self, expression=None, convert_to_SI=False):
        """Retrieve the data magnitude of an expression.

        Parameters
        ----------
        expression : str, optional
            Name of the expression. The default is ``None``, in which case the
            active expression is used.
        convert_to_SI : bool, optional
            Whether to convert the data to the SI unit system.
            The default is ``False``.

        Returns
        -------
        list
            List of data.

        """
        if not expression:
            expression = self.active_expression
        elif expression not in self.expressions:
            return False
        temp = self._variation_tuple()
        solution_Data = self._solutions_mag[expression]
        sol = []
        position = list(self._sweeps_names).index(self.primary_sweep)
        sw = self.variation_values(self.primary_sweep)
        for el in sw:
            temp[position] = el
            try:
                sol.append(solution_Data[tuple(temp)])
            except KeyError:
                sol.append(None)
        if convert_to_SI and self._quantity(self.units_data[expression]):
            sol = self._convert_list_to_SI(
                sol, self._quantity(self.units_data[expression]), self.units_data[expression]
            )
        if self.enable_pandas_output:
            return pd.Series(sol)
        return sol

    @staticmethod
    @pyaedt_function_handler()
    def _convert_list_to_SI(datalist, dataunits, units):
        """Convert a data list to the SI unit system.

        Parameters
        ----------
        datalist : list
           List of data to convert.
        dataunits :

        units :


        Returns
        -------
        list
           List of the data converted to the SI unit system.

        """
        sol = datalist
        if dataunits in AEDT_UNITS and units in AEDT_UNITS[dataunits]:
            sol = [i * AEDT_UNITS[dataunits][units] for i in datalist]
        return sol

    @pyaedt_function_handler()
    def data_db10(self, expression=None, convert_to_SI=False):
        """Retrieve the data in the database for an expression and convert in db10.

        Parameters
        ----------
        expression : str, optional
            Name of the expression. The default is ``None``,
            in which case the active expression is used.
        convert_to_SI : bool, optional
            Whether to convert the data to the SI unit system.
            The default is ``False``.

        Returns
        -------
        list
            List of the data in the database for the expression.

        """
        if not expression:
            expression = self.active_expression
        if self.enable_pandas_output:
            return 10 * np.log10(self.data_magnitude(expression, convert_to_SI))
        return [db10(i) for i in self.data_magnitude(expression, convert_to_SI)]

    @pyaedt_function_handler()
    def data_db20(self, expression=None, convert_to_SI=False):
        """Retrieve the data in the database for an expression and convert in db20.

        Parameters
        ----------
        expression : str, optional
            Name of the expression. The default is ``None``,
            in which case the active expression is used.
        convert_to_SI : bool, optional
            Whether to convert the data to the SI unit system.
            The default is ``False``.

        Returns
        -------
        list
            List of the data in the database for the expression.

        """
        if not expression:
            expression = self.active_expression
        if self.enable_pandas_output:
            return 20 * np.log10(self.data_magnitude(expression, convert_to_SI))
        return [db20(i) for i in self.data_magnitude(expression, convert_to_SI)]

    @pyaedt_function_handler()
    def data_phase(self, expression=None, radians=True):
        """Retrieve the phase part of the data for an expression.

        Parameters
        ----------
        expression : str, None
            Name of the expression. The default is ``None``,
            in which case the active expression is used.
        radians : bool, optional
            Whether to convert the data into radians or degree.
            The default is ``True`` for radians.

        Returns
        -------
        list
            Phase data for the expression.

        """
        if not expression:
            expression = self.active_expression
        coefficient = 1
        if not radians:
            coefficient = 180 / math.pi
        if self.enable_pandas_output:
            return coefficient * np.arctan2(self.data_imag(expression), self.data_real(expression))
        return [coefficient * math.atan2(k, i) for i, k in zip(self.data_real(expression), self.data_imag(expression))]

    @property
    def primary_sweep_values(self):
        """Retrieve the primary sweep for a given data and primary variable.

        Returns
        -------
        list
            List of the primary sweep valid points for the expression.

        """
        if self.enable_pandas_output:
            return pd.Series(self.variation_values(self.primary_sweep))
        return self.variation_values(self.primary_sweep)

    @property
    def primary_sweep_variations(self):
        """Retrieve the variations lists for a given primary variable.

        Returns
        -------
        list
            List of the primary sweep valid points for the expression.

        """
        expression = self.active_expression
        temp = self._variation_tuple()

        solution_Data = list(self._solutions_real[expression].keys())
        sol = []
        position = list(self._sweeps_names).index(self.primary_sweep)

        for el in self.primary_sweep_values:
            temp[position] = el
            if tuple(temp) in solution_Data:
                sol_dict = OrderedDict({})
                i = 0
                for sn in self._sweeps_names:
                    sol_dict[sn] = temp[i]
                    i += 1
                sol.append(sol_dict)
            else:
                sol.append(None)
        if self.enable_pandas_output:
            return pd.Series(sol)
        return sol

    @pyaedt_function_handler()
    def data_real(self, expression=None, convert_to_SI=False):
        """Retrieve the real part of the data for an expression.

        Parameters
        ----------
        expression : str, None
            Name of the expression. The default is ``None``,
            in which case the active expression is used.
        convert_to_SI : bool, optional
            Whether to convert the data to the SI unit system.
            The default is ``False``.

        Returns
        -------
        list
            List of the real data for the expression.

        """
        if not expression:
            expression = self.active_expression
        temp = self._variation_tuple()

        solution_Data = self._solutions_real[expression]
        sol = []
        position = list(self._sweeps_names).index(self.primary_sweep)

        for el in self.primary_sweep_values:
            temp[position] = el
            try:
                sol.append(solution_Data[tuple(temp)])
            except KeyError:
                sol.append(None)

        if convert_to_SI and self._quantity(self.units_data[expression]):
            sol = self._convert_list_to_SI(
                sol, self._quantity(self.units_data[expression]), self.units_data[expression]
            )
        if self.enable_pandas_output:
            return pd.Series(sol)
        return sol

    @pyaedt_function_handler()
    def data_imag(self, expression=None, convert_to_SI=False):
        """Retrieve the imaginary part of the data for an expression.

        Parameters
        ----------
        expression : str, optional
            Name of the expression. The default is ``None``,
            in which case the active expression is used.
        convert_to_SI : bool, optional
            Whether to convert the data to the SI unit system.
            The default is ``False``.

        Returns
        -------
        list
            List of the imaginary data for the expression.

        """
        if not expression:
            expression = self.active_expression
        temp = self._variation_tuple()

        solution_Data = self._solutions_imag[expression]
        sol = []
        position = list(self._sweeps_names).index(self.primary_sweep)
        for el in self.primary_sweep_values:
            temp[position] = el
            try:
                sol.append(solution_Data[tuple(temp)])
            except KeyError:
                sol.append(None)
        if convert_to_SI and self._quantity(self.units_data[expression]):
            sol = self._convert_list_to_SI(
                sol, self._quantity(self.units_data[expression]), self.units_data[expression]
            )
        if self.enable_pandas_output:
            return pd.Series(sol)
        return sol

    @pyaedt_function_handler()
    def is_real_only(self, expression=None):
        """Check if the expression has only real values or not.

        Parameters
        ----------
        expression : str, optional
            Name of the expression. The default is ``None``,
            in which case the active expression is used.

        Returns
        -------
        bool
            ``True`` if the Solution Data for specific expression contains only real values.
        """
        if not expression:
            expression = self.active_expression
        if self.enable_pandas_output:
            return True if self._solutions_imag[expression].abs().sum() > 0.0 else False
        for v in list(self._solutions_imag[expression].values()):
            if float(v) != 0.0:
                return False
        return True

    @pyaedt_function_handler()
    def export_data_to_csv(self, output, delimiter=";"):
        """Save to output csv file the Solution Data.

        Parameters
        ----------
        output : str,
            Full path to csv file.
        delimiter : str,
            CSV Delimiter. Default is ``";"``.

        Returns
        -------
        bool
        """
        header = [el for el in self._sweeps_names]
        for el in self.expressions:
            if not self.is_real_only(el):
                header.append(el + " (Real)")
                header.append(el + " (Imag)")
            else:
                header.append(el)

        list_full = [header]
        for e, v in self._solutions_real[self.active_expression].items():
            list_full.append(list(e))
        for el in self.expressions:
            i = 1
            for e, v in self._solutions_real[el].items():
                list_full[i].extend([v])
                i += 1
            i = 1
            if not self.is_real_only(el):
                for e, v in self._solutions_imag[el].items():
                    list_full[i].extend([v])
                    i += 1

        return write_csv(output, list_full, delimiter=delimiter)

    @pyaedt_function_handler()
    def plot(
        self,
        curves=None,
        math_formula=None,
        size=(2000, 1000),
        show_legend=True,
        xlabel="",
        ylabel="",
        title="",
        snapshot_path=None,
        is_polar=False,
    ):
        """Create a matplotlib plot based on a list of data.

        Parameters
        ----------
        curves : list
            Curves to be plotted. If None, the first curve will be plotted.
        math_formula : str , optional
            Mathematical formula to apply to the plot curve.
            Valid values are `"re"`, `"im"`, `"db20"`, `"db10"`, `"abs"`, `"mag"`, `"phasedeg"`, `"phaserad"`.
            `None` value will plot only real value of the data stored in solution data.
        size : tuple, optional
            Image size in pixel (width, height).
        show_legend : bool
            Either to show legend or not. Flag will be ignored if number of curves to plot is greater than 15.
        xlabel : str
            Plot X label.
        ylabel : str
            Plot Y label.
        title : str
            Plot Title label.
        snapshot_path : str
            Full path to image file if a snapshot is needed.
        is_polar : bool, optional
            Set to `True` if this is a polar plot.

        Returns
        -------
        :class:`matplotlib.plt`
            Matplotlib fig object.
        """
        if is_ironpython:
            return False  # pragma: no cover
        if not curves:
            curves = [self.active_expression]
        if isinstance(curves, str):
            curves = [curves]
        data_plot = []
        sweep_name = self.primary_sweep
        if is_polar:
            sw = self.to_radians(self.primary_sweep_values)
        else:
            sw = self.primary_sweep_values
        for curve in curves:
            if not math_formula:
                data_plot.append([sw, self.data_real(curve), curve])
            elif math_formula == "re":
                data_plot.append([sw, self.data_real(curve), "{}({})".format(math_formula, curve)])
            elif math_formula == "im":
                data_plot.append([sw, self.data_imag(curve), "{}({})".format(math_formula, curve)])
            elif math_formula == "db20":
                data_plot.append([sw, self.data_db20(curve), "{}({})".format(math_formula, curve)])
            elif math_formula == "db10":
                data_plot.append([sw, self.data_db10(curve), "{}({})".format(math_formula, curve)])
            elif math_formula == "mag":
                data_plot.append([sw, self.data_magnitude(curve), "{}({})".format(math_formula, curve)])
            elif math_formula == "phasedeg":
                data_plot.append([sw, self.data_phase(curve, False), "{}({})".format(math_formula, curve)])
            elif math_formula == "phaserad":
                data_plot.append([sw, self.data_phase(curve, True), "{}({})".format(math_formula, curve)])
        if not xlabel:
            xlabel = sweep_name
        if not ylabel:
            ylabel = math_formula
        if not title:
            title = "Simulation Results Plot"
        if len(data_plot) > 15:
            show_legend = False
        if is_polar:
            return plot_polar_chart(data_plot, size, show_legend, xlabel, ylabel, title, snapshot_path)
        else:
            return plot_2d_chart(data_plot, size, show_legend, xlabel, ylabel, title, snapshot_path)

    @pyaedt_function_handler()
    def plot_3d(
        self,
        curve=None,
        x_axis="Theta",
        y_axis="Phi",
        xlabel="",
        ylabel="",
        title="",
        math_formula=None,
        size=(2000, 1000),
        snapshot_path=None,
    ):
        """Create a matplotlib 3d plot based on a list of data.

        Parameters
        ----------
        curve : str
            Curve to be plotted. If None, the first curve will be plotted.
        x_axis : str, optional
            X Axis sweep. Default is `"Theta"`.
        y_axis : str, optional
            Y Axis sweep. Default is `"Phi"`.
        math_formula : str , optional
            Mathematical formula to apply to the plot curve.
            Valid values are `"re"`, `"im"`, `"db20"`, `"db10"`, `"abs"`, `"mag"`, `"phasedeg"`, `"phaserad"`.
        size : tuple, optional
            Image size in pixel (width, height).
        snapshot_path : str
            Full path to image file if a snapshot is needed.
        is_polar : bool, optional
            Set to `True` if this is a polar plot.

        Returns
        -------
        :class:`matplotlib.plt`
            Matplotlib fig object.
        """
        if is_ironpython:
            return False  # pragma: no cover
        if not curve:
            curve = self.active_expression

        if not math_formula:
            math_formula = "mag"
        theta = self.variation_values(x_axis)
        y_axis_val = self.variation_values(y_axis)

        phi = []
        r = []
        for el in y_axis_val:
            self.active_variation[y_axis] = el
            phi.append(el * math.pi / 180)

            if math_formula == "re":
                r.append(self.data_real(curve))
            elif math_formula == "im":
                r.append(self.data_imag(curve))
            elif math_formula == "db20":
                r.append(self.data_db20(curve))
            elif math_formula == "db10":
                r.append(self.data_db10(curve))
            elif math_formula == "mag":
                r.append(self.data_magnitude(curve))
            elif math_formula == "phasedeg":
                r.append(self.data_phase(curve, False))
            elif math_formula == "phaserad":
                r.append(self.data_phase(curve, True))
        active_sweep = self.active_intrinsic[self.primary_sweep]
        position = self.variation_values(self.primary_sweep).index(active_sweep)
        if len(self.variation_values(self.primary_sweep)) > 1:
            new_r = []
            for el in r:
                new_r.append([el[position]])
            r = new_r
        data_plot = [theta, phi, r]
        if not xlabel:
            xlabel = x_axis
        if not ylabel:
            ylabel = y_axis
        if not title:
            title = "Simulation Results Plot"
        return plot_3d_chart(data_plot, size, xlabel, ylabel, title, snapshot_path)

    @pyaedt_function_handler()
    def ifft(self, curve_header="NearE", u_axis="_u", v_axis="_v", window=False):
        """Create IFFT of given complex data.

        Parameters
        ----------
        curve_header : curve header. Solution data must contain 3 curves with X, Y and Z components of curve header.
        u_axis : str, optional
            U Axis name. Default is Hfss name "_u"
        v_axis : str, optional
            V Axis name. Default is Hfss name "_v"
        window : bool, optional
            Either if Hanning windowing has to be applied.

        Returns
        -------
        List
            IFFT Matrix.
        """
        if is_ironpython:
            return False
        u = self.variation_values(u_axis)
        v = self.variation_values(v_axis)

        freq = self.variation_values("Freq")
        if self.enable_pandas_output:
            E_realx = np.reshape(self._solutions_real[curve_header + "X"].copy().values, (len(freq), len(v), len(u)))
            E_imagx = np.reshape(self._solutions_imag[curve_header + "X"].copy().values, (len(freq), len(v), len(u)))
            E_realy = np.reshape(self._solutions_real[curve_header + "Y"].copy().values, (len(freq), len(v), len(u)))
            E_imagy = np.reshape(self._solutions_imag[curve_header + "Y"].copy().values, (len(freq), len(v), len(u)))
            E_realz = np.reshape(self._solutions_real[curve_header + "Z"].copy().values, (len(freq), len(v), len(u)))
            E_imagz = np.reshape(self._solutions_imag[curve_header + "Z"].copy().values, (len(freq), len(v), len(u)))
        else:
            vals_real_Ex = [j for j in self._solutions_real[curve_header + "X"].values()]
            vals_imag_Ex = [j for j in self._solutions_imag[curve_header + "X"].values()]
            vals_real_Ey = [j for j in self._solutions_real[curve_header + "Y"].values()]
            vals_imag_Ey = [j for j in self._solutions_imag[curve_header + "Y"].values()]
            vals_real_Ez = [j for j in self._solutions_real[curve_header + "Z"].values()]
            vals_imag_Ez = [j for j in self._solutions_imag[curve_header + "Z"].values()]

            E_realx = np.reshape(vals_real_Ex, (len(freq), len(v), len(u)))
            E_imagx = np.reshape(vals_imag_Ex, (len(freq), len(v), len(u)))
            E_realy = np.reshape(vals_real_Ey, (len(freq), len(v), len(u)))
            E_imagy = np.reshape(vals_imag_Ey, (len(freq), len(v), len(u)))
            E_realz = np.reshape(vals_real_Ez, (len(freq), len(v), len(u)))
            E_imagz = np.reshape(vals_imag_Ez, (len(freq), len(v), len(u)))

        Temp_E_compx = E_realx + 1j * E_imagx  # Here is the complex FD data matrix, ready for transforming
        Temp_E_compy = E_realy + 1j * E_imagy
        Temp_E_compz = E_realz + 1j * E_imagz

        E_compx = np.zeros((len(freq), len(v), len(u)), dtype="complex_")
        E_compy = np.zeros((len(freq), len(v), len(u)), dtype="complex_")
        E_compz = np.zeros((len(freq), len(v), len(u)), dtype="complex_")
        if window:
            timewin = np.hanning(len(freq))

            for row in range(0, len(v)):
                for col in range(0, len(u)):
                    E_compx[:, row, col] = np.multiply(Temp_E_compx[:, row, col], timewin)
                    E_compy[:, row, col] = np.multiply(Temp_E_compy[:, row, col], timewin)
                    E_compz[:, row, col] = np.multiply(Temp_E_compz[:, row, col], timewin)
        else:
            E_compx = Temp_E_compx
            E_compy = Temp_E_compy
            E_compz = Temp_E_compz

        E_time_x = np.fft.ifft(np.fft.fftshift(E_compx, 0), len(freq), 0, None)
        E_time_y = np.fft.ifft(np.fft.fftshift(E_compy, 0), len(freq), 0, None)
        E_time_z = np.fft.ifft(np.fft.fftshift(E_compz, 0), len(freq), 0, None)
        E_time = np.zeros((np.size(freq), np.size(v), np.size(u)))
        for i in range(0, len(freq)):
            E_time[i, :, :] = np.abs(
                np.sqrt(np.square(E_time_x[i, :, :]) + np.square(E_time_y[i, :, :]) + np.square(E_time_z[i, :, :]))
            )
        self._ifft = E_time

        return self._ifft

    @pyaedt_function_handler()
    def ifft_to_file(
        self,
        u_axis="_u",
        v_axis="_v",
        coord_system_center=None,
        db_val=False,
        num_frames=None,
        csv_dir=None,
        name_str="res_",
    ):
        """Save IFFT Matrix to a list of csv files (one per time step).

        Parameters
        ----------
        u_axis : str, optional
            U Axis name. Default is Hfss name "_u"
        v_axis : str, optional
            V Axis name. Default is Hfss name "_v"
        coord_system_center : list, optional
            List of UV GlobalCS Center.
        db_val : bool, optional
            Either if data has to be exported in db or not.
        num_frames : int, optional
            Number of frames to export.
        csv_dir : str
            Output path
        name_str : str, optional
            csv file header.

        Returns
        -------
        str
            Path to file containing the list of csv files.
        """
        if not coord_system_center:
            coord_system_center = [0, 0, 0]
        t_matrix = self._ifft
        x_c_list = self.variation_values(u_axis)
        y_c_list = self.variation_values(v_axis)

        adj_x = coord_system_center[0]
        adj_y = coord_system_center[1]
        adj_z = coord_system_center[2]
        if num_frames:
            frames = num_frames
        else:
            frames = t_matrix.shape[0]
        csv_list = []
        if os.path.exists(csv_dir):
            files = [os.path.join(csv_dir, f) for f in os.listdir(csv_dir) if name_str in f and ".csv" in f]
            for file in files:
                os.remove(file)
        else:
            os.mkdir(csv_dir)

        for frame in range(frames):
            output = os.path.join(csv_dir, name_str + str(frame) + ".csv")
            list_full = [["x", "y", "z", "val"]]
            for i, y in enumerate(y_c_list):
                for j, x in enumerate(x_c_list):
                    y_coord = y + adj_y
                    x_coord = x + adj_x
                    z_coord = adj_z
                    if db_val:
                        val = 10.0 * np.log10(np.abs(t_matrix[frame, i, j]))
                    else:
                        val = t_matrix[frame, i, j]
                    row_lst = [x_coord, y_coord, z_coord, val]
                    list_full.append(row_lst)
            write_csv(output, list_full, delimiter=",")
            csv_list.append(output)

        txt_file_name = csv_dir + "fft_list.txt"
        textfile = open_file(txt_file_name, "w")

        for element in csv_list:
            textfile.write(element + "\n")
        textfile.close()
        return txt_file_name


class FfdSolutionData(object):
    """Contains Hfss Far Field Solution Data (ffd)."""

    def __init__(
        self,
        app,
        sphere_name,
        setup_name,
        frequencies,
        variations=None,
        overwrite=True,
        taper="flat",
        sbr_3d_comp_name=None,
    ):
        self._app = app
        self.levels = 64
        self._native_indexes = []
        self._port_indexes = {}
        self.all_max = 1
        self.sphere_name = sphere_name
        self.setup_name = setup_name
        self.sbr_comp = sbr_3d_comp_name
        if not isinstance(frequencies, list):
            self.frequencies = [frequencies]
        else:
            self.frequencies = frequencies
        self._frequency = self.frequencies[0]
        self.variations = variations
        self.overwrite = overwrite
        self._all_solutions = self._export_all_ffd()
        self.ffd_dict = self._all_solutions[0]
        self.lattice_vectors = self.get_lattice_vectors()
        self.taper = taper
        self.data_dict = {}
        self._init_ffd()
        self._phase_offset = [0] * len(self.all_port_names)

    @pyaedt_function_handler()
    def _init_ffd(self):
        all_ports = list(self.ffd_dict.keys())
        valid_ffd = True

        if os.path.exists(self.ffd_dict[all_ports[0]]):
            with open(self.ffd_dict[all_ports[0]], "r") as reader:
                theta = [int(i) for i in reader.readline().split()]
                phi = [int(i) for i in reader.readline().split()]
            reader.close()
            for port in self.ffd_dict.keys():
                if ":" in port:
                    port = port.split(":")[0]
                temp_dict = {}
                theta_range = np.linspace(*theta)
                phi_range = np.linspace(*phi)
                if os.path.exists(self.ffd_dict[port]):
                    eep_txt = np.loadtxt(self.ffd_dict[port], skiprows=4)
                    Etheta = np.vectorize(complex)(eep_txt[:, 0], eep_txt[:, 1])
                    Ephi = np.vectorize(complex)(eep_txt[:, 2], eep_txt[:, 3])
                    # eep=np.column_stack((etheta, ephi))
                    temp_dict["Theta"] = theta_range
                    temp_dict["Phi"] = phi_range
                    temp_dict["rETheta"] = Etheta
                    temp_dict["rEPhi"] = Ephi
                    self.data_dict[port] = temp_dict
                else:
                    valid_ffd = False
            if valid_ffd:
                # differential area of sphere, based on observation angle
                self.d_theta = np.abs(theta_range[1] - theta_range[0])
                self.d_phi = np.abs(phi_range[1] - phi_range[0])
                self.diff_area = np.radians(self.d_theta) * np.radians(self.d_phi) * np.sin(np.radians(theta_range))
                self.num_samples = len(temp_dict["rETheta"])
                self.all_port_names = list(self.data_dict.keys())
                if self._native_indexes:
                    i = 0
                    for p in self.all_port_names:
                        self._port_indexes[p] = self._native_indexes[i]
                        i += 1
                else:
                    for p in self.all_port_names:
                        self._port_indexes[p] = self.get_array_index(p)
                self.solution_type = "DrivenModal"
                self.unique_beams = None
                self.renormalize = False
                self.renormalize_dB = True
                self.renorm_value = 1
        else:
            valid_ffd = False
            self._app.logger.info("ERROR: Far Field Files are Missing")
        self.valid_ffd = valid_ffd
        self.Ax = float(self.lattice_vectors[0])
        self.Ay = float(self.lattice_vectors[1])
        self.Bx = float(self.lattice_vectors[3])
        self.By = float(self.lattice_vectors[4])
        self._phase_offset = [0] * len(self.all_port_names)
        self._mag_offset = [1] * len(self.all_port_names)
        self.beamform()

    @property
    def frequency(self):
        """Get/set the Active Frequency.

        Returns
        -------
        float
        """
        return self._frequency

    @frequency.setter
    def frequency(self, val):
        if val in self.frequencies:
            self._frequency = val
            self.ffd_dict = self._all_solutions[self.frequencies.index(val)]
            self._init_ffd()

    @property
    def phase_offset(self):
        """Additional phase offset in degrees on each port. Useful when element has more than one port.

        Returns
        -------
        list
        """
        return self._phase_offset

    @phase_offset.setter
    def phase_offset(self, phases):
        if len(phases) != len(self.all_port_names):
            self._app.logger.error("Number of phases must be equal to number of ports")
        else:
            phases_to_rad = []
            for phase in phases:
                phases_to_rad.append(math.radians(phase))
            self._phase_offset = phases_to_rad
            self.beamform()

    @property
    def mag_offset(self):
        """Additional magnitude on each port. Useful when element has more than one port.

        Returns
        -------
        list
        """
        return self._mag_offset

    @mag_offset.setter
    def mag_offset(self, mags):
        if len(mags) != len(self.all_port_names):
            self._app.logger.error("Number of magnitude must be equal to number of ports")
        else:
            self._mag_offset = mags
            self.beamform()

    @pyaedt_function_handler()
    def get_array_index(self, port_name):
        """Get index of a given port.

        Parameters
        ----------
        port_name : str

        Returns
        -------
        list of int
        """
        if self._port_indexes and port_name in self._port_indexes:
            return self._port_indexes[port_name]
        try:
            str1 = port_name.split("[", 1)[1].split("]", 1)[0]
            index_str = [int(i) for i in str1.split(",")]
        except:
            return [1, 1]
        return index_str

    @pyaedt_function_handler()
    def array_min_max_values(self):
        """Array bounding box.

        Returns
        -------
        list of float
        """
        row_min = 1
        row_max = 1
        col_min = 1
        col_max = 1
        rows = []
        cols = []
        for portstring in self.all_port_names:
            index_str = self.get_array_index(portstring)
            rows.append(index_str[1])
            cols.append(index_str[0])

        row_min = np.min(rows)
        row_max = np.max(rows)
        col_min = np.min(cols)
        col_max = np.max(cols)
        return [col_min, col_max, row_min, row_max]

    @pyaedt_function_handler()
    def array_center_and_edge(self):
        """Find the center and edge of our array, assuming all ports in far field
        mapping file are active ports.

        Returns
        -------
        bool
        """
        AMax = 0
        BMax = 0
        RMax = 0
        XMax = 0
        YMax = 0
        CenterA = 0
        CenterB = 0
        CenterX = 0
        CenterY = 0

        # collecting all active cells inside the specified region
        activeCells = []

        for i in range(0, len(self.all_port_names)):
            index_str = self.get_array_index(self.all_port_names[i])
            row = index_str[1]
            col = index_str[0]
            a = row
            b = col

            activeCells.append((a, b))  # because ffd is assuming all ffd files are active
        if len(activeCells) == 0:
            return

        [a_min, a_max, b_min, b_max] = self.array_min_max_values()

        CenterA = (a_min + a_max) / 2
        CenterB = (b_min + b_max) / 2
        CenterX = (CenterA + 0.5) * self.Ax + (CenterB + 0.5) * self.Bx
        CenterY = (CenterA + 0.5) * self.Ay + (CenterB + 0.5) * self.By

        self.CenterA = CenterA
        self.CenterB = CenterB
        self.CenterX = CenterX
        self.CenterY = CenterY
        # find the distance from the edge to the center
        AMax = a_max - a_min
        BMax = b_max - b_min

        self.AMax = AMax
        self.BMax = BMax
        for a, b in activeCells:
            x = (a + 0.5) * self.Ax + (b + 0.5) * self.Bx
            y = (a + 0.5) * self.Ay + (b + 0.5) * self.By
            x_dis = abs(x - CenterX)
            y_dis = abs(y - CenterY)
            distance = math.sqrt(x_dis**2 + y_dis**2)
            XMax = max(XMax, x_dis)
            YMax = max(YMax, y_dis)
            RMax = max(RMax, distance)

        self.RMax = RMax
        self.XMax = XMax
        self.YMax = YMax
        self.RMax *= 2
        self.XMax *= 2
        self.YMax *= 2
        return True

    @pyaedt_function_handler()
    def element_location(self, a, b):
        """Element location in the array.

        Parameters
        ----------
        a : int
        b : int

        Returns
        -------
        list of float
        """
        a = int(a)
        b = int(b)

        x = (a + 0.5) * self.Ax + (b + 0.5) * self.Bx
        y = (a + 0.5) * self.Ay + (b + 0.5) * self.By
        x_dis = x - self.CenterX
        y_dis = y - self.CenterY

        return np.array([x_dis, y_dis, 0])

    @pyaedt_function_handler()
    def assign_weight(self, a, b, taper="flat", port_cont=0):
        """Assign weight to array.

        Parameters
        ----------
        a : int
            Inndex of array, column.
        b : int
            Inndex of array, row.
        taper : string, optional
            This is the type of taper we want to apply. The default is 'flat'.
            It can be ``"cosine"``, ``"triangular"``, ``"hamming"`` or ``"flat"``.

        Returns
        -------
        float
            Weight to applied to specific index of array.
        """
        a = int(a)
        b = int(b)
        if taper.lower() == "flat":  # Flat
            return self.mag_offset[port_cont]

        cosinePow = 1
        edgeTaper_dB = -200

        edgeTaper = 10 ** ((float(edgeTaper_dB)) / 20)

        threshold = 1e-10
        length_in_direction1 = 0
        max_length_in_dir1 = 0
        length_in_direction2 = 0
        max_length_in_dir2 = 0
        w1 = w2 = None

        # find the distance between current cell and array center in terms of index
        length_in_direction1 = a - self.CenterA
        length_in_direction2 = b - self.CenterB
        max_length_in_dir1 = self.AMax
        max_length_in_dir2 = self.BMax

        if taper.lower() == "cosine":  # Cosine
            if max_length_in_dir1 < threshold:
                w1 = 1
            else:
                w1 = (1 - edgeTaper) * (
                    math.cos(math.pi * length_in_direction1 / max_length_in_dir1)
                ) ** cosinePow + edgeTaper
            if max_length_in_dir2 < threshold:
                w2 = 1
            else:
                w2 = (1 - edgeTaper) * (
                    math.cos(math.pi * length_in_direction2 / max_length_in_dir2)
                ) ** cosinePow + edgeTaper
        elif taper.lower() == "triangular":  # Triangular
            if max_length_in_dir1 < threshold:
                w1 = 1
            else:
                w1 = (1 - edgeTaper) * (1 - (math.fabs(length_in_direction1) / (max_length_in_dir1 / 2))) + edgeTaper
            if max_length_in_dir2 < threshold:
                w2 = 1
            else:
                w2 = (1 - edgeTaper) * (1 - (math.fabs(length_in_direction2) / (max_length_in_dir2 / 2))) + edgeTaper
        elif taper.lower() == "hamming":  # Hamming Window
            if max_length_in_dir1 < threshold:
                w1 = 1
            else:
                w1 = 0.54 - 0.46 * math.cos(2 * math.pi * (length_in_direction1 / max_length_in_dir1 - 0.5))
            if max_length_in_dir2 < threshold:
                w2 = 1
            else:
                w2 = 0.54 - 0.46 * math.cos(2 * math.pi * (length_in_direction2 / max_length_in_dir2 - 0.5))
        else:
            return 0

        return w1 * w2 * self.mag_offset[port_cont]

    @pyaedt_function_handler()
    def beamform(self, phi_scan=0, theta_scan=0):
        """Compute the far field pattern calculated for a specific phi/scan angle requested.
        This is calculated based on the lattice vector spacing and the embedded element
        patterns of a ca-ddm or fa-ddm array in HFSS.
        Calculates phase shifts between array elements in A and B directions,
        PhaseShiftA and PhaseShiftB, given Wave Vector (k), lattice vectors
        (Ax, Ay, Bx, By), Scan angles (theta, phi) using formula below
        Phase Shift A = - (Ax*k*sin(theta)*cos(phi) + Ay*k*sin(theta)*sin(phi))
        Phase Shift B = - (Bx*k*sin(theta)*cos(phi) + By*k*sin(theta)*sin(phi)).

        Parameters
        ----------
        phi_scan : int, float
            Spherical cs for desired scan angle of beam.
        theta_scan: : int, float
            Spherical cs for desired scan angle of beam.

        Returns
        -------
        dict
            Updated quantities dictionary.
        """
        num_ports = len(self.all_port_names)
        self.array_center_and_edge()

        c = 299792458
        k = (2 * math.pi * self.frequency) / c

        theta_scan = math.radians(theta_scan)
        phi_scan = math.radians(phi_scan)

        phase_shift_A_rad = -1 * (
            (self.Ax * k * math.sin(theta_scan) * math.cos(phi_scan))
            + (self.Ay * k * math.sin(theta_scan) * math.sin(phi_scan))
        )
        phase_shift_B_rad = -1 * (
            (self.Bx * k * math.sin(theta_scan) * math.cos(phi_scan))
            + (self.By * k * math.sin(theta_scan) * math.sin(phi_scan))
        )

        w_dict = {}
        w_dict_ang = {}
        w_dict_mag = {}
        array_positions = {}
        port_cont = 0
        for port_name in self.all_port_names:
            index_str = self.get_array_index(port_name)
            a = index_str[0] - 1
            b = index_str[1] - 1
            w_mag = np.round(np.abs(self.assign_weight(a, b, taper=self.taper, port_cont=port_cont)), 3)
            w_ang = self.phase_offset[port_cont] + (a * phase_shift_A_rad + b * phase_shift_B_rad)
            w_dict[port_name] = np.sqrt(w_mag) * np.exp(1j * w_ang)
            w_dict_ang[port_name] = w_ang
            w_dict_mag[port_name] = w_mag
            array_positions[port_name] = self.element_location(a, b)
            port_cont += 1

        length_of_ff_data = len(self.data_dict[self.all_port_names[0]]["rETheta"])

        rEtheta_fields = np.zeros((num_ports, length_of_ff_data), dtype=complex)
        rEphi_fields = np.zeros((num_ports, length_of_ff_data), dtype=complex)
        w = np.zeros((1, num_ports), dtype=complex)
        # create port mapping
        for n, port in enumerate(self.all_port_names):
            re_theta = self.data_dict[port]["rETheta"]  # this is re_theta index of loaded data
            re_phi = self.data_dict[port]["rEPhi"]  # this is re_ohi index of loaded data

            w[0][n] = w_dict[port]  # build 1xNumPorts array of weights

            rEtheta_fields[n] = re_theta
            rEphi_fields[n] = re_phi

            theta_range = self.data_dict[port]["Theta"]
            phi_range = self.data_dict[port]["Phi"]
            Ntheta = len(theta_range)
            Nphi = len(phi_range)

        rEtheta_fields_sum = np.dot(w, rEtheta_fields)
        rEtheta_fields_sum = np.reshape(rEtheta_fields_sum, (Ntheta, Nphi))

        rEphi_fields_sum = np.dot(w, rEphi_fields)
        rEphi_fields_sum = np.reshape(rEphi_fields_sum, (Ntheta, Nphi))

        self.all_qtys = {}
        self.all_qtys["rEPhi"] = rEphi_fields_sum
        self.all_qtys["rETheta"] = rEtheta_fields_sum
        self.all_qtys["rETotal"] = np.sqrt(
            np.power(np.abs(rEphi_fields_sum), 2) + np.power(np.abs(rEtheta_fields_sum), 2)
        )
        self.all_qtys["Theta"] = theta_range
        self.all_qtys["Phi"] = phi_range
        self.all_qtys["nPhi"] = Nphi
        self.all_qtys["nTheta"] = Ntheta
        pin = np.sum(np.power(np.abs(w), 2))
        self.all_qtys["Pincident"] = pin
        self._app.logger.info("Incident Power: %s", pin)
        real_gain = 2 * np.pi * np.abs(np.power(self.all_qtys["rETotal"], 2)) / pin / 377
        self.all_qtys["RealizedGain"] = real_gain
        self.all_qtys["RealizedGain_dB"] = 10 * np.log10(real_gain)
        self.max_gain = np.max(10 * np.log10(real_gain))
        self.min_gain = np.min(10 * np.log10(real_gain))
        self._app.logger.info("Peak Realized Gain: %s dB", self.max_gain)
        self.all_qtys["Element_Location"] = array_positions

        return self.all_qtys

    @pyaedt_function_handler()
    def beamform_2beams(self, phi_scan1=0, theta_scan1=0, phi_scan2=0, theta_scan2=0):
        """Compute the far field pattern calculated for a specific phi/scan angle requested.
        This is calculated based on the lattice vector spacing and the embedded element
        patterns of a ca-ddm or fa-ddm array in HFSS.

        Parameters
        ----------
        phi_scan1 : int, float
            Spherical cs for desired scan angle of beam.
        theta_scan1: : int, float
            Spherical cs for desired scan angle of beam.
        phi_scan2 : int, float
            Spherical cs for desired scan angle of second beam.
        theta_scan2 : int, float
            Spherical cs for desired scan angle of second beam.

        Returns
        -------
        dict
            Updated quantities dictionary.
        """
        num_ports = len(self.all_port_names)
        self.array_center_and_edge()

        c = 299792458
        k = (2 * math.pi * self.frequency) / c

        # ---------------------- METHOD : CalculatePhaseShifts -------------------
        # Calculates phase shifts between array elements in A and B directions,
        # PhaseShiftA and PhaseShiftB, given Wave Vector (k), lattice vectors
        # (Ax, Ay, Bx, By), Scan angles (theta, phi) using formula below
        # Phase Shift A = - (Ax*k*sin(theta)*cos(phi) + Ay*k*sin(theta)*sin(phi))
        # Phase Shift B = - (Bx*k*sin(theta)*cos(phi) + By*k*sin(theta)*sin(phi))
        # ------------------------------------------------------------------------

        theta_scan1 = math.radians(theta_scan1)
        phi_scan1 = math.radians(phi_scan1)

        theta_scan2 = math.radians(theta_scan2)
        phi_scan2 = math.radians(phi_scan2)

        phase_shift_A_rad1 = -1 * (
            (self.Ax * k * math.sin(theta_scan1) * math.cos(phi_scan1))
            + (self.Ay * k * math.sin(theta_scan1) * math.sin(phi_scan1))
        )
        phase_shift_B_rad1 = -1 * (
            (self.Bx * k * math.sin(theta_scan1) * math.cos(phi_scan1))
            + (self.By * k * math.sin(theta_scan1) * math.sin(phi_scan1))
        )

        phase_shift_A_rad2 = -1 * (
            (self.Ax * k * math.sin(theta_scan2) * math.cos(phi_scan2))
            + (self.Ay * k * math.sin(theta_scan2) * math.sin(phi_scan2))
        )
        phase_shift_B_rad2 = -1 * (
            (self.Bx * k * math.sin(theta_scan2) * math.cos(phi_scan2))
            + (self.By * k * math.sin(theta_scan2) * math.sin(phi_scan2))
        )

        w_dict = {}
        w_dict_ang = {}
        w_dict_mag = {}
        array_positions = {}
        port_count = 0
        for port_name in self.all_port_names:
            index_str = self.get_array_index(port_name)
            a = index_str[0]
            b = index_str[1]
            w_mag1 = np.round(np.abs(self.assign_weight(a, b, taper=self.taper, port_cont=port_count)), 3)
            w_ang1 = a * phase_shift_A_rad1 + b * phase_shift_B_rad1

            w_mag2 = np.round(np.abs(self.assign_weight(a, b, taper=self.taper, port_cont=port_count)), 3)
            w_ang2 = a * phase_shift_A_rad2 + b * phase_shift_B_rad2

            w_dict[port_name] = np.sqrt(w_mag1) * np.exp(1j * w_ang1) + np.sqrt(w_mag2) * np.exp(1j * w_ang2)
            w_dict_ang[port_name] = np.angle(w_dict[port_name])
            w_dict_mag[port_name] = np.abs(w_dict[port_name])

            array_positions[port_name] = self.element_location(a, b)
            port_count += 1

        length_of_ff_data = len(self.data_dict[self.all_port_names[0]]["rETheta"])
        rEtheta_fields = np.zeros((num_ports, length_of_ff_data), dtype=complex)
        rEphi_fields = np.zeros((num_ports, length_of_ff_data), dtype=complex)
        w = np.zeros((1, num_ports), dtype=complex)
        # create port mapping
        for n, port in enumerate(self.all_port_names):
            re_theta = self.data_dict[port]["rETheta"]  # this is re_theta index of loaded data
            re_phi = self.data_dict[port]["rEPhi"]  # this is re_ohi index of loaded data

            w[0][n] = w_dict[port]  # build 1xNumPorts array of weights

            rEtheta_fields[n] = re_theta
            rEphi_fields[n] = re_phi

            theta_range = self.data_dict[port]["Theta"]
            phi_range = self.data_dict[port]["Phi"]
            Ntheta = len(theta_range)
            Nphi = len(phi_range)

        rEtheta_fields_sum = np.dot(w, rEtheta_fields)
        rEtheta_fields_sum = np.reshape(rEtheta_fields_sum, (Ntheta, Nphi))

        rEphi_fields_sum = np.dot(w, rEphi_fields)
        rEphi_fields_sum = np.reshape(rEphi_fields_sum, (Ntheta, Nphi))

        self.all_qtys = {}
        self.all_qtys["rEPhi"] = rEphi_fields_sum
        self.all_qtys["rETheta"] = rEtheta_fields_sum
        self.all_qtys["rETotal"] = np.sqrt(
            np.power(np.abs(rEphi_fields_sum), 2) + np.power(np.abs(rEtheta_fields_sum), 2)
        )
        self.all_qtys["Theta"] = theta_range
        self.all_qtys["Phi"] = phi_range
        self.all_qtys["nPhi"] = Nphi
        self.all_qtys["nTheta"] = Ntheta
        pin = np.sum(np.power(np.abs(w), 2))
        self.all_qtys["Pincident"] = pin
        self._app.logger.info("Incident Power: %s", pin)
        real_gain = 2 * np.pi * np.abs(np.power(self.all_qtys["rETotal"], 2)) / pin / 377
        self.all_qtys["RealizedGain"] = real_gain
        self.all_qtys["RealizedGain_dB"] = 10 * np.log10(real_gain)
        self.max_gain = np.max(10 * np.log10(real_gain))
        self.min_gain = np.min(10 * np.log10(real_gain))
        self._app.logger.info("Peak Realized Gain: %s dB", self.max_gain)
        self.all_qtys["Element_Location"] = array_positions

        return self.all_qtys

    @pyaedt_function_handler()
    def _get_far_field_mesh(self, qty_str="RealizedGain", convert_to_db=True):
        if convert_to_db:
            ff_data = 10 * np.log10(self.all_qtys[qty_str])

        else:
            ff_data = self.all_qtys[qty_str]
        theta = np.deg2rad(np.array(self.all_qtys["Theta"]))
        phi = np.deg2rad(np.array(self.all_qtys["Phi"]))
        self.mesh = get_structured_mesh(theta=theta, phi=phi, ff_data=ff_data)

    @pyaedt_function_handler()
    def get_lattice_vectors(self):
        """Compute Lattice vectors for Antenna Arrays or return default array in case of simple antenna analysis.

        Returns
        -------
        list of float
        """
        if self.sbr_comp and self.sbr_comp in self._app.modeler.user_defined_components:
            component_props = "NativeComponentDefinitionProvider"
            comp_obj = self._app.modeler.user_defined_components[self.sbr_comp]
            if "Project" in list(comp_obj.native_properties.keys()):
                # Project opened
                project = comp_obj.native_properties["Project"]
                proj_name = os.path.splitext(os.path.split(project)[-1])[0]
                close = False
                if proj_name not in self._app.project_list:
                    close = True
                    self._app.odesktop.OpenProject(project)
                comp = get_pyaedt_app(proj_name, comp_obj.native_properties["Design"])
                comp_units = comp.modeler.model_units
                lattice_vectors = comp.omodelsetup.GetLatticeVectors()
                source_names = [i[5:-1] for i in comp.post.available_report_quantities(quantities_category="VSWR")]
                for port in source_names:
                    try:
                        str1 = port.split("[", 1)[1].split("]", 1)[0]
                        self._native_indexes.append([int(i) for i in str1.split(",")])
                    except:
                        self._native_indexes.append([1, 1])
                if close:
                    comp.close_project()
            else:
                # Project not opened
                project = comp_obj.native_properties[component_props]["Project"]
                proj_name = os.path.splitext(os.path.split(project)[-1])[0]
                close = False
                if proj_name not in self._app.project_list:
                    close = True
                    self._app.odesktop.OpenProject(project)
                comp = get_pyaedt_app(proj_name, comp_obj.native_properties[component_props]["Design"])
                lattice_vectors = comp.omodelsetup.GetLatticeVectors()
                comp_units = comp.modeler.model_units
                source_names = [i[5:-1] for i in comp.post.available_report_quantities(quantities_category="VSWR")]
                for port in source_names:
                    try:
                        str1 = port.split("[", 1)[1].split("]", 1)[0]
                        self._native_indexes.append([int(i) for i in str1.split(",")])
                    except:
                        self._native_indexes.append([1, 1])
                if close:
                    comp.close_project(save_project=False)

            lattice_vectors = [
                str(x)
                for x in unit_converter(
                    values=[float(i) for i in lattice_vectors],
                    unit_system="Length",
                    input_units=comp_units,
                    output_units=self._app.modeler.model_units,
                )
            ]
        else:
            try:
                lattice_vectors = self._app.omodelsetup.GetLatticeVectors()
                lattice_vectors = [
                    float(vec) * AEDT_UNITS["Length"][self._app.modeler.model_units] for vec in lattice_vectors
                ]
            except:
                lattice_vectors = [0, 0, 0, 0, 1, 0]
        return lattice_vectors

    @pyaedt_function_handler()
    def _export_all_ffd(self):
        exported_name_base = "eep"
        exported_name_map = exported_name_base + ".txt"
        sol_setup_name_str = self.setup_name.replace(":", "_").replace(" ", "")
        path_dict = []
        for frequency in self.frequencies:
            full_setup_str = "{}-{}-{}".format(sol_setup_name_str, self.sphere_name, frequency)
            export_path = "{}/{}/eep/".format(self._app.working_directory, full_setup_str)
            if settings.remote_rpc_session:
                settings.remote_rpc_session.filemanager.makedirs(export_path)
                file_exists = settings.remote_rpc_session.filemanager.pathexists(
                    export_path + exported_name_base + ".txt"
                )
            elif not os.path.exists(export_path):
                os.makedirs(export_path)
                file_exists = os.path.exists(export_path + exported_name_base + ".txt")
            else:
                file_exists = os.path.exists(export_path + exported_name_base + ".txt")
            path_dict.append({})
            time_before = time.time()
            if self.overwrite or not file_exists:
                self._app.logger.info("Exporting Embedded Element Patterns...")
                var = []
                if self.variations:
                    for k, v in self.variations.items():
                        var.append("{}='{}'".format(k, v))
                variation = " ".join(var)
                try:
                    self._app.oradfield.ExportElementPatternToFile(
                        [
                            "ExportFileName:=",
                            export_path + exported_name_base + ".ffd",
                            "SetupName:=",
                            self.sphere_name,
                            "IntrinsicVariationKey:=",
                            "Freq='" + str(frequency) + "'",
                            "DesignVariationKey:=",
                            variation,
                            "SolutionName:=",
                            self.setup_name,
                        ]
                    )
                except:
                    self._app.logger.error("Failed to export one Element Pattern.")
                    self._app.logger.error(export_path + exported_name_base + ".ffd")

            else:
                self._app.logger.info("Using Existing Embedded Element Patterns")
            local_path = "{}/{}/eep/".format(settings.remote_rpc_session_temp_folder, full_setup_str)
            export_path = check_and_download_folder(local_path, export_path)
            if os.path.exists(export_path + "/" + exported_name_map):
                with open(export_path + "/" + exported_name_map, "r") as reader:
                    lines = [line.split(None) for line in reader]
                lines = lines[1:]  # remove header
                for pattern in lines:
                    if len(pattern) >= 2:
                        port = pattern[0]
                        if ":" in port:
                            port = port.split(":")[0]
                        path_dict[-1][port] = export_path + "/" + pattern[1] + ".ffd"
        elapsed_time = time.time() - time_before
        self._app.logger.info("Exporting Embedded Element Patterns...Done: %s seconds", elapsed_time)
        return path_dict

    @pyaedt_function_handler()
    def plot_farfield_contour(
        self,
        qty_str="RealizedGain",
        phi_scan=0,
        theta_scan=0,
        title="RectangularPlot",
        convert_to_db=True,
        export_image_path=None,
    ):
        """Create a Contour plot of specified quantity.

        Parameters
        ----------
        qty_str : str, optional
            Quantity to plot. Default `"RealizedGain"`.
        phi_scan : float, int, optional
            Phi Scan Angle in degree. Default `0`.
        theta_scan : float, int, optional
            Theta Scan Angle in degree. Default `0`.
        title : str, optional
            Plot title. Default `"RectangularPlot"`.
        convert_to_db : bool, optional
            Either if the quantity has to be converted in db or not. Default is `True`.
        export_image_path : str, optional
            Full path to image file. Default is None to not export.

        Returns
        -------
        :class:`matplotlib.plt`
            Matplotlib fig object.
        """
        data = self.beamform(phi_scan, theta_scan)
        if qty_str == "":
            qty_to_plot = data
            qty_str = "Data"
        else:
            qty_to_plot = data[qty_str]
        qty_to_plot = np.reshape(qty_to_plot, (data["nTheta"], data["nPhi"]))
        th, ph = np.meshgrid(data["Theta"], data["Phi"])

        if convert_to_db:
            factor = 20
            if "Gain" in qty_str:
                factor = 10
            qty_to_plot = factor * np.log10(np.abs(qty_to_plot))

        return plot_contour(
            x=th,
            y=ph,
            qty_to_plot=qty_to_plot,
            xlabel="Theta (degree)",
            ylabel="Phi (degree)",
            title=title,
            levels=self.levels,
            snapshot_path=export_image_path,
        )

    @pyaedt_function_handler()
    def plot_2d_cut(
        self,
        qty_str="RealizedGain",
        primary_sweep="phi",
        secondary_sweep_value=0,
        phi_scan=0,
        theta_scan=0,
        title="Far Field Cut",
        convert_to_db=True,
        export_image_path=None,
    ):
        """Create a 2D plot of specified quantity in matplotlib.

        Parameters
        ----------
        qty_str : str, optional
            Quantity to plot. Default `"RealizedGain"`.
        primary_sweep : str, optional.
            X Axis variable. Default is `"phi"`. Option is  `"theta"`.
        secondary_sweep_value : float, list, string, optional
            List of cuts on secondary sweep to plot. Options are `"all"`, single value float or list of float.
        phi_scan : float, int, optional
            Phi Scan Angle in degree. Default `0`.
        theta_scan : float, int, optional
            Theta Scan Angle in degree. Default `0`.
        title : str, optional
            Plot title. Default `"RectangularPlot"`.
        convert_to_db : bool, optional
            Either if the quantity has to be converted in db or not. Default is `True`.
        export_image_path : str, optional
            Full path to image file. Default is None to not export.


        Returns
        -------
        :class:`matplotlib.plt`
            Matplotlib fig object.
        """
        data = self.beamform(phi_scan, theta_scan)

        data_to_plot = data[qty_str]
        curves = []
        if primary_sweep == "phi":
            x_key = "Phi"
            y_key = "Theta"
        else:
            y_key = "Phi"
            x_key = "Theta"
        x = data[x_key]
        xlabel = x_key
        if x_key == "Phi":
            temp = data_to_plot
        else:
            temp = data_to_plot.T
        if secondary_sweep_value == "all":
            for el in data[y_key]:
                idx = self._find_nearest(data[y_key], el)
                y = temp[idx]
                if convert_to_db:
                    if "Gain" in qty_str or "Dir" in qty_str:
                        y = 10 * np.log10(y)
                    else:
                        y = 20 * np.log10(y)
                curves.append([x, y, "{}={}".format(y_key, el)])
        elif isinstance(secondary_sweep_value, list):
            list_inserted = []
            for el in secondary_sweep_value:
                theta_idx = self._find_nearest(data[y_key], el)
                if theta_idx not in list_inserted:
                    y = temp[theta_idx]
                    if convert_to_db:
                        if "Gain" in qty_str or "Dir" in qty_str:
                            y = 10 * np.log10(y)
                        else:
                            y = 20 * np.log10(y)
                    curves.append([x, y, "{}={}".format(y_key, el)])
                    list_inserted.append(theta_idx)
        else:
            theta_idx = self._find_nearest(data[y_key], secondary_sweep_value)
            y = temp[theta_idx]
            if convert_to_db:
                if "Gain" in qty_str or "Dir" in qty_str:
                    y = 10 * np.log10(y)
                else:
                    y = 20 * np.log10(y)
            curves.append([x, y, "{}={}".format(y_key, data[y_key][theta_idx])])
        show_legend = True
        if len(curves) > 15:
            show_legend = False
        return plot_2d_chart(
            curves, xlabel=xlabel, ylabel=qty_str, title=title, snapshot_path=export_image_path, show_legend=show_legend
        )

    @pyaedt_function_handler()
    def polar_plot_3d(
        self,
        qty_str="RealizedGain",
        phi_scan=0,
        theta_scan=0,
        title="3D Plot",
        convert_to_db=True,
        export_image_path=None,
    ):
        """Create a 3d plot of specified quantity.

        Parameters
        ----------
        qty_str : str, optional
            Quantity to plot. Default `"RealizedGain"`.
        phi_scan : float, int, optional
            Phi Scan Angle in degree. Default `0`.
        theta_scan : float, int, optional
            Theta Scan Angle in degree. Default `0`.
        title : str, optional
            Plot title. Default `"3D Plot"`.
        convert_to_db : bool, optional
            Either if the quantity has to be converted in db or not. Default is `True`.
        export_image_path : str, optional
            Full path to image file. Default is None to not export.

        """
        data = self.beamform(phi_scan, theta_scan)

        if convert_to_db:
            ff_data = 10 * np.log10(data[qty_str])
            # renormalize to 0 and 1
            ff_max_dB = np.max(ff_data)
            ff_min_dB = np.min(ff_data)
            ff_data_renorm = (ff_data - ff_min_dB) / (ff_max_dB - ff_min_dB)
        else:
            ff_data = data[qty_str]
            # renormalize to 0 and 1
            ff_max = np.max(ff_data)
            ff_min = np.min(ff_data)
            ff_data_renorm = (ff_data - ff_max) / (ff_max - ff_min)

        theta = np.deg2rad(np.array(data["Theta"]))
        phi = np.deg2rad(np.array(data["Phi"]))
        phi_grid, theta_grid = np.meshgrid(phi, theta)
        r = np.reshape(ff_data_renorm, (len(data["Theta"]), len(data["Phi"])))

        x = r * np.sin(theta_grid) * np.cos(phi_grid)
        y = r * np.sin(theta_grid) * np.sin(phi_grid)
        z = r * np.cos(theta_grid)
        plot_3d_chart([x, y, z], xlabel="Theta", ylabel="Phi", title=title, snapshot_path=export_image_path)

    @pyaedt_function_handler()
    def _get_geometry(self, is_antenna_array=True):
        data = self.beamform(0, 0)
        time_before = time.time()
        self._app.logger.info("Exporting Geometry...")

        # obj is being exported as model units, scaling factor needed for display
        sf = AEDT_UNITS["Length"][self._app.modeler.model_units]

        bounding_box = self._app.modeler.obounding_box
        xmax = float(bounding_box[3]) - float(bounding_box[0])
        ymax = float(bounding_box[4]) - float(bounding_box[1])
        zmax = float(bounding_box[5]) - float(bounding_box[2])

        geo_path = "{}\\geo\\".format(self._app.working_directory)
        if not os.path.exists(geo_path):
            os.makedirs(geo_path)

        model_pv = self._app.post.get_model_plotter_geometries(plot_air_objects=False)

        obj_meshes = []
        center = []
        if is_antenna_array:
            i = 0
            for obj in model_pv.objects:
                for each in data["Element_Location"]:
                    mesh = obj._cached_polydata
                    translated_mesh = mesh.copy()
                    offset_xyz = data["Element_Location"][each] / sf
                    if np.abs(2 * offset_xyz[0]) > xmax:  # assume array is centere, factor of 2
                        xmax = offset_xyz[0] * 2
                    if np.abs(2 * offset_xyz[1]) > ymax:  # assume array is centere, factor of 2
                        ymax = offset_xyz[1] * 2
                    translated_mesh.position = offset_xyz
                    translated_mesh.translate(offset_xyz, inplace=True)
                    color_cad = [i / 255 for i in obj.color]

                    if len(obj_meshes) > i:
                        obj_meshes[i][0] += translated_mesh
                    else:
                        obj_meshes.append([translated_mesh, color_cad, obj.opacity])
                i += 1
                if not center:
                    center = obj_meshes[-1][0].center
                else:
                    center = [i + j for i, j in zip(obj_meshes[-1][0].center, center)]
        center = [-k / i for k in center]
        self.all_max = np.max(np.array([xmax, ymax, zmax]))
        elapsed_time = time.time() - time_before
        self._app.logger.info("Exporting Geometry...Done: %s seconds", elapsed_time)
        for mesh in obj_meshes:
            mesh[0].translate(center, inplace=True)
        return obj_meshes

    @pyaedt_function_handler()
    def polar_plot_3d_pyvista(
        self,
        qty_str="RealizedGain",
        convert_to_db=True,
        position=None,
        rotation=None,
        export_image_path=None,
        show=True,
        show_as_standalone=False,
    ):
        """Create a 3d Polar Plot of Geometry with Radiation Pattern in Pyvista.

        Parameters
        ----------
        qty_str : str, optional
            Quantity to plot. Default `"RealizedGain"`.
        convert_to_db : bool, optional
            Either if the quantity has to be converted in db or not. Default is `True`.
        export_image_path : str, optional
            Full path to image file. Default is None to not export.
        position : list, optional
            It can be a list of numpy list of origin of plot. Default is [0,0,0].
        rotation : list, optional
            It can be a list of numpy list of origin of plot.
            Default is [[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]].
        show : bool, optional
            Either if the plot has to be shown or not. Default is `True`.
        show_as_standalone : bool, optional
            Either if the plot has to be shown as standalone or not. Default is `True`.

        Returns
        -------
        bool or :class:`Pyvista.Plotter`
            Return :class:`Pyvista.Plotter` in case show and export_image_path is `False`.
            In other cases return ``True`` when successful.

        """
        if not position:
            position = np.zeros(3)
        elif isinstance(position, (list, tuple)):
            position = np.array(position)
        if not rotation:
            rotation = np.eye(3)
        elif isinstance(rotation, (list, tuple)):
            rotation = np.array(rotation)
        self.beamform(phi_scan=0, theta_scan=0)
        plot_min = -40
        self._get_far_field_mesh(qty_str=qty_str, convert_to_db=convert_to_db)

        # plot everything together
        rotation_euler = self._rotation_to_euler_angles(rotation) * 180 / np.pi

        if not export_image_path and not show:
            off_screen = False
        else:
            off_screen = not show

        if show_as_standalone:
            p = pv.Plotter(notebook=False, off_screen=off_screen)
        else:
            p = pv.Plotter(notebook=is_notebook(), off_screen=off_screen)

        uf = UpdateBeamForm(self)

        p.add_slider_widget(
            uf.update_phi,
            rng=[0, 360],
            value=0,
            title="Phi",
            pointa=(0.55, 0.1),
            pointb=(0.74, 0.1),
            style="modern",
            event_type="always",
            title_height=0.02,
        )
        p.add_slider_widget(
            uf.update_theta,
            rng=[-180, 180],
            value=0,
            title="Theta",
            pointa=(0.77, 0.1),
            pointb=(0.98, 0.1),
            style="modern",
            event_type="always",
            title_height=0.02,
        )

        # sargs = dict(height=0.4, vertical=True, position_x=0.05, position_y=0.5)
        sargs = dict(
            title_font_size=12,
            label_font_size=10,
            shadow=True,
            n_labels=7,
            italic=True,
            fmt="%.1f",
            font_family="arial",
            vertical=True,
            position_x=0.05,
            position_y=0.65,
            height=0.3,
            width=0.06,
            outline=True,
        )
        # ff_mesh_inst = p.add_mesh(uf.output,smooth_shading=True,cmap="jet",scalar_bar_args=sargs,opacity=0.5)
        # not sure why, but smooth_shading causes this to not update

        ff_mesh_inst = p.add_mesh(uf.output, cmap="jet", clim=[plot_min, self.max_gain], scalar_bar_args=sargs)
        cad_mesh = self._get_geometry()
        if cad_mesh:

            def toggle_vis_ff(flag):
                ff_mesh_inst.SetVisibility(flag)

            def toggle_vis_cad(flag):
                for i in cad:
                    i.SetVisibility(flag)

            def scale(value=1):
                ff_mesh_inst.SetScale(value, value, value)
                ff_mesh_inst.SetPosition(position)
                ff_mesh_inst.SetOrientation(rotation_euler)
                # p.add_mesh(ff_mesh, smooth_shading=True,cmap="jet")
                return

            p.add_checkbox_button_widget(toggle_vis_ff, value=True, size=30)
            p.add_text("Show Far Fields", position=(70, 25), color="white", font_size=10)
            slider_max = int(np.ceil(self.all_max / 2 / self.max_gain))
            if slider_max > 0:
                slider_min = 0
                value = slider_max / 3
            else:
                slider_min = slider_max
                slider_max = 0
                value = slider_min / 3

            p.add_slider_widget(
                scale,
                [slider_min, slider_max],
                title="Scale Plot",
                value=value,
                pointa=(0.7, 0.93),
                pointb=(0.99, 0.93),
                style="modern",
                title_height=0.02,
            )

            cad = []
            for cm in cad_mesh:
                cad.append(p.add_mesh(cm[0], color=cm[1], show_scalar_bar=False, opacity=cm[2]))
            p.add_checkbox_button_widget(toggle_vis_cad, value=True, position=(10, 70), size=30)
            p.add_text("Show Geometry", position=(70, 75), color="white", font_size=10)

        if export_image_path:
            p.show(screenshot=export_image_path)
            return True
        elif show:  # pragma: no cover
            p.show()
            return True
        return p

    @pyaedt_function_handler()
    def polar_plot_3d_pyvista_2beams(
        self,
        qty_str="RealizedGain",
        convert_to_db=True,
        position=None,
        rotation=None,
        export_image_path=None,
        show=True,
    ):  # pragma: no cover
        """Create a 3d Polar Plot with 2 beams of Geometry with Radiation Pattern in Pyvista.

        Parameters
        ----------
        qty_str : str, optional
            Quantity to plot. Default `"RealizedGain"`.
        convert_to_db : bool, optional
            Either if the quantity has to be converted in db or not. Default is `True`.
        export_image_path : str, optional
            Full path to image file. Default is None to not export.
        position : list, optional
            It can be a list of numpy list of origin of plot. Default is [0,0,0].
        rotation : list, optional
            It can be a list of numpy list of origin of plot.
            Default is [[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]].
        show : bool, optional
            Either if the plot has to be shown or not. Default is `True`.

        Returns
        -------
        bool or :class:`Pyvista.Plotter`
            Return :class:`Pyvista.Plotter` in case show and export_image_path is `False`.
            In other cases return ``True`` when successful.
        """
        if not position:
            position = np.zeros(3)
        elif isinstance(position, (list, tuple)):
            position = np.array(position)
        if not rotation:
            rotation = np.eye(3)
        elif isinstance(rotation, (list, tuple)):
            rotation = np.array(rotation)
        self.beamform_2beams(phi_scan1=0, theta_scan1=0, phi_scan2=0, theta_scan2=0)
        self._get_far_field_mesh(qty_str=qty_str, convert_to_db=convert_to_db)

        uf = Update2BeamForms(self, max_value=self.max_gain)
        rotation_euler = self._rotation_to_euler_angles(rotation) * 180 / np.pi

        if not export_image_path and not show:
            off_screen = False
        else:
            off_screen = not show

        p = pv.Plotter(notebook=is_notebook(), off_screen=off_screen, window_size=[1024, 768])

        p.add_slider_widget(
            uf.update_phi1,
            rng=[0, 360],
            value=0,
            title="Phi1",
            pointa=(0.35, 0.1),
            pointb=(0.64, 0.1),
            style="modern",
            event_type="always",
        )
        p.add_slider_widget(
            uf.update_theta1,
            rng=[-180, 180],
            value=0,
            title="Theta1",
            pointa=(0.67, 0.1),
            pointb=(0.98, 0.1),
            style="modern",
            event_type="always",
        )

        p.add_slider_widget(
            uf.update_phi2,
            rng=[0, 360],
            value=0,
            title="Phi2",
            pointa=(0.35, 0.25),
            pointb=(0.64, 0.25),
            style="modern",
            event_type="always",
        )
        p.add_slider_widget(
            uf.update_theta2,
            rng=[-180, 180],
            value=0,
            title="Theta2",
            pointa=(0.67, 0.25),
            pointb=(0.98, 0.25),
            style="modern",
            event_type="always",
        )
        sargs = dict(height=0.4, vertical=True, position_x=0.05, position_y=0.5)
        # ff_mesh_inst = p.add_mesh(uf.output,smooth_shading=True,cmap="jet",scalar_bar_args=sargs,opacity=0.5)
        # not sure why, but smooth_shading causes this to not update
        plot_min = self.min_gain
        ff_mesh_inst = p.add_mesh(uf.output, cmap="jet", clim=[plot_min, self.max_gain], scalar_bar_args=sargs)
        cad_mesh = self._get_geometry()
        if cad_mesh:

            def toggle_vis_ff(flag):
                ff_mesh_inst.SetVisibility(flag)

            def toggle_vis_cad(flag):
                for i in cad:
                    i.SetVisibility(flag)

            def scale(value=1):
                ff_mesh_inst.SetScale(value, value, value)
                ff_mesh_inst.SetPosition(position)
                ff_mesh_inst.SetOrientation(rotation_euler)
                # p.add_mesh(ff_mesh, smooth_shading=True,cmap="jet")
                return

            p.add_checkbox_button_widget(toggle_vis_ff, value=True)
            p.add_text("Show Far Fields", position=(70, 25), color="black", font_size=12)
            slider_max = int(np.ceil(self.all_max / 2 / self.max_gain))
            if slider_max > 0:
                slider_min = 0
                value = slider_max / 3
            else:
                slider_min = slider_max
                slider_max = 0
                value = slider_min / 3
            p.add_slider_widget(scale, [0, slider_max], title="Scale Plot", value=value)

            if "MaterialIds" in cad_mesh.array_names:
                color_display_type = cad_mesh["MaterialIds"]
            else:
                color_display_type = None
            cad = []
            for cm in cad_mesh:
                cad.append(p.add_mesh(cm[0], color=cm[1], show_scalar_bar=False, opacity=cm[2]))
            size = int(p.window_size[1] / 40)
            p.add_checkbox_button_widget(toggle_vis_cad, size=size, value=True, position=(10, 70))
            p.add_text("Show Geometry", position=(70, 75), color="black", font_size=12)

        if export_image_path:
            p.show(screenshot=export_image_path)
            return True
        elif show:
            p.show()
            return True
        return p

    @staticmethod
    @pyaedt_function_handler()
    def _find_nearest(array, value):
        idx = np.searchsorted(array, value, side="left")
        if idx > 0 and (idx == len(array) or math.fabs(value - array[idx - 1]) < math.fabs(value - array[idx])):
            return idx - 1
        else:
            return idx

    @staticmethod
    @pyaedt_function_handler()
    def _rotation_to_euler_angles(R):
        sy = math.sqrt(R[0, 0] * R[0, 0] + R[1, 0] * R[1, 0])
        singular = sy < 1e-6
        if not singular:
            x = math.atan2(R[2, 1], R[2, 2])
            y = math.atan2(-R[2, 0], sy)
            z = math.atan2(R[1, 0], R[0, 0])
        else:
            x = math.atan2(-R[1, 2], R[1, 1])
            y = math.atan2(-R[2, 0], sy)
            z = 0
        return np.array([x, y, z])


class UpdateBeamForm:
    def __init__(self, ff):
        self.output = ff.mesh
        self._phi = 0
        self._theta = 0
        # default parameters
        self.ff = ff
        self.qty_str = "RealizedGain"
        self.convert_to_db = True

    def _update_both(self):
        self.ff.beamform(phi_scan=self._phi, theta_scan=self._theta)
        # perc_of_maxgain= self.ff.max_gain/self.max_value

        self.ff._get_far_field_mesh(self.qty_str, self.convert_to_db)

        self.output.overwrite(self.ff.mesh)
        return

    def update_phi(self, phi):
        """Update the Pyvista Plot with new phi value."""
        self._phi = phi
        self._update_both()

    def update_theta(self, theta):
        """Update the Pyvista Plot with new theta value."""
        self._theta = theta
        self._update_both()


class Update2BeamForms:
    def __init__(self, ff, max_value=1):
        self.max_value = max_value
        self.output = ff.mesh
        self._phi1 = 0
        self._theta1 = 0
        self._phi2 = 0
        self._theta2 = 0
        # default parameters
        self.ff = ff
        self.qty_str = "RealizedGain"
        self.convert_to_db = True

    def _update_both(self):
        self.ff.beamform_2beams(
            phi_scan1=self._phi1, theta_scan1=self._theta1, phi_scan2=self._phi2, theta_scan2=self._theta2
        )
        self.ff._get_far_field_mesh(self.qty_str, self.convert_to_db)
        current_max = np.max(self.ff.mesh["FarFieldData"])
        delta = self.max_value - current_max
        self.ff.mesh["FarFieldData"] = self.ff.mesh["FarFieldData"] - delta
        self.output.overwrite(self.ff.mesh)
        return

    def update_phi1(self, phi1):
        """Update the Pyvista Plot with new phi1 value."""
        self._phi1 = phi1
        self._update_both()

    def update_theta1(self, theta1):
        """Update the Pyvista Plot with new theta1 value."""
        self._theta1 = theta1
        self._update_both()

    def update_phi2(self, phi2):
        """Update the Pyvista Plot with new phi2 value."""
        self._phi2 = phi2
        self._update_both()

    def update_theta2(self, theta2):
        """Updates the Pyvista Plot with new theta2 value."""
        self._theta2 = theta2
        self._update_both()


class FieldPlot:
    """Creates and edits field plots.

    Parameters
    ----------
    postprocessor : :class:`pyaedt.modules.PostProcessor.PostProcessor`
    objlist : list
        List of objects.
    solutionName : str
        Name of the solution.
    quantityName : str
        Name of the plot or the name of the object.
    intrinsincList : dict, optional
        Name of the intrinsic dictionary. The default is ``{}``.

    """

    def __init__(
        self,
        postprocessor,
        objlist=[],
        surfacelist=[],
        linelist=[],
        cutplanelist=[],
        solutionName="",
        quantityName="",
        intrinsincList={},
        seedingFaces=[],
        layers_nets=[],
        layers_plot_type="LayerNetsExtFace",
    ):
        self._postprocessor = postprocessor
        self.oField = postprocessor.ofieldsreporter
        self.volume_indexes = objlist
        self.surfaces_indexes = surfacelist
        self.line_indexes = linelist
        self.cutplane_indexes = cutplanelist
        self.layers_nets = layers_nets
        self.layers_plot_type = layers_plot_type
        self.seeding_faces = seedingFaces
        self.solutionName = solutionName
        self.quantityName = quantityName
        self.intrinsincList = intrinsincList
        self.name = "Field_Plot"
        self.plotFolder = "Field_Plot"
        self.Filled = False
        self.IsoVal = "Fringe"
        self.SmoothShade = True
        self.AddGrid = False
        self.MapTransparency = True
        self.Refinement = 0
        self.Transparency = 0
        self.SmoothingLevel = 0
        self.ArrowUniform = True
        self.ArrowSpacing = 0
        self.MinArrowSpacing = 0
        self.MaxArrowSpacing = 0
        self.GridColor = [255, 255, 255]
        self.PlotIsoSurface = True
        self.PointSize = 1
        self.CloudSpacing = 0.5
        self.CloudMinSpacing = -1
        self.CloudMaxSpacing = -1
        self.LineWidth = 4
        self.LineStyle = "Cylinder"
        self.IsoValType = "Tone"
        self.NumofPoints = 100
        self.TraceStepLength = "0.001mm"
        self.UseAdaptiveStep = True
        self.SeedingSamplingOption = True
        self.SeedingPointsNumber = 15
        self.FractionOfMaximum = 0.8
        self._filter_boxes = []
        self.field_type = None

    @property
    def filter_boxes(self):
        """Volumes on which filter the plot."""
        return self._filter_boxes

    @filter_boxes.setter
    def filter_boxes(self, val):
        if isinstance(val, str):
            val = [val]
        self._filter_boxes = val

    @property
    def plotGeomInfo(self):
        """Plot geometry information."""
        idx = 0
        if self.volume_indexes:
            idx += 1
        if self.surfaces_indexes:
            idx += 1
        if self.cutplane_indexes:
            idx += 1
        if self.line_indexes:
            idx += 1
        if self.layers_nets:
            idx += 1

        info = [idx]
        if self.volume_indexes:
            info.append("Volume")
            info.append("ObjList")
            info.append(len(self.volume_indexes))
            for index in self.volume_indexes:
                info.append(str(index))
        if self.surfaces_indexes:
            model_faces = []
            nonmodel_faces = []
            if self._postprocessor._app.design_type == "HFSS 3D Layout Design":
                model_faces = [str(i) for i in self.surfaces_indexes]
            else:
                models = self._postprocessor.modeler.model_objects
                for index in self.surfaces_indexes:
                    try:
                        if isinstance(index, FacePrimitive):
                            index = index.id
                        oname = self._postprocessor.modeler.oeditor.GetObjectNameByFaceID(index)
                        if oname in models:
                            model_faces.append(str(index))
                        else:
                            nonmodel_faces.append(str(index))
                    except:
                        pass
            info.append("Surface")
            if model_faces:
                info.append("FacesList")
                info.append(len(model_faces))
                for index in model_faces:
                    info.append(index)
            if nonmodel_faces:
                info.append("NonModelFaceList")
                info.append(len(nonmodel_faces))
                for index in nonmodel_faces:
                    info.append(index)
        if self.cutplane_indexes:
            info.append("Surface")
            info.append("CutPlane")
            info.append(len(self.cutplane_indexes))
            for index in self.cutplane_indexes:
                info.append(str(index))
        if self.line_indexes:
            info.append("Line")
            info.append(len(self.line_indexes))
            for index in self.line_indexes:
                info.append(str(index))
        if self.layers_nets:
            if self.layers_plot_type == "LayerNets":
                info.append("Volume")
                info.append("LayerNets")
            else:
                info.append("Surface")
                info.append("LayerNetsExtFace")
            info.append(len(self.layers_nets))
            for index in self.layers_nets:
                info.append(index[0])
                info.append(len(index[1:]))
                info.extend(index[1:])
        return info

    @property
    def intrinsicVar(self):
        """Intrinsic variable.

        Returns
        -------
        list or dict
            List or dictionary of the variables for the field plot.
        """
        var = ""
        if type(self.intrinsincList) is list:
            l = 0
            while l < len(self.intrinsincList):
                val = self.intrinsincList[l + 1]
                if ":=" in self.intrinsincList[l] and isinstance(self.intrinsincList[l + 1], list):
                    val = self.intrinsincList[l + 1][0]
                ll = self.intrinsincList[l].split(":=")
                var += ll[0] + "='" + str(val) + "' "
                l += 2
        else:
            for a in self.intrinsincList:
                var += a + "='" + str(self.intrinsincList[a]) + "' "
        return var

    @property
    def plotsettings(self):
        """Plot settings.

        Returns
        -------
        list
            List of plot settings.
        """
        if (
            self.surfaces_indexes
            or self.cutplane_indexes
            or (self.layers_nets and self.layers_plot_type == "LayerNetsExtFace")
        ):
            arg = [
                "NAME:PlotOnSurfaceSettings",
                "Filled:=",
                self.Filled,
                "IsoValType:=",
                self.IsoVal,
                "SmoothShade:=",
                self.SmoothShade,
                "AddGrid:=",
                self.AddGrid,
                "MapTransparency:=",
                self.MapTransparency,
                "Refinement:=",
                self.Refinement,
                "Transparency:=",
                self.Transparency,
                "SmoothingLevel:=",
                self.SmoothingLevel,
                [
                    "NAME:Arrow3DSpacingSettings",
                    "ArrowUniform:=",
                    self.ArrowUniform,
                    "ArrowSpacing:=",
                    self.ArrowSpacing,
                    "MinArrowSpacing:=",
                    self.MinArrowSpacing,
                    "MaxArrowSpacing:=",
                    self.MaxArrowSpacing,
                ],
                "GridColor:=",
                self.GridColor,
            ]
        elif self.line_indexes:
            arg = [
                "NAME:PlotOnLineSettings",
                ["NAME:LineSettingsID", "Width:=", self.LineWidth, "Style:=", self.LineStyle],
                "IsoValType:=",
                self.IsoValType,
                "ArrowUniform:=",
                self.ArrowUniform,
                "NumofArrow:=",
                self.NumofPoints,
                "Refinement:=",
                self.Refinement,
            ]
        else:
            arg = [
                "NAME:PlotOnVolumeSettings",
                "PlotIsoSurface:=",
                self.PlotIsoSurface,
                "PointSize:=",
                self.PointSize,
                "Refinement:=",
                self.Refinement,
                "CloudSpacing:=",
                self.CloudSpacing,
                "CloudMinSpacing:=",
                self.CloudMinSpacing,
                "CloudMaxSpacing:=",
                self.CloudMaxSpacing,
                [
                    "NAME:Arrow3DSpacingSettings",
                    "ArrowUniform:=",
                    self.ArrowUniform,
                    "ArrowSpacing:=",
                    self.ArrowSpacing,
                    "MinArrowSpacing:=",
                    self.MinArrowSpacing,
                    "MaxArrowSpacing:=",
                    self.MaxArrowSpacing,
                ],
            ]
        return arg

    @property
    def surfacePlotInstruction(self):
        """Surface plot settings.

        Returns
        -------
        list
            List of surface plot settings.

        """
        out = [
            "NAME:" + self.name,
            "SolutionName:=",
            self.solutionName,
            "QuantityName:=",
            self.quantityName,
            "PlotFolder:=",
            self.plotFolder,
        ]
        if self.field_type:
            out.extend(["FieldType:=", self.field_type])
        out.extend(
            [
                "UserSpecifyName:=",
                1,
                "UserSpecifyFolder:=",
                1,
                "StreamlinePlot:=",
                False,
                "AdjacentSidePlot:=",
                False,
                "FullModelPlot:=",
                False,
                "IntrinsicVar:=",
                self.intrinsicVar,
                "PlotGeomInfo:=",
                self.plotGeomInfo,
                "FilterBoxes:=",
                [len(self.filter_boxes)] + self.filter_boxes,
                self.plotsettings,
                "EnableGaussianSmoothing:=",
                False,
            ]
        )
        return out

    @property
    def surfacePlotInstructionLineTraces(self):
        """Surface plot settings for field line traces.

        ..note::
            ``Specify seeding points on selections`` is by default set to ``by sampling``.

        Returns
        -------
        list
            List of plot settings for line traces.

        """
        out = [
            "NAME:" + self.name,
            "SolutionName:=",
            self.solutionName,
            "UserSpecifyName:=",
            0,
            "UserSpecifyFolder:=",
            0,
            "QuantityName:=",
            "QuantityName_FieldLineTrace",
            "PlotFolder:=",
            self.plotFolder,
        ]
        if self.field_type:
            out.extend(["FieldType:=", self.field_type])
        out.extend(
            [
                "IntrinsicVar:=",
                self.intrinsicVar,
                "Trace Step Length:=",
                self.TraceStepLength,
                "Use Adaptive Step:=",
                self.UseAdaptiveStep,
                "Seeding Faces:=",
                self.seeding_faces,
                "Seeding Markers:=",
                [0],
                "Surface Tracing Objects:=",
                self.surfaces_indexes,
                "Volume Tracing Objects:=",
                self.volume_indexes,
                "Seeding Sampling Option:=",
                self.SeedingSamplingOption,
                "Seeding Points Number:=",
                self.SeedingPointsNumber,
                "Fractional of Maximal:=",
                self.FractionOfMaximum,
                "Discrete Seeds Option:=",
                "Marker Point",
                [
                    "NAME:InceptionEvaluationSettings",
                    "Gas Type:=",
                    0,
                    "Gas Pressure:=",
                    1,
                    "Use Inception:=",
                    True,
                    "Potential U0:=",
                    0,
                    "Potential K:=",
                    0,
                    "Potential A:=",
                    1,
                ],
                self.field_line_trace_plot_settings,
            ]
        )
        return out

    @property
    def field_plot_settings(self):
        """Field Plot Settings.

        Returns
        -------
        list
            Field Plot Settings.
        """
        return [
            "NAME:FieldsPlotItemSettings",
            [
                "NAME:PlotOnSurfaceSettings",
                "Filled:=",
                self.Filled,
                "IsoValType:=",
                self.IsoVal,
                "AddGrid:=",
                self.AddGrid,
                "MapTransparency:=",
                self.MapTransparency,
                "Refinement:=",
                self.Refinement,
                "Transparency:=",
                self.Transparency,
                "SmoothingLevel:=",
                self.SmoothingLevel,
                "ShadingType:=",
                self.SmoothShade,
                [
                    "NAME:Arrow3DSpacingSettings",
                    "ArrowUniform:=",
                    self.ArrowUniform,
                    "ArrowSpacing:=",
                    self.ArrowSpacing,
                    "MinArrowSpacing:=",
                    self.MinArrowSpacing,
                    "MaxArrowSpacing:=",
                    self.MaxArrowSpacing,
                ],
                "GridColor:=",
                self.GridColor,
            ],
        ]

    @property
    def field_line_trace_plot_settings(self):
        """Settings for the field line traces in the plot.

        Returns
        -------
        list
            List of settings for the field line traces in the plot.
        """
        return [
            "NAME:FieldLineTracePlotSettings",
            ["NAME:LineSettingsID", "Width:=", self.LineWidth, "Style:=", self.LineStyle],
            "IsoValType:=",
            self.IsoValType,
        ]

    @pyaedt_function_handler()
    def create(self):
        """Create a field plot.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        try:
            if self.seeding_faces:
                self.oField.CreateFieldPlot(self.surfacePlotInstructionLineTraces, "FieldLineTrace")
            else:
                self.oField.CreateFieldPlot(self.surfacePlotInstruction, "Field")
            return True
        except:
            return False

    @pyaedt_function_handler()
    def update(self):
        """Update the field plot.

        .. note::
           This method works on any plot created inside PyAEDT.
           For Plot already existing in AEDT Design it may produce incorrect results.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        try:
            if self.seeding_faces:
                if self.seeding_faces[0] != len(self.seeding_faces) - 1:
                    for face in self.seeding_faces[1:]:
                        if not isinstance(face, int):
                            self._postprocessor.logger.error("Provide valid object id for seeding faces.")
                            return False
                        else:
                            if face not in list(self._postprocessor._app.modeler.objects.keys()):
                                self._postprocessor.logger.error("Invalid object id.")
                                self.seeding_faces.remove(face)
                                return False
                    self.seeding_faces[0] = len(self.seeding_faces) - 1
                if self.volume_indexes[0] != len(self.volume_indexes) - 1:
                    for obj in self.volume_indexes[1:]:
                        if not isinstance(obj, int):
                            self._postprocessor.logger.error("Provide valid object id for in-volume object.")
                            return False
                        else:
                            if obj not in list(self._postprocessor._app.modeler.objects.keys()):
                                self._postprocessor.logger.error("Invalid object id.")
                                self.volume_indexes.remove(obj)
                                return False
                    self.volume_indexes[0] = len(self.volume_indexes) - 1
                if self.surfaces_indexes[0] != len(self.surfaces_indexes) - 1:
                    for obj in self.surfaces_indexes[1:]:
                        if not isinstance(obj, int):
                            self._postprocessor.logger.error("Provide valid object id for surface object.")
                            return False
                        else:
                            if obj not in list(self._postprocessor._app.modeler.objects.keys()):
                                self._postprocessor.logger.error("Invalid object id.")
                                self.surfaces_indexes.remove(obj)
                                return False
                    self.surfaces_indexes[0] = len(self.surfaces_indexes) - 1
                self.oField.ModifyFieldPlot(self.name, self.surfacePlotInstructionLineTraces)
            else:
                self.oField.ModifyFieldPlot(self.name, self.surfacePlotInstruction)
            return True
        except:
            return False

    @pyaedt_function_handler()
    def update_field_plot_settings(self):
        """Modify the field plot settings.

        .. note::
            This method is not available for field plot line traces.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        self.oField.SetFieldPlotSettings(self.name, ["NAME:FieldsPlotItemSettings", self.plotsettings])
        return True

    @pyaedt_function_handler()
    def delete(self):
        """Delete the field plot."""
        self.oField.DeleteFieldPlot([self.name])
        self._postprocessor.field_plots.pop(self.name, None)

    @pyaedt_function_handler()
    def change_plot_scale(self, minimum_value, maximum_value, is_log=False, is_db=False):
        """Change Field Plot Scale.

        Parameters
        ----------
        minimum_value : str, float
            Minimum value of the scale.
        maximum_value : str, float
            Maximum value of the scale.
        is_log : bool, optional
            Set to ``True`` if Log Scale is setup.
        is_db : bool, optional
            Set to ``True`` if dB Scale is setup.

        Returns
        -------
        bool
            ``True`` if successful.

        References
        ----------
        >>> oModule.SetPlotFolderSettings
        """
        args = ["NAME:FieldsPlotSettings", "Real Time mode:=", True]
        args += [
            [
                "NAME:ColorMaPSettings",
                "ColorMapType:=",
                "Spectrum",
                "SpectrumType:=",
                "Rainbow",
                "UniformColor:=",
                [127, 255, 255],
                "RampColor:=",
                [255, 127, 127],
            ]
        ]
        args += [
            [
                "NAME:Scale3DSettings",
                "minvalue:=",
                minimum_value,
                "maxvalue:=",
                maximum_value,
                "log:=",
                not is_log,
                "dB:=",
                is_db,
                "ScaleType:=",
                1,
            ]
        ]
        self.oField.SetPlotFolderSettings(self.plotFolder, args)
        return True

    @pyaedt_function_handler()
    def export_image(self, full_path=None, width=1920, height=1080, orientation="isometric", display_wireframe=True):
        """Export the active plot to an image file.

        .. note::
           There are some limitations on HFSS 3D Layout plots.

        full_path : str, optional
            Path for saving the image file. PNG and GIF formats are supported.
            The default is ``None`` which export file in working_directory.
        width : int, optional
            Plot Width.
        height : int, optional
            Plot height.
        orientation : str, optional
            View of the exported plot. Options are ``isometric``,
            ``top``, ``bottom``, ``right``, ``left``, ``front``,
            ``back``, and any custom orientation.
        display_wireframe : bool, optional
            Set to ``True`` if the objects has to be put in wireframe mode.

        Returns
        -------
        str
            Full path to exported file if successful.

        References
        ----------
        >>> oModule.ExportPlotImageToFile
        >>> oModule.ExportModelImageToFile
        >>> oModule.ExportPlotImageWithViewToFile
        """
        self.oField.UpdateQuantityFieldsPlots(self.plotFolder)
        if not full_path:
            full_path = os.path.join(self._postprocessor._app.working_directory, self.name + ".png")
        status = self._postprocessor.export_field_jpg(
            full_path,
            self.name,
            self.plotFolder,
            orientation=orientation,
            width=width,
            height=height,
            display_wireframe=display_wireframe,
        )
        if status:
            return full_path
        else:
            return False

    @pyaedt_function_handler()
    def export_image_from_aedtplt(
        self, export_path=None, view="isometric", plot_mesh=False, scale_min=None, scale_max=None
    ):
        """Save an image of the active plot using PyVista.

        .. note::
            This method only works if the CPython with PyVista module is installed.

        Parameters
        ----------
        export_path : str, optional
            Path where image will be saved.
            The default is ``None`` which export file in working_directory.
        view : str, optional
           View to export. Options are ``"isometric"``, ``"xy"``, ``"xz"``, ``"yz"``.
        plot_mesh : bool, optional
            Plot mesh.
        scale_min : float, optional
            Scale output min.
        scale_max : float, optional
            Scale output max.

        Returns
        -------
        str
            Full path to exported file if successful.

        References
        ----------
        >>> oModule.UpdateAllFieldsPlots
        >>> oModule.UpdateQuantityFieldsPlots
        >>> oModule.ExportFieldPlot
        """
        if not export_path:
            export_path = self._postprocessor._app.working_directory
        if sys.version_info.major > 2:
            return self._postprocessor.plot_field_from_fieldplot(
                self.name,
                project_path=export_path,
                meshplot=plot_mesh,
                imageformat="jpg",
                view=view,
                plot_label=self.quantityName,
                show=False,
                scale_min=scale_min,
                scale_max=scale_max,
            )
        else:
            self._postprocessor.logger.info("This method works only on CPython with PyVista")
            return False


class VRTFieldPlot:
    """Creates and edits VRT field plots for SBR+ and Creeping Waves.

    Parameters
    ----------
    postprocessor : :class:`pyaedt.modules.PostProcessor.PostProcessor`
    is_creeping_wave : bool
        Whether it is a creeping wave model or not.
    quantity_name : str, optional
        Name of the plot or the name of the object.
    max_frequency : str, optional
        Maximum Frequency. The default is ``"1GHz"``.
    ray_density : int, optional
        Ray Density. The default is ``2``.
    bounces : int, optional
        Maximum number of bounces. The default is ``5``.
    intrinsinc_list : dict, optional
        Name of the intrinsic dictionary. The default is ``{}``.

    """

    def __init__(
        self,
        postprocessor,
        is_creeping_wave=False,
        quantity_name="QuantityName_SBR",
        max_frequency="1GHz",
        ray_density=2,
        bounces=5,
        intrinsinc_list={},
    ):
        self.is_creeping_wave = is_creeping_wave
        self._postprocessor = postprocessor
        self._ofield = postprocessor.ofieldsreporter
        self.quantity_name = quantity_name
        self.intrinsics = intrinsinc_list
        self.name = "Field_Plot"
        self.plot_folder = "Field_Plot"
        self.max_frequency = max_frequency
        self.ray_density = ray_density
        self.number_of_bounces = bounces
        self.multi_bounce_ray_density_control = False
        self.mbrd_max_subdivision = 2
        self.shoot_utd_rays = False
        self.shoot_type = "All Rays"
        self.start_index = 0
        self.stop_index = 1
        self.step_index = 1
        self.is_plane_wave = True
        self.incident_theta = "0deg"
        self.incident_phi = "0deg"
        self.vertical_polarization = False
        self.custom_location = [0, 0, 0]
        self.ray_box = None
        self.ray_elevation = "0deg"
        self.ray_azimuth = "0deg"
        self.custom_coordinatesystem = 1
        self.ray_cutoff = 40
        self.sample_density = 10
        self.irregular_surface_tolerance = 50

    @property
    def intrinsicVar(self):
        """Intrinsic variable.

        Returns
        -------
        list or dict
            List or dictionary of the variables for the field plot.
        """
        var = ""
        if isinstance(self.intrinsics, list):
            l = 0
            while l < len(self.intrinsics):
                val = self.intrinsics[l + 1]
                if ":=" in self.intrinsics[l] and isinstance(self.intrinsics[l + 1], list):
                    val = self.intrinsics[l + 1][0]
                ll = self.intrinsics[l].split(":=")
                var += ll[0] + "='" + str(val) + "' "
                l += 2
        else:
            for a in self.intrinsics:
                var += a + "='" + str(self.intrinsics[a]) + "' "
        return var

    @pyaedt_function_handler()
    def _create_args(self):
        args = [
            "NAME:" + self.name,
            "UserSpecifyName:=",
            0,
            "UserSpecifyFolder:=",
            0,
            "QuantityName:=",
            self.quantity_name,
            "PlotFolder:=",
            "Visual Ray Trace SBR",
            "IntrinsicVar:=",
            self.intrinsicVar,
            "MaxFrequency:=",
            self.max_frequency,
            "RayDensity:=",
            self.ray_density,
            "NumberBounces:=",
            self.number_of_bounces,
            "Multi-Bounce Ray Density Control:=",
            self.multi_bounce_ray_density_control,
            "MBRD Max sub divisions:=",
            self.mbrd_max_subdivision,
            "Shoot UTD Rays:=",
            self.shoot_utd_rays,
            "ShootFilterType:=",
            self.shoot_type,
        ]
        if self.shoot_type == "Rays by index":
            args.extend(
                [
                    "start index:=",
                    self.start_index,
                    "stop index:=",
                    self.stop_index,
                    "index step:=",
                    self.step_index,
                ]
            )
        elif self.shoot_type == "Rays in box":
            box_id = None
            if isinstance(self.ray_box, int):
                box_id = self.ray_box
            elif isinstance(self.ray_box, str):
                box_id = self._postprocessor._primitives._object_names_to_ids[self.ray_box]
            else:
                box_id = self.ray_box.id
            args.extend("FilterBoxID:=", box_id)
        elif self.shoot_type == "Single ray":
            args.extend("Ray elevation:=", self.ray_elevation, "Ray azimuth:=", self.ray_azimuth)
        args.append("LaunchFrom:=")
        if self.is_plane_wave:
            args.append("Launch from Plane-Wave")
            args.append("Incident direction theta:=")
            args.append(self.incident_theta)
            args.append("Incident direction phi:=")
            args.append(self.incident_phi)
            args.append("Vertical Incident Polarization:=")
            args.append(self.vertical_polarization)
        else:
            args.append("Launch from Custom")
            args.append("LaunchFromPointID:=")
            args.append(-1)
            args.append("CustomLocationCoordSystem:=")
            args.append(self.custom_coordinatesystem)
            args.append("CustomLocation:=")
            args.append(self.custom_location)
        return args

    @pyaedt_function_handler()
    def _create_args_creeping(self):
        args = [
            "NAME:" + self.name,
            "UserSpecifyName:=",
            0,
            "UserSpecifyFolder:=",
            0,
            "QuantityName:=",
            self.quantity_name,
            "PlotFolder:=",
            "Visual Ray Trace CW",
            "IntrinsicVar:=",
            "",
            "MaxFrequency:=",
            self.max_frequency,
            "SampleDensity:=",
            self.sample_density,
            "RayCutOff:=",
            self.ray_cutoff,
            "Irregular Surface Tolerance:=",
            self.irregular_surface_tolerance,
            "LaunchFrom:=",
        ]
        if self.is_plane_wave:
            args.append("Launch from Plane-Wave")
            args.append("Incident direction theta:=")
            args.append(self.incident_theta)
            args.append("Incident direction phi:=")
            args.append(self.incident_phi)
            args.append("Vertical Incident Polarization:=")
            args.append(self.vertical_polarization)
        else:
            args.append("Launch from Custom")
            args.append("LaunchFromPointID:=")
            args.append(-1)
            args.append("CustomLocationCoordSystem:=")
            args.append(self.custom_coordinatesystem)
            args.append("CustomLocation:=")
            args.append(self.custom_location)
        args.append("SBRRayDensity:=")
        args.append(self.ray_density)
        return args

    @pyaedt_function_handler()
    def create(self):
        """Create a field plot.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        try:
            if self.is_creeping_wave:
                self._ofield.CreateFieldPlot(self._create_args_creeping(), "CreepingWave_VRT")
            else:
                self._ofield.CreateFieldPlot(self._create_args(), "VRT")
            return True
        except:
            return False

    @pyaedt_function_handler()
    def update(self):
        """Update the field plot.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        try:
            if self.is_creeping_wave:
                self._ofield.ModifyFieldPlot(self.name, self._create_args_creeping())

            else:
                self._ofield.ModifyFieldPlot(self.name, self._create_args())
            return True
        except:
            return False

    @pyaedt_function_handler()
    def delete(self):
        """Delete the field plot."""
        self._ofield.DeleteFieldPlot([self.name])
        return True

    @pyaedt_function_handler()
    def export(self, path_to_hdm_file=None):
        """Export the Visual Ray Tracing to ``hdm`` file.

        Parameters
        ----------
        path_to_hdm_file : str, optional
            Full path to output file. If ``None``, the file will be exported in working directory.

        Returns
        -------
        str
            Path to the file.
        """
        if not path_to_hdm_file:
            path_to_hdm_file = os.path.join(self._postprocessor._app.working_directory, self.name + ".hdm")
        self._ofield.ExportFieldPlot(self.name, False, path_to_hdm_file)
        return path_to_hdm_file
