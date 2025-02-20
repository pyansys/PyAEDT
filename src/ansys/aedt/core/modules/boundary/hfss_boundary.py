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

from ansys.aedt.core.generic.data_handlers import _dict2arg
from ansys.aedt.core.generic.general_methods import pyaedt_function_handler
from ansys.aedt.core.modeler.cad.elements_3d import BinaryTreeNode
from ansys.aedt.core.modules.boundary.common import BoundaryCommon
from ansys.aedt.core.modules.boundary.common import BoundaryProps


class FieldSetup(BoundaryCommon, BinaryTreeNode):
    """Manages far field and near field component data and execution.

    Examples
    --------
    In this example the sphere1 returned object is a ``ansys.aedt.core.modules.boundary.hfss_boundary.FarFieldSetup``
    >>> from ansys.aedt.core import Hfss
    >>> hfss = Hfss()
    >>> sphere1 = hfss.insert_infinite_sphere()
    >>> sphere1.props["ThetaStart"] = "-90deg"
    >>> sphere1.props["ThetaStop"] = "90deg"
    >>> sphere1.props["ThetaStep"] = "2deg"
    >>> sphere1.delete()
    """

    def __init__(self, app, component_name, props, component_type):
        self.auto_update = False
        self._app = app
        self.type = component_type
        self._name = component_name
        self.__props = BoundaryProps(self, props) if props else {}
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
        design_childs = self._app.get_oo_name(self._app.odesign)

        if "Radiation" in design_childs:
            cc = self._app.get_oo_object(self._app.odesign, "Radiation")
            cc_names = self._app.get_oo_name(cc)
            if self._name in cc_names:
                child_object = cc.GetChildObject(self._name)
        return child_object

    @property
    def props(self):
        """Field Properties."""
        if not self.__props and self._app.design_properties:
            if (
                self.type == "FarFieldSphere"
                and self._app.design_properties.get("RadField")
                and self._app.design_properties["RadField"].get("FarFieldSetups")
            ):
                for val in self._app.design_properties["RadField"]["FarFieldSetups"]:
                    if val == self.name:
                        self.__props = self._app.design_properties["RadField"]["FarFieldSetups"][val]
            elif self.type != "FarFieldSphere" and self._app.design_properties["RadField"].get("NearFieldSetups"):
                for val in self._app.design_properties["RadField"]["NearFieldSetups"]:
                    if val == self.name:
                        self.__props = self._app.design_properties["RadField"]["NearFieldSetups"][val]
            self.__props = BoundaryProps(self, self.__props)
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
                self.properties["Name"] = value
            except KeyError:
                self._app.logger.error("Name %s already assigned in the design", value)

    @pyaedt_function_handler()
    def _get_args(self, props=None):
        if props is None:
            props = self.props
        arg = ["NAME:" + self.name]
        _dict2arg(props, arg)
        return arg

    @pyaedt_function_handler()
    def create(self):
        """Create a Field Setup Component in HFSS.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        if self.type == "FarFieldSphere":
            self._app.oradfield.InsertInfiniteSphereSetup(self._get_args())
        elif self.type == "NearFieldBox":
            self._app.oradfield.InsertBoxSetup(self._get_args())
        elif self.type == "NearFieldSphere":
            self._app.oradfield.InsertSphereSetup(self._get_args())
        elif self.type == "NearFieldRectangle":
            self._app.oradfield.InsertRectangleSetup(self._get_args())
        elif self.type == "NearFieldLine":
            self._app.oradfield.InsertLineSetup(self._get_args())
        elif self.type == "AntennaOverlay":
            self._app.oradfield.AddAntennaOverlay(self._get_args())
        elif self.type == "FieldSourceGroup":
            self._app.oradfield.AddRadFieldSourceGroup(self._get_args())
        return self._initialize_tree_node()

    @pyaedt_function_handler()
    def update(self):
        """Update the Field Setup in AEDT.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if self.type == "FarFieldSphere":
            self._app.oradfield.EditInfiniteSphereSetup(self.name, self._get_args())
        elif self.type == "NearFieldBox":
            self._app.oradfield.EditBoxSetup(self.name, self._get_args())
        elif self.type == "NearFieldSphere":
            self._app.oradfield.EditSphereSetup(self.name, self._get_args())
        elif self.type == "NearFieldRectangle":
            self._app.oradfield.EditRectangleSetup(self.name, self._get_args())
        elif self.type == "NearFieldLine":
            self._app.oradfield.EditLineSetup(self.name, self._get_args())
        elif self.type == "AntennaOverlay":
            self._app.oradfield.EditAntennaOverlay(self.name, self._get_args())
        elif self.type == "FieldSourceGroup":
            self._app.oradfield.EditRadFieldSourceGroup(self._get_args())
        return True

    @pyaedt_function_handler()
    def delete(self):
        """Delete the Field Setup in AEDT.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        self._app.oradfield.DeleteSetup([self.name])
        for el in self._app.field_setups:
            if el.name == self.name:
                self._app.field_setups.remove(el)
        return True


class FarFieldSetup(FieldSetup, object):
    """Manages Far Field Component data and execution.

    Examples
    --------
    in this example the sphere1 returned object is a ``ansys.aedt.core.modules.boundary.hfss_boundary.FarFieldSetup``
    >>> from ansys.aedt.core import Hfss
    >>> hfss = Hfss()
    >>> sphere1 = hfss.insert_infinite_sphere()
    >>> sphere1.props["ThetaStart"] = "-90deg"
    >>> sphere1.props["ThetaStop"] = "90deg"
    >>> sphere1.props["ThetaStep"] = "2deg"
    >>> sphere1.delete()
    """

    def __init__(self, app, component_name, props, component_type, units="deg"):
        FieldSetup.__init__(self, app, component_name, props, component_type)
        self.units = units

    @property
    def definition(self):
        """Set/Get the Far Field Angle Definition."""
        return self.props["CSDefinition"]

    @definition.setter
    def definition(self, value):
        actual_value = self.props["CSDefinition"]
        self.props["CSDefinition"] = value
        actual_defs = None
        defs = None
        if actual_value != value and value == "Theta-Phi":
            defs = ["ThetaStart", "ThetaStop", "ThetaStep", "PhiStart", "PhiStop", "PhiStep"]
            actual_defs = [
                "AzimuthStart",
                "AzimuthStop",
                "AzimuthStep",
                "ElevationStart",
                "ElevationStop",
                "ElevationStep",
            ]
        elif actual_value != value and value == "El Over Az":
            defs = ["AzimuthStart", "AzimuthStop", "AzimuthStep", "ElevationStart", "ElevationStop", "ElevationStep"]
            if actual_value == "Theta-Phi":
                actual_defs = ["ThetaStart", "ThetaStop", "ThetaStep", "PhiStart", "PhiStop", "PhiStep"]
            else:
                actual_defs = [
                    "AzimuthStart",
                    "AzimuthStop",
                    "AzimuthStep",
                    "ElevationStart",
                    "ElevationStop",
                    "ElevationStep",
                ]
        elif actual_value != value:
            defs = ["ElevationStart", "ElevationStop", "ElevationStep", "AzimuthStart", "AzimuthStop", "AzimuthStep"]
            if actual_value == "Theta-Phi":
                actual_defs = ["ThetaStart", "ThetaStop", "ThetaStep", "PhiStart", "PhiStop", "PhiStep"]
            else:
                actual_defs = [
                    "ElevationStart",
                    "ElevationStop",
                    "ElevationStep",
                    "AzimuthStart",
                    "AzimuthStop",
                    "AzimuthStep",
                ]
        if actual_defs != defs:
            self.props[defs[0]] = self.props[actual_defs[0]]
            self.props[defs[1]] = self.props[actual_defs[1]]
            self.props[defs[2]] = self.props[actual_defs[2]]
            self.props[defs[3]] = self.props[actual_defs[3]]
            self.props[defs[4]] = self.props[actual_defs[4]]
            self.props[defs[5]] = self.props[actual_defs[5]]
            del self.props[actual_defs[0]]
            del self.props[actual_defs[1]]
            del self.props[actual_defs[2]]
            del self.props[actual_defs[3]]
            del self.props[actual_defs[4]]
            del self.props[actual_defs[5]]
        self.update()

    @property
    def use_custom_radiation_surface(self):
        """Set/Get the Far Field Radiation Surface Enable."""
        return self.props["UseCustomRadiationSurface"]

    @use_custom_radiation_surface.setter
    def use_custom_radiation_surface(self, value):
        self.props["UseCustomRadiationSurface"] = value
        self.update()

    @property
    def custom_radiation_surface(self):
        """Set/Get the Far Field Radiation Surface FaceList."""
        return self.props["CustomRadiationSurface"]

    @custom_radiation_surface.setter
    def custom_radiation_surface(self, value):
        if value:
            self.props["UseCustomRadiationSurface"] = True
            self.props["CustomRadiationSurface"] = value
        else:
            self.props["UseCustomRadiationSurface"] = False
            self.props["CustomRadiationSurface"] = ""
        self.update()

    @property
    def use_local_coordinate_system(self):
        """Set/Get the usage of a custom Coordinate System."""
        return self.props["UseLocalCS"]

    @use_local_coordinate_system.setter
    def use_local_coordinate_system(self, value):
        self.props["UseLocalCS"] = value
        self.update()

    @property
    def local_coordinate_system(self):
        """Set/Get the custom Coordinate System name."""
        try:
            return self.properties["Coordinate System"]
        except Exception:  # pragma: no cover
            return None

    @local_coordinate_system.setter
    def local_coordinate_system(self, value):
        if value:
            self.props["UseLocalCS"] = True
            self.props["CoordSystem"] = value
        else:
            self.props["UseLocalCS"] = False
            self.props["CoordSystem"] = ""
        self.update()

    @property
    def polarization(self):
        """Set/Get the Far Field Polarization."""
        return self.props["Polarization"]

    @polarization.setter
    def polarization(self, value):
        self.props["Polarization"] = value
        self.update()

    @property
    def slant_angle(self):
        """Set/Get the Far Field Slant Angle if Polarization is Set to `Slant`."""

        if self.props["Polarization"] == "Slant":
            return self.props["SlantAngle"]
        else:
            return

    @slant_angle.setter
    def slant_angle(self, value):
        self.props["Polarization"] = "Slant"
        self.props["SlantAngle"] = value
        self.update()

    @property
    def theta_start(self):
        """Set/Get the Far Field Theta Start Angle if Definition is Set to `Theta-Phi`."""

        if "ThetaStart" in self.props:
            return self.props["ThetaStart"]
        else:
            return

    @property
    def theta_stop(self):
        """Set/Get the Far Field Theta Stop Angle if Definition is Set to `Theta-Phi`."""

        if "ThetaStop" in self.props:
            return self.props["ThetaStop"]
        else:
            return

    @property
    def theta_step(self):
        """Set/Get the Far Field Theta Step Angle if Definition is Set to `Theta-Phi`."""

        if "ThetaStep" in self.props:
            return self.props["ThetaStep"]
        else:
            return

    @property
    def phi_start(self):
        """Set/Get the Far Field Phi Start Angle if Definition is Set to `Theta-Phi`."""

        if "PhiStart" in self.props:
            return self.props["PhiStart"]
        else:
            return

    @property
    def phi_stop(self):
        """Set/Get the Far Field Phi Stop Angle if Definition is Set to `Theta-Phi`."""

        if "PhiStop" in self.props:
            return self.props["PhiStop"]
        else:
            return

    @property
    def phi_step(self):
        """Set/Get the Far Field Phi Step Angle if Definition is Set to `Theta-Phi`."""

        if "PhiStep" in self.props:
            return self.props["PhiStep"]
        else:
            return

    @property
    def azimuth_start(self):
        """Set/Get the Far Field Azimuth Start Angle if Definition is Set to `Az Over El` or `El Over Az`."""

        if "AzimuthStart" in self.props:
            return self.props["AzimuthStart"]
        else:
            return

    @property
    def azimuth_stop(self):
        """Set/Get the Far Field Azimuth Stop Angle if Definition is Set to `Az Over El` or `El Over Az`."""

        if "AzimuthStop" in self.props:
            return self.props["AzimuthStop"]
        else:
            return

    @property
    def azimuth_step(self):
        """Set/Get the Far Field Azimuth Step Angle if Definition is Set to `Az Over El` or `El Over Az`."""

        if "AzimuthStep" in self.props:
            return self.props["AzimuthStep"]
        else:
            return

    @property
    def elevation_start(self):
        """Set/Get the Far Field Elevation Start Angle if Definition is Set to `Az Over El` or `El Over Az`."""

        if "ElevationStart" in self.props:
            return self.props["ElevationStart"]
        else:
            return

    @property
    def elevation_stop(self):
        """Set/Get the Far Field Elevation Stop Angle if Definition is Set to `Az Over El` or `El Over Az`."""

        if "ElevationStop" in self.props:
            return self.props["ElevationStop"]
        else:
            return

    @property
    def elevation_step(self):
        """Set/Get the Far Field Elevation Step Angle if Definition is Set to `Az Over El` or `El Over Az`."""

        if "ElevationStep" in self.props:
            return self.props["ElevationStep"]
        else:
            return

    @theta_start.setter
    def theta_start(self, value):
        if "ThetaStart" in self.props:
            self.props["ThetaStart"] = self._app.value_with_units(value, self.units)
            self.update()

    @theta_stop.setter
    def theta_stop(self, value):
        if "ThetaStop" in self.props:
            self.props["ThetaStop"] = self._app.value_with_units(value, self.units)
            self.update()

    @theta_step.setter
    def theta_step(self, value):
        if "ThetaStep" in self.props:
            self.props["ThetaStep"] = self._app.value_with_units(value, self.units)
            self.update()

    @phi_start.setter
    def phi_start(self, value):
        if "PhiStart" in self.props:
            self.props["PhiStart"] = self._app.value_with_units(value, self.units)
            self.update()

    @phi_stop.setter
    def phi_stop(self, value):
        if "PhiStop" in self.props:
            self.props["PhiStop"] = self._app.value_with_units(value, self.units)
            self.update()

    @phi_step.setter
    def phi_step(self, value):
        if "PhiStep" in self.props:
            self.props["PhiStep"] = self._app.value_with_units(value, self.units)
            self.update()

    @azimuth_start.setter
    def azimuth_start(self, value):
        if "AzimuthStart" in self.props:
            self.props["AzimuthStart"] = self._app.value_with_units(value, self.units)
            self.update()

    @azimuth_stop.setter
    def azimuth_stop(self, value):
        if "AzimuthStop" in self.props:
            self.props["AzimuthStop"] = self._app.value_with_units(value, self.units)
            self.update()

    @azimuth_step.setter
    def azimuth_step(self, value):
        if "AzimuthStep" in self.props:
            self.props["AzimuthStep"] = self._app.value_with_units(value, self.units)
            self.update()

    @elevation_start.setter
    def elevation_start(self, value):
        if "ElevationStart" in self.props:
            self.props["ElevationStart"] = self._app.value_with_units(value, self.units)
            self.update()

    @elevation_stop.setter
    def elevation_stop(self, value):
        if "ElevationStop" in self.props:
            self.props["ElevationStop"] = self._app.value_with_units(value, self.units)
            self.update()

    @elevation_step.setter
    def elevation_step(self, value):
        if "ElevationStep" in self.props:
            self.props["ElevationStep"] = self._app.value_with_units(value, self.units)
            self.update()


class NearFieldSetup(FieldSetup, object):
    """Manages Near Field Component data and execution.

    Examples
    --------
    In this example the rectangle1 returned object is a
    ``ansys.aedt.core.modules.boundary.hfss_boundary.NearFieldSetup``

    >>> from ansys.aedt.core import Hfss
    >>> hfss = Hfss()
    >>> rectangle1 = hfss.insert_near_field_rectangle()
    """

    def __init__(self, app, component_name, props, component_type):
        FieldSetup.__init__(self, app, component_name, props, component_type)
