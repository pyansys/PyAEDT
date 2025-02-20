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

from ansys.aedt.core.generic.checks import min_aedt_version
from ansys.aedt.core.generic.constants import AEDT_UNITS
from ansys.aedt.core.generic.general_methods import _uname
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.generic.general_methods import read_csv


class ComponentArray(object):
    """Manages object attributes for a 3D component array.

    Parameters
    ----------
    app : :class:`ansys.aedt.core.Hfss`
        HFSS PyAEDT object.
    name : str, optional
        Array name. The default is ``None``, in which case a random name is assigned.

    Examples
    --------
    Basic usage demonstrated with an HFSS design with an existing array:

    >>> from ansys.aedt.core import Hfss
    >>> aedtapp = Hfss(project="Array.aedt")
    >>> array_names = aedtapp.component_array_names[0]
    >>> array = aedtapp.component_array[array_names[0]]
    """

    def __init__(self, app, name=None):
        # Public attributes
        self.logger = app.logger
        self.update_cells = True

        # Private attributes
        self.__app = app
        if name is None:
            name = _uname("Array_")
        self.__name = name

        # Leverage csv file if possible (aedt version > 2023.2)
        if self.__app.settings.aedt_version > "2023.2":  # pragma: no cover
            self.export_array_info(output_file=None)
            self.__array_info_path = os.path.join(self.__app.toolkit_directory, "array_info.csv")
        else:
            self.__app.save_project()
            self.__array_info_path = None

        # Data that cannot be obtained from CSV
        try:
            self.__cs_id = app.design_properties["ArrayDefinition"]["ArrayObject"]["ReferenceCSID"]
        except (AttributeError, TypeError, KeyError):  # pragma: no cover
            self.__cs_id = 1

        self.__omodel = self.__app.get_oo_object(self.__app.odesign, "Model")
        self.__oarray = self.__app.get_oo_object(self.__omodel, name)
        self.__cells = None
        self.__post_processing_cells = {}

    @pyaedt_function_handler()
    def __getitem__(self, key):
        """Get cell object corresponding to a key (row, column).

        Parameters
        ----------
        key : tuple(int,int)
            Row and column associated to the cell.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.component_array.CellArray`
        """

        if key[0] > self.a_size or key[1] > self.b_size:
            self.logger.error("Specified cell does not exist.")
            return False

        if key[0] <= 0 or key[1] <= 0:
            self.logger.error("Row and column index start with ``1``.")
            return False

        return self.cells[key[0] - 1][key[1] - 1]

    @property
    def component_names(self):
        """List of component names."""
        return self.properties["component"]

    @property
    def cells(self):
        """List of :class:`ansys.aedt.core.modeler.cad.component_array.CellArray` objects."""
        if not self.update_cells:
            return self.__cells

        if self.__app.settings.aedt_version > "2023.2":  # pragma: no cover
            self.export_array_info(output_file=None)
        else:
            self.__app.save_project()

        self.__cells = [[None for _ in range(self.b_size)] for _ in range(self.a_size)]
        array_props = self.properties
        component_names = self.component_names
        for row_cell in range(0, self.a_size):
            for col_cell in range(0, self.b_size):
                self.__cells[row_cell][col_cell] = CellArray(row_cell, col_cell, array_props, component_names, self)
        return self.__cells

    @property
    def name(self):
        """Name of the array."""
        return self.__name

    @name.setter
    def name(self, array_name):
        if array_name not in self.__app.component_array_names:
            if array_name != self.__name:
                self.__oarray.SetPropValue("Name", array_name)
                self.__app.component_array.update({array_name: self})
                self.__app.component_array_names = list(self.__app.omodelsetup.GetArrayNames())
                del self.__app.component_array[self.__name]
                self.__name = array_name
        else:  # pragma: no cover
            self.logger.warning("Name %s already assigned in the design", array_name)

    @property
    def properties(self):
        """Ordered dictionary of the properties of the component array."""
        # From 2024R1, array information can be loaded from a CSV
        if self.__array_info_path and os.path.exists(self.__array_info_path):  # pragma: no cover
            res = self.parse_array_info_from_csv(self.__array_info_path)
        else:
            res = self.__get_properties_from_aedt()
        return res

    @property
    def post_processing_cells(self):
        """Dictionary of each component's postprocessing cells."""
        if not self.__post_processing_cells:
            self.__post_processing_cells = {}
            component_info = {}
            for row, row_info in enumerate(self.cells, start=1):
                for col, col_info in enumerate(row_info, start=1):
                    name = col_info.component
                    component_info.setdefault(name, []).append([row, col])

            for component_name, component_cells in component_info.items():
                if component_name not in self.__post_processing_cells.keys() and component_name is not None:
                    self.__post_processing_cells[component_name] = component_cells[0]

        return self.__post_processing_cells

    @post_processing_cells.setter
    def post_processing_cells(self, val):
        if isinstance(val, dict):
            self.__post_processing_cells = val
            self.edit_array()
        else:  # pragma: no cover
            self.logger.error("Dictionary with component names and cell is not correct.")

    @property
    def visible(self):
        """Flag indicating if the array is visible."""
        return self.__app.get_oo_property_value(self.__omodel, self.name, "Visible")

    @visible.setter
    def visible(self, val):
        self.__oarray.SetPropValue("Visible", val)

    @property
    def show_cell_number(self):
        """Flag indicating if the array cell number is shown."""
        return self.__app.get_oo_property_value(self.__omodel, self.name, "Show Cell Number")

    @show_cell_number.setter
    def show_cell_number(self, val):
        self.__oarray.SetPropValue("Show Cell Number", val)

    @property
    def render_choices(self):
        """List of rendered name choices."""
        return list(self.__oarray.GetPropValue("Render/Choices"))

    @property
    def render(self):
        """Array rendering."""
        return self.__app.get_oo_property_value(self.__omodel, self.name, "Render")

    @render.setter
    def render(self, val):
        if val not in self.render_choices:
            self.logger.warning("Render value is not available.")
        else:
            self.__oarray.SetPropValue("Render", val)

    @property
    def render_id(self):
        """Array rendering ID."""
        res = self.render_choices.index(self.render)
        return res

    @property
    def a_vector_choices(self):
        """List of name choices for vector A."""
        return list(self.__app.get_oo_property_value(self.__omodel, self.name, "A Vector/Choices"))

    @property
    def b_vector_choices(self):
        """List of name choices for vector B."""
        return list(self.__app.get_oo_property_value(self.__omodel, self.name, "B Vector/Choices"))

    @property
    def a_vector_name(self):
        """Name of vector A."""
        return self.__app.get_oo_property_value(self.__omodel, self.name, "A Vector")

    @a_vector_name.setter
    def a_vector_name(self, val):
        if val in self.a_vector_choices:
            self.__oarray.SetPropValue("A Vector", val)
        else:
            self.logger.warning("A vector name not available")

    @property
    def b_vector_name(self):
        """Name of vector B."""
        return self.__oarray.GetPropValue("B Vector")

    @b_vector_name.setter
    def b_vector_name(self, val):
        if val in self.b_vector_choices:
            self.__oarray.SetPropValue("B Vector", val)
        else:
            self.logger.warning("B vector name not available")

    @property
    def a_size(self):
        """Number of cells in the vector A direction."""
        return int(self.__app.get_oo_property_value(self.__omodel, self.name, "A Cell Count"))

    @a_size.setter
    def a_size(self, val):  # pragma: no cover
        # Bug in 2024.1, not possible to change cell count.
        # self._oarray.SetPropValue("A Cell Count", val)
        self.logger.warning("A size cannot be modified.")

    @property
    def b_size(self):
        """Number of cells in the vector B direction."""
        return int(self.__app.get_oo_property_value(self.__omodel, self.name, "B Cell Count"))

    @b_size.setter
    def b_size(self, val):  # pragma: no cover
        # Bug in 2024.1, not possible to change cell count.
        # self._oarray.SetPropValue("B Cell Count", val)
        self.logger.warning("B size cannot be modified.")

    @property
    def a_length(self):
        """Length of the array in A direction."""
        lattice_vector = self.lattice_vector()
        if lattice_vector[0] != 0:  # pragma: no cover
            x_spacing = lattice_vector[0]
        else:
            x_spacing = lattice_vector[3]

        return x_spacing * self.a_size

    @property
    def b_length(self):
        """Length of the array in B direction."""
        lattice_vector = self.lattice_vector()
        if lattice_vector[1] != 0:
            y_spacing = lattice_vector[1]
        else:  # pragma: no cover
            y_spacing = lattice_vector[4]

        return y_spacing * self.b_size

    @property
    def padding_cells(self):
        """Number of padding cells."""
        return int(self.__app.get_oo_property_value(self.__omodel, self.name, "Padding"))

    @padding_cells.setter
    def padding_cells(self, val):
        self.__oarray.SetPropValue("Padding", val)

    @property
    def coordinate_system(self):
        """Coordinate system name."""
        cs_dict = self.__map_coordinate_system_to_id()
        res = "Global"
        for name, cs_id in cs_dict.items():
            if cs_id == self.__cs_id:
                res = name
        if res == "Global":
            self.logger.warning("Coordinate system is not loaded. Save the project.")
        return res

    @coordinate_system.setter
    def coordinate_system(self, name):
        cs_dict = self.__map_coordinate_system_to_id()
        if name not in cs_dict:
            self.logger.warning("Coordinate system is not loaded. Save the project.")
        else:
            self.__cs_id = cs_dict[name]
            self.edit_array()

    @pyaedt_function_handler()
    def update_properties(self):
        """Update component array properties.

        Returns
        -------
        dict
           Ordered dictionary of the properties of the component array.
        """
        # From 2024R1, array information can be loaded from a CSV, and this method is not needed.
        if self.__app.settings.aedt_version > "2023.2":  # pragma: no cover
            self.export_array_info(output_file=None)
        else:
            self.__app.save_project()
        new_properties = self.properties
        # TODO : post_processing_cells property can not be retrieved, so if the length of the components and the
        #  property is different, the method will reset the property.
        if len(new_properties["component"]) != len(self.post_processing_cells):
            self.__post_processing_cells = {}
            new_properties = self.properties
        return new_properties

    @pyaedt_function_handler()
    def delete(self):
        """Delete the component array.

        References
        ----------
        >>> oModule.DeleteArray

        """
        self.__app.omodelsetup.DeleteArray()
        del self.__app.component_array[self.name]
        self.__app.component_array_names = list(self.__app.get_oo_name(self.__app.odesign, "Model"))

    @pyaedt_function_handler(array_path="output_file")
    @min_aedt_version("2024.1")
    def export_array_info(self, output_file=None):  # pragma: no cover
        """Export array information to a CSV file.

        Returns
        -------
        str
           Path of the CSV file.

        References
        ----------
        >>> oModule.ExportArray
        """
        if not output_file:  # pragma: no cover
            output_file = os.path.join(self.__app.toolkit_directory, "array_info.csv")
        self.__app.omodelsetup.ExportArray(self.name, output_file)
        return output_file

    @pyaedt_function_handler(csv_file="input_file")
    def parse_array_info_from_csv(self, input_file):  # pragma: no cover
        """Parse component array information from the CSV file.

        Parameters
        ----------
        input_file : str
             Name of the CSV file.

        Returns
        -------
        dict
           Ordered dictionary of the properties of the component array.

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> aedtapp = Hfss(project="Array.aedt")
        >>> array_names = aedtapp.component_array_names[0]
        >>> array = aedtapp.component_array[array_names[0]]
        >>> array_csv = array.export_array_info()
        >>> array_info = array.array_info_parser(array_csv)
        """

        info = read_csv(input_file)
        if not info:
            self.logger.error("Data from CSV file is not loaded.")
            return False

        components = {}
        array_matrix = []
        array_matrix_rotation = []
        array_matrix_active = []

        # Components
        start_str = ["Component Index", "Component Name"]
        end_str = ["Source Row", "Source Column", "Source Name", "Magnitude", "Phase"]

        capture_data = False
        line_cont = 0
        for element_data in info:
            if element_data == start_str:
                capture_data = True
            elif element_data == end_str:
                break
            elif capture_data:
                components[int(float(element_data[0]))] = element_data[1]
            line_cont += 1

        # Array matrix
        start_str = ["Array", "Format: Component_index:Rotation_angle:Active_or_Passive"]
        capture_data = False

        for element_data in info[line_cont + 1 :]:
            if capture_data:
                rows = element_data[:-1]
                component_index = []
                rotation = []
                active_passive = []

                for row in rows:
                    split_elements = row.split(":")

                    # Check for non-empty strings
                    if split_elements[0]:
                        component_index.append(int(split_elements[0]))
                    else:
                        component_index.append(-1)

                    # Some elements might not have the rotation and active/passive status, so we check for their
                    # existence
                    if split_elements[0] and len(split_elements) > 1:
                        string_part = re.findall("[a-zA-Z]+", split_elements[1])
                        if string_part and string_part[0] == "deg":
                            rot = re.findall(r"[+-]?\d+\.\d+", split_elements[1])
                            rotation.append(int(float(rot[0])))
                            if len(split_elements) > 2:
                                active_passive.append(bool(int(split_elements[2])))
                            else:
                                active_passive.append(True)
                        else:
                            active_passive.append(False)
                            rotation.append(0)
                    elif split_elements[0]:
                        active_passive.append(True)
                        rotation.append(0)
                    else:
                        active_passive.append(False)
                        rotation.append(0)

                array_matrix.append(component_index)
                array_matrix_rotation.append(rotation)
                array_matrix_active.append(active_passive)
            elif element_data == start_str:
                capture_data = True
        res = {}
        res["component"] = components
        res["active"] = array_matrix_active
        res["rotation"] = array_matrix_rotation
        res["cells"] = array_matrix
        return res

    @pyaedt_function_handler()
    def edit_array(self):
        """Edit component array.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oModule.EditArray
        """

        args = [
            "NAME:" + self.name,
            "Name:=",
            self.name,
            "UseAirObjects:=",
            True,
            "RowPrimaryBnd:=",
            self.a_vector_name,
            "ColumnPrimaryBnd:=",
            self.b_vector_name,
            "RowDimension:=",
            self.a_size,
            "ColumnDimension:=",
            self.b_size,
            "Visible:=",
            self.visible,
            "ShowCellNumber:=",
            self.show_cell_number,
            "RenderType:=",
            self.render_id,
            "Padding:=",
            self.padding_cells,
            "ReferenceCSID:=",
            self.__cs_id,
        ]

        cells = ["NAME:Cells"]
        component_info = {}
        cells_obj = self.cells[:]
        for row, row_info in enumerate(cells_obj, start=1):
            for col, col_info in enumerate(row_info, start=1):
                name = col_info.component
                component_info.setdefault(name, []).append([row, col])

        for component_name, component_cells in component_info.items():
            if component_name:
                cells.append(component_name + ":=")
                component_cells_str = ", ".join(str(item) for item in component_cells)
                cells.append([component_cells_str])

        rotations = ["NAME:Rotation"]
        component_rotation = {}
        for row, row_info in enumerate(cells_obj, start=1):
            for col, col_info in enumerate(row_info, start=1):
                component_rotation.setdefault(col_info.rotation, []).append([row, col])

        for rotation, rotation_cells in component_rotation.items():
            rotations.append(str(rotation) + " deg:=")
            component_cells_str = ", ".join(str(item) for item in rotation_cells)
            rotations.append([component_cells_str])

        args.append(cells)
        args.append(rotations)

        args.append("Active:=")

        component_active = []
        for row, row_info in enumerate(cells_obj, start=1):
            for col, col_info in enumerate(row_info, start=1):
                if col_info.is_active:
                    component_active.append([row, col])

        if component_active:
            args.append(", ".join(str(item) for item in component_active))
        else:  # pragma: no cover
            args.append("All")

        post = ["NAME:PostProcessingCells"]
        for component_name, values in self.post_processing_cells.items():
            post.append(component_name + ":=")
            post.append([str(values[0]), str(values[1])])
        args.append(post)
        args.append("Colors:=")
        col = []
        args.append(col)
        self.__app.omodelsetup.EditArray(args)
        return True

    @pyaedt_function_handler()
    def get_cell(self, row, col):
        """Get cell object corresponding to a row and column.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.component_array.CellArray`

        """
        return self[row, col]

    @pyaedt_function_handler()
    def lattice_vector(self):
        """Get model lattice vector.

        Returns
        -------
        list
            List of starting point coordinates paired with ending point coordinates.

        References
        ----------
        >>> oModule.GetLatticeVectors()

        """
        lattice_vectors = self.__app.omodelsetup.GetLatticeVectors()

        lattice_vectors = [float(vec) * AEDT_UNITS["Length"][self.__app.modeler.model_units] for vec in lattice_vectors]
        return lattice_vectors

    @pyaedt_function_handler()
    def get_component_objects(self):
        """Get 3D component center.

        Returns
        -------
        dict
            Dictionary of the center position and part name for all 3D components.

        """
        component_info = {}
        component_names = self.component_names
        for component in component_names.values():
            parts = self.__app.modeler.user_defined_components[component].parts
            for part_name in parts.values():
                if component not in component_info:
                    center = self.__app.modeler.user_defined_components[component].center
                    scaled_center = [
                        float(cen) * AEDT_UNITS["Length"][self.__app.modeler.model_units] for cen in center
                    ]
                    component_info[component] = (scaled_center, str(part_name))
                else:
                    component_info[component] = component_info[component] + (str(part_name),)

        return component_info

    @pyaedt_function_handler()
    def get_cell_position(self):
        """Get cell position.

        Returns
        -------
        list
            List of the center position and part name for all cells.

        """
        cell_info = [[None for _ in range(self.b_size)] for _ in range(self.a_size)]
        lattice_vector = self.lattice_vector()
        # Perpendicular lattice vector
        a_x_dir = True
        if lattice_vector[0] != 0:  # pragma: no cover
            x_spacing = lattice_vector[0]
        else:
            a_x_dir = False
            x_spacing = lattice_vector[3]

        if lattice_vector[1] != 0:
            y_spacing = lattice_vector[1]
        else:  # pragma: no cover
            y_spacing = lattice_vector[4]

        cells = self.cells
        for row_cell in range(0, self.a_size):
            for col_cell in range(0, self.b_size):
                if a_x_dir:  # pragma: no cover
                    y_position = col_cell * y_spacing
                    x_position = row_cell * x_spacing

                else:
                    y_position = row_cell * y_spacing
                    x_position = col_cell * x_spacing

                cell_info[row_cell][col_cell] = (
                    cells[row_cell][col_cell].component,
                    [x_position, y_position, 0.0],
                    cells[row_cell][col_cell].rotation,
                    [row_cell + 1, col_cell + 1],
                )
        return cell_info

    @pyaedt_function_handler()
    def __get_properties_from_aedt(self):
        """Get array properties from an AEDT file.

        Returns
        -------
        dict
            Ordered dictionary of the properties of the component array.

        """
        props = self.__app.design_properties
        component_id = {}
        user_defined_models = props["ModelSetup"]["GeometryCore"]["GeometryOperations"]["UserDefinedModels"][
            "UserDefinedModel"
        ]
        if not isinstance(user_defined_models, list):
            user_defined_models = [user_defined_models]
        for component_defined in user_defined_models:
            component_id[component_defined["ID"]] = component_defined["Attributes"]["Name"]

        components_map = props["ArrayDefinition"]["ArrayObject"]["ComponentMap"]
        components = {}
        for c in components_map:
            m = re.search(r"'(\d+)'=(\d+)", c)
            components[int(m.group(1))] = component_id[int(m.group(2))]
        res = {}
        res["component"] = components
        res["active"] = props["ArrayDefinition"]["ArrayObject"]["Active"]["matrix"]
        res["rotation"] = props["ArrayDefinition"]["ArrayObject"]["Rotation"]["matrix"]
        res["cells"] = props["ArrayDefinition"]["ArrayObject"]["Cells"]["matrix"]
        return res

    @pyaedt_function_handler()
    def __map_coordinate_system_to_id(self):
        """Map coordinate system to ID.

        Returns
        -------
        dict
            Coordinate system ID.
        """
        res = {"Global": 1}
        if self.__app.design_properties and "ModelSetup" in self.__app.design_properties:  # pragma: no cover
            cs = self.__app.design_properties["ModelSetup"]["GeometryCore"]["GeometryOperations"]["CoordinateSystems"]
            for _, val in cs.items():
                try:
                    if isinstance(val, dict):
                        val = [val]
                    for ite in val:
                        name = ite["Attributes"]["Name"]
                        cs_id = ite["ID"]
                        res[name] = cs_id
                except AttributeError:
                    pass
        return res


