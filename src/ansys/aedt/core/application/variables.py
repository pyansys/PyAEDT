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

"""
This module contains these classes: `CSVDataset`, `DataSet`, `Expression`, `Variable`, and `VariableManager`.

This module is used to create and edit design and project variables in the 3D tools.

Examples
--------
>>> from ansys.aedt.core import Hfss
>>> hfss = Hfss()
>>> hfss["$d"] = "5mm"
>>> hfss["d"] = "5mm"
>>> hfss["postd"] = "1W"

"""

from __future__ import absolute_import  # noreorder
from __future__ import division

import ast
import os
import re
import types
import warnings

from ansys.aedt.core.generic.constants import AEDT_UNITS
from ansys.aedt.core.generic.constants import SI_UNITS
from ansys.aedt.core.generic.constants import _resolve_unit_system
from ansys.aedt.core.generic.constants import unit_system
from ansys.aedt.core.generic.errors import GrpcApiError
from ansys.aedt.core.generic.general_methods import check_numeric_equivalence
from ansys.aedt.core.generic.general_methods import open_file
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.generic.numbers import Quantity
from ansys.aedt.core.generic.numbers import decompose_variable_value
from ansys.aedt.core.generic.numbers import is_array
from ansys.aedt.core.generic.numbers import is_number


class CSVDataset:
    """Reads in a CSV file and extracts data, which can be augmented with constant values.

    Parameters
    ----------
    csv_file : str, optional
        Input file consisting of delimited data with the first line as the header.
        The CSV value includes the header and data, which supports AEDT units information
        such as ``"1.23Wb"``. You can also augment the data with constant values.
    separator : str, optional
        Value to use for the delimiter. The default is``None`` in which case a comma is
        assumed.
    units_dict : dict, optional
        Dictionary consisting of ``{Variable Name: unit}`` to rescale the data
        if it is not in the desired unit system.
    append_dict : dict, optional
        Dictionary consisting of ``{New Variable Name: value}`` to add variables
        with constant values to all data points. This dictionary is used to add
        multiple sweeps to one result file.
    valid_solutions : bool, optional
        The default is ``True``.
    invalid_solutions : bool, optional
        The default is ``False``.

    """

    @property
    def number_of_rows(self):
        """Number of rows."""
        if self._data:
            for variable, data_list in self._data.items():
                return len(data_list)
        else:
            return 0

    @property
    def number_of_columns(self):
        """Number of columns."""
        return len(self._header)

    @property
    def header(self):
        """Header."""
        return self._header

    @property
    def data(self):
        """Data."""
        return self._data

    @property
    def path(self):
        """Path."""
        return os.path.dirname(os.path.realpath(self._csv_file))

    def __init__(
        self,
        csv_file=None,
        separator=None,
        units_dict=None,
        append_dict=None,
        valid_solutions=True,
        invalid_solutions=False,
    ):
        self._header = []
        self._data = {}
        self._unit_dict = {}
        self._append_dict = {}

        # Set the index counter explicitly to zero
        self._index = 0

        if separator:
            self._separator = separator
        else:
            self._separator = ","

        if units_dict:
            self._unit_dict = units_dict

        if append_dict:
            self._append_dict = append_dict

        self._csv_file = csv_file
        if csv_file:
            with open_file(csv_file, "r") as fi:
                file_data = fi.readlines()
                for line in file_data:
                    if self._header:
                        line_data = line.strip().split(self._separator)
                        # Check for invalid data in the line (fields with 'nan')
                        if "nan" not in line_data:
                            for j, value in enumerate(line_data):
                                var_name = self._header[j]
                                if var_name in self._unit_dict:
                                    var_value = Variable(value).rescale_to(self._unit_dict[var_name]).numeric_value
                                else:
                                    var_value = Variable(value).value
                                self._data[var_name].append(var_value)

                            # Add augmented quantities
                            for entry in self._append_dict:
                                var_value_str = self._append_dict[entry]
                                numeric_value = Variable(var_value_str).numeric_value
                                self._data[entry].append(numeric_value)

                    else:
                        self._header = line.strip().split(",")
                        for additional_quantity_name in self._append_dict:
                            self._header.append(additional_quantity_name)
                        for quantity_name in self._header:
                            self._data[quantity_name] = []

    @pyaedt_function_handler()
    def __getitem__(self, item):
        variable_list = item.split(",")
        data_out = CSVDataset()
        for variable in variable_list:
            found_variable = False
            for key_string in self._data:
                if variable in key_string:
                    found_variable = True
                    break
            if not found_variable:
                raise KeyError(f"Input string {variable} is not a key of the data dictionary.")
            data_out._data[variable] = self._data[key_string]
            data_out._header.append(variable)
        return data_out

    @pyaedt_function_handler()
    def __add__(self, other):
        if self.number_of_columns != other.number_of_columns:
            raise ValueError("Number of columns is inconsistent.")

        # Create a new object to return, avoiding changing the original inputs
        new_dataset = CSVDataset()
        # Add empty columns to new_dataset
        for column in self._data:
            new_dataset._data[column] = []

        # Add the data from 'self' to a the new dataset
        for column, row_data in self.data.items():
            for value in row_data:
                new_dataset._data[column].append(value)

        # Add the data from 'other' to a the new dataset
        for column, row_data in other.data.items():
            for value in row_data:
                new_dataset._data[column].append(value)

        return new_dataset

    def __iadd__(self, other):
        """Incrementally add the dataset in one CSV file to a dataset in another CSV file.

        .. note:
           This assumes that the number of columns in both datasets are the same,
           or that one of the datasets is empty. No checking is done for
           equivalency of units or variable names.

        """

        # Handle the case of an empty data set and create empty lists for the column data
        if self.number_of_columns == 0:
            self._header = other.header
            for column in other.data:
                self._data[column] = []

        if self.number_of_columns != other.number_of_columns:
            raise ValueError("Number of columns is inconsistent.")

        # Append the data from 'other'
        for column, row_data in other.data.items():
            for value in row_data:
                self._data[column].append(value)

        return self

    # Called when iteration is initialized
    def __iter__(self):
        self._index = 0
        return self

    # Create an iterator to yield the row data as a string as we loop through the object
    def __next__(self):
        if self._index < (self.number_of_rows - 1):
            output = []
            for column in self._header:
                evaluated_value = str(self._data[column][self._index])
                output.append(evaluated_value)
            output_string = " ".join(output)
            self._index += 1
        else:
            raise StopIteration

        return output_string

    def next(self):
        """Yield the next row."""
        return self.__next__()


@pyaedt_function_handler()
def _generate_property_validation_errors(property_name, expected, actual):
    expected_value, expected_unit = decompose_variable_value(expected)
    actual_value, actual_unit = decompose_variable_value(actual)

    if isinstance(expected_value, (float, int)) and isinstance(actual_value, (float, int)):
        if not check_numeric_equivalence(expected_value, actual_value, 1e-9):
            yield f"Value Error {property_name}: Expected {expected}, got {actual}"
        if expected_unit != actual_unit:
            yield f"Unit Error {property_name}: Expected {expected_unit}, got {actual_unit}"
    else:
        if expected != actual:
            yield f"Error {property_name}: Expected {expected}, got {actual}"


@pyaedt_function_handler()
def generate_validation_errors(property_names, expected_settings, actual_settings):
    """From the given property names, expected settings and actual settings, return a list of validation errors.

    If no errors are found, an empty list is returned. The validation of values such as "10mm"
    ensures that they are close to within a relative tolerance.
    For example an expected setting of "10mm", and actual of "10.000000001mm" will not yield a validation error.
    For values with no numerical value, an equivalence check is made.

    Parameters
    ----------
    property_names : List[str]
        List of property names.
    expected_settings : List[str]
        List of the expected settings.
    actual_settings : List[str]
        List of actual settings.

    Returns
    -------
    List[str]
        A list of validation errors for the given settings.
    """
    validation_errors = [
        error
        for property_name, expected, actual in zip(property_names, expected_settings, actual_settings)
        for error in _generate_property_validation_errors(property_name, expected, actual)
    ]
    return validation_errors


