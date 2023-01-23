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
from collections import OrderedDict

from pyaedt.generic.constants import CSS4_COLORS
from pyaedt.generic.DataHandlers import _dict2arg
from pyaedt.generic.general_methods import pyaedt_function_handler


class MatProperties(object):
    """Contains a list of constant names for all materials with
    mappings to their internal XML names.

    Internal names are used in scripts, and XML names are used in the XML syntax.
    """

    aedtname = [
        "permittivity",
        "permeability",
        "conductivity",
        "dielectric_loss_tangent",
        "magnetic_loss_tangent",
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
    defaultvalue = [1.0, 1.0, 0, 0, 0, 0.01, 0, 0, 0, 0, 0, 0.8, 0, 0, 0, 0, 0, 0]
    defaultunit = [
        None,
        None,
        "[siemens m^-1]",
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
    """Contains a list of constant names for all surface materials with
    mappings to their internal XML names.

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
    """Manges closed-form thermal modifiers."""

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

    value = None
    dataset = None
    thermalmodifier = None
    spatialmodifier = None


class MatProperty(object):
    """Manages simple, anisotropic, tensor, and non-linear properties.

    Parameters
    ----------
    material : :class:`pyaedt.modules.Material.Material`
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
    >>> from pyaedt import Hfss
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
        elif val is not None and val["property_type"] == "AnisoProperty":
            self.type = "anisotropic"
            self.value = [val["component1"], val["component2"], val["component3"]]
        elif val is not None and val["property_type"] == "nonlinear":
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
                    self.value = v["Point"]
                    self._unit = v["DimUnits"]
                elif e == "Temperatures":
                    self.temperatures = v
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
            Type of properties. Options are ``simple"``,
            ``"anisotropic",`` ``"tensor"``, and ``"nonlinear",``
        """
        return self._type

    @type.setter
    def type(self, type):
        self._type = type
        if self._type == "simple":
            self._property_value = [self._property_value[0]]
        elif self._type == "anisotropic":
            self._property_value = [self._property_value[0] for i in range(3)]
        elif self._type == "tensor":
            self._property_value = [self._property_value[0] for i in range(9)]
        elif self._type == "nonlinear":
            self._property_value = [self._property_value[0]]

    @property
    def value(self):
        """Value for a material property."""
        if len(self._property_value) == 1:
            return self._property_value[0].value
        else:
            return [i.value for i in self._property_value]

    @value.setter
    def value(self, val):
        if self.type == "nonlinear":
            self._property_value[0].value = val
        elif isinstance(val, list):
            i = 0
            for el in val:
                if i >= len(self._property_value):
                    self._property_value.append(BasicValue())

                self._property_value[i].value = el
                i += 1
        else:
            self._property_value[0].value = val

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
        if isinstance(thermal_value, str):
            self._add_thermal_modifier(thermal_value, 0)
        else:
            for i in thermal_value:
                self._add_thermal_modifier(i, thermal_value.index(i))

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
        ):
            tm = OrderedDict(
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
                self._material._props["ModifierData"] = OrderedDict(
                    {
                        "SpatialModifierData": self._material._props["ModifierData"]["SpatialModifierData"],
                        "ThermalModifierData": OrderedDict(
                            {
                                "modifier_data": "thermal_modifier_data",
                                "all_thermal_modifiers": OrderedDict({"one_spatial_modifier": tm}),
                            }
                        ),
                    }
                )
            else:
                self._material._props["ModifierData"] = OrderedDict(
                    {
                        "ThermalModifierData": OrderedDict(
                            {
                                "modifier_data": "thermal_modifier_data",
                                "all_thermal_modifiers": OrderedDict({"one_thermal_modifier": tm}),
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
                        tm = OrderedDict(
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
                    tm = OrderedDict(
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

        >>> from pyaedt import Hfss
        >>> hfss = Hfss(specified_version="2021.2")
        >>> mat1 = hfss.materials.add_material("new_copper2")
        >>> mat1.add_thermal_modifier_free_form("if(Temp > 1000cel, 1, if(Temp < -273.15cel, 1, 1))")
        """
        self._property_value[index].thermalmodifier = formula
        return self._add_thermal_modifier(formula, index)

    @pyaedt_function_handler()
    def add_thermal_modifier_dataset(self, dataset_name, index=0):
        """Add a thermal modifier to a material property using an existing dataset.

        Parameters
        ----------
        dataset_name : str
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

        >>> from pyaedt import Hfss
        >>> hfss = Hfss(specified_version="2021.2")
        >>> mat1 = hfss.materials.add_material("new_copper2")
        >>> mat1.add_thermal_modifier_dataset("$ds1")
        """

        formula = "pwl({}, Temp)".format(dataset_name)
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

        >>> from pyaedt import Hfss
        >>> hfss = Hfss(specified_version="2021.2")
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
            tm_new = OrderedDict(
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
            tm_new = OrderedDict(
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
        ):
            if (
                "ModifierData" in self._material._props
                and "SpatialModifierData" in self._material._props["ModifierData"]
            ):
                self._material._props["ModifierData"] = OrderedDict(
                    {
                        "SpatialModifierData": self._material._props["ModifierData"]["SpatialModifierData"],
                        "ThermalModifierData": OrderedDict(
                            {
                                "modifier_data": "thermal_modifier_data",
                                "all_thermal_modifiers": OrderedDict({"one_spatial_modifier": tm_new}),
                            }
                        ),
                    }
                )
            else:
                self._material._props["ModifierData"] = OrderedDict(
                    {
                        "ThermalModifierData": OrderedDict(
                            {
                                "modifier_data": "thermal_modifier_data",
                                "all_thermal_modifiers": OrderedDict({"one_thermal_modifier": tm_new}),
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
            self._material._props["ModifierData"] = OrderedDict(
                {
                    "ThermalModifierData": OrderedDict(
                        {
                            "modifier_data": "thermal_modifier_data",
                            "all_thermal_modifiers": OrderedDict({"one_thermal_modifier": tm_definition}),
                        }
                    )
                }
            )
        return self._material.update()

    @pyaedt_function_handler()
    def set_non_linear(self, point_list, x_unit=None, y_unit=None):
        """Enable Non Linear Material.

        Parameters
        ----------
        point_list : list of list
            list of [x,y] nonlinear couple of points.
        x_unit : str, optional
            X units. Defaults will be used if `None`.
        y_unit : str, optional
            Y units. Defaults will be used if `None`.

        Returns
        -------
        bool
            `True` if succeeded.
        """
        if self.name not in ["permeability", "conductivity", "permittivity"]:
            self.logger.error(
                "Non linear parameters are only supported for permeability, conductivity and permittivity."
            )
            return False
        self.type = "nonlinear"
        self.value = point_list
        if self.name == "permeability":
            if not x_unit:
                x_unit = "tesla"
            if not y_unit:
                y_unit = "A_per_meter"
            self.bunit = x_unit
            self.hunit = y_unit
            self.is_temperature_dependent = False
            self.btype_for_single_curve = "normal"
            self.temperatures = OrderedDict({})
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
        return self._material._update_props(self.name, self.value)

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
        if isinstance(spatial_value, str):
            self._add_spatial_modifier(spatial_value, 0)
        else:
            for i in spatial_value:
                self._add_spatial_modifier(i, spatial_value.index(i))

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
        ):
            sm = OrderedDict(
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
                self._material._props["ModifierData"] = OrderedDict(
                    {
                        "ThermalModifierData": self._material._props["ModifierData"]["ThermalModifierData"],
                        "SpatialModifierData": OrderedDict(
                            {
                                "modifier_data": "spatial_modifier_data",
                                "all_spatial_modifiers": OrderedDict({"one_spatial_modifier": sm}),
                            }
                        ),
                    }
                )
            else:
                self._material._props["ModifierData"] = OrderedDict(
                    {
                        "SpatialModifierData": OrderedDict(
                            {
                                "modifier_data": "spatial_modifier_data",
                                "all_spatial_modifiers": OrderedDict({"one_spatial_modifier": sm}),
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
                        sm = OrderedDict(
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
                    sm = OrderedDict(
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

        >>> from pyaedt import Hfss
        >>> hfss = Hfss(specified_version="2021.2")
        >>> mat1 = hfss.materials.add_material("new_copper2")
        >>> mat1.add_spatial_modifier_free_form("if(X > 1mm, 1, if(X < 1mm, 2, 1))")
        """
        self._property_value[index].spatialmodifier = formula
        return self._add_spatial_modifier(formula, index)

    @pyaedt_function_handler()
    def add_spatial_modifier_dataset(self, dataset_name, index=0):
        """Add a spatial modifier to a material property using an existing dataset.

        Parameters
        ----------
        dataset_name : str
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

        >>> from pyaedt import Hfss
        >>> hfss = Hfss(specified_version="2021.2")
        >>> mat1 = hfss.materials.add_material("new_copper2")
        >>> mat1.add_spatial_modifier_dataset("$ds1")
        """

        formula = "clp({}, X,Y,Z)".format(dataset_name)
        self._property_value[index].spatialmodifier = formula
        return self._add_spatial_modifier(formula, index)


class CommonMaterial(object):
    """Manages datasets with frequency-dependent materials.

    Parameters
    ----------
    materials : :class:`pyaedt.modules.MaterialLib.Materials`

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
        self.coordinate_system = ""
        self.is_sweep_material = False
        if props:
            self._props = props.copy()
        else:
            self._props = OrderedDict()
        if "CoordinateSystemType" in self._props:
            self.coordinate_system = self._props["CoordinateSystemType"]
        else:
            self._props["CoordinateSystemType"] = "Cartesian"
            self.coordinate_system = "Cartesian"
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

    @pyaedt_function_handler()
    def _get_args(self, props=None):
        """Retrieve the arguments for a property.

        Parameters
        ----------
        prop : str, optoinal
            Name of the property.  The default is ``None``.
        """
        if not props:
            props = self._props
        arg = ["NAME:" + self.name]
        _dict2arg(props, arg)
        return arg

    def _update_props(self, propname, provpavlue, update_aedt=True):
        """Update properties.

        Parameters
        ----------
        propname : str
            Name of the property.
        provpavlue :
            Value of the property.
        update_aedt : bool, optional
            Whether to update the property in AEDT. The default is ``True``.

        """
        if (
            isinstance(provpavlue, list)
            and self.__dict__["_" + propname].type != "simple"
            and self.__dict__["_" + propname].type != "nonlinear"
        ):
            i = 1
            for val in provpavlue:
                if not self._props.get(propname, None) or isinstance(self._props[propname], str):
                    self._props[propname] = OrderedDict({"property_type": "AnisoProperty"})
                    self._props[propname]["unit"] = ""
                self._props[propname]["component" + str(i)] = str(val)
                i += 1
            if update_aedt:
                return self.update()
        elif isinstance(provpavlue, (str, float, int)):
            self._props[propname] = str(provpavlue)
            if update_aedt:
                return self.update()
        elif isinstance(provpavlue, OrderedDict):
            self._props[propname] = provpavlue
            if update_aedt:
                return self.update()
        elif isinstance(provpavlue, list) and self.__dict__["_" + propname].type == "nonlinear":
            if propname == "permeability":
                bh = OrderedDict({"DimUnits": ["", ""]})
                for point in provpavlue:
                    if "Point" in bh:
                        bh["Point"].append(point)
                    else:
                        bh["Point"] = [point]
                self._props[propname] = OrderedDict({"property_type": "nonlinear"})
                self._props[propname]["BTypeForSingleCurve"] = self.__dict__["_" + propname].btype_for_single_curve
                self._props[propname]["HUnit"] = self.__dict__["_" + propname].hunit
                self._props[propname]["BUnit"] = self.__dict__["_" + propname].bunit
                self._props[propname]["IsTemperatureDependent"] = self.__dict__["_" + propname].is_temperature_dependent
                self._props[propname]["BHCoordinates"] = bh
                try:
                    self._props[propname]["BHCoordinates"]["Temperatures"] = self.__dict__["_" + propname].temperatures
                except:
                    self._props[propname]["BHCoordinates"]["Temperatures"] = OrderedDict({})
            else:
                bh = OrderedDict({"DimUnits": [self.__dict__["_" + propname]._unit]})
                for point in provpavlue:
                    if "Point" in bh:
                        bh["Point"].append(point)
                    else:
                        bh["Point"] = [point]
                if propname == "conductivity":
                    pr_name = "JECoordinates"
                else:
                    pr_name = "DECoordinates"
                self._props[propname] = OrderedDict({"property_type": "nonlinear", pr_name: bh})
            if update_aedt:
                return self.update()
        return False


class Material(CommonMaterial, object):
    """Manages material properties.

    Parameters
    ----------
    materiallib : :class:`pyaedt.modules.MaterialLib.Materials`
        Inherited parent object.
    name : str
        Name of the material.
    props  :
        The default is ``None``.

    Examples
    --------
    >>> from pyaedt import Hfss
    >>> app = Hfss()
    >>> material = app.materials["copper"]
    """

    def __init__(self, materiallib, name, props=None):
        CommonMaterial.__init__(self, materiallib, name, props)
        self.thermal_material_type = "Solid"
        if "thermal_material_type" in self._props:
            self.thermal_material_type = self._props["thermal_material_type"]["Choice"]
        if "PhysicsTypes" in self._props:
            self.physics_type = self._props["PhysicsTypes"]["set"]
        else:
            self.physics_type = ["Electromagnetic", "Thermal", "Structural"]
            self._props["PhysicsTypes"] = OrderedDict({"set": ["Electromagnetic", "Thermal", "Structural"]})
        if "AttachedData" in self._props and "MatAppearanceData" in self._props["AttachedData"]:
            self._material_appearance = []
            self._material_appearance.append(self._props["AttachedData"]["MatAppearanceData"]["Red"])
            self._material_appearance.append(self._props["AttachedData"]["MatAppearanceData"]["Green"])
            self._material_appearance.append(self._props["AttachedData"]["MatAppearanceData"]["Blue"])
        else:
            vals = list(CSS4_COLORS.values())
            if (materiallib._color_id) > len(vals):
                materiallib._color_id = 0
            h = vals[materiallib._color_id].lstrip("#")
            self._material_appearance = list(int(h[i : i + 2], 16) for i in (0, 2, 4))
            materiallib._color_id += 1
            self._props["AttachedData"] = OrderedDict(
                {
                    "MatAppearanceData": OrderedDict(
                        {
                            "property_data": "appearance_data",
                            "Red": self._material_appearance[0],
                            "Green": self._material_appearance[1],
                            "Blue": self._material_appearance[2],
                        }
                    )
                }
            )
        if "stacking_type" in self._props:
            self.stacking_type = self._props["stacking_type"]["Choice"]

        if "wire_type" in self._props:
            self.wire_type = self._props["wire_type"]["Choice"]

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
        pass

    @property
    def material_appearance(self):
        """Material Appearance specified as an RGB list.

        Returns
        -------
        list
            Color of the material in RGB.  Values are in the range ``[0, 255]``.

        Examples
        --------
        Create a new material with color ``[0, 153, 153]`` (darker cyan).

        >>> from pyaedt import Hfss
        >>> hfss = Hfss(specified_version="2021.2")
        >>> mat1 = hfss.materials.add_material("new_material")
        >>> rgbcolor = mat1.material_appearance
        >>> mat1.material_appearance = [0, 153, 153]
        """
        return self._material_appearance

    @material_appearance.setter
    def material_appearance(self, rgb):
        if not isinstance(rgb, (list, tuple)):
            raise TypeError("`material_apperance` must be a list or tuple")
        if len(rgb) != 3:
            raise ValueError("`material_appearance` must be three items (RGB)")
        value_int = []
        for rgb_item in rgb:
            rgb_int = int(rgb_item)
            if rgb_int < 0 or rgb_int > 255:
                raise ValueError("RGB value must be between 0 and 255")
            value_int.append(rgb_int)
        self._material_appearance = value_int
        self._props["AttachedData"] = OrderedDict(
            {
                "MatAppearanceData": OrderedDict(
                    {
                        "property_data": "appearance_data",
                        "Red": value_int[0],
                        "Green": value_int[1],
                        "Blue": value_int[2],
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
        :class:`pyaedt.modules.Material.MatProperty`
            Permittivity of the material.

        References
        ----------

        >>> oDefinitionManager.EditMaterial
        """
        return self._permittivity

    @permittivity.setter
    def permittivity(self, value):
        if isinstance(value, list) and isinstance(value[0], list):
            self._permittivity.set_non_linear(value)
        elif isinstance(value, list):
            self._permittivity.value = value
            self._permittivity.type = "anisotropic"
            self._update_props("permittivity", value)
        else:
            self._permittivity.value = value
            self._permittivity.type = "simple"
            self._update_props("permittivity", value)

    @property
    def permeability(self):
        """Permeability.

        Returns
        -------
        :class:`pyaedt.modules.Material.MatProperty`
            Permeability of the material.

        References
        ----------

        >>> oDefinitionManager.EditMaterial
        """
        return self._permeability

    @permeability.setter
    def permeability(self, value):
        if isinstance(value, list) and isinstance(value[0], list):
            self._permeability.set_non_linear(value)
        elif isinstance(value, list):
            self._permeability.value = value
            self._permeability.type = "anisotropic"
            self._update_props("permeability", value)
        else:
            self._permeability.value = value
            self._permeability.type = "simple"
            self._update_props("permeability", value)

    @property
    def conductivity(self):
        """Conductivity.

        Returns
        -------
        :class:`pyaedt.modules.Material.MatProperty`
            Conductivity of the material.

        References
        ----------

        >>> oDefinitionManager.EditMaterial
        """
        return self._conductivity

    @conductivity.setter
    def conductivity(self, value):
        if isinstance(value, list) and isinstance(value[0], list):
            self._conductivity.set_non_linear(value)
        elif isinstance(value, list):
            self._conductivity.value = value
            self._conductivity.type = "anisotropic"
            self._update_props("conductivity", value)
        else:
            self._conductivity.value = value
            self._conductivity.type = "simple"
            self._update_props("conductivity", value)

    @property
    def dielectric_loss_tangent(self):
        """Dielectric loss tangent.

        Returns
        -------
        :class:`pyaedt.modules.MatProperty`
            Dielectric loss tangent of the material.
        """
        return self._dielectric_loss_tangent

    @dielectric_loss_tangent.setter
    def dielectric_loss_tangent(self, value):
        self._dielectric_loss_tangent.value = value
        self._update_props("dielectric_loss_tangent", value)

    @property
    def magnetic_loss_tangent(self):
        """Magnetic loss tangent.

        Returns
        -------
        :class:`pyaedt.modules.Material.MatProperty`
            Magnetic loss tangent of the material.

        References
        ----------

        >>> oDefinitionManager.EditMaterial
        """
        return self._magnetic_loss_tangent

    @magnetic_loss_tangent.setter
    def magnetic_loss_tangent(self, value):
        self._magnetic_loss_tangent.value = value
        self._update_props("magnetic_loss_tangent", value)

    @property
    def thermal_conductivity(self):
        """Thermal conductivity.

        Returns
        -------
        :class:`pyaedt.modules.Material.MatProperty`
            Thermal conductivity of the material.

        References
        ----------

        >>> oDefinitionManager.EditMaterial
        """
        return self._thermal_conductivity

    @thermal_conductivity.setter
    def thermal_conductivity(self, value):
        self._thermal_conductivity.value = value
        self.physics_type = ["Electromagnetic", "Thermal", "Structural"]
        self._props["PhysicsTypes"] = OrderedDict({"set": ["Electromagnetic", "Thermal", "Structural"]})
        if isinstance(value, list):
            self._thermal_conductivity.type = "anisotropic"
            self._update_props("thermal_conductivity", value)
        else:
            self._thermal_conductivity.type = "simple"
            self._update_props("thermal_conductivity", value)

    @property
    def mass_density(self):
        """Mass density.

        Returns
        -------
        :class:`pyaedt.modules.Material.MatProperty`
            Mass density of the material.

        References
        ----------

        >>> oDefinitionManager.EditMaterial
        """
        return self._mass_density

    @mass_density.setter
    def mass_density(self, value):
        self._mass_density.value = value
        self._update_props("mass_density", value)

    @property
    def specific_heat(self):
        """Specific heat.

        Returns
        -------
        :class:`pyaedt.modules.Material.MatProperty`
            Specific heat of the material.

        References
        ----------

        >>> oDefinitionManager.EditMaterial
        """
        return self._specific_heat

    @specific_heat.setter
    def specific_heat(self, value):
        self._specific_heat.value = value
        self._update_props("specific_heat", value)

    @property
    def thermal_expansion_coefficient(self):
        """Thermal expansion coefficient.

        Returns
        -------
        :class:`pyaedt.modules.Material.MatProperty`
            Thermal expansion coefficient of the material.

        References
        ----------

        >>> oDefinitionManager.EditMaterial
        """
        return self._thermal_expansion_coefficient

    @thermal_expansion_coefficient.setter
    def thermal_expansion_coefficient(self, value):
        self._thermal_expansion_coefficient.value = value
        self._update_props("thermal_expansion_coefficient", value)

    @property
    def youngs_modulus(self):
        """Young's modulus.

        Returns
        -------
        :class:`pyaedt.modules.Material.MatProperty`
            Young's modulus of the material.

        References
        ----------

        >>> oDefinitionManager.EditMaterial
        """
        return self._youngs_modulus

    @youngs_modulus.setter
    def youngs_modulus(self, value):
        self._youngs_modulus.value = value
        self.physics_type = ["Electromagnetic", "Thermal", "Structural"]
        self._props["PhysicsTypes"] = OrderedDict({"set": ["Electromagnetic", "Thermal", "Structural"]})
        self._update_props("youngs_modulus", value)

    @property
    def poissons_ratio(self):
        """Poisson's ratio.

        Returns
        -------
        :class:`pyaedt.modules.Material.MatProperty`
            Poisson's ratio of the material.

        References
        ----------

        >>> oDefinitionManager.EditMaterial
        """
        return self._poissons_ratio

    @poissons_ratio.setter
    def poissons_ratio(self, value):
        self._poissons_ratio.value = value
        self.physics_type = ["Electromagnetic", "Thermal", "Structural"]
        self._props["PhysicsTypes"] = OrderedDict({"set": ["Electromagnetic", "Thermal", "Structural"]})
        self._update_props("poissons_ratio", value)

    @property
    def diffusivity(self):
        """Diffusivity.

        Returns
        -------
        :class:`pyaedt.modules.Material.MatProperty`
            Diffusivity of the material.

        References
        ----------

        >>> oDefinitionManager.EditMaterial
        """
        return self._diffusivity

    @diffusivity.setter
    def diffusivity(self, value):
        self._diffusivity.value = value
        self._update_props("diffusivity", value)

    @property
    def molecular_mass(self):
        """Molecular mass.

        Returns
        -------
        :class:`pyaedt.modules.Material.MatProperty`
            Molecular mass of the material.

        References
        ----------

        >>> oDefinitionManager.EditMaterial
        """
        return self._molecular_mass

    @molecular_mass.setter
    def molecular_mass(self, value):
        self._molecular_mass.value = value
        self._update_props("molecular_mass", value)

    @property
    def viscosity(self):
        """Viscosity.

        Returns
        -------
        :class:`pyaedt.modules.Material.MatProperty`
            Viscosity of the material.

        References
        ----------

        >>> oDefinitionManager.EditMaterial
        """
        return self._viscosity

    @viscosity.setter
    def viscosity(self, value):
        self._viscosity.value = value
        self._update_props("viscosity", value)

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
        self._update_props(
            "stacking_type",
            OrderedDict(
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
        self._update_props("wire_type", OrderedDict({"property_type": "ChoiceProperty", "Choice": value}))

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
        self._update_props(
            "wire_thickness_direction", OrderedDict({"property_type": "ChoiceProperty", "Choice": value})
        )

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
        self._update_props("wire_width_direction", OrderedDict({"property_type": "ChoiceProperty", "Choice": value}))

    @property
    def strand_number(self):
        """Strand number for litz wire.

        Returns
        -------
        :class:`pyaedt.modules.Material.MatProperty`
            Number of strands for the wire.

        References
        ----------

        >>> oDefinitionManager.EditMaterial
        """
        return self._strand_number

    @strand_number.setter
    def strand_number(self, value):
        self._strand_number = value
        self._update_props("strand_number", value)

    @property
    def wire_thickness(self):
        """Thickness of rectangular litz wire.

        Returns
        -------
        :class:`pyaedt.modules.Material.MatProperty`
            Thickness of the litz wire.

        References
        ----------

        >>> oDefinitionManager.EditMaterial
        """
        return self._wire_thickness

    @wire_thickness.setter
    def wire_thickness(self, value):
        self._wire_thickness = value
        self._update_props("wire_thickness", value)

    @property
    def wire_diameter(self):
        """Diameter of the round litz wire.

        Returns
        -------
        :class:`pyaedt.modules.Material.MatProperty`
            Diameter of the litz wire.

        References
        ----------

        >>> oDefinitionManager.EditMaterial
        """
        return self._wire_diameter

    @wire_diameter.setter
    def wire_diameter(self, value):
        self._wire_diameter = value
        self._update_props("wire_diameter", value)

    @property
    def wire_width(self):
        """Width of the rectangular or square litz wire.

        Returns
        -------
        :class:`pyaedt.modules.Material.MatProperty`
            Width of the litz wire.

        References
        ----------

        >>> oDefinitionManager.EditMaterial
        """
        return self._wire_width

    @wire_width.setter
    def wire_width(self, value):
        self._wire_width = value
        self._update_props("wire_width", value)

    @property
    def stacking_factor(self):
        """Stacking factor for lamination.

        Returns
        -------
        :class:`pyaedt.modules.Material.MatProperty`
            Stacking factor.

        References
        ----------

        >>> oDefinitionManager.EditMaterial
        """
        return self._stacking_factor

    @stacking_factor.setter
    def stacking_factor(self, value):
        self._stacking_factor = value
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
        self._update_props("stacking_direction", OrderedDict({"property_type": "ChoiceProperty", "Choice": value}))

    @pyaedt_function_handler()
    def set_magnetic_coercitivity(self, value=0, x=1, y=0, z=0):
        """Set Magnetic Coercitivity for material.

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
        self._props["magnetic_coercivity"] = OrderedDict(
            {
                "property_type": "VectorProperty",
                "Magnitude": "{}A_per_meter".format(value),
                "DirComp1": str(x),
                "DirComp2": str(y),
                "DirComp3": str(z),
            }
        )
        return self.update()

    @pyaedt_function_handler()
    def set_electrical_steel_coreloss(self, kh=0, kc=0, ke=0, kdc=0, cut_depth=0.0001):
        """Set Electrical Steel Type Core Loss.

        Parameters
        ----------
        kh : float
        kc : float
        ke : float
        kdc : float
        cut_depth : float

        Returns
        -------
        bool
        """
        if "core_loss_type" not in self._props:
            self._props["core_loss_type"] = OrderedDict(
                {"property_type": "ChoiceProperty", "Choice": "Electrical Steel"}
            )
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
        self._props["core_loss_equiv_cut_depth"] = "{}meter".format(cut_depth)
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
            self._props["core_loss_type"] = OrderedDict(
                {"property_type": "ChoiceProperty", "Choice": "Hysteresis Model"}
            )
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
        self._props["core_loss_hci"] = "{}A_per_meter".format(hci)
        self._props["core_loss_br"] = "{}tesla".format(br)
        self._props["core_loss_hkc"] = str(hkc)
        self._props["core_loss_kdc"] = str(kdc)
        self._props["core_loss_equiv_cut_depth"] = "{}meter".format(cut_depth)
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
            self._props["core_loss_type"] = OrderedDict({"property_type": "ChoiceProperty", "Choice": "Power Ferrite"})
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
        self._props["core_loss_cm"] = "{}A_per_meter".format(cm)
        self._props["core_loss_x"] = "{}tesla".format(x)
        self._props["core_loss_y"] = str(y)
        self._props["core_loss_kdc"] = str(kdc)
        self._props["core_loss_equiv_cut_depth"] = "{}meter".format(cut_depth)
        return self.update()

    @pyaedt_function_handler()
    def set_bp_curve_coreloss(
        self, point_list, kdc=0, cut_depth=0.0001, punit="kw/m^3", bunit="tesla", frequency=60, thickness="0.5mm"
    ):
        """Set B-P Type Core Loss.

        Parameters
        ----------
        point_list : list of list
            List of [x,y] points.
        kdc : float
        cut_depth : float
        punit : str
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
            self._props["core_loss_type"] = OrderedDict({"property_type": "ChoiceProperty", "Choice": "B-P Curve"})
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
        self._props["core_loss_equiv_cut_depth"] = "{}meter".format(cut_depth)
        self._props["core_loss_curves"] = OrderedDict({})
        self._props["core_loss_curves"]["property_type"] = "nonlinear"
        self._props["core_loss_curves"]["PUnit"] = punit
        self._props["core_loss_curves"]["BUnit"] = bunit
        self._props["core_loss_curves"]["Frequency"] = "{}Hz".format(frequency)
        self._props["core_loss_curves"]["Thickness"] = thickness
        self._props["core_loss_curves"]["IsTemperatureDependent"] = False

        self._props["core_loss_curves"]["BPCoordinates"] = OrderedDict({})
        self._props["core_loss_curves"]["BPCoordinates"]["Point"] = []
        for points in point_list:
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
    def get_magnetic_coercitivity(self):
        """Get the magnetic coercitivity values.

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
            ``True`` when the material is a condutor, ``False`` otherwise.

        """
        cond = self.conductivity.value
        if not cond:
            return False
        if "Freq" in str(cond):
            return True
        try:
            if float(cond) >= threshold:
                return True
        except:
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
    materiallib : :class:`pyaedt.modules.MaterialLib.Materials`
        Inherited parent object.
    name : str
        Name of the surface material
    props :
        The default is ``None``.
    """

    def __init__(self, materiallib, name, props=None):
        CommonMaterial.__init__(self, materiallib, name, props)
        self.surface_clarity_type = "Opaque"
        if "surface_clarity_type" in self._props:
            self.surface_clarity_type = self._props["surface_clarity_type"]["Choice"]
        if "PhysicsTypes" in self._props:
            self.physics_type = self._props["PhysicsTypes"]["set"]
        else:
            self.physics_type = ["Thermal"]
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
        pass

    @property
    def emissivity(self):
        """Emissivity.

        Returns
        -------
        :class:`pyaedt.modules.Material.MatProperty`
            Emissivity of the surface material.

        References
        ----------

        >>> oDefinitionManager.EditSurfaceMaterial
        """
        return self._surface_emissivity

    @emissivity.setter
    def emissivity(self, value):

        self._surface_emissivity.value = value
        self._update_props("surface_emissivity", value)

    @property
    def surface_diffuse_absorptance(self):
        """Surface diffuse absorptance.

        Returns
        -------
        :class:`pyaedt.modules.Material.MatProperty`
            Surface diffuse absorptance of the surface material.

        References
        ----------

        >>> oDefinitionManager.EditSurfaceMaterial
        """
        return self._surface_diffuse_absorptance

    @surface_diffuse_absorptance.setter
    def surface_diffuse_absorptance(self, value):

        self._surface_diffuse_absorptance.value = value
        self._update_props("surface_diffuse_absorptance", value)

    @property
    def surface_incident_absorptance(self):
        """Surface incident absorptance.

        Returns
        -------
        :class:`pyaedt.modules.Material.MatProperty`
            Surface incident absorptance of the surface material.

        References
        ----------

        >>> oDefinitionManager.EditSurfaceMaterial
        """
        return self._surface_incident_absorptance

    @surface_incident_absorptance.setter
    def surface_incident_absorptance(self, value):

        self._surface_incident_absorptance.value = value
        self._update_props("surface_incident_absorptance", value)

    @property
    def surface_roughness(self):
        """Surface roughness.

        Returns
        -------
        :class:`pyaedt.modules.Material.MatProperty`
            Surface roughness of the surface material.

        References
        ----------

        >>> oDefinitionManager.EditSurfaceMaterial
        """
        return self._surface_roughness

    @surface_roughness.setter
    def surface_roughness(self, value):
        self._surface_roughness.value = value
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
