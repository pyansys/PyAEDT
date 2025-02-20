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

import copy


def HFSS3DLayout_AdaptiveFrequencyData(freq):
    """Update HFSS 3D adaptive frequency data.

    Parameters
    ----------
    freq : float
        Adaptive frequency value.


    Returns
    -------
    list
        List of frequency data.

    """
    value = dict({"AdaptiveFrequency": freq, "MaxDelta": "0.02", "MaxPasses": 10, "Expressions": []})
    return value


meshlink = dict({"ImportMesh": False})
autosweep = dict({"RangeType": "LinearCount", "RangeStart": "1GHz", "RangeEnd": "10GHz", "RangeCount": "501"})
autosweeps = dict({"Sweep": autosweep})
multifreq = dict({"1GHz": [0.02], "2GHz": [0.02], "5GHz": [0.02]})
sweepsbr = dict({"RangeType": "LinearStep", "RangeStart": "1GHz", "RangeEnd": "10GHz", "RangeStep": "1GHz"})
sweepssbr = dict({"Sweep": sweepsbr})
muoption = dict({"MuNonLinearBH": True})
transientelectrostatic = dict({"SaveField": True, "Stop": "100s", "InitialStep": "0.01s", "MaxStep": "5s"})
transienthfss = dict(
    {
        "TimeProfile": "Broadband Pulse",
        "HfssFrequency": "5GHz",
        "MinFreq": "100MHz",
        "MaxFreq": "1GHz",
        "NumFreqsExtracted": 401,
        "SweepMinFreq": "100MHz",
        "SweepMaxFreq": "1GHz",
        "UseAutoTermination": 1,
        "SteadyStateCriteria": 0.01,
        "UseMinimumDuration": 0,
        "TerminateOnMaximum": 0,
    }
)
HFSSDrivenAuto = dict(
    {
        "IsEnabled": True,
        "MeshLink": meshlink,
        "AutoSolverSetting": "Balanced",
        "Sweeps": autosweeps,
        "SaveRadFieldsOnly": False,
        "SaveAnyFields": True,
        "Type": "Discrete",
    }
)
"""HFSS automatic setup properties and default values."""

HFSSDrivenDefault = dict(
    {
        "SolveType": "Single",
        "MultipleAdaptiveFreqsSetup": multifreq,
        "Frequency": "5GHz",
        "MaxDeltaS": 0.02,
        "PortsOnly": False,
        "UseMatrixConv": False,
        "MaximumPasses": 6,
        "MinimumPasses": 1,
        "MinimumConvergedPasses": 1,
        "PercentRefinement": 30,
        "IsEnabled": True,
        "MeshLink": meshlink,
        "BasisOrder": 1,
        "DoLambdaRefine": True,
        "DoMaterialLambda": True,
        "SetLambdaTarget": False,
        "Target": 0.3333,
        "UseMaxTetIncrease": False,
        "PortAccuracy": 2,
        "UseABCOnPort": False,
        "SetPortMinMaxTri": False,
        "UseDomains": False,
        "UseIterativeSolver": False,
        "SaveRadFieldsOnly": False,
        "SaveAnyFields": True,
        "IESolverType": "Auto",
        "LambdaTargetForIESolver": 0.15,
        "UseDefaultLambdaTgtForIESolver": True,
        "IE Solver Accuracy": "Balanced",
    }
)
"""HFSS driven properties and default values."""

HFSSEigen = dict(
    {
        "MinimumFrequency": "2GHz",
        "NumModes": 1,
        "MaxDeltaFreq": 10,
        "ConvergeOnRealFreq": False,
        "MaximumPasses": 3,
        "MinimumPasses": 1,
        "MinimumConvergedPasses": 1,
        "PercentRefinement": 30,
        "IsEnabled": True,
        "MeshLink": meshlink,
        "BasisOrder": 1,
        "DoLambdaRefine": True,
        "DoMaterialLambda": True,
        "SetLambdaTarget": False,
        "Target": 0.2,
        "UseMaxTetIncrease": False,
    }
)
"""HFSS Eigenmode properties and default values."""

HFSSTransient = dict(
    {
        "Frequency": "5GHz",
        "MaxDeltaS": 0.02,
        "MaximumPasses": 20,
        "UseImplicitSolver": True,
        "IsEnabled": True,
        "MeshLink": meshlink,
        "BasisOrder": -1,
        "Transient": transienthfss,
    }
)
"""HFSS transient setup properties and default values."""

HFSSSBR = dict(
    {
        "IsEnabled": True,
        "MeshLink": meshlink,
        "IsSbrRangeDoppler": False,
        "RayDensityPerWavelength": 4,
        "MaxNumberOfBounces": 5,
        "RadiationSetup": "",
        "PTDUTDSimulationSettings": "None",
        "Sweeps": sweepssbr,
        "ComputeFarFields": True,
    }
)
"""HFSS SBR+ setup properties and default values."""

MaxwellTransient = dict(
    {
        "Enabled": True,
        "MeshLink": meshlink,
        "NonlinearSolverResidual": "0.005",
        "ScalarPotential": "Second Order",
        "SmoothBHCurve": False,
        "StopTime": "10000000ns",
        "TimeStep": "2000000ns",
        "OutputError": False,
        "UseControlProgram": False,
        "ControlProgramName": "",
        "ControlProgramArg": "",
        "CallCtrlProgAfterLastStep": False,
        "FastReachSteadyState": False,
        "AutoDetectSteadyState": False,
        "IsGeneralTransient": True,
        "IsHalfPeriodicTransient": False,
        "SaveFieldsType": "None",
        "CacheSaveKind": "Count",
        "NumberSolveSteps": 1,
        "RangeStart": "0s",
        "RangeEnd": "0.1s",
    }
)
"""Maxwell transient setup properties and default values."""

Magnetostatic = dict(
    {
        "Enabled": True,
        "MeshLink": meshlink,
        "MaximumPasses": 10,
        "MinimumPasses": 2,
        "MinimumConvergedPasses": 1,
        "PercentRefinement": 30,
        "SolveFieldOnly": False,
        "PercentError": 1,
        "SolveMatrixAtLast": True,
        "UseIterativeSolver": False,
        "RelativeResidual": 1e-06,
        "NonLinearResidual": 0.001,
        "SmoothBHCurve": False,
        "MuOption": muoption,
    }
)
"""Maxwell magnetostatic setup properties and default values."""

DCConduction = dict(
    {
        "Enabled": True,
        "MeshLink": meshlink,
        "MaximumPasses": 10,
        "MinimumPasses": 2,
        "MinimumConvergedPasses": 1,
        "PercentRefinement": 30,
        "SolveFieldOnly": False,
        "PercentError": 1,
        "SolveMatrixAtLast": True,
        "UseNonLinearIterNum": False,
        "UseIterativeSolver": False,
        "RelativeResidual": 1e-06,
        "NonLinearResidual": 0.001,
    }
)
"""Maxwell DCConduction setup properties and default values."""

ElectroDCConduction = dict(
    {
        "Enabled": True,
        "MeshLink": meshlink,
        "MaximumPasses": 10,
        "MinimumPasses": 2,
        "MinimumConvergedPasses": 1,
        "PercentRefinement": 30,
        "SolveFieldOnly": False,
        "PercentError": 1,
        "SolveMatrixAtLast": True,
        "UseNonLinearIterNum": False,
        "UseIterativeSolver": False,
        "RelativeResidual": 1e-06,
        "NonLinearResidual": 0.001,
    }
)
"""Maxwell ElectroDCConduction setup properties and default values."""

ACConduction = dict(
    {
        "Enabled": True,
        "MeshLink": meshlink,
        "MaximumPasses": 10,
        "MinimumPasses": 2,
        "MinimumConvergedPasses": 1,
        "PercentRefinement": 30,
        "SolveFieldOnly": False,
        "PercentError": 1,
        "SolveMatrixAtLast": True,
        "UseNonLinearIterNum": False,
        "NonLinearResidual": 0.001,
        "Frequency": "60Hz",
        "HasSweepSetup": False,
    }
)
"""Maxwell ACConduction setup properties and default values."""

Electrostatic = dict(
    {
        "Enabled": True,
        "MeshLink": meshlink,
        "MaximumPasses": 10,
        "MinimumPasses": 2,
        "MinimumConvergedPasses": 1,
        "PercentRefinement": 30,
        "SolveFieldOnly": False,
        "PercentError": 1,
        "SolveMatrixAtLast": True,
        "UseIterativeSolver": False,
        "RelativeResidual": 1e-06,
        "NonLinearResidual": 0.001,
    }
)
"""Maxwell electrostatic setup properties and default values."""

SweepEddyCurrent = dict(
    {
        "RangeType": "LinearStep",
        "RangeStart": "1e-08GHz",
        "RangeEnd": "1e-06GHz",
    }
)

EddyCurrent = dict(
    {
        "Enabled": True,
        "MeshLink": meshlink,
        "MaximumPasses": 6,
        "MinimumPasses": 1,
        "MinimumConvergedPasses": 1,
        "PercentRefinement": 30,
        "SolveFieldOnly": False,
        "PercentError": 1,
        "SolveMatrixAtLast": True,
        "UseIterativeSolver": False,
        "RelativeResidual": 1e-5,
        "NonLinearResidual": 0.0001,
        "SmoothBHCurve": False,
        "Frequency": "60Hz",
        "HasSweepSetup": False,
        "UseHighOrderShapeFunc": False,
        "UseMuLink": False,
    }
)
"""Maxwell eddy current setup properties and default values."""

