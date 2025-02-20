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

from ansys.aedt.core import constants
from ansys.aedt.core import pyaedt_path
from ansys.aedt.core.generic.general_methods import generate_unique_name
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.modules.material_lib import Material

LAYERS = {"s": "signal", "g": "ground", "d": "dielectric"}


def _replace_by_underscore(character, string):
    """Replace each character of a string by underscores.

    This method is used to create Hfss variable relative to a material,
    and so reformat the material name into the variable name format.

    Parameters
    ----------
    character : str
        The character to replace by underscore.
    string : str
        The string where the replacement is made.

    Examples
    --------

    >>> from ansys.aedt.core.modeler.advanced_cad.stackup_3d import _replace_by_underscore
    >>> name = "Duroid (tm)"
    >>> name = _replace_by_underscore(" ", name)
    >>> name = _replace_by_underscore("(", name)
    >>> name = _replace_by_underscore(")", name)
    """
    if not isinstance(character, str):
        raise TypeError("character must be str")
    if not isinstance(character, str):
        raise TypeError("string must be str")
    reformat_name = list(string)
    while character in reformat_name:
        index = reformat_name.index(character)
        reformat_name[index] = "_"
    return "".join(reformat_name)


class NamedVariable(object):
    """Cast PyAEDT variable object to simplify getters and setters in Stackup3D.

    Parameters
    ----------
    application : :class:`ansys.aedt.core.hfss.Hfss`
        HFSS design or project where the variable is to be created.
    name : str
        The name of the variable. If the name begins with an '$', the variable will be a project variable.
        Otherwise, it will be a design variable.
    expression : str
        Expression of the value.

    Examples
    --------

    >>> from ansys.aedt.core import Hfss
    >>> from ansys.aedt.core.modeler.advanced_cad.stackup_3d import NamedVariable
    >>> hfss = Hfss()
    >>> my_frequency = NamedVariable(hfss, "my_frequency", "900000Hz")
    >>> wave_length_formula = "c0/" + my_frequency.name
    >>> my_wave_length = NamedVariable(hfss, "my_wave_length", wave_length_formula)
    >>> my_permittivity = NamedVariable(hfss, "my_permittivity", "2.2")
    >>> my_wave_length.expression = my_wave_length.expression + "/" + my_permittivity.name

    """

    def __init__(self, application, name, expression):
        self._application = application
        self._name = name
        self._expression = expression
        application[name] = expression

    @property
    def _variable(self):
        return self._application.variable_manager.variables[self._name]

    @property
    def name(self):
        """Name of the variable as a string."""
        return self._name

    @property
    def expression(self):
        """Expression of the variable as a string."""
        return self._expression

    @expression.setter
    def expression(self, expression):
        """Set the expression of the variable.

        Parameters
        ----------
        expression: str
            Value expression of the variable."""
        if isinstance(expression, str):
            self._expression = expression
            self._application[self.name] = expression
        else:
            self._application.logger.error("Expression must be a string")

    @property
    def unit_system(self):
        """Unit system of the expression as a string."""
        return self._variable.unit_system

    @property
    def units(self):
        """Units."""
        return self._variable.units

    @property
    def value(self):
        """Value."""
        return self._variable.value

    @property
    def numeric_value(self):
        """Numeric part of the expression as a float value."""
        return self._variable.numeric_value

    @property
    def evaluated_value(self):
        """String that combines the numeric value and the units."""
        return self._variable.evaluated_value

    @pyaedt_function_handler()
    def hide_variable(self, value=True):
        """Set the variable to a hidden variable.

        Parameters
        ----------
        value : bool, optional
            Whether the variable is a hidden variable. The default is ``True``.

        Returns
        -------
        bool
        """
        self._application.variable_manager[self._name].hidden = value
        return True

    @pyaedt_function_handler()
    def read_only_variable(self, value=True):
        """Set the variable to a read-only variable.

        Parameters
        ----------
        value : bool, optional
            Whether the variable is a read-only variable. The default is ``True``.

        Returns
        -------
        bool
        """
        self._application.variable_manager[self._name].read_only = value
        return True


class DuplicatedParametrizedMaterial(object):
    """Provides a class to duplicate a material and manage its duplication in PyAEDT and in AEDT.

    For each material property a NamedVariable is created as attribute.

    Parameters
    ----------
    application : :class:`ansys.aedt.core.hfss.Hfss
        HFSS design or project where the variable is to be created.
    material_name : str
        The material name which will be cloned.
    cloned_material_name : str
        The cloned material named
    list_of_properties : list of string
        Currently unavailable, but this parameter could be used to select the properties which needs to be parametrized.
        Currently, the permittivity, permeability, conductivity, dielectric loss tangent and the magnetic loss tangent
         are parametrized with a NamedVariable.

    Examples
    --------

    >>> from ansys.aedt.core import Hfss
    >>> from ansys.aedt.core.modeler.advanced_cad.stackup_3d import DuplicatedParametrizedMaterial
    >>> hfss = Hfss()
    >>> my_copper = DuplicatedParametrizedMaterial(hfss, "copper", "my_copper")
    >>> my_material_name = my_copper.material_name
    >>> my_material = my_copper.material
    >>> my_copper_conductivity = my_copper.conductivity

    """

    def __init__(self, application, material_name, cloned_material_name, list_of_properties=None):
        self._thickness = None
        self._permittivity = None
        self._permeability = None
        self._conductivity = None
        self._dielectric_loss_tangent = None
        self._magnetic_loss_tangent = None
        self._material = None
        self._material_name = None
        if application.materials.exists_material(material_name):
            if not list_of_properties:
                cloned_material = application.materials.duplicate_material(material_name, cloned_material_name)
                permittivity = cloned_material.permittivity.value
                permeability = cloned_material.permeability.value
                conductivity = cloned_material.conductivity.value
                dielectric_loss_tan = cloned_material.dielectric_loss_tangent.value
                magnetic_loss_tan = cloned_material.magnetic_loss_tangent.value
                reformat_name = _replace_by_underscore(" ", cloned_material_name)
                reformat_name = _replace_by_underscore("(", reformat_name)
                reformat_name = _replace_by_underscore(")", reformat_name)
                reformat_name = _replace_by_underscore("/", reformat_name)
                reformat_name = _replace_by_underscore("-", reformat_name)
                reformat_name = _replace_by_underscore(".", reformat_name)
                reformat_name = _replace_by_underscore(",", reformat_name)
                permittivity_variable = "$" + reformat_name + "_permittivity"
                permeability_variable = "$" + reformat_name + "_permeability"
                conductivity_variable = "$" + reformat_name + "_conductivity"
                dielectric_loss_variable = "$" + reformat_name + "_dielectric_loss"
                magnetic_loss_variable = "$" + reformat_name + "_magnetic_loss"
                self._permittivity = NamedVariable(application, permittivity_variable, permittivity)
                self._permeability = NamedVariable(application, permeability_variable, permeability)
                self._conductivity = NamedVariable(application, conductivity_variable, conductivity)
                self._dielectric_loss_tangent = NamedVariable(
                    application, dielectric_loss_variable, dielectric_loss_tan
                )
                self._magnetic_loss_tangent = NamedVariable(application, magnetic_loss_variable, magnetic_loss_tan)
                cloned_material.permittivity = permittivity_variable
                cloned_material.permeability = permeability_variable
                cloned_material.conductivity = conductivity_variable
                cloned_material.dielectric_loss_tangent = dielectric_loss_variable
                cloned_material.magnetic_loss_tangent = magnetic_loss_variable
                self._material = cloned_material
                self._material_name = cloned_material_name
        else:
            application.logger.error("The material name %s doesn't exist" % material_name)

    @property
    def material(self):
        return self._material

    @property
    def material_name(self):
        return self._material_name

    @property
    def permittivity(self):
        return self._permittivity

    @property
    def permeability(self):
        return self._permeability

    @property
    def conductivity(self):
        return self._conductivity

    @property
    def dielectric_loss_tangent(self):
        return self._dielectric_loss_tangent

    @property
    def magnetic_loss_tangent(self):
        return self._magnetic_loss_tangent


