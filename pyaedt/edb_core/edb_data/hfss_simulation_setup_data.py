from pyaedt.edb_core.general import convert_py_list_to_net_list
from pyaedt.generic.clr_module import Tuple
from pyaedt.generic.general_methods import generate_unique_name
from pyaedt.generic.general_methods import pyaedt_function_handler


class EdbFrequencySweep(object):
    """Manages EDB methods for frequency sweep."""

    def __init__(self, sim_setup, frequency_sweep=None, name=None, edb_sweep_data=None):

        self._sim_setup = sim_setup

        if edb_sweep_data:
            self._edb_sweep_data = edb_sweep_data
            self._name = self._edb_sweep_data.Name
        else:
            if not name:
                self._name = generate_unique_name("sweep")
            else:
                self._name = name
            self._edb_sweep_data = self._sim_setup._edb.simsetupdata.SweepData(self._name)
            self.set_frequencies(frequency_sweep)

    @pyaedt_function_handler()
    def _update_sweep(self):
        """Update sweep."""
        self._sim_setup._edb_sim_setup_info.SweepDataList.Clear()
        for el in list(self._sim_setup.frequency_sweeps.values()):
            self._sim_setup._edb_sim_setup_info.SweepDataList.Add(el._edb_sweep_data)
        self._sim_setup._edb_sim_setup_info.SweepDataList.Add(self._edb_sweep_data)
        return self._sim_setup._update_setup()

    @property
    def name(self):
        """Name of the sweep."""
        return self._edb_sweep_data.Name

    @name.setter
    def name(self, value):
        """Set name of this sweep"""
        self._edb_sweep_data.Name = value
        self._update_sweep()

    @property
    def sweep_type(self):
        """Sweep type."""
        return

    @property
    def frequencies(self):
        """List of frequencies points."""
        return list(self._edb_sweep_data.Frequencies)

    @property
    def adaptive_sampling(self):
        """Whether adaptive sampling is used.

        Returns
        -------
        bool
            ``True`` if adaptive sampling is used, ``False`` otherwise.
        """
        return self._edb_sweep_data.AdaptiveSampling

    @property
    def adv_dc_extrapolation(self):
        """Whether to turn on advanced DC Extrapolation.

        Returns
        -------
        bool
            ``True`` if advanced DC Extrapolation is used, ``False`` otherwise.

        """
        return self._edb_sweep_data.AdvDCExtrapolation

    @property
    def auto_s_mat_only_solve(self):
        """Whether to turn on Auto/Manual SMatrix only solve.

        Returns
        -------
        bool
            ``True`` if Auto/Manual SMatrix only solve is used, ``False`` otherwise.
        """
        return self._edb_sweep_data.AutoSMatOnlySolve

    @property
    def enforce_causality(self):
        """Whether to enforce causality during interpolating sweep.

        Returns
        -------
        bool
            ``True`` if enforce causality is used, ``False`` otherwise.
        """
        return self._edb_sweep_data.EnforceCausality

    @property
    def enforce_dc_and_causality(self):
        """Whether to enforce DC point and causality.

        Returns
        -------
        bool
            ``True`` if enforce dc point and causality is used, ``False`` otherwise.

        """
        return self._edb_sweep_data.EnforceDCAndCausality

    @property
    def enforce_passivity(self):
        """Whether to enforce passivity during interpolating sweep.

        Returns
        -------
        bool
            ``True`` if enforce passivity is used, ``False`` otherwise.
        """
        return self._edb_sweep_data.EnforcePassivity

    @property
    def freq_sweep_type(self):
        """Sweep type.
        Options are:
        - ``kInterpolatingSweep``.
        - ``kDiscreteSweep``.
        - ``kBroadbandFastSweep``.

        Returns
        -------
        str
        """
        return self._edb_sweep_data.FreqSweepType.ToString()

    @property
    def interp_use_full_basis(self):
        """Whether to use Full basis elements.

        Returns
        -------
        bool
            ``True`` if full basis interpolation is used, ``False`` otherwise.
        """
        return self._edb_sweep_data.InterpUseFullBasis

    @property
    def interp_use_port_impedance(self):
        """Whether to turn on the port impedance interpolation.

        Returns
        -------
        bool
            ``True`` if port impedance is used, ``False`` otherwise.
        """
        return self._edb_sweep_data.InterpUsePortImpedance

    @property
    def interp_use_prop_const(self):
        """Whether to use propagation constants.

        Returns
        -------
        bool
            ``True`` if propagation constants are used, ``False`` otherwise.
        """
        return self._edb_sweep_data.InterpUsePropConst

    @property
    def interp_use_s_matrix(self):
        """Whether to use S matrix.

        Returns
        -------
        bool
            ``True`` if S matrix are used, ``False`` otherwise.
        """
        return self._edb_sweep_data.InterpUseSMatrix

    @property
    def max_solutions(self):
        """Number of aximum solutions.

        Returns
        -------
        int
        """
        return self._edb_sweep_data.MaxSolutions

    @property
    def min_freq_s_mat_only_solve(self):
        """Minimum frequency SMatrix only solve.

        Returns
        -------
        str
            Frequency with units.
        """
        return self._edb_sweep_data.MinFreqSMatOnlySolve

    @property
    def min_solved_freq(self):
        """Minimum solved frequency.

        Returns
        -------
        str
            Frequency with units.
        """
        return self._edb_sweep_data.MinSolvedFreq

    @property
    def passivity_tolerance(self):
        """Tolerance for passivity enforcement.

        Returns
        -------
        float
        """
        return self._edb_sweep_data.PassivityTolerance

    @property
    def relative_s_error(self):
        """Specify S-parameter error tolerance for interpolating sweep.

        Returns
        -------
        float
        """
        return self._edb_sweep_data.RelativeSError

    @property
    def save_fields(self):
        """Whether to turn on or off the extraction of surface current data.

        Returns
        -------
        bool
            ``True`` if save fields is enabled, ``False`` otherwise.
        """
        return self._edb_sweep_data.SaveFields

    @property
    def save_rad_fields_only(self):
        """Whether to turn on save radiated fields only.

        Returns
        -------
        bool
            ``True`` if save radiated field only is used, ``False`` otherwise.

        """
        return self._edb_sweep_data.SaveRadFieldsOnly

    @property
    def use_q3d_for_dc(self):
        """Whether to enable Q3D solver for DC point extraction .

        Returns
        -------
        bool
            ``True`` if Q3d for DC point is used, ``False`` otherwise.
        """
        return self._edb_sweep_data.UseQ3DForDC

    @adaptive_sampling.setter
    def adaptive_sampling(self, value):
        self._edb_sweep_data.AdaptiveSampling = value
        self._update_sweep()

    @adv_dc_extrapolation.setter
    def adv_dc_extrapolation(self, value):
        self._edb_sweep_data.AdvDCExtrapolation = value
        self._update_sweep()

    @auto_s_mat_only_solve.setter
    def auto_s_mat_only_solve(self, value):
        self._edb_sweep_data.AutoSMatOnlySolve = value
        self._update_sweep()

    @enforce_causality.setter
    def enforce_causality(self, value):
        self._edb_sweep_data.EnforceCausality = value
        self._update_sweep()

    @enforce_dc_and_causality.setter
    def enforce_dc_and_causality(self, value):
        self._edb_sweep_data.EnforceDCAndCausality = value
        self._update_sweep()

    @enforce_passivity.setter
    def enforce_passivity(self, value):
        self._edb_sweep_data.EnforcePassivity = value
        self._update_sweep()

    @freq_sweep_type.setter
    def freq_sweep_type(self, value):
        edb_freq_sweep_type = self._edb_sweep_data.TFreqSweepType
        if value in [0, "kInterpolatingSweep"]:
            self._edb_sweep_data.FreqSweepType = edb_freq_sweep_type.kInterpolatingSweep
        elif value in [1, "kDiscreteSweep"]:
            self._edb_sweep_data.FreqSweepType = edb_freq_sweep_type.kDiscreteSweep
        elif value in [2, "kBroadbandFastSweep"]:
            self._edb_sweep_data.FreqSweepType = edb_freq_sweep_type.kBroadbandFastSweep
        elif value in [3, "kNumSweepTypes"]:
            self._edb_sweep_data.FreqSweepType = edb_freq_sweep_type.kNumSweepTypes
        self._edb_sweep_data.FreqSweepType.ToString()

    @interp_use_full_basis.setter
    def interp_use_full_basis(self, value):
        self._edb_sweep_data.InterpUseFullBasis = value
        self._update_sweep()

    @interp_use_port_impedance.setter
    def interp_use_port_impedance(self, value):
        self._edb_sweep_data.InterpUsePortImpedance = value
        self._update_sweep()

    @interp_use_prop_const.setter
    def interp_use_prop_const(self, value):
        self._edb_sweep_data.InterpUsePropConst = value
        self._update_sweep()

    @interp_use_s_matrix.setter
    def interp_use_s_matrix(self, value):
        self._edb_sweep_data.InterpUseSMatrix = value
        self._update_sweep()

    @max_solutions.setter
    def max_solutions(self, value):
        self._edb_sweep_data.MaxSolutions = value
        self._update_sweep()

    @min_freq_s_mat_only_solve.setter
    def min_freq_s_mat_only_solve(self, value):
        self._edb_sweep_data.MinFreqSMatOnlySolve = value
        self._update_sweep()

    @min_solved_freq.setter
    def min_solved_freq(self, value):
        self._edb_sweep_data.MinSolvedFreq = value
        self._update_sweep()

    @passivity_tolerance.setter
    def passivity_tolerance(self, value):
        self._edb_sweep_data.PassivityTolerance = value
        self._update_sweep()

    @relative_s_error.setter
    def relative_s_error(self, value):
        self._edb_sweep_data.RelativeSError = value
        self._update_sweep()

    @save_fields.setter
    def save_fields(self, value):
        self._edb_sweep_data.SaveFields = value
        self._update_sweep()

    @save_rad_fields_only.setter
    def save_rad_fields_only(self, value):
        self._edb_sweep_data.SaveRadFieldsOnly = value
        self._update_sweep()

    @use_q3d_for_dc.setter
    def use_q3d_for_dc(self, value):
        self._edb_sweep_data.UseQ3DForDC = value
        self._update_sweep()

    @pyaedt_function_handler()
    def _set_frequencies(self, freq_sweep_string="Linear Step: 0GHz to 20GHz, step=0.05GHz"):
        self._edb_sweep_data.SetFrequencies(freq_sweep_string)
        self._update_sweep()

    @pyaedt_function_handler()
    def set_frequencies_linear_scale(self, start="0.1GHz", stop="20GHz", step="50MHz"):
        """Set a linear scale frequency sweep.

        Parameters
        ----------
        start : str, float
            Start frequency.
        stop : str, float
            Stop frequency.
        step : str, float
            Step frequency.

        Returns
        -------
        bool
            ``True`` if correctly executed, ``False`` otherwise.

        """
        self._edb_sweep_data.Frequencies = self._edb_sweep_data.SetFrequencies(start, stop, step)
        return self._update_sweep()

    @pyaedt_function_handler()
    def set_frequencies_linear_count(self, start="1kHz", stop="0.1GHz", count=10):
        """Set a linear count frequency sweep.

        Parameters
        ----------
        start : str, float
            Start frequency.
        stop : str, float
            Stop frequency.
        count : int
            Step frequency.

        Returns
        -------
        bool
            ``True`` if correctly executed, ``False`` otherwise.

        """
        start = self._sim_setup._edb.arg_to_dim(start, "Hz")
        stop = self._sim_setup._edb.arg_to_dim(stop, "Hz")
        self._edb_sweep_data.Frequencies = self._edb_sweep_data.SetFrequencies(start, stop, count)
        return self._update_sweep()

    @pyaedt_function_handler()
    def set_frequencies_log_scale(self, start="1kHz", stop="0.1GHz", samples=10):
        """Set a log count frequency sweep.

        Parameters
        ----------
        start : str, float
            Start frequency.
        stop : str, float
            Stop frequency.
        samples : int
            Step frequency.

        Returns
        -------
        bool
            ``True`` if correctly executed, ``False`` otherwise.
        """
        start = self._sim_setup._edb.arg_to_dim(start, "Hz")
        stop = self._sim_setup._edb.arg_to_dim(stop, "Hz")
        self._edb_sweep_data.Frequencies = self._edb_sweep_data.SetLogFrequencies(start, stop, samples)
        return self._update_sweep()

    @pyaedt_function_handler()
    def set_frequencies(self, frequency_list=None):
        """Set frequency list to the sweep frequencies.

        Parameters
        ----------
        frequency_list : list, optional
            List of lists with four elements. Each list must contain:

              1- frequency type (``"linear count"``, ``"log scale"`` or ``"linear scale"``)
              2- start frequency
              3- stop frequency
              4- step frequency or count

        Returns
        -------
        bool
            ``True`` if correctly executed, ``False`` otherwise.

        """
        if not frequency_list:
            frequency_list = [
                ["linear count", "0", "1kHz", 1],
                ["log scale", "1kHz", "0.1GHz", 10],
                ["linear scale", "0.1GHz", "10GHz", "0.1GHz"],
            ]
        temp = []
        for i in frequency_list:
            if i[0] == "linear count":
                temp.extend(list(self._edb_sweep_data.SetFrequencies(i[1], i[2], i[3])))
            elif i[0] == "linear scale":
                temp.extend(list(self._edb_sweep_data.SetFrequencies(i[1], i[2], i[3])))
            elif i[0] == "log scale":
                temp.extend(list(self._edb_sweep_data.SetLogFrequencies(i[1], i[2], i[3])))
            else:
                return False
        for i in temp:
            self._edb_sweep_data.Frequencies.Add(i)
        return self._update_sweep()


