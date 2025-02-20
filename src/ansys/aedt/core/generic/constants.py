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

from enum import IntEnum
from enum import auto
from enum import unique
import math
import warnings

RAD2DEG = 180.0 / math.pi
DEG2RAD = math.pi / 180
HOUR2SEC = 3600.0
MIN2SEC = 60.0
SEC2MIN = 1 / 60.0
SEC2HOUR = 1 / 3600.0
INV2PI = 0.5 / math.pi
V2PI = 2.0 * math.pi
METER2IN = 0.0254
METER2MILES = 1609.344051499
MILS2METER = 39370.078740157
SpeedOfLight = 299792458.0


def db20(x, inverse=True):
    """Convert db20 to decimal and vice versa."""
    if inverse:
        return 20 * math.log10(x)
    else:
        return math.pow(10, x / 20.0)


def db10(x, inverse=True):
    """Convert db10 to decimal and vice versa."""
    if inverse:
        return 10 * math.log10(x)
    else:
        return math.pow(10, x / 10.0)


def dbw(x, inverse=True):
    """Convert W to decimal and vice versa."""
    if inverse:
        return 10 * math.log10(x)
    else:
        return math.pow(10, x / 10.0)


def dbm(x, inverse=True):
    """Convert W to decimal and vice versa."""
    if inverse:
        return 10 * math.log10(x) + 30
    else:
        return math.pow(10, x / 10.0) / 1000


def fah2kel(val, inverse=True):
    """Convert a temperature from Fahrenheit to Kelvin.

    Parameters
    ----------
    val : float
        Temperature value in Fahrenheit.
    inverse : bool, optional
        The default is ``True``.

    Returns
    -------
    float
        Temperature value converted to Kelvin.

    """
    if inverse:
        return (val - 273.15) * 9 / 5 + 32
    else:
        return (val - 32) * 5 / 9 + 273.15


def cel2kel(val, inverse=True):
    """Convert a temperature from Celsius to Kelvin.

    Parameters
    ----------
    val : float
        Temperature value in Celsius.
    inverse : bool, optional
        The default is ``True``.

    Returns
    -------
    float
        Temperature value converted to Kelvin.

    """

    if inverse:
        return val - 273.15
    else:
        return val + 273.15


def unit_system(units):
    """Retrieve the name of the unit system associated with a unit string.

    Parameters
    ----------
    units : str
        Units for retrieving the associated unit system name.

    Returns
    -------
    str
        Key from the ``AEDT_units`` when successful. For example, ``"AngularSpeed"``.
    ``False`` when the units specified are not defined in AEDT units.

    """

    for unit_type, unit_dict in AEDT_UNITS.items():
        if units.lower() in [i.lower() for i in unit_dict.keys()]:
            return unit_type

    return False


def _resolve_unit_system(unit_system_1, unit_system_2, operation):
    """Retrieve the unit string of an arithmetic operation on ``Variable`` objects.

    If no resulting unit system is defined for a specific operation (in unit_system_operations),
    an empty string is returned.

    Parameters
    ----------
    unit_system_1 : str
        Name of a unit system, which is a key of ``AEDT_units``.
    unit_system_2 : str
        Name of another unit system, which is a key of ``AEDT_units``.
    operation : str
        Name of an operator within the data set of ``["multiply" ,"divide"]``.

    Returns
    -------
    str
        Unit system when successful, ``""`` when failed.
    """
    try:
        key = f"{unit_system_1}_{operation}_{unit_system_2}"
        result_unit_system = UNIT_SYSTEM_OPERATIONS[key]
        return SI_UNITS[result_unit_system]
    except KeyError:
        return ""


def unit_converter(values, unit_system="Length", input_units="meter", output_units="mm"):
    """Convert unit in specified unit system.

    Parameters
    ----------
    values : float, list
        Values to convert.
    unit_system : str
        Unit system. Default is `"Length"`.
    input_units : str
        Input units. Default is `"meter"`.
    output_units : str
        Output units. Default is `"mm"`.

    Returns
    -------
    float, list
        Converted value.
    """
    if unit_system in AEDT_UNITS:
        if input_units not in AEDT_UNITS[unit_system]:
            warnings.warn(f"Unknown units: '{input_units}'")
            return values
        elif output_units not in AEDT_UNITS[unit_system]:
            warnings.warn(f"Unknown units: '{output_units}'")
            return values
        else:
            input_is_list = isinstance(values, list)
            if not input_is_list:
                values = [values]
            converted_values = []
            for value in values:
                if unit_system == "Temperature":
                    value = AEDT_UNITS[unit_system][input_units](value, False)
                    value = AEDT_UNITS[unit_system][output_units](value, output_units != "kel")
                elif not callable(AEDT_UNITS[unit_system][input_units]) and not callable(
                    AEDT_UNITS[unit_system][output_units]
                ):
                    value = value * AEDT_UNITS[unit_system][input_units] / AEDT_UNITS[unit_system][output_units]
                elif not callable(AEDT_UNITS[unit_system][input_units]) and callable(
                    AEDT_UNITS[unit_system][output_units]
                ):
                    value = value * AEDT_UNITS[unit_system][input_units]
                    value = AEDT_UNITS[unit_system][output_units](value, True)
                elif callable(AEDT_UNITS[unit_system][input_units]) and not callable(
                    AEDT_UNITS[unit_system][output_units]
                ):
                    value = AEDT_UNITS[unit_system][input_units](value, False) / AEDT_UNITS[unit_system][output_units]
                else:
                    value = AEDT_UNITS[unit_system][input_units](value, False)
                    value = AEDT_UNITS[unit_system][output_units](value, True)

                converted_values.append(value)
            if input_is_list:
                return converted_values
            else:
                return converted_values[0]
    warnings.warn("No system unit found")
    return values


def scale_units(scale_to_unit):
    """Find the scale_to_unit into main system unit.

    Parameters
    ----------
    scale_to_unit : str
        Unit to Scale.

    Returns
    -------
    float
        Return the scaling factor if any.
    """
    sunit = 1.0
    for val in list(AEDT_UNITS.values()):
        for unit, scale_val in val.items():
            if scale_to_unit.lower() == unit.lower():
                sunit = scale_val
                break
        else:
            continue
        break
    return sunit


def validate_enum_class_value(cls, value):
    """Check whether the value for the class ``enumeration-class`` is valid.

    Parameters
    ----------
    cls : class
        Enumeration-style class with integer members in range(0, N) where cls.Invalid equals N-1.
    value : int
        Value to check.

    Returns
    -------
    bool
        ``True`` when the value is valid for the ``enumeration-class``, ``False`` otherwise.
    """
    return isinstance(value, int) and value >= 0 and value < cls.Invalid