DCBiasedEddyCurrent = dict(
    {
        "Enabled": True,
        "MeshLink": meshlink,
        "MaximumPasses": 6,
        "MinimumPasses": 1,
        "MinimumConvergedPasses": 1,
        "PercentRefinement": 30,
        "SolveFieldOnly": False,
        "PercentError": 1,
        "SolveMatrixAtLast": True,
        "UseIterativeSolver": False,
        "RelativeResidual": 1e-5,
        "NonLinearResidual": 0.0001,
        "SmoothBHCurve": False,
        "Frequency": "60Hz",
        "HasSweepSetup": False,
        "UseHighOrderShapeFunc": False,
        "UseMuLink": False,
        "DCPercentRefinement": 30,
        "DCMinimumPasses": 2,
        "DCMinConvergedPasses": 1,
        "DCNonLinearResidual": 0.001,
        "DCSmoothBHCurve": True,
        "DCMaxmumPasses": 10,
        "DCPercentError": 1,
    }
)


ElectricTransient = dict(
    {
        "Enabled": True,
        "MeshLink": meshlink,
        "Tolerance": 0.005,
        "ComputePowerLoss": False,
        "Data": transientelectrostatic,
        "Initial Voltage": "0mV",
    }
)
"""Maxwell electric transient setup properties and default values."""

SteadyTemperatureAndFlow = dict(
    {
        "Enabled": True,
        "Flow Regime": "Laminar",
        "Turbulent Model Eqn": "ZeroEquation",
        "Include Temperature": True,
        "Include Flow": True,
        "Include Gravity": False,
        "Solution Initialization - X Velocity": "0m_per_sec",
        "Solution Initialization - Y Velocity": "0m_per_sec",
        "Solution Initialization - Z Velocity": "0m_per_sec",
        "Solution Initialization - Temperature": "AmbientTemp",
        "Solution Initialization - Turbulent Kinetic Energy": "1m2_per_s2",
        "Solution Initialization - Turbulent Dissipation Rate": "1m2_per_s3",
        "Solution Initialization - Specific Dissipation Rate": "1diss_per_s",
        "Convergence Criteria - Flow": "0.001",
        "Convergence Criteria - Energy": "1e-07",
        "Convergence Criteria - Turbulent Kinetic Energy": "0.001",
        "Convergence Criteria - Turbulent Dissipation Rate": "0.001",
        "Convergence Criteria - Specific Dissipation Rate": "0.001",
        "Convergence Criteria - Discrete Ordinates": "1e-06",
        "IsEnabled": False,
        "Radiation Model": "Off",
        "Under-relaxation - Pressure": "0.7",
        "Under-relaxation - Momentum": "0.3",
        "Under-relaxation - Temperature": "1",
        "Under-relaxation - Turbulent Kinetic Energy": "0.8",
        "Under-relaxation - Turbulent Dissipation Rate": "0.8",
        "Under-relaxation - Specific Dissipation Rate": "0.8",
        "Discretization Scheme - Pressure": "Standard",
        "Discretization Scheme - Momentum": "First",
        "Discretization Scheme - Temperature": "Second",
        "Secondary Gradient": False,
        "Discretization Scheme - Turbulent Kinetic Energy": "First",
        "Discretization Scheme - Turbulent Dissipation Rate": "First",
        "Discretization Scheme - Specific Dissipation Rate": "First",
        "Discretization Scheme - Discrete Ordinates": "First",
        "Linear Solver Type - Pressure": "V",
        "Linear Solver Type - Momentum": "flex",
        "Linear Solver Type - Temperature": "F",
        "Linear Solver Type - Turbulent Kinetic Energy": "flex",
        "Linear Solver Type - Turbulent Dissipation Rate": "flex",
        "Linear Solver Type - Specific Dissipation Rate": "flex",
        "Linear Solver Termination Criterion - Pressure": "0.1",
        "Linear Solver Termination Criterion - Momentum": "0.1",
        "Linear Solver Termination Criterion - Temperature": "0.1",
        "Linear Solver Termination Criterion - Turbulent Kinetic Energy": "0.1",
        "Linear Solver Termination Criterion - Turbulent Dissipation  Rate": "0.1",
        "Linear Solver Termination Criterion - Specific Dissipation Rate": "0.1",
        "Linear Solver Residual Reduction Tolerance - Pressure": "0.1",
        "Linear Solver Residual Reduction Tolerance - Momentum": "0.1",
        "Linear Solver Residual Reduction Tolerance - Temperature": "0.1",
        "Linear Solver Residual Reduction Tolerance - Turbulent Kinetic Energy": "0.1",
        "Linear Solver Residual Reduction Tolerance - Turbulent Dissipation Rate": "0.1",
        "Linear Solver Residual Reduction Tolerance - Specific Dissipation Rate": "0.1",
        "Linear Solver Stabilization - Pressure": "None",
        "Linear Solver Stabilization - Temperature": "None",
        "Frozen Flow Simulation": False,
        "Sequential Solve of Flow and Energy Equations": False,
        "Convergence Criteria - Max Iterations": 100,
    }
)
"""Icepak steady temperature and steady flow setup properties and default values."""

SteadyTemperatureOnly = dict(
    {
        "Enabled": True,
        "Flow Regime": "Laminar",
        "Turbulent Model Eqn": "ZeroEquation",
        "Include Temperature": True,
        "Include Gravity": False,
        "Solution Initialization - X Velocity": "0m_per_sec",
        "Solution Initialization - Y Velocity": "0m_per_sec",
        "Solution Initialization - Z Velocity": "0m_per_sec",
        "Solution Initialization - Temperature": "AmbientTemp",
        "Solution Initialization - Turbulent Kinetic Energy": "1m2_per_s2",
        "Solution Initialization - Turbulent Dissipation Rate": "1m2_per_s3",
        "Solution Initialization - Specific Dissipation Rate": "1diss_per_s",
        "Convergence Criteria - Flow": "0.001",
        "Convergence Criteria - Energy": "1e-07",
        "Convergence Criteria - Turbulent Kinetic Energy": "0.001",
        "Convergence Criteria - Turbulent Dissipation Rate": "0.001",
        "Convergence Criteria - Specific Dissipation Rate": "0.001",
        "Convergence Criteria - Discrete Ordinates": "1e-06",
        "IsEnabled": False,
        "Radiation Model": "Off",
        "Under-relaxation - Pressure": "0.7",
        "Under-relaxation - Momentum": "0.3",
        "Under-relaxation - Temperature": "1",
        "Under-relaxation - Turbulent Kinetic Energy": "0.8",
        "Under-relaxation - Turbulent Dissipation Rate": "0.8",
        "Under-relaxation - Specific Dissipation Rate": "0.8",
        "Discretization Scheme - Pressure": "Standard",
        "Discretization Scheme - Momentum": "First",
        "Discretization Scheme - Temperature": "Second",
        "Secondary Gradient": False,
        "Discretization Scheme - Turbulent Kinetic Energy": "First",
        "Discretization Scheme - Turbulent Dissipation Rate": "First",
        "Discretization Scheme - Specific Dissipation Rate": "First",
        "Discretization Scheme - Discrete Ordinates": "First",
        "Linear Solver Type - Pressure": "V",
        "Linear Solver Type - Momentum": "flex",
        "Linear Solver Type - Temperature": "F",
        "Linear Solver Type - Turbulent Kinetic Energy": "flex",
        "Linear Solver Type - Turbulent Dissipation Rate": "flex",
        "Linear Solver Type - Specific Dissipation Rate": "flex",
        "Linear Solver Termination Criterion - Pressure": "0.1",
        "Linear Solver Termination Criterion - Momentum": "0.1",
        "Linear Solver Termination Criterion - Temperature": "0.1",
        "Linear Solver Termination Criterion - Turbulent Kinetic Energy": "0.1",
        "Linear Solver Termination Criterion - Turbulent Dissipation  Rate": "0.1",
        "Linear Solver Termination Criterion - Specific Dissipation Rate": "0.1",
        "Linear Solver Residual Reduction Tolerance - Pressure": "0.1",
        "Linear Solver Residual Reduction Tolerance - Momentum": "0.1",
        "Linear Solver Residual Reduction Tolerance - Temperature": "0.1",
        "Linear Solver Residual Reduction Tolerance - Turbulent Kinetic Energy": "0.1",
        "Linear Solver Residual Reduction Tolerance - Turbulent Dissipation Rate": "0.1",
        "Linear Solver Residual Reduction Tolerance - Specific Dissipation Rate": "0.1",
        "Linear Solver Stabilization - Pressure": "None",
        "Linear Solver Stabilization - Temperature": "None",
        "Sequential Solve of Flow and Energy Equations": False,
        "Convergence Criteria - Max Iterations": 100,
    }
)
"""Icepak steady temperature setup properties and default values."""

