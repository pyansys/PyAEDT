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

import os
import re
from warnings import warn

from ansys.aedt.core.generic.general_methods import generate_unique_name
from ansys.aedt.core.generic.general_methods import get_filename_without_extension
from ansys.aedt.core.generic.general_methods import inside_desktop
from ansys.aedt.core.generic.general_methods import open_file
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.generic.settings import settings
from ansys.aedt.core.modeler.cad.modeler import Modeler
from ansys.aedt.core.modeler.pcb.object_3d_layout import ComponentsSubCircuit3DLayout
from ansys.aedt.core.modeler.pcb.primitives_3d_layout import Primitives3DLayout
from ansys.aedt.core.modules.layer_stackup import Layers


class Modeler3DLayout(Modeler, Primitives3DLayout):
    """Manages Modeler 3D layouts.

    This class is inherited in the caller application and is accessible through the modeler variable
    object (for example, ``hfss3dlayout.modeler``).

    Parameters
    ----------
    app : :class:`ansys.aedt.core.application.analysis_3d_layout.FieldAnalysis3DLayout`
            Inherited parent object.

    Examples
    --------
    >>> from ansys.aedt.core import Hfss3dLayout
    >>> hfss = Hfss3dLayout()
    >>> my_modeler = hfss.modeler
    """

    def __init__(self, app):
        self._app = app
        self._edb = None
        self.logger.info("Loading Modeler.")
        self._model_units = None
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
        :class:`ansys.aedt.core.modules.layer_stackup.Layers`
        """
        return self.layers

    @property
    def oeditor(self):
        """Oeditor Module.

        References
        ----------
        >>> oEditor = oDesign.SetActiveEditor("Layout")"""
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
        """EBD. Supported only in IronPython.

        Returns
        -------
        :class:`ansys.aedt.core.edb.Edb`
             EDB.

        """
        if settings.remote_api or settings.remote_rpc_session:
            return self._edb
        if not self._edb:
            from pyedb import Edb

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
        except Exception:
            self._desktop.RestoreWindow()

    @property
    def model_units(self):
        """Model units as a string (for example, "mm").

        References
        ----------
        >>> oEditor.GetActiveUnits
        >>> oEditor.SetActiveUnits
        """
        return self._app.units.length

    @model_units.setter
    def model_units(self, units):
        self._app.units.length = units

    @property
    def primitives(self):
        """Primitives.

        .. deprecated:: 0.4.15
            There is no need to use the ``primitives`` property anymore. You can instantiate
            methods for primitives directly from the modeler.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.primitives_3d_layout.Primitives3DLayout`

        """
        mess = "`primitives` is deprecated.\n"
        mess += " Use `app.modeler` directly to instantiate primitives methods."
        warn(mess, DeprecationWarning)
        return self._primitives

    @pyaedt_function_handler(object_name="assignment")
    def obounding_box(self, assignment):
        """Bounding box of a specified object.

        Returns
        -------
        list
            List of [LLx, LLy, URx, URy] coordinates.

        References
        ----------
        >>> oEditor.GetBBox
        """
        bb = self.oeditor.GetBBox(assignment)
        pll = bb.BBoxLL()
        pur = bb.BBoxUR()
        return [pll.GetX(), pll.GetY(), pur.GetX(), pur.GetY()]

    @pyaedt_function_handler()
    def _arg_with_dim(self, value, units=None):
        if units is None:
            units = self.model_units
        if isinstance(value, str):
            try:
                float(value)
                val = f"{value}{units}"
            except Exception:
                val = value
        else:
            val = f"{value}{units}"
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

    @pyaedt_function_handler(
        property_object="assignment", property_name="name", property_value="value", property_tab="aedt_tab"
    )
    def change_property(self, assignment, name, value, aedt_tab="BaseElementTab"):
        """Change an oeditor property.

        Parameters
        ----------
        assignment : str
            Name of the property object. It can be the name of an excitation or field reporter.
            For example, ``Excitations:Port1`` or ``FieldsReporter:Mag_H``.
        name : str
            Name of the property. For example, ``Rotation Angle``.
        value : str, list
            Value of the property. It is a string for a single value and a list of three elements for
            ``[x,y,z]`` coordianates.
        aedt_tab : str
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
        if isinstance(value, list) and len(value) == 3:
            xpos, ypos, zpos = self._pos_with_arg(value)
            self.oeditor.ChangeProperty(
                [
                    "NAME:AllTabs",
                    [
                        "NAME:" + aedt_tab,
                        ["NAME:PropServers", assignment],
                        ["NAME:ChangedProps", ["NAME:" + name, "X:=", xpos, "Y:=", ypos, "Z:=", zpos]],
                    ],
                ]
            )
        elif isinstance(value, bool):
            self.oeditor.ChangeProperty(
                [
                    "NAME:AllTabs",
                    [
                        "NAME:" + aedt_tab,
                        ["NAME:PropServers", assignment],
                        ["NAME:ChangedProps", ["NAME:" + name, "Value:=", value]],
                    ],
                ]
            )
        elif isinstance(value, (float, int)):
            xpos = self._arg_with_dim(value, self.model_units)
            self.oeditor.ChangeProperty(
                [
                    "NAME:AllTabs",
                    [
                        "NAME:" + aedt_tab,
                        ["NAME:PropServers", assignment],
                        ["NAME:ChangedProps", ["NAME:" + name, "Value:=", xpos]],
                    ],
                ]
            )
        elif isinstance(value, str):
            self.oeditor.ChangeProperty(
                [
                    "NAME:AllTabs",
                    [
                        "NAME:" + aedt_tab,
                        ["NAME:PropServers", assignment],
                        ["NAME:ChangedProps", ["NAME:" + name, "Value:=", value]],
                    ],
                ]
            )
        else:
            self.logger.error("Wrong Property Value")
            return False
        self.logger.info(f"Property {name} Changed correctly.")
        return True

    @pyaedt_function_handler(pos_x="x", pos_y="y", pos_z="z")
    def merge_design(self, merged_design=None, x="0.0", y="0.0", z="0.0", rotation="0.0"):
        """Merge a design into another.

        Parameters
        ----------
        merged_design : :class:`ansys.aedt.core.hfss3dlayout.Hfss3dLayout`
            Design to merge.
        x : float, str
            X Offset.
        y : float, str
            Y Offset.
        z : float, str
            Z Offset.
        rotation : float, str
            Rotation angle in deg.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.Object3d.ComponentsSubCircuit3DLayout`
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
            except Exception:
                self.logger.debug(f"Couldn't get component name from component {i}")
        if not comp_name:
            return False
        comp = ComponentsSubCircuit3DLayout(self, comp_name)
        self.components_3d[comp_name] = comp
        comp.is_3d_placement = True
        comp.local_origin = [0.0, 0.0, 0.0]
        x = self._arg_with_dim(x)
        y = self._arg_with_dim(y)
        z = self._arg_with_dim(z)
        rotation = self._arg_with_dim(rotation, "deg")
        comp.angle = rotation
        comp.location = [x, y, z]
        return comp

    @pyaedt_function_handler(clip_name="name", position="location")
    def change_clip_plane_position(self, name, location):
        """Change the clip plane position.

        Parameters
        ----------
        name : str
            Name of the clip plane.
        location : list
            List of ``[x,y,z]`` coordinates for the new position.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.ChangeProperty
        """
        return self.change_property(name, "Location", location)

    @pyaedt_function_handler(selection="assignment")
    def colinear_heal(self, assignment, tolerance=0.1):
        """Remove small edges of one or more primitives.

        Parameters
        ----------
        assignment : str or list
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
        >>> from ansys.aedt.core import Hfss3dLayout
        >>> h3d=Hfss3dLayout(version="2021.2")
        >>> h3d.modeler.layers.add_layer("TOP")
        >>> l1=h3d.modeler.create_line("TOP",[[0,0],[100,0]],0.5)
        >>> l2=h3d.modeler.create_line("TOP",[[100,0],[120,-35]],0.5)
        >>> h3d.modeler.unite([l1,l2])
        >>> h3d.modeler.colinear_heal("poly_2",0.25)
        True
        """
        if isinstance(assignment, str):
            assignment = [assignment]
        self.oeditor.Heal(
            [
                "NAME:Repair",
                "Selection:=",
                assignment,
                "Type:=",
                "Colinear",
                "Tol:=",
                self.number_with_units(tolerance),
            ]
        )

        return True

    @pyaedt_function_handler(object_to_expand="assignment")
    def expand(self, assignment, size=1, expand_type="ROUND", replace_original=False):
        """Expand the object by a specific size.

        Parameters
        ----------
        assignment : str
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
        >>> from ansys.aedt.core import Hfss3dLayout
        >>> h3d=Hfss3dLayout(version="2021.2")
        >>> h3d.modeler.layers.add_layer("TOP")
        >>> h3d.modeler.create_rectangle("TOP", [20,20],[50,50], name="rect_1")
        >>> h3d.modeler.create_line("TOP",[[25,25],[40,40]])
        >>> out1 = h3d.modeler.expand("line_3")
        >>> print(out1)
        line_4

        """
        assignment = self.convert_to_selections(assignment)
        self.cleanup_objects()
        layer = self.oeditor.GetPropertyValue("BaseElementTab", assignment, "PlacementLayer")
        poly = self.oeditor.GetPolygonDef(assignment).GetPoints()
        pos = [poly[0].GetX(), poly[0].GetY()]
        geom_names = self.oeditor.FindObjectsByPoint(self.oeditor.Point().Set(pos[0], pos[1]), layer)
        self.oeditor.Expand(self.number_with_units(size), expand_type, replace_original, ["NAME:elements", assignment])
        self.cleanup_objects()
        if not replace_original:
            new_geom_names = [
                i
                for i in self.oeditor.FindObjectsByPoint(self.oeditor.Point().Set(pos[0], pos[1]), layer)
                if i not in geom_names
            ]
            return new_geom_names[0]
        return assignment

    @pyaedt_function_handler(brd_filename="input_file", edb_path="output_dir", edb_name="name")
    def import_cadence_brd(self, input_file, output_dir=None, name=None):
        """Import a cadence board.

        Parameters
        ----------
        input_file : str
            Full path and name of the BRD file to import.
        output_dir : str, optional
            Path where the EDB is to be created. The default is ``None``, in which
            case the project directory is used.
        name : str, optional
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
        if not output_dir:
            output_dir = self.projdir
        if not name:
            name = os.path.basename(input_file)
            name = os.path.splitext(name)[0]

        self._oimportexport.ImportExtracta(
            input_file, os.path.join(output_dir, name + ".aedb"), os.path.join(output_dir, name + ".xml")
        )
        self._app.__init__(self._app.desktop_class.active_project().GetName())
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

    @pyaedt_function_handler(ipc_filename="input_file", edb_path="output_dir", edb_name="name")
    def import_ipc2581(self, input_file, output_dir=None, name=None):
        """Import an IPC file.

        Parameters
        ----------
        input_file : str
            Full path and name of the IPC file.
        output_dir : str, optional
            Path where the EDB is to be created. The default is ``None``, in which
            case the project directory is used.
        name : str, optional
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
        if not output_dir:
            output_dir = self.projdir
        if not name:
            name = os.path.basename(input_file)
            name = os.path.splitext(name)[0]

        self._oimportexport.ImportIPC(
            input_file, os.path.join(output_dir, name + ".aedb"), os.path.join(output_dir, name + ".xml")
        )
        self._app.__init__(self._app.desktop_class.active_project().GetName())
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

    @pyaedt_function_handler(objects_to_split="assignment")
    def convert_to_selections(self, assignment, return_list=False):
        """Convert one or more object to selections.

        Parameters
        ----------
        assignment : str, int, list
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

        if not isinstance(assignment, list):
            assignment = [assignment]
        objnames = []
        for el in assignment:
            if isinstance(el, str):
                objnames.append(el)
            elif "name" in dir(el):
                objnames.append(el.name)
        if return_list:
            return objnames
        else:
            return ",".join(objnames)

    @pyaedt_function_handler(objectlists="assignment")
    def unite(self, assignment):
        """Unite objects from names.

        Parameters
        ----------
        assignment : list
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
        if len(assignment) >= 2:
            assignment = self.convert_to_selections(assignment, True)
            self.cleanup_objects()

            for el in assignment:
                vArg1.append(el)
            self.oeditor.Unite(vArg1)
            return self.cleanup_objects()
        else:
            self.logger.error("Input list must contain at least two elements.")
            return False

    @pyaedt_function_handler(objectlists="assignment")
    def intersect(self, assignment):
        """Intersect objects from names.

        Parameters
        ----------
        assignment : list
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
        if len(assignment) >= 2:
            assignment = self.convert_to_selections(assignment, True)
            self.cleanup_objects()

            for el in assignment:
                vArg1.append(el)
            self.oeditor.Intersect(vArg1)
            return self.cleanup_objects()
        else:
            self.logger.error("Input list must contain at least two elements.")
            return False

    @pyaedt_function_handler(objectlists="assignment", direction_vector="vector")
    def duplicate(self, assignment, count, vector):
        """Duplicate one or more elements along a vector.

        Parameters
        ----------
        assignment : list
            List of elements to duplicate.
        count : int
            Number of clones.
        vector : list
            List of ``[x,y]`` coordinates for the direction vector.

        Returns
        -------
        tuple
            List of added objects, List of removed names.

        References
        ----------
        >>> oEditor.Duplicate
        """
        assignment = self.convert_to_selections(assignment, True)

        self.cleanup_objects()
        self.oeditor.Duplicate(["NAME:options", "count:=", count], ["NAME:elements"] + assignment, vector)
        return self.cleanup_objects()

    @pyaedt_function_handler(objects="assignment")
    def duplicate_across_layers(self, assignment, layers):
        """Duplicate one or more elements along a vector.

        Parameters
        ----------
        assignment : list
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
        assignment = self.convert_to_selections(assignment, True)
        self.cleanup_objects()

        if isinstance(layers, str):
            layers = [layers]
        varg1 = ["NAME:elements"] + assignment
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
        except Exception:
            self.logger.error("Failed to enable the temperature dependence.")
            return False
        else:
            self.logger.info("Assigned Objects Temperature")
            return True

    @pyaedt_function_handler(component_name="assignment", model_path="input_file")
    def set_spice_model(self, assignment, input_file, model_name=None, subcircuit_name=None, pin_map=None):
        """Assign a Spice model to a component.

        Parameters
        ----------
        assignment : str
            Name of the component.
        input_file : str, optional
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

        >>> from ansys.aedt.core import Hfss3dLayout
        >>> h3d = Hfss3dLayout("myproject")
        >>> h3d.modeler.set_spice_model(assignment="A1",input_file=,subcircuit_name="SUBCK1")

        """
        if not model_name:
            model_name = get_filename_without_extension(input_file)
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
                input_file,
                "modelname:=",
                model_name,
            ]
            self.o_model_manager.Add(args)
        if not subcircuit_name:
            subcircuit_name = model_name
        with open_file(input_file, "r") as f:
            for line in f:
                if "subckt" in line.lower():
                    pinNames = [i.strip() for i in re.split(" |\t", line) if i]
                    pinNames.remove(pinNames[0])
                    pinNames.remove(pinNames[0])
                    break
        componentPins = list(self.components[assignment].pins.keys())
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
                input_file,
                "SPICE_model_name:=",
                model_name,
                "SPICE_subckt:=",
                subcircuit_name,
                "terminal_pin_map:=",
                pin_map,
            ],
        ]
        args = ["NAME:ModelChanges", ["NAME:UpdateModel0", ["NAME:ComponentNames", assignment], "Prop:=", args2]]
        self.oeditor.UpdateModels(args)
        self.logger.info(f"Spice Model Correctly assigned to {assignment}.")
        return True

    @pyaedt_function_handler()
    def set_touchstone_model(self, assignment, input_file, model_name=None):
        """Assign a Touchstone model to a component.

        Parameters
        ----------
        assignment : str
            Name of the component.
        input_file : str, optional
            Full path to the model file. The default is ``None``.
        model_name : str, optional
            Name of the model. The default is ``None``, in which case the model name is the file name without an
            extension.


        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------

        >>> from ansys.aedt.core import Hfss3dLayout
        >>> h3d = Hfss3dLayout("myproject")
        >>> h3d.modeler.set_touchstone_model(assignment="C1",input_file="comp.s2p")

        """

        if not model_name:
            model_name = os.path.splitext(os.path.basename(input_file))[0]
            if "." in model_name:
                model_name = model_name.replace(".", "_")
        if model_name in list(self.o_model_manager.GetNames()):
            model_name = generate_unique_name(model_name, n=2)
        num_terminal = int(os.path.splitext(input_file)[1].lower().strip(".sp"))

        port_names = []
        with open_file(input_file, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith(("!", "#", "")):
                    if "Port" in line and "=" in line and "Impedance" not in line:
                        port_names.append(line.split("=")[-1].strip().replace(" ", "_").strip("[]"))
                else:
                    break
        image_subcircuit_path = ""
        bmp_file_name = ""

        if not port_names:
            port_names = ["Port" + str(i + 1) for i in range(num_terminal)]
        arg = [
            "NAME:" + model_name,
            "Name:=",
            model_name,
            "ModTime:=",
            0,
            "Library:=",
            "",
            "LibLocation:=",
            "Project",
            "ModelType:=",
            "nport",
            "Description:=",
            "",
            "ImageFile:=",
            image_subcircuit_path,
            "SymbolPinConfiguration:=",
            0,
            ["NAME:PortInfoBlk"],
            ["NAME:PortOrderBlk"],
            "filename:=",
            input_file,
            "numberofports:=",
            num_terminal,
            "sssfilename:=",
            "",
            "sssmodel:=",
            False,
            "PortNames:=",
            port_names,
            "domain:=",
            "frequency",
            "datamode:=",
            "Link",
            "devicename:=",
            "",
            "SolutionName:=",
            "",
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
        self.o_model_manager.Add(arg)
        arg = [
            "NAME:" + model_name,
            "Info:=",
            [
                "Type:=",
                10,
                "NumTerminals:=",
                num_terminal,
                "DataSource:=",
                "",
                "ModifiedOn:=",
                1618569625,
                "Manufacturer:=",
                "",
                "Symbol:=",
                "",
                "ModelNames:=",
                "",
                "Footprint:=",
                "",
                "Description:=",
                "",
                "InfoTopic:=",
                "",
                "InfoHelpFile:=",
                "",
                "IconFile:=",
                bmp_file_name,
                "Library:=",
                "",
                "OriginalLocation:=",
                "Project",
                "IEEE:=",
                "",
                "Author:=",
                "",
                "OriginalAuthor:=",
                "",
                "CreationDate:=",
                1618569625,
                "ExampleFile:=",
                "",
                "HiddenComponent:=",
                0,
                "CircuitEnv:=",
                0,
                "GroupID:=",
                0,
            ],
            "CircuitEnv:=",
            0,
            "Refbase:=",
            "S",
            "NumParts:=",
            1,
            "ModSinceLib:=",
            False,
        ]
        for i in range(num_terminal):
            arg.append("Terminal:=")
            arg.append([port_names[i], port_names[i], "A", False, i, 1, "", "Electrical", "0"])
        arg.append("CompExtID:=")
        arg.append(5)
        arg.append(
            [
                "NAME:Parameters",
                "MenuProp:=",
                ["CoSimulator", "SD", "", "Default", 0],
                "ButtonProp:=",
                ["CosimDefinition", "SD", "", "Edit", "Edit", 40501, "ButtonPropClientData:=", []],
            ]
        )
        arg.append(
            [
                "NAME:CosimDefinitions",
                [
                    "NAME:CosimDefinition",
                    "CosimulatorType:=",
                    102,
                    "CosimDefName:=",
                    "Default",
                    "IsDefinition:=",
                    True,
                    "Connect:=",
                    True,
                    "ModelDefinitionName:=",
                    model_name,
                    "ShowRefPin2:=",
                    2,
                    "LenPropName:=",
                    "",
                ],
                "DefaultCosim:=",
                "Default",
            ]
        )

        self.o_component_manager.Add(arg)
        self.o_component_manager.AddSolverOnDemandModel(
            self.components[assignment].part,
            [
                "NAME:CosimDefinition",
                "CosimulatorType:=",
                102,
                "CosimDefName:=",
                model_name,
                "IsDefinition:=",
                True,
                "Connect:=",
                True,
                "ModelDefinitionName:=",
                model_name,
                "ShowRefPin2:=",
                2,
                "LenPropName:=",
                "",
            ],
        )
        self.oeditor.ChangeProperty(
            [
                "NAME:AllTabs",
                [
                    "NAME:BaseElementTab",
                    ["NAME:PropServers", assignment],
                    [
                        "NAME:ChangedProps",
                        [
                            "NAME:Model Info",
                            [
                                "NAME:Model",
                                "RLCProp:=",
                                [
                                    "CompPropEnabled:=",
                                    True,
                                    "Pid:=",
                                    -1,
                                    "Pmo:=",
                                    "0",
                                    "CompPropType:=",
                                    0,
                                    "PinPairRLC:=",
                                    ["RLCModelType:=", 1, "CosimDefintion:=", model_name],
                                ],
                                "CompType:=",
                                3,
                            ],
                        ],
                    ],
                ],
            ]
        )

        return model_name

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
        except Exception:
            self.logger.error("Geometry check Failed.")
            return False
