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

import warnings

from ansys.aedt.core import emit_core
from ansys.aedt.core.application.design import Design
from ansys.aedt.core.emit_core.couplings import CouplingsEmit
from ansys.aedt.core.emit_core.emit_constants import EMIT_VALID_UNITS
from ansys.aedt.core.emit_core.emit_constants import emit_unit_type_string_to_enum
from ansys.aedt.core.emit_core.results.results import Results
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.modeler.schematic import ModelerEmit


class Emit(Design, object):
    """Provides the EMIT application interface.

    Parameters
    ----------
    project : str, optional
        Name of the project to select or the full path to the project
        or AEDTZ archive to open.  The default is ``None``, in which case
        an attempt is made to get an active project. If no projects are
        present, an empty project is created.
    design : str, optional
        Name of the design to select. The default is ``None``, in which case
        an attempt is made to get an active design. If no designs are
        present, an empty design is created.
    solution_type : str, optional
        Solution type to apply to the design. The default is ``None``, in which
        case the default type is applied.
    version : str, int, float, optional
        Version of AEDT to use. The default is ``None``, in which case
        the active setup is used or the latest installed version is
        used.
        Examples of input values are ``251``, ``25.1``, ``2025.1``, ``"2025.1"``.
    non_graphical : bool, optional
        Whether to launch AEDT in non-graphical mode. The default
        is ``False``, in which case AEDT is launched in graphical mode.
        This parameter is ignored when a script is launched within AEDT.
    new_desktop : bool, optional
        Whether to launch an instance of AEDT in a new thread, even if
        another instance of the ``specified_version`` is active on the
        machine.  The default is ``False``.
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
        ``None``. This parameter is only used when ``new_desktop = False``.
    remove_lock : bool, optional
        Whether to remove lock to project before opening it or not.
        The default is ``False``, which means to not unlock
        the existing project if needed and raise an exception.

    Examples
    --------
    Create an ``Emit`` instance. You can also choose to define parameters for this instance here.

    >>> from ansys.aedt.core import Emit
    >>> aedtapp = Emit()

    Typically, it is desirable to specify a project name, design name, and other parameters.

    >>> aedtapp = Emit(projectname, designame, version=251)

    Once an ``Emit`` instance is initialized, you can edit the schematic:

    >>> rad1 = aedtapp.modeler.components.create_component("Bluetooth")
    >>> ant1 = aedtapp.modeler.components.create_component("Antenna")
    >>> if rad1 and ant1:
    >>>     ant1.move_and_connect_to(rad1)

    Once the schematic is generated, the ``Emit`` object can be analyzed to generate
    a revision. Each revision is added as an element of the ``Emit`` object member's
    ``Results.revisions`` list.

    >>> revision = aedtapp.results.analyze()

    A revision within PyAEDT is analogous to a revision in AEDT. An interaction domain must
    be defined and then used as the input to the run command used on that revision.

    >>> domain = aedtapp.results.interaction_domain()
    >>> domain.rx_radio_name = "UE - HandHeld"
    >>> interaction = revision.run(domain)

    The output of the run command is an ``interaction`` object. This object summarizes the interaction data
    that is defined in the interaction domain.

    >>> instance = interaction.worst_instance(ResultType.SENSITIVITY)
    >>> val = instance.value(ResultType.SENSITIVITY)
    >>> print(f"Worst-case sensitivity for Rx '{domain.rx_radio_name}' is {val}dB.")
    """

    @pyaedt_function_handler(
        designname="design",
        projectname="project",
        specified_version="version",
        setup_name="setup",
        new_desktop_session="new_desktop",
    )
    def __init__(
        self,
        project=None,
        design=None,
        solution_type=None,
        version=None,
        non_graphical=False,
        new_desktop=True,
        close_on_exit=True,
        student_version=False,
        machine="",
        port=0,
        aedt_process_id=None,
        remove_lock=False,
    ):
        self.__emit_api_enabled = False
        self.results = None
        """Constructor for the ``FieldAnalysisEmit`` class"""

        self._units = {}
        """Default EMIT units."""

        Design.__init__(
            self,
            "EMIT",
            project,
            design,
            solution_type,
            version,
            non_graphical,
            new_desktop,
            close_on_exit,
            student_version,
            machine=machine,
            port=port,
            aedt_process_id=aedt_process_id,
            remove_lock=remove_lock,
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
        :class:`ansys.aedt.core.modeler.schematic.ModelerEmit`
            Design oModeler.
        """
        return self._modeler

    @property
    def couplings(self):
        """EMIT Couplings.

        Returns
        -------
        ansys.aedt.core.emit_core.couplings.CouplingsEmit
            Couplings within the EMIT Design
        """
        return self._couplings

    @pyaedt_function_handler()
    def version(self, detailed=False):
        """
        Get version information.

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
        """Set units for the EMIT design.

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
                        f"[{t}] units are not supported by EMIT. The options are: {EMIT_VALID_UNITS.keys()}: "
                    )
                    return False
                if v not in EMIT_VALID_UNITS[t]:
                    warnings.warn(f"[{v}] are not supported by EMIT. The options are: {EMIT_VALID_UNITS[t]}: ")
                    return False
                ut = emit_unit_type_string_to_enum(t)
                self._emit_api.set_units(ut, v)
                self._units[t] = v
        else:
            if unit_type not in EMIT_VALID_UNITS:
                warnings.warn(
                    f"[{unit_type}] units are not supported by EMIT. The options are: {EMIT_VALID_UNITS.keys()}: "
                )
                return False
            if unit_value not in EMIT_VALID_UNITS[unit_type]:
                warnings.warn(
                    f"[{unit_value}] are not supported by EMIT. The options are: {EMIT_VALID_UNITS[unit_type]}: "
                )
                return False
            # keep the backend global units synced
            ut = emit_unit_type_string_to_enum(unit_type)
            self._emit_api.set_units(ut, unit_value)
            self._units[unit_type] = unit_value
        return True

    @pyaedt_function_handler()
    def get_units(self, unit_type=""):
        """Get units for the EMIT design.

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
                f"[{unit_type}] units are not supported by EMIT. The options are: {EMIT_VALID_UNITS.keys()}: "
            )
            return None
        return self._units[unit_type]

    @pyaedt_function_handler()
    def save_project(self, file_name=None, overwrite=True, refresh_ids=False):
        """Save the AEDT project and the current EMIT revision.

        Parameters
        ----------
        file_name : str, optional
            Full path and project name. The default is ````None``.
        overwrite : bool, optional
            Whether to overwrite the existing project. The default is ``True``.
        refresh_ids : bool, optional
            Whether to refresh object IDs after saving the project.
            The default is ``False``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        """
        if self.__emit_api_enabled:
            self._emit_api.save_project()

        result = Design.save_project(self, file_name, overwrite, refresh_ids)

        return result
