from __future__ import absolute_import

import warnings

from pyaedt import emit_core, generate_unique_project_name
from pyaedt.application.Design import Design
from pyaedt.emit_core.Couplings import CouplingsEmit
from pyaedt.emit_core.emit_constants import EMIT_VALID_UNITS, emit_unit_type_string_to_enum
from pyaedt.emit_core.results.results import Results
from pyaedt.generic.general_methods import pyaedt_function_handler
from pyaedt.modeler.schematic import ModelerEmit


class Emit(Design, object):
    """Provides the EMIT application interface.

    Parameters
    ----------
    projectname : str, optional
        Name of the project to select or the full path to the project
        or AEDTZ archive to open.  The default is ``None``, in which case
        an attempt is made to get an active project. If no projects are
        present, an empty project is created.
    designname : str, optional
        Name of the design to select. The default is ``None``, in which case
        an attempt is made to get an active design. If no designs are
        present, an empty design is created.
    solution_type : str, optional
        Solution type to apply to the design. The default is ``None``, in which
        case the default type is applied.
    setup_name : str, optional
        Name of the setup to use as the nominal. The default is
        ``None``, in which case the active setup is used or
        nothing is used.
    specified_version : str, int, float, optional
        Version of AEDT to use. The default is ``None``, in which case
        the active setup is used or the latest installed version is
        used.
        Examples of input values are ``232``, ``23.2``,``2023.2``,``"2023.2"``.
    non_graphical : bool, optional
        Whether to launch AEDT in non-graphical mode. The default
        is ``False``, in which case AEDT is launched in graphical mode.
        This parameter is ignored when a script is launched within AEDT.
    new_desktop_session : bool, optional
        Whether to launch an instance of AEDT in a new thread, even if
        another instance of the ``specified_version`` is active on the
        machine.  The default is ``True``.
    close_on_exit : bool, optional
        Whether to release AEDT on exit. The default is ``False``.
    student_version : bool, optional
        Whether to start the AEDT student version. The default is ``False``.
    port : int, optional
        Port number on which to start the oDesktop communication on an already existing server.
        This parameter is ignored when creating a server. This parameter works only in 2022 R2 or later.
        The remote server must be up and running with the command `"ansysedt.exe -grpcsrv portnum"`.
        The default is ``0``.
    machine : str, optional
        Machine name that the Desktop session is to connect to. This
        parameter works only in 2022 R2 and later. The remote server must be
        up and running with the command `"ansysedt.exe -grpcsrv portnum"`.
        If the machine is `"localhost"`, the server starts if it is not present.
    aedt_process_id : int, optional
        Process ID for the instance of AEDT to point PyAEDT at. The default is
        ``None``. This parameter is only used when ``new_desktop_session = False``.

    Examples
    --------
    Create an ``Emit`` instance. You can also choose to define parameters for this instance here.

    >>> from pyaedt import Emit
    >>> aedtapp = Emit()

    Typically, it is desirable to specify a project name, design name, and other parameters.

    >>> aedtapp = Emit(projectname, designame, specified_version=232)

    Once an ``Emit`` instance is initialized, you can edit the schematic:

    >>> rad1 = aedtapp.modeler.components.create_component("Bluetooth")
    >>> ant1 = aedtapp.modeler.components.create_component("Antenna")
    >>> if rad1 and ant1:
    >>>     ant1.move_and_connect_to(rad1)

    Once the schematic is generated, the ``Emit`` object can be analyzed to generate
    a revision. Each revision is added as an element of the ``Emit`` object member's
    revisions_list.

    >>> aedtapp.analyze()

    A revision within PyAEDT is analogous to a revision in AEDT. An interaction domain must
    be defined and then used as the input to the run command used on that revision.

    >>> domain = aedtapp.interaction_domain()
    >>> domain.rx_radio_name = "UE - HandHeld"
    >>> interaction = aedtapp.revisions_list[0].run(domain)

    The output of the run command is an ``interaction`` object. This object summarizes the interaction data
    that is defined in the interaction domain.

    >>> instance = interaction.worst_instance(ResultType.SENSITIVITY)
    >>> val = instance.value(ResultType.SENSITIVITY)
    >>> print("Worst-case sensitivity for Rx '{}' is {}dB.".format(domain.rx_radio_name, val))
    """

    def __init__(
        self,
        projectname=None,
        designname=None,
        solution_type=None,
        setup_name=None,
        specified_version=None,
        non_graphical=False,
        new_desktop_session=True,
        close_on_exit=True,
        student_version=False,
        machine="",
        port=0,
        aedt_process_id=None,
    ):
        if projectname is None:
            projectname = generate_unique_project_name()
        self.__emit_api_enabled = False
        self.results = None
        """Constructor for the ``FieldAnalysisEmit`` class"""

        self._units = {}
        """Default EMIT units."""

        Design.__init__(
            self,
            "EMIT",
            projectname,
            designname,
            solution_type,
            specified_version,
            non_graphical,
            new_desktop_session,
            close_on_exit,
            student_version,
            machine=machine,
            port=port,
            aedt_process_id=aedt_process_id,
        )
        self._modeler = ModelerEmit(self)
        self._couplings = CouplingsEmit(self)
        if self._aedt_version > "2023.1":
            # the next 2 lines of code are needed to point
            # the EMIT object to the correct EmiApiPython
            # module for the current AEDT version
            emit_core._set_api(self.aedt_version_id)
            self._emit_api = emit_core.emit_api_python().EmitApi()
            """Instance of the EMIT API."""

            self.results = Results(self)
            """''Result'' object for the selected design."""

            self.__emit_api_enabled = True

            # set the default units here to make sure the EmitApi level
            # stays synced with pyaedt
            unit_types = ["Power", "Frequency", "Length", "Time", "Voltage", "Data Rate", "Resistance"]
            unit_values = ["dBm", "MHz", "meter", "ns", "mV", "bps", "Ohm"]
            self.set_units(unit_types, unit_values)

    def _init_from_design(self, *args, **kwargs):
        self.__init__(*args, **kwargs)

    @property
    def modeler(self):
        """Modeler.

        Returns
        -------
        pyaedt.modeler.schematic.ModelerEmit
            Design oModeler
        """
        return self._modeler

    @property
    def couplings(self):
        """EMIT Couplings.

        Returns
        -------
        pyaedt.emit_core.Couplings.CouplingsEmit
            Couplings within the EMIT Design
        """
        return self._couplings

    @pyaedt_function_handler()
    def __enter__(self):
        return self

    @pyaedt_function_handler()
    def version(self, detailed=False):
        """Get version information.

        Parameters
        ----------
        detailed : bool, optional
            Whether to return a verbose description. The default is ``False``.

        Returns
        -------
        ver : str
            All of the version information.

        Examples
        --------
        >>> print(aedtapp.version())

        """
        if self.__emit_api_enabled:
            ver = self._emit_api.get_version(detailed)
            return ver

    @pyaedt_function_handler()
    def set_units(self, unit_type, unit_value):
        """Set units for the component.

        Parameters
        ----------
        unit_type : str
            System of units.
        unit_value : str
            Units to use.

        Power : mW, W, kW, dBm, dBW
        Frequency : Hz, kHz, MHz, GHz, THz
        Length : pm, nm, um, mm, cm, dm, meter, km, mil, in, ft, yd, mile
        Time : ps, ns, us, ms, s
        Voltage : mV, V
        Data Rate : bps, kbps, Mbps, Gbps
        Resistance : uOhm, mOhm, Ohm, kOhm, megOhm, GOhm

        Returns
        -------
        Bool
            ``True`` if the units were successfully changed and ``False``
            if there was an error.
        """
        if isinstance(unit_type, list):
            for t, v in zip(unit_type, unit_value):
                if t not in EMIT_VALID_UNITS:
                    warnings.warn(
                        "[{}] units are not supported by EMIT. The options are: {}: ".format(t, EMIT_VALID_UNITS.keys())
                    )
                    return False
                if v not in EMIT_VALID_UNITS[t]:
                    warnings.warn(
                        "[{}] are not supported by EMIT. The options are: {}: ".format(v, EMIT_VALID_UNITS[t])
                    )
                    return False
                ut = emit_unit_type_string_to_enum(t)
                self._emit_api.set_units(ut, v)
                self._units[t] = v
        else:
            if unit_type not in EMIT_VALID_UNITS:
                warnings.warn(
                    "[{}] units are not supported by EMIT. The options are: {}: ".format(
                        unit_type, EMIT_VALID_UNITS.keys()
                    )
                )
                return False
            if unit_value not in EMIT_VALID_UNITS[unit_type]:
                warnings.warn(
                    "[{}] are not supported by EMIT. The options are: {}: ".format(
                        unit_value, EMIT_VALID_UNITS[unit_type]
                    )
                )
                return False
            # keep the backend global units synced
            ut = emit_unit_type_string_to_enum(unit_type)
            self._emit_api.set_units(ut, unit_value)
            self._units[unit_type] = unit_value
        return True

    @pyaedt_function_handler()
    def get_units(self, unit_type=""):
        """Get units for the component.

        Parameters
        ----------
        unit_type : str, optional
            System of units: options are power, frequency,
            length, time, voltage, data rate, or resistance.
            The default is ``None`` which uses the units
            specified globally for the project.

        Returns
        -------
        Str or Dict
            If unit_type is specified returns the units for that type
            and if unit_type="", returns a Dict of all units.
        """
        if not unit_type:
            return self._units
        if unit_type not in EMIT_VALID_UNITS:
            warnings.warn(
                "[{}] units are not supported by EMIT. The options are: {}: ".format(unit_type, EMIT_VALID_UNITS.keys())
            )
            return None
        return self._units[unit_type]
