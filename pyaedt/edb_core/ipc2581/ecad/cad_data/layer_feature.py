import math

from pyaedt.edb_core.ipc2581.ecad.cad_data.feature import Feature, FeatureType
from pyaedt.generic.general_methods import ET, pyaedt_function_handler


class LayerFeature(object):
    """Class describing IPC2581 layer feature."""

    def __init__(self, ipc):
        self._ipc = ipc
        self.layer_name = ""
        self.color = ""
        self._features = []
        self.is_drill_feature = False

    @property
    def features(self):
        return self._features

    @features.setter
    def features(self, value):  # pragma no cover
        if isinstance(value, list):
            if len([feat for feat in value if isinstance(feat, Feature)]) == len(value):
                self._features = value

    @pyaedt_function_handler()
    def add_feature(self, obj_instance=None):  # pragma no cover
        if obj_instance:
            feature = Feature(self._ipc)
            feature.net = obj_instance.net_name
            if obj_instance.type == "Polygon":
                feature.feature_type = FeatureType.Polygon
                feature.polygon.add_poly_step(obj_instance)
            elif obj_instance.type == "Path":
                feature.feature_type = FeatureType.Path
                feature.path.add_path_step(obj_instance)
            self.features.append(feature)
        else:
            return False

    @pyaedt_function_handler()
    def add_via_instance_feature(self, padstack_inst=None, padstackdef=None, layer_name=None):  # pragma no cover
        if padstack_inst and padstackdef:
            feature = Feature(self._ipc)
            def_name = padstackdef.name
            position = padstack_inst.position if padstack_inst.position else padstack_inst.position
            feature.padstack_instance.net = padstack_inst.net_name
            feature.padstack_instance.isvia = True
            feature.padstack_instance.padstack_def = def_name
            feature.feature_type = FeatureType.PadstackInstance
            feature.padstack_instance.x = self._ipc.from_meter_to_units(position[0], self._ipc.units)
            feature.padstack_instance.y = self._ipc.from_meter_to_units(position[1], self._ipc.units)
            if padstackdef._hole_params is None:
                hole_props = [i.ToDouble() for i in padstackdef.hole_params[2]]
            else:
                hole_props = [i.ToDouble() for i in padstackdef._hole_params[2]]
            feature.padstack_instance.diameter = float(hole_props[0]) if hole_props else 0
            feature.padstack_instance.hole_name = def_name
            feature.padstack_instance.name = padstack_inst.name
            try:
                if padstackdef.pad_by_layer[layer_name].parameters_values is None:
                    feature.padstack_instance.standard_primimtive_ref = "CIRCLE_{}".format(
                        self._ipc.from_meter_to_units(
                            padstackdef.pad_by_layer[layer_name].parameters_values[0], self._ipc.units
                        )
                    )
                else:
                    feature.padstack_instance.standard_primimtive_ref = "CIRCLE_{}".format(
                        self._ipc.from_meter_to_units(
                            padstackdef.pad_by_layer[layer_name].parameters_values[0], self._ipc.units
                        )
                    )
                self.features.append(feature)
            except:
                pass

    @pyaedt_function_handler()
    def add_drill_feature(self, via, diameter=0.0):  # pragma no cover
        feature = Feature(self._ipc)
        feature.feature_type = FeatureType.Drill
        feature.drill.net = via.net_name
        position = via._position if via._position else via.position
        feature.drill.x = self._ipc.from_meter_to_units(position[0], self._ipc.units)
        feature.drill.y = self._ipc.from_meter_to_units(via.position[1], self._ipc.units)
        feature.drill.diameter = self._ipc.from_meter_to_units(diameter, self._ipc.units)
        self.features.append(feature)

    @pyaedt_function_handler()
    def add_component_padstack_instance_feature(
        self, component=None, pin=None, top_bottom_layers=[], padstack_def=None
    ):  # pragma no cover
        if component:
            if pin:
                is_via = False
                if not pin.start_layer == pin.stop_layer:
                    is_via = True
                pin_net = pin.GetNet().GetName()
                pos_rot = pin._edb_padstackinstance.GetPositionAndRotationValue()
                pin_rotation = pos_rot[2].ToDouble()
                if pin._edb_padstackinstance.IsLayoutPin():
                    out2 = pin._edb_padstackinstance.GetComponent().GetTransform().TransformPoint(pos_rot[1])
                    pin_position = [out2.X.ToDouble(), out2.Y.ToDouble()]
                else:
                    pin_position = [pos_rot[1].X.ToDouble(), pos_rot[1].Y.ToDouble()]
                pin_x = self._ipc.from_meter_to_units(pin_position[0], self._ipc.units)
                pin_y = self._ipc.from_meter_to_units(pin_position[1], self._ipc.units)
                cmp_rot_deg = component.rotation * 180 / math.pi
                mirror = False
                rotation = cmp_rot_deg + pin_rotation * 180 / math.pi
                if rotation < 0:
                    rotation += 360
                comp_placement_layer = component.placement_layer
                if comp_placement_layer == top_bottom_layers[-1]:
                    mirror = True
                feature = Feature(self._ipc)
                feature.feature_type = FeatureType.PadstackInstance
                feature.net = pin_net
                feature.padstack_instance.net = pin_net
                feature.padstack_instance.pin = pin.pin.GetName()
                feature.padstack_instance.x = pin_x
                feature.padstack_instance.y = pin_y
                feature.padstack_instance.rotation = rotation
                feature.padstack_instance.mirror = mirror
                feature.padstack_instance.isvia = is_via
                feature.padstack_instance.refdes = component.refdes
                feature.padstack_instance.padstack_def = padstack_def.name
                primitive_ref = self._get_primitive_ref(padstack_def.name, comp_placement_layer)
                if primitive_ref == "default_value":
                    other_layer = [lay for lay in top_bottom_layers if lay != comp_placement_layer][0]
                    primitive_ref = self._get_primitive_ref(padstack_def.name, other_layer)
                feature.padstack_instance.standard_primimtive_ref = primitive_ref
                self.features.append(feature)

    @pyaedt_function_handler()
    def _get_primitive_ref(self, padstack_def=None, layer=None):
        if padstack_def and layer:
            for pad_def in self._ipc.ecad.cad_data.cad_data_step.padstack_defs[padstack_def].padstack_pad_def:
                if pad_def.layer_ref == layer:
                    return pad_def.primitive_ref
            return "default_value"

    @pyaedt_function_handler()
    def write_xml(self, step):  # pragma no cover
        layer_feature = ET.SubElement(step, "LayerFeature")
        layer_feature.set("layerRef", self.layer_name)
        color_set = ET.SubElement(layer_feature, "Set")
        color_ref = ET.SubElement(color_set, "ColorRef")
        color_ref.set("id", self.layer_name)
        for feature in self.features:
            feature.write_xml(layer_feature)
