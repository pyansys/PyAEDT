import copy
import os
import re
import sys

from pyaedt.aedt_logger import pyaedt_logger
from pyaedt.generic.general_methods import ET, env_path, env_value, is_ironpython, is_linux, pyaedt_function_handler
from pyaedt.misc import list_installed_ansysem
from pyaedt.misc.aedtlib_personalib_install import write_pretty_xml

if is_linux and is_ironpython:
    import subprocessdotnet as subprocess
else:
    import subprocess


@pyaedt_function_handler()
def convert_technology_file(tech_file, edbversion=None, control_file=None):
    """Convert a technology file to edb control file (xml).

    Parameters
    ----------
    tech_file : str
        Full path to technology file
    edbversion : str,  optional
            Edb version to use. Default is `None` to use latest available version of Edb.
    control_file : str,  optional
            Control file output file. Default is `None` to use same path and same name of `tech_file`.

    Returns
    -------
    str
        Control file full path if created.
    """
    if is_linux:  # pragma: no cover
        if not edbversion:
            edbversion = "20{}.{}".format(list_installed_ansysem()[0][-3:-1], list_installed_ansysem()[0][-1:])
        if env_value(edbversion) in os.environ:
            base_path = env_path(edbversion)
            sys.path.append(base_path)
        else:
            pyaedt_logger.error("No Edb installation found. Check environment variables")
            return False
        os.environ["HELIC_ROOT"] = os.path.join(base_path, "helic")
        if os.getenv("ANSYSLMD_LICENCE_FILE", None) is None:
            lic = os.path.join(base_path, "..", "..", "shared_files", "licensing", "ansyslmd.ini")
            if os.path.exists(lic):
                with open(lic, "r") as fh:
                    lines = fh.read().splitlines()
                    for line in lines:
                        if line.startswith("SERVER="):
                            os.environ["ANSYSLMD_LICENSE_FILE"] = line.split("=")[1]
                            break
            else:
                pyaedt_logger.error("ANSYSLMD_LICENSE_FILE is not defined.")
        vlc_file_name = os.path.splitext(tech_file)[0]
        if not control_file:
            control_file = vlc_file_name + ".xml"
        vlc_file = vlc_file_name + ".vlc.tech"
        commands = []
        command = [
            os.path.join(base_path, "helic", "tools", "bin", "afet", "tech2afet"),
            "-i",
            tech_file,
            "-o",
            vlc_file,
            "--backplane",
            "False",
        ]
        commands.append(command)
        command = [
            os.path.join(base_path, "helic", "tools", "raptorh", "bin", "make-edb"),
            "--dielectric-simplification-method",
            "1",
            "-t",
            vlc_file,
            "-o",
            vlc_file_name,
            "--export-xml",
            control_file,
        ]
        commands.append(command)
        commands.append(["rm", "-r", vlc_file_name + ".aedb"])
        my_env = os.environ.copy()
        for command in commands:
            p = subprocess.Popen(command, env=my_env)
            p.wait()
        if os.path.exists(control_file):
            pyaedt_logger.info("Xml file created.")
            return control_file
    pyaedt_logger.error("Technology files are supported only in Linux. Use control file instead.")
    return False


class ControlProperty:
    def __init__(self, property_name, value):
        self.name = property_name
        self.value = value
        if isinstance(value, str):
            self.type = 1
        elif isinstance(value, list):
            self.type = 2
        else:
            try:
                float(value)
                self.type = 0
            except TypeError:
                pass

    def _write_xml(self, root):
        try:
            if self.type == 0:
                content = ET.SubElement(root, self.name)
                double = ET.SubElement(content, "Double")
                double.text = str(self.value)
            else:
                pass
        except:
            pass


class ControlFileMaterial:
    def __init__(self, name, properties):
        self.name = name
        self.properties = {}
        for name, property in properties.items():
            self.properties[name] = ControlProperty(name, property)

    def _write_xml(self, root):
        content = ET.SubElement(root, "Material")
        content.set("Name", self.name)
        for property_name, property in self.properties.items():
            property._write_xml(content)


class ControlFileDielectric:
    def __init__(self, name, properties):
        self.name = name
        self.properties = {}
        for name, prop in properties.items():
            self.properties[name] = prop

    def _write_xml(self, root):
        content = ET.SubElement(root, "Layer")
        for property_name, property in self.properties.items():
            if not property_name == "Index":
                content.set(property_name, str(property))


class ControlFileLayer:
    def __init__(self, name, properties):
        self.name = name
        self.properties = {}
        for name, prop in properties.items():
            self.properties[name] = prop

    def _write_xml(self, root):
        content = ET.SubElement(root, "Layer")
        content.set("Color", self.properties.get("Color", "#5c4300"))
        if self.properties.get("Elevation"):
            content.set("Elevation", self.properties["Elevation"])
        if self.properties.get("GDSDataType"):
            content.set("GDSDataType", self.properties["GDSDataType"])
        if self.properties.get("GDSIIVia") or self.properties.get("GDSDataType"):
            content.set("GDSIIVia", self.properties.get("GDSIIVia", "false"))
        if self.properties.get("Material"):
            content.set("Material", self.properties.get("Material", "air"))
        content.set("Name", self.name)
        if self.properties.get("StartLayer"):
            content.set("StartLayer", self.properties["StartLayer"])
        if self.properties.get("StopLayer"):
            content.set("StopLayer", self.properties["StopLayer"])
        if self.properties.get("TargetLayer"):
            content.set("TargetLayer", self.properties["TargetLayer"])
        if self.properties.get("Thickness"):
            content.set("Thickness", self.properties.get("Thickness", "0.001"))
        if self.properties.get("Type"):
            content.set("Type", self.properties.get("Type", "conductor"))


