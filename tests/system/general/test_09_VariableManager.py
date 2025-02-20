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

from __future__ import division  # noreorder

import math

from ansys.aedt.core import MaxwellCircuit
from ansys.aedt.core.application.variables import Variable
from ansys.aedt.core.application.variables import generate_validation_errors
from ansys.aedt.core.generic.numbers import decompose_variable_value
from ansys.aedt.core.generic.numbers import isclose
from ansys.aedt.core.modeler.geometry_operators import GeometryOperators
import pytest

from tests.system.general.conftest import desktop_version


@pytest.fixture(scope="class")
def aedtapp(add_app):
    app = add_app(project_name="Test_09")
    return app


@pytest.fixture()
def validation_input():
    property_names = [
        "+X Padding Type",
        "+X Padding Data",
        "-X Padding Type",
        "-X Padding Data",
        "+Y Padding Type",
        "+Y Padding Data",
        "-Y Padding Type",
        "-Y Padding Data",
        "+Z Padding Type",
        "+Z Padding Data",
        "-Z Padding Type",
        "-Z Padding Data",
    ]
    expected_settings = [
        "Absolute Offset",
        "10mm",
        "Percentage Offset",
        "100",
        "Transverse Percentage Offset",
        "100",
        "Percentage Offset",
        "10",
        "Absolute Offset",
        "50mm",
        "Absolute Position",
        "-600mm",
    ]
    actual_settings = list(expected_settings)
    return property_names, expected_settings, actual_settings


@pytest.fixture()
def validation_float_input():
    property_names = ["+X Padding Data", "-X Padding Data", "+Y Padding Data"]
    expected_settings = [100, 200.1, 300]
    actual_settings = list(expected_settings)
    return property_names, expected_settings, actual_settings


