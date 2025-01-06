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

import warnings

from ansys.aedt.core.generic.data_handlers import _dict2arg
from ansys.aedt.core.generic.data_handlers import random_string
from ansys.aedt.core.generic.general_methods import GrpcApiError
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.modeler.cad.elements_3d import BinaryTreeNode
from ansys.aedt.core.modules.boundary.common import BoundaryCommon
from ansys.aedt.core.modules.boundary.common import BoundaryProps
from ansys.aedt.core.modules.boundary.common import disable_auto_update


class NativeComponentObject(BoundaryCommon, BinaryTreeNode):
    """Manages Native Component data and execution.

    Parameters
    ----------
    app : object
        An AEDT application from ``ansys.aedt.core.application``.
    component_type : str
        Type of the component.
    component_name : str
        Name of the component.
    props : dict
        Properties of the boundary.

    Examples
    --------
    This example the par_beam returned object is a
    :class:`ansys.aedt.core.modules.boundary.layout_boundary.NativeComponentObject`.

    >>> from ansys.aedt.core import Hfss
    >>> hfss = Hfss(solution_type="SBR+")
    >>> ffd_file ="path/to/ffdfile.ffd"
    >>> par_beam = hfss.create_sbr_file_based_antenna(ffd_file)
    >>> par_beam.native_properties["Size"] = "0.1mm"
    >>> par_beam.update()
    >>> par_beam.delete()
    """

    def __init__(self, app, component_type, component_name, props):
        self.auto_update = False
        self._app = app
        self._name = component_name

        self.__props = BoundaryProps(
            self,
            {
                "TargetCS": "Global",
                "SubmodelDefinitionName": self.name,
                "ComponentPriorityLists": {},
                "NextUniqueID": 0,
                "MoveBackwards": False,
                "DatasetType": "ComponentDatasetType",
                "DatasetDefinitions": {},
                "BasicComponentInfo": {
                    "ComponentName": self.name,
                    "Company": "",
                    "Company URL": "",
                    "Model Number": "",
                    "Help URL": "",
                    "Version": "1.0",
                    "Notes": "",
                    "IconType": "",
                },
                "GeometryDefinitionParameters": {"VariableOrders": {}},
                "DesignDefinitionParameters": {"VariableOrders": {}},
                "MaterialDefinitionParameters": {"VariableOrders": {}},
                "DefReferenceCSID": 1,
                "MapInstanceParameters": "DesignVariable",
                "UniqueDefinitionIdentifier": "89d26167-fb77-480e-a7ab-"
                + random_string(12, char_set="abcdef0123456789"),
                "OriginFilePath": "",
                "IsLocal": False,
                "ChecksumString": "",
                "ChecksumHistory": [],
                "VersionHistory": [],
                "NativeComponentDefinitionProvider": {"Type": component_type},
                "InstanceParameters": {"GeometryParameters": "", "MaterialParameters": "", "DesignParameters": ""},
            },
        )
        if props:
            self._update_props(self.__props, props)
        self.native_properties = self.__props["NativeComponentDefinitionProvider"]
        self.auto_update = True

        self._initialize_tree_node()

    @property
    def _child_object(self):
        """Object-oriented properties.

        Returns
        -------
        class:`ansys.aedt.core.modeler.cad.elements_3d.BinaryTreeNode`

        """
        child_object = None
        for el in self._app.oeditor.GetChildNames("ComponentDefinition"):
            design_childs = self._app.get_oo_object(self._app.oeditor, el).GetChildNames()
            if self._name in design_childs:
                child_object = self._app.get_oo_object(self._app.oeditor, f"{el}\\{self._name}")
                break
        return child_object

    @property
    def props(self):
        """AEDT boundary component internal properties.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryProps`
        """
        warnings.warn("This method is deprecated. Use properties instead.", DeprecationWarning)
        return self.properties

    @property
    def properties(self):
        return self.__props

    @property
    def name(self):
        """Boundary Name."""
        if self._child_object:
            self._name = str(self.properties["Name"])
        return self._name

    @name.setter
    def name(self, value):
        if self._child_object:
            try:
                legacy_name = self._name
                self.properties["Name"] = value
                self._app.modeler.user_defined_components[self._name] = self
                del self._app.modeler.user_defined_components[legacy_name]
            except KeyError:
                self._app.logger.error("Name %s already assigned in the design", value)

    @property
    def definition_name(self):
        """Definition name of the native component.

        Returns
        -------
        str
           Name of the native component.

        """
        definition_name = None
        if self.props and "SubmodelDefinitionName" in self.props:
            definition_name = self.props["SubmodelDefinitionName"]
        return definition_name

    @property
    def targetcs(self):
        """Native Component Coordinate System.

        Returns
        -------
        str
            Native Component Coordinate System.
        """
        if "TargetCS" in list(self.props.keys()):
            return self.props["TargetCS"]
        else:
            return "Global"

    @targetcs.setter
    def targetcs(self, cs):
        self.props["TargetCS"] = cs

    def _update_props(self, d, u):
        for k, v in u.items():
            if isinstance(v, dict):
                if k not in d:
                    d[k] = {}
                d[k] = self._update_props(d[k], v)
            else:
                d[k] = v
        return d

    @pyaedt_function_handler()
    def _get_args(self, props=None):
        if props is None:
            props = self.props
        arg = ["NAME:InsertNativeComponentData"]
        _dict2arg(props, arg)
        return arg

    @pyaedt_function_handler()
    def create(self):
        """Create a Native Component in AEDT.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        try:
            names = [i for i in self._app.excitations]
        except GrpcApiError:  # pragma: no cover
            names = []
        self._name = self._app.modeler.oeditor.InsertNativeComponent(self._get_args())
        try:
            a = [i for i in self._app.excitations if i not in names]
            self.excitation_name = a[0].split(":")[0]
        except (GrpcApiError, IndexError):
            self.excitation_name = self._name
        return self._initialize_tree_node()

    @pyaedt_function_handler()
    def update(self):
        """Update the Native Component in AEDT.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """

        self.update_props = {}
        self.update_props["DefinitionName"] = self.props["SubmodelDefinitionName"]
        self.update_props["GeometryDefinitionParameters"] = self.props["GeometryDefinitionParameters"]
        self.update_props["DesignDefinitionParameters"] = self.props["DesignDefinitionParameters"]
        self.update_props["MaterialDefinitionParameters"] = self.props["MaterialDefinitionParameters"]
        self.update_props["NextUniqueID"] = self.props["NextUniqueID"]
        self.update_props["MoveBackwards"] = self.props["MoveBackwards"]
        self.update_props["DatasetType"] = self.props["DatasetType"]
        self.update_props["DatasetDefinitions"] = self.props["DatasetDefinitions"]
        self.update_props["NativeComponentDefinitionProvider"] = self.props["NativeComponentDefinitionProvider"]
        self.update_props["ComponentName"] = self.props["BasicComponentInfo"]["ComponentName"]
        self.update_props["Company"] = self.props["BasicComponentInfo"]["Company"]
        self.update_props["Model Number"] = self.props["BasicComponentInfo"]["Model Number"]
        self.update_props["Help URL"] = self.props["BasicComponentInfo"]["Help URL"]
        self.update_props["Version"] = self.props["BasicComponentInfo"]["Version"]
        self.update_props["Notes"] = self.props["BasicComponentInfo"]["Notes"]
        self.update_props["IconType"] = self.props["BasicComponentInfo"]["IconType"]
        self._app.modeler.oeditor.EditNativeComponentDefinition(self._get_args(self.update_props))

        return True

    @pyaedt_function_handler()
    def delete(self):
        """Delete the Native Component in AEDT.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        self._app.modeler.oeditor.Delete(["NAME:Selections", "Selections:=", self.name])
        for el in self._app._native_components:
            if el.name == self.name:
                self._app._native_components.remove(el)
                del self._app.modeler.user_defined_components[self.name]
                self._app.modeler.cleanup_objects()
        return True


