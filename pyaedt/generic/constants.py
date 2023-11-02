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
        if units in unit_dict:
            return unit_type

    return False


def _resolve_unit_system(unit_system_1, unit_system_2, operation):
    """Retrieve the unit string of an arithmetic operation on ``Variable`` objects. If no resulting unit system
    is defined for a specific operation (in unit_system_operations), an empty string is returned

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
        key = "{}_{}_{}".format(unit_system_1, operation, unit_system_2)
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
            warnings.warn("Unknown units: '{}'".format(input_units))
            return values
        elif output_units not in AEDT_UNITS[unit_system]:
            warnings.warn("Unknown units: '{}'".format(output_units))
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
            ElectroDCConduction,
            ElectroDCTransient,
            TransientAPhiFormulation,
        ) = (
            "Transient",
            "Magnetostatic",
            "EddyCurrent",
            "Electrostatic",
            "ElectroDCConduction",
            "ElectricTransient",
            "TransientAPhiFormulation",
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
            ElectroDCConductionX,
            ElectroDCConductionZ,
            ElectroDCTransientXY,
            ElectroDCTransientZ,
        ) = (
            "TransientXY",
            "TransientZ",
            "MagnetostaticXY",
            "MagnetostaticZ",
            "EddyCurrentXY",
            "EddyCurrentZ",
            "ElectrostaticXY",
            "ElectrostaticZ",
            "ElectroDCConductionXY",
            "ElectroDCConductionZ",
            "ElectricTransientXY",
            "ElectricTransientZ",
        )

    class Icepak(object):
        """Provides Icepak solution types."""

        (
            SteadyTemperatureAndFlow,
            SteadyTemperatureOnly,
            SteadyFlowOnly,
            TransientTemperatureAndFlow,
            TransientTemperatureOnly,
            TransientFlowOnly,
        ) = (
            "SteadyStateTemperatureAndFlow",
            "SteadyStateTemperatureOnly",
            "SteadyStateFlowOnly",
            "TransientTemperatureAndFlow",
            "TransientTemperatureOnly",
            "TransientFlowOnly",
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

        (Thermal, Structural, Modal) = ("Thermal", "Structural", "Modal")


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
        SteadyTemperatureAndFlow,
        SteadyTemperatureOnly,
        SteadyFlowOnly,
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
        TransientTemperatureAndFlow,
        TransientTemperatureOnly,
        TransientFlowOnly,
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
