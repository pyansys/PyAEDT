"""This module contains the ``Desktop`` class.
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
import re
import shutil
import socket
import sys
import tempfile
import threading
import time
import traceback
import warnings

from pyaedt import is_ironpython, is_linux, is_windows
from pyaedt.aedt_logger import pyaedt_logger
from pyaedt.generic.general_methods import generate_unique_name

if is_linux:
    os.environ["ANS_NODEPCHECK"] = str(1)

if is_linux and is_ironpython:
    import subprocessdotnet as subprocess
else:
    import subprocess

from pyaedt import __version__, pyaedt_function_handler, settings
from pyaedt.generic.desktop_sessions import _desktop_sessions
from pyaedt.generic.general_methods import (
    active_sessions,
    com_active_sessions,
    get_string_version,
    grpc_active_sessions,
    inside_desktop,
    is_ironpython,
    open_file,
)
from pyaedt.misc import current_student_version, current_version, installed_versions

pathname = os.path.dirname(__file__)

pyaedtversion = __version__

modules = [tup[1] for tup in pkgutil.iter_modules()]


@pyaedt_function_handler()
def launch_aedt(full_path, non_graphical, port, student_version, first_run=True):
    """Launch AEDT in gRPC mode."""

    def launch_desktop_on_port():
        command = [full_path, "-grpcsrv", str(port)]
        if non_graphical:
            command.append("-ng")
        if settings.wait_for_license:
            command.append("-waitforlicense")
        my_env = os.environ.copy()
        for env, val in settings.aedt_environment_variables.items():
            my_env[env] = val
        if is_linux:  # pragma: no cover
            command.append("&")
            with subprocess.Popen(command, env=my_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL) as p:
                p.wait()
        else:
            with subprocess.Popen(
                " ".join(command), env=my_env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            ) as p:
                p.wait()

    _aedt_process_thread = threading.Thread(target=launch_desktop_on_port)
    _aedt_process_thread.daemon = True
    _aedt_process_thread.start()
    timeout = settings.desktop_launch_timeout
    k = 0
    while not _check_grpc_port(port):
        if k > timeout:  # pragma: no cover
            active_s = active_sessions(student_version=student_version)
            for pid in active_s:
                if port == active_s[pid]:
                    try:
                        os.kill(pid, 9)
                    except (OSError, PermissionError):
                        pass
            if first_run:
                port = _find_free_port()
                return launch_aedt(full_path, non_graphical, port, student_version, first_run=False)
            return False, _find_free_port()
        time.sleep(1)
        k += 1
    return True, port


def launch_aedt_in_lsf(non_graphical, port):  # pragma: no cover
    """Launch AEDT in LSF in GRPC mode."""
    if settings.lsf_queue:
        command = [
            "bsub",
            "-n",
            str(settings.lsf_num_cores),
            "-R",
            '"rusage[mem={}]"'.format(settings.lsf_ram),
            "-queue {}".format(settings.lsf_queue),
            "-Is",
            settings.lsf_aedt_command,
            "-grpcsrv",
            str(port),
        ]
    else:
        command = [
            "bsub",
            "-n",
            str(settings.lsf_num_cores),
            "-R",
            '"rusage[mem={}]"'.format(settings.lsf_ram),
            "-Is",
            settings.lsf_aedt_command,
            "-grpcsrv",
            str(port),
        ]
    if non_graphical:
        command.append("-ng")
    if settings.wait_for_license:
        command.append("-waitforlicense")
    print(command)
    p = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    timeout = settings.lsf_timeout
    i = 0
    while i < timeout:
        err = p.stderr.readline().strip().decode("utf-8", "replace")
        m = re.search(r"<<Starting on (.+?)>>", err)
        if m:
            aedt_startup_timeout = 120
            k = 0
            while not _check_grpc_port(port, machine_name=m.group(1)):
                if k > aedt_startup_timeout:
                    return False, err
                time.sleep(1)
                k += 1
            return True, m.group(1)
        i += 1
        time.sleep(1)
    return False, err


def _check_grpc_port(port, machine_name=""):
    s = socket.socket()
    try:
        if not machine_name:
            machine_name = "127.0.0.1"
        s.connect((machine_name, port))
    except socket.error:
        success = False
    else:
        success = True
    finally:
        s.close()
    return success


def _find_free_port():
    from contextlib import closing

    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


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
    settings._aedt_version = None
    settings.remote_api = False
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
    try:
        del module.sDesktopinstallDirectory
    except AttributeError:
        pass
    try:
        del module.isoutsideDesktop
    except AttributeError:
        pass
    try:
        del module.AEDTVersion
    except AttributeError:
        pass
    try:
        del sys.modules["glob"]
    except:
        pass
    gc.collect()


@pyaedt_function_handler()
def _close_aedt_application(close_desktop, pid, is_grpc_api):
    """Release the AEDT API.

    Parameters
    ----------
    close_desktop : bool
        Whether to close the active AEDT session.
    pid : int
        Process ID of the desktop app that is being closed.
    is_grpc_api : bool
        Whether the active AEDT session is gRPC or COM.

    Returns
    -------
    bool
        ``True`` when successful, ``False`` when failed.

    """
    _main = sys.modules["__main__"]
    if settings.remote_rpc_session or (settings.aedt_version >= "2022.2" and is_grpc_api and not is_ironpython):
        if close_desktop:
            try:
                _main.oDesktop.QuitApplication()
            except:  # pragma: no cover
                warnings.warn("Something went wrong closing AEDT. Exception in `_main.oDesktop.QuitApplication()`.")
                pass
            try:
                _main.oDesktop.QuitApplication()
            except:  # pragma: no cover
                pass
        else:
            try:
                import pyaedt.generic.grpc_plugin as StandalonePyScriptWrapper

                StandalonePyScriptWrapper.Release()
            except:  # pragma: no cover
                warnings.warn(
                    "Something went wrong releasing AEDT. Exception in `StandalonePyScriptWrapper.Release()`."
                )
                pass
    elif not inside_desktop:
        if close_desktop:
            try:
                os.kill(pid, 9)
            except:  # pragma: no cover
                warnings.warn("Something went wrong closing AEDT. Exception in `os.kill(pid, 9)`.")
                return False
        else:
            try:
                scopeID = 0
                while scopeID <= 5:
                    _main.COMUtil.ReleaseCOMObjectScope(_main.COMUtil.PInvokeProxyAPI, scopeID)
                    scopeID += 1
            except:
                logging.warning(
                    "Something went wrong releasing AEDT. Exception in `_main.COMUtil.ReleaseCOMObjectScope`."
                )
                pass
    if not settings.remote_rpc_session and not is_ironpython and close_desktop:
        timeout = 10
        while pid in active_sessions():
            time.sleep(1)
            timeout -= 1
            if timeout == 0:
                try:
                    os.kill(pid, 9)
                except:  # pragma: no cover
                    warnings.warn("Something went wrong closing AEDT. Exception in `os.kill(pid, 9)` after timeout.")
                    return False
                break
    return True


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


def is_student_version(oDesktop):
    edt_root = os.path.normpath(oDesktop.GetExeDir())
    if is_windows and os.path.isdir(edt_root):
        if any("ansysedtsv" in fn.lower() for fn in os.listdir(edt_root)):
            return True
    return False


def _init_desktop_from_design(*args, **kwargs):
    """Distinguishes if the ``Desktop`` class is initialized internally from the ``Design``
    class or directly from the user. For example, ``desktop=Desktop()``).
    """
    Desktop._invoked_from_design = True
    return Desktop(*args, **kwargs)


class Desktop(object):
    """Provides the Ansys Electronics Desktop (AEDT) interface.

    Parameters
    ----------
    specified_version : str, int, float, optional
        Version of AEDT to use. The default is ``None``, in which case the
        active setup or latest installed version is used.
        Examples of input values are ``232``, ``23.2``,``2023.2``,``"2023.2"``.
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
        This option is used only when Desktop is used in a context manager (``with`` statement).
        If Desktop is used outside a context manager, see the ``release_desktop`` arguments.
    student_version : bool, optional
        Whether to open the AEDT student version. The default is
        ``False``.
    machine : str, optional
        Machine name to connect the oDesktop session to. This parameter works only in 2022 R2
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
    Launch AEDT 2023 R1 in non-graphical mode and initialize HFSS.

    >>> import pyaedt
    >>> desktop = pyaedt.Desktop(specified_version="2023.2", non_graphical=True)
    PyAEDT INFO: pyaedt v...
    PyAEDT INFO: Python version ...
    >>> hfss = pyaedt.Hfss(designname="HFSSDesign1")
    PyAEDT INFO: Project...
    PyAEDT INFO: Added design 'HFSSDesign1' of type HFSS.

    Launch AEDT 2023 R2 in graphical mode and initialize HFSS.

    >>> desktop = Desktop(232)
    PyAEDT INFO: pyaedt v...
    PyAEDT INFO: Python version ...
    >>> hfss = pyaedt.Hfss(designname="HFSSDesign1")
    PyAEDT INFO: No project is defined. Project...
    """

    # _sessions = {}
    _invoked_from_design = False

    def __new__(cls, *args, **kwargs):
        # The following commented lines will be useful when we will need to search among multiple saved desktop.
        # specified_version = kwargs.get("specified_version") or None if not args else args[0]
        # new_desktop_session = kwargs.get("new_desktop_session") or True if (not args or len(args)<3) else args[2]
        # student_version = kwargs.get("student_version") or False if (not args or len(args)<5) else args[4]
        # machine = kwargs.get("machine") or "" if (not args or len(args)<6) else args[5]
        # port = kwargs.get("port") or 0 if (not args or len(args)<7) else args[6]
        # aedt_process_id = kwargs.get("aedt_process_id") or None if (not args or len(args)<8) else args[7]

        if len(_desktop_sessions.keys()) > 0:
            sessions = list(_desktop_sessions.keys())
            try:
                # for the moment aedt supports only one desktop, which is saved in sessions[0]
                process_id = _desktop_sessions[sessions[0]].odesktop.GetProcessID()
                print("Returning found desktop with PID {}!".format(process_id))
                cls._invoked_from_design = False
                return _desktop_sessions[sessions[0]]
            except:
                del _desktop_sessions[sessions[0]]
                print("Initializing new desktop!")
                return object.__new__(cls)
        else:
            print("Initializing new desktop!")
            return object.__new__(cls)

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
        if aedt_process_id:  # pragma no cover
            aedt_process_id = int(aedt_process_id)
        if getattr(self, "_initialized", None) is not None and self._initialized:
            return
        else:
            self._initialized = True
        self._initialized_from_design = True if Desktop._invoked_from_design else False
        Desktop._invoked_from_design = False

        self._connected_designs = 0

        """Initialize desktop."""
        self.launched_by_pyaedt = False

        # Used in unit tests. The ``PYAEDT_NON_GRAPHICAL`` environment variable overrides
        # the ``non_graphical`` argument.
        if os.getenv("PYAEDT_NON_GRAPHICAL", None) is not None:
            non_graphical = os.getenv("PYAEDT_NON_GRAPHICAL", "false").lower() in ("true", "1", "t")
        # Used in Examples generation to force the desktop opening
        if os.getenv("PYAEDT_DOC_GENERATION", "False").lower() in ("true", "1", "t"):
            new_desktop_session = True
        # Used in toolkit scripts. The ``PYAEDT_SCRIPT_PROCESS_ID`` environment variable overrides
        # the ``aedt_process_id`` argument.
        if os.getenv("PYAEDT_SCRIPT_PROCESS_ID", None):
            aedt_process_id = int(os.getenv("PYAEDT_SCRIPT_PROCESS_ID"))
        # Used in toolkit scripts. The ``PYAEDT_SCRIPT_VERSION`` environment variable overrides
        # the ``specified_version`` argument.
        if os.getenv("PYAEDT_SCRIPT_VERSION", None):
            specified_version = str(os.getenv("PYAEDT_SCRIPT_VERSION"))

        self._main = sys.modules["__main__"]
        self.close_on_exit = close_on_exit
        self.machine = machine
        self.port = port
        self.non_graphical = non_graphical
        self.is_grpc_api = None

        self.logfile = None

        self._logger = pyaedt_logger
        if settings.enable_screen_logs:
            self._logger.enable_stdout_log()
        else:
            self._logger.disable_stdout_log()
        if settings.enable_file_logs:
            self._logger.enable_log_on_file()
        else:
            self._logger.disable_log_on_file()
        if settings.enable_desktop_logs and not non_graphical:
            self._logger.enable_desktop_log()
        else:
            self._logger.disable_desktop_log()
        if settings.enable_debug_logger:
            self._logger.info("Debug logger is enabled. PyAEDT methods will be logged.")
        else:
            self._logger.info("Debug logger is disabled. PyAEDT methods will not be logged.")
        student_version_flag, version_key, version = self._assert_version(specified_version, student_version)

        # start the AEDT opening decision tree
        # starting_mode can be one of these: "grpc", "com", "ironpython", "console_in", "console_out"
        if "oDesktop" in dir():  # pragma: no cover
            # we are inside the AEDT Ironpython console
            starting_mode = "console_in"
        elif "oDesktop" in dir(self._main) and self._main.oDesktop is not None:  # pragma: no cover
            # we are inside a python console outside AEDT (toolkit)
            starting_mode = "console_out"
        elif is_linux:
            starting_mode = "grpc"
        elif is_windows and "pythonnet" not in modules:
            starting_mode = "grpc"
        elif settings.remote_rpc_session:
            starting_mode = "grpc"
        elif is_ironpython:
            starting_mode = "ironpython"
        elif aedt_process_id and not new_desktop_session and not is_ironpython:  # pragma: no cover
            # connecting to an existing session has the precedence over use_grpc_api user preference
            sessions = active_sessions(
                version=specified_version, student_version=student_version_flag, non_graphical=non_graphical
            )
            self.logger.info(sessions)
            if aedt_process_id in sessions:
                if sessions[aedt_process_id] != -1:
                    self.port = sessions[aedt_process_id]
                    starting_mode = "grpc"
                else:
                    starting_mode = "com"
            else:
                raise ValueError(
                    "The version specified ({}) doesn't correspond to the pid specified ({})".format(
                        specified_version, aedt_process_id
                    )
                )
        elif float(version_key[0:6]) < 2022.2:
            starting_mode = "com"
        elif float(version_key[0:6]) == 2022.2:
            if self.machine and self.port:
                starting_mode = "grpc"  # if the machine and port is specified, user wants to use gRPC
            elif settings.use_grpc_api is None:
                starting_mode = "com"  # default if user doesn't specify use_grpc_api
            else:
                starting_mode = "grpc" if settings.use_grpc_api else "com"
        elif float(version_key[0:6]) > 2022.2:
            if settings.use_grpc_api is None:
                starting_mode = "grpc"  # default if user doesn't specify use_grpc_api
            else:
                starting_mode = "grpc" if settings.use_grpc_api else "com"
        else:  # pragma: no cover
            # it should not arrive here, it means that there is a starting case not covered by the decision tree
            raise Exception("Unsupported AEDT starting mode")

        # Starting AEDT
        if "console" in starting_mode:
            # technically not a startup mode, we have just to load oDesktop
            self.close_on_exit = False
            try:
                self.non_graphical = oDesktop.GetIsNonGraphical()
            except:  # pragma: no cover
                self.non_graphical = non_graphical
            self.is_grpc_api = False
            settings.aedt_version = self._main.oDesktop.GetVersion()[0:6]
            if starting_mode == "console_in":
                self._main.oDesktop = oDesktop
        else:
            settings.aedt_version = version_key
            if "oDesktop" in dir(self._main):
                del self._main.oDesktop
            if starting_mode == "ironpython":
                self._logger.info("Launching PyAEDT outside AEDT with IronPython.")
                self._init_ironpython(non_graphical, new_desktop_session, version)
            elif starting_mode == "com":
                self._logger.info("Launching PyAEDT outside AEDT with CPython and PythonNET.")
                self._init_dotnet(
                    non_graphical,
                    new_desktop_session,
                    version,
                    student_version_flag,
                    version_key,
                    aedt_process_id,
                )
            elif starting_mode == "grpc":
                self._logger.info("Launching PyAEDT outside AEDT with gRPC plugin.")
                self._init_grpc(non_graphical, new_desktop_session, version, student_version_flag, version_key)

        self._set_logger_file()
        settings.enable_desktop_logs = not self.non_graphical
        self._init_desktop()
        self._logger.info("pyaedt v%s", self._main.pyaedt_version)
        if not settings.remote_api:
            self._logger.info("Python version %s", sys.version)
        self.odesktop = self._main.oDesktop

        current_pid = int(self.odesktop.GetProcessID())
        if aedt_process_id and not new_desktop_session and aedt_process_id != current_pid:
            raise Exception(
                "AEDT started a new session instead of connecting to the session with pid: {}".format(aedt_process_id)
            )
        self.aedt_process_id = current_pid

        current_is_student = is_student_version(self._main.oDesktop)
        if student_version ^ current_is_student:
            self._logger.warning(
                "AEDT started as {} version, but requested as {} version.".format(
                    "Student" if current_is_student else "Regular", "Student" if student_version else "Regular"
                )
            )
        self.student_version = current_is_student

        self.aedt_version_id = self._main.oDesktop.GetVersion()[0:6]

        self._logger.info("AEDT %s Build Date %s", self.odesktop.GetVersion(), self.odesktop.GetBuildDateTimeString())

        if is_ironpython:
            sys.path.append(
                os.path.join(self._main.sDesktopinstallDirectory, "common", "commonfiles", "IronPython", "DLLs")
            )

        # save the current desktop session in the database
        _desktop_sessions[self.aedt_process_id] = self

    def __enter__(self):
        return self

    def __exit__(self, ex_type, ex_value, ex_traceback):
        # Write the trace stack to the log file if an exception occurred in the main script.
        if ex_type:
            err = self._exception(ex_value, ex_traceback)
        if self.close_on_exit or not is_ironpython:
            self.release_desktop(close_projects=self.close_on_exit, close_on_exit=self.close_on_exit)

    @pyaedt_function_handler()
    def __getitem__(self, project_design_name):
        """Get the application interface object (Hfss, Icepak, Maxwell3D...) for a given project name and design name.

        Parameters
        ----------
        project_design_name : List
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
        return installed_versions()[version_key]

    @property
    def current_version(self):
        """Current AEDT version."""
        return current_version()

    @property
    def current_student_version(self):
        """Current AEDT student  version."""
        return current_student_version()

    @property
    def installed_versions(self):
        """Dictionary of AEDT versions installed on the system and their installation paths."""
        return installed_versions()

    def _init_desktop(self):
        # run it after the settings.non_graphical is set
        self._main.pyaedt_version = pyaedtversion
        self._main.AEDTVersion = self._main.oDesktop.GetVersion()[0:6]
        self._main.oDesktop.RestoreWindow()
        self._main.sDesktopinstallDirectory = self._main.oDesktop.GetExeDir()
        self._main.pyaedt_initialized = True

    def _assert_version(self, specified_version, student_version):
        # avoid evaluating the env variables multiple times
        if settings.remote_rpc_session:
            try:
                version = "Ansoft.ElectronicsDesktop." + settings.remote_rpc_session.aedt_version[0:6]
                return settings.remote_rpc_session.student_version, settings.remote_rpc_session.aedt_version, version
            except:
                return False, "", ""
        self_current_version = self.current_version
        self_current_student_version = self.current_student_version

        if current_version == "":
            raise Exception("AEDT is not installed on your system. Install AEDT version 2022 R2 or higher.")
        if not specified_version:
            if student_version and self_current_student_version:
                specified_version = self_current_student_version
            elif student_version and self_current_version:
                specified_version = self_current_version
                student_version = False
                self.logger.warning("AEDT Student Version not found on the system. Using regular version.")
            else:
                specified_version = self_current_version
                if "SV" in specified_version:
                    student_version = True
                    self.logger.warning("Only AEDT Student Version found on the system. Using Student Version.")
        elif student_version:
            specified_version += "SV"
        specified_version = get_string_version(specified_version)

        if float(specified_version[0:6]) < 2019:
            raise ValueError("PyAEDT supports AEDT version 2021 R1 and later. Recommended version is 2022 R2 or later.")
        elif float(specified_version[0:6]) < 2022.2:
            warnings.warn(
                """PyAEDT has limited capabilities when used with an AEDT version earlier than 2022 R2.
                Update your AEDT installation to 2022 R2 or later."""
            )
        if specified_version not in self.installed_versions:
            raise ValueError(
                "Specified version {}{} is not installed on your system".format(
                    specified_version[0:6], " Student Version" if student_version else ""
                )
            )

        version = "Ansoft.ElectronicsDesktop." + specified_version[0:6]
        self._main.sDesktopinstallDirectory = self.installed_versions[specified_version]
        return student_version, specified_version, version

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
        self.is_grpc_api = False

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

    def _init_dotnet(
        self,
        non_graphical,
        new_aedt_session,
        version,
        student_version,
        version_key,
        aedt_process_id=None,
    ):  # pragma: no cover
        import pythoncom

        if is_linux:
            raise Exception(
                "PyAEDT supports COM initialization in Windows only. To use in Linux, upgrade to AEDT 2022 R2 or later."
            )
        base_path = self._main.sDesktopinstallDirectory
        sys.path.insert(0, base_path)
        sys.path.insert(0, os.path.join(base_path, "PythonFiles", "DesktopPlugin"))
        launch_msg = "AEDT installation Path {}.".format(base_path)
        self.logger.info(launch_msg)
        self.logger.info("Launching AEDT with COM plugin using PythonNET.")
        processID = []
        if is_windows:
            processID = com_active_sessions(version, student_version, non_graphical)
        if student_version and not processID:  # Opens an instance if processID is an empty list
            self._run_student()
        elif non_graphical or new_aedt_session or not processID:
            # Force new object if no non-graphical instance is running or if there is not an already existing process.
            self._initialize(non_graphical=non_graphical, new_session=True, is_grpc=False, version=version_key)
        else:
            self._initialize(new_session=False, is_grpc=False, version=version_key)
        processID2 = []
        if is_windows:
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
                self.logger.info("AEDT {} Student version started with process ID {}.".format(version_key, proc[0]))
            elif aedt_process_id:
                self.logger.info("Connecting to AEDT session with process ID {}.".format(proc[0]))
            else:
                self.logger.info("AEDT {} Started with process ID {}.".format(version_key, proc[0]))
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
        # we should have a check here to see if AEDT is really started
        self.is_grpc_api = False

    def _initialize(
        self,
        machine="",
        port=0,
        non_graphical=False,
        new_session=False,
        version=None,
        is_grpc=True,
    ):
        if not is_grpc:
            from pyaedt.generic.clr_module import _clr

            _clr.AddReference("Ansys.Ansoft.CoreCOMScripting")
            AnsoftCOMUtil = __import__("Ansys.Ansoft.CoreCOMScripting")
            self.COMUtil = AnsoftCOMUtil.Ansoft.CoreCOMScripting.Util.COMUtil
            self._main.COMUtil = self.COMUtil
            StandalonePyScriptWrapper = AnsoftCOMUtil.Ansoft.CoreCOMScripting.COM.StandalonePyScriptWrapper
            if non_graphical or new_session:
                self.launched_by_pyaedt = True
                return StandalonePyScriptWrapper.CreateObjectNew(non_graphical)
            else:
                return StandalonePyScriptWrapper.CreateObject(version)
        else:
            base_path = self._main.sDesktopinstallDirectory
            sys.path.insert(0, base_path)
            sys.path.insert(0, os.path.join(base_path, "PythonFiles", "DesktopPlugin"))
            if is_linux:
                pyaedt_path = os.path.realpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
                os.environ["PATH"] = pyaedt_path + os.pathsep + os.environ["PATH"]
            os.environ["DesktopPluginPyAEDT"] = os.path.join(
                self._main.sDesktopinstallDirectory, "PythonFiles", "DesktopPlugin"
            )
            launch_msg = "AEDT installation Path {}".format(base_path)
            self.logger.info(launch_msg)
            import pyaedt.generic.grpc_plugin as StandalonePyScriptWrapper

            if new_session:
                self.launched_by_pyaedt = new_session
            return StandalonePyScriptWrapper.CreateAedtApplication(machine, port, non_graphical, new_session)

    def _init_grpc(self, non_graphical, new_aedt_session, version, student_version, version_key):
        self.logger.info("Launching AEDT using the gRPC plugin.")
        if settings.remote_rpc_session:  # pragma: no cover
            settings.remote_api = True
            if not self.machine:
                try:
                    self.machine = settings.remote_rpc_session.server_name
                except:
                    pass
            if not self.port:
                try:
                    self.port = settings.remote_rpc_session.port
                except:
                    pass
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
                    if len(sessions) == 1:
                        self.logger.info("Found active AEDT gRPC session on port %s", self.port)
                    else:
                        self.logger.warning(
                            "Multiple AEDT gRPC sessions are found. Setting the active session on port %s", self.port
                        )
                else:
                    if is_windows:  # pragma: no cover
                        if com_active_sessions(
                            version=version, student_version=student_version, non_graphical=non_graphical
                        ):
                            # settings.use_grpc_api = False
                            self.logger.info("No AEDT gRPC found. Found active COM Sessions.")
                            return self._init_dotnet(
                                non_graphical, new_aedt_session, version, student_version, version_key
                            )
                    self.port = _find_free_port()
                    self.logger.info("New AEDT session is starting on gRPC port %s", self.port)
                    new_aedt_session = True
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

        if new_aedt_session and settings.use_lsf_scheduler and is_linux:  # pragma: no cover
            out, self.machine = launch_aedt_in_lsf(non_graphical, self.port)
            if out:
                self.launched_by_pyaedt = True
                oApp = self._initialize(
                    is_grpc=True, machine=self.machine, port=self.port, new_session=False, version=version_key
                )
            else:
                self.logger.error("Failed to start LSF job on machine: %s.", self.machine)
                return
        elif new_aedt_session:
            installer = os.path.join(self._main.sDesktopinstallDirectory, "ansysedt")
            if student_version:  # pragma: no cover
                installer = os.path.join(self._main.sDesktopinstallDirectory, "ansysedtsv")
            if not is_linux:
                if student_version:  # pragma: no cover
                    installer = os.path.join(self._main.sDesktopinstallDirectory, "ansysedtsv.exe")
                else:
                    installer = os.path.join(self._main.sDesktopinstallDirectory, "ansysedt.exe")

            out, self.port = launch_aedt(installer, non_graphical, self.port, student_version)
            self.launched_by_pyaedt = True
            oApp = self._initialize(
                is_grpc=True,
                non_graphical=non_graphical,
                machine=self.machine,
                port=self.port,
                new_session=not out,
                version=version_key,
            )
        else:
            oApp = self._initialize(
                is_grpc=True,
                non_graphical=non_graphical,
                machine=self.machine,
                port=self.port,
                new_session=new_aedt_session,
                version=version_key,
            )
        if oApp:
            self._main.isoutsideDesktop = True
            self._main.oDesktop = oApp.GetAppDesktop()
            _proc = self._main.oDesktop.GetProcessID()
            self.is_grpc_api = True
            if new_aedt_session:
                message = "{}{} version started with process ID {}.".format(
                    version, " Student" if student_version else "", _proc
                )
                self.logger.info(message)

        else:
            self.logger.error("Failed to connect to AEDT using gRPC plugin.")
            self.logger.error("Check installation, license and environment variables.")

    def _set_logger_file(self):
        # Set up the log file in the AEDT project directory
        if settings.logger_file_path:
            self.logfile = settings.logger_file_path
        else:
            if settings.remote_api or settings.remote_rpc_session:
                project_dir = tempfile.gettempdir()
            elif "oDesktop" in dir(self._main):
                project_dir = self._main.oDesktop.GetProjectDirectory()
            else:
                project_dir = tempfile.gettempdir()
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
        List
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
        List
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
        """Get the type of design.

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

    @pyaedt_function_handler()
    def load_project(self, project_file, design_name=None):
        """Open an AEDT project based on a project and optional design.

        Parameters
        ----------
        project_file : str
            Full path and name for the project.
        design_name : str, optional
            Design name. The default is ``None``.

        Returns
        -------
        :def :`pyaedt.Hfss`
            Any of the PyAEDT App initialized.

        References
        ----------
        >>> oDesktop.OpenProject

        """
        proj = self.odesktop.OpenProject(project_file)
        if proj:
            active_design = proj.GetActiveDesign()
            if design_name and design_name in proj.GetChildNames():  # pragma: no cover
                return self[[proj.GetName(), design_name]]
            elif active_design:
                return self[[proj.GetName(), active_design.GetName()]]
            return True
        else:  # pragma: no cover
            return False

    @pyaedt_function_handler()
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
        PyAEDT INFO: pyaedt v...
        PyAEDT INFO: Python version ...
        >>> desktop.release_desktop(close_projects=False, close_on_exit=False) # doctest: +SKIP

        """
        if close_projects:
            projects = self.odesktop.GetProjectList()
            for project in projects:
                try:
                    self.odesktop.CloseProject(project)
                except:  # pragma: no cover
                    self.logger.warning("Failed to close Project {}".format(project))
        result = _close_aedt_application(close_on_exit, self.aedt_process_id, self.is_grpc_api)
        del _desktop_sessions[self.aedt_process_id]
        props = [a for a in dir(self) if not a.startswith("__")]
        for a in props:
            self.__dict__.pop(a, None)
        dicts = [self, sys.modules["__main__"]]
        for dict_to_clean in dicts:
            props = [a for a in dir(dict_to_clean) if "win32com" in str(type(dict_to_clean.__dict__.get(a, None)))]
            for a in props:
                dict_to_clean.__dict__[a] = None

        self.odesktop = None
        try:
            del sys.modules["__main__"].oDesktop
        except AttributeError:
            pass
        gc.collect()
        return result

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
        PyAEDT INFO: pyaedt v...
        PyAEDT INFO: Python version ...
        >>> desktop.close_desktop() # doctest: +SKIP

        """
        return self.release_desktop(close_projects=True, close_on_exit=True)

    def enable_autosave(self):
        """Enable the autosave option.

        Examples
        --------
        >>> import pyaedt
        >>> desktop = pyaedt.Desktop("2021.2")
        PyAEDT INFO: pyaedt v...
        PyAEDT INFO: Python version ...
        >>> desktop.enable_autosave()

        """
        self._main.oDesktop.EnableAutoSave(True)

    def disable_autosave(self):
        """Disable the autosave option.

        Examples
        --------
        >>> import pyaedt
        >>> desktop = pyaedt.Desktop("2021.2")
        PyAEDT INFO: pyaedt v...
        PyAEDT INFO: Python version ...
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

    @pyaedt_function_handler()
    def get_available_toolkits(self):
        """Get toolkit ready for installation.

        Returns
        -------
        list
            List of toolkit names.
        """
        from pyaedt.misc.install_extra_toolkits import available_toolkits

        return list(available_toolkits.keys())

    @pyaedt_function_handler()
    def add_custom_toolkit(self, toolkit_name):  # pragma: no cover
        """Add toolkit to AEDT Automation Tab.

        Parameters
        ----------
        toolkit_name : str
            Name of toolkit to add.

        Returns
        -------
        bool
        """
        from pyaedt.misc.install_extra_toolkits import available_toolkits

        toolkit = available_toolkits[toolkit_name]
        toolkit_name = toolkit_name.replace("_", "")

        def install(package_path, package_name=None):
            executable = '"{}"'.format(sys.executable) if is_windows else sys.executable

            commands = []
            if package_path.startswith("git") and package_name:
                commands.append([executable, "-m", "pip", "uninstall", "--yes", package_name])

            commands.append([executable, "-m", "pip", "install", "--upgrade", package_path])

            if self.aedt_version_id == "2023.1" and is_windows and "AnsysEM" in sys.base_prefix:
                commands.append([executable, "-m", "pip", "uninstall", "--yes", "pywin32"])

            for command in commands:
                if is_linux:
                    p = subprocess.Popen(command)
                else:
                    p = subprocess.Popen(" ".join(command))
                p.wait()

        install(toolkit["pip"], toolkit.get("package_name", None))
        import site

        packages = site.getsitepackages()
        full_path = None
        for pkg in packages:
            if os.path.exists(os.path.join(pkg, toolkit["toolkit_script"])):
                full_path = os.path.join(pkg, toolkit["toolkit_script"])
                break
        if not full_path:
            raise FileNotFoundError("Error finding the package.")
        self.add_script_to_menu(
            toolkit_name=toolkit_name,
            script_path=full_path,
            script_image=toolkit,
            product=toolkit["installation_path"],
            copy_to_personal_lib=False,
            add_pyaedt_desktop_init=False,
        )

    @pyaedt_function_handler()
    def add_script_to_menu(
        self,
        toolkit_name,
        script_path,
        script_image=None,
        product="Project",
        copy_to_personal_lib=True,
        add_pyaedt_desktop_init=True,
    ):
        """Add a script to the ribbon menu.

        .. note::
           This method is available in AEDT 2023 R2 and later. PyAEDT must be installed
           in AEDT to allow this method to run. For more information, see `Installation
           <https://aedt.docs.pyansys.com/version/stable/Getting_started/Installation.html>`_.

        Parameters
        ----------
        toolkit_name : str
            Name of the toolkit to appear in AEDT.
        script_path : str
            Full path to the script file. The script will be moved to Personal Lib.
        script_image : str, optional
            Full path to the image logo (a 30x30 pixel PNG file) to add to the UI.
            The default is ``None``.
        product : str, optional
            Product to which the toolkit applies. The default is ``"Project"``, in which case
            it applies to all designs. You can also specify a product, such as ``"HFSS"``.
        copy_to_personal_lib : bool, optional
            Whether to copy the script to Personal Lib or link the original script. Default is ``True``.

        Returns
        -------
        bool

        """
        if not os.path.exists(script_path):
            self.logger.error("Script does not exists.")
            return False
        from pyaedt.misc.install_extra_toolkits import write_toolkit_config

        toolkit_dir = os.path.join(self.personallib, "Toolkits")
        aedt_version = self.aedt_version_id
        tool_dir = os.path.join(toolkit_dir, product, toolkit_name)
        lib_dir = os.path.join(tool_dir, "Lib")
        toolkit_rel_lib_dir = os.path.relpath(lib_dir, tool_dir)
        if is_linux and aedt_version <= "2023.1":
            toolkit_rel_lib_dir = os.path.join("Lib", toolkit_name)
            lib_dir = os.path.join(toolkit_dir, toolkit_rel_lib_dir)
            toolkit_rel_lib_dir = "../../" + toolkit_rel_lib_dir
        os.makedirs(lib_dir, exist_ok=True)
        os.makedirs(tool_dir, exist_ok=True)
        dest_script_path = script_path
        if copy_to_personal_lib:
            dest_script_path = os.path.join(lib_dir, os.path.split(script_path)[-1])
            shutil.copy2(script_path, dest_script_path)
        files_to_copy = ["Run_PyAEDT_Toolkit_Script"]
        executable_version_agnostic = sys.executable
        for file_name in files_to_copy:
            src = os.path.join(pathname, "misc", file_name + ".py_build")
            dst = os.path.join(tool_dir, file_name.replace("_", " ") + ".py")
            if not os.path.isfile(src):
                raise FileNotFoundError("File not found: {}".format(src))
            with open(src, "r") as build_file:
                with open(dst, "w") as out_file:
                    self.logger.info("Building to " + dst)
                    build_file_data = build_file.read()
                    build_file_data = (
                        build_file_data.replace("##TOOLKIT_REL_LIB_DIR##", toolkit_rel_lib_dir)
                        .replace("##PYTHON_EXE##", executable_version_agnostic)
                        .replace("##PYTHON_SCRIPT##", dest_script_path)
                    )
                    build_file_data = build_file_data.replace(" % version", "")
                    out_file.write(build_file_data)
        if aedt_version >= "2023.2":
            if not script_image:
                script_image = os.path.join(os.path.dirname(__file__), "misc", "images", "large", "pyansys.png")
            write_toolkit_config(os.path.join(toolkit_dir, product), lib_dir, toolkit_name, toolkit=script_image)
        self.logger.info("{} toolkit installed.".format(toolkit_name))
        return True

    @pyaedt_function_handler()
    def remove_script_from_menu(self, toolkit_name, product="Project"):
        """Remove a toolkit script from the menu.

        Parameters
        ----------
        toolkit_name : str
            Name of the toolkit to remove.
        product : str, optional
            Product to which the toolkit applies. The default is ``"Project"``, in which case
            it applies to all designs. You can also specify a product, such as ``"HFSS"``.

        Returns
        -------
        bool
        """
        from pyaedt.misc.install_extra_toolkits import remove_toolkit_config

        toolkit_dir = os.path.join(self.personallib, "Toolkits")
        aedt_version = self.aedt_version_id
        tool_dir = os.path.join(toolkit_dir, product, toolkit_name)
        shutil.rmtree(tool_dir, ignore_errors=True)
        if aedt_version >= "2023.2":
            remove_toolkit_config(os.path.join(toolkit_dir, product), toolkit_name)
        self.logger.info("{} toolkit removed successfully.".format(toolkit_name))
        return True

    @pyaedt_function_handler()
    def submit_job(
        self,
        project_file,
        clustername,
        aedt_full_exe_path=None,
        numnodes=1,
        numcores=32,
        wait_for_license=True,
        setting_file=None,
    ):  # pragma: no cover
        """Submit a job to be solved on a cluster.

        Parameters
        ----------
        project_file : str
            Full path to the project.
        clustername : str
            Name of the cluster to submit the job to.
        aedt_full_exe_path : str, optional
            Full path to the AEDT executable file. The default is ``None``, in which
            case ``"/clustername/AnsysEM/AnsysEM2x.x/Win64/ansysedt.exe"`` is used.
        numnodes : int, optional
            Number of nodes. The default is ``1``.
        numcores : int, optional
            Number of cores. The default is ``32``.
        wait_for_license : bool, optional
             Whether to wait for the license to be validated. The default is ``True``.
        setting_file : str, optional
            Name of the file to use as a template. The default value is ``None``.

        Returns
        -------
        int
            ID of the job.

        References
        ----------
        >>> oDesktop.SubmitJob
        """
        project_path = os.path.dirname(project_file)
        project_name = os.path.basename(project_file).split(".")[0]
        if not aedt_full_exe_path:
            version = self.odesktop.GetVersion()[2:6]
            if version >= "22.2":
                version_name = "v" + version.replace(".", "")
            else:
                version_name = "AnsysEM" + version
            if os.path.exists(r"\\" + clustername + r"\AnsysEM\{}\Win64\ansysedt.exe".format(version_name)):
                aedt_full_exe_path = (
                    r"\\\\\\\\" + clustername + r"\\\\AnsysEM\\\\{}\\\\Win64\\\\ansysedt.exe".format(version_name)
                )
            elif os.path.exists(r"\\" + clustername + r"\AnsysEM\{}\Linux64\ansysedt".format(version_name)):
                aedt_full_exe_path = (
                    r"\\\\\\\\" + clustername + r"\\\\AnsysEM\\\\{}\\\\Linux64\\\\ansysedt".format(version_name)
                )
            else:
                self.logger.error("AEDT shared path does not exist. Provide a full path.")
                return False
        else:
            if not os.path.exists(aedt_full_exe_path):
                self.logger.error("AEDT shared path does not exist. Provide a full path.")
                return False
            aedt_full_exe_path.replace("\\", "\\\\")
        if project_name in self.project_list():
            self.odesktop.CloseProject(project_name)
        path_file = os.path.dirname(__file__)
        destination_reg = os.path.join(project_path, "Job_settings.areg")
        if not setting_file:
            setting_file = os.path.join(path_file, "misc", "Job_Settings.areg")
        shutil.copy(setting_file, destination_reg)

        f1 = open_file(destination_reg, "w")
        with open_file(setting_file) as f:
            lines = f.readlines()
            for line in lines:
                if "\\	$begin" == line[:8]:
                    lin = "\\	$begin \\'{}\\'\\\n".format(clustername)
                    f1.write(lin)
                elif "\\	$end" == line[:6]:
                    lin = "\\	$end \\'{}\\'\\\n".format(clustername)
                    f1.write(lin)
                elif "NumCores" in line:
                    lin = "\\	\\	\\	\\	NumCores={}\\\n".format(numcores)
                    f1.write(lin)
                elif "NumNodes=1" in line:
                    lin = "\\	\\	\\	\\	NumNodes={}\\\n".format(numnodes)
                    f1.write(lin)
                elif "ProductPath" in line:
                    lin = "\\	\\	ProductPath =\\'{}\\'\\\n".format(aedt_full_exe_path)
                    f1.write(lin)
                elif "WaitForLicense" in line:
                    lin = "\\	\\	WaitForLicense={}\\\n".format(str(wait_for_license).lower())
                    f1.write(lin)
                else:
                    f1.write(line)
        f1.close()
        return self.odesktop.SubmitJob(os.path.join(project_path, "Job_settings.areg"), project_file)

    @pyaedt_function_handler()
    def submit_ansys_cloud_job(
        self,
        project_file,
        config_name,
        region,
        numnodes=1,
        numcores=32,
        wait_for_license=True,
        setting_file=None,
        job_name=None,
    ):  # pragma: no cover
        """Submit a job to be solved on a cluster.

        Parameters
        ----------
        project_file : str
            Full path to the project.
        config_name : str
            Name of the Ansys Cloud machine configuration selected.
        region : str
            Name of Ansys Cloud location region.
            Available regions are: ``"westeurope"``, ``"eastus"``, ``"northcentralus"``, ``"southcentralus"``,
            ``"northeurope"``, ``"japaneast"``, ``"westus2"``, ``"centralindia"``.
        numnodes : int, optional
            Number of nodes. The default is ``1``.
        numcores : int, optional
            Number of cores. The default is ``32``.
        wait_for_license : bool, optional
             Whether to wait for the license to be validated. The default is ``True``.
        setting_file : str, optional
            Name of the file to use as a template. The default value is ``None``.

        Returns
        -------
        str, str
            Job ID, job name.

        References
        ----------
        >>> oDesktop.SubmitJob

        Examples
        --------
        >>> from pyaedt import Desktop

        >>> d = Desktop(specified_version="2023.1", new_desktop_session=False)
        >>> d.select_scheduler("Ansys Cloud")
        >>> out = d.get_available_cloud_config()
        >>> job_id, job_name = d.submit_ansys_cloud_job('via_gsg.aedt',
        ...                                             list(out.keys())[0],
        ...                                             region="westeurope",
        ...                                             job_name="MyJob"
        ...                                             )
        >>> o1=d.get_ansyscloud_job_info(job_id=job_id)
        >>> o2=d.get_ansyscloud_job_info(job_name=job_name)
        >>> d.download_job_results(job_id=job_id,
        ...                        project_path='via_gsg.aedt',
        ...                        results_folder='via_gsg_results')
        >>> d.release_desktop(False,False)
        """
        project_path = os.path.dirname(project_file)
        project_name = os.path.basename(project_file).split(".")[0]
        if not job_name:
            job_name = generate_unique_name(project_name)
        if project_name in self.project_list():
            self.odesktop.CloseProject(project_name)
        path_file = os.path.dirname(__file__)
        reg_name = generate_unique_name("ansys_cloud") + ".areg"
        destination_reg = os.path.join(project_path, reg_name)
        if not setting_file:
            setting_file = os.path.join(path_file, "misc", "ansys_cloud.areg")
        shutil.copy(setting_file, destination_reg)

        f1 = open_file(destination_reg, "w")
        with open_file(setting_file) as f:
            lines = f.readlines()
            i = 0
            while i < len(lines):
                line = lines[i]
                if "NumTasks" in line:
                    lin = "\\	\\	\\	\\	NumTasks={}\\\n".format(numcores)
                    f1.write(lin)
                elif "NumMaxTasksPerNode" in line:
                    lin = "\\	\\	\\	\\	NumMaxTasksPerNode={}\\\n".format(numcores)
                    f1.write(lin)
                elif "NumNodes=1" in line:
                    lin = "\\	\\	\\	\\	NumNodes={}\\\n".format(numnodes)
                    f1.write(lin)
                elif "Name=\\'Region\\'" in line:
                    f1.write(line)
                    lin = "\\	\\	\\	\\	Value=\\'{}\\'\\\n".format(region)
                    f1.write(lin)
                    i += 1
                elif "WaitForLicense" in line:
                    lin = "\\	\\	WaitForLicense={}\\\n".format(str(wait_for_license).lower())
                    f1.write(lin)
                elif "	JobName" in line:
                    lin = "\\	\\	\\	JobName=\\'{}\\'\\\n".format(job_name)
                    f1.write(lin)
                elif "Name=\\'Config\\'" in line:
                    f1.write(line)
                    lin = "\\	\\	\\	\\	Value=\\'{}\\'\\\n".format(config_name)
                    f1.write(lin)
                    i += 1
                else:
                    f1.write(line)
                i += 1
        f1.close()
        try:
            id = self.odesktop.SubmitJob(destination_reg, project_file)[0]
            return id, job_name
        except:
            self.logger.error("Failed to submit job. check parameters and credentials and retry")
            return "", ""

    @pyaedt_function_handler()
    def get_ansyscloud_job_info(self, job_id=None, job_name=None):  # pragma: no cover
        """Monitor a job submitted to Ansys Cloud.

        Parameters
        ----------
        job_id : str, optional
            Job Id.  The default value is ``None`` if job name is used.
        job_name : str, optional
            Job name.  The default value is ``None`` if job id is used.

        Returns
        -------
        dict

        Examples
        --------
        >>> from pyaedt import Desktop

        >>> d = Desktop(specified_version="2023.1", new_desktop_session=False)
        >>> d.select_scheduler("Ansys Cloud")
        >>> out = d.get_available_cloud_config()
        >>> job_id, job_name = d.submit_ansys_cloud_job('via_gsg.aedt',
        ...                                             list(out.keys())[0],
        ...                                             region="westeurope",
        ...                                             job_name="MyJob"
        ...                                             )
        >>> o1=d.get_ansyscloud_job_info(job_id=job_id)
        >>> o2=d.get_ansyscloud_job_info(job_name=job_name)
        >>> d.download_job_results(job_id=job_id,
        ...                        project_path='via_gsg.aedt',
        ...                        results_folder='via_gsg_results')
        >>> d.release_desktop(False,False)
        """
        command = os.path.join(self.install_path, "common", "AnsysCloudCLI", "AnsysCloudCli.exe")
        ver = self.aedt_version_id.replace(".", "R")
        if job_name:
            command = [command, "jobinfo", "-j", job_name]
        elif job_id:
            command = [command, "jobinfo", "-i", job_id]
        cloud_info = os.path.join(tempfile.gettempdir(), generate_unique_name("job_info"))
        with open(cloud_info, "w") as outfile:
            subprocess.Popen(" ".join(command), stdout=outfile).wait()
        out = {}
        with open(cloud_info, "r") as infile:
            lines = infile.readlines()
            for i in lines:
                if ":" in i.strip():
                    strp = i.strip().split(":")
                    out[strp[0]] = ":".join(strp[1:])
        return out

    @pyaedt_function_handler()
    def select_scheduler(
        self, scheduler_type, address=None, username=None, force_password_entry=False
    ):  # pragma: no cover
        """Select a scheduler to submit the job.

        Parameters
        ----------
        scheduler_type : str
            Name of the scheduler.
            Options are `"RSM"``, `""Windows HPC"``, `""LSF``, `""SGE"``, `""PBS"``, `""Ansys Cloud"``.
        address : str, optional
            String specifying the IP address or hostname of the head node or for the
            remote host running the RSM service.
        username : str, optional
            Username string to use for remote RSM service (or blank to use username
            stored in current submission host user settings). If the (non-blank) username doesn't match the
            username stored in current submission host user
            settings, then the Select Scheduler dialog is displayed to allow for password entry prior to job submission.
        force_password_entry : bool, optional
            Boolean used to force display of the Select Scheduler GUI to allow for
             password entry prior to job submission.


        Returns
        -------
        str
            The selected scheduler (if selection was successful, this string should match the input option string,
            although it could differ in upper/lowercase).

        Examples
        --------
        >>> from pyaedt import Desktop

        >>> d = Desktop(specified_version="2023.1", new_desktop_session=False)
        >>> d.select_scheduler("Ansys Cloud")
        >>> out = d.get_available_cloud_config()
        >>> job_id, job_name = d.submit_ansys_cloud_job('via_gsg.aedt',
        ...                                             list(out.keys())[0],
        ...                                             region="westeurope",
        ...                                             job_name="MyJob"
        ...                                             )
        >>> o1=d.get_ansyscloud_job_info(job_id=job_id)
        >>> o2=d.get_ansyscloud_job_info(job_name=job_name)
        >>> d.download_job_results(job_id=job_id,
        ...                        project_path='via_gsg.aedt',
        ...                        results_folder='via_gsg_results')
        >>> d.release_desktop(False,False)
        """
        if not address:
            return self.odesktop.SelectScheduler(scheduler_type)
        elif not username:
            return self.odesktop.SelectScheduler(scheduler_type, address)
        else:
            return self.odesktop.SelectScheduler(scheduler_type, address, username, str(force_password_entry))

    @pyaedt_function_handler()
    def get_available_cloud_config(self, region="westeurope"):  # pragma: no cover
        """Get available Ansys Cloud machines configuration.

        Parameters
        ----------
        region : str
            Name of Ansys Cloud location region.
            Available regions are: ``"westeurope"``, ``"eastus"``, ``"northcentralus"``, ``"southcentralus"``,
            ``"northeurope"``, ``"japaneast"``, ``"westus2"``, ``"centralindia"``.

        Returns
        -------
        dict
            Dictionary containing the config name and config details.

        Examples
        --------
        >>> from pyaedt import Desktop

        >>> d = Desktop(specified_version="2023.1", new_desktop_session=False)
        >>> d.select_scheduler("Ansys Cloud")
        >>> out = d.get_available_cloud_config()
        >>> job_id, job_name = d.submit_ansys_cloud_job('via_gsg.aedt',
        ...                                             list(out.keys())[0],
        ...                                             region="westeurope",
        ...                                             job_name="MyJob"
        ...                                             )
        >>> o1=d.get_ansyscloud_job_info(job_id=job_id)
        >>> o2=d.get_ansyscloud_job_info(job_name=job_name)
        >>> d.download_job_results(job_id=job_id,
        ...                        project_path='via_gsg.aedt',
        ...                        results_folder='via_gsg_results')
        >>> d.release_desktop(False,False)
        """
        command = os.path.join(self.install_path, "common", "AnsysCloudCLI", "AnsysCloudCli.exe")
        ver = self.aedt_version_id.replace(".", "R")
        command = [command, "getQueues", "-p", "AEDT", "-v", ver, "--details"]
        cloud_info = os.path.join(tempfile.gettempdir(), generate_unique_name("cloud_info"))
        with open(cloud_info, "w") as outfile:
            subprocess.Popen(" ".join(command), stdout=outfile).wait()

        dict_out = {}
        with open(cloud_info, "r") as infile:
            lines = infile.readlines()
            for i in range(len(lines)):
                line = lines[i].strip()
                if line.endswith(ver):
                    split_line = line.split("_")
                    if split_line[1] == region:
                        name = "{} {}".format(split_line[0], split_line[3])
                        dict_out[name] = {"Name": line}
                        for k in range(i + 1, i + 8):
                            spl = lines[k].split(":")
                            try:
                                dict_out[name][spl[0].strip()] = int(spl[1].strip())
                            except ValueError:
                                dict_out[name][spl[0].strip()] = spl[1].strip()
        os.unlink(cloud_info)
        return dict_out

    @pyaedt_function_handler()
    def download_job_results(self, job_id, project_path, results_folder, filter="*"):  # pragma: no cover
        """Download job results to a specific folder from Ansys Cloud.

        Parameters
        ----------
        job_id : str
            Job Id of solved project.
        project_path : str
            Project path to aedt file. The ".q" file will be created there to monitor download status.
        results_folder : str
            Folder where the simulation results will be downloaded.
        filter : str, optional
            A string containing filters to download. The delimiter of file types is ";". If no filter
            specified, the default filter "*" will be applied, which requests all files for download

        Returns
        -------
        bool
        """
        download_status = self.odesktop.DownloadJobResults(job_id, project_path, results_folder, filter)
        return True if download_status == 1 else False

    @property
    def are_there_simulations_running(self):
        """Check if there are simulation running.

        .. note::
           It works only for AEDT >= ``"2023.2"``.

        Returns
        -------
        float

        """
        if self.aedt_version_id > "2023.1":
            return self.odesktop.AreThereSimulationsRunning()
        return False

    @pyaedt_function_handler()
    def get_monitor_data(self):
        """Check and get monitor data of an existing analysis.

        .. note::
           It works only for AEDT >= ``"2023.2"``.

        Returns
        -------
        dict

        """
        counts = {"profile": 0, "convergence": 0, "sweptvar": 0, "progress": 0, "variations": 0, "displaytype": 0}
        if self.are_there_simulations_running:
            reqstr = " ".join(["%s %d 0" % (t, counts[t]) for t in counts])
            data = self.odesktop.GetMonitorData(reqstr)
            all_lines = (line.strip() for line in data.split("\n"))
            for line in all_lines:
                if line.startswith("$begin"):
                    btype = line.split()[1].strip("'")
                    if btype == "MonitoringProfileMsg":
                        counts["profile"] += 1
                    elif btype == "MonConvData":
                        counts["convergence"] += 1
                    elif btype == "MonGenericVariations":
                        pass
                    elif btype == "MapMonGraphicalProgMsg":
                        pass
                    elif btype == "MonitoringSweptVariableMsg":
                        counts["sweptvar"] += 1
            return counts
        return counts

    @pyaedt_function_handler()
    def stop_simulations(self, clean_stop=True):
        """Check if there are simulation running and stops them.

        .. note::
           It works only for AEDT >= ``"2023.2"``.

        Returns
        -------
        str

        """
        if self.aedt_version_id > "2023.1":
            return self.odesktop.StopSimulations(clean_stop)
        else:
            self.logger.error("It works only for AEDT >= `2023.2`.")
        return False