SteadyFlowOnly = dict(
    {
        "Enabled": True,
        "Flow Regime": "Laminar",
        "Turbulent Model Eqn": "ZeroEquation",
        "Include Flow": True,
        "Include Gravity": False,
        "Solution Initialization - X Velocity": "0m_per_sec",
        "Solution Initialization - Y Velocity": "0m_per_sec",
        "Solution Initialization - Z Velocity": "0m_per_sec",
        "Solution Initialization - Temperature": "AmbientTemp",
        "Solution Initialization - Turbulent Kinetic Energy": "1m2_per_s2",
        "Solution Initialization - Turbulent Dissipation Rate": "1m2_per_s3",
        "Solution Initialization - Specific Dissipation Rate": "1diss_per_s",
        "Convergence Criteria - Flow": "0.001",
        "Convergence Criteria - Energy": "1e-07",
        "Convergence Criteria - Turbulent Kinetic Energy": "0.001",
        "Convergence Criteria - Turbulent Dissipation Rate": "0.001",
        "Convergence Criteria - Specific Dissipation Rate": "0.001",
        "Convergence Criteria - Discrete Ordinates": "1e-06",
        "IsEnabled": False,
        "Radiation Model": "Off",
        "Under-relaxation - Pressure": "0.7",
        "Under-relaxation - Momentum": "0.3",
        "Under-relaxation - Temperature": "1",
        "Under-relaxation - Turbulent Kinetic Energy": "0.8",
        "Under-relaxation - Turbulent Dissipation Rate": "0.8",
        "Under-relaxation - Specific Dissipation Rate": "0.8",
        "Discretization Scheme - Pressure": "Standard",
        "Discretization Scheme - Momentum": "First",
        "Discretization Scheme - Temperature": "First",
        "Secondary Gradient": False,
        "Discretization Scheme - Turbulent Kinetic Energy": "First",
        "Discretization Scheme - Turbulent Dissipation Rate": "First",
        "Discretization Scheme - Specific Dissipation Rate": "First",
        "Discretization Scheme - Discrete Ordinates": "First",
        "Linear Solver Type - Pressure": "V",
        "Linear Solver Type - Momentum": "flex",
        "Linear Solver Type - Temperature": "F",
        "Linear Solver Type - Turbulent Kinetic Energy": "flex",
        "Linear Solver Type - Turbulent Dissipation Rate": "flex",
        "Linear Solver Type - Specific Dissipation Rate": "flex",
        "Linear Solver Termination Criterion - Pressure": "0.1",
        "Linear Solver Termination Criterion - Momentum": "0.1",
        "Linear Solver Termination Criterion - Temperature": "0.1",
        "Linear Solver Termination Criterion - Turbulent Kinetic Energy": "0.1",
        "Linear Solver Termination Criterion - Turbulent Dissipation  Rate": "0.1",
        "Linear Solver Termination Criterion - Specific Dissipation Rate": "0.1",
        "Linear Solver Residual Reduction Tolerance - Pressure": "0.1",
        "Linear Solver Residual Reduction Tolerance - Momentum": "0.1",
        "Linear Solver Residual Reduction Tolerance - Temperature": "0.1",
        "Linear Solver Residual Reduction Tolerance - Turbulent Kinetic Energy": "0.1",
        "Linear Solver Residual Reduction Tolerance - Turbulent Dissipation Rate": "0.1",
        "Linear Solver Residual Reduction Tolerance - Specific Dissipation Rate": "0.1",
        "Linear Solver Stabilization - Pressure": "None",
        "Linear Solver Stabilization - Temperature": "None",
        "Frozen Flow Simulation": False,
        "Sequential Solve of Flow and Energy Equations": False,
        "Convergence Criteria - Max Iterations": 100,
    }
)
"""Icepak steady flow setup properties and default values."""

Q3DCond = dict({"MaxPass": 10, "MinPass": 1, "MinConvPass": 1, "PerError": 1, "PerRefine": 30})
Q3DMult = dict({"MaxPass": 1, "MinPass": 1, "MinConvPass": 1, "PerError": 1, "PerRefine": 30})
Q3DDC = dict({"SolveResOnly": False, "Cond": Q3DCond, "Mult": Q3DMult})
Q3DCap = dict(
    {
        "MaxPass": 10,
        "MinPass": 1,
        "MinConvPass": 1,
        "PerError": 1,
        "PerRefine": 30,
        "AutoIncreaseSolutionOrder": True,
        "SolutionOrder": "High",
        "Solver Type": "Iterative",
    }
)
Q3DAC = dict({"MaxPass": 10, "MinPass": 1, "MinConvPass": 1, "PerError": 1, "PerRefine": 30})
Matrix = dict(
    {
        "AdaptiveFreq": "1GHz",
        "SaveFields": False,
        "Enabled": True,
        "Cap": Q3DCap,
        "DC": Q3DDC,
        "AC": Q3DAC,
    }
)
"""Q3D Extractor setup properties and default values."""

OutputQuantities = {}
NoiseOutputQuantities = {}
SweepDefinition = dict({"Variable": "Freq", "Data": "LINC 1GHz 5GHz 501", "OffsetF1": False, "Synchronize": 0})
NexximLNA = dict(
    {
        "DataBlockID": 16,
        "OptionName": "Default Options",
        "AdditionalOptions": "",
        "AlterBlockName": "",
        "FilterText": "",
        "AnalysisEnabled": 1,
        "OutputQuantities": OutputQuantities,
        "NoiseOutputQuantities": NoiseOutputQuantities,
        "Name": "LinearFrequency",
        "LinearFrequencyData": [False, 0.1, False, "", False],
        "SweepDefinition": SweepDefinition,
    }
)
"""Nexxim linear network setup properties and default values."""

NexximDC = dict(
    {
        "DataBlockID": 15,
        "OptionName": "Default Options",
        "AdditionalOptions": "",
        "AlterBlockName": "",
        "FilterText": "",
        "AnalysisEnabled": 1,
        "OutputQuantities": OutputQuantities,
        "NoiseOutputQuantities": NoiseOutputQuantities,
        "Name": "LinearFrequency",
    }
)
"""Nexxim DC setup properties and default values."""

NexximTransient = dict(
    {
        "DataBlockID": 10,
        "OptionName": "Default Options",
        "AdditionalOptions": "",
        "AlterBlockName": "",
        "FilterText": "",
        "AnalysisEnabled": 1,
        "OutputQuantities": OutputQuantities,
        "NoiseOutputQuantities": NoiseOutputQuantities,
        "Name": "LinearFrequency",
        "TransientData": ["0.1ns", "10ns"],
        "TransientNoiseData": [False, "", "", 0, 1, 0, False, 1],
        "TransientOtherData": ["default"],
    }
)
"""Nexxim transient setup properties and default values."""

NexximQuickEye = dict(
    {
        "DataBlockID": 28,
        "OptionName": "Default Options",
        "AdditionalOptions": "",
        "AlterBlockName": "",
        "FilterText": "",
        "AnalysisEnabled": 1,
        "OutputQuantities": OutputQuantities,
        "NoiseOutputQuantities": NoiseOutputQuantities,
        "Name": "QuickEyeAnalysis",
        "QuickEyeAnalysis": [False, "1e-9", False, "0", "", True],
    }
)
NexximVerifEye = dict(
    {
        "DataBlockID": 27,
        "OptionName": "Default Options",
        "AdditionalOptions": "",
        "AlterBlockName": "",
        "FilterText": "",
        "AnalysisEnabled": 1,
        "OutputQuantities": OutputQuantities,
        "NoiseOutputQuantities": NoiseOutputQuantities,
        "Name": "VerifEyeAnalysis",
        "VerifEyeAnalysis": [False, "1e-9", False, "0", "", True],
    }
)
NexximAMI = dict(
    {
        "DataBlockID": 29,
        "OptionName": "Default Options",
        "AdditionalOptions": "",
        "AlterBlockName": "",
        "FilterText": "",
        "AnalysisEnabled": 1,
        "OutputQuantities": OutputQuantities,
        "NoiseOutputQuantities": NoiseOutputQuantities,
        "Name": "AMIAnalysis",
        "InputType": 1,
        "DataBlockSize": 10000,
        "AMIAnalysis": [32, False, False],
    }
)
NexximOscillatorRSF = {}
NexximOscillator1T = {}
NexximOscillatorNT = {}
NexximHarmonicBalance1T = {}
NexximHarmonicBalanceNT = {}
NexximSystem = dict(
    {
        "DataBlockID": 32,
        "OptionName": "Default Options",
        "AdditionalOptions": "",
        "AlterBlockName": "",
        "FilterText": "",
        "AnalysisEnabled": 1,
        "OutputQuantities": OutputQuantities,
        "NoiseOutputQuantities": NoiseOutputQuantities,
        "Name": "HSPICETransient",
        "HSPICETransientData": ["0.1ns", "10ns"],
        "HSPICETransientOtherData": [3],
    }
)
NexximTVNoise = {}
HSPICE = dict(
    {
        "DataBlockID": 30,
        "OptionName": "Default Options",
        "AdditionalOptions": "",
        "AlterBlockName": "",
        "FilterText": "",
        "AnalysisEnabled": 1,
        "OutputQuantities": OutputQuantities,
        "NoiseOutputQuantities": NoiseOutputQuantities,
        "Name": "SystemFDAnalysis",
        "SystemFDAnalysis": [False],
    }
)

HFSS3DLayout_Properties = dict({"Enable": "true"})
HFSS3DLayout_AdvancedSettings = dict(
    {
        "AccuracyLevel": 2,
        "GapPortCalibration": True,
        "ReferenceLengthRatio": 0.25,
        "RefineAreaRatio": 4,
        "DRCOn": False,
        "FastSolverOn": False,
        "StartFastSolverAt": 3000,
        "LoopTreeOn": True,
        "SingularElementsOn": False,
        "UseStaticPortSolver": False,
        "UseThinMetalPortSolver": False,
        "ComputeBothEvenAndOddCPWModes": False,
        "ZeroMetalLayerThickness": 0,
        "ThinDielectric": 0,
        "UseShellElements": False,
        "SVDHighCompression": False,
        "NumProcessors": 1,
        "SolverType": "Direct Solver",  # 2022.2
        "UseHfssIterativeSolver": False,
        "UseHfssMUMPSSolver": True,
        "RelativeResidual": 1e-06,
        "EnhancedLowFreqAccuracy": False,
        "OrderBasis": -1,
        "MaxDeltaZo": 2,
        "UseRadBoundaryOnPorts": False,
        "SetTrianglesForWavePort": False,
        "MinTrianglesForWavePort": 100,
        "MaxTrianglesForWavePort": 500,
        "numprocessorsdistrib": 1,
        "CausalMaterials": True,
        "enabledsoforopti": True,
        "usehfsssolvelicense": False,
        "ExportAfterSolve": False,
        "ExportDir": "",
        "CircuitSparamDefinition": False,
        "CircuitIntegrationType": "FFT",
        "DesignType": "generic",
        "MeshingMethod": "Phi",
        "EnableDesignIntersectionCheck": True,
        "UseAlternativeMeshMethodsAsFallBack": True,
        "ModeOption": "General mode",  # 2022.2
        "BroadbandFreqOption": "AutoMaxFreq",
        "BroadbandMaxNumFreq": 5,
        "SaveADP": True,
        "UseAdvancedDCExtrap": False,
        "PhiMesherDeltaZRatio": 100000,  # 2023.1
    }
)
HFSS3DLayout_CurveApproximation = dict(
    {
        "ArcAngle": "30deg",
        "StartAzimuth": "0deg",
        "UseError": False,
        "Error": "0meter",
        "MaxPoints": 8,
        "UnionPolys": True,
        "Replace3DTriangles": True,
    }
)
HFSS3DLayout_Q3D_DCSettings = dict(
    {
        "SolveResOnly": True,
        "Cond": Q3DCond,
        "Mult": Q3DMult,
        "Solution Order": "Normal",
    }
)

