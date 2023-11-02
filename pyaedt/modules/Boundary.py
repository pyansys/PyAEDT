"""This module contains these classes: `BoundaryCommon` and `BoundaryObject`.
"""
from collections import OrderedDict
import copy
import re

from pyaedt.application.Variables import decompose_variable_value
from pyaedt.generic.constants import CATEGORIESQ3D
from pyaedt.generic.DataHandlers import _dict2arg, random_string
from pyaedt.generic.general_methods import (
    PropsManager,
    _dim_arg,
    filter_tuple,
    generate_unique_name,
    pyaedt_function_handler,
)
from pyaedt.modeler.cad.elements3d import EdgePrimitive, FacePrimitive, VertexPrimitive
from pyaedt.modules.CircuitTemplates import SourceKeys


class BoundaryProps(OrderedDict):
    """AEDT Boundary Component Internal Parameters."""

    def __setitem__(self, key, value):
        OrderedDict.__setitem__(self, key, value)
        if self._pyaedt_boundary.auto_update:
            if key in ["Edges", "Faces", "Objects"]:
                res = self._pyaedt_boundary.update_assignment()
            else:
                res = self._pyaedt_boundary.update()
            if not res:
                self._pyaedt_boundary._app.logger.warning("Update of %s Failed. Check needed arguments", key)

    def __init__(self, boundary, props):
        OrderedDict.__init__(self)
        if props:
            for key, value in props.items():
                if isinstance(value, (OrderedDict, dict)):
                    OrderedDict.__setitem__(self, key, BoundaryProps(boundary, value))
                elif isinstance(value, list):
                    list_els = []
                    for el in value:
                        if isinstance(el, (OrderedDict, dict)):
                            list_els.append(BoundaryProps(boundary, el))
                        else:
                            list_els.append(el)
                    OrderedDict.__setitem__(self, key, list_els)
                else:
                    OrderedDict.__setitem__(self, key, value)
        self._pyaedt_boundary = boundary

    def _setitem_without_update(self, key, value):
        OrderedDict.__setitem__(self, key, value)