class ControlFileVia(ControlFileLayer):
    def __init__(self, name, properties):
        ControlFileLayer.__init__(self, name, properties)
        self.create_via_group = False
        self.check_containment = True
        self.method = "proximity"
        self.persistent = False
        self.tolerance = "1um"
        self.snap_via_groups = False
        self.snap_method = "areaFactor"
        self.remove_unconnected = True
        self.snap_tolerance = 3

    def _write_xml(self, root):
        content = ET.SubElement(root, "Layer")
        content.set("Color", self.properties.get("Color", "#5c4300"))
        if self.properties.get("Elevation"):
            content.set("Elevation", self.properties["Elevation"])
        if self.properties.get("GDSDataType"):
            content.set("GDSDataType", self.properties["GDSDataType"])
        if self.properties.get("Material"):
            content.set("Material", self.properties.get("Material", "air"))
        content.set("Name", self.name)
        content.set("StartLayer", self.properties.get("StartLayer", ""))
        content.set("StopLayer", self.properties.get("StopLayer", ""))
        if self.properties.get("TargetLayer"):
            content.set("TargetLayer", self.properties["TargetLayer"])
        if self.properties.get("Thickness"):
            content.set("Thickness", self.properties.get("Thickness", "0.001"))
        if self.properties.get("Type"):
            content.set("Type", self.properties.get("Type", "conductor"))
        if self.create_via_group:
            viagroup = ET.SubElement(content, "CreateViaGroups")
            viagroup.set("CheckContainment", "true" if self.check_containment else "false")
            viagroup.set("Method", self.method)
            viagroup.set("Persistent", "true" if self.persistent else "false")
            viagroup.set("Tolerance", self.tolerance)
        if self.snap_via_groups:
            snapgroup = ET.SubElement(content, "SnapViaGroups")
            snapgroup.set("Method", self.snap_method)
            snapgroup.set("RemoveUnconnected", "true" if self.remove_unconnected else "false")
            snapgroup.set("Tolerance", str(self.snap_tolerance))


