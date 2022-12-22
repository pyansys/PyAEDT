"""
This module contains the ``Workbench`` class.

This module is used to initialize Workbench class and provide all methods to connect AEDT with Workbench
It is designed to be called and accessed from Desktop class.
"""

import os

from pyaedt import pyaedt_function_handler
from pyaedt import pyaedt_logger
from pyaedt import settings
from pyaedt.generic.filesystem import create_toolkit_directory
from pyaedt.workbench.WBFlowAutomation import AutomateWB


class Workbench:
    """Initializes Workbench class based on the inputs provided.
    It is designed to be called and accessed from Desktop class.

    Parameters
    ----------
    desktop : class
        instance of the calling Desktop class.

    """

    def __init__(self, desktop):
        self._desktop = desktop
        self.logger = pyaedt_logger

    @pyaedt_function_handler()
    def add_design_to_workbench(self, aedt_project_file, aedt_design_name, wb_project_name=None):
        """Add the specified project in Workbench.
        Same Workbench version as Electronics Desktop is used.

        Parameters
        ----------
        aedt_project_file : str
            Electronics Desktop project file.
            The AEDT project file, specified with full path, containing the design that will be
            imported in Workbench.
            The only supported design types are: HFSS, Maxwell 2D, Maxwell 3D, Q3D, Q3D 2D.

        aedt_design_name : str
            HFSS design that will be imported in Workbench.

        wb_project_name : str, optional
            Workbench project name.
            The Workbench project file is created in the same folder where the aedt project file is located.
            If wb_project_name is ``None`` than the aedt project name is used.
            The default is ``None``.

        Returns
        -------

        """
        self.logger.info("Adding project to Workbench")
        self.logger.debug("Launch Workbench and Load WBMultiphysics.py and Mechanical Scripts")

        # check the file
        prjdir = os.path.dirname(aedt_project_file)
        prjname = os.path.splitext(os.path.basename(aedt_project_file))[0]
        if not os.path.isfile(aedt_project_file):
            self.logger.error("The specified AEDT project file does not exist!")
            return False
        if os.path.exists(aedt_project_file + ".lock"):
            self.logger.error("The specified AEDT project is locked! Please close the project.")
            return False
        # Set the wb project name
        if wb_project_name:
            wb_project_fullname = os.path.join(prjdir, wb_project_name + ".wbpj")
        else:
            wb_project_fullname = os.path.join(prjdir, prjname + ".wbpj")

        # set the toolkit directory
        toolkit_directory = create_toolkit_directory(aedt_project_file)

        self._wb = AutomateWB(
            project_fullname=wb_project_fullname,
            results_path=toolkit_directory,
            pictures_path=toolkit_directory,
            WBGui=not settings.non_graphical,
            MechGui=not settings.non_graphical,
            hostname="localhost",
            sWorkbenchVersion=settings.aedt_version,
            useSC=True,
            useDM=False,
            materialHFSS=False,
            AEDTproject_fullname=aedt_project_file,
            GEOMproject_fullname=None,
        )
        self._wb.launch_workbench()
        self._wb.import_hfss(aedt_design_name)
