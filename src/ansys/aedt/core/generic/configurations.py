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

import copy
from datetime import datetime
import json
import os
import tempfile

import ansys.aedt.core
from ansys.aedt.core import __version__
from ansys.aedt.core.application.variables import decompose_variable_value
from ansys.aedt.core.generic.data_handlers import _arg2dict
from ansys.aedt.core.generic.errors import GrpcApiError
from ansys.aedt.core.generic.general_methods import generate_unique_folder_name
from ansys.aedt.core.generic.general_methods import generate_unique_name
from ansys.aedt.core.generic.general_methods import open_file
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.generic.general_methods import read_configuration_file
from ansys.aedt.core.generic.general_methods import write_configuration_file
from ansys.aedt.core.generic.load_aedt_file import load_keyword_in_aedt_file
from ansys.aedt.core.modeler.cad.components_3d import UserDefinedComponent
from ansys.aedt.core.modeler.cad.modeler import CoordinateSystem
from ansys.aedt.core.modeler.geometry_operators import GeometryOperators
from ansys.aedt.core.modules.boundary.common import BoundaryObject
from ansys.aedt.core.modules.boundary.common import BoundaryProps
from ansys.aedt.core.modules.boundary.layout_boundary import NativeComponentObject
from ansys.aedt.core.modules.boundary.layout_boundary import NativeComponentPCB
from ansys.aedt.core.modules.design_xploration import SetupOpti
from ansys.aedt.core.modules.design_xploration import SetupParam
from ansys.aedt.core.modules.material_lib import Material
from ansys.aedt.core.modules.mesh import MeshOperation
from ansys.aedt.core.modules.mesh_icepak import MeshRegion
from ansys.aedt.core.modules.mesh_icepak import SubRegion
from jsonschema import exceptions
from jsonschema import validate


def _find_datasets(d, out_list):
    for v in list(d.values()):
        if isinstance(v, dict):
            _find_datasets(v, out_list)
        else:
            a = copy.deepcopy(v)
            val = a
            if str(type(a)) == r"<type 'List'>":
                val = list(a)
            if isinstance(val, list):
                for el in val:
                    try:
                        if "pwl" in el["free_form_value"]:
                            out_list.append(
                                el["free_form_value"][el["free_form_value"].find("$") : el["free_form_value"].find(",")]
                            )
                    except (KeyError, TypeError):
                        pass
            elif isinstance(val, str):
                if "pwl" in val:
                    out_list.append(val[val.find("$") : val.find(",")])


class ConfigurationsOptions(object):
    """Options class for the configurations.
    User can enable or disable import export components."""

    def __init__(self, is_layout=False):
        self._object_mapping_tolerance = 1e-9
        self._export_variables = True
        self._export_setups = True
        self._export_optimizations = True
        self._export_parametrics = True
        self._export_boundaries = True
        self._export_mesh_operations = True
        self._export_coordinate_systems = True
        # self._export_face_coordinate_systems = False
        self._export_materials = True
        self._export_object_properties = True
        self._export_datasets = True
        self._import_datasets = True
        self._import_variables = True
        self._import_setups = True
        self._import_optimizations = True
        self._import_parametrics = True
        self._import_boundaries = True
        self._import_mesh_operations = True
        self._import_coordinate_systems = True
        # self._import_face_coordinate_systems = False
        self._import_materials = True
        self._import_output_variables = True
        self._import_object_properties = True
        self._skip_import_if_exists = False

    @property
    def object_mapping_tolerance(self):
        """Get/Set the tolerance value to be used in the object mapping (used e.g. for boundaries).

        Returns
        -------
        float
        """
        return self._object_mapping_tolerance

    @object_mapping_tolerance.setter
    def object_mapping_tolerance(self, val):
        self._object_mapping_tolerance = val

    @property
    def export_variables(self):
        """Define if the variables have to be exported into json file. Default is `True`.

        Returns
        -------
        bool

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss.configurations.options.export_variables = False  # Disable the variables export
        """
        return self._export_variables

    @export_variables.setter
    def export_variables(self, val):
        self._export_variables = val

    @property
    def export_setups(self):
        """Define if the setups have to be exported to json file. Default is `True`.

        Returns
        -------
        bool

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss.configurations.options.export_setups = False  # Disable the setup export
        """
        return self._export_setups

    @export_setups.setter
    def export_setups(self, val):
        self._export_setups = val

    @property
    def export_optimizations(self):
        """Define if the optimizations have to be exported to json file. Default is `True`.

        Returns
        -------
        bool

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss.configurations.options.export_optimizations = False  # Disable the optimization export
        """
        return self._export_optimizations

    @export_optimizations.setter
    def export_optimizations(self, val):
        self._export_optimizations = val

    @property
    def export_parametrics(self):
        """Define if the parametrics have to be exported to json file. Default is `True`.

        Returns
        -------
        bool

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss.configurations.options.export_parametrics = False  # Disable the parametrics export
        """
        return self._export_parametrics

    @export_parametrics.setter
    def export_parametrics(self, val):
        self._export_parametrics = val

    @property
    def export_boundaries(self):
        """Define if the boundaries have to be exported to json file. Default is `True`.

        Returns
        -------
        bool

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss.configurations.options.export_boundaries = False  # Disable the boundaries export
        """
        return self._export_boundaries

    @export_boundaries.setter
    def export_boundaries(self, val):
        self._export_boundaries = val

    @property
    def import_datasets(self):
        """Define if datasets have to be imported from json file. Default is `True`.

        Returns
        -------
        bool

        """
        return self._import_datasets

    @import_datasets.setter
    def import_datasets(self, val):
        self._import_datasets = val

    @property
    def export_datasets(self):
        """Define if datasets have to be exported to json file. Default is `True`.

        Returns
        -------
        bool

        """
        return self._export_datasets

    @export_datasets.setter
    def export_datasets(self, val):
        self._export_datasets = val

    @property
    def export_mesh_operations(self):
        """Define if the Mesh Operations have to be exported to json file. Default is `True`.

        Returns
        -------
        bool

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss.configurations.options.export_mesh_operations = False  # Disable the mesh operations export
        """
        return self._export_mesh_operations

    @export_mesh_operations.setter
    def export_mesh_operations(self, val):
        self._export_mesh_operations = val

    @property
    def export_coordinate_systems(self):
        """Define if the Coordinate Systems have to be exported to json file. Default is `True`.

        Returns
        -------
        bool

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss.configurations.options.export_coordinate_systems = False  # Disable the coordinate systems export
        """
        return self._export_coordinate_systems

    @export_coordinate_systems.setter
    def export_coordinate_systems(self, val):
        self._export_coordinate_systems = val

    # @property
    # def export_face_coordinate_systems(self):
    #     """Define if the Face Coordinate Systems have to be exported to json file. Default is `True`.
    #
    #     Returns
    #     -------
    #     bool
    #
    #     Examples
    #     --------
    #     >>> from ansys.aedt.core import Hfss
    #     >>> hfss = Hfss()
    #     >>> hfss.configurations.options.export_face_coordinate_systems = False  # Disable the face coordinate export
    #     """
    #     return self._export_face_coordinate_systems
    #
    # @export_face_coordinate_systems.setter
    # def export_face_coordinate_systems(self, val):
    #     self._export_face_coordinate_systems = val

    @property
    def export_materials(self):
        """Define if the materials have to be exported to json file. Default is `True`.

        Returns
        -------
        bool

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss.configurations.options.export_export_materials = False  # Disable the materials export
        """
        return self._export_materials

    @export_materials.setter
    def export_materials(self, val):
        self._export_materials = val

    @property
    def export_object_properties(self):
        """Define if object properties have to be exported to json file. Default is `True`.

        Returns
        -------
        bool

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss.configurations.options.export_object_properties = False  # Disable the object properties export
        """
        return self._export_object_properties

    @export_object_properties.setter
    def export_object_properties(self, val):
        self._export_object_properties = val

    @property
    def import_variables(self):
        """Define if the variablbes have to be imported/created from json file. Default is `True`.

        Returns
        -------
        bool

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss.configurations.options.import_variables = False  # Disable the variables import
        """
        return self._import_variables

    @import_variables.setter
    def import_variables(self, val):
        self._import_variables = val

    @property
    def import_setups(self):
        """Define if the setups have to be imported/created from json file. Default is `True`.

        Returns
        -------
        bool

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss.configurations.options.import_setups = False  # Disable the setup import
        """
        return self._import_setups

    @import_setups.setter
    def import_setups(self, val):
        self._import_setups = val

    @property
    def import_optimizations(self):
        """Define if the optimizations have to be imported/created from json file. Default is `True`.

        Returns
        -------
        bool

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss.configurations.options.import_optimizations = False  # Disable the optimization import
        """
        return self._import_optimizations

    @import_optimizations.setter
    def import_optimizations(self, val):
        self._import_optimizations = val

    @property
    def import_parametrics(self):
        """Define if the parametrics have to be imported/created from json file. Default is `True`.

        Returns
        -------
        bool

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss.configurations.options.import_parametrics = False  # Disable the parametrics import
        """
        return self._import_parametrics

    @import_parametrics.setter
    def import_parametrics(self, val):
        self._import_parametrics = val

    @property
    def import_boundaries(self):
        """Define if the boundaries have to be imported/created from json file. Default is `True`.

        Returns
        -------
        bool

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss.configurations.options.import_boundaries = False  # Disable the boundaries import
        """
        return self._import_boundaries

    @import_boundaries.setter
    def import_boundaries(self, val):
        self._import_boundaries = val

    @property
    def import_mesh_operations(self):
        """Define if the Mesh Operations have to be imported/created from json file. Default is `True`.

        Returns
        -------
        bool

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss.configurations.options.import_mesh_operations = False  # Disable the mesh operations import
        """
        return self._import_mesh_operations

    @import_mesh_operations.setter
    def import_mesh_operations(self, val):
        self._import_mesh_operations = val

    @property
    def import_coordinate_systems(self):
        """Define if the Coordinate Systems have to be imported/created from json file. Default is `True`.

        Returns
        -------
        bool

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss.configurations.options.import_coordinate_systems = False  # Disable the coordinate systems import
        """
        return self._import_coordinate_systems

    @import_coordinate_systems.setter
    def import_coordinate_systems(self, val):
        self._import_coordinate_systems = val

    # @property
    # def import_face_coordinate_systems(self):
    #     """Define if the Face Coordinate Systems have to be imported/created from json file. Default is `True`.
    #
    #     Returns
    #     -------
    #     bool
    #
    #     Examples
    #     --------
    #     >>> from ansys.aedt.core import Hfss
    #     >>> hfss = Hfss()
    #     >>> hfss.configurations.options.import_face_coordinate_systems = False  # Disable the face coordinate import
    #     """
    #     return self._import_face_coordinate_systems
    #
    # @import_face_coordinate_systems.setter
    # def import_face_coordinate_systems(self, val):
    #     self._import_face_coordinate_systems = val

    @property
    def import_materials(self):
        """Define if the materials have to be imported/created from json file. Default is `True`.

        Returns
        -------
        bool

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss.configurations.options.import_import_materials = False  # Disable the materials import
        """
        return self._import_materials

    @property
    def import_output_variables(self):
        """Define if the output variables have to be imported/created from json file. Default is `True`.

        Returns
        -------
        bool

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss.configurations.options.import_output_variables = False  # Disable the materials import
        """
        return self._import_output_variables

    @import_output_variables.setter
    def import_output_variables(self, val):
        self._import_output_variables = val

    @import_materials.setter
    def import_materials(self, val):
        self._import_materials = val

    @property
    def import_object_properties(self):
        """Define if object properties have to be imported/created from json file. Default is `True`.

        Returns
        -------
        bool

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss.configurations.options.import_object_properties = False  # Disable the object properties import
        """
        return self._import_object_properties

    @import_object_properties.setter
    def import_object_properties(self, val):
        self._import_object_properties = val

    @property
    def skip_import_if_exists(self):
        """Define if the existing boundaries or properties will be updated or not. Default is `True`.

        Returns
        -------
        bool

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss.configurations.options.skip_import_if_exists = False  # Disable the update of existing properties
        """
        return self._skip_import_if_exists

    @skip_import_if_exists.setter
    def skip_import_if_exists(self, val):
        self._skip_import_if_exists = val

    @property
    def _is_any_import_set(self):
        """Returns ``True`` if any import setting is set to ``True``. It returns ``False`` otherwise.

        Returns
        -------
        bool
        """
        for prop, value in vars(self).items():
            if prop.startswith("_import_") and value is True:
                return True
        return False

    @pyaedt_function_handler()
    def unset_all_export(self):
        """Set all export properties to `False`.

        Returns
        -------
        bool
        """
        for prop in vars(self):
            if prop.startswith("_export_"):
                setattr(self, prop, False)
        return True

    @pyaedt_function_handler()
    def set_all_export(self):
        """Set all export properties to `True`.

        Returns
        -------
        bool
        """
        for prop in vars(self):
            if prop.startswith("_export_"):
                setattr(self, prop, True)
        return True

    @pyaedt_function_handler()
    def unset_all_import(self):
        """Set all import properties to `False`.

        Returns
        -------
        bool
        """
        for prop in vars(self):
            if prop.startswith("_import_"):
                setattr(self, prop, False)
        return True

    @pyaedt_function_handler()
    def set_all_import(self):
        """Set all import properties to `True`.

        Returns
        -------
        bool
        """
        for prop in vars(self):
            if prop.startswith("_import_"):
                setattr(self, prop, True)
        return True


