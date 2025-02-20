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

from __future__ import absolute_import
from __future__ import division

import ast
import re

from ansys.aedt.core.generic.constants import AEDT_UNITS
from ansys.aedt.core.generic.constants import SI_UNITS
from ansys.aedt.core.generic.constants import unit_converter
from ansys.aedt.core.generic.constants import unit_system


def _units_assignment(value):
    if isinstance(value, Quantity):
        return str(value)
    elif isinstance(value, list):
        return [_units_assignment(i) for i in value]
    return value


class Quantity:
    """Stores a number with its unit.

    Parameters
    ----------
    expression : float, str
        Numerical value of the variable with or without units.
    unit : str
        Units for the value.
    """

    def __init__(
        self,
        expression,
        unit=None,
    ):
        self._unit = ""
        if unit in AEDT_UNITS:
            self._unit_system = unit
            self._unit = list(AEDT_UNITS[unit].keys())[0]
        else:
            self._parse_units(unit)

        self._value, _unit = decompose_variable_value(expression)
        if _unit:
            self._parse_units(_unit)

    def to(self, unit):
        """Convert the actual number to new unit."""
        if unit in AEDT_UNITS[self.unit_system]:
            new_value = unit_converter(
                self.value, unit_system=self.unit_system, input_units=self._unit, output_units=unit
            )
            return Quantity(new_value, unit)

    @property
    def _units_lower(self):
        if self._unit_system and self._unit_system in AEDT_UNITS:
            return [i.lower() for i in list(AEDT_UNITS[self._unit_system].keys())]
        else:
            return []

    def _parse_units(self, unit):
        if unit:
            self._unit_system = unit_system(unit)
            if unit.lower() in self._units_lower:
                self._unit = list(AEDT_UNITS[self._unit_system].keys())[self._units_lower.index(unit.lower())]

    @property
    def expression(self):
        return f"{self._value}{self._unit}"

    @expression.setter
    def expression(self, value):
        """Value number with unit.

        Returns
        -------
        str
        """
        self._value, _unit = decompose_variable_value(value)
        if _unit:
            self._parse_units(_unit)

    @property
    def unit_system(self):
        """Value unit system.

        Returns
        -------
        str
        """
        return self._unit_system

    @property
    def unit(self):
        """Value unit.

        Returns
        -------
        str
        """
        return self._unit

    @unit.setter
    def unit(self, value):
        if value in AEDT_UNITS[self.unit_system]:
            self._unit = value

    @property
    def value(self):
        """Value number.

        Returns
        -------
        float
        """
        return self._value

    @value.setter
    def value(self, value):
        _value, _unit = decompose_variable_value(value)
        self._value = _value
        self._parse_units(_unit)

    def __repr__(self):
        return "%.16g" % self.value + self.unit

    def __str__(self):
        return "%.16g" % self.value + self.unit

    def __add__(self, other):
        if isinstance(other, Quantity):
            if self.unit == other.unit:
                return Quantity(self.value + other.value, self.unit)
            else:
                new_other = other.to(self.unit)
                return Quantity(self.value + new_other.value, self.unit)
        elif isinstance(other, str):
            other = Quantity(other)
            if other.unit_system == self.unit_system:
                new_other = other.to(self.unit)
                return Quantity(self.value + new_other.value, self.unit)
        elif isinstance(other, (int, float)):
            return Quantity(self.value + other, self.unit)
        else:
            raise TypeError("Unsupported type for addition")

    def __sub__(self, other):
        if isinstance(other, Quantity):
            if self.unit == other.unit:
                return Quantity(self.value - other.value, self.unit)
            else:
                new_other = other.to(self.unit)
                return Quantity(self.value + new_other.value, self.unit)
        elif isinstance(other, str):
            other = Quantity(other)
            if other.unit_system == self.unit_system:
                new_other = other.to(self.unit)
                return Quantity(self.value + new_other.value, self.unit)
        elif isinstance(other, (int, float)):
            return Quantity(self.value - other, self.unit)
        else:
            raise TypeError("Unsupported type for subtraction")

    def __mul__(self, other):
        if isinstance(other, (int, float)):
            return Quantity(self.value * other, self.unit)
        else:
            raise TypeError("Unsupported type for multiplication")

    def __truediv__(self, other):
        if isinstance(other, (int, float)):
            return Quantity(self.value / other, self.unit)
        else:
            raise TypeError("Unsupported type for division")

    def __eq__(self, other):
        if isinstance(other, Quantity):
            return self.value == other.value and self.unit == other.unit
        elif isinstance(other, (int, float)):
            return self.value == other
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __lt__(self, other):
        if isinstance(other, Quantity):
            if self.unit == other.unit:
                return self.value < other.value
            else:
                raise ValueError("Cannot compare numbers with different units")
        elif isinstance(other, (int, float)):
            return self.value < other
        else:
            raise TypeError("Unsupported type for comparison")

    def __le__(self, other):
        return self.__lt__(other) or self.__eq__(other)

    def __gt__(self, other):
        return not self.__le__(other)

    def __ge__(self, other):
        return not self.__lt__(other)

    def __float__(self):
        return float(self.value)

    def __int__(self):
        return int(self.value)