class ControlFileStackup:
    """Class that manages the Stackup info."""

    def __init__(self, units="mm"):
        self._materials = {}
        self._layers = []
        self._dielectrics = []
        self._vias = []
        self.units = units
        self.metal_layer_snapping_tolerance = None
        self.dielectrics_base_elevation = 0

    @property
    def vias(self):
        """Via list.

        Returns
        -------
        list of :class:`pyaedt.edb_core.edb_data.control_file.ControlFileVia`

        """
        return self._vias

    @property
    def materials(self):
        """Material list.

        Returns
        -------
        list of :class:`pyaedt.edb_core.edb_data.control_file.ControlFileMaterial`

        """
        return self._materials

    @property
    def dielectrics(self):
        """Dielectric layer list.

        Returns
        -------
        list of :class:`pyaedt.edb_core.edb_data.control_file.ControlFileLayer`

        """
        return self._dielectrics

    @property
    def layers(self):
        """Layer list.

        Returns
        -------
        list of :class:`pyaedt.edb_core.edb_data.control_file.ControlFileLayer`

        """
        return self._layers

    def add_material(
        self,
        material_name,
        permittivity=1.0,
        dielectric_loss_tg=0.0,
        permeability=1.0,
        conductivity=0.0,
        properties=None,
    ):
        """Add a new material with specific properties.

        Parameters
        ----------
        material_name : str
            Material name.
        permittivity : float, optional
            Material permittivity. The default is ``1.0``.
        dielectric_loss_tg : float, optional
            Material tangent losses. The default is ``0.0``.
        permeability : float, optional
            Material permeability. The default is ``1.0``.
        conductivity : float, optional
            Material conductivity. The default is ``0.0``.
        properties : dict, optional
            Specific material properties. The default is ``None``.
            Dictionary with key and material property value.

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.control_file.ControlFileMaterial`
        """
        if isinstance(properties, dict):
            self._materials[material_name] = ControlFileMaterial(material_name, properties)
            return self._materials[material_name]
        else:
            properties = {
                "Name": material_name,
                "Permittivity": permittivity,
                "Permeability": permeability,
                "Conductivity": conductivity,
                "DielectricLossTangent": dielectric_loss_tg,
            }
            self._materials[material_name] = ControlFileMaterial(material_name, properties)
            return self._materials[material_name]

    def add_layer(
        self,
        layer_name,
        elevation=0.0,
        material="",
        gds_type=0,
        target_layer="",
        thickness=0.0,
        layer_type="conductor",
        solve_inside=True,
        properties=None,
    ):
        """Add a new layer.

        Parameters
        ----------
        layer_name : str
            Layer name.
        elevation : float
            Layer elevation.
        material : str
            Material for the layer.
        gds_type : int
            GDS type assigned on the layer. The value must be the same as in the GDS file otherwise geometries won't be
            imported.
        target_layer : str
            Layer name assigned in EDB or HFSS 3D layout after import.
        thickness : float
            Layer thickness
        layer_type : str
            Define the layer type, default value for a layer is ``"conductor"``
        solve_inside : bool
            When ``True`` solver will solve inside metal, and not id ``False``. Default value is ``True``.
        properties : dict
            Dictionary with key and  property value.

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.control_file.ControlFileLayer`
        """
        if isinstance(properties, dict):
            self._layers.append(ControlFileLayer(layer_name, properties))
            return self._layers[-1]
        else:
            properties = {
                "Name": layer_name,
                "GDSDataType": str(gds_type),
                "TargetLayer": target_layer,
                "Type": layer_type,
                "Material": material,
                "Thickness": str(thickness),
                "Elevation": str(elevation),
                "SolveInside": str(solve_inside).lower(),
            }
            self._layers.append(ControlFileDielectric(layer_name, properties))
            return self._layers[-1]

    def add_dielectric(
        self,
        layer_name,
        layer_index=None,
        material="",
        thickness=0.0,
        properties=None,
        base_layer=None,
        add_on_top=True,
    ):
        """Add a new dielectric.

        Parameters
        ----------
        layer_name : str
            Layer name.
        layer_index : int, optional
            Dielectric layer index as they must be stacked. If not provided the layer index will be incremented.
        material : str
            Material name.
        thickness : float
            Layer thickness.
        properties : dict
            Dictionary with key and  property value.
        base_layer : str,  optional
            Layer name used for layer placement. Default value is ``None``. This option is used for inserting
            dielectric layer between two existing ones. When no argument is provided the dielectric layer will be placed
            on top of the stacked ones.
        method : bool, Optional.
            Provides the method to use when the argument ``base_layer`` is provided. When ``True`` the layer is added
            on top on the base layer, when ``False`` it will be added below.

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.control_file.ControlFileDielectric`
        """
        if isinstance(properties, dict):
            self._dielectrics.append(ControlFileDielectric(layer_name, properties))
            return self._dielectrics[-1]
        else:
            if not layer_index and self.dielectrics and not base_layer:
                layer_index = max([diel.properties["Index"] for diel in self.dielectrics]) + 1
            elif base_layer and self.dielectrics:
                if base_layer in [diel.properties["Name"] for diel in self.dielectrics]:
                    base_layer_index = next(
                        diel.properties["Index"] for diel in self.dielectrics if diel.properties["Name"] == base_layer
                    )
                    if add_on_top:
                        layer_index = base_layer_index + 1
                        for diel_layer in self.dielectrics:
                            if diel_layer.properties["Index"] > base_layer_index:
                                diel_layer.properties["Index"] += 1
                    else:
                        layer_index = base_layer_index
                        for diel_layer in self.dielectrics:
                            if diel_layer.properties["Index"] >= base_layer_index:
                                diel_layer.properties["Index"] += 1
            elif not layer_index:
                layer_index = 0
            properties = {"Index": layer_index, "Material": material, "Name": layer_name, "Thickness": thickness}
            self._dielectrics.append(ControlFileDielectric(layer_name, properties))
            return self._dielectrics[-1]

    def add_via(
        self,
        layer_name,
        material="",
        gds_type=0,
        target_layer="",
        start_layer="",
        stop_layer="",
        solve_inside=True,
        via_group_method="proximity",
        via_group_tol=1e-6,
        via_group_persistent=True,
        snap_via_group_method="distance",
        snap_via_group_tol=10e-9,
        properties=None,
    ):
        """Add a new via layer.

        Parameters
        ----------
        layer_name : str
            Layer name.
        material : str
            Define the material for this layer.
        gds_type : int
            Define the gds type.
        target_layer : str
            Target layer used after layout import in EDB and HFSS 3D layout.
        start_layer : str
            Define the start layer for the via
        stop_layer : str
            Define the stop layer for the via.
        solve_inside : bool
            When ``True`` solve inside this layer is anbled. Default value is ``True``.
        via_group_method : str
            Define the via group method, default value is ``"proximity"``
        via_group_tol : float
            Define the via group tolerance.
        via_group_persistent : bool
            When ``True`` activated otherwise when ``False``is deactivated. Default value is ``True``.
        snap_via_group_method : str
            Define the via group method, default value is ``"distance"``
        snap_via_group_tol : float
            Define the via group tolerance, default value is 10e-9.
        properties : dict
            Dictionary with key and  property value.

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.control_file.ControlFileVia`
        """
        if isinstance(properties, dict):
            self._vias.append(ControlFileVia(layer_name, properties))
            return self._vias[-1]
        else:
            properties = {
                "Name": layer_name,
                "GDSDataType": str(gds_type),
                "TargetLayer": target_layer,
                "Material": material,
                "StartLayer": start_layer,
                "StopLayer": stop_layer,
                "SolveInside": str(solve_inside).lower(),
                "ViaGroupMethod": via_group_method,
                "Persistent": via_group_persistent,
                "ViaGroupTolerance": via_group_tol,
                "SnapViaGroupMethod": snap_via_group_method,
                "SnapViaGroupTolerance": snap_via_group_tol,
            }
            self._vias.append(ControlFileVia(layer_name, properties))
            return self._vias[-1]

    def _write_xml(self, root):
        content = ET.SubElement(root, "Stackup")
        content.set("schemaVersion", "1.0")
        materials = ET.SubElement(content, "Materials")
        for materialname, material in self.materials.items():
            material._write_xml(materials)
        elayers = ET.SubElement(content, "ELayers")
        elayers.set("LengthUnit", self.units)
        if self.metal_layer_snapping_tolerance:
            elayers.set("MetalLayerSnappingTolerance", str(self.metal_layer_snapping_tolerance))
        dielectrics = ET.SubElement(elayers, "Dielectrics")
        dielectrics.set("BaseElevation", str(self.dielectrics_base_elevation))
        # sorting dielectric layers
        self._dielectrics = list(sorted(list(self._dielectrics), key=lambda x: x.properties["Index"], reverse=False))
        for layer in self.dielectrics:
            layer._write_xml(dielectrics)
        layers = ET.SubElement(elayers, "Layers")

        for layer in self.layers:
            layer._write_xml(layers)
        vias = ET.SubElement(elayers, "Vias")

        for layer in self.vias:
            layer._write_xml(vias)


