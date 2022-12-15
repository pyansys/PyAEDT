"""This module contains the ``Edb`` class.

This module is implicitily loaded in HFSS 3D Layout when launched.

"""
import gc
import os
import re
import shutil
import sys
import time
import traceback
import warnings

from pyaedt import pyaedt_logger
from pyaedt import settings
from pyaedt.edb_core import Components
from pyaedt.edb_core import EdbHfss
from pyaedt.edb_core import EdbLayout
from pyaedt.edb_core import EdbNets
from pyaedt.edb_core import EdbSiwave
from pyaedt.edb_core import EdbStackup
from pyaedt.edb_core.edb_data.edb_builder import EdbBuilder
from pyaedt.edb_core.edb_data.hfss_simulation_setup_data import HfssSimulationSetup
from pyaedt.edb_core.edb_data.padstacks_data import EDBPadstackInstance
from pyaedt.edb_core.edb_data.simulation_configuration import SimulationConfiguration
from pyaedt.edb_core.edb_data.siwave_simulation_setup_data import (
    SiwaveDCSimulationSetup,
)
from pyaedt.edb_core.edb_data.siwave_simulation_setup_data import (
    SiwaveSYZSimulationSetup,
)
from pyaedt.edb_core.edb_data.sources import ExcitationDifferential
from pyaedt.edb_core.edb_data.sources import ExcitationPorts
from pyaedt.edb_core.edb_data.sources import ExcitationProbes
from pyaedt.edb_core.edb_data.sources import ExcitationSources
from pyaedt.edb_core.edb_data.sources import SourceType
from pyaedt.edb_core.general import convert_py_list_to_net_list
from pyaedt.edb_core.materials import Materials
from pyaedt.edb_core.padstack import EdbPadstacks
from pyaedt.edb_core.stackup import Stackup
from pyaedt.generic.clr_module import Convert
from pyaedt.generic.clr_module import List
from pyaedt.generic.clr_module import _clr
from pyaedt.generic.clr_module import edb_initialized
from pyaedt.generic.constants import SolverType
from pyaedt.generic.general_methods import env_path
from pyaedt.generic.general_methods import env_path_student
from pyaedt.generic.general_methods import env_value
from pyaedt.generic.general_methods import generate_unique_name
from pyaedt.generic.general_methods import inside_desktop
from pyaedt.generic.general_methods import is_ironpython
from pyaedt.generic.general_methods import pyaedt_function_handler
from pyaedt.generic.process import SiwaveSolve
from pyaedt.misc.misc import list_installed_ansysem

if os.name == "posix" and is_ironpython:
    import subprocessdotnet as subprocess
else:
    import subprocess