class VariableManager(object):
    """Manages design properties and project variables.

    Design properties are the local variables in a design. Project
    variables are defined at the project level and start with ``$``.

    This class provides access to all variables or a subset of the
    variables. Manipulation of the numerical or string definitions of
    variable values is provided in the
    :class:`ansys.aedt.core.application.variables.Variable` class.

    Parameters
    ----------
    variables : dict
        Dictionary of all design properties and project variables in
        the active design.
    design_variables : dict
        Dictionary of all design properties in the active design.
    project_variables : dict
        Dictionary of all project variables available to the active
        design (key by variable name).
    dependent_variables : dict
        Dictionary of all dependent variables available to the active
        design (key by variable name).
    independent_variables : dict
       Dictionary of all independent variables (constant numeric
       values) available to the active design (key by variable name).
    independent_design_variables : dict

    independent_project_variables : dict

    variable_names : str or list
        One or more variable names.
    project_variable_names : str or list
        One or more project variable names.
    design_variable_names : str or list
        One or more design variable names.
    dependent_variable_names : str or list
        All dependent variable names within the project.
    independent_variable_names : list of str
        All independent variable names within the project. These can
        be sweep variables for optimetrics.
    independent_project_variable_names : str or list
        All independent project variable names within the
        project. These can be sweep variables for optimetrics.
    independent_design_variable_names : str or list
        All independent design properties (local variables) within the
        project. These can be sweep variables for optimetrics.

    See Also
    --------
    ansys.aedt.core.application.variables.Variable

    Examples
    --------

    >>> from ansys.aedt.core.maxwell import Maxwell3d
    >>> from ansys.aedt.core.desktop import Desktop
    >>> d = Desktop()
    >>> aedtapp = Maxwell3d()

    Define some test variables.

    >>> aedtapp["Var1"] = 3
    >>> aedtapp["Var2"] = "12deg"
    >>> aedtapp["Var3"] = "Var1 * Var2"
    >>> aedtapp["$PrjVar1"] = "pi"

    Get the variable manager for the active design.

    >>> v = aedtapp.variable_manager

    Get a dictionary of all project and design variables.

    >>> v.variables
    {'Var1': <ansys.aedt.core.application.variables.Variable at 0x2661f34c448>,
     'Var2': <ansys.aedt.core.application.variables.Variable at 0x2661f34c308>,
     'Var3': <ansys.aedt.core.application.variables.Expression at 0x2661f34cb48>,
     '$PrjVar1': <ansys.aedt.core.application.variables.Expression at 0x2661f34cc48>}

    Get a dictionary of only the design variables.

    >>> v.design_variables
    {'Var1': <ansys.aedt.core.application.variables.Variable at 0x2661f339508>,
     'Var2': <ansys.aedt.core.application.variables.Variable at 0x2661f3415c8>,
     'Var3': <ansys.aedt.core.application.variables.Expression at 0x2661f341808>}

    Get a dictionary of only the independent design variables.

    >>> v.independent_design_variables
    {'Var1': <ansys.aedt.core.application.variables.Variable at 0x2661f335d08>,
     'Var2': <ansys.aedt.core.application.variables.Variable at 0x2661f3557c8>}

    """

    @property
    def variables(self):
        """Variables.

        Returns
        -------

        dict[str, :class:`ansys.aedt.core.application.variables.Variable`]
            Dictionary of the `Variable` objects for each project variable and each
            design property in the active design.


        References
        ----------
        >>> oProject.GetVariables
        >>> oDesign.GetVariables
        >>> oProject.GetChildObject("Variables").GetChildNames
        >>> oDesign.GetChildObject("Variables").GetChildNames
        """
        return self._variable_dict([self._odesign, self._oproject])

    @pyaedt_function_handler(variable_value="variable")
    def decompose(self, variable):
        """Decompose a variable string to a floating with its unit.

        Parameters
        ----------
        variable : str

        Returns
        -------
        tuple
            The float value of the variable and the units exposed as a string.

        Examples
        --------
        >>> hfss = Hfss()
        >>> print(hfss.variable_manager.decompose("5mm"))
        >>> (5.0, 'mm')
        >>> hfss["v1"] = "3N"
        >>> print(hfss.variable_manager.decompose("v1"))
        >>> (3.0, 'N')
        >>> hfss["v2"] = "2*v1"
        >>> print(hfss.variable_manager.decompose("v2"))
        >>> (6.0, 'N')
        """
        if variable in self.independent_variable_names:
            val, unit = decompose_variable_value(self[variable].expression)
        elif variable in self.dependent_variable_names:
            val, unit = decompose_variable_value(self[variable].evaluated_value)
        else:
            val, unit = decompose_variable_value(variable)
        return val, unit

    @property
    def design_variables(self):
        """Design variables.

        Returns
        -------
        dict
            Dictionary of the design properties (local properties) in the design.

        References
        ----------
        >>> oDesign.GetVariables
        >>> oDesign.GetChildObject("Variables").GetChildNames
        """
        return self._variable_dict([self._odesign])

    @property
    def project_variables(self):
        """Project variables.

        Returns
        -------
        dict
            Dictionary of the project properties.

        References
        ----------
        >>> oProject.GetVariables
        >>> oProject.GetChildObject("Variables").GetChildNames
        """
        return self._variable_dict([self._oproject])

    @property
    def post_processing_variables(self):
        """Post Processing variables.

        Returns
        -------
        dict
            Dictionary of the post processing variables (constant numeric
            values) available to the design.

        References
        ----------
        >>> oProject.GetVariables
        >>> oDesign.GetVariables
        >>> oProject.GetChildObject("Variables").GetChildNames
        >>> oDesign.GetChildObject("Variables").GetChildNames
        """
        try:
            all_post_vars = list(self._odesign.GetPostProcessingVariables())
        except Exception:
            all_post_vars = []
        out = self.design_variables
        post_vars = {}
        for k, v in out.items():
            if k in all_post_vars:
                post_vars[k] = v
        return post_vars

    @property
    def independent_variables(self):
        """Independent variables.

        Returns
        -------
        dict
            Dictionary of the independent variables (constant numeric
            values) available to the design.

        References
        ----------
        >>> oProject.GetVariables
        >>> oDesign.GetVariables
        >>> oProject.GetChildObject("Variables").GetChildNames
        >>> oDesign.GetChildObject("Variables").GetChildNames
        """
        return self._variable_dict([self._odesign, self._oproject], dependent=False)

    @property
    def independent_project_variables(self):
        """Independent project variables.

        Returns
        -------
        dict
            Dictionary of the independent project variables available to the design.

        References
        ----------
        >>> oProject.GetVariables
        >>> oProject.GetChildObject("Variables").GetChildNames
        """
        return self._variable_dict([self._oproject], dependent=False)

    @property
    def independent_design_variables(self):
        """Independent design variables.

        Returns
        -------
        dict
            Dictionary of the independent design properties (local
            variables) available to the design.

        References
        ----------
        >>> oDesign.GetVariables
        >>> oDesign.GetChildObject("Variables").GetChildNames
        """
        return self._variable_dict([self._odesign], dependent=False)

    @property
    def dependent_variables(self):
        """Dependent variables.

        Returns
        -------
        dict
            Dictionary of the dependent design properties (local
            variables) and project variables available to the design.

        References
        ----------
        >>> oProject.GetVariables
        >>> oDesign.GetVariables
        >>> oProject.GetChildObject("Variables").GetChildNames
        >>> oDesign.GetChildObject("Variables").GetChildNames
        """
        return self._variable_dict([self._odesign, self._oproject], independent=False)

    @property
    def dependent_project_variables(self):
        """Dependent project variables.

        Returns
        -------
        dict
            Dictionary of the dependent project variables available to the design.

        References
        ----------
        >>> oProject.GetVariables
        >>> oProject.GetChildObject("Variables").GetChildNames
        """
        return self._variable_dict([self._oproject], independent=False)

    @property
    def dependent_design_variables(self):
        """Dependent design variables.

        Returns
        -------
        dict
            Dictionary of the dependent design properties (local
            variables) available to the design.

        References
        ----------
        >>> oDesign.GetVariables
        >>> oDesign.GetChildObject("Variables").GetChildNames
        """
        return self._variable_dict([self._odesign], independent=False)

    @property
    def variable_names(self):
        """List of variables."""
        return [var_name for var_name in self.variables]

    @property
    def project_variable_names(self):
        """List of project variables.

        References
        ----------
        >>> oProject.GetVariables
        >>> oProject.GetChildObject("Variables").GetChildNames
        """
        return [var_name for var_name in self.project_variables]

    @property
    def design_variable_names(self):
        """List of design variables.

        References
        ----------
        >>> oDesign.GetVariables
        >>> oDesign.GetChildObject("Variables").GetChildNames"""
        return [var_name for var_name in self.design_variables]

    @property
    def independent_project_variable_names(self):
        """List of independent project variables.

        References
        ----------
        >>> oProject.GetVariables
        >>> oProject.GetChildObject("Variables").GetChildNames
        """
        return [var_name for var_name in self.independent_project_variables]

    @property
    def independent_design_variable_names(self):
        """List of independent design variables.

        References
        ----------
        >>> oDesign.GetVariables
        >>> oDesign.GetChildObject("Variables").GetChildNames"""
        return [var_name for var_name in self.independent_design_variables]

    @property
    def independent_variable_names(self):
        """List of independent variables.

        References
        ----------
        >>> oProject.GetVariables
        >>> oDesign.GetVariables
        >>> oProject.GetChildObject("Variables").GetChildNames
        >>> oDesign.GetChildObject("Variables").GetChildNames"""
        return [var_name for var_name in self.independent_variables]

    @property
    def dependent_project_variable_names(self):
        """List of dependent project variables.

        References
        ----------
        >>> oProject.GetVariables
        >>> oProject.GetChildObject("Variables").GetChildNames
        """
        return [var_name for var_name in self.dependent_project_variables]

    @property
    def dependent_design_variable_names(self):
        """List of dependent design variables.

        References
        ----------
        >>> oDesign.GetVariables
        >>> oDesign.GetChildObject("Variables").GetChildNames"""
        return [var_name for var_name in self.dependent_design_variables]

    @property
    def dependent_variable_names(self):
        """List of dependent variables.

        References
        ----------
        >>> oProject.GetVariables
        >>> oDesign.GetVariables
        >>> oProject.GetChildObject("Variables").GetChildNames
        >>> oDesign.GetChildObject("Variables").GetChildNames"""
        return [var_name for var_name in self.dependent_variables]

    @property
    def _oproject(self):
        """Project."""
        return self._app._oproject

    @property
    def _odesign(self):
        """Design."""
        return self._app._odesign

    @property
    def _logger(self):
        """Logger."""
        return self._app.logger

    def __init__(self, app):
        # Global Desktop Environment
        self._app = app
        self._independent_design_variables = {}
        self._independent_project_variables = {}
        self._dependent_design_variables = {}
        self._dependent_project_variables = {}

    @property
    def _independent_variables(self):
        all_independent = {}
        all_independent.update(self._independent_project_variables)
        all_independent.update(self._independent_design_variables)
        return all_independent

    @property
    def _dependent_variables(self):
        all_dependent = {}
        for k, v in self._dependent_project_variables.items():
            all_dependent[k] = v
        for k, v in self._dependent_design_variables.items():
            all_dependent[k] = v
        return all_dependent

    @property
    def _all_variables(self):
        all_variables = {}
        all_variables.update(self._independent_variables)
        all_variables.update(self._dependent_variables)
        return all_variables

    @pyaedt_function_handler()
    def __delitem__(self, key):
        """Implement del with array name or index."""
        self.delete_variable(key)

    @pyaedt_function_handler()
    def __getitem__(self, variable_name):
        return self.variables[variable_name]

    @pyaedt_function_handler()
    def __setitem__(self, variable, value):
        self.set_variable(variable, value)
        return True

    @pyaedt_function_handler()
    def _cleanup_variables(self):
        variables = self._get_var_list_from_aedt(self._app.odesign) + self._get_var_list_from_aedt(self._app.oproject)
        all_dicts = [
            self._independent_project_variables,
            self._independent_design_variables,
            self._dependent_project_variables,
            self._dependent_design_variables,
        ]
        for dict_var in all_dicts:
            for var_name in list(dict_var.keys()):
                if var_name not in variables:
                    del dict_var[var_name]

    @pyaedt_function_handler()
    def _variable_dict(self, object_list, dependent=True, independent=True):
        """Retrieve the variable dictionary.

        Parameters
        ----------
        object_list : list
            List of objects.
        dependent : bool, optional
             Whether to include dependent variables. The default is ``True``.
        independent : bool, optional
             Whether to include independent variables. The default is ``True``.

        Returns
        -------
        dict
            Dictionary of the specified variables.

        """
        all_names = {}
        for obj in object_list:
            variables = [i for i in self._get_var_list_from_aedt(obj) if i not in list(self._all_variables.keys())]
            for variable_name in variables:
                variable_expression = self.get_expression(variable_name)
                if variable_expression:
                    all_names[variable_name] = variable_expression
                    si_value = self._app.get_evaluated_value(variable_name)
                    value = Variable(variable_expression, None, si_value, all_names, name=variable_name, app=self._app)
                    is_number_flag = is_number(value._calculated_value)
                    if variable_name.startswith("$") and is_number_flag:
                        self._independent_project_variables[variable_name] = value
                    elif variable_name.startswith("$"):
                        self._dependent_project_variables[variable_name] = value
                    elif is_number_flag:
                        self._independent_design_variables[variable_name] = value
                    else:
                        self._dependent_design_variables[variable_name] = value
        self._cleanup_variables()
        vars_to_output = {}
        dicts_to_add = []
        if independent:
            if self._app.odesign in object_list:
                dicts_to_add.append(self._independent_design_variables)
            if self._app.oproject in object_list:
                dicts_to_add.append(self._independent_project_variables)
        if dependent:
            if self._app.odesign in object_list:
                dicts_to_add.append(self._dependent_design_variables)
            if self._app.oproject in object_list:
                dicts_to_add.append(self._dependent_project_variables)
        for dict_var in dicts_to_add:
            for k, v in dict_var.items():
                vars_to_output[k] = v
        return vars_to_output

    @pyaedt_function_handler(variable_name="name")
    def get_expression(self, name):  # TODO: Should be renamed to "evaluate"
        """Retrieve the variable value of a project or design variable as a string.

        Parameters
        ----------
        name : str
            Name of the expression.

        References
        ----------
        >>> oProject.GetVariableValue
        >>> oDesign.GetVariableValue
        """
        invalid_names = ["CosimDefinition", "CoSimulator", "CoSimulator/Choices", "InstanceName", "ModelName"]
        if name not in invalid_names:
            try:
                return self.aedt_object(name).GetVariableValue(name)
            except Exception:
                return False
        else:
            return False

    @pyaedt_function_handler(variable="name")
    def aedt_object(self, name):
        """Retrieve an AEDT object.

        Parameters
        ----------
        name : str
            Name of the variable.

        """
        if name[0] == "$":
            return self._oproject
        else:
            return self._odesign

    @pyaedt_function_handler(variable_name="name", readonly="read_only", postprocessing="is_post_processing")
    def set_variable(
        self,
        name,
        expression=None,
        read_only=False,
        hidden=False,
        description=None,
        sweep=True,
        overwrite=True,
        is_post_processing=False,
        circuit_parameter=True,
    ):
        """Set the value of a design property or project variable.

        Parameters
        ----------
        name : str
            Name of the design property or project variable
            (``$var``). If this variable does not exist, a new one is
            created and a value is set.
        expression : str
            Valid string expression within the AEDT design and project
            structure.  For example, ``"3*cos(34deg)"``.
        read_only : bool, optional
            Whether to set the design property or project variable to
            read-only. The default is ``False``.
        hidden :  bool, optional
            Whether to hide the design property or project variable. The
            default is ``False``.
        description : str, optional
            Text to display for the design property or project variable in the
            ``Properties`` window. The default is ``None``.
        sweep : bool, optional
            Allows you to designate variables to include in solution indexing as a way to
            permit faster post-processing.
            Variables with the Sweep check box cleared are not used in solution indexing.
            The default is ``True``.
        overwrite : bool, optional
            Whether to overwrite an existing value for the design
            property or project variable. The default is ``False``, in
            which case this method is ignored.
        is_post_processing : bool, optional
            Whether to define a postprocessing variable.
             The default is ``False``, in which case the variable is not used in postprocessing.
        circuit_parameter : bool, optional
            Whether to define a parameter in a circuit design or a local parameter.
             The default is ``True``, in which case a circuit variable is created as a parameter default.

        Returns
        -------
        bool
             ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oProject.ChangeProperty
        >>> oDesign.ChangeProperty

        Examples
        --------
        >>> from ansys.aedt.core import Maxwell3d
        >>> aedtapp = Maxwell3d(specified_version="2025.1")

        Set the value of design property ``p1`` to ``"10mm"``,
        creating the property if it does not already eixst.

        >>> aedtapp.variable_manager.set_variable("p1",expression="10mm")

        Set the value of design property ``p1`` to ``"20mm"`` only if
        the property does not already exist.

        >>> aedtapp.variable_manager.set_variable("p1",expression="20mm",overwrite=False)

        Set the value of design property ``p2`` to ``"10mm"``,
        creating the property if it does not already exist. Also make
        it read-only and hidden and add a description.

        >>> aedtapp.variable_manager.set_variable(name="p2",
        ...                                       expression="10mm",
        ...                                       read_only=True,
        ...                                       hidden=True,
        ...                                       description="This is the description of this variable.")

        Set the value of the project variable ``$p1`` to ``"30mm"``,
        creating the variable if it does not exist.

        >>> aedtapp.variable_manager.set_variable["$p1"] == "30mm"
        """
        if name in self._independent_variables:
            del self._independent_variables[name]
            if name in self._independent_design_variables:
                del self._independent_design_variables[name]
            elif name in self._independent_project_variables:
                del self._independent_project_variables[name]
        elif name in self._dependent_variables:
            del self._dependent_variables[name]
            if name in self._dependent_design_variables:
                del self._dependent_design_variables[name]
            elif name in self._dependent_project_variables:
                del self._dependent_project_variables[name]
        if not description:
            description = ""

        desktop_object = self.aedt_object(name)
        if name.startswith("$"):
            tab_name = "ProjectVariableTab"
            prop_server = "ProjectVariables"
        else:
            tab_name = "LocalVariableTab"
            prop_server = "LocalVariables"
            if circuit_parameter and self._app.design_type in [
                "HFSS 3D Layout Design",
                "Circuit Design",
                "Maxwell Circuit",
                "Twin Builder",
            ]:
                tab_name = "DefinitionParameterTab"
            if self._app.design_type in ["HFSS 3D Layout Design", "Circuit Design", "Maxwell Circuit", "Twin Builder"]:
                prop_server = f"Instance:{desktop_object.GetName()}"

        prop_type = "VariableProp"
        if is_post_processing or "post" in name.lower()[0:5]:
            prop_type = "PostProcessingVariableProp"
        if isinstance(expression, str):
            # Handle string type variable (including arbitrary expression)# Handle input type variable
            variable = expression
        elif isinstance(expression, Variable):
            # Handle input type variable
            variable = expression.evaluated_value
        elif isinstance(expression, Quantity):
            variable = str(expression)
        elif is_number(expression):
            # Handle input type int/float, etc (including numeric 0)
            variable = str(expression)
        # Handle None, "" as Separator
        elif isinstance(expression, list):
            variable = str(expression)
        elif not expression:
            prop_type = "SeparatorProp"
            variable = ""
            try:
                if self.delete_separator(name):
                    desktop_object.Undo()
                    self._logger.clear_messages()
                    return
            except Exception:
                self._logger.debug(f"Something went wrong when deleting '{name}'.")
        else:
            raise Exception("Unhandled input type to the design property or project variable.")  # pragma: no cover

        # Get all design and project variables in lower case for a case-sensitive comparison
        var_list = self._get_var_list_from_aedt(desktop_object)
        lower_case_vars = [var_name.lower() for var_name in var_list]

        if name.lower() not in lower_case_vars:
            try:
                desktop_object.ChangeProperty(
                    [
                        "NAME:AllTabs",
                        [
                            f"NAME:{tab_name}",
                            ["NAME:PropServers", prop_server],
                            [
                                "NAME:NewProps",
                                [
                                    "NAME:" + name,
                                    "PropType:=",
                                    prop_type,
                                    "UserDef:=",
                                    True,
                                    "Value:=",
                                    variable,
                                    "Description:=",
                                    description,
                                    "ReadOnly:=",
                                    read_only,
                                    "Hidden:=",
                                    hidden,
                                    "Sweep:=",
                                    sweep,
                                ],
                            ],
                        ],
                    ]
                )
            except Exception:
                if ";" in desktop_object.GetName() and prop_type == "PostProcessingVariableProp":
                    self._logger.info("PostProcessing Variable exists already. Changing value.")
                    desktop_object.ChangeProperty(
                        [
                            "NAME:AllTabs",
                            [
                                f"NAME:{tab_name}",
                                ["NAME:PropServers", prop_server],
                                [
                                    "NAME:ChangedProps",
                                    [
                                        "NAME:" + name,
                                        "Value:=",
                                        variable,
                                        "Description:=",
                                        description,
                                        "ReadOnly:=",
                                        read_only,
                                        "Hidden:=",
                                        hidden,
                                    ],
                                ],
                            ],
                        ]
                    )
        elif overwrite:
            desktop_object.ChangeProperty(
                [
                    "NAME:AllTabs",
                    [
                        f"NAME:{tab_name}",
                        ["NAME:PropServers", prop_server],
                        [
                            "NAME:ChangedProps",
                            [
                                "NAME:" + name,
                                "Value:=",
                                variable,
                                "Description:=",
                                description,
                                "ReadOnly:=",
                                read_only,
                                "Hidden:=",
                                hidden,
                                "Sweep:=",
                                sweep,
                            ],
                        ],
                    ],
                ]
            )
            self._cleanup_variables()
        var_list = self._get_var_list_from_aedt(desktop_object)
        lower_case_vars = [var_name.lower() for var_name in var_list]
        if name.lower() not in lower_case_vars:
            return False
        return True

    @pyaedt_function_handler(separator_name="name")
    def delete_separator(self, name):
        """Delete a separator from either the active project or design.

        Parameters
        ----------
        name : str
            Value to use for the delimiter.

        Returns
        -------
        bool
            ``True`` when the separator exists and can be deleted, ``False`` otherwise.

        References
        ----------
        >>> oProject.ChangeProperty
        >>> oDesign.ChangeProperty
        """
        object_list = [(self._odesign, "Local"), (self._oproject, "Project")]

        for object_tuple in object_list:
            desktop_object = object_tuple[0]
            var_type = object_tuple[1]
            try:
                desktop_object.ChangeProperty(
                    [
                        "NAME:AllTabs",
                        [
                            f"NAME:{var_type}VariableTab",
                            ["NAME:PropServers", f"{var_type}Variables"],
                            ["NAME:DeletedProps", name],
                        ],
                    ]
                )
                return True
            except Exception:
                self._logger.debug("Failed to change desktop object property.")
        return False

    @pyaedt_function_handler(var_name="name")
    def delete_variable(self, name):
        """Delete a variable.

        Parameters
        ----------
        name : str
            Name of the variable.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oProject.ChangeProperty
        >>> oDesign.ChangeProperty
        """
        desktop_object = self.aedt_object(name)
        var_type = "Project" if desktop_object == self._oproject else "Local"
        var_list = self._get_var_list_from_aedt(desktop_object)
        lower_case_vars = [var_name.lower() for var_name in var_list]
        if name.lower() in lower_case_vars:
            try:
                desktop_object.ChangeProperty(
                    [
                        "NAME:AllTabs",
                        [
                            f"NAME:{var_type}VariableTab",
                            ["NAME:PropServers", f"{var_type}Variables"],
                            ["NAME:DeletedProps", name],
                        ],
                    ]
                )
            except Exception:  # pragma: no cover
                self._logger.debug("Failed to change desktop object property.")
            else:
                self._cleanup_variables()
                return True
        return False

    @pyaedt_function_handler(var_name="name")
    def is_used(self, name):
        """Find if a variable is used.

        Parameters
        ----------
        name : str
            Name of the variable.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        used = False
        # Modeler
        for obj in self._app.modeler.objects.values():
            used = self._find_used_variable_history(obj.history(), name)
        if used:
            self._logger.warning(f"{name} used in modeler.")
            return used

        # Material
        for mat in self._app.materials.material_keys.values():
            for _, v in mat._props.items():
                if isinstance(v, str) and name in re.findall("[$a-zA-Z0-9_]+", v):
                    used = True
                    self._logger.warning(f"{name} used in the material: {mat.name}.")
                    return used
        return used

    @pyaedt_function_handler(var_name="name")
    def is_used_variable(self, name):
        """Find if a variable is used.

        .. deprecated:: 0.7.4
           Use :func:`is_used` method instead.

        Parameters
        ----------
        name : str
            Name of the variable.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        warnings.warn("`is_used_variable` is deprecated. Use `is_used` method instead.", DeprecationWarning)
        return self.is_used(name)

    def _find_used_variable_history(self, history, var_name):
        """Find if a variable is used.

        Parameters
        ----------
        history : :class:`ansys.aedt.core.modeler.cad.elements_3d.BinaryTree`
            Object history.

        var_name : str
            Name of the variable.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        used = False
        for _, v in history.properties.items():
            if isinstance(v, str) and var_name in re.findall("[a-zA-Z0-9_]+", v):
                return True
        for el in history.children.values():
            used = self._find_used_variable_history(el, var_name)
            if used:
                return True
        return used

    @pyaedt_function_handler()
    def delete_unused_variables(self):
        """Delete unused design and project variables.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        var_list = self.variable_names

        for var in var_list[:]:
            if not self.is_used(var):
                self.delete_variable(var)
        return True

    @pyaedt_function_handler()
    def _get_var_list_from_aedt(self, desktop_object):
        var_list = []
        if self._app._is_object_oriented_enabled() and self._app.design_type not in [
            "Maxwell Circuit",
            "Circuit Netlist",
        ]:
            # To retrieve local variables
            try:
                v = list(self._app.get_oo_object(self._app.odesign, "LocalVariables").GetPropNames())
            except AttributeError:
                v = []
            var_list += v
        if self._app._is_object_oriented_enabled() and self._app.design_type in [
            "Circuit Design",
            "Twin Builder",
            "HFSS 3D Layout Design",
        ]:
            # To retrieve Parameter Default Variables
            try:
                v = list(self._app.get_oo_object(self._app.odesign, "DefinitionParameters").GetPropNames())
            except AttributeError:
                v = []
            var_list += v

        if "GetVariables" in desktop_object.__dir__():
            var_list += [i for i in list(desktop_object.GetVariables()) if i not in var_list]
        var_list += [i for i in list(self._app.oproject.GetArrayVariables()) if i not in var_list]
        return var_list


