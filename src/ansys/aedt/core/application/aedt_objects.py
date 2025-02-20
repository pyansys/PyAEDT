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

import sys
import time

from ansys.aedt.core.application.aedt_units import AedtUnits
from ansys.aedt.core.generic.desktop_sessions import _desktop_sessions
from ansys.aedt.core.generic.general_methods import is_linux
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.generic.general_methods import settings


class AedtObjects(object):
    def __init__(self, desktop=None, project=None, design=None, is_inherithed=False):
        self._odesign = design
        self._oproject = project
        if desktop:
            self._odesktop = desktop.odesktop
        elif _desktop_sessions and project:
            project_name = project.GetName()
            for desktop in list(_desktop_sessions.values()):
                if project_name in list(desktop.project_list):
                    self._odesktop = desktop.odesktop
                    break
        elif _desktop_sessions:
            self._odesktop = list(_desktop_sessions.values())[-1].odesktop
        elif "oDesktop" in dir(sys.modules["__main__"]):  # ironpython
            self._odesktop = sys.modules["__main__"].oDesktop  # ironpython

        if not is_inherithed:
            if project:
                if design:
                    self._odesign = design
                else:
                    self._odesign = self._oproject.GetActiveDesign()
            else:
                self._oproject = self._odesktop.GetActiveProject()
                if self._oproject:
                    self._odesign = self._oproject.GetActiveDesign()
        self._oboundary = None
        self._oimport_export = None
        self._ooptimetrics = None
        self._ooutput_variable = None
        self._oanalysis = None
        self._odefinition_manager = None
        self._omaterial_manager = None
        self._omodel_setup = None
        self._o_maxwell_parameters = None
        self._omonitor = None
        self._osolution = None
        self._oexcitation = None
        self._omatrix = None
        self._ofieldsreporter = None
        self._oreportsetup = None
        self._omeshmodule = None
        self._oeditor = None
        self._layouteditor = None
        self._o_component_manager = None
        self._o_model_manager = None
        self._o_symbol_manager = None
        self._opadstackmanager = None
        self._oradfield = None
        self._onetwork_data_explorer = None
        self.__aedtunits = AedtUnits(self)

    @property
    def units(self):
        """PyAEDT default units.

        Returns
        -------
        :class:`ansys.aedt.core.application.aedt_units.AedtUnits`

        """
        return self.__aedtunits

    @property
    def oradfield(self):
        """AEDT Radiation Field Object.

        References
        ----------
        >>> oDesign.GetModule("RadField")
        """
        if self.design_type == "HFSS" and self._odesign.GetSolutionType() not in ["EigenMode", "Characteristic Mode"]:
            return self._odesign.GetModule("RadField")
        return None

    @pyaedt_function_handler()
    def get_module(self, module_name):
        """Aedt Module object."""
        if self.design_type not in ["EMIT"] and self._odesign:
            try:
                return self._odesign.GetModule(module_name)
            except Exception:
                return None
        return None

    @property
    def o_symbol_manager(self):
        """Aedt Symbol Manager.

        References
        ----------
        >>> oSymbolManager = oDefinitionManager.GetManager("Symbol")
        """
        if self.odefinition_manager:
            return self.odefinition_manager.GetManager("Symbol")
        return

    @property
    def opadstackmanager(self):
        """AEDT oPadstackManager.

        References
        ----------
        >>> oPadstackManger = oDefinitionManager.GetManager("Padstack")
        """
        if self._oproject and not self._opadstackmanager:
            self._opadstackmanager = self._oproject.GetDefinitionManager().GetManager("Padstack")
        return self._opadstackmanager

    @property
    def design_type(self):
        return self._odesign.GetDesignType()

    @property
    def oboundary(self):
        """Boundary Object."""
        if not self._oboundary:
            if self.design_type in ["Twin Builder", "RMxprt", "RMxprtSolution", "Circuit Design", "Circuit Netlist"]:
                return
            if self.design_type in ["HFSS 3D Layout Design", "HFSS3DLayout"]:
                self._oboundary = self.get_module("Excitations")
            else:
                self._oboundary = self.get_module("BoundarySetup")
        return self._oboundary

    @property
    def oimport_export(self):
        """Import/Export Manager Module.

        References
        ----------
        >>> oDesktop.GetTool("ImportExport")
        """
        if not self._oimport_export:
            self._oimport_export = self._odesktop.GetTool("ImportExport")
        return self._oimport_export

    @property
    def ooptimetrics(self):
        """AEDT Optimetrics Module.

        References
        ----------
        >>> oDesign.GetModule("Optimetrics")
        """
        if not self._ooptimetrics and self.design_type not in ["Circuit Netlist", "Maxwell Circuit", "EMIT"]:
            self._ooptimetrics = self.get_module("Optimetrics")
        return self._ooptimetrics

    @property
    def ooutput_variable(self):
        """AEDT Output Variable Module.

        References
        ----------
        >>> oDesign.GetModule("OutputVariable")
        """
        if not self._ooutput_variable and self.design_type not in ["EMIT", "Maxwell Circuit", "Circuit Netlist"]:
            self._ooutput_variable = self.get_module("OutputVariable")
        return self._ooutput_variable

    @property
    def oanalysis(self):
        """Analysis AEDT Module.

        References
        ----------
        >>> oDesign.GetModule("SolveSetups")
        >>> oDesign.GetModule("SimSetup")
        >>> oDesign.GetModule("AnalysisSetup")
        """
        if self._oanalysis:
            return self._oanalysis
        if "HFSS 3D Layout Design" in self.design_type:
            self._oanalysis = self.get_module("SolveSetups")
        elif self.design_type in ["EMIT", "Circuit Netlist", "Maxwell Circuit"]:
            self._oanalysis = None
        elif "Circuit Design" in self.design_type or "Twin Builder" in self.design_type:
            self._oanalysis = self.get_module("SimSetup")
        else:
            self._oanalysis = self.get_module("AnalysisSetup")
        return self._oanalysis

    @property
    def odefinition_manager(self):
        """Definition Manager Module.

        References
        ----------
        >>> oDefinitionManager = oProject.GetDefinitionManager()
        """
        if not self._odefinition_manager and self._oproject:
            self._odefinition_manager = self._oproject.GetDefinitionManager()
        return self._odefinition_manager

    @property
    def omaterial_manager(self):
        """Material Manager Module.

        References
        ----------
        >>> oMaterialManager = oDefinitionManager.GetManager("Material")
        """
        if self.odefinition_manager and not self._omaterial_manager:
            self._omaterial_manager = self.odefinition_manager.GetManager("Material")
        return self._omaterial_manager

    @property
    def omodelsetup(self):
        """AEDT Model Setup Object.

        References
        ----------
        >>> oDesign.GetModule("ModelSetup")
        """
        if self.design_type not in ["Maxwell 3D", "Maxwell 2D", "HFSS"]:
            return
        if not self._omodel_setup:
            if (
                self.design_type in ["Maxwell 3D", "Maxwell 2D"]
                and self._odesign.GetSolutionType() == "Transient"
                or self.design_type == "HFSS"
            ):
                self._omodel_setup = self.get_module("ModelSetup")
        return self._omodel_setup

    @property
    def o_maxwell_parameters(self):
        """AEDT Maxwell Parameter Setup Object.

        References
        ----------
        >>> oDesign.GetModule("MaxwellParameterSetup")
        """
        if self._odesign and self.design_type not in ["Maxwell 3D", "Maxwell 2D"]:
            return
        if not self._o_maxwell_parameters:
            self._o_maxwell_parameters = self.get_module("MaxwellParameterSetup")
        return self._o_maxwell_parameters

    @property
    def omonitor(self):
        """AEDT Monitor Object."""
        if not self._odesign or not self.design_type == "Icepak":
            return
        if not self._omonitor:
            self._omonitor = self.get_module("Monitor")
        return self._omonitor

    @property
    def osolution(self):
        """Solution Module.

        References
        ----------
        >>> oModule = oDesign.GetModule("Solutions")
        """
        if not self._osolution:
            if self.design_type in [
                "RMxprt",
                "RMxprtSolution",
                "Twin Builder",
                "Circuit Design",
                "Maxwell Circuit",
                "Circuit Netlist",
            ]:
                return
            if self.design_type in ["HFSS 3D Layout Design", "HFSS3DLayout"]:
                self._osolution = self.get_module("SolveSetups")
            else:
                self._osolution = self.get_module("Solutions")
        return self._osolution

    @property
    def oexcitation(self):
        """Solution Module.

        References
        ----------
        >>> oModule = oDesign.GetModule("Excitations")
        """
        if self.design_type not in ["HFSS3DLayout", "HFSS 3D Layout Design"]:
            return
        if not self._oexcitation:
            self._oexcitation = self.get_module("Excitations")

        return self._oexcitation

    @property
    def omatrix(self):
        """Matrix Object."""
        if self.design_type not in ["Q3D Extractor", "2D Extractor"]:
            return
        if not self._omatrix:
            self._omatrix = self.get_module("ReduceMatrix")
        return self._omatrix

    @property
    def ofieldsreporter(self):
        """Fields reporter.

        Returns
        -------
        :attr:`ansys.aedt.core.modules.post_general.PostProcessor.ofieldsreporter`

        References
        ----------
        >>> oDesign.GetModule("FieldsReporter")
        """
        if self.design_type in [
            "Circuit Design",
            "Circuit Netlist",
            "Twin Builder",
            "Maxwell Circuit",
            "EMIT",
            "RMxprt",
            "RMxprtSolution",
        ]:
            return
        if not self._ofieldsreporter:
            self._ofieldsreporter = self.get_module("FieldsReporter")
        return self._ofieldsreporter

    @property
    def oreportsetup(self):
        """Report setup.

        Returns
        -------
        :attr:`ansys.aedt.core.modules.post_general.PostProcessor.oreportsetup`

        References
        ----------
        >>> oDesign.GetModule("ReportSetup")
        """
        if not self._oreportsetup:
            self._oreportsetup = self.get_module("ReportSetup")
        return self._oreportsetup

    @property
    def omeshmodule(self):
        """Icepak Mesh Module.

        References
        ----------
        >>> oDesign.GetModule("MeshRegion")
        """
        meshers = {
            "HFSS": "MeshSetup",
            "Icepak": "MeshRegion",
            "HFSS 3D Layout Design": "SolveSetups",
            "HFSS3DLayout": "SolveSetups",
            "Maxwell 2D": "MeshSetup",
            "Maxwell 3D": "MeshSetup",
            "Q3D Extractor": "MeshSetup",
            "Mechanical": "MeshSetup",
            "2D Extractor": "MeshSetup",
        }
        if not self._omeshmodule and self.design_type in meshers:
            self._omeshmodule = self.get_module(meshers[self.design_type])
        return self._omeshmodule

    @property
    def oeditor(self):
        """Oeditor Module.

        References
        ----------
        >>> oEditor = oDesign.SetActiveEditor("SchematicEditor")"""
        if not self._oeditor and self._odesign:
            if self.design_type in ["Circuit Design"]:
                self._oeditor = self._odesign.GetEditor("SchematicEditor")
                if is_linux and settings.aedt_version == "2024.1":  # pragma: no cover
                    time.sleep(1)
                    self.desktop_class.close_windows()
            elif self.design_type in ["Twin Builder", "Maxwell Circuit", "EMIT"]:
                self._oeditor = self._odesign.SetActiveEditor("SchematicEditor")
                if is_linux and settings.aedt_version == "2024.1":  # pragma: no cover
                    time.sleep(1)
                    self.desktop_class.close_windows()
            elif self.design_type in ["HFSS 3D Layout Design", "HFSS3DLayout"]:
                self._oeditor = self._odesign.GetEditor("Layout")
            elif self.design_type in ["RMxprt", "RMxprtSolution"]:
                self._oeditor = self._odesign.SetActiveEditor("Machine")
            elif self.design_type in ["Circuit Netlist"]:
                self._oeditor = None
            else:
                self._oeditor = self._odesign.SetActiveEditor("3D Modeler")
        return self._oeditor

    @property
    def layouteditor(self):
        """Return the Circuit Layout Editor.

        References
        ----------
        >>> oDesign.SetActiveEditor("Layout")
        """
        if not self._layouteditor and self.design_type in ["Circuit Design"]:
            self._layouteditor = self._odesign.GetEditor("Layout")
        return self._layouteditor

    @property
    def o_component_manager(self):
        """Component manager object."""
        if not self._o_component_manager and self.odefinition_manager:
            self._o_component_manager = self.odefinition_manager.GetManager("Component")
        return self._o_component_manager

    @property
    def o_model_manager(self):
        """Model manager object."""
        if not self._o_model_manager and self.odefinition_manager:
            self._o_model_manager = self.odefinition_manager.GetManager("Model")
        return self._o_model_manager

    @property
    def onetwork_data_explorer(self):
        """Network data explorer module.

        References
        ----------
        >>> oDesktop.GetTool("NdExplorer")
        """
        if not self._onetwork_data_explorer:
            self._onetwork_data_explorer = self._odesktop.GetTool("NdExplorer")
        return self._onetwork_data_explorer
