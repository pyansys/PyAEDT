from pyaedt.edb_core.ipc2581.content.entry_line import EntryLine
from pyaedt.edb_core.ipc2581.ecad.cad_data.polygon import PolyStep, PolyType
from pyaedt.generic.general_methods import ET, pyaedt_function_handler


class Path(object):
    """Class describing an IPC2581 trace."""

    def __init__(self, ipc):
        self._ipc = ipc
        self.location_x = 0.0
        self.location_y = 0.0
        self.poly_steps = []
        self.entry_line = EntryLine()
        self.width_ref_id = ""

    @pyaedt_function_handler()
    def add_path_step(self, path_step=None):  # pragma no cover
        arcs = path_step.primitive_object.GetCenterLine().GetArcData()
        if not arcs:
            return
        self.line_width = self._ipc.from_meter_to_units(path_step.primitive_object.GetWidth(), self._ipc.units)
        self.width_ref_id = "ROUND_{}".format(self.line_width)
        if self.width_ref_id not in self._ipc.content.dict_line.dict_lines:
            entry_line = EntryLine()
            entry_line.line_width = self.line_width
            self._ipc.content.dict_line.dict_lines[self.width_ref_id] = entry_line
        # first point
        arc = arcs[0]
        new_segment_tep = PolyStep()
        new_segment_tep.x = arc.Start.X.ToDouble()
        new_segment_tep.y = arc.Start.Y.ToDouble()
        self.poly_steps.append(new_segment_tep)
        if arc.Height == 0:
            new_segment_tep = PolyStep()
            new_segment_tep.poly_type = PolyType.Segment
            new_segment_tep.x = arc.End.X.ToDouble()
            new_segment_tep.y = arc.End.Y.ToDouble()
            self.poly_steps.append(new_segment_tep)
        else:
            arc_center = arc.GetCenter()
            new_poly_step = PolyStep()
            new_poly_step.poly_type = PolyType.Curve
            new_poly_step.center_X = arc_center.X.ToDouble()
            new_poly_step.center_y = arc_center.Y.ToDouble()
            new_poly_step.x = arc.End.X.ToDouble()
            new_poly_step.y = arc.End.Y.ToDouble()
            new_poly_step.clock_wise = not arc.IsCCW()
            self.poly_steps.append(new_poly_step)
        for arc in list(arcs)[1:]:
            if arc.Height == 0:
                new_segment_tep = PolyStep()
                new_segment_tep.poly_type = PolyType.Segment
                new_segment_tep.x = arc.End.X.ToDouble()
                new_segment_tep.y = arc.End.Y.ToDouble()
                self.poly_steps.append(new_segment_tep)
            else:
                arc_center = arc.GetCenter()
                new_poly_step = PolyStep()
                new_poly_step.poly_type = PolyType.Curve
                new_poly_step.center_X = arc_center.X.ToDouble()
                new_poly_step.center_y = arc_center.Y.ToDouble()
                new_poly_step.x = arc.End.X.ToDouble()
                new_poly_step.y = arc.End.Y.ToDouble()
                new_poly_step.clock_wise = not arc.IsCCW()
                self.poly_steps.append(new_poly_step)

    @pyaedt_function_handler()
    def write_xml(self, net_root):  # pragma no cover
        if not self.poly_steps:
            return
        feature = ET.SubElement(net_root, "Features")
        location = ET.SubElement(feature, "Location")
        location.set("x", "0")
        location.set("y", "0")
        polyline = ET.SubElement(feature, "Polyline")
        polyline_begin = ET.SubElement(polyline, "PolyBegin")
        polyline_begin.set("x", str(self._ipc.from_meter_to_units(self.poly_steps[0].x, self._ipc.units)))
        polyline_begin.set("y", str(self._ipc.from_meter_to_units(self.poly_steps[0].y, self._ipc.units)))
        for poly_step in self.poly_steps[1:]:
            poly_step.write_xml(polyline, self._ipc)
        line_disc_ref = ET.SubElement(polyline, "LineDescRef")
        line_disc_ref.set("id", self.width_ref_id)


class PathStep(object):
    def __init__(self):
        self.x = 0.0
        self.y = 0.0
