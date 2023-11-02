import os
import re
from warnings import warn

from pyaedt import settings
from pyaedt.edb import Edb
from pyaedt.generic.constants import AEDT_UNITS
from pyaedt.generic.general_methods import (
    generate_unique_name,
    get_filename_without_extension,
    inside_desktop,
    open_file,
    pyaedt_function_handler,
)
from pyaedt.modeler.cad.Modeler import Modeler
from pyaedt.modeler.pcb.object3dlayout import ComponentsSubCircuit3DLayout
from pyaedt.modeler.pcb.Primitives3DLayout import Primitives3DLayout
from pyaedt.modules.LayerStackup import Layers


class Modeler3DLayout(Modeler, Primitives3DLayout):
    """Manages Modeler 3D layouts.
    This class is inherited in the caller application and is accessible through the modeler variable
    object (for example, ``hfss3dlayout.modeler``).

    Parameters
    ----------
    app : :class:`pyaedt.application.Analysis3DLayout.FieldAnalysis3DLayout`
            Inherited parent object.

    Examples
    --------
    >>> from pyaedt import Hfss3dLayout
    >>> hfss = Hfss3dLayout()
    >>> my_modeler = hfss.modeler
    """

    def __init__(self, app):
        self._app = app
        self._edb = None
        self.logger.info("Loading Modeler.")
        Modeler.__init__(self, app)
        self.logger.info("Modeler loaded.")
        self.logger.info("EDB loaded.")
        self.layers = Layers(self, roughnessunits="um")
        self.logger.info("Layers loaded.")
        Primitives3DLayout.__init__(self, app)
        self._primitives = self
        self.logger.info("Primitives loaded.")
        self.rigid_flex = None

    @property
    def o_def_manager(self):
        """AEDT Definition manager."""
        return self._app.odefinition_manager

    @property
    def stackup(self):
        """Get the Stackup class and its methods.

        Returns
        -------
        :class:`pyaedt.modules.LayerStackup.Layers`
        """
        return self.layers

    @property
    def oeditor(self):
        """Oeditor Module.

        References
        ----------
        >>> oEditor = oDesign.SetActiveEditor("Layout")
        """
        return self._app.oeditor

    @property
    def o_component_manager(self):
        """Component manager object."""
        return self._app.o_component_manager

    @property
    def o_model_manager(self):
        """Model manager object."""
        return self._app.o_model_manager

    @property
    def _edb_folder(self):
        return os.path.join(self._app.project_path, self._app.project_name + ".aedb")

    @property
    def _edb_file(self):
        return os.path.join(self._edb_folder, "edb.def")

    @property
    def edb(self):
        """EBD.

        Returns
        -------
        :class:`pyaedt.edb.Edb`
             EDB.

        """
        if settings.remote_api or settings.remote_rpc_session:
            return self._edb
        if not self._edb:
            self._edb = None
            if os.path.exists(self._edb_file) or inside_desktop:
                self._edb = Edb(
                    self._edb_folder,
                    self._app.design_name,
                    True,
                    self._app._aedt_version,
                    isaedtowned=True,
                    oproject=self._app.oproject,
                )
        elif not inside_desktop:
            if self._app.project_timestamp_changed:
                if self._edb:
                    self._edb.close_edb()
                self._edb = Edb(
                    self._edb_folder,
                    self._app.design_name,
                    True,
                    self._app._aedt_version,
                    isaedtowned=True,
                    oproject=self._app.oproject,
                )
        return self._edb

    @property
    def logger(self):
        """Logger."""
        return self._app.logger

    @pyaedt_function_handler()
    def fit_all(self):
        """Fit all.

        References
        ----------
        >>> oEditor.ZoomToFit()
        """
        try:
            self._desktop.RestoreWindow()
            self.oeditor.ZoomToFit()
        except:
            self._desktop.RestoreWindow()

    @property
    def model_units(self):
        """Model units.

        References
        ----------
        >>> oEditor.GetActiveUnits
        >>> oEditor.SetActivelUnits
        """
        return self.oeditor.GetActiveUnits()

    @model_units.setter
    def model_units(self, units):
        assert units in AEDT_UNITS["Length"], "Invalid units string {0}.".format(units)
        """Set the model units as a string (for example, "mm")."""
        self.oeditor.SetActiveUnits(["NAME:Units Parameter", "Units:=", units, "Rescale:=", False])

    @property
    def primitives(self):
        """Primitives.

        .. deprecated:: 0.4.15
            There is no need to use the ``primitives`` property anymore. You can instantiate
            methods for primitives directly from the modeler.

        Returns
        -------
        :class:`pyaedt.modeler.Primitives3DLayout.Primitives3DLayout`

        """
        mess = "`primitives` is deprecated.\n"
        mess += " Use `app.modeler` directly to instantiate primitives methods."
        warn(mess, DeprecationWarning)
        return self._primitives

    @pyaedt_function_handler
    def obounding_box(self, object_name):
        """Bounding box of a specified object.

        Returns
        -------
        list
            List of [LLx, LLy, URx, URy] coordinates.

        References
        ----------
        >>> oEditor.GetBBox
        """
        bb = self.oeditor.GetBBox(object_name)
        pll = bb.BBoxLL()
        pur = bb.BBoxUR()
        return [pll.GetX(), pll.GetY(), pur.GetX(), pur.GetY()]

    @pyaedt_function_handler()
    def _arg_with_dim(self, value, units=None):
        if units is None:
            units = self.model_units
        if type(value) is str:
            try:
                float(value)
                val = "{0}{1}".format(value, units)
            except:
                val = value
        else:
            val = "{0}{1}".format(value, units)
        return val

    def _pos_with_arg(self, pos, units=None):
        xpos = self._arg_with_dim(pos[0], units)
        if len(pos) < 2:
            ypos = self._arg_with_dim(0, units)
        else:
            ypos = self._arg_with_dim(pos[1], units)
        if len(pos) < 3:
            zpos = self._arg_with_dim(0, units)
        else:
            zpos = self._arg_with_dim(pos[2], units)

        return xpos, ypos, zpos

    @pyaedt_function_handler()
    def change_property(self, property_object, property_name, property_value, property_tab="BaseElementTab"):
        """Change an oeditor property.

        Parameters
        ----------
        property_object : str
            Name of the property object. It can be the name of an excitation or field reporter.
            For example, ``Excitations:Port1`` or ``FieldsReporter:Mag_H``.
        property_name : str
            Name of the property. For example, ``Rotation Angle``.
        property_value : str, list
            Value of the property. It is a string for a single value and a list of three elements for
            ``[x,y,z]`` coordianates.
        property_tab : str
            Name of the tab to update. Options are ``BaseElementTab``, ``EM Design``, and
            ``FieldsPostProcessorTab``. The default is ``BaseElementTab``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.ChangeProperty
        """
        if isinstance(property_value, list) and len(property_value) == 3:
            xpos, ypos, zpos = self._pos_with_arg(property_value)
            self.oeditor.ChangeProperty(
                [
                    "NAME:AllTabs",
                    [
                        "NAME:" + property_tab,
                        ["NAME:PropServers", property_object],
                        ["NAME:ChangedProps", ["NAME:" + property_name, "X:=", xpos, "Y:=", ypos, "Z:=", zpos]],
                    ],
                ]
            )
        elif isinstance(property_value, bool):
            self.oeditor.ChangeProperty(
                [
                    "NAME:AllTabs",
                    [
                        "NAME:" + property_tab,
                        ["NAME:PropServers", property_object],
                        ["NAME:ChangedProps", ["NAME:" + property_name, "Value:=", property_value]],
                    ],
                ]
            )
        elif isinstance(property_value, (float, int)):
            xpos = self._arg_with_dim(property_value, self.model_units)
            self.oeditor.ChangeProperty(
                [
                    "NAME:AllTabs",
                    [
                        "NAME:" + property_tab,
                        ["NAME:PropServers", property_object],
                        ["NAME:ChangedProps", ["NAME:" + property_name, "Value:=", xpos]],
                    ],
                ]
            )
        elif isinstance(property_value, str):
            self.oeditor.ChangeProperty(
                [
                    "NAME:AllTabs",
                    [
                        "NAME:" + property_tab,
                        ["NAME:PropServers", property_object],
                        ["NAME:ChangedProps", ["NAME:" + property_name, "Value:=", property_value]],
                    ],
                ]
            )
        else:
            self.logger.error("Wrong Property Value")
            return False
        self.logger.info("Property {} Changed correctly.".format(property_name))
        return True

    @pyaedt_function_handler()
    def merge_design(self, merged_design=None, pos_x="0.0", pos_y="0.0", pos_z="0.0", rotation="0.0"):
        """Merge a design into another.

        Parameters
        ----------
        merged_design : :class:`pyaedt.hfss3dlayout.Hfss3dLayout`
            Design to merge.
        pos_x : float, str
            X Offset.
        pos_y : float, str
            Y Offset.
        pos_z : float, str
            Z Offset.
        rotation : float, str
            Rotation angle in deg.

        Returns
        -------
        :class:`pyaedt.modeler.Object3d.ComponentsSubCircuit3DLayout`
            Object if successful.
        """
        des_name = merged_design.design_name
        merged_design.oproject.CopyDesign(des_name)
        self._app.odesign.PasteDesign(1)
        comp_name = ""
        for i in range(100, 0, -1):
            try:
                cmp_info = self.oeditor.GetComponentInfo(str(i))
                if cmp_info and des_name in cmp_info[0]:
                    comp_name = str(i)
                    break
            except:
                continue
        if not comp_name:
            return False
        comp = ComponentsSubCircuit3DLayout(self, comp_name)
        self.components_3d[comp_name] = comp
        comp.is_3d_placement = True
        comp.local_origin = [0.0, 0.0, 0.0]
        pos_x = self._arg_with_dim(pos_x)
        pos_y = self._arg_with_dim(pos_y)
        pos_z = self._arg_with_dim(pos_z)
        rotation = self._arg_with_dim(rotation, "deg")
        comp.angle = rotation
        comp.location = [pos_x, pos_y, pos_z]
        return comp

    @pyaedt_function_handler()
    def change_clip_plane_position(self, clip_name, position):
        """Change the clip plane position.

        Parameters
        ----------
        clip_name : str
            Name of the clip plane.
        position : list
            List of ``[x,y,z]`` coordinates for the new position.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.ChangeProperty
        """
        return self.change_property(clip_name, "Location", position)

    @pyaedt_function_handler()
    def colinear_heal(self, selection, tolerance=0.1):
        """Remove small edges of one or more primitives.

        Parameters
        ----------
        selection : str or list
            One or more primitives to heal.
        tolerance :  float, optional
            Tolerance value. The default is ``0.1``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.


        References
        ----------
        >>> oEditor.Heal


        Examples
        --------
        >>> from pyaedt import Hfss3dLayout
        >>> h3d=Hfss3dLayout(specified_version="2021.2")
        >>> h3d.modeler.layers.add_layer("TOP")
        >>> l1=h3d.modeler.create_line("TOP", [[0,0],[100,0]],  0.5, name="poly_1")
        >>> l2=h3d.modeler.create_line("TOP", [[100,0],[120,-35]],  0.5, name="poly_2")
        >>> h3d.modeler.unite([l1,l2])
        >>> h3d.modeler.colinear_heal("poly_2", 0.25)
        True
        """
        if isinstance(selection, str):
            selection = [selection]
        self.oeditor.Heal(
            [
                "NAME:Repair",
                "Selection:=",
                selection,
                "Type:=",
                "Colinear",
                "Tol:=",
                self.number_with_units(tolerance),
            ]
        )

        return True

    @pyaedt_function_handler()
    def expand(self, object_to_expand, size=1, expand_type="ROUND", replace_original=False):
        """Expand the object by a specific size.

        Parameters
        ----------
        object_to_expand : str
            Name of the object.
        size : float, optional
            Size of the expansion. The default is ``1``.
        expand_type : str, optional
            Type of the expansion. Options are ``"ROUND"``, ``"MITER"``, and
            ``"CORNER"``. The default is ``"ROUND"``.
        replace_original : bool, optional
             Whether to replace the original object. The default is ``False``, in which case
             a new object is created.

        Returns
        -------
        str
            Name of the object.

        References
        ----------
        >>> oEditor.Expand


        Examples
        --------
        >>> from pyaedt import Hfss3dLayout
        >>> h3d=Hfss3dLayout(specified_version="2021.2")
        >>> h3d.modeler.layers.add_layer("TOP")
        >>> h3d.modeler.create_rectangle("TOP", [20,20],[50,50], name="rect_1")
        >>> h3d.modeler.create_line("TOP",[[25,25],[40,40]], name="line_3")
        >>> out1 = h3d.modeler.expand("line_3")
        >>> print(out1)
        line_4

        """
        object_to_expand = self.convert_to_selections(object_to_expand)
        self.cleanup_objects()
        layer = self.oeditor.GetPropertyValue("BaseElementTab", object_to_expand, "PlacementLayer")
        poly = self.oeditor.GetPolygonDef(object_to_expand).GetPoints()
        pos = [poly[0].GetX(), poly[0].GetY()]
        geom_names = self.oeditor.FindObjectsByPoint(self.oeditor.Point().Set(pos[0], pos[1]), layer)
        self.oeditor.Expand(
            self.number_with_units(size), expand_type, replace_original, ["NAME:elements", object_to_expand]
        )
        self.cleanup_objects()
        if not replace_original:
            new_geom_names = [
                i
                for i in self.oeditor.FindObjectsByPoint(self.oeditor.Point().Set(pos[0], pos[1]), layer)
                if i not in geom_names
            ]
            return new_geom_names[0]
        return object_to_expand

    @pyaedt_function_handler()
    def import_cadence_brd(self, brd_filename, edb_path=None, edb_name=None):
        """Import a cadence board.

        Parameters
        ----------
        brd_filename : str
            Full path and name of the BRD file to import.
        edb_path : str, optional
            Path where the EDB is to be created. The default is ``None``, in which
            case the project directory is used.
        edb_name : str, optional
            Name of the EDB. The default is ``None``, in which
            case the board name is used.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oImportExport.ImportExtracta
        """
        if not edb_path:
            edb_path = self.projdir
        if not edb_name:
            name = os.path.basename(brd_filename)
            edb_name = os.path.splitext(name)[0]

        self._oimportexport.ImportExtracta(
            brd_filename, os.path.join(edb_path, edb_name + ".aedb"), os.path.join(edb_path, edb_name + ".xml")
        )
        self._app.__init__(self._app._desktop.GetActiveProject().GetName())
        return True

    @pyaedt_function_handler()
    def modeler_variable(self, value):
        """Retrieve a modeler variable.

        Parameters
        ----------
        value :

        Returns
        -------

        """
        if isinstance(value, str):
            return value
        else:
            return str(value) + self.model_units

    @pyaedt_function_handler()
    def import_ipc2581(self, ipc_filename, edb_path=None, edb_name=None):
        """Import an IPC file.

        Parameters
        ----------
        ipc_filename : str
            Full path and name of the IPC file.
        edb_path : str, optional
            Path where the EDB is to be created. The default is ``None``, in which
            case the project directory is used.
        edb_name : str, optional
            Name of the EDB. The default is ``None``, in which
            case the board name is used.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oImportExport.ImportIPC
        """
        if not edb_path:
            edb_path = self.projdir
        if not edb_name:
            name = os.path.basename(ipc_filename)
            edb_name = os.path.splitext(name)[0]

        self._oimportexport.ImportIPC(
            ipc_filename, os.path.join(edb_path, edb_name + ".aedb"), os.path.join(edb_path, edb_name + ".xml")
        )
        self._app.__init__(self._app._desktop.GetActiveProject().GetName())
        return True

    @pyaedt_function_handler()
    def subtract(self, blank, tool):
        """Subtract objects from one or more names.

        Parameters
        ----------
        blank : str
            Name of the geometry to subtract from.
        tool : str or list
            One or more names of the geometries to subtract.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.Subtract
        """
        blank = self.convert_to_selections(blank)
        tool = self.convert_to_selections(tool, True)
        vArg1 = ["NAME:primitives", blank]
        self.cleanup_objects()
        for el in tool:
            vArg1.append(el)

        if self.oeditor is not None:
            self.oeditor.Subtract(vArg1)
        return self.cleanup_objects()

    @pyaedt_function_handler()
    def convert_to_selections(self, objects_to_split, return_list=False):
        """Convert one or more object to selections.

        Parameters
        ----------
        objects_to_split : str, int, list
            One or more objects to convert to selections. A list can contain
            both strings (object names) and integers (object IDs).
        return_list : bool, option
            Whether to return a list of the selections. The default is
            ``False``, in which case a string of the selections is returned.
            If ``True``, a list of the selections is returned.

        Returns
        -------
        str or list
           String or list of the selections.

        """
        if not isinstance(objects_to_split, list):
            objects_to_split = [objects_to_split]
        objnames = []
        for el in objects_to_split:
            if isinstance(el, str):
                objnames.append(el)
            elif "name" in dir(el):
                objnames.append(el.name)
            else:
                pass
        if return_list:
            return objnames
        else:
            return ",".join(objnames)

    @pyaedt_function_handler()
    def unite(self, objectlists):
        """Unite objects from names.

        Parameters
        ----------
        objectlists : list
            List of objects to unite.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.Unite
        """
        vArg1 = ["NAME:primitives"]
        if len(objectlists) >= 2:
            objectlists = self.convert_to_selections(objectlists, True)
            self.cleanup_objects()

            for el in objectlists:
                vArg1.append(el)
            self.oeditor.Unite(vArg1)
            return self.cleanup_objects()
        else:
            self.logger.error("Input list must contain at least two elements.")
            return False

    @pyaedt_function_handler()
    def intersect(self, objectlists):
        """Intersect objects from names.

        Parameters
        ----------
        objectlists : list
            List of objects to intersect.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.Intersect
        """
        vArg1 = ["NAME:primitives"]
        if len(objectlists) >= 2:
            objectlists = self.convert_to_selections(objectlists, True)
            self.cleanup_objects()

            for el in objectlists:
                vArg1.append(el)
            self.oeditor.Intersect(vArg1)
            return self.cleanup_objects()
        else:
            self.logger.error("Input list must contain at least two elements.")
            return False

    @pyaedt_function_handler()
    def duplicate(self, objectlists, count, direction_vector):
        """Duplicate one or more elements along a vector.

        Parameters
        ----------
        objectlists : list
            List of elements to duplicate.
        count : int

        direction_vector : list
            List of ``[x,y]`` coordinates for the direction vector.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.Duplicate
        """
        objectlists = self.convert_to_selections(objectlists, True)

        self.cleanup_objects()
        if isinstance(objectlists, str):
            objectlists = [objectlists]
        self.oeditor.Duplicate(
            ["NAME:options", "count:=", count], ["NAME:elements", ",".join(objectlists)], direction_vector
        )
        return self.cleanup_objects()

    @pyaedt_function_handler()
    def duplicate_across_layers(self, objects, layers):
        """Duplicate one or more elements along a vector.

        Parameters
        ----------
        objects : list
            List of elements to duplicate.
        layers : str, list
            Layer name on which duplicate object.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.DuplicateAcrossLyrs
        """
        objects = self.convert_to_selections(objects, True)
        self.cleanup_objects()

        if isinstance(layers, str):
            layers = [layers]
        varg1 = ["NAME:elements"] + objects
        varg2 = ["NAME:layers"] + layers

        self.oeditor.DuplicateAcrossLyrs(varg1, varg2)
        return self.cleanup_objects()

    @pyaedt_function_handler()
    def set_temperature_dependence(
        self,
        include_temperature_dependence=True,
        enable_feedback=True,
        ambient_temp=22,
        create_project_var=False,
    ):
        """Set the temperature dependence for the design.

        Parameters
        ----------
        include_temperature_dependence : bool, optional
            Whether to include the temperature setting for the design. The default is ``True``.
        enable_feedback : bool, optional
            Whether to enable feedback. The default is ``True``.
        ambient_temp : float, optional
            Ambient temperature. The default is ``22``.
        create_project_var : bool, optional
            Whether to create a project variable for the ambient temperature.
            The default is ``False``. If ``True,`` ``$AmbientTemp`` is created.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDesign.SetTemperatureSettings
        """
        self.logger.info("Set the temperature dependence for the design.")
        if create_project_var:
            self._app.variable_manager["$AmbientTemp"] = str(ambient_temp) + "cel"
            var = "$AmbientTemp"
        else:
            var = str(ambient_temp) + "cel"
        vargs1 = [
            "NAME:TemperatureSettings",
            "IncludeTempDependence:=",
            include_temperature_dependence,
            "EnableFeedback:=",
            enable_feedback,
            "Temperature:=",
            var,
        ]
        try:
            self._odesign.SetTemperatureSettings(vargs1)
        except:
            self.logger.error("Failed to enable the temperature dependence.")
            return False
        else:
            self.logger.info("Assigned Objects Temperature")
            return True

    @pyaedt_function_handler()
    def set_spice_model(self, component_name, model_path, model_name=None, subcircuit_name=None, pin_map=None):
        """Assign a Spice model to a component.

        Parameters
        ----------
        component_name : str
            Name of the component.
        model_path : str, optional
            Full path to the model file. The default is ``None``.
        model_name : str, optional
            Name of the model. The default is ``None``, in which case the model name is the file name without an
            extension.
        subcircuit_name : str, optional
            Name of the subcircuit. The default is ``None``, in which case the subcircuit name is the model name.
        pin_map : list, optional
            List of ``[spice_pin_name, aedt_pin_name]`` to customize the pin mapping between Spice pins and
            AEDT pins.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------
        >>> from pyaedt import Hfss3dLayout
        >>> h3d = Hfss3dLayout("myproject")
        >>> h3d.modeler.set_spice_model(component_name="A1",
        ...                             modelpath="pathtospfile",
        ...                             modelname="spicemodelname",
        ...                             subcircuit_name="SUBCK1")

        """
        if not model_name:
            model_name = get_filename_without_extension(model_path)
        if model_name not in list(self.o_model_manager.GetNames()):
            args = [
                "NAME:" + model_name,
                "Name:=",
                model_name,
                "ModTime:=",
                1643711258,
                "Library:=",
                "",
                "LibLocation:=",
                "Project",
                "ModelType:=",
                "dcirspice",
                "Description:=",
                "",
                "ImageFile:=",
                "",
                "SymbolPinConfiguration:=",
                0,
                ["NAME:PortInfoBlk"],
                ["NAME:PortOrderBlk"],
                "filename:=",
                model_path,
                "modelname:=",
                model_name,
            ]
            self.o_model_manager.Add(args)
        if not subcircuit_name:
            subcircuit_name = model_name
        with open_file(model_path, "r") as f:
            for line in f:
                if "subckt" in line.lower():
                    pinNames = [i.strip() for i in re.split(" |\t", line) if i]
                    pinNames.remove(pinNames[0])
                    pinNames.remove(pinNames[0])
                    break
        componentPins = self.components[component_name].pins
        componentPins.reverse()
        if not pin_map:
            pin_map = []
            i = 0
            if len(componentPins) >= len(pinNames):
                for pn in pinNames:
                    pin_map.append(pn + ":=")
                    pin_map.append(componentPins[i])
                    i += 1
        args2 = [
            "CompPropEnabled:=",
            True,
            "Pid:=",
            -1,
            "Pmo:=",
            "0",
            "CompPropType:=",
            0,
            "PinPairRLC:=",
            [
                "RLCModelType:=",
                4,
                "SPICE_file_path:=",
                model_path,
                "SPICE_model_name:=",
                model_name,
                "SPICE_subckt:=",
                subcircuit_name,
                "terminal_pin_map:=",
                pin_map,
            ],
        ]
        args = ["NAME:ModelChanges", ["NAME:UpdateModel0", ["NAME:ComponentNames", component_name], "Prop:=", args2]]
        self.oeditor.UpdateModels(args)
        self.logger.info("Spice Model Correctly assigned to {}.".format(component_name))
        return True

    @pyaedt_function_handler()
    def clip_plane(self):
        """Create a clip plane in the layout.

        .. note::
            This method works only in AEDT 2022 R2 and later.

        Returns
        -------
        str
            Name of newly created clip plane.
        """
        names = self.clip_planes[::]
        new_name = generate_unique_name("VCP", n=3)
        self.oeditor.ClipPlane(new_name)
        new_cp = [i for i in self.clip_planes if i not in names]
        return new_cp[0]

    @property
    def clip_planes(self):
        """All available clip planes. To be considered a clip plane, the name must follow this
        naming convention: "VCP_xxx".

        Returns
        -------
        list
        """
        return [i for i in self.oeditor.FindObjects("Name", "VCP*")]

    @pyaedt_function_handler()
    def geometry_check_and_fix_all(
        self,
        min_area=2e-6,
    ):
        """Run Geometry Check.

        All checks are used and all auto fix options are enabled.

        min_area : float, optional
            CutOuts that are smaller than this minimum area will be ignored during validation checks.
            The default is ``2e-6``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        try:
            self.oeditor.GeometryCheckAndAutofix(
                [
                    "NAME:checks",
                    "Self-Intersecting Polygons",
                    "Disjoint Nets (Floating Nodes)",
                    "DC-Short Errors",
                    "Identical/Overlapping Vias",
                    "Misaligments",
                ],
                "minimum_area_meters_squared:=",
                min_area,
                [
                    "NAME:fixes",
                    "Self-Intersecting Polygons",
                    "Disjoint Nets",
                    "Identical/Overlapping Vias",
                    "Traces-Inside-Traces Errors",
                    "Misalignments (Planes/Traces/Vias)",
                ],
            )
            self.logger.info("Geometry check succeed")
            return True
        except:
            self.logger.error("Geometry check Failed.")
            return False
