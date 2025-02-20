Settings
========

The Settings class is designed to handle the configurations of PyAEDT and AEDT.
This includes behavior for logging, LSF scheduler, environment variable and general
settings. Most of the default values used can be modified using a YAML configuration file.
The path to this YAML file should be defined through the environment variable
``PYAEDT_LOCAL_SETTINGS_PATH``. If the environment variable is set and a file exists,
the default configuration settings are updated according to the content of the file.
If the environment variable is not defined, a check is performed to see if a file named
``"pyaedt_settings.yaml"`` exist in the user's ``APPDATA`` folder for Windows and
``HOME`` folder for Linux. If such file exists, it is then used to update the default
configuration.

Here is an example of YAML file :download:`YAML configuration file <../Resources/pyaedt_settings.yaml>`

.. warning::
    In Linux, it is recommended to add the ``ANS_NODEPCHECK`` environment variable for speed reasons.
    This variable is commented out in the download file. Using this file without modifying it disables
    this option from the default settings behaviour.

.. note::
    Not all settings from class ``Settings`` can be modified through this file
    as some of them expect Python objects or values obtained from code execution.
    For example, that is the case for ``formatter`` which expects an object of type
    ``Formatter`` and ``time_tick`` which expects a time value, in seconds, since the
    `epoch <https://docs.python.org/3/library/time.html#epoc>`_ as a floating-point number.

Below is the content that can be updated through the YAML file.

.. code-block:: yaml  
  
    # Settings related to logging
    log:
        # Enable or disable the logging of EDB API methods
        enable_debug_edb_logger: false
        # Enable or disable the logging of the geometry operators
        enable_debug_geometry_operator_logger: false
        # Enable or disable the logging of the gRPC API calls
        enable_debug_grpc_api_logger: false
        # Enable or disable the logging of internal methods
        enable_debug_internal_methods_logger: false
        # Enable or disable the logging at debug level
        enable_debug_logger: false
        # Enable or disable the logging of methods' arguments at debug level
        enable_debug_methods_argument_logger: false
        # Enable or disable the logging to the AEDT message window
        enable_desktop_logs: true
        # Enable or disable the logging to a file
        enable_file_logs: true
        # Enable or disable the global PyAEDT log file located in the global temp folder
        enable_global_log_file: true
        # Enable or disable the local PyAEDT log file located in the ``projectname.pyaedt`` project folder
        enable_local_log_file: false
        # Enable or disable the logging overall
        enable_logger: true
        # Enable or disable the logging to STDOUT
        enable_screen_logs: true
        # Global PyAEDT log file path
        global_log_file_name: null
        # Global PyAEDT log file size in MB
        global_log_file_size: 10
        # Date format of the log entries
        logger_datefmt: '%Y/%m/%d %H.%M.%S'
        # PyAEDT log file path
        logger_file_path: null
        # Message format of the log entries
        logger_formatter: '%(asctime)s:%(destination)s:%(extra)s%(levelname)-8s:%(message)s'
        # Path to the AEDT log file
        aedt_log_file: null

    # Settings related to Linux systems running LSF scheduler
    lsf:
        # Command to launch in the LSF Scheduler
        custom_lsf_command: null
        # Command to launch the task in the LSF Scheduler
        lsf_aedt_command: 'ansysedt'
        # Number of LSF cores
        lsf_num_cores: 2
        # Operating system string
        lsf_osrel: null
        # LSF queue name
        lsf_queue: null
        # RAM allocated for the LSF job
        lsf_ram: 1000
        # Timeout in seconds for trying to start the interactive session
        lsf_timeout: 3600
        # Value passed in the LSF 'select' string to the ui resource
        lsf_ui: null
        # Enable or disable use LSF Scheduler
        use_lsf_scheduler: false

    # Settings related to environment variables thare are set before launching a new AEDT session
    # This includes those that enable the beta features !
    aedt_env_var:
        ANSYSEM_FEATURE_F335896_MECHANICAL_STRUCTURAL_SOLN_TYPE_ENABLE: '1'
        ANSYSEM_FEATURE_F395486_RIGID_FLEX_BENDING_ENABLE: '1'
        ANSYSEM_FEATURE_F538630_MECH_TRANSIENT_THERMAL_ENABLE: '1'
        ANSYSEM_FEATURE_F545177_ECAD_INTEGRATION_WITH_APHI_ENABLE: '1'
        ANSYSEM_FEATURE_F650636_MECH_LAYOUT_COMPONENT_ENABLE: '1'
        ANSYSEM_FEATURE_S432616_LAYOUT_COMPONENT_IN_3D_ENABLE: '1'
        ANSYSEM_FEATURE_SF159726_SCRIPTOBJECT_ENABLE: '1'
        ANSYSEM_FEATURE_SF222134_CABLE_MODELING_ENHANCEMENTS_ENABLE: '1'
        ANSYSEM_FEATURE_SF6694_NON_GRAPHICAL_COMMAND_EXECUTION_ENABLE: '1'
        ANS_MESHER_PROC_DUMP_PREPOST_BEND_SM3: '1'
        # Environment variable used in Linux to skip the dependency check for speed
        # ANS_NODEPCHECK: '1'

    general:
        # Enable or disable the lazy load
        lazy_load: true
        # Enable or disable the lazy load dedicated to objects associated to the modeler
        objects_lazy_load: true
        # AEDT installation path
        aedt_install_dir: null
        # AEDT version in the form ``"2023.x"``
        aedt_version: null
        # Timeout in seconds for trying to launch AEDT
        desktop_launch_timeout: 120
        # Enable or disable bounding box evaluation by exporting a SAT file
        disable_bounding_box_sat: false
        # Optional path for the EDB DLL file
        edb_dll_path: null
        # Enable or disable the internal PyAEDT error handling
        enable_error_handler: true
        # Enable or disable the use of Pandas to export dictionaries and lists
        enable_pandas_output: false
        # Enable or disable the check of the project path
        force_error_on_missing_project: false
        # Number of gRPC API retries
        number_of_grpc_api_retries: 6
        # Enable or disable the release of AEDT on exception
        release_on_exception: true
        # Time interval between the retries by the ``_retry_n_times`` inner method
        retry_n_times_time_interval: 0.1
        # Enable or disable the use of the gRPC API or legacy COM object
        use_grpc_api: null
        # Enable or disable the use of multiple desktop sessions in the same Python script
        use_multi_desktop: false
        # Enable or disable the use of the flag `-waitforlicense` when launching Electronic Desktop
        wait_for_license: false
        # State whether the remote API is used or not
        remote_api: false
        # Specify the port the RPyC server is to listen to
        remote_rpc_service_manager_port: 17878
        # Specify the path to AEDT in the server
        pyaedt_server_path: ''
        # Remote temp folder
        remote_rpc_session_temp_folder: ''