def _find_units_in_dependent_variables(variable_value, full_variables={}):
    m2 = re.findall(r"[0-9.]+ *([a-z_A-Z]+)", variable_value)
    if len(m2) > 0:
        if len(set(m2)) <= 1:
            return m2[0]
        else:
            if unit_system(m2[0]):
                return SI_UNITS[unit_system(m2[0])]
    else:
        m1 = re.findall(r"(?<=[/+-/*//^/(/[])([a-z_A-Z/$]\w*)", variable_value.replace(" ", ""))
        m2 = re.findall(r"^([a-z_A-Z/$]\w*)", variable_value.replace(" ", ""))
        m = list(set(m1).union(m2))
        for i, v in full_variables.items():
            if i in m and _find_units_in_dependent_variables(v):
                return _find_units_in_dependent_variables(v)
    return ""


def decompose_variable_value(variable_value, full_variables={}):
    """Decompose a variable value.

    Parameters
    ----------
    variable_value : str
    full_variables : dict

    Returns
    -------
    tuples
        Tuples made of the float value of the variable and the units exposed as a string.
    """
    # set default return values - then check for valid units
    float_value = variable_value
    units = ""

    if is_number(variable_value):
        float_value = float(variable_value)
    elif isinstance(variable_value, str) and variable_value != "nan":
        try:
            # Handle a numerical value in string form
            float_value = float(variable_value)
        except ValueError:
            # search for a valid units string at the end of the variable_value
            loc = re.search(r"[-+]?(\d+(\.\d*)?|\.\d+)([eE][-+]?\d+)?", variable_value)
            units = _find_units_in_dependent_variables(variable_value, full_variables)
            if loc:
                loc_units = loc.span()[1]
                extract_units = variable_value[loc_units:]
                chars = set("+*/()[]")
                if any((c in chars) for c in extract_units):
                    return variable_value, units
                try:
                    float_value = float(variable_value[0:loc_units])
                    units = extract_units
                except ValueError:
                    float_value = variable_value

    return float_value, units


def isclose(a, b, relative_tolerance=1e-9, absolute_tolerance=0.0):
    """Whether two numbers are close to each other given relative and absolute tolerances.

    Parameters
    ----------
    a : float, int
        First number to compare.
    b : float, int
        Second number to compare.
    relative_tolerance : float
        Relative tolerance. The default value is ``1e-9``.
    absolute_tolerance : float
        Absolute tolerance. The default value is ``0.0``.

    Returns
    -------
    bool
        ``True`` if the two numbers are closed, ``False`` otherwise.
    """
    return abs(a - b) <= max(relative_tolerance * max(abs(a), abs(b)), absolute_tolerance)


def is_number(a):
    """Whether the given input is a number.

    Parameters
    ----------
    a : float, int, str
        Number to check.

    Returns
    -------
    bool
        ``True`` if it is a number, ``False`` otherwise.
    """
    if isinstance(a, float) or isinstance(a, int):
        return True
    elif isinstance(a, str):
        try:
            float(a)
            return True
        except ValueError:
            return False
    else:
        return False


def is_array(a):
    """Whether the given input is an array.

    Parameters
    ----------
    a : list
        List to check.

    Returns
    -------
    bool
        ``True`` if it is an array, ``False`` otherwise.
    """
    try:
        v = list(ast.literal_eval(a))
    except (ValueError, TypeError, NameError, SyntaxError):
        return False
    else:
        if isinstance(v, list):
            return True
        else:
            return False
