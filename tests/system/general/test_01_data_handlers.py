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

from ansys.aedt.core.generic import data_handlers as dh
from ansys.aedt.core.generic.numbers import Quantity
import pytest


@pytest.fixture(scope="module", autouse=True)
def desktop():
    """Override the desktop fixture to DO NOT open the Desktop when running this test class"""
    return


class TestClass:

    def test_str_to_bool(self):
        test_list_1 = ["one", "two", "five"]
        bool_values = list(map(dh.str_to_bool, test_list_1))
        assert all(isinstance(b, str) for b in bool_values)  # All strings
        test_list_1.append("True")
        assert True in list(map(dh.str_to_bool, test_list_1))
        test_list_2 = ["Stop", "go", "run", "crawl", "False"]
        assert False in list(map(dh.str_to_bool, test_list_2))

    def test_normalize_string_format(self):
        dirty = "-Hello Wòrld - Test---Strïng  -  With -  Múltiple    Spaces ç & Unsupport€d Ch@rachter$ £ike * "  # codespell:ignore  # noqa: E501
        clean = "Hello_World_Test_String_With_Multiple_Spaces_c_and_UnsupportEd_ChatrachterS_Like"  # codespell:ignore  # noqa: E501
        assert dh.normalize_string_format(dirty) == clean

    def test_numbers(self):
        a = Quantity("1GHz")
        assert a == 1
        assert str(a) == "1GHz"
        a.rescale = True
        assert a.to("MHz") == 1e3
        a.unit = "Hz"
        assert a.unit == "Hz"
        assert a.value == 1
        a.rescale = False
        a.unit = "MHz"
        assert a.value == 1
        a.unit = "GHz"
        assert float(a + 1) == 2
        assert float(a + "2GHz") == 3
        b = Quantity("1GHz")
        assert isinstance(b - a, Quantity)
        assert b * 2
        assert b / 2
        assert b + "1GHz"
