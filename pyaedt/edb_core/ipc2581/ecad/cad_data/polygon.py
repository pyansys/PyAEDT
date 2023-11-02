import math

from pyaedt.generic.general_methods import ET, pyaedt_function_handler


class Polygon(object):
    def __init__(self, ipc):
        self._ipc = ipc
        self.is_void = False
        self.poly_steps = []
        self.solid_fill_id = ""
        self.cutout = []

    @pyaedt_function_handler()
    def add_poly_step(self, polygon=None):  # pragma no cover
        if polygon:
            polygon_data = polygon.GetPolygonData()
            if polygon_data.IsClosed():
                arcs = polygon_data.GetArcData()
                if not arcs:
                    return
                # begin
                new_segment_tep = PolyStep()
                new_segment_tep.poly_type = PolyType.Segment
                new_segment_tep.x = arcs[0].Start.X.ToDouble()
                new_segment_tep.y = arcs[0].Start.Y.ToDouble()
                self.poly_steps.append(new_segment_tep)
                for arc in arcs:
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
                for void in polygon.voids:
                    void_polygon_data = void.GetPolygonData()
                    if void_polygon_data.IsClosed():
                        void_arcs = void_polygon_data.GetArcData()
                        if not void_arcs:
                            return
                        void_polygon = Cutout(self._ipc)
                        self.cutout.append(void_polygon)
                        # begin
                        new_segment_tep = PolyStep()
                        new_segment_tep.poly_type = PolyType.Segment
                        new_segment_tep.x = void_arcs[0].Start.X.ToDouble()
                        new_segment_tep.y = void_arcs[0].Start.Y.ToDouble()
                        void_polygon.poly_steps.append(new_segment_tep)
                        for void_arc in void_arcs:
                            if void_arc.Height == 0:
                                new_segment_tep = PolyStep()
                                new_segment_tep.poly_type = PolyType.Segment
                                new_segment_tep.x = void_arc.End.X.ToDouble()
                                new_segment_tep.y = void_arc.End.Y.ToDouble()
                                void_polygon.poly_steps.append(new_segment_tep)
                            else:
                                arc_center = void_arc.GetCenter()
                                new_poly_step = PolyStep()
                                new_poly_step.poly_type = PolyType.Curve
                                new_poly_step.center_X = arc_center.X.ToDouble()
                                new_poly_step.center_y = arc_center.Y.ToDouble()
                                new_poly_step.x = void_arc.End.X.ToDouble()
                                new_poly_step.y = void_arc.End.Y.ToDouble()
                                new_poly_step.clock_wise = not void_arc.IsCCW()
                                void_polygon.poly_steps.append(new_poly_step)

    @pyaedt_function_handler()
    def add_cutout(self, cutout):  # pragma no cover
        if not isinstance(cutout, Cutout):
            return False
        self.cutout.append(cutout)

    @pyaedt_function_handler()
    def write_xml(self, root_net):  # pragma no cover
        if not self.poly_steps:
            return
        feature = ET.SubElement(root_net, "Features")
        location = ET.SubElement(feature, "Location")
        location.set("x", str(0))
        location.set("y", str(0))
        contour = ET.SubElement(feature, "Contour")
        polygon = ET.SubElement(contour, "Polygon")
        polygon_begin = ET.SubElement(polygon, "PolyBegin")
        polygon_begin.set("x", str(self._ipc.from_meter_to_units(self.poly_steps[0].x, self._ipc.units)))
        polygon_begin.set("y", str(self._ipc.from_meter_to_units(self.poly_steps[0].y, self._ipc.units)))
        for poly_step in self.poly_steps[1:]:
            poly_step.write_xml(polygon, self._ipc)
        for cutout in self.cutout:
            cutout.write_xml(contour, self._ipc)


class Cutout(object):
    def __init__(self, ipc):
        self._ipc = ipc
        self.poly_steps = []

    @pyaedt_function_handler()
    def write_xml(self, contour, ipc):  # pragma no cover
        cutout = ET.SubElement(contour, "Cutout")
        cutout_begin = ET.SubElement(cutout, "PolyBegin")
        cutout_begin.set("x", str(ipc.from_meter_to_units(self.poly_steps[0].x, ipc.units)))
        cutout_begin.set("y", str(ipc.from_meter_to_units(self.poly_steps[0].y, ipc.units)))
        for poly_step in self.poly_steps[1:]:
            if poly_step.poly_type == 0:
                poly = ET.SubElement(cutout, "PolyStepSegment")
                poly.set("x", str(ipc.from_meter_to_units(poly_step.x, ipc.units)))
                poly.set("y", str(ipc.from_meter_to_units(poly_step.y, ipc.units)))
            elif poly_step.poly_type == 1:
                poly = ET.SubElement(cutout, "PolyStepCurve")
                poly.set("x", str(ipc.from_meter_to_units(poly_step.x, ipc.units)))
                poly.set("y", str(ipc.from_meter_to_units(poly_step.y, ipc.units)))
                poly.set("centerX", str(ipc.from_meter_to_units(poly_step.center_X, ipc.units)))
                poly.set("centerY", str(ipc.from_meter_to_units(poly_step.center_y, ipc.units)))
                poly.set("clockwise", str(poly_step.clock_wise).lower())


class PolyStep(object):
    def __init__(self):
        self.poly_type = PolyType().Segment
        self.x = 0.0
        self.y = 0.0
        self.center_X = 0.0
        self.center_y = 0.0
        self.clock_wise = False

    @pyaedt_function_handler()
    def write_xml(self, polygon, ipc):  # pragma no cover
        if self.poly_type == 0:
            poly = ET.SubElement(polygon, "PolyStepSegment")
            poly.set("x", str(ipc.from_meter_to_units(self.x, ipc.units)))
            poly.set("y", str(ipc.from_meter_to_units(self.y, ipc.units)))
        elif self.poly_type == 1:
            poly = ET.SubElement(polygon, "PolyStepCurve")
            poly.set("x", str(ipc.from_meter_to_units(self.x, ipc.units)))
            poly.set("y", str(ipc.from_meter_to_units(self.y, ipc.units)))
            poly.set("centerX", str(ipc.from_meter_to_units(self.center_X, ipc.units)))
            poly.set("centerY", str(ipc.from_meter_to_units(self.center_y, ipc.units)))
            poly.set("clockwise", str(self.clock_wise).lower())


class PolyType(object):
    (Segment, Curve) = range(0, 2)


class Curve(object):
    def __init__(self):
        self.center_X = 0.0
        self.center_y = 0.0
        self.clock_wise = False


class Arc(object):
    @staticmethod
    def get_arc_radius_angle(h, c):  # pragma no cover
        if not isinstance(h, float) and isinstance(c, float):
            return False
        r = h / 2 + math.pow(c, 2) / (8 * h)
        theta = 2 * math.asin(c / (2 * r))
        return r, theta
