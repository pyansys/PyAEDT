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


import ast
import codecs
import csv
import datetime
import difflib
import fnmatch
from functools import update_wrapper
import inspect
import itertools
import json
import logging
import math
import os
import re
import string
import sys
import tempfile
import time
import traceback

from ansys.aedt.core.aedt_logger import pyaedt_logger
from ansys.aedt.core.generic.aedt_versions import aedt_versions
from ansys.aedt.core.generic.constants import CSS4_COLORS
from ansys.aedt.core.generic.errors import GrpcApiError
from ansys.aedt.core.generic.errors import MethodNotSupportedError
from ansys.aedt.core.generic.settings import inner_project_settings  # noqa: F401
from ansys.aedt.core.generic.settings import settings
import psutil

is_linux = os.name == "posix"
is_windows = not is_linux
inside_desktop = True if "4.0.30319.42000" in sys.version else False

inclusion_list = [
    "CreateVia",
    "PasteDesign",
    "Paste",
    "PushExcitations",
    "Rename",
    "RestoreProjectArchive",
    "ImportGerber",
    "EditSources",
]


def _write_mes(mes_text):
    mes_text = str(mes_text)
    parts = [mes_text[i : i + 250] for i in range(0, len(mes_text), 250)]
    for el in parts:
        settings.logger.error(el)


def _get_args_dicts(func, args, kwargs):
    if int(sys.version[0]) > 2:
        args_name = list(dict.fromkeys(inspect.getfullargspec(func)[0] + list(kwargs.keys())))
        args_dict = dict(list(itertools.zip_longest(args_name, args)) + list(kwargs.items()))
    else:
        args_name = list(dict.fromkeys(inspect.getargspec(func)[0] + list(kwargs.keys())))
        args_dict = dict(list(itertools.izip(args_name, args)) + list(kwargs.iteritems()))
    return args_dict


def _exception(ex_info, func, args, kwargs, message="Type Error"):
    """Write the trace stack to the desktop when a Python error occurs.

    Parameters
    ----------
    ex_info :

    func :

    args :

    kwargs :

    message :
         (Default value = "Type Error")

    Returns
    -------

    """
    header = "**************************************************************"
    _write_mes(header)
    tb_data = ex_info[2]
    tb_trace = traceback.format_tb(tb_data)

    for trace in traceback.format_stack():
        exceptions = [
            "_exception",
            "pydev",
            "traceback",
            "user_function",
            "__Invoke__",
            "interactiveshell",
            "async_helpers",
            "plugins",
        ]
        if any(exc in trace for exc in exceptions) or ("site-packages" in trace and "pyaedt" not in trace):
            continue
        for el in trace.split("\n"):
            _write_mes(el)
    for trace in tb_trace:
        exceptions = [
            "_exception",
            "pydev",
            "traceback",
            "user_function",
            "__Invoke__",
            "interactiveshell",
            "async_helpers",
            "plugins",
        ]
        if any(exc in trace for exc in exceptions) or ("site-packages" in trace and "pyaedt" not in trace):
            continue
        tblist = trace.split("\n")
        for el in tblist:
            if el:
                _write_mes(el)

    _write_mes(f"{message} on {func.__name__}")

    message_to_print = ""
    messages = ""
    from ansys.aedt.core.generic.desktop_sessions import _desktop_sessions

    if len(list(_desktop_sessions.values())) == 1:
        try:
            messages = list(list(_desktop_sessions.values())[0].odesktop.GetMessages("", "", 2))[-1].lower()
        except (GrpcApiError, AttributeError, TypeError, IndexError):
            pass
    if "error" in messages:
        message_to_print = messages[messages.index("[error]") :]

    if message_to_print:
        _write_mes("Last Electronics Desktop Message - " + message_to_print)

    try:
        args_dict = _get_args_dicts(func, args, kwargs)
        first_time_log = True

        for el in args_dict:
            if el != "self" and args_dict[el]:
                if first_time_log:
                    _write_mes("Method arguments: ")
                    first_time_log = False
                _write_mes(f"    {el} = {args_dict[el]} ")
    except Exception:
        pyaedt_logger.error("An error occurred while parsing and logging an error with method {}.")

    _write_mes(header)


def normalize_path(path_in, sep=None):
    """Normalize path separators.

    Parameters
    ----------
    path_in : str
        Path to normalize.
    sep : str, optional
        Separator.

    Returns
    -------
    str
        Path normalized to new separator.
    """
    if sep is None:
        sep = os.sep
    return path_in.replace("\\", sep).replace("/", sep)


def _check_types(arg):
    if "netref.builtins.list" in str(type(arg)):
        return "list"
    elif "netref.builtins.dict" in str(type(arg)):
        return "dict"
    elif "netref.__builtin__.list" in str(type(arg)):
        return "list"
    elif "netref.__builtin__.dict" in str(type(arg)):
        return "dict"
    return ""


def raise_exception_or_return_false(e):
    if not settings.enable_error_handler:
        if settings.release_on_exception:
            from ansys.aedt.core.generic.desktop_sessions import _desktop_sessions

            for v in list(_desktop_sessions.values())[:]:
                v.release_desktop(v.launched_by_pyaedt, v.launched_by_pyaedt)
        raise e
    elif "__init__" in str(e):  # pragma: no cover
        return
    else:
        return False


def _function_handler_wrapper(user_function, **deprecated_kwargs):
    def wrapper(*args, **kwargs):

        if deprecated_kwargs and kwargs:
            deprecate_kwargs(user_function.__name__, kwargs, deprecated_kwargs)
        try:
            settings.time_tick = time.time()
            out = user_function(*args, **kwargs)
            if settings.enable_debug_logger or settings.enable_debug_edb_logger:
                _log_method(user_function, args, kwargs)
            return out
        except MethodNotSupportedError as e:
            message = "This method is not supported in current AEDT design type."
            if settings.enable_screen_logs:
                pyaedt_logger.error("**************************************************************")
                pyaedt_logger.error(f"PyAEDT error on method {user_function.__name__}:  {message}. Check again")
                pyaedt_logger.error("**************************************************************")
                pyaedt_logger.error("")
            if settings.enable_file_logs:
                settings.error(message)
            return raise_exception_or_return_false(e)
        except GrpcApiError as e:
            _exception(sys.exc_info(), user_function, args, kwargs, "AEDT API Error")
            return raise_exception_or_return_false(e)
        except BaseException as e:
            _exception(sys.exc_info(), user_function, args, kwargs, str(sys.exc_info()[1]).capitalize())
            return raise_exception_or_return_false(e)

    return wrapper


def deprecate_kwargs(func_name, kwargs, aliases):
    """Use helper function for deprecating function arguments."""
    for alias, new in aliases.items():
        if alias in kwargs:
            if new in kwargs:
                msg = f"{func_name} received both {alias} and {new} as arguments!\n"
                msg += f"{alias} is deprecated, use {new} instead."
                raise TypeError(msg)
            pyaedt_logger.warning(f"Argument `{alias}` is deprecated for method `{func_name}`; use `{new}` instead.")
            kwargs[new] = kwargs.pop(alias)


def pyaedt_function_handler(direct_func=None, **deprecated_kwargs):
    """Provide an exception handler, logging mechanism, and argument converter for client-server communications.

    This method returns the function itself if correctly executed. Otherwise, it returns ``False``
    and displays errors.

    """
    if callable(direct_func):
        user_function = direct_func
        wrapper = _function_handler_wrapper(user_function, **deprecated_kwargs)
        return update_wrapper(wrapper, user_function)
    elif direct_func is not None:
        raise TypeError("Expected first argument to be a callable, or None")

    def decorating_function(user_function):
        wrapper = _function_handler_wrapper(user_function, **deprecated_kwargs)
        return update_wrapper(wrapper, user_function)

    return decorating_function


