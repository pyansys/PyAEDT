from __future__ import absolute_import  # noreorder

import difflib
import fnmatch
import logging
import os
import warnings

from pyaedt import is_ironpython
from pyaedt.edb_core.general import convert_py_list_to_net_list
from pyaedt.generic.clr_module import _clr
from pyaedt.generic.general_methods import pyaedt_function_handler

logger = logging.getLogger(__name__)


class Material(object):
    """Manages EDB methods for material property management."""

    def __init__(self, pclass, edb_material_def):
        self._pclass = pclass
        self._name = edb_material_def.GetName()
        self._edb_material_def = edb_material_def
        self._conductivity = 0.0
        self._loss_tangent = 0.0
        self._magnetic_loss_tangent = 0.0
        self._mass_density = 0.0
        self._permittivity = 0.0
        self._permeability = 0.0
        self._poisson_ratio = 0.0
        self._specific_heat = 0.0
        self._thermal_conductivity = 0.0
        self._youngs_modulus = 0.0
        self._thermal_expansion_coefficient = 0.0
        self._dc_conductivity = 0.0
        self._dc_permittivity = 0.0
        self._dielectric_model_frequency = 0.0
        self._loss_tangent_at_frequency = 0.0
        self._permittivity_at_frequency = 0.0

    def _edb_value(self, value):
        return self._pclass._edb_value(value)

    @property
    def name(self):
        """Retrieve material name."""
        return self._name

    @property
    def _db(self):
        return self._pclass._db

    @property
    def _edb(self):
        return self._pclass._edb

    @pyaedt_function_handler()
    def _get_property(self, property_name):
        if is_ironpython:  # pragma: no cover
            property_box = _clr.StrongBox[float]()
            self._edb_material_def.GetProperty(property_name, property_box)
            return float(property_box)
        else:
            _, property_box = self._edb_material_def.GetProperty(property_name)
            if isinstance(property_box, float):
                return property_box
            else:
                return property_box.ToDouble()

    @property
    def conductivity(self):
        material_id = self._edb.definition.MaterialPropertyId.Conductivity
        self._conductivity = self._get_property(material_id)
        return self._conductivity

    @conductivity.setter
    def conductivity(self, value):
        """Retrieve material conductivity."""
        material_id = self._edb.definition.MaterialPropertyId.Conductivity
        self._edb_material_def.SetProperty(material_id, self._edb_value(value))
        self._conductivity = value

    @property
    def permittivity(self):
        """Retrieve material permittivity."""
        material_id = self._edb.definition.MaterialPropertyId.Permittivity
        self._permittivity = self._get_property(material_id)
        return self._permittivity

    @permittivity.setter
    def permittivity(self, value):
        material_id = self._edb.definition.MaterialPropertyId.Permittivity
        self._edb_material_def.SetProperty(material_id, self._edb_value(value))
        self._permittivity = value

    @property
    def permeability(self):
        """Retrieve material permeability."""
        material_id = self._edb.definition.MaterialPropertyId.Permeability
        self._permeability = self._get_property(material_id)
        return self._permeability

    @permeability.setter
    def permeability(self, value):
        material_id = self._edb.definition.MaterialPropertyId.Permeability
        self._edb_material_def.SetProperty(material_id, self._edb_value(value))
        self._permeability = value

    @property
    def loss_tangent(self):
        """Retrieve material loss tangent."""
        material_id = self._edb.definition.MaterialPropertyId.DielectricLossTangent
        self._loss_tangent = self._get_property(material_id)
        return self._loss_tangent

    @loss_tangent.setter
    def loss_tangent(self, value):
        material_id = self._edb.definition.MaterialPropertyId.DielectricLossTangent
        self._edb_material_def.SetProperty(material_id, self._edb_value(value))
        self._loss_tangent = value

    @property
    def dc_conductivity(self):
        """"""
        if self._edb_material_def.GetDielectricMaterialModel():
            return self._edb_material_def.GetDielectricMaterialModel().GetDCConductivity()

    @dc_conductivity.setter
    def dc_conductivity(self, value):
        if self._edb_material_def.GetDielectricMaterialModel():
            self._edb_material_def.GetDielectricMaterialModel().SetDCConductivity(value)

    @property
    def dc_permittivity(self):
        """"""
        if self._edb_material_def.GetDielectricMaterialModel():
            return self._edb_material_def.GetDielectricMaterialModel().GetDCRelativePermitivity()

    @dc_permittivity.setter
    def dc_permittivity(self, value):
        if self._edb_material_def.GetDielectricMaterialModel():
            self._edb_material_def.GetDielectricMaterialModel().SetDCRelativePermitivity(value)

    @property
    def dielectric_model_frequency(self):
        """Returns
        -------
        Frequency in GHz
        """
        if self._edb_material_def.GetDielectricMaterialModel():
            return self._edb_material_def.GetDielectricMaterialModel().GetFrequency()

    @dielectric_model_frequency.setter
    def dielectric_model_frequency(self, value):
        if self._edb_material_def.GetDielectricMaterialModel():
            self._edb_material_def.GetDielectricMaterialModel().SetFrequency(value)

    @property
    def loss_tangent_at_frequency(self):
        if self._edb_material_def.GetDielectricMaterialModel():
            return self._edb_material_def.GetDielectricMaterialModel().GetLossTangentAtFrequency()

    @loss_tangent_at_frequency.setter
    def loss_tangent_at_frequency(self, value):
        if self._edb_material_def.GetDielectricMaterialModel():
            self._edb_material_def.GetDielectricMaterialModel().SetLossTangentAtFrequency(self._edb_value(value))

    @property
    def permittivity_at_frequency(self):
        if self._edb_material_def.GetDielectricMaterialModel():
            return self._edb_material_def.GetDielectricMaterialModel().GetRelativePermitivityAtFrequency()

    @permittivity_at_frequency.setter
    def permittivity_at_frequency(self, value):
        if self._edb_material_def.GetDielectricMaterialModel():
            self._edb_material_def.GetDielectricMaterialModel().SetRelativePermitivityAtFrequency(value)

    @property
    def magnetic_loss_tangent(self):
        """Retrieve material magnetic loss tangent."""
        material_id = self._edb.definition.MaterialPropertyId.MagneticLossTangent
        self._magnetic_loss_tangent = self._get_property(material_id)
        return self._magnetic_loss_tangent

    @magnetic_loss_tangent.setter
    def magnetic_loss_tangent(self, value):
        material_id = self._edb.definition.MaterialPropertyId.MagneticLossTangent
        self._edb_material_def.SetProperty(material_id, self._edb_value(value))
        self._magnetic_loss_tangent = value

    @property
    def thermal_conductivity(self):
        """Retrieve material thermal conductivity."""
        material_id = self._edb.definition.MaterialPropertyId.ThermalConductivity
        self._thermal_conductivity = self._get_property(material_id)
        return self._thermal_conductivity

    @thermal_conductivity.setter
    def thermal_conductivity(self, value):
        material_id = self._edb.definition.MaterialPropertyId.ThermalConductivity
        self._edb_material_def.SetProperty(material_id, self._edb_value(value))
        self._thermal_conductivity = value

    @property
    def mass_density(self):
        """Retrieve material mass density."""
        material_id = self._edb.definition.MaterialPropertyId.MassDensity
        self._mass_density = self._get_property(material_id)
        return self._mass_density

    @mass_density.setter
    def mass_density(self, value):
        material_id = self._edb.definition.MaterialPropertyId.MassDensity
        self._edb_material_def.SetProperty(material_id, self._edb_value(value))
        self._mass_density = value

    @property
    def youngs_modulus(self):
        """Retrieve material Young's Modulus."""
        material_id = self._edb.definition.MaterialPropertyId.YoungsModulus
        self._youngs_modulus = self._get_property(material_id)
        return self._youngs_modulus

    @youngs_modulus.setter
    def youngs_modulus(self, value):
        material_id = self._edb.definition.MaterialPropertyId.YoungsModulus
        self._edb_material_def.SetProperty(material_id, self._edb_value(value))
        self._youngs_modulus = value

    @property
    def specific_heat(self):
        """Retrieve material Specific Heat."""
        material_id = self._edb.definition.MaterialPropertyId.SpecificHeat
        self._specific_heat = self._get_property(material_id)
        return self._specific_heat

    @specific_heat.setter
    def specific_heat(self, value):
        material_id = self._edb.definition.MaterialPropertyId.SpecificHeat
        self._edb_material_def.SetProperty(material_id, self._edb_value(value))
        self._specific_heat = value

    @property
    def poisson_ratio(self):
        """Retrieve material Poisson Ratio."""
        material_id = self._edb.definition.MaterialPropertyId.PoissonsRatio
        self._poisson_ratio = self._get_property(material_id)
        return self._poisson_ratio

    @poisson_ratio.setter
    def poisson_ratio(self, value):
        material_id = self._edb.definition.MaterialPropertyId.PoissonsRatio
        self._edb_material_def.SetProperty(material_id, self._edb_value(value))
        self._poisson_ratio = value

    @property
    def thermal_expansion_coefficient(self):
        """Retrieve material Thermal Coefficient.."""
        material_id = self._edb.definition.MaterialPropertyId.ThermalExpansionCoefficient
        self._thermal_expansion_coefficient = self._get_property(material_id)
        return self._thermal_expansion_coefficient

    @thermal_expansion_coefficient.setter
    def thermal_expansion_coefficient(self, value):
        material_id = self._edb.definition.MaterialPropertyId.ThermalExpansionCoefficient
        self._edb_material_def.SetProperty(material_id, self._edb_value(value))
        self._thermal_expansion_coefficient = value

    @pyaedt_function_handler()
    def _json_format(self):
        out_dict = {}
        if self.permittivity == 0:  # pragma no cover
            self.permittivity = 1.0
        if self.permeability == 0:  # pragma no cover
            self.permeability = 1.0
        self._name = self.name
        self._conductivity = self.conductivity
        self._loss_tangent = self.loss_tangent
        self._magnetic_loss_tangent = self.magnetic_loss_tangent
        self._mass_density = self.mass_density
        self._permittivity = self.permittivity
        self._permeability = self.permeability
        self._poisson_ratio = self.poisson_ratio
        self._specific_heat = self.specific_heat
        self._thermal_conductivity = self.thermal_conductivity
        self._youngs_modulus = self.youngs_modulus
        self._thermal_expansion_coefficient = self.thermal_expansion_coefficient
        self._dc_conductivity = self.dc_conductivity
        self._dc_permittivity = self.dc_permittivity
        self._dielectric_model_frequency = self.dielectric_model_frequency
        self._loss_tangent_at_frequency = self.loss_tangent_at_frequency
        self._permittivity_at_frequency = self.permittivity_at_frequency
        for k, v in self.__dict__.items():
            if not k == "_pclass" and not k == "_edb_material_def":
                out_dict[k[1:]] = v
        return out_dict

    @pyaedt_function_handler()
    def _load(self, input_dict):
        default_material = {
            "name": "default",
            "conductivity": 0,
            "loss_tangent": 0,
            "magnetic_loss_tangent": 0,
            "mass_density": 0,
            "permittivity": 1,
            "permeability": 1,
            "poisson_ratio": 0,
            "specific_heat": 0,
            "thermal_conductivity": 0,
            "youngs_modulus": 0,
            "thermal_expansion_coefficient": 0,
            "dielectric_model_frequency": None,
            "dc_permittivity": None,
        }
        if input_dict:
            for k, v in input_dict.items():
                default_material[k] = v

            self.conductivity = default_material["conductivity"]
            self.loss_tangent = default_material["loss_tangent"]
            self.magnetic_loss_tangent = default_material["magnetic_loss_tangent"]
            self.mass_density = default_material["mass_density"]
            self.permittivity = default_material["permittivity"]
            self.permeability = default_material["permeability"]
            self.poisson_ratio = default_material["poisson_ratio"]
            self.specific_heat = default_material["specific_heat"]
            self.thermal_conductivity = default_material["thermal_conductivity"]
            self.youngs_modulus = default_material["youngs_modulus"]
            self.thermal_expansion_coefficient = default_material["thermal_expansion_coefficient"]
            if default_material["dielectric_model_frequency"] is not None:  # pragma: no cover
                if self._edb_material_def.GetDielectricMaterialModel():
                    model = self._edb_material_def.GetDielectricMaterialModel()
                    self.dielectric_model_frequency = default_material["dielectric_model_frequency"]
                    self.loss_tangent_at_frequency = default_material["loss_tangent_at_frequency"]
                    self.permittivity_at_frequency = default_material["permittivity_at_frequency"]
                    if default_material["dc_permittivity"] is not None:
                        model.SetUseDCRelativePermitivity(True)
                        self.dc_permittivity = default_material["dc_permittivity"]
                    self.dc_conductivity = default_material["dc_conductivity"]
                else:
                    if not self._pclass.add_djordjevicsarkar_material(
                        default_material["name"],
                        default_material["permittivity_at_frequency"],
                        default_material["loss_tangent_at_frequency"],
                        default_material["dielectric_model_frequency"],
                        default_material["dc_permittivity"],
                        default_material["dc_conductivity"],
                    ):
                        self._pclass._pedb.logger.warning(
                            'Cannot set DS model for material "{}". Check for realistic '
                            "values that define DS Model".format(default_material["name"])
                        )
            else:
                # To unset DS model if already assigned to the material in database
                if self._edb_material_def.GetDielectricMaterialModel():
                    self._edb_material_def.SetDielectricMaterialModel(self._edb_value(None))