class MeshOperation(object):
    """Mesh Operation Class."""

    def __init__(self, parent, mesh_operation):
        self._parent = parent
        self.mesh_operation = mesh_operation
        self._mesh_op_mapping = {
            "kMeshSetupBase": mesh_operation.TMeshOpType.kMeshSetupBase,
            "kMeshSetupLength": mesh_operation.TMeshOpType.kMeshSetupLength,
            "kMeshSetupSkinDepth": mesh_operation.TMeshOpType.kMeshSetupSkinDepth,
            "kNumMeshOpTypes": mesh_operation.TMeshOpType.kNumMeshOpTypes,
        }

    @property
    def enabled(self):
        """Whether if mesh operation is enabled.

        Returns
        -------
        bool
            ``True`` if mesh operation is used, ``False`` otherwise.
        """
        return self.mesh_operation.Enabled

    @property
    def mesh_operation_type(self):
        """Mesh operation type.
        Options:
        0- ``kMeshSetupBase``
        1- ``kMeshSetupLength``
        2- ``kMeshSetupSkinDepth``
        3- ``kNumMeshOpTypes``.

        Returns
        -------
        int
        """
        return self.mesh_operation.MeshOpType.ToString()

    @property
    def mesh_region(self):
        """Mesh region name.

        Returns
        -------
        str
            Name of the mesh region.
        """
        return self.mesh_operation.MeshRegion

    @property
    def name(self):
        """Mesh operation name.

        Returns
        -------
        str
        """
        return self.mesh_operation.Name

    @property
    def nets_layers_list(self):
        """List of nets and layers.

        Returns
        -------
        list
           List of lists with three elements. Each list must contain:
           1- net name
           2- layer name
           3- bool.
           Third element is represents whether if the mesh operation is enabled or disabled.

        """
        return self.mesh_operation.NetsLayersList

    @nets_layers_list.setter
    def nets_layers_list(self, values):
        temp = []
        for net, layers in values.items():
            for layer in layers:
                temp.append(Tuple[str, str, bool](net, layer, True))
        self.mesh_operation.NetsLayersList = convert_py_list_to_net_list(temp)

    @property
    def refine_inside(self):
        """Whether to turn on refine inside objects.

        Returns
        -------
        bool
            ``True`` if refine inside objects is used, ``False`` otherwise.

        """
        return self.mesh_operation.RefineInside

    @enabled.setter
    def enabled(self, value):
        self.mesh_operation.Enabled = value
        self._parent._update_setup()

    @mesh_region.setter
    def mesh_region(self, value):
        self.mesh_operation.MeshRegion = value
        self._parent._update_setup()

    @name.setter
    def name(self, value):
        self.mesh_operation.Name = value
        self._parent._update_setup()

    @refine_inside.setter
    def refine_inside(self, value):
        self.mesh_operation.RefineInside = value
        self._parent._update_setup()

    @property
    def max_elements(self):
        """Maximum number of elements.

        Returns
        -------
        str
        """
        return self.mesh_operation.MaxElems

    @property
    def restrict_max_elements(self):
        """Whether to restrict maximum number  of elements.

        Returns
        -------
        bool
        """
        return self.mesh_operation.RestrictMaxElem

    @max_elements.setter
    def max_elements(self, value):
        self.mesh_operation.MaxElems = str(value)
        self._parent._update_setup()

    @restrict_max_elements.setter
    def restrict_max_elements(self, value):
        """Whether to restrict maximum number  of elements.

        Returns
        -------
        bool
        """
        self.mesh_operation.RestrictMaxElem = value
        self._parent._update_setup()