CGDataBlock = dict(
    {
        "MaxPass": 10,
        "MinPass": 1,
        "MinConvPass": 1,
        "PerError": 1,
        "PerRefine": 30,
        "DataType": "CG",
        "Included": True,
        "UseParamConv": True,
        "UseLossyParamConv": False,
        "PerErrorParamConv": 1,
        "UseLossConv": True,
    }
)
RLDataBlock = dict(
    {
        "MaxPass": 10,
        "MinPass": 1,
        "MinConvPass": 1,
        "PerError": 1,
        "PerRefine": 30,
        "DataType": "CG",
        "Included": True,
        "UseParamConv": True,
        "UseLossyParamConv": False,
        "PerErrorParamConv": 1,
        "UseLossConv": True,
    }
)
Open = dict(
    {
        "AdaptiveFreq": "1GHz",
        "SaveFields": True,
        "Enabled": True,
        "MeshLink": meshlink,
        "CGDataBlock": CGDataBlock,
        "RLDataBlock": RLDataBlock,
        "CacheSaveKind": "Delta",
        "ConstantDelta": "0s",
    }
)
"""Q2D open setup properties and default values."""

Close = dict(
    {
        "AdaptiveFreq": "1GHz",
        "SaveFields": True,
        "Enabled": True,
        "MeshLink": meshlink,
        "CGDataBlock": CGDataBlock,
        "RLDataBlock": RLDataBlock,
        "CacheSaveKind": "Delta",
        "ConstantDelta": "0s",
    }
)
"""Q2D close setup properties and default values."""

TransientTemperatureAndFlow = dict(
    {
        "Enabled": True,
        "Flow Regime": "Laminar",
        "Turbulent Model Eqn": "ZeroEquation",
        "Include Temperature": True,
        "Include Flow": True,
        "Include Gravity": False,
        "Include Solar": False,
        "Solution Initialization - X Velocity": "0m_per_sec",
        "Solution Initialization - Y Velocity": "0m_per_sec",
        "Solution Initialization - Z Velocity": "0m_per_sec",
        "Solution Initialization - Temperature": "AmbientTemp",
        "Solution Initialization - Turbulent Kinetic Energy": "1m2_per_s2",
        "Solution Initialization - Turbulent Dissipation Rate": "1m2_per_s3",
        "Solution Initialization - Specific Dissipation Rate": "1diss_per_s",
        "Solution Initialization - Use Model Based Flow Initialization": False,
        "Convergence Criteria - Flow": "0.001",
        "Convergence Criteria - Energy": "1e-07",
        "Convergence Criteria - Turbulent Kinetic Energy": "0.001",
        "Convergence Criteria - Turbulent Dissipation Rate": "0.001",
        "Convergence Criteria - Specific Dissipation Rate": "0.001",
        "Convergence Criteria - Discrete Ordinates": "1e-06",
        "IsEnabled": False,
        "Radiation Model": "Off",
        "Solar Radiation Model": "Solar Radiation Calculator",
        "Solar Radiation - Scattering Fraction": "0",
        "Solar Radiation - Day": 1,
        "Solar Radiation - Month": 1,
        "Solar Radiation - Hours": 0,
        "Solar Radiation - Minutes": 0,
        "Solar Radiation - GMT": "0",
        "Solar Radiation - Latitude": "0",
        "Solar Radiation - Latitude Direction": "East",
        "Solar Radiation - Longitude": "0",
        "Solar Radiation - Longitude Direction": "North",
        "Solar Radiation - Ground Reflectance": "0",
        "Solar Radiation - Sunshine Fraction": "0",
        "Solar Radiation - North X": "0",
        "Solar Radiation - North Y": "0",
        "Solar Radiation - North Z": "1",
        "Under-relaxation - Pressure": "0.3",
        "Under-relaxation - Momentum": "0.7",
        "Under-relaxation - Temperature": "1",
        "Under-relaxation - Turbulent Kinetic Energy": "0.8",
        "Under-relaxation - Turbulent Dissipation Rate": "0.8",
        "Under-relaxation - Specific Dissipation Rate": "0.8",
        "Discretization Scheme - Pressure": "Standard",
        "Discretization Scheme - Momentum": "First",
        "Discretization Scheme - Temperature": "First",
        "Secondary Gradient": False,
        "Discretization Scheme - Turbulent Kinetic Energy": "First",
        "Discretization Scheme - Turbulent Dissipation Rate": "First",
        "Discretization Scheme - Specific Dissipation Rate": "First",
        "Discretization Scheme - Discrete Ordinates": "First",
        "Linear Solver Type - Pressure": "V",
        "Linear Solver Type - Momentum": "flex",
        "Linear Solver Type - Temperature": "F",
        "Linear Solver Type - Turbulent Kinetic Energy": "flex",
        "Linear Solver Type - Turbulent Dissipation Rate": "flex",
        "Linear Solver Type - Specific Dissipation Rate": "flex",
        "Linear Solver Termination Criterion - Pressure": "0.1",
        "Linear Solver Termination Criterion - Momentum": "0.1",
        "Linear Solver Termination Criterion - Temperature": "0.1",
        "Linear Solver Termination Criterion - Turbulent Kinetic Energy": "0.1",
        "Linear Solver Termination Criterion - Turbulent Dissipation Rate": "0.1",
        "Linear Solver Termination Criterion - Specific Dissipation Rate": "0.1",
        "Linear Solver Residual Reduction Tolerance - Pressure": "0.1",
        "Linear Solver Residual Reduction Tolerance - Momentum": "0.1",
        "Linear Solver Residual Reduction Tolerance - Temperature": "0.1",
        "Linear Solver Residual Reduction Tolerance - Turbulent Kinetic Energy": "0.1",
        "Linear Solver Residual Reduction Tolerance - Turbulent Dissipation Rate": "0.1",
        "Linear Solver Residual Reduction Tolerance - Specific Dissipation Rate": "0.1",
        "Linear Solver Stabilization - Pressure": "None",
        "Linear Solver Stabilization - Temperature": "None",
        "Coupled pressure-velocity formulation": False,
        "Frozen Flow Simulation": False,
        "Start Time": "0s",
        "Stop Time": "20s",
        "Time Step": "1s",
        "Iterations per Time Step": 20,
        "Import Start Time": False,
        "Copy Fields From Source": False,
        "SaveFieldsType": "Every N Steps",
        "N Steps": "10",
        "Enable Control Program": False,
        "Control Program Name": "",
    }
)
"""Icepak Transient Temperature and Flow setup properties and default values."""

TransientTemperatureOnly = dict(
    {
        "Enabled": True,
        "Flow Regime": "Laminar",
        "Turbulent Model Eqn": "ZeroEquation",
        "Include Temperature": True,
        "Include Flow": False,
        "Include Gravity": False,
        "Include Solar": False,
        "Solution Initialization - X Velocity": "0m_per_sec",
        "Solution Initialization - Y Velocity": "0m_per_sec",
        "Solution Initialization - Z Velocity": "0m_per_sec",
        "Solution Initialization - Temperature": "AmbientTemp",
        "Solution Initialization - Turbulent Kinetic Energy": "1m2_per_s2",
        "Solution Initialization - Turbulent Dissipation Rate": "1m2_per_s3",
        "Solution Initialization - Specific Dissipation Rate": "1diss_per_s",
        "Solution Initialization - Use Model Based Flow Initialization": False,
        "Convergence Criteria - Flow": "0.001",
        "Convergence Criteria - Energy": "1e-07",
        "Convergence Criteria - Turbulent Kinetic Energy": "0.001",
        "Convergence Criteria - Turbulent Dissipation Rate": "0.001",
        "Convergence Criteria - Specific Dissipation Rate": "0.001",
        "Convergence Criteria - Discrete Ordinates": "1e-06",
        "IsEnabled": False,
        "Radiation Model": "Off",
        "Solar Radiation Model": "Solar Radiation Calculator",
        "Solar Radiation - Scattering Fraction": "0",
        "Solar Radiation - Day": 1,
        "Solar Radiation - Month": 1,
        "Solar Radiation - Hours": 0,
        "Solar Radiation - Minutes": 0,
        "Solar Radiation - GMT": "0",
        "Solar Radiation - Latitude": "0",
        "Solar Radiation - Latitude Direction": "East",
        "Solar Radiation - Longitude": "0",
        "Solar Radiation - Longitude Direction": "North",
        "Solar Radiation - Ground Reflectance": "0",
        "Solar Radiation - Sunshine Fraction": "0",
        "Solar Radiation - North X": "0",
        "Solar Radiation - North Y": "0",
        "Solar Radiation - North Z": "1",
        "Under-relaxation - Pressure": "0.3",
        "Under-relaxation - Momentum": "0.7",
        "Under-relaxation - Temperature": "1",
        "Under-relaxation - Turbulent Kinetic Energy": "0.8",
        "Under-relaxation - Turbulent Dissipation Rate": "0.8",
        "Under-relaxation - Specific Dissipation Rate": "0.8",
        "Discretization Scheme - Pressure": "Standard",
        "Discretization Scheme - Momentum": "First",
        "Discretization Scheme - Temperature": "First",
        "Secondary Gradient": False,
        "Discretization Scheme - Turbulent Kinetic Energy": "First",
        "Discretization Scheme - Turbulent Dissipation Rate": "First",
        "Discretization Scheme - Specific Dissipation Rate": "First",
        "Discretization Scheme - Discrete Ordinates": "First",
        "Linear Solver Type - Pressure": "V",
        "Linear Solver Type - Momentum": "flex",
        "Linear Solver Type - Temperature": "F",
        "Linear Solver Type - Turbulent Kinetic Energy": "flex",
        "Linear Solver Type - Turbulent Dissipation Rate": "flex",
        "Linear Solver Type - Specific Dissipation Rate": "flex",
        "Linear Solver Termination Criterion - Pressure": "0.1",
        "Linear Solver Termination Criterion - Momentum": "0.1",
        "Linear Solver Termination Criterion - Temperature": "0.1",
        "Linear Solver Termination Criterion - Turbulent Kinetic Energy": "0.1",
        "Linear Solver Termination Criterion - Turbulent Dissipation Rate": "0.1",
        "Linear Solver Termination Criterion - Specific Dissipation Rate": "0.1",
        "Linear Solver Residual Reduction Tolerance - Pressure": "0.1",
        "Linear Solver Residual Reduction Tolerance - Momentum": "0.1",
        "Linear Solver Residual Reduction Tolerance - Temperature": "0.1",
        "Linear Solver Residual Reduction Tolerance - Turbulent Kinetic Energy": "0.1",
        "Linear Solver Residual Reduction Tolerance - Turbulent Dissipation Rate": "0.1",
        "Linear Solver Residual Reduction Tolerance - Specific Dissipation Rate": "0.1",
        "Linear Solver Stabilization - Pressure": "None",
        "Linear Solver Stabilization - Temperature": "None",
        "Coupled pressure-velocity formulation": False,
        "Frozen Flow Simulation": False,
        "Start Time": "0s",
        "Stop Time": "20s",
        "Time Step": "1s",
        "Iterations per Time Step": 20,
        "Import Start Time": False,
        "Copy Fields From Source": False,
        "SaveFieldsType": "Every N Steps",
        "N Steps": "10",
        "Enable Control Program": False,
        "Control Program Name": "",
    }
)
"""Icepak Transient Temperature only setup properties and default values."""