AEDT_UNITS = {
    "AngularSpeed": {
        "deg_per_hr": HOUR2SEC * DEG2RAD,
        "rad_per_hr": HOUR2SEC,
        "deg_per_min": MIN2SEC * DEG2RAD,
        "rad_per_min": MIN2SEC,
        "deg_per_sec": DEG2RAD,
        "rad_per_sec": 1.0,
        "rev_per_sec": V2PI,
        "per_sec": V2PI,
        "rpm": SEC2MIN * V2PI,
    },
    "Angle": {"deg": DEG2RAD, "rad": 1.0, "degmin": DEG2RAD * SEC2MIN, "degsec": DEG2RAD * SEC2HOUR},
    "Area": {
        "fm2": 1e-30,
        "pm2": 1e-24,
        "nm2": 1e-18,
        "um2": 1e-12,
        "mm2": 1e-6,
        "cm2": 1e-4,
        "dm2": 1e-2,
        "m2": 1.0,
        "meter2": 1.0,
        "km2": 1e6,
        "uin2": METER2IN * 1e-12,
        "mil2": METER2IN * 1e-6,
        "in2": METER2IN,
        "ft2": METER2IN * 24,
        "yd2": METER2IN * 288,
    },
    "Capacitance": {"fF": 1e-15, "pF": 1e-12, "nF": 1e-9, "uF": 1e-6, "mF": 1e-3, "F": 1.0},
    "Conductance": {"fSie": 1e-15, "pSie": 1e-12, "nSie": 1e-9, "uSie": 1e-6, "mSie": 1e-3, "Sie": 1.0},
    "Current": {
        "fA": 1e-15,
        "pA": 1e-12,
        "nA": 1e-9,
        "uA": 1e-6,
        "mA": 1e-3,
        "A": 1.0,
        "kA": 1e3,
        "MegA": 1e6,
        "gA": 1e9,
        "dBA": (db20,),
    },
    "Flux": {"Wb": 1.0, "mx": 1e-8, "vh": 3600, "vs": 1.0},
    "Force": {
        "fNewton": 1e-15,
        "pNewton": 1e-12,
        "nNewton": 1e-9,
        "uNewton": 1e-6,
        "mNewton": 1e-3,
        "newton": 1.0,
        "kNewton": 1e3,
        "megNewton": 1e6,
        "gNewton": 1e9,
        "dyne": 1e-5,
        "kp": 9.80665,
        "PoundsForce": 4.44822,
    },
    "Frequency": {"Hz": 1.0, "kHz": 1e3, "MHz": 1e6, "GHz": 1e9, "THz": 1e12, "rps": 1.0, "per_sec": 1.0},
    "Freq": {"Hz": 1.0, "kHz": 1e3, "MHz": 1e6, "GHz": 1e9, "THz": 1e12, "rps": 1.0, "per_sec": 1.0},
    "Inductance": {"fH": 1e-15, "pH": 1e-12, "nH": 1e-9, "uH": 1e-6, "mH": 1e-3, "H": 1.0},
    "Length": {
        "fm": 1e-15,
        "pm": 1e-12,
        "nm": 1e-9,
        "um": 1e-6,
        "mm": 1e-3,
        "cm": 1e-2,
        "dm": 1e-1,
        "meter": 1.0,
        "meters": 1.0,
        "km": 1e3,
        "uin": METER2IN * 1e-6,
        "mil": METER2IN * 1e-3,
        "in": METER2IN,
        "ft": METER2IN * 12,
        "yd": METER2IN * 144,
    },
    "Mass": {"ug": 1e-9, "mg": 1e-6, "g": 1e-3, "kg": 1.0, "ton": 1000, "oz": 0.0283495, "lb": 0.453592},
    "None": {
        "f": 1e-15,
        "p": 1e-12,
        "n": 1e-9,
        "u": 1e-6,
        "m": 1e-3,
        "": 1.0,
        "k": 1e3,
        "meg": 1e6,
        "g": 1e9,
        "t": 1e12,
    },
    "Resistance": {"uOhm": 1e-6, "mOhm": 1e-3, "ohm": 1.0, "kOhm": 1e3, "megohm": 1e6, "GOhm": 1e9},
    "Speed": {
        "mm_per_sec": 1e-3,
        "cm_per_sec": 1e-2,
        "m_per_sec": 1.0,
        "km_per_sec": 1e3,
        "inches_per_sec": METER2IN,
        "feet_per_sec": METER2IN * 12,
        "feet_per_min": METER2IN * 12 * SEC2MIN,
        "km_per_min": 60e3,
        "m_per_h": 3600,
        "miles_per_hour": METER2MILES * SEC2HOUR,
        "miles_per_minute": METER2MILES * SEC2MIN,
        "miles_per_sec": METER2MILES,
    },
    "Time": {
        "fs": 1e-15,
        "ps": 1e-12,
        "ns": 1e-9,
        "us": 1e-6,
        "ms": 1e-3,
        "s": 1,
        "min": 60,
        "hour": 3600,
        "day": 3600 * 12,
    },
    "Torque": {
        "fNewtonMeter": 1e-15,
        "pNewtonMeter": 1e-12,
        "nNewtonMeter": 1e-9,
        "uNewtonMeter": 1e-6,
        "mNewtonMeter": 1e-3,
        "cNewtonMeter": 1e-2,
        "NewtonMeter": 1,
        "kNewtonMeter": 1e3,
        "megNewtonMeter": 1e6,
        "gNewtonMeter": 1e9,
    },
    "Voltage": {
        "fV": 1e-15,
        "pV": 1e-12,
        "nV": 1e-9,
        "uV": 1e-6,
        "mV": 1e-3,
        "V": 1.0,
        "kV": 1e3,
        "MegV": 1e6,
        "gV": 1e9,
        "dBV": db20,
    },
    "Temperature": {"kel": lambda x, y: x, "cel": cel2kel, "fah": fah2kel},
    "Power": {
        "fW": 1e-15,
        "pW": 1e-12,
        "nW": 1e-9,
        "uW": 1e-6,
        "mW": 1e-3,
        "W": 1.0,
        "kW": 1e3,
        "megW": 1e6,
        "gW": 1e9,
        "Btu_per_hr": 3.4129693,
        "Btu_per_sec": 9.48047e-4,
        "dBm": dbm,
        "dBW": dbw,
        "HP": 1.34102e-3,
        "erg_per_sec": 1e7,
    },
    "B-field": {
        "ftesla": 1e-15,
        "ptesla": 1e-12,
        "ntesla": 1e-9,
        "utesla": 1e-6,
        "mtesla": 1e-3,
        "tesla": 1.0,
        "ktesla": 1e3,
        "megtesla": 1e6,
        "gtesla": 1e9,
    },
    "E-field": {
        "fV_per_m": 1e-15,
        "pV_per_m": 1e-12,
        "nV_per_m": 1e-9,
        "uV_per_m": 1e-6,
        "mV_per_m": 1e-3,
        "V_per_m": 1.0,
        "kV_per_m": 1e3,
        "megV_per_m": 1e6,
        "gV_per_m": 1e9,
        "fV_per_meter": 1e-15,
        "pV_per_meter": 1e-12,
        "nV_per_meter": 1e-9,
        "uV_per_meter": 1e-6,
        "mV_per_meter": 1e-3,
        "V_per_meter": 1.0,
        "kV_per_meter": 1e3,
        "megV_per_meter": 1e6,
        "gV_per_meter": 1e9,
    },
    "H-field": {
        "fA_per_m": 1e-15,
        "pA_per_m": 1e-12,
        "nA_per_m": 1e-9,
        "uA_per_m": 1e-6,
        "mA_per_m": 1e-3,
        "A_per_m": 1.0,
        "kA_per_m": 1e3,
        "megA_per_m": 1e6,
        "gA_per_m": 1e9,
        "fA_per_meter": 1e-15,
        "pA_per_meter": 1e-12,
        "nA_per_meter": 1e-9,
        "uA_per_meter": 1e-6,
        "mA_per_meter": 1e-3,
        "A_per_meter": 1.0,
        "kA_per_meter": 1e3,
        "megA_per_meter": 1e6,
        "gA_per_meter": 1e9,
    },
    "SurfaceHeat": {
        "uW_per_m2": 1e-6,
        "mW_per_m2": 1e-3,
        "irrad_W_per_m2": 1.0,
        "W_per_m2": 1.0,
        "kW_per_m2": 1e3,
        "megW_per_m2": 1e6,
        "irrad_W_per_cm2": 1e4,
        "W_per_cm2": 1e4,
        "W_per_in2": 1550,
        "erg_per_s_per_cm2": 1e-3,
        "btu_per_hr_per_ft2": 3.15,
        "btu_per_s_per_ft2": 11356.53,
        "irrad_W_per_mm2": 1e6,
        "irrad_met": 1.0,
    },
    "J-field": {
        "fA_per_m2": 1e-15,
        "pA_per_m2": 1e-12,
        "nA_per_m2": 1e-9,
        "uA_per_m2": 1e-6,
        "mA_per_m2": 1e-3,
        "A_per_m2": 1.0,
        "kA_per_m2": 1e3,
        "megA_per_m2": 1e6,
        "gA_per_m2": 1e9,
        "fA_per_meter2": 1e-15,
        "pA_per_meter2": 1e-12,
        "nA_per_meter2": 1e-9,
        "uA_per_meter2": 1e-6,
        "mA_per_meter2": 1e-3,
        "A_per_meter2": 1.0,
        "kA_per_meter2": 1e3,
        "megA_per_meter2": 1e6,
        "gA_per_meter2": 1e9,
    },
}
SI_UNITS = {
    "AngularSpeed": "rad_per_sec",
    "Angle": "rad",
    "Area": "m2",
    "Capacitance": "F",
    "Conductance": "Sie",
    "Current": "A",
    "Flux": "vs",
    "Force": "newton",
    "Freq": "Hz",
    "Inductance": "H",
    "Length": "meter",
    "Mass": "kg",
    "None": "",
    "Resistance": "ohm",
    "Speed": "m_per_sec",
    "SurfaceHeat": "W_per_m2",
    "Time": "s",
    "Torque": "NewtonMeter",
    "Voltage": "V",
    "Temperature": "kel",
    "Power": "W",
    "B-field": "tesla",
    "E-field": "V_per_meter",
    "H-field": "A_per_meter",
    "J-field": "A_per_m2",
}
UNIT_SYSTEM_OPERATIONS = {
    # Multiplication of physical domains
    "Voltage_multiply_Current": "Power",
    "Torque_multiply_AngularSpeed": "Power",
    "AngularSpeed_multiply_Time": "Angle",
    "Current_multiply_Resistance": "Voltage",
    "AngularSpeed_multiply_Inductance": "Resistance",
    "Speed_multiply_Time": "Length",
    # Division of Physical Domains
    "Power_divide_Voltage": "Current",
    "Power_divide_Current": "Voltage",
    "Power_divide_AngularSpeed": "Torque",
    "Power_divide_Torque": "AngularSpeed",
    "Angle_divide_AngularSpeed": "Time",
    "Angle_divide_Time": "AngularSpeed",
    "Voltage_divide_Current": "Resistance",
    "Voltage_divide_Resistance": "Current",
    "Resistance_divide_AngularSpeed": "Inductance",
    "Resistance_divide_Inductance": "AngularSpeed",
    "None_divide_Freq": "Time",
    "None_divide_Time": "Freq",
    "Length_divide_Time": "Speed",
    "Length_divide_Speed": "Time",
}