class BoundaryCommon(PropsManager):
    """ """

    @pyaedt_function_handler()
    def _get_args(self, props=None):
        """Retrieve boundary properties.

        Parameters
        ----------
        props : dict, optional
             The default is ``None``.

        Returns
        -------
        dict
            Dictionary of boundary properties.

        """
        if not props:
            props = self.props
        arg = ["NAME:" + self.name]
        _dict2arg(props, arg)
        return arg

    @pyaedt_function_handler()
    def delete(self):
        """Delete the boundary.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        if self.type == "Matrix" or self.type == "Force" or self.type == "Torque":
            self._app.o_maxwell_parameters.DeleteParameters([self.name])
        else:
            self._app.oboundary.DeleteBoundaries([self.name])
        for el in self._app.boundaries:
            if el.name == self.name:
                self._app.boundaries.remove(el)
        return True

    def _get_boundary_data(self, ds):
        try:
            if "MaxwellParameterSetup" in self._app.design_properties:
                param = "MaxwellParameters"
                setup = "MaxwellParameterSetup"
                if isinstance(self._app.design_properties[setup][param][ds], (OrderedDict, dict)):
                    return [
                        self._app.design_properties["MaxwellParameterSetup"]["MaxwellParameters"][ds],
                        self._app.design_properties["MaxwellParameterSetup"]["MaxwellParameters"][ds][
                            "MaxwellParameterType"
                        ],
                    ]
        except:
            pass
        try:
            if "MotionSetupList" in self._app.design_properties["ModelSetup"]:
                motion_list = "MotionSetupList"
                setup = "ModelSetup"
                # check moving part
                if isinstance(self._app.design_properties[setup][motion_list][ds], (OrderedDict, dict)):
                    return [
                        self._app.design_properties["ModelSetup"]["MotionSetupList"][ds],
                        self._app.design_properties["ModelSetup"]["MotionSetupList"][ds]["MotionType"],
                    ]
        except:
            pass
        try:
            if ds in self._app.design_properties["BoundarySetup"]["Boundaries"]:
                if (
                    self._app.design_properties["BoundarySetup"]["Boundaries"][ds]["BoundType"] == "Network"
                    and self._app.design_type == "Icepak"
                ):
                    return [self._app.design_properties["BoundarySetup"]["Boundaries"][ds], ""]
                else:
                    return [
                        self._app.design_properties["BoundarySetup"]["Boundaries"][ds],
                        self._app.design_properties["BoundarySetup"]["Boundaries"][ds]["BoundType"],
                    ]
        except:
            return []


class NativeComponentObject(BoundaryCommon, object):
    """Manages Native Component data and execution.

    Parameters
    ----------
    app : object
        An AEDT application from ``pyaedt.application``.
    component_type : str
        Type of the component.
    component_name : str
        Name of the component.
    props : dict
        Properties of the boundary.

    Examples
    --------
    in this example the par_beam returned object is a ``pyaedt.modules.Boundary.NativeComponentObject``
    >>> from pyaedt import Hfss
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
        self.name = "InsertNativeComponentData"
        self.component_name = component_name

        self.props = BoundaryProps(
            self,
            OrderedDict(
                {
                    "TargetCS": "Global",
                    "SubmodelDefinitionName": self.component_name,
                    "ComponentPriorityLists": OrderedDict({}),
                    "NextUniqueID": 0,
                    "MoveBackwards": False,
                    "DatasetType": "ComponentDatasetType",
                    "DatasetDefinitions": OrderedDict({}),
                    "BasicComponentInfo": OrderedDict(
                        {
                            "ComponentName": self.component_name,
                            "Company": "",
                            "Company URL": "",
                            "Model Number": "",
                            "Help URL": "",
                            "Version": "1.0",
                            "Notes": "",
                            "IconType": "",
                        }
                    ),
                    "GeometryDefinitionParameters": OrderedDict({"VariableOrders": OrderedDict({})}),
                    "DesignDefinitionParameters": OrderedDict({"VariableOrders": OrderedDict({})}),
                    "MaterialDefinitionParameters": OrderedDict({"VariableOrders": OrderedDict({})}),
                    "MapInstanceParameters": "DesignVariable",
                    "UniqueDefinitionIdentifier": "89d26167-fb77-480e-a7ab-"
                    + random_string(12, char_set="abcdef0123456789"),
                    "OriginFilePath": "",
                    "IsLocal": False,
                    "ChecksumString": "",
                    "ChecksumHistory": [],
                    "VersionHistory": [],
                    "NativeComponentDefinitionProvider": OrderedDict({"Type": component_type}),
                    "InstanceParameters": OrderedDict(
                        {"GeometryParameters": "", "MaterialParameters": "", "DesignParameters": ""}
                    ),
                }
            ),
        )
        if props:
            self._update_props(self.props, props)
        self.native_properties = self.props["NativeComponentDefinitionProvider"]
        self.auto_update = True

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
            if isinstance(v, (dict, OrderedDict)):
                if k not in d:
                    d[k] = OrderedDict({})
                d[k] = self._update_props(d[k], v)
            else:
                d[k] = v
        return d

    @pyaedt_function_handler()
    def _get_args(self, props=None):
        if props is None:
            props = self.props
        arg = ["NAME:" + self.name]
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
        except Exception:  # pragma: no cover
            names = []
        self.name = self._app.modeler.oeditor.InsertNativeComponent(self._get_args())
        try:
            a = [i for i in self._app.excitations if i not in names]
            self.excitation_name = a[0].split(":")[0]
        except Exception:
            self.excitation_name = self.name
        return True

    @pyaedt_function_handler()
    def update(self):
        """Update the Native Component in AEDT.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        self.update_props = OrderedDict({})
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
            if el.component_name == self.component_name:
                self._app._native_components.remove(el)
                del self._app.modeler.user_defined_components[self.name]
                self._app.modeler.cleanup_objects()
        return True


class BoundaryObject(BoundaryCommon, object):
    """Manages boundary data and execution.

    Parameters
    ----------
    app : object
        An AEDT application from ``pyaedt.application``.
    name : str
        Name of the boundary.
    props : dict, optional
        Properties of the boundary.
    boundarytype : str, optional
        Type of the boundary.

    Examples
    --------
    Create a cylinder at the XY working plane and assign a copper coating of 0.2 mm to it. The Coating is a boundary
    operation and coat will return a ``pyaedt.modules.Boundary.BoundaryObject``

    >>> from pyaedt import Hfss
    >>> hfss =Hfss()
    >>> origin = hfss.modeler.Position(0, 0, 0)
    >>> inner = hfss.modeler.create_cylinder(hfss.PLANE.XY, origin, 3, 200, 0, "inner")
    >>> inner_id = hfss.modeler.get_obj_id("inner")
    >>> coat = hfss.assign_coating([inner_id], "copper", usethickness=True, thickness="0.2mm")
    """

    def __init__(self, app, name, props=None, boundarytype=None, auto_update=True):
        self.auto_update = False
        self._app = app
        self._name = name
        self._props = None
        if props:
            self._props = BoundaryProps(self, OrderedDict(props))
        self._type = boundarytype
        self._boundary_name = self.name
        self.auto_update = auto_update

    @property
    def object_properties(self):
        """Object-oriented properties.

        Returns
        -------
        class:`pyaedt.modeler.cad.elements3d.BinaryTreeNode`

        """
        from pyaedt.modeler.cad.elements3d import BinaryTreeNode

        child_object = None
        design_childs = self._app.get_oo_name(self._app.odesign)

        if "Thermal" in design_childs:
            cc = self._app.get_oo_object(self._app.odesign, "Thermal")
            cc_names = self._app.get_oo_name(cc)
            if self.name in cc_names:
                child_object = cc_names
            if child_object:
                return BinaryTreeNode(self.name, child_object, False)
        elif "Boundaries" in design_childs:
            cc = self._app.get_oo_object(self._app.odesign, "Boundaries")
            if self.name in cc.GetChildNames():
                child_object = cc.GetChildObject(self.name)
            elif "Excitations" in design_childs and self.name in self._app.get_oo_name(
                self._app.odesign, "Excitations"
            ):
                child_object = self._app.get_oo_object(self._app.odesign, "Excitations").GetChildObject(self.name)
            elif self._app.design_type in ["Maxwell 3D", "Maxwell 2D"] and "Model" in design_childs:
                model = self._app.get_oo_object(self._app.odesign, "Model")
                if self.name in model.GetChildNames():
                    child_object = model.GetChildObject(self.name)
            elif "Excitations" in design_childs and self._app.get_oo_name(self._app.odesign, "Excitations"):
                for port in self._app.get_oo_name(self._app.odesign, "Excitations"):
                    terminals = self._app.get_oo_name(self._app.odesign, "Excitations\\{}".format(port))
                    if self.name in terminals:
                        child_object = self._app.get_oo_object(
                            self._app.odesign, "Excitations\\{}\\{}".format(port, self.name)
                        )
            elif "Conductors" in design_childs and self._app.get_oo_name(self._app.odesign, "Conductors"):
                for port in self._app.get_oo_name(self._app.odesign, "Conductors"):
                    if self.name == port:
                        child_object = self._app.get_oo_object(self._app.odesign, "Conductors\\{}".format(port))

        if child_object:
            return BinaryTreeNode(self.name, child_object, False)

        return False

    @property
    def props(self):
        """Boundary data.

        Returns
        -------
        :class:BoundaryProps
        """
        if self._props:
            return self._props
        props = self._get_boundary_data(self.name)

        if props:
            self._props = BoundaryProps(self, OrderedDict(props[0]))
            self._type = props[1]
        return self._props

    @property
    def type(self):
        """Boundary type.

        Returns
        -------
        str
            Returns the type of the boundary.
        """
        if not self._type:
            if self.available_properties:
                if "Type" in self.available_properties:
                    self._type = self.props["Type"]
                elif "BoundType" in self.available_properties:
                    self._type = self.props["BoundType"]
            elif self.object_properties and self.object_properties.props["Type"]:
                self._type = self.object_properties.props["Type"]

        if self._app.design_type == "Icepak" and self._type == "Source":
            return "SourceIcepak"
        else:
            return self._type

    @type.setter
    def type(self, value):
        self._type = value

    @property
    def name(self):
        """Boundary Name."""
        return self._name

    @name.setter
    def name(self, value):
        self._name = value
        self.update()

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
    def create(self):
        """Create a boundary.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        bound_type = self.type
        if bound_type == "Perfect E":
            self._app.oboundary.AssignPerfectE(self._get_args())
        elif bound_type == "Perfect H":
            self._app.oboundary.AssignPerfectH(self._get_args())
        elif bound_type == "Aperture":
            self._app.oboundary.AssignAperture(self._get_args())
        elif bound_type == "Radiation":
            self._app.oboundary.AssignRadiation(self._get_args())
        elif bound_type == "Finite Conductivity":
            self._app.oboundary.AssignFiniteCond(self._get_args())
        elif bound_type == "Lumped RLC":
            self._app.oboundary.AssignLumpedRLC(self._get_args())
        elif bound_type == "Impedance":
            self._app.oboundary.AssignImpedance(self._get_args())
        elif bound_type == "Layered Impedance":
            self._app.oboundary.AssignLayeredImp(self._get_args())
        elif bound_type == "Anisotropic Impedance":
            self._app.oboundary.AssignAnisotropicImpedance(self._get_args())
        elif bound_type == "Primary":
            self._app.oboundary.AssignPrimary(self._get_args())
        elif bound_type == "Secondary":
            self._app.oboundary.AssignSecondary(self._get_args())
        elif bound_type == "Lattice Pair":
            self._app.oboundary.AssignLatticePair(self._get_args())
        elif bound_type == "HalfSpace":
            self._app.oboundary.AssignHalfSpace(self._get_args())
        elif bound_type == "Multipaction SEE":
            self._app.oboundary.AssignMultipactionSEE(self._get_args())
        elif bound_type == "Fresnel":
            self._app.oboundary.AssignFresnel(self._get_args())
        elif bound_type == "Symmetry":
            self._app.oboundary.AssignSymmetry(self._get_args())
        elif bound_type == "Zero Tangential H Field":
            self._app.oboundary.AssignZeroTangentialHField(self._get_args())
        elif bound_type == "Zero Integrated Tangential H Field":
            self._app.oboundary.AssignIntegratedZeroTangentialHField(self._get_args())
        elif bound_type == "Tangential H Field":
            self._app.oboundary.AssignTangentialHField(self._get_args())
        elif bound_type == "Insulating":
            self._app.oboundary.AssignInsulating(self._get_args())
        elif bound_type == "Independent":
            self._app.oboundary.AssignIndependent(self._get_args())
        elif bound_type == "Dependent":
            self._app.oboundary.AssignDependent(self._get_args())
        elif bound_type == "Band":
            self._app.omodelsetup.AssignBand(self._get_args())
        elif bound_type == "InfiniteGround":
            self._app.oboundary.AssignInfiniteGround(self._get_args())
        elif bound_type == "ThinConductor":
            self._app.oboundary.AssignThinConductor(self._get_args())
        elif bound_type == "Stationary Wall":
            self._app.oboundary.AssignStationaryWallBoundary(self._get_args())
        elif bound_type == "Symmetry Wall":
            self._app.oboundary.AssignSymmetryWallBoundary(self._get_args())
        elif bound_type == "Resistance":
            self._app.oboundary.AssignResistanceBoundary(self._get_args())
        elif bound_type == "Conducting Plate":
            self._app.oboundary.AssignConductingPlateBoundary(self._get_args())
        elif bound_type == "Adiabatic Plate":
            self._app.oboundary.AssignAdiabaticPlateBoundary(self._get_args())
        elif bound_type == "Network":
            self._app.oboundary.AssignNetworkBoundary(self._get_args())
        elif bound_type == "Grille":
            self._app.oboundary.AssignGrilleBoundary(self._get_args())
        elif bound_type == "Block":
            self._app.oboundary.AssignBlockBoundary(self._get_args())
        elif bound_type == "SourceIcepak":
            self._app.oboundary.AssignSourceBoundary(self._get_args())
        elif bound_type == "Opening":
            self._app.oboundary.AssignOpeningBoundary(self._get_args())
        elif bound_type == "EMLoss":
            self._app.oboundary.AssignEMLoss(self._get_args())
        elif bound_type == "ThermalCondition":
            self._app.oboundary.AssignThermalCondition(self._get_args())
        elif bound_type == "Convection":
            self._app.oboundary.AssignConvection(self._get_args())
        elif bound_type == "HeatFlux":
            self._app.oboundary.AssignHeatFlux(self._get_args())
        elif bound_type == "HeatGeneration":
            self._app.oboundary.AssignHeatGeneration(self._get_args())
        elif bound_type == "Temperature":
            self._app.oboundary.AssignTemperature(self._get_args())
        elif bound_type == "RotatingFluid":
            self._app.oboundary.AssignRotatingFluid(self._get_args())
        elif bound_type == "Frictionless":
            self._app.oboundary.AssignFrictionlessSupport(self._get_args())
        elif bound_type == "FixedSupport":
            self._app.oboundary.AssignFixedSupport(self._get_args())
        elif bound_type == "Voltage":
            self._app.oboundary.AssignVoltage(self._get_args())
        elif bound_type == "VoltageDrop":
            self._app.oboundary.AssignVoltageDrop(self._get_args())
        elif bound_type == "Current":
            self._app.oboundary.AssignCurrent(self._get_args())
        elif bound_type == "CurrentDensity":
            self._app.oboundary.AssignCurrentDensity(self._get_args())
        elif bound_type == "CurrentDensityGroup":
            self._app.oboundary.AssignCurrentDensityGroup(self._get_args()[2], self._get_args()[3])
        elif bound_type == "CurrentDensityTerminal":
            self._app.oboundary.AssignCurrentDensityTerminal(self._get_args())
        elif bound_type == "CurrentDensityTerminalGroup":
            self._app.oboundary.AssignCurrentDensityTerminalGroup(self._get_args()[2], self._get_args()[3])
        elif bound_type == "Balloon":
            self._app.oboundary.AssignBalloon(self._get_args())
        elif bound_type == "Winding" or bound_type == "Winding Group":
            self._app.oboundary.AssignWindingGroup(self._get_args())
        elif bound_type == "Vector Potential":
            self._app.oboundary.AssignVectorPotential(self._get_args())
        elif bound_type == "CoilTerminal" or bound_type == "Coil Terminal":
            self._app.oboundary.AssignCoilTerminal(self._get_args())
        elif bound_type == "Coil":
            self._app.oboundary.AssignCoil(self._get_args())
        elif bound_type == "Source":
            self._app.oboundary.AssignSource(self._get_args())
        elif bound_type == "Sink":
            self._app.oboundary.AssignSink(self._get_args())
        elif bound_type == "SignalNet":
            self._app.oboundary.AssignSignalNet(self._get_args())
        elif bound_type == "GroundNet":
            self._app.oboundary.AssignGroundNet(self._get_args())
        elif bound_type == "FloatingNet":
            self._app.oboundary.AssignFloatingNet(self._get_args())
        elif bound_type == "SignalLine":
            self._app.oboundary.AssignSingleSignalLine(self._get_args())
        elif bound_type == "ReferenceGround":
            self._app.oboundary.AssignSingleReferenceGround(self._get_args())
        elif bound_type == "Circuit Port":
            self._app.oboundary.AssignCircuitPort(self._get_args())
        elif bound_type == "Lumped Port":
            self._app.oboundary.AssignLumpedPort(self._get_args())
        elif bound_type == "Wave Port":
            self._app.oboundary.AssignWavePort(self._get_args())
        elif bound_type == "Floquet Port":
            self._app.oboundary.AssignFloquetPort(self._get_args())
        elif bound_type == "AutoIdentify":
            # Build reference conductor argument as a list of strings
            # ref_cond_arg should be a list.
            ref_cond_arg = ["NAME:ReferenceConductors"] + self.props["ReferenceConductors"]
            self._app.oboundary.AutoIdentifyPorts(
                ["NAME:Faces", self.props["Faces"]],
                self.props["IsWavePort"],
                ref_cond_arg,
                self.name,
                self.props["RenormalizeModes"],
            )
        elif bound_type == "SBRTxRxSettings":
            self._app.oboundary.SetSBRTxRxSettings(self._get_args())
        elif bound_type == "EndConnection":
            self._app.oboundary.AssignEndConnection(self._get_args())
        elif bound_type == "Hybrid":
            self._app.oboundary.AssignHybridRegion(self._get_args())
        elif bound_type == "FluxTangential":
            self._app.oboundary.AssignFluxTangential(self._get_args())
        else:
            return False
        return True

    @pyaedt_function_handler()
    def update(self):
        """Update the boundary.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        bound_type = self.type
        if bound_type == "Perfect E":
            self._app.oboundary.EditPerfectE(self._boundary_name, self._get_args())
        elif bound_type == "Perfect H":
            self._app.oboundary.EditPerfectH(self._boundary_name, self._get_args())
        elif bound_type == "Aperture":
            self._app.oboundary.EditAperture(self._boundary_name, self._get_args())
        elif bound_type == "Radiation":
            self._app.oboundary.EditRadiation(self._boundary_name, self._get_args())
        elif bound_type == "Finite Conductivity":
            self._app.oboundary.EditFiniteCond(self._boundary_name, self._get_args())
        elif bound_type == "Lumped RLC":
            self._app.oboundary.EditLumpedRLC(self._boundary_name, self._get_args())
        elif bound_type == "Impedance":
            self._app.oboundary.EditImpedance(self._boundary_name, self._get_args())
        elif bound_type == "Layered Impedance":
            self._app.oboundary.EditLayeredImpedance(self._boundary_name, self._get_args())
        elif bound_type == "Anisotropic Impedance":
            self._app.oboundary.EditAssignAnisotropicImpedance(
                self._boundary_name, self._get_args()
            )  # pragma: no cover
        elif bound_type == "Primary":
            self._app.oboundary.EditPrimary(self._boundary_name, self._get_args())
        elif bound_type == "Secondary":
            self._app.oboundary.EditSecondary(self._boundary_name, self._get_args())
        elif bound_type == "Lattice Pair":
            self._app.oboundary.EditLatticePair(self._boundary_name, self._get_args())
        elif bound_type == "HalfSpace":
            self._app.oboundary.EditHalfSpace(self._boundary_name, self._get_args())
        elif bound_type == "Multipaction SEE":
            self._app.oboundary.EditMultipactionSEE(self._boundary_name, self._get_args())  # pragma: no cover
        elif bound_type == "Fresnel":
            self._app.oboundary.EditFresnel(self._boundary_name, self._get_args())  # pragma: no cover
        elif bound_type == "Symmetry":
            self._app.oboundary.EditSymmetry(self._boundary_name, self._get_args())
        elif bound_type == "Zero Tangential H Field":
            self._app.oboundary.EditZeroTangentialHField(self._boundary_name, self._get_args())  # pragma: no cover
        elif bound_type == "Zero Integrated Tangential H Field":
            self._app.oboundary.EditIntegratedZeroTangentialHField(
                self._boundary_name, self._get_args()
            )  # pragma: no cover
        elif bound_type == "Tangential H Field":
            self._app.oboundary.EditTangentialHField(self._boundary_name, self._get_args())  # pragma: no cover
        elif bound_type == "Insulating":
            self._app.oboundary.EditInsulating(self._boundary_name, self._get_args())  # pragma: no cover
        elif bound_type == "Independent":
            self._app.oboundary.EditIndependent(self._boundary_name, self._get_args())  # pragma: no cover
        elif bound_type == "Dependent":
            self._app.oboundary.EditDependent(self._boundary_name, self._get_args())  # pragma: no cover
        elif bound_type == "Band":
            self._app.omodelsetup.EditMotionSetup(self._boundary_name, self._get_args())  # pragma: no cover
        elif bound_type == "InfiniteGround":
            self._app.oboundary.EditInfiniteGround(self._boundary_name, self._get_args())
        elif bound_type == "ThinConductor":
            self._app.oboundary.EditThinConductor(self._boundary_name, self._get_args())
        elif bound_type == "Stationary Wall":
            self._app.oboundary.EditStationaryWallBoundary(self._boundary_name, self._get_args())  # pragma: no cover
        elif bound_type == "Symmetry Wall":
            self._app.oboundary.EditSymmetryWallBoundary(self._boundary_name, self._get_args())  # pragma: no cover
        elif bound_type == "Resistance":
            self._app.oboundary.EditResistanceBoundary(self._boundary_name, self._get_args())  # pragma: no cover
        elif bound_type == "Conducting Plate":
            self._app.oboundary.EditConductingPlateBoundary(self._boundary_name, self._get_args())  # pragma: no cover
        elif bound_type == "Adiabatic Plate":
            self._app.oboundary.EditAdiabaticPlateBoundary(self._boundary_name, self._get_args())  # pragma: no cover
        elif bound_type == "Network":
            self._app.oboundary.EditNetworkBoundary(self._boundary_name, self._get_args())  # pragma: no cover
        elif bound_type == "Grille":
            self._app.oboundary.EditGrilleBoundary(self._boundary_name, self._get_args())
        elif bound_type == "Opening":
            self._app.oboundary.EditOpeningBoundary(self._boundary_name, self._get_args())
        elif bound_type == "EMLoss":
            self._app.oboundary.EditEMLoss(self._boundary_name, self._get_args())  # pragma: no cover
        elif bound_type == "Block":
            self._app.oboundary.EditBlockBoundary(self._boundary_name, self._get_args())
        elif bound_type == "SourceIcepak":
            self._app.oboundary.EditSourceBoundary(self._boundary_name, self._get_args())
        elif bound_type == "HeatFlux":
            self._app.oboundary.EditHeatFlux(self._boundary_name, self._get_args())
        elif bound_type == "HeatGeneration":
            self._app.oboundary.EditHeatGeneration(self._boundary_name, self._get_args())
        elif bound_type == "Voltage":
            self._app.oboundary.EditVoltage(self._boundary_name, self._get_args())
        elif bound_type == "VoltageDrop":
            self._app.oboundary.EditVoltageDrop(self._boundary_name, self._get_args())
        elif bound_type == "Current":
            self._app.oboundary.EditCurrent(self._boundary_name, self._get_args())
        elif bound_type == "CurrentDensity":
            self._app.oboundary.AssignCurrentDensity(self._get_args())
        elif bound_type == "CurrentDensityGroup":
            self._app.oboundary.AssignCurrentDensityGroup(self._get_args()[2], self._get_args()[3])
        elif bound_type == "CurrentDensityTerminal":
            self._app.oboundary.AssignCurrentDensityTerminal(self._get_args())
        elif bound_type == "CurrentDensityTerminalGroup":
            self._app.oboundary.AssignCurrentDensityTerminalGroup(self._get_args()[2], self._get_args()[3])
        elif bound_type == "Winding" or bound_type == "Winding Group":
            self._app.oboundary.EditWindingGroup(self._boundary_name, self._get_args())  # pragma: no cover
        elif bound_type == "Vector Potential":
            self._app.oboundary.EditVectorPotential(self._boundary_name, self._get_args())  # pragma: no cover
        elif bound_type == "CoilTerminal" or bound_type == "Coil Terminal":
            self._app.oboundary.EditCoilTerminal(self._boundary_name, self._get_args())
        elif bound_type == "Coil":
            self._app.oboundary.EditCoil(self._boundary_name, self._get_args())
        elif bound_type == "Source":
            self._app.oboundary.EditTerminal(self._boundary_name, self._get_args())  # pragma: no cover
        elif bound_type == "Sink":
            self._app.oboundary.EditTerminal(self._boundary_name, self._get_args())
        elif bound_type == "SignalNet" or bound_type == "GroundNet" or bound_type == "FloatingNet":
            self._app.oboundary.EditTerminal(self._boundary_name, self._get_args())
        elif bound_type in "Circuit Port":
            self._app.oboundary.EditCircuitPort(self._boundary_name, self._get_args())
        elif bound_type in "Lumped Port":
            self._app.oboundary.EditLumpedPort(self._boundary_name, self._get_args())
        elif bound_type in "Wave Port":
            self._app.oboundary.EditWavePort(self._boundary_name, self._get_args())
        elif bound_type == "SetSBRTxRxSettings":
            self._app.oboundary.SetSBRTxRxSettings(self._get_args())  # pragma: no cover
        elif bound_type == "Floquet Port":
            self._app.oboundary.EditFloquetPort(self._boundary_name, self._get_args())  # pragma: no cover
        elif bound_type == "End Connection":
            self._app.oboundary.EditEndConnection(self._boundary_name, self._get_args())
        elif bound_type == "Hybrid":
            self._app.oboundary.EditHybridRegion(self._boundary_name, self._get_args())
        elif bound_type == "Terminal":
            self._app.oboundary.EditTerminal(self._boundary_name, self._get_args())
        else:
            return False  # pragma: no cover

        self._app._boundaries[self.name] = self._app._boundaries.pop(self._boundary_name)
        self._boundary_name = self.name

        return True

    @pyaedt_function_handler()
    def update_assignment(self):
        """Update the boundary assignment.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        out = ["Name:" + self.name]

        if "Faces" in self.props:
            faces = self.props["Faces"]
            faces_out = []
            if type(faces) is not list:
                faces = [faces]
            for f in faces:
                if type(f) is EdgePrimitive or type(f) is FacePrimitive or type(f) is VertexPrimitive:
                    faces_out.append(f.id)
                else:
                    faces_out.append(f)
            out += ["Faces:=", faces_out]

        if "Objects" in self.props:
            pr = []
            for el in self.props["Objects"]:
                try:
                    pr.append(self._app.modeler[el].name)
                except (KeyError, AttributeError):
                    pass
            out += ["Objects:=", pr]

        if len(out) == 1:
            return False

        self._app.oboundary.ReassignBoundary(out)

        return True