class Layer3D(object):
    """Provides a class for a management of a parametric layer in 3D Modeler.

    The Layer3D class is not intended to be used with its constructor,
    but by using the method "add_layer" available in the Stackup3D class.

    Parameters
    ----------
    stackup : :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.Stackup3D`
        The stackup where the layers will be added.
    app : :class:`ansys.aedt.core.hfss.Hfss`
        HFSS design or project where the variable is to be created.
    name : str
        Name of the layer.
    layer_type : str
        "S" for signal layers, "D" for dielectric layers, "G" for ground layers.
    material_name : str
        The material name of the layer.
    thickness : float
        The thickness of the layer.
    fill_material : str
        In ground and signal layers, the dielectric material name which will fill the non-conductive areas of the layer.
    index : int
        The number of the layer, starting from bottom to top.
    frequency : float
        The layer frequency, it will be common to all geometric shapes on the layer.

    Examples
    --------
    >>> from ansys.aedt.core import Hfss
    >>> from ansys.aedt.core.modeler.advanced_cad.stackup_3d import Stackup3D
    >>> hfss = Hfss()
    >>> my_stackup = Stackup3D(hfss, 2.5e9)
    >>> my_layer = my_stackup.add_layer("my_layer")
    >>> gnd = my_stackup.add_ground_layer("gnd")
    >>> diel = my_stackup.add_dielectric_layer("diel1", thickness=1.5, material="Duroid (tm)")
    >>> top = my_stackup.add_signal_layer("top")

    """

    def __init__(
        self,
        stackup,
        app,
        name,
        layer_type="S",
        material_name="copper",
        thickness=0.035,
        fill_material="FR4_epoxy",
        index=1,
        frequency=None,
    ):
        self._stackup = stackup
        self._index = index
        self._app = app
        self._name = name
        layer_position = "layer_" + name + "_position"
        self._position = NamedVariable(app, layer_position, "0mm")

        self._layer_type = LAYERS.get(layer_type.lower())

        if frequency:
            self._frequency = NamedVariable(self._app, self._name + "frequency", str(frequency) + "Hz")
        else:
            self._frequency = stackup.frequency

        self._obj_3d = []
        obj_3d = None
        self._duplicated_material = self.duplicate_parametrize_material(material_name)
        self._material = self._duplicated_material  # Set material for this layer.

        if self._layer_type != "dielectric":
            self._fill_duplicated_material = self.duplicate_parametrize_material(fill_material)
            self._fill_material = self._fill_duplicated_material
            self._fill_material_name = self._fill_material.name
        self._thickness_variable = self._name + "_thickness"
        if thickness:
            self._thickness = NamedVariable(self._app, self._thickness_variable, self._app.value_with_units(thickness))
        else:
            self._thickness = None
        if self._layer_type == "dielectric":
            obj_3d = self._app.modeler.create_box(
                ["dielectric_x_position", "dielectric_y_position", layer_position],
                ["dielectric_length", "dielectric_width", self._thickness_variable],
                name=self._name,
                material=self.material_name,
            )
        elif self._layer_type == "ground":
            if thickness:
                obj_3d = self._app.modeler.create_box(
                    ["dielectric_x_position", "dielectric_y_position", layer_position],
                    ["dielectric_length", "dielectric_width", self._thickness_variable],
                    name=self._name,
                    material=self.material_name,
                )

            else:
                obj_3d = self._app.modeler.create_rectangle(
                    constants.PLANE.XY,
                    ["dielectric_x_position", "dielectric_y_position", layer_position],
                    ["dielectric_length", "dielectric_width"],
                    name=self._name,
                    matname=self.material_name,
                )
        elif self._layer_type == "signal":
            if thickness:
                obj_3d = self._app.modeler.create_box(
                    ["dielectric_x_position", "dielectric_y_position", layer_position],
                    ["dielectric_length", "dielectric_width", self._thickness_variable],
                    name=self._name,
                    material=self._fill_material.name,
                )
            else:
                obj_3d = self._app.modeler.create_rectangle(
                    constants.PLANE.XY,
                    ["dielectric_x_position", "dielectric_y_position", layer_position],
                    ["dielectric_length", "dielectric_width"],
                    name=self._name,
                    matname=self._fill_material.name,
                )
        obj_3d.group_name = f"Layer_{self._name}"
        if obj_3d:
            self._obj_3d.append(obj_3d)
        else:
            self._app.logger.error("Generation of the ground layer does not work.")

    @property
    def name(self):
        """Layer name.

        Returns
        -------
        str
        """
        return self._name

    @property
    def type(self):
        """Layer type.

        Returns
        -------
        str
        """
        return self._layer_type

    @property
    def number(self):
        """Layer ID.

        Returns
        -------
        int
        """
        return self._index

    @property
    def material_name(self):
        """Material name.

        Returns
        -------
        str
        """
        return self._material.name

    @property
    def material(self):
        """Material.

        Returns
        -------
        :class:`ansys.aedt.core.modules.material.Material`
            Material.
        """
        return self._material

    @property
    def duplicated_material(self):
        """Duplicated material.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.DuplicatedParametrizedMaterial`
            Material.
        """
        return self._duplicated_material

    @property
    def filling_material(self):
        """Fill material.

        Returns
        -------
        :class:`ansys.aedt.core.modules.material.Material`
            Material.
        """
        return self._fill_material

    @property
    def filling_material_name(self):
        """Fill material name.

        Returns
        -------
        str
        """
        return self._fill_material_name

    @property
    def thickness(self):
        """Thickness variable.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable Object.
        """
        return self._thickness

    @property
    def thickness_value(self):
        """Thickness value.


        Returns
        -------
        float, str
        """
        return self._thickness.value

    @thickness.setter
    def thickness(self, value):
        self._thickness.expression = value

    @property
    def elevation(self):
        """Layer elevation.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable object.
        """
        return self._position

    @property
    def elevation_value(self):
        """Layer elevation value.

        Returns
        -------
        str, float
        """
        return self._app.variable_manager[self._position.name].value

    @property
    def stackup(self):
        """Stackup.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.Stackup3D`
        """
        return self._stackup

    @property
    def frequency(self):
        """Frequency variable.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
        """
        return self._frequency

    @pyaedt_function_handler()
    def duplicate_parametrize_material(
        self,
        material_name,
        cloned_material_name=None,
        list_of_properties=(
            "permittivity",
            "permeability",
            "conductivity",
            "dielectric_loss_tangent",
            "magnetic_loss_tangent",
        ),
    ):
        """Duplicate a material and parametrize all properties.

        Parameters
        ----------
        material_name : str
            Name of origin material
        cloned_material_name : str, optional
            Name of destination material. The default is ``None``.
        list_of_properties : list, optional
            Properties to parametrize. The default is
            ``("permittivity", "permeability", "conductivity", "dielectric_loss_tan", "magnetic_loss_tan")``.

        Returns
        -------
        :class:`ansys.aedt.core.modules.material.Material`
            Material object.
        """
        if isinstance(material_name, Material):  # Make sure material_name is of type str.
            material_name = material_name.name
        if isinstance(cloned_material_name, Material):  # Make sure cloned_material_name is of type str.
            cloned_material_name = cloned_material_name.name
        if not cloned_material_name:  # If a name has not been defined, create one.
            cloned_material_name = "cloned_" + material_name
        for duplicated_material in self._stackup.duplicated_material_list:  # If the new material exists, don't
            if duplicated_material.name == cloned_material_name:  # return that material.
                return duplicated_material
        duplicated_material = self._app.materials.duplicate_material(
            material_name, cloned_material_name, properties=list_of_properties
        )
        #        duplicated_material = DuplicatedParametrizedMaterial(
        #            application, material_name, cloned_material_name, list_of_properties
        #        )
        self._stackup.duplicated_material_list.append(duplicated_material)
        return duplicated_material

    @pyaedt_function_handler()
    def add_patch(
        self,
        frequency,
        patch_width,
        patch_length=None,
        patch_position_x=0,
        patch_position_y=0,
        patch_name=None,
        axis="X",
    ):
        """Create a parametric patch.

        Parameters
        ----------
        frequency : float, None
            Frequency value for the patch calculation in Hz.
        patch_width : float
            Patch width.
        patch_length : float, optional
            Patch length. The default is ``None``.
        patch_position_x : float, optional
            Patch start x position.
        patch_position_y : float, optional
            Patch start y position. The default is ``0.``
        patch_name : str, optional
            Patch name. The default is ``None``.
        axis : str, optional
            Line orientation axis. The default is ``"X"``.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.Patch`

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> from ansys.aedt.core.modeler.advanced_cad.stackup_3d import Stackup3D
        >>> hfss = Hfss()
        >>> my_stackup = Stackup3D(hfss, 2.5e9)
        >>> gnd = my_stackup.add_ground_layer("gnd")
        >>> my_stackup.add_dielectric_layer("diel1", thickness=1.5, material="Duroid (tm)")
        >>> top = my_stackup.add_signal_layer("top")
        >>> my_patch = top.add_patch(frequency=None, patch_width=51, patch_name="MLPatch")
        >>> my_stackup.resize_around_element(my_patch)
        """
        if not patch_name:
            patch_name = generate_unique_name(f"{self._name}_patch", n=3)
        layer_names = self._stackup._layer_name

        # Find the layer where the patch should be placed.
        for i in range(len(layer_names)):
            if layer_names[i] == self._name:
                if self._stackup.stackup_layers[layer_names[i - 1]].type == "dielectric":
                    below_layer = self._stackup.stackup_layers[layer_names[i - 1]]
                    break
                else:
                    self._app.logger.error("The layer below the selected one must be of dielectric type.")
                    return False
        created_patch = Patch(
            self._app,
            frequency,
            patch_width,
            signal_layer=self,
            dielectric_layer=below_layer,
            dy=patch_length,
            patch_position_x=patch_position_x,
            patch_position_y=patch_position_y,
            patch_name=patch_name,
            axis=axis,
        )
        self._obj_3d.append(created_patch.aedt_object)
        self._stackup._object_list.append(created_patch)
        created_patch.aedt_object.group_name = f"Layer_{self._name}"
        return created_patch

    @pyaedt_function_handler()
    def ml_patch(
        self,
        frequency,
        patch_width,
        patch_position_x=0,
        patch_position_y=0,
        patch_name=None,
        axis="X",
    ):
        """Create a new parametric patch using machine learning algorithm rather than analytic formulas.

        Parameters
        ----------
        frequency : float, None
            Frequency value for patch calculation in Hz.
        patch_width : float
            Patch width.
        patch_position_x : float, optional
            Patch start x position.
        patch_position_y : float, optional
            Patch start y position.
        patch_name : str, optional
            Patch name.
        axis : str, optional
            Line orientation axis.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.MachineLearningPatch`

        Examples
        --------

        >>> from ansys.aedt.core import Hfss
        >>> from ansys.aedt.core.modeler.advanced_cad.stackup_3d import Stackup3D
        >>> hfss = Hfss()
        >>> my_stackup = Stackup3D(hfss, 2.5e9)
        >>> gnd = my_stackup.add_ground_layer("gnd")
        >>> my_stackup.add_dielectric_layer("diel1", thickness=1.5, material="Duroid (tm)")
        >>> top = my_stackup.add_signal_layer("top")
        >>> my_patch = top.ml_patch(frequency=None, patch_width=51, patch_name="MLPatch")
        >>> my_stackup.resize_around_element(my_patch)

        """
        if not patch_name:
            patch_name = generate_unique_name(f"{self._name}_patch", n=3)
        lst = self._stackup._layer_name
        for i in range(len(lst)):
            if lst[i] == self._name:
                if self._stackup.stackup_layers[lst[i - 1]].type == "dielectric":
                    below_layer = self._stackup.stackup_layers[lst[i - 1]]
                    break
                else:
                    self._app.logger.error("The layer below the selected one must be of dielectric type")
                    return False
        created_patch = MachineLearningPatch(
            self._app,
            frequency,
            patch_width,
            signal_layer=self,
            dielectric_layer=below_layer,
            patch_position_x=patch_position_x,
            patch_position_y=patch_position_y,
            patch_name=patch_name,
            axis=axis,
        )
        self._obj_3d.append(created_patch.aedt_object)
        self._stackup._object_list.append(created_patch)
        created_patch.aedt_object.group_name = f"Layer_{self._name}"
        return created_patch

    @pyaedt_function_handler()
    def add_trace(
        self,
        line_width,
        line_length,
        is_electrical_length=False,
        is_impedance=False,
        line_position_x=0,
        line_position_y=0,
        line_name=None,
        axis="X",
        reference_system=None,
        frequency=1e9,
    ):
        """Create a trace.

        Parameters
        ----------
        line_width : float
            Line width. It can be the physical width or the line impedance.
        line_length : float
            Line length. It can be the physical length or the electrical length in degrees.
        is_electrical_length : bool, optional
            Whether the line length is an electrical length or a physical length. The default
            is ``False``, which means it is a physical length.
        is_impedance : bool, optional
            Whether the line width is an impedance. The default is ``False``, in which case
            the line width is a geometrical value.
        line_position_x : float, optional
            Line center start x position. The default is ``0``.
        line_position_y : float, optional
            Line center start y position. The default is ``0``.
        line_name : str, optional
            Line name. The default is ``None``.
        axis : str, optional
            Line orientation axis. The default is ``"X"``.
        reference_system : str, optional
            Line reference system. The default is ``None``, in which case a new coordinate
            system is created.
        frequency : float, optional
            Frequency value for the line calculation in Hz. The default is ``1e9``.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.Trace`

        Examples
        --------

        >>> from ansys.aedt.core import Hfss
        >>> from ansys.aedt.core.modeler.advanced_cad.stackup_3d import Stackup3D
        >>> hfss = Hfss(new_desktop=True)
        >>> my_stackup = Stackup3D(hfss, 2.5e9)
        >>> gnd = my_stackup.add_ground_layer("gnd")
        >>> my_stackup.add_dielectric_layer("diel1", thickness=1.5, material="Duroid (tm)")
        >>> top = my_stackup.add_signal_layer("top")
        >>> my_trace = top.add_trace(line_width=2.5, line_length=22)
        >>> my_stackup.resize_around_element(my_trace)

        """
        if not line_name:
            line_name = generate_unique_name(f"{self._name}_line", n=3)
        dielectric_layer = None
        for v in list(self._stackup._stackup.values()):
            if v._index == self._index - 1:
                dielectric_layer = v
                break
        if dielectric_layer is None:
            for v in list(self._stackup._stackup.values()):
                if v._index == self._index + 1:
                    dielectric_layer = v
                    break
            if not dielectric_layer:
                self._app.logger.error("There is no layer under or over this layer.")
                return False

        created_line = Trace(
            self._app,
            frequency,
            line_width if not is_impedance else None,
            line_width if is_impedance else None,
            self,
            dielectric_layer,
            line_length=line_length if not is_electrical_length else None,
            line_electrical_length=line_length if is_electrical_length else None,
            line_position_x=line_position_x,
            line_position_y=line_position_y,
            line_name=line_name,
            reference_system=reference_system,
            axis=axis,
        )
        created_line.aedt_object.group_name = f"Layer_{self._name}"
        self._obj_3d.append(created_line.aedt_object)
        self._stackup._object_list.append(created_line)
        return created_line

    @pyaedt_function_handler()
    def add_polygon(self, points, material="copper", is_void=False, poly_name=None):
        """Create a polygon.

        Parameters
        ----------
        points : list
            Points list of [x,y] coordinates.
        material : str, optional
            Material name. The default is ``"copper"``.
        is_void : bool, optional
            Whether the polygon is a void. The default is ``False``.
            On ground layers, it will act opposite of the Boolean value because the ground
            is negative.
        poly_name : str, optional
            Polygon name. The default is ``None``.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.Polygon`

        Examples
        --------

        >>> from ansys.aedt.core import Hfss
        >>> from ansys.aedt.core.modeler.advanced_cad.stackup_3d import Stackup3D
        >>> hfss = Hfss()
        >>> my_stackup = Stackup3D(hfss, 2.5e9)
        >>> gnd = my_stackup.add_ground_layer("gnd")
        >>> my_stackup.add_dielectric_layer("diel1", thickness=1.5, material="Duroid (tm)")
        >>> top = my_stackup.add_signal_layer("top")
        >>> my_polygon = top.add_polygon([[0, 0], [0, 1], [1, 1], [1, 0]])
        >>> my_stackup.dielectric_x_position = "2mm"
        >>> my_stackup.dielectric_y_position = "2mm"
        >>> my_stackup.dielectric_length = "-3mm"
        >>> my_stackup.dielectric_width = "-3mm"

        """
        if not poly_name:
            poly_name = generate_unique_name(f"{self._name}_poly", n=3)
        polygon = Polygon(
            self._app,
            points,
            signal_layer=self,
            mat_name=material,
            is_void=is_void,
            poly_name=poly_name,
        )
        polygon.aedt_object.group_name = f"Layer_{self._name}"

        if self._layer_type == "ground":
            if not is_void:
                if polygon.aedt_object.is3d:
                    self._app.modeler[self._name].subtract(polygon.aedt_object, True)
                    polygon.aedt_object.material_name = self.filling_material_name
                else:
                    self._app.modeler[self._name].subtract(polygon.aedt_object, False)
                    return True
        elif is_void:
            if polygon.aedt_object.is3d:
                self._app.modeler.subtract(self._obj_3d, polygon.aedt_object, True)
                polygon.aedt_object.material_name = self.filling_material_name
            else:
                self._app.modeler[self._name].subtract(polygon.aedt_object, False)
                return True
        else:
            self._app.modeler.subtract(self._obj_3d[0], polygon.aedt_object, True)
            self._obj_3d.append(polygon.aedt_object)
            self._stackup._object_list.append(polygon)
        return polygon


