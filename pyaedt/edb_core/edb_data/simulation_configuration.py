import json
import os
from collections import OrderedDict

from pyaedt import generate_unique_name
from pyaedt.edb_core.edb_data.sources import Source
from pyaedt.edb_core.edb_data.sources import SourceType
from pyaedt.generic.clr_module import Dictionary
from pyaedt.generic.constants import BasisOrder
from pyaedt.generic.constants import CutoutSubdesignType
from pyaedt.generic.constants import RadiationBoxType
from pyaedt.generic.constants import SolverType
from pyaedt.generic.constants import SweepType
from pyaedt.generic.constants import validate_enum_class_value
from pyaedt.generic.general_methods import pyaedt_function_handler


class SimulationConfigurationBatch(object):
    """Contains all Cuotut and Batch analysis settings.
    The class is part of `SimulationConfiguration` class as a property.

    """

    def __init__(self):
        self._signal_nets = []
        self._power_nets = []
        self._components = []
        self._cutout_subdesign_type = CutoutSubdesignType.Conformal  # Conformal
        self._cutout_subdesign_expansion = 0.001
        self._cutout_subdesign_round_corner = True
        self._use_default_cutout = True
        self._generate_solder_balls = True
        self._coax_solder_ball_diameter = []
        self._use_default_coax_port_radial_extension = True
        self._trim_reference_size = False
        self._output_aedb = None
        self._signal_layers_properties = {}
        self._coplanar_instances = []
        self._signal_layer_etching_instances = []
        self._etching_factor_instances = []
        self._dielectric_extent = 0.01
        self._airbox_horizontal_extent = 0.04
        self._airbox_negative_vertical_extent = 0.1
        self._airbox_positive_vertical_extent = 0.1
        self._honor_user_dielectric = False
        self._truncate_airbox_at_ground = False
        self._use_radiation_boundary = True
        self._do_cutout_subdesign = True
        self._do_pin_group = True
        self._sources = []

    @property
    def coplanar_instances(self):  # pragma: no cover
        """Retrieve the list of component to be replaced by circuit ports (obsolete).

        Returns
        -------
            list[str]
            List of component name.
        """
        return self._coplanar_instances

    @coplanar_instances.setter
    def coplanar_instances(self, value):  # pragma: no cover
        if isinstance(value, list):
            self._coplanar_instances = value

    @property
    def signal_layer_etching_instances(self):  # pragma: no cover
        """Retrieve the list of layers which has layer etching activated.

        Returns
        -------
            list[str]
            List of layer name.
        """
        return self._signal_layer_etching_instances

    @signal_layer_etching_instances.setter
    def signal_layer_etching_instances(self, value):  # pragma: no cover
        if isinstance(value, list):
            self._signal_layer_etching_instances = value

    @property
    def etching_factor_instances(self):  # pragma: no cover
        """Retrieve the list of etching factor with associated layers.

        Returns
        -------
            list[str]
            list etching parameters with layer name.
        """
        return self._etching_factor_instances

    @etching_factor_instances.setter
    def etching_factor_instances(self, value):  # pragma: no cover
        if isinstance(value, list):
            self._etching_factor_instances = value

    @property
    def dielectric_extent(self):  # pragma: no cover
        """Retrieve the value of dielectric extent.

        Returns
        -------
            float
            Value of the dielectric extent.
        """
        return self._dielectric_extent

    @dielectric_extent.setter
    def dielectric_extent(self, value):  # pragma: no cover
        if isinstance(value, (int, float)):
            self._dielectric_extent = value

    @property
    def airbox_horizontal_extent(self):  # pragma: no cover
        """Retrieve the air box horizontal extent size for HFSS.

        Returns
        -------
            float
            Value of the air box horizontal extent.
        """
        return self._airbox_horizontal_extent

    @airbox_horizontal_extent.setter
    def airbox_horizontal_extent(self, value):  # pragma: no cover
        if isinstance(value, (int, float)):
            self._airbox_horizontal_extent = value

    @property
    def airbox_negative_vertical_extent(self):  # pragma: no cover
        """Retrieve the air box negative vertical extent size for HFSS.

        Returns
        -------
            float
            Value of the air box negative vertical extent.
        """
        return self._airbox_negative_vertical_extent

    @airbox_negative_vertical_extent.setter
    def airbox_negative_vertical_extent(self, value):  # pragma: no cover
        if isinstance(value, (int, float)):
            self._airbox_negative_vertical_extent = value

    @property
    def airbox_positive_vertical_extent(self):  # pragma: no cover
        """Retrieve the air box positive vertical extent size for HFSS.

        Returns
        -------
            float
            Value of the air box positive vertical extent.
        """
        return self._airbox_positive_vertical_extent

    @airbox_positive_vertical_extent.setter
    def airbox_positive_vertical_extent(self, value):  # pragma: no cover
        if isinstance(value, (int, float)):
            self._airbox_positive_vertical_extent = value

    @property
    def use_default_cutout(self):  # pragma: no cover
        """Either if use the default EDB Cutout or new pyaedt cutout.

        Returns
        -------
        bool
        """
        return self._use_default_cutout

    @use_default_cutout.setter
    def use_default_cutout(self, value):  # pragma: no cover
        self._use_default_cutout = value

    @property
    def do_pingroup(self):  # pragma: no cover
        """Do pingroup on multi-pin component. ``True`` all pins from the same net are grouped, ``False`` one port
        is created for each pin.

        Returns
        -------
        bool
        """
        return self._do_pin_group

    @do_pingroup.setter
    def do_pingroup(self, value):  # pragma: no cover
        self._do_pin_group = value

    @property
    def generate_solder_balls(self):  # pragma: no cover
        """Retrieve the boolean for applying solder balls.

        Returns
        -------
        bool
            'True' when applied 'False' if not.
        """
        return self._generate_solder_balls

    @generate_solder_balls.setter
    def generate_solder_balls(self, value):
        if isinstance(value, bool):  # pragma: no cover
            self._generate_solder_balls = value

    @property
    def signal_nets(self):
        """Retrieve the list of signal net names.

        Returns
        -------
        List[str]
            List of signal net names.
        """

        return self._signal_nets

    @signal_nets.setter
    def signal_nets(self, value):
        if isinstance(value, list):  # pragma: no cover
            self._signal_nets = value

    @property
    def power_nets(self):
        """Retrieve the list of power and reference net names.

        Returns
        -------
        list[str]
            List of the net name.
        """
        return self._power_nets

    @power_nets.setter
    def power_nets(self, value):
        if isinstance(value, list):
            self._power_nets = value

    @property
    def components(self):
        """Retrieve the list component name to be included in the simulation.

        Returns
        -------
        list[str]
            List of the component name.
        """
        return self._components

    @components.setter
    def components(self, value):
        if isinstance(value, list):
            self._components = value

    @property
    def coax_solder_ball_diameter(self):  # pragma: no cover
        """Retrieve the list of solder balls diameter values when the auto evaluated one is overwritten.

        Returns
        -------
        list[float]
            List of the solder balls diameter.
        """
        return self._coax_solder_ball_diameter

    @coax_solder_ball_diameter.setter
    def coax_solder_ball_diameter(self, value):  # pragma: no cover
        if isinstance(value, list):
            self._coax_solder_ball_diameter = value

    @property
    def use_default_coax_port_radial_extension(self):
        """Retrieve the boolean for using the default coaxial port extension value.

        Returns
        -------
        bool
            'True' when the default value is used 'False' if not.
        """
        return self._use_default_coax_port_radial_extension

    @use_default_coax_port_radial_extension.setter
    def use_default_coax_port_radial_extension(self, value):  # pragma: no cover
        if isinstance(value, bool):
            self._use_default_coax_port_radial_extension = value

    @property
    def trim_reference_size(self):
        """Retrieve the trim reference size when used.

        Returns
        -------
        float
            The size value.
        """
        return self._trim_reference_size

    @trim_reference_size.setter
    def trim_reference_size(self, value):  # pragma: no cover
        if isinstance(value, bool):
            self._trim_reference_size = value

    @property
    def do_cutout_subdesign(self):
        """Retrieve boolean to perform the cutout during the project build.

        Returns
        -------
            bool
            'True' when clipping the design is applied 'False' is not.
        """
        return self._do_cutout_subdesign

    @do_cutout_subdesign.setter
    def do_cutout_subdesign(self, value):  # pragma: no cover
        if isinstance(value, bool):
            self._do_cutout_subdesign = value

    @property
    def cutout_subdesign_type(self):
        """Retrieve the CutoutSubdesignType selection for clipping the design.

        Returns
        -------
        CutoutSubdesignType object
        """
        return self._cutout_subdesign_type

    @cutout_subdesign_type.setter
    def cutout_subdesign_type(self, value):  # pragma: no cover
        if validate_enum_class_value(CutoutSubdesignType, value):
            self._cutout_subdesign_type = value

    @property
    def cutout_subdesign_expansion(self):
        """Retrieve expansion factor used for clipping the design.

        Returns
        -------
            float
            The value used as a ratio.
        """

        return self._cutout_subdesign_expansion

    @cutout_subdesign_expansion.setter
    def cutout_subdesign_expansion(self, value):  # pragma: no cover
        if isinstance(value, (int, float)):
            self._cutout_subdesign_expansion = value

    @property
    def cutout_subdesign_round_corner(self):
        """Retrieve boolean to perform the design clipping using round corner for the extent generation.

        Returns
        -------
            bool
            'True' when using round corner, 'False' if not.
        """

        return self._cutout_subdesign_round_corner

    @cutout_subdesign_round_corner.setter
    def cutout_subdesign_round_corner(self, value):  # pragma: no cover
        if isinstance(value, bool):
            self._cutout_subdesign_round_corner = value

    @property
    def output_aedb(self):  # pragma: no cover
        """Retrieve the path for the output aedb folder. When provided will copy the initial aedb to the specified
        path. This is used especially to preserve the initial project when several files have to be build based on
        the last one. When the path is None, the initial project will be overwritten. So when cutout is applied mand
        you want to preserve the project make sure you provide the full path for the new aedb folder.

        Returns
        -------
            str
            Absolute path for the created aedb folder.
        """
        return self._output_aedb

    @output_aedb.setter
    def output_aedb(self, value):  # pragma: no cover
        if isinstance(value, str):
            self._output_aedb = value

    @property
    def sources(self):  # pragma: no cover
        """Retrieve the source list.

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.sources.Source`
        """
        return self._sources

    @sources.setter
    def sources(self, value):  # pragma: no cover
        if isinstance(value, Source):
            value = [value]
        if isinstance(value, list):
            if len([src for src in value if isinstance(src, Source)]) == len(value):
                self._sources = value

    @pyaedt_function_handler()
    def add_source(self, source=None):  # pragma: no cover
        """Add a new source to configuration.

        Parameters
        ----------
        source :  :class:`pyaedt.edb_core.edb_data.sources.Source`

        Returns
        -------

        """
        if isinstance(source, Source):
            self._sources.append(source)

    @property
    def honor_user_dielectric(self):  # pragma: no cover
        """Retrieve the boolean to activate the feature "'Honor user dielectric'".

        Returns
        -------
            bool
            "'True'" activated, "'False'" deactivated.
        """
        return self._honor_user_dielectric

    @honor_user_dielectric.setter
    def honor_user_dielectric(self, value):  # pragma: no cover
        if isinstance(value, bool):
            self._honor_user_dielectric = value

    @property
    def truncate_airbox_at_ground(self):  # pragma: no cover
        """Retrieve the boolean to truncate hfss air box at ground.

        Returns
        -------
            bool
            "'True'" activated, "'False'" deactivated.
        """
        return self._truncate_airbox_at_ground

    @truncate_airbox_at_ground.setter
    def truncate_airbox_at_ground(self, value):  # pragma: no cover
        if isinstance(value, bool):
            self._truncate_airbox_at_ground = value

    @property
    def use_radiation_boundary(self):  # pragma: no cover
        """Retrieve the boolean to use radiation boundary with HFSS.

        Returns
        -------
            bool
            "'True'" activated, "'False'" deactivated.
        """
        return self._use_radiation_boundary

    @use_radiation_boundary.setter
    def use_radiation_boundary(self, value):  # pragma: no cover
        if isinstance(value, bool):
            self._use_radiation_boundary = value

    @property
    def signal_layers_properties(self):  # pragma: no cover
        """Retrieve the list of layers to have properties changes.

        Returns
        -------
            list[str]
            List of layer name.
        """
        return self._signal_layers_properties

    @signal_layers_properties.setter
    def signal_layers_properties(self, value):  # pragma: no cover
        if isinstance(value, dict):
            self._signal_layers_properties = value