class INFINITE_SPHERE_TYPE(object):
    """INFINITE_SPHERE_TYPE Enumerator class."""

    (ThetaPhi, AzOverEl, ElOverAz) = ("Theta-Phi", "Az Over El", "El Over Az")


class FILLET(object):
    """FilletType Enumerator class."""

    (Round, Mitered) = range(0, 2)


class AXIS(object):
    """CoordinateSystemAxis Enumerator class."""

    (X, Y, Z) = range(0, 3)


class PLANE(object):
    """CoordinateSystemPlane Enumerator class."""

    (YZ, ZX, XY) = range(0, 3)


class GRAVITY(object):
    """GravityDirection Enumerator class."""

    (XNeg, YNeg, ZNeg, XPos, YPos, ZPos) = range(0, 6)


class VIEW(object):
    """View Enumerator class."""

    (XY, YZ, ZX, ISO) = ("XY", "YZ", "ZX", "iso")


class GLOBALCS(object):
    """GlobalCS Enumerator class."""

    (XY, YZ, ZX) = ("Global:XY", "Global:YZ", "Global:XZ")


class MATRIXOPERATIONSQ3D(object):
    """Matrix Reduction types."""

    (JoinSeries, JoinParallel, FloatNet, GroundNet, FloatTerminal, FloatInfinity, ReturnPath, AddSink, MoveSink) = (
        "JoinSeries",
        "JoinParallel",
        "FloatNet",
        "GroundNet",
        "FloatTerminal",
        "FloatInfinity",
        "ReturnPath",
        "AddSink",
        "MoveSink",
    )


class MATRIXOPERATIONSQ2D(object):
    """Matrix Reduction types."""

    (AddGround, SetReferenceGround, Float, Parallel, DiffPair) = (
        "AddGround",
        "SetReferenceGround",
        "Float",
        "Parallel",
        "DiffPair",
    )


class CATEGORIESQ3D(object):
    """Plot Categories for Q2d and Q3d."""

    class Q2D(object):
        (
            CMatrix,
            GMatrix,
            RMatrix,
            LMatrix,
            LumpedC,
            LumpedG,
            LumpedR,
            LumpedL,
            CharacteristicImpedance,
            CrossTalkForward,
            LumpedCrossTalkForward,
            CrossTalkBackward,
        ) = ("C", "G", "R", "L", "lumpC", "lumpG", "lumpR", "lumpL", "Z0", "Kf", "lumpKf", "Kb")

    class Q3D(object):
        (C, G, DCL, DCR, ACL, ACR) = ("C", "G", "DCL", "DCR", "ACL", "ACR")


class CSMODE(object):
    """COORDINATE SYSTEM MODE Enumerator class."""

    (View, Axis, ZXZ, ZYZ, AXISROTATION) = ("view", "axis", "zxz", "zyz", "axisrotation")


class SEGMENTTYPE(object):
    """CROSSSECTION Enumerator class."""

    (Line, Arc, Spline, AngularArc) = range(0, 4)


class CROSSSECTION(object):
    """CROSSSECTION Enumerator class."""

    (NONE, Line, Circle, Rectangle, Trapezoid) = range(0, 5)


class SWEEPDRAFT(object):
    """SweepDraftType Enumerator class."""

    (Extended, Round, Natural, Mixed) = range(0, 4)


class FlipChipOrientation(object):
    """Chip orientation enumerator class."""

    (Up, Down) = range(0, 2)


class SolverType(object):
    """Provides solver type classes."""

    (Hfss, Siwave, Q3D, Maxwell, Nexxim, TwinBuilder, Hfss3dLayout, SiwaveSYZ, SiwaveDC) = range(0, 9)


class CutoutSubdesignType(object):
    (BoundingBox, Conformal, ConvexHull, Invalid) = range(0, 4)


class RadiationBoxType(object):
    (BoundingBox, Conformal, ConvexHull, Polygon, Invalid) = range(0, 5)


class SweepType(object):
    (Linear, LogCount, Invalid) = range(0, 3)


class BasisOrder(object):
    """Enumeration-class for HFSS basis order settings.

    Warning: the value ``single`` has been renamed to ``Single`` for consistency. Please update references to
    ``single``.
    """

    (Mixed, Zero, Single, Double, Invalid) = (-1, 0, 1, 2, 3)


class NodeType(object):
    """Type of node for source creation."""

    (Positive, Negative, Floating) = range(0, 3)


class SourceType(object):
    """Type of excitation enumerator."""

    (CoaxPort, CircPort, LumpedPort, Vsource, Isource, Rlc, DcTerminal) = range(0, 7)


