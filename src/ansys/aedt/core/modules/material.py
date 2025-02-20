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

"""
This module contains these data classes for creating a material library:

* `BasicValue`
* `ClosedFormTM`
* `CommonMaterial`
* `Dataset`
* `MatProperties`
* `MatProperty`
* `Material`
* `SurMatProperties`
* `SufaceMaterial`

"""


import copy
import warnings

from ansys.aedt.core.generic.constants import CSS4_COLORS
from ansys.aedt.core.generic.constants import unit_converter
from ansys.aedt.core.generic.data_handlers import _dict2arg
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.generic.numbers import decompose_variable_value
from ansys.aedt.core.generic.numbers import is_number


class MatProperties(object):
    """Contains a list of constant names for all materials with mappings to their internal XML names.

    Internal names are used in scripts, and XML names are used in the XML syntax.
    """

    aedtname = [
        "permittivity",
        "permeability",
        "conductivity",
        "dielectric_loss_tangent",
        "magnetic_loss_tangent",
        "magnetic_coercivity",
        "thermal_conductivity",
        "mass_density",
        "specific_heat",
        "thermal_expansion_coefficient",
        "youngs_modulus",
        "poissons_ratio",
        "diffusivity",
        "molecular_mass",
        "viscosity",
    ]

    defaultvalue = [
        1.0,
        1.0,
        0,
        0,
        0,
        dict(
            {
                "Magnitude": 0,
                "DirComp1": 1,
                "DirComp2": 0,
                "DirComp3": 0,
            }
        ),
        0.01,
        0,
        0,
        0,
        0,
        0,
        0.8,
        0,
        0,
        0,
        0,
        0,
        0,
    ]

    defaultunit = [
        None,
        None,
        "[siemens m^-1]",
        None,
        None,
        None,
        "[W m^-1 C^-1]",
        "[Kg m^-3]",
        "[J Kg^-1 C^-1]",
        "[C^-1]",
        "[Pa]",
        None,
        None,
        None,
        None,
        None,
        None,
        None,
        None,
    ]

    diel_order = [3, 0, 1, 4, 5, 6, 7, 8, 9, 10, 11, 1]

    cond_order = [2, 0, 1, 4, 5, 6, 7, 8, 9, 10, 11, 3]

    workbench_name = [
        "Relative Permittivity",
        "Relative Permeability",
        "Electrical Conductivity",
        "Electric Loss Tangent",
        "Magnetic Loss Tangent",
        "Magnetic Coercivity",
        "Thermal Conductivity",
        "Density",
        "Specific Heat",
        "Coefficient of Thermal Expansion",
        "Young's Modulus",
        "Poisson's Ratio",
        None,  # diffusivity
        "Molecular Weight",
        "Viscosity",
    ]

    @classmethod
    def wb_to_aedt_name(cls, wb_name):
        """Retrieve the corresponding AEDT property name for the specified Workbench property name.

        The Workbench names are specified in ``MatProperties.workbench_name``.
        The AEDT names are specified in ``MatProperties.aedtname``.

        Parameters
        ----------
        wb_name : str
            Workbench name of the property.

        Returns
        -------
        str
            AEDT name of the property.
        """
        return cls.aedtname[cls.workbench_name.index(wb_name)]

    @classmethod
    def get_defaultunit(cls, aedtname=None):
        """Retrieve the default unit for a full name or a category name.

        Parameters
        ----------
        aedtname : str, optional
            AEDT full name or category name. The default is ``None``.

        Returns
        -------
        str
            Default unit if it exists.
        """
        if aedtname:
            return cls.defaultunit[cls.aedtname.index(aedtname)]
        else:
            raise TypeError("get_defaultunit: Either the full name or category name must be defined.")

    @classmethod
    def get_defaultvalue(cls, aedtname):
        """Retrieve the default value for a full name or a category name.

        Parameters
        ----------
        aedtname : str
             AEDT full name or category name. The default is ``None``.

        Returns
        -------
        float
            Default value if it exists.
        """
        if aedtname:
            return cls.defaultvalue[cls.aedtname.index(aedtname)]
        else:
            raise TypeError("get_defaultunit: Either the full name or category name must be defined.")


class SurfMatProperties(object):
    """Contains a list of constant names for all surface materials with mappings to their internal XML names.

    Internal names are used in scripts, and XML names are used in the XML syntax.
    """

    aedtname = [
        "surface_emissivity",
        "surface_roughness",
        "surface_diffuse_absorptance",
        "surface_incident_absorptance",
    ]
    defaultvalue = [1.0, 0, 0.4, 0.4]
    defaultunit = [None, "[m]", None, None]

    @classmethod
    def get_defaultunit(cls, aedtname=None):
        """Retrieve the default unit for a full name or a category name.

        Parameters
        ----------
        aedtname : str, optional
            AEDT full name or category name. The default is ``None``.

        Returns
        -------
        str
            Default unit if it exists.

        """
        if aedtname:
            return cls.defaultunit[cls.aedtname.index(aedtname)]
        else:
            raise TypeError("get_defaultunit: either fullname or catname MUST be defined")

    @classmethod
    def get_defaultvalue(cls, aedtname=None):
        """Get the default value for a full name or a category name.

        Parameters
        ----------
        aedtname : str, optional
            AEDT full name or category name. The default is ``None``.

        Returns
        -------
        float
            Default value if it exists.

        """
        if aedtname:
            return cls.defaultvalue[cls.aedtname.index(aedtname)]
        else:
            raise TypeError("get_defaultunit: Either the full name or category name must be defined.")


class ClosedFormTM(object):
    """Manages closed-form thermal modifiers."""

    Tref = "22cel"
    C1 = 0
    C2 = 0
    TL = "-273.15cel"
    TU = "1000cel"
    autocalculation = True
    TML = 1000
    TMU = 1000


class Dataset(object):
    """Manages datasets."""

    ds = []
    unitx = ""
    unity = ""
    unitz = ""
    type = "Absolute"
    namex = ""
    namey = ""
    namez = None


class BasicValue(object):
    """Manages thermal and spatial modifier calculations."""

    def __init__(self):
        self.value = None
        self.dataset = None
        self.thermalmodifier = None
        self.spatialmodifier = None


