"""This module contains the ``Hfss3dLayout`` class."""

from __future__ import absolute_import  # noreorder

from collections import OrderedDict
import fnmatch
import io
import os
import re

from pyaedt import is_ironpython, settings
from pyaedt.application.Analysis3DLayout import FieldAnalysis3DLayout
from pyaedt.generic.general_methods import (
    generate_unique_name,
    open_file,
    parse_excitation_file,
    pyaedt_function_handler,
    tech_to_control_file,
)
from pyaedt.modeler.pcb.object3dlayout import Line3dLayout  # noqa: F401
from pyaedt.modules.Boundary import BoundaryObject3dLayout


class Hfss3dLayout(FieldAnalysis3DLayout):
    """Provides the HFSS 3D Layout application interface.

    This class inherits all objects that belong to HFSS 3D Layout, including EDB
    API queries.

    Parameters
    ----------
    projectname : str, optional
        Name of the project to select or the full path to the project
        or AEDTZ archive to open or the path to the ``aedb`` folder or
        ``edb.def`` file. The default is ``None``, in which case an
        attempt is made to get an active project. If no projects are present,
        an empty project is created.
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
    specified_version : str, int, float, optional
        Version of AEDT to use. The default is ``None``, in which case
        the active version or latest installed version is used.
        Examples of input values are ``232``, ``23.2``,``2023.2``,``"2023.2"``.
    non_graphical : bool, optional
        Whether to launch AEDT in non-graphical mode. The default
        is ``False```, in which case AEDT is launched in graphical mode.
        This parameter is ignored when a script is launched within AEDT.
    new_desktop_session : bool, optional
        Whether to launch an instance of AEDT in a new thread, even if
        another instance of the ``specified_version`` is active on the
        machine. The default is ``True``.
    close_on_exit : bool, optional
        Whether to release AEDT on exit. The default is ``False``.
    student_version : bool, optional
        Whether to open the AEDT student version. The default is ``False``.
    machine : str, optional
        Machine name to connect the oDesktop session to. This works only in 2022 R2 or later.
        The remote server must be up and running with the command `"ansysedt.exe -grpcsrv portnum"`.
        If the machine is `"localhost"`. the server also starts if not present.
    port : int, optional
        Port number on which to start the oDesktop communication on an already existing server.
        This parameter is ignored when creating a new server. It works only in 2022 R2 or later.
        The remote server must be up and running with the command `"ansysedt.exe -grpcsrv portnum"`.
    aedt_process_id : int, optional
        Process ID for the instance of AEDT to point PyAEDT at. The default is
        ``None``. This parameter is only used when ``new_desktop_session = False``.

    Examples
    --------
    Create an ``Hfss3dLayout`` object and connect to an existing HFSS
    design or create a new HFSS design if one does not exist.

    >>> from pyaedt import Hfss3dLayout
    >>> aedtapp = Hfss3dLayout()

    Create an ``Hfss3dLayout`` object and link to a project named
    ``projectname``. If this project does not exist, create one with
    this name.

    >>> aedtapp = Hfss3dLayout(projectname)

    Create an ``Hfss3dLayout`` object and link to a design named
    ``designname`` in a project named ``projectname``.

    >>> aedtapp = Hfss3dLayout(projectname,designame)

    Create an ``Hfss3dLayout`` object and open the specified project.

    >>> aedtapp = Hfss3dLayout("myfile.aedt")

    Create an AEDT 2023 R1 object and then create a
    ``Hfss3dLayout`` object and open the specified project.

    >>> aedtapp = Hfss3dLayout(specified_version="2023.1", projectname="myfile.aedt")

    Create an instance of ``Hfss3dLayout`` from an ``Edb``

    >>> import pyaedt
    >>> edb_path = "/path/to/edbfile.aedb"
    >>> edb = pyaedt.Edb(edb_path, edbversion=231)
    >>> edb.import_stackup("stackup.xml")  # Import stackup. Manipulate edb, ...
    >>> edb.save_edb()
    >>> edb.close_edb()
    >>> aedtapp = pyaedt.Hfss3dLayout(specified_version=231, projectname=edb_path)

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
        FieldAnalysis3DLayout.__init__(
            self,
            "HFSS 3D Layout Design",
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

    def _init_from_design(self, *args, **kwargs):
        self.__init__(*args, **kwargs)

    def __enter__(self):
        return self

    @pyaedt_function_handler()
    def create_edge_port(
        self,
        primivitivename,
        edgenumber,
        iscircuit=False,
        iswave=False,
        wave_horizontal_extension=5,
        wave_vertical_extension=3,
        wave_launcher="1mm",
        ref_primitive_name=None,
        ref_edge_number=0,
    ):
        # type: (str | Line3dLayout,int,bool, bool,float,float, str, str, str | int) -> BoundaryObject3dLayout | bool
        """Create an edge port.

        Parameters
        ----------
        primivitivename : str or :class:`pyaedt.modeler.pcb.object3dlayout.Line3dLayout`
            Name of the primitive to create the edge port on.
        edgenumber :
            Edge number to create the edge port on.
        iscircuit : bool, optional
            Whether the edge port is a circuit port. The default is ``False``.
        iswave : bool, optional
            Whether the edge port is a wave port. The default is ``False``.
        wave_horizontal_extension : float, optional
            Horizontal port extension factor. The default is `5`.
        wave_vertical_extension : float, optional
            Vertical port extension factor. The default is `5`.
        wave_launcher : str, optional
            PEC (perfect electrical conductor) launcher size with units. The
            default is `"1mm"`.
        ref_primitive_name : str, optional
            Name of the reference primitive to place negative edge port terminal.
            The default is ``None``.
        ref_edge_number : str, int
            Edge number of reference primitive. The default is ``0``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject3dLayout`
            Port objcet port when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.CreateEdgePort
        """
        primivitivename = self.modeler.convert_to_selections(primivitivename, False)
        listp = self.port_list
        self.modeler.oeditor.CreateEdgePort(
            [
                "NAME:Contents",
                "edge:=",
                ["et:=", "pe", "prim:=", primivitivename, "edge:=", edgenumber],
                "circuit:=",
                iscircuit,
                "btype:=",
                0,
            ]
        )

        listnew = self.port_list
        a = [i for i in listnew if i not in listp]

        if ref_primitive_name:
            self.modeler.oeditor.AddRefPort(
                [a[0]],
                ["NAME:Contents", "edge:=", ["et:=", "pe", "prim:=", ref_primitive_name, "edge:=", ref_edge_number]],
            )

        if len(a) > 0:
            if iswave:
                self.modeler.change_property(
                    property_object="Excitations:{}".format(a[0]),
                    property_name="HFSS Type",
                    property_value="Wave",
                    property_tab="EM Design",
                )
                self.modeler.change_property(
                    property_object="Excitations:{}".format(a[0]),
                    property_name="Horizontal Extent Factor",
                    property_value=str(wave_horizontal_extension),
                    property_tab="EM Design",
                )
                if "Vertical Extent Factor" in list(
                    self.modeler.oeditor.GetProperties("EM Design", "Excitations:{}".format(a[0]))
                ):
                    self.modeler.change_property(
                        property_object="Excitations:{}".format(a[0]),
                        property_name="Vertical Extent Factor",
                        property_value=str(wave_vertical_extension),
                        property_tab="EM Design",
                    )
                self.modeler.change_property(
                    property_object="Excitations:{}".format(a[0]),
                    property_name="PEC Launch Width",
                    property_value=str(wave_launcher),
                    property_tab="EM Design",
                )
            bound = self._update_port_info(a[0])
            if bound:
                self._boundaries[bound.name] = bound
                return bound
            else:
                return False
        else:
            return False

    @pyaedt_function_handler()
    def create_wave_port(
        self,
        primivitive_name,
        edge_number,
        wave_horizontal_extension=5,
        wave_vertical_extension=3,
        wave_launcher="1mm",
    ):
        """Create a single-ended wave port.

        Parameters
        ----------
        primivitive_name : str
            Name of the primitive to create the edge port on.
        edge_number : int
            Edge number to create the edge port on.
        wave_horizontal_extension : float, optional
            Horizontal port extension factor. The default is ``5``.
        wave_vertical_extension : float, optional
            Vertical port extension factor. The default is ``5``.
        wave_launcher : str, optional
            PEC (perfect electrical conductor) launcher size with units. The
            default is ``"1mm"``.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject3dLayout`
            Port objcet port when successful, ``False`` when failed.

        References
        ----------
        """
        port_name = self.create_edge_port(
            primivitive_name,
            edge_number,
            wave_horizontal_extension=wave_horizontal_extension,
            wave_vertical_extension=wave_vertical_extension,
            wave_launcher=wave_launcher,
        )
        if port_name:
            port_name["HFSS Type"] = "Wave"
            port_name["Horizontal Extent Factor"] = str(wave_horizontal_extension)
            if "Vertical Extent Factor" in list(port_name.props.keys()):
                port_name["Vertical Extent Factor"] = str(wave_vertical_extension)
            port_name["PEC Launch Width"] = str(wave_launcher)
            return port_name
        else:
            return False

    @pyaedt_function_handler()
    def create_wave_port_from_two_conductors(self, primivitivenames=[""], edgenumbers=[""]):
        """Create a wave port.

        Parameters
        ----------
        primivitivenames : list(str)
            List of the primitive names to create the wave port on.
            The list must have two entries, one entry for each of the two conductors,
            or the method is not executed.

        edgenumbers :
            List of the edge number to create the wave port on.
            The list must have two entries, one entry for each of the two edges,
            or the method is not executed.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject3dLayout`
            Port objcet port when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.CreateEdgePort
        """
        if len(primivitivenames) == 2 and len(edgenumbers) == 2:
            listp = self.port_list
            self.modeler.oeditor.CreateEdgePort(
                [
                    "NAME:Contents",
                    "edge:=",
                    ["et:=", "pe", "prim:=", primivitivenames[0], "edge:=", edgenumbers[0]],
                    "edge:=",
                    ["et:=", "pe", "prim:=", primivitivenames[1], "edge:=", edgenumbers[1]],
                    "external:=",
                    True,
                    "btype:=",
                    0,
                ]
            )
            listnew = self.port_list
            a = [i for i in listnew if i not in listp]
            if len(a) > 0:
                bound = self._update_port_info(a[0])
                if bound:
                    self.boundaries.append(bound)
                    return self.boundaries[-1]
                else:
                    return False
            else:
                return False
        else:
            return False

    @pyaedt_function_handler()
    def create_ports_on_component_by_nets(
        self,
        component_name,
        nets,
    ):
        """Create the ports on a component for a list of nets.

        Parameters
        ----------
        component_name : str
            Component name.
        nets : str, list
            Nets to include.


        Returns
        -------
        list of :class:`pyaedt.modules.Boundary.BoundaryObject3dLayout`
            Port Objects when successful.

        References
        ----------
        >>> oEditor.CreateEdgePort
        """
        listp = self.port_list
        if isinstance(nets, list):
            pass
        else:
            nets = [nets]
        net_array = ["NAME:Nets"] + nets
        self.oeditor.CreatePortsOnComponentsByNet(["NAME:Components", component_name], net_array, "Port", "0", "0", "0")
        listnew = self.port_list
        a = [i for i in listnew if i not in listp]
        ports = []
        if len(a) > 0:
            for port in a:
                bound = self._update_port_info(port)
                if bound:
                    self._boundaries[bound.name] = bound
                    ports.append(bound)
        return ports

    @pyaedt_function_handler()
    def create_differential_port(self, via_signal, via_reference, port_name, deembed=True):
        """Create a new differential port.

        Parameters
        ----------
        via_signal : str
            Signal pin.
        via_reference : float
            Reference pin.
        port_name : str
            New Port Name.
        deembed : bool, optional
            Either to deembed parasitics or not. Default is `True`.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject3dLayout`
            Port Object when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.CreateEdgePort
        """
        listp = self.port_list
        if port_name in self.port_list:
            self.logger.error("Port already existing on via {}".format(port_name))
            return False
        self.oeditor.ToggleViaPin(["NAME:elements", via_signal])

        listnew = self.port_list
        a = [i for i in listnew if i not in listp]
        if len(a) > 0:
            self.modeler.change_property("Excitations:{}".format(a[0]), "Port", port_name, "EM Design")
            self.modeler.oeditor.AssignRefPort([port_name], via_reference)
            if deembed:
                self.modeler.change_property(
                    "Excitations:{}".format(port_name), "DeembedParasiticPortInductance", deembed, "EM Design"
                )
            bound = self._update_port_info(port_name)
            if bound:
                self.boundaries.append(bound)
                return self.boundaries[-1]
            else:
                return False
        else:
            return False

    @pyaedt_function_handler()
    def create_coax_port(self, vianame, radial_extent=0.1, layer=None, alignment="lower"):
        """Create a new coax port.

        Parameters
        ----------
        vianame : str
            Name of the via to create the port on.
        radial_extent : float
            Radial coax extension.
        layer : str
            Name of the layer to apply the reference to.
        alignment : str, optional
            Port alignment on the layer.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject3dLayout`
            Port Object when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.CreateEdgePort
        """
        listp = self.port_list
        if vianame in self.port_list:
            self.logger.error("Port already existing on via {}".format(vianame))
            return False
        self.oeditor.ToggleViaPin(["NAME:elements", vianame])

        listnew = self.port_list
        a = [i for i in listnew if i not in listp]
        if len(a) > 0:
            self.modeler.change_property(
                "Excitations:{}".format(a[0]), "Radial Extent Factor", str(radial_extent), "EM Design"
            )
            self.modeler.change_property("Excitations:{}".format(a[0]), "Layer Alignment", alignment, "EM Design")
            if layer:
                self.modeler.change_property(
                    a[0],
                    "Pad Port Layer",
                    layer,
                )
            bound = self._update_port_info(a[0])
            if bound:
                self._boundaries[bound.name] = bound
                return bound
            else:
                return False
        else:
            return False

    @pyaedt_function_handler()
    def create_pin_port(self, name, xpos=0, ypos=0, rotation=0, top_layer=None, bot_layer=None):
        """Create a pin port.

        Parameters
        ----------
        name : str
            Name of the pin port.
        xpos : float, optional
            X-axis position of the pin. The default is ``0``.
        ypos : float, optional
            Y-axis position of the pin. The default is ``0``.
        rotation : float, optional
            Rotation of the pin in degrees. The default is ``0``.
        top_layer : str, optional
            Top layer of the pin. The default is ``None``, in which case the top
            layer is assigned automatically.
        bot_layer : str
            Bottom layer of the pin. The default is ``None``, in which case the
            bottom layer is assigned automatically.

        Returns
        -------
        :class:`pyaedt.modules.Boundary.BoundaryObject3dLayout`

            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.CreatePin
        """
        layers = self.modeler.layers.all_signal_layers
        if not top_layer:
            top_layer = layers[0].name
        if not bot_layer:
            bot_layer = layers[len(layers) - 1].name
        self.modeler.oeditor.CreatePin(
            [
                "NAME:Contents",
                ["NAME:Port", "Name:=", name],
                "ReferencedPadstack:=",
                "Padstacks:NoPad SMT East",
                "vposition:=",
                ["x:=", str(xpos) + self.modeler.model_units, "y:=", str(ypos) + self.modeler.model_units],
                "vrotation:=",
                [str(rotation) + "deg"],
                "overrides hole:=",
                False,
                "hole diameter:=",
                ["0mm"],
                "Pin:=",
                True,
                "highest_layer:=",
                top_layer,
                "lowest_layer:=",
                bot_layer,
            ]
        )
        bound = self._update_port_info(name)
        if bound:
            self._boundaries[bound.name] = bound
            return bound
        else:
            return False

    @pyaedt_function_handler()
    def delete_port(self, portname):
        """Delete a port.

        Parameters
        ----------
        portname : str
            Name of the port.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.Delete
        """
        self.oexcitation.Delete(portname)
        for bound in self.boundaries:
            if bound.name == portname:
                self.boundaries.remove(bound)
        return True

    @pyaedt_function_handler()
    def import_edb(self, edb_full_path):
        """Import EDB.

        Parameters
        ----------
        edb_full_path : str
            Full path to EDB.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.ImportEDB
        """
        if "edb.def" not in edb_full_path:
            edb_full_path = os.path.join(edb_full_path, "edb.def")
        self.oimport_export.ImportEDB(edb_full_path)
        self._close_edb()
        project_name = self.odesktop.GetActiveProject().GetName()
        design_name = self.odesktop.GetActiveProject().GetActiveDesign().GetName().split(";")[-1]
        self.__init__(projectname=project_name, designname=design_name)
        return True

    @pyaedt_function_handler()
    def validate_full_design(self, name=None, outputdir=None, ports=None):
        """Validate the design based on the expected value and save the information in the log file.

        Parameters
        ----------
        name : str, optional
            Name of the design to validate. The default is ``None``.
        outputdir : str, optional
            Output directory to save the log file to. The default is ``None``,
            in which case the file is exported to the working directory.

        ports : str, optional
            Number of excitations that are expected. The default is ``None``.

        Returns
        -------
        list of str
            List of validation messages.

        References
        ----------
        >>> oDesign.ValidateDesign
        """
        if name is None:
            name = self.design_name
        if outputdir is None:
            outputdir = self.working_directory

        self.logger.info("#### Design Validation Checks###")
        #
        # Routine outputs to the validation info to a log file in the project directory and also
        # returns the validation info to be used to update properties.xml file

        validation_ok = True

        #
        # Write an overall validation log file with all output from all checks
        # The design validation inside HFSS outputs to a separate log file which we merge into this overall file
        #
        val_list = []
        all_validate = outputdir + "\\all_validation.log"
        with open_file(all_validate, "w") as validation:
            # Desktop Messages
            msg = "Desktop Messages:"
            validation.writelines(msg + "\n")
            val_list.append(msg)
            msgs = self._desktop.GetMessages(self.project_name, name, 0)
            # need to check if design name is always this default name HFSSDesign1
            for msg in msgs:
                self.logger.info(msg)
                # msg = msg.replace('"','')
                msg = msg.rstrip("\r\n")
                val_list.append(msg)
                validation.writelines(msg + "\n")

            # Run Design Validation and write out the lines to the logger

            ret = self._odesign.ValidateCircuit()
            msg = "Design Validation Messages:"
            validation.writelines(msg + "\n")
            val_list.append(msg)
            if ret == 0:
                msg = "**** ERRORS Present - please check and confirm"
                self.logger.error(msg)
            else:
                msg = "**** Validation Completed Correctly"
                self.logger.info(msg)

            # Find the Excitations and check or list them out
            msg = "Excitation Messages:"
            validation.writelines(msg + "\n")
            val_list.append(msg)
            numportsdefined = int(len(self.excitations))
            if ports is not None and ports != numportsdefined:
                msg = "**** Port Number Error! - Please check model"
                self.logger.error(msg)
                validation.writelines(msg + "\n")
                val_list.append(msg)
                validation_ok = False
                # need to stop the simulation athis point
            else:
                msg1 = "Ports Requested: " + str(ports)
                msg2 = "Ports Defined: " + str(numportsdefined)
                self.logger.info(msg1)
                validation.writelines(msg1 + "\n")
                val_list.append(msg1)
                self.logger.info(msg2)
                validation.writelines(msg2 + "\n")
                val_list.append(msg2)

            excitation_names = self.excitations
            for excitation in excitation_names:
                msg = "Excitation name: " + str(excitation)
                self.logger.info(msg)
                validation.writelines(msg + "\n")
                val_list.append(msg)
        validation.close()
        return val_list, validation_ok  # return all the info in a list for use later

    @pyaedt_function_handler()
    def create_scattering(
        self, plot_name="S Parameter Plot Nominal", sweep_name=None, port_names=None, port_excited=None, variations=None
    ):
        """Create a scattering report.

        Parameters
        ----------
        plot_name : str, optional
            Name of the plot. The default is ``"S Parameter Plot Nominal"``.
        sweep_name : str, optional
            Name of the sweep. The default is ``None``.
        port_names : str or list, optional
            One or more port names. The default is ``None``.
        port_excited : optional
            The default is ``None``.
        variations : optional
            The default is ``None``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.CreateReport
        """
        solution_data = "Standard"
        if "Modal" in self.solution_type:
            solution_data = "Modal Solution Data"
        elif "Terminal" in self.solution_type:
            solution_data = "Terminal Solution Data"
        if not port_names:
            port_names = self.excitations
        if not port_excited:
            port_excited = port_names
        traces = ["dB(S(" + p + "," + q + "))" for p, q in zip(list(port_names), list(port_excited))]
        return self.post.create_report(
            traces, sweep_name, variations=variations, report_category=solution_data, plotname=plot_name
        )

    @pyaedt_function_handler()
    def export_touchstone(
        self, setup_name=None, sweep_name=None, file_name=None, variations=None, variations_value=None
    ):
        """Export a Touchstone file.

        Parameters
        ----------
        setup_name : str, optional
            Name of the setup that has been solved.
        sweep_name : str, optional
            Name of the sweep that has been solved.
        file_name : str, optional
            Full path and name for the Touchstone file.
            The default is ``None``, in which case the Touchstone file is exported to
            the working directory.
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
            setup_name=setup_name,
            sweep_name=sweep_name,
            file_name=file_name,
            variations=variations,
            variations_value=variations_value,
        )

    @pyaedt_function_handler()
    def set_export_touchstone(self, activate, export_dir=""):
        """Export the Touchstone file automatically if the simulation is successful.

        Parameters
        ----------
        activate : bool
            Whether to export the Touchstone file after the simulation.
        export_dir str, optional
            Path to export the Touchstone file to. The default is ``""``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesign.DesignOptions
        """
        settings = []
        if activate:
            settings.append("NAME:options")
            settings.append("ExportAfterSolve:=")
            settings.append(True)
            settings.append("ExportDir:=")
            settings.append(export_dir)
        elif not activate:
            settings.append("NAME:options")
            settings.append("ExportAfterSolve:=")
            settings.append(False)
        self.odesign.DesignOptions(settings, 0)
        return True

    @pyaedt_function_handler()
    def set_meshing_settings(self, mesh_method="Phi", enable_intersections_check=True, use_alternative_fallback=True):
        """Define the settings of the mesh.

        Parameters
        ----------
        mesh_method : string
            Mesh method. The default is ``"Phi"``. Options are ``"Phi"``, ``"PhiPlus"``,
            and ``"Classic"``.
        enable_intersections_check : bool, optional
            Whether to enable the alternative mesh intersections checks. The default is
            ``True``.
        use_alternative_fallback : bool, optional
            Whether to enable the alternative fall back mesh method. The default is ``True``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesign.DesignOptions
        """
        settings = []
        settings.append("NAME:options")
        settings.append("MeshingMethod:=")
        settings.append(mesh_method)
        settings.append("EnableDesignIntersectionCheck:=")
        settings.append(enable_intersections_check)
        settings.append("UseAlternativeMeshMethodsAsFallBack:=")
        settings.append(use_alternative_fallback)
        self.odesign.DesignOptions(settings, 0)
        return True

    @pyaedt_function_handler()
    def create_linear_count_sweep(
        self,
        setupname,
        unit,
        freqstart,
        freqstop,
        num_of_freq_points,
        sweepname=None,
        save_fields=True,
        save_rad_fields_only=False,
        sweep_type="Interpolating",
        interpolation_tol_percent=0.5,
        interpolation_max_solutions=250,
        use_q3d_for_dc=False,
    ):
        """Create a sweep with the specified number of points.

        Parameters
        ----------
        setupname : str
            Name of the setup to attach to the sweep.
        unit : str
            Unit of the frequency. For example, ``"MHz"`` or ``"GHz"``.
        freqstart : float
            Starting frequency of the sweep.
        freqstop : float
            Stopping frequency of the sweep.
        num_of_freq_points : int
            Number of frequency points in the range.
        sweepname : str, optional
            Name of the sweep. The default is ``None``.
        save_fields : bool, optional
            Whether to save fields for a discrete sweep only. The
            default is ``True``.
        save_rad_fields_only : bool, optional
            Whether to save only radiated fields if
            ``save_fields=True``. The default is ``False``.
        sweep_type : str, optional
            Type of the sweep. Options are ``"Fast"``,
            ``"Interpolating"``, and ``"Discrete"``.  The default is
            ``"Interpolating"``.
        interpolation_tol_percent : float, optional
            Error tolerance threshold for the interpolation process.
            The default is ``0.5``.
        interpolation_max_solutions : int, optional
            Maximum number of solutions to evaluate for the
            interpolation process. The default is ``250``.
        use_q3d_for_dc : bool, optional
            Whether to use Q3D to solve the DC point. The default is ``False``.

        Returns
        -------
        :class:`pyaedt.modules.SolveSweeps.SweepHFSS3DLayout` or bool
            Sweep object if successful, ``False`` otherwise.

        References
        ----------
        >>> oModule.AddSweep
        """
        if sweep_type not in ["Discrete", "Interpolating", "Fast"]:
            raise AttributeError(
                "Invalid value for `sweep_type`. The value must be 'Discrete', 'Interpolating', or 'Fast'."
            )
        if sweepname is None:
            sweepname = generate_unique_name("Sweep")

        interpolation = False
        if sweep_type == "Interpolating":
            interpolation = True
            save_fields = False

        if not save_fields:
            save_rad_fields_only = False

        interpolation_tol = interpolation_tol_percent / 100.0

        for s in self.setups:
            if s.name == setupname:
                setupdata = s
                if sweepname in [sweep.name for sweep in setupdata.sweeps]:
                    oldname = sweepname
                    sweepname = generate_unique_name(oldname)
                    self.logger.warning(
                        "Sweep %s is already present. Sweep has been renamed in %s.", oldname, sweepname
                    )
                sweep = setupdata.add_sweep(sweepname=sweepname)
                if not sweep:
                    return False
                sweep.change_range("LinearCount", freqstart, freqstop, num_of_freq_points, unit)
                sweep.props["GenerateSurfaceCurrent"] = save_fields
                sweep.props["SaveRadFieldsOnly"] = save_rad_fields_only
                sweep.props["FastSweep"] = interpolation
                sweep.props["SAbsError"] = interpolation_tol
                sweep.props["EnforcePassivity"] = interpolation
                sweep.props["UseQ3DForDC"] = use_q3d_for_dc
                sweep.props["MaxSolutions"] = interpolation_max_solutions
                sweep.update()
                self.logger.info("Linear count sweep %s has been correctly created.", sweepname)
                return sweep
        return False

    @pyaedt_function_handler()
    def create_linear_step_sweep(
        self,
        setupname,
        unit,
        freqstart,
        freqstop,
        step_size,
        sweepname=None,
        save_fields=True,
        save_rad_fields_only=False,
        sweep_type="Interpolating",
        interpolation_tol_percent=0.5,
        interpolation_max_solutions=250,
        use_q3d_for_dc=False,
    ):
        """Create a sweep with the specified frequency step.

        Parameters
        ----------
        setupname : str
            Name of the setup to attach to the sweep.
        unit : str
            Unit of the frequency. For example, ``"MHz"`` or ``"GHz"``.
        freqstart : float
            Starting frequency of the sweep.
        freqstop : float
            Stopping frequency of the sweep.
        step_size : float
            Frequency size of the step.
        sweepname : str, optional
            Name of the sweep. The default is ``None``.
        save_fields : bool, optional
            Whether to save fields for a discrete sweep only. The
            default is ``True``.
        save_rad_fields_only : bool, optional
            Whether to save only radiated fields if
            ``save_fields=True``. The default is ``False``.
        sweep_type : str, optional
            Type of the sweep. Options are ``"Fast"``,
            ``"Interpolating"``, and ``"Discrete"``.  The default is
            ``"Interpolating"``.
        interpolation_tol_percent : float, optional
            Error tolerance threshold for the interpolation
            process. The default is ``0.5``.
        interpolation_max_solutions : int, optional
            Maximum number of solutions to evaluate for the
            interpolation process. The default is ``250``.
        use_q3d_for_dc : bool, optional
            Whether to use Q3D to solve the DC point. The default is ``False``.

        Returns
        -------
        :class:`pyaedt.modules.SolveSweeps.SweepHFSS3DLayout` or bool
            Sweep object if successful, ``False`` otherwise.

        References
        ----------
        >>> oModule.AddSweep
        """
        if sweep_type not in ["Discrete", "Interpolating", "Fast"]:
            raise AttributeError(
                "Invalid value for `sweep_type`. The value must be 'Discrete', 'Interpolating', or 'Fast'."
            )
        if sweepname is None:
            sweepname = generate_unique_name("Sweep")

        interpolation = False
        if sweep_type == "Interpolating":
            interpolation = True
            save_fields = False

        if not save_fields:
            save_rad_fields_only = False

        interpolation_tol = interpolation_tol_percent / 100.0

        for s in self.setups:
            if s.name == setupname:
                setupdata = s
                if sweepname in [sweep.name for sweep in setupdata.sweeps]:
                    oldname = sweepname
                    sweepname = generate_unique_name(oldname)
                    self.logger.warning(
                        "Sweep %s is already present. Sweep has been renamed in %s.", oldname, sweepname
                    )
                sweep = setupdata.add_sweep(sweepname=sweepname)
                if not sweep:
                    return False
                sweep.change_range("LinearStep", freqstart, freqstop, step_size, unit)
                sweep.props["GenerateSurfaceCurrent"] = save_fields
                sweep.props["SaveRadFieldsOnly"] = save_rad_fields_only
                sweep.props["FastSweep"] = interpolation
                sweep.props["SAbsError"] = interpolation_tol
                sweep.props["EnforcePassivity"] = interpolation
                sweep.props["UseQ3DForDC"] = use_q3d_for_dc
                sweep.props["MaxSolutions"] = interpolation_max_solutions
                sweep.update()
                self.logger.info("Linear step sweep %s has been correctly created.", sweepname)
                return sweep
        return False

    @pyaedt_function_handler()
    def create_single_point_sweep(
        self,
        setupname,
        unit,
        freq,
        sweepname=None,
        save_fields=False,
        save_rad_fields_only=False,
    ):
        """Create a sweep with a single frequency point.

        Parameters
        ----------
        setupname : str
            Name of the setup.
        unit : str
            Unit of the frequency. For example, ``"MHz`` or ``"GHz"``.
        freq : float, list
            Frequency of the single point or list of frequencies to create distinct single points.
        sweepname : str, optional
            Name of the sweep. The default is ``None``.
        save_fields : bool, optional
            Whether to save fields for all points and subranges defined in the sweep. The default is ``False``.
        save_rad_fields_only : bool, optional
            Whether to save only radiating fields. The default is ``False``.

        Returns
        -------
        :class:`pyaedt.modules.SolveSweeps.SweepHFSS` or bool
            Sweep object if successful, ``False`` otherwise.

        References
        ----------
        >>> oModule.AddSweep
        """
        if sweepname is None:
            sweepname = generate_unique_name("SinglePoint")

        add_subranges = False
        if isinstance(freq, list):
            if not freq:
                raise AttributeError("Frequency list is empty. Specify at least one frequency point.")
            freq0 = freq.pop(0)
            if freq:
                add_subranges = True
        else:
            freq0 = freq

        if setupname not in self.setup_names:
            return False
        for s in self.setups:
            if s.name == setupname:
                setupdata = s
                if sweepname in [sweep.name for sweep in setupdata.sweeps]:
                    oldname = sweepname
                    sweepname = generate_unique_name(oldname)
                    self.logger.warning(
                        "Sweep %s is already present. Sweep has been renamed in %s.", oldname, sweepname
                    )
                sweepdata = setupdata.add_sweep(sweepname, "Discrete")
                sweepdata.change_range("SinglePoint", freq0, unit=unit)
                sweepdata.props["GenerateSurfaceCurrent"] = save_fields
                sweepdata.props["SaveRadFieldsOnly"] = save_rad_fields_only
                sweepdata.update()
                if add_subranges:
                    for f in freq:
                        sweepdata.add_subrange(rangetype="SinglePoint", start=f, unit=unit)
                self.logger.info("Single point sweep %s has been correctly created.", sweepname)
                return sweepdata
        return False

    @pyaedt_function_handler()
    def _import_cad(
        self, cad_path, cad_format="gds", aedb_path=None, xml_path=None, set_as_active=True, close_active_project=False
    ):
        method = None
        if cad_format == "gds":
            method = self.oimport_export.ImportGDSII
        elif cad_format == "dxf":
            method = self.oimport_export.ImportAutoCAD
        elif cad_format == "gerber":
            method = self.oimport_export.ImportGerber
        elif cad_format == "awr":
            method = self.oimport_export.ImportAWRMicrowaveOffice
        elif cad_format == "brd":
            method = self.oimport_export.ImportExtracta
        elif cad_format == "ipc2581":
            method = self.oimport_export.ImportIPC
        elif cad_format == "odb++":
            method = self.oimport_export.ImportODB
        if not method:
            return False
        active_project = self.project_name
        path_ext = os.path.splitext(cad_path)
        if not aedb_path:
            aedb_path = path_ext[0] + ".aedb"
        project_name = os.path.splitext(os.path.basename(aedb_path))[0]

        if os.path.exists(aedb_path):
            old_name = project_name
            project_name = generate_unique_name(project_name)
            aedb_path = aedb_path.replace(old_name, project_name)
            self.logger.warning("aedb_exists. Renaming it to %s", project_name)
        if not xml_path:
            xml_path = ""
        elif os.path.splitext(xml_path)[1] == ".tech":
            xml_path = tech_to_control_file(xml_path)
        if cad_format == "gds":
            method(cad_path, aedb_path, xml_path, "")
        else:
            method(cad_path, aedb_path, xml_path)

        if set_as_active:
            self._close_edb()
            self.__init__(project_name)
        if close_active_project:
            self.odesktop.CloseProject(active_project)
        return True

    @pyaedt_function_handler()
    def import_gds(self, gds_path, aedb_path=None, control_file=None, set_as_active=True, close_active_project=False):
        """Import a GDS file into HFSS 3D Layout and assign the stackup from an XML file if present.

        Parameters
        ----------
        gds_path : str
            Full path to the GDS file.
        aedb_path : str, optional
            Full path to the AEDB file.
        control_file : str, optional
            Path to the XML or TECH file with the stackup information. The default is ``None``, in
            which case the stackup is not edited.
            If a TECH file is provided and the layer name starts with ``"v"``, the layer
            is mapped as a via layer.
        set_as_active : bool, optional
            Whether to set the GDS file as active. The default is ``True``.
        close_active_project : bool, optional
            Whether to close the active project after loading the GDS file.
            The default is ''False``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.ImportGDSII
        """
        return self._import_cad(gds_path, "gds", aedb_path, control_file, set_as_active, close_active_project)

    @pyaedt_function_handler()
    def import_dxf(self, dxf_path, aedb_path=None, control_file=None, set_as_active=True, close_active_project=False):
        """Import a DXF file into HFSS 3D Layout and assign the stackup from an XML file if present.

        Parameters
        ----------
        dxf_path : str
            Full path to the DXF file.
        aedb_path : str, optional
            Full path to the AEDB file.
        control_file : str, optional
            Path to the XML or TECH file with the stackup information. The default is ``None``, in
            which case the stackup is not edited.
            If a TECH file is provided and the layer name starts with ``"v"``, the layer
            is mapped as a via layer.
        set_as_active : bool, optional
            Whether to set the DXF file as active. The default is ``True``.
        close_active_project : bool, optional
            Whether to close the active project after loading the DXF file.
            The default is ''False``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.ImportDXF
        """
        return self._import_cad(dxf_path, "dxf", aedb_path, control_file, set_as_active, close_active_project)

    @pyaedt_function_handler()
    def import_gerber(
        self, gerber_path, aedb_path=None, control_file=None, set_as_active=True, close_active_project=False
    ):
        """Import a Gerber zip file into HFSS 3D Layout and assign the stackup from an XML file if present.

        Parameters
        ----------
        gerber_path : str
            Full path to the Gerber zip file.
        aedb_path : str, optional
            Full path to the AEDB file.
        control_file : str, optional
            Path to the XML file with the stackup information. The default is ``None``, in
            which case the stackup is not edited.
        set_as_active : bool, optional
            Whether to set the Gerber zip file file as active. The default is ``True``.
        close_active_project : bool, optional
            Whether to close the active project after loading the Gerber zip file file.
            The default is ''False``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.ImportGerber
        """
        return self._import_cad(gerber_path, "gerber", aedb_path, control_file, set_as_active, close_active_project)

    @pyaedt_function_handler()
    def import_brd(
        self, input_file, aedb_path=None, set_as_active=True, close_active_project=False, control_file=None
    ):  # pragma: no cover
        """Import a board file into HFSS 3D Layout and assign the stackup from an XML file if present.

        Parameters
        ----------
        input_file : str
            Full path to the board file.
        aedb_path : str, optional
            Full path to the AEDB file.
        set_as_active : bool, optional
            Whether to set the board file as active. The default is ``True``.
        close_active_project : bool, optional
            Whether to close the active project after loading the board file.
            The default is ''False``.
        control_file : str, optional
            Path to the XML file with the stackup information. The default is ``None``, in
            which case the stackup is not edited.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.ImportExtracta
        """
        return self._import_cad(input_file, "brd", aedb_path, control_file, set_as_active, close_active_project)

    @pyaedt_function_handler()
    def import_awr(
        self, input_file, aedb_path=None, control_file=None, set_as_active=True, close_active_project=False
    ):  # pragma: no cover
        """Import an AWR Microwave Office file into HFSS 3D Layout and assign the stackup from an XML file if present.

        Parameters
        ----------
        input_file : str
            Full path to the AWR Microwave Office file.
        aedb_path : str, optional
            Full path to the AEDB file.
        control_file : str, optional
            Path to the XML file with the stackup information. The default is ``None``, in
            which case the stackup is not edited.
        set_as_active : bool, optional
            Whether to set the AWR Microwave Office file as active. The default is ``True``.
        close_active_project : bool, optional
            Whether to close the active project after loading the AWR Microwave Office file.
            The default is ''False``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.ImportAWRMicrowaveOffice
        """
        return self._import_cad(input_file, "awr", aedb_path, control_file, set_as_active, close_active_project)

    @pyaedt_function_handler()
    def import_ipc2581(
        self, input_file, aedb_path=None, control_file=None, set_as_active=True, close_active_project=False
    ):
        """Import an IPC2581 file into HFSS 3D Layout and assign the stackup from an XML file if present.

        Parameters
        ----------
        input_file : str
            Full path to the IPC2581 file.
        aedb_path : str, optional
            Full path to the AEDB file.
        control_file : str, optional
            Path to the XML file with the stackup information. The default is ``None``, in
            which case the stackup is not edited.
        set_as_active : bool, optional
            Whether to set the IPC2581 file as active. The default is ``True``.
        close_active_project : bool, optional
            Whether to close the active project after loading the IPC2581 file.
            The default is ''False``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.ImportAWRMicrowaveOffice
        """
        return self._import_cad(input_file, "ipc2581", aedb_path, control_file, set_as_active, close_active_project)

    @pyaedt_function_handler()
    def import_odb(self, input_file, aedb_path=None, control_file=None, set_as_active=True, close_active_project=False):
        """Import an ODB++ file into HFSS 3D Layout and assign the stackup from an XML file if present.

        Parameters
        ----------
        input_file : str
            Full path to the ODB++ file.
        aedb_path : str, optional
            Full path to the AEDB file.
        control_file : str, optional
            Path to the XML file with the stackup information. The default is ``None``, in
            which case the stackup is not edited.
        set_as_active : bool, optional
            Whether to set the ODB++ file as active. The default is ``True``.
        close_active_project : bool, optional
            Whether to close the active project after loading the ODB++ file.
            The default is ''False``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.ImportAWRMicrowaveOffice
        """
        return self._import_cad(input_file, "odb++", aedb_path, control_file, set_as_active, close_active_project)

    @pyaedt_function_handler()
    def edit_cosim_options(
        self,
        simulate_missing_solution=True,
        align_ports=True,
        renormalize_ports=True,
        renorm_impedance=50,
        setup_override_name=None,
        sweep_override_name=None,
        use_interpolating_sweep=False,
        use_y_matrix=True,
        interpolation_algorithm="auto",
    ):
        """Edit cosimulation options.

        Parameters
        ----------
        simulate_missing_solution : bool, optional
            Whether the solver is to simulate a missing solution. The default is ``True``. If
            ``False``, the solver interpolates a missing solution.
        align_ports : bool, optional
            Whether the solver is to align microwave parts. The default is ``True``.
        renormalize_ports : bool, optional
            Whether to renormalize port impendance. The default is ``True``.
        renorm_impedance : float, optional
            Renormalization impedance in ohms. The default is ``50``.
        setup_override_name : str, optional
            Setup name if there is a setup override. The default is ``None``.
        sweep_override_name : str, optional
            Sweep name if there is a sweep override. The default is ``None``.
        use_interpolating_sweep : bool, optional
            Whether the solver is to use an interpolating sweep. The default is ``True``.
            If ``False``, the solver is to use a discrete sweep.
        use_y_matrix : bool, optional
            Whether the interpolation algorithm is to use the Y matrix. The default is
            ``True``.
        interpolation_algorithm : str, optional
            Interpolation algorithm to use. Options are ``"auto"``, ``"lin"``, ``"shadH"``,
            and ``"shadNH"``. The default is ``"auto"``.

        Returns
        -------
        bool
            ``True`` if successful and ``False`` if failed.

        References
        ----------
        >>> oDesign.EditCoSimulationOptions

        Examples
        --------
        >>> from pyaedt import Hfss3dLayout
        >>> h3d = Hfss3dLayout()
        >>> h3d.edit_cosim_options(
        ...     simulate_missing_solution=True,
        ...     align_ports=True,
        ...     renormalize_ports=True,
        ...     renorm_impedance=50,
        ...     setup_override_name=None,
        ...     sweep_override_name=None,
        ...     use_interpolating_sweep=False,
        ...     use_y_matrix=True,
        ...     interpolation_algorithm="auto"
        ... )

        """
        if interpolation_algorithm not in ["auto", "lin", "shadH", "shadNH"]:
            self.logger.error("Wrong Interpolation Algorithm")
            return False
        arg = ["NAME:CoSimOptions", "Override:="]

        if setup_override_name:
            arg.append(True)
            arg.append("Setup:=")
            arg.append(setup_override_name)
        else:
            arg.append(False)
            arg.append("Setup:=")
            arg.append("")
        arg.append("OverrideSweep:=")

        if sweep_override_name:
            arg.append(True)
            arg.append("Sweep:=")
            arg.append(sweep_override_name)
        else:
            arg.append(False)
            arg.append("Sweep:=")
            arg.append("")
        arg.append("SweepType:=")
        if use_interpolating_sweep:
            arg.append(6)
        else:
            arg.append(4)
        arg.append("Interpolate:=")
        arg.append(not simulate_missing_solution)
        arg.append("YMatrix:=")
        arg.append(use_y_matrix)
        arg.append("AutoAlignPorts:=")
        arg.append(align_ports)
        arg.append("InterpAlg:=")
        arg.append(interpolation_algorithm)
        arg.append("Renormalize:=")
        arg.append(renormalize_ports)
        arg.append("RenormImpedance:=")
        arg.append(renorm_impedance)
        self.odesign.EditCoSimulationOptions(arg)
        return True

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
        matched=False,
    ):
        """Add a differential pair definition.

        Parameters
        ----------
        positive_terminal : str
            Name of the terminal to use as the positive terminal.
        negative_terminal : str
            Name of the terminal to use as the negative terminal.
        common_name : str, optional
            Name for the common mode. The default is ``None``, in which case a unique name is assigned.
        diff_name : str, optional
            Name for the differential mode. The default is ``None``, in which case a unique name is assigned.
        common_ref_z : float, optional
            Reference impedance for the common mode in ohms. The default is ``25``.
        diff_ref_z : float, optional
            Reference impedance for the differential mode in ohms. The default is ``100``.
        active : bool, optional
            Whether to set the differential pair as active. The default is ``True``.
        matched : bool, optional
            Whether to set the differential pair as active. The default is ``False``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.SetDiffPairs
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
            matched,
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
        self.oexcitation.SaveDiffPairsToFile(tmpfile1)
        with open_file(tmpfile1, "r") as fh:
            lines = fh.read().splitlines()
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
                data[3] == "1",
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
            self.oexcitation.SetDiffPairs(arg)
        except:  # pragma: no cover
            return False
        return True

    @pyaedt_function_handler()
    def get_differential_pairs(self):
        # type: () -> list
        """Get the list defined differential pairs.

        Parameters
        ----------
        None

        Returns
        -------
        list
            List of differential pairs.

        Examples
        --------
        >>> from pyaedt import Hfss3dLayout
        >>> hfss = Hfss3dLayout()
        >>> hfss.get_defined_diff_pairs()
        """
        list_output = []
        if len(self.excitations) != 0:
            tmpfile1 = os.path.join(self.working_directory, generate_unique_name("tmp"))
            file_flag = self.save_diff_pairs_to_file(tmpfile1)
            if file_flag and os.stat(tmpfile1).st_size != 0:
                with open_file(tmpfile1, "r") as fi:
                    fi_lst = fi.readlines()
                list_output = [line.split(",")[4] for line in fi_lst]
            else:
                self.logger.warning("ERROR: No differential pairs defined under Excitations > Differential Pairs...")

            try:
                os.remove(tmpfile1)
            except:  # pragma: no cover
                self.logger.warning("ERROR: Cannot remove temp files.")

        return list_output

    @pyaedt_function_handler()
    def load_diff_pairs_from_file(self, filename):
        # type: (str) -> bool
        """Load differtential pairs definition from file.

        You can use the ``save_diff_pairs_to_file`` method to obtain the file format.
        The ``File End Of Line`` must be UNIX (LF).
        New definitions are added only if compatible with the existing definition already defined in the project.

        Parameters
        ----------
        filename : str
            Fully qualified name of the file containing the differential pairs definition.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.LoadDiffPairsFromFile
        """
        if not os.path.isfile(filename):  # pragma: no cover
            raise ValueError("{}: unable to find the specified file.".format(filename))

        try:
            new_file = os.path.join(os.path.dirname(filename), generate_unique_name("temp") + ".txt")
            with open_file(filename, "r") as file:
                filedata = file.read().splitlines()
            with io.open(new_file, "w", newline="\n") as fh:
                for line in filedata:
                    fh.write(line + "\n")

            self.oexcitation.LoadDiffPairsFromFile(new_file)
            os.remove(new_file)
        except:  # pragma: no cover
            return False
        return True

    @pyaedt_function_handler()
    def save_diff_pairs_to_file(self, filename):
        # type: (str) -> bool
        """Save differtential pairs definition to a file.

        If a file with the specified name already exists, it is overwritten.

        Parameters
        ----------
        filename : str
            Fully qualified name of the file containing the differential pairs definition.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.SaveDiffPairsToFile
        """
        self.oexcitation.SaveDiffPairsToFile(filename)

        return os.path.isfile(filename)

    @pyaedt_function_handler()
    def export_3d_model(self, file_name=None):
        """Export the Ecad model to a 3D file.

        Parameters
        ----------
        file_name : str, optional
            Full name of the file to export. The default is None, in which case the file name is
            set to the design name and saved as a SAT file in the working directory.
            Extensions available are ``"sat"``, ``"sab"``, and ``"sm3"`` up to AEDT 2022R2 and
            Parasolid format `"x_t"` from AEDT 2023R1.

        Returns
        -------
        str
            File name if successful.
        """
        if not file_name:
            if settings.aedt_version > "2022.2":
                file_name = os.path.join(self.working_directory, self.design_name + ".x_t")
                self.modeler.oeditor.ExportCAD(["NAME:options", "FileName:=", file_name])

            else:
                file_name = os.path.join(self.working_directory, self.design_name + ".sat")
                self.modeler.oeditor.ExportAcis(["NAME:options", "FileName:=", file_name])

        return file_name

    @pyaedt_function_handler()
    def enable_rigid_flex(self):
        """Turn on or off the rigid flex of a board with bending if available.

        This function is the same for both turning on and off rigid flex.

        Returns
        -------
        bool
            ``True`` if rigid flex is turned off, ``False``` if rigid flex is turned off.
            In non-graphical, ``True`` is always returned due to a bug in the native API.
        """
        if settings.aedt_version >= "2022.2":
            self.modeler.oeditor.ProcessBentModelCmd()
        if self.desktop_class.non_graphical:
            return True
        return True if self.variable_manager["BendModel"].expression == "1" else False

    @pyaedt_function_handler
    def edit_hfss_extents(
        self,
        diel_extent_type=None,
        diel_extent_horizontal_padding=None,
        diel_honor_primitives_on_diel_layers="keep",
        air_extent_type=None,
        air_truncate_model_at_ground_layer="keep",
        air_vertical_positive_padding=None,
        air_vertical_negative_padding=None,
        airbox_values_as_dim=True,
        air_horizontal_padding=None,
    ):
        """Edit HFSS 3D Layout extents.

        Parameters
        ----------
        diel_extent_type : str, optional
            Dielectric extent type. The default is ``None``. Options are ``"BboxExtent"``,
            ``"ConformalExtent"``, and ``"ConvexHullExtent"``.
        diel_extent_horizontal_padding : str, optional
            Dielectric extent horizontal padding. The default is ``None``.
        diel_honor_primitives_on_diel_layers : str, optional
            Whether to set dielectric honor primitives on dielectric layers. The default is ``None``.
        air_extent_type : str, optional
            Airbox extent type. The default is ``None``. Options are ``"BboxExtent"``,
            ``"ConformalExtent"``, and ``"ConvexHullExtent"``.
        air_truncate_model_at_ground_layer : str, optional
            Whether to set airbox truncate model at ground layer. The default is ``None``.
        air_vertical_positive_padding : str, optional
            Airbox vertical positive padding. The default is ``None``.
        air_vertical_negative_padding : str, optional
            Airbox vertical negative padding. The default is ``None``.
        airbox_values_as_dim : bool, optional
            Either if inputs are dims or not. Default is `True`.
        air_horizontal_padding : float, optional
            Airbox horizontal padding. The default is ``None``.


        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        arg = ["NAME:HfssExportInfo"]
        if diel_extent_type:
            arg.append("DielExtentType:=")
            arg.append(diel_extent_type)
        if diel_extent_horizontal_padding:
            arg.append("DielExt:=")
            arg.append(["Ext:=", diel_extent_horizontal_padding, "Dim:=", False])
        if not diel_honor_primitives_on_diel_layers == "keep":
            arg.append("HonorUserDiel:=")
            arg.append(diel_honor_primitives_on_diel_layers)
        if air_extent_type:
            arg.append("ExtentType:=")
            arg.append(air_extent_type)
        if not air_truncate_model_at_ground_layer == "keep":
            arg.append("TruncAtGnd:=")
            arg.append(air_truncate_model_at_ground_layer)
        if air_horizontal_padding:
            arg.append("AirHorExt:=")
            arg.append(["Ext:=", str(air_horizontal_padding), "Dim:=", airbox_values_as_dim])
        if air_vertical_positive_padding:
            arg.append("AirPosZExt:=")
            arg.append(["Ext:=", air_vertical_positive_padding, "Dim:=", airbox_values_as_dim])
        if air_vertical_negative_padding:
            arg.append("AirNegZExt:=")
            arg.append(["Ext:=", air_vertical_negative_padding, "Dim:=", airbox_values_as_dim])
        arg.append("UseStackupForZExtFact:=")
        arg.append(True)

        self.odesign.EditHfssExtents(arg)
        return True

    @pyaedt_function_handler()
    def _update_port_info(self, port):
        propnames = self.oeditor.GetProperties("EM Design", "Excitations:{}".format(port))
        props = OrderedDict()
        for prop in propnames:
            props[prop] = self.oeditor.GetPropertyValue("EM Design", "Excitations:{}".format(port), prop)
        return BoundaryObject3dLayout(self, port, props, "Port")

    @pyaedt_function_handler()
    def get_model_from_mesh_results(self, binary=True):
        """Get the path for the parasolid file in the result folder.
        The parasolid file is generated after the mesh is created in 3D Layout.

        Parameters
        ----------
        binary : str, optional
            Either if retrieve binary format of parasoli or not.

        Returns
        -------
        str
            Path for the parasolid file in the results folder.
        """
        startpath = os.path.join(self.results_directory, self.design_name)
        if not binary:
            model_name = "model_sm3.x_t"
        else:
            model_name = "model.x_b"

        out_files = [
            os.path.join(dirpath, filename)
            for dirpath, _, filenames in os.walk(startpath)
            for filename in filenames
            if fnmatch.fnmatch(filename, model_name)
        ]
        if out_files:
            out_files.sort(key=lambda x: os.path.getmtime(x))
            return out_files[0]
        return ""

    @pyaedt_function_handler()
    def edit_source_from_file(
        self,
        source_name,
        file_name,
        is_time_domain=True,
        x_scale=1,
        y_scale=1,
        impedance=50,
        data_format="Power",
        encoding="utf-8",
        include_post_effects=True,
        incident_voltage=True,
    ):
        """Edit a source from file data.
        File data is a csv containing either frequency data or time domain data that will be converted through FFT.

        Parameters
        ----------
        source_name : str
            Source Name.
        file_name : str
            Full name of the input file.
        is_time_domain : bool, optional
            Either if the input data is Time based or Frequency Based. Frequency based data are Mag/Phase (deg).
        x_scale : float, optional
            Scaling factor for x axis.
        y_scale : float, optional
            Scaling factor for y axis.
        impedance : float, optional
            Excitation impedance. Default is `50`.
        data_format : str, optional
            Either `"Power"`, `"Current"` or `"Voltage"`.
        encoding : str, optional
            Csv file encoding.
        include_post_effects : bool, optional
            Either if include or not post-processing effects. Default is `True`,
        incident_voltage : bool, optional
            Either if include or incident or total voltage. Default is `True`, for incident voltage.


        Returns
        -------
        bool
        """
        out = "Voltage"
        freq, mag, phase = parse_excitation_file(
            file_name=file_name,
            is_time_domain=is_time_domain,
            x_scale=x_scale,
            y_scale=y_scale,
            impedance=impedance,
            data_format=data_format,
            encoding=encoding,
            out_mag=out,
        )
        ds_name_mag = "ds_" + source_name.replace(":", "_mode_") + "_Mag"
        ds_name_phase = "ds_" + source_name.replace(":", "_mode_") + "_Angle"
        if self.dataset_exists(ds_name_mag, False):
            self.design_datasets[ds_name_mag].x = freq
            self.design_datasets[ds_name_mag].y = mag
            self.design_datasets[ds_name_mag].update()
        else:
            self.create_dataset1d_design(ds_name_mag, freq, mag, xunit="Hz")
        if self.dataset_exists(ds_name_phase, False):
            self.design_datasets[ds_name_phase].x = freq
            self.design_datasets[ds_name_phase].y = phase
            self.design_datasets[ds_name_phase].update()

        else:
            self.create_dataset1d_design(ds_name_phase, freq, phase, xunit="Hz", yunit="deg")
        for p in self.boundaries:
            if p.name == source_name:
                str_val = ["TotalVoltage"]
                if incident_voltage:
                    str_val = ["IncidentVoltage"]
                if include_post_effects:
                    str_val.append("IncludePortPostProcess")
                self.oboundary.EditExcitations(
                    [
                        "NAME:Excitations",
                        [source_name, "pwl({}, Freq)".format(ds_name_mag), "pwl({}, Freq)".format(ds_name_phase)],
                    ],
                    ["NAME:Terminations", [source_name, False, str(impedance) + "ohm", "0ohm"]],
                    ",".join(str_val),
                    [],
                )

                self.logger.info("Source Excitation updated with Dataset.")
                return True
        self.logger.error("Port not found.")
        return False

    def get_dcir_solution_data(self, setup_name, show="RL", category="Loop_Resistance"):
        """Retrieve dcir solution data. Available element_names are dependent on element_type as below.
        Sources ["Voltage", "Current", "Power"]
        "RL" ['Loop Resistance', 'Path Resistance', 'Resistance', 'Inductance']
        "Vias" ['X', 'Y', 'Current', 'Limit', 'Resistance', 'IR Drop', 'Power']
        "Bondwires" ['Current', 'Limit', 'Resistance', 'IR Drop']
        "Probes" ['Voltage'].

        Parameters
        ----------
        setup_name : str
            Name of the setup.
        show : str, optional
            Type of the element. Options are ``"Sources"`, ``"RL"`, ``"Vias"``, ``"Bondwires"``, and ``"Probes"``.
        category : str, optional
            Name of the element. Options are ``"Voltage"`, ``"Current"`, ``"Power"``, ``"Loop_Resistance"``,
            ``"Path_Resistance"``, ``"Resistance"``, ``"Inductance"``, ``"X"``, ``"Y"``, ``"Limit"`` and ``"IR Drop"``.

        Returns
        -------
        pyaedt.modules.solutions.SolutionData
        """
        if is_ironpython:  # pragma: no cover
            self._logger.error("Function is only supported in CPython.")
            return False
        all_categories = self.post.available_quantities_categories(context=show, is_siwave_dc=True)
        if category not in all_categories:
            return False  # pragma: no cover
        all_quantities = self.post.available_report_quantities(
            context=show, is_siwave_dc=True, quantities_category=category
        )

        return self.post.get_solution_data(all_quantities, setup_sweep_name=setup_name, domain="DCIR", context=show)

    def get_touchstone_data(self, setup_name=None, sweep_name=None, variations=None):
        """Return a Touchstone data plot.

        Parameters
        ----------
        setup_name : list
            Name of the setup.
        sweep_name : str, optional
            Name of the sweep. The default value is ``None``.
        variations : dict, optional
            Dictionary of variation names. The default value is ``None``.

        Returns
        -------
        :class:`pyaedt.generic.touchstone_parser.TouchstoneData`
           Class containing all requested data.

        References
        ----------
        >>> oModule.GetSolutionDataPerVariation
        """
        from pyaedt.generic.touchstone_parser import TouchstoneData

        if not setup_name:
            setup_name = self.setups[0].name

        if not sweep_name:
            for setup in self.setups:
                if setup.name == setup_name:
                    sweep_name = setup.sweeps[0].name
        s_parameters = []
        solution = "{} : {}".format(setup_name, sweep_name)
        expression = self.get_traces_for_plot(category="S")
        sol_data = self.post.get_solution_data(expression, solution, variations=variations)
        for i in range(sol_data.number_of_variations):
            sol_data.set_active_variation(i)
            s_parameters.append(TouchstoneData(solution_data=sol_data))
        return s_parameters

    def get_dcir_element_data_loop_resistance(self, setup_name):
        """Get dcir element data loop resistance.

        Parameters
        ----------
        setup_name : str
            Name of the setup.

        Returns
        -------
        pandas.Dataframe
        """
        if is_ironpython:  # pragma: no cover
            self.logger.error("Method not supported in IronPython.")
            return False
        import pandas as pd

        solution_data = self.get_dcir_solution_data(setup_name=setup_name, show="RL", category="Loop Resistance")

        terms = []
        pattern = r"LoopRes\((.*?)\)"
        for ex in solution_data.expressions:
            matches = re.findall(pattern, ex)
            if matches:
                terms.extend(matches[0].split(","))
        terms = list(set(terms))

        data = {}
        for i in terms:
            data2 = []
            for ex in ["LoopRes({},{})".format(i, j) for j in terms]:
                d = solution_data.data_magnitude(ex)
                if d is not False:
                    data2.append(d[0])
                else:
                    data2.append(False)
            data[i] = data2

        df = pd.DataFrame(data)
        df.index = terms
        return df

    def get_dcir_element_data_current_source(self, setup_name):
        """Get dcir element data current source.

        Parameters
        ----------
        setup_name : str
            Name of the setup.

        Returns
        -------
        pandas.Dataframe
        """
        if is_ironpython:  # pragma: no cover
            self.logger.error("Method not supported in IronPython.")
            return False
        import pandas as pd

        solution_data = self.get_dcir_solution_data(setup_name=setup_name, show="Sources", category="Voltage")
        terms = []
        pattern = r"^V\((.*?)\)"
        for t_name in solution_data.expressions:
            matches = re.findall(pattern, t_name)
            if matches:
                terms.append(matches[0])
        terms = list(set(terms))

        data = {"Voltage": []}
        for t_name in terms:
            ex = "V({})".format(t_name)
            value = solution_data.data_magnitude(ex, convert_to_SI=True)
            if value is not False:
                data["Voltage"].append(value[0])
        df = pd.DataFrame(data)
        df.index = terms
        return df

    def get_dcir_element_data_via(self, setup_name):
        """Get dcir element data via.

        Parameters
        ----------
        setup_name : str
            Name of the setup.

        Returns
        -------
        pandas.Dataframe
        """
        if is_ironpython:
            self.logger.error("Method not supported in IronPython.")
            return False
        import pandas as pd

        cates = ["X", "Y", "Current", "Resistance", "IR Drop", "Power"]
        df = None
        for cat in cates:
            data = {cat: []}
            solution_data = self.get_dcir_solution_data(setup_name=setup_name, show="Vias", category=cat)
            tmp_via_names = []
            pattern = r"\((.*?)\)"
            for t_name in solution_data.expressions:
                matches = re.findall(pattern, t_name)
                if matches:
                    tmp_via_names.append(matches[0])

            for ex in solution_data.expressions:
                value = solution_data.data_magnitude(ex, convert_to_SI=True)[0]
                data[cat].append(value)

            df_tmp = pd.DataFrame(data)
            df_tmp.index = tmp_via_names
            if not isinstance(df, pd.DataFrame):
                df = df_tmp
            else:
                df.merge(df_tmp, left_index=True, right_index=True, how="outer")
        return df

    @pyaedt_function_handler
    def show_extent(self, show=True):
        """Show or hide extent in a HFSS3dLayout design.

        Parameters
        ----------
        show : bool, optional
            Whether to show or not the extent.
            The default value is ``True``.

        Returns
        -------
        bool
            ``True`` is successful, ``False`` if it fails.

        >>> oEditor.SetHfssExtentsVisible

        Examples
        --------
        >>> from pyaedt import Hfss3dLayout
        >>> h3d = Hfss3dLayout()
        >>> h3d.show_extent(show=True)
        """
        try:
            self.oeditor.SetHfssExtentsVisible(show)
            return True
        except:
            return False

    @pyaedt_function_handler
    def change_options(self, color_by_net=True):
        """Change options for an existing layout.

        It changes design visualization by color.

        Parameters
        ----------
        color_by_net : bool, optional
            Whether visualize color by net or by layer.
            The default value is ``True``, which means color by net.

        Returns
        -------
        bool
            ``True`` if successful, ``False`` if it fails.

        >>> oEditor.ChangeOptions

        Examples
        --------
        >>> from pyaedt import Hfss3dLayout
        >>> h3d = Hfss3dLayout()
        >>> h3d.change_options(color_by_net=True)
        """
        try:
            options = ["NAME:options", "ColorByNet:=", color_by_net, "CN:=", self.design_name]
            oeditor = self.odesign.SetActiveEditor("Layout")
            oeditor.ChangeOptions(options)
            return True
        except:
            return False
