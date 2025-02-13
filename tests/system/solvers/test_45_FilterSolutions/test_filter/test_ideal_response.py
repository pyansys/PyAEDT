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

from ansys.aedt.core.filtersolutions_core.ideal_response import FrequencyResponseColumn
from ansys.aedt.core.filtersolutions_core.ideal_response import PoleZerosResponseColumn
from ansys.aedt.core.filtersolutions_core.ideal_response import SParametersResponseColumn
from ansys.aedt.core.filtersolutions_core.ideal_response import TimeResponseColumn
from ansys.aedt.core.generic.settings import is_linux
import pytest

from tests.system.solvers.conftest import config
from tests.system.solvers.test_45_FilterSolutions.resources import read_resource_file


@pytest.mark.skipif(is_linux, reason="FilterSolutions API is not supported on Linux.")
@pytest.mark.skipif(config["desktopVersion"] < "2025.1", reason="Skipped on versions earlier than 2025.1")
class TestClass:
    def test_frequency_response_getter(self, lumped_design):
        mag_db = lumped_design.ideal_response._frequency_response_getter(FrequencyResponseColumn.MAGNITUDE_DB)
        assert len(mag_db) == 500
        assert mag_db[100] == pytest.approx(-0.0002779395744451339)
        assert mag_db[300] == pytest.approx(-14.14973347970826)
        assert mag_db[-1] == pytest.approx(-69.61741290615645)
        phs_deg = lumped_design.ideal_response._frequency_response_getter(FrequencyResponseColumn.PHASE_DEG)
        assert len(phs_deg) == 500
        assert phs_deg[100] == pytest.approx(-72.00174823521779)
        assert phs_deg[300] == pytest.approx(57.235563076374426)
        assert phs_deg[-1] == pytest.approx(-52.48142049626833)
        grp_dly = lumped_design.ideal_response._frequency_response_getter(FrequencyResponseColumn.GROUP_DELAY)
        assert len(grp_dly) == 500
        assert grp_dly[100] == pytest.approx(5.476886038520659e-10)
        assert grp_dly[300] == pytest.approx(3.6873949391963247e-10)
        assert grp_dly[-1] == pytest.approx(2.1202561661746704e-11)
        phs_rad = lumped_design.ideal_response._frequency_response_getter(FrequencyResponseColumn.PHASE_RAD)
        assert len(phs_rad) == 500
        assert phs_rad[100] == pytest.approx(-1.256667573896567)
        assert phs_rad[300] == pytest.approx(0.9989490249156284)
        assert phs_rad[-1] == pytest.approx(-0.9159735837835188)
        mag_art = lumped_design.ideal_response._frequency_response_getter(FrequencyResponseColumn.MAGNITUDE_ARITH)
        assert len(mag_art) == 500
        assert mag_art[100] == pytest.approx(0.9999680015359182)
        assert mag_art[300] == pytest.approx(0.1961161351381822)
        assert mag_art[-1] == pytest.approx(0.000330467956321812)
        mag_r = lumped_design.ideal_response._frequency_response_getter(FrequencyResponseColumn.MAGNITUDE_REAL)
        assert len(mag_r) == 500
        assert mag_r[100] == pytest.approx(0.3089780880159494)
        assert mag_r[300] == pytest.approx(0.10613537973464354)
        assert mag_r[-1] == pytest.approx(0.00020126115208825366)
        mag_x = lumped_design.ideal_response._frequency_response_getter(FrequencyResponseColumn.MAGNITUDE_IMAG)
        assert len(mag_x) == 500
        assert mag_x[100] == pytest.approx(-0.9510355120718397)
        assert mag_x[300] == pytest.approx(0.1649145828303876)
        assert mag_x[-1] == pytest.approx(-0.00026211260712835594)
        phs_dev_deg = lumped_design.ideal_response._frequency_response_getter(FrequencyResponseColumn.PHASE_DEV_DEG)
        assert len(phs_dev_deg) == 500
        assert phs_dev_deg[100] == pytest.approx(116.73031543331324)
        assert phs_dev_deg[300] == pytest.approx(-50.566997975196706)
        assert phs_dev_deg[-1] == pytest.approx(67.66973459820802)
        phs_dev_rad = lumped_design.ideal_response._frequency_response_getter(FrequencyResponseColumn.PHASE_DEV_RAD)
        assert len(phs_dev_rad) == 500
        assert phs_dev_rad[100] == pytest.approx(2.0373283412028673)
        assert phs_dev_rad[300] == pytest.approx(-0.8825606075164885)
        assert phs_dev_rad[-1] == pytest.approx(1.181059672689452)
        freqs = lumped_design.ideal_response._frequency_response_getter(FrequencyResponseColumn.FREQUENCY)
        assert len(freqs) == 500
        assert freqs[100] == 2392202091.5388284
        assert freqs[300] == 8669097136.772985
        assert freqs[-1] == 31214328219.225075

    def test_time_response_getter(self, lumped_design):
        step_response = lumped_design.ideal_response._time_response_getter(TimeResponseColumn.STEP_RESPONSE)
        assert len(step_response) == 300
        assert step_response[100] == pytest.approx(1.0006647872833518)
        assert step_response[200] == pytest.approx(0.9999988501385255)
        assert step_response[-1] == pytest.approx(0.9999999965045667)
        ramp_response = lumped_design.ideal_response._time_response_getter(TimeResponseColumn.RAMP_RESPONSE)
        assert len(ramp_response) == 300
        assert ramp_response[100] == pytest.approx(2.8184497075983895e-09)
        assert ramp_response[200] == pytest.approx(6.151630831481296e-09)
        assert ramp_response[-1] == pytest.approx(9.45163045223663e-09)
        impulse_response = lumped_design.ideal_response._time_response_getter(TimeResponseColumn.IMPULSE_RESPONSE)
        assert len(impulse_response) == 300
        assert impulse_response[100] == pytest.approx(-8537300.294689251)
        assert impulse_response[200] == pytest.approx(-8538.227868086184)
        assert impulse_response[-1] == pytest.approx(3.996366349798659)
        step_response_db = lumped_design.ideal_response._time_response_getter(TimeResponseColumn.STEP_RESPONSE_DB)
        assert len(step_response_db) == 300
        assert step_response_db[100] == pytest.approx(-1.0381882969997027)
        assert step_response_db[200] == pytest.approx(-1.0439706350712086)
        assert step_response_db[-1] == pytest.approx(-1.0439606778565478)
        ramp_response_db = lumped_design.ideal_response._time_response_getter(TimeResponseColumn.RAMP_RESPONSE_DB)
        assert len(ramp_response_db) == 300
        assert ramp_response_db[100] == pytest.approx(-10.540507747401335)
        assert ramp_response_db[200] == pytest.approx(-3.7609082425924782)
        assert ramp_response_db[-1] == pytest.approx(-0.03057888328183367)
        impulse_response_db = lumped_design.ideal_response._time_response_getter(TimeResponseColumn.IMPULSE_RESPONSE_DB)
        assert len(impulse_response_db) == 300
        assert impulse_response_db[100] == pytest.approx(-48.60282519370875)
        assert impulse_response_db[200] == pytest.approx(-100.0)
        assert impulse_response_db[-1] == pytest.approx(-100.0)
        time = lumped_design.ideal_response._time_response_getter(TimeResponseColumn.TIME)
        assert len(time) == 300
        assert time[1] == pytest.approx(3.3333333333333335e-11)
        assert time[200] == pytest.approx(6.666666666666667e-09)
        assert time[-1] == pytest.approx(9.966666666666667e-09)

    def test_sparameters_response_getter(self, lumped_design):
        s11_response_db = lumped_design.ideal_response._sparamaters_response_getter(SParametersResponseColumn.S11_DB)
        assert len(s11_response_db) == 500
        assert s11_response_db[100] == pytest.approx(-41.93847819973562)
        assert s11_response_db[300] == pytest.approx(-0.1703333929877981)
        assert s11_response_db[-1] == pytest.approx(-4.742889883456317e-07)
        s21_response_db = lumped_design.ideal_response._sparamaters_response_getter(SParametersResponseColumn.S21_DB)
        assert len(s21_response_db) == 500
        assert s21_response_db[100] == pytest.approx(-0.0002779395744451339)
        assert s21_response_db[300] == pytest.approx(-14.14973347970826)
        assert s21_response_db[-1] == pytest.approx(-69.61741290615645)
        s11_response = lumped_design.ideal_response._sparamaters_response_getter(SParametersResponseColumn.S11_ARITH)
        assert len(s11_response) == 500
        assert s11_response[100] == pytest.approx(0.007999744012287301)
        assert s11_response[300] == pytest.approx(0.9805806756909208)
        assert s11_response[-1] == pytest.approx(0.9999999453954638)
        s21_response = lumped_design.ideal_response._sparamaters_response_getter(SParametersResponseColumn.S21_ARITH)
        assert len(s21_response) == 500
        assert s21_response[100] == pytest.approx(0.9999680015359182)
        assert s21_response[300] == pytest.approx(0.1961161351381822)
        assert s21_response[-1] == pytest.approx(0.000330467956321812)
        freqs = lumped_design.ideal_response._sparamaters_response_getter(SParametersResponseColumn.FREQUENCY)
        assert len(freqs) == 500
        assert freqs[100] == pytest.approx(2392202091.5388284)
        assert freqs[300] == pytest.approx(8669097136.772985)
        assert freqs[-1] == pytest.approx(31214328219.225075)

    def test_pole_zeros_response_getter(self, lumped_design):
        pole_zero_den_x = lumped_design.ideal_response._pole_zeros_response_getter(
            PoleZerosResponseColumn.TX_ZERO_DEN_X
        )
        assert len(pole_zero_den_x) == 5
        assert pole_zero_den_x[0] == pytest.approx(-1000000000.0)
        assert pole_zero_den_x[1] == pytest.approx(-809016994.3749474)
        assert pole_zero_den_x[2] == pytest.approx(-809016994.3749474)
        assert pole_zero_den_x[3] == pytest.approx(-309016994.3749475)
        assert pole_zero_den_x[4] == pytest.approx(-309016994.3749475)
        pole_zero_den_y = lumped_design.ideal_response._pole_zeros_response_getter(
            PoleZerosResponseColumn.TX_ZERO_DEN_Y
        )
        assert len(pole_zero_den_y) == 5
        assert pole_zero_den_y[0] == pytest.approx(0.0)
        assert pole_zero_den_y[1] == pytest.approx(587785252.2924731)
        assert pole_zero_den_y[2] == pytest.approx(-587785252.2924731)
        assert pole_zero_den_y[3] == pytest.approx(951056516.2951534)
        assert pole_zero_den_y[4] == pytest.approx(-951056516.2951534)
        pole_zero_num_x = lumped_design.ideal_response._pole_zeros_response_getter(
            PoleZerosResponseColumn.TX_ZERO_NUM_X
        )
        assert len(pole_zero_num_x) == 0
        pole_zero_num_y = lumped_design.ideal_response._pole_zeros_response_getter(
            PoleZerosResponseColumn.TX_ZERO_NUM_Y
        )
        assert len(pole_zero_num_y) == 0
        proto_pole_zero_den_x = lumped_design.ideal_response._pole_zeros_response_getter(
            PoleZerosResponseColumn.PROTO_TX_ZERO_DEN_X
        )
        assert len(proto_pole_zero_den_x) == 5
        assert proto_pole_zero_den_x[0] == pytest.approx(-0.30901699437494745)
        assert proto_pole_zero_den_x[1] == pytest.approx(-0.30901699437494745)
        assert proto_pole_zero_den_x[2] == pytest.approx(-0.8090169943749475)
        assert proto_pole_zero_den_x[3] == pytest.approx(-0.8090169943749475)
        assert proto_pole_zero_den_x[4] == pytest.approx(-1.0)
        proto_pole_zero_den_y = lumped_design.ideal_response._pole_zeros_response_getter(
            PoleZerosResponseColumn.PROTO_TX_ZERO_DEN_Y
        )
        assert len(proto_pole_zero_den_y) == 5
        assert proto_pole_zero_den_y[0] == pytest.approx(0.9510565162951534)
        assert proto_pole_zero_den_y[1] == pytest.approx(-0.9510565162951534)
        assert proto_pole_zero_den_y[2] == pytest.approx(-0.5877852522924731)
        assert proto_pole_zero_den_y[3] == pytest.approx(0.5877852522924731)
        assert proto_pole_zero_den_y[4] == pytest.approx(0.0)
        proto_pole_zero_num_x = lumped_design.ideal_response._pole_zeros_response_getter(
            PoleZerosResponseColumn.PROTO_TX_ZERO_NUM_X
        )
        assert len(proto_pole_zero_num_x) == 0
        proto_pole_zero_num_y = lumped_design.ideal_response._pole_zeros_response_getter(
            PoleZerosResponseColumn.PROTO_TX_ZERO_NUM_Y
        )
        assert len(proto_pole_zero_num_y) == 0
        rx_zero_den_x = lumped_design.ideal_response._pole_zeros_response_getter(PoleZerosResponseColumn.RX_ZERO_DEN_X)
        assert len(rx_zero_den_x) == 5
        assert rx_zero_den_x[0] == pytest.approx(-1000000000.0)
        assert rx_zero_den_x[1] == pytest.approx(-809016994.3749474)
        assert rx_zero_den_x[2] == pytest.approx(-809016994.3749474)
        assert rx_zero_den_x[3] == pytest.approx(-309016994.3749475)
        assert rx_zero_den_x[4] == pytest.approx(-309016994.3749475)
        rx_zero_den_y = lumped_design.ideal_response._pole_zeros_response_getter(PoleZerosResponseColumn.RX_ZERO_DEN_Y)
        assert len(rx_zero_den_y) == 5
        assert rx_zero_den_y[0] == pytest.approx(0.0)
        assert rx_zero_den_y[1] == pytest.approx(587785252.2924731)
        assert rx_zero_den_y[2] == pytest.approx(-587785252.2924731)
        assert rx_zero_den_y[3] == pytest.approx(951056516.2951534)
        assert rx_zero_den_y[4] == pytest.approx(-951056516.2951534)
        rx_zero_num_x = lumped_design.ideal_response._pole_zeros_response_getter(PoleZerosResponseColumn.RX_ZERO_NUM_X)
        assert len(rx_zero_num_x) == 5
        assert rx_zero_num_x[0] == pytest.approx(0.0)
        assert rx_zero_num_x[1] == pytest.approx(0.0)
        assert rx_zero_num_x[2] == pytest.approx(0.0)
        assert rx_zero_num_x[3] == pytest.approx(0.0)
        assert rx_zero_num_x[4] == pytest.approx(0.0)
        rx_zero_num_y = lumped_design.ideal_response._pole_zeros_response_getter(PoleZerosResponseColumn.RX_ZERO_NUM_Y)
        assert len(rx_zero_num_y) == 5
        assert rx_zero_num_y[0] == pytest.approx(0.0)
        assert rx_zero_num_y[1] == pytest.approx(0.0)
        assert rx_zero_num_y[2] == pytest.approx(0.0)
        assert rx_zero_num_y[3] == pytest.approx(0.0)
        assert rx_zero_num_y[4] == pytest.approx(0.0)
        proto_rx_zero_den_x = lumped_design.ideal_response._pole_zeros_response_getter(
            PoleZerosResponseColumn.PROTO_RX_ZERO_DEN_X
        )
        assert len(proto_rx_zero_den_x) == 5
        assert proto_rx_zero_den_x[0] == pytest.approx(-0.30901699437494745)
        assert proto_rx_zero_den_x[1] == pytest.approx(-0.30901699437494745)
        assert proto_rx_zero_den_x[2] == pytest.approx(-0.8090169943749475)
        assert proto_rx_zero_den_x[3] == pytest.approx(-0.8090169943749475)
        assert proto_rx_zero_den_x[4] == pytest.approx(-1.0)
        proto_rx_zero_den_y = lumped_design.ideal_response._pole_zeros_response_getter(
            PoleZerosResponseColumn.PROTO_RX_ZERO_DEN_Y
        )
        assert len(proto_rx_zero_den_y) == 5
        assert proto_rx_zero_den_y[0] == pytest.approx(0.9510565162951534)
        assert proto_rx_zero_den_y[1] == pytest.approx(-0.9510565162951534)
        assert proto_rx_zero_den_y[2] == pytest.approx(-0.5877852522924731)
        assert proto_rx_zero_den_y[3] == pytest.approx(0.5877852522924731)
        assert proto_rx_zero_den_y[4] == pytest.approx(0.0)
        proto_rx_zero_num_x = lumped_design.ideal_response._pole_zeros_response_getter(
            PoleZerosResponseColumn.PROTO_RX_ZERO_NUM_X
        )
        assert len(proto_rx_zero_num_x) == 5
        assert proto_rx_zero_num_x[0] == pytest.approx(0.0)
        assert proto_rx_zero_num_x[1] == pytest.approx(0.0)
        assert proto_rx_zero_num_x[2] == pytest.approx(0.0)
        assert proto_rx_zero_num_x[3] == pytest.approx(0.0)
        assert proto_rx_zero_num_x[4] == pytest.approx(0.0)
        proto_rx_zero_num_y = lumped_design.ideal_response._pole_zeros_response_getter(
            PoleZerosResponseColumn.PROTO_RX_ZERO_NUM_Y
        )
        assert len(proto_rx_zero_num_y) == 5
        assert proto_rx_zero_num_y[0] == pytest.approx(0.0)
        assert proto_rx_zero_num_y[1] == pytest.approx(0.0)
        assert proto_rx_zero_num_y[2] == pytest.approx(0.0)
        assert proto_rx_zero_num_y[3] == pytest.approx(0.0)
        assert proto_rx_zero_num_y[4] == pytest.approx(0.0)

    def test_filter_vsg_analysis_enabled(self, lumped_design):
        assert lumped_design.ideal_response.vsg_analysis_enabled is False
        lumped_design.ideal_response.vsg_analysis_enabled = True
        assert lumped_design.ideal_response.vsg_analysis_enabled

    def test_frequency_response(self, lumped_design):
        freq, mag_db = lumped_design.ideal_response.frequency_response(
            y_axis_parameter=FrequencyResponseColumn.MAGNITUDE_DB,
            minimum_frequency=None,
            maximum_frequency=None,
            vsg_analysis_enabled=False,
        )
        assert len(freq) == 500
        assert freq[100] == pytest.approx(380730787.74317527)
        assert freq[300] == pytest.approx(1379729661.4612174)
        assert freq[-1] == pytest.approx(4967914631.382509)
        assert len(mag_db) == 500
        assert mag_db[100] == pytest.approx(-0.0002779395744451339)
        assert mag_db[300] == pytest.approx(-14.14973347970826)
        assert mag_db[-1] == pytest.approx(-69.61741290615645)
        freq, mag_db = lumped_design.ideal_response.frequency_response(
            y_axis_parameter=FrequencyResponseColumn.MAGNITUDE_DB,
            minimum_frequency="100 MHz",
            maximum_frequency="3 GHz",
            vsg_analysis_enabled=False,
        )
        assert freq[0] == pytest.approx(100000000)
        assert freq[-1] == pytest.approx(2979662067.4569254)
        assert mag_db[0] == pytest.approx(-4.342896962104627e-10)
        assert mag_db[-1] == pytest.approx(-47.41677994558435)

    def test_time_response(self, lumped_design):
        time, step_response = lumped_design.ideal_response.time_response(
            y_axis_parameter=TimeResponseColumn.STEP_RESPONSE,
            minimum_time=None,
            maximum_time=None,
            vsg_analysis_enabled=False,
        )
        assert len(time) == 300
        assert time[100] == pytest.approx(3.334e-09)
        assert time[200] == pytest.approx(6.667e-09)
        assert time[-1] == pytest.approx(9.9667e-09)
        assert len(step_response) == 300
        assert step_response[100] == pytest.approx(1.0006647872833518)
        assert step_response[200] == pytest.approx(0.9999988501385255)
        assert step_response[-1] == pytest.approx(0.9999999965045667)
        time, step_response = lumped_design.ideal_response.time_response(
            y_axis_parameter=TimeResponseColumn.STEP_RESPONSE,
            minimum_time="1 ns",
            maximum_time="5 ns",
            vsg_analysis_enabled=False,
        )
        assert time[0] == pytest.approx(1e-09)
        assert time[-1] == pytest.approx(4.9833e-09)
        assert step_response[0] == pytest.approx(1.127711560082254)
        assert step_response[-1] == pytest.approx(0.9999962734156826)

    def test_s_parameters(self, lumped_design):
        freq, s21_db = lumped_design.ideal_response.s_parameters(
            y_axis_parameter=SParametersResponseColumn.S21_DB,
            minimum_frequency=None,
            maximum_frequency=None,
        )
        assert len(freq) == 500
        assert freq[100] == pytest.approx(380730787.74317527)
        assert freq[300] == pytest.approx(1379729661.4612174)
        assert freq[-1] == pytest.approx(4967914631.382509)
        assert len(s21_db) == 500
        assert s21_db[100] == pytest.approx(-0.0002779395744451339)
        assert s21_db[300] == pytest.approx(-14.14973347970826)
        assert s21_db[-1] == pytest.approx(-69.61741290615645)
        freq, s21_db = lumped_design.ideal_response.s_parameters(
            y_axis_parameter=SParametersResponseColumn.S21_DB,
            minimum_frequency="100 MHz",
            maximum_frequency="3 GHz",
        )
        assert freq[0] == pytest.approx(100000000)
        assert freq[-1] == pytest.approx(2979662067.4569254)
        assert s21_db[0] == pytest.approx(-4.342896962104627e-10)
        assert s21_db[-1] == pytest.approx(-47.41677994558435)

    def test_pole_zero_locations(self, lumped_design):
        tx_zero_den_x, tx_zero_den_y = lumped_design.ideal_response.pole_zero_locations(
            x_axis_parameter=PoleZerosResponseColumn.TX_ZERO_DEN_X,
            y_axis_parameter=PoleZerosResponseColumn.TX_ZERO_DEN_Y,
        )
        assert len(tx_zero_den_x) == 5
        assert tx_zero_den_x[0] == pytest.approx(-1000000000.0)
        assert tx_zero_den_x[1] == pytest.approx(-809016994.3749474)
        assert tx_zero_den_x[2] == pytest.approx(-809016994.3749474)
        assert tx_zero_den_x[3] == pytest.approx(-309016994.3749475)
        assert tx_zero_den_x[4] == pytest.approx(-309016994.3749475)
        assert len(tx_zero_den_y) == 5
        assert tx_zero_den_y[0] == pytest.approx(0.0)
        assert tx_zero_den_y[1] == pytest.approx(587785252.2924731)
        assert tx_zero_den_y[2] == pytest.approx(-587785252.2924731)
        assert tx_zero_den_y[3] == pytest.approx(951056516.2951534)
        assert tx_zero_den_y[4] == pytest.approx(-951056516.2951534)

    def test_transfer_function_response(self, lumped_design):
        assert lumped_design.ideal_response.transfer_function_response().splitlines() == read_resource_file(
            "transferfunction.ckt", "Lumped"
        )