class SOLUTIONS(object):
    """Provides the names of default solution types."""

    class Hfss(object):
        """Provides HFSS solution types."""

        (DrivenModal, DrivenTerminal, EigenMode, Transient, SBR, Characteristic) = (
            "Modal",
            "Terminal",
            "Eigenmode",
            "Transient Network",
            "SBR+",
            "Characteristic",
        )

    class Maxwell3d(object):
        """Provides Maxwell 3D solution types."""

        (
            Transient,
            Magnetostatic,
            EddyCurrent,
            ElectroStatic,
            DCConduction,
            ElectroDCConduction,
            ACConduction,
            ElectricTransient,
            TransientAPhiFormulation,
            DCBiasedEddyCurrent,
        ) = (
            "Transient",
            "Magnetostatic",
            "EddyCurrent",
            "Electrostatic",
            "DCConduction",
            "ElectroDCConduction",
            "ACConduction",
            "ElectricTransient",
            "TransientAPhiFormulation",
            "DCBiasedEddyCurrent",
        )

    class Maxwell2d(object):
        """Provides Maxwell 2D solution types."""

        (
            TransientXY,
            TransientZ,
            MagnetostaticXY,
            MagnetostaticZ,
            EddyCurrentXY,
            EddyCurrentZ,
            ElectroStaticXY,
            ElectroStaticZ,
            DCConductionXY,
            DCConductionZ,
            ACConductionXY,
            ACConductionZ,
        ) = (
            "TransientXY",
            "TransientZ",
            "MagnetostaticXY",
            "MagnetostaticZ",
            "EddyCurrentXY",
            "EddyCurrentZ",
            "ElectrostaticXY",
            "ElectrostaticZ",
            "DCConductionXY",
            "DCConductionZ",
            "ACConductionXY",
            "ACConductionZ",
        )

    class Icepak(object):
        """Provides Icepak solution types."""

        (
            SteadyState,
            Transient,
        ) = (
            "SteadyState",
            "Transient",
        )

    class Circuit(object):
        """Provides Circuit solution types."""

        (
            NexximLNA,
            NexximDC,
            NexximTransient,
            NexximQuickEye,
            NexximVerifEye,
            NexximAMI,
            NexximOscillatorRSF,
            NexximOscillator1T,
            NexximOscillatorNT,
            NexximHarmonicBalance1T,
            NexximHarmonicBalanceNT,
            NexximSystem,
            NexximTVNoise,
            HSPICE,
            TR,
        ) = (
            "NexximLNA",
            "NexximDC",
            "NexximTransient",
            "NexximQuickEye",
            "NexximVerifEye",
            "NexximAMI",
            "NexximOscillatorRSF",
            "NexximOscillator1T",
            "NexximOscillatorNT",
            "NexximHarmonicBalance1T",
            "NexximHarmonicBalanceNT",
            "NexximSystem",
            "NexximTVNoise",
            "HSPICE",
            "TR",
        )

    class Mechanical(object):
        """Provides Mechanical solution types."""

        (Thermal, Structural, Modal, SteadyStateThermal) = ("Thermal", "Structural", "Modal", "Steady-State Thermal")


class SETUPS(object):
    """Provides constants for the default setup types."""

    (
        HFSSDrivenAuto,
        HFSSDrivenDefault,
        HFSSEigen,
        HFSSTransient,
        HFSSSBR,
        MaxwellTransient,
        Magnetostatic,
        EddyCurrent,
        Electrostatic,
        ElectrostaticDC,
        ElectricTransient,
        SteadyState,
        SteadyState,
        SteadyState,
        Matrix,
        NexximLNA,
        NexximDC,
        NexximTransient,
        NexximQuickEye,
        NexximVerifEye,
        NexximAMI,
        NexximOscillatorRSF,
        NexximOscillator1T,
        NexximOscillatorNT,
        NexximHarmonicBalance1T,
        NexximHarmonicBalanceNT,
        NexximSystem,
        NexximTVNoise,
        HSPICE,
        HFSS3DLayout,
        Open,
        Close,
        MechTerm,
        MechModal,
        GRM,
        TR,
        Transient,
        Transient,
        Transient,
        DFIG,
        TPIM,
        SPIM,
        TPSM,
        BLDC,
        ASSM,
        PMDC,
        SRM,
        LSSM,
        UNIM,
        DCM,
        CPSM,
        NSSM,
    ) = range(0, 52)


CSS4_COLORS = {
    "chocolate": "#D2691E",
    "darkgreen": "#006400",
    "orangered": "#FF4500",
    "darkseagreen": "#8FBC8F",
    "darkmagenta": "#8B008B",
    "saddlebrown": "#8B4513",
    "mediumaquamarine": "#66CDAA",
    "limegreen": "#32CD32",
    "blue": "#0000FF",
    "mediumseagreen": "#3CB371",
    "peru": "#CD853F",
    "turquoise": "#40E0D0",
    "darkcyan": "#008B8B",
    "olivedrab": "#6B8E23",
    "cyan": "#00FFFF",
    "aquamarine": "#7FFFD4",
    "powderblue": "#B0E0E6",
    "hotpink": "#FF69B4",
    "palegreen": "#98FB98",
    "darkturquoise": "#00CED1",
    "magenta": "#FF00FF",
    "slateblue": "#6A5ACD",
    "lightgreen": "#90EE90",
    "sienna": "#A0522D",
    "darkorchid": "#9932CC",
    "orange": "#FFA500",
    "forestgreen": "#228B22",
    "palegoldenrod": "#EEE8AA",
    "blueviolet": "#8A2BE2",
    "royalblue": "#4169E1",
    "teal": "#008080",
    "darkgoldenrod": "#B8860B",
    "lightskyblue": "#87CEFA",
    "lime": "#00FF00",
    "orchid": "#DA70D6",
    "mediumorchid": "#BA55D3",
    "indigo": "#4B0082",
    "mediumspringgreen": "#00FA9A",
    "tomato": "#FF6347",
    "mediumblue": "#0000CD",
    "midnightblue": "#191970",
    "deepskyblue": "#00BFFF",
    "salmon": "#FA8072",
    "rosybrown": "#BC8F8F",
    "mediumslateblue": "#7B68EE",
    "moccasin": "#FFE4B5",
    "paleturquoise": "#AFEEEE",
    "darkblue": "#00008B",
    "navy": "#000080",
    "steelblue": "#4682B4",
    "crimson": "#DC143C",
    "red": "#FF0000",
    "bisque": "#FFE4C4",
    "darkslategray": "#2F4F4F",
    "maroon": "#800000",
    "mediumpurple": "#9370DB",
    "darkslateblue": "#483D8B",
    "darksalmon": "#E9967A",
    "deeppink": "#FF1493",
    "seagreen": "#2E8B57",
    "mediumvioletred": "#C71585",
    "greenyellow": "#ADFF2F",
    "springgreen": "#00FF7F",
    "sandybrown": "#F4A460",
    "brown": "#A52A2A",
    "lightpink": "#FFB6C1",
    "olive": "#808000",
    "burlywood": "#DEB887",
    "dodgerblue": "#1E90FF",
    "darkolivegreen": "#556B2F",
    "lightsalmon": "#FFA07A",
    "aqua": "#00FFFF",
    "khaki": "#F0E68C",
    "pink": "#FFC0CB",
    "green": "#008000",
    "darkorange": "#FF8C00",
    "rebeccapurple": "#663399",
    "coral": "#FF7F50",
    "darkviolet": "#9400D3",
    "purple": "#800080",
    "palevioletred": "#DB7093",
    "lightseagreen": "#20B2AA",
    "indianred": "#CD5C5C",
    "darkkhaki": "#BDB76B",
    "lightcoral": "#F08080",
    "mediumturquoise": "#48D1CC",
    "peachpuff": "#FFDAB9",
    "skyblue": "#87CEEB",
    "fuchsia": "#FF00FF",
    "navajowhite": "#FFDEAD",
    "lawngreen": "#7CFC00",
    "cornflowerblue": "#6495ED",
    "tan": "#D2B48C",
    "darkred": "#8B0000",
    "firebrick": "#B22222",
    "gold": "#FFD700",
    "yellow": "#FFFF00",
    "wheat": "#F5DEB3",
    "chartreuse": "#7FFF00",
    "goldenrod": "#DAA520",
    "violet": "#EE82EE",
    "yellowgreen": "#9ACD32",
    "cadetblue": "#5F9EA0",
    "plum": "#DDA0DD",
}


class LineStyle(object):
    """Provides trace line style constants."""

    (Solid, Dot, ShortDash, DotShortDash, Dash, DotDash, DotDot, DotDotDash, LongDash) = (
        "Solid",
        "Dot",
        "ShortDash",
        "DotShortDash",
        "Dash",
        "DotDash",
        "DotDot",
        "DotDotDash",
        "LongDash",
    )


class TraceType(object):
    """Provides trace type constants."""

    (Continuous, Discrete, StickZero, StickInfinity, BarZero, BarInfinity, Histogram, Step, Stair, Digital) = (
        "Continuous",
        "Discrete",
        "Stick Zero",
        "Stick Infinity",
        "Bar Zero",
        "Bar Infinity",
        "Histogram",
        "Step",
        "Stair",
        "Digital",
    )


