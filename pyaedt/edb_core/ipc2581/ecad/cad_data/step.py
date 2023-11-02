import math

from pyaedt.edb_core.ipc2581.ecad.cad_data.component import Component
from pyaedt.edb_core.ipc2581.ecad.cad_data.layer_feature import LayerFeature
from pyaedt.edb_core.ipc2581.ecad.cad_data.logical_net import LogicalNet
from pyaedt.edb_core.ipc2581.ecad.cad_data.package import Package
from pyaedt.edb_core.ipc2581.ecad.cad_data.padstack_def import PadstackDef
from pyaedt.edb_core.ipc2581.ecad.cad_data.phy_net import PhyNet
from pyaedt.edb_core.ipc2581.ecad.cad_data.profile import Profile
from pyaedt.generic.general_methods import ET, pyaedt_function_handler


class Step(object):
    def __init__(self, caddata, edb, units, ipc):
        self.design_name = caddata.design_name
        self._pedb = edb
        self._ipc = ipc
        self.units = units
        self._cad_data = caddata
        self._padstack_defs = {}
        self._profile = Profile()
        self._packages = {}
        self._components = []
        self._logical_nets = []
        self._physical_nets = []
        self._layer_features = []

    @property
    def padstack_defs(self):
        return self._padstack_defs

    @padstack_defs.setter
    def padstack_defs(self, value):  # pragma no cover
        if isinstance(value, list):
            if len([pad for pad in value if isinstance(pad, PadstackDef)]) == len(value):
                self._padstack_defs = value

    @property
    def packages(self):
        return self._packages

    @packages.setter
    def packages(self, value):  # pragma no cover
        if isinstance(value, list):
            if len([pkg for pkg in value if isinstance(pkg, Package)]) == len(value):
                self._packages = value

    @property
    def components(self):
        return self._components

    @components.setter
    def components(self, value):  # pragma no cover
        if isinstance(value, list):
            if len([cmp for cmp in value if isinstance(cmp, Component)]) == len(value):
                self._components = value

    @property
    def logical_nets(self):
        return self._logical_nets

    @pyaedt_function_handler()
    def add_logical_net(self, net=None):  # pragma no cover
        net_name = net.name
        logical_net = LogicalNet()
        logical_net.name = net_name
        net_pins = list(net.PadstackInstances)
        for pin in net_pins:
            new_pin_ref = logical_net.get_pin_ref_def()
            new_pin_ref.pin = pin.GetName()
            new_pin_ref.component_ref = pin.GetComponent().GetName()
            logical_net.pin_ref.append(new_pin_ref)
        self.logical_nets.append(logical_net)

    @property
    def layer_features(self):
        return self._layer_features

    @layer_features.setter
    def layer_features(self, value):  # pragma no cover
        if isinstance(value, list):
            if len(
                [
                    feat
                    for feat in value
                    if isinstance(
                        feat,
                    )
                ]
            ):
                self._layer_features = value

    @property
    def physical_nets(self):
        return self._physical_nets

    @physical_nets.setter
    def physical_nets(self, value):  # pragma no cover
        if isinstance(value, list):
            if len([phy_net for phy_net in value if isinstance(phy_net, PhyNet)]) == len(value):
                self._physical_nets = value

    @pyaedt_function_handler()
    def add_physical_net(self, phy_net=None):  # pragma no cover
        if isinstance(phy_net, PhyNet):
            self._physical_nets.append(phy_net)
            return True
        return False

    @pyaedt_function_handler()
    def add_padstack_def(self, padstackdef=None):  # pragma no cover
        if isinstance(padstackdef, PadstackDef):
            self._padstack_defs.append(padstackdef)

    @pyaedt_function_handler()
    def add_component(self, component=None):  # pragma no cover
        # adding component add package in Step
        if component:
            if component.part_name not in self._packages:
                package = Package(self._ipc)
                package.add_component_outline(component)
                package.name = component.part_name
                package.height = ""
                package.type = component.type
                pin_number = 0
                for _, pin in component.pins.items():
                    geometry_type, pad_parameters, pos_x, pos_y, rot = self._pedb.padstacks.get_pad_parameters(
                        pin._edb_padstackinstance, component.placement_layer, 0
                    )
                    if pad_parameters:
                        position = pin._position if pin._position else pin.position
                        pin_pos_x = self._ipc.from_meter_to_units(position[0], self.units)
                        pin_pos_y = self._ipc.from_meter_to_units(position[1], self.units)
                        primitive_ref = ""
                        if geometry_type == 1:
                            primitive_ref = "CIRC_{}".format(pad_parameters[0])
                        elif geometry_type == 2:
                            primitive_ref = "RECT_{}_{}".format(pad_parameters[0], pad_parameters[0])
                        elif geometry_type == 3:
                            primitive_ref = "RECT_{}_{}".format(pad_parameters[0], pad_parameters[1])
                        elif geometry_type == 4:
                            primitive_ref = "OVAL_{}_{}_{}".format(
                                pad_parameters[0], pad_parameters[1], pad_parameters[2]
                            )
                        if primitive_ref:
                            package.add_pin(
                                number=pin_number, x=pin_pos_x, y=pin_pos_y, rotation=rot, primitive_ref=primitive_ref
                            )
                        pin_number += 1
                self.packages[package.name] = package
            ipc_component = Component()
            ipc_component.type = component.type
            try:
                ipc_component.value = component.value
            except:
                pass
            ipc_component.refdes = component.refdes
            center = component.center
            ipc_component.location = [
                self._ipc.from_meter_to_units(center[0], self.units),
                self._ipc.from_meter_to_units(center[1], self.units),
            ]
            ipc_component.rotation = component.rotation * 180 / math.pi
            ipc_component.part = ipc_component.package_ref = component.part_name
            ipc_component.layer_ref = component.placement_layer
            self.components.append(ipc_component)

    def layer_ranges(
        self,
        start_layer,
        stop_layer,
    ):  # pragma no cover
        started = False
        start_layer_name = start_layer.GetName()
        stop_layer_name = stop_layer.GetName()
        layer_list = []
        for layer_name in self._ipc.layers_name:
            if started:
                layer_list.append(layer_name)
                if layer_name == stop_layer_name or layer_name == start_layer_name:
                    break
            elif layer_name == start_layer_name:
                started = True
                layer_list.append(layer_name)
                if layer_name == stop_layer_name:
                    break
            elif layer_name == stop_layer_name:
                started = True
                layer_list.append(layer_name)
                if layer_name == start_layer_name:
                    break
        return layer_list

    @pyaedt_function_handler()
    def add_layer_feature(self, layer, polys):  # pragma no cover
        layer_name = layer.name
        layer_feature = LayerFeature(self._ipc)
        layer_feature.layer_name = layer_name
        layer_feature.color = layer.color

        for poly in polys:
            if not poly.is_void:
                layer_feature.add_feature(poly)
        self._ipc.ecad.cad_data.cad_data_step.layer_features.append(layer_feature)

    @pyaedt_function_handler()
    def add_padstack_instances(self, padstack_instances, padstack_defs):  # pragma no cover
        top_bottom_layers = self._ipc.top_bottom_layers
        layers = {j.layer_name: j for j in self._ipc.ecad.cad_data.cad_data_step.layer_features}

        for padstack_instance in padstack_instances:
            _, start_layer, stop_layer = padstack_instance._edb_padstackinstance.GetLayerRange()
            for layer_name in self.layer_ranges(start_layer, stop_layer):
                if layer_name not in layers:
                    layer_feature = LayerFeature(self._ipc)
                    layer_feature.layer_name = layer_name
                    layer_feature.color = self._ipc._pedb.stackup[layer_name].color
                    self._ipc.ecad.cad_data.cad_data_step.layer_features.append(layer_feature)
                    layers[layer_name] = self._ipc.ecad.cad_data.cad_data_step.layer_features[-1]
                pdef_name = (
                    padstack_instance._pdef if padstack_instance._pdef else padstack_instance.padstack_definition
                )
                padstack_def = padstack_defs[pdef_name]

                comp_name = padstack_instance.GetComponent().GetName()
                if padstack_instance.is_pin and comp_name:
                    component_inst = self._pedb.components.components[comp_name]
                    layers[layer_name].add_component_padstack_instance_feature(
                        component_inst, padstack_instance, top_bottom_layers, padstack_def
                    )
                else:
                    layers[layer_name].add_via_instance_feature(padstack_instance, padstack_def, layer_name)

    @pyaedt_function_handler()
    def add_drill_layer_feature(self, via_list=None, layer_feature_name=""):  # pragma no cover
        if via_list:
            drill_layer_feature = LayerFeature(self._ipc)
            drill_layer_feature.is_drill_feature = True
            drill_layer_feature.layer_name = layer_feature_name
            for via in via_list:
                try:
                    via_diameter = via.pin.GetPadstackDef().GetData().GetHoleParameters()[2][0]
                    drill_layer_feature.add_drill_feature(via, via_diameter)
                except:
                    pass
            self.layer_features.append(drill_layer_feature)

    @pyaedt_function_handler()
    def write_xml(self, cad_data):  # pragma no cover
        step = ET.SubElement(cad_data, "Step")
        step.set("name", self._ipc.design_name)
        for padsatck_def in list(self.padstack_defs.values()):
            padsatck_def.write_xml(step)
        for package in list(self.packages.values()):
            package.write_xml(step)
        for component in self.components:
            component.write_xml(step)
        for logical_net in self.logical_nets:
            logical_net.write_xml(step)
        for layer_feature in self.layer_features:
            layer_feature.write_xml(step)
