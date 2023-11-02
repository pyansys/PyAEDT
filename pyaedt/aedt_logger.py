# -*- coding: utf-8 -*-
import logging
from logging.handlers import RotatingFileHandler
import os
import shutil
import sys
import tempfile
import time

from pyaedt import settings

message_levels = {"Global": 0, "Project": 1, "Design": 2}


class Msg:
    (INFO, WARNING, ERROR, FATAL) = range(4)


class MessageList:
    """Collects and returns messages from the AEDT message manager for a specified project name and design name.

    Parameters
    ----------
    msg_list : list
        List of messages extracted from AEDT.
    project_name : str
        Name of the project. The default is the active project.
    design_name : str
        Name of the design within the specified project. The default is the active design.


    Attributes
    ----------
    global_level : list of str
        List of strings representing the message content at the global level of the message manager.

    project_level : list of str
        List of strings representing the message content within the specified project.

    design_level : list of str
        List of strings representing the message content for the specified design within the specified project.

    """

    def __init__(self, msg_list, project_name, design_name):
        self.global_level = []
        self.project_level = []
        self.design_level = []
        global_label = "Project: *Global - Messages, "
        project_label = "Project: {}, ".format(project_name)
        design_label = "Project: {}, Design: {} (".format(project_name, design_name)
        for line in msg_list:
            # Find the first instance of '[' to get the message context
            loc = line.find("[")
            if loc < 0:
                # Format is not clear - append to global
                self.global_level.append(line)
            else:
                line_label = line[0:loc]
                msg_txt = line[loc:].strip()
                if design_label in line_label:
                    self.design_level.append(msg_txt)
                elif project_label in line_label:
                    self.project_level.append(msg_txt)
                elif global_label in line_label:
                    self.global_level.append(msg_txt)


class AppFilter(logging.Filter):
    """Specifies the destination of the logger.

    AEDT exposes three different loggers, which are the global, project, and design loggers.

    Parameters
    ----------
    destination : str, optional
        Logger to write to. Options are ``"Global"`, ``"Project"``, and ``"Design"``.
        The default is ``"Global"``.
    extra : str, optional
        Name of the design or project. The default is ``""``.
    """

    def __init__(self, destination="Global", extra=""):
        self._destination = destination
        self._extra = extra

    def filter(self, record):
        """Modify the record sent to the logger.

        Parameters
        ----------
        record : class:`logging.LogRecord`
            Contains information related to the event being logged.
        """
        record.destination = self._destination

        # This will avoid the extra '::' for Global that does not have any extra info.
        if not self._extra:
            record.extra = self._extra
        else:
            record.extra = self._extra + ":"
        return True


