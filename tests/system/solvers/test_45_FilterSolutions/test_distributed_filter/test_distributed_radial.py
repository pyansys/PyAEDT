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

from ansys.aedt.core.generic.settings import is_linux
import pytest

from tests.system.solvers.conftest import config


@pytest.mark.skipif(is_linux, reason="FilterSolutions API is not applicable on Linux.")
@pytest.mark.skipif(config["desktopVersion"] < "2025.2", reason="Skipped on versions earlier than 2025.2")
class TestClass:

    def test_radial_stubs(self, distributed_design):
        assert distributed_design.radial.radial_stubs is False
        distributed_design.radial.radial_stubs = True
        assert distributed_design.radial.radial_stubs

    def test_fixed_angle(self, distributed_design):
        assert distributed_design.radial.fixed_angle == "90"
        distributed_design.radial.fixed_angle = "45"
        assert distributed_design.radial.fixed_angle == "45"

    def test_delta_stubs(self, distributed_design):
        assert distributed_design.radial.delta_stubs is False
        distributed_design.radial.delta_stubs = True
        assert distributed_design.radial.delta_stubs

    def test_split_wide_angle(self, distributed_design):
        assert distributed_design.radial.split_wide_angle == "0"
        distributed_design.radial.split_wide_angle = "10"
        assert distributed_design.radial.split_wide_angle == "10"

    def test_offset_from_feedline(self, distributed_design):
        assert distributed_design.radial.offset_from_feedline == "200 um"
        distributed_design.radial.offset_from_feedline = "100 um"
        assert distributed_design.radial.offset_from_feedline == "100 um"

    def test_alternate_radial_delta_orientation(self, distributed_design):
        assert distributed_design.radial.alternate_radial_delta_orientation
        distributed_design.radial.alternate_radial_delta_orientation = False
        assert distributed_design.radial.alternate_radial_delta_orientation is False

    def test_adjust_width_max(self, distributed_design):
        assert distributed_design.radial.adjust_width_max
        distributed_design.radial.adjust_width_max = False
        assert distributed_design.radial.adjust_width_max is False

    def test_max_radial_delta_angle(self, distributed_design):
        assert distributed_design.radial.max_radial_delta_angle == "120"
        distributed_design.radial.max_radial_delta_angle = "90"
        assert distributed_design.radial.max_radial_delta_angle == "90"

    def test_adjust_length_max(self, distributed_design):
        assert distributed_design.radial.adjust_length_max is False
        distributed_design.radial.adjust_length_max = True
        assert distributed_design.radial.adjust_length_max

    def test_min_radial_delta_angle(self, distributed_design):
        assert distributed_design.radial.min_radial_delta_angle == "15"
        distributed_design.radial.min_radial_delta_angle = "10"
        assert distributed_design.radial.min_radial_delta_angle == "10"

    def test_apply_limits_radial_delta(self, distributed_design):
        assert distributed_design.radial.apply_limits_radial_delta
        distributed_design.radial.apply_limits_radial_delta = False
        assert distributed_design.radial.apply_limits_radial_delta is False