@pyaedt_function_handler()
def check_numeric_equivalence(a, b, relative_tolerance=1e-7):
    """Check if two numeric values are equivalent to within a relative tolerance.

    Parameters
    ----------
    a : int, float
        Reference value to compare to.
    b : int, float
        Secondary value for the comparison.
    relative_tolerance : float, optional
        Relative tolerance for the equivalence test. The difference is relative to the first value.
        The default is ``1E-7``.

    Returns
    -------
    bool
        ``True`` if the two passed values are equivalent, ``False`` otherwise.
    """
    if abs(a) > 0.0:
        reldiff = abs(a - b) / a
    else:
        reldiff = abs(b)
    return True if reldiff < relative_tolerance else False


@pyaedt_function_handler()
def _check_path(path_to_check):
    return path_to_check.replace("\\", "/") if path_to_check[0] != "\\" else path_to_check


@pyaedt_function_handler()
def check_and_download_file(remote_path, overwrite=True):
    """Check if a file is remote and either download it or return the path.

    Parameters
    ----------
    remote_path : str
        Path to the remote file.
    overwrite : bool, optional
        Whether to overwrite the file if it already exists locally.
        The default is ``True``.

    Returns
    -------
    str
        Path to the remote file.
    """
    if settings.remote_rpc_session:
        remote_path = _check_path(remote_path)
        local_path = os.path.join(settings.remote_rpc_session_temp_folder, os.path.split(remote_path)[-1])
        if settings.remote_rpc_session.filemanager.pathexists(remote_path):
            settings.remote_rpc_session.filemanager.download_file(remote_path, local_path, overwrite=overwrite)
            return local_path
    return remote_path


@pyaedt_function_handler()
def check_if_path_exists(path):
    """Check whether a path exists or not local or remote machine (for remote sessions only).

    Parameters
    ----------
    path : str
        Local or remote path to check.

    Returns
    -------
    bool
        ``True`` when successful, ``False`` when fails.
    """
    if settings.remote_rpc_session:
        return settings.remote_rpc_session.filemanager.pathexists(path)
    return os.path.exists(path)


@pyaedt_function_handler()
def check_and_download_folder(local_path, remote_path, overwrite=True):
    """Check if a folder is remote and either download it or return the path.

    Parameters
    ----------
    local_path : str
        Local path to save the folder to.
    remote_path : str
        Path to the remote folder.
    overwrite : bool, optional
        Whether to overwrite the folder if it already exists locally.
        The default is ``True``.

    Returns
    -------
    str
    """
    if settings.remote_rpc_session:
        remote_path = remote_path.replace("\\", "/") if remote_path[0] != "\\" else remote_path
        settings.remote_rpc_session.filemanager.download_folder(remote_path, local_path, overwrite=overwrite)
        return local_path
    return remote_path


@pyaedt_function_handler()
def open_file(file_path, file_options="r", encoding=None, override_existing=True):
    """Open a file and return the object.

    Parameters
    ----------
    file_path : str or Path
        Full absolute path to the file (either local or remote).
    file_options : str, optional
        Options for opening the file.
    encoding : str, optional
        Name of the encoding used to decode or encode the file.
        The default is ``None``, which means a platform-dependent encoding is used. You can
        specify any encoding supported by Python.
    override_existing : bool, optional
        Whether to override an existing file if opening a file in write mode on a remote
        machine. The default is ``True``.

    Returns
    -------
    object
        Opened file.
    """

    file_path = str(file_path)
    file_path = file_path.replace("\\", "/") if file_path[0] != "\\" else file_path

    dir_name = os.path.dirname(file_path)
    if "r" in file_options:
        if os.path.exists(file_path):
            return open(file_path, file_options, encoding=encoding)
        elif settings.remote_rpc_session and settings.remote_rpc_session.filemanager.pathexists(
            file_path
        ):  # pragma: no cover
            local_file = os.path.join(tempfile.gettempdir(), os.path.split(file_path)[-1])
            settings.remote_rpc_session.filemanager.download_file(file_path, local_file)
            return open(local_file, file_options, encoding=encoding)
    elif os.path.exists(dir_name):
        return open(file_path, file_options, encoding=encoding)
    elif settings.remote_rpc_session and settings.remote_rpc_session.filemanager.pathexists(dir_name):
        if "w" in file_options:
            return settings.remote_rpc_session.create_file(
                file_path, file_options, encoding=encoding, override=override_existing
            )
        else:
            return settings.remote_rpc_session.open_file(file_path, file_options, encoding=encoding)
    else:
        settings.logger.error("The file or folder %s does not exist", dir_name)


@pyaedt_function_handler()
def read_configuration_file(file_path):
    """Parse a file and return the information in a list or dictionary.

    Parameters
    ----------
    file_path : str
        Full path to the file. Supported formats are ``"csv"``, ``"json"``, ``"tab"``, ``"toml"``, and ``"xlsx"``.

    Returns
    -------
    dict or list
        Dictionary if configuration file is ``"toml"`` or ``"json"``, List is ``"csv"``, ``"tab"`` or ``"xlsx"``.
    """
    ext = os.path.splitext(file_path)[1]
    if ext == ".toml":
        return read_toml(file_path)
    elif ext == ".tab":
        return read_tab(file_path)
    elif ext == ".csv":
        return read_csv(file_path)
    elif ext == ".xlsx":
        return read_xlsx(file_path)
    else:
        return read_json(file_path)


@pyaedt_function_handler()
def read_json(fn):
    """Load a JSON file to a dictionary.

    Parameters
    ----------
    fn : str
        Full path to the JSON file.

    Returns
    -------
    dict
        Parsed JSON file as a dictionary.
    """
    json_data = {}
    with open_file(fn) as json_file:
        try:
            json_data = json.load(json_file)
        except json.JSONDecodeError as e:  # pragma: no cover
            error = f"Error reading json: {e.msg} at line {e.lineno}"
            settings.logger.error(error)
    return json_data


@pyaedt_function_handler()
def read_toml(file_path):  # pragma: no cover
    """Read a TOML file and return as a dictionary.

    Parameters
    ----------
    file_path : str
        Full path to the TOML file.

    Returns
    -------
    dict
        Parsed TOML file as a dictionary.
    """
    try:
        import tomllib
    except (ImportError, ModuleNotFoundError):
        import tomli as tomllib

    with open_file(file_path, "rb") as fb:
        return tomllib.load(fb)


