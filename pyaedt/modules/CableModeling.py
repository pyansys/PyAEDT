import itertools
import json
import os

from pyaedt.application.Variables import decompose_variable_value
from pyaedt.generic.DataHandlers import json_to_dict
from pyaedt.generic.general_methods import generate_unique_name
from pyaedt.generic.LoadAEDTFile import load_entire_aedt_file


class Cable:
    """Contains all common Cable features.

    Parameters
    ----------
    app : :class:`pyaedt.hfss.Hfss`
    json_file_name : str, dict, optional
        Full path to either the JSON file or dictionary containing the cable information.
    working_dir : str, optional
        Working directory.

    Examples
    --------
    >>> from pyaedt import Hfss
    >>> from pyaedt.modules.CableModeling import Cable
    >>> hfss = Hfss()
    >>> cable_class = Cable(hfss)

    """

    def __init__(self, app, json_file_name=None, working_dir=None):
        self._app = app
        self._odesign = app.odesign
        self._omodule = self._odesign.GetModule("CableSetup")
        self.clock_source_definitions = None
        self.pwl_source_definitions = None
        if working_dir is None:
            self._working_dir = self._app.toolkit_directory
        else:
            self._working_dir = working_dir

        file_import = self._cable_properties_parser(self._omodule, self._working_dir)
        if file_import["CableManager"]["TDSources"]:
            if (
                "ClockSourceDef" in file_import["CableManager"]["TDSources"].keys()
                and file_import["CableManager"]["TDSources"]["ClockSourceDef"]
            ):
                self.clock_source_definitions = file_import["CableManager"]["TDSources"]["ClockSourceDef"]
            if (
                "PWLSourceDef" in file_import["CableManager"]["TDSources"].keys()
                and file_import["CableManager"]["TDSources"]["PWLSourceDef"]
            ):
                self.pwl_source_definitions = file_import["CableManager"]["TDSources"]["PWLSourceDef"]
            self.existing_sources_names = []
            if isinstance(self.clock_source_definitions, list):
                for source in self.clock_source_definitions:
                    if source.get("ClockSignalParams"):
                        self.existing_sources_names.append(source["TDSourceAttribs"]["Name"])
            elif isinstance(self.clock_source_definitions, dict):
                self.existing_sources_names.append(self.clock_source_definitions["TDSourceAttribs"]["Name"])
            if isinstance(self.pwl_source_definitions, list):
                for source in self.pwl_source_definitions:
                    if source.get("PWLSignalParams"):
                        self.existing_sources_names.append(source["TDSourceAttribs"]["Name"])
            elif isinstance(self.pwl_source_definitions, dict):
                self.existing_sources_names.append(self.pwl_source_definitions["TDSourceAttribs"]["Name"])

        self.cable_definitions = file_import["CableManager"]["Definitions"]
        self.existing_bundle_cables_names = []
        self.existing_straight_wire_cables_ids = []
        self.existing_straight_wire_cables_names = []
        self.existing_twisted_pair_cables_names = []
        bundle_cables_list = []
        st_wire_cables_list = []
        twisted_pair_cables_list = []
        if self.cable_definitions.get("CableBundle"):
            if not isinstance(self.cable_definitions.get("CableBundle"), list):
                bundle_cables_list.append(self.cable_definitions.get("CableBundle"))
            else:
                bundle_cables_list = self.cable_definitions.get("CableBundle")
            self.cables_in_bundle_list_dict = []
            for x in bundle_cables_list:
                self.existing_bundle_cables_names.append(x["BundleAttribs"]["Name"])
                if x["Instances"]:
                    if x["Instances"]["StWireInstance"]:
                        cables_in_bundle_dict = {}
                        cables_in_bundle_dict[x["BundleAttribs"]["Name"]] = []
                        for stwire in x["Instances"]["StWireInstance"]:
                            cables_in_bundle_dict[x["BundleAttribs"]["Name"]].append(stwire["CableInstAttribs"]["Name"])
                        self.cables_in_bundle_list_dict.append(cables_in_bundle_dict)

        if self.cable_definitions.get("StWireCable"):
            if not isinstance(self.cable_definitions.get("StWireCable"), list):
                st_wire_cables_list.append(self.cable_definitions.get("StWireCable"))
            else:
                st_wire_cables_list = self.cable_definitions.get("StWireCable")
            for x in st_wire_cables_list:
                self.existing_straight_wire_cables_ids.append(x["ID"])
                self.existing_straight_wire_cables_names.append(x["StWireAttribs"]["Name"])
        if self.cable_definitions.get("TwistedPairCable"):
            if not isinstance(self.cable_definitions.get("TwistedPairCable"), list):
                twisted_pair_cables_list.append(self.cable_definitions.get("TwistedPairCable"))
            else:
                twisted_pair_cables_list = self.cable_definitions.get("TwistedPairCable")
            for x in twisted_pair_cables_list:
                self.existing_twisted_pair_cables_names.append(x["TwistedPairAttribs"]["Name"])

        if json_file_name:
            self._init_from_json(json_file_name)

    def create_cable(self):
        """Create a cable.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        try:
            if self.cable_type == "bundle":
                if self.jacket_type == "insulation":
                    self._omodule.CreateCableBundle(
                        [
                            "NAME:BundleParams",
                            "AutoPack:=",
                            self.is_auto_pack,
                            [
                                "NAME:InsulationJacketParams",
                                "InsThickness:=",
                                self.insulation_thickness,
                                "JacketMaterial:=",
                                self.jacket_material,
                                "InnerDiameter:=",
                                self.inner_diameter,
                            ],
                        ],
                        ["NAME:BundleAttribs", "Name:=", self.cable_name],
                    )
                elif self.jacket_type == "braided shield":
                    self._omodule.CreateCableBundle(
                        [
                            "NAME:BundleParams",
                            "AutoPack:=",
                            self.is_auto_pack,
                            [
                                "NAME:BraidShieldJacketParams",
                                "JacketMaterial:=",
                                self.jacket_material,
                                "NumCarriers:=",
                                self.num_carriers,
                                "NumWiresInCarrier:=",
                                self.num_wires_carriers,
                                "WireDiameter:=",
                                self.wire_diameter,
                                "WeaveAngle:=",
                                self.weave_angle,
                                "InsThickness:=",
                                self.insulation_thickness,
                                "InnerDiameter:=",
                                self.inner_diameter,
                            ],
                        ],
                        ["NAME:BundleAttribs", "Name:=", self.cable_name],
                    )
                elif self.jacket_type == "no jacket":
                    self._omodule.CreateCableBundle(
                        [
                            "NAME:BundleParams",
                            "AutoPack:=",
                            self.is_auto_pack,
                            [
                                "NAME:VirtualJacketParams",
                                "JacketMaterial:=",
                                self.jacket_material,
                                "InnerDiameter:=",
                                self.inner_diameter,
                            ],
                        ],
                        ["NAME:BundleAttribs", "Name:=", self.cable_name],
                    )
            elif self.cable_type == "straight wire":
                self._omodule.CreateStraightWireCable(
                    [
                        "NAME:StWireParams",
                        "WireStandard:=",
                        self.wire_standard,
                        "WireGauge:=",
                        self.wire_type,
                        "CondDiameter:=",
                        self.conductor_diameter,
                        "CondMaterial:=",
                        self.conductor_material,
                        "InsThickness:=",
                        self.straight_wire_insulation_thickness,
                        "InsMaterial:=",
                        self.insulation_material,
                        "InsType:=",
                        self.insulation_type.title(),
                    ],
                    ["NAME:StWireAttribs", "Name:=", self.cable_name],
                )
            else:
                if self.is_lay_length_specified.lower() == "true":
                    self._omodule.CreateTwistedPairCable(
                        self.assign_cable_to_twisted_pair,
                        [
                            "NAME:TwistedPairParams",
                            "IsLayLengthSpecified:=",
                            True,
                            "LayLength:=",
                            self.lay_length,
                        ],
                        ["NAME:TwistedPairAttribs", "Name:=", self.cable_name],
                    )
                elif self.is_lay_length_specified.lower() == "false":
                    self._omodule.CreateTwistedPairCable(
                        self.assign_cable_to_twisted_pair,
                        [
                            "NAME:TwistedPairParams",
                            "IsLayLengthSpecified:=",
                            False,
                            "TurnsPerMeter:=",
                            self.turns_per_meter,
                        ],
                        ["NAME:TwistedPairAttribs", "Name:=", self.cable_name],
                    )
            return True
        except:
            self._app.logger.error("Cable creation was unsuccessful.")
            return False

    def update_cable_properties(self):
        """Update cable properties for all cable types.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        try:
            if self.cable_type == "bundle":
                if self.jacket_type == "no jacket":
                    self.insulation_thickness = "0mm"
                self._odesign.ChangeProperty(
                    [
                        "NAME:AllTabs",
                        [
                            "NAME:Cable",
                            ["NAME:PropServers", "CableSetup:" + self.cable_name],
                            [
                                "NAME:ChangedProps",
                                ["NAME:Name", "Value:=", self.updated_name],
                                ["NAME:JacketType", "Value:=", self.jacket_type],
                                ["NAME:JacketMaterial", "Value:=", '"{}"'.format(self.jacket_material)],
                                ["NAME:InsulationThickness", "Value:=", self.insulation_thickness],
                                ["NAME:JacketInnerDiameter", "Value:=", self.inner_diameter],
                            ],
                        ],
                    ]
                )
            elif self.cable_type == "straight wire":
                self._odesign.ChangeProperty(
                    [
                        "NAME:AllTabs",
                        [
                            "NAME:Cable",
                            ["NAME:PropServers", "CableSetup:" + self.cable_name],
                            [
                                "NAME:ChangedProps",
                                ["NAME:Name", "Value:=", self.updated_name],
                                ["NAME:WireStandard", "Value:=", self.wire_standard],
                                ["NAME:WireType", "Value:=", "{:.2f}".format(float(self.wire_type))],
                                ["NAME:ConductorDiameter", "Value:=", self.conductor_diameter],
                                ["NAME:ConductorMaterial", "Value:=", '"{}"'.format(self.conductor_material)],
                                ["NAME:InsulationType", "Value:=", self.insulation_type.title()],
                                ["NAME:InsulationThickness", "Value:=", self.straight_wire_insulation_thickness],
                                ["NAME:InsulationMaterial", "Value:=", '"{}"'.format(self.insulation_material)],
                            ],
                        ],
                    ]
                )
            else:
                self._odesign.ChangeProperty(
                    [
                        "NAME:AllTabs",
                        [
                            "NAME:Cable",
                            ["NAME:PropServers", "CableSetup:" + self.cable_name],
                            [
                                "NAME:ChangedProps",
                                ["NAME:Name", "Value:=", self.updated_name],
                                ["NAME:Contained Cable", "Value:=", self.assign_cable_to_twisted_pair],
                                ["NAME:Specify Lay Length", "Value:=", self.is_lay_length_specified],
                                ["NAME:Lay Length", "Value:=", self.lay_length],
                                ["NAME:Turns Per Meter", "Value:=", self.turns_per_meter],
                            ],
                        ],
                    ]
                )
            return True
        except:
            self._app.logger.error("Cable properties not updated.")
            return False

    def update_shielding(self):
        """Create jacket type when cable type is bundle and jacket type is braid shield.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        try:
            self._odesign.ChangeProperty(
                [
                    "NAME:AllTabs",
                    [
                        "NAME:Cable",
                        ["NAME:PropServers", "CableSetup:" + self.cable_name],
                        [
                            "NAME:ChangedProps",
                            ["NAME:Name", "Value:=", self.updated_name],
                            ["NAME:JacketType", "Value:=", self.jacket_type],
                            ["NAME:JacketMaterial", "Value:=", '"{}"'.format(self.jacket_material)],
                            ["NAME:InsulationThickness", "Value:=", self.insulation_thickness],
                            ["NAME:JacketInnerDiameter", "Value:=", self.inner_diameter],
                        ],
                    ],
                ]
            )
            self._odesign.ChangeProperty(
                [
                    "NAME:AllTabs",
                    [
                        "NAME:Shielding",
                        ["NAME:PropServers", "CableSetup:" + self.updated_name],
                        [
                            "NAME:ChangedProps",
                            ["NAME:NumCarriers", "Value:=", self.num_carriers],
                            ["NAME:NumWiresInCarrier", "Value:=", self.num_wires_carriers],
                            ["NAME:WireDiameter", "Value:=", self.wire_diameter],
                            ["NAME:WeaveAngle", "Value:=", self.weave_angle],
                        ],
                    ],
                ]
            )
            return True
        except:
            self._app.logger.error("Cable shielding properties not updated.")
            return False

    def remove_cables(self):
        """Remove a list of cables.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        for cable_to_remove in self.cables_to_remove:
            if cable_to_remove not in itertools.chain(
                self.existing_bundle_cables_names,
                self.existing_straight_wire_cables_names,
                self.existing_twisted_pair_cables_names,
            ):
                self._app.logger.error("Provided cable name to remove doesn't exist in the current design.")
                return False
            else:
                try:
                    self._omodule.RemoveCable(cable_to_remove)
                    return True
                except:
                    self._app.logger.error("Remove cable failed.")
                    return False

    def add_cable_to_bundle(self):
        """Add a cable to an existing cable bundle.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if [x for x in self.cables_to_add_to_bundle if x in self.existing_straight_wire_cables_names]:
            for cable_to_add in self.cables_to_add_to_bundle:
                try:
                    self._omodule.AddCableToBundle(
                        self.bundle_cable,
                        cable_to_add,
                        self.number_of_cables_to_add,
                        ["NAME:CableInstParams", "XPos:=", "0mm", "YPos:=", "0mm", "RotX:=", "0deg"],
                        ["NAME:CableInstAttribs", "Name:=", cable_to_add],
                    )
                    return True
                except:
                    self._app.logger.error("Add cable to Bundle failed. Please check the provided cable names.")
                    return False
        else:
            self._app.logger.error("There is not any cable with the provided name.")
            return False

    def create_clock_source(self):
        """Create a clock source.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        try:
            self._omodule.CreateClockSource(
                [
                    "NAME:ClockSignalParams",
                    "Period:=",
                    self.source_period,
                    "LowPulseVal:=",
                    self.low_pulse_value,
                    "HighPulseVal:=",
                    self.high_pulse_value,
                    "Risetime:=",
                    self.rise_time,
                    "Falltime:=",
                    self.fall_time,
                    "PulseWidth:=",
                    self.pulse_width,
                ],
                ["NAME:TDSourceAttribs", "Name:=", self.source_name],
            )
            return True
        except:
            self._app.logger.error("Clock source not created.")
            return False

    def update_clock_source(self):
        """Update clock source.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        try:
            self._odesign.ChangeProperty(
                [
                    "NAME:AllTabs",
                    [
                        "NAME:Cable",
                        ["NAME:PropServers", "CableSetup:" + self.source_name],
                        [
                            "NAME:ChangedProps",
                            ["NAME:Name", "Value:=", self.updated_source_name],
                            ["NAME:Period", "Value:=", self.source_period],
                            ["NAME:LowPulseVal", "Value:=", self.low_pulse_value],
                            ["NAME:HighPulseVal", "Value:=", self.high_pulse_value],
                            ["NAME:Risetime", "Value:=", self.rise_time],
                            ["NAME:Falltime", "Value:=", self.fall_time],
                            ["NAME:PulseWidth", "Value:=", self.pulse_width],
                        ],
                    ],
                ]
            )
            return True
        except:
            self._app.logger.error("Clock source not created.")
            return False

    def remove_source(self):
        """Remove source.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        try:
            self._omodule.RemoveTimeDomainSource(self.source_to_remove)
            return True
        except:
            self._app.logger.error("Source could not be removed.")
            return False

    def remove_all_sources(self):
        """Remove all sources.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        try:
            if self.existing_sources_names:
                for source in self.existing_sources_names:
                    self._omodule.RemoveTimeDomainSource(source)
            return True
        except:
            self._app.logger.error("Source could not be removed.")
            return False

    def create_pwl_source(self):
        """Create a clock source.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        try:
            self.signal_values.insert(0, "NAME:SignalValues")
            self.time_values.insert(0, "NAME:TimeValues")
            arg1 = [x for x in self.signal_values]
            arg2 = [x for x in self.time_values]
            self._omodule.CreatePWLSource(
                [
                    "NAME:PWLSignalParams",
                    arg1,
                    arg2,
                ],
                ["NAME:TDSourceAttribs", "Name:=", self.pwl_source_name],
            )
            return True
        except:
            self._app.logger.error("PWL source not created.")
            return False

    def create_pwl_source_from_file(self):
        """Create a pwl source from file.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        try:
            self._omodule.CreatePWLSourceFromFile(
                self.pwl_source_file_path, ["NAME:TDSourceAttribs", "Name:=", generate_unique_name("pwl")]
            )
            return True
        except:
            self._app.logger.error("PWL source from file not created.")
            return False

    def update_pwl_source(self):
        """Update pwl source.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        self.signal_values.insert(0, "NAME:SignalValues")
        self.time_values.insert(0, "NAME:TimeValues")
        try:
            self._odesign.ChangeProperty(
                [
                    "NAME:AllTabs",
                    [
                        "NAME:Cable",
                        ["NAME:PropServers", "CableSetup:" + self.pwl_source_name],
                        [
                            "NAME:ChangedProps",
                            [
                                "NAME:Edit PWL...",
                                [
                                    "NAME:PWLSignalParams",
                                    [
                                        [x for x in self.signal_values],
                                    ],
                                    [
                                        [x for x in self.time_values],
                                    ],
                                ],
                            ],
                            ["NAME:Name", "Value:=", self.updated_pwl_source_name],
                        ],
                    ],
                ]
            )
            return True
        except:
            self._app.logger.error("PWL source not created.")
            return False

    def create_cable_harness(self):
        """Create cable harness.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        try:
            self._omodule.CreateCableHarness(
                [
                    "NAME:HarnessParams",
                    "Bundle:=",
                    self.cable_harness_bundle,
                    "TwistAlongPath:=",
                    self.twist_angle_along_route,
                    "Route:=",
                    self.cable_harness_polyline,
                    "AutoOrient:=",
                    self.cable_harness_auto_orient,
                    "Origin:=",
                    self.cable_harness_x_axis_origin,
                    "XAxisEnd:=",
                    self.cable_harness_x_axis_end_point,
                    "PlaneFlip:=",
                    self.reverse_y_axis_direction,
                    self.args[0],
                    self.args[1],
                    self.args[2],
                ],
                ["NAME:HarnessAttribs", "Name:=", self.cable_harness_name],
            )
            oEditor = self._odesign.SetActiveEditor("3D Modeler")
            oEditor.InsertNativeComponent(
                [
                    "NAME:InsertNativeComponentData",
                    "TargetCS:=",
                    "Global",
                    "SubmodelDefinitionName:=",
                    self.cable_harness_name,
                    ["NAME:ComponentPriorityLists"],
                    "NextUniqueID:=",
                    0,
                    "MoveBackwards:=",
                    False,
                    "DatasetType:=",
                    "ComponentDatasetType",
                    ["NAME:DatasetDefinitions"],
                    [
                        "NAME:BasicComponentInfo",
                        "ComponentName:=",
                        self.cable_harness_name,
                        "Company:=",
                        "",
                        "Company URL:=",
                        "",
                        "Model Number:=",
                        "",
                        "Help URL:=",
                        "",
                        "Version:=",
                        "1.0",
                        "Notes:=",
                        "",
                        "IconType:=",
                        "CableHarness",
                    ],
                    ["NAME:GeometryDefinitionParameters", ["NAME:VariableOrders"]],
                    ["NAME:DesignDefinitionParameters", ["NAME:VariableOrders"]],
                    ["NAME:MaterialDefinitionParameters", ["NAME:VariableOrders"]],
                    "MapInstanceParameters:=",
                    "NotVariable",
                    "UniqueDefinitionIdentifier:=",
                    "5c0c451d-2fc3-4800-bcac-2109a11351ee",
                    "OriginFilePath:=",
                    "",
                    "IsLocal:=",
                    False,
                    "ChecksumString:=",
                    "",
                    "ChecksumHistory:=",
                    [],
                    "VersionHistory:=",
                    [],
                    [
                        "NAME:NativeComponentDefinitionProvider",
                        "Type:=",
                        "CableHarness",
                        "Unit:=",
                        self._app.modeler.model_units,
                        "Harness:=",
                        self.cable_harness_name,
                        "HarnessPartID:=",
                        -1,
                    ],
                    [
                        "NAME:InstanceParameters",
                        "GeometryParameters:=",
                        "",
                        "MaterialParameters:=",
                        "",
                        "DesignParameters:=",
                        "",
                    ],
                ]
            )

            return True
        except:
            self._app.logger.error("Couldn't create cable harness.")
            return False

    def _init_from_json(self, json_file_name):
        if isinstance(json_file_name, dict):
            json_dict = json_file_name
        else:
            json_dict = json_to_dict(json_file_name)

        # Cable implementation
        if json_dict["Add_Cable"].lower() == "true" or json_dict["Update_Cable"].lower() == "true":
            try:
                if json_dict["Cable_prop"]["CableType"].lower() in ["bundle", "straight wire", "twisted pair"]:
                    self.cable_type = json_dict["Cable_prop"]["CableType"]
                else:
                    msg = "Cable type is not valid. Available values are: bundle, straight wire, twisted pair."
                    raise ValueError(msg)

                if json_dict["Update_Cable"].lower() == "true":
                    if json_dict["Cable_prop"]["UpdatedName"]:
                        self.updated_name = json_dict["Cable_prop"]["UpdatedName"]
                    else:
                        raise ValueError("Insert a valid updated name for cable.")

                if self.cable_type == "bundle":
                    cable_bundle_properties = json_dict["CableManager"]["Definitions"]["CableBundle"]
                    if cable_bundle_properties["BundleAttribs"]["Name"] is None:
                        self.cable_name = generate_unique_name("bundle")
                    else:
                        self.cable_name = cable_bundle_properties["BundleAttribs"]["Name"]
                    self.is_auto_pack = cable_bundle_properties["BundleParams"]["AutoPack"]

                    # Check Jacket type : only one can be True
                    bool_jacket_type_list = [
                        el == "True"
                        for el in [
                            json_dict["Cable_prop"]["IsJacketTypeInsulation"],
                            json_dict["Cable_prop"]["IsJacketTypeBraidShield"],
                            json_dict["Cable_prop"]["IsJacketTypeNoJacket"],
                        ]
                    ]
                    if bool_jacket_type_list.count(True) > 1:
                        msg = "Only one jacket type can be selected at time."
                        raise ValueError(msg)
                    else:
                        # Bundle Jacket type : Insulation
                        if bool_jacket_type_list[0]:
                            self.jacket_type = "insulation"
                            # Set default values if one or more keys are empty
                            if [
                                x
                                for x in cable_bundle_properties["BundleParams"]["InsulationJacketParams"]
                                if cable_bundle_properties["BundleParams"]["InsulationJacketParams"][x]
                                in [" ", "", [], None, 0, False]
                            ]:
                                self.insulation_thickness = "0.25mm"
                                self.jacket_material = "PVC plastic"
                                self.inner_diameter = "2.5mm"
                            else:
                                self.insulation_thickness = cable_bundle_properties["BundleParams"][
                                    "InsulationJacketParams"
                                ]["InsThickness"]
                                if self._app.materials.material_keys.get(
                                    cable_bundle_properties["BundleParams"]["InsulationJacketParams"][
                                        "JacketMaterial"
                                    ].lower()
                                ):
                                    self.jacket_material = cable_bundle_properties["BundleParams"][
                                        "InsulationJacketParams"
                                    ]["JacketMaterial"]
                                else:
                                    msg = "material provided doesn't exist."
                                    raise ValueError(msg)
                                self.inner_diameter = cable_bundle_properties["BundleParams"]["InsulationJacketParams"][
                                    "InnerDiameter"
                                ]
                        # Bundle Jacket type : Braided Shield
                        elif bool_jacket_type_list[1]:
                            self.jacket_type = "braided shield"
                            # Set default values if one or more keys are empty
                            if [
                                x
                                for x in cable_bundle_properties["BundleParams"]["BraidShieldJacketParams"]
                                if cable_bundle_properties["BundleParams"]["BraidShieldJacketParams"][x]
                                in ("", [], None, 0, False)
                            ]:
                                self.insulation_thickness = "0.25mm"
                                self.jacket_material = "copper"
                                self.num_carriers = "2"
                                self.num_wires_carriers = "5"
                                self.wire_diameter = "0.1mm"
                                self.weave_angle = "30deg"
                                self.inner_diameter = "2.5mm"
                            else:
                                if self._app.materials.material_keys.get(
                                    cable_bundle_properties["BundleParams"]["BraidShieldJacketParams"][
                                        "JacketMaterial"
                                    ].lower()
                                ):
                                    self.jacket_material = cable_bundle_properties["BundleParams"][
                                        "BraidShieldJacketParams"
                                    ]["JacketMaterial"]
                                else:
                                    msg = "material provided doesn't exist."
                                    raise ValueError(msg)
                                self.insulation_thickness = "0.25mm"
                                self.num_carriers = cable_bundle_properties["BundleParams"]["BraidShieldJacketParams"][
                                    "NumCarriers"
                                ]
                                self.num_wires_carriers = cable_bundle_properties["BundleParams"][
                                    "BraidShieldJacketParams"
                                ]["NumWiresInCarrier"]
                                self.wire_diameter = cable_bundle_properties["BundleParams"]["BraidShieldJacketParams"][
                                    "WireDiameter"
                                ]
                                self.weave_angle = cable_bundle_properties["BundleParams"]["BraidShieldJacketParams"][
                                    "WeaveAngle"
                                ]
                                self.inner_diameter = cable_bundle_properties["BundleParams"][
                                    "BraidShieldJacketParams"
                                ]["InnerDiameter"]
                        # Bundle Jacket type : no jacket
                        elif bool_jacket_type_list[2]:
                            self.jacket_type = "no jacket"
                            # Set default values if one or more keys are empty
                            if [
                                x
                                for x in cable_bundle_properties["BundleParams"]["VirtualJacketParams"]
                                if cable_bundle_properties["BundleParams"]["VirtualJacketParams"][x]
                                in ("", [], None, 0, False)
                            ]:
                                self.jacket_material = "None"
                                self.insulation_thickness = "0.25mm"
                                self.inner_diameter = "2.5mm"
                            else:
                                self.jacket_material = "None"
                                self.inner_diameter = cable_bundle_properties["BundleParams"]["VirtualJacketParams"][
                                    "InnerDiameter"
                                ]
                elif self.cable_type == "straight wire":
                    cable_st_wire_properties = json_dict["CableManager"]["Definitions"]["StWireCable"]
                    if cable_st_wire_properties["StWireAttribs"]["Name"] is None:
                        self.cable_name = generate_unique_name("stwire")
                    else:
                        self.cable_name = cable_st_wire_properties["StWireAttribs"]["Name"]
                    # Set default values if one or more keys are empty
                    if [
                        x
                        for x in cable_st_wire_properties["StWireParams"]
                        if cable_st_wire_properties["StWireParams"][x] in ("", [], None, 0, False)
                    ]:
                        self.wire_standard = "ISO"
                        self.wire_type = "0.13"
                        self.conductor_diameter = "0.55mm"
                        self.conductor_material = "copper"
                        self.insulation_type = "Thin Wall"
                        self.straight_wire_insulation_thickness = "0.25mm"
                        self.insulation_material = "PVC plastic"
                    else:

                        if cable_st_wire_properties["StWireParams"]["WireStandard"] == "ISO":
                            self.wire_standard = cable_st_wire_properties["StWireParams"]["WireStandard"]
                        else:
                            msg = 'The only accepted wire standard is "ISO".'
                            raise ValueError(msg)
                        if cable_st_wire_properties["StWireParams"]["WireGauge"] in [
                            "0.13",
                            "0.22",
                            "0.35",
                            "0.5",
                            "0.75",
                            "1",
                            "1.5",
                            "2",
                            "2.5",
                            "3",
                            "4",
                            "5",
                            "6",
                            "10",
                            "16",
                            "25",
                            "35",
                            "50",
                            "70",
                            "95",
                            "120",
                        ]:
                            self.wire_type = cable_st_wire_properties["StWireParams"]["WireGauge"]
                            if self.wire_type in ["0.13", "0.22", "0.35"]:
                                insulation_type_options = ["Thin Wall", "Ultra-Thin Wall"]
                            elif self.wire_type in ["0.5", "0.75", "1", "1.5", "2", "2.5"]:
                                insulation_type_options = ["Thick Wall", "Thin Wall", "Ultra-Thin Wall"]
                            elif self.wire_type in ["3", "4", "5", "6", "10", "16", "25"]:
                                insulation_type_options = ["Thick Wall", "Thin Wall"]
                            elif self.wire_type in ["35", "50", "70", "95", "120"]:
                                insulation_type_options = ["Thick Wall"]
                        else:
                            msg = (
                                "Wire type not valid. Available options are: 0.13, 0.22, 0.35, 0.5, 0.75, 1, 1.5, 2, "
                                "2.5, 3, 4, 5, 6, 10, 16, 25, 35, 50, 70, 95, 120."
                            )
                            raise ValueError(msg)
                        self.conductor_diameter = cable_st_wire_properties["StWireParams"]["CondDiameter"]
                        if self._app.materials.material_keys.get(
                            cable_st_wire_properties["StWireParams"]["CondMaterial"].lower()
                        ):
                            self.conductor_material = cable_st_wire_properties["StWireParams"]["CondMaterial"]
                        else:
                            msg = "material provided doesn't exist."
                            raise ValueError(msg)
                        if cable_st_wire_properties["StWireParams"]["InsType"].title() in insulation_type_options:
                            self.insulation_type = cable_st_wire_properties["StWireParams"]["InsType"]
                        else:
                            msg = (
                                "insulation type provided is not valid. Depending on wire type the available options"
                                "are thick wall, thin wall or ultra-thin wall."
                            )
                            raise ValueError(msg)
                        self.straight_wire_insulation_thickness = cable_st_wire_properties["StWireParams"][
                            "InsThickness"
                        ]
                        if self._app.materials.material_keys.get(
                            cable_st_wire_properties["StWireParams"]["InsMaterial"].lower()
                        ):
                            self.insulation_material = cable_st_wire_properties["StWireParams"]["InsMaterial"]
                        else:
                            raise ValueError("Material provided doesn't exist.")
                else:
                    cable_twisted_pair_properties = json_dict["CableManager"]["Definitions"]["TwistedPairCable"]
                    if cable_twisted_pair_properties["TwistedPairAttribs"]["Name"] is None:
                        self.cable_name = generate_unique_name("tpair")
                    else:
                        self.cable_name = cable_twisted_pair_properties["TwistedPairAttribs"]["Name"]
                    if not self.existing_straight_wire_cables_names:
                        msg = (
                            "no straight wire cables existing in the project. "
                            "At least two are needed to create a twisted pair."
                        )
                        raise ValueError(msg)
                    else:
                        if (
                            cable_twisted_pair_properties["TwistedPairParams"]["StraightWireCableID"]
                            in self.existing_straight_wire_cables_ids
                        ):
                            index = self.existing_straight_wire_cables_ids.index(
                                cable_twisted_pair_properties["TwistedPairParams"]["StraightWireCableID"]
                            )
                            self.assign_cable_to_twisted_pair = self.existing_straight_wire_cables_names[index]
                        elif not cable_twisted_pair_properties["TwistedPairParams"]["StraightWireCableID"]:
                            msg = "no cable id provided. Please enter at least one valid cable id."
                            raise ValueError(msg)
                        else:
                            msg = (
                                "Cable provided doesn't exist in the current project. Please provide an existing"
                                " cable id."
                            )
                            raise ValueError(msg)
                            # Set default values if one or more keys are empty
                        if [
                            x
                            for x in cable_twisted_pair_properties["TwistedPairParams"]
                            if cable_twisted_pair_properties["TwistedPairParams"][x] in ("", [], None, 0, False)
                        ]:
                            self.assign_cable_to_twisted_pair = self.existing_straight_wire_cables_names[0]
                            self.is_lay_length_specified = "False"
                            self.lay_length = "14mm"
                            self.turns_per_meter = "72"
                        else:
                            self.is_lay_length_specified = cable_twisted_pair_properties["TwistedPairParams"][
                                "IsLayLengthSpecified"
                            ]
                            self.lay_length = cable_twisted_pair_properties["TwistedPairParams"]["LayLength"]
                            self.turns_per_meter = cable_twisted_pair_properties["TwistedPairParams"]["TurnsPerMeter"]
            except ValueError as e:
                self._app.logger.error(str(e))

        # Add Cable to Bundle
        if json_dict["Add_CablesToBundle"].lower() == "true":
            if json_dict["CablesToBundle_prop"]["CablesToAdd"]:
                if isinstance(json_dict["CablesToBundle_prop"]["CablesToAdd"], list):
                    self.cables_to_add_to_bundle = json_dict["CablesToBundle_prop"]["CablesToAdd"]
                elif isinstance(json_dict["CablesToBundle_prop"]["CablesToAdd"], str):
                    self.cables_to_add_to_bundle = [json_dict["CablesToBundle_prop"]["CablesToAdd"]]
                if json_dict["CablesToBundle_prop"]["BundleCable"]:
                    self.bundle_cable = json_dict["CablesToBundle_prop"]["BundleCable"]
                if json_dict["CablesToBundle_prop"]["NumberOfCableToAdd"]:
                    self.number_of_cables_to_add = json_dict["CablesToBundle_prop"]["NumberOfCableToAdd"]
                else:
                    self.number_of_cables_to_add = 2

        # Remove Cable
        if json_dict["Remove_Cable"].lower() == "true":
            self.cables_to_remove = [json_dict["Cable_prop"]["CablesToRemove"]]

        # Source implementation
        # Check whether both add and update source are True -> not possible.
        try:
            if json_dict["Add_Source"].lower() == "true" and json_dict["Update_Source"].lower() == "true":
                msg = "Add_Source and Update_Source fields can't have the same value."
                raise ValueError(msg)
        except ValueError as e:
            self._app.logger.error(str(e))
        if json_dict["Add_Source"].lower() == "true" or json_dict["Update_Source"].lower() == "true":
            if json_dict["Update_Source"].lower() == "true":
                json_dict["Source_prop"]["AddClockSource"] = "False"
                json_dict["Source_prop"]["AddPwlSource"] = "False"
            elif json_dict["Add_Source"].lower() == "true":
                json_dict["Source_prop"]["UpdateClockSource"] = "False"
                json_dict["Source_prop"]["UpdatePwlSource"] = "False"
            # Check whether both add and update source are True in Source_prop -> not possible.
            try:
                if (
                    json_dict["Source_prop"]["AddClockSource"].lower() == "true"
                    and json_dict["Source_prop"]["UpdateClockSource"].lower() == "true"
                ):
                    msg = "AddClockSource and UpdateClockSource fields can't have the same value."
                    raise ValueError(msg)
                if (
                    json_dict["Source_prop"]["AddPwlSource"].lower() == "true"
                    and json_dict["Source_prop"]["UpdatePwlSource"].lower() == "true"
                ):
                    msg = "AddPwlSource and UpdatePwlSource fields can't have the same value."
                    raise ValueError(msg)
            except ValueError as e:
                self._app.logger.error(str(e))

            try:
                # Check if user action is to add a clock source or update
                if (
                    json_dict["Source_prop"]["AddClockSource"].lower() == "true"
                    or json_dict["Source_prop"]["UpdateClockSource"].lower() == "true"
                ):
                    source_properties = json_dict["CableManager"]["TDSources"]["ClockSourceDef"]
                    if json_dict["Source_prop"]["UpdateClockSource"].lower() == "true":
                        self.updated_source_name = json_dict["Source_prop"]["UpdatedSourceName"]
                        if source_properties["TDSourceAttribs"]["Name"]:
                            self.source_name = source_properties["TDSourceAttribs"]["Name"]
                        else:
                            msg = "Provide source name to update."
                            raise ValueError(msg)
                    else:
                        if source_properties["TDSourceAttribs"]["Name"]:
                            self.source_name = source_properties["TDSourceAttribs"]["Name"]
                        else:
                            self.source_name = generate_unique_name("clock")

                    self.source_period = "35us"
                    if source_properties["ClockSignalParams"]["Period"]:
                        if decompose_variable_value(source_properties["ClockSignalParams"]["Period"])[1] not in [
                            "fs",
                            "ps",
                            "ns",
                            "us",
                            "ms",
                            "s",
                            "min",
                            "hour",
                            "day",
                        ]:
                            msg = "Period's unit provided is not valid."
                            raise ValueError(msg)
                        else:
                            self.source_period = source_properties["ClockSignalParams"]["Period"]

                    self.low_pulse_value = "0V"
                    if source_properties["ClockSignalParams"]["LowPulseVal"]:
                        if decompose_variable_value(source_properties["ClockSignalParams"]["LowPulseVal"])[1] not in [
                            "fV",
                            "pV",
                            "nV",
                            "uV",
                            "mV",
                            "V",
                            "kV",
                            "megV",
                            "gV",
                            "dBV",
                        ]:
                            msg = "Low Pulse Value's unit provided is not valid."
                            raise ValueError(msg)
                        else:
                            self.low_pulse_value = source_properties["ClockSignalParams"]["LowPulseVal"]

                    self.high_pulse_value = "1V"
                    if source_properties["ClockSignalParams"]["HighPulseVal"]:
                        if decompose_variable_value(source_properties["ClockSignalParams"]["HighPulseVal"])[1] not in [
                            "fV",
                            "pV",
                            "nV",
                            "uV",
                            "mV",
                            "V",
                            "kV",
                            "megV",
                            "gV",
                            "dBV",
                        ]:
                            msg = "High Pulse Value's unit provided is not valid."
                            raise ValueError(msg)
                        else:
                            self.high_pulse_value = source_properties["ClockSignalParams"]["HighPulseVal"]

                    self.rise_time = "5us"
                    if source_properties["ClockSignalParams"]["Risetime"]:
                        if decompose_variable_value(source_properties["ClockSignalParams"]["Risetime"])[1] not in [
                            "fs",
                            "ps",
                            "ns",
                            "us",
                            "ms",
                            "s",
                            "min",
                            "hour",
                            "day",
                        ]:
                            msg = "Rise time unit provided is not valid."
                            raise ValueError(msg)
                        else:
                            self.rise_time = source_properties["ClockSignalParams"]["Risetime"]

                    self.fall_time = "5us"
                    if source_properties["ClockSignalParams"]["Falltime"]:
                        if decompose_variable_value(source_properties["ClockSignalParams"]["Falltime"])[1] not in [
                            "fs",
                            "ps",
                            "ns",
                            "us",
                            "ms",
                            "s",
                            "min",
                            "hour",
                            "day",
                        ]:
                            msg = "Fall time unit provided is not valid."
                            raise ValueError(msg)
                        else:
                            self.fall_time = source_properties["ClockSignalParams"]["Falltime"]

                    self.pulse_width = "20us"
                    if source_properties["ClockSignalParams"]["PulseWidth"]:
                        if decompose_variable_value(source_properties["ClockSignalParams"]["PulseWidth"])[1] not in [
                            "fs",
                            "ps",
                            "ns",
                            "us",
                            "ms",
                            "s",
                            "min",
                            "hour",
                            "day",
                        ]:
                            msg = "Pulse width unit provided is not valid."
                            raise ValueError(msg)
                        else:
                            self.pulse_width = source_properties["ClockSignalParams"]["PulseWidth"]
                # Check if user action is to add a pwl source or update
                elif (
                    json_dict["Source_prop"]["AddPwlSource"].lower() == "true"
                    or json_dict["Source_prop"]["UpdatePwlSource"].lower() == "true"
                ):
                    # Check if user wants to add pwl source from file
                    if json_dict["Source_prop"]["AddPwlSourceFromFile"]:
                        self.pwl_source_file_path = json_dict["Source_prop"]["AddPwlSourceFromFile"]
                    else:
                        pwl_source_properties = json_dict["CableManager"]["TDSources"]["PWLSourceDef"]
                        # Check if user wants to update pwl source
                        if json_dict["Source_prop"]["UpdatePwlSource"].lower() == "true":
                            self.updated_pwl_source_name = json_dict["Source_prop"]["UpdatedSourceName"]
                            if (
                                pwl_source_properties["TDSourceAttribs"]
                                and "Name" in pwl_source_properties["TDSourceAttribs"]
                            ):
                                self.pwl_source_name = pwl_source_properties["TDSourceAttribs"]["Name"]
                            else:
                                msg = "Provide a pwl source name to update."
                                raise ValueError(msg)
                        # If user doesn't want to update pwl source a pwl source is added manually
                        else:
                            if (
                                pwl_source_properties["TDSourceAttribs"]
                                and "Name" in pwl_source_properties["TDSourceAttribs"]
                            ):
                                self.pwl_source_name = pwl_source_properties["TDSourceAttribs"]["Name"]
                            else:
                                self.pwl_source_name = generate_unique_name("pwl")

                        # User wants to manually add/update pwl source values
                        if (
                            pwl_source_properties["PWLSignalParams"]["SignalValues"][0]
                            != pwl_source_properties["PWLSignalParams"]["SignalValues"][-1]
                        ):
                            msg = "First and Last element of voltage list must be equal to each other."
                            raise ValueError(msg)
                        else:
                            self.signal_values = pwl_source_properties["PWLSignalParams"]["SignalValues"]
                        self.time_values = pwl_source_properties["PWLSignalParams"]["TimeValues"]
            except ValueError as e:
                self._app.logger.error(str(e))

        # Check if user action is to remove the source
        if json_dict["Remove_Source"].lower() == "true":
            self.source_to_remove = json_dict["Source_prop"]["SourcesToRemove"]

        # Cable Harness implementation
        if json_dict["Add_CableHarness"].lower() == "true":
            try:
                if json_dict["CableHarness_prop"]["Name"]:
                    self.cable_harness_name = json_dict["CableHarness_prop"]["Name"]
                else:
                    self.cable_harness_name = generate_unique_name("cable_harness")

                if json_dict["CableHarness_prop"]["Bundle"] not in self.existing_bundle_cables_names:
                    msg = "Cable bundle name doesn't exist in the current project."
                    raise ValueError(msg)
                else:
                    self.cable_harness_bundle = json_dict["CableHarness_prop"]["Bundle"]

                if decompose_variable_value(json_dict["CableHarness_prop"]["TwistAngleAlongRoute"])[1] not in [
                    "deg",
                    "degmin",
                    "degsec",
                    "rad",
                ]:
                    msg = "Angle's unit provided is not valid."
                    raise ValueError(msg)
                else:
                    self.twist_angle_along_route = json_dict["CableHarness_prop"]["TwistAngleAlongRoute"]

                if not [
                    x
                    for x in self._app.modeler.object_names
                    if json_dict["CableHarness_prop"]["Polyline"].lower() == x.lower()
                ]:
                    msg = "Polyline doesn't exist in the current project."
                    raise ValueError(msg)
                else:
                    self.cable_harness_polyline = [
                        x
                        for x in self._app.modeler.object_names
                        if json_dict["CableHarness_prop"]["Polyline"].lower() == x.lower()
                    ][0]

                if (
                    json_dict["CableHarness_prop"]["AutoOrient"].lower() == "true"
                    or json_dict["CableHarness_prop"]["AutoOrient"].lower() == "false"
                ):
                    self.cable_harness_auto_orient = json_dict["CableHarness_prop"]["AutoOrient"].title()
                    if json_dict["CableHarness_prop"]["AutoOrient"].lower() == "false":
                        if json_dict["CableHarness_prop"]["XAxis"] not in ["Undefined", "NewVector"]:
                            msg = "Invalid value for cable harness x axis."
                            raise ValueError(msg)
                        elif json_dict["CableHarness_prop"]["XAxis"] == "NewVector":
                            if [
                                x
                                for x in json_dict["CableHarness_prop"]["XAxisOrigin"]
                                if decompose_variable_value(x)[1] != self._app.modeler.model_units
                            ]:
                                msg = "Provided units for x axis origin point are not valid."
                                raise ValueError(msg)
                            else:
                                self.cable_harness_x_axis_origin = json_dict["CableHarness_prop"]["XAxisOrigin"]

                            if [
                                x
                                for x in json_dict["CableHarness_prop"]["XAxisEnd"]
                                if decompose_variable_value(x)[1] != self._app.modeler.model_units
                            ]:
                                msg = "Provided units for x axis end point are not valid."
                                raise ValueError(msg)
                            else:
                                self.cable_harness_x_axis_end_point = json_dict["CableHarness_prop"]["XAxisEnd"]
                        elif json_dict["CableHarness_prop"]["XAxis"] == "Undefined":
                            self.cable_harness_x_axis_origin = ["0mm", "0mm", "0mm"]
                            self.cable_harness_x_axis_end_point = ["0mm", "0mm", "0mm"]
                    elif json_dict["CableHarness_prop"]["AutoOrient"].lower() == "true":
                        self.cable_harness_x_axis_origin = ["0mm", "0mm", "0mm"]
                        self.cable_harness_x_axis_end_point = ["0mm", "0mm", "0mm"]
                else:
                    msg = "Provide  valid value for auto orientation boolean."
                    raise ValueError(msg)

                if (
                    json_dict["CableHarness_prop"]["ReverseYAxisDirection"].lower() == "true"
                    or json_dict["CableHarness_prop"]["ReverseYAxisDirection"].lower() == "false"
                ):
                    self.reverse_y_axis_direction = json_dict["CableHarness_prop"]["ReverseYAxisDirection"]
                else:
                    msg = "Provide  valid value for y axis direction boolean."
                    raise ValueError(msg)

                if [x for x in json_dict["CableHarness_prop"]["CableTerminationsToInclude"]]:
                    cable_terminations_to_include = json_dict["CableHarness_prop"]["CableTerminationsToInclude"]
                    self.args = []
                    terminations = []
                    input_terminations = ["NAME:InputTerminations"]
                    output_terminations = ["NAME:OutputTerminations"]
                    assignment_type = ["Imped:=", "50ohm"]
                    # Default values for input and output terminations set to ["Imped:=", "50ohm"]
                    for cable in [
                        x.get(self.cable_harness_bundle)
                        for x in self.cables_in_bundle_list_dict
                        if self.cable_harness_bundle in x.keys()
                    ][0]:
                        input_terminations.append("{}:=".format(cable))
                        input_terminations.append(assignment_type)
                        output_terminations.append("{}:=".format(cable))
                        output_terminations.append(assignment_type)
                    terminations.append(input_terminations)
                    terminations.append(output_terminations)
                    for cable_termination in cable_terminations_to_include:
                        if (
                            cable_termination["CableName"]
                            in [
                                cable.get(self.cable_harness_bundle)
                                for cable in self.cables_in_bundle_list_dict
                                if self.cable_harness_bundle in cable.keys()
                            ][0]
                        ):
                            if cable_termination["Assignment"] not in [
                                "Reference Conductor",
                                "Input Terminations",
                                "Output Terminations",
                            ]:
                                msg = "Invalid cable harness assignment."
                                raise ValueError(msg)
                            elif cable_termination["Assignment"] == "Reference Conductor":
                                ref_cond = ["NAME:RefConductors", cable_termination["CableName"]]
                                self.args.append(ref_cond)
                            elif (
                                cable_termination["Assignment"] == "Input Terminations"
                                or cable_termination["Assignment"] == "Output Terminations"
                            ):
                                if cable_termination["Assignment"] == "Input Terminations" and terminations[0].index(
                                    "{}:=".format(cable_termination["CableName"])
                                ):
                                    cable_index = terminations[0].index("{}:=".format(cable_termination["CableName"]))
                                    input_output = 0
                                elif cable_termination["Assignment"] == "Output Terminations" and terminations[1].index(
                                    "{}:=".format(cable_termination["CableName"])
                                ):
                                    cable_index = terminations[0].index("{}:=".format(cable_termination["CableName"]))
                                    input_output = 1
                                else:
                                    msg = "Invalid cable name."
                                    raise ValueError(msg)
                                if cable_termination["AssignmentType"] == "Impedance":
                                    if decompose_variable_value(cable_termination["Impedance"])[1] not in [
                                        "GOhm",
                                        "kOhm",
                                        "megohm",
                                        "mohm",
                                        "ohm",
                                        "uohm",
                                    ]:
                                        msg = "Invalid impedance unit."
                                        raise ValueError(msg)
                                    else:
                                        terminations[input_output][cable_index + 1] = [
                                            "Imped:=",
                                            cable_termination["Impedance"],
                                        ]
                                elif cable_termination["AssignmentType"] == "Source":
                                    terminations[input_output][cable_index + 1] = [
                                        "Source:=",
                                        '"{}"'.format(cable_termination["Source"]["Signal"]),
                                        "Imped:=",
                                        cable_termination["Source"]["ImpedanceValue"],
                                    ]
                                    if cable_termination["Source"]["Type"] not in ["Single Value", "Transient"]:
                                        msg = "Invalid source type value."
                                        raise ValueError(msg)
                                    elif cable_termination["Source"]["Type"] == "Transient":
                                        if cable_termination["Source"]["Signal"] not in self.existing_sources_names:
                                            msg = "Source name doesn't exist in current project."
                                            raise ValueError(msg)
                                    elif cable_termination["Source"]["Type"] == "Single Value":
                                        if decompose_variable_value(cable_termination["Source"]["Signal"])[1] not in [
                                            "fV",
                                            "pV",
                                            "nV",
                                            "uV",
                                            "mV",
                                            "V",
                                            "kV",
                                            "megV",
                                            "gV",
                                            "dBV",
                                        ] and decompose_variable_value(cable_termination["Source"]["ImpedanceValue"])[
                                            1
                                        ] not in [
                                            "GOhm",
                                            "kOhm",
                                            "megohm",
                                            "mohm",
                                            "ohm",
                                            "uohm",
                                        ]:
                                            msg = "Invalid source signal units."
                                            raise ValueError(msg)
                                        else:
                                            terminations[input_output][cable_index + 1] = [
                                                "Source:=",
                                                cable_termination["Source"]["Signal"],
                                                "Imped:=",
                                                cable_termination["Source"]["ImpedanceValue"],
                                            ]
                    self.args.append(terminations[0])
                    self.args.append(terminations[1])
                else:
                    msg = "Provide at least one cable to include when creating cable harness."
                    raise ValueError(msg)

            except ValueError as e:
                self._app.logger.error(str(e))

    def _cable_properties_parser(self, omodule, working_dir):
        file_path_export = os.path.join(working_dir, "export_cable_library_test.txt")
        omodule.ExportCableLibrary(file_path_export)
        file_path_export_as_json = os.path.join(working_dir, "export_cable_library_as_json_test.json")
        with open(file_path_export_as_json, "w") as f:
            json.dump(load_entire_aedt_file(file_path_export), f)
        return load_entire_aedt_file(file_path_export)