class ImportResults(object):
    """Contains the results of the import operations.

    Each result can be ``True`` or ``False``.
    """

    def __init__(self):
        self.import_units = None
        self.import_variables = None
        self.import_output_variables = None
        self.import_postprocessing_variables = None
        self.import_setup = None
        self.import_optimizations = None
        self.import_parametrics = None
        self.import_boundaries = None
        self.import_mesh_operations = None
        self.import_coordinate_systems = None
        self.import_face_coordinate_systems = None
        self.import_material_datasets = None
        self.import_materials = None
        self.import_object_properties = None
        self.import_monitor = None
        self.import_datasets = None

    @pyaedt_function_handler()
    def _reset_results(self):
        self.__init__()

    @property
    def global_import_success(self):
        """Returns ``True`` if all imports are successful. It returns ``False`` otherwise.

        Returns
        -------
        bool
        """
        for prop, value in vars(self).items():
            if prop.startswith("import_") and value is False:
                return False
        return True


class Configurations(object):
    """Enables export and import of a JSON configuration file that can be applied to a new or existing design."""

    def __init__(self, app):
        self._app = app
        self.options = ConfigurationsOptions()
        self.results = ImportResults()
        self._schema = None

    @property
    def schema(self):
        """Schema dictionary.

        Returns
        -------
        dict
        """
        if self._schema:
            return self._schema
        pyaedt_installed_path = os.path.dirname(ansys.aedt.core.__file__)

        schema_bytes = None

        config_schema_path = os.path.join(pyaedt_installed_path, "misc", "config.schema.json")

        if os.path.exists(config_schema_path):
            with open(config_schema_path, "rb") as schema:
                schema_bytes = schema.read()

        if schema_bytes:
            # Read the default configuration schema from pyaedt
            schema_string = schema_bytes.decode("utf-8")
            self._schema = json.loads(schema_string)
        else:  # pragma: no cover
            self._app.logger.error("Failed to load configuration schema.")
            self._schema = None
        return self._schema

    @staticmethod
    @pyaedt_function_handler()
    def _map_dict_value(dict_out, key, value):
        dict_out["general"]["object_mapping"][str(key)] = value

    @pyaedt_function_handler()
    def _map_object(self, props, dict_out):
        if "Objects" in props:
            for obj in props["Objects"]:
                if isinstance(obj, int):
                    self._map_dict_value(dict_out, obj, self._app.modeler.objects[obj].name)
        elif "Faces" in props:
            for face in props["Faces"]:
                for obj in self._app.modeler.objects.values():
                    for f in obj.faces:
                        if f.id == face:
                            self._map_dict_value(dict_out, face, [obj.name, f.center])
        elif "Edges" in props:
            for edge in props["Edges"]:
                for obj in self._app.modeler.objects.values():
                    for e in obj.edges:
                        if e.id == edge:
                            self._map_dict_value(dict_out, edge, [obj.name, e.midpoint])

    @pyaedt_function_handler()
    def _convert_objects(self, props, mapping):
        if "Objects" in props:
            new_list = []
            for obj in props["Objects"]:
                try:
                    int(obj)
                    try:
                        new_list.append(mapping[str(obj)])
                    except KeyError:
                        pass
                except ValueError:
                    new_list.append(obj)
            props["Objects"] = new_list
        elif "Faces" in props:
            new_list = []
            for face in props["Faces"]:
                try:
                    f_id = self._app.modeler.oeditor.GetFaceByPosition(
                        [
                            "NAME:FaceParameters",
                            "BodyName:=",
                            mapping[str(face)][0],
                            "XPosition:=",
                            self._app.value_with_units(mapping[str(face)][1][0], self._app.modeler.model_units),
                            "YPosition:=",
                            self._app.value_with_units(mapping[str(face)][1][1], self._app.modeler.model_units),
                            "ZPosition:=",
                            self._app.value_with_units(mapping[str(face)][1][2], self._app.modeler.model_units),
                        ]
                    )
                    new_list.append(f_id)
                except Exception:
                    for f in self._app.modeler[mapping[str(face)][0]].faces:
                        if (
                            GeometryOperators.points_distance(f.center, mapping[str(face)][1])
                            < self.options.object_mapping_tolerance
                        ):
                            new_list.append(f.id)
            props["Faces"] = new_list

        elif "Edges" in props:
            new_list = []
            for edge in props["Edges"]:
                for e in self._app.modeler[mapping[str(edge)][0]].edges:
                    if (
                        GeometryOperators.points_distance(e.midpoint, mapping[str(edge)][1])
                        < self.options.object_mapping_tolerance
                    ):
                        new_list.append(e.id)
            props["Edges"] = new_list

    @pyaedt_function_handler()
    def _update_coordinate_systems(self, name, props):
        for cs in self._app.modeler.coordinate_systems:
            if cs.name == name:
                if not self.options.skip_import_if_exists:
                    cs.props = props
                    cs.update()
                return True
        cs = CoordinateSystem(self._app.modeler, props, name)
        try:
            cs._modeler.oeditor.CreateRelativeCS(cs._orientation, cs._attributes)
            cs.ref_cs = props["Reference CS"]
            cs.update()
            self._app.modeler.coordinate_systems.insert(0, cs)
            self._app.logger.info(f"Coordinate System {name} added.")
            return True
        except Exception:
            self._app.logger.warning(f"Failed to add CS {name} ")
            return False

    # @pyaedt_function_handler()
    # def _update_face_coordinate_systems(self, name, props):
    #     update = False
    #     for cs in self._app.modeler.coordinate_systems:
    #         if cs.name == name:
    #             if not self.options.skip_import_if_exists:
    #                 cs.props = props
    #                 cs.update()
    #             update = True
    #     if update:
    #         return True
    #     cs = FaceCoordinateSystem(self._app.modeler, props, name)
    #     try:
    #         cs._modeler.oeditor.CreateFaceCS(cs._face_parameters, cs._attributes)
    #         cs._modeler.coordinate_systems.append(cs)
    #         self._app.logger.info("Face Coordinate System {} added.".format(name))
    #     except Exception:
    #         self._app.logger.warning("Failed to add CS {} ".format(name))

    @pyaedt_function_handler()
    def _update_object_properties(self, name, val):
        if name in self._app.modeler.object_names:
            arg = ["NAME:AllTabs", ["NAME:Geometry3DAttributeTab", ["NAME:PropServers", name]]]
            arg2 = ["NAME:ChangedProps"]
            if self._app.modeler[name].is3d or self._app.design_type in ["Maxwell 2D", "2D Extractor"]:
                if val.get("Material", None):
                    arg2.append(["NAME:Material", "Value:=", chr(34) + val["Material"] + chr(34)])
                if val.get("SolveInside", None):
                    arg2.append(["NAME:Solve Inside", "Value:=", val["SolveInside"]])
            if val.get("Model", None):
                arg2.append(["NAME:Model", "Value:=", val["Model"]])
            if val.get("Group", None):
                arg2.append(["NAME:Group", "Value:=", val["Group"]])
            if val.get("Transparency", None):
                arg2.append(["NAME:Transparent", "Value:=", val["Transparency"]])
            if val.get("Color", None):
                arg2.append(["NAME:Color", "R:=", val["Color"][0], "G:=", val["Color"][1], "B:=", val["Color"][2]])
            if val.get("CoordinateSystem", None):
                arg2.append(["NAME:Orientation", "Value:=", val["CoordinateSystem"]])
            arg[1].append(arg2)
            try:
                self._app.modeler.oeditor.ChangeProperty(arg)
                return True
            except Exception:
                return False

    @pyaedt_function_handler()
    def _update_boundaries(self, name, props):
        for bound in self._app.boundaries:
            if bound and bound.name == name:
                if not self.options.skip_import_if_exists:
                    bound.props = props
                    bound.update()
                return True
        bound = BoundaryObject(self._app, name, props, props["BoundType"])
        if bound.props.get("Independent", None):
            for b in self._app.boundaries:
                if b.type == "Independent" and b.props.get("ID", 999) == bound.props["Independent"]:
                    bound.auto_update = False
                    bound.props["Independent"] = b.name
                    bound.auto_update = True
        if bound.props.get("CurrentLine", None) and bound.props["CurrentLine"].get("GeometryPosition", None):
            current = bound.props["CurrentLine"]["GeometryPosition"]
            x1 = self._app.value_with_units(float(current[0]["XPosition"]), self._app.modeler.model_units)
            y1 = self._app.value_with_units(float(current[0]["YPosition"]), self._app.modeler.model_units)
            z1 = self._app.value_with_units(float(current[0]["ZPosition"]), self._app.modeler.model_units)
            x2 = self._app.value_with_units(float(current[1]["XPosition"]), self._app.modeler.model_units)
            y2 = self._app.value_with_units(float(current[1]["YPosition"]), self._app.modeler.model_units)
            z2 = self._app.value_with_units(float(current[1]["ZPosition"]), self._app.modeler.model_units)
            p1 = {"Coordinate System": "Global", "Start": [x1, y1, z1], "End": [x2, y2, z2]}
            bound.auto_update = False
            bound.props["CurrentLine"] = BoundaryProps(bound, p1)
            bound.auto_update = True
        if bound.props.get("Modes", None):
            modes = {}
            for k, v in bound.props["Modes"].items():
                p1 = {"ModeNum": v["ModeNum"], "UseIntLine": v["UseIntLine"]}
                if v["UseIntLine"] and v["IntLine"].get("GeometryPosition", None):
                    current = v["IntLine"]["GeometryPosition"]
                    x1 = self._app.value_with_units(float(current[0]["XPosition"]), self._app.modeler.model_units)
                    y1 = self._app.value_with_units(float(current[0]["YPosition"]), self._app.modeler.model_units)
                    z1 = self._app.value_with_units(float(current[0]["ZPosition"]), self._app.modeler.model_units)
                    x2 = self._app.value_with_units(float(current[1]["XPosition"]), self._app.modeler.model_units)
                    y2 = self._app.value_with_units(float(current[1]["YPosition"]), self._app.modeler.model_units)
                    z2 = self._app.value_with_units(float(current[1]["ZPosition"]), self._app.modeler.model_units)
                    p1["IntLine"] = {"Coordinate System": "Global", "Start": [x1, y1, z1], "End": [x2, y2, z2]}
                elif v["UseIntLine"]:
                    p1["IntLine"] = v["IntLine"]
                if v.get("AlignmentGroup", None):
                    p1["AlignmentGroup"] = v["AlignmentGroup"]
                if v.get("CharImp", None):
                    p1["CharImp"] = v["CharImp"]
                if v.get("RenormImp", None):
                    p1["RenormImp"] = v["RenormImp"]
                modes[k] = p1
            bound.auto_update = False
            bound.props["Modes"] = BoundaryProps(bound, modes)
            bound.auto_update = True
        if bound.create():
            self._app._boundaries[bound.name] = bound
            if props["BoundType"] in ["Coil Terminal", "Coil", "CoilTerminal"]:
                winding_name = ""
                for b in self._app.boundaries:
                    if b.props.get("ID", 999) == props.get("ParentBndID", -1):
                        winding_name = b.name
                        break
                if winding_name:
                    self._app.add_winding_coils(winding_name, name)

            self._app.logger.info(f"Boundary Operation {name} added.")
            return True
        else:
            self._app.logger.warning(f"Failed to add Boundary {name} ")
            return False

    @pyaedt_function_handler()
    def _update_mesh_operations(self, name, props):
        for mesh_el in self._app.mesh.meshoperations:
            if mesh_el.name == name:
                if not self.options.skip_import_if_exists:
                    mesh_el.props = props
                    mesh_el.update()
                return True
        bound = MeshOperation(self._app.mesh, name, props, props["Type"])
        if bound.create():
            self._app.mesh.meshoperations.append(bound)
            self._app.logger.info(f"Mesh Operation {name} added.")
            return True
        else:
            self._app.logger.warning(f"Failed to add Mesh {name} ")
            return False

    @pyaedt_function_handler()
    def _update_setup(self, name, props):
        for setup_el in self._app.setups:
            if setup_el.name == name:
                if not self.options.skip_import_if_exists:
                    setup_el.props = props
                    setup_el.update()
                return True
        if self._app.design_type == "Q3D Extractor":
            setup = self._app.create_setup(name, props=props)
        else:
            setup = self._app.create_setup(name, setup_type=props["SetupType"], props=props)
        if setup:
            self._app.logger.info(f"Setup {name} added.")
            return True
        else:
            self._app.logger.warning(f"Failed to add Setup {name} ")
            return False

    @pyaedt_function_handler()
    def _update_optimetrics(self, name, props):
        for setup_el in self._app.optimizations.setups:
            if setup_el.name == name:
                if not self.options.skip_import_if_exists:
                    setup_el.props = props
                    setup_el.update()
                return True
        setup = SetupOpti(self._app, name, dictinputs=props, optim_type=props.get("SetupType", None))
        if setup.create():
            self._app.optimizations.setups.append(setup)
            self._app.logger.info(f"Optim {name} added.")
            return True
        else:
            self._app.logger.warning(f"Failed to add Optim {name} ")
            return False

    @pyaedt_function_handler()
    def _update_parametrics(self, name, props):
        for setup_el in self._app.parametrics.setups:
            if setup_el.name == name:
                if not self.options.skip_import_if_exists:
                    setup_el.props = props
                    setup_el.update()
                return True
        setup = SetupParam(self._app, name, dictinputs=props, optim_type=props.get("SetupType", None))
        if setup.create():
            self._app.optimizations.setups.append(setup)
            self._app.logger.info(f"Optim {name} added.")
            return True
        else:
            self._app.logger.warning(f"Failed to add Optim {name} ")
            return False

    @pyaedt_function_handler()
    def _update_datasets(self, data_dict):
        name = data_dict["Name"]
        is_project_dataset = False
        if name.startswith("$"):
            is_project_dataset = True
        if name not in self._app.project_datasets.keys() or name not in self._app.design_datasets.keys():
            self._app.create_dataset(
                name,
                data_dict["x"],
                data_dict["y"],
                data_dict["z"],
                data_dict["v"],
                is_project_dataset,
                data_dict["xunit"],
                data_dict["yunit"],
                data_dict["zunit"],
                data_dict["vunit"],
            )

    @pyaedt_function_handler()
    def validate(self, config):
        """Validate a configuration file against the schema.

        The default schema can be found in ``pyaedt/misc/config.schema.json``.

        Parameters
        ----------
        config : str, dict
            Configuration as a JSON file or dictionary.

        Returns
        -------
        bool
            ``True`` if the configuration file is valid, ``False`` otherwise.
            If the validation fails, a warning is also written to the logger.
        """

        if isinstance(config, str):
            try:  # Try to parse config as a file
                config_data = read_configuration_file(config)
            except OSError:
                self._app.logger.warning("Unable to parse %s", config)
                return False
        elif isinstance(config, dict):
            config_data = config
        else:
            self._app.logger.warning("Incorrect data type.")
            return False

        try:
            validate(instance=config_data, schema=self.schema)
            return True
        except exceptions.ValidationError as e:  # pragma : no cover
            self._app.logger.warning("Configuration is invalid.")
            self._app.logger.warning("Validation error:" + e.message)
            return False

    @pyaedt_function_handler()
    def import_config(self, config_file, *args):
        """Import configuration settings from a JSON or TOML file and apply it to the current design.

        The sections to be applied are defined with the ``configuration.options`` class.
        The import operation result is saved in the ``configuration.results`` class.

        Parameters
        ----------
        config_file : str
            Full path to json file.

        Returns
        -------
        dict, bool
            Config dictionary.
        """
        if len(args) > 0:  # pragma: no cover
            raise TypeError("import_config expected at most 1 arguments, got %d" % (len(args) + 1))
        self.results._reset_results()

        dict_in = read_configuration_file(config_file)
        if self.options._is_any_import_set:
            try:
                self._app.modeler.model_units = dict_in["general"]["model_units"]
            except KeyError:
                self.results.import_units = False
            else:
                self.results.import_units = True

        if self.options.import_variables:
            try:
                for k, v in dict_in["general"]["variables"].items():
                    self._app.variable_manager.set_variable(k, v)
            except KeyError:
                self.results.import_variables = False
            else:
                self.results.import_variables = True
            try:
                for k, v in dict_in["general"]["postprocessing_variables"].items():
                    self._app.variable_manager.set_variable(k, v, is_post_processing=True)
            except KeyError:
                self.results.import_postprocessing_variables = False
            else:
                self.results.import_postprocessing_variables = True

        if self.options.import_materials and dict_in.get("material datasets", None):
            self.results.import_datasets = True
            for el, val in dict_in["material datasets"].items():
                numcol = len(val["Coordinates"]["DimUnits"])
                xunit = val["Coordinates"]["DimUnits"][0]
                yunit = val["Coordinates"]["DimUnits"][1]
                zunit = ""

                new_list = [
                    val["Coordinates"]["Points"][i : i + numcol]
                    for i in range(0, len(val["Coordinates"]["Points"]), numcol)
                ]
                xval = new_list[0]
                yval = new_list[1]
                zval = None
                if numcol > 2:
                    zunit = val["Coordinates"]["DimUnits"][2]
                    zval = new_list[2]
                if not self._app.create_dataset(el[1:], x=xval, y=yval, z=zval, x_unit=xunit, y_unit=yunit):
                    self.results.import_material_datasets = False

        if self.options.import_materials and dict_in.get("materials", None):
            self.results.import_materials = True
            for el, val in dict_in["materials"].items():
                if self._app.materials.exists_material(el):
                    newname = generate_unique_name(el)
                    self._app.logger.warning("Material %s already exists. Renaming to %s", el, newname)
                else:
                    newname = el
                newmat = Material(self._app, el, val, material_update=True)
                if newmat:
                    self._app.materials.material_keys[newname] = newmat
                else:  # pragma: no cover
                    self.results.import_materials = False

        if self.options.import_coordinate_systems and dict_in.get("coordinatesystems", None):
            self.results.import_coordinate_systems = True
            for name, props in dict_in["coordinatesystems"].items():
                if not self._update_coordinate_systems(name, props):  # pragma: no cover
                    self.results.import_coordinate_systems = False
        # Only set global CS in the appropriate context.
        if self._app.design_type not in [
            "HFSS 3D Layout Design",
            "HFSS3DLayout",
            "RMxprt",
            "Twin Builder",
            "Circuit Design",
        ]:
            self._app.modeler.set_working_coordinate_system("Global")

        if self.options.import_mesh_operations and dict_in.get("mesh", None):
            self.results.import_mesh_operations = True
            for name, props in dict_in["mesh"].items():
                self._convert_objects(props, dict_in["general"]["object_mapping"])
                if not self._update_mesh_operations(name, props):
                    self.results.import_mesh_operations = False

        if self.options.import_object_properties and dict_in.get("objects", None):
            self.results.import_object_properties = True
            for obj, val in dict_in["objects"].items():
                if not self._update_object_properties(obj, val):
                    self.results.import_object_properties = False
            self._app.logger.info("Object Properties updated.")

        if self.options.import_datasets and dict_in.get("datasets", None):
            self.results.import_datasets = True
            if not isinstance(dict_in["datasets"], list):  # backward compatibility
                dataset_list = []
                for k, v in dict_in["datasets"].items():
                    v["Name"] = k
                    dataset_list.append(v)
                dict_in["datasets"] = dataset_list
            for dataset in dict_in["datasets"]:
                self._update_datasets(dataset)

        if self.options.import_boundaries and dict_in.get("boundaries", None):
            self.results.import_boundaries = True
            sort_order = sorted(dict_in["boundaries"], key=lambda x: dict_in["boundaries"][x].get("ID", 999))
            for name in sort_order:
                self._convert_objects(dict_in["boundaries"][name], dict_in["general"]["object_mapping"])
                if not self._update_boundaries(name, dict_in["boundaries"][name]):
                    self.results.import_boundaries = False

        if self.options.import_setups and dict_in.get("setups", None):
            self.results.import_setup = True
            for setup, props in dict_in["setups"].items():
                if not self._update_setup(setup, props):
                    self.results.import_setup = False

        if self.options.import_output_variables:
            try:
                for k, v in dict_in["general"]["output_variables"].items():
                    self._app.create_output_variable(k, v)
            except KeyError:
                self.results.import_variables = False
            else:
                self.results.import_variables = True

        if self.options.import_optimizations and dict_in.get("optimizations", None):
            self.results.import_optimizations = True
            for setup, props in dict_in["optimizations"].items():
                if not self._update_optimetrics(setup, props):
                    self.results.import_optimizations = False

        if self.options.import_parametrics and dict_in.get("parametrics", None):
            self.results.import_parametrics = True
            for setup, props in dict_in["parametrics"].items():
                if not self._update_parametrics(setup, props):
                    self.results.import_parametrics = False
        return dict_in

    @pyaedt_function_handler()
    def _export_general(self, dict_out):
        dict_out["general"] = {}
        dict_out["general"]["pyaedt_version"] = __version__
        dict_out["general"]["model_units"] = self._app.modeler.model_units
        dict_out["general"]["design_name"] = self._app.design_name
        dict_out["general"]["date"] = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
        dict_out["general"]["object_mapping"] = {}
        dict_out["general"]["output_variables"] = {}
        if list(self._app.output_variables):
            oo_out = os.path.join(tempfile.gettempdir(), generate_unique_name("oo") + ".txt")
            self._app.ooutput_variable.ExportOutputVariables(oo_out)
            with open_file(oo_out, "r") as f:
                lines = f.readlines()
                for line in lines:
                    line_split = line.split(" ")
                    try:
                        dict_out["general"]["output_variables"][line_split[0]] = line.split("'")[1]
                    except IndexError:
                        pass

    @pyaedt_function_handler()
    def _export_variables(self, dict_out):
        dict_out["general"]["variables"] = {}
        dict_out["general"]["postprocessing_variables"] = {}
        post_vars = self._app.variable_manager.post_processing_variables
        for k, v in self._app.variable_manager.independent_variables.items():
            if k not in post_vars:
                dict_out["general"]["variables"][k] = v.evaluated_value
        for k, v in self._app.variable_manager.dependent_variables.items():
            if k not in post_vars:
                dict_out["general"]["variables"][k] = v.expression
        for k, v in post_vars.items():
            try:
                dict_out["general"]["postprocessing_variables"][k] = v.expression
            except AttributeError:
                dict_out["general"]["postprocessing_variables"][k] = v.evaluated_value

    @pyaedt_function_handler()
    def _export_setups(self, dict_out):
        if self._app.setups:
            dict_out["setups"] = {}
            for setup in self._app.setups:
                legacy_update = setup.auto_update
                setup.auto_update = False
                dict_out["setups"][setup.name] = setup.props
                dict_out["setups"][setup.name]["SetupType"] = setup.setuptype
                if setup.sweeps:
                    for sweep in setup.sweeps:
                        dict_out["setups"][setup.name][sweep.name] = sweep.props
                setup.auto_update = legacy_update

    @pyaedt_function_handler()
    def _export_optimizations(self, dict_out):
        if self._app.optimizations.setups:
            dict_out["optimizations"] = {}
            for setup in self._app.optimizations.setups:
                legacy_update = setup.auto_update
                setup.auto_update = False
                dict_out["optimizations"][setup.name] = dict(setup.props)
                dict_out["optimizations"][setup.name]["SetupType"] = setup.soltype
                setup.auto_update = legacy_update

    @pyaedt_function_handler()
    def _export_parametrics(self, dict_out):
        if self._app.parametrics.setups:
            dict_out["parametrics"] = {}
            for setup in self._app.parametrics.setups:
                legacy_update = setup.auto_update
                setup.auto_update = False
                dict_out["parametrics"][setup.name] = dict(setup.props)
                dict_out["parametrics"][setup.name]["SetupType"] = setup.soltype
                setup.auto_update = legacy_update

    @pyaedt_function_handler()
    def _export_boundaries(self, dict_out):
        if self._app.boundaries:
            dict_out["boundaries"] = {}
            for boundary in self._app.boundaries:
                legacy_update = boundary.auto_update
                boundary.auto_update = False
                dict_out["boundaries"][boundary.name] = dict(boundary.props)
                if not boundary.props.get("BoundType", None):
                    dict_out["boundaries"][boundary.name]["BoundType"] = boundary.type
                self._map_object(boundary.props, dict_out)
                boundary.auto_update = legacy_update

    @pyaedt_function_handler()
    def _export_coordinate_systems(self, dict_out):
        if self._app.modeler.coordinate_systems:
            dict_out["coordinatesystems"] = {}
            for cs in self._app.modeler.coordinate_systems:
                if isinstance(cs, CoordinateSystem):
                    legacy_update = cs.auto_update
                    cs.auto_update = False
                    if cs.props:
                        dict_out["coordinatesystems"][cs.name] = copy.deepcopy(dict(cs.props))
                        dict_out["coordinatesystems"][cs.name]["Reference CS"] = cs.ref_cs
                    cs.auto_update = legacy_update

    # @pyaedt_function_handler()
    # def _export_face_coordinate_systems(self, dict_out):
    #     if self._app.modeler.coordinate_systems:
    #         dict_out["facecoordinatesystems"] = {}
    #         for cs in self._app.modeler.coordinate_systems:
    #             if isinstance(cs, FaceCoordinateSystem):
    #                 dict_out["facecoordinatesystems"][cs.name] = cs.props

    @pyaedt_function_handler()
    def _export_objects_properties(self, dict_out):
        dict_out["objects"] = {}
        for val in self._app.modeler.objects.values():
            dict_out["objects"][val.name] = {}
            if self._app.modeler[val.name].is3d or self._app.design_type in ["Maxwell 2D", "2D Extractor"]:
                dict_out["objects"][val.name]["Material"] = val.material_name
                dict_out["objects"][val.name]["SolveInside"] = val.solve_inside
            dict_out["objects"][val.name]["Model"] = val.model
            dict_out["objects"][val.name]["Group"] = val.group_name
            dict_out["objects"][val.name]["Transparency"] = val.transparency
            dict_out["objects"][val.name]["Color"] = val.color
            dict_out["objects"][val.name]["CoordinateSystem"] = val.part_coordinate_system

    @pyaedt_function_handler()
    def _export_object_properties(self, dict_out):
        self._export_objects_properties(dict_out)

    @pyaedt_function_handler()
    def _export_mesh_operations(self, dict_out):
        if self._app.mesh.meshoperations:
            dict_out["mesh"] = {}
            for mesh in self._app.mesh.meshoperations:
                dict_out["mesh"][mesh.name] = copy.deepcopy(dict(mesh.props))
                self._map_object(mesh.props, dict_out)

    @pyaedt_function_handler()
    def _export_datasets(self, dict_out):
        if self._app.project_datasets or self._app.design_datasets:
            if dict_out.get("datasets", None) is None:
                dict_out["datasets"] = []
            for dataset_dict in [self._app.project_datasets, self._app.design_datasets]:
                for k, obj in dataset_dict.items():
                    if k not in dict_out.get("material datasets", []):
                        dict_out["datasets"].append(
                            {
                                "Name": k,
                                "v": obj.v,
                                "vunit": obj.vunit,
                                "x": obj.x,
                                "xunit": obj.xunit,
                                "y": obj.y,
                                "yunit": obj.yunit,
                                "z": obj.z,
                                "zunit": obj.zunit,
                            }
                        )

    @pyaedt_function_handler()
    def _export_monitor(self, dict_out):
        dict_monitors = []
        native_parts = [
            part.name
            for udc_name, udc in self._app.modeler.user_defined_components.items()
            for part_name, part in udc.parts.items()
            if self._app.modeler.user_defined_components[udc_name].definition_name in self._app.native_components
        ]
        if self._app.monitor.all_monitors != {}:
            for mon_name in self._app.monitor.all_monitors:
                dict_monitor = {
                    key: val
                    for key, val in self._app.monitor.all_monitors[mon_name].properties.items()
                    if key not in ["Name", "Object"]
                }
                dict_monitor["Name"] = mon_name
                if dict_monitor["Geometry Assignment"] in native_parts:
                    dict_monitor["Native Assignment"] = [
                        name
                        for name, dict_comp in self._app.modeler.user_defined_components.items()
                        if dict_monitor["Geometry Assignment"]
                        in [part.name for part_id, part in dict_comp.parts.items()]
                    ][0]
                    if dict_monitor["Type"] == "Face":
                        dict_monitor["Area Assignment"] = self._app.modeler.get_face_area(dict_monitor["ID"])
                    elif dict_monitor["Type"] == "Surface":
                        dict_monitor["Area Assignment"] = self._app.modeler.get_face_area(
                            self._app.modeler.get_object_from_name(dict_monitor["ID"]).faces[0].id
                        )
                    elif dict_monitor["Type"] == "Object":
                        bb = self._app.modeler.get_object_from_name([dict_monitor["ID"]][0]).bounding_box
                        dict_monitor["Location"] = [(bb[i] + bb[i + 3]) / 2 for i in range(3)]
                        dict_monitor["Volume Assignment"] = self._app.modeler.get_object_from_name(
                            dict_monitor["ID"]
                        ).volume
                dict_monitors.append(dict_monitor)
        dict_out["monitors"] = dict_monitors

    @pyaedt_function_handler()
    def _export_materials(self, dict_out):
        output_dict = {}
        for el, val in self._app.materials.material_keys.items():
            output_dict[val.name] = copy.deepcopy(val._props)
        out_list = []
        _find_datasets(output_dict, out_list)
        datasets = {}
        for ds in out_list:
            if ds in list(self._app.project_datasets.keys()):
                d = self._app.project_datasets[ds]
                if d.z:
                    units = [d.xunit, d.yunit, d.zunit]
                    points = [val for tup in zip(d.x, d.y, d.z) for val in tup]
                else:
                    units = [d.xunit, d.yunit]
                    points = [val for tup in zip(d.x, d.y) for val in tup]
                datasets[ds] = {
                    "Coordinates": {
                        "DimUnits": units,
                        "Points": points,
                    }
                }

        dict_out["materials"] = output_dict
        if datasets:
            dict_out["material datasets"] = datasets

    @pyaedt_function_handler()
    def export_config(self, config_file=None, overwrite=False):
        """Export current design properties to a JSON or TOML file.

        The sections to be exported are defined with ``configuration.options`` class.

        Parameters
        ----------
        config_file : str, optional
            Full path to json file. If ``None``, then the config file will be saved in working directory.
        overwrite : bool, optional
            If ``True`` the json file will be overwritten if already existing.
            If ``False`` and the version is compatible, the data in the existing file will be updated.
            Default is ``False``.

        Returns
        -------
        str
            Exported config file.
        """
        if not config_file:
            config_file = os.path.join(
                self._app.working_directory, generate_unique_name(self._app.design_name) + ".json"
            )
        dict_out = {}
        self._export_general(dict_out)
        for key, value in vars(self.options).items():  # Retrieve the dict() from the object.
            if key.startswith("_export_") and value:
                getattr(self, key)(dict_out)  # Call private export method to update dict_out.

        # update the json if it exists already

        if os.path.exists(config_file) and not overwrite:
            dict_in = read_configuration_file(config_file)
            try:  # TODO: Allow import of config created with other versions of pyaedt.
                if dict_in["general"]["pyaedt_version"] == __version__:
                    for k, v in dict_in.items():
                        if k not in dict_out:
                            dict_out[k] = v
                        elif isinstance(v, dict):
                            for i, j in v.items():
                                if i not in dict_out[k]:
                                    dict_out[k][i] = j
            except KeyError as e:
                self._app.logger.error(str(e))

        # write the updated dict to file
        if write_configuration_file(dict_out, config_file):
            self._app.logger.info(f"Json file {config_file} created correctly.")
            return config_file
        self._app.logger.error(f"Error creating json file {config_file}.")
        return False


