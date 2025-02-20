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

from ctypes import POINTER
from ctypes import byref
from ctypes import c_char_p
from ctypes import c_int
from ctypes import create_string_buffer
from enum import Enum

import ansys.aedt.core


class OptimizationGoalParameter(Enum):
    """Enumeration of optimization goals parameters table.

    **Attributes:**

    - LOWER_FREQUENCY: Represents the lower frequency parameter, positioned
    as the first value in the optimization goal table.
    - UPPER_FREQUENCY: Represents the upper frequency parameter, positioned
    as the second value in the optimization goal table.
    - GOAL_VALUE: Represents the goal value parameter, positioned
    as the third value in the optimization goal table.
    - CONDITION: Represents the condition parameter, positioned
    as the fourth value in the optimization goal table.
    - PARAMETER_NAME: Represents the name of the parameter, positioned
    as the fifth value in the optimization goal table.
    - WEIGHT: Represents the weight parameter, positioned
    as the sixth value in the optimization goal table.
    - ENABLED: Represents the status of using the goal parameters, positioned
    as the seventh value in the optimization goal table.
    """

    LOWER_FREQUENCY = 0
    UPPER_FREQUENCY = 1
    GOAL_VALUE = 2
    CONDITION = 3
    PARAMETER_NAME = 4
    WEIGHT = 5
    ENABLED = 6


