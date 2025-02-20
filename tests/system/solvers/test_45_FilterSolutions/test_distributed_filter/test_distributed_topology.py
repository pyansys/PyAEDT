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

from ansys.aedt.core.filtersolutions_core.attributes import FilterClass
from ansys.aedt.core.filtersolutions_core.attributes import FilterType
from ansys.aedt.core.filtersolutions_core.distributed_topology import TapPosition
from ansys.aedt.core.filtersolutions_core.distributed_topology import TopologyType
from ansys.aedt.core.generic.settings import is_linux
import pytest

from tests.system.solvers.conftest import config

from ..resources import read_resource_file


def convert_string(input_string) -> str:
    """
    Convert a string to have all words capitalized.

    Parameters
    ----------
    input_string: str
        String to modify.

    Returns
    -------
    str
        String with all words capitalized.
    """
    fixed_string = input_string.replace("_", " ").lower()
    return " ".join(word.capitalize() for word in fixed_string.split())


@pytest.mark.skipif(is_linux, reason="FilterSolutions API is not applicable on Linux.")
@pytest.mark.skipif(config["desktopVersion"] < "2025.2", reason="Skipped on versions earlier than 2025.2")
class TestClass:

    def test_distributed_source_resistance_30(self, distributed_design):
        assert distributed_design.topology.source_resistance == "50"
        distributed_design.topology.source_resistance = "30"
        assert distributed_design.topology.source_resistance == "30"
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "source_resistance.ckt", "Distributed"
        )

    def test_distributed_load_resistance_30(self, distributed_design):
        assert distributed_design.topology.load_resistance == "50"
        distributed_design.topology.load_resistance = "30"
        assert distributed_design.topology.load_resistance == "30"
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "load_resistance.ckt", "Distributed"
        )

    def test_distributed_first_shunt(self, distributed_design):
        assert distributed_design.topology.first_shunt
        with pytest.raises(RuntimeError) as info:
            distributed_design.topology.topology_type = TopologyType.SPACED_STUBS
            distributed_design.topology.first_shunt = False
        assert (
            info.value.args[0]
            == "The First Element Shunt or Series property is not applicable to the "
            + convert_string(distributed_design.topology.topology_type.name)
            + " topology"
        )
        distributed_design.topology.topology_type = TopologyType.LUMPED_TRANSLATION
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "first_shunt.ckt", "Distributed"
        )
        distributed_design.topology.first_shunt = False
        assert distributed_design.topology.first_shunt is False
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "first_series.ckt", "Distributed"
        )

    def test_distributed_first_fat(self, distributed_design):
        with pytest.raises(RuntimeError) as info:
            distributed_design.topology.first_fat = True
        assert (
            info.value.args[0]
            == "The First Element Fat or Thin property is not applicable to the "
            + convert_string(distributed_design.topology.topology_type.name)
            + " topology"
        )
        distributed_design.topology.topology_type = TopologyType.STEPPED_IMPEDANCE
        assert distributed_design.topology.first_fat
        assert distributed_design.topology.netlist().splitlines() == read_resource_file("first_fat.ckt", "Distributed")
        distributed_design.topology.first_fat = False
        assert distributed_design.topology.first_fat is False
        assert distributed_design.topology.netlist().splitlines() == read_resource_file("first_thin.ckt", "Distributed")

    def test_distributed_use_series_caps(self, distributed_design):
        with pytest.raises(RuntimeError) as info:
            distributed_design.topology.use_series_caps = True
        assert (
            info.value.args[0]
            == "The Series Caps property is not applicable to the "
            + convert_string(distributed_design.topology.topology_type.name)
            + " topology"
        )
        distributed_design.attributes.filter_class = FilterClass.BAND_PASS
        assert distributed_design.topology.use_series_caps is False
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "use_series_caps_false.ckt", "Distributed"
        )
        distributed_design.topology.use_series_caps = True
        assert distributed_design.topology.use_series_caps
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "use_series_caps_true.ckt", "Distributed"
        )

    def test_distributed_combine_stubs(self, distributed_design):
        with pytest.raises(RuntimeError) as info:
            distributed_design.topology.combine_stubs = True
        assert (
            info.value.args[0]
            == "The Combine Stubs property is not applicable to the "
            + convert_string(distributed_design.topology.topology_type.name)
            + " topology"
        )
        distributed_design.attributes.filter_class = FilterClass.BAND_PASS
        assert distributed_design.topology.combine_stubs is False
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "combine_stubs_false.ckt", "Distributed"
        )
        distributed_design.topology.combine_stubs = True
        assert distributed_design.topology.combine_stubs
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "combine_stubs_true.ckt", "Distributed"
        )

    def test_use_coupled_lines(self, distributed_design):
        with pytest.raises(RuntimeError) as info:
            distributed_design.topology.use_coupled_lines = True
        assert (
            info.value.args[0]
            == "The Coupled Lines property is not applicable to the "
            + convert_string(distributed_design.topology.topology_type.name)
            + " topology"
        )
        distributed_design.attributes.filter_class = FilterClass.BAND_PASS
        distributed_design.attributes.filter_type = FilterType.ELLIPTIC
        assert distributed_design.topology.use_coupled_lines is False
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "use_coupled_lines_false.ckt", "Distributed"
        )
        distributed_design.topology.use_coupled_lines = True
        assert distributed_design.topology.use_coupled_lines
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "use_coupled_lines_true.ckt", "Distributed"
        )

    def test_equal_width_approx(self, distributed_design):
        with pytest.raises(RuntimeError) as info:
            distributed_design.topology.equal_width_approx = True
        assert (
            info.value.args[0]
            == "The Equal Width property is not applicable to the "
            + convert_string(distributed_design.topology.topology_type.name)
            + " topology"
        )
        distributed_design.attributes.filter_class = FilterClass.BAND_PASS
        distributed_design.topology.topology_type = TopologyType.INTERDIGITAL
        assert distributed_design.topology.equal_width_approx
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "equal_width_approx_true.ckt", "Distributed"
        )
        distributed_design.topology.equal_width_approx = False
        assert distributed_design.topology.equal_width_approx is False
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "equal_width_approx_false.ckt", "Distributed"
        )

    def test_open_stub_ground(self, distributed_design):
        with pytest.raises(RuntimeError) as info:
            distributed_design.topology.open_stub_ground = True
        assert (
            info.value.args[0]
            == "The Open Stub Ground property is not applicable to the "
            + convert_string(distributed_design.topology.topology_type.name)
            + " topology"
        )
        distributed_design.attributes.filter_class = FilterClass.BAND_STOP
        distributed_design.topology.topology_type = TopologyType.NOTCH_RESONATORS
        assert distributed_design.topology.open_stub_ground is False
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "open_stub_ground_false.ckt", "Distributed"
        )
        distributed_design.topology.open_stub_ground = True
        assert distributed_design.topology.open_stub_ground
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "open_stub_ground_true.ckt", "Distributed"
        )

    def test_left_ground_side(self, distributed_design):
        with pytest.raises(RuntimeError) as info:
            distributed_design.topology.left_ground_side = True
        assert (
            info.value.args[0]
            == "The Left Ground Side property is not applicable to the "
            + convert_string(distributed_design.topology.topology_type.name)
            + " topology"
        )
        distributed_design.attributes.filter_class = FilterClass.BAND_STOP
        distributed_design.topology.topology_type = TopologyType.NOTCH_RESONATORS
        assert distributed_design.topology.left_ground_side
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "left_ground_side.ckt", "Distributed"
        )
        distributed_design.topology.left_ground_side = False
        assert distributed_design.topology.left_ground_side is False
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "right_ground_side.ckt", "Distributed"
        )

    def test_equal_stub_widths(self, distributed_design):
        with pytest.raises(RuntimeError) as info:
            distributed_design.topology.equal_stub_widths = True
        assert (
            info.value.args[0]
            == "The Equal Stub Widths property is not applicable to the "
            + convert_string(distributed_design.topology.topology_type.name)
            + " topology"
        )
        distributed_design.attributes.filter_class = FilterClass.BAND_PASS
        distributed_design.topology.topology_type = TopologyType.SHUNT_STUB_RESONATORS
        assert distributed_design.topology.equal_stub_widths is False
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "equal_stub_widths_false.ckt", "Distributed"
        )
        distributed_design.topology.equal_stub_widths = True
        assert distributed_design.topology.equal_stub_widths
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "equal_stub_widths_true.ckt", "Distributed"
        )

    def test_center_z0_impedance_55(self, distributed_design):
        with pytest.raises(RuntimeError) as info:
            distributed_design.topology.center_z0_impedance = "55"
        assert (
            info.value.args[0]
            == "The Center Z0 property is not applicable to the "
            + convert_string(distributed_design.topology.topology_type.name)
            + " topology"
        )
        distributed_design.attributes.filter_class = FilterClass.BAND_PASS
        distributed_design.topology.topology_type = TopologyType.SHUNT_STUB_RESONATORS
        distributed_design.topology.equal_stub_widths = False
        assert distributed_design.topology.center_z0_impedance == "75"
        distributed_design.topology.center_z0_impedance = "55"
        assert distributed_design.topology.center_z0_impedance == "55"
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "center_z0_impedance.ckt", "Distributed"
        )

    def test_equal_width_conductors(self, distributed_design):
        with pytest.raises(RuntimeError) as info:
            distributed_design.topology.equal_width_conductors = True
        assert (
            info.value.args[0]
            == "The Equal Width property is not applicable to the "
            + convert_string(distributed_design.topology.topology_type.name)
            + " topology"
        )
        distributed_design.attributes.filter_class = FilterClass.BAND_PASS
        distributed_design.topology.topology_type = TopologyType.PARALLEL_EDGE_COUPLED
        assert distributed_design.topology.equal_width_conductors
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "equal_width_conductors_true.ckt", "Distributed"
        )
        distributed_design.topology.equal_width_conductors = False
        assert distributed_design.topology.equal_width_conductors is False
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "equal_width_conductors_false.ckt", "Distributed"
        )

    def test_tapped(self, distributed_design):
        with pytest.raises(RuntimeError) as info:
            distributed_design.topology.tapped = True
        assert (
            info.value.args[0]
            == "The Tapped property is not applicable to the "
            + convert_string(distributed_design.topology.topology_type.name)
            + " topology"
        )
        distributed_design.attributes.filter_class = FilterClass.BAND_PASS
        distributed_design.topology.topology_type = TopologyType.PARALLEL_EDGE_COUPLED
        assert distributed_design.topology.tapped
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "tapped_true.ckt", "Distributed"
        )
        distributed_design.topology.tapped = False
        assert distributed_design.topology.tapped is False
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "tapped_false.ckt", "Distributed"
        )

    def test_pinned(self, distributed_design):
        with pytest.raises(RuntimeError) as info:
            distributed_design.topology.pinned = True
        assert (
            info.value.args[0]
            == "The Pinned property is not applicable to the "
            + convert_string(distributed_design.topology.topology_type.name)
            + " topology"
        )
        distributed_design.attributes.filter_class = FilterClass.BAND_PASS
        distributed_design.topology.topology_type = TopologyType.INTERDIGITAL
        with pytest.raises(RuntimeError) as info:
            distributed_design.topology.pinned = True
        assert info.value.args[0] == "The Pinned property is only available for Interdigital wideband filters"
        distributed_design.topology.topology_type = TopologyType.PARALLEL_EDGE_COUPLED
        assert distributed_design.topology.pinned is False
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "pinned_false.ckt", "Distributed"
        )
        distributed_design.topology.pinned = True
        assert distributed_design.topology.pinned
        # Check if the equal width conductors property is set to False when the pinned property is set to True
        assert distributed_design.topology.equal_width_conductors is False
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "pinned_true.ckt", "Distributed"
        )

    def test_stub_taps(self, distributed_design):
        with pytest.raises(RuntimeError) as info:
            distributed_design.topology.stub_taps = True
        assert (
            info.value.args[0]
            == "The Stub Taps property is not applicable to the "
            + convert_string(distributed_design.topology.topology_type.name)
            + " topology"
        )
        distributed_design.attributes.filter_class = FilterClass.BAND_PASS
        distributed_design.topology.topology_type = TopologyType.PARALLEL_EDGE_COUPLED
        assert distributed_design.topology.stub_taps is False
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "stub_taps_false.ckt", "Distributed"
        )
        distributed_design.topology.stub_taps = True
        assert distributed_design.topology.stub_taps
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "stub_taps_true.ckt", "Distributed"
        )

    def test_via_ends(self, distributed_design):
        with pytest.raises(RuntimeError) as info:
            distributed_design.topology.via_ends = True
        assert (
            info.value.args[0]
            == "The Via Ends property is not applicable to the "
            + convert_string(distributed_design.topology.topology_type.name)
            + " topology"
        )
        distributed_design.attributes.filter_class = FilterClass.BAND_PASS
        distributed_design.topology.topology_type = TopologyType.PARALLEL_EDGE_COUPLED
        assert distributed_design.topology.via_ends is False
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "via_ends_false.ckt", "Distributed"
        )
        distributed_design.topology.via_ends = True
        assert distributed_design.topology.via_ends
        # Check if the equal width conductors property is set to False when the via ends property is set to True
        assert distributed_design.topology.equal_width_conductors is False
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "via_ends_true.ckt", "Distributed"
        )

    def test_resonator_line_width_5mm(self, distributed_design):
        with pytest.raises(RuntimeError) as info:
            distributed_design.topology.resonator_line_width = "1.27 mm"
        assert (
            info.value.args[0]
            == "The Line Width property is not applicable to the "
            + convert_string(distributed_design.topology.topology_type.name)
            + " topology"
        )
        distributed_design.attributes.filter_class = FilterClass.BAND_PASS
        distributed_design.topology.topology_type = TopologyType.HAIRPIN
        assert distributed_design.topology.resonator_line_width == "1.27 mm"
        distributed_design.topology.resonator_line_width = "5 mm"
        assert distributed_design.topology.resonator_line_width == "5 mm"
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "resonator_line_width.ckt", "Distributed"
        )

    def test_resonator_rotation_angle_5deg(self, distributed_design):
        with pytest.raises(RuntimeError) as info:
            distributed_design.topology.resonator_rotation_angle = "0"
        assert (
            info.value.args[0]
            == "The Rotation Angle property is not applicable to the "
            + convert_string(distributed_design.topology.topology_type.name)
            + " topology"
        )
        distributed_design.attributes.filter_class = FilterClass.BAND_PASS
        distributed_design.topology.topology_type = TopologyType.PARALLEL_EDGE_COUPLED
        assert distributed_design.topology.resonator_rotation_angle == "0"
        distributed_design.topology.resonator_rotation_angle = "5"
        assert distributed_design.topology.resonator_rotation_angle == "5"
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "resonator_rotation_angle.ckt", "Distributed"
        )

    def test_mitered_corners(self, distributed_design):
        with pytest.raises(RuntimeError) as info:
            distributed_design.topology.mitered_corners = True
        assert (
            info.value.args[0]
            == "The Mitered Corners property is not applicable to the "
            + convert_string(distributed_design.topology.topology_type.name)
            + " topology"
        )
        distributed_design.attributes.filter_class = FilterClass.BAND_PASS
        distributed_design.topology.topology_type = TopologyType.HAIRPIN
        assert distributed_design.topology.mitered_corners is False
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "mitered_corners_false.ckt", "Distributed"
        )
        distributed_design.topology.mitered_corners = True
        assert distributed_design.topology.mitered_corners
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "mitered_corners_true.ckt", "Distributed"
        )

    def test_hairpin_gap_width_4mm(self, distributed_design):
        with pytest.raises(RuntimeError) as info:
            distributed_design.topology.hairpin_gap_width = "0.127 mm"
        assert (
            info.value.args[0]
            == "The Gap Width property is not applicable to the "
            + convert_string(distributed_design.topology.topology_type.name)
            + " topology"
        )
        distributed_design.attributes.filter_class = FilterClass.BAND_PASS
        distributed_design.topology.topology_type = TopologyType.HAIRPIN
        assert distributed_design.topology.hairpin_gap_width == "2.54 mm"
        distributed_design.topology.hairpin_gap_width = "4 mm"
        assert distributed_design.topology.hairpin_gap_width == "4 mm"
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "hairpin_gap_width.ckt", "Distributed"
        )

    def test_miniature_hairpin_gap_width_450um(self, distributed_design):
        with pytest.raises(RuntimeError) as info:
            distributed_design.topology.miniature_hairpin_gap_width = "635 um"
        assert (
            info.value.args[0]
            == "The Gap Width property is not applicable to the "
            + convert_string(distributed_design.topology.topology_type.name)
            + " topology"
        )
        distributed_design.attributes.filter_class = FilterClass.BAND_PASS
        distributed_design.topology.topology_type = TopologyType.MINIATURE_HAIRPIN
        assert distributed_design.topology.miniature_hairpin_gap_width == "635 um"
        distributed_design.topology.miniature_hairpin_gap_width = "450 um"
        assert distributed_design.topology.miniature_hairpin_gap_width == "450 um"
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "miniature_hairpin_gap_width.ckt", "Distributed"
        )

    def test_ring_resonator_gap_width_450um(self, distributed_design):
        with pytest.raises(RuntimeError) as info:
            distributed_design.topology.ring_resonator_gap_width = "635 um"
        assert (
            info.value.args[0]
            == "The Gap Width property is not applicable to the "
            + convert_string(distributed_design.topology.topology_type.name)
            + " topology"
        )
        distributed_design.attributes.filter_class = FilterClass.BAND_PASS
        distributed_design.topology.topology_type = TopologyType.RING_RESONATOR
        assert distributed_design.topology.ring_resonator_gap_width == "635 um"
        distributed_design.topology.ring_resonator_gap_width = "450 um"
        assert distributed_design.topology.ring_resonator_gap_width == "450 um"
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "ring_resonator_gap_width.ckt", "Distributed"
        )

    def test_hairpin_extension_length_2mm(self, distributed_design):
        with pytest.raises(RuntimeError) as info:
            distributed_design.topology.hairpin_extension_length = "0 mm"
        assert (
            info.value.args[0]
            == "The Tuning Extension property is not applicable to the "
            + convert_string(distributed_design.topology.topology_type.name)
            + " topology"
        )
        distributed_design.attributes.filter_class = FilterClass.BAND_PASS
        distributed_design.topology.topology_type = TopologyType.HAIRPIN
        assert distributed_design.topology.hairpin_extension_length == "0 um"
        distributed_design.topology.hairpin_extension_length = "2 mm"
        assert distributed_design.topology.hairpin_extension_length == "2 mm"
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "hairpin_extension_length.ckt", "Distributed"
        )

    def test_miniature_hairpin_end_curl_extension_2mm(self, distributed_design):
        with pytest.raises(RuntimeError) as info:
            distributed_design.topology.miniature_hairpin_end_curl_extension = "0 mm"
        assert (
            info.value.args[0]
            == "The Tuning Extension property is not applicable to the "
            + convert_string(distributed_design.topology.topology_type.name)
            + " topology"
        )
        distributed_design.attributes.filter_class = FilterClass.BAND_PASS
        distributed_design.topology.topology_type = TopologyType.MINIATURE_HAIRPIN
        assert distributed_design.topology.miniature_hairpin_end_curl_extension == "0 um"
        distributed_design.topology.miniature_hairpin_end_curl_extension = "2 mm"
        assert distributed_design.topology.miniature_hairpin_end_curl_extension == "2 mm"
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "miniature_hairpin_end_curl_extension.ckt", "Distributed"
        )

    def test_ring_resonator_end_gap_extension_2mm(self, distributed_design):
        with pytest.raises(RuntimeError) as info:
            distributed_design.topology.ring_resonator_end_gap_extension = "0 mm"
        assert (
            info.value.args[0]
            == "The Tuning Extension property is not applicable to the "
            + convert_string(distributed_design.topology.topology_type.name)
            + " topology"
        )
        distributed_design.attributes.filter_class = FilterClass.BAND_PASS
        distributed_design.topology.topology_type = TopologyType.RING_RESONATOR
        assert distributed_design.topology.ring_resonator_end_gap_extension == "0 um"
        distributed_design.topology.ring_resonator_end_gap_extension = "2 mm"
        assert distributed_design.topology.ring_resonator_end_gap_extension == "2 mm"
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "ring_resonator_end_gap_extension.ckt", "Distributed"
        )

    def test_tuning_type_1(self, distributed_design):
        with pytest.raises(RuntimeError) as info:
            distributed_design.topology.tuning_type_1 = True
        assert (
            info.value.args[0]
            == "The Tuning Type property is not applicable to the "
            + convert_string(distributed_design.topology.topology_type.name)
            + " topology"
        )
        distributed_design.attributes.filter_class = FilterClass.BAND_PASS
        distributed_design.topology.topology_type = TopologyType.HAIRPIN
        assert distributed_design.topology.tuning_type_1
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "tuning_type_1.ckt", "Distributed"
        )
        distributed_design.topology.tuning_type_1 = False
        assert distributed_design.topology.tuning_type_1 is False
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "tuning_type_2.ckt", "Distributed"
        )

    def test_tap_position(self, distributed_design):
        with pytest.raises(RuntimeError) as info:
            distributed_design.topology.tap_position = TapPosition.AUTO
        assert (
            info.value.args[0]
            == "The Tap Position property is not applicable to the "
            + convert_string(distributed_design.topology.topology_type.name)
            + " topology"
        )
        distributed_design.attributes.filter_class = FilterClass.BAND_PASS
        distributed_design.topology.topology_type = TopologyType.MINIATURE_HAIRPIN
        assert distributed_design.topology.tap_position == TapPosition.AUTO
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "tap_position_auto.ckt", "Distributed"
        )
        distributed_design.topology.tap_position = TapPosition.SIDES
        assert distributed_design.topology.tap_position == TapPosition.SIDES
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "tap_position_sides.ckt", "Distributed"
        )

    def test_wide_band(self, distributed_design):
        with pytest.raises(RuntimeError) as info:
            distributed_design.topology.wide_band = True
        assert (
            info.value.args[0]
            == "The Wide Band property is not applicable to the "
            + convert_string(distributed_design.topology.topology_type.name)
            + " topology"
        )
        distributed_design.attributes.filter_class = FilterClass.BAND_PASS
        distributed_design.topology.topology_type = TopologyType.INTERDIGITAL
        assert distributed_design.topology.wide_band is False
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "wide_band_false.ckt", "Distributed"
        )
        distributed_design.topology.wide_band = True
        # To have a wide band filter, the pinned property must be set to True
        distributed_design.topology.pinned = True
        assert distributed_design.topology.wide_band
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "wide_band_true.ckt", "Distributed"
        )

    def test_open_ends(self, distributed_design):
        with pytest.raises(RuntimeError) as info:
            distributed_design.topology.open_ends = True
        assert (
            info.value.args[0]
            == "The Open Ends property is not applicable to the "
            + convert_string(distributed_design.topology.topology_type.name)
            + " topology"
        )
        distributed_design.attributes.filter_class = FilterClass.BAND_PASS
        distributed_design.topology.topology_type = TopologyType.INTERDIGITAL
        assert distributed_design.topology.open_ends is False
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "open_ends_false.ckt", "Distributed"
        )
        distributed_design.topology.open_ends = True
        assert distributed_design.topology.open_ends
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "open_ends_true.ckt", "Distributed"
        )

    def test_combline_half_length_frequency_2ghz(self, distributed_design):
        with pytest.raises(RuntimeError) as info:
            distributed_design.topology.combline_half_length_frequency = "4G"
        assert (
            info.value.args[0]
            == "The 1/2 Length Frequency property is not applicable to the "
            + convert_string(distributed_design.topology.topology_type.name)
            + " topology"
        )
        distributed_design.attributes.filter_class = FilterClass.BAND_PASS
        distributed_design.topology.topology_type = TopologyType.COMBLINE
        assert distributed_design.topology.combline_half_length_frequency == "4G"
        distributed_design.topology.combline_half_length_frequency = "2 GHz"
        assert distributed_design.topology.combline_half_length_frequency == "2 GHz"
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "combline_half_length_frequency.ckt", "Distributed"
        )

    def test_coupled_segments_quarter_length_frequency_2ghz(self, distributed_design):
        with pytest.raises(RuntimeError) as info:
            distributed_design.topology.coupled_segments_quarter_length_frequency = "4G"
        assert (
            info.value.args[0]
            == "The 1/4 Length Frequency property is not applicable to the "
            + convert_string(distributed_design.topology.topology_type.name)
            + " topology"
        )
        distributed_design.attributes.filter_class = FilterClass.HIGH_PASS
        distributed_design.topology.topology_type = TopologyType.COUPLED_SEGMENTS
        assert distributed_design.topology.coupled_segments_quarter_length_frequency == "4G"
        distributed_design.topology.coupled_segments_quarter_length_frequency = "2 GHz"
        assert distributed_design.topology.coupled_segments_quarter_length_frequency == "2 GHz"
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "coupled_segments_quarter_length_frequency.ckt", "Distributed"
        )

    def test_netlist(self, distributed_design):
        assert distributed_design.topology.netlist().splitlines() == read_resource_file("default.ckt", "Distributed")

    def test_quick_optimize(self, distributed_design):
        assert distributed_design.topology.quick_optimize is False
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "quick_optimize_false.ckt", "Distributed"
        )
        distributed_design.topology.quick_optimize = True
        assert distributed_design.topology.quick_optimize
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "quick_optimize_true.ckt", "Distributed"
        )

    def test_resonator_length_extension(self, distributed_design):
        with pytest.raises(RuntimeError) as info:
            distributed_design.topology.resonator_length_extension = True
        assert (
            info.value.args[0]
            == "The Enable Extension property is not applicable to the "
            + convert_string(distributed_design.topology.topology_type.name)
            + " topology"
        )
        distributed_design.attributes.filter_class = FilterClass.BAND_PASS
        distributed_design.topology.topology_type = TopologyType.INTERDIGITAL
        assert distributed_design.topology.resonator_length_extension is False
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "resonator_length_extension_false.ckt", "Distributed"
        )
        distributed_design.topology.resonator_length_extension = True
        assert distributed_design.topology.resonator_length_extension
        assert distributed_design.topology.netlist().splitlines() == read_resource_file(
            "resonator_length_extension_true.ckt", "Distributed"
        )