def _log_method(func, new_args, new_kwargs):
    if not settings.enable_debug_internal_methods_logger and str(func.__name__)[0] == "_":
        return
    if not settings.enable_debug_geometry_operator_logger and "GeometryOperators" in str(func):
        return
    if (
        not settings.enable_debug_edb_logger
        and "Edb" in str(func) + str(new_args)
        or "edb_core" in str(func) + str(new_args)
    ):
        return
    line_begin = "ARGUMENTS: "
    message = []
    delta = time.time() - settings.time_tick
    m, s = divmod(delta, 60)
    h, m = divmod(m, 60)
    d, h = divmod(h, 24)
    msec = (s - int(s)) * 1000
    if d > 0:
        time_msg = f" {d}days {h}h {m}m {int(s)}sec."
    elif h > 0:
        time_msg = f" {h}h {m}m {int(s)}sec."
    else:
        time_msg = f"  {m}m {s}sec {int(msec)}msec."
    if settings.enable_debug_methods_argument_logger:
        args_dict = _get_args_dicts(func, new_args, new_kwargs)
        id = 0
        if new_args:
            object_name = str([new_args[0]])[1:-1]
            id = object_name.find(" object at ")
        if id > 0:
            object_name = object_name[1:id]
            message.append(f"'{object_name + '.' + str(func.__name__)}' was run in {time_msg}")
        else:
            message.append(f"'{str(func.__name__)}' was run in {time_msg}")
        message.append(line_begin)
        for k, v in args_dict.items():
            if k != "self":
                message.append(f"    {k} = {v}")
    for m in message:
        settings.logger.debug(m)


@pyaedt_function_handler()
def get_version_and_release(input_version):
    version = int(input_version[2:4])
    release = int(input_version[5])
    if version < 20:
        if release < 3:
            version -= 1
        else:
            release -= 2
    return (version, release)


@pyaedt_function_handler()
def get_string_version(input_version):
    output_version = input_version
    if isinstance(input_version, float):
        output_version = str(input_version)
        if len(output_version) == 4:
            output_version = "20" + output_version
    elif isinstance(input_version, int):
        output_version = str(input_version)
        output_version = f"20{output_version[:2]}.{output_version[-1]}"
    elif isinstance(input_version, str):
        if len(input_version) == 3:
            output_version = f"20{input_version[:2]}.{input_version[-1]}"
        elif len(input_version) == 4:
            output_version = "20" + input_version
    return output_version


@pyaedt_function_handler()
def env_path(input_version):
    """Get the path of the version environment variable for an AEDT version.

    Parameters
    ----------
    input_version : str
        AEDT version.

    Returns
    -------
    str
        Path of the version environment variable.

    Examples
    --------
    >>> env_path_student("2025.1")
    "C:/Program Files/ANSYSEM/ANSYSEM2025.1/Win64"
    """
    return os.getenv(
        f"ANSYSEM_ROOT{get_version_and_release(input_version)[0]}{get_version_and_release(input_version)[1]}", ""
    )


@pyaedt_function_handler()
def env_value(input_version):
    """Get the name of the version environment variable for an AEDT version.

    Parameters
    ----------
    input_version : str
        AEDT version.

    Returns
    -------
    str
        Name of the version environment variable.

    Examples
    --------
    >>> env_value(2025.1)
    "ANSYSEM_ROOT251"
    """
    return f"ANSYSEM_ROOT{get_version_and_release(input_version)[0]}{get_version_and_release(input_version)[1]}"


@pyaedt_function_handler()
def env_path_student(input_version):
    """Get the path of the version environment variable for an AEDT student version.

    Parameters
    ----------
    input_version : str
       AEDT student version.

    Returns
    -------
    str
        Path of the student version environment variable.

    Examples
    --------
    >>> env_path_student(2025.1)
    "C:/Program Files/ANSYSEM/ANSYSEM2025.1/Win64"
    """
    return os.getenv(
        f"ANSYSEMSV_ROOT{get_version_and_release(input_version)[0]}{get_version_and_release(input_version)[1]}",
        "",
    )


@pyaedt_function_handler()
def env_value_student(input_version):
    """Get the name of the version environment variable for an AEDT student version.

    Parameters
    ----------
    input_version : str
        AEDT student version.

    Returns
    -------
    str
         Name of the student version environment variable.

    Examples
    --------
    >>> env_value_student(2025.1)
    "ANSYSEMSV_ROOT251"
    """
    return f"ANSYSEMSV_ROOT{get_version_and_release(input_version)[0]}{get_version_and_release(input_version)[1]}"


@pyaedt_function_handler()
def get_filename_without_extension(path):
    """Get the filename without its extension.

    Parameters
    ----------
    path : str
        Path of the file.

    Returns
    -------
    str
       Name of the file without extension.
    """
    return os.path.splitext(os.path.split(path)[1])[0]


# FIXME: Remove usage of random module once IronPython compatibility is removed
@pyaedt_function_handler(rootname="root_name")
def generate_unique_name(root_name, suffix="", n=6):
    """Generate a new name given a root name and optional suffix.

    Parameters
    ----------
    root_name : string
        Root name to add random characters to.
    suffix : string, optional
        Suffix to add. The default is ``''``.
    n : int, optional
        Number of random characters to add to the name. The default value is ``6``.

    Returns
    -------
    str
        Newly generated name.
    """
    alphabet = string.ascii_uppercase + string.digits

    import secrets

    name = "".join(secrets.choice(alphabet) for _ in range(n))

    unique_name = root_name + "_" + name
    if suffix:
        unique_name += "_" + suffix
    return unique_name


@pyaedt_function_handler(rootname="root_name")
def generate_unique_folder_name(root_name=None, folder_name=None):
    """Generate a new AEDT folder name given a rootname.

    Parameters
    ----------
    root_name : str, optional
        Root name for the new folder. The default is ``None``.
    folder_name : str, optional
        Name for the new AEDT folder if one must be created.

    Returns
    -------
    str
        Newly generated name.
    """
    if not root_name:
        if settings.remote_rpc_session:
            root_name = settings.remote_rpc_session_temp_folder
        else:
            root_name = tempfile.gettempdir()
    if folder_name is None:
        folder_name = generate_unique_name("pyaedt_prj", n=3)
    temp_folder = os.path.join(root_name, folder_name)
    if settings.remote_rpc_session and not settings.remote_rpc_session.filemanager.pathexists(temp_folder):
        settings.remote_rpc_session.filemanager.makedirs(temp_folder)
    elif not os.path.exists(temp_folder):
        os.makedirs(temp_folder)

    return temp_folder


@pyaedt_function_handler(rootname="root_name")
def generate_unique_project_name(root_name=None, folder_name=None, project_name=None, project_format="aedt"):
    """Generate a new AEDT project name given a rootname.

    Parameters
    ----------
    root_name : str, optional
        Root name where the new project is to be created.
    folder_name : str, optional
        Name of the folder to create. The default is ``None``, in which case a random folder
        is created. Use ``""`` if you do not want to create a subfolder.
    project_name : str, optional
        Name for the project. The default is ``None``, in which case a random project is
        created. If a project with this name already exists, a new suffix is added.
    project_format : str, optional
        Project format. The default is ``"aedt"``. Options are ``"aedt"`` and ``"aedb"``.

    Returns
    -------
    str
        Newly generated name.
    """
    if not project_name:
        project_name = generate_unique_name("Project", n=3)
    name_with_ext = project_name + "." + project_format
    folder_path = generate_unique_folder_name(root_name, folder_name=folder_name)
    prj = os.path.join(folder_path, name_with_ext)
    if check_if_path_exists(prj):
        name_with_ext = generate_unique_name(project_name, n=3) + "." + project_format
        prj = os.path.join(folder_path, name_with_ext)
    return prj


