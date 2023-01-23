"""
This module contains the ``Desktop`` class.

This module is used to initialize AEDT and the message manager for managing AEDT.

You can initialize this module before launching an app or
have the app automatically initialize it to the latest installed AEDT version.
"""

from __future__ import absolute_import  # noreorder

import datetime
import gc
import logging
import os
import pkgutil
import random
import re
import socket
import sys
import tempfile
import time
import traceback
import warnings

from pyaedt import is_ironpython
from pyaedt import pyaedt_logger

if os.name == "nt":
    IsWindows = True
else:
    IsWindows = False
    os.environ["ANS_NODEPCHECK"] = str(1)

if not IsWindows and is_ironpython:
    import subprocessdotnet as subprocess


else:
    import subprocess

from pyaedt import __version__
from pyaedt import pyaedt_function_handler
from pyaedt import settings
from pyaedt.generic.general_methods import _pythonver
from pyaedt.generic.general_methods import com_active_sessions
from pyaedt.generic.general_methods import grpc_active_sessions
from pyaedt.generic.general_methods import inside_desktop
from pyaedt.generic.general_methods import is_ironpython
from pyaedt.misc import list_installed_ansysem

pathname = os.path.dirname(__file__)

pyaedtversion = __version__

modules = [tup[1] for tup in pkgutil.iter_modules()]

if is_ironpython:
    _com = "ironpython"
elif IsWindows and "pythonnet" in modules:  # pragma: no cover
    _com = "pythonnet_v3"
else:
    _com = "gprc_v3"
    settings.use_grpc_api = True


def _check_grpc_port(port, machine_name=""):
    s = socket.socket()
    try:
        if not machine_name:
            machine_name = socket.getfqdn()
        s.connect((machine_name, port))
    except socket.error:
        return False
    else:
        s.close()
        return True


def _find_free_port(port_start=50001, port_end=60000):
    list_ports = random.sample(range(port_start, port_end), port_end - port_start)
    s = socket.socket()
    for port in list_ports:
        try:
            s.connect((socket.getfqdn(), port))
        except socket.error:
            return port
        else:
            s.close()
    return 0


def exception_to_desktop(ex_value, tb_data):  # pragma: no cover
    """Writes the trace stack to AEDT when a Python error occurs.

    The message is added to the AEDT global logger and to the log file (if present).

    Parameters
    ----------
    ex_value : str
        Type of the exception.
    tb_data : str
        Traceback data.

    """
    tb_trace = traceback.format_tb(tb_data)
    tblist = tb_trace[0].split("\n")
    pyaedt_logger.error(str(ex_value))
    for el in tblist:
        pyaedt_logger.error(el)


def _delete_objects():
    module = sys.modules["__main__"]
    try:
        del module.COMUtil
    except AttributeError:
        pass
    pyaedt_logger.remove_all_project_file_logger()
    try:
        del module.oDesktop
    except AttributeError:
        pass
    try:
        del module.pyaedt_initialized
    except AttributeError:
        pass
    try:
        del module.oAnsoftApplication
    except AttributeError:
        pass
    try:
        del module.desktop
    except AttributeError:
        pass
    gc.collect()


def release_desktop(close_projects=True, close_desktop=True):
    """Release the AEDT API.

    Parameters
    ----------
    close_projects : bool, optional
        Whether to close the AEDT projects open in the session. The default is ``True``.
    close_desktop : bool, optional
        Whether to close the active AEDT session. The default is ``True``.

    Returns
    -------
    bool
        ``True`` when successful, ``False`` when failed.

    """

    _main = sys.modules["__main__"]
    try:
        desktop = _main.oDesktop
        if close_projects:
            projects = desktop.GetProjectList()
            for project in projects:
                desktop.CloseProject(project)
        pid = _main.oDesktop.GetProcessID()
        if settings.aedt_version >= "2022.2" and settings.use_grpc_api and not is_ironpython:
            if _check_grpc_port(settings.port, settings.machine):
                import ScriptEnv

                if close_desktop:
                    ScriptEnv.Shutdown()
                else:
                    ScriptEnv.Release()
            _delete_objects()
            return True
        elif not inside_desktop:
            i = 0
            scopeID = 5
            while i <= scopeID:
                _main.COMUtil.ReleaseCOMObjectScope(_main.COMUtil.PInvokeProxyAPI, i)
                i += 1
        if close_desktop:
            try:
                os.kill(pid, 9)
                _delete_objects()
                return True
            except Exception:  # pragma: no cover
                warnings.warn("Something went wrong in closing AEDT.")
                return False
        _delete_objects()
        return True
    except AttributeError:
        _delete_objects()
        return False