class PadstackLayer(object):
    """Provides a data class for the definition of a padstack layer and relative pad and antipad values."""

    def __init__(self, padstack, layer_name, elevation, thickness):
        self._padstack = padstack
        self._layer_name = layer_name
        self._layer_elevation = elevation
        self._layer_thickness = thickness
        self._pad_radius = 1
        self._antipad_radius = 2
        self._units = "mm"

    @property
    def layer_name(self):
        """Padstack instance layer.

        Returns
        -------
        str
            Name of the padstack instance layer.
        """
        return self._layer_name

    @property
    def pad_radius(self):
        """Pad radius on the specified layer.

        Returns
        -------
        float
            Pad radius on the specified layer.
        """
        return self._pad_radius

    @pad_radius.setter
    def pad_radius(self, value):
        self._pad_radius = value

    @property
    def antipad_radius(self):
        """Antipad radius on the specified layer.

        Returns
        -------
        float
            Antipad radius on the specified layer.
        """
        return self._antipad_radius

    @antipad_radius.setter
    def antipad_radius(self, value):
        self._antipad_radius = value


class Padstack(object):
    """Provides the ``Padstack`` class member of Stackup3D."""

    def __init__(self, app, stackup, name, material="copper"):
        self._app = app
        self._stackup = stackup
        self.name = name
        self._padstacks_by_layer = {}
        self._vias_objects = []
        self._num_sides = 16
        self._plating_ratio = 1
        layer = None
        layer_name = None
        for layer_name, layer in self._stackup.stackup_layers.items():
            if self._padstacks_by_layer or layer.type != "dielectric":
                self._padstacks_by_layer[layer_name] = PadstackLayer(self, layer_name, layer.elevation, layer.thickness)
        if layer and layer.type == "dielectric":
            del self._padstacks_by_layer[layer_name]
        self._padstacks_material = material

    @property
    def plating_ratio(self):
        """Plating ratio between 0 and 1.

        Returns
        -------
        float
        """
        return self._plating_ratio

    @plating_ratio.setter
    def plating_ratio(self, val):
        if isinstance(val, (float, int)) and 0 < val <= 1:
            self._plating_ratio = val
        elif isinstance(val, str):
            self._plating_ratio = val
        else:
            self._app.logger.error("Plating has to be between 0 and 1.")

    @property
    def padstacks_by_layer(self):
        """Get the padstack definitions by layers.

        Returns
        -------
        dict
            Dictionary of padstack definitions by layers.
        """
        return self._padstacks_by_layer

    @property
    def num_sides(self):
        """Number of sides on the circle, which is ``0`` for a true circle.

        Returns
        -------
        int
        """
        return self._num_sides

    @num_sides.setter
    def num_sides(self, val):
        self._num_sides = val

    @pyaedt_function_handler()
    def set_all_pad_value(self, value):
        """Set all pads in all layers to a specified value.

        Parameters
        ----------
        value : float
            Pad radius.

        Returns
        -------
        bool
            "True`` when successful, ``False`` when failed.
        """
        for v in list(self._padstacks_by_layer.values()):
            v._pad_radius = value
        return True

    @pyaedt_function_handler()
    def set_all_antipad_value(self, value):
        """Set all antipads in all layers to a specified value.

        Parameters
        ----------
        value : float
            Pad radius.

        Returns
        -------
        bool
             "True`` when successful, ``False`` when failed.
        """
        for v in list(self._padstacks_by_layer.values()):
            v._antipad_radius = value
        return True

    @pyaedt_function_handler()
    def set_start_layer(self, layer):
        """Set the start layer to a specified value.

        Parameters
        ----------
        layer : str
            Layer name.

        Returns
        -------
        bool
             "True`` when successful, ``False`` when failed.

        """
        found = False
        new_stackup = {}
        for k, v in self._stackup.stackup_layers.items():
            if k == layer:
                found = True
            if found and layer not in self._padstacks_by_layer:
                new_stackup[k] = PadstackLayer(self, k, v.elevation, v.thickness)
            elif found:
                new_stackup[k] = self._padstacks_by_layer[k]
        if not found:
            raise ValueError(f"The layer named: '{layer}' does not exist")
        self._padstacks_by_layer = new_stackup
        return True

    @pyaedt_function_handler()
    def set_stop_layer(self, layer):
        """Set the stop layer to a specified value.

        Parameters
        ----------
        layer : str
            Layer name.

        Returns
        -------
        bool
             "True`` when successful, ``False`` when failed.

        """
        found = False
        new_stackup = {}
        for k in list(self._stackup.stackup_layers.keys()):
            if not found and k in list(self._padstacks_by_layer.keys()):
                new_stackup[k] = self._padstacks_by_layer[k]
            if k == layer:
                found = True
        self._padstacks_by_layer = new_stackup
        return True

    @pyaedt_function_handler()
    def add_via(self, position_x=0, position_y=0, instance_name=None, reference_system=None):
        """Insert a new via on this padstack.

        Parameters
        ----------
        position_x : float, optional
            Center x position. The default is ``0``.
        position_y : float, optional
            Center y position. The default is ``0``.
        instance_name : str, optional
            Via name. The default is ``None``.
        reference_system : str, optional
            Whether to use an existing reference system or create a new one. The default
            is ``None``, in which case a new reference system is created.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
            Object created.
        """
        if not instance_name:
            instance_name = generate_unique_name(f"{self.name}_", n=3)
            if reference_system:
                self._app.modeler.set_working_coordinate_system(reference_system)
                self._reference_system = reference_system
            else:
                self._app.modeler.create_coordinate_system(
                    origin=[0, 0, 0], reference_cs="Global", name=instance_name + "_CS"
                )
                self._app.modeler.set_working_coordinate_system(instance_name + "_CS")
                self._reference_system = instance_name + "_CS"

            cyls = []
            for v in list(self._padstacks_by_layer.values()):
                position_x = self._app.value_with_units(position_x)
                position_y = self._app.value_with_units(position_y)
                if v._pad_radius > 0:
                    cyls.append(
                        self._app.modeler.create_cylinder(
                            "Z",
                            [position_x, position_y, v._layer_elevation.name],
                            v._pad_radius,
                            v._layer_thickness.name,
                            num_sides=self._num_sides,
                            name=instance_name,
                            material=self._padstacks_material,
                        )
                    )
                    if self.plating_ratio < 1:
                        hole = self._app.modeler.create_cylinder(
                            "Z",
                            [position_x, position_y, v._layer_elevation.name],
                            f"{self._app.value_with_units(v._pad_radius)}*{1 - self.plating_ratio}",
                            v._layer_thickness.name,
                            num_sides=self._num_sides,
                            name=instance_name,
                            material=self._padstacks_material,
                        )
                        cyls[-1].subtract(hole, False)
                if v._antipad_radius > 0:
                    anti = self._app.modeler.create_cylinder(
                        "Z",
                        [position_x, position_y, v._layer_elevation.name],
                        v._antipad_radius,
                        v._layer_thickness.name,
                        num_sides=self._num_sides,
                        name=instance_name + "_antipad",
                        material="air",
                    )
                    self._app.modeler.subtract(
                        self._stackup._signal_list + self._stackup._ground_list + self._stackup._dielectric_list,
                        anti,
                        False,
                    )
            if len(cyls) > 1:
                self._app.modeler.unite(cyls)
            if cyls:
                self._vias_objects.append(cyls[0])
                cyls[0].group_name = "Vias"
                self._stackup._vias.append(self)
                return cyls[0]
            else:
                return


