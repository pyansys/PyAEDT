"""This module contains the ``Edb`` class.

This module is implicitily loaded in HFSS 3D Layout when launched.

"""
from itertools import combinations
import os
import shutil
import sys
import tempfile
import time
import traceback
import warnings

from pyaedt import settings
from pyaedt.application.Variables import decompose_variable_value
from pyaedt.edb_core.components import Components
from pyaedt.edb_core.dotnet.database import Database
from pyaedt.edb_core.dotnet.layout import LayoutDotNet
from pyaedt.edb_core.edb_data.control_file import ControlFile, convert_technology_file
from pyaedt.edb_core.edb_data.design_options import EdbDesignOptions
from pyaedt.edb_core.edb_data.edbvalue import EdbValue
from pyaedt.edb_core.edb_data.hfss_simulation_setup_data import HfssSimulationSetup
from pyaedt.edb_core.edb_data.ports import BundleWavePort, CoaxPort, ExcitationSources, GapPort, WavePort
from pyaedt.edb_core.edb_data.simulation_configuration import SimulationConfiguration
from pyaedt.edb_core.edb_data.siwave_simulation_setup_data import SiwaveDCSimulationSetup, SiwaveSYZSimulationSetup
from pyaedt.edb_core.edb_data.sources import SourceType
from pyaedt.edb_core.edb_data.terminals import (
    BundleTerminal,
    EdgeTerminal,
    PadstackInstanceTerminal,
    PinGroupTerminal,
    Terminal,
)
from pyaedt.edb_core.edb_data.variables import Variable
from pyaedt.edb_core.general import BoundaryType, LayoutObjType, Primitives, TerminalType, convert_py_list_to_net_list
from pyaedt.edb_core.hfss import EdbHfss
from pyaedt.edb_core.ipc2581.ipc2581 import Ipc2581
from pyaedt.edb_core.layout import EdbLayout
from pyaedt.edb_core.layout_validation import LayoutValidation
from pyaedt.edb_core.materials import Materials
from pyaedt.edb_core.net_class import EdbDifferentialPairs, EdbExtendedNets, EdbNetClasses
from pyaedt.edb_core.nets import EdbNets
from pyaedt.edb_core.padstack import EdbPadstacks
from pyaedt.edb_core.siwave import EdbSiwave
from pyaedt.edb_core.stackup import Stackup
from pyaedt.generic.constants import AEDT_UNITS, SolverType
from pyaedt.generic.general_methods import (
    generate_unique_name,
    get_string_version,
    inside_desktop,
    is_ironpython,
    is_linux,
    is_windows,
    pyaedt_function_handler,
)
from pyaedt.generic.process import SiwaveSolve
from pyaedt.modeler.geometry_operators import GeometryOperators

if is_linux and is_ironpython:
    import subprocessdotnet as subprocess
else:
    import subprocess