class OptimizationGoalsTable:
    """Provides management of optimization goals within a table structure.

    This class offers functionality to add, update, or delete entries in the optimization goals table,
    facilitating the manipulation of optimization parameters for simulation tasks.
    Each entry in the table can specify a range of parameters including lower and upper frequency limits,
    a target value for the optimization goal, a condition that defines how the goal is evaluated,
    the name of the parameter to optimize, the weight of the goal in the overall optimization process,
    and whether the goal is active or not.
    """

    def __init__(self):
        self._dll = ansys.aedt.core.filtersolutions_core._dll_interface()._dll
        self._dll_interface = ansys.aedt.core.filtersolutions_core._dll_interface()
        self._define_optimization_goals_dll_functions()

    def _define_optimization_goals_dll_functions(self):
        """Define C++ API DLL functions."""
        self._dll.getOptimizationGoalDefinitionRowCount.argtype = POINTER(c_int)
        self._dll.getOptimizationGoalDefinitionRowCount.restype = c_int

        self._dll.getOptimizationGoalDefinitionRow.argtype = [c_int, POINTER(c_char_p), c_int]
        self._dll.getOptimizationGoalDefinitionRow.restype = c_int

        self._dll.updateOptimizationGoalDefinitionRow.argtype = [c_int, c_int, c_char_p]
        self._dll.updateOptimizationGoalDefinitionRow.restype = c_int

        self._dll.appendOptimizationGoalDefinitionRow.argtype = [c_int, c_char_p]
        self._dll.appendOptimizationGoalDefinitionRow.restype = c_int

        self._dll.insertOptimizationGoalDefinitionRow.argtypes = [c_int, c_char_p, c_char_p]
        self._dll.insertOptimizationGoalDefinitionRow.restype = c_int

        self._dll.removeOptimizationGoalDefinitionRow.argtype = c_int
        self._dll.removeOptimizationGoalDefinitionRow.restype = c_int

        self._dll.adjustGoalFrequency.argtype = c_char_p
        self._dll.adjustGoalFrequency.restype = c_int

    def _bytes_or_none(self, str_value):
        if str_value:
            return bytes(str_value, "ascii")
        return None

    @property
    def row_count(self) -> int:
        """Number of golas in the optimization goals table.

        The default is `0`.

        Returns
        -------
        int
        """
        table_row_count = c_int()
        status = self._dll.getOptimizationGoalDefinitionRowCount(byref(table_row_count))
        self._dll_interface.raise_error(status)
        return int(table_row_count.value)

    def row(self, row_index) -> list:
        """Get the values for one row of the optimization goals table.

        The values are returned as a list: [value1, value2, ..., value7].

        Parameters
        ----------
        row_index: int
            Index of the row. Valid values range from ``0`` to ``49``, inclusive.

        Returns
        -------
        list
            A list of strings representing the row parameters.
        """
        row_parameter_buffer = create_string_buffer(1024)
        # Call the DLL function. Assuming it fills the buffer with comma-separated values.
        status = self._dll.getOptimizationGoalDefinitionRow(row_index, byref(row_parameter_buffer), 1024)
        self._dll_interface.raise_error(status)
        # Decode the buffer to a Python string and split by comma to get a list.
        row_parameters = row_parameter_buffer.value.decode("utf-8").split("|")
        return row_parameters

    def update_row(
        self,
        row_index,
        lower_frequency=None,
        upper_frequency=None,
        goal_value=None,
        condition=None,
        parameter_name=None,
        weight=None,
        enabled=None,
    ):
        """Update the row parameters for an existing row in the optimization goals table.

        Parameters
        ----------
        row_index: int
            Index of the row. Valid values range from ``0`` to ``49``, inclusive.
        lower_frequency: str, optional
            New lower frequency value to set.
            If no value is specified, the value remains unchanged.
        upper_frequency: str, optional
            New upper frequency value to set.
            If no value is specified, the value remains unchanged.
        goal_value: str, optional
            New goal value to set.
            If no value is specified, the value remains unchanged.
        condition: str, optional
            New condition value to set.
            If no value is specified, the value remains unchanged.
        parameter_name: str, optional
            New parameter name value to set.
            If no value is specified, the value remains unchanged.
        weight: str, optional
            New weight value to set.
            If no value is specified, the value remains unchanged.
        enabled: str, optional
            New enabled value to set.
            If no value is specified, the value remains unchanged.
        """
        status = self._dll.updateOptimizationGoalDefinitionRow(
            row_index,
            self._bytes_or_none(lower_frequency),
            self._bytes_or_none(upper_frequency),
            self._bytes_or_none(goal_value),
            self._bytes_or_none(condition),
            self._bytes_or_none(parameter_name),
            self._bytes_or_none(weight),
            self._bytes_or_none(enabled),
        )
        self._dll_interface.raise_error(status)

    def append_row(
        self,
        lower_frequency=None,
        upper_frequency=None,
        goal_value=None,
        condition=None,
        parameter_name=None,
        weight=None,
        enabled=None,
    ):
        """Append a new row of parameters to the optimization goals table,
        ensuring the total does not exceed 50 entries.

        Parameters
        ----------
        lower_frequency: str, optional
            Lower frequency value to set.
        upper_frequency: str, optional
            Upper frequency value to set.
        goal_value: str, optional
            Goal value to set.
        condition: str, optional
            Condition value to set.
        parameter_name: str, optional
            Parameter name value to set.
        weight: str, optional
            Weight value to set.
        enabled: str, optional
            Enabled value to set.
        """
        status = self._dll.appendOptimizationGoalDefinitionRow(
            self._bytes_or_none(lower_frequency),
            self._bytes_or_none(upper_frequency),
            self._bytes_or_none(goal_value),
            self._bytes_or_none(condition),
            self._bytes_or_none(parameter_name),
            self._bytes_or_none(weight),
            self._bytes_or_none(enabled),
        )
        self._dll_interface.raise_error(status)

    def insert_row(
        self,
        row_index,
        lower_frequency=None,
        upper_frequency=None,
        goal_value=None,
        condition=None,
        parameter_name=None,
        weight=None,
        enabled=None,
    ):
        """Insert a new row of parameters to the optimization goals table,
        ensuring the total does not exceed 50 entries.

        Parameters
        ----------
        row_index: int
            Index of the row. Valid values range from ``0`` to ``49``, inclusive.
        lower_frequency: str, optional
            Lower frequency value.
        upper_frequency: str, optional
            Upper frequency value.
        goal_value: str, optional
            Goal value.
        condition: str, optional
            Condition value.
        parameter_name: str, optional
            Parameter name.
        weight: str, optional
            Weight value.
        enabled: str, optional
            Enabled value.
        """
        status = self._dll.insertOptimizationGoalDefinitionRow(
            row_index,
            self._bytes_or_none(lower_frequency),
            self._bytes_or_none(upper_frequency),
            self._bytes_or_none(goal_value),
            self._bytes_or_none(condition),
            self._bytes_or_none(parameter_name),
            self._bytes_or_none(weight),
            self._bytes_or_none(enabled),
        )
        self._dll_interface.raise_error(status)

    def remove_row(self, row_index):
        """Remove a row from the optimization goals table.

        Parameters
        ----------
        row_index: int
            Index of the row. Valid values range from ``0`` to ``49``, inclusive.
        """
        status = self._dll.removeOptimizationGoalDefinitionRow(row_index)
        self._dll_interface.raise_error(status)

    def restore_design_goals(self):
        """Configure the optimization goal table according to the recommended goals for the current design."""
        status = self._dll.setDesignGoals()
        self._dll_interface.raise_error(status)

    def save_goals(self, file_path) -> str:
        """Save the optimization goals from a design's optimization goals table to a config file.

        Parameters
        ----------
        file_path: The path to the config file where the goals will be saved.
        """
        with open(file_path, mode="w", newline="") as file:
            for row_index in range(self.row_count):
                row_data = self.row(row_index)
                slash_separated = "/".join(row_data)
                file.write(slash_separated + "\n")

    def load_goals(self, file_path) -> str:
        """Load optimization goals from a config file into this optimization goals table.

        Parameters
        ----------
        file_path: str
            The path to the config file from which the goals will be loaded.
        """
        with open(file_path, mode="r", newline="") as file:
            self.clear_goal_entries()
            lines = file.readlines()
            for line in lines:
                row = line.strip().split("/")
                self.append_row(*row)

    def adjust_goal_frequency(self, adjust_goal_frequency_string):
        """Adjust all goal frequencies in the table by the adjusting
        frequency value which can be positive or negative."""
        self._dll_interface.set_string(self._dll.adjustGoalFrequency, adjust_goal_frequency_string)

    def clear_goal_entries(self):
        """Clear the goal entries from optimization goals table."""
        status = self._dll.clearGoalEntries()
        self._dll_interface.raise_error(status)