def _retry_ntimes(n, function, *args, **kwargs):
    """Retry a function several times.

    Parameters
    ----------
    n : int
        The number of retries.
    function : function
        Function to retry.
    *args : tuple
        Arguments for the function.
    **kwargs : dict
        Keyword arguments for the function.

    Returns
    -------
    None
    """
    func_name = None
    try:
        if function.__name__ == "InvokeAedtObjMethod":
            func_name = args[1]
    except Exception:
        pyaedt_logger.debug("An error occurred while accessing the arguments of a function " "called multiple times.")
    retry = 0
    ret_val = None
    # if func_name and func_name not in inclusion_list and not func_name.startswith("Get"):
    if func_name and func_name not in inclusion_list:
        n = 1
    while retry < n:
        try:
            ret_val = function(*args, **kwargs)
        except Exception:
            retry += 1
            time.sleep(settings.retry_n_times_time_interval)
        else:
            return ret_val
    if retry == n:
        if "__name__" in dir(function):
            raise AttributeError(f"Error in Executing Method {function.__name__}.")
        else:
            raise AttributeError("Error in Executing Method.")


@pyaedt_function_handler()
def time_fn(fn, *args, **kwargs):
    start = datetime.datetime.now()
    results = fn(*args, **kwargs)
    end = datetime.datetime.now()
    fn_name = fn.__module__ + "." + fn.__name__
    delta = (end - start).microseconds * 1e-6
    print(fn_name + ": " + str(delta) + "s")
    return results


@pyaedt_function_handler(rel_tol="relative_tolerance", abs_tol="absolute_tolerance")
def isclose(a, b, relative_tolerance=1e-9, absolute_tolerance=0.0):
    """Whether two numbers are close to each other given relative and absolute tolerances.

    Parameters
    ----------
    a : float, int
        First number to compare.
    b : float, int
        Second number to compare.
    relative_tolerance : float
        Relative tolerance. The default value is ``1e-9``.
    absolute_tolerance : float
        Absolute tolerance. The default value is ``0.0``.

    Returns
    -------
    bool
        ``True`` if the two numbers are closed, ``False`` otherwise.
    """
    return abs(a - b) <= max(relative_tolerance * max(abs(a), abs(b)), absolute_tolerance)


@pyaedt_function_handler()
def is_number(a):
    """Whether the given input is a number.

    Parameters
    ----------
    a : float, int, str
        Number to check.

    Returns
    -------
    bool
        ``True`` if it is a number, ``False`` otherwise.
    """
    if isinstance(a, float) or isinstance(a, int):
        return True
    elif isinstance(a, str):
        try:
            float(a)
            return True
        except ValueError:
            return False
    else:
        return False


@pyaedt_function_handler()
def is_array(a):
    """Whether the given input is an array.

    Parameters
    ----------
    a : list
        List to check.

    Returns
    -------
    bool
        ``True`` if it is an array, ``False`` otherwise.
    """
    try:
        v = list(ast.literal_eval(a))
    except (ValueError, TypeError, NameError, SyntaxError):
        return False
    else:
        if isinstance(v, list):
            return True
        else:
            return False


@pyaedt_function_handler()
def is_project_locked(project_path):
    """Check if an AEDT project lock file exists.

    Parameters
    ----------
    project_path : str
        Path for the AEDT project.

    Returns
    -------
    bool
        ``True`` when successful, ``False`` when failed.
    """
    if settings.remote_rpc_session:
        if settings.remote_rpc_session.filemanager.pathexists(project_path + ".lock"):
            return True
        else:
            return False
    return check_if_path_exists(project_path + ".lock")


@pyaedt_function_handler()
def available_license_feature(
    feature="electronics_desktop", input_dir=None, port=1055, name="127.0.0.1"
):  # pragma: no cover
    """Check available license feature.

    Parameters
    ----------
    feature : str
        Feature increment name. The default is the ``"electronics_desktop"``.
    input_dir : str, optional
        AEDT installation path. The default is ``None``, in which case the first identified AEDT
        installation from :func:`ansys.aedt.core.generic.aedt_versions.installed_versions`
        method is taken.
    port : int, optional
        Server port number.
    name : str, optional
        License server name.

    Returns
    -------
    int
        Number of available license features, ``False`` when license server is down.
    """
    import subprocess  # nosec B404

    if os.getenv("ANSYSLMD_LICENSE_FILE", None):
        name_env = os.getenv("ANSYSLMD_LICENSE_FILE")
        name_env = name_env.split(",")[0].split("@")
        if len(name_env) == 2:
            port = name_env[0]
            name = name_env[1]

    if not input_dir:
        input_dir = list(aedt_versions.installed_versions.values())[0]

    if is_linux:
        ansysli_util_path = os.path.join(input_dir, "licensingclient", "linx64", "lmutil")
    else:
        ansysli_util_path = os.path.join(input_dir, "licensingclient", "winx64", "lmutil")

    my_env = os.environ.copy()

    tempfile_checkout = tempfile.NamedTemporaryFile(suffix=".txt", delete=False).name

    cmd = [ansysli_util_path, "lmstat", "-f", feature, "-c", str(port) + "@" + str(name)]

    f = open(tempfile_checkout, "w")

    subprocess.Popen(cmd, stdout=f, stderr=f, env=my_env).wait()  # nosec

    f.close()

    available_licenses = 0
    pattern_license = r"Total of\s+(\d+)\s+licenses? issued;\s+Total of\s+(\d+)\s+licenses? in use"
    pattern_error = r"Error getting status"
    with open_file(tempfile_checkout, "r") as f:
        for line in f:
            line = line.strip()
            match_license = re.search(pattern_license, line)
            if match_license:
                total_licenses_issued = int(match_license.group(1))
                total_licenses_in_use = int(match_license.group(2))
                available_licenses = total_licenses_issued - total_licenses_in_use
                break
            match_error = re.search(pattern_error, line)
            if match_error:
                pyaedt_logger.error(line)
                return False

    # Clean up temp file after processing
    os.remove(tempfile_checkout)

    return available_licenses


@pyaedt_function_handler()
def remove_project_lock(project_path):
    """Check if an AEDT project exists and try to remove the lock file.

    .. note::
       This operation is risky because the file could be opened in another AEDT instance.

    Parameters
    ----------
    project_path : str
        Path for the AEDT project.

    Returns
    -------
    bool
        ``True`` when successful, ``False`` when failed.
    """
    if settings.remote_rpc_session and settings.remote_rpc_session.filemanager.pathexists(project_path + ".lock"):
        settings.remote_rpc_session.filemanager.unlink(project_path + ".lock")
        return True
    if os.path.exists(project_path + ".lock"):
        os.remove(project_path + ".lock")
    return True


@pyaedt_function_handler(filename="file_name")
def read_csv(file_name, encoding="utf-8"):
    """Read information from a CSV file and return a list.

    Parameters
    ----------
    file_name : str
            Full path and name for the CSV file.
    encoding : str, optional
            File encoding for the CSV file. The default is ``"utf-8"``.

    Returns
    -------
    list
        Content of the CSV file.
    """
    file_name = check_and_download_file(file_name)

    lines = []
    with codecs.open(file_name, "rb", encoding) as csvfile:
        reader = csv.reader(csvfile, delimiter=",")
        for row in reader:
            lines.append(row)
    return lines


@pyaedt_function_handler(filename="input_file")
def read_csv_pandas(input_file, encoding="utf-8"):
    """Read information from a CSV file and return a list.

    Parameters
    ----------
    input_file : str
            Full path and name for the CSV file.
    encoding : str, optional
            File encoding for the CSV file. The default is ``"utf-8"``.

    Returns
    -------
    :class:`pandas.DataFrame`
        CSV file content.
    """
    input_file = check_and_download_file(input_file)
    try:
        import pandas as pd

        return pd.read_csv(input_file, encoding=encoding, header=0, na_values=".")
    except ImportError:
        pyaedt_logger.error("Pandas is not available. Install it.")
        return None


