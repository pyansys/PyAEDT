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

"""Module containing the `Materials` class."""

import copy
import fnmatch
import math
import os
import re
import sys
import warnings

from ansys.aedt.core.generic.data_handlers import _arg2dict
from ansys.aedt.core.generic.general_methods import generate_unique_name
from ansys.aedt.core.generic.general_methods import open_file
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.generic.general_methods import read_json
from ansys.aedt.core.generic.general_methods import write_configuration_file
from ansys.aedt.core.generic.load_aedt_file import load_entire_aedt_file
from ansys.aedt.core.generic.settings import settings
from ansys.aedt.core.modules.material import MatProperties
from ansys.aedt.core.modules.material import Material
from ansys.aedt.core.modules.material import SurfaceMaterial
from ansys.aedt.core.modules.material_workbench import MaterialWorkbench


class Materials(object):
    """Contains the AEDT materials database and all methods for creating and editing materials.

    Parameters
    ----------
    app : :class:`ansys.aedt.core.application.analysis_3d.FieldAnalysis3D`
        Inherited parent object.

    Examples
    --------
    >>> from ansys.aedt.core import Hfss
    >>> app = Hfss()
    >>> materials = app.materials
    """

    def __init__(self, app):
        self._app = app
        self._color_id = 0
        self._mats = []
        self._mats_lower = []
        self._desktop = self._app.odesktop
        self._oproject = self._app.oproject
        self.logger = self._app.logger
        self.material_keys = {}
        self._surface_material_keys = {}
        self._load_from_project()

    @property
    def odefinition_manager(self):
        """Definition Manager from AEDT."""
        return self._app.odefinition_manager

    @property
    def omaterial_manager(self):
        """Material Manager from AEDT."""
        return self._app.omaterial_manager

    def __len__(self):
        return len(self.material_keys)

    def __iter__(self):
        return iter(self.material_keys.values()) if sys.version_info.major > 2 else self.material_keys.itervalues()

    def __getitem__(self, item):
        matobj = self.exists_material(item)
        if matobj:
            return matobj
        elif item in list(self.surface_material_keys.keys()):
            return self.surface_material_keys[item]
        return

    @property
    def surface_material_keys(self):
        """Dictionary of Surface Material in the project.

        Returns
        -------
        dict of :class:`ansys.aedt.core.modules.material.Material`
        """
        if not self._surface_material_keys and self._app.design_type == "Icepak":
            self._surface_material_keys = self._get_surface_materials()
        return self._surface_material_keys

    @property
    def liquids(self):
        """Return the liquids materials. A liquid is a fluid with density greater or equal to 100Kg/m3.

        Returns
        -------
        list
            List of fluid materials.
        """
        mats = []
        for el, val in self.material_keys.items():
            if val.thermal_material_type == "Fluid" and val.mass_density.value and float(val.mass_density.value) >= 100:
                mats.append(el)
        return mats

    @property
    def gases(self):
        """Return the gas materials. A gas is a fluid with density lower than 100Kg/m3.

        Returns
        -------
        list
            List of all Gas materials.
        """
        mats = []
        for el, val in self.material_keys.items():
            if val.thermal_material_type == "Fluid" and val.mass_density.value and float(val.mass_density.value) < 100:
                mats.append(el)
        return mats

    @property
    def _mat_names_aedt(self):
        if not self._mats:
            self._mats = self._read_materials()
        return self._mats

    @property
    def _mat_names_aedt_lower(self):
        if len(self._mats_lower) < len(self._mat_names_aedt):
            self._mats_lower = [i.casefold() for i in self._mat_names_aedt]
        return self._mats_lower

    @property
    def mat_names_aedt(self):
        """List material names."""
        return self._mat_names_aedt

    @property
    def mat_names_aedt_lower(self):
        """List material names with lower case."""
        return self._mat_names_aedt_lower

    @pyaedt_function_handler()
    def _read_materials(self):
        def get_mat_list(file_name):
            mats = []
            _begin_search = re.compile(r"^\$begin '(.+)'")
            with open_file(file_name, "rb") as aedt_fh:
                raw_lines = aedt_fh.read().splitlines()
                for line in raw_lines:
                    try:
                        ascii_line = line.decode("utf-8")
                    except UnicodeDecodeError:
                        continue
                    b = _begin_search.search(ascii_line)
                    if b:  # walk down a level
                        mats.append(b.group(1))
            return mats

        amat_sys = [
            os.path.join(dirpath, filename)
            for dirpath, _, filenames in os.walk(self._app.syslib)
            for filename in filenames
            if fnmatch.fnmatch(filename, "*.amat")
        ]
        amat_personal = [
            os.path.join(dirpath, filename)
            for dirpath, _, filenames in os.walk(self._app.personallib)
            for filename in filenames
            if fnmatch.fnmatch(filename, "*.amat")
        ]
        amat_user = [
            os.path.join(dirpath, filename)
            for dirpath, _, filenames in os.walk(self._app.userlib)
            for filename in filenames
            if fnmatch.fnmatch(filename, "*.amat")
        ]
        amat_libs = amat_sys + amat_personal + amat_user
        mats = []
        for amat in amat_libs:
            # m = load_entire_aedt_file(amat)
            # mats.extend(list(m.keys()))
            mats.extend(get_mat_list(amat))
        try:
            mats.remove("$index$")
        except ValueError:
            pass
        try:
            mats.remove("$base_index$")
        except ValueError:
            pass
        mats.extend(self.odefinition_manager.GetProjectMaterialNames())
        return mats

    @pyaedt_function_handler()
    def _get_aedt_case_name(self, material_name):
        if material_name.casefold() in self.material_keys:
            return self.material_keys[material_name.casefold()].name
        if material_name.casefold() in self.mat_names_aedt_lower:
            return self._mat_names_aedt[self.mat_names_aedt_lower.index(material_name.casefold())]
        return False

    @pyaedt_function_handler()
    def _get_surface_materials(self):
        mats = {}
        try:
            for ds in self._app.project_properties["AnsoftProject"]["Definitions"]["SurfaceMaterials"]:
                mats[ds.casefold()] = SurfaceMaterial(
                    self,
                    ds,
                    self._app.project_properties["AnsoftProject"]["Definitions"]["SurfaceMaterials"][ds],
                    material_update=False,
                )
        except Exception:
            self.logger.debug("An error occurred while accessing surface materials.")  # pragma: no cover
        return mats

    @pyaedt_function_handler(mat="material")
    def checkifmaterialexists(self, material):
        """Check if a material exists in AEDT or PyAEDT Definitions.

        .. deprecated:: 0.11.4
           Use :func:`exists_material` method instead.

        Parameters
        ----------
        material : str
            Name of the material. If the material exists and is not in the materials database,
            it is added to this database.

        Returns
        -------
        :class:`ansys.aedt.core.modules.material.Material`
            Material object if present, ``False`` when failed.

        References
        ----------
        >>> oDefinitionManager.GetProjectMaterialNames
        >>> oMaterialManager.GetData
        """
        warnings.warn(
            "`checkifmaterialexists` is deprecated. Use `exists_material` method instead.", DeprecationWarning
        )
        return self.exists_material(material=material)

    @pyaedt_function_handler()
    def exists_material(self, material):
        """Check if a material exists in AEDT or PyAEDT Definitions.

        Parameters
        ----------
        material : str
            Name of the material. If the material exists and is not in the materials database,
            it is added to this database.

        Returns
        -------
        :class:`ansys.aedt.core.modules.material.Material`
            Material object if present, ``False`` when failed.

        References
        ----------
        >>> oDefinitionManager.GetProjectMaterialNames
        >>> oMaterialManager.GetData
        """
        if isinstance(material, Material):
            if material.name.casefold() in self.material_keys:
                return material
            else:
                return False
        if material.casefold() in self.material_keys:
            if material.casefold() in self.mat_names_aedt_lower:
                return self.material_keys[material.casefold()]
            if material.casefold() not in list(self.odefinition_manager.GetProjectMaterialNames()):
                self.material_keys[material.casefold()].update()
            return self.material_keys[material.casefold()]
        elif material.casefold() in self.mat_names_aedt_lower:
            return self._aedmattolibrary(material)
        elif settings.remote_api or settings.remote_rpc_session:
            return self._aedmattolibrary(material)
        return False

    @pyaedt_function_handler(mat="material")
    def check_thermal_modifier(self, material):
        """Check a material to see if it has any thermal modifiers.

        Parameters
        ----------
        material : str
            Name of the material. All properties for this material are checked
            for thermal modifiers.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        omat = self.exists_material(material)
        if omat:
            for el in MatProperties.aedtname:
                if omat.__dict__["_" + el].thermalmodifier:
                    return True
        return False

    @pyaedt_function_handler(materialname="name", props="properties")
    def add_material(self, name, properties=None):
        """Add a material with default values.

        When the added material object is returned, you can customize
        the material. This method does not update the material.

        Parameters
        ----------
        name : str
            Name of the material.
        properties : dict, optional
            Material property dictionary. The default is ``None``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.material.Material`

        References
        ----------
        >>> oDefinitionManager.AddMaterial

        Examples
        --------

        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> mat = hfss.materials.add_material("MyMaterial")
        >>> print(mat.conductivity.value)

        >>> oDefinitionManager.GetProjectMaterialNames
        >>> oMaterialManager.GetData

        """
        self.logger.info("Adding new material to the Project Library: " + name)
        if name.casefold() in self.material_keys:
            self.logger.warning("Warning. The material is already in the database. Change or edit the name.")
            return self.material_keys[name.casefold()]
        elif self._get_aedt_case_name(name):
            return self._aedmattolibrary(self._get_aedt_case_name(name))
        else:
            material = Material(self, name, properties, material_update=False)
            material.update()
            material._material_update = True
            if material:
                self.logger.info("Material has been added in Desktop.")
                self.material_keys[name.casefold()] = material
                self._mats.append(name)
                return self.material_keys[name.casefold()]
        return False

    @pyaedt_function_handler(material_name="name")
    def add_surface_material(self, name, emissivity=None):
        """Add a surface material.

        In AEDT, base properties are loaded from the XML database file ``amat.xml``
        or from the emissivity.

        Parameters
        ----------
        name : str
            Name of the surface material.
        emissivity : float, optional
            Emissivity value.

        Returns
        -------
        :class:`ansys.aedt.core.modules.SurfaceMaterial`

        References
        ----------
        >>> oDefinitionManager.AddSurfaceMaterial

        Examples
        --------

        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> mat = hfss.materials.add_surface_material("Steel",0.85)
        >>> print(mat.emissivity.value)

        """
        self.logger.info("Adding a surface material to the project library: " + name)
        if name.casefold() in self.surface_material_keys:
            self.logger.warning("Warning. The material is already in the database. Change the name or edit it.")
            return self.surface_material_keys[name.casefold()]
        else:
            material = SurfaceMaterial(self._app, name, material_update=False)
            if emissivity:
                material.emissivity.value = emissivity
            material.update()
            material._material_update = True
            self.logger.info("Material has been added.")
            self.surface_material_keys[name.casefold()] = material
            return self.surface_material_keys[name.casefold()]

    @pyaedt_function_handler()
    def _create_mat_project_vars(self, matlist):
        matprop = {}
        tol = 1e-12
        for prop in MatProperties.aedtname:
            matprop[prop] = []
            for mat in matlist:
                try:
                    matprop[prop].append(float(mat.__dict__["_" + prop].value))
                except Exception:
                    self.logger.warning("Warning. Wrong parsed property. Reset to 0")
                    matprop[prop].append(0)
            try:
                a = sum(matprop[prop])
                if a < tol:
                    del matprop[prop]
            except Exception:
                self.logger.debug("An error occurred while creating material property.")  # pragma: no cover

        return matprop

    @pyaedt_function_handler(materials_list="assignment", material_name="name")
    def add_material_sweep(self, assignment, name):
        """Create a sweep material made of an array of materials.

        Parameters
        ----------
        assignment : list
            List of materials to merge into a single sweep material.
        name : str
            Name of the sweep material.

        Returns
        -------
        int
            Index of the project variable.

        References
        ----------
        >>> oDefinitionManager.AddMaterial

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss.materials.add_material("MyMaterial")
        >>> hfss.materials.add_material("MyMaterial2")
        >>> hfss.materials.add_material_sweep(["MyMaterial", "MyMaterial2"],"Sweep_copper")
        """
        matsweep = []
        for mat in assignment:
            matobj = self.exists_material(mat)
            if matobj:
                matsweep.append(matobj)

        mat_dict = self._create_mat_project_vars(matsweep)

        newmat = Material(self, name, material_update=False)
        index = "$ID" + name
        newmat.is_sweep_material = True
        self._app[index] = 0
        for el in mat_dict:
            if el in list(mat_dict.keys()):
                array_var_name = "$" + name + "_" + el
                self._app[array_var_name] = mat_dict[el]
                newmat.__dict__["_" + el].value = array_var_name + "[" + index + "]"
                newmat._update_props(el, array_var_name + "[" + index + "]", False)

        newmat.update()
        self.material_keys[name.casefold()] = newmat
        return index

    @pyaedt_function_handler(material_name="material", new_name="name", props="properties")
    def duplicate_material(self, material, name=None, properties=None):
        """Duplicate a material.

        Parameters
        ----------
        material : str
            Name of the material.
        name : str
            Name for the copy of the material. If a new name is not specified,
            the new material name is ``material_name`` plusa  "_clone"`` suffix.
        properties : list
            List of properties to parameterize when the material is duplicated.
            Parameterized properties have project scope. Options are:

            - `'permittivity'`
            - `'permeability'`
            - `'conductivity'`
            - '`dielectric_loss_tan'`
            - '`magnetic_loss_tan'`


        Returns
        -------
        :class:`ansys.aedt.core.modules.material.Material`

        References
        ----------
        >>> oDefinitionManager.AddMaterial

        Examples
        --------

        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss.materials.add_material("MyMaterial")
        >>> hfss.materials.duplicate_material("MyMaterial","MyMaterial2")

        """
        # Special characters must be removed from material names to make
        # valid strings for parameter names.
        replace_characters = [(" ", "_"), ("(", ""), (")", ""), ("/", "_"), ("-", "_"), (".", "_"), (",", "_")]
        valid_prop_names = (
            "permittivity",
            "permeability",
            "conductivity",
            "dielectric_loss_tangent",
            "magnetic_loss_tangent",
        )

        # Get the material definition.
        material_in_aedt = material.casefold() in list(self.mat_names_aedt_lower)
        material_in_project = material.casefold() in list(self.material_keys.keys())
        if not (material_in_aedt or material_in_project):  # Check for material definition
            self.logger.error(f"Material {material} is not present")
            return False
        if not material_in_project:
            material = self._aedmattolibrary(material)
        else:
            material = self.material_keys[material.casefold()]

        if not name:
            name = material + "_clone"
        new_material = Material(self, name, material._props, material_update=False)

        # Parameterize material properties if these were passed.
        if properties:
            for p in properties:
                if p in valid_prop_names:
                    var_name = "$" + name + "_" + p
                    for r in replace_characters:
                        var_name = var_name.replace(r[0], r[1])
                    self._app[var_name] = getattr(
                        material, p
                    ).value  # Assign default value to parameterized material parameter.
                    try:
                        setattr(new_material, p, var_name)
                    except TypeError:
                        print(f"p = {p}")
        new_material.update()
        new_material._material_update = True
        self._mats.append(name)
        self.material_keys[name.casefold()] = new_material
        return new_material

    @pyaedt_function_handler(new_name="name")
    def duplicate_surface_material(self, material, name=None):
        """Duplicate a surface material.

        Parameters
        ----------
         material : str
            Name of the surface material.
        name : str
            Name for the copy of the surface material.

        Returns
        -------
        :class:`ansys.aedt.core.modules.SurfaceMaterial`

        References
        ----------
        >>> oDefinitionManager.AddSurfaceMaterial

        Examples
        --------

        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss.materials.add_surface_material("MyMaterial")
        >>> hfss.materials.duplicate_surface_material("MyMaterial","MyMaterial2")
        """
        if material.casefold() not in list(self.surface_material_keys.keys()):
            self.logger.error(f"Material {material} is not present")
            return False
        if not name:
            name = material + "_clone"
        newmat = SurfaceMaterial(
            self, name, self.surface_material_keys[material.casefold()]._props, material_update=True
        )
        self.surface_material_keys[name.casefold()] = newmat
        return newmat

    @pyaedt_function_handler()
    def remove_material(self, material, library="Project"):
        """Remove a material.

        Parameters
        ----------
        material : str
            Name of the material.
        library : str, optional
            Name of the library containing this material.
            The default is ``"Project"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDefinitionManager.RemoveMaterial

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss()
        >>> hfss.materials.add_material("MyMaterial")
        >>> hfss.materials.remove_material("MyMaterial")

        """
        mat = material.casefold()
        if mat not in list(self.material_keys.keys()):
            self.logger.error(f"Material {mat} is not present")
            return False
        self.odefinition_manager.RemoveMaterial(self._get_aedt_case_name(mat), True, "", library)
        del self.material_keys[mat]
        return True

    @property
    def conductors(self):
        """Conductors in the material database.

        Returns
        -------
        list
            List of conductors in the material database.

        """
        data = []
        for key, mat in self.material_keys.items():
            if mat.is_conductor():
                data.append(key)
        return data

    @property
    def dielectrics(self):
        """Dielectrics in the material database.

        Returns
        -------
        list
            List of dielectrics in the material database.

        """
        data = []
        for key, mat in self.material_keys.items():
            if mat.is_dielectric():
                data.append(key)
        return data

    def _load_from_project(self):
        if self.odefinition_manager:
            mats = self.odefinition_manager.GetProjectMaterialNames()
            if not mats:
                mats = []
            for el in mats:
                if el not in list(self.material_keys.keys()):
                    try:
                        self._aedmattolibrary(el)
                    except Exception:
                        self.logger.info("aedmattolibrary failed for material %s", el)

    @pyaedt_function_handler()
    def _aedmattolibrary(self, matname):
        """Get and convert Material Properties from AEDT to Dictionary.

        Parameters
        ----------
        matname : str

        Returns
        -------
        :class:`ansys.aedt.core.modules.material.Material`
        """
        if matname not in self.odefinition_manager.GetProjectMaterialNames() and not (
            settings.remote_api or settings.remote_rpc_session
        ):
            matname = self._get_aedt_case_name(matname)
        props = {}
        _arg2dict(list(self.omaterial_manager.GetData(matname)), props)
        values_view = props.values()
        value_iterator = iter(values_view)
        first_value = next(value_iterator)
        newmat = Material(self, matname, first_value, material_update=False)
        newmat._material_update = True
        self.material_keys[matname.casefold()] = newmat
        return self.material_keys[matname.casefold()]

    @pyaedt_function_handler(full_json_path="output_file")
    def export_materials_to_file(self, output_file):
        """Export all materials to a JSON or TOML file.

        Parameters
        ----------
        output_file : str
            Full path and name of the JSON file to export to.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """

        def find_datasets(d, out_list):
            for k, v in d.items():
                if isinstance(v, dict):
                    find_datasets(v, out_list)
                else:
                    a = copy.deepcopy(v)
                    val = a
                    if str(type(a)) == r"<type 'List'>":
                        val = list(a)
                    if "pwl(" in str(val) or "cpl(" in str(val):
                        if isinstance(a, list):
                            for element in a:
                                m = re.search(r"(?:pwl|cwl)\((.*?),", str(element))
                                if m:
                                    out_list.append(m.group(1))
                        else:
                            out_list.append(a[a.find("$") : a.find(",")])

        # Data to be written
        output_dict = {}
        for el, val in self.material_keys.items():
            matobj = self.material_keys[el]
            matname = matobj.name
            output_dict[matname] = copy.deepcopy(val._props)
        out_list = []
        find_datasets(output_dict, out_list)
        datasets = {}
        for ds in out_list:
            if ds in list(self._app.project_datasets.keys()):
                d = self._app.project_datasets[ds]
                if d.z:
                    datasets[ds] = {
                        "Coordinates": {
                            "DimUnits": [d.xunit, d.yunit, d.zunit],
                            "Points": [val for tup in zip(d.x, d.y, d.z) for val in tup],
                        }
                    }
                else:
                    datasets[ds] = {
                        "Coordinates": {
                            "DimUnits": [d.xunit, d.yunit],
                            "Points": [val for tup in zip(d.x, d.y) for val in tup],
                        }
                    }
        json_dict = {}
        json_dict["materials"] = output_dict
        if datasets:
            json_dict["datasets"] = datasets
        return write_configuration_file(json_dict, output_file)

    @pyaedt_function_handler(full_path="input_file")
    def import_materials_from_file(self, input_file=None, **kwargs):
        """Import and create materials from a JSON or AMAT file.

        Parameters
        ----------
        input_file : str
            Full path and name for the JSON or AMAT file.

        Returns
        -------
        List of :class:`ansys.aedt.core.modules.material.Material`
        """
        if "full_json_path" in kwargs and kwargs["full_json_path"] is not None:  # pragma: no cover
            warnings.warn(
                "``full_json_path`` was deprecated in 0.8.1. Use ``full_path`` instead.",
                DeprecationWarning,
            )
            input_file = kwargs["full_json_path"]

        if input_file is None or not os.path.exists(input_file):
            self.logger.error("Incorrect path provided.")
            return False

        _, file_extension = os.path.splitext(input_file)
        json_flag = True
        datasets = {}
        if file_extension.casefold() == ".json":
            data = read_json(input_file)
            if "datasets" in list(data.keys()):
                datasets = data["datasets"]
        elif file_extension.casefold() == ".amat":
            data = load_entire_aedt_file(input_file)
            json_flag = False
            new_data = {}

            for mat_name in data:
                if "MaterialDef" in data[mat_name] and mat_name in data[mat_name]["MaterialDef"]:
                    new_data[mat_name] = data[mat_name]["MaterialDef"][mat_name]
                else:
                    new_data[mat_name] = data[mat_name]

                if "RefDatasets" in data[mat_name]:
                    for dataset in data[mat_name]["RefDatasets"]:
                        dataset_loaded = data[mat_name]["RefDatasets"][dataset]
                        datasets[dataset] = {"Coordinates": {"DimUnits": [], "Points": []}}
                        datasets[dataset]["Coordinates"]["DimUnits"] = dataset_loaded["DimUnits"]
                        for point_element in range(0, len(dataset_loaded["X"]) - 1):
                            datasets[dataset]["Coordinates"]["Points"].append(dataset_loaded["X"][point_element])
                            datasets[dataset]["Coordinates"]["Points"].append(dataset_loaded["Y"][point_element])
                if new_data:
                    data[mat_name] = new_data[mat_name]
        else:
            self.logger.error("Invalid file extension.")
            return False

        materials_added = []

        if datasets:
            for el, val in datasets.items():
                numcol = len(val["Coordinates"]["DimUnits"])
                xunit = val["Coordinates"]["DimUnits"][0]
                yunit = val["Coordinates"]["DimUnits"][1]
                zunit = ""

                new_list = [
                    val["Coordinates"]["Points"][i : i + numcol]
                    for i in range(0, len(val["Coordinates"]["Points"]), numcol)
                ]
                xval = [sublist[0] for sublist in new_list]
                yval = [sublist[1] for sublist in new_list]
                zval = None
                if numcol > 2:
                    zunit = val["Coordinates"]["DimUnits"][2]
                    zval = [sublist[2] for sublist in new_list]
                self._app.create_dataset(el[1:], x=xval, y=yval, z=zval, x_unit=xunit, y_unit=yunit, z_unit=zunit)
        if json_flag:
            for el, val in data["materials"].items():
                if el.casefold() in list(self.material_keys.keys()):
                    newname = generate_unique_name(el)
                    self.logger.warning("Material %s already exists. Renaming to %s", el, newname)
                else:
                    newname = el
                try:
                    newmat = Material(self, newname, val, material_update=False)
                    newmat.update()
                    newmat._material_update = True
                    self.material_keys[newname] = newmat
                    materials_added.append(newmat)
                except KeyError as e:
                    self.logger.error(f"Failed to import material {el!r} from {input_file!r}: key error on {e}")
                    raise e
        else:
            for mat_name in data:
                invalid_names = ["$base_index$", "$index$"]
                if mat_name in invalid_names:
                    continue
                if mat_name.casefold() in list(self.material_keys.keys()):
                    newname = generate_unique_name(mat_name)
                    self.logger.warning("Material %s already exists. Renaming to %s", mat_name, newname)
                else:
                    newname = mat_name

                newmat = self.add_material(newname, properties=data[mat_name])
                materials_added.append(newmat)
        return materials_added

    @pyaedt_function_handler(material_file="input_file")
    def import_materials_from_excel(self, input_file):
        """Import and create materials from a csv or excel file.

        Parameters
        ----------
        input_file : str
            Full path and name for the csv or xlsx file.

        Returns
        -------
        List of :class:`ansys.aedt.core.modules.material.Material`

        """
        try:  # pragma: no cover
            import pandas as pd
        except ImportError:
            self.logger.error("Pandas is needed. Install it.")
            return False
        materials_added = []
        props = {}
        if os.path.splitext(input_file)[1] == ".csv":
            df = pd.read_csv(input_file, index_col=0)
        elif os.path.splitext(input_file)[1] == ".xlsx":
            df = pd.read_excel(input_file, index_col=0)
        else:
            self.logger.error("Only csv and xlsx are supported.")
            return False
        keys = [i.casefold() for i in list(df.keys())]
        for el, val in df[::-1].iterrows():
            if isinstance(el, float):
                break
            if el.casefold() in list(self.material_keys.keys()):
                newname = generate_unique_name(el)
                self.logger.warning("Material %s already exists. Renaming to %s", el, newname)
            else:
                newname = el
            for prop in MatProperties.aedtname:
                if (
                    prop in keys
                    and val[keys.index(prop)]
                    and not (isinstance(val[keys.index(prop)], float) and math.isnan(val[keys.index(prop)]))
                ):
                    props[prop] = float(val[keys.index(prop)])
            new_material = Material(self, newname, props, material_update=False)
            new_material.update()
            new_material._material_update = True
            self.material_keys[newname] = new_material
            materials_added.append(new_material)

        return materials_added

    @pyaedt_function_handler
    def get_used_project_material_names(self):
        """Get list of material names in current project.

        Returns
        -------
        List of str
            List of material names used in the current project.

        References
        ----------
        >>> oDefinitionManager.GetInUseProjectMaterialNames
        """
        return self.odefinition_manager.GetInUseProjectMaterialNames()

    @pyaedt_function_handler
    def import_materials_from_workbench(self, input_file, name_suffix=None):
        """Import and create materials from Workbench Engineering Data XML file.

        Parameters
        ----------
        input_file : str
            Full path and name for the XML file.

        name_suffix : str, None, optional
            String containing the suffix to be applied to the imported material names.
            The default is ``None``, in which case "_wb" is used.
            Set it to ``""`` to maintain in AEDT the same name as in Workbench.

        Returns
        -------
        List of :class:`ansys.aedt.core.modules.material.Material`

        """
        # create an instance of the class
        mat_wb = MaterialWorkbench(self._app)
        # set the name suffix if any
        if name_suffix:
            mat_wb.mat_name_suffix = name_suffix
        # check if the xml file exists
        if not os.path.isfile(input_file):
            self.logger.error(f"The file specified does not exist: {input_file}")
            return False
        # import the materials in the xml
        return mat_wb.import_materials_from_workbench(input_file)
