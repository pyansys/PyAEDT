"""
This module contains the `EdbStackup` class.

"""

from __future__ import absolute_import  # noreorder

import json
import logging
import math
import os.path
import warnings
from collections import OrderedDict

from pyaedt.edb_core.edb_data.layer_data import EDBLayers
from pyaedt.edb_core.edb_data.layer_data import LayerEdbClass
from pyaedt.edb_core.general import convert_py_list_to_net_list
from pyaedt.generic.general_methods import is_ironpython
from pyaedt.generic.general_methods import pyaedt_function_handler

pd = None
if not is_ironpython:
    try:
        import numpy as np
        import pandas as pd
    except ImportError:
        warnings.warn(
            "The Pandas module is required to run some functionalities.\n" "Install with \n\npip install pandas\n"
        )


logger = logging.getLogger(__name__)


class Stackup(object):
    """Manages EDB methods for stackup accessible from `Edb.stackup` property."""

    def __getitem__(self, item):
        return self.layers[item]

    def __init__(self, pedb):
        self._pedb = pedb

    @property
    def layer_types(self):
        """Layer types.

        Returns
        -------
        type
            Types of layers.
        """
        return self._pedb.edb.Cell.LayerType

    @pyaedt_function_handler()
    def _int_to_layer_types(self, val):
        if int(val) == 0:
            return self.layer_types.SignalLayer
        elif int(val) == 1:
            return self.layer_types.DielectricLayer
        elif int(val) == 2:
            return self.layer_types.ConductingLayer
        elif int(val) == 3:
            return self.layer_types.AirlinesLayer
        elif int(val) == 4:
            return self.layer_types.ErrorsLayer
        elif int(val) == 5:
            return self.layer_types.SymbolLayer
        elif int(val) == 6:
            return self.layer_types.MeasureLayer
        elif int(val) == 8:
            return self.layer_types.AssemblyLayer
        elif int(val) == 9:
            return self.layer_types.SilkscreenLayer
        elif int(val) == 10:
            return self.layer_types.SolderMaskLayer
        elif int(val) == 11:
            return self.layer_types.SolderPasteLayer
        elif int(val) == 12:
            return self.layer_types.GlueLayer
        elif int(val) == 13:
            return self.layer_types.WirebondLayer
        elif int(val) == 14:
            return self.layer_types.UserLayer
        elif int(val) == 16:
            return self.layer_types.SIwaveHFSSSolverRegions
        elif int(val) == 17:
            return self.layer_types.PostprocessingLayer
        elif int(val) == 18:
            return self.layer_types.LayerTypesCount
        elif int(val) == -1:
            return self.layer_types.UndefinedLayerType

    @pyaedt_function_handler()
    def create_symmetric_stackup(
        self,
        layer_count,
        inner_layer_thickness="17um",
        outer_layer_thickness="50um",
        dielectric_thickness="100um",
        dielectric_material="fr4_epoxy",
        soldermask=True,
        soldermask_thickness="20um",
    ):  # pragma: no cover
        """Create a symmetric stackup.

        Parameters
        ----------
        layer_count : int
            Number of layer count.
        inner_layer_thickness : str, float, optional
            Thickness of inner conductor layer.
        outer_layer_thickness : str, float, optional
            Thickness of outer conductor layer.
        dielectric_thickness : str, float, optional
            Thickness of dielectric layer.
        dielectric_material : str, optional
            Material of dielectric layer.
        soldermask : bool, optional
            Whether to create soldermask layers. The default is``True``.
        soldermask_thickness : str, optional
            Thickness of soldermask layer.
        Returns
        -------
        bool
        """
        if not layer_count % 2 == 0:
            return False

        self.add_layer(
            "BOT",
            None,
            material="copper",
            thickness=outer_layer_thickness,
            fillMaterial=dielectric_material,
        )
        self.add_layer(
            "D" + str(int(layer_count / 2)),
            None,
            material="fr4_epoxy",
            thickness=dielectric_thickness,
            layer_type="dielectric",
            fillMaterial=dielectric_material,
        )
        self.add_layer(
            "TOP",
            None,
            material="copper",
            thickness=outer_layer_thickness,
            fillMaterial=dielectric_material,
        )
        if soldermask:
            self.add_layer(
                "SMT",
                None,
                material="solder_mask",
                thickness=soldermask_thickness,
                layer_type="dielectric",
                fillMaterial=dielectric_material,
            )
            self.add_layer(
                "SMB",
                None,
                material="solder_mask",
                thickness=soldermask_thickness,
                layer_type="dielectric",
                fillMaterial=dielectric_material,
                method="add_on_bottom",
            )
            self.stackup_layers["TOP"].dielectric_fill = "solder_mask"
            self.stackup_layers["BOT"].dielectric_fill = "solder_mask"

        for layer_num in np.arange(int(layer_count / 2), 1, -1):
            # Generate upper half
            self.add_layer(
                "L" + str(layer_num),
                "TOP",
                material="copper",
                thickness=inner_layer_thickness,
                fillMaterial=dielectric_material,
                method="insert_below",
            )
            self.add_layer(
                "D" + str(layer_num - 1),
                "TOP",
                material=dielectric_material,
                thickness=dielectric_thickness,
                layer_type="dielectric",
                fillMaterial=dielectric_material,
                method="insert_below",
            )

            # Generate lower half
            self.add_layer(
                "L" + str(layer_count - layer_num + 1),
                "BOT",
                material="copper",
                thickness=inner_layer_thickness,
                fillMaterial=dielectric_material,
                method="insert_above",
            )
            self.add_layer(
                "D" + str(layer_count - layer_num + 1),
                "BOT",
                material=dielectric_material,
                thickness=dielectric_thickness,
                layer_type="dielectric",
                fillMaterial=dielectric_material,
                method="insert_above",
            )
        return True

    @property
    def _layer_collection(self):
        """Copy of EDB layer collection.

        Returns
        -------
        class : Ansys.Ansoft.Edb.Cell.LayerCollection
            Collection of layers.
        """
        lc_readonly = self._pedb._active_layout.GetLayerCollection()
        layers = list(list(lc_readonly.Layers(self._pedb.edb.Cell.LayerTypeSet.AllLayerSet)))
        layer_collection = self._pedb.edb.Cell.LayerCollection()
        layer_collection.SetMode(lc_readonly.GetMode())
        for layer in layers:
            layer_collection.AddLayerBottom(layer.Clone())
        return layer_collection

    @property
    def _edb_layer_list(self):
        return list(self._layer_collection.Layers(self._pedb.edb.Cell.LayerTypeSet.AllLayerSet))

    @property
    def _edb_layer_list_nonstackup(self):
        return list(self._layer_collection.Layers(self._pedb.edb.Cell.LayerTypeSet.NonStackupLayerSet))

    @property
    def layers(self):
        """Retrieve the dictionary of layers.

        Returns
        -------
        dict
        """
        _lays = OrderedDict()
        for l in self._edb_layer_list:
            name = l.GetName()
            _lays[name] = LayerEdbClass(self, name)
        return _lays

    @property
    def signal_layers(self):
        """Retrieve the dictionary of signal layers.

        Returns
        -------
        dict
        """
        layer_type = self._pedb.edb.Cell.LayerType.SignalLayer
        _lays = OrderedDict()
        for name, obj in self.layers.items():
            if obj._edb_layer.GetLayerType() == layer_type:
                _lays[name] = obj
        return _lays

    @property
    def stackup_layers(self):
        """Retrieve the dictionary of signal and dielectric layers.

        Returns
        -------
        dict
        """
        layer_type = [
            self._pedb.edb.Cell.LayerType.SignalLayer,
            self._pedb.edb.Cell.LayerType.DielectricLayer,
        ]
        _lays = OrderedDict()
        for name, obj in self.layers.items():
            if obj._edb_layer.GetLayerType() in layer_type:
                _lays[name] = obj
        return _lays

    @property
    def non_stackup_layers(self):
        """Retrieve the dictionary of signal layers.

        Returns
        -------
        dict
        """
        return {l.GetName(): LayerEdbClass(self, l.GetName()) for l in self._edb_layer_list_nonstackup}

    @pyaedt_function_handler()
    def _edb_value(self, value):
        return self._pedb.edb_value(value)

    @pyaedt_function_handler()
    def _set_layout_stackup(self, layer_clone, operation, base_layer=None, method=1):
        """Internal method. Apply stackup change into EDB.

        Parameters
        ----------
        layer_clone : :class:`pyaedt.edb_core.EDB_Data.EDBLayer`
        operation : str
            Options are ``"change_attribute"``, ``"change_name"``,``"change_position"``, ``"insert_below"``,
             ``"insert_above"``, ``"add_on_top"``, ``"add_on_bottom"``, ``"non_stackup"``.
        base_layer : str, optional
            Name of the base layer. The default value is ``None``.
        Returns
        -------

        """
        edb_layers = self._edb_layer_list
        non_stackup = []
        if operation in ["change_attribute", "change_name", "change_position"]:
            new_layer_collection = self._pedb.edb.Cell.LayerCollection()
        else:
            new_layer_collection = self._pedb.edb.Cell.LayerCollection()
            for layer in edb_layers:
                to_layer = layer.Clone()
                if to_layer.IsStackupLayer() or (to_layer.GetName().lower() == "outline" and method == 1):
                    new_layer_collection.AddLayerBottom(to_layer)
                else:
                    non_stackup.append(to_layer)

        if operation == "change_position":
            for lyr in edb_layers:
                if not (layer_clone.GetName() == lyr.GetName()):
                    if base_layer == lyr.GetName():
                        new_layer_collection.AddLayerBottom(layer_clone)
                    new_layer_collection.AddLayerBottom(lyr)
        elif operation == "change_attribute":
            for lyr in edb_layers:
                if not (layer_clone.GetName() == lyr.GetName()):
                    new_layer_collection.AddLayerBottom(lyr)
                else:
                    new_layer_collection.AddLayerBottom(layer_clone)
        elif operation == "change_name":
            for lyr in edb_layers:
                if not (base_layer == lyr.GetName()):
                    new_layer_collection.AddLayerBottom(lyr)
                else:
                    new_layer_collection.AddLayerBottom(layer_clone)
        else:
            if operation == "insert_below":
                new_layer_collection.AddLayerBelow(layer_clone, base_layer)
            elif operation == "insert_above":
                new_layer_collection.AddLayerAbove(layer_clone, base_layer)
            elif operation == "add_on_top":
                new_layer_collection.AddLayerTop(layer_clone)
            elif operation == "add_on_bottom":
                new_layer_collection.AddLayerBottom(layer_clone)
            else:
                new_layer_collection.AddLayerTop(layer_clone)
            for lay in non_stackup:
                new_layer = self._pedb.edb.Cell.Layer(lay.GetName(), self._int_to_layer_types(lay.GetLayerType()))
                new_layer_collection.AddLayerBottom(new_layer)
        return self._pedb._active_layout.SetLayerCollection(new_layer_collection)

    @pyaedt_function_handler()
    def _create_stackup_layer(self, layer_name, thickness, layer_type="signal"):
        if layer_type == "signal":
            _layer_type = self._pedb.edb.Cell.LayerType.SignalLayer
        else:
            _layer_type = self._pedb.edb.Cell.LayerType.DielectricLayer

        return self._pedb.edb.Cell.StackupLayer(
            layer_name,
            _layer_type,
            self._edb_value(thickness),
            self._edb_value(0),
            "",
        )

    @pyaedt_function_handler()
    def _create_nonstackup_layer(self, layer_name, layer_type):
        if layer_type == "conducting":  # pragma: no cover
            _layer_type = self._pedb.edb.Cell.LayerType.ConductingLayer
        elif layer_type == "air_lines":  # pragma: no cover
            _layer_type = self._pedb.edb.Cell.LayerType.AirlinesLayer
        elif layer_type == "error":  # pragma: no cover
            _layer_type = self._pedb.edb.Cell.LayerType.ErrorsLayer
        elif layer_type == "symbol":  # pragma: no cover
            _layer_type = self._pedb.edb.Cell.LayerType.SymbolLayer
        elif layer_type == "measure":  # pragma: no cover
            _layer_type = self._pedb.edb.Cell.LayerType.MeasureLayer
        elif layer_type == "assembly":  # pragma: no cover
            _layer_type = self._pedb.edb.Cell.LayerType.AssemblyLayer
        elif layer_type == "silkscreen":  # pragma: no cover
            _layer_type = self._pedb.edb.Cell.LayerType.SilkscreenLayer
        elif layer_type == "solder_mask":  # pragma: no cover
            _layer_type = self._pedb.edb.Cell.LayerType.SolderMaskLayer
        elif layer_type == "solder_paste":  # pragma: no cover
            _layer_type = self._pedb.edb.Cell.LayerType.SolderPasteLayer
        elif layer_type == "glue":  # pragma: no cover
            _layer_type = self._pedb.edb.Cell.LayerType.GlueLayer
        elif layer_type == "wirebond":  # pragma: no cover
            _layer_type = self._pedb.edb.Cell.LayerType.WirebondLayer
        elif layer_type == "user":  # pragma: no cover
            _layer_type = self._pedb.edb.Cell.LayerType.UserLayer
        elif layer_type == "hfss_region":  # pragma: no cover
            _layer_type = self._pedb.edb.Cell.LayerType.SIwaveHFSSSolverRegions
        else:  # pragma: no cover
            _layer_type = self._pedb.edb.Cell.LayerType.OutlineLayer

        return self._pedb.edb.Cell.Layer(layer_name, _layer_type)

    @pyaedt_function_handler()
    def add_layer(
        self,
        layer_name,
        base_layer=None,
        method="add_on_top",
        layer_type="signal",
        material="copper",
        fillMaterial="fr4_epoxy",
        thickness="35um",
        etch_factor=None,
        is_negative=False,
        enable_roughness=False,
    ):
        """Insert a layer into stackup.

        Parameters
        ----------
        layer_name : str
            Name of the layer.
        base_layer : str, optional
            Name of the base layer.
        method : str, optional
            Where to insert the new layer. The default is ``"add_on_top"``. Options are ``"add_on_top"``,
            ``"add_on_bottom"``, ``"insert_above"``, ``"insert_below"``.
        layer_type : str, optional
            Type of layer. The default is ``"signal"``. Options are ``"signal"``, ``"dielectric"``, ``"conducting"``,
             ``"air_lines"``, ``"error"``, ``"symbol"``, ``"measure"``, ``"assembly"``, ``"silkscreen"``,
             ``"solder_mask"``, ``"solder_paste"``, ``"glue"``, ``"wirebond"``, ``"hfss_region"``, ``"user"``.
        material : str, optional
            Material of the layer.
        fillMaterial : str, optional
            Fill material of the layer.
        thickness : str, float, optional
            Thickness of the layer.
        etch_factor : int, float, optional
            Etch factor of the layer.
        is_negative : bool, optional
            Whether the layer is negative.
        enable_roughness : bool, optional
            Whether roughness is enabled.
        Returns
        -------

        """
        if layer_name in self.layers:
            logger.error("layer {} exists.".format(layer_name))
            return False
        materials_lower = {m.lower(): m for m in list(self._pedb.materials.materials.keys())}
        if not material:
            if layer_type == "signal":
                material = "copper"
            else:
                material = "fr4_epoxy"
        if not fillMaterial:
            fillMaterial = "fr4_epoxy"

        if material.lower() not in materials_lower:
            logger.error(material + " does not exist in material library")
        else:
            material = materials_lower[material.lower()]

        if layer_type != "dielectric":
            if fillMaterial.lower() not in materials_lower:
                logger.error(fillMaterial + " does not exist in material library")
            else:
                fillMaterial = materials_lower[fillMaterial.lower()]

        if layer_type in ["signal", "dielectric"]:
            new_layer = self._create_stackup_layer(layer_name, thickness, layer_type)
            new_layer.SetMaterial(material)
            if layer_type != "dielectric":
                new_layer.SetFillMaterial(fillMaterial)
            new_layer.SetNegative(is_negative)
            l1 = len(self.layers)
            self._set_layout_stackup(new_layer, method, base_layer)
            if len(self.layers) == l1:
                self._set_layout_stackup(new_layer, method, base_layer, method=2)
            if etch_factor:
                new_layer = self.layers[layer_name]
                new_layer.etch_factor = etch_factor
            if enable_roughness:
                new_layer = self.layers[layer_name]
                new_layer.roughness_enabled = True
        else:
            new_layer = self._create_nonstackup_layer(layer_name, layer_type)
            self._set_layout_stackup(new_layer, "non_stackup")

        return self.layers[layer_name]

    def remove_layer(self, name):
        """Remove a layer from stackup.

        Parameters
        ----------
        name : str
            Name of the layer to remove.

        Returns
        -------

        """
        new_layer_collection = self._pedb.edb.Cell.LayerCollection()
        for lyr in self._edb_layer_list:
            if not (lyr.GetName() == name):
                new_layer_collection.AddLayerBottom(lyr)
        return self._pedb._active_layout.SetLayerCollection(new_layer_collection)

    @pyaedt_function_handler
    def import_stackup(self, fpath):
        """Import stackup defnition from csv file.

        Parameters
        ----------
        fpath : str
            File path to csv or json file.
        """
        if os.path.splitext(fpath)[1] == ".json":
            return self._import_layer_stackup(fpath)
        if is_ironpython:
            self._pedb.logger.error("Method working on CPython only.")
            return False
        df = pd.read_csv(fpath, index_col=0)
        prev_layer = None
        for row, val in df[::-1].iterrows():
            if not self.stackup_layers:
                self.add_layer(
                    row,
                    None,
                    "add_on_top",
                    val.Type,
                    val.Material,
                    val.Dielectric_Fill if not pd.isnull(val.Dielectric_Fill) else "",
                    val.Thickness,
                )
            else:
                if row in self.stackup_layers.keys():
                    lyr = self.stackup_layers[row]
                    lyr.type = val.Type
                    lyr.material = val.Material
                    lyr.dielectric_fill = val.Dielectric_Fill if not pd.isnull(val.Dielectric_Fill) else ""
                    lyr.thickness = val.Thickness
                    if prev_layer:
                        self._set_layout_stackup(lyr._edb_layer, "change_position", prev_layer)
                else:
                    if prev_layer and prev_layer in self.stackup_layers:
                        layer_name = prev_layer
                    else:
                        layer_name = list(self.stackup_layers.keys())[-1] if self.stackup_layers else None
                    self.add_layer(
                        row,
                        layer_name,
                        "insert_above",
                        val.Type,
                        val.Material,
                        val.Dielectric_Fill if not pd.isnull(val.Dielectric_Fill) else "",
                        val.Thickness,
                    )
                prev_layer = row
        for name in self.stackup_layers:
            if name not in df.index:
                self.remove_layer(name)
        return True

    @pyaedt_function_handler
    def export_stackup(self, fpath, file_format="csv"):
        """Export stackup definition to csv file.

        Parameters
        ----------
        fpath : str
            File path to csv file.
        file_format : str, optional
            The format of the file to be exported. The default is ``"csv"``. Options are ``"csv"``, ``"xlsx"``.
        """
        if is_ironpython:
            return
        data = {
            "Type": [],
            "Material": [],
            "Dielectric_Fill": [],
            "Thickness": [],
        }
        idx = []
        for lyr in self.stackup_layers.values():
            idx.append(lyr.name)
            data["Type"].append(lyr.type)
            data["Material"].append(lyr.material)
            data["Dielectric_Fill"].append(lyr.dielectric_fill)
            data["Thickness"].append(lyr.thickness)
        df = pd.DataFrame(data, index=idx, columns=["Type", "Material", "Dielectric_Fill", "Thickness"])
        if file_format == "csv":  # pragma: no cover
            if not fpath.endswith(".csv"):
                fpath = fpath + ".csv"
            df.to_csv(fpath)
        else:  # pragma: no cover
            if not fpath.endswith(".xlsx"):  # pragma: no cover
                fpath = fpath + ".xlsx"
            df.to_excel(fpath)
        return True

    @pyaedt_function_handler
    def _export_layer_stackup_to_json(self, output_file=None, include_material_with_layer=False):
        if not include_material_with_layer:
            material_out = {}
            for k, v in self._pedb.materials.materials.items():
                material_out[k] = v._json_format()
        layers_out = {}
        for k, v in self.stackup_layers.items():
            layers_out[k] = v._json_format()
            if v.material in self._pedb.materials.materials:
                layer_material = self._pedb.materials.materials[v.material]
                if not v.dielectric_fill:
                    dielectric_fill = False
                else:
                    dielectric_fill = self._pedb.materials.materials[v.dielectric_fill]
                if include_material_with_layer:
                    layers_out[k]["material"] = layer_material._json_format()
                    if dielectric_fill:
                        layers_out[k]["dielectric_fill"] = dielectric_fill._json_format()
        if not include_material_with_layer:
            stackup_out = {"materials": material_out, "layers": layers_out}
        else:
            stackup_out = {"layers": layers_out}
        if output_file:
            with open(output_file, "w") as write_file:
                json.dump(stackup_out, write_file, indent=4)

            return True
        else:
            return False

    @pyaedt_function_handler()
    def _import_layer_stackup(self, input_file=None):
        if input_file:
            f = open(input_file)
            json_dict = json.load(f)  # pragma: no cover
            for k, v in json_dict.items():
                if k == "materials":
                    for material in v.values():
                        self._pedb.materials._load_materials(material)
                if k == "layers":
                    if len(list(v.values())) == len(list(self.stackup_layers.values())):
                        imported_layers_list = list(v.keys())
                        layout_layer_list = list(self.stackup_layers.keys())
                        for layer_name in imported_layers_list:
                            layer_index = imported_layers_list.index(layer_name)
                            if layout_layer_list[layer_index] != layer_name:
                                self.stackup_layers[layout_layer_list[layer_index]].name = layer_name
                    prev_layer = None
                    for layer_name, layer in v.items():
                        if layer_name not in self.stackup_layers:
                            if not prev_layer:
                                self.add_layer(
                                    layer_name,
                                    method="add_on_top",
                                    layer_type=layer["type"],
                                    material=layer["material"],
                                    fillMaterial=layer["dielectric_fill"],
                                    thickness=layer["thickness"],
                                )
                                prev_layer = layer_name
                            else:
                                self.add_layer(
                                    layer_name,
                                    base_layer=layer_name,
                                    method="insert_below",
                                    layer_type=layer["type"],
                                    material=layer["material"],
                                    fillMaterial=layer["dielectric_fill"],
                                    thickness=layer["thickness"],
                                )
                                prev_layer = layer_name
                        if layer_name in self.stackup_layers:
                            self.stackup_layers[layer["name"]]._load_layer(layer)
            return True

    @pyaedt_function_handler()
    def stackup_limits(self, only_metals=False):
        """Retrieve stackup limits.

        Parameters
        ----------
        only_metals : bool, optional
            Whether to retrieve only metals. The default is ``False``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if only_metals:
            input_layers = self._pedb.edb.Cell.LayerTypeSet.SignalLayerSet
        else:
            input_layers = self._pedb.edb.Cell.LayerTypeSet.StackupLayerSet

        res, topl, topz, bottoml, bottomz = self._layer_collection.GetTopBottomStackupLayers(input_layers)
        return topl.GetName(), topz, bottoml.GetName(), bottomz

    @pyaedt_function_handler()
    def flip_design(self):
        """Flip the current design of a layout.

        Returns
        -------
        bool
            ``True`` when succeed ``False`` if not.

        Examples
        --------
        >>> edb = Edb(edbpath=targetfile,  edbversion="2021.2")
        >>> edb.stackup.flip_design()
        >>> edb.save()
        >>> edb.close_edb()
        """
        try:
            lc = self._layer_collection
            new_lc = self._pedb.edb.Cell.LayerCollection()
            lc_mode = lc.GetMode()
            new_lc.SetMode(lc_mode)
            max_elevation = 0.0
            for layer in lc.Layers(self._pedb.edb.Cell.LayerTypeSet.StackupLayerSet):

                if "RadBox" not in layer.GetName():  # Ignore RadBox
                    lower_elevation = layer.Clone().GetLowerElevation() * 1.0e6
                    upper_elevation = layer.Clone().GetUpperElevation() * 1.0e6
                    max_elevation = max([max_elevation, lower_elevation, upper_elevation])

            non_stackup_layers = []
            for layer in lc.Layers(self._pedb.edb.Cell.LayerTypeSet.AllLayerSet):
                cloned_layer = layer.Clone()
                if not cloned_layer.IsStackupLayer():
                    non_stackup_layers.append(cloned_layer)
                    continue
                if "RadBox" not in cloned_layer.GetName() and not cloned_layer.IsViaLayer():
                    upper_elevation = cloned_layer.GetUpperElevation() * 1.0e6
                    updated_lower_el = max_elevation - upper_elevation
                    val = self._edb_value("{}um".format(updated_lower_el))
                    cloned_layer.SetLowerElevation(val)
                    if cloned_layer.GetTopBottomAssociation() == self._pedb.edb.Cell.TopBottomAssociation.TopAssociated:
                        cloned_layer.SetTopBottomAssociation(self._pedb.edb.Cell.TopBottomAssociation.BottomAssociated)
                    else:
                        cloned_layer.SetTopBottomAssociation(self._pedb.edb.Cell.TopBottomAssociation.TopAssociated)
                    new_lc.AddStackupLayerAtElevation(cloned_layer)

            vialayers = [
                lay for lay in lc.Layers(self._pedb.edb.Cell.LayerTypeSet.StackupLayerSet) if lay.Clone().IsViaLayer()
            ]
            for layer in vialayers:
                cloned_via_layer = layer.Clone()
                upper_ref_name = cloned_via_layer.GetRefLayerName(True)
                lower_ref_name = cloned_via_layer.GetRefLayerName(False)
                upper_ref = [
                    lay
                    for lay in lc.Layers(self._pedb.edb.Cell.LayerTypeSet.AllLayerSet)
                    if lay.GetName() == upper_ref_name
                ][0]
                lower_ref = [
                    lay
                    for lay in lc.Layers(self._pedb.edb.Cell.LayerTypeSet.AllLayerSet)
                    if lay.GetName() == lower_ref_name
                ][0]
                cloned_via_layer.SetRefLayer(lower_ref, True)
                cloned_via_layer.SetRefLayer(upper_ref, False)
                ref_layer_in_flipped_stackup = [
                    lay
                    for lay in new_lc.Layers(self._pedb.edb.Cell.LayerTypeSet.AllLayerSet)
                    if lay.GetName() == upper_ref_name
                ][0]
                via_layer_lower_elevation = (
                    ref_layer_in_flipped_stackup.GetLowerElevation() + ref_layer_in_flipped_stackup.GetThickness()
                )
                cloned_via_layer.SetLowerElevation(self._edb_value(via_layer_lower_elevation))
                new_lc.AddStackupLayerAtElevation(cloned_via_layer)

            layer_list = convert_py_list_to_net_list(non_stackup_layers)
            new_lc.AddLayers(layer_list)
            if not self._pedb.active_layout.SetLayerCollection(new_lc):
                self._pedb.logger.error("Failed to Flip Stackup.")
                return False
            for pyaedt_cmp in list(self._pedb.core_components.components.values()):
                cmp = pyaedt_cmp.edbcomponent
                cmp_type = cmp.GetComponentType()
                cmp_prop = cmp.GetComponentProperty().Clone()
                try:
                    if (
                        cmp_prop.GetSolderBallProperty().GetPlacement()
                        == self._pedb.Definition.SolderballPlacement.AbovePadstack
                    ):
                        sball_prop = cmp_prop.GetSolderBallProperty().Clone()
                        sball_prop.SetPlacement(self._pedb.Definition.SolderballPlacement.BelowPadstack)
                        cmp_prop.SetSolderBallProperty(sball_prop)
                    elif (
                        cmp_prop.GetSolderBallProperty().GetPlacement()
                        == self._pedb.Definition.SolderballPlacement.BelowPadstack
                    ):
                        sball_prop = cmp_prop.GetSolderBallProperty().Clone()
                        sball_prop.SetPlacement(self._pedb.Definition.SolderballPlacement.AbovePadstack)
                        cmp_prop.SetSolderBallProperty(sball_prop)
                except:
                    pass
                if cmp_type == self._pedb.Definition.ComponentType.IC:
                    die_prop = cmp_prop.GetDieProperty().Clone()
                    chip_orientation = die_prop.GetOrientation()
                    if chip_orientation == self._pedb.Definition.DieOrientation.ChipDown:
                        die_prop.SetOrientation(self._pedb.Definition.DieOrientation.ChipUp)
                        cmp_prop.SetDieProperty(die_prop)
                    else:
                        die_prop.SetOrientation(self._pedb.Definition.DieOrientation.ChipDown)
                        cmp_prop.SetDieProperty(die_prop)
                cmp.SetComponentProperty(cmp_prop)

            lay_list = list(new_lc.Layers(self._pedb.edb.Cell.LayerTypeSet.SignalLayerSet))
            for padstack in list(self._pedb.core_padstack.padstack_instances.values()):
                start_layer_id = [lay.GetLayerId() for lay in list(lay_list) if lay.GetName() == padstack.start_layer]
                stop_layer_id = [lay.GetLayerId() for lay in list(lay_list) if lay.GetName() == padstack.stop_layer]
                layer_map = padstack._edb_padstackinstance.GetLayerMap()
                layer_map.SetMapping(stop_layer_id[0], start_layer_id[0])
                padstack._edb_padstackinstance.SetLayerMap(layer_map)
            return True
        except:
            return False

    @pyaedt_function_handler()
    def get_layout_thickness(self):
        """Return the layout thickness.

        Returns
        -------
        float
            The thickness value.
        """
        layers_name = list(self.stackup_layers.keys())
        bottom_layer = self.stackup_layers[layers_name[0]]
        top_layer = self.stackup_layers[layers_name[-1]]
        thickness = top_layer.lower_elevation + top_layer.thickness - bottom_layer.lower_elevation
        return thickness

    @pyaedt_function_handler()
    def _get_solder_height(self, layer_name):
        for el, val in self._pedb.core_components.components.items():
            if val.solder_ball_height and val.placement_layer == layer_name:
                return val.solder_ball_height
        return 0

    @pyaedt_function_handler()
    def _remove_solder_pec(self, layer_name):
        for el, val in self._pedb.core_components.components.items():
            if val.solder_ball_height and val.placement_layer == layer_name:
                comp_prop = val.component_property
                port_property = comp_prop.GetPortProperty().Clone()
                port_property.SetReferenceSizeAuto(False)
                port_property.SetReferenceSize(self._edb_value(0.0), self._edb_value(0.0))
                comp_prop.SetPortProperty(port_property)
                val.edbcomponent.SetComponentProperty(comp_prop)

    @pyaedt_function_handler()
    def adjust_solder_dielectrics(self):
        """Adjust the stack-up by adding or modifying dielectric layers that contains Solder Balls.
        This method identifies the solder-ball height and adjust the dielectric thickness on top (or bottom) to fit
        the thickness in order to merge another layout.

        Returns
        -------
        bool
        """
        for el, val in self._pedb.core_components.components.items():
            if val.solder_ball_height:
                layer = val.placement_layer
                if layer == list(self.stackup_layers.keys())[0]:
                    self.add_layer(
                        "Bottom_air",
                        base_layer=list(self.stackup_layers.keys())[-1],
                        method="insert_below",
                        material="air",
                        thickness=val.solder_ball_height,
                        layer_type="dielectric",
                    )
                elif layer == list(self.stackup_layers.keys())[-1]:
                    self.add_layer(
                        "Top_Air",
                        base_layer=layer,
                        material="air",
                        thickness=val.solder_ball_height,
                        layer_type="dielectric",
                    )
                elif layer == list(self.signal_layers.keys())[-1]:
                    list(self.stackup_layers.values())[-1].thickness = val.solder_ball_height

                elif layer == list(self.signal_layers.keys())[0]:
                    list(self.stackup_layers.values())[0].thickness = val.solder_ball_height
        return True

    @pyaedt_function_handler()
    def place_in_layout(
        self,
        edb,
        angle=0.0,
        offset_x=0.0,
        offset_y=0.0,
        flipped_stackup=True,
        place_on_top=True,
    ):
        """Place current Cell into another cell using layer placement method.
        Flip the current layer stackup of a layout if requested. Transform parameters currently not supported.

        Parameters
        ----------
        edb : Edb
            Cell on which to place the current layout. If None the Cell will be applied on an empty new Cell.
        angle : double, optional
            The rotation angle applied on the design.
        offset_x : double, optional
            The x offset value.
        offset_y : double, optional
            The y offset value.
        flipped_stackup : bool, optional
            Either if the current layout is inverted.
            If `True` and place_on_top is `True` the stackup will be flipped before the merge.
        place_on_top : bool, optional
            Either if place the current layout on Top or Bottom of destination Layout.

        Returns
        -------
        bool
            ``True`` when succeed ``False`` if not.

        Examples
        --------
        >>> edb1 = Edb(edbpath=targetfile1,  edbversion="2021.2")
        >>> edb2 = Edb(edbpath=targetfile2, edbversion="2021.2")

        >>> hosting_cmp = edb1.core_components.get_component_by_name("U100")
        >>> mounted_cmp = edb2.core_components.get_component_by_name("BGA")

        >>> vector, rotation, solder_ball_height = edb1.core_components.get_component_placement_vector(
        ...                                                     mounted_component=mounted_cmp,
        ...                                                     hosting_component=hosting_cmp,
        ...                                                     mounted_component_pin1="A12",
        ...                                                     mounted_component_pin2="A14",
        ...                                                     hosting_component_pin1="A12",
        ...                                                     hosting_component_pin2="A14")
        >>> edb2.stackup.place_in_layout(edb1.active_cell, angle=0.0, offset_x=vector[0],
        ...                              offset_y=vector[1], flipped_stackup=False, place_on_top=True,
        ...                              )
        """
        # if flipped_stackup and place_on_top or (not flipped_stackup and not place_on_top):
        self.adjust_solder_dielectrics()
        if not place_on_top:
            edb.stackup.flip_design()
            place_on_top = True
            if not flipped_stackup:
                self.flip_design()
        elif flipped_stackup:
            self.flip_design()
        edb_cell = edb.active_cell
        _angle = self._edb_value(angle * math.pi / 180.0)
        _offset_x = self._edb_value(offset_x)
        _offset_y = self._edb_value(offset_y)

        if edb_cell.GetName() not in self._pedb.cell_names:
            _dbCell = convert_py_list_to_net_list([edb_cell])
            list_cells = self._pedb.db.CopyCells(_dbCell)
            edb_cell = list_cells[0]
        self._pedb.active_layout.GetCell().SetBlackBox(True)
        cell_inst2 = self._pedb.edb.Cell.Hierarchy.CellInstance.Create(
            edb_cell.GetLayout(), self._pedb.active_layout.GetCell().GetName(), self._pedb.active_layout
        )
        cell_trans = cell_inst2.GetTransform()
        cell_trans.SetRotationValue(_angle)
        cell_trans.SetXOffsetValue(_offset_x)
        cell_trans.SetYOffsetValue(_offset_y)
        cell_trans.SetMirror(flipped_stackup)
        cell_inst2.SetTransform(cell_trans)
        cell_inst2.SetSolveIndependentPreference(False)
        stackup_target = edb_cell.GetLayout().GetLayerCollection()

        if place_on_top:
            cell_inst2.SetPlacementLayer(
                list(stackup_target.Layers(self._pedb.edb.Cell.LayerTypeSet.SignalLayerSet))[0]
            )
        else:
            cell_inst2.SetPlacementLayer(
                list(stackup_target.Layers(self._pedb.edb.Cell.LayerTypeSet.SignalLayerSet))[-1]
            )

        return True

    @pyaedt_function_handler()
    def place_in_layout_3d_placement(
        self,
        edb,
        angle=0.0,
        offset_x=0.0,
        offset_y=0.0,
        flipped_stackup=True,
        place_on_top=True,
        solder_height=0,
    ):
        """Place current Cell into another cell using 3d placement method.
        Flip the current layer stackup of a layout if requested. Transform parameters currently not supported.

        Parameters
        ----------
        edb : Edb
            Cell on which to place the current layout. If None the Cell will be applied on an empty new Cell.
        angle : double, optional
            The rotation angle applied on the design.
        offset_x : double, optional
            The x offset value.
        offset_y : double, optional
            The y offset value.
        flipped_stackup : bool, optional
            Either if the current layout is inverted.
            If `True` and place_on_top is `True` the stackup will be flipped before the merge.
        place_on_top : bool, optional
            Either if place the current layout on Top or Bottom of destination Layout.
        solder_height : float, optional
            Solder Ball or Bumps eight.
            This value will be added to the elevation to align the two layouts.

        Returns
        -------
        bool
            ``True`` when succeed ``False`` if not.

        Examples
        --------
        >>> edb1 = Edb(edbpath=targetfile1,  edbversion="2021.2")
        >>> edb2 = Edb(edbpath=targetfile2, edbversion="2021.2")
        >>> hosting_cmp = edb1.core_components.get_component_by_name("U100")
        >>> mounted_cmp = edb2.core_components.get_component_by_name("BGA")
        >>> edb2.stackup.place_in_layout(edb1.active_cell, angle=0.0, offset_x="1mm",
        ...                                   offset_y="2mm", flipped_stackup=False, place_on_top=True,
        ...                                   )
        """
        _angle = angle * math.pi / 180.0

        if solder_height <= 0:
            if flipped_stackup and not place_on_top or (place_on_top and not flipped_stackup):
                minimum_elevation = None
                layers_from_the_bottom = sorted(self.signal_layers.values(), key=lambda lay: lay.upper_elevation)
                for lay in layers_from_the_bottom:
                    if minimum_elevation is None:
                        minimum_elevation = lay.lower_elevation
                    elif lay.lower_elevation > minimum_elevation:
                        break
                    lay_solder_height = self._get_solder_height(lay.name)
                    solder_height = max(lay_solder_height, solder_height)
                    self._remove_solder_pec(lay.name)
            else:
                maximum_elevation = None
                layers_from_the_top = sorted(self.signal_layers.values(), key=lambda lay: -lay.upper_elevation)
                for lay in layers_from_the_top:
                    if maximum_elevation is None:
                        maximum_elevation = lay.upper_elevation
                    elif lay.upper_elevation < maximum_elevation:
                        break
                    lay_solder_height = self._get_solder_height(lay.name)
                    solder_height = max(lay_solder_height, solder_height)
                    self._remove_solder_pec(lay.name)

        rotation = self._edb_value(0.0)
        if flipped_stackup:
            rotation = self._edb_value(math.pi)

        edb_cell = edb.active_cell
        _offset_x = self._edb_value(offset_x)
        _offset_y = self._edb_value(offset_y)

        if edb_cell.GetName() not in self._pedb.cell_names:
            _dbCell = convert_py_list_to_net_list([edb_cell])
            list_cells = self._pedb.db.CopyCells(_dbCell)
            edb_cell = list_cells[0]
        self._pedb.active_layout.GetCell().SetBlackBox(True)
        cell_inst2 = self._pedb.edb.Cell.Hierarchy.CellInstance.Create(
            edb_cell.GetLayout(), self._pedb.active_layout.GetCell().GetName(), self._pedb.active_layout
        )

        stackup_target = self._pedb.edb.Cell.LayerCollection(edb_cell.GetLayout().GetLayerCollection())
        stackup_source = self._pedb.edb.Cell.LayerCollection(self._pedb.active_layout.GetLayerCollection())

        if place_on_top:
            cell_inst2.SetPlacementLayer(
                list(stackup_target.Layers(self._pedb.edb.Cell.LayerTypeSet.SignalLayerSet))[0]
            )
        else:
            cell_inst2.SetPlacementLayer(
                list(stackup_target.Layers(self._pedb.edb.Cell.LayerTypeSet.SignalLayerSet))[-1]
            )
        cell_inst2.SetIs3DPlacement(True)
        sig_set = self._pedb.edb.Cell.LayerTypeSet.SignalLayerSet
        res = stackup_target.GetTopBottomStackupLayers(sig_set)
        target_top_elevation = res[2]
        target_bottom_elevation = res[4]
        res_s = stackup_source.GetTopBottomStackupLayers(sig_set)
        source_stack_top_elevation = res_s[2]
        source_stack_bot_elevation = res_s[4]

        if place_on_top and flipped_stackup:
            elevation = target_top_elevation + source_stack_top_elevation
        elif place_on_top:
            elevation = target_top_elevation - source_stack_bot_elevation
        elif flipped_stackup:
            elevation = target_bottom_elevation + source_stack_bot_elevation
            solder_height = -solder_height
        else:
            elevation = target_bottom_elevation - source_stack_top_elevation
            solder_height = -solder_height

        h_stackup = self._edb_value(elevation + solder_height)

        zero_data = self._edb_value(0.0)
        one_data = self._edb_value(1.0)
        point3d_t = self._pedb.edb.Geometry.Point3DData(_offset_x, _offset_y, h_stackup)
        point_loc = self._pedb.edb.Geometry.Point3DData(zero_data, zero_data, zero_data)
        point_from = self._pedb.edb.Geometry.Point3DData(one_data, zero_data, zero_data)
        point_to = self._pedb.edb.Geometry.Point3DData(
            self._edb_value(math.cos(_angle)), self._edb_value(-1 * math.sin(_angle)), zero_data
        )
        cell_inst2.Set3DTransformation(point_loc, point_from, point_to, rotation, point3d_t)
        return True

    @pyaedt_function_handler()
    def place_a3dcomp_3d_placement(self, a3dcomp_path, angle=0.0, offset_x=0.0, offset_y=0.0, place_on_top=True):
        """Place a 3D Component into current layout.
         3D Component ports are not visible via EDB. They will be visible after the EDB has been opened in Ansys
         Electronics Desktop as a project.

        Parameters
        ----------
        a3dcomp_path : str
            Path to the 3D Component file (\\*.a3dcomp) to place.
        angle : double, optional
            Clockwise rotation angle applied to the a3dcomp.
        offset_x : double, optional
            The x offset value.
            The default value is ``0.0``.
        offset_y : double, optional
            The y offset value.
            The default value is ``0.0``.
        place_on_top : bool, optional
            Whether to place the 3D Component on the top or the bottom of this layout.
            If ``False`` then the 3D Component will also be flipped over around its X axis.

        Returns
        -------
        bool
            ``True`` if successful and ``False`` if not.

        Examples
        --------
        >>> edb1 = Edb(edbpath=targetfile1,  edbversion="2021.2")
        >>> a3dcomp_path = "connector.a3dcomp"
        >>> edb1.stackup.place_a3dcomp_3d_placement(a3dcomp_path, angle=0.0, offset_x="1mm",
        ...                                   offset_y="2mm", flipped_stackup=False, place_on_top=True,
        ...                                   )
        """
        zero_data = self._edb_value(0.0)
        one_data = self._edb_value(1.0)
        local_origin = self._pedb.edb.Geometry.Point3DData(zero_data, zero_data, zero_data)
        rotation_axis_from = self._pedb.edb.Geometry.Point3DData(one_data, zero_data, zero_data)
        _angle = angle * math.pi / 180.0
        rotation_axis_to = self._pedb.edb.Geometry.Point3DData(
            self._edb_value(math.cos(_angle)), self._edb_value(-1 * math.sin(_angle)), zero_data
        )

        stackup_target = self._pedb.edb.Cell.LayerCollection(self._pedb.active_layout.GetLayerCollection())
        sig_set = self._pedb.edb.Cell.LayerTypeSet.SignalLayerSet
        res = stackup_target.GetTopBottomStackupLayers(sig_set)
        target_top_elevation = res[2]
        target_bottom_elevation = res[4]
        flip_angle = self._edb_value("0deg")
        if place_on_top:
            elevation = target_top_elevation
        else:
            flip_angle = self._edb_value("180deg")
            elevation = target_bottom_elevation
        h_stackup = self._edb_value(elevation)
        location = self._pedb.edb.Geometry.Point3DData(self._edb_value(offset_x), self._edb_value(offset_y), h_stackup)

        mcad_model = self._pedb.edb.McadModel.Create3DComp(self._pedb.active_layout, a3dcomp_path)
        if mcad_model.IsNull():  # pragma: no cover
            logger.error("Failed to create MCAD model from a3dcomp")
            return False

        cell_instance = mcad_model.GetCellInstance()
        if cell_instance.IsNull():  # pragma: no cover
            logger.error("Cell instance of a3dcomp is null")
            return False

        if not cell_instance.SetIs3DPlacement(True):  # pragma: no cover
            logger.error("Failed to set 3D placement on a3dcomp cell instance")
            return False

        if not cell_instance.Set3DTransformation(
            local_origin, rotation_axis_from, rotation_axis_to, flip_angle, location
        ):  # pragma: no cover
            logger.error("Failed to set 3D transform on a3dcomp cell instance")
            return False

        return True

    @pyaedt_function_handler
    def residual_copper_area_per_layer(self):
        """Report residual copper area per layer in percentage.

        Returns
        -------
        dict
            Copper area per layer.

        Examples
        --------
        >>> edb = Edb(edbpath=targetfile1,  edbversion="2021.2")
        >>> edb.stackup.residual_copper_area_per_layer()
        """
        temp_data = {name: 0 for name, _ in self.signal_layers.items()}
        outline_area = 0
        for i in self._pedb.core_primitives.primitives:
            layer_name = i.GetLayer().GetName()
            if layer_name.lower() == "outline":
                if i.area() > outline_area:
                    outline_area = i.area()
            elif layer_name not in temp_data:
                continue
            elif not i.is_void:
                temp_data[layer_name] = temp_data[layer_name] + i.area()
            else:
                pass
        temp_data = {name: area / outline_area * 100 for name, area in temp_data.items()}
        return temp_data


class EdbStackup(object):
    """Manages EDB methods for stackup and material management accessible from the
     ``Edb.core_stackup`` property (deprecated).

    .. deprecated:: 0.6.5
        This class has been deprecated and replaced by the ``Stackup`` class.

    Examples
    --------
    >>> from pyaedt import Edb
    >>> edbapp = Edb("myaedbfolder", edbversion="2021.2")
    >>> edb_stackup = edbapp.core_stackup
    """

    def __init__(self, p_edb):
        self._pedb = p_edb
        self._layer_dict = None

    @property
    def _builder(self):
        """ """
        return self._pedb.builder

    def _get_edb_value(self, value):
        return self._pedb.edb_value(value)

    @property
    def _edb(self):
        """ """
        return self._pedb.edb

    @property
    def _active_layout(self):
        """ """
        return self._pedb.active_layout

    @property
    def _cell(self):
        """ """
        return self._pedb.cell

    @property
    def _db(self):
        """ """
        return self._pedb.db

    @property
    def _logger(self):
        """ """
        return self._pedb.logger

    @property
    def stackup_layers(self):
        """Stackup layers.

        Returns
        -------
        :class:`pyaedt.edb_core.EDBData.EDBLayers`
            Dictionary of stackup layers.
        """
        if not self._layer_dict:
            self._layer_dict = EDBLayers(self)
        return self._layer_dict

    @property
    def signal_layers(self):
        """Dictionary of all signal layers.

        Returns
        -------
        dict[str, :class:`pyaedt.edb_core.EDB_Data.EDBLayer`]
            List of signal layers.
        """
        return self.stackup_layers.signal_layers

    @property
    def layer_types(self):
        """Layer types.

        Returns
        -------
        type
            Types of layers.
        """
        return self._pedb.edb.Cell.LayerType

    @property
    def materials(self):
        """Materials.

        Returns
        -------
        dict
            Dictionary of materials.
        """
        return self._pedb.materials

    @pyaedt_function_handler()
    def create_dielectric(self, name, permittivity=1, loss_tangent=0):
        """Create a dielectric with simple properties.

        .. deprecated:: 0.6.27
           Use :func:`Edb.materials.create_dielectric` function instead.

        Parameters
        ----------
        name : str
            Name of the dielectric.
        permittivity : float, optional
            Permittivity of the dielectric. The default is ``1``.
        loss_tangent : float, optional
            Loss tangent for the material. The default is ``0``.

        Returns
        -------
        type
            Material definition.
        """
        warnings.warn("Use `Edb.materials.create_dielectric` function instead.", DeprecationWarning)
        return self._pedb.materials.add_dielectric_material(name, permittivity=permittivity, loss_tangent=loss_tangent)

    @pyaedt_function_handler()
    def create_conductor(self, name, conductivity=1e6):
        """Create a conductor with simple properties.

        .. deprecated:: 0.6.27
           Use the :func:`Edb.materials.add_conductor_material` function instead.

        Parameters
        ----------
        name : str
            Name of the conductor.
        conductivity : float, optional
            Conductivity of the conductor. The default is ``1e6``.

        Returns
        -------
        :class:`pyaedt.edb_core.materials.Material`
            Material definition.
        """
        warnings.warn("Use `Edb.materials.add_conductor_material` function instead.", DeprecationWarning)

        return self._pedb.materials.add_conductor_material(name, conductivity=conductivity)

    @pyaedt_function_handler()
    def create_debye_material(
        self,
        name,
        relative_permittivity_low,
        relative_permittivity_high,
        loss_tangent_low,
        loss_tangent_high,
        lower_freqency,
        higher_frequency,
    ):
        """Create a dielectric with the Debye model.

        .. deprecated:: 0.6.27
           Use :func:`Edb.materials.add_debye_material` function instead.

        Parameters
        ----------
        name : str
            Name of the dielectric.
        relative_permittivity_low : float
            Relative permittivity of the dielectric at the frequency specified
            for ``lower_frequency``.
        relative_permittivity_high : float
            Relative permittivity of the dielectric at the frequency specified
            for ``higher_frequency``.
        loss_tangent_low : float
            Loss tangent for the material at the frequency specified
            for ``lower_frequency``.
        loss_tangent_high : float
            Loss tangent for the material at the frequency specified
            for ``higher_frequency``.
        lower_freqency : float
            Value for the lower frequency.
        higher_frequency : float
            Value for the higher frequency.

        Returns
        -------
        type
            Material definition.
        """
        warnings.warn("Use `Edb.materials.add_debye_material` function instead.", DeprecationWarning)

        return self._pedb.materials.add_debye_material(
            name=name,
            permittivity_low=relative_permittivity_low,
            permittivity_high=relative_permittivity_high,
            loss_tangent_low=loss_tangent_low,
            loss_tangent_high=loss_tangent_high,
            lower_freqency=lower_freqency,
            higher_frequency=higher_frequency,
        )

    @pyaedt_function_handler()
    def create_multipole_debye_material(
        self,
        name,
        frequencies,
        relative_permittivities,
        loss_tangents,
    ):
        """Create a dielectric with the Multipole Debye model.

        .. deprecated:: 0.6.27
           Use :func:`Edb.materials.add_multipole_debye_material` function instead.

        Parameters
        ----------
        name : str
            Name of the dielectic.
        frequencies : list
            Frequencies in GHz.
        relative_permittivities : list
            Relative permittivities at each frequency.
        loss_tangents : list
            Loss tangents at each frequency.

        Returns
        -------
        type
            Material definition.

        Examples
        --------
        >>> from pyaedt import Edb
        >>> edb = Edb()
        >>> freq = [0, 2, 3, 4, 5, 6]
        >>> rel_perm = [1e9, 1.1e9, 1.2e9, 1.3e9, 1.5e9, 1.6e9]
        >>> loss_tan = [0.025, 0.026, 0.027, 0.028, 0.029, 0.030]
        >>> diel = edb.core_stackup.create_multipole_debye_material("My_MP_Debye", freq, rel_perm, loss_tan)
        """
        warnings.warn("Use `Edb.materials.add_multipole_debye_material` function instead.", DeprecationWarning)

        return self._pedb.materials.add_multipole_debye_material(
            name=name,
            frequencies=frequencies,
            permittivities=relative_permittivities,
            loss_tangents=loss_tangents,
        )

    @pyaedt_function_handler()
    def get_layout_thickness(self):
        """Return the layout thickness.

        .. deprecated:: 0.6.27
           Use :func:`Edb.stackup.get_layout_thickness` function instead.

        Returns
        -------
        float
            The thickness value.
        """
        warnings.warn("Use `Edb.materials.get_layout_thickness` function instead.", DeprecationWarning)

        return self._pedb.stackup.get_layout_thickness()

    @pyaedt_function_handler()
    def duplicate_material(self, material_name, new_material_name):
        """Duplicate a material from the database.
        It duplicates these five properties: ``permittivity``, ``permeability``, ``conductivity``,
        ``dielectriclosstangent``, and ``magneticlosstangent``.

        .. deprecated:: 0.6.27
           Use :func:`Edb.stackup.duplicate` function instead.

        Parameters
        ----------
        material_name : str
            Name of the existing material.
        new_material_name : str
            Name of the new duplicated material.

        Returns
        -------
        EDB material : class: 'Ansys.Ansoft.Edb.Definition.MaterialDef'


        Examples
        --------

        >>> from pyaedt import Edb
        >>> edb_app = Edb()
        >>> my_material = edb_app.core_stackup.duplicate_material("copper", "my_new_copper")

        """
        warnings.warn("Use `Edb.materials.duplicate` function instead.", DeprecationWarning)

        return self._pedb.materials.duplicate(material_name, new_material_name)

    @pyaedt_function_handler
    def material_name_to_id(self, property_name):
        """Convert a material property name to a material property ID.

        .. deprecated:: 0.6.27
           Use :func:`Edb.materials.material_name_to_id` function instead.

        Parameters
        ----------
        property_name : str
            Name of the material property.

        Returns
        -------
        ID of the material property.
        """
        warnings.warn("Use `Edb.materials.material_name_to_id` function instead.", DeprecationWarning)

        return self._pedb.materials.material_name_to_id(property_name)

    @pyaedt_function_handler()
    def get_property_by_material_name(self, property_name, material_name):
        """Get the property of a material. If it is executed in IronPython,
         you must only use the first element of the returned tuple, which is a float.

        .. deprecated:: 0.6.27
           Use :func:`Edb.materials.get_property_by_material_name` function instead.

        Parameters
        ----------
        material_name : str
            Name of the existing material.
        property_name : str
            Name of the material property.
            ``permittivity``
            ``permeability``
            ``conductivity``
            ``dielectric_loss_tangent``
            ``magnetic_loss_tangent``

        Returns
        -------
        float
            The float value of the property.


        Examples
        --------
        >>> from pyaedt import Edb
        >>> edb_app = Edb()
        >>> returned_tuple = edb_app.core_stackup.get_property_by_material_name("conductivity", "copper")
        >>> edb_value = returned_tuple[0]
        >>> float_value = returned_tuple[1]

        """
        warnings.warn("Use `Edb.materials.get_property_by_material_name` function instead.", DeprecationWarning)

        return self._pedb.materials.get_property_by_material_name(property_name, material_name)

    @pyaedt_function_handler()
    def adjust_solder_dielectrics(self):
        """Adjust the stack-up by adding or modifying dielectric layers that contains Solder Balls.
        This method identifies the solder-ball height and adjust the dielectric thickness on top (or bottom) to fit
        the thickness in order to merge another layout.

        .. deprecated:: 0.6.27
           Use :func:`Edb.stackup.adjust_solder_dielectrics` function instead.

        Returns
        -------
        bool
        """
        warnings.warn("Use `Edb.stackup.adjust_solder_dielectrics` function instead.", DeprecationWarning)

        return self._pedb.stackup.adjust_solder_dielectrics()

    @pyaedt_function_handler()
    def place_in_layout(
        self,
        edb,
        angle=0.0,
        offset_x=0.0,
        offset_y=0.0,
        flipped_stackup=True,
        place_on_top=True,
    ):
        """Place current Cell into another cell using layer placement method.
        Flip the current layer stackup of a layout if requested. Transform parameters currently not supported.

        .. deprecated:: 0.6.27
           Use :func:`Edb.stackup.place_in_layout` function instead.

        Parameters
        ----------
        edb : Edb
            Cell on which to place the current layout. If None the Cell will be applied on an empty new Cell.
        angle : double, optional
            The rotation angle applied on the design.
        offset_x : double, optional
            The x offset value.
        offset_y : double, optional
            The y offset value.
        flipped_stackup : bool, optional
            Either if the current layout is inverted.
            If `True` and place_on_top is `True` the stackup will be flipped before the merge.
        place_on_top : bool, optional
            Either if place the current layout on Top or Bottom of destination Layout.

        Returns
        -------
        bool
            ``True`` when succeed ``False`` if not.

        Examples
        --------
        >>> edb1 = Edb(edbpath=targetfile1,  edbversion="2021.2")
        >>> edb2 = Edb(edbpath=targetfile2, edbversion="2021.2")

        >>> hosting_cmp = edb1.core_components.get_component_by_name("U100")
        >>> mounted_cmp = edb2.core_components.get_component_by_name("BGA")

        >>> vector, rotation, solder_ball_height = edb1.core_components.get_component_placement_vector(
        ...                                                     mounted_component=mounted_cmp,
        ...                                                     hosting_component=hosting_cmp,
        ...                                                     mounted_component_pin1="A12",
        ...                                                     mounted_component_pin2="A14",
        ...                                                     hosting_component_pin1="A12",
        ...                                                     hosting_component_pin2="A14")
        >>> edb2.core_stackup.place_in_layout(edb1.active_cell, angle=0.0, offset_x=vector[0],
        ...                                   offset_y=vector[1], flipped_stackup=False, place_on_top=True,
        ...                                   )
        """
        warnings.warn("Use `Edb.stackup.place_in_layout` function instead.", DeprecationWarning)

        return self._pedb.stackup.place_in_layout(
            edb=edb,
            angle=angle,
            offset_x=offset_x,
            offset_y=offset_y,
            flipped_stackup=flipped_stackup,
            place_on_top=place_on_top,
        )

    @pyaedt_function_handler()
    def place_in_layout_3d_placement(
        self,
        edb,
        angle=0.0,
        offset_x=0.0,
        offset_y=0.0,
        flipped_stackup=True,
        place_on_top=True,
        solder_height=0,
    ):
        """Place current Cell into another cell using 3d placement method.
        Flip the current layer stackup of a layout if requested. Transform parameters currently not supported.

        .. deprecated:: 0.6.27
           Use :func:`Edb.stackup.place_in_layout_3d_placement` function instead.

        Parameters
        ----------
        edb : Edb
            Cell on which to place the current layout. If None the Cell will be applied on an empty new Cell.
        angle : double, optional
            The rotation angle applied on the design.
        offset_x : double, optional
            The x offset value.
        offset_y : double, optional
            The y offset value.
        flipped_stackup : bool, optional
            Either if the current layout is inverted.
            If `True` and place_on_top is `True` the stackup will be flipped before the merge.
        place_on_top : bool, optional
            Either if place the current layout on Top or Bottom of destination Layout.
        solder_height : float, optional
            Solder Ball or Bumps eight.
            This value will be added to the elevation to align the two layouts.

        Returns
        -------
        bool
            ``True`` when succeed ``False`` if not.

        Examples
        --------
        >>> edb1 = Edb(edbpath=targetfile1,  edbversion="2021.2")
        >>> edb2 = Edb(edbpath=targetfile2, edbversion="2021.2")
        >>> hosting_cmp = edb1.core_components.get_component_by_name("U100")
        >>> mounted_cmp = edb2.core_components.get_component_by_name("BGA")
        >>> edb2.core_stackup.place_in_layout(edb1.active_cell, angle=0.0, offset_x="1mm",
        ...                                   offset_y="2mm", flipped_stackup=False, place_on_top=True,
        ...                                   )
        """
        warnings.warn("Use `Edb.stackup.place_in_layout_3d_placement` function instead.", DeprecationWarning)

        return self._pedb.stackup.place_in_layout_3d_placement(
            edb=edb,
            angle=angle,
            offset_x=offset_x,
            offset_y=offset_y,
            flipped_stackup=flipped_stackup,
            place_on_top=place_on_top,
            solder_height=solder_height,
        )

    @pyaedt_function_handler()
    def place_a3dcomp_3d_placement(self, a3dcomp_path, angle=0.0, offset_x=0.0, offset_y=0.0, place_on_top=True):
        """Place a 3D Component into current layout.
         3D Component ports are not visible via EDB. They will be visible after the EDB has been opened in Ansys
         Electronics Desktop as a project.

        .. deprecated:: 0.6.27
           Use :func:`Edb.stackup.place_a3dcomp_3d_placement` function instead.

        Parameters
        ----------
        a3dcomp_path : str
            Path to the 3D Component file (\\*.a3dcomp) to place.
        angle : double, optional
            Clockwise rotation angle applied to the a3dcomp.
        offset_x : double, optional
            The x offset value.
            The default value is ``0.0``.
        offset_y : double, optional
            The y offset value.
            The default value is ``0.0``.
        place_on_top : bool, optional
            Whether to place the 3D Component on the top or the bottom of this layout.
            If ``False`` then the 3D Component will also be flipped over around its X axis.

        Returns
        -------
        bool
            ``True`` if successful and ``False`` if not.

        Examples
        --------
        >>> edb1 = Edb(edbpath=targetfile1,  edbversion="2021.2")
        >>> a3dcomp_path = "connector.a3dcomp"
        >>> edb1.core_stackup.place_a3dcomp_3d_placement(a3dcomp_path, angle=0.0, offset_x="1mm",
        ...                                   offset_y="2mm", flipped_stackup=False, place_on_top=True,
        ...                                   )
        """
        warnings.warn("Use `Edb.stackup.place_a3dcomp_3d_placement` function instead.", DeprecationWarning)

        return self._pedb.stackup.place_a3dcomp_3d_placement(
            a3dcomp_path=a3dcomp_path, angle=angle, offset_x=offset_x, offset_y=offset_y, place_on_top=place_on_top
        )

    @pyaedt_function_handler()
    def flip_design(self):
        """Flip the current design of a layout.

        .. deprecated:: 0.6.27
           Use :func:`Edb.stackup.flip_design` function instead.

        Returns
        -------
        bool
            ``True`` when succeed ``False`` if not.

        Examples
        --------
        >>> edb = Edb(edbpath=targetfile,  edbversion="2021.2")
        >>> edb.core_stackup.flip_design()
        >>> edb.save()
        >>> edb.close_edb()
        """
        warnings.warn("Use `Edb.stackup.flip_design` function instead.", DeprecationWarning)

        return self._pedb.stackup.flip_design()

    @pyaedt_function_handler()
    def create_djordjevicsarkar_material(
        self, name, relative_permittivity, loss_tangent, test_frequency, dc_permittivity=None, dc_conductivity=None
    ):
        """Create a Djordjevic_Sarkar dielectric.

        .. deprecated:: 0.6.27
           Use :func:`Edb.materials.add_djordjevicsarkar_material` function instead.

        Parameters
        ----------
        name : str
            Name of the dielectic.
        relative_permittivity : float
            Relative permittivity of the dielectric.
        loss_tangent : float
            Loss tangent for the material.
        test_frequency : float
            Test frequency in GHz for the dielectric.
        dc_permittivity : float, optional
            DC Relative permittivity of the dielectric.
        dc_conductivity : float, optional
            DC Conductivity of the dielectric.
        Returns
        -------
        type
            Material definition.
        """
        warnings.warn("Use `Edb.materials.add_djordjevicsarkar_material` function instead.", DeprecationWarning)

        return self._pedb.materials.add_djordjevicsarkar_material(
            name=name,
            permittivity=relative_permittivity,
            loss_tangent=loss_tangent,
            test_frequency=test_frequency,
            dc_permittivity=dc_permittivity,
            dc_conductivity=dc_conductivity,
        )

    @pyaedt_function_handler()
    def stackup_limits(self, only_metals=False):
        """Retrieve stackup limits.

        .. deprecated:: 0.6.27
           Use :func:`Edb.stackup.stackup_limits` function instead.

        Parameters
        ----------
        only_metals : bool, optional
            Whether to retrieve only metals. The default is ``False``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        warnings.warn("Use `Edb.stackup.stackup_limits` function instead.", DeprecationWarning)

        return self._pedb.stackup.stackup_limits(only_metals=only_metals)

    def create_symmetric_stackup(
        self,
        layer_count,
        inner_layer_thickness="17um",
        outer_layer_thickness="50um",
        dielectric_thickness="100um",
        dielectric_material="FR4_epoxy",
        soldermask=True,
        soldermask_thickness="20um",
    ):
        """Create a symmetric stackup.

        .. deprecated:: 0.6.27
           Use :func:`Edb.stackup.create_symmetric_stackup` function instead.

        Parameters
        ----------
        layer_count : int
            Number of layer count.
        inner_layer_thickness : str, float, optional
            Thickness of inner conductor layer.
        outer_layer_thickness : str, float, optional
            Thickness of outer conductor layer.
        dielectric_thickness : str, float, optional
            Thickness of dielectric layer.
        dielectric_material : str, optional
            Material of dielectric layer.
        soldermask : bool, optional
            Whether to create soldermask layers. The default is``True``.
        soldermask_thickness : str, optional
            Thickness of soldermask layer.
        Returns
        -------
        bool
        """
        warnings.warn("Use `Edb.stackup.create_symmetric_stackup` function instead.", DeprecationWarning)

        return self._pedb.stackup.create_symmetric_stackup(
            layer_count=layer_count,
            inner_layer_thickness=inner_layer_thickness,
            outer_layer_thickness=outer_layer_thickness,
            dielectric_thickness=dielectric_thickness,
            dielectric_material=dielectric_material,
            soldermask=soldermask,
            soldermask_thickness=soldermask_thickness,
        )
