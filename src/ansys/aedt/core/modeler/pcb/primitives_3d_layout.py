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

# import sys
import warnings

from ansys.aedt.core.generic.general_methods import _uname
from ansys.aedt.core.generic.general_methods import generate_unique_name
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.modeler.cad.primitives import default_materials
from ansys.aedt.core.modeler.geometry_operators import GeometryOperators
from ansys.aedt.core.modeler.pcb.object_3d_layout import Circle3dLayout
from ansys.aedt.core.modeler.pcb.object_3d_layout import Components3DLayout
from ansys.aedt.core.modeler.pcb.object_3d_layout import ComponentsSubCircuit3DLayout
from ansys.aedt.core.modeler.pcb.object_3d_layout import Line3dLayout
from ansys.aedt.core.modeler.pcb.object_3d_layout import Nets3DLayout
from ansys.aedt.core.modeler.pcb.object_3d_layout import Padstack
from ansys.aedt.core.modeler.pcb.object_3d_layout import Pins3DLayout
from ansys.aedt.core.modeler.pcb.object_3d_layout import Polygons3DLayout
from ansys.aedt.core.modeler.pcb.object_3d_layout import Rect3dLayout


class Primitives3DLayout(object):
    """Manages primitives in HFSS 3D Layout.

    This class is inherited in the caller application and is accessible through the primitives variable part
    of modeler object( eg. ``hfss3dlayout.modeler``).

    Parameters
    ----------
    modeler : :class:`ansys.aedt.core.modeler.modeler_pcb.Modeler3DLayout`
        Name of the modeler.

    Examples
    --------
    Basic usage demonstrated with an HFSS 3D Layout design:

    >>> from ansys.aedt.core import Hfss3dLayout
    >>> aedtapp = Hfss3dLayout()
    >>> prim = aedtapp.modeler
    """

    @pyaedt_function_handler()
    def __getitem__(self, partname):
        """Retrieve a part.

        Parameters
        ----------
        partname : int or str
           Part ID or part name.

        Returns
        -------
        type
          Part object details.

        """
        if partname in self.geometries:
            return self.geometries[partname]
        if partname in self.vias:
            return self.vias[partname]
        if partname in self.nets:
            return self.nets[partname]
        if not isinstance(partname, (str, int, float, list, tuple)):
            return partname
        return None

    def __init__(self, app):
        # self.is_outside_desktop = sys.modules["__main__"].isoutsideDesktop
        self._app = app
        self._padstacks = {}
        self._components3d = {}
        self._init_prims()

    @pyaedt_function_handler()
    def _init_prims(self):
        self._components = {}
        self._rectangles = {}
        self._lines = {}
        self._circles = {}
        self._polygons = {}
        self._rectangles_voids = {}
        self._lines_voids = {}
        self._circles_voids = {}
        self._polygons_voids = {}
        self._pins = {}
        self._nets = {}
        self._power_nets = {}
        self._signal_nets = {}
        self._no_nets = {}
        self._vias = {}

    @property
    def _modeler(self):
        return self._app.modeler

    @property
    def opadstackmanager(self):
        """Aedt oPadstackManager.

        References
        ----------
        >>> oPadstackManger = oDefinitionManager.GetManager("Padstack")
        """
        return self._app.opadstackmanager

    @property
    def components(self):
        """Components.

        Returns
        -------
        dict[str, :class:`ansys.aedt.core.modeler.cad.object_3dlayout.Components3DLayout`]
            Components objects.

        """
        if self._components:
            return self._components
        objs = self.modeler.oeditor.FindObjects("Type", "component")
        for obj in objs:
            self._components[obj] = Components3DLayout(self, obj)
        return self._components

    @property
    def geometries(self):
        """All Geometries including voids.

        Returns
        -------
        dict
            Dictionary of geometries.

        """
        geom = {}
        for k, v in self.polygons.items():
            geom[k] = v
        for k, v in self.rectangles.items():
            geom[k] = v
        for k, v in self.lines.items():
            geom[k] = v
        for k, v in self.circles.items():
            geom[k] = v
        for k, v in self.voids.items():
            geom[k] = v
        return geom

    @property
    def voids(self):
        """All voids.

        Returns
        -------
        dict
            Dictionary of voids.

        """
        geom = {}
        for k, v in self.polygons_voids.items():
            geom[k] = v
        for k, v in self.rectangles_voids.items():
            geom[k] = v
        for k, v in self.lines_voids.items():
            geom[k] = v
        for k, v in self.circles_voids.items():
            geom[k] = v
        return geom

    @pyaedt_function_handler(layer_name="layer", object_filter="filter")
    def objects_by_layer(self, layer, object_filter=None, include_voids=False):
        """Retrieve the list of objects that belongs to a specific layer.

        Parameters
        ----------
        layer : str
            Name of the layer to filter.
        object_filter : str, list, optional
            Name of the category to include in search. Options are `"poly"`, `"circle"`,
            `"rect"`,`"line"`,`"arc"`, `"via"`,`"pin"` and `"component"`.
        include_voids : bool, optional
            Either if include or not the voids in search.

        Returns
        -------
        list
            Objects found.
        """

        objs = []
        if object_filter:
            if isinstance(object_filter, str):
                object_filter = [object_filter]

            for poly in object_filter:
                objs = self.modeler.oeditor.FilterObjectList(
                    "Type", poly, self.modeler.oeditor.FindObjects("Layer", layer)
                )
                if include_voids:
                    objs = self.modeler.oeditor.FilterObjectList(
                        "Type", poly + " void", self.modeler.oeditor.FindObjects("Layer", layer)
                    )

        else:
            objs = self.modeler.oeditor.FindObjects("Layer", layer)
        return objs

    @pyaedt_function_handler(net_name="net")
    def objects_by_net(self, net, object_filter=None, include_voids=False):
        """Retrieve the list of objects that belongs to a specific net.

        Parameters
        ----------
        net : str
            Name of the net to filter.
        object_filter : str, list, optional
            Name of the category to include in search. Options are `"poly"`, `"circle"`,
            `"rect"`,`"line"`,`"arc"`, `"via"`,`"pin"` and `"component"`.
        include_voids : bool, optional
            Either if include or not the voids in search.

        Returns
        -------
        list
            Objects found.
        """
        objs = []
        if object_filter:
            if isinstance(object_filter, str):
                object_filter = [object_filter]

            for poly in object_filter:
                objs = self.modeler.oeditor.FilterObjectList("Type", poly, self.modeler.oeditor.FindObjects("Net", net))
                if include_voids:
                    objs = self.modeler.oeditor.FilterObjectList(
                        "Type", poly + " void", self.modeler.oeditor.FindObjects("Net", net)
                    )

        else:
            objs = self.modeler.oeditor.FindObjects("Net", net)
        return objs

    @pyaedt_function_handler()
    def _get_names(self, categories):
        names = []
        for category in categories:
            names.extend(self.modeler.oeditor.FindObjects("Type", category))
        return names

    @property
    def polygon_names(self):
        """Get the list of all polygons in layout.

        Returns
        -------
        list
        """
        return self._get_names(["poly", "plg"])

    @property
    def polygon_voids_names(self):
        """Get the list of all void polygons in layout.

        Returns
        -------
        list
        """
        return self._get_names(["poly void", "plg void"])

    @property
    def line_names(self):
        """Get the list of all lines in layout.

        Returns
        -------
        list
        """
        return self._get_names(["line", "arc"])

    @property
    def line_voids_names(self):
        """Get the list of all void lines in layout.

        Returns
        -------
        list
        """
        return self._get_names(["line void", "arc void"])

    @property
    def rectangle_names(self):
        """Get the list of all rectangles in layout.

        Returns
        -------
        list
        """
        return self._get_names(["rect"])

    @property
    def rectangle_void_names(self):
        """Get the list of all void rectangles in layout.

        Returns
        -------
        list
        """
        return self._get_names(["rect void"])

    @property
    def circle_names(self):
        """Get the list of all circles in layout.

        Returns
        -------
        list
        """
        return self._get_names(["circle"])

    @property
    def circle_voids_names(self):
        """Get the list of all void circles in layout.

        Returns
        -------
        list
        """
        return self._get_names(["circle void"])

    @property
    def via_names(self):
        """Get the list of all vias in layout.

        Returns
        -------
        list
        """
        return self._get_names(["via"])

    @pyaedt_function_handler()
    def cleanup_objects(self):
        """Clean up all 3D Layout geometries.

        Clean up all 3D Layout geometries (circle, rectangles, polygons, lines and voids)
        that have been added or no longer exist in the modeler because they were removed by previous operations.

        Returns
        -------
        tuple
            List of added objects, List of removed names.
        """
        families = [
            [["poly", "plg"], self._polygons, Polygons3DLayout],
            [["line", "arc"], self._lines, Line3dLayout],
            [["circle"], self._circles, Circle3dLayout],
            [
                [
                    "rect",
                ],
                self._rectangles,
                Rect3dLayout,
            ],
            [["poly void", "plg void"], self._polygons, Polygons3DLayout],
            [["line void", "arc void"], self._lines, Line3dLayout],
            [["circle void"], self._circles, Circle3dLayout],
            [["rect void"], self._rectangles, Rect3dLayout],
        ]
        obj_to_add = []
        obj_removed = []
        for element in families:
            poly_types = element[0]
            dict_in = element[1]
            class_name = element[2]
            names = set(dict_in.keys())
            objs = set(self._get_names(poly_types))
            names_to_add = set.difference(objs, names)
            poly = poly_types[0]
            if "void" in poly:
                names_to_remove = [i for i in set.difference(names, objs) if dict_in[i].is_void]
            else:
                names_to_remove = [i for i in set.difference(names, objs) if not dict_in[i].is_void]
            for obj in names_to_add:
                if obj not in names:
                    if class_name == Polygons3DLayout:
                        dict_in[obj] = Polygons3DLayout(self, obj, poly, True if "void" in poly else False)
                    else:
                        dict_in[obj] = class_name(self, obj, True if "void" in poly else False)
                    obj_to_add.append(dict_in[obj])
            for obj in names_to_remove:
                del dict_in[obj]
                obj_removed.append(obj)
        return obj_to_add, obj_removed

    @property
    def polygons(self):
        """Polygons.

        Returns
        -------
        dict[str, :class:`ansys.aedt.core.modeler.cad.object_3dlayout.Polygons3DLayout`]
            Pyaedt Objects.
        """
        if self._polygons:
            return self._polygons
        for obj in self.polygon_names:
            self._polygons[obj] = Polygons3DLayout(self, obj, "poly", False)
        return self._polygons

    @property
    def lines(self):
        """Lines.

        Returns
        -------
        dict[str, :class:`ansys.aedt.core.modeler.cad.object_3dlayout.Line3dLayout`]
            Pyaedt Objects.
        """

        if self._lines:
            return self._lines

        for obj in self.line_names:
            self._lines[obj] = Line3dLayout(self, obj, False)
        return self._lines

    @property
    def circles(self):
        """Circles.

        Returns
        -------
        dict[str, :class:`ansys.aedt.core.modeler.cad.object_3dlayout.Circle3dLayout`]
            Pyaedt Objects.
        """
        if self._circles:
            return self._circles
        for obj in self.circle_names:
            self._circles[obj] = Circle3dLayout(self, obj, False)
        return self._circles

    @property
    def rectangles(self):
        """Rectangles.

        Returns
        -------
        dict[str, :class:`ansys.aedt.core.modeler.cad.object_3dlayout.Rect3dLayout`]
            Pyaedt Objects.
        """
        if self._rectangles:
            return self._rectangles
        for obj in self.rectangle_names:
            self._rectangles[obj] = Rect3dLayout(self, obj, False)
        return self._rectangles

    @property
    def polygons_voids(self):
        """Void Polygons.

        Returns
        -------
        dict[str, :class:`ansys.aedt.core.modeler.cad.object_3dlayout.Polygons3DLayout`]
            Pyaedt Objects.
        """
        if self._polygons_voids:
            return self._polygons_voids
        for obj in self.polygon_voids_names:
            self._polygons_voids[obj] = Polygons3DLayout(self, obj, "poly", True)
        return self._polygons_voids

    @property
    def lines_voids(self):
        """Void Lines.

        Returns
        -------
        dict[str, :class:`ansys.aedt.core.modeler.cad.object_3dlayout.Line3dLayout`]
            Pyaedt Objects.
        """

        if self._lines:
            return self._lines
        for obj in self.line_voids_names:
            self._lines[obj] = Line3dLayout(self, obj, True)
        return self._lines

    @property
    def circles_voids(self):
        """Void Circles.

        Returns
        -------
        dict[str, :class:`ansys.aedt.core.modeler.cad.object_3dlayout.Circle3dLayout`]
            Pyaedt Objects.
        """
        if self._circles:
            return self._circles
        for obj in self.circle_voids_names:
            self._circles[obj] = Circle3dLayout(self, obj, True)
        return self._circles

    @property
    def rectangles_voids(self):
        """Void Rectangles.

        Returns
        -------
        dict[str, :class:`ansys.aedt.core.modeler.cad.object_3dlayout.Rect3dLayout`]
            Pyaedt Objects.
        """
        if self._rectangles:
            return self._rectangles
        for obj in self.rectangle_void_names:
            self._rectangles[obj] = Rect3dLayout(self, obj, True)
        return self._rectangles

    @property
    def components_3d(self):
        """Components.

        Returns
        -------
        dict[str, :class:`ansys.aedt.core.modeler.cad.object_3dlayout.Components3DLayout`]
            Pyaedt Objects.
        """
        if not self._components3d:
            for i in range(1, 1000):
                cmp_info = self.oeditor.GetComponentInfo(str(i))
                if cmp_info and "ComponentName" in cmp_info[0]:
                    self._components3d[str(i)] = Components3DLayout(self, str(i))
        return self._components3d

    @pyaedt_function_handler()
    def _cleanup_vias(self, pins=True):
        if pins:
            vias = set(self._get_names(["pin"]))
        else:
            vias = set(self._get_names(["via"]))
        names = set(self._pins.keys())
        names_to_add = set.difference(vias, names)
        names_to_remove = set.difference(names, vias)
        obj_to_add = []
        for name in names_to_add:
            if pins:
                self._pins[name] = Pins3DLayout(self, name)
                obj_to_add.append(self._pins[name])
            else:
                self._vias[name] = Pins3DLayout(self, name, is_pin=False)
                obj_to_add.append(self._vias[name])

        for name in names_to_remove:
            if name in self._pins:
                del self._pins[name]
            elif name in self._vias:
                del self._vias[name]
        return obj_to_add, names_to_remove

    @property
    def pins(self):
        """Pins.

        Returns
        -------
        dict[str, :class:`ansys.aedt.core.modeler.cad.object_3dlayout.Pins3DLayout`]
            Pins Dictionary.

        """
        if self._pins or len(self._get_names(["pin"])) == len(self._pins):
            return self._pins
        self._cleanup_vias(True)
        return self._pins

    @property
    def vias(self):
        """Vias.

        Returns
        -------
        dict[str, :class:`ansys.aedt.core.modeler.cad.object_3dlayout.Pins3DLayout`]
            Vias Dictionary.
        """
        if self._vias or len(self._get_names(["via"])) == len(self._vias):
            return self._vias
        self._cleanup_vias(False)

        return self._vias

    @property
    def nets(self):
        """Nets.

        Returns
        -------
        dict[str, :class:`ansys.aedt.core.modeler.cad.object_3dlayout.Nets3DLayout`]
            Nets Dictionary.

        """
        n = {}
        for k, v in self.power_nets.items():
            n[k] = v
        for k, v in self.signal_nets.items():
            n[k] = v
        for k, v in self.no_nets.items():
            n[k] = v
        return n

    @property
    def power_nets(self):
        """Nets.

        Returns
        -------
        dict[str, :class:`ansys.aedt.core.modeler.cad.object_3dlayout.Nets3DLayout`]
            Power Nets Dictionary.

        """
        if self._power_nets:
            return self._power_nets

        objs = self.modeler.oeditor.GetNetClassNets("<Power/Ground>")
        for obj in objs:
            self._power_nets[obj] = Nets3DLayout(self, obj)
        return self._power_nets

    @property
    def signal_nets(self):
        """Nets.

        Returns
        -------
        dict[str, :class:`ansys.aedt.core.modeler.cad.object_3dlayout.Nets3DLayout`]
            Signal Nets Dictionary.

        """
        if self._signal_nets:
            return self._signal_nets

        objs = self.modeler.oeditor.GetNetClassNets("Non Power/Ground")
        for obj in objs:
            self._signal_nets[obj] = Nets3DLayout(self, obj)
        return self._signal_nets

    @property
    def no_nets(self):
        """Nets without class type.

        Returns
        -------
        dict[str, :class:`ansys.aedt.core.modeler.cad.object_3dlayout.Nets3DLayout`]
            No Nets Dictionary.

        """
        if self._no_nets:
            return self._no_nets

        objs = self.modeler.oeditor.GetNetClassNets("<All>")
        for obj in objs:
            if obj not in self.power_nets and obj not in self.signal_nets:
                self._no_nets[obj] = Nets3DLayout(self, obj)
        return self._no_nets

    @property
    def defaultmaterial(self):
        """Default materials.

        Returns
        -------
        list
            List of default materials.

        """
        return default_materials[self._app._design_type]

    @property
    def logger(self):
        """Logger."""
        return self._app.logger

    @property
    def version(self):
        """AEDT version.

        Returns
        -------
        str
            Version of AEDT.

        """
        return self._app._aedt_version

    @property
    def modeler(self):
        """Modeler."""
        return self._modeler

    @property
    def model_units(self):
        """Model units."""
        return self.modeler.model_units

    @property
    def Padstack(self):
        """Padstack."""
        return Padstack()

    @pyaedt_function_handler()
    def new_padstack(self, name="Padstack"):
        """Create a `Padstack` object that can be used to create a padstack.

        Parameters
        ----------
        name : str, optional
            Name of the padstack. The default is ``"Padstack"``.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.object_3dlayout.Padstack`
            Padstack object if a padstack with this name does not already exist.

        """
        if name in self.padstacks:
            return None
        else:
            self.padstacks[name] = Padstack(name, self.opadstackmanager, self.model_units)
            return self.padstacks[name]

    @property
    def padstacks(self):
        """Read all definitions from HFSS 3D Layout.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        if self._padstacks:
            return self._padstacks
        self._padstacks = {}
        names = GeometryOperators.List2list(self.opadstackmanager.GetNames())

        for name in names:
            props_all = GeometryOperators.List2list(self.opadstackmanager.GetData(name))

            props = []
            for p in props_all:
                try:
                    if p[0] == "NAME:psd":
                        props = p
                except Exception:
                    self.logger.debug("Couldn't access first property.")
            self._padstacks[name] = Padstack(name, self.opadstackmanager, self.model_units)

            for prop in props:
                if isinstance(prop, str):
                    if prop == "mat:=":
                        self._padstacks[name].mat = props[props.index(prop) + 1]
                    elif prop == "plt:=":
                        self._padstacks[name].plating = props[props.index(prop) + 1]
                    elif prop == "hRg:=":
                        self._padstacks[name].holerange = props[props.index(prop) + 1]
                    elif prop == "sbsh:=":
                        self._padstacks[name].solder_shape = props[props.index(prop) + 1]
                    elif prop == "sbpl:=":
                        self._padstacks[name].solder_placement = props[props.index(prop) + 1]
                    elif prop == "sbr:=":
                        self._padstacks[name].solder_rad = props[props.index(prop) + 1]
                    elif prop == "sb2:=":
                        self._padstacks[name].sb2 = props[props.index(prop) + 1]
                    elif prop == "sbn:=":
                        self._padstacks[name].solder_mat = props[props.index(prop) + 1]
                    elif prop == "hle:=":
                        self._padstacks[name].hole.shape = props[props.index(prop) + 1][1]
                        self._padstacks[name].hole.sizes = props[props.index(prop) + 1][3]
                        self._padstacks[name].hole.x = props[props.index(prop) + 1][5]
                        self._padstacks[name].hole.y = props[props.index(prop) + 1][7]
                        self._padstacks[name].hole.rot = props[props.index(prop) + 1][9]
                try:
                    if prop[0] == "NAME:pds":
                        layers_num = len(prop) - 1
                        i = 1
                        while i <= layers_num:
                            lay = prop[i]
                            lay_name = lay[2]
                            lay_id = int(lay[4])
                            self._padstacks[name].add_layer(layer=lay_name, layer_id=lay_id)
                            self._padstacks[name].layers[lay_name].layername = lay_name
                            self._padstacks[name].layers[lay_name].pad = self._padstacks[name].add_hole(
                                lay[6][1], list(lay[6][3]), lay[6][5], lay[6][7], lay[6][9]
                            )
                            self._padstacks[name].layers[lay_name].antipad = self._padstacks[name].add_hole(
                                lay[8][1], list(lay[8][3]), lay[8][5], lay[8][7], lay[8][9]
                            )
                            self._padstacks[name].layers[lay_name].thermal = self._padstacks[name].add_hole(
                                lay[10][1], list(lay[10][3]), lay[10][5], lay[10][7], lay[10][9]
                            )
                            self._padstacks[name].layers[lay_name].connectionx = lay[12]
                            self._padstacks[name].layers[lay_name].connectiony = lay[14]
                            self._padstacks[name].layers[lay_name].connectiondir = lay[16]
                            i += 1
                except Exception:
                    self.logger.debug(f"Exception caught when updating padstack '{name}' properties.")

        return self._padstacks

    @pyaedt_function_handler(netlist="assignment")
    def change_net_visibility(self, assignment=None, visible=False):
        """Change the visibility of one or more nets.

        Parameters
        ----------
        assignment : str  or list, optional
            One or more nets to visualize. The default is ``None``.
            If no nets are provided all the nets in the design will be selected.
        visible : bool, optional
            Whether to make the selected nets visible.
            The default value is ``False``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.SetNetVisible
        """
        nets_dictionary = {}
        if not assignment:
            assignment = self.nets
        elif [x for x in assignment if x not in self.nets]:
            self.logger.error("Selected net doesn't exist in current design.")
            return False
        if isinstance(assignment, str):
            assignment = [assignment]

        if isinstance(visible, str):
            if visible.lower() == "true":
                visible = True
            elif visible.lower() == "false":
                visible = False
            else:
                self.logger.error("Provide a valid string value for visibility.")
                return False
        elif not isinstance(visible, bool):
            self.logger.error("Provide a valid type value for visibility.")
            return False

        for net in self.nets:
            if net not in assignment:
                nets_dictionary[net] = not visible
            else:
                nets_dictionary[net] = visible

        args = ["NAME:Args"]
        try:
            for key in nets_dictionary:
                args.append("Name:=")
                args.append(key)
                args.append("Vis:=")
                args.append(nets_dictionary[key])
            self.oeditor.SetNetVisible(args)
            return True
        except Exception:
            self.logger.error("Couldn't change nets visibility.")
            return False

    @pyaedt_function_handler(netname="net")
    def create_via(
        self,
        padstack="PlanarEMVia",
        x=0,
        y=0,
        rotation=0,
        hole_diam=None,
        top_layer=None,
        bot_layer=None,
        name=None,
        net=None,
    ):
        # type: (str, float | str, float | str, float, float, str, str, str, str) -> Pins3DLayout
        """Create a via based on an existing padstack.

        Parameters
        ----------
        padstack : str, optional
            Name of the padstack. The default is ``"PlanarEMVia"``.
        x : float, optional
            Position on the X axis. The default is ``0``.
        y : float, optional
            Position on the Y axis. The default is ``0``.
        rotation : float, optional
            Angle rotation in degrees. The default is ``0``.
        hole_diam : float, optional
            Diameter of the hole. If ``None`` the default is ``1``,
            in which case the override is disabled.
        top_layer : str, optional
            Top layer. If ``None`` the first layer is taken.
        bot_layer : str, optional
            Bottom layer. If ``None`` the last layer is taken.
        name : str, optional
            Name of the via. If ``None`` a random name is generated.
        net : str, optional
            Name of the net. The default is ``None``, in which case no
            name is assigned.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.object_3dlayout.Pins3DLayout` or bool
            Object via created when successful, ``False`` when failed.

        References
        ----------
        >>> oEditor.CreateVia
        """
        layers = self.modeler.layers.all_signal_layers
        if not top_layer:
            top_layer = layers[0].name
        if not bot_layer:
            bot_layer = layers[len(layers) - 1].name
        if not name:
            name = generate_unique_name("via")
        else:
            listnames = self.oeditor.FindObjects("Name", name)
            if listnames:
                name = _uname(name)
        try:
            arg = ["NAME:Contents"]
            arg.append("name:="), arg.append(name)
            arg.append("ReferencedPadstack:="), arg.append(padstack),
            arg.append("vposition:="),
            arg.append(["x:=", self._app.value_with_units(x), "y:=", self._app.value_with_units(y)])
            arg.append("vrotation:="), arg.append([str(rotation) + "deg"])
            if hole_diam:
                arg.append("overrides hole:="), arg.append(True)
                arg.append("hole diameter:="), arg.append([self._app.value_with_units(hole_diam)])

            else:
                arg.append("overrides hole:="), arg.append(False)
                arg.append("hole diameter:="), arg.append([self._app.value_with_units(1)])

            arg.append("Pin:="), arg.append(False)
            arg.append("highest_layer:="), arg.append(top_layer)
            arg.append("lowest_layer:="), arg.append(bot_layer)

            self.oeditor.CreateVia(arg)
            if net:
                self.oeditor.ChangeProperty(
                    [
                        "NAME:AllTabs",
                        [
                            "NAME:BaseElementTab",
                            ["NAME:PropServers", name],
                            ["NAME:ChangedProps", ["NAME:Net", "Value:=", net]],
                        ],
                    ]
                )
            self._cleanup_vias(pins=False)
            return self.vias[name]
        except ValueError as e:
            self.logger.error(str(e))
            return False

    @pyaedt_function_handler(layername="layer", netname="net", net_name="net")
    def create_circle(self, layer, x, y, radius, name=None, net=None, **kwargs):
        """Create a circle on a layer.

        Parameters
        ----------
        layer : str
            Name of the layer.
        x : float
            Position on the X axis.
        y : float
            Position on the Y axis.
        radius : float
            Radius of the circle.
        name : str, optional
            Name of the circle. The default is ``None``, in which case the
            default name is assigned.
        net : str, optional
            Name of the net. The default is ``None``, in which case the
            default name is assigned.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.object_3dlayout.Circle3dLayout`
            Objects of the circle created when successful.

        References
        ----------
        >>> oEditor.CreateCircle
        """
        if not name:
            name = _uname()
        else:
            listnames = self.oeditor.FindObjects("Name", name)
            if listnames:
                name = _uname(name)

        vArg1 = ["NAME:Contents", "circleGeometry:="]
        vArg2 = []
        vArg2.append("Name:="), vArg2.append(name)
        vArg2.append("LayerName:="), vArg2.append(layer)
        vArg2.append("lw:="), vArg2.append("0")
        vArg2.append("x:="), vArg2.append(self._app.value_with_units(x))
        vArg2.append("y:="), vArg2.append(self._app.value_with_units(y))
        vArg2.append("r:="), vArg2.append(self._app.value_with_units(radius))
        vArg1.append(vArg2)
        self.oeditor.CreateCircle(vArg1)
        primitive = Circle3dLayout(self, name, False)
        self._circles[name] = primitive

        if net:
            primitive.change_property(value=["NAME:Net", "Value:=", net])

        return primitive

    @pyaedt_function_handler(layername="layer", dimensions="sizes", net_name="net", netname="net")
    def create_rectangle(self, layer, origin, sizes, corner_radius=0, angle=0, name=None, net=None, **kwargs):
        """Create a rectangle on a layer.

        Parameters
        ----------
        layer : str
            Name of the layer.
        origin : list
            Origin of the coordinate system in a list of ``[x, y]`` coordinates.
        sizes : list
            Dimensions for the box in a list of ``[x, y]`` coordinates.
        corner_radius : float, optional
        angle : float, optional
            Angle rotation in degrees. The default is ``0``.
        name : str, optional
            Name of the rectangle. The default is ``None``, in which case the
            default name is assigned.
        net : str, optional
            Name of the net. The default is ``None``, in which case the
            default name is assigned.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.object_3dlayout.Rect3dLayout`
            Name of the rectangle created when successful.

        References
        ----------
        >>> oEditor.CreateRectangle
        """
        if not name:
            name = _uname()
        else:
            listnames = self.oeditor.FindObjects("Name", name)
            if listnames:
                name = _uname(name)

        vArg1 = ["NAME:Contents", "rectGeometry:="]
        vArg2 = []
        vArg2.append("Name:="), vArg2.append(name)
        vArg2.append("LayerName:="), vArg2.append(layer)
        vArg2.append("lw:="), vArg2.append("0")
        vArg2.append("Ax:="), vArg2.append(self._app.value_with_units(origin[0]))
        vArg2.append("Ay:="), vArg2.append(self._app.value_with_units(origin[1]))
        vArg2.append("Bx:="), vArg2.append(
            self._app.value_with_units(origin[0]) + "+" + self._app.value_with_units(sizes[0])
        )
        vArg2.append("By:="), vArg2.append(
            self._app.value_with_units(origin[1]) + "+" + self._app.value_with_units(sizes[1])
        )
        vArg2.append("cr:="), vArg2.append(self._app.value_with_units(corner_radius))
        vArg2.append("ang:=")
        vArg2.append(self._app.value_with_units(angle, "deg"))
        vArg1.append(vArg2)
        self.oeditor.CreateRectangle(vArg1)
        primitive = Rect3dLayout(self, name, False)
        self._rectangles[name] = primitive

        if net:
            primitive.change_property(value=["NAME:Net", "Value:=", net])

        return primitive

    @pyaedt_function_handler(layername="layer", net_name="net")
    def create_polygon(self, layer, point_list, units=None, name=None, net=None):
        """Create a polygon on a specified layer.

        Parameters
        ----------
        layer : str
            Name of the layer.
        point_list : list
            Origin of the coordinate system in a list of ``[x, y]`` coordinates.
        units : str, optional
            Polygon units. Default is modeler units.
        name : str, optional
            Name of the rectangle. The default is ``None``, in which case the
            default name is assigned.
        net : str, optional
            Name of the net. The default is ``None``, in which case the
            default name is assigned.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.object_3dlayout.Polygons3DLayout`
            Object of the rectangle created when successful.

        References
        ----------
        >>> oEditor.CreatePolygon
        """
        if not name:
            name = _uname()
        else:
            listnames = self.oeditor.FindObjects("Name", name)
            if listnames:
                name = _uname(name)

        vArg1 = ["NAME:Contents", "polyGeometry:="]
        vArg2 = []
        vArg2.append("Name:="), vArg2.append(name)
        vArg2.append("LayerName:="), vArg2.append(layer)
        vArg2.append("lw:="), vArg2.append("0")
        vArg2.append("n:="), vArg2.append(len(point_list))
        vArg2.append("U:="), vArg2.append(units if units else self.model_units)
        for point in point_list:
            vArg2.append("x:="), vArg2.append(point[0])
            vArg2.append("y:="), vArg2.append(point[1])
        vArg1.append(vArg2)
        self.oeditor.CreatePolygon(vArg1)
        primitive = Polygons3DLayout(self, name, is_void=False)
        self._polygons[name] = primitive

        if net:
            primitive.change_property(value=["NAME:Net", "Value:=", net])

        return primitive

    @pyaedt_function_handler(layername="layer", point_list="points", object_owner="assignment")
    def create_polygon_void(self, layer, points, assignment, units=None, name=None):
        """Create a polygon void on a specified layer.

        Parameters
        ----------
        layer : str
            Name of the layer.
        points : list
            List of points in a list of ``[x, y]`` coordinates.
        assignment : str
            Object Owner.
        units : str, optional
            Polygon units. Default is modeler units.
        name : str, optional
            Name of the rectangle. The default is ``None``, in which case the
            default name is assigned.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.object_3dlayout.Polygons3DLayout`
            Object of the rectangle created when successful.

        References
        ----------
        >>> oEditor.CreatePolygon
        """
        if not name:
            name = _uname()
        else:
            listnames = self.oeditor.FindObjects("Name", name)
            if listnames:
                name = _uname(name)
        if not self.oeditor.FindObjects("Name", assignment):
            self._app.logger.error("Owner Polygon not found.")
            return False

        vArg1 = ["NAME:Contents", "owner:=", assignment, "poly voidGeometry:="]
        vArg2 = []
        vArg2.append("Name:="), vArg2.append(name)
        vArg2.append("LayerName:="), vArg2.append(layer)
        vArg2.append("lw:="), vArg2.append("0")
        vArg2.append("n:="), vArg2.append(len(points))
        vArg2.append("U:="), vArg2.append(units if units else self.model_units)
        for point in points:
            vArg2.append("x:="), vArg2.append(point[0])
            vArg2.append("y:="), vArg2.append(point[1])
        vArg1.append(vArg2)
        self.oeditor.CreatePolygonVoid(vArg1)
        primitive = Polygons3DLayout(self, name, is_void=True)
        self._polygons[name] = primitive

        return primitive

    @pyaedt_function_handler(
        layername="layer", center_line_list="center_line_coordinates", net_name="net", netname="net"
    )
    def create_line(
        self, layer, center_line_coordinates, lw=1, start_style=0, end_style=0, name=None, net=None, **kwargs
    ):
        # type: (str, list, float|str, int, int, str, str, any) -> Line3dLayout
        """Create a line based on a list of points.

        Parameters
        ----------
        layer : str
            Name of the layer to create the line on.
        center_line_coordinates : list
            List of centerline coordinates in the form of ``[x, y]``.
        lw : float, optional
            Line width. The default is ``1``.
        start_style :
            Starting style of the line. Options are:

            * ``0`` - Flat
            * ``1`` - Extended
            * ``2`` - Round

            The default is ``0``.
        end_style :
            Ending style of the line. The options are the same as
            those for ``start_style``. The default is ``0``.
        name : str, optional
            Name  of the line. The default is ``None``, in which case the
            default name is assigned.
        net : str, optional
            Name of the net. The default is ``None``, in which case the
            default name is assigned.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.object_3dlayout.Line3dLayout`
            Object of the line created when successful.

        References
        ----------
        >>> oEditor.CreateLine
        """
        if "netname" in kwargs:
            warnings.warn(
                "`netname` is deprecated. Use `net_name` instead.",
                DeprecationWarning,
            )
            net = kwargs["netname"]
        if not name:
            name = _uname()
        else:
            listnames = self.oeditor.FindObjects("Name", name)
            if listnames:
                name = _uname(name)
        arg = ["NAME:Contents", "lineGeometry:="]
        arg2 = [
            "Name:=",
            name,
            "LayerName:=",
            layer,
            "lw:=",
            self._app.value_with_units(lw),
            "endstyle:=",
            end_style,
            "StartCap:=",
            start_style,
            "n:=",
            len(center_line_coordinates),
            "U:=",
            self.model_units,
        ]
        for a in center_line_coordinates:
            arg2.append("x:=")
            arg2.append(a[0])
            arg2.append("y:=")
            arg2.append(a[1])
        arg.append(arg2)
        self.oeditor.CreateLine(arg)
        primitive = Line3dLayout(self, name, False)
        self._lines[name] = primitive

        if net:
            primitive.change_property(value=["NAME:Net", "Value:=", net])
        return primitive

    @pyaedt_function_handler()
    def number_with_units(self, value, units=None):
        """Convert a number to a string with units.

        .. deprecated:: 0.14.0
            Use :func:`value_with_units` in Analysis class instead.

        If value is a string, it's returned as is.

        Parameters
        ----------
        value : float, int, str
            Input  number or string.
        units : optional
            Units for formatting. The default is ``None``, which uses ``"meter"``.

        Returns
        -------
        str
           String concatenating the value and unit.

        """
        return self._app.value_with_units(value, units)

    @pyaedt_function_handler()
    def place_3d_component(
        self,
        component_path,
        number_of_terminals=1,
        placement_layer=None,
        component_name=None,
        pos_x=0,
        pos_y=0,
        create_ports=True,
        is_3d_placement=False,
        pos_z=0,
    ):
        """Place an HFSS 3D component in HFSS 3D Layout.

        Parameters
        ----------
        component_path : str
            Full path to the A3DCOMP file.
        number_of_terminals : int, optional
            Number of ports in the 3D component. The default is ``1``.
        placement_layer : str, optional
            Layer to place the component on. The default is ``None``, in which case it is
            placed on top.
        component_name : str, optional
            Name of the component. The default is ``None``, in which case a
            default name is assigned.
        pos_x : float, optional
            X placement. The default is ``0``.
        pos_y : float, optional
            Y placement. The default is ``0``.
        create_ports : bool, optional
            Whether to expose 3D component ports. The default is ``True``.
        is_3d_placement : bool, optional
            Whether if the component is placed on a layer or arbitrary.
        pos_z : float, optional
            Z placement. When enabled, 3d placement will be automatically enabled too.
             The default is ``False``.

        Returns
        -------
            :class:`ansys.aedt.core.modeler.pcb.object_3d_layout.ComponentsSubCircuit3DLayout`
        """
        if not component_name:
            component_name = os.path.basename(component_path).split(".")[0]
        args = ["NAME:" + component_name]
        infos = [
            "Type:=",
            27,
            "NumTerminals:=",
            number_of_terminals,
            "DataSource:=",
            "",
            "ModifiedOn:=",
            1646294080,
            "Manufacturer:=",
            "",
            "Symbol:=",
            "v1_" + component_name,
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
            "BlueDot.bmp",
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
            1646294079,
            "ExampleFile:=",
            "",
            "HiddenComponent:=",
            0,
            "CircuitEnv:=",
            0,
            "GroupID:=",
            0,
        ]
        args.append("Info:=")
        args.append(infos)
        args.append("CircuitEnv:=")
        args.append(0)
        args.append("Refbase:=")
        args.append("U")
        args.append("NumParts:=")
        args.append(1)
        args.append("ModSinceLib:=")
        args.append(True)
        args.append("CompExtID:=")
        args.append(8)
        args.append("3DCompSourceFileName:=")
        args.append(component_path)

        self.modeler.o_component_manager.Add(args)
        stack_layers = [f"0:{i.name}" for i in self.modeler.layers.stackup_layers]
        drawing = [f"{i.name}:{i.name}" for i in self.modeler.layers.drawing_layers]
        arg_x = self._app.value_with_units(pos_x)
        arg_y = self._app.value_with_units(pos_y)
        args = [
            "NAME:Contents",
            "definition_name:=",
            component_name,
            "placement:=",
            ["x:=", arg_x, "y:=", arg_y],
            "layer:=",
            placement_layer if placement_layer else self.modeler.layers.stackup_layers[0].name,
            "isCircuit:=",
            False,
            "compInstName:=",
            "1",
            "rect_width:=",
            0.01,
            "StackupLayers:=",
            stack_layers,
            "DrawLayers:=",
            drawing,
        ]
        comp_name = self.modeler.oeditor.CreateComponent(args)
        comp = ComponentsSubCircuit3DLayout(self, comp_name.split(";")[-1])
        if is_3d_placement or pos_z != 0:
            comp.is_3d_placement = True
            if pos_z:
                comp.location = [arg_x, arg_y, self._app.value_with_units(pos_z)]
        self.components_3d[comp_name.split(";")[-1]] = comp
        if create_ports:
            self.oeditor.CreatePortsOnComponentsByNet(["NAME:Components", comp.name], [], "Port", "0", "0", "0")
        return comp  #

    @pyaedt_function_handler()
    def create_component_on_pins(
        self,
        pins,
        definition_name=None,
        component_type="Other",
        ref_des="U100",
    ):
        """Create a component based on a pin list.

        Parameters
        ----------
        pins : list
            Pins to include in the new component.
        definition_name : str, optional
            Name of the component definition. If no name is provided, a
            name is automatically assigned.
        component_type : str, optional
            Component type. The default is ``"Other"``.
        ref_des : str, optional
            Reference designator. The default is ``"U100"``.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.object_3dlayout.Components3DLayout`

        """
        if not definition_name:
            definition_name = generate_unique_name("COMP")
        placement_layer = list(self.layers.signals.keys())[0]
        for pin in self.pins.items():
            if pin[0] == pins[0]:
                placement_layer = pin[1].start_layer
                break
        comp_name = self.modeler.oeditor.CreateComponent(
            [
                "NAME:Contents",
                "isRCS:=",
                True,
                "definition_name:=",
                definition_name,
                "type:=",
                component_type,
                "ref_des:=",
                ref_des,
                "placement_layer:=",
                placement_layer,
                "elements:=",
                pins,
            ]
        )
        comp = Components3DLayout(self, comp_name.split(";")[-1])
        return comp

    @pyaedt_function_handler(placement_layer="layer")
    def create_text(self, text, position, layer="PostProcessing", angle=0, font_size=12):
        """Create a text primitive object.

        Parameters
        ----------
        text : str
            Name for the text primitive object.
        position : list
            Position of the text.
        layer : str, optional
            Layer where text will be placed. The default value is ``"PostProcessing"``.
        angle : float, optional
            Angle of the text. The default value is ``0``.
        font_size : int, optional
            Font size. The default value is ``12``.

        Returns
        -------
        str
            Name of the text primitive.
        """
        name = _uname("text_")
        args = [
            "NAME:Contents",
            "textGeometry:=",
            [
                "Name:=",
                name,
                "LayerName:=",
                layer,
                "x:=",
                position[0],
                "y:=",
                position[1],
                "ang:=",
                angle,
                "isPlot:=",
                False,
                "font:=",
                "Arial",
                "size:=",
                font_size,
                "weight:=",
                3,
                "just:=",
                4,
                "mirror:=",
                False,
                "text:=",
                text,
            ],
        ]
        return self.modeler.oeditor.CreateText(args)