class MatProperty(object):
    """Manages simple, anisotropic, tensor, and non-linear properties.

    Parameters
    ----------
    material : :class:`ansys.aedt.core.modules.material.Material`
        Inherited parent object.
    name : str
        Name of the material property.
    val :
        The default is ``None``.
    thermalmodifier
        The default is ``None``.
    spatialmodifier
        The default is ``None``.

    Examples
    --------
    >>> from ansys.aedt.core import Hfss
    >>> app = Hfss()
    >>> matproperty = app.materials["copper"].conductivity
    """

    def __init__(self, material, name, val=None, thermalmodifier=None, spatialmodifier=None):
        self._material = material
        self.logger = self._material.logger
        self._type = "simple"
        self.name = name
        self._property_value = [BasicValue()]
        self._unit = None

        if val is not None and isinstance(val, (str, float, int)):
            self.value = val
        elif val is not None and "property_type" in val.keys() and val["property_type"] == "AnisoProperty":
            self.type = "anisotropic"
            self.value = [val["component1"], val["component2"], val["component3"]]
        elif val is not None and "property_type" in val.keys() and val["property_type"] == "nonlinear":
            self.type = "nonlinear"
            for e, v in val.items():
                if e == "BTypeForSingleCurve":
                    self.btype_for_single_curve = v
                elif e == "HUnit":
                    self.hunit = v
                elif e == "BUnit":
                    self.bunit = v
                elif e == "IsTemperatureDependent":
                    self.is_temperature_dependent = v
                elif e in ["BHCoordinates", "DECoordinates", "JECoordinates"]:
                    self._unit = v["DimUnits"]
                    if "Point" in v:
                        self.value = v["Point"]
                    elif "Points" in v:
                        pair_list = [v["Points"][i : i + 2] for i in range(0, len(v["Points"]), 2)]
                        self.value = pair_list
                elif e == "Temperatures":
                    self.temperatures = v
        elif val is not None and isinstance(val, dict) and "Magnitude" in val.keys():
            self.type = "vector"
            magnitude = val["Magnitude"]
            units = None
            if isinstance(magnitude, str):
                units = "".join(filter(lambda c: c.isalpha() or c == "_", val["Magnitude"]))
                magnitude = "".join(filter(str.isdigit, val["Magnitude"]))
            if units:
                self.unit = units
            self.value = [str(magnitude), str(val["DirComp1"]), str(val["DirComp2"]), str(val["DirComp3"])]
        if not isinstance(thermalmodifier, list):
            thermalmodifier = [thermalmodifier]
        for tm in thermalmodifier:
            if tm:
                if tm["use_free_form"]:
                    self._property_value[tm["Index:"]].thermalmodifier = tm["free_form_value"]
                else:
                    self._property_value[tm["Index:"]].thermalmodifier = ClosedFormTM()
                    self._property_value[tm["Index:"]].thermalmodifier.Tref = tm["Tref"]
                    self._property_value[tm["Index:"]].thermalmodifier.C1 = tm["C1"]
                    self._property_value[tm["Index:"]].thermalmodifier.C2 = tm["C2"]
                    self._property_value[tm["Index:"]].thermalmodifier.TL = tm["TL"]
                    self._property_value[tm["Index:"]].thermalmodifier.TU = tm["TU"]
                    self._property_value[tm["Index:"]].thermalmodifier.autocalculation = tm["auto_calculation"]
        if not isinstance(spatialmodifier, list):
            spatialmodifier = [spatialmodifier]
        for sm in spatialmodifier:
            if sm:
                self._property_value[sm["Index:"]].spatialmodifier = sm["free_form_value"]

    @property
    def type(self):
        """Type of the material property.

        Parameters
        ----------
        type : str
            Type of properties. Options are ``"simple"``,
            ``"anisotropic"``, ``"tensor"``, ``"vector"``, and ``"nonlinear"``
        """
        return self._type

    @type.setter
    def type(self, type):
        self._type = type
        if self._type == "simple":
            self._property_value = [self._property_value[0]]
        elif self._type == "anisotropic":
            try:
                self._property_value = [self._property_value[i] for i in range(3)]
            except IndexError:
                self._property_value = [copy.deepcopy(self._property_value[0]) for _ in range(3)]
        elif self._type == "tensor":
            try:
                self._property_value = [copy.deepcopy(self._property_value[i]) for i in range(9)]
            except IndexError:
                self._property_value = [self._property_value[0] for _ in range(9)]
        elif self._type == "nonlinear":
            self._property_value = [self._property_value[0]]

    @property
    def evaluated_value(self):
        """Evaluated value."""
        evaluated_expression = []
        if isinstance(self.value, list):
            for value in self.value:
                evaluated_expression.append(self._material._materials._app.evaluate_expression(value))
            return evaluated_expression
        return self._material._materials._app.evaluate_expression(self.value)

    @property
    def value(self):
        """Value for a material property."""
        if len(self._property_value) == 1:
            return self._property_value[0].value
        else:
            return [i.value for i in self._property_value]

    @value.setter
    def value(self, val):
        if isinstance(val, list) and isinstance(val[0], list):
            self._property_value[0].value = val
            self._set_non_linear()
        elif isinstance(val, list) and self.type != "vector":
            if len(val) == 3:
                self.type = "anisotropic"
            elif len(val) == 9:
                self.type = "tensor"

            i = 0
            for el in val:
                if i >= len(self._property_value):
                    self._property_value.append(BasicValue())

                self._property_value[i].value = el
                i += 1
            self._material._update_props(self.name, val, update_aedt=self._material._material_update)
        elif isinstance(val, list) and self.type == "vector":
            if len(val) == 4:
                self._property_value[0].value = val
                self._material._update_props(self.name, val, update_aedt=self._material._material_update)
        else:
            self.type = "simple"
            self._property_value[0].value = val
            self._material._update_props(self.name, val, update_aedt=self._material._material_update)

    @property
    def unit(self):
        """Units for a material property value."""
        return self._unit

    @unit.setter
    def unit(self, unit):
        self._unit = unit

    @property
    def data_set(self):
        """Dataset."""
        if len(self._property_value) == 1:
            return self._property_value[0].dataset
        else:
            return [i.dataset for i in self._property_value]

    @property
    def thermalmodifier(self):
        """Thermal modifier."""
        if len(self._property_value) == 1:
            return self._property_value[0].thermalmodifier
        else:
            return [i.thermalmodifier for i in self._property_value]

    @thermalmodifier.setter
    def thermalmodifier(self, thermal_value):
        """Thermal modifier.

        References
        ----------
        >>> oDefinitionManager.EditMaterial
        """
        if thermal_value is None:
            self._property_value[0].thermalmodifier = None
            self._reset_thermal_modifier()
        elif isinstance(thermal_value, str):
            self._property_value[0].thermalmodifier = thermal_value
            self._add_thermal_modifier(thermal_value, 0)
        else:
            for i, value in enumerate(thermal_value):
                self._add_thermal_modifier(value, i)
                try:
                    self._property_value[i].thermalmodifier = value
                except IndexError:
                    self._property_value.append(BasicValue())
                    self._property_value[i].thermalmodifier = value

    def _add_thermal_modifier(self, formula, index):
        """Add a thermal modifier.

        Parameters
        ----------
        formula : str
            Formula to apply.
        index : int
            Value for the index.

        Returns
        -------
        type

        """
        if (
            "ModifierData" not in self._material._props
            or "ThermalModifierData" not in self._material._props["ModifierData"]
            or (
                "all_thermal_modifiers" in self._material._props["ModifierData"]["ThermalModifierData"]
                and bool(self._material._props["ModifierData"]["ThermalModifierData"]["all_thermal_modifiers"]) == False
            )
        ):
            tm = dict(
                {
                    "Property:": self.name,
                    "Index:": index,
                    "prop_modifier": "thermal_modifier",
                    "use_free_form": True,
                    "free_form_value": formula,
                }
            )
            if (
                "ModifierData" in self._material._props
                and "SpatialModifierData" in self._material._props["ModifierData"]
            ):
                self._material._props["ModifierData"] = dict(
                    {
                        "SpatialModifierData": self._material._props["ModifierData"]["SpatialModifierData"],
                        "ThermalModifierData": dict(
                            {
                                "modifier_data": "thermal_modifier_data",
                                "all_thermal_modifiers": dict({"one_spatial_modifier": tm}),
                            }
                        ),
                    }
                )
            else:
                self._material._props["ModifierData"] = dict(
                    {
                        "ThermalModifierData": dict(
                            {
                                "modifier_data": "thermal_modifier_data",
                                "all_thermal_modifiers": dict({"one_thermal_modifier": tm}),
                            }
                        )
                    }
                )

        else:
            for tmname in self._material._props["ModifierData"]["ThermalModifierData"]["all_thermal_modifiers"]:
                if isinstance(
                    self._material._props["ModifierData"]["ThermalModifierData"]["all_thermal_modifiers"][tmname], list
                ):
                    found = False
                    for tm in self._material._props["ModifierData"]["ThermalModifierData"]["all_thermal_modifiers"][
                        tmname
                    ]:
                        if self.name == tm["Property:"] and index == tm["Index:"]:
                            found = True
                            tm["use_free_form"] = True
                            tm["free_form_value"] = formula
                            tm.pop("Tref", None)
                            tm.pop("C1", None)
                            tm.pop("C2", None)
                            tm.pop("TL", None)
                            tm.pop("TU", None)
                    if not found:
                        tm = dict(
                            {
                                "Property:": self.name,
                                "Index:": index,
                                "prop_modifier": "thermal_modifier",
                                "use_free_form": True,
                                "free_form_value": formula,
                            }
                        )
                        self._material._props["ModifierData"]["ThermalModifierData"]["all_thermal_modifiers"][
                            tmname
                        ].append(tm)
                elif (
                    self.name
                    == self._material._props["ModifierData"]["ThermalModifierData"]["all_thermal_modifiers"][tmname][
                        "Property:"
                    ]
                    and index
                    == self._material._props["ModifierData"]["ThermalModifierData"]["all_thermal_modifiers"][tmname][
                        "Index:"
                    ]
                ):
                    self._material._props["ModifierData"]["ThermalModifierData"]["all_thermal_modifiers"][tmname][
                        "use_free_form"
                    ] = True
                    self._material._props["ModifierData"]["ThermalModifierData"]["all_thermal_modifiers"][tmname][
                        "free_form_value"
                    ] = formula
                    self._material._props["ModifierData"]["ThermalModifierData"]["all_thermal_modifiers"][tmname].pop(
                        "Tref", None
                    )
                    self._material._props["ModifierData"]["ThermalModifierData"]["all_thermal_modifiers"][tmname].pop(
                        "C1", None
                    )
                    self._material._props["ModifierData"]["ThermalModifierData"]["all_thermal_modifiers"][tmname].pop(
                        "C2", None
                    )
                    self._material._props["ModifierData"]["ThermalModifierData"]["all_thermal_modifiers"][tmname].pop(
                        "TL", None
                    )
                    self._material._props["ModifierData"]["ThermalModifierData"]["all_thermal_modifiers"][tmname].pop(
                        "TU", None
                    )

                else:
                    self._material._props["ModifierData"]["ThermalModifierData"]["all_thermal_modifiers"][tmname] = [
                        self._material._props["ModifierData"]["ThermalModifierData"]["all_thermal_modifiers"][tmname]
                    ]
                    tm = dict(
                        {
                            "Property:": self.name,
                            "Index:": index,
                            "prop_modifier": "thermal_modifier",
                            "use_free_form": True,
                            "free_form_value": formula,
                        }
                    )
                    self._material._props["ModifierData"]["ThermalModifierData"]["all_thermal_modifiers"][
                        tmname
                    ].append(tm)
        return self._material.update()

    def _reset_thermal_modifier(self):
        """Set the thermal modifier to None.

        Returns
        -------
        type

        """
        if "ModifierData" in self._material._props and "ThermalModifierData" in self._material._props["ModifierData"]:
            if (
                "ModifierData" in self._material._props
                and "SpatialModifierData" in self._material._props["ModifierData"]
            ):
                self._material._props["ModifierData"] = {
                    "SpatialModifierData": self._material._props["ModifierData"]["SpatialModifierData"],
                    "ThermalModifierData": {
                        "modifier_data": "thermal_modifier_data",
                        "all_thermal_modifiers": None,
                    },
                }
            else:
                self._material._props["ModifierData"] = {
                    "ThermalModifierData": {
                        "modifier_data": "thermal_modifier_data",
                        "all_thermal_modifiers": None,
                    }
                }
        return self._material.update()

    @pyaedt_function_handler()
    def add_thermal_modifier_free_form(self, formula, index=0):
        """Add a thermal modifier to a material property using a free-form formula.

        Parameters
        ----------
        formula : str
            Full formula to apply.
        index : int, optional
            Value for the index. The default is ``0``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDefinitionManager.EditMaterial

        Examples
        --------

        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss(version="2021.2")
        >>> mat1 = hfss.materials.add_material("new_copper2")
        >>> mat1.add_thermal_modifier_free_form("if(Temp > 1000cel, 1, if(Temp < -273.15cel, 1, 1))")
        """
        self._property_value[index].thermalmodifier = formula
        return self._add_thermal_modifier(formula, index)

    @pyaedt_function_handler(dataset_name="dataset")
    def add_thermal_modifier_dataset(self, dataset, index=0):
        """Add a thermal modifier to a material property using an existing dataset.

        Parameters
        ----------
        dataset : str
            Name of the project dataset.
        index : int, optional
            Value for the index. The default is ``0``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.


        References
        ----------
        >>> oDefinitionManager.EditMaterial

        Examples
        --------

        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss(version="2021.2")
        >>> mat1 = hfss.materials.add_material("new_copper2")
        >>> mat1.add_thermal_modifier_dataset("$ds1")
        """

        formula = f"pwl({dataset}, Temp)"
        self._property_value[index].thermalmodifier = formula
        return self._add_thermal_modifier(formula, index)

    @pyaedt_function_handler()
    def add_thermal_modifier_closed_form(
        self, tref=22, c1=0.0001, c2=1e-6, tl=-273.15, tu=1000, units="cel", auto_calc=True, tml=1000, tmu=1000, index=0
    ):
        """Add a thermal modifier to a material property using a closed-form formula.

        Parameters
        ----------
        tref : float, optional
            Reference temperature. The default is ``22``.
        c1 : float, optional
            First coefficient value. The default is ``0.0001``.
        c2 : float, optional
            Second coefficient value. The default is ``1e-6``.
        tl : float, optional
            Lower temperature limit. The default is ``273.15``.
        tu : float, optional
            Upper temperature limit. The default is ``1000``.
        units : str, optional
            Units for the reference temperature. The default
            is ``"cel"``.
        auto_calc : bool, optional
            Whether to calculate the lower and upper
            temperature limits automatically. The default is
            ``True``.
        tml : float, optional
            Lower temperature limit when ``auto_calc=True.``
            The default is ``1000``.
        tmu : float, optional
            Upper temperature limit when ``auto_calc=True.``
            The default is ``1000``.
        index : int, optional
            Value for the index. The default is ``0``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDefinitionManager.EditMaterial

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss(version="2021.2")
        >>> mat1 = hfss.materials.add_material("new_copper2")
        >>> mat1.permittivity.add_thermal_modifier_closed_form(c1 = 1e-3)
        """
        if index > len(self._property_value):
            self.logger.error(
                "Wrong index number. Index must be 0 for simple or nonlinear properties,"
                " <=2 for anisotropic materials, <=9 for Tensors"
            )
            return False
        self._property_value[index].thermalmodifier = ClosedFormTM()
        self._property_value[index].thermalmodifier.Tref = str(tref) + units
        self._property_value[index].thermalmodifier.C1 = str(c1)
        self._property_value[index].thermalmodifier.C2 = str(c2)
        self._property_value[index].thermalmodifier.TL = str(tl) + units
        self._property_value[index].thermalmodifier.TU = str(tu) + units
        self._property_value[index].thermalmodifier.autocalculation = auto_calc
        if not auto_calc:
            self._property_value[index].thermalmodifier.TML = tml
            self._property_value[index].thermalmodifier.TMU = tmu
        if auto_calc:
            tm_new = dict(
                {
                    "Property:": self.name,
                    "Index:": index,
                    "prop_modifier": "thermal_modifier",
                    "use_free_form": False,
                    "Tref": str(tref) + units,
                    "C1": str(c1),
                    "C2": str(c2),
                    "TL": str(tl) + units,
                    "TU": str(tu) + units,
                    "auto_calculation": True,
                }
            )
        else:
            tm_new = dict(
                {
                    "Property:": self.name,
                    "Index:": index,
                    "prop_modifier": "thermal_modifier",
                    "use_free_form": False,
                    "Tref": str(tref) + units,
                    "C1": str(c1),
                    "C2": str(c2),
                    "TL": str(tl) + units,
                    "TU": str(tu) + units,
                    "auto_calculation": False,
                    "TML": str(tml),
                    "TMU": str(tmu),
                }
            )
        if (
            "ModifierData" not in self._material._props
            or "ThermalModifierData" not in self._material._props["ModifierData"]
            or (
                "all_thermal_modifiers" in self._material._props["ModifierData"]["ThermalModifierData"]
                and bool(self._material._props["ModifierData"]["ThermalModifierData"]["all_thermal_modifiers"]) == False
            )
        ):
            if (
                "ModifierData" in self._material._props
                and "SpatialModifierData" in self._material._props["ModifierData"]
            ):
                self._material._props["ModifierData"] = dict(
                    {
                        "SpatialModifierData": self._material._props["ModifierData"]["SpatialModifierData"],
                        "ThermalModifierData": dict(
                            {
                                "modifier_data": "thermal_modifier_data",
                                "all_thermal_modifiers": dict({"one_spatial_modifier": tm_new}),
                            }
                        ),
                    }
                )
            else:
                self._material._props["ModifierData"] = dict(
                    {
                        "ThermalModifierData": dict(
                            {
                                "modifier_data": "thermal_modifier_data",
                                "all_thermal_modifiers": dict({"one_thermal_modifier": tm_new}),
                            }
                        )
                    }
                )
        else:
            for tmname in self._material._props["ModifierData"]["ThermalModifierData"]["all_thermal_modifiers"]:
                tm_definition = self._material._props["ModifierData"]["ThermalModifierData"]["all_thermal_modifiers"][
                    tmname
                ]
                if isinstance(tm_definition, list):
                    found = False
                    for tm in tm_definition:
                        if self.name == tm["Property:"] and index == tm["Index:"]:
                            found = True
                            tm["use_free_form"] = False
                            tm.pop("free_form_value", None)
                            tm["Tref"] = str(tref) + units
                            tm["C1"] = str(c1)
                            tm["C2"] = str(c2)
                            tm["TL"] = str(tl) + units
                            tm["TU"] = str(tu) + units
                            tm["auto_calculation"] = auto_calc
                            if not auto_calc:
                                tm["TML"] = tml
                                tm["TMU"] = tmu
                            else:
                                tm.pop("TML", None)
                                tm.pop("TMU", None)
                    if not found:
                        tm_definition.append(tm_new)
                elif self.name == tm_definition["Property:"] and index == tm_definition["Index:"]:
                    tm_definition["use_free_form"] = False
                    tm_definition.pop("free_form_value", None)
                    tm_definition["Tref"] = str(tref) + units
                    tm_definition["C1"] = str(c1)
                    tm_definition["C2"] = str(c1)
                    tm_definition["TL"] = str(tl) + units
                    tm_definition["TU"] = str(tl) + units
                    tm_definition["auto_calculation"] = auto_calc
                    if not auto_calc:
                        tm_definition["TML"] = str(tml)
                        tm_definition["TMU"] = str(tmu)
                    else:
                        tm_definition.pop("TML", None)
                        tm_definition.pop("TMU", None)
                else:
                    tm_definition = [tm_definition]
                    tm_definition.append(tm_new)
            self._material._props["ModifierData"] = dict(
                {
                    "ThermalModifierData": dict(
                        {
                            "modifier_data": "thermal_modifier_data",
                            "all_thermal_modifiers": dict({"one_thermal_modifier": tm_definition}),
                        }
                    )
                }
            )
        return self._material.update()

    @pyaedt_function_handler()
    def _set_non_linear(self, x_unit=None, y_unit=None):
        """Enable non-linear material.

         This is a private method, and should not be used directly.

        Parameters
        ----------
        x_unit : str, optional
            X units. Defaults will be used if `None`.
        y_unit : str, optional
            Y units. Defaults will be used if `None`.

        Returns
        -------
        bool
            `True` if succeeded.

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss(version="2025.1")
        >>> B_value = [0.0, 0.1, 0.3, 0.4, 0.48, 0.55, 0.6, 0.61, 0.65]
        >>> H_value = [0.0, 500.0, 1000.0, 1500.0, 2000.0, 2500.0, 3500.0, 5000.0, 10000.0]
        >>> mat = hfss.materials.add_material("newMat")
        >>> b_h_dataset = [[b, h] for b, h in zip(B_value, H_value)]
        >>> mat.permeability = b_h_dataset
        """
        if self.name not in ["permeability", "conductivity", "permittivity"]:
            self.logger.error(
                "Non linear parameters are only supported for permeability, conductivity and permittivity."
            )
            return False
        self.type = "nonlinear"
        if self.name == "permeability":
            if not x_unit:
                x_unit = "tesla"
            if not y_unit:
                y_unit = "A_per_meter"
            self.bunit = x_unit
            self.hunit = y_unit
            self.is_temperature_dependent = False
            self.btype_for_single_curve = "normal"
            self.temperatures = {}
        elif self.name == "permittivity":
            if not x_unit:
                x_unit = "V_per_meter"
            if not y_unit:
                y_unit = "C_per_m2"
            self._unit = [x_unit, y_unit]
        elif self.name == "conductivity":
            if not x_unit:
                x_unit = "V_per_meter"
            if not y_unit:
                y_unit = "A_per_m2"
            self._unit = [x_unit, y_unit]
        if self._material._material_update:
            return self._material._update_props(self.name, self._property_value[0].value)
        else:
            return True

    @property
    def spatialmodifier(self):
        """Spatial modifier."""
        if len(self._property_value) == 1:
            return self._property_value[0].spatialmodifier
        else:
            return [i.spatialmodifier for i in self._property_value]

    @spatialmodifier.setter
    def spatialmodifier(self, spatial_value):
        """Spatial modifier.

        References
        ----------
        >>> oDefinitionManager.EditMaterial
        """
        if spatial_value is None:
            self._property_value[0].spatialmodifier = None
            self._reset_spatial_modifier()
        elif isinstance(spatial_value, str):
            self._property_value[0].spatialmodifier = spatial_value
            self._add_spatial_modifier(spatial_value, 0)
        else:
            for i, value in enumerate(spatial_value):
                self._add_spatial_modifier(value, i)
                try:
                    self._property_value[i].spatialmodifier = value
                except IndexError:
                    self._property_value.append(BasicValue())
                    self._property_value[i].spatialmodifier = value

    def _add_spatial_modifier(self, formula, index):
        """Add a spatial modifier.

        Parameters
        ----------
        formula : str
            Formula to apply.
        index : int
            Value for the index.

        Returns
        -------
        type

        """
        if (
            "ModifierData" not in self._material._props
            or "SpatialModifierData" not in self._material._props["ModifierData"]
            or (
                "all_spatial_modifiers" in self._material._props["ModifierData"]["SpatialModifierData"]
                and bool(self._material._props["ModifierData"]["SpatialModifierData"]["all_spatial_modifiers"]) == False
            )
        ):
            sm = dict(
                {
                    "Property:": self.name,
                    "Index:": index,
                    "prop_modifier": "spatial_modifier",
                    "free_form_value": formula,
                }
            )
            if (
                "ModifierData" in self._material._props
                and "ThermalModifierData" in self._material._props["ModifierData"]
            ):
                self._material._props["ModifierData"] = dict(
                    {
                        "ThermalModifierData": self._material._props["ModifierData"]["ThermalModifierData"],
                        "SpatialModifierData": dict(
                            {
                                "modifier_data": "spatial_modifier_data",
                                "all_spatial_modifiers": dict({"one_spatial_modifier": sm}),
                            }
                        ),
                    }
                )
            else:
                self._material._props["ModifierData"] = dict(
                    {
                        "SpatialModifierData": dict(
                            {
                                "modifier_data": "spatial_modifier_data",
                                "all_spatial_modifiers": dict({"one_spatial_modifier": sm}),
                            }
                        )
                    }
                )
        else:
            for smname in self._material._props["ModifierData"]["SpatialModifierData"]["all_spatial_modifiers"]:
                if isinstance(
                    self._material._props["ModifierData"]["SpatialModifierData"]["all_spatial_modifiers"][smname], list
                ):
                    found = False
                    for sm in self._material._props["ModifierData"]["SpatialModifierData"]["all_spatial_modifiers"][
                        smname
                    ]:
                        if self.name == sm["Property:"] and index == sm["Index:"]:
                            found = True
                            sm["free_form_value"] = formula

                    if not found:
                        sm = dict(
                            {
                                "Property:": self.name,
                                "Index:": index,
                                "prop_modifier": "spatial_modifier",
                                "free_form_value": formula,
                            }
                        )
                        self._material._props["ModifierData"]["SpatialModifierData"]["all_spatial_modifiers"][
                            smname
                        ].append(sm)
                elif (
                    self.name
                    == self._material._props["ModifierData"]["SpatialModifierData"]["all_spatial_modifiers"][smname][
                        "Property:"
                    ]
                    and index
                    == self._material._props["ModifierData"]["SpatialModifierData"]["all_spatial_modifiers"][smname][
                        "Index:"
                    ]
                ):
                    self._material._props["ModifierData"]["SpatialModifierData"]["all_spatial_modifiers"][smname][
                        "free_form_value"
                    ] = formula

                else:
                    self._material._props["ModifierData"]["SpatialModifierData"]["all_spatial_modifiers"][smname] = [
                        self._material._props["ModifierData"]["SpatialModifierData"]["all_spatial_modifiers"][smname]
                    ]
                    sm = dict(
                        {
                            "Property:": self.name,
                            "Index:": index,
                            "prop_modifier": "spatial_modifier",
                            "free_form_value": formula,
                        }
                    )
                    self._material._props["ModifierData"]["SpatialModifierData"]["all_spatial_modifiers"][
                        smname
                    ].append(sm)
        return self._material.update()

    def _reset_spatial_modifier(self):
        """Set the spatial modifier to None.

        Returns
        -------
        type

        """
        if "ModifierData" in self._material._props and "SpatialModifierData" in self._material._props["ModifierData"]:
            if (
                "ModifierData" in self._material._props
                and "ThermalModifierData" in self._material._props["ModifierData"]
            ):
                self._material._props["ModifierData"] = {
                    "ThermalModifierData": self._material._props["ModifierData"]["ThermalModifierData"],
                    "SpatialModifierData": {
                        "modifier_data": "spatial_modifier_data",
                        "all_spatial_modifiers": None,
                    },
                }
            else:
                self._material._props["ModifierData"] = {
                    "SpatialModifierData": {
                        "modifier_data": "spatial_modifier_data",
                        "all_spatial_modifiers": None,
                    }
                }
        return self._material.update()

    @pyaedt_function_handler()
    def add_spatial_modifier_free_form(self, formula, index=0):
        """Add a spatial modifier to a material property using a free-form formula.

        Parameters
        ----------
        formula : str
            Full formula to apply.
        index : int, optional
            Value for the index. The default is ``0``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDefinitionManager.EditMaterial

        Examples
        --------

        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss(version="2021.2")
        >>> mat1 = hfss.materials.add_material("new_copper2")
        >>> mat1.add_spatial_modifier_free_form("if(X > 1mm, 1, if(X < 1mm, 2, 1))")
        """
        self._property_value[index].spatialmodifier = formula
        return self._add_spatial_modifier(formula, index)

    @pyaedt_function_handler(dataset_name="dataset")
    def add_spatial_modifier_dataset(self, dataset, index=0):
        """Add a spatial modifier to a material property using an existing dataset.

        Parameters
        ----------
        dataset : str
            Name of the project dataset.
        index : int, optional
            Value for the index. The default is ``0``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.


        References
        ----------
        >>> oDefinitionManager.EditMaterial

        Examples
        --------
        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss(version="2021.2")
        >>> mat1 = hfss.materials.add_material("new_copper2")
        >>> mat1.add_spatial_modifier_dataset("$ds1")
        """
        formula = f"clp({dataset}, X,Y,Z)"
        self._property_value[index].spatialmodifier = formula
        return self._add_spatial_modifier(formula, index)