class ControlFileImportOptions:
    """Import Options."""

    def __init__(self):
        self.auto_close = False
        self.convert_closed_wide_lines_to_polys = False
        self.round_to = 0
        self.defeature_tolerance = 0.0
        self.flatten = True
        self.enable_default_component_values = True
        self.import_dummy_nets = False
        self.gdsii_convert_polygon_to_circles = False
        self.import_cross_hatch_shapes_as_lines = True
        self.max_antipad_radius = 0.0
        self.extracta_use_pin_names = False
        self.min_bondwire_width = 0.0
        self.antipad_repalce_radius = 0.0
        self.gdsii_scaling_factor = 0.0
        self.delte_empty_non_laminate_signal_layers = False

    def _write_xml(self, root):
        content = ET.SubElement(root, "ImportOptions")
        content.set("AutoClose", str(self.auto_close).lower())
        if self.round_to != 0:
            content.set("RoundTo", str(self.round_to))
        if self.defeature_tolerance != 0.0:
            content.set("DefeatureTolerance", str(self.defeature_tolerance))
        content.set("Flatten", str(self.flatten).lower())
        content.set("EnableDefaultComponentValues", str(self.enable_default_component_values).lower())
        content.set("ImportDummyNet", str(self.import_dummy_nets).lower())
        content.set("GDSIIConvertPolygonToCircles", str(self.convert_closed_wide_lines_to_polys).lower())
        content.set("ImportCrossHatchShapesAsLines", str(self.import_cross_hatch_shapes_as_lines).lower())
        content.set("ExtractaUsePinNames", str(self.extracta_use_pin_names).lower())
        if self.max_antipad_radius != 0.0:
            content.set("MaxAntiPadRadius", str(self.max_antipad_radius))
        if self.antipad_repalce_radius != 0.0:
            content.set("AntiPadReplaceRadius", str(self.antipad_repalce_radius))
        if self.min_bondwire_width != 0.0:
            content.set("MinBondwireWidth", str(self.min_bondwire_width))
        if self.gdsii_scaling_factor != 0.0:
            content.set("GDSIIScalingFactor", str(self.gdsii_scaling_factor))
        content.set("DeleteEmptyNonLaminateSignalLayers", str(self.delte_empty_non_laminate_signal_layers).lower())


class ControlExtent:
    """Extent options."""

    def __init__(
        self,
        type="bbox",
        dieltype="bbox",
        diel_hactor=0.25,
        airbox_hfactor=0.25,
        airbox_vr_p=0.25,
        airbox_vr_n=0.25,
        useradiation=True,
        honor_primitives=True,
        truncate_at_gnd=True,
    ):
        self.type = type
        self.dieltype = dieltype
        self.diel_hactor = diel_hactor
        self.airbox_hfactor = airbox_hfactor
        self.airbox_vr_p = airbox_vr_p
        self.airbox_vr_n = airbox_vr_n
        self.useradiation = useradiation
        self.honor_primitives = honor_primitives
        self.truncate_at_gnd = truncate_at_gnd

    def _write_xml(self, root):
        content = ET.SubElement(root, "Extents")
        content.set("Type", self.type)
        content.set("DielType", self.dieltype)
        content.set("DielHorizFactor", str(self.diel_hactor))
        content.set("AirboxHorizFactor", str(self.airbox_hfactor))
        content.set("AirboxVertFactorPos", str(self.airbox_vr_p))
        content.set("AirboxVertFactorNeg", str(self.airbox_vr_n))
        content.set("UseRadiationBoundary", str(self.useradiation).lower())
        content.set("DielHonorPrimitives", str(self.honor_primitives).lower())
        content.set("AirboxTruncateAtGround", str(self.truncate_at_gnd).lower())