class MaxwellParameters(BoundaryCommon, object):
    """Manages parameters data and execution.

    Parameters
    ----------
    app : :class:`pyaedt.maxwell.Maxwell3d`, :class:`pyaedt.maxwell.Maxwell2d`
        Either ``Maxwell3d`` or ``Maxwell2d`` application.
    name : str
        Name of the boundary.
    props : dict, optional
        Properties of the boundary.
    boundarytype : str, optional
        Type of the boundary.

    Examples
    --------
    Create a matrix in Maxwell3D return a ``pyaedt.modules.Boundary.BoundaryObject``

    >>> from pyaedt import Maxwell2d
    >>> maxwell_2d = Maxwell2d()
    >>> coil1 = maxwell_2d.modeler.create_rectangle([8.5,1.5, 0], [8, 3], True, "Coil_1", "vacuum")
    >>> coil2 = maxwell_2d.modeler.create_rectangle([8.5,1.5, 0], [8, 3], True, "Coil_2", "vacuum")
    >>> maxwell_2d.assign_matrix(["Coil_1", "Coil_2"])
    """

    def __init__(self, app, name, props=None, boundarytype=None):
        self.auto_update = False
        self._app = app
        self._name = name
        self._props = None
        if props:
            self._props = BoundaryProps(self, OrderedDict(props))
        self.type = boundarytype
        self._boundary_name = self.name
        self.auto_update = True

    @property
    def object_properties(self):
        """Object-oriented properties.

        Returns
        -------
        class:`pyaedt.modeler.cad.elements3d.BinaryTreeNode`

        """
        from pyaedt.modeler.cad.elements3d import BinaryTreeNode

        cc = self._app.odesign.GetChildObject("Parameters")
        child_object = None
        if self.name in cc.GetChildNames():
            child_object = self._app.odesign.GetChildObject("Parameters").GetChildObject(self.name)
        elif self.name in self._app.odesign.GetChildObject("Parameters").GetChildNames():
            child_object = self._app.odesign.GetChildObject("Parameters").GetChildObject(self.name)
        if child_object:
            return BinaryTreeNode(self.name, child_object, False)
        return False

    @property
    def props(self):
        """Maxwell parameter data.

        Returns
        -------
        :class:BoundaryProps
        """
        if self._props:
            return self._props
        props = self._get_boundary_data(self.name)

        if props:
            self._props = BoundaryProps(self, OrderedDict(props[0]))
            self._type = props[1]
        return self._props

    @property
    def name(self):
        """Boundary name."""
        return self._name

    @name.setter
    def name(self, value):
        self._name = value
        self.update()

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
    def create(self):
        """Create a boundary.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        if self.type == "Matrix":
            self._app.o_maxwell_parameters.AssignMatrix(self._get_args())
        elif self.type == "Torque":
            self._app.o_maxwell_parameters.AssignTorque(self._get_args())
        elif self.type == "Force":
            self._app.o_maxwell_parameters.AssignForce(self._get_args())
        elif self.type == "LayoutForce":
            self._app.o_maxwell_parameters.AssignLayoutForce(self._get_args())
        else:
            return False
        return True

    @pyaedt_function_handler()
    def update(self):
        """Update the boundary.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        if self.type == "Matrix":
            self._app.o_maxwell_parameters.EditMatrix(self._boundary_name, self._get_args())
        elif self.type == "Force":
            self._app.o_maxwell_parameters.EditForce(self._boundary_name, self._get_args())
        elif self.type == "Torque":
            self._app.o_maxwell_parameters.EditTorque(self._boundary_name, self._get_args())
        else:
            return False
        self._boundary_name = self.name
        return True

    @pyaedt_function_handler()
    def _create_matrix_reduction(self, red_type, sources, matrix_name=None, join_name=None):
        if not matrix_name:
            matrix_name = generate_unique_name("ReducedMatrix", n=3)
        if not join_name:
            join_name = generate_unique_name("Join" + red_type, n=3)
        try:
            self._app.o_maxwell_parameters.AddReduceOp(
                self.name,
                matrix_name,
                ["NAME:" + join_name, "Type:=", "Join in " + red_type, "Sources:=", ",".join(sources)],
            )
            return matrix_name, join_name
        except:
            self._app.logger.error("Failed to create Matrix Reduction")
            return False, False

    @pyaedt_function_handler()
    def join_series(self, sources, matrix_name=None, join_name=None):
        """Parameters
        ----------
        sources : list
            Sources to be included in matrix reduction.
        matrix_name :  str, optional
            name of the string to create.
        join_name : str, optional
            Name of the Join operation.

        Returns
        -------
        (str, str)
            Matrix name and Joint name.

        """
        return self._create_matrix_reduction(
            red_type="Series", sources=sources, matrix_name=matrix_name, join_name=join_name
        )

    @pyaedt_function_handler()
    def join_parallel(self, sources, matrix_name=None, join_name=None):
        """Parameters
        ----------
        sources : list
            Sources to be included in matrix reduction.
        matrix_name :  str, optional
            name of the string to create.
        join_name : str, optional
            Name of the Join operation.

        Returns
        -------
        (str, str)
            Matrix name and Joint name.

        """
        return self._create_matrix_reduction(
            red_type="Parallel", sources=sources, matrix_name=matrix_name, join_name=join_name
        )


class FieldSetup(BoundaryCommon, object):
    """Manages Far Field and Near Field Component data and execution.

    Examples
    --------
    In this example the sphere1 returned object is a ``pyaedt.modules.Boundary.FarFieldSetup``
    >>> from pyaedt import Hfss
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
        self.props = BoundaryProps(self, OrderedDict(props))
        self.auto_update = True

    @property
    def name(self):
        """Variable name."""
        return self._name

    @name.setter
    def name(self, value):
        self._app.oradfield.RenameSetup(self._name, value)
        self._name = value

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
        return True

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
    in this example the sphere1 returned object is a ``pyaedt.modules.Boundary.FarFieldSetup``
    >>> from pyaedt import Hfss
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
        return self.props["CoordSystem"]

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
            self.props["ThetaStart"] = _dim_arg(value, self.units)
            self.update()

    @theta_stop.setter
    def theta_stop(self, value):
        if "ThetaStop" in self.props:
            self.props["ThetaStop"] = _dim_arg(value, self.units)
            self.update()

    @theta_step.setter
    def theta_step(self, value):
        if "ThetaStep" in self.props:
            self.props["ThetaStep"] = _dim_arg(value, self.units)
            self.update()

    @phi_start.setter
    def phi_start(self, value):
        if "PhiStart" in self.props:
            self.props["PhiStart"] = _dim_arg(value, self.units)
            self.update()

    @phi_stop.setter
    def phi_stop(self, value):
        if "PhiStop" in self.props:
            self.props["PhiStop"] = _dim_arg(value, self.units)
            self.update()

    @phi_step.setter
    def phi_step(self, value):
        if "PhiStep" in self.props:
            self.props["PhiStep"] = _dim_arg(value, self.units)
            self.update()

    @azimuth_start.setter
    def azimuth_start(self, value):
        if "AzimuthStart" in self.props:
            self.props["AzimuthStart"] = _dim_arg(value, self.units)
            self.update()

    @azimuth_stop.setter
    def azimuth_stop(self, value):
        if "AzimuthStop" in self.props:
            self.props["AzimuthStop"] = _dim_arg(value, self.units)
            self.update()

    @azimuth_step.setter
    def azimuth_step(self, value):
        if "AzimuthStep" in self.props:
            self.props["AzimuthStep"] = _dim_arg(value, self.units)
            self.update()

    @elevation_start.setter
    def elevation_start(self, value):
        if "ElevationStart" in self.props:
            self.props["ElevationStart"] = _dim_arg(value, self.units)
            self.update()

    @elevation_stop.setter
    def elevation_stop(self, value):
        if "ElevationStop" in self.props:
            self.props["ElevationStop"] = _dim_arg(value, self.units)
            self.update()

    @elevation_step.setter
    def elevation_step(self, value):
        if "ElevationStep" in self.props:
            self.props["ElevationStep"] = _dim_arg(value, self.units)
            self.update()


class NearFieldSetup(FieldSetup, object):
    """Manages Near Field Component data and execution.

    Examples
    --------
    in this example the rectangle1 returned object is a ``pyaedt.modules.Boundary.NearFieldSetup``
    >>> from pyaedt import Hfss
    >>> hfss = Hfss()
    >>> rectangle1 = hfss.insert_near_field_rectangle()
    """

    def __init__(self, app, component_name, props, component_type):
        FieldSetup.__init__(self, app, component_name, props, component_type)


class Matrix(object):
    """Manages Matrix in Q3d and Q2d Projects.

    Examples
    --------


    """

    def __init__(self, app, name, operations=None):
        self._app = app
        self.omatrix = self._app.omatrix
        self.name = name
        self._sources = []
        if operations:
            if isinstance(operations, list):
                self._operations = operations
            else:
                self._operations = [operations]
        self.CATEGORIES = CATEGORIESQ3D()

    @pyaedt_function_handler()
    def sources(self, is_gc_sources=True):
        """List of matrix sources.

        Parameters
        ----------
        is_gc_sources : bool,
            In Q3d, define if to return GC sources or RL sources. Default `True`.

        Returns
        -------
        List
        """
        if self.name in list(self._app.omatrix.ListReduceMatrixes()):
            if self._app.design_type == "Q3D Extractor":
                self._sources = list(self._app.omatrix.ListReduceMatrixReducedSources(self.name, is_gc_sources))
            else:
                self._sources = list(self._app.omatrix.ListReduceMatrixReducedSources(self.name))
        return self._sources

    @pyaedt_function_handler()
    def get_sources_for_plot(
        self,
        get_self_terms=True,
        get_mutual_terms=True,
        first_element_filter=None,
        second_element_filter=None,
        category="C",
    ):
        """Return a list of source of specified matrix ready to be used in plot reports.

        Parameters
        ----------
        get_self_terms : bool
            Either if self terms have to be returned or not.
        get_mutual_terms : bool
            Either if mutual terms have to be returned or not.
        first_element_filter : str, optional
            Filter to apply to first element of equation. It accepts `*` and `?` as special characters.
        second_element_filter : str, optional
            Filter to apply to second element of equation. It accepts `*` and `?` as special characters.
        category : str
            Plot category name as in the report. Eg. "C" is category Capacitance.
            Matrix `CATEGORIES` property can be used to map available categories.

        Returns
        -------
        list

        Examples
        --------
        >>> from pyaedt import Q3d
        >>> q3d = Q3d(project_path)
        >>> q3d.matrices[0].get_sources_for_plot(first_element_filter="Bo?1",
        ...                                      second_element_filter="GND*", category="DCL")
        """
        if not first_element_filter:
            first_element_filter = "*"
        if not second_element_filter:
            second_element_filter = "*"
        is_cg = False
        if category in [self.CATEGORIES.Q3D.C, self.CATEGORIES.Q3D.G]:
            is_cg = True
        list_output = []
        if get_self_terms:
            for el in self.sources(is_gc_sources=is_cg):
                value = "{}({},{})".format(category, el, el)
                if filter_tuple(value, first_element_filter, second_element_filter):
                    list_output.append(value)
        if get_mutual_terms:
            for el1 in self.sources(is_gc_sources=is_cg):
                for el2 in self.sources(is_gc_sources=is_cg):
                    if el1 != el2:
                        value = "{}({},{})".format(category, el1, el2)
                        if filter_tuple(value, first_element_filter, second_element_filter):
                            list_output.append(value)
        return list_output

    @property
    def operations(self):
        """List of matrix operations.

        Returns
        -------
        List
        """
        if self.name in list(self._app.omatrix.ListReduceMatrixes()):
            self._operations = self._app.omatrix.ListReduceMatrixOperations(self.name)
        return self._operations

    @pyaedt_function_handler()
    def create(
        self,
        source_names=None,
        new_net_name=None,
        new_source_name=None,
        new_sink_name=None,
    ):
        """Create a new matrix.

        Parameters
        ----------
        source_names : str, list
            List or str containing the content of the matrix reduction (eg. source name).
        new_net_name : str, optional
            Name of the new net. The default is ``None``.
        new_source_name : str, optional
            Name of the new source. The default is ``None``.
        new_sink_name : str, optional
            Name of the new sink. The default is ``None``.

        Returns
        -------
        bool
            `True` if succeeded.
        """
        if not isinstance(source_names, list) and source_names:
            source_names = [source_names]

        command = self._write_command(source_names, new_net_name, new_source_name, new_sink_name)
        self.omatrix.InsertRM(self.name, command)
        return True

    @pyaedt_function_handler()
    def delete(self):
        """Delete current matrix.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        self.omatrix.DeleteRM(self.name)
        for el in self._app.matrices:
            if el.name == self.name:
                self._app.matrices.remove(el)
        return True

    @pyaedt_function_handler()
    def add_operation(
        self,
        operation_type,
        source_names=None,
        new_net_name=None,
        new_source_name=None,
        new_sink_name=None,
    ):
        """Add a new operation to existing matrix.

        Parameters
        ----------
        operation_type : str
            Operation to perform
        source_names : str, list
            List or str containing the content of the matrix reduction (eg. source name).
        new_net_name : str, optional
            Name of the new net. The default is ``None``.
        new_source_name : str, optional
            Name of the new source. The default is ``None``.
        new_sink_name : str, optional
            Name of the new sink. The default is ``None``.

        Returns
        -------
        bool
            `True` if succeeded.
        """
        self._operations.append(operation_type)
        if not isinstance(source_names, list) and source_names:
            source_names = [source_names]

        if not new_net_name:
            new_net_name = generate_unique_name("Net")

        if not new_source_name:
            new_source_name = generate_unique_name("Source")

        if not new_sink_name:
            new_sink_name = generate_unique_name("Sink")

        command = self._write_command(source_names, new_net_name, new_source_name, new_sink_name)
        self.omatrix.RMAddOp(self.name, command)
        return True

    @pyaedt_function_handler()
    def _write_command(self, source_names, new_name, new_source, new_sink):
        if self._operations[-1] == "JoinSeries":
            command = "{}('{}', '{}')".format(self._operations[-1], new_name, "', '".join(source_names))
        elif self._operations[-1] == "JoinParallel":
            command = "{}('{}', '{}', '{}', '{}')".format(
                self._operations[-1], new_name, new_source, new_sink, "', '".join(source_names)
            )
        elif self._operations[-1] == "JoinSelectedTerminals":
            command = "{}('', '{}')".format(self._operations[-1], "', '".join(source_names))
        elif self._operations[-1] == "FloatInfinity":
            command = "FloatInfinity()"
        elif self._operations[-1] == "AddGround":
            command = "{}(SelectionArray[{}: '{}'], OverrideInfo())".format(
                self._operations[-1], len(source_names), "', '".join(source_names)
            )
        elif (
            self._operations[-1] == "SetReferenceGround"
            or self._operations[-1] == "SetReferenceGround"
            or self._operations[-1] == "Float"
        ):
            command = "{}(SelectionArray[{}: '{}'], OverrideInfo())".format(
                self._operations[-1], len(source_names), "', '".join(source_names)
            )
        elif self._operations[-1] == "Parallel" or self._operations[-1] == "DiffPair":
            id_ = 0
            for el in self._app.boundaries:
                if el.name == source_names[0]:
                    id_ = self._app.modeler[el.props["Objects"][0]].id
            command = "{}(SelectionArray[{}: '{}'], OverrideInfo({}, '{}'))".format(
                self._operations[-1], len(source_names), "', '".join(source_names), id_, new_name
            )
        else:
            command = "{}('{}')".format(self._operations[-1], "', '".join(source_names))
        return command