class MeshOperationLength(MeshOperation, object):
    """Mesh operation Length class.
    This class is accessible from Hfss Setup in EDB and add_length_mesh_operation method.

    Examples
    --------
    >>> mop = edbapp.setups["setup1a"].add_length_mesh_operation({"GND": ["TOP", "BOTTOM"]})
    >>> mop.max_elements = 3000
    """

    def __init__(self, parent, mesh_operation):
        MeshOperation.__init__(self, parent, mesh_operation)

    @property
    def max_length(self):
        """Maximum length of elements.

        Returns
        -------
        str
        """
        return self.mesh_operation.MaxLength

    @property
    def restrict_length(self):
        """Whether to restrict length of elements.

        Returns
        -------
        bool
        """
        return self.mesh_operation.RestrictLength

    @max_length.setter
    def max_length(self, value):
        self.mesh_operation.MaxLength = value
        self._parent._update_setup()

    @restrict_length.setter
    def restrict_length(self, value):
        """Whether to restrict length of elements.

        Returns
        -------
        bool
        """
        self.mesh_operation.RestrictLength = value
        self._parent._update_setup()


class MeshOperationSkinDepth(MeshOperation, object):
    """Mesh operation Skin Depth class.
    This class is accessible from Hfss Setup in EDB and assign_skin_depth_mesh_operation method.

    Examples
    --------
    >>> mop = edbapp.setups["setup1a"].add_skin_depth_mesh_operation({"GND": ["TOP", "BOTTOM"]})
    >>> mop.max_elements = 3000
    """

    def __init__(self, parent, mesh_operation):
        MeshOperation.__init__(self, parent, mesh_operation)

    @property
    def skin_depth(self):
        """Skin depth value.

        Returns
        -------
        str
        """
        return self.mesh_operation.SkinDepth

    @skin_depth.setter
    def skin_depth(self, value):
        self.mesh_operation.SkinDepth = value
        self._parent._update_setup()

    @property
    def surface_triangle_length(self):
        """Surface triangle length value.

        Returns
        -------
        str
        """
        return self.mesh_operation.SurfTriLength

    @surface_triangle_length.setter
    def surface_triangle_length(self, value):
        self.mesh_operation.SurfTriLength = value
        self._parent._update_setup()

    @property
    def number_of_layer_elements(self):
        """Number of layer elements.

        Returns
        -------
        str
        """
        return self.mesh_operation.NumLayers

    @number_of_layer_elements.setter
    def number_of_layer_elements(self, value):
        self.mesh_operation.NumLayers = str(value)
        self._parent._update_setup()


class HfssPortSettings(object):
    """Manages EDB methods for HFSS port settings."""

    def __init__(self, parent):
        self._parent = parent

    @property
    def _hfss_port_settings(self):
        return self._parent._edb_sim_setup_info.SimulationSettings.HFSSPortSettings

    @property
    def max_delta_z0(self):
        """Maximum change to Z0 in successive passes.

        Returns
        -------
        float
        """
        return self._hfss_port_settings.MaxDeltaZ0

    @max_delta_z0.setter
    def max_delta_z0(self, value):
        self._hfss_port_settings.MaxDeltaZ0 = value
        self._parent._update_setup()

    @property
    def max_triangles_wave_port(self):
        """Maximum number of triangles allowed for wave ports.

        Returns
        -------
        int
        """
        return self._hfss_port_settings.MaxTrianglesWavePort

    @max_triangles_wave_port.setter
    def max_triangles_wave_port(self, value):
        self._hfss_port_settings.MaxTrianglesWavePort = value
        self._parent._update_setup()

    @property
    def min_triangles_wave_port(self):
        """Minimum number of triangles allowed for wave ports.

        Returns
        -------
        int
        """
        return self._hfss_port_settings.MinTrianglesWavePort

    @min_triangles_wave_port.setter
    def min_triangles_wave_port(self, value):
        self._hfss_port_settings.MinTrianglesWavePort = value
        self._parent._update_setup()

    @property
    def enable_set_triangles_wave_port(self):
        """Whether to enable setting of minimum and maximum mesh limits for wave ports.

        Returns
        -------
        bool
            ``True`` if triangles wave port  is used, ``False`` otherwise.
        """
        return self._hfss_port_settings.SetTrianglesWavePort

    @enable_set_triangles_wave_port.setter
    def enable_set_triangles_wave_port(self, value):
        self._hfss_port_settings.SetTrianglesWavePort = value
        self._parent._update_setup()


