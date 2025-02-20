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

from ansys.aedt.core.filtersolutions_core.export_to_aedt import ExportCreationMode
from ansys.aedt.core.filtersolutions_core.export_to_aedt import ExportFormat
from ansys.aedt.core.filtersolutions_core.export_to_aedt import PartLibraries
from ansys.aedt.core.filtersolutions_core.export_to_aedt import SubstrateEr
from ansys.aedt.core.filtersolutions_core.export_to_aedt import SubstrateResistivity
from ansys.aedt.core.filtersolutions_core.export_to_aedt import SubstrateType
from ansys.aedt.core.generic.settings import is_linux
import pytest

from tests.system.solvers.conftest import config

from ..resources import read_resource_file
from ..resources import resource_path

first_modelithics_inductor = "AVX -> IND_AVX_0201_101 Accu-L"
second_modelithics_inductor = "AVX -> IND_AVX_0402_101 AccuL"
third_modelithics_inductor = "Wurth -> IND_WTH_0603_003 WE-KI"
first_modelithics_capacitor = "Amotech -> CAP_AMH_0201_001 A60Z"
second_modelithics_capacitor = "Murata -> CAP_MUR_0805_004 GRM219"
first_modelithics_resistor = "AVX -> RES_AVX_0402_001 UBR0402"
second_modelithics_resistor = "Vishay -> RES_VIS_0603_001 D11"


