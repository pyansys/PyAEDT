from collections import OrderedDict
import itertools
import json
import logging
import math
import os
import shutil
import sys
import time

from pyaedt import is_ironpython
from pyaedt import pyaedt_function_handler
from pyaedt.application.Variables import decompose_variable_value
from pyaedt.generic.constants import AEDT_UNITS
from pyaedt.generic.constants import db10
from pyaedt.generic.constants import db20
from pyaedt.generic.constants import unit_converter
from pyaedt.generic.general_methods import check_and_download_file
from pyaedt.generic.general_methods import check_and_download_folder
from pyaedt.generic.general_methods import conversion_function
from pyaedt.generic.general_methods import open_file
from pyaedt.generic.general_methods import write_csv
from pyaedt.generic.plot import get_structured_mesh
from pyaedt.generic.plot import is_notebook
from pyaedt.generic.plot import plot_2d_chart
from pyaedt.generic.plot import plot_3d_chart
from pyaedt.generic.plot import plot_polar_chart
from pyaedt.generic.settings import settings
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
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        plt = None


def simplify_stl(input_file, output_file=None, decimation=0.5, preview=False):
    """Import and simplify a stl file using pyvista and fast-simplification.

    Parameters
    ----------
    input_file : str
        Input stl file.
    output_file : str, optional
        Output stl file.
    decimation : float, optional
        Fraction of the original mesh to remove before creating the stl file.  If set to ``0.9``,
        this function will try to reduce the data set to 10% of its
        original size and will remove 90% of the input triangles.
    preview : bool, optional
        Whether to preview the model in pyvista or skip it.

    Returns
    -------
    str
        Full path to output stl.
    """
    mesh = pv.read(input_file)
    if not output_file:
        output_file = os.path.splitext(input_file)[0] + "_output.stl"
    simple = mesh.decimate_pro(decimation, preserve_topology=True, boundary_vertex_deletion=False)
    simple.save(output_file)
    if preview:
        pl = pv.Plotter(shape=(1, 2))
        dargs = dict(show_edges=True, color=True)
        pl.add_mesh(mesh, **dargs)
        pl.add_text("Input mesh", font_size=24)
        pl.reset_camera()
        pl.subplot(0, 1)
        pl.add_mesh(simple, **dargs)
        pl.add_text("Decimated mesh", font_size=24)
        pl.reset_camera()
        pl.link_views()
        if "PYTEST_CURRENT_TEST" not in os.environ:
            pl.show()
    return output_file


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
            except Exception:
                self.units_sweeps[intrinsic] = None
        self.init_solutions_data()
        self._ifft = None

    @property
    def enable_pandas_output(self):
        """
        Set/Get a flag to use Pandas to export dict and lists. This applies to Solution data output.
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
            ``True`` when successful, ``False`` when failed.
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

    @pyaedt_function_handler(variation_name="variation")
    def variation_values(self, variation):
        """Get the list of the specific variation available values.

        Parameters
        ----------
        variation : str
            Name of variation to return.

        Returns
        -------
        list
            List of variation values.
        """
        if variation in self.intrinsics:
            return self.intrinsics[variation]
        else:
            vars_vals = []
            for el in self.variations:
                if variation in el and el[variation] not in vars_vals:
                    vars_vals.append(el[variation])
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
            solution_data = {}

            for data, comb in zip(self._original_data, self.variations):
                solution = list(data.GetRealDataValues(expression, False))
                values = []
                for el in list(self.intrinsics.keys()):
                    values.append(list(OrderedDict.fromkeys(data.GetSweepValues(el, False))))

                i = 0
                c = [comb[v] for v in list(comb.keys())]
                for t in itertools.product(*values):
                    solution_data[tuple(c + list(t))] = solution[i]
                    i += 1
            sols_data[expression] = solution_data
        if self.enable_pandas_output:
            return pd.DataFrame.from_dict(sols_data)
        else:
            return sols_data

    @pyaedt_function_handler()
    def _init_solution_data_imag(self):
        """ """
        sols_data = {}

        for expression in self.expressions:
            solution_data = {}
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
                    solution_data[tuple(c + list(t))] = solution[i]
                    i += 1
            sols_data[expression] = solution_data
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
        solution_data = self._solutions_mag[expression]
        sol = []
        position = list(self._sweeps_names).index(self.primary_sweep)
        sw = self.variation_values(self.primary_sweep)
        for el in sw:
            temp[position] = el
            try:
                sol.append(solution_data[tuple(temp)])
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
    @pyaedt_function_handler(datalist="data", dataunits="data_units")
    def _convert_list_to_SI(data, data_units, units):
        """Convert a data list to the SI unit system.

        Parameters
        ----------
        data : list
           List of data to convert.
        data_units : str
            Data units.
        units : str
            SI units to convert data into.


        Returns
        -------
        list
           List of the data converted to the SI unit system.

        """
        sol = data
        if data_units in AEDT_UNITS and units in AEDT_UNITS[data_units]:
            sol = [i * AEDT_UNITS[data_units][units] for i in data]
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

        solution_data = list(self._solutions_real[expression].keys())
        sol = []
        position = list(self._sweeps_names).index(self.primary_sweep)

        for el in self.primary_sweep_values:
            temp[position] = el
            if tuple(temp) in solution_data:
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

        solution_data = self._solutions_real[expression]
        sol = []
        position = list(self._sweeps_names).index(self.primary_sweep)

        for el in self.primary_sweep_values:
            temp[position] = el
            try:
                sol.append(solution_data[tuple(temp)])
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

        solution_data = self._solutions_imag[expression]
        sol = []
        position = list(self._sweeps_names).index(self.primary_sweep)
        for el in self.primary_sweep_values:
            temp[position] = el
            try:
                sol.append(solution_data[tuple(temp)])
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
            ``True`` when successful, ``False`` when failed.
        """
        header = []
        des_var = self._original_data[0].GetDesignVariableNames()
        sweep_var = self._original_data[0].GetSweepNames()
        for el in self._sweeps_names:
            unit = ""
            if el in des_var:
                unit = self._original_data[0].GetDesignVariableUnits(el)
            elif el in sweep_var:
                unit = self._original_data[0].GetSweepUnits(el)
            if unit == "":
                header.append("{}".format(el))
            else:
                header.append("{} [{}]".format(el, unit))
        # header = [el for el in self._sweeps_names]
        for el in self.expressions:
            data_unit = self._original_data[0].GetDataUnits(el)
            if data_unit:
                data_unit = " [{}]".format(data_unit)
            if not self.is_real_only(el):

                header.append(el + " (Real){}".format(data_unit))
                header.append(el + " (Imag){}".format(data_unit))
            else:
                header.append(el + "{}".format(data_unit))

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

    @pyaedt_function_handler(math_formula="formula", xlabel="x_label", ylabel="y_label")
    def plot(
        self,
        curves=None,
        formula=None,
        size=(2000, 1000),
        show_legend=True,
        x_label="",
        y_label="",
        title="",
        snapshot_path=None,
        is_polar=False,
        show=True,
    ):
        """Create a matplotlib figure based on a list of data.

        Parameters
        ----------
        curves : list
            Curves to be plotted. The default is ``None``, in which case
            the first curve is plotted.
        formula : str , optional
            Mathematical formula to apply to the plot curve. The default is ``None``,
            in which case only real value of the data stored in the solution data is plotted.
            Options are ``"abs"``, ``"db10"``, ``"db20"``, ``"im"``, ``"mag"``, ``"phasedeg"``,
            ``"phaserad"``, and ``"re"``.
        size : tuple, optional
            Image size in pixels (width, height).
        show_legend : bool
            Whether to show the legend. The default is ``True``.
            This parameter is ignored if the number of curves to plot is
            greater than 15.
        x_label : str
            Plot X label.
        y_label : str
            Plot Y label.
        title : str
            Plot title label.
        snapshot_path : str
            Full path to image file if a snapshot is needed.
        is_polar : bool, optional
            Set to `True` if this is a polar plot.

        Returns
        -------
        :class:`matplotlib.pyplot.Figure`
            Matplotlib figure object.
        """
        if is_ironpython:  # pragma: no cover
            return False
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
            if not formula:
                data_plot.append([sw, self.data_real(curve), curve])
            elif formula == "re":
                data_plot.append([sw, self.data_real(curve), "{}({})".format(formula, curve)])
            elif formula == "im":
                data_plot.append([sw, self.data_imag(curve), "{}({})".format(formula, curve)])
            elif formula == "db20":
                data_plot.append([sw, self.data_db20(curve), "{}({})".format(formula, curve)])
            elif formula == "db10":
                data_plot.append([sw, self.data_db10(curve), "{}({})".format(formula, curve)])
            elif formula == "mag":
                data_plot.append([sw, self.data_magnitude(curve), "{}({})".format(formula, curve)])
            elif formula == "phasedeg":
                data_plot.append([sw, self.data_phase(curve, False), "{}({})".format(formula, curve)])
            elif formula == "phaserad":
                data_plot.append([sw, self.data_phase(curve, True), "{}({})".format(formula, curve)])
        if not x_label:
            x_label = sweep_name
        if not y_label:
            y_label = formula
        if not title:
            title = "Simulation Results Plot"
        if len(data_plot) > 15:
            show_legend = False
        if is_polar:
            return plot_polar_chart(data_plot, size, show_legend, x_label, y_label, title, snapshot_path, show=show)
        else:
            return plot_2d_chart(data_plot, size, show_legend, x_label, y_label, title, snapshot_path, show=show)

    @pyaedt_function_handler(xlabel="x_label", ylabel="y_label", math_formula="formula")
    def plot_3d(
        self,
        curve=None,
        x_axis="Theta",
        y_axis="Phi",
        x_label="",
        y_label="",
        title="",
        formula=None,
        size=(2000, 1000),
        snapshot_path=None,
        show=True,
    ):
        """Create a matplotlib 3D figure based on a list of data.

        Parameters
        ----------
        curve : str
            Curve to be plotted. If None, the first curve will be plotted.
        x_axis : str, optional
            X-axis sweep. The default is ``"Theta"``.
        y_axis : str, optional
            Y-axis sweep. The default is ``"Phi"``.
        x_label : str
            Plot X label.
        y_label : str
            Plot Y label.
        title : str
            Plot title label.
        formula : str , optional
            Mathematical formula to apply to the plot curve. The default is ``None``.
            Options are `"abs"``, ``"db10"``, ``"db20"``, ``"im"``, ``"mag"``, ``"phasedeg"``,
            ``"phaserad"``, and ``"re"``.
        size : tuple, optional
            Image size in pixels (width, height). The default is ``(2000, 1000)``.
        snapshot_path : str, optional
            Full path to image file if a snapshot is needed.
            The default is ``None``.

        Returns
        -------
        :class:`matplotlib.figure.Figure`
            Matplotlib figure object.
        """
        if is_ironpython:
            return False  # pragma: no cover
        if not curve:
            curve = self.active_expression

        if not formula:
            formula = "mag"
        theta = self.variation_values(x_axis)
        y_axis_val = self.variation_values(y_axis)

        phi = []
        r = []
        for el in y_axis_val:
            self.active_variation[y_axis] = el
            phi.append(el * math.pi / 180)

            if formula == "re":
                r.append(self.data_real(curve))
            elif formula == "im":
                r.append(self.data_imag(curve))
            elif formula == "db20":
                r.append(self.data_db20(curve))
            elif formula == "db10":
                r.append(self.data_db10(curve))
            elif formula == "mag":
                r.append(self.data_magnitude(curve))
            elif formula == "phasedeg":
                r.append(self.data_phase(curve, False))
            elif formula == "phaserad":
                r.append(self.data_phase(curve, True))
        active_sweep = self.active_intrinsic[self.primary_sweep]
        position = self.variation_values(self.primary_sweep).index(active_sweep)
        if len(self.variation_values(self.primary_sweep)) > 1:
            new_r = []
            for el in r:
                new_r.append([el[position]])
            r = new_r
        data_plot = [theta, phi, r]
        if not x_label:
            x_label = x_axis
        if not y_label:
            y_label = y_axis
        if not title:
            title = "Simulation Results Plot"
        return plot_3d_chart(data_plot, size, x_label, y_label, title, snapshot_path, show=show)

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
            e_real_x = np.reshape(self._solutions_real[curve_header + "X"].copy().values, (len(freq), len(v), len(u)))
            e_imag_x = np.reshape(self._solutions_imag[curve_header + "X"].copy().values, (len(freq), len(v), len(u)))
            e_real_y = np.reshape(self._solutions_real[curve_header + "Y"].copy().values, (len(freq), len(v), len(u)))
            e_imag_y = np.reshape(self._solutions_imag[curve_header + "Y"].copy().values, (len(freq), len(v), len(u)))
            e_real_z = np.reshape(self._solutions_real[curve_header + "Z"].copy().values, (len(freq), len(v), len(u)))
            e_imag_z = np.reshape(self._solutions_imag[curve_header + "Z"].copy().values, (len(freq), len(v), len(u)))
        else:
            vals_e_real_x = [j for j in self._solutions_real[curve_header + "X"].values()]
            vals_e_imag_x = [j for j in self._solutions_imag[curve_header + "X"].values()]
            vals_e_real_y = [j for j in self._solutions_real[curve_header + "Y"].values()]
            vals_e_imag_y = [j for j in self._solutions_imag[curve_header + "Y"].values()]
            vals_e_real_z = [j for j in self._solutions_real[curve_header + "Z"].values()]
            vals_e_imag_z = [j for j in self._solutions_imag[curve_header + "Z"].values()]

            e_real_x = np.reshape(vals_e_real_x, (len(freq), len(v), len(u)))
            e_imag_x = np.reshape(vals_e_imag_x, (len(freq), len(v), len(u)))
            e_real_y = np.reshape(vals_e_real_y, (len(freq), len(v), len(u)))
            e_imag_y = np.reshape(vals_e_imag_y, (len(freq), len(v), len(u)))
            e_real_z = np.reshape(vals_e_real_z, (len(freq), len(v), len(u)))
            e_imag_z = np.reshape(vals_e_imag_z, (len(freq), len(v), len(u)))

        temp_e_comp_x = e_real_x + 1j * e_imag_x  # Here is the complex FD data matrix, ready for transforming
        temp_e_comp_y = e_real_y + 1j * e_imag_y
        temp_e_comp_z = e_real_z + 1j * e_imag_z

        e_comp_x = np.zeros((len(freq), len(v), len(u)), dtype="complex_")
        e_comp_y = np.zeros((len(freq), len(v), len(u)), dtype="complex_")
        e_comp_z = np.zeros((len(freq), len(v), len(u)), dtype="complex_")
        if window:
            timewin = np.hanning(len(freq))

            for row in range(0, len(v)):
                for col in range(0, len(u)):
                    e_comp_x[:, row, col] = np.multiply(temp_e_comp_x[:, row, col], timewin)
                    e_comp_y[:, row, col] = np.multiply(temp_e_comp_y[:, row, col], timewin)
                    e_comp_z[:, row, col] = np.multiply(temp_e_comp_z[:, row, col], timewin)
        else:
            e_comp_x = temp_e_comp_x
            e_comp_y = temp_e_comp_y
            e_comp_z = temp_e_comp_z

        e_time_x = np.fft.ifft(np.fft.fftshift(e_comp_x, 0), len(freq), 0, None)
        e_time_y = np.fft.ifft(np.fft.fftshift(e_comp_y, 0), len(freq), 0, None)
        e_time_z = np.fft.ifft(np.fft.fftshift(e_comp_z, 0), len(freq), 0, None)
        e_time = np.zeros((np.size(freq), np.size(v), np.size(u)))
        for i in range(0, len(freq)):
            e_time[i, :, :] = np.abs(
                np.sqrt(np.square(e_time_x[i, :, :]) + np.square(e_time_y[i, :, :]) + np.square(e_time_z[i, :, :]))
            )
        self._ifft = e_time

        return self._ifft

    @pyaedt_function_handler(csv_dir="csv_path", name_str="csv_file_header")
    def ifft_to_file(
        self,
        u_axis="_u",
        v_axis="_v",
        coord_system_center=None,
        db_val=False,
        num_frames=None,
        csv_path=None,
        csv_file_header="res_",
    ):
        """Save IFFT matrix to a list of CSV files (one per time step).

        Parameters
        ----------
        u_axis : str, optional
            U Axis name. Default is Hfss name "_u"
        v_axis : str, optional
            V Axis name. Default is Hfss name "_v"
        coord_system_center : list, optional
            List of UV GlobalCS Center.
        db_val : bool, optional
            Whether data must be exported into a database. The default is ``False``.
        num_frames : int, optional
            Number of frames to export. The default is ``None``.
        csv_path : str, optional
            Output path. The default is ``None``.
        csv_file_header : str, optional
            CSV file header. The default is ``"res_"``.

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
        if os.path.exists(csv_path):
            files = [os.path.join(csv_path, f) for f in os.listdir(csv_path) if csv_file_header in f and ".csv" in f]
            for file in files:
                os.remove(file)
        else:
            os.mkdir(csv_path)

        for frame in range(frames):
            output = os.path.join(csv_path, csv_file_header + str(frame) + ".csv")
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

        txt_file_name = csv_path + "fft_list.txt"
        textfile = open_file(txt_file_name, "w")

        for element in csv_list:
            textfile.write(element + "\n")
        textfile.close()
        return txt_file_name


class FfdSolutionData(object):
    """Provides antenna array far-field data.

    Read embedded element patterns generated in HFSS and return the Python interface
    to plot and analyze the array far-field data.

    Parameters
    ----------
    eep_files : list or str
        List of embedded element pattern files for each frequency.
        If data is only provided for a single frequency, then a string can be passed
        instead of a one-element list.
    frequencies : list, str, int, or float
        List of frequencies.
        If data is only available for a single frequency, then a float or integer may be passed
        instead of a one-element list.

    Examples
    --------

    >>> import pyaedt
    >>> from pyaedt.modules.solutions import FfdSolutionData
    >>> app = pyaedt.Hfss(specified_version="2023.2", designname="Antenna")
    >>> setup_name = "Setup1 : LastAdaptive"
    >>> frequencies = [77e9]
    >>> sphere = "3D"
    >>> data = app.get_antenna_ffd_solution_data(frequencies,setup_name,sphere)
    >>> eep_files = data.eep_files
    >>> frequencies = data.frequencies
    >>> app.release_desktop()
    >>> farfield_data = FfdSolutionData(frequencies=frequencies, eep_files=eep_files)
    >>> farfield_data.polar_plot_3d_pyvista(quantity_format="dB10",qty_str="rETotal")
    """

    def __init__(
        self,
        eep_files,
        frequencies,
    ):
        self.logger = logging.getLogger(__name__)

        self._raw_data = {}
        self.farfield_data = {}
        self._eep_file_info_list = []
        self.port_position = {}

        if isinstance(frequencies, (float, str, int)):
            frequencies = [frequencies]
        self._freq_index = 0
        self.frequencies = frequencies

        if isinstance(eep_files, str):
            eep_files = [eep_files]
        self.eep_files = eep_files

        if len(self.eep_files) != len(self.frequencies):  # pragma: no cover
            raise Exception("Number of frequencies are different than the number of EEP files.")

        for eep in eep_files:
            self._read_eep_files(eep)

        if (
            not self._eep_file_info_list
            or not self.port_position
            or len(self._eep_file_info_list) != len(self.frequencies)
        ):  # pragma: no cover
            raise Exception("Wrong farfield file load.")

        self.eep_file_info = self._eep_file_info_list[0]
        self.all_port_names = list(self.eep_file_info.keys())

        self._phase_offset = [0] * len(self.all_port_names)
        self._mag_offset = [1] * len(self.all_port_names)
        self._origin = [0, 0, 0]
        self._taper = "flat"

        self.model_info = []
        self._is_array = []
        self._component_objects = []
        self._array_dimension = []
        self._cell_position = []
        self._lattice_vector = []
        self.mesh = None

        for eep in eep_files:
            metadata_file = os.path.join(os.path.dirname(eep), "eep.json")
            if os.path.exists(metadata_file):
                with open_file(metadata_file) as f:
                    # Load JSON data from file
                    metadata = json.load(f)
                self.model_info.append(metadata["model_info"])
                if "array_dimension" in metadata and "component_objects" in metadata and "cell_position" in metadata:
                    self._is_array.append(True)
                    self._component_objects.append(metadata["component_objects"])
                    self._array_dimension.append(metadata["array_dimension"])
                    self._cell_position.append(metadata["cell_position"])
                    self._lattice_vector.append(metadata["lattice_vector"])
                else:
                    self._is_array.append(False)

        self.port_index = self._get_port_index()
        if not self._get_port_index:  # pragma: no cover
            raise Exception("Wrong port index load.")
        self.__model_units = "meter"
        self.frequency = self.frequencies[0]

        self.a_min = sys.maxsize
        self.a_max = 0
        self.b_min = sys.maxsize
        self.b_max = 0
        if self.port_index:
            for row, col in self.port_index.values():
                self.a_min = min(self.a_min, row - 1)
                self.a_max = max(self.a_max, row - 1)
                self.b_min = min(self.b_min, col - 1)
                self.b_max = max(self.b_max, col - 1)

    @property
    def frequency(self):
        """Active frequency."""
        return self._frequency

    @frequency.setter
    def frequency(self, val):
        if val in self.frequencies:
            freq_index = self.frequencies.index(val)
            eep_file_info = self._eep_file_info_list[freq_index]
            init_flag = self._init_ffd(eep_file_info)
            if init_flag:
                self._frequency = val
                self._freq_index = self.frequencies.index(val)
                self.eep_file_info = self._eep_file_info_list[self._freq_index]
                self.farfield_data = self.combine_farfield()
            else:  # pragma: no cover
                self.logger.error("Wrong farfield information.")
        else:  # pragma: no cover
            self.logger.error("Frequency not available.")

    @property
    def frequency_value(self):
        """Frequency value in Hz."""
        if isinstance(self.frequency, str):
            frequency, units = decompose_variable_value(str(self.frequency))
            return unit_converter(frequency, "Freq", units, "Hz")
        else:
            return float(self.frequency)

    @property
    def phase_offset(self):
        """List of additional phase offsets in degrees on each port. This property
        is useful when an element has more than one port."""
        return self._phase_offset

    @phase_offset.setter
    def phase_offset(self, phases):
        if len(phases) != len(self.all_port_names):
            self.logger.error("Number of phases must be equal to number of ports.")
        else:
            self._phase_offset = phases
            self.farfield_data = self.combine_farfield()

    @property
    def mag_offset(self):
        """List of additional magnitudes on each port. This property is
        useful when an element has more than one port."""
        return self._mag_offset

    @mag_offset.setter
    def mag_offset(self, mags):
        if len(mags) != len(self.all_port_names):
            self.logger.error("Number of magnitude must be equal to number of ports.")
        else:
            self._mag_offset = mags
            self.farfield_data = self.combine_farfield()

    @property
    def taper(self):
        """Taper type.

        Options are:

        - ``"cosine"``
        - ``"flat"``
        - ``"hamming"``
        - ``"triangular"``
        - ``"uniform"``
        """
        return self._taper

    @taper.setter
    def taper(self, val):
        if val.lower() in ("flat", "uniform", "cosine", "triangular", "hamming"):
            self._taper = val
        else:
            self.logger.error("This taper is not implemented")

    @property
    def origin(self):
        """Far field origin in meters."""
        return self._origin

    @origin.setter
    def origin(self, vals):
        if len(vals) != 3:
            self.logger.error("Origin is wrong.")
        else:
            self._origin = vals
            self.farfield_data = self.combine_farfield()

    @pyaedt_function_handler()
    def _assign_weight(self, a, b):
        """Assign weight to array.

        Parameters
        ----------
        a : int
            Index of array, column.
        b : int
            Index of array, row.

        Returns
        -------
        float
            Weight applied to specific index of the array.
        """
        taper = self.taper

        if taper.lower() in ("flat", "uniform") or not self._is_array[self._freq_index]:
            return 1

        cosinePow = 1
        edgeTaper_dB = -200

        edgeTaper = 10 ** ((float(edgeTaper_dB)) / 20)

        threshold = 1e-10

        # find the distance between current cell and array center in terms of index
        lattice_vector = self._lattice_vector[self._freq_index]
        if not lattice_vector or not len(lattice_vector) == 6:
            return 1

        center_a = (self.a_min + self.a_max) / 2
        center_b = (self.b_min + self.b_max) / 2

        length_in_direction1 = a - center_a
        length_in_direction2 = b - center_b
        max_length_in_dir1 = self.a_max - self.a_min
        max_length_in_dir2 = self.b_max - self.b_min

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

        return w1 * w2

    def _phase_shift_steering(self, a, b, theta=0.0, phi=0.0):
        """Shift element phase for a specific Theta and Phi scan angle in degrees.

        This method calculates phase shifts between array elements in A and B directions given the lattice vector.

        Parameters
        ----------
        a : int
            Index of array, column.
        b : int
            Index of array, row.
        theta : float, optional
            Theta scan angle in degrees. The default is ``0.0``.
        phi : float, optional
            Phi scan angle in degrees. The default is ``0.0``.

        Returns
        -------
        float
            Phase shift in degrees.
        """
        c = 299792458
        k = (2 * math.pi * self.frequency_value) / c
        a = int(a)
        b = int(b)
        theta = np.deg2rad(theta)
        phi = np.deg2rad(phi)

        lattice_vector = self._lattice_vector[self._freq_index]

        a_x, a_y, b_x, b_y = [lattice_vector[0], lattice_vector[1], lattice_vector[3], lattice_vector[4]]

        phase_shift_a = -((a_x * k * np.sin(theta) * np.cos(phi)) + (a_y * k * np.sin(theta) * np.sin(phi)))

        phase_shift_b = -((b_x * k * np.sin(theta) * np.cos(phi)) + (b_y * k * np.sin(theta) * np.sin(phi)))

        phase_shift = a * phase_shift_a + b * phase_shift_b

        return np.rad2deg(phase_shift)

    @pyaedt_function_handler()
    def combine_farfield(self, phi_scan=0, theta_scan=0):
        """Compute the far field pattern calculated for a specific phi and theta scan angle requested.

        Parameters
        ----------
        phi_scan : float, optional
            Phi scan angle in degrees. The default is ``0.0``.
        theta_scan : float, optional
            Theta scan angle in degrees. The default is ``0.0``.

        Returns
        -------
        dict
            Far field data dictionary.
        """
        w_dict = {}
        w_dict_ang = {}
        w_dict_mag = {}
        port_positions = {}
        port_cont = 0
        initial_port = self.all_port_names[0]

        # Obtain weights for each port
        for port_name in self.all_port_names:
            index_str = self.port_index[port_name]
            a = index_str[0] - 1
            b = index_str[1] - 1
            if self._is_array[self._freq_index]:
                phase_shift = self._phase_shift_steering(a, b, theta_scan, phi_scan)
                magnitude = self._assign_weight(a=a, b=b)
            else:
                phase_shift = 0
                magnitude = 1
            w_mag = magnitude * self.mag_offset[port_cont]
            w_ang = np.deg2rad(self.phase_offset[port_cont] + phase_shift)
            w_dict[port_name] = np.sqrt(w_mag) * np.exp(1j * w_ang)
            w_dict_ang[port_name] = w_ang
            w_dict_mag[port_name] = w_mag
            port_positions[port_name] = self.port_position[port_name]
            port_cont += 1

        # Combine farfield of each port
        length_of_ff_data = len(self._raw_data[initial_port]["rETheta"])
        theta_range = self._raw_data[initial_port]["Theta"]
        phi_range = self._raw_data[initial_port]["Phi"]
        Ntheta = len(theta_range)
        Nphi = len(phi_range)
        incident_power = 0
        ph, th = np.meshgrid(self._raw_data[initial_port]["Phi"], self._raw_data[initial_port]["Theta"])
        ph = np.deg2rad(ph)
        th = np.deg2rad(th)
        c = 299792458
        k = 2 * np.pi * self.frequency_value / c
        kx_grid = k * np.sin(th) * np.cos(ph)
        ky_grid = k * np.sin(th) * np.sin(ph)
        kz_grid = k * np.cos(th)
        kx_flat = kx_grid.ravel()
        ky_flat = ky_grid.ravel()
        kz_flat = kz_grid.ravel()
        rEphi_fields_sum = np.zeros(length_of_ff_data, dtype=complex)
        rETheta_fields_sum = np.zeros(length_of_ff_data, dtype=complex)

        # Farfield superposition
        for _, port in enumerate(self.all_port_names):
            if port not in w_dict:
                w_dict[port] = np.sqrt(0) * np.exp(1j * 0)
            incident_power += w_dict_mag[port]
            xyz_pos = port_positions[port]
            array_factor = (
                np.exp(1j * (xyz_pos[0] * kx_flat + xyz_pos[1] * ky_flat + xyz_pos[2] * kz_flat)) * w_dict[port]
            )
            rEphi_fields_sum += array_factor * self._raw_data[port]["rEPhi"]
            rETheta_fields_sum += array_factor * self._raw_data[port]["rETheta"]

        # Farfield origin sift
        origin = self.origin
        array_factor = np.exp(-1j * (origin[0] * kx_flat + origin[1] * ky_flat + origin[2] * kz_flat))
        rETheta_fields_sum = array_factor * rETheta_fields_sum
        rEphi_fields_sum = array_factor * rEphi_fields_sum

        rEtheta_fields_sum = np.reshape(rETheta_fields_sum, (Ntheta, Nphi))
        rEphi_fields_sum = np.reshape(rEphi_fields_sum, (Ntheta, Nphi))

        farfield_data = OrderedDict()
        farfield_data["rEPhi"] = rEphi_fields_sum
        farfield_data["rETheta"] = rEtheta_fields_sum
        farfield_data["rETotal"] = np.sqrt(
            np.power(np.abs(rEphi_fields_sum), 2) + np.power(np.abs(rEtheta_fields_sum), 2)
        )
        farfield_data["Theta"] = theta_range
        farfield_data["Phi"] = phi_range
        farfield_data["nPhi"] = Nphi
        farfield_data["nTheta"] = Ntheta
        farfield_data["Pincident"] = incident_power
        real_gain = 2 * np.pi * np.abs(np.power(farfield_data["rETotal"], 2)) / incident_power / 377
        farfield_data["RealizedGain"] = real_gain
        farfield_data["RealizedGain_Total"] = real_gain
        farfield_data["RealizedGain_dB"] = 10 * np.log10(real_gain)
        real_gain = 2 * np.pi * np.abs(np.power(farfield_data["rETheta"], 2)) / incident_power / 377
        farfield_data["RealizedGain_Theta"] = real_gain
        real_gain = 2 * np.pi * np.abs(np.power(farfield_data["rEPhi"], 2)) / incident_power / 377
        farfield_data["RealizedGain_Phi"] = real_gain
        farfield_data["Element_Location"] = port_positions
        return farfield_data

    # fmt: off
    @pyaedt_function_handler(farfield_quantity="quantity",
                             phi_scan="phi",
                             theta_scan="theta",
                             export_image_path="image_path")
    def plot_farfield_contour(
            self,
            quantity="RealizedGain",
            phi=0,
            theta=0,
            size=None,
            title=None,
            quantity_format="dB10",
            image_path=None,
            levels=64,
            show=True,
            polar=True,
            max_theta=180,
            **kwargs
    ):
        # fmt: on
        """Create a contour plot of a specified quantity.

        Parameters
        ----------
        quantity : str, optional
            Far field quantity to plot. The default is ``"RealizedGain"``.
            Available quantities are: ``"RealizedGain"``, ``"RealizedGain_Phi"``, ``"RealizedGain_Theta"``,
            ``"rEPhi"``, ``"rETheta"``, and ``"rETotal"``.
        phi : float, int, optional
            Phi scan angle in degrees. The default is ``0``.
        theta : float, int, optional
            Theta scan angle in degrees. The default is ``0``.
        size : tuple, optional
            Image size in pixel (width, height). The default is ``None``, in which case resolution
            is determined automatically.
        title : str, optional
            Plot title. The default is ``"RectangularPlot"``.
        quantity_format : str, optional
            Conversion data function.
            Available functions are: ``"abs"``, ``"ang"``, ``"dB10"``, ``"dB20"``, ``"deg"``, ``"imag"``, ``"norm"``,
            and ``"real"``.
        image_path : str, optional
            Full path for the image file. The default is ``None``, in which case the file is not exported.
        levels : int, optional
            Color map levels. The default is ``64``.
        show : bool, optional
            Whether to show the plot. The default is ``True``. If ``False``, the Matplotlib
            instance of the plot is shown.
        polar : bool, optional
            Generate the plot in polar coordinates. The default is ``True``. If ``False``, the plot
            generated is rectangular.
        max_theta : float or int, optional
            Maxmum theta angle for plotting. The default is ``180``, which plots the far-field data for
            all angles. Setting ``max_theta`` to 90 limits the displayed data to the upper
            hemisphere, that is (0 < theta < 90).

        Returns
        -------
        :class:`matplotlib.pyplot.Figure`
            Matplotlib figure object.

        Examples
        --------
        >>> import pyaedt
        >>> app = pyaedt.Hfss(specified_version="2024.1", designname="Antenna")
        >>> setup_name = "Setup1 : LastAdaptive"
        >>> frequencies = [77e9]
        >>> sphere = "3D"
        >>> data = app.get_antenna_ffd_solution_data(frequencies,setup_name,sphere)
        >>> data.plot_farfield_contour()

        """
        if not title:
            title = quantity
        for k in kwargs:
            if k == "convert_to_db":  # pragma: no cover
                self.logger.warning("`convert_to_db` is deprecated since v0.7.8. Use `quantity_format` instead.")
                quantity_format = "dB10" if kwargs["convert_to_db"] else "abs"
            elif k == "qty_str":  # pragma: no cover
                self.logger.warning("`qty_str` is deprecated since v0.7.8. Use `quantity` instead.")
                quantity = kwargs["qty_str"]
            else:  # pragma: no cover
                msg = "{} not valid.".format(k)
                self.logger.error(msg)
                raise TypeError(msg)

        data = self.combine_farfield(phi, theta)
        if quantity not in data:  # pragma: no cover
            self.logger.error("Far field quantity is not available.")
            return False
        select = np.abs(data["Theta"]) <= max_theta  # Limit theta range for plotting.

        data_to_plot = data[quantity][select, :]
        data_to_plot = conversion_function(data_to_plot, quantity_format)
        if not isinstance(data_to_plot, np.ndarray):  # pragma: no cover
            self.logger.error("Wrong format quantity")
            return False
        ph, th = np.meshgrid(data["Phi"], data["Theta"][select])
        ph = ph * np.pi/180 if polar else ph
        # Convert to radians for polar plot.

        # TODO: Is it necessary to set the plot size?

        default_figsize = plt.rcParams["figure.figsize"]
        if size:  # Retain this code to remain consistent with other plotting methods.
            dpi = 100.0
            figsize = (size[0] / dpi, size[1] / dpi)
            plt.rcParams["figure.figsize"] = figsize
        else:
            figsize = default_figsize

        projection = 'polar' if polar else 'rectilinear'
        fig, ax = plt.subplots(subplot_kw={'projection': projection}, figsize=figsize)

        fig.suptitle(title)
        ax.set_xlabel("$\phi$ (Degrees)")
        if polar:
            ax.set_rticks(np.linspace(0, max_theta, 3))
        else:
            ax.set_ylabel("$\\theta (Degrees")

        plt.contourf(
            ph,
            th,
            data_to_plot,
            levels=levels,
            cmap="jet",
        )
        cbar = plt.colorbar()
        cbar.set_label(quantity_format, rotation=270, labelpad=20)

        if image_path:
            plt.savefig(image_path)
        if show:  # pragma: no cover
            plt.show()

        plt.rcParams["figure.figsize"] = default_figsize
        return fig

    # fmt: off
    @pyaedt_function_handler(farfield_quantity="quantity",
                             phi_scan="phi",
                             theta_scan="theta",
                             export_image_path="image_path")
    def plot_2d_cut(
            self,
            quantity="RealizedGain",
            primary_sweep="phi",
            secondary_sweep_value=0,
            phi=0,
            theta=0,
            title="Far Field Cut",
            quantity_format="dB10",
            image_path=None,
            show=True,
            is_polar=False,
            show_legend=True,
            **kwargs
    ):
        # fmt: on
        """Create a 2D plot of a specified quantity in Matplotlib.

        Parameters
        ----------
        quantity : str, optional
            Quantity to plot. The default is ``"RealizedGain"``.
            Available quantities are: ``"RealizedGain"``, ``"RealizedGain_Theta"``, ``"RealizedGain_Phi"``,
            ``"rETotal"``, ``"rETheta"``, and ``"rEPhi"``.
        primary_sweep : str, optional.
            X axis variable. The default is ``"phi"``. Options are ``"phi"`` and ``"theta"``.
        secondary_sweep_value : float, list, string, optional
            List of cuts on the secondary sweep to plot. The default is ``0``. Options are
            `"all"`, a single value float, or a list of float values.
        phi : float, int, optional
            Phi scan angle in degrees. The default is ``0``.
        theta : float, int, optional
            Theta scan angle in degrees. The default is ``0``.
        title : str, optional
            Plot title. The default is ``"RectangularPlot"``.
        quantity_format : str, optional
            Conversion data function.
            Available functions are: ``"abs"``, ``"ang"``, ``"dB10"``, ``"dB20"``, ``"deg"``, ``"imag"``, ``"norm"``,
            and ``"real"``.
        image_path : str, optional
            Full path for the image file. The default is ``None``, in which case an image in not exported.
        show : bool, optional
            Whether to show the plot. The default is ``True``.
            If ``False``, the Matplotlib instance of the plot is shown.
        is_polar : bool, optional
            Whether this plot is a polar plot. The default is ``True``.
        show_legend : bool, optional
            Whether to display the legend or not. The default is ``True``.

        Returns
        -------
        :class:`matplotlib.pyplot.Figure`
            Matplotlib figure object.
            If ``show=True``, a Matplotlib figure instance of the plot is returned.
            If ``show=False``, the plotted curve is returned.

        Examples
        --------
        >>> import pyaedt
        >>> app = pyaedt.Hfss(specified_version="2023.2", designname="Antenna")
        >>> setup_name = "Setup1 : LastAdaptive"
        >>> frequencies = [77e9]
        >>> sphere = "3D"
        >>> data = app.get_antenna_ffd_solution_data(frequencies,setup_name,sphere)
        >>> data.plot_2d_cut(theta=20)
        """
        for k in kwargs:
            if k == "convert_to_db":  # pragma: no cover
                self.logger.warning("`convert_to_db` is deprecated since v0.7.8. Use `quantity_format` instead.")
                quantity_format = "dB10" if kwargs["convert_to_db"] else "abs"
            elif k == "qty_str":  # pragma: no cover
                self.logger.warning("`qty_str` is deprecated since v0.7.8. Use `quantity` instead.")
                quantity = kwargs["qty_str"]
            else:  # pragma: no cover
                msg = "{} not valid.".format(k)
                self.logger.error(msg)
                raise TypeError(msg)

        data = self.combine_farfield(phi, theta)
        if quantity not in data:  # pragma: no cover
            self.logger.error("Far field quantity not available")
            return False

        data_to_plot = data[quantity]

        curves = []
        if primary_sweep == "phi":
            x_key, y_key = "Phi", "Theta"
            temp = data_to_plot
        else:
            y_key, x_key = "Phi", "Theta"
            temp = data_to_plot.T
        x = data[x_key]
        if is_polar:
            x = [i * 2 * math.pi / 360 for i in x]
        if secondary_sweep_value == "all":
            for el in data[y_key]:
                idx = self._find_nearest(data[y_key], el)
                y = temp[idx]
                y = conversion_function(y, quantity_format)
                if not isinstance(y, np.ndarray):  # pragma: no cover
                    self.logger.error("Format of quantity is wrong.")
                    return False
                curves.append([x, y, "{}={}".format(y_key, el)])
        elif isinstance(secondary_sweep_value, list):
            list_inserted = []
            for el in secondary_sweep_value:
                theta_idx = self._find_nearest(data[y_key], el)
                if theta_idx not in list_inserted:
                    y = temp[theta_idx]
                    y = conversion_function(y, quantity_format)
                    if not isinstance(y, np.ndarray):  # pragma: no cover
                        self.logger.error("Format of quantity is wrong.")
                        return False
                    curves.append([x, y, "{}={}".format(y_key, el)])
                    list_inserted.append(theta_idx)
        else:
            theta_idx = self._find_nearest(data[y_key], secondary_sweep_value)
            y = temp[theta_idx]
            y = conversion_function(y, quantity_format)
            if not isinstance(y, np.ndarray):  # pragma: no cover
                self.logger.error("Wrong format quantity")
                return False
            curves.append([x, y, "{}={}".format(y_key, data[y_key][theta_idx])])

        # FIXME: See if we need to keep this check on the curves length
        # if len(curves) > 15:
        #     show_legend = False
        if is_polar:
            return plot_polar_chart(
                curves,
                xlabel=x_key,
                ylabel=quantity,
                title=title,
                snapshot_path=image_path,
                show_legend=show_legend,
                show=show,
            )
        else:
            return plot_2d_chart(
                curves,
                xlabel=x_key,
                ylabel=quantity,
                title=title,
                snapshot_path=image_path,
                show_legend=show_legend,
                show=show,
            )

    # fmt: off
    @pyaedt_function_handler(farfield_quantity="quantity",
                             phi_scan="phi",
                             theta_scan="theta",
                             export_image_path="image_path")
    def polar_plot_3d(
            self,
            quantity="RealizedGain",
            phi=0,
            theta=0,
            title="3D Plot",
            quantity_format="dB10",
            image_path=None,
            show=True,
            **kwargs
    ):
        # fmt: on
        """Create a 3D plot of a specified quantity.

        Parameters
        ----------
        quantity : str, optional
            Far field quantity to plot. The default is ``"RealizedGain"``.
            Available quantities are: ``"RealizedGain"``, ``"RealizedGain_Phi"``, ``"RealizedGain_Theta"``,
            ``"rEPhi"``, ``"rETheta"``, and ``"rETotal"``.
        phi : float, int, optional
            Phi scan angle in degree. The default is ``0``.
        theta : float, int, optional
            Theta scan angle in degree. The default is ``0``.
        title : str, optional
            Plot title. The default is ``"3D Plot"``.
        quantity_format : str, optional
            Conversion data function.
            Available functions are: ``"abs"``, ``"ang"``, ``"dB10"``, ``"dB20"``, ``"deg"``, ``"imag"``, ``"norm"``,
            and ``"real"``.
        image_path : str, optional
            Full path for the image file. The default is ``None``, in which case a file is not exported.
        show : bool, optional
            Whether to show the plot. The default is ``True``.
            If ``False``, the Matplotlib instance of the plot is not shown.

        Returns
        -------
        :class:`matplotlib.pyplot.Figure`
            Matplotlib figure object.
            If ``show=True``, a Matplotlib figure instance of the plot is returned.
            If ``show=False``, the plotted curve is returned.

        Examples
        --------
        >>> import pyaedt
        >>> app = pyaedt.Hfss(specified_version="2023.2", designname="Antenna")
        >>> setup_name = "Setup1 : LastAdaptive"
        >>> frequencies = [77e9]
        >>> sphere = "3D"
        >>> data = app.get_antenna_ffd_solution_data(frequencies,setup_name,sphere)
        >>> data.polar_plot_3d(theta=10)
        """
        for k in kwargs:
            if k == "convert_to_db":  # pragma: no cover
                self.logger.warning("`convert_to_db` is deprecated since v0.7.8. Use `quantity_format` instead.")
                quantity_format = "dB10" if kwargs["convert_to_db"] else "abs"
            elif k == "qty_str":  # pragma: no cover
                self.logger.warning("`qty_str` is deprecated since v0.7.8. Use `quantity` instead.")
                quantity = kwargs["qty_str"]
            else:  # pragma: no cover
                msg = "{} not valid.".format(k)
                self.logger.error(msg)
                raise TypeError(msg)

        data = self.combine_farfield(phi, theta)
        if quantity not in data:  # pragma: no cover
            self.logger.error("Far field quantity is not available.")
            return False

        ff_data = conversion_function(data[quantity], quantity_format)
        if not isinstance(ff_data, np.ndarray):  # pragma: no cover
            self.logger.error("Format of the quantity is wrong.")
            return False

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
        return plot_3d_chart([x, y, z], xlabel="Theta", ylabel="Phi", title=title, snapshot_path=image_path, show=show)

    # fmt: off
    @pyaedt_function_handler(farfield_quantity="quantity", export_image_path="image_path")
    def polar_plot_3d_pyvista(
            self,
            quantity="RealizedGain",
            quantity_format="dB10",
            rotation=None,
            image_path=None,
            show=True,
            show_as_standalone=False,
            pyvista_object=None,
            background=None,
            scale_farfield=None,
            show_beam_slider=True,
            show_geometry=True,
            **kwargs
    ):
        # fmt: on
        """Create a 3D polar plot of the geometry with a radiation pattern in PyVista.

        Parameters
        ----------
        quantity : str, optional
            Quantity to plot. The default is ``"RealizedGain"``.
            Available quantities are: ``"RealizedGain"``, ``"RealizedGain_Theta"``, ``"RealizedGain_Phi"``,
            ``"rETotal"``, ``"rETheta"``, and ``"rEPhi"``.
        quantity_format : str, optional
            Conversion data function.
            Available functions are: ``"abs"``, ``"ang"``, ``"dB10"``, ``"dB20"``, ``"deg"``, ``"imag"``, ``"norm"``,
            and ``"real"``.
        image_path : str, optional
            Full path for the image file. The default is ``None``, in which case a file is not exported.
        rotation : list, optional
            Far field rotation matrix. The matrix contains three vectors, around x, y, and z axes.
            The default is ``[[1., 0., 0.], [0., 1., 0.], [0., 0., 1.]]``.
        show : bool, optional
            Whether to show the plot. The default is ``True``.
        show_as_standalone : bool, optional
            Whether to show a plot as standalone. The default is ``True``.
        pyvista_object : :class:`Pyvista.Plotter`, optional
            PyVista instance defined externally. The default is ``None``.
        background : list or str, optional
            Background color if a list is passed or background picture if a string is passed.
            The default is ``None``.
        scale_farfield : list, optional
            List with minimum and maximum values of the scale slider. The default is
            ``None``.
        show_beam_slider : bool, optional
            Whether the Theta and Phi scan slider is active. The default is ``True``.
        show_geometry :
            Whether to show the geometry. The default is ``True``.

        Returns
        -------
        bool or :class:`Pyvista.Plotter`
            ``True`` when successful. The :class:`Pyvista.Plotter` is returned when ``show`` and
            ``export_image_path`` are ``False``.

        Examples
        --------
        >>> import pyaedt
        >>> app = pyaedt.Hfss(specified_version="2023.2", designname="Antenna")
        >>> setup_name = "Setup1 : LastAdaptive"
        >>> frequencies = [77e9]
        >>> sphere = "3D"
        >>> data = app.get_antenna_ffd_solution_data(frequencies,setup_name,sphere)
        >>> data.polar_plot_3d_pyvista(quantity_format="dB10",qty_str="RealizedGain")
        """
        for k in kwargs:
            if k == "convert_to_db":  # pragma: no cover
                self.logger.warning("`convert_to_db` is deprecated since v0.7.8. Use `quantity_format` instead.")
                quantity_format = "dB10" if kwargs["convert_to_db"] else "abs"
            elif k == "qty_str":  # pragma: no cover
                self.logger.warning("`qty_str` is deprecated since v0.7.8. Use `quantity` instead.")
                quantity = kwargs["qty_str"]
            else:  # pragma: no cover
                msg = "{} not valid.".format(k)
                self.logger.error(msg)
                raise TypeError(msg)

        if not rotation:
            rotation = np.eye(3)
        elif isinstance(rotation, (list, tuple)):  # pragma: no cover
            rotation = np.array(rotation)
        text_color = "white"
        if background is None:
            background = [255, 255, 255]
            text_color = "black"

        farfield_data = self.combine_farfield(phi_scan=0, theta_scan=0)
        if quantity not in farfield_data:  # pragma: no cover
            self.logger.error("Far field quantity is not available.")
            return False

        self.farfield_data = farfield_data

        self.mesh = self.get_far_field_mesh(quantity=quantity, quantity_format=quantity_format)

        rotation_euler = self._rotation_to_euler_angles(rotation) * 180 / np.pi

        if not image_path and not show:
            off_screen = False
        else:
            off_screen = not show

        if not pyvista_object:
            if show_as_standalone:
                p = pv.Plotter(notebook=False, off_screen=off_screen)
            else:
                p = pv.Plotter(notebook=is_notebook(), off_screen=off_screen)
        else:  # pragma: no cover
            p = pyvista_object

        uf = UpdateBeamForm(self, quantity, quantity_format)

        default_background = [255, 255, 255]
        axes_color = [i / 255 for i in default_background]

        if isinstance(background, list):
            background_color = [i / 255 for i in background]
            p.background_color = background_color
            axes_color = [0 if i >= 128 else 255 for i in background]
        elif isinstance(background, str):  # pragma: no cover
            p.add_background_image(background, scale=2.5)

        if show_beam_slider and self._is_array[self._freq_index]:
            p.add_slider_widget(
                uf.update_phi,
                rng=[0, 360],
                value=0,
                title="Phi",
                pointa=(0.55, 0.1),
                pointb=(0.74, 0.1),
                style="modern",
                interaction_event="always",
                title_height=0.02,
                color=axes_color,
            )
            p.add_slider_widget(
                uf.update_theta,
                rng=[-180, 180],
                value=0,
                title="Theta",
                pointa=(0.77, 0.1),
                pointb=(0.98, 0.1),
                style="modern",
                interaction_event="always",
                title_height=0.02,
                color=axes_color,
            )

        sargs = dict(
            title_font_size=12,
            label_font_size=12,
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
            color=axes_color,
            title=None,
            outline=False,
        )

        cad_mesh = self._get_geometry()
        data = conversion_function(self.farfield_data[quantity], function=quantity_format)
        if not isinstance(data, np.ndarray):  # pragma: no cover
            self.logger.error("Wrong format quantity")
            return False
        max_data = np.max(data)
        min_data = np.min(data)
        ff_mesh_inst = p.add_mesh(uf.output, cmap="jet", clim=[min_data, max_data], scalar_bar_args=sargs)

        if cad_mesh:

            def toggle_vis_ff(flag):
                ff_mesh_inst.SetVisibility(flag)

            def toggle_vis_cad(flag):
                for i in cad:
                    i.SetVisibility(flag)

            def scale(value=1):
                ff_mesh_inst.SetScale(value, value, value)
                sf = AEDT_UNITS["Length"][self.__model_units]
                ff_mesh_inst.SetPosition(np.divide(self.origin, sf))
                ff_mesh_inst.SetOrientation(rotation_euler)

            p.add_checkbox_button_widget(toggle_vis_ff, value=True, size=30)
            p.add_text("Show Far Fields", position=(70, 25), color=text_color, font_size=10)
            if not scale_farfield:
                if self._is_array[self._freq_index]:
                    slider_max = int(
                        np.ceil(np.abs(np.max(self._array_dimension[self._freq_index]) / np.min(np.abs(p.bounds))))
                    )
                else:  # pragma: no cover
                    slider_max = int(np.ceil((np.max(p.bounds) / 2 / np.min(np.abs(p.bounds)))))
                slider_min = 0
            else:
                slider_max = scale_farfield[1]
                slider_min = scale_farfield[0]
            value = slider_max / 3

            p.add_slider_widget(
                scale,
                [slider_min, slider_max],
                title="Scale Plot",
                value=value,
                pointa=(0.7, 0.93),
                pointb=(0.99, 0.93),
                style="modern",
                title_height=0.02,
                color=axes_color,
            )

            cad = []
            for cm in cad_mesh:
                cad.append(p.add_mesh(cm[0], color=cm[1], show_scalar_bar=False, opacity=cm[2]))

            if not show_geometry:
                p.add_checkbox_button_widget(toggle_vis_cad, value=False, position=(10, 70), size=30)
                toggle_vis_cad(False)
            else:
                p.add_checkbox_button_widget(toggle_vis_cad, value=True, position=(10, 70), size=30)

            p.add_text("Show Geometry", position=(70, 75), color=text_color, font_size=10)

        if image_path:
            p.show(screenshot=image_path)
        if show:  # pragma: no cover
            p.show()
        return p

    @pyaedt_function_handler()
    def _init_ffd(self, eep_file_info):
        """Load far field information.

        Parameters
        ----------
        eep_file_info : dict
            Information about the far fields imported.
            The keys of the dictionary represent the port names.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        all_ports = self.all_port_names
        valid_ffd = True

        if os.path.exists(eep_file_info[all_ports[0]][0]):
            with open_file(eep_file_info[all_ports[0]][0], "r") as reader:
                theta = [int(i) for i in reader.readline().split()]
                phi = [int(i) for i in reader.readline().split()]
            reader.close()
            for port in eep_file_info.keys():
                temp_dict = {}
                if ":" in port:
                    port = port.split(":")[0]
                theta_range = np.linspace(*theta)
                phi_range = np.linspace(*phi)
                if os.path.exists(eep_file_info[port][0]):
                    eep_txt = np.loadtxt(eep_file_info[port][0], skiprows=4)
                    Etheta = np.vectorize(complex)(eep_txt[:, 0], eep_txt[:, 1])
                    Ephi = np.vectorize(complex)(eep_txt[:, 2], eep_txt[:, 3])
                    temp_dict["Theta"] = theta_range
                    temp_dict["Phi"] = phi_range
                    temp_dict["rETheta"] = Etheta
                    temp_dict["rEPhi"] = Ephi
                    self._raw_data[port] = temp_dict
                else:
                    valid_ffd = False
        else:
            self.logger.error("Wrong far fields were imported.")
            return False

        if not valid_ffd:
            return False

        return True

    @pyaedt_function_handler(farfield_quantity="quantity")
    def get_far_field_mesh(self, quantity="RealizedGain", quantity_format="dB10", **kwargs):
        """Generate a PyVista ``UnstructuredGrid`` object that represents the far field mesh.

        Parameters
        ----------
        quantity : str, optional
            Far field quantity to plot. The default is ``"RealizedGain"``.
            Available quantities are: ``"RealizedGain"``, ``"RealizedGain_Phi"``, ``"RealizedGain_Theta"``,
            ``"rEPhi"``, ``"rETheta"``, and ``"rETotal"``.
        quantity_format : str, optional
            Conversion data function.
            Available functions are: ``"abs"``, ``"ang"``, ``"dB10"``, ``"dB20"``, ``"deg"``, ``"imag"``, ``"norm"``,
            and ``"real"``.

        Returns
        -------
        :class:`Pyvista.Plotter`
            ``UnstructuredGrid`` object representing the far field mesh.
        """
        for k in kwargs:
            if k == "convert_to_db":  # pragma: no cover
                self.logger.warning("`convert_to_db` is deprecated since v0.7.8. Use `quantity_format` instead.")
                quantity_format = "dB10" if kwargs["convert_to_db"] else "abs"
            else:  # pragma: no cover
                msg = "{} not valid.".format(k)
                self.logger.error(msg)
                raise TypeError(msg)

        if quantity not in self.farfield_data:
            self.logger.error("Far field quantity is not available.")
            return False

        data = self.farfield_data[quantity]

        ff_data = conversion_function(data, quantity_format)

        if not isinstance(ff_data, np.ndarray):  # pragma: no cover
            self.logger.error("Format of the quantity is wrong.")
            return False

        theta = np.deg2rad(np.array(self.farfield_data["Theta"]))
        phi = np.deg2rad(np.array(self.farfield_data["Phi"]))
        mesh = get_structured_mesh(theta=theta, phi=phi, ff_data=ff_data)
        return mesh

    @pyaedt_function_handler()
    def _read_eep_files(self, eep_path):
        """Read the EEP file and populate all attributes with information about each port in the file.

        Parameters
        ----------
        eep_path : str
            Path to the EEP file.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        self._eep_file_info_list.append({})
        if os.path.exists(eep_path):
            with open_file(eep_path, "r") as reader:
                lines = [line.split(None) for line in reader]
            lines = lines[1:]  # remove header
            for pattern in lines:
                if len(pattern) >= 2:
                    port = pattern[0]
                    if ":" in port:
                        port = port.split(":")[0] + "_" + port.split(":")[1]
                    self._eep_file_info_list[-1][port] = [
                        os.path.join(os.path.dirname(eep_path), pattern[1] + ".ffd"),
                        pattern[2],
                        pattern[3],
                        pattern[4],
                    ]
                    self.port_position[port] = [float(pattern[2]), float(pattern[3]), float(pattern[4])]
            return True
        return False

    @pyaedt_function_handler()
    def _get_geometry(self):
        """Get 3D meshes."""
        from pyaedt.generic.plot import ModelPlotter

        eep_file_path = os.path.abspath(self.eep_files[self._freq_index])
        model_info = self.model_info[self._freq_index]
        obj_meshes = []
        if self._is_array[self._freq_index]:
            non_array_geometry = model_info.copy()
            components_info = self._component_objects[self._freq_index]
            array_dimension = self._array_dimension[self._freq_index]
            first_value = next(iter(model_info.values()))
            sf = AEDT_UNITS["Length"][first_value[3]]
            self.__model_units = first_value[3]
            cell_info = self._cell_position[self._freq_index]

            for cell_row in cell_info:
                for cell_col in cell_row:
                    # Initialize an empty mesh for this component
                    model_pv = ModelPlotter()
                    component_name = cell_col[0]
                    component_info = components_info[component_name]
                    rotation = cell_col[2]
                    for component_obj in component_info[1:]:
                        if component_obj in model_info:
                            if component_obj in non_array_geometry:
                                del non_array_geometry[component_obj]

                            cad_path = os.path.join(os.path.dirname(eep_file_path), model_info[component_obj][0])
                            if os.path.exists(cad_path):
                                model_pv.add_object(
                                    cad_path,
                                    model_info[component_obj][1],
                                    model_info[component_obj][2],
                                    model_info[component_obj][3],
                                )

                    model_pv.generate_geometry_mesh()
                    comp_meshes = []
                    row, col = cell_col[3]

                    # Perpendicular lattice vector
                    if self._lattice_vector[self._freq_index][0] != 0:
                        pos_x = (row - 1) * array_dimension[2] - array_dimension[0] / 2 + array_dimension[2] / 2
                        pos_y = (col - 1) * array_dimension[3] - array_dimension[1] / 2 + array_dimension[3] / 2
                    else:
                        pos_y = (row - 1) * array_dimension[2] - array_dimension[0] / 2 + array_dimension[2] / 2
                        pos_x = (col - 1) * array_dimension[3] - array_dimension[1] / 2 + array_dimension[3] / 2

                    for obj in model_pv.objects:
                        mesh = obj._cached_polydata
                        translated_mesh = mesh.copy()
                        color_cad = [i / 255 for i in obj.color]

                        translated_mesh.translate(
                            [-component_info[0][0] / sf, -component_info[0][1] / sf, -component_info[0][2] / sf],
                            inplace=True,
                        )

                        if rotation != 0:
                            translated_mesh.rotate_z(rotation, inplace=True)

                        # Translate the mesh to its position
                        translated_mesh.translate([pos_x / sf, pos_y / sf, component_info[0][2] / sf], inplace=True)

                        comp_meshes.append([translated_mesh, color_cad, obj.opacity])

                    obj_meshes.append(comp_meshes)

            obj_meshes = [item for sublist in obj_meshes for item in sublist]
        else:
            non_array_geometry = model_info

        if non_array_geometry:  # pragma: no cover
            model_pv = ModelPlotter()
            first_value = next(iter(non_array_geometry.values()))
            sf = AEDT_UNITS["Length"][first_value[3]]

            model_pv.off_screen = True
            for object_in in non_array_geometry.values():
                cad_path = os.path.join(os.path.dirname(eep_file_path), object_in[0])
                if os.path.exists(cad_path):
                    model_pv.add_object(
                        cad_path,
                        object_in[1],
                        object_in[2],
                        object_in[3],
                    )
                else:
                    self.logger.warning("Geometry objects are not defined.")
                    return False
            self.__model_units = first_value[3]
            model_pv.generate_geometry_mesh()
            i = 0
            for obj in model_pv.objects:
                mesh = obj._cached_polydata
                translated_mesh = mesh.copy()
                color_cad = [i / 255 for i in obj.color]

                if len(obj_meshes) > i:
                    obj_meshes[i][0] += translated_mesh
                else:
                    obj_meshes.append([translated_mesh, color_cad, obj.opacity])
                i += 1

        return obj_meshes

    @pyaedt_function_handler()
    def _get_port_index(self, port_name=None):
        """Get index of a given port.

        Parameters
        ----------
        port_name : str or list
            Port name or a list of port names.

        Returns
        -------
        list
            Element index.
        """
        port_index = {}

        if not port_name:
            port_name = self.all_port_names
        elif isinstance(port_name, str):
            port_name = [port_name]

        index_offset = 0
        if self._is_array[self._freq_index]:
            port = port_name[0]
            first_index = port.split("[", 1)[1].split("]", 1)[0]
            if first_index[0] != "1":
                index_offset = int(float(first_index[0])) - 1

        for port in port_name:
            if self._is_array[self._freq_index]:
                try:
                    str1 = port.split("[", 1)[1].split("]", 1)[0]
                    port_index[port] = [int(i) - index_offset for i in str1.split(",")]
                except Exception:
                    return False
            else:
                if not port_index:
                    port_index[port] = [1, 1]
                else:
                    last_value = list(port_index.values())[-1]
                    port_index[port] = [1, last_value[1] + 1]

        return port_index

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


class FfdSolutionDataExporter(FfdSolutionData):
    """Class to enable export of embedded element pattern data from HFSS.

    An instance of this class is returned from the
    :meth:`pyaedt.Hfss.get_antenna_ffd_solution_data` method. This method allows creation of
    the embedded
    element pattern (EEP) files for an antenna array that have been solved in HFSS. The
    ``frequencies`` and ``eep_files`` properties can then be passed as arguments to
    instantiate an instance of the :class:`pyaedt.modules.solutions.FfdSolutionData` class for
    subsequent analysis and postprocessing of the array data.

    Note that this class is derived from the :class:`FfdSolutionData` class and can be used directly for
    far-field postprocessing and array analysis, but it remains a property of the
    :class:`pyaedt.Hfss` application.

    Parameters
    ----------
    app : :class:`pyaedt.Hfss`
        HFSS application instance.
    sphere_name : str
        Infinite sphere to use.
    setup_name : str
        Name of the setup. Make sure to build a setup string in the form of ``"SetupName : SetupSweep"``.
    frequencies : list
        Frequency list to export. Specify either a list of strings with units or a list of floats in Hertz units.
        For example, ``["9GHz", 9e9]``.
    variations : dict, optional
        Dictionary of all families including the primary sweep. The default value is ``None``.
    overwrite : bool, optional
        Whether to overwrite the existing far field solution data. The default is ``True``.

    Examples
    --------
    >>> import pyaedt
    >>> app = pyaedt.Hfss(specified_version="2023.2", designname="Antenna")
    >>> setup_name = "Setup1 : LastAdaptive"
    >>> frequencies = [77e9]
    >>> sphere = "3D"
    >>> data = app.get_antenna_ffd_solution_data(frequencies,setup_name,sphere)
    >>> data.polar_plot_3d_pyvista(quantity_format="dB10",qty_str="rETotal")
    """

    def __init__(
        self,
        app,
        sphere_name,
        setup_name,
        frequencies,
        variations=None,
        overwrite=True,
    ):
        self._app = app
        self.sphere_name = sphere_name
        self.setup_name = setup_name
        if not isinstance(frequencies, list):
            self.frequencies = [frequencies]
        else:
            self.frequencies = frequencies
        self.variations = variations
        self.overwrite = overwrite
        self.model_info = []
        if self._app.desktop_class.is_grpc_api:
            self._app.set_phase_center_per_port()
        else:
            self._app.logger.warning("Set phase center in port location manually.")
        eep_files = self._export_all_ffd()
        FfdSolutionData.__init__(self, eep_files, self.frequencies)

    @pyaedt_function_handler()
    def _export_all_ffd(self):
        """Export far field solution data of each port."""
        exported_name_base = "eep"
        exported_name_map = exported_name_base + ".txt"
        sol_setup_name_str = self.setup_name.replace(":", "_").replace(" ", "")
        path_dict = []
        for frequency in self.frequencies:
            full_setup_str = "{}-{}-{}".format(sol_setup_name_str, self.sphere_name, frequency)
            export_path = "{}/{}/eep/".format(self._app.working_directory, full_setup_str)
            if settings.remote_rpc_session:
                settings.remote_rpc_session.filemanager.makedirs(export_path)
                file_exists = settings.remote_rpc_session.filemanager.pathexists(export_path + exported_name_map)
            elif not os.path.exists(export_path):
                os.makedirs(export_path)
                file_exists = False
            else:
                file_exists = os.path.exists(export_path + exported_name_map)
            time_before = time.time()
            if self.overwrite or not file_exists:
                self._app.logger.info("Exporting embedded element patterns...")
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
                except Exception:
                    self._app.logger.error("Failed to export one element pattern.")
                    self._app.logger.error(export_path + exported_name_base + ".ffd")

            else:
                self._app.logger.info("Using Existing Embedded Element Patterns")
            local_path = "{}/{}/eep/".format(settings.remote_rpc_session_temp_folder, full_setup_str)
            export_path = check_and_download_folder(local_path, export_path)
            if os.path.exists(os.path.join(export_path, exported_name_map)):
                geometry_path = os.path.join(export_path, "geometry")
                if not os.path.exists(geometry_path):
                    os.mkdir(geometry_path)

                path_dict.append(os.path.join(export_path, exported_name_map))
                metadata_file_name = os.path.join(export_path, "eep.json")
                items = {"variation": self._app.odesign.GetNominalVariation(), "frequency": frequency}

                obj_list = self._create_geometries(geometry_path)
                if obj_list:
                    items["model_info"] = obj_list
                    self.model_info.append(obj_list)

                if self._app.component_array:
                    component_array = self._app.component_array[self._app.component_array_names[0]]
                    items["component_objects"] = component_array.get_component_objects()
                    items["cell_position"] = component_array.get_cell_position()
                    items["array_dimension"] = [
                        component_array.a_length,
                        component_array.b_length,
                        component_array.a_length / component_array.a_size,
                        component_array.b_length / component_array.b_size,
                    ]
                    items["lattice_vector"] = component_array.lattice_vector()

                with open_file(metadata_file_name, "w") as f:
                    json.dump(items, f, indent=2)
        elapsed_time = time.time() - time_before
        self._app.logger.info("Exporting embedded element patterns.... Done: %s seconds", elapsed_time)
        return path_dict

    @pyaedt_function_handler()
    def _create_geometries(self, export_path):
        """Export the geometry in OBJ format."""
        self._app.logger.info("Exporting geometry...")
        model_pv = self._app.post.get_model_plotter_geometries(plot_air_objects=False)
        obj_list = {}
        for obj in model_pv.objects:
            object_name = os.path.basename(obj.path)
            name = os.path.splitext(object_name)[0]
            original_path = os.path.dirname(obj.path)
            new_path = os.path.join(os.path.abspath(export_path), object_name)

            if not os.path.exists(new_path):
                new_path = shutil.move(obj.path, export_path)
            if os.path.exists(os.path.join(original_path, name + ".mtl")):
                try:
                    os.remove(os.path.join(original_path, name + ".mtl"))
                except SystemExit:
                    self.logger.warning("File cannot be removed.")
            obj_list[obj.name] = [
                os.path.join(os.path.basename(export_path), object_name),
                obj.color,
                obj.opacity,
                obj.units,
            ]
        return obj_list


class UpdateBeamForm:
    """Provides for updating far field data.

    This class is used to interact with the far field Theta and Phi scan.

    Parameters
    ----------
    ff : :class:`pyaedt.modules.solutions.FfdSolutionData`
        Far field solution data instance.
    farfield_quantity : str, optional
        Quantity to plot. The default is ``"RealizedGain"``.
        Available quantities are: ``"RealizedGain"``, ``"RealizedGain_Phi"``, ``"RealizedGain_Theta"``,
        ``"rEPhi"``, ``"rETheta"``, and ``"rETotal"``.
    quantity_format : str, optional
        Conversion data function.
        Available functions are: ``"abs"``, ``"ang"``, ``"dB10"``, ``"dB20"``, ``"deg"``, ``"imag"``, ``"norm"``,
            and ``"real"``.
    """

    @pyaedt_function_handler(farfield_quantity="quantity")
    def __init__(self, ff, farfield_quantity="RealizedGain", quantity_format="abs"):
        self.output = ff.mesh
        self._phi = 0
        self._theta = 0
        # default parameters
        self.ff = ff
        self.quantity = farfield_quantity
        self.quantity_format = quantity_format

    @pyaedt_function_handler()
    def _update_both(self):
        """Update far field."""
        self.ff.farfield_data = self.ff.combine_farfield(phi_scan=self._phi, theta_scan=self._theta)

        self.ff.mesh = self.ff.get_far_field_mesh(self.quantity, self.quantity_format)

        self.output.copy_from(self.ff.mesh)
        return

    @pyaedt_function_handler()
    def update_phi(self, phi):
        """Update the Phi value."""
        self._phi = phi
        self._update_both()

    @pyaedt_function_handler()
    def update_theta(self, theta):
        """Update the Theta value."""
        self._theta = theta
        self._update_both()


class FieldPlot:
    """Provides for creating and editing field plots.

    Parameters
    ----------
    postprocessor : :class:`pyaedt.modules.PostProcessor.PostProcessor`
    objects : list
        List of objects.
    solution : str
        Name of the solution.
    quantity : str
        Name of the plot or the name of the object.
    intrinsics : dict, optional
        Name of the intrinsic dictionary. The default is ``{}``.

    """

    @pyaedt_function_handler(
        objlist="objects",
        surfacelist="surfaces",
        linelist="lines",
        cutplanelist="cutplanes",
        solutionName="solution",
        quantityName="quantity",
        IntrinsincList="intrinsics",
        seedingFaces="seeding_faces",
        layers_nets="layer_nets",
        layers_plot_type="layer_plot_type",
    )
    def __init__(
        self,
        postprocessor,
        objects=[],
        surfaces=[],
        lines=[],
        cutplanes=[],
        solution="",
        quantity="",
        intrinsics={},
        seeding_faces=[],
        layer_nets=[],
        layer_plot_type="LayerNetsExtFace",
    ):
        self._postprocessor = postprocessor
        self.oField = postprocessor.ofieldsreporter
        self.volumes = objects
        self.surfaces = surfaces
        self.lines = lines
        self.cutplanes = cutplanes
        self.layer_nets = layer_nets
        self.layer_plot_type = layer_plot_type
        self.seeding_faces = seeding_faces
        self.solution = solution
        self.quantity = quantity
        self.intrinsics = intrinsics
        self.name = "Field_Plot"
        self.plot_folder = "Field_Plot"
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
        if self.volumes:
            idx += 1
        if self.surfaces:
            idx += 1
        if self.cutplanes:
            idx += 1
        if self.lines:
            idx += 1
        if self.layer_nets:
            idx += 1

        info = [idx]
        if self.volumes:
            info.append("Volume")
            info.append("ObjList")
            info.append(len(self.volumes))
            for index in self.volumes:
                info.append(str(index))
        if self.surfaces:
            model_faces = []
            nonmodel_faces = []
            if self._postprocessor._app.design_type == "HFSS 3D Layout Design":
                model_faces = [str(i) for i in self.surfaces]
            else:
                models = self._postprocessor.modeler.model_objects
                for index in self.surfaces:
                    try:
                        if isinstance(index, FacePrimitive):
                            index = index.id
                        oname = self._postprocessor.modeler.oeditor.GetObjectNameByFaceID(index)
                        if oname in models:
                            model_faces.append(str(index))
                        else:
                            nonmodel_faces.append(str(index))
                    except Exception:
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
        if self.cutplanes:
            info.append("Surface")
            info.append("CutPlane")
            info.append(len(self.cutplanes))
            for index in self.cutplanes:
                info.append(str(index))
        if self.lines:
            info.append("Line")
            info.append(len(self.lines))
            for index in self.lines:
                info.append(str(index))
        if self.layer_nets:
            if self.layer_plot_type == "LayerNets":
                info.append("Volume")
                info.append("LayerNets")
            else:
                info.append("Surface")
                info.append("LayerNetsExtFace")
            info.append(len(self.layer_nets))
            for index in self.layer_nets:
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

    @property
    def plotsettings(self):
        """Plot settings.

        Returns
        -------
        list
            List of plot settings.
        """
        if self.surfaces or self.cutplanes or (self.layer_nets and self.layer_plot_type == "LayerNetsExtFace"):
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
        elif self.lines:
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
            self.solution,
            "QuantityName:=",
            self.quantity,
            "PlotFolder:=",
            self.plot_folder,
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
                "SurfaceOnly:=",
                True if self.surfaces or self.cutplanes else False,
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
            self.solution,
            "UserSpecifyName:=",
            0,
            "UserSpecifyFolder:=",
            0,
            "QuantityName:=",
            "QuantityName_FieldLineTrace",
            "PlotFolder:=",
            self.plot_folder,
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
                self.surfaces,
                "Volume Tracing Objects:=",
                self.volumes,
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
            if (
                "Maxwell" in self._postprocessor._app.design_type
                and "Transient" in self._postprocessor.post_solution_type
            ):
                self._postprocessor.ofieldsreporter.SetPlotsViewSolutionContext(
                    [self.name], self.solution, "Time:" + self.intrinsics["Time"]
                )
            self._postprocessor.field_plots[self.name] = self
            return True
        except Exception:
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
                if self.volumes[0] != len(self.volumes) - 1:
                    for obj in self.volumes[1:]:
                        if not isinstance(obj, int):
                            self._postprocessor.logger.error("Provide valid object id for in-volume object.")
                            return False
                        else:
                            if obj not in list(self._postprocessor._app.modeler.objects.keys()):
                                self._postprocessor.logger.error("Invalid object id.")
                                self.volumes.remove(obj)
                                return False
                    self.volumes[0] = len(self.volumes) - 1
                if self.surfaces[0] != len(self.surfaces) - 1:
                    for obj in self.surfaces[1:]:
                        if not isinstance(obj, int):
                            self._postprocessor.logger.error("Provide valid object id for surface object.")
                            return False
                        else:
                            if obj not in list(self._postprocessor._app.modeler.objects.keys()):
                                self._postprocessor.logger.error("Invalid object id.")
                                self.surfaces.remove(obj)
                                return False
                    self.surfaces[0] = len(self.surfaces) - 1
                self.oField.ModifyFieldPlot(self.name, self.surfacePlotInstructionLineTraces)
            else:
                self.oField.ModifyFieldPlot(self.name, self.surfacePlotInstruction)
            return True
        except Exception:
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
            ``True`` when successful, ``False`` when failed.

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
        self.oField.SetPlotFolderSettings(self.plot_folder, args)
        return True

    @pyaedt_function_handler()
    def export_image(
        self,
        full_path=None,
        width=1920,
        height=1080,
        orientation="isometric",
        display_wireframe=True,
        selections=None,
        show_region=True,
        show_axis=True,
        show_grid=True,
        show_ruler=True,
    ):
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
            Whether the objects has to be put in wireframe mode. Default is ``True``.
        selections : str or List[str], optional
            Objects to fit for the zoom on the exported image.
            Default is None in which case all the objects in the design will be shown.
            One important note is that, if the fieldplot extension is larger than the
            selection extension, the fieldplot extension will be the one considered
            for the zoom of the exported image.
        show_region : bool, optional
            Whether to include the air region in the exported image. Default is ``True``.
        show_grid : bool, optional
            Whether to display the background grid in the exported image.
            Default is ``True``.
        show_axis : bool, optional
            Whether to display the axis triad in the exported image. Default is ``True``.
        show_ruler : bool, optional
            Whether to display the ruler in the exported image. Default is ``True``.

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
        self.oField.UpdateQuantityFieldsPlots(self.plot_folder)
        if not full_path:
            full_path = os.path.join(self._postprocessor._app.working_directory, self.name + ".png")
        status = self._postprocessor.export_field_jpg(
            full_path,
            self.name,
            self.plot_folder,
            orientation=orientation,
            width=width,
            height=height,
            display_wireframe=display_wireframe,
            selections=selections,
            show_region=show_region,
            show_axis=show_axis,
            show_grid=show_grid,
            show_ruler=show_ruler,
        )
        full_path = check_and_download_file(full_path)
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
                plot_label=self.quantity,
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
    quantity : str, optional
        Name of the plot or the name of the object.
    max_frequency : str, optional
        Maximum Frequency. The default is ``"1GHz"``.
    ray_density : int, optional
        Ray Density. The default is ``2``.
    bounces : int, optional
        Maximum number of bounces. The default is ``5``.
    intrinsics : dict, optional
        Name of the intrinsic dictionary. The default is ``{}``.

    """

    @pyaedt_function_handler(quantity_name="quantity")
    def __init__(
        self,
        postprocessor,
        is_creeping_wave=False,
        quantity="QuantityName_SBR",
        max_frequency="1GHz",
        ray_density=2,
        bounces=5,
        intrinsics={},
    ):
        self.is_creeping_wave = is_creeping_wave
        self._postprocessor = postprocessor
        self._ofield = postprocessor.ofieldsreporter
        self.quantity = quantity
        self.intrinsics = intrinsics
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
            self.quantity,
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
                box_id = self._postprocessor._primitives.objects[self.ray_box].id
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
            self.quantity,
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
        except Exception:
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
        except Exception:
            return False

    @pyaedt_function_handler()
    def delete(self):
        """Delete the field plot."""
        self._ofield.DeleteFieldPlot([self.name])
        return True

    @pyaedt_function_handler(path_to_hdm_file="path")
    def export(self, path=None):
        """Export the Visual Ray Tracing to ``hdm`` file.

        Parameters
        ----------
        path : str, optional
            Full path to the output file. The default is ``None``, in which case the file is
            exported to the working directory.

        Returns
        -------
        str
            Path to the file.
        """
        if not path:
            path = os.path.join(self._postprocessor._app.working_directory, self.name + ".hdm")
        self._ofield.ExportFieldPlot(self.name, False, path)
        return path
