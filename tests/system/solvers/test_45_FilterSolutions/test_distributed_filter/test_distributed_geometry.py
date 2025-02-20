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

from ansys.aedt.core.generic.general_methods import is_linux
import pytest

from tests.system.solvers.conftest import config


@pytest.mark.skipif(is_linux, reason="FilterSolutions API is not applicable on Linux.")
@pytest.mark.skipif(config["desktopVersion"] < "2025.2", reason="Skipped on versions earlier than 2025.2")
class TestClass:

    def test_fixed_width_to_height_ratio_capacitor_sections(self, distributed_design):
        assert distributed_design.geometry.fixed_width_to_height_ratio_capacitor_sections == "4"
        distributed_design.geometry.fixed_width_to_height_ratio_capacitor_sections = "2"
        assert distributed_design.geometry.fixed_width_to_height_ratio_capacitor_sections == "2"

    def test_fixed_width_to_height_ratio_inductor_sections(self, distributed_design):
        assert distributed_design.geometry.fixed_width_to_height_ratio_inductor_sections == "0.25"
        distributed_design.geometry.fixed_width_to_height_ratio_inductor_sections = "2"
        assert distributed_design.geometry.fixed_width_to_height_ratio_inductor_sections == "2"

    def test_wide_stubs_width_to_substrate_height_ratio(self, distributed_design):
        assert distributed_design.geometry.wide_stubs_width_to_substrate_height_ratio == "0"
        distributed_design.geometry.wide_stubs_width_to_substrate_height_ratio = "1"
        assert distributed_design.geometry.wide_stubs_width_to_substrate_height_ratio == "1"

    def test_alternate_stub_orientation(self, distributed_design):
        assert distributed_design.geometry.alternate_stub_orientation is False
        distributed_design.geometry.alternate_stub_orientation = True
        assert distributed_design.geometry.alternate_stub_orientation

    def test_max_width(self, distributed_design):
        assert distributed_design.geometry.max_width == "6.35 mm"
        distributed_design.geometry.max_width = "1.25mm"
        assert distributed_design.geometry.max_width == "1.25mm"

    def test_min_width(self, distributed_design):
        assert distributed_design.geometry.min_width == "50 um"
        distributed_design.geometry.min_width = "200 um"
        assert distributed_design.geometry.min_width == "200 um"

    def test_max_gap(self, distributed_design):
        assert distributed_design.geometry.max_gap == "6.35 mm"
        distributed_design.geometry.max_gap = "1.25mm"
        assert distributed_design.geometry.max_gap == "1.25mm"

    def test_min_gap(self, distributed_design):
        assert distributed_design.geometry.min_gap == "50 um"
        distributed_design.geometry.min_gap = "200 um"
        assert distributed_design.geometry.min_gap == "200 um"

    def test_apply_limits(self, distributed_design):
        assert distributed_design.geometry.apply_limits
        distributed_design.geometry.apply_limits = False
        assert distributed_design.geometry.apply_limits is False

    def test_adjust_length_on_limit(self, distributed_design):
        assert distributed_design.geometry.adjust_length_on_limit
        distributed_design.geometry.adjust_length_on_limit = False
        assert distributed_design.geometry.adjust_length_on_limit is False