class CellArray(object):
    """Manages object attributes for a 3D component and a user-defined model.

    Parameters
    ----------
    row : int
        Row index of the cell.
    col : int
        Column index of the cell.
    array_props : dict
        Dictionary containing the properties of the array.
    component_names : list
        List of component names in the array.
    array_obj : class:`ansys.aedt.core.modeler.cad.component_array.ComponentArray`
        Instance of the array containing the cell.

    """

    def __init__(self, row, col, array_props, component_names, array_obj):
        self.__row = row + 1
        self.__col = col + 1
        self.__array_obj = array_obj
        self.__cell_props = {
            "component": array_props["cells"][row][col],
            "active": array_props["active"][row][col],
            "rotation": array_props["rotation"][row][col],
        }

        self.__rotation = self.__cell_props["rotation"]
        self.__is_active = self.__cell_props["active"]

        component_index = self.__cell_props["component"]
        if component_index == -1:
            self.__component = None
        else:
            self.__component = component_names[component_index]

    @property
    def rotation(self):
        """Rotation value of the cell object."""
        return self.__rotation

    @rotation.setter
    def rotation(self, val):
        if val in [0, 90, 180, 270]:
            self.__rotation = val
            self.__array_obj.update_cells = False
            self.__array_obj.edit_array()
            self.__array_obj.update_cells = True
        else:
            self.__array_obj.logger.error("Rotation must be an integer. 0, 90, 180, and 270 degrees are available.")

    @property
    def component(self):
        """Component name of the cell object."""
        return self.__component

    @component.setter
    def component(self, val):
        component_names = self.__array_obj.component_names
        if val in component_names.values() or val is None:
            self.__array_obj.update_cells = False
            if val is None:
                post_processing_cells = self.__array_obj.post_processing_cells
                for values in post_processing_cells:
                    if (values[0], values[1]) == (self.__row, self.__col):
                        flat_cell_list = [item for sublist in self.__array_obj.cells for item in sublist]
                        for cell in flat_cell_list:
                            if cell.component == self.component and cell.col != self.__col or cell.row != self.__row:
                                self.__array_obj.post_processing_cells[self.component] = [cell.row, cell.col]
                                break
                        break
            self.__component = val
            self.__array_obj.edit_array()
            self.__array_obj.update_cells = True
        else:  # pragma: no cover
            self.__array_obj.logger.error("Component must be defined.")

    @property
    def is_active(self):
        """Flag indicating if the cell object is active or passive."""
        return self.__is_active

    @is_active.setter
    def is_active(self, val):
        if isinstance(val, bool):
            self.__is_active = val
            self.__array_obj.update_cells = False
            self.__array_obj.edit_array()
            self.__array_obj.update_cells = True
        else:
            self.__array_obj.logger.error("Only Boolean type is allowed.")
