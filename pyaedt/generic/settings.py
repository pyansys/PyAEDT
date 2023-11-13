import logging
import os
import time

is_linux = os.name == "posix"


class Settings(object):
    """Manages all PyAEDT environment variables and global settings."""

    def __init__(self):
        self._enable_logger = True
        self._enable_desktop_logs = True
        self._enable_screen_logs = True
        self._enable_file_logs = True
        self.pyaedt_server_path = ""
        self._logger_file_path = None
        self._logger_formatter = "%(asctime)s:%(destination)s:%(extra)s%(levelname)-8s:%(message)s"
        self._logger_datefmt = "%Y/%m/%d %H.%M.%S"
        self._enable_debug_edb_logger = False
        self._enable_debug_grpc_api_logger = False
        self._enable_debug_methods_argument_logger = False
        self._enable_debug_geometry_operator_logger = False
        self._enable_debug_internal_methods_logger = False
        self._enable_debug_logger = False
        self._enable_error_handler = True
        self._aedt_version = None
        self.remote_api = False
        self._use_grpc_api = None
        self._use_grpc_edb_api = False
        self.formatter = None
        self.remote_rpc_session = None
        self.remote_rpc_session_temp_folder = ""
        self.remote_rpc_service_manager_port = 17878
        self._project_properties = {}
        self._project_time_stamp = 0
        self._disable_bounding_box_sat = False
        self._force_error_on_missing_project = False
        self._enable_pandas_output = False
        self.time_tick = time.time()
        self._global_log_file_name = "pyaedt_{}.log".format(os.path.split(os.path.expanduser("~"))[-1])
        self._enable_global_log_file = True
        self._enable_local_log_file = False
        self._global_log_file_size = 10
        self._edb_dll_path = None
        self._lsf_num_cores = 2
        self._lsf_ram = 1000
        self._use_lsf_scheduler = False
        self._lsf_aedt_command = "ansysedt"
        self._lsf_timeout = 3600
        self._lsf_queue = None
        self._aedt_environment_variables = {
            "ANS_MESHER_PROC_DUMP_PREPOST_BEND_SM3": "1",
            "ANSYSEM_FEATURE_SF6694_NON_GRAPHICAL_COMMAND_EXECUTION_ENABLE": "1",
            "ANSYSEM_FEATURE_SF159726_SCRIPTOBJECT_ENABLE": "1",
            "ANSYSEM_FEATURE_SF222134_CABLE_MODELING_ENHANCEMENTS_ENABLE": "1",
            "ANSYSEM_FEATURE_F395486_RIGID_FLEX_BENDING_ENABLE": "1",
            "ANSYSEM_FEATURE_S432616_LAYOUT_COMPONENT_IN_3D_ENABLE": "1",
            "ANSYSEM_FEATURE_F545177_ECAD_INTEGRATION_WITH_APHI_ENABLE": "1",
            "ANSYSEM_FEATURE_F650636_MECH_LAYOUT_COMPONENT_ENABLE": "1",
            "ANSYSEM_FEATURE_F538630_MECH_TRANSIENT_THERMAL_ENABLE": "1",
            "ANSYSEM_FEATURE_F335896_MECHANICAL_STRUCTURAL_SOLN_TYPE_ENABLE": "1",
        }
        if is_linux:
            self._aedt_environment_variables["ANS_NODEPCHECK"] = "1"
        self._desktop_launch_timeout = 120
        self._number_of_grpc_api_retries = 6
        self._retry_n_times_time_interval = 0.1
        self._wait_for_license = False

    @property
    def wait_for_license(self):
        """Whether if Electronics Desktop has to be launched with ``-waitforlicense`` flag enabled or not.
        Default is ``False``.

        Returns
        -------
        bool
        """
        return self._wait_for_license

    @wait_for_license.setter
    def wait_for_license(self, value):
        self._wait_for_license = value

    @property
    def retry_n_times_time_interval(self):
        """Time interval between the retries by the ``_retry_n_times`` method."""
        return self._retry_n_times_time_interval

    @retry_n_times_time_interval.setter
    def retry_n_times_time_interval(self, value):
        self._retry_n_times_time_interval = float(value)

    @property
    def number_of_grpc_api_retries(self):
        """Number of gRPC API retries. The default is ``3``."""
        return self._number_of_grpc_api_retries

    @number_of_grpc_api_retries.setter
    def number_of_grpc_api_retries(self, value):
        self._number_of_grpc_api_retries = int(value)

    @property
    def desktop_launch_timeout(self):
        """Timeout in seconds for trying to launch AEDT. The default is ``90`` seconds."""
        return self._desktop_launch_timeout

    @desktop_launch_timeout.setter
    def desktop_launch_timeout(self, value):
        self._desktop_launch_timeout = int(value)

    @property
    def aedt_environment_variables(self):
        """Environment variables that are set before launching a new AEDT session,
        including those that enable the beta features."""
        return self._aedt_environment_variables

    @aedt_environment_variables.setter
    def aedt_environment_variables(self, value):
        self._aedt_environment_variables = value

    @property
    def lsf_queue(self):
        """LSF queue name. This attribute is valid only on Linux
        systems running LSF Scheduler."""
        return self._lsf_queue

    @lsf_queue.setter
    def lsf_queue(self, value):
        self._lsf_queue = value

    @property
    def use_lsf_scheduler(self):
        """Whether to use LSF Scheduler. This attribute is valid only on Linux
        systems running LSF Scheduler."""
        return self._use_lsf_scheduler

    @use_lsf_scheduler.setter
    def use_lsf_scheduler(self, value):
        self._use_lsf_scheduler = value

    @property
    def lsf_aedt_command(self):
        """Command to launch the task in the LSF Scheduler. The default is ``"ansysedt"``.
        This attribute is valid only on Linux systems running LSF Scheduler."""
        return self._lsf_aedt_command

    @lsf_aedt_command.setter
    def lsf_aedt_command(self, value):
        self._lsf_aedt_command = value

    @property
    def lsf_num_cores(self):
        """Number of LSF cores. This attribute is valid only
        on Linux systems running LSF Scheduler."""
        return self._lsf_num_cores

    @lsf_num_cores.setter
    def lsf_num_cores(self, value):
        self._lsf_num_cores = int(value)

    @property
    def lsf_ram(self):
        """RAM allocated for the LSF job. This attribute is valid
        only on Linux systems running LSF Scheduler."""
        return self._lsf_ram

    @lsf_ram.setter
    def lsf_ram(self, value):
        self._lsf_ram = int(value)

    @property
    def lsf_timeout(self):
        """Timeout in seconds for trying to start the interactive session. The default is ``3600`` seconds."""
        return self._lsf_timeout

    @lsf_timeout.setter
    def lsf_timeout(self, value):
        self._lsf_timeout = int(value)

    @property
    def aedt_version(self):
        """AEDT version in the form ``"2023.x"``. In AEDT 2022 R2 and later,
        evaluating a bounding box by exporting a SAT file is disabled."""
        return self._aedt_version

    @aedt_version.setter
    def aedt_version(self, value):
        self._aedt_version = value
        if self._aedt_version >= "2023.1":
            self.disable_bounding_box_sat = True

    @property
    def edb_dll_path(self):
        """Optional path for the EDB DLL file."""
        return self._edb_dll_path

    @edb_dll_path.setter
    def edb_dll_path(self, value):
        if os.path.exists(value):
            self._edb_dll_path = value

    @property
    def global_log_file_size(self):
        """Global PyAEDT log file size in MB. The default value is ``10``."""
        return self._global_log_file_size

    @global_log_file_size.setter
    def global_log_file_size(self, value):
        self._global_log_file_size = value

    @property
    def enable_global_log_file(self):
        """Flag for enabling and disabling the global PyAEDT log file located in the global temp folder.
        The default is ``True``."""
        return self._enable_global_log_file

    @enable_global_log_file.setter
    def enable_global_log_file(self, value):
        self._enable_global_log_file = value

    @property
    def enable_local_log_file(self):
        """Flag for enabling and disabling the local PyAEDT log file located
        in the ``projectname.pyaedt`` project folder. The default is ``True``."""
        return self._enable_local_log_file

    @enable_local_log_file.setter
    def enable_local_log_file(self, value):
        self._enable_local_log_file = value

    @property
    def global_log_file_name(self):
        """Global PyAEDT log file path. The default is ``pyaedt_username.log``."""
        return self._global_log_file_name

    @global_log_file_name.setter
    def global_log_file_name(self, value):
        self._global_log_file_name = value

    @property
    def enable_pandas_output(self):
        """Flag for whether Pandas is being used to export dictionaries and lists. This attribute
        applies to Solution data output.  The default is ``False``. If ``True``, the property or
        method returns a Pandas object. This property is valid only in the CPython environment."""
        return self._enable_pandas_output

    @enable_pandas_output.setter
    def enable_pandas_output(self, val):
        self._enable_pandas_output = val

    @property
    def enable_debug_methods_argument_logger(self):
        """Flag for whether to write out the method's arguments in the debug logger.
        The default is ``False``."""
        return self._enable_debug_methods_argument_logger

    @enable_debug_methods_argument_logger.setter
    def enable_debug_methods_argument_logger(self, val):
        self._enable_debug_methods_argument_logger = val

    @property
    def force_error_on_missing_project(self):
        """Flag for whether to check the project path. The default is ``False``. If
        ``True``, when passing a project path, the project has to exist. Otherwise, an
        error is raised."""
        return self._force_error_on_missing_project

    @force_error_on_missing_project.setter
    def force_error_on_missing_project(self, val):
        self._force_error_on_missing_project = val

    @property
    def disable_bounding_box_sat(self):
        """Flag for enabling and disabling bounding box evaluation by exporting a SAT file."""
        return self._disable_bounding_box_sat

    @disable_bounding_box_sat.setter
    def disable_bounding_box_sat(self, val):
        self._disable_bounding_box_sat = val

    @property
    def use_grpc_api(self):
        """Flag for whether to use the gRPC API or legacy COM object."""
        return self._use_grpc_api

    @use_grpc_api.setter
    def use_grpc_api(self, val):
        self._use_grpc_api = val

    @property
    def use_grpc_edb_api(self):
        """Flag for whether to use the gRPC EDB API or legacy .NET dll."""
        return self._use_grpc_edb_api

    @use_grpc_edb_api.setter
    def use_grpc_edb_api(self, val):
        self._use_grpc_edb_api = val

    @property
    def logger(self):
        """Active logger."""
        try:
            return logging.getLogger("Global")
        except:  # pragma: no cover
            return logging.getLogger(__name__)

    @property
    def enable_error_handler(self):
        """Flag for enabling and disabling the internal PyAEDT error handling."""
        return self._enable_error_handler

    @enable_error_handler.setter
    def enable_error_handler(self, val):
        self._enable_error_handler = val

    @property
    def enable_desktop_logs(self):
        """Flag for enabling and disabling the logging to the AEDT message window."""
        return self._enable_desktop_logs

    @enable_desktop_logs.setter
    def enable_desktop_logs(self, val):
        self._enable_desktop_logs = val

    @property
    def enable_screen_logs(self):
        """Flag for enabling and disabling the logging to STDOUT."""
        return self._enable_screen_logs

    @enable_screen_logs.setter
    def enable_screen_logs(self, val):
        self._enable_screen_logs = val

    @property
    def pyaedt_server_path(self):
        """``PYAEDT_SERVER_AEDT_PATH`` environment variable."""
        return os.getenv("PYAEDT_SERVER_AEDT_PATH", "")

    @pyaedt_server_path.setter
    def pyaedt_server_path(self, val):
        os.environ["PYAEDT_SERVER_AEDT_PATH"] = str(val)

    @property
    def enable_file_logs(self):
        """Flag for enabling and disabling the logging to a file."""
        return self._enable_file_logs

    @enable_file_logs.setter
    def enable_file_logs(self, val):
        self._enable_file_logs = val

    @property
    def enable_logger(self):
        """Flag for enabling and disabling the logging overall."""
        return self._enable_logger

    @enable_logger.setter
    def enable_logger(self, val):
        self._enable_logger = val

    @property
    def logger_file_path(self):
        """PyAEDT log file path."""
        return self._logger_file_path

    @logger_file_path.setter
    def logger_file_path(self, val):
        self._logger_file_path = val

    @property
    def logger_formatter(self):
        """Message format of the log entries.
        The default is ``'%(asctime)s:%(destination)s:%(extra)s%(levelname)-8s:%(message)s'``"""
        return self._logger_formatter

    @logger_formatter.setter
    def logger_formatter(self, val):
        self._logger_formatter = val

    @property
    def logger_datefmt(self):
        """Date format of the log entries.
        The default is ``'%Y/%m/%d %H.%M.%S'``"""
        return self._logger_datefmt

    @logger_datefmt.setter
    def logger_datefmt(self, val):
        self._logger_datefmt = val

    @property
    def enable_debug_edb_logger(self):
        """Flag for enabling and disabling the logger for any EDB API methods."""
        return self._enable_debug_edb_logger

    @enable_debug_edb_logger.setter
    def enable_debug_edb_logger(self, val):
        self._enable_debug_edb_logger = val

    @property
    def enable_debug_grpc_api_logger(self):
        """Flag for enabling and disabling the logging for the gRPC API calls."""
        return self._enable_debug_grpc_api_logger

    @enable_debug_grpc_api_logger.setter
    def enable_debug_grpc_api_logger(self, val):
        self._enable_debug_grpc_api_logger = val

    @property
    def enable_debug_geometry_operator_logger(self):
        """Flag for enabling and disabling the logging for the geometry operators.
        This setting is useful for debug purposes."""
        return self._enable_debug_geometry_operator_logger

    @enable_debug_geometry_operator_logger.setter
    def enable_debug_geometry_operator_logger(self, val):
        self._enable_debug_geometry_operator_logger = val

    @property
    def enable_debug_internal_methods_logger(self):
        """Flag for enabling and disabling the logging for internal methods.
        This setting is useful for debug purposes."""
        return self._enable_debug_internal_methods_logger

    @enable_debug_internal_methods_logger.setter
    def enable_debug_internal_methods_logger(self, val):
        self._enable_debug_internal_methods_logger = val

    @property
    def enable_debug_logger(self):
        """Flag for enabling and disabling the debug level logger."""
        return self._enable_debug_logger

    @enable_debug_logger.setter
    def enable_debug_logger(self, val):
        self._enable_debug_logger = val


settings = Settings()
