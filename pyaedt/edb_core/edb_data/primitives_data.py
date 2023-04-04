import math

from pyaedt.edb_core.general import convert_py_list_to_net_list
from pyaedt.generic.general_methods import pyaedt_function_handler
from pyaedt.modeler.geometry_operators import GeometryOperators


class EDBPrimitives(object):
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

    def __getattr__(self, key):
        try:
            return self[key]
        except:
            try:
                return getattr(self.primitive_object, key)
            except AttributeError:
                raise AttributeError("Attribute not present")

    def __init__(self, raw_primitive, core_app):
        self._app = core_app
        self._core_stackup = core_app.stackup
        self._core_net = core_app.nets
        self.primitive_object = raw_primitive

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
    def is_void(self):
        """Either if the primitive is a void or not.

        Returns
        -------
        bool
        """
        if not hasattr(self.primitive_object, "IsVoid"):
            return False
        return self.primitive_object.IsVoid()

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

    @property
    def id(self):
        """Primitive ID.

        Returns
        -------
        int
        """
        return self.GetId()

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
        """
        Get the points to be plotted.
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

    @pyaedt_function_handler()
    def __repr__(self):
        return f"{self.id}: '{self.type}' on net: '{self.net_name}' and on layer '{self.layer_name}'."

    @pyaedt_function_handler()
    def points(self, arc_segments=6):
        """Return the list of points with arcs converted to segments.

        Parameters
        ----------
        arc_segments : int
            Number of facets to convert an arc. Default is `6`.

        Returns
        -------
        tuple
            The tuple contains 2 lists made of X and Y points coordinates.
        """
        try:
            my_net_points = list(self.primitive_object.GetPolygonData().Points)
            xt, yt = self._get_points_for_plot(my_net_points, arc_segments)
            if not xt:
                return []
            x, y = GeometryOperators.orient_polygon(xt, yt, clockwise=True)
            return x, y
        except:
            x = []
            y = []
        return x, y

    @property
    def voids(self):
        """Return a list of voids of the given primitive if any.

        Returns
        -------
        list of :class:`pyaedt.edb_core.edb_data.primitives_data.EDBPrimitives`
        """
        voids = []
        for void in self.primitive_object.Voids:
            voids.append(EDBPrimitives(void, self._app))
        return voids

    @pyaedt_function_handler()
    def points_raw(self):
        """Return a list of Edb points.

        Returns
        -------
        list
            Edb Points.
        """
        points = []
        try:
            my_net_points = list(self.primitive_object.GetPolygonData().Points)
            for point in my_net_points:
                points.append(point)
            return points
        except:
            return points

    @property
    def bbox(self):
        """Return the primitive bounding box points. Lower left corner, upper right corner.

        Returns
        -------
        list
            [lower_left x, lower_left y, upper right x, upper right y]

        """
        bbox = self.polygon_data.GetBBox()
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

    @pyaedt_function_handler()
    def is_arc(self, point):
        """Either if a point is an arc or not.

        Returns
        -------
        bool
        """
        return point.IsArc()

    @property
    def type(self):
        """Return the type of the primitive.
        Allowed outputs are ``"Circle"``, ``"Rectangle"``,``"Polygon"``,``"Path"`` or ``"Bondwire"``.

        Returns
        -------
        str
        """
        types = ["Circle", "Path", "Polygon", "Rectangle", "Bondwire"]
        str_type = self.primitive_object.ToString().split(".")
        if str_type[-1] in types:
            return str_type[-1]
        return None

    @property
    def net(self):
        """Return EDB Net Object."""
        return self.primitive_object.GetNet()

    @property
    def net_name(self):
        """Get or Set the primitive net name.

        Returns
        -------
        str
        """
        return self.net.GetName()

    @net_name.setter
    def net_name(self, val):
        if not isinstance(val, str):
            try:
                self.primitive_object.SetNet(val)
            except:
                raise AttributeError("Value inserted not found. Input has to be layer name or net object.")
        elif val in self._core_net.nets:
            net = self._core_net.nets[val].net_object
            self.primitive_object.SetNet(net)
        else:
            raise AttributeError("Value inserted not found. Input has to be layer name or net object.")

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
        if val in self._core_stackup.stackup_layers.layers:
            lay = self._core_stackup.stackup_layers.layers[val]._edb_layer
            self.primitive_object.SetLayer(lay)
        elif not isinstance(val, str):
            try:
                self.primitive_object.SetLayer(val)
            except:
                raise AttributeError("Value inserted not found. Input has to be layer name or layer object.")
        else:
            raise AttributeError("Value inserted not found. Input has to be layer name or layer object.")

    @pyaedt_function_handler()
    def delete(self):
        """Delete this primitive."""
        return self.primitive_object.Delete()

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
    def add_void(self, point_list):
        """Add a void to current primitive.

        Parameters
        ----------
        point_list : list or  :class:`pyaedt.edb_core.edb_data.primitives_data.EDBPrimitives` or EDB Primitive Object
            Point list in the format of `[[x1,y1], [x2,y2],..,[xn,yn]]`.

        Returns
        -------
        bool
            ``True`` if successful, either  ``False``.
        """
        if isinstance(point_list, list):
            plane = self._app.modeler.Shape("polygon", points=point_list)
            _poly = self._app.modeler.shape_to_polygon_data(plane)
            if _poly is None or _poly.IsNull() or _poly is False:
                self._logger.error("Failed to create void polygon data")
                return False
            prim = self._app.edb.Cell.Primitive.Polygon.Create(
                self._app.active_layout, self.layer_name, self.primitive_object.GetNet(), _poly
            )
        elif isinstance(point_list, EDBPrimitives):
            prim = point_list.primitive_object
        else:
            prim = point_list
        return self.primitive_object.AddVoid(prim)

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
        for prim in primitives:
            if isinstance(prim, EDBPrimitives):
                primi_polys.append(prim.primitive_object.GetPolygonData())
            else:
                try:
                    primi_polys.append(prim.GetPolygonData())
                except:
                    primi_polys.append(prim)
        list_poly = poly.Subtract(convert_py_list_to_net_list([poly]), convert_py_list_to_net_list(primi_polys))
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
                        void_pdata = void.primitive_object.GetPolygonData()
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
                                    EDBPrimitives(
                                        self._app.modeler.create_polygon(
                                            polys_clean, self.layer_name, net_name=self.net_name, voids=void_to_append
                                        ),
                                        self._app,
                                    )
                                )
                    else:
                        new_polys.append(
                            EDBPrimitives(
                                self._app.modeler.create_polygon(
                                    p, self.layer_name, net_name=self.net_name, voids=list_void
                                ),
                                self._app,
                            )
                        )
                else:
                    new_polys.append(
                        EDBPrimitives(
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
                        void_pdata = void.primitive_object.GetPolygonData()
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
                            EDBPrimitives(
                                self._app.modeler.create_polygon(
                                    polys_clean, self.layer_name, net_name=self.net_name, voids=void_to_append
                                ),
                                self._app,
                            )
                        )
                    else:
                        new_polys.append(
                            EDBPrimitives(
                                self._app.modeler.create_polygon(
                                    p, self.layer_name, net_name=self.net_name, voids=list_void
                                ),
                                self._app,
                            )
                        )
                else:
                    new_polys.append(
                        EDBPrimitives(
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
                    EDBPrimitives(
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

    @property
    def polygon_data(self):
        """Get the Primitive Polygon data object."""
        return self.primitive_object.GetPolygonData()

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
        if isinstance(primitive, EDBPrimitives):
            poly = primitive.polygon_data
        return int(self.polygon_data.GetIntersectionType(poly))

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
        if isinstance(point, list):
            point = self._app.edb.Geometry.PointData(self._app.edb_value(point[0]), self._app.edb_value(point[1]))

        p0 = self.polygon_data.GetClosestPoint(point)
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
        if isinstance(point, self._app.edb.Geometry.PointData):
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
        arcs = []
        if self.polygon_data.IsClosed():
            arcs = [EDBArcs(self, i) for i in list(self.polygon_data.GetArcData())]
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
            point_data = self._app.edb.Geometry.PointData(
                self._app.edb_value(point_data[0]), self._app.edb_value(point_data[1])
            )
        int_val = int(self.polygon_data.PointInPolygon(point_data))

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

    @pyaedt_function_handler
    def clone(self):
        """Clone a primitive object with keeping same definition and location.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        if self.type == "Path":
            center_line = self.primitive_object.GetCenterLine()
            width = self.primitive_object.GetWidthValue()
            corner_style = self.primitive_object.GetCornerStyle()
            end_cap_style = self.primitive_object.GetEndCapStyle()
            cloned_path = self._app.edb.Cell.Primitive.Path.Create(
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
        cloned_poly = self._app.edb.Cell.Primitive.Polygon.Create(
            self._app.active_layout, self.layer_name, self.net, self.polygon_data
        )
        if cloned_poly:
            return cloned_poly
        return False


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