class Variable(object):
    """Stores design properties and project variables and provides operations to perform on them.

    Parameters
    ----------
    value : float, str
        Numerical value of the variable in SI units.
    units : str
        Units for the value.

    Examples
    --------

    >>> from ansys.aedt.core.application.variables import Variable

    Define a variable using a string value consistent with the AEDT properties.

    >>> v = Variable("45mm")

    Define an unitless variable with a value of 3.0.

    >>> v = Variable(3.0)

    Define a variable defined by a numeric result and a unit string.

    >>> v = Variable(3.0 * 4.5, units="mm")
    >>> assert v.numeric_value = 13.5
    >>> assert v.units = "mm"

    """

    def __init__(
        self,
        expression,
        units=None,
        si_value=None,
        full_variables=None,
        name=None,
        app=None,
        readonly=False,
        hidden=False,
        sweep=True,
        description=None,
        postprocessing=False,
        circuit_parameter=True,
    ):
        if not full_variables:
            full_variables = {}
        self._variable_name = name
        self._app = app
        self._readonly = readonly
        self._hidden = hidden
        self._sweep = sweep
        self._postprocessing = postprocessing
        self._circuit_parameter = circuit_parameter
        self._description = description
        self._is_optimization_included = None
        if units:
            if unit_system(units):
                specified_units = units
        self._units = None
        self._expression = expression
        self._calculated_value, self._units = decompose_variable_value(expression, full_variables)
        if si_value:
            self._value = si_value
        else:
            self._value = self._calculated_value
        # If units have been specified, check for a conflict and otherwise use the specified unit system
        if units:
            if self._units and self._units != specified_units:
                raise RuntimeError(
                    f"The unit specification {specified_units} is inconsistent with the identified units {self._units}."
                )
            self._units = specified_units

        if not si_value and is_number(self._value):
            try:
                scale = AEDT_UNITS[self.unit_system][self._units]
            except KeyError:
                scale = 1
            if isinstance(scale, tuple):
                self._value = scale[0](self._value, inverse=False)
            elif isinstance(scale, types.FunctionType):
                self._value = scale(self._value, False)
            else:
                self._value = self._value * scale

    @property
    def _aedt_obj(self):
        if "$" in self._variable_name and self._app:
            return self._app._oproject
        elif self._app:
            return self._app._odesign
        return None

    @pyaedt_function_handler()
    def _update_var(self):
        if self._app:
            return self._app.variable_manager.set_variable(
                self._variable_name,
                self._expression,
                read_only=self._readonly,
                hidden=self._hidden,
                sweep=self._sweep,
                description=self._description,
                is_post_processing=self._postprocessing,
                circuit_parameter=self._circuit_parameter,
            )
        return False

    @pyaedt_function_handler()
    def _set_prop_val(self, prop, val, n_times=10):
        if self._app.design_type == "Maxwell Circuit":
            return
        try:
            name = "Variables"

            if self._app.design_type in [
                "Circuit Design",
                "Twin Builder",
                "HFSS 3D Layout Design",
            ]:
                if self._variable_name in list(
                    self._app.get_oo_object(self._app.odesign, "DefinitionParameters").GetPropNames()
                ):
                    name = "DefinitionParameters"
                else:
                    name = "LocalVariables"
            i = 0
            while i < n_times:
                if name == "DefinitionParameters":
                    result = self._app.get_oo_object(self._aedt_obj, name).SetPropValue(prop, val)
                else:
                    result = self._app.get_oo_object(self._aedt_obj, f"{name}/{self._variable_name}").SetPropValue(
                        prop, val
                    )
                if result:
                    break
                i += 1
        except Exception:
            self._app.logger.debug(f"Failed to set property '{prop}' value.")

    @pyaedt_function_handler()
    def _get_prop_val(self, prop):
        if self._app.design_type == "Maxwell Circuit":
            return
        try:
            name = "Variables"

            if self._app.design_type in [
                "Circuit Design",
                "Twin Builder",
                "HFSS 3D Layout Design",
            ]:
                if self._variable_name in list(
                    self._app.get_oo_object(self._app.odesign, "DefinitionParameters").GetPropNames()
                ):
                    return self._app.get_oo_object(self._aedt_obj, "DefinitionParameters").GetPropValue(prop)
                else:
                    name = "LocalVariables"
            return self._app.get_oo_object(self._aedt_obj, f"{name}/{self._variable_name}").GetPropValue(prop)
        except Exception:
            self._app.logger.debug(f"Failed to get property '{prop}' value.")

    @property
    def name(self):
        """Variable name."""
        return self._variable_name

    @name.setter
    def name(self, value):
        fallback_val = self._variable_name
        self._variable_name = value
        if not self._update_var():
            self._variable_name = fallback_val
            if self._app:
                self._app.logger.error('"Failed to update property "name".')

    @property
    def is_optimization_enabled(self):
        """ "Check if optimization is enabled."""
        return self._get_prop_val("Optimization/Included")

    @is_optimization_enabled.setter
    def is_optimization_enabled(self, value):
        self._set_prop_val("Optimization/Included", value, 10)

    @property
    def optimization_min_value(self):
        """ "Optimization min value."""
        return self._get_prop_val("Optimization/Min")

    @optimization_min_value.setter
    def optimization_min_value(self, value):
        self._set_prop_val("Optimization/Min", value, 10)

    @property
    def optimization_max_value(self):
        """ "Optimization max value."""
        return self._get_prop_val("Optimization/Max")

    @optimization_max_value.setter
    def optimization_max_value(self, value):
        self._set_prop_val("Optimization/Max", value, 10)

    @property
    def is_sensitivity_enabled(self):
        """Check if Sensitivity is enabled."""
        return self._get_prop_val("Sensitivity/Included")

    @is_sensitivity_enabled.setter
    def is_sensitivity_enabled(self, value):
        self._set_prop_val("Sensitivity/Included", value, 10)

    @property
    def sensitivity_min_value(self):
        """ "Sensitivity min value."""
        return self._get_prop_val("Sensitivity/Min")

    @sensitivity_min_value.setter
    def sensitivity_min_value(self, value):
        self._set_prop_val("Sensitivity/Min", value, 10)

    @property
    def sensitivity_max_value(self):
        """ "Sensitivity max value."""
        return self._get_prop_val("Sensitivity/Max")

    @sensitivity_max_value.setter
    def sensitivity_max_value(self, value):
        self._set_prop_val("Sensitivity/Max", value, 10)

    @property
    def sensitivity_initial_disp(self):
        """ "Sensitivity initial value."""
        return self._get_prop_val("Sensitivity/IDisp")

    @sensitivity_initial_disp.setter
    def sensitivity_initial_disp(self, value):
        self._set_prop_val("Sensitivity/IDisp", value, 10)

    @property
    def is_tuning_enabled(self):
        """Check if tuning is enabled."""
        return self._get_prop_val("Tuning/Included")

    @is_tuning_enabled.setter
    def is_tuning_enabled(self, value):
        self._set_prop_val("Tuning/Included", value, 10)

    @property
    def tuning_min_value(self):
        """ "Tuning min value."""
        return self._get_prop_val("Tuning/Min")

    @tuning_min_value.setter
    def tuning_min_value(self, value):
        self._set_prop_val("Tuning/Min", value, 10)

    @property
    def tuning_max_value(self):
        """ "Tuning max value."""
        return self._get_prop_val("Tuning/Max")

    @tuning_max_value.setter
    def tuning_max_value(self, value):
        self._set_prop_val("Tuning/Max", value, 10)

    @property
    def tuning_step_value(self):
        """ "Tuning Step value."""
        return self._get_prop_val("Tuning/Step")

    @tuning_step_value.setter
    def tuning_step_value(self, value):
        self._set_prop_val("Tuning/Step", value, 10)

    @property
    def is_statistical_enabled(self):
        """Check if statistical is enabled."""
        return self._get_prop_val("Statistical/Included")

    @is_statistical_enabled.setter
    def is_statistical_enabled(self, value):
        self._set_prop_val("Statistical/Included", value, 10)

    @property
    def read_only(self):
        """Read-only flag value."""
        self._readonly = self._get_prop_val("ReadOnly")
        return self._readonly

    @read_only.setter
    def read_only(self, value):
        fallback_val = self._readonly
        self._readonly = value
        if not self._update_var():
            self._readonly = fallback_val
            if self._app:
                self._app.logger.error('Failed to update property "read_only".')

    @property
    def hidden(self):
        """Hidden flag value."""
        self._hidden = self._get_prop_val("Hidden")
        return self._hidden

    @hidden.setter
    def hidden(self, value):
        fallback_val = self._hidden
        self._hidden = value
        if not self._update_var():
            self._hidden = fallback_val
            if self._app:
                self._app.logger.error('Failed to update property "hidden".')

    @property
    def sweep(self):
        """Sweep flag value."""
        self._sweep = self._get_prop_val("Sweep")
        return self._sweep

    @sweep.setter
    def sweep(self, value):
        fallback_val = self._sweep
        self._sweep = value
        if not self._update_var():
            self._sweep = fallback_val
            if self._app:
                self._app.logger.error('Failed to update property "sweep".')

    @property
    def description(self):
        """Description value."""
        self._description = self._get_prop_val("Description")
        return self._description

    @description.setter
    def description(self, value):
        fallback_val = self._description
        self._description = value
        if not self._update_var():
            self._description = fallback_val
            if self._app:
                self._app.logger.error('Failed to update property "description".')

    @property
    def post_processing(self):
        """Postprocessing flag value."""
        if self._app:
            return True if self._variable_name in self._app.variable_manager.post_processing_variables else False

    @property
    def circuit_parameter(self):
        """Circuit parameter flag value."""
        if "$" in self._variable_name:
            return False
        if self._app.design_type in ["HFSS 3D Layout Design", "Circuit Design", "Maxwell Circuit", "Twin Builder"]:
            prop_server = f"Instance:{self._aedt_obj.GetName()}"
            return (
                True
                if self._variable_name in self._aedt_obj.GetProperties("DefinitionParameterTab", prop_server)
                else False
            )
        return False

    @property
    def expression(self):
        """Expression."""
        if self._aedt_obj:
            return self._aedt_obj.GetVariableValue(self._variable_name)
        return

    @expression.setter
    def expression(self, value):
        fallback_val = self._expression
        self._expression = value
        if not self._update_var():
            self._expression = fallback_val
            if self._app:
                self._app.logger.error("Failed to update property Expression.")

    @property
    def numeric_value(self):
        """Numeric part of the expression as a float value."""
        if is_array(self._value):
            return list(ast.literal_eval(self._value))
        try:
            var_obj = self._aedt_obj.GetChildObject("Variables").GetChildObject(self._variable_name)
            evaluated_value = (
                var_obj.GetPropEvaluatedValue()
                if self._app._aedt_version > "2024.2"
                else var_obj.GetPropEvaluatedValue("EvaluatedValue")
            )
            if (
                isinstance(evaluated_value, str)
                and evaluated_value.strip().startswith("[")
                and evaluated_value.strip().endswith("]")
            ):
                evaluated_value = ast.literal_eval(evaluated_value)
            val, _ = decompose_variable_value(evaluated_value)
            return val
        except (TypeError, AttributeError):
            if is_number(self._value):
                try:
                    scale = AEDT_UNITS[self.unit_system][self._units]
                except KeyError:
                    scale = 1
                if isinstance(scale, tuple):
                    return scale[0](self._value, True)
                elif isinstance(scale, types.FunctionType):
                    return scale(self._value, True)
                else:
                    return self._value / scale
            else:  # pragma: no cover
                return self._value

    @property
    def unit_system(self):
        """Unit system of the expression as a string."""
        return unit_system(self._units)

    @property
    def units(self):
        """Units."""
        try:
            var_obj = self._aedt_obj.GetChildObject("Variables").GetChildObject(self._variable_name)
            evaluated_value = (
                var_obj.GetPropEvaluatedValue()
                if self._app._aedt_version > "2024.2"
                else var_obj.GetPropEvaluatedValue("EvaluatedValue")
            )

            _, self._units = decompose_variable_value(evaluated_value)
            return self._units
        except (TypeError, AttributeError, GrpcApiError):
            pass
        return self._units

    @property
    def value(self):
        """Value."""

        return self._value

    @property
    def evaluated_value(self):
        """String value.

        The numeric value with the unit is concatenated and returned as a string. The numeric display
        in the modeler and the string value can differ. For example, you might see ``10mm`` in the
        modeler and see ``10.0mm`` returned as the string value.

        """
        return f"{self.numeric_value}{self._units}"

    @pyaedt_function_handler()
    def decompose(self):
        """Decompose a variable value to a floating with its unit.

        Returns
        -------
        tuple
            The float value of the variable and the units exposed as a string.

        Examples
        --------
        >>> hfss = Hfss()
        >>> hfss["v1"] = "3N"
        >>> print(hfss.variable_manager["v1"].decompose("v1"))
        >>> (3.0, 'N')

        """
        return decompose_variable_value(self.evaluated_value)

    @pyaedt_function_handler()
    def rescale_to(self, units):
        """Rescale the expression to a new unit within the current unit system.

        Parameters
        ----------
        units : str
            Units to rescale to.

        Examples
        --------
        >>> from ansys.aedt.core.application.variables import Variable

        >>> v = Variable("10W")
        >>> assert v.numeric_value == 10
        >>> assert v.units == "W"
        >>> v.rescale_to("kW")
        >>> assert v.numeric_value == 0.01
        >>> assert v.units == "kW"

        """
        new_unit_system = unit_system(units)
        if new_unit_system != self.unit_system:
            raise ValueError(
                f"New unit system {new_unit_system} is inconsistent with the current unit system {self.unit_system}."
            )
        self._units = units
        return self

    @pyaedt_function_handler()
    def format(self, format):
        """Retrieve the string value with the specified numerical formatting.

        Parameters
        ----------
        format : str
            Format for the numeric value of the string. For example, ``'06.2f'``. For
            more information, see the `PyFormat documentation <https://pyformat.info/>`_.

        Returns
        -------
        str
            String value with the specified numerical formatting.

        Examples
        --------
        >>> from ansys.aedt.core.application.variables import Variable

        >>> v = Variable("10W")
        >>> assert v.format("f") == '10.000000W'
        >>> assert v.format("06.2f") == '010.00W'
        >>> assert v.format("6.2f") == ' 10.00W'

        """
        return f'{self.numeric_value:" + format + "}{self._units}'

    @pyaedt_function_handler()
    def __mul__(self, other):
        """Multiply the variable with a number or another variable and return a new object.

                Parameters
                ----------
                other : numbers.Number or variable
                    Object to be multiplied.

                Returns
                -------
                type
                    Variable.

                Examples
                --------
                >>> from ansys.aedt.core.application.variables import Variable

                Multiply ``'Length1'`` by unitless ``'None'``` to obtain ``'Length'``.
                A numerical value is also considered to be unitless.

        import ansys.aedt.core.generic.constants        >>> v1 = Variable("10mm")
                >>> v2 = Variable(3)
                >>> result_1 = v1 * v2
                >>> result_2 = v1 * 3
                >>> assert result_1.numeric_value == 30.0
                >>> assert result_1.unit_system == "Length"
                >>> assert result_2.numeric_value == result_1.numeric_value
                >>> assert result_2.unit_system == "Length"

                Multiply voltage times current to obtain power.

        import ansys.aedt.core.generic.constants        >>> v3 = Variable("3mA")
                >>> v4 = Variable("40V")
                >>> result_3 = v3 * v4
                >>> assert result_3.numeric_value == 0.12
                >>> assert result_3.units == "W"
                >>> assert result_3.unit_system == "Power"

        """
        if not is_number(other) and not isinstance(other, Variable):
            raise ValueError("Multiplier must be a scalar quantity or a variable.")

        if is_number(other):
            result_value = self.numeric_value * other
            result_units = self.units
        else:
            if self.unit_system == "None":
                return self.numeric_value * other
            elif other.unit_system == "None":
                return other.numeric_value * self
            else:
                result_value = self.value * other.value
                result_units = _resolve_unit_system(self.unit_system, other.unit_system, "multiply")
                if not result_units:
                    result_units = _resolve_unit_system(other.unit_system, self.unit_system, "multiply")

        return Variable(f"{result_value}{result_units}")

    __rmul__ = __mul__

    @pyaedt_function_handler()
    def __add__(self, other):
        """Add the variable to another variable to return a new object.

        Parameters
        ----------
        other : class:`ansys.aedt.core.application.variables.Variable`
            Object to be multiplied.

        Returns
        -------
        type
            Variable.

        Examples
        --------
        >>> from ansys.aedt.core.application.variables import Variable
        >>> import ansys.aedt.core.generic.constants
        >>> v1 = Variable("3mA")
        >>> v2 = Variable("10A")
        >>> result = v1 + v2
        >>> assert result.numeric_value == 10.003
        >>> assert result.units == "A"
        >>> assert result.unit_system == "Current"

        """
        if not isinstance(other, Variable):
            raise ValueError("You can only add a variable with another variable.")
        if self.unit_system != other.unit_system:
            raise ValueError("Only Variable objects with the same unit system can be added.")

        result_value = self.value + other.value
        result_units = SI_UNITS[self.unit_system]
        # If the units of the two operands are different, return SI-Units
        result_variable = Variable(f"{result_value}{result_units}")

        # If the units of both operands are the same, return those units
        if self.units == other.units:
            result_variable.rescale_to(self.units)

        return result_variable

    @pyaedt_function_handler()
    def __sub__(self, other):
        """Subtract another variable from the variable to return a new object.

        Parameters
        ----------
        other : class:`ansys.aedt.core.application.variables.Variable`
            Object to be subtracted.

        Returns
        -------
        type
            Variable.

        Examples
        --------

        >>> import ansys.aedt.core.generic.constants
        >>> from ansys.aedt.core.application.variables import Variable
        >>> v3 = Variable("3mA")
        >>> v4 = Variable("10A")
        >>> result_2 = v3 - v4
        >>> assert result_2.numeric_value == -9.997
        >>> assert result_2.units == "A"
        >>> assert result_2.unit_system == "Current"

        """
        if not isinstance(other, Variable):
            raise ValueError("You can only subtract a variable from another variable.")
        if self.unit_system != other.unit_system:
            raise ValueError("Only Variable objects with the same unit system can be subtracted.")

        result_value = self.value - other.value
        result_units = SI_UNITS[self.unit_system]
        # If the units of the two operands are different, return SI-Units
        result_variable = Variable(f"{result_value}{result_units}")

        # If the units of both operands are the same, return those units
        if self.units == other.units:
            result_variable.rescale_to(self.units)

        return result_variable

    # Python 3.x version
    @pyaedt_function_handler()
    def __truediv__(self, other):
        """Divide the variable by a number or another variable to return a new object.

        Parameters
        ----------
        other : numbers.Number or variable
            Object by which to divide.

        Returns
        -------
        type
            Variable.

        Examples
        --------
        Divide a variable with units ``"W"`` by a variable with units ``"V"`` and automatically
        resolve the new units to ``"A"``.

        >>> from ansys.aedt.core.application.variables import Variable
        >>> import ansys.aedt.core.generic.constants
        >>> v1 = Variable("10W")
        >>> v2 = Variable("40V")
        >>> result = v1 / v2
        >>> assert result_1.numeric_value == 0.25
        >>> assert result_1.units == "A"
        >>> assert result_1.unit_system == "Current"

        """
        if not is_number(other) and not isinstance(other, Variable):
            raise ValueError("Divisor must be a scalar quantity or a variable.")

        if is_number(other):
            result_value = self.numeric_value / other
            result_units = self.units
        else:
            result_value = self.value / other.value
            result_units = _resolve_unit_system(self.unit_system, other.unit_system, "divide")

        return Variable(f"{result_value}{result_units}")

    # Python 2.7 version
    @pyaedt_function_handler()
    def __div__(self, other):
        return self.__truediv__(other)

    @pyaedt_function_handler()
    def __rtruediv__(self, other):
        """Divide another object by this object.

        Parameters
        ----------
        other : numbers.Number or variable
            Object to divide by.

        Returns
        -------
        type
            Variable.

        Examples
        --------
        Divide a number by a variable with units ``"s"`` and automatically determine that
        the result is in ``"Hz"``.

        >>> import ansys.aedt.core.generic.constants
        >>> from ansys.aedt.core.application.variables import Variable
        >>> v = Variable("1s")
        >>> result = 3.0 / v
        >>> assert result.numeric_value == 3.0
        >>> assert result.units == "Hz"
        >>> assert result.unit_system == "Freq"

        """
        if is_number(other):
            result_value = other / self.numeric_value
            result_units = _resolve_unit_system("None", self.unit_system, "divide")

        else:
            result_value = other.numeric_value / self.numeric_value
            result_units = _resolve_unit_system(other.unit_system, self.unit_system, "divide")

        return Variable(f"{result_value}{result_units}")

    # # Python 2.7 version
    # @pyaedt_function_handler()
    # def __div__(self, other):
    #     return self.__rtruediv__(other)