class Stackup3D(object):
    """Main Stackup3D Class.

    Parameters
    ----------
    application : :class:`ansys.aedt.core.hfss.Hfss`
        HFSS design or project where the variable is to be created.
    frequency : float
        The stackup frequency, it will be common to all layers in the stackup.

    Examples
    --------

    >>> from ansys.aedt.core import Hfss
    >>> from ansys.aedt.core.modeler.advanced_cad.stackup_3d import Stackup3D
    >>> hfss = Hfss(new_desktop=True)
    >>> my_stackup = Stackup3D(hfss, 2.5e9)

    """

    def __init__(self, application, frequency=None):
        self._app = application
        self._layer_name = []
        self._layer_position = []
        self._dielectric_list = []
        self._dielectric_name_list = []
        self._ground_list = []
        self._ground_name_list = []
        self._ground_fill_material = []
        self._signal_list = []
        self._signal_name_list = []
        self._signal_material = []
        self._duplicated_material_list = []
        self._object_list = []
        self._vias = []
        self._z_position_offset = 0
        self._first_layer_position = "layer_1_position"
        self._shifted_index = 0
        self._stackup = {}
        self._start_position = NamedVariable(self._app, self._first_layer_position, "0mm")
        self._dielectric_x_position = NamedVariable(self._app, "dielectric_x_position", "0mm")
        self._dielectric_y_position = NamedVariable(self._app, "dielectric_y_position", "0mm")
        self._dielectric_width = NamedVariable(self._app, "dielectric_width", "1000mm")
        self._dielectric_length = NamedVariable(self._app, "dielectric_length", "1000mm")
        self._end_of_stackup3D = NamedVariable(self._app, "StackUp_End", "layer_1_position")
        self._stackup_thickness = NamedVariable(self._app, "StackUp_Thickness", "StackUp_End-layer_1_position")

        if frequency:
            self._frequency = NamedVariable(self._app, "frequency", str(frequency) + "Hz")
        else:
            self._frequency = frequency
        self._padstacks = []

    @property
    def thickness(self):
        """Total stackup thickness.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
        """
        return self._stackup_thickness

    @property
    def application(self):
        """Application object.

        Returns
        -------
        :class:`ansys.aedt.core.hfss.Hfss`
        """
        return self._app

    @property
    def padstacks(self):
        """List of definitions created.

        Returns
        -------
        List
        """
        return self._padstacks

    @property
    def dielectrics(self):
        """List of dielectrics created.

        Returns
        -------
        List
        """
        return self._dielectric_list

    @property
    def grounds(self):
        """List of grounds created.

        Returns
        -------
        List
        """
        return self._ground_list

    @property
    def signals(self):
        """List of signals created.

        Returns
        -------
        List
        """
        return self._signal_list

    @property
    def objects(self):
        """List of objects created.

        Returns
        -------
        List
        """
        return self._object_list

    @property
    def objects_by_layer(self):
        """List of definitions created.

        Returns
        -------
        List
        """
        objs = {}
        for obj in self.objects:
            if objs.get(obj.layer_name, None):
                objs[obj.layer_name].append(obj)
            else:
                objs[obj.layer_name] = [obj]
        return objs

    @property
    def start_position(self):
        """Variable containing the start position.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
        """
        return self._start_position

    @start_position.setter
    def start_position(self, expression):
        self._start_position.expression = expression

    @property
    def dielectric_x_position(self):
        """Stackup x origin.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable object.
        """
        return self._dielectric_x_position

    @dielectric_x_position.setter
    def dielectric_x_position(self, expression):
        self._dielectric_x_position.expression = expression

    @property
    def dielectric_y_position(self):
        """Stackup y origin.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable object.
        """
        return self._dielectric_x_position

    @dielectric_y_position.setter
    def dielectric_y_position(self, expression):
        self._dielectric_y_position.expression = expression

    @property
    def dielectric_width(self):
        """Stackup width.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable object.
        """
        return self._dielectric_width

    @dielectric_width.setter
    def dielectric_width(self, expression):
        self._dielectric_width.expression = expression

    @property
    def dielectric_length(self):
        """Stackup length.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable object.
        """
        return self._dielectric_length

    @dielectric_length.setter
    def dielectric_length(self, expression):
        self._dielectric_length.expression = expression

    @property
    def layer_names(self):
        """List of all layer names.

        Returns
        -------
        list
        """
        return self._layer_name

    @property
    def layer_positions(self):
        """List of all layer positions.

        Returns
        -------
        List
        """
        return self._layer_position

    @property
    def stackup_layers(self):
        """Dictionary of all stackup layers.

        Returns
        -------
        dict
        """
        return self._stackup

    @property
    def z_position_offset(self):
        """Elevation.

        Returns
        -------

        """
        return self._z_position_offset

    @property
    def frequency(self):
        """Frequency variable.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
        """
        return self._frequency

    @property
    def duplicated_material_list(self):
        """List of all duplicated material.

        Returns
        -------
        List
        """
        return self._duplicated_material_list

    @pyaedt_function_handler()
    def add_padstack(self, name, material="copper"):
        """Add a new padstack definition.

        Parameters
        ----------
        name : str
            padstack name
        material : str, optional
            Padstack material. The default is ``"copper"``.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.Padstack`
        """
        p = Padstack(self._app, self, name, material)
        self._padstacks.append(p)
        return p

    @pyaedt_function_handler()
    def add_layer(
        self, name, layer_type="S", material_name="copper", thickness=0.035, fill_material="FR4_epoxy", frequency=None
    ):
        """Add a new layer to the stackup.

        The new layer can be a signal (S), ground (G), or dielectric (D).
        The layer is entirely filled with the specified fill material. Anything will be drawn
        material.

        Parameters
        ----------
        name : str
            Layer name.
        layer_type : str, optional
            Layer type. The default is ``"S"``. Options are:

             - ``"D"`` for "dielectric" layer
             - ``"G"`` for "ground" layer
             - ``"S"`` for "signal" layer

        material_name : str, optional
            Material name. The default is ``"copper"``. The material is parametrized.
        thickness : float, optional
            Thickness value. The default is ``0.035``. The thickness will be parametrized.
        fill_material : str, optional
            Fill material name. The default is ``"FR4_epoxy"``. The fill material will be
            parametrized. This parameter is not valid for dielectrics.
        frequency : float, optional
            The layer frequency, it will be common to all geometric shapes on the layer. The default is None, so each
            shape must have their own frequency.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.Layer3D`
            Layer object.

        Examples
        --------

        >>> from ansys.aedt.core import Hfss
        >>> from ansys.aedt.core.modeler.advanced_cad.stackup_3d import Stackup3D
        >>> hfss = Hfss()
        >>> my_stackup = Stackup3D(hfss, 2.5e9)
        >>> my_layer = my_stackup.add_layer("my_layer")

        """
        self._shifted_index += 1
        if not layer_type:
            raise ValueError("Layer type has to be an S, D, or G string.")
        self._layer_name.append(name)  # update the list of layer names.

        lay = Layer3D(
            stackup=self,
            app=self._app,
            name=name,
            layer_type=layer_type,
            material_name=material_name,
            thickness=thickness,
            fill_material=fill_material,
            index=self._shifted_index,
            frequency=frequency,
        )
        self._layer_position_manager(lay)
        if layer_type == "D":
            self._dielectric_list.extend(lay._obj_3d)
            self._dielectric_name_list.append(lay._name)
            lay._obj_3d[-1].transparency = "0.8"
        elif layer_type == "G":
            self._ground_list.extend(lay._obj_3d)
            self._ground_name_list.append(lay._name)
            self._ground_fill_material.append(lay._fill_material)
            lay._obj_3d[-1].transparency = "0.6"
            lay._obj_3d[-1].color = (255, 0, 0)

        elif layer_type == "S":
            self._signal_list.extend(lay._obj_3d)
            self._signal_name_list.append(lay._name)
            self._signal_material.append(lay.material_name)
            lay._obj_3d[-1].transparency = "0.8"
        self._stackup[lay._name] = lay
        return lay

    @pyaedt_function_handler()
    def add_signal_layer(self, name, material="copper", thickness=0.035, fill_material="FR4_epoxy", frequency=None):
        """Add a new ground layer to the stackup.

        A signal layer is positive. The layer is entirely filled with the fill material.
        Anything will be drawn material.

        Parameters
        ----------
        name : str
            Layer name.
        material : str
            Material name. Material will be parametrized.
        thickness : float, str, None
            Thickness value. Thickness will be parametrized.
        fill_material : str
            Fill Material name. Material will be parametrized.=
        material : str, optional
            Material name. Material will be parametrized. Default value is `"copper"`.
        thickness : float, optional
            Thickness value. Thickness will be parametrized. Default value is `0.035`.
        fill_material : str, optional
            Fill material name. Material will be parametrized. Default value is `"FR4_epoxy"`.
        frequency : float, optional
            The layer frequency, it will be common to all geometric shapes on the layer. The default is None, so each
            shape must have their own frequency.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.Layer3D`
            Layer object.

        Examples
        --------

        >>> from ansys.aedt.core import Hfss
        >>> from ansys.aedt.core.modeler.advanced_cad.stackup_3d import Stackup3D
        >>> hfss = Hfss()
        >>> my_stackup = Stackup3D(hfss, 2.5e9)
        >>> my_signal_layer = my_stackup.add_signal_layer("signal_layer")

        """
        return self.add_layer(
            name=name,
            layer_type="S",
            material_name=material,
            thickness=thickness,
            fill_material=fill_material,
            frequency=frequency,
        )

    @pyaedt_function_handler()
    def add_dielectric_layer(self, name, material="FR4_epoxy", thickness=0.035, frequency=None):
        """Add a new dielectric layer to the stackup.

        Parameters
        ----------
        name : str
            Layer name.
        material : str
            Material name. The default is ``"FR4_epoxy"``. The material will be parametrized.
        thickness : float, str, optional
            Thickness value. The default is ``0.035``. The thickness will be parametrized.
        frequency : float, optional
            The layer frequency, it will be common to all geometric shapes on the layer. The default is None, so each
            shape must have their own frequency.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.Layer3D`
            Layer object.

        Examples
        --------

        >>> from ansys.aedt.core import Hfss
        >>> from ansys.aedt.core.modeler.advanced_cad.stackup_3d import Stackup3D
        >>> hfss = Hfss()
        >>> my_stackup = Stackup3D(hfss, 2.5e9)
        >>> my_dielectric_layer = my_stackup.add_dielectric_layer("diel", thickness=1.5, material="Duroid (tm)")

        """
        return self.add_layer(
            name=name,
            layer_type="D",
            material_name=material,
            thickness=thickness,
            fill_material=None,
            frequency=frequency,
        )

    @pyaedt_function_handler()
    def add_ground_layer(self, name, material="copper", thickness=0.035, fill_material="air", frequency=None):
        """Add a new ground layer to the stackup.

        A ground layer is negative.
        The layer is entirely filled with  metal. Any polygon will draw a void in it.

        Parameters
        ----------
        name : str
            Layer name.
        material : str, op
            Material name. Material will be parametrized.
        thickness : float, str, None
            Thickness value. Thickness will be parametrized.
        fill_material : str
            Fill Material name. Material will be parametrized.
        frequency : float, optional
            The layer frequency, it will be common to all geometric shapes on the layer. The default is None, so each
            shape must have their own frequency.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.Layer3D`
            Layer Object.

        Examples
        --------

        >>> from ansys.aedt.core import Hfss
        >>> from ansys.aedt.core.modeler.advanced_cad.stackup_3d import Stackup3D
        >>> hfss = Hfss()
        >>> my_stackup = Stackup3D(hfss, 2.5e9)
        >>> my_ground_layer = my_stackup.add_ground_layer("gnd")

        """
        return self.add_layer(
            name=name,
            layer_type="G",
            material_name=material,
            thickness=thickness,
            fill_material=fill_material,
            frequency=frequency,
        )

    @pyaedt_function_handler()
    def _layer_position_manager(self, layer):
        """Set the last layer of the stackup.

        Parameters
        ----------
        layer

        Returns
        -------

        """
        previous_layer_end = self._end_of_stackup3D.expression

        layer.elevation.expression = previous_layer_end
        if layer.thickness:
            self._end_of_stackup3D.expression = layer.elevation.name + " + " + layer.thickness.name
        else:
            self._end_of_stackup3D.expression = layer.elevation.name

    @pyaedt_function_handler()
    def resize(self, percentage_offset):
        """Resize the stackup around objects created by a percentage offset.

        Parameters
        ----------
        percentage_offset : float
            Offset of resize. The value must be greater than 0.

        Returns
        -------
        bool
        """
        list_of_2d_points = []
        list_of_x_coordinates = []
        list_of_y_coordinates = []
        for obj3d in self._object_list:
            points_list_by_object = obj3d.points_on_layer
            list_of_2d_points = points_list_by_object + list_of_2d_points
        for via in self._vias:
            for v in via._vias_objects:
                list_of_x_coordinates.append(v.bounding_box[0] - v.bounding_dimension[0])
                list_of_x_coordinates.append(v.bounding_box[3] - v.bounding_dimension[0])
                list_of_y_coordinates.append(v.bounding_box[1] - v.bounding_dimension[1])
                list_of_y_coordinates.append(v.bounding_box[4] - v.bounding_dimension[1])
                list_of_x_coordinates.append(v.bounding_box[0] + v.bounding_dimension[0])
                list_of_x_coordinates.append(v.bounding_box[4] + v.bounding_dimension[0])
                list_of_y_coordinates.append(v.bounding_box[4] + v.bounding_dimension[1])
                list_of_y_coordinates.append(v.bounding_box[1] + v.bounding_dimension[1])
        for point in list_of_2d_points:
            list_of_x_coordinates.append(point[0])
            list_of_y_coordinates.append(point[1])
        maximum_x = max(list_of_x_coordinates)
        minimum_x = min(list_of_x_coordinates)
        maximum_y = max(list_of_y_coordinates)
        minimum_y = min(list_of_y_coordinates)
        variation_x = abs(maximum_x - minimum_x)
        variation_y = abs(maximum_y - minimum_y)
        self._app["dielectric_x_position"] = self._app.value_with_units(
            minimum_x - variation_x * percentage_offset / 100
        )
        self._app["dielectric_y_position"] = self._app.value_with_units(
            minimum_y - variation_y * percentage_offset / 100
        )
        self._app["dielectric_length"] = self._app.value_with_units(
            maximum_x - minimum_x + 2 * variation_x * percentage_offset / 100
        )
        self._app["dielectric_width"] = self._app.value_with_units(
            maximum_y - minimum_y + 2 * variation_y * percentage_offset / 100
        )
        return True

    def resize_around_element(self, element, percentage_offset=0.25):
        """Resize the stackup around parametrized objects and make it parametrize.

        Parameters
        ----------
        element : :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.Patch,
            :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.Trace
            Element around which the resizing is done.
        percentage_offset : float, optional
            Offset of resize. Value accepted are greater than 0. O.25 by default.

        Returns
        -------
        bool

        Examples
        --------

        >>> from ansys.aedt.core import Hfss
        >>> from ansys.aedt.core.modeler.advanced_cad.stackup_3d import Stackup3D
        >>> hfss = Hfss()
        >>> my_stackup = Stackup3D(hfss, 2.5e9)
        >>> gnd = my_stackup.add_ground_layer("gnd")
        >>> my_stackup.add_dielectric_layer("diel1", thickness=1.5, material="Duroid (tm)")
        >>> top = my_stackup.add_signal_layer("top")
        >>> my_patch = top.add_patch(frequency=None, patch_width=51, patch_name="MLPatch")
        >>> my_stackup.resize_around_element(my_patch)

        """
        self.dielectric_x_position = (
            element.position_x.name + " - " + element.length.name + " * " + str(percentage_offset)
        )
        self.dielectric_y_position = (
            element.position_y.name + " - " + element.width.name + " * (0.5 + " + str(percentage_offset) + ")"
        )
        self.dielectric_length.expression = element.length.name + " * (1 + " + str(percentage_offset) + " * 2)"
        self.dielectric_width.expression = element.width.name + " * (1 + " + str(percentage_offset) + " * 2)"
        return True