class BoundaryObject3dLayout(BoundaryCommon, object):
    """Manages boundary data and execution for Hfss3dLayout.

    Parameters
    ----------
    app : object
        An AEDT application from ``pyaedt.application``.
    name : str
        Name of the boundary.
    props : dict
        Properties of the boundary.
    boundarytype : str
        Type of the boundary.
    """

    def __init__(self, app, name, props, boundarytype):
        self.auto_update = False
        self._app = app
        self._name = name
        self._props = None
        if props:
            self._props = BoundaryProps(self, OrderedDict(props))
        self.type = boundarytype
        self._boundary_name = self.name
        self.auto_update = True

    @property
    def object_properties(self):
        """Object-oriented properties.

        Returns
        -------
        class:`pyaedt.modeler.cad.elements3d.BinaryTreeNode`

        """
        from pyaedt.modeler.cad.elements3d import BinaryTreeNode

        cc = self._app.odesign.GetChildObject("Excitations")
        child_object = None
        if self.name in cc.GetChildNames():
            child_object = self._app.odesign.GetChildObject("Excitations").GetChildObject(self.name)
        elif self.name in self._app.odesign.GetChildObject("Excitations").GetChildNames():
            child_object = self._app.odesign.GetChildObject("Excitations").GetChildObject(self.name)
        if child_object:
            return BinaryTreeNode(self.name, child_object, False)
        return False

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
        :class:BoundaryProps
        """
        if self._props:
            return self._props
        props = self._get_boundary_data(self.name)

        if props:
            self._props = BoundaryProps(self, OrderedDict(props[0]))
            self._type = props[1]
        return self._props

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
        if len(self._app.oeditor.GetProperties("EM Design", "Excitations:{}".format(self.name))) != len(self.props):
            propnames = self._app.oeditor.GetProperties("EM Design", "Excitations:{}".format(self.name))
            props = OrderedDict()
            for prop in propnames:
                props[prop] = self._app.oeditor.GetPropertyValue("EM Design", "Excitations:{}".format(self.name), prop)
            self._props = BoundaryProps(self, props)

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
            elif el in self._app.oeditor.GetProperties("EM Design", "Excitations:{}".format(self.name)) and self.props[
                el
            ] != self._app.oeditor.GetPropertyValue("EM Design", "Excitations:" + self.name, el):
                self._app.oeditor.SetPropertyValue("EM Design", "Excitations:" + self.name, el, self.props[el])
                updated = True

        if updated:
            self._refresh_properties()

        return True


class Sources(object):
    """Manages sources in Circuit projects."""

    def __init__(self, app, name, source_type=None):
        self._app = app
        self._name = name
        self._props = self._source_props(name, source_type)
        self.source_type = source_type
        if not source_type:
            self.source_type = self._source_type_by_key()
        self._auto_update = True

    @property
    def name(self):
        """Source name.

        Returns
        -------
        str
        """
        return self._name

    @name.setter
    def name(self, source_name):
        if source_name not in self._app.source_names:
            if source_name != self._name:
                original_name = self._name
                self._name = source_name
                for port in self._app.excitations:
                    if original_name in self._app.excitations[port].props["EnabledPorts"]:
                        self._app.excitations[port].props["EnabledPorts"] = [
                            w.replace(original_name, source_name)
                            for w in self._app.excitations[port].props["EnabledPorts"]
                        ]
                    if original_name in self._app.excitations[port].props["EnabledAnalyses"]:
                        self._app.excitations[port].props["EnabledAnalyses"][source_name] = (
                            self._app.excitations[port].props["EnabledAnalyses"].pop(original_name)
                        )
                self.update(original_name)
        else:
            self._logger.warning("Name %s already assigned in the design", source_name)

    @property
    def _logger(self):
        """Logger."""
        return self._app.logger

    @pyaedt_function_handler()
    def _source_props(self, source, source_type=None):
        source_prop_dict = {}
        if source in self._app.source_names:
            source_aedt_props = self._app.odesign.GetChildObject("Excitations").GetChildObject(source)
            for el in source_aedt_props.GetPropNames():
                if el == "CosimDefinition":
                    source_prop_dict[el] = None
                elif el == "FreqDependentSourceData":
                    data = self._app.design_properties["NexximSources"]["Data"][source]["FDSFileName"]
                    freqs = re.findall("freqs=\[(.*?)\]", data)
                    magnitude = re.findall("magnitude=\[(.*?)\]", data)
                    angle = re.findall("angle=\[(.*?)\]", data)
                    vreal = re.findall("vreal=\[(.*?)\]", data)
                    vimag = re.findall("vimag=\[(.*?)\]", data)
                    source_file = re.findall("voltage_source_file=", data)
                    source_prop_dict["frequencies"] = None
                    source_prop_dict["vmag"] = None
                    source_prop_dict["vang"] = None
                    source_prop_dict["vreal"] = None
                    source_prop_dict["vimag"] = None
                    source_prop_dict["fds_filename"] = None
                    source_prop_dict["magnitude_angle"] = False
                    source_prop_dict["FreqDependentSourceData"] = data
                    if freqs:
                        source_prop_dict["frequencies"] = [float(i) for i in freqs[0].split()]
                    if magnitude:
                        source_prop_dict["vmag"] = [float(i) for i in magnitude[0].split()]
                    if angle:
                        source_prop_dict["vang"] = [float(i) for i in angle[0].split()]
                    if vreal:
                        source_prop_dict["vreal"] = [float(i) for i in vreal[0].split()]
                    if vimag:
                        source_prop_dict["vimag"] = [float(i) for i in vimag[0].split()]
                    if source_file:
                        source_prop_dict["fds_filename"] = data[len(re.findall("voltage_source_file=", data)[0]) :]
                    else:
                        if freqs and magnitude and angle:
                            source_prop_dict["magnitude_angle"] = True
                        elif freqs and vreal and vimag:
                            source_prop_dict["magnitude_angle"] = False

                elif el != "Name" and el != "Noise":
                    source_prop_dict[el] = source_aedt_props.GetPropValue(el)
                    if not source_prop_dict[el]:
                        source_prop_dict[el] = ""
        else:
            if source_type in SourceKeys.SourceNames:
                command_template = SourceKeys.SourceTemplates[source_type]
                commands = copy.deepcopy(command_template)
                props = [value for value in commands if type(value) == list]
                for el in props[0]:
                    if isinstance(el, list):
                        if el[0] == "CosimDefinition":
                            source_prop_dict[el[0]] = None
                        elif el[0] == "FreqDependentSourceData":
                            source_prop_dict["frequencies"] = None
                            source_prop_dict["vmag"] = None
                            source_prop_dict["vang"] = None
                            source_prop_dict["vreal"] = None
                            source_prop_dict["vimag"] = None
                            source_prop_dict["fds_filename"] = None
                            source_prop_dict["magnitude_angle"] = True
                            source_prop_dict["FreqDependentSourceData"] = ""

                        elif el[0] != "ModelName" and el[0] != "LabelID":
                            source_prop_dict[el[0]] = el[3]

        return OrderedDict(source_prop_dict)

    @pyaedt_function_handler()
    def _update_command(self, name, source_prop_dict, source_type, fds_filename=None):
        command_template = SourceKeys.SourceTemplates[source_type]
        commands = copy.deepcopy(command_template)
        commands[0] = "NAME:" + name
        commands[10] = source_prop_dict["Netlist"]
        if fds_filename:
            commands[14] = fds_filename
        cont = 0
        props = [value for value in commands if type(value) == list]
        for command in props[0]:
            if isinstance(command, list) and command[0] in source_prop_dict.keys() and command[0] != "CosimDefinition":
                if command[0] == "Netlist":
                    props[0].pop(cont)
                elif command[0] == "file" and source_prop_dict[command[0]]:
                    props[0][cont][3] = source_prop_dict[command[0]]
                    props[0][cont][4] = source_prop_dict[command[0]]
                elif command[0] == "FreqDependentSourceData" and fds_filename:
                    props[0][cont][3] = fds_filename
                    props[0][cont][4] = fds_filename
                else:
                    props[0][cont][3] = source_prop_dict[command[0]]
            cont += 1

        return commands

    @pyaedt_function_handler()
    def _source_type_by_key(self):
        for source_name in SourceKeys.SourceNames:
            template = SourceKeys.SourceProps[source_name]
            if list(self._props.keys()) == template:
                return source_name
        return None

    @pyaedt_function_handler()
    def update(self, original_name=None, new_source=None):
        """Update the source in AEDT.

        Parameters
        ----------
        original_name : str, optional
            Original name of the source. The default value is ``None``.
        new_source : str, optional
            New name of the source. The default value is ``None``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        arg0 = ["NAME:Data"]
        if self.source_type != "VoltageFrequencyDependent":
            fds_filename = None
        else:
            fds_filename = self._props["FreqDependentSourceData"]

        for source in self._app.sources:
            if "FreqDependentSourceData" in self._app.sources[source]._props.keys():
                fds_filename_source = self._app.sources[source]._props["FreqDependentSourceData"]
            else:
                fds_filename_source = None
            if source == self.name:
                arg0.append(list(self._update_command(source, self._props, self.source_type, fds_filename)))
            elif source != self.name and original_name == source:
                arg0.append(
                    list(
                        self._update_command(
                            self.name, self._props, self._app.sources[source].source_type, fds_filename
                        )
                    )
                )
            else:
                arg0.append(
                    list(
                        self._update_command(
                            source,
                            self._app.sources[source]._props,
                            self._app.sources[source].source_type,
                            fds_filename_source,
                        )
                    )
                )

        if new_source and new_source not in self._app.sources:
            arg0.append(list(self._update_command(self.name, self._props, self.source_type, fds_filename)))

        arg1 = ["NAME:NexximSources", ["NAME:NexximSources", arg0]]
        arg2 = ["NAME:ComponentConfigurationData"]

        # Check Ports with Sources
        arg3 = ["NAME:EnabledPorts"]
        for source_name in self._app.sources:
            excitation_source = []
            for port in self._app.excitations:
                if source_name in self._app.excitations[port]._props["EnabledPorts"]:
                    excitation_source.append(port)
            arg3.append(source_name + ":=")
            arg3.append(excitation_source)

        if new_source and new_source not in self._app.sources:
            arg3.append(new_source + ":=")
            arg3.append([])

        arg4 = ["NAME:EnabledMultipleComponents"]
        for source_name in self._app.sources:
            arg4.append(source_name + ":=")
            arg4.append([])

        if new_source and new_source not in self._app.sources:
            arg4.append(new_source + ":=")
            arg4.append([])

        arg5 = ["NAME:EnabledAnalyses"]
        for source_name in self._app.sources:
            arg6 = ["NAME:" + source_name]
            for port in self._app.excitations:
                if source_name in self._app.excitations[port]._props["EnabledAnalyses"]:
                    arg6.append(port + ":=")
                    arg6.append(self._app.excitations[port]._props["EnabledAnalyses"][source_name])
                else:
                    arg6.append(port + ":=")
                    arg6.append([])
            arg5.append(arg6)

        if new_source and new_source not in self._app.sources:
            arg6 = ["NAME:" + new_source]
            for port in self._app.excitations:
                arg6.append(port + ":=")
                arg6.append([])
            arg5.append(arg6)

        arg7 = ["NAME:ComponentConfigurationData", arg3, arg4, arg5]
        arg2.append(arg7)

        self._app.odesign.UpdateSources(arg1, arg2)
        return True

    @pyaedt_function_handler()
    def delete(self):
        """Delete the source in AEDT.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        self._app.modeler._odesign.DeleteSource(self.name)
        for port in self._app.excitations:
            if self.name in self._app.excitations[port].props["EnabledPorts"]:
                self._app.excitations[port].props["EnabledPorts"].remove(self.name)
            if self.name in self._app.excitations[port].props["EnabledAnalyses"]:
                del self._app.excitations[port].props["EnabledAnalyses"][self.name]
        return True

    @pyaedt_function_handler()
    def create(self):
        """Create a new source in AEDT.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        self.update(original_name=None, new_source=self.name)
        return True