class DataSet(object):
    """Manages datasets.

    Parameters
    ----------
    app :
    name : str
        Name of the app.
    x : list
        List of X-axis values for the dataset.
    y : list
        List of Y-axis values for the dataset.
    z : list, optional
        List of Z-axis values for a 3D dataset only. The default is ``None``.
    v : list, optional
        List of V-axis values for a 3D dataset only. The default is ``None``.
    xunit : str, optional
        Units for the X axis. The default is ``""``.
    yunit : str, optional
        Units for the Y axis. The default is ``""``.
    zunit : str, optional
        Units for the Z axis for a 3D dataset only. The default is ``""``.
    vunit : str, optional
        Units for the V axis for a 3D dataset only. The default is ``""``.
    sort : bool, optional
        Sort dataset. The default is ``True``.
    """

    def __init__(self, app, name, x, y, z=None, v=None, xunit="", yunit="", zunit="", vunit="", sort=True):
        self._app = app
        self.name = name
        self.x = x
        self.y = y
        self.z = z
        self.v = v
        self.xunit = xunit
        self.yunit = yunit
        self.zunit = zunit
        self.vunit = vunit
        self.sort = sort

    @pyaedt_function_handler()
    def _args(self):
        """Retrieve arguments."""
        arg = ["Name:" + self.name]
        arg2 = ["Name:Coordinates"]
        if self.z is None:
            arg2.append(["NAME:DimUnits", self.xunit, self.yunit])
        elif self.v is not None:
            arg2.append(["NAME:DimUnits", self.xunit, self.yunit, self.zunit, self.vunit])
        else:
            return False
        z = {}
        v = {}
        if self.z:
            if self.sort:
                x, y, z, v = (
                    list(t) for t in zip(*sorted(zip(self.x, self.y, self.z, self.v), key=lambda e: float(e[0])))
                )
            else:
                x, y, z, v = (list(t) for t in zip(*zip(self.x, self.y, self.z, self.v)))
        else:
            if self.sort:
                x, y = (list(t) for t in zip(*sorted(zip(self.x, self.y), key=lambda e: float(e[0]))))
            else:
                x, y = (list(t) for t in zip(*(zip(self.x, self.y))))

        ver = self._app._aedt_version
        for i in range(len(x)):
            if ver >= "2022.1":
                arg3 = ["NAME:Point", float(x[i]), float(y[i])]
                if self.z:
                    arg3.append(float(z[i]))
                    arg3.append(float(v[i]))
                arg2.append(arg3)
            else:
                arg3 = []
                arg3.append("NAME:Coordinate")
                arg4 = ["NAME:CoordPoint"]
                arg4.append(float(x[i]))
                arg4.append(float(y[i]))
                if self.z:
                    arg4.append(float(z[i]))
                    arg4.append(float(v[i]))
                arg3.append(arg4)
                arg2.append(arg3)
        arg.append(arg2)
        return arg

    @pyaedt_function_handler()
    def create(self):
        """Create a dataset.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oProject.AddDataset
        >>> oDesign.AddDataset
        """
        if self.name[0] == "$":
            self._app._oproject.AddDataset(self._args())
        else:
            self._app._odesign.AddDataset(self._args())
        return True

    @pyaedt_function_handler()
    def add_point(self, x, y, z=None, v=None):
        """Add a point to the dataset.

        Parameters
        ----------
        x : float
            X coordinate of the point.
        y : float
            Y coordinate of the point.
        z : float, optional
            The default is ``None``.
        v : float, optional
            The default is ``None``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oProject.EditDataset
        >>> oDesign.EditDataset
        """
        self.x.append(x)
        self.y.append(y)
        if self.z and self.v:
            self.z.append(z)
            self.v.append(v)

        return self.update()

    @pyaedt_function_handler()
    def remove_point_from_x(self, x):
        """Remove a point from an X-axis value.

        Parameters
        ----------
        x : float

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oProject.EditDataset
        >>> oDesign.EditDataset
        """
        if x not in self.x:
            self._app.logger.error(f"Value {x} is not found.")
            return False
        id_to_remove = self.x.index(x)
        return self.remove_point_from_index(id_to_remove)

    @pyaedt_function_handler()
    def remove_point_from_index(self, id_to_remove):
        """Remove a point from an index.

        Parameters
        ----------
        id_to_remove : int
            ID of the index.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oProject.EditDataset
        >>> oDesign.EditDataset
        """
        if id_to_remove < len(self.x) > 2:
            self.x.pop(id_to_remove)
            self.y.pop(id_to_remove)
            if self.z and self.v:
                self.z.pop(id_to_remove)
                self.v.pop(id_to_remove)
            return self.update()
        self._app.logger.error(f"cannot Remove {id_to_remove} index.")
        return False

    @pyaedt_function_handler()
    def update(self):
        """Update the dataset.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oProject.EditDataset
        >>> oDesign.EditDataset
        """
        args = self._args()
        if not args:
            return False
        if self.name[0] == "$":
            self._app._oproject.EditDataset(self.name, self._args())
        else:
            self._app._odesign.EditDataset(self.name, self._args())
        return True

    @pyaedt_function_handler()
    def delete(self):
        """Delete the dataset.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oProject.DeleteDataset
        >>> oDesign.DeleteDataset
        """
        if self.name[0] == "$":
            self._app._oproject.DeleteDataset(self.name)
            del self._app.project_datasets[self.name]
        else:
            self._app._odesign.DeleteDataset(self.name)
            del self._app.design_datasets[self.name]
        return True

    @pyaedt_function_handler(dataset_path="output_dir")
    def export(self, output_dir=None):
        """Export the dataset.

        Parameters
        ----------
        output_dir : str, optional
            Path to export the dataset to. The default is ``None``, in which
            case the dataset is exported to the working_directory path.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oProject.ExportDataset
        >>> oDesign.ExportDataset
        """
        if not output_dir:
            output_dir = os.path.join(self._app.working_directory, self.name + ".tab")
        if self.name[0] == "$":
            self._app._oproject.ExportDataset(self.name, output_dir)
        else:
            self._app._odesign.ExportDataset(self.name, output_dir)
        return True