class SymbolStyle(object):
    """Provides symbol style constants."""

    (
        Box,
        Circle,
        VerticalEllipse,
        HorizontalEllipse,
        VerticalUpTriangle,
        VerticalDownTriangle,
        HorizontalLeftTriangle,
        HorizontalRightTriangle,
    ) = (
        "Box",
        "Circle",
        "VerticalEllipse",
        "HorizontalEllipse",
        "VerticalUpTriangle",
        "VerticalDownTriangle",
        "HorizontalLeftTriangle",
        "HorizontalRightTriangle",
    )


@unique
class EnumUnits(IntEnum):
    # Frequency
    hz = 0
    khz = auto()
    mhz = auto()
    ghz = auto()
    thz = auto()
    rps = auto()
    dbFrequency = auto()
    # Resistance
    mohm = auto()
    ohm = auto()
    kohm = auto()
    megohm = auto()
    gohm = auto()
    dbResistance = auto()
    # Conductance
    fsie = auto()
    psie = auto()
    nsie = auto()
    usie = auto()
    msie = auto()
    sie = auto()
    dbConductance = auto()
    # Inductance
    fh = auto()
    ph = auto()
    nh = auto()
    uh = auto()
    mh = auto()
    h = auto()
    dbInductance = auto()
    # Capacitance
    ff = auto()
    pf = auto()
    nf = auto()
    uf = auto()
    mf = auto()
    farad = auto()
    dbCapacitance = auto()
    # Length
    nm = auto()
    um = auto()
    mm = auto()
    meter = auto()
    cm = auto()
    ft = auto()
    inch = auto()  # actually it is "in" but would not be valid
    mil = auto()
    uin = auto()
    dbLength = auto()
    # Time
    fs = auto()
    ps = auto()
    ns = auto()
    us = auto()
    ms = auto()
    s = auto()
    dbTime = auto()
    # Angle
    deg = auto()
    rad = auto()
    dbAngle = auto()
    # Power
    fw = auto()
    pw = auto()
    nw = auto()
    uw = auto()
    mw = auto()
    w = auto()
    dbm = auto()
    dbw = auto()
    dbPower = auto()
    # Voltage
    fv = auto()
    pv = auto()
    nv = auto()
    uv = auto()
    mv = auto()
    v = auto()
    kv = auto()
    dbv = auto()
    dbVoltage = auto()
    # Current
    fa = auto()
    pa = auto()
    na = auto()
    ua = auto()
    ma = auto()
    a = auto()
    dbCurrent = auto()
    # Temperature
    kel = auto()
    cel = auto()
    fah = auto()
    dbTemperature = auto()
    # Noise spectrum (dBc/Hz)
    dbchz = auto()
    dbNoiseSpectrum = auto()
    # Mass (obsolete:  replaced with new enum below)
    oz_obsolete = auto()
    dbWeight_obsolete = auto()
    # Volume
    l = auto()
    ml = auto()
    dbVolume = auto()
    # Magnetic Induction
    gauss = auto()
    ugauss = auto()
    tesla = auto()
    utesla = auto()
    dbMagInduction = auto()
    # Magnetic Field Strength
    oersted = auto()
    a_per_meter = auto()
    dbMagFieldStrength = auto()
    # Force
    fnewton = auto()
    pnewton = auto()
    nnewton = auto()
    unewton = auto()
    mnewton = auto()
    newton = auto()
    knewton = auto()
    megnewton = auto()
    gnewton = auto()
    lbForce = auto()
    dbForce = auto()
    # Torque
    fnewtonmeter = auto()
    pnewtonmeter = auto()
    nnewtonmeter = auto()
    unewtonmeter = auto()
    mnewtonmeter = auto()
    newtonmeter = auto()
    knewtonmeter = auto()
    megnewtonmeter = auto()
    gnewtonmeter = auto()
    OzIn = auto()
    LbIn = auto()
    ftlb = auto()
    GmCm = auto()
    KgCm = auto()
    KgMeter = auto()
    dbTorque = auto()
    # Speed (mph is meter_per_hour)
    mmps = auto()
    cmps = auto()
    mps = auto()
    mph = auto()
    fps = auto()
    fpm = auto()
    miph = auto()
    dbSpeed = auto()
    # AngularSpeed
    rpm = auto()
    degps = auto()
    degpm = auto()
    degph = auto()
    radps = auto()
    radpm = auto()
    radph = auto()
    dbAngularSpeed = auto()
    # Flux
    weber = auto()
    dbFlux = auto()
    # ElectricFieldStrength
    vpm = auto()
    # Mass (replaces obsolete previous)
    ugram = auto()
    mgram = auto()
    gram = auto()
    kgram = auto()
    oz = auto()
    lb = auto()
    dbMass = auto()
    # More Length
    km = auto()
    # More Voltage
    megv = auto()
    # More Current
    ka = auto()
    # More MagneticInduction
    mtesla = auto()
    mgauss = auto()
    kgauss = auto()
    ktesla = auto()
    # More MagneticFieldStrength
    ka_per_meter = auto()
    koersted = auto()
    # More power units
    kw = auto()
    horsepower = auto()
    btu_per_hr = auto()
    # More speed units
    km_per_hr = auto()
    km_per_min = auto()
    km_per_sec = auto()
    mi_per_min = auto()
    mi_per_sec = auto()
    in_per_sec = auto()
    # Pressure units
    n_per_msq = auto()
    kn_per_msq = auto()
    megn_per_msq = auto()
    gn_per_msq = auto()
    psi = auto()
    kpsi = auto()
    megpsi = auto()
    gpsi = auto()
    #
    upascal = auto()
    mpascal = auto()
    cpascal = auto()
    dpascal = auto()
    pascal = auto()
    hpascal = auto()
    kpascal = auto()
    megpascal = auto()
    gpascal = auto()
    # kAcceleration
    inps2 = auto()
    mmps2 = auto()
    cmps2 = auto()
    mps2 = auto()
    # kAIGB
    aigb2 = auto()
    aigb1 = auto()
    # kAmountOfSubstance
    nmol = auto()
    umol = auto()
    mmol = auto()
    mol = auto()
    kmol = auto()
    # kAngle
    degsec = auto()
    degmin = auto()
    # kAngleCoefficient
    perdeg = auto()
    perrad = auto()
    vpervperdeg = auto()
    vpervperrad = auto()
    # kAngularAcceleration
    degpers2 = auto()
    pers2 = auto()
    radpers2 = auto()
    # kAngularDamping
    dmsperrad = auto()
    nmsperrad = auto()
    kmsperrad = auto()
    # kAngularJerk
    jerk_degpers2 = auto()
    jerk_radpers2 = auto()
    # kAngularMomentum
    kgm2pers = auto()
    newtonmetersec = auto()
    # kAngularSpeed
    AngRps = auto()
    AngSpers = auto()
    # kAngularStiffness
    newtonmeterperdeg = auto()
    newtonmeterperrad = auto()
    # kAngularWindage
    kgm2perrad2 = auto()
    nms2perrad2 = auto()
    # kArea
    in2 = auto()
    ft2 = auto()
    um2 = auto()
    mm2 = auto()
    cm2 = auto()
    m2 = auto()
    km2 = auto()
    # kAreaCoefficient
    percm2 = auto()
    perm2 = auto()
    # kArealFlowRate (also Diffusivity)
    m2perhour = auto()
    m2permin = auto()
    m2pers = auto()
    # kAreaPerPower
    m2perJs = auto()
    m2perw = auto()
    # kAreaPerVoltage
    Am2perkW = auto()
    Am2perW = auto()
    m2perkV = auto()
    m2perV = auto()
    # kAreaPerVoltageTemperature
    Am2perWKel = auto()
    m2perVKel = auto()
    # kBIGB
    bigB1 = auto()
    bigB2 = auto()
    # kCapacitancePerArea
    Fpercm2 = auto()
    nFperm2 = auto()
    uFperm2 = auto()
    mFperm2 = auto()
    Fperm2 = auto()
    # kCapacitancePerAreaPerVoltage
    pFperVm2 = auto()
    nFperVm2 = auto()
    uFperVm2 = auto()
    mFperVm2 = auto()
    FperVm2 = auto()
    # kCapacitancePerLength
    pFperm = auto()
    nFperm = auto()
    uFperm = auto()
    mFperm = auto()
    Fperm = auto()
    # kCapacitanceTemperatureCoeff
    nFperCel = auto()
    uFperCel = auto()
    FperCel = auto()
    pFperFah = auto()
    nFperFah = auto()
    uFperFah = auto()
    mFperFah = auto()
    FperFah = auto()
    mFperCel = auto()
    pFperCel = auto()
    pFperKel = auto()
    nFperKel = auto()
    uFperKel = auto()
    mFperKel = auto()
    FperKel = auto()
    # kCharge
    As = auto()
    Ah = auto()
    nC = auto()
    uC = auto()
    mC = auto()
    C = auto()
    kC = auto()
    # kCompliance
    inperlbf = auto()
    cmperN = auto()
    mperN = auto()
    # kConductance
    mho = auto()
    inverseohm = auto()
    apv = auto()
    ksie = auto()
    megsie = auto()
    # kConductancePerLength
    uSperm = auto()
    mSperm = auto()
    cSperm = auto()
    Sperm = auto()
    kSperm = auto()
    # kCurrentChangeRate
    Apermin = auto()
    Aperhour = auto()
    uApers = auto()
    mApers = auto()
    Apers = auto()
    kApers = auto()
    # kCurrentDensity
    uApercm2 = auto()
    mApercm2 = auto()
    Apercm2 = auto()
    uAperm2 = auto()
    mAperm2 = auto()
    Aperm2 = auto()
    Apermm2 = auto()
    # kCurrentGain
    ApermA = auto()
    mAperA = auto()
    AperA = auto()
    # kCurrentLengthPerVoltage
    uAmperV = auto()
    mAmperV = auto()
    AmperV = auto()
    # kCurrentPerCharge
    AperC = auto()
    AperAhour = auto()
    AperAs = auto()
    # kCurrentPerIrradiance
    uAperWperm2 = auto()
    mAperWperm2 = auto()
    AperWperm2 = auto()
    kAperWperm2 = auto()
    # kCurrentPerLength
    uAperm = auto()
    mAperm = auto()
    Aperm = auto()
    kAperm = auto()
    # kCurrentPerTemperature2_half
    AperKel2half = auto()
    # kCurrentPerTemperatureCubed
    AperKel3 = auto()
    # kCurrentPerTemperatureDiffCubed
    AperCelDiff3 = auto()
    AperKelDiff3 = auto()
    # kCurrentSquaredTime
    mA2s = auto()
    A2s = auto()
    # kCurrentTemperatureCoeff
    uAperCel = auto()
    mAperCel = auto()
    AperCel = auto()
    mAperFah = auto()
    AperFah = auto()
    uAperKel = auto()
    mAperKel = auto()
    AperKel = auto()
    kAperKel = auto()
    # kDamping
    mNsperm = auto()
    cNsperm = auto()
    dNsperm = auto()
    Nsperm = auto()
    kNsperm = auto()
    # kDensity
    gpcm3 = auto()
    gpl = auto()
    kgpl = auto()
    kgpdm3 = auto()
    kgpm3 = auto()
    # kElectricFieldStrength
    vpcm = auto()
    # kElectricFluxDensity
    nCperm2 = auto()
    uCperm2 = auto()
    mCperm2 = auto()
    Cperm2 = auto()
    # kEnergy
    Whour = auto()
    kWhour = auto()
    eV = auto()
    erg = auto()
    Ws = auto()
    uJ = auto()
    mJ = auto()
    J = auto()
    kJ = auto()
    megJ = auto()
    GJ = auto()
    # kFluidicCapacitance
    cm3perPa = auto()
    m3perPa = auto()
    # kFluidicConductance
    cm3perPas = auto()
    m3perPas = auto()
    # kFluidicResistance
    Nsperm5 = auto()
    Pasperm3 = auto()
    # kFlux
    maxwell = auto()
    vh = auto()
    vs = auto()
    # kForce
    dyne = auto()
    kpond = auto()
    # kFrequency
    persec = auto()
    # kIlluminance
    lmperm2 = auto()
    lmpercm2 = auto()
    Wperm2 = auto()
    Wpercm2 = auto()
    lmperin2 = auto()
    lx = auto()
    klx = auto()
    meglx = auto()
    # kInductancePerLength
    pHperm = auto()
    nHperm = auto()
    uHperm = auto()
    mHperm = auto()
    Hperm = auto()
    # kInertance
    kgperm4 = auto()
    Ns2perm5 = auto()
    Pas2perm3 = auto()
    # kIrradiance
    IrradWpercm2 = auto()
    Wperin2 = auto()
    uWperm2 = auto()
    mWperm2 = auto()
    IrradWperm2 = auto()
    kWperm2 = auto()
    megWperm2 = auto()
    # kJerk
    inpers3 = auto()
    nmpers3 = auto()
    umpers3 = auto()
    mmpers3 = auto()
    cmpers3 = auto()
    mpers3 = auto()
    # kLength
    yd = auto()
    mileUS = auto()
    ltyr = auto()
    mileNaut = auto()
    fm = auto()
    pm = auto()
    dm = auto()
    mileTerr = auto()
    # kLength2PerVoltage2
    m2perV2 = auto()
    # kLengthCoefficient
    percm = auto()
    permm = auto()
    perum = auto()
    perkm = auto()
    perin = auto()
    VperVperm = auto()
    VperVperin = auto()
    perm = auto()
    # kLengthPerVoltage
    umperV = auto()
    mmperV = auto()
    cmperV = auto()
    dmperV = auto()
    mperV = auto()
    kmperV = auto()
    # kLengthPerVoltageRoot
    umperVhalf = auto()
    mmperVhalf = auto()
    cmperVhalf = auto()
    dmperVhalf = auto()
    mperVhalf = auto()
    kmperVhalf = auto()
    # kLuminousFlux
    gm2pers3 = auto()
    mlm = auto()
    lm = auto()
    klm = auto()
    meglm = auto()
    # kLuminousIntensity
    mCd = auto()
    Cd = auto()
    kCd = auto()
    megCd = auto()
    GCd = auto()
    # kMagneticReluctance
    AperVs = auto()
    AperWb = auto()
    # kMassFlowRate
    gpers = auto()
    kgpers = auto()
    # kMolarDensity
    molperdm3 = auto()
    molpercm3 = auto()
    molperl = auto()
    molperm3 = auto()
    # kMolarEnergy
    uJpermol = auto()
    mJpermol = auto()
    Jpermol = auto()
    kJpermol = auto()
    megJpermol = auto()
    gJpermol = auto()
    # kMolarVelocity
    umolpers = auto()
    mmolpers = auto()
    cmolpers = auto()
    molpers = auto()
    kmolpers = auto()
    # kMolarViscosity
    Paspermol = auto()
    # kMomentInertia
    lbin2 = auto()
    lbft2 = auto()
    kgm2 = auto()
    # kMomentum
    gmpers = auto()
    kgmpers = auto()
    # kPercentage
    percent = auto()
    # kPercentagePerTime
    percentperm = auto()
    percentperhour = auto()
    percentperday = auto()
    pers = auto()
    permin = auto()
    perhour = auto()
    perday = auto()
    percentpers = auto()
    # kPermeance
    VsperA = auto()
    WbperA = auto()
    # kPower
    megw = auto()
    gw = auto()
    # kPressure
    mbar = auto()
    bar = auto()
    mmh2o = auto()
    mmhg = auto()
    techAtm = auto()
    torr = auto()
    stAtm = auto()
    # kPressureChangeRate
    psipermin = auto()
    statmpermin = auto()
    techatmpermin = auto()
    mmH2Opermin = auto()
    torrpermin = auto()
    Paperhour = auto()
    mbarperhour = auto()
    barperhour = auto()
    psiperhour = auto()
    statmperhour = auto()
    techatmperhour = auto()
    mbarpers = auto()
    barpers = auto()
    mmH2Operhour = auto()
    torrperhour = auto()
    psipers = auto()
    statmpers = auto()
    techatmpers = auto()
    mmH2Opers = auto()
    torrpers = auto()
    Papermin = auto()
    mbarpermin = auto()
    barpermin = auto()
    Papers = auto()
    # kPressureCoefficient
    perbar = auto()
    permbar = auto()
    perpsi = auto()
    perstatm = auto()
    pertechatm = auto()
    permmHg = auto()
    permmH2O = auto()
    VperVperPa = auto()
    perPa = auto()
    # kRatio
    bel = auto()
    # kReciprocalPower
    permegW = auto()
    permW = auto()
    perkW = auto()
    pergW = auto()
    perJs = auto()
    perW = auto()
    # kReciprocalResistanceCharge
    perOhmAs = auto()
    perOhmAh = auto()
    perOhmC = auto()
    # kReciprocalResistanceTime
    perOhmmin = auto()
    perOhmhour = auto()
    perOhms = auto()
    # kResistance
    uohm = auto()
    # kResistancePerCharge
    OhmperAs = auto()
    OhmperAhour = auto()
    nOhmperC = auto()
    uOhmperC = auto()
    mOhmperC = auto()
    OhmperC = auto()
    kOhmperC = auto()
    megOhmperC = auto()
    gOhmperC = auto()
    # kResistancePerLength
    Ohmperum = auto()
    uOhmperm = auto()
    mOhmperm = auto()
    Ohmperm = auto()
    kOhmperm = auto()
    megOhmperm = auto()
    # kResistanceTemperatureCoeff
    OhmperCel = auto()
    mOhmperKel = auto()
    OhmperKel = auto()
    kOhmperKel = auto()
    # kResistivity
    Ohmmm2permm = auto()
    Ohmum = auto()
    Ohmcm = auto()
    Ohmm = auto()
    # kSpecificHeatCapacity
    mJperKelkg = auto()
    JperKelkg = auto()
    kJperKelkg = auto()
    # kStiffness
    Npercm = auto()
    lbfperin = auto()
    Nperm = auto()
    kNperm = auto()
    # kSurfaceChargeDensity
    SufCDAsperm2 = auto()
    SufCDnCperm2 = auto()
    SufCDuCperm2 = auto()
    SufCDmCperm2 = auto()
    SufCDCperm2 = auto()
    # kSurfaceMobility
    cm2perVs = auto()
    m2perVs = auto()
    # kSurfaceMobilityPerVoltage
    cm2pV2s = auto()
    m2pV2s = auto()
    # kTemperature
    mkel = auto()
    ckel = auto()
    dkel = auto()
    # kTemperatureAreaPerPower
    kelm2pw = auto()
    celm2pw = auto()
    # kTemperatureCoefficient
    perCel = auto()
    perFah = auto()
    percentperKel = auto()
    percentperCel = auto()
    percentperFah = auto()
    perKel = auto()
    # kTemperatureCoefficient2
    perCel2 = auto()
    perFah2 = auto()
    perKel2 = auto()
    # kTemperatureDifference
    celdiff = auto()
    mkeldiff = auto()
    keldiff = auto()
    # kThermalCapacitance
    WsperKel = auto()
    JperKel = auto()
    # kThermalConductance
    mWperCel = auto()
    WperCel = auto()
    kWperCel = auto()
    mWperKel = auto()
    WperKel = auto()
    kWperKel = auto()
    # kThermalConductivity
    mWperKelm = auto()
    WperKelm = auto()
    # kThermalConvection
    wpcm2kel = auto()
    wpm2kel = auto()
    # kThermalRadiationCoeff
    mWperKel4 = auto()
    WperKel4 = auto()
    kWperKel4 = auto()
    # kThermalRadiationConstant
    Wpercm2Kel4 = auto()
    Wperm2Kel4 = auto()
    # kThermalResistance
    KelsperJ = auto()
    KelperW = auto()
    # kTime
    min = auto()
    hour = auto()
    day = auto()
    # kTimePerAngle
    sperdeg = auto()
    sperrev = auto()
    msperrad = auto()
    sperrad = auto()
    # kTimeSqPerAngleSq
    s2perdeg2 = auto()
    s2perrad2 = auto()
    # kTorque
    cnewtonmeter = auto()
    # kTransconductanceParameter
    mAperV = auto()
    AperV = auto()
    kAperV = auto()
    # kTransistorConstant
    mAperV2 = auto()
    AperV2 = auto()
    # kTranslationalAcceleration
    inpers2 = auto()
    cmpers2 = auto()
    dmpers2 = auto()
    mpers2 = auto()
    # kVelocitySaturation
    VelSatumperV = auto()
    VelSatmmperV = auto()
    VelSatcmperV = auto()
    VelSatmperV = auto()
    # kVelocitySaturationPerVoltage
    umperV2 = auto()
    mmperV2 = auto()
    cmperV2 = auto()
    mperV2 = auto()
    # kViscocity
    Nsperm2 = auto()
    cpoise = auto()
    poise = auto()
    uPas = auto()
    mPas = auto()
    cPas = auto()
    dPas = auto()
    Pas = auto()
    hPas = auto()
    kPas = auto()
    # kViscousFriction
    VisFricmNsperm = auto()
    VisFricCNsperm = auto()
    VisFricNsperm = auto()
    VisFrickNsperm = auto()
    # kVoltage
    gv = auto()
    # kVoltageAccelerationCoefficient
    mVperm2pers2 = auto()
    Vperm2pers2 = auto()
    # kVoltageChangeRate
    Vpermin = auto()
    Vperhour = auto()
    mVpers = auto()
    Vpers = auto()
    kVpers = auto()
    # kVoltageCoefficient
    permV = auto()
    perkV = auto()
    perV = auto()
    # kVoltageCoefficient2
    perV2 = auto()
    # kVoltageCubed
    mV3 = auto()
    V3 = auto()
    # kVoltageGain
    VpermV = auto()
    mVperV = auto()
    VperV = auto()
    # kVoltageJerkCoefficient
    mVpermpers3 = auto()
    Vpermpers3 = auto()
    # kVoltageLength
    uVm = auto()
    mVm = auto()
    Vm = auto()
    kVm = auto()
    # kVoltagePerCell
    pVpercell = auto()
    nVpercell = auto()
    uVpercell = auto()
    mVpercell = auto()
    Vpercell = auto()
    kVpercell = auto()
    megVpercell = auto()
    gVpercell = auto()
    # kVoltagePerLengthRoot
    Vpermhalf = auto()
    # kVoltagePressureRootCoeff
    mVperPahalf = auto()
    VperPahalf = auto()
    # kVoltageRoot
    Vhalf = auto()
    # kVoltageRootCoefficient
    perVhalf = auto()
    # kVoltageTemperature10Coeff
    uVperCel10 = auto()
    mVperCel10 = auto()
    VperCel10 = auto()
    uVperKel10 = auto()
    mVperKel10 = auto()
    VperKel10 = auto()
    # kVoltageTemperature11Coeff
    uVperCel11 = auto()
    mVperCel11 = auto()
    VperCel11 = auto()
    uVperKel11 = auto()
    mVperKel11 = auto()
    VperKel11 = auto()
    # kVoltageTemperature12Coeff
    uVperCel12 = auto()
    mVperCel12 = auto()
    VperCel12 = auto()
    uVperKel12 = auto()
    mVperKel12 = auto()
    VperKel12 = auto()
    # kVoltageTemperature13Coeff
    uVperCel13 = auto()
    mVperCel13 = auto()
    VperCel13 = auto()
    uVperKel13 = auto()
    mVperKel13 = auto()
    VperKel13 = auto()
    # kVoltageTemperature14Coeff
    uVperCel14 = auto()
    mVperCel14 = auto()
    VperCel14 = auto()
    uVperKel14 = auto()
    mVperKel14 = auto()
    VperKel14 = auto()
    # kVoltageTemperature15Coeff
    uVperCel15 = auto()
    mVperCel15 = auto()
    VperCel15 = auto()
    uVperKel15 = auto()
    mVperKel15 = auto()
    VperKel15 = auto()
    # kVoltageTemperature2Coeff
    uVperCel2 = auto()
    mVperCel2 = auto()
    VperCel2 = auto()
    uVperKel2 = auto()
    mVperKel2 = auto()
    VperKel2 = auto()
    # kVoltageTemperature3Coeff
    uVperCel3 = auto()
    mVperCel3 = auto()
    VperCel3 = auto()
    uVperKel3 = auto()
    mVperKel3 = auto()
    VperKel3 = auto()
    # kVoltageTemperature4Coeff
    uVperCel4 = auto()
    mVperCel4 = auto()
    VperCel4 = auto()
    uVperKel4 = auto()
    mVperKel4 = auto()
    VperKel4 = auto()
    # kVoltageTemperature5Coeff
    uVperCel5 = auto()
    mVperCel5 = auto()
    VperCel5 = auto()
    uVperKel5 = auto()
    mVperKel5 = auto()
    VperKel5 = auto()
    # kVoltageTemperature6Coeff
    uVperCel6 = auto()
    mVperCel6 = auto()
    VperCel6 = auto()
    uVperKel6 = auto()
    mVperKel6 = auto()
    VperKel6 = auto()
    # kVoltageTemperature7Coeff
    uVperCel7 = auto()
    mVperCel7 = auto()
    VperCel7 = auto()
    uVperKel7 = auto()
    mVperKel7 = auto()
    VperKel7 = auto()
    # kVoltageTemperature8Coeff
    uVperCel8 = auto()
    mVperCel8 = auto()
    VperCel8 = auto()
    uVperKel8 = auto()
    mVperKel8 = auto()
    VperKel8 = auto()
    # kVoltageTemperature9Coeff
    uVperCel9 = auto()
    mVperCel9 = auto()
    VperCel9 = auto()
    uVperKel9 = auto()
    mVperKel9 = auto()
    VperKel9 = auto()
    # kVoltageTemperatureCoeff
    uVperCel = auto()
    mVperCel = auto()
    VperCel = auto()
    uVperKel = auto()
    mVperKel = auto()
    VperKel = auto()
    # kVolume
    mm3 = auto()
    m3 = auto()
    galUK = auto()
    cup = auto()
    galUS = auto()
    # kVolumeCoefficient
    percm3 = auto()
    perm3 = auto()
    # kVolumeFlowConductance
    VolFConcm3perPas = auto()
    VolFConm3perPas = auto()
    # kVolumeFlowPerPressureRoot
    m3persPahalf = auto()
    # kVolumeFlowRate
    m3permin = auto()
    m3perhour = auto()
    cm3pers = auto()
    m3pers = auto()
    ltrpermin = auto()
    # kVolumeFlowRateChangeRate
    cm3pers2 = auto()
    m3pers2 = auto()
    # kMass
    mton = auto()
    # kWireCrossSection
    Wirein2 = auto()
    Wireft2 = auto()
    Wireum2 = auto()
    Wiremm2 = auto()
    Wirecm2 = auto()
    Wirem2 = auto()
    # kEnergyDensity
    JPerM3 = auto()
    kJPerM3 = auto()
    # Additional Volume Units
    cm3 = auto()
    inch3 = auto()
    foot3 = auto()
    yard3 = auto()
    # Magnetomotive Force
    at = auto()
    uat = auto()
    nat = auto()
    mat = auto()
    kat = auto()
    # additional kPercentage
    Fraction = auto()
    # delta temperature
    fah_diff = auto()
    # Delta Fahrenheit
    ckel_diff = auto()
    dkel_diff = auto()
    # Delta Kelvin
    # Additional units for Areal Flow Rate (e.g. Diffusivity)
    ft2pers = auto()
    cm2pers = auto()
    # kMolarMass
    kgpermol = auto()
    gpermol = auto()
    # Additional units for kViscocity
    kgperms = auto()
    lbmperfts = auto()
    slugperfts = auto()
    # Additions for kTemperatureAreaPerPower (e.g. Thermal Impedance)
    celin2pw = auto()
    # C-in2/W
    celmm2pw = auto()
    # C-mm2/W
    # Additions for kIrradiance (e.g. Heat Flux Density)
    btupspft2 = auto()
    # BTU/s-ft2
    btuphrpft2 = auto()
    # BTU/h-ft2
    ergpspcm2 = auto()
    # erg/s-cm2
    # Additional units for area
    micron2 = auto()
    mil2 = auto()
    # Additional units for thermal conductance
    btuPerFahSec = auto()
    btuPerRankSec = auto()
    btuPerFahHr = auto()
    btuPerRankHr = auto()
    # Additional units for thermal conductivity
    btuPerFahFtSec = auto()
    btuPerRankFtSec = auto()
    btuPerFahFtHr = auto()
    btuPerRankFtHr = auto()
    calpersmCel = auto()
    calpersmKel = auto()
    ergperscmKel = auto()
    wPerCelM = auto()
    # Additional units for density
    lbmPerFt3 = auto()
    slugPerFt3 = auto()
    # Additional units for thermal convection
    btuPerFahSecFt2 = auto()
    btuPerFahHrFt2 = auto()
    btuPerRankSecFt2 = auto()
    btuPerRankHrFt2 = auto()
    wPerCelM2 = auto()
    # Additional unit(s) for length
    copperOzPerFt2 = auto()
    # Additional units for mass flow rate
    lbmPerSec = auto()
    lbmPerMin = auto()
    # Additional units for power
    btuPerSec = auto()
    ergPerSec = auto()
    # Additional units for power-per-area (surface heat)
    IrradWPerMm2 = auto()
    IrradMet = auto()
    # Power per volume
    btuPerSecFt3 = auto()
    btuPerHrFt3 = auto()
    ergPerSecCm3 = auto()
    wPerM3 = auto()
    # Additional unit(s) for pressure
    lbfPerFt2 = auto()
    # Additional units for thermal resistance
    celPerW = auto()
    fahSecPerBtu = auto()
    # Additional units for specific heat capacity
    btuPerLbmFah = auto()
    btuPerLbmRank = auto()
    calPerGKel = auto()
    calPerGCel = auto()
    ergPerGKel = auto()
    JPerCelKg = auto()
    kcalPerKgKel = auto()
    kcalPerKgCel = auto()
    # Additional units for temperature and delta-temperature (Rankine)
    rank = auto()
    rankdiff = auto()
    # Turbulent dissipation rate
    m2PerSec3 = auto()
    ft2PerSec3 = auto()
    # Turbulent kinetic energy
    m2PerSec2 = auto()
    ft2PerSec2 = auto()
    # Specific turbulence dissipation rate
    dissPerSec = auto()
    # Additional unit for temperature coefficient (volumetric expansion coefficient)
    perRank = auto()
    percentperRank = auto()
    # Additional units for volumetric flow rate
    ft3PerMin = auto()
    ft3PerSec = auto()
    cfm = auto()
    # Additional unit for pressure
    pressWaterInches = auto()
    # Additional unit for kCharge
    q = auto()
    # change of a proton (negative for electron)
    # data rate units of bits/sec (added for EMIT)
    bps = auto()
    kbps = auto()
    mbps = auto()
    gbps = auto()
    # kMassFlux
    kgpersm2 = auto()
    lbmperminft2 = auto()
    gperscm2 = auto()
    # kThermalConductancePerArea
    Wperm2perCel = auto()
    Wperin2perCel = auto()
    Wpermm2perCel = auto()
    # kAttenutation
    dBperm = auto()
    dBpercm = auto()
    dBperdm = auto()
    dBperkm = auto()
    dBperft = auto()
    dBpermi = auto()
    Nppercm = auto()
    Npperdm = auto()
    Npperft = auto()
    Npperkm = auto()
    Npperm = auto()
    Nppermi = auto()


@unique
class AllowedMarkers(IntEnum):
    Octahedron = 12
    Tetrahedron = 11
    Sphere = 9
    Box = 10
    Arrow = 0