TransientFlowOnly = dict(
    {
        "Enabled": True,
        "Flow Regime": "Laminar",
        "Turbulent Model Eqn": "ZeroEquation",
        "Include Temperature": False,
        "Include Flow": True,
        "Include Gravity": False,
        "Include Solar": False,
        "Solution Initialization - X Velocity": "0m_per_sec",
        "Solution Initialization - Y Velocity": "0m_per_sec",
        "Solution Initialization - Z Velocity": "0m_per_sec",
        "Solution Initialization - Temperature": "AmbientTemp",
        "Solution Initialization - Turbulent Kinetic Energy": "1m2_per_s2",
        "Solution Initialization - Turbulent Dissipation Rate": "1m2_per_s3",
        "Solution Initialization - Specific Dissipation Rate": "1diss_per_s",
        "Solution Initialization - Use Model Based Flow Initialization": False,
        "Convergence Criteria - Flow": "0.001",
        "Convergence Criteria - Energy": "1e-07",
        "Convergence Criteria - Turbulent Kinetic Energy": "0.001",
        "Convergence Criteria - Turbulent Dissipation Rate": "0.001",
        "Convergence Criteria - Specific Dissipation Rate": "0.001",
        "Convergence Criteria - Discrete Ordinates": "1e-06",
        "IsEnabled": False,
        "Radiation Model": "Off",
        "Solar Radiation Model": "Solar Radiation Calculator",
        "Solar Radiation - Scattering Fraction": "0",
        "Solar Radiation - Day": 1,
        "Solar Radiation - Month": 1,
        "Solar Radiation - Hours": 0,
        "Solar Radiation - Minutes": 0,
        "Solar Radiation - GMT": "0",
        "Solar Radiation - Latitude": "0",
        "Solar Radiation - Latitude Direction": "East",
        "Solar Radiation - Longitude": "0",
        "Solar Radiation - Longitude Direction": "North",
        "Solar Radiation - Ground Reflectance": "0",
        "Solar Radiation - Sunshine Fraction": "0",
        "Solar Radiation - North X": "0",
        "Solar Radiation - North Y": "0",
        "Solar Radiation - North Z": "1",
        "Under-relaxation - Pressure": "0.3",
        "Under-relaxation - Momentum": "0.7",
        "Under-relaxation - Temperature": "1",
        "Under-relaxation - Turbulent Kinetic Energy": "0.8",
        "Under-relaxation - Turbulent Dissipation Rate": "0.8",
        "Under-relaxation - Specific Dissipation Rate": "0.8",
        "Discretization Scheme - Pressure": "Standard",
        "Discretization Scheme - Momentum": "First",
        "Discretization Scheme - Temperature": "First",
        "Secondary Gradient": False,
        "Discretization Scheme - Turbulent Kinetic Energy": "First",
        "Discretization Scheme - Turbulent Dissipation Rate": "First",
        "Discretization Scheme - Specific Dissipation Rate": "First",
        "Discretization Scheme - Discrete Ordinates": "First",
        "Linear Solver Type - Pressure": "V",
        "Linear Solver Type - Momentum": "flex",
        "Linear Solver Type - Temperature": "F",
        "Linear Solver Type - Turbulent Kinetic Energy": "flex",
        "Linear Solver Type - Turbulent Dissipation Rate": "flex",
        "Linear Solver Type - Specific Dissipation Rate": "flex",
        "Linear Solver Termination Criterion - Pressure": "0.1",
        "Linear Solver Termination Criterion - Momentum": "0.1",
        "Linear Solver Termination Criterion - Temperature": "0.1",
        "Linear Solver Termination Criterion - Turbulent Kinetic Energy": "0.1",
        "Linear Solver Termination Criterion - Turbulent Dissipation Rate": "0.1",
        "Linear Solver Termination Criterion - Specific Dissipation Rate": "0.1",
        "Linear Solver Residual Reduction Tolerance - Pressure": "0.1",
        "Linear Solver Residual Reduction Tolerance - Momentum": "0.1",
        "Linear Solver Residual Reduction Tolerance - Temperature": "0.1",
        "Linear Solver Residual Reduction Tolerance - Turbulent Kinetic Energy": "0.1",
        "Linear Solver Residual Reduction Tolerance - Turbulent Dissipation Rate": "0.1",
        "Linear Solver Residual Reduction Tolerance - Specific Dissipation Rate": "0.1",
        "Linear Solver Stabilization - Pressure": "None",
        "Linear Solver Stabilization - Temperature": "None",
        "Coupled pressure-velocity formulation": False,
        "Frozen Flow Simulation": False,
        "Start Time": "0s",
        "Stop Time": "20s",
        "Time Step": "1s",
        "Iterations per Time Step": 20,
        "Import Start Time": False,
        "Copy Fields From Source": False,
        "SaveFieldsType": "Every N Steps",
        "N Steps": "10",
        "Enable Control Program": False,
        "Control Program Name": "",
    }
)
"""Icepak Transient Flow only setup properties and default values."""

HFSS3DLayout_SingleFrequencyDataList = dict({"AdaptiveFrequencyData": HFSS3DLayout_AdaptiveFrequencyData("5GHz")})
HFSS3DLayout_BroadbandFrequencyDataList = dict(
    {
        "AdaptiveFrequencyData": [
            HFSS3DLayout_AdaptiveFrequencyData("5GHz"),
            HFSS3DLayout_AdaptiveFrequencyData("10GHz"),
        ]
    }
)
HFSS3DLayout_MultiFrequencyDataList = dict(
    {
        "AdaptiveFrequencyData": [
            HFSS3DLayout_AdaptiveFrequencyData("2.5GHz"),
            HFSS3DLayout_AdaptiveFrequencyData("5GHz"),
            HFSS3DLayout_AdaptiveFrequencyData("10GHz"),
        ]
    }
)
HFSS3DLayout_AdaptiveSettings = dict(
    {
        "DoAdaptive": True,
        "SaveFields": False,
        "SaveRadFieldsOnly": False,
        "MaxRefinePerPass": 30,
        "MinPasses": 1,
        "MinConvergedPasses": 1,
        "AdaptType": "kSingle",  # possible values are "kSingle": "kMultiFrequencies": "kBroadband"
        "Basic": True,
        "SingleFrequencyDataList": HFSS3DLayout_SingleFrequencyDataList,
        "BroadbandFrequencyDataList": HFSS3DLayout_BroadbandFrequencyDataList,
        "MultiFrequencyDataList": HFSS3DLayout_MultiFrequencyDataList,
    }
)
HFSS3DLayout = dict(
    {
        "Properties": HFSS3DLayout_Properties,
        "CustomSetup": False,
        "SolveSetupType": "HFSS",
        "PercentRefinementPerPass": 30,
        "MinNumberOfPasses": 1,
        "MinNumberOfConvergedPasses": 1,
        "UseDefaultLambda": True,
        "UseMaxRefinement": False,
        "MaxRefinement": 1000000,
        "SaveAdaptiveCurrents": False,
        "SaveLastAdaptiveRadFields": False,
        "ProdMajVerID": -1,
        "ProjDesignSetup": "",
        "ProdMinVerID": -1,
        "Refine": False,
        "Frequency": "10GHz",
        "LambdaRefine": True,
        "MeshSizeFactor": 1.5,
        "QualityRefine": True,
        "MinAngle": "15deg",
        "UniformityRefine": False,
        "MaxRatio": 2,
        "Smooth": False,
        "SmoothingPasses": 5,
        "UseEdgeMesh": False,
        "UseEdgeMeshAbsLength": False,
        "EdgeMeshRatio": 0.1,
        "EdgeMeshAbsLength": "1000mm",
        "LayerProjectThickness": "0meter",
        "UseDefeature": True,
        "UseDefeatureAbsLength": False,
        "DefeatureRatio": 1e-06,
        "DefeatureAbsLength": "0mm",
        "InfArrayDimX": 0,
        "InfArrayDimY": 0,
        "InfArrayOrigX": 0,
        "InfArrayOrigY": 0,
        "InfArraySkew": 0,
        "ViaNumSides": 6,
        "ViaMaterial": "copper",
        "Style25DVia": "Mesh",
        "Replace3DTriangles": True,
        "LayerSnapTol": "1e-05",
        "ViaDensity": 0,
        "HfssMesh": True,
        "Q3dPostProc": False,
        "UnitFactor": 1000,
        "Verbose": False,
        "NumberOfProcessors": 0,
        "SmallVoidArea": -2e-09,
        "HealingOption": 1,
        "InclBBoxOption": 1,
        "AuxBlock": {},
        "DoAdaptive": True,
        "Color": ["R", 0, "G", 0, "B", 0],  # TODO: create something smart for color arrays: like a class
        "AdvancedSettings": HFSS3DLayout_AdvancedSettings,
        "CurveApproximation": HFSS3DLayout_CurveApproximation,
        "Q3D_DCSettings": HFSS3DLayout_Q3D_DCSettings,
        "AdaptiveSettings": HFSS3DLayout_AdaptiveSettings,
    }
)