class CommonObject(object):
    """CommonObject Class in Stackup3D. This class must not be directly used."""

    def __init__(self, application):
        self._app = application
        self._name = None
        self._dielectric_layer = None
        self._signal_layer = None
        self._aedt_object = None
        self._layer_name = None
        self._layer_number = None
        self._material_name = None
        self._reference_system = None

    @property
    def reference_system(self):
        """Coordinate system of the object.

        Returns
        -------
        str
        """
        return self._reference_system

    @property
    def dielectric_layer(self):
        """Dielectric layer that the object belongs to.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.Layer3D`
        """
        return self._dielectric_layer

    @property
    def signal_layer(self):
        """Signal layer that the object belongs to.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.Layer3D`
        """
        return self._signal_layer

    @property
    def name(self):
        """Object name.

        Returns
        -------
        str
        """
        return self._name

    @property
    def application(self):
        """App object."""
        return self._app

    @property
    def aedt_object(self):
        """PyAEDT object 3D.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.cad.object_3d.Object3d`
        """
        return self._aedt_object

    @property
    def layer_name(self):
        """Layer name.

        Returns
        -------
        str
        """
        return self._layer_name

    @property
    def layer_number(self):
        """Layer ID.

        Returns
        -------
        int
        """
        return self._layer_number

    @property
    def material_name(self):
        """Material name.

        Returns
        -------
        str
        """
        return self._material_name

    @property
    def points_on_layer(self):
        """Object bounding box.

        Returns
        -------
        List
            List of [x,y] coordinate of the bounding box.
        """
        bb = self._aedt_object.bounding_box
        return [[bb[0], bb[1]], [bb[0], bb[4]], [bb[3], bb[4]], [bb[3], bb[1]]]


class Patch(CommonObject, object):
    """Patch Class in Stackup3D. Create a parametrized patch.

    It is preferable to use the add_patch method
    in the class Layer3D than directly the class constructor.

    Parameters
    ----------
    application : :class:`ansys.aedt.core.hfss.Hfss`
        HFSS design or project where the variable is to be created.
    frequency : float, None
        Target resonant frequency for the patch antenna. The default is ``None``,
        in which case the patch frequency is that of the
        layer or of the stackup.
    dx : float
        The patch width.
    signal_layer : :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.Layer3D`
        The signal layer where the patch will be drawn.
    dielectric_layer : :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.Layer3D`
        The dielectric layer between the patch and the ground layer. Its permittivity and thickness are used in
        prediction formulas.
    dy : float, None, optional
        The patch length. By default, it is None and so the length is calculated by prediction formulas.
    patch_position_x : float, optional
        Patch x position, by default it is 0.
    patch_position_y : float, optional
        Patch y position, by default it is 0.
    patch_name : str, optional
        Patch name, by  default "patch".
    reference_system : str, None, optional
        Coordinate system of the patch. By default, None.
    axis : str, optional
        Patch length axis, by default "X".

    Examples
    --------
    >>> from ansys.aedt.core import Hfss
    >>> from ansys.aedt.core.modeler.advanced_cad.stackup_3d import Stackup3D
    >>> hfss = Hfss()
    >>> stackup = Stackup3D(hfss)
    >>> gnd = stackup.add_ground_layer("ground", material="copper", thickness=0.035, fill_material="air")
    >>> dielectric = stackup.add_dielectric_layer("dielectric", thickness="0.5" + length_units, material="Duroid (tm)")
    >>> signal = stackup.add_signal_layer("signal", material="copper", thickness=0.035, fill_material="air")
    >>> patch = signal.add_patch(patch_length=9.57, patch_width=9.25, patch_name="Patch")
    >>> stackup.resize_around_element(patch)
    >>> pad_length = [3, 3, 3, 3, 3, 3]  # Air bounding box buffer in mm.
    >>> region = hfss.modeler.create_region(pad_length,is_percentage=False)
    >>> hfss.assign_radiation_boundary_to_objects(region)
    >>> patch.create_probe_port(gnd, rel_x_offset=0.485)

    """

    def __init__(
        self,
        application,
        frequency,
        dx,
        signal_layer,
        dielectric_layer,
        dy=None,
        patch_position_x=0,
        patch_position_y=0,
        patch_name="patch",
        reference_system=None,
        axis="X",
    ):
        CommonObject.__init__(self, application)
        if frequency:
            self._frequency = NamedVariable(application, patch_name + "_frequency", str(frequency) + "Hz")
        elif signal_layer.frequency:
            self._frequency = signal_layer.frequency
        else:
            self._frequency = signal_layer.stackup.frequency
        if not self._frequency:
            self.application.logger.error("The patch frequency must not be None.")
        self._signal_layer = signal_layer
        self._dielectric_layer = dielectric_layer
        self._substrate_thickness = dielectric_layer.thickness
        self._width = NamedVariable(application, patch_name + "_width", application.value_with_units(dx))
        self._position_x = NamedVariable(
            application, patch_name + "_position_x", application.value_with_units(patch_position_x)
        )
        self._position_y = NamedVariable(
            application, patch_name + "_position_y", application.value_with_units(patch_position_y)
        )
        self._position_z = signal_layer.elevation
        self._dielectric_layer = dielectric_layer
        self._signal_layer = signal_layer
        self._dielectric_material = dielectric_layer.material
        self._material_name = signal_layer.material_name
        self._layer_name = signal_layer.name
        self._layer_number = signal_layer.number
        self._name = patch_name
        self._patch_thickness = signal_layer.thickness
        self._application = application
        self._aedt_object = None
        self._permittivity = NamedVariable(
            application,
            patch_name + "_permittivity",
            self._dielectric_layer.duplicated_material.permittivity.value,  # value -> name
        )
        if isinstance(dy, float) or isinstance(dy, int):
            self._length = NamedVariable(application, patch_name + "_length", application.value_with_units(dy))
            self._effective_permittivity = self._effective_permittivity_calcul
            self._wave_length = self._wave_length_calcul
        elif dy is None:
            self._effective_permittivity = self._effective_permittivity_calcul
            self._added_length = self._added_length_calcul
            self._wave_length = self._wave_length_calcul
            self._length = self._length_calcul
        self._impedance_l_w, self._impedance_w_l = self._impedance_calcul
        if reference_system:
            application.modeler.set_working_coordinate_system(reference_system)
            if axis == "X":
                start_point = [
                    f"{self._name}_position_x",
                    f"{self._name}_position_y-{0}_width/2",
                    0,
                ]
            else:
                start_point = [
                    f"{self._name}_position_x-{0}_width/2",
                    f"{self._name}_position_y",
                    0,
                ]
            self._reference_system = reference_system
        else:
            application.modeler.create_coordinate_system(
                origin=[
                    f"{patch_name}_position_x",
                    f"{patch_name}_position_y",
                    signal_layer.elevation.name,
                ],
                reference_cs="Global",
                name=patch_name + "_CS",
            )
            if axis == "X":
                start_point = [0, f"-{patch_name}_width/2", 0]

            else:
                start_point = [f"-{patch_name}_width/2", 0, 0]
            application.modeler.set_working_coordinate_system(patch_name + "_CS")

            self._reference_system = patch_name + "_CS"
        if signal_layer.thickness:
            self._aedt_object = application.modeler.create_box(
                origin=start_point,
                sizes=[
                    f"{patch_name}_length",
                    f"{patch_name}_width",
                    signal_layer.thickness.name,
                ],
                name=patch_name,
                material=signal_layer.material_name,
            )
        else:
            self._aedt_object = application.modeler.create_rectangle(
                origin=start_point,
                sizes=[self.length.name, self.width.name],
                name=patch_name,
                material=signal_layer.material_name,
            )
            application.assign_coating(self._aedt_object.name, signal_layer.material)
        application.modeler.set_working_coordinate_system("Global")
        application.modeler.subtract(blank_list=[signal_layer.name], tool_list=[patch_name], keep_originals=True)

    @property
    def frequency(self):
        """Model frequency.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable Object.
        """
        return self._frequency

    @property
    def substrate_thickness(self):
        """Substrate thickness.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable Object.
        """
        return self._substrate_thickness

    @property
    def width(self):
        """Width.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable object.
        """
        return self._width

    @property
    def position_x(self):
        """Starting position X.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable object.
        """
        return self._position_x

    @property
    def position_y(self):
        """Starting position Y.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable object.
        """
        return self._position_y

    @property
    def permittivity(self):
        """Permittivity.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable object.
        """
        return self._permittivity

    @property
    def _permittivity_calcul(self):
        """Permittivity calculation.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable object.
        """
        self._permittivity = self.application.materials[self._dielectric_material].permittivity
        return self._permittivity

    @property
    def effective_permittivity(self):
        """Effective permittivity.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable object.
        """
        return self._effective_permittivity

    @property
    def _effective_permittivity_calcul(self):
        """Create a NamedVariable containing the calculation of the patch effective permittivity and return it.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable object.
        """
        # "(substrat_permittivity + 1)/2 + (substrat_permittivity -
        # 1)/(2 * sqrt(1 + 12 * substrate_thickness/patch_width))"
        er = self._permittivity.name
        h = self._substrate_thickness.name
        w = self._width.name
        patch_eff_permittivity_formula = "(" + er + "+ 1)/2 + (" + er + "- 1)/(2 * sqrt(1 + 12 * " + h + "/" + w + "))"
        self._effective_permittivity = NamedVariable(
            self.application, self._name + "_eff_permittivity", patch_eff_permittivity_formula
        )
        return self._effective_permittivity

    @property
    def added_length(self):
        """Added length calculation.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable object.
        """
        return self._added_length

    @property
    def _added_length_calcul(self):
        """Create a NamedVariable containing the calculation of the patch added length and return it.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable object.
        """
        # "0.412 * substrate_thickness * (patch_eff_permittivity + 0.3) * (patch_width/substrate_thickness + 0.264)"
        # " / ((patch_eff_permittivity - 0.258) * (patch_width/substrate_thickness + 0.813)) "

        er_e = self._effective_permittivity.name
        h = self._substrate_thickness.name
        w = self._width.name
        patch_added_length_formula = (
            "0.412 * " + h + " * (" + er_e + " + 0.3) * (" + w + "/" + h + " + 0.264)/"
            "((" + er_e + " - 0.258) * (" + w + "/" + h + " + 0.813))"
        )
        self._added_length = NamedVariable(self.application, self._name + "_added_length", patch_added_length_formula)
        return self._added_length

    @property
    def wave_length(self):
        """Wave length.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable Object.
        """
        return self._wave_length

    @property
    def _wave_length_calcul(self):
        """Create a NamedVariable containing the calculation of the patch wave length and return it.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable Object.
        """
        # "c0 * 1000/(patch_frequency * sqrt(patch_eff_permittivity))"
        f = self._frequency.name
        er_e = self._effective_permittivity.name
        patch_wave_length_formula = "(c0 * 1000/(" + f + "* sqrt(" + er_e + ")))mm"
        self._wave_length = NamedVariable(
            self.application,
            self._name + "_wave_length",
            self.application.value_with_units(patch_wave_length_formula),
        )
        return self._wave_length

    @property
    def length(self):
        """Length.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable Object.
        """
        return self._length

    @property
    def _length_calcul(self):
        """Create a NamedVariable containing the calculation of the patch length and return it.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable Object.
        """
        # "patch_wave_length / 2 - 2 * patch_added_length"
        d_l = self._added_length.name
        lbd = self._wave_length.name
        patch_length_formula = lbd + "/2" + " - 2 * " + d_l
        self._length = NamedVariable(self.application, self._name + "_length", patch_length_formula)
        return self._length

    @property
    def impedance(self):
        """Impedance.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable Object.
        """
        return self._impedance_l_w, self._impedance_w_l

    @property
    def _impedance_calcul(self):
        """Create NamedVariable containing the calculations of the patch impedance and return it.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable Object.
        """
        # "45 * (patch_wave_length/patch_width * sqrt(patch_eff_permittivity)) ** 2"
        # "60 * patch_wave_length/patch_width * sqrt(patch_eff_permittivity)"
        # "90 * (patch_permittivity)**2/(patch_permittivity -1) * dy/patch_width
        er_e = self._effective_permittivity.name
        lbd = self._wave_length.name
        w = self._width.name
        l = self.length.name
        er = self.permittivity.name
        patch_impedance_formula_l_w = "45 * (" + lbd + "/" + w + "* sqrt(" + er_e + ")) ** 2"
        patch_impedance_formula_w_l = "60 * " + lbd + "/" + w + "* sqrt(" + er_e + ")"
        patch_impedance_balanis_formula = "90 *" + er + "**2/(" + er + " - 1) * " + l + "/" + w
        self._impedance_l_w = NamedVariable(
            self.application, self._name + "_impedance_l_w", patch_impedance_formula_l_w
        )
        self._impedance_w_l = NamedVariable(
            self.application, self._name + "_impedance_w_l", patch_impedance_formula_w_l
        )
        self._impedance_bal = NamedVariable(
            self.application, self._name + "_impedance_bal", patch_impedance_balanis_formula
        )
        self.application.logger.warning(
            "The closer the ratio between wave length and the width is to 1,"
            " the less correct the impedance calculation is"
        )
        return self._impedance_l_w, self._impedance_w_l

    def create_probe_port(self, reference_layer, rel_x_offset=0, rel_y_offset=0, r=0.01, name="Probe"):
        """Create a coaxial probe port for the patch.

        Parameters
        ----------
        reference_layer : class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.Layer3D`
            Reference layer (ground).

        rel_x_offset : float,
            Relative x-offset for probe feed.
            Provide a value between 0.0 and 1.0.
            Offset in the x-direction relative to the center of the patch.
            `0` places the probe at the center of the patch.
            `1` places the probe at the edge of the patch.
            Default: 0

        rel_y_offset : float, value between 0 and 1
            `0` places the probe at the center of the patch.
            `1` places the probe at the edge of the patch.
            Default: 0

        d : float, probe diameter
            Default: 0.01

        name : str, optional name of probe port.
            Default value `"Probe"`

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------

        >>> from ansys.aedt.core import Hfss
        >>> from ansys.aedt.core.modeler.advanced_cad.stackup_3d import Stackup3D
        >>> hfss = Hfss()
        >>> my_stackup = Stackup3D(hfss, 2.5e9)
        >>> gnd = my_stackup.add_ground_layer("gnd")
        >>> my_stackup.add_dielectric_layer("diel1", thickness=1.5, material="Duroid (tm)")
        >>> top = my_stackup.add_signal_layer("top")
        >>> my_patch = top.add_patch(frequency=None, patch_width=51, patch_name="MLPatch")
        >>> my_stackup.resize_around_element(my_patch)
        >>> my_patch.create_probe_port(gnd)
        """
        probe_or = 2.45 * r  # Probe outer radius (relative to inner radius).
        feed_length = 6 * probe_or

        # Add parameters for relative probe feed location.
        self.application["probe_x_rel"] = str(rel_x_offset)
        self.application["probe_y_rel"] = str(rel_y_offset)
        x_probe = self.position_x.name + "+(1.0 + probe_x_rel)*" + self.length.name + " / 2"
        y_probe = self.position_y.name + "+  probe_y_rel *" + self.width.name + " / 2"

        probe_height = (
            self._signal_layer.elevation.name
            + " - "
            + reference_layer.elevation.name
            + " - "
            + reference_layer.thickness.name
        )
        z_ref = reference_layer.elevation.name + " + " + reference_layer.thickness.name
        probe_pos = [x_probe, y_probe, z_ref]  # Probe base position.
        probe_wire = self.application.modeler.create_cylinder(
            orientation="Z", origin=probe_pos, radius=r, height=probe_height, name=name, material="copper"
        )
        probe_feed_wire = self.application.modeler.create_cylinder(
            orientation="Z",
            origin=probe_pos,
            radius=r,
            height=-feed_length,
            name=name + "_feed_wire",
            material="copper",
        )
        probe_feed_outer = self.application.modeler.create_cylinder(
            orientation="Z",
            origin=probe_pos,
            radius=probe_or,
            height=-feed_length,
            name=name + "_feed_outer",
            material="vacuum",
        )

        # Probe extends through the ground plane.
        self.application.modeler.subtract(reference_layer.name, probe_feed_outer.name)

        # Find face on probe with max area. This is the outer ground and will be assigned PEC.
        areas = [f.area for f in probe_feed_outer.faces]
        i_pec = areas.index(max(areas))
        outer_sheet_id = probe_feed_outer.faces[i_pec].id
        self.application.assign_perfecte_to_sheets(outer_sheet_id, "Probe_PEC")

        # Assign port. Find the face with the minimum z-position.
        self.application.wave_port(
            probe_feed_outer.bottom_face_z, reference=probe_feed_outer.name, create_pec_cap=True, name="Probe_Port"
        )

    def create_lumped_port(self, reference_layer, opposite_side=False, port_name=None, axisdir=None):
        """Create a parametrized lumped port.

        Parameters
        ----------
        reference_layer : class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.Layer3D`
            Reference layer, which is the ground layer in most cases.
        opposite_side : bool, optional
            Change the side where the port is created.
        port_name : str, optional
            Name of the lumped port.
        axisdir : int or :class:`ansys.aedt.core.application.analysis.Analysis.AxisDir`, optional
            Position of the port. It should be one of the values for ``Application.AxisDir``,
            which are: ``XNeg``, ``YNeg``, ``ZNeg``, ``XPos``, ``YPos``, and ``ZPos``.
            The default is ``Application.AxisDir.XNeg``.

        Returns
        -------
        bool

        Examples
        --------

        >>> from ansys.aedt.core import Hfss
        >>> from ansys.aedt.core.modeler.advanced_cad.stackup_3d import Stackup3D
        >>> hfss = Hfss()
        >>> my_stackup = Stackup3D(hfss, 2.5e9)
        >>> gnd = my_stackup.add_ground_layer("gnd")
        >>> my_stackup.add_dielectric_layer("diel1", thickness=1.5, material="Duroid (tm)")
        >>> top = my_stackup.add_signal_layer("top")
        >>> my_patch = top.add_patch(frequency=None, patch_width=51, patch_name="MLPatch")
        >>> my_stackup.resize_around_element(my_patch)
        >>> my_patch.create_lumped_port(gnd)
        """
        string_position_x = self.position_x.name
        if opposite_side:
            string_position_x = self.position_x.name + " + " + self.length.name
        string_position_y = self.position_y.name + " - " + self.width.name + "/2"
        string_position_z = reference_layer.elevation.name
        string_width = self.width.name
        string_length = (
            self._signal_layer.elevation.name
            + " + "
            + self._signal_layer.thickness.name
            + " - "
            + reference_layer.elevation.name
        )
        rect = self.application.modeler.create_rectangle(
            orientation=constants.PLANE.YZ,
            origin=[string_position_x, string_position_y, string_position_z],
            sizes=[string_width, string_length],
            name=self.name + "_port",
            material=None,
        )
        if self.application.solution_type == "Modal":
            if axisdir is None:
                axisdir = self.application.AxisDir.ZPos
            port = self.application.lumped_port(rect.name, integration_line=axisdir, name=port_name)
        elif self.application.solution_type == "Terminal":
            port = self.application.lumped_port(rect.name, reference=[reference_layer.name], name=port_name)
        return port

    def quarter_wave_feeding_line(self, impedance_to_adapt=50):
        """Create a Trace to feed the patch.

        The trace length is the quarter wavelength, and this width is calculated
        to return the desired impedance.

        Parameters
        ----------
        impedance_to_adapt : float, optional
            Impedance the feeding line must return. By default 50 Ohms.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.Trace`

        Examples
        --------

        >>> from ansys.aedt.core import Hfss
        >>> from ansys.aedt.core.modeler.advanced_cad.stackup_3d import Stackup3D
        >>> hfss = Hfss()
        >>> my_stackup = Stackup3D(hfss, 2.5e9)
        >>> gnd = my_stackup.add_ground_layer("gnd")
        >>> my_stackup.add_dielectric_layer("diel1", thickness=1.5, material="Duroid (tm)")
        >>> top = my_stackup.add_signal_layer("top")
        >>> my_patch = top.add_patch(frequency=None, patch_width=51, patch_name="MLPatch")
        >>> my_stackup.resize_around_element(my_patch)
        >>> my_feeding_line = my_patch.quarter_wave_feeding_line()
        >>> my_stackup.dielectric_x_position.expression = my_stackup.dielectric_x_position.expression +
        >>> " - " + my_feeding_line.length.name
        >>> my_stackup.dielectric_length.expression = my_stackup.dielectric_length.expression +
        >>> " + " + my_feeding_line.length.name

        """
        string_formula = "sqrt(" + str(impedance_to_adapt) + "*" + self._impedance_bal.name + ")"
        feeding_line = Trace(
            self.application,
            self.frequency.value,
            string_formula,
            None,
            self.signal_layer,
            self.dielectric_layer,
            line_length=None,
            line_electrical_length=90,
            line_position_x=0,
            line_position_y=0,
            line_name=self.name + "_feeding_line",
            reference_system=self.reference_system,
            axis="X",
        )
        feeding_line.position_x.expression = "-" + feeding_line.length.name
        return feeding_line

    def set_optimal_width(self):
        """Set the expression of the NamedVariable corresponding to the patch width, to an optimal expression.

        Examples
        --------

        >>> from ansys.aedt.core import Hfss
        >>> from ansys.aedt.core.modeler.advanced_cad.stackup_3d import Stackup3D
        >>> hfss = Hfss()
        >>> my_stackup = Stackup3D(hfss, 2.5e9)
        >>> gnd = my_stackup.add_ground_layer("gnd")
        >>> my_stackup.add_dielectric_layer("diel1", thickness=1.5, material="Duroid (tm)")
        >>> top = my_stackup.add_signal_layer("top")
        >>> my_patch = top.add_patch(frequency=None, patch_width=51, patch_name="MLPatch")
        >>> my_stackup.resize_around_element(my_patch)
        >>> my_patch.set_optimal_width()

        """
        f = self.frequency.name
        er = self.permittivity.name
        self.width.expression = "(c0 * 1000/(2 * " + f + " * sqrt((" + er + " + 1)/2)))mm"