def force_close_desktop():
    """Forcibly close all AEDT projects and shut down AEDT.

    Returns
    -------
    bool
        ``True`` when successful, ``False`` when failed.
    """
    Module = sys.modules["__main__"]
    pid = Module.oDesktop.GetProcessID()
    logger = logging.getLogger(__name__)

    if pid > 0:
        try:
            projects = Module.oDesktop.GetProjectList()
            for project in projects:
                Module.oDesktop.CloseProject(project)
        except:
            logger.warning("No projects are open. Closing the AEDT connection.")
        try:
            i = 0
            scopeID = 5
            while i <= scopeID:
                Module.COMUtil.ReleaseCOMObjectScope(Module.COMUtil.PInvokeProxyAPI, 0)
                i += 1
        except:
            logger.warning("No COM UTIL. Closing AEDT....")
        try:
            del Module.pyaedt_initialized
        except:
            pass
        try:
            os.kill(pid, 9)
            del Module.oDesktop
            successfully_closed = True
        except:
            pyaedt_logger.error("Something went wrong in closing AEDT.")
            successfully_closed = False
        finally:
            log = logging.getLogger("Global")
            handlers = log.handlers[:]
            for handler in handlers:
                handler.close()
                log.removeHandler(handler)
            return successfully_closed


def run_process(command, bufsize=None):
    """Run a process with a subprocess.

    Parameters
    ----------
    command : str
        Command to execute.
    bufsize : int, optional
        Buffer size. The default is ``None``.

    """
    if bufsize:
        return subprocess.call(command, bufsize=bufsize)
    else:
        return subprocess.call(command)


def get_version_env_variable(version_id):
    """Get the environment variable for the AEDT version.

    Parameters
    ----------
    version_id : str
        Full AEDT version number. For example, ``"2021.2"``.

    Returns
    -------
    str
        Environment variable for the version.

    Examples
    --------
    >>> from pyaedt import desktop
    >>> desktop.get_version_env_variable("2021.2")
    'ANSYSEM_ROOT212'

    """
    version_env_var = "ANSYSEM_ROOT"
    values = version_id.split(".")
    version = int(values[0][2:])
    release = int(values[1])
    if version < 20:
        if release < 3:
            version += 1
        else:
            release += 2
    version_env_var += str(version) + str(release)
    return version_env_var


