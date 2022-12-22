"""
WBFlowAutomation
----------------

Disclaimer
==========

**Copyright (c) 1986-2021, ANSYS Inc. unauthorised use, distribution or duplication is prohibited**

**This tool release is unofficial and not covered by standard Ansys Support license.**


Description
==================================================================

This class contains the link to Workbench


================================================================

"""

import csv
import os
import random
import re
import shutil

# import socket
import subprocess
import time

# import logging
import traceback

from pyaedt import pyaedt_logger
from pyaedt.generic.filesystem import pyaedt_dir
from pyaedt.workbench.WB2Client import WB2Client


class DataAttr:
    def __init__(self, arguments):
        for el in arguments:
            setattr(self, el, arguments[el])


class MeshData(object):
    def __init__(self):
        self._assign_global_mesh = None
        self._assign_local_mesh = []
        self._assign_local_sweep = []

    def assign_local_mesh(self, mesh_size=None, name=None, name_selection=False, curvature=False, mesh_refinement=1):
        self._assign_local_mesh.append(
            DataAttr(
                {
                    "mesh_size": mesh_size,
                    "name": name,
                    "name_selection": name_selection,
                    "curvature": curvature,
                    "mesh_refinement": mesh_refinement,
                }
            )
        )

    def assign_global_mesh(self, curvature=False, defeaturing=False, mesh_refinement=1):
        self._assign_global_mesh = DataAttr(
            {"curvature": curvature, "defeaturing": defeaturing, "mesh_refinement": mesh_refinement}
        )

    def assign_local_sweep(self, divisions, name=None, name_selection=True):
        self._assign_local_sweep.append(
            DataAttr({"divisions": divisions, "name": name, "name_selection": name_selection})
        )


class SetupData(object):
    def __init__(self):
        self.emissivity = [0.8]
        self.convection_dict = {0: 1e-6, 100: 1e-5}
        self.ambient_temperature = 22
        self.weak_springs = False
        self.numcores = 4
        self.version = 212
        self.gravity = "-Z"
        self._import_hfss_load_structural = []
        self._import_hfss_load_thermal = []
        self._import_hfss_load_thermal_JS = []
        self._add_command = []
        self._add_convection = []
        self._add_radiation = []
        self._define_initial_temperature_thermal = None
        self._define_environment_temperature = None
        self._create_fixed_support_pcb = []
        self._create_frictionless = []
        self._create_structural_setup = None
        self._import_fld_load = []

    def import_hfss_load_structural(self, ns_bodies, hfss_solution=1, mapping_weighting=1):
        self._import_hfss_load_structural.append(
            DataAttr({"ns_bodies": ns_bodies, "hfss_solution": hfss_solution, "mapping_weighting": mapping_weighting})
        )
        pass

    def import_hfss_load_thermal(self, ns_solvebodies, ns_solvefaces, hfss_solution=1, mapping_weighting=1):
        self._import_hfss_load_thermal.append(
            DataAttr(
                {
                    "ns_solvebodies": ns_solvebodies,
                    "ns_solvefaces": ns_solvefaces,
                    "hfss_solution": hfss_solution,
                    "mapping_weighting": mapping_weighting,
                }
            )
        )
        pass

    def import_hfss_load_thermal_JS(self, ns_solvebodies, ns_solvefaces, hfss_solution=1, mapping_weighting=1):
        self._import_hfss_load_thermal_JS.append(
            DataAttr(
                {
                    "ns_solvebodies": ns_solvebodies,
                    "ns_solvefaces": ns_solvefaces,
                    "hfss_solution": hfss_solution,
                    "mapping_weighting": mapping_weighting,
                }
            )
        )
        pass

    # New functions
    def add_command(self, input_argument, parameter, parameter_name):
        self._add_command.append(
            DataAttr({"input_argument": input_argument, "parameter": parameter, "parameter_name": parameter_name})
        )
        pass

    def add_convection(self, ns_external_surface, convection=None, AmbientTemp=None):
        if not convection:
            convection = self.convection_dict
        if not AmbientTemp:
            AmbientTemp = self.ambient_temperature
        self._add_convection.append(
            DataAttr({"convection": convection, "ns_external_surface": ns_external_surface, "AmbientTemp": AmbientTemp})
        )
        pass

    def add_radiation(self, ns_external_surface, emissivity=None, AmbientTemp=None, correlation=None):
        if not emissivity:
            emissivity = self.emissivity[0]
        if not AmbientTemp:
            AmbientTemp = self.ambient_temperature
        if not correlation:
            correlation = 0
        self._add_radiation.append(
            DataAttr(
                {
                    "emissivity": emissivity,
                    "ns_external_surface": ns_external_surface,
                    "AmbientTemp": AmbientTemp,
                    "correlation": correlation,
                }
            )
        )

    def define_initial_temperature_thermal(self, temperature=None):
        if not temperature:
            temperature = self.ambient_temperature
        self._define_initial_temperature_thermal = DataAttr({"temperature": temperature})
        pass

    def define_environment_temperature(self, temperature=None):
        if not temperature:
            temperature = self.ambient_temperature
        self._define_environment_temperature = DataAttr({"temperature": temperature})
        pass

    def create_fixed_support_pcb(self, component_name, gravity=None):
        if not gravity:
            gravity = self.gravity
        self._create_fixed_support_pcb.append(DataAttr({"component_name": component_name, "gravity": gravity}))
        pass

    def create_frictionless(self, gravity=None):
        if not gravity:
            gravity = self.gravity
        self._create_frictionless.append(DataAttr({"gravity": gravity}))
        pass

    def create_structural_setup(self, WeakSpring=None, MechNumCores=None, version=None):
        if not WeakSpring:
            WeakSpring = self.weak_springs
        if not MechNumCores:
            MechNumCores = self.numcores
        if not version:
            version = self.version
        self._create_structural_setup = DataAttr(
            {"WeakSpring": WeakSpring, "MechNumCores": MechNumCores, "version": version}
        )
        pass

    # TO BE REFACTOR
    def import_fld_load(self, ns_bodies, file=1):
        self._import_fld_load.append(DataAttr({"ns_bodies": ns_bodies, "file": file}))
        pass


class GeometryData(object):
    def __init__(self):
        self._resize_ui = None
        self._assign_material = None
        self._create_body_name_selection = []
        self._create_body_name_selection_auto = []
        self._create_face_name_selection = []
        self._create_externalface_name_selection = None
        self._create_supportface_name_selection = None
        self._find_external_faces = []
        self._find_object_face_gravity = []
        self._select_body = []
        self.assign_units = None
        self.suppressed_solids_list = []
        self.chassis_solids_list = []
        self.material_assignment_dict = {}
        self.dielectrics_list = []
        self.metals_list = []

        # LEGACY
        self._create_name_selection = None
        self._body_selection = []
        self._body_selection_bylist = []
        self._face_selection = []
        self._face_selection_bylist = []

    def resize_ui(self, ui):
        self._resize_ui = DataAttr({"ui": ui})
        pass

    def assign_material(self):
        self._assign_material = DataAttr({})
        pass

    def create_body_name_selection(self, ns_name, objects):
        self._create_body_name_selection.append(DataAttr({"ns_name": ns_name, "objects": objects}))
        pass

    def create_body_name_selection_auto(self, ns_name, ns_allbodies=True, ns_positive=True, find_name=None):
        self._create_body_name_selection_auto.append(
            DataAttr(
                {"ns_name": ns_name, "ns_allbodies": ns_allbodies, "ns_positive": ns_positive, "find_name": find_name}
            )
        )
        pass

    def create_face_name_selection(self, ns_name, objects):
        self._create_face_name_selection.append(DataAttr({"ns_name": ns_name, "objects": objects}))
        pass

    def create_externalface_name_selection(self, ns_name):
        self._create_externalface_name_selection = DataAttr({"ns_name": ns_name})
        pass

    def create_supportface_name_selection(self, ns_name, gravity, objects):
        self._create_supportface_name_selection = DataAttr({"ns_name": ns_name, "gravity": gravity, "objects": objects})
        pass

    # Refactoring new functions
    def find_external_faces(self):
        self._find_external_faces.append(DataAttr({}))
        pass

    def find_object_face_gravity(self, object_name, gravity):
        self._find_object_face_gravity.append(DataAttr({"object_name": object_name, "gravity": gravity}))
        pass

    def face_selection(self, ns_allfaces=True, ns_positive=True, find_name=str()):
        self._face_selection.append(
            DataAttr({"ns_allfaces": ns_allfaces, "ns_positive": ns_positive, "find_name": find_name})
        )
        pass

    def face_selection_bylist(self, find_objects=[]):
        self._face_selection_bylist.append(DataAttr({"find_objects": find_objects}))
        pass

    # LEGACY
    def create_name_selection(self, bodies, ns_name):
        self._create_name_selection = DataAttr({"bodies": bodies, "ns_name": ns_name})
        pass

    def body_selection(self, ns_allbodies=True, ns_positive=True, find_name=str()):
        self._body_selection.append(
            DataAttr({"ns_allbodies": ns_allbodies, "ns_positive": ns_positive, "find_name": find_name})
        )
        pass

    def body_selection_bylist(self, find_objects=[]):
        self._body_selection_bylist.append(DataAttr({"find_objects": find_objects}))
        pass

    def select_body(self, component):
        self._select_body.append(DataAttr({"component": component}))
        pass


