import math

from pyaedt import constants
from pyaedt.generic.constants import AEDT_UNITS, SpeedOfLight
from pyaedt.generic.general_methods import pyaedt_function_handler


class TransmissionLine(object):
    """Provides base methods common to transmission line calculation.

    Parameters
    ----------
    frequency : float, optional
        Center frequency. The default is ``10.0``.
    frequency_unit : str, optional
        Frequency units. The default is ``"GHz"``.

    Returns
    -------
    :class:`aedt.toolkits.antennas.common.TransmissionLine`
        Transmission line calculator object.

    Examples
    --------
    >>> from pyaedt.modeler.calculators import TransmissionLine
    >>> tl_calc = TransmissionLine(frequency=2)
    >>> tl_calc.stripline_calculator(substrate_height=10, permittivity=2.2, impedance=60)
    """

    def __init__(self, frequency=10, frequency_unit="GHz"):
        self.frequency = frequency
        self.frequency_unit = frequency_unit

    @pyaedt_function_handler()
    def microstrip_synthesis(self, substrate_height, permittivity, impedance=50.0, electrical_length=150.0):
        """Strip line calculator.

        Parameters
        ----------
        substrate_height : float
            Substrate height.
        permittivity : float
            Substrate permittivity.
        impedance : str, optional
            Impedance. The default is ``50.0``.
        electrical_length : str, optional
            Electrical length in degrees. The default is ``150.0``.

        Returns
        -------
        tuple
            Line width and length.
        """
        z0 = impedance
        e0 = permittivity
        h0 = substrate_height

        A_us = z0 / 60.0 * math.sqrt((e0 + 1.0) / 2.0) + (e0 - 1.0) / (e0 + 1.0) * (0.23 + 0.11 / e0)
        B_us = 377.0 * math.pi / (2.0 * z0 * math.sqrt(e0))

        w_over_subH_1 = 8.0 * math.exp(A_us) / (math.exp(2.0 * A_us) - 2.0)
        w_over_subH_2 = (
            2.0
            / math.pi
            * (
                B_us
                - 1.0
                - math.log(2.0 * B_us - 1.0)
                + (e0 - 1.0) / (2.0 * e0) * (math.log(B_us - 1.0) + 0.39 - 0.61 / e0)
            )
        )

        ustrip_width = w_over_subH_1 * h0
        if w_over_subH_1 < 2.0:
            ustrip_width = w_over_subH_1 * h0

        if w_over_subH_2 >= 2:
            ustrip_width = w_over_subH_2 * h0

        er_eff = (e0 + 1.0) / 2.0 + (e0 - 1.0) / 2.0 * 1.0 / (math.sqrt(1.0 + 12.0 * h0 / ustrip_width))
        f = constants.unit_converter(self.frequency, "Freq", self.frequency_unit, "Hz")

        k0 = 2.0 * math.pi * f / 3.0e8

        ustrip_length = math.radians(electrical_length) / (math.sqrt(er_eff) * k0)

        return ustrip_width, ustrip_length

    @pyaedt_function_handler()
    def microstrip_analysis(self, substrate_height, permittivity, width, thickness):
        """Strip line calculator.

        Parameters
        ----------
        substrate_height : float
            Substrate height.
        permittivity : float
            Substrate permittivity.
        width : float
            Trace width.
        thickness : float
            Trace thickness.

        Returns
        -------
        float
            z0
        """
        e0 = permittivity
        h0 = substrate_height
        z1 = 87 / (math.sqrt(e0 + 1.41))
        z2 = math.log(5.98 * h0 / ((0.8 * width) + thickness))
        z0 = z1 * z2
        return z0

    @pyaedt_function_handler()
    def differential_microstrip_analysis(self, substrate_height, permittivity, width, separation, thickness):
        """Strip line calculator.

        Parameters
        ----------
        substrate_height : float
            Substrate height.
        permittivity : float
            Substrate permittivity.
        width : float
            Trace width.
        separation : float
            Trace separation.
        thickness : float
            Trace thickness.


        Returns
        -------
        tuple
            z0 single end and differential.
        """
        e0 = permittivity
        h0 = substrate_height
        z1 = 87 / (math.sqrt(e0 + 1.41))
        z2 = math.log(5.98 * substrate_height / ((0.8 * width) + thickness))
        z0 = z1 * z2
        z0d = 2 * z0 * (1 - (0.48 * math.exp(-0.96 * separation / h0)))
        return z0, z0d

    @pyaedt_function_handler()
    def stripline_synthesis(self, substrate_height, permittivity, impedance=50.0):
        """Strip line calculator.

        Parameters
        ----------
        substrate_height : float
            Substrate height.
        permittivity : float
            Substrate permittivity.
        impedance : str, optional
            Impedance. The default is ``50.0``.

        Returns
        -------
        float
            Line width.
        """
        x = 30.0 * math.pi / (math.sqrt(permittivity) * impedance) - 0.441

        if math.sqrt(permittivity) * impedance <= 120:
            w_over_h = x
        else:
            w_over_h = 0.85 - math.sqrt(0.6 - x)

        width = w_over_h * substrate_height
        return width

    @pyaedt_function_handler()
    def suspended_strip_synthesis(self, substrate_height, permittivity, w1, units="mm"):
        """Suspended stripline calculator.

        Parameters
        ----------
        substrate_height : float
            Substrate in meter.
        permittivity : float
            Dielectric permittivity
        w1 : float

        Returns
        -------
        float
            Effective permittivity.
        """
        wavelength = (SpeedOfLight / AEDT_UNITS["Length"][units]) / (
            self.frequency * AEDT_UNITS["Freq"][self.frequency_unit]
        )
        Hfrac = 16.0  # H_as_fraction_of_wavelength 1/H
        H = (wavelength / math.sqrt(permittivity) + substrate_height * Hfrac) / Hfrac
        heigth_ratio = substrate_height / (H - substrate_height)
        a = math.pow(0.8621 - 0.125 * math.log(heigth_ratio), 4.0)
        b = math.pow(0.4986 - 0.1397 * math.log(heigth_ratio), 4.0)

        Width_to_height_ratio = w1 / (H - substrate_height)
        sqrt_er_eff = math.pow(
            1.0 + heigth_ratio * (a - b * math.log(Width_to_height_ratio)) * (1.0 / math.sqrt(permittivity) - 1.0),
            -1.0,
        )
        effective_permittivity = math.pow(sqrt_er_eff, 2.0)

        if (permittivity >= 6.0) and (permittivity <= 10.0):
            effective_permittivity = effective_permittivity * 1.15  # about 15% larger than calculated
        if permittivity > 10:
            effective_permittivity = effective_permittivity * 1.25  # about 25% lager then calculated

        if effective_permittivity >= (permittivity + 1.0) / 2.0:
            effective_permittivity = (permittivity + 1.0) / 2.0

        return effective_permittivity