class Edb(object):
    """Provides the EDB application interface.

    This module inherits all objects that belong to EDB.

    Parameters
    ----------
    edbpath : str, optional
        Full path to the ``aedb`` folder. The variable can also contain
        the path to a layout to import. Allowed formats are BRD,
        XML (IPC2581), GDS, and DXF. The default is ``None``.
        For GDS import, the Ansys control file (also XML) should have the same
        name as the GDS file. Only the file extension differs.
    cellname : str, optional
        Name of the cell to select. The default is ``None``.
    isreadonly : bool, optional
        Whether to open EBD in read-only mode when it is
        owned by HFSS 3D Layout. The default is ``False``.
    edbversion : str, optional
        Version of EDB to use. The default is ``"2021.2"``.
    isaedtowned : bool, optional
        Whether to launch EDB from HFSS 3D Layout. The
        default is ``False``.
    oproject : optional
        Reference to the AEDT project object.
    student_version : bool, optional
        Whether to open the AEDT student version. The default is ``False.``

    Examples
    --------
    Create an ``Edb`` object and a new EDB cell.

    >>> from pyaedt import Edb
    >>> app = Edb()

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
    ):
        self._clean_variables()
        if is_ironpython and inside_desktop:
            self.standalone = False
        else:
            self.standalone = True
        if edb_initialized:
            self.oproject = oproject
            self._main = sys.modules["__main__"]
            self._global_logger = pyaedt_logger
            self._logger = pyaedt_logger
            self.student_version = student_version
            self.logger.info("Logger is initialized in EDB.")
            if not edbversion:
                try:
                    edbversion = "20{}.{}".format(list_installed_ansysem()[0][-3:-1], list_installed_ansysem()[0][-1:])
                    self._logger.info("Edb version " + edbversion)
                except IndexError:
                    raise Exception("No ANSYSEM_ROOTxxx is found.")
            self.edbversion = edbversion
            self.isaedtowned = isaedtowned
            self._init_dlls()
            self._db = None
            # self._edb.Database.SetRunAsStandAlone(not isaedtowned)
            self.isreadonly = isreadonly
            self.cellname = cellname
            if not edbpath:
                if os.name != "posix":
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

            if isaedtowned and (inside_desktop or settings.remote_api):
                self.open_edb_inside_aedt()
            elif edbpath[-3:] in ["brd", "gds", "xml", "dxf", "tgz"]:
                self.edbpath = edbpath[:-4] + ".aedb"
                working_dir = os.path.dirname(edbpath)
                self.import_layout_pcb(edbpath, working_dir, use_ppe=use_ppe)
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
                self.logger.info("EDB %s was created correctly.", self.edbpath)
            elif ".aedb" in edbpath:
                self.edbpath = edbpath
                if settings.enable_local_log_file and self.log_name:
                    self._logger = self._global_logger.add_file_logger(self.log_name, "Edb")
                self.open_edb()
            if self.builder:
                self.logger.info("EDB was initialized.")
            else:
                self.logger.info("Failed to initialize DLLs.")
        else:
            warnings.warn("Failed to initialize DLLs.")

    def __enter__(self):
        return self

    def __exit__(self, ex_type, ex_value, ex_traceback):
        if ex_type:
            self.edb_exception(ex_value, ex_traceback)

    def _clean_variables(self):
        """Initialize internal variables and perform garbage collection."""

        self._components = None
        self._core_primitives = None
        self._stackup = None
        self._padstack = None
        self._siwave = None
        self._hfss = None
        self._nets = None
        self._db = None
        self._edb = None
        self.builder = None
        self._edblib = None
        self.edbutils = None
        self.simSetup = None
        self.simsetupdata = None
        self._setups = {}
        self._layout_instance = None
        # time.sleep(2)
        # gc.collect()

    @pyaedt_function_handler()
    def _init_objects(self):
        time.sleep(1)
        self._components = Components(self)
        self._stackup = EdbStackup(self)
        self._padstack = EdbPadstacks(self)
        self._siwave = EdbSiwave(self)
        self._hfss = EdbHfss(self)
        self._nets = EdbNets(self)
        self._core_primitives = EdbLayout(self)
        self._stackup2 = Stackup(self)
        self._materials = Materials(self)

        self.logger.info("Objects Initialized")

    @property
    def logger(self):
        """Logger for EDB.

        Returns
        -------
        :class:`pyaedt.aedt_logger.AedtLogger`
        """
        return self._logger

    @property
    def cell_names(self):
        """Cell name container.
        Returns
        -------
        list of str, cell names.
        """
        names = []
        for cell in list(self._db.TopCircuitCells):
            names.append(cell.GetName())
        return names

    @pyaedt_function_handler()
    def _init_dlls(self):
        """Initialize DLLs."""
        sys.path.append(os.path.join(os.path.dirname(__file__), "dlls", "EDBLib"))
        if os.name == "posix":
            if env_value(self.edbversion) in os.environ:
                self.base_path = env_path(self.edbversion)
                sys.path.append(self.base_path)
            else:
                main = sys.modules["__main__"]
                if "oDesktop" in dir(main):
                    self.base_path = main.oDesktop.GetExeDir()
                    sys.path.append(main.oDesktop.GetExeDir())
                    os.environ[env_value(self.edbversion)] = self.base_path
                else:
                    edb_path = os.getenv("PYAEDT_SERVER_AEDT_PATH")
                    if edb_path:
                        self.base_path = edb_path
                        sys.path.append(edb_path)
                        os.environ[env_value(self.edbversion)] = self.base_path
            if is_ironpython:
                _clr.AddReferenceToFile("Ansys.Ansoft.Edb.dll")
                _clr.AddReferenceToFile("Ansys.Ansoft.EdbBuilderUtils.dll")
                _clr.AddReferenceToFileAndPath(os.path.join(self.base_path, "Ansys.Ansoft.SimSetupData.dll"))
            else:
                _clr.AddReference("Ansys.Ansoft.Edb")
                _clr.AddReference("Ansys.Ansoft.EdbBuilderUtils")
                _clr.AddReference("Ansys.Ansoft.SimSetupData")
        else:
            if self.student_version:
                self.base_path = env_path_student(self.edbversion)
            else:
                self.base_path = env_path(self.edbversion)
            sys.path.append(self.base_path)
            _clr.AddReference("Ansys.Ansoft.Edb")
            _clr.AddReference("Ansys.Ansoft.EdbBuilderUtils")
            _clr.AddReference("Ansys.Ansoft.SimSetupData")
        os.environ["ECAD_TRANSLATORS_INSTALL_DIR"] = self.base_path
        oaDirectory = os.path.join(self.base_path, "common", "oa")
        os.environ["ANSYS_OADIR"] = oaDirectory
        os.environ["PATH"] = "{};{}".format(os.environ["PATH"], self.base_path)
        edb = __import__("Ansys.Ansoft.Edb")
        self.edb = edb.Ansoft.Edb
        edbbuilder = __import__("Ansys.Ansoft.EdbBuilderUtils")
        self._edblib = None
        self.edbutils = edbbuilder.Ansoft.EdbBuilderUtils
        self.simSetup = __import__("Ansys.Ansoft.SimSetupData")
        self.simsetupdata = self.simSetup.Ansoft.SimSetupData.Data

    @property
    def edblib(self):
        """EDB library object containing advanced EDB methods not accessible directly from Python."""
        if not self._edblib:
            if os.name == "posix" and is_ironpython:
                _clr.AddReferenceToFile("EdbLib.dll")
                _clr.AddReferenceToFile("DataModel.dll")
            else:
                _clr.AddReference("EdbLib")
                _clr.AddReference("DataModel")
            self._edblib = __import__("EdbLib")
            dllpath = os.path.join(os.path.abspath(os.path.dirname(__file__)), "dlls", "EDBLib")
            try:
                self._edblib.Layout.LayoutMethods.LoadDataModel(dllpath, self.edbversion)
            except:
                pass
        return self._edblib

    @property
    def excitations(self):
        """Get all layout excitations."""
        terms = [term for term in list(self._active_layout.Terminals) if int(term.GetBoundaryType()) == 0]
        terms = [i for i in terms if not i.IsReferenceTerminal()]
        temp = {}
        for ter in terms:
            if "BundleTerminal" in ter.GetType().ToString():
                temp[ter.GetName()] = ExcitationDifferential(self, ter)
            else:
                temp[ter.GetName()] = ExcitationPorts(self, ter)
        return temp

    @property
    def sources(self):
        """Get all layout sources."""
        terms = [term for term in list(self._active_layout.Terminals) if int(term.GetBoundaryType()) in [3, 4, 7]]
        return {ter.GetName(): ExcitationSources(self, ter) for ter in terms}

    @property
    def probes(self):
        """Get all layout sources."""
        terms = [term for term in list(self._active_layout.Terminals) if int(term.GetBoundaryType()) in [8]]
        return {ter.GetName(): ExcitationProbes(self, ter) for ter in terms}

    @pyaedt_function_handler()
    def open_edb(self, init_dlls=False):
        """Open EDB.

        Parameters
        ----------
        init_dlls : bool, optional
            Whether to initialize DLLs. The default is ``False``.

        Returns
        -------

        """
        if init_dlls:
            self._init_dlls()
        self.logger.info("EDB Path %s", self.edbpath)
        self.logger.info("EDB Version %s", self.edbversion)
        self.edb.Database.SetRunAsStandAlone(self.standalone)
        self.logger.info("EDB Standalone %s", self.standalone)
        try:
            db = self.edb.Database.Open(self.edbpath, self.isreadonly)
        except Exception as e:
            db = None
            self.logger.error("Builder is not Initialized.")
        if not db:
            self.logger.warning("Error Opening db")
            self._db = None
            self._active_cell = None
            self.builder = None
            return None
        self._db = db
        self.logger.info("Database Opened")

        self._active_cell = None
        if self.cellname:
            for cell in list(self._db.TopCircuitCells):
                if cell.GetName() == self.cellname:
                    self._active_cell = cell
        # if self._active_cell is still None, set it to default cell
        if self._active_cell is None:
            self._active_cell = list(self._db.TopCircuitCells)[0]
        self.logger.info("Cell %s Opened", self._active_cell.GetName())
        if self._db and self._active_cell:
            dllpath = os.path.join(os.path.abspath(os.path.dirname(__file__)), "dlls", "EDBLib")
            self.logger.info(dllpath)
            self.builder = EdbBuilder(self.edbutils, self._db, self._active_cell)
            self._init_objects()
            self.logger.info("Builder was initialized.")
        else:
            self.builder = None
            self.logger.error("Builder was not initialized.")

        return self.builder

    @pyaedt_function_handler()
    def open_edb_inside_aedt(self, init_dlls=False):
        """Open EDB inside of AEDT.

        Parameters
        ----------
        init_dlls : bool, optional
            Whether to initialize DLLs. The default is ``False``.

        Returns
        -------

        """
        if init_dlls:
            self._init_dlls()
        self.logger.info("Opening EDB from HDL")
        self.edb.Database.SetRunAsStandAlone(False)
        if self.oproject.GetEDBHandle():
            hdl = Convert.ToUInt64(self.oproject.GetEDBHandle())
            db = self.edb.Database.Attach(hdl)
            if not db:
                self.logger.warning("Error getting the database.")
                self._db = None
                self._active_cell = None
                self.builder = None
                return None
            self._db = db
            self._active_cell = self.edb.Cell.Cell.FindByName(
                self.db, self.edb.Cell.CellType.CircuitCell, self.cellname
            )
            if self._active_cell is None:
                self._active_cell = list(self._db.TopCircuitCells)[0]
            if self._db and self._active_cell:
                if not os.path.exists(self.edbpath):
                    os.makedirs(self.edbpath)
                time.sleep(3)
                self.builder = EdbBuilder(self.edbutils, self._db, self._active_cell)
                self._init_objects()
                return self.builder
            else:
                self.builder = None
                return None
        else:
            self._db = None
            self._active_cell = None
            self.builder = None
            return None

    @pyaedt_function_handler()
    def create_edb(self, init_dlls=False):
        """Create EDB.

        Parameters
        ----------
        init_dlls : bool, optional
            Whether to initialize DLLs. The default is ``False``.

        """
        if init_dlls:
            self._init_dlls()
        self.edb.Database.SetRunAsStandAlone(self.standalone)
        db = self.edb.Database.Create(self.edbpath)
        if not db:
            self.logger.warning("Error creating the database.")
            self._db = None
            self._active_cell = None
            self.builder = None
            return None
        self._db = db
        if not self.cellname:
            self.cellname = generate_unique_name("Cell")
        self._active_cell = self.edb.Cell.Cell.Create(self._db, self.edb.Cell.CellType.CircuitCell, self.cellname)
        dllpath = os.path.join(os.path.dirname(__file__), "dlls", "EDBLib")
        if self._db and self._active_cell:
            self.builder = EdbBuilder(self.edbutils, self._db, self._active_cell)
            self._init_objects()
            return self.builder
        self.builder = None
        return None

    @pyaedt_function_handler()
    def import_layout_pcb(
        self, input_file, working_dir, init_dlls=False, anstranslator_full_path="", use_ppe=False, control_file=None
    ):
        """Import a board file and generate an ``edb.def`` file in the working directory.

        This function supports all AEDT formats (DXF, GDS, SML (IPC2581), BRD, TGZ ...).

        Parameters
        ----------
        input_file : str
            Full path to the board file.
        working_dir : str
            Directory in which to create the ``aedb`` folder. The name given to the AEDB file
            is the same as the name of the board file.
        init_dlls : bool
            Whether to initialize DLLs. The default is ``False``.
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
        self._db = None
        if init_dlls:
            self._init_dlls()
        aedb_name = os.path.splitext(os.path.basename(input_file))[0] + ".aedb"
        if anstranslator_full_path and os.path.exists(anstranslator_full_path):
            command = anstranslator_full_path
        else:
            command = os.path.join(self.base_path, "anstranslator")
            if os.name != "posix":
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
        if control_file and input_file[-3:] not in ["brd"]:
            if os.name == "posix":
                cmd_translator.append("-c={}".format(control_file))
            else:
                cmd_translator.append('-c="{}"'.format(control_file))
        p = subprocess.Popen(cmd_translator)
        p.wait()
        if not os.path.exists(os.path.join(working_dir, aedb_name)):
            self.logger.error("Translator failed to translate.")
            return False
        self.edbpath = os.path.join(working_dir, aedb_name)
        self.open_edb()

    @pyaedt_function_handler()
    def export_to_ipc2581(self, ipc_path=None, units="millimeter"):
        """Create an XML IPC2581 file from the active EDB.

        .. note::
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
        if units.lower() not in ["millimeter", "inch", "micron"]:
            self.logger.warning("The wrong unit is entered. Setting to the default, millimeter.")
            units = "millimeter"

        if not ipc_path:
            ipc_path = self.edbpath[:-4] + "xml"
        self.logger.info("Export IPC 2581 is starting. This operation can take a while.")
        start = time.time()
        try:
            result = self.edblib.IPC8521.IPCExporter.ExportIPC2581FromLayout(
                self.active_layout, self.edbversion, ipc_path, units.lower()
            )
            end = time.time() - start
            if result:
                self.logger.info("Export IPC 2581 completed in %s sec.", end)
                self.logger.info("File saved as %s", ipc_path)
                return ipc_path
        except Exception as e:
            self.logger.info("Error exporting IPC 2581.")
            self.logger.info(str(e))
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
    def db(self):
        """Database object."""
        return self._db

    @property
    def active_cell(self):
        """Active cell."""
        return self._active_cell

    @property
    def core_components(self):
        """Core components."""
        if not self._components and self.builder:
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
        if not self._stackup and self.builder:
            self._stackup = EdbStackup(self)
        return self._stackup

    @property
    def stackup(self):
        """Stackup."""
        if not self._stackup2 and self.builder:
            self._stackup2 = Stackup(self)
        return self._stackup2

    @property
    def materials(self):
        """Material Database."""
        if not self._materials and self.builder:
            self._materials = Materials(self)
        return self._materials

    @property
    def core_padstack(self):
        """Core padstack."""
        if not self._padstack and self.builder:
            self._padstack = EdbPadstacks(self)
        return self._padstack

    @property
    def core_siwave(self):
        """Core SI Wave."""
        if not self._siwave and self.builder:
            self._siwave = EdbSiwave(self)
        return self._siwave

    @property
    def core_hfss(self):
        """Core HFSS."""
        if not self._hfss and self.builder:
            self._hfss = EdbHfss(self)
        return self._hfss

    @property
    def core_nets(self):
        """Core nets."""
        if not self._nets and self.builder:
            self._nets = EdbNets(self)
        return self._nets

    @property
    def core_primitives(self):
        """Core primitives."""
        if not self._core_primitives and self.builder:
            self._core_primitives = EdbLayout(self)
        return self._core_primitives

    @property
    def active_layout(self):
        """Active layout."""
        self._active_layout = None
        if self._active_cell:
            self._active_layout = self.active_cell.GetLayout()
        return self._active_layout

    @property
    def layout_instance(self):
        if not self._layout_instance:
            self._layout_instance = self.active_layout.GetLayoutInstance()
        return self._layout_instance

    @property
    def pins(self):
        """EDBPadstackInstance of Component.

        Returns
        -------
        dic[str, :class:`pyaedt.edb_core.edb_data.padstacks.EDBPadstackInstance`]
            Dictionary of EDBPadstackInstance Components.
        """
        pins = {}
        if self.core_components:
            for el in self.core_components.components:
                comp = self.edb.Cell.Hierarchy.Component.FindByName(self.active_layout, el)
                temp = [
                    p
                    for p in comp.LayoutObjs
                    if p.GetObjType() == self.edb.Cell.LayoutObjType.PadstackInstance and p.IsLayoutPin()
                ]
                for p in temp:
                    pins[p.GetId()] = EDBPadstackInstance(p, self)
        return pins

    class Boundaries:
        """Boundaries.

        Parameters
        ----------
        Port :

        Pec :

        RLC :

        CurrentSource :

        VoltageSource :

        NexximGround :

        NexximPort :

        DcTerminal :

        VoltageProbe :

        """

        (Port, Pec, RLC, CurrentSource, VoltageSource, NexximGround, NexximPort, DcTerminal, VoltageProbe) = range(0, 9)

    @pyaedt_function_handler()
    def edb_value(self, val):
        """EDB value.

        Parameters
        ----------
        val : str, float, int


        Returns
        -------

        """
        if isinstance(val, (int, float)):
            return self.edb.Utility.Value(val)
        m1 = re.findall(r"(?<=[/+-/*//^/(/[])([a-z_A-Z/$]\w*)", str(val).replace(" ", ""))
        m2 = re.findall(r"^([a-z_A-Z/$]\w*)", str(val).replace(" ", ""))
        val_decomposed = list(set(m1).union(m2))
        if not val_decomposed:
            return self.edb.Utility.Value(val)
        var_server_db = self.db.GetVariableServer()
        var_names = var_server_db.GetAllVariableNames()
        var_server_cell = self.active_cell.GetVariableServer()
        var_names_cell = var_server_cell.GetAllVariableNames()
        if set(val_decomposed).intersection(var_names):
            return self.edb.Utility.Value(val, var_server_db)
        if set(val_decomposed).intersection(var_names_cell):
            return self.edb.Utility.Value(val, var_server_cell)
        return self.edb.Utility.Value(val)

    @pyaedt_function_handler()
    def _is_file_existing_and_released(self, filename):
        if os.path.exists(filename):
            try:
                os.rename(filename, filename + "_")
                os.rename(filename + "_", filename)
                return True
            except OSError as e:
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
        """Close EDB.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        self._db.Close()
        if self.log_name and settings.enable_local_log_file:
            self._global_logger.remove_file_logger(os.path.splitext(os.path.split(self.log_name)[-1])[0])
            self._logger = self._global_logger
        time.sleep(2)
        start_time = time.time()
        self._wait_for_file_release()
        elapsed_time = time.time() - start_time
        self.logger.info("EDB file release time: {0:.2f}ms".format(elapsed_time * 1000.0))
        self._clean_variables()
        timeout = 4
        time.sleep(2)
        while gc.collect() != 0 and timeout > 0:
            time.sleep(1)
            timeout -= 1
        return True

    @pyaedt_function_handler()
    def save_edb(self):
        """Save the EDB file.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        self._db.Save()
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
        self._db.SaveAs(fname)
        self.edbpath = self._db.GetDirectory()
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
        return self.edb.Utility.Command.Execute(func)

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
    def import_gds_file(self, inputGDS, WorkDir=None, anstranslator_full_path="", use_ppe=False, control_file=None):
        """Import a GDS file and generate an ``edb.def`` file in the working directory.

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

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
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
    ):
        if extent_type in ["Conforming", self.edb.Geometry.ExtentType.Conforming, 1]:

            if use_pyaedt_extent:
                _poly = self._create_conformal(net_signals, expansion_size, 1e-12, use_round_corner, expansion_size)
            else:
                _poly = self.active_layout.GetExpandedExtentFromNets(
                    net_signals, self.edb.Geometry.ExtentType.Conforming, expansion_size, False, use_round_corner, 1
                )
        elif extent_type in ["Bounding", self.edb.Geometry.ExtentType.BoundingBox, 0]:
            _poly = self.active_layout.GetExpandedExtentFromNets(
                net_signals, self.edb.Geometry.ExtentType.BoundingBox, expansion_size, False, use_round_corner, 1
            )
        else:
            if use_pyaedt_extent:
                _poly = self._create_convex_hull(net_signals, expansion_size, 1e-12, use_round_corner, expansion_size)
            else:
                _poly = self.active_layout.GetExpandedExtentFromNets(
                    net_signals, self.edb.Geometry.ExtentType.Conforming, expansion_size, False, use_round_corner, 1
                )
                _poly_list = convert_py_list_to_net_list([_poly])
                _poly = self.edb.Geometry.PolygonData.GetConvexHullOfPolygons(_poly_list)
        return _poly

    @pyaedt_function_handler()
    def _create_conformal(self, net_signals, expansion_size, tolerance, round_corner, round_extension):
        names = []
        _polys = []
        for net in net_signals:
            names.append(net.GetName())
        for prim in self.core_primitives.primitives:
            if prim.net_name in names:
                obj_data = prim.primitive_object.GetPolygonData().Expand(
                    expansion_size, tolerance, round_corner, round_extension
                )
                if obj_data:
                    _polys.extend(list(obj_data))
        _poly = self.edb.Geometry.PolygonData.Unite(convert_py_list_to_net_list(_polys))[0]
        return _poly

    @pyaedt_function_handler()
    def _create_convex_hull(self, net_signals, expansion_size, tolerance, round_corner, round_extension):
        names = []
        _polys = []
        for net in net_signals:
            names.append(net.GetName())
        for prim in self.core_primitives.primitives:
            if prim.net_name in names:
                _polys.append(prim.primitive_object.GetPolygonData())
        _poly = self.edb.Geometry.PolygonData.GetConvexHullOfPolygons(convert_py_list_to_net_list(_polys))
        _poly = _poly.Expand(expansion_size, tolerance, round_corner, round_extension)[0]
        return _poly

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
        """Create a cutout and save it to a new AEDB file.

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
        expansion_size = self.edb_value(expansion_size).ToDouble()

        # validate nets in layout
        net_signals = convert_py_list_to_net_list(
            [net for net in list(self.active_layout.Nets) if net.GetName() in signal_list]
        )
        # validate references in layout
        _netsClip = convert_py_list_to_net_list(
            [net for net in list(self.active_layout.Nets) if net.GetName() in reference_list]
        )

        _poly = self._create_extent(
            net_signals,
            extent_type,
            expansion_size,
            use_round_corner,
            use_pyaedt_extent_computing,
        )

        # Create new cutout cell/design
        included_nets_list = signal_list + reference_list
        included_nets = convert_py_list_to_net_list(
            [net for net in list(self.active_layout.Nets) if net.GetName() in included_nets_list]
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
            db2 = self.edb.Database.Create(output_aedb_path)
            _success = db2.Save()
            _dbCells = convert_py_list_to_net_list(_dbCells)
            db2.CopyCells(_dbCells)  # Copies cutout cell/design to db2 project
            if len(list(db2.CircuitCells)) > 0:
                for net in list(list(db2.CircuitCells)[0].GetLayout().Nets):
                    if not net.GetName() in included_nets_list:
                        net.Delete()
                _success = db2.Save()
            for c in list(self.db.TopCircuitCells):
                if c.GetName() == _cutout.GetName():
                    c.Delete()
            if open_cutout_at_end:  # pragma: no cover
                self._db = db2
                self.edbpath = output_aedb_path
                self._active_cell = list(self._db.TopCircuitCells)[0]
                dllpath = os.path.join(os.path.dirname(__file__), "dlls", "EDBLib")
                self.builder = EdbBuilder(self.edbutils, self._db, self._active_cell)
                self.edbpath = self._db.GetDirectory()
                self._init_objects()
            else:
                db2.Close()
                source = os.path.join(output_aedb_path, "edb.def.tmp")
                target = os.path.join(output_aedb_path, "edb.def")
                self._wait_for_file_release(file_to_release=output_aedb_path)
                if os.path.exists(source) and not os.path.exists(target):
                    try:
                        shutil.copy(source, target)
                    except:
                        pass
        # else:
        # cells = self.db.CopyCells(convert_py_list_to_net_list(_dbCells))
        elif open_cutout_at_end:
            self._active_cell = _cutout
            self._init_objects()
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
    ):
        """Create a cutout using an approach entirely based on pyaedt.
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

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------
        >>> edb = Edb(r'C:.aedb', edbversion="2022.2")
        >>> edb.logger.info_timer("Edb Opening")
        >>> edb.logger.reset_timer()
        >>> start = time.time()
        >>> signal_list = []
        >>> for net in edb.core_nets.nets.keys():
        >>>      if "3V3" in net:
        >>>           signal_list.append(net)
        >>> power_list = ["PGND"]
        >>> edb.create_cutout_multithread(signal_list=signal_list, reference_list=power_list, extent_type="Conforming")
        >>> end_time = str((time.time() - start)/60)
        >>> edb.logger.info("Total pyaedt cutout time in min %s", end_time)
        >>> edb.core_nets.plot(signal_list, None, color_by_net=True)
        >>> edb.core_nets.plot(power_list, None, color_by_net=True)
        >>> edb.save_edb()
        >>> edb.close_edb()

        """
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
            reference_list = reference_list + signal_list
            all_list = reference_list
        else:
            all_list = signal_list + reference_list

        reference_pinsts = []
        reference_prims = []
        for i in self.core_padstack.padstack_instances.values():
            net_name = i.net_name
            if net_name not in all_list:
                i.delete()
            elif net_name in reference_list:
                reference_pinsts.append(i)
        for i in self.core_primitives.primitives:
            net_name = i.net_name
            if net_name not in all_list:
                i.delete()
            elif net_name in reference_list and not i.is_void:
                reference_prims.append(i)

        for i in self.core_nets.nets.values():
            if i.name not in all_list:
                i.net_object.Delete()
        self.logger.info_timer("Net clean up")
        self.logger.reset_timer()

        if custom_extent and isinstance(custom_extent, list):
            plane = self.core_primitives.Shape("polygon", points=custom_extent)
            _poly = self.core_primitives.shape_to_polygon_data(plane)
        elif custom_extent:
            _poly = custom_extent
        else:
            net_signals = convert_py_list_to_net_list(
                [net for net in list(self.active_layout.Nets) if net.GetName() in signal_list]
            )
            _poly = self._create_extent(
                net_signals, extent_type, expansion_size, use_round_corner, use_pyaedt_extent_computing
            )
            if extent_type in ["Conforming", self.edb.Geometry.ExtentType.Conforming, 1] and extent_defeature > 0:
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

        def get_polygon_data(prim):
            return prim.primitive_object.GetPolygonData()

        def intersect(poly1, poly2):
            return list(poly1.Intersect(poly2))

        def subtract(poly, voids):
            return poly.Subtract(convert_py_list_to_net_list(poly), convert_py_list_to_net_list(voids))

        def clean_prim(prim_1):  # pragma: no cover
            pdata = get_polygon_data(prim_1)
            int_data = _poly.GetIntersectionType(pdata)
            if int_data == 0:
                prims_to_delete.append(prim_1)
            elif int_data != 2:
                list_poly = intersect(_poly, pdata)
                if list_poly:
                    net = prim_1.net_name
                    voids = prim_1.voids
                    for p in list_poly:
                        if p.IsNull():
                            continue
                        list_void = []
                        void_to_subtract = []
                        if voids:
                            for void in voids:
                                void_pdata = get_polygon_data(void)
                                int_data2 = p.GetIntersectionType(void_pdata)
                                if int_data2 > 2 or int_data2 == 1:
                                    void_to_subtract.append(void_pdata)
                                elif int_data2 == 2:
                                    list_void.append(void_pdata)
                            if void_to_subtract:
                                polys_cleans = subtract(p, void_to_subtract)
                                for polys_clean in polys_cleans:
                                    if not polys_clean.IsNull():
                                        void_to_append = [
                                            v for v in list_void if polys_clean.GetIntersectionType(v) == 2
                                        ]
                                        poly_to_create.append([polys_clean, prim_1.layer_name, net, void_to_append])
                            else:
                                poly_to_create.append([p, prim_1.layer_name, net, list_void])
                        else:
                            poly_to_create.append([p, prim_1.layer_name, net, list_void])

                prims_to_delete.append(prim_1)

        def pins_clean(pinst):
            if not pinst.in_polygon(_poly, simple_check=True):
                pins_to_delete.append(pinst)

        with ThreadPoolExecutor(number_of_threads) as pool:
            pool.map(lambda item: pins_clean(item), reference_pinsts)

        for pin in pins_to_delete:
            pin.delete()

        self.logger.info_timer("Padstack Instances removal completed")
        self.logger.reset_timer()

        with ThreadPoolExecutor(number_of_threads) as pool:
            pool.map(lambda item: clean_prim(item), reference_prims)

        for el in poly_to_create:
            self.core_primitives.create_polygon(el[0], el[1], net_name=el[2], voids=el[3])

        for prim in prims_to_delete:
            prim.delete()
        self.logger.info_timer("Primitives cleanup completed")
        self.logger.reset_timer()

        i = 0
        for comp, val in self.core_components.components.items():
            if val.numpins == 0:
                val.edbcomponent.Delete()
                i += 1
        self.logger.info("Deleted {} additional components".format(i))
        if remove_single_pin_components:
            self.core_components.delete_single_pin_rlc()
            self.logger.info_timer("Single Pins components deleted")

        self.core_components.refresh_components()

        self.logger.info_timer("Cutout completed.", timer_start)
        self.logger.reset_timer()
        return True

    @pyaedt_function_handler()
    def get_conformal_polygon_from_netlist(self, netlist=None):
        """Return an EDB conformal polygon based on a netlist.

        Parameters
        ----------

        netlist : List of net names.
            list[str]

        Returns
        -------

        Edb polygon object
            Edb.Cell.Primitive.Polygon object

        """
        temp_edb_path = self.edbpath[:-5] + "_temp_aedb.aedb"
        shutil.copytree(self.edbpath, temp_edb_path)
        temp_edb = Edb(temp_edb_path)
        for via in list(temp_edb.core_padstack.padstack_instances.values()):
            via.pin.Delete()
        if netlist:
            nets = convert_py_list_to_net_list(
                [net for net in list(self.active_layout.Nets) if net.GetName() in netlist]
            )
            _poly = temp_edb.active_layout.GetExpandedExtentFromNets(
                nets, self.edb.Geometry.ExtentType.Conforming, 0.0, True, True, 1
            )
        else:
            nets = convert_py_list_to_net_list(
                [net for net in list(temp_edb.active_layout.Nets) if "gnd" in net.GetName().lower()]
            )
            _poly = temp_edb.active_layout.GetExpandedExtentFromNets(
                nets, self.edb.Geometry.ExtentType.Conforming, 0.0, True, True, 1
            )
            temp_edb.close_edb()
        if _poly:
            return _poly
        else:
            return False

    @pyaedt_function_handler()
    def arg_with_dim(self, Value, sUnits):
        """Format arguments with dimensions.

        Parameters
        ----------
        Value :

        sUnits :

        Returns
        -------
        str
            String containing the value or the value and units if ``sUnits`` is not ``None``.
        """
        if type(Value) is str:
            val = Value
        else:
            val = "{0}{1}".format(Value, sUnits)

        return val

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

        if point_list[0] != point_list[-1]:
            point_list.append(point_list[0])
        point_list = [[self.arg_with_dim(i[0], units), self.arg_with_dim(i[1], units)] for i in point_list]
        plane = self.core_primitives.Shape("polygon", points=point_list)
        polygonData = self.core_primitives.shape_to_polygon_data(plane)
        _ref_nets = []
        if nets_to_include:
            self.logger.info("Creating cutout on {} nets.".format(len(nets_to_include)))
        else:
            self.logger.info("Creating cutout on all nets.")  # pragma: no cover

        # Check Padstack Instances overlapping the cutout
        pinstance_to_add = []
        if include_partial_instances:
            if nets_to_include:
                pinst = [
                    i for i in list(self.core_padstack.padstack_instances.values()) if i.net_name in nets_to_include
                ]
            else:
                pinst = [i for i in list(self.core_padstack.padstack_instances.values())]
            for p in pinst:
                if p.in_polygon(polygonData):
                    pinstance_to_add.append(p)
        # validate references in layout
        for _ref in self.core_nets.nets:
            if nets_to_include:
                if _ref in nets_to_include:
                    _ref_nets.append(self.core_nets.nets[_ref].net_object)
            else:
                _ref_nets.append(self.core_nets.nets[_ref].net_object)  # pragma: no cover
        if keep_voids:
            voids = [p for p in self.core_primitives.circles if p.is_void]
            voids2 = [p for p in self.core_primitives.polygons if p.is_void]
            voids.extend(voids2)
        else:
            voids = []
        voids_to_add = []
        for circle in voids:
            if polygonData.GetIntersectionType(circle.primitive_object.GetPolygonData()) >= 3:
                voids_to_add.append(circle)

        _netsClip = convert_py_list_to_net_list(_ref_nets)
        net_signals = List[type(_ref_nets[0])]()  # pragma: no cover
        # Create new cutout cell/design
        _cutout = self.active_cell.CutOut(net_signals, _netsClip, polygonData)
        layout = _cutout.GetLayout()
        cutout_obj_coll = list(layout.PadstackInstances)
        ids = []
        for lobj in cutout_obj_coll:
            ids.append(lobj.GetId())

        if include_partial_instances:
            p_missing = [i for i in pinstance_to_add if i.id not in ids]
            self.logger.info("Added {} padstack instances after cutout".format(len(p_missing)))
            for p in p_missing:
                position = self.edb.Geometry.PointData(self.edb_value(p.position[0]), self.edb_value(p.position[1]))
                net = self.core_nets.find_or_create_net(p.net_name)
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
                for pad in list(self.core_padstack.padstacks.keys()):
                    if pad == p.padstack_definition:
                        padstack = self.core_padstack.padstacks[pad].edb_padstack
                        padstack_instance = self.edb.Cell.Primitive.PadstackInstance.Create(
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
                cloned_circle = self.edb.Cell.Primitive.Circle.Create(
                    layout,
                    void_circle.layer_name,
                    void_circle.net,
                    self.edb_value(center_x),
                    self.edb_value(center_y),
                    self.edb_value(radius),
                )
                cloned_circle.SetIsNegative(True)
            elif void_circle.type == "Polygon":
                cloned_polygon = self.edb.Cell.Primitive.Polygon.Create(
                    layout, void_circle.layer_name, void_circle.net, void_circle.primitive_object.GetPolygonData()
                )
                cloned_polygon.SetIsNegative(True)
        layers = [i for i in list(self.stackup.signal_layers.keys())]
        for layer in layers:
            layer_primitves = self.core_primitives.get_primitives(layer_name=layer)
            if len(layer_primitves) == 0:
                self.core_primitives.create_polygon(plane, layer, net_name="DUMMY")
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
            db2 = self.edb.Database.Create(output_aedb_path)
            if not db2.Save():
                self.logger.error("Failed to create new Edb. Check if the path already exists and remove it.")
                return False
            _dbCells = convert_py_list_to_net_list(_dbCells)
            cell_copied = db2.CopyCells(_dbCells)  # Copies cutout cell/design to db2 project
            cell = list(cell_copied)[0]
            cell.SetName(os.path.basename(output_aedb_path[:-5]))
            db2.Save()
            for c in list(self.db.TopCircuitCells):
                if c.GetName() == _cutout.GetName():
                    c.Delete()
            if open_cutout_at_end:  # pragma: no cover
                _success = db2.Save()
                self._db = db2
                self.edbpath = output_aedb_path
                self._active_cell = cell
                self.builder = EdbBuilder(self.edbutils, self._db, self._active_cell)
                self.edbpath = self._db.GetDirectory()
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
            self._db.Close()
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
            list of files generated.
        """
        process = SiwaveSolve(self.edbpath, aedt_version=self.edbversion)
        try:
            self._db.Close()
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
    def add_design_variable(self, variable_name, variable_value, is_parameter=False):
        """Add a design variable.

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
        >>> boolean_2, para_length = edb_app.change_design_variable_value("my_parameter", "1m", is_parameter=True
        >>> boolean_3, project_length = edb_app.change_design_variable_value("$my_project_variable", "1m")


        """
        if "$" in variable_name:
            if variable_name.index("$") == 0:
                var_server = self.db.GetVariableServer()
                is_parameter = False
                string_message = [
                    "Creating project variable %s.",
                    "Project variable %s already exists. You can use it.",
                ]
            else:
                var_server = self.active_cell.GetVariableServer()
                self.logger.warning(
                    "The character ``$`` must be placed at the beginning of your variable name,"
                    " to make it a project variable."
                )

                string_message = ["Creating local variable %s.", "Local variable %s already exists. You can use it."]
        else:
            var_server = self.active_cell.GetVariableServer()
            string_message = ["Creating local variable %s.", "Local variable %s already exists. You can use it."]
        variables = var_server.GetAllVariableNames()
        if variable_name in list(variables):
            if var_server.IsVariableParameter(variable_name):
                string_message[1] = "Parameter default %s already exists. You can use it."
            self.logger.warning(string_message[1], variable_name)
            return False, var_server
        else:
            if is_parameter:
                string_message[0] = "Creating parameter default %s"
            self.logger.info(string_message[0], variable_name)
            var_server.AddVariable(variable_name, self.edb_value(variable_value), is_parameter)
            return True, var_server

    @pyaedt_function_handler()
    def change_design_variable_value(self, variable_name, variable_value):
        """Change a variable value.

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

        """
        if "$" in variable_name:
            if variable_name.index("$") == 0:
                var_server = self.db.GetVariableServer()
                string_message = [
                    "Value of the project variable %s has been changed from %s to %s.",
                    "Project variable %s doesn't exist. You can create it using the method add_design_variable.",
                ]
            else:
                var_server = self.active_cell.GetVariableServer()
                string_message = [
                    "Value of the local variable %s has been changed from %s to %s.",
                    "Local variable or parameter default %s doesn't exist."
                    " You can create it using method add_design_variable.",
                ]
        else:
            var_server = self.active_cell.GetVariableServer()
            string_message = [
                "Value of the local variable %s has been changed from %s to %s.",
                "Local variable or parameter default %s doesn't exist."
                " You can create it using the method add_design_variable.",
            ]
        variables = var_server.GetAllVariableNames()
        if variable_name in list(variables):
            if is_ironpython:
                tuple_value = var_server.GetVariableValue(variable_name)
            else:
                out_value = self.edb.Utility.Value("")
                tuple_value = var_server.GetVariableValue(variable_name, out_value)
            var_server.SetVariableValue(variable_name, self.edb_value(variable_value))
            if var_server.IsVariableParameter(variable_name):
                string_message[0] = "Value of the parameter default %s has been changed from %s to %s."
            self.logger.info(string_message[0], variable_name, tuple_value[1], variable_value)
            return True, var_server
        else:
            self.logger.error(string_message[1], variable_name)
            return False

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
        """Build a ready-to-solve simulation project.

        Parameters
        ----------
        simulation_setup : edb_data.SimulationConfiguratiom object.
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

            self.core_nets.classify_nets(simulation_setup.power_nets, simulation_setup.signal_nets)
            if simulation_setup.do_cutout_subdesign:
                self.logger.info("Cutting out using method: {0}".format(simulation_setup.cutout_subdesign_type))
                if simulation_setup.use_default_cutout:
                    old_cell_name = self.active_cell.GetName()
                    if self.create_cutout(
                        signal_list=simulation_setup.signal_nets,
                        reference_list=simulation_setup.power_nets,
                        expansion_size=simulation_setup.cutout_subdesign_expansion,
                        use_round_corner=simulation_setup.cutout_subdesign_round_corner,
                        extent_type=simulation_setup.cutout_subdesign_type,
                    ):
                        self.logger.info("Cutout processed.")
                        old_cell = self.active_cell.FindByName(
                            self._db, self.edb.Cell.CellType.CircuitCell, old_cell_name
                        )
                        if old_cell:
                            old_cell.Delete()
                    else:  # pragma: no cover
                        self.logger.error("Cutout failed.")
                else:
                    self.logger.info("Cutting out using method: {0}".format(simulation_setup.cutout_subdesign_type))
                    self.create_cutout_multithread(
                        signal_list=simulation_setup.signal_nets,
                        reference_list=simulation_setup.power_nets,
                        expansion_size=simulation_setup.cutout_subdesign_expansion,
                        use_round_corner=simulation_setup.cutout_subdesign_round_corner,
                        extent_type=simulation_setup.cutout_subdesign_type,
                        use_pyaedt_extent_computing=True,
                        remove_single_pin_components=True,
                    )
                    self.logger.info("Cutout processed.")
            self.logger.info("Deleting existing ports.")
            map(lambda port: port.Delete(), list(self.active_layout.Terminals))
            map(lambda pg: pg.Delete(), list(self.active_layout.PinGroups))
            if simulation_setup.solver_type == SolverType.Hfss3dLayout:
                self.logger.info("Creating HFSS ports for signal nets.")
                for cmp in simulation_setup.components:
                    self.core_components.create_port_on_component(
                        cmp,
                        net_list=simulation_setup.signal_nets,
                        do_pingroup=False,
                        reference_net=simulation_setup.power_nets,
                        port_type=SourceType.CoaxPort,
                    )
                if not self.core_hfss.set_coax_port_attributes(simulation_setup):  # pragma: no cover
                    self.logger.error("Failed to configure coaxial port attributes.")
                self.logger.info("Number of ports: {}".format(self.core_hfss.get_ports_number()))
                self.logger.info("Configure HFSS extents.")
                if simulation_setup.trim_reference_size:  # pragma: no cover
                    self.logger.info(
                        "Trimming the reference plane for coaxial ports: {0}".format(
                            bool(simulation_setup.trim_reference_size)
                        )
                    )
                    self.core_hfss.trim_component_reference_size(simulation_setup)  # pragma: no cover
                self.core_hfss.configure_hfss_extents(simulation_setup)
                if not self.core_hfss.configure_hfss_analysis_setup(simulation_setup):
                    self.logger.error("Failed to configure HFSS simulation setup.")
            if simulation_setup.solver_type == SolverType.SiwaveSYZ:
                for cmp in simulation_setup.components:
                    self.core_components.create_port_on_component(
                        cmp,
                        net_list=simulation_setup.signal_nets,
                        do_pingroup=True,
                        reference_net=simulation_setup.power_nets,
                        port_type=SourceType.CircPort,
                    )
                self.logger.info("Configuring analysis setup.")
                if not self.core_siwave.configure_siw_analysis_setup(simulation_setup):  # pragma: no cover
                    self.logger.error("Failed to configure Siwave simulation setup.")

            if simulation_setup.solver_type == SolverType.SiwaveDC:
                self.core_components.create_source_on_component(simulation_setup.sources)
                if not self.core_siwave.configure_siw_analysis_setup(simulation_setup):  # pragma: no cover
                    self.logger.error("Failed to configure Siwave simulation setup.")
            self.save_edb()
            if not simulation_setup.open_edb_after_build and simulation_setup.output_aedb:
                self.close_edb()
                self.edbpath = legacy_name
                self.open_edb(True)
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
        return self.core_primitives.get_layout_statistics(evaluate_area=compute_area, net_list=None)

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
        """
        self.logger.reset_timer()
        if not common_reference:
            common_reference = list(
                set([i.reference_net_name for i in self.excitations.values() if i.reference_net_name])
            )
            if len(common_reference) > 1:
                self.logger.error("More than 1 reference found.")
            common_reference = common_reference[0]
        setList = [
            set(i.reference_object.get_connected_object_id_set())
            for i in self.excitations.values()
            if i.reference_net_name == common_reference
        ]

        # Get the set intersections for all the ID sets.
        iDintersection = set.intersection(*setList)
        self.logger.info_timer(
            "Terminal reference primitive IDs total intersections = {}\n\n".format(len(iDintersection))
        )

        # If the intersections are non-zero, the termimal references are connected.
        return True if len(iDintersection) > 0 else False

    @pyaedt_function_handler()
    def new_simulation_configuration(self, filename=None):
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
                if i.GetType() == self.edb.Utility.SimulationSetupType.kHFSS:
                    self._setups[i.GetName()] = HfssSimulationSetup(self, i.GetName(), i)
                elif i.GetType() == self.edb.Utility.SimulationSetupType.kSIWave:
                    self._setups[i.GetName()] = SiwaveSYZSimulationSetup(self, i.GetName(), i)
                elif i.GetType() == self.edb.Utility.SimulationSetupType.kSIWaveDCIR:
                    self._setups[i.GetName()] = SiwaveDCSimulationSetup(self, i.GetName(), i)
        return self._setups

    @property
    def hfss_setups(self):
        """Active HFSS setup in EDB.

        Returns
        -------
        Dict[str, :class:`pyaedt.edb_core.edb_data.hfss_simulation_setup_data.HfssSimulationSetup`]

        """
        return {i.name: i for i in self.setups if i.setup_type == "kHFSS"}

    @property
    def siwave_dc_setups(self):
        """Active Siwave DC IR Setups.

        Returns
        -------
        Dict[str, :class:`pyaedt.edb_core.edb_data.siwave_simulation_setup_data.SiwaveDCSimulationSetup`]
        """
        return {i.name: i for i in self.setups if i.setup_type == "kSIWave"}

    @property
    def siwave_ac_setups(self):
        """Active Siwave SYZ setups.

        Returns
        -------
        Dict[str, :class:`pyaedt.edb_core.edb_data.siwave_simulation_setup_data.SiwaveSYZSimulationSetup`]
        """
        return {i.name: i for i in self.setups if i.setup_type == "kSIWaveDCIR"}

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
        self._setups[name] = setup
        return setup

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