@pyaedt_function_handler(filename="file_name")
def read_tab(file_name):
    """Read information from a TAB file and return a list.

    Parameters
    ----------
    file_name : str
            Full path and name for the TAB file.

    Returns
    -------
    list
        TAB file content.
    """
    with open_file(file_name) as my_file:
        lines = my_file.readlines()
    return lines


@pyaedt_function_handler(filename="file_name")
def read_xlsx(file_name):
    """Read information from an XLSX file and return a list.

    Parameters
    ----------
    file_name : str
            Full path and name for the XLSX file.

    Returns
    -------
    list
        XLSX file content.
    """
    file_name = check_and_download_file(file_name)
    try:
        import pandas as pd

        lines = pd.read_excel(file_name)
        return lines
    except ImportError:
        lines = []
        return lines


@pyaedt_function_handler(output="output_file", quotechar="quote_char")
def write_csv(output_file, list_data, delimiter=",", quote_char="|", quoting=csv.QUOTE_MINIMAL):
    """Write data to a CSV .

    Parameters
    ----------
    output_file : str
        Full path and name of the file to write the data to.
    list_data : list
        Data to be written to the specified output file.
    delimiter : str
        Delimiter. The default value is ``"|"``.
    quote_char : str
        Quote character. The default value is ``"|"``
    quoting : int
        Quoting character. The default value is ``"csv.QUOTE_MINIMAL"``.
        It can take one any of the following module constants:

        - ``"csv.QUOTE_MINIMAL"`` means only when required, for example, when a
            field contains either the quote char or the delimiter
        - ``"csv.QUOTE_ALL"`` means that quotes are always placed around fields.
        - ``"csv.QUOTE_NONNUMERIC"`` means that quotes are always placed around
            fields which do not parse as integers or floating point
            numbers.
        - ``"csv.QUOTE_NONE"`` means that quotes are never placed around fields.

    Return
    ------
    bool
        ``True`` when successful, ``False`` when failed.
    """
    f = open(output_file, "w", newline="")
    writer = csv.writer(f, delimiter=delimiter, quotechar=quote_char, quoting=quoting)
    for data in list_data:
        writer.writerow(data)
    f.close()
    return True


@pyaedt_function_handler(search_key1="search_key_1", search_key2="search_key_2")
def filter_tuple(value, search_key_1, search_key_2):
    """Filter a tuple of two elements with two search keywords."""
    ignore_case = True

    def _create_pattern(k1, k2):
        k1a = re.sub(r"\?", r".", k1)
        k1b = re.sub(r"\*", r".*?", k1a)
        k2a = re.sub(r"\?", r".", k2)
        k2b = re.sub(r"\*", r".*?", k2a)
        pattern = f".*\\({k1b},{k2b}\\)"
        return pattern

    if ignore_case:
        compiled_re = re.compile(_create_pattern(search_key_1, search_key_2), re.IGNORECASE)
    else:
        compiled_re = re.compile(_create_pattern(search_key_1, search_key_2))

    m = compiled_re.search(value)
    if m:
        return True
    return False


@pyaedt_function_handler(search_key1="search_key_1")
def filter_string(value, search_key_1):
    """Filter a string"""
    ignore_case = True

    def _create_pattern(k1):
        k1a = re.sub(r"\?", r".", k1.replace("\\", "\\\\"))
        k1b = re.sub(r"\*", r".*?", k1a)
        pattern = f"^{k1b}$"
        return pattern

    if ignore_case:
        compiled_re = re.compile(_create_pattern(search_key_1), re.IGNORECASE)
    else:
        compiled_re = re.compile(_create_pattern(search_key_1))  # pragma: no cover

    m = compiled_re.search(value)
    if m:
        return True
    return False


@pyaedt_function_handler(startpath="path", filepattern="file_pattern")
def recursive_glob(path, file_pattern):
    """Get a list of files matching a pattern, searching recursively from a start path.

    Parameters
    ----------
    path : str
        Starting path.
    file_pattern : str
        File pattern to match.

    Returns
    -------
    list
        List of files matching the given pattern.
    """
    if settings.remote_rpc_session:
        files = []
        for i in settings.remote_rpc_session.filemanager.listdir(path):
            if settings.remote_rpc_session.filemanager.isdir(os.path.join(path, i)):
                files.extend(recursive_glob(os.path.join(path, i), file_pattern))
            elif fnmatch.fnmatch(i, file_pattern):
                files.append(os.path.join(path, i))
        return files
    else:
        return [
            os.path.join(dirpath, filename)
            for dirpath, _, filenames in os.walk(path)
            for filename in filenames
            if fnmatch.fnmatch(filename, file_pattern)
        ]


@pyaedt_function_handler()
def number_aware_string_key(s):
    """Get a key for sorting strings that treats embedded digit sequences as integers.

    Parameters
    ----------
    s : str
        String to calculate the key from.

    Returns
    -------
    tuple
        Tuple of key entries.
    """

    def is_digit(c):
        return "0" <= c <= "9"

    result = []
    i = 0
    while i < len(s):
        if is_digit(s[i]):
            j = i + 1
            while j < len(s) and is_digit(s[j]):
                j += 1
            key = int(s[i:j])
            result.append(key)
            i = j
        else:
            j = i + 1
            while j < len(s) and not is_digit(s[j]):
                j += 1
            key = s[i:j]
            result.append(key)
            i = j
    return tuple(result)


@pyaedt_function_handler()
def _create_toml_file(input_dict, full_toml_path):
    import tomli_w

    if not os.path.exists(os.path.dirname(full_toml_path)):
        os.makedirs(os.path.dirname(full_toml_path))

    def _dict_toml(d):
        new_dict = {}
        for k, v in d.items():
            new_k = k
            if not isinstance(k, str):
                new_k = str(k)
            new_v = v
            if isinstance(v, dict):
                new_v = _dict_toml(v)
            elif isinstance(v, tuple):
                new_v = list(v)
            new_dict[new_k] = new_v
        return new_dict

    new_dict = _dict_toml(input_dict)
    with open_file(full_toml_path, "wb") as fp:
        tomli_w.dump(new_dict, fp)
    settings.logger.info(f"{full_toml_path} correctly created.")
    return True


@pyaedt_function_handler()
def _create_json_file(json_dict, full_json_path):
    if not os.path.exists(os.path.dirname(full_json_path)):
        os.makedirs(os.path.dirname(full_json_path))

    with open_file(full_json_path, "w") as fp:
        json.dump(json_dict, fp, indent=4)
    settings.logger.info(f"{full_json_path} correctly created.")

    return True


@pyaedt_function_handler(dict_in="input_data", full_path="output_file")
def write_configuration_file(input_data, output_file):
    """Create a configuration file in JSON or TOML format from a dictionary.

    Parameters
    ----------
    input_data : dict
        Dictionary to write the file to.
    output_file : str
        Full path to the file, including its extension.

    Returns
    -------
    bool
        ``True`` when successful, ``False`` when failed.
    """
    ext = os.path.splitext(output_file)[1]
    if ext == ".json":
        return _create_json_file(input_data, output_file)
    elif ext == ".toml":
        return _create_toml_file(input_data, output_file)