class ConfigurationOptionsIcepak(ConfigurationsOptions):
    def __init__(self, app):
        ConfigurationsOptions.__init__(self)
        self._export_monitor = True
        self._import_monitor = True
        self._export_native_components = True
        self._import_native_components = True

    @property
    def import_monitor(self):
        return self._import_monitor

    @import_monitor.setter
    def import_monitor(self, val):
        self._import_monitor = val

    @property
    def export_monitor(self):
        return self._export_monitor

    @export_monitor.setter
    def export_monitor(self, val):
        self._export_monitor = val

    @property
    def import_native_components(self):
        return self._import_native_components

    @import_native_components.setter
    def import_native_components(self, val):
        self._import_native_components = val

    @property
    def export_native_components(self):
        return self._export_native_components

    @export_native_components.setter
    def export_native_components(self, val):
        self._export_native_components = val


class ConfigurationOptions3DLayout(ConfigurationsOptions):
    def __init__(self, app):
        ConfigurationsOptions.__init__(self)
        self._export_mesh_operations = False
        self._export_coordinate_systems = False
        self._export_boundaries = False
        self._export_object_properties = False
        self._import_mesh_operations = False
        self._import_coordinate_systems = False
        self._import_boundaries = False
        self._import_object_properties = False


class Configurations3DLayout(Configurations):
    """Enables export and import configuration options to be applied to a new or existing 3DLayout design."""

    def __init__(self, app):
        Configurations.__init__(self, app)
        self.options = ConfigurationOptions3DLayout(app)


