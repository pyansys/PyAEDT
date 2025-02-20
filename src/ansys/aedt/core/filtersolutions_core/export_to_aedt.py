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

from ctypes import POINTER
from ctypes import byref
from ctypes import c_bool
from ctypes import c_char_p
from ctypes import c_int
from ctypes import create_string_buffer
from enum import Enum
import os
from typing import Union

import ansys.aedt.core


class ExportFormat(Enum):
    """Provides an enum of export format types.

    **Attributes:**

    - DIRECT_TO_AEDT: Represents a direct export to ``AEDT``.
    - PYTHON: Represents a Python scripted export.
    """

    DIRECT_TO_AEDT = 0
    PYTHON_SCRIPT = 1


class ExportCreationMode(Enum):
    """Provides an enum of export creation modes.

    **Attributes:**

    - OVERWRITE: Represents export to ``AEDT`` and overwrite to existing design.
    - APPEND: Represents export to ``AEDT`` and append to existing design.
    """

    OVERWRITE = 0
    APPEND = 1


class PartLibraries(Enum):
    """Provides an enum of export format types.

    **Attributes:**

    - LUMPED = Represents a lumped part library.
    - INTERCONNECT_ONLY = Represents an interconnect only part library.
    - MODELITHICS = Represents a ``Modelithics`` part library.
    """

    LUMPED = 0
    INTERCONNECT = 1
    MODELITHICS = 2


class SubstrateType(Enum):
    """Provides an enum of substrate types for various materials.

    **Attributes:**

    - RGLC = Represents a RGLC substrate type.
    - STRIPLINE = Represents a stripline substrate type.
    - MICROSTRIP = Represents a microstrip substrate type.
    - SUSPEND = Represents a suspended substrate type.
    - INVERTED = Represents an inverted substrate type.
    """

    RGLC = 0
    STRIPLINE = 1
    MICROSTRIP = 2
    SUSPEND = 3
    INVERTED = 4


class SubstrateEr(Enum):
    """Provides an enum of substrate relative permitivity (``Er``) for various materials.

    The enum values represent common materials used in substrates and their associated ``Er`` value.

    **Attributes:**

    - AIR = Represents air substrate with an ``Er`` of ``1.00``.
    - ALUMINA = Represents alumina substrate with an ``Er`` of ``9.8``.
    - GA_AS = Represents Gallium Arsenide substrate with an ``Er`` of ``12.9``.
    - GERMANIUM = Represents Germanium substrate with an ``Er`` of ``16.0``.
    - INDIUM_PHOSPHATE = Represents Indium Phosphate substrate with an ``Er`` of ``12.4``.
    - SILICON = Represents Silicon substrate with an ``Er`` of ``11.7``.
    - QUARTZ = Represents Quartz substrate with an ``Er`` of ``3.78``.
    - RT_DUROID_5880 = Represents RT Duroid 5880 substrate with an ``Er`` of ``2.2``.
    - RT_DUROID_5870 = Represents RT Duroid 5870 substrate with an ``Er`` of ``2.33``.
    - RT_DUROID_6006 = Represents RT Duroid 6006 substrate with an ``Er`` of ``6.15``.
    - G_10_LOW_RESIN = Represents G-10 Low Resin substrate with an ``Er`` of ``4.8``.
    - G_10_HIGH_RESIN = Represents G-10 High Resin substrate with an ``Er`` of ``3.5``.
    - PAPER_PHONELIC = Represents Paper Phenolic substrate with an ``Er`` of ``4.5``.
    - POLYTHYLENE = Represents Polyethylene substrate with an ``Er`` of ``2.25``.
    - POLYSTYRENE = Represents Polystyrene substrate with an ``Er`` of ``2.56``.
    - CORNING_GLASS_7059 = Represents Corning Glass 7059 substrate with an ``Er`` of ``7.9``.
    - BERYLIUM_OXIDE = Represents Beryllium Oxide substrate with an ``Er`` of ``6.7``.
    """

    AIR = 0
    ALUMINA = 1
    GA_AS = 2
    GERMANIUM = 3
    INDIUM_PHOSPHATE = 4
    SILICON = 5
    QUARTZ = 6
    RT_DUROID_5880 = 7
    RT_DUROID_5870 = 8
    RT_DUROID_6006 = 9
    G_10_LOW_RESIN = 10
    G_10_HIGH_RESIN = 11
    PAPER_PHONELIC = 12
    POLYTHYLENE = 13
    POLYSTYRENE = 14
    CORNING_GLASS_7059 = 15
    BERYLIUM_OXIDE = 16


class SubstrateResistivity(Enum):
    """Provides an enum of substrate resistivity types for various materials.

    The enum values represent common materials used in substrates and their associated resistivity index.

    **Attributes:**

    - IDEAL: Represents an ideal, perfect conductor, ``0`` with respect to copper resistivity.
    - SILVER: Represents Silver resitivity, ``0.95`` with respect to copper resistivity.
    - COPPER: Represents Copper, ``1.00`` as referernce resistivity.
    - GOLD: Represents Gold, ``1.43`` with respect to copper resistivity.
    - ALUMINUM: Represents Aluminum, ``1.67`` with respect to copper resistivity.
    - MAGNESIUM: Represents Magnesium, ``2.67`` with respect to copper resistivity.
    - TUNGSTEN: Represents Tungsten, ``3.23`` with respect to copper resistivity.
    - ZINC: Represents Zinc, ``3.56`` with respect to copper resistivity.
    - NICKEL: Represents Nickel, ``4.00`` with respect to copper resistivity.
    - IRON: Represents Iron, ``5.80`` with respect to copper resistivity.
    - PLATINUM: Represents Platinum, ``6.34`` with respect to copper resistivity.
    """

    IDEAL = 0
    SILVER = 1
    COPPER = 2
    GOLD = 3
    ALUMINUM = 4
    MAGNESIUM = 5
    TUNGSTEN = 6
    ZINC = 7
    NICKEL = 8
    IRON = 9
    PLATINUM = 10