class PowerSinSource(Sources, object):
    """Power Sinusoidal Class."""

    def __init__(self, app, name, source_type=None):
        Sources.__init__(self, app, name, source_type)

    @property
    def _child(self):
        return self._app.odesign.GetChildObject("Excitations").GetChildObject(self.name)

    @property
    def ac_magnitude(self):
        """AC magnitude value.

        Returns
        -------
        str
        """
        return self._props["ACMAG"]

    @ac_magnitude.setter
    def ac_magnitude(self, value):
        self._props["ACMAG"] = value
        self._child.SetPropValue("ACMAG", value)

    @property
    def ac_phase(self):
        """AC phase value.

        Returns
        -------
        str
        """
        return self._props["ACPHASE"]

    @ac_phase.setter
    def ac_phase(self, value):
        self._props["ACPHASE"] = value
        self._child.SetPropValue("ACPHASE", value)

    @property
    def dc_magnitude(self):
        """DC voltage value.

        Returns
        -------
        str
        """
        return self._props["DC"]

    @dc_magnitude.setter
    def dc_magnitude(self, value):
        self._props["DC"] = value
        self._child.SetPropValue("DC", value)

    @property
    def power_offset(self):
        """Power offset from zero watts.

        Returns
        -------
        str
        """
        return self._props["VO"]

    @power_offset.setter
    def power_offset(self, value):
        self._props["VO"] = value
        self._child.SetPropValue("VO", value)

    @property
    def power_magnitude(self):
        """Available power of the source above power offset.

        Returns
        -------
        str
        """
        return self._props["POWER"]

    @power_magnitude.setter
    def power_magnitude(self, value):
        self._props["POWER"] = value
        self._child.SetPropValue("POWER", value)

    @property
    def frequency(self):
        """Frequency.

        Returns
        -------
        str
        """
        return self._props["FREQ"]

    @frequency.setter
    def frequency(self, value):
        self._props["FREQ"] = value
        self._child.SetPropValue("FREQ", value)

    @property
    def delay(self):
        """Delay to start of sine wave.

        Returns
        -------
        str
        """
        return self._props["TD"]

    @delay.setter
    def delay(self, value):
        self._props["TD"] = value
        self._child.SetPropValue("TD", value)

    @property
    def damping_factor(self):
        """Damping factor.

        Returns
        -------
        str
        """
        return self._props["ALPHA"]

    @damping_factor.setter
    def damping_factor(self, value):
        self._props["ALPHA"] = value
        self._child.SetPropValue("ALPHA", value)

    @property
    def phase_delay(self):
        """Phase delay.

        Returns
        -------
        str
        """
        return self._props["THETA"]

    @phase_delay.setter
    def phase_delay(self, value):
        self._props["THETA"] = value
        self._child.SetPropValue("THETA", value)

    @property
    def tone(self):
        """Frequency to use for harmonic balance.

        Returns
        -------
        str
        """
        return self._props["TONE"]

    @tone.setter
    def tone(self, value):
        self._props["TONE"] = value
        self._child.SetPropValue("TONE", value)


class PowerIQSource(Sources, object):
    """Power IQ Class."""

    def __init__(self, app, name, source_type=None):
        Sources.__init__(self, app, name, source_type)

    @property
    def _child(self):
        return self._app.odesign.GetChildObject("Excitations").GetChildObject(self.name)

    @property
    def carrier_frequency(self):
        """Carrier frequency value.

        Returns
        -------
        str
        """
        return self._props["FC"]

    @carrier_frequency.setter
    def carrier_frequency(self, value):
        self._props["FC"] = value
        self._child.SetPropValue("FC", value)

    @property
    def sampling_time(self):
        """Sampling time value.

        Returns
        -------
        str
        """
        return self._props["TS"]

    @sampling_time.setter
    def sampling_time(self, value):
        self._props["TS"] = value
        self._child.SetPropValue("TS", value)

    @property
    def dc_magnitude(self):
        """DC voltage value.

        Returns
        -------
        str
        """
        return self._props["DC"]

    @dc_magnitude.setter
    def dc_magnitude(self, value):
        self._props["DC"] = value
        self._child.SetPropValue("DC", value)

    @property
    def repeat_from(self):
        """Repeat from time.

        Returns
        -------
        str
        """
        return self._props["R"]

    @repeat_from.setter
    def repeat_from(self, value):
        self._props["R"] = value
        self._child.SetPropValue("R", value)

    @property
    def delay(self):
        """Delay to start of sine wave.

        Returns
        -------
        str
        """
        return self._props["TD"]

    @delay.setter
    def delay(self, value):
        self._props["TD"] = value
        self._child.SetPropValue("TD", value)

    @property
    def carrier_amplitude_voltage(self):
        """Carrier amplitude value, voltage-based.

        Returns
        -------
        str
        """
        return self._props["V"]

    @carrier_amplitude_voltage.setter
    def carrier_amplitude_voltage(self, value):
        self._props["V"] = value
        self._child.SetPropValue("V", value)

    @property
    def carrier_amplitude_power(self):
        """Carrier amplitude value, power-based.

        Returns
        -------
        str
        """
        return self._props["VA"]

    @carrier_amplitude_power.setter
    def carrier_amplitude_power(self, value):
        self._props["VA"] = value
        self._child.SetPropValue("VA", value)

    @property
    def carrier_offset(self):
        """Carrier offset.

        Returns
        -------
        str
        """
        return self._props["VO"]

    @carrier_offset.setter
    def carrier_offset(self, value):
        self._props["VO"] = value
        self._child.SetPropValue("VO", value)

    @property
    def real_impedance(self):
        """Real carrier impedance.

        Returns
        -------
        str
        """
        return self._props["RZ"]

    @real_impedance.setter
    def real_impedance(self, value):
        self._props["RZ"] = value
        self._child.SetPropValue("RZ", value)

    @property
    def imaginary_impedance(self):
        """Imaginary carrier impedance.

        Returns
        -------
        str
        """
        return self._props["IZ"]

    @imaginary_impedance.setter
    def imaginary_impedance(self, value):
        self._props["IZ"] = value
        self._child.SetPropValue("IZ", value)

    @property
    def damping_factor(self):
        """Damping factor.

        Returns
        -------
        str
        """
        return self._props["ALPHA"]

    @damping_factor.setter
    def damping_factor(self, value):
        self._props["ALPHA"] = value
        self._child.SetPropValue("ALPHA", value)

    @property
    def phase_delay(self):
        """Phase delay.

        Returns
        -------
        str
        """
        return self._props["THETA"]

    @phase_delay.setter
    def phase_delay(self, value):
        self._props["THETA"] = value
        self._child.SetPropValue("THETA", value)

    @property
    def tone(self):
        """Frequency to use for harmonic balance.

        Returns
        -------
        str
        """
        return self._props["TONE"]

    @tone.setter
    def tone(self, value):
        self._props["TONE"] = value
        self._child.SetPropValue("TONE", value)

    @property
    def i_q_values(self):
        """I and Q value at each timepoint.

        Returns
        -------
        str
        """
        i_q = []
        for cont in range(1, 20):
            i_q.append(
                [self._props["time" + str(cont)], self._props["ival" + str(cont)], self._props["qval" + str(cont)]]
            )
        return i_q

    @i_q_values.setter
    def i_q_values(self, value):
        cont = 0
        for point in value:
            self._props["time" + str(cont + 1)] = point[0]
            self._child.SetPropValue("time" + str(cont + 1), point[0])
            self._props["ival" + str(cont + 1)] = point[1]
            self._child.SetPropValue("ival" + str(cont + 1), point[1])
            self._props["qval" + str(cont + 1)] = point[2]
            self._child.SetPropValue("qval" + str(cont + 1), point[2])
            cont += 1

    @property
    def file(
        self,
    ):
        """File path with I and Q values.

        Returns
        -------
        str
        """
        return self._props["file"]

    @file.setter
    def file(self, value):
        self._props["file"] = value
        self.update()


class VoltageFrequencyDependentSource(Sources, object):
    """Voltage Frequency Dependent Class."""

    def __init__(self, app, name, source_type=None):
        Sources.__init__(self, app, name, source_type)

    @property
    def _child(self):
        return self._app.odesign.GetChildObject("Excitations").GetChildObject(self.name)

    @property
    def frequencies(self):
        """List of frequencies in ``Hz``.

        Returns
        -------
        list
        """
        return self._props["frequencies"]

    @frequencies.setter
    def frequencies(self, value):
        self._props["frequencies"] = [float(i) for i in value]
        self._update_prop()

    @property
    def vmag(self):
        """List of magnitudes in ``V``.

        Returns
        -------
        list
        """
        return self._props["vmag"]

    @vmag.setter
    def vmag(self, value):
        self._props["vmag"] = [float(i) for i in value]
        self._update_prop()

    @property
    def vang(self):
        """List of angles in ``rad``.

        Returns
        -------
        list
        """
        return self._props["vang"]

    @vang.setter
    def vang(self, value):
        self._props["vang"] = [float(i) for i in value]
        self._update_prop()

    @property
    def vreal(self):
        """List of real values in ``V``.

        Returns
        -------
        list
        """
        return self._props["vreal"]

    @vreal.setter
    def vreal(self, value):
        self._props["vreal"] = [float(i) for i in value]
        self._update_prop()

    @property
    def vimag(self):
        """List of imaginary values in ``V``.

        Returns
        -------
        list
        """
        return self._props["vimag"]

    @vimag.setter
    def vimag(self, value):
        self._props["vimag"] = [float(i) for i in value]
        self._update_prop()

    @property
    def magnitude_angle(self):
        """Enable magnitude and angle data.

        Returns
        -------
        bool
        """
        return self._props["magnitude_angle"]

    @magnitude_angle.setter
    def magnitude_angle(self, value):
        self._props["magnitude_angle"] = value
        self._update_prop()

    @property
    def fds_filename(self):
        """FDS file path.

        Returns
        -------
        bool
        """
        return self._props["fds_filename"]

    @fds_filename.setter
    def fds_filename(self, name):
        if not name:
            self._props["fds_filename"] = None
            self._update_prop()
        else:
            self._props["fds_filename"] = name
            self._props["FreqDependentSourceData"] = "voltage_source_file=" + name
            self.update()

    @pyaedt_function_handler()
    def _update_prop(self):
        if (
            self._props["vmag"]
            and self._props["vang"]
            and self._props["frequencies"]
            and self._props["magnitude_angle"]
            and not self._props["fds_filename"]
        ):
            if len(self._props["vmag"]) == len(self._props["vang"]) == len(self._props["frequencies"]):
                self._props["FreqDependentSourceData"] = (
                    "freqs="
                    + str(self._props["frequencies"]).replace(",", "")
                    + " vmag="
                    + str(self._props["vmag"]).replace(",", "")
                    + " vang="
                    + str(self._props["vang"]).replace(",", "")
                )
                self.update()
        elif (
            self._props["vreal"]
            and self._props["vimag"]
            and self._props["frequencies"]
            and not self._props["magnitude_angle"]
            and not self._props["fds_filename"]
        ):
            if len(self._props["vreal"]) == len(self._props["vimag"]) == len(self._props["frequencies"]):
                self._props["FreqDependentSourceData"] = (
                    "freqs="
                    + str(self._props["frequencies"]).replace(",", "")
                    + " vreal="
                    + str(self._props["vreal"]).replace(",", "")
                    + " vimag="
                    + str(self._props["vimag"]).replace(",", "")
                )
                self.update()
        else:
            self._props["FreqDependentSourceData"] = ""
            self.update()
        return True


class VoltageDCSource(Sources, object):
    """Power Sinusoidal Class."""

    def __init__(self, app, name, source_type=None):
        Sources.__init__(self, app, name, source_type)

    @property
    def _child(self):
        return self._app.odesign.GetChildObject("Excitations").GetChildObject(self.name)

    @property
    def ac_magnitude(self):
        """AC magnitude value.

        Returns
        -------
        str
        """
        return self._props["ACMAG"]

    @ac_magnitude.setter
    def ac_magnitude(self, value):
        self._props["ACMAG"] = value
        self._child.SetPropValue("ACMAG", value)

    @property
    def ac_phase(self):
        """AC phase value.

        Returns
        -------
        str
        """
        return self._props["ACPHASE"]

    @ac_phase.setter
    def ac_phase(self, value):
        self._props["ACPHASE"] = value
        self._child.SetPropValue("ACPHASE", value)

    @property
    def dc_magnitude(self):
        """DC voltage value.

        Returns
        -------
        str
        """
        return self._props["DC"]

    @dc_magnitude.setter
    def dc_magnitude(self, value):
        self._props["DC"] = value
        self._child.SetPropValue("DC", value)


class VoltageSinSource(Sources, object):
    """Power Sinusoidal Class."""

    def __init__(self, app, name, source_type=None):
        Sources.__init__(self, app, name, source_type)

    @property
    def _child(self):
        return self._app.odesign.GetChildObject("Excitations").GetChildObject(self.name)

    @property
    def ac_magnitude(self):
        """AC magnitude value.

        Returns
        -------
        str
        """
        return self._props["ACMAG"]

    @ac_magnitude.setter
    def ac_magnitude(self, value):
        self._props["ACMAG"] = value
        self._child.SetPropValue("ACMAG", value)

    @property
    def ac_phase(self):
        """AC phase value.

        Returns
        -------
        str
        """
        return self._props["ACPHASE"]

    @ac_phase.setter
    def ac_phase(self, value):
        self._props["ACPHASE"] = value
        self._child.SetPropValue("ACPHASE", value)

    @property
    def dc_magnitude(self):
        """DC voltage value.

        Returns
        -------
        str
        """
        return self._props["DC"]

    @dc_magnitude.setter
    def dc_magnitude(self, value):
        self._props["DC"] = value
        self._child.SetPropValue("DC", value)

    @property
    def voltage_amplitude(self):
        """Voltage amplitude.

        Returns
        -------
        str
        """
        return self._props["VA"]

    @voltage_amplitude.setter
    def voltage_amplitude(self, value):
        self._props["VA"] = value
        self._child.SetPropValue("VA", value)

    @property
    def voltage_offset(self):
        """Voltage offset from zero watts.

        Returns
        -------
        str
        """
        return self._props["VO"]

    @voltage_offset.setter
    def voltage_offset(self, value):
        self._props["VO"] = value
        self._child.SetPropValue("VO", value)

    @property
    def frequency(self):
        """Frequency.

        Returns
        -------
        str
        """
        return self._props["FREQ"]

    @frequency.setter
    def frequency(self, value):
        self._props["FREQ"] = value
        self._child.SetPropValue("FREQ", value)

    @property
    def delay(self):
        """Delay to start of sine wave.

        Returns
        -------
        str
        """
        return self._props["TD"]

    @delay.setter
    def delay(self, value):
        self._props["TD"] = value
        self._child.SetPropValue("TD", value)

    @property
    def damping_factor(self):
        """Damping factor.

        Returns
        -------
        str
        """
        return self._props["ALPHA"]

    @damping_factor.setter
    def damping_factor(self, value):
        self._props["ALPHA"] = value
        self._child.SetPropValue("ALPHA", value)

    @property
    def phase_delay(self):
        """Phase delay.

        Returns
        -------
        str
        """
        return self._props["THETA"]

    @phase_delay.setter
    def phase_delay(self, value):
        self._props["THETA"] = value
        self._child.SetPropValue("THETA", value)

    @property
    def tone(self):
        """Frequency to use for harmonic balance.

        Returns
        -------
        str
        """
        return self._props["TONE"]

    @tone.setter
    def tone(self, value):
        self._props["TONE"] = value
        self._child.SetPropValue("TONE", value)