class ConfigurationsIcepak(Configurations):
    """Enables export and import configuration options to be applied on a new or existing design."""

    def __init__(self, app):
        Configurations.__init__(self, app)
        self.options = ConfigurationOptionsIcepak(app)

    @pyaedt_function_handler()
    def _update_object_properties(self, name, val):
        if name in self._app.modeler.object_names:
            arg = ["NAME:AllTabs", ["NAME:Geometry3DAttributeTab", ["NAME:PropServers", name]]]
            arg2 = ["NAME:ChangedProps"]
            if val.get("Material", None):
                arg2.append(["NAME:Material", "Value:=", chr(34) + val["Material"] + chr(34)])
            if val.get("SolveInside", None):
                arg2.append(["NAME:Solve Inside", "Value:=", val["SolveInside"]])
            try:
                arg2.append(
                    [
                        "NAME:Surface Material",
                        "Value:=",
                        chr(34) + val.get("SurfaceMaterial") + chr(34),
                    ]
                )
            except TypeError:
                arg2.append(
                    [
                        "NAME:Surface Material",
                        "Value:=",
                        chr(34) + "Steel-oxidised-surface" + chr(34),
                    ]
                )
            if val.get("Model", None):
                arg2.append(["NAME:Model", "Value:=", val["Model"]])
            if val.get("Group", None):
                arg2.append(["NAME:Group", "Value:=", val["Group"]])
            if val.get("Transparency", None):
                arg2.append(["NAME:Transparent", "Value:=", val["Transparency"]])
            if val.get("Color", None):
                arg2.append(["NAME:Color", "R:=", val["Color"][0], "G:=", val["Color"][1], "B:=", val["Color"][1]])
            if val.get("CoordinateSystem", None):
                arg2.append(["NAME:Orientation", "Value:=", val["CoordinateSystem"]])
            arg[1].append(arg2)
            try:
                self._app.modeler.oeditor.ChangeProperty(arg)
                return True
            except Exception:
                return False

    @pyaedt_function_handler()
    def _update_mesh_operations(self, name, props):
        if name == "Settings":
            if not self.options.skip_import_if_exists:
                for el in props:
                    if el in self._app.mesh.global_mesh_region.__dict__:
                        self._app.mesh.global_mesh_region.__dict__[el] = props[el]
                return self._app.mesh.global_mesh_region.update()
        for mesh_el in self._app.mesh.meshregions:
            if mesh_el.name == name:
                if not self.options.skip_import_if_exists:
                    for el in props:
                        if el in mesh_el.__dict__:
                            mesh_el.__dict__[el] = props[el]
                    return mesh_el.update()
        try:
            if self._app.settings.aedt_version < "2024.1":
                objs = props.get("Objects", []) + props.get("Submodels", [])
            else:
                subregion = SubRegion(self._app, props["_subregion_information"]["parts"])
                subregion.padding_values = props["_subregion_information"]["pad_vals"]
                subregion.padding_types = props["_subregion_information"]["pad_types"]
                objs = subregion.name
            bound = MeshRegion(app=self._app, name=name, objects=objs)
            bound.manual_settings = props["UserSpecifiedSettings"]
            for el in props:
                if el in bound.settings:
                    bound.settings[el] = props[el]
            self._app.mesh.meshregions.append(bound)
            self._app.logger.info(f"Mesh Operation {name} added.")
        except GrpcApiError:
            self._app.logger.warning(f"Failed to add mesh {name} ")
        return True

    @pyaedt_function_handler()
    def _export_objects_properties(self, dict_out):
        dict_out["objects"] = {}
        udc_parts_id = []
        if hasattr(self._app.modeler, "user_defined_components"):
            self._app.modeler.refresh_all_ids()
            udc_parts_id = [part for _, uc in self._app.modeler.user_defined_components.items() for part in uc.parts]
        for val in self._app.modeler.objects.values():
            if val.id in udc_parts_id or val.history().command == "CreateSubRegion":
                continue
            dict_out["objects"][val.name] = {}
            dict_out["objects"][val.name]["SurfaceMaterial"] = val.surface_material_name
            dict_out["objects"][val.name]["Material"] = val.material_name
            dict_out["objects"][val.name]["SolveInside"] = val.solve_inside
            dict_out["objects"][val.name]["Model"] = val.model
            dict_out["objects"][val.name]["Group"] = val.group_name
            dict_out["objects"][val.name]["Transparency"] = val.transparency
            dict_out["objects"][val.name]["Color"] = val.color
            dict_out["objects"][val.name]["CoordinateSystem"] = val.part_coordinate_system

    @pyaedt_function_handler()
    def _export_mesh_operations(self, dict_out):
        dict_out["mesh"] = {}
        args = ["NAME:Settings"]
        args += self._app.mesh.global_mesh_region.settings.parse_settings_as_args()
        mop = {}
        _arg2dict(args, mop)
        dict_out["mesh"]["Settings"] = mop["Settings"]
        if self._app.mesh.meshregions:
            for mesh in self._app.mesh.meshregions:
                if mesh.name in ["Settings", "Global"]:
                    args = ["NAME:Settings"]
                else:
                    args = ["NAME:" + mesh.name, "Enable:=", mesh.Enable]
                args += mesh.settings.parse_settings_as_args()
                if mesh.name not in ["Settings", "Global"]:
                    args += getattr(mesh, "_parse_assignment_value")()
                args += ["UserSpecifiedSettings:=", not mesh.manual_settings]
                mop = {}
                _arg2dict(args, mop)
                if (
                    mesh.name not in ["Settings", "Global"]
                    and self._app.modeler[args[-3][0]].history().command == "CreateSubRegion"
                ):
                    mop[mesh.name]["_subregion_information"] = {
                        "pad_vals": mesh.assignment.padding_values,
                        "pad_types": mesh.assignment.padding_types,
                        "parts": list(mesh.assignment.parts.keys()),
                    }
                if mesh.name in mop:
                    dict_out["mesh"][mesh.name] = mop[mesh.name]
                self._map_object(mop, dict_out)

    @pyaedt_function_handler()
    def update_monitor(self, m_case, m_object, m_quantity, m_name):
        """Generic method for inserting monitor object

        Parameters
        ----------
        m_case : str
            Type of monitored geometry object. "Point", "Face", "Vertex", "Surface" or "Object".
        m_object : lost or str or int
            Name or id (or list of these) of the geometry object being monitored.
        m_quantity : list or str
            Name or list of names of the quantity being monitored.
        m_name : str
            Name of the monitor object.

        Returns
        -------
        bool
            ``True`` if successful.
        """
        if m_case == "Point":
            self._app.monitor.assign_point_monitor(m_object, monitor_quantity=m_quantity, monitor_name=m_name)
        elif m_case == "Face":
            self._app.monitor.assign_face_monitor(m_object, monitor_quantity=m_quantity, monitor_name=m_name)
        elif m_case == "Vertex":
            self._app.monitor.assign_point_monitor_to_vertex(m_object, monitor_quantity=m_quantity, monitor_name=m_name)
        elif m_case == "Surface":
            self._app.monitor.assign_surface_monitor(m_object, monitor_quantity=m_quantity, monitor_name=m_name)
        elif m_case == "Object":
            self._app.monitor.assign_point_monitor_in_object(m_object, monitor_quantity=m_quantity, monitor_name=m_name)
        return True

    @pyaedt_function_handler()
    def _monitor_assignment_finder(self, dict_in, monitor_obj, exclude_set):
        idx = dict_in["monitors"].index(monitor_obj)
        if monitor_obj.get("Native Assignment", None):
            objects_to_check = [obj for _, obj in self._app.modeler.objects.items()]
            objects_to_check = list(set(objects_to_check) - exclude_set)
            if monitor_obj["Type"] == "Face":
                for obj in objects_to_check:
                    for f in obj.faces:
                        if (
                            GeometryOperators.v_norm(GeometryOperators.v_sub(f.center, monitor_obj["Location"]))
                            <= 1e-12
                            and abs(f.area - monitor_obj["Area Assignment"]) <= 1e-12
                        ):
                            monitor_obj["ID"] = f.id
                            dict_in["monitors"][idx] = monitor_obj
                            return
            elif monitor_obj["Type"] == "Surface":
                for obj in objects_to_check:
                    if len(obj.faces) == 1:
                        for f in obj.faces:
                            if (
                                GeometryOperators.v_norm(GeometryOperators.v_sub(f.center, monitor_obj["Location"]))
                                <= 1e-12
                                and abs(f.area - monitor_obj["Area Assignment"]) <= 1e-12
                            ):
                                monitor_obj["ID"] = obj.name
                                dict_in["monitors"][idx] = monitor_obj
                                return
            elif monitor_obj["Type"] == "Object":
                for obj in objects_to_check:
                    bb = obj.bounding_box
                    if (
                        GeometryOperators.v_norm(
                            GeometryOperators.v_sub(
                                [(bb[i] + bb[i + 3]) / 2 for i in range(3)], monitor_obj["Location"]
                            )
                        )
                        <= 1e-12
                        and abs(obj.volume - monitor_obj["Volume Assignment"]) <= 1e-12
                    ):
                        monitor_obj["ID"] = obj.id
                        dict_in["monitors"][idx] = monitor_obj
                        return
            elif monitor_obj["Type"] == "Vertex":
                for obj in objects_to_check:
                    for v in obj.vertices:
                        if (
                            GeometryOperators.v_norm(GeometryOperators.v_sub(v.position, monitor_obj["Location"]))
                            <= 1e-12
                        ):
                            monitor_obj["ID"] = v.id
                            dict_in["monitors"][idx] = monitor_obj
                            return

    @pyaedt_function_handler()
    def import_config(self, config_file, *args):
        """Import configuration settings from a JSON or TOML file and apply it to the current design.

        The sections to be applied are defined with ``configuration.options`` class.
        The import operation result is saved in the ``configuration.results`` class.

        Parameters
        ----------
        config_file : str
            Full path to json file.
        *args : set, optional
            Name of objects to ignore for monitor assignment.

        Returns
        -------
        dict, bool
            Config dictionary.
        """
        if len(args) == 0:
            exclude_set = set()
        elif len(args) == 1:
            exclude_set = args[0]
        else:  # pragma: no cover
            raise TypeError("import_config expected at most 2 arguments, got %d" % (len(args) + 1))
        dict_in = read_configuration_file(config_file)
        self.results._reset_results()

        if self.options.import_native_components and dict_in.get("native components", None):
            result_coordinate_systems = True
            add_cs = list(dict_in["coordinatesystems"].keys())
            available_cs = ["Global"] + [cs.name for cs in self._app.modeler.coordinate_systems]
            i = 0
            while add_cs:
                if dict_in["coordinatesystems"][add_cs[i]]["Reference CS"] in available_cs:
                    if not self._update_coordinate_systems(
                        add_cs[i], dict_in["coordinatesystems"][add_cs[i]]
                    ):  # pragma: no cover
                        result_coordinate_systems = False
                    available_cs.append(add_cs[i])
                    add_cs.pop(i)
                    i = 0
                else:
                    i += 1
            self.options.import_coordinate_systems = False
            result_native_component = True
            for component_name, component_dict in dict_in["native components"].items():
                if not self._update_native_components(component_name, component_dict):  # pragma: no cover
                    result_native_component = False

        dict_in = Configurations.import_config(self, config_file)
        if self.options.import_monitor and dict_in.get("monitor", None):  # backward compatibility
            dict_in["monitors"] = dict_in.pop("monitor")
        if self.options.import_monitor and dict_in.get("monitors", None):
            if not isinstance(dict_in["monitors"], list):  # backward compatibility
                mon_list = []
                for k, v in dict_in["monitors"].items():
                    v["Name"] = k
                    mon_list.append(v)
                dict_in["monitors"] = mon_list
            self.results.import_monitor = True
            for monitor_obj in dict_in["monitors"]:
                self._monitor_assignment_finder(dict_in, monitor_obj, exclude_set)
                m_type = monitor_obj["Type"]
                m_obj = monitor_obj["ID"]
                if m_type == "Point":
                    m_obj = monitor_obj["Location"]
                if not self.update_monitor(
                    m_type, m_obj, monitor_obj["Quantity"], monitor_obj["Name"]
                ):  # pragma: no cover
                    self.results.import_monitor = False
        try:
            self.results.import_native_components = result_native_component
            self.results.import_coordinate_systems = result_coordinate_systems
        except UnboundLocalError:
            pass
        return dict_in

    @pyaedt_function_handler
    def _get_duplicate_names(self):
        # Copy project to get dictionary
        from ansys.aedt.core.icepak import Icepak

        directory = os.path.join(
            self._app.toolkit_directory,
            self._app.design_name,
            generate_unique_folder_name("config_export_temp_project"),
        )
        os.makedirs(directory)
        tempproj_name = os.path.join(directory, "temp_proj.aedt")
        tempproj = Icepak(tempproj_name, version=self._app._aedt_version)
        empty_design = tempproj.design_list[0]
        self._app.modeler.refresh()
        self._app.modeler.delete(
            list(
                set([id for id, obj in self._app.modeler.objects.items() if obj.model])
                - set([id for _, obj in self._app.modeler.user_defined_components.items() for id in obj.parts])
            )
        )
        self._app.oproject.CopyDesign(self._app.design_name)
        self._app.odesign.Undo()
        tempproj.oproject.Paste()
        tempproj.modeler.refresh_all_ids()
        tempproj.delete_design(empty_design)
        tempproj.close_project()
        dictionary = load_keyword_in_aedt_file(tempproj_name, "UserDefinedModels")["UserDefinedModels"]
        for root, dirs, files in os.walk(directory, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(directory)
        operation_dict = {"Source": {}, "Duplicate": {}}
        list_dictionaries = []
        for key in ["NativeComponentInstanceWithParams", "NativeComponentInstance", "UserDefinedModel"]:
            if dictionary.get(key, None):
                if not isinstance(dictionary[key], list):
                    list_dictionaries.append(dictionary[key])
                else:
                    list_dictionaries += dictionary[key]
        for component in list_dictionaries:
            obj_name = component["Attributes"]["Name"]
            counter_line, counter_axis, counter_mirror = 0, 0, 0
            if component["Operations"].get("UDMOperation", None):
                udm_operations = component["Operations"]["UDMOperation"]
                if not isinstance(udm_operations, list):
                    udm_operations = [udm_operations]
                for operation in udm_operations:
                    if operation["OperationType"].startswith("UDMFromDup"):
                        if operation["CloneOperId"] in operation_dict["Duplicate"]:
                            operation_dict["Duplicate"][operation["CloneOperId"]].append(obj_name)
                        else:
                            operation_dict["Duplicate"][operation["CloneOperId"]] = [obj_name]
            if component["Operations"].get("CloneToOperation", None):
                clone_operations = component["Operations"]["CloneToOperation"]
                if not isinstance(clone_operations, list):
                    clone_operations = [clone_operations]
                for operation in clone_operations:
                    if operation["OperationType"] == "UDMDuplicateAlongLine":
                        counter_line += 1
                        operation_dict["Source"][operation["ID"]] = [
                            "DuplicateAlongLine:" + str(counter_line),
                            obj_name,
                        ]
                    elif operation["OperationType"] == "UDMDuplicateAroundAxis":
                        counter_axis += 1
                        operation_dict["Source"][operation["ID"]] = [
                            "DuplicateAroundAxis:" + str(counter_axis),
                            obj_name,
                        ]
                    elif operation["OperationType"] == "UDMDuplicateMirror":
                        counter_mirror += 1
                        operation_dict["Source"][operation["ID"]] = ["DuplicateMirror:" + str(counter_mirror), obj_name]
        duplicate_dict = {}
        for operation_id, prop in operation_dict["Source"].items():
            if not duplicate_dict.get(prop[1], None):
                duplicate_dict[prop[1]] = {}
            duplicate_dict[prop[1]][prop[0]] = operation_dict["Duplicate"][operation_id]
        return duplicate_dict

    @pyaedt_function_handler
    def _export_native_components(self, dict_out):
        dict_out["native components"] = {}
        duplicate_dict = self._get_duplicate_names()

        def add_duplicate_dic_to_history(node_name, node, obj_name):
            if node_name.startswith("Duplicate"):
                node["Props"]["Duplicate Object"] = duplicate_dict[obj_name][node_name]
            if node["Children"] != {}:
                for node_name, node in node["Children"].items():
                    add_duplicate_dic_to_history(node_name, node, obj_name)

        for _, nc in self._app.native_components.items():
            instance_name = nc.props["SubmodelDefinitionName"]
            dict_out["native components"][instance_name] = {}
            nc_props = dict(nc.props).copy()
            nc_type = nc.props["NativeComponentDefinitionProvider"]["Type"]
            dict_out["native components"][instance_name]["Type"] = nc_type
            if (
                nc_type == "PCB"
                and nc_props["NativeComponentDefinitionProvider"]["DefnLink"]["Project"] == "This Project*"
            ):
                nc_props["NativeComponentDefinitionProvider"]["DefnLink"]["Project"] = self._app.project_file
            dict_out["native components"][instance_name]["Properties"] = nc_props
            dict_out["native components"][instance_name]["Instances"] = {}
            for i, v in self._app.modeler.user_defined_components.items():
                cs_name = None
                if v.definition_name == instance_name:
                    if "Target Coordinate System" in self._app.oeditor.GetChildObject(i).GetPropNames():
                        cs_name = v.target_coordinate_system
                    obj_history = v.history()
                    if obj_history:
                        obj_history = obj_history.jsonalize_tree()
                        for node_name, node in obj_history.items():
                            add_duplicate_dic_to_history(node_name, node, i)
                    else:
                        obj_history = None
                    dict_out["native components"][instance_name]["Instances"][v.name] = {
                        "CS": cs_name,
                        "Operations": obj_history,
                    }
        if not self.options.export_coordinate_systems:  # pragma: no cover
            self._export_coordinate_systems(dict_out)

    @pyaedt_function_handler
    def _update_native_components(self, native_name, native_dict):
        def apply_operations_to_native_components(obj, operation_dict, native_dict):  # pragma: no cover
            cache_cs = self._app.oeditor.GetActiveCoordinateSystem()
            self._app.modeler.set_working_coordinate_system(operation_dict["Props"]["Coordinate System"])
            new_objs = None
            self._app.modeler.refresh_all_ids()
            old_objs = list(self._app.modeler.user_defined_components.keys())
            if operation_dict["Props"]["Command"] == "Move":
                if len(operation_dict["Props"]["Move Vector"]) == 6:
                    operation_list = [
                        decompose_variable_value(operation_dict["Props"]["Move Vector"][2 * i + 1])[0] for i in range(3)
                    ]
                else:
                    operation_list = [
                        decompose_variable_value(operation_dict["Props"]["Move Vector"][i])[0] for i in range(3)
                    ]
                obj.move(operation_list)
            elif operation_dict["Props"]["Command"] == "Rotate":
                rotation = decompose_variable_value(operation_dict["Props"]["Angle"])
                obj.rotate(operation_dict["Props"]["Axis"], angle=rotation[0], units=rotation[1])
            elif operation_dict["Props"]["Command"] == "Mirror":
                if len(operation_dict["Props"]["Base Position"]) == 6:
                    base_list = [
                        decompose_variable_value(operation_dict["Props"]["Base Position"][2 * i + 1])[0]
                        for i in range(3)
                    ]
                    normal_list = [
                        decompose_variable_value(operation_dict["Props"]["Normal Position"][2 * i + 1])[0]
                        for i in range(3)
                    ]

                else:
                    base_list = [
                        decompose_variable_value(operation_dict["Props"]["Base Position"][i])[0] for i in range(3)
                    ]
                    normal_list = [
                        decompose_variable_value(operation_dict["Props"]["Normal Position"][i])[0] for i in range(3)
                    ]

                obj.mirror(base_list, normal_list)
            elif operation_dict["Props"]["Command"] == "DuplicateAlongLine":
                if len(operation_dict["Props"]["Vector"]) == 6:
                    vector_list = [
                        decompose_variable_value(operation_dict["Props"]["Vector"][2 * i + 1])[0] for i in range(3)
                    ]
                else:
                    vector_list = [decompose_variable_value(operation_dict["Props"]["Vector"][i])[0] for i in range(3)]
                new_objs = obj.duplicate_along_line(
                    vector_list,
                    clones=operation_dict["Props"]["Total Number"],
                    attach_object=operation_dict["Props"]["Attach To Original Object"],
                )
            elif operation_dict["Props"]["Command"] == "DuplicateAroundAxis":
                rotation = decompose_variable_value(operation_dict["Props"]["Angle"])
                new_objs = obj.duplicate_around_axis(
                    operation_dict["Props"]["Axis"], angle=rotation[0], clones=operation_dict["Props"]["Total Number"]
                )
            elif operation_dict["Props"]["Command"] == "DuplicateMirror":
                if len(operation_dict["Props"]["Base Position"]) == 6:
                    base_list = [
                        decompose_variable_value(operation_dict["Props"]["Base Position"][2 * i + 1])[0]
                        for i in range(3)
                    ]
                    normal_list = [
                        decompose_variable_value(operation_dict["Props"]["Normal Position"][2 * i + 1])[0]
                        for i in range(3)
                    ]

                else:
                    base_list = [
                        decompose_variable_value(operation_dict["Props"]["Base Position"][i])[0] for i in range(3)
                    ]
                    normal_list = [
                        decompose_variable_value(operation_dict["Props"]["Normal Position"][i])[0] for i in range(3)
                    ]
                new_objs = obj.duplicate_and_mirror(
                    base_list,
                    normal_list,
                )
            else:  # pragma: no cover
                raise ValueError("Operation not supported")
            if new_objs:
                new_objs = list(set(new_objs) - set(old_objs))
                for new_obj in new_objs:
                    if native_dict[new_obj]["Operations"]:
                        for dup_obj in operation_dict["Props"]["Duplicate Object"]:
                            for _, operation_dict in native_dict[dup_obj]["Operations"].items():
                                apply_operations_to_native_components(
                                    self._app.modeler.user_defined_components[new_obj], operation_dict, native_dict
                                )
            for _, operation_dict in operation_dict["Children"].items():
                apply_operations_to_native_components(obj, operation_dict, native_dict)
            self._app.modeler.set_working_coordinate_system(cache_cs)
            return True

        for _, instance_dict in native_dict["Instances"].items():
            if instance_dict["CS"]:
                nc_dict = copy.deepcopy(native_dict["Properties"])
                nc_dict["TargetCS"] = instance_dict["CS"]
                component3d_names = list(self._app.modeler.oeditor.Get3DComponentInstanceNames(native_name))
                if native_dict["Type"] == "PCB":
                    native = NativeComponentPCB(self._app, native_dict["Type"], native_name, nc_dict)
                else:
                    native = NativeComponentObject(self._app, native_dict["Type"], native_name, nc_dict)
                prj_list = set(self._app.project_list)
                definition_names = set(self._app.oeditor.Get3DComponentDefinitionNames())
                instance_names = {
                    def_name: set(self._app.oeditor.Get3DComponentInstanceNames(def_name))
                    for def_name in definition_names
                }
                if not native.create():  # pragma: no cover
                    return False
                try:
                    definition_names = list(set(self._app.oeditor.Get3DComponentDefinitionNames()) - definition_names)[
                        0
                    ]
                    instance_names = list(self._app.oeditor.Get3DComponentInstanceNames(definition_names))[0]
                except IndexError:
                    definition_names = [
                        def_name
                        for def_name in definition_names
                        if len(set(self._app.oeditor.Get3DComponentInstanceNames(def_name)) - instance_names[def_name])
                        > 0
                    ][0]
                    instance_names = list(
                        set(self._app.oeditor.Get3DComponentInstanceNames(definition_names))
                        - instance_names[definition_names]
                    )[0]
                native.component_name = definition_names
                native.name = instance_names
                if nc_dict["NativeComponentDefinitionProvider"]["Type"] == "PCB" and nc_dict[
                    "NativeComponentDefinitionProvider"
                ]["DefnLink"]["Project"] not in [self._app.project_file or "This Project*"]:
                    prj = list(set(self._app.project_list) - prj_list)[0]
                    design = nc_dict["NativeComponentDefinitionProvider"]["DefnLink"]["Design"]
                    from ansys.aedt.core.generic.design_types import get_pyaedt_app

                    app = get_pyaedt_app(prj, design)
                    app.oproject.Close()
                user_defined_component = UserDefinedComponent(
                    self._app.modeler, instance_names, nc_dict["NativeComponentDefinitionProvider"], native_dict["Type"]
                )
                self._app.modeler.user_defined_components[instance_names] = user_defined_component
                new_name = [
                    i
                    for i in list(
                        self._app.modeler.oeditor.Get3DComponentInstanceNames(user_defined_component.definition_name)
                    )
                    if i not in component3d_names
                ][0]
                self._app.modeler.refresh_all_ids()
                self._app.materials._load_from_project()
                if native.component_name not in self._app.native_components:
                    self._app._native_components.append(native)
                if instance_dict.get("Operations", None):
                    for _, operation_dict in instance_dict["Operations"].items():
                        apply_operations_to_native_components(
                            self._app.modeler.user_defined_components[new_name],
                            operation_dict,
                            native_dict["Instances"],
                        )
        return True