class CommonMaterial(object):
    """Manages datasets with frequency-dependent materials.

    Parameters
    ----------
    materials : :class:`ansys.aedt.core.modules.material_lib.Materials`
    name : str
    props : dict
        The default is ``None``.
    """

    def __init__(self, materials, name, props=None):
        self._materials = materials
        self.odefinition_manager = self._materials.odefinition_manager
        self._omaterial_manager = self._materials.omaterial_manager

        self._oproject = self._materials._oproject
        self.logger = self._materials.logger
        self.name = name
        self._coordinate_system = ""
        self.is_sweep_material = False
        if props:
            self._props = copy.deepcopy(props)
        else:
            self._props = {}
        if "CoordinateSystemType" in self._props:
            self._coordinate_system = self._props["CoordinateSystemType"]
        else:
            self._props["CoordinateSystemType"] = "Cartesian"
            self._coordinate_system = "Cartesian"
        if "BulkOrSurfaceType" in self._props:
            self.bulkorsurface = self._props["BulkOrSurfaceType"]
        else:
            self._props["BulkOrSurfaceType"] = 1
        if "ModTime" in self._props:
            self._modtime = self._props["ModTime"]
            del self._props["ModTime"]
        if "LibLocation" in self._props:
            self.lib_location = self._props["LibLocation"]
            del self._props["LibLocation"]
        if "ModSinceLib" in self._props:
            self.mod_since_lib = self._props["ModSinceLib"]
            del self._props["ModSinceLib"]

    @property
    def is_used(self):
        """Checks if a project material is in use."""
        is_used = self._omaterial_manager.IsUsed(self.name)
        if is_used == 0:
            return False
        return True

    @property
    def coordinate_system(self):
        """Material coordinate system."""
        return self._coordinate_system

    @coordinate_system.setter
    def coordinate_system(self, value):
        if value in ["Cartesian", "Cylindrical", "Spherical"]:
            self._coordinate_system = value
            self._update_props("CoordinateSystemType", value)

    @pyaedt_function_handler()
    def _get_args(self, props=None):
        """Retrieve the arguments for a property.

        Parameters
        ----------
        props : str, optional
            Name of the property.  The default is ``None``.
        """
        if not props:
            props = self._props
        arg = ["NAME:" + self.name]
        _dict2arg(props, arg)
        return arg

    def _update_props(self, propname, propvalue, update_aedt=True):
        """Update properties.

        Parameters
        ----------
        propname : str
            Name of the property.
        propvalue :
            Value of the property.
        update_aedt : bool, optional
            Whether to update the property in AEDT. The default is ``True``.
        """
        try:
            material_props = getattr(self, propname)
            material_props_type = material_props.type
        except Exception:
            material_props_type = None

        if isinstance(propvalue, list) and material_props_type and material_props_type in ["tensor", "anisotropic"]:
            i = 1
            for val in propvalue:
                if not self._props.get(propname, None) or not isinstance(self._props[propname], dict):
                    if material_props_type == "tensor":
                        self._props[propname] = dict({"property_type": "TensorProperty"})
                        self._props[propname]["Symmetric"] = False
                    else:
                        self._props[propname] = dict({"property_type": "AnisoProperty"})
                    self._props[propname]["unit"] = ""
                self._props[propname]["component" + str(i)] = str(val)
                i += 1
            if update_aedt:
                return self.update()
        elif isinstance(propvalue, (str, float, int)):
            self._props[propname] = str(propvalue)
            if update_aedt:
                return self.update()
        elif isinstance(propvalue, dict):
            self._props[propname] = propvalue
            if update_aedt:
                return self.update()
        elif isinstance(propvalue, list) and material_props_type and material_props_type == "nonlinear":
            if propname == "permeability":
                bh = dict({"DimUnits": ["", ""]})
                for point in propvalue:
                    if "Point" in bh:
                        bh["Point"].append(point)
                    else:
                        bh["Point"] = [point]
                self._props[propname] = dict({"property_type": "nonlinear"})
                self._props[propname]["BTypeForSingleCurve"] = self.__dict__["_" + propname].btype_for_single_curve
                self._props[propname]["HUnit"] = self.__dict__["_" + propname].hunit
                self._props[propname]["BUnit"] = self.__dict__["_" + propname].bunit
                self._props[propname]["IsTemperatureDependent"] = self.__dict__["_" + propname].is_temperature_dependent
                self._props[propname]["BHCoordinates"] = bh
                try:
                    self._props[propname]["BHCoordinates"]["Temperatures"] = self.__dict__["_" + propname].temperatures
                except Exception:
                    self._props[propname]["BHCoordinates"]["Temperatures"] = {}
            else:
                bh = dict({"DimUnits": [self.__dict__["_" + propname]._unit]})
                for point in propvalue:
                    if "Point" in bh:
                        bh["Point"].append(point)
                    else:
                        bh["Point"] = [point]
                if propname == "conductivity":
                    pr_name = "JECoordinates"
                else:
                    pr_name = "DECoordinates"
                self._props[propname] = dict({"property_type": "nonlinear", pr_name: bh})
            if update_aedt:
                return self.update()
        elif isinstance(propvalue, list) and material_props_type and material_props_type == "vector":
            if propname == "magnetic_coercivity":
                return self.set_magnetic_coercivity(propvalue[0], propvalue[1], propvalue[2], propvalue[3])
        return False