@pyaedt_function_handler()
def active_sessions(version=None, student_version=False, non_graphical=False):
    """Get information for the active AEDT sessions.

    Parameters
    ----------
    version : str, optional
        Version to check. The default is ``None``, in which case all versions are checked.
        When specifying a version, you can use a three-digit format like ``"222"`` or a
        five-digit format like ``"2022.2"``.
    student_version : bool, optional
    non_graphical : bool, optional

    Returns
    -------
    dict
        {AEDT PID: port}
        If the PID corresponds to a COM session port is set to -1
    """
    return_dict = {}
    if student_version:
        keys = ["ansysedtsv.exe", "ansysedtsv"]
    else:
        keys = ["ansysedt.exe", "ansysedt"]
    if version and "." in version:
        version = version[-4:].replace(".", "")
    if version and version < "221":
        version = version[:2] + "." + version[2]
    for p in psutil.process_iter():
        try:
            if p.name() in keys:
                cmd = p.cmdline()
                if non_graphical and "-ng" in cmd or not non_graphical:
                    if not version or (version and version in cmd[0]):
                        if "-grpcsrv" in cmd:
                            if not version or (version and version in cmd[0]):
                                try:
                                    return_dict[p.pid] = int(cmd[cmd.index("-grpcsrv") + 1])
                                except (IndexError, ValueError):
                                    # default desktop grpc port.
                                    return_dict[p.pid] = 50051
                        else:
                            return_dict[p.pid] = -1
                            for i in psutil.net_connections():
                                if i.pid == p.pid and (i.laddr.port > 50050 and i.laddr.port < 50200):
                                    return_dict[p.pid] = i.laddr.port
                                    break
        except psutil.NoSuchProcess as e:  # pragma: no cover
            pyaedt_logger.debug(f"The process exited and cannot be an active session: {e}")
        except Exception as e:  # pragma: no cover
            pyaedt_logger.error(
                f"A(n) {type(e)} error occurred while retrieving information for the active AEDT sessions: {e}"
            )
    return return_dict


@pyaedt_function_handler()
def com_active_sessions(version=None, student_version=False, non_graphical=False):
    """Get information for the active COM AEDT sessions.

    Parameters
    ----------
    version : str, optional
        Version to check. The default is ``None``, in which case all versions are checked.
        When specifying a version, you can use a three-digit format like ``"222"`` or a
        five-digit format like ``"2022.2"``.
    student_version : bool, optional
        Whether to check for student version sessions. The default is ``False``.
    non_graphical : bool, optional
        Whether to check only for active non-graphical sessions. The default is ``False``.

    Returns
    -------
    List
        List of AEDT process IDs.
    """

    all_sessions = active_sessions(version, student_version, non_graphical)

    return_list = []
    for s, p in all_sessions.items():
        if p == -1:
            return_list.append(s)
    return return_list


@pyaedt_function_handler()
def grpc_active_sessions(version=None, student_version=False, non_graphical=False):
    """Get information for the active gRPC AEDT sessions.

    Parameters
    ----------
    version : str, optional
        Version to check. The default is ``None``, in which case all versions are checked.
        When specifying a version, you can use a three-digit format like ``"222"`` or a
        five-digit format like ``"2022.2"``.
    student_version : bool, optional
        Whether to check for student version sessions. The default is ``False``.
    non_graphical : bool, optional
        Whether to check only for active non-graphical sessions. The default is ``False``.

    Returns
    -------
    List
        List of gRPC ports.
    """
    all_sessions = active_sessions(version, student_version, non_graphical)

    return_list = []
    for _, p in all_sessions.items():
        if p > -1:
            return_list.append(p)
    return return_list


@pyaedt_function_handler(time_vals="time_values", value="data_values")
def compute_fft(time_values, data_values, window=None):  # pragma: no cover
    """Compute FFT of input transient data.

    Parameters
    ----------
    time_values : `pandas.Series`
        Time points corresponding to the x-axis of the input transient data.
    data_values : `pandas.Series`
        Points corresponding to the y-axis.
    time_values : `pandas.Series`
    data_values : `pandas.Series`
    window : str, optional
        Fft window. Options are "hamming", "hanning", "blackman", "bartlett".

    Returns
    -------
    tuple
        Frequency and Values.
    """
    try:
        import numpy as np
    except ImportError:
        pyaedt_logger.error("NumPy is not available. Install it.")
        return False

    deltaT = time_values[-1] - time_values[0]
    num_points = len(time_values)
    win = None
    if window:

        if window == "hamming":
            win = np.hamming(num_points)
        elif window == "hanning":
            win = np.hanning(num_points)
        elif window == "bartlett":
            win = np.bartlett(num_points)
        elif window == "blackman":
            win = np.blackman(num_points)
    if win is not None:
        valueFFT = np.fft.fft(data_values * win, num_points)
    else:
        valueFFT = np.fft.fft(data_values, num_points)
    Npoints = int(len(valueFFT) / 2)
    valueFFT = valueFFT[:Npoints]
    valueFFT = 2 * valueFFT / len(valueFFT)
    n = np.arange(num_points)
    freq = n / deltaT
    return freq, valueFFT


@pyaedt_function_handler(function_str="function")
def conversion_function(data, function=None):  # pragma: no cover
    """Convert input data based on a specified function string.

    The available functions are:

    - `"dB10"`: Converts the data to decibels using base 10 logarithm.
    - `"dB20"`: Converts the data to decibels using base 20 logarithm.
    - `"abs"`: Computes the absolute value of the data.
    - `"real"`: Computes the real part of the data.
    - `"imag"`: Computes the imaginary part of the data.
    - `"norm"`: Normalizes the data to have values between 0 and 1.
    - `"ang"`: Computes the phase angle of the data in radians.
    - `"ang_deg"`: Computes the phase angle of the data in degrees.

    If an invalid function string is specified, the method returns ``False``.

    Parameters
    ----------
    data : list, numpy.array
        Numerical values to convert. The format can be ``list`` or ``numpy.array``.
    function : str, optional
        Conversion function. The default is `"dB10"`.

    Returns
    -------
    numpy.array or bool
        Converted data, ``False`` otherwise.

    Examples
    --------
    >>> values = [1, 2, 3, 4]
    >>> conversion_function(values,"dB10")
    array([-inf, 0., 4.77, 6.02])

    >>> conversion_function(values,"abs")
    array([1, 2, 3, 4])

    >>> conversion_function(values,"ang_deg")
    array([ 0., 0., 0., 0.])
    """
    try:
        import numpy as np
    except ImportError:
        logging.error("NumPy is not available. Install it.")
        return False

    function = function or "dB10"
    available_functions = {
        "dB10": lambda x: 10 * np.log10(np.abs(x)),
        "dB20": lambda x: 20 * np.log10(np.abs(x)),
        "abs": np.abs,
        "real": np.real,
        "imag": np.imag,
        "norm": lambda x: np.abs(x) / np.max(np.abs(x)),
        "ang": np.angle,
        "ang_deg": lambda x: np.angle(x, deg=True),
    }

    if function not in available_functions:
        logging.error("Specified conversion is not available.")
        return False

    data = available_functions[function](data)
    return data