class BoundaryObject3dLayout(BoundaryCommon, BinaryTreeNode):
    """Manages boundary data and execution for Hfss3dLayout.

    Parameters
    ----------
    app : object
        An AEDT application from ``ansys.aedt.core.application``.
    name : str
        Name of the boundary.
    props : dict, optional
        Properties of the boundary.
    boundarytype : str
        Type of the boundary.
    """

    def __init__(self, app, name, props=None, boundarytype="Port"):
        self.auto_update = False
        self._app = app
        self._name = name
        self.__props = None
        if props:
            self.__props = BoundaryProps(self, props)
        self.type = boundarytype
        self.auto_update = True
        self._initialize_tree_node()

    @property
    def _child_object(self):

        cc = self._app.odesign.GetChildObject("Excitations")
        child_object = None
        if self.name in cc.GetChildNames():
            child_object = self._app.odesign.GetChildObject("Excitations").GetChildObject(self.name)
        elif self.name in self._app.odesign.GetChildObject("Excitations").GetChildNames():
            child_object = self._app.odesign.GetChildObject("Excitations").GetChildObject(self.name)

        if "Boundaries" in self._app.odesign.GetChildNames():
            cc = self._app.odesign.GetChildObject("Boundaries")
            if self.name in cc.GetChildNames():
                child_object = self._app.odesign.GetChildObject("Boundaries").GetChildObject(self.name)
            elif self.name in self._app.odesign.GetChildObject("Boundaries").GetChildNames():
                child_object = self._app.odesign.GetChildObject("Boundaries").GetChildObject(self.name)

        return child_object

    @property
    def name(self):
        """Boundary Name."""
        return self._name

    @name.setter
    def name(self, value):
        if "Port" in self.props:
            self.auto_update = False
            self.props["Port"] = value
            self.auto_update = True
        self.update()
        self._name = value

    @property
    def props(self):
        """Excitation data.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryProps`
        """
        warnings.warn("This method is deprecated. Use properties instead.", DeprecationWarning)
        return self.properties

    @property
    def properties(self):
        """Excitation data.

        Returns
        -------
        :class:`ansys.aedt.core.modules.boundary.common.BoundaryProps`
        """
        if self.__props:
            return self.__props
        props = self._get_boundary_data(self.name)

        if props:
            self.__props = BoundaryProps(self, props[0])
            self._type = props[1]
        return self.__props

    @pyaedt_function_handler()
    def _get_args(self, props=None):
        """Retrieve arguments.

        Parameters
        ----------
        props :
            The default is ``None``.

        Returns
        -------
        list
            List of boundary properties.

        """
        if props is None:
            props = self.props
        arg = ["NAME:" + self.name]
        _dict2arg(props, arg)
        return arg

    @pyaedt_function_handler()
    def _refresh_properties(self):
        if len(self._app.oeditor.GetProperties("EM Design", f"Excitations:{self.name}")) != len(self.props):
            propnames = self._app.oeditor.GetProperties("EM Design", f"Excitations:{self.name}")
            props = {}
            for prop in propnames:
                props[prop] = self._app.oeditor.GetPropertyValue("EM Design", f"Excitations:{self.name}", prop)
            self.__props = BoundaryProps(self, props)

    @pyaedt_function_handler()
    def update(self):
        """Update the boundary.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        updated = False
        for el in list(self.props.keys()):
            if el == "Port" and self._name != self.props[el]:
                self._app.oeditor.SetPropertyValue("EM Design", "Excitations:" + self.name, el, self.props[el])
                self._name = self.props[el]
            elif el in self._app.oeditor.GetProperties("EM Design", f"Excitations:{self.name}") and self.props[
                el
            ] != self._app.oeditor.GetPropertyValue("EM Design", "Excitations:" + self.name, el):
                self._app.oeditor.SetPropertyValue("EM Design", "Excitations:" + self.name, el, self.props[el])
                updated = True

        if updated:
            self._refresh_properties()

        return True


class NativeComponentPCB(NativeComponentObject, object):
    """Manages native component PCB data and execution.

    Parameters
    ----------
    app : object
        AEDT application from the ``pyaedt.application`` class.
    component_type : str
        Type of the component.
    component_name : str
        Name of the component.
    props : dict
        Properties of the boundary.
    """

    def __init__(self, app, component_type, component_name, props):
        NativeComponentObject.__init__(self, app, component_type, component_name, props)

    @pyaedt_function_handler()
    @disable_auto_update
    def set_resolution(self, resolution):
        """Set metal fraction mapping resolution.

        Parameters
        -------
        resolution : int
            Resolution level. Accepted variables between 1 and 5.

        Returns
        -------
        bool
            True if successful, else False.
        """
        if resolution < 1 or resolution > 5:
            self._app.logger.error("Valid resolution values are between 1 and 5.")
            return False
        self.props["NativeComponentDefinitionProvider"]["Resolution"] = resolution
        self.props["NativeComponentDefinitionProvider"]["CustomResolution"] = False
        return True

    @pyaedt_function_handler()
    @disable_auto_update
    def set_custom_resolution(self, row, col):
        """Set custom metal fraction mapping resolution.

        Parameters
        ----------
        row : int
            Resolution level in rows direction.
        col : int
            Resolution level in columns direction.

        Returns
        -------
        bool
            True if successful, else False.
        """
        self.props["NativeComponentDefinitionProvider"]["CustomResolutionRow"] = row
        self.props["NativeComponentDefinitionProvider"]["CustomResolutionCol"] = col
        self.props["NativeComponentDefinitionProvider"]["CustomResolution"] = True
        return True

    @property
    def power(self):
        """Power dissipation assigned to the PCB."""
        return self.props["NativeComponentDefinitionProvider"].get("Power", "0W")

    @pyaedt_function_handler()
    @disable_auto_update
    def set_high_side_radiation(
        self,
        enabled,
        surface_material="Steel-oxidised-surface",
        radiate_to_ref_temperature=False,
        view_factor=1,
        ref_temperature="AmbientTemp",
    ):
        """Set high side radiation properties.

        Parameters
        ----------
        enabled : bool
            Whether high side radiation is enabled.
        surface_material : str, optional
            Surface material to apply. Default is ``"Steel-oxidised-surface"``.
        radiate_to_ref_temperature : bool, optional
            Whether to radiate to a reference temperature instead of objects in the model.
            Default is ``False``.
        view_factor : float, optional
            View factor to use for radiation computation if ``radiate_to_ref_temperature``
            is set to ``True``. Default is 1.
        ref_temperature : str, optional
            Reference temperature to use for radiation computation if
            ``radiate_to_ref_temperature`` is set to True. Default is ``"AmbientTemp"``.

        Returns
        -------
        bool
            ``True`` if successful, else ``False``.
        """
        high_rad = {
            "Radiate": enabled,
            "RadiateTo - High": "RefTemperature - High" if radiate_to_ref_temperature else "AllObjects - High",
            "Surface Material - High": surface_material,
        }
        if radiate_to_ref_temperature:
            high_rad["Ref. Temperature - High"] = (ref_temperature,)
            high_rad["View Factor - High"] = view_factor
        self.props["NativeComponentDefinitionProvider"]["HighSide"] = high_rad
        return True

    @power.setter
    @disable_auto_update
    def power(self, value):
        """Assign power dissipation to the PCB.

        Parameters
        ----------
        value : str
            Power to apply to the PCB.
        """
        self.props["NativeComponentDefinitionProvider"]["Power"] = value

    @property
    def force_source_solve(self):
        """Force source solution option."""
        return self.props["NativeComponentDefinitionProvider"].get("DefnLink", {}).get("ForceSourceToSolve", False)

    @force_source_solve.setter
    @disable_auto_update
    def force_source_solve(self, val):
        """Set Whether to force source solution.

        Parameters
        ----------
        value : bool
            Whether to force source solution.
        """
        if not isinstance(val, bool):
            self._app.logger.error("Only Boolean value can be accepted.")
            return
        return self.props["NativeComponentDefinitionProvider"]["DefnLink"].update({"ForceSourceToSolve": val})

    @property
    def preserve_partner_solution(self):
        """Preserve parner solution option."""
        return self.props["NativeComponentDefinitionProvider"].get("DefnLink", {}).get("PreservePartnerSoln", False)

    @preserve_partner_solution.setter
    @disable_auto_update
    def preserve_partner_solution(self, val):
        """Set Whether to preserve partner solution.

        Parameters
        ----------
        val : bool
            Whether to preserve partner solution.
        """
        if not isinstance(val, bool):
            self._app.logger.error("Only boolean can be accepted.")
            return
        return self.props["NativeComponentDefinitionProvider"]["DefnLink"].update({"PreservePartnerSoln": val})

    @property
    def included_parts(self):
        """Parts options."""
        p = self.props["NativeComponentDefinitionProvider"].get("PartsChoice", 0)
        if p == 0:
            return None
        elif p == 1:
            return PCBSettingsDeviceParts(self, self._app)
        elif p == 2:
            return PCBSettingsPackageParts(self, self._app)

    @included_parts.setter
    @disable_auto_update
    def included_parts(self, value):
        """Set PCB parts incusion option.

        Parameters
        ----------
        value : str or int
            Valid options are ``"None"``, ``"Device"``, and ``"Package"`` (or 0, 1, and 2 respectivaly)
        """
        if value is None:
            value = "None"
        part_map = {"None": 0, "Device": 1, "Package": 2}
        if not isinstance(value, int):
            value = part_map.get(value, None)
        if value is not None:
            self.props["NativeComponentDefinitionProvider"]["PartsChoice"] = value
        else:
            self._app.logger.error(
                'Invalid part choice. Valid options are "None", "Device", and "Package" (or 0, 1, and 2 respectively).'
            )

    @pyaedt_function_handler()
    @disable_auto_update
    def set_low_side_radiation(
        self,
        enabled,
        surface_material="Steel-oxidised-surface",
        radiate_to_ref_temperature=False,
        view_factor=1,
        ref_temperature="AmbientTemp",
    ):
        """Set low side radiation properties.

        Parameters
        ----------
        enabled : bool
            Whether high side radiation is enabled.
        surface_material : str, optional
            Surface material to apply. Default is ``"Steel-oxidised-surface"``.
        radiate_to_ref_temperature : bool, optional
            Whether to radiate to a reference temperature instead of objects in the model.
            Default is ``False``.
        view_factor : float, optional
            View factor to use for radiation computation if ``radiate_to_ref_temperature``
            is set to True. Default is 1.
        ref_temperature : str, optional
            Reference temperature to use for radiation computation if
            ``radiate_to_ref_temperature`` is set to ``True``. Default is ``"AmbientTemp"``.

        Returns
        -------
        bool
            ``True`` if successful, else ``False``.
        """
        low_side = {
            "Radiate": enabled,
            "RadiateTo": "RefTemperature - High" if radiate_to_ref_temperature else "AllObjects",
            "Surface Material": surface_material,
        }
        if radiate_to_ref_temperature:
            low_side["Ref. Temperature"] = (ref_temperature,)
            low_side["View Factor"] = view_factor
        self.props["NativeComponentDefinitionProvider"]["LowSide"] = low_side
        return True

    @power.setter
    @disable_auto_update
    def power(self, value):
        """Assign power dissipation to the PCB.

        Parameters
        ----------
        value : str
            Power to apply to the PCB.
        """
        self.props["NativeComponentDefinitionProvider"]["Power"] = value

    @force_source_solve.setter
    @disable_auto_update
    def force_source_solve(self, val):
        """Set Whether to force source solution.

        Parameters
        ----------
        value : bool
            Whether to force source solution.
        """
        if not isinstance(val, bool):
            self._app.logger.error("Only Boolean value can be accepted.")
            return
        return self.props["NativeComponentDefinitionProvider"]["DefnLink"].update({"ForceSourceToSolve": val})

    @preserve_partner_solution.setter
    @disable_auto_update
    def preserve_partner_solution(self, val):
        """Set Whether to preserve partner solution.

        Parameters
        ----------
        val : bool
            Whether to preserve partner solution.
        """
        if not isinstance(val, bool):
            self._app.logger.error("Only boolean can be accepted.")
            return
        return self.props["NativeComponentDefinitionProvider"]["DefnLink"].update({"PreservePartnerSoln": val})

    @included_parts.setter
    @disable_auto_update
    def included_parts(self, value):
        """Set PCB parts incusion option.

        Parameters
        ----------
        value : str or int
            Valid options are ``"None"``, ``"Device"``, and ``"Package"`` (or 0, 1, and 2 respectivaly)
        """
        if value is None:
            value = "None"
        part_map = {"None": 0, "Device": 1, "Package": 2}
        if not isinstance(value, int):
            value = part_map.get(value, None)
        if value is not None:
            self.props["NativeComponentDefinitionProvider"]["PartsChoice"] = value
        else:
            self._app.logger.error(
                'Invalid part choice. Valid options are "None", "Device", and "Package" (or 0, 1, and 2 respectively).'
            )

    @pyaedt_function_handler()
    def identify_extent_poly(self):
        """Get polygon that defines board extent.

        Returns
        -------
        str
            Name of the polygon to include.
        """
        from ansys.aedt.core import Hfss3dLayout

        prj = self.props["NativeComponentDefinitionProvider"]["DefnLink"]["Project"]
        if prj == "This Project*":
            prj = self._app.project_name
        layout = Hfss3dLayout(project=prj, design=self.props["NativeComponentDefinitionProvider"]["DefnLink"]["Design"])
        layer = [o for o in layout.modeler.stackup.drawing_layers if o.type == "outline"][0]
        outlines = [p for p in layout.modeler.polygons.values() if p.placement_layer == layer.name]
        if len(outlines) > 1:
            self._app.logger.info(
                f"{outlines[0].name} automatically selected as ``extent_polygon``, "
                f"pass ``extent_polygon`` argument explixitly to select a different one. "
                f"Available choices are: {', '.join([o.name for o in outlines])}"
            )
        elif len(outlines) == 0:
            self._app.logger.error("No polygon found in the Outline layer.")
            return False
        return outlines[0].name

    @property
    def board_cutout_material(self):
        """Material applied to cutout regions."""
        return self.props["NativeComponentDefinitionProvider"].get("BoardCutoutMaterial", "air ")

    @property
    def via_holes_material(self):
        """Material applied to via hole regions."""
        return self.props["NativeComponentDefinitionProvider"].get("ViaHoleMaterial", "copper")

    @board_cutout_material.setter
    @disable_auto_update
    def board_cutout_material(self, value):
        """Set material to apply to cutout regions.

        Parameters
        ----------
        value : str
            Material to apply to cutout regions.
        """
        self.props["NativeComponentDefinitionProvider"]["BoardCutoutMaterial"] = value

    @via_holes_material.setter
    @disable_auto_update
    def via_holes_material(self, value):
        """Set material to apply to via hole regions.

        Parameters
        ----------
        value : str
            Material to apply to via hole regions.
        """
        self.props["NativeComponentDefinitionProvider"]["ViaHoleMaterial"] = value

    @pyaedt_function_handler()
    @disable_auto_update
    def set_board_extents(self, extent_type=None, extent_polygon=None):
        """Set board extent.

        Parameters
        ----------
        extent_type : str, optional
            Extent definition of the PCB. Default is ``None`` in which case the 3D Layout extent
            will be used. Other possible options are: ``"Bounding Box"`` or ``"Polygon"``.
        extent_polygon : str, optional
            Polygon name to use in the extent definition of the PCB. Default is ``None``. This
            argument is mandatory if ``extent_type`` is ``"Polygon"``.

        Returns
        -------
        bool
            ``True`` if successful. ``False`` otherwise.
        """
        if extent_type is None:
            self.props["NativeComponentDefinitionProvider"]["Use3DLayoutExtents"] = True
        else:
            allowed_extent_types = ["Bounding Box", "Polygon"]
            if extent_type not in allowed_extent_types:
                self._app.logger.error(
                    f"Accepted argument for ``extent_type`` are:"
                    f" {', '.join(allowed_extent_types)}. {extent_type} provided"
                )
                return False
            self.props["NativeComponentDefinitionProvider"]["ExtentsType"] = extent_type
            if extent_type == "Polygon":
                if extent_polygon is None:
                    extent_polygon = self.identify_extent_poly()
                    if not extent_polygon:
                        return False
                self.props["NativeComponentDefinitionProvider"]["OutlinePolygon"] = extent_polygon
        return True


class PCBSettingsPackageParts(object):
    """Handle package part settings of the PCB component.

    Parameters
    ----------
    pcb_obj : :class:`ansys.aedt.core.modules.layout_boundary.NativeComponentPCB`
            Inherited pcb object.
    app : :class:`pyaedt.Icepak`
            Inherited application object.
    """

    def __init__(self, pcb_obj, app):
        self._app = app
        self.pcb = pcb_obj
        self._solderbumps_map = {"Lumped": "SbLumped", "Cylinders": "SbCylinder", "Boxes": "SbBlock"}

    def __eq__(self, other):
        if isinstance(other, str):
            return other == "Package"
        elif isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    @pyaedt_function_handler()
    @disable_auto_update
    def set_solderballs_modeling(self, modeling=None):
        """Set how to model solderballs.

        Parameters
        ----------
        modeling : str, optional
            Method for modeling solderballs located below the stackup. The default is
            ``None``, in which case they are not modeled. Options for modeling are
            ``"Boxes"``, ``"Cylinders"``, and ``"Lumped"``.

        Returns
        -------
        bool
            ``True`` if successful, ``False`` otherwise.
        """
        update_properties = {
            "CreateBottomSolderballs": modeling is not None,
            "BottomSolderballsModelType": self._solderbumps_map[modeling],
        }

        self.pcb.props["NativeComponentDefinitionProvider"].update(update_properties)
        return True

    @pyaedt_function_handler()
    @disable_auto_update
    def set_connectors_modeling(
        self,
        modeling=None,
        solderbumps_modeling="Boxes",
        bondwire_material="Au-Typical",
        bondwire_diameter="0.05mm",
    ):
        """Set how to model connectors.

        Parameters
        ----------
            modeling : str, optional
                Method for modeling connectors located above the stackup. The default is
                ``None``, in which case they are not modeled. Options for modeling are
                ``"Bondwire"`` and ``"Solderbump"``.
            solderbumps_modeling : str, optional
                Method for modeling solderbumps if ``modeling="Solderbump"``.
                The default is ```"Boxes"``. Options are ``"Boxes"``, ``"Cylinders"``,
                and ``"Lumped"``.
            bondwire_material : str, optional
                Bondwire material if ``modeling="Bondwire"``. The default is
                ``"Au-Typical"``.
            bondwire_diameter : str, optional
                Bondwires diameter if ``modeling="Bondwire".
                The default is ``"0.05mm"``.

        Returns
        -------
        bool
            ``True`` if successful, ``False`` otherwise.
        """
        valid_connectors = ["Solderbump", "Bondwire"]
        if modeling is not None and modeling not in valid_connectors:
            self._app.logger.error(
                f"{modeling} option is not supported. Use one of the following: {', '.join(valid_connectors)}"
            )
            return False
        if bondwire_material not in self._app.materials.mat_names_aedt:
            self._app.logger.error(f"{bondwire_material} material is not present in the library.")
            return False
        if self._solderbumps_map.get(solderbumps_modeling, None) is None:
            self._app.logger.error(
                f"Solderbumps modeling option {solderbumps_modeling} is not valid. "
                f"Available options are: {', '.join(list(self._solderbumps_map.keys()))}."
            )
            return False

        update_properties = {
            "CreateTopSolderballs": modeling is not None,
            "TopConnectorType": modeling,
            "TopSolderballsModelType": self._solderbumps_map[solderbumps_modeling],
            "BondwireMaterial": bondwire_material,
            "BondwireDiameter": bondwire_diameter,
        }

        self.pcb.props["NativeComponentDefinitionProvider"].update(update_properties)
        return True

    def __repr__(self):
        return "Package"


class PCBSettingsDeviceParts(object):
    """Handle device part settings of the PCB component.

    Parameters
    ----------
    pcb_obj : :class:`ansys.aedt.core.modules.layout_boundary.NativeComponentPCB`
            Inherited pcb object.
    app : :class:`pyaedt.Icepak`
            Inherited application object.
    """

    def __init__(self, pcb_obj, app):
        self._app = app
        self.pcb = pcb_obj
        self._filter_map2name = {"Cap": "Capacitors", "Ind": "Inductors", "Res": "Resistors"}

    def __eq__(self, other):
        if isinstance(other, str):
            return other == "Device"
        elif isinstance(other, self.__class__):
            return self.__dict__ == other.__dict__
        else:
            return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __repr__(self):
        return "Device"

    @property
    @pyaedt_function_handler()
    def simplify_parts(self):
        """Get whether parts are simplified as cuboid."""
        return self.pcb.props["NativeComponentDefinitionProvider"]["ModelDeviceAsRect"]

    @simplify_parts.setter
    @pyaedt_function_handler()
    def simplify_parts(self, value):
        """Set whether parts are simplified as cuboid.

        Parameters
        ----------
        value : bool
            Whether parts are simplified as cuboid.
        """
        self.pcb.props["NativeComponentDefinitionProvider"]["ModelDeviceAsRect"] = value

    @property
    @pyaedt_function_handler()
    def surface_material(self):
        """Surface material to apply to parts."""
        return self.pcb.props["NativeComponentDefinitionProvider"]["DeviceSurfaceMaterial"]

    @surface_material.setter
    @pyaedt_function_handler()
    def surface_material(self, value):
        """Set surface material to apply to parts.

        Parameters
        ----------
        value : str
            Surface material to apply to parts.
        """
        self.pcb.props["NativeComponentDefinitionProvider"]["DeviceSurfaceMaterial"] = value

    @property
    @pyaedt_function_handler()
    def footprint_filter(self):
        """Minimum component footprint for filtering."""
        if self.pcb.props["NativeComponentDefinitionProvider"]["PartsChoice"] != 1:
            self._app.logger.error(
                "Device parts modeling is not active.  No filtering or override option is available."
            )
            return None
        if self._app.settings.aedt_version < "2024.2":
            return None
        return self.filters.get("FootPrint", {}).get("Value", None)

    @footprint_filter.setter
    @pyaedt_function_handler()
    @disable_auto_update
    def footprint_filter(self, minimum_footprint):
        """Set minimum component footprint for filtering.

        Parameters
        ----------
        minimum_footprint : str
            Value with unit of the minimum component footprint for filtering.
        """
        if self.pcb.props["NativeComponentDefinitionProvider"]["PartsChoice"] != 1:
            self._app.logger.error(
                "Device parts modeling is not active.  No filtering or override option is available."
            )
            return
        if self._app.settings.aedt_version < "2024.2":
            return
        new_filters = self.pcb.props["NativeComponentDefinitionProvider"].get("Filters", [])
        if "FootPrint" in new_filters:
            new_filters.remove("FootPrint")
        if minimum_footprint is not None:
            new_filters.append("FootPrint")
            self.pcb.props["NativeComponentDefinitionProvider"]["FootPrint"] = minimum_footprint
        self.pcb.props["NativeComponentDefinitionProvider"]["Filters"] = new_filters

    @property
    @pyaedt_function_handler()
    def power_filter(self):
        """Minimum component power for filtering."""
        if self.pcb.props["NativeComponentDefinitionProvider"]["PartsChoice"] != 1:
            self._app.logger.error(
                "Device parts modeling is not active.  No filtering or override option is available."
            )
            return None
        return self.filters.get("Power", {}).get("Value")

    @power_filter.setter
    @pyaedt_function_handler()
    @disable_auto_update
    def power_filter(self, minimum_power):
        """Set minimum component power for filtering.

        Parameters
        ----------
        minimum_power : str
            Value with unit of the minimum component power for filtering.
        """
        if self.pcb.props["NativeComponentDefinitionProvider"]["PartsChoice"] != 1:
            self._app.logger.error(
                "Device parts modeling is not active.  No filtering or override option is available."
            )
            return
        new_filters = self.pcb.props["NativeComponentDefinitionProvider"].get("Filters", [])
        if "Power" in new_filters:
            new_filters.remove("Power")
        if minimum_power is not None:
            new_filters.append("Power")
            self.pcb.props["NativeComponentDefinitionProvider"]["PowerVal"] = minimum_power
        self.pcb.props["NativeComponentDefinitionProvider"]["Filters"] = new_filters

    @property
    @pyaedt_function_handler()
    def type_filters(self):
        """Types of component that are filtered."""
        if self.pcb.props["NativeComponentDefinitionProvider"]["PartsChoice"] != 1:
            self._app.logger.error(
                "Device parts modeling is not active.  No filtering or override option is available."
            )
            return None
        return self.filters.get("Types")

    @type_filters.setter
    @pyaedt_function_handler()
    @disable_auto_update
    def type_filters(self, object_type):
        """Set types of component to filter.

        Parameters
        ----------
        object_type : str or list
            Types of object to filter. Options are ``"Capacitors"``, ``"Inductors"``, and ``"Resistors"``.
        """
        if self.pcb.props["NativeComponentDefinitionProvider"]["PartsChoice"] != 1:
            self._app.logger.error(
                "Device parts modeling is not active.  No filtering or override option is available."
            )
            return
        if not isinstance(object_type, list):
            object_type = [object_type]
        if not all(o in self._filter_map2name.values() for o in object_type):
            self._app.logger.error(
                f"Accepted elements of the list are: {', '.join(list(self._filter_map2name.values()))}"
            )
        else:
            new_filters = self.pcb.props["NativeComponentDefinitionProvider"].get("Filters", [])
            map2arg = {v: k for k, v in self._filter_map2name.items()}
            for f, _ in self._filter_map2name.items():
                if f in new_filters:
                    new_filters.remove(f)
            new_filters += [map2arg[o] for o in object_type]
            self.pcb.props["NativeComponentDefinitionProvider"]["Filters"] = new_filters

    @property
    @pyaedt_function_handler()
    def height_filter(self):
        """Minimum component height for filtering."""
        if self.pcb.props["NativeComponentDefinitionProvider"]["PartsChoice"] != 1:
            self._app.logger.error(
                "Device parts modeling is not active.  No filtering or override option is available."
            )
            return None
        return self.filters.get("Height", {}).get("Value", None)

    @height_filter.setter
    @pyaedt_function_handler()
    @disable_auto_update
    def height_filter(self, minimum_height):
        """Set minimum component height for filtering and whether to filter 2D objects.

        Parameters
        ----------
        minimum_height : str
            Value with unit of the minimum component power for filtering.
        """
        if self.pcb.props["NativeComponentDefinitionProvider"]["PartsChoice"] != 1:
            self._app.logger.error(
                "Device parts modeling is not active.  No filtering or override option is available."
            )
            return
        new_filters = self.pcb.props["NativeComponentDefinitionProvider"].get("Filters", [])
        if "Height" in new_filters:
            new_filters.remove("Height")
        if minimum_height is not None:
            new_filters.append("Height")
            self.pcb.props["NativeComponentDefinitionProvider"]["HeightVal"] = minimum_height
        self.pcb.props["NativeComponentDefinitionProvider"]["Filters"] = new_filters

    @property
    @pyaedt_function_handler()
    def objects_2d_filter(self):
        """Whether 2d objects are filtered."""
        if self.pcb.props["NativeComponentDefinitionProvider"]["PartsChoice"] != 1:
            self._app.logger.error(
                "Device parts modeling is not active.  No filtering or override option is available."
            )
            return None
        return self.filters.get("Exclude2DObjects", False)

    @objects_2d_filter.setter
    @pyaedt_function_handler(filter="enable")
    @disable_auto_update
    def objects_2d_filter(self, enable):
        """Set whether 2d objects are filtered.

        Parameters
        ----------
        enable : bool
            Whether 2d objects are filtered.
        """
        if self.pcb.props["NativeComponentDefinitionProvider"]["PartsChoice"] != 1:
            self._app.logger.error(
                "Device parts modeling is not active.  No filtering or override option is available."
            )
            return
        new_filters = self.pcb.props["NativeComponentDefinitionProvider"].get("Filters", [])
        if "HeightExclude2D" in new_filters:
            new_filters.remove("HeightExclude2D")
        if enable:
            new_filters.append("HeightExclude2D")
        self.pcb.props["NativeComponentDefinitionProvider"]["Filters"] = new_filters

    @property
    @pyaedt_function_handler()
    def filters(self):
        """All active filters."""
        if self.pcb.props["NativeComponentDefinitionProvider"].get("PartsChoice", None) != 1:
            self._app.logger.error(
                "Device parts modeling is not active.  No filtering or override option is available."
            )
            return None
        out_filters = {"Type": {"Capacitors": False, "Inductors": False, "Resistors": False}}
        filters = self.pcb.props["NativeComponentDefinitionProvider"].get("Filters", [])
        filter_map2type = {
            "Cap": "Type",
            "FootPrint": "FootPrint",
            "Height": "Height",
            "HeightExclude2D": None,
            "Ind": "Type",
            "Power": "Power",
            "Res": "Type",
        }
        filter_map2val = {"FootPrint": "FootPrint", "Height": "HeightVal", "Power": "PowerVal"}
        for f in filters:
            if filter_map2type[f] == "Type":
                out_filters["Type"][self._filter_map2name[f]] = True
            elif filter_map2type[f] is not None:
                out_filters[f] = {"Value": filter_map2val[f]}
        if "HeightExclude2D" in filters:
            out_filters["Exclude2DObjects"] = True
        return out_filters

    @property
    @pyaedt_function_handler()
    def overridden_components(self):
        """All overridden components."""
        override_component = (
            self.pcb.props["NativeComponentDefinitionProvider"]
            .get("instanceOverridesMap", {})
            .get("oneOverrideBlk", [])
        )
        return {o["overrideName"]: o["overrideProps"] for o in override_component}

    @pyaedt_function_handler()
    def _override_common(
        self,
        map_name,
        package=None,
        part=None,
        reference_designator=None,
        filter_component=False,
        power=None,
        r_jb=None,
        r_jc=None,
        height=None,
    ):
        override_component = (
            self.pcb.props["NativeComponentDefinitionProvider"]
            .get(map_name, {})  # "instanceOverridesMap"
            .get("oneOverrideBlk", [])
        )
        if map_name == "instanceOverridesMap":
            for o in override_component:
                if o["overrideName"] == reference_designator:
                    override_component.remove(o)
        elif map_name == "definitionOverridesMap":  # pragma: no cover
            for o in override_component:
                if o["overridePartNumberName"] == part:
                    override_component.remove(o)
        new_filter = {}
        if filter_component or any(override_val is not None for override_val in [power, r_jb, r_jc, height]):
            if map_name == "instanceOverridesMap":
                new_filter.update({"overrideName": reference_designator})
            elif map_name == "definitionOverridesMap":  # pragma: no cover
                new_filter.update({"overridePartNumberName": part, "overrideGeometryName": package})
            new_filter.update(
                {
                    "overrideProps": {
                        "isFiltered": filter_component,
                        "isOverridePower": power is not None,
                        "isOverrideThetaJb": r_jb is not None,
                        "isOverrideThetaJc": r_jc is not None,
                        "isOverrideHeight": height is not None,
                        "powerOverride": power if power is not None else "nan",
                        "thetaJbOverride": r_jb if r_jb is not None else "nan",
                        "thetaJcOverride": r_jc if r_jc is not None else "nan",
                        "heightOverride": height if height is not None else "nan",
                    },
                }
            )
            override_component.append(new_filter)
        self.pcb.props["NativeComponentDefinitionProvider"][map_name] = {"oneOverrideBlk": override_component}
        return True

    @pyaedt_function_handler()
    @disable_auto_update
    def override_definition(self, package, part, filter_component=False, power=None, r_jb=None, r_jc=None, height=None):
        """Set component override.

        Parameters
        ----------
        package : str
            Package name of the definition to override.
        part : str
            Part name of the definition to override.
        filter_component : bool, optional
            Whether to filter out the component. The default is ``False``.
        power : str, optional
            Override component power. Default is ``None``, in which case the power is not overridden.
        r_jb : str, optional
            Override component r_jb value. Default is ``None``, in which case the resistance is not overridden.
        r_jc : str, optional
            Override component r_jc value. Default is ``None``, in which case the resistance is not overridden.
        height : str, optional
            Override component height value. Default is ``None``, in which case the height is not overridden.

        Returns
        -------
        bool
            ``True`` if successful, ``False`` otherwise.
        """
        if self._app.settings.aedt_version < "2024.2":
            self._app.logger.error(
                "This method is available only with AEDT 2024 R2 or later. Use 'override_instance()' method instead."
            )
            return False
        return self._override_common(  # pragma : no cover
            "definitionOverridesMap",
            package=package,
            part=part,
            filter_component=filter_component,
            power=power,
            r_jb=r_jb,
            r_jc=r_jc,
            height=height,
        )

    @pyaedt_function_handler()
    @disable_auto_update
    def override_instance(
        self, reference_designator, filter_component=False, power=None, r_jb=None, r_jc=None, height=None
    ):
        """Set instance override.

        Parameters
        ----------
        reference_designator : str
            Reference designator of the instance to override.
        filter_component : bool, optional
            Whether to filter out the component. The default is ``False``.
        power : str, optional
            Override component power. The default is ``None``, in which case the power is not overridden.
        r_jb : str, optional
            Override component r_jb value. The default is ``None``, in which case the resistance is not overridden.
        r_jc : str, optional
            Override component r_jc value. The default is ``None``, in which case the resistance is not overridden.
        height : str, optional
            Override component height value. The default is ``None``, in which case the height is not overridden.

        Returns
        -------
        bool
            ``True`` if successful, ``False`` otherwise.
        """
        return self._override_common(
            "instanceOverridesMap",
            reference_designator=reference_designator,
            filter_component=filter_component,
            power=power,
            r_jb=r_jb,
            r_jc=r_jc,
            height=height,
        )