class ExportToAedt:
    """Defines attributes and parameters for exporting filter .

    This class allows you to define and modify the parameters for exporting a designed filter to ``AEDT``.
    """

    def __init__(self):
        self._dll = ansys.aedt.core.filtersolutions_core._dll_interface()._dll
        self._dll_interface = ansys.aedt.core.filtersolutions_core._dll_interface()
        self._define_export_to_desktop_dll_functions()
        self._substrate_er = SubstrateEr.AIR.value  # Default to AIR's Er value

    def _define_export_to_desktop_dll_functions(self):
        """Define C++ API DLL functions."""

        self._dll.setSchematicName.argtype = c_char_p
        self._dll.setSchematicName.restype = c_int
        self._dll.getSchematicName.argtypes = [c_char_p, c_int]
        self._dll.getSchematicName.restype = c_int

        self._dll.setSimulateAfterExport.argtype = c_bool
        self._dll.setSimulateAfterExport.restype = c_int
        self._dll.getSimulateAfterExport.argtype = POINTER(c_bool)
        self._dll.getSimulateAfterExport.restype = c_int

        self._dll.setGroupDelay.argtype = c_bool
        self._dll.setGroupDelay.restype = c_int
        self._dll.getGroupDelay.argtype = POINTER(c_bool)
        self._dll.getGroupDelay.restype = c_int

        self._dll.setGTGain.argtype = c_bool
        self._dll.setGTGain.restype = c_int
        self._dll.getGTGain.argtype = POINTER(c_bool)
        self._dll.getGTGain.restype = c_int

        self._dll.setVGSL.argtype = c_bool
        self._dll.setVGSL.restype = c_int
        self._dll.getVGSL.argtype = POINTER(c_bool)
        self._dll.getVGSL.restype = c_int

        self._dll.setVGIN.argtype = c_bool
        self._dll.setVGIN.restype = c_int
        self._dll.getVGIN.argtype = POINTER(c_bool)
        self._dll.getVGIN.restype = c_int

        self._dll.setS11.argtype = c_bool
        self._dll.setS11.restype = c_int
        self._dll.getS11.argtype = POINTER(c_bool)
        self._dll.getS11.restype = c_int

        self._dll.setS21.argtype = c_bool
        self._dll.setS21.restype = c_int
        self._dll.getS21.argtype = POINTER(c_bool)
        self._dll.getS21.restype = c_int

        self._dll.setS12.argtype = c_bool
        self._dll.setS12.restype = c_int
        self._dll.getS12.argtype = POINTER(c_bool)
        self._dll.getS12.restype = c_int

        self._dll.setS22.argtype = c_bool
        self._dll.setS22.restype = c_int
        self._dll.getS22.argtype = POINTER(c_bool)
        self._dll.getS22.restype = c_int

        self._dll.setDbFormat.argtype = c_bool
        self._dll.setDbFormat.restype = c_int
        self._dll.getDbFormat.argtype = POINTER(c_bool)
        self._dll.getDbFormat.restype = c_int

        self._dll.setRectPlot.argtype = c_bool
        self._dll.setRectPlot.restype = c_int
        self._dll.getRectPlot.argtype = POINTER(c_bool)
        self._dll.getRectPlot.restype = c_int

        self._dll.setSmithPlot.argtype = c_bool
        self._dll.setSmithPlot.restype = c_int
        self._dll.getSmithPlot.argtype = POINTER(c_bool)
        self._dll.getSmithPlot.restype = c_int

        self._dll.setPolarPlot.argtype = c_bool
        self._dll.setPolarPlot.restype = c_int
        self._dll.getPolarPlot.argtype = POINTER(c_bool)
        self._dll.getPolarPlot.restype = c_int

        self._dll.setTableData.argtype = c_bool
        self._dll.setTableData.restype = c_int
        self._dll.getTableData.argtype = POINTER(c_bool)
        self._dll.getTableData.restype = c_int

        self._dll.setOptimetrics.argtype = c_bool
        self._dll.setOptimetrics.restype = c_int
        self._dll.getOptimetrics.argtype = POINTER(c_bool)
        self._dll.getOptimetrics.restype = c_int

        self._dll.setOptimizeAfterExport.argtype = c_bool
        self._dll.setOptimizeAfterExport.restype = c_int
        self._dll.getOptimizeAfterExport.argtype = POINTER(c_bool)
        self._dll.getOptimizeAfterExport.restype = c_int

        self._dll.loadLibraryPartsConf.argtype = c_char_p
        self._dll.loadLibraryPartsConf.restype = c_int

        self._dll.saveLibraryPartsConf.argtype = c_char_p
        self._dll.saveLibraryPartsConf.restype = c_int

        self._dll.importTunedVariablesSize.argtype = POINTER(c_int)
        self._dll.importTunedVariablesSize.restype = c_int
        self._dll.importTunedVariables.argtypes = [c_char_p, c_int]
        self._dll.importTunedVariables.restype = c_int

        self._dll.setPartLibraries.argtype = c_int
        self._dll.setPartLibraries.restype = c_int
        self._dll.getPartLibraries.argtype = POINTER(c_int)
        self._dll.getPartLibraries.restype = c_int

        self._dll.setLengthToWidthRatio.argtype = c_char_p
        self._dll.setLengthToWidthRatio.restype = c_int
        self._dll.getLengthToWidthRatio.argtypes = [c_char_p, c_int]
        self._dll.getLengthToWidthRatio.restype = c_int

        self._dll.setLowerLengthGeometricLimitRatio.argtype = c_char_p
        self._dll.setLowerLengthGeometricLimitRatio.restype = c_int
        self._dll.getLowerLengthGeometricLimitRatio.argtypes = [c_char_p, c_int]
        self._dll.getLowerLengthGeometricLimitRatio.restype = c_int

        self._dll.setUpperLengthGeometricLimitRatio.argtype = c_char_p
        self._dll.setUpperLengthGeometricLimitRatio.restype = c_int
        self._dll.getUpperLengthGeometricLimitRatio.argtypes = [c_char_p, c_int]
        self._dll.getUpperLengthGeometricLimitRatio.restype = c_int

        self._dll.setLineWidthToTerminationWidthRatio.argtype = c_char_p
        self._dll.setLineWidthToTerminationWidthRatio.restype = c_int
        self._dll.getLineWidthToTerminationWidthRatio.argtypes = [c_char_p, c_int]
        self._dll.getLineWidthToTerminationWidthRatio.restype = c_int

        self._dll.setLowerWidthGeometricLimitRatio.argtype = c_char_p
        self._dll.setLowerWidthGeometricLimitRatio.restype = c_int
        self._dll.getLowerWidthGeometricLimitRatio.argtypes = [c_char_p, c_int]
        self._dll.getLowerWidthGeometricLimitRatio.restype = c_int

        self._dll.setUpperWidthGeometricLimitRatio.argtype = c_char_p
        self._dll.setUpperWidthGeometricLimitRatio.restype = c_int
        self._dll.getUpperWidthGeometricLimitRatio.argtypes = [c_char_p, c_int]
        self._dll.getUpperWidthGeometricLimitRatio.restype = c_int

        self._dll.setLengthToWidthValue.argtype = c_char_p
        self._dll.setLengthToWidthValue.restype = c_int
        self._dll.getLengthToWidthValue.argtypes = [c_char_p, c_int]
        self._dll.getLengthToWidthValue.restype = c_int

        self._dll.setLowerLengthGeometricLimitValue.argtype = c_char_p
        self._dll.setLowerLengthGeometricLimitValue.restype = c_int
        self._dll.getLowerLengthGeometricLimitValue.argtypes = [c_char_p, c_int]
        self._dll.getLowerLengthGeometricLimitValue.restype = c_int

        self._dll.setUpperLengthGeometricLimitValue.argtype = c_char_p
        self._dll.setUpperLengthGeometricLimitValue.restype = c_int
        self._dll.getUpperLengthGeometricLimitValue.argtypes = [c_char_p, c_int]
        self._dll.getUpperLengthGeometricLimitValue.restype = c_int

        self._dll.setLineWidthToTerminationWidthValue.argtype = c_char_p
        self._dll.setLineWidthToTerminationWidthValue.restype = c_int
        self._dll.getLineWidthToTerminationWidthValue.argtypes = [c_char_p, c_int]
        self._dll.getLineWidthToTerminationWidthValue.restype = c_int

        self._dll.setLowerWidthGeometricLimitValue.argtype = c_char_p
        self._dll.setLowerWidthGeometricLimitValue.restype = c_int
        self._dll.getLowerWidthGeometricLimitValue.argtypes = [c_char_p, c_int]
        self._dll.getLowerWidthGeometricLimitValue.restype = c_int

        self._dll.setUpperWidthGeometricLimitValue.argtype = c_char_p
        self._dll.setUpperWidthGeometricLimitValue.restype = c_int
        self._dll.getUpperWidthGeometricLimitValue.argtypes = [c_char_p, c_int]
        self._dll.getUpperWidthGeometricLimitValue.restype = c_int

        self._dll.setInterConnectInductorTolerance.argtype = c_char_p
        self._dll.setInterConnectInductorTolerance.restype = c_int
        self._dll.getInterConnectInductorTolerance.argtypes = [c_char_p, c_int]
        self._dll.getInterConnectInductorTolerance.restype = c_int

        self._dll.setInterConnectCapacitorTolerance.argtype = c_char_p
        self._dll.setInterConnectCapacitorTolerance.restype = c_int
        self._dll.getInterConnectCapacitorTolerance.argtypes = [c_char_p, c_int]
        self._dll.getInterConnectCapacitorTolerance.restype = c_int

        self._dll.setInterconnectGeometryOptimization.argtype = c_bool
        self._dll.setInterconnectGeometryOptimization.restype = c_int
        self._dll.getInterconnectGeometryOptimization.argtype = POINTER(c_bool)
        self._dll.getInterconnectGeometryOptimization.restype = c_int

        self._dll.setSubstrateType.argtype = c_char_p
        self._dll.setSubstrateType.restype = int
        self._dll.getSubstrateType.argtypes = [c_char_p, c_int]
        self._dll.getSubstrateType.restype = int

        self._dll.setEr.argtype = [c_char_p, c_int]
        self._dll.setEr.restype = c_int
        self._dll.getEr.argtype = [c_char_p, POINTER(c_int), c_int]
        self._dll.getEr.restype = c_int

        self._dll.setResistivity.argtype = [c_char_p, c_int]
        self._dll.setResistivity.restype = c_int
        self._dll.getResistivity.argtype = [c_char_p, POINTER(c_int), c_int]
        self._dll.getResistivity.restype = c_int

        self._dll.setLossTangent.argtype = [c_char_p, c_int]
        self._dll.setLossTangent.restype = c_int
        self._dll.getLossTangent.argtype = [c_char_p, POINTER(c_int), c_int]
        self._dll.getLossTangent.restype = c_int

        self._dll.setConductorThickness.argtype = c_char_p
        self._dll.setConductorThickness.restype = c_int
        self._dll.getConductorThickness.argtypes = [c_char_p, c_int]
        self._dll.getConductorThickness.restype = c_int

        self._dll.setDielectricHeight.argtype = c_char_p
        self._dll.setDielectricHeight.restype = c_int
        self._dll.getDielectricHeight.argtypes = [c_char_p, c_int]
        self._dll.getDielectricHeight.restype = c_int

        self._dll.setLowerDielectricHeight.argtype = c_char_p
        self._dll.setLowerDielectricHeight.restype = c_int
        self._dll.getLowerDielectricHeight.argtypes = [c_char_p, c_int]
        self._dll.getLowerDielectricHeight.restype = c_int

        self._dll.setSuspendDielectricHeight.argtype = c_char_p
        self._dll.setSuspendDielectricHeight.restype = c_int
        self._dll.getSuspendDielectricHeight.argtypes = [c_char_p, c_int]
        self._dll.getSuspendDielectricHeight.restype = c_int

        self._dll.setCoverHeight.argtype = c_char_p
        self._dll.setCoverHeight.restype = c_int
        self._dll.getCoverHeight.argtypes = [c_char_p, c_int]
        self._dll.getCoverHeight.restype = c_int

        self._dll.setUnbalancedStripLine.argtype = c_bool
        self._dll.setUnbalancedStripLine.restype = c_int
        self._dll.getUnbalancedStripLine.argtype = POINTER(c_bool)
        self._dll.getUnbalancedStripLine.restype = c_int

        self._dll.setGroundedCoverAboveLine.argtype = c_bool
        self._dll.setGroundedCoverAboveLine.restype = c_int
        self._dll.getGroundedCoverAboveLine.argtype = POINTER(c_bool)
        self._dll.getGroundedCoverAboveLine.restype = c_int

        self._dll.setModelithicsIncludeInterconnect.argtype = c_bool
        self._dll.setModelithicsIncludeInterconnect.restype = c_int
        self._dll.getModelithicsIncludeInterconnect.argtype = POINTER(c_bool)
        self._dll.getModelithicsIncludeInterconnect.restype = c_int

        self._dll.getModelithicsInductorsListCount.argtype = POINTER(c_int)
        self._dll.getModelithicsInductorsListCount.restype = c_int

        self._dll.getModelithicsInductorsList.argtype = [c_int, c_char_p, c_int]
        self._dll.getModelithicsInductorsList.restype = c_int

        self._dll.setModelithicsInductors.argtype = c_char_p
        self._dll.setModelithicsInductors.restype = c_int
        self._dll.getModelithicsInductors.argtypes = [c_char_p, c_int]
        self._dll.getModelithicsInductors.restype = c_int

        self._dll.getModelithicsInductorsFamilyListCount.argtype = POINTER(c_int)
        self._dll.getModelithicsInductorsFamilyListCount.restype = c_int

        self._dll.getModelithicsInductorsFamilyList.argtype = [c_int, c_char_p, c_int]
        self._dll.getModelithicsInductorsFamilyList.restype = c_int

        self._dll.addModelithicsInductorsFamily.argtype = c_char_p
        self._dll.addModelithicsInductorsFamily.restype = c_int

        self._dll.removeModelithicsInductorsFamily.argtype = c_char_p
        self._dll.removeModelithicsInductorsFamily.restype = c_int

        self._dll.getModelithicsCapacitorsListCount.argtype = POINTER(c_int)
        self._dll.getModelithicsCapacitorsListCount.restype = c_int

        self._dll.getModelithicsCapacitorsList.argtype = [c_int, c_char_p, c_int]
        self._dll.getModelithicsCapacitorsList.restype = c_int

        self._dll.setModelithicsCapacitors.argtype = c_char_p
        self._dll.setModelithicsCapacitors.restype = c_int
        self._dll.getModelithicsCapacitors.argtypes = [c_char_p, c_int]
        self._dll.getModelithicsCapacitors.restype = c_int

        self._dll.getModelithicsCapacitorsFamilyListCount.argtype = POINTER(c_int)
        self._dll.getModelithicsCapacitorsFamilyListCount.restype = c_int

        self._dll.getModelithicsCapacitorsFamilyList.argtype = [c_int, c_char_p, c_int]
        self._dll.getModelithicsCapacitorsFamilyList.restype = c_int

        self._dll.addModelithicsCapacitorsFamily.argtype = c_char_p
        self._dll.addModelithicsCapacitorsFamily.restype = c_int

        self._dll.removeModelithicsCapacitorsFamily.argtype = c_char_p
        self._dll.removeModelithicsCapacitorsFamily.restype = c_int

        self._dll.getModelithicsResistorsListCount.argtype = POINTER(c_int)
        self._dll.getModelithicsResistorsListCount.restype = c_int

        self._dll.getModelithicsResistorsList.argtype = [c_int, c_char_p, c_int]
        self._dll.getModelithicsResistorsList.restype = c_int

        self._dll.setModelithicsResistors.argtype = c_char_p
        self._dll.setModelithicsResistors.restype = c_int
        self._dll.getModelithicsResistors.argtypes = [c_char_p, c_int]
        self._dll.getModelithicsResistors.restype = c_int

        self._dll.getModelithicsResistorsFamilyListCount.argtype = POINTER(c_int)
        self._dll.getModelithicsResistorsFamilyListCount.restype = c_int

        self._dll.getModelithicsResistorsFamilyList.argtype = [c_int, c_char_p, c_int]
        self._dll.getModelithicsResistorsFamilyList.restype = c_int

        self._dll.addModelithicsResistorsFamily.argtype = c_char_p
        self._dll.addModelithicsResistorsFamily.restype = c_int
        self._dll.removeModelithicsResistorsFamily.argtype = c_char_p
        self._dll.removeModelithicsResistorsFamily.restype = c_int

        self._dll.setCircuitDesign.argtype = c_bool
        self._dll.setCircuitDesign.restype = c_int
        self._dll.getCircuitDesign.argtype = POINTER(c_bool)
        self._dll.getCircuitDesign.restype = c_int

        self._dll.setHFSSDesign.argtype = c_bool
        self._dll.setHFSSDesign.restype = c_int
        self._dll.getHFSSDesign.argtype = POINTER(c_bool)
        self._dll.getHFSSDesign.restype = c_int

        self._dll.setHFSS3DLDesign.argtype = c_bool
        self._dll.setHFSS3DLDesign.restype = c_int
        self._dll.getHFSS3DLDesign.argtype = POINTER(c_bool)
        self._dll.getHFSS3DLDesign.restype = c_int

        self._dll.setFullParametrization.argtype = c_bool
        self._dll.setFullParametrization.restype = c_int
        self._dll.getFullParametrization.argtype = POINTER(c_bool)
        self._dll.getFullParametrization.restype = c_int

        self._dll.setPortsOnSides.argtype = c_bool
        self._dll.setPortsOnSides.restype = c_int
        self._dll.getPortsOnSides.argtype = POINTER(c_bool)
        self._dll.getPortsOnSides.restype = c_int

        self._dll.setFlipXAxis.argtype = c_bool
        self._dll.setFlipXAxis.restype = c_int
        self._dll.getFlipXAxis.argtype = POINTER(c_bool)
        self._dll.getFlipXAxis.restype = c_int

        self._dll.setFlipYAxis.argtype = c_bool
        self._dll.setFlipYAxis.restype = c_int
        self._dll.getFlipYAxis.argtype = POINTER(c_bool)
        self._dll.getFlipYAxis.restype = c_int

        self._dll.setIncludeTuningPorts.argtype = c_bool
        self._dll.setIncludeTuningPorts.restype = c_int
        self._dll.getIncludeTuningPorts.argtype = POINTER(c_bool)
        self._dll.getIncludeTuningPorts.restype = c_int

        self._dll.setSeriesHorizontalPorts.argtype = c_bool
        self._dll.setSeriesHorizontalPorts.restype = c_int
        self._dll.getSeriesHorizontalPorts.argtype = POINTER(c_bool)
        self._dll.getSeriesHorizontalPorts.restype = c_int

    @property
    def schematic_name(self) -> str:
        """Name of the exported schematic in ``AEDT``, displayed as the project and design names.

        The default name is ``FilterSolutions`` if not specified.

        Returns
        -------
        str
        """
        schematic_name_string = self._dll_interface.get_string(self._dll.getSchematicName)
        return schematic_name_string

    @schematic_name.setter
    def schematic_name(self, schematic_name_string):
        self._dll_interface.set_string(self._dll.setSchematicName, schematic_name_string)

    @property
    def simulate_after_export_enabled(self) -> bool:
        """Flag indicating if the simulation will be initiated upon export to ``AEDT``.

        Returns
        -------
        bool
        """
        simulate_after_export_enabled = c_bool()
        status = self._dll.getSimulateAfterExport(byref(simulate_after_export_enabled))
        self._dll_interface.raise_error(status)
        return bool(simulate_after_export_enabled.value)

    @simulate_after_export_enabled.setter
    def simulate_after_export_enabled(self, simulate_after_export_enabled: bool):
        status = self._dll.setSimulateAfterExport(simulate_after_export_enabled)
        self._dll_interface.raise_error(status)

    @property
    def include_group_delay_enabled(self) -> bool:
        """Flag indicating if the group delay report will be created upon export to ``AEDT``.

        Returns
        -------
        bool
        """
        include_group_delay_enabled = c_bool()
        status = self._dll.getGroupDelay(byref(include_group_delay_enabled))
        self._dll_interface.raise_error(status)
        return bool(include_group_delay_enabled.value)

    @include_group_delay_enabled.setter
    def include_group_delay_enabled(self, include_group_delay_enabled: bool):
        status = self._dll.setGroupDelay(include_group_delay_enabled)
        self._dll_interface.raise_error(status)

    @property
    def include_gt_gain_enabled(self) -> bool:
        """Flag indicating if the total voltage gain report will be created upon export to ``AEDT``.

        Returns
        -------
        bool
        """
        include_gt_gain_enabled = c_bool()
        status = self._dll.getGTGain(byref(include_gt_gain_enabled))
        self._dll_interface.raise_error(status)
        return bool(include_gt_gain_enabled.value)

    @include_gt_gain_enabled.setter
    def include_gt_gain_enabled(self, include_gt_gain_enabled: bool):
        status = self._dll.setGTGain(include_gt_gain_enabled)
        self._dll_interface.raise_error(status)

    @property
    def include_vgsl_enabled(self) -> bool:
        """Flag indicating if the voltage gain source load report will be created upon export to ``AEDT``.

        Returns
        -------
        bool
        """
        include_vgsl_enabled = c_bool()
        status = self._dll.getVGSL(byref(include_vgsl_enabled))
        self._dll_interface.raise_error(status)
        return bool(include_vgsl_enabled.value)

    @include_vgsl_enabled.setter
    def include_vgsl_enabled(self, include_vgsl_enabled: bool):
        status = self._dll.setVGSL(include_vgsl_enabled)
        self._dll_interface.raise_error(status)

    @property
    def include_vgin_enabled(self) -> bool:
        """Flag indicating if the voltage gain insertion report will be created upon export to ``AEDT``.

        Returns
        -------
        bool
        """
        include_vgin_enabled = c_bool()
        status = self._dll.getVGIN(byref(include_vgin_enabled))
        self._dll_interface.raise_error(status)
        return bool(include_vgin_enabled.value)

    @include_vgin_enabled.setter
    def include_vgin_enabled(self, include_vgin_enabled: bool):
        status = self._dll.setVGIN(include_vgin_enabled)
        self._dll_interface.raise_error(status)

    @property
    def include_input_return_loss_s11_enabled(self) -> bool:
        """Flag indicating if the input return loss report will be created upon
        export to ``AEDT``.

        Returns
        -------
        bool
        """
        include_input_return_loss_s11_enabled = c_bool()
        status = self._dll.getS11(byref(include_input_return_loss_s11_enabled))
        self._dll_interface.raise_error(status)
        return bool(include_input_return_loss_s11_enabled.value)

    @include_input_return_loss_s11_enabled.setter
    def include_input_return_loss_s11_enabled(self, include_input_return_loss_s11_enabled: bool):
        status = self._dll.setS11(include_input_return_loss_s11_enabled)
        self._dll_interface.raise_error(status)

    @property
    def include_forward_transfer_s21_enabled(self) -> bool:
        """Flag indicating if the forward transfer gain report will be created upon export to ``AEDT``.

        Returns
        -------
        bool
        """
        include_forward_transfer_s21_enabled = c_bool()
        status = self._dll.getS21(byref(include_forward_transfer_s21_enabled))
        self._dll_interface.raise_error(status)
        return bool(include_forward_transfer_s21_enabled.value)

    @include_forward_transfer_s21_enabled.setter
    def include_forward_transfer_s21_enabled(self, include_forward_transfer_s21_enabled: bool):
        status = self._dll.setS21(include_forward_transfer_s21_enabled)
        self._dll_interface.raise_error(status)

    @property
    def include_reverse_transfer_s12_enabled(self) -> bool:
        """Flag indicating if the reverse transfer gain report will be created upon export to ``AEDT``.

        Returns
        -------
        bool
        """
        include_reverse_transfer_s12_enabled = c_bool()
        status = self._dll.getS12(byref(include_reverse_transfer_s12_enabled))
        self._dll_interface.raise_error(status)
        return bool(include_reverse_transfer_s12_enabled.value)

    @include_reverse_transfer_s12_enabled.setter
    def include_reverse_transfer_s12_enabled(self, include_reverse_transfer_s12_enabled: bool):
        status = self._dll.setS12(include_reverse_transfer_s12_enabled)
        self._dll_interface.raise_error(status)

    @property
    def include_output_return_loss_s22_enabled(self) -> bool:
        """Flag indicating if the output return loss report will be created upon export to ``AEDT``.

        Returns
        -------
        bool
        """
        include_output_return_loss_s22_enabled = c_bool()
        status = self._dll.getS22(byref(include_output_return_loss_s22_enabled))
        self._dll_interface.raise_error(status)
        return bool(include_output_return_loss_s22_enabled.value)

    @include_output_return_loss_s22_enabled.setter
    def include_output_return_loss_s22_enabled(self, include_output_return_loss_s22_enabled: bool):
        status = self._dll.setS22(include_output_return_loss_s22_enabled)
        self._dll_interface.raise_error(status)

    @property
    def db_format_enabled(self) -> bool:
        """Flag indicating if the report format in dB in the exported filter to ``AEDT`` is enabled.

        Returns
        -------
        bool
        """
        db_format_enabled = c_bool()
        status = self._dll.getDbFormat(byref(db_format_enabled))
        self._dll_interface.raise_error(status)
        return bool(db_format_enabled.value)

    @db_format_enabled.setter
    def db_format_enabled(self, db_format_enabled: bool):
        status = self._dll.setDbFormat(db_format_enabled)
        self._dll_interface.raise_error(status)

    @property
    def rectangular_plot_enabled(self) -> bool:
        """Flag indicating if the rectangular report format in the
         exported filter to ``AEDT`` is enabled.

        Returns
        -------
        bool
        """
        rectangular_plot_enabled = c_bool()
        status = self._dll.getRectPlot(byref(rectangular_plot_enabled))
        self._dll_interface.raise_error(status)
        return bool(rectangular_plot_enabled.value)

    @rectangular_plot_enabled.setter
    def rectangular_plot_enabled(self, rectangular_plot_enabled: bool):
        status = self._dll.setRectPlot(rectangular_plot_enabled)
        self._dll_interface.raise_error(status)

    @property
    def smith_plot_enabled(self) -> bool:
        """Flag indicating if the ``Smith Chart`` report format in the
         exported filter to ``AEDT`` is enabled.

        Returns
        -------
        bool
        """
        smith_plot_enabled = c_bool()
        status = self._dll.getSmithPlot(byref(smith_plot_enabled))
        self._dll_interface.raise_error(status)
        return bool(smith_plot_enabled.value)

    @smith_plot_enabled.setter
    def smith_plot_enabled(self, smith_plot_enabled: bool):
        status = self._dll.setSmithPlot(smith_plot_enabled)
        self._dll_interface.raise_error(status)

    @property
    def polar_plot_enabled(self) -> bool:
        """Flag indicating if the polar report format in the exported filter to ``AEDT`` is enabled.

        Returns
        -------
        bool
        """
        polar_plot_enabled = c_bool()
        status = self._dll.getPolarPlot(byref(polar_plot_enabled))
        self._dll_interface.raise_error(status)
        return bool(polar_plot_enabled.value)

    @polar_plot_enabled.setter
    def polar_plot_enabled(self, polar_plot_enabled: bool):
        status = self._dll.setPolarPlot(polar_plot_enabled)
        self._dll_interface.raise_error(status)

    @property
    def table_data_enabled(self) -> bool:
        """Flag indicating if the table data format in the exported filter to ``AEDT`` is enabled.

        Returns
        -------
        bool
        """
        table_data_enabled = c_bool()
        status = self._dll.getTableData(byref(table_data_enabled))
        self._dll_interface.raise_error(status)
        return bool(table_data_enabled.value)

    @table_data_enabled.setter
    def table_data_enabled(self, table_data_enabled: bool):
        status = self._dll.setTableData(table_data_enabled)
        self._dll_interface.raise_error(status)

    @property
    def optimitrics_enabled(self) -> bool:
        """Flag indicating if the optimitric parameters in the exported filter to ``AEDT`` is enabled.

        Returns
        -------
        bool
        """
        optimitrics_enabled = c_bool()
        status = self._dll.getOptimetrics(byref(optimitrics_enabled))
        self._dll_interface.raise_error(status)
        return bool(optimitrics_enabled.value)

    @optimitrics_enabled.setter
    def optimitrics_enabled(self, optimitrics_enabled: bool):
        status = self._dll.setOptimetrics(optimitrics_enabled)
        self._dll_interface.raise_error(status)

    @property
    def optimize_after_export_enabled(self) -> bool:
        """Flag indicating if the optimization after exporting to ``AEDT`` is enabled.

        Returns
        -------
        bool
        """
        optimize_after_export_enabled = c_bool()
        status = self._dll.getOptimizeAfterExport(byref(optimize_after_export_enabled))
        self._dll_interface.raise_error(status)
        return bool(optimize_after_export_enabled.value)

    @optimize_after_export_enabled.setter
    def optimize_after_export_enabled(self, optimize_after_export_enabled: bool):
        status = self._dll.setOptimizeAfterExport(optimize_after_export_enabled)
        self._dll_interface.raise_error(status)

    def export_design(self, export_format=None, export_creation_mode=None, export_path=None):
        """Export the design directly to ``AEDT` or generate a ``Python`` script for exporting.

        When exporting to ``AEDT``, the design can either be appended to an existing project or overwrite it.
        When generating a Python script, the script is created and saved to the specified file location.

        Parameters
        ----------
        export_format : `ExportFormat`
            The export format type.
            The default is ``None``.
        design_creation_mode : `ExportCreationMode`
            The design creation mode.
            The default is ``None``.
        export_path : str
            The export path for Python script.
            The default is ``None``.
        """
        if export_format is None:
            export_format = ExportFormat.DIRECT_TO_AEDT
        if export_creation_mode is None:
            export_creation_mode = ExportCreationMode.OVERWRITE
        if export_path is None:
            export_path = ""
        else:
            directory_path = os.path.dirname(export_path)
            # Check if the directory path exists, if not, create it to ensure the export path is valid
            if not os.path.exists(directory_path):
                os.makedirs(directory_path)
        export_path_bytes = bytes(export_path, "ascii")
        status = self._dll.exportDesign(export_format.value, export_creation_mode.value, export_path_bytes)
        self._dll_interface.raise_error(status)

    def load_library_parts_config(self, load_library_parts_config_string):
        self._dll_interface.set_string(self._dll.loadLibraryPartsConf, load_library_parts_config_string)

    def save_library_parts_config(self, save_library_parts_config_string):
        self._dll_interface.set_string(self._dll.saveLibraryPartsConf, save_library_parts_config_string)

    def import_tuned_variables(self):
        """Imported ``AEDT`` tuned parameter variables back into the ``FilterSolutions`` project."""
        size = c_int()
        status = self._dll.importTunedVariablesSize(byref(size))
        self._dll_interface.raise_error(status)
        netlist_string = self._dll_interface.get_string(self._dll.importTunedVariables, max_size=size.value)
        return netlist_string

    @property
    def part_libraries(self) -> PartLibraries:
        """Part libraries selection. The default is ``LUMPED``.

        The ``PartLibraries`` enum provides a list of all options.

        Returns
        -------
        :enum:`PartLibraries`
        """
        index = c_int()
        part_libraries_list = list(PartLibraries)
        status = self._dll.getPartLibraries(byref(index))
        self._dll_interface.raise_error(status)
        part_libraries = part_libraries_list[index.value]
        return part_libraries

    @part_libraries.setter
    def part_libraries(self, library_type: PartLibraries):
        status = self._dll.setPartLibraries(library_type.value)
        self._dll_interface.raise_error(status)

    @property
    def interconnect_length_to_width_ratio(self) -> str:
        """Length to width ratio of interconnect line.

        The length to width ratio is a measure of the proportion between the length and width of the interconnect line.
        This ratio is important for determining the electrical characteristics of the interconnect, such as impedance
        and signal integrity.
        The default is ``2``.

        Returns
        -------
        str
        """
        interconnect_length_to_width_ratio_string = self._dll_interface.get_string(self._dll.getLengthToWidthRatio)
        return interconnect_length_to_width_ratio_string

    @interconnect_length_to_width_ratio.setter
    def interconnect_length_to_width_ratio(self, interconnect_length_to_width_ratio_string):
        self._dll_interface.set_string(self._dll.setLengthToWidthRatio, interconnect_length_to_width_ratio_string)

    @property
    def interconnect_minimum_length_to_width_ratio(self) -> str:
        """Minimum length to width ratio of interconnect line.

        The minimum length to width ratio is a measure of the smallest proportion between the length and width
        of the interconnect line that is allowed. This parameter is used to determine the minimum dimensions of
        interconnect lines for optimization purposes.
        The default is ``0.5``.

        Returns
        -------
        str
        """
        interconnect_minimum_length_to_width_ratio_string = self._dll_interface.get_string(
            self._dll.getLowerLengthGeometricLimitRatio
        )
        return interconnect_minimum_length_to_width_ratio_string

    @interconnect_minimum_length_to_width_ratio.setter
    def interconnect_minimum_length_to_width_ratio(self, interconnect_minimum_length_to_width_ratio_string):
        self._dll_interface.set_string(
            self._dll.setLowerLengthGeometricLimitRatio, interconnect_minimum_length_to_width_ratio_string
        )

    @property
    def interconnect_maximum_length_to_width_ratio(self) -> str:
        """Maximum length to width ratio of interconnect line.

        The maximum length to width ratio is a measure of the largest proportion between the length and width
        of the interconnect line that is allowed. This parameter is used to determine the maximum dimensions of
        interconnect lines for optimization purposes.
        The default is ``2``.

        Returns
        -------
        str
        """
        interconnect_maximum_length_to_width_ratio_string = self._dll_interface.get_string(
            self._dll.getUpperLengthGeometricLimitRatio
        )
        return interconnect_maximum_length_to_width_ratio_string

    @interconnect_maximum_length_to_width_ratio.setter
    def interconnect_maximum_length_to_width_ratio(self, interconnect_maximum_length_to_width_ratio_string):
        self._dll_interface.set_string(
            self._dll.setUpperLengthGeometricLimitRatio, interconnect_maximum_length_to_width_ratio_string
        )

    @property
    def interconnect_line_to_termination_width_ratio(self) -> str:
        """Line width to termination width ratio of interconnect line.

        The line width to termination width ratio is a measure of the proportion between the width of the
        interconnect line and the width of its termination. This ratio is crucial for ensuring proper
        impedance matching and signal integrity at the points where the interconnect line connects to
        other components or circuits.
        The default is ``1``.

        Returns
        -------
        str
        """
        interconnect_line_to_termination_width_ratio_string = self._dll_interface.get_string(
            self._dll.getLineWidthToTerminationWidthRatio
        )
        return interconnect_line_to_termination_width_ratio_string

    @interconnect_line_to_termination_width_ratio.setter
    def interconnect_line_to_termination_width_ratio(self, interconnect_line_to_termination_width_ratio_string):
        self._dll_interface.set_string(
            self._dll.setLineWidthToTerminationWidthRatio, interconnect_line_to_termination_width_ratio_string
        )

    @property
    def interconnect_minimum_line_to_termination_width_ratio(self) -> str:
        """Minimum line width to termination width ratio of interconnect line.

        The minimum line width to termination width ratio is a measure of the smallest proportion between the
        width of the interconnect line and the width of its termination that is allowed. This parameter is used
        to determine the minimum dimensions of interconnect lines for optimization purposes.
        The default is ``0.5``.

        Returns
        -------
        str
        """
        interconnect_minimum_line_to_termination_width_ratio_string = self._dll_interface.get_string(
            self._dll.getLowerWidthGeometricLimitRatio
        )
        return interconnect_minimum_line_to_termination_width_ratio_string

    @interconnect_minimum_line_to_termination_width_ratio.setter
    def interconnect_minimum_line_to_termination_width_ratio(
        self, interconnect_minimum_line_to_termination_width_ratio_string
    ):
        self._dll_interface.set_string(
            self._dll.setLowerWidthGeometricLimitRatio, interconnect_minimum_line_to_termination_width_ratio_string
        )

    @property
    def interconnect_maximum_line_to_termination_width_ratio(self) -> str:
        """Maximum line width to termination width ratio of interconnect line.

        The maximum line width to termination width ratio is a measure of the largest proportion between the
        width of the interconnect line and the width of its termination that is allowed. This parameter is used
        to determine the maximum dimensions of interconnect lines for optimization purposes.
        The default is ``2``.

        Returns
        -------
        str
        """
        interconnect_maximum_line_to_termination_width_ratio_string = self._dll_interface.get_string(
            self._dll.getUpperWidthGeometricLimitRatio
        )
        return interconnect_maximum_line_to_termination_width_ratio_string

    @interconnect_maximum_line_to_termination_width_ratio.setter
    def interconnect_maximum_line_to_termination_width_ratio(
        self, interconnect_maximum_line_to_termination_width_ratio_string
    ):
        self._dll_interface.set_string(
            self._dll.setUpperWidthGeometricLimitRatio, interconnect_maximum_line_to_termination_width_ratio_string
        )

    @property
    def interconnect_length_value(self) -> str:
        """Interconnect physical length value.

        The interconnect physical length value represents the actual length of the interconnect line in the design.
        This value is crucial for determining the electrical characteristics of the interconnect, such as signal delay,
        impedance, and potential signal loss. Accurate length measurements are essential for ensuring that the
        interconnect performsas expected in high-frequency and high-speed applications.
        The default is ``2.54 mm``.

        Returns
        -------
        str
        """
        interconnect_length_value_string = self._dll_interface.get_string(self._dll.getLengthToWidthValue)
        return interconnect_length_value_string

    @interconnect_length_value.setter
    def interconnect_length_value(self, interconnect_length_value_string):
        self._dll_interface.set_string(self._dll.setLengthToWidthValue, interconnect_length_value_string)

    @property
    def interconnect_minimum_length_value(self) -> str:
        """Minimum value of interconnect physical length.

        The minimum value of the interconnect physical length represents the smallest length that the interconnect
        line can have in the design. This value is used to determine the minimum dimensions of interconnect lines
        for optimization purposes.
        The default is ``1.27 mm``.

        Returns
        -------
        str
        """
        interconnect_minimum_length_value_string = self._dll_interface.get_string(
            self._dll.getLowerLengthGeometricLimitValue
        )
        return interconnect_minimum_length_value_string

    @interconnect_minimum_length_value.setter
    def interconnect_minimum_length_value(self, interconnect_minimum_length_value_string):
        self._dll_interface.set_string(
            self._dll.setLowerLengthGeometricLimitValue, interconnect_minimum_length_value_string
        )

    @property
    def interconnect_maximum_length_value(self) -> str:
        """Maximum value of interconnect physical length.
        The maximum value of the interconnect physical length represents the largest length that the interconnect
        line can have in the design. This value is used to determine the maximum dimensions of interconnect lines
        for optimization purposes.
        The default is ``5.08 mm``.

        Returns
        -------
        str
        """
        interconnect_maximum_length_value_string = self._dll_interface.get_string(
            self._dll.getUpperLengthGeometricLimitValue
        )
        return interconnect_maximum_length_value_string

    @interconnect_maximum_length_value.setter
    def interconnect_maximum_length_value(self, interconnect_maximum_length_value_string):
        self._dll_interface.set_string(
            self._dll.setUpperLengthGeometricLimitValue, interconnect_maximum_length_value_string
        )

    @property
    def interconnect_line_width_value(self) -> str:
        """Interconnect conductor width value.

        The interconnect conductor width value represents the actual width of the interconnect line in the design.
        This value is crucial for determining the electrical characteristics of the interconnect, such as impedance,
        signal integrity, and potential signal loss. Accurate width measurements are essential for ensuring that the
        interconnect performs as expected in high-frequency and high-speed applications.
        The default is ``1.27 mm``.

        Returns
        -------
        str
        """
        interconnect_line_width_value_string = self._dll_interface.get_string(
            self._dll.getLineWidthToTerminationWidthValue
        )
        return interconnect_line_width_value_string

    @interconnect_line_width_value.setter
    def interconnect_line_width_value(self, interconnect_line_width_value_string):
        self._dll_interface.set_string(
            self._dll.setLineWidthToTerminationWidthValue, interconnect_line_width_value_string
        )

    @property
    def interconnect_minimum_width_value(self) -> str:
        """Minimum value of interconnect conductor width.

        The minimum value of the interconnect conductor width represents the smallest width that the interconnect
        line can have in the design. This value is used to determine the minimum dimensions of interconnect lines
        for optimization purposes.
        The default is ``635 um``.

        Returns
        -------
        str
        """
        interconnect_minimum_width_value_string = self._dll_interface.get_string(
            self._dll.getLowerWidthGeometricLimitValue
        )
        return interconnect_minimum_width_value_string

    @interconnect_minimum_width_value.setter
    def interconnect_minimum_width_value(self, interconnect_minimum_width_value_string):
        self._dll_interface.set_string(
            self._dll.setLowerWidthGeometricLimitValue, interconnect_minimum_width_value_string
        )

    @property
    def interconnect_maximum_width_value(self) -> str:
        """Maximum value of interconnect conductor width.

        The maximum value of the interconnect conductor width represents the largest width that the interconnect
        line can have in the design. This value is used to determine the maximum dimensions of interconnect lines
        for optimization purposes.
        The default is ``2.54 mm``.

        Returns
        -------
        str
        """
        interconnect_maximum_width_value_string = self._dll_interface.get_string(
            self._dll.getUpperWidthGeometricLimitValue
        )
        return interconnect_maximum_width_value_string

    @interconnect_maximum_width_value.setter
    def interconnect_maximum_width_value(self, interconnect_maximum_width_value_string):
        self._dll_interface.set_string(
            self._dll.setUpperWidthGeometricLimitValue, interconnect_maximum_width_value_string
        )

    @property
    def interconnect_inductor_tolerance_value(self) -> str:
        """Tolerance value of interconnect inductor in ``%``.

        The default is ``1``.

        Returns
        -------
        str
        """
        interconnect_inductor_tolerance_value_string = self._dll_interface.get_string(
            self._dll.getInterConnectInductorTolerance
        )
        return interconnect_inductor_tolerance_value_string

    @interconnect_inductor_tolerance_value.setter
    def interconnect_inductor_tolerance_value(self, interconnect_inductor_tolerance_value_string):
        self._dll_interface.set_string(
            self._dll.setInterConnectInductorTolerance, interconnect_inductor_tolerance_value_string
        )

    @property
    def interconnect_capacitor_tolerance_value(self) -> str:
        """Tolerance value of interconnect capacitor in ``%``.

        The default is ``1``.

        Returns
        -------
        str
        """
        interconnect_capacitor_tolerance_value_string = self._dll_interface.get_string(
            self._dll.getInterConnectCapacitorTolerance
        )
        return interconnect_capacitor_tolerance_value_string

    @interconnect_capacitor_tolerance_value.setter
    def interconnect_capacitor_tolerance_value(self, interconnect_capacitor_tolerance_value_string):
        self._dll_interface.set_string(
            self._dll.setInterConnectCapacitorTolerance, interconnect_capacitor_tolerance_value_string
        )

    @property
    def interconnect_geometry_optimization_enabled(self) -> bool:
        """Flag indicating if the interconnect geometry optimization is enabled.

        Returns
        -------
        bool
        """
        interconnect_geometry_optimization_enabled = c_bool()
        status = self._dll.getInterconnectGeometryOptimization(byref(interconnect_geometry_optimization_enabled))
        self._dll_interface.raise_error(status)
        return bool(interconnect_geometry_optimization_enabled.value)

    @interconnect_geometry_optimization_enabled.setter
    def interconnect_geometry_optimization_enabled(self, interconnect_geometry_optimization_enabled: bool):
        status = self._dll.setInterconnectGeometryOptimization(interconnect_geometry_optimization_enabled)
        self._dll_interface.raise_error(status)

    def update_interconncet_parameters(self):  # pragma: no cover
        """Update interconnect geometry equations with entered and selected parameters"""
        status = self._dll.updateInterConnectParmeters()
        self._dll_interface.raise_error(status)

    def update_inductor_capacitor_tolerances(self):  # pragma: no cover
        """Update interconnect inductor and capacitor tolerances with entered values"""
        status = self._dll.updatePartsTolerances()
        self._dll_interface.raise_error(status)

    @property
    def substrate_type(self) -> SubstrateType:
        """Subctrate type of the filter.

        The ``SubstrateType`` enum provides a list of all substrate types.

        Returns
        -------
        :enum:`SubstrateType`
        """
        type_string = self._dll_interface.get_string(self._dll.getSubstrateType)
        return self._dll_interface.string_to_enum(SubstrateType, type_string)

    @substrate_type.setter
    def substrate_type(self, substrate_type: SubstrateType):
        if substrate_type:
            string_value = self._dll_interface.enum_to_string(substrate_type)
            self._dll_interface.set_string(self._dll.setSubstrateType, string_value)

    @property
    def substrate_er(self) -> Union[SubstrateType, str]:
        """Substrate's relative permittivity ``Er``.

        The value can be either a string or an instance of the ``SubstrateEr`` enum.
        The default is ``9.8`` for ``SubstrateEr.ALUMINA``.

        Returns
        -------
        Union[SubstrateEr, str]

        """
        substrate_er_index = c_int()
        substrate_er_value_str = create_string_buffer(100)
        status = self._dll.getEr(substrate_er_value_str, byref(substrate_er_index), 100)
        self._dll_interface.raise_error(status)
        if substrate_er_index.value in [e.value for e in SubstrateEr]:
            return SubstrateEr(substrate_er_index.value)
        else:
            return substrate_er_value_str.value.decode("ascii")

    @substrate_er.setter
    def substrate_er(self, substrate_input):
        if substrate_input in list(SubstrateEr):
            substrate_er_index = SubstrateEr(substrate_input).value
            substrate_er_value = ""
        elif isinstance(substrate_input, str):
            substrate_er_value = substrate_input
            substrate_er_index = -1
        else:
            raise ValueError("Invalid substrate input. Must be a SubstrateEr enum member or a string.")
        substrate_er_value_bytes = bytes(substrate_er_value, "ascii")
        status = self._dll.setEr(substrate_er_value_bytes, substrate_er_index)
        self._dll_interface.raise_error(status)

    @property
    def substrate_resistivity(self) -> Union[SubstrateResistivity, str]:
        """Substrate's resistivity.

        The value can be either a string or an instance of the ``SubstrateResistivity`` enum.
        The default is ``1.43`` for ``SubstrateResistivity.GOLD``.

        Returns
        -------
        Union[SubstrateResistivity, str]
        """
        substrate_resistivity_index = c_int()
        substrate_resistivity_value_str = create_string_buffer(100)
        status = self._dll.getResistivity(substrate_resistivity_value_str, byref(substrate_resistivity_index), 100)
        self._dll_interface.raise_error(status)
        if substrate_resistivity_index.value in [e.value for e in SubstrateResistivity]:
            return SubstrateResistivity(substrate_resistivity_index.value)
        else:
            return substrate_resistivity_value_str.value.decode("ascii")

    @substrate_resistivity.setter
    def substrate_resistivity(self, substrate_input):
        if substrate_input in list(SubstrateResistivity):
            substrate_resistivity_index = SubstrateResistivity(substrate_input).value
            substrate_resistivity_value = ""
        elif isinstance(substrate_input, str):
            substrate_resistivity_value = substrate_input
            substrate_resistivity_index = -1
        else:
            raise ValueError("Invalid substrate input. Must be a SubstrateResistivity enum member or a string.")
        substrate_resistivity_value_bytes = bytes(substrate_resistivity_value, "ascii")
        status = self._dll.setResistivity(substrate_resistivity_value_bytes, substrate_resistivity_index)
        self._dll_interface.raise_error(status)

    @property
    def substrate_loss_tangent(self) -> Union[SubstrateEr, str]:
        """Substrate's loss tangent.

        The value can be either a string or an instance of the ``SubstrateEr`` enum.
        The default is ``0.0005`` for ``SubstrateEr.ALUMINA``.

        Returns
        -------
        Union[SubstrateEr, str]
        """
        substrate_loss_tangent_index = c_int()
        substrate_loss_tangent_value_str = create_string_buffer(100)
        status = self._dll.getLossTangent(substrate_loss_tangent_value_str, byref(substrate_loss_tangent_index), 100)
        self._dll_interface.raise_error(status)
        if substrate_loss_tangent_index.value in [e.value for e in SubstrateEr]:
            return SubstrateEr(substrate_loss_tangent_index.value)
        else:
            return substrate_loss_tangent_value_str.value.decode("ascii")

    @substrate_loss_tangent.setter
    def substrate_loss_tangent(self, substrate_input):
        if substrate_input in list(SubstrateEr):
            substrate_loss_tangent_index = SubstrateEr(substrate_input).value
            substrate_loss_tangent_value = ""
        elif isinstance(substrate_input, str):
            substrate_loss_tangent_value = substrate_input
            substrate_loss_tangent_index = -1
        else:
            raise ValueError("Invalid substrate input. Must be a SubstrateEr enum member or a string.")
        substrate_loss_tangent_value_bytes = bytes(substrate_loss_tangent_value, "ascii")
        status = self._dll.setLossTangent(substrate_loss_tangent_value_bytes, substrate_loss_tangent_index)
        self._dll_interface.raise_error(status)

    @property
    def substrate_conductor_thickness(self) -> str:
        """Substrate's conductor thickness.

        The default is ``2.54 um``.

        Returns
        -------
        str
        """
        substrate_conductor_thickness_string = self._dll_interface.get_string(self._dll.getConductorThickness)
        return substrate_conductor_thickness_string

    @substrate_conductor_thickness.setter
    def substrate_conductor_thickness(self, substrate_conductor_thickness_string):
        self._dll_interface.set_string(self._dll.setConductorThickness, substrate_conductor_thickness_string)

    @property
    def substrate_dielectric_height(self) -> str:
        """Substrate's dielectric height.

        The default is ``1.27 mm``.

        Returns
        -------
        str
        """
        substrate_dielectric_height_string = self._dll_interface.get_string(self._dll.getDielectricHeight)
        return substrate_dielectric_height_string

    @substrate_dielectric_height.setter
    def substrate_dielectric_height(self, substrate_dielectric_height_string):
        self._dll_interface.set_string(self._dll.setDielectricHeight, substrate_dielectric_height_string)

    @property
    def substrate_unbalanced_lower_dielectric_height(self) -> str:
        """Substrate's lower dielectric height for unbalanced stripline substrate type.

        The default is ``6.35 mm``.

        Returns
        -------
        str
        """
        substrate_unbalanced_lower_dielectric_height_string = self._dll_interface.get_string(
            self._dll.getLowerDielectricHeight
        )
        return substrate_unbalanced_lower_dielectric_height_string

    @substrate_unbalanced_lower_dielectric_height.setter
    def substrate_unbalanced_lower_dielectric_height(self, substrate_unbalanced_lower_dielectric_height_string):
        self._dll_interface.set_string(
            self._dll.setLowerDielectricHeight, substrate_unbalanced_lower_dielectric_height_string
        )

    @property
    def substrate_suspend_dielectric_height(self) -> str:
        """Substrate's suspend dielectric height above ground plane for suspend and inverted substrate types.

        The default is ``1.27 mm``.

        Returns
        -------
        str
        """
        substrate_suspend_dielectric_height_string = self._dll_interface.get_string(
            self._dll.getSuspendDielectricHeight
        )
        return substrate_suspend_dielectric_height_string

    @substrate_suspend_dielectric_height.setter
    def substrate_suspend_dielectric_height(self, substrate_suspend_dielectric_height_string):
        self._dll_interface.set_string(self._dll.setSuspendDielectricHeight, substrate_suspend_dielectric_height_string)

    @property
    def substrate_cover_height(self) -> str:
        """Substrate's cover height for microstrip, suspend, and inverted substrate types.
        The default is ``6.35 mm``.

        Returns
        -------
        str
        """
        substrate_cover_height_string = self._dll_interface.get_string(self._dll.getCoverHeight)
        return substrate_cover_height_string

    @substrate_cover_height.setter
    def substrate_cover_height(self, substrate_cover_height_string):
        self._dll_interface.set_string(self._dll.setCoverHeight, substrate_cover_height_string)

    @property
    def substrate_unbalanced_stripline_enabled(self) -> bool:
        """Flag indicating if the substrate unbalanced stripline is enabled.

        Returns
        -------
        bool
        """
        substrate_unbalanced_stripline_enabled = c_bool()
        status = self._dll.getUnbalancedStripLine(byref(substrate_unbalanced_stripline_enabled))
        self._dll_interface.raise_error(status)
        return bool(substrate_unbalanced_stripline_enabled.value)

    @substrate_unbalanced_stripline_enabled.setter
    def substrate_unbalanced_stripline_enabled(self, substrate_unbalanced_stripline_enabled: bool):
        status = self._dll.setUnbalancedStripLine(substrate_unbalanced_stripline_enabled)
        self._dll_interface.raise_error(status)

    @property
    def substrate_cover_height_enabled(self) -> bool:
        """Flag indicating if the substrate cover height is enabled.

        Returns
        -------
        bool
        """
        substrate_cover_height_enabled = c_bool()
        status = self._dll.getGroundedCoverAboveLine(byref(substrate_cover_height_enabled))
        self._dll_interface.raise_error(status)
        return bool(substrate_cover_height_enabled.value)

    @substrate_cover_height_enabled.setter
    def substrate_cover_height_enabled(self, substrate_cover_height_enabled: bool):
        status = self._dll.setGroundedCoverAboveLine(substrate_cover_height_enabled)
        self._dll_interface.raise_error(status)

    def load_modelithics_models(self):
        """Load ``Modelithics`` models from ``AEDT``."""
        status = self._dll.loadModelithicsModels()
        self._dll_interface.raise_error(status)

    @property
    def modelithics_include_interconnect_enabled(self) -> bool:
        """Flag indicating if the inclusion of interconnects is enabled for``Modelithics`` export.

        Returns
        -------
        bool
        """
        modelithics_include_interconnect_enabled = c_bool()
        status = self._dll.getModelithicsIncludeInterconnect(byref(modelithics_include_interconnect_enabled))
        self._dll_interface.raise_error(status)
        return bool(modelithics_include_interconnect_enabled.value)

    @modelithics_include_interconnect_enabled.setter
    def modelithics_include_interconnect_enabled(self, modelithics_include_interconnect_enabled: bool):
        status = self._dll.setModelithicsIncludeInterconnect(modelithics_include_interconnect_enabled)
        self._dll_interface.raise_error(status)

    @property
    def modelithics_inductor_list_count(self) -> int:
        """Total count of ``Modelithics`` inductor families that have been loaded into the current design.

        Returns
        -------
        int
        """
        count = c_int()
        status = self._dll.getModelithicsInductorsListCount(byref(count))
        self._dll_interface.raise_error(status)
        return int(count.value)

    def modelithics_inductor_list(self, row_index) -> str:
        """Get the name of the ``Modelithics` inductor family model from the loaded list based
        on the specified index."""

        modelithics_inductor_buffer = create_string_buffer(100)
        status = self._dll.getModelithicsInductorsList(row_index, modelithics_inductor_buffer, 100)
        self._dll_interface.raise_error(status)
        modelithics_inductor = modelithics_inductor_buffer.value.decode("utf-8")
        return modelithics_inductor

    @property
    def modelithics_inductor_selection(self) -> str:
        """Selected ``Modelithics`` inductor family from the loaded list.

        The Modelithics inductor family selection allows you to choose a specific inductor model from the
        Modelithics library.

        Returns
        -------
        str
        """
        modelithics_inductor_selection_string = self._dll_interface.get_string(self._dll.getModelithicsInductors)
        return modelithics_inductor_selection_string

    @modelithics_inductor_selection.setter
    def modelithics_inductor_selection(self, modelithics_inductor_selection_string):
        self._dll_interface.set_string(self._dll.setModelithicsInductors, modelithics_inductor_selection_string)

    @property
    def modelithics_inductor_family_list_count(self) -> int:
        """Total count of ``Modelithics`` family inductors added to the inductor family list.

        Returns
        -------
        int
        """
        count = c_int()
        status = self._dll.getModelithicsInductorsFamilyListCount(byref(count))
        self._dll_interface.raise_error(status)
        return int(count.value)

    def modelithics_inductor_family_list(self, index) -> str:
        """Get the name of ``Modelithics`` inductor family from the inductor family list based on the specified index.

        Parameters
        ----------
        index : int
            Index of the inductor family list.

        Returns
        -------
        str
        """
        modelithics_inductor_family_buffer = create_string_buffer(100)
        status = self._dll.getModelithicsInductorsFamilyList(index, modelithics_inductor_family_buffer, 100)
        self._dll_interface.raise_error(status)
        modelithics_inductor_family = modelithics_inductor_family_buffer.value.decode("utf-8")
        return modelithics_inductor_family

    def modelithics_inductor_add_family(self, modelithics_inductor) -> str:
        """Add a specified ``Modelithics`` inductor family to the inductor family list.

        Parameters
        ----------
        modelithics_inductor : str
            Name of the inductor family.
        """
        self._dll_interface.set_string(self._dll.addModelithicsInductorsFamily, modelithics_inductor)

    def modelithics_inductor_remove_family(self, modelithics_inductor) -> str:
        """Remove a specified ``Modelithics`` inductor family from the inductor family list.

        Parameters
        ----------
        modelithics_inductor : str
            Name of the inductor family.
        """
        self._dll_interface.set_string(self._dll.removeModelithicsInductorsFamily, modelithics_inductor)

    @property
    def modelithics_capacitor_list_count(self) -> int:
        """Total count of ``Modelithics`` capacitor families that have been loaded into the current design.

        Returns
        -------
        int
        """
        count = c_int()
        status = self._dll.getModelithicsCapacitorsListCount(byref(count))
        self._dll_interface.raise_error(status)
        return int(count.value)

    def modelithics_capacitor_list(self, row_index) -> str:
        """Get the name of the ``Modelithics`` capacitor family model from the loaded list based on
        the specified index."""

        modelithics_capacitor_buffer = create_string_buffer(100)
        status = self._dll.getModelithicsCapacitorsList(row_index, modelithics_capacitor_buffer, 100)
        self._dll_interface.raise_error(status)
        modelithics_capacitor = modelithics_capacitor_buffer.value.decode("utf-8")
        return modelithics_capacitor

    @property
    def modelithics_capacitor_selection(self) -> str:
        """Selected ``Modelithics`` capacitor family from the loaded list.

        The Modelithics capacitor family selection allows you to choose a specific capacitor model from the
        Modelithics library.

        Returns
        -------
        str
        """
        modelithics_capacitor_selection_string = self._dll_interface.get_string(self._dll.getModelithicsCapacitors)
        return modelithics_capacitor_selection_string

    @modelithics_capacitor_selection.setter
    def modelithics_capacitor_selection(self, modelithics_capacitor_selection_string):
        self._dll_interface.set_string(self._dll.setModelithicsCapacitors, modelithics_capacitor_selection_string)

    @property
    def modelithics_capacitor_family_list_count(self) -> int:
        """Total count of ``Modelithics`` family capacitors added to the capacitor family list.

        Returns
        -------
        int
        """
        count = c_int()
        status = self._dll.getModelithicsCapacitorsFamilyListCount(byref(count))
        self._dll_interface.raise_error(status)
        return int(count.value)

    def modelithics_capacitor_family_list(self, index) -> str:
        """Get the name of ``Modelithics`` capacitor family from the capacitor family list based on the specified index.

        Parameters
        ----------
        index : int
            Index of the capacitor family list.

        Returns
        -------
        str
        """
        modelithics_capacitor_family_buffer = create_string_buffer(100)
        status = self._dll.getModelithicsCapacitorsFamilyList(index, modelithics_capacitor_family_buffer, 100)
        self._dll_interface.raise_error(status)
        modelithics_capacitor_family = modelithics_capacitor_family_buffer.value.decode("utf-8")
        return modelithics_capacitor_family

    def modelithics_capacitor_add_family(self, modelithics_capacitor) -> str:
        """Add a specified``Modelithics`` capacitor family to the capacitor family list.

        Parameters
        ----------
        modelithics_capacitor : str
            Name of the capacitor family.
        """
        self._dll_interface.set_string(self._dll.addModelithicsCapacitorsFamily, modelithics_capacitor)

    def modelithics_capacitor_remove_family(self, modelithics_capacitor) -> str:
        """Remove a specified ``Modelithics`` capacitor family from the capacitor family list.

        Parameters
        ----------
        modelithics_capacitor : str
            Name of the capacitor family.
        """
        self._dll_interface.set_string(self._dll.removeModelithicsCapacitorsFamily, modelithics_capacitor)

    @property
    def modelithics_resistor_list_count(self) -> int:
        """Total count of ``Modelithics`` resistor families that have been loaded into the current design.

        Returns
        -------
        int
        """
        count = c_int()
        status = self._dll.getModelithicsResistorsListCount(byref(count))
        self._dll_interface.raise_error(status)
        return int(count.value)

    def modelithics_resistor_list(self, row_index) -> str:
        """Get the name of the ``Modelithics`` resistor family model from the loaded list based on the
        specified index."""

        modelithics_resistor_buffer = create_string_buffer(100)
        status = self._dll.getModelithicsResistorsList(row_index, modelithics_resistor_buffer, 100)
        self._dll_interface.raise_error(status)
        modelithics_resistor = modelithics_resistor_buffer.value.decode("utf-8")
        return modelithics_resistor

    @property
    def modelithics_resistor_selection(self) -> str:
        """Selected ``Modelithics`` resistor family from the loaded list.

        The Modelithics resistor family selection allows you to choose a specific resistor model from the
        Modelithics library.

        Returns
        -------
        str
        """
        modelithics_resistor_selection_string = self._dll_interface.get_string(self._dll.getModelithicsResistors)
        return modelithics_resistor_selection_string

    @modelithics_resistor_selection.setter
    def modelithics_resistor_selection(self, modelithics_resistor_selection_string):
        self._dll_interface.set_string(self._dll.setModelithicsResistors, modelithics_resistor_selection_string)

    @property
    def modelithics_resistor_family_list_count(self) -> int:
        """Total count of ``Modelithics`` family resistors added to the resistor family list.

        Returns
        -------
        int
        """
        count = c_int()
        status = self._dll.getModelithicsResistorsFamilyListCount(byref(count))
        self._dll_interface.raise_error(status)
        return int(count.value)

    def modelithics_resistor_family_list(self, index) -> str:
        """Get the name of ``Modelithics`` resistor family from the resistor family list based on
        the specified index.

        Parameters
        ----------
        index : int
            Index of the resistor family list.

        Returns
        -------
        str
        """
        modelithics_resistor_family_buffer = create_string_buffer(100)
        status = self._dll.getModelithicsResistorsFamilyList(index, modelithics_resistor_family_buffer, 100)
        self._dll_interface.raise_error(status)
        modelithics_resistor_family = modelithics_resistor_family_buffer.value.decode("utf-8")
        return modelithics_resistor_family

    def modelithics_resistor_add_family(self, modelithics_resistor) -> str:
        """Add a specified ``Modelithics`` resistor family to the resistor family list.

        Parameters
        ----------
        modelithics_resistor : str
            Name of the resistor family.
        """
        self._dll_interface.set_string(self._dll.addModelithicsResistorsFamily, modelithics_resistor)

    def modelithics_resistor_remove_family(self, modelithics_resistor) -> str:
        """Remove a specified ``Modelithics`` resistor family from the resistor family list.

        Parameters
        ----------
        modelithics_resistor : str
            Name of the resistor family.
        """
        self._dll_interface.set_string(self._dll.removeModelithicsResistorsFamily, modelithics_resistor)

    @property
    def insert_circuit_design(self) -> bool:
        """Flag indicating if the filter is inserted as an ``AEDT Circuit Design``.

        Returns
        -------
        bool
        """
        insert_circuit_design = c_bool()
        status = self._dll.getCircuitDesign(byref(insert_circuit_design))
        self._dll_interface.raise_error(status)
        return bool(insert_circuit_design.value)

    @insert_circuit_design.setter
    def insert_circuit_design(self, insert_circuit_design: bool):
        status = self._dll.setCircuitDesign(insert_circuit_design)
        self._dll_interface.raise_error(status)

    @property
    def insert_hfss_design(self) -> bool:
        """Flag indicating if the filter is inserted as an ``AEDT HFSS Design``.

        Returns
        -------
        bool
        """
        insert_hfss_design = c_bool()
        status = self._dll.getHFSSDesign(byref(insert_hfss_design))
        self._dll_interface.raise_error(status)
        return bool(insert_hfss_design.value)

    @insert_hfss_design.setter
    def insert_hfss_design(self, insert_hfss_design: bool):
        status = self._dll.setHFSSDesign(insert_hfss_design)
        self._dll_interface.raise_error(status)

    @property
    def insert_hfss_3dl_design(self) -> bool:
        """Flag indicating if the filter is inserted as an ``AEDT HFSS 3D Layout Design``.

        Returns
        -------
        bool
        """
        insert_hfss_3dl_design = c_bool()
        status = self._dll.getHFSS3DLDesign(byref(insert_hfss_3dl_design))
        self._dll_interface.raise_error(status)
        return bool(insert_hfss_3dl_design.value)

    @insert_hfss_3dl_design.setter
    def insert_hfss_3dl_design(self, insert_hfss_3dl_design: bool):
        status = self._dll.setHFSS3DLDesign(insert_hfss_3dl_design)
        self._dll_interface.raise_error(status)

    @property
    def full_parametrization_enabled(self) -> bool:
        """Flag indicating if the parameter equations are used to define layout geometries for
        tuning and optimizating purpose in ``HFSS``.

        Returns
        -------
        bool
        """
        full_parametrization_enabled = c_bool()
        status = self._dll.getFullParametrization(byref(full_parametrization_enabled))
        self._dll_interface.raise_error(status)
        return bool(full_parametrization_enabled.value)

    @full_parametrization_enabled.setter
    def full_parametrization_enabled(self, full_parametrization_enabled: bool):
        status = self._dll.setFullParametrization(full_parametrization_enabled)
        self._dll_interface.raise_error(status)

    @property
    def ports_always_on_sides_enabled(self) -> bool:
        """Flag indicating if the ports are always placed on the side walls.

        Returns
        -------
        bool
        """
        ports_always_on_sides_enabled = c_bool()
        status = self._dll.getPortsOnSides(byref(ports_always_on_sides_enabled))
        self._dll_interface.raise_error(status)
        return bool(ports_always_on_sides_enabled.value)

    @ports_always_on_sides_enabled.setter
    def ports_always_on_sides_enabled(self, ports_always_on_sides_enabled: bool):
        status = self._dll.setPortsOnSides(ports_always_on_sides_enabled)
        self._dll_interface.raise_error(status)

    @property
    def reverse_x_axis_enabled(self) -> bool:
        """Flag indicating if the layout is mirrored along the x-axis.

        Returns
        -------
        bool
        """
        reverse_x_axis_enabled = c_bool()
        status = self._dll.getFlipXAxis(byref(reverse_x_axis_enabled))
        self._dll_interface.raise_error(status)
        return bool(reverse_x_axis_enabled.value)

    @reverse_x_axis_enabled.setter
    def reverse_x_axis_enabled(self, reverse_x_axis_enabled: bool):
        status = self._dll.setFlipXAxis(reverse_x_axis_enabled)
        self._dll_interface.raise_error(status)

    @property
    def reverse_y_axis_enabled(self) -> bool:
        """Flag indicating if the layout is mirrored along the y-axis.

        Returns
        -------
        bool
        """
        reverse_y_axis_enabled = c_bool()
        status = self._dll.getFlipYAxis(byref(reverse_y_axis_enabled))
        self._dll_interface.raise_error(status)
        return bool(reverse_y_axis_enabled.value)

    @reverse_y_axis_enabled.setter
    def reverse_y_axis_enabled(self, reverse_y_axis_enabled: bool):
        status = self._dll.setFlipYAxis(reverse_y_axis_enabled)
        self._dll_interface.raise_error(status)

    @property
    def export_with_tuning_port_format_enabled(self) -> bool:
        """Flag indicating if the export with tuning port format is enabled.

        Returns
        -------
        bool
        """
        export_with_tuning_port_format_enabled = c_bool()
        status = self._dll.getIncludeTuningPorts(byref(export_with_tuning_port_format_enabled))
        self._dll_interface.raise_error(status)
        return bool(export_with_tuning_port_format_enabled.value)

    @export_with_tuning_port_format_enabled.setter
    def export_with_tuning_port_format_enabled(self, export_with_tuning_port_format_enabled: bool):
        status = self._dll.setIncludeTuningPorts(export_with_tuning_port_format_enabled)
        self._dll_interface.raise_error(status)

    @property
    def use_series_horizontal_ports_enabled(self) -> bool:
        """Flag indicating if  horizontal ports are used for series element only cases.

        Returns
        -------
        bool
        """
        use_series_horizontal_ports_enabled = c_bool()
        status = self._dll.getSeriesHorizontalPorts(byref(use_series_horizontal_ports_enabled))
        self._dll_interface.raise_error(status)
        return bool(use_series_horizontal_ports_enabled.value)

    @use_series_horizontal_ports_enabled.setter
    def use_series_horizontal_ports_enabled(self, use_series_horizontal_ports_enabled: bool):
        status = self._dll.setSeriesHorizontalPorts(use_series_horizontal_ports_enabled)
        self._dll_interface.raise_error(status)

    def import_tuned_variables_port_tuning(self):
        """Import tuned variables from the port tuning project."""
        status = self._dll.importPortTunedVariables()
        self._dll_interface.raise_error(status)

    def import_and_reexport_over_port_tuning(self):
        """Import tuned variables and export back over the port tuning project."""
        status = self._dll.importReexportPortTunedVariables()
        self._dll_interface.raise_error(status)

    def simulate_full_port_tuning(self):
        """Simulate the port tuning project and the linked circuits schematic."""
        status = self._dll.simulateFull()
        self._dll_interface.raise_error(status)

    def simulate_tuning_circuit_port_tuning(self):
        """Simulate only the linked circuits schematic of the port tuning project."""
        status = self._dll.simulateTune()
        self._dll_interface.raise_error(status)

    def optimize_port_tuning(self):
        """Simulate the ``HFSS Design`` or ``HFSS 3D Layout Design`` of the port tuning project."""
        status = self._dll.optimizerPortTunedVariables()
        self._dll_interface.raise_error(status)