class CurrentSinSource(Sources, object):
    """Current Sinusoidal Class."""

    def __init__(self, app, name, source_type=None):
        Sources.__init__(self, app, name, source_type)

    @property
    def _child(self):
        return self._app.odesign.GetChildObject("Excitations").GetChildObject(self.name)

    @property
    def ac_magnitude(self):
        """AC magnitude value.

        Returns
        -------
        str
        """
        return self._props["ACMAG"]

    @ac_magnitude.setter
    def ac_magnitude(self, value):
        self._props["ACMAG"] = value
        self._child.SetPropValue("ACMAG", value)

    @property
    def ac_phase(self):
        """AC phase value.

        Returns
        -------
        str
        """
        return self._props["ACPHASE"]

    @ac_phase.setter
    def ac_phase(self, value):
        self._props["ACPHASE"] = value
        self._child.SetPropValue("ACPHASE", value)

    @property
    def dc_magnitude(self):
        """DC current value.

        Returns
        -------
        str
        """
        return self._props["DC"]

    @dc_magnitude.setter
    def dc_magnitude(self, value):
        self._props["DC"] = value
        self._child.SetPropValue("DC", value)

    @property
    def current_amplitude(self):
        """Current amplitude.

        Returns
        -------
        str
        """
        return self._props["VA"]

    @current_amplitude.setter
    def current_amplitude(self, value):
        self._props["VA"] = value
        self._child.SetPropValue("VA", value)

    @property
    def current_offset(self):
        """Current offset.

        Returns
        -------
        str
        """
        return self._props["VO"]

    @current_offset.setter
    def current_offset(self, value):
        self._props["VO"] = value
        self._child.SetPropValue("VO", value)

    @property
    def frequency(self):
        """Frequency.

        Returns
        -------
        str
        """
        return self._props["FREQ"]

    @frequency.setter
    def frequency(self, value):
        self._props["FREQ"] = value
        self._child.SetPropValue("FREQ", value)

    @property
    def delay(self):
        """Delay to start of sine wave.

        Returns
        -------
        str
        """
        return self._props["TD"]

    @delay.setter
    def delay(self, value):
        self._props["TD"] = value
        self._child.SetPropValue("TD", value)

    @property
    def damping_factor(self):
        """Damping factor.

        Returns
        -------
        str
        """
        return self._props["ALPHA"]

    @damping_factor.setter
    def damping_factor(self, value):
        self._props["ALPHA"] = value
        self._child.SetPropValue("ALPHA", value)

    @property
    def phase_delay(self):
        """Phase delay.

        Returns
        -------
        str
        """
        return self._props["THETA"]

    @phase_delay.setter
    def phase_delay(self, value):
        self._props["THETA"] = value
        self._child.SetPropValue("THETA", value)

    @property
    def multiplier(self):
        """Multiplier for simulating multiple parallel current sources.

        Returns
        -------
        str
        """
        return self._props["M"]

    @multiplier.setter
    def multiplier(self, value):
        self._props["M"] = value
        self._child.SetPropValue("M", value)

    @property
    def tone(self):
        """Frequency to use for harmonic balance.

        Returns
        -------
        str
        """
        return self._props["TONE"]

    @tone.setter
    def tone(self, value):
        self._props["TONE"] = value
        self._child.SetPropValue("TONE", value)


class Excitations(object):
    """Manages Excitations in Circuit Projects.

    Examples
    --------

    """

    def __init__(self, app, name):
        self._app = app
        self._name = name
        for comp in self._app.modeler.schematic.components:
            if (
                "PortName" in self._app.modeler.schematic.components[comp].parameters.keys()
                and self._app.modeler.schematic.components[comp].parameters["PortName"] == self.name
            ):
                self.schematic_id = comp
                self.id = self._app.modeler.schematic.components[comp].id
                self._angle = self._app.modeler.schematic.components[comp].angle
                self.levels = self._app.modeler.schematic.components[comp].levels
                self._location = self._app.modeler.schematic.components[comp].location
                self._mirror = self._app.modeler.schematic.components[comp].mirror
                self.pins = self._app.modeler.schematic.components[comp].pins
                self._use_symbol_color = self._app.modeler.schematic.components[comp].usesymbolcolor
                break
        self._props = self._excitation_props(name)
        self._auto_update = True

    @property
    def name(self):
        """Excitation name.

        Returns
        -------
        str
        """
        return self._name

    @name.setter
    def name(self, port_name):
        if port_name not in self._app.excitation_names:
            if port_name != self._name:
                # Take previous properties
                self._app.odesign.RenamePort(self._name, port_name)
                self._name = port_name
                self._app.modeler.schematic.components[self.schematic_id].name = "IPort@" + port_name
                self.pins[0].name = "IPort@" + port_name + ";" + str(self.schematic_id)
        else:
            self._logger.warning("Name %s already assigned in the design", port_name)

    @property
    def angle(self):
        """Symbol angle.

        Returns
        -------
        float
        """
        return self._angle

    @angle.setter
    def angle(self, angle):
        self._app.modeler.schematic.components[self.schematic_id].angle = angle

    @property
    def mirror(self):
        """Enable port mirror.

        Returns
        -------
        bool
        """
        return self._mirror

    @mirror.setter
    def mirror(self, mirror_value=True):
        self._app.modeler.schematic.components[self.schematic_id].mirror = mirror_value
        self._mirror = mirror_value

    @property
    def location(self):
        """Port location.

        Returns
        -------
        list
        """
        return self._location

    @location.setter
    def location(self, location_xy):
        # The command must be called two times.
        self._app.modeler.schematic.components[self.schematic_id].location = location_xy
        self._app.modeler.schematic.components[self.schematic_id].location = location_xy
        self._location = location_xy

    @property
    def use_symbol_color(self):
        """Use symbol color.

        Returns
        -------
        list
        """
        return self._use_symbol_color

    @use_symbol_color.setter
    def use_symbol_color(self, use_color=True):
        self._app.modeler.schematic.components[self.schematic_id].usesymbolcolor = use_color
        self._app.modeler.schematic.components[self.schematic_id].set_use_symbol_color(use_color)
        self._use_symbol_color = use_color

    @property
    def impedance(self):
        """Port termination.

        Returns
        -------
        list
        """
        return [self._props["rz"], self._props["iz"]]

    @impedance.setter
    def impedance(self, termination=None):
        if termination and len(termination) == 2:
            self._app.modeler.schematic.components[self.schematic_id].change_property(
                ["NAME:rz", "Value:=", termination[0]]
            )
            self._app.modeler.schematic.components[self.schematic_id].change_property(
                ["NAME:iz", "Value:=", termination[1]]
            )
            self._props["rz"] = termination[0]
            self._props["iz"] = termination[1]

    @property
    def enable_noise(self):
        """Enable noise.

        Returns
        -------
        bool
        """
        return self._props["EnableNoise"]

    @enable_noise.setter
    def enable_noise(self, enable=False):
        self._app.modeler.schematic.components[self.schematic_id].change_property(
            ["NAME:EnableNoise", "Value:=", enable]
        )
        self._props["EnableNoise"] = enable

    @property
    def noise_temperature(self):
        """Enable noise.

        Returns
        -------
        str
        """
        return self._props["noisetemp"]

    @noise_temperature.setter
    def noise_temperature(self, noise=None):
        if noise:
            self._app.modeler.schematic.components[self.schematic_id].change_property(
                ["NAME:noisetemp", "Value:=", noise]
            )
            self._props["noisetemp"] = noise

    @property
    def microwave_symbol(self):
        """Enable microwave symbol.

        Returns
        -------
        bool
        """
        if self._props["SymbolType"] == 1:
            return True
        else:
            return False

    @microwave_symbol.setter
    def microwave_symbol(self, enable=False):
        if enable:
            self._props["SymbolType"] = 1
        else:
            self._props["SymbolType"] = 0
        self.update()

    @property
    def reference_node(self):
        """Reference node.

        Returns
        -------
        str
        """
        if self._props["RefNode"] == "Z":
            return "Ground"
        return self._props["RefNode"]

    @reference_node.setter
    def reference_node(self, ref_node=None):
        if ref_node:
            self._logger.warning("Set reference node only working with GRPC")
            if ref_node == "Ground":
                ref_node = "Z"
            self._props["RefNode"] = ref_node
            self.update()

    @property
    def enabled_sources(self):
        """Enabled sources.

        Returns
        -------
        list
        """
        return self._props["EnabledPorts"]

    @enabled_sources.setter
    def enabled_sources(self, sources=None):
        if sources:
            self._props["EnabledPorts"] = sources
            self.update()

    @property
    def enabled_analyses(self):
        """Enabled analyses.

        Returns
        -------
        dict
        """
        return self._props["EnabledAnalyses"]

    @enabled_analyses.setter
    def enabled_analyses(self, analyses=None):
        if analyses:
            self._props["EnabledAnalyses"] = analyses
            self.update()

    @pyaedt_function_handler()
    def _excitation_props(self, port):
        excitation_prop_dict = {}
        for comp in self._app.modeler.schematic.components:
            if (
                "PortName" in self._app.modeler.schematic.components[comp].parameters.keys()
                and self._app.modeler.schematic.components[comp].parameters["PortName"] == port
            ):
                excitation_prop_dict["rz"] = "50ohm"
                excitation_prop_dict["iz"] = "0ohm"
                excitation_prop_dict["term"] = None
                excitation_prop_dict["TerminationData"] = None
                excitation_prop_dict["RefNode"] = "Z"
                excitation_prop_dict["EnableNoise"] = False
                excitation_prop_dict["noisetemp"] = "16.85cel"

                if "RefNode" in self._app.modeler.schematic.components[comp].parameters:
                    excitation_prop_dict["RefNode"] = self._app.modeler.schematic.components[comp].parameters["RefNode"]
                if "term" in self._app.modeler.schematic.components[comp].parameters:
                    excitation_prop_dict["term"] = self._app.modeler.schematic.components[comp].parameters["term"]
                    excitation_prop_dict["TerminationData"] = self._app.modeler.schematic.components[comp].parameters[
                        "TerminationData"
                    ]
                else:
                    if "rz" in self._app.modeler.schematic.components[comp].parameters:
                        excitation_prop_dict["rz"] = self._app.modeler.schematic.components[comp].parameters["rz"]
                        excitation_prop_dict["iz"] = self._app.modeler.schematic.components[comp].parameters["iz"]

                if "EnableNoise" in self._app.modeler.schematic.components[comp].parameters:
                    if self._app.modeler.schematic.components[comp].parameters["EnableNoise"] == "true":
                        excitation_prop_dict["EnableNoise"] = True
                    else:
                        excitation_prop_dict["EnableNoise"] = False

                    excitation_prop_dict["noisetemp"] = self._app.modeler.schematic.components[comp].parameters[
                        "noisetemp"
                    ]

                if not self._app.design_properties or not self._app.design_properties["NexximPorts"]["Data"]:
                    excitation_prop_dict["SymbolType"] = 0
                else:
                    excitation_prop_dict["SymbolType"] = self._app.design_properties["NexximPorts"]["Data"][port][
                        "SymbolType"
                    ]

                if "pnum" in self._app.modeler.schematic.components[comp].parameters:
                    excitation_prop_dict["pnum"] = self._app.modeler.schematic.components[comp].parameters["pnum"]
                else:
                    excitation_prop_dict["pnum"] = None
                source_port = []
                if not self._app.design_properties:
                    enabled_ports = None
                else:
                    enabled_ports = self._app.design_properties["ComponentConfigurationData"]["EnabledPorts"]
                if isinstance(enabled_ports, dict):
                    for source in enabled_ports:
                        if enabled_ports[source] and port in enabled_ports[source]:
                            source_port.append(source)
                excitation_prop_dict["EnabledPorts"] = source_port

                components_port = []
                if not self._app.design_properties:
                    multiple = None
                else:
                    multiple = self._app.design_properties["ComponentConfigurationData"]["EnabledMultipleComponents"]
                if isinstance(multiple, dict):
                    for source in multiple:
                        if multiple[source] and port in multiple[source]:
                            components_port.append(source)
                excitation_prop_dict["EnabledMultipleComponents"] = components_port

                port_analyses = {}
                if not self._app.design_properties:
                    enabled_analyses = None
                else:
                    enabled_analyses = self._app.design_properties["ComponentConfigurationData"]["EnabledAnalyses"]
                if isinstance(enabled_analyses, dict):
                    for source in enabled_analyses:
                        if (
                            enabled_analyses[source]
                            and port in enabled_analyses[source]
                            and source in excitation_prop_dict["EnabledPorts"]
                        ):
                            port_analyses[source] = enabled_analyses[source][port]
                excitation_prop_dict["EnabledAnalyses"] = port_analyses
                return OrderedDict(excitation_prop_dict)

    @pyaedt_function_handler()
    def update(self):
        """Update the excitation in AEDT.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        # self._logger.warning("Property port update only working with GRPC")

        if self._props["RefNode"] == "Ground":
            self._props["RefNode"] = "Z"

        arg0 = [
            "NAME:" + self.name,
            "IIPortName:=",
            self.name,
            "SymbolType:=",
            self._props["SymbolType"],
            "DoPostProcess:=",
            False,
        ]

        arg1 = ["NAME:ChangedProps"]
        arg2 = []

        # Modify RefNode
        if self._props["RefNode"] != "Z":
            arg2 = [
                "NAME:NewProps",
                ["NAME:RefNode", "PropType:=", "TextProp", "OverridingDef:=", True, "Value:=", self._props["RefNode"]],
            ]

        # Modify Termination
        if self._props["term"] and self._props["TerminationData"]:
            arg2 = [
                "NAME:NewProps",
                ["NAME:term", "PropType:=", "TextProp", "OverridingDef:=", True, "Value:=", self._props["term"]],
            ]

        for prop in self._props:
            skip1 = (prop == "rz" or prop == "iz") and isinstance(self._props["term"], str)
            skip2 = prop == "EnabledPorts" or prop == "EnabledMultipleComponents" or prop == "EnabledAnalyses"
            skip3 = prop == "SymbolType"
            skip4 = prop == "TerminationData" and not isinstance(self._props["term"], str)
            if not skip1 and not skip2 and not skip3 and not skip4 and self._props[prop] is not None:
                command = ["NAME:" + prop, "Value:=", self._props[prop]]
                arg1.append(command)

        arg1 = [["NAME:Properties", arg2, arg1]]
        self._app.odesign.ChangePortProperty(self.name, arg0, arg1)

        for source in self._app.sources:
            self._app.sources[source].update()
        return True

    @pyaedt_function_handler()
    def delete(self):
        """Delete the port in AEDT.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        self._app.modeler._odesign.DeletePort(self.name)
        return True

    @property
    def _logger(self):
        """Logger."""
        return self._app.logger


