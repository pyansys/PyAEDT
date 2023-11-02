import math

from pyaedt.edb_core.ipc2581.content.entry_line import EntryLine
from pyaedt.edb_core.ipc2581.ecad.cad_data.assembly_drawing import AssemblyDrawing
from pyaedt.edb_core.ipc2581.ecad.cad_data.outline import Outline
from pyaedt.edb_core.ipc2581.ecad.cad_data.pin import Pin
from pyaedt.edb_core.ipc2581.ecad.cad_data.polygon import PolyStep
from pyaedt.generic.general_methods import ET, pyaedt_function_handler


class Package(object):
    """Class describing an IPC2581 package definition."""

    def __init__(self, ipc):
        self._ipc = ipc
        self.name = ""
        self.type = "OTHER"
        self.pin_one = "1"
        self.pin_orientation = "OTHER"
        self.height = 0.1
        self.assembly_drawing = AssemblyDrawing(self._ipc)
        self.outline = Outline(self._ipc)
        self._pins = []
        self.pickup_point = [0.0, 0.0]

    @property
    def pins(self):
        return self._pins

    @pins.setter
    def pins(self, value):  # pragma no cover
        if isinstance(value, list):
            if len([pin for pin in value if isinstance(pin, Pin)]) == len(value):
                self._pins = value

    @pyaedt_function_handler()
    def add_pin(self, number=0, x=0.0, y=0.0, rotation=0.0, primitive_ref=""):  # pragma no cover
        added_pin = Pin()
        added_pin.x = x
        added_pin.y = y
        added_pin.rotation = rotation * 180 / math.pi
        added_pin.number = number
        added_pin.primitive_def = primitive_ref
        self.pins.append(added_pin)

    @pyaedt_function_handler()
    def add_component_outline(self, component):  # pragma no cover
        if component:
            _bbox = component.bounding_box
            _rot = component.rotation
            average_x = (_bbox[0] + _bbox[2]) / 2
            average_y = (_bbox[1] + _bbox[3]) / 2
            bb1x = _bbox[0] - average_x
            bb1y = _bbox[1] - average_y
            bb2x = _bbox[2] - average_x
            bb2y = _bbox[3] - average_y

            bb1x_rot = bb1x
            bb2x_rot = bb2x
            bb1y_rot = bb1y
            bb2y_rot = bb2y
            if _rot >= math.pi / 4 and _rot <= 0.75 * math.pi:
                bb = bb1x_rot
                bb1x_rot = bb1y_rot
                bb1y_rot = bb
                bb = bb2x_rot
                bb2x_rot = bb2y_rot
                bb2y_rot = bb
            poly_step1 = PolyStep()
            poly_step2 = PolyStep()
            poly_step3 = PolyStep()
            poly_step4 = PolyStep()
            poly_step5 = PolyStep()
            poly_step1.x = str(self._ipc.from_meter_to_units(bb1x_rot, self._ipc.units))
            poly_step1.y = str(self._ipc.from_meter_to_units(bb1y_rot, self._ipc.units))
            poly_step2.x = str(self._ipc.from_meter_to_units(bb2x_rot, self._ipc.units))
            poly_step2.y = str(self._ipc.from_meter_to_units(bb1y_rot, self._ipc.units))
            poly_step3.x = str(self._ipc.from_meter_to_units(bb2x_rot, self._ipc.units))
            poly_step3.y = str(self._ipc.from_meter_to_units(bb2y_rot, self._ipc.units))
            poly_step4.x = str(self._ipc.from_meter_to_units(bb1x_rot, self._ipc.units))
            poly_step4.y = str(self._ipc.from_meter_to_units(bb2y_rot, self._ipc.units))
            poly_step5.x = str(self._ipc.from_meter_to_units(bb1x_rot, self._ipc.units))
            poly_step5.y = str(self._ipc.from_meter_to_units(bb1y_rot, self._ipc.units))
            self.outline.polygon.poly_steps = [poly_step1, poly_step2, poly_step3, poly_step4, poly_step5]
            if "ROUND_0" not in self._ipc.content.dict_line.dict_lines:
                entry_line = EntryLine()
                entry_line.line_width = 0.0
                self._ipc.content.dict_line.dict_lines["ROUND_0"] = entry_line
            self.outline.line_ref = "ROUND_0"
            self.assembly_drawing.polygon.poly_steps = [poly_step1, poly_step2, poly_step3, poly_step4, poly_step5]
            self.assembly_drawing.line_ref = "ROUND_0"

    @pyaedt_function_handler()
    def write_xml(self, step):  # pragma no cover
        package = ET.SubElement(step, "Package")
        package.set("name", self.name)
        package.set("type", self.type)
        package.set("pinOne", self.pin_one)
        package.set("pinOneOrientation", self.pin_orientation)
        package.set("height", str(self.height))
        self.outline.write_xml(package)
        self.assembly_drawing.write_xml(package)
        for pin in self.pins:
            pin.write_xml(package)