class Material(CommonMaterial, object):
    """Manages material properties.

    Parameters
    ----------
    materiallib : :class:`ansys.aedt.core.modules.material_lib.Materials`
        Inherited parent object.
    name : str
        Name of the material.
    props :
        The default is ``None``.
    material_update : bool, optional
        The default is ``True``.

    Examples
    --------
    >>> from ansys.aedt.core import Hfss
    >>> app = Hfss()
    >>> material = app.materials["copper"]
    """

    def __init__(self, materiallib, name, props=None, material_update=True):
        CommonMaterial.__init__(self, materiallib, name, props)
        self.thermal_material_type = "Solid"
        self._material_update = material_update
        self._wire_type = None
        self._wire_width = None
        self._wire_diameter = None
        self._wire_width_direction = None
        self._wire_thickness_direction = None
        self._wire_thickness = None
        self._stacking_type = None
        self._stacking_direction = None
        self._stacking_factor = None
        self._strand_number = None

        if "thermal_material_type" in self._props:
            self.thermal_material_type = self._props["thermal_material_type"]["Choice"]
        if "PhysicsTypes" in self._props:
            self.physics_type = self._props["PhysicsTypes"]["set"]
        else:
            self.physics_type = ["Electromagnetic", "Thermal", "Structural"]
            self._props["PhysicsTypes"] = dict({"set": ["Electromagnetic", "Thermal", "Structural"]})
        if "AttachedData" in self._props and "MatAppearanceData" in self._props["AttachedData"]:
            self._material_appearance = []
            self._material_appearance.append(self._props["AttachedData"]["MatAppearanceData"]["Red"])
            self._material_appearance.append(self._props["AttachedData"]["MatAppearanceData"]["Green"])
            self._material_appearance.append(self._props["AttachedData"]["MatAppearanceData"]["Blue"])
            self._material_appearance.append(self._props["AttachedData"]["MatAppearanceData"].get("Transparency", 0.0))
        else:
            vals = list(CSS4_COLORS.values())
            if (materiallib._color_id) >= len(vals):
                materiallib._color_id = 0
            h = vals[materiallib._color_id].lstrip("#")
            self._material_appearance = list(int(h[i : i + 2], 16) for i in (0, 2, 4))
            materiallib._color_id += 1
            self._material_appearance.append(0)
            self._props["AttachedData"] = dict(
                {
                    "MatAppearanceData": dict(
                        {
                            "property_data": "appearance_data",
                            "Red": self._material_appearance[0],
                            "Green": self._material_appearance[1],
                            "Blue": self._material_appearance[2],
                            "Transparency": self._material_appearance[3],
                        }
                    )
                }
            )
        if "stacking_type" in self._props:
            self.stacking_type = self._props["stacking_type"]["Choice"]

        if "wire_type" in self._props:
            self.wire_type = self._props["wire_type"]["Choice"]

        # Update the material properties
        for property in MatProperties.aedtname:
            tmods = None
            smods = None
            if "ModifierData" in self._props:
                if "ThermalModifierData" in self._props["ModifierData"]:
                    modifiers = self._props["ModifierData"]["ThermalModifierData"]["all_thermal_modifiers"]
                    for mod in modifiers:
                        if isinstance(modifiers[mod], list):
                            for one_tm in modifiers[mod]:
                                if one_tm["Property:"] == property:
                                    if tmods:
                                        tmods = [tmods]
                                        tmods.append(one_tm)
                                    else:
                                        tmods = one_tm
                        else:
                            if modifiers[mod]["Property:"] == property:
                                tmods = modifiers[mod]
                if "SpatialModifierData" in self._props["ModifierData"]:
                    modifiers = self._props["ModifierData"]["SpatialModifierData"]["all_spatial_modifiers"]
                    for mod in modifiers:
                        if isinstance(modifiers[mod], list):
                            for one_tm in modifiers[mod]:
                                if one_tm["Property:"] == property:
                                    if smods:
                                        smods = [smods]
                                        smods.append(one_tm)
                                    else:
                                        smods = one_tm
                        else:
                            if modifiers[mod]["Property:"] == property:
                                smods = modifiers[mod]
            property_value = (
                self._props[property] if property in self._props else MatProperties.get_defaultvalue(aedtname=property)
            )
            self.__dict__["_" + property] = MatProperty(self, property, property_value, tmods, smods)

    @property
    def material_appearance(self):
        """Material appearance specified as a list.

        The first three items are RGB color and the fourth one is transparency.

        Returns
        -------
        list
            Color of the material in RGB and transparency.
            Color values are in the range ``[0, 255]``.
            Transparency is a float in the range ``[0,1]``.

        Examples
        --------
        Create a material with color ``[0, 153, 153]`` (darker cyan) and transparency ``0.5``.

        >>> from ansys.aedt.core import Hfss
        >>> hfss = Hfss(version="2021.2")
        >>> mat1 = hfss.materials.add_material("new_material")
        >>> appearance_props = mat1.material_appearance
        >>> mat1.material_appearance = [0, 153, 153, 0.5]
        """
        return self._material_appearance

    @material_appearance.setter
    def material_appearance(self, appearance_props):
        if not isinstance(appearance_props, (list, tuple)):
            raise TypeError("`material_appearance` must be a list or tuple.")
        if len(appearance_props) != 3 and len(appearance_props) != 4:
            raise ValueError("`material_appearance` must be four items (R, G, B, transparency).")
        elif len(appearance_props) == 3:
            transparency_value = self.material_appearance[3]
            msg = "Only RGB specified. Transparency is set to " + str(transparency_value)
            self.logger.info(msg)
            appearance_props.append(transparency_value)
        value = []
        for i in range(len(appearance_props)):
            if i < 3:
                rgb_int = int(appearance_props[i])
                if rgb_int < 0 or rgb_int > 255:
                    raise ValueError("RGB value must be between 0 and 255.")
                value.append(rgb_int)
            else:
                transparency = float(appearance_props[i])
                if transparency < 0 or transparency > 1:
                    raise ValueError("Transparency value must be between 0 and 1.")
                value.append(transparency)
        self._material_appearance = value
        self._props["AttachedData"] = dict(
            {
                "MatAppearanceData": dict(
                    {
                        "property_data": "appearance_data",
                        "Red": value[0],
                        "Green": value[1],
                        "Blue": value[2],
                        "Transparency": value[3],
                    }
                )
            }
        )
        self.update()

    @property
    def permittivity(self):
        """Permittivity.

        Returns
        -------
        :class:`ansys.aedt.core.modules.material.MatProperty`
            Permittivity of the material.

        References
        ----------
        >>> oDefinitionManager.EditMaterial
        """
        return self._permittivity

    @permittivity.setter
    def permittivity(self, value):
        self._permittivity.value = value

    @property
    def permeability(self):
        """Permeability.

        Returns
        -------
        :class:`ansys.aedt.core.modules.material.MatProperty`
            Permeability of the material.

        References
        ----------
        >>> oDefinitionManager.EditMaterial
        """
        return self._permeability

    @permeability.setter
    def permeability(self, value):
        self._permeability.value = value

    @property
    def conductivity(self):
        """Conductivity.

        Returns
        -------
        :class:`ansys.aedt.core.modules.material.MatProperty`
            Conductivity of the material.

        References
        ----------
        >>> oDefinitionManager.EditMaterial
        """
        return self._conductivity

    @conductivity.setter
    def conductivity(self, value):
        self._conductivity.value = value

    @property
    def dielectric_loss_tangent(self):
        """Dielectric loss tangent.

        Returns
        -------
        :class:`ansys.aedt.core.modules.MatProperty`
            Dielectric loss tangent of the material.
        """
        return self._dielectric_loss_tangent

    @dielectric_loss_tangent.setter
    def dielectric_loss_tangent(self, value):
        self._dielectric_loss_tangent.value = value

    @property
    def magnetic_loss_tangent(self):
        """Magnetic loss tangent.

        Returns
        -------
        :class:`ansys.aedt.core.modules.material.MatProperty`
            Magnetic loss tangent of the material.

        References
        ----------
        >>> oDefinitionManager.EditMaterial
        """
        return self._magnetic_loss_tangent

    @magnetic_loss_tangent.setter
    def magnetic_loss_tangent(self, value):
        self._magnetic_loss_tangent.value = value

    @property
    def thermal_conductivity(self):
        """Thermal conductivity.

        Returns
        -------
        :class:`ansys.aedt.core.modules.material.MatProperty`
            Thermal conductivity of the material.

        References
        ----------
        >>> oDefinitionManager.EditMaterial
        """
        return self._thermal_conductivity

    @thermal_conductivity.setter
    def thermal_conductivity(self, value):
        self._props["PhysicsTypes"] = dict({"set": ["Electromagnetic", "Thermal", "Structural"]})
        self.physics_type = ["Electromagnetic", "Thermal", "Structural"]
        self._thermal_conductivity.value = value

    @property
    def mass_density(self):
        """Mass density.

        Returns
        -------
        :class:`ansys.aedt.core.modules.material.MatProperty`
            Mass density of the material.

        References
        ----------
        >>> oDefinitionManager.EditMaterial
        """
        return self._mass_density

    @mass_density.setter
    def mass_density(self, value):
        self._mass_density.value = value

    @property
    def specific_heat(self):
        """Specific heat.

        Returns
        -------
        :class:`ansys.aedt.core.modules.material.MatProperty`
            Specific heat of the material.

        References
        ----------
        >>> oDefinitionManager.EditMaterial
        """
        return self._specific_heat

    @specific_heat.setter
    def specific_heat(self, value):
        self._specific_heat.value = value

    @property
    def thermal_expansion_coefficient(self):
        """Thermal expansion coefficient.

        Returns
        -------
        :class:`ansys.aedt.core.modules.material.MatProperty`
            Thermal expansion coefficient of the material.

        References
        ----------
        >>> oDefinitionManager.EditMaterial
        """
        return self._thermal_expansion_coefficient

    @thermal_expansion_coefficient.setter
    def thermal_expansion_coefficient(self, value):
        self._thermal_expansion_coefficient.value = value

    @property
    def youngs_modulus(self):
        """Young's modulus.

        Returns
        -------
        :class:`ansys.aedt.core.modules.material.MatProperty`
            Young's modulus of the material.

        References
        ----------
        >>> oDefinitionManager.EditMaterial
        """
        return self._youngs_modulus

    @youngs_modulus.setter
    def youngs_modulus(self, value):
        self.physics_type = ["Electromagnetic", "Thermal", "Structural"]
        self._props["PhysicsTypes"] = dict({"set": ["Electromagnetic", "Thermal", "Structural"]})
        self._youngs_modulus.value = value

    @property
    def poissons_ratio(self):
        """Poisson's ratio.

        Returns
        -------
        :class:`ansys.aedt.core.modules.material.MatProperty`
            Poisson's ratio of the material.

        References
        ----------
        >>> oDefinitionManager.EditMaterial
        """
        return self._poissons_ratio

    @poissons_ratio.setter
    def poissons_ratio(self, value):
        self.physics_type = ["Electromagnetic", "Thermal", "Structural"]
        self._props["PhysicsTypes"] = dict({"set": ["Electromagnetic", "Thermal", "Structural"]})
        self._poissons_ratio.value = value

    @property
    def diffusivity(self):
        """Diffusivity.

        Returns
        -------
        :class:`ansys.aedt.core.modules.material.MatProperty`
            Diffusivity of the material.

        References
        ----------
        >>> oDefinitionManager.EditMaterial
        """
        return self._diffusivity

    @diffusivity.setter
    def diffusivity(self, value):
        self._diffusivity.value = value

    @property
    def magnetic_coercivity(self):
        """Magnetic coercivity.

        Returns
        -------
        :class:`ansys.aedt.core.modules.material.MatProperty`
            Magnetic coercivity of the material.

        References
        ----------
        >>> oDefinitionManager.EditMaterial
        """
        return self._magnetic_coercivity

    @magnetic_coercivity.setter
    def magnetic_coercivity(self, value):
        if isinstance(value, list) and len(value) == 4:
            self.set_magnetic_coercivity(value[0], value[1], value[2], value[3])
            self._magnetic_coercivity.value = value

    @property
    def molecular_mass(self):
        """Molecular mass.

        Returns
        -------
        :class:`ansys.aedt.core.modules.material.MatProperty`
            Molecular mass of the material.

        References
        ----------
        >>> oDefinitionManager.EditMaterial
        """
        return self._molecular_mass

    @molecular_mass.setter
    def molecular_mass(self, value):
        self._molecular_mass.value = value

    @property
    def viscosity(self):
        """Viscosity.

        Returns
        -------
        :class:`ansys.aedt.core.modules.material.MatProperty`
            Viscosity of the material.

        References
        ----------
        >>> oDefinitionManager.EditMaterial
        """
        return self._viscosity

    @viscosity.setter
    def viscosity(self, value):
        self._viscosity.value = value

    @property
    def stacking_type(self):
        """Composition of the wire can either be "Solid", "Lamination" or "Litz Wire".

        Returns
        -------
        string
            Structure of the wire.

        References
        ----------
        >>> oDefinitionManager.EditMaterial
        """
        return self._stacking_type

    @stacking_type.setter
    def stacking_type(self, value):
        if not value in ["Solid", "Lamination", "Litz Wire"]:
            raise ValueError("Composition of the wire can either be 'Solid', 'Lamination' or 'Litz Wire'.")

        self._stacking_type = value
        if self._material_update:
            self._update_props(
                "stacking_type",
                dict(
                    {
                        "property_type": "ChoiceProperty",
                        "Choice": value,
                    }
                ),
            )

    @property
    def wire_type(self):
        """The type of the wire can either be "Round", "Square" or "Rectangular".

        Returns
        -------
        string
            Type of the wire.

        References
        ----------
        >>> oDefinitionManager.EditMaterial
        """
        return self._wire_type

    @wire_type.setter
    def wire_type(self, value):
        if not value in ["Round", "Square", "Rectangular"]:
            raise ValueError("The type of the wire can either be 'Round', 'Square' or 'Rectangular'.")

        self._wire_type = value
        if self._material_update:
            self._update_props("wire_type", dict({"property_type": "ChoiceProperty", "Choice": value}))

    @property
    def wire_thickness_direction(self):
        """Thickness direction of the wire can either be "V(1)", "V(2)" or "V(3)".

        Returns
        -------
        string
            Thickness direction of the wire.

        References
        ----------
        >>> oDefinitionManager.EditMaterial
        """
        return self._wire_thickness_direction

    @wire_thickness_direction.setter
    def wire_thickness_direction(self, value):
        if not value in ["V(1)", "V(2)", "V(3)"]:
            raise ValueError("Thickness direction of the wire can either be 'V(1)', 'V(2)' or 'V(3)'.")

        self._wire_thickness_direction = value
        if self._material_update:
            self._update_props("wire_thickness_direction", dict({"property_type": "ChoiceProperty", "Choice": value}))

    @property
    def wire_width_direction(self):
        """Width direction of the wire can either be "V(1)", "V(2)" or "V(3)".

        Returns
        -------
        string
            Width direction of the wire.

        References
        ----------
        >>> oDefinitionManager.EditMaterial
        """
        return self._wire_width_direction

    @wire_width_direction.setter
    def wire_width_direction(self, value):
        if not value in ["V(1)", "V(2)", "V(3)"]:
            raise ValueError("Width direction of the wire can either be 'V(1)', 'V(2)' or 'V(3)'.")

        self._wire_width_direction = value
        if self._material_update:
            self._update_props("wire_width_direction", dict({"property_type": "ChoiceProperty", "Choice": value}))

    @property
    def strand_number(self):
        """Strand number for litz wire.

        Returns
        -------
        :class:`ansys.aedt.core.modules.material.MatProperty`
            Number of strands for the wire.

        References
        ----------
        >>> oDefinitionManager.EditMaterial
        """
        return self._strand_number

    @strand_number.setter
    def strand_number(self, value):
        self._strand_number = value
        if self._material_update:
            self._update_props("strand_number", value)

    @property
    def wire_thickness(self):
        """Thickness of rectangular litz wire.

        Returns
        -------
        :class:`ansys.aedt.core.modules.material.MatProperty`
            Thickness of the litz wire.

        References
        ----------
        >>> oDefinitionManager.EditMaterial
        """
        return self._wire_thickness

    @wire_thickness.setter
    def wire_thickness(self, value):
        self._wire_thickness = value
        if self._material_update:
            self._update_props("wire_thickness", value)

    @property
    def wire_diameter(self):
        """Diameter of the round litz wire.

        Returns
        -------
        :class:`ansys.aedt.core.modules.material.MatProperty`
            Diameter of the litz wire.

        References
        ----------
        >>> oDefinitionManager.EditMaterial
        """
        return self._wire_diameter

    @wire_diameter.setter
    def wire_diameter(self, value):
        self._wire_diameter = value
        if self._material_update:
            self._update_props("wire_diameter", value)

    @property
    def wire_width(self):
        """Width of the rectangular or square litz wire.

        Returns
        -------
        :class:`ansys.aedt.core.modules.material.MatProperty`
            Width of the litz wire.

        References
        ----------
        >>> oDefinitionManager.EditMaterial
        """
        return self._wire_width

    @wire_width.setter
    def wire_width(self, value):
        self._wire_width = value
        if self._material_update:
            self._update_props("wire_width", value)

    @property
    def stacking_factor(self):
        """Stacking factor for lamination.

        Returns
        -------
        :class:`ansys.aedt.core.modules.material.MatProperty`
            Stacking factor.

        References
        ----------
        >>> oDefinitionManager.EditMaterial
        """
        return self._stacking_factor

    @stacking_factor.setter
    def stacking_factor(self, value):
        self._stacking_factor = value
        if self._material_update:
            self._update_props("stacking_factor", value)

    @property
    def stacking_direction(self):
        """Stacking direction for the lamination can either be "V(1)", "V(2)" or "V(3)".

        Returns
        -------
        string
            Stacking direction for lamination.

        References
        ----------
        >>> oDefinitionManager.EditMaterial
        """
        return self._stacking_direction

    @stacking_direction.setter
    def stacking_direction(self, value):
        if not value in ["V(1)", "V(2)", "V(3)"]:
            raise ValueError("Stacking direction for the lamination either be 'V(1)', 'V(2)' or 'V(3)'.")

        self._stacking_direction = value
        if self._material_update:
            self._update_props("stacking_direction", dict({"property_type": "ChoiceProperty", "Choice": value}))

    @pyaedt_function_handler()
    def set_magnetic_coercitivity(self, value=0, x=1, y=0, z=0):  # pragma: no cover
        """Set magnetic coercivity for material.

        .. deprecated:: 0.7.0

        Returns
        -------
        bool

        """
        warnings.warn(
            "`set_magnetic_coercitivity` is deprecated. Use `set_magnetic_coercivity` instead.", DeprecationWarning
        )
        return self.set_magnetic_coercivity(value, x, y, z)

    @pyaedt_function_handler()
    def set_magnetic_coercivity(self, value=0, x=1, y=0, z=0):
        """Set magnetic coercivity for material.

        Parameters
        ----------
        value : float, optional
            Magnitude in A_per_meter. Default value is ``0``.
        x : float, optional
            Vector x component. Default value is ``1``.
        y : float, optional
            Vector y component. Default value is ``0``.
        z : float, optional
            Vector z component. Default value is ``0``.

        Returns
        -------
        bool
        """
        self._props["magnetic_coercivity"] = dict(
            {
                "property_type": "VectorProperty",
                "Magnitude": f"{value}A_per_meter",
                "DirComp1": str(x),
                "DirComp2": str(y),
                "DirComp3": str(z),
            }
        )
        return self.update()

    @pyaedt_function_handler(points_list_at_freq="points_at_frequency")
    def get_core_loss_coefficients(
        self,
        points_at_frequency,
        core_loss_model_type="Electrical Steel",
        thickness="0.5mm",
        conductivity=0,
        coefficient_setup="w_per_cubic_meter",
    ):
        """Get electrical steel or power ferrite core loss coefficients at a given frequency.

        Parameters
        ----------
        points_at_frequency : dict
            Dictionary where keys are the frequencies (in Hz) and values are lists of points (BP curve).
            If the core loss model is calculated at one frequency, this parameter must be provided as a
            dictionary with one key (single frequency in Hz) and values are lists of points at
            that specific frequency (BP curve).
        core_loss_model_type : str, optional
            Core loss model type. The default value is ``"Electrical Steel"``.
            Options are ``"Electrical Steel"`` and ``"Power Ferrite"``.
        thickness : str, optional
            Thickness provided as the value plus the unit.
            The default is ``0.5mm``.
        conductivity : float, optional
            Material conductivity.
            The default is ``0``.
        coefficient_setup : str, optional
            Core loss unit. The default is ``"w_per_cubic_meter"``.
            Options are ``"kw_per_cubic_meter"``, ``"w_per_cubic_meter"``, ``"w_per_kg"``,
            and ``"w_per_lb"``.


        Returns
        -------
        list
            List of core loss coefficients.
            Returns Kh, Kc, and Ke coefficients if the core loss model is ``"Electrical Steel"``.
            Returns Cm, X, and Y if the core loss model is ``"Power Ferrite"``.

        Examples
        --------
        This example shows how to get core loss coefficients for Electrical Steel core loss model.

        >>> from ansys.aedt.core import Maxwell3d
        >>> m3d = Maxwell3d()
        >>> box = m3d.modeler.create_box([-10, -10, 0],[20, 20, 20],"box_to_split")
        >>> box.material = "magnesium"
        >>> coefficients = m3d.materials["magnesium"].get_core_loss_coefficients(
        ...                                                         points_at_frequency={60 : [[0, 0], [1, 3], [2, 7]]},
        ...                                                         thickness="0.5mm",conductivity=0)
        >>> print(coefficients)
        >>> m3d.release_desktop(True, True)
        """
        if not isinstance(points_at_frequency, dict):
            raise TypeError("Points list at frequency must be provided as a dictionary.")
        if not isinstance(thickness, str):
            raise TypeError("Thickness must be provided as a string with value and unit.")
        else:
            value, unit = decompose_variable_value(thickness)
            if not is_number(value) and not unit:
                raise TypeError("Thickness must be provided as a string with value and unit.")
        if len(points_at_frequency) <= 1 and core_loss_model_type == "Power Ferrite":
            raise ValueError("At least 2 frequencies must be included.")
        props = {}
        freq_keys = list(points_at_frequency.keys())
        for i in range(0, len(freq_keys)):
            if isinstance(freq_keys[i], str):
                value, unit = decompose_variable_value(freq_keys[i])
                if unit != "Hz":
                    value = unit_converter(values=value, unit_system="Freq", input_units=unit, output_units="Hz")
                points_at_frequency[value] = points_at_frequency[freq_keys[i]]
                del points_at_frequency[freq_keys[i]]

        if len(points_at_frequency) == 1:
            props["CoefficientSetupData"] = {}
            props["CoefficientSetupData"]["property_data"] = "coreloss_data"
            props["CoefficientSetupData"]["coefficient_setup"] = coefficient_setup
            frequency = list(points_at_frequency.keys())[0]
            props["CoefficientSetupData"]["Frequency"] = f"{frequency}Hz"
            props["CoefficientSetupData"]["Thickness"] = thickness
            props["CoefficientSetupData"]["Conductivity"] = str(conductivity)
            points = [i for p in points_at_frequency[frequency] for i in p]
            props["CoefficientSetupData"]["Coordinates"] = dict({"DimUnits": ["", ""], "Points": points})
        elif len(points_at_frequency) > 1:
            props["CoreLossMultiCurveData"] = {}
            props["CoreLossMultiCurveData"]["property_data"] = "coreloss_multi_curve_data"
            props["CoreLossMultiCurveData"]["coreloss_unit"] = coefficient_setup

            props["CoreLossMultiCurveData"]["AllCurves"] = {}
            props["CoreLossMultiCurveData"]["AllCurves"]["OneCurve"] = []
            for freq in points_at_frequency.keys():
                points = [i for p in points_at_frequency[freq] for i in p]
                one_curve = dict(
                    {
                        "Frequency": f"{freq}Hz",
                        "Coordinates": dict({"DimUnits": ["", ""], "Points": points}),
                    }
                )
                props["CoreLossMultiCurveData"]["AllCurves"]["OneCurve"].append(one_curve)

        props = self._get_args(props)
        props.pop(0)
        if len(points_at_frequency) == 1:
            props[0][-1][2] = "NAME:Points"
            points = props[0][-1].pop(2)
            props[0][-1][2].insert(0, points)
        else:
            for p in props[0][-1]:
                if isinstance(p, list):
                    p[3].pop(2)
                    p[3][2].insert(0, "NAME:Points")
        coefficients = self.odefinition_manager.ComputeCoreLossCoefficients(
            core_loss_model_type, self.mass_density.evaluated_value, props[0]
        )
        return list(coefficients)

    @pyaedt_function_handler(points_list_at_freq="points_at_frequency")
    def set_coreloss_at_frequency(
        self,
        points_at_frequency,
        kdc=0,
        cut_depth="1mm",
        thickness="0.5mm",
        conductivity=0,
        coefficient_setup="w_per_cubic_meter",
        core_loss_model_type="Electrical Steel",
    ):
        """Set electrical steel or power ferrite core loss model at one single frequency or at multiple frequencies.

        Parameters
        ----------
        points_at_frequency : dict
            Dictionary where keys are the frequencies (in Hz) and values are lists of points (BP curve).
            If the core loss model is calculated at one frequency, this parameter must be provided as a
            dictionary with one key (single frequency in Hz) and values are lists of points at
            that specific frequency (BP curve).
        kdc : float
            Coefficient considering the DC flux bias effects
        cut_depth : str, optional
            Equivalent cut depth.
            You use this parameter to consider the manufacturing effects on core loss computation.
            The default value is ``"1mm"``.
        thickness : str, optional
            Thickness specified in terms of the value plus the unit.
            The default is ``"0.5mm"``.
        conductivity : float, optional
            Conductivity. The unit is S/m.
            The default is ``"0 S/m"``.
        coefficient_setup : str, optional
            Core loss unit. The default is ``"w_per_cubic_meter"``.
            Options are ``"kw_per_cubic_meter"``, ``"w_per_cubic_meter"``, ``"w_per_kg"``,
            and ``"w_per_lb"``.
        core_loss_model_type : str, optional
            Core loss model type. The default value is ``"Electrical Steel"``.
            Options are ``"Electrical Steel"`` and ``"Power Ferrite"``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDefinitionManager.EditMaterial

        Examples
        --------
        This example shows how to set a core loss model for a material in case material properties are calculated for
        core losses at one frequency or core losses versus frequencies (core losses multicurve data).
        The first case shows how to set properties for core losses at one frequency:

        >>> from ansys.aedt.core import Maxwell3d
        >>> m3d = Maxwell3d()
        >>> box = m3d.modeler.create_box([-10, -10, 0],[20, 20, 20],"box_to_split")
        >>> box.material = "magnesium"
        >>> m3d.materials["magnesium"].set_coreloss_at_frequency(
                                                    ... points_at_frequency={60 : [[0,0], [1,3.5], [2,7.4]]}
                                                    ... )
        >>> m3d.release_desktop(True, True)

        The second case shows how to set properties for core losses versus frequencies:

        >>> from ansys.aedt.core import Maxwell3d
        >>> m3d = Maxwell3d()
        >>> box = m3d.modeler.create_box([-10, -10, 0],[20, 20, 20],"box_to_split")
        >>> box.material = "magnesium"
        >>> m3d.materials["magnesium"].set_coreloss_at_frequency(
                                                    ... points_at_frequency={60 : [[0,0], [1,3.5], [2,7.4]],
                                                    ...                      100 : [[0,0], [1,8], [2,9]],
                                                    ...                      150 : [[0,0], [1,10], [2,19]]}
                                                    ... )
        >>> m3d.release_desktop(True, True)

        """
        if not isinstance(points_at_frequency, dict):
            raise TypeError("Points list at frequency must be provided as a dictionary.")
        if len(points_at_frequency) <= 1 and core_loss_model_type == "Power Ferrite":
            raise ValueError("At least 2 frequencies must be included.")
        freq_keys = list(points_at_frequency.keys())
        for i in range(0, len(freq_keys)):
            if isinstance(freq_keys[i], str):
                value, unit = decompose_variable_value(freq_keys[i])
                if unit != "Hz":
                    value = unit_converter(values=value, unit_system="Freq", input_units=unit, output_units="Hz")
                points_at_frequency[value] = points_at_frequency[freq_keys[i]]
                del points_at_frequency[freq_keys[i]]
        if "core_loss_type" not in self._props:
            choice = "Electrical Steel" if core_loss_model_type == "Electrical Steel" else "Power Ferrite"
            self._props["core_loss_type"] = dict({"property_type": "ChoiceProperty", "Choice": choice})
        else:
            self._props.pop("core_loss_cm", None)
            self._props.pop("core_loss_x", None)
            self._props.pop("core_loss_y", None)
            self._props.pop("core_loss_hci", None)
            self._props.pop("core_loss_br", None)
            self._props.pop("core_loss_hkc", None)
            self._props.pop("core_loss_curves", None)
            self._props["core_loss_type"]["Choice"] = core_loss_model_type
        if len(points_at_frequency) == 1:
            self._props["AttachedData"]["CoefficientSetupData"] = {}
            self._props["AttachedData"]["CoefficientSetupData"]["property_data"] = "coreloss_data"
            self._props["AttachedData"]["CoefficientSetupData"]["coefficient_setup"] = coefficient_setup
            frequency = list(points_at_frequency.keys())[0]
            self._props["AttachedData"]["CoefficientSetupData"]["Frequency"] = f"{frequency}Hz"
            self._props["AttachedData"]["CoefficientSetupData"]["Thickness"] = thickness
            self._props["AttachedData"]["CoefficientSetupData"]["Conductivity"] = str(conductivity)
            points = [i for p in points_at_frequency[frequency] for i in p]
            self._props["AttachedData"]["CoefficientSetupData"]["Coordinates"] = dict(
                {"DimUnits": ["", ""], "Points": points}
            )
        elif len(points_at_frequency) > 1:
            self._props["AttachedData"]["CoreLossMultiCurveData"] = {}
            self._props["AttachedData"]["CoreLossMultiCurveData"]["property_data"] = "coreloss_multi_curve_data"
            self._props["AttachedData"]["CoreLossMultiCurveData"]["coreloss_unit"] = coefficient_setup

            self._props["AttachedData"]["CoreLossMultiCurveData"]["AllCurves"] = {}
            self._props["AttachedData"]["CoreLossMultiCurveData"]["AllCurves"]["OneCurve"] = []
            for freq in points_at_frequency.keys():
                points = [i for p in points_at_frequency[freq] for i in p]
                one_curve = dict(
                    {
                        "Frequency": f"{freq}Hz",
                        "Coordinates": dict({"DimUnits": ["", ""], "Points": points}),
                    }
                )
                self._props["AttachedData"]["CoreLossMultiCurveData"]["AllCurves"]["OneCurve"].append(one_curve)

        coefficients = self.get_core_loss_coefficients(
            points_at_frequency, thickness=thickness, conductivity=conductivity
        )
        if core_loss_model_type == "Electrical Steel":
            self._props["core_loss_kh"] = str(coefficients[0])
            self._props["core_loss_kc"] = str(coefficients[1])
            self._props["core_loss_ke"] = str(coefficients[2])
        else:
            self._props["core_loss_cm"] = str(coefficients[0])
            self._props["core_loss_x"] = str(coefficients[1])
            self._props["core_loss_y"] = str(coefficients[2])
        self._props["core_loss_kdc"] = str(kdc)
        self._props["core_loss_equiv_cut_depth"] = cut_depth
        return self.update()

    @pyaedt_function_handler()
    def set_electrical_steel_coreloss(self, kh=0, kc=0, ke=0, kdc=0, cut_depth="1mm"):
        """Set electrical steel core loss.

        Parameters
        ----------
        kh : float, optional
            Hysteresis core loss coefficient.
            The default is ``0``.
        kc : float, optional
            Eddy-current core loss coefficient.
            The default is ``0``.
        ke : float, optional
            Excess core loss coefficient.
            The default is ``0``.
        kdc : float, optional
            Coefficient considering the DC flux bias effects.
            The default is ``0``.
        cut_depth : str, optional
            Equivalent cut depth considering manufacturing effects on core loss computation.
            The default value is ``"1mm"``.

        Returns
        -------
        bool
        """
        if "core_loss_type" not in self._props:
            self._props["core_loss_type"] = dict({"property_type": "ChoiceProperty", "Choice": "Electrical Steel"})
        else:
            self._props.pop("core_loss_cm", None)
            self._props.pop("core_loss_x", None)
            self._props.pop("core_loss_y", None)
            self._props.pop("core_loss_hci", None)
            self._props.pop("core_loss_br", None)
            self._props.pop("core_loss_hkc", None)
            self._props.pop("core_loss_curves", None)
            self._props["core_loss_type"]["Choice"] = "Electrical Steel"
        self._props["core_loss_kh"] = str(kh)
        self._props["core_loss_kc"] = str(kc)
        self._props["core_loss_ke"] = str(ke)
        self._props["core_loss_kdc"] = str(kdc)
        self._props["core_loss_equiv_cut_depth"] = cut_depth
        return self.update()

    @pyaedt_function_handler()
    def set_hysteresis_coreloss(self, kdc=0, hci=0, br=0, hkc=0, cut_depth=0.0001):
        """Set Hysteresis Type Core Loss.

        Parameters
        ----------
        kdc : float
        hci : float
        br : float
        hkc : float
        cut_depth : float

        Returns
        -------
        bool
        """
        if "core_loss_type" not in self._props:
            self._props["core_loss_type"] = dict({"property_type": "ChoiceProperty", "Choice": "Hysteresis Model"})
        else:
            self._props.pop("core_loss_kh", None)
            self._props.pop("core_loss_kc", None)
            self._props.pop("core_loss_ke", None)
            self._props.pop("core_loss_cm", None)
            self._props.pop("core_loss_x", None)
            self._props.pop("core_loss_y", None)
            self._props.pop("core_loss_hci", None)
            self._props.pop("core_loss_br", None)
            self._props.pop("core_loss_hkc", None)
            self._props.pop("core_loss_curves", None)
            self._props["core_loss_type"]["Choice"] = "Hysteresis Model"
        self._props["core_loss_hci"] = f"{hci}A_per_meter"
        self._props["core_loss_br"] = f"{br}tesla"
        self._props["core_loss_hkc"] = str(hkc)
        self._props["core_loss_kdc"] = str(kdc)
        self._props["core_loss_equiv_cut_depth"] = f"{cut_depth}meter"
        return self.update()

    @pyaedt_function_handler()
    def set_power_ferrite_coreloss(self, cm=0, x=0, y=0, kdc=0, cut_depth=0.0001):
        """Set Power Ferrite Type Core Loss.

        Parameters
        ----------
        cm : float
        x : float
        y : float
        kdc : float
        cut_depth : float

        Returns
        -------
        bool
        """
        if "core_loss_type" not in self._props:
            self._props["core_loss_type"] = dict({"property_type": "ChoiceProperty", "Choice": "Power Ferrite"})
        else:
            self._props.pop("core_loss_kh", None)
            self._props.pop("core_loss_kc", None)
            self._props.pop("core_loss_ke", None)
            self._props.pop("core_loss_cm", None)
            self._props.pop("core_loss_x", None)
            self._props.pop("core_loss_y", None)
            self._props.pop("core_loss_hci", None)
            self._props.pop("core_loss_br", None)
            self._props.pop("core_loss_hkc", None)
            self._props.pop("core_loss_curves", None)
            self._props["core_loss_type"]["Choice"] = "Power Ferrite"
        self._props["core_loss_cm"] = f"{cm}A_per_meter"
        self._props["core_loss_x"] = f"{x}tesla"
        self._props["core_loss_y"] = str(y)
        self._props["core_loss_kdc"] = str(kdc)
        self._props["core_loss_equiv_cut_depth"] = f"{cut_depth}meter"
        return self.update()

    @pyaedt_function_handler(point_list="points", punit="units")
    def set_bp_curve_coreloss(
        self, points, kdc=0, cut_depth=0.0001, units="kw/m^3", bunit="tesla", frequency=60, thickness="0.5mm"
    ):
        """Set B-P Type Core Loss.

        Parameters
        ----------
        points : list of list
            List of [x,y] points.
        kdc : float
        cut_depth : float
        units : str
            Core loss unit. The default is ``"kw/m^3"``.
        bunit : str
            Magnetic field unit. The default is ``"tesla"``.
        frequency : float
        thickness : str, optional
            Lamination thickness. The default is ``"0.5mm"``.

        Returns
        -------
        bool
        """
        if "core_loss_type" not in self._props:
            self._props["core_loss_type"] = dict({"property_type": "ChoiceProperty", "Choice": "B-P Curve"})
        else:
            self._props.pop("core_loss_kh", None)
            self._props.pop("core_loss_kc", None)
            self._props.pop("core_loss_ke", None)
            self._props.pop("core_loss_cm", None)
            self._props.pop("core_loss_x", None)
            self._props.pop("core_loss_y", None)
            self._props.pop("core_loss_hci", None)
            self._props.pop("core_loss_br", None)
            self._props.pop("core_loss_hkc", None)
            self._props.pop("core_loss_curves", None)
            self._props["core_loss_type"]["Choice"] = "B-P Curve"
        self._props["core_loss_kdc"] = str(kdc)
        self._props["core_loss_equiv_cut_depth"] = f"{cut_depth}meter"
        self._props["core_loss_curves"] = {}
        self._props["core_loss_curves"]["property_type"] = "nonlinear"
        self._props["core_loss_curves"]["PUnit"] = units
        self._props["core_loss_curves"]["BUnit"] = bunit
        self._props["core_loss_curves"]["Frequency"] = f"{frequency}Hz"
        self._props["core_loss_curves"]["Thickness"] = thickness
        self._props["core_loss_curves"]["IsTemperatureDependent"] = False

        self._props["core_loss_curves"]["BPCoordinates"] = {}
        self._props["core_loss_curves"]["BPCoordinates"]["Point"] = []
        for points in points:
            self._props["core_loss_curves"]["BPCoordinates"]["Point"].append(points)
        return self.update()

    @pyaedt_function_handler()
    def get_curve_coreloss_type(self):
        """Return the curve core loss type assigned to material.

        Returns
        -------
        str
        """
        if self._props.get("core_loss_type", None):
            return self._props["core_loss_type"].get("Choice", None)
        return None

    @pyaedt_function_handler()
    def get_curve_coreloss_values(self):
        """Return the curve core values type assigned to material.

        Returns
        -------
        dict
        """
        out = {}
        if self._props.get("core_loss_type", None):
            if self._props["core_loss_type"].get("Choice", None) == "Electrical Steel":
                out["core_loss_kh"] = self._props["core_loss_kh"]
                out["core_loss_kc"] = self._props["core_loss_kc"]
                out["core_loss_ke"] = self._props["core_loss_ke"]
                out["core_loss_kdc"] = self._props["core_loss_kdc"]
                out["core_loss_equiv_cut_depth"] = self._props["core_loss_equiv_cut_depth"]
            elif self._props["core_loss_type"].get("Choice", None) == "B-P Curve":
                out["core_loss_curves"] = self._props["core_loss_curves"]
                out["core_loss_kdc"] = self._props["core_loss_kdc"]
                out["core_loss_equiv_cut_depth"] = self._props["core_loss_equiv_cut_depth"]
            if self._props["core_loss_type"].get("Choice", None) == "Power Ferrite":
                out["core_loss_cm"] = self._props["core_loss_cm"]
                out["core_loss_x"] = self._props["core_loss_x"]
                out["core_loss_y"] = self._props["core_loss_y"]
                out["core_loss_kdc"] = self._props["core_loss_kdc"]
                out["core_loss_equiv_cut_depth"] = self._props["core_loss_equiv_cut_depth"]
            elif self._props["core_loss_type"].get("Choice", None) == "Hysteresis Model":
                out["core_loss_hci"] = self._props["core_loss_hci"]
                out["core_loss_br"] = self._props["core_loss_br"]
                out["core_loss_hkc"] = self._props["core_loss_hkc"]
                out["core_loss_kdc"] = self._props["core_loss_kdc"]
                out["core_loss_equiv_cut_depth"] = self._props["core_loss_equiv_cut_depth"]
        return out

    @pyaedt_function_handler()
    def get_magnetic_coercivity(self):
        """Get the magnetic coercivity values.

        Returns
        -------
        tuple
            Tuple of (Magnitude, x, y, z).
        """
        if "magnetic_coercivity" in self._props:
            return (
                self._props["magnetic_coercivity"]["Magnitude"],
                self._props["magnetic_coercivity"]["DirComp1"],
                self._props["magnetic_coercivity"]["DirComp2"],
                self._props["magnetic_coercivity"]["DirComp3"],
            )
        return False

    @pyaedt_function_handler()
    def get_magnetic_coercitivity(self):  # pragma: no cover
        """Get the magnetic coercivity values.

        .. deprecated:: 0.7.0

        Returns
        -------
        bool

        """
        warnings.warn(
            "`get_magnetic_coercitivity` is deprecated. Use `get_magnetic_coercivity` instead.", DeprecationWarning
        )
        return self.get_magnetic_coercivity()

    @pyaedt_function_handler()
    def is_conductor(self, threshold=100000):
        """Check if the material is a conductor.

        Parameters
        ----------
        threshold : float, optional
            Threshold to define if a material is a conductor. The
            default is ``100000``. If the conductivity is equal to or
            greater than the threshold, the material is
            considered a conductor.

        Returns
        -------
        bool
            ``True`` when the material is a conductor, ``False`` otherwise.

        """
        cond = self.conductivity.evaluated_value
        if not cond:
            return False
        if "Freq" in str(cond):
            return True
        try:
            if float(cond) >= threshold:
                return True
        except Exception:
            return False
        return False

    @pyaedt_function_handler()
    def is_dielectric(self, threshold=100000):
        """Check if the material is dielectric.

        Parameters
        ----------
        threshold : float, optional
            Threshold to define if a material is dielectric. The
            default is ``100000``. If the conductivity is equal to or
            greater than the threshold, the material is
            considered dielectric.

        Returns
        -------
        bool
            ``True`` when the material is dielectric, ``False`` otherwise.
        """
        return not self.is_conductor(threshold)

    @pyaedt_function_handler(i_freq="frequency")
    def set_djordjevic_sarkar_model(
        self,
        dk=4,
        df=0.02,
        frequency=1e9,
        sigma_dc=1e-12,
        freq_hi=159.15494e9,
    ):
        """Set Djordjevic-Sarkar model.

        Parameters
        ----------
        dk : int, float, str, optional
            Dielectric constant at input frequency.
        df : int, float, str, optional
            Loss tangent at input frequency.
        frequency : int, float, optional.
            Input frequency in Hz.
        sigma_dc : int, float, optional
            Conductivity at DC. The default is ``1e-12``.
        freq_hi : int, float, optional
            High-frequency corner in Hz. The default is ``159.15494e9``.

        Returns
        -------
        bool
            ``True`` if successful, ``False`` otherwise.
        """
        # K = f"({dk} * {df} - {sigma_dc} / (2 * pi * {i_freq} * e0)) / atan({freq_hi} / {i_freq})"
        K = f"({dk} * {df} - {sigma_dc} / (2 * pi * {frequency} * e0)) / atan({freq_hi} / {frequency})"
        epsilon_inf = f"({dk} - {K} / 2 * ln({freq_hi}**2 / {frequency}**2 + 1))"
        freq_low = f"({freq_hi} / exp(10 * {df} * {epsilon_inf} / ({K})))"
        ds_er = f"{epsilon_inf} + {K} / 2 * ln(({freq_hi}**2 + Freq**2) / ({freq_low}**2 + Freq**2))"
        cond = f"{sigma_dc} + 2 * pi * Freq * e0 * ({K}) * (atan(Freq / ({freq_low})) - atan(Freq / {freq_hi}))"
        # ds_tande = "{} / (e0 * {} * 2 * pi * Freq)".format(cond, ds_er)

        self.conductivity = cond
        self.permittivity = ds_er

        return self.update()

    @pyaedt_function_handler()
    def update(self):
        """Update the material in AEDT.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDefinitionManager.AddMaterial
        >>> oDefinitionManager.EditMaterial
        """
        args = self._get_args()
        if not self._does_material_exists(self.name):
            self.odefinition_manager.AddMaterial(args)
        elif not self.is_sweep_material:
            self.odefinition_manager.EditMaterial(self.name, args)
        return True

    @pyaedt_function_handler()
    def _does_material_exists(self, material_name):
        listmatprj = [i.lower() for i in list(self.odefinition_manager.GetProjectMaterialNames())]
        if material_name.lower() in listmatprj:
            return True
        else:
            return False


