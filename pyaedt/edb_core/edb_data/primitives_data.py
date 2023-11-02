import math

from pyaedt.edb_core.dotnet.primitive import (
    BondwireDotNet,
    CircleDotNet,
    PathDotNet,
    PolygonDataDotNet,
    PolygonDotNet,
    RectangleDotNet,
    TextDotNet,
)
from pyaedt.edb_core.edb_data.connectable import Connectable
from pyaedt.edb_core.general import convert_py_list_to_net_list
from pyaedt.generic.general_methods import pyaedt_function_handler
from pyaedt.modeler.geometry_operators import GeometryOperators


def cast(raw_primitive, core_app):
    """Cast the primitive object to correct concrete type.

    Returns
    -------
    Primitive
    """
    if isinstance(raw_primitive, RectangleDotNet):
        return EdbRectangle(raw_primitive.prim_obj, core_app)
    elif isinstance(raw_primitive, PolygonDotNet):
        return EdbPolygon(raw_primitive.prim_obj, core_app)
    elif isinstance(raw_primitive, PathDotNet):
        return EdbPath(raw_primitive.prim_obj, core_app)
    elif isinstance(raw_primitive, BondwireDotNet):
        return EdbBondwire(raw_primitive.prim_obj, core_app)
    elif isinstance(raw_primitive, TextDotNet):
        return EdbText(raw_primitive.prim_obj, core_app)
    elif isinstance(raw_primitive, CircleDotNet):
        return EdbCircle(raw_primitive.prim_obj, core_app)
    else:
        try:
            prim_type = raw_primitive.GetPrimitiveType()
            if prim_type == prim_type.Rectangle:
                return EdbRectangle(raw_primitive, core_app)
            elif prim_type == prim_type.Polygon:
                return EdbPolygon(raw_primitive, core_app)
            elif prim_type == prim_type.Path:
                return EdbPath(raw_primitive, core_app)
            elif prim_type == prim_type.Bondwire:
                return EdbBondwire(raw_primitive, core_app)
            elif prim_type == prim_type.Text:
                return EdbText(raw_primitive, core_app)
            elif prim_type == prim_type.Circle:
                return EdbCircle(raw_primitive, core_app)
            else:
                return None
        except:
            return None


class EDBPrimitivesMain(Connectable):
    """Manages EDB functionalities for a primitives.
    It Inherits EDB Object properties.

    Examples
    --------
    >>> from pyaedt import Edb
    >>> edb = Edb(myedb, edbversion="2021.2")
    >>> edb_prim = edb.modeler.primitives[0]
    >>> edb_prim.is_void # Class Property
    >>> edb_prim.IsVoid() # EDB Object Property
    """

    def __init__(self, raw_primitive, core_app):
        super().__init__(core_app, raw_primitive)
        self._app = self._pedb
        self._core_stackup = core_app.stackup
        self._core_net = core_app.nets
        self.primitive_object = self._edb_object

    @property
    def type(self):
        """Return the type of the primitive.
        Allowed outputs are ``"Circle"``, ``"Rectangle"``,``"Polygon"``,``"Path"`` or ``"Bondwire"``.

        Returns
        -------
        str
        """
        return self._edb_object.GetPrimitiveType().ToString()

    @property
    def net_name(self):
        """Get or Set the primitive net name.

        Returns
        -------
        str
        """
        return self.net.GetName()

    @net_name.setter
    def net_name(self, name):
        if isinstance(name, str):
            net = self._app.nets.nets[name].net_object
            self.primitive_object.SetNet(net)
        else:
            try:
                self.net = name
            except:
                self._app.logger.error("Failed to set net name.")

    @property
    def layer(self):
        """Get the primitive edb layer object."""
        return self.primitive_object.GetLayer()

    @property
    def layer_name(self):
        """Get or Set the primitive layer name.

        Returns
        -------
        str
        """
        return self.layer.GetName()

    @layer_name.setter
    def layer_name(self, val):
        if isinstance(val, str) and val in list(self._core_stackup.layers.keys()):
            lay = self._core_stackup.layers["TOP"]._edb_layer
            if lay:
                self.primitive_object.SetLayer(lay)
            else:
                raise AttributeError("Layer {} not found in layer".format(val))
        elif isinstance(val, type(self._core_stackup.layers["TOP"])):
            try:
                self.primitive_object.SetLayer(val._edb_layer)
            except:
                raise AttributeError("Failed to assign new layer on primitive.")
        else:
            raise AttributeError("Invalid input value")

    @property
    def is_void(self):
        """Either if the primitive is a void or not.

        Returns
        -------
        bool
        """
        return self._edb_object.IsVoid()

    def get_connected_objects(self):
        """Get connected objects.

        Returns
        -------
        list
        """
        return self._pedb.get_connected_objects(self._layout_obj_instance)