class ControlCircuitPt:
    """Circuit Port."""

    def __init__(self, name, x1, y1, lay1, x2, y2, lay2, z0):
        self.name = name
        self.x1 = x1
        self.x2 = x2
        self.lay1 = lay1
        self.lay2 = lay2
        self.y1 = y1
        self.y2 = y2
        self.z0 = z0

    def _write_xml(self, root):
        content = ET.SubElement(root, "CircuitPortPt")
        content.set("Name", self.name)
        content.set("x1", self.x1)
        content.set("y1", self.y1)
        content.set("Layer1", self.lay1)
        content.set("x2", self.x2)
        content.set("y2", self.y2)
        content.set("Layer2", self.lay2)
        content.set("Z0", self.z0)


class ControlFileComponent:
    """Components."""

    def __init__(self):
        self.refdes = "U1"
        self.partname = "BGA"
        self.parttype = "IC"
        self.die_type = "None"
        self.die_orientation = "Chip down"
        self.solderball_shape = "None"
        self.solder_diameter = "65um"
        self.solder_height = "65um"
        self.solder_material = "solder"
        self.pins = []
        self.ports = []

    def add_pin(self, name, x, y, layer):
        self.pins.append({"Name": name, "x": x, "y": y, "Layer": layer})

    def add_port(self, name, z0, pospin, refpin=None, pos_type="pin", ref_type="pin"):
        args = {"Name": name, "Z0": z0}
        if pos_type == "pin":
            args["PosPin"] = pospin
        elif pos_type == "pingroup":
            args["PosPinGroup"] = pospin
        if refpin:
            if ref_type == "pin":
                args["RefPin"] = refpin
            elif ref_type == "pingroup":
                args["RefPinGroup"] = refpin
            elif ref_type == "net":
                args["RefNet"] = refpin
        self.ports.append(args)

    def _write_xml(self, root):
        content = ET.SubElement(root, "GDS_COMPONENT")
        for p in self.pins:
            prop = ET.SubElement(content, "GDS_PIN")
            for pname, value in p.items():
                prop.set(pname, value)

        prop = ET.SubElement(content, "Component")
        prop.set("RefDes", self.refdes)
        prop.set("PartName", self.partname)
        prop.set("PartType", self.parttype)
        prop2 = ET.SubElement(prop, "DieProperties")
        prop2.set("Type", self.die_type)
        prop2.set("Orientation", self.die_orientation)
        prop2 = ET.SubElement(prop, "SolderballProperties")
        prop2.set("Shape", self.solderball_shape)
        prop2.set("Diameter", self.solder_diameter)
        prop2.set("Height", self.solder_height)
        prop2.set("Material", self.solder_material)
        for p in self.ports:
            prop = ET.SubElement(prop, "ComponentPort")
            for pname, value in p.items():
                prop.set(pname, value)


class ControlFileComponents:
    """Class for component management."""

    def __init__(self):
        self.units = "um"
        self.components = []

    def add_component(self, ref_des, partname, component_type, die_type="None", solderball_shape="None"):
        """Create a new component.

        Parameters
        ----------
        ref_des : str
            Reference Designator name.
        partname : str
            Part name.
        component_type : str
            Component Type. Can be `"IC"`, `"IO"` or `"Other"`.
        die_type : str, optional
            Die Type. Can be `"None"`, `"Flip chip"` or `"Wire bond"`.
        solderball_shape : str, optional
            Solderball Type. Can be `"None"`, `"Cylinder"` or `"Spheroid"`.

        Returns
        -------

        """
        comp = ControlFileComponent()
        comp.refdes = ref_des
        comp.partname = partname
        comp.parttype = component_type
        comp.die_type = die_type
        comp.solderball_shape = solderball_shape
        self.components.append(comp)
        return comp


class ControlFileBoundaries:
    """Boundaries management."""

    def __init__(self, units="um"):
        self.ports = {}
        self.extents = []
        self.circuit_models = {}
        self.circuit_elements = {}
        self.units = units

    def add_port(self, name, x1, y1, layer1, x2, y2, layer2, z0=50):
        """Add a new port to the gds.

        Parameters
        ----------
        name : str
            Port name.
        x1 : str
            Pin 1 x position.
        y1 : str
            Pin 1 y position.
        layer1 : str
            Pin 1 layer.
        x2 : str
            Pin 2 x position.
        y2 : str
            Pin 2 y position.
        layer2 : str
            Pin 2 layer.
        z0 : str
            Characteristic impedance.

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.control_file.ControlCircuitPt`
        """
        self.ports[name] = ControlCircuitPt(name, str(x1), str(y1), layer1, str(x2), str(y2), layer2, str(z0))
        return self.ports[name]

    def add_extent(
        self,
        type="bbox",
        dieltype="bbox",
        diel_hactor=0.25,
        airbox_hfactor=0.25,
        airbox_vr_p=0.25,
        airbox_vr_n=0.25,
        useradiation=True,
        honor_primitives=True,
        truncate_at_gnd=True,
    ):
        """Add a new extent.

        Parameters
        ----------
        type
        dieltype
        diel_hactor
        airbox_hfactor
        airbox_vr_p
        airbox_vr_n
        useradiation
        honor_primitives
        truncate_at_gnd

        Returns
        -------

        """
        self.extents.append(
            ControlExtent(
                type=type,
                dieltype=dieltype,
                diel_hactor=diel_hactor,
                airbox_hfactor=airbox_hfactor,
                airbox_vr_p=airbox_vr_p,
                airbox_vr_n=airbox_vr_n,
                useradiation=useradiation,
                honor_primitives=honor_primitives,
                truncate_at_gnd=truncate_at_gnd,
            )
        )
        return self.extents[-1]

    def _write_xml(self, root):
        content = ET.SubElement(root, "Boundaries")
        content.set("LengthUnit", self.units)
        for p in self.circuit_models.values():
            p._write_xml(content)
        for p in self.circuit_elements.values():
            p._write_xml(content)
        for p in self.ports.values():
            p._write_xml(content)
        for p in self.extents:
            p._write_xml(content)