@pyaedt_function_handler(file_name="input_file")
def parse_excitation_file(
    input_file,
    is_time_domain=True,
    x_scale=1,
    y_scale=1,
    impedance=50,
    data_format="Power",
    encoding="utf-8",
    out_mag="Voltage",
    window="hamming",
):
    """Parse a csv file and convert data in list that can be applied to Hfss and Hfss3dLayout sources.

    Parameters
    ----------
    input_file : str
        Full name of the input file.
    is_time_domain : bool, optional
        Either if the input data is Time based or Frequency Based. Frequency based data are Mag/Phase (deg).
    x_scale : float, optional
        Scaling factor for x axis.
    y_scale : float, optional
        Scaling factor for y axis.
    data_format : str, optional
        Either `"Power"`, `"Current"` or `"Voltage"`.
    impedance : float, optional
        Excitation impedance. Default is `50`.
    encoding : str, optional
        Csv file encoding.
    out_mag : str, optional
        Output magnitude format. It can be `"Voltage"` or `"Power"` depending on Hfss solution.
    window : str, optional
        Fft window. Options are ``"hamming"``, ``"hanning"``, ``"blackman"``, ``"bartlett"`` or ``None``.

    Returns
    -------
    tuple
        Frequency, magnitude and phase.
    """
    try:
        import numpy as np
    except ImportError:
        pyaedt_logger.error("NumPy is not available. Install it.")
        return False
    df = read_csv_pandas(input_file, encoding=encoding)
    if is_time_domain:
        time = df[df.keys()[0]].values * x_scale
        val = df[df.keys()[1]].values * y_scale
        freq, fval = compute_fft(time, val, window)

        if data_format.lower() == "current":
            if out_mag == "Voltage":
                fval = fval * impedance
            else:
                fval = fval * fval * impedance
        elif data_format.lower() == "voltage":
            if out_mag == "Power":
                fval = fval * fval / impedance
        else:
            if out_mag == "Voltage":
                fval = np.sqrt(fval * impedance)
        mag = list(np.abs(fval))
        phase = [math.atan2(j, i) * 180 / math.pi for i, j in zip(list(fval.real), list(fval.imag))]

    else:
        freq = list(df[df.keys()[0]].values * x_scale)
        if data_format.lower() == "current":
            mag = df[df.keys()[1]].values * df[df.keys()[1]].values * impedance * y_scale * y_scale
        elif data_format.lower() == "voltage":
            mag = df[df.keys()[1]].values * df[df.keys()[1]].values / impedance * y_scale * y_scale
        else:
            mag = df[df.keys()[1]].values * y_scale
        mag = list(mag)
        phase = list(df[df.keys()[2]].values)
    return freq, mag, phase