class TestClass:
    @pytest.fixture(autouse=True)
    def init(self, aedtapp, local_scratch):
        self.aedtapp = aedtapp
        self.local_scratch = local_scratch

    def test_01_set_globals(self):
        var = self.aedtapp.variable_manager
        self.aedtapp["$Test_Global1"] = "5rad"
        self.aedtapp["$Test_Global2"] = -1.0
        self.aedtapp["$Test_Global3"] = "0"
        self.aedtapp["$Test_Global4"] = "$Test_Global2*$Test_Global1"
        independent = self.aedtapp._variable_manager.independent_variable_names
        dependent = self.aedtapp._variable_manager.dependent_variable_names
        val = var["$Test_Global4"]
        assert val.numeric_value == -5.0
        assert "$Test_Global1" in independent
        assert "$Test_Global2" in independent
        assert "$Test_Global3" in independent
        assert "$Test_Global4" in dependent

        self.aedtapp["$test"] = "1mm"
        self.aedtapp["$test2"] = "$test"
        assert "$test2" in self.aedtapp.variable_manager.dependent_project_variable_names
        assert "$test" in self.aedtapp.variable_manager.independent_project_variable_names
        del self.aedtapp["$test2"]
        assert "$test2" not in self.aedtapp.variable_manager.variables
        del self.aedtapp["$test"]
        assert "$test" not in self.aedtapp.variable_manager.variables

    def test_01_set_var_simple(self):
        var = self.aedtapp.variable_manager
        self.aedtapp["Var1"] = "1rpm"
        var_1 = self.aedtapp["Var1"]
        var_2 = var["Var1"].expression
        assert var_1 == var_2
        assert isclose(var["Var1"].numeric_value, 1.0)

        self.aedtapp["test"] = "1mm"
        self.aedtapp["test2"] = "test"
        assert "test2" in self.aedtapp.variable_manager.dependent_design_variable_names
        del self.aedtapp["test2"]
        assert "test2" not in self.aedtapp.variable_manager.variables
        del self.aedtapp["test"]
        assert "test" not in self.aedtapp.variable_manager.variables

    def test_02_test_formula(self):
        self.aedtapp["Var1"] = 3
        self.aedtapp["Var2"] = "12deg"
        self.aedtapp["Var3"] = "Var1 * Var2"

        self.aedtapp["$PrjVar1"] = "2*pi"
        self.aedtapp["$PrjVar2"] = 45
        self.aedtapp["$PrjVar3"] = "sqrt(34 * $PrjVar2/$PrjVar1 )"

        v = self.aedtapp.variable_manager
        for var_name in v.variable_names:
            print(f"{var_name} = {self.aedtapp[var_name]}")
        tol = 1e-9
        c2pi = math.pi * 2.0
        assert abs(v["$PrjVar1"].numeric_value - c2pi) < tol
        assert abs(v["$PrjVar3"].numeric_value - math.sqrt(34 * 45.0 / c2pi)) < tol
        assert abs(v["Var3"].numeric_value - 3.0 * 12.0) < tol
        assert v["Var3"].units == "deg"

    def test_03_test_evaluated_value(self):
        self.aedtapp["p1"] = "10mm"
        self.aedtapp["p2"] = "20mm"
        self.aedtapp["p3"] = "p1 * p2"
        v = self.aedtapp.variable_manager

        eval_p3_nom = v._app.get_evaluated_value("p3")
        assert isclose(eval_p3_nom, 0.0002)
        v_app = self.aedtapp.variable_manager
        assert v_app["p1"].sweep
        v_app["p1"].sweep = False
        assert not v_app["p1"].sweep
        assert not v_app["p1"].read_only
        v_app["p1"].read_only = True
        assert v_app["p1"].read_only
        assert not v_app["p1"].hidden
        v_app["p1"].hidden = True
        assert v_app["p1"].hidden
        assert v_app["p2"].description == ""
        v_app["p2"].description = "myvar"
        assert v_app["p2"].description == "myvar"
        assert v_app["p2"].expression == "20mm"
        v_app["p2"].expression = "5rad"
        assert v_app["p2"].expression == "5rad"

    def test_04_set_variable(self):
        assert self.aedtapp.variable_manager.set_variable("p1", expression="10mm")
        assert self.aedtapp["p1"] == "10mm"
        assert self.aedtapp.variable_manager.set_variable("p1", expression="20mm", overwrite=False)
        assert self.aedtapp["p1"] == "10mm"
        assert self.aedtapp.variable_manager.set_variable("p1", expression="30mm")
        assert self.aedtapp["p1"] == "30mm"
        assert self.aedtapp.variable_manager.set_variable(
            name="p2",
            expression="10mm",
            read_only=True,
            hidden=True,
            description="This is a description of this variable",
        )
        assert self.aedtapp.variable_manager.set_variable("$p1", expression="10mm")
        assert self.aedtapp.variable_manager.set_variable("$p1", expression="12mm")

    def test_05_variable_class(self):
        v = Variable("4mm")
        num_value = v.numeric_value
        assert num_value == 4.0

        v = v.rescale_to("meter")
        assert v.evaluated_value == "0.004meter"
        assert v.numeric_value == 0.004
        assert v.value == v.numeric_value

        v = Variable("100cel")
        assert v.numeric_value == 100.0
        assert v.evaluated_value == "100.0cel"
        assert v.value == 373.15
        v.rescale_to("fah")
        assert v.numeric_value == 212.0

        v = Variable("30dBW")
        assert v.numeric_value == 30.0
        assert v.evaluated_value == "30.0dBW"
        assert v.value == 1000
        v.rescale_to("megW")
        assert v.numeric_value == 0.001
        assert v.evaluated_value == "0.001megW"
        assert v.value == 1000

        v = Variable("10dBm")
        assert v.numeric_value == 10.0
        assert v.evaluated_value == "10.0dBm"
        assert v.value == 0.01
        v.rescale_to("W")
        assert v.numeric_value == 0.01
        assert v.evaluated_value == "0.01W"
        assert v.value == 0.01

    def test_06_multiplication(self):
        v1 = Variable("10mm")
        v2 = Variable(3)
        v3 = Variable("3mA")
        v4 = Variable("40V")
        v5 = Variable("100NewtonMeter")
        v6 = Variable("1000rpm")
        tol = 1e-4
        result_1 = v1 * v2
        result_2 = v2 * v3
        result_3 = v3 * v4
        result_4 = v4 * v3
        result_5 = v4 * 24.0 * v3
        result_6 = v5 * v6
        result_7 = v6 * v5
        result_8 = (v5 * v6).rescale_to("kW")
        assert result_1.numeric_value == 30.0
        assert result_1.unit_system == "Length"

        assert result_2.numeric_value == 9.0
        assert result_2.units == "mA"
        assert result_2.unit_system == "Current"

        assert result_3.numeric_value == 0.12
        assert result_3.units == "W"
        assert result_3.unit_system == "Power"

        assert result_4.numeric_value == 0.12
        assert result_4.units == "W"
        assert result_4.unit_system == "Power"

        assert result_5.numeric_value == 2.88
        assert result_5.units == "W"
        assert result_5.unit_system == "Power"

        assert abs(result_6.numeric_value - 10471.9755) / result_6.numeric_value < tol
        assert result_6.units == "W"
        assert result_6.unit_system == "Power"

        assert abs(result_7.numeric_value - 10471.9755) / result_4.numeric_value < tol
        assert result_7.units == "W"
        assert result_7.unit_system == "Power"

        assert abs(result_8.numeric_value - 10.4719755) / result_8.numeric_value < tol
        assert result_8.units == "kW"
        assert result_8.unit_system == "Power"

    def test_07_addition(self):
        v1 = Variable("10mm")
        v2 = Variable(3)
        v3 = Variable("3mA")
        v4 = Variable("10A")
        with pytest.raises(ValueError):
            v1 + v2

        with pytest.raises(ValueError):
            v2 + v1
        result_1 = v2 + v2
        result_2 = v3 + v4
        result_3 = v3 + v3

        assert result_1.numeric_value == 6.0
        assert result_1.unit_system == "None"

        assert result_2.numeric_value == 10.003
        assert result_2.units == "A"
        assert result_2.unit_system == "Current"

        assert result_3.numeric_value == 6.0
        assert result_3.units == "mA"
        assert result_3.unit_system == "Current"

    def test_08_subtraction(self):
        v1 = Variable("10mm")
        v2 = Variable(3)
        v3 = Variable("3mA")
        v4 = Variable("10A")

        with pytest.raises(ValueError):
            v1 - v2

        with pytest.raises(ValueError):
            v2 - v1

        result_1 = v2 - v2
        result_2 = v3 - v4
        result_3 = v3 - v3

        assert result_1.numeric_value == 0.0
        assert result_1.unit_system == "None"

        assert result_2.numeric_value == -9.997
        assert result_2.units == "A"
        assert result_2.unit_system == "Current"

        assert result_3.numeric_value == 0.0
        assert result_3.units == "mA"
        assert result_3.unit_system == "Current"

    def test_09_specify_units(self):
        # Scaling of the unit system "Angle"
        angle = Variable("1rad")
        angle.rescale_to("deg")
        assert isclose(angle.numeric_value, 57.29577951308232)
        angle.rescale_to("degmin")
        assert isclose(angle.numeric_value, 57.29577951308232 * 60.0)
        angle.rescale_to("degsec")
        assert isclose(angle.numeric_value, 57.29577951308232 * 3600.0)

        # Convert 200Hz to Angular speed numerically
        omega = Variable(200 * math.pi * 2, "rad_per_sec")
        assert omega.unit_system == "AngularSpeed"
        assert isclose(omega.value, 1256.6370614359173)
        omega.rescale_to("rpm")
        assert isclose(omega.numeric_value, 12000.0)
        omega.rescale_to("rev_per_sec")
        assert isclose(omega.numeric_value, 200.0)

        # test speed times time equals diestance
        v = Variable("100m_per_sec")
        assert v.unit_system == "Speed"
        v.rescale_to("feet_per_sec")
        assert isclose(v.numeric_value, 328.08398950131)
        v.rescale_to("feet_per_min")
        assert isclose(v.numeric_value, 328.08398950131 * 60)
        v.rescale_to("miles_per_sec")
        assert isclose(v.numeric_value, 0.06213711723534)
        v.rescale_to("miles_per_minute")
        assert isclose(v.numeric_value, 3.72822703412)
        v.rescale_to("miles_per_hour")
        assert isclose(v.numeric_value, 223.69362204724)

        t = Variable("20s")
        distance = v * t
        assert distance.unit_system == "Length"
        assert distance.evaluated_value == "2000.0meter"
        distance.rescale_to("in")
        assert isclose(distance.numeric_value, 2000 / 0.0254)

    def test_10_division(self):
        """
        'Power_divide_Voltage': 'Current',
        'Power_divide_Current': 'Voltage',
        'Power_divide_AngularSpeed': 'Torque',
        'Power_divide_Torque': 'Angular_Speed',
        'Angle_divide_AngularSpeed': 'Time',
        'Angle_divide_Time': 'AngularSpeed',
        'Voltage_divide_Current': 'Resistance',
        'Voltage_divide_Resistance': 'Current',
        'Resistance_divide_AngularSpeed': 'Inductance',
        'Resistance_divide_Inductance': 'AngularSpeed',
        'None_divide_Freq': 'Time',
        'None_divide_Time': 'Freq',
        'Length_divide_Time': 'Speed',
        'Length_divide_Speed': 'Time'
        """

        v1 = Variable("10W")
        v2 = Variable("40V")
        v3 = Variable("1s")
        v4 = Variable("5mA")
        v5 = Variable("100NewtonMeter")
        v6 = Variable("1000rpm")
        tol = 1e-4

        result_1 = v1 / v2
        assert result_1.numeric_value == 0.25
        assert result_1.units == "A"
        assert result_1.unit_system == "Current"

        result_2 = v2 / result_1
        assert result_2.numeric_value == 160.0
        assert result_2.units == "ohm"
        assert result_2.unit_system == "Resistance"

        result_3 = 3 / v3
        assert result_3.numeric_value == 3.0
        assert result_3.units == "Hz"
        assert result_3.unit_system == "Freq"

        result_4 = v3 / 2
        assert abs(result_4.numeric_value - 0.5) < tol
        assert result_4.units == "s"
        assert result_4.unit_system == "Time"

        result_5 = v4 / v5
        assert abs(result_5.numeric_value - 0.00005) < tol
        assert result_5.units == ""
        assert result_5.unit_system == "None"

        result_6 = v1 / v5 + v6
        assert abs(result_6.numeric_value - 104.8198) / result_6.numeric_value < tol
        assert result_6.units == "rad_per_sec"
        assert result_6.unit_system == "AngularSpeed"

    def test_11_delete_variable(self):
        assert self.aedtapp.variable_manager.delete_variable("Var1")

    def test_12_decompose_variable_value(self):
        assert decompose_variable_value("3.123456m") == (3.123456, "m")
        assert decompose_variable_value("3m") == (3, "m")
        assert decompose_variable_value("3") == (3, "")
        assert decompose_variable_value("3.") == (3.0, "")
        assert decompose_variable_value("3.123456m2") == (3.123456, "m2")
        assert decompose_variable_value("3.123456Nm-2") == (3.123456, "Nm-2")
        assert decompose_variable_value("3.123456kg2m2") == (3.123456, "kg2m2")
        assert decompose_variable_value("3.123456kgm2") == (3.123456, "kgm2")

    def test_13_postprocessing(self):
        v1 = self.aedtapp.variable_manager.set_variable("test_post1", 10, is_post_processing=True)
        assert v1
        assert not self.aedtapp.variable_manager.set_variable("test2", "v1+1")
        assert self.aedtapp.variable_manager.set_variable("test2", "test_post1+1", is_post_processing=True)
        x1 = GeometryOperators.parse_dim_arg(
            self.aedtapp.variable_manager["test2"].evaluated_value, variable_manager=self.aedtapp.variable_manager
        )
        assert x1 == 11

    def test_14_intrinsics(self):
        self.aedtapp["fc"] = "Freq"
        assert self.aedtapp["fc"] == "Freq"
        assert self.aedtapp.variable_manager.dependent_variables["fc"].units == self.aedtapp.units.frequency

    def test_15_arrays(self):
        self.aedtapp["arr_index"] = 0
        self.aedtapp["arr1"] = "[1, 2, 3]"
        self.aedtapp["arr2"] = [1, 2, 3]
        self.aedtapp["getvalue1"] = "arr1[arr_index]"
        self.aedtapp["getvalue2"] = "arr2[arr_index]"
        assert self.aedtapp.variable_manager["getvalue1"].numeric_value == 1.0
        assert self.aedtapp.variable_manager["getvalue2"].numeric_value == 1.0

    def test_16_maxwell_circuit_variables(self):
        mc = MaxwellCircuit(version=desktop_version)
        mc["var2"] = "10mm"
        assert mc["var2"] == "10mm"
        v_circuit = mc.variable_manager
        var_circuit = v_circuit.variable_names
        assert "var2" in var_circuit
        assert v_circuit.independent_variables["var2"].units == "mm"
        mc["var3"] = "10deg"
        mc["var4"] = "10rad"
        assert mc["var3"] == "10deg"
        assert mc["var4"] == "10rad"

    def test_17_project_variable_operation(self):
        self.aedtapp["$my_proj_test"] = "1mm"
        self.aedtapp["$my_proj_test2"] = 2
        self.aedtapp["$my_proj_test3"] = "$my_proj_test*$my_proj_test2"
        assert self.aedtapp.variable_manager["$my_proj_test3"].units == "mm"
        assert self.aedtapp.variable_manager["$my_proj_test3"].numeric_value == 2.0

    def test_18_test_optimization_properties(self):
        var = "v1"
        self.aedtapp[var] = "10mm"
        v = self.aedtapp.variable_manager
        assert not v[var].is_optimization_enabled
        v[var].is_optimization_enabled = True
        assert v[var].is_optimization_enabled
        assert v[var].optimization_min_value == "5mm"
        v[var].optimization_min_value = "1m"
        assert v[var].optimization_max_value == "15mm"
        v[var].optimization_max_value = "14mm"
        assert v[var].optimization_max_value == "14mm"
        assert not v[var].is_tuning_enabled
        v[var].is_tuning_enabled = True
        assert v[var].is_tuning_enabled
        assert v[var].tuning_min_value == "5mm"
        v[var].tuning_min_value = "4mm"
        assert v[var].tuning_max_value == "15mm"
        v[var].tuning_max_value = "14mm"
        assert v[var].tuning_max_value == "14mm"
        assert v[var].tuning_step_value == "1mm"
        v[var].tuning_step_value = "0.5mm"
        assert v[var].tuning_step_value == "0.5mm"
        assert not v[var].is_statistical_enabled
        v[var].is_statistical_enabled = True
        assert v[var].is_statistical_enabled
        assert not v[var].is_sensitivity_enabled
        v[var].is_sensitivity_enabled = True
        assert v[var].is_sensitivity_enabled
        assert v[var].sensitivity_min_value == "5mm"
        v[var].sensitivity_min_value = "4mm"
        assert v[var].sensitivity_max_value == "15mm"
        v[var].sensitivity_max_value = "14mm"
        assert v[var].sensitivity_max_value == "14mm"
        assert v[var].sensitivity_initial_disp == "1mm"
        v[var].sensitivity_initial_disp = "0.5mm"
        assert v[var].sensitivity_initial_disp == "0.5mm"

    def test_19_test_optimization_global_properties(self):
        var = "$v1"
        self.aedtapp[var] = "10mm"
        v = self.aedtapp.variable_manager
        assert not v[var].is_optimization_enabled
        v[var].is_optimization_enabled = True
        assert v[var].is_optimization_enabled
        assert v[var].optimization_min_value == "5mm"
        v[var].optimization_min_value = "4mm"
        assert v[var].optimization_max_value == "15mm"
        v[var].optimization_max_value = "14mm"
        assert v[var].optimization_max_value == "14mm"
        assert not v[var].is_tuning_enabled
        v[var].is_tuning_enabled = True
        assert v[var].is_tuning_enabled
        assert v[var].tuning_min_value == "5mm"
        v[var].tuning_min_value = "4mm"
        assert v[var].tuning_max_value == "15mm"
        v[var].tuning_max_value = "14mm"
        assert v[var].tuning_max_value == "14mm"
        assert v[var].tuning_step_value == "1mm"
        v[var].tuning_step_value = "0.5mm"
        assert v[var].tuning_step_value == "0.5mm"
        assert not v[var].is_statistical_enabled
        v[var].is_statistical_enabled = True
        assert v[var].is_statistical_enabled
        assert not v[var].is_sensitivity_enabled
        v[var].is_sensitivity_enabled = True
        assert v[var].is_sensitivity_enabled
        assert v[var].sensitivity_min_value == "5mm"
        v[var].sensitivity_min_value = "4mm"
        assert v[var].sensitivity_max_value == "15mm"
        v[var].sensitivity_max_value = "14mm"
        assert v[var].sensitivity_max_value == "14mm"
        assert v[var].sensitivity_initial_disp == "1mm"
        v[var].sensitivity_initial_disp = "0.5mm"
        assert v[var].sensitivity_initial_disp == "0.5mm"

    def test_20_variable_with_units(self):
        self.aedtapp["v1"] = "3mm"
        self.aedtapp["v2"] = "2*v1"
        assert self.aedtapp.variable_manager.decompose("v1") == (3.0, "mm")
        assert self.aedtapp.variable_manager.decompose("v2") == (6.0, "mm")
        assert self.aedtapp.variable_manager["v2"].decompose() == (6.0, "mm")
        assert self.aedtapp.variable_manager.decompose("5mm") == (5.0, "mm")
        assert self.aedtapp.number_with_units(3.0, "mil") == "3.0mil"

    def test_21_test_validator_exact_match(self, validation_input):
        property_names, expected_settings, actual_settings = validation_input
        validation_errors = generate_validation_errors(property_names, expected_settings, actual_settings)
        assert len(validation_errors) == 0

    def test_22_test_validator_tolerance(self, validation_input):
        property_names, expected_settings, actual_settings = validation_input

        # Small difference should produce no validation errors
        actual_settings[1] = "10.0000000001mm"
        actual_settings[3] = "100.0000000001"
        actual_settings[5] = "100.0000000001"
        validation_errors = generate_validation_errors(property_names, expected_settings, actual_settings)

        assert len(validation_errors) == 0

    def test_23_test_validator_invalidate_offset_type(self, validation_input):
        property_names, expected_settings, actual_settings = validation_input

        # Are expected to be "Absolute Offset"
        actual_settings[0] = "Percentage Offset"

        validation_errors = generate_validation_errors(property_names, expected_settings, actual_settings)

        assert len(validation_errors) == 1

    def test_24_test_validator_invalidate_value(self, validation_input):
        property_names, expected_settings, actual_settings = validation_input

        # Above tolerance
        actual_settings[1] = "10.000002mm"

        validation_errors = generate_validation_errors(property_names, expected_settings, actual_settings)

        assert len(validation_errors) == 1

    def test_25_test_validator_invalidate_unit(self, validation_input):
        property_names, expected_settings, actual_settings = validation_input

        actual_settings[1] = "10in"

        validation_errors = generate_validation_errors(property_names, expected_settings, actual_settings)

        assert len(validation_errors) == 1

    def test_26_test_validator_invalidate_multiple(self, validation_input):
        property_names, expected_settings, actual_settings = validation_input

        actual_settings[0] = "Percentage Offset"
        actual_settings[1] = "22mm"
        actual_settings[2] = "Transverse Percentage Offset"

        validation_errors = generate_validation_errors(property_names, expected_settings, actual_settings)

        assert len(validation_errors) == 3

    def test_27_test_validator_invalidate_wrong_type(self, validation_input):
        property_names, expected_settings, actual_settings = validation_input

        actual_settings[1] = "nonnumeric"

        validation_errors = generate_validation_errors(property_names, expected_settings, actual_settings)

        assert len(validation_errors) == 1

    def test_28_test_validator_float_type(self, validation_float_input):
        property_names, expected_settings, actual_settings = validation_float_input

        validation_errors = generate_validation_errors(property_names, expected_settings, actual_settings)

        assert len(validation_errors) == 0

    def test_29_test_validator_float_type_tolerance(self, validation_float_input):
        property_names, expected_settings, actual_settings = validation_float_input

        # Set just below the tolerance to pass the check
        actual_settings[0] *= 1 + 0.99 * 1e-9
        actual_settings[1] *= 1 - 0.99 * 1e-9
        actual_settings[2] *= 1 + 0.99 * 1e-9

        validation_errors = generate_validation_errors(property_names, expected_settings, actual_settings)

        assert len(validation_errors) == 0

    def test_30_test_validator_float_type_invalidate(self, validation_float_input):
        property_names, expected_settings, actual_settings = validation_float_input

        # Set just above the tolerance to fail the check
        actual_settings[0] *= 1 + 1.01 * 1e-9
        actual_settings[1] *= 1 + 1.01 * 1e-9
        actual_settings[2] *= 1 + 1.01 * 1e-9

        validation_errors = generate_validation_errors(property_names, expected_settings, actual_settings)

        assert len(validation_errors) == 3

    def test_31_test_validator_float_type_invalidate(self, validation_float_input):
        property_names, expected_settings, actual_settings = validation_float_input

        actual_settings[0] *= 2

        validation_errors = generate_validation_errors(property_names, expected_settings, actual_settings)

        assert len(validation_errors) == 1

    def test_32_delete_unused_variables(self):
        self.aedtapp.insert_design("used_variables")
        self.aedtapp["used_var"] = "1mm"
        self.aedtapp["unused_var"] = "1mm"
        self.aedtapp["$project_used_var"] = "1"
        self.aedtapp.modeler.create_rectangle(0, ["used_var", "used_var", "used_var"], [10, 20])
        mat1 = self.aedtapp.materials.add_material("new_copper2")
        mat1.permittivity = "$project_used_var"
        assert self.aedtapp.variable_manager.is_used("used_var")
        assert not self.aedtapp.variable_manager.is_used("unused_var")
        assert self.aedtapp.variable_manager.delete_variable("unused_var")
        self.aedtapp["unused_var"] = "1mm"
        number_of_variables = len(self.aedtapp.variable_manager.variable_names)
        assert self.aedtapp.variable_manager.delete_unused_variables()
        new_number_of_variables = len(self.aedtapp.variable_manager.variable_names)
        assert number_of_variables != new_number_of_variables