HFSS3DLayout_v231 = dict(
    {
        "Properties": HFSS3DLayout_Properties,
        "CustomSetup": False,
        "AutoSetup": False,
        "SliderType": "Balanced",
        "SolveSetupType": "HFSS",
        "PercentRefinementPerPass": 30,
        "MinNumberOfPasses": 1,
        "MinNumberOfConvergedPasses": 1,
        "UseDefaultLambda": True,
        "UseMaxRefinement": False,
        "MaxRefinement": 1000000,
        "SaveAdaptiveCurrents": False,
        "SaveLastAdaptiveRadFields": False,
        "UseConvergenceMatrix": False,
        "AllEntries": False,
        "AllDiagEntries": False,
        "AllOffDiagEntries": False,
        "MagMinThreshold": 0.01,
        "ProdMajVerID": -1,
        "ProjDesignSetup": "",
        "ProdMinVerID": -1,
        "Refine": False,
        "Frequency": "10GHz",
        "LambdaRefine": True,
        "MeshSizeFactor": 1.5,
        "QualityRefine": True,
        "MinAngle": "15deg",
        "UniformityRefine": False,
        "MaxRatio": 2,
        "Smooth": False,
        "SmoothingPasses": 5,
        "UseEdgeMesh": False,
        "UseEdgeMeshAbsLength": False,
        "EdgeMeshRatio": 0.1,
        "EdgeMeshAbsLength": "1000mm",
        "LayerProjectThickness": "0meter",
        "UseDefeature": True,
        "UseDefeatureAbsLength": False,
        "DefeatureRatio": 1e-06,
        "DefeatureAbsLength": "0mm",
        "InfArrayDimX": 0,
        "InfArrayDimY": 0,
        "InfArrayOrigX": 0,
        "InfArrayOrigY": 0,
        "InfArraySkew": 0,
        "ViaNumSides": 6,
        "ViaMaterial": "copper",
        "Style25DVia": "Mesh",
        "Replace3DTriangles": True,
        "LayerSnapTol": "1e-05",
        "ViaDensity": 0,
        "HfssMesh": True,
        "Q3dPostProc": False,
        "UnitFactor": 1000,
        "Verbose": False,
        "NumberOfProcessors": 0,
        "SmallVoidArea": -2e-09,
        "RemoveFloatingGeometry": False,
        "HealingOption": 1,
        "InclBBoxOption": 1,
        "ModelType": 0,
        "ICModeAuto": 1,
        "ICModeLength": "50nm",
        "AuxBlock": {},
        "DoAdaptive": True,
        "Color": ["R", 0, "G", 0, "B", 0],  # TODO: create something smart for color arrays: like a class
        "AdvancedSettings": HFSS3DLayout_AdvancedSettings,
        "CurveApproximation": HFSS3DLayout_CurveApproximation,
        "Q3D_DCSettings": HFSS3DLayout_Q3D_DCSettings,
        "AdaptiveSettings": HFSS3DLayout_AdaptiveSettings,
        "Data": {},
        "MeshOps": {},
    }
)
"""HFSS 3D Layout setup properties and default values."""

HFSS3DLayout_SweepDataList = {}
HFSS3DLayout_SIWAdvancedSettings = dict(
    {
        "IncludeCoPlaneCoupling": True,
        "IncludeInterPlaneCoupling": False,
        "IncludeSplitPlaneCoupling": True,
        "IncludeFringeCoupling": True,
        "IncludeTraceCoupling": True,
        "XtalkThreshold": "-34",
        "MaxCoupledLines": 12,
        "MinVoidArea": "2mm2",
        "MinPadAreaToMesh": "1mm2",
        "MinPlaneAreaToMesh": "6.25e-6mm2",
        "SnapLengthThreshold": "2.5um",
        "MeshAutoMatic": True,
        "MeshFrequency": "4GHz",
        "ReturnCurrentDistribution": False,
        "IncludeVISources": False,
        "IncludeInfGnd": False,
        "InfGndLocation": "0mm",
        "PerformERC": False,
        "IgnoreNonFunctionalPads": True,
    }
)
HFSS3DLayout_SIWDCSettings = dict(
    {
        "UseDCCustomSettings": False,
        "PlotJV": True,
        "ComputeInductance": False,
        "ContactRadius": "0.1mm",
        "DCSliderPos": 1,
    }
)
HFSS3DLayout_SIWDCAdvancedSettings = dict(
    {
        "DcMinPlaneAreaToMesh": "0.25mm2",
        "DcMinVoidAreaToMesh": "0.01mm2",
        "MaxInitMeshEdgeLength": "2.5mm",
        "PerformAdaptiveRefinement": True,
        "MaxNumPasses": 5,
        "MinNumPasses": 1,
        "PercentLocalRefinement": 20,
        "EnergyError": 2,
        "MeshBws": True,
        "RefineBws": False,
        "MeshVias": True,
        "RefineVias": False,
        "NumBwSides": 8,
        "NumViaSides": 8,
    }
)
HFSS3DLayout_SIWDCIRSettings = dict(
    {
        "IcepakTempFile": "D:/Program Files/AnsysEM/AnsysEM21.2/Win64/",
        "SourceTermsToGround": {},
        "ExportDCThermalData": False,
        "ImportThermalData": False,
        "FullDCReportPath": "",
        "ViaReportPath": "",
        "PerPinResPath": "",
        "DCReportConfigFile": "",
        "DCReportShowActiveDevices": False,
        "PerPinUsePinFormat": False,
        "UseLoopResForPerPin": False,
    }
)

HFSS3DLayout_SimulationSettings = dict(
    {
        "Enabled": True,
        "UseSISettings": True,
        "UseCustomSettings": False,
        "SISliderPos": 1,
        "PISliderPos": 1,
        "SIWAdvancedSettings": HFSS3DLayout_SIWAdvancedSettings,
        "SIWDCSettings": HFSS3DLayout_SIWDCSettings,
        "SIWDCAdvancedSettings": HFSS3DLayout_SIWDCAdvancedSettings,
        "SIWDCIRSettings": HFSS3DLayout_SIWDCIRSettings,
    }
)

HFSS3DLayout_ACSimulationSettings = dict(
    {
        "Enabled": True,
        "UseSISettings": True,
        "UseCustomSettings": False,
        "SISliderPos": 1,
        "PISliderPos": 1,
        "SIWAdvancedSettings": HFSS3DLayout_SIWAdvancedSettings,
        "SIWDCSettings": HFSS3DLayout_SIWDCSettings,
        "SIWDCAdvancedSettings": HFSS3DLayout_SIWDCAdvancedSettings,
    }
)
SiwaveAC3DLayout = dict(
    {
        "Properties": HFSS3DLayout_Properties,
        "CustomSetup": False,
        "SolveSetupType": "SIwave",
        "Color": ["R", 0, "G", 0, "B", 0],
        "Position": 0,
        "SimSetupType": "kSIwave",
        "SimulationSettings": HFSS3DLayout_ACSimulationSettings,
        "SweepDataList": HFSS3DLayout_SweepDataList,
    }
)

SiwaveDC3DLayout = dict(
    {
        "Properties": HFSS3DLayout_Properties,
        "CustomSetup": False,
        "SolveSetupType": "SIwaveDCIR",
        "Position": 0,
        "SimSetupType": "kSIwaveDCIR",
        "SimulationSettings": HFSS3DLayout_SimulationSettings,
        "SweepDataList": HFSS3DLayout_SweepDataList,
    }
)

HFSS3DLayout_LNASimulationSettings = dict(
    {
        "Enabled": True,
        "GroupDelay": False,
        "Perturbation": 0.1,
        "Noise": False,
        "Skip_DC": False,
        "AdditionalOptions": "",
        "BaseOptionName": "Default Options",
        "FilterText": "",
    }
)
LNA_Sweep = dict(
    {
        "DataId": "Sweep0",
        "Properties": HFSS3DLayout_Properties,
        "Sweep": SweepDefinition,
        "SolutionID": -1,
    }
)
HFSS3DLayout_LNAData = dict({"LNA Sweep 1": LNA_Sweep})
LNA3DLayout = dict(
    {
        "Properties": HFSS3DLayout_Properties,
        "CustomSetup": False,
        "SolveSetupType": "LNA",
        "Position": 0,
        "SimSetupType": "kLNA",
        "SimulationSettings": HFSS3DLayout_LNASimulationSettings,
        "SweepDataList": HFSS3DLayout_SweepDataList,
        "Data": HFSS3DLayout_LNAData,
    }
)
MechTerm = dict(
    {
        "Enabled": True,
        "MeshLink": meshlink,
        "Solver": "Program Controlled",
        "Stepping": "Program Controlled",
    }
)
"""Mechanical thermal setup properties and default values."""