class StandardWaveguide(object):
    """Provides base methods common to standard waveguides.

    Parameters
    ----------
    frequency : float, optional
        Center frequency. The default is ``10.0``.
    frequency_unit : str, optional
        Frequency units. The default is ``"GHz"``.

    Returns
    -------
    :class:`aedt.toolkits.antennas.common.StandardWaveguide`
        Standard waveguide object.

    Examples
    --------
    >>> from pyaedt.modeler.calculators import StandardWaveguide
    >>> wg_calc = StandardWaveguide()
    >>> wg_dim = wg_calc.get_waveguide_dimensions("WR-75")
    """

    wg = {}
    wg["WR-2300"] = [23.0, 11.5, 0.15]
    wg["WR-2100"] = [21.0, 10.5, 0.125]
    wg["WR-1800"] = [18.0, 9.0, 0.125]
    wg["WR-1500"] = [15.0, 7.5, 0.125]
    wg["WR-1150"] = [11.5, 5.75, 0.125]
    wg["WR-975"] = [9.75, 4.875, 0.125]
    wg["WR-770"] = [7.7, 3.850, 0.125]
    wg["WR-650"] = [6.5, 3.25, 0.08]
    wg["WR-510"] = [5.1, 2.55, 0.08]
    wg["WR-430"] = [4.3, 2.15, 0.08]
    wg["WR-340"] = [3.4, 1.7, 0.08]
    wg["WR-284"] = [2.84, 1.34, 0.08]
    wg["WR-229"] = [2.29, 1.145, 0.064]
    wg["WR-187"] = [1.872, 0.872, 0.064]
    wg["WR-159"] = [1.53, 0.795, 0.064]
    wg["WR-137"] = [1.372, 0.622, 0.064]
    wg["WR-112"] = [1.122, 0.497, 0.064]
    wg["WR-102"] = [1.02, 0.51, 0.064]
    wg["WR-90"] = [0.9, 0.4, 0.05]
    wg["WR-75"] = [0.75, 0.375, 0.05]
    wg["WR-62"] = [0.622, 0.311, 0.04]
    wg["WR-51"] = [0.51, 0.255, 0.04]
    wg["WR-42"] = [0.42, 0.17, 0.04]
    wg["WR-34"] = [0.34, 0.17, 0.04]
    wg["WR-28"] = [0.28, 0.14, 0.04]
    wg["WR-22"] = [0.224, 0.112, 0.04]
    wg["WR-19"] = [0.188, 0.094, 0.04]
    wg["WR-15"] = [0.148, 0.074, 0.04]
    wg["WR-12"] = [0.122, 0.061, 0.04]
    wg["WR-10"] = [0.1, 0.05, 0.04]
    wg["WR-8"] = [0.08, 0.04, 0.02]
    wg["WR-7"] = [0.065, 0.0325, 0.02]
    wg["WR-5"] = [0.0510, 0.0255, 0.02]

    def __init__(self, frequency=10, frequency_unit="GHz"):
        self.frequency = frequency
        self.frequency_unit = frequency_unit

    @property
    def waveguide_list(self):
        """Waveguide lists."""
        return self.wg.keys()

    @pyaedt_function_handler()
    def get_waveguide_dimensions(self, name, units="mm"):
        """Strip line calculator.

        Parameters
        ----------
        name : str
            Waveguide name.
        units : str
           Dimension units. The default is ``mm``.

        Returns
        -------
        list
            Waveguide dimensions.
        """
        if name in self.wg:
            wg_dim = []
            for dbl in self.wg[name]:
                wg_dim.append(constants.unit_converter(dbl, "Length", "in", units))
            return wg_dim
        else:
            return False

    @pyaedt_function_handler()
    def find_waveguide(self, freq, units="GHz"):  # pragma: no cover
        """Find the closest standard waveguide for the operational frequency.

        Parameters
        ----------
        freq : float
            Operational frequency.
        units : str, optional
           Input frequency units. The default is ``"GHz"``.

        Returns
        -------
        str
            Waveguide name.
        """
        freq = constants.unit_converter(freq, "Frequency", units, "GHz")
        op_freq = freq * 0.8

        if op_freq >= 140:
            wg_name = "WR-5"
        elif op_freq >= 110:
            wg_name = "WR-7"
        elif op_freq >= 90:
            wg_name = "WR-8"
        elif op_freq >= 75:
            wg_name = "WR-10"
        elif op_freq >= 60:
            wg_name = "WR-12"
        elif op_freq >= 50:
            wg_name = "WR-15"
        elif op_freq >= 40:
            wg_name = "WR-19"
        elif op_freq >= 33:
            wg_name = "WR-22"
        elif op_freq >= 26.50:
            wg_name = "WR-28"
        elif op_freq >= 22:
            wg_name = "WR-34"
        elif op_freq >= 18:
            wg_name = "WR-42"
        elif op_freq >= 15:
            wg_name = "WR-51"
        elif op_freq >= 12.4:
            wg_name = "WR-62"
        elif op_freq >= 10:
            wg_name = "WR-75"
        elif op_freq >= 8.2:
            wg_name = "WR-90"
        elif op_freq >= 6.95:
            wg_name = "WR-102"
        elif op_freq >= 7.05:
            wg_name = "WR-112"
        elif op_freq >= 5.85:
            wg_name = "WR-137"
        elif op_freq >= 4.9:
            wg_name = "WR-159"
        elif op_freq >= 3.95:
            wg_name = "WR-187"
        elif op_freq >= 3.3:
            wg_name = "WR-229"
        elif op_freq >= 2.6:
            wg_name = "WR-284"
        elif op_freq >= 2.2:
            wg_name = "WR-340"
        elif op_freq >= 1.70:
            wg_name = "WR-430"
        elif op_freq >= 1.45:
            wg_name = "WR-510"
        elif op_freq >= 1.12:
            wg_name = "WR-650"
        elif op_freq >= 0.96:
            wg_name = "WR-770"
        elif op_freq >= 0.75:
            wg_name = "WR-975"
        elif op_freq >= 0.64:
            wg_name = "WR-1150"
        elif op_freq >= 0.49:
            wg_name = "WR-1500"
        elif op_freq >= 0.41:
            wg_name = "WR-1800"
        elif op_freq >= 0.35:
            wg_name = "WR-2100"
        elif op_freq > 0:
            wg_name = "WR-2300"
        else:
            wg_name = None
        return wg_name