class NetworkObject(BoundaryObject):
    """Manages networks in Icepak projects."""

    def __init__(self, app, name=None, props=None, create=False):
        if not app.design_type == "Icepak":  # pragma: no cover
            raise NotImplementedError("Networks object works only with Icepak projects ")
        if name is None:
            self._name = generate_unique_name("Network")
        else:
            self._name = name
        super(NetworkObject, self).__init__(app, self._name, props, "Network", False)
        if self.props is None:
            self._props = {}
        self._nodes = []
        self._links = []
        self._schematic_data = OrderedDict({})
        self._update_from_props()
        if create:
            self.create()

    def _clean_list(self, arg):
        new_list = []
        for item in arg:
            if isinstance(item, list):
                if item[0] == "NAME:PageNet":
                    page_net_list = []
                    for i in item:
                        if isinstance(i, list):
                            name = page_net_list[-1]
                            page_net_list.pop(-1)
                            for j in i:
                                page_net_list.append(name)
                                page_net_list.append(j)
                        else:
                            page_net_list.append(i)
                    new_list.append(page_net_list)
                else:
                    new_list.append(self._clean_list(item))
            else:
                new_list.append(item)
        return new_list

    @pyaedt_function_handler
    def create(self):
        """Create network in AEDT.

        Returns
        -------
        bool:
            True if successful.
        """
        if not self.props.get("Faces", None):
            self.props["Faces"] = [node.props["FaceID"] for _, node in self.face_nodes.items()]
        if not self.props.get("SchematicData", None):
            self.props["SchematicData"] = OrderedDict({})
        args = self._get_args()

        clean_args = self._clean_list(args)
        self._app.oboundary.AssignNetworkBoundary(clean_args)
        return True

    @pyaedt_function_handler
    def _update_from_props(self):
        nodes = self.props.get("Nodes", None)
        if nodes is not None:
            nd_name_list = [node.name for node in self._nodes]
            for node_name, node_dict in nodes.items():
                if node_name not in nd_name_list:
                    nd_type = node_dict.get("NodeType", None)
                    if nd_type == "InternalNode":
                        self.add_internal_node(
                            node_name,
                            node_dict.get("Power", node_dict.get("Power Variation Data", None)),
                            mass=node_dict.get("Mass", None),
                            specific_heat=node_dict.get("SpecificHeat", None),
                        )
                    elif nd_type == "BoundaryNode":
                        self.add_boundary_node(
                            node_name,
                            assignment_type=node_dict["ValueType"].replace("Value", ""),
                            value=node_dict[node_dict["ValueType"].replace("Value", "")],
                        )
                    else:
                        if (
                            node_dict["ThermalResistance"] == "NoResistance"
                            or node_dict["ThermalResistance"] == "Specified"
                        ):
                            node_material, node_thickness = None, None
                            node_resistance = node_dict["Resistance"]
                        else:
                            node_thickness, node_material = node_dict["Thickness"], node_dict["Material"]
                            node_resistance = None
                        self.add_face_node(
                            node_dict["FaceID"],
                            name=node_name,
                            thermal_resistance=node_dict["ThermalResistance"],
                            material=node_material,
                            thickness=node_thickness,
                            resistance=node_resistance,
                        )
        links = self.props.get("Links", None)
        if links is not None:
            l_name_list = [l.name for l in self._links]
            for link_name, link_dict in links.items():
                if link_name not in l_name_list:
                    self.add_link(link_dict[0], link_dict[1], link_dict[-1], link_name)

    @property
    def auto_update(self):
        """Get if auto-update is enabled.

        Returns
        -------
        bool:
            Whether auto-update is enabled.
        """
        return False

    @auto_update.setter
    def auto_update(self, b):
        """Set auto-update on or off.

        Parameters
        ----------
        b : bool
            Whether to enable auto-update.

        """
        if b:
            self._app.logger.warning(
                "Network objects auto_update property is False by default" " and cannot be set to True."
            )

    @property
    def links(self):
        """Get links of the network.

        Returns
        -------
        dict:
            Links dictionary.

        """
        self._update_from_props()
        return {link.name: link for link in self._links}

    @property
    def r_links(self):
        """Get r-links of the network.

        Returns
        -------
        dict:
            R-links dictionary.

        """
        self._update_from_props()
        return {link.name: link for link in self._links if link._link_type[0] == "R-Link"}

    @property
    def c_links(self):
        """Get c-links of the network.

        Returns
        -------
        dict:
            C-links dictionary.

        """
        self._update_from_props()
        return {link.name: link for link in self._links if link._link_type[0] == "C-Link"}

    @property
    def nodes(self):
        """Get nodes of the network.

        Returns
        -------
        dict:
            Nodes dictionary.

        """
        self._update_from_props()
        return {node.name: node for node in self._nodes}

    @property
    def face_nodes(self):
        """Get face nodes of the network.

        Returns
        -------
        dict:
            Face nodes dictionary.

        """
        self._update_from_props()
        return {node.name: node for node in self._nodes if node.node_type == "FaceNode"}

    @property
    def faces_ids_in_network(self):
        """Get ID of faces included in the network.

        Returns
        -------
        list:
            Face IDs.

        """
        out_arr = []
        for _, node_dict in self.face_nodes.items():
            out_arr.append(node_dict.props["FaceID"])
        return out_arr

    @property
    def objects_in_network(self):
        """Get objects included in the network.

        Returns
        -------
        list:
            Objects names.

        """
        out_arr = []
        for face_id in self.faces_ids_in_network:
            out_arr.append(self._app.oeditor.GetObjectNameByFaceID(face_id))
        return out_arr

    @property
    def internal_nodes(self):
        """Get internal nodes.

        Returns
        -------
        dict:
            Internal nodes.

        """
        self._update_from_props()
        return {node.name: node for node in self._nodes if node.node_type == "InternalNode"}

    @property
    def boundary_nodes(self):
        """Get boundary nodes.

        Returns
        -------
        dict:
            Boundary nodes.

        """
        self._update_from_props()
        return {node.name: node for node in self._nodes if node.node_type == "BoundaryNode"}

    @property
    def name(self):
        """Get network name.

        Returns
        -------
        str
            Network name.
        """
        return self._name

    @name.setter
    def name(self, new_network_name):
        """Set new name of the network.

        Parameters
        ----------
        new_network_name : str
            New name of the network.
        """
        bound_names = [b.name for b in self._app.boundaries]
        if self.name in bound_names:
            if new_network_name not in bound_names:
                if new_network_name != self._name:
                    self._app._oboundary.RenameBoundary(self._name, new_network_name)
                    self._name = new_network_name
            else:
                self._app.logger.warning("Name %s already assigned in the design", new_network_name)
        else:
            self._name = new_network_name

    @pyaedt_function_handler()
    def add_internal_node(self, name, power, mass=None, specific_heat=None):
        """Parameters
        ----------
        name : str
            Name of the node.
        power : str or float or dict
            String, float, or dictionary containing the value of the assignment.
            If a float is passed, the ``"W"`` unit is used. A dictionary can be
            passed to use temperature-dependent or transient
            assignments.
        mass : str or float, optional
            Value of the mass assignment. This parameter is relevant only
            if the solution is transient. If a float is passed, the ``"Kg"`` unit
            is used. The default is ``None``, in which case ``"0.001kg"`` is used.
        specific_heat : str or float, optional
            Value of the specific heat assignment. This parameter is
            relevant only if the solution is transient. If a float is passed,
            the ``"J_per_Kelkg"`` unit is used. The default is ``None`, in
            which case ``"1000J_per_Kelkg"`` is used.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------
        >>> import pyaedt
        >>> app = pyaedt.Icepak()
        >>> network = pyaedt.modules.Boundary.Network(app)
        >>> network.add_internal_node("TestNode", {"Type": "Transient",
        >>>                                        "Function": "Linear", "Values": ["0.01W", "1"]})
        """
        if self._app.solution_type != "SteadyState" and mass is None and specific_heat is None:
            self._app.logger.warning("The solution is transient but neither mass nor specific heat is assigned.")
        if self._app.solution_type == "SteadyState" and (
            mass is not None or specific_heat is not None
        ):  # pragma: no cover
            self._app.logger.warning(
                "Because the solution is steady state, neither mass nor specific heat assignment is relevant."
            )
        if isinstance(power, (int, float)):
            power = str(power) + "W"
        props_dict = {"Power": power}
        if mass is not None:
            if isinstance(mass, (int, float)):
                mass = str(mass) + "kg"
            props_dict.update({"Mass": mass})
        if specific_heat is not None:
            if isinstance(specific_heat, (int, float)):
                specific_heat = str(specific_heat) + "J_per_Kelkg"
            props_dict.update({"SpecificHeat": specific_heat})
        new_node = self._Node(name, self._app, node_type="InternalNode", props=props_dict, network=self)
        self._nodes.append(new_node)
        self._add_to_props(new_node)
        return new_node

    @pyaedt_function_handler()
    def add_boundary_node(self, name, assignment_type, value):
        """Parameters
        ----------
        name : str
            Name of the node.
        assignment_type : str
            Type assignment. Options are ``"Power"`` and ``"Temperature"``.
        value : str or float or dict
            String, float, or dictionary containing the value of the assignment.
            If a float is passed the ``"W"`` or ``"cel"`` unit is used, depending on
            the selection for the ``assignment_type`` parameter. If ``"Power"`
            is selected for the type, a dictionary can be passed to use
            temperature-dependent or transient assignment.

        Returns
        -------
        bool
            ``True`` if successful.

        Examples
        --------
        >>> import pyaedt
        >>> app = pyaedt.Icepak()
        >>> network = pyaedt.modules.Boundary.Network(app)
        >>> network.add_boundary_node("TestNode", "Temperature", 2)
        >>> ds = app.create_dataset1d_design("Test_DataSet", [1, 2, 3], [3, 4, 5])
        >>> network.add_boundary_node("TestNode", "Power", {"Type": "Temp Dep",
        >>>                                                       "Function": "Piecewise Linear",
        >>>                                                       "Values": "Test_DataSet"})
        """
        if assignment_type not in ["Power", "Temperature", "PowerValue", "TemperatureValue"]:  # pragma: no cover
            raise AttributeError('``type`` can be only ``"Power"`` or ``"Temperature"``.')
        if isinstance(value, (float, int)):
            if assignment_type == "Power" or assignment_type == "PowerValue":
                value = str(value) + "W"
            else:
                value = str(value) + "cel"
        if isinstance(value, dict) and (
            assignment_type == "Temperature" or assignment_type == "TemperatureValue"
        ):  # pragma: no cover
            raise AttributeError(
                "Temperature-dependent or transient assignment is not supported in a temperature boundary node."
            )
        if not assignment_type.endswith("Value"):
            assignment_type += "Value"
        new_node = self._Node(
            name,
            self._app,
            node_type="BoundaryNode",
            props={"ValueType": assignment_type, assignment_type.removesuffix("Value"): value},
            network=self,
        )
        self._nodes.append(new_node)
        self._add_to_props(new_node)
        return new_node

    @pyaedt_function_handler()
    def _add_to_props(self, new_node, type_dict="Nodes"):
        try:
            self.props[type_dict].update({new_node.name: new_node.props})
        except KeyError:
            self.props[type_dict] = {new_node.name: new_node.props}

    @pyaedt_function_handler()
    def add_face_node(
        self, face_id, name=None, thermal_resistance="NoResistance", material=None, thickness=None, resistance=None
    ):
        """Create a face node in the network.

        Parameters
        ----------
        face_id : int
            Face ID.
        name : str, optional
            Name of the node. Default is ``None``.
        thermal_resistance : str
            Thermal resistance value and unit. Default is ``"NoResistance"``.
        material : str, optional
            Material specification (required if ``thermal_resistance="Compute"``).
            Default is ``None``.
        thickness : str or float, optional
            Thickness value and unit (required if ``thermal_resistance="Compute"``).
            If a float is passed, ``"mm"`` unit is automatically used. Default is ``None``.
        resistance : str or float, optional
            Resistance value and unit (required if ``thermal_resistance="Specified"``).
            If a float is passed, ``"cel_per_w"`` unit is automatically used. Default is ``None``.

        Returns
        -------
        bool
            True if successful.

        Examples
        --------
        >>> import pyaedt
        >>> app = pyaedt.Icepak()
        >>> network = pyaedt.modules.Boundary.Network(app)
        >>> box = app.modeler.create_box([5, 5, 5], [20, 50, 80])
        >>> faces_ids = [face.id for face in box.faces]
        >>> network.add_face_node(faces_ids[0])
        >>> network.add_face_node(faces_ids[1], name="TestNode", thermal_resistance="Compute",
        >>>                       material="Al-Extruded", thickness="2mm")
        >>> network.add_face_node(faces_ids[2], name="TestNode", thermal_resistance="Specified", resistance=2)
        """
        props_dict = OrderedDict({})
        props_dict["FaceID"] = face_id
        if thermal_resistance is not None:
            if thermal_resistance == "Compute":
                if resistance is not None:
                    self._app.logger.info(
                        '``resistance`` assignment is incompatible with ``thermal_resistance="Compute"``'
                        "and it is ignored."
                    )
                if material is not None or thickness is not None:
                    props_dict["ThermalResistance"] = thermal_resistance
                    props_dict["Material"] = material
                    if not isinstance(thickness, str):
                        thickness = str(thickness) + "mm"
                    props_dict["Thickness"] = thickness
                else:  # pragma: no cover
                    raise AttributeError(
                        'If ``thermal_resistance="Compute"`` both ``material`` and ``thickness``'
                        "arguments must be prescribed."
                    )
            if thermal_resistance == "Specified":
                if material is not None or thickness is not None:
                    self._app.logger.warning(
                        "Because ``material`` and ``thickness`` assignments are incompatible with"
                        '``thermal_resistance="Specified"``, they are ignored.'
                    )
                if resistance is not None:
                    props_dict["ThermalResistance"] = thermal_resistance
                    if not isinstance(resistance, str):
                        resistance = str(resistance) + "cel_per_w"
                    props_dict["Resistance"] = resistance
                else:  # pragma : no cover
                    raise AttributeError(
                        'If ``thermal_resistance="Specified"``, ``resistance`` argument must be prescribed.'
                    )

        if name is None:
            name = "FaceID" + str(face_id)
        new_node = self._Node(name, self._app, node_type="FaceNode", props=props_dict, network=self)
        self._nodes.append(new_node)
        self._add_to_props(new_node)
        return new_node

    @pyaedt_function_handler()
    def add_nodes_from_dictionaries(self, nodes_dict):
        """Add nodes to the network from dictionary.

        Parameters
        ----------
        nodes_dict : list or dict
            A dictionary or list of dictionaries containing nodes to add to the network. Different
            node types require different key and value pairs:

            - Face nodes must contain the ``"ID"`` key associated with an integer containing the face ID.
              Optional keys and values pairs are:

              - ``"ThermalResistance"``: a string specifying the type of thermal resistance.
                 Options are ``"NoResistance"`` (default), ``"Compute"``, and ``"Specified"``.
              - ``"Thickness"``: a string with the thickness value and unit (required if ``"Compute"``
              is selected for ``"ThermalResistance"``).
              - ``"Material"``: a string with the name of the material (required if ``"Compute"`` is
              selected for ``"ThermalResistance"``).
              - ``"Resistance"``: a string with the resistance value and unit (required if
                 ``"Specified"`` is selected for ``"ThermalResistance"``).
              - ``"Name"``: a string with the name of the node. If not
                 specified, a name is generated automatically.


            - Internal nodes must contain the following keys and values pairs:

              - ``"Name"``: a string with the node name
              - ``"Power"``: a string with the assigned power or a dictionary for transient or
              temperature-dependent assignment
              Optional keys and values pairs:
              - ``"Mass"``: a string with the mass value and unit
              - ``"SpecificHeat"``: a string with the specific heat value and unit

            - Boundary nodes must contain the following keys and values pairs:
              - ``"Name"``: a string with the node name
              - ``"ValueType"``: a string specifying the type of value (``"Power"`` or
              ``"Temperature"``)
              Depending on the ``"ValueType"`` choice, one of the following keys and values pairs must
              be used:
              - ``"Power"``: a string with the power value and unit or a dictionary for transient or
              temperature-dependent assignment
              - ``"Temperature"``: a string with the temperature value and unit or a dictionary for
              transient or temperature-dependent assignment
              According to the ``"ValueType"`` choice, ``"Power"`` or ``"Temperature"`` key must be
              used. Their associated value a string with the value and unit of the quantity prescribed or
              a dictionary for transient or temperature dependent assignment.

            All the temperature dependent or thermal dictionaries should contain three keys:
            ``"Type"``, ``"Function"``, and ``"Values"``. Accepted ``"Type"`` values are:
            ``"Temp Dep"`` and ``"Transient"``. Accepted ``"Function"`` are: ``"Linear"``,
            ``"Power Law"``, ``"Exponential"``, ``"Sinusoidal"``, ``"Square Wave"``, and
            ``"Piecewise Linear"``. ``"Temp Dep"`` only support the latter. ``"Values"``
            contains a list of strings containing the parameters required by the ``"Function"``
            selection (e.g. ``"Linear"`` requires two parameters: the value of the variable at t=0
            and the slope of the line). The parameters required by each ``Function`` option is in
            Icepak documentation. The parameters must contain the units where needed.

        Returns
        -------
        bool
            ``True`` if successful. ``False`` otherwise.

        Examples
        --------
        >>> import pyaedt
        >>> app = pyaedt.Icepak()
        >>> network = pyaedt.modules.Boundary.Network(app)
        >>> box = app.modeler.create_box([5, 5, 5], [20, 50, 80])
        >>> faces_ids = [face.id for face in box.faces]
        >>> nodes_dict = [
        >>>         {"FaceID": faces_ids[0]},
        >>>         {"Name": "TestNode", "FaceID": faces_ids[1],
        >>>          "ThermalResistance": "Compute", "Thickness": "2mm"},
        >>>         {"FaceID": faces_ids[2], "ThermalResistance": "Specified", "Resistance": "2cel_per_w"},
        >>>         {"Name": "Junction", "Power": "1W"}]
        >>> network.add_nodes_from_dictionaries(nodes_dict)

        """
        if isinstance(nodes_dict, dict):
            nodes_dict = [nodes_dict]
        for node_dict in nodes_dict:
            if "FaceID" in node_dict.keys():
                self.add_face_node(
                    face_id=node_dict["FaceID"],
                    name=node_dict.get("Name", None),
                    thermal_resistance=node_dict.get("ThermalResistance", None),
                    material=node_dict.get("Material", None),
                    thickness=node_dict.get("Thickness", None),
                    resistance=node_dict.get("Resistance", None),
                )
            elif "ValueType" in node_dict.keys():
                if node_dict["ValueType"].endswith("Value"):
                    value = node_dict[node_dict["ValueType"].removesuffix("Value")]
                else:
                    value = node_dict[node_dict["ValueType"]]
                self.add_boundary_node(name=node_dict["Name"], assignment_type=node_dict["ValueType"], value=value)
            else:
                self.add_internal_node(
                    name=node_dict["Name"],
                    power=node_dict.get("Power", None),
                    mass=node_dict.get("Mass", None),
                    specific_heat=node_dict.get("SpecificHeat", None),
                )
        return True

    @pyaedt_function_handler()
    def add_link(self, node1, node2, value, name=None):
        """Create links in the network object.

        Parameters
        ----------
        node1 : str or int
            String containing one of the node names that the link is connecting or an integer
            containing the ID of the face. If an ID is used and the node associated with the
            corresponding face is not created yet, it is added automatically.
        node2 : str or int
            String containing one of the node names that the link is connecting or an integer
            containing the ID of the face. If an ID is used and the node associated with the
            corresponding face is not created yet, it is added atuomatically.
        value : str or float
            String containing the value and unit of the connection. If a float is passed, an
            R-Link is added to the network and the ``"cel_per_w"`` unit is used.
        name : str, optional
            Name of the link. The default is ``None``, in which case a name is
            automatically generated.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        Examples
        --------
        >>> import pyaedt
        >>> app = pyaedt.Icepak()
        >>> network = pyaedt.modules.Boundary.Network(app)
        >>> box = app.modeler.create_box([5, 5, 5], [20, 50, 80])
        >>> faces_ids = [face.id for face in box.faces]
        >>> connection = {"Name": "LinkTest", "Connection": [faces_ids[1], faces_ids[0]], "Value": "1cel_per_w"}
        >>> network.add_links_from_dictionaries(connection)

        """
        if name is None:
            new_name = True
            while new_name:
                name = generate_unique_name("Link")
                if name not in self.links.keys():
                    new_name = False
        new_link = self._Link(node1, node2, value, name, self)
        self._links.append(new_link)
        self._add_to_props(new_link, "Links")
        return True

    @pyaedt_function_handler()
    def add_links_from_dictionaries(self, connections):
        """Create links in the network object.

        Parameters
        ----------
        connections : dict or list of dict
            Dictionary or list of dictionaries containing the links between nodes. Each dictionary
            consists of these elements:

            - ``"Link"``: a three-item list consisting of the two nodes that the link is connecting and
               the value with unit of the link. The node of the connection can be referred to with the
               name (str) or face ID (int). The link type (resistance, heat transfer coefficient, or
               mass flow) is determined automatically from the unit.
            - ``"Name"`` (optional): a string specifying the name of the link.


        Returns
        -------
        bool
            ``True`` if successful.

        Examples
        --------
        >>> import pyaedt
        >>> app = pyaedt.Icepak()
        >>> network = pyaedt.modules.Boundary.Network(app)
        >>> box = app.modeler.create_box([5, 5, 5], [20, 50, 80])
        >>> faces_ids = [face.id for face in box.faces]
        >>> [network.add_face_node(faces_ids[i]) for i in range(2)]
        >>> connection = {"Name": "LinkTest", "Link": [faces_ids[1], faces_ids[0], "1cel_per_w"]}
        >>> network.add_links_from_dictionaries(connection)

        """
        if isinstance(connections, dict):
            connections = [connections]
        for connection in connections:
            name = connection.get("Name", None)
            try:
                self.add_link(connection["Link"][0], connection["Link"][1], connection["Link"][2], name)
            except Exception:  # pragma : no cover
                if name:
                    self._app.logger.error("Failed to add " + name + " link.")
                else:
                    self._app.logger.error(
                        "Failed to add link associated with the following dictionary:\n" + str(connection)
                    )
        return True

    @pyaedt_function_handler()
    def update(self):
        """Update the network in AEDT.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        """
        if self.name in [b.name for b in self._app.boundaries]:
            self.delete()
            try:
                self.create()
                self._app.boundaries.append(self)
                return True
            except Exception:  # pragma : no cover
                self._app.odesign.Undo()
                self._app.logger.error("Update of network object failed.")
                return False
        else:  # pragma : no cover
            self._app.logger.warning("Network object not yet created in design.")
            return False

    @pyaedt_function_handler()
    def update_assignment(self):
        """Update assignments of the network.
        """
        return self.update()

    class _Link:
        def __init__(self, node_1, node_2, value, name, network):
            self.name = name
            if not isinstance(node_1, str):
                node_1 = "FaceID" + str(node_1)
            if not isinstance(node_2, str):
                node_2 = "FaceID" + str(node_2)
            if not isinstance(value, str):
                value = str(value) + "cel_per_w"
            self.node_1 = node_1
            self.node_2 = node_2
            self.value = value
            self._network = network

        @property
        def _link_type(self):
            unit2type_conversion = {
                "g_per_s": ["C-Link", "Node1ToNode2"],
                "kg_per_s": ["C-Link", "Node1ToNode2"],
                "lbm_per_min": ["C-Link", "Node1ToNode2"],
                "lbm_per_s": ["C-Link", "Node1ToNode2"],
                "Kel_per_W": ["R-Link", "R"],
                "cel_per_w": ["R-Link", "R"],
                "FahSec_per_btu": ["R-Link", "R"],
                "Kels_per_J": ["R-Link", "R"],
                "w_per_m2kel": ["R-Link", "HTC"],
                "w_per_m2Cel": ["R-Link", "HTC"],
                "btu_per_rankHrFt2": ["R-Link", "HTC"],
                "btu_per_fahHrFt2": ["R-Link", "HTC"],
                "btu_per_rankSecFt2": ["R-Link", "HTC"],
                "btu_per_fahSecFt2": ["R-Link", "HTC"],
                "w_per_cm2kel": ["R-Link", "HTC"],
            }
            _, unit = decompose_variable_value(self.value)
            return unit2type_conversion[unit]

        @property
        def props(self):
            """Get link properties.

            Returns
            -------
            list
                First two elements of the list are the node names that the link connects,
                the third element is the link type while the fourth contains the value
                associated with the link.
            """
            return [self.node_1, self.node_2] + self._link_type + [self.value]

        @pyaedt_function_handler
        def delete_link(self):
            """Delete link from network.
            """
            self._network.props["Links"].pop(self.name)
            self._network._links.remove(self)

    class _Node:
        def __init__(self, name, app, network, node_type=None, props=None):
            self.name = name
            self._type = node_type
            self._app = app
            self._props = props
            self._node_props()
            self._network = network

        @pyaedt_function_handler
        def delete_node(self):
            """Delete node from network.
            """
            self._network.props["Nodes"].pop(self.name)
            self._network._nodes.remove(self)

        @property
        def node_type(self):
            """Get node type.

            Returns
            -------
            str
                Node type.
            """
            if self._type is None:  # pragma: no cover
                if self.props is None:
                    self._app.logger.error(
                        "Cannot define node_type. Both its assignment and properties assignment are missing."
                    )
                    return None
                else:
                    type_in_dict = self.props.get("NodeType", None)
                    if type_in_dict is None:
                        self._type = "FaceNode"
                    else:
                        self._type = type_in_dict
            return self._type

        @property
        def props(self):
            """Get properties of the node.

            Returns
            -------
            dict
                Node properties.
            """
            return self._props

        @props.setter
        def props(self, props):
            """Set properties of the node.

            Parameters
            ----------
            props : dict
                Node properties.
            """
            self._props = props
            self._node_props()

        def _node_props(self):
            face_node_default_dict = {
                "FaceID": None,
                "ThermalResistance": "NoResistance",
                "Thickness": "1mm",
                "Material": "Al-Extruded",
                "Resistance": "0cel_per_w",
            }
            boundary_node_default_dict = {
                "NodeType": "BoundaryNode",
                "ValueType": "PowerValue",
                "Power": "0W",
                "Temperature": "25cel",
            }
            internal_node_default_dict = {
                "NodeType": "InternalNode",
                "Power": "0W",
                "Mass": "0.001kg",
                "SpecificHeat": "1000J_per_Kelkg",
            }
            if self.props is None:
                if self.node_type == "InternalNode":
                    self._props = internal_node_default_dict
                elif self.node_type == "FaceNode":
                    self._props = face_node_default_dict
                elif self.node_type == "BoundaryNode":
                    self._props = boundary_node_default_dict
            else:
                if self.node_type == "InternalNode":
                    self._props = self._create_node_dict(internal_node_default_dict)
                elif self.node_type == "FaceNode":
                    self._props = self._create_node_dict(face_node_default_dict)
                elif self.node_type == "BoundaryNode":
                    self._props = self._create_node_dict(boundary_node_default_dict)

        @pyaedt_function_handler()
        def _create_node_dict(self, default_dict):
            node_dict = self.props
            node_name = node_dict.get("Name", self.name)
            if not node_name:
                try:
                    self.name = "Face" + str(node_dict["FaceID"])
                except KeyError:  # pragma: no cover
                    raise KeyError('"Name" key is needed for "BoundaryNodes" and "InternalNodes" dictionaries.')
            else:
                self.name = node_name
                node_dict.pop("Name", None)
            node_args = copy.deepcopy(default_dict)
            for k in node_dict.keys():
                val = node_dict[k]
                if isinstance(val, dict):  # pragma : no cover
                    val = self._app._parse_variation_data(
                        k, val["Type"], variation_value=val["Values"], function=val["Function"]
                    )
                    node_args.pop(k)
                    node_args.update(val)
                else:
                    node_args[k] = val

            return node_args