class HfssSolverSettings(object):
    """Manages EDB methods for HFSS solver settings."""

    def __init__(self, parent):
        self._parent = parent

    @property
    def _hfss_solver_settings(self):
        return self._parent._edb_sim_setup_info.SimulationSettings.HFSSSolverSettings

    @property
    def enhanced_low_freq_accuracy(self):
        """Whether to enable legacy low-frequency sampling.

        Returns
        -------
        bool
            ``True`` if low frequency accuracy is used, ``False`` otherwise.
        """
        return self._hfss_solver_settings.EnhancedLowFreqAccuracy

    @enhanced_low_freq_accuracy.setter
    def enhanced_low_freq_accuracy(self, value):
        self._hfss_solver_settings.EnhancedLowFreqAccuracy = value
        self._parent._update_setup()

    @property
    def order_basis(self):
        """Order of the basic functions for HFSS.
        - 0=Zero.
        - 1=1st order.
        - 2=2nd order.
        - 3=Mixed.

        Returns
        -------
        int
            Integer value according to the description."""
        mapping = {0: "zero", 1: "first", 2: "second", 3: "mixed"}
        return mapping[self._hfss_solver_settings.OrderBasis]

    @order_basis.setter
    def order_basis(self, value):
        mapping = {"zero": 0, "first": 1, "second": 2, "mixed": 3}
        self._hfss_solver_settings.OrderBasis = mapping[value]
        self._parent._update_setup()

    @property
    def relative_residual(self):
        """Residual for use by the iterative solver.

        Returns
        -------
        float
        """
        return self._hfss_solver_settings.RelativeResidual

    @relative_residual.setter
    def relative_residual(self, value):
        self._hfss_solver_settings.RelativeResidual = value
        self._parent._update_setup()

    @property
    def solver_type(self):
        """Get solver type to use (Direct/Iterative/Auto) for HFSS.
        Options:
        1- ``kAutoSolver``.
        2- ``kDirectSolver``.
        3- ``kIterativeSolver``.
        4- ``kNumSolverTypes``.

        Returns
        -------
        str
        """
        mapping = {"kAutoSolver": "auto", "kDirectSolver": "direct", "kIterativeSolver": "iterative"}
        solver_type = self._hfss_solver_settings.SolverType.ToString()
        return mapping[solver_type]

    @solver_type.setter
    def solver_type(self, value):
        mapping = {
            "auto": self._hfss_solver_settings.SolverType.kAutoSolver,
            "direct": self._hfss_solver_settings.SolverType.kDirectSolver,
            "iterative": self._hfss_solver_settings.SolverType.kIterativeSolver,
        }
        self._hfss_solver_settings.SolverType = mapping[value]
        self._parent._update_setup()

    @property
    def use_shell_elements(self):
        """Whether to enable use of shell elements.

        Returns
        -------
        bool
            ``True`` if shall elements are used, ``False`` otherwise.
        """
        return self._hfss_solver_settings.UseShellElements

    @use_shell_elements.setter
    def use_shell_elements(self, value):
        self._hfss_solver_settings.UseShellElements = value
        self._parent._update_setup()


class AdaptiveFrequencyData(object):
    """Manages EDB methods for adaptive frequency data."""

    def __init__(self, adaptive_frequency_data):
        self._adaptive_frequency_data = adaptive_frequency_data

    @property
    def adaptive_frequency(self):
        """Adaptive frequency for the setup.

        Returns
        -------
        str
            Frequency with units.
        """
        return self._adaptive_frequency_data.AdaptiveFrequency

    @adaptive_frequency.setter
    def adaptive_frequency(self, value):
        self._adaptive_frequency_data.AdaptiveFrequency = value

    @property
    def max_delta(self):
        """Maximum change of S-parameters between two consecutive passes, which serves as
        a stopping criterion.

        Returns
        -------
        str
        """
        return self._adaptive_frequency_data.MaxDelta

    @max_delta.setter
    def max_delta(self, value):
        self._adaptive_frequency_data.MaxDelta = str(value)

    @property
    def max_passes(self):
        """Maximum allowed number of mesh refinement cycles.

        Returns
        -------
        int
        """
        return self._adaptive_frequency_data.MaxPasses

    @max_passes.setter
    def max_passes(self, value):
        self._adaptive_frequency_data.MaxPasses = value