MechTransientThermal = dict(
    {
        "Enabled": True,
        "MeshLink": meshlink,
        "Solver": "Program Controlled",
        "Stepping": "Program Controlled",
        "Stepping Define By": "Time",
        "TemperatureConvergenceCondition": "Program Controlled",
        "TemperatureConvergenceTolerance": "0.5",
        "TemperatureConvergenceMinRef": "0cel",
        "HeatConvergenceCondition": "Program Controlled",
        "HeatConvergenceTolerance": "0.5",
        "HeatConvergenceMinRef": "1e-06W",
        "Initial Temperature": "AmbientTemp",
        "Start Time": "0s",
        "Stop Time": "20s",
        "Time Step": "1s",
        "SaveFieldsType": "None",
    }
)

MechModal = dict(
    {
        "Enabled": True,
        "MeshLink": meshlink,
        "Max Modes": 6,
        "Limit Search": True,
        "Range Max": "100MHz",
        "Range Min": "0Hz",
        "Solver": "Program Controlled",
    }
)
"""Mechanical modal setup properties and default values."""

MechStructural = dict(
    {
        "Enabled": True,
        "MeshLink": meshlink,
        "Solver": "Program Controlled",
        "Stepping": "Program Controlled",
    }
)
"""Mechanical structural setup properties and default values."""

# TODO complete the list of templates for other Solvers

RmxprtDefault = dict(
    {
        "Enabled": True,
        "OperationType": "Motor",
        "LoadType": "ConstPower",
        "RatedOutputPower": "1kW",
        "RatedVoltage": "100V",
        "RatedSpeed": "1000rpm",
        "OperatingTemperature": "75cel",
    }
)
"""RMxprt Default setup properties and default values."""

GRM = copy.deepcopy(RmxprtDefault)
"""RMxprt GRM Generic Rotating Machine setup properties and default values."""

GRM["RatedPowerFactor"] = "0.8"
GRM["Frequency"] = "60Hz"
GRM["CapacitivePowerFactor"] = False

DFIG = dict(
    {
        "Enabled": True,
        "RatedOutputPower": "1kW",
        "RatedVoltage": "100V",
        "RatedSpeed": "1000rpm",
        "OperatingTemperature": "75cel",
        "OperationType": "Wind Generator",
        "LoadType": "InfiniteBus",
        "RatedPowerFactor": "0.8",
        "Frequency": "60Hz",
        "CapacitivePowerFactor": False,
    }
)
"""RMxprt DFIG Doubly-fed induction generator setup properties."""

TPIM = copy.deepcopy(RmxprtDefault)
TPIM["Frequency"] = "60Hz"
TPIM["WindingConnection"] = 0

"""RMxprt TPIM Three-Phase Induction Machine setup properties."""
SPIM = copy.deepcopy(RmxprtDefault)
SPIM["Frequency"] = "60Hz"

"""RMxprt SPIM Single-Phase Induction Machine setup properties."""

TPSM = dict(
    {
        "Enabled": True,
        "RatedOutputPower": "100",
        "RatedVoltage": "100V",
        "RatedSpeed": "1000rpm",
        "OperatingTemperature": "75cel",
        "OperationType": "Generator",
        "LoadType": "InfiniteBus",
        "RatedPowerFactor": 0.8,
        "WindingConnection": False,
        "ExciterEfficiency": 90,
        "StartingFieldResistance": "0ohm",
        "InputExcitingCurrent": False,
        "ExcitingCurrent": "0A",
    }
)
"""RMxprt TPSM=SYNM Three-phase Synchronous Machine/Generator setup properties."""

NSSM = TPSM  # Non-salient Synchronous Machine defaults: same as salient synch mach

ASSM = BLDC = PMDC = SRM = RmxprtDefault
# --- ALL USING RMxprt DEFAULT VALUES --- #
# ASSM = Adjustable-speed Synchronous Machine
# BLDC = Brushless DC Machine
# PMDC = Permanent Magnet DC Machine
# SRM = Switched Reluctance Machine
LSSM = copy.deepcopy(RmxprtDefault)
LSSM["WindingConnection"] = False

"""RMxprt LSSM Line-start Synchronous Machine setup properties."""
UNIM = copy.deepcopy(RmxprtDefault)
UNIM["Frequency"] = "60Hz"

"""RMxprt UNIM Universal Machine setup properties."""

DCM = dict(
    {
        "Enabled": True,
        "RatedOutputPower": "1kW",
        "RatedVoltage": "100V",
        "RatedSpeed": "1000rpm",
        "OperatingTemperature": "75cel",
        "OperationType": "Generator",
        "LoadType": "InfiniteBus",
        "FieldExcitingType": False,
        "DeterminedbyRatedSpeed": False,
        "ExcitingVoltage": "100V",
        "SeriesResistance": "1ohm",
    }
)
"""RMxprt DCM DC Machine/Generator setup properties."""

CPSM = dict(
    {
        "Enabled": True,
        "RatedOutputPower": "100",
        "RatedVoltage": "100V",
        "RatedSpeed": "1000rpm",
        "OperatingTemperature": "75cel",
        "OperationType": "Generator",
        "LoadType": "InfiniteBus",
        "RatedPowerFactor": "0.8",
        "InputExcitingCurrent": False,
        "ExcitingCurrent": "0A",
    }
)
"""RMxprt CPSM Claw-pole synchronous machine/generator setup properties."""

TR = {}

# Default sweep settings for Q3D
SweepQ3D = dict(
    {
        "IsEnabled": True,
        "RangeType": "LinearStep",
        "RangeStart": "1GHz",
        "RangeEnd": "10GHz",
        "Type": "Discrete",
        "SaveFields": False,
        "SaveRadFields": False,
    }
)

SweepHfss3D = dict(
    {
        "Type": "Interpolating",
        "IsEnabled": True,
        "RangeType": "LinearCount",
        "RangeStart": "2.5GHz",
        "RangeEnd": "7.5GHz",
        "SaveSingleField": False,
        "RangeCount": 401,
        "RangeStep": "1MHz",
        "RangeSamples": 11,
        "SaveFields": True,
        "SaveRadFields": True,
        "GenerateFieldsForAllFreqs": False,
        "InterpTolerance": 0.5,
        "InterpMaxSolns": 250,
        "InterpMinSolns": 0,
        "InterpMinSubranges": 1,
        "InterpUseS": True,
        "InterpUsePortImped": False,
        "InterpUsePropConst": True,
        "UseDerivativeConvergence": False,
        "InterpDerivTolerance": 0.2,
        "EnforcePassivity": True,
        "UseFullBasis": True,
        "PassivityErrorTolerance": 0.0001,
        "EnforceCausality": False,
        "UseQ3DForDCSolve": False,
        "SMatrixOnlySolveMode": "Auto",
        "SMatrixOnlySolveAbove": "1MHz",
    }
)

enabled = dict({"Enable": "true"})

Sweep3DLayout = dict(
    {
        "Properties": enabled,
        "Sweeps": SweepDefinition,
        "GenerateSurfaceCurrent": False,
        "SaveRadFieldsOnly": False,
        "ZoSelected": False,
        "SAbsError": 0.005,
        "ZoPercentError": 1,
        "GenerateStateSpace": False,
        "EnforcePassivity": True,
        "PassivityTolerance": 0.0001,
        "UseQ3DForDC": False,
        "ResimulateDC": False,
        "MaxSolutions": 250,
        "InterpUseSMatrix": True,
        "InterpUsePortImpedance": True,
        "InterpUsePropConst": True,
        "InterpUseFullBasis": True,
        "AdvDCExtrapolation": False,
        "MinSolvedFreq": "0.01GHz",
        "AutoSMatOnlySolve": True,
        "MinFreqSMatrixOnlySolve": "1MHz",
        "CustomFrequencyString": "",
        "AllEntries": False,
        "AllDiagEntries": False,
        "AllOffDiagEntries": False,
        "MagMinThreshold": 0.01,
        "FreqSweepType": "kInterpolating",
    }
)

SweepSiwave = dict(
    {
        "Properties": enabled,
        "Sweeps": SweepDefinition,
        "Enabled": True,
        "FreqSweepType": "kInterpolating",
        "IsDiscrete": False,
        "UseQ3DForDC": False,
        "SaveFields": False,
        "SaveRadFieldsOnly": False,
        "RelativeSError": 0.005,
        "EnforceCausality": False,
        "EnforcePassivity": True,
        "PassivityTolerance": 0.0001,
        "ComputeDCPoint": False,
        "SIwaveWith3DDDM": False,
        "UseHFSSSolverRegions": False,
        "UseHFSSSolverRegionSchGen": False,
        "UseHFSSSolverRegionParallelSolve": False,
        "NumParallelHFSSRegions": 1,
        "HFSSSolverRegionsSetupName": "<default>",
        "HFSSSolverRegionsSweepName": "<default>",
        "AutoSMatOnlySolve": True,
        "MinFreqSMatOnlySolve": "1MHz",
        "MaxSolutions": 250,
        "InterpUseSMatrix": True,
        "InterpUsePortImpedance": True,
        "InterpUsePropConst": True,
        "InterpUseFullBasis": True,
        "FastSweep": False,
        "AdaptiveSampling": False,
        "EnforceDCAndCausality": False,
        "AdvDCExtrapolation": False,
        "MinSolvedFreq": "0.01GHz",
        "MatrixConvEntryList": {},
        "HFSSRegionsParallelSimConfig": {},
    }
)