class Materials(object):
    """Manages EDB methods for material management accessible from `Edb.materials` property."""

    def __getitem__(self, item):
        return self.materials[item]

    def __init__(self, pedb):
        self._pedb = pedb
        self._syslib = os.path.join(self._pedb.base_path, "syslib")
        self._personal_lib = None
        self._materials_in_aedt = None
        if not self.materials:
            self.add_material("air")
            self.add_material("copper", 1, 0.999991, 5.8e7, 0, 0)
            self.add_material("fr4_epoxy", 4.4, 1, 0, 0.02, 0)
            self.add_material("solder_mask", 3.1, 1, 0, 0.035, 0)

    @property
    def materials_in_aedt(self):
        """Retrieve the dictionary of materials available in AEDT syslib."""
        if self._materials_in_aedt:
            return self._materials_in_aedt
        self._materials_in_aedt = self._read_materials()
        return self._materials_in_aedt

    @property
    def syslib(self):
        """Retrieve the project sys library."""
        return self._syslib

    @property
    def personallib(self):
        """Get or Set the user personallib."""
        return self._personal_lib

    @personallib.setter
    def personallib(self, value):
        self._personal_lib = value
        self._materials_in_aedt = self._read_materials()

    @pyaedt_function_handler()
    def _edb_value(self, value):
        return self._pedb.edb_value(value)

    @property
    def _edb(self):
        return self._pedb.edb_api

    @property
    def _db(self):
        return self._pedb.active_db

    @property
    def materials(self):
        """Retrieve dictionary of material from material library."""
        return {obj.GetName(): Material(self, obj) for obj in list(self._db.MaterialDefs)}

    @pyaedt_function_handler
    def add_material(
        self,
        name="air",
        permittivity=1.0006,
        permeability=1.0000004,
        conductivity=0,
        dielectric_loss_tangent=0,
        magnetic_loss_tangent=0,
    ):
        """Add a new material.

        Parameters
        ----------
        name : str, optional
            Material Name. The default is ``"air"``.
        permittivity : float, str, optional
            Material permittivity. The default is ``1.0006``.
        permeability : float, str, optional
            Material permeability. The default is ``1.0000004``.
        conductivity : float, str, optional
            Material conductivity. The default is ``0``.
        dielectric_loss_tangent : float, str, optional
            Material dielectric loss tangent. The default is ``0``.
        magnetic_loss_tangent : float, str, optional
            Material magnetic loss tangent. The default is ``0``.

        Returns
        -------
        :class:`pyaedt.edb_core.materials.Material`
        """
        if name not in self.materials:
            self._edb.definition.MaterialDef.Create(self._db, name)
            new_material = self.materials[name]
            new_material.permittivity = permittivity
            new_material.permeability = permeability
            new_material.conductivity = conductivity
            new_material.loss_tangent = dielectric_loss_tangent
            new_material.magnetic_loss_tangent = magnetic_loss_tangent
            return new_material
        else:  # pragma: no cover
            warnings.warn("Material {} already exists in material library.".format(name))
            return False

    @pyaedt_function_handler()
    def add_conductor_material(self, name, conductivity):
        """Add a new conductor material in library.

        Parameters
        ----------
        name : str
            Name of the new material.
        conductivity : float
            Conductivity of the new material.

        Returns
        -------
        :class:`pyaedt.edb_core.materials.Material`

        """
        if name not in self.materials:
            self._edb.definition.MaterialDef.Create(self._db, name)
            new_material = self.materials[name]
            new_material.conductivity = conductivity
            new_material.permittivity = 1
            new_material.permeability = 1
            return new_material
        else:  # pragma: no cover
            warnings.warn("Material {} already exists in material library.".format(name))
            return False

    @pyaedt_function_handler()
    def add_dielectric_material(self, name, permittivity, loss_tangent, permeability=1):
        """Add a new dielectric material in library.

        Parameters
        ----------
        name : str
            Name of the new material.
        permittivity : float
            Permittivity of the new material.
        loss_tangent : float
            Loss tangent of the new material.
        permeability : float
            Permeability of the new material.

        Returns
        -------
        :class:`pyaedt.edb_core.materials.Material`
        """
        if name not in self.materials:
            self._edb.definition.MaterialDef.Create(self._db, name)
            new_material = self.materials[name]
            new_material.permittivity = permittivity
            new_material.loss_tangent = loss_tangent
            new_material.permeability = permeability
            return new_material
        else:
            warnings.warn("Material {} already exists in material library.".format(name))
            return False

    @pyaedt_function_handler()
    def get_djordjevicsarkar_model(self, material_name=None):
        """Djordjevic-Sarkar model if present.

        Parameters
        ----------
        material_name : str

        Returns
        -------

        """
        material = self.materials[material_name]
        if material:
            return material.GetDielectricMaterialModel()

    @pyaedt_function_handler()
    def add_djordjevicsarkar_material(
        self, name, permittivity, loss_tangent, test_frequency, dc_permittivity=None, dc_conductivity=None
    ):
        """Create a Djordjevic_Sarkar dielectric.

        Parameters
        ----------
        name : str
            Name of the dielectric.
        permittivity : float
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
        :class:`pyaedt.edb_core.materials.Material`
            Material definition.
        """
        material_def = self._edb.definition.DjordjecvicSarkarModel()
        material_def.SetFrequency(test_frequency)
        material_def.SetLossTangentAtFrequency(self._edb_value(loss_tangent))
        material_def.SetRelativePermitivityAtFrequency(permittivity)
        if dc_conductivity is not None:
            material_def.SetDCConductivity(dc_conductivity)
        if dc_permittivity is not None:
            material_def.SetUseDCRelativePermitivity(True)
            material_def.SetDCRelativePermitivity(dc_permittivity)
        return self._add_dielectric_material_model(name, material_def)

    @pyaedt_function_handler()
    def add_debye_material(
        self,
        name,
        permittivity_low,
        permittivity_high,
        loss_tangent_low,
        loss_tangent_high,
        lower_freqency,
        higher_frequency,
    ):
        """Create a dielectric with the Debye model.

        Parameters
        ----------
        name : str
            Name of the dielectric.
        permittivity_low : float
            Relative permittivity of the dielectric at the frequency specified
            for ``lower_frequency``.
        permittivity_high : float
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
        :class:`pyaedt.edb_core.materials.Material`
            Material definition.
        """
        material_def = self._edb.definition.DebyeModel()
        material_def.SetFrequencyRange(lower_freqency, higher_frequency)
        material_def.SetLossTangentAtHighLowFrequency(loss_tangent_low, loss_tangent_high)
        material_def.SetRelativePermitivityAtHighLowFrequency(
            self._edb_value(permittivity_low), self._edb_value(permittivity_high)
        )
        return self._add_dielectric_material_model(name, material_def)

    @pyaedt_function_handler()
    def add_multipole_debye_material(
        self,
        name,
        frequencies,
        permittivities,
        loss_tangents,
    ):
        """Create a dielectric with the Multipole Debye model.

        Parameters
        ----------
        name : str
            Name of the dielectric.
        frequencies : list
            Frequencies in GHz.
        permittivities : list
            Relative permittivities at each frequency.
        loss_tangents : list
            Loss tangents at each frequency.

        Returns
        -------
        :class:`pyaedt.edb_core.materials.Material`
            Material definition.

        Examples
        --------
        >>> from pyaedt import Edb
        >>> edb = Edb()
        >>> freq = [0, 2, 3, 4, 5, 6]
        >>> rel_perm = [1e9, 1.1e9, 1.2e9, 1.3e9, 1.5e9, 1.6e9]
        >>> loss_tan = [0.025, 0.026, 0.027, 0.028, 0.029, 0.030]
        >>> diel = edb.materials.add_multipole_debye_material("My_MP_Debye", freq, rel_perm, loss_tan)
        """
        frequencies = [float(i) for i in frequencies]
        permittivities = [float(i) for i in permittivities]
        loss_tangents = [float(i) for i in loss_tangents]
        material_def = self._edb.definition.MultipoleDebyeModel()
        material_def.SetParameters(
            convert_py_list_to_net_list(frequencies),
            convert_py_list_to_net_list(permittivities),
            convert_py_list_to_net_list(loss_tangents),
        )
        return self._add_dielectric_material_model(name, material_def)

    @pyaedt_function_handler()
    def _add_dielectric_material_model(self, name, material_model):
        if self._edb.definition.MaterialDef.FindByName(self._db, name).IsNull():
            self._edb.definition.MaterialDef.Create(self._db, name)
        material_def = self._edb.definition.MaterialDef.FindByName(self._db, name)
        succeeded = material_def.SetDielectricMaterialModel(material_model)
        if succeeded:
            return material_def
        return False

    @pyaedt_function_handler()
    def duplicate(self, material_name, new_material_name):
        """Duplicate a material from the database.

        Parameters
        ----------
        material_name : str
            Name of the existing material.
        new_material_name : str
            Name of the new duplicated material.

        Returns
        -------
        EDB material : class: 'Ansys.Ansoft.Edb.definition.MaterialDef'


        Examples
        --------
        >>> from pyaedt import Edb
        >>> edb_app = Edb()
        >>> my_material = edb_app.materials.duplicate("copper", "my_new_copper")

        """
        material_list = {i.lower(): i for i in list(self.materials.keys())}
        if material_name.lower() in material_list and new_material_name not in self.materials:
            material_name = material_list[material_name.lower()]
            permittivity = self._edb_value(self.materials[material_name].permittivity)
            permeability = self._edb_value(self.materials[material_name].permeability)
            conductivity = self._edb_value(self.materials[material_name].conductivity)
            dielectric_loss_tangent = self._edb_value(self.materials[material_name].loss_tangent)
            magnetic_loss_tangent = self._edb_value(self.materials[material_name].magnetic_loss_tangent)
            thermal_conductivity = self._edb_value(self.materials[material_name].thermal_conductivity)
            thermal_expansion_coefficient = self._edb_value(self.materials[material_name].thermal_expansion_coefficient)
            youngs_modulus = self._edb_value(self.materials[material_name].youngs_modulus)
            poisson_ratio = self._edb_value(self.materials[material_name].poisson_ratio)
            mass_density = self._edb_value(self.materials[material_name].mass_density)
            material_model = self.materials[material_name]._edb_material_def.GetDielectricMaterialModel()
            edb_material = self._edb.definition.MaterialDef.Create(self._db, new_material_name)
            edb_material.SetProperty(self._edb.definition.MaterialPropertyId.Permittivity, permittivity)
            edb_material.SetProperty(self._edb.definition.MaterialPropertyId.Permeability, permeability)
            edb_material.SetProperty(self._edb.definition.MaterialPropertyId.Conductivity, conductivity)
            edb_material.SetProperty(
                self._edb.definition.MaterialPropertyId.DielectricLossTangent, dielectric_loss_tangent
            )
            edb_material.SetProperty(self._edb.definition.MaterialPropertyId.ThermalConductivity, thermal_conductivity)
            edb_material.SetProperty(
                self._edb.definition.MaterialPropertyId.ThermalExpansionCoefficient, thermal_expansion_coefficient
            )
            edb_material.SetProperty(self._edb.definition.MaterialPropertyId.MassDensity, mass_density)
            edb_material.SetProperty(self._edb.definition.MaterialPropertyId.YoungsModulus, youngs_modulus)
            edb_material.SetProperty(self._edb.definition.MaterialPropertyId.PoissonsRatio, poisson_ratio)
            edb_material.SetProperty(self._edb.definition.MaterialPropertyId.MagneticLossTangent, magnetic_loss_tangent)
            edb_material.SetProperty(self._edb.definition.MaterialPropertyId.MagneticLossTangent, magnetic_loss_tangent)
            edb_material.SetDielectricMaterialModel(material_model)

            return edb_material

    @pyaedt_function_handler()
    def _load_materials(self, material=None):
        if self.materials:
            mat_keys = [i.lower() for i in self.materials.keys()]
            mat_keys_case = [i for i in self.materials.keys()]
        else:
            mat_keys = []
            mat_keys_case = []

        if not material:
            return
        if material["name"].lower() not in mat_keys:
            if material["conductivity"] > 1e4:
                self.add_conductor_material(material["name"], material["conductivity"])
            else:
                self.add_dielectric_material(material["name"], material["permittivity"], material["loss_tangent"])
            self.materials[material["name"]]._load(material)
        else:
            self.materials[mat_keys_case[mat_keys.index(material["name"].lower())]]._load(material)

    @pyaedt_function_handler
    def material_name_to_id(self, property_name):
        """Convert a material property name to a material property ID.

        Parameters
        ----------
        property_name : str
            Name of the material property.

        Returns
        -------
        ID of the material property.
        """
        props = {
            "Permittivity": self._edb.definition.MaterialPropertyId.Permittivity,
            "Permeability": self._edb.definition.MaterialPropertyId.Permeability,
            "Conductivity": self._edb.definition.MaterialPropertyId.Conductivity,
            "DielectricLossTangent": self._edb.definition.MaterialPropertyId.DielectricLossTangent,
            "MagneticLossTangent": self._edb.definition.MaterialPropertyId.MagneticLossTangent,
            "ThermalConductivity": self._edb.definition.MaterialPropertyId.ThermalConductivity,
            "MassDensity": self._edb.definition.MaterialPropertyId.MassDensity,
            "SpecificHeat": self._edb.definition.MaterialPropertyId.SpecificHeat,
            "YoungsModulus": self._edb.definition.MaterialPropertyId.YoungsModulus,
            "PoissonsRatio": self._edb.definition.MaterialPropertyId.PoissonsRatio,
            "ThermalExpansionCoefficient": self._edb.definition.MaterialPropertyId.ThermalExpansionCoefficient,
            "InvalidProperty": self._edb.definition.MaterialPropertyId.InvalidProperty,
        }

        found_el = difflib.get_close_matches(property_name, list(props.keys()), 1, 0.7)
        if found_el:
            return props[found_el[0]]
        else:
            return self._edb.definition.MaterialPropertyId.InvalidProperty

    @pyaedt_function_handler()
    def get_property_by_material_name(self, property_name, material_name):
        """Get the property of a material. If it is executed in IronPython,
         you must only use the first element of the returned tuple, which is a float.

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
        >>> returned_tuple = edb_app.materials.get_property_by_material_name("conductivity", "copper")
        >>> edb_value = returned_tuple[0]
        >>> float_value = returned_tuple[1]

        """
        if self._edb.definition.MaterialDef.FindByName(self._pedb._db, material_name).IsNull():
            self._pedb.logger.error("This material doesn't exists.")
        else:
            original_material = self._edb.definition.MaterialDef.FindByName(self._pedb._db, material_name)
            if is_ironpython:  # pragma: no cover
                property_box = _clr.StrongBox[float]()
                original_material.GetProperty(self.material_name_to_id(property_name), property_box)
                return float(property_box)
            else:
                _, property_box = original_material.GetProperty(
                    self.material_name_to_id(property_name), self._edb_value(0.0)
                )
                if isinstance(property_box, float):
                    return property_box
                else:
                    return property_box.ToDouble()
        return False

    @pyaedt_function_handler()
    def add_material_from_aedt(self, material_name):
        """Add a material read from ``syslib amat`` library.

        Parameters
        ----------
        material_name : str
            Material name.

        Returns
        -------
        bool
            "True`` when successful, ``False`` when failed.
        """
        if material_name in self.materials_in_aedt:
            if material_name in list(self.materials.keys()):
                self._pedb.logger.warning("Material {} already exists. Skipping it.".format(material_name))
                return False
            new_material = self.add_material(name=material_name)
            material = self.materials_in_aedt[material_name]
            try:
                new_material.permittivity = float(material["permittivity"])
            except (KeyError, TypeError):
                pass
            try:
                new_material.conductivity = float(material["conductivity"])
            except (KeyError, TypeError):
                pass
            try:
                new_material.mass_density = float(material["mass_density"])
            except (KeyError, TypeError):
                pass
            try:
                new_material.permeability = float(material["permeability"])
            except (KeyError, TypeError):
                pass
            try:
                new_material.loss_tangent = float(material["dielectric_loss_tangent"])
            except (KeyError, TypeError):
                pass
            try:
                new_material.specific_heat = float(material["specific_heat"])
            except (KeyError, TypeError):
                pass
            try:
                new_material.thermal_expansion_coefficient = float(material["thermal_expansion_coeffcient"])
            except (KeyError, TypeError):
                pass
            return True

    @pyaedt_function_handler()
    def load_amat(self, amat_file):
        """Load material from an amat file and add materials to Edb.

        Parameters
        ----------
        amat_file : str
            Full path to the amat file to read and add to the Edb.
        """
        material_dict = self._read_materials(amat_file)
        for material_name, material in material_dict.items():
            if material_name not in list(self.materials.keys()):
                new_material = self.add_material(name=material_name)
                try:
                    new_material.permittivity = float(material["permittivity"])
                except (KeyError, TypeError):
                    pass
                try:
                    new_material.conductivity = float(material["conductivity"])
                except (KeyError, TypeError):
                    pass
                try:
                    new_material.mass_density = float(material["mass_density"])
                except (KeyError, TypeError):
                    pass
                try:
                    new_material.permeability = float(material["permeability"])
                except (KeyError, TypeError):
                    pass
                try:
                    new_material.loss_tangent = float(material["dielectric_loss_tangent"])
                except (KeyError, TypeError):
                    pass
                try:
                    new_material.specific_heat = float(material["specific_heat"])
                except (KeyError, TypeError):
                    pass
                try:
                    new_material.thermal_expansion_coefficient = float(material["thermal_expansion_coeffcient"])
                except (KeyError, TypeError):
                    pass
        return True

    @pyaedt_function_handler()
    def _read_materials(self, mat_file=None):
        def get_mat_list(file_name, mats):
            from pyaedt.generic.LoadAEDTFile import load_entire_aedt_file

            mread = load_entire_aedt_file(file_name)
            for mat, mdict in mread.items():
                if mat != "$base_index$":
                    try:
                        mats[mat] = mdict["MaterialDef"][mat]
                    except KeyError:
                        mats[mat] = mdict

        if mat_file and os.path.exists(mat_file):
            materials = {}
            get_mat_list(mat_file, materials)
            return materials

        amat_sys = [
            os.path.join(dirpath, filename)
            for dirpath, _, filenames in os.walk(self.syslib)
            for filename in filenames
            if fnmatch.fnmatch(filename, "*.amat")
        ]
        amat_personal = []
        if self.personallib:
            amat_personal = [
                os.path.join(dirpath, filename)
                for dirpath, _, filenames in os.walk(self.personallib)
                for filename in filenames
                if fnmatch.fnmatch(filename, "*.amat")
            ]
        materials = {}
        for amat in amat_sys:
            get_mat_list(amat, materials)

        if amat_personal:
            for amat in amat_personal:
                get_mat_list(amat, materials)
        return materials