class AdaptiveSettings(object):
    """Manages EDB methods for adaptive settings."""

    def __init__(self, parent):
        self._parent = parent
        self._adapt_type_mapping = {
            "kSingle": self.adaptive_settings.AdaptType.kSingle,
            "kMultiFrequencies": self.adaptive_settings.AdaptType.kMultiFrequencies,
            "kBroadband": self.adaptive_settings.AdaptType.kBroadband,
            "kNumAdaptTypes": self.adaptive_settings.AdaptType.kNumAdaptTypes,
        }

    @property
    def adaptive_settings(self):
        """Adaptive EDB settings.

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.hfss_simulation_setup_data.AdaptiveSettings`
        """
        return self._parent._edb_sim_setup_info.SimulationSettings.AdaptiveSettings

    @property
    def adaptive_frequency_data_list(self):
        """List of all adaptive frequency data.

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.hfss_simulation_setup_data.AdaptiveFrequencyData`
        """
        return [AdaptiveFrequencyData(i) for i in list(self.adaptive_settings.AdaptiveFrequencyDataList)]

    @property
    def adapt_type(self):
        """Adaptive type.
        Options:
        1- ``kSingle``.
        2- ``kMultiFrequencies``.
        3- ``kBroadband``.
        4- ``kNumAdaptTypes``.

        Returns
        -------
        str
        """
        return self.adaptive_settings.AdaptType.ToString()

    @adapt_type.setter
    def adapt_type(self, value):
        self.adaptive_settings.AdaptType = self._adapt_type_mapping[value]
        self._parent._update_setup()

    @property
    def basic(self):
        """Whether if turn on basic adaptive.

        Returns
        -------
            ``True`` if bais adaptive is used, ``False`` otherwise.
        """
        return self.adaptive_settings.Basic

    @basic.setter
    def basic(self, value):
        self.adaptive_settings.Basic = value
        self._parent._update_setup()

    @property
    def do_adaptive(self):
        """Whether if adpative mesh is on.

        Returns
        -------
        bool
            ``True`` if adaptive is used, ``False`` otherwise.

        """
        return self.adaptive_settings.DoAdaptive

    @property
    def max_refinement(self):
        """Maximum number of mesh elements to be added per pass.

        Returns
        -------
        int
        """
        return self.adaptive_settings.MaxRefinement

    @max_refinement.setter
    def max_refinement(self, value):
        self.adaptive_settings.MaxRefinement = value
        self._parent._update_setup()

    @property
    def max_refine_per_pass(self):
        """Maximum number of mesh elementat that can be added during an adaptive pass.

        Returns
        -------
        int
        """
        return self.adaptive_settings.MaxRefinePerPass

    @max_refine_per_pass.setter
    def max_refine_per_pass(self, value):
        self.adaptive_settings.MaxRefinePerPass = value
        self._parent._update_setup()

    @property
    def min_passes(self):
        """Minimum number of passes.

        Returns
        -------
        int
        """
        return self.adaptive_settings.MinPasses

    @min_passes.setter
    def min_passes(self, value):
        self.adaptive_settings.MinPasses = value
        self._parent._update_setup()

    @property
    def save_fields(self):
        """Whether to turn on save fields.

        Returns
        -------
        bool
            ``True`` if save fields is used, ``False`` otherwise.
        """
        return self.adaptive_settings.SaveFields

    @save_fields.setter
    def save_fields(self, value):
        self.adaptive_settings.SaveFields = value
        self._parent._update_setup()

    @property
    def save_rad_field_only(self):
        """Whether to turn on save radiated fields only.

        Returns
        -------
        bool
            ``True`` if save radiated field only is used, ``False`` otherwise.

        """
        return self.adaptive_settings.SaveRadFieldsOnly

    @save_rad_field_only.setter
    def save_rad_field_only(self, value):
        self.adaptive_settings.SaveRadFieldsOnly = value
        self._parent._update_setup()

    @property
    def use_convergence_matrix(self):
        """Whether to turn on the convergence matrix.

        Returns
        -------
        bool
            ``True`` if convergence matrix is used, ``False`` otherwise.

        """
        return self.adaptive_settings.UseConvergenceMatrix

    @use_convergence_matrix.setter
    def use_convergence_matrix(self, value):
        self.adaptive_settings.UseConvergenceMatrix = value
        self._parent._update_setup()

    @property
    def use_max_refinement(self):
        """Whether to turn on maximum refinement.

        Returns
        -------
        bool
            ``True`` if maximum refinement is used, ``False`` otherwise.
        """
        return self.adaptive_settings.UseMaxRefinement

    @use_max_refinement.setter
    def use_max_refinement(self, value):
        self.adaptive_settings.UseMaxRefinement = value
        self._parent._update_setup()

    @pyaedt_function_handler()
    def add_adaptive_frequency_data(self, frequency=0, max_num_passes=10, max_delta_s=0.02):
        """Add a setup for frequency data.

        Parameters
        ----------
        frequency : str, float
            Frequency with units or float frequency (in Hz).
        max_num_passes : int, optional
            Maximum number of passes. The default is ``10``.
        max_delta_s : float, optional
            Maximum delta S. The default is ``0.02``.

        Returns
        -------
        bool
            ``True`` if method is successful, ``False`` otherwise.
        """
        low_freq_adapt_data = self._parent._edb.simsetupdata.AdaptiveFrequencyData()
        low_freq_adapt_data.MaxDelta = self._parent._edb.edb_value(max_delta_s).ToString()
        low_freq_adapt_data.MaxPasses = max_num_passes
        low_freq_adapt_data.AdaptiveFrequency = self._parent._edb.edb_value(frequency).ToString()
        high_freq_adapt_data = self._parent._edb.simsetupdata.AdaptiveFrequencyData()
        high_freq_adapt_data.MaxDelta = self._parent._edb.edb_value(max_delta_s).ToString()
        high_freq_adapt_data.MaxPasses = max_num_passes
        high_freq_adapt_data.AdaptiveFrequency = self._parent._edb.edb_value(frequency).ToString()
        self.adaptive_settings.AdaptiveFrequencyDataList.Add(low_freq_adapt_data)
        self.adaptive_settings.AdaptiveFrequencyDataList.Add(high_freq_adapt_data)
        return self._parent._update_setup()

    @pyaedt_function_handler()
    def add_broadband_adaptive_frequency_data(
        self, low_frequency=0, high_frequency=10e9, max_num_passes=10, max_delta_s=0.02
    ):
        """Add a setup for frequency data.

        Parameters
        ----------
        low_frequency : str, float
            Frequency with units or float frequency (in Hz).
        high_frequency : str, float
            Frequency with units or float frequency (in Hz).
        max_num_passes : int, optional
            Maximum number of passes. The default is ``10``.
        max_delta_s : float, optional
            Maximum delta S. The default is ``0.02``.

        Returns
        -------
        bool
            ``True`` if method is successful, ``False`` otherwise.
        """
        low_freq_adapt_data = self._parent._edb.simsetupdata.AdaptiveFrequencyData()
        low_freq_adapt_data.MaxDelta = self._parent._edb.edb_value(max_delta_s).ToString()
        low_freq_adapt_data.MaxPasses = max_num_passes
        low_freq_adapt_data.AdaptiveFrequency = self._parent._edb.edb_value(low_frequency).ToString()
        high_freq_adapt_data = self._parent._edb.simsetupdata.AdaptiveFrequencyData()
        high_freq_adapt_data.MaxDelta = self._parent._edb.edb_value(max_delta_s).ToString()
        high_freq_adapt_data.MaxPasses = max_num_passes
        high_freq_adapt_data.AdaptiveFrequency = self._parent._edb.edb_value(high_frequency).ToString()
        self.adaptive_settings.AdaptiveFrequencyDataList.Add(low_freq_adapt_data)
        self.adaptive_settings.AdaptiveFrequencyDataList.Add(high_freq_adapt_data)
        return self._parent._update_setup()


class DefeatureSettings(object):
    """Manages EDB methods for defeature settings."""

    def __init__(self, parent):
        self._parent = parent

    @property
    def _defeature_settings(self):
        return self._parent._edb_sim_setup_info.SimulationSettings.DefeatureSettings

    @property
    def defeature_abs_length(self):
        """Absolute length for polygon defeaturing.

        Returns
        -------
        str
        """
        return self._defeature_settings.DefeatureAbsLength

    @defeature_abs_length.setter
    def defeature_abs_length(self, value):
        self._defeature_settings.DefeatureAbsLength = value
        self._parent._update_setup()

    @property
    def defeature_ratio(self):
        """Defeature ratio.

        Returns
        -------
        float
        """
        return self._defeature_settings.DefeatureRatio

    @defeature_ratio.setter
    def defeature_ratio(self, value):
        self._defeature_settings.DefeatureRatio = value
        self._parent._update_setup()

    @property
    def healing_option(self):
        """Whether to turn on healing of mis-aligned points and edges.
        Options are:
        0- Turn off.
        1- Turn on.

        Returns
        -------
        int
        """
        return self._defeature_settings.HealingOption

    @healing_option.setter
    def healing_option(self, value):
        self._defeature_settings.HealingOption = value
        self._parent._update_setup()

    @property
    def model_type(self):
        """Model type.
        Options:
        0- General.
        1- IC.

        Returns
        -------
        int
        """
        return self._defeature_settings.ModelType

    @model_type.setter
    def model_type(self, value):
        """Model type (General 0 or IC 1)."""
        self._defeature_settings.ModelType = value
        self._parent._update_setup()

    @property
    def remove_floating_geometry(self):
        """Whether to remove floating geometries.

        Returns
        -------
        bool
            ``True`` if floating geometry removal is used, ``False`` otherwise.
        """
        return self._defeature_settings.RemoveFloatingGeometry

    @remove_floating_geometry.setter
    def remove_floating_geometry(self, value):
        self._defeature_settings.RemoveFloatingGeometry = value
        self._parent._update_setup()

    @property
    def small_void_area(self):
        """Small voids to remove area.

        Returns
        -------
        float
        """
        return self._defeature_settings.SmallVoidArea

    @small_void_area.setter
    def small_void_area(self, value):
        self._defeature_settings.SmallVoidArea = value
        self._parent._update_setup()

    @property
    def union_polygons(self):
        """Whether to turn on the union of polygons before meshing.

        Returns
        -------
        bool
            ``True`` if union polygons is used, ``False`` otherwise.
        """
        return self._defeature_settings.UnionPolygons

    @union_polygons.setter
    def union_polygons(self, value):
        self._defeature_settings.UnionPolygons = value
        self._parent._update_setup()

    @property
    def use_defeature(self):
        """Whether to turn on the defeature.

        Returns
        -------
        bool
            ``True`` if defeature is used, ``False`` otherwise.
        """
        return self._defeature_settings.UseDefeature

    @use_defeature.setter
    def use_defeature(self, value):
        self._defeature_settings.UseDefeature = value
        self._parent._update_setup()

    @property
    def use_defeature_abs_length(self):
        """Whether to turn on the defeature absolute length.

        Returns
        -------
        bool
            ``True`` if defeature absolute length is used, ``False`` otherwise.

        """
        return self._defeature_settings.UseDefeatureAbsLength

    @use_defeature_abs_length.setter
    def use_defeature_abs_length(self, value):
        self._defeature_settings.UseDefeatureAbsLength = value
        self._parent._update_setup()