class ControlFileSweep:
    def __init__(self, name, start, stop, step, sweep_type, step_type, use_q3d):
        self.name = name
        self.start = start
        self.stop = stop
        self.step = step
        self.sweep_type = sweep_type
        self.step_type = step_type
        self.use_q3d = use_q3d

    def _write_xml(self, root):
        sweep = ET.SubElement(root, "FreqSweep")
        prop = ET.SubElement(sweep, "Name")
        prop.text = self.name
        prop = ET.SubElement(sweep, "UseQ3DForDC")
        prop.text = str(self.use_q3d).lower()
        prop = ET.SubElement(sweep, self.sweep_type)
        prop2 = ET.SubElement(prop, self.step_type)
        prop3 = ET.SubElement(prop2, "Start")
        prop3.text = self.start
        prop3 = ET.SubElement(prop2, "Stop")
        prop3.text = self.stop
        if self.step_type == "LinearStep":
            prop3 = ET.SubElement(prop2, "Step")
            prop3.text = str(self.step)
        else:
            prop3 = ET.SubElement(prop2, "Count")
            prop3.text = str(self.step)


class ControlFileMeshOp:
    def __init__(self, name, region, type, nets_layers):
        self.name = name
        self.region = name
        self.type = type
        self.nets_layers = nets_layers
        self.num_max_elem = 1000
        self.restrict_elem = False
        self.restrict_length = True
        self.max_length = "20um"
        self.skin_depth = "1um"
        self.surf_tri_length = "1mm"
        self.num_layers = 2
        self.region_solve_inside = False

    def _write_xml(self, root):
        mop = ET.SubElement(root, "MeshOperation")
        prop = ET.SubElement(mop, "Name")
        prop.text = self.name
        prop = ET.SubElement(mop, "Enabled")
        prop.text = "true"
        prop = ET.SubElement(mop, "Region")
        prop.text = self.region
        prop = ET.SubElement(mop, "Type")
        prop.text = self.type
        prop = ET.SubElement(mop, "NetsLayers")
        for net, layer in self.nets_layers.items():
            prop2 = ET.SubElement(prop, "NetsLayer")
            prop3 = ET.SubElement(prop2, "Net")
            prop3.text = net
            prop3 = ET.SubElement(prop2, "Layer")
            prop3.text = layer
        prop = ET.SubElement(mop, "RestrictElem")
        prop.text = self.restrict_elem
        prop = ET.SubElement(mop, "NumMaxElem")
        prop.text = self.num_max_elem
        if self.type == "MeshOperationLength":
            prop = ET.SubElement(mop, "RestrictLength")
            prop.text = self.restrict_length
            prop = ET.SubElement(mop, "MaxLength")
            prop.text = self.max_length
        else:
            prop = ET.SubElement(mop, "SkinDepth")
            prop.text = self.skin_depth
            prop = ET.SubElement(mop, "SurfTriLength")
            prop.text = self.surf_tri_length
            prop = ET.SubElement(mop, "NumLayers")
            prop.text = self.num_layers
        prop = ET.SubElement(mop, "RegionSolveInside")
        prop.text = self.region_solve_inside