class Trace(CommonObject, object):
    """Trace Class in Stackup3D. Create a parametrized trace.

    It is preferable to use the add_trace method in the class Layer3D
    than directly the class constructor.

    Parameters
    ----------
    application : :class:`ansys.aedt.core.hfss.Hfss`
        HFSS design or project where the variable is to be created.
    frequency : float, None
        The line frequency, it is used in prediction formulas. If it is None, the line frequency will be that of the
        layer or of the stackup.
    line_width : float, None
        The line width. If it is None, it will calculate it from characteristic impedance of the line.
    line_impedance : float
        The characteristic impedance of the line. If a line width is entered by the user, the characteristic impedance
        will be calculated from it.
    signal_layer : :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.Layer3D`
        The signal layer where the line will be drawn.
    dielectric_layer : :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.Layer3D`
        The dielectric layer between the line and the ground layer. Its permittivity and thickness are used in
        prediction formulas.
    line_electrical_length : float, None, optional
        The ratio between the line length and the wavelength in degree. By default 90 which is corresponding
        to the quarter of the wavelength. If it is None, it will be directly calculated from the line length entered
        by the user.
    line_length : float, None, optional
        The line length. By default, it is None and so the length is calculated by prediction formulas according to the
        electrical length.
    line_position_x : float, optional
        Line x position, by default it is 0.
    line_position_y : float, optional
        Line y position, by default it is 0.
    line_name : str, optional
        Line name, by  default "line".
    reference_system : str, None, optional
        Coordinate system of the line. By default, None.
    axis : str, optional
        Line length axis, by default "X".

    Examples
    --------
    >>> from ansys.aedt.core import Hfss
    >>> from ansys.aedt.core.modeler.advanced_cad.stackup_3d import Stackup3D
    >>> hfss = Hfss(new_desktop=True)
    >>> my_stackup = Stackup3D(hfss, 2.5e9)
    >>> gnd = my_stackup.add_ground_layer("gnd")
    >>> my_stackup.add_dielectric_layer("diel1", thickness=1.5, material="Duroid (tm)")
    >>> top = my_stackup.add_signal_layer("top")
    >>> my_trace = top.add_trace(line_width=2.5, line_length=22)
    >>> my_stackup.resize_around_element(my_trace)
    """

    def __init__(
        self,
        application,
        frequency,
        line_width,
        line_impedance,
        signal_layer,
        dielectric_layer,
        line_electrical_length=90,
        line_length=None,
        line_position_x=0,
        line_position_y=0,
        line_name="line",
        reference_system=None,
        axis="X",
    ):
        CommonObject.__init__(self, application)
        if frequency:
            self._frequency = NamedVariable(application, line_name + "_frequency", str(frequency) + "Hz")
        elif signal_layer.frequency:
            self._frequency = signal_layer.frequency
        else:
            self._frequency = signal_layer.stackup.frequency
        self._signal_layer = signal_layer
        self._dielectric_layer = dielectric_layer
        self._substrate_thickness = dielectric_layer.thickness
        self._position_x = NamedVariable(
            application, line_name + "_position_x", application.value_with_units(line_position_x)
        )
        self._position_y = NamedVariable(
            application, line_name + "_position_y", application.value_with_units(line_position_y)
        )
        self._position_z = signal_layer.elevation
        self._dielectric_material = dielectric_layer.material
        self._material_name = signal_layer.material_name
        self._layer_name = signal_layer.name
        self._layer_number = signal_layer.number
        self._name = line_name
        self._line_thickness = signal_layer.thickness
        self._width = None
        self._width_h_w = None
        self._width_w_h = None
        self._effective_permittivity_h_w = None
        self._effective_permittivity_w_h = None
        self._axis = axis
        #  self._permittivity = NamedVariable(
        #      application, line_name + "_permittivity", self._dielectric_layer.duplicated_material.permittivity.name
        #  )
        if isinstance(line_width, float) or isinstance(line_width, int):
            self._width = NamedVariable(application, line_name + "_width", application.value_with_units(line_width))
            self._effective_permittivity_w_h, self._effective_permittivity_h_w = self._effective_permittivity_calcul
            self._wave_length = self._wave_length_calcul
            self._added_length = self._added_length_calcul
            if isinstance(line_electrical_length, float) or isinstance(line_electrical_length, int):
                self._electrical_length = NamedVariable(
                    application, line_name + "_elec_length", str(line_electrical_length)
                )
                self._length = self._length_calcul
            elif isinstance(line_length, float) or isinstance(line_length, int):
                self._length = NamedVariable(
                    application, line_name + "_length", application.value_with_units(line_length)
                )
                self._electrical_length = self._electrical_length_calcul
            else:
                application.logger.error("line_length must be a float.")
            self._charac_impedance_w_h, self._charac_impedance_h_w = self._charac_impedance_calcul
        elif line_width is None:
            self._charac_impedance = NamedVariable(
                self.application, line_name + "_charac_impedance_h_w", str(line_impedance)
            )
            self._width_w_h, self._width_h_w = self._width_calcul
            self._effective_permittivity_w_h, self._effective_permittivity_h_w = self._effective_permittivity_calcul
            self._wave_length = self._wave_length_calcul
            self._added_length = self._added_length_calcul
            if isinstance(line_electrical_length, float) or isinstance(line_electrical_length, int):
                self._electrical_length = NamedVariable(
                    application, line_name + "_elec_length", str(line_electrical_length)
                )
                self._length = self._length_calcul
            elif isinstance(line_length, float) or isinstance(line_length, int):
                self._length = NamedVariable(
                    application, line_name + "_length", application.value_with_units(line_length)
                )
                self._electrical_length = self._electrical_length_calcul
            else:
                application.logger.error("line_length must be a float.")
        if reference_system:
            application.modeler.set_working_coordinate_system(reference_system)
            if axis == "X":
                start_point = [
                    f"{self._name}_position_x",
                    self.position_y.name + " - " + self.width.name + "/2",
                    0,
                ]
            else:
                start_point = [
                    self.position_x.name + " - " + self.width.name + "/2",
                    f"{self._name}_position_y",
                    0,
                ]
            self._reference_system = reference_system
        else:
            application.modeler.create_coordinate_system(
                origin=[
                    f"{self._name}_position_x",
                    f"{self._name}_position_y",
                    signal_layer.elevation.name,
                ],
                reference_cs="Global",
                name=line_name + "_CS",
            )
            application.modeler.set_working_coordinate_system(line_name + "_CS")
            if axis == "X":
                start_point = [0, "-" + self.width.name + "/2", 0]
            else:
                start_point = ["-" + self.width.name + "/2", 0, 0]
            self._reference_system = line_name + "_CS"
        if signal_layer.thickness:
            self._aedt_object = application.modeler.create_box(
                origin=start_point,
                sizes=[
                    f"{self._name}_length",
                    self.width.name,
                    signal_layer.thickness.name,
                ],
                name=line_name,
                material=signal_layer.material_name,
            )
        else:
            self._aedt_object = application.modeler.create_rectangle(
                oring=start_point,
                sizes=[f"{self._name}_length", self.width.name],
                name=line_name,
                material=signal_layer.material_name,
            )
        application.modeler.set_working_coordinate_system("Global")
        application.modeler.subtract(blank_list=[signal_layer.name], tool_list=[line_name], keep_originals=True)

    @property
    def frequency(self):
        """Frequency.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable Object.
        """
        return self._frequency

    @property
    def substrate_thickness(self):
        """Substrate Thickness.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable Object.
        """
        return self._substrate_thickness

    @property
    def width(self):
        """Width.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable Object.
        """
        if self._width is not None:
            return self._width
        elif (
            self.width_h_w.numeric_value < self.dielectric_layer.thickness.numeric_value * 2
            and self.width_h_w.numeric_value < self.dielectric_layer.thickness.numeric_value * 2
        ):
            return self._width_h_w
        return self._width_w_h

    @property
    def width_h_w(self):
        """Width when the substrat thickness is two times upper than the width.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable Object.
        """
        if self._width_h_w is not None:
            return self._width_h_w

    @property
    def width_w_h(self):
        """Width when the width is two times upper than substrat thickness.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable Object.
        """
        if self._width_w_h is not None:
            return self._width_w_h

    @property
    def _width_calcul(self):
        """Create NamedVariable containing the calculations of the line width and return it.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable Object.
        """
        # if w/h < 2 :
        # a = z * sqrt((er + 1) / 2) / 60 + (0.23 + 0.11 / er) * (er - 1) / (er + 1)
        # w/h = 8 * exp(a) / (exp(2 * a) - 2)
        # else w/h > 2 :
        # b = 377 * pi / (2 * z * sqrt(er))
        # w/h = 2 * (b - 1 - log(2 * b - 1) * (er - 1) * (log(b - 1) + 0.39 - 0.61 / er) / (2 * er)) / pi
        h = self._substrate_thickness.name
        z = self._charac_impedance.name
        er = self._permittivity.value
        a_formula = (
            "("
            + z
            + " * sqrt(("
            + er
            + " + 1)/2)/60 + (0.23 + 0.11/"
            + er
            + ")"
            + " * ("
            + er
            + "- 1)/("
            + er
            + "+ 1))"
        )
        w_div_by_h_inf_2 = "(8 * exp(" + a_formula + ")/(exp(2 * " + a_formula + ") - 2))"

        b_formula = "(377 * pi/(2 * " + z + " * " + "sqrt(" + er + ")))"
        w_div_by_h_sup_2 = (
            "(2 * ("
            + b_formula
            + " - 1 - log(2 * "
            + b_formula
            + " - 1) * ("
            + er
            + " - 1) * (log("
            + b_formula
            + " - 1) + 0.39 - 0.61/"
            + er
            + ")/(2 * "
            + er
            + "))/pi)"
        )

        w_formula_inf = w_div_by_h_inf_2 + " * " + h
        w_formula_sup = w_div_by_h_sup_2 + " * " + h

        self._width_h_w = NamedVariable(self.application, self._name + "_width_h_w", w_formula_inf)
        self._width_w_h = NamedVariable(self.application, self._name + "_width", w_formula_sup)

        return self._width_w_h, self._width_h_w

    @property
    def position_x(self):
        """Starting Position X.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable Object.
        """
        return self._position_x

    @property
    def position_y(self):
        """Starting Position Y.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable Object.
        """
        return self._position_y

    @property
    def permittivity(self):
        """Permittivity.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable Object.
        """
        return self._permittivity

    @property
    def _permittivity(self):
        """Permittivity"""
        return self.application.materials[self._dielectric_material].permittivity

    @property
    def _permittivity_calcul(self):
        """Permittivity.

        (Obsolete)

        """
        # TODO: This property is superfluous and causes inconsistencies. Remove it later.

        self._permittivity = self.application.materials[self._dielectric_material].permittivity
        return self._permittivity

    @property
    def added_length(self):
        """Added Length.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable Object.
        """
        return self._added_length

    @property
    def _added_length_calcul(self):
        """Create a NamedVariable containing the calculation of the line added length and return it.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable Object.
        """
        # "0.412 * substrate_thickness * (patch_eff_permittivity + 0.3) * (patch_width/substrate_thickness + 0.264)"
        # " / ((patch_eff_permittivity - 0.258) * (patch_width/substrate_thickness + 0.813)) "

        er_e = self.effective_permittivity.name
        h = self._substrate_thickness.name
        w = self.width.name
        patch_added_length_formula = (
            "0.412 * " + h + " * (" + er_e + " + 0.3) * (" + w + "/" + h + " + 0.264)/"
            "((" + er_e + " - 0.258) * (" + w + "/" + h + " + 0.813))"
        )
        self._added_length = NamedVariable(self.application, self._name + "_added_length", patch_added_length_formula)
        return self._added_length

    @property
    def length(self):
        """Length.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable Object.
        """
        return self._length

    @property
    def _length_calcul(self):
        """Create a NamedVariable containing the calculation of the line length and return it.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable Object.
        """
        d_l = self._added_length.name
        lbd = self._wave_length.name
        e_l = self._electrical_length.name
        line_length_formula = lbd + "* (" + e_l + "/360)" + " - 2 * " + d_l
        self._length = NamedVariable(self.application, self._name + "_length", line_length_formula)
        return self._length

    @property
    def charac_impedance(self):
        """Characteristic Impedance.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable Object.
        """
        return self._charac_impedance

    @property
    def _charac_impedance_calcul(self):
        """Create NamedVariable containing the calculations of the line characteristic impedance and return it.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable Object.
        """
        # if w / h > 1: 60 * log(8 * h / w + w / (4 * h)) / sqrt(er_e)
        # if w / h < 1: 120 * pi / (sqrt(er_e) * (w / h + 1.393 + 0.667 * log(w / h + 1.444)))
        w = self.width.name
        h = self._dielectric_layer.thickness.name
        er_e = self.effective_permittivity.name
        charac_impedance_formula_w_h = (
            "60 * log(8 * " + h + "/" + w + " + " + w + "/(4 * " + h + "))/sqrt(" + er_e + ")"
        )
        charac_impedance_formula_h_w = (
            "120 * pi / (sqrt(" + er_e + ") * (" + w + "/" + h + "+ 1.393 + 0.667 * log(" + w + "/" + h + " + 1.444)))"
        )
        self._charac_impedance_w_h = NamedVariable(
            self.application, self._name + "_charac_impedance_w_h", charac_impedance_formula_w_h
        )
        self._charac_impedance_h_w = NamedVariable(
            self.application, self._name + "_charac_impedance_h_w", charac_impedance_formula_h_w
        )
        return self._charac_impedance_w_h, self._charac_impedance_h_w

    @property
    def effective_permittivity(self):
        """Effective Permittivity.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable Object.
        """
        if self.width.numeric_value >= self.dielectric_layer.thickness.numeric_value:
            return self._effective_permittivity_w_h
        else:
            return self._effective_permittivity_h_w

    @property
    def effective_permittivity_w_h(self):
        """Effective Permittivity when width is upper than dielectric thickness.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable Object.
        """
        return self._effective_permittivity_w_h

    @property
    def effective_permittivity_h_w(self):
        """Effective Permittivity when dielectric thickness is upper than width.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable Object.
        """
        return self._effective_permittivity_h_w

    @property
    def _effective_permittivity_calcul(self):
        """Create NamedVariable containing the calculations of the line effective permittivity and return it.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable Object.
        """
        # "(substrat_permittivity + 1)/2 +
        # (substrat_permittivity - 1)/(2 * sqrt(1 + 12 * substrate_thickness/patch_width))"
        #
        er = self._permittivity.value
        h = self._substrate_thickness.name
        w = self.width.name
        patch_eff_permittivity_formula_w_h = (
            "(" + er + " + 1)/2 + (" + er + " - 1)/(2 * sqrt(1 + 12 * " + h + "/" + w + "))"
        )
        patch_eff_permittivity_formula_h_w = (
            "("
            + er
            + " + 1)/2 + ("
            + er
            + " - 1)/2 * ((1 + 12 * "
            + h
            + "/"
            + w
            + ")**(-0.5) + 0.04 * (1 - 12 * "
            + w
            + "/"
            + h
            + ")**2)"
        )
        self._effective_permittivity_w_h = NamedVariable(
            self.application, self._name + "_eff_permittivity_w_h", patch_eff_permittivity_formula_w_h
        )
        self._effective_permittivity_h_w = NamedVariable(
            self.application, self._name + "_eff_permittivity", patch_eff_permittivity_formula_h_w
        )
        return self._effective_permittivity_w_h, self._effective_permittivity_h_w

    @property
    def wave_length(self):
        """Wave Length.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable Object.
        """
        return self._wave_length

    @property
    def _wave_length_calcul(self):
        """Create a NamedVariable containing the calculation of the line wavelength and return it.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable Object.
        """
        # "c0 * 1000/(patch_frequency * sqrt(patch_eff_permittivity))"
        # TODO it is currently only available for mm
        f = self._frequency.name
        er_e = self.effective_permittivity.name
        patch_wave_length_formula = "(c0 * 1000/(" + f + "* sqrt(" + er_e + ")))mm"
        self._wave_length = NamedVariable(
            self.application,
            self._name + "_wave_length",
            self.application.value_with_units(patch_wave_length_formula),
        )
        return self._wave_length

    @property
    def electrical_length(self):
        """Electrical Length.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable Object.
        """
        return self._electrical_length

    @property
    def _electrical_length_calcul(self):
        """Create a NamedVariable containing the calculation of the line electrical length and return it.

        Returns
        -------
        :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.NamedVariable`
            Variable Object.
        """
        lbd = self._wave_length.name
        length = self._length.name
        d_l = self._added_length.name
        elec_length_formula = "360 * (" + length + " + 2 * " + d_l + ")/" + lbd
        self._electrical_length = NamedVariable(self.application, self._name + "_elec_length", elec_length_formula)
        return self._electrical_length

    def create_lumped_port(self, reference_layer, opposite_side=False, port_name=None, axisdir=None):
        """Create a parametrized lumped port.

        Parameters
        ----------
        reference_layer : class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.Layer3D`
            Reference layer, which is the ground layer in most cases.
        opposite_side : bool, optional
            Change the side where the port is created.
        port_name : str, optional
            Name of the lumped port.
        axisdir : int or :class:`ansys.aedt.core.application.analysis.Analysis.AxisDir`, optional
            Position of the port. It should be one of the values for ``Application.AxisDir``,
            which are: ``XNeg``, ``YNeg``, ``ZNeg``, ``XPos``, ``YPos``, and ``ZPos``.
            The default is ``Application.AxisDir.XNeg``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
            ``True`` when successful, ``False`` when failed.

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> from ansys.aedt.core.modeler.advanced_cad.stackup_3d import Stackup3D
        >>> hfss = Hfss(new_desktop=True)
        >>> my_stackup = Stackup3D(hfss, 2.5e9)
        >>> gnd = my_stackup.add_ground_layer("gnd")
        >>> my_stackup.add_dielectric_layer("diel1", thickness=1.5, material="Duroid (tm)")
        >>> top = my_stackup.add_signal_layer("top")
        >>> my_trace = top.add_trace(line_width=2.5, line_length=90, is_electrical_length=True)
        >>> my_stackup.resize_around_element(my_trace)
        >>> my_trace.create_lumped_port(gnd)
        >>> my_trace.create_lumped_port(gnd, opposite_side=True)

        """
        string_position_x = self.position_x.name
        if opposite_side:
            string_position_x = self.position_x.name + " + " + self.length.name
        string_position_y = self.position_y.name + " - " + self.width.name + "/2"
        string_position_z = reference_layer.elevation.name
        string_width = self.width.name
        string_length = (
            self._signal_layer.elevation.name
            + " + "
            + self._signal_layer.thickness.name
            + " - "
            + reference_layer.elevation.name
        )
        port = self.application.modeler.create_rectangle(
            orientation=constants.PLANE.YZ,
            origin=[string_position_x, string_position_y, string_position_z],
            sizes=[string_width, string_length],
            name=self.name + "_port",
            material=None,
        )
        if self.application.solution_type == "Modal":
            if axisdir is None:
                axisdir = self.application.AxisDir.ZPos
            port = self.application.lumped_port(
                signal=port.name, name=port_name, integration_line=axisdir, create_port_sheet=False
            )
        elif self.application.solution_type == "Terminal":
            port = self.application.lumped_port(
                signal=port.name,
                name=port_name,
                integration_line=axisdir,
                create_port_sheet=False,
                reference=[reference_layer.name],
            )
        return port