icepak_newkeys_241 = {
    "GPU Convergence Criteria - Flow": "0.001",
    "GPU Convergence Criteria - Energy": "1e-05",
    "GPU Convergence Criteria - Turbulent Kinetic Energy": "0.001",
    "GPU Convergence Criteria - Turbulent Dissipation Rate": "0.001",
    "GPU Convergence Criteria - Specific Dissipation Rate": "0.001",
    "GPU Convergence Criteria - Discrete Ordinates": "1e-05",
    "GPU Convergence Criteria - Joule Heating": "1e-07",
    "Solution Initialization - Use Model Based Flow Initialization": False,
    "Include Solar": False,
    "Solar Radiation Model": "Solar Radiation Calculator",
    "Solar Enable Participating Solids": False,
    "Solar Radiation - Scattering Fraction": "0",
    "Solar Radiation - North X": "0",
    "Solar Radiation - North Y": "0",
    "Solar Radiation - North Z": "1",
    "Solar Radiation - Day": 1,
    "Solar Radiation - Month": 1,
    "Solar Radiation - Hours": 0,
    "Solar Radiation - Minutes": 0,
    "Solar Radiation - GMT": "0",
    "Solar Radiation - Latitude": "0",
    "Solar Radiation - Latitude Direction": "North",
    "Solar Radiation - Longitude": "0",
    "Solar Radiation - Longitude Direction": "East",
    "Solar Radiation - Ground Reflectance": "0",
    "Solar Radiation - Sunshine Fraction": "0",
    "Linear Solver Type - Joule Heating": "F",
    "Linear Solver Termination Criterion - Joule Heating": "1e-09",
    "Linear Solver Residual Reduction Tolerance - Joule Heating": "1e-09",
    "Maximum Cycles": "30",
    "Linear Solver Stabilization - Joule Heating": "None",
    "Coupled pressure-velocity formulation": False,
    "2D Profile Interpolation Method": "Inverse Distance Weighted",
    "TEC Coupling": False,
}

SteadyTemperatureOnly_241 = copy.deepcopy(SteadyTemperatureOnly)
SteadyFlowOnly_241 = copy.deepcopy(SteadyFlowOnly)
SteadyTemperatureAndFlow_241 = copy.deepcopy(SteadyTemperatureAndFlow)
TransientTemperatureOnly_241 = copy.deepcopy(TransientTemperatureOnly)
TransientTemperatureAndFlow_241 = copy.deepcopy(TransientTemperatureAndFlow)
TransientFlowOnly_241 = copy.deepcopy(TransientFlowOnly)
SteadyTemperatureOnly_241.update(icepak_newkeys_241)
SteadyFlowOnly_241.update(icepak_newkeys_241)
SteadyTemperatureAndFlow_241.update(icepak_newkeys_241)
TransientTemperatureOnly_241.update(icepak_newkeys_241)
TransientTemperatureAndFlow_241.update(icepak_newkeys_241)
TransientFlowOnly_241.update(icepak_newkeys_241)

list_modules = dir()

icepak_forced_convection_update = {
    "Convergence Criteria - Energy": "1e-12",
    "Linear Solver Termination Criterion - Temperature": "1e-06",
    "Linear Solver Residual Reduction Tolerance - Temperature": "1e-06",
    "Sequential Solve of Flow and Energy Equations": True,
}

icepak_natural_convection_update = {
    "Include Gravity": True,
    "Solution Initialization - Z Velocity": "0.000980665m_per_sec",
    "IsEnabled": True,
    "Radiation Model": "Discrete Ordinates Model",
    "Flow Iteration Per Radiation Iteration": "10",
    "Time Step Interval": "1",
    "ThetaDivision": "2",
    "PhiDivision": "2",
    "ThetaPixels": "2",
    "Under-relaxation - Pressure": "0.7",
    "Under-relaxation - Momentum": "0.3",
    "Linear Solver Termination Criterion - Temperature": "1e-06",
    "Linear Solver Residual Reduction Tolerance - Temperature": "1e-06",
}


class SetupKeys:
    """Provides setup keys."""

    SetupNames = [
        "HFSSDrivenAuto",
        "HFSSDriven",
        "HFSSEigen",
        "HFSSTransient",
        "HFSSDriven",
        "Transient",
        "Magnetostatic",
        "EddyCurrent",
        "Electrostatic",
        "ElectroDCConduction",
        "ElectricTransient",
        "IcepakSteadyState",
        "IcepakSteadyState",
        "IcepakSteadyState",
        "Matrix",
        "NexximLNA",
        "NexximDC",
        "NexximTransient",
        "NexximQuickEye",
        "NexximVerifEye",
        "NexximAMI",
        "NexximOscillatorRSF",
        "NexximOscillator1T",
        "NexximOscillatorNT",
        "NexximHarmonicBalance1T",
        "NexximHarmonicBalanceNT",
        "NexximSystem",
        "NexximTVNoise",
        "HSPICE",
        "HFSS3DLayout",
        "2DMatrix",
        "2DMatrix",
        "MechThermal",
        "MechModal",
        "GRM",
        "TR",
        "IcepakTransient",
        "IcepakTransient",
        "IcepakTransient",
        "MechStructural",
        "SiwaveDC3DLayout",
        "SiwaveAC3DLayout",
        "LNA3DLayout",
        "GRM",  # DFIG
        "TPIM",
        "SPIM",
        "SYNM",  # TPSM/SYNM
        "BLDC",
        "ASSM",
        "PMDC",
        "SRM",
        "LSSM",
        "UNIM",
        "DCM",
        "CPSM",
        "NSSM",
        "TransientAPhiFormulation",
        "MechTransientThermal",
        "DCConduction",
        "ACConduction",
        "DCBiasedEddyCurrent",
    ]

    SetupTemplates = {
        0: HFSSDrivenAuto,
        1: HFSSDrivenDefault,
        2: HFSSEigen,
        3: HFSSTransient,
        4: HFSSSBR,
        5: MaxwellTransient,
        6: Magnetostatic,
        7: EddyCurrent,
        8: Electrostatic,
        9: ElectroDCConduction,
        10: ElectricTransient,
        11: SteadyTemperatureAndFlow,
        12: SteadyTemperatureOnly,
        13: SteadyFlowOnly,
        14: Matrix,
        15: NexximLNA,
        16: NexximDC,
        17: NexximTransient,
        18: NexximQuickEye,
        19: NexximVerifEye,
        20: NexximAMI,
        21: NexximOscillatorRSF,
        22: NexximOscillator1T,
        23: NexximOscillatorNT,
        24: NexximHarmonicBalance1T,
        25: NexximHarmonicBalanceNT,
        26: NexximSystem,
        27: NexximTVNoise,
        28: HSPICE,
        29: HFSS3DLayout,
        30: Open,
        31: Close,
        32: MechTerm,
        33: MechModal,
        34: GRM,
        35: TR,
        36: TransientTemperatureAndFlow,
        37: TransientTemperatureOnly,
        38: TransientFlowOnly,
        39: MechStructural,
        40: SiwaveDC3DLayout,
        41: SiwaveAC3DLayout,
        42: LNA3DLayout,
        43: DFIG,
        44: TPIM,
        45: SPIM,
        46: TPSM,
        47: BLDC,
        48: ASSM,
        49: PMDC,
        50: SRM,
        51: LSSM,
        52: UNIM,
        53: DCM,
        54: CPSM,
        55: NSSM,
        56: MaxwellTransient,
        57: MechTransientThermal,
        58: DCConduction,
        59: ACConduction,
    }

    SetupTemplates_231 = {
        29: HFSS3DLayout_v231,
    }
    SetupTemplates_232 = {}

    SetupTemplates_241 = {
        11: SteadyTemperatureAndFlow_241,
        12: SteadyTemperatureOnly_241,
        13: SteadyFlowOnly_241,
        36: TransientTemperatureAndFlow_241,
        37: TransientTemperatureOnly_241,
        38: TransientFlowOnly_241,
    }
    SetupTemplates_251 = {
        60: DCBiasedEddyCurrent,
    }

    @staticmethod
    def _add_to_template(template_in, template_to_append):
        template_out = template_in.copy()
        for k, v in template_to_append.items():
            template_out[k] = v
        return template_out

    @staticmethod
    def get_setup_templates():
        from ansys.aedt.core.generic.general_methods import settings

        template = SetupKeys.SetupTemplates
        if settings.aedt_version is not None:
            if settings.aedt_version >= "2023.1":
                template = SetupKeys._add_to_template(SetupKeys.SetupTemplates, SetupKeys.SetupTemplates_231)
            if settings.aedt_version >= "2023.2":
                template = SetupKeys._add_to_template(template, SetupKeys.SetupTemplates_232)
            if settings.aedt_version >= "2024.1":
                template = SetupKeys._add_to_template(template, SetupKeys.SetupTemplates_241)
            if settings.aedt_version >= "2025.1":
                template = SetupKeys._add_to_template(template, SetupKeys.SetupTemplates_251)
        return template

    def get_default_icepak_template(self, default_type):
        """
        Update the setup based on the class arguments or a dictionary.

        Parameters
        ----------
        default_type : str
            Which default template to use. Available options are ``"Default"``,
            ``"Forced Convection"``, ``"Mixed Convection"``
            and ``"Natural Convection"``.

        Returns
        -------
        dict
            Dictionary containing the Icepak default setup for the chosen simulation type.


        """
        icepak_setups_n = [11, 12, 13, 36, 37, 38]
        template = self.get_setup_templates()
        icepak_template = {self.SetupNames[i]: template[i] for i in icepak_setups_n}
        if default_type == "Default":
            return icepak_template
        elif default_type == "Forced Convection":
            expand_dict = icepak_forced_convection_update
        elif default_type == "Natural Convection" or default_type == "Mixed Convection":
            expand_dict = icepak_natural_convection_update
        else:
            raise AttributeError(f"default_type {default_type} is not supported.")
        for i in icepak_setups_n:
            icepak_template[self.SetupNames[i]].update(expand_dict)
        return icepak_template