@pytest.mark.skipif(is_linux, reason="FilterSolutions API is not supported on Linux.")
@pytest.mark.skipif(config["desktopVersion"] < "2025.2", reason="Skipped on versions earlier than 2025.2")
class TestClass:

    def test_modelithics_include_interconnect_enabled(self, lumped_design):
        assert lumped_design.export_to_aedt.modelithics_include_interconnect_enabled
        lumped_design.export_to_aedt.modelithics_include_interconnect_enabled = False
        assert lumped_design.export_to_aedt.modelithics_include_interconnect_enabled is False

    @pytest.mark.skipif(config["skip_modelithics"], reason="Modelithics is not installed.")
    def test_modelithics_inductor_list_count(self, lumped_design):
        with pytest.raises(RuntimeError) as info:
            assert lumped_design.export_to_aedt.modelithics_capacitor_list_count == 2
        assert info.value.args[0] == "The part library is not set to Modelithics"
        lumped_design.export_to_aedt.part_libraries = PartLibraries.MODELITHICS
        assert lumped_design.export_to_aedt.modelithics_inductor_list_count == 116

    @pytest.mark.skipif(config["skip_modelithics"], reason="Modelithics is not installed.")
    def test_modelithics_inductor_list(self, lumped_design):
        with pytest.raises(RuntimeError) as info:
            lumped_design.export_to_aedt.modelithics_inductor_list(0)
        assert info.value.args[0] == "The part library is not set to Modelithics"
        lumped_design.export_to_aedt.part_libraries = PartLibraries.MODELITHICS
        with pytest.raises(RuntimeError) as info:
            lumped_design.export_to_aedt.modelithics_inductor_list(-1)
        assert info.value.args[0] == "The Modelithics inductor at the given index is not available"
        lumped_design.export_to_aedt.modelithics_inductor_selection = first_modelithics_inductor
        assert lumped_design.export_to_aedt.modelithics_inductor_list(0) == first_modelithics_inductor

    @pytest.mark.skipif(config["skip_modelithics"], reason="Modelithics is not installed.")
    def test_modelithics_inductor_selection(self, lumped_design):
        with pytest.raises(RuntimeError) as info:
            lumped_design.export_to_aedt.modelithics_inductor_selection = first_modelithics_inductor
        assert info.value.args[0] == "The part library is not set to Modelithics"
        lumped_design.export_to_aedt.part_libraries = PartLibraries.MODELITHICS
        with pytest.raises(RuntimeError) as info:
            assert lumped_design.export_to_aedt.modelithics_inductor_selection == first_modelithics_inductor
        assert info.value.args[0] == "No Modelithics inductor is selected"
        lumped_design.export_to_aedt.modelithics_inductor_selection = first_modelithics_inductor
        assert lumped_design.export_to_aedt.modelithics_inductor_selection == first_modelithics_inductor

    @pytest.mark.skipif(config["skip_modelithics"], reason="Modelithics is not installed.")
    def test_modelithics_inductor_family_list_count(self, lumped_design):
        with pytest.raises(RuntimeError) as info:
            assert lumped_design.export_to_aedt.modelithics_inductor_family_list_count == 2
        assert info.value.args[0] == "The part library is not set to Modelithics"
        lumped_design.export_to_aedt.part_libraries = PartLibraries.MODELITHICS
        assert lumped_design.export_to_aedt.modelithics_inductor_family_list_count == 0
        lumped_design.export_to_aedt.modelithics_inductor_add_family(second_modelithics_inductor)
        assert lumped_design.export_to_aedt.modelithics_inductor_family_list_count == 1
        lumped_design.export_to_aedt.modelithics_inductor_add_family(third_modelithics_inductor)
        assert lumped_design.export_to_aedt.modelithics_inductor_family_list_count == 2

    @pytest.mark.skipif(config["skip_modelithics"], reason="Modelithics is not installed.")
    def test_modelithics_inductor_family_list(self, lumped_design):
        with pytest.raises(RuntimeError) as info:
            lumped_design.export_to_aedt.modelithics_inductor_family_list(0)
        assert info.value.args[0] == "The part library is not set to Modelithics"
        lumped_design.export_to_aedt.part_libraries = PartLibraries.MODELITHICS
        with pytest.raises(RuntimeError) as info:
            lumped_design.export_to_aedt.modelithics_inductor_family_list(0)
        assert info.value.args[0] == "The Modelithics inductor family at the given index is not available"
        lumped_design.export_to_aedt.modelithics_inductor_add_family(second_modelithics_inductor)
        lumped_design.export_to_aedt.modelithics_inductor_add_family(third_modelithics_inductor)
        assert lumped_design.export_to_aedt.modelithics_inductor_family_list(0) == second_modelithics_inductor
        assert lumped_design.export_to_aedt.modelithics_inductor_family_list(1) == third_modelithics_inductor

    @pytest.mark.skipif(config["skip_modelithics"], reason="Modelithics is not installed.")
    def test_modelithics_inductor_family_list_add_family(self, lumped_design):
        with pytest.raises(RuntimeError) as info:
            lumped_design.export_to_aedt.modelithics_inductor_add_family(second_modelithics_inductor)
        assert info.value.args[0] == "The part library is not set to Modelithics"
        lumped_design.export_to_aedt.part_libraries = PartLibraries.MODELITHICS
        with pytest.raises(RuntimeError) as info:
            lumped_design.export_to_aedt.modelithics_inductor_family_list(0)
        assert info.value.args[0] == "The Modelithics inductor family at the given index is not available"
        lumped_design.export_to_aedt.modelithics_inductor_add_family(second_modelithics_inductor)
        lumped_design.export_to_aedt.modelithics_inductor_add_family(third_modelithics_inductor)
        assert lumped_design.export_to_aedt.modelithics_inductor_family_list(0) == second_modelithics_inductor
        assert lumped_design.export_to_aedt.modelithics_inductor_family_list(1) == third_modelithics_inductor

    @pytest.mark.skipif(config["skip_modelithics"], reason="Modelithics is not installed.")
    def test_modelithics_inductor_family_list_remove_family(self, lumped_design):
        with pytest.raises(RuntimeError) as info:
            lumped_design.export_to_aedt.modelithics_inductor_remove_family(second_modelithics_inductor)
        lumped_design.export_to_aedt.part_libraries = PartLibraries.MODELITHICS
        with pytest.raises(RuntimeError) as info:
            lumped_design.export_to_aedt.modelithics_inductor_family_list(0)
        assert info.value.args[0] == "The Modelithics inductor family at the given index is not available"
        lumped_design.export_to_aedt.modelithics_inductor_add_family(second_modelithics_inductor)
        lumped_design.export_to_aedt.modelithics_inductor_add_family(third_modelithics_inductor)
        assert lumped_design.export_to_aedt.modelithics_inductor_family_list_count == 2
        lumped_design.export_to_aedt.modelithics_inductor_remove_family(third_modelithics_inductor)
        assert lumped_design.export_to_aedt.modelithics_inductor_family_list_count == 1

    @pytest.mark.skipif(config["skip_modelithics"], reason="Modelithics is not installed.")
    def test_modelithics_capacitor_list_count(self, lumped_design):
        with pytest.raises(RuntimeError) as info:
            assert lumped_design.export_to_aedt.modelithics_capacitor_list_count == first_modelithics_capacitor
        assert info.value.args[0] == "The part library is not set to Modelithics"
        lumped_design.export_to_aedt.part_libraries = PartLibraries.MODELITHICS
        assert lumped_design.export_to_aedt.modelithics_capacitor_list_count == 143

    @pytest.mark.skipif(config["skip_modelithics"], reason="Modelithics is not installed.")
    def test_modelithics_capacitor_list(self, lumped_design):
        with pytest.raises(RuntimeError) as info:
            lumped_design.export_to_aedt.modelithics_capacitor_list(0)
        assert info.value.args[0] == "The part library is not set to Modelithics"
        lumped_design.export_to_aedt.part_libraries = PartLibraries.MODELITHICS
        with pytest.raises(RuntimeError) as info:
            lumped_design.export_to_aedt.modelithics_capacitor_list(-1)
        assert info.value.args[0] == "The Modelithics capacitor at the given index is not available"
        lumped_design.export_to_aedt.modelithics_capacitor_selection = first_modelithics_capacitor
        assert lumped_design.export_to_aedt.modelithics_capacitor_list(0) == first_modelithics_capacitor

    @pytest.mark.skipif(config["skip_modelithics"], reason="Modelithics is not installed.")
    def test_modelithics_capacitor_selection(self, lumped_design):
        with pytest.raises(RuntimeError) as info:
            lumped_design.export_to_aedt.modelithics_capacitor_selection = first_modelithics_capacitor
        assert info.value.args[0] == "The part library is not set to Modelithics"
        lumped_design.export_to_aedt.part_libraries = PartLibraries.MODELITHICS
        with pytest.raises(RuntimeError) as info:
            assert lumped_design.export_to_aedt.modelithics_capacitor_selection == first_modelithics_capacitor
        assert info.value.args[0] == "No Modelithics capacitor is selected"
        lumped_design.export_to_aedt.modelithics_capacitor_selection = first_modelithics_capacitor
        assert lumped_design.export_to_aedt.modelithics_capacitor_selection == first_modelithics_capacitor

    @pytest.mark.skipif(config["skip_modelithics"], reason="Modelithics is not installed.")
    def test_modelithics_capacitor_family_list_count(self, lumped_design):
        with pytest.raises(RuntimeError) as info:
            assert lumped_design.export_to_aedt.modelithics_capacitor_family_list_count == 2
        assert info.value.args[0] == "The part library is not set to Modelithics"
        lumped_design.export_to_aedt.part_libraries = PartLibraries.MODELITHICS
        assert lumped_design.export_to_aedt.modelithics_capacitor_family_list_count == 0
        lumped_design.export_to_aedt.modelithics_capacitor_add_family(first_modelithics_capacitor)
        assert lumped_design.export_to_aedt.modelithics_capacitor_family_list_count == 1
        lumped_design.export_to_aedt.modelithics_capacitor_add_family(second_modelithics_capacitor)
        assert lumped_design.export_to_aedt.modelithics_capacitor_family_list_count == 2

    @pytest.mark.skipif(config["skip_modelithics"], reason="Modelithics is not installed.")
    def test_modelithics_capacitor_family_list(self, lumped_design):
        with pytest.raises(RuntimeError) as info:
            lumped_design.export_to_aedt.modelithics_capacitor_family_list(0)
        assert info.value.args[0] == "The part library is not set to Modelithics"
        lumped_design.export_to_aedt.part_libraries = PartLibraries.MODELITHICS
        with pytest.raises(RuntimeError) as info:
            lumped_design.export_to_aedt.modelithics_capacitor_family_list(0)
        assert info.value.args[0] == "The Modelithics capacitor family at the given index is not available"
        lumped_design.export_to_aedt.modelithics_capacitor_add_family(first_modelithics_capacitor)
        lumped_design.export_to_aedt.modelithics_capacitor_add_family(second_modelithics_capacitor)
        assert lumped_design.export_to_aedt.modelithics_capacitor_family_list(0) == first_modelithics_capacitor
        assert lumped_design.export_to_aedt.modelithics_capacitor_family_list(1) == second_modelithics_capacitor

    @pytest.mark.skipif(config["skip_modelithics"], reason="Modelithics is not installed.")
    def test_modelithics_capacitor_family_list_add_family(self, lumped_design):
        with pytest.raises(RuntimeError) as info:
            lumped_design.export_to_aedt.modelithics_capacitor_add_family(first_modelithics_capacitor)
        assert info.value.args[0] == "The part library is not set to Modelithics"
        lumped_design.export_to_aedt.part_libraries = PartLibraries.MODELITHICS
        with pytest.raises(RuntimeError) as info:
            lumped_design.export_to_aedt.modelithics_capacitor_family_list(0)
        assert info.value.args[0] == "The Modelithics capacitor family at the given index is not available"
        lumped_design.export_to_aedt.modelithics_capacitor_add_family(first_modelithics_capacitor)
        lumped_design.export_to_aedt.modelithics_capacitor_add_family(second_modelithics_capacitor)
        assert lumped_design.export_to_aedt.modelithics_capacitor_family_list(0) == first_modelithics_capacitor
        assert lumped_design.export_to_aedt.modelithics_capacitor_family_list(1) == second_modelithics_capacitor

    @pytest.mark.skipif(config["skip_modelithics"], reason="Modelithics is not installed.")
    def test_modelithics_capacitor_family_list_remove_family(self, lumped_design):
        with pytest.raises(RuntimeError) as info:
            lumped_design.export_to_aedt.modelithics_capacitor_remove_family(second_modelithics_capacitor)
            assert info.value.args[0] == "The part library is not set to Modelithics"
        lumped_design.export_to_aedt.part_libraries = PartLibraries.MODELITHICS
        with pytest.raises(RuntimeError) as info:
            lumped_design.export_to_aedt.modelithics_capacitor_family_list(0)
        assert info.value.args[0] == "The Modelithics capacitor family at the given index is not available"
        lumped_design.export_to_aedt.modelithics_capacitor_add_family(first_modelithics_capacitor)
        lumped_design.export_to_aedt.modelithics_capacitor_add_family(second_modelithics_capacitor)
        assert lumped_design.export_to_aedt.modelithics_capacitor_family_list_count == 2
        lumped_design.export_to_aedt.modelithics_capacitor_remove_family(second_modelithics_capacitor)
        assert lumped_design.export_to_aedt.modelithics_capacitor_family_list_count == 1

    @pytest.mark.skipif(config["skip_modelithics"], reason="Modelithics is not installed.")
    def test_modelithics_resistor_list_count(self, lumped_design):
        with pytest.raises(RuntimeError) as info:
            assert lumped_design.export_to_aedt.modelithics_resistor_list_count == 2
        assert info.value.args[0] == "The part library is not set to Modelithics"
        lumped_design.export_to_aedt.part_libraries = PartLibraries.MODELITHICS
        assert lumped_design.export_to_aedt.modelithics_resistor_list_count == 39

    @pytest.mark.skipif(config["skip_modelithics"], reason="Modelithics is not installed.")
    def test_modelithics_resistor_list(self, lumped_design):
        with pytest.raises(RuntimeError) as info:
            lumped_design.export_to_aedt.modelithics_resistor_list(0)
        assert info.value.args[0] == "The part library is not set to Modelithics"
        lumped_design.export_to_aedt.part_libraries = PartLibraries.MODELITHICS
        with pytest.raises(RuntimeError) as info:
            lumped_design.export_to_aedt.modelithics_resistor_list(-1)
        assert info.value.args[0] == "The Modelithics resistor at the given index is not available"
        lumped_design.export_to_aedt.modelithics_resistor_selection = first_modelithics_resistor
        assert lumped_design.export_to_aedt.modelithics_resistor_list(0) == first_modelithics_resistor

    @pytest.mark.skipif(config["skip_modelithics"], reason="Modelithics is not installed.")
    def test_modelithics_resistor_selection(self, lumped_design):
        with pytest.raises(RuntimeError) as info:
            lumped_design.export_to_aedt.modelithics_resistor_selection = first_modelithics_resistor
        assert info.value.args[0] == "The part library is not set to Modelithics"
        lumped_design.export_to_aedt.part_libraries = PartLibraries.MODELITHICS
        with pytest.raises(RuntimeError) as info:
            assert lumped_design.export_to_aedt.modelithics_resistor_selection == first_modelithics_resistor
        assert info.value.args[0] == "No Modelithics resistor is selected"
        lumped_design.export_to_aedt.modelithics_resistor_selection = first_modelithics_resistor
        assert lumped_design.export_to_aedt.modelithics_resistor_selection == first_modelithics_resistor

    @pytest.mark.skipif(config["skip_modelithics"], reason="Modelithics is not installed.")
    def test_modelithics_resistor_family_list_count(self, lumped_design):
        with pytest.raises(RuntimeError) as info:
            assert lumped_design.export_to_aedt.modelithics_resistor_family_list_count == 2
        assert info.value.args[0] == "The part library is not set to Modelithics"
        lumped_design.export_to_aedt.part_libraries = PartLibraries.MODELITHICS
        assert lumped_design.export_to_aedt.modelithics_resistor_family_list_count == 0
        lumped_design.export_to_aedt.modelithics_resistor_add_family(first_modelithics_resistor)
        assert lumped_design.export_to_aedt.modelithics_resistor_family_list_count == 1
        lumped_design.export_to_aedt.modelithics_resistor_add_family(second_modelithics_resistor)
        assert lumped_design.export_to_aedt.modelithics_resistor_family_list_count == 2

    @pytest.mark.skipif(config["skip_modelithics"], reason="Modelithics is not installed.")
    def test_modelithics_resistor_family_list(self, lumped_design):
        with pytest.raises(RuntimeError) as info:
            lumped_design.export_to_aedt.modelithics_resistor_family_list(0)
        assert info.value.args[0] == "The part library is not set to Modelithics"
        lumped_design.export_to_aedt.part_libraries = PartLibraries.MODELITHICS
        with pytest.raises(RuntimeError) as info:
            lumped_design.export_to_aedt.modelithics_resistor_family_list(0)
        assert info.value.args[0] == "The Modelithics resistor family at the given index is not available"
        lumped_design.export_to_aedt.modelithics_resistor_add_family(first_modelithics_resistor)
        lumped_design.export_to_aedt.modelithics_resistor_add_family(second_modelithics_resistor)
        assert lumped_design.export_to_aedt.modelithics_resistor_family_list(0) == first_modelithics_resistor
        assert lumped_design.export_to_aedt.modelithics_resistor_family_list(1) == second_modelithics_resistor

    @pytest.mark.skipif(config["skip_modelithics"], reason="Modelithics is not installed.")
    def test_modelithics_resistor_family_list_add_family(self, lumped_design):
        with pytest.raises(RuntimeError) as info:
            lumped_design.export_to_aedt.modelithics_resistor_add_family(first_modelithics_resistor)
        assert info.value.args[0] == "The part library is not set to Modelithics"
        lumped_design.export_to_aedt.part_libraries = PartLibraries.MODELITHICS
        with pytest.raises(RuntimeError) as info:
            lumped_design.export_to_aedt.modelithics_resistor_family_list(0)
        assert info.value.args[0] == "The Modelithics resistor family at the given index is not available"
        lumped_design.export_to_aedt.modelithics_resistor_add_family(first_modelithics_resistor)
        lumped_design.export_to_aedt.modelithics_resistor_add_family(second_modelithics_resistor)
        assert lumped_design.export_to_aedt.modelithics_resistor_family_list(0) == first_modelithics_resistor
        assert lumped_design.export_to_aedt.modelithics_resistor_family_list(1) == second_modelithics_resistor

    @pytest.mark.skipif(config["skip_modelithics"], reason="Modelithics is not installed.")
    def test_modelithics_resistor_family_list_remove_family(self, lumped_design):
        with pytest.raises(RuntimeError) as info:
            lumped_design.export_to_aedt.modelithics_resistor_remove_family(second_modelithics_resistor)
        assert info.value.args[0] == "The part library is not set to Modelithics"
        lumped_design.export_to_aedt.part_libraries = PartLibraries.MODELITHICS
        with pytest.raises(RuntimeError) as info:
            lumped_design.export_to_aedt.modelithics_resistor_family_list(0)
        assert info.value.args[0] == "The Modelithics resistor family at the given index is not available"
        lumped_design.export_to_aedt.modelithics_resistor_add_family(first_modelithics_resistor)
        lumped_design.export_to_aedt.modelithics_resistor_add_family(second_modelithics_resistor)
        assert lumped_design.export_to_aedt.modelithics_resistor_family_list_count == 2
        lumped_design.export_to_aedt.modelithics_resistor_remove_family(second_modelithics_resistor)
        assert lumped_design.export_to_aedt.modelithics_resistor_family_list_count == 1

    def test_schematic_name(self, lumped_design):
        lumped_design.export_to_aedt.schematic_name = "my_schematic"
        assert lumped_design.export_to_aedt.schematic_name == "my_schematic"

    def test_simulate_after_export_enabled(self, lumped_design):
        assert lumped_design.export_to_aedt.simulate_after_export_enabled == False
        lumped_design.export_to_aedt.simulate_after_export_enabled = True
        assert lumped_design.export_to_aedt.simulate_after_export_enabled == True

    def test_include_group_delay_enabled(self, lumped_design):
        assert lumped_design.export_to_aedt.include_group_delay_enabled == False
        lumped_design.export_to_aedt.include_group_delay_enabled = True
        assert lumped_design.export_to_aedt.include_group_delay_enabled == True

    def test_include_gt_gain_enabled(self, lumped_design):
        assert lumped_design.export_to_aedt.include_gt_gain_enabled == False
        lumped_design.export_to_aedt.include_gt_gain_enabled = True
        assert lumped_design.export_to_aedt.include_gt_gain_enabled == True

    def test_include_vgsl_enabled(self, lumped_design):
        assert lumped_design.export_to_aedt.include_vgsl_enabled == False
        lumped_design.export_to_aedt.include_vgsl_enabled = True
        assert lumped_design.export_to_aedt.include_vgsl_enabled == True

    def test_include_vgin_enabled(self, lumped_design):
        assert lumped_design.export_to_aedt.include_vgin_enabled == False
        lumped_design.export_to_aedt.include_vgin_enabled = True
        assert lumped_design.export_to_aedt.include_vgin_enabled == True

    def test_include_input_return_loss_s11_enabled(self, lumped_design):
        assert lumped_design.export_to_aedt.include_input_return_loss_s11_enabled == True
        lumped_design.export_to_aedt.include_input_return_loss_s11_enabled = False
        assert lumped_design.export_to_aedt.include_input_return_loss_s11_enabled == False

    def test_include_forward_transfer_s21_enabled(self, lumped_design):
        assert lumped_design.export_to_aedt.include_forward_transfer_s21_enabled == True
        lumped_design.export_to_aedt.include_forward_transfer_s21_enabled = False
        assert lumped_design.export_to_aedt.include_forward_transfer_s21_enabled == False

    def test_include_reverse_transfer_s12_enabled(self, lumped_design):
        assert lumped_design.export_to_aedt.include_reverse_transfer_s12_enabled == False
        lumped_design.export_to_aedt.include_reverse_transfer_s12_enabled = True
        assert lumped_design.export_to_aedt.include_reverse_transfer_s12_enabled == True

    def test_include_output_return_loss_s22_enabled(self, lumped_design):
        assert lumped_design.export_to_aedt.include_output_return_loss_s22_enabled == False
        lumped_design.export_to_aedt.include_output_return_loss_s22_enabled = True
        assert lumped_design.export_to_aedt.include_output_return_loss_s22_enabled == True

    def test_db_format_enabled(self, lumped_design):
        assert lumped_design.export_to_aedt.db_format_enabled == True
        lumped_design.export_to_aedt.db_format_enabled = False
        assert lumped_design.export_to_aedt.db_format_enabled == False

    def test_rectangular_plot_enabled(self, lumped_design):
        assert lumped_design.export_to_aedt.rectangular_plot_enabled == True
        lumped_design.export_to_aedt.rectangular_plot_enabled = False
        assert lumped_design.export_to_aedt.rectangular_plot_enabled == False

    def test_smith_plot_enabled(self, lumped_design):
        assert lumped_design.export_to_aedt.smith_plot_enabled == False
        lumped_design.export_to_aedt.smith_plot_enabled = True
        assert lumped_design.export_to_aedt.smith_plot_enabled == True

    def test_polar_plot_enabled(self, lumped_design):
        assert lumped_design.export_to_aedt.polar_plot_enabled == False
        lumped_design.export_to_aedt.polar_plot_enabled = True
        assert lumped_design.export_to_aedt.polar_plot_enabled == True

    def test_table_data_enabled(self, lumped_design):
        assert lumped_design.export_to_aedt.table_data_enabled == False
        lumped_design.export_to_aedt.table_data_enabled = True
        assert lumped_design.export_to_aedt.table_data_enabled == True

    def test_optimitrics_enabled(self, lumped_design):
        assert lumped_design.export_to_aedt.optimitrics_enabled == True
        lumped_design.export_to_aedt.optimitrics_enabled = False
        assert lumped_design.export_to_aedt.optimitrics_enabled == False

    def test_optimize_after_export_enabled(self, lumped_design):
        assert lumped_design.export_to_aedt.optimize_after_export_enabled == False
        lumped_design.export_to_aedt.optimize_after_export_enabled = True
        assert lumped_design.export_to_aedt.optimize_after_export_enabled == True

    def test_export_design(self, lumped_design):
        export_path = resource_path("Test_Export/test_exported_design.py")
        lumped_design.export_to_aedt.export_design(
            export_format=ExportFormat.PYTHON_SCRIPT,
            export_creation_mode=ExportCreationMode.OVERWRITE,
            export_path=export_path,
        )
        assert os.path.exists(export_path)
        directory_path = os.path.dirname(export_path)
        assert os.path.exists(directory_path)
        os.remove(export_path)
        os.rmdir(directory_path)

    def test_load_library_parts_config(self, lumped_design):
        lumped_design.export_to_aedt.load_library_parts_config(resource_path("library_parts.cfg"))
        lumped_design.export_to_aedt.part_libraries = PartLibraries.INTERCONNECT
        assert lumped_design.export_to_aedt.substrate_er == SubstrateEr.ALUMINA
        assert lumped_design.export_to_aedt.substrate_resistivity == SubstrateResistivity.GOLD
        assert lumped_design.export_to_aedt.substrate_conductor_thickness == "2.54 um"
        assert lumped_design.export_to_aedt.substrate_dielectric_height == "1.27 mm"
        assert lumped_design.export_to_aedt.substrate_loss_tangent == SubstrateEr.ALUMINA

    def test_save_library_parts_config(self, lumped_design):
        lumped_design.export_to_aedt.part_libraries = PartLibraries.INTERCONNECT
        lumped_design.export_to_aedt.substrate_er = "2.25"
        lumped_design.export_to_aedt.substrate_resistivity = "4.2E+07 "
        lumped_design.export_to_aedt.substrate_conductor_thickness = "350 nm"
        lumped_design.export_to_aedt.substrate_dielectric_height = "3 mm"
        lumped_design.export_to_aedt.substrate_loss_tangent = "0.065 "
        lumped_design.export_to_aedt.save_library_parts_config(resource_path("library_parts_test.cfg"))
        lumped_design.export_to_aedt.load_library_parts_config(resource_path("library_parts_test.cfg"))
        assert lumped_design.export_to_aedt.part_libraries == PartLibraries.INTERCONNECT
        assert lumped_design.export_to_aedt.substrate_er == "2.25"
        assert lumped_design.export_to_aedt.substrate_resistivity == "4.2E+07 "
        assert lumped_design.export_to_aedt.substrate_conductor_thickness == "350 nm"
        assert lumped_design.export_to_aedt.substrate_dielectric_height == "3 mm"
        assert lumped_design.export_to_aedt.substrate_loss_tangent == "0.065 "

    def test_import_tuned_variables(self, lumped_design):
        lumped_design.export_to_aedt.simulate_after_export_enabled = True
        lumped_design.export_to_aedt.optimize_after_export_enabled = True
        lumped_design.export_to_aedt.part_libraries = PartLibraries.LUMPED
        lumped_design.export_to_aedt.export_design()
        assert lumped_design.export_to_aedt.import_tuned_variables().splitlines() == read_resource_file(
            "imported_netlist.ckt", "Lumped"
        )

    def test_part_libraries(self, lumped_design):
        assert lumped_design.export_to_aedt.part_libraries == PartLibraries.LUMPED
        assert len(PartLibraries) == 3
        lumped_design.export_to_aedt.part_libraries = PartLibraries.INTERCONNECT
        assert lumped_design.export_to_aedt.part_libraries == PartLibraries.INTERCONNECT

    def test_interconnect_length_to_width_ratio(self, lumped_design):
        assert lumped_design.export_to_aedt.interconnect_length_to_width_ratio == "2"
        lumped_design.export_to_aedt.interconnect_length_to_width_ratio = "3"
        assert lumped_design.export_to_aedt.interconnect_length_to_width_ratio == "3"

    def test_interconnect_minimum_length_to_width_ratio(self, lumped_design):
        assert lumped_design.export_to_aedt.interconnect_minimum_length_to_width_ratio == "0.5"
        lumped_design.export_to_aedt.interconnect_minimum_length_to_width_ratio = "0.6"
        assert lumped_design.export_to_aedt.interconnect_minimum_length_to_width_ratio == "0.6"

    def test_interconnect_maximum_length_to_width_ratio(self, lumped_design):
        assert lumped_design.export_to_aedt.interconnect_maximum_length_to_width_ratio == "2"
        lumped_design.export_to_aedt.interconnect_maximum_length_to_width_ratio = "3"
        assert lumped_design.export_to_aedt.interconnect_maximum_length_to_width_ratio == "3"

    def test_interconnect_line_to_termination_width_ratio(self, lumped_design):
        assert lumped_design.export_to_aedt.interconnect_line_to_termination_width_ratio == "1"
        lumped_design.export_to_aedt.interconnect_line_to_termination_width_ratio = "2"
        assert lumped_design.export_to_aedt.interconnect_line_to_termination_width_ratio == "2"

    def test_interconnect_minimum_line_to_termination_width_ratio(self, lumped_design):
        assert lumped_design.export_to_aedt.interconnect_minimum_line_to_termination_width_ratio == "0.5"
        lumped_design.export_to_aedt.interconnect_minimum_line_to_termination_width_ratio = "0.6"
        assert lumped_design.export_to_aedt.interconnect_minimum_line_to_termination_width_ratio == "0.6"

    def test_interconnect_maximum_line_to_termination_width_ratio(self, lumped_design):
        assert lumped_design.export_to_aedt.interconnect_maximum_line_to_termination_width_ratio == "2"
        lumped_design.export_to_aedt.interconnect_maximum_line_to_termination_width_ratio = "3"
        assert lumped_design.export_to_aedt.interconnect_maximum_line_to_termination_width_ratio == "3"

    def test_interconnect_length_value(self, lumped_design):
        assert lumped_design.export_to_aedt.interconnect_length_value == "2.54 mm"
        lumped_design.export_to_aedt.interconnect_length_value = "3 mm"
        assert lumped_design.export_to_aedt.interconnect_length_value == "3 mm"

    def test_interconnect_minimum_length_value(self, lumped_design):
        assert lumped_design.export_to_aedt.interconnect_minimum_length_value == "1.27 mm"
        lumped_design.export_to_aedt.interconnect_minimum_length_value = "0.6 mm"
        assert lumped_design.export_to_aedt.interconnect_minimum_length_value == "0.6 mm"

    def test_interconnect_maximum_length_value(self, lumped_design):
        assert lumped_design.export_to_aedt.interconnect_maximum_length_value == "5.08 mm"
        lumped_design.export_to_aedt.interconnect_maximum_length_value = "6 mm"
        assert lumped_design.export_to_aedt.interconnect_maximum_length_value == "6 mm"

    def test_interconnect_line_width_value(self, lumped_design):
        assert lumped_design.export_to_aedt.interconnect_line_width_value == "1.27 mm"
        lumped_design.export_to_aedt.interconnect_line_width_value = "2 mm"
        assert lumped_design.export_to_aedt.interconnect_line_width_value == "2 mm"

    def test_interconnect_minimum_width_value(self, lumped_design):
        assert lumped_design.export_to_aedt.interconnect_minimum_width_value == "635 um"
        lumped_design.export_to_aedt.interconnect_minimum_width_value = "725 um"
        assert lumped_design.export_to_aedt.interconnect_minimum_width_value == "725 um"

    def test_interconnect_maximum_width_value(self, lumped_design):
        assert lumped_design.export_to_aedt.interconnect_maximum_width_value == "2.54 mm"
        lumped_design.export_to_aedt.interconnect_maximum_width_value = "3 mm"
        assert lumped_design.export_to_aedt.interconnect_maximum_width_value == "3 mm"

    def test_interconnect_inductor_tolerance_value(self, lumped_design):
        lumped_design.export_to_aedt.part_libraries = PartLibraries.INTERCONNECT
        assert lumped_design.export_to_aedt.interconnect_inductor_tolerance_value == "1"
        lumped_design.export_to_aedt.interconnect_inductor_tolerance_value = "10"
        assert lumped_design.export_to_aedt.interconnect_inductor_tolerance_value == "10"

    def test_interconnect_capacitor_tolerance_value(self, lumped_design):
        lumped_design.export_to_aedt.part_libraries = PartLibraries.INTERCONNECT
        assert lumped_design.export_to_aedt.interconnect_capacitor_tolerance_value == "1"
        lumped_design.export_to_aedt.interconnect_capacitor_tolerance_value = "10"
        assert lumped_design.export_to_aedt.interconnect_capacitor_tolerance_value == "10"

    def test_interconnect_geometry_optimization_enabled(self, lumped_design):
        assert lumped_design.export_to_aedt.interconnect_geometry_optimization_enabled == True
        lumped_design.export_to_aedt.interconnect_geometry_optimization_enabled = False
        assert lumped_design.export_to_aedt.interconnect_geometry_optimization_enabled == False

    def test_substrate_type(self, lumped_design):
        assert lumped_design.export_to_aedt.substrate_type == SubstrateType.MICROSTRIP
        assert len(SubstrateType) == 5
        for substrate in SubstrateType:
            lumped_design.export_to_aedt.substrate_type = substrate
            assert lumped_design.export_to_aedt.substrate_type == substrate

    def test_substrate_er(self, lumped_design):
        assert lumped_design.export_to_aedt.substrate_er == SubstrateEr.ALUMINA
        assert len(SubstrateEr) == 17
        with pytest.raises(ValueError) as info:
            lumped_design.export_to_aedt.substrate_er = 3.2
        assert str(info.value) == "Invalid substrate input. Must be a SubstrateEr enum member or a string."
        for er in SubstrateEr:
            lumped_design.export_to_aedt.substrate_er = er
            assert lumped_design.export_to_aedt.substrate_er == er
        lumped_design.export_to_aedt.substrate_er = "3.2"
        assert lumped_design.export_to_aedt.substrate_er == "3.2"

    def test_substrate_resistivity(self, lumped_design):
        assert lumped_design.export_to_aedt.substrate_resistivity == SubstrateResistivity.GOLD
        assert len(SubstrateResistivity) == 11
        with pytest.raises(ValueError) as info:
            lumped_design.export_to_aedt.substrate_resistivity = 0.02
        assert str(info.value) == "Invalid substrate input. Must be a SubstrateResistivity enum member or a string."
        for resistivity in SubstrateResistivity:
            lumped_design.export_to_aedt.substrate_resistivity = resistivity
            assert lumped_design.export_to_aedt.substrate_resistivity == resistivity
        lumped_design.export_to_aedt.substrate_resistivity = "0.02"
        assert lumped_design.export_to_aedt.substrate_resistivity == "0.02"

    def test_substrate_loss_tangent(self, lumped_design):
        assert lumped_design.export_to_aedt.substrate_loss_tangent == SubstrateEr.ALUMINA
        assert len(SubstrateEr) == 17
        for loss in SubstrateEr:
            lumped_design.export_to_aedt.substrate_loss_tangent = loss
            assert lumped_design.export_to_aedt.substrate_loss_tangent == loss
        lumped_design.export_to_aedt.substrate_loss_tangent = "0.0002"
        assert lumped_design.export_to_aedt.substrate_loss_tangent == "0.0002"

    def test_substrate_loss_tangent_invalid_input(self, lumped_design):
        with pytest.raises(ValueError) as info:
            lumped_design.export_to_aedt.substrate_loss_tangent = 0.0002
        assert str(info.value) == "Invalid substrate input. Must be a SubstrateEr enum member or a string."

    def test_substrate_conductor_thickness(self, lumped_design):
        assert lumped_design.export_to_aedt.substrate_conductor_thickness == "2.54 um"
        lumped_design.export_to_aedt.substrate_conductor_thickness = "1.25 um"
        assert lumped_design.export_to_aedt.substrate_conductor_thickness == "1.25 um"

    def test_substrate_dielectric_height(self, lumped_design):
        assert lumped_design.export_to_aedt.substrate_dielectric_height == "1.27 mm"
        lumped_design.export_to_aedt.substrate_dielectric_height = "1.22 mm"
        assert lumped_design.export_to_aedt.substrate_dielectric_height == "1.22 mm"

    def test_substrate_unbalanced_lower_dielectric_height(self, lumped_design):
        lumped_design.export_to_aedt.substrate_type = SubstrateType.STRIPLINE
        lumped_design.export_to_aedt.substrate_unbalanced_stripline_enabled = True
        assert lumped_design.export_to_aedt.substrate_unbalanced_lower_dielectric_height == "6.35 mm"
        lumped_design.export_to_aedt.substrate_unbalanced_lower_dielectric_height = "5.2 mm"
        assert lumped_design.export_to_aedt.substrate_unbalanced_lower_dielectric_height == "5.2 mm"

    def test_substrate_suspend_dielectric_height(self, lumped_design):
        lumped_design.export_to_aedt.substrate_type = SubstrateType.SUSPEND
        assert lumped_design.export_to_aedt.substrate_suspend_dielectric_height == "1.27 mm"
        lumped_design.export_to_aedt.substrate_suspend_dielectric_height = "3.2 mm"
        assert lumped_design.export_to_aedt.substrate_suspend_dielectric_height == "3.2 mm"

    def test_substrate_cover_height(self, lumped_design):
        lumped_design.export_to_aedt.substrate_cover_height_enabled = True
        assert lumped_design.export_to_aedt.substrate_cover_height == "6.35 mm"
        lumped_design.export_to_aedt.substrate_cover_height = "2.5 mm"
        assert lumped_design.export_to_aedt.substrate_cover_height == "2.5 mm"

    @pytest.mark.skipif(config["skip_modelithics"], reason="Modelithics is not installed.")
    def test_load_modelithics_models(self, lumped_design):
        with pytest.raises(RuntimeError) as info:
            lumped_design.export_to_aedt.load_modelithics_models()
        assert info.value.args[0] == "The part library is not set to Modelithics"

    def test_substrate_unbalanced_stripline_enabled(self, lumped_design):
        lumped_design.export_to_aedt.substrate_type = SubstrateType.STRIPLINE
        assert lumped_design.export_to_aedt.substrate_unbalanced_stripline_enabled == False
        lumped_design.export_to_aedt.substrate_unbalanced_stripline_enabled = True
        assert lumped_design.export_to_aedt.substrate_unbalanced_stripline_enabled == True

    def test_substrate_cover_height_enabled(self, lumped_design):
        assert lumped_design.export_to_aedt.substrate_cover_height_enabled == False
        lumped_design.export_to_aedt.substrate_cover_height_enabled = True
        assert lumped_design.export_to_aedt.substrate_cover_height_enabled == True

    def test_insert_circuit_design(self, distributed_design):
        assert distributed_design.export_to_aedt.insert_circuit_design is False
        distributed_design.export_to_aedt.insert_circuit_design = True
        assert distributed_design.export_to_aedt.insert_circuit_design

    def test_insert_hfss_design(self, distributed_design):
        assert distributed_design.export_to_aedt.insert_hfss_design is False
        distributed_design.export_to_aedt.insert_hfss_design = True
        assert distributed_design.export_to_aedt.insert_hfss_design

    def test_insert_hfss_3dl_design(self, distributed_design):
        assert distributed_design.export_to_aedt.insert_hfss_3dl_design
        distributed_design.export_to_aedt.insert_hfss_3dl_design = False
        assert distributed_design.export_to_aedt.insert_hfss_3dl_design is False

    def test_full_parametrization_enabled(self, distributed_design):
        assert distributed_design.export_to_aedt.full_parametrization_enabled
        distributed_design.export_to_aedt.full_parametrization_enabled = False
        assert distributed_design.export_to_aedt.full_parametrization_enabled is False

    def test_ports_always_on_sides_enabled(self, distributed_design):
        assert distributed_design.export_to_aedt.ports_always_on_sides_enabled is False
        distributed_design.export_to_aedt.ports_always_on_sides_enabled = True
        assert distributed_design.export_to_aedt.ports_always_on_sides_enabled

    def test_reverse_x_axis_enabled(self, distributed_design):
        assert distributed_design.export_to_aedt.reverse_x_axis_enabled is False
        distributed_design.export_to_aedt.reverse_x_axis_enabled = True
        assert distributed_design.export_to_aedt.reverse_x_axis_enabled

    def test_reverse_y_axis_enabled(self, distributed_design):
        assert distributed_design.export_to_aedt.reverse_y_axis_enabled is False
        distributed_design.export_to_aedt.reverse_y_axis_enabled = True
        assert distributed_design.export_to_aedt.reverse_y_axis_enabled

    def test_export_with_tuning_port_format_enabled(self, distributed_design):
        assert distributed_design.export_to_aedt.export_with_tuning_port_format_enabled is False
        distributed_design.export_to_aedt.export_with_tuning_port_format_enabled = True
        assert distributed_design.export_to_aedt.export_with_tuning_port_format_enabled

    def test_use_series_horizontal_ports_enabled(self, distributed_design):
        assert distributed_design.export_to_aedt.use_series_horizontal_ports_enabled
        distributed_design.export_to_aedt.use_series_horizontal_ports_enabled = False
        assert distributed_design.export_to_aedt.use_series_horizontal_ports_enabled is False