@pyaedt_function_handler(tech_path="file_path", unit="units", control_path="output_file")
def tech_to_control_file(file_path, units="nm", output_file=None):
    """Convert a TECH file to an XML file for use in a GDS or DXF import.

    Parameters
    ----------
    file_path : str
        Full path to the TECH file.
    units : str, optional
        Tech units. If specified in tech file this parameter will not be used. Default is ``"nm"``.
    output_file : str, optional
        Path for outputting the XML file.

    Returns
    -------
    str
        Output file path.
    """
    result = []
    with open_file(file_path) as f:
        vals = list(CSS4_COLORS.values())
        id_layer = 0
        for line in f:
            line_split = line.split()
            if len(line_split) == 5:
                layerID, layer_name, _, elevation, layer_height = line.split()
                x = (
                    f'      <Layer Color="{vals[id_layer]}" '
                    f'GDSIIVia="{"true" if layer_name.lower().startswith("v") else "false"}" '
                    f'Name="{layerID}" TargetLayer="{layer_name}" Thickness="{layer_height}"'
                )
                x += ' Type="conductor"/>'
                result.append(x)
                id_layer += 1
            elif len(line_split) > 1 and "UNIT" in line_split[0]:
                units = line_split[1]
    if not output_file:
        output_file = os.path.splitext(file_path)[0] + ".xml"
    with open_file(output_file, "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8" standalone="no" ?>\n')
        f.write('    <c:Control xmlns:c="http://www.ansys.com/control" schemaVersion="1.0">\n')
        f.write("\n")
        f.write('      <Stackup schemaVersion="1.0">\n')
        f.write(f'        <Layers LengthUnit="{units}">\n')
        for res in result:
            f.write(res + "\n")

        f.write("    </Layers>\n")
        f.write("  </Stackup>\n")
        f.write("\n")
        f.write('  <ImportOptions Flatten="true" GDSIIConvertPolygonToCircles="false" ImportDummyNet="true"/>\n')
        f.write("\n")
        f.write("</c:Control>\n")

    return output_file


class PropsManager(object):
    def __getitem__(self, item):
        """Get the `self.props` key value.

        Parameters
        ----------
        item : str
            Key to search
        """
        item_split = item.split("/")
        if len(item_split) == 1:
            item_split = item_split[0].split("__")
        props = self.props
        found_el = []
        matching_percentage = 1
        while matching_percentage >= 0.4:
            for item_value in item_split:
                found_el = self._recursive_search(props, item_value, matching_percentage)
                # found_el = difflib.get_close_matches(item_value, list(props.keys()), 1, matching_percentage)
                if found_el:
                    props = found_el[1][found_el[2]]
                    # props = props[found_el[0]]
            if found_el:
                return props
            else:
                matching_percentage -= 0.02
        self._app.logger.warning("Key %s not found.Check one of available keys in self.available_properties", item)
        return None

    def __setitem__(self, key, value):
        """Set the `self.props` key value.

        Parameters
        ----------
        key : str
            Key to apply.
        value : int, float, bool, str, dict
            Value to apply.
        """
        item_split = key.split("/")
        if len(item_split) == 1:
            item_split = item_split[0].split("__")
        found_el = []
        props = self.props
        matching_percentage = 1
        key_path = []
        while matching_percentage >= 0.4:
            for item_value in item_split:
                found_el = self._recursive_search(props, item_value, matching_percentage)
                if found_el:
                    props = found_el[1][found_el[2]]
                    key_path.append(found_el[2])
            if found_el:
                if matching_percentage < 1:
                    self._app.logger.info(
                        "Key %s matched internal key '%s' with confidence of %s.",
                        key,
                        "/".join(key_path),
                        round(matching_percentage * 100),
                    )
                matching_percentage = 0

            else:
                matching_percentage -= 0.02
        if found_el:
            found_el[1][found_el[2]] = value
            self.update()
        else:
            props[key] = value
            self.update()
            self._app.logger.warning("Key %s not found. Trying to applying new key ", key)

    @pyaedt_function_handler()
    def _recursive_search(self, dict_in, key="", matching_percentage=0.8):
        f = difflib.get_close_matches(key, list(dict_in.keys()), 1, matching_percentage)
        if f:
            return True, dict_in, f[0]
        else:
            for v in list(dict_in.values()):
                if isinstance(v, dict):
                    out_val = self._recursive_search(v, key, matching_percentage)
                    if out_val:
                        return out_val
                elif isinstance(v, list) and isinstance(v[0], dict):
                    for val in v:
                        out_val = self._recursive_search(val, key, matching_percentage)
                        if out_val:
                            return out_val
        return False

    @pyaedt_function_handler()
    def _recursive_list(self, dict_in, prefix=""):
        available_list = []
        for k, v in dict_in.items():
            if prefix:
                name = prefix + "/" + k
            else:
                name = k
            available_list.append(name)
            if isinstance(v, dict):
                available_list.extend(self._recursive_list(v, name))
        return available_list

    @property
    def available_properties(self):
        """Available properties.

        Returns
        -------
        list
        """
        if self.props:
            return self._recursive_list(self.props)
        return []

    @pyaedt_function_handler()
    def update(self):
        """Update method."""
        pass


clamp = lambda n, minn, maxn: max(min(maxn, n), minn)
rgb_color_codes = {
    "Black": (0, 0, 0),
    "Green": (0, 128, 0),
    "White": (255, 255, 255),
    "Red": (255, 0, 0),
    "Lime": (0, 255, 0),
    "Blue": (0, 0, 255),
    "Yellow": (255, 255, 0),
    "Cyan": (0, 255, 255),
    "Magenta": (255, 0, 255),
    "Silver": (192, 192, 192),
    "Gray": (128, 128, 128),
    "Maroon": (128, 0, 0),
    "Olive": (128, 128, 0),
    "Purple": (128, 0, 128),
    "Teal": (0, 128, 128),
    "Navy": (0, 0, 128),
    "copper": (184, 115, 51),
    "stainless steel": (224, 223, 219),
}


# FIXME: Remove usage of random module once IronPython compatibility is removed
def _uname(name=None):
    """Append a 6-digit hash code to a specified name.

    Parameters
    ----------
    name : str
        Name to append the hash code to. The default is ``"NewObject_"``.

    Returns
    -------
    str

    """
    alphabet = string.ascii_uppercase + string.digits

    import secrets

    generator = secrets.SystemRandom()
    unique_name = "".join(secrets.SystemRandom.sample(generator, alphabet, 6))

    if name:
        return name + unique_name
    else:
        return "NewObject_" + unique_name


@pyaedt_function_handler()
def _to_boolean(val):
    """Retrieve the Boolean value of the provided input.

        If the value is a Boolean, return the value.
        Otherwise check to see if the value is in
        ["false", "f", "no", "n", "none", "0", "[]", "{}", "" ]
        and return True if the value is not in the list.

    Parameters
    ----------
    val : bool or str
        Input value to test for True/False condition.

    Returns
    -------
    bool

    """

    if val is True or val is False:
        return val

    false_items = ["false", "f", "no", "n", "none", "0", "[]", "{}", ""]

    return not str(val).strip().lower() in false_items


@pyaedt_function_handler()
def _arg_with_dim(value, units):
    """Concatenate a specified units string to a numerical input.

    Parameters
    ----------
    value : str or number
        Valid expression string in the AEDT modeler. For example, ``"5mm"``.
    units : str
        Valid units string in the AEDT modeler. For example, ``"mm"``.

    Returns
    -------
    str
        Concatenated string with value and units.
    """
    if isinstance(value, str):
        try:
            float(value)
            val = f"{value}{units}"
        except Exception:
            val = value
    else:
        val = f"{value}{units}"
    return val


@pyaedt_function_handler()
def _check_installed_version(install_path, long_version):
    """Check installation folder to determine if it is for specified Ansys EM version.

    Parameters
    ----------
    install_path: str
        Installation folder to check.  For example, ``"C:\\Program Files\\AnsysEM\\v231\\Win64"``.
    long_version: str
        Long form of version number.  For example, ``"2023.1"``.

    Returns
    -------
    bool

    """
    product_list_path = os.path.join(install_path, "config", "ProductList.txt")
    if os.path.isfile(product_list_path):
        try:
            with open_file(product_list_path, "r") as f:
                install_version = f.readline().strip()[-6:]
                if install_version == long_version:
                    return True
        except Exception:
            pyaedt_logger.debug("An error occurred while parsing installation version")
    return False


@pyaedt_function_handler()
def install_with_pip(package_name, package_path=None, upgrade=False, uninstall=False):  # pragma: no cover
    """Install a new package using pip.

    This method is useful for installing a package from the AEDT Console without launching the Python environment.

    Parameters
    ----------
    package_name : str
        Name of the package to install.
    package_path : str, optional
        Path for the GitHub package to download and install. For example, ``git+https://.....``.
    upgrade : bool, optional
        Whether to upgrade the package. The default is ``False``.
    uninstall : bool, optional
        Whether to install the package or uninstall the package.
    """
    import subprocess  # nosec B404

    executable = f'"{sys.executable}"' if is_windows else sys.executable

    commands = []
    if uninstall:
        commands.append([executable, "-m", "pip", "uninstall", "--yes", package_name])
    else:
        if package_path and upgrade:
            commands.append([executable, "-m", "pip", "uninstall", "--yes", package_name])
            command = [executable, "-m", "pip", "install", package_path]
        else:
            command = [executable, "-m", "pip", "install", package_name]
        if upgrade:
            command.append("-U")

        commands.append(command)
    for command in commands:
        if is_linux:
            p = subprocess.Popen(command)
        else:
            p = subprocess.Popen(" ".join(command))
        p.wait()


class Help:  # pragma: no cover
    def __init__(self):
        self._base_path = "https://aedt.docs.pyansys.com/version/stable"
        self.browser = "default"

    def _launch_ur(self, url):
        import webbrowser

        if self.browser != "default":
            webbrowser.get(self.browser).open_new_tab(url)
        else:
            webbrowser.open_new_tab(url)

    def search(self, keywords, app_name=None, search_in_examples_only=False):
        """Search for one or more keywords.

        Parameters
        ----------
        keywords : str or list
        app_name : str, optional
            Name of a PyAEDT app. For example, ``"Hfss"``, ``"Circuit"``, ``"Icepak"``, or any other available app.
        search_in_examples_only : bool, optional
            Whether to search for the one or more keywords only in the PyAEDT examples.
            The default is ``False``.
        """
        if isinstance(keywords, str):
            keywords = [keywords]
        if search_in_examples_only:
            keywords.append("This example")
        if app_name:
            keywords.append(app_name)
        url = self._base_path + f"/search.html?q={'+'.join(keywords)}"
        self._launch_ur(url)

    def getting_started(self):
        """Open the PyAEDT User guide page."""
        url = self._base_path + "/User_guide/index.html"
        self._launch_ur(url)

    def examples(self):
        """Open the PyAEDT Examples page."""
        url = self._base_path + "/examples/index.html"
        self._launch_ur(url)

    def github(self):
        """Open the PyAEDT GitHub page."""
        url = "https://github.com/ansys/pyaedt"
        self._launch_ur(url)

    def changelog(self, release=None):
        """Open the PyAEDT GitHub Changelog for a given release.

        Parameters
        ----------
        release : str, optional
            Release to get the changelog for. For example, ``"0.6.70"``.
        """
        if release is None:
            from ansys.aedt.core import __version__ as release
        url = "https://github.com/ansys/pyaedt/releases/tag/v" + release
        self._launch_ur(url)

    def issues(self):
        """Open the PyAEDT GitHub Issues page."""
        url = "https://github.com/ansys/pyaedt/issues"
        self._launch_ur(url)

    def ansys_forum(self):
        """Open the PyAEDT GitHub Issues page."""
        url = "https://discuss.ansys.com/discussions/tagged/pyaedt"
        self._launch_ur(url)

    def developer_forum(self):
        """Open the Discussions page on the Ansys Developer site."""
        url = "https://developer.ansys.com/"
        self._launch_ur(url)


# class Property(property):
#
#     @pyaedt_function_handler()
#     def getter(self, fget):
#         """Property getter."""
#         return self.__class__.__base__(fget, self.fset, self.fdel, self.__doc__)
#
#     @pyaedt_function_handler()
#     def setter(self, fset):
#         """Property setter."""
#         return self.__class__.__base__(self.fget, fset, self.fdel, self.__doc__)
#
#     @pyaedt_function_handler()
#     def deleter(self, fdel):
#         """Property deleter."""
#         return self.__class__.__base__(self.fget, self.fset, fdel, self.__doc__)

# property = Property

online_help = Help()