class TraceMappingData(object):
    def __init__(self):
        self.mesh_size = 0.01
        self.DefaultDiscretization = False
        self.Xdiscretization = 200
        self.Ydiscretization = 200
        self.XSize = 0.01
        self.YSize = 0.01
        self.fileIndex = 1
        self.TraceMaterial = "Structural Steel"
        self.PlatingMaterial = "Structural Steel"
        self.ViaFilled = False
        self.ViaFillMaterial = "Structural Steel"
        self.platingThickness = 0.0001  # m
        self._get_material_name = None
        self._setup_trace_mapping_on_named_selection = None
        self._fill_details_of_imported_trace = None
        self._fill_worksheet_of_imported_trace = None

    def get_material_name(self, nameToSearch):
        self._get_material_name = DataAttr({"nameToSearch": nameToSearch})
        pass

    def setup_trace_mapping_on_named_selection(
        self,
        ns_pcb,
        mesh_size=None,
        Xdiscretization=None,
        Ydiscretization=None,
        DefaultDiscretization=None,
        XSize=None,
        YSize=None,
        TraceMaterial=None,
        ViaFilled=None,
        ViaFillMaterial=None,
        PlatingMaterial=None,
        platingThickness=None,
    ):
        if not mesh_size:
            mesh_size = self.mesh_size
        if not Xdiscretization:
            Xdiscretization = self.Xdiscretization
        if not Ydiscretization:
            Ydiscretization = self.Ydiscretization
        if not DefaultDiscretization:
            DefaultDiscretization = self.DefaultDiscretization
        if not XSize:
            XSize = self.XSize
        if not YSize:
            YSize = self.YSize
        if not TraceMaterial:
            TraceMaterial = self.TraceMaterial
        if not ViaFilled:
            ViaFilled = self.ViaFilled
        if not ViaFillMaterial:
            ViaFillMaterial = self.ViaFillMaterial
        if not PlatingMaterial:
            PlatingMaterial = self.PlatingMaterial
        if not platingThickness:
            platingThickness = self.platingThickness

        self._setup_trace_mapping_on_named_selection = DataAttr(
            {
                "ns_pcb": ns_pcb,
                "mesh_size": mesh_size,
                "Xdiscretization": Xdiscretization,
                "Ydiscretization": Ydiscretization,
                "DefaultDiscretization": DefaultDiscretization,
                "XSize": XSize,
                "YSize": YSize,
                "TraceMaterial": TraceMaterial,
                "ViaFilled": ViaFilled,
                "ViaFillMaterial": ViaFillMaterial,
                "PlatingMaterial": PlatingMaterial,
                "platingThickness": platingThickness,
            }
        )
        pass

    def fill_details_of_imported_trace(self, importedTrace, NS_PCB):
        self._fill_details_of_imported_trace = DataAttr({"importedTrace": importedTrace, "NS_PCB": NS_PCB})

        pass

    def fill_worksheet_of_imported_trace(self, importedTrace):
        self._fill_worksheet_of_imported_trace = DataAttr({"importedTrace": importedTrace})

        pass


class ReportData(object):
    def __init__(self):
        self._total_deformation = []
        self._equivalent_stress = []
        self._temperature = []
        self._user_defined_deformation_report = []

    def total_deformation(self, report_name="AllBodies", name_selection=None, view=None):
        self._total_deformation.append(
            DataAttr({"report_name": report_name, "name_selection": name_selection, "view": view})
        )

    def equivalent_stress(self, report_name="AllBodies", name_selection=None, view=None):
        self._equivalent_stress.append(
            DataAttr({"report_name": report_name, "name_selection": name_selection, "view": view})
        )

    def temperature(self, report_name="AllBodies", name_selection=None, view=None):
        self._temperature.append(DataAttr({"report_name": report_name, "name_selection": name_selection, "view": view}))

    def user_defined_deformation_report(self, view=None, position=None):
        self._user_defined_deformation_report.append(DataAttr({"view": view, "position": position}))


# def _find_free_port(port_start=50001, port_end=60000):
#     list_ports = random.sample(range(port_start, port_end), port_end - port_start)
#     s = socket.socket()
#     for port in list_ports:
#         try:
#             s.connect((socket.getfqdn(), port))
#         except socket.error:
#             s.close()
#             return port
#         else:
#             s.close()
#     return 0