class EDBPrimitives(EDBPrimitivesMain):
    """Manages EDB functionalities for a primitives.
    It Inherits EDB Object properties.

    Examples
    --------
    >>> from pyaedt import Edb
    >>> edb = Edb(myedb, edbversion="2021.2")
    >>> edb_prim = edb.modeler.primitives[0]
    >>> edb_prim.is_void # Class Property
    >>> edb_prim.IsVoid() # EDB Object Property
    """

    def __init__(self, raw_primitive, core_app):
        EDBPrimitivesMain.__init__(self, raw_primitive, core_app)

    @pyaedt_function_handler()
    def area(self, include_voids=True):
        """Return the total area.

        Parameters
        ----------
        include_voids : bool, optional
            Either if the voids have to be included in computation.
            The default value is ``True``.

        Returns
        -------
        float
        """
        area = self.primitive_object.GetPolygonData().Area()
        if include_voids:
            for el in self.primitive_object.Voids:
                area -= el.GetPolygonData().Area()
        return area

    @property
    def is_negative(self):
        """Determine whether this primitive is negative.

        Returns
        -------
        bool
            True if it is negative, False otherwise.
        """
        return self.primitive_object.GetIsNegative()

    @is_negative.setter
    def is_negative(self, value):
        self.primitive_object.SetIsNegative(value)

    @staticmethod
    def _eval_arc_points(p1, p2, h, n=6, tol=1e-12):
        """Get the points of the arc

        Parameters
        ----------
        p1 : list
            Arc starting point.
        p2 : list
            Arc ending point.
        h : float
            Arc height.
        n : int
            Number of points to generate along the arc.
        tol : float
            Geometric tolerance.

        Returns
        -------
        list, list
            Points generated along the arc.
        """
        # fmt: off
        if abs(h) < tol:
            return [], []
        elif h > 0:
            reverse = False
            x1 = p1[0]
            y1 = p1[1]
            x2 = p2[0]
            y2 = p2[1]
        else:
            reverse = True
            x1 = p2[0]
            y1 = p2[1]
            x2 = p1[0]
            y2 = p1[1]
            h *= -1
        xa = (x2 - x1) / 2
        ya = (y2 - y1) / 2
        xo = x1 + xa
        yo = y1 + ya
        a = math.sqrt(xa ** 2 + ya ** 2)
        if a < tol:
            return [], []
        r = (a ** 2) / (2 * h) + h / 2
        if abs(r - a) < tol:
            b = 0
            th = 2 * math.asin(1)  # chord angle
        else:
            b = math.sqrt(r ** 2 - a ** 2)
            th = 2 * math.asin(a / r)  # chord angle

        # center of the circle
        xc = xo + b * ya / a
        yc = yo - b * xa / a

        alpha = math.atan2((y1 - yc), (x1 - xc))
        xr = []
        yr = []
        for i in range(n):
            i += 1
            dth = (float(i) / (n + 1)) * th
            xi = xc + r * math.cos(alpha - dth)
            yi = yc + r * math.sin(alpha - dth)
            xr.append(xi)
            yr.append(yi)

        if reverse:
            xr.reverse()
            yr.reverse()
        # fmt: on
        return xr, yr

    def _get_points_for_plot(self, my_net_points, num):
        """Get the points to be plotted.
        """
        # fmt: off
        x = []
        y = []
        for i, point in enumerate(my_net_points):
            if not self.is_arc(point):
                x.append(point.X.ToDouble())
                y.append(point.Y.ToDouble())
                # i += 1
            else:
                arc_h = point.GetArcHeight().ToDouble()
                p1 = [my_net_points[i - 1].X.ToDouble(), my_net_points[i - 1].Y.ToDouble()]
                if i + 1 < len(my_net_points):
                    p2 = [my_net_points[i + 1].X.ToDouble(), my_net_points[i + 1].Y.ToDouble()]
                else:
                    p2 = [my_net_points[0].X.ToDouble(), my_net_points[0].Y.ToDouble()]
                x_arc, y_arc = self._eval_arc_points(p1, p2, arc_h, num)
                x.extend(x_arc)
                y.extend(y_arc)
                # i += 1
        # fmt: on
        return x, y

    @property
    def bbox(self):
        """Return the primitive bounding box points. Lower left corner, upper right corner.

        Returns
        -------
        list
            [lower_left x, lower_left y, upper right x, upper right y]

        """
        bbox = self.polygon_data.edb_api.GetBBox()
        return [bbox.Item1.X.ToDouble(), bbox.Item1.Y.ToDouble(), bbox.Item2.X.ToDouble(), bbox.Item2.Y.ToDouble()]

    @property
    def center(self):
        """Return the primitive bounding box center coordinate.

        Returns
        -------
        list
            [x, y]

        """
        bbox = self.bbox
        return [(bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2]

    @pyaedt_function_handler()
    def is_arc(self, point):
        """Either if a point is an arc or not.

        Returns
        -------
        bool
        """
        return point.IsArc()

    @pyaedt_function_handler()
    def get_connected_object_id_set(self):
        """Produce a list of all geometries physically connected to a given layout object.

        Returns
        -------
        list
            Found connected objects IDs with Layout object.
        """
        layoutInst = self.primitive_object.GetLayout().GetLayoutInstance()
        layoutObjInst = layoutInst.GetLayoutObjInstance(self.primitive_object, None)  # 2nd arg was []
        return [loi.GetLayoutObj().GetId() for loi in layoutInst.GetConnectedObjects(layoutObjInst).Items]

    @pyaedt_function_handler()
    def convert_to_polygon(self):
        """Convert path to polygon.

        Returns
        -------
        Converted polygon.

        """
        if self.type == "Path":
            polygon_data = self.primitive_object.GetPolygonData()
            polygon = self._app.modeler.create_polygon(polygon_data, self.layer_name, [], self.net_name)
            self.primitive_object.Delete()
            return polygon

    @pyaedt_function_handler()
    def subtract(self, primitives):
        """Subtract active primitive with one or more primitives.

        Parameters
        ----------
        primitives : :class:`pyaedt.edb_core.edb_data.EDBPrimitives` or EDB PolygonData or EDB Primitive or list

        Returns
        -------
        List of :class:`pyaedt.edb_core.edb_data.EDBPrimitives`
        """
        poly = self.primitive_object.GetPolygonData()
        if not isinstance(primitives, list):
            primitives = [primitives]
        primi_polys = []
        voids_of_prims = []
        for prim in primitives:
            if isinstance(prim, EDBPrimitives):
                primi_polys.append(prim.primitive_object.GetPolygonData())
                for void in prim.voids:
                    voids_of_prims.append(void.polygon_data.edb_api)
            else:
                try:
                    primi_polys.append(prim.GetPolygonData())
                except:
                    primi_polys.append(prim)
        for v in self.voids[:]:
            primi_polys.append(v.polygon_data.edb_api)
        primi_polys = poly.Unite(convert_py_list_to_net_list(primi_polys))
        p_to_sub = poly.Unite(convert_py_list_to_net_list([poly] + voids_of_prims))
        list_poly = poly.Subtract(p_to_sub, primi_polys)
        new_polys = []
        if list_poly:
            for p in list_poly:
                if p.IsNull():
                    continue
            new_polys.append(
                cast(
                    self._app.modeler.create_polygon(p, self.layer_name, net_name=self.net_name, voids=[]),
                    self._app,
                )
            )
        self.delete()
        for prim in primitives:
            if isinstance(prim, EDBPrimitives):
                prim.delete()
            else:
                try:
                    prim.Delete()
                except AttributeError:
                    continue
        return new_polys

    @pyaedt_function_handler()
    def intersect(self, primitives):
        """Intersect active primitive with one or more primitives.

        Parameters
        ----------
        primitives : :class:`pyaedt.edb_core.edb_data.EDBPrimitives` or EDB PolygonData or EDB Primitive or list

        Returns
        -------
        List of :class:`pyaedt.edb_core.edb_data.EDBPrimitives`
        """
        poly = self.primitive_object.GetPolygonData()
        if not isinstance(primitives, list):
            primitives = [primitives]
        primi_polys = []
        for prim in primitives:
            if isinstance(prim, EDBPrimitives):
                primi_polys.append(prim.primitive_object.GetPolygonData())
            else:
                try:
                    primi_polys.append(prim.GetPolygonData())
                except:
                    primi_polys.append(prim)
        list_poly = poly.Intersect(convert_py_list_to_net_list([poly]), convert_py_list_to_net_list(primi_polys))
        new_polys = []
        if list_poly:
            voids = self.voids
            for p in list_poly:
                if p.IsNull():
                    continue
                list_void = []
                void_to_subtract = []
                if voids:
                    for void in voids:
                        void_pdata = void.prim_obj.GetPolygonData()
                        int_data2 = p.GetIntersectionType(void_pdata)
                        if int_data2 > 2 or int_data2 == 1:
                            void_to_subtract.append(void_pdata)
                        elif int_data2 == 2:
                            list_void.append(void_pdata)
                    if void_to_subtract:
                        polys_cleans = p.Subtract(
                            convert_py_list_to_net_list(p), convert_py_list_to_net_list(void_to_subtract)
                        )
                        for polys_clean in polys_cleans:
                            if not polys_clean.IsNull():
                                void_to_append = [v for v in list_void if polys_clean.GetIntersectionType(v) == 2]
                        new_polys.append(
                            cast(
                                self._app.modeler.create_polygon(
                                    polys_clean, self.layer_name, net_name=self.net_name, voids=void_to_append
                                ),
                                self._app,
                            )
                        )
                    else:
                        new_polys.append(
                            cast(
                                self._app.modeler.create_polygon(
                                    p, self.layer_name, net_name=self.net_name, voids=list_void
                                ),
                                self._app,
                            )
                        )
                else:
                    new_polys.append(
                        cast(
                            self._app.modeler.create_polygon(
                                p, self.layer_name, net_name=self.net_name, voids=list_void
                            ),
                            self._app,
                        )
                    )
        self.delete()
        for prim in primitives:
            if isinstance(prim, EDBPrimitives):
                prim.delete()
            else:
                try:
                    prim.Delete()
                except AttributeError:
                    continue
        return new_polys

    @pyaedt_function_handler()
    def unite(self, primitives):
        """Unite active primitive with one or more primitives.

        Parameters
        ----------
        primitives : :class:`pyaedt.edb_core.edb_data.EDBPrimitives` or EDB PolygonData or EDB Primitive or list

        Returns
        -------
        List of :class:`pyaedt.edb_core.edb_data.EDBPrimitives`
        """
        poly = self.primitive_object.GetPolygonData()
        if not isinstance(primitives, list):
            primitives = [primitives]
        primi_polys = []
        for prim in primitives:
            if isinstance(prim, EDBPrimitives):
                primi_polys.append(prim.primitive_object.GetPolygonData())
            else:
                try:
                    primi_polys.append(prim.GetPolygonData())
                except:
                    primi_polys.append(prim)
        list_poly = poly.Unite(convert_py_list_to_net_list([poly] + primi_polys))
        new_polys = []
        if list_poly:
            voids = self.voids
            for p in list_poly:
                if p.IsNull():
                    continue
                list_void = []
                if voids:
                    for void in voids:
                        void_pdata = void.primitive_object.GetPolygonData()
                        int_data2 = p.GetIntersectionType(void_pdata)
                        if int_data2 > 1:
                            list_void.append(void_pdata)
                new_polys.append(
                    cast(
                        self._app.modeler.create_polygon(p, self.layer_name, net_name=self.net_name, voids=list_void),
                        self._app,
                    )
                )
        self.delete()
        for prim in primitives:
            if isinstance(prim, EDBPrimitives):
                prim.delete()
            else:
                try:
                    prim.Delete()
                except AttributeError:
                    continue
        return new_polys

    @pyaedt_function_handler()
    def intersection_type(self, primitive):
        """Get intersection type between actual primitive and another primitive or polygon data.

        Parameters
        ----------
        primitive : :class:`pyaeedt.edb_core.edb_data.primitives_data.EDBPrimitives` or `PolygonData`

        Returns
        -------
        int
            Intersection type:
            0 - objects do not intersect,
            1 - this object fully inside other (no common contour points),
            2 - other object fully inside this,
            3 - common contour points,
            4 - undefined intersection.
        """
        poly = primitive
        try:
            poly = primitive.polygon_data
        except AttributeError:
            pass
        return int(self.polygon_data.edb_api.GetIntersectionType(poly.edb_api))

    @pyaedt_function_handler()
    def is_intersecting(self, primitive):
        """Check if actual primitive and another primitive or polygon data intesects.

        Parameters
        ----------
        primitive : :class:`pyaeedt.edb_core.edb_data.primitives_data.EDBPrimitives` or `PolygonData`

        Returns
        -------
        bool
        """
        return True if self.intersection_type(primitive) >= 1 else False

    @pyaedt_function_handler()
    def get_closest_point(self, point):
        """Get the closest point of the primitive to the input data.

        Parameters
        ----------
        point : list of float or PointData

        Returns
        -------
        list of float
        """
        if isinstance(point, (list, tuple)):
            point = self._app.edb_api.geometry.point_data(self._app.edb_value(point[0]), self._app.edb_value(point[1]))

        p0 = self.polygon_data.edb_api.GetClosestPoint(point)
        return [p0.X.ToDouble(), p0.Y.ToDouble()]

    @pyaedt_function_handler()
    def get_closest_arc_midpoint(self, point):
        """Get the closest arc midpoint of the primitive to the input data.

        Parameters
        ----------
        point : list of float or PointData

        Returns
        -------
        list of float
        """
        if isinstance(point, self._app.edb_api.geometry.geometry.PointData):
            point = [point.X.ToDouble(), point.Y.ToDouble()]
        dist = 1e12
        out = None
        for arc in self.arcs:
            mid_point = arc.mid_point
            mid_point = [mid_point.X.ToDouble(), mid_point.Y.ToDouble()]
            if GeometryOperators.points_distance(mid_point, point) < dist:
                out = arc.mid_point
                dist = GeometryOperators.points_distance(mid_point, point)
        return [out.X.ToDouble(), out.Y.ToDouble()]

    @property
    def arcs(self):
        """Get the Primitive Arc Data."""
        arcs = [EDBArcs(self, i) for i in self.polygon_data.arcs]
        return arcs

    @property
    def longest_arc(self):
        """Get the longest arc."""
        len = 0
        arc = None
        for i in self.arcs:
            if i.is_segment and i.length > len:
                arc = i
                len = i.length
        return arc

    @property
    def shortest_arc(self):
        """Get the longest arc."""
        len = 1e12
        arc = None
        for i in self.arcs:
            if i.is_segment and i.length < len:
                arc = i
                len = i.length
        return arc


class EdbPath(EDBPrimitives, PathDotNet):
    def __init__(self, raw_primitive, core_app):
        EDBPrimitives.__init__(self, raw_primitive, core_app)
        PathDotNet.__init__(self, self._app, raw_primitive)

    @property
    def width(self):
        """Path width.

        Returns
        -------
        float
            Path width or None.
        """
        if self.type == "Path":
            return self.primitive_object.GetWidth()
        return

    @width.setter
    def width(self, value):
        if self.type == "Path":
            if isinstance(value, (int, str, float)):
                self.primitive_object.SetWidth(self._app.edb_value(value))
            else:
                self.primitive_object.SetWidth(value)

    @property
    def length(self):
        """Path length in meters.

        Returns
        -------
        float
            Path length in meters.
        """
        center_line = self.get_center_line()
        length = 0
        for pt_ind in range(len(center_line)):
            if pt_ind < len(center_line) - 1:
                length += GeometryOperators.points_distance(center_line[pt_ind], center_line[pt_ind + 1])
        return length

    @pyaedt_function_handler
    def add_point(self, x, y, incremental=False):
        """Add a point at the end of the path.

        Parameters
        ----------
        x: str, int, float
            X coordinate.
        y: str, in, float
            Y coordinate.
        incremental: bool
            Add point incrementally. If True, coordinates of the added point is incremental to the last point.
            The default value is ``False``.

        Returns
        -------
        bool
        """
        center_line = PolygonDataDotNet(self._pedb, self._edb_object.GetCenterLine())
        center_line.add_point(x, y, incremental)
        return self._edb_object.SetCenterLine(center_line.edb_api)

    @pyaedt_function_handler
    def get_center_line(self, to_string=False):
        """Get the center line of the trace.

        Parameters
        ----------
        to_string : bool, optional
            Type of return. The default is ``"False"``.

        Returns
        -------
        list

        """
        if to_string:
            return [[p.X.ToString(), p.Y.ToString()] for p in list(self.primitive_object.GetCenterLine().Points)]
        else:
            return [[p.X.ToDouble(), p.Y.ToDouble()] for p in list(self.primitive_object.GetCenterLine().Points)]

    @pyaedt_function_handler
    def clone(self):
        """Clone a primitive object with keeping same definition and location.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        center_line = self.center_line
        width = self.width
        corner_style = self.corner_style
        end_cap_style = self.end_cap_style
        cloned_path = self._app.edb_api.cell.primitive.path.create(
            self._app.active_layout,
            self.layer_name,
            self.net,
            width,
            end_cap_style[1],
            end_cap_style[2],
            corner_style,
            center_line,
        )
        if cloned_path:
            return cloned_path

    # @pyaedt_function_handler
    @pyaedt_function_handler
    def create_edge_port(
        self,
        name,
        position="End",
        port_type="Wave",
        reference_layer=None,
        horizontal_extent_factor=5,
        vertical_extent_factor=3,
        pec_launch_width="0.01mm",
    ):
        """Parameters
        ----------
        name : str
            Name of the port.
        position : str, optional
            Position of the port. The default is ``"End"``, in which case the port is created at the end of the trace.
            Options are ``"Start"`` and ``"End"``.
        port_type : str, optional
            Type of the port. The default is ``"Wave"``, in which case a wave port is created. Options are ``"Wave"``
             and ``"Gap"``.
        reference_layer : str, optional
            Name of the references layer. The default is ``None``. Only available for gap port.
        horizontal_extent_factor : int, optional
            Horizontal extent factor of the wave port. The default is ``5``.
        vertical_extent_factor : int, optional
            Vertical extent factor of the wave port. The default is ``3``.
        pec_launch_width : float, str, optional
            Perfect electrical conductor width of the wave port. The default is ``"0.01mm"``.

        Returns
        -------
            :class:`pyaedt.edb_core.edb_data.sources.ExcitationPorts`

        Examples
        --------
        >>> edbapp = pyaedt.Edb("myproject.aedb")
        >>> sig = appedb.modeler.create_trace([[0, 0], ["9mm", 0]], "TOP", "1mm", "SIG", "Flat", "Flat")
        >>> sig.create_edge_port("pcb_port", "end", "Wave", None, 8, 8)

        """
        center_line = self.get_center_line()
        pos = center_line[-1] if position.lower() == "end" else center_line[0]

        if port_type.lower() == "wave":
            return self._app.hfss.create_wave_port(
                self.id, pos, name, 50, horizontal_extent_factor, vertical_extent_factor, pec_launch_width
            )
        else:
            return self._app.hfss.create_edge_port_vertical(self.id, pos, name, 50, reference_layer)

    pyaedt_function_handler()

    def create_via_fence(self, distance, gap, padstack_name):
        """Create via fences on both sides of the trace.

        Parameters
        ----------
        distance: str, float
            Distance between via fence and trace center line.
        gap: str, float
            Gap between vias.
        padstack_name: str
            Name of the via padstack.

        Returns
        -------

        """

        def getAngle(v1, v2):  # pragma: no cover
            v1_mag = math.sqrt(v1[0] ** 2 + v1[1] ** 2)
            v2_mag = math.sqrt(v2[0] ** 2 + v2[1] ** 2)
            dotsum = v1[0] * v2[0] + v1[1] * v2[1]
            if v1[0] * v2[1] - v1[1] * v2[0] > 0:
                scale = 1
            else:
                scale = -1
            dtheta = scale * math.acos(dotsum / (v1_mag * v2_mag))

            return dtheta

        def getLocations(line, gap):  # pragma: no cover
            location = [line[0]]
            residual = 0

            for n in range(len(line) - 1):
                x0, y0 = line[n]
                x1, y1 = line[n + 1]
                length = math.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2)
                dx, dy = (x1 - x0) / length, (y1 - y0) / length
                x = x0 - dx * residual
                y = y0 - dy * residual
                length = length + residual
                while length >= gap:
                    x += gap * dx
                    y += gap * dy
                    location.append((x, y))
                    length -= gap

                residual = length
            return location

        def getParalletLines(pts, distance):  # pragma: no cover
            leftline = []
            rightline = []

            x0, y0 = pts[0]
            x1, y1 = pts[1]
            vector = (x1 - x0, y1 - y0)
            orientation1 = getAngle((1, 0), vector)

            leftturn = orientation1 + math.pi / 2
            righrturn = orientation1 - math.pi / 2
            leftPt = (x0 + distance * math.cos(leftturn), y0 + distance * math.sin(leftturn))
            leftline.append(leftPt)
            rightPt = (x0 + distance * math.cos(righrturn), y0 + distance * math.sin(righrturn))
            rightline.append(rightPt)

            for n in range(1, len(pts) - 1):
                x0, y0 = pts[n - 1]
                x1, y1 = pts[n]
                x2, y2 = pts[n + 1]

                v1 = (x1 - x0, y1 - y0)
                v2 = (x2 - x1, y2 - y1)
                dtheta = getAngle(v1, v2)
                orientation1 = getAngle((1, 0), v1)

                leftturn = orientation1 + dtheta / 2 + math.pi / 2
                righrturn = orientation1 + dtheta / 2 - math.pi / 2

                distance2 = distance / math.sin((math.pi - dtheta) / 2)
                leftPt = (x1 + distance2 * math.cos(leftturn), y1 + distance2 * math.sin(leftturn))
                leftline.append(leftPt)
                rightPt = (x1 + distance2 * math.cos(righrturn), y1 + distance2 * math.sin(righrturn))
                rightline.append(rightPt)

            x0, y0 = pts[-2]
            x1, y1 = pts[-1]

            vector = (x1 - x0, y1 - y0)
            orientation1 = getAngle((1, 0), vector)
            leftturn = orientation1 + math.pi / 2
            righrturn = orientation1 - math.pi / 2
            leftPt = (x1 + distance * math.cos(leftturn), y1 + distance * math.sin(leftturn))
            leftline.append(leftPt)
            rightPt = (x1 + distance * math.cos(righrturn), y1 + distance * math.sin(righrturn))
            rightline.append(rightPt)
            return leftline, rightline

        distance = self._pedb.edb_value(distance).ToDouble()
        gap = self._pedb.edb_value(gap).ToDouble()
        center_line = self.get_center_line()
        leftline, rightline = getParalletLines(center_line, distance)
        for x, y in getLocations(rightline, gap) + getLocations(leftline, gap):
            self._pedb.padstacks.place([x, y], padstack_name)


class EdbRectangle(EDBPrimitives, RectangleDotNet):
    def __init__(self, raw_primitive, core_app):
        EDBPrimitives.__init__(self, raw_primitive, core_app)
        RectangleDotNet.__init__(self, self._app, raw_primitive)


class EdbCircle(EDBPrimitives, CircleDotNet):
    def __init__(self, raw_primitive, core_app):
        EDBPrimitives.__init__(self, raw_primitive, core_app)
        CircleDotNet.__init__(self, self._app, raw_primitive)


class EdbPolygon(EDBPrimitives, PolygonDotNet):
    def __init__(self, raw_primitive, core_app):
        EDBPrimitives.__init__(self, raw_primitive, core_app)
        PolygonDotNet.__init__(self, self._app, raw_primitive)

    @pyaedt_function_handler
    def clone(self):
        """Clone a primitive object with keeping same definition and location.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        cloned_poly = self._app.edb_api.cell.primitive.polygon.create(
            self._app.active_layout, self.layer_name, self.net, self.polygon_data.edb_api
        )
        if cloned_poly:
            for void in self.voids:
                cloned_void = self._app.edb_api.cell.primitive.polygon.create(
                    self._app.active_layout, self.layer_name, self.net, void.polygon_data.edb_api
                )
                # cloned_void
                cloned_poly.prim_obj.AddVoid(cloned_void.prim_obj)
            return cloned_poly
        return False

    @pyaedt_function_handler()
    def in_polygon(
        self,
        point_data,
        include_partial=True,
    ):
        """Check if padstack Instance is in given polygon data.

        Parameters
        ----------
        point_data : PointData Object or list of float
        include_partial : bool, optional
            Whether to include partial intersecting instances. The default is ``True``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if isinstance(point_data, list):
            point_data = self._app.edb_api.geometry.point_data(
                self._app.edb_value(point_data[0]), self._app.edb_value(point_data[1])
            )
        int_val = int(self.polygon_data.edb_api.PointInPolygon(point_data))

        # Intersection type:
        # 0 = objects do not intersect
        # 1 = this object fully inside other (no common contour points)
        # 2 = other object fully inside this
        # 3 = common contour points 4 = undefined intersection
        if int_val == 0:
            return False
        elif include_partial:
            return True
        elif int_val < 3:
            return True
        else:
            return False

    # @pyaedt_function_handler()
    # def add_void(self, point_list):
    #     """Add a void to current primitive.
    #
    #     Parameters
    #     ----------
    #     point_list : list or  :class:`pyaedt.edb_core.edb_data.primitives_data.EDBPrimitives` or EDB Primitive Object
    #         Point list in the format of `[[x1,y1], [x2,y2],..,[xn,yn]]`.
    #
    #     Returns
    #     -------
    #     bool
    #         ``True`` if successful, either  ``False``.
    #     """
    #     if isinstance(point_list, list):
    #         plane = self._app.modeler.Shape("polygon", points=point_list)
    #         _poly = self._app.modeler.shape_to_polygon_data(plane)
    #         if _poly is None or _poly.IsNull() or _poly is False:
    #             self._logger.error("Failed to create void polygon data")
    #             return False
    #         prim = self._app.edb_api.cell.primitive.polygon.create(
    #             self._app.active_layout, self.layer_name, self.primitive_object.GetNet(), _poly
    #         )
    #     elif isinstance(point_list, EDBPrimitives):
    #         prim = point_list.primitive_object
    #     else:
    #         prim = point_list
    #     return self.add_void(prim)


class EdbText(EDBPrimitivesMain, TextDotNet):
    def __init__(self, raw_primitive, core_app):
        TextDotNet.__init__(self, self._app, raw_primitive)
        EDBPrimitives.__init__(self, raw_primitive, core_app)


class EdbBondwire(EDBPrimitivesMain, BondwireDotNet):
    def __init__(self, raw_primitive, core_app):
        BondwireDotNet.__init__(self, self._app, raw_primitive)
        EDBPrimitives.__init__(self, raw_primitive, core_app)


class EDBArcs(object):
    """Manages EDB Arc Data functionalities.
    It Inherits EDB primitives arcs properties.

    Examples
    --------
    >>> from pyaedt import Edb
    >>> edb = Edb(myedb, edbversion="2021.2")
    >>> prim_arcs = edb.modeler.primitives[0].arcs
    >>> prim_arcs.center # arc center
    >>> prim_arcs.points # arc point list
    >>> prim_arcs.mid_point # arc mid point
    """

    def __init__(self, app, arc):
        self._app = app
        self.arc_object = arc

    @property
    def start(self):
        """Get the coordinates of the starting point.

        Returns
        -------
        list
            List containing the X and Y coordinates of the starting point.


        Examples
        --------
        >>> appedb = Edb(fpath, edbversion="2023.2")
        >>> start_coordinate = appedb.nets["V1P0_S0"].primitives[0].arcs[0].start
        >>> print(start_coordinate)
        [x_value, y_value]
        """
        point = self.arc_object.Start
        return [point.X.ToDouble(), point.Y.ToDouble()]

    @property
    def end(self):
        """Get the coordinates of the ending point.

        Returns
        -------
        list
            List containing the X and Y coordinates of the ending point.

        Examples
        --------
        >>> appedb = Edb(fpath, edbversion="2023.2")
        >>> end_coordinate = appedb.nets["V1P0_S0"].primitives[0].arcs[0].end
        """
        point = self.arc_object.End
        return [point.X.ToDouble(), point.Y.ToDouble()]

    @property
    def height(self):
        """Get the height of the arc.

        Returns
        -------
        float
            Height of the arc.


        Examples
        --------
        >>> appedb = Edb(fpath, edbversion="2023.2")
        >>> arc_height = appedb.nets["V1P0_S0"].primitives[0].arcs[0].height
        """
        return self.arc_object.Height

    @property
    def center(self):
        """Arc center.

        Returns
        -------
        list
        """
        cent = self.arc_object.GetCenter()
        return [cent.X.ToDouble(), cent.Y.ToDouble()]

    @property
    def length(self):
        """Arc length.

        Returns
        -------
        float
        """
        return self.arc_object.GetLength()

    @property
    def mid_point(self):
        """Arc mid point.

        Returns
        -------
        float
        """
        return self.arc_object.GetMidPoint()

    @property
    def radius(self):
        """Arc radius.

        Returns
        -------
        float
        """
        return self.arc_object.GetRadius()

    @property
    def is_segment(self):
        """Either if it is a straight segment or not.

        Returns
        -------
        bool
        """
        return self.arc_object.IsSegment()

    @property
    def is_point(self):
        """Either if it is a point or not.

        Returns
        -------
        bool
        """
        return self.arc_object.IsPoint()

    @property
    def is_ccw(self):
        """Test whether arc is counter clockwise.

        Returns
        -------
        bool
        """
        return self.arc_object.IsCCW()

    @property
    def points_raw(self):
        """Return a list of Edb points.

        Returns
        -------
        list
            Edb Points.
        """
        return list(self.arc_object.GetPointData())

    @property
    def points(self, arc_segments=6):
        """Return the list of points with arcs converted to segments.

        Parameters
        ----------
        arc_segments : int
            Number of facets to convert an arc. Default is `6`.

        Returns
        -------
        list, list
            x and y list of points.
        """
        try:
            my_net_points = self.points_raw
            xt, yt = self._app._get_points_for_plot(my_net_points, arc_segments)
            if not xt:
                return []
            x, y = GeometryOperators.orient_polygon(xt, yt, clockwise=True)
            return x, y
        except:
            x = []
            y = []
        return x, y
