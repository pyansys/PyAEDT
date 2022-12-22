"""
This module contains the ``Siwave`` class.

The ``Siwave`` module can be initialized as standalone before launching an app or
automatically initialized by an app to the latest installed AEDT version.

"""
from __future__ import absolute_import  # noreorder

import os
import pkgutil
import sys
import time

from pyaedt.generic.clr_module import _clr
from pyaedt.generic.general_methods import _pythonver
from pyaedt.generic.general_methods import is_ironpython
from pyaedt.generic.general_methods import pyaedt_function_handler
from pyaedt.misc import list_installed_ansysem


class Siwave:
    """Initializes SIwave based on the inputs provided and manages SIwave release and closing.

    Parameters
    ----------
    specified_version : str, optional
        Version of AEDT to use. The default is ``None``, in which case
        the active setup is used or the latest installed version is used.

    """

    @property
    def version_keys(self):
        """Version keys for AEDT."""

        self._version_keys = []
        self._version_ids = {}

        version_list = list_installed_ansysem()
        for version_env_var in version_list:
            current_version_id = version_env_var.replace("ANSYSEM_ROOT", "").replace("ANSYSEMSV_ROOT", "")
            version = int(current_version_id[0:2])
            release = int(current_version_id[2])
            if version < 20:
                if release < 3:
                    version -= 1
                else:
                    release -= 2
            v_key = "20{0}.{1}".format(version, release)
            self._version_keys.append(v_key)
            self._version_ids[v_key] = version_env_var
        return self._version_keys

    @property
    def current_version(self):
        """Current version of AEDT."""
        return self.version_keys[0]

    def __init__(self, specified_version=None):  # pragma: no cover
        if is_ironpython:
            _com = "pythonnet"
            import System
        elif os.name == "nt":  # pragma: no cover
            modules = [tup[1] for tup in pkgutil.iter_modules()]
            if _clr:
                import win32com.client

                _com = "pythonnet_v3"
            elif "win32com" in modules:
                import win32com.client

                _com = "pywin32"
            else:
                raise Exception("Error. No win32com.client or PythonNET modules are found. They need to be installed.")
        self._main = sys.modules["__main__"]
        print("Launching Siwave Init")
        if "oSiwave" in dir(self._main) and self._main.oSiwave is not None:
            self._main.AEDTVersion = self._main.oSiwave.GetVersion()[0:6]
            self._main.oSiwave.RestoreWindow()
            specified_version = self.current_version
            assert specified_version in self.version_keys, "Specified version {} is not known.".format(
                specified_version
            )
            version_key = specified_version
            base_path = os.getenv(self._version_ids[specified_version])
            self._main.sDesktopinstallDirectory = base_path
        else:
            if specified_version:
                assert specified_version in self.version_keys, "Specified version {} is not known.".format(
                    specified_version
                )
                version_key = specified_version
            else:
                version_key = self.current_version
            base_path = os.getenv(self._version_ids[version_key])
            self._main = sys.modules["__main__"]
            self._main.sDesktopinstallDirectory = base_path
            version = "Siwave.Application." + version_key
            self._main.AEDTVersion = version_key
            self._main.interpreter = _com
            self._main.interpreter_ver = _pythonver
            if "oSiwave" in dir(self._main):
                del self._main.oSiwave

            if _com == "pythonnet":
                self._main.oSiwave = System.Activator.CreateInstance(System.Type.GetTypeFromProgID(version))

            elif _com == "pythonnet_v3":
                # TODO check if possible to use pythonnet. at the moment the tool open AEDt
                # but doesn't return the wrapper of oApp
                print("Launching Siwave with module win32com.")

                self._main.oSiwave = win32com.client.Dispatch(version)

            self._main.AEDTVersion = version_key
            self.oSiwave = self._main.oSiwave
            self._main.oSiwave.RestoreWindow()
        self._main.siwave_initialized = True
        self._oproject = self.oSiwave.GetActiveProject()
        pass

    @property
    def project_name(self):
        """Project name.

        Returns
        -------
        str
            Name of the project.

        """
        return self._oproject.GetName()

    @property
    def project_path(self):
        """Project path.

        Returns
        -------
        str
            Full absolute path for the project.

        """
        return os.path.normpath(self.oSiwave.GetProjectDirectory())

    @property
    def project_file(self):
        """Project file.

        Returns
        -------
        str
            Full absolute path and name for the project file.

        """
        return os.path.join(self.project_path, self.project_name + ".siw")

    @property
    def lock_file(self):
        """Lock file.

        Returns
        -------
        str
            Full absolute path and name for the project lock file.

        """
        return os.path.join(self.project_path, self.project_name + ".siw.lock")

    @property
    def results_directory(self):
        """Results directory.

        Returns
        -------
        str
            Full absolute path to the ``aedtresults`` directory.
        """
        return os.path.join(self.project_path, self.project_name + ".siwresults")

    @property
    def oproject(self):
        """Project."""
        return self._oproject

    @pyaedt_function_handler()
    def open_project(self, proj_path=None):
        """Open a project.

        Parameters
        ----------
        proj_path : str, optional
            Full path to the project. The default is ``None``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """

        if os.path.exists(proj_path):
            open_result = self.oSiwave.OpenProject(proj_path)
            self._oproject = self.oSiwave.GetActiveProject()
            return open_result
        else:
            return False

    @pyaedt_function_handler()
    def save_project(self, projectpath=None, projectName=None):
        """Save the project.

        Parameters
        ----------
        proj_path : str, optional
            Full path to the project. The default is ``None``.
        projectName : str, optional
             Name of the project. The default is ``None``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        if projectName and projectpath:
            self.oproject.ScrSaveProjectAs(os.path.join(projectpath, projectName + ".siw"))
        else:
            self.oproject.Save()
        return True

    @pyaedt_function_handler()
    def close_project(self, save_project=False):
        """Close the project.

        Parameters
        ----------
        save_project : bool, optional
            Whether to save the current project before closing it. The default is ``False``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        if save_project:
            self.save_project()
        self.oproject.ScrCloseProject()
        self._oproject = None
        return True

    @pyaedt_function_handler()
    def quit_application(self):
        """Quit the application.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        self._main.oSiwave.Quit()
        return True

    @pyaedt_function_handler()
    def export_element_data(self, simulation_name, file_path, data_type="Vias"):
        """Export element data.

        Parameters
        ----------
        simulation_name :

        file_path :

        data_type : str, optional
            The default is ``"Vias"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        self.oproject.ScrExportElementData(simulation_name, file_path, data_type)
        return True

    @pyaedt_function_handler()
    def export_siwave_report(self, simulation_name, file_path, bkground_color="White"):
        """Export the SiwaveE report.

        Parameters
        ----------
        simulation_name :

        file_path :

        bkground_color : str, optional
            Color of the report's background. The default is ``"White"``.


        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        self.oproject.ScrExportDcSimReportScaling("All", "All", -1, -1, False)
        self.oproject.ScrExportDcSimReport(simulation_name, bkground_color, file_path)
        while not os.path.exists(file_path):
            time.sleep(0.1)
        return True