class AedtLogger(object):
    """Specifies the logger to use for each AEDT logger.

    This class allows you to add a handler to write messages to a file and to indicate
    whether to write mnessages to the standard output (stdout).

    Parameters
    ----------
    level : int, optional
        Logging level to filter the message severity allowed in the logger.
        The default is ``logging.DEBUG``.
    filename : str, optional
        Name of the file to write messages to. The default is ``None``.
    to_stdout : bool, optional
        Whether to write log messages to stdout. The default is ``False``.
    """

    def __init__(self, level=logging.DEBUG, filename=None, to_stdout=False):
        self._std_out_handler = None
        self._files_handlers = []
        self.level = level
        self.filename = filename or settings.logger_file_path
        settings.logger_file_path = self.filename

        self._global = logging.getLogger("Global")
        if not settings.enable_logger:
            self._global.addHandler(logging.NullHandler())
            return

        self._projects = {}

        self._global.setLevel(level)
        self._global.addFilter(AppFilter())

        if settings.formatter:
            self.formatter = settings.formatter
        else:
            self.formatter = logging.Formatter(settings.logger_formatter, datefmt=settings.logger_datefmt)
        global_handler = False
        if settings.enable_global_log_file:
            for handler in self._global.handlers:
                if settings.global_log_file_name in str(handler):
                    global_handler = True
                    break
            log_file = os.path.join(tempfile.gettempdir(), settings.global_log_file_name)
            my_handler = RotatingFileHandler(
                log_file,
                mode="a",
                maxBytes=float(settings.global_log_file_size) * 1024 * 1024,
                backupCount=2,
                encoding=None,
                delay=0,
            )
            my_handler.setFormatter(self.formatter)
            my_handler.setLevel(self.level)
            if not global_handler and settings.global_log_file_name:
                self._global.addHandler(my_handler)
            self._files_handlers.append(my_handler)
        if self.filename and os.path.exists(self.filename):
            shutil.rmtree(self.filename, ignore_errors=True)
        if self.filename and settings.enable_local_log_file:
            self.add_file_logger(self.filename, "Global", level)

        if to_stdout:
            settings.enable_screen_logs = True
            self._std_out_handler = logging.StreamHandler(sys.stdout)
            self._std_out_handler.setLevel(level)
            _logger_stdout_formatter = logging.Formatter("PyAEDT %(levelname)s: %(message)s")

            self._std_out_handler.setFormatter(_logger_stdout_formatter)
            self._global.addHandler(self._std_out_handler)
        self._timer = time.time()

    def add_file_logger(self, filename, project_name, level=None):
        """Add a new file to the logger handlers list."""
        _project = logging.getLogger(project_name)
        _project.setLevel(level if level else self.level)
        _project.addFilter(AppFilter("Project", project_name))
        _file_handler = logging.FileHandler(filename)
        _file_handler.setLevel(level if level else self.level)
        _file_handler.setFormatter(self.formatter)
        _project.addHandler(_file_handler)
        if self._std_out_handler is not None:
            _project.addHandler(self._std_out_handler)
        for handler in self._global.handlers:
            if settings.global_log_file_name in str(handler):
                _project.addHandler(handler)
                break
        self.info("New logger file {} added to handlers.".format(filename))
        self._files_handlers.append(_file_handler)
        _project.info_timer = self.info_timer
        _project.reset_timer = self.reset_timer
        _project._timer = time.time()

        return _project

    def remove_file_logger(self, project_name):
        """Remove a file from the logger handlers list."""
        handlers = [i for i in self._global.handlers]
        for handler in self._files_handlers:
            if "pyaedt_{}.log".format(project_name) in str(handler):
                handler.close()
                if handler in handlers:
                    self._global.removeHandler(handler)
                self.info("logger file pyaedt_{}.log removed from handlers.".format(project_name))

    def remove_all_project_file_logger(self):
        """Remove all the local files from the logger handlers list."""
        handlers = [i for i in self._global.handlers]
        for handler in handlers:
            if "pyaedt_" in str(handler):
                handler.close()
                self._global.removeHandler(handler)
        self.info("Project files removed from handlers.")

    @property
    def _desktop(self):
        if "oDesktop" in dir(sys.modules["__main__"]):
            MainModule = sys.modules["__main__"]
            return MainModule.oDesktop
        return None  # pragma: no cover

    @property
    def _log_on_desktop(self):
        try:
            if self._desktop and not self._desktop.GetIsNonGraphical() and settings.enable_desktop_logs:
                return True
            else:
                return False
        except:  # pragma: no cover
            return False

    @_log_on_desktop.setter
    def _log_on_desktop(self, val):
        settings.enable_desktop_logs = val

    @property
    def _log_on_file(self):
        return settings.enable_file_logs

    @_log_on_file.setter
    def _log_on_file(self, val):
        settings.enable_file_logs = val

    @property
    def _log_on_screen(self):
        return settings.enable_screen_logs

    @_log_on_screen.setter
    def _log_on_screen(self, val):
        settings.enable_screen_logs = val

    @property
    def logger(self):
        """AEDT logger object."""
        if self._log_on_file:
            return logging.getLogger("Global")
        else:
            return None  # pragma: no cover

    @property
    def messages(self):
        """Message manager content for the active project and design.

        Returns
        -------
        list of str
           List of messages for the active project and design.

        """
        return self.get_messages(self._project_name, self._design_name)

    def reset_timer(self, time_val=None):
        """ "Reset actual timer to  actual time or specified time.

        Parameters
        ----------
        time_val : float, optional
            Value time to apply.

        Returns
        -------

        """
        if time_val:
            self._timer = time_val
        else:
            self._timer = time.time()
        return self._timer

    def get_messages(self, project_name=None, design_name=None, level=0, aedt_messages=False):
        """Get the message manager content for a specified project and design.

        If the specified project and design names are invalid, they are ignored.

        Parameters
        ----------
        project_name : str
            Name of the project to read messages from. Leave empty string to get Desktop level messages.
        design_name : str
            Name of the design to read messages from. Leave empty string to get Desktop level messages.
        level : int
            Level of messages to read. 0 – info and above, 1 – warning and above, 2 – error and fatal
        aedt_messages : bool
            Read content of message manager even if logger is disabled.


        Returns
        -------
        list of str
            List of messages for the specified project and design.

        """
        project_name = project_name or self._project_name
        design_name = design_name or self._design_name
        if aedt_messages and self._desktop.GetVersion() > "2022.2":
            global_message_data = self._desktop.GetMessages("", "", level)
            # if a 3d component is open, GetMessages without the project name argument returns messages with
            # "(3D Component)" appended to project name
            if not any(msg in global_message_data for msg in self._desktop.GetMessages(project_name, "", 0)):
                project_name = project_name + " (3D Component)"
            return MessageList(global_message_data, project_name, design_name)
        return MessageList([], project_name, design_name)

    def add_error_message(self, message_text, level=None):
        """Add a type 2 "Error" message to the message manager tree.

        Also add an error message to the logger if the handler is present.

        Parameters
        ----------
        message_text : str
            Text to display as the error message.
        level : str, optional
            Level to add the error message to. Options are ``"Global"``,
            ``"Project"``, and ``"Design"``. The default is ``None``,
            in which case the error message gets added to the ``"Design"``
            level.

        Examples
        --------
        Add an error message to the AEDT message manager.

        >>> hfss.logger.project.error("Project Error Message", "Project")

        """
        self.add_message(2, message_text, level)

    def add_warning_message(self, message_text, level=None):
        """Add a type 1 "Warning" message to the message manager tree.

        Also add a warning message to the logger if the handler is present.

        Parameters
        ----------
        message_text : str
            Text to display as the warning message.
        level : str, optional
            Level to add the warning message to. Options are ``"Global"``,
            ``"Project"``, and ``"Design"``. The default is ``None``,
            in which case the warning message gets added to the ``"Design"``
            level.

        Examples
        --------
        Add a warning message to the AEDT message manager.

        >>> hfss.logger.warning("Global warning message")

        """
        self.add_message(1, message_text, level)

    def add_info_message(self, message_text, level=None):
        """Add a type 0 "Info" message to the active design level of the message manager tree.

        Also add an info message to the logger if the handler is present.

        Parameters
        ----------
        message_text : str
            Text to display as the info message.
        level : str, optional
            Level to add the info message to. Options are ``"Global"``,
            ``"Project"``, and ``"Design"``. The default is ``None``,
            in which case the info message gets added to the ``"Design"``
            level.

        Examples
        --------
        Add an info message at the global level.

        >>> hfss.logger.info("Global warning message", "Global")

        """
        self.add_message(0, message_text, level)

    def add_debug_message(self, message_text, level=None):
        """Parameterized message to the message manager to specify the type and project or design level.

        Parameters
        ----------
        message_text : str
            Text to display as the message.
        level : str, optional
            Level to add the info message to. Options are ``"Global"``,
            ``"Project"``, and ``"Design"``. The default value is ``None``,
            in which case the info message gets added to the ``"Design"``
            level.
        """
        return self.add_message(3, message_text, level=level)

    def add_message(self, message_type, message_text, level=None, proj_name=None, des_name=None):
        """Add a message to the message manager to specify the type and project or design level.

        Parameters
        ----------
        message_type : int
            Type of the message. Options are:
            * ``0`` : Info
            * ``1`` : Warning
            * ``2`` : Error
            * ``3`` : Debug
        message_text : str
            Text to display as the message.
        level : str, optional
            Level to add the message to. Options are ``"Global"``,
            ``"Project"``, and ``"Design"``. The default is ``None``,
            in which case the message gets added to the
            ``"Design"`` level.
        proj_name : str, optional
            Name of the project.
        des_name : str, optional
            Name of the design.
        """
        self._log_on_dekstop(
            message_type=message_type, message_text=message_text, level=level, proj_name=proj_name, des_name=des_name
        )

        self._log_on_handler(message_type, message_text)

    def _log_on_dekstop(self, message_type, message_text, level=None, proj_name=None, des_name=None):
        if not proj_name:
            proj_name = ""

        if not des_name:
            des_name = ""

        if not level:
            level = "Design"

        assert level in message_levels, "Message level must be `Design', 'Project', or 'Global'."

        if self._log_on_desktop and self._desktop:
            if not proj_name and message_levels[level] > 0:
                proj_name = self._project_name
            if not des_name and message_levels[level] > 1:
                des_name = self._design_name
            if des_name and ";" in des_name:
                des_name = des_name[des_name.find(";") + 1 :]
            try:
                self._desktop.AddMessage(proj_name, des_name, message_type, message_text)
            except:
                print("PyAEDT INFO: Failed in Adding Desktop Message")

    def _log_on_handler(self, message_type, message_text, *args, **kwargs):
        if not (self._log_on_file or self._log_on_screen) or not self._global:
            return
        if len(message_text) > 250:
            message_text = message_text[:250] + "..."
        if message_type == 0:
            self._global.info(message_text, *args, **kwargs)
        elif message_type == 1:
            self._global.warning(message_text, *args, **kwargs)
        elif message_type == 2:
            self._global.error(message_text, *args, **kwargs)
        elif message_type == 3:
            self._global.debug(message_text, *args, **kwargs)

    def clear_messages(self, proj_name=None, des_name=None, level=2):
        """Clear all messages.

        Parameters
        ----------
        proj_name : str, optional
            Name of project. The default is ``None``, in which case messages
            are cleared for the current project. If blank, messages are cleared
            for all projects.
        des_name : str, optional
            Name of the design within the specified project. The default
            is ``None,`` in which case the current design is used.
            If blank, all designs are used.
        level : int, optional
            Level of the messages to clear. Options are:

            * ``0`` : Clear all info messages.
            * ``1`` : Clear all info and warning messages.
            * ``2`` : Clear all info, warning, and error messages.
            * ``3`` : Clear all messages, which include info, warning,
              error, and fatal-error messages.

            The default is ``2.``

        Examples
        --------
        Clear all messages in the current design and project.

        >>> hfss.clear_messages(level=3)

        Clear all messages.

        >>> hfss.clear_messages(proj_name="", des_name="", level=3)
        """
        if self._log_on_desktop:
            if proj_name is None:
                proj_name = self._project_name
            if des_name is None:
                des_name = self._design_name
            self._desktop.ClearMessages(proj_name, des_name, level)

    @property
    def _oproject(self):
        if self._desktop:
            return self._desktop.GetActiveProject()

    @property
    def _odesign(self):
        if self._oproject:
            return self._oproject.GetActiveDesign()

    @property
    def _design_name(self):
        try:
            return self._odesign.GetName()
        except AttributeError:
            return ""

    @property
    def _project_name(self):
        try:
            return self._oproject.GetName()
        except AttributeError:
            return ""

    def add_logger(self, destination, level=logging.DEBUG):
        """Add a logger for either the active project or active design.

        Parameters
        ----------
        destination : str
            Logger to write to. Options are ``"Project"`` and ``"Design"``.
        level : int, optional
            Logging level enum. The default is ``logging.DEBUG``.
        """
        if destination == "Project":
            project_name = self._project_name
            self._project = logging.getLogger(project_name)
            self._project.setLevel(level)
            self._project.addFilter(AppFilter("Project", project_name))
            if self._files_handlers:
                for handler in self._files_handlers:
                    self._project.addHandler(handler)
            if self._std_out_handler is not None:
                self._project.addHandler(self._std_out_handler)
            return self._project
        elif destination == "Design":
            project_name = self._project_name
            design_name = self._design_name
            self._design = logging.getLogger(project_name + ":" + design_name)
            self._design.setLevel(level)
            self._design.addFilter(AppFilter("Design", design_name))
            if self._files_handlers:
                for handler in self._files_handlers:
                    self._design.addHandler(handler)
            if self._std_out_handler is not None:
                self._design.addHandler(self._std_out_handler)
            return self._design
        else:
            raise ValueError("The destination must be either 'Project' or 'Design'.")

    def disable_desktop_log(self):
        """Disable the log in AEDT."""
        self._log_on_desktop = False
        self.info("Log on Desktop Message Manager is disabled")

    def enable_desktop_log(self):
        """Enable the log in AEDT."""
        self._log_on_desktop = True
        self.info("Log on Desktop Message Manager is enabled")

    def disable_stdout_log(self):
        """Disable printing log messages to stdout."""
        self._log_on_screen = False
        self._global.removeHandler(self._std_out_handler)
        self.info("StdOut is disabled")

    def enable_stdout_log(self):
        """Enable printing log messages to stdout."""
        self._log_on_screen = True
        if not self._std_out_handler:
            self._std_out_handler = logging.StreamHandler(sys.stdout)
            self._std_out_handler.setLevel(self.level)
            _logger_stdout_formatter = logging.Formatter("pyaedt %(levelname)s: %(message)s")

            self._std_out_handler.setFormatter(_logger_stdout_formatter)
            self._global.addHandler(self._std_out_handler)
        self._global.addHandler(self._std_out_handler)
        self.info("StdOut is enabled")

    def disable_log_on_file(self):
        """Disable writing log messages to an output file."""
        self._log_on_file = False
        for _file_handler in self._files_handlers:
            _file_handler.close()
            self._global.removeHandler(_file_handler)
        self.info("Log on file is disabled")

    def enable_log_on_file(self):
        """Enable writing log messages to an output file."""
        self._log_on_file = True
        for _file_handler in self._files_handlers:
            self._global.addHandler(_file_handler)
        self.info("Log on file is enabled")

    def info(self, msg, *args, **kwargs):
        """Write an info message to the global logger."""
        if not settings.enable_logger:
            return
        if args:
            try:
                msg1 = msg % tuple(str(i) for i in args)
            except TypeError:
                msg1 = msg
        else:
            msg1 = msg
        self._log_on_dekstop(0, msg1, "Global")
        return self._log_on_handler(0, msg, *args, **kwargs)

    def info_timer(self, msg, start_time=None, *args, **kwargs):
        """Write an info message to the global logger with elapsed time.
        Message will have an appendix of type Elapsed time: time.
        """
        if not settings.enable_logger:
            return
        if not start_time:
            start_time = self._timer
        td = time.time() - start_time
        m, s = divmod(td, 60)
        h, m = divmod(m, 60)
        d, h = divmod(h, 24)
        if d > 0:
            msg += " Elapsed time: {}days {}h {}m {}sec".format(round(d), round(h), round(m), round(s))
        elif h > 0:
            msg += " Elapsed time: {}h {}m {}sec".format(round(h), round(m), round(s))
        else:
            msg += " Elapsed time: {}m {}sec".format(round(m), round(s))
        if args:
            try:
                msg1 = msg % tuple(str(i) for i in args)
            except TypeError:
                msg1 = msg
        else:
            msg1 = msg
        self._log_on_dekstop(0, msg1, "Global")
        return self._log_on_handler(0, msg, *args, **kwargs)

    def warning(self, msg, *args, **kwargs):
        """Write a warning message to the global logger."""
        if not settings.enable_logger:
            return
        if args:
            try:
                msg1 = msg % tuple(str(i) for i in args)
            except TypeError:
                msg1 = msg
        else:
            msg1 = msg
        self._log_on_dekstop(1, msg1, "Global")
        return self._log_on_handler(1, msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):
        """Write an error message to the global logger."""
        if args:
            try:
                msg1 = msg % tuple(str(i) for i in args)
            except TypeError:
                msg1 = msg
        else:
            msg1 = msg
        self._log_on_dekstop(2, msg1, "Global")
        return self._log_on_handler(2, msg, *args, **kwargs)

    def debug(self, msg, *args, **kwargs):
        """Write a debug message to the global logger."""
        if not settings.enable_debug_logger or not settings.enable_logger:
            return
        if args:
            try:
                msg1 = msg % tuple(str(i) for i in args)
            except TypeError:
                msg1 = msg
        else:
            msg1 = msg
        self._log_on_dekstop(0, msg1, "Global")
        return self._log_on_handler(3, msg, *args, **kwargs)

    @property
    def glb(self):
        """Global logger."""
        self._global = logging.getLogger("Global")
        return self._global

    @property
    def project(self):
        """Project logger."""
        self._project = logging.getLogger(self._project_name)
        if not self._project.handlers:
            self.add_logger("Project")
        return self._project

    @property
    def design(self):
        """Design logger."""
        self._design = logging.getLogger(self._project_name + ":" + self._design_name)
        if not self._design.handlers:
            self.add_logger("Design")
        return self._design


pyaedt_logger = AedtLogger(to_stdout=settings.enable_screen_logs)