class SimulationConfigurationDc(object):
    """Contains all DC analysis settings.
    The class is part of `SimulationConfiguration` class as a property.

    """

    def __init__(self):
        self._dc_compute_inductance = False
        self._dc_contact_radius = "100um"
        self._dc_slide_position = 1
        self._dc_use_dc_custom_settings = False
        self._dc_plot_jv = True
        self._dc_min_plane_area_to_mesh = "8mil2"
        self._dc_min_void_area_to_mesh = "0.734mil2"
        self._dc_error_energy = 0.02
        self._dc_max_init_mesh_edge_length = "5.0mm"
        self._dc_max_num_pass = 5
        self._dc_min_num_pass = 1
        self._dc_mesh_bondwires = True
        self._dc_num_bondwire_sides = 8
        self._dc_mesh_vias = True
        self._dc_num_via_sides = 8
        self._dc_percent_local_refinement = 0.2
        self._dc_perform_adaptive_refinement = True
        self._dc_refine_bondwires = True
        self._dc_refine_vias = True
        self._dc_report_config_file = ""
        self._dc_report_show_Active_devices = True
        self._dc_export_thermal_data = True
        self._dc_full_report_path = ""
        self._dc_icepak_temp_file = ""
        self._dc_import_thermal_data = False
        self._dc_per_pin_res_path = ""
        self._dc_per_pin_use_pin_format = True
        self._dc_use_loop_res_for_per_pin = True
        self._dc_via_report_path = ""
        self._dc_source_terms_to_ground = Dictionary[str, int]()

    @property
    def dc_min_plane_area_to_mesh(self):  # pragma: no cover
        """Retrieve the value of the minimum plane area to be meshed by Siwave for DC solution.

        Returns
        -------
            float
            The value of the minimum plane area.
        """
        return self._dc_min_plane_area_to_mesh

    @dc_min_plane_area_to_mesh.setter
    def dc_min_plane_area_to_mesh(self, value):  # pragma: no cover
        if isinstance(value, str):
            self._dc_min_plane_area_to_mesh = value

    @property
    def dc_compute_inductance(self):
        """Return the boolean for computing the inductance with SIwave DC solver.

        Returns
        -------
            bool
            'True' activate 'False' deactivated.
        """
        return self._dc_compute_inductance

    @dc_compute_inductance.setter
    def dc_compute_inductance(self, value):
        if isinstance(value, bool):
            self._dc_compute_inductance = value

    @property
    def dc_contact_radius(self):
        """Retrieve the value for SIwave DC contact radius.

        Returns
        -------
            str
            The contact radius value.

        """
        return self._dc_contact_radius

    @dc_contact_radius.setter
    def dc_contact_radius(self, value):
        if isinstance(value, str):
            self._dc_contact_radius = value

    @dc_compute_inductance.setter
    def dc_compute_inductance(self, value):
        if isinstance(value, str):
            self._dc_contact_radius = value

    @property
    def dc_slide_position(self):
        """Retrieve the SIwave DC slide position value.

        Returns
        -------
            int
            The position value, 0 Optimum speed, 1 balanced, 2 optimum accuracy.
        """
        return self._dc_slide_position

    @dc_slide_position.setter
    def dc_slide_position(self, value):
        if isinstance(value, int):
            self._dc_slide_position = value

    @property
    def dc_use_dc_custom_settings(self):
        """Retrieve the value for using DC custom settings.

        Returns
        -------
            bool
            'True' when activated, 'False' deactivated.

        """
        return self._dc_use_dc_custom_settings

    @dc_use_dc_custom_settings.setter
    def dc_use_dc_custom_settings(self, value):
        if isinstance(value, bool):
            self._dc_use_dc_custom_settings = value

    @property
    def dc_plot_jv(self):
        """Retrieve the value for computing current density and voltage distribution.

        Returns
        -------
            bool
            'True' when activated, 'False' deactivated. Default value True

        """
        return self._dc_plot_jv

    @dc_plot_jv.setter
    def dc_plot_jv(self, value):
        if isinstance(value, bool):
            self._dc_plot_jv = value

    @property
    def dc_min_void_area_to_mesh(self):
        """Retrieve the value for the minimum void surface to mesh.

        Returns
        -------
            str
            The area value.

        """
        return self._dc_min_void_area_to_mesh

    @dc_min_void_area_to_mesh.setter
    def dc_min_void_area_to_mesh(self, value):
        if isinstance(value, str):
            self._dc_min_void_area_to_mesh = value

    @property
    def dc_error_energy(self):
        """Retrieve the value for the DC error energy.

        Returns
        -------
            float
            The error energy value, 0.2 as default.

        """
        return self._dc_error_energy

    @dc_error_energy.setter
    def dc_error_energy(self, value):
        if isinstance(value, (int, float)):
            self._dc_error_energy = value

    @property
    def dc_max_init_mesh_edge_length(self):
        """Retrieve the maximum initial mesh edge value.

        Returns
        -------
            str
            maximum mesh length.

        """
        return self._dc_max_init_mesh_edge_length

    @dc_max_init_mesh_edge_length.setter
    def dc_max_init_mesh_edge_length(self, value):
        if isinstance(value, str):
            self._dc_max_init_mesh_edge_length = value

    @property
    def dc_max_num_pass(self):
        """Retrieve the maximum number of adaptive passes.

        Returns
        -------
            int
            number of passes.
        """
        return self._dc_max_num_pass

    @dc_max_num_pass.setter
    def dc_max_num_pass(self, value):
        if isinstance(value, int):
            self._dc_max_num_pass = value

    @property
    def dc_min_num_pass(self):
        """Retrieve the minimum number of adaptive passes.

        Returns
        -------
            nt
            number of passes.
        """
        return self._dc_min_num_pass

    @dc_min_num_pass.setter
    def dc_min_num_pass(self, value):
        if isinstance(value, int):
            self._dc_min_num_pass = value

    @property
    def dc_mesh_bondwires(self):
        """Retrieve the value for meshing bondwires.

        Returns
        -------
            bool
            'True' when activated, 'False' deactivated.

        """
        return self._dc_mesh_bondwires

    @dc_mesh_bondwires.setter
    def dc_mesh_bondwires(self, value):
        if isinstance(value, bool):
            self._dc_mesh_bondwires = value

    @property
    def dc_num_bondwire_sides(self):
        """Retrieve the number of sides used for cylinder discretization.

        Returns
        -------
            int
            Number of sides.

        """
        return self._dc_num_bondwire_sides

    @dc_num_bondwire_sides.setter
    def dc_num_bondwire_sides(self, value):
        if isinstance(value, int):
            self._dc_num_bondwire_sides = value

    @property
    def dc_mesh_vias(self):
        """Retrieve the value for meshing vias.

        Returns
        -------
            bool
            'True' when activated, 'False' deactivated.

        """
        return self._dc_mesh_vias

    @dc_mesh_vias.setter
    def dc_mesh_vias(self, value):
        if isinstance(value, bool):
            self._dc_mesh_vias = value

    @property
    def dc_num_via_sides(self):
        """Retrieve the number of sides used for cylinder discretization.

        Returns
        -------
            int
            Number of sides.

        """
        return self._dc_num_via_sides

    @dc_num_via_sides.setter
    def dc_num_via_sides(self, value):
        if isinstance(value, int):
            self._dc_num_via_sides = value

    @property
    def dc_percent_local_refinement(self):
        """Retrieve the value for local mesh refinement.

        Returns
        -------
            float
            The refinement value, 0.2 (20%) as default.

        """
        return self._dc_percent_local_refinement

    @dc_percent_local_refinement.setter
    def dc_percent_local_refinement(self, value):
        if isinstance(value, (int, float)):
            self._dc_percent_local_refinement = value

    @property
    def dc_perform_adaptive_refinement(self):
        """Retrieve the value for performing adaptive meshing.

        Returns
        -------
            bool
            'True' when activated, 'False' deactivated.

        """
        return self._dc_perform_adaptive_refinement

    @dc_perform_adaptive_refinement.setter
    def dc_perform_adaptive_refinement(self, value):
        if isinstance(value, bool):
            self._dc_perform_adaptive_refinement = value

    @property
    def dc_refine_bondwires(self):
        """Retrieve the value for performing bond wire refinement.

        Returns
        -------
            bool
            'True' when activated, 'False' deactivated.

        """
        return self._dc_refine_bondwires

    @dc_refine_bondwires.setter
    def dc_refine_bondwires(self, value):
        if isinstance(value, bool):
            self._dc_refine_bondwires = value

    @property
    def dc_refine_vias(self):
        """Retrieve the value for performing vias refinement.

        Returns
        -------
            bool
            'True' when activated, 'False' deactivated.

        """
        return self._dc_refine_vias

    @dc_refine_vias.setter
    def dc_refine_vias(self, value):
        if isinstance(value, bool):
            self._dc_refine_vias = value

    @property
    def dc_report_config_file(self):
        """Retrieve the report configuration file path.

        Returns
        -------
            str
            The file path.

        """
        return self._dc_report_config_file

    @dc_report_config_file.setter
    def dc_report_config_file(self, value):
        if isinstance(value, str):
            self._dc_report_config_file = value

    @property
    def dc_report_show_Active_devices(self):
        """Retrieve the value for showing active devices.

        Returns
        -------
            bool
            'True' when activated, 'False' deactivated.

        """
        return self._dc_report_show_Active_devices

    @dc_report_show_Active_devices.setter
    def dc_report_show_Active_devices(self, value):
        if isinstance(value, bool):
            self._dc_report_show_Active_devices = value

    @property
    def dc_export_thermal_data(self):
        """Retrieve the value for using external data.

        Returns
        -------
            bool
            'True' when activated, 'False' deactivated.

        """
        return self._dc_export_thermal_data

    @dc_export_thermal_data.setter
    def dc_export_thermal_data(self, value):
        if isinstance(value, bool):
            self._dc_export_thermal_data = value

    @property
    def dc_full_report_path(self):
        """Retrieve the path for the report.

        Returns
        -------
            str
            File path.

        """
        return self._dc_full_report_path

    @dc_full_report_path.setter
    def dc_full_report_path(self, value):
        if isinstance(value, str):
            self._dc_full_report_path = value

    @property
    def dc_icepak_temp_file(self):
        """Retrieve the icepak temp file path.

        Returns
        -------
            str
            File path.
        """
        return self._dc_icepak_temp_file

    @dc_icepak_temp_file.setter
    def dc_icepak_temp_file(self, value):
        if isinstance(value, str):
            self._dc_icepak_temp_file = value

    @property
    def dc_import_thermal_data(self):
        """Retrieve the value for importing thermal data.

        Returns
        -------
            bool
            'True' when activated,'False' deactivated.

        """
        return self._dc_import_thermal_data

    @dc_import_thermal_data.setter
    def dc_import_thermal_data(self, value):
        if isinstance(value, bool):
            self._dc_import_thermal_data = value

    @property
    def dc_per_pin_res_path(self):
        """Retrieve the file path.

        Returns
        -------
            str
            The file path.
        """
        return self._dc_per_pin_res_path

    @dc_per_pin_res_path.setter
    def dc_per_pin_res_path(self, value):
        if isinstance(value, str):
            self._dc_per_pin_res_path = value

    @property
    def dc_per_pin_use_pin_format(self):
        """Retrieve the value for using pin format.

        Returns
        -------
            bool
        """
        return self._dc_per_pin_use_pin_format

    @dc_per_pin_use_pin_format.setter
    def dc_per_pin_use_pin_format(self, value):
        if isinstance(value, bool):
            self._dc_per_pin_use_pin_format = value

    @property
    def dc_use_loop_res_for_per_pin(self):
        """Retrieve the value for using the loop resistor per pin.

        Returns
        -------
            bool
        """
        return self._dc_use_loop_res_for_per_pin

    @dc_use_loop_res_for_per_pin.setter
    def dc_use_loop_res_for_per_pin(self, value):
        if isinstance(value, bool):
            self._dc_use_loop_res_for_per_pin = value

    @property
    def dc_via_report_path(self):
        """Retrieve the via report file path.

        Returns
        -------
            str
            The file path.

        """
        return self._dc_via_report_path

    @dc_via_report_path.setter
    def dc_via_report_path(self, value):
        if isinstance(value, str):
            self._dc_via_report_path = value

    @dc_via_report_path.setter
    def dc_via_report_path(self, value):
        if isinstance(value, str):
            self._dc_via_report_path = value

    @property
    def dc_source_terms_to_ground(self):
        """Retrieve the dictionary of grounded terminals.

        Returns
        -------
            Dictionary
            {str, int}, keys is source name, value int 0 unspecified, 1 negative node, 2 positive one.

        """
        return self._dc_source_terms_to_ground

    @dc_source_terms_to_ground.setter
    def dc_source_terms_to_ground(self, value):  # pragma: no cover
        if isinstance(value, OrderedDict):
            if len([k for k in value.keys() if isinstance(k, str)]) == len(value.keys()):
                if len([v for v in value.values() if isinstance(v, int)]) == len(value.values()):
                    self._dc_source_terms_to_ground = value


