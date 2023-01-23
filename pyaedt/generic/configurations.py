import copy
import json
import os
from collections import OrderedDict
from datetime import datetime

from pyaedt import __version__
from pyaedt.generic.DataHandlers import _arg2dict
from pyaedt.generic.general_methods import _create_json_file
from pyaedt.generic.general_methods import generate_unique_name
from pyaedt.generic.general_methods import pyaedt_function_handler
from pyaedt.modeler.cad.Modeler import CoordinateSystem
from pyaedt.modeler.geometry_operators import GeometryOperators
from pyaedt.modules.Boundary import BoundaryObject
from pyaedt.modules.Boundary import BoundaryProps
from pyaedt.modules.DesignXPloration import SetupOpti
from pyaedt.modules.DesignXPloration import SetupParam
from pyaedt.modules.MaterialLib import Material
from pyaedt.modules.Mesh import MeshOperation


def _find_datasets(d, out_list):
    for v in list(d.values()):
        if isinstance(v, (dict, OrderedDict)):
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

    def __init__(self):
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
        >>> from pyaedt import Hfss
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
        >>> from pyaedt import Hfss
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
        >>> from pyaedt import Hfss
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
        >>> from pyaedt import Hfss
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
        >>> from pyaedt import Hfss
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
        >>> from pyaedt import Hfss
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
        >>> from pyaedt import Hfss
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
    #     >>> from pyaedt import Hfss
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
        >>> from pyaedt import Hfss
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
        >>> from pyaedt import Hfss
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
        >>> from pyaedt import Hfss
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
        >>> from pyaedt import Hfss
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
        >>> from pyaedt import Hfss
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
        >>> from pyaedt import Hfss
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
        >>> from pyaedt import Hfss
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
        >>> from pyaedt import Hfss
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
        >>> from pyaedt import Hfss
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
    #     >>> from pyaedt import Hfss
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
        >>> from pyaedt import Hfss
        >>> hfss = Hfss()
        >>> hfss.configurations.options.import_import_materials = False  # Disable the materials import
        """
        return self._import_materials

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
        >>> from pyaedt import Hfss
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
        >>> from pyaedt import Hfss
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
    """Import Results Class.
    Contains the results of the import operations. Each reusult can be ``True`` or ``False``.
    """

    def __init__(self):
        self.import_units = None
        self.import_variables = None
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
    """Configuration Class.
    It enables to export and import configuration options to be applied on a new/existing design.
    """

    def __init__(self, app):
        self._app = app
        self.options = ConfigurationsOptions()
        self.results = ImportResults()

    @staticmethod
    @pyaedt_function_handler()
    def _map_dict_value(dict_out, key, value):
        dict_out["general"]["object_mapping"][key] = value

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
                if isinstance(obj, int):
                    try:
                        new_list.append(mapping[str(obj)])
                    except KeyError:
                        pass
                else:
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
                            self._app.modeler._arg_with_dim(mapping[str(face)][1][0], self._app.modeler.model_units),
                            "YPosition:=",
                            self._app.modeler._arg_with_dim(mapping[str(face)][1][1], self._app.modeler.model_units),
                            "ZPosition:=",
                            self._app.modeler._arg_with_dim(mapping[str(face)][1][2], self._app.modeler.model_units),
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
            self._app.logger.info("Coordinate System {} added.".format(name))
            return True
        except Exception:
            self._app.logger.warning("Failed to add CS {} ".format(name))
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
    #         cs._modeler.oeditor.CreateFaceCS(cs._face_paramenters, cs._attributes)
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
            x1 = self._app.modeler._arg_with_dim(float(current[0]["XPosition"]), self._app.modeler.model_units)
            y1 = self._app.modeler._arg_with_dim(float(current[0]["YPosition"]), self._app.modeler.model_units)
            z1 = self._app.modeler._arg_with_dim(float(current[0]["ZPosition"]), self._app.modeler.model_units)
            x2 = self._app.modeler._arg_with_dim(float(current[1]["XPosition"]), self._app.modeler.model_units)
            y2 = self._app.modeler._arg_with_dim(float(current[1]["YPosition"]), self._app.modeler.model_units)
            z2 = self._app.modeler._arg_with_dim(float(current[1]["ZPosition"]), self._app.modeler.model_units)
            p1 = OrderedDict({"Coordinate System": "Global", "Start": [x1, y1, z1], "End": [x2, y2, z2]})
            bound.auto_update = False
            bound.props["CurrentLine"] = BoundaryProps(bound, p1)
            bound.auto_update = True
        if bound.props.get("Modes", None):
            modes = OrderedDict({})
            for k, v in bound.props["Modes"].items():
                p1 = OrderedDict({"ModeNum": v["ModeNum"], "UseIntLine": v["UseIntLine"]})
                if v["UseIntLine"] and v["IntLine"].get("GeometryPosition", None):
                    current = v["IntLine"]["GeometryPosition"]
                    x1 = self._app.modeler._arg_with_dim(float(current[0]["XPosition"]), self._app.modeler.model_units)
                    y1 = self._app.modeler._arg_with_dim(float(current[0]["YPosition"]), self._app.modeler.model_units)
                    z1 = self._app.modeler._arg_with_dim(float(current[0]["ZPosition"]), self._app.modeler.model_units)
                    x2 = self._app.modeler._arg_with_dim(float(current[1]["XPosition"]), self._app.modeler.model_units)
                    y2 = self._app.modeler._arg_with_dim(float(current[1]["YPosition"]), self._app.modeler.model_units)
                    z2 = self._app.modeler._arg_with_dim(float(current[1]["ZPosition"]), self._app.modeler.model_units)
                    p1["IntLine"] = OrderedDict(
                        {"Coordinate System": "Global", "Start": [x1, y1, z1], "End": [x2, y2, z2]}
                    )
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
            self._app.boundaries.append(bound)
            if props["BoundType"] in ["Coil Terminal", "Coil", "CoilTerminal"]:
                winding_name = ""
                for b in self._app.boundaries:
                    if b.props.get("ID", 999) == props.get("ParentBndID", -1):
                        winding_name = b.name
                        break
                if winding_name:
                    self._app.add_winding_coils(winding_name, name)

            self._app.logger.info("Boundary Operation {} added.".format(name))
            return True
        else:
            self._app.logger.warning("Failed to add Boundary {} ".format(name))
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
            self._app.logger.info("mesh Operation {} added.".format(name))
            return True
        else:
            self._app.logger.warning("Failed to add Mesh {} ".format(name))
            return False

    @pyaedt_function_handler()
    def _update_setup(self, name, props):
        for setup_el in self._app.setups:
            if setup_el.name == name:
                if not self.options.skip_import_if_exists:
                    setup_el.props = props
                    setup_el.update()
                return True
        if self._app.create_setup(name, props["SetupType"], props):
            self._app.logger.info("Setup {} added.".format(name))
            return True
        else:
            self._app.logger.warning("Failed to add Setup {} ".format(name))
            return False

    @pyaedt_function_handler()
    def _update_optimetrics(self, name, props):
        for setup_el in self._app.optimizations.setups:
            if setup_el.name == name:
                if not self.options.skip_import_if_exists:
                    setup_el.props = props
                    setup_el.update()
                return True
        setup = SetupOpti(self._app, name, optim_type=props.get("SetupType", None))
        if setup.create():
            self._app.optimizations.setups.append(setup)
            self._app.logger.info("Optim {} added.".format(name))
            return True
        else:
            self._app.logger.warning("Failed to add Optim {} ".format(name))
            return False

    @pyaedt_function_handler()
    def _update_parametrics(self, name, props):
        for setup_el in self._app.parametrics.setups:
            if setup_el.name == name:
                if not self.options.skip_import_if_exists:
                    setup_el.props = props
                    setup_el.update()
                return True
        setup = SetupParam(self._app, name, optim_type=props.get("SetupType", None))
        if setup.create():
            self._app.optimizations.setups.append(setup)
            self._app.logger.info("Optim {} added.".format(name))
            return True
        else:
            self._app.logger.warning("Failed to add Optim {} ".format(name))
            return False

    @pyaedt_function_handler()
    def _update_datasets(self, name, data_dict):
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
    def import_config(self, config_file):
        """Import configuration settings from a json file and apply it to the current design.
        The sections to be applied are defined with ``configuration.options`` class.
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
        self.results._reset_results()
        with open(config_file) as json_file:
            dict_in = json.load(json_file)

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
                    self._app.variable_manager.set_variable(k, v, postprocessing=True)
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
                if not self._app.create_dataset(
                    el[1:], xunit=xunit, yunit=yunit, zunit=zunit, xlist=xval, ylist=yval, zlist=zval
                ):
                    self.results.import_material_datasets = False

        if self.options.import_materials and dict_in.get("materials", None):
            self.results.import_materials = True
            for el, val in dict_in["materials"].items():
                if self._app.materials.checkifmaterialexists(el):
                    newname = generate_unique_name(el)
                    self._app.logger.warning("Material %s already exists. Renaming to %s", el, newname)
                else:
                    newname = el
                newmat = Material(self._app, el, val)
                if newmat.update():
                    self._app.materials.material_keys[newname] = newmat
                else:
                    self.results.import_materials = False

        if self.options.import_coordinate_systems and dict_in.get("coordinatesystems", None):
            self.results.import_coordinate_systems = True
            for name, props in dict_in["coordinatesystems"].items():
                if not self._update_coordinate_systems(name, props):
                    self.results.import_coordinate_systems = False

        # if self.options.import_face_coordinate_systems and dict_in.get("facecoordinatesystems", None):
        #     self.results.import_face_coordinate_systems = True
        #     for name, props in dict_in["facecoordinatesystems"].items():
        #         self._convert_objects(dict_in["facecoordinatesystems"][name], dict_in["general"]["object_mapping"])
        #         if not self._update_face_coordinate_systems(name, props):
        #             self.results.import_face_coordinate_systems = False
        self._app.modeler.set_working_coordinate_system("Global")
        if self.options.import_object_properties and dict_in.get("objects", None):
            self.results.import_object_properties = True
            for obj, val in dict_in["objects"].items():
                if not self._update_object_properties(obj, val):
                    self.results.import_object_properties = False
            self._app.logger.info("Object Properties updated.")

        if self.options.import_datasets and dict_in.get("datasets", None):
            self.results.import_datasets = True
            for k, v in dict_in["datasets"].items():
                self._update_datasets(k, v)

        if self.options.import_boundaries and dict_in.get("boundaries", None):
            self.results.import_boundaries = True
            sort_order = sorted(dict_in["boundaries"], key=lambda x: dict_in["boundaries"][x].get("ID", 999))
            for name in sort_order:
                self._convert_objects(dict_in["boundaries"][name], dict_in["general"]["object_mapping"])
                if not self._update_boundaries(name, dict_in["boundaries"][name]):
                    self.results.import_boundaries = False

        if self.options.import_mesh_operations and dict_in.get("mesh", None):
            self.results.import_mesh_operations = True
            for name, props in dict_in["mesh"].items():
                self._convert_objects(props, dict_in["general"]["object_mapping"])
                if not self._update_mesh_operations(name, props):
                    self.results.import_mesh_operations = False

        if self.options.import_setups and dict_in.get("setups", None):
            self.results.import_setup = True
            for setup, props in dict_in["setups"].items():
                if not self._update_setup(setup, props):
                    self.results.import_setup = False

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
                dict_out["setups"][setup.name] = setup.props
                dict_out["setups"][setup.name]["SetupType"] = setup.setuptype
                if setup.sweeps:
                    for sweep in setup.sweeps:
                        dict_out["setups"][setup.name][sweep.name] = sweep.props

    @pyaedt_function_handler()
    def _export_optimizations(self, dict_out):
        if self._app.optimizations.setups:
            dict_out["optimizations"] = {}
            for setup in self._app.optimizations.setups:
                dict_out["optimizations"][setup.name] = setup.props
                dict_out["optimizations"][setup.name]["SetupType"] = setup.soltype

    @pyaedt_function_handler()
    def _export_parametrics(self, dict_out):
        if self._app.parametrics.setups:
            dict_out["parametrics"] = {}
            for setup in self._app.parametrics.setups:
                dict_out["parametrics"][setup.name] = setup.props
                dict_out["parametrics"][setup.name]["SetupType"] = setup.soltype

    @pyaedt_function_handler()
    def _export_boundaries(self, dict_out):
        if self._app.boundaries:
            dict_out["boundaries"] = {}
            for boundary in self._app.boundaries:
                dict_out["boundaries"][boundary.name] = boundary.props
                if not boundary.props.get("BoundType", None):
                    dict_out["boundaries"][boundary.name]["BoundType"] = boundary.type
                self._map_object(boundary.props, dict_out)

    @pyaedt_function_handler()
    def _export_coordinate_systems(self, dict_out):
        if self._app.modeler.coordinate_systems:
            dict_out["coordinatesystems"] = {}
            for cs in self._app.modeler.coordinate_systems:
                if isinstance(cs, CoordinateSystem):
                    dict_out["coordinatesystems"][cs.name] = cs.props
                    dict_out["coordinatesystems"][cs.name]["Reference CS"] = cs.ref_cs

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
    def _export_mesh_operations(self, dict_out):
        if self._app.mesh.meshoperations:
            dict_out["mesh"] = {}
            for mesh in self._app.mesh.meshoperations:
                dict_out["mesh"][mesh.name] = mesh.props
                self._map_object(mesh.props, dict_out)

    @pyaedt_function_handler()
    def _export_datasets(self, dict_out):
        if self._app.project_datasets or self._app.design_datasets:
            if dict_out.get("datasets", None) is None:
                dict_out["datasets"] = {}
            for dataset_dict in [self._app.project_datasets, self._app.design_datasets]:
                for k, obj in dataset_dict.items():
                    if k not in dict_out.get("material datasets", []):
                        dict_out["datasets"][k] = {
                            "v": obj.v,
                            "vunit": obj.vunit,
                            "x": obj.x,
                            "xunit": obj.xunit,
                            "y": obj.y,
                            "yunit": obj.yunit,
                            "z": obj.z,
                            "zunit": obj.zunit,
                        }

    @pyaedt_function_handler()
    def _export_monitor(self, dict_out):
        dict_monitor = {}
        if self._app.monitor.all_monitors != {}:
            for mon_name in self._app.monitor.all_monitors:
                dict_monitor[mon_name] = {
                    key: val
                    for key, val in self._app.monitor.all_monitors[mon_name].properties.items()
                    if key not in ["Name", "Object"]
                }
        dict_out["monitor"] = dict_monitor

    @pyaedt_function_handler()
    def _export_materials(self, dict_out):
        output_dict = {}
        for el, val in self._app.materials.material_keys.items():
            output_dict[val.name] = copy.deepcopy(val._props)
        out_list = []
        _find_datasets(output_dict, out_list)
        datasets = OrderedDict()
        for ds in out_list:
            if ds in list(self._app.project_datasets.keys()):
                d = self._app.project_datasets[ds]
                if d.z:
                    units = [d.xunit, d.yunit, d.zunit]
                    points = [val for tup in zip(d.x, d.y, d.z) for val in tup]
                else:
                    units = [d.xunit, d.yunit]
                    points = [val for tup in zip(d.x, d.y) for val in tup]
                datasets[ds] = OrderedDict(
                    {
                        "Coordinates": OrderedDict(
                            {
                                "DimUnits": units,
                                "Points": points,
                            }
                        )
                    }
                )

        dict_out["materials"] = output_dict
        if datasets:
            dict_out["material datasets"] = datasets

    @pyaedt_function_handler()
    def export_config(self, config_file=None, overwrite=False):
        """Export current design properties to json file.
        The section to be exported are defined with ``configuration.options`` class.


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
        if self.options.export_variables:
            self._export_variables(dict_out)
        if self.options.export_setups:
            self._export_setups(dict_out)
        if self.options.export_optimizations:
            self._export_optimizations(dict_out)
        if self.options.export_parametrics:
            self._export_parametrics(dict_out)
        if self.options.export_boundaries:
            self._export_boundaries(dict_out)
        if self.options.export_coordinate_systems:
            self._export_coordinate_systems(dict_out)
        # if self.options.export_face_coordinate_systems:
        #     self._export_face_coordinate_systems(dict_out)
        if self.options.export_object_properties:
            self._export_objects_properties(dict_out)
        if self.options.export_mesh_operations:
            self._export_mesh_operations(dict_out)
        if self.options.export_materials:
            self._export_materials(dict_out)
        if self.options.export_datasets:
            self._export_datasets(dict_out)
        if hasattr(self.options, "export_monitor"):
            if self.options.export_monitor:
                self._export_monitor(dict_out)
        # update the json if it exists already

        if os.path.exists(config_file) and not overwrite:
            with open(config_file, "r") as json_file:
                try:
                    dict_in = json.load(json_file)
                except Exception:
                    dict_in = {}
            try:
                if dict_in["general"]["pyaedt_version"] == __version__:
                    for k, v in dict_in.items():
                        if k not in dict_out:
                            dict_out[k] = v
                        elif isinstance(v, dict):
                            for i, j in v.items():
                                if i not in dict_out[k]:
                                    dict_out[k][i] = j
            except KeyError:
                pass
        # write the updated json to file
        if _create_json_file(dict_out, config_file):
            self._app.logger.info("Json file {} created correctly.".format(config_file))
            return config_file
        self._app.logger.error("Error creating json file {}.".format(config_file))
        return False


class ConfigurationsOptionsIcepak(ConfigurationsOptions):
    def __init__(self, app):
        ConfigurationsOptions.__init__(self)
        self._export_monitor = True
        self._import_monitor = True

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


class ConfigurationsIcepak(Configurations):
    """Configuration Class.
    It enables to export and import configuration options to be applied on a new/existing design.
    """

    def __init__(self, app):
        Configurations.__init__(self, app)
        self.options = ConfigurationsOptionsIcepak(app)

    @pyaedt_function_handler()
    def _update_object_properties(self, name, val):
        if name in self._app.modeler.object_names:
            arg = ["NAME:AllTabs", ["NAME:Geometry3DAttributeTab", ["NAME:PropServers", name]]]
            arg2 = ["NAME:ChangedProps"]
            if val.get("Material", None):
                arg2.append(["NAME:Material", "Value:=", chr(34) + val["Material"] + chr(34)])
            if val.get("SolveInside", None):
                arg2.append(["NAME:Solve Inside", "Value:=", val["SolveInside"]])
            arg2.append(
                [
                    "NAME:Surface Material",
                    "Value:=",
                    chr(34) + val.get("SurfaceMaterial", "Steel-oxidised-surface") + chr(34),
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

        bound = self._app.mesh.MeshRegion(
            self._app.mesh.omeshmodule, self._app.mesh.boundingdimension, self._app.mesh._model_units, self._app
        )
        bound.name = name
        for el in props:
            if el in bound.__dict__:
                bound.__dict__[el] = props[el]
        if bound.create():
            self._app.mesh.meshregions.append(bound)
            self._app.logger.info("mesh Operation {} added.".format(name))
        else:
            self._app.logger.warning("Failed to add Mesh {} ".format(name))
        return True

    @pyaedt_function_handler()
    def _export_objects_properties(self, dict_out):
        dict_out["objects"] = {}
        for val in self._app.modeler.objects.values():
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
        if self._app.mesh.global_mesh_region.UserSpecifiedSettings:
            args += self._app.mesh.global_mesh_region.manualsettings
        else:
            args += self._app.mesh.global_mesh_region.autosettings
        mop = OrderedDict({})
        _arg2dict(args, mop)
        dict_out["mesh"]["Settings"] = mop["Settings"]
        if self._app.mesh.meshregions:
            for mesh in self._app.mesh.meshregions:
                if mesh.name == "Settings":
                    args = ["NAME:Settings"]
                else:
                    args = ["NAME:" + mesh.name, "Enable:=", mesh.Enable]
                if mesh.UserSpecifiedSettings:
                    args += mesh.manualsettings
                else:
                    args += mesh.autosettings
                mop = OrderedDict({})
                _arg2dict(args, mop)
                dict_out["mesh"][mesh.name] = mop[mesh.name]
                self._map_object(mop, dict_out)
        pass

    @pyaedt_function_handler()
    def update_monitor(self, m_case, m_object, m_quantity, m_name):
        """
        Generic method for inserting monitor object

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
    def import_config(self, config_file):
        dict_in = Configurations.import_config(self, config_file)
        if self.options.import_monitor and dict_in.get("monitor", None):
            self.results.import_monitor = True
            for monitor_obj in dict_in["monitor"]:
                m_type = dict_in["monitor"][monitor_obj]["Type"]
                m_obj = dict_in["monitor"][monitor_obj]["ID"]
                if m_type == "Point":
                    m_obj = dict_in["monitor"][monitor_obj]["Location"]
                if not self.update_monitor(m_type, m_obj, dict_in["monitor"][monitor_obj]["Quantity"], monitor_obj):
                    self.results.import_monitor = False
        return dict_in
