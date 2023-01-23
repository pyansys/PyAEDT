# -*- coding: utf-8 -*-
"""This module contains the ``Circuit`` class."""

from __future__ import absolute_import  # noreorder

import glob
import io
import math
import os
import re
import shutil

from pyaedt.application.AnalysisNexxim import FieldAnalysisCircuit
from pyaedt.generic import ibis_reader
from pyaedt.generic.DataHandlers import from_rkm_to_aedt
from pyaedt.generic.general_methods import generate_unique_name
from pyaedt.generic.general_methods import open_file
from pyaedt.generic.general_methods import pyaedt_function_handler
from pyaedt.modules.Boundary import CurrentSinSource
from pyaedt.modules.Boundary import PowerIQSource
from pyaedt.modules.Boundary import PowerSinSource
from pyaedt.modules.Boundary import Sources
from pyaedt.modules.Boundary import VoltageDCSource
from pyaedt.modules.Boundary import VoltageFrequencyDependentSource
from pyaedt.modules.Boundary import VoltageSinSource
from pyaedt.modules.CircuitTemplates import SourceKeys


class Circuit(FieldAnalysisCircuit, object):
    """Provides the Circuit application interface.

    Parameters
    ----------
    projectname : str, optional
        Name of the project to select or the full path to the project
        or AEDTZ archive to open.  The default is ``None``, in which
        case an attempt is made to get an active project. If no
        projects are present, an empty project is created.
    designname : str, optional
        Name of the design to select. The default is ``None``, in
        which case an attempt is made to get an active design. If no
        designs are present, an empty design is created.
    solution_type : str, optional
        Solution type to apply to the design. The default is
        ``None``, in which case the default type is applied.
    setup_name : str, optional
        Name of the setup to use as the nominal. The default is
        ``None``, in which case the active setup is used or
        nothing is used.
    specified_version : str, optional
        Version of AEDT to use. The default is ``None``, in which case
        the active version or latest installed version is  used.
        This parameter is ignored when Script is launched within AEDT.
    non_graphical : bool, optional
        Whether to run AEDT in non-graphical mode. The default
        is ``False``, in which case AEDT is launched in graphical mode.
        This parameter is ignored when a script is launched within AEDT.
    new_desktop_session : bool, optional
        Whether to launch an instance of AEDT in a new thread, even if
        another instance of the ``specified_version`` is active on the
        machine.  The default is ``True``. This parameter is ignored when
        a script is launched within AEDT.
    close_on_exit : bool, optional
        Whether to release AEDT on exit. The default is ``False``.
    student_version : bool, optional
        Whether to open the AEDT student version. The default is ``False``.
        This parameter is ignored when Script is launched within AEDT.
    machine : str, optional
        Machine name to which connect the oDesktop Session. Works only in 2022 R2
        or later. The remote server must be up and running with the command
        `"ansysedt.exe -grpcsrv portnum"`. If a machine is `"localhost"`, the
        server also starts if not present.
    port : int, optional
        Port number on which to start the oDesktop communication on an already existing server.
        This parameter is ignored when creating a new server. It works only in 2022 R2 or
        later. The remote server must be up and running with the command
        `"ansysedt.exe -grpcsrv portnum"`.
    aedt_process_id : int, optional
        Process ID for the instance of AEDT to point PyAEDT at. The default is
        ``None``. This parameter is only used when ``new_desktop_session = False``.

    Examples
    --------
    Create an instance of Circuit and connect to an existing HFSS
    design or create a new HFSS design if one does not exist.

    >>> from pyaedt import Circuit
    >>> aedtapp = Circuit()

    Create an instance of Circuit and link to a project named
    ``"projectname"``. If this project does not exist, create one with
    this name.

    >>> aedtapp = Circuit(projectname)

    Create an instance of Circuit and link to a design named
    ``"designname"`` in a project named ``"projectname"``.

    >>> aedtapp = Circuit(projectname,designame)

    Create an instance of Circuit and open the specified project,
    which is ``"myfie.aedt"``.

    >>> aedtapp = Circuit("myfile.aedt")

    Create an instance of Circuit using the 2021 R1 version and
    open the specified project, which is ``"myfile.aedt"``.

    >>> aedtapp = Circuit(specified_version="2021.2", projectname="myfile.aedt")

    Create an instance of Circuit using the 2021 R2 student version and open
    the specified project, which is named ``"myfile.aedt"``.

    >>> hfss = Circuit(specified_version="2021.2", projectname="myfile.aedt", student_version=True)

    """

    def __init__(
        self,
        projectname=None,
        designname=None,
        solution_type=None,
        setup_name=None,
        specified_version=None,
        non_graphical=False,
        new_desktop_session=False,
        close_on_exit=False,
        student_version=False,
        machine="",
        port=0,
        aedt_process_id=None,
    ):
        FieldAnalysisCircuit.__init__(
            self,
            "Circuit Design",
            projectname,
            designname,
            solution_type,
            setup_name,
            specified_version,
            non_graphical,
            new_desktop_session,
            close_on_exit,
            student_version,
            machine,
            port,
            aedt_process_id,
        )

        self.onetwork_data_explorer = self._desktop.GetTool("NdExplorer")

    def __enter__(self):
        return self

    def _get_number_from_string(self, stringval):
        value = stringval[stringval.find("=") + 1 :].strip().replace("{", "").replace("}", "").replace(",", ".")
        try:
            float(value)
            return value
        except:
            return from_rkm_to_aedt(value)

    @pyaedt_function_handler()
    def create_schematic_from_netlist(self, file_to_import):
        """Create a circuit schematic from an HSpice netlist.

        Supported currently are:

        * R
        * L
        * C
        * Diodes
        * Bjts
        * Discrete components with syntax ``Uxxx net1 net2 ... netn modname``

        Parameters
        ----------
        file_to_import : str
            Full path to the HSpice file to import.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        xpos = 0
        ypos = 0
        delta = 0.0508
        use_instance = True
        model = []
        self._desktop.CloseAllWindows()
        autosave = False
        if self._desktop.GetAutoSaveEnabled() == 1:
            self._desktop.EnableAutoSave(False)
            autosave = True
        with open_file(file_to_import, "rb") as f:
            for line in f:
                line = line.decode("utf-8")
                if ".param" in line[:7].lower():
                    try:
                        ppar = line[7:].split("=")[0]
                        pval = line[7:].split("=")[1]
                        self[ppar] = pval
                        xpos = 0.0254
                    except:
                        pass
                elif ".model" in line[:7].lower() or ".lib" in line[:4].lower():
                    model.append(line)
        if model:
            self.modeler.schematic.create_symbol("Models_Netlist", [])
            self.modeler.schematic.create_new_component_from_symbol("Models_Netlist", [], "")
            self.modeler.schematic.create_component(
                None,
                component_library=None,
                component_name="Models_Netlist",
                location=[xpos, 0],
                global_netlist_list=model,
            )
            self.modeler.schematic.disable_data_netlist(component_name="Models_Netlist")
            xpos += 0.0254
        counter = 0
        with open_file(file_to_import, "rb") as f:
            for line in f:
                line = line.decode("utf-8")
                mycomp = None
                fields = line.split(" ")
                name = fields[0].replace(".", "")

                if fields[0][0] == "R":
                    if "{" in fields[3][0]:
                        value = fields[3].strip()[1:-1]
                    elif (
                        "/" in fields[3]
                        and '"' not in fields[3][0]
                        and "'" not in fields[3][0]
                        and "{" not in fields[3][0]
                    ):
                        value = self._get_number_from_string(fields[3].split("/")[0])
                    else:
                        value = self._get_number_from_string(fields[3])
                    mycomp = self.modeler.schematic.create_resistor(
                        name, value, [xpos, ypos], use_instance_id_netlist=use_instance
                    )
                elif fields[0][0] == "L":
                    if len(fields) > 4 and "=" not in fields[4]:
                        try:
                            float(fields[4])
                        except:
                            self.logger.warning(
                                "Component {} was not imported. Check it and manually import".format(name)
                            )
                            continue
                    if "{" in fields[3][0]:
                        value = fields[3].strip()[1:-1]
                    elif "/" in fields[3] and '"' not in fields[3][0] and "'" not in fields[3][0]:
                        value = self._get_number_from_string(fields[3].split("/")[0])
                    else:
                        value = self._get_number_from_string(fields[3])
                    mycomp = self.modeler.schematic.create_inductor(
                        name, value, [xpos, ypos], use_instance_id_netlist=use_instance
                    )
                elif fields[0][0] == "C":
                    if "{" in fields[3][0]:
                        value = fields[3].strip()[1:-1]
                    elif "/" in fields[3] and '"' not in fields[3][0] and "'" not in fields[3][0]:
                        value = self._get_number_from_string(fields[3].split("/")[0])
                    else:
                        value = self._get_number_from_string(fields[3])
                    mycomp = self.modeler.schematic.create_capacitor(
                        name, value, [xpos, ypos], use_instance_id_netlist=use_instance
                    )
                elif fields[0][0] == "Q" or fields[0][0] == "U":
                    if len(fields) == 4 and fields[0][0] == "Q":
                        value = fields[3].strip()
                        mycomp = self.modeler.schematic.create_npn(
                            fields[0], value, [xpos, ypos], use_instance_id_netlist=use_instance
                        )
                    else:
                        numpins = len(fields) - 2
                        i = 1
                        pins = []
                        while i <= numpins:
                            pins.append("Pin" + str(i))
                            i += 1
                        parameter = fields[len(fields) - 1][:-1].strip()
                        if "=" in parameter:
                            parameter_list = [parameter[: parameter.find("=") - 1]]
                            parameter_value = [parameter[parameter.find("=") + 1 :]]
                        else:
                            parameter_list = ["MOD"]
                            parameter_value = [parameter]
                        self.modeler.schematic.create_symbol(parameter, pins)
                        already_exist = False
                        for el in self.modeler.schematic.components:
                            if self.modeler.schematic.components[el].name == parameter:
                                already_exist = True
                        if not already_exist:
                            self.modeler.schematic.create_new_component_from_symbol(
                                parameter,
                                pins,
                                refbase=fields[0][0],
                                parameter_list=parameter_list,
                                parameter_value=parameter_value,
                            )
                        mycomp = self.modeler.schematic.create_component(
                            fields[0],
                            component_library=None,
                            component_name=parameter,
                            location=[xpos, ypos],
                            use_instance_id_netlist=use_instance,
                        )
                        value = None
                elif fields[0][0] == "J":
                    numpins = len(fields) - 1
                    i = 1
                    pins = []
                    while i <= numpins:
                        pins.append("Pin" + str(i))
                        i += 1
                    parameter = fields[len(fields) - 1][:-1].strip()
                    if "=" in parameter:
                        parameter_list = [parameter[: parameter.find("=") - 1]]
                        parameter_value = [parameter[parameter.find("=") + 1 :]]
                    else:
                        parameter_list = ["MOD"]
                        parameter_value = [parameter]
                    self.modeler.schematic.create_symbol(parameter, pins)
                    already_exist = False
                    for el in self.modeler.schematic.components:
                        if self.modeler.schematic.components[el].name == parameter:
                            already_exist = True
                    if not already_exist:
                        self.modeler.schematic.create_new_component_from_symbol(
                            parameter,
                            pins,
                            refbase=fields[0][0],
                            parameter_list=parameter_list,
                            parameter_value=parameter_value,
                        )
                    mycomp = self.modeler.schematic.create_component(
                        fields[0],
                        component_library=None,
                        component_name=parameter,
                        location=[xpos, ypos],
                        use_instance_id_netlist=use_instance,
                    )
                    value = None
                elif fields[0][0] == "D":
                    value = self._get_number_from_string(fields[3])
                    mycomp = self.modeler.schematic.create_diode(
                        name, value, [xpos, ypos], use_instance_id_netlist=use_instance
                    )
                elif fields[0][0] == "V":
                    if "PULSE" not in line:
                        value = self._get_number_from_string(fields[3])
                        mycomp = self.modeler.schematic.create_voltage_dc(
                            name, value, [xpos, ypos], use_instance_id_netlist=use_instance
                        )
                    else:
                        value = line[line.index("PULSE") + 6 : line.index(")") - 1].split(" ")
                        value = [i.replace("{", "").replace("}", "") for i in value]
                        fields[1], fields[2] = fields[2], fields[1]
                        mycomp = self.modeler.schematic.create_voltage_pulse(
                            name, value, [xpos, ypos], use_instance_id_netlist=use_instance
                        )
                elif fields[0][0] == "K":
                    value = self._get_number_from_string(fields[3])
                    mycomp = self.modeler.schematic.create_coupling_inductors(
                        name, fields[1], fields[2], value, [xpos, ypos], use_instance_id_netlist=use_instance
                    )
                elif fields[0][0] == "I":
                    if "PULSE" not in line:
                        value = self._get_number_from_string(fields[3])
                        mycomp = self.modeler.schematic.create_current_dc(
                            name, value, [xpos, ypos], use_instance_id_netlist=use_instance
                        )
                    else:
                        value = line[line.index("PULSE") + 6 : line.index(")") - 1].split(" ")
                        value = [i.replace("{", "").replace("}", "") for i in value]
                        mycomp = self.modeler.schematic.create_current_pulse(
                            name, value, [xpos, ypos], use_instance_id_netlist=use_instance
                        )
                if mycomp:
                    id = 1
                    for pin in mycomp.pins:
                        pos = pin.location
                        if pos[0] < xpos:
                            angle = 0.0
                        else:
                            angle = math.pi
                        self.modeler.schematic.create_page_port(fields[id], [pos[0], pos[1]], angle)
                        id += 1
                    ypos += delta
                    if ypos > 0.254:
                        xpos += delta
                        ypos = 0
                    counter += 1
                    if counter > 59:
                        self.modeler.oeditor.CreatePage("<Page Title>")
                        counter = 0
        if autosave:
            self._desktop.EnableAutoSave(True)
        self.logger.info("Netlist was correctly imported into %s", self.design_name)
        return True

    @pyaedt_function_handler()
    def get_ibis_model_from_file(self, path):
        """Create an IBIS model based on the data contained in an IBIS file.

        Parameters
        ----------
        path : str
            Path of the IBIS file.

        Returns
        -------
        :class:`pyaedt.generic.ibis_reader.Ibis`
            IBIS object exposing all data from the IBIS file.
        """

        reader = ibis_reader.IbisReader(path, self)
        reader.parse_ibis_file()
        return reader.ibis_model

    @pyaedt_function_handler()
    def create_schematic_from_mentor_netlist(self, file_to_import):
        """Create a circuit schematic from a Mentor netlist.

        Supported currently are:

        * R
        * L
        * C
        * Diodes
        * Bjts
        * Discrete components with syntax ``Uxxx net1 net2get_source_pin_names ... netn modname``

        Parameters
        ----------
        file_to_import : str
            Full path to the HSpice file to import.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        xpos = 0
        ypos = 0
        delta = 0.0508
        use_instance = True
        my_netlist = []
        with open_file(file_to_import, "r") as f:
            for line in f:
                my_netlist.append(line.split(" "))
        nets = [i for i in my_netlist if i[0] == "NET"]
        comps = [i for i in my_netlist if i[0] == "COMP:"]
        props = {}
        for el in my_netlist:
            if el[0] == "COMP:":
                n = el[2].strip()
                n = n[1:-1]
                props[n] = []
                i = my_netlist.index(el) + 1
                finished = False
                while not finished and i < len(my_netlist):
                    if my_netlist[i][0] == "Property:":
                        props[n].append(my_netlist[i][1])
                    elif "Pin:" in my_netlist[i]:
                        props[n].append(my_netlist[i])
                    else:
                        finished = True
                    i += 1

        column_number = int(math.sqrt(len(comps)))
        for el in comps:
            name = el[2].strip()  # Remove carriage return.
            name = name[1:-1]  # Remove quotes.
            if len(el) > 3:
                comptype = el[3]
            else:
                comptype = self.retrieve_mentor_comp(el[2])
            value = "required"
            for prop in props[name]:
                if "Value=" in prop:
                    value = prop.split("=")[1].replace(",", ".").strip()

            mycomp = None
            if "resistor:RES." in comptype:
                mycomp = self.modeler.schematic.create_resistor(
                    name, value, [xpos, ypos], use_instance_id_netlist=use_instance
                )
            elif "inductor:COIL." in comptype:
                mycomp = self.modeler.schematic.create_inductor(
                    name, value, [xpos, ypos], use_instance_id_netlist=use_instance
                )
            elif "capacitor:CAP." in comptype:
                mycomp = self.modeler.schematic.create_capacitor(
                    name, value, [xpos, ypos], use_instance_id_netlist=use_instance
                )
            elif "transistor:NPN" in comptype:
                mycomp = self.modeler.schematic.create_npn(
                    name, value, [xpos, ypos], use_instance_id_netlist=use_instance
                )
            elif "transistor:PNP" in comptype:
                mycomp = self.modeler.schematic.create_pnp(
                    name, value, [xpos, ypos], use_instance_id_netlist=use_instance
                )
            elif "diode:" in comptype:
                mycomp = self.modeler.schematic.create_diode(
                    name, value, [xpos, ypos], use_instance_id_netlist=use_instance
                )

            if mycomp:
                id = 1
                for pin in mycomp.pins:
                    pos = pin.location
                    if pos[0] < xpos:
                        angle = 0.0
                    else:
                        angle = math.pi
                    netname = None
                    for net in nets:
                        net = [i.strip() for i in net]
                        if (name + "-" + str(id)) in net:
                            fullnetname = net[2]
                            netnames = fullnetname.split("/")
                            netname = (
                                netnames[len(netnames) - 1].replace(",", "_").replace("'", "").replace("$", "").strip()
                            )
                    if not netname:
                        prop = props[name]
                        if "Pin:" in prop and id in prop:
                            netname = prop[-1]
                            netname = netname.replace("$", "")

                    if netname:
                        self.modeler.schematic.create_page_port(netname, [pos[0], pos[1]], angle)
                    else:
                        self.logger.info("Page port was not created.")
                    id += 1
                ypos += delta
                if ypos > delta * (column_number):
                    xpos += delta
                    ypos = 0

        for el in nets:
            netname = el[2][1:-1]
            netname = netname.replace("$", "")
            if "GND" in netname.upper():
                self.modeler.schematic.create_gnd([xpos, ypos])
                page_pos = ypos + 0.00254
                mod1 = self.modeler.schematic.create_page_port(netname, [xpos, ypos], 0.0)
                mod1.location = [str(xpos) + "meter", str(page_pos) + "meter"]
                ypos += delta
                if ypos > delta * column_number:
                    xpos += delta
                    ypos = 0

        self.logger.info("Netlist was correctly imported into %s", self.design_name)
        return True

    @pyaedt_function_handler()
    def retrieve_mentor_comp(self, refid):
        """Retrieve the type of the Mentor netlist component for a given reference ID.

        Parameters
        ----------
        refid : int
            Reference ID.

        Returns
        -------
        str
            Type of the Mentor netlist component.

        """
        if refid[1] == "R":
            return "resistor:RES."
        elif refid[1] == "C":
            return "capacitor:CAP."
        elif refid[1] == "L":
            return "inductor:COIL."
        elif refid[1] == "D":
            return "diode"
        elif refid[1] == "Q":
            return "transistor:NPN"
        else:
            return ""

    @pyaedt_function_handler()
    def get_source_pin_names(
        self, source_design_name, source_project_name=None, source_project_path=None, port_selector=3
    ):
        """Retrieve pin names.

        Parameters
        ----------
        source_design_name : str
            Name of the source design.
        source_project_name : str, optional
            Name of the source project. The default is ``None``.
        source_project_path : str, optional
            Path to the source project if different than the existing path. The default is ``None``.
        port_selector : int, optional
            Type of the port. Options are ``1``, ``2``, and ``3``, corresponding respectively to ``"Wave Port"``,
            ``"Terminal"``, or ``"Circuit Port"``. The default is ``3``, which is a circuit port.

        Returns
        -------
        list
            List of pin names.

        References
        ----------

        >>> oModule.GetExcitationsOfType
        """
        if source_project_name and self.project_name != source_project_name and not source_project_path:
            raise AttributeError(
                "If the source project is different from the current one, `source_project_path` must also be provided."
            )
        if source_project_path and not source_project_name:
            raise AttributeError(
                "When `source_project_path` is specified, `source_project_name` must also be provided."
            )
        if not source_project_name or self.project_name == source_project_name:
            oSrcProject = self._desktop.GetActiveProject()
        else:
            self._desktop.OpenProject(source_project_path)
            oSrcProject = self._desktop.SetActiveProject(source_project_name)
        oDesign = oSrcProject.SetActiveDesign(source_design_name)
        tmp_oModule = oDesign.GetModule("BoundarySetup")
        port = None
        if port_selector == 1:
            port = "Wave Port"
        elif port_selector == 2:
            port = "Terminal"
        elif port_selector == 3:
            port = "Circuit Port"
        if not port:
            return False
        pins = list(tmp_oModule.GetExcitationsOfType(port))
        self.logger.info("%s Excitations Pins found.", len(pins))
        return pins

    @pyaedt_function_handler()
    def import_touchstone_solution(self, filename, solution_name="Imported_Data"):
        """Import a Touchstone file as the solution.

        Parameters
        ----------
        filename : str
            Name of the Touchstone file.
        solution_name : str, optional
            Name of the solution. The default is ``"Imported_Data"``.

        Returns
        -------
        list
            List of ports.

        References
        ----------

        >>> oDesign.ImportData
        """
        if filename[-2:] == "ts":
            with open_file(filename, "r") as f:
                lines = f.readlines()
                for i in lines:
                    if "[Number of Ports]" in i:
                        ports = int(i[i.find("]") + 1 :])
                portnames = [i.split(" = ")[1].strip() for i in lines if "! Port" in i[:9]]
                if not portnames:
                    portnames = ["Port{}".format(i + 1) for i in range(ports)]
        else:
            re_filename = re.compile(r"\.s(?P<ports>\d+)+p", re.I)
            m = re_filename.search(filename)
            ports = int(m.group("ports"))
            portnames = None
            with open_file(filename, "r") as f:
                lines = f.readlines()
                portnames = [i.split(" = ")[1].strip() for i in lines if "Port[" in i]
            if not portnames:
                portnames = ["Port{}".format(i + 1) for i in range(ports)]
        arg = [
            "NAME:NPortData",
            "Description:=",
            "",
            "ImageFile:=",
            "",
            "SymbolPinConfiguration:=",
            0,
            ["NAME:PortInfoBlk"],
            ["NAME:PortOrderBlk"],
            "filename:=",
            filename,
            "numberofports:=",
            ports,
            "sssfilename:=",
            "",
            "sssmodel:=",
            False,
            "PortNames:=",
            portnames,
            "domain:=",
            "frequency",
            "datamode:=",
            "Link",
            "devicename:=",
            "",
            "SolutionName:=",
            solution_name,
            "displayformat:=",
            "MagnitudePhase",
            "datatype:=",
            "SMatrix",
            [
                "NAME:DesignerCustomization",
                "DCOption:=",
                0,
                "InterpOption:=",
                0,
                "ExtrapOption:=",
                1,
                "Convolution:=",
                0,
                "Passivity:=",
                0,
                "Reciprocal:=",
                False,
                "ModelOption:=",
                "",
                "DataType:=",
                1,
            ],
            [
                "NAME:NexximCustomization",
                "DCOption:=",
                3,
                "InterpOption:=",
                1,
                "ExtrapOption:=",
                3,
                "Convolution:=",
                0,
                "Passivity:=",
                0,
                "Reciprocal:=",
                False,
                "ModelOption:=",
                "",
                "DataType:=",
                2,
            ],
            [
                "NAME:HSpiceCustomization",
                "DCOption:=",
                1,
                "InterpOption:=",
                2,
                "ExtrapOption:=",
                3,
                "Convolution:=",
                0,
                "Passivity:=",
                0,
                "Reciprocal:=",
                False,
                "ModelOption:=",
                "",
                "DataType:=",
                3,
            ],
            "NoiseModelOption:=",
            "External",
        ]
        self.odesign.ImportData(arg, "", True)
        self.logger.info("Touchstone file was correctly imported into %s", self.design_name)
        return portnames

    @pyaedt_function_handler()
    def export_touchstone(
        self, solution_name=None, sweep_name=None, file_name=None, variations=None, variations_value=None
    ):
        """Export the Touchstone file to a local folder.

        Parameters
        ----------
        solution_name : str, optional
            Name of the solution that has been solved.
        sweep_name : str, optional
            Name of the sweep that has been solved.
        file_name : str, optional
            Full path and name for the Touchstone file.
            The default is ``None``, in which case the file is exported to the working directory.
        variations : list, optional
            List of all parameter variations. For example, ``["$AmbientTemp", "$PowerIn"]``.
            The default is ``None``.
        variations_value : list, optional
            List of all parameter variation values. For example, ``["22cel", "100"]``.
            The default is ``None``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oDesign.ExportNetworkData
        """
        return self._export_touchstone(
            solution_name=solution_name,
            sweep_name=sweep_name,
            file_name=file_name,
            variations=variations,
            variations_value=variations_value,
        )

    @pyaedt_function_handler()
    def export_fullwave_spice(
        self,
        designname=None,
        setupname=None,
        is_solution_file=False,
        filename=None,
        passivity=False,
        causality=False,
        renormalize=False,
        impedance=50,
        error=0.5,
        poles=10000,
    ):
        """
        Export a full wave HSpice file using NDE.

        .. warning::
          This method doesn't work.

        Parameters
        ----------
        designname : str, optional
            Name of the design or the full path to the solution file if it is an imported file.
            The default is ``None``.
        setupname : str, optional
            Name of the setup if it is a design. The default is ``None``.
        is_solution_file : bool, optional
            Whether it is an imported solution file. The default is ``False``.
        filename : str, optional
            Full path and name for exporting the HSpice file.
            The default is ``None``, in which case the file is exported to the working directory.
        passivity : bool, optional
            Whether to compute the passivity. The default is ``False``.
        causality : bool, optional
            Whether to compute the causality. The default is ``False``.
        renormalize : bool, optional
            Whether to renormalize the S-matrix to a specific port impedance.
            The default is ``False``.
        impedance : float, optional
            Impedance value if ``renormalize=True``. The default is ``50``.
        error : float, optional
            Fitting error. The default is ``0.5``.
        poles : int, optional
            Number of fitting poles. The default is ``10000``.

        Returns
        -------
        str
            Name of the HSpice file if the export is successful.

        References
        ----------

        >>> oDesign.ExportFullWaveSpice
        """
        if not designname:
            designname = self.design_name
        if not filename:
            filename = os.path.join(self.working_directory, self.design_name + ".sp")
        if is_solution_file:
            setupname = designname
            designname = ""
        else:
            if not setupname:
                setupname = self.nominal_sweep
        self.onetwork_data_explorer.ExportFullWaveSpice(
            designname,
            is_solution_file,
            setupname,
            "",
            [],
            [
                "NAME:SpiceData",
                "SpiceType:=",
                "HSpice",
                "EnforcePassivity:=",
                passivity,
                "EnforceCausality:=",
                causality,
                "UseCommonGround:=",
                True,
                "ShowGammaComments:=",
                True,
                "Renormalize:=",
                renormalize,
                "RenormImpedance:=",
                impedance,
                "FittingError:=",
                error,
                "MaxPoles:=",
                poles,
                "PassivityType:=",
                "IteratedFittingOfPV",
                "ColumnFittingType:=",
                "Matrix",
                "SSFittingType:=",
                "FastFit",
                "RelativeErrorToleranc:=",
                False,
                "EnsureAccurateZfit:=",
                True,
                "TouchstoneFormat:=",
                "MA",
                "TouchstoneUnits:=",
                "GHz",
                "TouchStonePrecision:=",
                15,
                "SubcircuitName:=",
                "",
                "SYZDataInAutoMode:=",
                False,
                "ExportDirectory:=",
                os.path.dirname(filename) + "\\",
                "ExportSpiceFileName:=",
                os.path.basename(filename),
                "FullwaveSpiceFileName:=",
                os.path.basename(filename),
                "UseMultipleCores:=",
                True,
                "NumberOfCores:=",
                20,
            ],
        )
        self.logger.info("FullWaveSpice correctly exported to %s", filename)

        return filename

    @pyaedt_function_handler()
    def create_touchstone_report(
        self,
        plot_name,
        curvenames,
        solution_name=None,
        variation_dict=None,
        differential_pairs=False,
        subdesign_id=None,
    ):
        """
        Create a Touchstone plot.

        Parameters
        ----------
        plot_name : str
            Name of the plot.
        curvenames : list
            List of names for the curves to plot.
        solution_name : str, optional
            Name of the solution. The default value is ``None``.
        variation_dict : dict, optional
            Dictionary of variation names. The default value is ``None``.
        differential_pairs : bool, optional
            Specify if the plot is on differential pairs traces. The default value is ``False``.
        subdesign_id : int, optional
            Specify a subdesign ID to export a Touchstone file of this subdesign. The default value is ``None``.
        Returns
        -------
        bool
           ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oModule.CreateReport
        """
        if not solution_name:
            solution_name = self.nominal_sweep
        variations = {"Freq": ["All"]}
        if variation_dict:
            for el in variation_dict:
                variations[el] = [variation_dict[el]]
        dif = None
        if differential_pairs:
            dif = "Differential Pairs"
        return self.post.create_report(
            curvenames, solution_name, variations=variations, plotname=plot_name, context=dif, subdesign_id=subdesign_id
        )

    @pyaedt_function_handler()
    def get_touchstone_data(self, curvenames, solution_name=None, variation_dict=None):
        """
        Return a Touchstone data plot.

        Parameters
        ----------
        curvenames : list
            List of the curves to plot.
        solution_name : str, optional
            Name of the solution. The default value is ``None``.
        variation_dict : dict, optional
            Dictionary of variation names. The default value is ``None``.

        Returns
        -------
        :class:`pyaedt.modules.solutions.SolutionData`
           Class containing all requested data.

        References
        ----------

        >>> oModule.GetSolutionDataPerVariation
        """
        if not solution_name:
            solution_name = self.nominal_sweep
        variations = {"Freq": ["All"]}
        if variation_dict:
            for el in variation_dict:
                variations[el] = [variation_dict[el]]
        ctxt = ["NAME:Context", "SimValueContext:=", [3, 0, 2, 0, False, False, -1, 1, 0, 1, 1, "", 0, 0]]
        return self.post.get_solution_data_per_variation("Standard", solution_name, ctxt, variations, curvenames)

    @pyaedt_function_handler()
    def push_excitations(self, instance_name, thevenin_calculation=False, setup_name="LinearFrequency"):
        """Push excitations.

        Parameters
        ----------
        instance_name : str
            Name of the instance.
        thevenin_calculation : bool, optional
            Whether to perform the Thevenin equivalent calculation. The default is ``False``.
        setup_name : str, optional
            Name of the solution setup to push. The default is ``"LinearFrequency"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> oEditor.PushExcitations
        """
        arg = ["NAME:options", "CalcThevenin:=", thevenin_calculation, "Sol:=", setup_name]

        self.modeler.oeditor.PushExcitations(instance_name, arg)
        return True

    @pyaedt_function_handler()
    def create_source(self, source_type, name=None):
        """Create a source in Circuit.

        Parameters
        ----------
        source_type : str
            Source type to create. Sources available are:

            * PowerSin.
            * PowerIQ.
            * VoltageFrequencyDependent.
            * VoltageDC.
            * VoltageSin.
            * CurrentSin.

        name : str, optional
            Source name.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.Source`
            Circuit Source Object.

        References
        ----------

        >>> oDesign.UpdateSources
        """
        if not name:
            name = generate_unique_name("Source")
        if name in self.source_names:
            self.logger.warning("Source name is defined in the design.")
            return False
        if source_type not in SourceKeys.SourceNames:
            self.logger.warning("Source type is not correct.")
            return False
        if source_type == "PowerSin":
            new_source = PowerSinSource(self, name, source_type)
        elif source_type == "PowerIQ":
            new_source = PowerIQSource(self, name, source_type)
        elif source_type == "VoltageFrequencyDependent":
            new_source = VoltageFrequencyDependentSource(self, name, source_type)
        elif source_type == "VoltageDC":
            new_source = VoltageDCSource(self, name, source_type)
        elif source_type == "VoltageSin":
            new_source = VoltageSinSource(self, name, source_type)
        elif source_type == "CurrentSin":
            new_source = CurrentSinSource(self, name, source_type)
        else:
            new_source = Sources(self, name, source_type)
        new_source.create()
        if not self._internal_sources:
            self._internal_sources = {name: new_source}
        else:
            self._internal_sources.update({name: new_source})
        return new_source

    @pyaedt_function_handler()
    def assign_voltage_sinusoidal_excitation_to_ports(self, ports):
        """Assign a voltage sinusoidal excitation to circuit ports.

        Parameters
        ----------
        ports : list
            List of circuit ports to assign to the sinusoidal excitation.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.Source`
            Circuit Source Object.

        References
        ----------

        >>> oDesign.UpdateSources
        """

        source_v = self.create_source(source_type="VoltageSin")
        for port in ports:
            self.excitations[port].enabled_sources.append(source_v.name)
            self.excitations[port].update()
        return source_v

    @pyaedt_function_handler()
    def assign_current_sinusoidal_excitation_to_ports(self, ports):
        """Assign a current sinusoidal excitation to circuit ports.

        Parameters
        ----------
        ports : list
            List of circuit ports to assign to the sinusoidal excitation.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.Source`
            Circuit Source Object.

        References
        ----------

        >>> oDesign.UpdateSources
        """
        source_i = self.create_source(source_type="CurrentSin")
        for port in ports:
            self.excitations[port].enabled_sources.append(source_i.name)
            self.excitations[port].update()
        return source_i

    @pyaedt_function_handler()
    def assign_power_sinusoidal_excitation_to_ports(self, ports):
        """Assign a power sinusoidal excitation to circuit ports.

        Parameters
        ----------
        ports : list
            List of circuit ports to assign to the sinusoidal excitation.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.Source`
            Circuit Source Object.

        References
        ----------

        >>> oDesign.UpdateSources
        """
        source_p = self.create_source(source_type="CurrentSin")
        for port in ports:
            self.excitations[port].enabled_sources.append(source_p.name)
            self.excitations[port].update()
        return source_p

    @pyaedt_function_handler()
    def assign_voltage_frequency_dependent_excitation_to_ports(self, ports, filepath):
        """Assign a frequency dependent excitation to circuit ports from a frequency dependent source (.fds format).

        Parameters
        ----------
        ports : list
            List of circuit ports to assign to the frequency dependent excitation.
        filepath : str
            Path to the frequency dependent file.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.Source`
            Circuit Source Object.

        References
        ----------

        >>> oDesign.UpdateSources
        """
        if not os.path.exists(filepath) or os.path.splitext(filepath)[1] != ".fds":
            self.logger.error("Introduced file is not correct. Check path and format.")
            return False

        if not all(elem in self.excitation_names for elem in ports):
            self.logger.error("Defined ports do not exist")
            return False

        source_freq = self.create_source(source_type="VoltageFrequencyDependent")
        source_freq.fds_filename = filepath
        for port in ports:
            self.excitations[port].enabled_sources.append(source_freq.name)
            self.excitations[port].update()
        return source_freq

    @pyaedt_function_handler()
    def set_differential_pair(
        self,
        positive_terminal,
        negative_terminal,
        common_name=None,
        diff_name=None,
        common_ref_z=25,
        diff_ref_z=100,
        active=True,
    ):
        """Add a differential pair definition.

        Parameters
        ----------
        positive_terminal : str
            Name of the terminal to use as the positive terminal.
        negative_terminal : str
            Name of the terminal to use as the negative terminal.
        common_name : str, optional
            Name for the common mode. Default is ``None`` in which case a unique name is chosen.
        diff_name : str, optional
            Name for the differential mode. Default is ``None`` in which case a unique name is chosen.
        common_ref_z : float, optional
            Reference impedance for the common mode. Units are Ohm. Default is ``25``.
        diff_ref_z : float, optional
            Reference impedance for the differential mode. Units are Ohm. Default is ``100``.
        active : bool, optional
            Set the differential pair as active. Default is ``True``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesign.SetDiffPairs
        """
        if not diff_name:
            diff_name = generate_unique_name("Diff")
        if not common_name:
            common_name = generate_unique_name("Comm")

        arg1 = [
            "Pos:=",
            positive_terminal,
            "Neg:=",
            negative_terminal,
            "On:=",
            active,
            "matched:=",
            False,
            "Dif:=",
            diff_name,
            "DfZ:=",
            [float(diff_ref_z), 0],
            "Com:=",
            common_name,
            "CmZ:=",
            [float(common_ref_z), 0],
        ]

        arg = ["NAME:DiffPairs"]
        arg.append("Pair:=")
        arg.append(arg1)

        tmpfile1 = os.path.join(self.working_directory, generate_unique_name("tmp"))
        self.odesign.SaveDiffPairsToFile(tmpfile1)
        with open_file(tmpfile1, "r") as fh:
            lines = fh.read().splitlines()
        num_diffs_before = len(lines)
        old_arg = []
        for line in lines:
            data = line.split(",")
            data_arg = [
                "Pos:=",
                data[0],
                "Neg:=",
                data[1],
                "On:=",
                data[2] == "1",
                "matched:=",
                False,
                "Dif:=",
                data[4],
                "DfZ:=",
                [float(data[5]), 0],
                "Com:=",
                data[6],
                "CmZ:=",
                [float(data[7]), 0],
            ]
            old_arg.append(data_arg)

        for arg2 in old_arg:
            arg.append("Pair:=")
            arg.append(arg2)

        try:
            os.remove(tmpfile1)
        except:  # pragma: no cover
            self.logger.warning("ERROR: Cannot remove temp files.")

        try:
            self.odesign.SetDiffPairs(arg)
        except:  # pragma: no cover
            return False
        return True

    @pyaedt_function_handler()
    def load_diff_pairs_from_file(self, filename):
        """Load differtential pairs definition from a file.

        You can use the the ``save_diff_pairs_to_file`` method to obtain the file format.
        New definitions are added only if they are compatible with the existing definitions in the project.

        Parameters
        ----------
        filename : str
            Full qualified name of the file containing the differential pairs definition.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesign.LoadDiffPairsFromFile
        """
        if not os.path.isfile(filename):  # pragma: no cover
            raise ValueError("{}: The specified file could not be found.".format(filename))

        try:
            new_file = os.path.join(os.path.dirname(filename), generate_unique_name("temp") + ".txt")
            with open_file(filename, "r") as file:
                filedata = file.read().splitlines()
            with io.open(new_file, "w", newline="\n") as fh:
                for line in filedata:
                    fh.write(line + "\n")

            self.odesign.LoadDiffPairsFromFile(new_file)
            os.remove(new_file)
        except:  # pragma: no cover
            return False
        return True

    @pyaedt_function_handler()
    def save_diff_pairs_to_file(self, filename):
        """Save differtential pairs definition to file.

        If the file that is specified already exists, it is overwritten.

        Parameters
        ----------
        filename : str
            Full qualified name of the file containing the differential pairs definition.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesign.SaveDiffPairsToFile
        """
        self.odesign.SaveDiffPairsToFile(filename)

        return os.path.isfile(filename)

    @pyaedt_function_handler()
    def add_netlist_datablock(self, netlist_file, datablock_name=None):
        """Add a new netlist data block to the circuit schematic.

        Parameters
        ----------
        netlist_file : str
            Path to the netlist file.
        datablock_name : str, optional
            Name of the data block.

        Returns
        -------
        bool
            ``True`` if successfully created, ``False`` otherwise.
        """
        if not os.path.exists(netlist_file):
            self.logger.error("Netlist File doesn't exists")
            return False
        if not datablock_name:
            datablock_name = generate_unique_name("Inc")

        tmp_oModule = self.odesign.GetModule("DataBlock")
        tmp_oModule.AddNetlistDataBlock(
            ["NAME:DataBlock", "name:=", datablock_name, "filename:=", netlist_file, "filelocation:=", 0]
        )
        return True

    @pyaedt_function_handler()
    def browse_log_file(self, filepath=None):
        """Save most recent log file into a new directory.

        Parameters
        ----------
        filepath : str, optional
            New log file path. The default is the pyaedt folder.

        Returns
        -------
        str
            File Path.
        """
        if filepath and not os.path.exists(os.path.normpath(filepath)):
            self.logger.error("Path does not exist.")
            return None
        elif not filepath:
            filepath = os.path.join(os.path.normpath(self.working_directory), "logfile")
            if not os.path.exists(filepath):
                os.mkdir(filepath)

        results_path = os.path.join(os.path.normpath(self.results_directory), self.design_name)
        results_temp_path = os.path.join(results_path, "temp")

        # Check if .log exist in temp folder
        if os.path.exists(results_temp_path) and glob.glob(os.path.join(results_temp_path, "*.log")):
            # Check the most recent
            files = glob.glob(os.path.join(results_temp_path, "*.log"))
            latest_file = max(files, key=os.path.getctime)
        elif os.path.exists(results_path) and glob.glob(os.path.join(results_path, "*.log")):
            # Check the most recent
            files = glob.glob(os.path.join(results_path, "*.log"))
            latest_file = max(files, key=os.path.getctime)
        else:
            self.logger.error("Design not solved")
            return None

        shutil.copy(latest_file, filepath)
        filename = os.path.basename(latest_file)
        return os.path.join(filepath, filename)