def _port_is_free(port):
    """
    This method enables to check if a port is free before we serve on it
    More stable than using socket package
    """
    out = subprocess.Popen(
        ["netstat", "-an", "-p", "tcp"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding="utf8"
    )
    (data, err) = out.communicate()

    lines = data.splitlines()
    """
      TCP    192.168.1.8:64763      192.168.1.8:8089       TIME_WAIT
    """
    occupied_ports = set(range(1030))
    pattern = re.compile(r"^\s*TCP\s+[0-9]{1,3}(\.[0-9]{1,3}){3}\:(?P<port>[0-9]{1,5})\s+.+")
    for line in lines:
        m = pattern.search(line)
        if m:
            occupied_ports.add(int(m.group("port")))
    return port not in occupied_ports


def _free_port_in_range(start, stop):
    if not isinstance(start, int) or not isinstance(stop, int):
        raise TypeError("start and stop must be integers.")
    if start >= stop:
        raise ValueError("stop must be larger than start")
    shuffled_range = random.sample(range(start, stop + 1), (stop + 1 - start))
    for port in shuffled_range:
        if _port_is_free(port):
            return port
    return False


class AutomateWB:
    """
    Class that manages connection with Workbench using socket connection


    """

    def __init__(
        self,
        project_fullname,
        results_path=None,
        pictures_path=None,
        WBGui=True,
        MechGui=True,
        hostname="localhost",
        sWorkbenchVersion="2022.2",
        useSC=True,
        useDM=False,
        materialHFSS=False,
        AEDTproject_fullname=None,
        GEOMproject_fullname=None,
        TempMap_fullname=None,
        PCB_fullname=None,
        AEDTMatproject_fullname=None,
    ):
        self.logger = pyaedt_logger
        values = sWorkbenchVersion.split(".")
        version = int(values[0][2:])
        release = int(values[1])
        if version < 20:
            if release < 3:
                version += 1
            else:
                release += 2
        version_number = str(version) + str(release)
        self.version = version_number

        self.hostName = hostname
        self.portNumber = _free_port_in_range(40001, 50000)
        self.client = WB2Client(self.portNumber, self.hostName, WBGui, "AWP_ROOT" + self.version)
        self._project_fullname = project_fullname
        self._results_path = results_path
        self._pictures_path = pictures_path

        self.Gui = WBGui
        self.MechGui = MechGui
        self.use_spaceclaim = useSC
        self.useDM = useDM
        self.materialHFSS = materialHFSS
        self.CaptureCurvatureInMesh = True

        self.mesh_data = MeshData()
        self.geo_data = GeometryData()
        self.setup_data = SetupData()
        self.trace_mapping_data = TraceMappingData()
        self.report_data = ReportData()
        # self.export_mechanical_script()
        # self.export_report_script()

        self._AEDTproject_name = AEDTproject_fullname
        self._AEDTMatproject_name = AEDTMatproject_fullname
        self._GEOMproject_name = GEOMproject_fullname
        self._TempMap_name = TempMap_fullname
        self._PCB_name = PCB_fullname

    @property
    def project_fullname(self):
        return self._project_fullname.replace("\\", "/")

    @property
    def name(self):
        return os.path.splitext(os.path.basename(self._project_fullname))[0]  # project_name

    @property
    def project_path(self):
        return os.path.dirname(self._project_fullname).replace("\\", "/")

    @property
    def results_path(self):
        if self._results_path:
            return self._results_path.replace("\\", "/")
        else:
            return os.path.join(self.project_path, self.name + "_Results").replace("\\", "/")

    @property
    def pictures_path(self):
        if self._pictures_path:
            return self._pictures_path.replace("\\", "/")
        else:
            return os.path.join(self.project_path, self.name + "_Results").replace("\\", "/")

    @property
    def AEDTproject_name(self):
        if self._AEDTproject_name:
            return self._AEDTproject_name.replace("\\", "/")
        else:
            return None

    @property
    def AEDTMatproject_name(self):
        if self._AEDTMatproject_name:
            return self._AEDTMatproject_name.replace("\\", "/")
        else:
            return None

    @property
    def GEOMproject_name(self):
        if self._GEOMproject_name:
            return self._GEOMproject_name.replace("\\", "/")
        else:
            return None

    @property
    def TempMap_name(self):
        if self._TempMap_name:
            return self._TempMap_name.replace("\\", "/")
        else:
            return None

    @property
    def PCB_name(self):
        if self._PCB_name:
            return self._PCB_name.replace("\\", "/")
        else:
            return None

    def __exit__(self, ex_type, ex_value, ex_traceback):
        # Write the trace stack to the log file if an exception occurred in the main script
        if ex_type:
            self._exception(ex_value, ex_traceback)

    def __enter__(self):
        return self

    def _exception(self, ex_value, tb_data):
        """
        writes the trace stack to the desktop when a python error occurs
        """
        tb_trace = traceback.format_tb(tb_data)
        tblist = tb_trace[0].split("\n")
        self.logger.error(str(ex_value))
        for el in tblist:
            self.logger.error(el)

    def _get_methods_and_vars(self, class_name, class_object, variables):
        write_val = ""
        for var in variables:
            try:
                object_name = class_object.__getattribute__("_" + var)
            except:
                continue

            if object_name:
                if type(object_name) is not list:
                    object_name = [object_name]
                if not isinstance(object_name[0], DataAttr):
                    continue
                for el in object_name:
                    write_val += "\n" + class_name + "."
                    write_val += var + "("
                    for att in dir(el):
                        if "_" not in att[0] and getattr(el, att) != None:
                            if type(getattr(el, att)) is not str:
                                write_val += att + "=" + str(getattr(el, att)) + ","
                            else:
                                write_val += att + '="' + str(getattr(el, att)) + '",'
                    if write_val[len(write_val) - 1] == ",":
                        write_val = write_val[:-1]
                    write_val += ")\n"

        return write_val

    def analyze_hfss(self, design_name):
        """
        Run the simulation of the HFSS (force to run).

        Arguments:
        design_name (str) = design name of the HFSS module
        """
        client = self.client
        self.logger.info("Simulating HFSS Project {}".format(design_name))
        string = "WB.analyze_hfss('" + str(design_name) + "')"
        mssg = self.send_command(string, client)
        parse_mssg = self.parse_string(mssg)
        return parse_mssg

    def clear_wbmessages(self):
        """
        Get messages and clean message window
        :return:
        """
        client = self.client
        string = "ClearMessagess()"
        mssg = self.send_command(string, client)
        parse_mssg = self.parse_string(mssg)
        return parse_mssg

    def close(self):
        """
        Close Workbench
        """
        self.logger.info("Closing Workbench")
        client = self.client
        client.CloseWorkbench()
        time.sleep(3)
        return True

    def create_design_points(self, variables, values, createLabels=True):
        """
        createDesignPoints(self,variables,values,createLabels=True)
        Create Design Points In DesignXplorer based on a seto of variables and a list of values
        variables: list of variable names
        values: list of arrays of values
        createLabels: enable creation of labels
        """
        self.logger.info("Creating Design Points for DX...")

        client = self.client
        string = "inputVar=["
        for v in variables:
            string = string + chr(34) + str(v) + chr(34) + ","
        string = string[:-1] + "]"
        mssg = self.send_command(string, client)
        parse_mssg1 = self.parse_string(mssg)

        parse_mssg2 = True
        if createLabels:
            string = "inputLabels=["
            for v, val in zip(variables, values):
                try:
                    float(val[0])
                except Exception as e:
                    # print(str(e))
                    string = string + chr(34) + str(v) + "Label" + chr(34) + ","
            string = string[:-1] + "]"
            mssg = self.send_command(string, client)
            parse_mssg2 = self.parse_string(mssg)

        string = "varValues=["
        for v in values:
            string = string + "["
            id = 0
            for el in v:
                try:
                    float(el)
                    string = string + chr(34) + str(el) + chr(34) + ","

                except Exception as e:
                    print(str(e))
                    string = string + chr(34) + str(id) + chr(34) + ","
                    id = id + 1
            string = string[:-1] + "],"
        string = string[:-1] + "]"
        mssg = self.send_command(string, client)
        parse_mssg3 = self.parse_string(mssg)

        parse_mssg4 = True
        if createLabels:
            string = "labelValues=["
            for v in values:
                try:
                    float(v[0])
                except Exception as e:
                    print(str(e))
                    string = string + "["
                    for el in v:
                        string = string + chr(34) + chr(39) + str(el) + chr(39) + chr(34) + ","
                    string = string[:-1] + "],"
            string = string[:-1] + "]"
            mssg = self.send_command(string, client)
            parse_mssg4 = self.parse_string(mssg)

        if createLabels:
            string = "createLabels=True"
        else:
            string = "createLabels=False"

        mssg = self.send_command(string, client)
        parse_mssg5 = self.parse_string(mssg)
        mypath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "createDesignPoints.py")
        if os.path.exists(mypath):
            self.client.SendScriptFile(mypath)

        if parse_mssg1 and parse_mssg2 and parse_mssg3 and parse_mssg4 and parse_mssg5:
            parse_mssg = True
        else:
            parse_mssg = False

        return parse_mssg

    def create_feedback_iterator(self, numIterations, deltaT, deltaD, design_name):
        """
        Create Feedback iterator block and setup numIterations
        numIterations: integer with number of iterations
        design_name: HFSS Design name
        """
        self.logger.info("Creating Feedback Iterator")

        client = self.client
        string = (
            "WB.setup_iterations("
            + str(numIterations)
            + ","
            + str(deltaT)
            + ","
            + str(deltaD)
            + ",'"
            + str(design_name)
            + "')"
        )
        mssg = self.send_command(string, client)
        parse_mssg = self.parse_string(mssg)
        self.logger.info("Setup Completed...")

        return parse_mssg

    def create_structural_link(self):
        """
        Create a Link HFSS-Structural Mechanical. HFSS Design must be created before
        Geometry could come from SCDM, DM or HFSS
        Engineering Data could be linked from a second HFSS Design if it exists
        """
        self.logger.info("Creating Structural Mechanical Design")

        client = self.client

        string = "WB.create_structural_with_hfss()"
        mssg1 = self.send_command(string, client)
        parse_mssg1 = self.parse_string(mssg1)
        if self.materialHFSS:
            string = "WB.transfer_material_hfss2structural_ed()"
        else:
            string = "WB.transfer_hfss2structural_ed()"
        mssg2 = self.send_command(string, client)
        parse_mssg2 = self.parse_string(mssg2)
        if self.use_spaceclaim:
            string = "WB.link_geometry_scdm2structural()"
        elif self.useDM:
            string = "WB.link_geometry_dm2structural()"
        else:
            string = "WB.link_geometry_hfss2structural()"
        mssg3 = self.send_command(string, client)
        parse_mssg3 = self.parse_string(mssg3)
        string = "WB.link_setup_hfss2structural()"
        mssg4 = self.send_command(string, client)
        parse_mssg4 = self.parse_string(mssg4)

        if parse_mssg1 and parse_mssg2 and parse_mssg3 and parse_mssg4:
            parse_mssg = True
        else:
            parse_mssg = False

        return parse_mssg

    def create_structural_pcb_link(self):
        """
        Create a Link Structural Mechanical to Temperature Map
        """
        self.logger.info("Creating Link Structural Setup to Temperature Map")

        client = self.client
        string = "WB.link_setup_pcb2structural()"
        mssg = self.send_command(string, client)
        parse_mssg = self.parse_string(mssg)
        return parse_mssg

    def create_structural_temperaturemap_link(self):
        """
        Create a Link Structural Mechanical to Temperature Map
        """
        self.logger.info("Creating Link Structural Setup to Temperature Map")

        client = self.client
        string = "WB.link_setup_temperaturemap2structural()"
        mssg = self.send_command(string, client)
        parse_mssg = self.parse_string(mssg)
        return parse_mssg

    def create_structural_thermal_link(self):
        """
        Create a Link to Structural Mechanical with a Thermal Structural existing
        """
        self.logger.info("Creating Structural Mechanical Design")

        client = self.client

        string = "WB.create_structural_with_thermal()"
        mssg1 = self.send_command(string, client)
        parse_mssg1 = self.parse_string(mssg1)

        string = "WB.link_setup_hfss2thermalstructural()"
        mssg2 = self.send_command(string, client)
        parse_mssg2 = self.parse_string(mssg2)

        string = "WB.update_hfss()"
        mssg3 = self.send_command(string, client)
        parse_mssg3 = self.parse_string(mssg3)

        string = "Refresh()"
        mssg4 = self.send_command(string, client)
        parse_mssg4 = self.parse_string(mssg4)

        string = "WB.link_setup_thermal2structural()"
        mssg5 = self.send_command(string, client)
        parse_mssg5 = self.parse_string(mssg5)

        string = "Refresh()"
        mssg6 = self.send_command(string, client)
        parse_mssg6 = self.parse_string(mssg6)

        if parse_mssg1 and parse_mssg2 and parse_mssg3 and parse_mssg4 and parse_mssg5 and parse_mssg6:
            parse_mssg = True
        else:
            parse_mssg = False

        return parse_mssg

    def create_thermal_link(self):
        """
        Create a Link to thermal Mechanical this includes Engineering data which is cleaned by air and pec objects
        It also creates the link between HFSS and Mechanical in Workbench
        """
        self.logger.info("Creating Thermal Mechanical Design")

        client = self.client

        string = "WB.create_thermal_with_hfss()"
        mssg1 = self.send_command(string, client)
        parse_mssg1 = self.parse_string(mssg1)

        string = "WB.transfer_hfss2thermal_ed()"
        mssg2 = self.send_command(string, client)
        parse_mssg2 = self.parse_string(mssg2)
        if self.use_spaceclaim:
            string = "WB.link_geometry_scdm2thermal()"
        else:
            string = "WB.link_geometry_hfss2thermal()"
        mssg3 = self.send_command(string, client)
        parse_mssg3 = self.parse_string(mssg3)
        string = "WB.link_setup_hfss2thermal()"
        mssg4 = self.send_command(string, client)
        parse_mssg4 = self.parse_string(mssg4)

        if parse_mssg1 and parse_mssg2 and parse_mssg3 and parse_mssg4:
            parse_mssg = True
        else:
            parse_mssg = False

        return parse_mssg

    # def export_mechanical_script(self):
    #     """
    #     export_mechanical_script Function write a PY function for Mechanical API.
    #     From version 2021R1, JScript is not allowed.
    #     It start from createMech.py file and integrates it with variables and lanuchers.
    #
    #     - Added WBSuppressSolids option:
    #         1. the objects names specified in the list are suppessed in Workbench
    #         2. the list defaults to empty list
    #     """
    #
    #     Filename1 = os.path.join(self.project_path, '{0}.py'.format(self.name + "_Setup"))
    #     Filename1 = Filename1.replace('\\', '/')
    #     current_path = os.path.dirname(os.path.realpath(__file__))
    #     shutil.copy2(os.path.join(current_path, 'WB_MechWrapper.py'), Filename1)
    #
    #     Filename2 = os.path.join(self.project_path, '{0}.py'.format(self.name + "_Report"))
    #     Filename2 = Filename2.replace('\\', '/')
    #     shutil.copy2(os.path.join(current_path, 'WB_MechWrapper.py'), Filename2)
    #
    #     # Create callings to Mechanical classes and definitions
    #     return os.path.exists(os.path.join(current_path, 'WB_MechWrapper.py'))

    def export_mechanical_script_auto(self):
        """
        export_mechanical_script Function write a PY function for Mechanical API.
        It start from createMech.py file and integrates it with variables and lanuchers.

        - Added WBSuppressSolids option:
            1. the objects names specified in the list are suppessed in Workbench
            2. the list defaults to empty list
        """
        Filename1 = os.path.join(self.project_path, "{0}.py".format(self.name + "_Setup"))
        Filename1 = Filename1.replace("\\", "/")
        current_path = os.path.dirname(os.path.realpath(__file__))
        shutil.copy2(os.path.join(current_path, "WB_MechWrapper.py"), Filename1)

        # Filename = os.path.join(self.project_path, '{0}.py'.format(self.name + "_Setup"))
        # Filename = Filename.replace('\\', '/')
        with open(Filename1, "a+") as f:

            # Change Units
            f.write("\nExtAPI.Application.ActiveUnitSystem = MechanicalUnitSystem.")
            if self.geo_data.assign_units == "mm":
                f.write("StandardNMM\n")
            else:
                f.write("StandardMKS\n")

            f.write("\nDesktopMat = {}\n")
            for objName, matName in self.geo_data.material_assignment_dict.items():
                f.write('DesktopMat["SYS\{0}"] = "{1}", \n'.format(objName, matName))
                f.write('DesktopMat["{0}"] = "{1}"\n'.format(objName, matName))
                f.write('DesktopMat["{0}\{0}"] = "{1}"\n'.format(objName, matName))

            # Check Suppress bodies
            f.write("\nWBSuppressSolids = { \n")
            iObjI = 0
            for objName in self.geo_data.suppressed_solids_list:
                f.write('"SYS\{0}" : 1,\n'.format(objName))
                f.write('"{0}" : 1'.format(objName))
                iObjI += 1
                f.write(",\n")
            f.write("}\n")

            # Create NS SolvedBodies
            f.write("\nDesktopSolveInside = {} \n".format(str(self.geo_data.dielectrics_list)))

            # Material Assignment
            f.write("\ngeo=Geometry()\n")
            variables = [i for i in dir(self.geo_data) if ("_" not in i[0])]
            if "Data" in variables:
                variables.remove("Data")
            f.write(self._get_methods_and_vars("geo", self.geo_data, variables))

            # Mesh Assignment
            f.write("\nm=Mesh()\n")
            variables = [i for i in dir(self.mesh_data) if ("_" not in i[0])]
            if "Data" in variables:
                variables.remove("Data")
            f.write(self._get_methods_and_vars("m", self.mesh_data, variables))

            # Trace Mapping
            f.write("\ntrace = TraceMapping()\n")
            variables = [i for i in dir(self.trace_mapping_data) if ("_" not in i[0])]
            if "Data" in variables:
                variables.remove("Data")
            f.write(self._get_methods_and_vars("trace", self.trace_mapping_data, variables))

            # Setup
            f.write("\nsetup = Setup()\n")

            variables = [i for i in dir(self.setup_data) if ("_" not in i[0])]
            if "Data" in variables:
                variables.remove("Data")
            f.write(self._get_methods_and_vars("setup", self.setup_data, variables))
            return True

    def export_mechanicalreport_script_auto(self):
        """
        export_mechanicalreport_script Function write a PY function for Mechanical API.
        It start from Report.py file and integrates it with variables and lanuchers.

        - Added WBSuppressSolids option:
            1. the objects names specified in the list are suppressed in Workbench
            2. the list defaults to empty list
        """
        Filename2 = os.path.join(self.project_path, "{0}.py".format(self.name + "_Report"))
        Filename2 = Filename2.replace("\\", "/")
        current_path = os.path.dirname(os.path.realpath(__file__))
        shutil.copy2(os.path.join(current_path, "WB_MechWrapper.py"), Filename2)

        # Filename = os.path.join(self.project_path, '{0}.py'.format(self.name + "_Report"))
        # Filename = Filename.replace('\\', '/')
        with open(Filename2, "a+") as f:
            f.write('\npictures_fullpath = "%s" \n' % self.pictures_path.replace("\\\\", "////"))
            # f.write('\nname = "%s" \n' % self.name)
            f.write("\nrep=Report(pictures_fullpath)\n")
            variables = [i for i in dir(self.report_data) if ("_" not in i[0])]
            if "Data" in variables:
                variables.remove("Data")
            f.write(self._get_methods_and_vars("rep", self.report_data, variables))
            return True

    def export_reports(self, dx, id, v, mat_name, outputdx, csvFileName):
        parse_mssg = []
        client = self.client
        string = "pars=Parameters.GetAllParameters()"
        mssg = self.send_command(string, client)
        parse_mssg.append(self.parse_string(mssg))

        for el in outputdx:
            string = "for p in pars:"
            mssg = self.send_command(string, client)
            parse_mssg.append(self.parse_string(mssg))
            string = '    if "DirectOutput" in p.Usage:'
            mssg = self.send_command(string, client)
            parse_mssg.append(self.parse_string(mssg))
            string = "        chart1 = Parameters.CreateParameterVsParameterChart()"
            mssg = self.send_command(string, client)
            parse_mssg.append(self.parse_string(mssg))
            string = '        parameter1 = Parameters.GetParameter(Name="' + el + '")'
            mssg = self.send_command(string, client)
            parse_mssg.append(self.parse_string(mssg))
            string = "        chart1.XAxisBottom = parameter1"
            mssg = self.send_command(string, client)
            parse_mssg.append(self.parse_string(mssg))
            string = "        parameter2 = Parameters.GetParameter(Name=p.Name)"
            mssg = self.send_command(string, client)
            parse_mssg.append(self.parse_string(mssg))
            string = "        chart1.YAxisLeft = parameter2"
            mssg = self.send_command(string, client)
            parse_mssg.append(self.parse_string(mssg))
            string = (
                '        Graphics.PrintChart(chart1.Chart,"'
                + self.pictures_path
                + "//"
                + self.name
                + '"+p.DisplayText+".png",640,480)'
            )
            mssg = self.send_command(string, client)
            parse_mssg.append(self.parse_string(mssg))
            string = ""
            mssg = self.send_command(string, client)
            parse_mssg.append(self.parse_string(mssg))

        # write csv file containing the variation combinations
        try:
            with open(csvFileName, "w") as f:
                # writing file content
                f.writelines("ID," + ",".join(dx) + "\n")
                for i in range(1, id):
                    f.writelines(str(i) + "," + ",".join(v[i]))
                    if bool(mat_name):
                        f.writelines("{" + mat_name[i] + "}")
                    f.writelines("\n")
        except IOError as e:
            self.logger.error("export_reports: Couldn't open or write to file (%s)." % e)

        return parse_mssg.count(parse_mssg[0]) == len(parse_mssg)

    def export_sparameter_from_hfss(self, design_name, PlotName, PortNames, PortExcited, YMarkerDB=None):
        """
        Creates the S Parameter Plot reports from the HFSS module
        This function prepare the script the will be launched in HFSS from Workbench
        Arguments:

        design_name (str) = design name of the HFSS module
        PortNames (list) = list of port names
        PortExcited (str) = name of the excited port
        YMarkerDB (number, optional) = dB of the Y marker
        """

        client = self.client

        SavePath_Pictures = self.pictures_path
        SavePath_Results = self.results_path

        # set name for the python script
        ScriptFileName = self.results_path + "//" + "tmp-scriptHFSSWB.py"

        # prepare the traces
        Traces = ["dB(S(" + PortExcited + "," + p + "))" for p in PortNames]

        # HFSS SCRIPT

        # script content preparation
        scriptContent = """
oProject = oDesktop.GetActiveProject()
oDesign = oProject.GetActiveDesign()
oModule = oDesign.GetModule("ReportSetup")
oSetup = oDesign.GetModule("AnalysisSetup")

# set variables to be substituted
Traces = %s                 # ["dB(S("+PortExcited+","+p+"))" for p in PortNames]
# Traces = ["dB(S("+ PortNames[0]+","+p+"))" for p in PortNames]
YMarkerDB = %s              # -20
PlotName = "%s"
SavePath_Pictures = r"%s"            # <projectpath>/Pictures
SavePath_Results = r"%s"            # <projectpath>/Results

jpgFileName = SavePath_Pictures + "\\SParametersPlot_Multiphysics" + ".jpg"
dataFileName = SavePath_Results + "\\SParametersData_Multiphysics" + ".csv"
TouchstoneFileName = SavePath_Results + "\\SParametersData_Multiphysics" + ".s2p"

setupnames = oSetup.GetSetups()
sweepnames = oSetup.GetSweeps(setupnames[0])

# Create S parameter plot
oModule.CreateReport(PlotName, "Terminal Solution Data", "Rectangular Plot", setupnames[0] + " : " + sweepnames[0],
    [
        "Domain:="		, "Sweep"
    ],
    [
        "Freq:="		, ["All"],
    ],
    [
        "X Component:="		, "Freq",
        "Y Component:="		, Traces
    ])


# set the horizontal marker if any
if YMarkerDB:
    # Create an Y marker at YMarkerDB
    oModule.AddCartesianYMarker(PlotName, "MY1", "Y1", str(YMarkerDB), "")
    # Set the properties of Y marker
    oModule.ChangeProperty(
        [
            "NAME:AllTabs",
            [
                "NAME:Y Marker",
                [
                    "NAME:PropServers",
                    PlotName+":MY1"
                ],
                [
                    "NAME:ChangedProps",
                    [
                        "NAME:Box Background",
                        "R:="            , 166,
                        "G:="            , 226,
                        "B:="            , 255
                    ],
                    [
                        "NAME:Line Color",
                        "R:="            , 0,
                        "G:="            , 128,
                        "B:="            , 192
                    ],
                    [
                        "NAME:Line Width",
                        "Value:="        , "2"
                    ],
                    [
                        "NAME:Line Style",
                        "Value:="        , "Dash"
                    ]
                ]
            ]
        ])

oModule.ExportImageToFile(PlotName, jpgFileName, 1920, 1080)

oModule.ExportToFile(PlotName, dataFileName)

DesignVariations = ""
SolutionSelectionArray = [setupnames[0] + " : " + sweepnames[0]]   # array containing "SetupName:SolutionName" pairs
FileFormat = 3                          # 2=tab delimited spreadsheet (.tab), 3= touchstone (.sNp), 4= CitiFile (.cit),
                                        # 7=Matlab (.m), 8=Terminal Z0 spreadsheet
OutFile = TouchstoneFileName            # full path of output file
FreqsArray = ["all"]                    # array containin the frequencies to export, use ["all"] for all frequencies
DoRenorm = True                         # perform renormalization before export
RenormImped = 50                        # Real impedance value in ohm, for renormalization
DataType = "S"                          # Type: "S", "Y", or "Z" matrix to export
Pass = -1                               # The pass to export. -1 = export all passes.
ComplexFormat = 0                       # 0=Magnitude/Phase, 1=Real/Immaginary, 2=dB/Phase
DigitsPrecision = 15                    # Touchstone number of digits precision
IncludeGammaImpedance = True            # Include Gamma and Impedance in comments
NonStandardExtensions = False           # Support for non-standard Touchstone extensions
oModule = oDesign.GetModule("Solutions")
oModule.ExportNetworkData(
            DesignVariations,
            SolutionSelectionArray,
            FileFormat,
            OutFile,
            FreqsArray,
            DoRenorm,
            RenormImped,
            DataType,
            Pass,
            ComplexFormat,
            DigitsPrecision,
            False,
            IncludeGammaImpedance,
            NonStandardExtensions,
        )

"""

        # END HFSS SCRIPT
        # Modify the script for the variation
        scriptContentID = scriptContent % (
            str(Traces),
            str(YMarkerDB),
            str(PlotName),
            SavePath_Pictures,
            SavePath_Results,
        )

        # write script content to file
        try:
            with open(ScriptFileName, "w") as f:
                # writing file content
                f.write(scriptContentID)
        except IOError as e:
            self.logger.error("export_sparameter_from_hfss: Couldn't open or write to file (%s)." % e)

        # This function is pre-loaded in WB
        string = "WB.run_hfss_script(r'" + ScriptFileName + "','" + str(design_name) + "')"
        # send the string command to WB
        mssg = self.send_command(string, client)
        parse_mssg = self.parse_string(mssg)
        # deleting temp script file
        try:
            os.remove(ScriptFileName)
        except IOError as e:
            self.logger.error("export_sparameter_from_hfss: Couldn't delete file (%s)." % e)

        return parse_mssg

    def export_sparameter_from_hfss2(
        self,
        design_name,
        jpgFileName,
        PortNames,
        setupName,
        PlotName,
        PortExcited,
        YMarkerDB=None,
        DesignVariations=None,
    ):
        """
        Creates the S Parameter Plot reports from the HFSS module
        This function prepare the script will be launched in HFSS from Workbench
        Arguments:

        design_name (str) = design name of the HFSS module
        PortNames (list) = list of port names
        PortExcited (str) = name of the excited port
        YMarkerDB (number, optional) = dB of the Y marker
        """

        client = self.client

        SavePath_Pictures = jpgFileName
        SavePath_Results = self.results_path

        # set name for the python script
        ScriptFileName = self.results_path + "//" + "tmp-scriptHFSSWB.py"

        # prepare the traces
        Traces = ["dB(S(" + PortExcited + "," + p + "))" for p in PortNames]

        # HFSS SCRIPT

        # script content preparation
        scriptContent = """
oProject = oDesktop.GetActiveProject()
oDesign = oProject.GetActiveDesign()
oModule = oDesign.GetModule("ReportSetup")
oSetup = oDesign.GetModule("AnalysisSetup")

# set variables to be substituted
Traces = %s
YMarkerDB = %s            # -20
jpgFileName = r"%s"
setupName = r"%s"
VariationsValue = %s
PlotName = r"%s"
PlotNameNominal = "S Parameter Plot Nominal"

setupnames = oSetup.GetSetups()
sweepnames = oSetup.GetSweeps(setupnames[0])

# Detect if the Report exists and remove it
names = oModule.GetAllReportNames()
for name in names:
     # print(str(name))
     if str(name) == PlotName:
          oModule.DeleteReports(PlotName)

# make a copy of the nominal plot
oModule.CopyReportDefinitions([PlotNameNominal])
oModule.PasteReports()
oModule.RenameReport(PlotNameNominal+"_1", PlotName)

# add the traces for the variation
Families = ["Freq:=", ["All"]]
for s in  VariationsValue:
    Families.append(s + ":=")
    Families.append([VariationsValue[s]])

Trace = ["X Component:=", "Freq", "Y Component:=", Traces]

oModule.AddTraces(
    PlotName,
    setupName,
    { "Domain": "Sweep" },
    Families,
    Trace,
    [])

# set the horizontal marker if any
if YMarkerDB:
    # Create an Y marker at YMarkerDB
    oModule.AddCartesianYMarker(PlotName, "MY1", "Y1", str(YMarkerDB), "")
    # Set the properties of Y marker
    oModule.ChangeProperty(
        [
            "NAME:AllTabs",
            [
                "NAME:Y Marker",
                [
                    "NAME:PropServers",
                    PlotName+":MY1"
                ],
                [
                    "NAME:ChangedProps",
                    [
                        "NAME:Box Background",
                        "R:="            , 166,
                        "G:="            , 226,
                        "B:="            , 255
                    ],
                    [
                        "NAME:Line Color",
                        "R:="            , 0,
                        "G:="            , 128,
                        "B:="            , 192
                    ],
                    [
                        "NAME:Line Width",
                        "Value:="        , "2"
                    ],
                    [
                        "NAME:Line Style",
                        "Value:="        , "Dash"
                    ]
                ]
            ]
        ])

oModule.ExportImageToFile(PlotName, jpgFileName, 0, 0)
"""

        # END HFSS SCRIPT
        if not DesignVariations:
            DesignVariations = ""
        # Modify the script for the variation
        scriptContentID = scriptContent % (
            str(Traces),
            str(YMarkerDB),
            SavePath_Pictures,
            setupName,
            DesignVariations,
            PlotName,
        )

        # write script content to file
        try:
            with open(ScriptFileName, "w") as f:
                # writing file content
                f.write(scriptContentID)
        except IOError as e:
            self.logger.error("export_sparameter_from_hfss: Couldn't open or write to file (%s)." % e)

        # This function is pre-loaded in WB
        string = "WB.run_hfss_script(r'" + ScriptFileName + "','" + str(design_name) + "')"
        # send the string command to WB
        mssg = self.send_command(string, client)
        parse_mssg = self.parse_string(mssg)
        # deleting temp script file
        try:
            os.remove(ScriptFileName)
        except IOError as e:
            self.logger.error("export_sparameter_from_hfss: Couldn't delete file (%s)." % e)

        return parse_mssg

    def export_touchstone_from_hfss(self, design_name, s2pFileName, setupName, DesignVariations=None):
        """
        Creates the S Parameter Touchstone file from the HFSS module
        This function prepare the script the will be launched in HFSS from Workbench
        Arguments:

        design_name (str) = design name of the HFSS module
        s2pFileName (str) = Full path with .sxp extension
        setupName (str) = HFSS Setup name
        DesignVariations (str) = "ambient_temp=\'22cel\' powerin=\'100\'"
        """

        client = self.client

        # set name for the python script
        ScriptFileName = self.results_path + "//" + "tmp-scriptHFSSWB.py"

        # HFSS SCRIPT
        # script content preparation
        scriptContent = """
oProject = oDesktop.GetActiveProject()
oDesign = oProject.GetActiveDesign()
oModule = oDesign.GetModule("Solutions")

FileName = r"%s"
DesignVariations = r"%s"

SolutionSelectionArray = [r"%s"]        # array containing "SetupName:SolutionName" pairs
FileFormat = 3                          # 2=tab delimited spreadsheet (.tab), 3= touchstone (.sNp), 4= CitiFile (.cit),
                                        # 7=Matlab (.m), 8=Terminal Z0 spreadsheet
OutFile = FileName                      # full path of output file
FreqsArray = ["all"]                    # array containin the frequencies to export, use ["all"] for all frequencies
DoRenorm = True                         # perform renormalization before export
RenormImped = 50                        # Real impedance value in ohm, for renormalization
DataType = "S"                          # Type: "S", "Y", or "Z" matrix to export
Pass = -1                               # The pass to export. -1 = export all passes.
ComplexFormat = 0                       # 0=Magnitude/Phase, 1=Real/Immaginary, 2=dB/Phase
DigitsPrecision = 15                    # Touchstone number of digits precision
IncludeGammaImpedance = True            # Include Gamma and Impedance in comments
NonStandardExtensions = False           # Support for non-standard Touchstone extensions

oModule.ExportNetworkData(DesignVariations,
                            SolutionSelectionArray,
                            FileFormat,
                            OutFile,
                            FreqsArray,
                            DoRenorm,
                            RenormImped,
                            DataType,
                            Pass,
                            ComplexFormat,
                            DigitsPrecision,
                            False,
                            IncludeGammaImpedance,
                            NonStandardExtensions)
"""
        # END HFSS SCRIPT
        if not DesignVariations:
            DesignVariations = ""

        scriptContentID = scriptContent % (s2pFileName, DesignVariations, setupName)

        # write script content to file
        try:
            with open(ScriptFileName, "w") as f:
                # writing file content
                f.write(scriptContentID)
        except IOError as e:
            self.logger.error("export_touchstone_from_hfss: Couldn't open or write to file (%s)." % e)

        # This function is pre-loaded in WB
        string = "WB.run_hfss_script(r'" + ScriptFileName + "','" + str(design_name) + "')"
        # send the string command to WB
        mssg = self.send_command(string, client)
        parse_mssg = self.parse_string(mssg)
        # deleting temp script file
        try:
            os.remove(ScriptFileName)
        except IOError as e:
            self.logger.error("export_touchstone_from_hfss: Couldn't delete file (%s)." % e)

        return parse_mssg

    def import_dm(self):
        """
        Import an Step Project into Workbench without SCDM, using Design Modeler.
        Project name is predefined into the __init__
        """
        client = self.client
        self.logger.info("Importing Step Project")
        string = "WB.import_dm()"
        mssg = self.send_command(string, client)
        parse_mssg = self.parse_string(mssg)
        return parse_mssg

    def import_externaldata_fld(self):
        """
        Import External Data into Workbench. Project name is predefined into the __init__
        """
        client = self.client
        self.logger.info("Importing External Data .fld")
        string = "WB.import_externaldata_fld()"
        mssg = self.send_command(string, client)
        parse_mssg = self.parse_string(mssg)
        return parse_mssg

    def import_externaldata_pcb(self):
        """
        Import External Data into Workbench. Project name is predefined into the __init__
        """
        client = self.client
        self.logger.info("Importing External Data PCB")
        string = "WB.import_externaldata_pcb()"
        mssg = self.send_command(string, client)
        parse_mssg = self.parse_string(mssg)
        return parse_mssg

    def import_hfss(self, design_name):
        """
        Import an HFSS (.aedt) Project into Workbench. Project name is predefined into the __init__
        """
        client = self.client
        self.logger.info("Importing HFSS Project")
        string = "WB.import_hfss('" + str(design_name) + "')"
        mssg = self.send_command(string, client)
        parse_mssg = self.parse_string(mssg)
        return parse_mssg

    def import_material_hfss(self, design_name):
        """
        Import an second HFSS Project into Workbench to Update Engineering Data.
        Project name is predefined into the __init__, name of the project must be 'Material_*'
        """
        client = self.client
        self.logger.info("Importing HFSS Project")
        string = "WB.import_material_hfss('" + str(design_name) + "')"
        mssg = self.send_command(string, client)
        parse_mssg = self.parse_string(mssg)
        return parse_mssg

    def import_scdm(self):
        """
        Import an SCDM Project into Workbench. Project name is predefined into the __init__
        """
        client = self.client
        self.logger.info("Importing SCDM Project")
        string = "WB.import_scdm()"
        mssg = self.send_command(string, client)
        parse_mssg = self.parse_string(mssg)
        return parse_mssg

    def load_wbcode(self):
        """
        Most important function. It will load WBMultiphysics.py in WB, to use all its functions
        If Mechanical will be used, it has to be called after the creation of the Mechanical script
        """
        self.logger.info("Loading WB Code")
        client = self.client
        mypath = os.path.join(os.path.dirname(os.path.realpath(__file__)), "WBMultiphysics.py")
        try:
            client.SendScriptFile(mypath)
        except Exception as e:
            print(str(e))
        string = (
            'WB=WBMultiphysics("'
            + self.project_path
            + '","'
            + self.name
            + '","'
            + pyaedt_dir()
            + '","'
            + str(self.AEDTproject_name)
            + '","'
            + str(self.AEDTMatproject_name)
            + '","'
            + str(self.GEOMproject_name)
            + '","'
            + str(self.TempMap_name)
            + '","'
            + str(self.PCB_name)
            + '") '
        )
        mssg = self.send_command(string, client)
        parse_mssg = self.parse_string(mssg)
        return parse_mssg

    def launch_workbench(self):
        self.logger.info("Launching Workbench. This may take few minutes.")
        client = self.client
        pid = client.LaunchWorkbenchInServerMode()
        self.load_wbcode()
        return isinstance(pid, int)

    def open_project(self, filename):
        """
        Open an existing wbpj project
        """
        client = self.client

        string = 'Open(FilePath="' + filename.replace("\\", "/") + '")'
        mssg1 = self.send_command(string, client)
        parse_mssg1 = self.parse_string(mssg1)
        if not parse_mssg1:
            string = "Open(FilePath='" + filename.replace("\\", "\\\\") + "')"
            mssg1 = self.send_command(string, client)
            parse_mssg1 = self.parse_string(mssg1)

        self._project_fullname = filename

        string = "import os"
        mssg2 = self.send_command(string, client)
        parse_mssg2 = self.parse_string(mssg2)
        string = "pid=os.getpid()"
        mssg3 = self.send_command(string, client)
        parse_mssg3 = self.parse_string(mssg3)
        # self.pid = client.GetVariableValue("pid")
        if parse_mssg1 and parse_mssg2 and parse_mssg3:
            parse_mssg = True
        else:
            parse_mssg = False

        return parse_mssg

    def send_command(self, str, client):
        """
        Parse a Workbench Command. Updates the interface LOG UI
        """
        mssg = client.SendScriptStatement(str)
        return mssg

    def parse_string(self, mssg):
        """
        Assert Workbench Command
        """

        if mssg == "<OK>":
            return True
        else:
            return False

    def remove_feedback_iterator(self):
        """
        Create Feedback iterator block and setup numIterations
        numIterations: integer with number of iterations
        design_name: HFSS Design name
        """
        client = self.client
        self.logger.info("Remove Feedback Iterator")
        string = "WB.remove_iterations()"
        mssg = self.send_command(string, client)
        parse_mssg = self.parse_string(mssg)
        return parse_mssg

    def run_report_script(self):
        """
        Open Thermal Mechanical and execute 1 Script file
        filename.py: is a python script with all python commands for setting up materials, mesh, named selection,
                        solution
        filenanme.js: is a javascript which setup the external load transfer from HFSS
        """
        client = self.client
        string = "WB.run_report_script(" + str(True) + ")"
        mssg = self.send_command(string, client)
        parse_mssg = self.parse_string(mssg)
        return parse_mssg

    def run_setup_script(self):
        """
        Open Thermal Mechanical and execute 1 Script file
        filename.py: is a python script with all python commands for setting up materials, mesh, named selection,
                        solution
        filenanme.js: is a javascript which setup the external load transfer from HFSS
        """
        client = self.client
        string = "WB.run_setup_script(" + str(self.MechGui) + ")"
        mssg = self.send_command(string, client)
        parse_mssg = self.parse_string(mssg)
        return parse_mssg

    def save(self):
        """
        Save workbench project to filename
        """
        client = self.client
        string = "Refresh()"
        mssg1 = self.send_command(string, client)
        parse_mssg1 = self.parse_string(mssg1)
        string = 'Save(FilePath="' + self.project_fullname + '", Overwrite=True)'
        mssg2 = self.send_command(string, client)
        parse_mssg2 = self.parse_string(mssg2)
        if not parse_mssg2:
            string = "Save(FilePath='" + self.project_fullname.replace("\\", "\\\\") + "', Overwrite=True)"
            mssg2 = self.send_command(string, client)
            parse_mssg2 = self.parse_string(mssg2)

        if parse_mssg1 and parse_mssg2:
            parse_mssg = True
        else:
            parse_mssg = False

        return parse_mssg

    def saveandclose(self):
        """
        Save workbench project to filename and close Workbench
        """
        self.logger.info("Closing Workbench")

        # Save
        client = self.client
        string = "Save(Overwrite=True)"
        mssg = self.send_command(string, client)
        parse_mssg = self.parse_string(mssg)

        client.CloseWorkbench()
        time.sleep(5)
        return parse_mssg

    def save_as(self, filename):
        """
        save the project with the specific input name
        name: string
        """
        client = self.client
        string = 'Save(FilePath="' + filename.replace("\\", "/") + '", Overwrite=True)'
        mssg = self.send_command(string, client)
        parse_mssg = self.parse_string(mssg)
        if not parse_mssg:
            string = "Save(FilePath='" + filename.replace("\\", "\\\\") + "', Overwrite=True)"
            mssg = self.send_command(string, client)
            parse_mssg = self.parse_string(mssg)
        self._project_fullname = filename
        return parse_mssg

    def save_data(self, csv_fullname=None):
        """
        Save workbench project to filename
        """

        client = self.client
        if not csv_fullname:
            Filename = os.path.join(self.results_path, "{0}.csv".format(self.name + "_out"))
        elif os.path.splitext(csv_fullname)[1] != ".csv":
            Filename = csv_fullname + ".csv"
        else:
            Filename = csv_fullname

        #     Filename = os.path.join(self.path, '{0}.csv'.format(name + "//Results//" + name + "_out"))

        self.logger.info("Saving Simulated Data Points")

        string = 'Parameters.ExportAllDesignPointsData(FilePath="' + Filename.replace("\\", "//") + '")'
        mssg = self.send_command(string, client)
        parse_mssg = self.parse_string(mssg)
        return parse_mssg

    def structural_update_ed(self):
        """
        Update Engineering Data. To be refactored
        """
        self.logger.info("Creating the Final Engineering Data")

        client = self.client
        string = "WB.modify_structural_ed()"
        mssg = self.send_command(string, client)
        parse_mssg = self.parse_string(mssg)
        return parse_mssg

    def structural_update_mesh(self):
        """
        Update Mesh
        """
        self.logger.info("Updating the Mesh after Structural Setup")

        client = self.client
        string = "WB.modify_structural_mesh()"
        mssg = self.send_command(string, client)
        parse_mssg = self.parse_string(mssg)
        return parse_mssg

    def structural_update_setup(self):
        """
        Update Mesh
        """
        self.logger.info("Updating the Mesh after Structural Setup")

        client = self.client
        string = "WB.modify_structural_setup()"
        mssg = self.send_command(string, client)
        parse_mssg = self.parse_string(mssg)
        return parse_mssg

    def thermal_update_setup(self):
        """
        Update Thermal Setup
        """
        self.logger.info("Updating the Setup")

        client = self.client
        string = "WB.modify_thermal_setup()"
        mssg = self.send_command(string, client)
        parse_mssg = self.parse_string(mssg)
        return parse_mssg

    def thermal_update_solution(self):
        """
        Update Thermal Solution
        """
        self.logger.info("Updating the Setup")

        client = self.client
        string = "WB.modify_thermal_solution()"
        mssg = self.send_command(string, client)
        parse_mssg = self.parse_string(mssg)
        return parse_mssg

    def thermal_update_ed(self):
        """
        Update Engineering Data. To be refactored
        """
        self.logger.info("Creating the Final Engineering Data")

        client = self.client
        string = "WB.modify_thermal_ed()"
        mssg = self.send_command(string, client)
        parse_mssg = self.parse_string(mssg)
        return parse_mssg

    def structural_thermal_update_setup(self):
        """
        Update Structural with Thermal Setup
        """
        self.logger.info("Updating the Setup")

        client = self.client
        string = "WB.modify_structuralthermal_setup()"
        mssg = self.send_command(string, client)
        parse_mssg = self.parse_string(mssg)
        return parse_mssg

    def structural_thermal_update_solution(self):
        """
        Update Structural with Thermal Setup
        """
        self.logger.info("Updating the Setup")

        client = self.client
        string = "WB.modify_structuralthermal_solution()"
        mssg = self.send_command(string, client)
        parse_mssg = self.parse_string(mssg)
        return parse_mssg

    def unarchive_project(self, path):
        """
        Unarchive a project and Save as with wbpj extension
        """
        client = self.client
        unzipped_name = os.path.splitext(path)[0] + ".wbpj"
        string = 'Unarchive(ArchivePath="' + path + '",' + 'ProjectPath="' + unzipped_name + '",' + "Overwrite=True)"
        mssg = self.send_command(string, client)
        parse_mssg = self.parse_string(mssg)
        return parse_mssg

    def update(self):
        """
        Update WB project
        """
        client = self.client
        self.logger.info("Launching Simulation...")

        string = "Refresh()"
        mssg1 = self.send_command(string, client)
        parse_mssg1 = self.parse_string(mssg1)
        string = "Update()"
        mssg2 = self.send_command(string, client)
        parse_mssg2 = self.parse_string(mssg2)

        if parse_mssg1 and parse_mssg2:
            parse_mssg = True
        else:
            parse_mssg = False

        return parse_mssg

    def update_all(self):
        """
        Update all design points in WB project
        """
        client = self.client
        self.logger.info("Updating All Design Points")
        string = "backgroundSession1 = UpdateAllDesignPoints()"
        mssg = self.send_command(string, client)
        parse_mssg = self.parse_string(mssg)
        return parse_mssg

    def update_hfss(self):
        """
        Update an HFSS Project into Workbench. Project name is predefined into the __init__
        """
        client = self.client
        self.logger.info("Importing HFSS Project")
        string = "WB.update_hfss()"
        mssg = self.send_command(string, client)
        parse_mssg = self.parse_string(mssg)
        return parse_mssg

    def update_iterations(self, numIterations, deltaT, deltaD):
        """
        Update Feedback iterator block and setup new numIterations
        numIterations: integer with number of iterations
        """
        client = self.client
        self.logger.info("Updating Feedback Iterator")
        string = "WB.update_iterations(" + str(numIterations) + "," + str(deltaT) + "," + str(deltaD) + ")"
        mssg = self.send_command(string, client)
        parse_mssg = self.parse_string(mssg)
        return parse_mssg

    def load_csv(self, csvname):
        """
        Print to logger the design points info
        """
        try:
            with open(csvname, "r") as csvfile:
                reader = csv.reader(csvfile, delimiter=",", quotechar="|")
                # count = 0
                table = []
                for row in reader:
                    r = []
                    for el in row:
                        r.append(el)
                    table.append(r)
                i = 7
                header = 3
                while i < len(table):
                    k = 0
                    self.logger.info("Updated Table")
                    while k < len(table[i]):
                        try:
                            self.logger.info(table[header][k] + "=" + str(format(float(table[i][k]), ".2e")))
                        except Exception as e:
                            # print(str(e))
                            self.logger.info(table[header][k] + "=" + str(table[i][k]))
                        k = k + 1
                    i = i + 1

        except Exception as e:
            self.logger.error(str(e))
            self.logger.error("Error in opening csv")
        pass

    # OLD NOT MAINTAINED

    def createVariableinDX(self, variable):
        """
        Create Design Points In DesignXplorer based on a seto of variables and a list of values
        variables: list of variable names
        values: list of arrays of values
        """
        client = self.client
        string = 'par = Parameters.CreateParameter(IsOutput=False,DisplayText="' + variable + '")'
        self.parse_string(string, client)

    def ExportSParameterReportfromHFSS_OLD(self, PortsList, PortExct, VariationsArray, YMarkerDB):
        """
        Create the S Parameter report after the Design Exploration loops
        Arguments:
        PortsList (list) = list of port names
        PortExct (str) = name of the excited port
        VariationsArray (list) = list of Parameter Variables defined in designXplorerInput
        YMarkerDB (number, optional) = dB of the Y marker
        """
        client = self.client

        ProjectPath = self.project_path.replace("//", "/")
        psplit = ProjectPath.strip("/").split("/")
        folder = psplit[len(psplit) - 1]
        FileName = '"' + ProjectPath + "/" + folder + "/Pictures/" + self.name + '_Sparam_DesignSweep.jpg"'

        # The function ExportSParameterReportfromHFSS is in WBMultiphysics.py
        # This function is pre-loaded in WB
        string = (
            "WB.ExportSParameterReportfromHFSS_WB("
            + FileName
            + ","
            + str(PortsList)
            + ',"'
            + str(PortExct)
            + '",'
            + str(VariationsArray)
            + ',"'
            + str(YMarkerDB)
            + '")'
        )
        # send the string command to WB
        self.parse_string(string, client)

    ####################################################

    ####################################################
    def WBCreateStructuralLinkNew(self):
        """
        Create a Link to Structural Mechanical from Thermal Mechanical
        It also creates the link between HFSS and Mechanical in Workbench
        """
        self.logger.info("Creating Thermal and Structural Mechanical Design")

        client = self.client
        string = "WB.createStruct()"
        self.parse_string(string, client)
        pass

    def WBCleanIntersectionsinSpaceClaim(self):
        """
        Clean all intersections between objects in SpaceClaim
        """
        self.logger.info("Cleaning intersections in SpaceClaim")

        client = self.client
        string = "WB.cleanintersectionsinSpaceClaim()"
        self.parse_string(string, client)
        pass

    def ExportTouchstonefromHFSS(self, dx, sweeps, nports):
        """
        This function prepare the script the will be launched in HFSS from Workbench
        It uses dx and sweeps to evaluate all Design variation combinations

        Example:
            dx = ["$AmbientTemp", "$PowerIn"]
            sweeps = [["22","50","80"],["1","100","2000"],["0"],["0"]]
            It export a touchstone file for each combination
            It prepare a csv file as index file for the exports

        :param dx:
        :param sweeps:
        :param nports:
        :return:
        """

        # from WB2Client import *
        client = self.client

        # set name for the python script
        ScriptFileName = os.path.join(self.results_path, "tmp-scriptHFSSWB.py")
        # set name for the csv file containing the design variation combinations
        csvFileName = os.path.join(self.results_path, "IndexVariations.csv")

        # prepare the dictionary with all design variation combinations
        v = {}
        id = 1
        for a in sweeps[0]:
            for p in sweeps[1]:
                v[id] = [a + "cel", p]
                id += 1

        # write csv file containing the variation combinations
        try:
            with open(csvFileName, "w") as f:
                # writing file content
                f.writelines("ID," + ",".join(dx) + "\n")
                for i in range(1, id):
                    f.writelines(str(i) + "," + ",".join(v[i]) + "\n")
        except IOError as e:
            self.logger.error("ExportTouchstonefromHFSS: Couldn't open or write to file (%s)." % e)

        # script content preparation
        scriptContent = """
oProject = oDesktop.GetActiveProject()
oDesign = oProject.GetActiveDesign()
oModule = oDesign.GetModule("Solutions")

FileName = r"%s"
DesignVariations = r"%s"

SolutionSelectionArray = ["AFS:Sweep"]  # array containing "SetupName:SolutionName" pairs
FileFormat = 3                          # 2=tab delimited spreadsheet (.tab), 3= touchstone (.sNp), 4= CitiFile (.cit),
                                        # 7=Matlab (.m), 8=Terminal Z0 spreadsheet
OutFile = FileName                      # full path of output file
FreqsArray = ["all"]                    # array containin the frequencies to export, use ["all"] for all frequencies
DoRenorm = True                         # perform renormalization before export
RenormImped = 50                        # Real impedance value in ohm, for renormalization
DataType = "S"                          # Type: "S", "Y", or "Z" matrix to export
Pass = -1                               # The pass to export. -1 = export all passes.
ComplexFormat = 0                       # 0=Magnitude/Phase, 1=Real/Immaginary, 2=dB/Phase
DigitsPrecision = 15                    # Touchstone number of digits precision
IncludeGammaImpedance = True            # Include Gamma and Impedance in comments
NonStandardExtensions = False           # Support for non-standard Touchstone extensions

oModule.ExportNetworkData(DesignVariations,
                            SolutionSelectionArray,
                            FileFormat,
                            OutFile,
                            FreqsArray,
                            DoRenorm,
                            RenormImped,
                            DataType,
                            Pass,
                            ComplexFormat,
                            DigitsPrecision,
                            False,
                            IncludeGammaImpedance,
                            NonStandardExtensions)
"""

        # cycle over the variation combinations
        for ID in v:
            # Touchstone file name
            s2pFileName = os.path.join(self.results_path, "Touchstone-IDVar" + str(ID) + ".s" + str(nports) + "p")
            DesignVariations = (
                str(dx[0]) + "='" + str(v[ID][0]) + "' " + str(dx[1]) + "='" + str(v[ID][1]) + "'"
            )  # e.g. DesignVariations = "$AmbientTemp=\'22cel\' $PowerIn=\'100\'"
            scriptContentID = scriptContent % (s2pFileName, DesignVariations)

            # write script content to file
            try:
                with open(ScriptFileName, "w") as f:
                    # writing file content
                    f.write(scriptContentID)
            except IOError as e:
                self.logger.error("ExportTouchstonefromHFSS: Couldn't open or write to file (%s)." % e)

            # This function is pre-loaded in WB
            string = "WB.RunScriptInHFSS(r'" + ScriptFileName + "')"
            # send the string command to WB
            self.parse_string(string, client)

            # deleting temp script file
            try:
                os.remove(ScriptFileName)
            except IOError as e:
                self.logger.error("ExportTouchstonefromHFSS: Couldn't delete file (%s)." % e)

    def WBParametricAnalysis(self, name, list):
        """
        Create Feedback iterator block and setup numIterations
        numIterations: integer with number of iterations
        """
        client = self.client
        string = "inppars=Parameters.GetAllConstantInputParameters()"
        self.parse_string(string, client)
        string = 'parameter1=""'
        self.parse_string(string, client)
        string = 'name="' + name + '"'
        self.parse_string(string, client)
        string = "for inppar in inppars:"
        self.parse_string(string, client)
        string = "   if name==inppar.DisplayText:"
        self.parse_string(string, client)
        string = "      parameter1 = Parameters.GetParameter(Name=inppar.Name)"
        self.parse_string(string, client)
        string = ""
        self.parse_string(string, client)
        """
        Check if the input list is made of integer. If not it will create an index from 0 to len of list of designpoints
        """
        if type(list[0]) is str:
            string = 'parameter2 = Parameters.CreateParameter(IsOutput=False,DisplayText="VarLabel")'
            self.parse_string(string, client)
            first = True
            index = 0
            for id in list:
                if not first:
                    string = "designPoint1 = Parameters.CreateDesignPoint()"
                    self.parse_string(string, client)
                else:
                    string = "designPoint1 = Parameters.GetDesignPoint(Name=" + chr(34) + str(index) + chr(34) + ")"
                    self.parse_string(string, client)
                    first = False

                string = (
                    "designPoint1.SetParameterExpression(Parameter=parameter1, Expression="
                    + chr(34)
                    + str(index)
                    + chr(34)
                    + ")"
                )
                self.parse_string(string, client)
                string = (
                    "designPoint1.SetParameterExpression(Parameter=parameter2,Expression="
                    + chr(39)
                    + chr(34)
                    + id
                    + chr(34)
                    + chr(39)
                    + ")"
                )
                self.parse_string(string, client)
                index = index + 1
        else:
            first = True
            for id in list:
                if first:
                    first = False
                else:
                    string = "designPoint1 = Parameters.CreateDesignPoint()"
                    self.parse_string(string, client)
                    string = 'designPoint1.SetParameterExpression(Parameter=parameter1, Expression="' + str(id) + '")'
                    self.parse_string(string, client)

        pass