class Polygon(CommonObject, object):
    """Polygon Class in Stackup3D. It is preferable to use the add_polygon method in the class Layer3D than directly
    the class constructor.

    Parameters
    ----------
    application : :class:`ansys.aedt.core.hfss.Hfss`
        HFSS design or project where the variable is to be created.
    point_list : list
        Points list of [x,y] coordinates.
    signal_layer : :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.Layer3D`
        The signal layer where the line will be drawn.
    poly_name : str, optional
            Polygon name. The default is ``poly``.
    mat_name : str, optional
        The polygon material name.
    is_void : bool, optional
            Whether the polygon is a void. The default is ``False``.
            On ground layers, it will act opposite of the Boolean value because the ground
            is negative.
    reference_system : str, None, optional
        Coordinate system of the polygon. By default, None.

    Examples
    --------

    >>> from ansys.aedt.core import Hfss
    >>> from ansys.aedt.core.modeler.advanced_cad.stackup_3d import Stackup3D
    >>> hfss = Hfss(new_desktop=True)
    >>> my_stackup = Stackup3D(hfss, 2.5e9)
    >>> gnd = my_stackup.add_ground_layer("gnd", thickness=None)
    >>> my_stackup.add_dielectric_layer("diel1", thickness=1.5, material="Duroid (tm)")
    >>> top = my_stackup.add_signal_layer("top", thickness=None)
    >>> my_polygon = top.add_polygon([[0, 0], [0, 1], [1, 1], [1, 0]])
    >>> my_stackup.dielectric_x_position = "2mm"
    >>> my_stackup.dielectric_y_position = "2mm"
    >>> my_stackup.dielectric_length = "-3mm"
    >>> my_stackup.dielectric_width = "-3mm"

    """

    def __init__(
        self,
        application,
        point_list,
        signal_layer,
        poly_name="poly",
        mat_name="copper",
        is_void=False,
        reference_system=None,
    ):
        CommonObject.__init__(self, application)

        self._is_void = is_void
        self._layer_name = signal_layer
        self._thickness = signal_layer.thickness
        self._app = application
        pts = []
        for el in point_list:
            pts.append(
                [
                    application.value_with_units(el[0]),
                    application.value_with_units(el[1]),
                    signal_layer.elevation.name,
                ]
            )
        if reference_system:
            application.modeler.set_working_coordinate_system(reference_system)
            self._reference_system = reference_system
        else:
            application.modeler.create_coordinate_system(
                origin=[0, 0, 0], reference_cs="Global", name=poly_name + "_CS"
            )
            application.modeler.set_working_coordinate_system(poly_name + "_CS")

            self._reference_system = poly_name + "_CS"
        self._aedt_object = application.modeler.create_polyline(
            points=pts, cover_surface=True, name=poly_name, material=mat_name
        )
        if self._thickness:
            application.modeler.sweep_along_vector(
                self._aedt_object, [0, 0, self._thickness.name], draft_type="Natural"
            )
        application.modeler.set_working_coordinate_system("Global")

    @property
    def points_on_layer(self):
        """Object Bounding Box.

        Returns
        -------
        List
            List of [x,y] coordinate of bounding box.
        """
        bb = self._aedt_object.bounding_box
        return [[bb[0], bb[1]], [bb[0], bb[4]], [bb[3], bb[4]], [bb[3], bb[1]]]