class ControlFileSetup:
    """Setup Class."""

    def __init__(self, name):
        self.name = name
        self.enabled = True
        self.save_fields = False
        self.save_rad_fields = False
        self.frequency = "1GHz"
        self.maxpasses = 10
        self.max_delta = 0.02
        self.union_polygons = True
        self.small_voids_area = 0
        self.mode_type = "IC"
        self.ic_model_resolution = "Auto"
        self.order_basis = "FirstOrder"
        self.solver_type = "Auto"
        self.low_freq_accuracy = False
        self.mesh_operations = []
        self.sweeps = []

    def add_sweep(self, name, start, stop, step, sweep_type="Interpolating", step_type="LinearStep", use_q3d=True):
        """Add a new sweep.

        Parameters
        ----------
        name : str
            Sweep name.
        start : str
            Frequency start.
        stop : str
            Frequency stop.
        step : str
            Frequency step or count.
        sweep_type : str
            Sweep type. It can be `"Discrete"` or  `"Interpolating"`.
        step_type : str
            Sweep type. It can be `"LinearStep"`, `"DecadeCount"` or  `"LinearCount"`.
        use_q3d

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.control_file.ControlFileSweep`
        """
        self.sweeps.append(ControlFileSweep(name, start, stop, step, sweep_type, step_type, use_q3d))
        return self.sweeps[-1]

    def add_mesh_operation(self, name, region, type, nets_layers):
        """Add mesh operations.

        Parameters
        ----------
        name : str
            Mesh name.
        region : str
            Region to apply mesh operation.
        type : str
            Mesh operation type. It can be `"MeshOperationLength"` or  `"MeshOperationSkinDepth"`.
        nets_layers : dict
            Dictionary containing nets and layers on which apply mesh.

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.control_file.ControlFileMeshOp`

        """
        mop = ControlFileMeshOp(name, region, type, nets_layers)
        self.mesh_operations.append(mop)
        return mop

    def _write_xml(self, root):
        setups = ET.SubElement(root, "HFSSSetup")
        setups.set("schemaVersion", "1.0")
        setups.set("Name", self.name)
        setup = ET.SubElement(setups, "HFSSSimulationSettings")
        prop = ET.SubElement(setup, "Enabled")
        prop.text = str(self.enabled).lower()
        prop = ET.SubElement(setup, "SaveFields")
        prop.text = str(self.save_fields).lower()
        prop = ET.SubElement(setup, "SaveRadFieldsOnly")
        prop.text = str(self.save_rad_fields).lower()
        prop = ET.SubElement(setup, "HFSSAdaptiveSettings")
        prop = ET.SubElement(prop, "AdaptiveSettings")
        prop = ET.SubElement(prop, "SingleFrequencyDataList")
        prop = ET.SubElement(prop, "AdaptiveFrequencyData")
        prop2 = ET.SubElement(prop, "AdaptiveFrequency")
        prop2.text = self.frequency
        prop2 = ET.SubElement(prop, "MaxPasses")
        prop2.text = str(self.maxpasses)
        prop2 = ET.SubElement(prop, "MaxDelta")
        prop2.text = str(self.max_delta)
        prop = ET.SubElement(setup, "HFSSDefeatureSettings")
        prop2 = ET.SubElement(prop, "UnionPolygons")
        prop2.text = str(self.union_polygons).lower()

        prop2 = ET.SubElement(prop, "SmallVoidArea")
        prop2.text = str(self.small_voids_area)
        prop2 = ET.SubElement(prop, "ModelType")
        prop2.text = str(self.mode_type)
        prop2 = ET.SubElement(prop, "ICModelResolutionType")
        prop2.text = str(self.ic_model_resolution)

        prop = ET.SubElement(setup, "HFSSSolverSettings")
        prop2 = ET.SubElement(prop, "OrderBasis")
        prop2.text = str(self.order_basis)
        prop2 = ET.SubElement(prop, "SolverType")
        prop2.text = str(self.solver_type)
        prop = ET.SubElement(setup, "HFSSMeshOperations")
        for mesh in self.mesh_operations:
            mesh._write_xml(prop)
        prop = ET.SubElement(setups, "HFSSSweepDataList")
        for sweep in self.sweeps:
            sweep._write_xml(prop)


class ControlFileSetups:
    """Setup manager class."""

    def __init__(self):
        self.setups = []

    def add_setup(self, name, frequency):
        """Add a new setup

        Parameters
        ----------
        name : str
            Setup name.
        frequency : str
            Setup Frequency.

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.control_file.ControlFileSetup`
        """
        setup = ControlFileSetup(name)
        setup.frequency = frequency
        self.setups.append(setup)
        return setup

    def _write_xml(self, root):
        content = ET.SubElement(root, "SimulationSetups")
        for setup in self.setups:
            setup._write_xml(content)