class Edb(Database):
    """Provides the EDB application interface.

    This module inherits all objects that belong to EDB.

    Parameters
    ----------
    edbpath : str, optional
        Full path to the ``aedb`` folder. The variable can also contain
        the path to a layout to import. Allowed formats are BRD, MCM,
        XML (IPC2581), GDS, and DXF. The default is ``None``.
        For GDS import, the Ansys control file (also XML) should have the same
        name as the GDS file. Only the file extension differs.
    cellname : str, optional
        Name of the cell to select. The default is ``None``.
    isreadonly : bool, optional
        Whether to open EBD in read-only mode when it is
        owned by HFSS 3D Layout. The default is ``False``.
    edbversion : str, int, float, optional
        Version of EDB to use. The default is ``None``.
        Examples of input values are ``232``, ``23.2``,``2023.2``,``"2023.2"``.
    isaedtowned : bool, optional
        Whether to launch EDB from HFSS 3D Layout. The
        default is ``False``.
    oproject : optional
        Reference to the AEDT project object.
    student_version : bool, optional
        Whether to open the AEDT student version. The default is ``False.``
    technology_file : str, optional
        Full path to technology file to be converted to xml before importing or xml. Supported by GDS format only.

    Examples
    --------
    Create an ``Edb`` object and a new EDB cell.

    >>> from pyaedt import Edb
    >>> app = Edb()

    Add a new variable named "s1" to the ``Edb`` instance.

    >>> app['s1'] = "0.25 mm"
    >>> app['s1'].tofloat
    >>> 0.00025
    >>> app['s1'].tostring
    >>> "0.25mm"

    or add a new parameter with description:

    >>> app['s2'] = ["20um", "Spacing between traces"]
    >>> app['s2'].value
    >>> 1.9999999999999998e-05
    >>> app['s2'].description
    >>> 'Spacing between traces'


    Create an ``Edb`` object and open the specified project.

    >>> app = Edb("myfile.aedb")

    Create an ``Edb`` object from GDS and control files.
    The XML control file resides in the same directory as the GDS file: (myfile.xml).

    >>> app = Edb("/path/to/file/myfile.gds")

    """

    def __init__(
        self,
        edbpath=None,
        cellname=None,
        isreadonly=False,
        edbversion=None,
        isaedtowned=False,
        oproject=None,
        student_version=False,
        use_ppe=False,
        technology_file=None,
    ):
        edbversion = get_string_version(edbversion)
        self._clean_variables()
        Database.__init__(self, edbversion=edbversion, student_version=student_version)
        self.standalone = True
        self.oproject = oproject
        self._main = sys.modules["__main__"]
        self.edbversion = edbversion
        self.isaedtowned = isaedtowned
        self.isreadonly = isreadonly
        self.cellname = cellname
        if not edbpath:
            if is_windows:
                edbpath = os.getenv("USERPROFILE")
                if not edbpath:
                    edbpath = os.path.expanduser("~")
                edbpath = os.path.join(edbpath, "Documents", generate_unique_name("layout") + ".aedb")
            else:
                edbpath = os.getenv("HOME")
                if not edbpath:
                    edbpath = os.path.expanduser("~")
                edbpath = os.path.join(edbpath, generate_unique_name("layout") + ".aedb")
            self.logger.info("No EDB is provided. Creating a new EDB {}.".format(edbpath))
        self.edbpath = edbpath
        self.log_name = None
        if edbpath:
            self.log_name = os.path.join(
                os.path.dirname(edbpath), "pyaedt_" + os.path.splitext(os.path.split(edbpath)[-1])[0] + ".log"
            )

        if isaedtowned and (inside_desktop or settings.remote_api or settings.remote_rpc_session):
            self.open_edb_inside_aedt()
        elif edbpath[-3:] in ["brd", "mcm", "gds", "xml", "dxf", "tgz"]:
            self.edbpath = edbpath[:-4] + ".aedb"
            working_dir = os.path.dirname(edbpath)
            control_file = None
            if technology_file:
                if os.path.splitext(technology_file)[1] == ".xml":
                    control_file = technology_file
                else:
                    control_file = convert_technology_file(technology_file, edbversion=edbversion)
            self.import_layout_pcb(edbpath, working_dir, use_ppe=use_ppe, control_file=control_file)
            if settings.enable_local_log_file and self.log_name:
                self._logger = self._global_logger.add_file_logger(self.log_name, "Edb")
            self.logger.info("EDB %s was created correctly from %s file.", self.edbpath, edbpath[-2:])
        elif edbpath.endswith("edb.def"):
            self.edbpath = os.path.dirname(edbpath)
            if settings.enable_local_log_file and self.log_name:
                self._logger = self._global_logger.add_file_logger(self.log_name, "Edb")
            self.open_edb()
        elif not os.path.exists(os.path.join(self.edbpath, "edb.def")):
            self.create_edb()
            if settings.enable_local_log_file and self.log_name:
                self._logger = self._global_logger.add_file_logger(self.log_name, "Edb")
            self.logger.info("EDB %s created correctly.", self.edbpath)
        elif ".aedb" in edbpath:
            self.edbpath = edbpath
            if settings.enable_local_log_file and self.log_name:
                self._logger = self._global_logger.add_file_logger(self.log_name, "Edb")
            self.open_edb()
        if self.active_cell:
            self.logger.info("EDB initialized.")
        else:
            self.logger.info("Failed to initialize DLLs.")

    def __enter__(self):
        return self

    def __exit__(self, ex_type, ex_value, ex_traceback):
        if ex_type:
            self.edb_exception(ex_value, ex_traceback)

    @pyaedt_function_handler()
    def __getitem__(self, variable_name):
        """Get or Set a variable to the Edb project. The variable can be project using ``$`` prefix or
        it can be a design variable, in which case the ``$`` is omitted.

        Parameters
        ----------
        variable_name : str

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.variables.Variable`

        """
        if self.variable_exists(variable_name)[0]:
            return self.variables[variable_name]
        return

    @pyaedt_function_handler()
    def __setitem__(self, variable_name, variable_value):
        type_error_message = "Allowed values are str, numeric or two-item list with variable description."
        if type(variable_value) in [list, tuple]:  # Two-item list or tuple. 2nd argument is a str description.
            if len(variable_value) == 2:
                if type(variable_value[1]) is str:
                    description = variable_value[1] if len(variable_value[1]) > 0 else None
                else:
                    description = None
                    pyaedt.edb_core.general.logger.warning("Invalid type for Edb variable desciprtion is ignored.")
                val = variable_value[0]
            else:
                raise TypeError(type_error_message)
        else:
            description = None
            val = variable_value
        if self.variable_exists(variable_name)[0]:
            self.change_design_variable_value(variable_name, val)
        else:
            self.add_design_variable(variable_name, val)
        if description:  # Add the variable description if a two-item list is passed for variable_value.
            self.__getitem__(variable_name).description = description

    def _clean_variables(self):
        """Initialize internal variables and perform garbage collection."""
        self._materials = None
        self._components = None
        self._core_primitives = None
        self._stackup = None
        self._stackup2 = None
        self._padstack = None
        self._siwave = None
        self._hfss = None
        self._nets = None
        self._setups = {}
        self._layout_instance = None
        self._variables = None
        self._active_cell = None
        self._layout = None
        # time.sleep(2)
        # gc.collect()

    @pyaedt_function_handler()
    def _init_objects(self):
        self._components = Components(self)
        self._stackup = Stackup(self)
        self._padstack = EdbPadstacks(self)
        self._siwave = EdbSiwave(self)
        self._hfss = EdbHfss(self)
        self._nets = EdbNets(self)
        self._core_primitives = EdbLayout(self)
        self._stackup2 = self._stackup
        self._materials = Materials(self)

    @property
    def cell_names(self):
        """Cell name container.

        Returns
        -------
        list of str, cell names.
        """
        names = []
        for cell in self.circuit_cells:
            names.append(cell.GetName())
        return names

    @property
    def design_variables(self):
        """Get all edb design variables.

        Returns
        -------
        Dict[str, :class:`pyaedt.edb_core.edb_data.variables.Variable`]
        """
        d_var = dict()
        for i in self.active_cell.GetVariableServer().GetAllVariableNames():
            d_var[i] = Variable(self, i)
        return d_var

    @property
    def project_variables(self):
        """Get all project variables.

        Returns
        -------
        Dict[str, :class:`pyaedt.edb_core.edb_data.variables.Variable`]

        """
        p_var = dict()
        for i in self.active_db.GetVariableServer().GetAllVariableNames():
            p_var[i] = Variable(self, i)
        return p_var

    @property
    def layout_validation(self):
        """:class:`pyaedt.edb_core.edb_data.layout_validation.LayoutValidation`."""
        return LayoutValidation(self)

    @property
    def variables(self):
        """Get all Edb variables.

        Returns
        -------
        Dict[str, :class:`pyaedt.edb_core.edb_data.variables.Variable`]

        """
        all_vars = dict()
        for i, j in self.project_variables.items():
            all_vars[i] = j
        for i, j in self.design_variables.items():
            all_vars[i] = j
        return all_vars

    @property
    def terminals(self):
        """Get terminals belonging to active layout."""
        temp = {}
        for i in self.layout.terminals:
            terminal_type = i.ToString().split(".")[-1]
            if terminal_type == TerminalType.EdgeTerminal.name:
                ter = EdgeTerminal(self, i)
            elif terminal_type == TerminalType.BundleTerminal.name:
                ter = BundleTerminal(self, i)
            elif terminal_type == TerminalType.PadstackInstanceTerminal.name:
                ter = PadstackInstanceTerminal(self, i)
            elif terminal_type == TerminalType.PinGroupTerminal.name:
                ter = PinGroupTerminal(self, i)
            else:
                ter = Terminal(self, i)
            temp[ter.name] = ter

        return temp

    @property
    def excitations(self):
        """Get all layout excitations."""
        terms = [term for term in self.layout.terminals if int(term.GetBoundaryType()) == 0]
        temp = {}
        for ter in terms:
            if "BundleTerminal" in ter.GetType().ToString():
                temp[ter.GetName()] = BundleWavePort(self, ter)
            else:
                temp[ter.GetName()] = GapPort(self, ter)
        return temp

    @property
    def ports(self):
        """Get all ports.

        Returns
        -------
        Dict[str, [:class:`pyaedt.edb_core.edb_data.ports.GapPort`,
                   :class:`pyaedt.edb_core.edb_data.ports.WavePort`,]]

        """
        temp = [term for term in self.layout.terminals if not term.IsReferenceTerminal()]

        ports = {}
        for t in temp:
            t2 = Terminal(self, t)
            if t2.terminal_type == TerminalType.BundleTerminal.name:
                bundle_ter = BundleWavePort(self, t)
                ports[bundle_ter.name] = bundle_ter
            elif t2.hfss_type == "Wave":
                ports[t2.name] = WavePort(self, t)
            elif t2.terminal_type == TerminalType.PadstackInstanceTerminal.name:
                ports[t2.name] = CoaxPort(self, t)
            else:
                ports[t2.name] = GapPort(self, t)
        return ports

    @property
    def excitations_nets(self):
        """Get all excitations net names."""
        names = list(set([i.GetNet().GetName() for i in self.layout.terminals]))
        names = [i for i in names if i]
        return names

    @property
    def sources(self):
        """Get all layout sources."""
        terms = [term for term in self.layout.terminals if int(term.GetBoundaryType()) in [3, 4, 7]]
        return {ter.GetName(): ExcitationSources(self, ter) for ter in terms}

    @property
    def probes(self):
        """Get all layout sources."""
        temp = {}
        for name, val in self.terminals.items():
            if val.boundary_type == BoundaryType.kVoltageProbe.name:
                if not val.is_reference_terminal:
                    temp[name] = val
        return temp

    @pyaedt_function_handler()
    def open_edb(self):
        """Open EDB.

        Returns
        -------

        """
        # self.logger.info("EDB Path is %s", self.edbpath)
        # self.logger.info("EDB Version is %s", self.edbversion)
        # if self.edbversion > "2023.1":
        #     self.standalone = False

        self.run_as_standalone(self.standalone)

        # self.logger.info("EDB Standalone %s", self.standalone)
        try:
            self.open(self.edbpath, self.isreadonly)
        except Exception:
            self.logger.error("Builder is not Initialized.")
        if not self.active_db:
            self.logger.warning("Error Opening db")
            self._active_cell = None
            return None
        self.logger.info("Database {} Opened in {}".format(os.path.split(self.edbpath)[-1], self.edbversion))

        self._active_cell = None
        if self.cellname:
            for cell in list(self.top_circuit_cells):
                if cell.GetName() == self.cellname:
                    self._active_cell = cell
        # if self._active_cell is still None, set it to default cell
        if self._active_cell is None:
            self._active_cell = list(self.top_circuit_cells)[0]
        self.logger.info("Cell %s Opened", self._active_cell.GetName())
        if self._active_cell:
            self._init_objects()
            self.logger.info("Builder was initialized.")
        else:
            self.logger.error("Builder was not initialized.")

        return True

    @pyaedt_function_handler()
    def open_edb_inside_aedt(self):
        """Open EDB inside of AEDT.

        Returns
        -------

        """
        self.logger.info("Opening EDB from HDL")
        self.run_as_standalone(False)
        if self.oproject.GetEDBHandle():
            self.attach(self.oproject.GetEDBHandle())
            if not self.active_db:
                self.logger.warning("Error getting the database.")
                self._active_cell = None
                return None
            self._active_cell = self.edb_api.cell.cell.FindByName(
                self.active_db, self.edb_api.cell._cell.CellType.CircuitCell, self.cellname
            )
            if self._active_cell is None:
                self._active_cell = list(self.top_circuit_cells)[0]
            if self._active_cell:
                if not os.path.exists(self.edbpath):
                    os.makedirs(self.edbpath)
                self._init_objects()
                return True
            else:
                return None
        else:
            self._active_cell = None
            return None

    @pyaedt_function_handler()
    def create_edb(self):
        """Create EDB."""
        # if self.edbversion > "2023.1":
        #     self.standalone = False

        self.run_as_standalone(self.standalone)
        self.create(self.edbpath)
        if not self.active_db:
            self.logger.warning("Error creating the database.")
            self._active_cell = None
            return None
        if not self.cellname:
            self.cellname = generate_unique_name("Cell")
        self._active_cell = self.edb_api.cell.create(
            self.active_db, self.edb_api.cell.CellType.CircuitCell, self.cellname
        )
        if self._active_cell:
            self._init_objects()
            return True
        return None

    @pyaedt_function_handler()
    def import_layout_pcb(self, input_file, working_dir, anstranslator_full_path="", use_ppe=False, control_file=None):
        """Import a board file and generate an ``edb.def`` file in the working directory.

        This function supports all AEDT formats, including DXF, GDS, SML (IPC2581), BRD, MCM and TGZ.

        Parameters
        ----------
        input_file : str
            Full path to the board file.
        working_dir : str
            Directory in which to create the ``aedb`` folder. The name given to the AEDB file
            is the same as the name of the board file.
        anstranslator_full_path : str, optional
            Full path to the Ansys translator. The default is ``""``.
        use_ppe : bool
            Whether to use the PPE License. The default is ``False``.
        control_file : str, optional
            Path to the XML file. The default is ``None``, in which case an attempt is made to find
            the XML file in the same directory as the board file. To succeed, the XML file and board file
            must have the same name. Only the extension differs.

        Returns
        -------
        str
            Full path to the AEDB file.
        """
        self._components = None
        self._core_primitives = None
        self._stackup = None
        self._padstack = None
        self._siwave = None
        self._hfss = None
        self._nets = None
        aedb_name = os.path.splitext(os.path.basename(input_file))[0] + ".aedb"
        if anstranslator_full_path and os.path.exists(anstranslator_full_path):
            command = anstranslator_full_path
        else:
            command = os.path.join(self.base_path, "anstranslator")
            if is_windows:
                command += ".exe"

        if not working_dir:
            working_dir = os.path.dirname(input_file)
        cmd_translator = [
            command,
            input_file,
            os.path.join(working_dir, aedb_name),
            "-l={}".format(os.path.join(working_dir, "Translator.log")),
        ]
        if not use_ppe:
            cmd_translator.append("-ppe=false")
        if control_file and input_file[-3:] not in ["brd", "mcm"]:
            if is_linux:
                cmd_translator.append("-c={}".format(control_file))
            else:
                cmd_translator.append('-c="{}"'.format(control_file))
        p = subprocess.Popen(cmd_translator)
        p.wait()
        if not os.path.exists(os.path.join(working_dir, aedb_name)):
            self.logger.error("Translator failed to translate.")
            return False
        else:
            self.logger.info("Translation correctly completed")
        self.edbpath = os.path.join(working_dir, aedb_name)
        return self.open_edb()

    @pyaedt_function_handler()
    def export_to_ipc2581(self, ipc_path=None, units="MILLIMETER"):
        """Create an XML IPC2581 file from the active EDB.

        .. note::
           The method works only in CPython because of some limitations on Ironpython in XML parsing and
           because it's time-consuming.
           This method is still being tested and may need further debugging.
           Any feedback is welcome. Backdrills and custom pads are not supported yet.

        Parameters
        ----------
        ipc_path : str, optional
            Path to the XML IPC2581 file. The default is ``None``, in which case
            an attempt is made to find the XML IPC2581 file in the same directory
            as the active EDB. To succeed, the XML IPC2581 file and the active
            EDT must have the same name. Only the extension differs.
        units : str, optional
            Units of the XML IPC2581 file. Options are ``"millimeter"``,
            ``"inch"``, and ``"micron"``. The default is ``"millimeter"``.

        Returns
        -------
        bool
            ``True`` if successful, ``False`` if failed.
        """
        if is_ironpython:  # pragma no cover
            self.logger.error("This method is not supported in Ironpython")
            return False
        if units.lower() not in ["millimeter", "inch", "micron"]:  # pragma no cover
            self.logger.warning("The wrong unit is entered. Setting to the default, millimeter.")
            units = "millimeter"

        if not ipc_path:
            ipc_path = self.edbpath[:-4] + "xml"
        self.logger.info("Export IPC 2581 is starting. This operation can take a while.")
        start = time.time()
        ipc = Ipc2581(self, units)
        ipc.load_ipc_model()
        ipc.file_path = ipc_path
        result = ipc.write_xml()

        if result:  # pragma no cover
            self.logger.info_timer("Export IPC 2581 completed.", start)
            self.logger.info("File saved as %s", ipc_path)
            return ipc_path
        self.logger.info("Error exporting IPC 2581.")
        return False

    def edb_exception(self, ex_value, tb_data):
        """Write the trace stack to AEDT when a Python error occurs.

        Parameters
        ----------
        ex_value :

        tb_data :


        Returns
        -------

        """
        tb_trace = traceback.format_tb(tb_data)
        tblist = tb_trace[0].split("\n")
        self.logger.error(str(ex_value))
        for el in tblist:
            self.logger.error(el)

    @property
    def active_db(self):
        """Database object."""
        return self.db

    @property
    def active_cell(self):
        """Active cell."""
        return self._active_cell

    @property
    def core_components(self):  # pragma: no cover
        """Edb Components methods and properties.

        .. deprecated:: 0.6.62
           Use new property :func:`components` instead.

        Returns
        -------
        Instance of :class:`pyaedt.edb_core.Components.Components`

        Examples
        --------
        >>> edbapp = pyaedt.Edb("myproject.aedb")
        >>> comp = self.edbapp.components.get_component_by_name("J1")
        """
        warnings.warn("Use new property :func:`components` instead.", DeprecationWarning)
        return self.components

    @property
    def components(self):
        """Edb Components methods and properties.

        Returns
        -------
        :class:`pyaedt.edb_core.components.Components`

        Examples
        --------
        >>> edbapp = pyaedt.Edb("myproject.aedb")
        >>> comp = self.edbapp.components.get_component_by_name("J1")
        """
        if not self._components and self.active_db:
            self._components = Components(self)
        return self._components

    @property
    def core_stackup(self):
        """Core stackup.

        .. deprecated:: 0.6.5
            There is no need to use the ``core_stackup`` property anymore.
            You can instantiate a new ``stackup`` class directly from the ``Edb`` class.
        """
        mess = "`core_stackup` is deprecated.\n"
        mess += " Use `app.stackup` directly to instantiate new stackup methods."
        warnings.warn(mess, DeprecationWarning)
        if not self._stackup and self.active_db:
            self._stackup = Stackup(self)
        return self._stackup

    @property
    def design_options(self):
        """Edb Design Settings and Options.

        Returns
        -------
        Instance of :class:`pyaedt.edb_core.edb_data.design_options.EdbDesignOptions`
        """
        return EdbDesignOptions(self.active_cell)

    @property
    def stackup(self):
        """Stackup manager.

        Returns
        -------
        Instance of :class: 'pyaedt.edb_core.Stackup`

        Examples
        --------
        >>> edbapp = pyaedt.Edb("myproject.aedb")
        >>> edbapp.stackup.layers["TOP"].thickness = 4e-5
        >>> edbapp.stackup.layers["TOP"].thickness == 4e-05
        >>> edbapp.stackup.add_layer("Diel", "GND", layer_type="dielectric", thickness="0.1mm", material="FR4_epoxy")
        """
        if not self._stackup2 and self.active_db:
            self._stackup2 = Stackup(self)
        return self._stackup2

    @property
    def materials(self):
        """Material Database.

        Returns
        -------
        Instance of :class: `pyaedt.edb_core.Materials`

        Examples
        --------
        >>> edbapp = pyaedt.Edb("myproject.aedb")
        >>> edbapp.materials["FR4_epoxy"].conductivity = 1
        >>> edbapp.materials.add_debye_material("My_Debye2", 5, 3, 0.02, 0.05, 1e5, 1e9)
        >>> edbapp.materials.add_djordjevicsarkar_material("MyDjord2", 3.3, 0.02, 3.3)
        """
        if not self._materials and self.active_db:
            self._materials = Materials(self)
        return self._materials

    @property
    def core_padstack(self):  # pragma: no cover
        """Core padstack.

        .. deprecated:: 0.6.62
           Use new property :func:`padstacks` instead.

        Returns
        -------
        Instance of :class: `pyaedt.edb_core.padstack.EdbPadstack`

        Examples
        --------
        >>> edbapp = pyaedt.Edb("myproject.aedb")
        >>> p = edbapp.padstacks.create(padstackname="myVia_bullet", antipad_shape="Bullet")
        >>> edbapp.padstacks.get_pad_parameters(
        >>> ... p, "TOP", self.edbapp.padstacks.pad_type.RegularPad
        >>> ... )
        """
        warnings.warn("Use new property :func:`padstacks` instead.", DeprecationWarning)
        return self.padstacks

    @property
    def padstacks(self):
        """Core padstack.

        Returns
        -------
        Instance of :class: `pyaedt.edb_core.padstack.EdbPadstack`

        Examples
        --------
        >>> edbapp = pyaedt.Edb("myproject.aedb")
        >>> p = edbapp.padstacks.create(padstackname="myVia_bullet", antipad_shape="Bullet")
        >>> edbapp.padstacks.get_pad_parameters(
        >>> ... p, "TOP", self.edbapp.padstacks.pad_type.RegularPad
        >>> ... )
        """
        if not self._padstack and self.active_db:
            self._padstack = EdbPadstacks(self)
        return self._padstack

    @property
    def core_siwave(self):  # pragma: no cover
        """Core SIWave methods and properties.

        .. deprecated:: 0.6.62
           Use new property :func:`siwave` instead.

        Returns
        -------
        Instance of :class: `pyaedt.edb_core.siwave.EdbSiwave`

        Examples
        --------
        >>> edbapp = pyaedt.Edb("myproject.aedb")
        >>> p2 = edbapp.siwave.create_circuit_port_on_net("U2A5", "V3P3_S0", "U2A5", "GND", 50, "test")
        """
        warnings.warn("Use new property :func:`siwave` instead.", DeprecationWarning)
        return self.siwave

    @property
    def siwave(self):
        """Core SIWave methods and properties.

        Returns
        -------
        Instance of :class: `pyaedt.edb_core.siwave.EdbSiwave`

        Examples
        --------
        >>> edbapp = pyaedt.Edb("myproject.aedb")
        >>> p2 = edbapp.siwave.create_circuit_port_on_net("U2A5", "V3P3_S0", "U2A5", "GND", 50, "test")
        """
        if not self._siwave and self.active_db:
            self._siwave = EdbSiwave(self)
        return self._siwave

    @property
    def core_hfss(self):  # pragma: no cover
        """Core HFSS methods and properties.

        .. deprecated:: 0.6.62
           Use new property :func:`hfss` instead.

        Returns
        -------
        Instance of :class:`pyaedt.edb_core.hfss.EdbHfss`

        Examples
        --------
        >>> edbapp = pyaedt.Edb("myproject.aedb")
        >>> edbapp.hfss.configure_hfss_analysis_setup(sim_config)
        """
        warnings.warn("Use new property :func:`hfss` instead.", DeprecationWarning)
        return self.hfss

    @property
    def hfss(self):
        """Core HFSS methods and properties.

        Returns
        -------
        :class:`pyaedt.edb_core.hfss.EdbHfss`

        Examples
        --------
        >>> edbapp = pyaedt.Edb("myproject.aedb")
        >>> edbapp.hfss.configure_hfss_analysis_setup(sim_config)
        """
        if not self._hfss and self.active_db:
            self._hfss = EdbHfss(self)
        return self._hfss

    @property
    def core_nets(self):  # pragma: no cover
        """Core nets.

        .. deprecated:: 0.6.62
           Use new property :func:`nets` instead.

        Returns
        -------
        :class:`pyaedt.edb_core.nets.EdbNets`

        Examples
        --------
        >>> edbapp = pyaedt.Edb("myproject.aedb")
        >>> edbapp.nets.find_or_create_net("GND")
        >>> edbapp.nets.find_and_fix_disjoint_nets("GND", keep_only_main_net=True)
        """
        warnings.warn("Use new property :func:`nets` instead.", DeprecationWarning)
        return self.nets

    @property
    def nets(self):
        """Core nets.

        Returns
        -------
        :class:`pyaedt.edb_core.nets.EdbNets`

        Examples
        --------
        >>> edbapp = pyaedt.Edb("myproject.aedb")
        >>> edbapp.nets.find_or_create_net("GND")
        >>> edbapp.nets.find_and_fix_disjoint_nets("GND", keep_only_main_net=True)
        """
        if not self._nets and self.active_db:
            self._nets = EdbNets(self)
        return self._nets

    @property
    def net_classes(self):
        """Get all net classes.

        Returns
        -------
        :class:`pyaedt.edb_core.nets.EdbNetClasses`

        Examples
        --------
        >>> edbapp = pyaedt.Edb("myproject.aedb")
        >>> edbapp.net_classes
        """
        if self.active_db:
            return EdbNetClasses(self)

    @property
    def extended_nets(self):
        """Get all extended nets.

        Returns
        -------
        :class:`pyaedt.edb_core.nets.EdbExtendedNets`

        Examples
        --------
        >>> edbapp = pyaedt.Edb("myproject.aedb")
        >>> edbapp.extended_nets
        """
        if self.active_db:
            return EdbExtendedNets(self)

    @property
    def differential_pairs(self):
        """Get all differential pairs.

        Returns
        -------
        :class:`pyaedt.edb_core.nets.EdbDifferentialPairs`

        Examples
        --------
        >>> edbapp = pyaedt.Edb("myproject.aedb")
        >>> edbapp.differential_pairs
        """
        if self.active_db:
            return EdbDifferentialPairs(self)
        else:  # pragma: no cover
            return

    @property
    def core_primitives(self):  # pragma: no cover
        """Core primitives.

        .. deprecated:: 0.6.62
           Use new property :func:`modeler` instead.

        Returns
        -------
        Instance of :class: `pyaedt.edb_core.layout.EdbLayout`

        Examples
        --------
        >>> edbapp = pyaedt.Edb("myproject.aedb")
        >>> top_prims = edbapp.modeler.primitives_by_layer["TOP"]
        """
        warnings.warn("Use new property :func:`modeler` instead.", DeprecationWarning)
        return self.modeler

    @property
    def modeler(self):
        """Core primitives modeler.

        Returns
        -------
        Instance of :class: `pyaedt.edb_core.layout.EdbLayout`

        Examples
        --------
        >>> edbapp = pyaedt.Edb("myproject.aedb")
        >>> top_prims = edbapp.modeler.primitives_by_layer["TOP"]
        """
        if not self._core_primitives and self.active_db:
            self._core_primitives = EdbLayout(self)
        return self._core_primitives

    @property
    def layout(self):
        """Layout object.

        Returns
        -------
        :class:`pyaedt.edb_core.dotnet.layout.Layout`
        """
        return LayoutDotNet(self)

    @property
    def active_layout(self):
        """Active layout.

        Returns
        -------
        Instance of EDB API Layout Class.
        """
        return self.layout._layout

    @property
    def layout_instance(self):
        """Edb Layout Instance."""
        return self.layout.layout_instance

    @pyaedt_function_handler
    def get_connected_objects(self, layout_object_instance):
        """Get connected objects.

        Returns
        -------
        list
        """
        temp = []
        for i in list(
            [
                loi.GetLayoutObj()
                for loi in self.layout_instance.GetConnectedObjects(layout_object_instance._edb_object).Items
            ]
        ):
            obj_type = i.GetObjType().ToString()
            if obj_type == LayoutObjType.PadstackInstance.name:
                from pyaedt.edb_core.edb_data.padstacks_data import EDBPadstackInstance

                temp.append(EDBPadstackInstance(i, self))
            elif obj_type == LayoutObjType.Primitive.name:
                prim_type = i.GetPrimitiveType().ToString()
                if prim_type == Primitives.Path.name:
                    from pyaedt.edb_core.edb_data.primitives_data import EdbPath

                    temp.append(EdbPath(i, self))
                elif prim_type == Primitives.Rectangle.name:
                    from pyaedt.edb_core.edb_data.primitives_data import EdbRectangle

                    temp.append(EdbRectangle(i, self))
                elif prim_type == Primitives.Circle.name:
                    from pyaedt.edb_core.edb_data.primitives_data import EdbCircle

                    temp.append(EdbCircle(i, self))
                elif prim_type == Primitives.Polygon.name:
                    from pyaedt.edb_core.edb_data.primitives_data import EdbPolygon

                    temp.append(EdbPolygon(i, self))
                else:
                    continue
            else:
                continue
        return temp

    @property
    def pins(self):
        """EDB padstack instance of the component.

        .. deprecated:: 0.6.62
           Use new method :func:`edb.padstacks.pins` instead.

        Returns
        -------
        dic[str, :class:`pyaedt.edb_core.edb_data.definitions.EDBPadstackInstance`]
            Dictionary of EDBPadstackInstance Components.


        Examples
        --------
        >>> edbapp = pyaedt.Edb("myproject.aedb")
        >>> pin_net_name = edbapp.pins[424968329].netname
        """
        warnings.warn("Use new method :func:`edb.padstacks.pins` instead.", DeprecationWarning)
        return self.padstacks.pins

    class Boundaries:
        """Boundaries Enumerator.

        Returns
        -------
        int
        """

        (Port, Pec, RLC, CurrentSource, VoltageSource, NexximGround, NexximPort, DcTerminal, VoltageProbe) = range(0, 9)

    @pyaedt_function_handler()
    def edb_value(self, val):
        """Convert a value to an EDB value. Value can be a string, float or integer. Mainly used in internal calls.

        Parameters
        ----------
        val : str, float, int


        Returns
        -------
        Instance of `Edb.Utility.Value`

        """
        return self.edb_api.utility.value(val)

    @pyaedt_function_handler()
    def point_3d(self, x, y, z=0.0):
        """Compute the Edb 3d Point Data.

        Parameters
        ----------
        x : float, int or str
            X value.
        y : float, int or str
            Y value.
        z : float, int or str, optional
            Z value.

        Returns
        -------
        ``Geometry.Point3DData``.
        """
        return self.edb_api.geometry.point3d_data(x, y, z)

    @pyaedt_function_handler()
    def point_data(self, x, y=None):
        """Compute the Edb Point Data.

        Parameters
        ----------
        x : float, int or str
            X value.
        y : float, int or str, optional
            Y value.


        Returns
        -------
        ``Geometry.PointData``.
        """
        if y is None:
            return self.edb_api.geometry.point_data(x)
        else:
            return self.edb_api.geometry.point_data(x, y)

    @pyaedt_function_handler()
    def _is_file_existing_and_released(self, filename):
        if os.path.exists(filename):
            try:
                os.rename(filename, filename + "_")
                os.rename(filename + "_", filename)
                return True
            except OSError:
                return False
        else:
            return False

    @pyaedt_function_handler()
    def _is_file_existing(self, filename):
        if os.path.exists(filename):
            return True
        else:
            return False

    @pyaedt_function_handler()
    def _wait_for_file_release(self, timeout=30, file_to_release=None):
        if not file_to_release:
            file_to_release = os.path.join(self.edbpath)
        tstart = time.time()
        while True:
            if self._is_file_existing_and_released(file_to_release):
                return True
            elif time.time() - tstart > timeout:
                return False
            else:
                time.sleep(0.250)

    @pyaedt_function_handler()
    def _wait_for_file_exists(self, timeout=30, file_to_release=None, wait_count=4):
        if not file_to_release:
            file_to_release = os.path.join(self.edbpath)
        tstart = time.time()
        times = 0
        while True:
            if self._is_file_existing(file_to_release):
                # print 'File is released'
                times += 1
                if times == wait_count:
                    return True
            elif time.time() - tstart > timeout:
                # print 'Timeout reached'
                return False
            else:
                times = 0
                time.sleep(0.250)

    @pyaedt_function_handler()
    def close_edb(self):
        """Close EDB and cleanup variables.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        self.close()
        if self.log_name and settings.enable_local_log_file:
            self._global_logger.remove_file_logger(os.path.splitext(os.path.split(self.log_name)[-1])[0])
            self._logger = self._global_logger
        start_time = time.time()
        self._wait_for_file_release()
        elapsed_time = time.time() - start_time
        self.logger.info("EDB file release time: {0:.2f}ms".format(elapsed_time * 1000.0))
        self._clean_variables()
        return True

    @pyaedt_function_handler()
    def save_edb(self):
        """Save the EDB file.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        self.save()
        start_time = time.time()
        self._wait_for_file_release()
        elapsed_time = time.time() - start_time
        self.logger.info("EDB file save time: {0:.2f}ms".format(elapsed_time * 1000.0))
        return True

    @pyaedt_function_handler()
    def save_edb_as(self, fname):
        """Save the EDB file as another file.

        Parameters
        ----------
        fname : str
            Name of the new file to save to.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        self.save_as(fname)
        start_time = time.time()
        self._wait_for_file_release()
        elapsed_time = time.time() - start_time
        self.logger.info("EDB file save time: {0:.2f}ms".format(elapsed_time * 1000.0))
        self.edbpath = self.directory
        if self.log_name:
            self._global_logger.remove_file_logger(os.path.splitext(os.path.split(self.log_name)[-1])[0])
            self._logger = self._global_logger

        self.log_name = os.path.join(
            os.path.dirname(fname), "pyaedt_" + os.path.splitext(os.path.split(fname)[-1])[0] + ".log"
        )
        if settings.enable_local_log_file:
            self._logger = self._global_logger.add_file_logger(self.log_name, "Edb")
        return True

    @pyaedt_function_handler()
    def execute(self, func):
        """Execute a function.

        Parameters
        ----------
        func : str
            Function to execute.


        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        return self.edb_api.utility.utility.Command.Execute(func)

    @pyaedt_function_handler()
    def import_cadence_file(self, inputBrd, WorkDir=None, anstranslator_full_path="", use_ppe=False):
        """Import a board file and generate an ``edb.def`` file in the working directory.

        Parameters
        ----------
        inputBrd : str
            Full path to the board file.
        WorkDir : str, optional
            Directory in which to create the ``aedb`` folder. The default value is ``None``,
            in which case the AEDB file is given the same name as the board file. Only
            the extension differs.
        anstranslator_full_path : str, optional
            Full path to the Ansys translator.
        use_ppe : bool, optional
            Whether to use the PPE License. The default is ``False``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        if self.import_layout_pcb(
            inputBrd, working_dir=WorkDir, anstranslator_full_path=anstranslator_full_path, use_ppe=use_ppe
        ):
            return True
        else:
            return False

    @pyaedt_function_handler()
    def import_gds_file(
        self,
        inputGDS,
        WorkDir=None,
        anstranslator_full_path="",
        use_ppe=False,
        control_file=None,
        tech_file=None,
        map_file=None,
    ):
        """Import a GDS file and generate an ``edb.def`` file in the working directory.

        ..note::
            `ANSYSLMD_LICENSE_FILE` is needed to run the translator.

        Parameters
        ----------
        inputGDS : str
            Full path to the GDS file.
        WorkDir : str, optional
            Directory in which to create the ``aedb`` folder. The default value is ``None``,
            in which case the AEDB file is given the same name as the GDS file. Only the extension
            differs.
        anstranslator_full_path : str, optional
            Full path to the Ansys translator.
        use_ppe : bool, optional
            Whether to use the PPE License. The default is ``False``.
        control_file : str, optional
            Path to the XML file. The default is ``None``, in which case an attempt is made to find
            the XML file in the same directory as the GDS file. To succeed, the XML file and GDS file must
            have the same name. Only the extension differs.
        tech_file : str, optional
            Technology file. It uses Helic to convert tech file to xml and then imports the gds. Works on Linux only.
        map_file : str, optional
            Layer map file.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        if tech_file or map_file:
            control_file_temp = os.path.join(tempfile.gettempdir(), os.path.split(inputGDS)[-1][:-3] + "xml")
            control_file = ControlFile(xml_input=control_file, tecnhology=tech_file, layer_map=map_file).write_xml(
                control_file_temp
            )
        elif tech_file:
            self.logger.error("Technology files are supported only in Linux. Use control file instead.")
            return False
        if self.import_layout_pcb(
            inputGDS,
            working_dir=WorkDir,
            anstranslator_full_path=anstranslator_full_path,
            use_ppe=use_ppe,
            control_file=control_file,
        ):
            return True
        else:
            return False

    @pyaedt_function_handler()
    def _create_extent(
        self,
        net_signals,
        extent_type,
        expansion_size,
        use_round_corner,
        use_pyaedt_extent=False,
        smart_cut=False,
        reference_list=[],
        include_pingroups=True,
    ):
        if extent_type in ["Conforming", self.edb_api.geometry.extent_type.Conforming, 1]:
            if use_pyaedt_extent:
                _poly = self._create_conformal(
                    net_signals,
                    expansion_size,
                    1e-12,
                    use_round_corner,
                    expansion_size,
                    smart_cut,
                    reference_list,
                    include_pingroups,
                )
            else:
                _poly = self.layout.expanded_extent(
                    net_signals,
                    self.edb_api.geometry.extent_type.Conforming,
                    expansion_size,
                    False,
                    use_round_corner,
                    1,
                )
        elif extent_type in ["Bounding", self.edb_api.geometry.extent_type.BoundingBox, 0]:
            _poly = self.layout.expanded_extent(
                net_signals, self.edb_api.geometry.extent_type.BoundingBox, expansion_size, False, use_round_corner, 1
            )
        else:
            if use_pyaedt_extent:
                _poly = self._create_convex_hull(
                    net_signals,
                    expansion_size,
                    1e-12,
                    use_round_corner,
                    expansion_size,
                    smart_cut,
                    reference_list,
                    include_pingroups,
                )
            else:
                _poly = self.layout.expanded_extent(
                    net_signals,
                    self.edb_api.geometry.extent_type.Conforming,
                    expansion_size,
                    False,
                    use_round_corner,
                    1,
                )
                _poly_list = convert_py_list_to_net_list([_poly])
                _poly = self.edb_api.geometry.polygon_data.get_convex_hull_of_polygons(_poly_list)
        return _poly

    @pyaedt_function_handler()
    def _create_conformal(
        self,
        net_signals,
        expansion_size,
        tolerance,
        round_corner,
        round_extension,
        smart_cutout=False,
        reference_list=[],
        include_pingroups=True,
    ):
        names = []
        _polys = []
        for net in net_signals:
            names.append(net.GetName())
        for prim in self.modeler.primitives:
            if prim is not None and prim.net_name in names:
                obj_data = prim.primitive_object.GetPolygonData().Expand(
                    expansion_size, tolerance, round_corner, round_extension
                )
                if obj_data:
                    _polys.extend(list(obj_data))
        if smart_cutout:
            _polys.extend(self._smart_cut(net_signals, reference_list, include_pingroups))
        _poly_unite = self.edb_api.geometry.polygon_data.unite(_polys)
        if len(_poly_unite) == 1:
            return _poly_unite[0]
        else:
            areas = [i.Area() for i in _poly_unite]
            return _poly_unite[areas.index(max(areas))]

    @pyaedt_function_handler()
    def _smart_cut(self, net_signals, reference_list=[], include_pingroups=True):
        _polys = []
        terms = [term for term in self.layout.terminals if int(term.GetBoundaryType()) in [0, 3, 4, 7, 8]]
        locations = []
        for term in terms:
            if term.GetTerminalType().ToString() == "PadstackInstanceTerminal":
                if term.GetParameters()[1].GetNet().GetName() in reference_list:
                    locations.append(self.padstacks.instances[term.GetParameters()[1].GetId()].position)
            elif term.GetTerminalType().ToString() == "PointTerminal" and term.GetNet().GetName() in reference_list:
                pd = term.GetParameters()[1]
                locations.append([pd.X.ToDouble(), pd.Y.ToDouble()])
        if include_pingroups:
            for reference in reference_list:
                for pin in self.nets.nets[reference].padstack_instances:
                    if pin.pingroups:
                        locations.append(pin.position)
        for point in locations:
            pointA = self.edb_api.geometry.point_data(
                self.edb_value(point[0] - 1e-12), self.edb_value(point[1] - 1e-12)
            )
            pointB = self.edb_api.geometry.point_data(
                self.edb_value(point[0] + 1e-12), self.edb_value(point[1] + 1e-12)
            )

            points = Tuple[self.edb_api.geometry.geometry.PointData, self.edb_api.geometry.geometry.PointData](
                pointA, pointB
            )
            _polys.append(self.edb_api.geometry.polygon_data.create_from_bbox(points))
        for cname, c in self.components.instances.items():
            if (
                set(net_signals).intersection(c.nets)
                and c.is_enabled
                and c.model_type in ["SParameterModel", "SpiceModel", "NetlistModel"]
            ):
                for pin in c.pins:
                    locations.append(pin.position)
        return _polys

    @pyaedt_function_handler()
    def _create_convex_hull(
        self,
        net_signals,
        expansion_size,
        tolerance,
        round_corner,
        round_extension,
        smart_cut=False,
        reference_list=[],
        include_pingroups=True,
    ):
        names = []
        _polys = []
        for net in net_signals:
            names.append(net.GetName())
        for prim in self.modeler.primitives:
            if prim is not None and prim.net_name in names:
                _polys.append(prim.primitive_object.GetPolygonData())
        if smart_cut:
            _polys.extend(self._smart_cut(net_signals, reference_list, include_pingroups))
        _poly = self.edb_api.geometry.polygon_data.get_convex_hull_of_polygons(convert_py_list_to_net_list(_polys))
        _poly = _poly.Expand(expansion_size, tolerance, round_corner, round_extension)[0]
        return _poly

    @pyaedt_function_handler()
    def cutout(
        self,
        signal_list=None,
        reference_list=None,
        extent_type="ConvexHull",
        expansion_size=0.002,
        use_round_corner=False,
        output_aedb_path=None,
        open_cutout_at_end=True,
        use_pyaedt_cutout=True,
        number_of_threads=4,
        use_pyaedt_extent_computing=True,
        extent_defeature=0,
        remove_single_pin_components=False,
        custom_extent=None,
        custom_extent_units="mm",
        include_partial_instances=False,
        keep_voids=True,
        check_terminals=False,
        include_pingroups=False,
        expansion_factor=0,
        maximum_iterations=10,
        preserve_components_with_model=False,
        simple_pad_check=True,
        keep_lines_as_path=False,
    ):
        """Create a cutout using an approach entirely based on PyAEDT.
        This method replaces all legacy cutout methods in PyAEDT.
        It does in sequence:
        - delete all nets not in list,
        - create a extent of the nets,
        - check and delete all vias not in the extent,
        - check and delete all the primitives not in extent,
        - check and intersect all the primitives that intersect the extent.

        Parameters
        ----------
         signal_list : list
            List of signal strings.
        reference_list : list, optional
            List of references to add. The default is ``["GND"]``.
        extent_type : str, optional
            Type of the extension. Options are ``"Conforming"``, ``"ConvexHull"``, and
            ``"Bounding"``. The default is ``"Conforming"``.
        expansion_size : float, str, optional
            Expansion size ratio in meters. The default is ``0.002``.
        use_round_corner : bool, optional
            Whether to use round corners. The default is ``False``.
        output_aedb_path : str, optional
            Full path and name for the new AEDB file. If None, then current aedb will be cutout.
        open_cutout_at_end : bool, optional
            Whether to open the cutout at the end. The default is ``True``.
        use_pyaedt_cutout : bool, optional
            Whether to use new PyAEDT cutout method or EDB API method.
            New method is faster than native API method since it benefits of multithread.
        number_of_threads : int, optional
            Number of thread to use. Default is 4. Valid only if ``use_pyaedt_cutout`` is set to ``True``.
        use_pyaedt_extent_computing : bool, optional
            Whether to use pyaedt extent computing (experimental) or EDB API.
        extent_defeature : float, optional
            Defeature the cutout before applying it to produce simpler geometry for mesh (Experimental).
            It applies only to Conforming bounding box. Default value is ``0`` which disable it.
        remove_single_pin_components : bool, optional
            Remove all Single Pin RLC after the cutout is completed. Default is `False`.
        custom_extent : list
            Points list defining the cutout shape. This setting will override `extent_type` field.
        custom_extent_units : str
            Units of the point list. The default is ``"mm"``. Valid only if `custom_extend` is provided.
        include_partial_instances : bool, optional
            Whether to include padstack instances that have bounding boxes intersecting with point list polygons.
            This operation may slow down the cutout export.Valid only if `custom_extend` and
            `use_pyaedt_cutout` is provided.
        keep_voids : bool
            Boolean used for keep or not the voids intersecting the polygon used for clipping the layout.
            Default value is ``True``, ``False`` will remove the voids.Valid only if `custom_extend` is provided.
        check_terminals : bool, optional
            Whether to check for all reference terminals and increase extent to include them into the cutout.
            This applies to components which have a model (spice, touchstone or netlist) associated.
        include_pingroups : bool, optional
            Whether to check for all pingroups terminals and increase extent to include them into the cutout.
            It requires ``check_terminals``.
        expansion_factor : int, optional
            The method computes a float representing the largest number between
            the dielectric thickness or trace width multiplied by the expansion_factor factor.
            The trace width search is limited to nets with ports attached. Works only if `use_pyaedt_cutout`.
            Default is `0` to disable the search.
        maximum_iterations : int, optional
            Maximum number of iterations before stopping a search for a cutout with an error.
            Default is `10`.
        preserve_components_with_model : bool, optional
            Whether to preserve all pins of components that have associated models (Spice or NPort).
            This parameter is applicable only for a PyAEDT cutout (except point list).
        simple_pad_check : bool, optional
            Whether to use the center of the pad to find the intersection with extent or use the bounding box.
            Second method is much slower and requires to disable multithread on padstack removal.
            Default is `True`.
        keep_lines_as_path : bool, optional
            Whether to keep the lines as Path after they are cutout or convert them to PolygonData.
            This feature works only in Electronics Desktop (3D Layout).
            If the flag is set to ``True`` it can cause issues in SiWave once the Edb is imported.
            Default is ``False`` to generate PolygonData of cut lines.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------
        >>> edb = Edb(r'C:\\test.aedb', edbversion="2022.2")
        >>> edb.logger.info_timer("Edb Opening")
        >>> edb.logger.reset_timer()
        >>> start = time.time()
        >>> signal_list = []
        >>> for net in edb.nets.netlist:
        >>>      if "3V3" in net:
        >>>           signal_list.append(net)
        >>> power_list = ["PGND"]
        >>> edb.cutout(signal_list=signal_list, reference_list=power_list, extent_type="Conforming")
        >>> end_time = str((time.time() - start)/60)
        >>> edb.logger.info("Total pyaedt cutout time in min %s", end_time)
        >>> edb.nets.plot(signal_list, None, color_by_net=True)
        >>> edb.nets.plot(power_list, None, color_by_net=True)
        >>> edb.save_edb()
        >>> edb.close_edb()


        """
        if expansion_factor > 0:
            expansion_size = self.calculate_initial_extent(expansion_factor)
        if signal_list is None:
            signal_list = []
        if isinstance(reference_list, str):
            reference_list = [reference_list]
        elif reference_list is None:
            reference_list = []
        if not use_pyaedt_cutout and custom_extent:
            return self._create_cutout_on_point_list(
                custom_extent,
                units=custom_extent_units,
                output_aedb_path=output_aedb_path,
                open_cutout_at_end=open_cutout_at_end,
                nets_to_include=signal_list + reference_list,
                include_partial_instances=include_partial_instances,
                keep_voids=keep_voids,
            )
        elif not use_pyaedt_cutout:
            return self._create_cutout_legacy(
                signal_list=signal_list,
                reference_list=reference_list,
                extent_type=extent_type,
                expansion_size=expansion_size,
                use_round_corner=use_round_corner,
                output_aedb_path=output_aedb_path,
                open_cutout_at_end=open_cutout_at_end,
                use_pyaedt_extent_computing=use_pyaedt_extent_computing,
                check_terminals=check_terminals,
                include_pingroups=include_pingroups,
            )
        else:
            legacy_path = self.edbpath
            if expansion_factor > 0 and not custom_extent:
                start = time.time()
                self.save_edb()
                dummy_path = self.edbpath.replace(".aedb", "_smart_cutout_temp.aedb")
                working_cutout = False
                i = 1
                expansion = expansion_size
                while i <= maximum_iterations:
                    self.logger.info("-----------------------------------------")
                    self.logger.info("Trying cutout with {}mm expansion size".format(expansion * 1e3))
                    self.logger.info("-----------------------------------------")
                    result = self._create_cutout_multithread(
                        signal_list=signal_list,
                        reference_list=reference_list,
                        extent_type=extent_type,
                        expansion_size=expansion,
                        use_round_corner=use_round_corner,
                        number_of_threads=number_of_threads,
                        custom_extent=custom_extent,
                        output_aedb_path=dummy_path,
                        remove_single_pin_components=remove_single_pin_components,
                        use_pyaedt_extent_computing=use_pyaedt_extent_computing,
                        extent_defeature=extent_defeature,
                        custom_extent_units=custom_extent_units,
                        check_terminals=check_terminals,
                        include_pingroups=include_pingroups,
                        preserve_components_with_model=preserve_components_with_model,
                        include_partial=include_partial_instances,
                        simple_pad_check=simple_pad_check,
                        keep_lines_as_path=keep_lines_as_path,
                    )
                    if self.are_port_reference_terminals_connected():
                        if output_aedb_path:
                            self.save_edb_as(output_aedb_path)
                        else:
                            self.save_edb_as(legacy_path)
                        working_cutout = True
                        break
                    self.close_edb()
                    self.edbpath = legacy_path
                    self.open_edb()
                    i += 1
                    expansion = expansion_size * i
                if working_cutout:
                    msg = "Cutout completed in {} iterations with expansion size of {}mm".format(i, expansion * 1e3)
                    self.logger.info_timer(msg, start)
                else:
                    msg = "Cutout failed after {} iterations and expansion size of {}mm".format(i, expansion * 1e3)
                    self.logger.info_timer(msg, start)
                    return False
            else:
                result = self._create_cutout_multithread(
                    signal_list=signal_list,
                    reference_list=reference_list,
                    extent_type=extent_type,
                    expansion_size=expansion_size,
                    use_round_corner=use_round_corner,
                    number_of_threads=number_of_threads,
                    custom_extent=custom_extent,
                    output_aedb_path=output_aedb_path,
                    remove_single_pin_components=remove_single_pin_components,
                    use_pyaedt_extent_computing=use_pyaedt_extent_computing,
                    extent_defeature=extent_defeature,
                    custom_extent_units=custom_extent_units,
                    check_terminals=check_terminals,
                    include_pingroups=include_pingroups,
                    preserve_components_with_model=preserve_components_with_model,
                    include_partial=include_partial_instances,
                    simple_pad_check=simple_pad_check,
                    keep_lines_as_path=keep_lines_as_path,
                )
            if result and not open_cutout_at_end and self.edbpath != legacy_path:
                self.save_edb()
                self.close_edb()
                self.edbpath = legacy_path
                self.open_edb()
            return result

    @pyaedt_function_handler()
    def _create_cutout_legacy(
        self,
        signal_list=[],
        reference_list=["GND"],
        extent_type="Conforming",
        expansion_size=0.002,
        use_round_corner=False,
        output_aedb_path=None,
        open_cutout_at_end=True,
        use_pyaedt_extent_computing=False,
        remove_single_pin_components=False,
        check_terminals=False,
        include_pingroups=True,
    ):
        expansion_size = self.edb_value(expansion_size).ToDouble()

        # validate nets in layout
        net_signals = [net.api_object for net in self.layout.nets if net.name in signal_list]

        # validate references in layout
        _netsClip = convert_py_list_to_net_list(
            [net.api_object for net in self.layout.nets if net.name in reference_list]
        )

        _poly = self._create_extent(
            net_signals,
            extent_type,
            expansion_size,
            use_round_corner,
            use_pyaedt_extent_computing,
            smart_cut=check_terminals,
            reference_list=reference_list,
            include_pingroups=include_pingroups,
        )

        # Create new cutout cell/design
        included_nets_list = signal_list + reference_list
        included_nets = convert_py_list_to_net_list(
            [net.api_object for net in self.layout.nets if net.name in included_nets_list]
        )
        _cutout = self.active_cell.CutOut(included_nets, _netsClip, _poly, True)
        # Analysis setups do not come over with the clipped design copy,
        # so add the analysis setups from the original here.
        id = 1
        for _setup in self.active_cell.SimulationSetups:
            # Empty string '' if coming from setup copy and don't set explicitly.
            _setup_name = _setup.GetName()
            if "GetSimSetupInfo" in dir(_setup):
                # setup is an Ansys.Ansoft.Edb.Utility.HFSSSimulationSetup object
                _hfssSimSetupInfo = _setup.GetSimSetupInfo()
                _hfssSimSetupInfo.Name = "HFSS Setup " + str(id)  # Set name of analysis setup
                # Write the simulation setup info into the cell/design setup
                _setup.SetSimSetupInfo(_hfssSimSetupInfo)
                _cutout.AddSimulationSetup(_setup)  # Add simulation setup to the cutout design
                id += 1
            else:
                _cutout.AddSimulationSetup(_setup)  # Add simulation setup to the cutout design

        _dbCells = [_cutout]

        if output_aedb_path:
            db2 = self.create(output_aedb_path)
            _success = db2.Save()
            _dbCells = convert_py_list_to_net_list(_dbCells)
            db2.CopyCells(_dbCells)  # Copies cutout cell/design to db2 project
            if len(list(db2.CircuitCells)) > 0:
                for net in list(list(db2.CircuitCells)[0].GetLayout().Nets):
                    if net.GetName() not in included_nets_list:
                        net.Delete()
                _success = db2.Save()
            for c in list(self.active_db.TopCircuitCells):
                if c.GetName() == _cutout.GetName():
                    c.Delete()
            if open_cutout_at_end:  # pragma: no cover
                self._db = db2
                self.edbpath = output_aedb_path
                self._active_cell = list(self.top_circuit_cells)[0]
                self.edbpath = self.directory
                self._init_objects()
                if remove_single_pin_components:
                    self.components.delete_single_pin_rlc()
                    self.logger.info_timer("Single Pins components deleted")
                    self.components.refresh_components()
            else:
                if remove_single_pin_components:
                    try:
                        layout = list(db2.CircuitCells)[0].GetLayout()
                        _cmps = [
                            l
                            for l in layout.Groups
                            if l.ToString() == "Ansys.Ansoft.Edb.Cell.Hierarchy.Component" and l.GetNumberOfPins() < 2
                        ]
                        for _cmp in _cmps:
                            _cmp.Delete()
                    except:
                        self._logger.error("Failed to remove single pin components.")
                db2.Close()
                source = os.path.join(output_aedb_path, "edb.def.tmp")
                target = os.path.join(output_aedb_path, "edb.def")
                self._wait_for_file_release(file_to_release=output_aedb_path)
                if os.path.exists(source) and not os.path.exists(target):
                    try:
                        shutil.copy(source, target)
                    except:
                        pass
        elif open_cutout_at_end:
            self._active_cell = _cutout
            self._init_objects()
            if remove_single_pin_components:
                self.components.delete_single_pin_rlc()
                self.logger.info_timer("Single Pins components deleted")
                self.components.refresh_components()
        return True

    @pyaedt_function_handler()
    def create_cutout(
        self,
        signal_list=[],
        reference_list=["GND"],
        extent_type="Conforming",
        expansion_size=0.002,
        use_round_corner=False,
        output_aedb_path=None,
        open_cutout_at_end=True,
        use_pyaedt_extent_computing=False,
    ):
        """Create a cutout using an approach entirely based on pyaedt.
        It does in sequence:
        - delete all nets not in list,
        - create an extent of the nets,
        - check and delete all vias not in the extent,
        - check and delete all the primitives not in extent,
        - check and intersect all the primitives that intersect the extent.

        .. deprecated:: 0.6.58
           Use new method :func:`cutout` instead.

        Parameters
        ----------
        signal_list : list
            List of signal strings.
        reference_list : list, optional
            List of references to add. The default is ``["GND"]``.
        extent_type : str, optional
            Type of the extension. Options are ``"Conforming"``, ``"ConvexHull"``, and
            ``"Bounding"``. The default is ``"Conforming"``.
        expansion_size : float, str, optional
            Expansion size ratio in meters. The default is ``0.002``.
        use_round_corner : bool, optional
            Whether to use round corners. The default is ``False``.
        output_aedb_path : str, optional
            Full path and name for the new AEDB file.
        open_cutout_at_end : bool, optional
            Whether to open the cutout at the end. The default
            is ``True``.
        use_pyaedt_extent_computing : bool, optional
            Whether to use pyaedt extent computing (experimental).

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        warnings.warn("Use new method `cutout` instead.", DeprecationWarning)
        return self._create_cutout_legacy(
            signal_list=signal_list,
            reference_list=reference_list,
            extent_type=extent_type,
            expansion_size=expansion_size,
            use_round_corner=use_round_corner,
            output_aedb_path=output_aedb_path,
            open_cutout_at_end=open_cutout_at_end,
            use_pyaedt_extent_computing=use_pyaedt_extent_computing,
        )

    @pyaedt_function_handler()
    def _create_cutout_multithread(
        self,
        signal_list=[],
        reference_list=["GND"],
        extent_type="Conforming",
        expansion_size=0.002,
        use_round_corner=False,
        number_of_threads=4,
        custom_extent=None,
        output_aedb_path=None,
        remove_single_pin_components=False,
        use_pyaedt_extent_computing=False,
        extent_defeature=0.0,
        custom_extent_units="mm",
        check_terminals=False,
        include_pingroups=True,
        preserve_components_with_model=False,
        include_partial=False,
        simple_pad_check=True,
        keep_lines_as_path=False,
    ):
        if is_ironpython:  # pragma: no cover
            self.logger.error("Method working only in Cpython")
            return False
        from concurrent.futures import ThreadPoolExecutor

        if output_aedb_path:
            self.save_edb_as(output_aedb_path)
        self.logger.info("Cutout Multithread started.")
        expansion_size = self.edb_value(expansion_size).ToDouble()

        timer_start = self.logger.reset_timer()
        if custom_extent:
            if not reference_list and not signal_list:
                reference_list = self.nets.netlist[::]
                all_list = reference_list
            else:
                reference_list = reference_list + signal_list
                all_list = reference_list
        else:
            all_list = signal_list + reference_list
        pins_to_preserve = []
        nets_to_preserve = []
        if preserve_components_with_model:
            for el in self.components.instances.values():
                if el.model_type in ["SPICEModel", "SParameterModel", "NetlistModel"] and list(
                    set(el.nets[:]) & set(signal_list[:])
                ):
                    pins_to_preserve.extend([i.id for i in el.pins.values()])
                    nets_to_preserve.extend(el.nets)

        for i in self.nets.nets.values():
            name = i.name
            if name not in all_list and name not in nets_to_preserve:
                i.net_object.Delete()
        reference_pinsts = []
        reference_prims = []
        reference_paths = []
        for i in self.padstacks.instances.values():
            net_name = i.net_name
            id = i.id
            if net_name not in all_list and id not in pins_to_preserve:
                i.delete()
            elif net_name in reference_list and id not in pins_to_preserve:
                reference_pinsts.append(i)
        for i in self.modeler.primitives:
            if i:
                net_name = i.net_name
                if net_name not in all_list:
                    i.delete()
                elif net_name in reference_list and not i.is_void:
                    if keep_lines_as_path and i.type == "Path":
                        reference_paths.append(i)
                    else:
                        reference_prims.append(i)
        self.logger.info_timer("Net clean up")
        self.logger.reset_timer()

        if custom_extent and isinstance(custom_extent, list):
            if custom_extent[0] != custom_extent[-1]:
                custom_extent.append(custom_extent[0])
            custom_extent = [
                [self.number_with_units(i[0], custom_extent_units), self.number_with_units(i[1], custom_extent_units)]
                for i in custom_extent
            ]
            plane = self.modeler.Shape("polygon", points=custom_extent)
            _poly = self.modeler.shape_to_polygon_data(plane)
        elif custom_extent:
            _poly = custom_extent
        else:
            net_signals = [net.api_object for net in self.layout.nets if net.name in signal_list]
            _poly = self._create_extent(
                net_signals,
                extent_type,
                expansion_size,
                use_round_corner,
                use_pyaedt_extent_computing,
                smart_cut=check_terminals,
                reference_list=reference_list,
                include_pingroups=include_pingroups,
            )
            if extent_type in ["Conforming", self.edb_api.geometry.extent_type.Conforming, 1] and extent_defeature > 0:
                _poly = _poly.Defeature(extent_defeature)

        if not _poly or _poly.IsNull():
            self._logger.error("Failed to create Extent.")
            return False
        self.logger.info_timer("Expanded Net Polygon Creation")
        self.logger.reset_timer()
        _poly_list = convert_py_list_to_net_list([_poly])
        prims_to_delete = []
        poly_to_create = []
        pins_to_delete = []

        def intersect(poly1, poly2):
            if not isinstance(poly2, list):
                poly2 = [poly2]
            return list(poly1.Intersect(convert_py_list_to_net_list(poly1), convert_py_list_to_net_list(poly2)))

        def subtract(poly, voids):
            return poly.Subtract(convert_py_list_to_net_list(poly), convert_py_list_to_net_list(voids))

        def clip_path(path):
            pdata = path.polygon_data.edb_api
            int_data = _poly.GetIntersectionType(pdata)
            if int_data == 0:
                prims_to_delete.append(path)
                return
            result = path._edb_object.SetClipInfo(_poly, True)
            if not result:
                self.logger.info("Failed to clip path {}. Clipping as polygon.".format(path.id))
                reference_prims.append(path)

        def clean_prim(prim_1):  # pragma: no cover
            pdata = prim_1.polygon_data.edb_api
            int_data = _poly.GetIntersectionType(pdata)
            if int_data == 2:
                return
            elif int_data == 0:
                prims_to_delete.append(prim_1)
            else:
                list_poly = intersect(_poly, pdata)
                if list_poly:
                    net = prim_1.net_name
                    voids = prim_1.voids
                    for p in list_poly:
                        if p.IsNull():
                            continue
                        # points = list(p.Points)
                        list_void = []
                        if voids:
                            voids_data = [void.polygon_data.edb_api for void in voids]
                            list_prims = subtract(p, voids_data)
                            for prim in list_prims:
                                if not prim.IsNull():
                                    poly_to_create.append([prim, prim_1.layer_name, net, list_void])
                        else:
                            poly_to_create.append([p, prim_1.layer_name, net, list_void])

                prims_to_delete.append(prim_1)

        def pins_clean(pinst):
            if not pinst.in_polygon(_poly, include_partial=include_partial, simple_check=simple_pad_check):
                pins_to_delete.append(pinst)

        if not simple_pad_check:
            pad_cores = 1
        else:
            pad_cores = number_of_threads
        with ThreadPoolExecutor(pad_cores) as pool:
            pool.map(lambda item: pins_clean(item), reference_pinsts)

        for pin in pins_to_delete:
            pin.delete()

        self.logger.info_timer("Padstack Instances removal completed")
        self.logger.reset_timer()

        # with ThreadPoolExecutor(number_of_threads) as pool:
        #     pool.map(lambda item: clip_path(item), reference_paths)

        for item in reference_paths:
            clip_path(item)
        with ThreadPoolExecutor(number_of_threads) as pool:
            pool.map(lambda item: clean_prim(item), reference_prims)

        for el in poly_to_create:
            self.modeler.create_polygon(el[0], el[1], net_name=el[2], voids=el[3])

        for prim in prims_to_delete:
            prim.delete()

        self.logger.info_timer("Primitives cleanup completed")
        self.logger.reset_timer()

        i = 0
        for _, val in self.components.components.items():
            if val.numpins == 0:
                val.edbcomponent.Delete()
                i += 1
                i += 1
        self.logger.info("Deleted {} additional components".format(i))
        if remove_single_pin_components:
            self.components.delete_single_pin_rlc()
            self.logger.info_timer("Single Pins components deleted")

        self.components.refresh_components()
        if output_aedb_path:
            self.save_edb()
        self.logger.info_timer("Cutout completed.", timer_start)
        self.logger.reset_timer()
        return True

    @pyaedt_function_handler()
    def create_cutout_multithread(
        self,
        signal_list=[],
        reference_list=["GND"],
        extent_type="Conforming",
        expansion_size=0.002,
        use_round_corner=False,
        number_of_threads=4,
        custom_extent=None,
        output_aedb_path=None,
        remove_single_pin_components=False,
        use_pyaedt_extent_computing=False,
        extent_defeature=0,
        keep_lines_as_path=False,
    ):
        """Create a cutout using an approach entirely based on pyaedt.
        It does in sequence:
        - delete all nets not in list,
        - create a extent of the nets,
        - check and delete all vias not in the extent,
        - check and delete all the primitives not in extent,
        - check and intersect all the primitives that intersect the extent.


        .. deprecated:: 0.6.58
           Use new method :func:`cutout` instead.

        Parameters
        ----------
        signal_list : list
            List of signal strings.
        reference_list : list, optional
            List of references to add. The default is ``["GND"]``.
        extent_type : str, optional
            Type of the extension. Options are ``"Conforming"``, ``"ConvexHull"``, and
            ``"Bounding"``. The default is ``"Conforming"``.
        expansion_size : float, str, optional
            Expansion size ratio in meters. The default is ``0.002``.
        use_round_corner : bool, optional
            Whether to use round corners. The default is ``False``.
        number_of_threads : int, optional
            Number of thread to use. Default is 4
        custom_extent : list, optional
            Custom extent to use for the cutout. It has to be a list of points [[x1,y1],[x2,y2]....] or
            Edb PolygonData object. In this case, both signal_list and reference_list will be cut.
        output_aedb_path : str, optional
            Full path and name for the new AEDB file. If None, then current aedb will be cutout.
        remove_single_pin_components : bool, optional
            Remove all Single Pin RLC after the cutout is completed. Default is `False`.
        use_pyaedt_extent_computing : bool, optional
            Whether to use pyaedt extent computing (experimental).
        extent_defeature : float, optional
            Defeature the cutout before applying it to produce simpler geometry for mesh (Experimental).
            It applies only to Conforming bounding box. Default value is ``0`` which disable it.
        keep_lines_as_path : bool, optional
            Whether to keep the lines as Path after they are cutout or convert them to PolygonData.
            This feature works only in Electronics Desktop (3D Layout).
            If the flag is set to True it can cause issues in SiWave once the Edb is imported.
            Default is ``False`` to generate PolygonData of cut lines.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------
        >>> edb = Edb(r'C:\\test.aedb', edbversion="2022.2")
        >>> edb.logger.info_timer("Edb Opening")
        >>> edb.logger.reset_timer()
        >>> start = time.time()
        >>> signal_list = []
        >>> for net in edb.nets.nets.keys():
        >>>      if "3V3" in net:
        >>>           signal_list.append(net)
        >>> power_list = ["PGND"]
        >>> edb.create_cutout_multithread(signal_list=signal_list, reference_list=power_list, extent_type="Conforming")
        >>> end_time = str((time.time() - start)/60)
        >>> edb.logger.info("Total pyaedt cutout time in min %s", end_time)
        >>> edb.nets.plot(signal_list, None, color_by_net=True)
        >>> edb.nets.plot(power_list, None, color_by_net=True)
        >>> edb.save_edb()
        >>> edb.close_edb()

        """
        warnings.warn("Use new method `cutout` instead.", DeprecationWarning)
        return self._create_cutout_multithread(
            signal_list=signal_list,
            reference_list=reference_list,
            extent_type=extent_type,
            expansion_size=expansion_size,
            use_round_corner=use_round_corner,
            number_of_threads=number_of_threads,
            custom_extent=custom_extent,
            output_aedb_path=output_aedb_path,
            remove_single_pin_components=remove_single_pin_components,
            use_pyaedt_extent_computing=use_pyaedt_extent_computing,
            extent_defeature=extent_defeature,
            keep_lines_as_path=keep_lines_as_path,
        )

    @pyaedt_function_handler()
    def get_conformal_polygon_from_netlist(self, netlist=None):
        """Return an EDB conformal polygon based on a netlist.

        Parameters
        ----------
        netlist : List of net names.
            list[str]

        Returns
        -------
        :class:`Edb.Cell.Primitive.Polygon`
            Edb polygon object.

        """
        temp_edb_path = self.edbpath[:-5] + "_temp_aedb.aedb"
        shutil.copytree(self.edbpath, temp_edb_path)
        temp_edb = Edb(temp_edb_path)
        for via in list(temp_edb.padstacks.instances.values()):
            via.pin.Delete()
        if netlist:
            nets = [net.net_obj for net in temp_edb.layout.nets if net.name in netlist]
            _poly = temp_edb.layout.expanded_extent(
                nets, self.edb_api.geometry.extent_type.Conforming, 0.0, True, True, 1
            )
        else:
            nets = [net.api_object for net in temp_edb.layout.nets if "gnd" in net.name.lower()]
            _poly = temp_edb.layout.expanded_extent(
                nets, self.edb_api.geometry.extent_type.Conforming, 0.0, True, True, 1
            )
            temp_edb.close_edb()
        if _poly:
            return _poly
        else:
            return False

    @pyaedt_function_handler()
    def number_with_units(self, value, units=None):
        """Convert a number to a string with units. If value is a string, it's returned as is.

        Parameters
        ----------
        value : float, int, str
            Input number or string.
        units : optional
            Units for formatting. The default is ``None``, which uses ``"meter"``.

        Returns
        -------
        str
           String concatenating the value and unit.

        """
        if units is None:
            units = "meter"
        if isinstance(value, str):
            return value
        else:
            return "{0}{1}".format(value, units)

    @pyaedt_function_handler()
    def arg_with_dim(self, Value, sUnits):
        """Convert a number to a string with units. If value is a string, it's returned as is.

        .. deprecated:: 0.6.56
           Use :func:`number_with_units` property instead.

        Parameters
        ----------
        Value : float, int, str
            Input  number or string.
        sUnits : optional
            Units for formatting. The default is ``None``, which uses ``"meter"``.

        Returns
        -------
        str
           String concatenating the value and unit.

        """
        warnings.warn("Use :func:`number_with_units` instead.", DeprecationWarning)
        return self.number_with_units(Value, sUnits)

    def _decompose_variable_value(self, value, unit_system=None):
        val, units = decompose_variable_value(value)
        if units and unit_system and units in AEDT_UNITS[unit_system]:
            return AEDT_UNITS[unit_system][units] * val
        else:
            return val

    @pyaedt_function_handler()
    def _create_cutout_on_point_list(
        self,
        point_list,
        units="mm",
        output_aedb_path=None,
        open_cutout_at_end=True,
        nets_to_include=None,
        include_partial_instances=False,
        keep_voids=True,
    ):
        if point_list[0] != point_list[-1]:
            point_list.append(point_list[0])
        point_list = [[self.number_with_units(i[0], units), self.number_with_units(i[1], units)] for i in point_list]
        plane = self.modeler.Shape("polygon", points=point_list)
        polygonData = self.modeler.shape_to_polygon_data(plane)
        _ref_nets = []
        if nets_to_include:
            self.logger.info("Creating cutout on {} nets.".format(len(nets_to_include)))
        else:
            self.logger.info("Creating cutout on all nets.")  # pragma: no cover

        # Check Padstack Instances overlapping the cutout
        pinstance_to_add = []
        if include_partial_instances:
            if nets_to_include:
                pinst = [i for i in list(self.padstacks.instances.values()) if i.net_name in nets_to_include]
            else:
                pinst = [i for i in list(self.padstacks.instances.values())]
            for p in pinst:
                if p.in_polygon(polygonData):
                    pinstance_to_add.append(p)
        # validate references in layout
        for _ref in self.nets.nets:
            if nets_to_include:
                if _ref in nets_to_include:
                    _ref_nets.append(self.nets.nets[_ref].net_object)
            else:
                _ref_nets.append(self.nets.nets[_ref].net_object)  # pragma: no cover
        if keep_voids:
            voids = [p for p in self.modeler.circles if p.is_void]
            voids2 = [p for p in self.modeler.polygons if p.is_void]
            voids.extend(voids2)
        else:
            voids = []
        voids_to_add = []
        for circle in voids:
            if polygonData.GetIntersectionType(circle.primitive_object.GetPolygonData()) >= 3:
                voids_to_add.append(circle)

        _netsClip = convert_py_list_to_net_list(_ref_nets)
        # net_signals = convert_py_list_to_net_list([], type(_ref_nets[0]))

        # Create new cutout cell/design
        _cutout = self.active_cell.CutOut(_netsClip, _netsClip, polygonData)
        layout = _cutout.GetLayout()
        cutout_obj_coll = list(layout.PadstackInstances)
        ids = []
        for lobj in cutout_obj_coll:
            ids.append(lobj.GetId())

        if include_partial_instances:
            p_missing = [i for i in pinstance_to_add if i.id not in ids]
            self.logger.info("Added {} padstack instances after cutout".format(len(p_missing)))
            for p in p_missing:
                position = self.edb_api.geometry.point_data(
                    self.edb_value(p.position[0]), self.edb_value(p.position[1])
                )
                net = self.nets.find_or_create_net(p.net_name)
                rotation = self.edb_value(p.rotation)
                sign_layers = list(self.stackup.signal_layers.keys())
                if not p.start_layer:  # pragma: no cover
                    fromlayer = self.stackup.signal_layers[sign_layers[0]]._edb_layer
                else:
                    fromlayer = self.stackup.signal_layers[p.start_layer]._edb_layer

                if not p.stop_layer:  # pragma: no cover
                    tolayer = self.stackup.signal_layers[sign_layers[-1]]._edb_layer
                else:
                    tolayer = self.stackup.signal_layers[p.stop_layer]._edb_layer
                padstack = None
                for pad in list(self.padstacks.definitions.keys()):
                    if pad == p.padstack_definition:
                        padstack = self.padstacks.definitions[pad].edb_padstack
                        padstack_instance = self.edb_api.cell.primitive.padstack_instance.create(
                            _cutout.GetLayout(),
                            net,
                            p.name,
                            padstack,
                            position,
                            rotation,
                            fromlayer,
                            tolayer,
                            None,
                            None,
                        )
                        padstack_instance.SetIsLayoutPin(p.is_pin)
                        break

        for void_circle in voids_to_add:
            if void_circle.type == "Circle":
                if is_ironpython:  # pragma: no cover
                    res, center_x, center_y, radius = void_circle.primitive_object.GetParameters()
                else:
                    res, center_x, center_y, radius = void_circle.primitive_object.GetParameters(0.0, 0.0, 0.0)
                cloned_circle = self.edb_api.cell.primitive.circle.create(
                    layout,
                    void_circle.layer_name,
                    void_circle.net,
                    self.edb_value(center_x),
                    self.edb_value(center_y),
                    self.edb_value(radius),
                )
                cloned_circle.SetIsNegative(True)
            elif void_circle.type == "Polygon":
                cloned_polygon = self.edb_api.cell.primitive.polygon.create(
                    layout, void_circle.layer_name, void_circle.net, void_circle.primitive_object.GetPolygonData()
                )
                cloned_polygon.SetIsNegative(True)
        layers = [i for i in list(self.stackup.signal_layers.keys())]
        for layer in layers:
            layer_primitves = self.modeler.get_primitives(layer_name=layer)
            if len(layer_primitves) == 0:
                self.modeler.create_polygon(plane, layer, net_name="DUMMY")
        self.logger.info("Cutout %s created correctly", _cutout.GetName())
        id = 1
        for _setup in self.active_cell.SimulationSetups:
            # Empty string '' if coming from setup copy and don't set explicitly.
            _setup_name = _setup.GetName()
            if "GetSimSetupInfo" in dir(_setup):
                # setup is an Ansys.Ansoft.Edb.Utility.HFSSSimulationSetup object
                _hfssSimSetupInfo = _setup.GetSimSetupInfo()
                _hfssSimSetupInfo.Name = "HFSS Setup " + str(id)  # Set name of analysis setup
                # Write the simulation setup info into the cell/design setup
                _setup.SetSimSetupInfo(_hfssSimSetupInfo)
                _cutout.AddSimulationSetup(_setup)  # Add simulation setup to the cutout design
                id += 1
            else:
                _cutout.AddSimulationSetup(_setup)  # Add simulation setup to the cutout design

        _dbCells = [_cutout]
        if output_aedb_path:
            db2 = self.create(output_aedb_path)
            if not db2.Save():
                self.logger.error("Failed to create new Edb. Check if the path already exists and remove it.")
                return False
            _dbCells = convert_py_list_to_net_list(_dbCells)
            cell_copied = db2.CopyCells(_dbCells)  # Copies cutout cell/design to db2 project
            cell = list(cell_copied)[0]
            cell.SetName(os.path.basename(output_aedb_path[:-5]))
            db2.Save()
            for c in list(self.active_db.TopCircuitCells):
                if c.GetName() == _cutout.GetName():
                    c.Delete()
            if open_cutout_at_end:  # pragma: no cover
                _success = db2.Save()
                self._db = db2
                self.edbpath = output_aedb_path
                self._active_cell = cell
                self.edbpath = self.directory
                self._init_objects()
            else:
                db2.Close()
                source = os.path.join(output_aedb_path, "edb.def.tmp")
                target = os.path.join(output_aedb_path, "edb.def")
                self._wait_for_file_release(file_to_release=output_aedb_path)
                if os.path.exists(source) and not os.path.exists(target):
                    try:
                        shutil.copy(source, target)
                        self.logger.warning("aedb def file manually created.")
                    except:
                        pass
        return True

    @pyaedt_function_handler()
    def create_cutout_on_point_list(
        self,
        point_list,
        units="mm",
        output_aedb_path=None,
        open_cutout_at_end=True,
        nets_to_include=None,
        include_partial_instances=False,
        keep_voids=True,
    ):
        """Create a cutout on a specified shape and save it to a new AEDB file.

        .. deprecated:: 0.6.58
           Use new method :func:`cutout` instead.

        Parameters
        ----------
        point_list : list
            Points list defining the cutout shape.
        units : str
            Units of the point list. The default is ``"mm"``.
        output_aedb_path : str, optional
            Full path and name for the new AEDB file.
            The aedb folder shall not exist otherwise the method will return ``False``.
        open_cutout_at_end : bool, optional
            Whether to open the cutout at the end. The default is ``True``.
        nets_to_include : list, optional
            List of nets to include in the cutout. The default is ``None``, in
            which case all nets are included.
        include_partial_instances : bool, optional
            Whether to include padstack instances that have bounding boxes intersecting with point list polygons.
            This operation may slow down the cutout export.
        keep_voids : bool
            Boolean used for keep or not the voids intersecting the polygon used for clipping the layout.
            Default value is ``True``, ``False`` will remove the voids.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        warnings.warn("Use new method `cutout` instead.", DeprecationWarning)
        return self._create_cutout_on_point_list(
            point_list=point_list,
            units=units,
            output_aedb_path=output_aedb_path,
            open_cutout_at_end=open_cutout_at_end,
            nets_to_include=nets_to_include,
            include_partial_instances=include_partial_instances,
            keep_voids=keep_voids,
        )

    @pyaedt_function_handler()
    def write_export3d_option_config_file(self, path_to_output, config_dictionaries=None):
        """Write the options for a 3D export to a configuration file.

        Parameters
        ----------
        path_to_output : str
            Full path to the configuration file to save 3D export options to.

        config_dictionaries : dict, optional
            Configuration dictionaries. The default is ``None``.

        """
        option_config = {
            "UNITE_NETS": 1,
            "ASSIGN_SOLDER_BALLS_AS_SOURCES": 0,
            "Q3D_MERGE_SOURCES": 0,
            "Q3D_MERGE_SINKS": 0,
            "CREATE_PORTS_FOR_PWR_GND_NETS": 0,
            "PORTS_FOR_PWR_GND_NETS": 0,
            "GENERATE_TERMINALS": 0,
            "SOLVE_CAPACITANCE": 0,
            "SOLVE_DC_RESISTANCE": 0,
            "SOLVE_DC_INDUCTANCE_RESISTANCE": 1,
            "SOLVE_AC_INDUCTANCE_RESISTANCE": 0,
            "CreateSources": 0,
            "CreateSinks": 0,
            "LAUNCH_Q3D": 0,
            "LAUNCH_HFSS": 0,
        }
        if config_dictionaries:
            for el, val in config_dictionaries.items():
                option_config[el] = val
        with open(os.path.join(path_to_output, "options.config"), "w") as f:
            for el, val in option_config.items():
                f.write(el + " " + str(val) + "\n")
        return os.path.join(path_to_output, "options.config")

    @pyaedt_function_handler()
    def export_hfss(self, path_to_output, net_list=None, num_cores=None, aedt_file_name=None, hidden=False):
        """Export EDB to HFSS.

        Parameters
        ----------
        path_to_output : str
            Full path and name for saving the AEDT file.
        net_list : list, optional
            List of nets to export if only certain ones are to be exported.
            The default is ``None``, in which case all nets are eported.
        num_cores : int, optional
            Number of cores to use for the export. The default is ``None``.
        aedt_file_name : str, optional
            Name of the AEDT output file without the ``.aedt`` extension. The default is ``None``,
            in which case the default name is used.
        hidden : bool, optional
            Open Siwave in embedding mode. User will only see Siwave Icon but UI will be hidden.

        Returns
        -------
        str
            Full path to the AEDT file.

        Examples
        --------
        >>> from pyaedt import Edb

        >>> edb = Edb(edbpath=r"C:\temp\myproject.aedb", edbversion="2021.2")

        >>> options_config = {'UNITE_NETS' : 1, 'LAUNCH_Q3D' : 0}
        >>> edb.write_export3d_option_config_file(r"C:\temp", options_config)
        >>> edb.export_hfss(r"C:\temp")
        "C:\\temp\\hfss_siwave.aedt"

        """
        siwave_s = SiwaveSolve(self.edbpath, aedt_installer_path=self.base_path)
        return siwave_s.export_3d_cad("HFSS", path_to_output, net_list, num_cores, aedt_file_name, hidden=hidden)

    @pyaedt_function_handler()
    def export_q3d(self, path_to_output, net_list=None, num_cores=None, aedt_file_name=None, hidden=False):
        """Export EDB to Q3D.

        Parameters
        ----------
        path_to_output : str
            Full path and name for saving the AEDT file.
        net_list : list, optional
            List of nets to export only if certain ones are to be exported.
            The default is ``None``, in which case all nets are eported.
        num_cores : int, optional
            Number of cores to use for the export. The default is ``None``.
        aedt_file_name : str, optional
            Name of the AEDT output file without the ``.aedt`` extension. The default is ``None``,
            in which case the default name is used.
        hidden : bool, optional
            Open Siwave in embedding mode. User will only see Siwave Icon but UI will be hidden.

        Returns
        -------
        str
            Full path to the AEDT file.

        Examples
        --------
        >>> from pyaedt import Edb

        >>> edb = Edb(edbpath=r"C:\temp\myproject.aedb", edbversion="2021.2")

        >>> options_config = {'UNITE_NETS' : 1, 'LAUNCH_Q3D' : 0}
        >>> edb.write_export3d_option_config_file(r"C:\temp", options_config)
        >>> edb.export_q3d(r"C:\temp")
        "C:\\temp\\q3d_siwave.aedt"

        """
        siwave_s = SiwaveSolve(self.edbpath, aedt_installer_path=self.base_path)
        return siwave_s.export_3d_cad(
            "Q3D", path_to_output, net_list, num_cores=num_cores, aedt_file_name=aedt_file_name, hidden=hidden
        )

    @pyaedt_function_handler()
    def export_maxwell(self, path_to_output, net_list=None, num_cores=None, aedt_file_name=None, hidden=False):
        """Export EDB to Maxwell 3D.

        Parameters
        ----------
        path_to_output : str
            Full path and name for saving the AEDT file.
        net_list : list, optional
            List of nets to export only if certain ones are to be
            exported. The default is ``None``, in which case all nets are exported.
        num_cores : int, optional
            Number of cores to use for the export. The default is ``None.``
        aedt_file_name : str, optional
            Name of the AEDT output file without the ``.aedt`` extension. The default is ``None``,
            in which case the default name is used.
        hidden : bool, optional
            Open Siwave in embedding mode. User will only see Siwave Icon but UI will be hidden.

        Returns
        -------
        str
            Full path to the AEDT file.

        Examples
        --------
        >>> from pyaedt import Edb

        >>> edb = Edb(edbpath=r"C:\temp\myproject.aedb", edbversion="2021.2")

        >>> options_config = {'UNITE_NETS' : 1, 'LAUNCH_Q3D' : 0}
        >>> edb.write_export3d_option_config_file(r"C:\temp", options_config)
        >>> edb.export_maxwell(r"C:\temp")
        "C:\\temp\\maxwell_siwave.aedt"

        """
        siwave_s = SiwaveSolve(self.edbpath, aedt_installer_path=self.base_path)
        return siwave_s.export_3d_cad(
            "Maxwell",
            path_to_output,
            net_list,
            num_cores=num_cores,
            aedt_file_name=aedt_file_name,
            hidden=hidden,
        )

    @pyaedt_function_handler()
    def solve_siwave(self):
        """Close EDB and solve it with Siwave.

        Returns
        -------
        str
            Siwave project path.
        """
        process = SiwaveSolve(self.edbpath, aedt_version=self.edbversion)
        try:
            self.close()
        except:
            pass
        process.solve()
        return self.edbpath[:-5] + ".siw"

    @pyaedt_function_handler()
    def export_siwave_dc_results(
        self,
        siwave_project,
        solution_name,
        output_folder=None,
        html_report=True,
        vias=True,
        voltage_probes=True,
        current_sources=True,
        voltage_sources=True,
        power_tree=True,
        loop_res=True,
    ):
        """Close EDB and solve it with Siwave.

        Parameters
        ----------
        siwave_project : str
            Siwave full project name.
        solution_name : str
            Siwave DC Analysis name.
        output_folder : str, optional
            Ouptu folder where files will be downloaded.
        html_report : bool, optional
            Either if generate or not html report. Default is `True`.
        vias : bool, optional
            Either if generate or not vias report. Default is `True`.
        voltage_probes : bool, optional
            Either if generate or not voltage probe report. Default is `True`.
        current_sources : bool, optional
            Either if generate or not current source report. Default is `True`.
        voltage_sources : bool, optional
            Either if generate or not voltage source report. Default is `True`.
        power_tree : bool, optional
            Either if generate or not power tree image. Default is `True`.
        loop_res : bool, optional
            Either if generate or not loop resistance report. Default is `True`.

        Returns
        -------
        list
            List of files generated.
        """
        process = SiwaveSolve(self.edbpath, aedt_version=self.edbversion)
        try:
            self.close()
        except:
            pass
        return process.export_dc_report(
            siwave_project,
            solution_name,
            output_folder,
            html_report,
            vias,
            voltage_probes,
            current_sources,
            voltage_sources,
            power_tree,
            loop_res,
            hidden=True,
        )

    @pyaedt_function_handler()
    def variable_exists(self, variable_name):
        """Check if a variable exists or not.

        Returns
        -------
        tuple of bool and VaribleServer
            It returns a booleand to check if the variable exists and the variable
            server that should contain the variable.
        """
        if "$" in variable_name:
            if variable_name.index("$") == 0:
                var_server = self.active_db.GetVariableServer()

            else:
                var_server = self.active_cell.GetVariableServer()

        else:
            var_server = self.active_cell.GetVariableServer()

        variables = var_server.GetAllVariableNames()
        if variable_name in list(variables):
            return True, var_server
        return False, var_server

    @pyaedt_function_handler()
    def get_variable(self, variable_name):
        """Return Variable Value if variable exists.

        Parameters
        ----------
        variable_name

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.edbvalue.EdbValue`
        """
        var_server = self.variable_exists(variable_name)
        if var_server[0]:
            tuple_value = var_server[1].GetVariableValue(variable_name)
            return EdbValue(tuple_value[1])
        self.logger.info("Variable %s doesn't exists.", variable_name)
        return None

    @pyaedt_function_handler()
    def add_project_variable(self, variable_name, variable_value):
        """Add a variable to edb database (project). The variable will have the prefix `$`.

        ..note::
            User can use also the setitem to create or assign a variable. See example below.

        Parameters
        ----------
        variable_name : str
            Name of the variable. Name can be provided without ``$`` prefix.
        variable_value : str, float
            Value of the variable with units.

        Returns
        -------
        tuple
            Tuple containing the ``AddVariable`` result and variable server.

        Examples
        --------
        >>> from pyaedt import Edb
        >>> edb_app = Edb()
        >>> boolean_1, ant_length = edb_app.add_project_variable("my_local_variable", "1cm")
        >>> print(edb_app["$my_local_variable"])    #using getitem
        >>> edb_app["$my_local_variable"] = "1cm"   #using setitem

        """
        if not variable_name.startswith("$"):
            variable_name = "${}".format(variable_name)
        return self.add_design_variable(variable_name=variable_name, variable_value=variable_value)

    @pyaedt_function_handler()
    def add_design_variable(self, variable_name, variable_value, is_parameter=False):
        """Add a variable to edb. The variable can be a design one or a project variable (using ``$`` prefix).

        ..note::
            User can use also the setitem to create or assign a variable. See example below.

        Parameters
        ----------
        variable_name : str
            Name of the variable. To added the variable as a project variable, the name
            must begin with ``$``.
        variable_value : str, float
            Value of the variable with units.
        is_parameter : bool, optional
            Whether to add the variable as a local variable. The default is ``False``.
            When ``True``, the variable is added as a parameter default.

        Returns
        -------
        tuple
            Tuple containing the ``AddVariable`` result and variable server.

        Examples
        --------
        >>> from pyaedt import Edb
        >>> edb_app = Edb()
        >>> boolean_1, ant_length = edb_app.add_design_variable("my_local_variable", "1cm")
        >>> print(edb_app["my_local_variable"])    #using getitem
        >>> edb_app["my_local_variable"] = "1cm"   #using setitem
        >>> boolean_2, para_length = edb_app.change_design_variable_value("my_parameter", "1m", is_parameter=True
        >>> boolean_3, project_length = edb_app.change_design_variable_value("$my_project_variable", "1m")


        """
        var_server = self.variable_exists(variable_name)
        if not var_server[0]:
            var_server[1].AddVariable(variable_name, self.edb_value(variable_value), is_parameter)
            return True, var_server[1]
        self.logger.error("Variable %s already exists.", variable_name)
        return False, var_server[1]

    @pyaedt_function_handler()
    def change_design_variable_value(self, variable_name, variable_value):
        """Change a variable value.

        ..note::
            User can use also the getitem to read the variable value. See example below.

        Parameters
        ----------
        variable_name : str
            Name of the variable.
        variable_value : str, float
            Value of the variable with units.

        Returns
        -------
        tuple
            Tuple containing the ``SetVariableValue`` result and variable server.

        Examples
        --------
        >>> from pyaedt import Edb
        >>> edb_app = Edb()
        >>> boolean, ant_length = edb_app.add_design_variable("ant_length", "1cm")
        >>> boolean, ant_length = edb_app.change_design_variable_value("ant_length", "1m")
        >>> print(edb_app["ant_length"])    #using getitem
        """
        var_server = self.variable_exists(variable_name)
        if var_server[0]:
            var_server[1].SetVariableValue(variable_name, self.edb_value(variable_value))
            return True, var_server[1]
        self.logger.error("Variable %s does not exists.", variable_name)
        return False, var_server[1]

    @pyaedt_function_handler()
    def get_bounding_box(self):
        """Get the layout bounding box.

        Returns
        -------
        list of list of double
            Bounding box as a [lower-left X, lower-left Y], [upper-right X, upper-right Y]) pair in meters.
        """
        bbox = self.edbutils.HfssUtilities.GetBBox(self.active_layout)
        return [[bbox.Item1.X.ToDouble(), bbox.Item1.Y.ToDouble()], [bbox.Item2.X.ToDouble(), bbox.Item2.Y.ToDouble()]]

    @pyaedt_function_handler()
    def build_simulation_project(self, simulation_setup):
        # type: (SimulationConfiguration) -> bool
        """Build a ready-to-solve simulation project.

        Parameters
        ----------
        simulation_setup : :class:`pyaedt.edb_core.edb_data.simulation_configuration.SimulationConfiguration` object.
            SimulationConfiguration object that can be instantiated or directly loaded with a
            configuration file.

        Returns
        -------
        bool
            ``True`` when successful, False when ``Failed``.

        Examples
        --------
        >>> from pyaedt import Edb
        >>> from pyaedt.edb_core.edb_data.simulation_configuration import SimulationConfiguration
        >>> config_file = path_configuration_file
        >>> source_file = path_to_edb_folder
        >>> edb = Edb(source_file)
        >>> sim_setup = SimulationConfiguration(config_file)
        >>> edb.build_simulation_project(sim_setup)
        >>> edb.save_edb()
        >>> edb.close_edb()
        """
        self.logger.info("Building simulation project.")
        legacy_name = self.edbpath
        if simulation_setup.output_aedb:
            self.save_edb_as(simulation_setup.output_aedb)
        try:
            if simulation_setup.signal_layer_etching_instances:
                for layer in simulation_setup.signal_layer_etching_instances:
                    if layer in self.stackup.layers:
                        idx = simulation_setup.signal_layer_etching_instances.index(layer)
                        if len(simulation_setup.etching_factor_instances) > idx:
                            self.stackup[layer].etch_factor = float(simulation_setup.etching_factor_instances[idx])

            if not simulation_setup.signal_nets and simulation_setup.components:
                nets_to_include = []
                pnets = list(self.nets.power_nets.keys())[:]
                for el in simulation_setup.components:
                    nets_to_include.append([i for i in self.components[el].nets if i not in pnets])
                simulation_setup.signal_nets = [
                    i
                    for i in list(set.intersection(*map(set, nets_to_include)))
                    if i not in simulation_setup.power_nets and i != ""
                ]
            self.nets.classify_nets(simulation_setup.power_nets, simulation_setup.signal_nets)
            if not simulation_setup.power_nets or not simulation_setup.signal_nets:
                self.logger.info("Disabling cutout as no signals or power nets have been defined.")
                simulation_setup.do_cutout_subdesign = False
            if simulation_setup.do_cutout_subdesign:
                self.logger.info("Cutting out using method: {0}".format(simulation_setup.cutout_subdesign_type))
                if simulation_setup.use_default_cutout:
                    old_cell_name = self.active_cell.GetName()
                    if self.cutout(
                        signal_list=simulation_setup.signal_nets,
                        reference_list=simulation_setup.power_nets,
                        expansion_size=simulation_setup.cutout_subdesign_expansion,
                        use_round_corner=simulation_setup.cutout_subdesign_round_corner,
                        extent_type=simulation_setup.cutout_subdesign_type,
                        use_pyaedt_cutout=False,
                        use_pyaedt_extent_computing=False,
                    ):
                        self.logger.info("Cutout processed.")
                        old_cell = self.active_cell.FindByName(
                            self.db, self.edb_api.cell.CellType.CircuitCell, old_cell_name
                        )
                        if old_cell:
                            old_cell.Delete()
                    else:  # pragma: no cover
                        self.logger.error("Cutout failed.")
                else:
                    self.logger.info("Cutting out using method: {0}".format(simulation_setup.cutout_subdesign_type))
                    self.cutout(
                        signal_list=simulation_setup.signal_nets,
                        reference_list=simulation_setup.power_nets,
                        expansion_size=simulation_setup.cutout_subdesign_expansion,
                        use_round_corner=simulation_setup.cutout_subdesign_round_corner,
                        extent_type=simulation_setup.cutout_subdesign_type,
                        use_pyaedt_cutout=True,
                        use_pyaedt_extent_computing=True,
                        remove_single_pin_components=True,
                    )
                    self.logger.info("Cutout processed.")
            else:
                if simulation_setup.include_only_selected_nets:
                    included_nets = simulation_setup.signal_nets + simulation_setup.power_nets
                    nets_to_remove = [
                        net.name for net in list(self.nets.nets.values()) if net.name not in included_nets
                    ]
                    self.nets.delete(nets_to_remove)
            self.logger.info("Deleting existing ports.")
            map(lambda port: port.Delete(), self.layout.terminals)
            map(lambda pg: pg.Delete(), self.layout.pin_groups)
            if simulation_setup.solver_type == SolverType.Hfss3dLayout:
                if simulation_setup.generate_excitations:
                    self.logger.info("Creating HFSS ports for signal nets.")
                    source_type = SourceType.CoaxPort
                    if not simulation_setup.generate_solder_balls:
                        source_type = SourceType.CircPort
                    for cmp in simulation_setup.components:
                        self.components.create_port_on_component(
                            cmp,
                            net_list=simulation_setup.signal_nets,
                            do_pingroup=False,
                            reference_net=simulation_setup.power_nets,
                            port_type=source_type,
                        )
                    if simulation_setup.generate_solder_balls and not self.hfss.set_coax_port_attributes(
                        simulation_setup
                    ):  # pragma: no cover
                        self.logger.error("Failed to configure coaxial port attributes.")
                    self.logger.info("Number of ports: {}".format(self.hfss.get_ports_number()))
                    self.logger.info("Configure HFSS extents.")
                    if (
                        simulation_setup.generate_solder_balls and simulation_setup.trim_reference_size
                    ):  # pragma: no cover
                        self.logger.info(
                            "Trimming the reference plane for coaxial ports: {0}".format(
                                bool(simulation_setup.trim_reference_size)
                            )
                        )
                        self.hfss.trim_component_reference_size(simulation_setup)  # pragma: no cover
                self.hfss.configure_hfss_extents(simulation_setup)
                if not self.hfss.configure_hfss_analysis_setup(simulation_setup):
                    self.logger.error("Failed to configure HFSS simulation setup.")
            if simulation_setup.solver_type == SolverType.SiwaveSYZ:
                if simulation_setup.generate_excitations:
                    for cmp in simulation_setup.components:
                        self.components.create_port_on_component(
                            cmp,
                            net_list=simulation_setup.signal_nets,
                            do_pingroup=simulation_setup.do_pingroup,
                            reference_net=simulation_setup.power_nets,
                            port_type=SourceType.CircPort,
                        )
                self.logger.info("Configuring analysis setup.")
                if not self.siwave.configure_siw_analysis_setup(simulation_setup):  # pragma: no cover
                    self.logger.error("Failed to configure Siwave simulation setup.")

            if simulation_setup.solver_type == SolverType.SiwaveDC:
                if simulation_setup.generate_excitations:
                    self.components.create_source_on_component(simulation_setup.sources)
                if not self.siwave.configure_siw_analysis_setup(simulation_setup):  # pragma: no cover
                    self.logger.error("Failed to configure Siwave simulation setup.")
            self.padstacks.check_and_fix_via_plating()
            self.save_edb()
            if not simulation_setup.open_edb_after_build and simulation_setup.output_aedb:
                self.close_edb()
                self.edbpath = legacy_name
                self.open_edb()
            return True
        except:  # pragma: no cover
            return False

    @pyaedt_function_handler()
    def get_statistics(self, compute_area=False):
        """Get the EDBStatistics object.

        Returns
        -------
        EDBStatistics object from the loaded layout.
        """
        return self.modeler.get_layout_statistics(evaluate_area=compute_area, net_list=None)

    @pyaedt_function_handler()
    def are_port_reference_terminals_connected(self, common_reference=None):
        """Check if all terminal references in design are connected.
        If the reference nets are different, there is no hope for the terminal references to be connected.
        After we have identified a common reference net we need to loop the terminals again to get
        the correct reference terminals that uses that net.

        Parameters
        ----------
        common_reference : str, optional
            Common Reference name. If ``None`` it will be searched in ports terminal.
            If a string is passed then all excitations must have such reference assigned.

        Returns
        -------
        bool
            Either if the ports are connected to reference_name or not.

        Examples
        --------
        >>>edb = Edb()
        >>> edb.hfss.create_edge_port_vertical(prim_1_id, ["-66mm", "-4mm"], "port_ver")
        >>> edb.hfss.create_edge_port_horizontal(
        >>> ... prim_1_id, ["-60mm", "-4mm"], prim_2_id, ["-59mm", "-4mm"], "port_hori", 30, "Lower"
        >>> ... )
        >>> edb.hfss.create_wave_port(traces[0].id, trace_paths[0][0], "wave_port")
        >>> edb.cutout(["Net1"])
        >>> assert edb.are_port_reference_terminals_connected()
        """
        all_sources = [i for i in self.excitations.values() if not isinstance(i, (WavePort, GapPort, BundleWavePort))]
        all_sources.extend([i for i in self.sources.values()])
        if not all_sources:
            return True
        self.logger.reset_timer()
        if not common_reference:
            common_reference = list(set([i.reference_net_name for i in all_sources if i.reference_net_name]))
            if len(common_reference) > 1:
                self.logger.error("More than 1 reference found.")
                return False
            if not common_reference:
                self.logger.error("No Reference found.")
                return False

            common_reference = common_reference[0]
        all_sources = [i for i in all_sources if i.net_name != common_reference]

        setList = [
            set(i.reference_object.get_connected_object_id_set())
            for i in all_sources
            if i.reference_object and i.reference_net_name == common_reference
        ]
        if len(setList) != len(all_sources):
            self.logger.error("No Reference found.")
            return False
        cmps = [
            i
            for i in list(self.components.resistors.values())
            if i.numpins == 2 and common_reference in i.nets and self._decompose_variable_value(i.res_value) <= 1
        ]
        cmps.extend(
            [i for i in list(self.components.inductors.values()) if i.numpins == 2 and common_reference in i.nets]
        )

        for cmp in cmps:
            found = False
            ids = [i.GetId() for i in cmp.pinlist]
            for list_obj in setList:
                if len(set(ids).intersection(list_obj)) == 1:
                    for list_obj2 in setList:
                        if list_obj2 != list_obj and len(set(ids).intersection(list_obj)) == 1:
                            if (ids[0] in list_obj and ids[1] in list_obj2) or (
                                ids[1] in list_obj and ids[0] in list_obj2
                            ):
                                setList[setList.index(list_obj)] = list_obj.union(list_obj2)
                                setList[setList.index(list_obj2)] = list_obj.union(list_obj2)
                                found = True
                                break
                    if found:
                        break

        # Get the set intersections for all the ID sets.
        iDintersection = set.intersection(*setList)
        self.logger.info_timer(
            "Terminal reference primitive IDs total intersections = {}\n\n".format(len(iDintersection))
        )

        # If the intersections are non-zero, the terminal references are connected.
        return True if len(iDintersection) > 0 else False

    @pyaedt_function_handler()
    def new_simulation_configuration(self, filename=None):
        # type: (str) -> SimulationConfiguration
        """New SimulationConfiguration Object.

        Parameters
        ----------
        filename : str, optional
            Input config file.

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.simulation_configuration.SimulationConfiguration`
        """
        return SimulationConfiguration(filename, self)

    @property
    def setups(self):
        """Get the dictionary of all EDB HFSS and SIwave setups.

        Returns
        -------
        Dict[str, :class:`pyaedt.edb_core.edb_data.hfss_simulation_setup_data.HfssSimulationSetup`] or
        Dict[str, :class:`pyaedt.edb_core.edb_data.siwave_simulation_setup_data.SiwaveDCSimulationSetup`] or
        Dict[str, :class:`pyaedt.edb_core.edb_data.siwave_simulation_setup_data.SiwaveSYZSimulationSetup`]

        """
        for i in list(self.active_cell.SimulationSetups):
            if i.GetName() not in self._setups:
                if i.GetType() == self.edb_api.utility.utility.SimulationSetupType.kHFSS:
                    self._setups[i.GetName()] = HfssSimulationSetup(self, i.GetName(), i)
                elif i.GetType() == self.edb_api.utility.utility.SimulationSetupType.kSIWave:
                    self._setups[i.GetName()] = SiwaveSYZSimulationSetup(self, i.GetName(), i)
                elif i.GetType() == self.edb_api.utility.utility.SimulationSetupType.kSIWaveDCIR:
                    self._setups[i.GetName()] = SiwaveDCSimulationSetup(self, i.GetName(), i)
        return self._setups

    @property
    def hfss_setups(self):
        """Active HFSS setup in EDB.

        Returns
        -------
        Dict[str, :class:`pyaedt.edb_core.edb_data.hfss_simulation_setup_data.HfssSimulationSetup`]

        """
        return {name: i for name, i in self.setups.items() if i.setup_type == "kHFSS"}

    @property
    def siwave_dc_setups(self):
        """Active Siwave DC IR Setups.

        Returns
        -------
        Dict[str, :class:`pyaedt.edb_core.edb_data.siwave_simulation_setup_data.SiwaveDCSimulationSetup`]
        """
        return {name: i for name, i in self.setups.items() if i.setup_type == "kSIWaveDCIR"}

    @property
    def siwave_ac_setups(self):
        """Active Siwave SYZ setups.

        Returns
        -------
        Dict[str, :class:`pyaedt.edb_core.edb_data.siwave_simulation_setup_data.SiwaveSYZSimulationSetup`]
        """
        return {name: i for name, i in self.setups.items() if i.setup_type == "kSIWave"}

    def create_hfss_setup(self, name=None):
        """Create a setup from a template.

        Parameters
        ----------
        name : str, optional
            Setup name.

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.hfss_simulation_setup_data.HfssSimulationSetup`

        Examples
        --------
        >>> setup1 = edbapp.create_hfss_setup("setup1")
        >>> setup1.hfss_port_settings.max_delta_z0 = 0.5
        """
        if name in self.setups:
            return False
        setup = HfssSimulationSetup(self, name)
        self._setups[name] = setup
        return setup

    @pyaedt_function_handler()
    def create_siwave_syz_setup(self, name=None):
        """Create a setup from a template.

        Parameters
        ----------
        name : str, optional
            Setup name.

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.siwave_simulation_setup_data.SiwaveSYZSimulationSetup`

        Examples
        --------
        >>> setup1 = edbapp.create_siwave_syz_setup("setup1")
        >>> setup1.add_frequency_sweep(frequency_sweep=[
        ...                           ["linear count", "0", "1kHz", 1],
        ...                           ["log scale", "1kHz", "0.1GHz", 10],
        ...                           ["linear scale", "0.1GHz", "10GHz", "0.1GHz"],
        ...                           ])
        """
        if not name:
            name = generate_unique_name("Siwave_SYZ")
        if name in self.setups:
            return False
        setup = SiwaveSYZSimulationSetup(self, name)
        setup.si_slider_postion = 1
        setup.pi_slider_postion = 1
        self._setups[name] = setup
        return setup

    @pyaedt_function_handler()
    def create_siwave_dc_setup(self, name=None):
        """Create a setup from a template.

        Parameters
        ----------
        name : str, optional
            Setup name.

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.siwave_simulation_setup_data.SiwaveSYZSimulationSetup`

        Examples
        --------
        >>> setup1 = edbapp.create_siwave_dc_setup("setup1")
        >>> setup1.mesh_bondwires = True

        """
        if not name:
            name = generate_unique_name("Siwave_DC")
        if name in self.setups:
            return False
        setup = SiwaveDCSimulationSetup(self, name)
        self._setups[name] = setup
        return setup

    @pyaedt_function_handler()
    def calculate_initial_extent(self, expansion_factor):
        """Compute a float representing the larger number between the dielectric thickness or trace width
        multiplied by the nW factor. The trace width search is limited to nets with ports attached.

        Parameters
        ----------
        expansion_factor : float
            Value for the width multiplier (nW factor).

        Returns
        -------
        float
        """
        nets = []
        for port in self.excitations.values():
            nets.append(port.net_name)
        for port in self.sources.values():
            nets.append(port.net_name)
        nets = list(set(nets))
        max_width = 0
        for net in nets:
            for primitive in self.nets[net].primitives:
                if primitive.type == "Path":
                    max_width = max(max_width, primitive.width)

        for layer in list(self.stackup.dielectric_layers.values()):
            max_width = max(max_width, layer.thickness)

        max_width = max_width * expansion_factor
        self.logger.info("The W factor is {}, The initial extent = {:e}".format(expansion_factor, max_width))
        return max_width

    @pyaedt_function_handler()
    def copy_zones(self, working_directory=None):
        """Copy multizone EDB project to one new edb per zone.

        Parameters
        ----------
        working_directory : str
            Directory path where all EDB project are copied, if empty will use the current EDB project.

        Returns
        -------
           dict[str](int, EDB PolygonData)
           Return a dictionary with edb path as key and tuple Zone Id as first item and EDB polygon Data defining
           the region as second item.

        """
        if working_directory:
            if not os.path.isdir(working_directory):
                os.mkdir(working_directory)
            else:
                shutil.rmtree(working_directory)
                os.mkdir(working_directory)
        else:
            working_directory = os.path.dirname(self.edbpath)
        zone_primitives = list(self.layout.zone_primitives)
        zone_ids = list(self.stackup._layer_collection.GetZoneIds())
        edb_zones = {}
        if not self.setups:
            self.siwave.add_siwave_syz_analysis()
            self.save_edb()
        for zone_primitive in zone_primitives:
            edb_zone_path = os.path.join(
                working_directory, "{}_{}".format(zone_primitive.GetId(), os.path.basename(self.edbpath))
            )
            shutil.copytree(self.edbpath, edb_zone_path)
            poly_data = zone_primitive.GetPolygonData()
            if self.version[0] >= 10:
                edb_zones[edb_zone_path] = (zone_primitive.GetZoneId(), poly_data)
            elif len(zone_primitives) == len(zone_ids):
                edb_zones[edb_zone_path] = (zone_ids[0], poly_data)
            else:
                self.logger.info(
                    "Number of zone primitives is not equal to zone number. Zone information will be lost."
                    "Use Ansys 2024 R1 or later."
                )
                edb_zones[edb_zone_path] = (-1, poly_data)
        return edb_zones

    @pyaedt_function_handler()
    def cutout_multizone_layout(self, zone_dict, common_reference_net=None):
        """Create a multizone project cutout.

        Parameters
        ----------
        zone_dict : dict[str](EDB PolygonData)
            Dictionary with EDB path as key and EDB PolygonData as value defining the zone region.
            This dictionary is returned from the command copy_zones():
            >>> edb = Edb(edb_file)
            >>> zone_dict = edb.copy_zones(r"C:\Temp\test")

        common_reference_net : str
            the common reference net name. This net name must be provided to provide a valid project.

        Returns
        -------
        dict[str][str] , list of str
        first dictionary defined_ports with edb name as key and existing port name list as value. Those ports are the
        ones defined before processing the multizone clipping.
        second is the list of connected port.

        """
        terminals = {}
        defined_ports = {}
        project_connexions = None
        for edb_path, zone_info in zone_dict.items():
            edb = Edb(edbversion=self.edbversion, edbpath=edb_path)
            edb.cutout(use_pyaedt_cutout=True, custom_extent=zone_info[1], open_cutout_at_end=True)
            if not zone_info[0] == -1:
                layers_to_remove = [
                    lay.name for lay in list(edb.stackup.layers.values()) if not lay._edb_layer.IsInZone(zone_info[0])
                ]
                for layer in layers_to_remove:
                    edb.stackup.remove_layer(layer)
            edb.stackup.stackup_mode = "Laminate"
            edb.cutout(use_pyaedt_cutout=True, custom_extent=zone_info[1], open_cutout_at_end=True)
            edb.active_cell.SetName(os.path.splitext(os.path.basename(edb_path))[0])
            if common_reference_net:
                signal_nets = list(self.nets.signal.keys())
                defined_ports[os.path.splitext(os.path.basename(edb_path))[0]] = list(edb.excitations.keys())
                edb_terminals_info = edb.hfss.create_vertical_circuit_port_on_clipped_traces(
                    nets=signal_nets, reference_net=common_reference_net, user_defined_extent=zone_info[1]
                )
                if edb_terminals_info:
                    terminals[os.path.splitext(os.path.basename(edb_path))[0]] = edb_terminals_info
                project_connexions = self._get_connected_ports_from_multizone_cutout(terminals)
            edb.save_edb()
            edb.close_edb()
        return defined_ports, project_connexions

    @pyaedt_function_handler()
    def _get_connected_ports_from_multizone_cutout(self, terminal_info_dict):
        """Return connected port list from clipped multizone layout.

        Parameters
        ----------
            terminal_info_dict : dict[str][str]
                dictionary terminals with edb name as key and created ports name on clipped signal nets.
                Dictionary is generated by the command cutout_multizone_layout:
                >>> edb = Edb(edb_file)
                >>> edb_zones = edb.copy_zones(r"C:\Temp\test")
                >>> defined_ports, terminals_info = edb.cutout_multizone_layout(edb_zones, common_reference_net)
                >>> project_connexions = get_connected_ports(terminals_info)

        Returns
        -------
        list[str]
            list of connected ports.
        """
        if terminal_info_dict:
            tolerance = 1e-8
            connected_ports_list = []
            project_list = list(terminal_info_dict.keys())
            project_combinations = list(combinations(range(0, len(project_list)), 2))
            for comb in project_combinations:
                terminal_set1 = terminal_info_dict[project_list[comb[0]]]
                terminal_set2 = terminal_info_dict[project_list[comb[1]]]
                project1_nets = [t[0] for t in terminal_set1]
                project2_nets = [t[0] for t in terminal_set2]
                net_with_connected_ports = list(set(project1_nets).intersection(project2_nets))
                if net_with_connected_ports:
                    for net_name in net_with_connected_ports:
                        project1_port_info = [term_info for term_info in terminal_set1 if term_info[0] == net_name]
                        project2_port_info = [term_info for term_info in terminal_set2 if term_info[0] == net_name]
                        port_list = [p[3] for p in project1_port_info] + [p[3] for p in project2_port_info]
                        port_combinations = list(combinations(port_list, 2))
                        for port_combination in port_combinations:
                            if not port_combination[0] == port_combination[1]:
                                port1 = [port for port in terminal_set1 if port[3] == port_combination[0]]
                                if not port1:
                                    port1 = [port for port in terminal_set2 if port[3] == port_combination[0]]
                                port2 = [port for port in terminal_set2 if port[3] == port_combination[1]]
                                if not port2:
                                    port2 = [port for port in terminal_set1 if port[3] == port_combination[1]]
                                port1 = port1[0]
                                port2 = port2[0]
                                if not port1[3] == port2[3]:
                                    port_distance = GeometryOperators.points_distance(port1[1:3], port2[1:3])
                                    if port_distance < tolerance:
                                        port1_connexion = None
                                        port2_connexion = None
                                        for project_path, port_info in terminal_info_dict.items():
                                            port1_map = [port for port in port_info if port[3] == port1[3]]
                                            if port1_map:
                                                port1_connexion = (project_path, port1[3])
                                            port2_map = [port for port in port_info if port[3] == port2[3]]
                                            if port2_map:
                                                port2_connexion = (project_path, port2[3])
                                        if port1_connexion and port2_connexion:
                                            if (
                                                not port1_connexion[0] == port2_connexion[0]
                                                or not port1_connexion[1] == port2_connexion[1]
                                            ):
                                                connected_ports_list.append((port1_connexion, port2_connexion))
            return connected_ports_list