class SurfaceMaterial(CommonMaterial, object):
    """Manages surface material properties for Icepak only.

    Parameters
    ----------
    materiallib : :class:`ansys.aedt.core.modules.material_lib.Materials`
        Inherited parent object.
    name : str
        Name of the surface material
    props :
        The default is ``None``.
    material_update : bool, optional
        The default is ``True``.
    """

    def __init__(self, materiallib, name, props=None, material_update=True):
        CommonMaterial.__init__(self, materiallib, name, props)
        self.surface_clarity_type = "Opaque"
        self._material_update = material_update
        if "surface_clarity_type" in self._props:
            self.surface_clarity_type = self._props["surface_clarity_type"]["Choice"]
        if "PhysicsTypes" in self._props:
            self.physics_type = self._props["PhysicsTypes"]["set"]
        else:
            self.physics_type = ["Thermal"]
            self._props["PhysicsTypes"] = dict({"set": ["Thermal"]})
        for property in SurfMatProperties.aedtname:
            if property in self._props:
                mods = None
                if "ModifierData" in self._props:
                    modifiers = self._props["ModifierData"]["ThermalModifierData"]["all_thermal_modifiers"]
                    for mod in modifiers:
                        if isinstance(modifiers[mod], list):
                            for one_tm in modifiers[mod]:
                                if one_tm["Property:"] == property:
                                    if mods:
                                        mods = [mods]
                                        mods.append(one_tm)
                                    else:
                                        mods = one_tm
                        else:
                            if modifiers[mod]["Property:"] == property:
                                mods = modifiers[mod]
                self.__dict__["_" + property] = MatProperty(self, property, self._props[property], mods)
            else:
                self.__dict__["_" + property] = MatProperty(
                    self, property, SurfMatProperties.get_defaultvalue(aedtname=property)
                )

    @property
    def emissivity(self):
        """Emissivity.

        Returns
        -------
        :class:`ansys.aedt.core.modules.material.MatProperty`
            Emissivity of the surface material.

        References
        ----------
        >>> oDefinitionManager.EditSurfaceMaterial
        """
        return self._surface_emissivity

    @emissivity.setter
    def emissivity(self, value):
        self._surface_emissivity.value = value
        if self._material_update:
            self._update_props("surface_emissivity", value)

    @property
    def surface_diffuse_absorptance(self):
        """Surface diffuse absorptance.

        Returns
        -------
        :class:`ansys.aedt.core.modules.material.MatProperty`
            Surface diffuse absorptance of the surface material.

        References
        ----------
        >>> oDefinitionManager.EditSurfaceMaterial
        """
        return self._surface_diffuse_absorptance

    @surface_diffuse_absorptance.setter
    def surface_diffuse_absorptance(self, value):
        self._surface_diffuse_absorptance.value = value
        if self._material_update:
            self._update_props("surface_diffuse_absorptance", value)

    @property
    def surface_incident_absorptance(self):
        """Surface incident absorptance.

        Returns
        -------
        :class:`ansys.aedt.core.modules.material.MatProperty`
            Surface incident absorptance of the surface material.

        References
        ----------
        >>> oDefinitionManager.EditSurfaceMaterial
        """
        return self._surface_incident_absorptance

    @surface_incident_absorptance.setter
    def surface_incident_absorptance(self, value):
        self._surface_incident_absorptance.value = value
        if self._material_update:
            self._update_props("surface_incident_absorptance", value)

    @property
    def surface_roughness(self):
        """Surface roughness.

        Returns
        -------
        :class:`ansys.aedt.core.modules.material.MatProperty`
            Surface roughness of the surface material.

        References
        ----------
        >>> oDefinitionManager.EditSurfaceMaterial
        """
        return self._surface_roughness

    @surface_roughness.setter
    def surface_roughness(self, value):
        self._surface_roughness.value = value
        if self._material_update:
            self._update_props("surface_roughness", value)

    @pyaedt_function_handler()
    def update(self):
        """Update the surface material in AEDT.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------
        >>> oDefinitionManager.DoesSurfaceMaterialExist
        >>> oDefinitionManager.AddSurfaceMaterial
        >>> oDefinitionManager.EditSurfaceMaterial
        """
        args = self._get_args()
        if self._does_material_exists(self.name):
            self.odefinition_manager.EditSurfaceMaterial(self.name, args)
        else:
            self.odefinition_manager.AddSurfaceMaterial(args)
        return True

    @pyaedt_function_handler()
    def _does_material_exists(self, szMat):
        a = self.odefinition_manager.DoesSurfaceMaterialExist(szMat)
        if a != 0:
            return True
        return False