class MachineLearningPatch(Patch, object):
    """MachineLearningPatch Class in Stackup3D. Create an antenna whose length is predicted by a
    machine learning algorithm.

    The machine learning algorithm determines the length according to resonant frequency,
    patch width, substrat thickness and relative permittivity. The other parameter have no or only a minor influence.
    We can consider that the patch thickness has no influence as long as it is lower than 50 um,
    for machine learning training is set to 35 um. The patch conductivity and other dielectric properties are
    respectively those of copper and duroid (tm) for the machine learning training, but predictions work
    regardless of the dielectric or the conductor. The predictions are, in the most of cases, better than the
    predictions with formula used in the class Patch. The machine learning model used, is Support Vector Regression,
    it is a classic model in the non-linear prediction, it can be used for other non-linear application.
    Two models were created, one from 0.1 GHz to 1 GHz and another from 1 GHz to 10 GHz. The example of the creation of
    these models is available in a PyAEDT example named Machine_learning_applied_to_Patch. The two databases and models
    are available in PyAEDT in misc.

    It is preferable to use the ml_patch method in the class Layer3D than directly the class constructor.

    Parameters
    ----------
    application : :class:`ansys.aedt.core.hfss.Hfss`
        HFSS design or project where the variable is to be created.
    frequency : float, None
        The patch frequency, it is used in prediction formulas. If it is None, the patch frequency will be that of the
        layer or of the stackup. From 0.1 to 10 GHz.
    dx : float
        The patch width. From O.5 to 1.5 of the optimal width value : c0 * 1000/(2 * f * sqrt((er  + 1)/2))
    signal_layer : :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.Layer3D`
        The signal layer where the patch will be drawn.
    dielectric_layer : :class:`ansys.aedt.core.modeler.advanced_cad.stackup_3d.Layer3D`
        The dielectric layer between the patch and the ground layer. Its permittivity and thickness are used in
        prediction formulas. Thickness must be from 0.003 to 0.05 of the wavelength in vacuum and relative permittivity
        from 1 to 12.
    patch_position_x : float, optional
        Patch x position, by default it is 0.
    patch_position_y : float, optional
        Patch y position, by default it is 0.
    patch_name : str, optional
        Patch name, by  default "patch".
    reference_system : str, None, optional
        Coordinate system of the patch. By default, None.
    axis : str, optional
        Patch length axis, by default ``"X"``.

    Examples
    --------

    >>> from ansys.aedt.core import Hfss
    >>> from ansys.aedt.core.modeler.advanced_cad.stackup_3d import Stackup3D
    >>> hfss = Hfss()
    >>> my_stackup = Stackup3D(hfss, 2.5e9)
    >>> gnd = my_stackup.add_ground_layer("gnd")
    >>> my_stackup.add_dielectric_layer("diel1", thickness=1.5, material="Duroid (tm)")
    >>> top = my_stackup.add_signal_layer("top")
    >>> my_patch = top.ml_patch(frequency=None, patch_width=51, patch_name="MLPatch")
    >>> my_stackup.resize_around_element(my_patch)

    """

    def __init__(
        self,
        application,
        frequency,
        dx,
        signal_layer,
        dielectric_layer,
        patch_position_x=0,
        patch_position_y=0,
        patch_name="patch",
        reference_system=None,
        axis="X",
    ):
        Patch.__init__(
            self,
            application,
            frequency,
            dx,
            signal_layer,
            dielectric_layer,
            dy=None,
            patch_position_x=patch_position_x,
            patch_position_y=patch_position_y,
            patch_name=patch_name,
            reference_system=reference_system,
            axis=axis,
        )
        self.predict_length()

    def predict_length(self):
        try:
            import joblib
            import numpy as np
        except ImportError:  # pragma: no cover
            raise ImportError("Package Joblib and Numpy are required to run ML.")
        training_file = None
        if 1e9 >= self.frequency.numeric_value >= 1e8:
            training_file = os.path.join(pyaedt_path, "misc", "patch_svr_model_100MHz_1GHz.joblib")
        elif 1e10 >= self.frequency.numeric_value > 1e9:
            training_file = os.path.join(pyaedt_path, "misc", "patch_svr_model_1GHz_10GHz.joblib")
        else:  # pragma: no cover
            self.application.logger.error("This ML algorithm can only predict patch antennas from 100 MHz to 10 GHz.")
        if training_file:
            model = joblib.load(training_file)
            list_for_array = [
                [
                    self.frequency.numeric_value,
                    self.width.numeric_value,
                    self._permittivity.numeric_value,
                    self.dielectric_layer.thickness.numeric_value,
                ]
            ]
            array_for_prediction = np.array(list_for_array, dtype=np.float32)
            length = model.predict(array_for_prediction)[0]
            self.length.expression = self.application.value_with_units(length)
