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
        self._wb = None

    @pyaedt_function_handler()
    def open_workbench(self, non_graphical=False):
        """Open the Workbench application.
        Same Workbench version as Electronics Desktop is used.

        Parameters
        ----------
        non_graphical : bool, optional
            Whether to launch Workbench in non-graphical mode.
            The default is ``False``, in which case Workbench is launched in graphical mode.
        """
        msg = "non graphical" if non_graphical else "graphical"
        self.logger.info("Opening Workbench in {} mode.".format(msg))

        try:
            self._wb = AutomateWB(
                non_graphical=non_graphical,
                hostname=None,
                port_number=None,
                workbench_version=settings.aedt_version,
            )
        except Exception as e:
            # WB failed to initialize the class
            raise e

        return self._wb.launch_workbench()

    @pyaedt_function_handler()
    def add_design_to_workbench(self, aedt_project_file, aedt_design_name, wb_project_name=None):
        """Add the specified project in Workbench.

        TO BE FINISHED!!!

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

        self._wb.import_hfss(aedt_design_name)