class SimulationConfigurationAc(object):
    """Contains all AC analysis settings.
    The class is part of `SimulationConfiguration` class as a property.

    """

    def __init__(self):
        self._sweep_interpolating = True
        self._use_q3d_for_dc = False
        self._relative_error = 0.5
        self._use_error_z0 = False
        self._percentage_error_z0 = 1
        self._enforce_causality = True
        self._enforce_passivity = False
        self._passivity_tolerance = 0.0001
        self._sweep_name = "Sweep1"
        self._radiation_box = RadiationBoxType.ConvexHull  # 'ConvexHull'
        self._start_freq = "0.0GHz"  # 0.0
        self._stop_freq = "10.0GHz"  # 10e9
        self._sweep_type = SweepType.Linear  # 'Linear'
        self._step_freq = "0.025GHz"  # 10e6
        self._decade_count = 100  # Newly Added
        self._mesh_freq = "3GHz"  # 5e9
        self._max_num_passes = 30
        self._max_mag_delta_s = 0.03
        self._min_num_passes = 1
        self._basis_order = BasisOrder.Mixed  # 'Mixed'
        self._do_lambda_refinement = True
        self._arc_angle = "30deg"  # 30
        self._start_azimuth = 0
        self._max_arc_points = 8
        self._use_arc_to_chord_error = True
        self._arc_to_chord_error = "1um"  # 1e-6
        self._defeature_abs_length = "1um"  # 1e-6
        self._defeature_layout = True
        self._minimum_void_surface = 0
        self._max_suf_dev = 1e-3
        self._process_padstack_definitions = False
        self._return_current_distribution = True
        self._ignore_non_functional_pads = True
        self._include_inter_plane_coupling = True
        self._xtalk_threshold = -50
        self._min_void_area = "0.01mm2"
        self._min_pad_area_to_mesh = "0.01mm2"
        self._snap_length_threshold = "2.5um"
        self._min_plane_area_to_mesh = "4mil2"  # Newly Added
        self._mesh_sizefactor = 0.0

    @property
    def sweep_interpolating(self):  # pragma: no cover
        """Retrieve boolean to add a sweep interpolating sweep.

        Returns
        -------
            bool
            'True' when a sweep interpolating is defined, 'False' when a discrete one is defined instead.
        """

        return self._sweep_interpolating

    @sweep_interpolating.setter
    def sweep_interpolating(self, value):  # pragma: no cover
        if isinstance(value, bool):
            self._sweep_interpolating = value

    @property
    def use_q3d_for_dc(self):  # pragma: no cover
        """Retrieve boolean to Q3D solver for DC point value computation.

        Returns
        -------
            bool
            'True' when Q3D solver is used 'False' when interpolating value is used instead.
        """

        return self._use_q3d_for_dc

    @use_q3d_for_dc.setter
    def use_q3d_for_dc(self, value):  # pragma: no cover
        if isinstance(value, bool):
            self._use_q3d_for_dc = value

    @property
    def relative_error(self):  # pragma: no cover
        """Retrieve relative error used for the interpolating sweep convergence.

        Returns
        -------
            float
            The value of the error interpolating sweep to reach the convergence criteria.
        """

        return self._relative_error

    @relative_error.setter
    def relative_error(self, value):  # pragma: no cover
        if isinstance(value, (int, float)):
            self._relative_error = value

    @property
    def use_error_z0(self):  # pragma: no cover
        """Retrieve value for the error on Z0 for the port.

        Returns
        -------
            float
            The Z0 value.
        """

        return self._use_error_z0

    @use_error_z0.setter
    def use_error_z0(self, value):  # pragma: no cover
        if isinstance(value, bool):
            self._use_error_z0 = value

    @property
    def percentage_error_z0(self):  # pragma: no cover
        """Retrieve boolean to perform the cutout during the project build.

        Returns
        -------
            bool
            'True' when clipping the design is applied 'False' if not.
        """

        return self._percentage_error_z0

    @percentage_error_z0.setter
    def percentage_error_z0(self, value):  # pragma: no cover
        if isinstance(value, (int, float)):
            self._percentage_error_z0 = value

    @property
    def enforce_causality(self):  # pragma: no cover
        """Retrieve boolean to enforce causality for the frequency sweep.

        Returns
        -------
            bool
            'True' when causality is enforced 'False' if not.
        """

        return self._enforce_causality

    @enforce_causality.setter
    def enforce_causality(self, value):  # pragma: no cover
        if isinstance(value, bool):
            self._enforce_causality = value

    @property
    def enforce_passivity(self):  # pragma: no cover
        """Retrieve boolean to enforce passivity for the frequency sweep.

        Returns
        -------
            bool
            'True' when passivity is enforced 'False' if not.
        """
        return self._enforce_passivity

    @enforce_passivity.setter
    def enforce_passivity(self, value):  # pragma: no cover
        if isinstance(value, bool):
            self._enforce_passivity = value

    @property
    def passivity_tolerance(self):  # pragma: no cover
        """Retrieve the value for the passivity tolerance when used.

        Returns
        -------
            float
            The passivity tolerance criteria for the frequency sweep.
        """
        return self._passivity_tolerance

    @passivity_tolerance.setter
    def passivity_tolerance(self, value):  # pragma: no cover
        if isinstance(value, (int, float)):
            self._passivity_tolerance = value

    @property
    def sweep_name(self):  # pragma: no cover
        """Retrieve frequency sweep name.

        Returns
        -------
            str
            The name of the frequency sweep defined in the project.
        """
        return self._sweep_name

    @sweep_name.setter
    def sweep_name(self, value):  # pragma: no cover
        if isinstance(value, str):
            self._sweep_name = value

    @property
    def radiation_box(self):  # pragma: no cover
        """Retrieve RadiationBoxType object selection defined for the radiation box type.

        Returns
        -------
            RadiationBoxType object
            3 values can be chosen, Conformal, BoundingBox or ConvexHull.
        """
        return self._radiation_box

    @radiation_box.setter
    def radiation_box(self, value):
        if validate_enum_class_value(RadiationBoxType, value):
            self._radiation_box = value

    @property
    def start_freq(self):  # pragma: no cover
        """Starting frequency for the frequency sweep.

        Returns
        -------
        float
            Value of the frequency point.
        """
        return self._start_freq

    @start_freq.setter
    def start_freq(self, value):  # pragma: no cover
        if isinstance(value, str):
            self._start_freq = value

    @property
    def stop_freq(self):  # pragma: no cover
        """Retrieve stop frequency for the frequency sweep.

        Returns
        -------
            float
            The value of the frequency point.
        """
        return self._stop_freq

    @stop_freq.setter
    def stop_freq(self, value):  # pragma: no cover
        if isinstance(value, str):
            self._stop_freq = value

    @property
    def sweep_type(self):  # pragma: no cover
        """Retrieve SweepType object for the frequency sweep.

        Returns
        -------
            SweepType
            The SweepType object,2 selections are supported Linear and LogCount.
        """
        return self._sweep_type

    @sweep_type.setter
    def sweep_type(self, value):  # pragma: no cover
        if validate_enum_class_value(SweepType, value):
            self._sweep_type = value

    @property
    def step_freq(self):  # pragma: no cover
        """Retrieve step frequency for the frequency sweep.

        Returns
        -------
            float
            The value of the frequency point.
        """
        return self._step_freq

    @step_freq.setter
    def step_freq(self, value):  # pragma: no cover
        if isinstance(value, str):
            self._step_freq = value

    @property
    def decade_count(self):  # pragma: no cover
        """Retrieve decade count number for the frequency sweep in case of a log sweep selected.

        Returns
        -------
            int
            The value of the decade count number.
        """
        return self._decade_count

    @decade_count.setter
    def decade_count(self, value):  # pragma: no cover
        if isinstance(value, int):
            self._decade_count = value

    @property
    def mesh_freq(self):
        """Retrieve the meshing frequency for the HFSS adaptive convergence.

        Returns
        -------
            float
            The value of the frequency point.
        """
        return self._mesh_freq

    @mesh_freq.setter
    def mesh_freq(self, value):  # pragma: no cover
        if isinstance(value, str):
            self._mesh_freq = value

    @property
    def max_num_passes(self):  # pragma: no cover
        """Retrieve maximum of points for the HFSS adaptive meshing.

        Returns
        -------
            int
            The maximum number of adaptive passes value.
        """
        return self._max_num_passes

    @max_num_passes.setter
    def max_num_passes(self, value):  # pragma: no cover
        if isinstance(value, int):
            self._max_num_passes = value

    @property
    def max_mag_delta_s(self):  # pragma: no cover
        """Retrieve the magnitude of the delta S convergence criteria for the interpolating sweep.

        Returns
        -------
            float
            The value of convergence criteria.
        """
        return self._max_mag_delta_s

    @max_mag_delta_s.setter
    def max_mag_delta_s(self, value):  # pragma: no cover
        if isinstance(value, (int, float)):
            self._max_mag_delta_s = value

    @property
    def min_num_passes(self):  # pragma: no cover
        """Retrieve the minimum number of adaptive passes for HFSS convergence.

        Returns
        -------
            int
            The value of minimum number of adaptive passes.
        """
        return self._min_num_passes

    @min_num_passes.setter
    def min_num_passes(self, value):  # pragma: no cover
        if isinstance(value, int):
            self._min_num_passes = value

    @property
    def basis_order(self):  # pragma: no cover
        """Retrieve the BasisOrder object.

        Returns
        -------
            BasisOrder class
            This class supports 4 selections Mixed, Zero, single and Double for the HFSS order matrix.
        """
        return self._basis_order

    @basis_order.setter
    def basis_order(self, value):  # pragma: no cover
        if validate_enum_class_value(BasisOrder, value):
            self._basis_order = value

    @property
    def do_lambda_refinement(self):  # pragma: no cover
        """Retrieve boolean to activate the lambda refinement.

        Returns
        -------
            bool
            'True' Enable the lambda meshing refinement with HFSS, 'False' deactivate.
        """
        return self._do_lambda_refinement

    @do_lambda_refinement.setter
    def do_lambda_refinement(self, value):  # pragma: no cover
        if isinstance(value, bool):
            self._do_lambda_refinement = value

    @property
    def arc_angle(self):  # pragma: no cover
        """Retrieve the value for the HFSS meshing arc angle.

        Returns
        -------
            float
            Value of the arc angle.
        """
        return self._arc_angle

    @arc_angle.setter
    def arc_angle(self, value):  # pragma: no cover
        if isinstance(value, str):
            self._arc_angle = value

    @property
    def start_azimuth(self):  # pragma: no cover
        """Retrieve the value of the starting azimuth for the HFSS meshing.

        Returns
        -------
            float
            Value of the starting azimuth.
        """
        return self._start_azimuth

    @start_azimuth.setter
    def start_azimuth(self, value):  # pragma: no cover
        if isinstance(value, (int, float)):
            self._start_azimuth = value

    @property
    def max_arc_points(self):  # pragma: no cover
        """Retrieve the value of the maximum arc points number for the HFSS meshing.

        Returns
        -------
            int
            Value of the maximum arc point number.
        """
        return self._max_arc_points

    @max_arc_points.setter
    def max_arc_points(self, value):  # pragma: no cover
        if isinstance(value, int):
            self._max_arc_points = value

    @property
    def use_arc_to_chord_error(self):  # pragma: no cover
        """Retrieve the boolean for activating the arc to chord for HFSS meshing.

        Returns
        -------
            bool
            Activate when 'True', deactivated when 'False'.
        """
        return self._use_arc_to_chord_error

    @use_arc_to_chord_error.setter
    def use_arc_to_chord_error(self, value):  # pragma: no cover
        if isinstance(value, bool):
            self._use_arc_to_chord_error = value

    @property
    def arc_to_chord_error(self):  # pragma: no cover
        """Retrieve the value of arc to chord error for HFSS meshing.

        Returns
        -------
            flot
            Value of the arc to chord error.
        """
        return self._arc_to_chord_error

    @arc_to_chord_error.setter
    def arc_to_chord_error(self, value):  # pragma: no cover
        if isinstance(value, str):
            self._arc_to_chord_error = value

    @property
    def defeature_abs_length(self):  # pragma: no cover
        """Retrieve the value of arc to chord for HFSS meshing.

        Returns
        -------
            flot
            Value of the arc to chord error.
        """
        return self._defeature_abs_length

    @defeature_abs_length.setter
    def defeature_abs_length(self, value):  # pragma: no cover
        if isinstance(value, str):
            self._defeature_abs_length = value

    @property
    def defeature_layout(self):  # pragma: no cover
        """Retrieve the boolean to activate the layout defeaturing.This method has been developed to simplify polygons
        with reducing the number of points to simplify the meshing with controlling its surface deviation. This method
        should be used at last resort when other methods failed.

        Returns
        -------
            bool
            'True' when activated 'False when deactivated.
        """
        return self._defeature_layout

    @defeature_layout.setter
    def defeature_layout(self, value):  # pragma: no cover
        if isinstance(value, bool):
            self._defeature_layout = value

    @property
    def minimum_void_surface(self):  # pragma: no cover
        """Retrieve the minimum void surface to be considered for the layout defeaturing.
        Voids below this value will be ignored.

        Returns
        -------
            flot
            Value of the minimum surface.
        """
        return self._minimum_void_surface

    @minimum_void_surface.setter
    def minimum_void_surface(self, value):  # pragma: no cover
        if isinstance(value, (int, float)):
            self._minimum_void_surface = value

    @property
    def max_suf_dev(self):  # pragma: no cover
        """Retrieve the value for the maximum surface deviation for the layout defeaturing.

        Returns
        -------
            flot
            Value of maximum surface deviation.
        """
        return self._max_suf_dev

    @max_suf_dev.setter
    def max_suf_dev(self, value):  # pragma: no cover
        if isinstance(value, (int, float)):
            self._max_suf_dev = value

    @property
    def process_padstack_definitions(self):  # pragma: no cover
        """Retrieve the boolean for activating the padstack definition processing.

        Returns
        -------
            flot
            Value of the arc to chord error.
        """
        return self._process_padstack_definitions

    @process_padstack_definitions.setter
    def process_padstack_definitions(self, value):  # pragma: no cover
        if isinstance(value, bool):
            self._process_padstack_definitions = value

    @property
    def return_current_distribution(self):  # pragma: no cover
        """Boolean to activate the current distribution return with Siwave.

        Returns
        -------
            flot
            Value of the arc to chord error.
        """
        return self._return_current_distribution

    @return_current_distribution.setter
    def return_current_distribution(self, value):  # pragma: no cover
        if isinstance(value, bool):
            self._return_current_distribution = value

    @property
    def ignore_non_functional_pads(self):  # pragma: no cover
        """Boolean to ignore nonfunctional pads with Siwave.

        Returns
         -------
            flot
            Value of the arc to chord error.
        """
        return self._ignore_non_functional_pads

    @ignore_non_functional_pads.setter
    def ignore_non_functional_pads(self, value):  # pragma: no cover
        if isinstance(value, bool):
            self._ignore_non_functional_pads = value

    @property
    def include_inter_plane_coupling(self):  # pragma: no cover
        """Boolean to activate the inter-plane coupling with Siwave.

        Returns
        -------
            bool
            'True' activated 'False' deactivated.
        """
        return self._include_inter_plane_coupling

    @include_inter_plane_coupling.setter
    def include_inter_plane_coupling(self, value):  # pragma: no cover
        if isinstance(value, bool):
            self._include_inter_plane_coupling = value

    @property
    def xtalk_threshold(self):  # pragma: no cover
        """Return the value for Siwave cross talk threshold. THis value specifies the distance for the solver to
        consider lines coupled during the cross-section computation. Decreasing the value below -60dB can
        potentially cause solver failure.

        Returns
        -------
            flot
            Value of cross-talk threshold.
        """
        return self._xtalk_threshold

    @xtalk_threshold.setter
    def xtalk_threshold(self, value):  # pragma: no cover
        if isinstance(value, (int, float)):
            self._xtalk_threshold = value

    @property
    def min_void_area(self):  # pragma: no cover
        """Retrieve the value of minimum void area to be considered by Siwave.

        Returns
        -------
            flot
            Value of the arc to chord error.
        """
        return self._min_void_area

    @min_void_area.setter
    def min_void_area(self, value):  # pragma: no cover
        if isinstance(value, str):
            self._min_void_area = value

    @property
    def min_pad_area_to_mesh(self):  # pragma: no cover
        """Retrieve the value of minimum pad area to be meshed by Siwave.

        Returns
        -------
            flot
            Value of minimum pad surface.
        """
        return self._min_pad_area_to_mesh

    @min_pad_area_to_mesh.setter
    def min_pad_area_to_mesh(self, value):  # pragma: no cover
        if isinstance(value, str):
            self._min_pad_area_to_mesh = value

    @property
    def snap_length_threshold(self):  # pragma: no cover
        """Retrieve the boolean to activate the snapping threshold feature.

        Returns
        -------
            bool
            'True' activate 'False' deactivated.
        """
        return self._snap_length_threshold

    @snap_length_threshold.setter
    def snap_length_threshold(self, value):  # pragma: no cover
        if isinstance(value, str):
            self._snap_length_threshold = value

    @property
    def min_plane_area_to_mesh(self):  # pragma: no cover
        """Retrieve the minimum plane area to be meshed by Siwave.

        Returns
        -------
            flot
            Value of the minimum plane area.
        """
        return self._min_plane_area_to_mesh

    @min_plane_area_to_mesh.setter
    def min_plane_area_to_mesh(self, value):  # pragma: no cover
        if isinstance(value, str):
            self._min_plane_area_to_mesh = value

    @property
    def mesh_sizefactor(self):
        """Retrieve the Mesh Size factor value.

        Returns
        -------
        float
        """
        return self._mesh_sizefactor

    @mesh_sizefactor.setter
    def mesh_sizefactor(self, value):
        if isinstance(value, (int, float)):
            self._mesh_sizefactor = value
            if value > 0.0:
                self._do_lambda_refinement = False