class ViaSettings(object):
    """Manages EDB methods for via settings."""

    def __init__(
        self,
        parent,
    ):
        self._parent = parent
        self._via_style_mapping = {
            "k25DViaWirebond": self._via_settings.T25DViaStyle.k25DViaWirebond,
            "k25DViaRibbon": self._via_settings.T25DViaStyle.k25DViaRibbon,
            "k25DViaMesh": self._via_settings.T25DViaStyle.k25DViaMesh,
            "k25DViaField": self._via_settings.T25DViaStyle.k25DViaField,
            "kNum25DViaStyle": self._via_settings.T25DViaStyle.kNum25DViaStyle,
        }

    @property
    def _via_settings(self):
        return self._parent._edb_sim_setup_info.SimulationSettings.ViaSettings

    @property
    def via_density(self):
        """Via density.

        Returns
        -------
        float
        """
        return self._via_settings.ViaDensity

    @via_density.setter
    def via_density(self, value):
        self._via_settings.ViaDensity = value
        self._parent._update_setup()

    @property
    def via_material(self):
        """Via material.

        Returns
        -------
        str
        """
        return self._via_settings.ViaMaterial

    @via_material.setter
    def via_material(self, value):
        self._via_settings.ViaMaterial = value
        self._parent._update_setup()

    @property
    def via_num_sides(self):
        """Via number of sides.

        Returns
        -------
        int
        """
        return self._via_settings.ViaNumSides

    @via_num_sides.setter
    def via_num_sides(self, value):
        self._via_settings.ViaNumSides = value
        self._parent._update_setup()

    @property
    def via_style(self):
        """Via style.
        Options:
        1- ``k25DViaWirebond``.
        2- ``k25DViaRibbon``.
        3- ``k25DViaMesh``.
        4- ``k25DViaField``.
        5- ``kNum25DViaStyle``.

        Returns
        -------
        str
        """
        return self._via_settings.ViaStyle.ToString()

    @via_style.setter
    def via_style(self, value):
        self._via_settings.ViaStyle = self._via_style_mapping[value]
        self._parent._update_setup()


class AdvancedMeshSettings(object):
    """Manages EDB methods for advanced mesh settings."""

    def __init__(self, parent):
        self._parent = parent

    @property
    def _advanced_mesh_settings(self):
        return self._parent._edb_sim_setup_info.SimulationSettings.AdvancedMeshSettings

    @property
    def layer_snap_tol(self):
        """Layer snap tolerance. Attempt to align independent stackups in the mesher.

        Returns
        -------
        str

        """
        return self._advanced_mesh_settings.LayerSnapTol

    @layer_snap_tol.setter
    def layer_snap_tol(self, value):
        self._advanced_mesh_settings.LayerSnapTol = value
        self._parent._update_setup()

    @property
    def mesh_display_attributes(self):
        """Mesh display attributes. Set color for mesh display (i.e. ``"#000000"``).

        Returns
        -------
        str
        """
        return self._advanced_mesh_settings.MeshDisplayAttributes

    @mesh_display_attributes.setter
    def mesh_display_attributes(self, value):
        self._advanced_mesh_settings.MeshDisplayAttributes = value
        self._parent._update_setup()

    @property
    def replace_3d_triangles(self):
        """Whether to turn on replace 3D triangles.

        Returns
        -------
        bool
            ``True`` if replace 3D triangles is used, ``False`` otherwise.

        """
        return self._advanced_mesh_settings.Replace3DTriangles

    @replace_3d_triangles.setter
    def replace_3d_triangles(self, value):
        self._advanced_mesh_settings.Replace3DTriangles = value
        self._parent._update_setup()


class CurveApproxSettings(object):
    """Manages EDB methods for curve approximate settings."""

    def __init__(self, parent):
        self._parent = parent

    @property
    def _curve_approx_settings(self):
        return self._parent._edb_sim_setup_info.SimulationSettings.CurveApproxSettings

    @property
    def arc_angle(self):
        """Step-size to be used for arc faceting.

        Returns
        -------
        str
        """
        return self._curve_approx_settings.ArcAngle

    @arc_angle.setter
    def arc_angle(self, value):
        self._curve_approx_settings.ArcAngle = value
        self._parent._update_setup()

    @property
    def arc_to_chord_error(self):
        """Maximum tolerated error between straight edge (chord) and faceted arc.

        Returns
        -------
        str
        """
        return self._curve_approx_settings.ArcToChordError

    @arc_to_chord_error.setter
    def arc_to_chord_error(self, value):
        self._curve_approx_settings.ArcToChordError = value
        self._parent._update_setup()

    @property
    def max_arc_points(self):
        """Maximum number of mesh points for arc segments.

        Returns
        -------
        int
        """
        return self._curve_approx_settings.MaxArcPoints

    @max_arc_points.setter
    def max_arc_points(self, value):
        self._curve_approx_settings.MaxArcPoints = value
        self._parent._update_setup()

    @property
    def start_azimuth(self):
        """Azimuth angle for first mesh point of the arc.

        Returns
        -------
        str
        """
        return self._curve_approx_settings.StartAzimuth

    @start_azimuth.setter
    def start_azimuth(self, value):
        self._curve_approx_settings.StartAzimuth = value
        self._parent._update_setup()

    @property
    def use_arc_to_chord_error(self):
        """Whether to turn on the arc-to-chord error setting for arc faceting.

        Returns
        -------
            ``True`` if arc-to-chord error is used, ``False`` otherwise.
        """
        return self._curve_approx_settings.UseArcToChordError

    @use_arc_to_chord_error.setter
    def use_arc_to_chord_error(self, value):
        self._curve_approx_settings.UseArcToChordError = value
        self._parent._update_setup()


class DcrSettings(object):
    """Manages EDB methods for DCR settings."""

    def __init__(self, parent):
        self._parent = parent

    @property
    def _dcr_settings(self):
        return self._parent._edb_sim_setup_info.SimulationSettings.DCRSettings

    @property
    def conduction_max_passes(self):
        """Conduction maximum number of passes.

        Returns
        -------
        int
        """
        return self._dcr_settings.ConductionMaxPasses

    @conduction_max_passes.setter
    def conduction_max_passes(self, value):
        self._dcr_settings.ConductionMaxPasses = value
        self._parent._update_setup()

    @property
    def conduction_min_converged_passes(self):
        """Conduction minimum number of converged passes.

        Returns
        -------
        int
        """
        return self._dcr_settings.ConductionMinConvergedPasses

    @conduction_min_converged_passes.setter
    def conduction_min_converged_passes(self, value):
        self._dcr_settings.ConductionMinConvergedPasses = value
        self._parent._update_setup()

    @property
    def conduction_min_passes(self):
        """Conduction minimum number of passes.

        Returns
        -------
        int
        """
        return self._dcr_settings.ConductionMinPasses

    @conduction_min_passes.setter
    def conduction_min_passes(self, value):
        self._dcr_settings.ConductionMinPasses = value
        self._parent._update_setup()

    @property
    def conduction_per_error(self):
        """WConduction error percentage.

        Returns
        -------
        float
        """
        return self._dcr_settings.ConductionPerError

    @conduction_per_error.setter
    def conduction_per_error(self, value):
        self._dcr_settings.ConductionPerError = value
        self._parent._update_setup()

    @property
    def conduction_per_refine(self):
        """Conduction refinement.

        Returns
        -------
        float
        """
        return self._dcr_settings.ConductionPerRefine

    @conduction_per_refine.setter
    def conduction_per_refine(self, value):
        self._dcr_settings.ConductionPerRefine = value
        self._parent._update_setup()