class Desktop(object):
    """Provides the Ansys Electronics Desktop (AEDT) interface.

    Parameters
    ----------
    specified_version : str, optional
        Version of AEDT to use. The default is ``None``, in which case the
        active setup or latest installed version is used.
    non_graphical : bool, optional
        Whether to launch AEDT in non-graphical mode. The default
        is ``False``, in which case AEDT is launched in graphical mode.
        This parameter is ignored when a script is launched within AEDT.
    new_desktop_session : bool, optional
        Whether to launch an instance of AEDT in a new thread, even if
        another instance of the ``specified_version`` is active on the machine.
        The default is ``True``.
    close_on_exit : bool, optional
        Whether to close AEDT on exit. The default is ``True``.
    student_version : bool, optional
        Whether to open the AEDT student version. The default is
        ``False``.
    machine : str, optional
        Machine name to connect the oDesktop session to. This parameters works only in 2022 R2
        and later. The remote server must be up and running with the command
        `"ansysedt.exe -grpcsrv portnum"`. If the machine is `"localhost"`, the server also
        starts if not present.
    port : int, optional
        Port number on which to start the oDesktop communication on the already existing server.
        This parameter is ignored when creating a new server. It works only in 2022 R2 and
        later. The remote server must be up and running with the command `"ansysedt.exe -grpcsrv portnum"`.
    aedt_process_id : int, optional
        Process ID for the instance of AEDT to point PyAEDT at. The default is
        ``None``. This parameter is only used when ``new_desktop_session = False``.

    Examples
    --------
    Launch AEDT 2021 R1 in non-graphical mode and initialize HFSS.

    >>> import pyaedt
    >>> desktop = pyaedt.Desktop("2021.2", non_graphical=True)
    pyaedt INFO: pyaedt v...
    pyaedt INFO: Python version ...
    >>> hfss = pyaedt.Hfss(designname="HFSSDesign1")
    pyaedt INFO: Project...
    pyaedt INFO: Added design 'HFSSDesign1' of type HFSS.

    Launch AEDT 2021 R1 in graphical mode and initialize HFSS.

    >>> desktop = Desktop("2021.2")
    pyaedt INFO: pyaedt v...
    pyaedt INFO: Python version ...
    >>> hfss = pyaedt.Hfss(designname="HFSSDesign1")
    pyaedt INFO: No project is defined. Project...
    """

    def __init__(
        self,
        specified_version=None,
        non_graphical=False,
        new_desktop_session=True,
        close_on_exit=True,
        student_version=False,
        machine="",
        port=0,
        aedt_process_id=None,
    ):
        """Initialize desktop."""
        self._main = sys.modules["__main__"]
        self._main.interpreter = _com
        self.release_on_exit = close_on_exit
        self.close_on_exit = close_on_exit
        self._main.pyaedt_version = pyaedtversion
        self._main.interpreter_ver = _pythonver
        self._main.student_version = student_version
        self.machine = machine
        self.port = port
        self.aedt_process_id = aedt_process_id
        if is_ironpython:
            self._main.isoutsideDesktop = False
        else:
            self._main.isoutsideDesktop = True
        self.release_on_exit = True
        self.logfile = None

        self._logger = pyaedt_logger
        self._logger.info("using existing logger.")

        if "oDesktop" in dir():  # pragma: no cover
            self.release_on_exit = False
            self._main.oDesktop = oDesktop
            try:
                settings.non_graphical = oDesktop.GetIsNonGraphical()
            except:
                settings.non_graphical = non_graphical
        elif "oDesktop" in dir(self._main) and self._main.oDesktop is not None:  # pragma: no cover
            self.release_on_exit = False
            try:
                settings.non_graphical = self._main.oDesktop.GetIsNonGraphical()
            except:
                settings.non_graphical = non_graphical
        else:
            settings.non_graphical = non_graphical

            if "oDesktop" in dir(self._main):
                del self._main.oDesktop
            self._main.student_version, version_key, version = self._set_version(specified_version, student_version)
            if version_key < "2022.2":
                settings.use_grpc_api = False
            elif (
                version_key == "2022.2"
                and not self.port
                and not self.machine
                and settings.use_grpc_api is None
                and _com != "gprc_v3"
            ):
                settings.use_grpc_api = False
            elif settings.use_grpc_api is None or _com == "gprc_v3":
                settings.use_grpc_api = True
            if _com == "ironpython":  # pragma: no cover
                self._logger.info("Launching PyAEDT outside AEDT with IronPython.")
                self._init_ironpython(non_graphical, new_desktop_session, version)
            elif settings.use_grpc_api:
                settings.use_grpc_api = True
                self._init_cpython_new(non_graphical, new_desktop_session, version, self._main.student_version)
            elif _com == "pythonnet_v3":
                self._logger.info("Launching PyAEDT outside AEDT with CPython and PythonNET.")
                self._init_cpython(
                    non_graphical,
                    new_desktop_session,
                    version,
                    self._main.student_version,
                    version_key,
                    aedt_process_id,
                )
            else:
                from pyaedt.generic.clr_module import win32_client

                oAnsoftApp = win32_client.Dispatch(version)
                self._main.oDesktop = oAnsoftApp.GetAppDesktop()
                self._main.isoutsideDesktop = True
        self._set_logger_file()
        self._init_desktop()
        self._logger.info("pyaedt v%s", self._main.pyaedt_version)
        if not settings.remote_api:
            self._logger.info("Python version %s", sys.version)
        self.odesktop = self._main.oDesktop
        settings.aedt_version = self.odesktop.GetVersion()[0:6]
        settings.machine = self.machine
        settings.port = self.port
        self.aedt_process_id = self.odesktop.GetProcessID()  # bit of cleanup for consistency if used in future

        if _com == "ironpython":
            sys.path.append(
                os.path.join(self._main.sDesktopinstallDirectory, "common", "commonfiles", "IronPython", "DLLs")
            )

    def __enter__(self):
        return self

    def __exit__(self, ex_type, ex_value, ex_traceback):
        # Write the trace stack to the log file if an exception occurred in the main script.
        if ex_type:
            err = self._exception(ex_value, ex_traceback)
        if self.close_on_exit:
            self.release_desktop(close_projects=self.close_on_exit, close_on_exit=self.close_on_exit)

    @pyaedt_function_handler()
    def __getitem__(self, project_design_name):
        """Get the application interface object (Hfss, Icepak, Maxwell3D...) for a given project name and design name.

        Parameters
        ----------
        project_design_name : list
            Project and design name.

        Returns
        -------
        :class:Application interface
            Returns None if project and design name are not found.

        """
        from pyaedt import get_pyaedt_app

        if len(project_design_name) != 2:
            return None
        if isinstance(project_design_name[0], int) and project_design_name[0] < len(self.project_list()):
            projectname = self.project_list()[project_design_name[0]]
        elif isinstance(project_design_name[0], str) and project_design_name[0] in self.project_list():
            projectname = project_design_name[0]
        else:
            return None

        initial_oproject = self.odesktop.GetActiveProject()
        if initial_oproject.GetName() != projectname:
            self.odesktop.SetActiveProject(projectname)

        if isinstance(project_design_name[1], int) and project_design_name[1] < len(self.design_list()):
            designname = self.design_list()[project_design_name[1]]
        elif isinstance(project_design_name[1], str) and project_design_name[1] in self.design_list():
            designname = project_design_name[1]
        else:
            return None

        return get_pyaedt_app(projectname, designname)

    @property
    def install_path(self):
        """Installation path for AEDT."""
        version_key = self._main.AEDTVersion
        root = self._version_ids[version_key]
        return os.environ[root]

    @property
    def version_keys(self):
        """Version keys for AEDT."""

        self._version_keys = []
        self._version_ids = {}
        version_list = list_installed_ansysem()
        for version_env_var in version_list:
            if "ANSYSEMSV_ROOT" in version_env_var:
                current_version_id = version_env_var.replace("ANSYSEMSV_ROOT", "")
                student = True
            else:
                current_version_id = version_env_var.replace("ANSYSEM_ROOT", "")
                student = False
            try:
                version = int(current_version_id[0:2])
                release = int(current_version_id[2])
                if version < 20:
                    if release < 3:
                        version -= 1
                    else:
                        release -= 2
                if student:
                    v_key = "20{0}.{1}SV".format(version, release)
                    self._version_keys.append(v_key)
                    self._version_ids[v_key] = version_env_var
                else:
                    v_key = "20{0}.{1}".format(version, release)
                    self._version_keys.append(v_key)
                    self._version_ids[v_key] = version_env_var
            except:
                pass
        return self._version_keys

    @property
    def current_version(self):
        """Current AEDT version."""
        try:
            return self.version_keys[0]
        except (NameError, IndexError):
            return ""

    @property
    def current_version_student(self):
        """Current student AEDT version."""
        for version_key in self.version_keys:
            if "SV" in version_key:
                return version_key
        return ""

    def _init_desktop(self):
        self._main.AEDTVersion = self._main.oDesktop.GetVersion()[0:6]
        self._main.oDesktop.RestoreWindow()
        self._main.sDesktopinstallDirectory = self._main.oDesktop.GetExeDir()
        self._main.pyaedt_initialized = True
        settings.enable_desktop_logs = self._main.oDesktop.GetIsNonGraphical()

    def _set_version(self, specified_version, student_version):
        student_version_flag = False
        if specified_version:
            if float(specified_version) < 2021:
                if float(specified_version) < 2019:
                    raise ValueError("PyAEDT supports AEDT version 2021 R1 and later.")
                else:
                    warnings.warn(
                        """PyAEDT has limited capabilities when used with an AEDT version earlier than 2021 R1.
                        PyAEDT officially supports AEDT version 2021 R1 and later."""
                    )
            if student_version:
                specified_version += "SV"
                student_version_flag = True
            assert specified_version in self.version_keys, "Specified version {} is not known".format(specified_version)
            version_key = specified_version
        else:
            if student_version and self.current_version_student:
                version_key = self.current_version_student
                student_version_flag = True
            else:
                version_key = self.current_version
                student_version_flag = False
        if student_version and student_version_flag:
            version = "Ansoft.ElectronicsDesktop." + version_key[:-2]
        else:
            version = "Ansoft.ElectronicsDesktop." + version_key
        self._main.sDesktopinstallDirectory = os.getenv(self._version_ids[version_key])
        return student_version_flag, version_key, version

    def _init_ironpython(self, non_graphical, new_aedt_session, version):
        from pyaedt.generic.clr_module import _clr

        base_path = self._main.sDesktopinstallDirectory
        sys.path.append(base_path)
        sys.path.append(os.path.join(base_path, "PythonFiles", "DesktopPlugin"))
        _clr.AddReference("Ansys.Ansoft.CoreCOMScripting")
        AnsoftCOMUtil = __import__("Ansys.Ansoft.CoreCOMScripting")
        self.COMUtil = AnsoftCOMUtil.Ansoft.CoreCOMScripting.Util.COMUtil
        self._main.COMUtil = self.COMUtil
        StandalonePyScriptWrapper = AnsoftCOMUtil.Ansoft.CoreCOMScripting.COM.StandalonePyScriptWrapper
        if non_graphical or new_aedt_session:
            # forcing new thread to start in non-graphical
            oAnsoftApp = StandalonePyScriptWrapper.CreateObjectNew(non_graphical)
        else:
            oAnsoftApp = StandalonePyScriptWrapper.CreateObject(version)
        self._main.oDesktop = oAnsoftApp.GetAppDesktop()
        self._main.isoutsideDesktop = True
        sys.path.append(os.path.join(base_path, "common", "commonfiles", "IronPython", "DLLs"))

        return True

    def _run_student(self):
        DETACHED_PROCESS = 0x00000008
        pid = subprocess.Popen(
            [os.path.join(self._main.sDesktopinstallDirectory, "ansysedtsv.exe")], creationflags=DETACHED_PROCESS
        ).pid
        time.sleep(5)

    def _dispatch_win32(self, version):
        from pyaedt.generic.clr_module import win32_client

        o_ansoft_app = win32_client.Dispatch(version)
        self._main.oDesktop = o_ansoft_app.GetAppDesktop()
        self._main.isoutsideDesktop = True

    def _init_cpython(
        self,
        non_graphical,
        new_aedt_session,
        version,
        student_version,
        version_key,
        aedt_process_id=None,
    ):
        import pythoncom

        from pyaedt.generic.clr_module import _clr

        if os.name == "posix":
            raise Exception(
                "PyAEDT supports COM initialization in Windows only. To use in Linux, upgrade to AEDT 2022 R2 or later."
            )
        base_path = self._main.sDesktopinstallDirectory
        sys.path.append(base_path)
        sys.path.append(os.path.join(base_path, "PythonFiles", "DesktopPlugin"))
        launch_msg = "AEDT installation Path {}.".format(base_path)
        self.logger.info(launch_msg)
        _clr.AddReference("Ansys.Ansoft.CoreCOMScripting")
        AnsoftCOMUtil = __import__("Ansys.Ansoft.CoreCOMScripting")
        self.COMUtil = AnsoftCOMUtil.Ansoft.CoreCOMScripting.Util.COMUtil
        self._main.COMUtil = self.COMUtil
        StandalonePyScriptWrapper = AnsoftCOMUtil.Ansoft.CoreCOMScripting.COM.StandalonePyScriptWrapper
        self.logger.info("Launching AEDT with module PythonNET.")
        processID = []
        if IsWindows:
            processID = com_active_sessions(version, student_version, non_graphical)
        if student_version and not processID:  # Opens an instance if processID is an empty list
            self._run_student()
        elif non_graphical or new_aedt_session or not processID:
            # Force new object if no non-graphical instance is running or if there is not an already existing process.
            StandalonePyScriptWrapper.CreateObjectNew(non_graphical)
        else:
            StandalonePyScriptWrapper.CreateObject(version)
        processID2 = []
        if IsWindows:
            processID2 = com_active_sessions(version, student_version, non_graphical)
        proc = [i for i in processID2 if i not in processID]  # Looking for the "new" process
        if (
            not proc and (not new_aedt_session) and aedt_process_id
        ):  # if it isn't a new aedt session and a process ID is given
            proc = [aedt_process_id]
        elif not proc:
            proc = processID2
        if proc == processID2 and len(processID2) > 1:
            self._dispatch_win32(version)
        elif version_key >= "2021.2":
            if student_version:
                self.logger.info("{} Student version started with process ID {}.".format(version, proc[0]))
            else:
                self.logger.info("{} Started with process ID {}.".format(version, proc[0]))
            context = pythoncom.CreateBindCtx(0)
            running_coms = pythoncom.GetRunningObjectTable()
            monikiers = running_coms.EnumRunning()
            for monikier in monikiers:
                m = re.search(version[10:] + r"\.\d:" + str(proc[0]), monikier.GetDisplayName(context, monikier))
                if m:
                    obj = running_coms.GetObject(monikier)
                    self._main.isoutsideDesktop = True
                    from pyaedt.generic.clr_module import win32_client

                    self._main.oDesktop = win32_client.Dispatch(obj.QueryInterface(pythoncom.IID_IDispatch))
                    break
        else:
            self.logger.warning(
                "PyAEDT is not supported in AEDT versions earlier than 2021 R2. Trying to launch PyAEDT with PyWin32."
            )
            self._dispatch_win32(version)

    def _init_cpython_new(self, non_graphical, new_aedt_session, version, student_version):
        base_path = self._main.sDesktopinstallDirectory
        sys.path.append(base_path)
        sys.path.append(os.path.join(base_path, "PythonFiles", "DesktopPlugin"))
        if os.name == "posix":
            if os.environ.get("LD_LIBRARY_PATH"):
                os.environ["LD_LIBRARY_PATH"] = (
                    os.path.join(base_path, "defer") + os.pathsep + os.environ["LD_LIBRARY_PATH"]
                )
            else:
                os.environ["LD_LIBRARY_PATH"] = os.path.join(base_path, "defer")
            pyaedt_path = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
            os.environ["PATH"] = pyaedt_path + os.pathsep + os.environ["PATH"]
        import ScriptEnv

        launch_msg = "AEDT installation Path {}".format(base_path)
        self.logger.info(launch_msg)
        self.logger.info("Launching AEDT with the gRPC plugin.")
        if not self.machine or self.machine in [
            "localhost",
            "127.0.0.1",
            socket.getfqdn(),
            socket.getfqdn().split(".")[0],
        ]:
            self.machine = ""
        else:
            settings.remote_api = True

        if not self.port:
            if self.machine:
                self.logger.error("New Session of AEDT cannot be started on remote machine from Desktop Class.")
                self.logger.error("Either use port argument or start an rpc session to start AEDT on remote machine.")
                self.logger.error("Use client = pyaedt.common_rpc.client(machinename) to start a remote session.")
                self.logger.error("Use client.aedt(port) to start aedt on remote machine before connecting.")
            elif new_aedt_session:
                self.port = _find_free_port()
                self.logger.info("New AEDT session is starting on gRPC port %s", self.port)
            else:
                sessions = grpc_active_sessions(
                    version=version, student_version=student_version, non_graphical=non_graphical
                )
                if sessions:
                    self.port = sessions[0]
                    if len(sessions):
                        self.logger.info("Found active gRPC session on port %s", self.port)
                    else:
                        self.logger.warning(
                            "Multiple AEDT gRPC sessions are found. Setting the active session on port %s", self.port
                        )
                else:
                    self.port = _find_free_port()
                    self.logger.info("New AEDT session is starting on gRPC port %s", self.port)
        elif new_aedt_session and not _check_grpc_port(self.port, self.machine):
            self.logger.info("New AEDT session is starting on gRPC port %s", self.port)
        elif new_aedt_session:
            self.logger.warning("New Session of AEDT cannot be started on specified port because occupied.")
            self.port = _find_free_port()
            self.logger.info("New AEDT session is starting on gRPC port %s", self.port)
        elif _check_grpc_port(self.port, self.machine):
            self.logger.info("Connecting to AEDT session on gRPC port %s", self.port)
        else:
            self.logger.info("AEDT session is starting on gRPC port %s", self.port)
            new_aedt_session = True

        ScriptEnv._doInitialize(version, None, new_aedt_session, non_graphical, self.machine, self.port)

        if "oAnsoftApplication" in dir(self._main):
            self._main.isoutsideDesktop = True
            self._main.oDesktop = self._main.oAnsoftApplication.GetAppDesktop()
            _proc = self._main.oDesktop.GetProcessID()
            if new_aedt_session:
                message = "{} {} version started with process ID {}.".format(
                    version, "Student" if student_version else "", _proc
                )
                self.logger.info(message)

        else:
            self.logger.warning("The gRPC plugin is not supported in AEDT versions earlier than 2022 R2.")

    def _set_logger_file(self):
        # Set up the log file in the AEDT project directory
        if settings.remote_api:
            project_dir = tempfile.gettempdir()
        elif "oDesktop" in dir(self._main):
            project_dir = self._main.oDesktop.GetProjectDirectory()
        else:
            project_dir = tempfile.gettempdir()
        if settings.logger_file_path:
            self.logfile = settings.logger_file_path
        else:
            self.logfile = os.path.join(
                project_dir, "pyaedt{}.log".format(datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
            )

        return True

    @property
    def messenger(self):
        """Messenger manager for the AEDT logger."""
        return pyaedt_logger

    @property
    def logger(self):
        """AEDT logger."""
        return self._logger

    @pyaedt_function_handler()
    def project_list(self):
        """Get a list of projects.

        Returns
        -------
        list
            List of projects.

        """
        return list(self.odesktop.GetProjectList())

    @pyaedt_function_handler()
    def analyze_all(self, project=None, design=None):
        """Analyze all setups in a project.

        Parameters
        ----------
        project : str, optional
            Project name. The default is ``None``, in which case the active project
            is used.
        design : str, optional
            Design name. The default is ``None``, in which case all designs in
            the project are analyzed.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if not project:
            oproject = self.odesktop.GetActiveProject()
        else:
            oproject = self.odesktop.SetActiveProject(project)
        if oproject:
            if not design:
                oproject.AnalyzeAll()
            else:
                odesign = oproject.SetActiveDesign(design)
                if odesign:
                    odesign.AnalyzeAll()
        return True

    @pyaedt_function_handler()
    def clear_messages(self):
        """Clear all AEDT messages.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        self.odesktop.ClearMessages("", "", 3)
        return True

    @pyaedt_function_handler()
    def save_project(self, project_name=None, project_path=None):
        """Save the project.

        Parameters
        ----------
        project_name : str, optional
            Project name. The default is ``None``, in which case the active project
            is used.
        project_path : str, optional
            Full path to the project. The default is ``None``. If a path is
            provided, ``save as`` is used.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if not project_name:
            oproject = self.odesktop.GetActiveProject()
        else:
            oproject = self.odesktop.SetActiveProject(project_name)
        if project_path:
            oproject.SaveAs(project_path, True)
        else:
            oproject.Save()
        return True

    @pyaedt_function_handler()
    def copy_design(self, project_name=None, design_name=None, target_project=None):
        """Copy a design and paste it in an existing project or new project.

        .. deprecated:: 0.6.31
           Use :func:`copy_design_from` instead.

        Parameters
        ----------
        project_name : str, optional
            Project name. The default is ``None``, in which case the active project
            is used.
        design_name : str, optional
            Design name. The default is ``None``.
        target_project : str, optional
            Target project. The default is ``None``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if not project_name:  # pragma: no cover
            oproject = self.odesktop.GetActiveProject()
        else:  # pragma: no cover
            oproject = self.odesktop.SetActiveProject(project_name)
        if oproject:  # pragma: no cover
            if not design_name:
                odesign = oproject.GetActiveDesign()
            else:
                odesign = oproject.SetActiveDesign(design_name)
            if odesign:
                oproject.CopyDesign(design_name)
                if not target_project:
                    oproject.Paste()
                    return True
                else:
                    oproject_target = self.odesktop.SetActiveProject(target_project)
                    if not oproject_target:
                        oproject_target = self.odesktop.NewProject(target_project)
                        oproject_target.Paste()
                        return True
        return False

    @pyaedt_function_handler()
    def project_path(self, project_name=None):
        """Get the path to the project.

        Parameters
        ----------
        project_name : str, optional
            Project name. The default is ``None``, in which case the active
            project is used.

        Returns
        -------
        str
            Path to the project.

        """
        if not project_name:
            oproject = self.odesktop.GetActiveProject()
        else:
            oproject = self.odesktop.SetActiveProject(project_name)
        if oproject:
            return oproject.GetPath()
        return None

    @pyaedt_function_handler()
    def design_list(self, project=None):
        """Get a list of the designs.

        Parameters
        ----------
        project : str, optional
            Project name. The default is ``None``, in which case the active
            project is used.

        Returns
        -------
        list
            List of the designs.
        """

        updateddeslist = []
        if not project:
            oproject = self.odesktop.GetActiveProject()
        else:
            oproject = self.odesktop.SetActiveProject(project)
        if oproject:
            deslist = list(oproject.GetTopDesignList())
            for el in deslist:
                m = re.search(r"[^;]+$", el)
                updateddeslist.append(m.group(0))
        return updateddeslist

    @pyaedt_function_handler()
    def design_type(self, project_name=None, design_name=None):
        """Get the type of a design.

        Parameters
        ----------
        project_name : str, optional
            Project name. The default is ``None``, in which case the active
            project is used.
        design_name : str, optional
            Design name. The default is ``None``, in which case the active
            design is used.

        Returns
        -------
        str
            Design type.
        """
        if not project_name:
            oproject = self.odesktop.GetActiveProject()
        else:
            oproject = self.odesktop.SetActiveProject(project_name)
        if not oproject:
            return ""
        if not design_name:
            odesign = oproject.GetActiveDesign()
        else:
            odesign = oproject.SetActiveDesign(design_name)
        if odesign:
            return odesign.GetDesignType()
        return ""

    @property
    def personallib(self):
        """PersonalLib directory.

        Returns
        -------
        str
            Full absolute path for the ``PersonalLib`` directory.

        """
        return self.odesktop.GetPersonalLibDirectory()

    @property
    def userlib(self):
        """UserLib directory.

        Returns
        -------
        str
            Full absolute path for the ``UserLib`` directory.

        """
        return self.odesktop.GetUserLibDirectory()

    @property
    def syslib(self):
        """SysLib directory.

        Returns
        -------
        str
            Full absolute path for the ``SysLib`` directory.

        """
        return self.odesktop.GetLibraryDirectory()

    @property
    def aedt_version_id(self):
        """AEDT version.

        Returns
        -------
        str
            Version of AEDT.

        """
        version = self.odesktop.GetVersion().split(".")
        v = ".".join([version[0], version[1]])
        return v

    @property
    def src_dir(self):
        """Python source directory.

        Returns
        -------
        str
            Full absolute path for the ``python`` directory.

        """
        return os.path.dirname(os.path.realpath(__file__))

    @property
    def pyaedt_dir(self):
        """PyAEDT directory.

        Returns
        -------
        str
           Full absolute path for the ``pyaedt`` directory.

        """
        return os.path.realpath(os.path.join(self.src_dir, ".."))

    def _exception(self, ex_value, tb_data):
        """Write the trace stack to AEDT when a Python error occurs.

        Parameters
        ----------
        ex_value : str
            Type of the exception.
        tb_data : str
            Traceback data.

        Returns
        -------
        str
            Type of the exception.

        """
        tb_trace = traceback.format_tb(tb_data)
        tblist = tb_trace[0].split("\n")
        self.logger.error(str(ex_value))
        for el in tblist:
            self.logger.error(el)

        return str(ex_value)

    def release_desktop(self, close_projects=True, close_on_exit=True):
        """Release AEDT.

        Parameters
        ----------
        close_projects : bool, optional
            Whether to close the AEDT projects that are open in the session.
            The default is ``True``.
        close_on_exit : bool, optional
            Whether to close the active AEDT session on exiting AEDT.
            The default is ``True``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------
        >>> import pyaedt
        >>> desktop = pyaedt.Desktop("2021.2")
        pyaedt INFO: pyaedt v...
        pyaedt INFO: Python version ...
        >>> desktop.release_desktop(close_projects=False, close_on_exit=False) # doctest: +SKIP

        """
        result = release_desktop(close_projects, close_on_exit)
        self.odesktop = None
        return result

    def force_close_desktop(self):
        """Forcibly close all projects and shut down AEDT.

        .. deprecated:: 0.4.0
           Use :func:`desktop.close_desktop` instead.

        """

        warnings.warn(
            "`force_close_desktop` is deprecated. Use `close_desktop` instead.",
            DeprecationWarning,
        )

        force_close_desktop()

    def close_desktop(self):
        """Close all projects and shut down AEDT.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------
        >>> import pyaedt
        >>> desktop = pyaedt.Desktop("2021.2")
        pyaedt INFO: pyaedt v...
        pyaedt INFO: Python version ...
        >>> desktop.close_desktop() # doctest: +SKIP

        """
        return self.release_desktop(close_projects=True, close_on_exit=True)

    def enable_autosave(self):
        """Enable the autosave option.

        Examples
        --------
        >>> import pyaedt
        >>> desktop = pyaedt.Desktop("2021.2")
        pyaedt INFO: pyaedt v...
        pyaedt INFO: Python version ...
        >>> desktop.enable_autosave()

        """
        self._main.oDesktop.EnableAutoSave(True)

    def disable_autosave(self):
        """Disable the autosave option.

        Examples
        --------
        >>> import pyaedt
        >>> desktop = pyaedt.Desktop("2021.2")
        pyaedt INFO: pyaedt v...
        pyaedt INFO: Python version ...
        >>> desktop.disable_autosave()

        """
        self._main.oDesktop.EnableAutoSave(False)

    def change_license_type(self, license_type="Pool"):
        """Change the license type.

        Parameters
        ----------
        license_type : str, optional
            Type of the license. The options are ``"Pack"`` and ``"Pool"``.
            The default is ``"Pool"``.

        Returns
        -------
        bool
           ``True``.

            .. note::
               Because of an API limitation, this method returns ``True`` even when the key is wrong.

        """
        try:
            self._main.oDesktop.SetRegistryString("Desktop/Settings/ProjectOptions/HPCLicenseType", license_type)
            return True
        except:
            return False

    def change_registry_key(self, key_full_name, key_value):
        """Change an AEDT registry key to a new value.

        Parameters
        ----------
        key_full_name : str
            Full name of the AEDT registry key.
        key_value : str, int
            Value for the AEDT registry key.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if isinstance(key_value, str):
            try:
                self._main.oDesktop.SetRegistryString(key_full_name, key_value)
                self.logger.info("Key %s correctly changed.", key_full_name)
                return True
            except:
                self.logger.warning("Error setting up Key %s.", key_full_name)
                return False
        elif isinstance(key_value, int):
            try:
                self._main.oDesktop.SetRegistryInt(key_full_name, key_value)
                self.logger.info("Key %s correctly changed.", key_full_name)
                return True
            except:
                self.logger.warning("Error setting up Key %s.", key_full_name)
                return False
        else:
            self.logger.warning("Key value must be an integer or string.")
            return False

    def change_active_dso_config_name(self, product_name="HFSS", config_name="Local"):
        """Change a specific registry key to a new value.

        Parameters
        ----------
        product_name : str, optional
            Name of the tool to apply the active configuration to. The default is
            ``"HFSS"``.
        config_name : str, optional
            Name of the configuration to apply. The default is ``"Local"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        try:
            self.change_registry_key("Desktop/ActiveDSOConfigurations/{}".format(product_name), config_name)
            self.logger.info("Configuration Changed correctly to %s for %s.", config_name, product_name)
            return True
        except:
            self.logger.warning("Error Setting Up Configuration %s for %s.", config_name, product_name)
            return False

    def change_registry_from_file(self, registry_file, make_active=True):
        """Apply desktop registry settings from an ACF file.

        One way to get an ACF file is to export a configuration from the AEDT UI and then edit and reuse it.

        Parameters
        ----------
        registry_file : str
            Full path to the ACF file.
        make_active : bool, optional
            Whether to set the imported configuration as active. The default is ``True``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        try:
            self._main.oDesktop.SetRegistryFromFile(registry_file)
            if make_active:
                with open(registry_file, "r") as f:
                    for line in f:
                        stripped_line = line.strip()
                        if "ConfigName" in stripped_line:
                            config_name = stripped_line.split("=")
                        elif "DesignType" in stripped_line:
                            design_type = stripped_line.split("=")
                            break
                    if design_type and config_name:
                        self.change_registry_key(design_type[1], config_name[1])
            return True
        except:
            return False
