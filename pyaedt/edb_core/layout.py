"""
This module contains these classes: `EdbLayout` and `Shape`.
"""
import math

from pyaedt.edb_core.edb_data.primitives_data import EDBPrimitives
from pyaedt.edb_core.edb_data.utilities import EDBStatistics
from pyaedt.edb_core.general import convert_py_list_to_net_list
from pyaedt.generic.clr_module import Tuple
from pyaedt.generic.general_methods import pyaedt_function_handler


class EdbLayout(object):
    """Manages EDB methods for primitives management accessible from `Edb.modeler` property.

    Examples
    --------
    >>> from pyaedt import Edb
    >>> edbapp = Edb("myaedbfolder", edbversion="2021.2")
    >>> edb_layout = edbapp.modeler
    """

    def __init__(self, p_edb):
        self._pedb = p_edb
        self._prims = []

    @property
    def _edb(self):
        return self._pedb.edb

    def _get_edb_value(self, value):
        return self._pedb.edb_value(value)

    @property
    def _logger(self):
        """Logger."""
        return self._pedb.logger

    @property
    def _builder(self):
        return self._pedb.builder

    @property
    def _edbutils(self):
        return self._pedb.edbutils

    @property
    def _active_layout(self):
        return self._pedb.active_layout

    @property
    def _cell(self):
        return self._pedb.active_cell

    @property
    def db(self):
        """Db object."""
        return self._pedb.db

    @property
    def layers(self):
        """Dictionary of layers.

        Returns
        -------
        dict
            Dictionary of layers.
        """
        return self._pedb.stackup.layers

    @property
    def primitives(self):
        """Primitives.

        Returns
        -------
        list of :class:`pyaedt.edb_core.edb_data.primitives_data.EDBPrimitives`
            List of primitives.
        """
        # TODO: See https://github.com/pyansys/pyaedt/issues/2768
        self._update_primitives()
        return self._prims

    @pyaedt_function_handler()
    def _update_primitives(self):
        """Method to ensure that the list of primitives is correct."""

        self._prims = []
        if self._active_layout:
            for lay_obj in list(self._active_layout.Primitives):
                self._prims.append(EDBPrimitives(lay_obj, self._pedb))
        return True

    @property
    def polygons_by_layer(self):
        """Primitives with layer names as keys.

        Returns
        -------
        dict
            Dictionary of primitives with layer names as keys.
        """
        _primitives_by_layer = {}
        for lay in self.layers:
            _primitives_by_layer[lay] = self.get_polygons_by_layer(lay)
        return _primitives_by_layer

    @property
    def primitives_by_net(self):
        """Primitives with net names as keys.

        Returns
        -------
        dict
            Dictionary of primitives with nat names as keys.
        """
        _prim_by_net = {}
        for net in list(self._pedb.nets.nets.keys()):
            _prim_by_net[net] = [
                EDBPrimitives(i, self._pedb) for i in self._active_layout.Primitives if i.GetNet().GetName() == net
            ]
        return _prim_by_net

    @property
    def primitives_by_layer(self):
        """Primitives with layer names as keys.

        Returns
        -------
        dict
            Dictionary of primitives with layer names as keys.
        """
        _primitives_by_layer = {}
        for lay in self.layers:
            _primitives_by_layer[lay] = []
        for i in self._active_layout.Primitives:
            lay = i.GetLayer().GetName()
            _primitives_by_layer[lay].append(EDBPrimitives(i, self._pedb))
        return _primitives_by_layer

    @property
    def rectangles(self):
        """Rectangles.

        Returns
        -------
        list of :class:`pyaedt.edb_core.edb_data.primitives_data.EDBPrimitives`
            List of rectangles.

        """
        return [i for i in self.primitives if i.type == "Rectangle"]

    @property
    def circles(self):
        """Circles.

        Returns
        -------
        list of :class:`pyaedt.edb_core.edb_data.primitives_data.EDBPrimitives`
            List of circles.

        """
        return [i for i in self.primitives if i.type == "Circle"]

    @property
    def paths(self):
        """Paths.

        Returns
        -------
        list of :class:`pyaedt.edb_core.edb_data.primitives_data.EDBPrimitives`
            List of paths.
        """
        return [i for i in self.primitives if i.type == "Path"]

    @property
    def bondwires(self):
        """Bondwires.

        Returns
        -------
        list of :class:`pyaedt.edb_core.edb_data.primitives_data.EDBPrimitives`
            List of bondwires.
        """
        return [i for i in self.primitives if i.type == "Bondwire"]

    @property
    def polygons(self):
        """Polygons.

        Returns
        -------
        list of :class:`pyaedt.edb_core.edb_data.primitives_data.EDBPrimitives`
            List of polygons.
        """
        return [i for i in self.primitives if i.type == "Polygon"]

    @pyaedt_function_handler()
    def get_polygons_by_layer(self, layer_name, net_list=None):
        """Retrieve polygons by a layer.

        Parameters
        ----------
        layer_name : str
            Name of the layer.
        net_list : list, optional
            List of net names.

        Returns
        -------
        list
            List of primitive objects.
        """
        objinst = []
        for el in self.polygons:
            if el.GetLayer().GetName() == layer_name:
                if net_list and el.GetNet().GetName() in net_list:
                    objinst.append(el)
                else:
                    objinst.append(el)
        return objinst

    @pyaedt_function_handler()
    def get_polygon_bounding_box(self, polygon):
        """Retrieve a polygon bounding box.

        Parameters
        ----------
        polygon :
            Name of the polygon.

        Returns
        -------
        list
            List of bounding box coordinates in the format ``[-x, -y, +x, +y]``.

        Examples
        --------
        >>> poly = edb_core.modeler.get_polygons_by_layer("GND")
        >>> bounding = edb_core.modeler.get_polygon_bounding_box(poly[0])
        """
        bounding = []
        try:
            bounding_box = polygon.GetPolygonData().GetBBox()
            bounding = [
                bounding_box.Item1.X.ToDouble(),
                bounding_box.Item1.Y.ToDouble(),
                bounding_box.Item2.X.ToDouble(),
                bounding_box.Item2.Y.ToDouble(),
            ]
        except:
            pass
        return bounding

    @pyaedt_function_handler()
    def get_polygon_points(self, polygon):
        """Retrieve polygon points.

        .. note::
           For arcs, one point is returned.

        Parameters
        ----------
        polygon :
            Name of the polygon.

        Returns
        -------
        list
            List of doubles.

        Examples
        --------

        >>> poly = edb_core.modeler.get_polygons_by_layer("GND")
        >>> points  = edb_core.modeler.get_polygon_points(poly[0])

        """
        points = []
        i = 0
        continue_iterate = True
        prev_point = None
        while continue_iterate:
            try:
                point = polygon.GetPolygonData().GetPoint(i)
                if prev_point != point:
                    if point.IsArc():
                        points.append([point.X.ToDouble()])
                    else:
                        points.append([point.X.ToDouble(), point.Y.ToDouble()])
                    prev_point = point
                    i += 1
                else:
                    continue_iterate = False
            except:
                continue_iterate = False
        return points

    @pyaedt_function_handler()
    def parametrize_polygon(self, polygon, selection_polygon, offset_name="offsetx", origin=None):
        """Parametrize pieces of a polygon based on another polygon.

        Parameters
        ----------
        polygon :
            Name of the polygon.
        selection_polygon :
            Polygon to use as a filter.
        offset_name : str, optional
            Name of the offset to create.  The default is ``"offsetx"``.
        origin : list, optional
            List of the X and Y origins, which impacts the vector
            computation and is needed to determine expansion direction.
            The default is ``None``, in which case the vector is
            computed from the polygon's center.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """

        def calc_slope(point, origin):
            if point[0] - origin[0] != 0:
                slope = math.atan((point[1] - origin[1]) / (point[0] - origin[0]))
                xcoeff = math.sin(slope)
                ycoeff = math.cos(slope)

            else:
                if point[1] > 0:
                    xcoeff = 0
                    ycoeff = 1
                else:
                    xcoeff = 0
                    ycoeff = -1
            if ycoeff > 0:
                ycoeff = "+" + str(ycoeff)
            else:
                ycoeff = str(ycoeff)
            if xcoeff > 0:
                xcoeff = "+" + str(xcoeff)
            else:
                xcoeff = str(xcoeff)
            return xcoeff, ycoeff

        selection_polygon_data = selection_polygon.GetPolygonData()
        poligon_data = polygon.GetPolygonData()
        bound_center = poligon_data.GetBoundingCircleCenter()
        bound_center2 = selection_polygon_data.GetBoundingCircleCenter()
        center = [bound_center.X.ToDouble(), bound_center.Y.ToDouble()]
        center2 = [bound_center2.X.ToDouble(), bound_center2.Y.ToDouble()]
        x1, y1 = calc_slope(center2, center)

        if not origin:
            origin = [center[0] + float(x1) * 10000, center[1] + float(y1) * 10000]
        self._pedb.add_design_variable(offset_name, 0.0, is_parameter=True)
        i = 0
        continue_iterate = True
        prev_point = None
        while continue_iterate:
            try:
                point = poligon_data.GetPoint(i)
                if prev_point != point:
                    check_inside = selection_polygon_data.PointInPolygon(point)
                    if check_inside:
                        xcoeff, ycoeff = calc_slope([point.X.ToDouble(), point.X.ToDouble()], origin)

                        new_points = self._edb.Geometry.PointData(
                            self._get_edb_value(point.X.ToString() + "{}*{}".format(xcoeff, offset_name)),
                            self._get_edb_value(point.Y.ToString() + "{}*{}".format(ycoeff, offset_name)),
                        )
                        poligon_data.SetPoint(i, new_points)
                    prev_point = point
                    i += 1
                else:
                    continue_iterate = False
            except:
                continue_iterate = False
        polygon.SetPolygonData(poligon_data)
        return True

    @pyaedt_function_handler()
    def _create_path(
        self,
        path_list,
        layer_name,
        width=1,
        net_name="",
        start_cap_style="Round",
        end_cap_style="Round",
        corner_style="Round",
    ):
        """
        Create a path based on a list of points.

        Parameters
        ----------
        path_list : :class:`pyaedt.edb_core.layout.Shape`
            List of points.
        layer_name : str
            Name of the layer on which to create the path.
        width : float, optional
            Width of the path. The default is ``1``.
        net_name : str, optional
            Name of the net. The default is ``""``.
        start_cap_style : str, optional
            Style of the cap at its start. Options are ``"Round"``,
            ``"Extended",`` and ``"Flat"``. The default is
            ``"Round"``.
        end_cap_style : str, optional
            Style of the cap at its end. Options are ``"Round"``,
            ``"Extended",`` and ``"Flat"``. The default is
            ``"Round"``.
        corner_style : str, optional
            Style of the corner. Options are ``"Round"``,
            ``"Sharp"`` and ``"Mitered"``. The default is ``"Round"``.

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.primitives_data.EDBPrimitives`
            ``True`` when successful, ``False`` when failed.
        """
        net = self._pedb.nets.find_or_create_net(net_name)
        if start_cap_style.lower() == "round":
            start_cap_style = self._edb.Cell.Primitive.PathEndCapStyle.Round
        elif start_cap_style.lower() == "extended":
            start_cap_style = self._edb.Cell.Primitive.PathEndCapStyle.Extended  # pragma: no cover
        else:
            start_cap_style = self._edb.Cell.Primitive.PathEndCapStyle.Flat  # pragma: no cover
        if end_cap_style.lower() == "round":
            end_cap_style = self._edb.Cell.Primitive.PathEndCapStyle.Round  # pragma: no cover
        elif end_cap_style.lower() == "extended":
            end_cap_style = self._edb.Cell.Primitive.PathEndCapStyle.Extended  # pragma: no cover
        else:
            end_cap_style = self._edb.Cell.Primitive.PathEndCapStyle.Flat
        if corner_style.lower() == "round":
            corner_style = self._edb.Cell.Primitive.PathCornerStyle.RoundCorner
        elif corner_style.lower() == "sharp":
            corner_style = self._edb.Cell.Primitive.PathCornerStyle.SharpCorner  # pragma: no cover
        else:
            corner_style = self._edb.Cell.Primitive.PathCornerStyle.MiterCorner  # pragma: no cover

        pointlists = [
            self._edb.Geometry.PointData(self._get_edb_value(i[0]), self._get_edb_value(i[1])) for i in path_list.points
        ]
        polygonData = self._edb.Geometry.PolygonData(convert_py_list_to_net_list(pointlists), False)
        polygon = self._edb.Cell.Primitive.Path.Create(
            self._active_layout,
            layer_name,
            net,
            self._get_edb_value(width),
            start_cap_style,
            end_cap_style,
            corner_style,
            polygonData,
        )
        if polygon.IsNull():
            self._logger.error("Null path created")
            return False
        return EDBPrimitives(polygon, self._pedb)

    @pyaedt_function_handler()
    def create_trace(
        self,
        path_list,
        layer_name,
        width=1,
        net_name="",
        start_cap_style="Round",
        end_cap_style="Round",
        corner_style="Round",
    ):
        """
        Create a trace based on a list of points.

        Parameters
        ----------
        path_list : list
            List of points.
        layer_name : str
            Name of the layer on which to create the path.
        width : float, optional
            Width of the path. The default is ``1``.
        net_name : str, optional
            Name of the net. The default is ``""``.
        start_cap_style : str, optional
            Style of the cap at its start. Options are ``"Round"``,
            ``"Extended",`` and ``"Flat"``. The default is
            ``"Round"``.
        end_cap_style : str, optional
            Style of the cap at its end. Options are ``"Round"``,
            ``"Extended",`` and ``"Flat"``. The default is
            ``"Round"``.
        corner_style : str, optional
            Style of the corner. Options are ``"Round"``,
            ``"Sharp"`` and ``"Mitered"``. The default is ``"Round"``.

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.primitives_data.EDBPrimitives`
        """
        path = self.Shape("Polygon", points=path_list)
        primitive = self._create_path(
            path,
            layer_name=layer_name,
            net_name=net_name,
            width=width,
            start_cap_style=start_cap_style,
            end_cap_style=end_cap_style,
            corner_style=corner_style,
        )
        if primitive:
            self._prims.append(primitive)
            return primitive
        else:
            return False

    @pyaedt_function_handler()
    def create_polygon(self, main_shape, layer_name, voids=[], net_name=""):
        """Create a polygon based on a list of points and voids.

        Parameters
        ----------
        main_shape : list of points or PolygonData or ``modeler.Shape``
            Shape or point lists of the main object.
        layer_name : str
            Name of the layer on which to create the polygon.
        voids : list, optional
            List of shape objects for voids or points that creates the shapes. The default is``[]``.
        net_name : str, optional
            Name of the net. The default is ``""``.

        Returns
        -------
        bool, :class:`pyaedt.edb_core.edb_data.primitives.EDBPrimitives`
            Polygon when successful, ``False`` when failed.
        """
        net = self._pedb.nets.find_or_create_net(net_name)
        if isinstance(main_shape, list):
            shape = self.Shape("polygon", points=main_shape)
            polygonData = self.shape_to_polygon_data(shape)
        elif isinstance(main_shape, EdbLayout.Shape):
            polygonData = self.shape_to_polygon_data(main_shape)
        else:
            polygonData = main_shape
        if polygonData is None or polygonData.IsNull() or polygonData is False:
            self._logger.error("Failed to create main shape polygon data")
            return False
        for void in voids:
            if isinstance(void, list):
                void = self.Shape("polygon", points=void)
                voidPolygonData = self.shape_to_polygon_data(void)
            elif isinstance(void, EdbLayout.Shape):
                voidPolygonData = self.shape_to_polygon_data(void)
            else:
                voidPolygonData = void
            if voidPolygonData is None or voidPolygonData.IsNull() or polygonData is False:
                self._logger.error("Failed to create void polygon data")
                return False
            polygonData.AddHole(voidPolygonData)
        polygon = self._edb.Cell.Primitive.Polygon.Create(self._active_layout, layer_name, net, polygonData)
        if polygon.IsNull() or polygonData is False:
            self._logger.error("Null polygon created")
            return False
        else:
            p = EDBPrimitives(polygon, self._pedb)
            self._prims.append(p)
            return p

    @pyaedt_function_handler()
    def create_polygon_from_points(self, point_list, layer_name, net_name=""):
        """Create a new polygon from a point list.

        Parameters
        ----------
        point_list : list
            Point list in the format of `[[x1,y1], [x2,y2],..,[xn,yn]]`.
        layer_name : str
            Name of layer on which create the polygon.
        net_name : str, optional
            Name of the net on which create the polygon.

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.primitives_data.EDBPrimitives`
        """
        net = self._pedb.nets.find_or_create_net(net_name)
        plane = self.Shape("polygon", points=point_list)
        _poly = self.shape_to_polygon_data(plane)
        if _poly is None or _poly.IsNull() or _poly is False:
            self._logger.error("Failed to create main shape polygon data")
            return False
        polygon = self._edb.Cell.Primitive.Polygon.Create(self._active_layout, layer_name, net, _poly)
        if polygon.IsNull():
            self._logger.error("Null polygon created")
            return False
        else:
            p = EDBPrimitives(polygon, self._pedb)
            self._prims.append(p)
            return p

    @pyaedt_function_handler()
    def create_rectangle(
        self,
        layer_name,
        net_name="",
        lower_left_point="",
        upper_right_point="",
        center_point="",
        width="",
        height="",
        representation_type="LowerLeftUpperRight",
        corner_radius="0mm",
        rotation="0deg",
    ):
        """Create rectangle.

        Parameters
        ----------
        layer_name : str
            Name of the layer on which to create the rectangle.
        net_name : str
            Name of the net. The default is ``""``.
        lower_left_point : list
            Lower left point when ``representation_type="LowerLeftUpperRight"``. The default is ``""``.
        upper_right_point : list
            Upper right point when ``representation_type="LowerLeftUpperRight"``. The default is ``""``.
        center_point : list
            Center point when ``representation_type="CenterWidthHeight"``. The default is ``""``.
        width : str
            Width of the rectangle when ``representation_type="CenterWidthHeight"``. The default is ``""``.
        height : str
            Height of the rectangle when ``representation_type="CenterWidthHeight"``. The default is ``""``.
        representation_type : str, optional
            Type of the rectangle representation. The default is ``LowerLeftUpperRight``. Options are
            ``"LowerLeftUpperRight"`` and ``"CenterWidthHeight"``.
        corner_radius : str, optional
            Radius of the rectangle corner. The default is ``"0mm"``.
        rotation : str, optional
            Rotation of the rectangle. The default is ``"0deg"``.

        Returns
        -------
         :class:`pyaedt.edb_core.edb_data.primitives_data.EDBPrimitives`
            Rectangle when successful, ``False`` when failed.
        """
        edb_net = self._pedb.nets.find_or_create_net(net_name)
        if representation_type == "LowerLeftUpperRight":
            rep_type = self._edb.Cell.Primitive.RectangleRepresentationType.LowerLeftUpperRight
            rect = self._edb.Cell.Primitive.Rectangle.Create(
                self._active_layout,
                layer_name,
                edb_net,
                rep_type,
                self._get_edb_value(lower_left_point[0]),
                self._get_edb_value(lower_left_point[1]),
                self._get_edb_value(upper_right_point[0]),
                self._get_edb_value(upper_right_point[1]),
                self._get_edb_value(corner_radius),
                self._get_edb_value(rotation),
            )
        else:
            rep_type = self._edb.Cell.Primitive.RectangleRepresentationType.CenterWidthHeight
            rect = self._edb.Cell.Primitive.Rectangle.Create(
                self._active_layout,
                layer_name,
                edb_net,
                rep_type,
                self._get_edb_value(center_point[0]),
                self._get_edb_value(center_point[1]),
                self._get_edb_value(width),
                self._get_edb_value(height),
                self._get_edb_value(corner_radius),
                self._get_edb_value(rotation),
            )
        if rect:
            p = EDBPrimitives(rect, self._pedb)
            self._prims.append(p)
            return p
        return False  # pragma: no cover

    @pyaedt_function_handler()
    def create_circle(self, layer_name, x, y, radius, net_name=""):
        """Create a circle on a specified layer.

        Parameters
        ----------
        layer_name : str
            Name of the layer.
        x : float
            Position on the X axis.
        y : float
            Position on the Y axis.
        radius : float
            Radius of the circle.
        net_name : str, optional
            Name of the net. The default is ``None``, in which case the
            default name is assigned.

        Returns
        -------
        :class:`pyaedt.edb_core.edb_data.primitives_data.EDBPrimitives`
            Objects of the circle created when successful.
        """
        edb_net = self._pedb.nets.find_or_create_net(net_name)

        circle = self._edb.Cell.Primitive.Circle.Create(
            self._active_layout,
            layer_name,
            edb_net,
            self._get_edb_value(x),
            self._get_edb_value(y),
            self._get_edb_value(radius),
        )
        if circle:
            p = EDBPrimitives(circle, self._pedb)
            self._prims.append(p)
            return p
        return False  # pragma: no cover

    @pyaedt_function_handler
    def delete_primitives(self, net_names):
        """Delete primitives by net names.

        Parameters
        ----------
        net_names : str, list
            Names of the nets to delete.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.

        References
        ----------

        >>> Edb.modeler.delete_primitives(net_names=["GND"])
        """
        if not isinstance(net_names, list):  # pragma: no cover
            net_names = [net_names]

        for p in self.primitives[:]:
            if p.net_name in net_names:
                p.delete()
        return True

    @pyaedt_function_handler()
    def get_primitives(self, net_name=None, layer_name=None, prim_type=None, is_void=False):
        """Get primitives by conditions.

        Parameters
        ----------
        net_name : str, optional
            Set filter on net_name. Default is `None`.
        layer_name : str, optional
            Set filter on layer_name. Default is `None`.
        prim_type :  str, optional
            Set filter on primitive type. Default is `None`.
        is_void : bool
            Set filter on is_void. Default is 'False'
        Returns
        -------
        list
            List of filtered primitives
        """
        prims = []
        for el in self.primitives:
            if not el.type:
                continue
            if net_name:
                if not el.net_name == net_name:
                    continue
            if layer_name:
                if not el.layer_name == layer_name:
                    continue
            if prim_type:
                if not el.type == prim_type:
                    continue
            if not el.is_void == is_void:
                continue
            prims.append(el)
        return prims

    @pyaedt_function_handler()
    def fix_circle_void_for_clipping(self):
        """Fix issues when circle void are clipped due to a bug in EDB.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when no changes were applied.
        """
        for void_circle in self.circles:
            if not void_circle.is_void:
                continue
            (
                res,
                center_x,
                center_y,
                radius,
            ) = void_circle.primitive_object.GetParameters()

            cloned_circle = self._edb.Cell.Primitive.Circle.Create(
                self._active_layout,
                void_circle.layer_name,
                void_circle.net,
                self._get_edb_value(center_x),
                self._get_edb_value(center_y),
                self._get_edb_value(radius),
            )
            if res:
                cloned_circle.SetIsNegative(True)
                void_circle.Delete()
        return True

    @pyaedt_function_handler()
    def add_void(self, shape, void_shape):
        """Add a void into a shape.

        Parameters
        ----------
        shape : Polygon
            Shape of the main object.
        void_shape : list, Path
            Shape of the voids.
        """
        flag = False
        if isinstance(shape, EDBPrimitives):
            shape = shape.primitive_object
        if not isinstance(void_shape, list):
            void_shape = [void_shape]
        for void in void_shape:
            if isinstance(void, EDBPrimitives):
                flag = shape.AddVoid(void.primitive_object)
            else:
                flag = shape.AddVoid(void)
            if not flag:
                return flag
        return True

    @pyaedt_function_handler()
    def shape_to_polygon_data(self, shape):
        """Convert a shape to polygon data.

        Parameters
        ----------
        shape : :class:`pyaedt.edb_core.layout.EdbLayout.Shape`
            Type of the shape to convert. Options are ``"rectangle"`` and ``"polygon"``.
        """
        if shape.type == "polygon":
            return self._createPolygonDataFromPolygon(shape)
        elif shape.type == "rectangle":
            return self._createPolygonDataFromRectangle(shape)
        else:
            self._logger.error(
                "Unsupported shape type %s when creating a polygon primitive.",
                shape.type,
            )
            return None

    @pyaedt_function_handler()
    def _createPolygonDataFromPolygon(self, shape):
        points = shape.points
        if not self._validatePoint(points[0]):
            self._logger.error("Error validating point.")
            return None
        arcs = []
        is_parametric = False
        for i in range(len(points) - 1):
            if i == 0:
                startPoint = points[-1]
                endPoint = points[i]
            else:
                startPoint = points[i - 1]
                endPoint = points[i]

            if not self._validatePoint(endPoint):
                return None
            startPoint = [self._get_edb_value(i) for i in startPoint]
            endPoint = [self._get_edb_value(i) for i in endPoint]
            if len(endPoint) == 2:
                is_parametric = (
                    is_parametric
                    or startPoint[0].IsParametric()
                    or startPoint[1].IsParametric()
                    or endPoint[0].IsParametric()
                    or endPoint[1].IsParametric()
                )
                arc = self._edb.Geometry.ArcData(
                    self._edb.Geometry.PointData(
                        self._get_edb_value(startPoint[0].ToDouble()),
                        self._get_edb_value(startPoint[1].ToDouble()),
                    ),
                    self._edb.Geometry.PointData(
                        self._get_edb_value(endPoint[0].ToDouble()),
                        self._get_edb_value(endPoint[1].ToDouble()),
                    ),
                )
                arcs.append(arc)
            elif len(endPoint) == 5:
                is_parametric = (
                    is_parametric
                    or startPoint[0].IsParametric()
                    or startPoint[1].IsParametric()
                    or endPoint[0].IsParametric()
                    or endPoint[1].IsParametric()
                    or endPoint[3].IsParametric()
                    or endPoint[4].IsParametric()
                )
                rotationDirection = self._edb.Geometry.RotationDirection.Colinear
                if endPoint[2].ToString() == "cw":
                    rotationDirection = self._edb.Geometry.RotationDirection.CW
                elif endPoint[2].ToString() == "ccw":
                    rotationDirection = self._edb.Geometry.RotationDirection.CCW
                else:
                    self._logger.error("Invalid rotation direction %s is specified.", endPoint[2])
                    return None
                arc = self._edb.Geometry.ArcData(
                    self._edb.Geometry.PointData(
                        self._get_edb_value(startPoint[0].ToDouble()),
                        self._get_edb_value(startPoint[1].ToDouble()),
                    ),
                    self._edb.Geometry.PointData(
                        self._get_edb_value(endPoint[0].ToDouble()),
                        self._get_edb_value(endPoint[1].ToDouble()),
                    ),
                    rotationDirection,
                    self._edb.Geometry.PointData(
                        self._get_edb_value(endPoint[3].ToDouble()),
                        self._get_edb_value(endPoint[4].ToDouble()),
                    ),
                )
                arcs.append(arc)
        polygon = self._edb.Geometry.PolygonData.CreateFromArcs(convert_py_list_to_net_list(arcs), True)
        if not is_parametric:
            return polygon
        else:
            k = 0
            for pt in points:
                point = [self._get_edb_value(i) for i in pt]
                new_points = self._edb.Geometry.PointData(point[0], point[1])
                if len(point) > 2:
                    k += 1
                polygon.SetPoint(k, new_points)
                k += 1
        return polygon

    @pyaedt_function_handler()
    def _validatePoint(self, point, allowArcs=True):
        if len(point) == 2:
            if not isinstance(point[0], (int, float, str)):
                self._logger.error("Point X value must be a number.")
                return False
            if not isinstance(point[1], (int, float, str)):
                self._logger.error("Point Y value must be a number.")
                return False
            return True
        elif len(point) == 5:
            if not allowArcs:
                self._logger.error("Arc found but arcs are not allowed in _validatePoint.")
                return False
            if not isinstance(point[0], (int, float, str)):
                self._logger.error("Point X value must be a number.")
                return False
            if not isinstance(point[1], (int, float, str)):
                self._logger.error("Point Y value must be a number.")
                return False
            if not isinstance(point[2], str) or point[2] not in ["cw", "ccw"]:
                self._logger.error("Invalid rotation direction {} is specified.")
                return False
            if not isinstance(point[3], (int, float, str)):
                self._logger.error("Arc center point X value must be a number.")
                return False
            if not isinstance(point[4], (int, float, str)):
                self._logger.error("Arc center point Y value must be a number.")
                return False
            return True
        else:
            self._logger.error("Arc point descriptor has incorrect number of elements (%s)", len(point))
            return False

    def _createPolygonDataFromRectangle(self, shape):
        if not self._validatePoint(shape.pointA, False) or not self._validatePoint(shape.pointB, False):
            return None
        pointA = self._edb.Geometry.PointData(
            self._get_edb_value(shape.pointA[0]), self._get_edb_value(shape.pointA[1])
        )
        pointB = self._edb.Geometry.PointData(
            self._get_edb_value(shape.pointB[0]), self._get_edb_value(shape.pointB[1])
        )
        points = Tuple[self._edb.Geometry.PointData, self._edb.Geometry.PointData](pointA, pointB)
        return self._edb.Geometry.PolygonData.CreateFromBBox(points)

    class Shape(object):
        """Shape class.

        Parameters
        ----------
        type : str, optional
            Type of the shape. Options are ``"circle"``, ``"rectangle"``, and ``"polygon"``.
            The default is ``"unknown``.
        pointA : optional
            Lower-left corner when ``type="rectangle"``. The default is ``None``.
        pointB : optional
            Upper-right corner when ``type="rectangle"``. The default is ``None``.
        centerPoint : optional
            Center point when ``type="circle"``. The default is ``None``.
        radius : optional
            Radius when ``type="circle"``. The default is ``None``.
        points : list, optional
            List of points when ``type="polygon"``. The default is ``None``.
        properties : dict, optional
            Dictionary of properties associated with the shape. The default is ``{}``.
        """

        def __init__(
            self,
            type="unknown",  # noqa
            pointA=None,
            pointB=None,
            centerPoint=None,
            radius=None,
            points=None,
            properties={},
        ):  # noqa
            self.type = type
            self.pointA = pointA
            self.pointB = pointB
            self.centerPoint = centerPoint
            self.radius = radius
            self.points = points
            self.properties = properties

    @pyaedt_function_handler()
    def parametrize_trace_width(
        self,
        nets_name,
        layers_name=None,
        parameter_name="trace_width",
        variable_value=None,
    ):
        """Parametrize a Trace on specific layer or all stackup.

        Parameters
        ----------
        nets_name : str, list
            name of the net or list of nets to parametrize.
        layers_name : str, optional
            name of the layer or list of layers to which the net to parametrize has to be included.
        parameter_name : str, optional
            name of the parameter to create.
        variable_value : str, float, optional
            value with units of parameter to create.
            If None, the first trace width of Net will be used as parameter value.

        Returns
        -------
        bool
        """
        if isinstance(nets_name, str):
            nets_name = [nets_name]
        if isinstance(layers_name, str):
            layers_name = [layers_name]
        for net_name in nets_name:
            var_server = False
            for p in self.paths:
                if p.GetNet().GetName() == net_name:
                    if not layers_name:
                        if not var_server:
                            if not variable_value:
                                variable_value = p.GetWidth()
                            result, var_server = self._pedb.add_design_variable(
                                parameter_name, variable_value, is_parameter=True
                            )
                        p.SetWidth(self._pedb.edb_value(parameter_name))
                    elif p.GetLayer().GetName() in layers_name:
                        if not var_server:
                            if not variable_value:
                                variable_value = p.GetWidth()
                            result, var_server = self._pedb.add_design_variable(
                                parameter_name, variable_value, is_parameter=True
                            )
                        p.SetWidth(self._pedb.edb_value(parameter_name))
        return True

    @pyaedt_function_handler()
    def unite_polygons_on_layer(self, layer_name=None, delete_padstack_gemometries=False):
        """Try to unite all Polygons on specified layer.

        Parameters
        ----------
        layer_name : str, optional
            Layer Name on which unite objects. If ``None``, all layers will be taken.
        delete_padstack_gemometries : bool, optional
            ``True`` to delete all padstack geometry.

        Returns
        -------
        bool
            ``True`` is successful.
        """
        if isinstance(layer_name, str):
            layer_name = [layer_name]
        if not layer_name:
            layer_name = list(self._pedb.stackup.signal_layers.keys())

        for lay in layer_name:
            self._logger.info("Uniting Objects on layer %s.", lay)
            poly_by_nets = {}
            if lay in list(self.polygons_by_layer.keys()):
                for poly in self.polygons_by_layer[lay]:
                    if not poly.GetNet().GetName() in list(poly_by_nets.keys()):
                        if poly.GetNet().GetName():
                            poly_by_nets[poly.GetNet().GetName()] = [poly]
                    else:
                        if poly.GetNet().GetName():
                            poly_by_nets[poly.GetNet().GetName()].append(poly)
            for net in poly_by_nets:
                list_polygon_data = [i.GetPolygonData() for i in poly_by_nets[net]]
                all_voids = [i.Voids for i in poly_by_nets[net]]
                a = self._edb.Geometry.PolygonData.Unite(convert_py_list_to_net_list(list_polygon_data))
                for item in a:
                    for v in all_voids:
                        for void in v:
                            if int(item.GetIntersectionType(void.GetPolygonData())) == 2:
                                item.AddHole(void.GetPolygonData())
                    poly = self._edb.Cell.Primitive.Polygon.Create(
                        self._active_layout,
                        lay,
                        self._pedb.nets.nets[net].net_object,
                        item,
                    )
                list_to_delete = [i for i in poly_by_nets[net]]
                for v in all_voids:
                    for void in v:
                        for poly in poly_by_nets[net]:
                            if int(void.GetPolygonData().GetIntersectionType(poly.GetPolygonData())) >= 2:
                                try:
                                    id = list_to_delete.index(poly)
                                except ValueError:
                                    id = -1
                                if id >= 0:
                                    list_to_delete.pop(id)

                [i.Delete() for i in list_to_delete]

        if delete_padstack_gemometries:
            self._logger.info("Deleting Padstack Definitions")
            for pad in self._pedb.padstacks.definitions:
                p1 = self._pedb.padstacks.definitions[pad].edb_padstack.GetData()
                if len(p1.GetLayerNames()) > 1:
                    self._pedb.padstacks.remove_pads_from_padstack(pad)
        return True

    @pyaedt_function_handler()
    def defeature_polygon(self, setup_info, poly, max_surface_deviation=0.001):
        """Defeature the polygon based on the maximum surface deviation criteria.

        Parameters
        ----------
        setup_info : EDB_Data_SimulatiomConfiguratio object
            When the ``setup_info`` argument is provided, it overwrites the
            ``maximum_surface_deviation`` value.

        poly : Edb Polygon primitive
            Polygon to defeature.

        max_surface_deviation : float, optional
            Maximum surface deviation criteria. The default is ``0.001``.

        Returns
        -------
        bool
            ``True`` when successful, ``False`` when failed.
        """
        try:
            if setup_info:
                max_surface_deviation = setup_info.max_suf_dev
            poly_data = poly.GetPolygonData()
            pts_list = []
            pts = poly_data.Points
            defeaturing_step = 1e-6
            if len(poly_data) <= 16:
                # Defeaturing skipped for polygons with less than 16 points
                self._logger.info(
                    "Polygon {} is skipped for defeaturing because its number of point is less than 16. ".format(
                        poly.GetId()
                    )
                )
                return poly_data

            for pt in pts:
                pts_list.append(pt)
            nb_ini_pts = len(pts_list)
            minimum_distance = defeaturing_step  # 1e-6
            init_surf = poly_data.Area()
            nb_pts_removed = 0
            surf_dev = 0
            new_poly = None
            while (surf_dev < max_surface_deviation and pts_list.Count > 16 and minimum_distance < 1000e-6) and float(
                nb_pts_removed
            ) / float(nb_ini_pts) < 0.4:
                pts_list, nb_pts_removed = self._trim_polygon_points(pts, minimum_distance)
                new_poly = self._edb.Geometry.PolygonData(pts_list, True)
                current_surf = new_poly.Area()
                if current_surf == 0:
                    surf_dev = 1
                else:
                    surf_dev = abs(init_surf - current_surf) / init_surf
                    minimum_distance = minimum_distance + defeaturing_step
            self._logger.info(
                "Defeaturing polygon {0}: Final surface deviation = {1} , Maximum distance(um) = {2}, "
                "Number of points removed = {3}/{4}".format(
                    str(poly.GetId()),
                    str(surf_dev),
                    str(minimum_distance * 1e6),
                    str(nb_pts_removed),
                    str(nb_ini_pts),
                )
            )
            return new_poly
        except:
            return False

    @pyaedt_function_handler()
    def _trim_polygon_points(self, points, minimum_distance):
        pts_list = []
        ind = 0

        nb_pts_removed = 0
        for pt in points:
            pts_list.append(pt)
        # NbIniPts = pts_list.Count

        while ind < pts_list.Count - 2:
            pts_list, nb_pts_removed = self._get_point_list_with_minimum_distance(
                pts_list, minimum_distance, ind, nb_pts_removed
            )
            ind = ind + 1

        return pts_list, nb_pts_removed

    @pyaedt_function_handler()
    def _get_point_list_with_minimum_distance(self, pts_list, minimum_distance, ind, nb_pts_removed):
        pt_ind = ind + 1
        while pts_list[ind].Distance(pts_list[pt_ind]) < minimum_distance and pt_ind < pts_list.Count - 2:
            pts_list.RemoveAt(pt_ind)
            nb_pts_removed += 1
            pt_ind += 1

        return pts_list, nb_pts_removed

    @pyaedt_function_handler()
    def get_layout_statistics(self, evaluate_area=False, net_list=None):
        """Return EDBStatistics object from a layout.

        Parameters
        ----------

        evaluate_area : optional bool
            When True evaluates the layout metal surface, can take time-consuming,
            avoid using this option on large design.

        Returns
        -------

        EDBStatistics object.

        """
        stat_model = EDBStatistics()
        stat_model.num_layers = len(list(self._pedb.stackup.stackup_layers.values()))
        stat_model.num_capacitors = len(self._pedb.components.capacitors)
        stat_model.num_resistors = len(self._pedb.components.resistors)
        stat_model.num_inductors = len(self._pedb.components.inductors)
        stat_model.layout_size = self._pedb._hfss.get_layout_bounding_box(self._active_layout)
        stat_model.num_discrete_components = (
            len(self._pedb.components.Others) + len(self._pedb.components.ICs) + len(self._pedb.components.IOs)
        )
        stat_model.num_inductors = len(self._pedb.components.inductors)
        stat_model.num_resistors = len(self._pedb.components.resistors)
        stat_model.num_capacitors = len(self._pedb.components.capacitors)
        stat_model.num_nets = len(self._pedb.nets.nets)
        stat_model.num_traces = len(self._pedb.modeler.paths)
        stat_model.num_polygons = len(self._pedb.modeler.polygons)
        stat_model.num_vias = len(self._pedb.padstacks.instances)
        stat_model.stackup_thickness = self._pedb.stackup.get_layout_thickness()
        if evaluate_area:
            if net_list:
                netlist = list(self._pedb.nets.nets.keys())
                _poly = self._pedb.get_conformal_polygon_from_netlist(netlist)
            else:
                _poly = self._pedb.get_conformal_polygon_from_netlist()
            stat_model.occupying_surface = _poly.Area()
            outline_surface = (stat_model.layout_size[2] - stat_model.layout_size[0]) * (
                stat_model.layout_size[3] - stat_model.layout_size[1]
            )
            stat_model.occupying_ratio = stat_model.occupying_surface / outline_surface
        return stat_model