class HfssSimulationSetup(object):
    """Manages EDB methods for HFSS simulation setup."""

    def __init__(self, edb, name=None, edb_hfss_sim_setup=None):
        self._edb = edb
        self._name = None
        self._mesh_operations = {}

        if edb_hfss_sim_setup:
            self._edb_sim_setup = edb_hfss_sim_setup
            self._edb_sim_setup_info = edb_hfss_sim_setup.GetSimSetupInfo()
            self._name = edb_hfss_sim_setup.GetName()
        else:
            self._edb_sim_setup_info = self._edb.simsetupdata.SimSetupInfo[
                self._edb.simsetupdata.HFSSSimulationSettings
            ]()
            if not name:
                self._edb_sim_setup_info.Name = generate_unique_name("hfss")
            else:
                self._edb_sim_setup_info.Name = name
            self._name = name
            self.hfss_solver_settings.order_basis = "mixed"

            self._edb_sim_setup = self._edb.edb.Utility.HFSSSimulationSetup(self._edb_sim_setup_info)
            self._update_setup()

    @property
    def edb_sim_setup_info(self):
        """EDB internal simulation setup object."""
        return self._edb_sim_setup_info

    @pyaedt_function_handler()
    def _update_setup(self):
        mesh_operations = self._edb_sim_setup_info.SimulationSettings.MeshOperations
        mesh_operations.Clear()
        for mop in self.mesh_operations.values():
            mesh_operations.Add(mop.mesh_operation)

        self._edb_sim_setup = self._edb.edb.Utility.HFSSSimulationSetup(self._edb_sim_setup_info)

        if self._name in self._edb.setups:
            self._edb.active_cell.DeleteSimulationSetup(self._name)
        self._name = self.name
        self._edb.active_cell.AddSimulationSetup(self._edb_sim_setup)
        for i in list(self._edb.active_cell.SimulationSetups):
            if i.GetSimSetupInfo().Name == self._name:
                self._edb_sim_setup_info = i.GetSimSetupInfo()
                return True
        return False

    @property
    def frequency_sweeps(self):
        """Frequency sweep list.

        Returns
        -------
        List of :class:`pyaedt.edb_core.edb_data.hfss_simulation_setup_data.EdbFrequencySweep`
        """
        sweep_data_list = {}
        for i in list(self._edb_sim_setup_info.SweepDataList):
            sweep_data_list[i.Name] = EdbFrequencySweep(self, None, i.Name, i)
        return sweep_data_list

    @property
    def name(self):
        """Name of the setup."""
        return self._edb_sim_setup_info.Name

    @name.setter
    def name(self, value):
        legacy_name = self._name
        self._edb_sim_setup_info.Name = value
        self._update_setup()
        if legacy_name in self._edb.setups:
            del self._edb._setups[legacy_name]
        self._name = value

    @property
    def solver_slider_type(self):
        """Solver slider type.
        Options are:
        1 - ``kFast``.
        2 - ``kMedium``.
        3 - ``kAccurate``.
        4 - ``kNumSliderTypes``.

        Returns
        -------
        str
        """
        return self._edb_sim_setup_info.SimulationSettings.TSolveSliderType.ToString()

    @solver_slider_type.setter
    def solver_slider_type(self, value):
        """Set solver slider type."""
        solver_types = {
            "kFast": self._edb_sim_setup_info.SimulationSettings.TSolveSliderType.k25DViaWirebond,
            "kMedium": self._edb_sim_setup_info.SimulationSettings.TSolveSliderType.k25DViaRibbon,
            "kAccurate": self._edb_sim_setup_info.SimulationSettings.TSolveSliderType.k25DViaMesh,
            "kNumSliderTypes": self._edb_sim_setup_info.SimulationSettings.TSolveSliderType.k25DViaField,
        }
        self._edb_sim_setup_info.SimulationSettings.TSolveSliderType = solver_types[value]
        self._update_setup()

    @property
    def is_auto_setup(self):
        """Whether if auto setup is enabled."""
        return self._edb_sim_setup_info.SimulationSettings.IsAutoSetup

    @is_auto_setup.setter
    def is_auto_setup(self, value):
        self._edb_sim_setup_info.SimulationSettings.IsAutoSetup = value
        self._update_setup()

    @property
    def setup_type(self):
        """Setup type."""
        return self._edb_sim_setup_info.SimulationSettings.SetupType

    @property
    def hfss_solver_settings(self):
        """Manages EDB methods for HFSS solver settings.

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.hfss_simulation_setup_data.HfssSolverSettings`

        """
        return HfssSolverSettings(self)

    @property
    def adaptive_settings(self):
        """Adaptive Settings Class.

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.hfss_simulation_setup_data.AdaptiveSettings`

        """
        return AdaptiveSettings(self)

    @property
    def defeature_settings(self):
        """Defeature settings Class.

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.hfss_simulation_setup_data.DefeatureSettings`

        """
        return DefeatureSettings(self)

    @property
    def via_settings(self):
        """Via settings Class.

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.hfss_simulation_setup_data.ViaSettings`

        """
        return ViaSettings(self)

    @property
    def advanced_mesh_settings(self):
        """Advanced mesh settings Class.

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.hfss_simulation_setup_data.AdvancedMeshSettings`

        """
        return AdvancedMeshSettings(self)

    @property
    def curve_approx_settings(self):
        """Curve approximation settings Class.

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.hfss_simulation_setup_data.CurveApproxSettings`

        """
        return CurveApproxSettings(self)

    @property
    def dcr_settings(self):
        """Dcr settings Class.

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.hfss_simulation_setup_data.DcrSettings`

        """
        return DcrSettings(self)

    @property
    def hfss_port_settings(self):
        """HFSS port settings Class.

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.hfss_simulation_setup_data.HfssPortSettings`

        """
        return HfssPortSettings(self)

    @property
    def mesh_operations(self):
        """Mesh operations settings Class.

        Returns
        -------
        List of :class:`pyaedt.edb_core.edb_data.hfss_simulation_setup_data.MeshOperation`

        """
        if self._mesh_operations:
            return self._mesh_operations
        settings = self._edb_sim_setup_info.SimulationSettings.MeshOperations
        self._mesh_operations = {}
        for i in list(settings):
            if i.MeshOpType == i.TMeshOpType.kMeshSetupLength:
                self._mesh_operations[i.Name] = MeshOperationLength(self, i)
            elif i.MeshOpType == i.TMeshOpType.kMeshSetupSkinDepth:
                self._mesh_operations[i.Name] = MeshOperationSkinDepth(self, i)
            elif i.MeshOpType == i.TMeshOpType.kMeshSetupBase:
                self._mesh_operations[i.Name] = MeshOperationSkinDepth(self, i)

        return self._mesh_operations

    @pyaedt_function_handler()
    def add_length_mesh_operation(
        self,
        net_layer_list,
        name=None,
        max_elements=1000,
        max_length="1mm",
        restrict_elements=True,
        restrict_length=True,
        refine_inside=False,
        mesh_region=None,
    ):
        """Add a mesh operation to the setup.

        Parameters
        ----------
        net_layer_list : dict
            Dictionary containing nets and layers on which enable Mesh operation. Example ``{"A0_N": ["TOP", "PWR"]}``.
        name : str, optional
            Mesh operation name.
        max_elements : int, optional
            Maximum number of elements. Default is ``1000``.
        max_length : str, optional
            Maximum length of elements. Default is ``1mm``.
        restrict_elements : bool, optional
            Whether to restrict number of elements. Default is ``True``.
        restrict_length : bool, optional
            Whether to restrict length of elements. Default is ``True``.
        mesh_region : str, optional
            Mesh region name.
        refine_inside : bool, optional
            Whether to refine inside or not.  Default is ``False``.

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.hfss_simulation_setup_data.LengthMeshOperation`
        """
        if not name:
            name = generate_unique_name("skin")
        mesh_operation = MeshOperationLength(self, self._edb.simsetupdata.LengthMeshOperation())
        mesh_operation.mesh_region = mesh_region
        mesh_operation.name = name
        mesh_operation.nets_layers_list = net_layer_list
        mesh_operation.refine_inside = refine_inside
        mesh_operation.max_elements = str(max_elements)
        mesh_operation.max_length = max_length
        mesh_operation.restrict_length = restrict_length
        mesh_operation.restrict_max_elements = restrict_elements
        self.mesh_operations[name] = mesh_operation
        return mesh_operation if self._update_setup() else False

    @pyaedt_function_handler()
    def add_skin_depth_mesh_operation(
        self,
        net_layer_list,
        name=None,
        max_elements=1000,
        skin_depth="1um",
        restrict_elements=True,
        surface_triangle_length="1mm",
        number_of_layers=2,
        refine_inside=False,
        mesh_region=None,
    ):
        """Add a mesh operation to the setup.

        Parameters
        ----------
        net_layer_list : dict
            Dictionary containing nets and layers on which enable Mesh operation. Example ``{"A0_N": ["TOP", "PWR"]}``.
        name : str, optional
            Mesh operation name.
        max_elements : int, optional
            Maximum number of elements. Default is ``1000``.
        skin_depth : str, optional
            Skin Depth. Default is ``1um``.
        restrict_elements : bool, optional
            Whether to restrict number of elements. Default is ``True``.
        surface_triangle_length : bool, optional
            Surface Triangle length. Default is ``1mm``.
        number_of_layers : int, str, optional
            Number of layers. Default is ``2``.
        mesh_region : str, optional
            Mesh region name.
        refine_inside : bool, optional
            Whether to refine inside or not.  Default is ``False``.

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.hfss_simulation_setup_data.LengthMeshOperation`
        """
        if not name:
            name = generate_unique_name("length")
        mesh_operation = MeshOperationSkinDepth(self, self._edb.simsetupdata.SkinDepthMeshOperation())
        mesh_operation.mesh_region = mesh_region
        mesh_operation.name = name
        mesh_operation.nets_layers_list = net_layer_list
        mesh_operation.refine_inside = refine_inside
        mesh_operation.max_elements = max_elements
        mesh_operation.skin_depth = skin_depth
        mesh_operation.number_of_layer_elements = number_of_layers
        mesh_operation.surface_triangle_length = surface_triangle_length
        mesh_operation.restrict_max_elements = restrict_elements
        self.mesh_operations[name] = mesh_operation
        return mesh_operation if self._update_setup() else False

    @pyaedt_function_handler()
    def add_frequency_sweep(self, name=None, frequency_sweep=None):
        """Add frequency sweep.

        Parameters
        ----------
        name : str, optional
            Name of the frequency sweep.
        frequency_sweep : list, optional
            List of frequency points.

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.hfss_simulation_setup_data.EdbFrequencySweep`

        Examples
        --------
        >>> setup1 = edbapp.create_hfss_setup("setup1")
        >>> setup1.add_frequency_sweep(frequency_sweep=[
        ...                           ["linear count", "0", "1kHz", 1],
        ...                           ["log scale", "1kHz", "0.1GHz", 10],
        ...                           ["linear scale", "0.1GHz", "10GHz", "0.1GHz"],
        ...                           ])
        """
        if name in self.frequency_sweeps:
            return False
        if not name:
            name = generate_unique_name("sweep")
        return EdbFrequencySweep(self, frequency_sweep, name)

    @pyaedt_function_handler()
    def set_solution_single_frequency(self, frequency="5GHz", max_num_passes=10, max_delta_s=0.02):
        """Set single-frequency solution.

        Parameters
        ----------
        frequency : str, float, optional
            Adaptive frequency. The default is ``5GHz``.
        max_num_passes : int, optional
            Maximum number of passes. The default is ``10``.
        max_delta_s : float, optional
            Maximum delta S. The default is ``0.02``.

        Returns
        -------
        bool

        """
        self.adaptive_settings.adapt_type = "kSingle"
        self.adaptive_settings.adaptive_settings.AdaptiveFrequencyDataList.Clear()
        return self.adaptive_settings.add_adaptive_frequency_data(frequency, max_num_passes, max_delta_s)

    @pyaedt_function_handler()
    def set_solution_multi_frequencies(self, frequencies=("5GHz", "10GHz"), max_num_passes=10, max_delta_s="0.02"):
        """Set multi-frequency solution.

        Parameters
        ----------
        frequencies : list, tuple, optional
            List or tuple of adaptive frequencies. The default is ``5GHz``.
        max_num_passes : int, optional
            Maximum number of passes. Default is ``10``.
        max_delta_s : float, optional
            Maximum delta S. The default is ``0.02``.

        Returns
        -------
        bool

        """
        self.adaptive_settings.adapt_type = "kMultiFrequencies"
        self.adaptive_settings.adaptive_settings.AdaptiveFrequencyDataList.Clear()
        for i in frequencies:
            if not self.adaptive_settings.add_adaptive_frequency_data(i, max_num_passes, max_delta_s):
                return False
        return True

    @pyaedt_function_handler()
    def set_solution_broadband(
        self, low_frequency="5GHz", high_frequency="10GHz", max_num_passes=10, max_delta_s="0.02"
    ):
        """Set broadband solution.

        Parameters
        ----------
        low_frequency : str, float, optional
            Low frequency. The default is ``5GHz``.
        high_frequency : str, float, optional
            High frequency. The default is ``10GHz``.
        max_num_passes : int, optional
            Maximum number of passes. The default is ``10``.
        max_delta_s : float, optional
            Maximum Delta S. Default is ``0.02``.

        Returns
        -------
        bool
        """
        self.adaptive_settings.adapt_type = "kBroadband"
        self.adaptive_settings.adaptive_settings.AdaptiveFrequencyDataList.Clear()
        if not self.adaptive_settings.add_broadband_adaptive_frequency_data(
            low_frequency, high_frequency, max_num_passes, max_delta_s
        ):  # pragma no cover
            return False
        return True