class ControlFile:
    """Control File Class. It helps the creation and modification of edb xml control files."""

    def __init__(self, xml_input=None, tecnhology=None, layer_map=None):
        self.stackup = ControlFileStackup()
        if xml_input:
            self.parse_xml(xml_input)
        if tecnhology:
            self.parse_technology(tecnhology)
        if layer_map:
            self.parse_layer_map(layer_map)
        self.boundaries = ControlFileBoundaries()
        self.remove_holes = False
        self.remove_holes_area_minimum = 30
        self.remove_holes_units = "um"
        self.setups = ControlFileSetups()
        self.components = ControlFileComponents()
        self.import_options = ControlFileImportOptions()
        pass

    def parse_technology(self, tecnhology, edbversion=None):
        """Parse technology files using Helic and convert it to xml file.

        Parameters
        ----------
        layer_map : str
            Full path to technology file.

        Returns
        -------
        bool
        """
        xml_temp = os.path.splitext(tecnhology)[0] + "_temp.xml"
        xml_temp = convert_technology_file(tech_file=tecnhology, edbversion=edbversion, control_file=xml_temp)
        if xml_temp:
            return self.parse_xml(xml_temp)

    def parse_layer_map(self, layer_map):
        """Parse layer map and adds info to the stackup info.
        This operation must be performed after a tech file is imported.

        Parameters
        ----------
        layer_map : str
            Full path to `".map"` file.

        Returns
        -------

        """
        with open(layer_map, "r") as f:
            lines = f.readlines()
            for line in lines:
                if not line.startswith("#") and re.search(r"\w+", line.strip()):
                    out = re.split(r"\s+", line.strip())
                    layer_name = out[0]
                    layer_id = out[2]
                    layer_type = out[3]
                    for layer in self.stackup.layers[:]:
                        if layer.name == layer_name:
                            layer.properties["GDSDataType"] = layer_type
                            layer.name = layer_id
                            layer.properties["TargetLayer"] = layer_name
                            break
                        elif layer.properties.get("TargetLayer", None) == layer_name:
                            new_layer = ControlFileLayer(layer_id, copy.deepcopy(layer.properties))
                            new_layer.properties["GDSDataType"] = layer_type
                            new_layer.name = layer_id
                            new_layer.properties["TargetLayer"] = layer_name
                            self.stackup.layers.append(new_layer)
                            break
                    for layer in self.stackup.vias[:]:
                        if layer.name == layer_name:
                            layer.properties["GDSDataType"] = layer_type
                            layer.name = layer_id
                            layer.properties["TargetLayer"] = layer_name
                            break
                        elif layer.properties.get("TargetLayer", None) == layer_name:
                            new_layer = ControlFileVia(layer_id, copy.deepcopy(layer.properties))
                            new_layer.properties["GDSDataType"] = layer_type
                            new_layer.name = layer_id
                            new_layer.properties["TargetLayer"] = layer_name
                            self.stackup.vias.append(new_layer)
                            self.stackup.vias.append(new_layer)
                            break
        return True

    def parse_xml(self, xml_input):
        """Parse an xml and populate the class with materials and Stackup only.

        Parameters
        ----------
        xml_input : str
            Full path to xml.

        Returns
        -------
        bool
        """
        tree = ET.parse(xml_input)
        root = tree.getroot()
        for el in root:
            if el.tag == "Stackup":
                for st_el in el:
                    if st_el.tag == "Materials":
                        for mat in st_el:
                            mat_name = mat.attrib["Name"]
                            properties = {}
                            for prop in mat:
                                if prop[0].tag == "Double":
                                    properties[prop.tag] = prop[0].text
                            self.stackup.add_material(mat_name, properties)
                    elif st_el.tag == "ELayers":
                        if st_el.attrib == "LengthUnits":
                            self.stackup.units = st_el.attrib
                        for layers_el in st_el:
                            if "BaseElevation" in layers_el.attrib:
                                self.stackup.dielectrics_base_elevation = layers_el.attrib["BaseElevation"]
                            for layer_el in layers_el:
                                properties = {}
                                layer_name = layer_el.attrib["Name"]
                                for propname, prop_val in layer_el.attrib.items():
                                    properties[propname] = prop_val
                                if layers_el.tag == "Dielectrics":
                                    self.stackup.add_dielectric(
                                        layer_name=layer_name,
                                        material=properties["Material"],
                                        thickness=properties["Thickness"],
                                    )
                                elif layers_el.tag == "Layers":
                                    self.stackup.add_layer(layer_name=layer_name, properties=properties)
                                elif layers_el.tag == "Vias":
                                    via = self.stackup.add_via(layer_name, properties=properties)
                                    for i in layer_el:
                                        if i.tag == "CreateViaGroups":
                                            via.create_via_group = True
                                            if "CheckContainment" in i.attrib:
                                                via.check_containment = (
                                                    True if i.attrib["CheckContainment"] == "true" else False
                                                )
                                            if "Tolerance" in i.attrib:
                                                via.tolerance = i.attrib["Tolerance"]
                                            if "Method" in i.attrib:
                                                via.method = i.attrib["Method"]
                                            if "Persistent" in i.attrib:
                                                via.persistent = True if i.attrib["Persistent"] == "true" else False
                                        elif i.tag == "SnapViaGroups":
                                            if "Method" in i.attrib:
                                                via.snap_method = i.attrib["Method"]
                                            if "Tolerance" in i.attrib:
                                                via.snap_tolerance = i.attrib["Tolerance"]
                                            if "RemoveUnconnected" in i.attrib:
                                                via.remove_unconnected = (
                                                    True if i.attrib["RemoveUnconnected"] == "true" else False
                                                )
        return True

    @pyaedt_function_handler()
    def write_xml(self, xml_output):
        """Write xml to output file

        Parameters
        ----------
        xml_output : str
            Path to the output xml file.

        Returns
        -------
        bool
        """
        control = ET.Element("{http://www.ansys.com/control}Control", attrib={"schemaVersion": "1.0"})
        self.stackup._write_xml(control)
        if self.boundaries.ports or self.boundaries.extents:
            self.boundaries._write_xml(control)
        if self.remove_holes:
            hole = ET.SubElement(control, "RemoveHoles")
            hole.set("HoleAreaMinimum", str(self.remove_holes_area_minimum))
            hole.set("LengthUnit", self.remove_holes_units)
        if self.setups.setups:
            setups = ET.SubElement(control, "SimulationSetups")
            for setup in self.setups.setups:
                setup._write_xml(setups)
        self.import_options._write_xml(control)
        if self.components.components:
            comps = ET.SubElement(control, "GDS_COMPONENTS")
            comps.set("LengthUnit", self.components.units)
            for comp in self.components.components:
                comp._write_xml(comps)
        write_pretty_xml(control, xml_output)
        return True if os.path.exists(xml_output) else False