class SimulationConfiguration(object):
    """Provides an ASCII simulation configuration file parser.

    This parser supports all types of inputs for setting up and automating any kind
    of SI or PI simulation with HFSS 3D Layout or Siwave. If fields are omitted, default
    values are applied. This class can be instantiated directly from
    Configuration file.

    Examples
    --------
    >>> from pyaedt import Edb
    >>> edb = Edb()
    >>> sim_setup = edb.new_simulation_configuration()
    >>> sim_setup.solver_type = SolverType.SiwaveSYZ
    >>> sim_setup.batch_solve_settings.cutout_subdesign_expansion = 0.01
    >>> sim_setup.batch_solve_settings.do_cutout_subdesign = True
    >>> sim_setup.batch_solve_settings.signal_nets = ["PCIE0_RX0_P", "PCIE0_RX0_N", "PCIE0_TX0_P_C", "PCIE0_TX0_N_C"]
    >>> sim_setup.batch_solve_settings.components = ["U2A5", "J2L1"]
    >>> sim_setup.batch_solve_settings.power_nets = ["GND"]
    >>> sim_setup.ac_settings.start_freq = "100Hz"
    >>> sim_setup.ac_settings.stop_freq = "6GHz"
    >>> sim_setup.ac_settings.step_freq = "10MHz"
    >>> sim_setup.export_json(os.path.join(project_path, "configuration.json"))
    >>> sim_setup.build_simulation_project(sim_setup)

    """

    def __getattr__(self, item):
        if item in dir(self):
            return self.__getattribute__(item)
        elif item in dir(self.dc_settings):
            return self.dc_settings.__getattribute__(item)
        elif item in dir(self.ac_settings):
            return self.ac_settings.__getattribute__(item)
        elif item in dir(self.batch_solve_settings):
            return self.batch_solve_settings.__getattribute__(item)
        else:
            raise AttributeError("Attribute {} not present.".format(item))

    def __setattr__(self, key, value):
        if "_dc_settings" in dir(self) and key in dir(self._dc_settings):
            return self.dc_settings.__setattr__(key, value)
        elif "_ac_settings" in dir(self) and key in dir(self._ac_settings):
            return self.ac_settings.__setattr__(key, value)
        elif "_batch_solve_settings" in dir(self) and key in dir(self._batch_solve_settings):
            return self.batch_solve_settings.__setattr__(key, value)
        else:
            return super(SimulationConfiguration, self).__setattr__(key, value)

    def __init__(self, filename=None, edb=None):
        self._filename = filename
        self._open_edb_after_build = True
        self._dc_settings = SimulationConfigurationDc()
        self._ac_settings = SimulationConfigurationAc()
        self._batch_solve_settings = SimulationConfigurationBatch()
        self._setup_name = "Pyaedt_setup"
        self._solver_type = SolverType.Hfss3dLayout
        if self._filename and os.path.splitext(self._filename)[1] == ".json":
            self.import_json(filename)
        self._read_cfg()
        self._pedb = edb
        self.SOLVER_TYPE = SolverType

    @property
    def open_edb_after_build(self):
        """Either if open the Edb after the build or not.

        Returns
        -------
        bool
        """
        return self._open_edb_after_build

    @open_edb_after_build.setter
    def open_edb_after_build(self, value):
        if isinstance(value, bool):
            self._open_edb_after_build = value

    @property
    def dc_settings(self):
        """DC Settings class.

        Returns
        -------
        :class:`pyaedt.edb_core_edb_data.simulationconfiguration.SimulationConfigurationDc`
        """
        return self._dc_settings

    @property
    def ac_settings(self):
        """AC Settings class.

        Returns
        -------
        :class:`pyaedt.edb_core_edb_data.simulationconfiguration.SimulationConfigurationAc`
        """
        return self._ac_settings

    @property
    def batch_solve_settings(self):
        """Cutout and Batch Settings class.

        Returns
        -------
        :class:`pyaedt.edb_core_edb_data.simulationconfiguration.SimulationConfigurationBatch`
        """
        return self._batch_solve_settings

    def build_simulation_project(self):
        """Build active simulation project. This method requires to be run inside Edb Class."""
        if self._pedb:
            return self._pedb.build_simulation_project(self)

    @property
    def solver_type(self):  # pragma: no cover
        """Retrieve the SolverType class to select the solver to be called during the project build.

        Returns
        -------
            SolverType
            selections are supported, Hfss3dLayout and Siwave.
        """
        return self._solver_type

    @solver_type.setter
    def solver_type(self, value):  # pragma: no cover
        if isinstance(value, int):
            self._solver_type = value

    @property
    def filename(self):  # pragma: no cover
        """Retrieve the file name loaded for mapping properties value.

        Returns
        -------
        str
            the absolute path for the filename.
        """
        return self._filename

    @filename.setter
    def filename(self, value):
        if isinstance(value, str):  # pragma: no cover
            self._filename = value

    @property
    def setup_name(self):
        """Retrieve setup name for the simulation.

        Returns
        -------
        str
            Setup name.
        """
        return self._setup_name

    @setup_name.setter
    def setup_name(self, value):
        if isinstance(value, str):  # pragma: no cover
            self._setup_name = value

    def _get_bool_value(self, value):  # pragma: no cover
        val = value.lower()
        if val in ("y", "yes", "t", "true", "on", "1"):
            return True
        elif val in ("n", "no", "f", "false", "off", "0"):
            return False
        else:
            raise ValueError("Invalid truth value %r" % (val,))

    def _get_list_value(self, value):  # pragma: no cover
        value = value[1:-1]
        if len(value) == 0:
            return []
        else:
            value = value.split(",")
            if isinstance(value, list):
                prop_values = [i.strip() for i in value]
            else:
                prop_values = [value.strip()]
            return prop_values

    @pyaedt_function_handler()
    def add_dc_ground_source_term(self, source_name=None, node_to_ground=1):
        """Add a dc ground source terminal for Siwave.

        Parameters
        ----------
        source_name : str, optional
            The source name to assign the reference node to.
            Default value is ``None``.

        node_to_ground : int, optional
            Value must be ``0``: unspecified, ``1``: negative node, ``2``: positive node.
            Default value is ``1``.

        """
        if source_name:
            if node_to_ground in [0, 1, 2]:
                self._dc_source_terms_to_ground[source_name] = node_to_ground

    def _parse_signal_layer_properties(self, signal_properties):  # pragma: no cover
        for lay in signal_properties:
            lp = lay.split(":")
            try:
                self.signal_layers_properties.update({lp[0]: [lp[1], lp[2], lp[3], lp[4], lp[5]]})
            except:
                print("Missing parameter for layer {0}".format(lp[0]))

    def _read_cfg(self):  # pragma: no cover
        """Configuration file reader.

        Examples
        --------

        >>> from pyaedt import Edb
        >>> from pyaedt.edb_core.edb_data.simulation_configuration import SimulationConfiguration
        >>> config_file = path_configuration_file
        >>> source_file = path_to_edb_folder
        >>> edb = Edb(source_file)
        >>> sim_setup = SimulationConfiguration(config_file)
        >>> edb.build_simulation_project(sim_setup)
        >>> edb.save_edb()
        >>> edb.close_edb()
        """

        if not self.filename or not os.path.exists(self.filename):
            # raise Exception("{} does not exist.".format(self.filename))
            return

        try:
            with open(self.filename) as cfg_file:
                cfg_lines = cfg_file.read().split("\n")
                for line in cfg_lines:
                    if line.strip() != "":
                        if line.find("="):
                            i, prop_value = line.strip().split("=")
                            value = prop_value.replace("'", "").strip()
                            if i.lower().startswith("generatesolderballs"):
                                self.generate_solder_balls = self._get_bool_value(value)
                            elif i.lower().startswith("signalnets"):
                                self.signal_nets = value[1:-1].split(",") if value[0] == "[" else value.split(",")
                                self.signal_nets = [item.strip() for item in self.signal_nets]
                            elif i.lower().startswith("powernets"):
                                self.power_nets = value[1:-1].split(",") if value[0] == "[" else value.split(",")
                                self.power_nets = [item.strip() for item in self.power_nets]
                            elif i.lower().startswith("components"):
                                self.components = value[1:-1].split(",") if value[0] == "[" else value.split(",")
                                self.components = [item.strip() for item in self.components]
                            elif i.lower().startswith("coaxsolderballsdiams"):
                                self.coax_solder_ball_diameter = (
                                    value[1:-1].split(",") if value[0] == "[" else value.split(",")
                                )
                                self.coax_solder_ball_diameter = [
                                    item.strip() for item in self.coax_solder_ball_diameter
                                ]
                            elif i.lower().startswith("usedefaultcoaxportradialextentfactor"):
                                self.signal_nets = self._get_bool_value(value)
                            elif i.lower().startswith("trimrefsize"):
                                self.trim_reference_size = self._get_bool_value(value)
                            elif i.lower().startswith("cutoutsubdesigntype"):
                                if value.lower().startswith("conformal"):
                                    self.cutout_subdesign_type = CutoutSubdesignType.Conformal
                                elif value.lower().startswith("boundingbox"):
                                    self.cutout_subdesign_type = CutoutSubdesignType.BoundingBox
                                else:
                                    print("Unprocessed value for CutoutSubdesignType '{0}'".format(value))
                            elif i.lower().startswith("cutoutsubdesignexpansion"):
                                self.cutout_subdesign_expansion = float(value)
                            elif i.lower().startswith("cutoutsubdesignroundcorners"):
                                self.cutout_subdesign_round_corner = self._get_bool_value(value)
                            elif i.lower().startswith("sweepinterpolating"):
                                self.sweep_interpolating = self._get_bool_value(value)
                            elif i.lower().startswith("useq3dfordc"):
                                self.use_q3d_for_dc = self._get_bool_value(value)
                            elif i.lower().startswith("relativeerrors"):
                                self.relative_error = float(value)
                            elif i.lower().startswith("useerrorz0"):
                                self.use_error_z0 = self._get_bool_value(value)
                            elif i.lower().startswith("percenterrorz0"):
                                self.percentage_error_z0 = float(value)
                            elif i.lower().startswith("enforcecausality"):
                                self.enforce_causality = self._get_bool_value(value)
                            elif i.lower().startswith("enforcepassivity"):
                                self.enforce_passivity = self._get_bool_value(value)
                            elif i.lower().startswith("passivitytolerance"):
                                self.passivity_tolerance = float(value)
                            elif i.lower().startswith("sweepname"):
                                self.sweep_name = value
                            elif i.lower().startswith("radiationbox"):
                                if value.lower().startswith("conformal"):
                                    self.radiation_box = RadiationBoxType.Conformal
                                elif value.lower().startswith("boundingbox"):
                                    self.radiation_box = RadiationBoxType.BoundingBox
                                elif value.lower().startswith("convexhull"):
                                    self.radiation_box = RadiationBoxType.ConvexHull
                                else:
                                    print("Unprocessed value for RadiationBox '{0}'".format(value))
                            elif i.lower().startswith("startfreq"):
                                self.start_freq = value
                            elif i.lower().startswith("stopfreq"):
                                self.stop_freq = value
                            elif i.lower().startswith("sweeptype"):
                                if value.lower().startswith("linear"):
                                    self.sweep_type = SweepType.Linear
                                elif value.lower().startswith("logcount"):
                                    self.sweep_type = SweepType.LogCount
                                else:
                                    print("Unprocessed value for SweepType '{0}'".format(value))
                            elif i.lower().startswith("stepfreq"):
                                self.step_freq = value
                            elif i.lower().startswith("decadecount"):
                                self.decade_count = int(value)
                            elif i.lower().startswith("mesh_freq"):
                                self.mesh_freq = value
                            elif i.lower().startswith("maxnumpasses"):
                                self.max_num_passes = int(value)
                            elif i.lower().startswith("maxmagdeltas"):
                                self.max_mag_delta_s = float(value)
                            elif i.lower().startswith("minnumpasses"):
                                self.min_num_passes = int(value)
                            elif i.lower().startswith("basisorder"):
                                if value.lower().startswith("mixed"):
                                    self.basis_order = BasisOrder.Mixed
                                elif value.lower().startswith("zero"):
                                    self.basis_order = BasisOrder.Zero
                                elif value.lower().startswith("first"):  # single
                                    self.basis_order = BasisOrder.Single
                                elif value.lower().startswith("second"):  # double
                                    self.basis_order = BasisOrder.Double
                                else:
                                    print("Unprocessed value for BasisOrder '{0}'".format(value))
                            elif i.lower().startswith("dolambdarefinement"):
                                self.do_lambda_refinement = self._get_bool_value(value)
                            elif i.lower().startswith("arcangle"):
                                self.arc_angle = value
                            elif i.lower().startswith("startazimuth"):
                                self.start_azimuth = float(value)
                            elif i.lower().startswith("maxarcpoints"):
                                self.max_arc_points = int(value)
                            elif i.lower().startswith("usearctochorderror"):
                                self.use_arc_to_chord_error = self._get_bool_value(value)
                            elif i.lower().startswith("arctochorderror"):
                                self.arc_to_chord_error = value
                            elif i.lower().startswith("defeatureabsLength"):
                                self.defeature_abs_length = value
                            elif i.lower().startswith("defeaturelayout"):
                                self.defeature_layout = self._get_bool_value(value)
                            elif i.lower().startswith("minimumvoidsurface"):
                                self.minimum_void_surface = float(value)
                            elif i.lower().startswith("maxsurfdev"):
                                self.max_suf_dev = float(value)
                            elif i.lower().startswith("processpadstackdefinitions"):
                                self.process_padstack_definitions = self._get_bool_value(value)
                            elif i.lower().startswith("returncurrentdistribution"):
                                self.return_current_distribution = self._get_bool_value(value)
                            elif i.lower().startswith("ignorenonfunctionalpads"):
                                self.ignore_non_functional_pads = self._get_bool_value(value)
                            elif i.lower().startswith("includeinterplanecoupling"):
                                self.include_inter_plane_coupling = self._get_bool_value(value)
                            elif i.lower().startswith("xtalkthreshold"):
                                self.xtalk_threshold = float(value)
                            elif i.lower().startswith("minvoidarea"):
                                self.min_void_area = value
                            elif i.lower().startswith("minpadareatomesh"):
                                self.min_pad_area_to_mesh = value
                            elif i.lower().startswith("snaplengththreshold"):
                                self.snap_length_threshold = value
                            elif i.lower().startswith("minplaneareatomesh"):
                                self.min_plane_area_to_mesh = value
                            elif i.lower().startswith("dcminplaneareatomesh"):
                                self.dc_min_plane_area_to_mesh = value
                            elif i.lower().startswith("maxinitmeshedgelength"):
                                self.max_init_mesh_edge_length = value
                            elif i.lower().startswith("signallayersproperties"):
                                self._parse_signal_layer_properties = value[1:-1] if value[0] == "[" else value
                                self._parse_signal_layer_properties = [
                                    item.strip() for item in self._parse_signal_layer_properties
                                ]
                            elif i.lower().startswith("coplanar_instances"):
                                self.coplanar_instances = value[1:-1] if value[0] == "[" else value
                                self.coplanar_instances = [item.strip() for item in self.coplanar_instances]
                            elif i.lower().startswith("signallayersetching"):
                                self.signal_layer_etching_instances = value[1:-1] if value[0] == "[" else value
                                self.signal_layer_etching_instances = [
                                    item.strip() for item in self.signal_layer_etching_instances
                                ]
                            elif i.lower().startswith("etchingfactor"):
                                self.etching_factor_instances = value[1:-1] if value[0] == "[" else value
                                self.etching_factor_instances = [item.strip() for item in self.etching_factor_instances]
                            elif i.lower().startswith("docutoutsubdesign"):
                                self.do_cutout_subdesign = self._get_bool_value(value)
                            elif i.lower().startswith("solvertype"):
                                if value.lower() == "hfss":
                                    self.solver_type = 0
                                if value.lower() == "hfss3dlayout":
                                    self.solver_type = 6
                                elif value.lower().startswith("siwavesyz"):
                                    self.solver_type = 7
                                elif value.lower().startswith("siwavedc"):
                                    self.solver_type = 8
                                elif value.lower().startswith("q3d"):
                                    self.solver_type = 2
                                elif value.lower().startswith("nexxim"):
                                    self.solver_type = 4
                                elif value.lower().startswith("maxwell"):
                                    self.solver_type = 3
                                elif value.lower().startswith("twinbuilder"):
                                    self.solver_type = 5
                                else:
                                    self.solver_type = SolverType.Hfss3dLayout
                        else:
                            print("Unprocessed line in cfg file: {0}".format(line))
                    else:
                        continue
        except EnvironmentError as e:
            print("Error reading cfg file: {}".format(e.message))
            raise

    def _dict_to_json(self, dict_out, dict_in=None):
        exclude = ["_pedb", "SOLVER_TYPE"]
        for k, v in dict_in.items():
            if k in exclude:
                continue
            if k[0] == "_":
                if k[1:] in ["dc_settings", "ac_settings", "batch_solve_settings"]:
                    dict_out[k[1:]] = {}
                    dict_out[k[1:]] = self._dict_to_json(dict_out[k[1:]], self.__getattr__(k).__dict__)
                elif k == "_sources":
                    sources_out = [src._json_format() for src in v]
                    dict_out[k[1:]] = sources_out
                elif k == "_dc_source_terms_to_ground":
                    dc_term_gnd = {}
                    for k2 in list(v.Keys):  # pragma: no cover
                        dc_term_gnd[k2] = v[k2]
                    dict_out[k[1:]] = dc_term_gnd
                else:
                    dict_out[k[1:]] = v
            else:
                dict_out[k] = v
        return dict_out

    def _json_to_dict(self, json_dict):
        for k, v in json_dict.items():
            if k == "sources":
                for src in json_dict[k]:  # pragma: no cover
                    source = Source()
                    source._read_json(src)
                    self.batch_solve_settings.sources.append(source)
            elif k == "dc_source_terms_to_ground":
                dc_term_gnd = Dictionary[str, int]()
                for k1, v1 in json_dict[k]:  # pragma: no cover
                    dc_term_gnd[k1] = v1
                self.dc_source_terms_to_ground = dc_term_gnd
            elif k in ["dc_settings", "ac_settings", "batch_solve_settings"]:
                self._json_to_dict(v)
            else:
                self.__setattr__(k, v)

    @pyaedt_function_handler()
    def export_json(self, output_file):
        """Export Json file from SimulationConfiguration object.

        Parameters
        ----------
        output_file : str
            Json file name.

        Returns
        -------
        bool
            True when succeeded False when file name not provided.

        Examples
        --------

        >>> from pyaedt.edb_core.edb_data.simulation_configuration import SimulationConfiguration
        >>> config = SimulationConfiguration()
        >>> config.export_json(r"C:\Temp\test_json\test.json")
        """
        dict_out = {}
        dict_out = self._dict_to_json(dict_out, self.__dict__)
        if output_file:
            with open(output_file, "w") as write_file:
                json.dump(dict_out, write_file, indent=4)
            return True
        else:
            return False

    @pyaedt_function_handler()
    def import_json(self, input_file):
        """Import Json file into SimulationConfiguration object instance.

        Parameters
        ----------
        input_file : str
            Json file name.

        Returns
        -------
        bool
            True when succeeded False when file name not provided.

        Examples
        --------
        >>> from pyaedt.edb_core.edb_data.simulation_configuration import SimulationConfiguration
        >>> test = SimulationConfiguration()
        >>> test.import_json(r"C:\Temp\test_json\test.json")
        """
        if input_file:
            f = open(input_file)
            json_dict = json.load(f)  # pragma: no cover
            self._json_to_dict(json_dict)
            self.filename = input_file
            return True
        else:
            return False

    @pyaedt_function_handler()
    def add_voltage_source(
        self,
        name="",
        voltage_value=1,
        phase_value=0,
        impedance=1e-6,
        positive_node_component="",
        positive_node_net="",
        negative_node_component="",
        negative_node_net="",
    ):
        """Add a voltage source for the current SimulationConfiguration instance.

        Parameters
        ----------
        name : str
            Source name.

        voltage_value : float
            Amplitude value of the source. Either amperes for current source or volts for
            voltage source.

        phase_value : float
            Phase value of the source.

        impedance : float
            Impedance value of the source.

        positive_node_component : str
            Name of the component used for the positive node.

        negative_node_component : str
            Name of the component used for the negative node.

        positive_node_net : str
            Net used for the positive node.

        negative_node_net : str
            Net used for the negative node.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------
        >>> edb = Edb(target_file)
        >>> sim_setup = SimulationConfiguration()
        >>> sim_setup.add_voltage_source(voltage_value=1.0, phase_value=0, positive_node_component="V1",
        >>> positive_node_net="HSG", negative_node_component="V1", negative_node_net="SW")

        """
        if name == "":  # pragma: no cover
            name = generate_unique_name("v_source")
        source = Source()
        source.source_type = SourceType.Vsource
        source.name = name
        source.amplitude = voltage_value
        source.phase = phase_value
        source.positive_node.component = positive_node_component
        source.positive_node.net = positive_node_net
        source.negative_node.component = negative_node_component
        source.negative_node.net = negative_node_net
        source.impedance_value = impedance
        try:  # pragma: no cover
            self.sources.append(source)
            return True
        except:  # pragma: no cover
            return False

    @pyaedt_function_handler()
    def add_current_source(
        self,
        name="",
        current_value=0.1,
        phase_value=0,
        impedance=5e7,
        positive_node_component="",
        positive_node_net="",
        negative_node_component="",
        negative_node_net="",
    ):
        """Add a current source for the current SimulationConfiguration instance.

        Parameters
        ----------
        name : str
            Source name.

        current_value : float
            Amplitude value of the source. Either amperes for current source or volts for
            voltage source.

        phase_value : float
            Phase value of the source.

        impedance : float
            Impedance value of the source.

        positive_node_component : str
            Name of the component used for the positive node.

        negative_node_component : str
            Name of the component used for the negative node.

        positive_node_net : str
            Net used for the positive node.

        negative_node_net : str
            Net used for the negative node.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------
        >>> edb = Edb(target_file)
        >>> sim_setup = SimulationConfiguration()
        >>> sim_setup.add_voltage_source(voltage_value=1.0, phase_value=0, positive_node_component="V1",
        >>> positive_node_net="HSG", negative_node_component="V1", negative_node_net="SW")
        """

        if name == "":  # pragma: no cover
            name = generate_unique_name("I_source")
        source = Source()
        source.source_type = SourceType.Isource
        source.name = name
        source.amplitude = current_value
        source.phase = phase_value
        source.positive_node.component = positive_node_component
        source.positive_node.net = positive_node_net
        source.negative_node.component = negative_node_component
        source.negative_node.net = negative_node_net
        source.impedance_value = impedance
        try:  # pragma: no cover
            self.sources.append(source)
            return True
        except:  # pragma: no cover
            return False

    @pyaedt_function_handler()
    def add_rlc(
        self,
        name="",
        r_value=1.0,
        c_value=0.0,
        l_value=0.0,
        positive_node_component="",
        positive_node_net="",
        negative_node_component="",
        negative_node_net="",
        create_physical_rlc=True,
    ):
        """Add a voltage source for the current SimulationConfiguration instance.

        Parameters
        ----------
        name : str
            Source name.

        r_value : float
            Resistor value in Ohms.

        l_value : float
            Inductance value in Henry.

        c_value : float
            Capacitance value in Farrad.

        positive_node_component : str
            Name of the component used for the positive node.

        negative_node_component : str
            Name of the component used for the negative node.

        positive_node_net : str
            Net used for the positive node.

        negative_node_net : str
            Net used for the negative node.

        create_physical_rlc : bool
            When True create a physical Rlc component. Recommended setting to True to be compatible with Siwave.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------
        >>> edb = Edb(target_file)
        >>> sim_setup = SimulationConfiguration()
        >>> sim_setup.add_voltage_source(voltage_value=1.0, phase_value=0, positive_node_component="V1",
        >>> positive_node_net="HSG", negative_node_component="V1", negative_node_net="SW")
        """

        if name == "":  # pragma: no cover
            name = generate_unique_name("Rlc")
        source = Source()
        source.source_type = SourceType.Rlc
        source.name = name
        source.r_value = r_value
        source.l_value = l_value
        source.c_value = c_value
        source.create_physical_resistor = create_physical_rlc
        source.positive_node.component = positive_node_component
        source.positive_node.net = positive_node_net
        source.negative_node.component = negative_node_component
        source.negative_node.net = negative_node_net
        try:  # pragma: no cover
            self.sources.append(source)
            return True
        except:  # pragma: no cover
            return False
